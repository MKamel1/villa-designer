"""Bounded North Garden swing/bed feasibility with actual model cover.

Coordinates are metres. Keep the swing's orientation and 0.25 m motion
allowance; the 0.05 m translation grid is a declared search, not an optimum
proof. Compare old omitted-boundary guards with current boundary-aware guards.
"""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
from shapely.geometry import box
from archpipe.concept import villa_landscape as L, villa_r11 as R, revit_spec as S
from archpipe.concept.garden_render_review import overhead_cover


def measure(scene):
    lay = R.design('D1')
    meshes, props, _, plan = L.review_candidate(S.build(lay), lay)
    cover = overhead_cover(scene, L.GROUND)
    swing = next(p for p in props if p['asset'] == 'sf_egg_chair')
    rect = L._rect(swing)
    center = [(rect[0]+rect[2])/2, (rect[1]+rect[3])/2]
    counts = dict(sampled=0, clear_cover=0, clear_old_envelope=0,
                  old_all_guards=0, current_all_guards=0)
    obstacles = props + plan['objects'] + plan['plants'] + [
        dict(id='bed-'+name, rect=rect) for name, rect in plan['beds'].items()]
    old_plan = dict(plan, boundary_obstacles=[])
    rejected = []
    for x in np.arange(-.3, 3.6, .05):
        for y in np.arange(-29.8, -23.65, .05):
            counts['sampled'] += 1
            candidate = copy.deepcopy(swing)
            candidate['position'][0] += x-center[0]
            candidate['position'][1] += y-center[1]
            rect = L._rect(candidate)
            # "Out of cover" applies to the actual stand footprint. Motion
            # still clears modeled walls, furniture and planting; overhead
            # sky projection alone is not a solid obstruction at seat height.
            if box(*rect).intersection(cover).area > 1e-6:
                continue
            counts['clear_cover'] += 1
            if L.swing_violations(candidate, obstacles):
                continue
            counts['clear_old_envelope'] += 1
            placed = [candidate if p['id'] == swing['id'] else p for p in props]
            if L.candidate_violations(meshes, placed, old_plan, lay):
                continue
            counts['old_all_guards'] += 1
            failures = L.candidate_violations(meshes, placed, plan, lay)
            if not failures:
                counts['current_all_guards'] += 1
            else:
                rejected.append(dict(swing=candidate, failures=failures))
    bed = L.BEDS['west']
    minimum_shift = -28.671-bed[1]
    shifted = (bed[0], bed[1]+minimum_shift+.02, bed[2], bed[3]+minimum_shift+.02)
    return dict(swing_translation_search=counts, spacing_m=.05, orientation_changed=False,
                rejected_candidates=rejected, boundary_obstacles=plan['boundary_obstacles'],
                retained_current_guard_failures=L.candidate_violations(meshes, props, plan, lay),
                bed=dict(original_rect_m=bed, minimum_model_y_translation_m=minimum_shift,
                         tested_rect_m=shifted,
                         door_route_overlap_m2=box(*shifted).intersection(box(*L.PATHS['lounge-west'])).area))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', default='out/garden-g2f/current-scene.json')
    parser.add_argument('--output', default='out/garden-g2f/open-placement-proof.json')
    args = parser.parse_args()
    report = measure(json.loads(Path(args.scene).read_text()))
    Path(args.output).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['swing_translation_search']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
