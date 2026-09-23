# Bedroom capability validation

Validated 2026-09-23. This completes the bedroom capability example in the
[full villa roadmap](ROADMAP.md). It does not approve a real villa, site,
design gate, or construction package. The recovered Claude plan is kept
in [its original form](plans/bedroom-approved-original.md).

## Deliverables and evidence

Generated files live under `out/` and are intentionally excluded from
source control. The current machine-readable result is
[`bedroom-acceptance.json`](../out/bedroom-acceptance.json); its content
hashes identify the outputs that were actually checked.

The drawings use A3 paper, measuring 420 by 297 millimetres. Their scale
is 1:50: one unit on paper represents fifty units in the model. PDF means
Portable Document Format.

| Capability | Measured result | Artifact |
|---|---|---|
| Text specification to saved Revit model | Four walls, two openings, six furniture pieces and five lights; 57 checks, zero failures, one disclosed chair-size difference | [Model](../out/revit2027/bedroom.rvt), [read-back log](../out/run-logs/roundtrip.log) |
| Actual geometry review | Room scope passes with a qualitative view advisory; dwelling checks remain explicitly unassessed | [Review](../out/bedroom-review.json) |
| Native Revit drawings | Six sheets: floor plan, reflected ceiling plan, two true elevations, section and three-dimensional cutaway; A3 paper at scale 1:50 | [Drawing PDF](../out/bedroom-native/bedroom-native-views.pdf), [native view report](../out/bedroom-native/views-report.json) |
| Markup transport | Labelled synthetic text and four-sided revision cloud survive saving and extraction | [Extract](../out/bedroom-from-revit.json) |
| Authored finishes | Wall paint, timber floor and plaster ceiling identities/hues survive extraction | [Extract](../out/bedroom-from-revit.json) |
| Lighting example targets | Average about 155 lux; reading points about 380 and 375 lux; three layers | [Lighting report](../out/bedroom-lighting.json) |
| Remote rendering | Blender scene build and graphics-accelerated Cycles render run on `ai-workstation` | [Rendered image](../out/bedroom.png) |
| Independent direct-light comparison | 10,944 sample points; median rendered-to-analytical ratio about 0.971, within the example's five-percent tolerance | [Comparison log](../out/run-logs/photometry_agreement.log) |

Lux is illuminance: light arriving per unit area. The calibration probe
excludes furniture and reflected light. It verifies direct-light
agreement, not furnished-room shadows or lighting uniformity.

The sheets were inspected as images. That caught problems missed by
vector-count checks: note/title overlap, long titles wrapping over scale,
and reversed elevation names. Native paper frames, reserved title spacing,
short display titles and correct direction interpretation address them.

## Reusable system delivered

The [local Model Context Protocol server](MCP.md) exposes seven typed
operations and two shared documentation resources. Its default resume
operation reuses matching recorded inputs and artifacts, and an exclusive
lock prevents simultaneous model writers. Real client/server tests cover
successful calls, negative inputs, and complete cached reuse. A Windows
input-pipe hang was reproduced and fixed; the cached transport regression
now has a 30-second deadline and rejects stale prerequisites.

Three canonical skills and three agent roles cover the villa method,
Revit round-trip work and lighting verification. Claude and Codex use
nine generated adapters from these common sources; the synchronization
check detects drift. [LEARNINGS.md](LEARNINGS.md) records demonstrated
failures and their code, test or workflow consequences. This is maintained
engineering knowledge, not automatic model training.

The project verification suite, ten additional regressions, the real
protocol integration test, skill validation and adapter checks pass.
Project-local assistant connection files are generated; a new session
must load this project configuration. Autodesk Assistant's private server
has not been connected.

To repeat the example from the project directory:

```powershell
.\.venv\Scripts\python.exe scripts/run_bedroom.py --resume
.\.venv\Scripts\python.exe scripts/test_mcp.py --cached-run
```

Omit `--resume` after changing installed applications or remote
photometric assets: these environment dependencies are not yet part of
the cache fingerprint. Preserve manual model edits before using a builder
that regenerates the example.

## Limits and next work

The furniture render uses measured box proxies, including five proxy
objects in Revit. Paint hue is extracted, but optical reflectance is
assumed. Photometry is explicitly joined from the authored specification.
Two lights have disclosed near-field point-source warnings. Door hinge
handedness is not extracted yet, so automated swing checks are provisional.
The markup is synthetic and conveys no client approval.

For reusable infrastructure, the next priority is a versioned workstation
job manifest that fingerprints assets and runtime, followed by resumable
batch jobs and bounded alternative studies. The
[compute-placement table](ops/compute-placement.md) separates current
usage from proposed work. Further design capabilities include exact family
geometry, door handedness, multi-room coordination and independent
reflected-light/daylight simulation. Real villa design still needs the
actual brief, site and client gate decisions.
