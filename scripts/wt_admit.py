"""Local admission of the planned route on the BASE scene (door leaves closed, as built): swing the doors open for this route, then run the villa guards
(no Blender-evaluated meshes, so cloth is not seen). A minutes-long stand-in for prepare + assembly while the stops are being chosen.
usage: python scripts/wt_admit.py [path.json]   (first run: scene base from out/wt/scene-base.json, built by `--build`)"""
import collections, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from archpipe import flythrough as FT
from archpipe.concept import villa_r11 as R, revit_spec as RS
BASE = ROOT/'out/wt/scene-base.json'

if __name__ == '__main__':
    if sys.argv[1:] == ['--build']:
        from archpipe.concept import villa_render as V
        BASE.write_text(json.dumps(V.build(views=[]))); sys.exit()
    path = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else ROOT/'out/wt/villa4/plan-only.json').read_text()); scene = json.loads(BASE.read_text())
    layout = R.design('D1'); spec = RS.build(layout); vm = FT.VillaMap(layout, spec, scene=scene)
    states = FT.open_interior_doors(scene, vm, path['frames'], door_anim=path.get('door_anim'))
    print('closed doors:', [(s['element'], s['reason']) for s in states if s['state'] != 'open' and 'core' not in s['element']])
    g = FT.admit_villa_path(path, scene, layout, spec, None, vm)
    bad = [f for f in g['frames'] if f['failures']]; print(g['summary'])
    print(collections.Counter((path['frames'][f['index']]['room'], tuple(f['swept_obstacles'])) for f in bad).most_common(12))
    json.dump([f["index"] for f in bad], open("/tmp/badidx.json","w")); print(collections.Counter(x[:70] for f in bad for x in f['failures']).most_common(5))
