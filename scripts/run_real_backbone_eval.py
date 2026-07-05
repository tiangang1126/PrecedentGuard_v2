"""
Run real-backbone evaluation on AgentHarm slices using the current code layout.

Goals
-----
1. Preserve human-readable text in EIG payloads so HF backbones see real content.
2. Provide one unified JSONL output format across several experimental modes.
3. Decouple real evaluation from earlier Day 5 smoke-only script assumptions.

Modes
-----
- backbone_only: frozen backbone on base view B(I, A)
- no_counterfactual: frozen backbone on full current context + retrieved precedents
- clipping_only: PrecedentGuard over current evidence only (no precedents)
- pg_with_precedents: full PrecedentGuard pipeline with precedent retrieval
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from precedentguard import (
    GraniteGuardianBackend,
    LlamaGuardBackend,
    NodeType,
    PrecedentCapsule,
    PrecedentGuard,
    Provenance,
    RuntimeEvent,
    ShieldGemmaBackend,
    SimplePrecedentStore,
    build_eig_from_events,
)
from precedentguard.clipping import symmetric_caps
from precedentguard.counterfactual import Intervention, resolve_view
from precedentguard.guard import AttestationContext


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "day5"
ARTIFACT_DIR = ROOT / "artifacts" / "day5"


def short_hash(text: str, *, tag: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{tag}-{digest}"


def load_rows(file_path: Path, limit: int | None) -> list[dict]:
    rows: list[dict] = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def _candidate_dataset_paths(subset: str) -> list[Path]:
    patterns = [
        f"agentharm_{subset}_*.jsonl",
        f"**/agentharm_{subset}_*.jsonl",
    ]
    out: list[Path] = []
    for pattern in patterns:
        out.extend(sorted(ROOT.glob(pattern)))
    # de-duplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in out:
        if path not in seen and path.is_file():
            seen.add(path)
            unique.append(path)
    return unique


def resolve_dataset_file(subset: str, explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"--dataset-file points to a missing file: {path}"
            )
        return path

    if subset not in {"harmful", "harmless_benign"}:
        raise ValueError(f"unsupported subset: {subset}")

    default_path = DATA_DIR / f"agentharm_{subset}_176.jsonl"
    if default_path.is_file():
        return default_path

    mixed_agentharm = ROOT / "artifacts" / "day5" / "agentharm" / "agentharm.jsonl"
    if mixed_agentharm.is_file():
        return mixed_agentharm

    candidates = _candidate_dataset_paths(subset)
    if candidates:
        return candidates[0]

    searched = [
        str(default_path),
        str(ROOT / f"agentharm_{subset}_*.jsonl"),
        str(ROOT / f"**/agentharm_{subset}_*.jsonl"),
    ]
    raise FileNotFoundError(
        "Could not locate a local AgentHarm dataset file for subset "
        f"{subset!r}. Searched:\n- " + "\n- ".join(searched) + "\n"
        "Please pass an explicit --dataset-file path."
    )


def normalize_row(raw: dict) -> dict:
    """Normalize different local AgentHarm layouts into one schema."""
    if {"id", "prompt", "subset", "category"}.issubset(raw.keys()):
        return {
            "id": raw["id"],
            "prompt": raw["prompt"],
            "subset": raw["subset"],
            "category": raw["category"],
            "name": raw.get("name", ""),
            "trajectory": raw.get("trajectory", []),
        }

    metadata = raw.get("metadata", {})
    label = raw.get("label")
    if label not in {"safe", "unsafe"}:
        raise ValueError(
            "Unsupported AgentHarm row format: expected label in {'safe','unsafe'}"
        )
    return {
        "id": raw["id"],
        "prompt": raw.get("intent") or metadata.get("prompt") or "",
        "subset": "harmless_benign" if label == "safe" else "harmful",
        "category": metadata.get("category", "unknown"),
        "name": metadata.get("name", ""),
        "trajectory": raw.get("trajectory", []),
    }


def load_agentharm_rows(file_path: Path, subset: str, limit: int | None) -> list[dict]:
    rows: list[dict] = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = normalize_row(json.loads(line))
            if row["subset"] != subset:
                continue
            rows.append(row)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def make_precedent_store(rows: Iterable[dict], *, scope: str) -> SimplePrecedentStore:
    store = SimplePrecedentStore()
    for row in rows:
        is_safe = row.get("subset") != "harmful"
        trust = Provenance(
            origin_id="audit-validator" if is_safe else "historical-audit",
            signature_valid=is_safe,
            semantic_authorization=is_safe,
            scope=scope if is_safe else None,
            policy_version="v1" if is_safe else None,
        )
        store.add(
            PrecedentCapsule(
                capsule_id=f"ah-{row['id']}",
                trajectory_summary=row["prompt"],
                proposed_action=f"Execute the requested task: {row['prompt']}",
                audited_label=0 if is_safe else 1,
                justification=row.get("name", ""),
                trust=trust,
            )
        )
    return store


def make_leave_one_out_precedent_store(
    rows: Iterable[dict],
    *,
    scope: str,
    held_out_example_id: str,
) -> SimplePrecedentStore:
    return make_precedent_store(
        [row for row in rows if row["id"] != held_out_example_id],
        scope=scope,
    )


def _render_trajectory_event_payload(event: dict[str, Any]) -> str:
    parts = []
    for key in ("tool", "action", "result"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key}: {value.strip()}")
    return "\n".join(parts)


def infer_trajectory_node_type(event: dict[str, Any]) -> NodeType:
    tool = str(event.get("tool", "")).lower()
    action = str(event.get("action", "")).lower()
    result = str(event.get("result", "")).lower()
    combined = " ".join(part for part in (tool, action, result) if part)

    memory_keywords = (
        "email",
        "inbox",
        "message",
        "dm_",
        "direct_message",
        "login_data",
        "database",
        "read_file",
        "dir_list",
        "transaction",
        "client_",
    )
    retrieval_keywords = (
        "query_",
        "search",
        "webpage",
        "scrape",
        "query_posts",
        "get_posts",
        "browse",
        "query_google",
        "query_bing",
        "query_onion",
    )
    observation_keywords = (
        "assistant",
        "observation",
        "tool_plan::",
    )

    if any(keyword in combined for keyword in observation_keywords):
        return NodeType.OBSERVATION
    if any(keyword in combined for keyword in memory_keywords):
        return NodeType.MEMORY
    if any(keyword in combined for keyword in retrieval_keywords):
        return NodeType.RETRIEVAL
    return NodeType.TOOL_RETURN


def build_trajectory_events(
    example_id: str,
    intent_id: str,
    trajectory: list[dict[str, Any]],
) -> list[RuntimeEvent]:
    events: list[RuntimeEvent] = []
    previous_id = intent_id
    for idx, raw_event in enumerate(trajectory):
        payload = _render_trajectory_event_payload(raw_event)
        event_id = f"{example_id}-traj-{idx}"
        events.append(
            RuntimeEvent(
                event_id=event_id,
                node_type=infer_trajectory_node_type(raw_event),
                content_hash=short_hash(payload or f"empty-{idx}", tag="traj"),
                provenance=Provenance(),
                timestamp_ms=idx + 1,
                consumes=[previous_id],
                payload=payload,
            )
        )
        previous_id = event_id
    return events


def build_eig(example_id: str, prompt: str, trajectory: list[dict[str, Any]]) -> tuple[object, str]:
    intent_id = f"{example_id}-intent"
    action_id = f"{example_id}-action"
    trajectory_events = build_trajectory_events(example_id, intent_id, trajectory)
    action_consumes = [intent_id, *[event.event_id for event in trajectory_events]]
    action_payload = (
        str(trajectory[-1].get("action")).strip()
        if trajectory and str(trajectory[-1].get("action", "")).strip()
        else f"Execute the requested task: {prompt}"
    )
    events = [
        RuntimeEvent(
            event_id=intent_id,
            node_type=NodeType.INTENT,
            content_hash=short_hash(prompt, tag="intent"),
            provenance=Provenance(),
            timestamp_ms=0,
            payload=prompt,
        ),
        *trajectory_events,
        RuntimeEvent(
            event_id=action_id,
            node_type=NodeType.ACTION,
            content_hash=short_hash(action_payload, tag="action"),
            provenance=Provenance(),
            timestamp_ms=len(trajectory_events) + 1,
            consumes=action_consumes,
            payload=action_payload,
        ),
    ]
    return build_eig_from_events(events), action_id


def make_backend(name: str, model_id: str):
    if name == "llama_guard":
        return LlamaGuardBackend(model_id=model_id)
    if name == "shieldgemma":
        return ShieldGemmaBackend(model_id=model_id)
    if name == "granite_guardian":
        return GraniteGuardianBackend(model_id=model_id)
    raise ValueError(f"unsupported backend: {name}")


def make_guard(backend, *, store: SimplePrecedentStore | None, top_k: int) -> PrecedentGuard:
    caps = {
        NodeType.MEMORY: symmetric_caps(0.20),
        NodeType.RETRIEVAL: symmetric_caps(0.20),
        NodeType.OBSERVATION: symmetric_caps(0.20),
        NodeType.TOOL_RETURN: symmetric_caps(0.20),
        NodeType.PRECEDENT: symmetric_caps(0.15),
    }
    return PrecedentGuard(
        base_guard=backend,
        caps_by_type=caps,
        threshold=0.5,
        precedent_store=store,
        precedent_top_k=top_k,
        attestation_ctx=AttestationContext(
            current_scope="agentharm",
            accepted_policy_versions=frozenset({"v1"}),
        ),
    )


def backbone_only_score(guard: PrecedentGuard, eig, action_id: str) -> tuple[float, list[PrecedentCapsule]]:
    base_view = guard._base_view(eig)
    score = float(guard.base_guard(eig, action_id, base_view, precedents=[]))
    return score, []


def no_counterfactual_score(guard: PrecedentGuard, eig, action_id: str) -> tuple[float, list[PrecedentCapsule]]:
    retrieved = guard._retrieve_precedents(eig, action_id, None, None)
    capsules = [r.capsule for r in retrieved]
    full_view = resolve_view(eig, Intervention.empty())
    score = float(guard.base_guard(eig, action_id, full_view, precedents=capsules))
    return score, capsules


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        default="pg_with_precedents",
        choices=["backbone_only", "no_counterfactual", "clipping_only", "pg_with_precedents"],
    )
    parser.add_argument("--backend-name", default="llama_guard")
    parser.add_argument("--model-id", default="meta-llama/Llama-Guard-3-1B")
    parser.add_argument("--subset", default="harmful", choices=["harmful", "harmless_benign"])
    parser.add_argument("--dataset-file", default="")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--precedent-top-k", type=int, default=5)
    parser.add_argument("--output-file", default="")
    args = parser.parse_args()

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        dataset_path = resolve_dataset_file(args.subset, args.dataset_file or None)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    rows = load_agentharm_rows(dataset_path, args.subset, args.limit)

    backend = make_backend(args.backend_name, args.model_id)
    guard_without_precedents = make_guard(backend, store=None, top_k=args.precedent_top_k)

    out_path = (
        Path(args.output_file)
        if args.output_file
        else ARTIFACT_DIR / f"{args.backend_name}_{args.mode}_{args.subset}_{args.limit}.jsonl"
    )

    with out_path.open("w", encoding="utf-8") as out:
        for row in rows:
            eig, action_id = build_eig(
                row["id"],
                row["prompt"],
                row.get("trajectory", []),
            )
            guard_with_precedents = None
            if args.mode in {"no_counterfactual", "pg_with_precedents"}:
                precedent_store = make_leave_one_out_precedent_store(
                    rows,
                    scope="agentharm",
                    held_out_example_id=row["id"],
                )
                guard_with_precedents = make_guard(
                    backend,
                    store=precedent_store,
                    top_k=args.precedent_top_k,
                )

            if args.mode == "backbone_only":
                score, capsules = backbone_only_score(guard_without_precedents, eig, action_id)
                decision_payload = {
                    "score": score,
                    "base_score": score,
                    "s_pg": score,
                    "verdict": "block" if score >= 0.5 else "allow",
                    "precedent_ids": [],
                    "parent_ids": [],
                }
            elif args.mode == "no_counterfactual":
                assert guard_with_precedents is not None
                score, capsules = no_counterfactual_score(guard_with_precedents, eig, action_id)
                decision_payload = {
                    "score": score,
                    "base_score": score,
                    "s_pg": score,
                    "verdict": "block" if score >= 0.5 else "allow",
                    "precedent_ids": [c.capsule_id for c in capsules],
                    "parent_ids": [],
                }
            elif args.mode == "clipping_only":
                decision = guard_without_precedents.decide(eig, action_id)
                capsules = []
                decision_payload = {
                    "score": decision.s_pg,
                    "base_score": decision.base_score,
                    "s_pg": decision.s_pg,
                    "verdict": decision.verdict.value,
                    "precedent_ids": [],
                    "parent_ids": list(decision.parent_ids),
                }
            else:
                assert guard_with_precedents is not None
                decision = guard_with_precedents.decide(eig, action_id)
                capsules = [
                    guard_with_precedents.precedent_store.get(cid)
                    for cid in decision.precedent_ids
                ]
                decision_payload = {
                    "score": decision.s_pg,
                    "base_score": decision.base_score,
                    "s_pg": decision.s_pg,
                    "verdict": decision.verdict.value,
                    "precedent_ids": list(decision.precedent_ids),
                    "parent_ids": list(decision.parent_ids),
                }

            out.write(
                json.dumps(
                    {
                        "example_id": row["id"],
                        "subset": row["subset"],
                        "category": row["category"],
                        "mode": args.mode,
                        "backend_name": args.backend_name,
                        "model_id": args.model_id,
                        "prompt_text": row["prompt"],
                        "action_text": f"Execute the requested task: {row['prompt']}",
                        "retrieved_precedents": [
                            {
                                "capsule_id": c.capsule_id,
                                "audited_label": c.audited_label,
                            }
                            for c in capsules
                        ],
                        **decision_payload,
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )

    print(out_path)


if __name__ == "__main__":
    main()
