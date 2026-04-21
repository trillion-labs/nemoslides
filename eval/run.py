"""Per-model eval orchestrator.

For each row in the test JSONL:
  1. Generate with the chosen model (raw + <think>-stripped deck_md).
  2. Render via renderer/render.sh to PNGs.
  3. Judge via Gemini 3 Flash (user prompt + PNGs only).
  4. Persist gen.md / deck.md / slides/*.png / score.json under
     eval/runs/<model>/<seed_id>/.

Resumable: a row with a valid score.json is skipped. Render failures are
recorded with rendered=false and excluded from mean_over_renderable, floor-
scored as 1s across all dims in floor_scored_mean.

Usage:
    uv run python -m eval.run --model nemotron-nano
    uv run python -m eval.run --model nemotron-nano --limit 3
    uv run python -m eval.run --model gpt-5.4 --force
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eval.features import scan as scan_features
from eval.generate import MODELS, ModelSpec, generate
from eval.judge import judge_deck
from eval.rubric import DIMENSIONS, JUDGE_DIMENSIONS

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDER_SCRIPT = REPO_ROOT / "renderer" / "render.sh"
DEFAULT_TEST_JSONL = REPO_ROOT / "data/hf/slides-sft-v0.test.jsonl"
RUNS_ROOT = REPO_ROOT / "eval" / "runs"


@dataclass
class RowResult:
    seed_id: str
    rendered: bool
    error: str | None = None
    n_slides: int = 0
    scores: dict[str, int] = field(default_factory=dict)      # dim -> 1..5
    rationale: dict[str, str] = field(default_factory=dict)   # dim -> text


def _load_rows(path: Path, limit: int | None) -> list[dict[str, Any]]:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return rows[:limit] if limit else rows


# Signatures of compile errors that Slidev prints but does NOT exit non-zero on.
# When present, Playwright snapshots the Vue/Vite error overlay and we'd count
# it as "rendered" unless we validate the output text.
_RENDER_ERROR_SIGNATURES = (
    "[vite] Internal server error",
    "Plugin: vite:vue",
    "Element is missing end tag",
    "YAMLParseError",
    "ReferenceError: Unresolved alias",
)


MIN_RENDERED_SLIDES = 3  # below this is almost always a parse / frontmatter bug


def _render(deck_md: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(RENDER_SCRIPT), str(deck_md), str(out_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(
            f"render failed (exit {proc.returncode}):\n"
            f"stderr:\n{proc.stderr[-2000:]}"
        )
    for sig in _RENDER_ERROR_SIGNATURES:
        if sig in combined:
            tail = combined[-1500:]
            raise RuntimeError(f"render compile error ({sig!r}):\n{tail}")
    pngs = sorted(out_dir.glob("*.png"))
    if not pngs:
        raise RuntimeError("render produced no PNGs")
    if len(pngs) < MIN_RENDERED_SLIDES:
        raise RuntimeError(
            f"render produced only {len(pngs)} slide(s) — likely a frontmatter/parse bug"
        )
    return pngs


def _load_existing(score_path: Path) -> RowResult | None:
    if not score_path.exists():
        return None
    try:
        d = json.loads(score_path.read_text())
    except json.JSONDecodeError:
        return None
    # v2 schema: scores dict. Reject v1 rows on load so --force isn't needed.
    if "scores" not in d or not isinstance(d["scores"], dict):
        return None
    if d.get("rendered") and not all(dim in d["scores"] for dim in DIMENSIONS):
        return None
    return RowResult(
        seed_id=d["seed_id"],
        rendered=d["rendered"],
        error=d.get("error"),
        n_slides=d.get("n_slides", 0),
        scores=d.get("scores") or {},
        rationale=d.get("rationale") or {},
    )


def _persist(score_path: Path, r: RowResult) -> None:
    score_path.write_text(json.dumps(r.__dict__, ensure_ascii=False, indent=2))


async def eval_row_async(
    spec: ModelSpec,
    row: dict[str, Any],
    *,
    force: bool = False,
) -> RowResult:
    """Row-level async wrapper — dispatches blocking calls to threads."""
    seed_id = row["seed_id"]
    system = row["messages"][0]["content"]
    user = row["messages"][1]["content"]

    run_dir = RUNS_ROOT / spec.name / seed_id
    run_dir.mkdir(parents=True, exist_ok=True)
    gen_path = run_dir / "gen.md"
    deck_path = run_dir / "deck.md"
    slides_dir = run_dir / "slides"
    score_path = run_dir / "score.json"

    if not force:
        existing = _load_existing(score_path)
        if existing is not None:
            return existing

    # Reuse cached deck + slides if present (lets a rubric-only iteration
    # skip gen+render — delete score.json and re-run to rejudge).
    cached_slides = sorted(slides_dir.glob("*.png")) if slides_dir.exists() else []
    if deck_path.exists() and len(cached_slides) >= MIN_RENDERED_SLIDES:
        pngs = cached_slides
    else:
        # Generate
        try:
            out = await asyncio.to_thread(generate, spec, system=system, user=user)
        except Exception as e:
            r = RowResult(seed_id=seed_id, rendered=False, error=f"generate: {e!r}")
            _persist(score_path, r)
            return r

        gen_path.write_text(out["raw"])
        deck_path.write_text(out["deck_md"])
        if out.get("reasoning"):
            (run_dir / "reasoning.md").write_text(out["reasoning"])

        # Render
        try:
            pngs = await asyncio.to_thread(_render, deck_path, slides_dir)
        except Exception as e:
            err = f"render: {e!s}"[:500]
            r = RowResult(seed_id=seed_id, rendered=False, error=err)
            _persist(score_path, r)
            return r

    # Judge (subjective dims only)
    try:
        scores_raw = await asyncio.to_thread(judge_deck, user, pngs)
    except Exception as e:
        err = f"judge: {e!r}"[:500]
        r = RowResult(
            seed_id=seed_id,
            rendered=True,
            n_slides=len(pngs),
            error=err,
        )
        _persist(score_path, r)
        return r

    # Objective visual_craft via Slidev-feature scan of deck.md
    features = scan_features(deck_path.read_text())

    scores = {dim: scores_raw[dim]["score"] for dim in JUDGE_DIMENSIONS}
    scores["visual_craft"] = features.score
    rationale = {dim: scores_raw[dim]["rationale"] for dim in JUDGE_DIMENSIONS}
    rationale["visual_craft"] = (
        f"features: {features.total_points} pts "
        f"(layouts={features.distinct_non_default_layouts}, "
        f"shiki={int(features.has_shiki)}, mermaid={int(features.has_mermaid)}, "
        f"katex={int(features.has_katex)}, v-click={int(features.has_v_click)}, "
        f"notes={int(features.has_notes)}, transitions={int(features.has_transitions)}, "
        f"theme={int(features.non_default_theme)})"
    )

    r = RowResult(
        seed_id=seed_id,
        rendered=True,
        n_slides=len(pngs),
        scores=scores,
        rationale=rationale,
    )
    _persist(score_path, r)
    return r


def aggregate(results: list[RowResult]) -> dict[str, Any]:
    n = len(results)
    scored = [r for r in results if r.rendered and r.scores]
    render_rate = sum(1 for r in results if r.rendered) / n if n else 0.0

    def _mean(xs: list[int]) -> float | None:
        return round(sum(xs) / len(xs), 3) if xs else None

    mean_over_renderable = {
        dim: _mean([r.scores[dim] for r in scored if dim in r.scores])
        for dim in DIMENSIONS
    }

    # Floor-score unscored rows as 1 across all dims
    floor_scored_mean = {
        dim: round(
            sum(r.scores.get(dim, 1) for r in results) / n, 3
        ) if n else None
        for dim in DIMENSIONS
    }

    return {
        "n": n,
        "render_rate": round(render_rate, 3),
        "mean_over_renderable": mean_over_renderable,
        "floor_scored_mean": floor_scored_mean,
    }


_DIM_LABEL = {"content": "C", "design": "D", "coherence": "Co", "visual_craft": "V"}


async def run_model(
    spec: ModelSpec,
    rows: list[dict[str, Any]],
    *,
    concurrency: int,
    force: bool,
) -> list[RowResult]:
    sem = asyncio.Semaphore(concurrency)
    total = len(rows)
    done = 0
    lock = asyncio.Lock()

    async def _one(row: dict[str, Any]) -> RowResult:
        nonlocal done
        seed_id = row["seed_id"]
        async with sem:
            try:
                r = await eval_row_async(spec, row, force=force)
            except Exception:
                traceback.print_exc()
                r = RowResult(seed_id=seed_id, rendered=False, error="uncaught exception")
        async with lock:
            done += 1
            if r.rendered and r.scores:
                short = " ".join(f"{_DIM_LABEL[d]}={r.scores[d]}" for d in DIMENSIONS)
                print(f"[{spec.name}] ({done}/{total}) {seed_id} {short} ({r.n_slides} slides)", flush=True)
            else:
                print(f"[{spec.name}] ({done}/{total}) {seed_id} FAIL ({r.error or 'unknown'})", flush=True)
        return r

    return await asyncio.gather(*(_one(row) for row in rows))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(MODELS))
    ap.add_argument("--test", type=Path, default=DEFAULT_TEST_JSONL)
    ap.add_argument("--limit", type=int, default=None, help="cap rows for smoke testing")
    ap.add_argument("--force", action="store_true", help="ignore existing score.json")
    ap.add_argument("--concurrency", type=int, default=5, help="parallel rows per model")
    args = ap.parse_args()

    spec = MODELS[args.model]
    rows = _load_rows(args.test, args.limit)
    print(f"[{spec.name}] evaluating {len(rows)} rows (concurrency={args.concurrency}) -> {RUNS_ROOT / spec.name}")

    t0 = time.time()
    results = asyncio.run(
        run_model(spec, rows, concurrency=args.concurrency, force=args.force)
    )

    agg = aggregate(results)
    out = {
        "model": spec.name,
        "slug": spec.slug,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rubric_version": 5,
        "dimensions": list(DIMENSIONS),
        "aggregate": agg,
        "per_row": [r.__dict__ for r in results],
    }
    out_path = REPO_ROOT / "eval" / f"{spec.name}_results.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    elapsed = time.time() - t0
    print(f"\n[{spec.name}] done in {elapsed:.0f}s -> {out_path}")
    print(json.dumps(agg, indent=2))


if __name__ == "__main__":
    main()
