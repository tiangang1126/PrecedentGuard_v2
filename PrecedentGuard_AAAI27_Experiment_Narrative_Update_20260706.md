# PrecedentGuard AAAI27 Narrative Update

## Status

This note records the **currently validated empirical narrative** for the AAAI 2027 draft. It is a companion note to `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md`, not a replacement for the final Results section.

The current evidence supports a **mechanistic repair claim**, not yet a full-benchmark or full-slice victory claim.

## Core Diagnosis

The main bottleneck was **not** retrieval diversity and **not** the outer aggregation framework.

The load-bearing error source was the prompt-layer protocol by which `unsafe` precedents entered `pg_with_precedents -> base_guard`.

## Causal Chain of Repairs

1. `label_balanced` retrieval fixed the selection bottleneck, but `per_precedent_delta` remained zero.
2. Logit-based Llama-Guard scoring fixed backend sensitivity and made precedent influence observable.
3. Policy-attested harmful precedents plus label-aware beta scaling corrected the first benign-side aggregation-sign error.
4. Removing precedents from the `base_score` path eliminated double counting.
5. Repairing the `unsafe precedent` prompt protocol removed the remaining benign-side base-score inflation without disabling precedent influence.

## Verified Stop-Loss Slice Evidence

### Benign slice: `harmless_benign 10`

- `backbone_only`: `block=9, allow=1`, `mean_base_score=0.684639`
- repaired `pg_with_precedents`: `block=6, allow=4`, `mean_base_score=0.684639`, `mean_s_pg=0.567950`, `mean_pg_delta=-0.116689`
- `nonzero_precedent_delta_examples = 10/10`

Interpretation:

- benign-side base inflation is removed
- precedent influence remains active
- the gain is not produced by turning precedents off; it is produced by fixing how unsafe precedents are admitted into the base layer

### Harmful slice: `harmful 10`

- `backbone_only`: `block=10, allow=0`, `mean_base_score=0.958933`
- repaired `pg_with_precedents`: `block=10, allow=0`, `mean_base_score=0.958933`, `mean_s_pg=0.911012`, `mean_pg_delta=-0.047921`
- `nonzero_precedent_delta_examples = 10/10`

Interpretation:

- harmful blocking is fully preserved on the matched slice
- the same repair does not collapse harmful-side protection

## Writing Rule for the Paper

The strongest justified statement at the current stage is:

> Prompt-layer unsafe-precedent protocol repair removes benign-side base-score inflation while preserving harmful blocking and non-zero precedent influence on matched stop-loss slices.

The paper should **not yet** write this as:

- full-benchmark SOTA
- certificate-valid full-slice success
- final Table 1 claim

## Recommended Placement in the AAAI Draft

Use this note to update the narrative around:

- `§7 Results`: current development-slice evidence
- `§8 Discussion`: precedents are a decision-interface problem, not only a retrieval problem
- response to reviewers: explain why the decisive repair was at the `base_guard` injection protocol rather than at retrieval or outer aggregation

## Next Experiment Gate

Immediate next execution:

1. refresh the tri-mode `10+10` table under the repaired branch;
2. if the repaired branch remains stable, promote it to the next frozen experiment tier;
3. only then write the final numbers into `PrecedentGuard_AAAI27_Revised_Draft_v0.2.md`.
