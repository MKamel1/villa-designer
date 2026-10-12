"""Actual downloaded desk extents, immutable review and independent chair fallbacks."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
import numpy as np
from archpipe.furniture_fit import model_fit,require_furniture_geometry,review_selection
from archpipe.beds import model_review_meshes,scene_with_model_geometry

FIXTURE=Path(__file__).parent/'fixtures/desks-stage2-extremal-faces.json'

class FittedFurniture(unittest.TestCase):
    def models(self):return json.loads(FIXTURE.read_text())

    def test_real_desks_fit_footprint_floor_and_top_with_one_whole_item_transform(self):
        for model in self.models():
            require_furniture_geometry(model)
            rows=model_review_meshes([model]);points=np.asarray([p for r in rows for f in r['faces'] for p in f])
            low,high=points.min(0),points.max(0)
            np.testing.assert_allclose(high[:2]-low[:2],[model['footprint_w'],model['footprint_d']],atol=1e-9)
            np.testing.assert_allclose((high[:2]+low[:2])/2,model['position'][:2],atol=1e-9)
            self.assertAlmostEqual(low[2],model['position'][2])
            self.assertAlmostEqual(high[2]-low[2],.75)

    def test_actual_desk_source_replacement_never_removes_its_derived_chair_sibling(self):
        model=self.models()[0];chair='furn-'+model['label']+'-chair-1-0'
        original=dict(id=chair,faces=[[[0,0,0],[1,0,0],[0,1,0]]],group='furniture')
        source=dict(id=model['replacement_mesh_ids'][0],faces=original['faces'],group='furniture')
        scene=dict(models=[model],meshes=[source,original])
        result=scene_with_model_geometry(scene)
        self.assertIn(original,result['meshes']);self.assertNotIn(source,result['meshes'])
        self.assertEqual(scene['meshes'],[source,original])
        # Rename both desk and its derived chair: no project identifiers in
        # the construction control.
        renamed=deepcopy(model);renamed['replacement_mesh_ids']=['furn-other-desk-0']
        renamed['replaces']='furn-other-desk-';renamed['id']='other-instance'
        other=dict(original,id='furn-other-desk-chair-1-0')
        result=scene_with_model_geometry(dict(models=[renamed],meshes=[dict(source,id='furn-other-desk-0'),other]))
        self.assertIn(other,result['meshes'])

    def test_factor_contents_placement_and_review_mutations_refuse(self):
        model=self.models()[0];require_furniture_geometry(model)
        for field,value in [('scale_xyz',[1,1,1]),('omitted_meshes',[model['review_geometry']['meshes'][0]['name']])]:
            changed=deepcopy(model);changed[field]=value
            with self.assertRaises(ValueError):require_furniture_geometry(changed)
        changed=deepcopy(model);changed['position'][0]+=.01
        with self.assertRaisesRegex(ValueError,'not bound'):require_furniture_geometry(changed)
        changed=deepcopy(model);changed['neutral_review']['status']='pending'
        with self.assertRaisesRegex(ValueError,'accepted'):require_furniture_geometry(changed)
        require_furniture_geometry(changed,neutral_diagnostic=True)
        changed=deepcopy(model);changed['contents_review']['fused_extras']=['monitor fused into desktop']
        with self.assertRaisesRegex(ValueError,'fused'):require_furniture_geometry(changed)

if __name__=='__main__':unittest.main()
