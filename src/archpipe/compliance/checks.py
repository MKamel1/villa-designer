"""Safety and quality checkers for a DesignModel (lane L1). International best practice is the gate; the Egyptian
Executive Regulations (Law 119/2008) are reported as INFORMATIVE rows (gate=False) from the same measured values.

Every checker returns a list of contracts.CheckResult. Missing data gives `not_evaluated` with the reason, never
`pass`. Each threshold is a SourceCard id in knowledge/eg/*.json (see sources.py).

Criterion ids follow docs/quality/a-plus-architecture.md: EG4 clear height, EG5 room size, EG6 doors, EG7 daylight and
openings, EG9 sills, LS1 stair geometry, LS2 open risers and gaps, LS3 guards, LS4 door near a flight, LS5 escape.
The EG ids are kept for continuity; the thresholds behind them are now the international ones.
"""
from __future__ import annotations

import math

from ..contracts import CheckResult
from .model import HABITABLE, DesignModel, Room

LANE = "L1"
SPHERE_MM = 100.0


def _res(criterion, status, subject, achieved=None, required=None, unit="", message="", sources=(), elements=(),
         gate=True):
    return CheckResult(criterion=criterion, lane=LANE, status=status, subject=subject, achieved=achieved,
                       required=required, unit=unit, message=message, source_ids=tuple(sources),
                       element_ids=tuple(elements), gate=gate)


def _ne(criterion, subject, reason, elements=(), gate=True):
    return _res(criterion, "not_evaluated", subject, message="not evaluated: " + reason, elements=elements, gate=gate)


def _room_label(r: Room) -> str:
    return "%s (%s)" % (r.id, r.name.split(" (")[0] if r.name else r.occupancy)


# ----------------------------------------------------------------------------------------------- EG4 heights
def check_clear_heights(m: DesignModel) -> list:
    out = []
    for r in m.rooms.values():
        samples = m.clear.get(r.id)
        if not samples:
            out.append(_ne("EG4", _room_label(r), "no clear-height data for this room", (r.id,)))
            continue
        habitable = r.occupancy in HABITABLE
        lo, hi = min(samples), max(samples)
        share23 = 100.0 * sum(1 for h in samples if h >= 2.3 - 1e-9) / len(samples)
        share24 = 100.0 * sum(1 for h in samples if h >= 2.4 - 1e-9) / len(samples)
        if habitable:
            ok = share23 >= 75.0 - 1e-9
            out.append(_res("EG4", "pass" if ok else "fail", _room_label(r) + " clear height",
                            round(share23, 1), 75.0, "% of floor >= 2.3 m",
                            "clear %.2f-%.2f m; %.0f %% of the floor is >= 2.3 m (needs 75 %%, Metric Handbook / NDSS); "
                            "%.0f %% is >= 2.4 m (the preferable height)" % (lo, hi, share23, share24),
                            ["mh-dwelling-ceiling-min"], (r.id,)))
            if ok and share24 < 100.0 - 1e-9:
                out.append(_res("EG4", "warn", _room_label(r) + " clear height, preferable 2.4 m",
                                round(share24, 1), 100.0, "% of floor >= 2.4 m",
                                "meets the 2.3 m minimum but only %.0f %% of the floor reaches the preferable "
                                "2.4 m" % share24, ["mh-dwelling-ceiling-min"], (r.id,), gate=False))
        else:
            out.append(_res("EG4", "pass" if lo >= 2.0 - 1e-9 else "warn", _room_label(r) + " clear height (service)",
                            round(lo, 2), 2.0, "m",
                            "%s room: min clear %.2f m (max %.2f); the ceiling minimum applies to habitable rooms; "
                            "2.0 m is the door/head height, project judgement" % (r.occupancy, lo, hi),
                            ["mh-dwelling-ceiling-min"], (r.id,), gate=False))
        # Egyptian ER Art.93: informative
        er_min = 2.30 if r.occupancy in ("bathroom", "wc", "ensuite", "hall", "corridor", "entrance", "landing",
                                         "utility", "stair") else 2.70
        out.append(_res("EG4", "pass" if lo >= er_min - 1e-9 else "fail", _room_label(r) + " [ER informative]",
                        round(lo, 2), er_min, "m",
                        "ER Art.93 reading: least clear %.2f m vs %.2f m (informative, not a gate)" % (lo, er_min),
                        ["er119-art93"], (r.id,), gate=False))
    if m.beam_clear_m is not None:
        ok = m.beam_clear_m >= 2.3 - 1e-9
        out.append(_res("EG4", "pass" if ok else "fail", "clear under the perimeter beams (all levels)",
                        m.beam_clear_m, 2.3, "m",
                        "beams 600 deep (ASSUMED section): %.2f m under the beam vs 2.3 m minimum; 0.10 m under the "
                        "2.4 m preferable, local to the perimeter and window heads" % m.beam_clear_m,
                        ["mh-dwelling-ceiling-min"], gate=True))
    return out


