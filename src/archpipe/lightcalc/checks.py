"""Lighting checks that emit `contracts.CheckResult` (criteria LA1-LA4, LA9, LA12, LA13).

Every function returns CheckResult records. A check that cannot run returns
`not_evaluated` (never a pass). A threshold whose card is `unverified` can never
produce a hard `fail`: it produces `warn` (LANES rule 4: unverified cannot gate).
"""
from __future__ import annotations

import math

from ..contracts import CheckResult
from .direct import Placement, direct_illuminance, luminance_toward, upward_light_ratio, _norm
from .geometry import dist_to_edges
from .metrics import GridStats
from .sources import CARDS

LANE = "L6"
OVER_LIGHTING_FACTOR = 1.5          # POLICY (card L6-POLICY-LA2-over-lighting-1.5x)
LUMINANCE_CAP_CD_M2 = 3000.0        # POLICY (card L6-POLICY-LA4-luminance-3000)
AXIS_TOL_M = 0.010                  # POLICY (card L6-POLICY-LA9-axis-tolerance-10mm)


def _res(criterion, status, subject, card_ids, *, achieved=None, required=None, unit="", message="",
         element_ids=(), gate=False):
    return CheckResult(criterion=criterion, lane=LANE, status=status, subject=subject, achieved=achieved,
                       required=required, unit=unit, message=message, source_ids=tuple(card_ids),
                       element_ids=tuple(element_ids), gate=gate)


def _gate_status(ok: bool, card_ids) -> str:
    """pass/fail, except that a rule resting only on an unverified card can only warn."""
    if ok:
        return "pass"
    if all(CARDS[c].status == "unverified" for c in card_ids):
        return "warn"
    return "fail"


# ---------------------------------------------------------------- LA1 / LA2 / LA3

def check_la1(subject: str, em: float, target: float, *, gauge: str = "average", tol: float = 0.10,
              emin: float | None = None) -> CheckResult:
    """Task illuminance within +/-10 % of the card (average-gauged); a minimum-gauged
    task must reach the card (IES p.33.25: 'Minima and maxima must be achieved as intended')."""
    cards = ["IES-HB10-p33.25-avg-allowance"]
    if gauge == "minimum":
        val = em if emin is None else emin
        ok = val >= target
        msg = f"minimum-gauged task: achieved {val:.0f} lx vs card {target:.0f} lx minimum"
        return _res("LA1", _gate_status(ok, cards), subject, cards, achieved=val, required=target, unit="lx", message=msg)
    lo, hi = target * (1 - tol), target * (1 + tol)
    ok = lo <= em <= hi
    msg = (f"Eavg {em:.0f} lx vs card {target:.0f} lx; allowed {lo:.0f}-{hi:.0f} lx "
           f"({em / target:.2f}x of target)")
    return _res("LA1", _gate_status(ok, cards), subject, cards, achieved=em, required=target, unit="lx", message=msg)


def check_la2(subject: str, em: float, target: float, *, factor: float = OVER_LIGHTING_FACTOR) -> CheckResult:
    """Over-lighting cap (POLICY): Eavg must not exceed `factor` x target."""
    cards = ["L6-POLICY-LA2-over-lighting-1.5x"]
    cap = factor * target
    ok = em <= cap
    msg = (f"Eavg {em:.0f} lx vs cap {cap:.0f} lx ({factor:g} x card {target:.0f} lx): "
           f"{em / target:.2f} x target")
    return _res("LA2", "pass" if ok else "fail", subject, cards, achieved=em, required=cap, unit="lx", message=msg)


