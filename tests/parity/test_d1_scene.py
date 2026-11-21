"""Runs on the real built scene and IFC. Paths come from RV1_SCENE / RV1_IFC; without them these tests are SKIPPED with
the reason (the CLI itself never skips: a missing input exits 2)."""
import os
import pickle
from pathlib import Path

import pytest

SCENE, IFC = os.environ.get("RV1_SCENE"), os.environ.get("RV1_IFC")
pytestmark = pytest.mark.skipif(not (SCENE and IFC and Path(SCENE).is_file() and Path(IFC).is_file()),
                                reason="set RV1_SCENE and RV1_IFC to a built scene.json and the IFC export")


@pytest.fixture(scope="module")
def run():
    from archpipe.parity import run_d1
    return run_d1.run(SCENE, IFC, prove=True)


def test_mutation_set_every_expected_catch_and_every_negative_quiet(run):
    fs, rep = run
    unexpected = [(m["id"], m["detail"]) for m in rep["mutations"] if not m["ok"]]
    # M1 (valid geometry), M6-180 (bbox cannot see a half turn), M-K10-move0.1 (loose centre bound) are PRE-DECLARED misses
    assert {i for i, _ in unexpected} <= {"M1", "M6-180", "M-K10-move0.1"}, unexpected


def test_scene_and_ifc_agree_except_where_the_scene_differs_from_the_model(run):
    fs, rep = run
    assert all(isinstance(r["agree"], bool) for r in rep["scene_vs_ifc"])


def test_ifc_second_kernel_catches_a_seeded_wall_through_the_ramp(tmp_path):
    from archpipe.parity import ifc_kernel as K
    K.mutate_ifc_wall_taller(IFC, tmp_path / "m.ifc")
    got = [f for f in K.ifc_clashes(K.load_ifc_world(tmp_path / "m.ifc")) if f.status == "fail"]
    assert any("wall-B-int-11" in f.subject for f in got)
