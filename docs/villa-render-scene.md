# Villa render scene: the contract between the design and the renderer

`src/archpipe/concept/villa_render.py` (laptop, plain Python; owns every design decision) writes
`out/villa/render-d1/scene.json`. `src/archpipe/blender/villa_scene.py` (inside Blender, bpy only; owns no design
decision) builds and renders it. `scripts/villa_render.py` is the driver: deploy to the workstation, render, pull,
QA. The renderer never invents content: anything not in scene.json is not in the image.

## Product furniture and climbers (WP4b)

`villa_furnish.PRODUCT` maps a piece to a library asset and its real width, depth, height, and one native-to-metre
scale derived from `ops/workstation/library-manifest.json`. Native centimetres and millimetres are inferred from
overall size; the Probber chair, kids' chair, and round rug use stated ASSUMED references where native units are
ambiguous. A selected product replaces the generic `w` and `d` in the layout and every furnishing check runs on
that box. A failed clearance, route, door, overlap, kitchen, or facing check retains the procedural piece and
records the first failure. The renderer imports only accepted assets, centres them on the authored piece, seats
them on the floor, and checks the world box against the product footprint plus 20 mm and height within 5 percent.
The hidden procedural mesh remains available for cloth simulation.

`climber_placement.placements` seeds foliage within each landscape climber envelope at a density calculated for
at least 80 percent face coverage, with 70 percent green leaves and 30 percent magenta bracts. The real trellis
envelopes are 0.12 m deep. Blender hides the envelope box and builds the visible leaf geometry; the envelope
remains in the contract and its bounds are tested. A fixed density of 120 pieces per square metre is the failed
round-three reproduction.

Landscape props normally have one uniform scale. The top-garden bench has independent scene-axis scales so its
world box reaches a 1.80 m length along the scene Y axis and a 0.40 m seat height. The scene contract,
Blender importer and landscape world-box calculation accept either form; `bench_violations` checks both dimensions
and its orientation. Reproduce a suspect camera placement with `scripts/villa_render_views.py`, which checks the
four garden views against every prop world box and furniture footprint at a 1.0 m minimum, and checks whether a
tall specimen pot fills the foreground. The historical v26 camera fails proximity and the historical v28 camera
fails foreground span even though its lemon pot was farther than 1.0 m away.

## scene.json (`"schema": "villa-render/1"`)

Units metres. Model axes: x street -> garden, y party wall -> east face, z absolute (GF FFL = 0.0, basement FFL =
-3.0, street = -1.2). Faces are planar polygons, counter-clockwise seen from outside (normal = right-hand rule).

