"""Reproduce source-size mattress intake from immutable round-4 bed receipts.

Recipes name reviewed parts or welded components, never a frame box as a
mattress. Component indices are zero-based in the frozen extraction order;
expected vertex counts and source hashes detect a changed input. Missing or
partial mattress geometry fails closed. No asset, extract or layout is edited.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from archpipe.beds import fit_bed, unit_scale
from bed_axis_evidence import components, native, bounds


def selected_points(meshes, selection):
    selected = []
    for item in selection:
        mesh = next(m for m in meshes if m['name'] == item['mesh'])
        if 'component_index' in item:
            points = components(mesh['faces'])[item['component_index']]
            if len(points) != item['expected_vertices']:
                raise ValueError('reviewed mattress component changed: '+item['mesh'])
        else:
            points = [p for face in mesh['faces'] for p in face]
        selected.extend(points)
    return selected


def recheck(recipes, geometry_root, library_root):
    result = []
    for recipe in recipes['candidates']:
        asset = recipe['asset']
        geometry = json.loads(gzip.decompress((geometry_root/(asset+'.json.gz')).read_bytes()))
        source = library_root/'props'/asset
        for name, digest in geometry['source_sha256'].items():
            path = (source/name).resolve()
            if not path.is_relative_to(source.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError(asset+': stale geometry receipt: '+name)
        meshes = geometry['meshes']
        frame = bounds(native([p for m in meshes for face in m['faces'] for p in face]))
        mattresses = {berth: bounds(native(selected_points(meshes, selection)))
                      for berth, selection in recipe['mattress_selections'].items()}
        fit = fit_bed(frame, *recipe['target_m'], None, recipe['dimension_front_axis'],
                      recipe['length_axis'], mattress_bounds=mattresses,
                      unit_evidence=recipes['unit_evidence'], scale=unit_scale(recipes['unit_evidence']),
                      required_berths=recipe['required_berths'])
        if recipe.get('identification_failure'):
            fit['ok'] = False
            fit['reason'] += '; '+recipe['identification_failure']
        evidence = {}
        for name, selection in recipe.get('partial_or_frame_selections', {}).items():
            box = bounds(native(selected_points(meshes, selection)))
            extents = np.asarray(box['max'])-box['min']
            evidence[name] = dict(bounds_native_m=box,
                width_length_height_m=[float(extents[0 if recipe['length_axis']=='Z' else 2]),
                                       float(extents[2 if recipe['length_axis']=='Z' else 0]),float(extents[1])],
                status='partial mattress or frame only; never a complete mattress measurement')
        sizes = {}
        for berth, data in fit['mattresses'].items():
            signed = [1000*(achieved-planned) for achieved,planned in zip(data['size_m'],recipe['target_m'])]
            sizes[berth] = dict(size_m=data['size_m'],signed_difference_mm=signed,
                beyond_tolerance_mm=[max(0,abs(v)-20) for v in signed])
        result.append(dict(recipe, source_sha256=geometry['source_sha256'],
            actual_frame_bounds_native_m=frame, actual_mattress_bounds_native_m=mattresses,
            actual_mattresses=sizes, partial_or_frame_evidence=evidence, fit=fit,
            scale=unit_scale(recipes['unit_evidence']), omitted_meshes=[],
            integration='refused at mattress intake' if not fit['ok'] else 'pending neutral and real-frame C8 review',
            c8='not run: mattress rejected before placement' if not fit['ok'] else 'required before activation',
            cloth='not simulated: mattress rejected before placement' if not fit['ok'] else 'model-first required'))
    return dict(schema='beds-round4-recheck/1',client_source=recipes['client_source'],
                unit_evidence=recipes['unit_evidence'],results=result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipes',type=Path,default=ROOT/'docs/beds-intake-round4.json')
    parser.add_argument('--geometry',type=Path,default=ROOT/'out/beds/round4/geometry')
    parser.add_argument('--library-root',type=Path,default=Path('/home/omar/archpipe/assets/library'))
    parser.add_argument('--output',type=Path,default=ROOT/'out/beds/round4/recheck.json')
    args=parser.parse_args()
    report=recheck(json.loads(args.recipes.read_text()),args.geometry,args.library_root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    for row in report['results']:
        print(row['asset'],row['fit']['reason'])
