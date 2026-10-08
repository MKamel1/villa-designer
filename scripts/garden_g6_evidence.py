"""Reproduce G6 diagnostic input and acceptance, never presentation renders.

Run with --specimens before Blender isolated review; otherwise export the
authoritative scene and independently measure its support and openings.
"""
import argparse
import json
from pathlib import Path

from archpipe.concept import garden_g6 as G, garden_g6_east as E
from archpipe.concept import villa_render as V, render_support as S
from archpipe.concept.garden_sun import SunStudy, DATES

OUT = Path('out/garden-g6')


def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2)+'\n')


def specimens():
    meshes, plants, objects, plan = G.build()
    east, east_plants, beds, light = E.build()
    save('builder-meshes.json', meshes)
    save('builder-plan.json', plan)
    save('east-builder-meshes.json', east)
    save('east-builder-report.json', light)
    assemblies = [dict(id=name, meshes=[m for m in meshes if predicate(m)])
                  for name, predicate in (
        ('pergola-climbers', lambda m: m.get('pergola_role') or m.get('g6_element')=='climber'),
        ('centrepiece', lambda m: m.get('g6_element')=='centrepiece'),
        ('outdoor-furniture', lambda m: m.get('g6_element')=='furniture'),
        ('loquat-espalier', lambda m: m.get('g6_element')=='espalier'),
        ('south-layered-foliage', lambda m: m.get('g6_element')=='foliage' and m.get('species')))]
    assemblies += [dict(id='east-jasmine-trellis', meshes=[m for m in east if m.get('part_kind') in ('trellis','climber','climber-branch')]),
                   dict(id='east-layered-foliage', meshes=[m for m in east if m.get('part_kind')=='plant-clump'])]
    save('specimens.json', dict(materials=V.M, assemblies=assemblies))


def acceptance():
    path, scene = V.write(OUT/'scene.json')
    study = SunStudy(scene)
    results = dict(unsupported=S.unsupported(scene), blocked_openings=S.blocked_openings(scene),
                   g6_findings=G.scene_findings(scene), scene=str(path))
    save('acceptance.json', results)
    save('light-applicability.json', scene['garden_sun_evidence'])
    east = [m for m in scene['meshes'] if m.get('species') and
            (m.get('bed')=='east' or str(m.get('bed','')).startswith('door-pot-'))]
    results['east_light_findings'] = E.quote_match_findings(east, study=study)
    save('east-light-applicability.json', E.light_report(east, study=study))
    results['sun_dates'] = list(DATES)
    save('acceptance.json', results)
    print(json.dumps(results, indent=2), flush=True)
    if any(results[key] for key in ('unsupported','blocked_openings','g6_findings','east_light_findings')):
        raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--specimens', action='store_true')
    parser.add_argument('--output', type=Path, default=OUT)
    args=parser.parse_args()
    OUT=args.output
    OUT.mkdir(parents=True,exist_ok=True)
    specimens() if args.specimens else acceptance()
