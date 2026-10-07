---
document_outline:
  - title: Executive Summary
    link: "#executive-summary"
  - title: Material Basis Classification Taxonomy
    link: "#material-basis-classification-taxonomy"
  - title: Inventory of Scene Materials (villa_render.py & villa_scene.py)
    link: "#inventory-of-scene-materials"
  - title: Inventory of Dynamic Lighting & Emitter Materials
    link: "#inventory-of-dynamic-lighting--emitter-materials"
  - title: Inventory of Revit Specification & Extraction Materials
    link: "#inventory-of-revit-specification--extraction-materials"
  - title: Inventory of Asset Library Manifest Textures
    link: "#inventory-of-asset-library-manifest-textures"
  - title: Audit Findings and Flagged Gaps
    link: "#audit-findings-and-flagged-gaps"
executive_summary: >
  This document provides the Phase 1 material basis inventory for lessons class C7 ("appearance lacks verified basis").
  It audits all 54 static materials in the villa renderer, dynamic lighting emitters, Revit specification elements,
  and 37 asset library textures against physical optical records, cited standards, and real-world dimensions.
  Flagged defects include materials lacking optical records, uncalibrated CAD hues, unanchored texture scales,
  degenerate wood grain axes, and unanchored glass transmission records.
---

# Material Basis Inventory: Class C7 ("Appearance Lacks Verified Basis")

## Executive Summary

Under project rule ADR-0013 and class rule C7 from `docs/lessons-audit.md` ("Bind visible surfaces and models to verified product and optical records"), every surface and volume presented to clients, reviewers, or simulation engines must be anchored to verifiable physical records. Historically, unbacked CAD shading colours, uncalibrated texture repetitions, unanchored glass transmission values, and orientation-blind procedural mappings caused recurring visual and photometric failures (e.g., `l0016`, `l0028`, `l0049`, `l0064`, `l0065`, `l0083`, `l0084`, `l0677`, `l0795`, `l0891`, `l0900`, `l0910`).

This inventory establishes the baseline optical and geometric basis for every material utilized in `src/archpipe/concept/villa_render.py`, `src/archpipe/blender/villa_scene.py`, `src/archpipe/concept/revit_spec.py`, and `ops/workstation/library-manifest.json`.

---

## Material Basis Classification Taxonomy

Each material is classified into one of three rigorous status tiers:

1. **`VERIFIED`**: Optical parameters (diffuse reflectance $\rho$, specular roughness $\sigma$, visible transmittance $\tau$, index of refraction $\eta$, or texture tile extent $s_{\text{tile}}$) are directly anchored to a verifiable cited standard (e.g., ASTM E903, CIBSE SLL Code for Lighting, Metric Handbook, IES Lighting Handbook) or physical scanning record with published real-world dimensions (e.g., Poly Haven physical scans).
2. **`ASSUMED`**: Parameters have an explicit architectural reason or design hypothesis documented in code/comments, but lack a physical laboratory measurement or manufacturer product cut sheet.
3. **`NONE`**: The material lacks any optical basis, uses an unverified raw CAD hue/placeholder, has contradictory definitions between modules, or omits mandatory physical properties (such as glass transmittance or real-world texture scale).

---

## Inventory of Scene Materials

Audited from `src/archpipe/concept/villa_render.py` (`M` dictionary, lines 44–220) and configured in `src/archpipe/blender/villa_scene.py` (`add_material`, lines 226–350).

