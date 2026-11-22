"""North court and east yard designs, one per concept (A tree court, B two rooms, C axial terrace), each with and without the flush koi pond.

North court frame (u, v): u = distance from the house face (x = 3.617 - u), v = y + 28.671 (0 at the entrance-steps block, 4.83 at the yard wall).
East yard frame (u, v): u = x - 15.412 (0 at the roof-wall end, 7.185 at the south garden mouth), v = y + 23.591 (0 at the house wall, 2.99 at the east fence).
Pond specifications (freeboard, depth, grille, shore slope, margin) are specifications for a supplier to certify, as in pass 1.
"""
from __future__ import annotations

from . import ty_core as C
from .species import sun_ok
from .ty_core import bed, frag, pergola, row, tree

NX1, NY0, NY1 = 3.617, -28.671, -23.841
EX0, EY0 = 15.412, -23.591
NW, NH = 4.83, 3.74         # north court: v width, u depth
EL, EW = 7.185, 2.99        # east yard: u length, v width


def NR(u0, v0, u1, v1):
    return [round(NX1 - u1, 3), round(NY0 + v0, 3), round(NX1 - u0, 3), round(NY0 + v1, 3)]


def ER(u0, v0, u1, v1):
    return [round(EX0 + u0, 3), round(EY0 + v0, 3), round(EX0 + u1, 3), round(EY0 + v1, 3)]


def pond_feat(fid, rect, depth_mm=1000):
    area = (rect[2] - rect[0]) * (rect[3] - rect[1])
    koi = max(1, int(28.7 * area / 27.6))
    return {"id": fid, "kind": "pond", "rect": rect, "flush": True, "edge": "soft", "freeboard_mm": 150, "depth_mm": depth_mm, "volume_m3": round(0.7 * depth_mm / 1000 * area, 2),
            "koi_count": koi, "koi_adult_length_cm": 70, "aerated": False, "child_protection": "rigid_grille", "edge_slope_run_per_rise": 4, "margin_slope_back_mm": 600,
            "area_m2": round(area, 2), "trace": ["U-POND", "D-FLUSH", "LS-POND-GUARD", "LS-POND-DEPTH", "LS-POND-STOCK", "LS-POND-FLUSH-MARGIN", "LS-POND-EDGE-SLOPE"]}


def _paving(f, zone_rect, cuts, material="unit-paving"):
    f["paved_areas"] += C.paving_from(zone_rect, cuts, material)


def _bench(f, sid, rect, zone, seats=2):
    f["seating"].append({"id": sid, "zone": zone, "rect": rect, "seats": seats, "trace": ["U-N-QUIET", "LS-FIRE-SEAT"] if False else ["U-N-QUIET"]})


def _zone(f, zid, use, rect, surface, **kw):
    f["zones"].append({"id": zid, "use": use, "rect": rect, "surface": surface, "enclosure_height_m": 4.0, "trace": ["U-N-QUIET"], **kw})


def _path(f, pid, rect=None, polyline=None, w=1.2, cls="main"):
    d = {"id": pid, "class": cls, "width_m": w, "cross_slope_pct": 1.5, "trace": ["U-ACCESS", "LS-PATH-MAIN"]}
    if rect:
        d["rect"] = rect
    else:
        d["polyline"] = polyline
    f["paths"].append(d)


# palettes: rows from the back to the front of a bed: (species, spacing, run, spread basis, spread cap) ------------------------------------
PAL = {
    "shade_mass": [(["jasminum_sambac"], 1.2, 1, "min", C.SPREAD_CAP_CLIMBER), (["fatsia_japonica", "phoenix_roebelenii"], 0.9, 2, "min", None), (["aspidistra_elatior"], 0.45, 6, "min", None)],
    "shade_strip": [(["aspidistra_elatior", "farfugium_japonicum"], 0.45, 4, "min", None)],
    "pond_mass": [(["alpinia_zerumbet"], 1.0, 4, "min", None), (["acorus_gramineus"], 0.4, 5, "min", None)],
    "pond_strip": [(["acorus_gramineus"], 0.4, 6, "min", None)],
    "yard_mass": [(["jasminum_sambac", "petrea_volubilis"], 1.2, 2, "min", C.SPREAD_CAP_CLIMBER), (["justicia_brandegeeana", "salvia_leucantha"], 0.7, 4, "min", None),
                  (["pennisetum_alopecuroides", "aspidistra_elatior"], 0.6, 4, "min", None)],
    "yard_shade_mass": [(["fatsia_japonica", "phoenix_roebelenii"], 0.9, 2, "min", None), (["farfugium_japonicum", "aspidistra_elatior"], 0.45, 5, "min", None)],
}
HZ = {"shade_mass": "medium", "shade_strip": "medium", "pond_mass": "high", "pond_strip": "high", "yard_mass": "medium", "yard_shade_mass": "medium"}


