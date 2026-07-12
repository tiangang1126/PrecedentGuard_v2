"""
tests/test_certificate.py

Unit tests for certificate.py:
  - hoeffding_tail matches scripts/day1_theorem_numerical_example.log values
  - vulnerable_margin_rate on hand-computed calibration sets
  - grid_hash is deterministic and pre-commitment via commit_grid_hash/assert_grid_committed
  - certify() end-to-end with a mocked calibration set
  - Assumption A5 enforcement rejects post-hoc grids
"""

from __future__ import annotations

import math
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from precedentguard.certificate import (
    Certificate,
    CertificateConfig,
    MarginSample,
    assert_grid_committed,
    certify,
    commit_grid_hash,
    grid_hash,
    hoeffding_tail,
    vulnerable_margin_rate,
)
from precedentguard.clipping import TypeCaps, symmetric_caps
from precedentguard.types import NodeType


# ----------------------------------------------------------------------
# hoeffding_tail — must match Day 1 script
# ----------------------------------------------------------------------


class TestHoeffdingTail(unittest.TestCase):

    def test_day1_baseline(self):
        # From scripts/day1_theorem_numerical_example.log:
        #   n=500, |Gamma|=20, alpha=0.05, one-sided => t = 0.081759
        t = hoeffding_tail(n=500, grid_size=20, alpha=0.05, one_sided=True)
        self.assertAlmostEqual(t, 0.081759, places=5)

    def test_two_sided_larger(self):
        t1 = hoeffding_tail(n=500, grid_size=20, alpha=0.05, one_sided=True)
        t2 = hoeffding_tail(n=500, grid_size=20, alpha=0.05, one_sided=False)
        self.assertGreater(t2, t1)
        # Relative gap (t_4 - t_2) / t_2 == 5.06% at (|Gamma|=20, alpha=0.05)
        rel = (t2 - t1) / t1 * 100.0
        self.assertAlmostEqual(rel, 5.06, places=1)

    def test_reviewer_datapoints(self):
        # From AI cold-read audit 2026-07-01 spot-check reproduction:
        for gamma, alpha, expected_pct in [(10, 0.05, 5.63),
                                            (100, 0.05, 4.09),
                                            (1000, 0.01, 2.80)]:
            t2 = hoeffding_tail(n=1, grid_size=gamma, alpha=alpha, one_sided=True)
            t4 = hoeffding_tail(n=1, grid_size=gamma, alpha=alpha, one_sided=False)
            pct = (t4 / t2 - 1) * 100.0
            self.assertAlmostEqual(pct, expected_pct, places=1,
                                   msg=f"|Gamma|={gamma}, alpha={alpha}: {pct} vs {expected_pct}")

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            hoeffding_tail(n=0, grid_size=10, alpha=0.05)
        with self.assertRaises(ValueError):
            hoeffding_tail(n=100, grid_size=0, alpha=0.05)
        with self.assertRaises(ValueError):
            hoeffding_tail(n=100, grid_size=10, alpha=1.0)
        with self.assertRaises(ValueError):
            hoeffding_tail(n=100, grid_size=10, alpha=0.0)


# ----------------------------------------------------------------------
# vulnerable_margin_rate
# ----------------------------------------------------------------------


class TestVulnerableMarginRate(unittest.TestCase):

    def test_unsafe_class(self):
        theta = 0.5
        # Unsafe (Y=1) samples with scores: 0.4, 0.7, 0.8, 0.55
        # M_1 = S - theta = [-0.1, 0.2, 0.3, 0.05]
        # rho_- = 0.15: M_1 <= 0.15 => {-0.1, 0.05} => 2/4 = 0.5
        samples = [
            MarginSample(label=1, score=0.4),
            MarginSample(label=1, score=0.7),
            MarginSample(label=1, score=0.8),
            MarginSample(label=1, score=0.55),
        ]
        rate = vulnerable_margin_rate(samples, theta=0.5, rho=0.15,
                                      positive_class=True)
        self.assertAlmostEqual(rate, 0.5)

    def test_safe_class(self):
        theta = 0.5
        # Safe (Y=0) samples with scores: 0.1, 0.3, 0.5, 0.6
        # M_0 = theta - S = [0.4, 0.2, 0.0, -0.1]
        # rho_+ = 0.1: M_0 <= 0.1 => {0.0, -0.1} => 2/4 = 0.5
        samples = [
            MarginSample(label=0, score=0.1),
            MarginSample(label=0, score=0.3),
            MarginSample(label=0, score=0.5),
            MarginSample(label=0, score=0.6),
        ]
        rate = vulnerable_margin_rate(samples, theta=0.5, rho=0.1,
                                      positive_class=False)
        self.assertAlmostEqual(rate, 0.5)

    def test_ignores_other_label(self):
        # Mixed sample; only positive-class samples counted for FN rate
        samples = [
            MarginSample(label=1, score=0.4),  # M_1 = -0.1, vulnerable
            MarginSample(label=0, score=0.4),  # ignored
            MarginSample(label=1, score=0.9),  # M_1 = 0.4, safe
        ]
        rate = vulnerable_margin_rate(samples, theta=0.5, rho=0.0,
                                      positive_class=True)
        self.assertAlmostEqual(rate, 0.5)  # 1 vulnerable of 2 positives

    def test_empty_class_raises(self):
        samples = [MarginSample(label=1, score=0.5)]
        with self.assertRaises(ValueError):
            vulnerable_margin_rate(samples, theta=0.5, rho=0.0,
                                   positive_class=False)


