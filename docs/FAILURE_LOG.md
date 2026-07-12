# FAILURE_LOG — PrecedentGuard

**Purpose:** every failed hypothesis, misconfiguration, or dead-end during the sprint, so that (a) later iterations do not repeat them and (b) the paper's §9 Limitations reflects an honest accounting.

**Discipline:** log a failure BEFORE moving on. If it turns out later that the failure was actually a positive, add a follow-up entry pointing back.

---

## 2026-07-01 F-001: Corollary 1 DPI direction inverted

**Symptom:** Corollary 1 as originally stated claimed "adding trusted evidence increases TV distance"; this is the wrong direction — the data-processing inequality says marginalisation decreases TV.

**Root cause:** notational sloppiness in §5.6.

**Fix:** rewrote to make the projection channel $\pi: (O, Z) \to O$ explicit and re-derived the direction (marginalisation shrinks TV, so *withholding* trusted evidence cannot help).

**Lesson:** every application of DPI must name the specific channel; abbreviation "add Z" is unsafe.

---

## 2026-07-04 F-002: `hash-based` prompt rendering returned zero counterfactual delta

**Symptom:** on the first real-backbone smoke test (Day 6 morning), every parent produced $\delta \approx 0$ under counterfactual replay. The mechanism was structurally invisible.

**Root cause:** the backend was receiving `content_hash` tokens (16-hex opaque strings) rather than the raw payload text. Llama-Guard-3-1B treated the hashes as noise and produced near-identical scores for present vs. absent nodes.

**Fix:** added `node_prompt_text` helper that prefers raw payload text, with `content_hash` as fallback. Payload-aware rendering restored per-parent delta signal on 100/100 dev examples.

**Lesson:** any hash-based identifier passed to an LLM through prompt context must be verified to actually affect the output. Do NOT trust "the pipeline runs" as evidence that the mechanism is exercised — verify per-parent delta magnitude before running the sweep.

---

## 2026-07-05 F-003: Vanilla top-k retrieval skewed toward majority-label

**Symptom:** on the AgentHarm public precedent pool, vanilla top-2 retrieval systematically returned two unsafe capsules for benign queries (because unsafe examples had higher raw similarity to the retrieval query text under token Jaccard).

**Root cause:** the AgentHarm training pool is label-imbalanced and topic-imbalanced; text similarity alone favors the majority-label cluster.

**Fix:** introduced `label_balanced` retrieval that from the top-$K$ probe pool selects up to $\lfloor top_k/2 \rfloor + 1$ per label class before filling remaining slots by raw similarity. Enforced only when both classes are present; degrades gracefully to vanilla top-k otherwise.

**Lesson:** retrieval is *never* label-neutral when the pool is imbalanced. Every retrieval-based defense needs to inspect the label distribution of its returns.

---

## 2026-07-06 F-004: Symmetric $\beta = 1$ inflated benign FPR

**Symptom:** under label-balanced retrieval with $\beta_{\text{safe}} = \beta_{\text{unsafe}} = 1$, benign FPR still ran ahead of backbone (mean $\Delta_{PG}$ = +0.03 on benign).

**Root cause:** the frozen backbone was systematically more conservative on benign queries than on unsafe ones; a symmetric $\beta$ under-weighted the negative-direction signal that a safe-audited precedent should produce.

**Fix:** asymmetric $\beta_{\text{safe}} = 2.0, \beta_{\text{unsafe}} = 0.5$ on the AgentHarm-public dev split. This is documented as a hyperparameter fit and now enters the A5 grid pre-commitment (D-004).

**Lesson:** asymmetric operational cost demands asymmetric aggregation weights; symmetric-by-default is not neutral.

---

## 2026-07-10 F-005 (BLOCKER): LOEO precedent split leaked near-duplicates

**Symptom:** on the Day 7 n=200 sweep, `retrieval_diagnostics.top_matches[0].capsule_id` shared the query's AgentHarm base task id in 400/400 queries (100.0 %).

**Root cause:** `make_leave_one_out_precedent_store` filtered by exact `row["id"]`, e.g. excluded "1-1" only, leaving "1-2", "1-3", "1-4" in the pool. AgentHarm-public generates ~4 near-duplicate variants per base task (`{base}-{variant}`), so LOEO admits a semantic near-clone of the query.

