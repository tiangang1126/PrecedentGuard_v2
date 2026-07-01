"""
tests/test_clipping.py

Unit tests for per-type clipping, directional trust constraint, outer clip,
full aggregation, and Theorem 1 rho_+/rho_- computation.

Critical property covered: an unauthenticated insertion cannot lower the score
(Theorem 1 Step 2 refinement, v0.2 Section 4.6 directional trust constraint).
"""

from __future__ import annotations

import math
import unittest

from precedentguard.types import NodeType
from precedentguard.clipping import (
    AggregationResult,
    Contribution,
    TypeCaps,
    aggregate,
    compute_rho,
    directional_trust_clip,
    outer_clip,
    symmetric_caps,
    type_clip,
)


# ----------------------------------------------------------------------
# TypeCaps
# ----------------------------------------------------------------------


class TestTypeCaps(unittest.TestCase):

    def test_negative_cap_rejected(self):
        with self.assertRaises(ValueError):
            TypeCaps(c_neg=-0.1, c_pos=0.3)
        with self.assertRaises(ValueError):
            TypeCaps(c_neg=0.3, c_pos=-0.1)

    def test_delta_k(self):
        caps = TypeCaps(c_neg=0.3, c_pos=0.5)
        self.assertAlmostEqual(caps.delta_k, 0.8, places=6)

    def test_symmetric_helper(self):
        caps = symmetric_caps(0.3)
        self.assertEqual(caps.c_neg, 0.3)
        self.assertEqual(caps.c_pos, 0.3)
        self.assertAlmostEqual(caps.delta_k, 0.6, places=6)


# ----------------------------------------------------------------------
# type_clip
# ----------------------------------------------------------------------


class TestTypeClip(unittest.TestCase):

    def test_within_range_unchanged(self):
        caps = TypeCaps(c_neg=0.5, c_pos=0.5)
        self.assertAlmostEqual(type_clip(0.2, caps), 0.2)
        self.assertAlmostEqual(type_clip(-0.2, caps), -0.2)
        self.assertAlmostEqual(type_clip(0.0, caps), 0.0)

    def test_upper_saturation(self):
        caps = TypeCaps(c_neg=0.5, c_pos=0.3)
        self.assertAlmostEqual(type_clip(10.0, caps), 0.3)

    def test_lower_saturation(self):
        caps = TypeCaps(c_neg=0.4, c_pos=0.3)
        self.assertAlmostEqual(type_clip(-10.0, caps), -0.4)

    def test_asymmetric_caps(self):
        # Untrusted web content example from v0.2 Sec 4.5:
        # small negative cap, larger positive cap
        caps = TypeCaps(c_neg=0.1, c_pos=0.5)
        self.assertAlmostEqual(type_clip(-1.0, caps), -0.1)
        self.assertAlmostEqual(type_clip(1.0, caps), 0.5)


# ----------------------------------------------------------------------
# directional_trust_clip
# ----------------------------------------------------------------------


class TestDirectionalTrustClip(unittest.TestCase):

    def test_attested_unchanged(self):
        # Attested evidence can go negative
        self.assertAlmostEqual(directional_trust_clip(-0.3, is_attested=True), -0.3)
        self.assertAlmostEqual(directional_trust_clip(0.5, is_attested=True), 0.5)

    def test_unattested_lower_bound_zero(self):
        # This is the crux of Theorem 1's asymmetric rho_-
        self.assertAlmostEqual(directional_trust_clip(-0.3, is_attested=False), 0.0)
        self.assertAlmostEqual(directional_trust_clip(-1.0, is_attested=False), 0.0)
        # Positive unaffected
        self.assertAlmostEqual(directional_trust_clip(0.5, is_attested=False), 0.5)
        self.assertAlmostEqual(directional_trust_clip(0.0, is_attested=False), 0.0)


# ----------------------------------------------------------------------
# outer_clip
# ----------------------------------------------------------------------


