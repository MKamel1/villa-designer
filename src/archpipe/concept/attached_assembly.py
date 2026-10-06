"""Explicit attached-part ownership and one rigid translation, in metres."""
from copy import deepcopy
from .fitting_mounting import bounds


def bind(scene, root_id, child_ids):
    meshes = {m['id']: m for m in scene['meshes']}
    root = meshes[root_id]
    origin = bounds(root)[:3]
    for identifier in child_ids:
        child = meshes[identifier]
        child['associated_mounting_root'] = root_id
        child['attached_relative_origin_m'] = [bounds(child)[i]-origin[i] for i in range(3)]


def translate(scene, root_id, delta, *, deferred_ids=()):
    """Move the root and every declared child once; retain per-vertex proof."""
    members = [m for m in scene['meshes'] if m['id'] == root_id or
               (m.get('associated_mounting_root') == root_id and m['id'] not in deferred_ids)]
    if not any(m['id'] == root_id for m in members):
        raise ValueError('Missing attached assembly root: '+root_id)
    records = []
    for member in members:
        before = deepcopy(member['faces'])
        member['faces'] = [[[p[i]+delta[i] for i in range(3)] for p in f] for f in before]
        records.append(dict(id=member['id'], root_id=root_id, delta=list(delta),
                            old_faces=before, new_faces=deepcopy(member['faces']),
                            basis='Explicit attached assembly rigid translation'))
    return records


def findings(scene):
    meshes = {m['id']: m for m in scene['meshes']}
    failures = []
    for child in meshes.values():
        relative = child.get('attached_relative_origin_m')
        if relative is None:
            continue
        root = meshes.get(child.get('associated_mounting_root'))
        if root is None:
            failures.append(child['id']+': MISSING attached assembly root')
        elif any(abs(bounds(child)[i]-bounds(root)[i]-relative[i]) > 1e-8 for i in range(3)):
            failures.append(child['id']+': attached assembly split movement')
    return failures
