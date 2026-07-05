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


def summarize(path: Path) -> dict:
    rows = load_rows(path)
    if not rows:
        return {"path": str(path), "n": 0}

    def hot_rows() -> list[dict]:
        return rows[1:] if len(rows) > 1 else rows

    def avg(metric: str, subset: list[dict]) -> float:
        values = [row["timing_ms"].get(metric, 0.0) for row in subset]
        return round(mean(values), 3) if values else 0.0

    label_distribution = {"safe": 0, "unsafe": 0}
    selected_label_distribution = {"safe": 0, "unsafe": 0}
    top_matches = []
    nonzero_pg_delta = 0
    nonzero_precedent_delta = 0
    for row in rows:
        diag = row.get("retrieval_diagnostics", {})
        label_distribution["safe"] += diag.get("label_distribution", {}).get("safe", 0)
        label_distribution["unsafe"] += diag.get("label_distribution", {}).get("unsafe", 0)
        selected_label_distribution["safe"] += diag.get("selected_label_distribution", {}).get("safe", 0)
        selected_label_distribution["unsafe"] += diag.get("selected_label_distribution", {}).get("unsafe", 0)
        top_matches.extend(diag.get("top_matches", []))
        if abs(row.get("pg_delta", 0.0)) > 1e-9:
            nonzero_pg_delta += 1
        if any(abs(v) > 1e-9 for v in row.get("per_precedent_delta", {}).values()):
            nonzero_precedent_delta += 1

    return {
        "path": str(path),
        "mode": rows[0]["mode"],
        "subset": rows[0]["subset"],
        "n": len(rows),
        "retrieval_strategy": rows[0].get("retrieval_strategy", "vanilla"),
        "cold_sample_wall_clock_ms": round(rows[0]["timing_ms"].get("sample_wall_clock_ms", 0.0), 3),
        "steady_sample_wall_clock_ms": avg("sample_wall_clock_ms", hot_rows()),
        "steady_base_guard_ms": avg("base_guard_ms", hot_rows()),
        "steady_evidence_counterfactual_ms": avg("evidence_counterfactual_ms", hot_rows()),
        "steady_precedent_counterfactual_ms": avg("precedent_counterfactual_ms", hot_rows()),
        "avg_hit_count": round(mean(row.get("retrieval_diagnostics", {}).get("hit_count", 0) for row in rows), 3),
        "retrieval_probe_label_distribution": label_distribution,
        "retrieval_selected_label_distribution": selected_label_distribution,
        "avg_top_text_similarity": round(mean(match.get("text_similarity", 0.0) for match in top_matches), 3) if top_matches else 0.0,
        "avg_top_action_similarity": round(mean(match.get("action_similarity", 0.0) for match in top_matches), 3) if top_matches else 0.0,
        "nonzero_pg_delta_examples": nonzero_pg_delta,
        "nonzero_precedent_delta_examples": nonzero_precedent_delta,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    args = parser.parse_args()

    for item in args.input:
        print(json.dumps(summarize(Path(item)), ensure_ascii=True))


if __name__ == "__main__":
    main()
