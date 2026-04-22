"""Build the static SlidevBench comparison gallery.

Two modes:

    # 1. Regenerate committed webp thumbnails from local PNG renders.
    #    Run once after a new eval sweep; commits thumbs under
    #    assets/gallery/thumbs/<model>/<seed>/NN.webp.
    uv run python -m nemoslides.gallery.build --regenerate-thumbs

    # 2. Build the static site from committed thumbs + committed
    #    results/eval/*_results.json + the test JSONL. Used in CI.
    uv run python -m nemoslides.gallery.build --out site/gallery

UI mirrors src/nemoslides/blindtest/templates/vote.html: sticky prompt
header, vertical slide stacks, click-to-lightbox. Index = one row per
seed with a horizontal filmstrip per model. Detail = 2-up picker, user
selects any pair of models (default: ours vs base nano).
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nemoslides._paths import ASSETS, DATA, REPO_ROOT, RESULTS

# (slug, display, is_ours) — order = gallery column order
MODELS: list[tuple[str, str, bool]] = [
    ("nano-local", "nemoslides-30b-a3b", True),
    ("gpt-5.4", "gpt-5.4", False),
    ("glm-5.1", "glm-5.1", False),
    ("nemotron-super", "nemotron-super (120B)", False),
    ("nemotron-nano", "nemotron-nano (base)", False),
]
DEFAULT_LEFT = "nano-local"
DEFAULT_RIGHT = "nemotron-nano"

DIM_ORDER = ("content", "design", "coherence", "visual_craft")
DIM_LABEL = {
    "content": "Content",
    "design": "Design",
    "coherence": "Coherence",
    "visual_craft": "Visual Craft",
}
# Weighted Overall: 0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence
DIM_WEIGHT = {"visual_craft": 0.40, "design": 0.25, "content": 0.20, "coherence": 0.15}

RUNS_DIR = RESULTS / "eval" / "runs"
EVAL_DIR = RESULTS / "eval"
THUMBS_DIR = ASSETS / "gallery" / "thumbs"
TEST_JSONL = DATA / "hf" / "slides-sft-v0.test.jsonl"
THUMB_WIDTH = 800  # webp width; height auto from 16:9 slides (~450px)


# ---------- thumbnail generation ----------


def regenerate_thumbs() -> None:
    from PIL import Image  # lazy: Pillow only needed for regeneration

    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    n_written = 0
    n_skipped = 0
    for slug, _, _ in MODELS:
        model_dir = RUNS_DIR / slug
        if not model_dir.exists():
            print(f"[warn] no runs for {slug} at {model_dir}")
            continue
        for seed_dir in sorted(model_dir.iterdir()):
            if not seed_dir.is_dir():
                continue
            slides = sorted((seed_dir / "slides").glob("*.png"))
            if not slides:
                continue
            out_seed = THUMBS_DIR / slug / seed_dir.name
            out_seed.mkdir(parents=True, exist_ok=True)
            for png in slides:
                out_path = out_seed / (png.stem + ".webp")
                if out_path.exists() and out_path.stat().st_mtime >= png.stat().st_mtime:
                    n_skipped += 1
                    continue
                with Image.open(png) as im:
                    im = im.convert("RGB")
                    ratio = THUMB_WIDTH / im.width
                    h = int(im.height * ratio)
                    im = im.resize((THUMB_WIDTH, h), Image.LANCZOS)
                    im.save(out_path, "WEBP", quality=82, method=6)
                n_written += 1
        print(f"[ok] {slug}: thumbs up to date")
    total = _dir_size(THUMBS_DIR)
    print(f"\n[done] wrote {n_written}, skipped {n_skipped}. total {THUMBS_DIR}: {total / 1e6:.1f} MB")


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


# ---------- data loading ----------


@dataclass
class Cell:
    model_slug: str
    model_display: str
    is_ours: bool
    rendered: bool
    error: str | None
    n_slides: int
    scores: dict[str, int]
    rationale: dict[str, str]
    overall: float  # floor-scored (unrendered = 1 across all dims)
    thumb_paths: list[str]  # relative to site root (gallery/)


@dataclass
class SeedRow:
    seed_id: str
    prompt: str
    cells: list[Cell]  # in MODELS order

    @property
    def ours_overall(self) -> float:
        for c in self.cells:
            if c.is_ours:
                return c.overall
        return 0.0

    def cell_for(self, slug: str) -> Cell | None:
        for c in self.cells:
            if c.model_slug == slug:
                return c
        return None


def _weighted_overall(scores: dict[str, int], rendered: bool) -> float:
    if not rendered:
        return sum(DIM_WEIGHT[d] * 1 for d in DIM_ORDER)
    return round(sum(DIM_WEIGHT[d] * scores.get(d, 1) for d in DIM_ORDER), 3)


def _load_prompts() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in TEST_JSONL.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        out[r["seed_id"]] = r["messages"][1]["content"]
    return out


def _load_results() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for slug, _, _ in MODELS:
        p = EVAL_DIR / f"{slug}_results.json"
        if not p.exists():
            print(f"[warn] missing {p}")
            out[slug] = {}
            continue
        data = json.loads(p.read_text())
        out[slug] = {r["seed_id"]: r for r in data["per_row"]}
    return out


def _thumbs_for(slug: str, seed_id: str, thumbs_root: Path) -> list[str]:
    seed_dir = thumbs_root / slug / seed_id
    if not seed_dir.exists():
        return []
    return [f"thumbs/{slug}/{seed_id}/{p.name}" for p in sorted(seed_dir.glob("*.webp"))]


def _build_rows(thumbs_root: Path) -> list[SeedRow]:
    prompts = _load_prompts()
    results = _load_results()
    all_seed_ids = sorted(prompts.keys())
    rows: list[SeedRow] = []
    for seed_id in all_seed_ids:
        cells: list[Cell] = []
        for slug, display, is_ours in MODELS:
            per_row = results.get(slug, {}).get(seed_id) or {}
            rendered = bool(per_row.get("rendered", False))
            scores = per_row.get("scores") or {}
            rationale = per_row.get("rationale") or {}
            overall = _weighted_overall(scores, rendered)
            cells.append(
                Cell(
                    model_slug=slug,
                    model_display=display,
                    is_ours=is_ours,
                    rendered=rendered,
                    error=per_row.get("error"),
                    n_slides=per_row.get("n_slides", 0),
                    scores=scores,
                    rationale=rationale,
                    overall=overall,
                    thumb_paths=_thumbs_for(slug, seed_id, thumbs_root),
                )
            )
        rows.append(SeedRow(seed_id=seed_id, prompt=prompts[seed_id], cells=cells))
    rows.sort(key=lambda r: r.ours_overall, reverse=True)
    return rows


# ---------- HTML rendering ----------
# Tailwind CDN for parity with src/nemoslides/blindtest/templates/vote.html.

HEAD_COMMON = """
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body { font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }
  .slide-img { cursor: zoom-in; }
  .lightbox {
    position: fixed; inset: 0; background: rgba(0,0,0,0.92);
    display: none; align-items: center; justify-content: center; z-index: 50;
    cursor: zoom-out; padding: 1.5rem;
  }
  .lightbox.active { display: flex; }
  .lightbox img { max-width: 100%; max-height: 100%; object-fit: contain; }
  .filmstrip { scrollbar-width: thin; scrollbar-color: #cbd5e1 transparent; }
  .filmstrip::-webkit-scrollbar { height: 6px; }
  .filmstrip::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
  details > summary { cursor: pointer; list-style: none; }
  details > summary::-webkit-details-marker { display: none; }
</style>
"""


def _overall_classes(v: float, rendered: bool) -> str:
    if not rendered:
        return "text-rose-700 bg-rose-50 border-rose-200"
    if v >= 3.5:
        return "text-emerald-700 bg-emerald-50 border-emerald-200"
    if v >= 2.5:
        return "text-amber-700 bg-amber-50 border-amber-200"
    return "text-rose-700 bg-rose-50 border-rose-200"


def _overall_badge(cell: Cell) -> str:
    cls = _overall_classes(cell.overall, cell.rendered)
    txt = f"{cell.overall:.2f}" if cell.rendered else "fail"
    return (
        f'<span class="inline-flex items-center px-2 py-0.5 rounded border font-mono text-xs '
        f'font-semibold {cls}">{txt}</span>'
    )


def _dim_pills(cell: Cell) -> str:
    if not (cell.rendered and cell.scores):
        return ""
    out = []
    for d in DIM_ORDER:
        s = cell.scores.get(d, "-")
        label = DIM_LABEL[d][0]
        out.append(
            f'<span class="inline-block px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 '
            f'font-mono text-[10px]">{label}{s}</span>'
        )
    return '<div class="flex gap-1 flex-wrap">' + "".join(out) + "</div>"


def _filmstrip(cell: Cell, seed_id: str) -> str:
    if not cell.rendered:
        err = html.escape((cell.error or "render failed")[:200])
        return (
            f'<div class="h-[92px] flex items-center justify-center bg-rose-50 border '
            f'border-rose-200 rounded text-rose-700 text-xs px-3 font-mono">{err}</div>'
        )
    if not cell.thumb_paths:
        return (
            '<div class="h-[92px] flex items-center justify-center bg-slate-100 border '
            'border-slate-200 rounded text-slate-500 text-xs font-mono">no thumbs</div>'
        )
    imgs = "".join(
        f'<a href="{seed_id}/" class="block shrink-0">'
        f'<img loading="lazy" src="{p}" alt="{cell.model_slug} slide {i+1}" '
        f'class="h-[92px] w-auto rounded border border-slate-200 bg-black hover:border-slate-400"></a>'
        for i, p in enumerate(cell.thumb_paths)
    )
    return f'<div class="filmstrip overflow-x-auto"><div class="flex gap-1 pb-1">{imgs}</div></div>'


def _cell_card_index(cell: Cell, seed_id: str) -> str:
    ours_ring = "ring-2 ring-slate-900" if cell.is_ours else "border border-slate-200"
    ours_tag = (
        '<span class="inline-block px-1.5 py-0.5 rounded bg-slate-900 text-white '
        'font-mono text-[10px] tracking-wide">OURS</span>' if cell.is_ours else ""
    )
    return f"""
<div class="bg-white rounded-lg p-3 space-y-2 {ours_ring}">
  <div class="flex items-center justify-between gap-2">
    <div class="flex items-center gap-2 min-w-0">
      <code class="text-xs font-semibold text-slate-900 truncate">{html.escape(cell.model_display)}</code>
      {ours_tag}
    </div>
    {_overall_badge(cell)}
  </div>
  {_filmstrip(cell, seed_id)}
  {_dim_pills(cell)}
</div>
"""


def _row_index(row: SeedRow) -> str:
    prompt = html.escape(row.prompt)
    cells = "".join(_cell_card_index(c, row.seed_id) for c in row.cells)
    return f"""
<article class="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3">
  <div class="flex items-baseline justify-between gap-4">
    <h2 class="text-base font-semibold text-slate-900">
      <a href="{row.seed_id}/" class="hover:underline">{html.escape(row.seed_id)}</a>
    </h2>
    <div class="text-xs font-mono text-slate-500">
      ours Overall <span class="font-semibold text-slate-900">{row.ours_overall:.2f}</span>
    </div>
  </div>
  <p class="text-sm text-slate-600 line-clamp-2">{prompt}</p>
  <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
    {cells}
  </div>
</article>
"""


def _index_html(rows: list[SeedRow]) -> str:
    rendered_rows = "\n".join(_row_index(r) for r in rows)
    return f"""<!doctype html>
<html lang="en">
<head>
<title>SlidevBench gallery — NemoSlides</title>
{HEAD_COMMON}
</head>
<body class="bg-white text-slate-900">

<header class="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200">
  <div class="max-w-[1800px] mx-auto px-6 py-3">
    <div class="flex items-center justify-between gap-4">
      <div class="text-xs font-mono text-slate-500">
        <a href="../" class="hover:underline">NemoSlides</a>
        <span class="text-slate-300 mx-1">/</span>
        <span class="text-slate-900">gallery</span>
      </div>
      <div class="text-xs font-mono text-slate-400">{len(rows)} seeds · {len(MODELS)} models</div>
    </div>
    <h1 class="text-xl font-semibold text-slate-900 mt-1">SlidevBench — side-by-side gallery</h1>
    <p class="text-sm text-slate-600">
      Every SlidevBench prompt rendered by all 5 models. Horizontal filmstrip shows every slide.
      Rows sorted by our model's floor-scored weighted Overall. Click a seed for 2-up comparison.
    </p>
  </div>
</header>

<main class="max-w-[1800px] mx-auto px-6 py-6 space-y-5">
  {rendered_rows}
</main>

</body>
</html>
"""


# ---------- detail (blindtest-style 2-up) ----------


def _cell_payload(cell: Cell) -> dict[str, Any]:
    return {
        "slug": cell.model_slug,
        "display": cell.model_display,
        "is_ours": cell.is_ours,
        "rendered": cell.rendered,
        "error": cell.error,
        "n_slides": cell.n_slides,
        "scores": cell.scores,
        "rationale": cell.rationale,
        "overall": cell.overall,
        "thumbs": [f"../{p}" for p in cell.thumb_paths],
    }


def _detail_html(row: SeedRow, prev_seed: str | None, next_seed: str | None) -> str:
    payload = {c.model_slug: _cell_payload(c) for c in row.cells}
    model_options = [
        {"slug": slug, "display": disp, "is_ours": is_ours}
        for slug, disp, is_ours in MODELS
    ]
    data_json = json.dumps(
        {
            "seed_id": row.seed_id,
            "ours_overall": row.ours_overall,
            "models": model_options,
            "default_left": DEFAULT_LEFT,
            "default_right": DEFAULT_RIGHT,
            "cells": payload,
            "dim_order": list(DIM_ORDER),
            "dim_label": DIM_LABEL,
        },
        ensure_ascii=False,
    )

    prev_link = (
        f'<a href="../{prev_seed}/" class="text-xs font-mono px-2 py-1 rounded border '
        f'border-slate-200 hover:bg-slate-100">← {prev_seed}</a>' if prev_seed else ""
    )
    next_link = (
        f'<a href="../{next_seed}/" class="text-xs font-mono px-2 py-1 rounded border '
        f'border-slate-200 hover:bg-slate-100">{next_seed} →</a>' if next_seed else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<title>{html.escape(row.seed_id)} — SlidevBench gallery</title>
{HEAD_COMMON}
</head>
<body class="bg-slate-50 text-slate-900">

<header class="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200">
  <div class="max-w-[1800px] mx-auto px-6 py-3 space-y-2">
    <div class="flex items-center gap-3 flex-wrap">
      <div class="text-xs font-mono text-slate-500">
        <a href="../../" class="hover:underline">NemoSlides</a>
        <span class="text-slate-300 mx-1">/</span>
        <a href="../" class="hover:underline">gallery</a>
        <span class="text-slate-300 mx-1">/</span>
        <span class="text-slate-900">{html.escape(row.seed_id)}</span>
      </div>
      <div class="flex-1"></div>
      {prev_link}
      {next_link}
    </div>
    <div class="text-xs uppercase tracking-wider text-slate-500 font-semibold">Prompt</div>
    <div class="text-sm text-slate-800 whitespace-pre-wrap bg-slate-50 p-3 rounded border border-slate-200 max-h-40 overflow-y-auto">{html.escape(row.prompt)}</div>
  </div>
</header>

<div class="max-w-[1800px] mx-auto px-6 pt-4">
  <div class="grid grid-cols-2 gap-6">
    <div class="space-y-2">
      <div class="flex items-center gap-2 flex-wrap">
        <label class="text-xs uppercase tracking-wider text-slate-500 font-semibold">Left</label>
        <select id="picker-left" class="text-sm font-mono border border-slate-300 rounded px-2 py-1 bg-white"></select>
        <span id="badge-left"></span>
        <span id="ours-tag-left"></span>
      </div>
      <div id="meta-left" class="text-xs text-slate-500 font-mono"></div>
    </div>
    <div class="space-y-2">
      <div class="flex items-center gap-2 flex-wrap">
        <label class="text-xs uppercase tracking-wider text-slate-500 font-semibold">Right</label>
        <select id="picker-right" class="text-sm font-mono border border-slate-300 rounded px-2 py-1 bg-white"></select>
        <span id="badge-right"></span>
        <span id="ours-tag-right"></span>
        <button id="swap-btn" class="ml-auto text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100 font-mono">swap ↔</button>
      </div>
      <div id="meta-right" class="text-xs text-slate-500 font-mono"></div>
    </div>
  </div>
</div>

<main class="max-w-[1800px] mx-auto px-6 py-4 pb-24">
  <div class="grid grid-cols-2 gap-6">
    <section>
      <div id="slides-left" class="space-y-3"></div>
      <div id="rationale-left" class="mt-5 space-y-1 text-sm"></div>
    </section>
    <section>
      <div id="slides-right" class="space-y-3"></div>
      <div id="rationale-right" class="mt-5 space-y-1 text-sm"></div>
    </section>
  </div>
</main>

<div class="lightbox" id="lightbox"><img id="lightbox-img" src=""></div>

<script id="gallery-data" type="application/json">{data_json}</script>
<script>
(() => {{
  const data = JSON.parse(document.getElementById('gallery-data').textContent);

  function fillPicker(el) {{
    for (const m of data.models) {{
      const o = document.createElement('option');
      o.value = m.slug;
      o.textContent = m.display + (m.is_ours ? ' (ours)' : '');
      el.appendChild(o);
    }}
  }}
  const L = document.getElementById('picker-left');
  const R = document.getElementById('picker-right');
  fillPicker(L);
  fillPicker(R);
  L.value = data.default_left;
  R.value = data.default_right;

  function overallClasses(v, rendered) {{
    if (!rendered) return 'text-rose-700 bg-rose-50 border-rose-200';
    if (v >= 3.5) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    if (v >= 2.5) return 'text-amber-700 bg-amber-50 border-amber-200';
    return 'text-rose-700 bg-rose-50 border-rose-200';
  }}

  function renderSide(side) {{
    const slug = (side === 'left' ? L.value : R.value);
    const c = data.cells[slug];
    const slidesEl = document.getElementById('slides-' + side);
    const badgeEl = document.getElementById('badge-' + side);
    const oursEl = document.getElementById('ours-tag-' + side);
    const metaEl = document.getElementById('meta-' + side);
    const ratEl = document.getElementById('rationale-' + side);

    badgeEl.className = 'inline-flex items-center px-2 py-0.5 rounded border font-mono text-xs font-semibold ' + overallClasses(c.overall, c.rendered);
    badgeEl.textContent = c.rendered ? c.overall.toFixed(2) : 'fail';

    oursEl.innerHTML = c.is_ours
      ? '<span class="inline-block px-1.5 py-0.5 rounded bg-slate-900 text-white font-mono text-[10px]">OURS</span>'
      : '';

    metaEl.textContent = c.rendered
      ? (c.n_slides + ' slides rendered')
      : ('render failed — ' + (c.error || 'unknown'));

    slidesEl.innerHTML = '';
    if (!c.rendered || !c.thumbs.length) {{
      const div = document.createElement('div');
      div.className = 'p-4 bg-rose-50 border border-rose-200 rounded text-rose-700 font-mono text-sm';
      div.textContent = c.error || 'no slides';
      slidesEl.appendChild(div);
    }} else {{
      c.thumbs.forEach((url, i) => {{
        const img = document.createElement('img');
        img.src = url;
        img.loading = 'lazy';
        img.dataset.src = url;
        img.dataset.side = side;
        img.dataset.idx = i;
        img.className = 'slide-img w-full rounded border border-slate-200 shadow-sm';
        img.alt = slug + ' slide ' + (i+1);
        slidesEl.appendChild(img);
      }});
    }}

    ratEl.innerHTML = '';
    if (c.rendered && c.scores) {{
      for (const d of data.dim_order) {{
        const det = document.createElement('details');
        det.className = 'bg-white rounded border border-slate-200 px-3 py-2';
        const sum = document.createElement('summary');
        sum.className = 'text-xs font-mono text-slate-700 flex justify-between items-center';
        sum.innerHTML = '<span>' + data.dim_label[d] + '</span>' +
          '<span class="font-semibold text-slate-900">' + (c.scores[d] ?? '-') + ' / 5</span>';
        det.appendChild(sum);
        const body = document.createElement('div');
        body.className = 'mt-2 text-xs text-slate-600 leading-relaxed';
        body.textContent = c.rationale[d] || '';
        det.appendChild(body);
        ratEl.appendChild(det);
      }}
    }}
  }}

  // lightbox
  const lb = document.getElementById('lightbox');
  const lbImg = document.getElementById('lightbox-img');
  let lbSide = null, lbIdx = 0;

  function openLightbox(img) {{
    lbSide = img.dataset.side;
    lbIdx = parseInt(img.dataset.idx, 10);
    lbImg.src = img.dataset.src;
    lb.classList.add('active');
  }}
  function closeLightbox() {{ lb.classList.remove('active'); }}
  function stepLightbox(delta) {{
    if (!lb.classList.contains('active')) return;
    const imgs = document.querySelectorAll('#slides-' + lbSide + ' .slide-img');
    if (!imgs.length) return;
    lbIdx = (lbIdx + delta + imgs.length) % imgs.length;
    lbImg.src = imgs[lbIdx].dataset.src;
  }}
  document.addEventListener('click', (e) => {{
    if (e.target.matches('.slide-img')) openLightbox(e.target);
  }});
  lb.addEventListener('click', closeLightbox);
  document.addEventListener('keydown', (e) => {{
    if (e.target.tagName === 'SELECT') return;
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowRight') stepLightbox(1);
    else if (e.key === 'ArrowLeft') stepLightbox(-1);
    else if (e.key === 's' || e.key === 'S') swap();
  }});

  function swap() {{
    const a = L.value, b = R.value;
    L.value = b; R.value = a;
    renderSide('left'); renderSide('right');
  }}
  document.getElementById('swap-btn').addEventListener('click', swap);
  L.addEventListener('change', () => renderSide('left'));
  R.addEventListener('change', () => renderSide('right'));

  renderSide('left');
  renderSide('right');
}})();
</script>
</body>
</html>
"""


# ---------- site build ----------


def build_site(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)

    out_thumbs = out / "thumbs"
    if out_thumbs.exists():
        shutil.rmtree(out_thumbs)
    if THUMBS_DIR.exists():
        shutil.copytree(THUMBS_DIR, out_thumbs)
    else:
        print(f"[warn] no thumbs at {THUMBS_DIR} — gallery will be imageless")

    rows = _build_rows(out_thumbs)

    (out / "index.html").write_text(_index_html(rows))
    for i, row in enumerate(rows):
        prev_seed = rows[i - 1].seed_id if i > 0 else None
        next_seed = rows[i + 1].seed_id if i < len(rows) - 1 else None
        d = out / row.seed_id
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(_detail_html(row, prev_seed, next_seed))

    print(f"[done] built gallery at {out} — {len(rows)} seeds, {len(MODELS)} models")
    if out_thumbs.exists():
        print(f"       thumbs: {_dir_size(out_thumbs) / 1e6:.1f} MB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--regenerate-thumbs",
        action="store_true",
        help="read PNGs from results/eval/runs/ and write webp to assets/gallery/thumbs/",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "site" / "gallery",
        help="output dir for the static site (default: site/gallery)",
    )
    args = ap.parse_args()

    if args.regenerate_thumbs:
        regenerate_thumbs()
        return

    build_site(args.out)


if __name__ == "__main__":
    main()
