"""
precedentguard/certificate.py

Theorem 3 (Finite-Sample Double-Sided Certificate) — computation layer.

Given class-conditional calibration sets C_1 (Y=1) and C_0 (Y=0), and a
configuration gamma = (theta, caps, eps_-, eps_+), this module computes:

  U_FN(gamma) = R_hat_FN(gamma) + t
  U_FP(gamma) = R_hat_FP(gamma) + t

where t = sqrt(log(2|Gamma|/alpha) / (2n)) is the one-sided Hoeffding tail
(v0.2 Remark 5.4.1, aligned with skeleton Theorem 3 with N = 2|Gamma|).

Assumption A5 (grid pre-commitment) is enforced via `assert_grid_committed`,
which verifies that a hash of the configuration grid has been logged BEFORE the
calibration data are touched. Callers must invoke `commit_grid_hash` first.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional

from precedentguard.clipping import TypeCaps, compute_rho
from precedentguard.types import NodeType


# ----------------------------------------------------------------------
# Configuration grid gamma and Assumption A5 enforcement
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class CertificateConfig:
    """A single grid point gamma = (theta, caps, eps_-, eps_+, m, m_ins_unattested)."""

    theta: float
    caps_by_type: Mapping[NodeType, TypeCaps]
    eps_neg: float
    eps_pos: float
    m: Mapping[NodeType, int]                       # attack budget per type
    m_ins_unattested: Mapping[NodeType, int]        # unauth-insertion sub-budget

    def serialize(self) -> str:
        """Deterministic JSON serialization for hashing (A5 grid pre-commitment)."""
        payload = {
            "theta": self.theta,
            "caps": {
                nt.value: {"c_neg": c.c_neg, "c_pos": c.c_pos}
                for nt, c in sorted(self.caps_by_type.items(), key=lambda kv: kv[0].value)
            },
            "eps_neg": self.eps_neg,
            "eps_pos": self.eps_pos,
            "m": {nt.value: v for nt, v in sorted(self.m.items(), key=lambda kv: kv[0].value)},
            "m_ins_unattested": {
                nt.value: v
                for nt, v in sorted(self.m_ins_unattested.items(), key=lambda kv: kv[0].value)
            },
        }
        return json.dumps(payload, sort_keys=True)


def grid_hash(configs: Iterable[CertificateConfig]) -> str:
    """SHA-256 hash of a fixed configuration grid (A5).

    The grid must be materialized as a list before hashing so that iteration
    order and content are deterministic.
    """
    concat = "\n".join(cfg.serialize() for cfg in configs)
    return hashlib.sha256(concat.encode("utf-8")).hexdigest()


REGISTRY_PATH_DEFAULT = "experiments/registry.csv"


def commit_grid_hash(configs: list[CertificateConfig],
                     registry_path: str = REGISTRY_PATH_DEFAULT,
                     tag: str = "certificate_grid") -> str:
    """Commit the grid hash to the experiment registry (A5).

    Returns the hash so callers can log it in downstream artifacts. Appends a
    row to registry.csv: timestamp, tag, |grid|, hash.
    """
    h = grid_hash(configs)
    path = Path(registry_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    import datetime as _dt
    ts = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with path.open("a", encoding="utf-8", newline="") as f:
        if not exists:
            f.write("timestamp,tag,grid_size,hash\n")
        f.write(f"{ts},{tag},{len(configs)},{h}\n")
    return h


def assert_grid_committed(configs: list[CertificateConfig],
                          registry_path: str = REGISTRY_PATH_DEFAULT,
                          tag: str = "certificate_grid") -> None:
    """Raise if the given grid's hash is not present in the registry (A5).

    Callers should invoke this after computing R_hat but before returning the
    certificate — this catches the case where the grid was chosen post-hoc.
    """
    h = grid_hash(configs)
    path = Path(registry_path)
    if not path.exists():
        raise RuntimeError(
            f"A5 violation: registry {registry_path!r} not found; call "
            f"commit_grid_hash() before certifying."
        )
    hashes: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        _ = f.readline()  # header
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 4 and parts[1] == tag:
                hashes.add(parts[3])
    if h not in hashes:
        raise RuntimeError(
            f"A5 violation: grid hash {h!r} not in registry (tag={tag!r}); "
            f"grid was not pre-committed before calibration."
        )


# ----------------------------------------------------------------------
# Hoeffding tail (one-sided per Remark added 2026-07-01)
# ----------------------------------------------------------------------


def hoeffding_tail(n: int, grid_size: int, alpha: float,
                   one_sided: bool = True) -> float:
    """Return t = sqrt(log(N/alpha) / (2n)) with N = 2|Gamma| (one-sided)
    or N = 4|Gamma| (two-sided, conservative).

    Aligned with skeleton Theorem 3 (2|Gamma|) after the 2026-07-01 decision.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    if grid_size < 1:
        raise ValueError(f"grid_size must be >= 1, got {grid_size}")
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    multiplier = 2 if one_sided else 4
    return math.sqrt(math.log(multiplier * grid_size / alpha) / (2 * n))


