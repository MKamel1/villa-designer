"""V8 mutation tests: seed known errors and confirm that the layer meant to catch each one does.

Each mutation returns {name, layer, caught, detail}. A mutation is `caught` when the target layer reports a fail on the
mutated input that it does NOT report on the original. 100 % recall is the bar (LV-V8-MUT); a miss means that layer
cannot be trusted for that class of error.
"""
from __future__ import annotations

import dataclasses
import json
import shutil
import tempfile
from pathlib import Path

from .common import LayerResult, check
from .sources import ids

SRC = ids("LV-V8-MUT")


def _fails(L) -> set:
    return {r.subject for r in L.results if r.status == "fail"}


def _fresh_villa(fixtures=None):
    from ..lightcalc.villa import Villa
    return Villa(fixtures=fixtures)


def m_doubled_lumens(villa):
    from ..fixture_record import PRODUCTS
    from . import v1_inputs as V1
    from ..lightcalc.villa import Villa
    base = _fails(V1.check_inputs(villa))
    old = PRODUCTS["DL"]
    PRODUCTS["DL"] = dict(old, lm=old["lm"] * 2)
    try:
        got = _fails(V1.check_inputs(Villa()))
    finally:
        PRODUCTS["DL"] = old
    return "V1", got - base, "product record DL lumens doubled (732.6 -> 1465.2 lm)"


def m_wrong_watts(villa):
    from ..fixture_record import PRODUCTS
    from . import v1_inputs as V1
    from ..lightcalc.villa import Villa
    base = _fails(V1.check_inputs(villa))
    old = PRODUCTS["ADJ"]
    PRODUCTS["ADJ"] = dict(old, watts=old["watts"] * 2)
    try:
        got = _fails(V1.check_inputs(Villa()))
    finally:
        PRODUCTS["ADJ"] = old
    return "V1", got - base, "product record ADJ watts doubled"


def _fx(villa, fid, **kw):
    return [dataclasses.replace(f, **kw) if f.id == fid else f for f in villa.fixtures]


def m_into_ceiling(villa):
    from . import v2_placement as V2
    f = next(f for f in villa.fixtures if f.id == "DL-lounge-01")
    base = _fails(V2.check_placement(villa))
    got = _fails(V2.check_placement(_fresh_villa(_fx(villa, f.id, z=f.z + 0.30))))
    return "V2", got - base, "DL-lounge-01 moved 300 mm up into the slab"


def m_datum_swap(villa):
    from . import v2_placement as V2
    f = next(f for f in villa.fixtures if f.id == "DL-lounge-01")
    base = _fails(V2.check_placement(villa))
    got = _fails(V2.check_placement(_fresh_villa(_fx(villa, f.id, z=f.z + 1.2))))
    return "V2", got - base, "DL-lounge-01 z shifted by the Revit/scene datum difference (1.2 m)"


def m_sensor_in_vase(villa, ts):
    from . import scene_geom as G, v3_sensors as V3
    pl = next(p for p in villa.planes() if p.id == "dining-table")
    pts, _, _ = V3.plane_points(pl)
    cx, cy = pts[len(pts) // 2]                      # stands on a real sensor point, as the October vase did
    base = V3.check_plane(ts, pl)["blocked"]
    import numpy as np
    c = np.array([[x, y, z] for x in (cx - 0.1, cx + 0.1) for y in (cy - 0.1, cy + 0.1) for z in (pl.z, pl.z + 0.4)])
    ts.add(G._tris_from_corners(c), "MUTANT-vase")
    ts.build()
    try:
        got = V3.check_plane(ts, pl)["blocked"]
    finally:
        ts.remove("MUTANT-vase")
    return "V3", ({"dining-table"} if got > base else set()), "0.20 x 0.20 x 0.40 m vase standing on a dining-table sensor point"


def m_plane_too_high(villa, ts):
    from . import v3_sensors as V3
    pl = next(p for p in villa.planes() if p.id == "dining-table")
    row = V3.check_plane(ts, dataclasses.replace(pl, z=pl.z + 0.03))
    base = V3.check_plane(ts, pl)
    caught = row["worst_gap_mm"] is not None and row["worst_gap_mm"] > 5 and not (base["worst_gap_mm"] is not None and base["worst_gap_mm"] > 5)
    return "V3", ({"dining-table"} if caught else set()), "dining-table plane raised 30 mm above the table top"


def m_rotated_ies():
    from . import ies, ldt, v10_manufacturer as V10
    c = "LSEVO-AAKR2I"
    b = V10.LIB / c
    di = ies.parse((b / ("mfr_%s.ies" % c)).read_text(errors="replace"))
    dl = ldt.parse((b / (c + ".ldt")).read_text(errors="replace"))
    ok0, _ = V10.cross_check(di, dl)
    k = len(di.cd) // 4
    di.cd = di.cd[k:] + di.cd[:k]                           # the same file turned 90 deg about its axis
    ok1, worst = V10.cross_check(di, dl)
    return "V10", ({c} if ok0 and not ok1 else set()), "wall-washer .ies rotated 90 deg against its .ldt (axis points differ %.0f %%)" % (100 * worst)


def m_doubled_radiance(villa, rad_dir):
    from . import v5_engines as V5
    src = Path(rad_dir) / "B-guest-wc.json"
    tmp = Path(tempfile.mkdtemp(prefix="lv-mut-"))
    d = json.loads(src.read_text())
    d["zones"] = {z: {ab: [v * 2 for v in vals] for ab, vals in zz.items()} for z, zz in d["zones"].items()}
    (tmp / "B-guest-wc.json").write_text(json.dumps(d))
    keep = dict(V5.ROOMS)
    V5.ROOMS.clear()
    V5.ROOMS["guest WC"] = keep["guest WC (small wet room)"]
    try:
        L = V5.run(villa, tmp, with_cycles=False)
        got = _fails(L)
    finally:
        V5.ROOMS.clear()
        V5.ROOMS.update(keep)
        shutil.rmtree(tmp, ignore_errors=True)
    return "V5", got, "Radiance output of the guest WC doubled (a lamp-scale error inside one engine)"


def m_driver_over_limit(villa):
    from ..concept import villa_lighting as VL
    from . import v12_headroom as V12
    base = _fails(V12.run(villa))
    d = dict(VL._drivers(), **{"Z-B-GUEST-WC-BASIN-TASK": 0.95})
    return "V12", _fails(V12.run(villa, drivers=d)) - base, "guest-WC basin zone driver raised from 0.42 to 0.95"


def run(villa, rad_dir, ts=None) -> LayerResult:
    L = LayerResult("V8")
    muts = [m_doubled_lumens(villa), m_wrong_watts(villa), m_into_ceiling(villa), m_datum_swap(villa)]
    if ts is not None:
        muts += [m_sensor_in_vase(villa, ts), m_plane_too_high(villa, ts)]
    muts += [m_rotated_ies(), m_doubled_radiance(villa, rad_dir), m_driver_over_limit(villa)]
    for layer, caught, detail in muts:
        L.results.append(check("LV8", "pass" if caught else "fail", detail, SRC, message="%s %s: %s" % (layer, "caught" if caught else "MISSED", detail)))
        L.table.append(dict(layer=layer, caught=bool(caught), detail=detail))
    n = sum(1 for _, c, _ in muts if c)
    L.notes.append("mutation recall %d / %d" % (n, len(muts)))
    return L
