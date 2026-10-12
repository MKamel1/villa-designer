---
name: lighting-proof
description: Verify lighting calculations and Blender render fidelity using real extracted geometry, measured photometric files, and independent probes. Use when changing fixtures, materials, scene conversion, or lighting claims.
---

Read [lighting lessons](../../../docs/LEARNINGS.md),
[calibration decision](../../../docs/decisions/ADR-0010-photometric-render-calibration.md),
and [direct-light limits](../../../docs/decisions/ADR-0009-no-uniformity-verdict-from-direct-light.md).

Use geometry from a fresh saved-model extract. Join photometry to the
explicit specification by stable model identity and reject unmatched
fixtures. A family write that appears successful is not proof its light
definition survived save.

A luminaire's position is its **measured emitter** (`archpipe.fixture_source`:
Light Source symbol apex, else lens centre), and the spec's
`mounting_height` means emitter height. Two consumers agreeing is not
validation when both read the same wrong input: render and lux engine
agreed to 3% while every source sat outside its fitting. Validate each
input against something independent (`check_bedroom.py` measures the
built geometry).

The photometric file must describe the fitting it is attached to:
`make_render_input` warns when the IES opening differs from the lens by
more than x2 in size or x3 in shape (a strip file lit a round drum). A
generic substitution is reported in every render caption until the
specified product replaces it.

Run the analytical report and the independent Blender direct-light probe
on the same input. State maintenance factors, probe height, included
geometry, bounce count and assumed reflectances. Compare direct with
direct. Empty-room calibration does not validate furnished shadows or
total-light uniformity. A numerical mismatch must produce a failed gate.

Task probes must own an exported mesh face, including the actual rim datum
for a sink aperture. Author ownership before mounting, then derive the final
plane from that face after mounting with its explicit reading/grooming
clearance; keep the sensor 1 mm above that plane. Export and measurement
unconditionally refuse hidden metered pixels and solid hits in the local
source approach, naming the task and hit. Blender checks evaluated geometry
before any probe render, so imported assets and cloth cannot hide a sensor
silently. A remote furniture shadow remains legitimate light transport.
Never repair instrumentation by moving furniture or tuning lights/targets.
Run `tests/test_task_probe.py` and the pinned Blender background command
`--python-exit-code 1 --python tests/blender_task_probe.py` for ownership
changes. Lead decision 2026-10-11: when a nominal contact point is covered by
an object resting on its host, `task_probe.resolve_surface_probes` searches
outward on the SAME finite owning face within the cited task area. It uses
a nominal-anchored 5 mm lattice ordered by distance, then signed horizontal
indices; this is instrument sampling resolution, not a design rule. Record
the original obstruction, measured resting-object bounds, all tested offsets,
selected measurement position and offset; keep the nominal target position.
The nearest clear tested point must pass every metered/source path and retain
its meter footprint on that face. An unblocked point stays unchanged. Never
use achieved lux to choose the position. No cited area, an overhead obstacle,
or an exhausted area fails closed; retain its hit and unavailable illuminance.
Test the actual covered point, unchanged clean point and translated host/object
sibling in Python and Blender. Re-measure the complete point set and report
achieved versus target with offsets. A guarded subset remains partial evidence;
the full measurement gate stays failed until every probe is valid.
Freeze every analytic light AND emissive mesh centre from `probe_sources`
for search regressions; an analytic-only fixture omits valid local approaches
and can choose a different clear point from the complete production scene.

Inspect the final image as well as the numbers. Check ceiling, openings,
fixture placement, measured furniture bounds, authored finish hue and
camera framing. Never retouch a simulation with image generation to make
it look correct. Proxies and unmeasured optical properties stay labelled.

Use the configured rendering workstation to keep the laptop's workload
bounded. Use `run_workstation_job` or `scripts/workstation.py` for cached
view batches, probes and independent Radiance jobs; see
[worker operations](../../../docs/ops/workstation-jobs.md). Graphics probes
are the measured default. Re-benchmark after meaningful renderer, hardware
or probe changes; do not rerun a benchmark merely because documentation changed.
Keep execution success distinct from lighting/design acceptance.
Capture a minimal failing input for new photometric bugs, add a
regression, and update the calibration evidence. Do not generalize an
example target into a code-compliance requirement without a verified source.
