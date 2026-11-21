#!/usr/bin/env bash
# Start the villa A+ orchestrator in a persistent tmux session on the workstation.
#   start:   ~/archpipe/ops/start_lead.sh
#   attach:  tmux attach -t villa-lead      (detach again: Ctrl-b then d)
# Claude runs with permissions bypassed (client decision 2026-11-21) in ~/archpipe/lead,
# with the start prompt from ops/workstation/lead_prompt.md already submitted.
set -euo pipefail
SESSION=villa-lead
LEAD="$HOME/archpipe/lead"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' is already running: tmux attach -t $SESSION"
  exit 0
fi
cd "$LEAD"
git pull -q --ff-only origin integ/aplus || echo "warning: could not fast-forward integ/aplus"
tmux new-session -d -s "$SESSION" -c "$LEAD" "$HOME/archpipe/ops/run_lead.sh"
echo "started tmux session '$SESSION': tmux attach -t $SESSION"
