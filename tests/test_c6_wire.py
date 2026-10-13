"""C6 view-intent wiring: finite walls, glazing and outward doorway rays."""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from archpipe.concept.render_views import (
    camera_wall_sightline_clearance, scene_wall_hosts, wall_sightline_findings)

FIXTURE = Path(__file__).parent / 'fixtures/c6-wall-clearance.json'


class WallSightlineTest(unittest.TestCase):
    def setUp(self):
        self.scene = json.loads(FIXTURE.read_text())
        self.views = {v['id']: v for v in self.scene['views']}
        self.hosts = scene_wall_hosts(self.scene)

    def test_forward_partition_rectangle_and_clear_siblings(self):
        view = {'camera': {'position': [0, 0, 1.35], 'target': [1, 0, 1.35]}}
        wall = (.95, -1, 1.05, 1)
        self.assertAlmostEqual(camera_wall_sightline_clearance(view, [wall])[0][1], .95)
        self.assertEqual(camera_wall_sightline_clearance(view, [(-1.05, -1, -.95, 1),
                                                                (.1, 2, .2, 3), (1, -1, 1.1, 1)]), [])
        self.assertEqual(camera_wall_sightline_clearance(view, [(-.1, -.1, .1, .1)])[0][1], 0)

    def test_real_v30_outward_face_quiet_inward_and_inside_fire(self):
        view = self.views['v30-under-ramp-store']
        self.assertEqual(wall_sightline_findings(view, self.hosts), [])
        reverse = deepcopy(view)
        x, y, z = reverse['camera']['position']
        reverse['camera']['target'] = [x, y-1, z]
        hits = camera_wall_sightline_clearance(reverse, self.hosts)
        self.assertEqual(hits[0], ('shell-038-paint-exterior-grey-green', 0.0))
        inside = deepcopy(view)
        inside['camera']['position'][1] -= .001
        self.assertTrue(wall_sightline_findings(inside, self.hosts))

    def test_real_v27_window_is_not_an_opaque_wall(self):
        view = self.views['v27-east-yard-above']
        self.assertEqual(wall_sightline_findings(view, self.hosts), [])
        opaque = deepcopy(self.scene)
        for material in opaque['materials'].values():
            if material['kind'] == 'glass':
                material['kind'] = 'principled'
        hits = camera_wall_sightline_clearance(view, scene_wall_hosts(opaque))
        self.assertTrue(hits, 'opaque injected glazing must block the real through-window view')
        self.assertLess(hits[0][1], 1.0)

    def test_real_wall_and_camera_translate_and_rename_together(self):
        shifted = deepcopy(self.scene)
        offset = [40, -20, 7]
        for mesh in shifted['meshes']:
            mesh['id'] = 'other-' + mesh['id']
            for face in mesh['faces']:
                for point in face:
                    for axis in range(3):
                        point[axis] += offset[axis]
        view = deepcopy(self.views['v30-under-ramp-store'])
        view['id'] = 'other-villa'
        for field in ('position', 'target'):
            view['camera'][field] = [v+d for v, d in zip(view['camera'][field], offset)]
        hosts = scene_wall_hosts(shifted)
        self.assertEqual(wall_sightline_findings(view, hosts), [])
        x, y, z = view['camera']['position']
        view['camera']['target'] = [x, y-1, z]
        self.assertIn('other-villa: camera faces wall other-shell-038', wall_sightline_findings(view, hosts)[0])

    def test_plan_review_calls_the_production_screen(self):
        from scripts import villa_render_views as review
        scene = deepcopy(self.scene)
        scene['props'] = []
        view = deepcopy(self.views['v30-under-ramp-store'])
        x, y, z = view['camera']['position']
        view['camera']['target'] = [x, y-1, z]
        view['subjects'] = []
        scene['views'] = [view]
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'scene.json').write_text(json.dumps(scene))
            output = io.StringIO()
            with patch.object(review, 'OUT', Path(folder)), contextlib.redirect_stdout(output), \
                    patch('archpipe.concept.garden_g6.scene_findings', return_value=[]):
                self.assertEqual(review.main([]), 1)
            self.assertIn('v30-under-ramp-store: camera faces wall', output.getvalue())
            self.assertTrue(Path(folder, 'views-plan.png').is_file())


if __name__ == '__main__':
    unittest.main()