# --------------------------------------------------------------------------------------------- EG5 room sizes
def check_room_sizes(m: DesignModel) -> list:
    out = []
    bedrooms = [r for r in m.rooms.values() if r.occupancy == "bedroom" and not r.part_of]
    first_done = False
    for r in sorted(bedrooms, key=lambda r: -(r.area_m2 or 0)):
        a = r.area_m2 or r.rect_area
        wmin = min(r.w, r.d) - 0.15
        need_w = 2.75 if not first_done else 2.55
        first_done = True
        # a double bedroom: 11.5 m2; the first double 2.75 m wide, others 2.55 m (NDSS via Metric Handbook)
        out.append(_res("EG5", "pass" if a >= 11.5 - 1e-9 else "fail", _room_label(r) + " area", round(a, 2), 11.5,
                        "m2", "net area %.2f m2 vs 11.5 m2 for a double/twin bedroom (NDSS)" % a,
                        ["ndss-double-bedroom-area"], (r.id,)))
        out.append(_res("EG5", "pass" if wmin >= need_w - 1e-9 else "fail", _room_label(r) + " width", round(wmin, 2),
                        need_w, "m", "narrowest net dimension %.2f m vs %.2f m (NDSS)" % (wmin, need_w),
                        ["ndss-first-double-bedroom-width" if need_w == 2.75 else "ndss-other-double-bedroom-width"],
                        (r.id,)))
        out.append(_res("EG5", "pass" if (a >= 7.5 and wmin >= 2.5) else "fail", _room_label(r) + " [ER informative]",
                        round(a, 2), 7.5, "m2", "ER Art.94: %.2f m2 / %.2f m vs 7.5 m2 / 2.5 m" % (a, wmin),
                        ["er119-art94"], (r.id,), gate=False))
    for r in m.rooms.values():
        if r.occupancy in ("bathroom", "ensuite"):
            a = r.area_m2 or r.rect_area
            out.append(_res("EG5", "pass" if a >= 4.3 - 1e-9 else "warn", _room_label(r) + " area (target)",
                            round(a, 2), 4.3, "m2", "net area %.2f m2 vs 4.30 m2 recommended for an adaptable-dwelling "
                            "bathroom (Metric Handbook Fig 22.12d; a target, not a gate)" % a,
                            ["mh-bathroom-m42-4.30"], (r.id,), gate=False))
        if r.occupancy == "wc":
            a = r.area_m2 or r.rect_area
            out.append(_res("EG5", "pass" if a >= 2.61 - 1e-9 else "warn", _room_label(r) + " area (target)",
                            round(a, 2), 2.61, "m2", "net area %.2f m2 vs 2.61 m2 recommended (Metric Handbook "
                            "Fig 22.12c; a target)" % a, ["mh-wc-m42-2.61"], (r.id,), gate=False))
    return out


