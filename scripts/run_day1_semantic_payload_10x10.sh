#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="$ROOT_DIR/artifacts/day5"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-Guard-3-1B}"
BACKEND_NAME="${BACKEND_NAME:-llama_guard}"
LIMIT="${LIMIT:-10}"

mkdir -p "$ARTIFACT_DIR"

run_mode() {
  local mode="$1"
  local subset="$2"
  local outfile="$ARTIFACT_DIR/day1_${mode}_${subset}_${LIMIT}.jsonl"
  python "$ROOT_DIR/scripts/run_real_backbone_eval.py" \
    --mode "$mode" \
    --backend-name "$BACKEND_NAME" \
    --model-id "$MODEL_ID" \
    --subset "$subset" \
    --limit "$LIMIT" \
    --output-file "$outfile"
}

run_mode backbone_only harmful
run_mode backbone_only harmless_benign
run_mode clipping_only harmful
run_mode clipping_only harmless_benign
run_mode pg_with_precedents harmful
run_mode pg_with_precedents harmless_benign

python - <<'PY'
import json
from pathlib import Path

root = Path("artifacts/day5")
modes = ["backbone_only", "clipping_only", "pg_with_precedents"]
required = {
    "example_id",
    "subset",
    "category",
    "mode",
    "base_score",
    "s_pg",
    "verdict",
    "precedent_ids",
    "parent_ids",
}
print("=== Day 1 10x10 Summary ===")
for mode in modes:
    harmful = [json.loads(x) for x in (root / f"day1_{mode}_harmful_10.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    benign = [json.loads(x) for x in (root / f"day1_{mode}_harmless_benign_10.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    missing = sorted(required - set(harmful[0].keys()))
    tp = sum(r["verdict"] == "block" for r in harmful)
    fn = sum(r["verdict"] == "allow" for r in harmful)
    fp = sum(r["verdict"] == "block" for r in benign)
    tn = sum(r["verdict"] == "allow" for r in benign)
    mean_h = sum(r["s_pg"] for r in harmful) / len(harmful)
    mean_b = sum(r["s_pg"] for r in benign) / len(benign)
    print(mode, {
        "missing_fields": missing,
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "mean_h": round(mean_h, 3),
        "mean_b": round(mean_b, 3),
    })
PY
