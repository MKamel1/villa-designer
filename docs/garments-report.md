# Dressing-room garments — C3 package

The renderer now builds 235 closed physical dressing parts: 25 hanging garments
with hangers on five rails, 76 separate folded textile pieces, ten filled drawers
with trays and four divided inserts, eight lidded upper boxes, and two shoe pairs.
Structural wardrobe plinths, dividers and backs remain. Native furniture inputs,
wardrobe footprints, doors, existing cameras, beds and furniture integration files
were not changed. No garment uses a proxy exemption or cloth simulation.

C3 means closed, outward solid admission with declared axes; C4 means mounting
and support; C8 means geometric relationships. Here x runs along the rails,
y crosses the wardrobe depth, and z points upwards. Coordinates are metres; mm means millimetres.
Colours, stock choices, cloth relief, thickness, pitch and unsourced dimensions
are labelled ASSUMED. These are owned procedural appearances, not specified
manufacturer products.

| Rail | Measured length | Garments |
|---|---:|---|
| Hers, long hang | 600 mm | 4 dresses + 3 abayas |
| Hers, upper double hang | 400 mm | 2 shirts + 2 jackets |
| Hers, lower double hang | 400 mm | 4 folded trousers |
| His, upper double hang | 500 mm | 3 shirts + 2 jackets |
| His, lower double hang | 500 mm | 5 folded trousers |

Packing uses ASSUMED 85 mm centres and a maximum 58 mm cloth envelope, leaving
at least 27 mm between independent garment envelopes. Counts derive from the
measured rail length; no edge garment is narrowed to fit. His six authored drawer
fronts now each have contents; the earlier renderer showed only four. Closed
fronts remain closed in room views. Front-omitted insert previews are diagnostics.
Upper boxes start on the live 2.102 m shelf surface and finish at 2.248 m.

The held Neufert original was reread: *Architects' Data*, 2nd International English
edition (1980), printed p.74, Fig.6, “Dimensions of clothes”. The existing card
`neufert-longhang-drop-1600` gives dress drops 1450–1600 mm and jackets 850 mm.
This build uses dresses 1530 mm, abayas 1580 mm (ASSUMED analogy to dresses),
jackets 850 mm, and shirts 840 mm (ASSUMED; not stated in that figure).
The same drawing gives folded men's trousers 900 mm, distinct from full hanging
at 1300 mm. The new [verified card](../knowledge/garment-dimensions.json) and its
regression replace the inherited 680–720 mm assumption. This conservative folded
drop is used on both partners' lower rails. The smallest modeled shoe-to-trouser
vertical gap is 2 mm; none intersects. Household inventory and the existing
per-person minimum of 1.0 m rail / four drawers remain ASSUMED in `villa_furnish`.
This package does not certify actual household capacity or fixing load capacity.
Checks cover the static closed-front state; opening motions are not simulated.

Construction now gives sleeves, neckline and pleats closed skins with thinner
hems and folded bulk; trouser legs taper below the fold. Shelf textiles have
separate rounded folds. Shoes have closed soles and a closed leather shell around
a visible opening. Hanger members follow the textile shoulder datum, rather than
entering its volume, and each saddle contacts its actual rail. Contents have
named, acyclic contact chains to live floor-bearing joinery. The ten old bracket
approval rows are retired only by exact frozen value in the new contents contract;
they remain available to historical callers and cannot approve the new shapes.

The real l0923 input is frozen by value in
[the reproduction](../tests/fixtures/l0923-dressing-before.json.gz).
The first fix exposed two more failures: constant-thickness garments looked like
planks in the unchanged cameras, and the triangular hanger bar entered the textile.
The actual pair/body is frozen in
[the first-fix reproduction](../tests/fixtures/garment-hanger-before.json.gz).
Construction fixes and independent morphology, contact and solid-interior checks
now cover these failures. Narrowing the trouser hem also exposed an oversized
fixed corner radius; [its actual cap](../tests/fixtures/garment-rounded-profile-before.json.gz)
is frozen by value. Rounding now derives from both section dimensions and actual
cap-edge checks reject self-crossings, which closed edge tables alone had missed. Renamed/translated real siblings, injected defects and
clean cases are in [test_garments.py](../tests/test_garments.py).

Neutral preview paths (all from the final saved scene; no presentation images):

- [v31: hers](../out/garments/context/v31-dressing-hers-neutral.png)
- [v32: his](../out/garments/context/v32-dressing-his-neutral.png)
- [Whole hers wardrobe, 1.8 m reference](../out/garments/isolated/hers-wardrobe.png)
- [Whole his wardrobe, 1.8 m reference](../out/garments/isolated/his-wardrobe.png)
- [Dress](../out/garments/isolated/dress.png), [abaya](../out/garments/isolated/abaya.png),
  [shirt](../out/garments/isolated/shirt.png), [jacket](../out/garments/isolated/jacket.png),
  [folded trousers](../out/garments/isolated/trousers.png), each with the 1.8 m reference
