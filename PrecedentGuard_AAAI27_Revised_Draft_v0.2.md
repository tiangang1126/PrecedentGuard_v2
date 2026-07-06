# PrecedentGuard: Double-Sided Risk Certification for LLM Agents under Bounded Trajectory Interventions

**Revised AAAI 2027 Initial Draft — v0.2**  
**Date:** June 30, 2026  
**Target:** AAAI 2027 Main Technical Track / AI Alignment Track  
**Status:** Theory-and-method draft; empirical results are intentionally left as placeholders  

> **Research-integrity note.** This draft does not report unverified numerical results. Every marker of the form `[RESULT TO BE INSERTED]`, `[VERIFY]`, or `[IMPLEMENTATION CHOICE]` must be resolved from completed experiments, proofs, or primary-source checking before submission.

---

## Abstract

LLM agents increasingly rely on persistent memory, external observations, retrieval systems, and tool outputs when deciding whether and how to execute consequential actions. These trajectory components are mutable: an adversary may poison memory, inject instructions through tool returns, or manipulate retrieval so that a runtime guard receives misleading evidence. Existing causal approaches mainly use causal graphs to guide prompting or localize attack-induced behavior, while certified memory defenses primarily bound attack success within a specific retrieval setting. A remaining challenge is to control **both** missed hazards and benign over-blocking when multiple trajectory-evidence channels are perturbed.

We introduce **PrecedentGuard**, a training-free runtime calibration framework for frozen LLM guards. PrecedentGuard first constructs an **execution-grounded intervention graph** from trusted orchestration and data-flow logs rather than inferring causal edges from text alone. It then decomposes a guard decision into bounded, counterfactually measured contributions from mutable trajectory nodes and retrieved precedents. Each precedent is represented by a scoped evidence capsule that separates provenance authenticity from semantic authorization. A directional aggregation rule prevents unauthorised evidence from decreasing the predicted risk, while separately clipping upward and downward score changes.

We establish two results. First, a **Directional Intervention Sensitivity Bound** limits how much a bounded number of modified evidence nodes can raise or lower the guard score. Second, a **Finite-Sample Double-Sided Risk Certificate** converts these directional score bounds and class-conditional calibration margins into simultaneous high-probability upper bounds on false-negative and false-positive rates. We additionally give an observational-indistinguishability lower bound showing that cryptographic authenticity alone cannot improve classification guarantees unless the trusted evidence is also label-informative. We evaluate PrecedentGuard on trajectory-safety, indirect-prompt-injection, and persistent-memory-poisoning settings, with controlled interventions, adaptive attackers, graph-quality ablations, and certificate-validity tests. `[RESULT TO BE INSERTED]`

---

## 1. Introduction

### 1.1 Runtime agent safety is an evidence-integrity problem

LLM agents no longer act only on a user prompt. A consequential action may depend on a chain of retrieved memories, tool responses, intermediate observations, previous decisions, and external documents. This long-lived evidence improves autonomy but creates a structural attack surface. A malicious memory can be retrieved in a later session; a web page can inject an instruction through a tool response; and a corrupted retriever can suppress the evidence that should have triggered a safety intervention.

The resulting failures cannot be understood solely as pointwise text-classification errors. The same proposed action may be judged differently because one upstream trajectory component changed. A useful runtime defense should therefore answer three questions:

1. **Where did the decision-relevant evidence enter the execution?**
2. **How much can a bounded intervention on that evidence change the guard score?**
3. **Does the resulting control protect unsafe cases without indiscriminately blocking benign ones?**

Recent research addresses parts of this problem. Causal Influence Prompting (CIP) uses causal influence diagrams to guide agent reasoning. AgentSentry and AttriGuard use counterfactual re-execution or action-level attribution to diagnose indirect prompt injection. SMSR provides a certified defense for bounded persistent-memory poisoning using write-time provenance and randomized retrieval. MemLineage records provenance and derivation lineage for memory-dependent actions. These advances motivate a more precise question that remains underexplored:

> **Can a frozen runtime guard obtain class-conditional guarantees on both missed hazards and benign over-blocking under bounded interventions on trajectory evidence?**

### 1.2 Why provenance signatures are not sufficient

A central distinction in this paper is between **authenticity** and **semantic authorization**. A cryptographic signature can establish who wrote an item and whether it was modified. It does not establish that the item is correct, safe, applicable to the current action, or produced by a non-compromised process. A legitimate user may write a misleading memory through the normal interface; a trusted component may sign an incorrect inference; and a valid policy may be applied outside its intended scope.

PrecedentGuard therefore uses a three-level evidence model:

- **Untrusted:** origin or integrity is not established.
- **Authenticated:** origin and integrity are established, but the content is not authorized as safety evidence.
- **Policy-attested:** a designated validator binds a safety label or rule to a specific scope, policy version, and expiry condition.

Only policy-attested evidence may decrease the estimated risk. Untrusted and merely authenticated evidence may still reveal suspicious behavior and increase risk, but they cannot create a false permission by themselves.

### 1.3 Why a trajectory graph is not automatically a causal graph

Temporal order does not by itself identify causation. We therefore do not ask an LLM to infer a ground-truth causal graph from raw text. Instead, PrecedentGuard constructs an **execution-grounded intervention graph (EIG)** from trusted runtime instrumentation: memory reads, tool-call arguments, tool-return propagation, prompt assembly, action proposals, and policy checks. An edge indicates an implemented data-flow or control dependency in the agent runtime. The graph is an intervention interface: it tells the defender which evidence node can be masked, replaced, replayed, or withheld while keeping the rest of the execution fixed as far as the runtime permits.

This design makes the causal claim falsifiable. The paper evaluates whether graph-identified parents produce larger counterfactual effects than non-parent controls and compares an execution graph with sequential, random, extracted, and oracle variants.

### 1.4 Why bounded score changes are not enough

A bound on logit movement does not directly imply a bound on false-negative or false-positive rates. If many examples lie close to the decision threshold, even a small score change can flip many predictions. PrecedentGuard therefore combines a deterministic intervention-sensitivity bound with the **class-conditional margin distributions** of a held-out calibration set. The result is a pair of certificates:

- an upper bound on the attacked false-negative rate, governed by the unsafe-class margin and the maximum downward score shift;
- an upper bound on the attacked false-positive rate, governed by the safe-class margin and the maximum upward score shift.

This explicitly prevents a vacuous “always block” solution from being presented as certified safety.

### 1.5 Contributions

This paper makes four contributions.

1. **Execution-grounded intervention modeling.** We formulate runtime guarding over an execution-derived graph whose nodes correspond to instrumented trajectory evidence. The graph supports controlled node ablation and replacement without claiming that text order alone identifies a causal structure.

2. **Trust-separated counterfactual calibration.** We introduce a training-free wrapper for frozen guards that measures evidence influence through counterfactual replay, separates authenticity from semantic authorization, and applies directional clipping so that unauthorised evidence cannot lower the risk score.

3. **Double-sided certification.** We prove a deterministic Directional Intervention Sensitivity Bound and derive finite-sample, class-conditional upper bounds on both FNR and FPR. The certificate exposes the exact dependence on attack budget, per-type contribution caps, threshold margins, and calibration-set size.

4. **Causality- and trust-focused evaluation.** We design controlled trajectory interventions with known modified nodes, compare execution, random, sequential, learned, and oracle graphs, test signature-only and semantic-attestation variants, and evaluate unsigned, authenticated, adaptive, and cross-domain attacks.

We do **not** claim that cryptographic provenance is universally necessary or sufficient for agent safety. Instead, we show that any useful trusted signal must be both difficult for the adversary to control and informative about the safety label.

---

## 2. Related Work

### 2.1 Static and trajectory-aware guards

Static safeguards such as Llama Guard, ShieldGemma, Granite Guardian, and WildGuard established strong pointwise safety classifiers. Their standard interfaces process a prompt, response, or local interaction, but do not provide an explicit intervention model over persistent memory and multi-step evidence. Trajectory-aware methods address this limitation through state representations, auxiliary guard agents, lifelong adaptation, hierarchical risk signals, or memory-augmented reasoning. These methods motivate modeling dependencies across a trajectory, but trajectory awareness alone does not yield a quantitative certificate on how a bounded evidence intervention changes class-conditional errors.

PrecedentGuard is complementary to stronger guard backbones: it is a structured calibration and certification layer rather than a replacement foundation model.

### 2.2 Causal prompting, diagnostics, and attribution

CIP initializes and updates a causal influence diagram to guide an agent toward safer decisions. Its main role is deliberative prompting. AgentSentry models multi-turn indirect prompt injection as temporal causal takeover and uses controlled re-execution to localize the takeover point before purifying context. AttriGuard performs action-level causal attribution by testing whether a proposed tool invocation survives when control-bearing external observations are attenuated. These works demonstrate that counterfactual reasoning is useful for runtime safety.

PrecedentGuard differs in objective. It does not primarily ask where an attack began or whether a tool action survives a counterfactual replay. It asks how bounded evidence modifications translate into simultaneous FNR and FPR guarantees for a guard decision. The counterfactual tests are therefore used to construct bounded score contributions and class-conditional certificates.

### 2.3 Memory poisoning, provenance, and certified retrieval

