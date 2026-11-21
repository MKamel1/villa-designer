#!/usr/bin/env bash
# usage: run_lane.sh <lane-dir-name> <prompt-file>
# Runs `codex exec` for one lane inside a detached tmux session (survives ssh drops),
# logging to ~/archpipe/logs/lanes/<lane>-<name>.log and writing a .done marker.
set -u
lane="$1"; prompt="$2"; name=$(basename "$prompt" .txt)
log=~/archpipe/logs/lanes/$lane-$name.log; done=~/archpipe/logs/lanes/$lane-$name.done
sess="codex-$lane"
if tmux has-session -t "$sess" 2>/dev/null; then echo "session $sess already running"; exit 1; fi
rm -f "$done"
tmux new-session -d -s "$sess" -c ~/archpipe/work/$lane \
  "bash -lc 'codex exec --sandbox workspace-write -m gpt-6.1-sol --skip-git-repo-check \"\$(cat $prompt)\" > $log 2>&1; echo exit=\$? > $done'"
echo "started $sess ($name); attach: tmux attach -t $sess"