def _sun_rows(rows, june):
    """Drop species whose sun class the bed's 21-June sun does not meet (policy thresholds, species.sun_ok); an emptied row is dropped."""
    out = []
    for sp, spacing, run, how, cap in rows:
        keep = [s for s in sp if sun_ok(C.POOL[s], june) != "fail"]
        if keep:
            out.append((keep, spacing, run, how, cap))
    return out


def layered(rect, pal, back="lo"):
    """Rows of drifts across the bed depth (min side), back row first, rows run along the long side."""
    x0, y0, x1, y1 = rect
    along = "x" if (x1 - x0) >= (y1 - y0) else "y"
    depth = min(x1 - x0, y1 - y0)
    rows = _sun_rows(PAL[pal], C.bed_sun(rect))
    if not rows:                                   # too dark for the palette: shade species only (aspidistra, farfugium: LDL 'shade')
        rows = _sun_rows(PAL["shade_strip"], C.bed_sun(rect))
    out = []
    for i, (sp, spacing, run, how, cap) in enumerate(rows):
        off = depth * (i + 0.5) / len(rows)
        if back == "hi":
            off = depth - off
        out += row(rect, along, off, sp, spacing, run=run, how=how, cap=cap)
    return out


def build_court(kit, zone_id="n"):
    f = frag()
    zone = kit["zone"]
    cuts = [b["rect"] for b in kit["beds"]] + [kit[k] for k in ("pond", "gravel", "bench") if kit.get(k)] + [s_["rect"] for s_ in kit.get("sculpture", [])]
    f["paved_areas"] += C.paving_from(zone, cuts, kit.get("material", "unit-paving"))
    for b in kit["beds"]:
        bed(f, b["id"], b["rect"], layered(b["rect"], b["pal"], b.get("back", "lo")), b["role"],
            trace=("U-POND" if b["pal"].startswith("pond") else "U-PRIVACY", "LS-HYDROZONE"))
    if kit.get("pond"):
        f["features"].append(pond_feat(f"pond-{zone_id}", kit["pond"], kit.get("depth", 1000)))
    for sc in kit.get("sculpture", []):
        f["features"].append({"id": sc["id"], "kind": "sculpture", "rect": sc["rect"], "trace": ["U-N-QUIET"]})
    if kit.get("bench"):
        f["zones"].append({"id": f"quiet-{zone_id}", "use": "quiet", "rect": kit["quiet"], "surface": kit.get("quiet_surface", "paving"), "enclosure_height_m": 4.0, "trace": ["U-N-QUIET"]})
        f["seating"].append({"id": f"bench-{zone_id}", "zone": f"quiet-{zone_id}", "rect": kit["bench"], "seats": 2, "trace": ["U-N-QUIET"]})
    if kit.get("gravel"):
        f["zones"].append({"id": f"floor-{zone_id}", "use": "other", "rect": kit["gravel"], "surface": "gravel", "label": False, "trace": ["U-N-QUIET"]})
    if kit.get("pergola"):
        pergola(f, f"pergola-{zone_id}", kit["pergola"], 2.6, 0.6)
    for k, pth in enumerate(kit["paths"]):
        _path(f, f"path-{zone_id}-{k}", **pth)
    for t in kit.get("trees", []):
        tree(f, f"tree-{zone_id}-{t['species']}", t["species"], t["at"])
    f["meta"][f"focal-{zone_id}"] = kit.get("focal", "")
    rooms = {}
    return f, rooms, ([kit["pergola"]] if kit.get("pergola") else [])


