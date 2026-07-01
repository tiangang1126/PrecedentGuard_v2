"""
precedentguard/guard.py

PrecedentGuard runtime decision layer — implements Algorithm 1 (v0.2 Section 4.8).

Five-stage pipeline:
  1. Build/receive EIG from trusted runtime instrumentation (A1).
  2. Select decision-relevant evidence parents (mutable ancestors of target action).
  3. [Deferred to Day 4-5] Retrieve precedent capsules — Day 3 uses empty set.
  4. Estimate bounded counterfactual contributions (delta_e per parent).
  5. Aggregate under directional trust constraints + calibrated threshold.

Precedent retrieval (v0.2 Section 4.3) is deferred to a later iteration; the
current implementation focuses on the current-trajectory evidence pipeline, which
is sufficient for the Day 3 end-to-end smoke test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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
    resolve_view,
)
from precedentguard.eig import EIG
from precedentguard.types import InterventionOp, NodeType


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
        Per-type contribution caps c_k^-, c_k^+.
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
    """

    base_guard: GuardInterface
    caps_by_type: Mapping[NodeType, TypeCaps]
    eps_neg: float = 1.0
    eps_pos: float = 1.0
    threshold: float = 0.5
    q: int = 1
    beta_fn: BetaFn = field(default=_uniform_beta)
    attestation_ctx: AttestationContext = field(default_factory=AttestationContext)

    def _base_view(self, eig: EIG) -> dict[str, EffectiveNode]:
        """Minimal context for base score B(I, A): ablate all mutable evidence."""
        mutable_ids = [
            nid for nid, n in eig.nodes.items() if n.node_type.is_mutable_by_attacker
        ]
        return resolve_view(eig, Intervention.ablate(mutable_ids))

    def decide(
        self,
        eig: EIG,
        target_action_id: str,
    ) -> Decision:
        """Return the runtime decision for the target action given the EIG."""
        if target_action_id not in eig.nodes:
            raise ValueError(f"target action {target_action_id!r} not in EIG")

        # Stage 1: parent selection (mutable ancestors of the target action)
        parent_ids = tuple(sorted(eig.mutable_ancestors_of(target_action_id)))

        # Stage 2: base score B(I, A) on the mutable-ablated context
        base_view = self._base_view(eig)
        base_score = float(self.base_guard(eig, target_action_id, base_view))

        # Stage 3: per-parent counterfactual influence
        per_delta: dict[str, float] = {}
        contribs: list[Contribution] = []
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

        # Stage 4-5: TypeClip -> DirectionalTrustClip -> weighted sum -> outer clip
        agg = aggregate(contribs, self.caps_by_type, self.eps_neg, self.eps_pos)

        s_pg = base_score + agg.final_z
        verdict = Verdict.BLOCK if s_pg >= self.threshold else Verdict.ALLOW

        return Decision(
            verdict=verdict,
            s_pg=s_pg,
            base_score=base_score,
            z_before_outer=agg.weighted_sum_before_outer,
            z_after_outer=agg.final_z,
            parent_ids=parent_ids,
            per_parent_delta=per_delta,
            per_parent_type_clipped=agg.per_node_type_clipped,
            per_parent_pg_clipped=agg.per_node_pg_clipped,
        )