# ----------------------------------------------------------------------
# Margin computation and R_hat
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class MarginSample:
    """A single calibration sample: label + score."""

    label: int          # 0 or 1
    score: float        # S_PG(x)

    def margin_M1(self, theta: float) -> float:
        """M_1 = S(x) - theta (for Y=1 examples)."""
        return self.score - theta

    def margin_M0(self, theta: float) -> float:
        """M_0 = theta - S(x) (for Y=0 examples)."""
        return theta - self.score


def vulnerable_margin_rate(samples: list[MarginSample], theta: float,
                           rho: float, positive_class: bool) -> float:
    """Empirical rate of samples with vulnerable margin.

    Positive class (Y=1):  R_hat_FN(gamma) = |{x : M_1(x) <= rho_-}| / n_1.
    Negative class (Y=0):  R_hat_FP(gamma) = |{x : M_0(x) <= rho_+}| / n_0.
    """
    target_label = 1 if positive_class else 0
    filtered = [s for s in samples if s.label == target_label]
    n = len(filtered)
    if n == 0:
        raise ValueError(
            f"no samples with label={target_label} in calibration set"
        )
    if positive_class:
        vuln = sum(1 for s in filtered if s.margin_M1(theta) <= rho)
    else:
        vuln = sum(1 for s in filtered if s.margin_M0(theta) <= rho)
    return vuln / n


# ----------------------------------------------------------------------
# Full certificate
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Certificate:
    """Theorem 3 certificate output for a single grid point gamma."""

    U_FN: float                     # upper bound on FNR
    U_FP: float                     # upper bound on FPR
    R_hat_FN: float                 # empirical vulnerable-margin rate (unsafe)
    R_hat_FP: float                 # empirical vulnerable-margin rate (safe)
    t_FN: float                     # Hoeffding tail on the unsafe class
    t_FP: float                     # Hoeffding tail on the safe class
    rho_plus: float
    rho_minus: float
    n_1: int
    n_0: int
    grid_size: int
    alpha: float
    non_vacuous_FN: bool            # U_FN < 0.5
    non_vacuous_FP: bool            # U_FP < 0.5


def certify(
    cal_samples: list[MarginSample],
    config: CertificateConfig,
    grid: list[CertificateConfig],
    alpha: float,
    *,
    one_sided: bool = True,
    enforce_A5: bool = True,
    registry_path: str = REGISTRY_PATH_DEFAULT,
) -> Certificate:
    """Compute the Theorem 3 certificate for a single grid point.

    Parameters
    ----------
    cal_samples : list[MarginSample]
        All calibration samples (mixed labels).
    config : CertificateConfig
        The specific grid point being certified.
    grid : list[CertificateConfig]
        The full pre-committed configuration grid |Gamma|.
    alpha : float
        Confidence parameter.
    one_sided : bool
        Use one-sided (2|Gamma|) Hoeffding by default; set False for the
        conservative two-sided (4|Gamma|) variant.
    enforce_A5 : bool
        If True, `assert_grid_committed` is called before computing R_hat.
    registry_path : str
        Path to the experiment registry for A5 verification.

    Returns
    -------
    Certificate
    """
    if config not in grid:
        raise ValueError(f"config not in provided grid; ensure it was pre-committed")

    if enforce_A5:
        assert_grid_committed(grid, registry_path=registry_path)

    # Compute rho_+, rho_-
    rho_plus, rho_minus = compute_rho(
        m=config.m,
        m_ins_unattested=config.m_ins_unattested,
        caps_by_type=config.caps_by_type,
        eps_neg=config.eps_neg,
        eps_pos=config.eps_pos,
    )

    # Empirical vulnerable-margin rates
    R_FN = vulnerable_margin_rate(cal_samples, config.theta, rho_minus,
                                  positive_class=True)
    R_FP = vulnerable_margin_rate(cal_samples, config.theta, rho_plus,
                                  positive_class=False)

    n_1 = sum(1 for s in cal_samples if s.label == 1)
    n_0 = sum(1 for s in cal_samples if s.label == 0)

    grid_size = len(grid)
    t_FN = hoeffding_tail(n_1, grid_size, alpha, one_sided=one_sided)
    t_FP = hoeffding_tail(n_0, grid_size, alpha, one_sided=one_sided)

    U_FN = R_FN + t_FN
    U_FP = R_FP + t_FP

    return Certificate(
        U_FN=U_FN,
        U_FP=U_FP,
        R_hat_FN=R_FN,
        R_hat_FP=R_FP,
        t_FN=t_FN,
        t_FP=t_FP,
        rho_plus=rho_plus,
        rho_minus=rho_minus,
        n_1=n_1,
        n_0=n_0,
        grid_size=grid_size,
        alpha=alpha,
        non_vacuous_FN=U_FN < 0.5,
        non_vacuous_FP=U_FP < 0.5,
    )