| Material ID | Kind | Base RGB (Linear) | Reflectance ($\rho$) | Roughness ($\sigma$) | Transmittance ($\tau$) / IOR ($\eta$) | Texture Asset & Tile Size | Grain Axis | Status | Citation (`file:line`) | Optical Record & Rationale |
|---|---|---|---:|---:|---:|---|---|---|---|---|
| `plaster-warm-white` | principled | `[0.80, 0.785, 0.755]` | 0.80 | 0.85 | — | None | None | `VERIFIED` | `src/archpipe/concept/villa_render.py:45` | CIBSE SLL Code for Lighting / ADR-0013: clean smooth gypsum plaster target $\rho = 0.80$. |
| `ceiling-white` | principled | `[0.86, 0.85, 0.83]` | 0.85 | 0.95 | — | None | None | `VERIFIED` | `src/archpipe/concept/villa_render.py:49` | CIBSE SLL / ADR-0013: matt white false ceiling target $\rho = 0.85$. |
| `travertine` | principled | `[0.66, 0.63, 0.57]` | 0.55 | 0.35 | — | `Marble014`, $s = 1.20\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:51` | Honed cream stone look-alike; ambientCG texture scale assumed. |
| `oak-floor` | principled | `[0.45, 0.33, 0.22]` | 0.33 | 0.50 | — | `oak_wood_planks`, $s = 1.20\text{ m}$ | `x` | `VERIFIED` | `src/archpipe/concept/villa_render.py:54` | Poly Haven real scan $1.20\text{ m}$; plank grain axis along $x$. |
| `marble-ensuite` | principled | `[0.66, 0.60, 0.52]` | 0.58 | 0.25 | — | `Marble020`, $s = 1.20\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:57` | Warm cream marble look-alike; ambientCG texture scale assumed. |
| `marble-bath` | principled | `[0.70, 0.66, 0.58]` | 0.62 | 0.30 | — | `Marble014`, $s = 1.20\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:59` | Cream marble look-alike; ambientCG texture scale assumed. |
| `marble-wet` | principled | `[0.62, 0.59, 0.53]` | 0.55 | 0.45 | — | `Marble014`, $s = 0.30\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:61` | Smaller-format wet-zone stone look-alike; slip rating pending. |
| `marble-white` | principled | `[0.78, 0.78, 0.76]` | 0.72 | 0.18 | — | `Marble012`, $s = 1.40\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:64` | White veined stone worktop; ambientCG texture scale assumed. |
| `walnut` | principled | `[0.20, 0.11, 0.06]` | 0.12 | 0.45 | — | `natural_walnut_veneer`, $s = 1.00\text{ m}$ | `z` | `VERIFIED` | `src/archpipe/concept/villa_render.py:75` | Poly Haven real scan $1.00\text{ m}$. Flag: `grain_axis="z"` collides on horizontal members. |
| `oak` | principled | `[0.52, 0.40, 0.27]` | 0.40 | 0.50 | — | `white_oak_veneer`, $s = 0.50\text{ m}$ | `z` | `VERIFIED` | `src/archpipe/concept/villa_render.py:78` | Poly Haven real scan $0.50\text{ m}$. Flag: `grain_axis="z"` collides on horizontal frames. |
| `greige-lacquer` | principled | `[0.46, 0.42, 0.37]` | 0.43 | 0.35 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:82` | Matt greige kitchen fronts; physical product pending. |
| `boucle` | principled | `[0.74, 0.70, 0.64]` | 0.66 | 0.95 | — | `Fabric082A`, $s = 0.30\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:84` | Cream boucle upholstery; ambientCG texture scale assumed. |
| `linen` | principled | `[0.55, 0.50, 0.43]` | 0.48 | 0.95 | — | `Fabric036`, $s = 0.30\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:86` | Oatmeal linen upholstery; ambientCG texture scale assumed. |
| `sage-fabric` | principled | `[0.40, 0.44, 0.36]` | 0.38 | 0.95 | — | `Fabric066`, $s = 0.30\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:88` | Sage cotton upholstery; ambientCG texture scale assumed. |
| `charcoal-fabric` | principled | `[0.07, 0.07, 0.07]` | 0.07 | 0.95 | — | `Fabric030`, $s = 0.40\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:90` | Charcoal acoustic wall fabric; cinema darkness target $\rho = 0.07$. |
| `taupe-fabric` | principled | `[0.33, 0.28, 0.23]` | 0.25 | 0.95 | — | `Fabric036`, $s = 0.40\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:93` | Warm taupe acoustic panels; ambientCG texture scale assumed. |
| `bedding-white` | principled | `[0.82, 0.81, 0.78]` | 0.78 | 0.95 | — | `Fabric081C`, $s = 0.18\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:96` | White cotton bedding weave scale assumed. Reflectance 0.78 plausible. |
| `throw-taupe` | principled | `[0.34, 0.29, 0.25]` | 0.28 | 0.92 | — | `Fabric036`, $s = 0.22\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:98` | Woven taupe bed throw dressing; ambientCG texture scale assumed. |
| `rug` | principled | `[0.62, 0.58, 0.51]` | 0.55 | 1.00 | — | `Carpet016`, $s = 0.80\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:100` | Wool rug; ambientCG texture scale assumed. |
| `leather-brown` | principled | `[0.14, 0.08, 0.05]` | 0.10 | 0.50 | — | `Leather030`, $s = 0.50\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:102` | Cognac leather; ambientCG texture scale assumed. |
| `garment-ivory` | principled | `[0.86, 0.83, 0.76]` | 0.55 | 0.60 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:106` | Wardrobe garment dressing palette; physical fabric pending. |
| `garment-blush` | principled | `[0.70, 0.52, 0.50]` | 0.45 | 0.65 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:108` | Wardrobe garment dressing palette; physical fabric pending. |
| `garment-terracotta` | principled | `[0.58, 0.32, 0.22]` | 0.35 | 0.70 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:110` | Wardrobe garment dressing palette; physical fabric pending. |
| `garment-sage-soft` | principled | `[0.46, 0.50, 0.40]` | 0.38 | 0.68 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:112` | Wardrobe garment dressing palette; physical fabric pending. |
| `garment-navy` | principled | `[0.10, 0.13, 0.22]` | 0.25 | 0.55 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:114` | Wardrobe garment dressing palette; physical fabric pending. |
| `garment-charcoal` | principled | `[0.16, 0.16, 0.17]` | 0.22 | 0.55 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:116` | Wardrobe garment dressing palette; physical fabric pending. |
| `garment-stone` | principled | `[0.55, 0.52, 0.46]` | 0.42 | 0.60 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:118` | Wardrobe garment dressing palette; physical fabric pending. |
| `garment-olive` | principled | `[0.28, 0.30, 0.18]` | 0.28 | 0.62 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:120` | Wardrobe garment dressing palette; physical fabric pending. |
| `brass` | principled | `[0.80, 0.62, 0.34]` | 0.62 | 0.30 | — | None | None | `NONE` | `src/archpipe/concept/villa_render.py:122` | Procedural flat brushed brass; no manufacturer alloy/finish record. |
| `black-metal` | principled | `[0.03, 0.03, 0.03]` | 0.03 | 0.40 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:124` | Black powder coat; specular metallic $\rho = 0.03$. |
| `ceramic-white` | principled | `[0.85, 0.85, 0.84]` | 0.84 | 0.08 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:126` | Glazed sanitary ceramic; manufacturer product cut sheet pending. |
| `screen-black` | principled | `[0.01, 0.01, 0.01]` | 0.01 | 0.05 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:128` | Unlit TV/display glass; low specular reflection $\rho = 0.01$. |
| `glass-clear` | glass | `[1.0, 1.0, 1.0]` | — | 0.00 | $\tau = 0.70, \eta = 1.50$ | None | None | `VERIFIED` | `src/archpipe/concept/villa_render.py:130` | Metric Handbook p. 9-8: clear double glazing $\tau = 0.70, \text{interfaces} = 2$. |
| `glass-guard` | glass | `[1.0, 1.0, 1.0]` | — | 0.00 | $\tau = 0.85, \eta = 1.50$ | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:132` | Laminated glass balustrade; optical record unanchored. |
| `glass-edge` | principled | `[0.58, 0.69, 0.65]` | 0.55 | 0.12 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:134` | Polished laminated-glass exposed edge look-alike. |
| `opal-strip` | principled | `[0.88, 0.85, 0.78]` | 0.78 | 0.32 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:136` | Opal diffuser over cabinet LED strip; product pending. |
| `silvered-mirror` | principled | `[0.91, 0.92, 0.92]` | 0.92 | 0.035 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:138` | Silvered vanity mirror; high specular reflectance $\rho = 0.92$. |
| `door-oak` | principled | `[0.52, 0.40, 0.27]` | 0.40 | 0.50 | — | `oak_veneer_01`, $s = 1.83\text{ m}$ | `z` | `VERIFIED` | `src/archpipe/concept/villa_render.py:140` | Poly Haven real scan $1.83\text{ m}$; vertical grain axis $z$. |
| `render-exterior` | principled | `[0.65, 0.65, 0.65]` | 0.65 | 0.85 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:144` | Smooth mineral exterior render on neighbours. |
| `paint-exterior-grey-green` | principled | `[0.590, 0.672, 0.605]` | 0.65 | 0.82 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:146` | Stated reflectance 0.65, green cast $G/R = 1.14$. |
| `paving` | principled | `[0.62, 0.58, 0.52]` | 0.45 | 0.80 | — | `PavingStones146`, $s = 2.00\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:148` | Stone garden paving; ambientCG texture scale assumed. |
| `garden-gravel` | principled | `[0.47, 0.43, 0.36]` | 0.32 | 1.00 | — | `gravel_ground_01`, $s = 2.00\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:150` | CC0 gravel beds scan; scale assumed. |
| `artificial-grass` | principled | `[0.16, 0.235, 0.105]` | 0.20 | 0.92 | — | `Grass002`, $s = 1.00\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:158` | Short turf ambientCG Grass002 CC0 scan, tile $1.0\text{ m}$; fixed from `l0891`. |
| `stepping-stone` | principled | `[0.62, 0.58, 0.50]` | 0.45 | 0.85 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:162` | Honed sandstone stepping stones; texture asset missing. |
| `trellis` | principled | `[0.16, 0.12, 0.08]` | 0.13 | 0.70 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:164` | Timber wall trellis; texture asset missing. |
| `bougainvillea-bract` | principled | `[0.58, 0.035, 0.25]` | 0.20 | 0.85 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:166` | Procedural magenta flower mass; optical basis unanchored. |
| `bougainvillea-leaf` | principled | `[0.07, 0.22, 0.055]` | 0.17 | 0.78 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:168` | Procedural foliage; optical basis unanchored. |
| `garden-pebbles` | principled | `[0.48, 0.46, 0.41]` | 0.36 | 0.90 | — | `floor_pebbles_01`, $s = 1.50\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:170` | CC0 scan pebbles; tile size assumed. |
| `garden-sandstone` | principled | `[0.60, 0.52, 0.40]` | 0.42 | 0.85 | — | `sandstone_cracks`, $s = 1.00\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:172` | CC0 scan sandstone planters; tile size assumed. |
| `lawn` | principled | `[0.10, 0.16, 0.05]` | 0.12 | 1.00 | — | `Grass004`, $s = 2.00\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:174` | Garden lawn ambientCG Grass004; tile size assumed. |
| `outdoor-fabric` | principled | `[0.62, 0.58, 0.50]` | 0.55 | 0.95 | — | `Fabric036`, $s = 0.30\text{ m}$ | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:176` | Outdoor acrylic fabric; ambientCG scale assumed. |
| `teak` | principled | `[0.35, 0.22, 0.12]` | 0.22 | 0.60 | — | `teak_veneer`, $s = 1.00\text{ m}$ | `x` | `VERIFIED` | `src/archpipe/concept/villa_render.py:178` | Poly Haven real scan $1.00\text{ m}$; grain axis $x$. |
| `alu-bronze` | principled | `[0.10, 0.09, 0.08]` | 0.09 | 0.35 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:180` | Dark bronze anodised aluminium ($\rho = 0.09$); fixed from `l0084` pale tan. |
| `stainless` | principled | `[0.62, 0.65, 0.66]` | 0.55 | 0.28 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:182` | Brushed stainless steel linear drain; product pending. |
| `paint-white-satin` | principled | `[0.82, 0.81, 0.79]` | 0.80 | 0.35 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:184` | White satin trim paint; manufacturer sheet pending. |
| `white-paint-joinery` | principled | `[0.80, 0.79, 0.76]` | 0.78 | 0.40 | — | None | None | `ASSUMED` | `src/archpipe/concept/villa_render.py:186` | White painted joinery; manufacturer sheet pending. |
| `curtain-sheer` | translucent | `[0.86, 0.84, 0.79]` | 0.70 | 0.85 | $\tau = 0.55$ | `rough_linen`, $s = 0.27\text{ m}$ | None | `VERIFIED` | `src/archpipe/concept/villa_render.py:194` | Poly Haven real scan $0.27\text{ m}$; diffuse transmittance $\tau = 0.55$ assumed. |
| `curtain-heavy` | translucent | `[0.40, 0.36, 0.31]` | 0.32 | 0.60 | $\tau = 0.02$ | `crepe_satin`, $s = 0.266\text{ m}$ | None | `VERIFIED` | `src/archpipe/concept/villa_render.py:202` | Poly Haven real scan $0.266\text{ m}$; blackout transmittance $\tau = 0.02$ assumed. |
| `curtain-heavy-dimout` | translucent | `[0.40, 0.36, 0.31]` | 0.32 | 0.60 | $\tau = 0.10$ | `crepe_satin`, $s = 0.266\text{ m}$ | None | `VERIFIED` | `src/archpipe/concept/villa_render.py:206` | Poly Haven real scan $0.266\text{ m}$; dimout transmittance $\tau = 0.10$ assumed. |
| `oak-grain-x` | principled | `[0.52, 0.40, 0.27]` | 0.40 | 0.50 | — | `white_oak_veneer`, $s = 0.50\text{ m}$ | `x` | `VERIFIED` | `src/archpipe/concept/villa_render.py:212` | Horizontal bed frame variant; non-degenerate projection. |
| `walnut-grain-x` | principled | `[0.20, 0.11, 0.06]` | 0.12 | 0.45 | — | `natural_walnut_veneer`, $s = 1.00\text{ m}$ | `x` | `VERIFIED` | `src/archpipe/concept/villa_render.py:213` | Horizontal top/shelf variant; non-degenerate projection. |
| `walnut-grain-y` | principled | `[0.20, 0.11, 0.06]` | 0.12 | 0.45 | — | `natural_walnut_veneer`, $s = 1.00\text{ m}$ | `y` | `VERIFIED` | `src/archpipe/concept/villa_render.py:220` | Stair tread length variant; non-degenerate along tread run. |

