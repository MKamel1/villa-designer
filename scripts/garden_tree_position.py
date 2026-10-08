"""Reproduce D4's continuous whole-lawn minimum tree offset; never alters design.

Run with PYTHONPATH=src. Coordinates and translations are horizontal metres;
all walking bands use D2's 2.0 m passage height. Scene export remains subject
to every landscape guard, independently of this placement calculation.
"""
import copy
import json
from archpipe.concept import villa_landscape as L, villa_r11 as R, revit_spec as RS
from archpipe.concept.route_geometry import prop_triangles, nearest_clear_translation


def search_position():
    lay = R.design('D1')
    meshes, props, _, _ = L.review_candidate(RS.build(lay), lay)
    tree = copy.deepcopy(next(p for p in props if p['asset'] == 'sf_frangipani'))
    current = tree['center']
    for axis in (0,1):
        tree['position'][axis] += L.SOUTH_CENTER[axis]-current[axis]
    tree['center'] = L.SOUTH_CENTER
    fence = L.E.FENCE_T/1000
    usable = (L.SOUTH[0],L.SOUTH[1],L.SOUTH[2]-fence,L.SOUTH[3]-fence)
    model = L._rect(tree)
    center = tree['center']
    radius = L.require_species('Plumeria rubra')['spread']['range_m'][0]/2
    # Whole lawn intersected with the model canopy, mature circle and D4 x band.
    bounds = (max(-.5,usable[0]-model[0],usable[0]+radius-center[0]),
              max(usable[1]-model[1],usable[1]+radius-center[1]),
              min(.5,usable[2]-model[2],usable[2]-radius-center[0]),
              min(usable[3]-model[3],usable[3]-radius-center[1]))
    routes, ground = L.walking_routes(meshes)
    # Check the band of every route reachable within the search domain.
    for name, rect in routes.items():
        if (model[0]+bounds[0] <= rect[2] and model[2]+bounds[2] >= rect[0]
                and model[1]+bounds[1] <= rect[3] and model[3]+bounds[3] >= rect[1]):
            prop_triangles(tree, walking_top_m=ground[name]+2.0)
    answer = nearest_clear_translation(prop_triangles(tree),bounds,routes,ground)
    if answer is None:
        raise ValueError('no whole-lawn route-clear tree position')
    answer['center_m'] = [center[i]+answer['translation_m'][i] for i in (0,1)]
    for axis in (0,1):
        tree['position'][axis] += answer['translation_m'][axis]
    tree['center'] = tuple(answer['center_m'])
    failures = (L.route_violations([tree],routes,ground)+L.canopy_violations([tree])+
                L.canopy_violations([tree],mature=True)+L.extent_violations([tree],L.garden_level_rooms(lay)))
    if failures:
        raise ValueError('minimum candidate fails independent guards: '+str(failures))
    return answer


if __name__ == '__main__':
    print(json.dumps(search_position(),indent=2))