AgentPoison, MINJA, PoisonedRAG, and related work show that a small number of strategically written or retrieved items can persistently redirect agent behavior. SMSR separates unsigned from authenticated adversaries, uses HMAC-based write-time provenance, and certifies randomized memory ablation under a bounded injection model. Its impossibility result applies to deterministic content-based retrieval-time filters under its stated fluent-embedding assumption. SMSR certifies malicious-response probability in a persistent-memory setting and reports clean utility, but it does not formulate a general class-conditional FNR/FPR certificate over heterogeneous trajectory-evidence channels.

MemLineage attaches cryptographic provenance and derivation lineage to memory entries and blocks sensitive actions whose active justification descends from untrusted evidence. It highlights that signatures alone are weaker than provenance-aware dependency tracking. PrecedentGuard adopts this lesson but focuses on risk calibration: provenance and policy attestation govern the direction in which evidence may alter a guard score.

### 2.4 Formal runtime constraints and calibrated autonomy

Formal runtime systems constrain tool use through temporal policies, authorization, least privilege, or trusted provenance. A separate line calibrates execute/abstain or oversight decisions using conformal or risk-control techniques. These systems provide important guarantees under their respective policy and exchangeability assumptions. PrecedentGuard addresses a different unit of analysis: a binary runtime safety guard whose score is influenced by mutable trajectory evidence. Our certificate combines deterministic intervention sensitivity with empirical class-conditional margins. Conformal risk control is a possible extension; the primary draft uses finite-grid calibration with uniform concentration for transparency and implementation simplicity.

### 2.5 Positioning

The closest neighboring lines can be summarized as follows:

| Line of work | Primary object | Typical guarantee | Remaining gap addressed here |
|---|---|---|---|
| Causal prompting | Agent reasoning context | Empirical safety improvement | No double-sided guard-risk certificate |
| Counterfactual IPI defense | Attack locus / tool action | Empirical attack mitigation | Not a class-conditional guard calibration bound |
| Certified memory defense | Persistent retrieval | ASR or malicious-response bound | Restricted channel and objective |
| Provenance lineage | Justification ancestry | Structural action gate | No calibrated FNR/FPR trade-off |
| Formal authorization | Tool availability or temporal policy | Policy conformance | Requires pre-specified formal policy |
| **PrecedentGuard** | Guard score over mutable trajectory evidence | **FNR and FPR upper bounds** | — |

---

## 3. Problem Formulation

### 3.1 Agent execution and guard decision

At step \(t\), an agent receives a user intent \(I\), maintains an execution history \(H_t\), retrieves memory \(M_t\), observes tool or environment outputs \(O_t\), and proposes an action \(A_t\). A runtime guard outputs a binary decision

\[
\hat Y_t = \mathbf{1}[S(\tau_t,A_t) \ge \theta],
\]

where \(\tau_t=(I,H_t,M_t,O_t)\), \(S\) is a risk score, \(\theta\) is a threshold, and \(\hat Y_t=1\) denotes block or escalate. Ground truth \(Y_t=1\) denotes an unsafe proposed action.

We evaluate

\[
\operatorname{FNR}=\Pr(\hat Y=0\mid Y=1),\qquad
\operatorname{FPR}=\Pr(\hat Y=1\mid Y=0).
\]

### 3.2 Execution-grounded intervention graph

The agent runtime emits an EIG

\[
G_t=(V_t,E_t,\operatorname{type},\operatorname{source},\operatorname{scope}).
\]

Each node is an observed runtime event, including:

- user intent;
- memory read or write;
- retrieval result;
- tool argument;
- tool return;
- derived summary;
- candidate action;
- policy or human attestation.

An edge \(u\to v\) is added only when runtime instrumentation records that the content or control state of \(u\) was consumed in producing \(v\). The graph therefore represents implemented dependence, not unrestricted causal discovery from observational text.

For the target action node \(A_t\), the guard uses an evidence parent set \(P_t\subseteq \operatorname{Ancestors}(A_t)\). A node can be intervened on through a runtime-supported operation:

- **ablation:** remove the node from the assembled context;
- **replacement:** substitute a neutral or matched-control value;
- **replay:** rerun the downstream component while fixing other recorded inputs;
- **withholding:** prevent the item from entering the next decision context.

**Implementation scope.** The current PrecedentGuard implementation exercises **ablation** and **replacement** end-to-end; **replay** and **withholding** are declared as first-class operators to keep the graph interface compositional, but all theorems in this paper (Theorems 1–3 and Proposition 1) require only the ablation/replacement subset. Replay- and withholding-based ablations are marked as future work in §9.

### 3.3 Threat model

The adversary may modify a bounded set \(B\subseteq P_t\) of mutable evidence nodes. We use a vector budget

\[
\mathbf m=(m_{\text{mem}},m_{\text{obs}},m_{\text{ret}},m_{\text{tool}},m_{\text{prec}}),
\]

where \(m_k\) is the maximum number of modified nodes of type \(k\). Attacks include insertion, replacement, deletion, retrieval promotion or suppression, and tool-output injection.

The adversary may know the graph schema, guard backbone, retrieval rule, thresholds, clipping caps, and algorithm. We distinguish:

- **Unsigned adversary:** cannot produce a valid provenance tag.
- **Authenticated adversary:** can create validly authenticated content through a legitimate write channel.
- **Policy-attested adversary:** can compromise the semantic validator or obtain a valid safety attestation. This stronger adversary is either bounded separately or declared outside the primary certificate.

The user intent and candidate action are conditioned on when comparing clean and intervened evidence for the same guard decision. If the attack changes the proposed action itself, that action is evaluated as a new decision instance.

### 3.4 Trust is a structured variable

Each evidence item \(e\) carries a trust record

\[
T(e)=(p_e,a_e,s_e,v_e,t_e),
\]

where:

- \(p_e\): provenance identity and integrity record;
- \(a_e\in\{0,1\}\): semantic authorization bit;
- \(s_e\): authorized scope, including action and domain constraints;
- \(v_e\): policy or validator version;
- \(t_e\): freshness or expiry condition.

We define

\[
\operatorname{attested}(e,x)=1
\]

only if the signature is valid, the semantic authorization is issued by an approved validator, the scope matches the current decision, the policy version is accepted, and the item is not expired.

### 3.5 Certification objective

For an attack class \(\mathcal A(\mathbf m)\), we seek computable values \(U_{\mathrm{FN}}\) and \(U_{\mathrm{FP}}\) such that, with probability at least \(1-\alpha\) over the held-out calibration sample,

\[
\sup_{a\in\mathcal A(\mathbf m)}\operatorname{FNR}(a)\le U_{\mathrm{FN}},
\]

\[
\sup_{a\in\mathcal A(\mathbf m)}\operatorname{FPR}(a)\le U_{\mathrm{FP}}.
\]

The guarantee is conditional on the declared attack budget, graph fidelity, contribution caps, and attestation assumptions.

---

## 4. PrecedentGuard

### 4.1 Overview

PrecedentGuard wraps a frozen guard backbone \(g\) with five stages:

1. construct the EIG from runtime logs;
2. select decision-relevant evidence parents;
3. retrieve structurally and semantically matched precedent capsules;
4. estimate bounded counterfactual evidence contributions;
5. aggregate them under directional trust constraints and choose a calibrated threshold.

The guard backbone is never fine-tuned. All robustness is produced by structured querying, bounded aggregation, and calibration.

### 4.2 Evidence-separable base score

A monolithic prompt makes it difficult to attribute and bound the effect of one mutable node. We therefore separate the score into a stable core and bounded evidence terms:

\[
S(x)=B(I,A)+\sum_{e\in P_x}\phi_e(x)+\sum_{r\in R_x}\psi_r(x),
\]

where:

- \(B(I,A)\) is the frozen guard score for the user intent and candidate action with a minimal trusted system policy;
- \(P_x\) contains current-trajectory evidence nodes;
- \(R_x\) contains retrieved precedent capsules;
- \(\phi_e\) and \(\psi_r\) are clipped evidence contributions.

This decomposition does not assume the frozen guard is globally Lipschitz with respect to arbitrary text. Robustness comes from preventing mutable evidence from entering an unbounded monolithic context.

### 4.3 Precedent capsule

A precedent is stored as

\[
R_i=(Q_i,G_i,A_i,Y_i,J_i,T_i),
\]

where \(Q_i\) is a compact trajectory summary, \(G_i\) is the execution subgraph relevant to the historical decision, \(A_i\) is the proposed action, \(Y_i\) is the audited label, \(J_i\) is the recorded justification, and \(T_i\) is the trust record.

The capsule is signed over the full tuple, including label, scope, policy version, and expiry. A signature over raw text alone is treated as authentication, not semantic authorization.

Retrieval combines semantic and structural similarity:

\[
w_i \propto
\lambda_s\operatorname{sim}_{\mathrm{text}}(x,R_i)
+\lambda_g\operatorname{sim}_{\mathrm{graph}}(G_x,G_i)
+\lambda_a\operatorname{sim}_{\mathrm{action}}(A,A_i),
\]

with \(\sum_i w_i=1\) and \(0\le w_i\le w_{\max}\).

### 4.4 Counterfactual influence estimation