```jsonc
{
  "schema": "villa-render/1",
  "id": "D1",
  "north": {"model_y_bearing_deg": 20.0},          // true bearing of model +y (measured, villa_climate.ROTATION)
  "library_root": "$HOME/archpipe/assets/library",   // on the workstation; materials/<asset>/ (ambientCG layout)
  "materials": {
    "<name>": {
      "kind": "principled" | "glass" | "emissive" | "translucent",
      "asset": "WoodFloor051",           // optional PBR set in library_root/materials/<asset>/ (Color, Roughness,
                                         //   NormalGL, optional Displacement); absent -> flat base_rgb
      "base_rgb": [0.8, 0.78, 0.74],     // LINEAR rgb; with an asset, the texture mean is scaled per
                                         //   linear colour channel to the stated base colour
      "reflectance": 0.80,               //   target linear luminance of that colour; output is bounded to 1
      "roughness": 0.6, "metallic": 0.0,
      "tile_m": 1.2,                     // real-world size of one texture tile, box/triplanar in OBJECT space
      "grain_axis": "x" | "y" | "z",     // optional: plank / grain direction
      "transmittance": 0.70,             // glass: normal transmittance (shadow/diffuse rays pass, as
                                         //   photoreal.architectural_glass), translucent: opal shade diffuse transmission
      "emission_lm_per_m2": 0,           // emissive: real luminous exitance from outward faces, in lumens/mÂ²
      "cct_k": 2700,
      "note": "what product / finish this stands for"
    }
  },
  "meshes": [
    {"id": "shell-0001", "group": "shell" | "context" | "furniture" | "fixture" | "dressing" | "ground",
     "material": "<name>", "room": "kitchen" | null, "label": "text for captions",
     "layer": "ambient" | "task" | "accent" | "decorative" | "night", // optional; switches emissive output
     "keep_object": false,             // optional; true prevents material-based batching
     "bevel_m": 0.006,                  // optional; edge bevel width in metres, 0 to 0.05; keeps its own object
     "subdivide": 1,                   // optional; Subdivision Surface levels, integer 0 to 2; keeps its own object
     "visibility": {"camera": true, "shadow": true, "diffuse": true,
                    "glossy": true, "transmission": true}, // optional per-ray overrides
     "faces": [[[x, y, z], [x, y, z], [x, y, z], ...], ...]}
  ],
  "props": [                            // optional dressing, never design geometry
    {"id": "p-kitchen-vase", "asset": "brass_vase_03", "position": [x, y, z],
     "rotation_deg": [0, 0, 90], "scale": 1.0, "label": "dressing: brass vase"}
  ],
  "lights": [
    {"id": "L-K-01", "room": "kitchen", "layer": "ambient" | "task" | "accent" | "decorative" | "night",
     "type": "ies" | "area" | "line",
     "position": [x, y, z],              // the EMITTER (ies: photometric centre; area: centre of the emitting face)
     "aim": [0, 0, -1],                  // ies: photometric nadir direction; area/line: emitting normal
     "spin_deg": 0,                      // rotation about aim (C0 plane direction), ies only
     "ies": "iguzzini/451g_l73t.ies",    // relative to the bundled ies/ folder shipped with the job
     "lumens": 650, "cct_k": 2700, "cri": 90,
     "size": [0.02, 1.6],                // area/line: width x length of the emitting face, along "length_dir"
     "length_dir": [1, 0, 0],
     "spread_deg": 120,                  // area only (Cycles area spread)
     "product": {"manufacturer": "iguzzini", "code": "451G", "generic": false},
     "dimmer": 1.0}                      // fraction of full output this scene state uses (stated, per view below)
  ],
  "views": [
    {"id": "v01-kitchen-garden", "title": "Kitchen island to the garden", "state": "day" | "evening" | "night" | "exterior-dusk",
     "when": "2026-10-15T15:30:00+03:00",
     "sun": {"altitude_deg": 32.1, "azimuth_true_deg": 231.0},     // computed on the laptop (archpipe.solar)
     "camera": {"position": [x, y, z], "target": [x, y, z], "lens_mm": 24, "sensor_mm": 36,
                "shift_x": 0.0, "shift_y": 0.0,
                "home_room": "kitchen", "reframed": false},       // false, true (moved within room), or "doorway"; level camera
     "resolution": [1920, 1280],
     "layers_on": ["ambient", "task", "accent", "decorative"],       // lights and layered emissive meshes
     "dimmers": {"ambient": 0.6},                                   // optional per-layer scale for this view
     "exposure": "day",                                               // any named key into "exposure"
     "subjects": ["k-island", "dining-table"],                      // entire subject footprints must fit
     "hide_meshes": ["door-leaf-001"],                             // optional: door open for this view only
     "caption_notes": ["Door open for this doorway view."],         // optional: shown in caption
     "samples": 1024, "max_bounces": 16}                            // max_bounces optional
  ],
  "cloth": [{"id": "duvet-bed", "material": "bedding-white",
             "center": [x, y], "size": [width, length], "z_start": z,
             "colliders": ["furn-bed-"], "pin": ["y", 0.55, 0.03], // axis, head-side coordinate, band width
             "cut": {"foot_overhang_m": 0.30, "side_overhang_m": 0.30,
                     "head_to_pin_m": 0.55},
             "bunk": false, "mattress_top": z,
             "label": "dressing: duvet (cloth)"}],
  "exposure_mode": "set-metered",
  "exposure": {"day": {"ev100": 9.0, "white_balance_k": 5500},
               "evening": {"ev100": 3.5, "white_balance_k": 3200},
               "night-lamps": {"ev100": 0.0, "white_balance_k": 3200}},
  "sky": {"day": "nishita", "evening": {"hdri": "belfast_sunset_puresky.exr", "horizontal_lux": 400},
          "night": {"hdri": "dikhololo_night.exr", "horizontal_lux": 0.3}},
  "notes": ["stated assumptions that must appear in every caption"]
}
```

