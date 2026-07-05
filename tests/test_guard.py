"""
tests/test_guard.py

Integration tests for Algorithm 1 via PrecedentGuard.decide().

Coverage:
  - Verdict logic (BLOCK vs ALLOW around threshold)
  - Base score = guard(mutable-ablated context)
  - Aggregation matches per-parent counterfactual deltas
  - Directional trust: unattested parents cannot lower s_pg
  - Missing caps for a node_type raises
  - Audit trail fields are populated
"""

from __future__ import annotations

import unittest

from precedentguard import (
    NodeType,
    Provenance,
    RuntimeEvent,
    build_eig_from_events,
)
from precedentguard.clipping import TypeCaps, symmetric_caps
from precedentguard.counterfactual import EffectiveNode
from precedentguard.guard import (
    AttestationContext,
    Decision,
    PrecedentGuard,
    Verdict,
)
from precedentguard.eig import EIG


# ----------------------------------------------------------------------
# Fixtures: a simple 4-node EIG plus a deterministic mock guard
# ----------------------------------------------------------------------


def mk_prov(*, signed: bool = False, attested: bool = False,
            scope: str = "default", policy_ver: str = "v1") -> Provenance:
    return Provenance(
        origin_id="w" if signed else None,
        signature_valid=signed,
        semantic_authorization=attested,
        scope=scope if signed else None,
        policy_version=policy_ver if signed else None,
    )


def mk_eig(mem_attested: bool = False, retr_attested: bool = False) -> EIG:
    events = [
        RuntimeEvent(event_id="intent", node_type=NodeType.INTENT,
                     content_hash="I", provenance=mk_prov(), timestamp_ms=0),
        RuntimeEvent(event_id="retr", node_type=NodeType.RETRIEVAL,
                     content_hash="R", provenance=mk_prov(signed=True, attested=retr_attested),
                     timestamp_ms=1, consumes=["intent"]),
        RuntimeEvent(event_id="mem", node_type=NodeType.MEMORY,
                     content_hash="M", provenance=mk_prov(signed=True, attested=mem_attested),
                     timestamp_ms=2, consumes=["intent", "retr"]),
        RuntimeEvent(event_id="act", node_type=NodeType.ACTION,
                     content_hash="A", provenance=mk_prov(), timestamp_ms=3,
                     consumes=["mem"]),
    ]
    return build_eig_from_events(events)


def constant_guard_factory(base: float, mem_effect: float, retr_effect: float):
    """Guard that returns `base + mem_effect + retr_effect` where each effect
    is added only if the corresponding node is present in the view."""

    def guard(eig: EIG, target_action_id: str,
              view: dict[str, EffectiveNode],
              precedents=None) -> float:
        score = base
        if "mem" in view and view["mem"].is_present:
            score += mem_effect
        if "retr" in view and view["retr"].is_present:
            score += retr_effect
        return score

    return guard


CAPS_ALL = {
    NodeType.MEMORY: symmetric_caps(0.3),
    NodeType.RETRIEVAL: symmetric_caps(0.3),
    NodeType.TOOL_RETURN: symmetric_caps(0.3),
    NodeType.OBSERVATION: symmetric_caps(0.3),
}


# ----------------------------------------------------------------------
# Basic pipeline
# ----------------------------------------------------------------------


