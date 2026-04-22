#!/usr/bin/env bash
# Launch NemoSlides SFT via Automodel.
#
# Clones Automodel on first run, syncs deps, runs full-param SFT with the
# NemoSlides recipe. Run from the repo root.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"

# Setup SFT
AUTOMODEL_DIR="${AUTOMODEL_DIR:-$REPO_DIR/.external/Automodel}"
SFT_RECIPE="$REPO_DIR/src/nemoslides/train/recipes/sft-nemotron-nano.yaml"

if [[ ! -d "$AUTOMODEL_DIR" ]]; then
  mkdir -p "$(dirname "$AUTOMODEL_DIR")"
  git clone https://github.com/NVIDIA-NeMo/Automodel.git "$AUTOMODEL_DIR"
fi

cd "$AUTOMODEL_DIR"
uv sync --frozen --extra cuda

# Setup DPO
NEMO_RL_DIR="${NEMO_RL_DIR:-$REPO_DIR/.external/NeMo-RL}"
DPO_RECIPE="$REPO_DIR/src/nemoslides/train/recipes/dpo-nemotron-nano.yaml"

if [[ ! -d "$NEMO_RL_DIR" ]]; then
  mkdir -p "$(dirname "$NEMO_RL_DIR")"
  git clone --depth 1 https://github.com/NVIDIA-NeMo/RL.git "$NEMO_RL_DIR"
fi

cd "$NEMO_RL_DIR"
uv venv

# Run SFT
cd "$AUTOMODEL_DIR"
uv run automodel finetune llm -c "$SFT_RECIPE"

# Run DPO
cd "$NEMO_RL_DIR"
uv run python examples/dpo.py --config "$DPO_RECIPE"