---

## Inventory of Dynamic Lighting & Emitter Materials

Audited from `src/archpipe/concept/villa_render.py` (`_build` emitter and diffuser generation, lines 1803–2012).

| Material ID Pattern | Kind | Base RGB | Emission Target | CCT ($K$) | Status | Citation (`file:line`) | Optical Record & Rationale |
|---|---|---|---|---|---|---|---|
| `lens-{cct}` | emissive | `[1.0, 1.0, 1.0]` | $40{,}000\text{ lm/m}^2$ | 2700 / 3000 | `ASSUMED` | `src/archpipe/concept/villa_render.py:1803` | Camera lens glow only (no light contribution). |
| `opal-vsconce-{cct}` | emissive | `[0.95, 0.93, 0.90]` | $\text{lumens} / \text{area}$ | 2700 | `ASSUMED` | `src/archpipe/concept/villa_render.py:1846` | Vertical opal sconce diffuser; generic luminaire model. |
| `swing-disc-{cct}` | emissive | `[1.0, 0.94, 0.82]` | $\text{lumens} / \text{area}$ | 2700 | `ASSUMED` | `src/archpipe/concept/villa_render.py:1912` | Articulated swing reading lamp disc emitter. |
| `opal-pen-globe-{cct}` | translucent | `[0.97, 0.96, 0.92]` | $\tau = 0.65, \rho = 0.85$ | — | `ASSUMED` | `src/archpipe/concept/villa_render.py:1929` | Island/stair pendant globes: milky opal translucent glass shade lit from inside. Fixed from `l0900`. |
| `opal-inner-{cct}` | emissive | `[1.0, 0.96, 0.88]` | $\text{lumens} / \text{area}$ | 2700 | `ASSUMED` | `src/archpipe/concept/villa_render.py:1940` | Internal emitter bulb within translucent opal globe. |
| `opal-pen-small-{cct}` | emissive | `[0.95, 0.93, 0.90]` | $\text{lumens} / \text{area}$ | 2700 | `ASSUMED` | `src/archpipe/concept/villa_render.py:1932` | Small pendant opal diffuser globe. |
| `opal-sconce-{cct}` | emissive | `[0.95, 0.93, 0.90]` | $\text{lumens} / \text{area}$ | 2700 | `ASSUMED` | `src/archpipe/concept/villa_render.py:1932` | Wall sconce opal diffuser globe. |
| `opal-wall-read-{cct}` | emissive | `[0.95, 0.93, 0.90]` | $\text{lumens} / \text{area}$ | 2700 | `ASSUMED` | `src/archpipe/concept/villa_render.py:1932` | Bedside reading swing diffuser. |
| `led-lin-{cct}` | emissive | `[1.0, 1.0, 1.0]` | $\text{lumens} / \text{area}$ | 2700 / 3000 | `ASSUMED` | `src/archpipe/concept/villa_render.py:1967` | Linear pendant acrylic diffuser. |
| `marker-{cct}` | emissive | `[1.0, 1.0, 1.0]` | $\text{lumens} / \text{area}$ | 2700 | `ASSUMED` | `src/archpipe/concept/villa_render.py:2010` | Recessed low-level wall step marker. |