# ------------------------------------------------------------------------------------------------ EG6 doors
def check_doors(m: DesignModel) -> list:
    out = []
    for o in m.openings:
        if o.kind != "door":
            continue
        entrance = "core" in o.rooms
        need = 0.775 if entrance else 0.75
        sid = "ukadm-entrance-door-min" if entrance else "ukadm-door-750"
        label = "door %s (%s)" % (o.id, "/".join(o.rooms))
        # the spec holds the nominal opening; clear opening is not modelled, so a pass means "could qualify"
        ok = o.width >= need - 1e-9
        out.append(_res("EG6", "pass" if ok else "fail", label, round(o.width, 3), need, "m",
                        "nominal width %.2f m vs %.3f m clear needed (Approved Document M); clear opening is not "
                        "modelled, so a pass means the door could qualify" % (o.width, need), [sid], (o.id,),
                        gate=False))
        if o.height < 2.0 - 1e-9:
            out.append(_res("EG6", "warn", label + " height", round(o.height, 2), 2.0, "m",
                            "leaf height %.2f m is under the 2.0 m head height (reduced door under the ramp, a "
                            "project decision; no source card)" % o.height, ["ukadk-stair-headroom-min"], (o.id,),
                            gate=False))
        er = 0.70 if any(k in " ".join(o.rooms) for k in ("wc", "bath", "kitchen", "ensuite")) else 0.80
        out.append(_res("EG6", "pass" if o.width >= er - 1e-9 else "fail", label + " [ER informative]",
                        round(o.width, 3), er, "m", "ER Art.97: %.2f m vs %.2f m" % (o.width, er), ["er119-art97"],
                        (o.id,), gate=False))
    return out


# ------------------------------------------------------------------------------------ EG7 daylight / openings
def check_daylight(m: DesignModel) -> list:
    out = []
    adf = {"living": ("sll-min-adf-living", 1.5), "dining": ("sll-min-adf-living", 1.5),
           "media": ("sll-min-adf-living", 1.5), "study": ("sll-min-adf-living", 1.5),
           "bedroom": ("sll-min-adf-bedroom", 1.0), "kitchen": ("sll-min-adf-kitchen", 2.0)}
    groups = sorted({r.group for r in m.rooms.values() if r.occupancy in adf and r.level == "B"} |
                    {r.group for r in m.rooms.values() if r.occupancy in adf and r.level == "GF"})
    for g in groups:
        rooms = m.group_rooms(g)
        main = m.rooms.get(g) or rooms[0]
        occ = main.occupancy
        if occ not in adf:
            continue
        sid, need = adf[occ]
        area = m.group_area(g)
        # area-weighted mean DF over the parts that have a DF
        num = sum((r.area_m2 or r.rect_area) * m.df[r.id] for r in rooms if r.id in m.df)
        den = sum((r.area_m2 or r.rect_area) for r in rooms if r.id in m.df)
        ids = tuple(r.id for r in rooms)
        label = "%s (%s)" % (g, main.name.split(" (")[0])
        if den <= 0:
            out.append(_ne("EG7", label + " daylight factor", "no simulated daylight factor for this room", ids,
                           gate=False))
        else:
            df = num / den
            out.append(_res("EG7", "pass" if df >= need - 1e-9 else "fail", label + " mean daylight factor",
                            round(df, 2), need, "%",
                            "simulated mean DF %.2f %% vs %.1f %% minimum average daylight factor (SLL Code, a "
                            "recommendation; the client prefers shade, so this is reported, not a safety gate)"
                            % (df, need), [sid], ids, gate=False))
        glaz = sum(o.width * o.height for o in m.openings if o.exterior and o.kind in ("door", "window") and
                   any(r.id in o.rooms for r in rooms) and (o.kind == "window" or o.rooms and o.rooms[-1] in
                                                              ("yard", "deck")))
        ratio = 100.0 * glaz / area if area else 0.0
        out.append(_res("EG7", "pass" if ratio >= 8.0 - 1e-9 else "fail", label + " glazing / floor area",
                        round(ratio, 1), 8.0, "%",
                        "%.2f m2 of glazed openings on %.2f m2 of floor = %.1f %% vs 8 %% (IRC R303.1, quoted in "
                        "Residential Interior Design; the Egyptian ER Art.96 gives the same 8 %%). Frames and "
                        "borrowed light not counted" % (glaz, area, ratio), ["irc-r303-glazing"], ids, gate=False))
    return out


