"""
Day 14 trust-variant summariser — produces §7.4 authenticity vs semantic
authorization table.

For each of the four trust tiers, computes benign block-rate + harmful
block-rate + mean pg_delta on the benign subset, plus Fisher exact tests
against the no_provenance baseline (the weakest tier). The key claim §7.4
must support is: pg_delta on benign is bounded below by 0 for the un-attested
tiers (no_provenance, signature_only, lineage) but can go negative under
policy_attested. That monotonicity is the empirical evidence for directional
trust as the load-bearing mechanism.

Usage:
    PYTHONPATH=. python scripts/day14_summarize_trust.py \
        --root artifacts/day14 --prefix day14_trust_llama_guard --limit 200
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean


TIERS = ["no_provenance", "signature_only", "lineage", "policy_attested"]


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def _log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    n = a + b + c + d
    r1 = a + b
    r2 = c + d
    c1 = a + c
    if n == 0:
        return 1.0
    obs_lp = _log_comb(r1, a) + _log_comb(r2, c1 - a) - _log_comb(n, c1)
    obs_p = math.exp(obs_lp)
    total_p = 0.0
    for k in range(max(0, c1 - r2), min(r1, c1) + 1):
        lp = _log_comb(r1, k) + _log_comb(r2, c1 - k) - _log_comb(n, c1)
        p = math.exp(lp)
        if p <= obs_p + 1e-12:
            total_p += p
    return min(1.0, total_p)


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.open("r", encoding="utf-8") if l.strip()]


def summarise(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "block": 0, "block_rate": 0.0, "ci": (0.0, 0.0),
                "mean_delta": 0.0, "negative_delta_frac": 0.0}
    n = len(rows)
    block = sum(1 for r in rows if r["verdict"] == "block")
    deltas = [r.get("pg_delta", 0.0) for r in rows]
    neg = sum(1 for d in deltas if d < -1e-9)
    return {
        "n": n,
        "block": block,
        "block_rate": block / n,
        "ci": wilson_ci(block, n),
        "mean_delta": mean(deltas),
        "negative_delta_frac": neg / n,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="artifacts/day14")
    parser.add_argument("--prefix", default="day14_trust_llama_guard")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument(
        "--output", default="experiments/day14_trust_table4.md"
    )
    args = parser.parse_args()

    root = Path(args.root)
    per_tier: dict[str, dict[str, dict]] = {}
    for tier in TIERS:
        per_tier[tier] = {}
        for subset in ("harmful", "harmless_benign"):
            path = root / f"{args.prefix}_{tier}_{subset}_{args.limit}.jsonl"
            per_tier[tier][subset] = summarise(load(path))

    lines = [
        "# Day 14 Trust Variant Summary — §7.4 authenticity vs semantic authorization",
        "",
        f"Root: `{args.root}`",
        f"Prefix: `{args.prefix}`",
        f"Limit: `{args.limit}`",
        "",
        "### Table 4a — Trust tier block-rate and directional delta",
        "",
        "| Trust tier | Harmful block / n (TPR, 95 % CI) | Benign block / n (FPR, 95 % CI) | Mean $\\Delta_{PG}$ (benign) | Negative-$\\Delta_{PG}$ frac (benign) |",
        "|---|---|---|---|---|",
    ]
    for tier in TIERS:
        h = per_tier[tier]["harmful"]
        b = per_tier[tier]["harmless_benign"]
        if h["n"] == 0 or b["n"] == 0:
            lines.append(f"| `{tier}` | *no data* | *no data* | — | — |")
            continue
        lines.append(
            f"| `{tier}` | {h['block']} / {h['n']}, **{h['block_rate']:.3f}** "
            f"[{h['ci'][0]:.3f}, {h['ci'][1]:.3f}] | "
            f"{b['block']} / {b['n']}, **{b['block_rate']:.3f}** "
            f"[{b['ci'][0]:.3f}, {b['ci'][1]:.3f}] | "
            f"**{b['mean_delta']:+.3f}** | {b['negative_delta_frac']:.3f} |"
        )
    lines.append("")

    # Fisher tests: each tier vs no_provenance (the weakest tier)
    lines.extend([
        "### Table 4b — Fisher exact benign-FPR contrast vs `no_provenance`",
        "",
        "| Tier | 2x2 (tier vs no_provenance) | Fisher $p$ |",
        "|---|---|---|",
    ])
    ref = per_tier["no_provenance"]["harmless_benign"]
    for tier in TIERS[1:]:
        b = per_tier[tier]["harmless_benign"]
        if b["n"] == 0 or ref["n"] == 0:
            continue
        p = fisher_exact_two_sided(
            b["block"], b["n"] - b["block"],
            ref["block"], ref["n"] - ref["block"],
        )
        lines.append(
            f"| `{tier}` | [[{b['block']}, {b['n'] - b['block']}], "
            f"[{ref['block']}, {ref['n'] - ref['block']}]] | {p:.4f} |"
        )
    lines.append("")

    # Directional-monotone check
    lines.extend([
        "### Directional-monotone check (H3 from `docs/RESEARCH_SPEC.md`)",
        "",
        "H3 predicts that only `policy_attested` can produce negative "
        "$\\Delta_{PG}$ on benign examples; the un-attested tiers "
        "(`no_provenance`, `signature_only`, `lineage`) should have "
        "`negative_delta_frac` $\\le 0.05$ under the directional-trust rule.",
        "",
    ])
    all_ok = True
    for tier in TIERS[:3]:
        b = per_tier[tier]["harmless_benign"]
        if b["n"] == 0:
            continue
        frac = b["negative_delta_frac"]
        ok = frac <= 0.05
        all_ok = all_ok and ok
        status = "PASS" if ok else "FAIL"
        lines.append(
            f"- `{tier}`: negative-$\\Delta$ frac = {frac:.3f} — {status}"
        )
    pol = per_tier["policy_attested"]["harmless_benign"]
    if pol["n"] > 0:
        frac = pol["negative_delta_frac"]
        ok = frac > 0.10
        status = "PASS" if ok else "FAIL"
        all_ok = all_ok and ok
        lines.append(
            f"- `policy_attested`: negative-$\\Delta$ frac = {frac:.3f} "
            f"(expected > 0.10) — {status}"
        )
    lines.append(f"\n**H3 verdict: {'PASS' if all_ok else 'FAIL'}**")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OUT] Wrote {args.output}")


if __name__ == "__main__":
    main()
