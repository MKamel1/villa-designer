"""C4i render finish construction: real omission, topology and siblings."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from archpipe.concept import villa_render as VR, villa_r11 as R, villa_furnish as F
from archpipe.concept.finish_layers import build, clip, extrude, surface_findings, solid_findings
from archpipe.concept.fitting_mounting import normal
from archpipe.concept.render_support import _triangles, _point_triangle_distance, _tri_box_overlap, unsupported


class FinishLayers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build the actual 9069c24 failure with construction suppressed, not a
        # synthetic wall invented to make the new check pass.
        with patch('archpipe.concept.finish_layers.build'):
            cls.before = VR.build(views=[])
        cls.scene = deepcopy(cls.before)
        lay = R.design("D1")
        build(cls.scene, {room:F.clear_rect(lay,room) for room in lay["rooms"]})

    def test_real_suppressed_finish_fires_and_clean_scene_stays_quiet(self):
        frozen_ids = json.loads(Path('tests/fixtures/c4i-floating-ids.json').read_text())
        floating = unsupported(self.before)
        self.assertEqual(len(floating), 51)
        self.assertEqual({mid for mid,_ in floating}, set(frozen_ids))
        failures = surface_findings(self.before)
        failed_ids = {f.split(':')[0] for f in failures}
        self.assertTrue(set(frozen_ids) <= failed_ids, set(frozen_ids)-failed_ids)
        # Plaster is a sibling that the older 15 mm float tolerance missed.
        self.assertIn('detail-headboard-slats', failed_ids)
        self.assertEqual(surface_findings(self.scene), [])
        self.assertEqual(unsupported(self.scene), [])

    def test_finish_solids_closed_outward_full_extent_same_material(self):
        self.assertEqual(solid_findings(self.scene), [])
        original = {m['id']:m for m in self.before['meshes']}
        layers = [m for m in self.scene['meshes'] if m['id'].startswith('finish-layer-')]
        self.assertTrue(layers)
        render = {m['id']:m for m in self.scene['meshes']}
        seen = set()
        for layer in layers:
            source = original[layer['source_mesh']]
            self.assertEqual(layer['group'], 'shell')
            for hid in layer['finish_host_ids']:
                self.assertEqual(layer['material'],self.scene['mounting_hosts'][hid]['source_material'])
            # One shared material specification supplies texture projection,
            # metre scale and tint to both shell and layer in the renderer.
            material = self.scene['materials'][layer['material']]
            if layer['material']=='marble-bath':
                self.assertEqual(layer['material'],source['material'])
                self.assertEqual(material, VR.M['marble-bath'])
                self.assertGreater(material['tile_m'], 0)
            self.assertNotIn('visibility', layer)
            self.assertNotIn('diagnostic', layer)
            face = layer['source_faces'][0]
            self.assertIn(layer['source_face'], source['faces'])
            axis = layer['zone_axis']
            low,high = layer['zone_bounds_m']
            self.assertEqual(face,clip(clip(layer['source_face'],axis,low,True),axis,high,False))
            self.assertNotIn(face, render.get(source['id'], {}).get('faces', []))
            identity = (layer['source_mesh'], str(face))
            self.assertNotIn(identity, seen)
            seen.add(identity)
            n = layer['finish_normal']
            depth = layer['thickness_m']
            # Every original boundary point survives on BOTH interfaces,
            # including complete wall extents and door/window contours.
            vertices = {tuple(p) for f in layer['faces'] for p in f}
            for p in face:
                self.assertIn(tuple(p), vertices)
                self.assertIn(tuple(p[i]+depth*n[i] for i in range(3)), vertices)
            for hid in layer['finish_host_ids']:
                host = self.scene['mounting_hosts'][hid]
                self.assertEqual(depth,host['finish']['thickness_m'])
        self.assertFalse(any(m['id'].startswith(('host-face-','support-')) for m in self.scene['meshes']))
        bad = deepcopy(self.scene)
        layer = next(m for m in bad['meshes'] if m['id'].startswith('finish-layer-'))
        layer['faces'].pop()
        self.assertTrue(solid_findings(bad))
        reversed_scene = deepcopy(self.scene)
        layer = next(m for m in reversed_scene['meshes'] if m['id'].startswith('finish-layer-'))
        layer['faces'] = [f[::-1] for f in layer['faces']]
        self.assertTrue(solid_findings(reversed_scene))

    def test_keyhole_opening_and_translated_reversed_normal_sibling(self):
        # A complete 4 x 3 m wall with a 1 x 1 m window, joined by a
        # zero-width keyhole slit. These are chosen test dimensions.
        face = [[0,0,0],[4,0,0],[4,0,3],[0,0,3],
                [0,0,0],[1,0,1],[1,0,2],[2,0,2],[2,0,1],[1,0,1]]
        for direction,shift in ((-1,0),(1,17)):
            f = [[p[0]+shift,p[1],p[2]] for p in face]
            if direction==1: f.reverse()
            n = [0,direction,0]
            layer = dict(id='finish-layer-unrelated', faces=extrude(f,n,.023))
            scene = dict(meshes=[layer])
            self.assertEqual(solid_findings(scene), [])
            triangles,_ = _triangles([layer])
            p = np.array([[1.5+shift,direction*.023,1.5]])
            self.assertGreater(float(_point_triangle_distance(p,triangles).min()),.49)
            caps = [f for f in layer['faces'] if abs(normal(f)[1])>.99]
            self.assertTrue(any(normal(f)[1]*direction > .99 for f in caps))
            # A finish-zone boundary through the window must create a
            # closed notch, not retain the keyhole's doubled boundary slit.
            for high in (1.5,2.5):
                clipped = clip(clip(f,0,shift+.5,True),0,shift+high,False)
                notch = dict(id='finish-layer-opening-edge',faces=extrude(clipped,n,.023))
                self.assertEqual(solid_findings(dict(meshes=[notch])), [])
                triangles,_ = _triangles([notch])
                point = np.array([[shift+1.25,direction*.023,1.5]])
                self.assertGreater(float(_point_triangle_distance(point,triangles).min()),.24)
            with self.assertRaisesRegex(ValueError,'disconnected contours'):
                clip(clip(f,0,shift+1.2,True),0,shift+1.8,False)
            # Closed topology alone cannot hide a missing render support.
            from archpipe.concept.mounting import Host, Finish, MountItem, binding
            from dataclasses import asdict
            host = Host('other-host','wall',(shift,0,0),tuple(n),Finish('marble',.023))
            mounted = dict(id='other-fitting',faces=[[[shift+.1,direction*.023,.1],
                [shift+.2,direction*.023,.1],[shift+.2,direction*.023,.2]]],
                mounting=binding(MountItem('other-fitting'),host,0,'surface-mounted'))
            trial = dict(meshes=[dict(layer,group='shell',material='marble-bath'),mounted],
                         mounting_hosts={host.id:asdict(host)})
            self.assertEqual(surface_findings(trial), [])
            trial['meshes'].pop(0)
            self.assertTrue(surface_findings(trial))

    def test_ensuite_rail_is_carried_by_its_own_brackets(self):
        by = {m['id']:m for m in self.scene['meshes']}
        rail = by['detail-pe-hand-shower-rail']
        host = self.scene['mounting_hosts'][rail['mounting']['host_id']]
        n = np.array(host['normal'])
        plane = np.array(host['structural_point'])+n*host['finish']['thickness_m']
        rail_vertices = np.array([p for f in rail['faces'] for p in f])
        self.assertAlmostEqual(float(((rail_vertices-plane)@n).min()),.063)
        self.assertEqual(rail['faces'], next(m for m in self.before['meshes'] if m['id']==rail['id'])['faces'])
        for suffix in ('lower','upper'):
            bracket = by['detail-pe-hand-shower-bracket-'+suffix]
            vertices = np.array([p for f in bracket['faces'] for p in f])
            gaps = (vertices-plane)@n
            self.assertAlmostEqual(float(gaps.min()),0)
            self.assertGreater(float(gaps.max()),.063)
            # The rail's side intersects the solid bracket between the
            # rail's end rings; end-ring vertex distances miss that contact.
            triangles,_ = _triangles([rail])
            low,high = vertices.min(axis=0),vertices.max(axis=0)
            self.assertTrue(_tri_box_overlap(triangles,(low+high)/2,(high-low)/2).any())
        self.assertEqual(unsupported(self.scene), [])
        broken = deepcopy(self.scene)
        broken['meshes'] = [m for m in broken['meshes'] if m['id'] not in
                            ('detail-pe-hand-shower-bracket-lower','detail-pe-hand-shower-bracket-upper')]
        self.assertIn(rail['id'], {mid for mid,_ in unsupported(broken)})


if __name__=='__main__': unittest.main()
