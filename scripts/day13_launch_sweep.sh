#!/usr/bin/env bash
#
# Day 13 LOBTO sweep launcher — Gate β primary data producer.
#
# One command runs the full 8-mode x 2-subset x n=200 sweep on
# Llama-Guard-3-1B under the leave-one-base-task-out precedent split
# (Day 10 audit BLOCKER-1 fix) with the label-balanced retrieval strategy,
# asymmetric precedent beta scaling from D-004, and policy-attested trust
# tier (the primary configuration).
#
# Resumable: existing JSONL files are NOT overwritten. If the sweep is
# interrupted, rerunning this script only executes the missing (mode,subset)
# pairs. This lets a wall-clock 6-8h run be split across two GPU sessions.
#
# Usage:
#   bash scripts/day13_launch_sweep.sh              # default n=200
#   N=100 bash scripts/day13_launch_sweep.sh        # smaller pilot
#   BACKEND=shieldgemma bash scripts/day13_launch_sweep.sh  # different backbone
#
# Env overrides:
#   N                — examples per subset (default 200)
#   BACKEND          — llama_guard | shieldgemma | granite_guardian
#   MODEL_ID         — HF model id
#   ARTIFACT_DIR     — output directory (default artifacts/day13)
#   PREFIX           — filename prefix (default day13_lobto)
#   TOP_K            — precedent top-k (default 2)
#   SAFE_BETA        — beta scale for safe precedents (default 2.0)
#   UNSAFE_BETA      — beta scale for unsafe precedents (default 0.5)
#   TRUST_VARIANT    — no_provenance | signature_only | lineage | policy_attested
#   MODES            — space-separated mode list to run (default all 8)
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

N="${N:-200}"
BACKEND="${BACKEND:-llama_guard}"
case "${BACKEND}" in
  llama_guard)     DEFAULT_MODEL="meta-llama/Llama-Guard-3-1B" ;;
  shieldgemma)     DEFAULT_MODEL="google/shieldgemma-2b" ;;
  granite_guardian) DEFAULT_MODEL="ibm-granite/granite-guardian-3.2-2b" ;;
  *) echo "unknown BACKEND ${BACKEND}" >&2; exit 2 ;;
esac
MODEL_ID="${MODEL_ID:-${DEFAULT_MODEL}}"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day13}"
PREFIX="${PREFIX:-day13_lobto_${BACKEND}}"
TOP_K="${TOP_K:-2}"
SAFE_BETA="${SAFE_BETA:-2.0}"
UNSAFE_BETA="${UNSAFE_BETA:-0.5}"
TRUST_VARIANT="${TRUST_VARIANT:-policy_attested}"

DEFAULT_MODES=(
  backbone_only
  clipping_only
  pg_with_precedents
  flattened_trajectory
  raw_rag_concat
  cip_style
  sequential_graph
  random_graph
)
if [ -n "${MODES:-}" ]; then
  read -r -a RUN_MODES <<< "${MODES}"
else
  RUN_MODES=("${DEFAULT_MODES[@]}")
fi

mkdir -p "${ARTIFACT_DIR}"

echo "== Day 13 LOBTO sweep =="
echo "backend      ${BACKEND}"
echo "model_id     ${MODEL_ID}"
echo "n            ${N}"
echo "top_k        ${TOP_K}"
echo "beta(s,u)    ${SAFE_BETA} / ${UNSAFE_BETA}"
echo "trust        ${TRUST_VARIANT}"
echo "artifact_dir ${ARTIFACT_DIR}"
echo "prefix       ${PREFIX}"
echo "modes        ${RUN_MODES[*]}"
echo

TOTAL_START=$(date +%s)
for MODE in "${RUN_MODES[@]}"; do
  for SUBSET in harmful harmless_benign; do
    OUT="${ARTIFACT_DIR}/${PREFIX}_${MODE}_${SUBSET}_${N}.jsonl"
    if [ -s "${OUT}" ]; then
      LINES=$(wc -l < "${OUT}")
      if [ "${LINES}" -ge "${N}" ]; then
        echo "[skip] ${OUT} (already has ${LINES} rows)"
        continue
      fi
      echo "[warn] ${OUT} exists with only ${LINES} rows; rerunning"
    fi
    echo "[run ] ${MODE} / ${SUBSET}  ->  ${OUT}"
    STAGE_START=$(date +%s)
    PYTHONPATH=. python scripts/run_real_backbone_eval.py \
      --mode "${MODE}" \
      --subset "${SUBSET}" \
      --limit "${N}" \
      --backend-name "${BACKEND}" \
      --model-id "${MODEL_ID}" \
      --precedent-top-k "${TOP_K}" \
      --retrieval-strategy label_balanced \
      --precedent-safe-beta-scale "${SAFE_BETA}" \
      --precedent-unsafe-beta-scale "${UNSAFE_BETA}" \
      --trust-variant "${TRUST_VARIANT}" \
      --output-file "${OUT}" \
      2>&1 | tail -3
    STAGE_END=$(date +%s)
    echo "[done] ${MODE} / ${SUBSET} in $((STAGE_END - STAGE_START))s"
  done
done
TOTAL_END=$(date +%s)

echo
echo "== Sweep complete =="
echo "wall clock: $((TOTAL_END - TOTAL_START))s"
echo "next: PYTHONPATH=. python scripts/day13_summarize_sweep.py --root ${ARTIFACT_DIR} --prefix ${PREFIX} --limit ${N}"