# ------------------------------------------------------------------------------------------------ EG9 sills
def check_sills(m: DesignModel) -> list:
    out = []
    for o in m.openings:
        if o.kind != "window":
            continue
        label = "window %s (%s, %s)" % (o.id, o.rooms[0], o.level)
        if o.level != "GF":
            out.append(_res("EG9", "pass", label, 0.0, 0.0, "m",
                            "basement window opens at yard level: no fall of more than 0.6 m", ["ukadk-guarding-drop-dwelling"],
                            (o.id,)))
            continue
        ok = o.sill >= 0.8 - 1e-9
        out.append(_res("EG9", "pass" if ok else "fail", label, round(o.sill, 2), 0.8, "m",
                        "GF window over a drop: sill %.2f m vs 0.80 m guard height at opening windows (ADK Diagram "
                        "3.1)" % o.sill, ["ukadk-glazing-guard-800"], (o.id,)))
        out.append(_res("EG9", "pass" if o.sill >= 0.9 - 1e-9 else "fail", label + " [ER informative]",
                        round(o.sill, 2), 0.9, "m", "ER Art.96 sill 0.9 m", ["er119-art96-sill"], (o.id,), gate=False))
    return out


# ----------------------------------------------------------------------------------------------- stair maths
def stair_geometry(stair) -> dict:
    """Rise, going, width, pitch and gaps measured from the tread boxes as built (mm)."""
    tr = sorted((b for b in stair.treads if (b[5] - b[2]) < 300), key=lambda b: b[5])
    if len(tr) < 2:
        return {}
    tops = [b[5] for b in tr]
    rise = (tops[-1] - tops[0]) / (len(tops) - 1)
    going = tr[0][3] - tr[0][0]
    thick = tr[0][5] - tr[0][2]
    # step above the last tread to the GF floor: the top step is the landing edge
    last_rise = stair.gf_floor_z_mm - tops[-1]
    width = tr[0][4] - tr[0][1]
    # plan overlap of consecutive treads (tread i+1 sits beyond tread i in plan)
    overlaps = []
    for a, b in zip(tr, tr[1:]):
        lo = max(min(a[0], a[3]), min(b[0], b[3]))
        hi = min(max(a[0], a[3]), max(b[0], b[3]))
        overlaps.append(max(0.0, hi - lo))
    foot_x = max(max(b[0], b[3]) for b in tr)
    return {"risers": len(tr) + 1, "rise": rise, "last_rise": last_rise, "going": going, "tread_t": thick,
            "width": width, "pitch": math.degrees(math.atan2(rise, going)), "overlap_min": min(overlaps),
            "gap": rise - thick, "foot_x": foot_x, "tops": tops, "y0": tr[0][1], "y1": tr[0][4],
            "x_top": min(min(b[0], b[3]) for b in tr)}


