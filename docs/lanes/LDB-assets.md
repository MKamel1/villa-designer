## Free outdoor furniture and koi

Date 2026-11-22. Binaries: `~/archpipe/shared/assets/user/landscape/outdoor/<id>/scene.gltf` (outside git). Record: `knowledge/landscape/build/outdoor-assets.json` (schema `outdoor-assets/1`), previews in `knowledge/landscape/build/outdoor-previews/`. Preview tool: `src/archpipe/landscape/build/tools/outdoor_preview.py` (Blender, ran on CPU through jobq, ids `ldb-outdoor-prev-cpu*`, because the GPU queue was full).

**Searched.** Poly Haven API (all 150-odd CC0 models filtered by furniture/outdoor words; no fish or koi exists there) and the Sketchfab search API (`downloadable=true`, licence label restricted to "CC0 Public Domain" or "CC Attribution"), queries: outdoor dining table, garden table, patio table, garden/outdoor chair, garden/park bench, koi, koi fish, carp fish, koi pond. 28 Sketchfab and 6 Poly Haven models downloaded, each unzipped into its own empty directory, never executed, rendered 4 azimuths, and measured (triangles, extents, textures, open-edge share, flat-card test). The licence was re-read from `/v3/models/<uid>` at download time; all downloaded Sketchfab items were "CC Attribution" (CC-BY 4.0). Poly Haven is CC0 by site policy (its API has no per-asset licence field).

**Result.** koi_found = true. No asset graded A. Grade B means recognisable, clean, plausible proportions; C is a usable fallback with a stated flaw.

| role | best | also |
|---|---|---|
| dining_table | `skf_12cf06b5` Wooden Dining Table Set (table + 6 chairs, B); `skf_4febe1ee` Worn garden table, 2.46 x 0.71 m, table only (B) | `ph_wooden_picnic_table` (B), `skf_76d6011a` (B, 4 chairs), two C fallbacks |
| dining_chair | `ph_plastic_monobloc_chair_01` (CC0, B); `skf_7f558fcd` folding patio chair (B); the 6 chairs in `skf_12cf06b5` | `ph_outdoor_table_chair_set_01` (B, bistro) |
| bench | `skf_01a5b644` park bench 2.0 x 0.72 x 0.90 m in metres (B); `skf_d0d03173`, `skf_df71b965`, `skf_1ddafec2`, `skf_82cadef8` (B) | |
| koi | `skf_3e1b80c3` single red/white (B); `skf_8bc4556d` school of about 15 (B); `skf_602b3cbf` tricolour (B) | `skf_236859b8`, `skf_8ffded4f` (C) |

**Refused or rejected** (full reasons in the JSON `rejected` list): sun loungers (wrong role); a pergola set with a noise-baked texture; tables too small for 8-10 (0.7-0.8 m); lounge sofa sets; urban modular seating; an indoor Poly Haven dining chair and sofa; a koi in a glass ball; a common carp (not koi); a cartoon koi; the CC0 carp scans (0.5-3.4 M faces, brown carp, not koi); the Sketchfab copy of the monobloc chair (same mesh as the CC0 Poly Haven copy, which needs no credit). No NC or ND item was downloaded: those labels were filtered out in the search, so nothing was licence-refused after download.

**Unit warning for the build.** glTF is nominally metres but many authors used cm or arbitrary units; `size_m` is the native extent. Scale by a target dimension (bench length 1.6-1.8 m, table length 2.4 m, koi 0.5-0.7 m), not by unit. Metre-native: `skf_4febe1ee`, `skf_01a5b644`, `skf_df71b965`, `skf_02633251`, `skf_3e1b80c3` and all `ph_*`. `skf_12cf06b5` imports at 0.02 m (x100 gives about 2.0 x 1.3 x 0.9 m). Fronts are given in the JSON in Blender Z-up axes after glTF import (front -Y equals glTF +Z).

**Attribution strings (CC-BY 4.0, "Author must be credited", commercial use allowed), one line per asset used:**

- "Wooden Dining Table Set" by aziseptian (https://sketchfab.com/3d-models/wooden-dining-table-set-12cf06b544574248bab985de436b15e2) is licensed under CC BY 4.0 (http://creativecommons.org/licenses/by/4.0/).
- "Worn garden table (LowPoly)" by toxiccrack (https://sketchfab.com/3d-models/worn-garden-table-lowpoly-4febe1eec0a5419a8816ac7f30aa9189), CC BY 4.0.
- "External Metal Table and Chairs" by Francesco Coldesina (https://sketchfab.com/3d-models/external-metal-table-and-chairs-76d6011abc8848c89f080df54ed4d0f8), CC BY 4.0.
- "Patio Chair (reconstruction)" by pigfinite (https://sketchfab.com/3d-models/patio-chair-reconstruction-7f558fcd893a4a78aaa6e91e41ce798f), CC BY 4.0.
- "Classic Park Bench (Low Poly)" by Berk Gedik; "Bench -- aged and gritty" by Glowbox 3D; "Japanese Garden Bench" by Anastasiia Shevchenko; "Street Bench" by donnichols; "Fancy Bench" by SomeKevin: each CC BY 4.0, URLs in the JSON.
- "Koi Fish" by SDPM Esare (`skf_3e1b80c3`); "Koi Fish" by local.yany (`skf_8bc4556d`); "Koi fish" by amalie.kma (`skf_602b3cbf`): each CC BY 4.0, URLs in the JSON.
- CC0 (no credit required, credit courtesy): Poly Haven "Plastic Monobloc Chair 01" (Kuutti Siitonen), "Outdoor Table Chair Set 01" (James Ray Cock), "Wooden Picnic Table" (Ulan Cabanilla).

Each downloaded Sketchfab folder keeps the author's `license.txt` with the exact credit text; use that if wording matters. Run the credit through the drawing/report credits list if the asset is shown to the client.