def check_la3(subject: str, stats: GridStats, *, u0_min: float | None = None,
              max_avg_limit: float | None = None, avg_min_limit: float | None = None) -> list[CheckResult]:
    """Uniformity reporting. Without a limit the result is `pass` as a report
    (IES 33.3.4: report where cited); with a limit it is evaluated."""
    base = ["IES-HB10-p33.25-uniformity-targets"]
    amin = "inf" if stats.avg_min == float("inf") else f"{stats.avg_min:.2f}"
    rep = (f"n={stats.n} Em {stats.em:.0f} Emin {stats.emin:.0f} Emax {stats.emax:.0f} lx; "
           f"U0 {stats.u0:.2f}; max:avg {stats.max_avg:.2f}; avg:min {amin}")
    out = []
    if u0_min is None and max_avg_limit is None and avg_min_limit is None:
        out.append(_res("LA3", "pass", subject, base, achieved=stats.u0, unit="U0", message="reported: " + rep))
        return out
    if u0_min is not None:
        cards = base + ["EN12464-1-task-U0-0.6"]
        ok = stats.u0 >= u0_min
        out.append(_res("LA3", "pass" if ok else "fail", subject, cards, achieved=stats.u0, required=u0_min,
                        unit="U0", message=f"U0 {stats.u0:.2f} vs required >= {u0_min:.2f}; " + rep))
    if max_avg_limit is not None:
        ok = stats.max_avg <= max_avg_limit
        out.append(_res("LA3", "pass" if ok else "fail", subject, base, achieved=stats.max_avg,
                        required=max_avg_limit, unit="max:avg", message=f"max:avg {stats.max_avg:.2f} vs <= {max_avg_limit:.2f}; " + rep))
    if avg_min_limit is not None:
        ok = stats.avg_min <= avg_min_limit
        out.append(_res("LA3", "pass" if ok else "fail", subject, base, achieved=None if stats.avg_min == float("inf") else stats.avg_min,
                        required=avg_min_limit, unit="avg:min", message=f"avg:min {amin} vs <= {avg_min_limit:.2f}; " + rep))
    return out


# ---------------------------------------------------------------- LA4

def check_la4_ugr(subject: str, ugr: float | None, *, limit: float = 19.0, method: str = "CIE 117 formula",
                  position_index_verified: bool = False) -> CheckResult:
    """UGR against the study limit. UGR values are rounded for comparison (ZVEI paper: rounded UGR
    must not exceed the limit). If the position index has not been verified against a held
    source the result cannot gate (status warn/pass-as-report)."""
    cards = ["UGR-limit-19-reading-writing", "SLL-p207-UGR-basic-equation"]
    if ugr is None or not math.isfinite(ugr):
        return _res("LA4", "not_evaluated", subject, [], message="no UGR could be computed (no luminaires in view or missing Lb)")
    ok = round(ugr) <= limit
    msg = f"UGR {ugr:.1f} ({method}) vs limit {limit:g}"
    if not position_index_verified:
        return _res("LA4", "pass" if ok else "warn", subject, cards, achieved=ugr, required=limit, unit="UGR",
                    message=msg + "; position index not verified against a held CIE source, so it cannot gate")
    return _res("LA4", "pass" if ok else "fail", subject, cards, achieved=ugr, required=limit, unit="UGR", message=msg)


def check_la4_luminance(subject: str, sightlines: list[dict], placements: list[Placement], *,
                        cap: float = LUMINANCE_CAP_CD_M2, cone_deg: float = 45.0) -> list[CheckResult]:
    """No luminaire above `cap` cd/m2 toward an observer within `cone_deg` of a sightline, unless shielded.

    sightline = {"id", "eye": (x,y,z), "dir": (dx,dy,dz)}; a placement with
    meta['shielded'] True is excluded (shielded sources are the declared exception).
    """
    out = []
    for sl in sightlines:
        cards = ["L6-POLICY-LA4-luminance-3000"] + list(sl.get("cards", ()))
        eye = tuple(sl["eye"])
        sdir = _norm(tuple(sl["dir"]))
        worst = (0.0, "")
        for p in placements:
            if p.meta.get("shielded"):
                continue
            v = tuple(p.position[i] - eye[i] for i in range(3))
            d = math.sqrt(sum(c * c for c in v))
            if d == 0:
                continue
            ang = math.degrees(math.acos(max(-1.0, min(1.0, sum(v[i] / d * sdir[i] for i in range(3))))))
            if ang > cone_deg:
                continue
            try:
                L, _a, _d = luminance_toward(p, eye)
            except ValueError as exc:
                out.append(_res("LA4", "not_evaluated", f"{subject}/{sl['id']}", [], message=str(exc), element_ids=(p.id,)))
                continue
            if L > worst[0]:
                worst = (L, p.id)
        ok = worst[0] <= cap
        msg = (f"max source luminance within {cone_deg:g} deg of the sightline {worst[0]:.0f} cd/m2 "
               f"({worst[1] or 'none in view'}) vs cap {cap:.0f} cd/m2")
        out.append(_res("LA4", "pass" if ok else "fail", f"{subject}/{sl['id']}", cards, achieved=worst[0],
                        required=cap, unit="cd/m2", message=msg, element_ids=(worst[1],) if worst[1] else ()))
    return out


