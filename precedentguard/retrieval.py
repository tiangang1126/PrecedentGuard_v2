"""
precedentguard/retrieval.py

Precedent capsule storage and retrieval (paper §4.3).

A precedent is stored as a tuple
    R_i = (Q_i, G_i, A_i, Y_i, J_i, T_i)
where Q_i is a compact trajectory summary, G_i is a subgraph signature,
A_i is the proposed action, Y_i is the audited label, J_i is a recorded
justification, and T_i is the trust record (Provenance).

Retrieval weights follow paper §4.3:
    w_i ∝ λ_s * sim_text(x, R_i) + λ_g * sim_graph(G_x, G_i) + λ_a * sim_action(A, A_i)
with Σ w_i = 1 and 0 ≤ w_i ≤ w_max.

Default similarity functions use token-Jaccard (deterministic, no ML dependency).
Callers may inject sentence-transformer or FAISS-backed similarities.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from precedentguard.types import Provenance


# ----------------------------------------------------------------------
# Capsule
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class PrecedentCapsule:
    """A stored precedent (paper §4.3 tuple R_i).

    Fields
    ------
    capsule_id : str
        Unique identifier.
    trajectory_summary : str
        Q_i — compact human-readable summary of the trajectory.
    proposed_action : str
        A_i — the action that was proposed at decision time.
    audited_label : int
        Y_i — 1 for unsafe (should have been blocked), 0 for safe.
    justification : str
        J_i — free-text rationale from the audit.
    trust : Provenance
        T_i — the capsule's own provenance / attestation record.
    subgraph_signature : str
        A serialized signature of G_i (used for structural similarity).
        Empty string means "no subgraph available".
    """

    capsule_id: str
    trajectory_summary: str
    proposed_action: str
    audited_label: int
    justification: str = ""
    trust: Provenance = field(default_factory=Provenance)
    subgraph_signature: str = ""


@dataclass(frozen=True)
class RetrievedPrecedent:
    """A retrieved precedent with its retrieval weight (w_i in §4.3)."""

    capsule: PrecedentCapsule
    weight: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError(f"weight must be in [0, 1]; got {self.weight}")


@dataclass(frozen=True)
class RetrievalDebugMatch:
    """Per-capsule retrieval score breakdown for diagnostics only."""

    capsule_id: str
    audited_label: int
    text_similarity: float
    action_similarity: float
    graph_similarity: float
    raw_score: float
    normalized_weight: float
    selected: bool = False


# ----------------------------------------------------------------------
# Default similarity functions
# ----------------------------------------------------------------------


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(s: str) -> set[str]:
    """Lowercase-token bag (no ordering)."""
    return {t.lower() for t in _TOKEN_RE.findall(s)}


def token_jaccard(a: str, b: str) -> float:
    """Jaccard similarity between token bags of two strings. Symmetric."""
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 1.0
    union = ta | tb
    if not union:
        return 0.0
    inter = ta & tb
    return len(inter) / len(union)


def exact_match_similarity(a: str, b: str) -> float:
    """Return 1.0 if strings are identical (case-insensitive), else Jaccard."""
    if a.lower().strip() == b.lower().strip():
        return 1.0
    return token_jaccard(a, b)


# ----------------------------------------------------------------------
# SimplePrecedentStore
# ----------------------------------------------------------------------


SimilarityFn = Callable[[str, str], float]


@dataclass
class SimplePrecedentStore:
    """In-memory precedent store with pluggable similarity functions.

    Retrieval combines text / action / subgraph similarities per §4.3 with
    normalization Σ w_i = 1 and per-item cap w_max.

    Parameters
    ----------
    text_sim : Callable[[str, str], float]
        Default: token_jaccard on trajectory_summary.
    action_sim : Callable[[str, str], float]
        Default: exact_match_similarity on proposed_action.
    subgraph_sim : Callable[[str, str], float]
        Default: token_jaccard on subgraph_signature.
    lambda_s, lambda_a, lambda_g : float
        Convex combination weights for text / action / subgraph similarities.
        Must be non-negative and sum to 1 (checked).
    w_max : float
        Per-item weight cap. Default 0.5 (no single precedent may dominate).
    """

    text_sim: SimilarityFn = token_jaccard
    action_sim: SimilarityFn = exact_match_similarity
    subgraph_sim: SimilarityFn = token_jaccard
    lambda_s: float = 0.5
    lambda_a: float = 0.3
    lambda_g: float = 0.2
    w_max: float = 0.5
    label_balance_min_ratio: float = 0.75

    _capsules: dict[str, PrecedentCapsule] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        s = self.lambda_s + self.lambda_a + self.lambda_g
        if any(x < 0 for x in (self.lambda_s, self.lambda_a, self.lambda_g)):
            raise ValueError(
                f"lambda_s/a/g must be non-negative; got "
                f"({self.lambda_s}, {self.lambda_a}, {self.lambda_g})"
            )
        if not math.isclose(s, 1.0, abs_tol=1e-6):
            raise ValueError(
                f"lambda_s + lambda_a + lambda_g must sum to 1; got {s}"
            )
        if not (0.0 < self.w_max <= 1.0):
            raise ValueError(f"w_max must be in (0, 1]; got {self.w_max}")
        if not (0.0 <= self.label_balance_min_ratio <= 1.0):
            raise ValueError(
                "label_balance_min_ratio must be in [0, 1]; "
                f"got {self.label_balance_min_ratio}"
            )

    # -------- CRUD --------

    def add(self, capsule: PrecedentCapsule) -> None:
        if capsule.capsule_id in self._capsules:
            raise ValueError(f"duplicate capsule_id: {capsule.capsule_id}")
        self._capsules[capsule.capsule_id] = capsule

    def add_many(self, capsules: Iterable[PrecedentCapsule]) -> None:
        for c in capsules:
            self.add(c)

    def get(self, capsule_id: str) -> PrecedentCapsule:
        return self._capsules[capsule_id]

    def __len__(self) -> int:
        return len(self._capsules)

    def __contains__(self, capsule_id: str) -> bool:
        return capsule_id in self._capsules

    def all_capsules(self) -> list[PrecedentCapsule]:
        return list(self._capsules.values())

    # -------- Retrieval --------

    def raw_score(
        self,
        capsule: PrecedentCapsule,
        query_summary: str,
        query_action: str,
        query_subgraph_signature: str = "",
    ) -> float:
        """Un-normalized combined similarity for one capsule."""
        s_text = self.text_sim(query_summary, capsule.trajectory_summary)
        s_action = self.action_sim(query_action, capsule.proposed_action)
        s_graph = (
            self.subgraph_sim(query_subgraph_signature, capsule.subgraph_signature)
            if capsule.subgraph_signature or query_subgraph_signature
            else 0.0
        )
        return (
            self.lambda_s * s_text
            + self.lambda_a * s_action
            + self.lambda_g * s_graph
        )

    def score_breakdown(
        self,
        capsule: PrecedentCapsule,
        query_summary: str,
        query_action: str,
        query_subgraph_signature: str = "",
    ) -> dict[str, float]:
        """Return component-wise similarities for diagnostics."""
        s_text = self.text_sim(query_summary, capsule.trajectory_summary)
        s_action = self.action_sim(query_action, capsule.proposed_action)
        s_graph = (
            self.subgraph_sim(query_subgraph_signature, capsule.subgraph_signature)
            if capsule.subgraph_signature or query_subgraph_signature
            else 0.0
        )
        combined = (
            self.lambda_s * s_text
            + self.lambda_a * s_action
            + self.lambda_g * s_graph
        )
        return {
            "text_similarity": s_text,
            "action_similarity": s_action,
            "graph_similarity": s_graph,
            "raw_score": combined,
        }

    def retrieval_debug_summary(
        self,
        query_summary: str,
        query_action: str,
        query_subgraph_signature: str = "",
        top_k: int = 5,
        selected_top_k: int | None = None,
        strategy: str = "vanilla",
    ) -> dict[str, Any]:
        """Return top-k diagnostic breakdown without changing retrieval logic."""
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1; got {top_k}")
        if selected_top_k is None:
            selected_top_k = top_k
        if selected_top_k < 1:
            raise ValueError(f"selected_top_k must be >= 1; got {selected_top_k}")
        if not self._capsules:
            return {
                "hit_count": 0,
                "label_distribution": {"safe": 0, "unsafe": 0},
                "selected_label_distribution": {"safe": 0, "unsafe": 0},
                "top_matches": [],
                "strategy": strategy,
            }

        scored = self._score_capsules(
            query_summary,
            query_action,
            query_subgraph_signature,
        )
        probe = scored[:top_k]
        selected = self._select_capsules(
            scored,
            top_k=selected_top_k,
            strategy=strategy,
        )
        selected_ids = {cap.capsule_id for cap, _ in selected}
        report_items = list(probe)
        for item in selected:
            if item[0].capsule_id not in {cap.capsule_id for cap, _ in report_items}:
                report_items.append(item)
        report_items.sort(key=lambda t: (-t[1]["raw_score"], t[0].capsule_id))

        weights = self._normalize_scores(
            [metrics["raw_score"] for _, metrics in report_items]
        )
        matches = [
            RetrievalDebugMatch(
                capsule_id=cap.capsule_id,
                audited_label=cap.audited_label,
                text_similarity=metrics["text_similarity"],
                action_similarity=metrics["action_similarity"],
                graph_similarity=metrics["graph_similarity"],
                raw_score=metrics["raw_score"],
                normalized_weight=weight,
                selected=cap.capsule_id in selected_ids,
            )
            for (cap, metrics), weight in zip(report_items, weights)
        ]
        return {
            "hit_count": len(matches),
            "label_distribution": {
                "safe": sum(1 for m in matches if m.audited_label == 0),
                "unsafe": sum(1 for m in matches if m.audited_label == 1),
            },
            "selected_label_distribution": {
                "safe": sum(
                    1 for cap, _ in selected if cap.audited_label == 0
                ),
                "unsafe": sum(
                    1 for cap, _ in selected if cap.audited_label == 1
                ),
            },
            "strategy": strategy,
            "top_matches": [
                {
                    "capsule_id": match.capsule_id,
                    "audited_label": match.audited_label,
                    "text_similarity": round(match.text_similarity, 6),
                    "action_similarity": round(match.action_similarity, 6),
                    "graph_similarity": round(match.graph_similarity, 6),
                    "raw_score": round(match.raw_score, 6),
                    "normalized_weight": round(match.normalized_weight, 6),
                    "selected": match.selected,
                }
                for match in matches
            ],
        }

    def _score_capsules(
        self,
        query_summary: str,
        query_action: str,
        query_subgraph_signature: str = "",
    ) -> list[tuple[PrecedentCapsule, dict[str, float]]]:
        scored: list[tuple[PrecedentCapsule, dict[str, float]]] = []
        for cid, cap in self._capsules.items():
            _ = cid
            scored.append(
                (
                    cap,
                    self.score_breakdown(
                        cap,
                        query_summary,
                        query_action,
                        query_subgraph_signature,
                    ),
                )
            )
        scored.sort(key=lambda t: (-t[1]["raw_score"], t[0].capsule_id))
        return scored

    def _normalize_scores(self, raw_scores: list[float]) -> list[float]:
        if not raw_scores:
            return []
        raw_sum = sum(raw_scores)
        if raw_sum <= 0:
            uniform = min(self.w_max, 1.0 / len(raw_scores))
            return [uniform for _ in raw_scores]
        return self._water_fill_cap([score / raw_sum for score in raw_scores])

    def _select_capsules(
        self,
        scored: list[tuple[PrecedentCapsule, dict[str, float]]],
        *,
        top_k: int,
        strategy: str,
    ) -> list[tuple[PrecedentCapsule, dict[str, float]]]:
        if strategy == "vanilla":
            return scored[:top_k]
        if strategy != "label_balanced":
            raise ValueError(f"unsupported retrieval strategy: {strategy}")

        if not scored or top_k <= 0:
            return []

        selected: list[tuple[PrecedentCapsule, dict[str, float]]] = [scored[0]]
        remaining = scored[1:]
        if top_k == 1:
            return selected

        first_label = selected[0][0].audited_label
        first_score = selected[0][1]["raw_score"]
        min_score = first_score * self.label_balance_min_ratio
        opposite = next(
            (
                item for item in remaining
                if item[0].audited_label != first_label
                and item[1]["raw_score"] >= min_score
            ),
            None,
        )
        if opposite is not None:
            selected.append(opposite)
            remaining = [
                item for item in remaining
                if item[0].capsule_id != opposite[0].capsule_id
            ]
        for item in remaining:
            if len(selected) >= top_k:
                break
            selected.append(item)
        return selected

    def retrieve(
        self,
        query_summary: str,
        query_action: str,
        query_subgraph_signature: str = "",
        top_k: int = 5,
        strategy: str = "vanilla",
    ) -> list[RetrievedPrecedent]:
        """Return top-k precedents ranked by combined similarity.

        Weights are normalized (Σ w_i = 1) and clipped to [0, w_max]. Ties
        are broken by capsule_id for determinism.
        """
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1; got {top_k}")
        if not self._capsules:
            return []

        scored = self._score_capsules(
            query_summary,
            query_action,
            query_subgraph_signature,
        )
        top = self._select_capsules(scored, top_k=top_k, strategy=strategy)
        final = self._normalize_scores([metrics["raw_score"] for _, metrics in top])
        return [
            RetrievedPrecedent(cap, w) for (cap, _), w in zip(top, final)
        ]

    def _water_fill_cap(self, weights: list[float]) -> list[float]:
        """Cap each weight at w_max and redistribute excess to non-capped items.

        Guarantees w_i ≤ w_max and (if feasible) Σ w_i = 1.
        Infeasible when k · w_max < 1 (returns capped weights summing to k · w_max).
        """
        k = len(weights)
        w_max = self.w_max
        w = list(weights)

        # Handle infeasibility: k * w_max < 1 means we cannot reach Σ = 1
        if k * w_max < 1.0 - 1e-12:
            return [w_max] * k

        for _ in range(k + 1):
            capped = [min(wi, w_max) for wi in w]
            deficit = 1.0 - sum(capped)
            if abs(deficit) < 1e-9:
                return capped
            # Distribute deficit to non-capped items
            free_idx = [i for i, wi in enumerate(capped) if wi < w_max - 1e-9]
            if not free_idx:
                return capped
            free_sum = sum(capped[i] for i in free_idx)
            if free_sum > 1e-12:
                # Proportional to current (non-capped) weight
                for i in free_idx:
                    capped[i] += deficit * capped[i] / free_sum
            else:
                # Uniform among non-capped items
                per_item = deficit / len(free_idx)
                for i in free_idx:
                    capped[i] += per_item
            w = capped
        return w
