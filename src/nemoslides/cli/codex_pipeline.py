"""Canonical Codex-authored Slidev corpus pipeline.

Commands:
    uv run python -m nemoslides.cli.codex_pipeline init --seeds data/seeds.json --out work_1615
    uv run python -m nemoslides.cli.codex_pipeline status --work work_1615
    uv run python -m nemoslides.cli.codex_pipeline pack --work work_1615 --out data/raw/codex
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from nemoslides._paths import REFERENCE
from nemoslides.pipeline.slidev_reference import (
    ALLOWED_LAYOUTS,
    ALLOWED_THEMES,
    SLIDEV_CHEATSHEET,
    TASK_INSTRUCTIONS,
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "codex_templates"
HERO_EXAMPLE_PATH = REFERENCE / "gold_examples" / "hero_tech_talk.md"

TEACHER_MODEL = "codex-manual"

MIN_PROMPT_BYTES = 40
MIN_DECK_BYTES = 300
MIN_THINK_BYTES = 400

STUB_MARKER = "<!--\nCodex:"

_FENCE_START_RE = re.compile(r"^```(?:markdown|md)?\s*\n", re.IGNORECASE)
_FENCE_END_RE = re.compile(r"\n```\s*$")
_LEADING_DOUBLE_FM = re.compile(
    r"\A\s*---\n(.*?)\n---\s*\n\s*---\n(.*?)\n---\s*\n",
    re.DOTALL,
)
_BAD_MERMAID_COMPONENT = re.compile(
    r"<(?:Mermaid|mermaid)\b[^>]*chart=\{`([^`]+)`\}\s*/?>",
    re.DOTALL,
)
_THEME_RE = re.compile(r"^\s*theme:\s*(\S+)", re.MULTILINE)
_LAYOUT_RE = re.compile(r"^\s*layout:\s*(\S+)", re.MULTILINE)
_IMAGE_URL_RE = re.compile(r"^\s*image:\s*https?://", re.MULTILINE)
_COVER_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_NONCOVER_LAYOUT_START_RE = re.compile(r"\n---\nlayout:\s*(\S+)", re.MULTILINE)
_BLANK_LINE_AFTER_SEPARATOR_RE = re.compile(r"\n---\n(?:[ \t]*\n)+layout:\s*(\S+)", re.MULTILINE)
_PROMPT_BANNED_RE = re.compile(
    r"\b(think\.md|chain[- ]of[- ]thought|training data|sft|supervised fine[- ]tuning|internal pipeline)\b",
    re.IGNORECASE,
)


def _load_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text().rstrip() + "\n"


def build_instructions_md() -> str:
    layouts_whitelist_line = (
        "- Every `layout:` value is in this whitelist: "
        + ", ".join(f"`{layout}`" for layout in ALLOWED_LAYOUTS)
        + "\n"
    )
    parts = [
        _load_template("header.md"),
        _load_template("workflow_contract.md"),
        _load_template("quality_guidance.md"),
        SLIDEV_CHEATSHEET,
        _load_template("final_reminder.md") + layouts_whitelist_line,
    ]
    return "\n\n".join(part.rstrip() for part in parts) + "\n"


def build_training_system_prompt(include_cheatsheet: bool = True) -> str:
    parts = [TASK_INSTRUCTIONS]
    if include_cheatsheet:
        parts.append(SLIDEV_CHEATSHEET)
    return "\n\n".join(parts)


def is_substantive(path: Path, min_bytes: int) -> bool:
    if not path.exists():
        return False
    raw = path.read_text()
    if raw.strip().startswith(STUB_MARKER):
        return False
    return len(raw.encode()) >= min_bytes


def is_stub(path: Path) -> bool:
    if not path.exists():
        return True
    return path.read_text().strip().startswith(STUB_MARKER)


def _load_seed(folder: Path) -> dict[str, Any]:
    return json.loads((folder / "seed.json").read_text())


def _load_user_prompt(folder: Path) -> str | None:
    prompt_path = folder / "PROMPT.md"
    if not is_substantive(prompt_path, MIN_PROMPT_BYTES):
        return None
    return prompt_path.read_text().strip()


def _merge_leading_frontmatter(md: str) -> str:
    match = _LEADING_DOUBLE_FM.match(md)
    if not match:
        return md
    fm_global = match.group(1)
    fm_cover = match.group(2)
    tail = md[match.end() :]
    keys_seen: set[str] = set()
    merged_lines: list[str] = []
    for block in (fm_cover, fm_global):
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" not in stripped:
                merged_lines.append(line)
                continue
            key = stripped.split(":", 1)[0].strip()
            if key in keys_seen:
                continue
            keys_seen.add(key)
            merged_lines.append(line)
    return "---\n" + "\n".join(merged_lines) + "\n---\n" + tail


def _fix_bad_mermaid(md: str) -> str:
    def _sub(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        return f"```mermaid\n{body}\n```"

    return _BAD_MERMAID_COMPONENT.sub(_sub, md)


def clean_deck_markdown(raw: str) -> str:
    text = raw.strip()
    text = _FENCE_START_RE.sub("", text, count=1)
    text = _FENCE_END_RE.sub("", text, count=1)
    text = text.strip()
    text = _merge_leading_frontmatter(text)
    text = _fix_bad_mermaid(text)
    return text


def validate_deck(deck_md: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if not deck_md.startswith("---\n"):
        reasons.append("deck must start with a top frontmatter block")

    cover_match = _COVER_FRONTMATTER_RE.match(deck_md)
    if not cover_match:
        reasons.append("cover frontmatter malformed or missing closing delimiter")
    else:
        cover_fm = cover_match.group(1)
        if re.search(r"^\s*layout:\s*cover\b", cover_fm, re.MULTILINE) is None:
            reasons.append("first slide frontmatter must declare layout: cover")

    theme_match = _THEME_RE.search(deck_md)
    if not theme_match:
        reasons.append("no theme: declared")
    else:
        theme = theme_match.group(1).strip().strip('"\'')
        if theme not in ALLOWED_THEMES:
            reasons.append(f"theme '{theme}' not in whitelist")

    layouts = [m.group(1).strip().strip('"\'') for m in _LAYOUT_RE.finditer(deck_md)]
    if not layouts:
        reasons.append("no layout: declared on any slide")
    bad_layouts = [layout for layout in layouts if layout not in ALLOWED_LAYOUTS]
    if bad_layouts:
        reasons.append(f"unknown layouts: {sorted(set(bad_layouts))}")

    noncover_layouts = [
        m.group(1).strip().strip('"\'') for m in _NONCOVER_LAYOUT_START_RE.finditer(deck_md)
    ]
    if _BLANK_LINE_AFTER_SEPARATOR_RE.search(deck_md):
        reasons.append("blank line between slide separator and non-cover frontmatter")
    if layouts and len(layouts) != len(noncover_layouts) + 1:
        reasons.append("some non-cover slides do not start frontmatter with layout:")

    if _IMAGE_URL_RE.search(deck_md):
        reasons.append("literal image URL in frontmatter (must use image-query:)")

    n_slides = 1 + len(noncover_layouts)
    if n_slides < 4:
        reasons.append(f"deck too short ({n_slides} slides)")

    return (len(reasons) == 0, reasons)


def validate_prompt(prompt: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if len(prompt.encode()) < MIN_PROMPT_BYTES:
        reasons.append("prompt too short")
    if prompt.strip().startswith("```") or prompt.strip().endswith("```"):
        reasons.append("prompt wrapped in code fences")
    if _PROMPT_BANNED_RE.search(prompt):
        reasons.append("prompt leaks internal pipeline or reasoning terms")
    return (len(reasons) == 0, reasons)


def validate_think(reasoning: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    headings = [
        "## Reading the user prompt",
        "## Theme fit",
        "## Narrative arc",
        "## Key slide mapping",
        "## Image & feature choices",
        "## Self-review",
    ]
    for heading in headings:
        if heading not in reasoning:
            reasons.append(f"missing heading: {heading}")
    n_words = len(reasoning.split())
    if n_words < 250:
        reasons.append(f"think too short ({n_words} words)")
    if n_words > 1200:
        reasons.append(f"think too long ({n_words} words)")
    if "seed" in reasoning.lower() and "user prompt" not in reasoning.lower():
        reasons.append("think refers to seed without grounding on user prompt")
    banned_phrases = ("render feedback", "after rendering", "post-render", "I rendered")
    if any(phrase in reasoning.lower() for phrase in banned_phrases):
        reasons.append("think claims post-render inspection")
    return (len(reasons) == 0, reasons)


def init_workspace(seeds: list[dict[str, Any]], out_dir: Path, repo_root: Path | None = None) -> dict[str, int]:
    shared = out_dir / "_shared"
    shared.mkdir(parents=True, exist_ok=True)

    (shared / "INSTRUCTIONS.md").write_text(build_instructions_md())

    hero_src = HERO_EXAMPLE_PATH
    if not hero_src.exists():
        raise FileNotFoundError(f"missing hero example: {hero_src}")
    shutil.copy2(hero_src, shared / "HERO_EXAMPLE.md")

    prompt_stub = _load_template("prompt_stub.md")
    deck_stub = _load_template("deck_stub.md")
    think_stub = _load_template("think_stub.md")

    created = 0
    preserved = 0
    for seed in seeds:
        sid = seed.get("id")
        if not sid:
            raise ValueError(f"seed missing id: {seed}")
        sdir = out_dir / sid
        sdir.mkdir(parents=True, exist_ok=True)

        (sdir / "seed.json").write_text(json.dumps(seed, indent=2, ensure_ascii=False))

        for name in ("INSTRUCTIONS.md", "HERO_EXAMPLE.md"):
            link = sdir / name
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(Path("..") / "_shared" / name)

        for filename, stub in (
            ("PROMPT.md", prompt_stub),
            ("deck.md", deck_stub),
            ("think.md", think_stub),
        ):
            path = sdir / filename
            if is_stub(path) or path.stat().st_size == 0:
                path.write_text(stub)
            else:
                preserved += 1
        created += 1

    return {"created": created, "preserved_files": preserved}


def summarize_workspace(work_dir: Path) -> dict[str, Any]:
    folders = sorted(
        path
        for path in work_dir.iterdir()
        if path.is_dir() and path.name != "_shared" and (path / "seed.json").exists()
    )
    prompt_ready = 0
    deck_ready = 0
    think_ready = 0
    complete = 0
    pending: list[str] = []
    for folder in folders:
        prompt_ok = is_substantive(folder / "PROMPT.md", MIN_PROMPT_BYTES)
        deck_ok = is_substantive(folder / "deck.md", MIN_DECK_BYTES)
        think_ok = is_substantive(folder / "think.md", MIN_THINK_BYTES)
        prompt_ready += int(prompt_ok)
        deck_ready += int(deck_ok)
        think_ready += int(think_ok)
        if prompt_ok and deck_ok and think_ok:
            complete += 1
        else:
            pending.append(folder.name)

    total = len(folders)
    return {
        "workspace": str(work_dir),
        "seed_folders": total,
        "prompt_ready": prompt_ready,
        "deck_ready": deck_ready,
        "think_ready": think_ready,
        "complete": complete,
        "remaining": total - complete,
        "completion_rate": 0.0 if total == 0 else complete / total * 100.0,
        "pending": pending,
    }


def pack_workspace(work_dir: Path, out_dir: Path, overwrite: bool = False) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    folders = sorted(
        path
        for path in work_dir.iterdir()
        if path.is_dir() and path.name != "_shared" and (path / "seed.json").exists()
    )
    if not folders:
        raise FileNotFoundError(f"no seed folders under {work_dir}")

    stats = {
        "total": len(folders),
        "packed": 0,
        "invalid": 0,
        "skipped": 0,
        "already": 0,
    }

    for folder in folders:
        prompt = _load_user_prompt(folder)
        deck_ok = is_substantive(folder / "deck.md", MIN_DECK_BYTES)
        think_ok = is_substantive(folder / "think.md", MIN_THINK_BYTES)
        if not prompt or not deck_ok or not think_ok:
            stats["skipped"] += 1
            continue

        seed = _load_seed(folder)
        reasoning = (folder / "think.md").read_text().strip()
        deck_md = clean_deck_markdown((folder / "deck.md").read_text())

        prompt_valid, prompt_reasons = validate_prompt(prompt)
        think_valid, think_reasons = validate_think(reasoning)
        deck_valid, deck_reasons = validate_deck(deck_md)
        valid = prompt_valid and think_valid and deck_valid
        reasons = prompt_reasons + think_reasons + deck_reasons

        out_path = out_dir / f"{seed['id']}.json"
        if out_path.exists() and not overwrite:
            stats["already"] += 1
            continue

        system = build_training_system_prompt(include_cheatsheet=True)
        rec = {
            "seed_id": seed.get("id"),
            "seed": seed,
            "include_cheatsheet": True,
            "teacher_model": TEACHER_MODEL,
            "teacher_wall_s": None,
            "usage": None,
            "reasoning": reasoning,
            "deck_md": deck_md,
            "assistant_content_with_think": f"<think>\n{reasoning}\n</think>\n\n{deck_md}",
            "valid": valid,
            "validation_reasons": reasons,
            "chat_messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": deck_md, "reasoning": reasoning},
            ],
        }
        out_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
        if valid:
            stats["packed"] += 1
        else:
            stats["invalid"] += 1

    return stats


def _load_seeds(seed_path: Path, limit: int = 0, one_per_theme: bool = False) -> list[dict[str, Any]]:
    seeds = json.loads(seed_path.read_text())
    if one_per_theme:
        seen: dict[str, dict[str, Any]] = {}
        for seed in seeds:
            theme = seed.get("theme_hint") or "unknown"
            seen.setdefault(theme, seed)
        seeds = list(seen.values())
    if limit:
        seeds = seeds[:limit]
    return seeds


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--seeds", type=Path, required=True)
    p_init.add_argument("--out", type=Path, default=Path("work"))
    p_init.add_argument("--limit", type=int, default=0)
    p_init.add_argument("--one-per-theme", action="store_true")

    p_status = sub.add_parser("status")
    p_status.add_argument("--work", type=Path, default=Path("work"))

    p_pack = sub.add_parser("pack")
    p_pack.add_argument("--work", type=Path, default=Path("work"))
    p_pack.add_argument("--out", type=Path, default=Path("data/raw/codex"))
    p_pack.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()

    if args.command == "init":
        seeds = _load_seeds(args.seeds, limit=args.limit, one_per_theme=args.one_per_theme)
        stats = init_workspace(seeds, args.out)
        print(f"materialized {stats['created']} seed folders under {args.out}")
        print(f"preserved existing non-empty files: {stats['preserved_files']}")
        print(f"shared instructions: {args.out / '_shared' / 'INSTRUCTIONS.md'}")
        print(f"hero example:        {args.out / '_shared' / 'HERO_EXAMPLE.md'}")
        return

    if args.command == "status":
        stats = summarize_workspace(args.work)
        print(f"workspace:        {stats['workspace']}")
        print(f"seed folders:     {stats['seed_folders']}")
        print(f"prompt ready:     {stats['prompt_ready']}")
        print(f"deck ready:       {stats['deck_ready']}")
        print(f"think ready:      {stats['think_ready']}")
        print(f"complete:         {stats['complete']}")
        print(f"remaining:        {stats['remaining']}")
        print(f"completion rate:  {stats['completion_rate']:.1f}%")
        if stats["pending"]:
            print()
            print("next pending:")
            for name in stats["pending"][:20]:
                print(f"  {name}")
            if len(stats["pending"]) > 20:
                print(f"  ... and {len(stats['pending']) - 20} more")
        return

    if args.command == "pack":
        stats = pack_workspace(args.work, args.out, overwrite=args.overwrite)
        print(f"folders total:     {stats['total']}")
        print(f"packed (valid):    {stats['packed']}")
        print(f"packed (invalid):  {stats['invalid']}")
        print(f"skipped:           {stats['skipped']}")
        print(f"already written:   {stats['already']}")
        print(f"records written →  {args.out}")


if __name__ == "__main__":
    main()
