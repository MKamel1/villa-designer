# C3 phase 2a checkpoint

The D1 procedural scene still has 903 mesh records. The diagnostic collector now reports **212 failing records**, down from 632 in phase 1. The full per-record evidence is `out/c3-phase2a-failures.json`. Collection remains enabled for this checkpoint; strict construction still raises on the first rejected part. No design position, layout or camera changed, and no preview was rendered here.

## Cause and control

The phase 1 sink inferred physical kinds from identifiers and labels. That made the library cabinet `BACK` LED strip a book, and hid door leaves, stair stringers and exterior finish behind broad assembly names. Every procedural mesh emitter now supplies its kind; a missing declaration raises even in collection mode. Rectangular solids are admitted only for the approved physical kinds, each with a reason in `physical_part.py`. A declared surface must supply its occupied-side direction; a glass pane cannot use that surface exemption.

The repeated open downlight discs came from `disc_down`, which emitted one face. It now emits a closed shallow disc with the visible underside facing down. The swing shade is a closed thin shell; the desk shade has a bottom face; the stair glass shoe and sloped members use a closed prism. The exterior ground ring's repeated bridge vertices produced the zero-area triangle in shell paving; four non-overlapping quads now cover the same ring.

The new collection has **zero zero-area triangles** and **zero inward-facing light fittings**. One inward-facing solid remains in a suitcase handle (`furn-stair-flight-store-10`), part of the phase 2b luggage replacement. There are 74 records with open or inconsistent edges, 129 with unapproved bare rectangular proxies, and eight with a surface facing error; a record may have more than one reason. These are real failures, not waivers. In particular, 63 `finish-layer` records and 13 `door-leaf` records still need shell face separation or solid construction. The shell material buckets combine faces with different orientation or omit solid edges; declaring the bucket a surface would hide that construction issue. The cove ceiling lip also cannot share the field's one downward occupied-side direction.

## Phase 2b worklist

Counts below are failing procedural mesh records in the D1 collection, except the imported picture frame:

| Recognisable placeholder | Count | Required replacement |
|---|---:|---|
| Climbers | 4 | Branched growth or verified measured assets |
| Trellises | 4 | Actual open frame members |
| Rain-head drops and plates | 4 | Circular shower bodies and nozzles |
| Riser rails | 2 | Tube, slider and hose |
| Shower heads | 2 | Shaped head and outlet |
| Fan grilles | 2 | Louvre and opening geometry |
| Storage boxes | 6 | Lids, seams and handles; inspect grouped bay boxes too |
| Suitcase and luggage stand-ins | 9 | Handles, wheels and measured proportions |
| Wardrobe garment rails | 5 | Closed tube sections |
| Door-pot planters | 7 | Real container geometry |
| Hanging picture frame | 1 imported asset | Artwork and contents review through asset intake |

The phase 2b list is deliberately unmodified. Other red records in the evidence file also require separate construction work before strict mode can become the default.

## Lead preview request

Render `v24-bar-alcove` for the swing heads, `v04-study-deck` and `v08-cinema` for desk shades, and `v23-gf-gallery` for downlight trims and lenses. Compare them with the prior previews at the same cameras, looking for changed visible undersides, dark faces or light leaks. The workstation is required for those images; this checkpoint has code and geometry evidence only.

`NO_COLOR=1` focused part and landscape regressions passed (24 tests), and `tests.test_render_standard` passed (53 tests). `scripts/verify.py` exited 0 with `RESULT: ALL PASS`. No commit was made.
