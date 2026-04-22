#!/usr/bin/env bash
# Build a hostable Slidev SPA using the canonical renderer env.
#
# Usage: ./assets/renderer/build.sh <input.md> <output_dir> <base_path>
#
# The deck is preprocessed first so any `image-query:` placeholders become
# real image URLs before Slidev compiles the site.

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <input.md> <output_dir> <base_path>" >&2
  exit 1
fi

INPUT_ABS="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUTPUT_ABS="$(mkdir -p "$2" && cd "$2" && pwd)"
BASE_PATH="$3"
RENDERER_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$RENDERER_DIR/../.." && pwd)"
DEFAULT_PYTHON="$REPO_DIR/.venv/bin/python"
if [[ -x "$DEFAULT_PYTHON" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-$DEFAULT_PYTHON}"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
fi

STAGED="$(mktemp "$RENDERER_DIR/.tmp-deck-$$-$(date +%N)-XXXXXX.md")"
trap 'rm -f "$STAGED"' EXIT

( cd "$REPO_DIR" && "$PYTHON_BIN" -m nemoslides.pipeline.image_resolver "$INPUT_ABS" -o "$STAGED" )

cd "$RENDERER_DIR"
npx slidev build "$(basename "$STAGED")" --out "$OUTPUT_ABS" --base "$BASE_PATH"

# Hide Slidev's goto-dialog (slide title list in upper-right corner).
if [[ -f "$OUTPUT_ABS/index.html" ]]; then
  sed -i '' 's|</head>|<style>#slidev-goto-dialog{display:none!important}</style></head>|' "$OUTPUT_ABS/index.html"
fi
