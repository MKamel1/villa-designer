# C4 final Linux continuation: CHECKPOINT, uncommitted

2026-10-05. Continued from [package f](c4-phase2f-checkpoint.md), retained
unchanged, and verified the final implementation already present in this
transferred checkout. No commit or full suite. No native rebuild, deployment,
or presentation integration. The lead owns full-suite and render review.

All commands ran from `/home/omar/archpipe/work/laneA`, using
`/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`, `PYTHONPATH=src`,
`NO_COLOR=1`, and a writable `MPLCONFIGDIR=/tmp/archpipe-c4-mpl` where needed.
The virtual environment and shared `assets/user` and `out/villa/round3`
symlinks were not modified. Historical Windows execution claims are not
current Linux evidence.

Model x runs street to garden, model y toward plot east, and model z upward;
coordinates are metres. Movements, widths and clearances below are millimetres.
WC means water closet. The 10 mm margin and movements are lead decisions.

All fourteen revised exterior rows are applied from frozen
[authority](../knowledge/c4-final-approvals.json): east 113, west 177,
north 191 and south 135.660 mm, each carrying trellis, branches and climber;
both grilles move 12 mm onto the exterior face. There are zero pending rows.
South still uses the declared polygon edge with no modeled wall solid;
construction and fixing capacity remain unverified.

Parents' headboard width is **1,980 → 1,586 mm**, symmetric about the unchanged
bed centreline at model x 20.330 m. Its left end is x 19.537 m, 10 mm short
of the full-height wall end at x 19.527 m; its right end is x 21.123 m.
Bed geometry and placement are unchanged.

Both coffee assemblies lift 12 mm as complete bodies, drip trays, spouts and
water tanks. Builder-declared ownership and `attached_assembly.translate`
also carry the hood chimney with its canopy. Five existing final regressions
pass, including parent-only split moves on real frozen coffee/hood parts,
automatic small parent moves, renamed/translated siblings, rigid vertex
displacements and frozen approval drift refusal. The lowest retained assembly
part sits on the modeled worktop; geometry is not flattened to achieve contact.

Linux verification initially failed before review: transferred library rows
contained Windows separators. The added library regression freezes the actual
three product path strings, fails before the fix, and passes after portable
serialization and common row-read normalization. Photometric export and family
folder lookup share that boundary. Temporary proofs preserve index bytes;
the shared library was not rebuilt or rewritten. Code, test, learning index,
guard registry, workflow and synchronized skill adapter were updated together.

The authoritative [portable verify log](../out/c4-final-linux-verify.log) and
[exit](../out/c4-final-linux-verify.exit) report **117 passing checks and exit 1**:
only the bathroom-clearance check fails, with exactly three family-bath rows.

| Family-bath finding | Achieved | Required |
|---|---:|---:|
| WC narrow centreline side | 197 mm | 350 mm |
| WC wide centreline side | 200 mm | 1,000 mm |
| Basin front approach | 0 mm | 1,100 mm |

Working and proposed mounting findings, missing hosts, signed-plane errors,
finite coverage failures, appliance penetrations and unresolved clearance rows
are zero. [Geometry comparison](../out/c4-final/geometry-diff-from-f.json) records
23 changed meshes, zero changed family-bath meshes, unchanged bed meshes and
unchanged cameras. The client's WC-on-east-wall job remains next.

**Remaining verification limits:** plain `scripts/verify.py` also reports
`rfa version reader (1 failures): no installed families found to check the parser
against; the compatibility logic was still tested`; its
[log](../out/c4-final-linux-verify-native-corpus.log) and
[exit 1](../out/c4-final-linux-verify-native-corpus.exit) are retained.
The existing Ubuntu `--portable` mode explicitly skips the Windows installed
family corpus; two focused parser regressions pass separately. The installed
Revit photometry library and downloaded-family screening are also unavailable
and reported as skipped. This is not native-model verification.

