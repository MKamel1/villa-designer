"""Is L6c's change of the engine's patch-radiosity test (8 -> 16 patches, bar 6 % -> 8 %) a resolution correction or tuning?
Evidence kept as a test: against LV's own Radiance results, the guest WC converges with the patch count (the 8-patch value is
the outlier, not the 16-patch one), and at 24 patches it agrees within 3 %."""
from pathlib import Path

import pytest

from archpipe.lightcalc import radiosity, villa_report as VR
from archpipe.lightcalc.villa import MF, Villa

RAD = Path(__file__).resolve().parents[2] / "knowledge" / "lighting-verify" / "radiance"


@pytest.fixture(scope="module")
def guest_wc():
    v = Villa()
    pls = [p for p in v.cluster_placements("B-guest-wc") if p.layer not in VR.NIGHT_LAYERS]
    res = VR.ClusterRes.load(RAD / "B-guest-wc.json")
    vals = res.values("room-guest-wc", VR.full_levels(res))
    return v.cluster_room("B-guest-wc"), pls, sum(vals) / len(vals)


def test_radiosity_converges_towards_radiance_with_patch_count(guest_wc):
    room, pls, radiance = guest_wc
    dev = {n: radiosity.floor_mean_lux(room, pls, MF, n) / radiance - 1 for n in (8, 16, 24)}
    assert dev[8] > 0.06                                  # coarse: overstates (the 7-10 % L6c saw)
    assert abs(dev[16]) < abs(dev[8]) / 2                 # halving the patch size removes most of it
    assert abs(dev[24]) < 0.03                            # converged: agrees with Radiance
    assert dev[8] > dev[16] > dev[24]                     # monotone, i.e. a discretisation error, not noise


def test_a_wrong_reflectance_still_breaks_the_converged_agreement(guest_wc):
    from dataclasses import replace
    room, pls, radiance = guest_wc
    dark = replace(room, rho_wall=0.4)
    assert abs(radiosity.floor_mean_lux(dark, pls, MF, 16) / radiance - 1) > 0.08
