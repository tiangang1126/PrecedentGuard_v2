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


def summarize(rows: list[dict], backbone_by_id: dict[str, dict] | None = None) -> dict:
    summary = {
        "n": len(rows),
        "block": sum(r["verdict"] == "block" for r in rows),
        "allow": sum(r["verdict"] == "allow" for r in rows),
        "mean_base_score": round(mean(r["base_score"] for r in rows), 6),
        "mean_s_pg": round(mean(r["s_pg"] for r in rows), 6),
        "mean_pg_delta": round(mean(r.get("pg_delta", 0.0) for r in rows), 6),
    }
    if backbone_by_id is not None:
        inflations = [
            row["base_score"] - backbone_by_id[row["example_id"]]["base_score"]
            for row in rows
        ]
        summary["mean_base_inflation_vs_backbone"] = round(mean(inflations), 6)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backbone", required=True)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    args = parser.parse_args()

    backbone = load_rows(Path(args.backbone))
    before = load_rows(Path(args.before))
    after = load_rows(Path(args.after))

    backbone_by_id = {r["example_id"]: r for r in backbone}
    before_by_id = {r["example_id"]: r for r in before}

    changed_examples = []
    for row_after in after:
        example_id = row_after["example_id"]
        row_before = before_by_id[example_id]
        row_backbone = backbone_by_id[example_id]
        if (
            abs(row_after["base_score"] - row_before["base_score"]) > 1e-9
            or abs(row_after["s_pg"] - row_before["s_pg"]) > 1e-9
            or row_after["verdict"] != row_before["verdict"]
        ):
            changed_examples.append(
                {
                    "example_id": example_id,
                    "backbone_base_score": round(row_backbone["base_score"], 6),
                    "before_base_score": round(row_before["base_score"], 6),
                    "after_base_score": round(row_after["base_score"], 6),
                    "before_base_inflation": round(
                        row_before["base_score"] - row_backbone["base_score"], 6
                    ),
                    "after_base_inflation": round(
                        row_after["base_score"] - row_backbone["base_score"], 6
                    ),
                    "before_s_pg": round(row_before["s_pg"], 6),
                    "after_s_pg": round(row_after["s_pg"], 6),
                    "before_verdict": row_before["verdict"],
                    "after_verdict": row_after["verdict"],
                }
            )

    print(json.dumps({"backbone": summarize(backbone)}, ensure_ascii=True))
    print(
        json.dumps(
            {"before": summarize(before, backbone_by_id=backbone_by_id)},
            ensure_ascii=True,
        )
    )
    print(
        json.dumps(
            {"after": summarize(after, backbone_by_id=backbone_by_id)},
            ensure_ascii=True,
        )
    )
    print(json.dumps({"changed_examples": changed_examples}, ensure_ascii=True))


if __name__ == "__main__":
    main()