def north_kit(concept, pond):
    a = {}
    if concept == "A":
        # a gravel room around a focal Phoenix/fatsia mass; bench alcove on the yard wall under a pergola
        if not pond:
            st = NR(2.5, 0, NH, NW)
            kit = dict(zone=NR(0, 0, NH, NW), beds=[dict(id="n-street", rect=st, role="border", pal="shade_mass", back="hi")], gravel=NR(1.2, 0, 2.5, 4.38),
                       bench=NR(1.05, 4.38, 2.45, NW), quiet=NR(0.9, 3.4, 2.9, NW), pergola=NR(0.9, 3.4, 2.9, NW), focal="the fatsia and Phoenix mass seen from the lounge door",
                       paths=[dict(rect=NR(0, 1.7, 1.2, 3.1))])
        else:
            kit = dict(zone=NR(0, 0, NH, NW), pond=NR(1.9, 1.6, 3.0, 3.6),
                       beds=[dict(id="n-street", rect=NR(3.3, 0, NH, NW), role="strip", pal="pond_strip", back="hi"), dict(id="n-pondmass", rect=NR(1.2, 0, 3.3, 1.25), role="mass", pal="pond_mass", back="hi")],
                       gravel=NR(1.2, 1.25, 3.3, 4.38), bench=NR(1.05, 4.38, 2.45, NW), quiet=NR(0.9, 3.4, 2.9, NW), pergola=NR(0.9, 3.4, 2.9, NW),
                       focal="the pond seen from the lounge door", paths=[dict(rect=NR(0, 1.7, 1.2, 3.1))])
    elif concept == "B":
        # a quiet room entered over a threshold: bench niche in the steps-block corner behind a planted screen
        scr = NR(1.5, 1.9, NH, 3.1)
        if not pond:
            kit = dict(zone=NR(0, 0, NH, NW), beds=[dict(id="n-screen", rect=scr, role="mass", pal="shade_mass", back="lo"), dict(id="n-back", rect=NR(1.5, 3.1, NH, NW), role="border", pal="shade_strip")],
                       bench=NR(1.6, 0.0, 3.0, 0.45), quiet=NR(1.2, 0.0, 3.2, 1.9), pergola=NR(1.2, 0.0, 3.2, 1.9), focal="the bench niche behind the planted screen",
                       paths=[dict(polyline=[[NX1, NY0 + 2.5], [NX1 - 1.1, NY0 + 2.5], [NX1 - 1.1, NY0 + 1.0]])])
        else:
            kit = dict(zone=NR(0, 0, NH, NW), pond=NR(1.6, 3.1, 2.8, 4.8),
                       beds=[dict(id="n-screen", rect=scr, role="mass", pal="shade_mass", back="lo"), dict(id="n-back", rect=NR(2.8, 3.1, NH, NW), role="strip", pal="pond_strip", back="hi")],
                       bench=NR(1.6, 0.0, 3.0, 0.45), quiet=NR(1.2, 0.0, 3.2, 1.9), pergola=NR(1.2, 0.0, 3.2, 1.9), focal="the pond past the screen gap",
                       paths=[dict(polyline=[[NX1, NY0 + 2.5], [NX1 - 1.1, NY0 + 2.5], [NX1 - 1.1, NY0 + 1.0]])])
    else:
        # C: an axis from the lounge door north to the street fence; deep borders either side
        axis = NY0 + NW / 2
        bn = NR(1.0, 3.1, 2.2, 3.55)                         # bench along the axis edge, facing it
        qz = NR(0.8, 3.0, 2.4, 3.7)
        left, right = NR(1.3, 0, NH, 1.2), NR(1.3, NW - 1.2, NH, NW)
        if not pond:
            kit = dict(zone=NR(0, 0, NH, NW), beds=[dict(id="n-left", rect=left, role="border", pal="shade_mass", back="hi"), dict(id="n-right", rect=right, role="border", pal="shade_mass", back="hi")],
                       sculpture=[dict(id="sculpture-n", rect=[NX1 - NH + 0.05, axis - 0.4, NX1 - NH + 0.55, axis + 0.4])], bench=bn, quiet=qz,
                       focal="axis from the lounge door to a sculpture place on the street fence", paths=[dict(polyline=[[NX1, axis], [NX1 - 3.2, axis]])])
        else:
            kit = dict(zone=NR(0, 0, NH, NW), pond=NR(2.3, NW / 2 - 0.85, 3.5, NW / 2 + 0.85), beds=[dict(id="n-left", rect=left, role="border", pal="pond_mass", back="hi"),
                       dict(id="n-right", rect=right, role="border", pal="pond_mass", back="hi")], bench=bn, quiet=qz,
                       focal="axis from the lounge door to the pond at the end", paths=[dict(polyline=[[NX1, axis], [NX1 - 2.25, axis]])])
    return kit


