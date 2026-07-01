"""
precedentguard/types.py

Type definitions for the Execution-grounded Intervention Graph (EIG).
Symbols aligned with:
  - PrecedentGuard_AAAI27_Revised_Draft_v0.2.md, Section 3.2
  - precedentguard_theorems_v0.2_skeleton.tex, Assumptions A1-A5

References
----------
Node types: v0.2 main draft Section 3.2 lists "user intent; memory read/write;
retrieval result; tool argument; tool return; derived summary; candidate action;
policy or human attestation."

Trust levels: v0.2 main draft Section 1.2 defines the 3-tier trust hierarchy
(untrusted / authenticated / policy-attested). Aligned with the directional
constraint in Section 4.6 and Assumption A4.

Intervention operators: v0.2 main draft Section 3.2 lists the four supported
operators (ablation, replacement, replay, withholding).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class NodeType(Enum):
    """Types of nodes in the Execution-grounded Intervention Graph.

    Day 2 morning scope per Sprint Dashboard: memory, tool, retrieval.
    Others are declared but not yet used in the minimal EIG extractor.
    """

    INTENT = "intent"                    # user intent (root, not mutable by attacker)
    MEMORY = "memory"                    # memory read (mutable)
    RETRIEVAL = "retrieval"              # retrieval result (mutable)
    TOOL_ARG = "tool_arg"                # argument to a tool call (derived)
    TOOL_RETURN = "tool_return"          # return value from a tool call (mutable)
    OBSERVATION = "observation"          # environmental observation (mutable)
    DERIVED_SUMMARY = "derived_summary"  # LLM-produced intermediate summary
    ACTION = "action"                    # candidate action (target of the guard)
    POLICY_ATTESTATION = "policy_attestation"  # signed attestation from validator

    @property
    def is_mutable_by_attacker(self) -> bool:
        """Whether an adversary with EIG-consistent capabilities can modify this node.

        Ties to the threat model in v0.2 Section 3.3: the attacker may modify
        memory, retrieval, tool returns, and observations; user intent and action
        are conditioned on (see Section 3.3 last paragraph); policy attestations
        require breaking A4.
        """
        return self in {
            NodeType.MEMORY,
            NodeType.RETRIEVAL,
            NodeType.TOOL_RETURN,
            NodeType.OBSERVATION,
        }

    @property
    def contributes_to_pg_score(self) -> bool:
        """Whether this node type enters the PrecedentGuard evidence aggregation.

        Currently only mutable evidence + policy attestations enter aggregation
        (via phi_e in v0.2 Section 4.2). Intent/action are conditioned on and
        appear in the base score B(I, A).
        """
        return self.is_mutable_by_attacker or self == NodeType.POLICY_ATTESTATION


class TrustLevel(Enum):
    """Three-tier trust hierarchy from v0.2 Section 1.2.

    Ordering (low to high):
      UNTRUSTED < AUTHENTICATED < POLICY_ATTESTED
    """

    UNTRUSTED = 0        # origin or integrity is not established
    AUTHENTICATED = 1    # origin and integrity established, but no semantic authorization
    POLICY_ATTESTED = 2  # a designated validator binds a safety label to a scope

    def __lt__(self, other: "TrustLevel") -> bool:
        return self.value < other.value

    def __le__(self, other: "TrustLevel") -> bool:
        return self.value <= other.value


class EdgeType(Enum):
    """Types of edges in the EIG.

    Per v0.2 Section 3.2: an edge is added only when runtime instrumentation
    records that the content or control state of u was consumed in producing v.
    """

    DATAFLOW = "dataflow"      # content of source was read into target
    CONTROL = "control"        # source's control state gated target's creation
    DERIVATION = "derivation"  # target was derived by transformation of source


class InterventionOp(Enum):
    """Runtime-supported intervention operators (v0.2 Section 3.2)."""

    ABLATION = "ablation"          # remove node from assembled context
    REPLACEMENT = "replacement"    # substitute a neutral/matched control value
    REPLAY = "replay"              # rerun downstream with other recorded inputs fixed
    WITHHOLDING = "withholding"    # prevent item from entering next decision context


@dataclass(frozen=True)
class Provenance:
    """Provenance record for a node's trust status (v0.2 Section 3.4: T(e))."""

    origin_id: Optional[str] = None       # p_e: writer identity
    signature_valid: bool = False         # part of p_e
    semantic_authorization: bool = False  # a_e: 0/1 whether an approved validator issued attestation
    scope: Optional[str] = None           # s_e: action/domain scope
    policy_version: Optional[str] = None  # v_e
    expiry_epoch_ms: Optional[int] = None # t_e; None means no expiry

    def is_attested(self, current_scope: Optional[str] = None,
                    current_epoch_ms: Optional[int] = None,
                    accepted_policy_versions: Optional[frozenset[str]] = None) -> bool:
        """Check the five-condition attestation predicate from v0.2 Section 3.4.

        attested(e, x) = 1 iff (i) signature valid, (ii) semantic authorization issued
        by an approved validator, (iii) scope matches, (iv) policy version accepted,
        (v) not expired.
        """
        if not self.signature_valid:
            return False
        if not self.semantic_authorization:
            return False
        if current_scope is not None and self.scope != current_scope:
            return False
        if (accepted_policy_versions is not None
                and self.policy_version not in accepted_policy_versions):
            return False
        if (self.expiry_epoch_ms is not None and current_epoch_ms is not None
                and current_epoch_ms > self.expiry_epoch_ms):
            return False
        return True

    def trust_level(self, **attestation_ctx) -> TrustLevel:
        """Derive the three-tier trust level from the provenance record."""
        if self.is_attested(**attestation_ctx):
            return TrustLevel.POLICY_ATTESTED
        if self.signature_valid:
            return TrustLevel.AUTHENTICATED
        return TrustLevel.UNTRUSTED
