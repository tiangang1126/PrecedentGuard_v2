# DECISIONS Log — PrecedentGuard AAAI 2027

**Purpose:** Every non-trivial architectural / methodological / scientific decision is recorded here with (a) date, (b) options considered, (c) chosen path, (d) rationale, (e) rejected alternatives.

**Discipline:** Add a decision *before* committing the code / draft change. If a decision is later reversed, add a new dated entry — do not edit the old one.

---

## 2026-06-30 D-001: Framework choice: EIG over CID

**Options:** (a) Causal Influence Diagram (CID) framing (v1.1 PaperPlan default); (b) Execution-grounded Intervention Graph (EIG) framing.
**Chosen:** (b) EIG.
**Rationale:** CID framing requires arguing causal identifiability from observed data, which LLM-agent settings do not readily support; EIG is honest about being an intervention *interface* derived from runtime instrumentation. Falsifiable via "does graph-identified parent produce larger counterfactual effect than non-parent control?"
**Rejected:** CID framing preserved to `PrecedentGuard_AAAI27_PaperPlan_20260630.md` as historical reference (SUPERSEDED).

---

## 2026-07-04 D-002: Assumption A5 extended to $(\Gamma, \alpha)$ joint pre-commitment

**Options:** (a) Original A5 only commits configuration grid $\Gamma$; (b) Extend A5 to jointly commit $\Gamma$ and the set of candidate confidence levels.
**Chosen:** (b) Joint pre-commitment.
**Rationale:** Post-hoc $\alpha$ selection is a selective-inference threat equivalent to post-hoc $\Gamma$ selection (identified by R3 in Gate α AI cold-read). If not addressed, union bound is invalidated.
**Rejected:** (a) — preserved as citation-only in §5.1 A5 explanation.
**Implementation:** `precedentguard/certificate.py:grid_hash` accepts `alpha_grid` argument; `commit_grid_hash` and `assert_grid_committed` both check joint hash.

---

## 2026-07-06 D-003: Payload-aware backend prompt rendering

**Options:** (a) Pass `content_hash` (opaque) to backend; (b) Pass raw payload text with hash as fallback.
**Chosen:** (b) Payload-aware.
**Rationale:** With opaque hashes, Llama-Guard-3-1B treated them as noise tokens and returned near-zero counterfactual delta for every parent — the mechanism could not be observed at all. Payload rendering restored per-parent delta signal.
**Rejected:** (a) — kept as deterministic identifier for A5 grid-hash logging only.
**Implementation:** `precedentguard/backends/base.py:node_prompt_text` helper.

---

## 2026-07-06 D-004: Label-balanced retrieval + asymmetric $\beta$ scaling

**Options:** (a) Vanilla top-k retrieval with symmetric $\beta$; (b) Label-balanced retrieval + asymmetric $\beta_{\text{safe}} = 2.0, \beta_{\text{unsafe}} = 0.5$.
**Chosen:** (b) — for the Day 7 sweep.
**Rationale:** Vanilla top-k skewed toward the majority label in the AgentHarm pool. Symmetric $\beta$ under skew produced net-positive $\Delta_{PG}$ on benign subset. Empirically observed on Day 5 dev slice.
**Rejected:** (a) — retained as sanity-check baseline in ablations.
**Risk noted:** Asymmetric $\beta$ tuned on dev slice is an implicit A5 grid extension. Day 10 audit MAJOR-1 flags this; Day 12 β ablation will formally commit the $\beta$ grid before calibration.

---

## 2026-07-10 D-005: LOEO → LOBTO precedent split protocol

**Options:** (a) Leave-one-example-out (LOEO); (b) Leave-one-base-task-out (LOBTO).
**Chosen:** (b) LOBTO — as the paper's primary evaluation protocol from Day 12 onward.
**Rationale:** Day 10 audit BLOCKER-1: LOEO leaks 100 % of top-1 retrievals to same-base-task variants in AgentHarm-public (each base task has 4 near-duplicate variants). Under LOEO the reported FPR improvement mixes the mechanism with retrieval leakage. LOBTO strictly excludes every AgentHarm variant sharing the query's base task id.
**Rejected:** (a) — kept in §7.1.a as reference-only "preliminary sweep" with explicit leakage disclosure.
**Implementation:** `scripts/run_real_backbone_eval.py:make_leave_one_base_task_out_precedent_store`; old function renamed and now raises `RuntimeError`. 3 regression unit tests added.

