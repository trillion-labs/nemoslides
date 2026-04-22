"""Build the landing hub page at site/index.html.

Sibling pages under the site root:
    /          -> this hub (replaces the mkdocs landing page)
    /pitch/    -> slidev deck
    /gallery/  -> SlidevBench comparison gallery
    /docs/     -> mkdocs writeup (moved from /)

The hub is the "what is this and where do I go" entry point. Primary
tiles (pitch, gallery, docs) show a preview image; secondary row links
external artifacts (HF dataset, HF base model, GitHub source).

Usage:
    uv run python -m nemoslides.hub.build --out site
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from nemoslides._paths import REPO_ROOT, RESULTS

HEADLINE_NUMBERS = [
    ("#1", "SlidevBench rank", "ahead of gpt-5.4, glm-5.1, nemotron-super 120B"),
    ("3.69", "Weighted Overall", "floor-scored, 30-row held-out test set"),
    ("+48%", "Δ vs base nano", "2.50 → 3.69 after SFT"),
]


def _ours_best_seed() -> str:
    """Pick the seed where our model had the highest Overall — used for gallery preview."""
    p = RESULTS / "eval" / "nano-local_results.json"
    if not p.exists():
        return "seed_00022"
    data = json.loads(p.read_text())
    from nemoslides.gallery.build import DIM_WEIGHT, DIM_ORDER  # reuse

    def overall(row: dict) -> float:
        if not row.get("rendered"):
            return 0.0
        s = row.get("scores") or {}
        return sum(DIM_WEIGHT[d] * s.get(d, 1) for d in DIM_ORDER)

    best = max(data["per_row"], key=overall)
    return best["seed_id"]


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NemoSlides — SFT-tuned Nemotron for Slidev</title>
<meta name="description" content="NVIDIA Nemotron Hackathon 2026 · Track B. 2-day solo SFT of Nemotron-3-Nano-30B-A3B on 705 synthetic decks. #1 on 30-row SlidevBench.">
<meta property="og:title" content="NemoSlides — SFT-tuned Nemotron for Slidev">
<meta property="og:description" content="#1 on SlidevBench · 3.69 Overall · +48% Δ vs base nano">
<meta property="og:type" content="website">
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body {{ font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }}
  .stat-num {{ font-feature-settings: "tnum"; font-variant-numeric: tabular-nums; }}
  .tile-preview {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }}
  .tile:hover .tile-title {{ color: #0ea5e9; }}
</style>
</head>
<body class="bg-slate-50 text-slate-900">

<main class="max-w-[1200px] mx-auto px-6 py-12 md:py-16">

  <!-- hero -->
  <section class="mb-12">
    <div class="flex items-center gap-3 text-xs font-mono text-slate-500 mb-3">
      <span class="px-2 py-0.5 rounded bg-slate-900 text-white">NVIDIA Nemotron Hackathon 2026</span>
      <span>Track B</span>
    </div>
    <h1 class="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight mb-3">NemoSlides</h1>
    <p class="text-lg text-slate-700 max-w-3xl leading-relaxed">
      Two-day solo SFT of <code class="text-base bg-slate-200 px-1.5 py-0.5 rounded">NVIDIA-Nemotron-3-Nano-30B-A3B</code>
      on 705 synthetic Slidev decks. The resulting 30B-MoE (3B active) ranks <strong>#1</strong> on the 30-row
      SlidevBench held-out test — ahead of <code>gpt-5.4</code>, <code>glm-5.1</code>, and the 120B
      <code>nemotron-super</code>.
    </p>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
      {headline_stats}
    </div>
  </section>

  <!-- live demo CTA -->
  <section class="mb-10">
    <a href="https://nemoslides-production.up.railway.app/" target="_blank" rel="noopener"
       class="block rounded-xl overflow-hidden border border-slate-900 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white hover:shadow-xl transition group">
      <div class="px-6 py-5 md:px-8 md:py-6 flex flex-col md:flex-row md:items-center gap-4">
        <div class="flex items-center gap-3 md:flex-1">
          <span class="relative flex h-2.5 w-2.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400"></span>
          </span>
          <div>
            <div class="text-[10px] uppercase tracking-widest text-emerald-300 font-mono font-semibold">Live demo</div>
            <div class="text-xl md:text-2xl font-semibold">Try NemoSlides on your own prompt</div>
            <div class="text-sm text-slate-300 mt-0.5">Served over vLLM — type a prompt, watch the model write a Slidev deck, render it in-browser.</div>
          </div>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <code class="text-xs text-slate-400 font-mono hidden md:inline">nemoslides-production.up.railway.app</code>
          <span class="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-white text-slate-900 font-semibold text-sm group-hover:bg-emerald-300 transition">
            Open demo
            <span>↗</span>
          </span>
        </div>
      </div>
    </a>
  </section>

  <!-- primary tiles -->
  <section class="mb-10">
    <h2 class="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-4">Explore</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      {primary_tiles}
    </div>
  </section>

  <!-- secondary row -->
  <section class="mb-8">
    <h2 class="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-4">Artifacts</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      {secondary_tiles}
    </div>
  </section>

  <footer class="mt-16 pt-8 border-t border-slate-200 text-xs text-slate-500 flex flex-wrap gap-x-6 gap-y-2">
    <span>© 2026 · Hackathon submission</span>
    <span>Base model: NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 (Apache-2.0)</span>
    <span>Training framework: NVIDIA-NeMo/RL</span>
  </footer>

</main>

</body>
</html>
"""