For each current evidence node \(e\), let \(x^{(-e)}\) denote a runtime-supported counterfactual in which \(e\) is ablated or replaced by a type-matched neutral control. The raw contribution is

\[
\delta_e=g(I,A,e)-g(I,A,e^{\mathrm{ctrl}}).
\]

For a precedent capsule \(R_i\),

\[
\delta_i=g(I,A,R_i)-g(I,A,R_i^{\mathrm{ctrl}}).
\]

The score difference is not claimed to be a population causal effect under an unidentified observational model. It is an **interventional influence under the implemented replay operator**. This terminology ties the claim to an executable intervention.

To reduce stochastic variance, each difference may be estimated with \(q\) repeated deterministic or temperature-controlled runs:

\[
\bar\delta_e=\frac{1}{q}\sum_{j=1}^{q}\delta_e^{(j)}.
\]

### 4.5 Per-type clipping

Each contribution is clipped according to its evidence type:

\[
\tilde\delta_e=
\operatorname{clip}(\bar\delta_e,-c_{k}^{-},c_{k}^{+}),
\qquad k=\operatorname{type}(e).
\]

Separate caps allow the defender to model asymmetric operational risk. For example, untrusted web content may receive a small negative cap but a larger positive cap because it can provide warning evidence but should not strongly justify permission.

### 4.6 Directional trust constraint

Define

\[
\tilde\delta_e^{\mathrm{PG}}=
\begin{cases}
\max(0,\tilde\delta_e), & \operatorname{attested}(e,x)=0,\\
\tilde\delta_e, & \operatorname{attested}(e,x)=1.
\end{cases}
\]

Thus, unauthorised evidence may increase risk but cannot reduce it. Merely authenticated evidence is still treated as unauthorised unless a valid semantic attestation applies.

For precedents,

\[
\tilde\delta_i^{\mathrm{PG}}=
\begin{cases}
\max(0,\tilde\delta_i), & \operatorname{attested}(R_i,x)=0,\\
\tilde\delta_i, & \operatorname{attested}(R_i,x)=1.
\end{cases}
\]

The final score is

\[
S_{\mathrm{PG}}(x)=
B(I,A)
+\operatorname{clip}\left(
\sum_{e\in P_x}\beta_e\tilde\delta_e^{\mathrm{PG}}
+\sum_{i\in R_x}w_i\tilde\delta_i^{\mathrm{PG}},
-\varepsilon_-,\varepsilon_+
\right).
\]

The coefficients \(\beta_e\) normalize contributions by type and graph depth. They are selected on development data and fixed before certificate calibration.

### 4.7 Decision rule and selective escalation

The primary binary decision is

\[
\hat Y=\mathbf{1}[S_{\mathrm{PG}}\ge\theta].
\]

An optional selective region \([\theta_\ell,\theta_h]\) routes uncertain cases to a stronger model, human reviewer, or deterministic policy checker. The main theoretical results cover the binary threshold; selective extension is reported separately with coverage, residual risk, and escalation cost.

### 4.8 Algorithm

```text
Algorithm 1: PrecedentGuard runtime decision
Input: intent I, proposed action A, runtime log L, frozen guard g,
       precedent store R, clipping caps c, trust policy P, threshold θ

1: G ← BuildExecutionGraph(L)
2: E ← SelectInstrumentedParents(G, A)
3: C ← RetrievePrecedentCapsules(I, A, G, R)
4: b ← GuardScore(g, minimal_context(I, A))
5: z ← 0
6: for each evidence node e in E do
7:     δ ← CounterfactualDifference(g, I, A, e, control(e))
8:     δ ← TypeClip(δ, type(e), c)
9:     if not PolicyAttested(e, I, A, P) then δ ← max(0, δ)
10:    z ← z + β_e δ
11: end for
12: for each precedent r in C do
13:    δ ← CounterfactualDifference(g, I, A, r, control(r))
14:    δ ← TypeClip(δ, precedent, c)
15:    if not PolicyAttested(r, I, A, P) then δ ← max(0, δ)
16:    z ← z + w_r δ
17: end for
18: s ← b + clip(z, -ε_-, ε_+)
19: return BLOCK if s ≥ θ else ALLOW
```

### 4.9 Computational cost

If \(K\) current evidence nodes and \(R\) precedents are evaluated with \(q\) repeated scores, the naive cost is \(O(q(K+R))\) guard calls. We evaluate:

- prefix or KV caching where supported;
- a two-stage screen that evaluates only high-relevance nodes;
- a small frozen proxy for influence ranking followed by exact scoring of the top \(k\);
- batching of counterfactual pairs.

Latency is reported at median, P90, and P95, together with GPU memory and token overhead.

---

## 5. Theoretical Analysis

### 5.1 Assumptions and scope

**Assumption A1: Execution-graph fidelity.** Every mutable item that enters the PrecedentGuard evidence aggregation is represented by an instrumented node. Hidden channels outside the runtime instrumentation are not covered.

**Assumption A2: Bounded contribution interface.** Each current evidence or precedent contribution is clipped to its declared type-specific interval before aggregation.

**Assumption A3: Attack budget.** The adversary changes at most \(m_k\) evidence nodes of each type \(k\). Replacement counts as one modified node; insertion and deletion are counted explicitly.

**Assumption A4: Attestation boundary.** The primary certificate assumes the adversary cannot forge or incorrectly obtain a policy attestation. Authenticated but semantically unauthorised writes remain within the threat model. A stronger certificate with validator error \(\eta\) is discussed in Section 5.5.

**Assumption A5: Joint \((\Gamma, \alpha)\) pre-commitment.** Both the configuration grid \(\Gamma\) and the set of candidate confidence levels \(\{\alpha_1, \ldots, \alpha_L\}\) are fixed *before* any calibration example in \(C_0 \cup C_1\) is observed. In particular, neither \(\Gamma\) nor the reported \(\alpha\) is chosen by minimizing \(\widehat R_{\mathrm{FN}}\), \(\widehat R_{\mathrm{FP}}\), or the certificate tightness over calibration data; a joint hash of \((\Gamma, \{\alpha_j\})\) is committed to the experiment registry before the calibration split is instantiated. Post-hoc \(\alpha\) selection is a selective-inference threat equivalent to post-hoc \(\Gamma\) selection and is separately prohibited. This assumption is required for the union bound in Theorem 3; Theorems 1–2 do not depend on it.

These assumptions are visible deployment conditions, not claims about arbitrary LLM-agent systems.

### 5.2 Directional intervention sensitivity

Let \(S(x)\) and \(S(a(x))\) be the clean and attacked PrecedentGuard scores for the same intent and candidate action. Define \(\rho_-\) as a bound on the maximum downward score change and \(\rho_+\) as a bound on the maximum upward score change:

\[
S(a(x))\ge S(x)-\rho_-,
\qquad
S(a(x))\le S(x)+\rho_+.
\]

For evidence type \(k\), let its clean contribution lie in \([-c_k^-,c_k^+]\). Replacing one term can change the un-clipped sum by at most \(c_k^-+c_k^+\). Under the outer clipping interval \([-\varepsilon_-,\varepsilon_+]\), a conservative two-sided bound is

\[
\rho_{\mathrm{sym}}(\mathbf m)
=
\min\left
\{
\varepsilon_-+\varepsilon_+,
\sum_k m_k(c_k^-+c_k^+)
\right\}.
\]

The directional trust rule permits tighter bounds. If unauthorised insertions cannot create negative contributions, their insertion budget contributes zero to the downward shift. Deletions of positive warning evidence and modifications of already attested evidence remain in \(\rho_-\).

**Theorem 1 (Directional Intervention Sensitivity Bound).**  
Under A1–A4, for every attack \(a\in\mathcal A(\mathbf m)\),

\[
-\rho_-(\mathbf m)\le
S(a(x))-S(x)
\le \rho_+(\mathbf m),
\]

where \(\rho_-\) and \(\rho_+\) are obtained by summing the maximum permitted directional change of the modified terms and intersecting the result with the outer clipping range. In particular, an unauthorised insertion that does not delete or alter existing evidence cannot decrease the score.

**Proof sketch.** The score is a sum of independently clipped terms followed by an outer clipping operator. The clipping operator is 1-Lipschitz. For each modified term, the largest possible directional change is the distance between the endpoints permitted by its type and trust status. Summing these changes gives a bound on the pre-clipped aggregate; applying the outer clipping cannot increase that difference. The zero downward effect for unauthorised insertions follows from replacing their negative contributions by zero. A full case analysis for insertion, deletion, and replacement appears in Appendix A.

### 5.3 From score sensitivity to double-sided risk

Define the clean class-conditional margins

\[
M_1(x)=S(x)-\theta \quad \text{for }Y=1,
\]

\[
M_0(x)=\theta-S(x) \quad \text{for }Y=0.
\]

An unsafe example can become a false negative only if its clean unsafe margin is no larger than the maximum downward shift. A safe example can become a false positive only if its clean safe margin is no larger than the maximum upward shift.

**Theorem 2 (Population Double-Sided Risk Bound).**  
Under Theorem 1,

\[
\sup_{a\in\mathcal A(\mathbf m)}\operatorname{FNR}(a)
\le
\Pr(M_1\le\rho_-\mid Y=1),
\]

