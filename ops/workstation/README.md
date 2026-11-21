# ops/workstation: runner and ops scripts for ai-workstation

Everything here was either loose in `~/archpipe/` on the workstation (untracked) or new in lane L8.
Review of origin: `docs/reviews/2026-11/workstation-ops.md`.

| File | What it is | Deployed to |
|---|---|---|
| `jobq.py` | The job queue and runner (stdlib only). GPU jobs take `~/archpipe/locks/graphics.lock`. | `~/archpipe/bin/jobq` |
| `systemd/jobq.service` | systemd user service running `jobq daemon` (restarts, survives reboot; linger is on) | `~/.config/systemd/user/` |
| `install_jobq.sh` | Idempotent install of the two above. `python scripts/workstation.py install-runner` does it from the laptop | |
| `run_lane.sh`, `auto_resume.sh`, `lane_queue.sh` | Codex lane runner (tmux), quota/capacity resume loop, lane chaining. `auto_resume.sh` now reports crashes as `crashed` (not `finished`), times out, and notices a vanished tmux session | `~/archpipe/` (call by repo path) |
| `run_tests_ws.sh` | Full suite plus verify in a detached tmux session | |
| `ssh-local-shim.sh` | Install as `~/archpipe/bin/ssh`: makes `ssh ai-workstation cmd` run locally when a render driver runs on the workstation | `~/archpipe/bin/ssh` |
| `union_json.py` | Union-merge LEARNINGS-style JSON by `lesson_id`; usable as a git merge driver (see its docstring) | |
| `worker-environment.template.json` | Shape of `~/archpipe/worker-environment.json` (bootstrap writes the real one; thermal and Blender entries get hand-edited) | |
| `final-queue.py` | Reference copy of the laneA flythrough final queue (was in a gitignored `out/`). Hard-coded laneA paths | |

Not repoed on purpose: `dispatch.sh` and `patch_release.py` (one-offs already merged into `scripts/workstation.py`).
Not yet repoed (outside what L8 can write, or not in the shipped scope): `prompts/` (600 K of Codex task prompts, belongs
in `docs/ops/prompts/`), `bootstrap_trellis2.sh` (only on `backup/trellis-wip`).

## jobq in short

```
python scripts/workstation.py submit --gpu --timeout 1800 --id my-job -- <command> [args]   # prints the job id
ssh ai-workstation '~/archpipe/bin/jobq status my-job'      # state, attempt, exit code
ssh ai-workstation '~/archpipe/bin/jobq log my-job -n 50'   # tail of the output
```

See `docs/lanes/L8-runner.md` for states, rules and recovery. Local logic tests: `python -m unittest discover -s tests/ops`.

## Deploying changes to the runner

`python scripts/workstation.py install-runner` copies `jobq.py` over `~/archpipe/bin/jobq` and restarts the service.
Running jobs are not killed by the restart (`KillMode=process`); the new daemon re-adopts them.