def stair_headroom_mm(stair, g) -> tuple:
    """Least vertical clearance (mm) from the pitch line to the GF slab soffit where the flight is under the slab.
    The pitch line runs through the tread nosings (the foot-side edge of each tread)."""
    ox0, oy0, ox1, oy1 = (v * 1000.0 for v in stair.gf_opening_m)
    best, at = 1e9, None
    x = g["foot_x"]
    going, rise = g["going"], g["rise"]
    z0 = g["tops"][0] - rise                      # basement floor z under the foot
    xs = [g["foot_x"] - i * 5.0 for i in range(int((g["foot_x"] - g["x_top"]) / 5.0) + 1)]
    for x in xs:
        if ox0 <= x <= ox1:
            continue                              # inside the slab opening: nothing overhead
        z_pitch = z0 + rise * (1 + (g["foot_x"] - x) / going)
        c = stair.slab_soffit_mm - z_pitch
        if c < best:
            best, at = c, x
    return best, at


# ---------------------------------------------------------------------------------------------- LS1 stairs
def check_stair_geometry(m: DesignModel) -> list:
    out = []
    st = m.stair
    if st is None:
        return [_ne("LS1", "stair", "no stair in the model")]
    g = stair_geometry(st)
    if not g:
        return [_ne("LS1", "stair", "tread boxes could not be read")]
    el = (st.id,)
    rows = [("rise", g["rise"], 220.0, "mm", g["rise"] <= 220 + 1e-9, "ukadk-private-stair-rise-max",
             "<= 220 mm (private stair, ADK Table 1.1)"),
            ("going", g["going"], 220.0, "mm", g["going"] >= 220 - 1e-9, "ukadk-private-stair-going-min",
             ">= 220 mm"),
            ("pitch", g["pitch"], 42.0, "deg", g["pitch"] <= 42 + 1e-9, "ukadk-private-stair-pitch-max", "<= 42 deg")]
    for name, ach, req, unit, ok, sid, txt in rows:
        out.append(_res("LS1", "pass" if ok else "fail", "stair %s" % name, round(ach, 1), req, unit,
                        "%.1f %s vs %s" % (ach, unit, txt), [sid], el))
    two = 2 * g["rise"] + g["going"]
    out.append(_res("LS1", "pass" if 550 <= two <= 700 else "fail", "stair 2R+G", round(two, 1), 550.0, "mm",
                    "2R+G = %.0f mm, band 550-700 mm (ADK Table 1.1 footnote)" % two, ["ukadk-2r-plus-g"], el))
    uniform = abs(g["last_rise"] - g["rise"]) <= 5.0
    out.append(_res("LS1", "pass" if uniform else "fail", "stair uniform steps", round(abs(g["last_rise"] - g["rise"]), 1),
                    5.0, "mm", "top rise %.1f mm vs typical %.1f mm (ADK 1.5: consistent rise)" % (g["last_rise"], g["rise"]),
                    ["ukadk-private-stair-rise-max"], el))
    hr, hx = stair_headroom_mm(st, g)
    out.append(_res("LS1", "pass" if hr >= 2000 - 1e-9 else "fail", "stair headroom over the pitch line",
                    round(hr), 2000.0, "mm",
                    "least %.0f mm at x=%.2f m under the GF slab soffit (z %.0f mm, 200 slab + 100 build-up ASSUMED)"
                    % (hr, hx / 1000, st.slab_soffit_mm), ["ukadk-stair-headroom-min"], el))
    # landings: width and length at least the flight width
    tl, bl = st.top_landing, st.bottom_landing
    wflight = g["width"] / 1000.0
    for nm, rc in (("top", tl), ("bottom", bl)):
        if not rc:
            out.append(_ne("LS1", "stair %s landing" % nm, "landing rectangle not in the model", el))
            continue
        w, d = abs(rc[2] - rc[0]), abs(rc[3] - rc[1])
        small = min(w, d)
        out.append(_res("LS1", "pass" if small >= wflight - 1e-9 else "fail", "stair %s landing" % nm, round(small, 2),
                        round(wflight, 2), "m", "landing %.2f x %.2f m vs flight width %.2f m (ADK 1.20)" % (w, d, wflight),
                        ["ukadk-landing-1-20"], el))
    # under-stair soffit: treads whose underside is under 2.0 m above the basement floor
    lo = [b for b in st.treads if (b[5] - b[2]) < 300 and (b[2] - st.b_floor_z_mm) < 2000.0]
    if lo:
        xs = [min(b[0], b[3]) for b in lo] + [max(b[0], b[3]) for b in lo]
        run = (max(xs) - min(xs)) / 1000.0
        out.append(_res("LS1", "warn", "space under the flight (soffit < 2 m)", round(run, 2), 0.0, "m",
                        "the underside of the lowest %d treads is under 2.0 m above the basement floor over %.2f m of "
                        "run; the steps are open beneath (no enclosure or guard + cane detection in the model); "
                        "ADK 1.8 asks for one" % (len(lo), run), ["ukadk-soffit-under-stair"], el))
    # Egyptian ER informative
    out.append(_res("LS1", "pass" if g["width"] >= 1100 else "fail", "stair width [ER informative]", round(g["width"]),
                    1100.0, "mm", "ER Art.100: clear width %.0f mm vs 1100 mm (ADK sets no private-stair width)"
                    % g["width"], ["er119-art100"], el, gate=False))
    out.append(_res("LS1", "pass" if g["risers"] <= 14 else "fail", "stair risers per flight [ER informative]",
                    g["risers"], 14.0, "risers", "ER Art.100: %d risers in one flight vs 14 then a landing" % g["risers"],
                    ["er119-art100"], el, gate=False))
    out.append(_res("LS1", "pass" if g["going"] >= 270 and g["rise"] <= 170 else "fail", "stair tread and riser [ER informative]",
                    round(g["rise"], 1), 170.0, "mm", "ER Art.100: riser %.1f mm vs 170, tread %.0f vs 270" % (g["rise"], g["going"]),
                    ["er119-art100"], el, gate=False))
    return out