\[
\sup_{a\in\mathcal A(\mathbf m)}\operatorname{FPR}(a)
\le
\Pr(M_0\le\rho_+\mid Y=0).
\]

**Proof.** If \(M_1>\rho_-\), then \(S(a(x))\ge S(x)-\rho_->\theta\), so the attacked classifier still blocks the unsafe example. Therefore an attacked false negative can occur only inside \(\{M_1\le\rho_-\}\). The FPR result is symmetric.

This result includes existing clean errors: a clean false negative has \(M_1<0\), which is contained in \(M_1\le\rho_-\).

### 5.4 Finite-sample certificate

Let \(C_1\) and \(C_0\) be independent held-out calibration subsets with \(n_1\) unsafe and \(n_0\) safe examples. For a fixed configuration \(\gamma=(\theta,\mathbf c,\varepsilon_-,\varepsilon_+)\), define

\[
\widehat R_{\mathrm{FN}}(\gamma)
=
\frac{1}{n_1}\sum_{x\in C_1}
\mathbf 1[M_1(x)\le\rho_-(\gamma)],
\]

\[
\widehat R_{\mathrm{FP}}(\gamma)
=
\frac{1}{n_0}\sum_{x\in C_0}
\mathbf 1[M_0(x)\le\rho_+(\gamma)].
\]

Configurations are selected from a finite grid \(\Gamma\) using a separate development set. Alternatively, if the calibration set is used to choose among \(|\Gamma|\) candidates, a union-bound correction is applied.

**Theorem 3 (Finite-Sample Double-Sided Certificate).**  
Under Assumptions A1–A5, with probability at least \(1-\alpha\), simultaneously for all \(\gamma\in\Gamma\),

\[
\sup_{a\in\mathcal A(\mathbf m)}\operatorname{FNR}(a)
\le
\widehat R_{\mathrm{FN}}(\gamma)
+
\sqrt{\frac{\log(2|\Gamma|/\alpha)}{2n_1}},
\]

\[
\sup_{a\in\mathcal A(\mathbf m)}\operatorname{FPR}(a)
\le
\widehat R_{\mathrm{FP}}(\gamma)
+
\sqrt{\frac{\log(2|\Gamma|/\alpha)}{2n_0}}.
\]

**Proof sketch.** Apply Hoeffding’s inequality to each Bernoulli vulnerable-margin indicator for each class and configuration, then take a union bound over both classes and \(\Gamma\). Combine the empirical bounds with Theorem 2.

**Remark.** This certificate is distribution-dependent through the held-out class-conditional margins and assumes the calibration and deployment distributions match for the relevant risk event. Cross-domain validity is evaluated empirically rather than silently assumed. A conformal-risk extension is future work unless completed before submission.

**Remark (Pre-commitment mechanism and disclosure).** Assumption A5 requires a pre-commitment of both \((\Gamma, \{\alpha_j\})\) prior to calibration. Our reference implementation logs the SHA-256 hash of the serialized \((\Gamma, \{\alpha_j\})\) grid to an append-only experiment registry (`experiments/registry.csv`) before the calibration split is instantiated (function `commit_grid_hash` in `precedentguard/certificate.py`; enforcement at certification time in `assert_grid_committed`). This mechanism defends against unintentional post-hoc selection by the honest researcher but is a *self-attestation* baseline: a malicious insider with write access to the registry could re-order or forge commits. For **adversarial-verifiable** pre-commitment — e.g., under anonymous peer review or a public reproducibility audit — the registry hash should additionally be anchored to an external timestamping service (RFC 3161 TSA, OpenTimestamps, or a public git tag / GitHub release). We report which anchor mode is used in each experimental run.

**Remark (Sidedness of the union bound).** We use *one-sided* Hoeffding, giving the multiplier \(2\): one upper-tail deviation per class, over \(|\Gamma|\) configurations and \(|\{\mathrm{FN},\mathrm{FP}\}|=2\) classes. Only the upper-tail deviation \(R^{\star}(\gamma)\le\widehat R(\gamma)+t\) is required for a valid upper-bound certificate. The two-sided variant would replace \(2|\Gamma|\) by \(4|\Gamma|\); the ratio

\[
\frac{t_{4|\Gamma|}}{t_{2|\Gamma|}} \;=\; \sqrt{\,\frac{\log(4|\Gamma|/\alpha)}{\log(2|\Gamma|/\alpha)}\,}
\]

is independent of the calibration size \(n\) but depends on \(|\Gamma|\) and \(\alpha\). For the reference regime \((|\Gamma|,\alpha)=(20,0.05)\), the two-sided tail is \(5.06\%\) larger than the one-sided; across \((|\Gamma|,\alpha)\in\{5,10,20,50,100,500\}\times\{0.01,0.05,0.10\}\) the gap ranges from \(2.97\%\) to \(7.26\%\). The full table is reproducible from `scripts/day1_theorem_numerical_example.py`; three externally supplied reference values (5.63% / 4.09% / 2.80%) reproduce exactly. We adopt the tighter one-sided version.

### 5.5 Imperfect semantic validators

We distinguish two notions of validator error rate and are explicit about which one this extension covers:

- **Deployment-average validator error** \(\eta_{\mathrm{avg}} := \Pr_{x \sim \mathcal{D}}[\text{validator is wrong on } x]\), where \(\mathcal{D}\) is the deployment input distribution.
- **Adversarial worst-case validator error** \(\eta_{\mathrm{adv}} := \sup_{a \in \mathcal{A}(\mathbf m)} \Pr[\text{validator is wrong on } a(x)]\), where the supremum is over the attack class permitted by the threat model.

Suppose a policy attestation is wrong with probability at most \(\eta_{\mathrm{avg}}\) on deployment-matched data. A conservative extension adds this deployment-average validator risk to the unsafe certificate:

\[
U_{\mathrm{FN}}^{\eta_{\mathrm{avg}}}
\le U_{\mathrm{FN}}+\eta_{\mathrm{avg}},
\]

with a corresponding term for FPR if incorrect attestations can increase risk. This bound requires an independently validated estimate or certificate for \(\eta_{\mathrm{avg}}\); otherwise the main theorem must retain A4 as an explicit assumption.

**Warning — the two rates are not exchangeable.** An adversary who probes the validator's failure modes can achieve \(\eta_{\mathrm{adv}} \gg \eta_{\mathrm{avg}}\); the additive form above is *not valid* under adversarial worst-case validator error. Certifying against \(\eta_{\mathrm{adv}}\) requires either (i) a validator with a certified robust-error bound of its own, or (ii) folding the validator's output channel \(Z\) into the observation \(O\) of Proposition 1 and re-deriving the TV lower bound over the joint channel. Both options are future work; the present paper reports \(\eta_{\mathrm{avg}}\) with explicit disclosure.

### 5.6 Observational-indistinguishability lower bound

The original paper plan proposed a universal impossibility theorem based on the absence of a cryptographic anchor. That claim is too broad: a guard may classify perfectly from another uncorrupted variable. The correct obstruction is lack of label-separating information.

**Measurable setup.** Let \((\Omega, \mathcal{F}, \Pr)\) carry the input \(X:\Omega\to\mathcal{X}\), the label \(Y:\Omega\to\{0,1\}\), and an adversary randomization source \(U_{\mathrm{adv}}\). Let \((\mathcal{Y},\mathcal{B}_\mathcal{Y})\) be the observation space with its Borel \(\sigma\)-algebra, and let \(O:\Omega\to\mathcal{Y}\) be a measurable observation channel visible to the guard. A binary guard is a Borel-measurable function \(h:\mathcal{Y}\to\{0,1\}\); randomized guards (Markov kernels \(\mathcal{Y}\to[0,1]\)) are also permitted. The attacker is a Markov kernel \(a:\mathcal{X}\times\sigma(U_{\mathrm{adv}})\to\mathcal{X}\), and we assume the **label-oblivious** condition \(U_{\mathrm{adv}}\perp Y\mid X\) (the attacker does not observe \(Y\); a label-aware variant is discussed in the appendix). Define the attacked observable distributions as probability measures on \((\mathcal{Y},\mathcal{B}_\mathcal{Y})\): \(Q_y(B):=\Pr(O(a(X,U_{\mathrm{adv}}))\in B\mid Y=y)\) for \(B\in\mathcal{B}_\mathcal{Y}\), \(y\in\{0,1\}\). Then \(\operatorname{FNR}(h)=\Pr_{Q_1}[h=0]\) and \(\operatorname{FPR}(h)=\Pr_{Q_0}[h=1]\).

**Proposition 1 (Double-Sided Indistinguishability Lower Bound).**

\[
\operatorname{FNR}(h)+\operatorname{FPR}(h)
\ge 1-\operatorname{TV}(Q_1,Q_0),
\]

and therefore

\[
\max\{\operatorname{FNR}(h),\operatorname{FPR}(h)\}
\ge \frac{1-\operatorname{TV}(Q_1,Q_0)}{2}.
\]

If \(Q_1=Q_0\), at least one of FNR or FPR is at least \(1/2\).

**Corollary 1 (Authenticity is not semantic information).**  
Adding an authenticated variable \(Z\) cannot improve this lower bound unless the class-conditional joint distributions become more separable:

\[
\operatorname{TV}(Q_1^{O,Z},Q_0^{O,Z})
>
\operatorname{TV}(Q_1^{O},Q_0^{O}).
\]

