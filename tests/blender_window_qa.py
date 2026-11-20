"""Pinned native proof on frozen actual window, foreground and hidden curtain faces."""
import copy
import gzip
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import bpy
from mathutils import Vector
from archpipe.window_qa import visible_windows,unpack_pixels
from archpipe.blender.villa_scene import configure_camera


class NativeWindowOwnership(unittest.TestCase):
    def test_actual_small_pane_retains_ownership_before_individual_size_screen(self):
        value=json.loads(gzip.decompress((ROOT/'tests/fixtures/walk2-small-pane-native.json.gz').read_bytes()))
        case=copy.deepcopy(value)
        for obj in case['objects']:
            obj['faces']=[face['vertices'] for face in obj['faces']]
        original=next(obj for obj in value['objects'] if obj['glass'])
        index=next(i for i,face in enumerate(original['faces']) if face['index']==6)
        old={'__name__':'frozen_small_pane'}
        exec(compile(value['before_source'],'frozen_small_pane','exec'),old)
        for shift,prefix in (((0,0,0),''),((13,-21,7),'another-villa-')):
            scene,camera,objects,glass=self.build(case,shift,prefix)
            identity=f'{prefix}{original["name"]}-face-{index}'
            self.assertFalse(any(window['id']==identity for window in old['visible_windows'](scene,camera,glass)))
            windows,room=visible_windows(scene,camera,glass,include_room=True)
            pane=next(window for window in windows if window['id']==identity)
            expected={tuple(sample['pixel']) for sample in value['samples']
                      if sample['first_hit']==[original['name'],6]}
            self.assertEqual(unpack_pixels(pane['visible_pixels'],480,270),expected)
            self.assertEqual(len(expected),107)
            self.assertLess(pane['screen'][2]-pane['screen'][0],.03)
            self.assertTrue(unpack_pixels(room,480,270,expected_step=3))

    def build(self,case,shift=(0,0,0),rename=''):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene=bpy.context.scene;scene.render.resolution_x=480;scene.render.resolution_y=270
        scene.render.resolution_percentage=100;objects=[];glass=[]
        for spec in case['objects']:
            vertices=[];faces=[]
            for face in spec['faces']:
                first=len(vertices);vertices.extend([[a+b for a,b in zip(p,shift)] for p in face]);faces.append(list(range(first,len(vertices))))
            mesh=bpy.data.meshes.new(rename+spec['name']);mesh.from_pydata(vertices,[],faces)
            obj=bpy.data.objects.new(rename+spec['name'],mesh);scene.collection.objects.link(obj)
            obj.hide_render=spec['hide_render'];obj.visible_camera=spec['visible_camera'];objects.append(obj)
            if spec['glass']:glass.append(obj)
        view=dict(camera=copy.deepcopy(case['camera']))
        for key in ('position','target'):view['camera'][key]=[a+b for a,b in zip(view['camera'][key],shift)]
        camera,_=configure_camera(view);bpy.context.view_layer.update()
        return scene,camera,objects,glass

    def cases(self):
        return json.loads(gzip.decompress((ROOT/'tests/fixtures/walk2-window-native-geometry.json.gz').read_bytes()))['cases']

    def test_actual_foreground_and_translated_renamed_sibling_have_correct_pixel_owners(self):
        case=self.cases()[0]
        for shift,name in (((0,0,0),''),((13,-21,7),'another-villa-')):
            scene,camera,objects,glass=self.build(case,shift,name)
            windows=visible_windows(scene,camera,glass)
            owned=set().union(*(unpack_pixels(w['visible_pixels'],480,270) for w in windows))
            # Frozen native first-hit values are independent of today's geometry builder.
            expected={tuple(s['pixel']) for s in case['samples'] if s['visible'] and
                      any(o['glass'] and o['name']==s['visible'][0] for o in case['objects'])}
            checked={tuple(s['pixel']) for s in case['samples']}
            self.assertEqual(owned & checked,expected)
            self.assertTrue(expected)
            self.assertNotEqual(owned & checked,checked)

    def test_actual_hidden_curtain_cannot_hide_glazing_but_visible_blocker_does(self):
        case=self.cases()[1];scene,camera,objects,glass=self.build(case)
        windows=visible_windows(scene,camera,glass)
        self.assertTrue(windows)
        self.assertTrue(any(o.hide_render and 'curtain' in o.name for o in objects))
        curtain=next(o for o in objects if 'curtain' in o.name)
        curtain.hide_render=False;bpy.context.view_layer.update()
        # Compare actual frozen ray positions; tiny extracted curtain faces are
        # only the nine real sampled blockers, not a synthetic full curtain.
        from archpipe.window_qa import render_geometry
        tree,owners=render_geometry(scene,bpy.context.evaluated_depsgraph_get())
        for sample in case['samples']:
            if sample['scene_query'] and sample['scene_query'][0]==curtain.name:
                x,y=sample['pixel'];corners=camera.data.view_frame(scene=scene)
                lo=Vector((min(v.x for v in corners),min(v.y for v in corners),corners[0].z));hi=Vector((max(v.x for v in corners),max(v.y for v in corners),corners[0].z))
                local=Vector((lo.x+(x+.5)/480*(hi.x-lo.x),hi.y-(y+.5)/270*(hi.y-lo.y),lo.z))
                location,normal,index,distance=tree.ray_cast(camera.matrix_world.translation,(camera.matrix_world.to_3x3()@local).normalized())
                self.assertIsNotNone(location);self.assertEqual(owners[index][0],curtain.name)
        curtain.visible_camera=False;bpy.context.view_layer.update()
        self.assertTrue(visible_windows(scene,camera,glass))

    def test_collection_instance_occludes_and_visibility_invalidates_static_cache(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene=bpy.context.scene;scene.render.resolution_x=120;scene.render.resolution_y=80
        scene.render.resolution_percentage=100
        def plane(name,x,collection):
            mesh=bpy.data.meshes.new(name)
            mesh.from_pydata([(x,-2,-2),(x,2,-2),(x,2,2),(x,-2,2)],[],[(0,1,2,3)])
            obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);return obj
        glass=plane('sibling-glass',2,scene.collection)
        camera,_=configure_camera(dict(camera=dict(position=[0,0,0],target=[1,0,0],lens_mm=24,sensor_mm=36)))
        bpy.context.view_layer.update()
        self.assertTrue(visible_windows(scene,camera,[glass],geometry_key='verified-static-fixture'))
        collection=bpy.data.collections.new('unlinked-instance-source')
        plane('instanced-opaque-blocker',1,collection)
        instance=bpy.data.objects.new('linked-instance',None);instance.instance_type='COLLECTION'
        instance.instance_collection=collection;scene.collection.objects.link(instance)
        bpy.context.view_layer.update()
        self.assertEqual(visible_windows(scene,camera,[glass],geometry_key='verified-static-fixture'),[])
        instance.hide_render=True;bpy.context.view_layer.update()
        self.assertTrue(visible_windows(scene,camera,[glass],geometry_key='verified-static-fixture'))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeWindowOwnership))
    if not result.wasSuccessful():raise RuntimeError('Native window ownership regression failed')