- [Folded sportswear](../out/garments/isolated/folded-sportswear.png),
  [folded knit hat](../out/garments/isolated/folded-knit-hat.png),
  [lingerie insert](../out/garments/isolated/lingerie.png),
  [scarf insert](../out/garments/isolated/headscarves.png),
  [shoe](../out/garments/isolated/shoe.png), [lidded box](../out/garments/isolated/lidded-top-box.png)
- [Measurements](../out/garments/measurements.json),
  [isolated receipts](../out/garments/isolated/isolated-preview-evidence.json),
  [context receipts](../out/garments/context/context-preview-evidence.json)

Only v31/v32 are current dressing cameras; the duplicate v14 is retired.
Their crops do not show every upper box, shoe or drawer, so whole-wardrobe and
insert specimens supplement them. Diagnostic lighting disables design emission
and adds two recorded white 350 W, 1 m area sources; the cameras and geometry
retain their authored values. Earlier previews in `first-fix`, `sleeved-first-fix`,
`final-samples` and `rejected-context` are superseded diagnostics. The revised
existing-camera checkpoint is under `profile-checkpoint`. Local image review is
recorded in `out/garments/preview-review.json`; lead visual acceptance remains open.

Resume audit confirmed that the saved scene's 235 contents parts and module
receipts exactly match the current builder. All 15 preview receipts match their
source geometry; isolated receipts also match their materials and lights, and
context cameras match the saved scene. The local review records image hashes.
Simplified textile detail and small folded/shoe specimens limit appearance
judgement; the neutral fill washes the light fabrics.

A separate shared-importer defect remains OPEN: the neutral context reader
reports nine false negative-volume reversals on small hanger/bracket solids.
Single-precision arithmetic at their world position changes the volume sign;
double precision or evaluating relative to a local origin preserves the source's
outward winding. [Actual source cases](../tests/fixtures/garment-importer-precision-before.json.gz)
and [measurements](../out/garments/importer-precision.json) are preserved, with a
reproduction in `tests.test_garments`. This does not invalidate source C3 admission,
but the integration lead must fix and verify the shared importer before accepting
its winding or presentation output. That file is in Codex-B's model-import scope
and was not edited. Design geometry must remain fixed.

Validation, judged by process exit status with NO_COLOR=1:

- The requested dressing/furnishing, render-standard and render-view batch passed:
  134 tests, exit 0 ([log](../out/garments/acceptance-tests.log)).
- The final garment, adapter and affected render regressions passed: 24 tests,
  exit 0, including the complete-scene no-floating check
  ([final log](../out/garments/final-garment-tests.log)).
- `scripts/verify.py --portable` passed with normal and empty HOME, both exit 0;
  recorded in
  [normal log](../out/garments/verify-normal.log) and
  [empty-HOME log](../out/garments/verify-empty-home.log).
- The canonical skill adapters were regenerated; `sync_agent_assets.py --check`
  and `tests.test_agent_assets` passed. The lead runs the full suite.
- Resume checks passed: 27 garment/support, adapter and strict physical-part
  tests, exit 0 ([focused log](../out/garments/resume-focused-tests.log)); after
  adding the shared-importer reproduction, all 13 source tests passed, exit 0
  ([source log](../out/garments/resume-source-tests.log)). Production geometry
  is unchanged from the completed acceptance batch. Normal portable verification
  was repeated, exit 0 ([resume log](../out/garments/resume-verify-normal.log));
  the empty-HOME repeat also passed, exit 0
  ([resume empty-HOME log](../out/garments/resume-verify-empty-home.log)).
  [Resume validation record](../out/garments/resume-validation.json) records
  the exit statuses and pending integration items.

[Repeatable workflow](ops/garments.md) and `scripts/garments_evidence.py` support
small candidate previews before expensive acceptance, then fresh final receipts.
No shared symlink data was modified. No commit was made. This remains a capability
example and does not approve a real villa design gate.

lessons to register: `l0923-garments-physical-contents` → `garments.build`,
`contents_findings`, `profile_findings`, `sleeve_findings`, `hanger_penetrations`
`contact_gap` and `horizontal_profile_findings` → `tests.test_garments.PhysicalGarments` /
`FreshDressingScene` → scene construction/export and Stage 7 neutral review;
include the exact historical-approval retirement and the new 900 mm source card.
The integration lead owns `guard_registry.py` and its tests; they were not edited.
Also track `garments-importer-volume-precision` as OPEN in the shared-importer
package; its reproduction is evidence of the defect, not an implemented guard.
