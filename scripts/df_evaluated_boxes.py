"""World boxes of the Blender-EVALUATED cloth (duvet, throw, curtains) in one room, for the dressed circulation check.

usage: blender -b -P scripts/df_evaluated_boxes.py -- SCENE.json OUT.json ROOM_ID IES_DIR

Builds the scene exactly as a render does (cloth simulated, curtains settled) with --cpu so no GPU is touched, then writes
[{id, lo, hi}] for every cloth/curtain object whose evaluated bounds touch the room's clear rectangle. Nothing is rendered.
Same box format as knowledge/flythrough/evaluated-obstacles.json."""
import json
import sys
from argparse import Namespace
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from archpipe.blender import villa_scene as VS  # noqa: E402

scene_path, out_path, room, ies_dir = sys.argv[sys.argv.index("--") + 1:][:4]
data = json.loads(Path(scene_path).read_text())
from archpipe.blender.element_ids import without_ids  # noqa: E402
from archpipe.concept import villa_furnish as F  # noqa: E402
from archpipe.concept import villa_r11 as R  # noqa: E402
rx0, ry0, rx1, ry1 = F.clear_rect(R.design("D1"), room)


def dump(scene_data, args, env):
    dg = bpy.context.evaluated_depsgraph_get()
    boxes = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.name.startswith(("cloth-", "curtain-")) or obj.hide_render and "closed" in obj.name:
            continue
        ev = obj.evaluated_get(dg)
        mesh = ev.to_mesh()
        pts = [ev.matrix_world @ v.co for v in mesh.vertices]
        ev.to_mesh_clear()
        if not pts:
            continue
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        if hi[0] < rx0 - 0.5 or lo[0] > rx1 + 0.5 or hi[1] < ry0 - 0.5 or lo[1] > ry1 + 0.5:
            continue
        boxes.append(dict(id=obj.name, lo=[round(v, 3) for v in lo], hi=[round(v, 3) for v in hi]))
    Path(out_path).write_text(json.dumps(dict(room=room, boxes=boxes), indent=1))
    print("WROTE", out_path, len(boxes))


args = Namespace(scene=scene_path, views="all", out=str(Path(out_path).parent), ies_dir=ies_dir,
                 library_root=str(Path.home() / "archpipe/assets/library"), samples=None, res=None, cpu=True, calibrate=False,
                 measure_lighting=False, measure_exposure_groups=False, blend_cache=None, walkthrough_callback=dump)
VS.render(without_ids(data), args)
