#!/usr/bin/env bash
# Render a Slidev deck to PNGs using the canonical renderer env.
#
# Usage: ./renderer/render.sh <input.md> <output_dir>
#
# Pre-processing:
#   - Any `image-query: "<text>"` frontmatter field is resolved to a real
#     Unsplash URL by `pipeline.image_resolver` before Slidev sees the file.
#
# Slidev resolves themes relative to the directory containing the deck (not
# the CLI's cwd), so we stage the preprocessed deck inside renderer/.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <input.md> <output_dir>" >&2
  exit 1
fi

INPUT_ABS="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUTPUT_ABS="$(mkdir -p "$2" && cd "$2" && pwd)"
RENDERER_DIR="$(cd "$(dirname "$0")" && pwd)"
# renderer moved to assets/renderer/, so repo is 2 levels up (not 1)
REPO_DIR="$(cd "$RENDERER_DIR/../.." && pwd)"

# Include PID + nanoseconds so parallel invocations never collide on the tmp name.
STAGED="$(mktemp "$RENDERER_DIR/.tmp-deck-$$-$(date +%N)-XXXXXX.md")"
trap 'rm -f "$STAGED"' EXIT

# resolve image-query placeholders via the uv-managed python env at the repo root
( cd "$REPO_DIR" && PYTHONPATH=src uv run --quiet python -m nemoslides.pipeline.image_resolver "$INPUT_ABS" -o "$STAGED" )

cd "$RENDERER_DIR"

# Slidev's `export` internally calls getPort(12445), which races when
# multiple export processes run in parallel (both see 12445 as free,
# one binds, the other's Playwright fails with ERR_CONNECTION_REFUSED).
# Serialize across processes with an exclusive file lock.
LOCKFILE="/tmp/slidev-export.lock"
STAGED_BASE="$(basename "$STAGED")"

python3 - "$LOCKFILE" "$STAGED_BASE" "$OUTPUT_ABS" "$RENDERER_DIR" <<'PYEOF'
import fcntl, subprocess, sys
lockfile, staged, output, cwd = sys.argv[1:5]
with open(lockfile, "w") as lf:
    fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
    proc = subprocess.run(
        ["npx", "slidev", "export", staged,
         "--format", "png",
         "--output", output,
         "--dark", "false",
         "--per-slide",
         "--timeout", "60000"],
        cwd=cwd,
    )
    sys.exit(proc.returncode)
PYEOF
