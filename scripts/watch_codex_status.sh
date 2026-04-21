#!/bin/zsh
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <workdir> [interval_seconds]" >&2
  exit 2
fi

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
WORK_DIR_INPUT="$1"
INTERVAL="${2:-120}"

if [[ "$WORK_DIR_INPUT" = /* ]]; then
  WORK_DIR="$WORK_DIR_INPUT"
else
  WORK_DIR="$ROOT_DIR/$WORK_DIR_INPUT"
fi

if [[ ! -d "$WORK_DIR" ]]; then
  echo "workdir not found: $WORK_DIR" >&2
  exit 1
fi

LOG_DIR="$WORK_DIR/_batch_logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/status_watch.log"

while true; do
  {
    echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
    python3 -m nemoslides.cli.codex_pipeline status --work "$WORK_DIR"
    python3 - "$WORK_DIR" "$LOG_FILE" <<'PY'
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

work_dir = Path(sys.argv[1])
log_file = Path(sys.argv[2])
mins = {"PROMPT.md": 40, "think.md": 400, "deck.md": 300}


def is_complete(folder: Path) -> bool:
    for name, min_bytes in mins.items():
        path = folder / name
        if not path.exists():
            return False
        text = path.read_text(errors="ignore").strip()
        if len(text.encode()) < min_bytes or text.startswith("<!--\nCodex:"):
            return False
    return True


seed_folders = sorted(p for p in work_dir.glob("seed_*") if p.is_dir())
complete = sum(1 for folder in seed_folders if is_complete(folder))
remaining = max(len(seed_folders) - complete, 0)

timestamp_re = re.compile(r"^===== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
complete_re = re.compile(r"^complete:\s+(\d+)")
samples: list[tuple[datetime, int]] = []
if log_file.exists():
    current_ts: datetime | None = None
    for line in log_file.read_text(errors="ignore").splitlines():
        ts_match = timestamp_re.match(line)
        if ts_match:
            current_ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S")
            continue
        comp_match = complete_re.match(line)
        if comp_match and current_ts is not None:
            samples.append((current_ts, int(comp_match.group(1))))

rate = None
eta = None
if len(samples) >= 2:
    recent = samples[-6:]
    start_ts, start_complete = recent[0]
    end_ts, end_complete = recent[-1]
    elapsed = (end_ts - start_ts).total_seconds()
    delta = end_complete - start_complete
    if elapsed > 0 and delta > 0:
        rate = delta / elapsed
elif len(samples) == 1 and samples[0][1] < complete:
    start_ts, start_complete = samples[0]
    elapsed = max((datetime.now() - start_ts).total_seconds(), 1)
    delta = complete - start_complete
    if delta > 0:
        rate = delta / elapsed

if rate and remaining > 0:
    seconds_left = int(remaining / rate)
    eta = datetime.now() + timedelta(seconds=seconds_left)

if rate:
    print(f"throughput:      {rate * 60:.2f} seeds/min ({rate * 3600:.0f} seeds/hour)")
else:
    print("throughput:      warming up")
if eta:
    print(f"eta:             {eta.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print("eta:             warming up")
PY
    echo
  } >> "$LOG_FILE"
  sleep "$INTERVAL"
done
