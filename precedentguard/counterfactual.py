"""
precedentguard/counterfactual.py

Counterfactual replay interface — the executable-intervention layer that
supports the interventional influence estimator in v0.2 Section 4.4.

Terminology note (v0.2 Section 4.4, matching AI cold-read audit):
  The score difference delta_e = g(I, A, e) - g(I, A, e_ctrl) is an
  *interventional influence under the implemented replay operator*, NOT a
  population causal effect. Correctness rests on Assumption A1 (execution-graph
  fidelity): every mutable channel the attacker can touch is instrumented as a
  Node in the EIG, so the four operators below cover the attack surface.

Design choices
--------------
- Interventions are represented as **immutable** `Intervention` records that a
  `GuardInterface` interprets when reading the EIG. This avoids deep-cloning
  the EIG on every counterfactual and keeps the tests deterministic.
- The `GuardInterface` protocol is a callable that returns a scalar risk score.
  Real guards will bind to a frozen LLM backbone; unit tests use deterministic
  mocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Protocol

from precedentguard.eig import EIG, Node
from precedentguard.types import InterventionOp


# ----------------------------------------------------------------------
# Intervention records
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class NodeIntervention:
    """A single intervention on one node.

    For ABLATION and WITHHOLDING, `control_content_hash` and `control_payload`
    are ignored (the node is absent from the effective context).
    For REPLACEMENT, both control fields describe the substituted value.
    For REPLAY, the intervention rebuilds downstream and its semantics depend
    on the guard implementation.
    """

    node_id: str
    op: InterventionOp
    control_content_hash: Optional[str] = None
    control_payload: Optional[Any] = None


@dataclass(frozen=True)
class Intervention:
    """A set of node-level interventions applied jointly."""

    node_interventions: tuple[NodeIntervention, ...] = ()

    @classmethod
    def empty(cls) -> "Intervention":
        return cls(node_interventions=())

    @classmethod
    def ablate(cls, node_ids: Iterable[str]) -> "Intervention":
        return cls(tuple(
            NodeIntervention(nid, InterventionOp.ABLATION) for nid in node_ids
        ))

    @classmethod
    def replace(cls, node_id: str, control_content_hash: str,
                control_payload: Any = None) -> "Intervention":
        return cls((
            NodeIntervention(node_id, InterventionOp.REPLACEMENT,
                             control_content_hash, control_payload),
        ))

    def ablated_ids(self) -> set[str]:
        return {
            ni.node_id for ni in self.node_interventions
            if ni.op in (InterventionOp.ABLATION, InterventionOp.WITHHOLDING)
        }

    def replaced_map(self) -> dict[str, NodeIntervention]:
        return {
            ni.node_id: ni for ni in self.node_interventions
            if ni.op == InterventionOp.REPLACEMENT
        }

    def touches(self) -> set[str]:
        return {ni.node_id for ni in self.node_interventions}


# ----------------------------------------------------------------------
# Effective node view (what the guard "sees" after an intervention)
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class EffectiveNode:
    """A read-only view of a node under an intervention.

    - `is_present=False` means the node has been ablated / withheld.
    - `content_hash` reflects any replacement (or the clean value).
    - `payload` reflects the replacement payload where applicable.
    """

    node_id: str
    is_present: bool
    node: Node                          # the original Node (immutable)
    content_hash: str                   # possibly overridden
    payload: Optional[Any]              # possibly overridden


def resolve_view(eig: EIG, intervention: Intervention) -> dict[str, EffectiveNode]:
    """Compute the guard-visible view of every node in the EIG under the intervention."""
    ablated = intervention.ablated_ids()
    replaced = intervention.replaced_map()
    view: dict[str, EffectiveNode] = {}
    for node_id, node in eig.nodes.items():
        if node_id in ablated:
            view[node_id] = EffectiveNode(
                node_id=node_id, is_present=False, node=node,
                content_hash=node.content_hash, payload=node.payload,
            )
        elif node_id in replaced:
            ni = replaced[node_id]
            view[node_id] = EffectiveNode(
                node_id=node_id, is_present=True, node=node,
                content_hash=ni.control_content_hash or node.content_hash,
                payload=ni.control_payload,
            )
        else:
            view[node_id] = EffectiveNode(
                node_id=node_id, is_present=True, node=node,
                content_hash=node.content_hash, payload=node.payload,
            )
    return view


# ----------------------------------------------------------------------
# Guard interface protocol
# ----------------------------------------------------------------------


class GuardInterface(Protocol):
    """Callable protocol for a runtime guard.

    Implementations bind to a frozen LLM backbone (v0.2 Section 4.1) and score
    the risk of the target action given the intent and the intervened context.

    Contract
    --------
    - Deterministic (same inputs -> same output), OR
    - Stochastic with an explicit seed argument that callers may fix.
    """

    def __call__(
        self,
        eig: EIG,
        target_action_id: str,
        view: dict[str, EffectiveNode],
    ) -> float:
        ...


# ----------------------------------------------------------------------
# Counterfactual influence estimator
# ----------------------------------------------------------------------


DEFAULT_CTRL_HASH = "CTRL-NEUTRAL"


def counterfactual_delta(
    guard: GuardInterface,
    eig: EIG,
    target_action_id: str,
    node_id: str,
    *,
    op: InterventionOp = InterventionOp.ABLATION,
    control_content_hash: str = DEFAULT_CTRL_HASH,
    control_payload: Any = None,
    q: int = 1,
) -> float:
    """Compute the interventional influence delta_e of a single node.

    delta_e = mean_{q}(g(I, A, e)) - mean_{q}(g(I, A, e_ctrl))

    Parameters
    ----------
    guard : GuardInterface
        Scoring function.
    eig : EIG
        The clean execution graph.
    target_action_id : str
        Node id of the target action (the guard's decision subject).
    node_id : str
        The evidence node whose influence we estimate.
    op : InterventionOp
        Either ABLATION or REPLACEMENT. Others are not supported here yet.
    control_content_hash, control_payload
        Neutral control value used when op == REPLACEMENT.
    q : int
        Number of repeated evaluations for variance reduction (v0.2 Section 4.4).

    Returns
    -------
    float : the estimated interventional influence.

    Raises
    ------
    ValueError
        If `node_id` is not in the EIG or `op` is not supported.
    """
    if node_id not in eig.nodes:
        raise ValueError(f"node_id {node_id!r} not in EIG")
    if op not in (InterventionOp.ABLATION, InterventionOp.REPLACEMENT):
        raise ValueError(
            f"counterfactual_delta supports ABLATION or REPLACEMENT; got {op}"
        )
    if q < 1:
        raise ValueError(f"q must be >= 1, got {q}")

    # Clean and intervened interventions
    clean = Intervention.empty()
    if op == InterventionOp.ABLATION:
        cf = Intervention.ablate([node_id])
    else:  # REPLACEMENT
        cf = Intervention.replace(node_id, control_content_hash, control_payload)

    clean_view = resolve_view(eig, clean)
    cf_view = resolve_view(eig, cf)

    clean_scores = [guard(eig, target_action_id, clean_view) for _ in range(q)]
    cf_scores = [guard(eig, target_action_id, cf_view) for _ in range(q)]
    return (sum(clean_scores) / q) - (sum(cf_scores) / q)


def counterfactual_deltas_for_ancestors(
    guard: GuardInterface,
    eig: EIG,
    target_action_id: str,
    *,
    mutable_only: bool = True,
    op: InterventionOp = InterventionOp.ABLATION,
    q: int = 1,
) -> dict[str, float]:
    """Estimate delta_e for every mutable ancestor of the target action.

    This is the batched form used by Alg. 1 (v0.2 Section 4.8), lines 6-11:
    iterate over instrumented evidence parents and evaluate their influence.
    """
    if mutable_only:
        candidates = eig.mutable_ancestors_of(target_action_id)
    else:
        candidates = eig.ancestors_of(target_action_id)
    return {
        nid: counterfactual_delta(
            guard, eig, target_action_id, nid, op=op, q=q
        )
        for nid in sorted(candidates)  # sorted for deterministic iteration order
    }
