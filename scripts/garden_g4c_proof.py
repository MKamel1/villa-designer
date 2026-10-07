"""Record actual-chair sightline mutations from an explicitly exported scene.

All positions/lengths are metres, yaw is counterclockwise degrees about z.
Writes diagnostic evidence only; never modifies an extract or render scene.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from archpipe.concept import garden_swing as S


def proof(scene):
    record=scene['north_swing'];parts=[m for m in scene['meshes'] if m.get('hanging_swing')]
    cones=record['lounge_view_cones'];centres=record['opening_centers_m'];garden=cones[0]['garden_center_m']
    moved=deepcopy(record);moved['center']=[3.,centres[0][1]];front,_=S.build(moved)
    rotated=deepcopy(record);rotated['yaw_deg']=(rotated['yaw_deg']+180)%360;back,_=S.build(rotated)
    mutant=deepcopy(scene);mutant['meshes']=[m for m in mutant['meshes'] if not m.get('hanging_swing')]+back
    findings=S.seat_findings(mutant,rotated)
    result=dict(clean=S.scene_findings(deepcopy(scene)),lounge_cones=cones,seat_cone=record['seat_view_cone'],
        motion_envelope_m=S.envelope(parts,record),decision=record['decision'],
        in_front_of_lounge_door=dict(record=moved,failures=S.view_findings(front,moved,centres,garden)),
        seat_facing_house=dict(record=rotated,failures=findings,evidence=mutant['swing_view_evidence']),
        clean_seated_evidence=scene['swing_view_evidence'])
    result['passed']=not result['clean'] and bool(result['in_front_of_lounge_door']['failures']) and any('central field filled' in f[1] for f in findings)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,default=Path('out/garden-g4c/scene.json'))
    parser.add_argument('--output',type=Path,default=Path('out/garden-g4c/mutation-proof.json'))
    args=parser.parse_args();result=proof(json.loads(args.scene.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('G4c view mutation proof:', 'PASS' if result['passed'] else 'FAIL')
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
