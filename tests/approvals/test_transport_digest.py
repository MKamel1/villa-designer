"""RA: the frozen exposure transport digest ignores the P2 element-identity fields and nothing else."""
import copy

from archpipe import exposure_groups as EG
from archpipe.blender.element_ids import FIELDS


def scene(ids):
    mesh = lambda i: dict(id=i, faces=[[[0, 0, 0], [1, 0, 0], [1, 1, 0]]], material='plaster', group='shell')
    meshes = [mesh('a'), mesh('b')]
    if ids:
        meshes[0].update(element_ids=['wall-1'], faces_by_element={'wall-1': [0]}, element_id_basis='face-tracked')
        meshes[1].update(element_ids=[], element_id_basis='unresolved')
    return dict(north=0, materials={'plaster': {}}, meshes=meshes, props=[], models=[], cloth=[], curtains=[])


def test_digest_identical_with_and_without_ids():
    assert EG.transport_digest(scene(True)) == EG.transport_digest(scene(False))
    assert set(FIELDS) == {'element_ids', 'faces_by_element', 'element_id_basis'}


def test_digest_does_not_mutate_scene():
    s = scene(True); before = copy.deepcopy(s)
    EG.transport_digest(s)
    assert s == before


def test_any_other_change_still_alters_digest():
    base = EG.transport_digest(scene(True))
    moved = scene(True); moved['meshes'][0]['faces'][0][0][0] = 1e-6
    renamed = scene(True); renamed['meshes'][1]['material'] = 'glass'
    extra = scene(True); extra['meshes'].append(dict(id='c', faces=[], material='plaster', group='shell'))
    north = scene(True); north['north'] = 1
    new_field = scene(True); new_field['meshes'][0]['emissive'] = 1
    for changed in (moved, renamed, extra, north, new_field):
        assert EG.transport_digest(changed) != base
