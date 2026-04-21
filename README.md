# slides-sft

**Teaching a 30B-A3B MoE open-weight model to design pitch decks.**

NVIDIA Nemotron Hackathon 2026 · Track B (training process + metric validity) · 2-day solo project.

## What this is

We fine-tune **Nemotron-3-Nano-30B-A3B** (MoE, 3B active) on a Codex-authored corpus of Slidev training samples. Each sample has:

- `PROMPT.md` — a realistic user request
- `think.md` — a one-pass reasoning trace
- `deck.md` — the final Slidev deck

The assistant target is:

```text
<think>{think.md}</think>

{deck.md}
```

The packed dataset is published (private) at [`trillionlabs/slides-sft-v0`](https://huggingface.co/datasets/trillionlabs/slides-sft-v0) — 584 train / 30 test rows, chat-format JSONL with `reasoning_content` on the assistant turn.

## Pitch

> Gamma, but open weights, runs on your laptop, and we're shipping the dataset too.

- **Productivity:** every knowledge worker builds decks — unlimited, free, local generation.
- **OSS parity:** closes the gap between open-weight models and closed slide-gen tools (Gamma, Beautiful.ai, Canva Magic Design).
- **NVIDIA ecosystem:** finetuned checkpoint is a deployable NeMo microservice candidate.

## Stack

| Layer | Choice |
|---|---|
| Base model | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` (post-trained; native `<think>` reasoning) |
| Training | [NeMo-RL](https://github.com/NVIDIA-NeMo/RL) `examples/run_sft.py` + LoRA + FSDP2 (adapted from `sft-nanov3-30BA3B-2n8g-fsdp2-lora.yaml`) |
| Corpus author | [Codex CLI](https://developers.openai.com/codex/cli) — per-seed workspace with PROMPT / think / deck files |
| Slide format | [Slidev](https://sli.dev) markdown — full capability surface (layouts, shiki, Mermaid, KaTeX, `v-click`, transitions) |
| Image strategy | Model emits `image-query:` placeholders; pre-render preprocessor resolves via Unsplash + curated `data/image_bank.json` fallback |
| Judge | **Gemini 3 Flash** via OpenRouter (`google/gemini-3-flash-preview`) — PPTEval rubric: Content / Design / Coherence, 1–5 each |
| Rendering | `renderer/render.sh` — pinned Slidev env with common themes pre-installed |

## Install

Python deps via [`uv`](https://docs.astral.sh/uv/) only — `pip` / `conda` / `poetry` are not used in this repo.

```bash
uv sync
cp .env.example .env   # fill in OPENAI_API_KEY, OPENROUTER_API_KEY, UNSPLASH_ACCESS_KEY, GEMINI_API_KEY
```

Renderer (Node, for Slidev export):

```bash
cd renderer && npm install
```

## Repo structure

```
slides-sft/
├── README.md          — this file
├── PLAN.md            — 48-hour execution plan
├── DECISIONS.md       — locked design decisions + rationale
├── PROGRESS.md        — live execution log
├── pipeline/          — shared Slidev reference + image tools + helpers
├── scripts/           — Codex pipeline + HF dataset packer
├── data/              — seeds, image bank (packed JSONL + work dirs gitignored)
├── train/             — NeMo-RL config + launch scripts
├── eval/              — PPTEval harness (generate + render + judge + score)
├── renderer/          — Slidev rendering env (node_modules gitignored)
├── reference/         — Slidev docs + gold few-shot examples
├── demo/              — pre-rendered smoke gallery
└── docs/              — hour-1 qualitative evidence
```

## Pipeline

```bash
# 1. Materialize a Codex workspace from locked seeds
uv run python -m scripts.codex_pipeline init --seeds data/seeds.json --out work_1615

# 2. Track completion while Codex fills PROMPT.md / think.md / deck.md
uv run python -m scripts.codex_pipeline status --work work_1615

# 3. Pack completed folders into training records (local JSONL)
uv run python -m scripts.codex_pipeline pack --work work_1615 --out data/raw/codex

# 4. Pack into messages-only JSONL + push to HF Hub
uv run python -m scripts.push_hf_dataset --work work_1615 --push
```

`PROMPT.md` is authored by Codex, not generated from the seed by the pipeline.

## Eval

Identical protocol across base and finetuned checkpoints:

```bash
uv run python -m eval.run --model <name> --out eval/runs/<name>
```

Generates 50 held-out decks → renders via `renderer/render.sh` → judges with Gemini 3 Flash on the PPTEval rubric → writes scored JSONL. Baseline must run first and is the single point of comparison.

## Results

*Populated at hour 26 after finetuned checkpoint is available.*

| Metric | Base | Finetuned | Δ |
|---|---|---|---|
| PPTEval Content (1–5) | — | — | — |
| PPTEval Design (1–5) | — | — | — |
| PPTEval Coherence (1–5) | — | — | — |
| Pairwise win rate vs base | — | — | — |

## References

- **Framework:** [NeMo-RL SFT guide](https://docs.nvidia.com/nemo/rl/latest/guides/sft.html) · [Nemotron-3-Nano recipe dir](https://github.com/NVIDIA-NeMo/RL/tree/main/examples/configs/recipes/llm)
- **Eval:** PPTAgent (EMNLP 2025, arXiv [2501.03936](https://arxiv.org/abs/2501.03936)) — PPTEval rubric
- **Context:** AutoPresent (CVPR 2025, arXiv [2501.00912](https://arxiv.org/abs/2501.00912))
- **Model:** [Nemotron-3-Nano on HuggingFace](https://huggingface.co/nvidia)
- **Slide format:** [Slidev named layouts](https://sli.dev/builtin/layouts.html)
