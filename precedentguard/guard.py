"""
precedentguard/guard.py

PrecedentGuard runtime decision layer — implements Algorithm 1 (v0.2 Section 4.8).

Five-stage pipeline:
  1. Build/receive EIG from trusted runtime instrumentation (A1).
  2. Select decision-relevant evidence parents (mutable ancestors of target action).
  3. Retrieve precedent capsules when a precedent_store is configured.
  4. Estimate bounded counterfactual contributions (delta_e per parent, delta_i per precedent).
  5. Aggregate under directional trust constraints + calibrated threshold.

The current implementation supports both precedent-free execution and the full
precedent-aware decision path used in v0.2 Section 4.3-4.8.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Mapping, Optional

from precedentguard.clipping import (
    Contribution,
    TypeCaps,
    aggregate,
)
from precedentguard.counterfactual import (
    DEFAULT_CTRL_HASH,
    EffectiveNode,
    GuardInterface,
    Intervention,
    counterfactual_delta,
    precedent_counterfactual_delta,
    resolve_view,
)
from precedentguard.eig import EIG
from precedentguard.retrieval import (
    PrecedentCapsule,
    RetrievedPrecedent,
    SimplePrecedentStore,
)
from precedentguard.types import InterventionOp, NodeType


def _node_query_text(node: Any) -> str:
    payload = getattr(node, "payload", None)
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    return getattr(node, "content_hash", "")


class Verdict(Enum):
    """Binary guard verdict (v0.2 Section 4.7)."""

    ALLOW = "allow"
    BLOCK = "block"


@dataclass(frozen=True)
class Decision:
    """A runtime decision with full audit trail.

    Fields
    ------
    verdict : Verdict
        BLOCK if S_PG >= theta else ALLOW.
    s_pg : float
        Final score S_PG = B(I, A) + clip(sum contributions, -eps_-, +eps_+).
    base_score : float
        B(I, A) — frozen guard on intent+action alone.
    z_before_outer : float
        Weighted sum of PG-clipped contributions before the outer clip.
    z_after_outer : float
        z_before_outer after outer_clip.
    parent_ids : tuple[str, ...]
        The evidence parent set P_x used for aggregation (sorted).
    per_parent_delta : dict[str, float]
        Raw delta_e for each parent (pre-clip).
    per_parent_type_clipped : dict[str, float]
        After type-clip.
    per_parent_pg_clipped : dict[str, float]
        After directional trust rule.
    precedent_ids : tuple[str, ...]
        Capsule ids of retrieved precedents used for aggregation (sorted).
    per_precedent_delta : dict[str, float]
        Raw delta_i for each precedent (pre-clip).
    per_precedent_pg_clipped : dict[str, float]
        Post type-clip + directional-trust-clip; keys are `precedent:<cid>`.
    timing_ms : dict[str, float]
        Stage-level profiling summary in milliseconds.
    retrieval_diagnostics : dict[str, Any]
        Retrieval hit diagnostics for runtime analysis.
    """

    verdict: Verdict
    s_pg: float
    base_score: float
    z_before_outer: float
    z_after_outer: float
    parent_ids: tuple[str, ...]
    per_parent_delta: dict[str, float]
    per_parent_type_clipped: dict[str, float]
    per_parent_pg_clipped: dict[str, float]
    precedent_ids: tuple[str, ...] = ()
    per_precedent_delta: dict[str, float] = field(default_factory=dict)
    per_precedent_pg_clipped: dict[str, float] = field(default_factory=dict)
    timing_ms: dict[str, float] = field(default_factory=dict)
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)


# Coefficient policy: callers may provide a function beta(node_id, node_type) -> float.
BetaFn = Callable[[str, NodeType], float]


def _uniform_beta(_node_id: str, _node_type: NodeType) -> float:
    return 1.0


# Attestation context for the Provenance.is_attested() call in each parent.
@dataclass(frozen=True)
class AttestationContext:
    """Context passed to Provenance.is_attested() during aggregation."""

    current_scope: Optional[str] = None
    current_epoch_ms: Optional[int] = None
    accepted_policy_versions: Optional[frozenset[str]] = None


@dataclass
class PrecedentGuard:
    """Runtime decision layer wrapping a frozen backbone guard.

    Parameters
    ----------
    base_guard : GuardInterface
        Frozen backbone (e.g., a Llama-Guard-family or ShieldGemma-family model).
        Must be deterministic given (eig, target_action_id, view) or accept a seed.
    caps_by_type : Mapping[NodeType, TypeCaps]
        Per-type contribution caps c_k^-, c_k^+. Should include
        `NodeType.PRECEDENT` if `precedent_store` is provided.
    eps_neg, eps_pos : float
        Outer clip bounds.
    threshold : float
        Decision threshold theta (v0.2 Section 3.1).
    q : int
        Number of repeated counterfactual evaluations per parent.
    beta_fn : BetaFn
        Per-parent coefficient function (defaults to 1.0).
    attestation_ctx : AttestationContext
        Context for evaluating the attested predicate per parent.
    precedent_store : Optional[SimplePrecedentStore]
        When provided, `decide()` retrieves top-k precedents and incorporates
        their counterfactual influence into the aggregated score
        (v0.2 §4.3-§4.6). When None, the decision uses only current-trajectory
        evidence (backward-compatible).
    precedent_top_k : int
        Number of precedents retrieved per decision.
    precedent_retrieval_strategy : str
        Retrieval selection strategy passed to the precedent store.
    """

    base_guard: GuardInterface
    caps_by_type: Mapping[NodeType, TypeCaps]
    eps_neg: float = 1.0
    eps_pos: float = 1.0
    threshold: float = 0.5
    q: int = 1
    beta_fn: BetaFn = field(default=_uniform_beta)
    attestation_ctx: AttestationContext = field(default_factory=AttestationContext)
    precedent_store: Optional[SimplePrecedentStore] = None
    precedent_top_k: int = 5
    precedent_retrieval_strategy: str = "vanilla"
    precedent_safe_beta_scale: float = 1.0
    precedent_unsafe_beta_scale: float = 1.0

    def _base_view(self, eig: EIG) -> dict[str, EffectiveNode]:
        """Minimal context for base score B(I, A): ablate all mutable evidence."""
        mutable_ids = [
            nid for nid, n in eig.nodes.items() if n.node_type.is_mutable_by_attacker
        ]
        return resolve_view(eig, Intervention.ablate(mutable_ids))

    def _query_subgraph_signature(self, eig: EIG) -> str:
        """Derive the query-side counterpart to precedent subgraph signatures.

        Sorted multiset of mutable-ancestor node types. Callers that need a
        different structural fingerprint pass it through ``decide()``.
        """
        tokens = sorted(
            node.node_type.value
            for node in eig.nodes.values()
            if node.node_type.is_mutable_by_attacker
        )
        return " ".join(tokens) if tokens else "empty"

    def _retrieve_precedents(
        self,
        eig: EIG,
        target_action_id: str,
        query_summary: Optional[str],
        query_action: Optional[str],
        query_subgraph_signature: Optional[str] = None,
    ) -> list[RetrievedPrecedent]:
        """Retrieve top-k precedents when a store is configured (§4.3)."""
        if self.precedent_store is None or len(self.precedent_store) == 0:
            return []
        # Sensible defaults if caller doesn't supply queries
        if query_summary is None:
            intent_ids = eig.nodes_by_type(NodeType.INTENT)
            query_summary = (
                _node_query_text(eig.nodes[intent_ids[0]]) if intent_ids else ""
            )
        if query_action is None:
            query_action = (
                _node_query_text(eig.nodes[target_action_id])
                if target_action_id in eig.nodes else ""
            )
        if query_subgraph_signature is None:
            query_subgraph_signature = self._query_subgraph_signature(eig)
        return self.precedent_store.retrieve(
            query_summary=query_summary,
            query_action=query_action,
            query_subgraph_signature=query_subgraph_signature,
            top_k=self.precedent_top_k,
            strategy=self.precedent_retrieval_strategy,
        )

    def decide(
        self,
        eig: EIG,
        target_action_id: str,
        *,
        query_summary: Optional[str] = None,
        query_action: Optional[str] = None,
        query_subgraph_signature: Optional[str] = None,
    ) -> Decision:
        """Return the runtime decision for the target action given the EIG.

        Implements Algorithm 1 (v0.2 §4.8) with the full five-stage pipeline:
        parent selection, base score, precedent retrieval, counterfactual
        influence estimation (evidence + precedents), and directional-trust
        aggregation.

        Parameters
        ----------
        eig : EIG
            The execution-grounded intervention graph.
        target_action_id : str
            Node id of the candidate action being scored.
        query_summary, query_action : Optional[str]
            Retrieval queries for the precedent store. Defaults derive from
            intent and action node content hashes.
        """
        if target_action_id not in eig.nodes:
            raise ValueError(f"target action {target_action_id!r} not in EIG")
        total_started = time.perf_counter()
        timing_ms: dict[str, float] = {
            "retrieval_ms": 0.0,
            "base_guard_ms": 0.0,
            "evidence_counterfactual_ms": 0.0,
            "precedent_counterfactual_ms": 0.0,
            "aggregation_ms": 0.0,
            "total_ms": 0.0,
        }

        # Stage 1: parent selection (mutable ancestors of the target action)
        parent_ids = tuple(sorted(eig.mutable_ancestors_of(target_action_id)))

        # Stage 2: retrieve precedents (empty when store is None)
        retrieval_started = time.perf_counter()
        retrieved = self._retrieve_precedents(
            eig,
            target_action_id,
            query_summary,
            query_action,
            query_subgraph_signature,
        )
        timing_ms["retrieval_ms"] = (
            time.perf_counter() - retrieval_started
        ) * 1000.0
        retrieved_capsules = [r.capsule for r in retrieved]
        retrieval_diagnostics = {
            "hit_count": len(retrieved),
            "label_distribution": {
                "safe": sum(1 for r in retrieved if r.capsule.audited_label == 0),
                "unsafe": sum(1 for r in retrieved if r.capsule.audited_label == 1),
            },
            "weights": {
                r.capsule.capsule_id: round(r.weight, 6)
                for r in retrieved
            },
        }

        # Stage 3: base score B(I, A) on the mutable-ablated context only.
        # Retrieved precedents are excluded here so their effect is accounted
        # for exactly once through delta_i aggregation below.
        base_view = self._base_view(eig)
        base_guard_started = time.perf_counter()
        base_score = float(self.base_guard(
            eig, target_action_id, base_view, precedents=[],
        ))
        timing_ms["base_guard_ms"] = (
            time.perf_counter() - base_guard_started
        ) * 1000.0

        # Stage 4a: per-evidence-parent counterfactual influence (delta_e).
        # Precedents are held constant during the evidence ablation.
        per_delta: dict[str, float] = {}
        contribs: list[Contribution] = []
        evidence_cf_started = time.perf_counter()
        for pid in parent_ids:
            node = eig.nodes[pid]
            if node.node_type not in self.caps_by_type:
                raise ValueError(
                    f"no caps configured for node_type {node.node_type} "
                    f"(parent {pid!r})"
                )
            delta = counterfactual_delta(
                self.base_guard, eig, target_action_id, pid,
                op=InterventionOp.ABLATION,
                q=self.q,
                precedents=retrieved_capsules,
            )
            per_delta[pid] = delta
            is_attested = node.provenance.is_attested(
                current_scope=self.attestation_ctx.current_scope,
                current_epoch_ms=self.attestation_ctx.current_epoch_ms,
                accepted_policy_versions=self.attestation_ctx.accepted_policy_versions,
            )
            contribs.append(Contribution(
                node_id=pid,
                node_type=node.node_type,
                raw_delta=delta,
                is_attested=is_attested,
                beta=self.beta_fn(pid, node.node_type),
            ))
        timing_ms["evidence_counterfactual_ms"] = (
            time.perf_counter() - evidence_cf_started
        ) * 1000.0

        # Stage 4b: per-precedent counterfactual influence (delta_i, §4.4).
        # Precedent contributions use w_i (retrieval weight) as beta and are
        # type-clipped under NodeType.PRECEDENT.
        per_precedent_delta: dict[str, float] = {}
        precedent_ids: list[str] = []
        precedent_cf_started = time.perf_counter()
        for rp in retrieved:
            if NodeType.PRECEDENT not in self.caps_by_type:
                raise ValueError(
                    "precedent_store is configured but caps_by_type has no "
                    "NodeType.PRECEDENT entry; add per-type caps for precedents."
                )
            cap = rp.capsule
            delta_i = precedent_counterfactual_delta(
                self.base_guard, eig, target_action_id, base_view,
                all_precedents=retrieved_capsules,
                precedent_capsule_id=cap.capsule_id,
                q=self.q,
            )
            per_precedent_delta[cap.capsule_id] = delta_i
            precedent_ids.append(cap.capsule_id)

            is_attested = cap.trust.is_attested(
                current_scope=self.attestation_ctx.current_scope,
                current_epoch_ms=self.attestation_ctx.current_epoch_ms,
                accepted_policy_versions=self.attestation_ctx.accepted_policy_versions,
            )
            label_scale = (
                self.precedent_unsafe_beta_scale
                if cap.audited_label == 1
                else self.precedent_safe_beta_scale
            )
            contribs.append(Contribution(
                node_id=f"precedent:{cap.capsule_id}",
                node_type=NodeType.PRECEDENT,
                raw_delta=delta_i,
                is_attested=is_attested,
                beta=rp.weight * label_scale,
            ))
        timing_ms["precedent_counterfactual_ms"] = (
            time.perf_counter() - precedent_cf_started
        ) * 1000.0

        # Stage 5: TypeClip -> DirectionalTrustClip -> weighted sum -> outer clip
        aggregation_started = time.perf_counter()
        agg = aggregate(contribs, self.caps_by_type, self.eps_neg, self.eps_pos)
        timing_ms["aggregation_ms"] = (
            time.perf_counter() - aggregation_started
        ) * 1000.0

        s_pg = base_score + agg.final_z
        verdict = Verdict.BLOCK if s_pg >= self.threshold else Verdict.ALLOW

        # Split audit-trail dicts by contribution class
        per_parent_type_clipped = {
            nid: v for nid, v in agg.per_node_type_clipped.items()
            if not nid.startswith("precedent:")
        }
        per_parent_pg_clipped = {
            nid: v for nid, v in agg.per_node_pg_clipped.items()
            if not nid.startswith("precedent:")
        }
        per_precedent_pg_clipped = {
            nid: v for nid, v in agg.per_node_pg_clipped.items()
            if nid.startswith("precedent:")
        }
        timing_ms["total_ms"] = (time.perf_counter() - total_started) * 1000.0

        return Decision(
            verdict=verdict,
            s_pg=s_pg,
            base_score=base_score,
            z_before_outer=agg.weighted_sum_before_outer,
            z_after_outer=agg.final_z,
            parent_ids=parent_ids,
            per_parent_delta=per_delta,
            per_parent_type_clipped=per_parent_type_clipped,
            per_parent_pg_clipped=per_parent_pg_clipped,
            precedent_ids=tuple(precedent_ids),
            per_precedent_delta=per_precedent_delta,
            per_precedent_pg_clipped=per_precedent_pg_clipped,
            timing_ms=timing_ms,
            retrieval_diagnostics=retrieval_diagnostics,
        )
