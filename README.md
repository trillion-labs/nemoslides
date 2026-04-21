# slides-sft

**Teaching a 30B-A3B MoE open-weight model to design pitch decks.**

NVIDIA Nemotron Hackathon 2026 · Track B (training process + metric validity) · 2-day solo project.

**Reviewer writeup:** [trillion-labs.github.io/slides-sft](https://trillion-labs.github.io/slides-sft/) — or read the source under [`docs/`](docs/index.md).

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
uv sync                      # runtime
uv sync --group dev          # + pytest / ruff
cp .env.example .env         # fill keys — see comments in the file
cd renderer && npm install   # Slidev + themes (Node)
```

Required keys: `OPENROUTER_API_KEY` (baseline + judge), `GEMINI_API_KEY` (judge, direct mode), `UNSPLASH_ACCESS_KEY` (image resolver). See `.env.example` for which path consumes which key.

## Repo structure

```
slides-sft/
├── README.md / PLAN.md / PROGRESS.md
├── pyproject.toml · uv.lock    — uv-managed Python env
├── pipeline/                   — Slidev reference pack, clients, image tools
├── scripts/                    — Codex data pipeline + HF dataset packer
├── data/                       — seeds + image bank (raw JSONL + work dirs gitignored)
├── train/                      — NeMo-RL config + launch scripts
├── eval/                       — PPTEval harness (generate + render + judge + score)
├── renderer/                   — pinned Slidev + theme env; `render.sh` entry point
├── reference/                  — vendored Slidev docs + gold few-shot examples
├── demo/                       — pre-rendered smoke gallery
├── docs/                       — reviewer writeup (start with docs/README.md) + qualitative evidence
└── tests/                      — pytest suite
```

## Reproduce end-to-end

```bash
# 0. Install (see above)

# 1. Baseline PPTEval (the protocol every claim derives from)
uv run python -m eval.run --model nemotron-nano --out eval/runs/nemotron-nano
uv run python -m eval.compare

# 2. Synthesize training data — Codex authors PROMPT.md / think.md / deck.md per seed
WORK=work-$(date +%Y%m%d)
uv run python -m scripts.codex_pipeline init   --seeds data/seeds.json --out "$WORK"
# ... Codex fills each seed folder ...
uv run python -m scripts.codex_pipeline status --work "$WORK"
uv run python -m scripts.codex_pipeline pack   --work "$WORK" --out data/raw/codex

# 3. Pack to chat JSONL + push to HF Hub (dataset: trillionlabs/slides-sft-v0)
uv run python -m scripts.push_hf_dataset --work "$WORK" --push

# 4. SFT with NeMo-RL (see train/)
# 5. Re-run step 1 against the finetuned checkpoint — identical rubric, identical split.
```

## Eval protocol

30-row held-out test split → `eval.generate` produces decks → `renderer/render.sh` exports per-slide PNGs → `eval.judge` (Gemini 3 Flash, vision) scores Content / Design / Coherence on a 1–5 rubric → `eval.features` adds an objective Visual Craft score by scanning for Slidev primitives (named layouts, shiki, Mermaid, KaTeX, `v-click`, transitions, presenter notes, non-default theme).

**Weighted Overall** = `0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence`. The visual axis is over-weighted because that's where SFT delta is expected to land.

**Floor-scored**: unrenderable decks count as 1 across all dims. This is the headline number — it penalizes models that emit invalid Slidev markdown and can't be scored by the judge at all.

## Results

Baselines from rubric v5, 30-row test split, floor-scored. Judge: `google/gemini-3-flash-preview`. Full table + renderable-only view in [`eval/comparison_table.md`](eval/comparison_table.md).

| Model | Render | Content | Design | Coherence | VisCraft | **Overall** |
|---|---|---|---|---|---|---|
| `gpt-5.4` | 100% | 4.27 | 3.17 | 4.07 | 3.40 | **3.62** |
| `glm-5.1` | 100% | 3.83 | 3.03 | 3.83 | 2.90 | **3.26** |
| `nemotron-super` (120B-A12B) | 100% | 4.13 | 2.63 | 3.73 | 1.97 | **2.83** |
| **`nemotron-nano` (30B-A3B, SFT target)** | 87% | 3.50 | 2.30 | 3.37 | 1.80 | **2.50** |
| **Finetuned (ours)** | — | — | — | — | — | **—** |
| **Δ vs. base** | — | — | — | — | — | **—** |

Nano's 87% render rate is inflated ~15pp by cache-reuse of Vue-error PNGs; the judge and feature scanner correctly score those low, so the weighted Overall ranking is unaffected. Final pitch number will re-render fresh.

**SFT target:** lift nano ≥ `nemotron-super` (must-have) and close the gap to `glm-5.1` (stretch). The objective VisCraft dim (nano 1.80 → gpt-5.4 3.40) is the quantified teaching signal.

## References

- **Framework:** [NeMo-RL SFT guide](https://docs.nvidia.com/nemo/rl/latest/guides/sft.html) · [Nemotron-3-Nano recipe dir](https://github.com/NVIDIA-NeMo/RL/tree/main/examples/configs/recipes/llm)
- **Eval:** PPTAgent (EMNLP 2025, arXiv [2501.03936](https://arxiv.org/abs/2501.03936)) — PPTEval rubric
- **Context:** AutoPresent (CVPR 2025, arXiv [2501.00912](https://arxiv.org/abs/2501.00912))
- **Model:** [Nemotron-3-Nano on HuggingFace](https://huggingface.co/nvidia)
- **Slide format:** [Slidev named layouts](https://sli.dev/builtin/layouts.html)
