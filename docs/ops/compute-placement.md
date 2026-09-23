# Compute placement

Measured 2026-09-22: Ubuntu host `ai-workstation`, 32 processor threads,
91 GiB system memory reported by Linux, NVIDIA RTX 3090 with 24 GiB
graphics memory, Blender 4.2.9. GiB means gibibytes, units of binary memory
capacity. Revit stays on the Windows laptop by client decision.

| Operation | Current location | Intended placement |
|---|---|---|
| Procedural Blender scene build | Ubuntu | Ubuntu |
| Cycles image render | Ubuntu, RTX 3090 through NVIDIA OptiX | Ubuntu; batch views and higher-quality final runs |
| Blender illuminance probe | Ubuntu, currently processor rendering | Ubuntu; benchmark graphics acceleration only if probe workload warrants it |
| Direct-light numerical grid/heat map | Laptop | Both; quick local checks, larger grids/batches remotely |
| Geometry/rule engine | Laptop | Both; fast local feedback and whole-villa remote batches |
| Regression suite | Laptop | Add an independent Ubuntu environment/test run |
| Alternatives and parameter sweeps | No batch runner yet | Ubuntu with bounded workers, cached inputs, and a job queue |
| Radiance | Not installed (`rtrace` and `oconv` absent from PATH) | Ubuntu when added; independent reflected-light/daylight studies |
| Native Revit authoring, extract, drawings, markup | Windows laptop | Keep local |
| Shared skills, roles, tools and evidence | Versioned project on laptop | Same versioned project deployed with reproducible remote worker |

Latest measured render (2026-09-23): 1280 by 800 pixels, 512 samples, 12.31 seconds
for the render/save stage, excluding startup and transfer. The scene used
roughly 736 MB of graphics render memory according to Blender's log; this
is a small proxy scene, not a benchmark for a detailed villa.

The current coordinator is `scripts/run_bedroom.py`, with two remote
jobs in `~/archpipe/bedroom-e2e`. Assets already present in
`~/archpipe/ies` are dependencies, not installed by this run. Transferred
scene scripts and extract are generated job inputs. No system-wide
Ubuntu changes were made in this continuation.

Next infrastructure work: a user-space, reproducible Python environment,
versioned worker deployment, job manifest with dependency hashes,
structured results, resumable jobs and bounded resource use. Keep quick
checks local where network/startup cost exceeds compute savings. Test
the Ubuntu path rather than declaring portability from Python syntax.

Radiance's intended role is independent physical lighting prediction,
including direct and indirect components; see its
[official description](https://www.radiance-online.org/about/detailed-description.html).