# ---------------------------------------------------------------- LA9

def check_la9(subject: str, luminaires: list[dict], axes_x: list[float], axes_y: list[float], *,
              mode: str = "any", tol: float = AXIS_TOL_M, work_plane_z: float = 0.85,
              wallwash: list[dict] | None = None, room_polygon: list | None = None) -> list[CheckResult]:
    """RCP setting-out. luminaires: [{"id","x","y","z","shr_max"?}] metres.

    * every ceiling luminaire lies on a declared axis (mode 'any': on an x- or y-axis line;
      'both': on a node, i.e. both) within `tol`;
    * nearest-neighbour spacing <= shr_max x (z - work_plane_z) for luminaires that carry shr_max;
    * wall-washers (list of {"id","x","y"}) sit 0.6-1.0 m from the nearest wall (unverified card: warn only).
    """
    out = []
    off = []
    for l in luminaires:
        dx = min((abs(l["x"] - a) for a in axes_x), default=math.inf)
        dy = min((abs(l["y"] - a) for a in axes_y), default=math.inf)
        ok = (dx <= tol and dy <= tol) if mode == "both" else (dx <= tol or dy <= tol)
        if not ok:
            off.append((l["id"], round(min(dx, dy) * 1000, 1)))
    cards = ["L6-POLICY-LA9-axis-tolerance-10mm"]
    n = len(luminaires)
    pct = 100.0 * (n - len(off)) / n if n else 0.0
    out.append(_res("LA9", "not_evaluated" if n == 0 else ("pass" if not off else "fail"), f"{subject}/axes", cards if n else [],
                    achieved=pct, required=100.0, unit="% on axis",
                    message=(f"{n - len(off)}/{n} luminaires on a declared axis within {tol * 1000:.0f} mm"
                             + (f"; off-axis (id, nearest-axis offset mm): {off}" if off else "")),
                    element_ids=[o[0] for o in off]))
    # spacing
    bad = []
    for i, a in enumerate(luminaires):
        shr = a.get("shr_max")
        if shr is None:
            continue
        others = [b for j, b in enumerate(luminaires) if j != i]
        if not others:
            continue
        nn = min(math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for b in others)
        lim = shr * (a["z"] - work_plane_z)
        if nn > lim + 1e-9:
            bad.append((a["id"], round(nn, 3), round(lim, 3)))
    if any(l.get("shr_max") is not None for l in luminaires):
        scards = ["L6-LA9-spacing-SHR"]
        out.append(_res("LA9", "pass" if not bad else "fail", f"{subject}/spacing", scards,
                        achieved=float(len(bad)), required=0.0, unit="luminaires over SHR",
                        message=("nearest-neighbour spacing within SHR_max x height for all" if not bad else
                                 f"over SHR (id, spacing m, limit m): {bad}"), element_ids=[b[0] for b in bad]))
    if wallwash and room_polygon:
        wcards = ["L6-LA9-washer-setback-0.6-1.0"]
        wb = []
        for w in wallwash:
            d = dist_to_edges((w["x"], w["y"]), room_polygon)
            if not (0.6 - 1e-9 <= d <= 1.0 + 1e-9):
                wb.append((w["id"], round(d, 3)))
        out.append(_res("LA9", _gate_status(not wb, wcards), f"{subject}/wall-wash setback", wcards,
                        achieved=float(len(wb)), required=0.0, unit="washers outside 0.6-1.0 m",
                        message=("all wall-washers 0.6-1.0 m from the wall" if not wb else f"outside range (id, setback m): {wb}"),
                        element_ids=[b[0] for b in wb]))
    return out


# ---------------------------------------------------------------- LA12

E3 = {"ev_pre": 10.0, "ev_post": 2.0, "i_pre": 10000.0, "i_post": 1000.0, "ulr": 0.15, "lb": 10.0}


