"""Aggregate per-model eval results into a single comparison table.

Reads eval/{model}_results.json for each model found, emits:
  - eval/comparison_table.md (human-readable)
  - eval/comparison.json (machine-readable)

Usage:
    uv run python -m eval.compare
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.rubric import DIMENSIONS

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "eval"

SHORT = {
    "content": "Content",
    "design": "Design",
    "coherence": "Coherence",
    "visual_craft": "VisCraft",
    "prompt_fidelity": "Fidelity",
}


def _fmt(x: float | None) -> str:
    return f"{x:.2f}" if isinstance(x, (int, float)) else "—"


def _fmt_pct(x: float | None) -> str:
    return f"{x * 100:.0f}%" if isinstance(x, (int, float)) else "—"


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

    # Rank by floor-scored overall (sum across dims), robust to None
    def rank_key(r):
        return -sum(v for v in r["fl"].values() if isinstance(v, (int, float)))
    rows.sort(key=rank_key)

    def _mean_all(d: dict[str, float | None]) -> float | None:
        vals = [v for v in d.values() if isinstance(v, (int, float))]
        return sum(vals) / len(vals) if vals else None

    lines: list[str] = []
    lines.append("# Eval comparison")
    lines.append("")
    lines.append(f"Test set: {rows[0]['n']} rows. Judge: `google/gemini-3-flash-preview` (vision).")
    lines.append("")
    lines.append("**Rubric v2:** Content / Design / Coherence / Visual Richness / Prompt Fidelity, 1–5 each.")
    lines.append("**Render-fail accounting:** floor-scored = unrenderable rows count as 1 across all dims.")
    lines.append("")

    header = (
        "| Model | Render | "
        + " | ".join(SHORT[d] for d in DIMENSIONS)
        + " | **Overall** |"
    )
    sep = "|---|---|" + "|".join(["---"] * len(DIMENSIONS)) + "|---|"

    lines.append("## Headline (floor-scored means, ranked by Overall)")
    lines.append("")
    lines.append(header)
    lines.append(sep)
    for r in rows:
        vals = " | ".join(_fmt(r["fl"][d]) for d in DIMENSIONS)
        overall = _mean_all(r["fl"])
        lines.append(
            f"| `{r['model']}` | {_fmt_pct(r['render_rate'])} | {vals} | **{_fmt(overall)}** |"
        )
    lines.append("")

    # Rerank by mean-over-renderable for second table
    rows_mor = sorted(rows, key=lambda r: -(_mean_all(r["mor"]) or 0))
    lines.append("## Mean over renderable only (ranked by Overall)")
    lines.append("")
    lines.append(header)
    lines.append(sep)
    for r in rows_mor:
        vals = " | ".join(_fmt(r["mor"][d]) for d in DIMENSIONS)
        overall = _mean_all(r["mor"])
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
