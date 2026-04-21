# NemoSlides training

SFT the `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` post-trained checkpoint
on the packed chat-JSONL corpus (`trillionlabs/slides-sft-v0`) using
[NeMo-RL](https://github.com/NVIDIA-NeMo/RL)'s `examples/run_sft.py` with
LoRA + FSDP2.

## Layout

```
train/
├── recipes/
│   └── sft-nemotron-nano-lora.yaml   - NeMo-RL recipe (LoRA + FSDP2)
└── launch.sh                          - one-shot launcher (clones NeMo-RL, runs SFT)
```

## Run

```bash
# One-shot: clones NeMo-RL (if missing), syncs deps, launches SFT on 2n8g.
./src/nemoslides/train/launch.sh
```

The recipe is adapted from NeMo-RL's published
`sft-nanov3-30BA3B-2n8g-fsdp2-lora.yaml` — only the dataset path, output
directory, and run name are project-specific.
