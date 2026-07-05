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


def selected_matches(row: dict) -> dict[str, dict]:
    return {
        item["capsule_id"]: item
        for item in row.get("retrieval_diagnostics", {}).get("top_matches", [])
        if item.get("selected")
    }


def analyze(rows: list[dict]) -> dict:
    positives = [r for r in rows if r["pg_delta"] > 1e-9]
    negatives = [r for r in rows if r["pg_delta"] < -1e-9]

    def contribution_stats(group: list[dict]) -> dict:
        safe_weighted: list[float] = []
        unsafe_weighted: list[float] = []
        examples: list[str] = []

        for row in group:
            examples.append(row["example_id"])
            selected = selected_matches(row)
            for pid, pg_clipped in row.get("per_precedent_pg_clipped", {}).items():
                capsule_id = pid.split("precedent:", 1)[1]
                match = selected.get(capsule_id)
                if not match:
                    continue
                weighted = pg_clipped * match["normalized_weight"]
                if match["audited_label"] == 0:
                    safe_weighted.append(weighted)
                else:
                    unsafe_weighted.append(weighted)

        return {
            "examples": examples,
            "safe_weighted_mean": round(mean(safe_weighted), 6) if safe_weighted else 0.0,
            "unsafe_weighted_mean": round(mean(unsafe_weighted), 6) if unsafe_weighted else 0.0,
            "safe_weighted_sum": round(sum(safe_weighted), 6),
            "unsafe_weighted_sum": round(sum(unsafe_weighted), 6),
        }

    return {
        "n": len(rows),
        "positive_pg_delta_examples": len(positives),
        "negative_pg_delta_examples": len(negatives),
        "positive_group": contribution_stats(positives),
        "negative_group": contribution_stats(negatives),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    rows = load_rows(Path(args.input))
    print(json.dumps(analyze(rows), ensure_ascii=True))


if __name__ == "__main__":
    main()
