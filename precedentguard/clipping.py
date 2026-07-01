"""
precedentguard/clipping.py

Per-type contribution clipping, directional trust constraint, and outer aggregate
clipping — the mechanical layer that supports Theorems 1--2 (v0.2 Sections 5.2--5.3).

The three transformations, applied to each raw counterfactual delta:

  1. Type clip (v0.2 Section 4.5):  delta_e -> clip(delta_e, -c_k^-, +c_k^+)
     where k = type(e).

  2. Directional trust constraint (v0.2 Section 4.6, Thm 1 Step 2):
        if not attested(e): pg_delta_e = max(0, clipped_delta_e)
        else:               pg_delta_e = clipped_delta_e
     This is the mechanism that yields Theorem 1's asymmetric rho_-.

  3. Outer clip (v0.2 Section 4.6 final form): aggregate -> clip to [-eps_-, +eps_+].

Downstream, `compute_rho` returns Theorem 1's rho_+ and rho_-, matching the
values produced by scripts/day1_theorem_numerical_example.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from precedentguard.types import NodeType


# ----------------------------------------------------------------------
# TypeCaps: c_k^-, c_k^+ for each evidence type
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class TypeCaps:
    """Per-type contribution cap (v0.2 Section 4.5).

    Fields
    ------
    c_neg : non-negative bound on downward contribution.
    c_pos : non-negative bound on upward contribution.
    """

    c_neg: float
    c_pos: float

    def __post_init__(self) -> None:
        if self.c_neg < 0:
            raise ValueError(f"c_neg must be >= 0, got {self.c_neg}")
        if self.c_pos < 0:
            raise ValueError(f"c_pos must be >= 0, got {self.c_pos}")

    @property
    def delta_k(self) -> float:
        """Delta_k = c_neg + c_pos, the width of the interval."""
        return self.c_neg + self.c_pos


# Convenience: symmetric caps
def symmetric_caps(c: float) -> TypeCaps:
    return TypeCaps(c_neg=c, c_pos=c)


# ----------------------------------------------------------------------
# Point transformations
# ----------------------------------------------------------------------


def type_clip(delta: float, caps: TypeCaps) -> float:
    """Clip delta to [-c_neg, +c_pos] (v0.2 Section 4.5)."""
    return max(-caps.c_neg, min(caps.c_pos, delta))


def directional_trust_clip(clipped_delta: float, is_attested: bool) -> float:
    """Apply the directional trust constraint (v0.2 Section 4.6).

    Unauthenticated evidence may raise risk but cannot lower it:
        not attested  =>  max(0, clipped_delta)
        attested      =>  clipped_delta (unchanged)

    This is the mechanism that produces the asymmetric rho_- in Theorem 1.
    """
    if is_attested:
        return clipped_delta
    return max(0.0, clipped_delta)


def outer_clip(aggregate: float, eps_neg: float, eps_pos: float) -> float:
    """Clip the aggregated score contribution to [-eps_neg, +eps_pos]."""
    if eps_neg < 0 or eps_pos < 0:
        raise ValueError(f"eps caps must be non-negative; got ({eps_neg}, {eps_pos})")
    return max(-eps_neg, min(eps_pos, aggregate))


# ----------------------------------------------------------------------
# Full aggregation pipeline (v0.2 Section 4.6 final form)
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Contribution:
    """A single raw evidence contribution before clipping."""

    node_id: str
    node_type: NodeType
    raw_delta: float
    is_attested: bool
    beta: float = 1.0     # coefficient beta_e or precedent weight w_i


@dataclass(frozen=True)
class AggregationResult:
    """Detailed breakdown of the aggregation, for auditing and tests."""

    per_node_type_clipped: dict[str, float]
    per_node_pg_clipped: dict[str, float]
    weighted_sum_before_outer: float
    final_z: float


def aggregate(
    contributions: list[Contribution],
    caps_by_type: Mapping[NodeType, TypeCaps],
    eps_neg: float,
    eps_pos: float,
) -> AggregationResult:
    """Full PrecedentGuard aggregation from raw deltas to final z.

    Implements the pipeline in Algorithm 1 (v0.2 Section 4.8) lines 7-18:
      delta -> TypeClip -> DirectionalTrustClip -> weighted sum -> outer clip.
    """
    per_type: dict[str, float] = {}
    per_pg: dict[str, float] = {}
    total = 0.0
    for c in contributions:
        if c.node_type not in caps_by_type:
            raise ValueError(f"no caps configured for node_type {c.node_type}")
        caps = caps_by_type[c.node_type]
        clipped = type_clip(c.raw_delta, caps)
        pg = directional_trust_clip(clipped, c.is_attested)
        per_type[c.node_id] = clipped
        per_pg[c.node_id] = pg
        total += c.beta * pg
    final_z = outer_clip(total, eps_neg, eps_pos)
    return AggregationResult(
        per_node_type_clipped=per_type,
        per_node_pg_clipped=per_pg,
        weighted_sum_before_outer=total,
        final_z=final_z,
    )


# ----------------------------------------------------------------------
# Theorem 1 rho_+, rho_- computation (aligned with day1 numerical example)
# ----------------------------------------------------------------------


def compute_rho(
    m: Mapping[NodeType, int],
    m_ins_unattested: Mapping[NodeType, int],
    caps_by_type: Mapping[NodeType, TypeCaps],
    eps_neg: float,
    eps_pos: float,
) -> tuple[float, float]:
    """Compute (rho_plus, rho_minus) per Theorem 1 (v0.2 Section 5.2).

    rho_+(m) = min(eps_+, sum_k m_k * Delta_k)
    rho_-(m) = min(eps_-, sum_k (m_k - m_k^{ins,unattested}) * Delta_k)

    An unauthenticated-insertion sub-budget m_k^{ins,unattested} contributes zero
    to the downward shift by the directional trust rule (Step 2 of Thm 1 proof).
    """
    # Validate budgets
    for nt in m:
        if m[nt] < 0:
            raise ValueError(f"m[{nt}] must be >= 0, got {m[nt]}")
        m_ins = m_ins_unattested.get(nt, 0)
        if m_ins < 0:
            raise ValueError(f"m_ins_unattested[{nt}] must be >= 0, got {m_ins}")
        if m_ins > m[nt]:
            raise ValueError(
                f"m_ins_unattested[{nt}]={m_ins} exceeds m[{nt}]={m[nt]}"
            )

    r_plus = 0.0
    r_minus = 0.0
    for nt, budget in m.items():
        if nt not in caps_by_type:
            raise ValueError(f"no caps configured for node_type {nt}")
        delta_k = caps_by_type[nt].delta_k
        r_plus += budget * delta_k
        r_minus += (budget - m_ins_unattested.get(nt, 0)) * delta_k

    rho_plus = min(eps_pos, r_plus)
    rho_minus = min(eps_neg, r_minus)
    return rho_plus, rho_minus