---

## Inventory of Revit Specification & Extraction Materials

Audited from `src/archpipe/concept/revit_spec.py` and dynamic assembly builders in `src/archpipe/concept/villa_render.py`.

| Element / Material ID | Category | Optical Properties | Status | Citation (`file:line`) | Optical Record & Rationale |
|---|---|---|---|---|---|
| `pe-bath-screen` (`glass-bath-screen`) | fixed-frameless-glass | $\tau = 0.91, \eta = 1.52, \text{interfaces} = 2, \sigma = 0.0$ | `ASSUMED` | `src/archpipe/concept/revit_spec.py:434`, `src/archpipe/concept/villa_render.py:1543` | "ASSUMED 10 mm low-iron glass: 0.91 transmittance, 1.52 index of refraction; TODO low-iron-glass-optics". Fixed from `l0910`. |
| `pe-linear-drain` (`stainless`) | sanitary-drain | $\rho = 0.55, \text{metallic} = 1.0, \sigma = 0.28$ | `ASSUMED` | `src/archpipe/concept/revit_spec.py:428`, `src/archpipe/concept/villa_render.py:1528` | "ASSUMED 70 mm tile-in grate at wet-zone edge; product pending". |
| Revit Wall & Ceiling Paint Hue | finish | Raw .NET RGB byte channel values | `NONE` | `docs/LEARNINGS.md:172` (`l0028`) | Revit shading colour is a display hue, not measured reflectance. Treated as unbacked CAD hue. |

