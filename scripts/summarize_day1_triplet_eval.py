from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def load_rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize_file(path: Path) -> dict:
    rows = load_rows(path)
    if not rows:
        return {"path": str(path), "n": 0}

    subset = rows[0]["subset"]
    mode = rows[0]["mode"]
    block = sum(1 for row in rows if row["verdict"] == "block")
    allow = sum(1 for row in rows if row["verdict"] == "allow")
    mean_base = mean(row["base_score"] for row in rows)
    mean_spg = mean(row["s_pg"] for row in rows)
    mean_pg_delta = mean(row.get("pg_delta", 0.0) for row in rows)
    nonzero_pg_delta = sum(1 for row in rows if abs(row.get("pg_delta", 0.0)) > 1e-9)
    nonzero_precedent_delta = sum(
        1
        for row in rows
        if any(abs(v) > 1e-9 for v in row.get("per_precedent_delta", {}).values())
    )
    selected_safe = sum(
        row.get("retrieval_diagnostics", {})
        .get("selected_label_distribution", {})
        .get("safe", 0)
        for row in rows
    )
    selected_unsafe = sum(
        row.get("retrieval_diagnostics", {})
        .get("selected_label_distribution", {})
        .get("unsafe", 0)
        for row in rows
    )

    return {
        "path": str(path),
        "mode": mode,
        "subset": subset,
        "n": len(rows),
        "block": block,
        "allow": allow,
        "mean_base_score": round(mean_base, 6),
        "mean_s_pg": round(mean_spg, 6),
        "mean_pg_delta": round(mean_pg_delta, 6),
        "nonzero_pg_delta_examples": nonzero_pg_delta,
        "nonzero_precedent_delta_examples": nonzero_precedent_delta,
        "selected_safe": selected_safe,
        "selected_unsafe": selected_unsafe,
        "retrieval_strategy": rows[0].get("retrieval_strategy", "vanilla"),
        "precedent_safe_beta_scale": rows[0].get("precedent_safe_beta_scale", 1.0),
        "precedent_unsafe_beta_scale": rows[0].get("precedent_unsafe_beta_scale", 1.0),
    }


def print_triplet_summary(root: Path, prefix: str, limit: int) -> None:
    modes = ["backbone_only", "clipping_only", "pg_with_precedents"]
    subsets = ["harmful", "harmless_benign"]
    summary_by_key: dict[tuple[str, str], dict] = {}

    for mode in modes:
        for subset in subsets:
            path = root / f"{prefix}_{mode}_{subset}_{limit}.jsonl"
            summary = summarize_file(path)
            summary_by_key[(mode, subset)] = summary
            print(json.dumps(summary, ensure_ascii=True))

    benign_backbone = summary_by_key[("backbone_only", "harmless_benign")]
    benign_clipping = summary_by_key[("clipping_only", "harmless_benign")]
    benign_pg = summary_by_key[("pg_with_precedents", "harmless_benign")]
    harmful_backbone = summary_by_key[("backbone_only", "harmful")]
    harmful_clipping = summary_by_key[("clipping_only", "harmful")]
    harmful_pg = summary_by_key[("pg_with_precedents", "harmful")]

    comparison = {
        "benign_block_delta_pg_vs_backbone": benign_pg["block"] - benign_backbone["block"],
        "benign_block_delta_pg_vs_clipping": benign_pg["block"] - benign_clipping["block"],
        "benign_mean_s_pg_delta_pg_vs_backbone": round(
            benign_pg["mean_s_pg"] - benign_backbone["mean_s_pg"], 6
        ),
        "benign_mean_s_pg_delta_pg_vs_clipping": round(
            benign_pg["mean_s_pg"] - benign_clipping["mean_s_pg"], 6
        ),
        "harmful_block_delta_pg_vs_backbone": harmful_pg["block"] - harmful_backbone["block"],
        "harmful_block_delta_pg_vs_clipping": harmful_pg["block"] - harmful_clipping["block"],
        "pg_benign_nonzero_precedent_delta_examples": benign_pg["nonzero_precedent_delta_examples"],
        "pg_harmful_nonzero_precedent_delta_examples": harmful_pg["nonzero_precedent_delta_examples"],
    }
    print(json.dumps({"comparison": comparison}, ensure_ascii=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="artifacts/day5")
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--limit", type=int, required=True)
    args = parser.parse_args()

    print_triplet_summary(Path(args.root), args.prefix, args.limit)


if __name__ == "__main__":
    main()
