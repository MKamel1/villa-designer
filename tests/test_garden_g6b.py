"""Frozen G6 appearance failures, clean construction and sibling mutations."""
import gzip,json,unittest
from copy import deepcopy
from pathlib import Path
from archpipe.concept import garden_g6 as G,garden_g6_east as E

class AppearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meshes,cls.plants,_,cls.plan=G.build()
        cls.east,_,_,_=E.build()
        cls.before=json.loads(gzip.decompress(Path('tests/fixtures/garden-g6b-appearance-before.json.gz').read_bytes()))

    def test_real_before_fails_each_class_and_clean_siblings_stay_quiet(self):
        failures=G.appearance_findings(self.before)
        for word in ('mound','species-sized','Petrea','loquat','seating'):
            self.assertIn(word,str(failures))
        self.assertEqual(G.appearance_findings(self.meshes+self.east),[])

    def test_fixed_roots_positions_and_seat_facing(self):
        current={m['id']:m for m in self.meshes+self.east}
        for before in self.before:
            after=current[before['id']]
            for field in ('center','root_z_m','post_index','facing','seats'):
                if field in before:self.assertEqual(json.loads(json.dumps(after[field])),before[field],(before['id'],field))
        self.assertEqual(G.findings(self.meshes,self.plan),[])

    def test_first_fix_barrel_and_hidden_racemes_fail_clean_forms_stay_quiet(self):
        before=json.loads(gzip.decompress(Path('tests/fixtures/garden-g6b-first-fix-before.json.gz').read_bytes()))
        failures=str(G.appearance_findings(before))
        self.assertIn('stacked horizontal foliage rings',failures)
        self.assertIn('clear below beams',failures)
        for shift in (0.,30.):
            sibling=deepcopy(before)
            for mesh in sibling:
                mesh['id']='another-villa-'+mesh['species']
                mesh['root_z_m']+=shift
                mesh['center']=[v+shift for v in mesh['center']]
                for face in mesh['faces']:
                    for point in face:
                        for axis in range(3):point[axis]+=shift
            self.assertIn('stacked horizontal foliage rings',str(G.appearance_findings(sibling)))
            self.assertIn('clear below beams',str(G.appearance_findings(sibling)))
        self.assertEqual(G.appearance_findings(self.meshes+self.east),[])

    def test_renamed_translated_mounds_and_missing_low_foliage(self):
        for source in (self.meshes,self.east):
            shrub=deepcopy(next(m for m in source if m.get('species')=="Pittosporum tobira 'Wheeler\'s Dwarf'"))
            shrub['id']='another-villa-shrub';shrub['center']=[v+30 for v in shrub['center']];shrub['root_z_m']+=7
            for f in shrub['faces']:
                for p in f:p[0]+=30;p[1]+=30;p[2]+=7
            self.assertEqual(G.appearance_findings([shrub]),[])
            shrub['leaf_face_indices']=[i for i in shrub['leaf_face_indices'] if min(p[2] for p in shrub['faces'][i])>shrub['root_z_m']+.25]
            self.assertIn('mound',str(G.appearance_findings([shrub])))

    def test_leaf_size_hanging_sprays_veins_and_lounge_parts_mutations(self):
        vine=deepcopy(next(m for m in self.meshes if m.get('species')=='Petrea volubilis'))
        vine['flower_face_indices']=[];self.assertIn('hanging Petrea',str(G.appearance_findings([vine])))
        vine=deepcopy(next(m for m in self.meshes if m.get('species')=='Trachelospermum jasminoides'))
        record=vine['leaf_records'][0];indices=record['face_indices'];center=__import__('numpy').mean([p for i in indices for p in vine['faces'][i]],axis=0)
        for i in indices:
            vine['faces'][i]=[(center+(p-center)*3).tolist() for p in __import__('numpy').array(vine['faces'][i])]
        self.assertIn('species size',str(G.appearance_findings([vine])))
        tree=deepcopy(next(m for m in self.meshes if m.get('species')=='Eriobotrya japonica'));tree['face_materials']=['garden-foliage']*len(tree['faces'])
        self.assertIn('veins',str(G.appearance_findings([tree])));self.assertIn('ties',str(G.appearance_findings([tree])))
        chair=deepcopy(next(m for m in self.meshes if m.get('g6_element')=='furniture'));chair['id']='another-villa-seat';chair['seating_parts'].pop('back-cushion')
        self.assertIn('seating',str(G.appearance_findings([chair])))

    def test_full_subject_intent_uses_real_vertices_and_translated_sibling(self):
        from archpipe.concept.garden_render_review import subject_frame_findings
        from archpipe.concept import villa_render as V
        mesh=next(m for m in self.meshes if m.get('species')=='Eriobotrya japonica')
        view=next(v for v in V.VIEWS(resolve=False) if v['id']=='v40-south-garden-espalier')
        view['require_full_subject_frame']=True
        for offset in (0.,40.):
            case=deepcopy(mesh);camera=deepcopy(view)
            camera['id']='another-villa-physical-detail'
            for face in case['faces']:
                for point in face:point[0]+=offset
            for key in ('position','target'):camera['camera'][key][0]+=offset
            scene=dict(meshes=[case],props=[])
            self.assertEqual(subject_frame_findings(camera,scene),[])
            camera['camera']['shift_y']+=.5
            self.assertIn('outside frame',str(subject_frame_findings(camera,scene)))
            camera['require_full_subject_frame']=False
            self.assertEqual(subject_frame_findings(camera,scene),[])

    def test_real_upper_crop_refused_current_portrait_and_translated_sibling(self):
        from archpipe.concept.garden_render_review import subject_frame_findings
        from archpipe.concept import villa_render as V
        before=json.loads(gzip.decompress(Path('tests/fixtures/garden-g6b-upper-frame-before.json.gz').read_bytes()))
        # The accepted G6b portrait is historical evidence after the view-intent change.
        current=next(v for v in json.loads(Path('tests/fixtures/garden-views-cameras-before.json').read_text()) if v['id']=='v27-east-yard-above')
        self.assertTrue(current['require_full_subject_frame'])
        for offset in (0.,40.):
            scene=deepcopy(before);old=scene['view'];new=deepcopy(current)
            old['require_full_subject_frame']=True
            for mesh in scene['meshes']:
                for face in mesh['faces']:
                    for point in face:point[0]+=offset
            for view in (old,new):
                view['id']='another-villa-upper-planting'
                for key in ('position','target'):view['camera'][key][0]+=offset
            self.assertIn('outside frame',str(subject_frame_findings(old,scene)))
            self.assertEqual(subject_frame_findings(new,scene),[])
            self.assertEqual(new['camera']['position'],old['camera']['position'])
            self.assertEqual(new['camera']['target'],old['camera']['target'])
            self.assertEqual(new['camera']['lens_mm'],24)

    def test_real_unstamped_camera_input_and_stale_siblings_refused(self):
        from scripts.garden_g6b_camera import require_current_scene
        from archpipe.concept.villa_render import source_provenance
        frozen=json.loads(Path('tests/fixtures/garden-g6b-camera-input-before.json').read_text())
        current=source_provenance()
        for label in ('original','another-villa'):
            case=deepcopy(frozen);case['id']=label
            with self.assertRaisesRegex(ValueError,'current authoritative'):
                require_current_scene(case,current)
            case['provenance']=deepcopy(current)
            self.assertIsNone(require_current_scene(case,current))
            case['provenance']['source_hash']='0'*64
            with self.assertRaisesRegex(ValueError,'current authoritative'):
                require_current_scene(case,current)

    def test_real_finish_register_omission_and_arbitrary_sibling_refused(self):
        from scripts.verify import unregistered_render_finishes
        from archpipe.concept import villa_render as V
        old=set(json.loads(Path('tests/fixtures/garden-g6b-finish-register-before.json').read_text()))
        self.assertEqual(set(unregistered_render_finishes(V.M,old)),{
            'g6-jasmine-leaf','g6-petrea-leaf','g6-pittosporum-leaf','g6-leaf-vein',
            'g6-wire-tie','g6-loquat-leaf','g6-outdoor-timber','g6-shrub-wood',
            'north-light-stone','north-pale-gravel','aspidistra-leaf'})
        self.assertEqual(unregistered_render_finishes(V.M),[])
        for name in ('north-light-stone','north-pale-gravel','aspidistra-leaf'):
            # Reviewed G4d/G4e names must be independently registered; omission
            # of either real new finish and an unlisted replacement refuse.
            from scripts.verify import registered_render_finishes
            self.assertEqual(unregistered_render_finishes(V.M,registered_render_finishes()-{name}),[name])
            mutant=dict(V.M);mutant['unlisted-'+name]=mutant.pop(name)
            self.assertEqual(unregistered_render_finishes(mutant),['unlisted-'+name])
        self.assertEqual(unregistered_render_finishes({'another-villa-finish':{}}),['another-villa-finish'])

if __name__=='__main__':unittest.main()