def check_la12(subject: str, *, boundary_ev: list[float] | None = None,
               exterior: list[Placement] | None = None, neighbour_points: list[tuple] | None = None,
               facade_lb: float | None = None, curfew: str = "post") -> list[CheckResult]:
    """Obtrusive light, zone E3 (SLL Table 3.2): boundary Ev, intensity toward neighbour points,
    ULR, facade luminance. curfew 'pre' or 'post' selects the limit column."""
    c = ["SLL-T3.2-E3"]
    ev_lim = E3["ev_" + curfew]
    i_lim = E3["i_" + curfew]
    out = []
    if boundary_ev is not None:
        worst = max(boundary_ev)
        out.append(_res("LA12", "pass" if worst <= ev_lim else "fail", f"{subject}/Ev ({curfew}-curfew)", c,
                        achieved=worst, required=ev_lim, unit="lx",
                        message=f"max vertical illuminance on the boundary {worst:.2f} lx vs E3 {ev_lim:g} lx"))
    if exterior is not None and neighbour_points:
        worst, wid = 0.0, ""
        for p in exterior:
            for q in neighbour_points:
                v = tuple(q[i] - p.position[i] for i in range(3))
                if sum(x * x for x in v) == 0:
                    continue
                val = p.intensity_toward(_norm(v))
                if val > worst:
                    worst, wid = val, p.id
        out.append(_res("LA12", "pass" if worst <= i_lim else "fail", f"{subject}/I toward neighbours ({curfew}-curfew)", c,
                        achieved=worst, required=i_lim, unit="cd",
                        message=f"max intensity toward neighbour points {worst:.0f} cd ({wid or 'n/a'}) vs E3 {i_lim:g} cd",
                        element_ids=(wid,) if wid else ()))
    if exterior is not None:
        worst, wid = 0.0, ""
        for p in exterior:
            u = upward_light_ratio(p)
            if u > worst:
                worst, wid = u, p.id
        out.append(_res("LA12", "pass" if worst <= E3["ulr"] else "fail", f"{subject}/ULR", c, achieved=worst,
                        required=E3["ulr"], unit="fraction",
                        message=f"worst upward light ratio {worst:.3f} ({wid or 'n/a'}) vs E3 {E3['ulr']} (installed attitude)",
                        element_ids=(wid,) if wid else ()))
    if facade_lb is not None:
        out.append(_res("LA12", "pass" if facade_lb <= E3["lb"] else "fail", f"{subject}/facade Lb", c,
                        achieved=facade_lb, required=E3["lb"], unit="cd/m2",
                        message=f"mean facade luminance {facade_lb:.1f} cd/m2 vs E3 {E3['lb']:g}"))
    if not out:
        out.append(_res("LA12", "not_evaluated", subject, [], message="no obtrusive-light inputs supplied"))
    return out


# ---------------------------------------------------------------- LA13

def check_la13(subject: str, route: list[tuple[float, float, float]], emergency: list[Placement], *,
               required_lx: float = 1.0, edge_offset: float = 0.0, spacing: float = 0.25) -> CheckResult:
    """Emergency path: direct illuminance (battery lumens = the placements' `dim`-scaled photometry)
    along the route centre line >= `required_lx`. route = polyline of (x, y, z) at floor/tread level
    (horizontal plane). Direct component only (conservative; no inter-reflection)."""
    cards = ["EN1838-1lx-escape-route"]
    if not emergency or len(route) < 2:
        return _res("LA13", "not_evaluated", subject, [], message="no emergency luminaires or route supplied")
    pts = []
    for a, b in zip(route, route[1:]):
        L = math.dist(a, b)
        n = max(1, math.ceil(L / spacing))
        for k in range(n):
            t = k / n
            pts.append(tuple(a[i] + t * (b[i] - a[i]) for i in range(3)))
    pts.append(route[-1])
    vals = [direct_illuminance(emergency, p, (0, 0, 1)) for p in pts]
    lo = min(vals)
    where = pts[vals.index(lo)]
    ok = lo >= required_lx
    msg = (f"min centre-line illuminance {lo:.2f} lx at ({where[0]:.2f}, {where[1]:.2f}) over {len(pts)} points "
           f"vs required {required_lx:g} lx (direct only)")
    return _res("LA13", "pass" if ok else "fail", subject, cards, achieved=lo, required=required_lx, unit="lx", message=msg)
