# 4-Week Sprint Dashboard — AAAI 2027 Submission

**Sprint period:** 2026-06-30 → 2026-07-28
**Primary research draft:** `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md`
**Sprint mode:** No plan-mode dialogue — daily execution
**Quality target:** AAAI 2027 Oral candidate (top 5-10% of accepted papers)

---

## Critical Deadlines (Hard Wall)

| Milestone | Date | Days from sprint start |
|---|---|---|
| **Abstract submission** | **July 21, 2026** | Day 21 |
| **Full paper submission** | **July 28, 2026** | Day 28 |

---

## Three Stop-Loss Gates (BLOCKING)

| Gate | Date | Pass criteria | Fail consequence |
|---|---|---|---|
| **🚨 Gate α** | **July 4 EOD** (Day 5) | Theorems 1-3 + Prop 1 all proved AND independently verified; minimum implementation runs on toy trajectories | **STOP** sprint → retreat to NeurIPS 2027 (May 2027 deadline). Loss: 5 days. |
| **🚨 Gate β** | **July 11 EOD** (Day 12) | Certificate validity holds on dev set (empirical FNR/FPR ≤ predicted bound); 5+ baselines implemented | **STOP** sprint → retreat to NeurIPS 2027. Loss: 12 days. |
| **🚨 Gate γ** | **July 18 EOD** (Day 19) | All 3 benchmark suites complete; main tables/figures frozen | Cut content → submit to ICLR 2028 (Sep 2026 deadline). Loss: 19 days but ICLR still feasible. |

**Iron rule:** No "soldier through" past a failed gate. Every fallback venue has its own competitive timeline.

---

## Week 1 (June 30 – July 4): Theory Freeze + Minimal Implementation

### Day 1 — July 1 (Tue): Theorem proofs

| Time | Task | Deliverable |
|---|---|---|
| 09:00–11:00 | **Theorem 1** complete proof (directional intervention sensitivity) | Appendix A.1 LaTeX final |
| 11:00–12:00 | **Theorem 2** complete proof (population double-sided risk bound) | Appendix A.2 LaTeX final |
| 14:00–16:00 | **Theorem 3** complete proof (finite-sample certificate, Hoeffding + union bound) | Appendix A.3 LaTeX final |
| 16:00–17:00 | **Proposition 1** complete proof (TV-based indistinguishability LB) | Appendix A.4 LaTeX final |
| 17:00–18:00 | Send to Claude/colleague for independent mathematical review | Review request out |

**Day 1 self-check:** Every proof step justified by either (i) direct algebraic manipulation, (ii) standard inequality (Hoeffding, union bound, Pinsker), or (iii) cited prior result.

### Day 2 — July 2 (Wed): Implementation kickoff

| Time | Task |
|---|---|
| 09:00–12:00 | EIG extractor (memory + tool + retrieval node types only) |
| 14:00–16:00 | Counterfactual replay interface (ablation + control replacement) |
| 16:00–18:00 | Per-type clipping wrapper + unit tests |

### Day 3 — July 3 (Thu): Trust + certificate

| Time | Task |
|---|---|
| 09:00–12:00 | Directional trust constraint implementation (3-tier) |
| 14:00–16:00 | Certificate calculation function (input: calibration set; output: $U_{FN}, U_{FP}$) |
| 16:00–18:00 | End-to-end smoke test on 10 toy trajectories |

### Day 4 — July 4 (Fri): Related Work + Reference verification (= action C)

| Time | Task |
|---|---|
| 09:00–12:00 | Verify BibTeX for AgentSentry, AttriGuard, SMSR (2606), MemLineage |
| 14:00–17:00 | Rewrite Related Work (§2) per v0.2 — add AgentSentry, AttriGuard, MemLineage |
| 17:00–18:00 | Self-audit: remove all "first to X" overclaims |

### **🚨 Gate α — July 4 EOD**
- [ ] All 4 proofs complete and reviewed
- [ ] Min implementation runs on toy trajectories (smoke test pass)
- [ ] Related Work updated for v0.2

**FAIL → STOP. Move to NeurIPS 2027.**

---

## Week 2 (July 5 – July 11): Controlled Interventions + Core Baselines

### Day 5–6 — July 5–6 (Sat–Sun): Controlled Causal Intervention Suite

