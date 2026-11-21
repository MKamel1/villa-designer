#!/usr/bin/env bash
# Runs inside the tmux session "villa-lead" (see start_lead.sh).
cd "$HOME/archpipe/lead"
export PATH="$HOME/.local/bin:$HOME/archpipe/envs/laneP-venv/bin:$HOME/archpipe/bin:$PATH"
claude --model opus --dangerously-skip-permissions "$(cat "$HOME/archpipe/lead/ops/workstation/lead_prompt.md")"
echo "claude exited; this shell stays open (restart: claude --model opus --dangerously-skip-permissions --continue)"
exec bash
