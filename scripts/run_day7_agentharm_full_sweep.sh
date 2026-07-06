#!/usr/bin/env bash
#
# scripts/run_day7_agentharm_full_sweep.sh
#
# Full-scale test-set sweep on AgentHarm public with Llama-Guard-3-1B.
# Runs the three-mode triplet (backbone_only / clipping_only / pg_with_precedents)
# across both subsets (harmful, harmless_benign) at n = LIMIT per subset.
#
# Default LIMIT = 200 (well within the 208 safe / 260 unsafe totals).
# Prefix defaults to `day7_agentharm_full` and is written to artifacts/day6/.
#
# Environment overrides:
#   ARTIFACT_DIR          artifacts/day6            output dir
#   BACKEND_NAME          llama_guard               backends: llama_guard | shieldgemma | granite_guardian
#   MODEL_ID              meta-llama/Llama-Guard-3-1B
#   LIMIT                 200                       examples per subset
#   PRECEDENT_TOP_K       2
#   RETRIEVAL_PROBE_TOP_K 5
#   RETRIEVAL_STRATEGY    label_balanced            {vanilla, label_balanced}
#   PG_BACKEND_DEVICE     auto                      auto | cuda | cpu
#   PG_BACKEND_DTYPE      float16                   float16 | bfloat16 | float32
#   PRECEDENT_SAFE_BETA_SCALE   2.0
#   PRECEDENT_UNSAFE_BETA_SCALE 0.5
#   PREFIX                day7_agentharm_full
#
# Assumption A5 (grid pre-commitment): pair this run with commit_grid_hash
# BEFORE execution (see experiments/registry.csv).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day6}"
BACKEND_NAME="${BACKEND_NAME:-llama_guard}"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-Guard-3-1B}"
PG_BACKEND_DEVICE="${PG_BACKEND_DEVICE:-auto}"
PG_BACKEND_DTYPE="${PG_BACKEND_DTYPE:-float16}"
LIMIT="${LIMIT:-200}"
PRECEDENT_TOP_K="${PRECEDENT_TOP_K:-2}"
RETRIEVAL_PROBE_TOP_K="${RETRIEVAL_PROBE_TOP_K:-5}"
RETRIEVAL_STRATEGY="${RETRIEVAL_STRATEGY:-label_balanced}"
PRECEDENT_SAFE_BETA_SCALE="${PRECEDENT_SAFE_BETA_SCALE:-2.0}"
PRECEDENT_UNSAFE_BETA_SCALE="${PRECEDENT_UNSAFE_BETA_SCALE:-0.5}"
PREFIX="${PREFIX:-day7_agentharm_full}"

mkdir -p "$ARTIFACT_DIR"
export PG_BACKEND_DEVICE
export PG_BACKEND_DTYPE

echo "[Day 7 full sweep] backend=$BACKEND_NAME model=$MODEL_ID limit=$LIMIT"
echo "[Day 7 full sweep] artifact_dir=$ARTIFACT_DIR prefix=$PREFIX"
echo "[Day 7 full sweep] device=$PG_BACKEND_DEVICE dtype=$PG_BACKEND_DTYPE"
echo "[Day 7 full sweep] strategy=$RETRIEVAL_STRATEGY beta_safe=$PRECEDENT_SAFE_BETA_SCALE beta_unsafe=$PRECEDENT_UNSAFE_BETA_SCALE"
echo

run_mode() {
  local mode="$1"
  local subset="$2"
  local outfile="$ARTIFACT_DIR/${PREFIX}_${mode}_${subset}_${LIMIT}.jsonl"
  echo "[$(date -u +%FT%TZ)] START mode=$mode subset=$subset -> $outfile"
  python scripts/run_real_backbone_eval.py \
    --mode "$mode" \
    --backend-name "$BACKEND_NAME" \
    --model-id "$MODEL_ID" \
    --subset "$subset" \
    --limit "$LIMIT" \
    --precedent-top-k "$PRECEDENT_TOP_K" \
    --retrieval-probe-top-k "$RETRIEVAL_PROBE_TOP_K" \
    --retrieval-strategy "$RETRIEVAL_STRATEGY" \
    --precedent-safe-beta-scale "$PRECEDENT_SAFE_BETA_SCALE" \
    --precedent-unsafe-beta-scale "$PRECEDENT_UNSAFE_BETA_SCALE" \
    --output-file "$outfile"
  echo "[$(date -u +%FT%TZ)] DONE  mode=$mode subset=$subset"
}

# Order chosen to fail fast: cheapest first
run_mode backbone_only harmful
run_mode backbone_only harmless_benign
run_mode clipping_only harmful
run_mode clipping_only harmless_benign
run_mode pg_with_precedents harmful
run_mode pg_with_precedents harmless_benign

echo
echo "[Day 7 full sweep] all 6 runs complete"
echo "Summarize with:"
echo "  PYTHONPATH=. python scripts/summarize_day1_triplet_eval.py --root $ARTIFACT_DIR --prefix $PREFIX --limit $LIMIT"
