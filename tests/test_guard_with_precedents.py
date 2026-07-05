"""
tests/test_guard_with_precedents.py

Integration tests for PrecedentGuard with SimplePrecedentStore configured
— exercises v0.2 §4.3-§4.6 full pipeline including precedent retrieval,
precedent counterfactual influence, and directional trust on precedents.
"""

from __future__ import annotations

import unittest

from precedentguard import (
    NodeType,
    PrecedentCapsule,
    Provenance,
    RuntimeEvent,
    SimplePrecedentStore,
    build_eig_from_events,
)
from precedentguard.clipping import symmetric_caps
from precedentguard.guard import (
    AttestationContext,
    PrecedentGuard,
    Verdict,
)
from precedentguard.eig import EIG


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def mk_eig() -> EIG:
    events = [
        RuntimeEvent(event_id="intent", node_type=NodeType.INTENT,
                     content_hash="request-transfer-funds",
                     provenance=Provenance(), timestamp_ms=0),
        RuntimeEvent(event_id="mem", node_type=NodeType.MEMORY,
                     content_hash="user-approved-transfer-yesterday",
                     provenance=Provenance(), timestamp_ms=1,
                     consumes=["intent"]),
        RuntimeEvent(event_id="act", node_type=NodeType.ACTION,
                     content_hash="send-transfer-500-usd",
                     provenance=Provenance(), timestamp_ms=2,
                     consumes=["mem"]),
    ]
    return build_eig_from_events(events)


def mk_capsule(cid: str, label: int, summary: str = "prior-transfer-case",
               action: str = "send-transfer-500-usd",
               attested: bool = False) -> PrecedentCapsule:
    prov = Provenance(
        origin_id="validator" if attested else None,
        signature_valid=attested,
        semantic_authorization=attested,
        scope="default" if attested else None,
        policy_version="v1" if attested else None,
    )
    return PrecedentCapsule(
        capsule_id=cid,
        trajectory_summary=summary,
        proposed_action=action,
        audited_label=label,
        trust=prov,
    )


def guard_with_precedent_effect(base: float, mem_effect: float,
                                 precedent_effect_per_item: float):
    """Mock guard: base + mem_effect (if mem present) + N * precedent_effect."""

    def guard(_eig, _target_action_id, view, precedents=None):
        score = base
        if "mem" in view and view["mem"].is_present:
            score += mem_effect
        if precedents:
            score += len(precedents) * precedent_effect_per_item
        return score

    return guard


CAPS = {
    NodeType.MEMORY: symmetric_caps(0.20),
    NodeType.RETRIEVAL: symmetric_caps(0.20),
    NodeType.OBSERVATION: symmetric_caps(0.20),
    NodeType.TOOL_RETURN: symmetric_caps(0.20),
    NodeType.PRECEDENT: symmetric_caps(0.15),
}


# ----------------------------------------------------------------------
# Precedent store integrates through decide()
# ----------------------------------------------------------------------


