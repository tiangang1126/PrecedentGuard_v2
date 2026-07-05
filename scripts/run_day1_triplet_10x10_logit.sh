#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day5}"
BACKEND_NAME="${BACKEND_NAME:-llama_guard}"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-Guard-3-1B}"
LIMIT="${LIMIT:-10}"
PRECEDENT_TOP_K="${PRECEDENT_TOP_K:-2}"
RETRIEVAL_PROBE_TOP_K="${RETRIEVAL_PROBE_TOP_K:-5}"
RETRIEVAL_STRATEGY="${RETRIEVAL_STRATEGY:-label_balanced}"
PRECEDENT_SAFE_BETA_SCALE="${PRECEDENT_SAFE_BETA_SCALE:-2.0}"
PRECEDENT_UNSAFE_BETA_SCALE="${PRECEDENT_UNSAFE_BETA_SCALE:-0.5}"
PREFIX="${PREFIX:-day1_triplet_logit_repaired}"

mkdir -p "$ARTIFACT_DIR"

run_mode() {
  local mode="$1"
  local subset="$2"
  local outfile="$ARTIFACT_DIR/${PREFIX}_${mode}_${subset}_${LIMIT}.jsonl"
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
}

run_mode backbone_only harmful
run_mode backbone_only harmless_benign
run_mode clipping_only harmful
run_mode clipping_only harmless_benign
run_mode pg_with_precedents harmful
run_mode pg_with_precedents harmless_benign

python scripts/summarize_day1_triplet_eval.py \
  --root "$ARTIFACT_DIR" \
  --prefix "$PREFIX" \
  --limit "$LIMIT"
