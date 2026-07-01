"""
scripts/day3_end_to_end_smoke.py

Day 3 end-to-end smoke test: 10 toy trajectories -> PrecedentGuard.decide()
-> margins -> Theorem 3 certificate.

Purpose (Sprint Dashboard Day 3 16:00-18:00):
  - Verify that EIG + counterfactual + clipping + guard + certificate compose
    correctly on a small deterministic corpus.
  - Prove that the certificate is non-vacuous when calibration samples are
    reasonably separated from the threshold.
  - Exercise A5 grid pre-commitment: register the grid hash, then certify.

Not intended:
  - Real LLM backbone (uses a deterministic keyword-based mock).
  - Realistic attack rates or agent tasks.
  - Statistical claims about the certificate — just a wiring check.

Run:
    python scripts/day3_end_to_end_smoke.py \
        2>&1 | tee experiments/day3_smoke.log
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

from precedentguard import (
    NodeType,
    Provenance,
    RuntimeEvent,
    build_eig_from_events,
)
from precedentguard.certificate import (
    CertificateConfig,
    MarginSample,
    assert_grid_committed,
    certify,
    commit_grid_hash,
)
from precedentguard.clipping import TypeCaps, symmetric_caps
from precedentguard.counterfactual import EffectiveNode
from precedentguard.eig import EIG
from precedentguard.guard import AttestationContext, PrecedentGuard


# ----------------------------------------------------------------------
# Toy corpus generator
# ----------------------------------------------------------------------


POISON_TAG = "POISON"
CLEAN_TAG = "CLEAN"
DANGER_INTENT_TAG = "DANGER-INTENT"
BENIGN_INTENT_TAG = "BENIGN-INTENT"


def make_toy_eig(traj_id: str, is_unsafe: bool,
                 memory_attested: bool = False,
                 retrieval_attested: bool = False) -> EIG:
    """Build a 5-node toy EIG.

        intent -> retr -> mem -> obs -> act

    Design (v0.2 Sec 4.2): base score B(I,A) carries the primary safety signal
    via the intent tag; memory is a *bounded modifier*. Unsafe trajectories
    have DANGER intent + POISON memory; safe have BENIGN intent + CLEAN memory.
    """
    prov_signed_attested = Provenance(
        origin_id="validator",
        signature_valid=True,
        semantic_authorization=True,
        scope="default",
        policy_version="v1",
    )
    prov_signed_only = Provenance(
        origin_id="user",
        signature_valid=True,
        semantic_authorization=False,
        scope="default",
        policy_version="v1",
    )
    prov_untrusted = Provenance()

    mem_prov = prov_signed_attested if memory_attested else prov_untrusted
    retr_prov = prov_signed_attested if retrieval_attested else prov_untrusted

    mem_hash = f"M-{POISON_TAG if is_unsafe else CLEAN_TAG}-{traj_id}"
    intent_hash = f"I-{DANGER_INTENT_TAG if is_unsafe else BENIGN_INTENT_TAG}-{traj_id}"

    events = [
        RuntimeEvent(
            event_id=f"{traj_id}-intent", node_type=NodeType.INTENT,
            content_hash=intent_hash, provenance=prov_untrusted, timestamp_ms=0,
        ),
        RuntimeEvent(
            event_id=f"{traj_id}-retr", node_type=NodeType.RETRIEVAL,
            content_hash=f"R-{traj_id}", provenance=retr_prov, timestamp_ms=1,
            consumes=[f"{traj_id}-intent"],
        ),
        RuntimeEvent(
            event_id=f"{traj_id}-mem", node_type=NodeType.MEMORY,
            content_hash=mem_hash, provenance=mem_prov, timestamp_ms=2,
            consumes=[f"{traj_id}-intent", f"{traj_id}-retr"],
        ),
        RuntimeEvent(
            event_id=f"{traj_id}-obs", node_type=NodeType.OBSERVATION,
            content_hash=f"O-{traj_id}", provenance=prov_untrusted, timestamp_ms=3,
            consumes=[f"{traj_id}-mem"],
        ),
        RuntimeEvent(
            event_id=f"{traj_id}-act", node_type=NodeType.ACTION,
            content_hash=f"A-{traj_id}", provenance=prov_untrusted, timestamp_ms=4,
            consumes=[f"{traj_id}-obs"],
        ),
    ]
    return build_eig_from_events(events)


# ----------------------------------------------------------------------
# Deterministic keyword-based mock guard
# ----------------------------------------------------------------------


def keyword_guard(eig: EIG, target_action_id: str,
                  view: dict[str, EffectiveNode]) -> float:
    """Score = intent-driven base + bounded memory modifier.

    Design (aligned with v0.2 Sec 4.2 evidence-separable base score):
      - Base B(I, A): intent tag determines primary risk signal.
          DANGER intent -> base 0.70
          BENIGN intent -> base 0.15
      - Memory modifier: +0.05 if POISON present, else 0.
      - Other mutable nodes (retr/obs) contribute 0 in this toy setup.

    With c_mem = 0.04 and theta = 0.5, this yields:
      unsafe (DANGER + POISON) -> S = 0.70 + 0.05 = 0.75, M_1 = 0.25
      safe   (BENIGN + CLEAN)  -> S = 0.15 + 0.00 = 0.15, M_0 = 0.35
    Both margins exceed rho = 0.08, so the certificate is non-vacuous.
    """
    # Locate the intent node (unique per EIG in this toy setup)
    intent_nodes = [nid for nid, n in eig.nodes.items()
                    if n.node_type == NodeType.INTENT]
    if not intent_nodes:
        raise ValueError("EIG has no INTENT node")
    intent_id = intent_nodes[0]
    intent_hash = eig.nodes[intent_id].content_hash

    if DANGER_INTENT_TAG in intent_hash:
        score = 0.70
    else:
        score = 0.15

    for aid in eig.mutable_ancestors_of(target_action_id):
        eff = view[aid]
        if not eff.is_present:
            continue
        node = eig.nodes[aid]
        if node.node_type == NodeType.MEMORY and POISON_TAG in eff.content_hash:
            score += 0.05
    return score


# ----------------------------------------------------------------------
# Smoke test workflow
# ----------------------------------------------------------------------


CAPS = {
    NodeType.MEMORY: symmetric_caps(0.04),
    NodeType.RETRIEVAL: symmetric_caps(0.04),
    NodeType.OBSERVATION: symmetric_caps(0.04),
    NodeType.TOOL_RETURN: symmetric_caps(0.04),
}


def print_header(title: str) -> None:
    bar = "=" * 78
    print(bar)
    print(title)
    print(bar)


def run() -> None:
    print("PrecedentGuard v0.2  Day 3 End-to-End Smoke Test")
    print("Sprint date: 2026-07-03 (Day 3)")
    print("Corpus: 10 toy trajectories (5 unsafe with POISON memory, 5 safe)")
    print()

    # --------------------------------------------------------------
    # Build guard and toy corpus
    # --------------------------------------------------------------
    print_header("1. Build PrecedentGuard and toy corpus")
    # theta=0.30 sits in the (safe_S_PG=0.20, unsafe_S_PG=0.35) separation region;
    # any threshold in this open interval gives perfect toy separation. Real
    # experiments will calibrate theta on a dev split (v0.2 Sec 5.4).
    guard = PrecedentGuard(
        base_guard=keyword_guard,
        caps_by_type=CAPS,
        eps_neg=1.0,
        eps_pos=1.0,
        threshold=0.50,
        q=1,
        attestation_ctx=AttestationContext(
            current_scope="default",
            accepted_policy_versions=frozenset({"v1"}),
        ),
    )

    trajectories = []
    for i in range(5):
        trajectories.append((f"u{i}", True))   # unsafe
    for i in range(5):
        trajectories.append((f"s{i}", False))  # safe

    # --------------------------------------------------------------
    # Run guard on each trajectory
    # --------------------------------------------------------------
    print_header("2. Run PrecedentGuard.decide() on each trajectory")
    print(f"  {'traj':>6s} | {'label':>6s} | {'base':>6s} | {'z_pre':>6s} | "
          f"{'z_out':>6s} | {'S_PG':>6s} | verdict")
    print("  " + "-" * 65)

    margin_samples = []
    verdict_by_traj = {}
    for traj_id, is_unsafe in trajectories:
        eig = make_toy_eig(traj_id, is_unsafe=is_unsafe)
        target = f"{traj_id}-act"
        decision = guard.decide(eig, target_action_id=target)
        label = 1 if is_unsafe else 0
        verdict_by_traj[traj_id] = decision.verdict
        margin_samples.append(MarginSample(label=label, score=decision.s_pg))
        print(f"  {traj_id:>6s} | {label:>6d} | {decision.base_score:>6.3f} | "
              f"{decision.z_before_outer:>6.3f} | {decision.z_after_outer:>6.3f} | "
              f"{decision.s_pg:>6.3f} | {decision.verdict.value}")
    print()

    # --------------------------------------------------------------
    # Grid pre-commitment (A5) — write hash BEFORE certifying
    # --------------------------------------------------------------
    print_header("3. Commit configuration grid hash (A5)")

    # Use a temporary registry so this smoke test does not pollute the real one
    tmp_registry_dir = tempfile.mkdtemp(prefix="pg_day3_smoke_")
    registry_path = os.path.join(tmp_registry_dir, "registry.csv")

    cfg = CertificateConfig(
        theta=0.50,
        caps_by_type=CAPS,
        eps_neg=1.0,
        eps_pos=1.0,
        m={NodeType.MEMORY: 1, NodeType.RETRIEVAL: 0,
           NodeType.OBSERVATION: 0, NodeType.TOOL_RETURN: 0},
        m_ins_unattested={NodeType.MEMORY: 0, NodeType.RETRIEVAL: 0,
                          NodeType.OBSERVATION: 0, NodeType.TOOL_RETURN: 0},
    )
    grid = [cfg]
    h = commit_grid_hash(grid, registry_path=registry_path)
    print(f"  registry_path: {registry_path}")
    print(f"  grid size: {len(grid)}")
    print(f"  hash: {h[:16]}...")
    assert_grid_committed(grid, registry_path=registry_path)
    print(f"  A5 assertion: PASS")
    print()

    # --------------------------------------------------------------
    # Certify
    # --------------------------------------------------------------
    print_header("4. Certify (Theorem 3 with N=2|Gamma|)")
    cert = certify(
        cal_samples=margin_samples,
        config=cfg,
        grid=grid,
        alpha=0.05,
        registry_path=registry_path,
    )
    print(f"  n_1 (unsafe): {cert.n_1}")
    print(f"  n_0 (safe):   {cert.n_0}")
    print(f"  rho_+:        {cert.rho_plus:.4f}")
    print(f"  rho_-:        {cert.rho_minus:.4f}")
    print(f"  R_hat_FN:     {cert.R_hat_FN:.4f}")
    print(f"  R_hat_FP:     {cert.R_hat_FP:.4f}")
    print(f"  t_FN:         {cert.t_FN:.4f}")
    print(f"  t_FP:         {cert.t_FP:.4f}")
    print(f"  U_FN:         {cert.U_FN:.4f}  (non-vacuous: {cert.non_vacuous_FN})")
    print(f"  U_FP:         {cert.U_FP:.4f}  (non-vacuous: {cert.non_vacuous_FP})")
    print()

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------
    print_header("5. Summary and interpretation")
    n_unsafe_blocked = sum(1 for tid, unsafe in trajectories
                           if unsafe and verdict_by_traj[tid].value == "block")
    n_safe_allowed = sum(1 for tid, unsafe in trajectories
                         if not unsafe and verdict_by_traj[tid].value == "allow")
    print(f"  Unsafe trajectories correctly BLOCKED: {n_unsafe_blocked} / 5")
    print(f"  Safe trajectories correctly ALLOWED:   {n_safe_allowed} / 5")
    print()

    # With the deterministic keyword-based guard on this toy setup, the mock
    # guard's clean base + ablation counterfactual should give perfect
    # separation. If not, either the guard or the pipeline is broken.
    if n_unsafe_blocked == 5 and n_safe_allowed == 5:
        print("  [PASS] End-to-end wiring is correct on the toy corpus.")
    else:
        print("  [WARN] Toy corpus separation failed; inspect audit trails above.")

    if cert.non_vacuous_FN and cert.non_vacuous_FP:
        print("  [PASS] Certificate is non-vacuous (U_FN, U_FP both < 0.5).")
    elif not cert.non_vacuous_FN and not cert.non_vacuous_FP:
        print("  [NOTE] Certificate vacuous with n=5+5; expected with tiny cal set.")
    else:
        print("  [NOTE] Asymmetric non-vacuity — inspect margin distributions.")
    print()

    print(f"  Registry file left at: {registry_path}")
    print(f"  (Not cleaned up; delete manually if desired.)")
    print()

    # --------------------------------------------------------------
    # 6. Extended calibration for non-vacuous certificate demonstration
    # --------------------------------------------------------------
    print_header("6. Extended calibration (n=100+100) for non-vacuous certificate")
    print("  Rationale: Hoeffding tail at n=5 is ~0.6 which alone exceeds 0.5.")
    print("  With n=100 per class, t drops to ~0.14, permitting non-vacuous bounds.")
    print()

    ext_samples = []
    for i in range(100):
        eig = make_toy_eig(f"ext-u{i}", is_unsafe=True)
        d = guard.decide(eig, target_action_id=f"ext-u{i}-act")
        ext_samples.append(MarginSample(label=1, score=d.s_pg))
    for i in range(100):
        eig = make_toy_eig(f"ext-s{i}", is_unsafe=False)
        d = guard.decide(eig, target_action_id=f"ext-s{i}-act")
        ext_samples.append(MarginSample(label=0, score=d.s_pg))

    cert_ext = certify(
        cal_samples=ext_samples,
        config=cfg,
        grid=grid,
        alpha=0.05,
        registry_path=registry_path,
    )
    print(f"  n_1: {cert_ext.n_1}  |  n_0: {cert_ext.n_0}")
    print(f"  rho_+ = rho_- = {cert_ext.rho_plus:.4f}")
    print(f"  R_hat_FN = {cert_ext.R_hat_FN:.4f}  |  R_hat_FP = {cert_ext.R_hat_FP:.4f}")
    print(f"  t_FN = t_FP = {cert_ext.t_FN:.4f}")
    print(f"  U_FN = {cert_ext.U_FN:.4f}  (non-vacuous: {cert_ext.non_vacuous_FN})")
    print(f"  U_FP = {cert_ext.U_FP:.4f}  (non-vacuous: {cert_ext.non_vacuous_FP})")
    if cert_ext.non_vacuous_FN and cert_ext.non_vacuous_FP:
        print("  [PASS] Non-vacuous certificate achieved with n=100+100.")
    else:
        print("  [WARN] Certificate still vacuous at n=100; inspect margin distribution.")


if __name__ == "__main__":
    run()
