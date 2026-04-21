#!/usr/bin/env bash
# Pick one representative synthesized deck per theme and render it to PNGs.
#
# Usage:
#   ./scripts/render_theme_gallery.sh <synth_dir> <out_gallery_dir>
#
# For each unique theme present in synth_dir/*.json, takes the first record,
# writes its deck_md to a scratch file, and renders via renderer/render.sh.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <synth_dir> <out_gallery_dir>" >&2
  exit 1
fi

SYNTH_DIR="$(cd "$1" && pwd)"
OUT_DIR="$(mkdir -p "$2" && cd "$2" && pwd)"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

cd "$REPO_DIR"

# Build a map file of "theme<TAB>path" — one line per theme (first valid record).
PICKS_FILE="$SCRATCH/picks.tsv"
uv run --quiet python - "$SYNTH_DIR" "$PICKS_FILE" <<'PY'
import json, sys, pathlib
d, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
seen = {}
for f in sorted(d.glob("*.json")):
    try:
        rec = json.loads(f.read_text())
    except Exception:
        continue
    if not rec.get("valid", False):
        continue
    theme = (rec.get("seed") or {}).get("theme_hint") or "unknown"
    seen.setdefault(theme, str(f))
with out.open("w") as fh:
    for theme, p in sorted(seen.items()):
        fh.write(f"{theme}\t{p}\n")
PY

n_picks=$(wc -l < "$PICKS_FILE" | tr -d ' ')
if [[ "$n_picks" -eq 0 ]]; then
  echo "No valid records found in $SYNTH_DIR" >&2
  exit 1
fi

echo "Rendering $n_picks theme decks..."
while IFS=$'\t' read -r theme recpath; do
  [[ -z "$theme" ]] && continue
  deck_md="$SCRATCH/$theme.md"
  uv run --quiet python - "$recpath" "$theme" "$deck_md" <<'PY'
import json, sys
rec = json.loads(open(sys.argv[1]).read())
seed = rec.get("seed") or {}
theme = sys.argv[2]
topic = (seed.get("topic") or "")[:80]
audience = (seed.get("audience") or "")[:60]
with open(sys.argv[3], "w") as fh:
    fh.write(f"<!-- theme={theme} topic={topic} audience={audience} -->\n")
    fh.write(rec["deck_md"])
PY
  out_theme="$OUT_DIR/$theme"
  echo ""
  echo "=== $theme ==="
  if "$REPO_DIR/renderer/render.sh" "$deck_md" "$out_theme" > "$SCRATCH/$theme.log" 2>&1; then
    n=$(ls "$out_theme"/*.png 2>/dev/null | wc -l | tr -d ' ')
    echo "  -> $n PNGs at $out_theme"
  else
    echo "  !! render failed for $theme (see $SCRATCH/$theme.log)"
    tail -5 "$SCRATCH/$theme.log" || true
  fi
done < "$PICKS_FILE"

echo ""
echo "Gallery written to $OUT_DIR"
