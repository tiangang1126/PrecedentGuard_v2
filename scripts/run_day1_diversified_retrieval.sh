#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day5}"
BACKEND_NAME="${BACKEND_NAME:-llama_guard}"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-Guard-3-1B}"
SUBSET="${SUBSET:-harmless_benign}"
LIMIT="${LIMIT:-10}"
PRECEDENT_TOP_K="${PRECEDENT_TOP_K:-2}"
RETRIEVAL_PROBE_TOP_K="${RETRIEVAL_PROBE_TOP_K:-5}"

mkdir -p "$ARTIFACT_DIR"

run_eval() {
  local strategy="$1"
  local output_file="$ARTIFACT_DIR/day1_pg_${SUBSET}_${LIMIT}_${strategy}.jsonl"
  python scripts/run_real_backbone_eval.py \
    --mode pg_with_precedents \
    --backend-name "$BACKEND_NAME" \
    --model-id "$MODEL_ID" \
    --subset "$SUBSET" \
    --limit "$LIMIT" \
    --precedent-top-k "$PRECEDENT_TOP_K" \
    --retrieval-probe-top-k "$RETRIEVAL_PROBE_TOP_K" \
    --retrieval-strategy "$strategy" \
    --output-file "$output_file"
}

run_eval vanilla
run_eval label_balanced

python scripts/summarize_day1_iterability_diag.py \
  --input "$ARTIFACT_DIR/day1_pg_${SUBSET}_${LIMIT}_vanilla.jsonl" \
  --input "$ARTIFACT_DIR/day1_pg_${SUBSET}_${LIMIT}_label_balanced.jsonl"