def east_kit(concept, pond):
    """East yard: the main path runs along the house wall (v 0..1.2) between the dining door (u 1.5) and living door (u 5.1) and the south-garden mouth (u 7.2)."""
    path = dict(rect=ER(0.2, 0, EL, 1.2), cls="service")
    if concept == "A":
        if not pond:
            return dict(zone=ER(0, 0, EL, EW), beds=[dict(id="e-border", rect=ER(0, 1.5, EL, EW), role="border", pal="yard_shade_mass", back="hi")], paths=[path],
                        focal="a layered border seen from the dining and living doors")
        return dict(zone=ER(0, 0, EL, EW), pond=ER(1.4, 1.5, 4.9, 2.5), beds=[dict(id="e-edge", rect=ER(1.4, 2.5, 4.9, EW), role="strip", pal="pond_strip", back="hi"),
                    dict(id="e-pondmass", rect=ER(4.9, 1.2, EL, EW), role="mass", pal="pond_mass", back="hi")],
                    bench=ER(0.2, 1.5, 0.65, 2.7), quiet=ER(0.0, 1.3, 1.2, EW), pergola=ER(0.0, 0.9, 1.4, EW), paths=[path], focal="the pond seen from the dining and living doors")
    if concept == "B":
        # the quiet garden room: a bench at the roof-wall end facing the focal; a planted divider across the garden mouth
        div = ER(5.6, 1.5, EL, EW)
        if not pond:
            return dict(zone=ER(0, 0, EL, EW), beds=[dict(id="e-divider", rect=div, role="mass", pal="yard_shade_mass", back="hi"), dict(id="e-far", rect=ER(0, 1.5, 1.2, EW), role="mass", pal="yard_shade_mass", back="hi")],
                        bench=ER(1.3, 2.45, 2.7, 2.9), quiet=ER(0.9, 1.4, 3.2, EW), pergola=ER(0.9, 1.4, 3.2, EW), paths=[path], focal="the quiet room: bench facing the divider planting")
        return dict(zone=ER(0, 0, EL, EW), pond=ER(1.7, 1.5, 5.2, 2.5), beds=[dict(id="e-divider", rect=ER(5.6, 1.5, EL, EW), role="mass", pal="pond_mass", back="hi"),
                    dict(id="e-far", rect=ER(0, 1.5, 1.2, EW), role="mass", pal="pond_mass", back="hi")], bench=ER(2.8, 2.54, 4.2, 2.99), quiet=ER(2.5, 2.4, 4.5, EW), pergola=ER(2.2, 1.9, 4.8, EW), paths=[path], focal="the pond is the focal point of the quiet room")
    # C
    if not pond:
        return dict(zone=ER(0, 0, EL, EW), beds=[dict(id="e-border", rect=ER(0.9, 1.5, EL, EW), role="border", pal="yard_mass", back="hi")], sculpture=[dict(id="sculpture-e", rect=ER(0.0, 0.2, 0.4, 1.0))],
                    paths=[dict(rect=ER(0.5, 0, EL, 1.2), cls="service")], focal="the path along the house runs to a sculpture place at the north end")
    return dict(zone=ER(0, 0, EL, EW), pond=ER(0.9, 1.6, 4.6, 2.6), beds=[dict(id="e-border", rect=ER(4.9, 1.2, EL, EW), role="mass", pal="pond_mass", back="hi"),
                dict(id="e-edge", rect=ER(0.9, 2.6, 4.6, EW), role="strip", pal="pond_strip", back="hi")], bench=ER(0.1, 1.5, 0.55, 2.7), quiet=ER(0.0, 1.3, 0.9, EW), pergola=ER(0.0, 0.9, 1.3, EW), paths=[dict(rect=ER(0.5, 0, EL, 1.2), cls="service")],
                focal="a long straight pond parallel to the path, ending at the garden")
