#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day5}"
BACKEND_NAME="${BACKEND_NAME:-llama_guard}"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-Guard-3-1B}"
SUBSET="${SUBSET:-harmless_benign}"
LIMIT="${LIMIT:-2}"
PRECEDENT_TOP_K="${PRECEDENT_TOP_K:-2}"
RETRIEVAL_PROBE_TOP_K="${RETRIEVAL_PROBE_TOP_K:-5}"
RETRIEVAL_STRATEGY="${RETRIEVAL_STRATEGY:-label_balanced}"

mkdir -p "$ARTIFACT_DIR"

OUTPUT_FILE="$ARTIFACT_DIR/day1_pg_${SUBSET}_${LIMIT}_${RETRIEVAL_STRATEGY}_prompt_sensitive.jsonl"

python scripts/run_real_backbone_eval.py \
  --mode pg_with_precedents \
  --backend-name "$BACKEND_NAME" \
  --model-id "$MODEL_ID" \
  --subset "$SUBSET" \
  --limit "$LIMIT" \
  --precedent-top-k "$PRECEDENT_TOP_K" \
  --retrieval-probe-top-k "$RETRIEVAL_PROBE_TOP_K" \
  --retrieval-strategy "$RETRIEVAL_STRATEGY" \
  --output-file "$OUTPUT_FILE"

python scripts/summarize_day1_iterability_diag.py \
  --input "$OUTPUT_FILE"
