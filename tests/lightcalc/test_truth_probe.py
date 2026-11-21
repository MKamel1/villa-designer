"""L6b truth question: dining-table centre, engine 963 lx vs the recorded Cycles probe 405 lx.

The frozen Cycles variants (knowledge/lighting/truth/) were produced by truth_probe_blender.py with the production light
constructor and probe method. Variant A (spots only, open table) must equal the analytic engine; variant C (spots +
pendant + the vase on the sensor) must reproduce the recorded probe file (405 / 467 lx direct)."""
import json
from pathlib import Path

from archpipe.lightcalc.direct import Placement, direct_illuminance
from archpipe.photometry import load as load_ies

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "knowledge" / "lighting" / "truth"
IES = ROOT / "knowledge" / "lighting" / "ies"
RECORDED = {"centre": 404.784524509424, "end": 466.64330695681167}      # out/villa/render-d1/lighting-measurements.json
MF = 0.8


def _cycles():
    d = json.loads((T / "cycles-variants-A-E.json").read_text(encoding="utf-8"))
    return {k: [r["direct_lux"] for r in v["readings"]] for k, v in d.items()}


def _analytic(z_shift=0.0):
    cases = json.loads((T / "cases-A-E.json").read_text(encoding="utf-8"))
    spots = next(c for c in cases if c["name"] == "A_spots")
    ph = load_ies(IES / "LSEVO-AAHENX.ies")
    scale = spots["lights"][0]["lumens"] / ph.integrated_flux()          # the render scales the file to the spec lumens
    pl = [Placement(l["id"], ph, (l["position"][0], l["position"][1], l["position"][2] + z_shift), aim=tuple(l["aim"]))
          for l in spots["lights"] if l["ies"].endswith("AAHENX.ies")]
    return [direct_illuminance(pl, p) * MF * scale for p in spots["points"]]


def test_cycles_open_table_equals_analytic_engine():
    """No vase: Cycles (IES, aim, energy, MF, sensor) agrees with the closed-form engine to 1.5 % at centre and end."""
    a, c = _analytic(), _cycles()["A_spots"]
    for k in (0, 1):
        assert abs(c[k] / a[k] - 1) < 0.015, (k, c[k], a[k])


def test_engine_963_is_total_light_and_direct_is_939():
    """The engine's 963 lx at the centre is TOTAL light (Radiance ab 6, closed walls); its direct part is 939 lx (emitter at
    the recess aperture z = -0.30, knowledge/lighting/L6-dining-result.json). Cycles open-table direct is 952 lx with the
    emitter at the rendered z = -0.33: the 1.3 % difference is the 30 mm emitter datum."""
    hi, lo = _analytic(0.03)[0], _analytic(0.0)[0]            # shift +0.03 -> z = -0.30
    assert abs(hi - 939) < 3 and abs(lo - 952) < 3 and hi < lo
    res = json.loads((ROOT / "knowledge" / "lighting" / "L6-dining-result.json").read_text(encoding="utf-8"))
    pl = res["variants"]["built"]["scenes"]["full"]["planes"]["table-centre-point"]
    assert abs(pl["total"]["em"] - 963) < 1 and abs(pl["direct_only"]["em"] - 939) < 1


def test_recorded_probe_is_the_vase_obstructed_reading():
    c = _cycles()
    assert abs(c["C_spots_pendant_vase"][0] / RECORDED["centre"] - 1) < 0.02
    assert abs(c["C_spots_pendant_vase"][1] / RECORDED["end"] - 1) < 0.02
    assert c["D_spots_vase"][0] == 0.0            # the vase removes the spot light at the sensor entirely


def test_unobstructed_centre_is_more_than_twice_the_recorded_probe():
    c = _cycles()
    assert c["A_spots"][0] > 2 * RECORDED["centre"]
    assert c["B_spots_pendant"][0] > 3 * RECORDED["centre"]