---

## Inventory of Asset Library Manifest Textures

Audited from `ops/workstation/library-manifest.json` (materials section, lines 4–227).

| Asset ID | Source | Role | Dimensions / Tile Size | Status | Manifest Source Citation |
|---|---|---|---|---|---|
| `oak_wood_planks` | Poly Haven | oak floor planks | $1.20\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:186` |
| `white_oak_veneer` | Poly Haven | light oak veneer joinery | $0.50\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:162` |
| `natural_walnut_veneer` | Poly Haven | walnut veneer joinery | $1.00\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:168` |
| `american_walnut_veneer` | Poly Haven | walnut veneer alternative | $1.00\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:174` |
| `teak_veneer` | Poly Haven | outdoor teak veneer | $1.00\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:180` |
| `oak_veneer_01` | Poly Haven | door flush oak veneer | $1.83\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:156` |
| `plank_flooring_02` | Poly Haven | engineered floor alternate | $1.50\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:192` |
| `rough_linen` | Poly Haven | sheer linen curtain weave | $0.27\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:198` |
| `crepe_satin` | Poly Haven | curtain face weave | $0.266\text{ m}$ (verified API) | `VERIFIED` | `ops/workstation/library-manifest.json:204` |
| `gravel_ground_01` | Poly Haven | garden gravel | $2.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:210` |
| `floor_pebbles_01` | Poly Haven | planter mulch pebbles | $1.50\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:216` |
| `sandstone_cracks` | Poly Haven | stone planter walls | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:222` |
| `Marble012` | ambientCG | stone worktops | $1.40\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:48` |
| `Marble014` | ambientCG | bathroom marble / travertine | $1.20\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:72` |
| `Marble020` | ambientCG | ensuite marble | $1.20\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:78` |
| `Travertine009` | ambientCG | travertine floor | $1.20\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:66` |
| `Fabric030` | ambientCG | cinema upholstery | $0.40\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:96` |
| `Fabric036` | ambientCG | linen upholstery / throw | $0.30\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:18` |
| `Fabric066` | ambientCG | kids cotton upholstery | $0.30\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:102` |
| `Fabric081C` | ambientCG | bedding white | $0.18\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:120` |
| `Fabric082A` | ambientCG | boucle upholstery | $0.30\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:30` |
| `Carpet016` | ambientCG | rugs | $0.80\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:114` |
| `Leather030` | ambientCG | stool leather | $0.50\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:108` |
| `Grass002` | ambientCG | artificial grass turf | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:138` |
| `Grass004` | ambientCG | garden lawn | $2.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:132` |
| `PavingStones146` | ambientCG | terrace paving | $2.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:126` |
| `Plaster001` | ambientCG | rough wall plaster (unused) | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:36` |
| `Plaster003` | ambientCG | exterior render | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:144` |
| `Metal046A` | ambientCG | dark hardware (unused) | $0.50\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:42` |
| `Wood049` | ambientCG | oak furniture (unused) | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:6` |
| `Wood051` | ambientCG | dark walnut (unused) | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:150` |
| `Wood066` | ambientCG | walnut joinery (unused) | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:84` |
| `Wood094` | ambientCG | light oak (unused) | $1.00\text{ m}$ (assumed tile) | `ops/workstation/library-manifest.json:90` |
| `WoodFloor041` | ambientCG | floor planks (unused) | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:12` |
| `WoodFloor051` | ambientCG | light oak planks (unused) | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:54` |
| `Carpet001` | ambientCG | rug (unused) | $1.00\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:60` |
| `Fabric019` | ambientCG | bedding weave (unused) | $0.20\text{ m}$ (assumed tile) | `ASSUMED` | `ops/workstation/library-manifest.json:24` |

