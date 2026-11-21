#!/usr/bin/env bash
# Run one A+ lane as an unattended Claude Code (Sonnet) session on the workstation.
#
#   launch:  systemd-run --user --unit=lane-<ID> --collect \
#              ~/archpipe/ops/run_claude_lane.sh <ID> ~/archpipe/lanes/briefs/<ID>.md
#   watch:   tail -f ~/archpipe/lanes/<ID>.log ; cat ~/archpipe/lanes/<ID>.status
#   result:  ~/archpipe/lanes/<ID>.report.md   (the agent's final hand-back)
#
# The lane works in its own GitHub clone (~/archpipe/lanes/<ID>) on branch lane/<ID>,
# branched from origin/integ/aplus (or resumed from origin/lane/<ID> if it exists),
# and pushes that branch itself. Permissions: full bypass (client decision 2026-11-21).
set -uo pipefail
LANE="$1"; BRIEF="$2"
ROOT="$HOME/archpipe/lanes"; DIR="$ROOT/$LANE"
LOG="$ROOT/$LANE.log"; REPORT="$ROOT/$LANE.report.md"; STATUS="$ROOT/$LANE.status"
SHARED_ASSETS="$HOME/archpipe/shared/assets/user"
mkdir -p "$ROOT"
echo "running $(date -Is)" > "$STATUS"
exec 2>>"$LOG"

if [ ! -d "$SHARED_ASSETS" ] && [ -d "$HOME/archpipe/work/laneP/assets/user" ]; then
  mkdir -p "$(dirname "$SHARED_ASSETS")"
  cp -a "$HOME/archpipe/work/laneP/assets/user" "$SHARED_ASSETS"
fi

if [ ! -d "$DIR/.git" ]; then
  git clone -q git@github.com:MKamel1/villa-designer.git "$DIR" || { echo "failed clone $(date -Is)" > "$STATUS"; exit 1; }
fi
cd "$DIR"
git config user.name "villa-designer lane $LANE"
git config user.email "lane-$LANE@ai-workstation.local"
git config core.autocrlf false
git fetch -q origin
if git ls-remote --exit-code --heads origin "lane/$LANE" >/dev/null 2>&1; then
  git checkout -q -B "lane/$LANE" "origin/lane/$LANE"
else
  git checkout -q -B "lane/$LANE" origin/integ/aplus
fi
if [ ! -e assets/user ] && [ -d "$SHARED_ASSETS" ]; then
  mkdir -p assets && ln -s "$SHARED_ASSETS" assets/user
fi

export PATH="$HOME/.local/bin:$HOME/archpipe/envs/laneP-venv/bin:$PATH"
export PYTHONPATH=src
PREAMBLE="You are running unattended on the Linux GPU workstation (ai-workstation) in a GitHub clone at $DIR on branch lane/$LANE. Python: $HOME/archpipe/envs/laneP-venv/bin/python (on PATH as python). Blender, Radiance and Ollama are local; GPU jobs go through ~/archpipe/bin/jobq (docs/lanes/L8-runner.md). There is no human to answer questions: decide within scope and list decisions. Push lane/$LANE to origin after each step. Your final message is your hand-back report."
echo "=== start $(date -Is) lane=$LANE" >> "$LOG"
claude -p "$PREAMBLE

$(cat "$BRIEF")" --model sonnet --dangerously-skip-permissions --output-format text > "$REPORT" 2>>"$LOG"
RC=$?
git push -q origin "lane/$LANE" 2>>"$LOG"
echo "=== end $(date -Is) rc=$RC" >> "$LOG"
if [ $RC -eq 0 ]; then echo "done $(date -Is)" > "$STATUS"; else echo "failed rc=$RC $(date -Is)" > "$STATUS"; fi
exit $RC