---

## 2026-07-10 D-006: Subgraph signature computation activated

**Options:** (a) Leave `subgraph_signature=""` (Day 7 state); (b) Compute node-type multiset signature per trajectory + query.
**Chosen:** (b).
**Rationale:** Day 10 audit BLOCKER-2: with empty signatures, `SimplePrecedentStore.raw_score` short-circuited to $s_{\text{graph}} = 0$, meaning $\lambda_g = 0.2$ contribution was empirically zero across all 400 rows. Paper §4.3 formula "combines semantic and structural similarity" was decoupled from implementation.
**Rejected:** (a) — would require downgrading paper claim, weakening §2.4 CIP comparison.
**Implementation:** `_trajectory_subgraph_signature` sorted node-type multiset; `guard._query_subgraph_signature` derives query-side signature from EIG mutable ancestors.
**Note:** Structural signature is a proxy, not a fingerprint. If Day 12 rerun shows negligible additional value from $\lambda_g$, we may reduce it to $\lambda_g = 0.05$ and rebalance.

---

## 2026-07-10 D-007: Trust variant flag added

**Options:** (a) Hardcoded `policy_attested` provenance for all precedents; (b) `--trust-variant` CLI flag with 4 tiers.
**Chosen:** (b).
**Rationale:** Contribution #2 "trust-separated" requires empirical ablation across the 3-tier trust taxonomy (unsigned / authenticated / policy-attested). Day 10 audit MAJOR-4 flagged that no such ablation had been run. `--trust-variant` supports {no_provenance, signature_only, lineage, policy_attested}.
**Implementation:** `scripts/run_real_backbone_eval.py:_apply_trust_variant`; unit test `test_trust_variant_no_provenance_is_unattested`.

---

## 2026-07-11 D-008: Contribution #3 precise wording

**Options:** (a) "Double-sided certification" (v0.2 default); (b) "Class-conditional two-sided certificates over heterogeneous trajectory-evidence channels."
**Chosen:** (b).
**Rationale:** R4 M11 (Gate α AI cold-read) identified that (a) risks being read as "we do double-sided, SMSR does single-sided" without justifying novelty. (b) makes precise:
- *class-conditional* — separate $U_{FN}, U_{FP}$ under class-conditional Hoeffding
- *two-sided* — controls both FNR and FPR
- *heterogeneous trajectory-evidence channels* — memory + retrieval + observation + tool + precedent, unlike SMSR's single retrieval channel
- *on a frozen guard's decision layer* — not on end-agent behavior, which is where CIP operates
**Rejected:** (a) — considered "overclaim" per R4.

---

## 2026-07-11 D-009: §7.1 restructuring to §7.1.a-d

**Options:** (a) Keep single §7.1 with LOEO n=200 numbers; (b) Split into 7.1.a (LOEO reference), 7.1.b (LOBTO primary), 7.1.c (n=50 pilot), 7.1.d (leakage-independent anchor).
**Chosen:** (b).
**Rationale:** Honest disclosure of leakage discovery, distinguishes preliminary from primary, and elevates the clipping-only regression as the paper's cleanest leakage-independent empirical anchor.
**Rejected:** (a) — would require either omitting Day 7 data (loses reproducibility trail) or presenting LOEO numbers as headline (violates CLAUDE.md §11).

---

## 2026-07-12 D-010: Sprint gate strategy — accept honest LOBTO judgment

