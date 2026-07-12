#!/usr/bin/env bash
#
# scripts/run_day7_agentharm_full_overnight.sh
#
# Overnight runner for the Day 7 full AgentHarm sweep.
# It forces a fresh ARTIFACT_DIR + PREFIX by default so we do not reuse
# stale/corrupted mounted-filesystem entries from prior failed runs.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_TAG="${RUN_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day6_${RUN_TAG}}"
PREFIX="${PREFIX:-day7_agentharm_full_${RUN_TAG}}"
LIMIT="${LIMIT:-200}"
PG_BACKEND_DEVICE="${PG_BACKEND_DEVICE:-auto}"
PG_BACKEND_DTYPE="${PG_BACKEND_DTYPE:-float16}"
LOG_DIR="${LOG_DIR:-artifacts/logs}"

mkdir -p "$ARTIFACT_DIR" "$LOG_DIR"

SWEEP_LOG="$LOG_DIR/${PREFIX}_sweep.log"
SUMMARY_LOG="$LOG_DIR/${PREFIX}_summary.log"
GATE_LOG="$LOG_DIR/${PREFIX}_gate_beta.log"

export ARTIFACT_DIR
export PREFIX
export LIMIT
export PG_BACKEND_DEVICE
export PG_BACKEND_DTYPE

echo "[overnight] run_tag=$RUN_TAG"
echo "[overnight] artifact_dir=$ARTIFACT_DIR"
echo "[overnight] prefix=$PREFIX"
echo "[overnight] device=$PG_BACKEND_DEVICE dtype=$PG_BACKEND_DTYPE"
echo "[overnight] logs:"
echo "  sweep   -> $SWEEP_LOG"
echo "  summary -> $SUMMARY_LOG"
echo "  gate    -> $GATE_LOG"
echo

echo "[overnight] starting full sweep"
bash scripts/run_day7_agentharm_full_sweep.sh | tee "$SWEEP_LOG"

echo
echo "[overnight] summarizing triplet results"
PYTHONPATH=. python scripts/summarize_day1_triplet_eval.py \
  --root "$ARTIFACT_DIR" \
  --prefix "$PREFIX" \
  --limit "$LIMIT" | tee "$SUMMARY_LOG"

echo
echo "[overnight] judging Gate beta"
PYTHONPATH=. python scripts/judge_day7_gate_beta.py \
  --root "$ARTIFACT_DIR" \
  --prefix "$PREFIX" \
  --limit "$LIMIT" \
  --dev-root artifacts/day5 \
  --dev-prefix day1_triplet_logit_prompt_repaired_v3_dev50 \
  --dev-limit 50 | tee "$GATE_LOG"

echo
echo "[overnight] complete"
echo "[overnight] next file to inspect: $GATE_LOG"
