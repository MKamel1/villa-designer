"""Door states of a plan on the BASE scene (stand-in for the assembly's door-states.json): usage: python scripts/wt_states.py <plan.json> <out.json>"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from archpipe import flythrough as FT
from archpipe.concept import villa_r11 as R, revit_spec as RS
scene = json.loads((ROOT/'out/wt/scene-base.json').read_text()); layout = R.design('D1'); spec = RS.build(layout); vm = FT.VillaMap(layout, spec, scene=scene)
path = json.loads(Path(sys.argv[1]).read_text()); st = FT.open_interior_doors(scene, vm, path['frames'], door_anim=path.get('door_anim'))
Path(sys.argv[2]).write_text(json.dumps(st, default=str)); print([(s['element'], s['state']) for s in st])
