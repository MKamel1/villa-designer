# Compute placement

Measured 2026-09-22: Ubuntu host `ai-workstation`, 32 processor threads,
91 GiB system memory reported by Linux, NVIDIA RTX 3090 with 24 GiB
graphics memory, Blender 4.2.9. GiB means gibibytes, units of binary memory
capacity. Revit stays on the Windows laptop by client decision.

| Operation | Current location | Intended placement |
|---|---|---|
| Procedural Blender scene build | Ubuntu | Ubuntu |
| Cycles image render | Ubuntu, RTX 3090 through NVIDIA OptiX; three named views | Keep final renders and batch views remote |
| Blender illuminance probe | Ubuntu graphics processor; processor mode retained for comparison | Graphics acceleration verified for both direct and reflected probes |
| Direct-light numerical grid/heat map | Quick checks on Windows; dense candidate grids on Ubuntu | Keep immediate feedback local and larger batches remote |
| Geometry/rule engine | Windows and bounded Ubuntu candidate sweeps | Whole-villa batches can reuse the same worker interface |
| Regression suite | Windows plus pinned Ubuntu Python environment | Native Revit family corpus stays on Windows; portable and synthetic tests run on both |
| Alternatives and parameter sweeps | Ubuntu, bounded workers and content-verified caching | Submitted batches supported; persistent service scheduling remains future work |
| Radiance | Headless 6.0 patch 1 installed under the Ubuntu user's directory | Independent reflected-light/daylight adapter under integration; installation alone is not simulation validation |
| Native Revit authoring, extract, drawings, markup | Windows laptop | Keep local |
| Shared skills, roles, tools and evidence | Versioned project deployed as hashed source releases | Shared command-line and Model Context Protocol operations |

Latest measured render (2026-09-23): 1280 by 800 pixels, 512 samples, 12.31 seconds
for the render/save stage, excluding startup and transfer. The scene used
roughly 736 MB of graphics render memory according to Blender's log; this
is a small proxy scene, not a benchmark for a detailed villa.

The coordinator `scripts/run_bedroom.py` uses versioned jobs through
`scripts/workstation.py`. Setup installs a pinned Python environment and
the Radiance command-line subset under `~/archpipe`; no system-wide
Ubuntu changes are required. Source, runtime, photometry and output hashes
govern reuse. See [worker operations and measured benchmarks](workstation-jobs.md).

Three repeated probe trials measured median processor/graphics times of
1.315/0.665 seconds for direct light and 10.725/1.516 seconds for sixteen
bounces. These include Blender startup but exclude network transfer.
Mean illuminance differed by less than 0.001 percent. A repeated view
batch reused all three renders. Keep quick local checks where network
cost exceeds compute savings.

Radiance's intended role is independent physical lighting prediction,
including direct and indirect components; see its
[official description](https://www.radiance-online.org/about/detailed-description.html).
