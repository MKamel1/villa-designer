"""Bounded swing feasibility in the fixed G4 landscape, metres throughout.

A 0.05 m translation grid keeps the retained asset scale and orientation;
this is a bounded feasibility screen, not a continuous optimum proof.
"""
import argparse,copy,json,gzip
from pathlib import Path
import numpy as np
from shapely.geometry import box
from archpipe.concept import villa_landscape as L,villa_r11 as R,revit_spec as RS
from archpipe.concept.garden_render_review import overhead_cover


def measure(scene):
    frozen=json.loads(gzip.decompress(Path('tests/fixtures/garden-g4-before.json.gz').read_bytes()))
    swing=frozen['swing'];rect=L._rect(swing);center=((rect[0]+rect[2])/2,(rect[1]+rect[3])/2)
    meshes,props,_,plan=L.review_candidate(RS.build(R.design('D1')),R.design('D1'))
    obstacles=props+plan['objects']+plan['plants']+plan['boundary_obstacles']+[
        dict(id=name,rect=rect) for name,rect in dict(plan['beds'],**plan['accent_beds']).items()]
    cover=overhead_cover(scene,L.GROUND);counts=dict(sampled=0,open_motion=0,clear_obstacles=0,clear_routes=0)
    accepted=[]
    for x in np.arange(-.3,3.6,.05):
        for y in np.arange(-29.8,-23.65,.05):
            counts['sampled']+=1;p=copy.deepcopy(swing);p['position'][0]+=x-center[0];p['position'][1]+=y-center[1]
            r=L._rect(p);envelope=(r[0]-.25,r[1]-.25,r[2]+.25,r[3]+.25)
            if box(*envelope).intersection(cover).area>1e-6:continue
            counts['open_motion']+=1
            if L.swing_violations(p,obstacles):continue
            counts['clear_obstacles']+=1
            if L.route_violations([p]):continue
            counts['clear_routes']+=1;accepted.append(p)
    return dict(counts=counts,spacing_m=.05,accepted=accepted,orientation_changed=False,scale_changed=False,decision='Omit swing; client to confirm removal' if not accepted else 'Open candidates need full authoritative readback')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--scene',default='out/garden-g4/scene.json');ap.add_argument('--output',default='out/garden-g4/swing-proof.json');args=ap.parse_args()
    report=measure(json.loads(Path(args.scene).read_text()));Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(report['counts']);return 0

if __name__=='__main__':raise SystemExit(main())
