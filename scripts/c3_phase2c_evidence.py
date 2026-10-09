"""Measure C3 migration geometry and draw neutral engineering comparisons.

These plots are geometric previews with neutral faces, never presentation
images or photometric acceptance. All coordinates and bounds are metres.
The input scenes are saved builder output; this script never edits them.
"""
from collections import Counter
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from archpipe.concept.physical_part import PartMeshList  # noqa: E402


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), sort_keys=True).encode()).hexdigest()


def bounds(faces):
    points = [p for face in faces for p in face]
    return [min(p[i] for p in points) for i in range(3)] + [max(p[i] for p in points) for i in range(3)]


def unoriented(face):
    return tuple(sorted(tuple(p) for p in face))


def preview(before, after, output, *, show_normals=False):
    """Neutral grey surfaces; shared framing; no emissive materials or sky."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from archpipe.concept.render_support import _ear_clip
    import numpy as np

    figure = plt.figure(figsize=(12, 6))
    bb = bounds(before['faces'] + after['faces'])
    centre = [(bb[i]+bb[i+3])/2 for i in range(3)]
    span = max(bb[i+3]-bb[i] for i in range(3)) * .6
    for index, member in enumerate((before, after), 1):
        ax = figure.add_subplot(1, 2, index, projection='3d', computed_zorder=False)
        faces = [[[p[i]-centre[i] for i in range(3)] for p in f] for f in member['faces']]
        triangles = [triangle for face in faces for triangle in _ear_clip(face)]
        ax.add_collection3d(Poly3DCollection(triangles, facecolors='#cccccc', edgecolors='#444444', linewidths=.3, zorder=2))
        if show_normals:
            face = np.array(faces[0]); normal = np.cross(face[1]-face[0], face[2]-face[0])
            normal /= np.linalg.norm(normal)
            ax.quiver(*face.mean(axis=0), *normal, length=span*.6, color='#a02020', zorder=3)
            axis = int(np.argmax(np.abs(normal)))
            direction = ('positive ' if normal[axis]>0 else 'negative ') + 'xyz'[axis]
            ax.text2D(.05, .91, 'Face normal: '+direction, transform=ax.transAxes, color='#a02020')
        ax.set(xlim=(-span, span), ylim=(-span, span), zlim=(-span, span),
               xlabel='x offset (m)', ylabel='y offset (m)', zlabel='z offset (m)',
               title=('Before' if index == 1 else 'After') + ': %d faces' % len(faces))
        ax.set_box_aspect((1,1,1))
        ax.view_init(elev=22, azim=-55)
    figure.suptitle(after['id'] + '\nNeutral geometry only; red arrow = surface normal')
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, default=ROOT/'out/c3-phase2c-before-scene.json')
    parser.add_argument('--after', type=Path, default=ROOT/'out/c3-phase2c-after-scene.json')
    parser.add_argument('--rebuild', action='store_true', help='build a fresh strict scene before measuring')
    parser.add_argument('--previews-only', action='store_true', help='redraw previews from the unchanged measured scene')
    args = parser.parse_args()
    if args.rebuild:
        from archpipe.concept.villa_render import build
        scene = build(views=[])
        if scene['meshes'].collect:
            raise ValueError('fresh scene is not strict')
        args.after.write_text(json.dumps(scene, separators=(',', ':')))
        del scene
    before = json.loads(args.before.read_text())
    after = json.loads(args.after.read_text())
    baseline = json.loads(gzip.decompress((ROOT/'tests/fixtures/c3-phase2c-baseline-audit.json.gz').read_bytes()))
    frozen = json.loads(gzip.decompress((ROOT/'tests/fixtures/c3-phase2c-before.json.gz').read_bytes()))
    # Independently re-admit the saved actual final values, never historical
    # failure metadata. An exemption cannot hide an open/wrongly wound solid.
    admitted = PartMeshList()
    admitted.extend(after['meshes'])
    old = {m['id']:m for m in before['meshes']}
    new = {m['id']:m for m in after['meshes']}
    if set(old) != {m['id'] for m in baseline['meshes']} or any(
            digest(old[m['id']]['faces']) != m['faces_sha256'] for m in baseline['meshes']):
        raise ValueError('Before scene differs from the frozen branch-start final geometry')
    if any(digest(before[k]) != v for k,v in baseline['unchanged_scene_fields'].items()):
        raise ValueError('Before scene appearance differs from the frozen branch-start inputs')
    rows = []
    for original in baseline['meshes']:
        mid = original['id']
        if mid not in new:
            continue
        member = new[mid]
        bb = bounds(member['faces'])
        changed = original['faces_sha256'] != digest(member['faces'])
        fronts = Counter(unoriented(f) for f in old[mid]['faces'])
        remaining = fronts - Counter(unoriented(f) for f in member['faces'])
        old_slots = old[mid].get('face_materials', [old[mid]['material']]*len(old[mid]['faces']))
        new_slots = member.get('face_materials', [member['material']]*len(member['faces']))
        old_finishes = Counter((unoriented(f), material) for f,material in zip(old[mid]['faces'], old_slots))
        new_finishes = Counter((unoriented(f), material) for f,material in zip(member['faces'], new_slots))
        rows.append(dict(id=mid, old_kind=original['part_kind'], new_kind=member['part_kind'],
                         before_bounds=original['bounds'], after_bounds=bb,
                         maximum_bound_change_m=max(abs(a-b) for a,b in zip(original['bounds'], bb)),
                         before_faces=original['face_count'], after_faces=len(member['faces']),
                         geometry_changed=changed, visible_fronts_retained=not remaining,
                         visible_front_materials_retained=not (old_finishes-new_finishes),
                         construction_backing_m=member.get('construction_backing_m'),
                         material_unchanged=member['material']==original['material'],
                         exemption=member.get('proxy_exemption')))
    output = ROOT/'out/c3-phase2c-previews'
    output.mkdir(exist_ok=True)
    representatives = {}
    for row in rows:
        if row['geometry_changed']:
            member = new[row['id']]
            key = ('marker' if member['part_kind']=='wall-marker' else
                   'host-bridge' if member['id']=='finish-stair-stacked-slab-edge' else
                   'door' if member['part_kind']=='door-leaf' else
                   'cove' if member['id'].startswith('ceiling-') and len(old[row['id']]['faces'])>1 else
                   'floor' if member['id'].startswith('floor-') else
                   'shell-opening' if any(len(f)>8 for f in old[row['id']]['faces']) else 'shell')
            representatives.setdefault(key, row['id'])
    previews = {}
    for group, mid in representatives.items():
        path = output/(group+'.png')
        preview(old[mid], new[mid], path, show_normals=group in ('marker','host-bridge'))
        previews[group] = str(path.relative_to(ROOT))
    if args.previews_only:
        prior = json.loads((ROOT/'out/c3-phase2c-measurements.json').read_text())
        if hashlib.sha256(args.after.read_bytes()).hexdigest() != prior['after_sha256']:
            raise ValueError('Preview scene differs from the measured scene')
        print(json.dumps(dict(previews=previews, measured_scene_unchanged=True), indent=2))
        return 0
    unchanged_fields = {k:digest(after[k])==v for k,v in baseline['unchanged_scene_fields'].items()}
    source_changes = [r for r in rows if r['geometry_changed']]
    evidence = dict(branch_start=baseline['branch_start'], fresh_strict_build=args.rebuild,
        before_sha256=hashlib.sha256(args.before.read_bytes()).hexdigest(),
        after_sha256=hashlib.sha256(args.after.read_bytes()).hexdigest(),
        final_part_failures=after['part_failures'], mesh_count_before=len(old), mesh_count_after=len(new),
        removed_meshes=sorted(set(old)-set(new)), added_meshes=sorted(set(new)-set(old)),
        unchanged_scene_fields=unchanged_fields, geometry_changed_count=len(source_changes),
        maximum_bound_change_m=max(r['maximum_bound_change_m'] for r in rows),
        frozen_failure_counts=dict(Counter(f['kind'] for f in frozen['camera_free_collection'])),
        default_frozen_failure_counts=dict(Counter(f['kind'] for f in frozen['failures'])),
        proxy_exemption_counts=dict(Counter(m['part_kind'] for m in admitted if m.get('proxy_exemption'))),
        surface_exemption_counts=dict(Counter(m['part_kind'] for m in admitted if m.get('surface'))),
        previews=previews, rows=rows)
    target = ROOT/'out/c3-phase2c-measurements.json'
    target.write_text(json.dumps(evidence, indent=2)+'\n')
    failures = []
    if evidence['removed_meshes'] or evidence['added_meshes']:
        failures.append('render inventory changed')
    if not all(unchanged_fields.values()):
        failures.append('appearance or scene inputs changed')
    if after['part_failures']:
        failures.append('final part failures remain')
    for row in rows:
        if not row['material_unchanged'] or not row['visible_fronts_retained'] or not row['visible_front_materials_retained']:
            failures.append(row['id']+': visible material/front changed')
        orientation_only = row['new_kind']=='wall-marker' and row['visible_fronts_retained'] and row['maximum_bound_change_m']==0
        if row['geometry_changed'] and not orientation_only and (not row['construction_backing_m'] or row['maximum_bound_change_m']>.001000001):
            failures.append(row['id']+': change beyond shell backing')
    print(json.dumps(dict(evidence=str(target.relative_to(ROOT)), previews=previews,
                          changed=len(source_changes), failures=failures), indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
