<p align="center">
  <img src="docs/assets/logo.svg" alt="NemoSlides" width="360" />
</p>

<h3 align="center">Open-weight slide generation, fine-tuned on Nemotron.</h3>

<p align="center">
  <a href="https://build.nvidia.com"><img alt="NVIDIA Nemotron" src="https://img.shields.io/badge/NVIDIA-Nemotron--3--Nano--30B--A3B-76B900?logo=nvidia&logoColor=white"></a>
  <a href="https://github.com/NVIDIA-NeMo/RL"><img alt="NeMo-RL" src="https://img.shields.io/badge/Built%20with-NeMo--RL-76B900"></a>
  <a href="https://sli.dev"><img alt="Slidev" src="https://img.shields.io/badge/format-Slidev-06b6d4"></a>
  <a href="https://huggingface.co/datasets/trillionlabs/slides-sft-v0"><img alt="HF dataset" src="https://img.shields.io/badge/%F0%9F%A4%97%20dataset-slides--sft--v0-FFD21F"></a>
  <a href="https://ai.google.dev/gemini-api/docs"><img alt="Gemini judge" src="https://img.shields.io/badge/judge-Gemini%203%20Flash-4285F4"></a>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white"></a>
  <a href="https://docs.astral.sh/uv/"><img alt="uv" src="https://img.shields.io/badge/managed%20by-uv-261230"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-green"></a>
</p>

<p align="center">
  <a href="https://trillion-labs.github.io/nemoslides/">Docs</a> ·
  <a href="#quickstart">Quickstart</a> ·
  <a href="#results">Results</a> ·
  <a href="#reproduce">Reproduce</a>
</p>

---

**NemoSlides** fine-tunes `NVIDIA-Nemotron-3-Nano-30B-A3B` (30B params, 3B active MoE) on a 705-sample corpus of Slidev decks, producing an open-weight model that generates designer-grade presentations from a single prompt — locally, offline, and permissively licensed.

> _Gamma, but open-weights, runs on your laptop, and we're shipping the dataset too._

## Results

30-row held-out test split. Judge: `google/gemini-3-flash-preview` (vision). Rubric v5: Content / Design / Coherence (subjective) + Visual Craft (objective Slidev-feature scan). 1–5 each. **Weighted Overall** = `0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence`. Floor-scored: unrenderable decks count as 1 across all dims.

| Model | Render | Content | Design | Coherence | VisCraft | **Overall** |
|---|---|---|---|---|---|---|
| `gpt-5.4` (closed reference) | 100% | 4.27 | 3.17 | 4.07 | 3.40 | **3.62** |
| `glm-5.1` (open reference) | 100% | 3.83 | 3.03 | 3.83 | 2.90 | **3.26** |
| `nemotron-super` (120B-A12B) | 100% | 4.13 | 2.63 | 3.73 | 1.97 | **2.83** |
| **`nemotron-nano` (30B-A3B, SFT target)** | 87% | 3.50 | 2.30 | 3.37 | 1.80 | **2.50** |
| **NemoSlides (ours, finetuned)** | — | — | — | — | — | **—** |

## Quickstart

```bash
uv sync                       # installs nemoslides + deps
cp .env.example .env          # fill: OPENROUTER_API_KEY, UNSPLASH_ACCESS_KEY
cd assets/renderer && npm i && cd ../..
uv run uvicorn nemoslides.demo.app:app --reload    # prompt-to-deck web UI
```

## How it works

1. **Synthesis.** `nemoslides.cli.codex_pipeline` emits per-seed prompts; Codex authors `PROMPT.md` / `think.md` / `deck.md` per sample — 705 train + 30 test rows.
2. **Render-validate.** Every sample is compiled with Slidev + Playwright. Parse errors, Vue overlays, and <3-slide renders are dropped.
3. **Pack.** `nemoslides.cli.push_hf_dataset` projects seeds into chat-JSONL (`messages[0..2]` with `reasoning_content` on the assistant turn) and pushes to HF Hub.
4. **SFT.** NeMo-RL `run_sft.py` with LoRA + FSDP2 on the Nemotron-3-Nano base. Recipe at `src/nemoslides/train/recipes/`.
5. **PPTEval.** `nemoslides.eval.run` generates → renders → judges each held-out prompt. Identical protocol for base and finetuned — the delta is the only thing that matters.

## Repo

```
nemoslides/
├── src/nemoslides/        pipeline · cli · eval · demo · blindtest · train
├── assets/                renderer/ (pinned Slidev) · reference/ (Slidev docs + gold examples)
├── data/                  seeds · theme profiles · image bank
├── results/               eval JSONs · qualitative renders · blindtest DB
├── docs/                  reviewer writeup (mkdocs)
└── tests/
```

## Reproduce

```bash
# 1. Baseline PPTEval — the protocol every claim derives from.
uv run python -m nemoslides.eval.run --model nemotron-nano
uv run python -m nemoslides.eval.compare

# 2. Synthesize corpus — Codex writes PROMPT / think / deck per seed.
WORK=work-$(date +%Y%m%d)
uv run python -m nemoslides.cli.codex_pipeline init --seeds data/seeds.json --out "$WORK"
./scripts/run_codex_batch.sh "$WORK"
uv run python -m nemoslides.cli.push_hf_dataset --work "$WORK" --push

# 3. SFT (requires 2n8g).
./src/nemoslides/train/launch.sh

# 4. Re-run step 1 against the finetuned checkpoint — same rubric, same split.
```

See [docs](docs/index.md) for the full writeup: problem framing, data pipeline, training config, evaluation protocol.

## References

- **Base model:** [Nemotron-3-Nano-30B-A3B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16)
- **Framework:** [NeMo-RL](https://github.com/NVIDIA-NeMo/RL)
- **Rubric:** [PPTAgent (EMNLP 2025)](https://arxiv.org/abs/2501.03936) · [AutoPresent (CVPR 2025)](https://arxiv.org/abs/2501.00912)
- **Format:** [Slidev](https://sli.dev)

## License

Code: Apache-2.0. Model weights: governed by the [NVIDIA Open Model License](https://developer.download.nvidia.com/licenses/nvidia-open-model-license-agreement). Dataset: research use only.

---

<p align="center">Built for the <b>NVIDIA Nemotron Hackathon 2026 · Track B</b> by <a href="https://trillionlabs.co">Trillion Labs</a>.</p>