# ------------------------------------------------------------------------------------------- LS2 open risers
def check_open_risers(m: DesignModel) -> list:
    st = m.stair
    if st is None:
        return [_ne("LS2", "stair risers", "no stair in the model")]
    g = stair_geometry(st)
    if not g:
        return [_ne("LS2", "stair risers", "tread boxes could not be read")]
    el = (st.id,)
    out = []
    if st.has_risers:
        out.append(_res("LS2", "pass", "stair risers closed", 0.0, SPHERE_MM, "mm",
                        "riser boards modelled: no open gap (A+ target: closed risers)",
                        ["ukadk-open-risers-dwelling", "ukadk-closed-risers"], el))
        return out
    gap = g["gap"]
    sphere_passes = gap >= SPHERE_MM
    out.append(_res("LS2", "fail" if sphere_passes else "pass", "stair open-riser gap (100 mm sphere)", round(gap, 1),
                    SPHERE_MM, "mm",
                    "no riser boards: the gap between treads is %.1f mm (rise %.1f less a %.0f mm tread); a 100 mm "
                    "sphere passes if the gap is >= 100 mm, so it must be under 100 mm" % (gap, g["rise"], g["tread_t"]),
                    ["ukadk-open-risers-dwelling", "ukadk-guard-sphere"], el))
    ok = g["overlap_min"] >= 16 - 1e-9
    out.append(_res("LS2", "pass" if ok else "fail", "stair tread overlap (open risers)", round(g["overlap_min"], 1),
                    16.0, "mm", "consecutive treads overlap by %.1f mm in plan vs 16 mm minimum for open risers (ADK 1.9a)"
                    % g["overlap_min"], ["ukadk-open-risers-dwelling"], el))
    out.append(_res("LS2", "fail", "stair closed risers (A+ target)", 0.0, 1.0, "closed",
                    "risers are open; closed risers are the A+ target (ADK 1.6 for non-dwellings) and remove both "
                    "failures above", ["ukadk-closed-risers"], el, gate=False))
    out.append(_res("LS2", "fail", "stair open risers [ER informative]", round(gap, 1), 100.0, "mm",
                    "ER Art.103: objects >= 10 cm must not fall through; a %.0f mm gap does not stop one" % gap,
                    ["er119-art103-railing"], el, gate=False))
    return out


