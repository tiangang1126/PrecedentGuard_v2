#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day5}"
BACKEND_NAME="${BACKEND_NAME:-llama_guard}"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-Guard-3-1B}"
PRECEDENT_TOP_K="${PRECEDENT_TOP_K:-1}"

mkdir -p "$ARTIFACT_DIR"

CLIPPING_OUT="$ARTIFACT_DIR/day1_diag_clipping_only_harmful_2.jsonl"
PG_OUT="$ARTIFACT_DIR/day1_diag_pg_with_precedents_benign_2.jsonl"

python scripts/run_real_backbone_eval.py \
  --mode clipping_only \
  --backend-name "$BACKEND_NAME" \
  --model-id "$MODEL_ID" \
  --subset harmful \
  --limit 2 \
  --output-file "$CLIPPING_OUT"

python scripts/run_real_backbone_eval.py \
  --mode pg_with_precedents \
  --backend-name "$BACKEND_NAME" \
  --model-id "$MODEL_ID" \
  --subset harmless_benign \
  --limit 2 \
  --precedent-top-k "$PRECEDENT_TOP_K" \
  --output-file "$PG_OUT"

python scripts/summarize_day1_iterability_diag.py \
  --input "$CLIPPING_OUT" \
  --input "$PG_OUT"