def _stat_card(num: str, label: str, sub: str) -> str:
    return f"""
<div class="bg-white border border-slate-200 rounded-lg p-5">
  <div class="stat-num text-4xl font-bold text-slate-900 mb-1">{html.escape(num)}</div>
  <div class="text-sm font-semibold text-slate-800">{html.escape(label)}</div>
  <div class="text-xs text-slate-500 mt-0.5">{html.escape(sub)}</div>
</div>
"""


def _primary_tile(
    *,
    href: str,
    title: str,
    blurb: str,
    preview_html: str,
    badge: str | None = None,
) -> str:
    badge_html = (
        f'<span class="absolute top-3 right-3 text-[10px] font-mono px-2 py-0.5 rounded bg-white/90 text-slate-700">{html.escape(badge)}</span>'
        if badge
        else ""
    )
    return f"""
<a href="{href}" class="tile block group bg-white border border-slate-200 rounded-xl overflow-hidden hover:border-slate-400 hover:shadow-lg transition">
  <div class="relative aspect-[16/9] tile-preview overflow-hidden">
    {preview_html}
    {badge_html}
  </div>
  <div class="p-5">
    <div class="tile-title text-lg font-semibold text-slate-900 mb-1 transition">{html.escape(title)}</div>
    <p class="text-sm text-slate-600 leading-relaxed">{html.escape(blurb)}</p>
  </div>
</a>
"""


def _secondary_tile(*, href: str, title: str, sub: str, icon: str, external: bool = True) -> str:
    target = ' target="_blank" rel="noopener"' if external else ""
    arrow = "↗" if external else "→"
    return f"""
<a href="{href}"{target} class="flex items-center gap-4 bg-white border border-slate-200 rounded-lg px-4 py-3 hover:border-slate-400 hover:shadow-sm transition group">
  <div class="text-2xl">{icon}</div>
  <div class="flex-1 min-w-0">
    <div class="text-sm font-semibold text-slate-900 flex items-center gap-1">
      {html.escape(title)}
      <span class="text-slate-400 group-hover:text-slate-700 transition">{arrow}</span>
    </div>
    <div class="text-xs text-slate-500 truncate font-mono">{html.escape(sub)}</div>
  </div>
</a>
"""


