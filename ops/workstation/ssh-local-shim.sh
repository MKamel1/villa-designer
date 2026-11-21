#!/usr/bin/env bash
# Local stand-in for `ssh ai-workstation <command>` when the render driver runs
# on the workstation itself; any other host goes to the real ssh.
args=("$@"); i=0
while [ $i -lt ${#args[@]} ]; do
  case "${args[$i]}" in
    -o|-p|-i|-l|-F) i=$((i+2));;
    -*) i=$((i+1));;
    *) break;;
  esac
done
if [ "${args[$i]:-}" = "ai-workstation" ]; then
  cd "$HOME"
  exec bash -c "${args[*]:$((i+1))}"
fi
exec /usr/bin/ssh "$@"