## Renderer rules (villa_scene.py)

- Merge shell, context and ground meshes that share a material and ray-visibility settings. Keep separate objects
  for furniture, fixtures, dressing, emissive meshes and any mesh with `keep_object: true`, `bevel_m` or
  `subdivide`. A `bevel_m` value above zero adds a two-segment, angle-limited Bevel modifier at 30 degrees with
  hardened normals. A `subdivide` value above zero adds a Subdivision Surface modifier at the stated viewport and
  render level, after Bevel when both are present. Detailed meshes are shaded smooth by angle at 30 degrees.
  Subject framing still
  uses each original mesh's own bounding box, matching its id prefix, label or room. Box/triplanar texture mapping
  uses object-space metres scaled by `tile_m`, without UV unwrapping. Per-mesh `visibility` sets Cycles camera,
  shadow, diffuse, glossy and transmission ray visibility; omitted flags default to true.
- Emissive meshes **light the scene** and stay visible to camera and glossy rays unless visibility explicitly
  disables them. `emission_lm_per_m2` is luminous exitance: emitted flux equals exitance times emitting area.
  For a flat mesh, the counter-clockwise front face emits into one hemisphere. For a closed mesh, all outward
  faces emit, so its entire area counts. Lambertian radiance is exitance divided by pi; Blender Emission strength
  uses that value because one Blender watt reads as one lumen in the calibrated scene. The light tree and mesh
  multiple-importance sampling are enabled where Blender exposes the mesh flag. An emitting mesh and a matching
  `lights` entry both contribute energy; the design author must avoid counting one luminaire's flux twice.
  An emissive mesh with `layer` emits only when that layer is in `layers_on`, scaled by the view's
  `dimmers[layer]` value (default 1). At zero output it remains in the image as its stated `base_rgb` surface;
  the object is never hidden or rendered black. Each layered emitter gets an independent material instance, so
  two meshes sharing one material can use different layers. An emissive mesh without `layer` always emits its
  stated exitance and ignores `layers_on` and `dimmers`. For non-emissive meshes, `layer` has no rendering effect.
- `translucent` is reserved for non-emitting opal shades.
- `props` are imported from `library_root/props/<asset>/model.gltf` with `photoreal.import_prop`. `position` places
  the asset's lowest point at the stated height; rotation is in degrees about the model X, Y and Z axes, and
  `scale` is uniform. Each view reports imported props; captions list them as dressing, separate from design.
- Glass as `photoreal.architectural_glass` (shadow and diffuse rays pass through `sqrt(Tv)` per face).
- IES lights: Cycles point/spot light with an IES Texture node reading the bundled file; luminous flux set in this
  project's calibrated units (1 W reads as 1 lm, see `build_scene.build_lights`, ADR-0010): the file's shape, the
  spec's lumens. Colour from `cct_k` via `build_scene.kelvin_to_rgb` (linear, not display sRGB).
  Area/line lights: Cycles area light (rectangle), power from lumens by the same calibration, `spread_deg`.
- Day: `photoreal.daylight_world(sun altitude, sun azimuth_true - model_y_bearing_deg)` (Nishita, scaled to lux).
  Evening and night: the respective named high-dynamic-range image scaled to `horizontal_lux`.
  `exterior-dusk` selects `sky.evening`; it can use its own named exposure preset. Only `day` is reported as
  daylight to villa image-quality checks.
