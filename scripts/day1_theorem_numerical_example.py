"""
scripts/day1_theorem_numerical_example.py

Purpose
-------
Verify that Theorems 1-3 (v0.2 framework, precedentguard_theorems_v0.2_skeleton.tex)
produce non-vacuous certificate values on a toy configuration, and quantify the
2|Gamma| vs 4|Gamma| Hoeffding-multiplier trade-off before Gate alpha (2026-07-04 EOD).

Notation is aligned with v0.2 main draft Sec. 3-5 and the theorem skeleton.

Deterministic, no external dependencies beyond Python stdlib.

Run
---
python scripts/day1_theorem_numerical_example.py \
    2>&1 | tee scripts/day1_theorem_numerical_example.log

Sprint context
--------------
Day 1 (2026-07-01) EOD verification of the numerical example promised in the
Day 1 advisor guidance (Section 5, "Numerical example, 30 minutes, tonight
must-do"). Non-vacuity is a required item on the Self-Review Checklist,
item 9 of Section 7 of the theorem skeleton.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Tuple


# ----------------------------------------------------------------------------
# Configuration data class
# ----------------------------------------------------------------------------

@dataclass
class PGConfig:
    """PrecedentGuard configuration and threat model parameters.

    Symbols match precedentguard_theorems_v0.2_skeleton.tex.
    """

    # Per-type contribution caps: c_k^- and c_k^+ for k in {mem, obs, ret, tool, prec}
    c_neg: Dict[str, float]
    c_pos: Dict[str, float]

    # Outer clip interval [-eps_neg, +eps_pos]
    eps_neg: float
    eps_pos: float

    # Attack budget m_k per type
    m: Dict[str, int]

    # Sub-budget: how many of m_k are unauthenticated insertions
    # (contribute [0, c_k^+] rather than [-c_k^-, c_k^+] by the trust rule)
    m_ins_unattested: Dict[str, int]

    # Calibration-set sizes (class-conditional)
    n_1: int  # number of unsafe (Y=1) calibration examples
    n_0: int  # number of safe   (Y=0) calibration examples

    # Configuration grid size |Gamma|
    Gamma: int

    # Confidence parameter alpha in Theorem 3
    alpha: float

    # Hoeffding sidedness multiplier: 2 (one-sided, tight) vs 4 (two-sided, conservative)
    hoeffding_multiplier: int

    # Decision threshold theta
    theta: float


# ----------------------------------------------------------------------------
# Theorem 1: Directional Intervention Sensitivity Bound
# ----------------------------------------------------------------------------

def compute_delta(cfg: PGConfig) -> Dict[str, float]:
    """Delta_k = c_k^- + c_k^+ (Thm 1 proof, Step 1)."""
    return {k: cfg.c_neg[k] + cfg.c_pos[k] for k in cfg.c_neg}


def compute_rho(cfg: PGConfig) -> Tuple[float, float, float, float]:
    """Return (rho_plus, rho_minus, r_plus, r_minus)."""
    Delta = compute_delta(cfg)
    r_plus = sum(cfg.m[k] * Delta[k] for k in cfg.m)
    r_minus = sum(
        (cfg.m[k] - cfg.m_ins_unattested[k]) * Delta[k] for k in cfg.m
    )
    rho_plus = min(cfg.eps_pos, r_plus)
    rho_minus = min(cfg.eps_neg, r_minus)
    return rho_plus, rho_minus, r_plus, r_minus


# ----------------------------------------------------------------------------
# Theorem 3: Finite-Sample Double-Sided Certificate
# ----------------------------------------------------------------------------

def hoeffding_tail(cfg: PGConfig, n: int) -> float:
    """Return t = sqrt(log(N/alpha) / (2n)) where N = multiplier * |Gamma|."""
    N = cfg.hoeffding_multiplier * cfg.Gamma
    return math.sqrt(math.log(N / cfg.alpha) / (2 * n))


def certificate(cfg: PGConfig, R_hat_FN: float, R_hat_FP: float) -> Dict[str, float]:
    rho_plus, rho_minus, r_plus, r_minus = compute_rho(cfg)
    t_FN = hoeffding_tail(cfg, cfg.n_1)
    t_FP = hoeffding_tail(cfg, cfg.n_0)
    U_FN = R_hat_FN + t_FN
    U_FP = R_hat_FP + t_FP
    return {
        "rho_plus": rho_plus,
        "rho_minus": rho_minus,
        "r_plus": r_plus,
        "r_minus": r_minus,
        "t_FN": t_FN,
        "t_FP": t_FP,
        "U_FN": U_FN,
        "U_FP": U_FP,
        "non_vacuous_FN": U_FN < 0.5,
        "non_vacuous_FP": U_FP < 0.5,
    }


# ----------------------------------------------------------------------------
# Reporting helpers
# ----------------------------------------------------------------------------

def _fmt(x: float, prec: int = 6) -> str:
    return f"{x:.{prec}f}"


def print_header(title: str) -> None:
    bar = "=" * 78
    print(bar)
    print(title)
    print(bar)


def print_config(cfg: PGConfig) -> None:
    print(f"  c_neg (per type): {cfg.c_neg}")
    print(f"  c_pos (per type): {cfg.c_pos}")
    print(f"  eps_neg={_fmt(cfg.eps_neg,3)}, eps_pos={_fmt(cfg.eps_pos,3)}")
    print(f"  attack budget m: {cfg.m}  (sum={sum(cfg.m.values())})")
    print(f"  m_ins_unattested: {cfg.m_ins_unattested}  "
          f"(sum={sum(cfg.m_ins_unattested.values())})")
    print(f"  n_1={cfg.n_1}, n_0={cfg.n_0}, |Gamma|={cfg.Gamma}, "
          f"alpha={cfg.alpha}")
    print(f"  Hoeffding multiplier (N=mult*|Gamma|): {cfg.hoeffding_multiplier}")


def print_thm1_result(cfg: PGConfig) -> None:
    rho_plus, rho_minus, r_plus, r_minus = compute_rho(cfg)
    print(f"  Delta_k        : {compute_delta(cfg)}")
    print(f"  r_+ (pre-clip) : {_fmt(r_plus,4)}")
    print(f"  r_- (pre-clip) : {_fmt(r_minus,4)}")
    print(f"  rho_+ = min(eps_+, r_+)  = min({_fmt(cfg.eps_pos,3)}, "
          f"{_fmt(r_plus,3)}) = {_fmt(rho_plus,4)}")
    print(f"  rho_- = min(eps_-, r_-)  = min({_fmt(cfg.eps_neg,3)}, "
          f"{_fmt(r_minus,3)}) = {_fmt(rho_minus,4)}")


def print_certificate(cert: Dict[str, float]) -> None:
    print(f"  Hoeffding tail t_FN : {_fmt(cert['t_FN'])}")
    print(f"  Hoeffding tail t_FP : {_fmt(cert['t_FP'])}")
    print(f"  U_FN = R_hat_FN + t_FN = {_fmt(cert['U_FN'])}")
    print(f"  U_FP = R_hat_FP + t_FP = {_fmt(cert['U_FP'])}")
    verdict_FN = "OK (< 0.5)" if cert["non_vacuous_FN"] else "VACUOUS"
    verdict_FP = "OK (< 0.5)" if cert["non_vacuous_FP"] else "VACUOUS"
    print(f"  Non-vacuity check   : FN {verdict_FN} | FP {verdict_FP}")


# ----------------------------------------------------------------------------
# Baseline configuration and scenarios (from advisor guidance Section 5)
# ----------------------------------------------------------------------------

def baseline_config(hoeffding_multiplier: int = 2) -> PGConfig:
    """Baseline configuration used in advisor guidance Section 5.

    c_k^- = c_k^+ = 0.3 for every type (symmetric caps)
    eps_- = eps_+ = 1.0 (outer clip)
    m = (mem=1, obs=1, ret=0, tool=0, prec=1) => sum m_k = 3
    n_1 = n_0 = 500, |Gamma| = 20, alpha = 0.05
    """
    types = ["mem", "obs", "ret", "tool", "prec"]
    return PGConfig(
        c_neg={k: 0.3 for k in types},
        c_pos={k: 0.3 for k in types},
        eps_neg=1.0,
        eps_pos=1.0,
        m={"mem": 1, "obs": 1, "ret": 0, "tool": 0, "prec": 1},
        m_ins_unattested={k: 0 for k in types},  # overridden per scenario
        n_1=500,
        n_0=500,
        Gamma=20,
        alpha=0.05,
        hoeffding_multiplier=hoeffding_multiplier,
        theta=0.5,
    )


# ----------------------------------------------------------------------------
# Main verification suite
# ----------------------------------------------------------------------------

def scenario_A_all_replacements() -> None:
    print_header("Scenario A: All 3 modifications are REPLACEMENTS")
    print("  (worst case for downward shift: rho_- is at its maximum)")
    cfg = baseline_config(hoeffding_multiplier=2)
    print_config(cfg)
    print()
    print("Theorem 1 (rho +/-):")
    print_thm1_result(cfg)
    print()
    print("Theorem 3 (assume R_hat_FN=0.10, R_hat_FP=0.05):")
    cert = certificate(cfg, R_hat_FN=0.10, R_hat_FP=0.05)
    print_certificate(cert)
    print()


def scenario_B_all_unauth_insertions() -> None:
    print_header("Scenario B: All 3 modifications are UNAUTHENTICATED INSERTIONS")
    print("  (best case for downward shift by trust rule: rho_- = 0)")
    cfg = baseline_config(hoeffding_multiplier=2)
    cfg.m_ins_unattested = {"mem": 1, "obs": 1, "ret": 0, "tool": 0, "prec": 1}
    print_config(cfg)
    print()
    print("Theorem 1 (rho +/-):")
    print_thm1_result(cfg)
    print()
    print("Theorem 3 (assume R_hat_FN=0.10, R_hat_FP=0.05):")
    cert = certificate(cfg, R_hat_FN=0.10, R_hat_FP=0.05)
    print_certificate(cert)
    print()


def scenario_C_mixed() -> None:
    print_header("Scenario C: MIXED (1 replacement + 2 unauth insertions)")
    print("  (typical adversary; only 1 modification contributes to rho_-)")
    cfg = baseline_config(hoeffding_multiplier=2)
    cfg.m_ins_unattested = {"mem": 0, "obs": 1, "ret": 0, "tool": 0, "prec": 1}
    print_config(cfg)
    print()
    print("Theorem 1 (rho +/-):")
    print_thm1_result(cfg)
    print()
    print("Theorem 3 (assume R_hat_FN=0.10, R_hat_FP=0.05):")
    cert = certificate(cfg, R_hat_FN=0.10, R_hat_FP=0.05)
    print_certificate(cert)
    print()


def compare_hoeffding_multipliers() -> None:
    print_header("Hoeffding multiplier comparison: 2|Gamma| (one-sided) vs 4|Gamma| (two-sided)")
    print("  Convention: 'two-sided tail is X% larger than one-sided' = (t_4 - t_2) / t_2")
    print("  (matches the convention used by the independent reviewer 2026-07-01).")
    print("  Note: percentage is INDEPENDENT of n; the raw tail scales with 1/sqrt(n).")
    print()
    for n in [250, 500, 1000, 2000, 5000]:
        cfg2 = baseline_config(hoeffding_multiplier=2)
        cfg4 = baseline_config(hoeffding_multiplier=4)
        cfg2.n_1 = n
        cfg2.n_0 = n
        cfg4.n_1 = n
        cfg4.n_0 = n
        t2 = hoeffding_tail(cfg2, n)
        t4 = hoeffding_tail(cfg4, n)
        gap = t4 - t2
        rel = 100.0 * gap / t2 if t2 > 0 else 0.0
        print(f"  n={n:>5d} | t(2|Gamma|)={_fmt(t2)} | t(4|Gamma|)={_fmt(t4)} | "
              f"gap={_fmt(gap)} ({rel:.2f}% larger)")
    print()


def sensitivity_grid_gamma_alpha() -> None:
    """Grid scan of the 2|Gamma| vs 4|Gamma| tail ratio over (|Gamma|, alpha).

    The ratio sqrt(log(4|Gamma|/alpha) / log(2|Gamma|/alpha)) - 1 is
    independent of n (n cancels in the tail formula), so this table is
    a complete summary of the sidedness cost for the reference config.
    """
    print_header("Sensitivity grid: (|Gamma|, alpha) -> two-sided vs one-sided tail ratio")
    print("  Definition:  gap = t(4|Gamma|) / t(2|Gamma|) - 1")
    print("  Reading:     'the two-sided tail is X% larger than the one-sided tail'")
    print("  Property:    the ratio is INDEPENDENT of n and of R_hat.")
    print()

    Gamma_values = [5, 10, 20, 50, 100, 500]
    alpha_values = [0.01, 0.05, 0.10]

    header = "  |Gamma| \\ alpha" + "".join(f" | {a:>7.2f}" for a in alpha_values)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for G in Gamma_values:
        row = f"  |Gamma|={G:>5d}    "
        for a in alpha_values:
            log_4 = math.log(4 * G / a)
            log_2 = math.log(2 * G / a)
            ratio = math.sqrt(log_4 / log_2) - 1.0
            row += f" | {100.0 * ratio:>6.3f}%"
        print(row)
    print()

    print("  Markdown table (paste-ready for paper appendix or remark):")
    print()
    print("  | \\|Gamma\\| | alpha=0.01 | alpha=0.05 | alpha=0.10 |")
    print("  |---|---|---|---|")
    for G in Gamma_values:
        row = f"  | {G} |"
        for a in alpha_values:
            log_4 = math.log(4 * G / a)
            log_2 = math.log(2 * G / a)
            ratio = math.sqrt(log_4 / log_2) - 1.0
            row += f" {100.0 * ratio:.2f}% |"
        print(row)
    print()

    # Reproduce the three reviewer datapoints verbatim as spot-check
    print("  Reviewer spot-check reproduction (2026-07-01 audit report):")
    print()
    spot_checks = [
        (10, 0.05, 5.63),
        (100, 0.05, 4.09),
        (1000, 0.01, 2.80),
    ]
    all_match = True
    for G, a, expected in spot_checks:
        log_4 = math.log(4 * G / a)
        log_2 = math.log(2 * G / a)
        ratio_pct = (math.sqrt(log_4 / log_2) - 1.0) * 100.0
        match = abs(ratio_pct - expected) < 0.05
        if not match:
            all_match = False
        mark = "MATCH" if match else "MISMATCH"
        print(f"    [{mark}] (|Gamma|={G:>4d}, alpha={a:.2f}): "
              f"reviewer reported {expected:.2f}%, script computes {ratio_pct:.3f}%")
    print()
    print(f"  Overall spot-check: {'PASS' if all_match else 'FAIL'}")
    print()


def sensitivity_scan_grid_size() -> None:
    print_header("Sensitivity: how does |Gamma| affect the tail width?")
    print("  Fixed: n_1=n_0=500, alpha=0.05, multiplier=2 (one-sided)")
    print()
    for Gsize in [1, 5, 10, 20, 50, 100, 500]:
        cfg = baseline_config(hoeffding_multiplier=2)
        cfg.Gamma = Gsize
        t = hoeffding_tail(cfg, cfg.n_1)
        print(f"  |Gamma|={Gsize:>4d} | t = {_fmt(t)}")
    print()


def sensitivity_scan_R_hat() -> None:
    print_header("Certificate non-vacuity vs empirical R_hat (Scenario A, mult=2)")
    print("  U_FN = R_hat_FN + t_FN; U_FP = R_hat_FP + t_FP")
    print("  Non-vacuous <=> U < 0.5")
    print()
    cfg = baseline_config(hoeffding_multiplier=2)
    t = hoeffding_tail(cfg, cfg.n_1)
    print(f"  Fixed tail t = {_fmt(t)}")
    print()
    print(f"  {'R_hat':>10s} | {'U (R_hat+t)':>15s} | non-vacuous?")
    print(f"  {'-'*10:>10s} | {'-'*15:>15s} | {'-'*13}")
    for R in [0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.42]:
        U = R + t
        mark = "OK" if U < 0.5 else "VACUOUS"
        print(f"  {R:>10.4f} | {U:>15.4f} | {mark}")
    print()


def sanity_check_manual_calculations() -> None:
    """Cross-check hand-computed values from advisor guidance Section 5."""
    print_header("Sanity check: manual calculations vs script output")
    print("  Advisor guidance Section 5 claims:")
    print("    - Scenario A (all replacements): rho_+ = rho_- = 1.0")
    print("    - Scenario B (all unauth insert): rho_+ = 1.0, rho_- = 0.0")
    print("    - t (n=500, |Gamma|=20, alpha=0.05, 2|Gamma|) approx 0.082")
    print("    - U_FN approx 0.10 + 0.082 = 0.182 (with R_hat_FN=0.10)")
    print("    - U_FP approx 0.05 + 0.082 = 0.132 (with R_hat_FP=0.05)")
    print()

    cfg_A = baseline_config(hoeffding_multiplier=2)
    rho_plus_A, rho_minus_A, _, _ = compute_rho(cfg_A)
    cfg_B = baseline_config(hoeffding_multiplier=2)
    cfg_B.m_ins_unattested = {"mem": 1, "obs": 1, "ret": 0, "tool": 0, "prec": 1}
    rho_plus_B, rho_minus_B, _, _ = compute_rho(cfg_B)
    t = hoeffding_tail(cfg_A, 500)

    checks: List[Tuple[str, float, float]] = [
        ("rho_+ (A)", rho_plus_A, 1.0),
        ("rho_- (A)", rho_minus_A, 1.0),
        ("rho_+ (B)", rho_plus_B, 1.0),
        ("rho_- (B)", rho_minus_B, 0.0),
        ("t (n=500)", t, 0.082),
        ("U_FN A",    0.10 + t, 0.182),
        ("U_FP A",    0.05 + t, 0.132),
    ]

    all_pass = True
    for name, computed, expected in checks:
        # Manual values were rounded to 3 sig figs in the guidance
        ok = abs(computed - expected) < 5e-3
        mark = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{mark}] {name:12s}  computed={computed:.6f}  "
              f"expected~{expected:.3f}  diff={computed - expected:+.6f}")
    print()
    print(f"  Overall sanity check: {'PASS' if all_pass else 'FAIL'}")
    print()


def edge_case_zero_budget() -> None:
    """No attack: certificate should reduce to clean risk + Hoeffding tail."""
    print_header("Edge case: zero attack budget (all m_k = 0)")
    cfg = baseline_config(hoeffding_multiplier=2)
    cfg.m = {"mem": 0, "obs": 0, "ret": 0, "tool": 0, "prec": 0}
    print_config(cfg)
    print()
    print("Theorem 1 (rho +/-):")
    print_thm1_result(cfg)
    print()
    print("Theorem 3 (assume R_hat_FN=0.10, R_hat_FP=0.05):")
    cert = certificate(cfg, R_hat_FN=0.10, R_hat_FP=0.05)
    print_certificate(cert)
    print("  Interpretation: rho_+ = rho_- = 0 (no adversary can move the score);")
    print("  U_FN, U_FP degrade to the clean empirical error + Hoeffding tail.")
    print()


def edge_case_budget_saturates_outer_clip() -> None:
    """Attack budget large enough that outer clip becomes binding."""
    print_header("Edge case: attack budget saturates the outer clip")
    cfg = baseline_config(hoeffding_multiplier=2)
    cfg.m = {"mem": 5, "obs": 5, "ret": 0, "tool": 0, "prec": 5}  # 15 mods
    print_config(cfg)
    print()
    print("Theorem 1 (rho +/-):")
    print_thm1_result(cfg)
    print()
    print("Theorem 3 (assume R_hat_FN=0.10, R_hat_FP=0.05):")
    cert = certificate(cfg, R_hat_FN=0.10, R_hat_FP=0.05)
    print_certificate(cert)
    print("  Interpretation: raw sum 15*0.6 = 9.0 >> outer clip 1.0, so rho +/- = 1.0.")
    print("  This is Remark 2 in the skeleton (outer clip as adaptive-adversary safety).")
    print()


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------

def main() -> None:
    print("PrecedentGuard v0.2  Day 1 Numerical Example")
    print("Sprint date: 2026-07-01 (Sprint Day 1, Gate alpha at 2026-07-04 EOD)")
    print("Script: scripts/day1_theorem_numerical_example.py")
    print()

    sanity_check_manual_calculations()
    scenario_A_all_replacements()
    scenario_B_all_unauth_insertions()
    scenario_C_mixed()
    compare_hoeffding_multipliers()
    sensitivity_grid_gamma_alpha()
    sensitivity_scan_grid_size()
    sensitivity_scan_R_hat()
    edge_case_zero_budget()
    edge_case_budget_saturates_outer_clip()

    print_header("Summary")
    print("  * Theorem 1 directional bound: computed rho_+/rho_- match hand calc.")
    print("  * Theorem 3 finite-sample tail: computed t matches hand calc (~0.082).")
    print("  * Certificate non-vacuous on the baseline toy config for R_hat up to")
    print("    approximately 0.418 (i.e., 0.5 - t).")
    print("  * 2|Gamma| vs 4|Gamma| gap grows slowly; see the multiplier comparison")
    print("    section for exact numbers at various n.")
    print("  * Skeleton Section 7 Self-Review Checklist item 9 (non-vacuous")
    print("    numerical example) is now supported by this deterministic script.")


if __name__ == "__main__":
    main()
