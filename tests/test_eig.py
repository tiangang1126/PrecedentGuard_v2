"""
tests/test_eig.py

Unit tests for the EIG data structures and builder.
Covers:
  - Node and edge construction validity checks
  - Topological ordering enforcement (Assumption A1)
  - Parents / ancestors / mutable_ancestors_of queries
  - TrustLevel derivation from Provenance (5-condition attested predicate)
  - NodeType.is_mutable_by_attacker semantics

Run:
    python -m pytest tests/test_eig.py -v
    OR:
    python -m unittest tests.test_eig -v
"""

from __future__ import annotations

import unittest

from precedentguard import (
    EIG,
    Edge,
    EIGBuilder,
    EdgeType,
    Node,
    NodeType,
    Provenance,
    RuntimeEvent,
    TrustLevel,
    build_eig_from_events,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def mk_prov(*, signed: bool = False, attested: bool = False,
            scope: str = "default", policy_ver: str = "v1",
            expiry: int | None = None) -> Provenance:
    return Provenance(
        origin_id="test-writer" if signed else None,
        signature_valid=signed,
        semantic_authorization=attested,
        scope=scope if signed else None,
        policy_version=policy_ver if signed else None,
        expiry_epoch_ms=expiry,
    )


def mk_event(event_id: str, ntype: NodeType, ts: int,
             consumes: list[str] | None = None,
             prov: Provenance | None = None) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=event_id,
        node_type=ntype,
        content_hash=f"h-{event_id}",
        provenance=prov if prov is not None else mk_prov(),
        timestamp_ms=ts,
        consumes=consumes or [],
    )


# ----------------------------------------------------------------------
# NodeType.is_mutable_by_attacker
# ----------------------------------------------------------------------


class TestNodeTypeMutability(unittest.TestCase):
    def test_mutable_types(self):
        for nt in [NodeType.MEMORY, NodeType.RETRIEVAL,
                   NodeType.TOOL_RETURN, NodeType.OBSERVATION]:
            self.assertTrue(nt.is_mutable_by_attacker, f"{nt} should be mutable")

    def test_immutable_types(self):
        for nt in [NodeType.INTENT, NodeType.ACTION,
                   NodeType.POLICY_ATTESTATION, NodeType.TOOL_ARG,
                   NodeType.DERIVED_SUMMARY]:
            self.assertFalse(nt.is_mutable_by_attacker, f"{nt} should not be mutable")

    def test_score_contribution(self):
        # Mutable evidence + policy attestations enter the PG score aggregation
        self.assertTrue(NodeType.MEMORY.contributes_to_pg_score)
        self.assertTrue(NodeType.POLICY_ATTESTATION.contributes_to_pg_score)
        # Intent and action are in the base score B(I,A), not the aggregation
        self.assertFalse(NodeType.INTENT.contributes_to_pg_score)
        self.assertFalse(NodeType.ACTION.contributes_to_pg_score)


# ----------------------------------------------------------------------
# Provenance and TrustLevel (v0.2 Sec 3.4 five-condition attestation)
# ----------------------------------------------------------------------


class TestProvenanceAttestation(unittest.TestCase):
    def test_untrusted_by_default(self):
        p = mk_prov(signed=False, attested=False)
        self.assertEqual(p.trust_level(), TrustLevel.UNTRUSTED)
        self.assertFalse(p.is_attested())

    def test_authenticated_only(self):
        p = mk_prov(signed=True, attested=False)
        self.assertEqual(p.trust_level(), TrustLevel.AUTHENTICATED)
        self.assertFalse(p.is_attested())

    def test_policy_attested_full(self):
        p = mk_prov(signed=True, attested=True, scope="default", policy_ver="v1")
        self.assertEqual(p.trust_level(), TrustLevel.POLICY_ATTESTED)
        self.assertTrue(p.is_attested())

    def test_scope_mismatch_denies_attestation(self):
        p = mk_prov(signed=True, attested=True, scope="scope-A")
        # Attested predicate must match declared scope
        self.assertTrue(p.is_attested(current_scope="scope-A"))
        self.assertFalse(p.is_attested(current_scope="scope-B"))

    def test_policy_version_denial(self):
        p = mk_prov(signed=True, attested=True, scope="default", policy_ver="v1")
        self.assertFalse(
            p.is_attested(accepted_policy_versions=frozenset({"v2", "v3"}))
        )
        self.assertTrue(
            p.is_attested(accepted_policy_versions=frozenset({"v1"}))
        )

    def test_expiry(self):
        p = Provenance(
            origin_id="test",
            signature_valid=True,
            semantic_authorization=True,
            scope="default",
            policy_version="v1",
            expiry_epoch_ms=1_000,
        )
        self.assertTrue(p.is_attested(current_epoch_ms=500))
        self.assertFalse(p.is_attested(current_epoch_ms=2_000))

    def test_trust_level_ordering(self):
        self.assertLess(TrustLevel.UNTRUSTED, TrustLevel.AUTHENTICATED)
        self.assertLess(TrustLevel.AUTHENTICATED, TrustLevel.POLICY_ATTESTED)


