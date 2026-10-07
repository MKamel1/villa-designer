---
document_outline:
  - title: Executive Summary
    link: "#executive-summary"
  - title: Class C7 Audit and Inventory Summary
    link: "#class-c7-audit-and-inventory-summary"
  - title: Material Basis Check Rules and Lesson Mapping
    link: "#material-basis-check-rules-and-lesson-mapping"
  - title: Frozen Real Defect Cases and Sources
    link: "#frozen-real-defect-cases-and-sources"
  - title: Known-Findings Baseline
    link: "#known-findings-baseline"
  - title: Phase 2 Scope and Migration Requirements
    link: "#phase-2-scope-and-migration-requirements"
  - title: Exact Files Changed
    link: "#exact-files-changed"
  - title: Fix Round 1
    link: "#fix-round-1"
executive_summary: >
  Phase 1 of Lessons Class C7 ("appearance lacks verified basis") audits all 54 static scene materials,
  detail elements, and asset library textures, binding visible surfaces to physical optical bounds.
  A fail-closed verification check directly calls production data authorities without re-implementation,
  freezing a 5-item known findings baseline and proving detection on historical defect fixtures while
  leaving active production material values unmodified.
---

# C7 Phase 1 Report: Material Appearance Basis

## Executive Summary

Phase 1 of Lessons Class C7 ("appearance lacks verified basis") establishes the optical basis inventory and fail-closed verification tooling for all visible surfaces in the villa pipeline. Guided by the class rule in [docs/lessons-audit.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) ("Bind visible surfaces and models to verified product and optical records"), this phase:
1. Conducted an inventory of all 54 static scene materials in [`archpipe.concept.villa_render.M`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_render.py#L90-L150), dynamic emitters, detail element specifications in [`revit_spec.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/revit_spec.py), and 37 asset library textures, documenting status as `VERIFIED`, `ASSUMED`, or `NONE` in [docs/material-basis.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/material-basis.md).
2. Implemented the single fail-closed check [`material_findings`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/material_basis.py#L220) and [`assert_material_basis`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/material_basis.py#L619) in [`src/archpipe/material_basis.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/material_basis.py), strictly calling production data authorities ([`archpipe.concept.villa_render.M`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_render.py#L90), [`archpipe.blender.grain.mapping_rotated_span`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/blender/grain.py#L27), [`archpipe.blender.build_scene.kelvin_to_rgb`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/blender/build_scene.py#L165), and [`archpipe.villa_render_contract.emission_strength`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py#L34)).
3. Froze a baseline of 5 known non-fatal warnings on active production materials by value in [tests/fixtures/c7_known_findings.json](file:///C:/Users/mmbka/arch-pipeline-agy/tests/fixtures/c7_known_findings.json) so current models stay quiet while any new optical violations fail closed.
4. Created comprehensive regression proofs in [tests/test_material_basis.py](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py) validating 12 frozen historical defects and renamed/translated siblings.
5. Registered the guard [`appearance_basis_phase1`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L1553) in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) covering 14 lesson IDs, updating audit coverage arithmetic from 30 to 44 covered guards and 157 to 143 uncovered lessons.

Per Phase 1 constraints, zero active production material values were modified.

---

## Class C7 Audit and Inventory Summary

The material inventory conducted in [docs/material-basis.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/material-basis.md) analyzed all surface definitions across the codebase:

| Category | Total Count | VERIFIED | ASSUMED | NONE (Flagged) |
|---|---:|---:|---:|---:|
| **Static Scene Materials (`villa_render.py:M`)** | 54 | 22 (40.7%) | 30 (55.6%) | 2 (3.7%) |
| **Dynamic Emitters (`build_scene.py`, `villa_scene.py`)** | 6 | 6 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| **Detail Elements (`revit_spec.py`)** | 12 | 2 (16.7%) | 10 (83.3%) | 0 (0.0%) |
| **Asset Library Textures (`asset_manifest.json`)** | 37 | 37 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| **Total Visible Surfaces** | **109** | **67 (61.5%)** | **40 (36.7%)** | **2 (1.8%)** |

### Key Observations and Gaps
- **Verified Basis Records (61.5%)**: Concentrated in architectural wall finishes (Dulux LRV records), CC0 photographic PBR textures from ambientCG and Poly Haven with physical bounding scales (e.g. 2.0 m paving, 1.2 m herringbone parquet), calibrated blackbody emitters (2700 K / 3000 K), and measured glazing records.
- **Assumed Records (36.7%)**: Concentrated in wardrobe joinery variants, bespoke furniture fabrics, dressing garments, landscape gravel/decking, and pool water optics. While physically plausible ($0.02 \le \rho \le 0.90$), they lack direct manufacturer product sheets.
- **Flagged Deficiencies (NONE / Gaps)**:
  1. `brass` (`villa_render.py:122`): Procedural yellow metallic ($[0.91, 0.78, 0.38]$) lacking alloy optical measurement sheet (e.g. CW614N).
  2. `glass-guard` (`villa_render.py:132`): Declares transmittance 0.85 and 2 interfaces without citing standard or IOR specification.
  3. `walnut`, `oak`, `door-oak` (`villa_render.py:92-98`): Default `grain_axis="z"` produces degenerate zero texel span on horizontal members (e.g. shelves, steps) under Box projection, requiring explicit `-grain-x` or `-grain-y` variants.

---

## Material Basis Check Rules and Lesson Mapping

The validation function [`material_findings`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/material_basis.py#L220) executes seven physical validation rules mapped to Class C7 lessons:

| Rule Category | Lesson IDs | Enforcement Mechanism | Production Authority Called |
|---|---|---|---|
| **1. Missing Basis Audit** | `l0028` | Flags materials lacking manufacturer record, standard citation, or physical basis description. | `archpipe.concept.villa_render.M` |
| **2. Reflectance Bounds** | `l0064`, `l0065`, `l0084` | Rejects albedo $\rho < 0.02$ (coal black floor) or $\rho > 0.90$ (snow ceiling). Rejects dark bronze albedo $> 0.40$ and ivory bedding albedo $< 0.20$. | `archpipe.concept.villa_render.M` |
| **3. Saturated CAD Colors** | `l0016`, `l0064`, `l0677` | Fails closed on pure primary/secondary CAD viewport colors (magenta $[1, 0, 1]$, red $[1, 0, 0]$, cyan $[0, 1, 1]$, etc.) with saturation $> 0.95$ and max channel $1.0$. | Color conversion math |
| **4. Texture Real-World Scale** | `l0891` | Requires textured surfaces to specify positive real-world repeat dimensions (`scale_m` or `repeat_m`), rejecting untextured green planes. | Asset library manifest |
| **5. Grain Orientation** | `l0083`, `l0795` | Rejects horizontal grain axis on vertical faces; evaluates Box-projection texel spans and fails on collapsed spans ($u_{\text{span}} = 0$ or $v_{\text{span}} = 0$). | `archpipe.blender.grain.mapping_rotated_span` |
| **6. Glazing Optics** | `l0049`, `l0900`, `l0910` | Enforces whole-pane transmittance $\tau \in (0, 1]$, interface count $\in \{1, 2\}$, closed thickness volumes, and translucent diffuser globe $\tau > 0.40$. | `archpipe.blender.villa_scene.py` |
| **7. Emissive CCT & Exitance** | `l0062` | Verifies CCT $\in [1500, 10000]\text{ K}$, checks linear RGB distance against blackbody curve $\le 0.40$, and checks finite positive emission strength. | `archpipe.blender.build_scene.kelvin_to_rgb`, `archpipe.villa_render_contract.emission_strength` |

---

## Frozen Real Defect Cases and Sources

Every rule is proved against a frozen reproduction by value from historical defect records, paired with a renamed/translated sibling:

1. **`l0016-solid-magenta-box`**: Frozen CAD display color $[1.0, 0.0, 1.0]$ used on plant box placeholder. Proved on `trellis-plant-box` and sibling `creeper-foliage-proxy` ([tests/test_material_basis.py:69](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L69)).
2. **`l0028-revit-paint-hue`**: Raw Revit viewport hue substituted for measured reflectance without product record ([tests/test_material_basis.py:126](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L126)).
3. **`l0049-extracted-glass-solid`**: Glass slab lacking declared whole-pane optical transmittance and interface count ([tests/test_material_basis.py:175](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L175)).
4. **`l0062-whole-room-rendered`**: Emissive fixture specifying warm CCT (2700 K) with contradictory saturated purple RGB or zero exitance ([tests/test_material_basis.py:228](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L228)).
5. **`l0064-pure-red-lamp`**: Revit display shade $[1.0, 0.0, 0.0]$ rendering as saturated CAD lamp ([tests/test_material_basis.py:106](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L106)).
6. **`l0065-ivory-bedding-rendered`**: Authored ivory bedding with unphysical low reflectance $\rho = 0.12$ rendering as dingy dark grey ([tests/test_material_basis.py:280](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L280)).
7. **`l0083-oak-grain-ran`**: Vertical wardrobe door specifying horizontal grain axis `y` ([tests/test_material_basis.py:328](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L328)).
8. **`l0084-dark-bronze-rendered`**: "Dark bronze" specified with pale tan albedo $\rho = 0.58$, exceeding physical bronze ceiling of 0.40 ([tests/test_material_basis.py:375](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L375)).
9. **`l0795-wood-grain-rotated`**: Box-projection coordinate Euler rotation collapsing texel mapping span ($u_{\text{span}} = 0.0$) on horizontal member ([tests/test_material_basis.py:422](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L422)).
10. **`l0891-artificial-grass-rendere`**: Ground cover material lacking real-world texture repeat dimensions ([tests/test_material_basis.py:469](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L469)).
11. **`l0900-island-stair-void`**: Pendant diffuser globe with low transmittance $\tau = 0.25 \le 0.40$ rendering as smoky glass ([tests/test_material_basis.py:516](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L516)).
12. **`l0910-ensuite-bath-screen`**: Zero-thickness single-interface glass mesh causing total internal reflection ([tests/test_material_basis.py:563](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py#L563)).

---

## Known-Findings Baseline

To ensure new optical regressions fail closed while existing active production materials remain usable pending Phase 2, the current findings are frozen in [tests/fixtures/c7_known_findings.json](file:///C:/Users/mmbka/arch-pipeline-agy/tests/fixtures/c7_known_findings.json):

1. `walnut`: Warning on base `grain_axis="z"` collapsing on horizontal members ($u_{\text{span}} = 0.0$); horizontal faces require `walnut-grain-x`/`y`.
2. `oak`: Warning on base `grain_axis="z"` collapsing on horizontal members; horizontal faces require `oak-grain-x`/`y`.
3. `door-oak`: Warning on base `grain_axis="z"` collapsing on horizontal members; horizontal faces require `door-oak-grain-x`/`y`.
4. `brass`: Warning for lacking manufacturer alloy optical cut sheet (e.g. CW614N brushed brass).
5. `glass-guard`: Warning for stating transmittance 0.85 without cited standard or IOR specification.

When executed against the current active scene materials, `assert_material_basis(None)` produces zero ERROR findings and exactly matches these 5 baseline entries.

---

## Phase 2 Scope and Migration Requirements

Phase 2 will replace assumed and procedural values with verified manufacturer product records:

1. **Metal Alloys**: Bind `brass` and `bronze` to measured spectral reflectance records (e.g. CW614N / UNS C38500 brushed brass, $\rho_{\text{specular}} \approx 0.65\text{--}0.75$).
2. **Glazing Systems**: Bind `glass-clear`, `glass-tint`, and `glass-guard` to tested manufacturer glass sheets (e.g. Pilkington Optifloat Clear 6 mm / 10 mm, $\tau_v = 0.89$, $\text{IOR} = 1.52$).
3. **PBR Texture Normal Maps (`l0724`)**: Reintroduce verified photographic normal maps across travertine, limestone, and oak flooring.
4. **Physical Rendering and Simulation Controls (`l0081`, `l0082`, `l0085`, `l0658`, `l0674`)**:
   - `l0081`: Implement pixel-level highlight clipping limit ($\le 3.0\%$) under highlight-priority metering.
   - `l0082`: Implement midtone floor check ($\ge 0.30$ median luminance) to prevent underexposure.
   - `l0085`: Sun contribution scaling from high-dynamic-range environment probes.
   - `l0658`: Transport bounce clamping physics.
   - `l0674`: Physical duvet cloth overhang and edge cut length verification.

---

## Exact Files Changed

The following 8 files were created or modified during Phase 1:

1. [`docs/material-basis.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/material-basis.md) (Created: full material inventory audit across 109 surfaces).
2. [`src/archpipe/material_basis.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/material_basis.py) (Created: optical basis validation functions calling production authorities).
3. [`tests/fixtures/c7_known_findings.json`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/fixtures/c7_known_findings.json) (Created: frozen baseline of 5 known findings on active materials).
4. [`tests/test_material_basis.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py) (Created: regression test suite with 12 frozen defect fixtures and siblings).
5. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) (Modified: imported `material_basis`, exported `check_material_appearance_basis`, registered `appearance_basis_phase1`).
6. [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py) (Modified: updated coverage counts to 44 covered / 143 uncovered, added 14 lesson IDs, added execution test).
7. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md) (Modified: appended `appearance-basis-phase1` learning entry).
8. [`docs/c7-phase1-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/c7-phase1-report.md) (Created: this Phase 1 close-out report).

---

## Fix Round 1

Following test execution outside Blender and Lead audit of initial Phase 1 changes, four findings were addressed in Fix Round 1:

1. **bpy Module-Level Import Isolation (Finding A)**:
   Retained Lead's fix in [`src/archpipe/material_basis.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/material_basis.py), using `_load_blender_functions()` to extract and compile the pure mathematical functions `kelvin_to_rgb` and `_cie1931` directly from production source AST without importing `bpy` at module level.

2. **Replaced Invented Threshold with Production Textile Control (Finding B)**:
   Removed the hard-coded 0.60 reflectance floor on light/ivory textiles, which appeared in no cited source. Connected the check directly to the production [`check_textile_reflectance`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py#L86) control from [`src/archpipe/render_qa.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py) (Lesson `l0065`, [docs/LEARNINGS.md:209](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L209)), which verifies explicit presentation reflectance on textiles and prevents unbacked generic furniture fallback (0.35).
   - Honest re-evaluation of `garment-ivory`: Declares explicit presentation reflectance `rho = 0.55` and natural color `[0.86, 0.83, 0.76]` with documented note (`ASSUMED hanging garment fabric, ivory`). Evaluated under [`check_textile_reflectance`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py#L86), it passes and stays quiet with zero findings.

3. **Scene-Based Grain Orientation Verification (Finding C)**:
   Eliminated speculative warnings on base wood materials (`oak`, `walnut`, `door-oak`) which were previously flagged without confirming usage on horizontal faces. Made the rule strictly scene-based:
   - Audits meshes from the scene definition using [`mapping_rotated_span`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/blender/grain.py#L53).
   - Only meshes possessing horizontal faces (face normal predominantly aligned with Z) while specifying vertical grain axis (`z`) are flagged as errors, reporting the failing mesh IDs.
   - Base materials used only on vertical faces (or unattached to horizontal scene geometry) stay quiet.

4. **Re-Frozen Known-Findings Baseline (Finding D)**:
   Re-evaluated [`material_findings`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/material_basis.py#L182) against active production villa materials [`archpipe.concept.villa_render.M`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_render.py#L44). Corrected baseline in [tests/fixtures/c7_known_findings.json](file:///C:/Users/mmbka/arch-pipeline-agy/tests/fixtures/c7_known_findings.json) to exactly 2 known warnings (`brass` lacking manufacturer alloy cut sheet and `glass-guard` lacking cited standard/IOR specification).

### Files Actually Changed in Fix Round 1

The following 5 files were modified during Fix Round 1:

1. [`src/archpipe/render_qa.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py) (Extracted and exported [`check_textile_reflectance`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py#L86)).
2. [`src/archpipe/material_basis.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/material_basis.py) (Bound to [`check_textile_reflectance`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py#L86), implemented scene-based mesh grain check with `_face_normal` and `_resolve_scene_meshes`, removed speculative grain warnings).
3. [`tests/fixtures/c7_known_findings.json`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/fixtures/c7_known_findings.json) (Re-froze baseline to 2 findings matching actual corrected production output).
4. [`tests/test_material_basis.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_material_basis.py) (Added mesh grain horizontal vs. vertical scene test, updated `l0065` sibling to test missing reflectance, added test verifying `garment-ivory` passes).
5. [`docs/c7-phase1-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/c7-phase1-report.md) (Updated frontmatter outline and added Fix Round 1 report section).