class TestDecidePipeline(unittest.TestCase):

    def test_allow_below_threshold(self):
        # Base 0, mem contributes +0.1, retr +0.1; s_pg = 0.2 < 0.5
        guard = constant_guard_factory(base=0.0, mem_effect=0.1, retr_effect=0.1)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS_ALL, threshold=0.5)
        decision = pg.decide(mk_eig(), target_action_id="act")
        self.assertEqual(decision.verdict, Verdict.ALLOW)
        self.assertAlmostEqual(decision.s_pg, 0.2, places=6)
        # Base score: mutable ablated -> only base=0.0 remains
        self.assertAlmostEqual(decision.base_score, 0.0, places=6)

    def test_block_above_threshold(self):
        # Base 0.4, mem +0.2, retr +0.2; s_pg = 0.4 + 0.4 = 0.8 >= 0.5
        guard = constant_guard_factory(base=0.4, mem_effect=0.2, retr_effect=0.2)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS_ALL, threshold=0.5)
        decision = pg.decide(mk_eig(), target_action_id="act")
        self.assertEqual(decision.verdict, Verdict.BLOCK)
        self.assertAlmostEqual(decision.s_pg, 0.8, places=6)

    def test_parent_ids_sorted_mutable_ancestors(self):
        guard = constant_guard_factory(base=0.0, mem_effect=0.1, retr_effect=0.1)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS_ALL, threshold=0.5)
        decision = pg.decide(mk_eig(), target_action_id="act")
        # intent is not mutable; mem and retr are; sorted alphabetically
        self.assertEqual(decision.parent_ids, ("mem", "retr"))

    def test_audit_trail_populated(self):
        guard = constant_guard_factory(base=0.0, mem_effect=0.1, retr_effect=0.1)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS_ALL, threshold=0.5)
        decision = pg.decide(mk_eig(), target_action_id="act")
        self.assertIn("mem", decision.per_parent_delta)
        self.assertIn("retr", decision.per_parent_delta)
        # Per-parent delta: ablation of mem removes 0.1 from the score, so delta_mem = 0.1
        self.assertAlmostEqual(decision.per_parent_delta["mem"], 0.1, places=6)
        self.assertAlmostEqual(decision.per_parent_delta["retr"], 0.1, places=6)


# ----------------------------------------------------------------------
# Directional trust: unattested parents cannot lower s_pg
# ----------------------------------------------------------------------


class TestDirectionalTrust(unittest.TestCase):

    def test_unattested_negative_becomes_zero(self):
        # Guard: base 0.5, mem effect -0.2 (present) => delta_mem = -0.2
        # If mem is UNATTESTED, PG-clip pushes it to max(0, -0.2) = 0
        # s_pg = base_score_mutable_ablated (0.5) + 0 (mem contribution zeroed)
        #      = 0.5
        guard = constant_guard_factory(base=0.5, mem_effect=-0.2, retr_effect=0.0)
        eig = mk_eig(mem_attested=False)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS_ALL, threshold=0.5,
                            attestation_ctx=AttestationContext(current_scope="default",
                                accepted_policy_versions=frozenset({"v1"})))
        decision = pg.decide(eig, target_action_id="act")
        self.assertAlmostEqual(decision.per_parent_delta["mem"], -0.2, places=6)
        # Directional trust must zero out the negative
        self.assertAlmostEqual(decision.per_parent_pg_clipped["mem"], 0.0, places=6)

    def test_attested_negative_survives(self):
        # Same guard but mem is now POLICY_ATTESTED — negative delta preserved
        guard = constant_guard_factory(base=0.5, mem_effect=-0.2, retr_effect=0.0)
        eig = mk_eig(mem_attested=True)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS_ALL, threshold=0.5,
                            attestation_ctx=AttestationContext(current_scope="default",
                                accepted_policy_versions=frozenset({"v1"})))
        decision = pg.decide(eig, target_action_id="act")
        self.assertAlmostEqual(decision.per_parent_delta["mem"], -0.2, places=6)
        # Attested: negative preserved (after type_clip which is -0.2 within [-0.3, 0.3])
        self.assertAlmostEqual(decision.per_parent_pg_clipped["mem"], -0.2, places=6)


# ----------------------------------------------------------------------
# Error paths
# ----------------------------------------------------------------------


class TestGuardErrors(unittest.TestCase):

    def test_missing_action_raises(self):
        guard = constant_guard_factory(base=0.0, mem_effect=0.0, retr_effect=0.0)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS_ALL)
        with self.assertRaises(ValueError):
            pg.decide(mk_eig(), target_action_id="not-in-eig")

    def test_missing_caps_for_type_raises(self):
        # Remove RETRIEVAL from caps; the guard should raise when it hits retr
        guard = constant_guard_factory(base=0.0, mem_effect=0.1, retr_effect=0.1)
        partial_caps = {NodeType.MEMORY: symmetric_caps(0.3)}
        pg = PrecedentGuard(base_guard=guard, caps_by_type=partial_caps)
        with self.assertRaises(ValueError):
            pg.decide(mk_eig(), target_action_id="act")


if __name__ == "__main__":
    unittest.main(verbosity=2)
