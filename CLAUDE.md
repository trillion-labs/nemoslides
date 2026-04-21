# CLAUDE.md

Guidance for Claude Code sessions working in this repo.

## What this project is

`slides-sft` — NVIDIA Nemotron Hackathon 2026 · **Track B** · 2-day solo project. SFT `Nemotron-3-Nano-30B-A3B` on synthetic Slidev-markdown decks to beat the base model on PPTEval.

## Read these first, in order

1. [`README.md`](README.md) — project summary, stack, repo structure
2. [`PLAN.md`](PLAN.md) — 48-hour hour-by-hour execution plan + success criteria
3. [`docs/README.md`](docs/README.md) — reviewer writeup entry point. Locked design decisions live inline in each topical doc (`docs/02-data-pipeline.md`, `docs/03-training.md`, `docs/04-evaluation.md`).
4. [`PROGRESS.md`](PROGRESS.md) — live execution log. **Update this as work progresses.**

Do not re-litigate locked decisions in the `docs/` writeup unless the user explicitly reopens them.

## Conventions

- **No emojis.** Not in code, docs, commits, or responses — unless the user explicitly asks.
- **Terse docs.** No marketing language, no hedging, no filler. Write for a reviewer reading at 2am.
- **Minimal comments in code.** Only when WHY is non-obvious.
- **Python deps via `uv` only.** This is a hard rule. Use `uv sync`, `uv add <pkg>`, `uv run <script>`. **Never** `pip install ...`, `pip install -r requirements.txt`, `conda`, `poetry`, or a bare `python script.py`. Commit `pyproject.toml` + `uv.lock`. New dependency? → `uv add <name>`, no other path.
- **Never skip NeMo for a "simpler" training stack.** NeMo-RL is a hard requirement for hackathon eligibility.
- **The baseline run at hour 7–8 is non-negotiable.** Every number the project claims derives from the base-vs-finetuned delta on the identical 50-prompt held-out protocol.
- **Slidev is the output format — AND the training target is the full Slidev feature surface**, not just a template-constrained subset. Scott wants the finetuned model to unlock advanced Slidev capabilities (code blocks with shiki highlighting, Mermaid diagrams, KaTeX math, `v-click` progressive reveals, `v-motion` animations, all named layouts, theme variety, presenter notes, transitions). The synthetic dataset must cover this surface — use the official Slidev demos (sli.dev/demo, slidevjs/slidev repo samples, community themes) as few-shot / style references during data synthesis.

## Progress-tracking protocol

Two layers:

1. **In-session:** use `TaskCreate` / `TaskUpdate` to track tasks during an active work session. Mark `in_progress` on start, `completed` immediately on finish — don't batch.
2. **Across sessions:** update `PROGRESS.md` when a `PLAN.md` block completes, when a blocker appears, or when the plan deviates. `PROGRESS.md` is the durable log reviewers can read.

If a new session starts, read `PROGRESS.md` first to know what's been done.

## Stack quick reference

| Layer | Concrete choice |
|---|---|
| Base model (SFT target) | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` (post-trained; native `<think>` reasoning; `enable_thinking=True` default). Baseline eval via OpenRouter `nvidia/nemotron-3-nano-30b-a3b` (same post-trained model). |
| Training | NeMo-RL `examples/run_sft.py` with **chat JSONL**, LoRA + FSDP2, adapted from `examples/configs/recipes/llm/sft-nanov3-30BA3B-2n8g-fsdp2-lora.yaml`. Training examples preserve the native Nemotron chat template + `<think>` reasoning tags. |
| Training data format | Chat JSONL. Assistant content = `<think>{reasoning}</think>\n\n{Slidev markdown}`. No tool calls in training — images resolved by post-generation preprocessor. |
| Teacher (synthesis) | **GLM-5.1 via OpenRouter** (`z-ai/glm-5.1`). Exposes raw reasoning trace in a separate `reasoning` field — we wrap as `<think>{reasoning}</think>`. OpenAI hides reasoning, so it's not used as teacher. |
| Image strategy | Model emits `image-query: "<natural text>"` placeholders; pre-render preprocessor calls `unsplash_search` to resolve. Unsplash tool has API mode + curated-bank fallback at `pipeline/tools/unsplash.py`. |
| Slide format | Slidev markdown — **full capability surface** (all named layouts, code+shiki, Mermaid, KaTeX, v-click, transitions, presenter notes). Themes restricted to `default`, `seriph`, `apple-basic` (only professionally-designed ones; bricks/shibainu dropped as placeholder-looking). Slidev knowledge pack at `pipeline/slidev_reference.py` is injected into synthesis system prompts. |
| Judge (PPTEval) | **Gemini 3 Flash** via OpenRouter (`google/gemini-3-flash-preview`) or direct Google API. Vision-enabled, rubric = Content / Design / Coherence, 1–5 each. |
| Renderer | `./renderer/render.sh` — canonical env with all common themes pre-installed. Includes image-query preprocessor before Slidev export. |

## Things to NOT do

- Do not run `uv sync` in the NeMo-RL repo until hour 7 of the execution plan.
- Do not launch SFT before the baseline PPTEval run has completed and produced `eval/baseline_results.json`.
- Do not commit `data/*.jsonl`, `data/raw/`, rendered PNGs, or checkpoints to git.
- Do not change the judge model or rubric between baseline and finetuned eval — protocol identity is what makes the delta valid.
- Do not add RL / DPO / reward-modeling stages. Pure SFT only.
- Do not generate images or use multimodal pipelines. Slide images are URL placeholders or emoji.

## User profile

Scott Suk (juyoung.suk@trillionlabs.co). ML practitioner, comfortable at the training-stack level. Blunt, terse, informal. Expects pushback over hand-holding. Asks to be interviewed to high confidence before execution. See also `~/.claude/projects/-Users-scottsuk-Projects-slides-sft/memory/` for cross-session user and project memory.
