#!/usr/bin/env bash
#
# Day 14 trust-variant sweep — produces §7.4 authenticity vs semantic
# authorization data.
#
# Runs pg_with_precedents under each of the four trust tiers (no_provenance,
# signature_only, lineage, policy_attested) x 2 subsets x n=200 on
# Llama-Guard-3-1B. Total 8 JSONL files.
#
# The policy_attested variant is skipped if the Day 13 primary sweep already
# produced its JSONL (recognised by identical prefix), since that is the same
# configuration. This makes the Day 14 sweep incremental.
#
# Usage:
#   bash scripts/day14_trust_variant_sweep.sh
#
# Env overrides:
#   N               — examples per subset (default 200)
#   BACKEND         — llama_guard | shieldgemma | granite_guardian
#   MODEL_ID        — HF model id
#   ARTIFACT_DIR    — output directory (default artifacts/day14)
#   PREFIX          — filename prefix (default day14_trust_${BACKEND})
#   DAY13_PREFIX    — Day 13 prefix to reuse policy_attested JSONL from
#                     (default day13_lobto_${BACKEND})
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
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/day14}"
PREFIX="${PREFIX:-day14_trust_${BACKEND}}"
DAY13_PREFIX="${DAY13_PREFIX:-day13_lobto_${BACKEND}}"

mkdir -p "${ARTIFACT_DIR}"

TRUST_TIERS=(no_provenance signature_only lineage policy_attested)

echo "== Day 14 trust variant sweep =="
echo "backend      ${BACKEND}"
echo "model_id     ${MODEL_ID}"
echo "n            ${N}"
echo "artifact_dir ${ARTIFACT_DIR}"
echo "prefix       ${PREFIX}"
echo "trust tiers  ${TRUST_TIERS[*]}"
echo

TOTAL_START=$(date +%s)
for TIER in "${TRUST_TIERS[@]}"; do
  for SUBSET in harmful harmless_benign; do
    OUT="${ARTIFACT_DIR}/${PREFIX}_${TIER}_${SUBSET}_${N}.jsonl"
    if [ -s "${OUT}" ]; then
      LINES=$(wc -l < "${OUT}")
      if [ "${LINES}" -ge "${N}" ]; then
        echo "[skip] ${OUT} (already has ${LINES} rows)"
        continue
      fi
    fi
    # Reuse Day 13 policy_attested JSONL to save GPU time (same config).
    if [ "${TIER}" = "policy_attested" ]; then
      DAY13_JSONL="artifacts/day13/${DAY13_PREFIX}_pg_with_precedents_${SUBSET}_${N}.jsonl"
      if [ -s "${DAY13_JSONL}" ]; then
        LINES=$(wc -l < "${DAY13_JSONL}")
        if [ "${LINES}" -ge "${N}" ]; then
          cp "${DAY13_JSONL}" "${OUT}"
          echo "[copy] ${OUT} <- ${DAY13_JSONL}"
          continue
        fi
      fi
    fi
    echo "[run ] trust=${TIER} / ${SUBSET}  ->  ${OUT}"
    STAGE_START=$(date +%s)
    PYTHONPATH=. python scripts/run_real_backbone_eval.py \
      --mode pg_with_precedents \
      --subset "${SUBSET}" \
      --limit "${N}" \
      --backend-name "${BACKEND}" \
      --model-id "${MODEL_ID}" \
      --precedent-top-k 2 \
      --retrieval-strategy label_balanced \
      --precedent-safe-beta-scale 2.0 \
      --precedent-unsafe-beta-scale 0.5 \
      --trust-variant "${TIER}" \
      --output-file "${OUT}" \
      2>&1 | tail -3
    STAGE_END=$(date +%s)
    echo "[done] trust=${TIER} / ${SUBSET} in $((STAGE_END - STAGE_START))s"
  done
done
TOTAL_END=$(date +%s)

echo
echo "== Trust variant sweep complete =="
echo "wall clock: $((TOTAL_END - TOTAL_START))s"
echo "next: PYTHONPATH=. python scripts/day14_summarize_trust.py --root ${ARTIFACT_DIR} --prefix ${PREFIX} --limit ${N}"
