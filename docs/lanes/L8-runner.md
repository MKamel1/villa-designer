# L8: the workstation job runner (jobq)

Use this for any GPU or long CPU job on `ai-workstation` so lanes do not collide on the 3090.

## Submit (one command)

```
python scripts/workstation.py submit --gpu --timeout 1800 --id <unique-name> -- <command> [args...]
```

- `--gpu`: the job holds `~/archpipe/locks/graphics.lock` (the same flock the critic/lighting scripts take), and only
  one GPU job runs at a time, in submit order. Without `--gpu` up to 2 jobs run in parallel and no lock is taken.
- `--timeout S` (default 3600): the command and its process group are killed after S seconds of running time
  (waiting for the lock does not count). A timeout is final, not retried.
- `--attempts N` (default 2): how many times a job is started if it dies without a verdict (runner killed, reboot, command
  killed by a signal such as the OOM killer). An ordinary nonzero exit is a verdict (`failed`) and is not retried.
- `--id`: idempotent. Submitting an id that exists returns it unchanged (use this to re-attach after a dropped session).
  `--retry` requeues a `failed`/`timeout`/`died` job. `--wait` blocks until it ends and exits 0 only for `done`.
- `--cwd DIR`: working directory (default: the daemon's home). Give an absolute path; use `sh -c '...'` for pipelines.

Without the laptop helper, on the workstation: `~/archpipe/bin/jobq submit --gpu --timeout 1800 --id X -- cmd args`.

## Where results land

`~/archpipe/queue/jobs/<id>/`

| File | Content |
|---|---|
| `status.json` | `state`, `attempt`, `exit_code`, `reason`, `seconds`, pids (written atomically) |
| `job.log` | stdout+stderr of every attempt, separated by `--- attempt N ---` lines |
| `history.jsonl` | every state change with timestamp |
| `spec.json` | what was submitted |

The job's own outputs go wherever the command writes them. It gets `JOBQ_JOB_DIR` and `JOBQ_JOB_ID` in its environment;
write results under `$JOBQ_JOB_DIR/out/` if you have no better place.
States: `queued -> launching -> waiting_lock -> running -> done | failed | timeout | died | cancelled`.

## Watch

```
ssh ai-workstation '~/archpipe/bin/jobq list'            # all jobs, one line each
ssh ai-workstation '~/archpipe/bin/jobq status <id>'     # full JSON
ssh ai-workstation '~/archpipe/bin/jobq log <id> -n 100'
ssh ai-workstation '~/archpipe/bin/jobq wait <id>'       # blocks; exit 0 only if done
ssh ai-workstation 'systemctl --user status jobq; journalctl --user -u jobq -n 50'
ssh ai-workstation '~/archpipe/bin/jobq cancel <id>'
```

`waiting_lock` for a long time means both slots are held by something outside the queue (a direct `graphics.lock` flock takes only slot 0) (e.g. a script run with
`flock ~/archpipe/locks/graphics.lock ...`); check `fuser -v ~/archpipe/locks/graphics.lock`. Do not delete the lock file.

## For lanes: submit Blender previews with `--gpu`

Waits are short now (two GPU slots, previews overlap each other's CPU phases), so **do not fall back to CPU renders to
dodge the queue**: CPU renders load the 32 threads the test suites need. Submit previews as `--gpu` (add
`--vram-mb 4000` if yours is small). Render **final timing jobs and any timing measurement with `--exclusive`** so
another job does not skew the number. Tools that `flock graphics.lock` directly still work, but they occupy slot 0 only.

## Rules

- Any script of yours that touches the GPU and is not submitted here must itself run under
  `flock ~/archpipe/locks/graphics.lock`.
- `scripts/villa_render.py` now submits its Blender job here (id `villa-<content hash>`), so it takes the GPU lock and
  recovers from a dead runner; `--retry` relaunches a failed/timed-out/died one, `--job-timeout S` (default 6 h) bounds it.
- The service is `systemd --user` `jobq.service`, enabled with linger, so it starts at boot and relaunches jobs that
  died with the machine. Update it with `python scripts/workstation.py install-runner`. Slot counts are in the unit's `ExecStart`
  (`--cpu-slots 4 --gpu-slots 2`). Restarting the daemon never touches running jobs: each runner holds its own flock.
- Broken job dirs are moved, never deleted, into `~/archpipe/quarantine/`.
