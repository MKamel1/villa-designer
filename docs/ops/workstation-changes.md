# ai-workstation — change log

Every change to the workstation is scripted in `ops/workstation/` and
recorded here: what changed, when, why, and **how to undo it**. The
machine should be rebuildable from this repo rather than from anyone's
shell history.

Rules we work to:

- Scripted, not typed. One script per concern, idempotent.
- No sudo unless it is genuinely required, and say so when it is.
- Nothing installed outside a package manager without noting where it went.
- Ask before anything destructive or system-wide.

---

## 2026-09-22 — Blender 4.2.9 LTS

**Script:** `ops/workstation/10-blender.sh`
**Changed:** unpacked the official upstream tarball to
`~/opt/blender-4.2.9-linux-x64`, with `~/opt/blender` symlinked to it.
**Sudo:** none.
**Undo:** `rm -rf ~/opt/blender-4.2.9-linux-x64 ~/opt/blender`

**Why this way.** Sudo on this machine requires a password, which would
hang a non-interactive SSH session. The upstream tarball needs no
elevation, pins an exact version, and removes with one command. Snap and
apt were both considered: apt ships 4.0.2, and neither pins as precisely.

**Why pinned.** The scene builder uses Blender's `bpy` API, which changes
between releases. If the laptop and the workstation ever run different
Blenders, the same script produces different scenes and nothing errors —
the worst kind of difference. 4.2 LTS gives a long-supported stable API.

**Verified:**
- `Blender 4.2.9 LTS`, bundled Python 3.11.7
- Cycles backends available: `CUDA`, `OPTIX`, `HIP`, `ONEAPI`
- Devices seen: `NVIDIA GeForce RTX 3090` (both CUDA and OPTIX) and the
  `AMD Ryzen 9 9950X`
- Headless render on OptiX succeeded

**Not verified:** the download had no published `.sha256` at the expected
URL, so integrity was not checked. The script says so rather than
implying it verified.

**Benchmark** (test extract, 512 samples, 1280×720):

| Device | Wall time |
|---|---|
| OptiX, RTX 3090 | **2.13 s** |
| CPU, 9950X (32 threads) | 4.90 s |

Only 2.3×, and that understates it: this scene is five objects and
Blender's ~1.5 s startup dominates. Expect a much wider gap on a
furnished, glazed interior with real light bounces.

---

## Current continuation (2026-09-23)

The bedroom now runs its scene build, graphics-accelerated render, and
independent direct-light probe on this host. See
[compute placement](compute-placement.md) for measured results and the
current versus intended responsibilities. This continuation deployed job
scripts and inputs only under the user's `~/archpipe/bedroom-e2e` directory;
it made no system-wide Ubuntu changes.

## Pending / considered but not done

- **Radiance** — not in apt (`Candidate: (none)`). Will need a source
  build when lighting simulation starts; it should go in `/opt` with its
  own script, not scattered.
- **GPU passthrough / vfio** — a Windows VM was set up and later stopped.
  The RTX 3090 is now back on the `nvidia` driver and free. Nothing in
  this repo depends on that configuration, and nothing here re-creates
  it.