# ----------------------------------------------------------------------
# grid_hash and A5 enforcement
# ----------------------------------------------------------------------


def _mk_cfg(theta: float, c: float = 0.3, eps: float = 1.0,
            m_mem: int = 1, m_ins: int = 0) -> CertificateConfig:
    return CertificateConfig(
        theta=theta,
        caps_by_type={
            NodeType.MEMORY: symmetric_caps(c),
            NodeType.RETRIEVAL: symmetric_caps(c),
        },
        eps_neg=eps, eps_pos=eps,
        m={NodeType.MEMORY: m_mem, NodeType.RETRIEVAL: 0},
        m_ins_unattested={NodeType.MEMORY: m_ins, NodeType.RETRIEVAL: 0},
    )


class TestGridHash(unittest.TestCase):

    def test_deterministic(self):
        grid1 = [_mk_cfg(0.5), _mk_cfg(0.6)]
        grid2 = [_mk_cfg(0.5), _mk_cfg(0.6)]
        self.assertEqual(grid_hash(grid1), grid_hash(grid2))

    def test_order_matters(self):
        # If the caller reorders the grid, the hash changes. This is intentional:
        # A5 requires exact pre-commitment.
        grid1 = [_mk_cfg(0.5), _mk_cfg(0.6)]
        grid2 = [_mk_cfg(0.6), _mk_cfg(0.5)]
        self.assertNotEqual(grid_hash(grid1), grid_hash(grid2))

    def test_content_matters(self):
        grid1 = [_mk_cfg(0.5)]
        grid2 = [_mk_cfg(0.55)]
        self.assertNotEqual(grid_hash(grid1), grid_hash(grid2))


class TestA5Enforcement(unittest.TestCase):

    def setUp(self):
        # Use an isolated temp registry per test
        self._tmp = tempfile.mkdtemp()
        self.registry_path = os.path.join(self._tmp, "registry.csv")

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_commit_then_assert_passes(self):
        grid = [_mk_cfg(0.5), _mk_cfg(0.6)]
        commit_grid_hash(grid, registry_path=self.registry_path)
        # Should not raise
        assert_grid_committed(grid, registry_path=self.registry_path)

    def test_uncommitted_grid_raises(self):
        grid = [_mk_cfg(0.5)]
        with self.assertRaises(RuntimeError):
            assert_grid_committed(grid, registry_path=self.registry_path)

    def test_post_hoc_grid_raises(self):
        """A5 attack scenario: adversary tries to certify a grid different from
        what was committed."""
        committed = [_mk_cfg(0.5)]
        commit_grid_hash(committed, registry_path=self.registry_path)
        post_hoc = [_mk_cfg(0.5), _mk_cfg(0.6)]  # extended grid
        with self.assertRaises(RuntimeError):
            assert_grid_committed(post_hoc, registry_path=self.registry_path)

    def test_a5_extended_alpha_grid_locking(self):
        """A5-extended: (Gamma, alpha_grid) joint commitment.

        Post-hoc alpha selection (choosing alpha after seeing calibration
        outcomes) must be blocked equivalently to post-hoc Gamma selection.
        """
        grid = [_mk_cfg(0.5)]
        alpha_committed = [0.05, 0.01]
        commit_grid_hash(grid, registry_path=self.registry_path,
                         alpha_grid=alpha_committed)
        # Same (grid, alpha_grid): passes
        assert_grid_committed(grid, registry_path=self.registry_path,
                              alpha_grid=alpha_committed)
        # Different alpha_grid: rejected (post-hoc alpha selection)
        with self.assertRaises(RuntimeError):
            assert_grid_committed(grid, registry_path=self.registry_path,
                                  alpha_grid=[0.05, 0.10])
        # Missing alpha_grid arg on assertion but committed with one: rejected
        # (asserts a different, legacy hash)
        with self.assertRaises(RuntimeError):
            assert_grid_committed(grid, registry_path=self.registry_path,
                                  alpha_grid=None)

    def test_a5_extended_certify_rejects_out_of_grid_alpha(self):
        """certify() with alpha_grid should reject an alpha not in the grid."""
        cfg = _mk_cfg(theta=0.5)
        grid = [cfg]
        alpha_grid = [0.05, 0.01]
        commit_grid_hash(grid, registry_path=self.registry_path,
                         alpha_grid=alpha_grid)
        cal = [MarginSample(1, 0.9), MarginSample(0, 0.1)]
        # Requesting an alpha not in the committed set is a violation
        with self.assertRaises(ValueError):
            certify(
                cal_samples=cal, config=cfg, grid=grid,
                alpha=0.10,  # NOT in {0.05, 0.01}
                alpha_grid=alpha_grid,
                registry_path=self.registry_path,
            )

    def test_certify_accepts_nondefault_registry_tag(self):
        """certify() should verify A5 against the caller-specified registry tag."""
        cfg = _mk_cfg(theta=0.5)
        grid = [cfg]
        alpha_grid = [0.05]
        commit_grid_hash(
            grid,
            registry_path=self.registry_path,
            tag="certificate_grid_day8",
            alpha_grid=alpha_grid,
        )
        cal = [MarginSample(1, 0.9), MarginSample(0, 0.1)]
        cert = certify(
            cal_samples=cal,
            config=cfg,
            grid=grid,
            alpha=0.05,
            alpha_grid=alpha_grid,
            registry_path=self.registry_path,
            registry_tag="certificate_grid_day8",
        )
        self.assertIsInstance(cert, Certificate)