# ---------------------------------------------------------------------------------------------- LS3 guards
def check_guards(m: DesignModel) -> list:
    out = []
    for gd in m.guards:
        label = "%s (%s)" % (gd.id, gd.where)
        if gd.height_m is None:
            out.append(_ne("LS3", label, "guard height not in the model", (gd.id,)))
            continue
        if gd.kind == "handrail":
            ok = 0.9 - 1e-9 <= gd.height_m <= 1.0 + 1e-9
            out.append(_res("LS3", "pass" if ok else "fail", label, round(gd.height_m, 3), 0.9, "m",
                            "handrail %.2f m above the nosings (ADK 1.34: 900-1000 mm); height only, not a guard"
                            % gd.height_m, ["ukadk-guarding-height-internal"], (gd.id,), gate=False))
            continue
        if gd.drop_m is not None or gd.level == "street":
            need, sid = 0.9, "ukadk-guarding-height-internal"
            ok = gd.height_m >= need - 1e-9
            out.append(_res("LS3", "pass" if ok else "fail", label, round(gd.height_m, 3), need, "m",
                            "guard %.2f m vs 0.90 m minimum at a drop > 0.6 m (ADK K2/3.2a)" % gd.height_m,
                            ["ukadk-k2b-sunken-areas", "ukadk-guarding-height-internal"], (gd.id,)))
            tgt = 1.1
            out.append(_res("LS3", "pass" if gd.height_m >= tgt - 1e-9 else "fail", label + " (A+ target 1100)",
                            round(gd.height_m, 3), tgt, "m",
                            "%.2f m vs 1.10 m (external balcony / roof edge, ADK Diagram 3.1; used for sunken "
                            "edges: the table does not list them)" % gd.height_m, ["ukadk-guarding-height-external"],
                            (gd.id,), gate=False))
        else:
            need = 0.9
            ok = gd.height_m >= need - 1e-9
            out.append(_res("LS3", "pass" if ok else "fail", label, round(gd.height_m, 3), need, "m",
                            "stair guard %.2f m above the nosings vs 0.90 m (ADK Diagram 3.1, stairs); passes with no "
                            "margin" % gd.height_m, ["ukadk-guarding-height-internal"], (gd.id,)))
        if not gd.solid:
            out.append(_res("LS3", "warn", label + " openings", None, SPHERE_MM, "mm",
                            "guard infill is not solid; a 100 mm sphere test needs the balusters", ["ukadk-guard-sphere"],
                            (gd.id,)))
        else:
            out.append(_res("LS3", "pass", label + " 100 mm sphere", 0.0, SPHERE_MM, "mm",
                            "modelled as solid or glazed: no opening for a sphere (construction detail pending)",
                            ["ukadk-guard-sphere"], (gd.id,)))
    for subject, why in m.needed_but_unmodelled:
        out.append(_ne("LS3", subject, why))
    return out


