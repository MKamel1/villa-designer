"""Orientation of the Cycles light (L6d, LV defect A): the azimuth offset of `villa_scene.add_light` was calibrated on straight-down
lights only, so a tilted asymmetric light (the wallwasher) was thrown 90 deg off the engine's pattern. The light's rotation must be the
engine's own (`Placement.rotation`) composed with the calibrated Rz(90) frame change, for every aim and spin.
Runs Blender headless for the matrix only (no render); the rendered proof is LV's `v5_engines.kind_orientation` (tests/lightverify)."""
import json
import math
import os
import subprocess
import sys

import pytest

from archpipe.lightcalc.direct import Placement

BLENDER = os.path.expanduser("~/opt/blender/blender")
pytestmark = pytest.mark.skipif(not os.path.exists(BLENDER), reason="Blender (workstation) not available")

CASES = [((0, 0, -1), 0.0), ((0, 0, -1), 37.0), ((0, -0.25, -1), 0.0), ((0.25, 0, -1), 0.0), ((-0.25, 0, -1), 0.0), ((0, 0.25, -1), 0.0),
         ((0.35, 0, -1), 0.0), ((0.3, 0.4, -0.5), 20.0), ((-0.3, -0.4, -0.6), 90.0), ((1, 0, 0), 0.0), ((0, 0.3, -0.55), 0.0)]

SCRIPT = r'''
import json, math, sys
sys.path.insert(0, %(src)r)
from mathutils import Vector
from archpipe.blender import villa_scene as VS
out = []
for aim, spin in json.loads(%(cases)r):
    m = VS.ies_rotation(aim, spin)
    old = Vector(aim).normalized().to_track_quat("-Z", "Y").to_euler()
    old.rotate_axis("Z", math.radians(spin + VS.IES_AZIMUTH_OFFSET_DEG))
    out.append({"new": [list(r) for r in m], "old": [list(r) for r in old.to_matrix()]})
print("RESULT" + json.dumps(out))
'''


@pytest.fixture(scope="module")
def mats():
    src = str(__import__("pathlib").Path(__file__).resolve().parents[2] / "src")
    r = subprocess.run([BLENDER, "-b", "--python-expr", SCRIPT % {"src": src, "cases": json.dumps(CASES)}], capture_output=True, text=True, timeout=300)
    line = next(l for l in r.stdout.splitlines() if l.startswith("RESULT"))
    return json.loads(line[len("RESULT"):])


def _rz90(m):
    c, s = math.cos(math.pi / 2), math.sin(math.pi / 2)
    rz = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    return [[sum(m[i][k] * rz[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _close(a, b, tol=1e-6):
    return all(abs(a[i][j] - b[i][j]) < tol for i in range(3) for j in range(3))


@pytest.mark.parametrize("k", range(len(CASES)))
def test_light_rotation_is_the_engines_composed_with_the_calibrated_frame(mats, k):
    aim, spin = CASES[k]
    eng = Placement.__new__(Placement)
    object.__setattr__(eng, "aim", tuple(aim)); object.__setattr__(eng, "spin_deg", spin)
    assert _close(mats[k]["new"], _rz90(eng.rotation()))
    aimed = [-mats[k]["new"][i][2] for i in range(3)]                                   # local -Z is the emission axis
    n = math.sqrt(sum(x * x for x in aim))
    assert all(abs(aimed[i] - aim[i] / n) < 1e-6 for i in range(3))


def test_straight_down_lights_are_unchanged(mats):
    """The calibration cases (DL, DESK, PEN-LIN aim straight down) keep exactly the matrix of the old construction."""
    for k, (aim, spin) in enumerate(CASES):
        if aim == (0, 0, -1):
            assert _close(mats[k]["new"], mats[k]["old"])


def test_the_old_construction_was_wrong_for_a_tilted_asymmetric_light(mats):
    """Negative / regression: for the wallwasher's aim (0, -0.25, -1) the old matrix differs from the engine's (the 90 deg error)."""
    k = CASES.index(((0, -0.25, -1), 0.0))
    assert not _close(mats[k]["old"], mats[k]["new"], 1e-3)


GAIN_SCRIPT = r'''
import json, sys
sys.path.insert(0, %(src)r)
from archpipe.blender import villa_scene as VS
out = {}
for name in %(names)r:
    p = %(root)r + "/knowledge/lighting/ies/" + name
    out[name] = [VS.ies_horizontal_planes(p), VS.ies_plane_gain(p)]
print("RESULT" + json.dumps(out))
'''


def test_multiplane_files_get_the_measured_gain_and_single_plane_files_do_not():
    """L6d (LV defect B): Cycles renders multi-plane Type-C files 8.6 % dim. WW (145 planes) and DESK (73) get the gain; DL, ADJ (1 plane) do not."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    names = ["ERCO-41374.ies", "ERCO-31327.ies", "ERCO-41321.ies", "ERCO-A9000028.ies"]
    r = subprocess.run([BLENDER, "-b", "--python-expr", GAIN_SCRIPT % {"src": str(root / "src"), "names": names, "root": str(root)}],
                       capture_output=True, text=True, timeout=300)
    out = json.loads(next(l for l in r.stdout.splitlines() if l.startswith("RESULT"))[len("RESULT"):])
    assert out["ERCO-41374.ies"] == [145, 1.094] and out["ERCO-31327.ies"] == [73, 1.094]
    assert out["ERCO-41321.ies"] == [1, 1.0] and out["ERCO-A9000028.ies"] == [1, 1.0]
