# RESEARCH_SPEC — PrecedentGuard

**Purpose:** the load-bearing problem statement, research questions, hypotheses, contributions, and success/failure criteria that the AAAI 2027 submission is judged against. Any change to §2–§4 of the paper must be reflected here first.

---

## 1. Problem

LLM agents that browse, write files, execute code, and call external APIs make consequential decisions that depend on trajectory-level evidence — retrieved memories, external observations, tool arguments, tool returns, and past precedents — much of which is **mutable and attacker-controllable**. A runtime safety guard that receives poisoned or misleading trajectory evidence can be induced to (a) allow an unsafe action that would have been blocked under clean evidence, or (b) block a benign action that would have been allowed under clean evidence.

Existing runtime safeguards fall into three families, each with structural gaps against this failure mode:

- **Static / pointwise guards** (Llama Guard, ShieldGemma, Granite Guardian, WildGuard) classify each step as if i.i.d. text and do not model dependencies among trajectory components.
- **Trajectory-aware guards** (TRACES, Trajectory Guard, GuardAgent, AGrail, Spider-Sense, AgentDoG) model dependencies but provide no formal bound on how a bounded intervention on trajectory evidence changes class-conditional error rates.
- **Certified memory defenses** (SMSR) certify attack-success rate under bounded poisoning of a single retrieval channel, but do not simultaneously control benign over-blocking (false positives) and do not extend to heterogeneous evidence channels beyond persistent memory.

## 2. Research questions

**RQ1.** Can a frozen runtime guard obtain *class-conditional* guarantees on both false-negative and false-positive rates under bounded interventions on heterogeneous trajectory evidence (memory / retrieval / observation / tool return / precedent)?

**RQ2.** Does a runtime-instrumented execution graph (EIG), constructed from data-flow and control dependencies rather than inferred from text alone, produce controlled counterfactual effects that a randomised or sequential graph does not?

**RQ3.** Does the paper's tiered trust taxonomy (unsigned / authenticated / policy-attested) empirically translate into monotone effects on the aggregated evidence contribution — i.e., is authentication necessary but not sufficient for safety, and is semantic policy attestation the load-bearing signal?

**RQ4.** Under an adaptive attacker that knows the clipping caps, retrieval rule, and threshold, does the certificate remain empirically valid at the calibrated budgets?

## 3. Hypotheses (falsifiable)

- **H1 (RQ1).** Under LOBTO precedent split, a properly calibrated $(\Gamma, \alpha)$ grid yields non-vacuous $U_{FN} < 0.5$ AND $U_{FP} < 0.5$ that are empirically satisfied on $\ge 4/5$ bootstrap seeds on the AgentHarm-public dev split at the (theta = 0.7, eps = 0.05) primary grid point.
- **H2 (RQ2).** On a controlled 1000-example intervention suite, a non-parent counterfactual has strictly smaller mean absolute score effect than a graph-identified parent counterfactual ($p < 0.01$, Wilcoxon signed-rank).
- **H3 (RQ3).** Precedent contributions from the `policy_attested` trust tier can move $S_{PG}$ downward on benign examples; the `no_provenance`, `signature_only`, and `lineage` tiers cannot, and their pg_delta on benign examples is bounded below by 0 on $\ge 95 \%$ of the sample.
- **H4 (RQ4).** An adaptive attacker with knowledge of $(c^\pm, w_i, \theta)$ and a query budget of 100 per trajectory raises empirical FNR by no more than $t_{FN}$ (the Hoeffding tail) beyond the clean-attack FNR.

## 4. Contributions (v0.2)

1. **Execution-grounded intervention modeling.** Formulate runtime guarding over an EIG whose nodes correspond to instrumented trajectory evidence.
2. **Trust-separated counterfactual calibration.** A training-free wrapper for frozen guards that measures evidence influence through counterfactual replay, separates authenticity from semantic authorization, and applies directional clipping so that unauthorised evidence cannot lower the risk score.
3. **Class-conditional two-sided certificates over heterogeneous trajectory-evidence channels.** A Directional Intervention Sensitivity Bound (Theorem 1) plus finite-sample class-conditional upper bounds $U_{FN}, U_{FP}$ (Theorem 3) that hold jointly at level $1 - \alpha$ under an A5 pre-committed calibration grid, over five channels simultaneously.
4. **Causality- and trust-focused evaluation.** Controlled trajectory interventions with known modified nodes; execution / random / sequential / learned / oracle graph comparison; unsigned / authenticated / semantic-attested variants; unsigned, authenticated, adaptive, and cross-domain attacks.

## 5. Success criteria

The submission is judged successful (Poster-defensible) if:

- H1 is empirically confirmed on ≥ 1 backbone (Llama-Guard-3-1B primary) at the pre-committed grid.
- H3 is empirically confirmed (`policy_attested` strictly outperforms `no_provenance` on benign FPR at $\theta = 0.5$, Fisher $p < 0.05$).
- ≥ 3 baselines from {backbone_only, clipping_only, flattened_trajectory, raw_rag_concat, cip_style, sequential_graph, random_graph} are reported with numbers.
- Certificate validity holds on ≥ 4/5 bootstrap seeds on the primary grid point.
- Suite A (AgentHarm-public) is complete; Suite B or Suite C has at least PG-full + backbone_only reported.

Oral-candidate if additionally:

- H1 confirmed across ≥ 2 backbones (Llama-Guard + ShieldGemma or Granite).
- H2 empirically confirmed ($p < 0.01$).
- H4 confirmed with adaptive attack.
- ≥ 1 human independent mathematical review completed.

## 6. Failure criteria (STOP-LOSS)

Any of the following triggers immediate retreat to NeurIPS 2027 / ICLR 2028:

- Under LOBTO, PG-full benign FPR $\ge$ backbone benign FPR at $\theta = 0.5$ on the primary backbone (mechanism unsupported).
- Certificate violates on $\ge 3/5$ bootstrap seeds under the pre-committed grid (theory not empirically operational).
- Any BLOCKER-level scientific integrity issue is discovered after Day 21 (abstract submission).

## 7. Out of scope

- OOD generalization (Paper 4 in the doctoral trajectory).
- Multi-agent collusion / emergent risk (Paper 3+ or later).
- Intent hijacking (declared out-of-scope in §3.3 threat model).
- Cross-domain certificate transfer (reported empirically only; no formal claim).

## 8. Evidence anchors

The paper stands on these three empirical anchors, in decreasing order of independence from any single design choice:

1. **Clipping-only over-blocking regression** (§7.1.d): benign block-rate 67.5 % → 76.0 % on AgentHarm-public with Wilson [+2.5, +15.0] pp. Independent of LOBTO/LOEO because this mode does not query the precedent store.
2. **LOBTO primary result** (§7.1.b, pending Day 13): PG-full benign FPR under the strict LOBTO protocol.
3. **Certificate empirical validity** (§7.2, pending Day 13): ≥ 4/5 seeds on the primary $(\theta = 0.7, \varepsilon_\pm = 0.05)$ grid point.

If evidence #1 stays and #2 confirms the mechanism direction, we have a Poster-defensible paper regardless of #3.

If #1 stays and #3 confirms non-vacuous certificates, we have an Oral-candidate paper regardless of #2 magnitude.

If all three land, the paper is submission-ready as an Oral-candidate.
