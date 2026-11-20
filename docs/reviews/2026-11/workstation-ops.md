# R4: workstation operations review (ai-workstation:~/archpipe, read-only, 2026-11-20)

## Findings, most severe first

**S1. Nothing on the workstation is backed up, and it all sits on one 3.6 TB NVMe** (`/dev/nvme0n1p2`, 86 % used). There is no crontab and no backup timer; the only one is `dpkg-db-backup`. `rclone` is installed but nothing uses it. Git is safe: all five workstation branches not merged into main exist on GitHub at identical SHAs. The one exception is `tmp/reg13-check`, which is absent from GitHub. The lane clones have 0 commits that are not on the bare repo. The irreplaceable non-git data is small (table below).

**S2. Three execution paths exist, and only the dormant one is documented.**
- `scripts/workstation.py` → `worker_entry.py` → `worker.cached_job` (`jobs/`). This path has content-addressed jobs, flock, fresh attempts and hash-verified reuse. It is well built but has not run since 2026-09-24: all 83 jobs date from Sep 23–24, and the last 13 releases date from Oct 5–15.
- `scripts/villa_render.py` (`villa-render/`, Sep 27 – Oct 15) launches Blender with `setsid nohup` under a content identity. Of 87 jobs, 79 exited 0, 4 failed ("Blender quit") and 2 have no status file (`af7b251c…`, `fd37f177…`). The launch guard `test -f status || (test -f pid || launch)` means a dead pid with no status is never relaunched. Those 2 jobs are permanently wedged until someone deletes the folder by hand.
- Codex lanes (`run_lane.sh`, `auto_resume.sh`, `lane_queue.sh`, `dispatch.sh`, all in tmux) did most of the October work. Only 3 scripts (`blender52_eval.py`, `blender52_speed_driver.py`, `check_bed_import.py`) take `locks/graphics.lock`. `villa_render.py` and the lane renders do not, so two lanes plus a villa render can share the 24 GB GPU. Other tenants share it too: ace-step was compiling torch while I looked. `docs/ops/workstation-jobs.md` describes only the first path.

**S3. `auto_resume.sh` is a single-shot babysitter and cannot survive a reboot.**
- All 43 nonzero `.done` markers are Codex quota or capacity stops (`logs/lanes/*.log` tails), and there were 21 usage-limit waits. The headline failure is Codex quota, not the pipeline.
- Any other ending, a crash included, is logged as "finished".
- `until [ -f done ]` has no timeout.
- Everything runs inside tmux. There was no tmux server after the Nov 13 boot, and nothing restarts it.
- `walk2` hit "gave up after 6 attempts" (2026-10-22, about 20 h of waiting). It left 64 dirty files in `work/laneA`; laneB still has 8. They are snapshotted to the `backup/*-wip-2026-11-20` branches but the trees are still dirty.
- `dispatch.sh` is a one-off: it hard-codes `integ-6`, drape/repro, and tmux kills.

**S4. Ops code lives outside the repo.** The root scripts, `bin/ssh` (a shim that makes `ssh ai-workstation` local), `worker-environment.json` (written by bootstrap but also hand-edited for thermal and Blender), `prompts/` (600 K, the Codex task prompts, i.e. provenance), and `work/laneA/out/flythrough/final-queue.py` (production code in a gitignored `out/`) are all untracked.

**S5. Reproducibility is partial.** This is good:
- Worker and thermal Python are `==`-pinned, with environments keyed by the SHA of the requirements file.
- Radiance 6.0.1 and OpenStudio 3.11.0 are SHA-pinned in `ops/workstation/bootstrap.py`.
- Blender 4.5.14 is pinned with a checksum in `10-blender.sh`, and the job runtime records the Blender SHA, the driver version and the Radiance binaries.

These are not rebuildable from the repo:
- **trellis2** (21 G: CUDA 12.4 plus a custom CuMesh build). Its `bootstrap_trellis2.sh` exists only on `backup/trellis-wip`.
- **Blender 5.2.2**, which was installed by hand.
- **The blender-mcp venv.**
- **The Codex CLI version.** The model `gpt-6.1-sol` is hard-coded in `run_lane.sh`.
- **System build dependencies** (cmake, compilers).

Two more risks:
- The Radiance URL is `latest-release`, so a rebuild will fail closed on a SHA mismatch once upstream moves. Only `downloads/rad6R0P1.tar.gz` (41 M) keeps a copy.
- `~/opt/blender` is a symlink, so re-pointing it changes the renderer silently. It is recorded, but not refused.

