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

**NemoSlides** fine-tunes `NVIDIA-Nemotron-3-Nano-30B-A3B` (3B active, MoE) on 705 Slidev decks. Prompt in, presentation out — runs locally.

> _Gamma, but open-weights, runs on your laptop, and we're shipping the dataset too._

## Results

**SlidevBench** — 30-row held-out split. Judge: `google/gemini-3-flash-preview`. Rubric = Content / Design / Coherence (subjective, 1–5) + Visual Craft (objective Slidev-feature scan, 1–5). **Overall** = `0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence`. Unrenderable decks floor to 1.

<p align="center">
  <img src="results/eval/plots/overall_bar.png" alt="SlidevBench Weighted Overall per model — nemoslides-30b-a3b ranks #1 in both floor-scored and renderable regimes" width="100%" />
</p>

**`nemoslides-30b-a3b` ranks #1** at **3.69 floor / 3.99 renderable** — beats `gpt-5.4`, `glm-5.1`, and the `nemotron-super` 120B base. Against the Nano base: **+48% Overall** (`2.50 → 3.69`), +1.56 Design, +1.53 Visual Craft, render rate `87% → 93%`.

<p align="center">
  <img src="results/eval/plots/sft_delta.png" alt="Base vs SFT per-dim gain" width="88%" />
</p>

Full plots → [`results/eval/plots/`](results/eval/plots/). Numbers → [`results/eval/comparison_table.md`](results/eval/comparison_table.md).

## Quickstart

```bash
uv sync                       # installs nemoslides + deps
cp .env.example .env          # fill: OPENROUTER_API_KEY, UNSPLASH_ACCESS_KEY
cd assets/renderer && npm i && cd ../..
uv run uvicorn nemoslides.demo.app:app --reload    # prompt-to-deck web UI
```

## How it works

1. **Synthesis.** Seeds generated via [NeMo Data Designer](https://github.com/NVIDIA-NeMo/DataDesigner) (categorical spine × GLM-5.1); Codex authors `PROMPT.md` / `think.md` / `deck.md` per seed. 705 train + 30 test.
2. **Render-validate.** Slidev + Playwright compile every sample; parse errors, Vue overlays, and <3-slide renders are dropped.
3. **Pack.** Chat-JSONL with `reasoning_content` on the assistant turn; pushed to HF Hub.
4. **SFT.** NeMo-RL `run_sft.py` + LoRA + FSDP2. Recipe at `src/nemoslides/train/recipes/`.
5. **SlidevBench.** Generate → render → judge. Identical protocol for base and finetuned — the delta is what counts.

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
# 1. Baseline SlidevBench.
uv run python -m nemoslides.eval.run --model nemotron-nano
uv run python -m nemoslides.eval.compare

# 2. Synthesize corpus.
WORK=work-$(date +%Y%m%d)
uv run python -m nemoslides.cli.codex_pipeline init --seeds data/seeds.json --out "$WORK"
./scripts/run_codex_batch.sh "$WORK"
uv run python -m nemoslides.cli.push_hf_dataset --work "$WORK" --push

# 3. SFT (requires 2n8g).
./src/nemoslides/train/launch.sh

# 4. Re-run step 1 against the finetuned checkpoint.
```

Full writeup: [docs](docs/index.md).

## References

- **Base model:** [Nemotron-3-Nano-30B-A3B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16)
- **Training:** [NeMo-RL](https://github.com/NVIDIA-NeMo/RL)
- **Data synthesis:** [NeMo Data Designer](https://github.com/NVIDIA-NeMo/DataDesigner)
- **Rubric:** [PPTAgent (EMNLP 2025)](https://arxiv.org/abs/2501.03936) · [AutoPresent (CVPR 2025)](https://arxiv.org/abs/2501.00912)
- **Format:** [Slidev](https://sli.dev)

## License

Code: Apache-2.0. Model weights: governed by the [NVIDIA Open Model License](https://developer.download.nvidia.com/licenses/nvidia-open-model-license-agreement). Dataset: research use only.

---

<p align="center">Built for the <b>NVIDIA Nemotron Hackathon 2026 · Track B</b> by <a href="https://trillionlabs.co">Trillion Labs</a>.</p>
