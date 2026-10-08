# Client orientation naming and actual-scene sun hours

2026-10-06. No render, commit, native-model change or protected shared-data write. The authoritative record is [site-orientation.json](../knowledge/site-orientation.json).

| Model direction | Client name | Garden |
|---|---|---|
| −x | north | Street-side sunken garden; ground-floor balcony and open part |
| +y | east | Ramp, top deck and open sunken yard |
| +x | south | Rear lawn with frangipani |
| −y | west | Sister side |

Model x and y are horizontal scene coordinates in metres; z is elevation in metres, with ground-floor finished level at zero. IDs means identifiers; UTC means Coordinated Universal Time; RHS means Royal Horticultural Society. True model +y bearing remains 20 degrees clockwise from true north; the street facade true azimuth remains 290 degrees. These are solar/sun inputs only. No sun bearing rotates because of the naming change.

The guard checks landscape IDs (including one-letter side tokens), actual bed/route centroids, garden view IDs, labels, titles and every compass word in captions. Top trough edge names use the local top-garden centre. Paired pot end suffixes use the measured local axis order. Garden report coordinate tables and explicit model-axis statements are checked in portable verification; other narrative is bound to recorded reviewed hashes so an edit requires renewed naming review. The frozen committed street-side `landscape-bed-west` and `v36-west-court` fail; renamed/translated siblings and mutations also fail, while the corrected geometry stays quiet.

Actual landscape faces, asset transforms, materials and camera coordinates are preserved. Climber appearance seeds preserve the legacy deterministic foliage distribution. Frozen fixtures and historical approval coordinates remain unchanged; consumers migrate their identifiers explicitly through the recorded aliases. The route archive is keyed by native asset identities, not placement IDs, so `knowledge/asset-route-geometry.json.gz` is unchanged.

Sun rays use the final actual scene’s opaque building, context and architectural ground, including the house, four-metre basement-level fence and twelve-metre neighbours. Glass/translucent surfaces, plants and furniture are excluded. Sampling is at 50 mm above lower ground or deck, at each local standard clock hour when the sun is above the horizon, on 21 June, 20 March and 21 December 2026. Local standard time is UTC+02:00; latitude and longitude come from villa_env. True azimuth subtracts the recorded 20-degree model-Y bearing before conversion to model direction.

Comparison tolerance was declared as 0.5 hour: half the one-hour step. The lead file gives counts and rounded means but no point coordinates or sampling phase; this is an independent resampling comparison. The machine-readable report records every coordinate, date and visible hour. The balcony sample covers only our own half of the shared twin strip (four grid points); the lead counted eight points without disclosing their positions. Top samples remain inside the recorded rail-clear strip. It is a geometric enclosure screen, not weather-weighted plant illuminance or nursery approval.

| Zone | Points | June mean, hours | March mean, hours | December mean, hours | Old proxy June mean, hours |
|---|---:|---:|---:|---:|---:|
| north open | 20 | 1.100 | 0.650 | 0.150 | 4.750 |
| north balcony | 4 | 0.000 | 0.000 | 1.000 | 4.750 |
| east sunken | 21 | 4.381 | 1.762 | 0.238 | 9.000 |
| south rear | 54 | 4.167 | 3.056 | 2.741 | 6.204 |
| top deck | 24 | 7.917 | 2.083 | 0.000 | 9.000 |

| Required independent comparison | Measured hours | Lead hours | Difference hours | Pass at 0.5 h |
|---|---:|---:|---:|---|
| north open, 2026-06-21 | 1.100 | 0.9 | 0.200 | True |
| south rear, 2026-06-21 | 4.167 | 4.2 | 0.033 | True |
| south rear, 2026-12-21 | 2.741 | 2.8 | 0.059 | True |

