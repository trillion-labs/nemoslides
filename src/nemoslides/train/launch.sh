#!/usr/bin/env bash
# Launch NemoSlides SFT via NeMo-RL.
#
# Clones NeMo-RL on first run, syncs deps, fires run_sft.py with the
# NemoSlides recipe. Run from the repo root.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
NEMO_RL_DIR="${NEMO_RL_DIR:-$REPO_DIR/.external/NeMo-RL}"
RECIPE="$REPO_DIR/src/nemoslides/train/recipes/sft-nemotron-nano-lora.yaml"

if [[ ! -d "$NEMO_RL_DIR" ]]; then
  mkdir -p "$(dirname "$NEMO_RL_DIR")"
  git clone --depth 1 https://github.com/NVIDIA-NeMo/RL.git "$NEMO_RL_DIR"
fi

cd "$NEMO_RL_DIR"
uv sync

exec uv run python examples/run_sft.py --config-path "$REPO_DIR/src/nemoslides/train/recipes" --config-name sft-nemotron-nano-lora
