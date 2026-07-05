"""
tests/test_counterfactual.py

Unit tests for the counterfactual replay interface.

Coverage:
  - Intervention constructors (empty, ablate, replace)
  - resolve_view produces correct EffectiveNode records under each op
  - counterfactual_delta over ABLATION and REPLACEMENT
  - counterfactual_deltas_for_ancestors iterates over mutable ancestors only
  - q > 1 averages correctly (deterministic guard)
"""

from __future__ import annotations

import unittest

from precedentguard import (
    EIG,
    InterventionOp,
    NodeType,
    Provenance,
    RuntimeEvent,
    build_eig_from_events,
)
from precedentguard.counterfactual import (
    DEFAULT_CTRL_HASH,
    EffectiveNode,
    Intervention,
    NodeIntervention,
    counterfactual_delta,
    counterfactual_deltas_for_ancestors,
    resolve_view,
)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def mk_eig() -> EIG:
    """Four-node EIG: intent -> retrieval + memory -> action."""
    prov_untrust = Provenance()
    events = [
        RuntimeEvent(
            event_id="intent", node_type=NodeType.INTENT,
            content_hash="H-intent", provenance=prov_untrust, timestamp_ms=0,
        ),
        RuntimeEvent(
            event_id="retr", node_type=NodeType.RETRIEVAL,
            content_hash="H-retr", provenance=prov_untrust, timestamp_ms=1,
            consumes=["intent"],
        ),
        RuntimeEvent(
            event_id="mem", node_type=NodeType.MEMORY,
            content_hash="H-mem", provenance=prov_untrust, timestamp_ms=2,
            consumes=["intent", "retr"],
        ),
        RuntimeEvent(
            event_id="act", node_type=NodeType.ACTION,
            content_hash="H-act", provenance=prov_untrust, timestamp_ms=3,
            consumes=["mem"],
        ),
    ]
    return build_eig_from_events(events)


def deterministic_guard(eig: EIG, target_action_id: str,
                        view: dict[str, EffectiveNode],
                        precedents=None) -> float:
    """A deterministic mock guard that scores the sum of content-hash-derived
    values for all *present* mutable-ancestor nodes.

    Score = number of characters across present-node content hashes / 10.
    Deterministic and content-sensitive: replacements shift the score.
    """
    score = 0.0
    for aid in eig.mutable_ancestors_of(target_action_id):
        eff = view[aid]
        if not eff.is_present:
            continue
        score += len(eff.content_hash) / 10.0
    return score


# ----------------------------------------------------------------------
# Intervention constructors
# ----------------------------------------------------------------------


class TestInterventionConstructors(unittest.TestCase):

    def test_empty(self):
        iv = Intervention.empty()
        self.assertEqual(iv.node_interventions, ())
        self.assertEqual(iv.ablated_ids(), set())
        self.assertEqual(iv.replaced_map(), {})
        self.assertEqual(iv.touches(), set())

    def test_ablate_multi(self):
        iv = Intervention.ablate(["mem", "retr"])
        self.assertEqual(iv.ablated_ids(), {"mem", "retr"})
        self.assertEqual(iv.replaced_map(), {})
        self.assertEqual(iv.touches(), {"mem", "retr"})

    def test_replace(self):
        iv = Intervention.replace("mem", "H-mem-CTRL", "payload-ctrl")
        self.assertEqual(iv.ablated_ids(), set())
        rep = iv.replaced_map()
        self.assertIn("mem", rep)
        self.assertEqual(rep["mem"].control_content_hash, "H-mem-CTRL")
        self.assertEqual(rep["mem"].control_payload, "payload-ctrl")


# ----------------------------------------------------------------------
# resolve_view
# ----------------------------------------------------------------------


class TestResolveView(unittest.TestCase):

    def test_clean_view_all_present(self):
        eig = mk_eig()
        view = resolve_view(eig, Intervention.empty())
        for nid, eff in view.items():
            self.assertTrue(eff.is_present)
            self.assertEqual(eff.content_hash, eig.nodes[nid].content_hash)

    def test_ablation_view(self):
        eig = mk_eig()
        view = resolve_view(eig, Intervention.ablate(["mem"]))
        self.assertFalse(view["mem"].is_present)
        for nid in ["intent", "retr", "act"]:
            self.assertTrue(view[nid].is_present)

    def test_replacement_view(self):
        eig = mk_eig()
        view = resolve_view(eig,
                            Intervention.replace("retr", "H-retr-CTRL", "P-ctrl"))
        self.assertTrue(view["retr"].is_present)
        self.assertEqual(view["retr"].content_hash, "H-retr-CTRL")
        self.assertEqual(view["retr"].payload, "P-ctrl")
        # Non-touched nodes unchanged
        self.assertEqual(view["mem"].content_hash, "H-mem")


