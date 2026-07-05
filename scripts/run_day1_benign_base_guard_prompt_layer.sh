#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_NAME="${BACKEND_NAME:-llama_guard}"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-Guard-3-1B}"
LIMIT="${LIMIT:-10}"
PRECEDENT_TOP_K="${PRECEDENT_TOP_K:-2}"
RETRIEVAL_PROBE_TOP_K="${RETRIEVAL_PROBE_TOP_K:-5}"
RETRIEVAL_STRATEGY="${RETRIEVAL_STRATEGY:-label_balanced}"
PRECEDENT_SAFE_BETA_SCALE="${PRECEDENT_SAFE_BETA_SCALE:-2.0}"
PRECEDENT_UNSAFE_BETA_SCALE="${PRECEDENT_UNSAFE_BETA_SCALE:-0.5}"
OUTFILE="${OUTFILE:-artifacts/day5/day1_benign10_base_guard_prompt_layer_diag.jsonl}"

python scripts/analyze_day1_base_guard_prompt_layer.py \
  --backend-name "$BACKEND_NAME" \
  --model-id "$MODEL_ID" \
  --subset harmless_benign \
  --limit "$LIMIT" \
  --precedent-top-k "$PRECEDENT_TOP_K" \
  --retrieval-probe-top-k "$RETRIEVAL_PROBE_TOP_K" \
  --retrieval-strategy "$RETRIEVAL_STRATEGY" \
  --precedent-safe-beta-scale "$PRECEDENT_SAFE_BETA_SCALE" \
  --precedent-unsafe-beta-scale "$PRECEDENT_UNSAFE_BETA_SCALE" \
  --output-file "$OUTFILE"