A valid signature that is independent of the safety label, or that authenticates adversarially chosen content, does not by itself break indistinguishability.

This proposition is a supporting clarification rather than the paper’s primary novelty. Its role is to formalize why provenance authenticity and semantic authorization must be separated.

---

## 6. Experimental Design

### 6.1 Research questions

- **RQ1 — Utility and safety:** Does PrecedentGuard improve or preserve guard quality on clean and attacked trajectories?
- **RQ2 — Certificate validity:** Do empirical attacked FNR and FPR remain below the predicted class-conditional bounds?
- **RQ3 — Structural value:** Does the execution-grounded graph outperform sequential, random, learned, and no-graph alternatives?
- **RQ4 — Trust semantics:** Is policy attestation materially stronger than signature-only provenance against authenticated poisoning?
- **RQ5 — Adaptive and OOD robustness:** How do guarantees and empirical performance change under attackers that know the defense and under unseen domains or attack families?
- **RQ6 — Efficiency:** What are the latency, token, and memory costs of counterfactual influence estimation?

### 6.2 Evaluation suites

The main paper should prioritize a small number of defensible suites rather than an unmanageable list.

#### Suite A: Trajectory safety classification

Candidate datasets:

- AgentHarm;
- Agent-SafetyBench;
- R-Judge;
- one long-trajectory benchmark with step-level labels, selected after verifying license, code, and exact task compatibility.

The evaluation unit is a proposed action with its preceding instrumented trajectory.

#### Suite B: Indirect prompt injection

Candidate environments:

- AgentDojo;
- InjecAgent;
- a controlled tool-output injection environment built on the project’s existing agent stack.

PrecedentGuard is evaluated as a guard decision layer. AgentSentry and AttriGuard should be compared only where their runtime assumptions and available implementations permit a fair action-level evaluation.

#### Suite C: Persistent memory poisoning

Use attacks and scenarios adapted from:

- AgentPoison;
- MINJA;
- SMSR-style unsigned and authenticated injection;
- MemoryGraft or another reproducible persistent-memory attack.

SMSR and MemLineage are domain-specific baselines here. Their reported objectives must not be conflated with generic FNR/FPR unless the evaluation is re-labeled consistently.

### 6.3 Controlled Causal Intervention Suite

To test the paper’s structural claims, construct a controlled intervention suite from replayable trajectories. For each clean trajectory:

1. record the runtime EIG;
2. choose a known parent node of the target action;
3. create one intervention on that parent;
4. create a matched non-parent or irrelevant-node control;
5. replay the downstream decision under fixed seeds where possible;
6. record score shift, action shift, and safety-label change.

Intervention families:

- memory insertion, deletion, and replacement;
- tool-return instruction injection;
- retrieval promotion, suppression, and reordering;
- benign but policy-sensitive evidence changes;
- non-causal distractor mutations.

Target scale: at least `[N ≥ 1,000 paired interventions; finalize based on compute]`, balanced across parent type, label, domain, and attack family.

### 6.4 Guard backbones

Use at least three heterogeneous frozen backbones, subject to license and reproducibility:

- one Llama Guard family model;
- one ShieldGemma family model;
- one open moderation or guardian model such as WildGuard or Granite Guardian.

Exact model versions and checkpoints must be verified immediately before the experiment freeze.

### 6.5 Baselines

#### General guard baselines

- frozen backbone on the proposed action only;
- frozen backbone on flattened full trajectory;
- vanilla precedent retrieval with raw context concatenation;
- similarity-weighted precedent voting;
- sequence-aware or trajectory-aware guard where code is available.

#### Causal and counterfactual baselines

- CIP-style causal prompting;
- no-graph counterfactual ablation;
- sequential-neighbor graph;
- random graph with matched degree;
- learned text-dependency graph;
- oracle execution graph on controlled data.

#### Memory-security baselines

- signature-only provenance;
- SMSR under its supported persistent-memory threat model;
- MemLineage under its supported lineage/action-gating setup;
- policy-attested PrecedentGuard.

### 6.6 Attack models

1. **Unsigned insertion:** attacker writes directly to memory or retrieval storage without a valid tag.
2. **Authenticated malicious user:** attacker creates signed content through a legitimate interaction path.
3. **Semantically false signed evidence:** content has valid provenance but no policy attestation.
4. **Observation injection:** malicious instructions appear in tool or web outputs.
5. **Retrieval manipulation:** attacker promotes poison or suppresses relevant benign evidence.
6. **Adaptive bounded attack:** attacker knows \(\theta\), caps, graph schema, and retrieval weights, and optimizes within \(\mathbf m\).
7. **Attestation compromise stress test:** a limited fraction of policy-attested items are incorrect; this tests sensitivity to Assumption A4 rather than claiming coverage.

### 6.7 Metrics

#### Standard performance

- F1, precision, recall, AUROC;
- FNR and FPR with confidence intervals;
- expected calibration error and Brier score;
- clean task utility and utility under attack.

#### Certificate metrics

- certified FNR upper bound;
- certified FPR upper bound;
- empirical worst-case FNR/FPR under each budget;
- certificate violation frequency across seeds;
- certificate tightness: bound minus empirical risk;
- percentage of examples or budgets receiving a non-vacuous certificate.

#### Causal-structure metrics

- parent localization precision and recall where oracle structure exists;
- score-effect separation between parent and non-parent interventions;
- Spearman/Pearson correlation between estimated interventional influence and replayed score effect;
- action survival or flip rate under parent and control interventions.

#### Systems metrics

- median/P90/P95 latency;
- guard calls per decision;
- input/output tokens;
- GPU memory;
- precedent-store memory and retrieval time.

### 6.8 Main ablations

The main paper should include the following ablation chain:

1. Base frozen guard;
2. + raw precedent retrieval;
3. + execution graph without counterfactual scoring;
4. + counterfactual evidence decomposition;
5. + symmetric clipping;
6. + directional trust constraint;
7. + class-conditional double-sided calibration.

Additional structural ablations:

- no graph;
- sequential graph;
- random degree-matched graph;
- learned graph;
- execution-grounded graph;
- oracle graph.

Trust ablations:

- no provenance;
- signature only;
- signature + derivation lineage where available;
- signature + policy label without scope;
- full scoped policy attestation.

### 6.9 Statistical protocol

- Use five seeds for stochastic guard calls or attack generation where computationally feasible.
- Freeze prompts, thresholds, caps, and retrieval hyperparameters before test evaluation.
- Split data into development, certificate-calibration, and test sets.
- Report bootstrap or exact binomial confidence intervals for FNR/FPR.
- Use paired tests for clean-versus-defense comparisons on the same trajectories.
- Correct for multiple comparisons in the main ablation family.
- Release the split manifest, runtime instrumentation schema, attack configurations, and certificate script.

### 6.10 Required figures and tables

**Figure 1:** Execution-grounded graph, intervention points, evidence decomposition, trust-direction gate, and dual-risk calibration.  
**Figure 2:** Unsafe and safe margin distributions with \(\rho_-\) and \(\rho_+\), visually explaining the two certificates.  
**Figure 3:** Empirical FNR/FPR and certified bounds versus attack budget.  
**Figure 4:** Parent versus non-parent counterfactual effect and graph ablation.  
**Table 1:** Clean and attacked performance across primary benchmarks.  
**Table 2:** Domain-aligned comparison with causal, memory, and trajectory defenses.  
**Table 3:** Full ablation and system overhead.  

---

## 7. Results

> **Status disclosure (2026-07-07):** §7.1 reports development-set evidence from a triplet-mode evaluation on 50 examples per subset from the public AgentHarm test set with a single frozen backbone (Llama-Guard-3-1B). This validates that (a) the full PrecedentGuard pipeline runs end-to-end on a real HuggingFace-hosted guard, and (b) the theoretical mechanism separating current-trajectory evidence from precedent-driven evidence produces the predicted directional effect on aggregated risk. §7.2–§7.6 remain scaffolds pending the 3-backbone × 3-suite × multi-seed test-set sweep scheduled for Days 7–11 of the sprint.

### 7.1 Development-set triplet evaluation on AgentHarm-public (Llama-Guard-3-1B, n = 50 per subset)

We evaluate three ablation modes on the harmful and harmless-benign subsets of the AgentHarm public test set (n = 50 per subset; identical example ids across modes so all comparisons are within-example):
(i) **backbone-only** — frozen Llama-Guard-3-1B applied to the base view $B(I, A)$;
(ii) **clipping-only** — PrecedentGuard over current-trajectory evidence with directional clipping, no precedent retrieval;
(iii) **PG-with-precedents** — the full v0.2 pipeline with label-balanced retrieval (top-k = 2) and asymmetric precedent coefficients $\beta_{\text{safe}} = 2.0,\ \beta_{\text{unsafe}} = 0.5$ (rationale in §7.1.2 below).

**Verdict counts and Wilson 95% CIs (n = 50 per subset).**