# ----------------------------------------------------------------------
# End-to-end certify()
# ----------------------------------------------------------------------


class TestCertifyEndToEnd(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.registry_path = os.path.join(self._tmp, "registry.csv")

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_certify_baseline(self):
        cfg = _mk_cfg(theta=0.5, c=0.3, eps=1.0, m_mem=1, m_ins=0)
        grid = [cfg]
        commit_grid_hash(grid, registry_path=self.registry_path)

        # Hand-constructed calibration set (margins chosen to avoid rho_- boundary
        # to sidestep floating-point equality on the vulnerable-margin indicator):
        # 5 unsafe samples with M_1 in {-0.3, -0.1, 0.0, 0.2, 0.4}, all < 0.6
        # 5 safe samples with M_0 in {-0.3, -0.1, 0.0, 0.2, 0.4}, all < 0.6
        cal = [
            # unsafe: S = theta + M_1
            MarginSample(1, 0.2),
            MarginSample(1, 0.4),
            MarginSample(1, 0.5),
            MarginSample(1, 0.7),
            MarginSample(1, 0.9),
            # safe: S = theta - M_0
            MarginSample(0, 0.8),
            MarginSample(0, 0.6),
            MarginSample(0, 0.5),
            MarginSample(0, 0.3),
            MarginSample(0, 0.1),
        ]
        cert = certify(
            cal_samples=cal, config=cfg, grid=grid, alpha=0.05,
            registry_path=self.registry_path,
        )
        # rho_+ = rho_- = min(1.0, 1*0.6) = 0.6
        self.assertAlmostEqual(cert.rho_plus, 0.6, places=6)
        self.assertAlmostEqual(cert.rho_minus, 0.6, places=6)
        # All 5 unsafe M_1 in {-0.3, -0.1, 0.0, 0.2, 0.4} are < 0.6 => all vulnerable
        self.assertAlmostEqual(cert.R_hat_FN, 1.0)
        self.assertAlmostEqual(cert.R_hat_FP, 1.0)
        # This deliberately-vacuous case: U_FN > 1.0 (still above 0.5 => vacuous)
        self.assertGreater(cert.U_FN, 1.0)
        self.assertFalse(cert.non_vacuous_FN)

    def test_certify_non_vacuous_narrow_rho(self):
        # Choose a smaller cap so rho is tight and few samples are vulnerable
        cfg = _mk_cfg(theta=0.5, c=0.05, eps=1.0, m_mem=1, m_ins=0)
        grid = [cfg]
        commit_grid_hash(grid, registry_path=self.registry_path)

        # 100 unsafe with score = 0.9 (very safe from attack); 100 safe with S = 0.1
        cal = [MarginSample(1, 0.9) for _ in range(100)] + \
              [MarginSample(0, 0.1) for _ in range(100)]
        cert = certify(
            cal_samples=cal, config=cfg, grid=grid, alpha=0.05,
            registry_path=self.registry_path,
        )
        # rho = 0.1 (min of eps=1.0 and 1 * 2*0.05=0.1)
        self.assertAlmostEqual(cert.rho_plus, 0.1, places=6)
        # M_1 = 0.9 - 0.5 = 0.4 > 0.1 => no vulnerable => R_hat_FN = 0
        self.assertAlmostEqual(cert.R_hat_FN, 0.0)
        self.assertAlmostEqual(cert.R_hat_FP, 0.0)
        self.assertTrue(cert.non_vacuous_FN)
        self.assertTrue(cert.non_vacuous_FP)

    def test_certify_rejects_uncommitted(self):
        cfg = _mk_cfg(theta=0.5)
        grid = [cfg]
        # Do NOT commit
        cal = [MarginSample(1, 0.9), MarginSample(0, 0.1)]
        with self.assertRaises(RuntimeError):
            certify(cal_samples=cal, config=cfg, grid=grid, alpha=0.05,
                    registry_path=self.registry_path)

    def test_certify_config_not_in_grid_rejected(self):
        cfg_in = _mk_cfg(theta=0.5)
        cfg_out = _mk_cfg(theta=0.7)
        grid = [cfg_in]
        commit_grid_hash(grid, registry_path=self.registry_path)
        cal = [MarginSample(1, 0.9), MarginSample(0, 0.1)]
        with self.assertRaises(ValueError):
            certify(cal_samples=cal, config=cfg_out, grid=grid, alpha=0.05,
                    registry_path=self.registry_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