- Replayable trajectory collection: target ≥1000 paired interventions
- Each trajectory has EIG and ground-truth parent set
- 4 intervention families × 250 each: memory ins/del/repl, tool injection, retrieval manip, benign sensitive
- Balanced over: parent type, label, domain, attack family

### Day 7–8 — July 7–8 (Mon–Tue): Core baseline implementation

| Baseline | Status |
|---|---|
| Frozen backbone only (LLaMA-Guard 4) | required |
| Flattened trajectory | required |
| Raw RAG concatenation | required |
| CIP-style prompting | required |
| No-graph counterfactual | required |
| Sequential graph | required |
| Random graph (degree-matched) | required |
| **PrecedentGuard (ours)** | required |

### Day 9–10 — July 9–10 (Wed–Thu): Trust ablations + Certificate calibration

- 4 trust variants: no provenance / signature only / + lineage / full policy attestation
- Certificate calibration: find $(\rho_-, \rho_+, \theta)$ dev-optimal
- Validity check: held-out test set FNR/FPR ≤ bound (binary pass/fail per seed)

### Day 11 — July 11 (Fri): Gate β prep

- All baselines must produce numbers
- Certificate validity binary verdict on dev set

### **🚨 Gate β — July 11 EOD**
- [ ] All 8 baselines run on intervention suite
- [ ] Certificate empirically valid on dev set (≥4/5 seeds pass)
- [ ] 4 trust variants comparison numbers ready

**FAIL → STOP. Move to NeurIPS 2027.**

---

## Week 3 (July 12 – July 18): Primary Benchmarks + Adaptive

### Day 12–14 — July 12–14 (Sat–Mon): 3 benchmark suites (1 day each)

| Day | Suite | Benchmarks |
|---|---|---|
| 12 | A: Trajectory safety | AgentHarm + R-Judge |
| 13 | B: IPI | AgentDojo + InjecAgent |
| 14 | C: Memory poisoning | AgentPoison + MINJA-adaptation |

### Day 15 — July 15 (Tue): Adaptive attack + Cross-domain

- Adaptive attacker: known $\theta, c, \varepsilon$, retrieval weights
- Cross-domain: R-Judge as unseen domain → certificate validity (in)variance

### Day 16 — July 16 (Wed): Latency + Efficiency

- median, P90, P95 latency
- guard calls per decision, tokens, GPU memory
- Two-stage screening ablation

### Day 17–18 — July 17–18 (Thu–Fri): Tables + Figures freeze

| Output | Tool |
|---|---|
| Figure 1 (EIG + intervention + trust gate) | TikZ |
| Figure 2 (margin + $\rho$) | matplotlib |
| Figure 3 (certified vs empirical) | matplotlib |
| Figure 4 (parent vs non-parent counterfactual) | matplotlib |
| Tables 1, 2, 3 | LaTeX (data frozen, no cherry-pick) |

### **🚨 Gate γ — July 18 EOD**
- [ ] All 3 suites complete
- [ ] Adaptive attack data collected
- [ ] All figures + tables frozen
- [ ] Main 7-page narrative drafted

**FAIL → cut content + move to ICLR 2028.**

---

## Week 4 (July 19 – July 28): Writing + Red-team + Submission

### Day 19–20 — July 19–20 (Sat–Sun): Main paper writing

- Polish §1–§4 (already strong from v0.2)
- Write §6 Experiments narrative
- Write §7 Results (replace placeholders with real numbers)

### Day 21 — July 21 (Mon): **🛑 Abstract Submission**
- Submit verified-claims-only abstract
- 17:00 hard cutoff

### Day 22–25 — July 22–25 (Tue–Fri): Red-team review (4 reviewers, 1 per day)

| Day | Reviewer | Focus |
|---|---|---|
| 22 | Causal-inference reviewer | EIG semantics, counterfactual replay terminology |
| 23 | Security reviewer | Trust boundary, authenticated attacker, attestation assumptions |
| 24 | Learning-theory reviewer | Hoeffding application, union bound, calibration independence |
| 25 | Empirical reviewer | Leakage, baseline fairness, statistical protocol |

### Day 26 — July 26 (Sat): Integration + revision
- Address all 4 red-team feedbacks
- Final reproducibility checklist

### Day 27 — July 27 (Sun): Final audit
- Reference verification (every DOI/arXiv ID checked)
- Citation density audit
- LaTeX compile + PDF check

### Day 28 — July 28 (Mon): **🛑 Paper Submission**
- Submit by 17:00 hard cutoff
- Backup: submit by 12:00 noon to allow for system issues

