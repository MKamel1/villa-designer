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

Run the analytical report and the independent Blender direct-light probe
on the same input. State maintenance factors, probe height, included
geometry, bounce count and assumed reflectances. Compare direct with
direct. Empty-room calibration does not validate furnished shadows or
total-light uniformity. A numerical mismatch must produce a failed gate.

Inspect the final image as well as the numbers. Check ceiling, openings,
fixture placement, measured furniture bounds, authored finish hue and
camera framing. Never retouch a simulation with image generation to make
it look correct. Proxies and unmeasured optical properties stay labelled.

Use the configured rendering workstation to keep the laptop's workload
bounded. Capture a minimal failing input for new photometric bugs, add a
regression, and update the calibration evidence. Do not generalize an
example target into a code-compliance requirement without a verified source.
