"""Aggregate per-model eval results into a single comparison table.

Reads results/eval/{model}_results.json for each model found, emits:
  - results/eval/comparison_table.md (human-readable)
  - results/eval/comparison.json (machine-readable)

Overall is the weighted composite defined in rubric.WEIGHTS.

Usage:
    uv run python -m nemoslides.eval.compare
"""

from __future__ import annotations

import json

from nemoslides._paths import RESULTS
from nemoslides.eval.rubric import DIMENSIONS, WEIGHTS

EVAL_DIR = RESULTS / "eval"

SHORT = {
    "content": "Content",
    "design": "Design",
    "coherence": "Coherence",
    "visual_craft": "VisCraft",
}


def _fmt(x: float | None) -> str:
    return f"{x:.2f}" if isinstance(x, (int, float)) else "—"


def _fmt_pct(x: float | None) -> str:
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else "—"


def _weighted_overall(d: dict[str, float | None]) -> float | None:
    total = 0.0
    wsum = 0.0
    for dim, w in WEIGHTS.items():
        v = d.get(dim)
        if isinstance(v, (int, float)):
            total += v * w
            wsum += w
    return total / wsum if wsum > 0 else None


def main() -> None:
    results_files = sorted(EVAL_DIR.glob("*_results.json"))
    if not results_files:
        raise SystemExit("no *_results.json files found in eval/")

    rows = []
    for f in results_files:
        d = json.loads(f.read_text())
        agg = d["aggregate"]
        rows.append({
            "model": d["model"],
            "slug": d.get("slug", ""),
            "n": agg["n"],
            "render_rate": agg["render_rate"],
            "mor": agg["mean_over_renderable"],
            "fl": agg["floor_scored_mean"],
        })

    rows.sort(key=lambda r: -(_weighted_overall(r["fl"]) or 0))

    weights_str = " + ".join(f"{w:.2f}·{SHORT[d]}" for d, w in WEIGHTS.items())

    lines: list[str] = []
    lines.append("# Eval comparison")
    lines.append("")
    lines.append(f"Test set: {rows[0]['n']} rows. Judge: `google/gemini-3-flash-preview` (vision).")
    lines.append("")
    lines.append(
        "**Rubric v5:** Content / Design / Coherence (judge) + Visual Craft "
        "(objective Slidev-feature scan). 1–5 each."
    )
    lines.append(f"**Weighted Overall:** `{weights_str}`")
    lines.append("**Render-fail accounting:** floor-scored = unrenderable rows count as 1 across all dims.")
    lines.append("")

    header = (
        "| Model | Render | "
        + " | ".join(SHORT[d] for d in DIMENSIONS)
        + " | **Overall** |"
    )
    sep = "|---|---|" + "|".join(["---"] * len(DIMENSIONS)) + "|---|"

    lines.append("## Headline (floor-scored, ranked by weighted Overall)")
    lines.append("")
    lines.append(header)
    lines.append(sep)
    for r in rows:
        vals = " | ".join(_fmt(r["fl"].get(d)) for d in DIMENSIONS)
        overall = _weighted_overall(r["fl"])
        lines.append(
            f"| `{r['model']}` | {_fmt_pct(r['render_rate'])} | {vals} | **{_fmt(overall)}** |"
        )
    lines.append("")

    rows_mor = sorted(rows, key=lambda r: -(_weighted_overall(r["mor"]) or 0))
    lines.append("## Mean over renderable only (ranked by weighted Overall)")
    lines.append("")
    lines.append(header)
    lines.append(sep)
    for r in rows_mor:
        vals = " | ".join(_fmt(r["mor"].get(d)) for d in DIMENSIONS)
        overall = _weighted_overall(r["mor"])
        lines.append(
            f"| `{r['model']}` | {_fmt_pct(r['render_rate'])} | {vals} | **{_fmt(overall)}** |"
        )
    lines.append("")

    lines.append("## Model slugs")
    lines.append("")
    for r in rows:
        lines.append(f"- `{r['model']}` → `{r['slug']}`")
    lines.append("")

    md_path = EVAL_DIR / "comparison_table.md"
    md_path.write_text("\n".join(lines))

    json_path = EVAL_DIR / "comparison.json"
    json_path.write_text(json.dumps({"rows": rows}, indent=2))

    print(f"wrote {md_path}")
    print(f"wrote {json_path}")
    print()
    print("\n".join(lines))


if __name__ == "__main__":
    main()