# ------------------------------------------------------------------------------------------ LS4 door by flight
def check_door_near_flight(m: DesignModel) -> list:
    st = m.stair
    if st is None:
        return [_ne("LS4", "doors near the stair", "no stair in the model")]
    g = stair_geometry(st)
    out = []
    top_nosing = (st.gf_opening_m[0])                        # the flight meets the GF at the opening's start
    for o in m.openings:
        if o.kind != "door" or o.level != "GF" or "core" not in o.rooms or "landing-gf" not in o.rooms:
            continue
        lo, hi = o.x - o.width / 2, o.x + o.width / 2
        clear_to_flight = top_nosing - hi
        out.append(_res("LS4", "warn" if not o.swing_known else ("pass" if clear_to_flight >= 0.4 else "fail"),
                        "GF core door onto the stair top landing (%s)" % o.id, round(clear_to_flight, 3), 0.4, "m",
                        "the door's near jamb is %.3f m from the top step; ADK 1.24 / Diagram 1.8 lets a door swing "
                        "over a landing at the BOTTOM of a flight only, with 400 mm each side; the top landing must be "
                        "kept clear (1.21). The swing direction is not in the model: if the leaf opens into the landing "
                        "this fails" % clear_to_flight, ["ukadk-landing-door-1-24"], (o.id,)))
        out.append(_res("LS4", "pass" if clear_to_flight >= 1.0 else "fail",
                        "GF core door to the top step [ER informative]", round(clear_to_flight, 3), 1.0, "m",
                        "ER Art.96: door opening directly onto a stair flight needs 1.0 m; here %.3f m" % clear_to_flight,
                        ["er119-art96-door-stair"], (o.id,), gate=False))
    if not out:
        out.append(_ne("LS4", "doors near the stair", "no door onto a landing found in the model"))
    return out


# ------------------------------------------------------------------------------------------------ LS5 escape
def check_escape(m: DesignModel) -> list:
    out = []
    by_room: dict = {}
    for o in m.openings:
        for rid in o.rooms:
            by_room.setdefault(rid, []).append(o)
    for r in m.rooms.values():
        if r.occupancy not in HABITABLE and r.occupancy != "bedroom":
            continue
        if r.part_of:
            continue
        grp = [x.id for x in m.group_rooms(r.group)]
        ops = [o for rid in grp for o in by_room.get(rid, [])]
        label = _room_label(r)
        ext_doors = [o for o in ops if o.kind == "door" and o.exterior]
        wins = [o for o in ops if o.kind == "window"]
        escapes = []
        for w in wins:
            ok = w.sill <= 1.1 + 1e-9 and w.width * w.height >= 0.33 - 1e-9 and min(w.width, w.height) >= 0.45 - 1e-9 \
                and w.level == r.level
            if ok:
                escapes.append(w)
        if ext_doors or escapes:
            kind = "an external door" if ext_doors else "a window (sill %.2f m, %.2f m2)" % (
                escapes[0].sill, escapes[0].width * escapes[0].height)
            out.append(_res("LS5", "pass", label + " escape opening", 1.0, 1.0, "opening",
                            "has %s; whole window taken as openable (openable area is not modelled)" % kind,
                            ["adb-escape-window-area", "adb-escape-window-min", "adb-escape-window-sill",
                             "irc-r310-escape"], (r.id,)))
        else:
            # an inner room: escape only through another room
            routes = [(l[0] if l[1] == r.id else l[1]) for l in m.links if r.id in l] if hasattr(m, "links") else []
            out.append(_res("LS5", "fail", label + " escape opening", 0.0, 1.0, "opening",
                            "no external door or escape window: the room is entered only from %s, an inner room. "
                            "Approved Document B 2.11 allows inner rooms only for a kitchen, utility, dressing room, "
                            "bathroom/WC, a gallery, or a room with an escape window; IRC R310 asks for one "
                            "emergency opening in every basement habitable space" % (", ".join(routes) or "another room"),
                            ["adb-inner-room", "irc-r310-escape"], (r.id,)))
    out.append(_ne("LS5", "dead-end hall and the single stair",
                   "no sourced dead-end or travel-distance limit for a single dwelling is held (Approved Document B "
                   "travel distances are not carded); a reviewer step. GF exits: the core door at the stair top and "
                   "the escape windows; basement exits: the stair, the core door, the garden doors"))
    return out


# --------------------------------------------------------------------------------------------------- runner
ALL = (check_clear_heights, check_room_sizes, check_doors, check_daylight, check_sills, check_stair_geometry,
       check_open_risers, check_guards, check_door_near_flight, check_escape)


def run_all(m: DesignModel) -> list:
    out = []
    for fn in ALL:
        out.extend(fn(m))
    return out
