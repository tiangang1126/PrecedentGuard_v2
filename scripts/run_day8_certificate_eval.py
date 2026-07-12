#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from precedentguard.certificate import (
    CertificateConfig,
    MarginSample,
    certify,
    commit_grid_hash,
)
from precedentguard.clipping import symmetric_caps
from precedentguard.types import NodeType


def parse_int_list(text: str) -> list[int]:
    values = [part.strip() for part in text.split(",") if part.strip()]
    if not values:
        raise ValueError("expected at least one integer value")
    return [int(v) for v in values]


def parse_float_list(text: str) -> list[float]:
    values = [part.strip() for part in text.split(",") if part.strip()]
    if not values:
        raise ValueError("expected at least one float value")
    return [float(v) for v in values]


def load_rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def expected_pg_paths(root: Path, prefix: str, limit: int) -> dict[str, Path]:
    return {
        subset: root / f"{prefix}_pg_with_precedents_{subset}_{limit}.jsonl"
        for subset in ("harmful", "harmless_benign")
    }


def discover_latest_pg_paths(limit: int, backend_name: str | None) -> dict[str, Path] | None:
    repo_root = Path.cwd()
    harmful_candidates = sorted(
        repo_root.glob(f"artifacts/day8_*/*_pg_with_precedents_harmful_{limit}.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for harmful_path in harmful_candidates:
        benign_path = Path(
            str(harmful_path).replace(
                "_pg_with_precedents_harmful_",
                "_pg_with_precedents_harmless_benign_",
            )
        )
        if not benign_path.is_file():
            continue
        if backend_name:
            needle = backend_name.lower()
            joined = f"{harmful_path.parent.name} {harmful_path.name}".lower()
            if needle not in joined:
                continue
        return {
            "harmful": harmful_path,
            "harmless_benign": benign_path,
        }
    return None


def resolve_pg_paths(
    root: Path,
    prefix: str,
    limit: int,
    backend_name: str | None,
) -> dict[str, Path]:
    paths = expected_pg_paths(root, prefix, limit)
    if all(path.is_file() for path in paths.values()):
        return paths

    discovered = discover_latest_pg_paths(limit=limit, backend_name=backend_name)
    if discovered is not None:
        return discovered

    missing = ", ".join(str(path) for path in paths.values() if not path.is_file())
    hint = (
        "Could not locate the expected Day 8 pg_with_precedents JSONL files. "
        f"Missing: {missing}. "
        "This usually means --root/--prefix was derived from an empty RUN_TAG_BASE "
        "or the Day 8 backbone run has not finished yet. "
        "Pass the concrete Day 8 artifact root/prefix, or set --backend-name so the script can "
        "auto-discover the latest successful run."
    )
    raise FileNotFoundError(hint)


def load_pg_rows(root: Path, prefix: str, limit: int, backend_name: str | None) -> tuple[list[dict], dict[str, Path]]:
    rows: list[dict] = []
    resolved_paths = resolve_pg_paths(root, prefix, limit, backend_name)
    for subset in ("harmful", "harmless_benign"):
        rows.extend(load_rows(resolved_paths[subset]))
    return rows, resolved_paths


def row_to_margin_sample(row: dict) -> MarginSample:
    subset = row["subset"]
    if subset == "harmful":
        label = 1
    elif subset == "harmless_benign":
        label = 0
    else:
        raise ValueError(f"unsupported subset for certificate eval: {subset}")
    return MarginSample(label=label, score=float(row["s_pg"]))


def stable_bucket(example_id: str, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}:{example_id}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 10_000


def split_rows(rows: list[dict], calibration_fraction: float, split_salt: str) -> tuple[list[dict], list[dict]]:
    if not (0.0 < calibration_fraction < 1.0):
        raise ValueError("calibration_fraction must be in (0, 1)")
    cutoff = int(calibration_fraction * 10_000)
    calibration: list[dict] = []
    evaluation: list[dict] = []
    for row in rows:
        bucket = stable_bucket(str(row["example_id"]), split_salt)
        target = calibration if bucket < cutoff else evaluation
        target.append(row)
    return calibration, evaluation


def empirical_risks(samples: list[MarginSample], theta: float) -> dict[str, float]:
    harmful = [s for s in samples if s.label == 1]
    benign = [s for s in samples if s.label == 0]
    if not harmful or not benign:
        raise ValueError("evaluation split must contain both harmful and benign samples")
    fnr = sum(1 for s in harmful if s.score < theta) / len(harmful)
    fpr = sum(1 for s in benign if s.score >= theta) / len(benign)
    return {
        "empirical_FNR": fnr,
        "empirical_FPR": fpr,
        "n_1_eval": len(harmful),
        "n_0_eval": len(benign),
    }


def make_grid(
    budget_values: list[int],
    *,
    theta: float,
    memory_cap: float,
    retrieval_cap: float,
    precedent_cap: float,
    eps_neg: float,
    eps_pos: float,
) -> list[CertificateConfig]:
    grid: list[CertificateConfig] = []
    for budget in budget_values:
        grid.append(
            CertificateConfig(
                theta=theta,
                caps_by_type={
                    NodeType.MEMORY: symmetric_caps(memory_cap),
                    NodeType.RETRIEVAL: symmetric_caps(retrieval_cap),
                    NodeType.PRECEDENT: symmetric_caps(precedent_cap),
                },
                eps_neg=eps_neg,
                eps_pos=eps_pos,
                m={
                    NodeType.MEMORY: budget,
                    NodeType.RETRIEVAL: budget,
                    NodeType.PRECEDENT: budget,
                },
                m_ins_unattested={
                    NodeType.MEMORY: 0,
                    NodeType.RETRIEVAL: 0,
                    NodeType.PRECEDENT: 0,
                },
            )
        )
    return grid


def result_record(
    *,
    budget: int,
    cert_obj,
    eval_metrics: dict[str, float],
) -> dict:
    gap_fn = cert_obj.U_FN - eval_metrics["empirical_FNR"]
    gap_fp = cert_obj.U_FP - eval_metrics["empirical_FPR"]
    return {
        "budget": budget,
        "U_FN": round(cert_obj.U_FN, 6),
        "U_FP": round(cert_obj.U_FP, 6),
        "R_hat_FN": round(cert_obj.R_hat_FN, 6),
        "R_hat_FP": round(cert_obj.R_hat_FP, 6),
        "empirical_FNR": round(eval_metrics["empirical_FNR"], 6),
        "empirical_FPR": round(eval_metrics["empirical_FPR"], 6),
        "gap_FN": round(gap_fn, 6),
        "gap_FP": round(gap_fp, 6),
        "rho_plus": round(cert_obj.rho_plus, 6),
        "rho_minus": round(cert_obj.rho_minus, 6),
        "n_1_cal": cert_obj.n_1,
        "n_0_cal": cert_obj.n_0,
        "n_1_eval": eval_metrics["n_1_eval"],
        "n_0_eval": eval_metrics["n_0_eval"],
        "valid_FN": eval_metrics["empirical_FNR"] <= cert_obj.U_FN,
        "valid_FP": eval_metrics["empirical_FPR"] <= cert_obj.U_FP,
        "non_vacuous_FN": cert_obj.non_vacuous_FN,
        "non_vacuous_FP": cert_obj.non_vacuous_FP,
    }


def summarize(records: list[dict]) -> dict:
    if not records:
        raise ValueError("no certificate records to summarize")
    non_vacuous_fn_ratio = sum(1 for r in records if r["non_vacuous_FN"]) / len(records)
    non_vacuous_fp_ratio = sum(1 for r in records if r["non_vacuous_FP"]) / len(records)

    breakdown_point = None
    for record in sorted(records, key=lambda r: r["budget"]):
        if not (record["non_vacuous_FN"] and record["non_vacuous_FP"]):
            breakdown_point = record["budget"]
            break

    return {
        "validity_FN_all": all(r["valid_FN"] for r in records),
        "validity_FP_all": all(r["valid_FP"] for r in records),
        "non_vacuous_FN_ratio": round(non_vacuous_fn_ratio, 6),
        "non_vacuous_FP_ratio": round(non_vacuous_fp_ratio, 6),
        "breakdown_point": breakdown_point,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--backend-name")
    parser.add_argument("--theta", type=float, default=0.5)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--alpha-grid", default="0.05")
    parser.add_argument("--budget-values", default="0,1,2,3")
    parser.add_argument("--memory-cap", type=float, default=0.30)
    parser.add_argument("--retrieval-cap", type=float, default=0.30)
    parser.add_argument("--precedent-cap", type=float, default=0.15)
    parser.add_argument("--eps-neg", type=float, default=1.0)
    parser.add_argument("--eps-pos", type=float, default=1.0)
    parser.add_argument("--calibration-fraction", type=float, default=0.5)
    parser.add_argument("--split-salt", default="day8_certificate_v1")
    parser.add_argument("--registry-path", default="experiments/registry.csv")
    parser.add_argument("--registry-tag", default="certificate_grid_day8")
    parser.add_argument("--commit-grid", action="store_true")
    parser.add_argument("--no-enforce-a5", action="store_true")
    parser.add_argument("--output-file")
    args = parser.parse_args()

    budget_values = parse_int_list(args.budget_values)
    alpha_grid = parse_float_list(args.alpha_grid)
    grid = make_grid(
        budget_values,
        theta=args.theta,
        memory_cap=args.memory_cap,
        retrieval_cap=args.retrieval_cap,
        precedent_cap=args.precedent_cap,
        eps_neg=args.eps_neg,
        eps_pos=args.eps_pos,
    )

    grid_hash_value = None
    if args.commit_grid:
        grid_hash_value = commit_grid_hash(
            grid,
            registry_path=args.registry_path,
            tag=args.registry_tag,
            alpha_grid=alpha_grid,
        )

    rows, resolved_paths = load_pg_rows(
        Path(args.root),
        args.prefix,
        args.limit,
        args.backend_name,
    )
    calibration_rows, evaluation_rows = split_rows(
        rows,
        calibration_fraction=args.calibration_fraction,
        split_salt=args.split_salt,
    )
    calibration_samples = [row_to_margin_sample(row) for row in calibration_rows]
    evaluation_samples = [row_to_margin_sample(row) for row in evaluation_rows]
    eval_metrics = empirical_risks(evaluation_samples, theta=args.theta)

    records: list[dict] = []
    for budget, config in zip(budget_values, grid):
        cert_obj = certify(
            cal_samples=calibration_samples,
            config=config,
            grid=grid,
            alpha=args.alpha,
            registry_path=args.registry_path,
            registry_tag=args.registry_tag,
            alpha_grid=alpha_grid,
            enforce_A5=not args.no_enforce_a5,
        )
        records.append(
            result_record(
                budget=budget,
                cert_obj=cert_obj,
                eval_metrics=eval_metrics,
            )
        )

    payload = {
        "root": args.root,
        "prefix": args.prefix,
        "backend_name": args.backend_name,
        "resolved_paths": {
            subset: str(path) for subset, path in resolved_paths.items()
        },
        "limit": args.limit,
        "theta": args.theta,
        "alpha": args.alpha,
        "alpha_grid": alpha_grid,
        "split": {
            "strategy": "stable_hash_by_example_id",
            "salt": args.split_salt,
            "calibration_fraction": args.calibration_fraction,
            "calibration_n": len(calibration_rows),
            "evaluation_n": len(evaluation_rows),
        },
        "grid": {
            "budget_values": budget_values,
            "memory_cap": args.memory_cap,
            "retrieval_cap": args.retrieval_cap,
            "precedent_cap": args.precedent_cap,
            "eps_neg": args.eps_neg,
            "eps_pos": args.eps_pos,
            "registry_tag": args.registry_tag,
            "registry_path": args.registry_path,
            "committed_hash": grid_hash_value,
        },
        "results": records,
        "summary": summarize(records),
    }

    text = json.dumps(payload, ensure_ascii=True, indent=2)
    if args.output_file:
        out_path = Path(args.output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