Every planted species is checked below, including both climbers. Ranges are per actual plant sampling point; the full JSON preserves individual dates and hours. The RHS midsummer full-sun definition in the sole palette is strictly more than six hours; quoted best-flowering preferences are distinguished from tolerance of some shade. Missing quotes remain UNVERIFIED. Direct rays at ground do not measure neighbouring foliage shade, so indirect-light suitability remains unresolved where rays reach an Aspidistra. Retained placement is unchanged; newly found mismatch is not a waiver or a nursery acceptance.

| Species / actual zone | June hours | March hours | December hours | June quote applicability / seasonal limits |
|---|---|---|---|---|
| [Aloe vera](https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=282054) / top | 3–9 | 0–3 | 0–0 | SUPPORTED BY MIDSUMMER SCREEN.  Winter measures fewer than two direct hours; this screen cannot establish the quoted sun/partial-shade applicability in winter. |
| [Aspidistra elatior](https://www.rhs.org.uk/plants/aspidistra-elatior) / east | 4–4 | 1–2 | 0–0 | UNRESOLVED. Direct rays reach the sampling point; neighbouring foliage shade is excluded, so indirect-light suitability is unproven.  |
| [Aspidistra elatior](https://www.rhs.org.uk/plants/aspidistra-elatior) / north | 1–1 | 0–1 | 0–1 | UNRESOLVED. Direct rays reach the sampling point; neighbouring foliage shade is excluded, so indirect-light suitability is unproven.  |
| [Bougainvillea glabra](https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=282937) / east | 5–5 | 2–2 | 0–0 | MISMATCH. Full-sun preference/best flowering not met: midsummer requires more than six direct hours (tracked RHS definition). Winter measures fewer than two direct hours; this screen cannot establish the quoted sun/partial-shade applicability in winter. |
| [Chlorophytum comosum](https://plants.ces.ncsu.edu/plants/chlorophytum-comosum/) / north | 1–2 | 0–0 | 0–0 | MISMATCH. Quote excludes direct sunlight; enclosure-only rays reach this plant.  |
| [Cissus alata](https://plants.ces.ncsu.edu/plants/cissus-alata/) / north | 2–2 | 1–1 | 0–0 | PARTIAL. site measures ~0.9 h direct sun on 21 Jun and ~0.3 h on 21 Dec (lead ray-cast, out/villa/garden-sun-hours.json); deep shade is not listed by the source; client accepted the risk of sparser growth 2026-10-06 Winter measures fewer than two direct hours; this screen cannot establish the quoted sun/partial-shade applicability in winter. |
| [Fatsia japonica](https://plants.ces.ncsu.edu/plants/fatsia-japonica/) / north | 1–2 | 0–1 | 0–0 | SUPPORTED BY MIDSUMMER SCREEN.   |
| [Ixora coccinea](https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=286675) / east | 3–4 | 1–3 | 0–0 | MISMATCH. Full-sun preference/best flowering not met: midsummer requires more than six direct hours (tracked RHS definition). Winter measures fewer than two direct hours; this screen cannot establish the quoted sun/partial-shade applicability in winter. |
| [Ixora coccinea](https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=286675) / top | 5–10 | 1–4 | 0–0 | MISMATCH, SUPPORTED BY MIDSUMMER SCREEN. Full-sun preference/best flowering not met: midsummer requires more than six direct hours (tracked RHS definition). Winter measures fewer than two direct hours; this screen cannot establish the quoted sun/partial-shade applicability in winter. |
| [Ophiopogon japonicus](https://plants.ces.ncsu.edu/plants/ophiopogon-japonicus/) / north | 0–1 | 0–0 | 0–1 | MISMATCH. Deep shade screen; quoted dappled/partial shade does not establish deep-shade applicability. Retain recorded client trial risk. Winter measures fewer than two direct hours; this screen cannot establish the quoted sun/partial-shade applicability in winter. |
| [Plumeria rubra](https://plantfinder.mobot.org/PlantFinderDetails.aspx?kempercode=d451) / south | 4–4 | 3–3 | 3–3 | UNVERIFIED. No checked light quote; hours cannot establish suitability.  |
| [Rhapis excelsa](https://plants.ces.ncsu.edu/plants/rhapis-excelsa/) / north | 2–2 | 1–1 | 0–0 | SUPPORTED BY MIDSUMMER SCREEN.   |
| [Salvia rosmarinus Prostrata Group](https://www.rhs.org.uk/plants/salvia-rosmarinus-prostrata-group) / top | 9–9 | 4–5 | 0–0 | UNVERIFIED. No checked light quote; hours cannot establish suitability.  |
| [Strelitzia reginae](https://www.rhs.org.uk/plants/strelitzia-reginae) / east | 4–5 | 2–3 | 0–0 | UNVERIFIED. No checked light quote; hours cannot establish suitability.  |

Species source quotes and statuses remain in [garden-palette.json](../knowledge/garden-palette.json); the output records the exact quote joined to every plant. Cairo performance, leaf-level seasonal light and nursery/root/structural decisions remain unresolved.

Reproduce with `PYTHONPATH=src python scripts/orientation_naming_report.py`. [Measured evidence](../out/orientation/sun-report.json), [acceptance](../out/orientation/acceptance.json), and [current generated scene](../out/orientation/scene.json). Actual unsupported and blocked-opening lists: {"unsupported": [], "blocked_openings": []}.

Renamed current IDs and subject prefixes (historical removed assemblies also have explicit aliases in the record):

| Old ID | New ID |
|---|---|
| `east_center` | `south_center` |
| `east_rect` | `south_rect` |
| `landscape-accent-bed-west` | `landscape-accent-bed-north` |
| `landscape-bed-north` | `landscape-bed-east` |
| `landscape-bed-west` | `landscape-bed-north` |
| `landscape-climber-branches-north` | `landscape-climber-branches-east` |
| `landscape-climber-branches-west` | `landscape-climber-branches-north` |
| `landscape-climber-north` | `landscape-climber-east` |
| `landscape-climber-west` | `landscape-climber-north` |
| `landscape-door-pot-dining-e` | `landscape-door-pot-dining-s` |
| `landscape-door-pot-dining-e-planter` | `landscape-door-pot-dining-s-planter` |
| `landscape-door-pot-dining-w` | `landscape-door-pot-dining-n` |
| `landscape-door-pot-dining-w-planter` | `landscape-door-pot-dining-n-planter` |
| `landscape-door-pot-living-north-e` | `landscape-door-pot-living-east-s` |
| `landscape-door-pot-living-north-e-planter` | `landscape-door-pot-living-east-s-planter` |
| `landscape-door-pot-living-north-w` | `landscape-door-pot-living-east-n` |
| `landscape-door-pot-living-north-w-planter` | `landscape-door-pot-living-east-n-planter` |
| `landscape-door-pot-planter-dining-e-body` | `landscape-door-pot-planter-dining-s-body` |
| `landscape-door-pot-planter-dining-e-rim` | `landscape-door-pot-planter-dining-s-rim` |
| `landscape-door-pot-planter-dining-e-soil` | `landscape-door-pot-planter-dining-s-soil` |
| `landscape-door-pot-planter-dining-w-body` | `landscape-door-pot-planter-dining-n-body` |
| `landscape-door-pot-planter-dining-w-rim` | `landscape-door-pot-planter-dining-n-rim` |
| `landscape-door-pot-planter-dining-w-soil` | `landscape-door-pot-planter-dining-n-soil` |
| `landscape-door-pot-planter-living-north-e-body` | `landscape-door-pot-planter-living-east-s-body` |
| `landscape-door-pot-planter-living-north-e-rim` | `landscape-door-pot-planter-living-east-s-rim` |
| `landscape-door-pot-planter-living-north-e-soil` | `landscape-door-pot-planter-living-east-s-soil` |
| `landscape-door-pot-planter-living-north-w-body` | `landscape-door-pot-planter-living-east-n-body` |
| `landscape-door-pot-planter-living-north-w-rim` | `landscape-door-pot-planter-living-east-n-rim` |
| `landscape-door-pot-planter-living-north-w-soil` | `landscape-door-pot-planter-living-east-n-soil` |
| `landscape-edging-west` | `landscape-edging-north` |
| `landscape-edging-west-accent` | `landscape-edging-north-accent` |
| `landscape-edging-west-swing-back` | `landscape-edging-north-swing-back` |
| `landscape-grass-east` | `landscape-grass-south` |
| `landscape-grass-north` | `landscape-grass-east` |
| `landscape-gravel-west` | `landscape-gravel-north` |
| `landscape-north-back` | `landscape-east-back` |
| `landscape-north-back-00` | `landscape-east-back-00` |
| `landscape-north-back-01` | `landscape-east-back-01` |
| `landscape-north-back-02` | `landscape-east-back-02` |
| `landscape-north-front` | `landscape-east-front` |
| `landscape-north-front-00` | `landscape-east-front-00` |
| `landscape-north-front-01` | `landscape-east-front-01` |
| `landscape-north-front-02` | `landscape-east-front-02` |
| `landscape-north-mid` | `landscape-east-mid` |
| `landscape-north-mid-drift-00` | `landscape-east-mid-drift-00` |
| `landscape-north-mid-drift-01` | `landscape-east-mid-drift-01` |
| `landscape-north-mid-drift-02` | `landscape-east-mid-drift-02` |
| `landscape-soil-west-swing-back` | `landscape-soil-north-swing-back` |
| `landscape-stone-living-east-00` | `landscape-stone-living-south-00` |
| `landscape-stone-living-east-01` | `landscape-stone-living-south-01` |
| `landscape-stone-living-east-02` | `landscape-stone-living-south-02` |
| `landscape-stone-living-east-end-0` | `landscape-stone-living-south-end-0` |
| `landscape-stone-living-east-end-1` | `landscape-stone-living-south-end-1` |
| `landscape-stone-living-north-00` | `landscape-stone-living-east-00` |
| `landscape-stone-living-north-01` | `landscape-stone-living-east-01` |
| `landscape-stone-living-north-02` | `landscape-stone-living-east-02` |
| `landscape-stone-living-north-end-0` | `landscape-stone-living-east-end-0` |
| `landscape-stone-living-north-end-1` | `landscape-stone-living-east-end-1` |
| `landscape-stone-lounge-west-00` | `landscape-stone-lounge-north-00` |
| `landscape-stone-lounge-west-01` | `landscape-stone-lounge-north-01` |
| `landscape-stone-lounge-west-02` | `landscape-stone-lounge-north-02` |
| `landscape-stone-lounge-west-03` | `landscape-stone-lounge-north-03` |
| `landscape-stone-lounge-west-end-0` | `landscape-stone-lounge-north-end-0` |
| `landscape-stone-lounge-west-end-1` | `landscape-stone-lounge-north-end-1` |
| `landscape-top-deck-north` | `landscape-top-deck-east` |
| `landscape-top-deck-north-00` | `landscape-top-deck-east-00` |
| `landscape-top-deck-north-01` | `landscape-top-deck-east-01` |
| `landscape-top-deck-north-02` | `landscape-top-deck-east-02` |
| `landscape-top-north-ixora-0` | `landscape-top-pot-ixora-0` |
| `landscape-top-north-ixora-1` | `landscape-top-pot-ixora-1` |
| `landscape-top-roof-north-00` | `landscape-top-roof-east-00` |
| `landscape-top-roof-north-01` | `landscape-top-roof-east-01` |
| `landscape-top-roof-north-02` | `landscape-top-roof-east-02` |
| `landscape-top-roof-south-00` | `landscape-top-roof-west-00` |
| `landscape-top-roof-south-01` | `landscape-top-roof-west-01` |
| `landscape-top-roof-south-02` | `landscape-top-roof-west-02` |
| `landscape-top-trough-deck-north` | `landscape-top-trough-deck-east` |
| `landscape-top-trough-deck-north-body` | `landscape-top-trough-deck-east-body` |
| `landscape-top-trough-deck-north-soil` | `landscape-top-trough-deck-east-soil` |
| `landscape-top-trough-roof-north` | `landscape-top-trough-roof-east` |
| `landscape-top-trough-roof-north-body` | `landscape-top-trough-roof-east-body` |
| `landscape-top-trough-roof-north-soil` | `landscape-top-trough-roof-east-soil` |
| `landscape-top-trough-roof-south` | `landscape-top-trough-roof-west` |
| `landscape-top-trough-roof-south-body` | `landscape-top-trough-roof-west-body` |
| `landscape-top-trough-roof-south-soil` | `landscape-top-trough-roof-west-soil` |
| `landscape-tree-east` | `landscape-tree-south` |
| `landscape-tree-pit-east` | `landscape-tree-pit-south` |
| `landscape-trellis-north` | `landscape-trellis-east` |
| `landscape-trellis-west` | `landscape-trellis-north` |
| `landscape-west-back-00` | `landscape-north-back-00` |
| `landscape-west-back-01` | `landscape-north-back-01` |
| `landscape-west-back-02` | `landscape-north-back-02` |
| `landscape-west-edge` | `landscape-north-edge` |
| `landscape-west-edge-00` | `landscape-north-edge-00` |
| `landscape-west-edge-01` | `landscape-north-edge-01` |
| `landscape-west-edge-02` | `landscape-north-edge-02` |
| `landscape-west-edge-03` | `landscape-north-edge-03` |
| `landscape-west-edge-04` | `landscape-north-edge-04` |
| `landscape-west-feature-stone` | `landscape-north-feature-stone` |
| `landscape-west-front` | `landscape-north-front` |
| `landscape-west-front-00` | `landscape-north-front-00` |
| `landscape-west-front-01` | `landscape-north-front-01` |
| `landscape-west-front-02` | `landscape-north-front-02` |
| `landscape-west-mid-00` | `landscape-north-mid-00` |
| `landscape-west-mid-01` | `landscape-north-mid-01` |
| `landscape-west-mid-02` | `landscape-north-mid-02` |
| `landscape-west-rhapis-accent` | `landscape-north-rhapis-accent` |
| `v26-top-garden-north` | `v26-top-garden-east` |
| `v27-north-garden-above` | `v27-east-yard-above` |
| `v28-north-garden-below` | `v28-east-yard-below` |
| `v36-west-court` | `v36-north-garden` |
| `v37-west-court-bistro` | `v37-north-garden-lounge` |

Portable verification: normal exit 0, fresh empty-HOME exit 0; HOME verified empty before launch: True. Logs: [normal](../out/orientation/verify-normal-final.log), [empty HOME](../out/orientation/verify-empty-home-final.log).

| Legacy zone/route/edge | Current name |
|---|---|
| `west` | `north` |
| `north` | `east` |
| `east` | `south` |
| `south` | `west` |
| `living-north` | `living-east` |
| `living-east` | `living-south` |
| `lounge-west` | `lounge-north` |
| `deck-north` | `deck-east` |
| `roof-north` | `roof-east` |
| `roof-south` | `roof-west` |
| `dining-w` | `dining-n` |
| `dining-e` | `dining-s` |
| `living-north-w` | `living-east-n` |
| `living-north-e` | `living-east-s` |
| `lounge-west-n` | `lounge-north-e` |
| `lounge-west-s` | `lounge-north-w` |
| `west-accent` | `north-accent` |
| `west-swing-back` | `north-swing-back` |
