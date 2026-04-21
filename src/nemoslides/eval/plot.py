"""Plots for the 5-model v5 comparison.

Reads results/eval/*_results.json and emits three plots to results/eval/plots/:

  1. overall_bar.png      — weighted Overall per model, ranked (floor + mor)
  2. per_dim_bars.png     — grouped bars per rubric dimension
  3. radar.png            — 4-dim profile shape per model
  4. sft_delta.png        — before/after bars for base nano vs SFT

Run:
    PYTHONPATH=src uv run python -m nemoslides.eval.plot
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from nemoslides._paths import RESULTS
from nemoslides.eval.rubric import DIMENSIONS, WEIGHTS

EVAL_DIR = RESULTS / "eval"
PLOTS_DIR = EVAL_DIR / "plots"

# Consistent colors across plots. Highlight SFT model.
COLORS = {
    "nano-local":      "#d62728",   # red — the SFT model, stand out
    "gpt-5.4":         "#1f77b4",   # blue
    "glm-5.1":         "#2ca02c",   # green
    "nemotron-super":  "#9467bd",   # purple
    "nemotron-nano":   "#8c8c8c",   # gray — baseline
}
DISPLAY_NAME = {
    "nano-local":     "nano-local (SFT)",
    "gpt-5.4":        "gpt-5.4",
    "glm-5.1":        "glm-5.1",
    "nemotron-super": "nemotron-super (120B)",
    "nemotron-nano":  "nemotron-nano (base)",
}
DIM_LABEL = {
    "content":      "Content",
    "design":       "Design",
    "coherence":    "Coherence",
    "visual_craft": "Visual Craft",
}


def _load() -> list[dict]:
    rows = []
    for f in sorted(EVAL_DIR.glob("*_results.json")):
        d = json.loads(f.read_text())
        rows.append({
            "model": d["model"],
            "render_rate": d["aggregate"]["render_rate"],
            "fl": d["aggregate"]["floor_scored_mean"],
            "mor": d["aggregate"]["mean_over_renderable"],
            "n": d["aggregate"]["n"],
        })
    return rows


def _weighted(d: dict[str, float | None]) -> float:
    total, wsum = 0.0, 0.0
    for k, w in WEIGHTS.items():
        v = d.get(k)
        if isinstance(v, (int, float)):
            total += v * w
            wsum += w
    return total / wsum if wsum else 0.0


def plot_overall(rows: list[dict]) -> Path:
    rows_f = sorted(rows, key=lambda r: -_weighted(r["fl"]))
    rows_m = sorted(rows, key=lambda r: -_weighted(r["mor"]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, rs, title, key in [
        (ax1, rows_f, "Weighted Overall — floor-scored\n(render failures penalized as 1s)", "fl"),
        (ax2, rows_m, "Weighted Overall — mean over renderable only", "mor"),
    ]:
        names = [DISPLAY_NAME[r["model"]] for r in rs]
        scores = [_weighted(r[key]) for r in rs]
        cols = [COLORS[r["model"]] for r in rs]
        bars = ax.barh(names, scores, color=cols)
        ax.invert_yaxis()
        ax.set_xlabel("Weighted Overall (1-5)")
        ax.set_xlim(0, 5)
        ax.set_title(title, fontsize=11)
        ax.grid(axis="x", alpha=0.3)
        for bar, s in zip(bars, scores):
            ax.text(s + 0.05, bar.get_y() + bar.get_height() / 2, f"{s:.2f}",
                    va="center", fontsize=10)

    fig.suptitle("5-model PPTEval v5 — rubric v5, 30-row test set", fontsize=13, y=1.02)
    fig.tight_layout()
    out = PLOTS_DIR / "overall_bar.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_per_dim(rows: list[dict]) -> Path:
    """Grouped bars: X-axis dims, each group has one bar per model."""
    ordered = sorted(rows, key=lambda r: -_weighted(r["fl"]))
    dims = list(DIMENSIONS)
    n_models = len(ordered)
    width = 0.8 / n_models

    fig, ax = plt.subplots(figsize=(12, 5.5))
    x = np.arange(len(dims))
    for i, r in enumerate(ordered):
        vals = [r["fl"][d] for d in dims]
        ax.bar(x + i * width - (n_models - 1) * width / 2, vals, width,
               label=DISPLAY_NAME[r["model"]], color=COLORS[r["model"]])

    ax.set_xticks(x)
    ax.set_xticklabels([DIM_LABEL[d] for d in dims])
    ax.set_ylabel("Score (1-5, floor-scored)")
    ax.set_ylim(0, 5)
    ax.set_title("Per-dimension scores — floor-scored")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    fig.tight_layout()
    out = PLOTS_DIR / "per_dim_bars.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_radar(rows: list[dict], key: str = "fl", suffix: str = "floor") -> Path:
    dims = list(DIMENSIONS)
    labels = [DIM_LABEL[d] for d in dims]
    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(8.5, 8), subplot_kw={"projection": "polar"})
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)
    ax.set_rticks([1, 2, 3, 4, 5])
    ax.set_ylim(0, 5)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=11)
    ax.tick_params(axis="y", labelsize=8)

    ordered = sorted(rows, key=lambda r: -_weighted(r[key]))
    for r in ordered:
        vals = [r[key].get(d) or 0 for d in dims]
        vals_closed = vals + vals[:1]
        lw = 2.5 if r["model"] == "nano-local" else 1.2
        alpha_fill = 0.18 if r["model"] == "nano-local" else 0.05
        ax.plot(angles_closed, vals_closed, color=COLORS[r["model"]], linewidth=lw,
                label=DISPLAY_NAME[r["model"]])
        ax.fill(angles_closed, vals_closed, color=COLORS[r["model"]], alpha=alpha_fill)

    ax.legend(loc="lower right", bbox_to_anchor=(1.3, 0.0), fontsize=9)
    title = "Rubric profile — " + ("floor-scored" if suffix == "floor" else "renderable only")
    ax.set_title(title, fontsize=13, pad=20)
    fig.tight_layout()
    out = PLOTS_DIR / f"radar_{suffix}.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_sft_delta(rows: list[dict]) -> Path:
    """Before (base nano) vs after (SFT nano-local), per dim, with Δ arrows."""
    base = next(r for r in rows if r["model"] == "nemotron-nano")
    sft = next(r for r in rows if r["model"] == "nano-local")
    dims = list(DIMENSIONS)
    labels = [DIM_LABEL[d] for d in dims]
    base_vals = [base["fl"][d] for d in dims]
    sft_vals = [sft["fl"][d] for d in dims]

    x = np.arange(len(dims))
    width = 0.38
    fig, ax = plt.subplots(figsize=(11, 5.5))
    b1 = ax.bar(x - width / 2, base_vals, width, label="nemotron-nano (base)",
                color=COLORS["nemotron-nano"])
    b2 = ax.bar(x + width / 2, sft_vals, width, label="nano-local (SFT)",
                color=COLORS["nano-local"])
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Score (1-5, floor-scored)")
    ax.set_ylim(0, 5)
    ax.grid(axis="y", alpha=0.3)

    # Δ annotations
    for i, (bv, sv) in enumerate(zip(base_vals, sft_vals)):
        delta = sv - bv
        color = "#1a7f1a" if delta > 0 else "#b00020"
        ax.annotate(f"Δ +{delta:.2f}", xy=(i, max(bv, sv) + 0.2),
                    ha="center", fontsize=10, fontweight="bold", color=color)

    base_overall = _weighted(base["fl"])
    sft_overall = _weighted(sft["fl"])
    gain_pct = (sft_overall - base_overall) / base_overall * 100
    ax.set_title(
        f"SFT Δ — nano-local vs base nemotron-nano\n"
        f"Weighted Overall: {base_overall:.2f} → {sft_overall:.2f}  (+{gain_pct:.0f}%)",
        fontsize=12,
    )
    ax.legend(loc="upper left", fontsize=10)
    fig.tight_layout()
    out = PLOTS_DIR / "sft_delta.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = _load()
    if not rows:
        raise SystemExit(f"no results in {EVAL_DIR}")

    paths = [
        plot_overall(rows),
        plot_per_dim(rows),
        plot_radar(rows, key="fl", suffix="floor"),
        plot_radar(rows, key="mor", suffix="renderable"),
        plot_sft_delta(rows),
    ]
    for p in paths:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
