"""RA2/B4: villa_render_contract.validate_scene judges a scene without the P2 element-identity fields."""
import copy
from unittest import mock

from archpipe import villa_render_contract as C
from archpipe import imported_appearance as IA
from archpipe.blender.element_ids import FIELDS


def scene(ids):
    m = dict(id='a', faces=[[[0, 0, 0], [1, 0, 0], [1, 1, 0]]], material='plaster', group='shell')
    if ids:
        m.update(element_ids=['wall-1'], faces_by_element={'wall-1': [0]}, element_id_basis='face-tracked')
    return dict(north=0, materials={'plaster': {}}, meshes=[m], props=[], models=[], cloth=[], curtains=[])


def test_same_verdict_with_and_without_ids():
    assert C.validate_scene(scene(True)) == C.validate_scene(scene(False))


def test_admission_never_sees_ids_and_scene_not_mutated():
    seen = []
    def spy(s):
        seen.append(any(f in m for m in s['meshes'] for f in FIELDS))
    s = scene(True); before = copy.deepcopy(s)
    with mock.patch.object(IA, 'needs_scene_admission', return_value=True), mock.patch.object(IA, 'require_scene', side_effect=spy):
        C.validate_scene(s)
    assert seen == [False] and s == before


def test_other_changes_still_caught():
    base = C.validate_scene(scene(True))
    bad = scene(True); bad['meshes'][0]['id'] = 'host-face-x'
    assert C.validate_scene(bad) != base
