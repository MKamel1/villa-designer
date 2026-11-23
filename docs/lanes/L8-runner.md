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

Waits are short now (three GPU slots, previews overlap each other's CPU phases), so **do not fall back to CPU renders to
dodge the queue**: CPU renders load the 32 threads the test suites need. Submit previews as `--gpu` (add
`--vram-mb 4000` if yours is small). Render **final timing jobs and any timing measurement with `--exclusive`** so
another job does not skew the number. Tools that `flock graphics.lock` directly still work, but they occupy slot 0 only.

## Scene build cache (stills): build once, render many

A `villa_scene.py` render first BUILDS the scene (hundreds of glTF imports, cloth) on the CPU: minutes, with a GPU
slot held and idle. `--blend-cache DIR` builds it once and saves a `.blend` that later jobs open instead
(`src/archpipe/blender/scene_cache.py`).

```
CACHE=$HOME/archpipe/cache/scene                       # any shared directory
# 1. build once, as a CPU job (no GPU slot held): exits 0 as soon as the entry exists (or already did)
jobq submit --id RF-build --cwd $LANE -- env ARCHPIPE_BLEND_CACHE_BUILD_ONLY=1 \
    blender -b --python-exit-code 1 -P src/archpipe/blender/villa_scene.py -- <the usual args> --views <any one view> --blend-cache $CACHE
# 2. every render chunk adds the same flag, otherwise unchanged
jobq submit --gpu --id RF-final-0 -- blender -b ... -P src/archpipe/blender/villa_scene.py -- <usual args> --blend-cache $CACHE
```

- Step 1 is optional: a render job with `--blend-cache` that finds no entry builds it itself and stores it. The build
  holds `$CACHE/<key>.lock`, so jobs submitted at the same time wait on the lock, then hit. Start the build job first
  and submit renders after it, so the waiting happens on a CPU slot and not on a GPU slot.
- Key = scene.json sha256 + builder source hash (`src/archpipe/blender/*.py` and `src/archpipe/*.py`) + Blender
  version + library root + IES dir. Edit any of those and the key changes: the old entry is left alone, a new one is
  built. Use the same `--scene`, `--ies-dir`, `--library-root` text in the build and render jobs. Library assets edited
  in place at an unchanged path are NOT detected.
- A hit is verified first (sizes and sha256 of `scene.blend` and `state.pkl`). A bad entry is moved to
  `$CACHE/_refused/` (never deleted) and the scene is rebuilt, so a corrupt cache costs time, never correctness.
- Entries are about 1.2 GB for the production scene; prune old key directories by hand when disk matters.
- Walkthrough chunks: `walkthrough.py` already caches its build as `<root>/assembly/scene.blend` (stage `assembly`)
  and every later stage opens it, so chunks do not rebuild. Do not add `--blend-cache` to them; the env var
  `ARCHPIPE_BLEND_CACHE` only affects the `assembly` stage if you want it to reuse a shared build.
- Measured 2026-11-22 on the production scene (633 MB scene.json, 1.09 GB `.blend` + 96 MB state), one view, 16 spp
  480x320, GPU shared with other lanes' jobs (so absolute numbers are loose): fresh 252.6 s wall, scene ready after
  195.5 s, GPU busy (nvidia-smi pmon, our pid) 17 % of wall; cached 119.3 s wall, scene ready after 70.9 s (of which the
  `.blend` open is 7 s; the rest is parsing scene.json and the receipt), GPU busy 31 %. On CPU, two views: 354 s fresh vs 179 s cached.
  The one-off build job takes about 230 s. A fresh GPU job showed no GPU context at all for its first ~195-228 s.
- Cached and fresh renders are not bit-identical, and neither are two fresh renders (denoised 16 spp, metered
  exposure): mean abs difference per 8-bit pixel was 0.39 / 2.84 (cached vs fresh, two views) against 0.41 / 2.66 (fresh
  vs fresh). The scene receipt is byte-identical and all structural report fields (object counts, lights, cloth, props)
  are equal; only noise-driven fields (metered exposure, log-average) differ, as they do between two fresh runs.
- The cache replaces only the build. Exposure metering, the receipt and the render still run per job.

## Rules

- Any script of yours that touches the GPU and is not submitted here must itself run under
  `flock ~/archpipe/locks/graphics.lock`.
- `scripts/villa_render.py` now submits its Blender job here (id `villa-<content hash>`), so it takes the GPU lock and
  recovers from a dead runner; `--retry` relaunches a failed/timed-out/died one, `--job-timeout S` (default 6 h) bounds it.
- The service is `systemd --user` `jobq.service`, enabled with linger, so it starts at boot and relaunches jobs that
  died with the machine. Update it with `python scripts/workstation.py install-runner`. Slot counts are in the unit's `ExecStart`
  (`--cpu-slots 4 --gpu-slots 3`). Restarting the daemon never touches running jobs: each runner holds its own flock.
- Jobs get `~/opt/blender` and the laneP venv `bin` in front of PATH, so `blender` and `python` as argv[0] resolve.
  A command that cannot be executed (`FileNotFoundError`/`PermissionError`) ends `failed`, reason `exec failed: <error>`,
  at once, with no retry, and frees its slot.
- Broken job dirs are moved, never deleted, into `~/archpipe/quarantine/`.
