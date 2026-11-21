#!/usr/bin/env bash
# usage: lane_queue.sh <lane> <current-job-name> <base-ref> <next-prompt> <next-branch>
# Waits for the lane's current auto_resume job to log "finished", "gave up", "crashed" or "timeout",
# snapshots that job's uncommitted work on its own branch (for lead review),
# then starts <next-prompt> on a new branch from <base-ref> under auto_resume.
# After a crash or timeout it snapshots but does NOT start the next prompt.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
lane="$1"; cur="$2"; base="$3"; prompt="$4"; branch="$5"
L=~/archpipe/logs/lanes; Q="$L/$lane-queue.log"
until grep -q -E "finished|gave up|crashed|timeout" "$L/$lane-$cur.autoresume" 2>/dev/null; do sleep 120; done
cd ~/archpipe/work/"$lane" || exit 1
last=$(tail -1 "$L/$lane-$cur.autoresume")
echo "$(date '+%F %T') $cur ended: $last" >> "$Q"
if [ -n "$(git status --porcelain)" ]; then
  git add -A && git commit -q -m "lead-queue snapshot: $cur result (unreviewed; lead reviews before merge)" >> "$Q" 2>&1
  echo "$(date '+%F %T') snapshot $(git rev-parse --short HEAD) on $(git branch --show-current)" >> "$Q"
fi
case "$last" in
  *crashed*|*timeout*) echo "$(date '+%F %T') not starting the next prompt after a crash or timeout" >> "$Q"; exit 1;;
esac
git checkout -q -b "$branch" "$base" >> "$Q" 2>&1 || { echo "$(date '+%F %T') branch failed" >> "$Q"; exit 1; }
echo "$(date '+%F %T') starting $(basename "$prompt") on $branch from $base" >> "$Q"
cd ~/archpipe && exec "$HERE/auto_resume.sh" "$lane" "$prompt"