**Options:** (a) If LOBTO Day 12 rerun shows PG-full FPR $\ge$ backbone, silently drop that result and retry with different retrieval config; (b) Accept the LOBTO result as the paper's headline and stop-loss to NeurIPS 2027 if it fails.
**Chosen:** (b).
**Rationale:** CLAUDE.md §2 forbids silent config retries. LOBTO with the pre-committed grid is the reproducible experiment; if PG fails under LOBTO, the paper's directional-trust mechanism is not supported and cannot be defended under adversarial review.
**Rejected:** (a) — would constitute cherry-picking and would be caught by any competent reviewer.

---

## 2026-07-12 D-011: Certificate grid tightening + dual-threshold strategy

**Options:** (a) Keep the runtime-default certificate grid ($\varepsilon_\pm = 1.0$, $\theta = 0.5$, $m_k = 1$ for every type); (b) Tighten the outer clip to $\varepsilon_\pm = 0.05$, exclude observation and tool-return from the attack budget, and commit a **dual-threshold** primary/secondary grid where the primary certificate uses $\theta = 0.7$ and the secondary uses $\theta = 0.5$.

**Chosen:** (b).

**Rationale:** A dry run of `scripts/day12_certificate_empirical_validity.py` on the Day 7 LOEO data with configuration (a) yielded $U_{FN} = U_{FP} \approx 1.107 > 1$ on every seed — a **vacuous certificate** that is scientifically indistinguishable from having no certificate. The root cause is that AgentHarm-public benign $S_{PG}$ concentrates in $[0.4, 0.9]$; under $\theta = 0.5$ the margin $M_0 = \theta - S$ is small or negative for the vast majority of benign examples, so any $\rho_+ \le 1.0$ makes $\hat R_{FP} \approx 1$.

Quantile analysis (`experiments/day12_threshold_sensitivity.md`) shows that only $(\theta = 0.7, \varepsilon_\pm = 0.05)$ produces a non-vacuous FP-side certificate ($U_{FP} \le 0.42$) within the AgentHarm-public benign score distribution. Under this grid, all three modes (`backbone_only`, `clipping_only`, `pg_with_precedents`) achieve non-vacuous certificates on both sides, with PG-full producing the largest certificate gap on the FP side (empirical 0.13 vs predicted 0.42).

**Dual-threshold decoupling:**
- §7.1 primary metric (block-rate comparison with backbone) uses $\theta = 0.5$ — matches the backbone-comparison convention adopted by AgentHarm and prior guard papers, so numbers are directly comparable.
- §7.2 certificate is reported under $\theta = 0.7$ — the operationally-calibrated threshold that makes the class-conditional two-sided guarantee non-vacuous on AgentHarm-public.
- The secondary grid point ($\theta = 0.5, \varepsilon_\pm = 0.15$) is included in the pre-committed grid so that §7.2's threshold-sensitivity subsection can report both certificates under the same A5 hash.

**Rejected:** (a) — would require reporting a certified defense whose certificate is vacuous, violating CLAUDE.md §2 and §10.

**Implementation:** `scripts/day12_certificate_empirical_validity.py:build_certificate_grid()`; committed grid hash `0f5b73a9c02e9a5a59e68a43e0dfa87ad06de9fc7957562758be33d1975ceaf6` recorded in `experiments/registry.csv` under tag `certificate_grid_day12`.

**Risk:** the LOBTO rerun on Day 13 may shift the benign $S_{PG}$ distribution enough to change whether $(\theta = 0.7, \varepsilon_\pm = 0.05)$ remains non-vacuous. If the shift makes $\hat R_{FP} \ge 0.5$ on the LOBTO calibration split, we must either (i) further tighten $\varepsilon_\pm$ within the pre-committed grid or (ii) commit a wider grid **before** rerunning calibration. Post-hoc grid retuning is not permitted under A5.

---

## Placeholder for future decisions

**Day 12 planned decisions:** LOBTO primary result direction; β grid values to commit; Gate β verdict.
**Day 15 planned decisions:** Gate γ verdict; Suite B vs Suite C selection.
**Day 20 planned decisions:** Human independent reviewer status; camera-ready claim scope.

---

**Maintainer:** Add entries in ISO date order. Any decision that materially affects §1.5 Contributions, §5 Theorems, §7 Results tables, or §8 Discussion must have an entry here before the corresponding draft change.