def build_hub(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)

    # preview imagery (uses assets already present in the deployed site)
    best_seed = _ours_best_seed()

    pitch_preview = (
        '<div class="absolute inset-0 flex items-center justify-center p-6 text-center">'
        '<div>'
        '<div class="text-white/60 text-[10px] font-mono uppercase tracking-widest mb-2">Slidev · 13 slides</div>'
        '<div class="text-white text-2xl md:text-3xl font-semibold leading-tight">Pitch deck</div>'
        '<div class="text-slate-300 text-sm mt-2">Hackathon submission walkthrough</div>'
        '</div></div>'
    )

    gallery_preview = f"""
<div class="absolute inset-0 grid grid-cols-5 gap-1 p-2">
  <img src="gallery/thumbs/nano-local/{best_seed}/01.webp" class="w-full h-full object-cover rounded ring-2 ring-emerald-400" alt="ours">
  <img src="gallery/thumbs/gpt-5.4/{best_seed}/01.webp" class="w-full h-full object-cover rounded opacity-90" alt="gpt-5.4">
  <img src="gallery/thumbs/glm-5.1/{best_seed}/01.webp" class="w-full h-full object-cover rounded opacity-90" alt="glm-5.1">
  <img src="gallery/thumbs/nemotron-super/{best_seed}/01.webp" class="w-full h-full object-cover rounded opacity-90" alt="nemotron-super">
  <img src="gallery/thumbs/nemotron-nano/{best_seed}/01.webp" class="w-full h-full object-cover rounded opacity-90" alt="nemotron-nano">
</div>
<div class="absolute bottom-2 left-2 right-2 flex items-center justify-between text-[10px] font-mono">
  <span class="bg-emerald-500 text-white px-1.5 py-0.5 rounded">OURS</span>
  <span class="bg-white/90 text-slate-700 px-1.5 py-0.5 rounded">30 prompts × 5 models</span>
</div>
"""

    docs_preview = (
        '<img src="docs/assets/plots/overall_bar.png" class="absolute inset-0 w-full h-full object-contain bg-white p-4" alt="results chart">'
    )

    primary = [
        _primary_tile(
            href="pitch/",
            title="Pitch deck",
            blurb="The two-day story: problem, data synthesis, training, the SlidevBench win. Read end-to-end in 5 minutes.",
            preview_html=pitch_preview,
        ),
        _primary_tile(
            href="gallery/",
            title="SlidevBench gallery",
            blurb="Every test prompt rendered by all 5 models. Horizontal filmstrips and blindtest-style 2-up comparison.",
            preview_html=gallery_preview,
            badge="live results",
        ),
        _primary_tile(
            href="docs/",
            title="Technical docs",
            blurb="Full writeup: data pipeline, training recipe, rubric definition, per-dimension results, reproduction steps.",
            preview_html=docs_preview,
        ),
    ]

    secondary = [
        _secondary_tile(
            href="https://huggingface.co/datasets/trillionlabs/slides-sft-v0",
            title="Dataset",
            sub="trillionlabs/slides-sft-v0",
            icon="📊",
        ),
        _secondary_tile(
            href="https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16",
            title="Base model",
            sub="nvidia/Nemotron-3-Nano-30B-A3B",
            icon="🧠",
        ),
        _secondary_tile(
            href="https://github.com/trillion-labs/nemoslides",
            title="Source",
            sub="trillion-labs/nemoslides",
            icon="⌨",
        ),
    ]

    content = HTML_TEMPLATE.format(
        headline_stats="".join(_stat_card(*n) for n in HEADLINE_NUMBERS),
        primary_tiles="".join(primary),
        secondary_tiles="".join(secondary),
    )
    (out / "index.html").write_text(content)
    print(f"[done] wrote hub at {out / 'index.html'} ({len(content)/1024:.1f} KB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "site",
        help="output dir for site/index.html (default: site/)",
    )
    args = ap.parse_args()
    build_hub(args.out)


if __name__ == "__main__":
    main()
