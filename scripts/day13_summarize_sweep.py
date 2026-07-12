"""
Day 13 sweep summariser — produces §7.1.b Table 2 (LOBTO primary result) as
markdown, including Wilson 95 % CIs, Fisher exact tests, and McNemar exact
tests when paired within-example data are available.

The script is stdlib-only (no scipy / numpy) so it runs in the same environment
as ``run_real_backbone_eval.py``. The Wilson interval uses the closed form; the
Fisher exact test uses hypergeometric enumeration; McNemar exact uses the
binomial two-tail with continuity applied.

Usage
-----
    PYTHONPATH=. python scripts/day13_summarize_sweep.py \
        --root artifacts/day13 \
        --prefix day13_lobto_llama_guard \
        --limit 200 \
        --output experiments/day13_lobto_table2.md

Outputs a self-contained markdown file suitable for direct paste into §7.1.b.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean
from typing import Iterable


# ----------------------------------------------------------------------
# Statistics utilities
# ----------------------------------------------------------------------


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score two-sided 95 % CI for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    return (lo, hi)


def _log_comb(n: int, k: int) -> float:
    """log(nCk) via lgamma to avoid overflow."""
    if k < 0 or k > n:
        return float("-inf")
    return (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
    )


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-tailed Fisher exact test on the 2x2 table ``[[a, b], [c, d]]``.

    Uses hypergeometric enumeration; sums probabilities of all tables with row
    and column marginals fixed whose probability is <= that of the observed
    table (Fisher's classical two-sided definition).
    """
    n = a + b + c + d
    r1 = a + b
    r2 = c + d
    c1 = a + c
    c2 = b + d

    def logp(k: int) -> float:
        return (
            _log_comb(r1, k)
            + _log_comb(r2, c1 - k)
            - _log_comb(n, c1)
        )

    if n == 0:
        return 1.0
    log_obs = logp(a)
    total_log = 0.0
    total_p = 0.0
    lo = max(0, c1 - r2)
    hi = min(r1, c1)
    obs_p = math.exp(log_obs)
    for k in range(lo, hi + 1):
        lp = logp(k)
        p = math.exp(lp)
        if p <= obs_p + 1e-12:
            total_p += p
    return min(1.0, total_p)


def mcnemar_exact_two_sided(b: int, c: int) -> float:
    """Exact two-sided McNemar test on discordant counts (b, c)."""
    n = b + c
    if n == 0:
        return 1.0
    # Probability of observing k successes under Binomial(n, 0.5)
    k_obs = min(b, c)
    total = 0.0
    for k in range(0, k_obs + 1):
        total += math.exp(_log_comb(n, k) - n * math.log(2))
    p = min(1.0, 2 * total)
    return p


# ----------------------------------------------------------------------
# JSONL parsing
# ----------------------------------------------------------------------


MODES_DEFAULT = [
    "backbone_only",
    "clipping_only",
    "pg_with_precedents",
    "flattened_trajectory",
    "raw_rag_concat",
    "cip_style",
    "sequential_graph",
    "random_graph",
]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(l) for l in path.open("r", encoding="utf-8") if l.strip()
    ]


def summarise_one_mode(rows: list[dict]) -> dict:
    if not rows:
        return {
            "n": 0,
            "block": 0,
            "block_rate": 0.0,
            "ci_lo": 0.0,
            "ci_hi": 0.0,
            "mean_base": 0.0,
            "mean_s_pg": 0.0,
            "mean_delta": 0.0,
            "nonzero_precedent_delta": 0,
        }
    n = len(rows)
    block = sum(1 for r in rows if r["verdict"] == "block")
    ci = wilson_ci(block, n)
    return {
        "n": n,
        "block": block,
        "block_rate": block / n,
        "ci_lo": ci[0],
        "ci_hi": ci[1],
        "mean_base": mean(r.get("base_score", 0.0) for r in rows),
        "mean_s_pg": mean(r.get("s_pg", 0.0) for r in rows),
        "mean_delta": mean(r.get("pg_delta", 0.0) for r in rows),
        "nonzero_precedent_delta": sum(
            1
            for r in rows
            if any(abs(v) > 1e-9 for v in r.get("per_precedent_delta", {}).values())
        ),
    }


def paired_transitions(a_rows: list[dict], b_rows: list[dict]) -> tuple[int, int, int, int]:
    """(a_block ^ b_block, a_block ^ b_allow, a_allow ^ b_block, a_allow ^ b_allow)."""
    idx_a = {r["example_id"]: r["verdict"] for r in a_rows}
    idx_b = {r["example_id"]: r["verdict"] for r in b_rows}
    common = idx_a.keys() & idx_b.keys()
    bb = ba = ab = aa = 0
    for eid in common:
        av, bv = idx_a[eid], idx_b[eid]
        if av == "block" and bv == "block":
            bb += 1
        elif av == "block" and bv == "allow":
            ba += 1
        elif av == "allow" and bv == "block":
            ab += 1
        else:
            aa += 1
    return bb, ba, ab, aa


# ----------------------------------------------------------------------
# Markdown emission
# ----------------------------------------------------------------------