class TestOuterClip(unittest.TestCase):

    def test_within_range(self):
        self.assertAlmostEqual(outer_clip(0.5, 1.0, 1.0), 0.5)
        self.assertAlmostEqual(outer_clip(-0.5, 1.0, 1.0), -0.5)

    def test_saturate_upper(self):
        self.assertAlmostEqual(outer_clip(5.0, 1.0, 1.0), 1.0)

    def test_saturate_lower(self):
        self.assertAlmostEqual(outer_clip(-5.0, 1.0, 1.0), -1.0)

    def test_asymmetric_epsilon(self):
        self.assertAlmostEqual(outer_clip(10.0, 0.5, 2.0), 2.0)
        self.assertAlmostEqual(outer_clip(-10.0, 0.5, 2.0), -0.5)

    def test_negative_epsilon_rejected(self):
        with self.assertRaises(ValueError):
            outer_clip(0.0, -0.1, 1.0)


# ----------------------------------------------------------------------
# aggregate — full pipeline
# ----------------------------------------------------------------------


class TestAggregate(unittest.TestCase):

    def _caps(self) -> dict[NodeType, TypeCaps]:
        return {
            NodeType.MEMORY: symmetric_caps(0.3),
            NodeType.RETRIEVAL: symmetric_caps(0.3),
            NodeType.TOOL_RETURN: symmetric_caps(0.3),
            NodeType.OBSERVATION: symmetric_caps(0.3),
        }

    def test_empty_input_yields_zero(self):
        result = aggregate([], self._caps(), eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(result.weighted_sum_before_outer, 0.0)
        self.assertAlmostEqual(result.final_z, 0.0)

    def test_attested_negative_contribution_survives(self):
        contribs = [
            Contribution(node_id="e1", node_type=NodeType.MEMORY,
                         raw_delta=-0.2, is_attested=True),
        ]
        result = aggregate(contribs, self._caps(), eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(result.per_node_pg_clipped["e1"], -0.2)
        self.assertAlmostEqual(result.final_z, -0.2)

    def test_unattested_negative_contribution_becomes_zero(self):
        # Theorem 1 Step 2 in action
        contribs = [
            Contribution(node_id="e1", node_type=NodeType.MEMORY,
                         raw_delta=-0.2, is_attested=False),
        ]
        result = aggregate(contribs, self._caps(), eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(result.per_node_pg_clipped["e1"], 0.0)
        self.assertAlmostEqual(result.final_z, 0.0)

    def test_type_clip_then_directional(self):
        # Raw = -10, type-clip => -0.3, unattested => max(0, -0.3) = 0
        contribs = [
            Contribution(node_id="e1", node_type=NodeType.MEMORY,
                         raw_delta=-10.0, is_attested=False),
        ]
        result = aggregate(contribs, self._caps(), eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(result.per_node_type_clipped["e1"], -0.3)
        self.assertAlmostEqual(result.per_node_pg_clipped["e1"], 0.0)

    def test_beta_coefficient_applied(self):
        contribs = [
            Contribution(node_id="e1", node_type=NodeType.MEMORY,
                         raw_delta=0.2, is_attested=True, beta=2.0),
        ]
        result = aggregate(contribs, self._caps(), eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(result.weighted_sum_before_outer, 0.4)

    def test_outer_clip_saturates(self):
        # Three attested contributions each at +0.3, sum = 0.9 within eps
        # Four attested contributions each at +0.3, sum = 1.2, clipped to eps_+ = 1.0
        contribs = [
            Contribution(node_id=f"e{i}", node_type=NodeType.MEMORY,
                         raw_delta=0.3, is_attested=True)
            for i in range(4)
        ]
        result = aggregate(contribs, self._caps(), eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(result.weighted_sum_before_outer, 1.2)
        self.assertAlmostEqual(result.final_z, 1.0)

    def test_missing_caps_type_raises(self):
        contribs = [
            Contribution(node_id="e1", node_type=NodeType.MEMORY,
                         raw_delta=0.1, is_attested=True),
        ]
        with self.assertRaises(ValueError):
            aggregate(contribs, {}, eps_neg=1.0, eps_pos=1.0)


# ----------------------------------------------------------------------
# compute_rho — must match scripts/day1_theorem_numerical_example.py
# ----------------------------------------------------------------------


class TestComputeRho(unittest.TestCase):

    def _caps(self) -> dict[NodeType, TypeCaps]:
        # Match the baseline in the numerical example script
        return {
            NodeType.MEMORY: symmetric_caps(0.3),
            NodeType.OBSERVATION: symmetric_caps(0.3),
            NodeType.RETRIEVAL: symmetric_caps(0.3),
            NodeType.TOOL_RETURN: symmetric_caps(0.3),
        }

    def test_scenario_A_all_replacements(self):
        """Match script Scenario A: m=(1,1,0,0), m_ins_unattested=(0,0,0,0)."""
        m = {NodeType.MEMORY: 1, NodeType.OBSERVATION: 1,
             NodeType.RETRIEVAL: 0, NodeType.TOOL_RETURN: 0}
        m_ins = {nt: 0 for nt in m}
        rho_plus, rho_minus = compute_rho(m, m_ins, self._caps(),
                                          eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(rho_plus, min(1.0, 2 * 0.6), places=6)
        self.assertAlmostEqual(rho_minus, min(1.0, 2 * 0.6), places=6)

    def test_scenario_B_all_unauth_insertions(self):
        """Match script Scenario B: all budget is unauth insertion => rho_- = 0."""
        m = {NodeType.MEMORY: 1, NodeType.OBSERVATION: 1,
             NodeType.RETRIEVAL: 0, NodeType.TOOL_RETURN: 0}
        m_ins = {NodeType.MEMORY: 1, NodeType.OBSERVATION: 1,
                 NodeType.RETRIEVAL: 0, NodeType.TOOL_RETURN: 0}
        rho_plus, rho_minus = compute_rho(m, m_ins, self._caps(),
                                          eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(rho_plus, min(1.0, 2 * 0.6), places=6)
        self.assertAlmostEqual(rho_minus, 0.0, places=6)

    def test_scenario_C_mixed(self):
        """Match script Scenario C: 1 replacement + 2 unauth insertions.

        Note: script uses budget (mem=1, obs=1, prec=1), m_ins=(mem=0, obs=1, prec=1).
        Here we substitute retr for prec since we're focused on mem+obs+retr+tool.
        r_- = (1-0)*0.6 + (1-1)*0.6 + (0-0)*0.6 = 0.6.
        """
        m = {NodeType.MEMORY: 1, NodeType.OBSERVATION: 1,
             NodeType.RETRIEVAL: 1, NodeType.TOOL_RETURN: 0}
        m_ins = {NodeType.MEMORY: 0, NodeType.OBSERVATION: 1,
                 NodeType.RETRIEVAL: 1, NodeType.TOOL_RETURN: 0}
        rho_plus, rho_minus = compute_rho(m, m_ins, self._caps(),
                                          eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(rho_plus, min(1.0, 3 * 0.6), places=6)
        self.assertAlmostEqual(rho_minus, min(1.0, 1 * 0.6), places=6)

    def test_zero_budget(self):
        m = {NodeType.MEMORY: 0, NodeType.OBSERVATION: 0}
        m_ins = {NodeType.MEMORY: 0, NodeType.OBSERVATION: 0}
        rho_plus, rho_minus = compute_rho(m, m_ins, self._caps(),
                                          eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(rho_plus, 0.0)
        self.assertAlmostEqual(rho_minus, 0.0)

    def test_saturates_outer_clip(self):
        # 15 modifications * 0.6 = 9.0 >> eps
        m = {NodeType.MEMORY: 5, NodeType.OBSERVATION: 5, NodeType.RETRIEVAL: 5}
        m_ins = {nt: 0 for nt in m}
        rho_plus, rho_minus = compute_rho(m, m_ins, self._caps(),
                                          eps_neg=1.0, eps_pos=1.0)
        self.assertAlmostEqual(rho_plus, 1.0, places=6)
        self.assertAlmostEqual(rho_minus, 1.0, places=6)

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValueError):
            compute_rho({NodeType.MEMORY: -1}, {NodeType.MEMORY: 0},
                        self._caps(), eps_neg=1.0, eps_pos=1.0)

    def test_ins_exceeds_budget_rejected(self):
        with self.assertRaises(ValueError):
            compute_rho({NodeType.MEMORY: 1}, {NodeType.MEMORY: 2},
                        self._caps(), eps_neg=1.0, eps_pos=1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
