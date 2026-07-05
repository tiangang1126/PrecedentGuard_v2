# Debug Session: pg-cost-hit-quality
- **Status**: [OPEN]
- **Issue**: `clipping_only` and `pg_with_precedents` have high per-sample runtime cost, while precedent retrieval still fails to deliver explainable benign-side gains.
- **Debug Server**: N/A for this session
- **Log File**: artifacts/day5/diag-pg-cost-hit-quality.jsonl

## Reproduction Steps
1. Run `python scripts/run_real_backbone_eval.py --mode clipping_only --backend-name llama_guard --model-id meta-llama/Llama-Guard-3-1B --subset harmful --limit 1 --output-file artifacts/day5/day1_diag_clipping_only_harmful_1.jsonl`
2. Run `python scripts/run_real_backbone_eval.py --mode pg_with_precedents --backend-name llama_guard --model-id meta-llama/Llama-Guard-3-1B --subset harmless_benign --limit 1 --output-file artifacts/day5/day1_diag_pg_with_precedents_benign_1.jsonl`
3. Compare per-sample runtime and precedent hit diagnostics.

## Hypotheses & Verification
| ID | Hypothesis | Likelihood | Effort | Evidence |
|----|------------|------------|--------|----------|
| A | Counterfactual recomputation over all parent nodes dominates runtime in `clipping_only` / `pg_with_precedents`. | High | Low | Confirmed. Hot-path `evidence_counterfactual_ms` is ~538-594 ms, larger than retrieval and precedent scoring. Cold-path wall time was mostly model load. |
| B | Precedent retrieval misses because the query and stored summaries are too prompt-only and ignore trajectory semantics. | High | Medium | Partially confirmed, then mitigated. Before alignment, `action_similarity` was ~0.08-0.10; after aligning query/store to shared `summary/action` text and stripping `Hint:`, top-match `action_similarity=1.0`. |
| C | PG has no benign gain because retrieved precedents are empty or label-skewed, so no independent signal reaches aggregation. | High | Low | Confirmed. With subset-only store, benign retrieval was all-safe. After switching to full-pool store, harmful analogues appear by `top5`, but active `top_k=2` is still safe-only and `per_precedent_delta` stays 0.0. |
| D | Current trajectory payload still includes low-information template text that increases token cost without increasing discriminative power. | Medium | Low | Confirmed and mitigated. Payloads were compacted by removing `tool_request/tool_plan/step_x_of_y` boilerplate and preserving tool/query/result semantics. |

## Log Evidence
- Instrumentation added in `precedentguard/guard.py` and `scripts/run_real_backbone_eval.py`:
  - `timing_ms.retrieval_ms / base_guard_ms / evidence_counterfactual_ms / precedent_counterfactual_ms / total_ms`
  - `retrieval_diagnostics.hit_count / label_distribution / top_matches`
  - `pg_delta / per_parent_delta / per_precedent_delta`
- Evidence files:
  - `artifacts/day5/day1_diag_clipping_only_harmful_2_compact.jsonl`
  - `artifacts/day5/day1_diag_pg_with_precedents_benign_2_delta.jsonl`
- Aggregated hot-path summary:
  - `clipping_only harmful`: cold `16.34s`, steady-state `0.676s`, with `base_guard_ms=137.7`, `evidence_counterfactual_ms=538.0`
  - `pg_with_precedents benign`: cold `13.27s`, steady-state `0.865s`, with `base_guard_ms=127.5`, `evidence_counterfactual_ms=593.8`, `precedent_counterfactual_ms=143.8`
- Retrieval-quality summary:
  - After query/store alignment, benign top-1 match reached `text_similarity=1.0`, `action_similarity=1.0`
  - Offline full-pool probe (`top5`) showed label mix `safe=3 / unsafe=2`; harmful analogues exist but are ranked behind safe near-duplicates
  - Active `top_k=2` remains safe-only on the checked benign pair, so PG independent contribution is still zero

## Verification Conclusion
- `clipping_only` and `pg_with_precedents` are already iterable in hot-path terms; the earlier “single-sample ~1 minute” diagnosis was polluted by model-load cold start.
- The current blocker has shifted from “retrieval miss” to “retrieval diversification + backend sensitivity”:
  1. Active PG retrieval needs a label-diverse or margin-aware strategy because harmful analogues are currently below safe near-duplicates.
  2. Even when a safe precedent is retrieved perfectly, `per_precedent_delta=0.0`, so the backbone prompt currently shows no sensitivity to precedent insertion on the checked benign pair.
- Next minimal move:
  - Keep active `precedent_top_k=1/2` for cost control.
  - Keep `retrieval_probe_top_k=5` for diagnostics.
  - Add a retrieval diversification experiment before expanding to `10+10` or full-slice.

## Follow-up Evidence: diversified retrieval
- Added `label_balanced` retrieval strategy in `precedentguard/retrieval.py`.
- Added CLI support in `scripts/run_real_backbone_eval.py`:
  - `--retrieval-strategy {vanilla,label_balanced}`
  - `--retrieval-probe-top-k 5`
- Added batch runner:
  - `scripts/run_day1_diversified_retrieval.sh`

### benign-2 comparison
- `vanilla`, `precedent_top_k=2`, `probe_top_k=5`
  - active selected labels: `safe=4, unsafe=0` across 2 examples
  - both examples stayed `safe+safe` in active top-2
- `label_balanced`, `precedent_top_k=2`, `probe_top_k=5`
  - active selected labels: `safe=2, unsafe=2` across 2 examples
  - both examples became `safe+unsafe` in active top-2
  - representative retrieved unsafe precedent:
    - `ah-harmful-1-3-caps-68e2b6d6e301b632`

### benign-10 label_balanced check
- File: `artifacts/day5/day1_pg_harmless_benign_10_label_balanced.jsonl`
- Summary:
  - `mixed_selected_examples = 8/10`
  - `retrieval_selected_label_distribution = safe=12, unsafe=8`
  - `nonzero_precedent_delta_examples = 0/10`
  - verdicts remain `10/10 block`

### Updated conclusion
- Diversified retrieval solved the *selection* problem: active top-2 is no longer monopolized by safe near-neighbors.
- Diversified retrieval did **not** solve the *contribution* problem: `per_precedent_delta` remains exactly `0.0`, even when a harmful analogue is actively selected.
- Therefore the next blocker is now isolated to **backend sensitivity to precedent context**, not retrieval quality.