def format_table_2(summaries: dict[str, dict[str, dict]], modes: list[str]) -> str:
    """Verdict counts + Wilson CIs table for §7.1.b."""
    lines = [
        "### Table 2 — LOBTO $n = 200$ primary result",
        "",
        "| Mode | Harmful block / n (TPR, 95 % Wilson CI) | Benign block / n (FPR, 95 % Wilson CI) | Mean $S_{PG}$ (harmful) | Mean $S_{PG}$ (benign) | Mean $\\Delta_{PG}$ (benign) |",
        "|---|---|---|---|---|---|",
    ]
    for mode in modes:
        h = summaries[mode].get("harmful")
        b = summaries[mode].get("harmless_benign")
        if not h or not b or h["n"] == 0 or b["n"] == 0:
            lines.append(
                f"| `{mode}` | *no data* | *no data* | — | — | — |"
            )
            continue
        lines.append(
            f"| `{mode}` | {h['block']} / {h['n']}, **{h['block_rate']:.3f}** "
            f"[{h['ci_lo']:.3f}, {h['ci_hi']:.3f}] | "
            f"{b['block']} / {b['n']}, **{b['block_rate']:.3f}** "
            f"[{b['ci_lo']:.3f}, {b['ci_hi']:.3f}] | "
            f"{h['mean_s_pg']:.3f} | {b['mean_s_pg']:.3f} | "
            f"**{b['mean_delta']:+.3f}** |"
        )
    return "\n".join(lines) + "\n"


def format_paired_tests(summaries, modes, ref: str = "backbone_only") -> str:
    """Fisher exact + McNemar exact tables for benign FPR contrasts vs ref."""
    lines = [
        f"### Table 2b — Paired benign-FPR contrasts vs `{ref}`",
        "",
        "| Contrast | 2x2 marginal | Fisher $p$ | McNemar transitions (ref→other block/allow) | McNemar exact $p$ |",
        "|---|---|---|---|---|",
    ]
    ref_rows = summaries[ref]["_harmless_benign_rows"]
    ref_block = sum(1 for r in ref_rows if r["verdict"] == "block")
    ref_allow = len(ref_rows) - ref_block
    for mode in modes:
        if mode == ref:
            continue
        other_rows = summaries[mode].get("_harmless_benign_rows", [])
        if not other_rows:
            continue
        oblock = sum(1 for r in other_rows if r["verdict"] == "block")
        oallow = len(other_rows) - oblock
        fisher_p = fisher_exact_two_sided(oblock, oallow, ref_block, ref_allow)
        bb, ba, ab, aa = paired_transitions(ref_rows, other_rows)
        mcnemar_p = mcnemar_exact_two_sided(ba, ab)
        lines.append(
            f"| `{mode}` vs `{ref}` | [[{oblock}, {oallow}], [{ref_block}, {ref_allow}]] | "
            f"{fisher_p:.4f} | {ref}→{mode}: block→block {bb}, block→allow {ba}, "
            f"allow→block {ab}, allow→allow {aa} | {mcnemar_p:.4f} |"
        )
    return "\n".join(lines) + "\n"


def format_headline_paragraph(summaries: dict, modes: list[str]) -> str:
    """Human-readable one-paragraph summary of the primary result."""
    def get(mode: str, subset: str, key: str, default=None):
        return summaries.get(mode, {}).get(subset, {}).get(key, default)

    bo_ben = get("backbone_only", "harmless_benign", "block_rate")
    co_ben = get("clipping_only", "harmless_benign", "block_rate")
    pg_ben = get("pg_with_precedents", "harmless_benign", "block_rate")
    bo_h = get("backbone_only", "harmful", "block_rate")
    pg_h = get("pg_with_precedents", "harmful", "block_rate")

    if bo_ben is None or pg_ben is None:
        return "*(headline paragraph unavailable — missing backbone_only or pg_with_precedents data)*\n"

    delta_pg = pg_ben - bo_ben
    delta_clip = (co_ben - bo_ben) if co_ben is not None else None

    p = (
        f"**Headline (LOBTO $n = "
        f"{get('backbone_only', 'harmless_benign', 'n')}$, Llama-Guard-3-1B).** "
        f"PG-full reduces benign block-rate from **{bo_ben:.3f}** (backbone) to "
        f"**{pg_ben:.3f}** ($\\Delta = {delta_pg:+.3f}$) "
    )
    if delta_clip is not None:
        p += (
            f"while clipping-only alone worsens it to **{co_ben:.3f}** "
            f"($\\Delta = {delta_clip:+.3f}$, §7.1.d anchor)"
        )
    if bo_h is not None and pg_h is not None:
        p += (
            f". Harmful blocking rate is **{pg_h:.3f}** for PG-full vs "
            f"**{bo_h:.3f}** for backbone."
        )
    p += "\n"
    return p


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="artifacts/day13")
    parser.add_argument("--prefix", default="day13_lobto_llama_guard")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument(
        "--modes",
        nargs="+",
        default=MODES_DEFAULT,
    )
    parser.add_argument(
        "--output",
        default="experiments/day13_lobto_table2.md",
    )
    args = parser.parse_args()

    root = Path(args.root)
    summaries: dict[str, dict] = {}
    for mode in args.modes:
        summaries[mode] = {}
        for subset in ("harmful", "harmless_benign"):
            path = root / f"{args.prefix}_{mode}_{subset}_{args.limit}.jsonl"
            rows = load_jsonl(path)
            summaries[mode][subset] = summarise_one_mode(rows)
            summaries[mode][f"_{subset}_rows"] = rows

    parts = [
        "# Day 13 LOBTO Sweep Summary",
        "",
        f"Root: `{args.root}`",
        f"Prefix: `{args.prefix}`",
        f"Limit: `{args.limit}`",
        f"Modes: {', '.join(f'`{m}`' for m in args.modes)}",
        "",
        format_table_2(summaries, args.modes),
    ]
    if summaries.get("backbone_only", {}).get("_harmless_benign_rows"):
        parts.append(format_paired_tests(summaries, args.modes, ref="backbone_only"))
    parts.append(format_headline_paragraph(summaries, args.modes))

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(parts), encoding="utf-8")
    print(f"[OUT] Wrote {args.output}")


if __name__ == "__main__":
    main()
