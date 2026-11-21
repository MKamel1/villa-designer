# L6b lessons (villa lighting)

## Verification-round defects (2026-11-21)

| defect | why it was missed | guard now |
|---|---|---|
| `Villa().cluster_room("GF-parents-bed")` was the 1.0 x 0.68 m entry: `union_rects` followed one outline and dropped the bedroom 50 mm away. Every bedroom number (pillow planes, room plane) came from a wrong volume. | The cluster outline was never compared with the model's rooms; a bedroom lit at 143 lx looked plausible and the pillow planes had no sensors failing loudly. | `union_rects` bridges gaps <= 60 mm and raises if the rectangles still form more than one outline; `test_every_cluster_room_area_equals_the_design_model_room_area` (all 13 clusters vs `archpipe.model.load("D1")`, 1 %). |
| Sensors inside or under objects (rails, shower, bath, chairs, bowl), basin and sink planes off their surface. | Planes were set out from design footprints and nominal heights, never tested against the built geometry. | `knowledge/lighting/sensor-obstructions.json`: per plane, the cells the independent scene test rejects (object above/inside, or a hole in the host); the engine drops those sensor points; `blocked_rects` raises if a plane moved without regeneration (`villa_sensors_gen`); `test_planes_sit_on_their_hosts_and_keep_sensors_out_of_objects`. |
| Bound-product driver > 1.0 silently clipped to 1.0 (`min(1.0, d)`). | The V12 headroom rule was checked on the table, not on what `apply_drivers` did with it. | `apply_drivers` raises above rated output; `test_driver_above_rated_output_of_a_bound_product_raises`. |
| Results at ab 6 were 4 to 6 % low on small bright rooms. | Convergence was reported, not used. | `villa.AB = 12`; every run also computes ab 24 and the doc reports the table. |
| The lumen-method check said the dressing room was 42 % short. | The closed-form (uniform inter-reflection) is wrong for room index 0.43 and nobody checked the transport by another method. | `radiosity.floor_mean_lux` (independent patch radiosity) agrees with Radiance within 4 % on the dressing room, guest WC, pantry and family bath: `test_radiosity_agrees_with_radiance_on_box_rooms`. |

## Finding for the verification lane (not an L6b file)

LV's scene loader (`lightverify/scene_geom.py:load_scene`) places imported models with `spec["scale"]` (1.0) and ignores
`scale_xyz`, which is what the renderer applies to every fitted model (desks, chairs, bed, vanity). Consequences found when
re-running its sensor test: desks come out 1.1 x 0.45 m and 0.722 m high instead of 1.8 x 0.7 m and 0.750 m, so the
"desk planes 28 mm too high" finding is an artefact (the real desk tops are at 0.750 m, 2 mm under the planes), and the chairs came out
2 m long, producing the "sensors inside chairs" findings. With `scale_xyz` applied the desk and chair findings vanish; the
sink (cutout), basin (bowl recess), rails, shower and bath findings are real and are fixed here.
