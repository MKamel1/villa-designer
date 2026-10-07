"""Actual renderer/guard consumer proofs for exported physical climbers."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest


class PhysicalClimberConsumers(unittest.TestCase):
    def test_explicit_climber_keeps_exported_geometry_in_blender(self):
        tree = ast.parse(Path('src/archpipe/blender/villa_scene.py').read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_climbers')
        def refuse(*args, **kwargs):
            raise AssertionError('physical geometry must not use scattered replacement')
        namespace = {'sibling': lambda name: SimpleNamespace(density_for_coverage=refuse)}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), 'actual-climber-consumer', 'exec'), namespace)
        obj = SimpleNamespace(hide_render=False)
        namespace['build_climbers']([{'id': 'authored-vine', 'part_kind': 'climber', 'explicit_geometry': True}], {'authored-vine': obj}, {}, [])
        self.assertFalse(obj.hide_render)

    def test_explicit_leaf_guard_uses_actual_faces_and_rejects_missing_indices(self):
        from archpipe.concept.garden_render_review import plant_form_findings
        mesh = dict(id='another-vine', part_kind='climber', explicit_geometry=True,
                    root_z_m=4., leaf_face_indices=[0],
                    faces=[[[2., 1., 4.1], [2.1, 1., 4.1], [2., 1.1, 4.12]],
                           [[2., 1., 4.], [2.01, 1., 4.], [2., 1., 5.]]])
        self.assertEqual(plant_form_findings([mesh]), [])
        raised = deepcopy(mesh)
        for point in raised['faces'][0]:
            point[2] += .5
        self.assertTrue(any('leaf mass' in f for f in plant_form_findings([raised])))
        absent = deepcopy(mesh); absent.pop('leaf_face_indices')
        self.assertTrue(plant_form_findings([absent]))
        invalid = deepcopy(mesh); invalid['leaf_face_indices'] = [999]
        self.assertTrue(plant_form_findings([invalid]))


if __name__ == '__main__':
    unittest.main()
