"""Exercise the actual Blender QA function/call without rendering or importing bpy."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

from archpipe import villa_render_contract as contract


class ImportedGardenSubjects(unittest.TestCase):
    def setUp(self):
        tree=ast.parse(Path('src/archpipe/blender/villa_scene.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='subjects')
        render=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render')
        self.call=next(n.value for n in ast.walk(render) if isinstance(n,ast.Assign) and
                       any(isinstance(t,ast.Name) and t.id=='subject_result' for t in n.targets))
        # The geometry projection is already proved against real asset
        # vertices by test_render_views. Here the consumer receives actual
        # imported-record/vertex shapes and the real render call expression.
        class IdentityMatrix:
            def __matmul__(self,point): return point
        vertices=[SimpleNamespace(co=SimpleNamespace(x=.25,y=.30,z=1)),
                  SimpleNamespace(co=SimpleNamespace(x=.75,y=.80,z=1))]
        obj=SimpleNamespace(matrix_world=IdentityMatrix(),data=SimpleNamespace(vertices=vertices))
        imported=[dict(id='other-imported-plant',objects=[obj],label='authored appearance')]
        self.namespace=dict(contract=contract,bpy=SimpleNamespace(context=SimpleNamespace(scene=SimpleNamespace(camera=None))),
                            world_to_camera_view=lambda scene,camera,point:point,
                            view={'subjects':['other-imported-plant']},scene_data={'meshes':[]},
                            objects={},imported_props=imported)
        module=ast.Module(body=[function],type_ignores=[])
        exec(compile(ast.fix_missing_locations(module),'actual-subject-function','exec'),self.namespace)

    def test_actual_render_call_resolves_imported_vertex_subject(self):
        result=eval(compile(ast.Expression(self.call),'actual-render-call','eval'),self.namespace)
        self.assertEqual(result[0]['matched_objects'],['other-imported-plant'])
        self.assertTrue(result[0]['in_frame'])
        self.assertEqual(result[0]['screen'],[.25,.30,.75,.80])
        self.namespace['imported_props']=[]
        result=eval(compile(ast.Expression(self.call),'actual-render-call','eval'),self.namespace)
        self.assertFalse(result[0]['in_frame'])

    def test_frozen_wrong_import_result_name_fires_before_qa(self):
        # Actual first wiring error found at read-through; the producer's
        # local result is imported_props, not imported.
        frozen=compile('subjects(view, scene_data["meshes"], objects, imported)','frozen-call','eval')
        with self.assertRaises(NameError):eval(frozen,self.namespace)

    def test_actual_render_call_resolves_mounted_descendants_and_missing_subject(self):
        # The production helper, including assembly ownership, participates
        # in this extracted consumer; Blender projection alone is doubled.
        points=[[.25,.30,1],[.75,.80,1]]
        meshes=[dict(id='stand-root',label='authored-assembly',faces=[points]),
                dict(id='unrelated-leaf-name',mounting={'assembly_root':'stand-root'},faces=[points])]
        obj=self.namespace['imported_props'][0]['objects'][0]
        self.namespace.update(view={'subjects':['authored-assembly']},
                              scene_data={'meshes':meshes},
                              objects={m['id']:obj for m in meshes},imported_props=[],
                              Vector=lambda p:SimpleNamespace(x=p[0],y=p[1],z=p[2]))
        result=eval(compile(ast.Expression(self.call),'actual-render-call','eval'),self.namespace)
        self.assertEqual(result[0]['matched_objects'],['stand-root','unrelated-leaf-name'])
        self.assertTrue(result[0]['full_frame'])
        meshes[1]['mounting']={}
        result=eval(compile(ast.Expression(self.call),'actual-render-call','eval'),self.namespace)
        self.assertEqual(result[0]['matched_objects'],['stand-root'])
        self.namespace['view']['subjects']=['missing-assembly']
        result=eval(compile(ast.Expression(self.call),'actual-render-call','eval'),self.namespace)
        self.assertEqual(result[0]['matched_objects'],[])
        self.assertFalse(result[0]['in_frame'])


if __name__=='__main__':unittest.main()