**Fix:** replaced with `make_leave_one_base_task_out_precedent_store` that filters by `id.split("-")[0]`. Old function renamed and now raises `RuntimeError` to prevent silent regression. Added 3 regression unit tests.

**Impact on paper:** Day 7 n=200 numbers demoted from primary result to "reference only" in §7.1.a; the LOBTO rerun scheduled for Day 13 is the true primary result (§7.1.b). Clipping-only regression in §7.1.d is unaffected because that mode does not query the store.

**Lesson:** for benchmark datasets that group prompt variants under a shared base task id, **variant-level leave-one-out is not sufficient**. Always audit retrieval leakage by matching query base-id against retrieved capsule base-id.

---

## 2026-07-10 F-006 (BLOCKER): Graph similarity channel empirically zero

**Symptom:** on the Day 7 n=200 sweep, `retrieval_diagnostics.top_matches[*].graph_similarity == 0` for 400/400 rows.

**Root cause:** `make_precedent_store` never set `subgraph_signature` on the `PrecedentCapsule`, so `SimplePrecedentStore.raw_score` short-circuited to $s_{\text{graph}} = 0$ under `if capsule.subgraph_signature or query_subgraph_signature`. Paper §4.3 claimed "combines semantic and structural similarity" while the structural channel contributed zero.

**Fix:** added `_trajectory_subgraph_signature` (sorted node-type multiset) and `make_query_subgraph_signature`; wired to `PrecedentGuard.decide(query_subgraph_signature=...)` through a new `_query_subgraph_signature` helper on `PrecedentGuard`.

**Lesson:** any weighted combination in a paper's formal formula must be verified to have non-zero contribution from every weighted term. Zero-weight terms are worse than absent terms — they signal a mismatch between the paper's structural claim and the deployed system.

---

## 2026-07-12 F-007: Certificate grid initially vacuous

**Symptom:** Day 12 dry run of `scripts/day12_certificate_empirical_validity.py` on Day 7 LOEO data returned $U_{FN} = U_{FP} \approx 1.107 > 1$ on every seed — a vacuous certificate that would have caused desk reject if reported as headline.

**Root cause:** the default grid used $\varepsilon_\pm = 1.0$, $m_k = 1$ for every type, $\theta = 0.5$. This drove $\rho_\pm = 1.0$ under Theorem 1's asymmetric sensitivity bound; under $\theta = 0.5$ the AgentHarm benign $S_{PG}$ concentrates in $[0.4, 0.9]$, so nearly every benign margin $M_0 = \theta - S$ was inside $[-0.4, +0.1]$ — well below $\rho_+ = 1.0$ — pushing $\hat R_{FP}$ to essentially 1.

**Fix:** committed a dual-threshold grid (D-011). Primary certificate: $(\theta = 0.7, \varepsilon_\pm = 0.05)$ with $m_{\text{obs}} = m_{\text{tool}} = 0$. This produces non-vacuous $U_{FN} \le 0.28$ and $U_{FP} \le 0.42$ on the Day 7 sample, and 5/5 seeds valid on all three modes.

**Lesson:** certificate grid selection must be validated dry-run *before* committing to the LOBTO sweep. The default parameters of a runtime system are almost never the right parameters for a formal certificate.

---

## Placeholder for future failures

**Day 13 candidates to watch:**
- LOBTO PG-full may show substantially reduced benign FPR improvement vs LOEO (mechanism strength attributable to leakage vs to directional trust).
- ShieldGemma-2B and Granite-Guardian-3.2-2B may have different score distributions than Llama-Guard, breaking the primary certificate grid on the FP side.
- Sequential / random graph baselines may not produce statistically significant degradation (if AgentHarm trajectories are too short to expose graph structure differences).

**Day 15 candidates to watch:**
- Adaptive attack may exceed the certified budget on 1-2 seeds even without violating theorem; report honestly rather than tune caps.
- AgentPoison subset loader may have variant-level leakage analogous to F-005; check base task id semantics upfront.
