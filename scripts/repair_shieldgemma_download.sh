#!/usr/bin/env bash
#
# scripts/repair_shieldgemma_download.sh
#
# Repair a corrupted local/cached ShieldGemma download by removing the broken
# shard(s), re-downloading the required files, and validating the safetensors
# shards before Day 8 multi-backbone runs.

# set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_REPO="${MODEL_REPO:-google/shieldgemma-2b}"
LOCAL_DIR="${LOCAL_DIR:-$ROOT_DIR/artifacts/model_store/shieldgemma-2b}"
DOWNLOAD_CACHE_DIR="${DOWNLOAD_CACHE_DIR:-$LOCAL_DIR/.hf-download-cache}"

mkdir -p "$LOCAL_DIR"

echo "[shieldgemma] repo=$MODEL_REPO"
echo "[shieldgemma] local_dir=$LOCAL_DIR"
echo "[shieldgemma] download_cache_dir=$DOWNLOAD_CACHE_DIR"

echo "[shieldgemma] removing known-bad partial files (if present)"
rm -f \
  "$LOCAL_DIR/model-00001-of-00002.safetensors" \
  "$LOCAL_DIR/generation_config.json"
rm -rf "$DOWNLOAD_CACHE_DIR"
mkdir -p "$DOWNLOAD_CACHE_DIR"

echo "[shieldgemma] downloading model files"
HF_HOME="$DOWNLOAD_CACHE_DIR" \
  hf download "$MODEL_REPO" \
    --local-dir "$LOCAL_DIR" \
    --force-download \
    config.json \
    generation_config.json \
    model-00001-of-00002.safetensors \
    model-00002-of-00002.safetensors \
    model.safetensors.index.json \
    tokenizer.json \
    tokenizer_config.json \
    special_tokens_map.json

echo "[shieldgemma] validating downloaded files"
LOCAL_DIR="$LOCAL_DIR" python - <<'PY'
import os
from pathlib import Path
from safetensors import safe_open

local_dir = Path(os.environ["LOCAL_DIR"])
required = [
    "config.json",
    "generation_config.json",
    "model-00001-of-00002.safetensors",
    "model-00002-of-00002.safetensors",
    "model.safetensors.index.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
]
missing = [name for name in required if not (local_dir / name).is_file()]
if missing:
    raise SystemExit(f"missing files after download: {missing}")

zero_bytes = [name for name in required if (local_dir / name).stat().st_size == 0]
if zero_bytes:
    raise SystemExit(f"zero-byte files after download: {zero_bytes}")

for name in [
    "model-00001-of-00002.safetensors",
    "model-00002-of-00002.safetensors",
]:
    path = local_dir / name
    with safe_open(str(path), framework="pt") as f:
        keys = list(f.keys())
        if not keys:
            raise SystemExit(f"empty safetensors shard: {path}")
        print(f"[shieldgemma] validated {name}: tensors={len(keys)}")

print(f"[shieldgemma] validated local model dir: {local_dir}")
PY

echo
echo "[shieldgemma] download repaired successfully"
echo "[shieldgemma] next run command:"
echo "  SHIELDGEMMA_MODEL_ID=$LOCAL_DIR bash scripts/run_day8_multibackbone_full.sh"
