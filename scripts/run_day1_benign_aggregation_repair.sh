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
SAFE_BETA_SCALE="${SAFE_BETA_SCALE:-2.0}"
UNSAFE_BETA_SCALE="${UNSAFE_BETA_SCALE:-0.5}"

mkdir -p "$ARTIFACT_DIR"

BASELINE_OUT="$ARTIFACT_DIR/day1_pg_harmless_benign_${LIMIT}_label_balanced_baseline.jsonl"
REPAIRED_OUT="$ARTIFACT_DIR/day1_pg_harmless_benign_${LIMIT}_label_balanced_repaired.jsonl"

python scripts/run_real_backbone_eval.py \
  --mode pg_with_precedents \
  --backend-name "$BACKEND_NAME" \
  --model-id "$MODEL_ID" \
  --subset harmless_benign \
  --limit "$LIMIT" \
  --precedent-top-k "$PRECEDENT_TOP_K" \
  --retrieval-probe-top-k "$RETRIEVAL_PROBE_TOP_K" \
  --retrieval-strategy "$RETRIEVAL_STRATEGY" \
  --precedent-safe-beta-scale 1.0 \
  --precedent-unsafe-beta-scale 1.0 \
  --output-file "$BASELINE_OUT"

python scripts/run_real_backbone_eval.py \
  --mode pg_with_precedents \
  --backend-name "$BACKEND_NAME" \
  --model-id "$MODEL_ID" \
  --subset harmless_benign \
  --limit "$LIMIT" \
  --precedent-top-k "$PRECEDENT_TOP_K" \
  --retrieval-probe-top-k "$RETRIEVAL_PROBE_TOP_K" \
  --retrieval-strategy "$RETRIEVAL_STRATEGY" \
  --precedent-safe-beta-scale "$SAFE_BETA_SCALE" \
  --precedent-unsafe-beta-scale "$UNSAFE_BETA_SCALE" \
  --output-file "$REPAIRED_OUT"

python scripts/analyze_day1_benign_aggregation.py --input "$BASELINE_OUT"
python scripts/analyze_day1_benign_aggregation.py --input "$REPAIRED_OUT"
