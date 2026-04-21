"""Plots for the 5-model v5 comparison.

Reads results/eval/*_results.json and emits five plots to
results/eval/plots/ with an editorial, NVIDIA-green-forward style:

  1. overall_bar.png      — weighted Overall per model, ranked (floor + mor)
  2. per_dim_bars.png     — grouped bars per rubric dimension
  3. radar_floor.png      — 4-dim profile shape per model (floor-scored)
  4. radar_renderable.png — same, renderable-only
  5. sft_delta.png        — dumbbell: base → SFT per dim, with Δ labels

Run:
    PYTHONPATH=src uv run python -m nemoslides.eval.plot
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

from nemoslides._paths import RESULTS
from nemoslides.eval.rubric import DIMENSIONS, WEIGHTS

EVAL_DIR = RESULTS / "eval"
PLOTS_DIR = EVAL_DIR / "plots"


NVIDIA_GREEN = "#76B900"
NVIDIA_GREEN_SOFT = "#A7D82C"

# One hero color (NVIDIA green for the SFT), everything else in cool neutrals.
# Reads as a hierarchy, not a rainbow.
COLORS = {
    "nano-local":     NVIDIA_GREEN,
    "gpt-5.4":        "#0F172A",   # slate-900 — the strongest rival
    "glm-5.1":        "#475569",   # slate-600
    "nemotron-super": "#94A3B8",   # slate-400
    "nemotron-nano":  "#CBD5E1",   # slate-300 — the baseline, subdued
}
DISPLAY_NAME = {
    "nano-local":     "nemoslides-30b-a3b",
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

TEXT_STRONG = "#0F172A"
TEXT_MUTED  = "#64748B"
GRID        = "#E5E7EB"
SPINE       = "#CBD5E1"


def _apply_style() -> None:
    mpl.rcParams.update({
        # DejaVu Sans first for full unicode (arrows, Δ). Inter/Helvetica
        # Neue lack U+2192 so we'd get tofu boxes in the SFT-delta subtitle.
        "font.family": "sans-serif",
        "font.sans-serif": ["Inter", "DejaVu Sans", "Helvetica Neue", "Helvetica", "Arial"],
        "font.size": 11,
        "text.color": TEXT_STRONG,

        "axes.edgecolor": SPINE,
        "axes.linewidth": 0.8,
        "axes.labelcolor": TEXT_MUTED,
        "axes.labelsize": 10.5,
        "axes.labelweight": "regular",
        "axes.titlesize": 15,
        "axes.titleweight": "semibold",
        "axes.titlecolor": TEXT_STRONG,
        "axes.titlepad": 14,
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,

        "xtick.color": TEXT_MUTED,
        "ytick.color": TEXT_MUTED,
        "xtick.labelsize": 10.5,
        "ytick.labelsize": 11,

        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "grid.linestyle": "-",
        "grid.alpha": 1.0,

        "legend.frameon": False,
        "legend.fontsize": 10,
        "legend.labelcolor": TEXT_STRONG,

        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 160,
        "figure.dpi": 140,
    })


def _suptitle(fig, title: str, subtitle: str | None = None) -> None:
    fig.text(0.015, 0.985, title, fontsize=17, fontweight="semibold",
             color=TEXT_STRONG, ha="left", va="top")
    if subtitle:
        fig.text(0.015, 0.945, subtitle, fontsize=10.5, color=TEXT_MUTED,
                 ha="left", va="top")


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


def _is_hero(model: str) -> bool:
    return model == "nano-local"


def plot_overall(rows: list[dict]) -> Path:
    rows_f = sorted(rows, key=lambda r: -_weighted(r["fl"]))
    rows_m = sorted(rows, key=lambda r: -_weighted(r["mor"]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.6))
    fig.subplots_adjust(top=0.80, bottom=0.12, left=0.06, right=0.98, wspace=0.35)

    for ax, rs, title, key in [
        (ax1, rows_f, "Floor-scored",       "fl"),
        (ax2, rows_m, "Renderable only",    "mor"),
    ]:
        names = [DISPLAY_NAME[r["model"]] for r in rs]
        scores = [_weighted(r[key]) for r in rs]
        cols = [COLORS[r["model"]] for r in rs]
        y = np.arange(len(rs))

        ax.barh(y, scores, color=cols, height=0.62, edgecolor="none", zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(names)
        for tick_lbl, r in zip(ax.get_yticklabels(), rs):
            if _is_hero(r["model"]):
                tick_lbl.set_fontweight("semibold")
                tick_lbl.set_color(TEXT_STRONG)
        ax.invert_yaxis()

        ax.set_xlim(0, 5)
        ax.set_xticks([0, 1, 2, 3, 4, 5])
        ax.set_xlabel("Weighted Overall (1–5)")
        ax.set_title(title, loc="left", pad=10, fontsize=13)
        ax.xaxis.grid(True)
        ax.yaxis.grid(False)
        ax.set_axisbelow(True)
        for spine in ("left",):
            ax.spines[spine].set_visible(False)
        ax.tick_params(axis="y", which="both", length=0)

        for yi, (s, r) in enumerate(zip(scores, rs)):
            hero = _is_hero(r["model"])
            ax.text(s + 0.08, yi, f"{s:.2f}",
                    va="center", ha="left",
                    fontsize=11.5 if hero else 10.5,
                    fontweight="semibold" if hero else "regular",
                    color=TEXT_STRONG if hero else TEXT_MUTED)

    _suptitle(fig, "SlidevBench — Weighted Overall",
              "30-row held-out split · 5 models · judge: Gemini 3 Flash")

    out = PLOTS_DIR / "overall_bar.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return out


def plot_per_dim(rows: list[dict]) -> Path:
    ordered = sorted(rows, key=lambda r: -_weighted(r["fl"]))
    dims = list(DIMENSIONS)
    n_models = len(ordered)
    width = 0.78 / n_models

    fig, ax = plt.subplots(figsize=(12.5, 5.6))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.07, right=0.98)

    x = np.arange(len(dims))
    for i, r in enumerate(ordered):
        vals = [r["fl"][d] for d in dims]
        xs = x + i * width - (n_models - 1) * width / 2
        ax.bar(xs, vals, width, label=DISPLAY_NAME[r["model"]],
               color=COLORS[r["model"]], edgecolor="none", zorder=3)
        if _is_hero(r["model"]):
            for xi, v in zip(xs, vals):
                ax.text(xi, v + 0.08, f"{v:.2f}",
                        ha="center", va="bottom", fontsize=10,
                        fontweight="semibold", color=TEXT_STRONG)

    ax.set_xticks(x)
    ax.set_xticklabels([DIM_LABEL[d] for d in dims], fontsize=11.5, color=TEXT_STRONG)
    ax.set_ylim(0, 5)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_ylabel("Score (1–5, floor-scored)")
    ax.yaxis.grid(True)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)
    ax.spines["bottom"].set_color(SPINE)
    ax.tick_params(axis="x", which="both", length=0)

    leg = ax.legend(loc="upper left", bbox_to_anchor=(0, 1.02), ncol=n_models,
                    handlelength=1.2, handleheight=0.8, columnspacing=1.4)
    for handle, text, r in zip(leg.legend_handles, leg.get_texts(), ordered):
        if _is_hero(r["model"]):
            text.set_fontweight("semibold")

    _suptitle(fig, "SlidevBench — per-dimension scores",
              "floor-scored · nemoslides-30b-a3b labeled · bars grouped by rubric dimension")

    out = PLOTS_DIR / "per_dim_bars.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return out


def plot_radar(rows: list[dict], key: str = "fl", suffix: str = "floor") -> Path:
    dims = list(DIMENSIONS)
    labels = [DIM_LABEL[d] for d in dims]
    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    angles_closed = angles + angles[:1]

    fig = plt.figure(figsize=(10.5, 8.8))
    fig.subplots_adjust(top=0.84, bottom=0.08, left=0.08, right=0.76)
    ax = fig.add_subplot(projection="polar")

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(90)
    ax.set_ylim(0, 5.4)

    # Custom grid: subtle concentric polygons at 1..5.
    for r_val in range(1, 6):
        poly = [r_val] * (len(dims) + 1)
        ax.plot(angles_closed, poly, color=GRID, linewidth=0.7, zorder=1)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=12.5, color=TEXT_STRONG)
    ax.set_rticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=9, color=TEXT_MUTED)
    ax.tick_params(axis="x", pad=18)

    ax.spines["polar"].set_color(SPINE)
    ax.spines["polar"].set_linewidth(0.8)
    ax.grid(False)  # we drew our own

    ordered = sorted(rows, key=lambda r: -_weighted(r[key]))
    # Non-hero first (so hero paints on top)
    for r in [x for x in ordered if not _is_hero(x["model"])]:
        vals = [r[key].get(d) or 0 for d in dims]
        vals_closed = vals + vals[:1]
        ax.plot(angles_closed, vals_closed, color=COLORS[r["model"]],
                linewidth=1.3, alpha=0.85, zorder=2, label=DISPLAY_NAME[r["model"]])
    for r in [x for x in ordered if _is_hero(x["model"])]:
        vals = [r[key].get(d) or 0 for d in dims]
        vals_closed = vals + vals[:1]
        ax.plot(angles_closed, vals_closed, color=COLORS[r["model"]],
                linewidth=3.0, zorder=4, label=DISPLAY_NAME[r["model"]])
        ax.fill(angles_closed, vals_closed, color=COLORS[r["model"]],
                alpha=0.18, zorder=3)
        # Value labels at each hero vertex.
        for ang, v in zip(angles, vals):
            ax.text(ang, v + 0.22, f"{v:.2f}", ha="center", va="center",
                    fontsize=10, fontweight="semibold", color=COLORS[r["model"]])

    leg = ax.legend(loc="center left", bbox_to_anchor=(1.18, 0.5),
                    handlelength=1.4, handleheight=1.0, labelspacing=0.9,
                    fontsize=10.5)
    legend_order = [DISPLAY_NAME[r["model"]] for r in ordered]
    for text in leg.get_texts():
        if "SFT" in text.get_text():
            text.set_fontweight("semibold")
            text.set_color(TEXT_STRONG)
        else:
            text.set_color(TEXT_MUTED)
    _ = legend_order  # silence lint; order already comes from `ordered`

    sub = "floor-scored" if suffix == "floor" else "renderable only"
    _suptitle(fig, "SlidevBench — rubric profile",
              f"4-dimension shape per model · {sub}")

    out = PLOTS_DIR / f"radar_{suffix}.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return out


def plot_sft_delta(rows: list[dict]) -> Path:
    """Dumbbell: base to SFT per dim. Lift per dim annotated beside each row."""
    base = next(r for r in rows if r["model"] == "nemotron-nano")
    sft = next(r for r in rows if r["model"] == "nano-local")
    dims = list(DIMENSIONS)
    labels = [DIM_LABEL[d] for d in dims]
    base_vals = [base["fl"][d] for d in dims]
    sft_vals = [sft["fl"][d] for d in dims]

    fig, ax = plt.subplots(figsize=(12.5, 5.8))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.13, right=0.93)

    y = np.arange(len(dims))
    for yi, (bv, sv) in enumerate(zip(base_vals, sft_vals)):
        ax.plot([bv, sv], [yi, yi], color="#CBD5E1", linewidth=3.2,
                solid_capstyle="round", zorder=2)
        ax.scatter([bv], [yi], s=140, color=COLORS["nemotron-nano"],
                   edgecolor="#94A3B8", linewidth=0.8, zorder=3)
        ax.scatter([sv], [yi], s=190, color=NVIDIA_GREEN, edgecolor="white",
                   linewidth=1.5, zorder=4)
        delta = sv - bv
        ax.text(max(sv, bv) + 0.22, yi, f"+{delta:.2f}",
                va="center", ha="left", fontsize=11,
                fontweight="semibold", color=NVIDIA_GREEN)
        # base value on the left of the base dot; SFT value on the right of the SFT dot.
        ax.text(bv - 0.18, yi, f"{bv:.2f}",
                ha="right", va="center", fontsize=10, color=TEXT_MUTED)
        ax.text(sv + 0.04, yi - 0.26, f"{sv:.2f}",
                ha="center", va="top", fontsize=10,
                fontweight="semibold", color=NVIDIA_GREEN)

    # Inline anchor labels on the first row (no floating legend).
    anchor_y = -0.05
    ax.annotate("base", xy=(base_vals[0], 0), xytext=(base_vals[0], anchor_y - 0.6),
                ha="center", va="bottom", fontsize=10, color=TEXT_MUTED,
                arrowprops=dict(arrowstyle="-", color="#94A3B8", lw=0.6,
                                shrinkA=6, shrinkB=2))
    ax.annotate("SFT", xy=(sft_vals[0], 0), xytext=(sft_vals[0], anchor_y - 0.6),
                ha="center", va="bottom", fontsize=10.5, fontweight="semibold",
                color=NVIDIA_GREEN,
                arrowprops=dict(arrowstyle="-", color=NVIDIA_GREEN, lw=0.6,
                                shrinkA=8, shrinkB=2))

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12, color=TEXT_STRONG)
    ax.invert_yaxis()
    ax.set_ylim(len(dims) - 0.4, anchor_y - 0.8)
    ax.set_xlim(0, 5.3)
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("Score (1–5, floor-scored)")
    ax.xaxis.grid(True)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", which="both", length=0)

    base_overall = _weighted(base["fl"])
    sft_overall = _weighted(sft["fl"])
    gain_pct = (sft_overall - base_overall) / base_overall * 100

    _suptitle(
        fig,
        "SlidevBench — SFT lift",
        f"nemotron-nano base → nemoslides-30b-a3b   ·   "
        f"Weighted Overall  {base_overall:.2f}  →  {sft_overall:.2f}  "
        f"(+{gain_pct:.0f}%)",
    )

    out = PLOTS_DIR / "sft_delta.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return out


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    _apply_style()
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
