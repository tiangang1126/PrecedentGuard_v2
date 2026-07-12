# Claim-Evidence Map

**Purpose:** Every load-bearing claim in `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md` maps here to (a) its evidence artifact, (b) figure/table location, (c) source-of-truth file. Any claim without a row here does not enter the final draft.

**Maintainer discipline:** Add a row *before* writing the claim into the draft. Delete a row *only* if the underlying claim is retracted.

---

## §1 Introduction claims

| Claim ID | Paper location | Evidence | Source-of-truth | Status |
|---|---|---|---|---|
| C-1.4.a | §1.4 line "raises benign block-rate from 67.5% to 76.0%" | Clipping-only benign block: 152/200; backbone benign block: 135/200; Wilson interval $[+2.5, +15.0]$ pp | `artifacts/day6/day7_agentharm_full_clipping_only_harmless_benign_200.jsonl`; `artifacts/day6/day7_agentharm_full_backbone_only_harmless_benign_200.jsonl` | ✅ verified (Day 10 audit §三) — leakage-independent |
| C-1.5.3 | §1.5 Contribution #3 "class-conditional two-sided certificates over heterogeneous trajectory-evidence channels" | Theorem 1 + Theorem 3 + Prop 1 | `precedentguard_theorems_v0.2_skeleton.tex` A.1-A.4 | ⚠️ Theorem proofs done; empirical certificate validity pending Day 12 |

## §3 Problem Formulation claims

| Claim ID | Paper location | Evidence | Source-of-truth | Status |
|---|---|---|---|---|
| C-3.2.a | §3.2 "we do not ask an LLM to infer a ground-truth causal graph from raw text" | EIG is constructed from runtime instrumentation only | `precedentguard/eig.py`; `scripts/run_real_backbone_eval.py:build_eig` | ✅ code-level verified |

## §4 Method claims

| Claim ID | Paper location | Evidence | Source-of-truth | Status |
|---|---|---|---|---|
| C-4.3.a | §4.3 "retrieval combines semantic and structural similarity" | Structural channel now active via `subgraph_signature` | `precedentguard/retrieval.py:raw_score`; `scripts/run_real_backbone_eval.py:_trajectory_subgraph_signature` | ⚠️ Day 12 rerun needed — Day 7 run had graph_similarity ≡ 0 |
| C-4.6.a | §4.6 "unauthorised evidence may increase risk but cannot reduce it" | Per-parent pg_clipped shows max(0, δ) for un-attested nodes | `artifacts/day6/*pg_with_precedents*.jsonl` `per_parent_pg_clipped` field | ✅ verified in JSONL sample |
| C-4.8.a | §4.8 Algorithm 1 five-stage pipeline | Implementation matches paper spec line-by-line | `precedentguard/guard.py:decide` (lines 213-404) | ✅ code-level verified; 165/165 unit tests green |

## §5 Theoretical Analysis claims

| Claim ID | Paper location | Evidence | Source-of-truth | Status |
|---|---|---|---|---|
| C-5.2.T1 | §5.2 Theorem 1 (Directional Intervention Sensitivity Bound) | Full proof + numerical example matches | Appendix A.1; `scripts/day1_theorem_numerical_example.py` (7 sanity checks PASS) | ✅ verified; AI cold-read reviewed |
| C-5.3.T2 | §5.3 Theorem 2 (Population Double-Sided Risk Bound) | Full proof | Appendix A.2 | ✅ AI cold-read reviewed; **pending human review** |
| C-5.4.T3 | §5.4 Theorem 3 (Finite-Sample Certificate) | Full proof; α + Γ joint pre-commitment (A5) | Appendix A.3; `precedentguard/certificate.py` | ✅ code + proof aligned |
| C-5.6.P1 | §5.6 Proposition 1 (TV Indistinguishability Lower Bound) | Existence counterexample proof; not a subsumption of SMSR | Appendix A.4 | ✅ AI cold-read reviewed; scope precisely stated |

## §7 Results claims

| Claim ID | Paper location | Evidence | Source-of-truth | Status |
|---|---|---|---|---|
| C-7.1.a.1 | §7.1.a Table 1 (LOEO n=200) | LOEO n=200 sweep (Llama-Guard-3-1B) | `artifacts/day6/day7_agentharm_full_*.jsonl` × 6 files | ✅ but labeled "reference only" due to leakage |
| C-7.1.b.1 | §7.1.b Table 2 (LOBTO n=200) | LOBTO n=200 sweep (Llama-Guard-3-1B) | `artifacts/day12/day12_lobto_*.jsonl` × 6 files | ⏳ **PENDING Day 12** |
| C-7.1.c.1 | §7.1.c Pilot (n=50) | Day 5 dev sweep | `artifacts/day5/day1_triplet_logit_prompt_repaired_v3_dev50_*.jsonl` × 6 files | ✅ verified; retained as sanity check |
| C-7.1.d.1 | §7.1.d Clipping-only regression 8.5 pp | 152/200 vs 135/200 benign block | Same as C-1.4.a | ✅ verified — **leakage-independent anchor** |
| C-7.2.1 | §7.2 Certificate empirical validity | Day 12 5-fold bootstrap | `experiments/day12_certificate_validity.csv` (pending) | ⏳ **PENDING Day 12** |
| C-7.3.1 | §7.3 EIG vs sequential vs random graph | Day 13 4 new baselines sweep | `artifacts/day13/` (pending) | ⏳ **PENDING Day 13** |
| C-7.4.1 | §7.4 Trust variant ablation | Day 14 4-tier sweep | `artifacts/day14/day14_trust_*.jsonl` (pending) | ⏳ **PENDING Day 14** |
| C-7.5.1 | §7.5 Adaptive attack survivor | Day 15 adaptive sweep | `artifacts/day15/day15_adaptive_*.jsonl` (pending) | ⏳ **PENDING Day 15** |
| C-7.6.1 | §7.6 Median latency dominated by counterfactual | `timing_ms` from JSONL, warmup discarded | `scripts/day15_efficiency_profile.py` output (pending) | ⏳ **PENDING Day 15-16** |

## Cross-cutting integrity claims

| Claim ID | Paper location | Evidence | Source-of-truth | Status |
|---|---|---|---|---|
| C-A5.1 | §5.1 Assumption A5 (grid + α pre-commitment) | SHA-256 hash of $(\Gamma, \alpha)$ committed to registry.csv before calibration | `experiments/registry.csv`; `precedentguard/certificate.py:grid_hash` | ✅ implemented; grid content pending Day 12 lock |
| C-LOO.1 | §6 protocol "leave-one-base-task-out" | `make_leave_one_base_task_out_precedent_store` excludes all variants sharing a base task id | `scripts/run_real_backbone_eval.py:277-296`; 3 regression tests | ✅ implemented Day 10; regression tests pass |
| C-LEAK.1 | §7.1 "under LOEO, top-1 retrieval leaked in 100 % of queries" | Verified from `retrieval_diagnostics` field | Day 10 audit §二 BLOCKER-1 script | ✅ verified |

---

**Maintenance:** every Day EOD, add rows for new claims introduced that day. Never let a claim ship without a row.
