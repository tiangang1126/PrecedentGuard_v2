"""
precedentguard/eig.py

Execution-grounded Intervention Graph (EIG) — data structures and builder.
Aligned with v0.2 main draft Section 3.2 and Assumption A1 (execution-graph fidelity).

Design principles (v0.2 Section 3.2 / Section 1.3):
  1. Edges are added ONLY when runtime instrumentation records that content or
     control state of u was consumed in producing v. This is NOT causal discovery
     from observational text.
  2. The graph is an intervention interface: it tells the defender which nodes
     can be ablated/replaced/replayed/withheld while keeping the rest fixed.
  3. Hidden channels outside instrumentation are out of scope (A1).

Day 2 morning scope: memory, tool, retrieval node types only. Intent, observation,
policy_attestation are needed for a minimal executable EIG. Others (derived_summary,
action) are stubs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from precedentguard.types import (
    EdgeType,
    NodeType,
    Provenance,
    TrustLevel,
)


@dataclass(frozen=True)
class Node:
    """A single node in the EIG.

    Fields
    ------
    node_id : str
        Unique identifier within an EIG instance (e.g., "mem-42", "tool-return-3").
    node_type : NodeType
        Category of the runtime event this node represents.
    content_hash : str
        Deterministic hash of the node's content (used for provenance and
        interventional replay reproducibility). We store hashes rather than
        raw content to keep the EIG compact and privacy-preserving.
    provenance : Provenance
        Trust record; supports the 5-condition attested(e, x) predicate.
    timestamp_ms : int
        Wall-clock time of the event (for temporal ordering and expiry checks).
    payload : Any, optional
        The actual content (kept optional for memory efficiency; extractors may
        drop it after hashing).
    """

    node_id: str
    node_type: NodeType
    content_hash: str
    provenance: Provenance
    timestamp_ms: int
    payload: Optional[Any] = None


@dataclass(frozen=True)
class Edge:
    """A directed edge (source -> target) in the EIG.

    An edge asserts that the runtime observed source's content or control state
    being consumed in producing target. This is an implementation claim, not a
    causal-discovery claim (v0.2 Section 3.2).
    """

    source_id: str
    target_id: str
    edge_type: EdgeType


@dataclass
class EIG:
    """Execution-grounded Intervention Graph.

    Storage is by-id maps + adjacency lists. Not thread-safe; construction is
    assumed to complete before the guard queries the graph.
    """

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    _out_adj: dict[str, list[str]] = field(default_factory=dict)
    _in_adj: dict[str, list[str]] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"duplicate node_id: {node.node_id}")
        self.nodes[node.node_id] = node
        self._out_adj.setdefault(node.node_id, [])
        self._in_adj.setdefault(node.node_id, [])

    def add_edge(self, edge: Edge) -> None:
        if edge.source_id not in self.nodes:
            raise ValueError(f"edge source not in EIG: {edge.source_id}")
        if edge.target_id not in self.nodes:
            raise ValueError(f"edge target not in EIG: {edge.target_id}")
        if edge.source_id == edge.target_id:
            raise ValueError(f"self-loop not permitted: {edge.source_id}")
        self.edges.append(edge)
        self._out_adj[edge.source_id].append(edge.target_id)
        self._in_adj[edge.target_id].append(edge.source_id)

    # ------------------------------------------------------------------
    # Graph queries used by the guard (v0.2 Section 3.2 evidence parents,
    # Section 4.2 evidence-separable base score)
    # ------------------------------------------------------------------

    def parents_of(self, node_id: str) -> list[str]:
        """Direct predecessors (used by SelectInstrumentedParents in Alg. 1)."""
        if node_id not in self.nodes:
            raise KeyError(node_id)
        return list(self._in_adj[node_id])

    def ancestors_of(self, node_id: str) -> set[str]:
        """All predecessors reachable via reverse BFS.

        Used to compute the P_t subset (evidence parent set) for the target action.
        """
        if node_id not in self.nodes:
            raise KeyError(node_id)
        visited: set[str] = set()
        frontier = list(self._in_adj[node_id])
        while frontier:
            nid = frontier.pop()
            if nid in visited:
                continue
            visited.add(nid)
            frontier.extend(self._in_adj[nid])
        return visited

    def mutable_ancestors_of(self, node_id: str) -> set[str]:
        """Ancestors that are attacker-mutable (Threat model, v0.2 Section 3.3).

        This is the set of nodes the defender considers for counterfactual
        replay and per-type clipping.
        """
        return {
            aid
            for aid in self.ancestors_of(node_id)
            if self.nodes[aid].node_type.is_mutable_by_attacker
        }

    def nodes_by_type(self, node_type: NodeType) -> list[str]:
        return [nid for nid, n in self.nodes.items() if n.node_type == node_type]

    def __len__(self) -> int:
        return len(self.nodes)


# ----------------------------------------------------------------------
# Runtime event -> EIG builder (Assumption A1: execution-graph fidelity)
# ----------------------------------------------------------------------


@dataclass
class RuntimeEvent:
    """A single event emitted by instrumented agent runtime.

    Contract (Assumption A1):
      Every mutable evidence item that enters PrecedentGuard evidence aggregation
      is represented by a RuntimeEvent with `node_type in {MEMORY, RETRIEVAL,
      TOOL_RETURN, OBSERVATION}` and a well-formed `consumes` list.
    """

    event_id: str
    node_type: NodeType
    content_hash: str
    provenance: Provenance
    timestamp_ms: int
    consumes: list[str] = field(default_factory=list)  # node_ids this event consumed
    edge_types: list[EdgeType] = field(default_factory=list)  # 1-1 with consumes
    payload: Optional[Any] = None


class EIGBuilder:
    """Build an EIG from a temporally ordered list of RuntimeEvents.

    Usage
    -----
    >>> builder = EIGBuilder()
    >>> for ev in runtime_log:
    ...     builder.ingest(ev)
    >>> eig = builder.finalize()

    Design notes
    ------------
    - Events must be topologically ordered: any node in `consumes` must have been
      ingested before the current event. This is enforced by a check on ingest.
    - The builder validates that `consumes` and `edge_types` have equal length;
      if `edge_types` is empty and `consumes` non-empty, we default to DATAFLOW.
    """

    def __init__(self) -> None:
        self._eig = EIG()

    def ingest(self, event: RuntimeEvent) -> None:
        # Validate consumes/edge_types length
        edge_types = event.edge_types
        if edge_types and len(edge_types) != len(event.consumes):
            raise ValueError(
                f"event {event.event_id}: consumes has {len(event.consumes)} entries "
                f"but edge_types has {len(edge_types)}"
            )
        if not edge_types:
            edge_types = [EdgeType.DATAFLOW] * len(event.consumes)

        # Validate topological order: predecessors must already be in the EIG
        for source_id in event.consumes:
            if source_id not in self._eig.nodes:
                raise ValueError(
                    f"event {event.event_id}: consumes {source_id!r} which was not "
                    f"previously ingested (topological ordering violated; check A1)"
                )

        node = Node(
            node_id=event.event_id,
            node_type=event.node_type,
            content_hash=event.content_hash,
            provenance=event.provenance,
            timestamp_ms=event.timestamp_ms,
            payload=event.payload,
        )
        self._eig.add_node(node)

        for source_id, edge_type in zip(event.consumes, edge_types):
            self._eig.add_edge(Edge(source_id, event.event_id, edge_type))

    def finalize(self) -> EIG:
        return self._eig


def build_eig_from_events(events: Iterable[RuntimeEvent]) -> EIG:
    """Convenience one-shot: ingest all events and return the EIG."""
    builder = EIGBuilder()
    for ev in events:
        builder.ingest(ev)
    return builder.finalize()