---

## Audit Findings and Flagged Gaps

### 1. Materials with No Basis (`NONE`)
- **`brass`**: Procedural flat shader with `base_rgb=[0.80, 0.62, 0.34]`, `reflectance=0.62`, `roughness=0.3`, `metallic=1.0`. No product alloy specification, brushed finish sample, or reflectance record cited.
- **Revit CAD Paint Hues**: In raw Revit extracts, paint colors are exported as .NET RGB bytes without reflectance or roughness data, falsely treated as finishes (`l0028`).

### 2. Conflicting Values in Two Places
- **`alu-bronze` vs Dark Bronze Name**: Defined as "dark bronze anodised aluminium", but historical draft set assigned `reflectance=0.42` (`base_rgb=[0.55, 0.45, 0.35]`), creating a pale tan finish instead of dark bronze (`l0084`). Corrected in `M` to $\rho = 0.09$, but requires continuous guard enforcement.
- **`glass-clear` vs `pe-bath-screen`**: Standard window glass specifies $\tau = 0.70$ (`Metric Handbook p. 9-8`), whereas bath screen specifies $\tau = 0.91$ with $\eta = 1.52$. Reusing generic window glass on the bath screen caused darkness and excessive reflection (`l0910`).

### 3. Texture Scale and Orientation Not Tied to Real Dimensions
- **Wood Grain Alignment**: Standard `walnut` and `oak` specify `grain_axis="z"`. When applied to horizontal surfaces (e.g., stair treads, bedside shelves, wardrobe side panels), the box projection rotation collapses one coordinate into the member's normal axis, smearing the texture into a single texel streak (`l0083`, `l0795`). Resolution requires dedicated variants (`walnut-grain-y`, `walnut-grain-x`, `oak-grain-x`).
- **ambientCG Textures**: 25 textures lack published physical scan bounds; tile dimensions ($s = 0.3\text{ m}$ to $2.0\text{ m}$) are design assumptions rather than physical facts.

### 4. Glass and Transmission Values Not Tied to Records
- **`glass-guard`**: Stated as $\tau = 0.85$ for laminated balustrade, but lacks cited manufacturer optical cut sheet and IOR value.
- **`detail-pe-bath-screen` Zero-Thickness Trap**: Originally built as a single-quad surface with $\text{interfaces}=1$, trapping rays in Cycles' glass BSDF and rendering as a mirror (`l0049`, `l0910`). Must enforce closed physical solids with $\text{interfaces}=2$.
