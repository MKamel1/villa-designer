# L6b villa lighting design

Branch `lane/L6b`. Code: `src/archpipe/lightcalc/villa*.py`, design `src/archpipe/concept/villa_lighting.py`, kinds
`src/archpipe/fixture_record.py`. Data: `knowledge/lighting/` (`zones-d1.json`, `zone-drivers.json`, `villa-before-rows.json`,
`villa-after-rows.json`, `villa-table.md`, `truth/`, frozen IES and `products-frozen.json`). Checks: `out/checks/L6.json`
(copy `knowledge/lighting/checks/L6.json`). Tests: `tests/lightcalc/test_villa.py`, `test_truth_probe.py`.
All calculation ran on `ai-workstation` (Radiance 6.0.1, Python venv `laneP-venv`).

## 1. The truth question: 963 lx (engine) vs 405 lx (Cycles probe) at the D1 dining-table centre

**Answer: the engine is right and the recorded probe is the vase-obstructed reading. They measured different things at the same
coordinates.**

Method: a minimal Cycles scene (`knowledge/lighting/truth/truth_probe_blender.py`, Blender 4.5.14 on the workstation) that reuses the
production light constructor (`villa_scene.add_light`: IES node, `IES_POINT_POWER`, aim) and the production sensor method
(0.5-reflectance 4 cm plane 1 mm over the point, 20 mm ortho camera, 0 bounces, radiance x pi / 0.5), MF 0.8, with the lights
and meshes of the job that produced the recorded file (`834db2128a44f9b196d3e5bd`, Sep 28).

| variant | centre (16.95, -25.9) | table end (16.35, -25.9) |
|---|---|---|
| A. the two crossed adjustable spots, open table | **952** | 218 |
| B. spots + the emissive pendant | 1295 | 468 |
| C. spots + pendant + `dining-vase` on the sensor | **403** | 460 |
| D. spots + vase | 0 | 218 |
| E. pendant only | 343 | 251 |
| F. pendant + vase, no spots | 403 | 243 |
| G. vase only | 0 | 0 |
| recorded `lighting-measurements.json` | **405** | 467 |

* Engine side: analytic direct 939 lx at the emitter datum z = -0.30 and 952 lx at the rendered z = -0.33 (the 1.3 % is the 30 mm
  datum). Variant A (Cycles) equals it to 1.5 % at both points. The engine's 963 lx is **total** light (Radiance ab 6, closed walls: 939 direct + 24
  indirect, `L6-dining-result.json`), not direct. This rules out aiming, IES azimuth, lamp scaling, MF, units and the B = -3000 / -1800 datum
  (both sides use -3.0).
* Probe side: variant C reproduces the recorded file to 0.7 % and 1.4 %. The Sep 28 run therefore read spots + the emissive pendant with
  the vase (0.20 m wide, 0.40 m tall, open mouth) standing on the centre sensor: D shows the vase removes all spot light, and C and F read the
  same 403 lx, so what reaches the sensor is pendant light (the camera is probably metering the vase interior; unconfirmed mechanism).
* "The probe was moved off the vase" is **false for that file**: its points carry no `measurement_position` and the resolver
  (`task_probe.resolve_surface_probes`) is newer. The recorded numbers are an obstructed reading, not a relocated one.
* Not in this lane, **finding for the render lane**: `out/villa/render-d1/lighting-measurements.json` is stale (Sep 28; `scene.json` is Oct 7, and
  its fixtures and probe points differ from it); in the Oct 7 scene the table top is at z = -2.248, so a probe at plane -2.25 + 1 mm sits below the surface
  and the measurement needs a re-run with the task-probe binding. Do not quote its dining numbers.
* In this lane (fixed): `dining.py` "built" omitted the emissive pendant that the render emits (343 lx at the centre); a `render` variant (spots +
  Lambertian pendant) was added. The model's pendant (generic cos^n 90 deg) gave about 464 lx at the centre, 35 % more than the rendered Lambertian
  strip; the villa harness models the pendant as Lambertian.
* Tests: `tests/lightcalc/test_truth_probe.py` (frozen Cycles variants vs the analytic engine and the recorded file).

## CONTINUE HERE (state at the end of the first L6b session)

Done and committed: truth question (section 1); harness; design changes; LA6, LA8, LA9, LA13, LA10 (completeness, night level), LA4 luminance and
LA12 (exterior: the 4 garden uplights fail ULR 1.0 vs 0.15) checks, all reported by `python -m archpipe.lightcalc.villa_probe`; tests
`tests/lightcalc/test_villa.py` (16 pass).
NOT done: the tuned after-state Radiance run, `zones-d1.json`, `out/checks/L6.json` for the villa, the per-room before->after table, the sections under "Still to write".

