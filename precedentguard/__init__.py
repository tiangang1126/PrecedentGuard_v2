"""PrecedentGuard: double-sided runtime certification for LLM agent guards.

Package entry point. See `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md` for the
paper draft, and `precedentguard_theorems_v0.2_skeleton.tex` for the proof
skeleton this implementation is built to satisfy.
"""

from precedentguard.types import (
    EdgeType,
    InterventionOp,
    NodeType,
    Provenance,
    TrustLevel,
)
from precedentguard.eig import (
    EIG,
    Edge,
    EIGBuilder,
    Node,
    RuntimeEvent,
    build_eig_from_events,
)

__version__ = "0.2.0-day2"

__all__ = [
    "EIG",
    "Edge",
    "EIGBuilder",
    "EdgeType",
    "InterventionOp",
    "Node",
    "NodeType",
    "Provenance",
    "RuntimeEvent",
    "TrustLevel",
    "build_eig_from_events",
]
