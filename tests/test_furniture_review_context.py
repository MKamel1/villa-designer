"""Real cold/cache audit-note mismatch; geometry and cameras still fail closed."""
from copy import deepcopy
import gzip,json
from pathlib import Path
import unittest
from archpipe.concept.furniture_stage2 import room_context,digest,integrate,physical_architecture

FIXTURE=Path(__file__).parent/'fixtures/furniture-review-context.json'

class ReviewContext(unittest.TestCase):
    def case(self):return json.loads(FIXTURE.read_text())
    def signature(self,case,furniture=None):
        return room_context(case['scene'],case['layout'],case['specification'],
            case['furniture'] if furniture is None else furniture,case['models'])
    def test_real_cold_and_cached_derivation_notes_are_not_physical_changes(self):
        case=self.case();self.assertNotEqual(case['cold_furniture'],case['furniture'])
        # The complete real diff also includes the family-WC revision. That
        # physical difference MUST fail; isolate only the real cache notes
        # as the quiet sibling, preserving all live values.
        self.assertNotEqual(self.signature(case),self.signature(case,case['cold_furniture']))
        notes_only=deepcopy(case['furniture'])
        cold={row['id']:row for row in case['cold_furniture']}
        for row in notes_only:
            if 'overrides' in cold[row['id']]:row['overrides']=cold[row['id']]['overrides']
        self.assertEqual(self.signature(case),self.signature(case,notes_only))
        for view_subset in ([],case['scene']['views'][:1]):
            altered=deepcopy(case);altered['scene']['views']=view_subset
            self.assertEqual(self.signature(case),self.signature(altered))
    def test_changed_actual_geometry_position_or_material_still_invalidates_review(self):
        case=self.case();baseline=self.signature(case)
        altered=deepcopy(case);altered['furniture'][0]['cx']+=.01
        self.assertNotEqual(baseline,self.signature(altered))
        altered=deepcopy(case);altered['scene']['meshes'][0]['faces'][0][0][0]+=.01
        self.assertNotEqual(baseline,self.signature(altered))
        altered=deepcopy(case);altered['scene']['materials']['walnut']['base_rgb'][0]+=.01
        self.assertNotEqual(baseline,self.signature(altered))
    def test_supplied_reviewed_camera_edit_refuses_before_furniture_activation(self):
        case=self.case();scene=deepcopy(case['scene']);view=scene['views'][0]
        receipt=dict(status='accepted',combined_room_review_ok=True,room_context_sha256=self.signature(case),
            reviewed_cameras={view['id']:digest(view['camera'])})
        view['camera']['position'][0]+=.2
        with self.assertRaisesRegex(ValueError,'camera changed'):
            integrate(scene,case['models'],case['layout'],case['specification'],case['furniture'],receipt)

    def shells(self):
        path=FIXTURE.with_name('furniture-review-shell-buckets.json.gz')
        return json.loads(gzip.decompress(path.read_bytes()))

    def test_real_empty_view_shell_buckets_and_renamed_sibling_keep_physical_binding(self):
        case=self.shells()
        self.assertNotEqual(digest(case['reviewed']),digest(case['empty_views']))
        before=digest(physical_architecture(case['reviewed']))
        self.assertEqual(before,digest(physical_architecture(case['empty_views'])))
        sibling=deepcopy(case['empty_views'])
        for row in sibling:
            row['id']='other-villa-export-'+row['id']
            row['label']='another export caption'
            if 'source_mesh' in row:row['source_mesh']='renamed-bucket'
        self.assertEqual(before,digest(physical_architecture(sibling)))
        # Exercise the actual context API, not only the serializer.
        context=self.case();other=deepcopy(context)
        context['scene']['meshes']=case['reviewed']
        other['scene']['meshes']=case['empty_views']
        self.assertEqual(self.signature(context),self.signature(other))

    def test_real_shell_geometry_material_and_finish_host_mutations_still_refuse(self):
        rows=self.shells()['reviewed'];baseline=digest(physical_architecture(rows))
        for field in ('geometry','material','finish_host','visibility'):
            changed=deepcopy(rows)
            if field=='geometry':changed[0]['faces'][0][0][0]+=.01
            elif field=='material':changed[0]['material']='unreviewed-finish'
            elif field=='visibility':changed[0]['visibility']={'camera':False}
            else:
                host=next(r for r in changed if 'finish_host_ids' in r)
                host['finish_host_ids']=['another-physical-host']
            self.assertNotEqual(baseline,digest(physical_architecture(changed)),field)

if __name__=='__main__':unittest.main()