Workstation (`ssh ai-workstation`), checkout `~/archpipe/work/L6b` (deployed from this branch; venv `~/archpipe/envs/laneP-venv`).
Radiance outputs to REUSE, not recompute (do not delete):

| tag | path | content |
|---|---|---|
| before | `~/archpipe/scratch/L6/before-<cluster>/`; frozen rows `knowledge/lighting/villa-before-rows.json` | the committed-design baseline (13 clusters) |
| iter1 | `~/archpipe/scratch/L6/iter1-<cluster>/`; `~/archpipe/work/L6b/out/L6b/iter1/<cluster>.json` | first redesign, all drivers 1 |
| iter2 | `~/archpipe/work/L6b/out/L6b/iter2/<cluster>/` and `<cluster>.json` | drivers from iter1 for the stable zones |
| iter3 | `~/archpipe/work/L6b/out/L6b/iter3/<cluster>/` and `<cluster>.json` (11 of 13 cluster JSONs existed at hand-off; the detached run was still finishing; log `~/archpipe/work/L6b/out_iter3.log`) | current structure + `zone-drivers.json` from iter2 |

Each `<cluster>.json` holds the per-zone, per-plane Radiance results (MF 1.0, linear in zone level); each `<cluster>/` directory holds the rtrace outputs
(`out_<zone>_ab6.txt`). They were computed with the design and `zone-drivers.json` of the commit deployed at the time (iter3 = this branch at
"L6b: iteration 3 inputs"). Later commits changed only checks, tests and the hemisphere photometry of the sconces (about 4 % less flux), which the final run includes.

Commands (on the workstation, from `~/archpipe/work/L6b`; first deploy from the worktree with
`git -c core.autocrlf=false archive HEAD | ssh ai-workstation 'tar -x -C ~/archpipe/work/L6b'`):

```
source ~/archpipe/envs/laneP-venv/bin/activate
export ARCHPIPE_L6_LOCAL=1 PATH=$HOME/archpipe/tools/radiance-6.0.1/bin:$PATH RADHOME=$HOME/archpipe/tools/radiance-6.0.1
# 1. complete iter3 (13 cluster JSONs); --reuse re-reads clusters whose outputs exist
PYTHONPATH=src python -m archpipe.lightcalc.villa_run --tag iter3 --out out/L6b --fast --reuse
# 2. solve drivers (relative to the applied ones); prints residuals per plane and the Dinner level for the table pendant
PYTHONPATH=src python -m archpipe.lightcalc.villa_tune_cli --tag iter3 --write
#    put the printed Dinner level into SCENES["B-open"]["Dinner"]["table-pendant"] (concept/villa_lighting.py)
# 3. any plane still outside +/-10 % (expect study desks, island prep): rerun the changed design as a new tag, solve again, repeat
PYTHONPATH=src python -m archpipe.lightcalc.villa_run --tag iter4 --out out/L6b --fast
PYTHONPATH=src python -m archpipe.lightcalc.villa_tune_cli --tag iter4 --write
# 4. final run WITH ab 12 (convergence), then publish
PYTHONPATH=src python -m archpipe.lightcalc.villa_run --tag after --out out/L6b
PYTHONPATH=src python -m archpipe.lightcalc.villa_emit --tag after
PYTHONPATH=src python -m pytest tests/lightcalc -q
```

`villa_emit` writes `knowledge/lighting/zones-d1.json`, `villa-after-rows.json`, `villa-table.md` and `out/checks/L6.json` (copy to `knowledge/lighting/checks/L6.json`).
Long runs: `setsid nohup ... &` or jobq (docs/lanes/L8-runner.md); a full run took 15 to 25 minutes. Then copy results back to the worktree with scp, paste
`villa-table.md` into this doc, write the sections below, delete scratch files (`scratch_*.py`, `patch*.py`, `scratch_data/`, `out_cases*.json`) and the `assets`
junction in the worktree, and run `python scripts/lane_guard.py L6b` (must print clean).

Still to write in this doc: per-room table (from `villa-table.md`); changes made (DL instead of DLN, the dining/island/parents' cuts, zones, drivers, scenes,
LA9 snap, route lights, kinds and CCT policy); scenes table (`SCENES`); exterior proposal (down-only shielded path, step and terrace lights at ULR 0, shield or replace the
tree uplights, curfew dimming, an exterior Radiance grid for boundary Ev); limits (no furniture or door shadows in Radiance, the open basement is one closed volume,
reflectances 0.80/0.85/0.33 ASSUMED, linear dimming, drivers are commissioning settings, zones needing a driver below about 0.35 reflect that the library has no
lower-output recessed product); and the finding for the render lane (stale `lighting-measurements.json`, section 1).

