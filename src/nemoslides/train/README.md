# NemoSlides training

SFT the `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` post-trained checkpoint
on the packed chat-JSONL corpus (`trillionlabs/slides-sft-v0`) using
[Automodel](https://github.com/NVIDIA-NeMo/Automodel)'s `automodel finetune llm`
with full-parameter fine-tuning. Then we ran DPO using [NeMo-RL](https://github.com/NVIDIA-NeMo/RL).

## Layout

```
train/
├── recipes/
│   ├── sft-nemotron-nano.yaml   - Automodel recipe (full-param)
│   └── dpo-nemotron-nano.yaml   - NeMo-RL DPO recipe
└── launch.sh                          - one-shot launcher (clones Automodel + NeMo-RL, runs SFT then DPO)
```

## Run

```bash
# One-shot: clones Automodel (if missing), syncs deps, launches SFT and DPO.
./src/nemoslides/train/launch.sh
```
