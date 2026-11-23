# GI assets and credits (production garden)

| what | where used | source | licence | stored |
|---|---|---|---|---|
| Charcoal Grill (kettle BBQ on a wheeled tripod), newArteest | `ld-s-bbq` (role `bbq`, `outdoor-assets.json`, id `skf_10162879`) | https://sketchfab.com/3d-models/charcoal-grill-10162879d1b048c48ee4d21ca9bc0fa7 | **CC-BY 4.0**, credit: "Charcoal Grill by newArteest" | `~/archpipe/shared/assets/user/landscape/outdoor/skf_10162879/` (outside git) |
| wood_chip_path (mulch), Poly Haven | `garden-mulch` | https://polyhaven.com/a/wood_chip_path | CC0 | `~/archpipe/assets/library/materials/wood_chip_path/` via `landscape/build/tools/fetch_gi_assets.py` |
| park_dirt (bare ground), Poly Haven | `garden-bare-ground`, `garden-ground-ours` | https://polyhaven.com/a/park_dirt | CC0 | same |
| Plaster003 (boundary render) | `garden-render` | ambientCG, already in the project library | CC0 | library |
| Travertine009 (coping, paving texture), gravel_ground_01 (gravel), teak_veneer (seat slats, trellis) | `garden-coping`, `garden-paving-*`, `garden-gravel-chip`, `garden-seat-timber`, `garden-trellis` | already in the project library | as recorded there | library |
| Star jasmine leaf atlas (Megascans, 15 live cut-outs) | climber leaf cards | LDL pass 6 (`fab_star_jasmine_trellis`), Fab listing 6daae790 | Fab Standard (client download) | `~/archpipe/shared/assets/user/landscape/fab/unzipped/` |

`knowledge/landscape/build/leaf-rects.json` = cut-out rectangles of the star-jasmine and bougainvillea atlases (`landscape/plants/tools/atlas_rects.py`); only star jasmine is used.
Rejected BBQs (looked at, not used): Sketchfab "Outdoor Grill" (016c9630, offset-drum smoker), "Barbecue grill" (d2b1e612), "Low Poly Barbecue" (b104816b, a diorama).
