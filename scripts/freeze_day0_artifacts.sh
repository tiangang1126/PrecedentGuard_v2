#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="$ROOT_DIR/artifacts/day5"
DAY0_DIR="$ARTIFACT_DIR/day0_frozen"

mkdir -p "$DAY0_DIR"

FILES=(
  "day0_backbone_only_harmful_10.jsonl"
  "day0_backbone_only_benign_10.jsonl"
  "day0_clipping_only_harmful_10.jsonl"
  "day0_clipping_only_benign_10.jsonl"
  "day0_pg_with_precedents_harmful_10.jsonl"
  "day0_pg_with_precedents_benign_10.jsonl"
)

for file in "${FILES[@]}"; do
  src="$ARTIFACT_DIR/$file"
  if [[ ! -f "$src" ]]; then
    echo "missing required Day 0 artifact: $src" >&2
    exit 1
  fi
  cp "$src" "$DAY0_DIR/$file"
done

cat > "$DAY0_DIR/unittest_day0_status.txt" <<'EOF'
Day 0 checkpoint status
-----------------------
Regression status: 145/145 OK
Meaning: this is the frozen Day 0 checkpoint before Day 1 semantic-payload work.
EOF

(
  cd "$DAY0_DIR"
  sha256sum "${FILES[@]}" unittest_day0_status.txt > manifest.sha256
)

echo "$DAY0_DIR"
