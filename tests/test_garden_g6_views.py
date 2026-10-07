"""Real G6 furniture cannot escape garden camera checks through new IDs."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import unittest

from scripts import villa_render_views as views


class GardenG6CameraChecks(unittest.TestCase):
    def setUp(self):
        self.mesh = json.loads(gzip.decompress(Path(
            "tests/fixtures/garden-g6-camera-chair-before.json.gz").read_bytes()))["mesh"]
        points = [p for f in self.mesh["faces"] for p in f]
        center = [(min(p[k] for p in points)+max(p[k] for p in points))/2 for k in range(2)]
        self.view = dict(id="v40-south-garden-pergola", subjects=[self.mesh["id"]],
                         camera=dict(position=center+[-1.65]))
        self.scene = dict(meshes=[self.mesh], props=[])

    def test_real_new_chair_and_renamed_sibling_cannot_bypass_clearance(self):
        # The former prefix whitelist stops at v39. The actual new chair
        # would therefore have reached a new v40 camera with no proximity test.
        self.assertFalse(self.view["id"].startswith(("v25-", "v26-", "v27-", "v28-", "v36-", "v37-", "v38-", "v39-")))
        self.assertTrue(views.garden_camera_view(self.view))
        self.assertEqual(views.camera_proximity_violations(self.view,self.scene,{})[0][0],self.mesh["id"])
        sibling = deepcopy(self.view)
        sibling["id"] = "unrelated-villa-garden-camera"
        self.assertTrue(views.garden_camera_view(sibling))
        self.assertTrue(views.camera_proximity_violations(sibling,self.scene,{}))

    def test_clear_point_and_interior_scope_stay_quiet(self):
        clear = deepcopy(self.view)
        clear["camera"]["position"] = [30,-20,-1.65]
        self.assertEqual(views.camera_proximity_violations(clear,self.scene,{}),[])
        self.assertFalse(views.garden_camera_view(dict(id="v40-indoor",subjects=["living-sofa"])))

    def test_every_new_physical_role_uses_same_clearance(self):
        for role in ("pergola","climber","centrepiece","furniture","espalier","foliage"):
            sibling = deepcopy(self.mesh)
            sibling.update(id="landscape-another-villa-part",part_kind="new-builder-role",g6_element=role)
            self.assertTrue(views.camera_proximity_violations(self.view,dict(meshes=[sibling],props=[]),{}),role)


if __name__ == "__main__":
    unittest.main()

class ExplicitPlantDistance(unittest.TestCase):
    def test_real_roof_vine_empty_box_is_not_lens_contact(self):
        from archpipe.concept import garden_g6 as G
        from archpipe.concept.render_support import _triangles,_point_triangle_distance
        import numpy as np
        # Freeze the real G6 empty-box reproduction: G6b correctly hangs
        # new flowers into some of that formerly empty air.
        before=json.loads(gzip.decompress(Path('tests/fixtures/garden-g6b-appearance-before.json.gz').read_bytes()))
        vine=deepcopy(next(m for m in before if m.get('g6_element')=='climber'))
        camera=dict(subjects=[vine['id']],camera=dict(position=[24.25,-28.31,-1.65]))
        # This point lies within the full root-to-roof box but is over one
        # metre from the actual vine surface. No clearance was relaxed.
        triangles,_=_triangles([vine])
        self.assertGreater(_point_triangle_distance(np.array([camera['camera']['position']]),triangles).min(),1.)
        scene=dict(meshes=[vine],props=[])
        self.assertEqual(views.camera_proximity_violations(camera,scene,{}),[])
        point=vine['faces'][0][0]
        camera['camera']['position']=point
        self.assertTrue(views.camera_proximity_violations(camera,scene,{}))
        vine['id']='other-villa-explicit-vine'
        self.assertTrue(views.camera_proximity_violations(camera,scene,{}))

class CrossYardCaption(unittest.TestCase):
    def test_actual_camera_context_does_not_grant_arbitrary_names(self):
        from archpipe.orientation_guard import scene_findings
        mesh=dict(id='landscape-g6-loquat-plant',faces=[[[24.55,-20.8,-3],[26.85,-20.8,-3],[26.85,-20.8,-.5]]])
        view=dict(id='v40-south-garden-espalier',subjects=[mesh['id']],title='South garden espalier',caption_camera_garden=True,
                  caption_notes=['South garden seen from east yard'],camera=dict(position=[21,-21,-1.65]))
        scene=dict(meshes=[mesh],props=[],views=[view])
        self.assertEqual(scene_findings(scene),[])
        view['caption_notes']=['South garden seen from west yard']
        self.assertTrue(scene_findings(scene))
        view['caption_notes']=['South garden seen from east yard'];view['camera']['position']=[26,-26,-1.65]
        self.assertTrue(scene_findings(scene))

class ReviewedComposition(unittest.TestCase):
    def test_actual_upper_camera_requires_native_floor_and_visible_plant_groups(self):
        from archpipe.concept import villa_render as V
        from archpipe.concept.garden_render_review import garden_camera_findings,subject_visibility_findings
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/garden-g6-v27-occluded-before.json.gz').read_bytes()))
        view=next(v for v in V.VIEWS(resolve=False) if v['id']=='v27-east-yard-above')
        self.assertEqual(view['standing_ground_m'],0.)
        self.assertEqual(len(view['visibility_targets']),3)
        for shift in (0.,40.):
            case=deepcopy(frozen);v=deepcopy(view)
            scene=dict(meshes=case['meshes']+case['floor_meshes'],props=[],materials=case['materials'],garden_camera_domain=case['garden_camera_domain'])
            for key in ('position','target'):v['camera'][key][0]+=shift
            for m in scene['meshes']:
                for f in m['faces']:
                    for p in f:p[0]+=shift
            for p in scene['garden_camera_domain']['yard_polygon_m']:p[0]+=shift
            self.assertEqual(garden_camera_findings(v,scene),[])
            self.assertEqual(subject_visibility_findings(v,scene),[])
            for subject in v['subjects']:self.assertEqual(views.subject_mesh_frame_violations(v,scene,subject),[])
            v['camera']['position']=[19.+shift,-22.5,1.35]
            self.assertIn('no actual standing floor',str(garden_camera_findings(v,scene)))

    def test_real_upper_projection_can_hide_every_plant_and_translated_sibling(self):
        from archpipe.concept.garden_render_review import subject_visibility_findings
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/garden-g6-v27-occluded-before.json.gz').read_bytes()))
        for shift in (0.,40.):
            case=deepcopy(frozen);view=case['view'];view['visibility_targets']=case['targets']
            for key in ('position','target'):view['camera'][key][0]+=shift
            for m in case['meshes']:
                for f in m['faces']:
                    for p in f:p[0]+=shift
            scene=dict(meshes=case['meshes'],props=[],materials=case['materials'])
            for subject in view['subjects']:
                self.assertEqual(views.subject_mesh_frame_violations(view,scene,subject),[])
            self.assertEqual(len(subject_visibility_findings(view,scene)),4)

    def test_reviewed_oblique_camera_improves_real_grazing_view_without_geometry_move(self):
        import numpy as np
        from archpipe.concept import garden_g6 as G,villa_render as V
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/garden-g6-loquat-camera-before.json.gz').read_bytes()))
        mesh=frozen['mesh'];current=next(v for v in V.VIEWS(resolve=False) if v['id']=='v40-south-garden-espalier')
        meshes,_,_,_=G.build()
        # G6b changes the plant's appearance inside its fixed trained envelope.
        # The old image's framing comparison still uses frozen G6 geometry.
        plant=next(m for m in meshes if m['id']==mesh['id'])
        self.assertEqual(plant['center'],mesh['center'])
        self.assertEqual(plant['root_z_m'],mesh['root_z_m'])
        scene=dict(meshes=[mesh],props=[])
        points=np.unique(np.array([p for f in mesh['faces'] for p in f]),axis=0)
        def width(view):
            c=view['camera'];eye=np.array(c['position']);d=np.array(c['target'])-eye;d/=np.linalg.norm(d)
            right=np.array([d[1],-d[0],0]);h=(c['lens_mm']/c['sensor_mm'])*((points-eye)@right)/((points-eye)@d)
            return float(h.max()-h.min())
        for view in (frozen['view'],current):
            self.assertEqual(views.subject_mesh_frame_violations(view,scene,mesh['id']),[])
        self.assertGreater(width(current),width(frozen['view']))
        self.assertAlmostEqual(width(current)*960,132.15332832166,places=3)
        by_id={v['id']:v for v in V.VIEWS(resolve=False)}
        for identifier in ('v07-terrace-dusk','v19-garden-facade'):
            self.assertIn('screens much of the new roof and bowl',' '.join(by_id[identifier]['caption_notes']))
        for identifier in ('v02-garden-living','v10-living-evening'):
            self.assertIn('lower sofa parts are out of frame',' '.join(by_id[identifier]['caption_notes']))
        self.assertIn('both beam cantilevers',' '.join(current['caption_notes']))
