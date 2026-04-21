# 03 — Training

Nothing in the training stack is novel. The point is that it doesn't need to be. A published NVIDIA recipe, the post-trained Nemotron checkpoint, and a clean chat-JSONL corpus produce the result we need. This doc walks through why each piece is the right pick and what the alternatives were.

## Base model: post-trained Nemotron-3-Nano-30B-A3B

*Post-trained variant, not the pretraining checkpoint. Native `<think>` reasoning is already there; SFT specializes an existing behavior rather than teaching chat format from scratch.*

`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` — the **post-trained** instruction/reasoning variant. MoE, 3B active params out of 30B total, 128K context, text-only, NVIDIA Open Model License.

The two deciding properties:

**Native `<think>` reasoning.** The post-trained model already emits `<think>...</think>` blocks and already has `enable_thinking=True` as the default chat-template flag. Our training samples carry exactly that format (see [02-data-pipeline.md](02-data-pipeline.md)).

The SFT loop specializes an existing reasoning behavior for slide generation — it doesn't teach the format from scratch. That's a dramatically smaller learning problem.

**Baseline cleanliness.** Both the baseline eval and the finetuned eval run against the same model with `enable_thinking=True`. The only thing that changes between the two runs is the LoRA adapter. Protocol identity matters for the Δ claim, and the post-trained checkpoint is what makes protocol identity easy.

**Rejected alternatives:**

- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-Base-BF16` (pretraining checkpoint). No chat template, no reasoning behavior, no instruction following. In 48h, the climb to produce a useful slide generator from a base checkpoint is unreasonable. Would also muddy the baseline-vs-finetuned story — the Δ would partially measure chat-format acquisition rather than the task-specific signal we want to isolate.
- Nemotron-Nano-9B-v2 (dense, older). Less capable starting point and less impressive as a final artifact.
- Nemotron-Nano-12B-v2-VL (multimodal). Overkill — the task target is markdown. Multimodal weights that never get exercised for input are wasted capacity and a harder recipe.

**Ablation, if hour-budget permits:** post-trained + SFT vs. base + SFT, to quantify how much of the final delta comes from post-training alignment. Not required for the Track B submission; a stretch item for the writeup only.

## Training framework: NeMo-RL SFT

*Published recipe, run as published. We change only the model checkpoint and the data path — everything else stays as NVIDIA ships it.*

`examples/run_sft.py` in [NVIDIA-NeMo/RL](https://github.com/NVIDIA-NeMo/RL), with the published `ResponseDataset` adapter for chat-JSONL input. The recipe we adapt is [`sft-nanov3-30BA3B-2n8g-fsdp2-lora.yaml`](https://github.com/NVIDIA-NeMo/RL/tree/main/examples/configs/recipes/llm) — LoRA + FSDP2, 2-node 8-GPU layout as published.

Two things this gets us:

**Hackathon eligibility.** The Track B submission must use a NeMo Framework component or Microservice. NeMo-RL's SFT path satisfies that explicitly. TRL+PEFT would be simpler but fails the eligibility gate — a disqualifying choice, not a marginal one.

**Zero recipe drift.** The published LoRA+FSDP2 config already has sane defaults for this model family. We change two things: `policy.model_name` to the post-trained Nemotron checkpoint, and the data path to `data/train.jsonl` (packed from the HF Hub dataset).

Everything else — LoRA rank, sequence length, FSDP2 sharding, AdamW beta/weight-decay, LR schedule — stays as published. The training loss curve and the deployment story both benefit from that inheritance.

**Rejected alternatives:**

- **TRL / PEFT / Axolotl.** Simpler, more familiar, and widely used for this size class. Fails the NeMo-component eligibility rule — this is a hard stop for Track B.
- **NeMo 2.0 / Megatron.** Overkill for ~700 samples over 2 days. Better fit for a pretraining-scale job or a larger corpus.
- **NeMo-AutoModel.** Kept as a backup path in case the NeMo-RL install broke (it didn't). Also eligibility-compliant.

## Training data format

*Chat JSONL with reasoning trace and Slidev markdown concatenated in the assistant content. System prompt is identical at synthesis, training, and inference — training and inference stay in distributional lockstep.*

Chat JSONL. One row per sample. Assistant content carries both the reasoning trace and the Slidev markdown in a single string, with `<think>...</think>` around the reasoning block.

The HF Hub dataset additionally exposes `reasoning_content` as a separate field on the assistant turn for tooling that consumes reasoning traces structurally; the training loop reads from the concatenated `content`.

```jsonl
{"messages": [
  {"role": "system", "content": "<Slidev expert system prompt + knowledge pack>"},
  {"role": "user", "content": "Create a Slidev deck: <topic, audience, constraints>"},
  {"role": "assistant", "content": "<think>\n<reasoning>\n</think>\n\n---\ntheme: seriph\nlayout: cover\n---\n# ...\n..."}
]}
```

The system prompt is the same one injected at synthesis time — `pipeline.slidev_reference.TASK_INSTRUCTIONS` plus the Slidev cheatsheet. This is load-bearing: the finetuned model, at inference time, will receive that same system prompt and expect the idioms it was trained against. Training and inference stay in distributional lockstep.

Images in training decks appear as `image-query:` placeholders. URL resolution is a render-time concern, not a training-time concern. See [02-data-pipeline.md](02-data-pipeline.md) for the full rationale.

## What we're not doing

*Pure SFT, one stage, text-only, topic→deck as a single unit. Keeping the recipe narrow keeps the attribution story clean.*

**No DPO, GRPO, or reward modeling.** Pure SFT only. Two-day budget doesn't support a second training stage, and the published eval stack is not set up to disambiguate SFT contribution from RL contribution. Keeping the training recipe to one stage keeps the "what caused the Δ" attribution clean.

**No outline-generation SFT.** The target is `topic → deck` as one unit. A real end-to-end product would likely factor outline generation separately, but that's a v1 concern. Keeping the unit intact avoids a cascade of decisions about how to split and re-join.

**No multimodal training.** Text-only Nemotron. Images in decks are URL placeholders (resolved at render time) or emoji. A multimodal recipe would add hours of integration work for a capability we don't need — we're generating markdown, not PNGs.

## Inference at eval time

*vLLM, `enable_thinking=true`, Nano-3 recommended sampling. Baseline and finetuned runs share everything except the adapter.*

vLLM with the post-trained Nemotron + LoRA adapter, `chat_template_kwargs: {enable_thinking: true}`. Recommended generation params for the reasoning path: `temperature=1.0`, `top_p=1.0` (per the Nano-3 model card). `reasoning_budget` available for trace-length control if a particular eval prompt needs it; by default we let the model decide.

!!! info "Protocol identity"
    The baseline run uses the same vLLM setup with no adapter. **The only thing that differs between the base and finetuned eval is the adapter.** That's the whole point of the training recipe choice — everything else is pinned so the Δ attribution is unambiguous.
