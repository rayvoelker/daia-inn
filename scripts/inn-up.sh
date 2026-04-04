#!/usr/bin/env bash
# Launch the daia-inn tmux workspace.
# Usage: ./scripts/inn-up.sh
#
# Attaches if the session already exists, otherwise loads the tmuxp config.

set -euo pipefail

SESSION="daia-inn"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG="$PROJECT_DIR/tmuxp.yaml"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Session '$SESSION' already running — attaching."
    tmux attach-session -t "$SESSION"
else
    cd "$PROJECT_DIR"
    uv run tmuxp load "$CONFIG"
fi
