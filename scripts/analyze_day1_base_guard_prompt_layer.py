from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from scripts.run_real_backbone_eval import (
    build_eig,
    load_all_agentharm_rows,
    make_backend,
    make_guard,
    make_leave_one_out_precedent_store,
    make_query_texts,
    resolve_dataset_file,
)


def _mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-name", default="llama_guard")
    parser.add_argument("--model-id", default="meta-llama/Llama-Guard-3-1B")
    parser.add_argument(
        "--subset",
        default="harmless_benign",
        choices=["harmful", "harmless_benign"],
    )
    parser.add_argument("--dataset-file", default="")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--precedent-top-k", type=int, default=2)
    parser.add_argument("--retrieval-probe-top-k", type=int, default=5)
    parser.add_argument(
        "--retrieval-strategy",
        default="label_balanced",
        choices=["vanilla", "label_balanced"],
    )
    parser.add_argument("--precedent-safe-beta-scale", type=float, default=2.0)
    parser.add_argument("--precedent-unsafe-beta-scale", type=float, default=0.5)
    parser.add_argument(
        "--output-file",
        default="artifacts/day5/day1_benign10_base_guard_prompt_layer_diag.jsonl",
    )
    args = parser.parse_args()

    dataset_path = resolve_dataset_file(args.subset, args.dataset_file or None)
    all_rows = load_all_agentharm_rows(dataset_path)
    rows = [row for row in all_rows if row["subset"] == args.subset]
    if args.limit is not None:
        rows = rows[: args.limit]

    backend = make_backend(args.backend_name, args.model_id)
    out_path = Path(args.output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written_rows: list[dict] = []
    with out_path.open("w", encoding="utf-8") as out:
        for row in rows:
            eig, action_id = build_eig(
                row["id"],
                row["prompt"],
                row.get("trajectory", []),
            )
            query_summary, query_action = make_query_texts(
                row["prompt"],
                row.get("trajectory", []),
            )
            precedent_store = make_leave_one_out_precedent_store(
                all_rows,
                scope="agentharm",
                held_out_example_id=row["id"],
            )
            guard = make_guard(
                backend,
                store=precedent_store,
                top_k=args.precedent_top_k,
                retrieval_strategy=args.retrieval_strategy,
                precedent_safe_beta_scale=args.precedent_safe_beta_scale,
                precedent_unsafe_beta_scale=args.precedent_unsafe_beta_scale,
            )
            base_view = guard._base_view(eig)
            retrieved = guard._retrieve_precedents(
                eig,
                action_id,
                query_summary=query_summary,
                query_action=query_action,
            )
            retrieved_capsules = [rp.capsule for rp in retrieved]
            safe_capsules = [cap for cap in retrieved_capsules if cap.audited_label == 0]
            unsafe_capsules = [cap for cap in retrieved_capsules if cap.audited_label == 1]

            backbone_base_score = float(
                guard.base_guard(eig, action_id, base_view, precedents=[])
            )
            all_precedents_base_score = float(
                guard.base_guard(eig, action_id, base_view, precedents=retrieved_capsules)
            )
            safe_only_base_score = float(
                guard.base_guard(eig, action_id, base_view, precedents=safe_capsules)
            )
            unsafe_only_base_score = float(
                guard.base_guard(eig, action_id, base_view, precedents=unsafe_capsules)
            )

            result = {
                "example_id": row["id"],
                "subset": row["subset"],
                "category": row["category"],
                "retrieval_strategy": args.retrieval_strategy,
                "precedent_top_k": args.precedent_top_k,
                "retrieval_probe_top_k": args.retrieval_probe_top_k,
                "prompt_text": row["prompt"],
                "action_text": query_action,
                "backbone_base_score": backbone_base_score,
                "all_precedents_base_score": all_precedents_base_score,
                "safe_only_base_score": safe_only_base_score,
                "unsafe_only_base_score": unsafe_only_base_score,
                "all_precedents_inflation": all_precedents_base_score - backbone_base_score,
                "safe_only_inflation": safe_only_base_score - backbone_base_score,
                "unsafe_only_inflation": unsafe_only_base_score - backbone_base_score,
                "selected_label_distribution": {
                    "safe": len(safe_capsules),
                    "unsafe": len(unsafe_capsules),
                },
                "retrieved_precedents": [
                    {
                        "capsule_id": cap.capsule_id,
                        "audited_label": cap.audited_label,
                        "trajectory_summary": cap.trajectory_summary,
                        "proposed_action": cap.proposed_action,
                    }
                    for cap in retrieved_capsules
                ],
            }
            written_rows.append(result)
            out.write(json.dumps(result, ensure_ascii=True) + "\n")

    summary = {
        "n": len(written_rows),
        "mean_backbone_base_score": round(
            _mean([row["backbone_base_score"] for row in written_rows]), 6
        ),
        "mean_all_precedents_base_score": round(
            _mean([row["all_precedents_base_score"] for row in written_rows]), 6
        ),
        "mean_safe_only_base_score": round(
            _mean([row["safe_only_base_score"] for row in written_rows]), 6
        ),
        "mean_unsafe_only_base_score": round(
            _mean([row["unsafe_only_base_score"] for row in written_rows]), 6
        ),
        "mean_all_precedents_inflation": round(
            _mean([row["all_precedents_inflation"] for row in written_rows]), 6
        ),
        "mean_safe_only_inflation": round(
            _mean([row["safe_only_inflation"] for row in written_rows]), 6
        ),
        "mean_unsafe_only_inflation": round(
            _mean([row["unsafe_only_inflation"] for row in written_rows]), 6
        ),
        "examples_with_positive_safe_only_inflation": [
            row["example_id"]
            for row in written_rows
            if row["safe_only_inflation"] > 1e-9
        ],
        "examples_with_positive_unsafe_only_inflation": [
            row["example_id"]
            for row in written_rows
            if row["unsafe_only_inflation"] > 1e-9
        ],
        "examples_sorted_by_all_precedents_inflation": [
            {
                "example_id": row["example_id"],
                "all_precedents_inflation": round(row["all_precedents_inflation"], 6),
                "safe_only_inflation": round(row["safe_only_inflation"], 6),
                "unsafe_only_inflation": round(row["unsafe_only_inflation"], 6),
                "selected_label_distribution": row["selected_label_distribution"],
            }
            for row in sorted(
                written_rows,
                key=lambda item: item["all_precedents_inflation"],
                reverse=True,
            )
        ],
        "output_file": str(out_path),
    }
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
