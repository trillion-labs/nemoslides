"""Generate the blindtest pair queue.

Scans `results/eval/runs/<model>/<seed_id>/slides/` for rendered decks, picks a
stratified sample of seeds, and emits all C(n_models, 2) model pairs × sampled
seeds as a shuffled queue. Re-runnable: if a queue already exists, new pairs
(e.g., from a newly-added model) are appended without touching existing
entries — so previously-cast votes stay valid.
"""

from __future__ import annotations

import argparse
import json
import random
from itertools import combinations

from nemoslides._paths import DATA, RESULTS

RUNS_ROOT = RESULTS / "eval" / "runs"
TEST_JSONL = DATA / "hf" / "slides-sft-v0.test.jsonl"
QUEUE_PATH = RESULTS / "blindtest" / "pair_queue.json"


def discover_models() -> list[str]:
    return sorted(p.name for p in RUNS_ROOT.iterdir() if p.is_dir())


def seeds_rendered(model: str) -> set[str]:
    model_dir = RUNS_ROOT / model
    out = set()
    for seed_dir in model_dir.iterdir():
        if not seed_dir.is_dir():
            continue
        slides = seed_dir / "slides"
        if slides.is_dir() and any(slides.glob("*.png")):
            out.add(seed_dir.name)
    return out


def load_prompts() -> dict[str, str]:
    prompts: dict[str, str] = {}
    with TEST_JSONL.open() as f:
        for line in f:
            row = json.loads(line)
            prompts[row["seed_id"]] = row["messages"][1]["content"]
    return prompts


def pair_id(seed_id: str, a: str, b: str) -> str:
    lo, hi = sorted([a, b])
    return f"{seed_id}__{lo}__vs__{hi}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-prompts", type=int, default=15,
                    help="How many seeds to sample per pair (default 15)")
    ap.add_argument("--seed", type=int, default=42,
                    help="RNG seed for sampling + shuffle")
    ap.add_argument("--force", action="store_true",
                    help="Rebuild from scratch (discard existing queue)")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    models = discover_models()
    if len(models) < 2:
        raise SystemExit(f"Need >=2 models in {RUNS_ROOT}, found {models}")

    # Seeds that every model has rendered — intersection keeps the matrix square.
    common_seeds = set.intersection(*(seeds_rendered(m) for m in models))
    if not common_seeds:
        raise SystemExit("No seeds are rendered across ALL models — check results/eval/runs/")

    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing queue (if any) to preserve pair_ids and only add new ones.
    existing: list[dict] = []
    existing_ids: set[str] = set()
    existing_seeds: set[str] = set()
    if QUEUE_PATH.exists() and not args.force:
        existing = json.loads(QUEUE_PATH.read_text())
        existing_ids = {p["pair_id"] for p in existing}
        existing_seeds = {p["seed_id"] for p in existing}

    # If there's an existing queue, reuse its seed set so new models slot in as
    # (new_model vs existing_model) pairs on the same seeds — keeps vote
    # attribution consistent. Only sample fresh when starting from scratch.
    if existing_seeds:
        stale = existing_seeds - common_seeds
        if stale:
            raise SystemExit(
                f"Existing queue references seeds no longer rendered across all models: "
                f"{sorted(stale)}. Add renders, or re-run with --force to resample."
            )
        sampled = sorted(existing_seeds)
    else:
        seed_pool = sorted(common_seeds)
        n = min(args.n_prompts, len(seed_pool))
        sampled = sorted(rng.sample(seed_pool, n))

    prompts = load_prompts()
    missing = [s for s in sampled if s not in prompts]
    if missing:
        raise SystemExit(f"Prompts missing from test JSONL: {missing}")

    new_entries: list[dict] = []
    for seed_id in sampled:
        for a, b in combinations(models, 2):
            pid = pair_id(seed_id, a, b)
            if pid in existing_ids:
                continue
            new_entries.append({
                "pair_id": pid,
                "seed_id": seed_id,
                "model_a": a,  # canonical (sorted) — actual L/R shown is randomized at render time
                "model_b": b,
                "prompt": prompts[seed_id],
            })

    rng.shuffle(new_entries)
    queue = existing + new_entries
    QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2))

    print(f"models: {models}")
    print(f"sampled seeds ({len(sampled)}): {sampled}")
    print(f"existing pairs: {len(existing)}")
    print(f"new pairs:      {len(new_entries)}")
    print(f"total queue:    {len(queue)} -> {QUEUE_PATH}")


if __name__ == "__main__":
    main()
