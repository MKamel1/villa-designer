"""V5 single-light orientation probe (found on L6c's ERCO wallwasher: Cycles throws the light 90 deg away from the engine)."""
import os

import pytest

from archpipe.lightcalc.villa import Villa
from archpipe.lightverify import v5_engines as V5

needs_blender = pytest.mark.skipif(not os.path.exists(V5.BLENDER) or not os.path.exists(V5.JOBQ), reason="Blender/jobq (workstation) not available")


@needs_blender
def test_orientation_probe_is_sensitive_to_spin_of_an_asymmetric_light():
    """The probe must move when the light is turned: WW is asymmetric (C0 throw), so +90 deg of spin changes the pattern error a lot.
    (Whether spin 0 itself agrees is the design finding recorded in LV-findings.md, not asserted here.)"""
    v = Villa()
    only = lambda r: next(x for x in r if x["kind"] == "WW")
    base = only(V5.kind_orientation(v))
    turned = only(V5.kind_orientation(v, spin_add=90.0))
    assert abs(base["l1"] - turned["l1"]) > 0.3


@needs_blender
def test_orientation_probe_stays_quiet_for_a_symmetric_downlight():
    v = Villa()
    dl = next(x for x in V5.kind_orientation(v) if x["kind"] == "DL")
    assert dl["l1"] <= V5.ORIENT_L1_TOL and abs(dl["sum_dev"]) <= V5.ORIENT_SUM_TOL
