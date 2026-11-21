#!/usr/bin/env bash
# usage: auto_resume.sh <lane> <prompt-file>
# Runs a Codex lane job; if it stops on a usage limit or a capacity error,
# waits until the stated reset time (+5 min) and re-runs it with a resume note.
# Gives up after 6 attempts. Logs to ~/archpipe/logs/lanes/<lane>-<name>.autoresume.
#
# Differences from the 2026-10 original (docs/reviews/2026-11/workstation-ops.md, S3):
#  - a crash (nonzero exit that is not a quota/capacity stop) is logged "crashed", not "finished",
#    and exits nonzero, so lane_queue.sh does not mistake it for success;
#  - the wait for the .done marker has a timeout (AUTORESUME_MAX_WAIT_S, default 12 h) and notices
#    a vanished tmux session (e.g. after a reboot) instead of waiting forever;
#  - run it under jobq (`jobq submit --id lane-<lane> --timeout 172800 -- auto_resume.sh ...`) to survive a reboot.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
lane="$1"; prompt="$2"; name=$(basename "$prompt" .txt)
L=~/archpipe/logs/lanes; A="$L/$lane-$name.autoresume"
MAX_WAIT=${AUTORESUME_MAX_WAIT_S:-43200}
note="RESUME NOTE: an earlier run of this same task was stopped by a usage limit or server capacity error. Its partial edits are uncommitted in this worktree (inspect git status/diff and the out/ evidence first); continue from them rather than starting over."
log() { echo "$(date '+%F %T') $*" >> "$A"; }
current="$prompt"
for attempt in 1 2 3 4 5 6; do
  job=$(basename "$current" .txt)
  rm -f "$L/$lane-$job.done"
  (cd ~/archpipe && "$HERE/run_lane.sh" "$lane" "$current") >> "$A" 2>&1
  waited=0
  until [ -f "$L/$lane-$job.done" ]; do
    sleep 60; waited=$((waited+60))
    if [ "$waited" -ge "$MAX_WAIT" ]; then
      log "attempt $attempt timeout after ${MAX_WAIT}s without a done marker; killing session codex-$lane"
      tmux kill-session -t "codex-$lane" 2>/dev/null; exit 2
    fi
    if [ "$waited" -ge 120 ] && ! tmux has-session -t "codex-$lane" 2>/dev/null && [ ! -f "$L/$lane-$job.done" ]; then
      log "attempt $attempt crashed: tmux session codex-$lane vanished without a done marker"; exit 3
    fi
  done
  code=$(sed -n 's/^exit=//p' "$L/$lane-$job.done" | tail -1)
  log "attempt $attempt $(cat "$L/$lane-$job.done")"
  tail_text=$(tail -c 4000 "$L/$lane-$job.log")
  if echo "$tail_text" | grep -q "hit your usage limit"; then
    when=$(echo "$tail_text" | grep -o "try again at [^.]*" | tail -1 | sed 's/try again at //')
    clean=$(echo "$when" | sed -E 's/([0-9])(st|nd|rd|th),/\1,/')
    target=$(date -d "$clean" +%s 2>/dev/null)
    now=$(date +%s); [ -z "$target" ] && target=$((now+3600)); [ "$target" -le "$now" ] && target=$((target+86400))
    log "usage limit; waiting until $(date -d @$((target+300)))"
    sleep $((target+300-now))
  elif echo "$tail_text" | grep -q "at capacity"; then
    log "capacity error; retry in 10 min"; sleep 600
  elif [ "${code:-1}" != "0" ]; then
    log "crashed exit=${code:-unknown} (not a usage or capacity stop); not retrying"; exit "${code:-1}"
  else
    log "finished"; exit 0
  fi
  resumed="${prompt%.txt}-r$attempt.txt"
  { head -1 "$prompt"; echo; echo "$note"; tail -n +2 "$prompt"; } > "$resumed"
  current="$resumed"
done
log "gave up after 6 attempts"; exit 4
