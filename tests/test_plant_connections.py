"""Actual rejected axis seats, clean species siblings and geometry mutations."""
import gzip
import json
import unittest
from copy import deepcopy
from pathlib import Path

from archpipe.concept import garden_g6 as G, garden_g6b as B, villa_landscape as L
from archpipe.concept.plant_connections import organ_connection_findings


class PlantAttachmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=json.loads(gzip.decompress(Path('tests/fixtures/garden-walk2-organ-attachment-before.json.gz').read_bytes()))['meshes']
        cls.meshes,cls.plants,_,cls.plan=G.build()
        cls.connected=[m for m in cls.meshes if m.get('organ_connections')]

    def test_frozen_actual_old_organs_fail_declared_axial_seat_witness(self):
        for mesh in self.before:
            failures=organ_connection_findings([mesh])
            self.assertEqual(len(failures),len(mesh['organ_connections']))
            self.assertTrue(all('contact witness is outside' in reason for _,reason in failures))

    def test_actual_old_mona_tip_overlap_is_not_misreported_as_disconnection(self):
        from archpipe.concept.plant_connections import contains_contact
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/garden-walk2-organ-attachment-before.json.gz').read_bytes()))
        mesh=deepcopy(frozen['meshes'][0])
        # The original lamina tips really intersect the stalk. A rejected
        # stalk-axis seat must never become a false geometric-gap claim.
        for record,probe in zip(mesh['organ_connections'],frozen['old_mona_overlap_probe']):
            points=probe['child_vertices_inside_stalk_m'];self.assertTrue(points)
            record['contact_m']=points[0]
            self.assertTrue(contains_contact([mesh['faces'][i] for i in record['parent_face_indices']],points[0]))
        self.assertEqual(organ_connection_findings([mesh]),[])

    def test_actual_old_petrea_lower_pedicel_misses_real_sloped_stalk(self):
        import numpy as np
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/garden-walk2-organ-attachment-before.json.gz').read_bytes()))
        mesh=frozen['old_petrea_pedicel']
        parent,child=np.asarray(mesh['measured_stem_axes_m'])
        parent_axis=parent[1]-parent[0];child_axis=child[1]-child[0]
        # Exact closest segment candidates: each endpoint projected onto the
        # other bounded segment, plus the interior line-line minimum.
        distances=[]
        for first,second in ((parent,child),(child,parent)):
            along=second[1]-second[0]
            for point in first:
                fraction=np.clip(np.dot(point-second[0],along)/np.dot(along,along),0,1)
                distances.append(np.linalg.norm(point-second[0]-along*fraction))
        matrix=np.column_stack((parent_axis,-child_axis))
        fractions=np.linalg.lstsq(matrix,child[0]-parent[0],rcond=None)[0]
        if np.all((fractions>=0)&(fractions<=1)):
            distances.append(np.linalg.norm(parent[0]+parent_axis*fractions[0]-child[0]-child_axis*fractions[1]))
        self.assertGreater(min(distances),sum(mesh['measured_maximum_tube_radii_m']))
        self.assertIn('contact witness is outside',str(organ_connection_findings([mesh])))
        vine=next(m for m in self.connected if m['species']=='Petrea volubilis')
        records=[r for r in vine['organ_connections'] if r['kind']=='flower-pedicel']
        self.assertTrue(records)
        self.assertEqual(organ_connection_findings([self._isolate(vine,records[-1])]),[])

    def test_clean_actual_species_organs_are_closed_attached_and_complete(self):
        self.assertEqual(organ_connection_findings(self.connected),[])
        self.assertEqual(G.appearance_findings(self.meshes),[])
        lavender=[m for m in self.plants if m.get('species')=="Plectranthus 'Mona Lavender'"]
        self.assertEqual(len(lavender),11)
        self.assertEqual(sum(m['bed']=='south-bowl' for m in lavender),5)
        for mesh in lavender:
            self.assertEqual(len([r for r in mesh['organ_connections'] if r['kind']=='flower']),17*6)
            self.assertEqual(len([r for r in mesh['organ_connections'] if r['kind']=='leaf']),17*4)

    def test_renamed_translated_actual_clean_and_detached_siblings(self):
        for species in ("Plectranthus 'Mona Lavender'",'Petrea volubilis','Trachelospermum jasminoides','Eriobotrya japonica'):
            original=next(m for m in self.connected if m['species']==species)
            # One real leaf/flower with its actual parent isolates continuity
            # from the rest of the botanical assembly for a small regression.
            record=next(r for r in original['organ_connections'] if r['kind'].startswith('flower')) if species!="Eriobotrya japonica" else original['organ_connections'][0]
            case=self._isolate(original,record)
            for shift in ([0,0,0],[13,-21,7]):
                translated=deepcopy(case);translated['id']='another-villa-organ'
                for face in translated['faces']:
                    for point in face:
                        for axis in range(3):point[axis]+=shift[axis]
                for point in [translated['organ_connections'][0]['contact_m']]:
                    for axis in range(3):point[axis]+=shift[axis]
                self.assertEqual(organ_connection_findings([translated]),[],species)
                for index in translated['organ_connections'][0]['child_face_indices']:
                    for point in translated['faces'][index]:point[0]+=.2
                self.assertIn('contact witness is outside',str(organ_connection_findings([translated])),species)

    def test_open_flower_missing_attachment_and_uncovered_faces_refuse(self):
        source=next(m for m in self.connected if m['species']=="Plectranthus 'Mona Lavender'")
        record=next(r for r in source['organ_connections'] if r['kind']=='flower')
        case=self._isolate(source,record)
        malformed=deepcopy(case);malformed['organ_connections']=[]
        self.assertIn('missing physical',str(organ_connection_findings([malformed])))
        malformed=deepcopy(case);malformed['organ_connections'][0]['child_face_indices'].pop()
        failures=str(organ_connection_findings([malformed]))
        self.assertIn('open or invalid',failures);self.assertIn('lack physical attachment',failures)
        malformed=deepcopy(case);malformed['organ_connections'][0]['parent_face_indices']=[]
        self.assertIn('invalid organ attachment',str(organ_connection_findings([malformed])))
        malformed=deepcopy(case);malformed['organ_connections'][0]['parent_face_indices']=list(malformed['organ_connections'][0]['child_face_indices'])
        self.assertIn('invalid organ attachment',str(organ_connection_findings([malformed])))
        malformed=deepcopy(source)
        for field in ('organ_connections','leaf_face_indices','flower_face_indices'):malformed[field]=[]
        self.assertIn('missing physical',str(organ_connection_findings([malformed])))

    def test_closed_flower_corolla_is_single_connected_surface(self):
        from archpipe.concept.physical_part import geometry_errors
        faces=B.corolla([0,0,0],[.028,0,.004])
        self.assertEqual(geometry_errors(faces),[])
        # Every triangle joins the rest through shared full edges. This is
        # stronger than merely closing several detached flower components.
        remaining=set(range(1,len(faces)));seen={0}
        while remaining:
            vertices={tuple(point) for index in seen for point in faces[index]}
            joined={index for index in remaining if len(vertices.intersection(map(tuple,faces[index])))>=2}
            self.assertTrue(joined,'corolla has a disconnected closed component')
            seen.update(joined);remaining.difference_update(joined)

    def test_east_jasmine_metadata_preserves_exact_old_geometry_and_checks_siblings(self):
        import hashlib
        from archpipe.concept import garden_g6_east as E
        fixture=json.loads(gzip.decompress(Path('tests/fixtures/garden-walk2-organ-attachment-before.json.gz').read_bytes()))
        meshes,plants=E.trellis()
        digest=hashlib.sha256(json.dumps([dict(faces=m['faces'],face_materials=m.get('face_materials')) for m in meshes],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.assertEqual(digest,fixture['old_east_jasmine_geometry_sha256'])
        self.assertEqual(organ_connection_findings(plants),[])
        for kind in ('leaf','flower'):
            record=next(r for r in plants[0]['organ_connections'] if r['kind']==kind)
            case=self._isolate(plants[0],record)
            for index in case['organ_connections'][0]['child_face_indices']:
                for point in case['faces'][index]:point[0]+=.2
            self.assertIn('contact witness is outside',str(organ_connection_findings([case])))

    def test_preview_preserves_frozen_actual_face_materials(self):
        import tempfile
        from scripts.walk2_plant_preview import prepare
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/garden-walk2-organ-attachment-before.json.gz').read_bytes()))
        with tempfile.TemporaryDirectory() as temporary:
            prepare(Path(temporary))
            data=json.loads((Path(temporary)/'before.json').read_text())
        spike=data['assemblies'][1]['meshes'][0]
        self.assertEqual(spike['face_materials'],frozen['old_lavender_clump']['face_materials'][252:448])
        self.assertEqual(set(spike['face_materials'][:28]),{'garden-foliage'})
        star=data['assemblies'][2]['meshes'][0]
        self.assertEqual(star['face_materials'],frozen['meshes'][1]['face_materials'])

    def test_actual_jasmine_form_population_equals_frozen_old_mixed_organs(self):
        import numpy as np
        frozen=json.loads(gzip.decompress(Path('tests/fixtures/garden-walk2-visibility-before.json.gz').read_bytes()))
        jasmine=next(m for m in self.connected if m['species']=='Trachelospermum jasminoides')
        points=np.unique(np.asarray([jasmine['faces'][i] for i in jasmine['visibility_face_indices']]).reshape(-1,3),axis=0)
        self.assertEqual(points.tolist(),frozen['old_target_vertices_m'])
        self.assertTrue(set(jasmine['leaf_face_indices']).issubset(jasmine['visibility_face_indices']))

    def test_actual_form_selection_translates_and_extra_connector_faces_do_not_redistribute_it(self):
        import numpy as np
        for species in ('Petrea volubilis','Trachelospermum jasminoides'):
            source=next(m for m in self.connected if m['species']==species)
            selected=set(source['visibility_face_indices'])
            for record in source['organ_connections']:
                child=set(record['child_face_indices'])
                if record['kind'] in ('flower-hub','flower-throat'):
                    self.assertFalse(child&selected)
                else:self.assertTrue(child.issubset(selected))
            source_form_faces=np.asarray([source['faces'][i] for i in source['visibility_face_indices']])
            connector=next(r for r in source['organ_connections'] if r['kind']=='flower-hub')
            for shift in ([0.,0.,0.],[13.,-21.,7.]):
                growth=B.Growth('garden-foliage')
                growth.faces=[[(np.asarray(point)+shift).tolist() for point in face] for face in source['faces']]
                growth.materials=list(source['face_materials']);growth.visibility_faces=list(source['visibility_face_indices'])
                translated_faces=np.asarray([growth.faces[i] for i in growth.visibility_faces])
                np.testing.assert_array_equal(translated_faces,source_form_faces+shift)
                before_add=np.unique(translated_faces.reshape(-1,3),axis=0)
                new_faces=[deepcopy(growth.faces[i]) for i in connector['child_face_indices']]
                added=growth.add(new_faces,'g6-lavender-flower',visibility=False)
                self.assertTrue(added);self.assertTrue(set(added).isdisjoint(growth.fields()['visibility_face_indices']))
                actual=np.unique(np.asarray([growth.faces[i] for i in growth.fields()['visibility_face_indices']]).reshape(-1,3),axis=0)
                # Compare populations within the translated coordinates.
                # Floating addition can reorder near-tied lexicographic
                # coordinates; it cannot admit new connection-only faces.
                np.testing.assert_array_equal(actual,before_add)

    @staticmethod
    def _isolate(mesh,record):
        indices=record['parent_face_indices']+record['child_face_indices']
        mapping={old:new for new,old in enumerate(indices)}
        cloned=deepcopy(record)
        for field in ('parent_face_indices','child_face_indices'):cloned[field]=[mapping[i] for i in record[field]]
        return dict(id=mesh['id'],species=mesh['species'],faces=[deepcopy(mesh['faces'][i]) for i in indices],
                    flower_face_indices=list(cloned['child_face_indices']),leaf_face_indices=[],organ_connections=[cloned])


if __name__=='__main__':unittest.main()