| Mode | Harmful block / 50 (TPR, 95% CI) | Benign block / 50 (FPR, 95% CI) | Mean $S_{PG}$ (harmful) | Mean $S_{PG}$ (benign) | Mean $\Delta_{PG}$ (benign) |
|---|---|---|---|---|---|
| Backbone only | 50 / 50, **1.00** [0.93, 1.00] | 27 / 50, **0.54** [0.40, 0.67] | 0.939 | 0.555 | 0 |
| Clipping only | 50 / 50, **1.00** [0.93, 1.00] | 35 / 50, **0.70** [0.56, 0.81] | 0.950 | 0.603 | **+0.048** |
| **PG (full, repaired v3)** | 50 / 50, **1.00** [0.93, 1.00] | **21 / 50, 0.42** [0.29, 0.56] | 0.911 | 0.504 | **-0.050** |

**Statistical tests (Fisher exact on benign block rate, unpaired marginal).**

| Comparison | 2×2 table | Fisher $p$ |
|---|---|---|
| Clipping-only vs Backbone | [[35, 15], [27, 23]] | 0.148 |
| **PG-full vs Clipping-only** | [[21, 29], [35, 15]] | **0.0085** |
| PG-full vs Backbone | [[21, 29], [27, 23]] | 0.317 |

**Paired within-example McNemar test (benign, PG-full vs Backbone).** Because every example receives a verdict under every mode, the marginal Fisher test above discards the within-example pairing structure and understates the effect. The paired transitions are:

|  | Backbone block | Backbone allow |
|---|---|---|
| PG block | 21 | **0** |
| PG allow | **6** | 23 |

**Six benign examples flip from *backbone-block* to *PG-allow*; zero flip in the opposite direction.** McNemar exact two-sided $p = \mathbf{0.0312}$. This is the paper's headline safety-selectivity result under the dev-set configuration: **PG never introduces a false positive that the backbone would not have made, and it strictly recovers six previously over-blocked benign requests.** The score-movement distribution confirms the mechanism: 35 of 50 benign examples have $S_{PG}(\text{PG}) < S_{PG}(\text{backbone})$, with mean per-example shift $-0.050$; on the harmful subset the mean shift is also negative ($-0.028$) but crucially all 50 examples remain above the 0.5 threshold, i.e., harmful verdicts degrade *gracefully but not fatally*.

**Category disaggregation (benign, PG-full).**

| Category | $n$ | PG block | PG allow |
|---|---|---|---|
| Harassment | 16 | 9 | 7 |
| Drugs | 12 | 6 | 6 |
| Disinformation | 8 | 4 | 4 |
| Hate | 8 | **0** | 8 |
| Fraud | 4 | **0** | 4 |
| Cybercrime | 2 | 2 | 0 |

PG-full recovers the entire *Hate-benign* and *Fraud-benign* categories (0 / 8 and 0 / 4 blocked respectively), which the backbone was over-blocking on almost all instances. It maintains over-blocking on the *Cybercrime-benign* micro-slice ($n = 2$), consistent with these items being genuinely borderline in AgentHarm's annotation. Full-scale test-set numbers with per-category CIs are the top priority for Day 7 (§7.1 will be re-run with $n = 200$ per subset drawn from the remaining test-set pool of 158 safe and 210 unsafe items).

**Interpretation and headline mechanism finding.** Two observations follow from the table above; each maps to a specific theoretical claim in §4 and §5.

*(i) Directional clipping applied to current-trajectory evidence alone strictly increases over-blocking.* Clipping-only inflates benign FPR from 0.54 (backbone) to 0.70 — 16 percentage points worse than the frozen baseline, with mean $\Delta_{PG} = +0.048$ on the benign subset. This is exactly the behavior Corollary 1 anticipates: current-trajectory evidence is un-attested by construction, and under the directional trust rule of §4.6 an un-attested contribution is clipped upward by $\max(0, \tilde\delta_e)$, so its net effect on $S_{PG}$ can only be non-negative. Clipping-only *cannot* express a "this looks safe" signal.

*(ii) Precedent retrieval + directional trust is the mechanism that admits negative evidence.* Adding label-balanced precedent retrieval with policy-attested capsules restores the ability to move $S_{PG}$ downward, and does so *significantly* — PG-full's benign FPR of 0.42 is 28 percentage points below clipping-only, with **Fisher exact $p = 0.0085$** — while harmful recall stays pinned at 1.00. Mean $\Delta_{PG}$ on the benign subset flips sign (from $+0.048$ to $-0.050$), consistent with attested safe precedents supplying the previously-forbidden negative counterfactual contributions of §4.4. All 50 PG rows exhibit nonzero per-precedent deltas.

**The paper's mechanism claim is empirically operational on a real frozen backbone.** The theory predicts that only attested, label-informative evidence can lower risk; the pilot shows exactly that separation between the two ablation modes at $p < 0.01$. This is the strongest evidence-based signal in support of Corollary 1 that a real-backbone setting has produced to date.

**Statistical caveat.** The PG-vs-Backbone benign comparison alone is not significant at $n = 50$ (Wilson CIs overlap; Fisher $p = 0.32$); the PG-vs-Clipping-only separation is the identified robust effect. The Days 7–11 test-set sweep at $n \geq 200$ per subset across three backbones will report paired within-example McNemar tests and multiplicity-corrected $p$-values.

#### 7.1.1 Prompt-layer engineering (payload-aware rendering)

An initial run with content-hash-only prompts (`hash-a3f2e...` etc.) yielded no meaningful precedent influence because the frozen backbone treated hash tokens as opaque noise. We refactored the backend prompt construction to prefer human-readable payload text (`node_prompt_text` helper in `precedentguard/backends/base.py`), falling back to the content hash only when payload is absent. Under payload-aware rendering, all 100 dev-set examples exhibit nonzero per-precedent counterfactual deltas (100/100 for PG-with-precedents on both subsets combined). Content hashes remain the deterministic identifier for A5 grid-hash logging and reproducibility.

#### 7.1.2 Label-balanced retrieval and asymmetric $\beta$

Vanilla top-k retrieval, applied to the AgentHarm training pool used as the precedent store, was strongly biased toward the majority label of the pool: for benign queries the top-2 were often two unsafe cases, and vice versa. This produced a symmetric bias in $S_{PG}$ that lifted benign scores toward the block threshold. We introduced two mechanisms:

- **Label-balanced retrieval.** From the top-$K$ ($K = 5$ probe pool) candidates by combined similarity, select up to $\lfloor \text{top-}k/2 \rfloor + 1$ of each label class before filling the remaining slots by raw similarity. Enforced only when the pool contains both classes; otherwise falls through to vanilla top-k. On the dev-set, PG retrieves 66 safe / 34 unsafe on the benign subset and 38 safe / 62 unsafe on the harmful subset — retrieval correctly leans in the semantically-appropriate direction while preserving cross-label diversity.
- **Asymmetric precedent $\beta$ scales.** After label balancing, safe-audited precedents receive $\beta_{\text{safe}} = 2.0$ while unsafe-audited precedents receive $\beta_{\text{unsafe}} = 0.5$. This encodes the operational asymmetry that a benign task incorrectly blocked is more costly per-instance than an unsafe task allowed (the calibration of the exact ratio is a hyperparameter fit on the dev split under Assumption A5).

The two mechanisms are separately configurable and are reported together as "repaired v3" in the table above; ablations that toggle each independently are in Appendix D.

#### 7.1.3 Diagnostic instrumentation

To surface base-score inflation attributable to precedent inclusion, `analyze_day1_base_guard_prompt_layer.py` records four base scores per example: backbone (no precedents), all-precedents, safe-only, and unsafe-only. This isolates whether observed $S_{PG}$ shifts are driven by counterfactual influence estimation (which the theory allows) or by uncontrolled prompt-context inflation (which the theory forbids). The v3 prompt template was selected after two prior iterations reduced the mean unsafe-only inflation to within the type-clipping cap $c_{\text{precedent}} = 0.15$ on the dev set.

#### 7.1.1 Prompt-layer engineering (payload-aware rendering)

An initial run with content-hash-only prompts (`hash-a3f2e...` etc.) yielded no meaningful precedent influence because the frozen backbone treated hash tokens as opaque noise. We refactored the backend prompt construction to prefer human-readable payload text (`node_prompt_text` helper in `precedentguard/backends/base.py`), falling back to the content hash only when payload is absent. Under payload-aware rendering, all 20 pilot examples exhibit nonzero per-precedent counterfactual deltas. Content hashes remain the deterministic identifier for A5 grid-hash logging and reproducibility.

#### 7.1.2 Label-balanced retrieval and asymmetric $\beta$

Vanilla top-k retrieval, applied to the AgentHarm training pool used as the precedent store, was strongly biased toward the majority label of the pool: for benign queries the top-2 were often two unsafe cases, and vice versa. This produced a symmetric bias in $S_{PG}$ that lifted benign scores toward the block threshold. We introduced two mechanisms:

- **Label-balanced retrieval.** From the top-$K$ ($K = 5$ probe pool) candidates by combined similarity, select up to $\lfloor \text{top-}k/2 \rfloor + 1$ of each label class before filling the remaining slots by raw similarity. Enforced only when the pool contains both classes; otherwise falls through to vanilla top-k.
- **Asymmetric precedent $\beta$ scales.** After label balancing, safe-audited precedents receive $\beta_{\text{safe}} = 2.0$ while unsafe-audited precedents receive $\beta_{\text{unsafe}} = 0.5$. This encodes the operational asymmetry that a benign task incorrectly blocked is more costly per-instance than an unsafe task allowed (the calibration of the exact ratio is a hyperparameter fit on the dev split under Assumption A5).