**S6. Disk hygiene.** `work/` is 118 G, of which `laneA/out` is 97 G: `walk2/production…production8` total about 34 G of superseded runs, and the flythrough `failed-*`/`superseded-*`/`diagnosis` dirs about 10.5 G. `laneB/out` is 19 G and `villa-render/` 19 G. Nothing prunes `releases/` (169 dirs) or rotates the lane logs, and `envs/3d2ecd4e…` is orphaned. Roughly 70–90 G is reclaimable.

**Not found:** no OOM evidence (the journal starts at the Nov 13 boot; the trellis "Killed" is Codex grep text), and no stuck locks (the lock files are flock files, so their presence does not mean they are held).

## Q4: Are four lanes worth it?

Not at the current scale. Between Sep 21 and Oct 16 the work needed 10 integration branches and 42 merges in laneM. It also needed bespoke conflict tooling: `union_json.py` for LEARNINGS lessons and `patch_release.py`.

Because work is bounded by Codex quota (43/43 stops), two concurrent lanes split one quota rather than adding throughput. laneR is a stale duplicate of laneM: same local branches, last commit integ-9. Each clone carries its own `out/`, which is where 118 G came from. The lanes have also been idle since Oct 22.

Recommendation:
- Use one integration clone, plus at most one `git worktree` agent lane that shares its object store.
- Point `out/` at a shared content-addressed render store.
- Have every GPU-using script take `graphics.lock`.
- Run lanes under `systemd --user` units instead of tmux.

## Q5: Move into the repo (`ops/workstation/`)

`run_lane.sh`, `auto_resume.sh` (fixing the "finished"-on-crash bug and adding a timeout), `lane_queue.sh`, `run_tests_ws.sh`, `bin/ssh`, `union_json.py` (as a git merge driver), a `worker-environment.json` template, `bootstrap_trellis2.sh`, `final-queue.py` → `scripts/`, and `prompts/` → `docs/ops/prompts/`. Delete `dispatch.sh` and `patch_release.py`: their effect is already merged into `scripts/workstation.py`.

## Data inventory and backup table

| Dir | Size | Class | Note |
|---|---|---|---|
| library/fab | 12 G | **a** | Fab account downloads (2K/4K zips plus json); re-download needs the account; licence-bound |
| library/sketchfab | 14 G | **a-** | CC-BY, with meta.json and uids.txt; `ops/workstation/fetch_sketchfab.py` can re-fetch, but authors can delete models |
| assets/library | 2.5 G | **a-** | Curated, measured, scale-fixed intake the pipeline reads (`ARCHPIPE_ASSET_LIBRARY`) |
| data/assets/user (luminaires) | 0.23 G | **a** | Manufacturer IES and catalogue sqlite; laptop copy at `arch-pipeline/assets/user/luminaires` |
| prompts, root *.sh/*.py, bin, worker-environment.json, final-queue.py | <1 M | **a** | Untracked ops code and provenance |
| logs/lanes | 232 M (~30 M compressed) | a- | Only record of the agent runs |
| library/cubicasa5k, swiss-dwellings | 11 G + 3.4 G | b | Public datasets with md5; calibration results already in `knowledge/precedents/` |
| library/ambientcg, polyhaven | 4.4 G + 0.9 G | b | CC0; `library-manifest.json` |
| tools/trellis2 | 21 G | b* | 12 G of HF weights; rebuildable only once the bootstrap is committed |
| tools/openstudio, radiance; downloads; build; envs | 1.3 G, 5 M; 0.4 G; 0.15 G; 1.1 G | b | SHA-pinned bootstrap (back up the Radiance tarball, 41 M) |
| tools/blender-mcp | 0.5 G | b* | No tracked installer |
| villa-render, daylight, thermal, products, data/out, batches, jobs, inputs | 19, 2.2, 0.65, 0.22, 0.53, 0.08, 0.15, 0.22 G | b | Outputs; finals are on the laptop (`out/villa/finals-2026-10-15/`) |
| releases, git | 1.2 G, 0.13 G | b | Rebuilt from git, which is on GitHub at identical SHAs |
| work/laneA+B out (finals excepted), laneR | ~115 G | c/b | Superseded productions and failed runs; walkthrough finals already on the laptop |
| inbox | 1 G | c | Candidate downloads that were triaged |
| scene, cal, bedroom-e2e, scratch, ies | 80 M | c | Prototypes; the code now lives in `src/archpipe/blender/` |
| weather | 9 M | b | Source on the laptop in `archpipe-sources/cairo-epw` |

**Offsite backup:** fab, sketchfab, assets/library, data/assets/user, prompts plus the ops scripts, compressed lane logs, and the Radiance tarball. That is **≈29 GB**. The minimum without sketchfab is about **15 GB**.

A nightly `rclone`/restic job in a systemd timer (rclone is already installed) is enough. The `b*` items become regenerable only after their bootstraps are committed.
