#!/usr/bin/env bash
# usage: run_tests_ws.sh <lane-dir-name>   full suite + verify in a detached tmux session
set -u
lane="$1"; sess="tests-$lane"; L=~/archpipe/logs/lanes
if tmux has-session -t "$sess" 2>/dev/null; then echo "session $sess already running"; exit 1; fi
rm -f $L/$lane.done
tmux new-session -d -s "$sess" -c ~/archpipe/work/$lane \
  "bash -c 'export PYTHONPATH=src NO_COLOR=1; P=/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python; s=\$(date +%s); \$P -m unittest discover -s tests > $L/$lane-suite.log 2>&1; u=\$?; \$P scripts/verify.py --portable > $L/$lane-verify.log 2>&1; v=\$?; echo unittest=\$u verify=\$v secs=\$((\$(date +%s)-s)) > $L/$lane.done'"
echo "started $sess; attach: tmux attach -t $sess"