class TestPrecedentFlowBasic(unittest.TestCase):

    def test_empty_store_returns_no_precedents(self):
        store = SimplePrecedentStore()
        guard = guard_with_precedent_effect(0.0, 0.0, 0.0)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS,
                            threshold=0.5, precedent_store=store)
        decision = pg.decide(mk_eig(), target_action_id="act")
        self.assertEqual(decision.precedent_ids, ())
        self.assertEqual(decision.per_precedent_delta, {})

    def test_none_store_ignores_precedent_flow(self):
        guard = guard_with_precedent_effect(0.0, 0.0, 0.0)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS,
                            threshold=0.5, precedent_store=None)
        decision = pg.decide(mk_eig(), target_action_id="act")
        self.assertEqual(decision.precedent_ids, ())

    def test_retrieval_populates_precedent_ids(self):
        store = SimplePrecedentStore()
        store.add(mk_capsule("c1", label=1, summary="prior-transfer-case"))
        store.add(mk_capsule("c2", label=0, summary="unrelated-order-food"))
        store.add(mk_capsule("c3", label=1, summary="prior-transfer-scam"))

        # Guard reports base 0.3; precedents count contributes +0.02 per item
        guard = guard_with_precedent_effect(0.3, 0.0, 0.02)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS,
                            threshold=0.5, precedent_store=store,
                            precedent_top_k=3)
        decision = pg.decide(mk_eig(), target_action_id="act")

        self.assertEqual(len(decision.precedent_ids), 3)
        # Each precedent's ablation delta should be exactly the per-item effect
        for cid in decision.precedent_ids:
            self.assertAlmostEqual(
                decision.per_precedent_delta[cid], 0.02, places=6
            )

    def test_decision_exposes_timing_and_retrieval_diagnostics(self):
        store = SimplePrecedentStore()
        store.add(mk_capsule("c1", label=1, summary="prior-transfer-case"))

        guard = guard_with_precedent_effect(0.3, 0.0, 0.02)
        pg = PrecedentGuard(
            base_guard=guard,
            caps_by_type=CAPS,
            threshold=0.5,
            precedent_store=store,
            precedent_top_k=1,
        )
        decision = pg.decide(mk_eig(), target_action_id="act")

        self.assertIn("retrieval_ms", decision.timing_ms)
        self.assertIn("base_guard_ms", decision.timing_ms)
        self.assertIn("total_ms", decision.timing_ms)
        self.assertGreaterEqual(decision.timing_ms["total_ms"], 0.0)
        self.assertEqual(decision.retrieval_diagnostics["hit_count"], 1)
        self.assertEqual(decision.retrieval_diagnostics["label_distribution"]["unsafe"], 1)


class TestPrecedentDirectionalTrust(unittest.TestCase):

    def test_unattested_precedent_cannot_lower_score(self):
        """A retrieved precedent with negative delta_i and unattested trust
        must be clipped up to 0 by the directional trust rule."""
        store = SimplePrecedentStore()
        store.add(mk_capsule("c1", label=0, attested=False))

        # Guard: base 0.5; precedents contribute -0.1 per item (i.e., safer
        # when precedent is present). delta_i = mean(with) - mean(without)
        # = (0.5 - 0.1) - 0.5 = -0.1. Untrusted -> clipped up to 0.
        guard = guard_with_precedent_effect(0.5, 0.0, -0.1)
        pg = PrecedentGuard(
            base_guard=guard, caps_by_type=CAPS, threshold=0.5,
            precedent_store=store, precedent_top_k=1,
            attestation_ctx=AttestationContext(
                current_scope="default",
                accepted_policy_versions=frozenset({"v1"}),
            ),
        )
        decision = pg.decide(mk_eig(), target_action_id="act")
        self.assertAlmostEqual(decision.per_precedent_delta["c1"], -0.1)
        # PG-clipped: max(0, clipped_delta) = 0
        self.assertAlmostEqual(
            decision.per_precedent_pg_clipped["precedent:c1"], 0.0
        )

    def test_attested_precedent_negative_survives(self):
        """An attested precedent's negative influence is preserved."""
        store = SimplePrecedentStore()
        store.add(mk_capsule("c1", label=0, attested=True))

        guard = guard_with_precedent_effect(0.5, 0.0, -0.1)
        pg = PrecedentGuard(
            base_guard=guard, caps_by_type=CAPS, threshold=0.5,
            precedent_store=store, precedent_top_k=1,
            attestation_ctx=AttestationContext(
                current_scope="default",
                accepted_policy_versions=frozenset({"v1"}),
            ),
        )
        decision = pg.decide(mk_eig(), target_action_id="act")
        # Type-clip: -0.1 within [-0.15, 0.15] -> -0.1
        # Attested: preserved
        self.assertAlmostEqual(
            decision.per_precedent_pg_clipped["precedent:c1"], -0.1
        )


class TestPrecedentCapsMandatory(unittest.TestCase):

    def test_missing_precedent_caps_raises(self):
        # Remove NodeType.PRECEDENT from caps
        partial_caps = {k: v for k, v in CAPS.items() if k != NodeType.PRECEDENT}
        store = SimplePrecedentStore()
        store.add(mk_capsule("c1", label=1))
        guard = guard_with_precedent_effect(0.3, 0.0, 0.02)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=partial_caps,
                            threshold=0.5, precedent_store=store)
        with self.assertRaises(ValueError):
            pg.decide(mk_eig(), target_action_id="act")


