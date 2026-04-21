# Reproduce

*The full experimental protocol: environment setup, baseline evaluation, corpus synthesis, training, finetuned evaluation. Steps 1 and 4 share byte-identical configuration — the Δ they produce is the project's headline claim.*

## 0 · Environment

Python dependencies managed by [`uv`](https://docs.astral.sh/uv/). Node required for the Slidev renderer.

```bash
# Python + project (hatchling-built, installed editable)
uv sync                       # runtime
uv sync --group dev           # + pytest / ruff
uv sync --only-group docs     # + mkdocs (docs-site only)

# API keys
cp .env.example .env
# fill: OPENROUTER_API_KEY (required — base + judge + reference models)
#       UNSPLASH_ACCESS_KEY (required — image resolver)
#       GEMINI_API_KEY      (optional — direct Google API for judge)
#       OPENAI_API_KEY      (optional — legacy qualitative_check only)

# Slidev renderer (Node)
cd assets/renderer && npm install && cd ../..
```

Verify: `uv run pytest` should pass. `./assets/renderer/render.sh assets/reference/gold_examples/hero_tech_talk.md /tmp/render-test` should produce a slide directory of PNGs.

## 1 · Baseline SlidevBench

The baseline is the reference point every SFT claim is compared against. It runs *before* any training begins.

```bash
# One reference model at a time; resumable per-seed via score.json gates.
uv run python -m nemoslides.eval.run --model nemotron-nano --concurrency 15

# All four reference points.
for m in nemotron-nano nemotron-super glm-5.1 gpt-5.4; do
  uv run python -m nemoslides.eval.run --model $m
done

# Aggregate + plot.
uv run python -m nemoslides.eval.compare
uv run python -m nemoslides.eval.plot
```

Outputs at `results/eval/runs/<model>/<seed>/` (`deck.md`, `reasoning.md`, `gen.md`, `slides/*.png`, `score.json`) and aggregated at `results/eval/comparison.json` / `comparison_table.md`. Plots at `results/eval/plots/`.

**Resumability.** A seed folder with a valid `score.json` is skipped. Delete that file to re-judge an existing render; delete the whole seed folder to regenerate + re-render + re-judge.

## 2 · Synthesize the training corpus

```bash
# Generate seeds with NeMo Data Designer.
uv run python -m nemoslides.pipeline.seeds_dd --out data/seeds.json

# Materialize per-seed Codex workspace.
WORK=work-$(date +%Y%m%d)
uv run python -m nemoslides.cli.codex_pipeline init \
  --seeds data/seeds.json --out "$WORK"

# Run Codex in parallel across all seeds (tmux-driven, 6-way default).
./scripts/run_codex_batch.sh "$WORK"

# Monitor progress.
./scripts/watch_codex_status.sh "$WORK"
uv run python -m nemoslides.cli.codex_pipeline status --work "$WORK"

# Validate + pack completed folders.
uv run python -m nemoslides.cli.codex_pipeline pack \
  --work "$WORK" --out data/raw/codex
```

Validators (prompt substance, think substance, deck syntax, image-URL ban, frontmatter hygiene) run during `pack` and drop non-conformant folders. Scan the output for the kept/dropped counts.

## 3 · Publish to Hugging Face Hub

```bash
# Pack kept folders into chat-JSONL and push.
uv run python -m nemoslides.cli.push_hf_dataset --work "$WORK" --push
```

Target: `trillionlabs/slides-sft-v0`. The dataset ships `messages[0..2]` with `reasoning_content` exposed as a separate field on the assistant turn.

## 4 · SFT with NeMo-RL

Requires a 2n8g layout (2 nodes × 8 GPUs) per the published LoRA+FSDP2 recipe.

```bash
./src/nemoslides/train/launch.sh
```

The launch script invokes NeMo-RL `examples/run_sft.py` with two overrides against the published recipe:

- `policy.model_name = nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`
- Data path pointing at the packed chat-JSONL from step 3.

Everything else — LoRA rank, sequence length, FSDP2 sharding, AdamW, LR schedule — stays as NVIDIA publishes. See [03 · Training](03-training.md) for detail.

## 5 · Serve the finetuned checkpoint

vLLM with the base Nemotron checkpoint and the LoRA adapter attached. Registered in `nemoslides.pipeline.clients` as the model alias passed to `--model` in step 6 below. If running on a remote node, tunnel the port:

```bash
ssh -N -L 8000:localhost:8000 <training-node>
```

## 6 · Finetuned SlidevBench — identical protocol

Same 30 prompts, same judge, same rubric, same render pipeline, same aggregation formula as step 1.

```bash
uv run python -m nemoslides.eval.run --model nano-local --concurrency 15
uv run python -m nemoslides.eval.compare
uv run python -m nemoslides.eval.plot
```

The Δ between step-1 and step-6 Overall is the project's headline claim. A deviation from protocol identity invalidates the comparison — do not change the judge, rubric, render pipeline, or aggregation weights between the two runs.

## 7 · Human blindtest (optional second fold)

```bash
# Build a balanced pair queue from the render artifacts in step 1 + step 6.
uv run python -m nemoslides.blindtest.build_pairs

# Start the voting UI.
uv run python -m nemoslides.blindtest.app
# → http://localhost:5000
```

Votes persist to `results/blindtest/votes.db`. Results feed back into [05 · Results](05-results.md#human-blindtest).

## Demo

Optional — the prompt-to-deck web UI.

```bash
uv run uvicorn nemoslides.demo.app:app --reload
# → http://localhost:8000
```

Requires `DEMO_OPENAI_API_KEY` in `.env` (or falls back to `OPENAI_API_KEY` + model `gpt-5.4` for showcase). Set `DEMO_OPENAI_BASE_URL` to point at the NemoSlides vLLM endpoint for end-to-end local inference.
