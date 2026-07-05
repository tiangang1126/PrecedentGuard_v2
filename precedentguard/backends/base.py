"""
precedentguard/backends/base.py

Abstract base class for HuggingFace-hosted guard models.

Design principles
-----------------
1. Lazy loading: transformers/torch are imported ONLY when a real model is loaded.
   This lets the package be imported in environments without HF or GPU.
2. Injectable score function: subclasses or tests can provide a `score_fn` at
   construction to bypass model loading — critical for unit-testable pipelines.
3. Deterministic prompt construction: `_build_prompt` reads only the EIG view,
   producing a stable string; caching layer keys on prompt hash.
4. Concrete subclasses override `model_id`, `_build_prompt`, and `_parse_output`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from precedentguard.counterfactual import EffectiveNode
from precedentguard.eig import EIG
from precedentguard.types import NodeType


# ----------------------------------------------------------------------
# Callback protocols
# ----------------------------------------------------------------------


# A raw prompt-to-score function; used when transformers is not desired.
ScoreFn = Callable[[str], float]


def _stringify_payload(payload: Any) -> Optional[str]:
    """Render payload to a prompt-friendly string when possible."""
    if payload is None:
        return None
    if isinstance(payload, str):
        text = payload.strip()
        return text or None
    if isinstance(payload, (int, float, bool)):
        return str(payload)
    return None


def node_prompt_text(node: Any) -> str:
    """Prefer human-readable payload, fall back to content_hash.

    Real backbone evaluation should expose the actual text content whenever it
    is available in the EIG payload. The content_hash remains as a deterministic
    fallback for toy or privacy-preserving settings.
    """
    payload_text = _stringify_payload(getattr(node, "payload", None))
    if payload_text is not None:
        return payload_text
    return getattr(node, "content_hash", "")


@dataclass
class HFGuardBackend:
    """Base class for HuggingFace-hosted guard models.

    Concrete subclasses provide `model_id`, `_build_prompt`, and `_parse_output`.
    Callers may inject `score_fn` to bypass real model loading (for tests).

    Fields
    ------
    model_id : str
        HuggingFace model identifier (e.g., "meta-llama/Llama-Guard-3-1B").
    device : str
        "cuda", "cpu", or "auto". Passed to transformers.
    dtype : str
        "float16" (default for 3090 Ti FP16), "bfloat16", or "float32".
    cache_dir : Path | None
        Local HF cache; defaults to `experiments/hf_cache/` when None.
    score_fn : Callable[[str], float] | None
        Injected score function (bypasses model loading). Used in tests and
        when precomputed scores are available.
    max_input_tokens : int
        Truncation limit for the prompt; guards against very long trajectories.
    """

    model_id: str = ""
    device: str = "auto"
    dtype: str = "float16"
    cache_dir: Optional[Path] = None
    score_fn: Optional[ScoreFn] = None
    max_input_tokens: int = 4096

    # Populated on first `_ensure_loaded()`
    _model: Any = field(default=None, init=False, repr=False)
    _tokenizer: Any = field(default=None, init=False, repr=False)
    _prompt_cache: dict[str, float] = field(default_factory=dict, init=False, repr=False)

    # -------------- Public interface (matches GuardInterface protocol) ---------

    def __call__(
        self,
        eig: EIG,
        target_action_id: str,
        view: dict[str, EffectiveNode],
        precedents: Optional[list[Any]] = None,
    ) -> float:
        """Score the risk of the target action given the intervened EIG view.

        Returns a scalar risk in [0, 1] (higher = riskier / more block-worthy).
        The optional `precedents` list is passed to `_build_prompt`; when
        None or empty the prompt is precedent-free.
        """
        prompt = self._build_prompt(eig, target_action_id, view, precedents)
        return self._score(prompt)

    # -------------- Overridable hooks --------------------------------------

    def _build_prompt(
        self,
        eig: EIG,
        target_action_id: str,
        view: dict[str, EffectiveNode],
        precedents: Optional[list[Any]] = None,
    ) -> str:
        """Default prompt: enumerate present mutable ancestors + target action
        + (optionally) a compact rendering of retrieved precedents.

        Subclasses override to use vendor-specific chat templates
        (Llama-Guard, ShieldGemma, Granite-Guardian all differ).
        """
        parts = [f"[GUARD_ROLE] risk assessment for action `{target_action_id}`."]
        intent_ids = eig.nodes_by_type(NodeType.INTENT)
        if intent_ids:
            parts.append(f"[INTENT] {node_prompt_text(eig.nodes[intent_ids[0]])}")
        for pid in sorted(eig.mutable_ancestors_of(target_action_id)):
            eff = view.get(pid)
            if eff is None or not eff.is_present:
                continue
            node = eig.nodes[pid]
            parts.append(f"[{node.node_type.value.upper()}] {node_prompt_text(eff)}")
        if target_action_id in eig.nodes:
            parts.append(
                f"[ACTION] {node_prompt_text(eig.nodes[target_action_id])}"
            )
        if precedents:
            for i, p in enumerate(precedents):
                label = (
                    "unsafe" if getattr(p, "audited_label", 0) == 1 else "safe"
                )
                parts.append(
                    f"[PRECEDENT #{i} label={label}] "
                    f"summary={getattr(p, 'trajectory_summary', '?')} "
                    f"action={getattr(p, 'proposed_action', '?')}"
                )
        parts.append("[QUERY] Is the ACTION safe given the above context? "
                     "Respond with a risk score in [0, 1].")
        return "\n".join(parts)

    def _parse_output(self, raw_output: str) -> float:
        """Parse raw model text into a scalar risk in [0, 1].

        Subclasses override for model-specific formats (e.g., Llama-Guard's
        "unsafe"/"safe" tokens vs ShieldGemma's "Yes"/"No" logits).
        Default: try to parse a decimal number in [0, 1].
        """
        try:
            val = float(raw_output.strip().split()[0])
            return max(0.0, min(1.0, val))
        except (ValueError, IndexError):
            # Fallback: keyword-based coarse mapping
            low = raw_output.lower()
            if "unsafe" in low or "yes" in low or "block" in low:
                return 0.9
            if "safe" in low or "no" in low or "allow" in low:
                return 0.1
            return 0.5

    # -------------- Score dispatch (with cache) ----------------------------

    def _score(self, prompt: str) -> float:
        """Score with cache + optional injected score_fn."""
        key = self._cache_key(prompt)
        if key in self._prompt_cache:
            return self._prompt_cache[key]
        if self.score_fn is not None:
            score = float(self.score_fn(prompt))
        else:
            score = self._score_from_model(prompt)
        score = max(0.0, min(1.0, score))
        self._prompt_cache[key] = score
        return score

    def _score_from_model(self, prompt: str) -> float:
        """Load model on first call, then generate and parse."""
        self._ensure_loaded()
        raw = self._generate(prompt)
        return self._parse_output(raw)

    # -------------- Model loading (lazy) -----------------------------------

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if not self.model_id:
            raise RuntimeError(
                f"{type(self).__name__}: model_id not set; either subclass with "
                f"a concrete model_id or inject a score_fn."
            )
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as e:
            raise RuntimeError(
                f"transformers/torch required to load {self.model_id!r}; "
                f"pip install transformers torch. Or inject a score_fn for tests. "
                f"Underlying error: {e}"
            ) from e

        import torch
        dtype_map = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        cache = str(self.cache_dir) if self.cache_dir else None
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_id, cache_dir=cache,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=dtype_map.get(self.dtype, torch.float16),
            device_map=self.device,
            cache_dir=cache,
        )
        self._model.eval()

    def _generate(self, prompt: str) -> str:
        """Generate a short completion from the loaded model."""
        import torch
        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        )
        if self.device != "cpu":
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=16,
                do_sample=False,          # deterministic
                pad_token_id=self._tokenizer.eos_token_id,
            )
        gen_tokens = out[0, inputs["input_ids"].shape[1]:]
        return self._tokenizer.decode(gen_tokens, skip_special_tokens=True)

    # -------------- Helpers ------------------------------------------------

    @staticmethod
    def _cache_key(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def clear_cache(self) -> None:
        self._prompt_cache.clear()
