#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day5}"
BACKEND_NAME="${BACKEND_NAME:-llama_guard}"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-Guard-3-1B}"
PG_BACKEND_DEVICE="${PG_BACKEND_DEVICE:-auto}"
PG_BACKEND_DTYPE="${PG_BACKEND_DTYPE:-float16}"
LIMIT="${LIMIT:-10}"
PRECEDENT_TOP_K="${PRECEDENT_TOP_K:-2}"
RETRIEVAL_PROBE_TOP_K="${RETRIEVAL_PROBE_TOP_K:-5}"
RETRIEVAL_STRATEGY="${RETRIEVAL_STRATEGY:-label_balanced}"
PRECEDENT_SAFE_BETA_SCALE="${PRECEDENT_SAFE_BETA_SCALE:-2.0}"
PRECEDENT_UNSAFE_BETA_SCALE="${PRECEDENT_UNSAFE_BETA_SCALE:-0.5}"

mkdir -p "$ARTIFACT_DIR"
export PG_BACKEND_DEVICE
export PG_BACKEND_DTYPE

OUTFILE="${OUTFILE:-$ARTIFACT_DIR/day1_pg_harmful_${LIMIT}_label_balanced_prompt_repaired_v3.jsonl}"

python scripts/run_real_backbone_eval.py \
  --mode pg_with_precedents \
  --backend-name "$BACKEND_NAME" \
  --model-id "$MODEL_ID" \
  --subset harmful \
  --limit "$LIMIT" \
  --precedent-top-k "$PRECEDENT_TOP_K" \
  --retrieval-probe-top-k "$RETRIEVAL_PROBE_TOP_K" \
  --retrieval-strategy "$RETRIEVAL_STRATEGY" \
  --precedent-safe-beta-scale "$PRECEDENT_SAFE_BETA_SCALE" \
  --precedent-unsafe-beta-scale "$PRECEDENT_UNSAFE_BETA_SCALE" \
  --output-file "$OUTFILE"

python scripts/analyze_day1_precedent_prompt_repair.py \
  --backbone "$ARTIFACT_DIR/day1_triplet_logit_repaired_backbone_only_harmful_${LIMIT}.jsonl" \
  --before "$ARTIFACT_DIR/day1_triplet_logit_repaired_pg_with_precedents_harmful_${LIMIT}.jsonl" \
  --after "$OUTFILE"