# ----------------------------------------------------------------------
# EIG construction, validation, and graph queries
# ----------------------------------------------------------------------


class TestEIGConstruction(unittest.TestCase):

    def test_add_node_and_edge_basic(self):
        eig = EIG()
        n1 = Node("n1", NodeType.INTENT, "h1", mk_prov(), 0)
        n2 = Node("n2", NodeType.MEMORY, "h2", mk_prov(), 1)
        eig.add_node(n1)
        eig.add_node(n2)
        eig.add_edge(Edge("n1", "n2", EdgeType.DATAFLOW))
        self.assertEqual(len(eig), 2)
        self.assertEqual(eig.parents_of("n2"), ["n1"])
        self.assertEqual(eig.parents_of("n1"), [])

    def test_duplicate_node_id_rejected(self):
        eig = EIG()
        eig.add_node(Node("n1", NodeType.INTENT, "h", mk_prov(), 0))
        with self.assertRaises(ValueError):
            eig.add_node(Node("n1", NodeType.MEMORY, "h2", mk_prov(), 1))

    def test_edge_to_unknown_node_rejected(self):
        eig = EIG()
        eig.add_node(Node("n1", NodeType.INTENT, "h", mk_prov(), 0))
        with self.assertRaises(ValueError):
            eig.add_edge(Edge("n1", "n2-missing", EdgeType.DATAFLOW))

    def test_self_loop_rejected(self):
        eig = EIG()
        eig.add_node(Node("n1", NodeType.INTENT, "h", mk_prov(), 0))
        with self.assertRaises(ValueError):
            eig.add_edge(Edge("n1", "n1", EdgeType.DATAFLOW))


class TestEIGQueries(unittest.TestCase):
    """A small four-node graph:

        intent -> memory -> action
                    ^
        retrieval --+
    """

    def _make(self) -> EIG:
        events = [
            mk_event("intent", NodeType.INTENT, ts=0),
            mk_event("retr", NodeType.RETRIEVAL, ts=1, consumes=["intent"]),
            mk_event("mem", NodeType.MEMORY, ts=2, consumes=["intent", "retr"]),
            mk_event("act", NodeType.ACTION, ts=3, consumes=["mem"]),
        ]
        return build_eig_from_events(events)

    def test_parents(self):
        eig = self._make()
        self.assertEqual(set(eig.parents_of("mem")), {"intent", "retr"})
        self.assertEqual(set(eig.parents_of("act")), {"mem"})
        self.assertEqual(eig.parents_of("intent"), [])

    def test_ancestors(self):
        eig = self._make()
        self.assertEqual(eig.ancestors_of("act"), {"intent", "retr", "mem"})
        self.assertEqual(eig.ancestors_of("mem"), {"intent", "retr"})
        self.assertEqual(eig.ancestors_of("intent"), set())

    def test_mutable_ancestors(self):
        eig = self._make()
        # Only MEMORY and RETRIEVAL are mutable-by-attacker in this graph
        self.assertEqual(eig.mutable_ancestors_of("act"), {"retr", "mem"})
        # Intent is not mutable
        self.assertNotIn("intent", eig.mutable_ancestors_of("act"))

    def test_nodes_by_type(self):
        eig = self._make()
        self.assertEqual(eig.nodes_by_type(NodeType.MEMORY), ["mem"])
        self.assertEqual(eig.nodes_by_type(NodeType.RETRIEVAL), ["retr"])
        self.assertEqual(eig.nodes_by_type(NodeType.TOOL_RETURN), [])


# ----------------------------------------------------------------------
# EIGBuilder topological ordering (Assumption A1)
# ----------------------------------------------------------------------


class TestEIGBuilderOrdering(unittest.TestCase):

    def test_out_of_order_consumes_rejected(self):
        """A5-adjacent: reject an event that consumes an unseen predecessor."""
        builder = EIGBuilder()
        with self.assertRaises(ValueError):
            builder.ingest(mk_event("mem", NodeType.MEMORY, ts=0,
                                    consumes=["intent-not-yet-seen"]))

    def test_edge_type_length_mismatch_rejected(self):
        builder = EIGBuilder()
        builder.ingest(mk_event("intent", NodeType.INTENT, ts=0))
        builder.ingest(mk_event("retr", NodeType.RETRIEVAL, ts=1, consumes=["intent"]))
        bad = RuntimeEvent(
            event_id="mem",
            node_type=NodeType.MEMORY,
            content_hash="h",
            provenance=mk_prov(),
            timestamp_ms=2,
            consumes=["intent", "retr"],
            edge_types=[EdgeType.DATAFLOW],  # length 1 != 2 consumes
        )
        with self.assertRaises(ValueError):
            builder.ingest(bad)

    def test_default_edge_type_dataflow(self):
        events = [
            mk_event("intent", NodeType.INTENT, ts=0),
            mk_event("mem", NodeType.MEMORY, ts=1, consumes=["intent"]),
        ]
        eig = build_eig_from_events(events)
        self.assertEqual(len(eig.edges), 1)
        self.assertEqual(eig.edges[0].edge_type, EdgeType.DATAFLOW)


if __name__ == "__main__":
    unittest.main(verbosity=2)