---

## What to Cut if Behind Schedule

Priority order (cut from bottom first):

1. ❌ Imperfect validator full analysis (§5.5) → keep proposition statement, defer proof
2. ❌ Selective escalation (§4.7) → mention in Discussion only
3. ❌ Conformal risk control extension → 1 line in §5.4 Remark
4. ❌ Cross-domain certificate (§7.5) → keep empirical measurement, drop claim
5. ❌ Two-stage screening latency optimization → keep main latency only
6. ❌ Suite C secondary attack (MINJA-adaptation) → keep AgentPoison only
7. ❌ Figure 4 (parent vs non-parent) → move to Appendix
8. ❌ 4th trust variant (signature + lineage) → keep 3 variants

**Do NOT cut:** any of Theorems 1-3, Proposition 1, Suite A, Suite B basics, adaptive attack.

---

## Current Empirical Status

### Verified narrative on matched stop-loss slices

- The highest-value empirical conclusion is now **method-level**, not yet full-slice leaderboard-level.
- Root cause has been narrowed to the `pg_with_precedents -> base_guard` prompt-layer injection protocol for unsafe precedents.
- Retrieval diversification and logit scoring were necessary enablers, but they were not the final bottleneck.

### Verified slice evidence

- `harmless_benign 10`
  - `backbone_only`: `block=9, allow=1`, `mean_base_score=0.684639`
  - repaired `pg_with_precedents`: `block=6, allow=4`, `mean_base_score=0.684639`, `mean_s_pg=0.567950`, `mean_pg_delta=-0.116689`
  - interpretation: benign-side base inflation removed; precedent signal still active
- `harmful 10`
  - `backbone_only`: `block=10, allow=0`, `mean_base_score=0.958933`
  - repaired `pg_with_precedents`: `block=10, allow=0`, `mean_base_score=0.958933`, `mean_s_pg=0.911012`, `mean_pg_delta=-0.047921`
  - interpretation: harmful-side blocking preserved after the same repair

### Writing rule for the draft

- Write this as:
  - **"prompt-layer unsafe-precedent protocol repair removes benign-side base-score inflation without sacrificing harmful blocking on matched stop-loss slices."**
- Do **not** yet write this as:
  - full-benchmark SOTA
  - certificate-valid full-slice success
  - final Table 1 claim
- Current companion note:
  - `PrecedentGuard_AAAI27_Experiment_Narrative_Update_20260706.md`

### Immediate next execution

- Run refreshed tri-mode `10+10` under the repaired branch
- Then decide whether the branch is stable enough to promote to the next frozen experiment tier

---

## What to Add for Oral Quality (if ahead of schedule)

In priority order:

1. ✅ Causal-validation experiment: parent-vs-non-parent intervention p-value (★★★★★ Oral signal)
2. ✅ Concrete deployment scenario in §8 (★★★ significance signal)
3. ✅ Interactive certificate calculator notebook in supplementary (★★★ reproducibility signal)
4. ✅ Per-domain failure analysis in §7 (★★ rigor signal)

---

## Daily Standup Template

End each day, answer in 60 seconds:

1. What did I complete today (vs the day's deliverable list)?
2. What's the next morning's first task?
3. Am I on track for the next gate?
4. If not — what specifically slipped?

If you slip 2 consecutive days, **invoke the next stop-loss gate immediately**.

---

## Communication Protocol

When you need help during sprint:

| Issue type | Response time | What to send |
|---|---|---|
| Proof gap | <2 hours | Specific lemma + the gap |
| Implementation bug | <4 hours | Minimal reproducer |
| Experiment design question | <1 day | Decision options + your inclination |
| Writing question | <1 day | Specific paragraph + concern |

For non-urgent items: batch and send at end of day.

---

## Files

| File | Role | Update freq |
|---|---|---|
| `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md` | Primary draft | continuous |
| `Sprint_Dashboard_4Week_AAAI27.md` (this file) | Execution plan | as gates progress |
| `PrecedentGuard_AAAI27_PaperPlan_20260630.md` | Historical/citation source | frozen |
| `archive/theorem2_proof_skeleton_v1_DEPRECATED_20260630.tex` | Archived old skeleton | frozen |

---

**Sprint dashboard version:** v1.0
**Last update:** 2026-06-30 evening
**Next update:** Day 5 (Gate α verdict)