class TestPrecedentSPGIntegration(unittest.TestCase):
    """End-to-end: base + evidence + precedent all flow into S_PG."""

    def test_full_pipeline_score_composition(self):
        store = SimplePrecedentStore()
        store.add(mk_capsule("c1", label=1))
        store.add(mk_capsule("c2", label=1))

        # base=0.4 (with all evidence/precedents present)
        # mem_effect=0.1, precedent_effect_per_item=0.05
        # With 2 precedents present: base_guard = 0.4 + 0.1 + 2*0.05 = 0.6
        # For BASE view (mutable ablated, no precedents in B(I,A)): 0.4
        # delta_mem = 0.6 - 0.5 = 0.1 (ablate mem; precedents stay constant)
        # For precedent ablation of c1: (0.6) - (0.4+0.1+1*0.05) = 0.05
        # After type-clip (mem cap=0.20, precedent cap=0.15): 0.1, 0.05 (no clip)
        # All untrusted -> pg_clip: max(0,·) preserves positive values
        # weighted_sum: 1.0*0.1 + w1*0.05 + w2*0.05  where w1+w2=1 uniformly => 0.5 each
        # => 0.1 + 0.5*0.05 + 0.5*0.05 = 0.1 + 0.05 = 0.15
        # outer_clip within [-1,1]: 0.15
        # base_score = 0.4, S_PG = 0.4 + 0.15 = 0.55
        guard = guard_with_precedent_effect(0.4, 0.1, 0.05)
        pg = PrecedentGuard(base_guard=guard, caps_by_type=CAPS,
                            threshold=0.5, precedent_store=store,
                            precedent_top_k=2)
        decision = pg.decide(mk_eig(), target_action_id="act")

        self.assertAlmostEqual(decision.base_score, 0.4, places=6)
        self.assertAlmostEqual(decision.per_parent_delta["mem"], 0.1, places=6)
        self.assertAlmostEqual(decision.per_precedent_delta["c1"], 0.05,
                               places=6)
        self.assertAlmostEqual(decision.per_precedent_delta["c2"], 0.05,
                               places=6)
        self.assertAlmostEqual(decision.z_after_outer, 0.15, places=6)
        self.assertAlmostEqual(decision.s_pg, 0.55, places=6)
        self.assertEqual(decision.verdict, Verdict.BLOCK)

    def test_base_score_excludes_precedent_context(self):
        store = SimplePrecedentStore()
        store.add(mk_capsule("c1", label=1))
        store.add(mk_capsule("c2", label=0))

        guard = guard_with_precedent_effect(0.4, 0.0, 0.05)
        pg = PrecedentGuard(
            base_guard=guard,
            caps_by_type=CAPS,
            threshold=0.5,
            precedent_store=store,
            precedent_top_k=2,
        )
        decision = pg.decide(mk_eig(), target_action_id="act")

        self.assertAlmostEqual(decision.base_score, 0.4, places=6)
        self.assertAlmostEqual(decision.per_precedent_delta["c1"], 0.05, places=6)
        self.assertAlmostEqual(decision.per_precedent_delta["c2"], 0.05, places=6)

    def test_label_aware_precedent_beta_scales_affect_aggregation(self):
        store = SimplePrecedentStore()
        store.add(mk_capsule("safe-cap", label=0, attested=True))
        store.add(mk_capsule("unsafe-cap", label=1, attested=True))

        guard = guard_with_precedent_effect(0.4, 0.0, 0.05)
        pg = PrecedentGuard(
            base_guard=guard,
            caps_by_type=CAPS,
            threshold=0.5,
            precedent_store=store,
            precedent_top_k=2,
            precedent_safe_beta_scale=2.0,
            precedent_unsafe_beta_scale=0.5,
            attestation_ctx=AttestationContext(
                current_scope="default",
                accepted_policy_versions=frozenset({"v1"}),
            ),
        )
        decision = pg.decide(mk_eig(), target_action_id="act")

        # Each precedent delta is +0.05 and weights are 0.5/0.5.
        # Scaled contribution = 0.5*2.0*0.05 + 0.5*0.5*0.05 = 0.0625
        self.assertAlmostEqual(decision.z_after_outer, 0.0625, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