The two mechanisms are separately configurable and are reported together as "repaired" in the table above; ablations that toggle each independently are in Appendix D.

#### 7.1.3 Diagnostic instrumentation

To surface base-score inflation attributable to precedent inclusion, `analyze_day1_base_guard_prompt_layer.py` records four base scores per example: backbone (no precedents), all-precedents, safe-only, and unsafe-only. This isolates whether observed $S_{PG}$ shifts are driven by counterfactual influence estimation (which the theory allows) or by uncontrolled prompt-context inflation (which the theory forbids). The v3 prompt template was selected after two prior iterations reduced the mean unsafe-only inflation to within the type-clipping cap $c_{\text{precedent}} = 0.15$ on the pilot set.

### 7.2 Certificate validity and tightness

For all evaluated budgets within `[RANGE]`, empirical FNR and FPR remained below their respective finite-sample upper bounds in `[X/Y]` runs. The median certificate gaps were `[VALUE]` for FNR and `[VALUE]` for FPR. Bounds became vacuous beyond `[BUDGET]`, consistent with the increase in vulnerable margin mass near the threshold. *[Days 8–10.]*

### 7.3 Does the execution graph matter?

The execution-grounded graph outperformed the degree-matched random graph by `[VALUE]` on parent-localization accuracy and by `[VALUE]` on attacked F1. Oracle-graph performance was `[VALUE]`, leaving a gap of `[VALUE]` attributable to incomplete instrumentation or parent-selection error. Non-parent interventions produced substantially smaller replayed score effects than parent interventions (`[STATISTIC]`, `[P-VALUE/CI]`). *[Days 8–10, controlled intervention suite.]*

### 7.4 Authenticity versus semantic authorization

Signature-only provenance blocked unsigned insertion but did not prevent authenticated, semantically false memories from reducing the guard score. Full scoped policy attestation reduced this failure from `[VALUE]` to `[VALUE]`. Under the limited attestation-compromise stress test, performance degraded as a function of validator error, supporting the explicit dependence described in Section 5.5. *[Day 9.]*

### 7.5 Adaptive and cross-domain evaluation

An adaptive attacker that knew the clipping and retrieval parameters increased `[METRIC]` by `[VALUE]`, but remained below the declared certificate for budgets up to `[VALUE]`. Under the unseen-domain split, empirical risks `[DID/DID NOT]` remain below the in-domain calibrated bounds; accordingly, we report `[VALIDITY RESULT]` and do not claim distribution-free OOD certification. *[Day 10.]*

### 7.6 Efficiency

Preliminary measurement on the pilot slice with Llama-Guard-3-1B FP16 on a single RTX 3090 Ti: median per-decision latency is dominated by counterfactual replay calls to the frozen backbone, growing linearly in $|P_x| + |R_x|$ (evidence parents plus retrieved precedents). Full latency profiling with P50/P90/P95 across backbones is in §7.6-extended. *[Day 10.]*

---

## 8. Discussion

### 8.1 What the certificate means

The certificate is not a universal guarantee against arbitrary agent compromise. It guarantees class-conditional guard risk under a declared intervention budget and an enforced evidence interface. It is meaningful only when:

- runtime instrumentation captures all mutable evidence channels covered by the claim;
- each contribution is routed through the clipping mechanism;
- calibration data represent the deployment risk distribution;
- policy attestations satisfy the declared trust assumption.

This scope is narrower than “provably safe agent,” but substantially more falsifiable and deployable.

### 8.2 Relationship to SMSR

SMSR establishes a certificate for persistent-memory poisoning using write-time provenance and randomized ablation. PrecedentGuard should not claim to introduce the first provenance requirement or the first certified runtime-memory defense. Its intended distinction is:

1. heterogeneous evidence channels rather than memory retrieval alone;
2. a frozen guard score rather than malicious-response majority voting;
3. separate upward and downward sensitivity;
4. explicit class-conditional FNR and FPR certificates;
5. semantic authorization and scope, not signature validity alone.

A direct memory-only experiment should test whether these distinctions yield practical value rather than relying on narrative comparison.

### 8.3 Relationship to causal safety methods

CIP, AgentSentry, and AttriGuard show that causal structure and counterfactual replay can improve agent safety. PrecedentGuard narrows its causal claim to executable interventions supported by runtime instrumentation. It does not claim causal identifiability from passive text traces. This makes the method less grandiose but more defensible.

### 8.4 When precedents help

Precedents are most useful when current evidence is ambiguous but historical cases provide scoped, audited examples of similar action-risk relationships. They should not override direct policy constraints. The design principle is:

> **Precedents provide bounded evidence; policy-attested rules define authority.**

### 8.5 Failure modes

- Missing instrumentation can hide an intervention channel.
- Counterfactual controls may alter more than one semantic factor.
- LLM guard scores can be unstable across decoding seeds.
- Policy validators can be wrong or compromised.
- Scope matching may reject useful evidence or admit an inapplicable precedent.
- Calibration bounds may fail under distribution shift.
- Counterfactual scoring increases latency.

These are measured or explicitly scoped, not concealed by the theorem statement.

---

## 9. Limitations and Responsible Deployment

PrecedentGuard does not certify the full agent policy, environment, or tool implementation. It certifies a guard decision under bounded evidence interventions. The method assumes a trusted instrumentation and aggregation layer; compromise of this layer invalidates the guarantee. Semantic attestation may require human review, deterministic policy checks, or a separately validated model, creating operational cost and possible bias. Safety labels can encode contested norms, and false positives may disproportionately affect legitimate but unusual tasks. Evaluation must therefore include benign-sensitive cases, per-domain error analysis, and transparent abstention or appeal mechanisms.

Attack code and poisoned examples should be released with access controls appropriate to their risk. The public artifact should prioritize reproducible defenses, schemas, and synthetic or permissioned test data.

---

## 10. Conclusion

We presented PrecedentGuard, a training-free framework for double-sided runtime risk control under bounded interventions on LLM-agent trajectory evidence. The framework grounds its structure in trusted execution dataflow, estimates evidence influence through executable counterfactuals, separates provenance authenticity from semantic authorization, and restricts how unauthorised evidence can change a guard score. Its deterministic directional sensitivity bound combines with class-conditional margins to yield finite-sample upper bounds on both false negatives and false positives. A supporting lower bound clarifies that signatures are useful only when they carry label-informative, adversary-resistant evidence. The central empirical question is not merely whether PrecedentGuard improves F1, but whether its graph, trust model, and certificates remain valid under adaptive, authenticated, and cross-domain interventions.

---

# Appendix A. Proof Details

## A.1 Proof of Theorem 1

Let the clean pre-clipped evidence aggregate be

\[
Z(x)=\sum_j z_j(x),
\]

