#!/bin/zsh
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "usage: $0 <workdir> [parallelism] [session_name]" >&2
  exit 2
fi

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
WORK_DIR_INPUT="$1"
PARALLELISM="${2:-6}"
SESSION_NAME="${3:-codex-batch}"

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

PROMPT='Read seed.json, INSTRUCTIONS.md, HERO_EXAMPLE.md, and the PROMPT.md/think.md/deck.md stubs in this folder only. Replace all three stub files completely with final content. Do not inspect sibling folders. Follow INSTRUCTIONS.md exactly and finish with valid Slidev markdown in deck.md.'

tmux has-session -t "$SESSION_NAME" 2>/dev/null && {
  echo "tmux session already exists: $SESSION_NAME" >&2
  exit 1
}

tmux new-session -d -s "$SESSION_NAME" "cd '$ROOT_DIR' && export CODEX_DISABLE_TELEMETRY=1 && find '$WORK_DIR' -mindepth 1 -maxdepth 1 -type d -name 'seed_*' | sort | xargs -I{} -P '$PARALLELISM' sh -c '
ready_file() {
  file=\"\$1\"
  min_bytes=\"\$2\"
  [ -f \"\$file\" ] || return 1
  [ \"\$(wc -c < \"\$file\")\" -ge \"\$min_bytes\" ] || return 1
  ! head -n 2 \"\$file\" | tail -n 1 | grep -q \"^Codex:\"
}
d=\"\$1\"
if ready_file \"\$d/PROMPT.md\" 40 && ready_file \"\$d/think.md\" 400 && ready_file \"\$d/deck.md\" 300; then
  exit 0
fi
codex exec --full-auto --ephemeral --skip-git-repo-check -C \"\$d\" -o \"\$d/codex_last.txt\" \"$PROMPT\" > \"\$d/codex_run.log\" 2>&1
' sh {} > '$LOG_DIR/xargs.log' 2>&1; python3 -m nemoslides.cli.codex_pipeline status --work '$WORK_DIR' > '$LOG_DIR/final_status.txt' 2>&1"

echo "started session: $SESSION_NAME"
echo "workdir: $WORK_DIR"
echo "parallelism: $PARALLELISM"
echo "log: $LOG_DIR/xargs.log"