# ----------------------------------------------------------------------
# counterfactual_delta
# ----------------------------------------------------------------------


class TestCounterfactualDelta(unittest.TestCase):

    def test_delta_ablation_removes_hash_contribution(self):
        eig = mk_eig()
        # Clean: retr and mem are mutable ancestors of act.
        # Clean score = (len("H-retr") + len("H-mem")) / 10 = (6+5)/10 = 1.1
        # Ablation of "mem": Clean score = 1.1, Ablated score = 0.6
        # delta_e = 1.1 - 0.6 = 0.5
        delta = counterfactual_delta(
            deterministic_guard, eig, target_action_id="act",
            node_id="mem", op=InterventionOp.ABLATION,
        )
        self.assertAlmostEqual(delta, 0.5, places=6)

    def test_delta_ablation_of_retr(self):
        eig = mk_eig()
        # len("H-retr") = 6, so delta = 0.6
        delta = counterfactual_delta(
            deterministic_guard, eig, target_action_id="act",
            node_id="retr", op=InterventionOp.ABLATION,
        )
        self.assertAlmostEqual(delta, 0.6, places=6)

    def test_delta_replacement(self):
        eig = mk_eig()
        # Replace "mem" (H-mem, 5 chars) with H-mem-XXX (9 chars)
        # delta = 5/10 - 9/10 = -0.4
        delta = counterfactual_delta(
            deterministic_guard, eig, target_action_id="act",
            node_id="mem", op=InterventionOp.REPLACEMENT,
            control_content_hash="H-mem-XXX",
        )
        self.assertAlmostEqual(delta, -0.4, places=6)

    def test_delta_unknown_node_raises(self):
        eig = mk_eig()
        with self.assertRaises(ValueError):
            counterfactual_delta(
                deterministic_guard, eig, target_action_id="act",
                node_id="does-not-exist",
            )

    def test_delta_unsupported_op_raises(self):
        eig = mk_eig()
        with self.assertRaises(ValueError):
            counterfactual_delta(
                deterministic_guard, eig, target_action_id="act",
                node_id="mem", op=InterventionOp.REPLAY,
            )

    def test_q_repetitions_average(self):
        # With a deterministic guard, q > 1 must give the same result as q=1
        eig = mk_eig()
        for q in [1, 3, 10]:
            delta = counterfactual_delta(
                deterministic_guard, eig, target_action_id="act",
                node_id="mem", q=q,
            )
            self.assertAlmostEqual(delta, 0.5, places=6)


# ----------------------------------------------------------------------
# counterfactual_deltas_for_ancestors
# ----------------------------------------------------------------------


class TestCounterfactualDeltasBatch(unittest.TestCase):

    def test_iterates_mutable_ancestors_only(self):
        eig = mk_eig()
        deltas = counterfactual_deltas_for_ancestors(
            deterministic_guard, eig, target_action_id="act",
            mutable_only=True,
        )
        # Only retr and mem are mutable ancestors of act
        self.assertEqual(set(deltas.keys()), {"retr", "mem"})
        self.assertAlmostEqual(deltas["mem"], 0.5, places=6)
        self.assertAlmostEqual(deltas["retr"], 0.6, places=6)

    def test_all_ancestors_when_mutable_only_false(self):
        eig = mk_eig()
        deltas = counterfactual_deltas_for_ancestors(
            deterministic_guard, eig, target_action_id="act",
            mutable_only=False,
        )
        # intent is not mutable but is an ancestor; included here
        self.assertEqual(set(deltas.keys()), {"intent", "retr", "mem"})
        # Ablation of intent: still 0 because deterministic_guard only scores
        # mutable ancestors; intent contributes 0 either way
        self.assertAlmostEqual(deltas["intent"], 0.0, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