The focused render regression still fails
`test_indoor_plants_have_integrated_pots_floor_support_and_clear_tv` on
`lounge-plant`, `living-plant-table`, `living-plant`, `bedroom-plant` and
`study-plant`. Their bases are respectively -2.998, -2.598, -2.998, +0.002 and
+0.002 m; the legacy check expects -3.000, -2.600, -3.000, 0.000 and 0.000 m.
All differ by +2 mm after measured support migration. The
[baseline reproduction](../out/c4-final-linux-indoor-plant-baseline.json) gives
identical findings before and after the final fixes. This known stale-datum
defect remains OPEN; no plant or tolerance was changed.

| Focused command / evidence | Result | Exit |
|---|---|---:|
| `run_focused_tests.py test_final_mounting test_support_mounting test_exterior_mounting test_mounting_scene test_luminaire_library`; [log](../out/c4-final-linux-core.log) | 48 passed, including 37 core mounting tests and 11 library tests | 0 |
| `run_focused_tests.py test_render_standard test_villa_lighting`; [log](../out/c4-final-linux-render-standard.log) | 72 passed, one retained plant-datum test failure; all 18 lighting tests pass | 1 |
| `run_focused_tests.py test_rfa_portable`; [log](../out/c4-final-linux-rfa-portable.log) | 2 passed | 0 |
| `checkpoint_mounting_final.py`; [log](../out/c4-final-linux-checkpoint.log) | Only the three family-bath rows | 1 |
| `verify.py --portable`; [log](../out/c4-final-linux-verify.log) | Only the three family-bath rows | 1 |
| `sync_agent_assets.py --check`; `git diff --check` | Both pass | 0 |

Ignored historical package-e/f outputs were absent on arrival. The diagnostic
baselines were reconstructed by the builder with subsequent approval functions
disabled, not edited by hand. [Recovery recipe](../out/c4-final-linux-reconstruct.py),
[log](../out/c4-final-linux-reconstruction-delivery.log) and package
[f provenance](../out/c4-phase2f/linux-reconstruction.json) explicitly label
them as reconstructed, not old execution evidence. Every final-approval mesh
matches the frozen fixture exactly before corrections. Nine unrelated meshes
have cross-platform last-bit coordinate differences of at most
0.000000000003553 mm, with zero bounding-box differences; the report retains
those differences rather than silently counting them as design changes.
Initial failed-start and reconstruction logs remain retained in `out`.

The [exterior preview](../out/c4-final/approved-exterior-preview.png) and
[assembly preview](../out/c4-final/assembly-first-fix-preview.png) were generated
and visually inspected. Exterior fixing faces, the panel's wall-end gap and
complete coffee contact are visible. These are geometric diagnostics; lead
photoreal review, native coordination and independent lighting proof remain pending.

Render from [the final working candidate](../out/c4-final/working-scene.json).

| Area | Views / additional close-ups |
|---|---|
| Boundary assemblies | v27-north-garden-above, v28-north-garden-below; four fixing-face close-ups, south edge explicitly unverified |
| Headboard | v05-parents-bedroom; left panel/wall end and bed centreline |
| Coffee and hood | v20-kitchen-run, v17-dirty-kitchen; both tray/worktop sections and hood/chimney joint |
| Grilles | Exterior guest-WC and dirty-kitchen close-ups; v17-dirty-kitchen context |
| Earlier C4 television assemblies | v03-street-lounge, v04-study-deck |
| Earlier C4 bars/nook lights | v24-bar-alcove; independent moved-emitter probes |
| Brackets and rails | v31-dressing-hers, v32-dressing-his |
| Stringer and markers | v11-stair-void, v23-gf-gallery, v29-under-stair-store, v30-under-ramp-store |
| Retained WC slides and next client job | v16-guest-wc, v12-ensuite, v15-family-bath |

**STOP: CHECKPOINT. No commit; no full suite.**
