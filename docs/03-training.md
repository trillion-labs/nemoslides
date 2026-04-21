# 03 — Training

*NemoSlides is a LoRA adapter produced by NeMo-RL's `run_sft.py` on top of the post-trained `NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` checkpoint. The recipe is the published 2n8g LoRA + FSDP2 configuration for this model family. Only two values are customized versus the published recipe: the policy model checkpoint and the training data path.*

## Base model

`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` — the post-trained instruction/reasoning variant.

| Property | Value |
|---|---|
| Architecture | Mixture-of-Experts |
| Total parameters | 30B |
| Active parameters | 3B |
| Context length | 128K |
| Modality | Text-only |
| License | [NVIDIA Open Model License](https://developer.download.nvidia.com/licenses/nvidia-open-model-license-agreement) |
| Chat template | Native `<think>...</think>` reasoning, `enable_thinking=true` default |

The native reasoning format is load-bearing. Training samples (see [02 · Data](02-data.md)) carry the same `<think>` block in the assistant content, so the SFT loop specializes an existing reasoning behavior for slide generation rather than teaching chat format from scratch. Both the baseline eval and the finetuned eval run against this model with `enable_thinking=true`; the only variable between the two runs is the LoRA adapter.

## Training framework — NeMo-RL SFT

NemoSlides uses [`NVIDIA-NeMo/RL`](https://github.com/NVIDIA-NeMo/RL) with the `examples/run_sft.py` entry point and the `ResponseDataset` adapter for chat-JSONL input. The base recipe is [`sft-nanov3-30BA3B-2n8g-fsdp2-lora.yaml`](https://github.com/NVIDIA-NeMo/RL/tree/main/examples/configs/recipes/llm) — LoRA parameter-efficient fine-tuning with FSDP2 sharding on a 2-node × 8-GPU layout.

The local copy of the recipe lives at `src/nemoslides/train/recipes/`. The launch wrapper at `src/nemoslides/train/launch.sh` invokes NeMo-RL with two parameter overrides; everything else — LoRA rank, sequence length, FSDP2 sharding, AdamW configuration, learning-rate schedule — stays as NVIDIA publishes it. Inheriting the published recipe also inherits its convergence behavior on this model family. **Pure SFT only** — no DPO, GRPO, or reward modeling — so any capability Δ between base and finetuned can only be attributed to the LoRA adapter weights.

```bash
./src/nemoslides/train/launch.sh
```

## Training data format

One chat-format JSONL row per sample — text-only, no multimodal generation path (images enter decks via the render-time resolver described in [02 · Data](02-data.md)). The training target is `topic → deck` as one unit, not factored into an outline-generation stage; deploying an outline/deck split is a downstream engineering concern this project doesn't need to answer. Assistant content carries both the reasoning trace and the Slidev markdown in a single string, wrapped in `<think>`:

```jsonl
{"messages": [
  {"role": "system", "content": "<Slidev expert system prompt + knowledge pack>"},
  {"role": "user", "content": "Create a Slidev deck: <topic · audience · tone · constraints>"},
  {"role": "assistant", "content": "<think>\n<reasoning>\n</think>\n\n---\ntheme: seriph\nlayout: cover\n---\n# ...\n..."}
]}
```

The system prompt is identical at synthesis time (when Codex authored the corpus), at training time (when NeMo-RL's `ResponseDataset` loads the chat messages), and at inference time (when vLLM serves the finetuned model). This keeps the training and inference distributions in lockstep.

The published dataset ([`trillionlabs/slides-sft-v0`](https://huggingface.co/datasets/trillionlabs/slides-sft-v0)) additionally exposes `reasoning_content` as a separate field on the assistant turn for downstream tooling that consumes reasoning traces structurally. The training loop itself reads from the concatenated `content`.

Images in training decks appear as `image-query:` placeholders rather than resolved URLs. Image backend concerns (Unsplash / Pexels / internal CDN) are render-time concerns; the model training stays backend-agnostic. Full rationale in [02 · Data](02-data.md#image-query-placeholders).

## Inference at eval time

vLLM serves the post-trained Nemotron checkpoint with the NemoSlides LoRA adapter attached. Inference parameters:

```yaml
chat_template_kwargs:
  enable_thinking: true
sampling:
  temperature: 1.0      # Nano-3 model card recommendation for reasoning
  top_p: 1.0
```

`reasoning_budget` is available for trace-length control on a per-request basis; the default leaves trace length to the model.

Served via `nemoslides.pipeline.clients` as an OpenAI-compatible vLLM endpoint (tunneled from the training node). The baseline eval run reuses the identical vLLM configuration with no adapter loaded. No other variable differs between base and finetuned evaluation; the Δ attribution is unambiguous.
