"""Pack a Codex workspace into messages-only JSONL and push to HF Hub.

Projects every substantive, validated seed folder under ``--work`` into a
single-column ``messages`` row (system / user / assistant). First
``--test-size`` rows (by sorted seed name) form the test split; the rest
form train. Writes both JSONLs locally for audit; only uploads when
``--push`` is passed.

Usage:
    uv run python -m scripts.push_hf_dataset --work work_1615
    uv run python -m scripts.push_hf_dataset --work work_1615 --push
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.codex_pipeline import (
    MIN_DECK_BYTES,
    MIN_THINK_BYTES,
    clean_deck_markdown,
    is_substantive,
    validate_deck,
    validate_prompt,
    validate_think,
    _load_user_prompt,
)

SYSTEM_PROMPT = (
    "You are an expert presentation designer. Given the user's deck request, "
    "produce a complete, renderable Slidev markdown file."
)

DEFAULT_REPO = "trillionlabs/slides-sft-v0"


def build_rows(work_dir: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    folders = sorted(
        p for p in work_dir.iterdir()
        if p.is_dir() and p.name != "_shared" and (p / "seed.json").exists()
    )
    stats = {"total": len(folders), "included": 0, "stub": 0, "invalid": 0}
    rows: list[dict[str, Any]] = []

    for folder in folders:
        prompt = _load_user_prompt(folder)
        deck_ok = is_substantive(folder / "deck.md", MIN_DECK_BYTES)
        think_ok = is_substantive(folder / "think.md", MIN_THINK_BYTES)
        if not prompt or not deck_ok or not think_ok:
            stats["stub"] += 1
            continue

        reasoning = (folder / "think.md").read_text().strip()
        deck_md = clean_deck_markdown((folder / "deck.md").read_text())

        p_ok, _ = validate_prompt(prompt)
        t_ok, _ = validate_think(reasoning)
        d_ok, _ = validate_deck(deck_md)
        if not (p_ok and t_ok and d_ok):
            stats["invalid"] += 1
            continue

        rows.append({
            "seed_id": folder.name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT, "reasoning_content": None},
                {"role": "user", "content": prompt, "reasoning_content": None},
                {"role": "assistant", "content": deck_md, "reasoning_content": reasoning},
            ],
        })
        stats["included"] += 1

    return rows, stats


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, default=Path("work_1615"))
    ap.add_argument("--out-dir", type=Path, default=Path("data/hf"))
    ap.add_argument("--name", default="slides-sft-v0", help="basename for local JSONLs")
    ap.add_argument("--test-size", type=int, default=30, help="first N validated rows go to test")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--push", action="store_true", help="upload to HF Hub (private, train+test)")
    args = ap.parse_args()

    if not args.work.exists():
        raise SystemExit(f"work dir not found: {args.work}")

    rows, stats = build_rows(args.work)
    if len(rows) <= args.test_size:
        raise SystemExit(f"need >{args.test_size} rows for a split, got {len(rows)}")

    test_rows = rows[: args.test_size]
    train_rows = rows[args.test_size :]

    train_path = args.out_dir / f"{args.name}.train.jsonl"
    test_path = args.out_dir / f"{args.name}.test.jsonl"
    _write_jsonl(train_path, train_rows)
    _write_jsonl(test_path, test_rows)

    print(json.dumps(stats, indent=2))
    print(f"wrote {len(train_rows)} train rows -> {train_path}")
    print(f"wrote {len(test_rows)} test rows  -> {test_path}")

    if not args.push:
        return

    from datasets import Dataset, DatasetDict

    dd = DatasetDict({
        "train": Dataset.from_list(train_rows),
        "test": Dataset.from_list(test_rows),
    })
    dd.push_to_hub(args.repo, private=True)
    print(f"pushed train={len(train_rows)} test={len(test_rows)} -> hf://{args.repo} (private)")


if __name__ == "__main__":
    main()