- With `exposure_mode: set-metered`, `photoreal.camera_meter` meters each selected view with a fast pre-render;
  the median exposure for each named `view.exposure` state is locked across the selected set. The fixed-exposure
  render remains the comparison image; the renderer also develops a metered view from the same linear render.
  The view report records `locked_ev100` and `view_meter`. Without this mode, the named preset
  `exposure[view.exposure].ev100` is used. White balance is the stated preset; the view transform is AgX.
  Keep the same selected comparison set when comparing locked exposures.
- `view.hide_meshes` hides only the listed mesh identifiers in that view, used to open a doorway leaf;
  `view.caption_notes` appears in the driver caption. `camera.home_room` names the authored room;
  `camera.reframed` is false if unchanged, true if moved within the room, or `"doorway"` if moved
  to its door opening. Optional `camera.lens_basis` records the measured reason for a 16 mm lens.
  The D1 views guard checks whole subject footprints and doorway clearances before rendering.
- `cloth` describes a sheet simulated onto its named collider parts. `cut` records the authored head pin
  and foot/side overhang; `bunk` records the rail-constrained cut, and `mattress_top` records the measured
  starting surface. The current Blender cloth function uses size, centre, start height, pin and colliders for
  simulation; cut, bunk and mattress_top are exporter evidence, not independent renderer controls.
- Per view: set layers/dimmers and optional `max_bounces` (default 16), place the camera (level, lens shift),
  render with OptiX on the GPU, OpenImageDenoise, light tree on, direct and indirect clamping disabled,
  sixteen diffuse, transmission and transparent bounces and eight glossy bounces,
  write `<view>.png` and `<view>.json` (samples, render time, lights on, subjects in frame via
  `world_to_camera_view`, imported props, fraction of pixels at clipping, mean luminance).
- `--calibrate` also renders a diffuse floor card lit by an emissive sphere of 0.3 m diameter and 800 lm total
  output. At the card directly below it, the point-source comparison is illuminance E = I h / dÂ³, where I is
  800 divided by four pi candela, h is the source height above the card, and d is the source-to-card distance.
  `calibration.json` records analytic and Blender illuminance and whether they agree within 10 percent.
  `--views none --calibrate` runs only the isolated probes, without loading villa geometry, props or sky. The
  synthetic generator accepts `--ies-source assets/ies/Downlight_LED.IES` in a deployed workstation release.
  The prior workstation IES probe measured 167.25 lx against 172.75 lx analytic (3.2 percent) and an exposure
  value at sensitivity 100 of 6.11 for 172 lx. The emissive-sphere probe has not yet been measured.
- No random dressing; every prop must be in `scene.json`.

## Driver (scripts/villa_render.py)

Before exporting real furniture models, place their measured footprints in
`villa_furnish.layout()` and rearrange the table, seats, and routes around
them. Run every furnishing check on the final arrangement. A model is placed
only when the measured layout passes; an approved procedural arrangement
keeps an explicit `product_rejected` reason when the real model cannot fit.
The living room's former coffee position is a regression case because it
fails the real sofa's front clearance.

`--scene out/villa/render-d1/scene.json --views all|v01,v02 --samples N --res WxH [--host ai-workstation]`:
deploy with `scripts/workstation.deploy`, push scene.json and the IES files it names, run Blender headless on the
workstation, pull PNG + JSON into `out/villa/render-d1/`, run `archpipe.render_qa.check` where it applies, and
write `<view>.caption.json` (what is design, what is assumed, generic photometry and dressing named). Villa QA
passes `daylight: true` only for day views. Its report lists the checks applied and names omitted checks that
require bedroom-only metadata, such as measured textiles or bedding.
The driver marks exterior cameras separately. A window seen from outside may be darker than the sunlit exterior;
the indoor window-brightness comparison applies only to interior cameras. Window detail and clipping checks still
run for both. The v25 exterior draft is the regression for this scope rule. The indoor brightness check allows a
0.02 luminance sampling tolerance; v01 measured 0.80 through the window against 0.81 elsewhere in the room.
The driver also accepts `--views none --measure-lighting` and returns
`lighting-measurements.json`. It accepts `--views none --calibrate` and retrieves `calibration.json`, the white-card PNG and both
linear probe images as OpenEXR files.

