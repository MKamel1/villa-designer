# L2 design model

One placed-object record per element of the D1 villa, using `archpipe.contracts.DesignElement` (v0, unchanged).

## Load it

```python
from archpipe.model import load, counts, validate
els = load("D1")             # list[DesignElement]
counts(els)                  # {'beam': 24, 'column': 9, ..., 'wall': 36, 'window': 8}
```

`load()` takes the first of: explicit `path=`, `out/model/d1-elements.json`, the committed snapshot
`src/archpipe/model/data/d1-elements.json`, then `generate()` (minutes). Other lanes' worktrees have no `out/`,
so they read the committed snapshot. Regenerate with:

```
PYTHONPATH=src python -m archpipe.model.export --snapshot     # slow: lighting 1 min + garden plan 5 min
```

The JSON file is `{schema: "archpipe-model/1", contract, design, units: "mm", levels, counts, elements: [...]}`;
`model.load_json(path)` reads it back. `model.validate(els)` returns a list of problems (empty = well formed).

## Semantics (what L2 fixes for the other lanes)

- Units: millimetres. `placement` is the reference point; `size` = (w, d, h) of the bounding box.
- Levels: `B`, `GF` (our two storeys), `L1` / `ROOF` (reserved, no elements yet), `SITE` (garden ground, context).
  `placement.z` is measured from that level's finished floor. Absolute z comes from `levels` in the JSON:
  scene datum GF FFL = 0 and B FFL = -3000; the Revit datum is 1200 mm higher (spec level names "B -1.80",
  "GF +1.20"). Contract text says B is "-1.80": that is the Revit elevation.
- Walls/doors/windows: wall `placement` = midpoint, `rotation_deg` = direction, `size` = (length, thickness, height).
  Doors/windows reference the nearest wall on their level in `host` (within 150 mm; empty when none).
- Rooms: `id = "room-<rid>"`; `room` fields on other elements hold the plain `<rid>`. `params` carry `polygon_mm`,
  `area_m2`, `clear_height_mm` (finished ceiling at the room centre from `villa_lighting.ceiling_z`; sloped soffit rooms
  under the ramp report the centre value), `clear_rect_mm` (floor clear of walls), `open_to`, `finish_codes`
  (floor/wall/ceiling material codes from `villa_render.FINISH`).
- Stair: `params` risers 17, treads 16, `riser_mm` 176.47, `tread_mm` 280, `width_mm` 950, rise 3000, per-tread boxes.
  Railings carry `guard_height_mm` (900 stair glass and wall handrail; 1100 ramp edge) and `host = "stair-main"`.
- Luminaires: `params.photometry` = {manufacturer, code, ies (repo-relative `out/villa/render-d1/ies/...`), substitute,
  generic}; `flux_lm`, `watts`, `cct_k`, `beam_deg`, `layer`, `mount`, `illuminance_card`; `product_id = "<mfr>/<code>"`.
  `placement.z` is the emitter height above the level FFL.
- Plants: species, bed, layer, spread. Gardens: beds, paths and the sunken north patio (`params.sunken`).
- `context`: neighbours, fences, core, street, apartment (villa_env boxes; not ours, for sun and sight-line studies).

## Coverage (D1 snapshot, 515 elements)

| kind | count | source |
|---|---|---|
| room | 30 | `villa_r11.design` rooms (B 17, GF 13) |
| wall | 36 | `revit_spec.build` walls |
| door / window | 18 / 8 | `revit_spec.build` doors, windows |
| stair / railing | 1 / 5 | `revit_spec` stair boxes, balustrades, ramp-edge rails |
| slab | 3 | ramp, deck, extension roof |
| column / beam | 9 / 24 | `villa_env` |
| context | 58 | `villa_env` |
| furniture | 80 | `villa_furnish.layout` (52) + `villa_render.props` dressing (28) |
| fixture | 7 | `revit_spec` bath fittings and wet zones |
| luminaire | 142 | `villa_lighting.design` + `fixture_record` |
| plant / garden | 80 / 14 | `villa_landscape.build` plan |

## Gaps (known, not hidden)

- Furniture, luminaires and plants come from their generators, not from the final built scene. The ~14 build patch
  passes (C4 mounting moves, WC slides, family relocation, furniture stage 2, bed replacement, garden swing/G4d/G6) are
  not reflected: small positional moves, replaced assets (real glTF products for the stand-ins) and garden structures
  (pergola, trough, swing, uplights) are missing from the model. Phase 2 moves them into data.
- No `device` elements (sockets, switches): L7 owns placement. No separate `slab` per floor and no ceilings; the
  false-ceiling and cove heights are room parameters.
- The GF stair-void guard (built in `villa_render`, "required, not yet in the Revit model") is not a railing element.
- `windows` lists only the spec's windows; glazed doors are doors. `host` is geometric (nearest wall), not a Revit id.
- Plant height is not recorded (the garden plan has spread only). Furniture `product_id` is empty where the layout
  uses a procedural stand-in.
- `L1` / `ROOF` levels carry no elements (the apartment above is not ours; the roof garden is `SITE`).

## Proposed contract changes (not applied; contracts.py is the lead's)

1. `DesignElement.level` doc: say "B" is -3000 in the scene datum and -1800 in Revit; add a `levels` table record.
2. Add `polygon: tuple[tuple[float, float], ...] = ()` for rooms/slabs/gardens (now `params["polygon_mm"]`).
3. Add `photometry: str = ""` for luminaires (now `params["photometry"]["ies"]`), and `layer`/`zone` so L6 zones can
   reference elements.
4. Add kinds `garden` and `context` to the documented list.
