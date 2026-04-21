# CLAUDE.md

Guidance for Claude Code sessions working in this repo.

## What this project is

**NemoSlides** — NVIDIA Nemotron Hackathon 2026, Track B. Two-day solo SFT of
`NVIDIA-Nemotron-3-Nano-30B-A3B` on 705 synthetic Slidev decks, producing an
open-weight 30B model that ranks **#1 on the 30-row PPTEval** — ahead of
`gpt-5.4`, `glm-5.1`, and `nemotron-super` (120B).

## Read these first

1. [`README.md`](README.md) — stack, quickstart, results plot
2. [`docs/`](docs/) — full mkdocs writeup (01-problem / 02-data-pipeline /
   03-training / 04-evaluation)
3. [`results/eval/comparison_table.md`](results/eval/comparison_table.md) —
   raw eval numbers
4. [`results/eval/plots/`](results/eval/plots/) — overall / per-dim / radar / Δ

## Conventions

- **No emojis.** Not in code, docs, commits, or responses — unless the user
  explicitly asks.
- **Terse docs.** No marketing language, no hedging, no filler. Write for a
  reviewer reading at 2am.
- **Minimal comments in code.** Only when WHY is non-obvious.
- **Python deps via `uv` only.** Hard rule. `uv sync`, `uv add <pkg>`,
  `uv run <script>`. Never `pip`, `conda`, `poetry`, or bare `python script.py`.
  Commit `pyproject.toml` + `uv.lock`.
- **No `PYTHONPATH=src`.** The project is `hatchling`-built with
  `packages = ["src/nemoslides"]`; `uv sync` installs it editable. Run
  modules via `uv run python -m nemoslides.<subpackage>.<mod>`.
- **NeMo-RL is the training path.** Hackathon eligibility requires a NeMo
  component; don't swap to TRL/Axolotl.
- **Baseline + finetuned use byte-identical eval protocol.** Same test
  split, same judge model, same rubric text. The Δ is the whole claim.

## Current status (as of 2026-04-22)

| Block | Status | Notes |
|---|---|---|
| Data synthesis | done | 705 train / 30 test rows on `trillionlabs/slides-sft-v0` |
| Quality filter | done | Codex pipeline validators + packer |
| Baseline SlidevBench (4 ref models) | done | rubric locked; numbers in `results/eval/` |
| SFT training | done | checkpoint served via vLLM as `nemotron-slide` |
| Finetuned SlidevBench | done | `nemoslides-30b-a3b` ranks #1 at 3.69 floor-scored Overall |
| Blindtest (human pairwise) | in progress | 90 pre-FT pairs voted; post-FT pending |
| Demo gallery | pending | — |
| Pitch polish | pending | — |

## Key numbers (SlidevBench, 30-row test, floor-scored weighted Overall)

| Model | Overall | Render |
|---|---|---|
| **`nemoslides-30b-a3b`** (ours) | **3.69** | 93% |
| `gpt-5.4` | 3.62 | 100% |
| `glm-5.1` | 3.26 | 100% |
| `nemotron-super` (120B) | 2.83 | 100% |
| `nemotron-nano` (base) | 2.50 | 87% |

SFT Δ vs base: **+48% Overall** (2.50 → 3.69), +1.56 Design, +1.70 Visual
Craft. The 30B SFT beats the 120B base on every individual dimension.

## Stack quick reference

| Layer | Choice |
|---|---|
| Base model | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` (post-trained; native `<think>`) |
| Training | NeMo-RL `run_sft.py`, LoRA + FSDP2. Recipe at `src/nemoslides/train/` |
| Teacher (synthesis) | NeMo Data Designer (categorical seed spine × GLM-5.1) → Codex authors `PROMPT.md` / `think.md` / `deck.md` per seed; validators in `src/nemoslides/cli/codex_pipeline.py` |
| Output format | Full Slidev capability surface (layouts, shiki, Mermaid, KaTeX, v-click, notes, transitions, theme variety) |
| Judge | `google/gemini-3-flash-preview` (vision) via OpenRouter |
| Renderer | `assets/renderer/render.sh` — Slidev + Playwright, file-locked parallel renders, vue/YAML error validator |
| Rubric | v5: Content / Design / Coherence (judge, 1-5) + Visual Craft (objective feature scan). Weighted Overall = `0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence` |
| Served inference | vLLM on `lunit-cloud-0:8000`; tunnel with `ssh -N -L 8000:localhost:8000 lunit-cloud-0` |

## Eval commands

```bash
# single model
uv run python -m nemoslides.eval.run --model nano-local --concurrency 15

# all references
for m in nemotron-nano nemotron-super glm-5.1 gpt-5.4; do
  uv run python -m nemoslides.eval.run --model $m
done

# aggregate + plot
uv run python -m nemoslides.eval.compare
uv run python -m nemoslides.eval.plot
```

Resumable: a row with a valid `results/eval/runs/<model>/<seed>/score.json`
is skipped. Delete that file to re-judge; delete the whole seed dir to
regenerate + re-render + re-judge.

## Things to NOT do

- Do not commit `data/**/*.jsonl`, `data/raw/`, rendered PNGs under
  `eval/runs/`, or checkpoints.
- Do not change the judge model or rubric between baseline and finetuned
  eval — protocol identity is what makes the Δ valid.
- Do not add RL / DPO stages. Pure SFT.
- Do not skip NeMo for a "simpler" training stack — kills hackathon
  eligibility.

## User profile

Scott Suk (juyoung.suk@trillionlabs.co). ML practitioner, comfortable at the
training-stack level. Blunt, terse, informal. Expects pushback over hand-
holding. Asks to be interviewed to high confidence before execution. See
also `~/.claude/projects/-Users-scottsuk-Projects-slides-sft/memory/` for
cross-session user and project memory.
