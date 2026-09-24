# Reusable Ubuntu jobs

`scripts/workstation.py` deploys source to `ai-workstation`, submits bounded
jobs, verifies cached artifacts and downloads one result bundle. It is
also exposed through the `run_workstation_job` Model Context Protocol
(MCP) operation. Revit authoring remains on Windows.

## Commands

Run from the project with `.venv/Scripts/python.exe` on Windows:

```text
scripts/workstation.py setup
scripts/workstation.py status
scripts/workstation.py verify
scripts/workstation.py benchmark
scripts/workstation.py sweep
scripts/workstation.py batch --samples 512 --resolution 1600x1000
scripts/workstation.py radiance
scripts/workstation.py bedroom --samples 512
```

`setup` installs pinned Python dependencies and twelve headless Radiance
tools under the user's `~/archpipe` directory. It does not need system
package changes. The official Radiance 6.0 patch 1 source archive is pinned
by its measured download checksum. Its upstream headless build still
attempts an OpenGL helper, so the installer builds named command-line
targets; it does not install an interactive Radiance viewer.

`verify` runs portable project tests, synthetic family-version parser
tests, and recorded geometry fixtures. It explicitly excludes the
installed native family corpus, which remains verified on Windows.
Automatic approval review rejected native family transfer; the deployment
now admits selected text source formats and photometric text only.

`sweep` evaluates five dimming levels and five bed-placement candidates
without editing the saved extract or authoring model. A successfully
executed candidate may fail design review. Reports distinguish execution
success from design acceptance; none automatically becomes approved work.

`batch` renders bed, window and overview cameras. `bedroom` additionally
runs the independent direct-light probe and Radiance studies. The main
`run_bedroom.py` coordinator uses this operation after local Revit work.

## Evidence and recovery

Source releases have content fingerprints. Each job identifies its code,
model, parameters, photometric assets, Python packages, Blender executable,
graphics driver and Radiance executables. Documentation changes do not
discard an otherwise identical render. A cached result is reused only if
the successful result's output files still match their recorded hashes.

Every retry writes a fresh attempt directory. Failed attempts retain their
logs and are never reused. Operating-system file locks serialize matching
jobs and release automatically if a worker dies. A separate graphics lock
allows one graphics render at a time; batches use at most four workers and
each numerical process at most eight processor threads. Benchmark trials
run sequentially to avoid resource contention corrupting the comparison.

This is a bounded submitted batch runner, not a permanently running queue
service. Rerun the same command after interruption: completed jobs reuse
their evidence and unfinished jobs retry. Persistent scheduling across
multiple users would require an additional service and retention policy.

Local reports are under `out/workstation/<operation>-latest.json`; bundles
are under `out/workstation/<batch identifier>/`. Large linear probe images
stay on Ubuntu; numerical readings, diagnostic logs and display renders
are downloaded. Commands and MCP return compact summaries with those paths
instead of repeating full manifests in an assistant's context.

## Measured device choice

Measured 2026-09-23 using Blender 4.2.9 and the RTX 3090, three isolated
trials per device. Times include Blender startup and the complete probe
process, but exclude source deployment and result transfer.

| Probe | Processor median | Graphics median | Speed improvement |
|---|---:|---:|---:|
| 128 by 128 pixels, direct light | 1.315 seconds | 0.665 seconds | 1.98 times |
| 256 by 256 pixels, sixteen diffuse bounces | 10.725 seconds | 1.516 seconds | 7.08 times |

Average illuminance differs by less than 0.001 percent between devices.
Routine probes therefore use graphics acceleration. The processor path
remains available in the benchmark and as an independent implementation
check. These small-room measurements do not predict whole-villa timings.

Primary references: [Radiance distribution](https://www.radiance-online.org/download-install/radiance-source-code/latest-release),
[IES conversion](https://radsite.lbl.gov/radiance/man_html/ies2rad.1.html),
[ray tracing](https://radsite.lbl.gov/radiance/man_html/rtrace.1.html).