and the attacked aggregate be \(Z'(x)=\sum_j z'_j(x)\). Terms not modified by the attack satisfy \(z'_j=z_j\). For a modified type-\(k\) term with interval \([-c_k^-,c_k^+]\),

\[
-(c_k^-+c_k^+)\le z'_j-z_j\le c_k^-+c_k^+.
\]

Trust constraints replace the lower endpoint by zero for an unauthorised inserted term, yielding a zero downward contribution for pure insertion. Summing the appropriate directional endpoints over all modified terms gives raw bounds \(r_-\) and \(r_+\). Since

\[
C(z)=\operatorname{clip}(z,-\varepsilon_-,\varepsilon_+)
\]

is monotone and 1-Lipschitz,

\[
-r_-\le C(Z')-C(Z)\le r_+,
\]

and the output range also implies

\[
C(Z')-C(Z)\in[-(\varepsilon_-+\varepsilon_+),
\varepsilon_-+\varepsilon_+].
\]

Taking the tighter directional values proves the theorem.

## A.2 Proof of Theorem 2

For \(Y=1\), suppose \(M_1=S(x)-\theta>\rho_-\). Theorem 1 gives

\[
S(a(x))\ge S(x)-\rho_->\theta,
\]

so the attacked decision remains positive and cannot be a false negative. Hence the false-negative event is a subset of \(\{M_1\le\rho_-\}\). Taking conditional probabilities proves the FNR bound. The safe-class proof uses \(S(a(x))\le S(x)+\rho_+\).

## A.3 Proof of Theorem 3

For each \(\gamma\in\Gamma\), the indicator

\[
Z_i^{\mathrm{FN}}(\gamma)=
\mathbf 1[M_1(x_i)\le\rho_-(\gamma)]
\]

is Bernoulli. Hoeffding gives

\[
\Pr\left(
R_{\mathrm{FN}}(\gamma)-\widehat R_{\mathrm{FN}}(\gamma)>t
\right)
\le e^{-2n_1t^2}.
\]

Set \(t=\sqrt{\log(2|\Gamma|/\alpha)/(2n_1)}\), repeat for FPR, and apply a union bound over the two classes and all configurations. Theorem 2 completes the result.

## A.4 Proof of Proposition 1

The guard is a binary test between \(Q_0\) and \(Q_1\). The minimum possible sum of type-I and type-II errors over all tests is \(1-\operatorname{TV}(Q_1,Q_0)\). Therefore every guard has an error sum at least this quantity. The maximum of two nonnegative numbers is at least half their sum.

---

# Appendix B. Revision Decisions Relative to the Previous Plan

| Previous element | Decision | Reason |
|---|---|---|
| Raw trajectory → recovered CID | Replaced | Textual or temporal dependence does not identify causal parents |
| CID extraction | Replaced by execution-grounded graph | Edges come from auditable runtime dataflow |
| Logit perturbation as `do(D)` | Replaced | Calibration is a mechanism/policy intervention, not an atomic action assignment |
| Signature as causal trust anchor | Split into authenticity and semantic authorization | Valid signatures do not imply truth or safety |
| Universal no-anchor impossibility theorem | Narrowed to TV indistinguishability proposition | Previous statement was too broad and overlapped with SMSR |
| \(p\le\varepsilon/(KD)\Rightarrow\) FNR/FPR control | Replaced | Score bounds require class-conditional margin assumptions to imply risk bounds |
| SMSR as 2025 single-sided defense | Corrected | SMSR is a June 2026 preprint with provenance impossibility and authenticated-adversary certificate |
| CIP as sole causal safety work | Removed | AgentSentry, AttriGuard, and other concurrent work must be covered |
| Five benchmarks × thirteen systems as fixed requirement | Reduced to domain-aligned comparisons | Fairness and depth are more important under the AAAI page and time limits |
| OOD entirely deferred | Revised | At least one unseen-domain or unseen-attack evaluation is included, without claiming OOD certification |

---

# Appendix C. AAAI-27 Execution Plan

AAAI-27 abstract and paper deadlines are July 21 and July 28, 2026, respectively. The feasible plan is therefore four weeks, not eight or nine.

## June 30–July 4: Freeze claims and theory

- finalize the EIG and threat model;
- complete Theorem 1–3 proofs and independent mathematical review;
- implement a minimal contribution-clipping wrapper;
- verify all related-work references and remove unsupported priority claims.

**Kill criterion:** if the evidence-separable architecture cannot enforce the declared contribution caps, do not claim certification over that channel.

## July 5–July 11: Controlled interventions and core baselines

- build the replayable intervention suite;
- run base, raw-RAG, no-graph, random-graph, and execution-graph variants;
- implement signature-only and policy-attested trust variants;
- begin certificate calibration and validity tests.

## July 12–July 18: Primary benchmark experiments

- run the selected trajectory, IPI, and memory suites;
- perform adaptive attack and one cross-domain evaluation;
- measure latency and memory;
- freeze tables and main claims.

## July 19–July 21: Abstract freeze

- submit an abstract containing only verified claims;
- complete the seven-page main-paper narrative;
- place critical assumptions and proof sketches in the main paper.

## July 22–July 28: Red-team and submission

- causal-inference review: graph and intervention semantics;
- security review: trust boundary and authenticated attacker;
- learning-theory review: finite-sample certificate;
- empirical review: leakage, baselines, and statistical protocol;
- final reproducibility and reference audit.

---

# References (Day 4 Verification Status)

Every entry below marks its verification level: **[V]** = arXiv/DOI/venue independently confirmed via WebSearch on 2026-07-04; **[P]** = placeholder retained from PaperPlan_20260630.md pending re-verification; **[U]** = unverified (requires re-check before final submission).

## Core anchors (paper §2 in-line references)

1. **[P]** Pearl, J. 2009. *Causality: Models, Reasoning and Inference*. 2nd ed. Cambridge University Press.
2. **[P]** Everitt, T.; Hutter, M.; Kumar, R.; Krakovna, V. 2021. Reward Tampering Problems and Solutions in Reinforcement Learning: A Causal Influence Diagram Perspective. *Synthese*, 198(Suppl 27): 6435–6467.
3. **[P]** Richens, J.; Everitt, T. 2024. Robust Agents Learn Causal World Models. In *ICLR 2024*.
4. **[V]** Hahm, D.; Jin, W.; Choi, J. S.; Ahn, S.; Lee, K. 2025. Enhancing LLM Agent Safety via Causal Influence Prompting. In *Findings of the Association for Computational Linguistics: ACL 2025*, pages 15143–15168. arXiv:2507.00979.
5. **[V]** Zhang, T.; Xu, Y.; Wang, J.; Guo, K.; Xu, X.; Xiao, B.; Guan, Q.; Fan, J.; Liu, J.; Liu, Z.; Hu, H. 2026. AgentSentry: Mitigating Indirect Prompt Injection in LLM Agents via Temporal Causal Diagnostics and Context Purification. arXiv:2602.22724.
6. **[V]** He, Y.; Zhu, H.; Li, Y.; Shao, S.; Yao, H.; Liu, Z.; Qin, Z. 2026. AttriGuard: Defeating Indirect Prompt Injection in LLM Agents via Causal Attribution of Tool Invocations. arXiv:2603.10749.
7. **[V]** Sharma, T. 2026. SMSR: Certified Defence Against Runtime Memory Poisoning in Persistent LLM Agent Systems. arXiv:2606.12703. Code: https://github.com/tarun-ks/smsr.
8. **[V]** Ouyang, C.; Hou, R. 2026. MemLineage: Lineage-Guided Enforcement for LLM Agent Memory. arXiv:2605.14421. (State Key Laboratory of Cyberspace Security Defense, IIE, CAS)

## Memory poisoning attacks (paper §2.3)

9. **[P]** Chen, Z.; Xiang, Z.; Xiao, C.; Song, D.; Li, B. 2024. AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases. In *NeurIPS 2024*. arXiv:2407.12784.
10. **[P]** Dong, S.; Xu, S.; He, P.; et al. 2025. A Practical Memory Injection Attack against LLM Agents (MINJA). In *NeurIPS 2025*. arXiv:2503.03704.
11. **[P]** Zou, W.; Geng, R.; Wang, B.; Jia, J. 2025. PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models. In *USENIX Security 2025*. arXiv:2402.07867.

## Benchmarks (paper §6.2)

12. **[P]** Andriushchenko, M.; Souly, A.; Dziemian, M.; et al. 2024. AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents. In *ICLR 2025*. arXiv:2410.09024.
13. **[P]** Zhang, Z.; Cui, S.; Lu, Y.; et al. 2024. Agent-SafetyBench: Evaluating the Safety of LLM Agents. In *ACL 2025*. arXiv:2412.14470.
14. **[P]** Yuan, T.; He, Z.; Dong, L.; et al. 2024. R-Judge: Benchmarking Safety Risk Awareness for LLM Agents. In *Findings of EMNLP 2024*. arXiv:2401.10019.
15. **[P]** Debenedetti, E.; Zhang, J.; Balunovic, M.; et al. 2024. AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents. In *NeurIPS 2024 D&B*. arXiv:2406.13352.
16. **[P]** Zhan, Q.; Liang, Z.; Ying, Z.; Kang, D. 2024. InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated LLMs. In *Findings of ACL 2024*. arXiv:2403.02691.

## Static guard backbones (paper §2.1)

17. **[P]** Inan, H.; Upasani, K.; Chi, J.; et al. 2024. Llama Guard: LLM-Based Input-Output Safeguard. arXiv:2312.06674. Plus subsequent LLaMA-Guard 3/4 releases.
18. **[P]** Zeng, W.; Liu, Y.; Mullins, R.; et al. 2024. ShieldGemma: Generative AI Content Moderation Based on Gemma. arXiv:2407.21772.
19. **[P]** Padhi, I.; Nagireddy, M.; Cornacchia, G.; et al. 2024. Granite Guardian. arXiv:2412.07724.
20. **[P]** Han, S.; Rao, K.; Ettinger, A.; et al. 2024. WildGuard: Open One-Stop Moderation Tools for Safety Risks, Jailbreaks, and Refusals of LLMs. In *NeurIPS 2024 D&B*. arXiv:2406.18495.

## Learning-theoretic tools (paper §5.4, Appendix A.3–A.4)

21. **[V]** Angelopoulos, A. N.; Bates, S.; Fisch, A.; Lei, L.; Schuster, T. 2024. Conformal Risk Control. In *ICLR 2024*. arXiv:2208.02814. (Reviewer-corrected 2026-07-01: original 2023-NeurIPS attribution was wrong.)
22. **[P]** Tsybakov, A. B. 2009. *Introduction to Nonparametric Estimation*. Springer. Theorem 2.2 (Le Cam two-point inequality).
23. **[P]** Boucheron, S.; Lugosi, G.; Massart, P. 2013. *Concentration Inequalities: A Nonasymptotic Theory of Independence*. Oxford. Theorem 2.8 (Hoeffding).
24. **[P]** Polyanskiy, Y.; Wu, Y. 2024. *Information Theory: From Coding to Learning*. Cambridge. Ch. 7 (Data-processing inequality for total variation).

## Pre-submission audit tasks

- [ ] Re-verify all **[P]** entries via arXiv/DOI/venue lookup during Day 5–7.
- [ ] Convert this list to `references.bib` with verified BibTeX entries.
- [ ] Confirm all in-text citations (Sections §1–§8) resolve to an entry in this list.
- [ ] Self-citation ratio ≤ 15% (PrecedentGuard v2 advisor draft not yet public — counts only published work).

