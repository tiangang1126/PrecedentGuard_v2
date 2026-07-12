#!/usr/bin/env bash
#
# scripts/run_day8_multibackbone_full.sh
#
# Run Day 8 multi-backbone full sweeps after the Day 7 LlamaGuard result is frozen.
# This wrapper reuses the overnight runner and launches ShieldGemma + Granite
# sequentially with fresh RUN_TAG / ARTIFACT_DIR / PREFIX values.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PG_BACKEND_DEVICE="${PG_BACKEND_DEVICE:-auto}"
PG_BACKEND_DTYPE="${PG_BACKEND_DTYPE:-float16}"
LIMIT="${LIMIT:-200}"
RUN_TAG_BASE="${RUN_TAG_BASE:-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_DIR="${LOG_DIR:-artifacts/logs}"
STATUS_LOG="${STATUS_LOG:-$LOG_DIR/day8_multibackbone_${RUN_TAG_BASE}.status.log}"
SHIELDGEMMA_MODEL_ID="${SHIELDGEMMA_MODEL_ID:-google/shieldgemma-2b}"
GRANITE_MODEL_ID="${GRANITE_MODEL_ID:-ibm-granite/granite-guardian-3.2-5b}"
DEFAULT_SHIELD_LOCAL_DIR="${DEFAULT_SHIELD_LOCAL_DIR:-artifacts/model_store/shieldgemma-2b}"

mkdir -p "$LOG_DIR"

if [[ "$SHIELDGEMMA_MODEL_ID" == "google/shieldgemma-2b" ]] && \
   [[ -f "$DEFAULT_SHIELD_LOCAL_DIR/config.json" ]] && \
   [[ -f "$DEFAULT_SHIELD_LOCAL_DIR/model-00001-of-00002.safetensors" ]] && \
   [[ -f "$DEFAULT_SHIELD_LOCAL_DIR/model-00002-of-00002.safetensors" ]]; then
  SHIELDGEMMA_MODEL_ID="$DEFAULT_SHIELD_LOCAL_DIR"
  echo "[day8] auto-using local ShieldGemma dir: $SHIELDGEMMA_MODEL_ID" | tee -a "$STATUS_LOG"
fi

is_model_access_blocked() {
  local logfile="$1"
  grep -Eq "MODEL_ACCESS_BLOCKED|gated repo|awaiting a review|Cannot access gated repo" "$logfile"
}

run_backend() {
  local backend_name="$1"
  local model_id="$2"
  local run_tag="${RUN_TAG_BASE}_${backend_name}"
  local prefix="day8_agentharm_full_${run_tag}"
  local sweep_log="$LOG_DIR/${prefix}_sweep.log"

  echo
  echo "[day8] backend=$backend_name model=$model_id"
  echo "[day8] run_tag=$run_tag"
  echo "[day8] sweep_log=$sweep_log"

  if RUN_TAG="$run_tag" \
    ARTIFACT_DIR="artifacts/day8_${run_tag}" \
    PREFIX="$prefix" \
    BACKEND_NAME="$backend_name" \
    MODEL_ID="$model_id" \
    LIMIT="$LIMIT" \
    LOG_DIR="$LOG_DIR" \
    PG_BACKEND_DEVICE="$PG_BACKEND_DEVICE" \
    PG_BACKEND_DTYPE="$PG_BACKEND_DTYPE" \
    bash scripts/run_day7_agentharm_full_overnight.sh; then
    echo "[day8] backend=$backend_name status=completed" | tee -a "$STATUS_LOG"
    return 0
  fi

  if [[ -f "$sweep_log" ]] && is_model_access_blocked "$sweep_log"; then
    echo "[day8] backend=$backend_name status=skipped_access_blocked model=$model_id" | tee -a "$STATUS_LOG"
    echo "[day8] skipping $backend_name because the model repository is gated or access is pending"
    return 0
  fi

  echo "[day8] backend=$backend_name status=failed_unexpected model=$model_id" | tee -a "$STATUS_LOG"
  echo "[day8] unexpected failure. inspect $sweep_log and stop the pipeline."
  return 1
}

run_backend shieldgemma "$SHIELDGEMMA_MODEL_ID"
run_backend granite_guardian "$GRANITE_MODEL_ID"

echo
echo "[day8] multi-backbone full sweeps complete"
echo "[day8] status_log=$STATUS_LOG"
