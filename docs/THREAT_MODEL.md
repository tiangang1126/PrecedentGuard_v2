# THREAT_MODEL — PrecedentGuard

**Purpose:** the paper's operational threat model, expressed as (assets, actors, capabilities, channels, out-of-scope). Any change to §3.3 must first be reflected here.

---

## 1. Assets

- **The guard's decision on the current step** — the paper certifies FNR and FPR of this decision only.
- **The frozen backbone guard** — a black-box scoring model. Not fine-tuned; not queried on out-of-domain data.
- **The runtime instrumentation** — the tap points that produce the EIG. Their integrity is part of Assumption A1.

## 2. Actors

- **Defender:** a runtime PrecedentGuard wrapper around the frozen guard. Has read-only access to the EIG, can drive counterfactual re-executions of the guard, and can enforce type-cap and directional-trust rules.
- **Attacker:** an adversary with a bounded per-type intervention budget over mutable trajectory evidence.
- **Benign user:** issues intents drawn from the same distribution as the calibration set.

## 3. Attacker capabilities

The paper's primary certificate covers the following capability set:

- **Knowledge:** graph schema, guard backbone identity, retrieval rule, thresholds, clipping caps, and the aggregation algorithm.
- **Budget:** per-type vector $\mathbf m = (m_{\text{mem}}, m_{\text{obs}}, m_{\text{ret}}, m_{\text{tool}}, m_{\text{prec}})$. The primary grid commits $m_{\text{mem}} = m_{\text{ret}} = m_{\text{prec}} = 1$, $m_{\text{obs}} = m_{\text{tool}} = 0$.
- **Operations:** ablation, replacement (both implemented); replay and withholding declared as first-class operators for extensibility but not exercised by the primary certificate.
- **Adaptivity:** the primary certificate covers the *worst-case* attacker within the budget. Section 7.5 additionally reports an empirical adaptive attacker with query budget 100 per trajectory.

The paper distinguishes three attacker classes by provenance capability:

- **Unsigned:** cannot produce a valid provenance tag.
- **Authenticated:** can create validly authenticated content through a legitimate write channel (but cannot make it semantically authorized).
- **Policy-attested:** can compromise the semantic validator. **Excluded from the primary certificate** (Assumption A4); Section 5.5 gives an ancillary bound under validator error $\eta$ with the distinction between deployment-average and adversarial-worst-case $\eta$ made explicit.

## 4. Attack channels

Each of the five mutable node types is a potential attack channel:

| Channel | Node type | Attack examples |
|---|---|---|
| Memory | `NodeType.MEMORY` | AgentPoison-style planted memories; MINJA-style online injection |
| Retrieval | `NodeType.RETRIEVAL` | PoisonedRAG-style corpus poisoning; retrieval-time promotion/suppression |
| Observation | `NodeType.OBSERVATION` | Indirect prompt injection via tool returns or web content |
| Tool return | `NodeType.TOOL_RETURN` | Malicious tool output; sandbox escape |
| Precedent | `NodeType.PRECEDENT` | Poisoned or expired precedent capsules; label manipulation |

For each channel, the attacker's operational effect is bounded by (a) the per-type contribution cap $c_k^\pm$, (b) the outer clip $\varepsilon_\pm$, and (c) the directional trust rule which prevents un-attested contributions from reducing risk.

## 5. Trust structured variable

Every evidence item carries a trust record $T(e) = (p_e, a_e, s_e, v_e, t_e)$ where:

- $p_e$: provenance identity + integrity record
- $a_e \in \{0, 1\}$: semantic authorization bit
- $s_e$: authorized scope (action + domain constraint)
- $v_e$: policy or validator version
- $t_e$: freshness / expiry condition

The predicate $\text{attested}(e, x) = 1$ iff all five components are valid and match the current decision. Only attested items are permitted to reduce the aggregated risk score under §4.6.

## 6. Assumptions

- **A1 (Execution-graph fidelity).** Every mutable item that enters the PrecedentGuard aggregation is represented by an instrumented node.
- **A2 (Bounded contribution interface).** Each current-evidence or precedent contribution is clipped to its declared type-specific interval before aggregation.
- **A3 (Attack budget).** The adversary changes at most $m_k$ evidence nodes per type.
- **A4 (Attestation boundary).** The adversary cannot forge or incorrectly obtain a policy attestation.
- **A5 ($(\Gamma, \alpha)$ pre-commitment).** The configuration grid AND the candidate confidence levels are both fixed *before* any calibration example is observed, and their joint SHA-256 hash is recorded in `experiments/registry.csv`.
- **A6 (Class-conditional i.i.d. calibration).** Calibration samples are i.i.d. class-conditional; when samples are trajectory steps, clustered Hoeffding is substituted (deferred to §5.6).

## 7. Out of scope

The primary certificate does **not** cover:

- **Intent hijacking.** The user intent and candidate action are conditioned on; a malicious user is out of scope. Rationale: this is an authorization problem, not a runtime-safety problem.
- **Policy-attested compromise.** Handled separately with $\eta$-degradation bound in §5.5.
- **Cross-session coordination.** Not part of $\mathbf m$; empirically studied in §7.5 stress test only.
- **OOD deployment.** The certificate is calibration-set-conditional; cross-domain transfer is empirical (§7.5).
- **Attacks that change the proposed action $A$ itself.** Such attacks are re-evaluated as new decision instances.

## 8. Residual risks

- If runtime instrumentation misses a mutable evidence channel, A1 fails silently. Mitigation: §7.3 evaluates parent-set recall against oracle.
- If the validator's certificate is stolen, A4 fails. Mitigation: §5.5 $\eta$-bound.
- If the attacker's actual budget exceeds $\mathbf m$, both directional bounds are voided. Mitigation: the certificate exposes budget as a first-class parameter so operators can select budgets that match their deployment threat model.

## 9. Likely adaptive bypasses

Enumerated for §7.5 adaptive attack sweep:

- **Precedent-slot forgery.** Attacker constructs an unsigned precedent with a signature that looks valid; caught by cryptographic verification (A4 holds).
- **Retrieval-similarity gaming.** Attacker crafts content to match a target precedent's similarity but with a different label; caught by the label-audit step (empirical §7.4).
- **Clipping-cap saturation.** Attacker fully saturates $c^+$ on every mutable channel; bounded by the outer clip $\varepsilon^+$.
- **Threshold straddling.** Attacker pushes many benign examples to just above $\theta$; certificate's class-conditional margin distribution reflects this in $\hat R_{FP}$.

All four are tested empirically at pre-committed budgets in §7.5.
