"""Quantity arithmetic from the design model (millimetres in, SI out). No IFC dependency.

One implementation feeds both the IFC Qto sets and the QS take-off, so the two cannot disagree by construction;
`validate.py` and the take-off reconciliation then check them against the geometry independently.
"""
from __future__ import annotations

import math

from ..contracts import DesignElement
from . import common as C


def signed_area(pts) -> float:
    s = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def perimeter(pts) -> float:
    return sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def opening_area_mm2(op: DesignElement, wall_h: float) -> float:
    """Wall area removed by one hosted door/window (clipped to the wall height)."""
    p = op.params
    sill = float(p.get("sill_mm") or 0.0) if op.kind == "window" else 0.0
    return float(p["width_mm"]) * max(0.0, min(float(p["height_mm"]), wall_h - sill))


def hosted(elements: list[DesignElement]) -> dict[str, list[DesignElement]]:
    out: dict[str, list[DesignElement]] = {}
    for e in elements:
        if e.kind in ("door", "window"):
            out.setdefault(e.host, []).append(e)
    return out


def wall_q(w: DesignElement, ops: list[DesignElement]) -> dict:
    """Length, Width, Height (mm); areas m2; volumes m3. Side area = one face; openings deducted for the Net values."""
    L, t, h = C.wall_length(w), float(w.params["thickness_mm"]), float(w.params["height_mm"])
    gross = L * h
    net = gross - sum(opening_area_mm2(o, h) for o in ops)
    return dict(Length=L, Width=t, Height=h, GrossSideArea=gross / 1e6, NetSideArea=net / 1e6,
                GrossVolume=gross * t / 1e9, NetVolume=net * t / 1e9, OpeningArea=(gross - net) / 1e6)


def slab_q(e: DesignElement) -> dict:
    """GrossArea = plan area of the outline (a sloped ramp: its plan footprint); NetArea minus holes; Depth = thickness."""
    p = e.params
    t = float(p.get("thickness_mm") or e.size[2])
    if p.get("polygon_mm"):
        poly = [tuple(map(float, v)) for v in p["polygon_mm"]]
        gross = abs(signed_area(poly))
        holes = sum(abs(signed_area([tuple(map(float, v)) for v in h])) for h in p.get("holes_mm") or [])
        per = perimeter(poly)
        net = gross - holes
        vol = net * t
        L, W = (max(v[i] for v in poly) - min(v[i] for v in poly) for i in (0, 1))
    else:
        L, W = e.size[0], e.size[1]
        gross = net = L * W
        per = 2 * (L + W)
        if p.get("profile_xz_mm"):                       # sloped slab: volume from the section, plan area from the footprint
            top = [(float(x), float(z)) for x, z in p["profile_xz_mm"]]
            vol = abs(signed_area(top + [(x, z - t) for x, z in reversed(top)])) * W
        else:
            vol = gross * t
    return dict(Length=L, Width=W, Depth=t, Perimeter=per, GrossArea=gross / 1e6, NetArea=net / 1e6,
                GrossVolume=(gross * t if not p.get("profile_xz_mm") else vol) / 1e9, NetVolume=vol / 1e9)


# ---------------------------------------------------------------------------------------------------------------------
# Take-off for the quantity surveyor: counts, areas, volumes, lengths. No prices, no rates.
# ---------------------------------------------------------------------------------------------------------------------
import csv  # noqa: E402
from collections import defaultdict  # noqa: E402
from pathlib import Path  # noqa: E402

NOT_AUTHORED = "structure, material not authored"
EXTERIOR = "(exterior / no room)"


def _r(v, n=4):
    return None if v is None else round(float(v), n)


def railing_length_m(e: DesignElement) -> float:
    p = e.params
    if p.get("length_mm"):
        return float(p["length_mm"]) / 1000
    prof = p.get("profile_mm") or []
    if prof and len(prof[0]) == 3:                                # stair guard: slope length of the nosing line
        return sum(math.dist(a, b) for a, b in zip(prof, prof[1:])) / 1000
    if prof:                                                      # ramp-edge guard: plan length
        xs = [v[0] for v in prof]
        return max(max(xs) - min(xs), e.size[0], e.size[1]) / 1000
    return max(e.size[0], e.size[1]) / 1000


def element_rows(elements: list[DesignElement]) -> list[dict]:
    """One row per element with its own quantities (the finest grain; every other table is a sum of these)."""
    H = hosted(elements)
    out = []
    for e in elements:
        k, p = e.kind, e.params
        row = dict(id=e.id, kind=k, level=e.level, room=e.room or "", type=p.get("type_id") or "", count=1,
                   length_m=None, area_m2=None, volume_m3=None, note="")
        if k == "wall":
            q = wall_q(e, H.get(e.id, []))
            row.update(length_m=q["Length"] / 1000, area_m2=q["NetSideArea"], volume_m3=q["NetVolume"],
                       note=f"{p.get('wall_kind')} wall t={p['thickness_mm']:g} h={p['height_mm']:g}; area = one face net of openings; "
                            f"gross face {q['GrossSideArea']:.3f} m2")
        elif k == "slab":
            q = slab_q(e)
            row.update(area_m2=q["NetArea"], volume_m3=q["NetVolume"], length_m=q["Perimeter"] / 1000,
                       note=f"{p.get('role')}; t={q['Depth']:g}; length = perimeter")
        elif k in ("floor", "ceiling"):
            row.update(area_m2=p["area_m2"], note=p.get("finish_code") or "")
        elif k == "room":
            row.update(area_m2=p.get("net_area_m2"), note=f"gross {p.get('gross_area_m2')} m2")
        elif k in ("door", "window"):
            W, Hh = float(p["width_mm"]), float(p["height_mm"])
            row.update(area_m2=W * Hh / 1e6, note=f"{W:g} x {Hh:g}; {p.get('operation') or ''}")
        elif k in ("column", "beam"):
            w, d, h = e.size
            row.update(length_m=(h if k == "column" else max(w, d)) / 1000, volume_m3=w * d * h / 1e9,
                       note=f"{w:g} x {d:g} x {h:g}")
        elif k == "railing":
            row.update(length_m=railing_length_m(e), note=f"guard height {p.get('guard_height_mm'):g}")
        elif k == "stair":
            tb = p["tread_boxes_mm"]
            row.update(area_m2=sum((b[3] - b[0]) * (b[4] - b[1]) for b in tb) / 1e6,
                       note=f"{p['treads']} treads, {p['risers']} risers, riser {p['riser_mm']}, going {p['tread_mm']}; "
                            "area = tread plates in plan")
        elif k == "garden":
            row.update(area_m2=p.get("area_m2") or abs(signed_area([tuple(v) for v in p["polygon_mm"]])) / 1e6)
        elif k == "context":
            row.update(note="NOT OURS: context volume")
        out.append(row)
    return out


def layer_rows(elements: list[DesignElement]) -> list[dict]:
    """Quantities per build-up layer, by room: finish areas (walls both sides, floors, ceilings) and structure volumes.
    A layer with no authored thickness has an area and a blank volume: the volume is never invented."""
    H = hosted(elements)
    acc: dict[tuple, dict] = defaultdict(lambda: dict(count=0, area_m2=0.0, volume_m3=0.0, has_vol=True, ids=[]))

    def put(kind, level, room, layer, area, vol_basis_area=None, eid=""):
        t = layer.get("thickness_mm")
        key = (kind, level, room, layer.get("side", ""), layer.get("function"), layer.get("material"), t, layer.get("status"))
        a = acc[key]
        a["count"] += 1
        a["area_m2"] += area
        if t is None:
            a["has_vol"] = False
        else:
            a["volume_m3"] += (vol_basis_area if vol_basis_area is not None else area) * float(t) / 1000
        a["ids"].append(eid)

    for e in elements:
        p = e.params
        if e.kind == "wall":
            q = wall_q(e, H.get(e.id, []))
            for lay in p.get("layers") or []:
                side = p["sides"].get(lay["side"]) if lay.get("side") in ("left", "right") else None
                room = (side or {}).get("room") or EXTERIOR if lay.get("side") in ("left", "right") else "(core)"
                put("wall", e.level, room, lay, q["NetSideArea"], eid=e.id)
        elif e.kind in ("floor", "ceiling", "slab"):
            area = (slab_q(e)["NetArea"] if e.kind == "slab" else float(p["area_m2"]))
            for lay in p.get("layers") or []:
                put(e.kind, e.level, e.room or "", lay, area, eid=e.id)
    rows = []
    for (kind, level, room, side, fn, mat, t, status), a in sorted(acc.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        rows.append(dict(element_kind=kind, level=level, room=room, side=side, function=fn, material=mat,
                         thickness_mm=t, thickness_status=status, elements=a["count"], area_m2=_r(a["area_m2"]),
                         volume_m3=_r(a["volume_m3"]) if a["has_vol"] else None,
                         note="" if a["has_vol"] else "thickness not authored: no volume"))
    return rows


def room_rows(elements: list[DesignElement]) -> list[dict]:
    """Per room: areas, finishes, wall finish area, ceiling, skirting candidate, counts of what sits in it."""
    H = hosted(elements)
    by = {e.id: e for e in elements}
    rooms = [e for e in elements if e.kind == "room"]
    floor = {e.room: e for e in elements if e.kind == "floor"}
    ceil = {e.room: e for e in elements if e.kind == "ceiling"}
    wall_area, skirt = defaultdict(float), defaultdict(float)
    finish_by_room: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for w in (e for e in elements if e.kind == "wall"):
        q = wall_q(w, H.get(w.id, []))
        full_w = sum(float(o.params["width_mm"]) for o in H.get(w.id, [])
                     if o.kind == "door" or o.params.get("full_height")) / 1000
        for sd in (w.params.get("sides") or {}).values():
            r = sd.get("room")
            if r:
                wall_area[r] += q["NetSideArea"]
                finish_by_room[r][sd.get("finish_code") or "?"] += q["NetSideArea"]
                skirt[r] += max(0.0, q["Length"] / 1000 - full_w)
    n_by = defaultdict(lambda: defaultdict(int))
    for e in elements:
        if e.kind in ("door", "window"):
            for r in (e.params.get("rooms") or [e.room]):
                n_by[r][e.kind] += 1
        elif e.kind in ("luminaire", "furniture", "fixture") and e.room:
            n_by[e.room][e.kind] += 1
    out = []
    for r in sorted(rooms, key=lambda e: (e.level, e.id)):
        name = r.id[5:] if r.id.startswith("room-") else r.id
        p = r.params
        fl, ce = floor.get(name), ceil.get(name)
        out.append(dict(
            room=name, level=r.level, description=p.get("name"), gross_area_m2=p.get("gross_area_m2"),
            net_floor_area_m2=p.get("net_area_m2"), floor_finish=fl.params.get("finish_code") if fl else None,
            floor_finish_area_m2=_r(fl.params["area_m2"]) if fl else None,
            ceiling_finish=ce.params.get("finish_code") if ce else None,
            ceiling_area_m2=_r(ce.params["area_m2"]) if ce else None, ceiling_kind=ce.params.get("ceiling_kind") if ce else None,
            wall_finish_area_m2=_r(wall_area.get(name, 0.0)),
            wall_finish_by_code="; ".join(f"{k} {v:.2f}" for k, v in sorted(finish_by_room[name].items())),
            skirting_candidate_m=_r(skirt.get(name, 0.0), 2),
            doors=n_by[name]["door"], windows=n_by[name]["window"], luminaires=n_by[name]["luminaire"],
            furniture=n_by[name]["furniture"], fixtures=n_by[name]["fixture"],
            note="skirting is not authored in the model: candidate = wall-side length less door and full-height openings"))
    return out


def type_rows(elements: list[DesignElement]) -> list[dict]:
    """Per element type (shared type for doors, windows, furniture, luminaires; per wall/slab spec otherwise)."""
    types = {e.id: e for e in elements if e.kind == "type"}
    acc: dict[tuple, dict] = defaultdict(lambda: dict(count=0, length_m=0.0, area_m2=0.0, volume_m3=0.0, has_len=False,
                                                       has_area=False, has_vol=False))
    for r in element_rows(elements):
        k = r["kind"]
        if k in ("type", "storey", "room", "floor", "ceiling"):
            continue
        if r["type"] and r["type"] in types:
            t = types[r["type"]]
            label = f"{t.id[5:]}"
        elif k == "wall":
            e = next(x for x in elements if x.id == r["id"])
            label = f"{e.params['wall_kind']} {e.params['thickness_mm']:g} mm x {e.params['height_mm']:g}"
        elif k == "slab":
            label = r["id"]
        elif k == "railing":
            label = r["id"]
        elif k == "plant":
            e = next(x for x in elements if x.id == r["id"])
            label = e.params.get("species") or "plant"
        elif k == "garden":
            label = r["id"]
        elif k in ("column", "beam"):
            label = r["note"]
        else:
            label = r["id"] if k in ("stair", "fixture") else k
        key = (k, r["level"], label)
        a = acc[key]
        a["count"] += 1
        for fld, flag in (("length_m", "has_len"), ("area_m2", "has_area"), ("volume_m3", "has_vol")):
            if r[fld] is not None:
                a[fld] += r[fld]
                a[flag] = True
    out = []
    for (k, level, label), a in sorted(acc.items()):
        out.append(dict(category=k, level=level, type=label, count=a["count"],
                        length_m=_r(a["length_m"]) if a["has_len"] else None, area_m2=_r(a["area_m2"]) if a["has_area"] else None,
                        volume_m3=_r(a["volume_m3"]) if a["has_vol"] else None,
                        note="NOT OURS (context)" if k == "context" else ""))
    return out


def reconcile(elements: list[DesignElement], dev_list: list[dict] | None = None) -> list[dict]:
    """Totals against the model and against the other schedules. Each row: what, take-off value, other value, difference."""
    from ..documents import schedules as S
    erows = element_rows(elements)
    tot = lambda kind, fld: sum(r[fld] or 0 for r in erows if r["kind"] == kind)       # noqa: E731
    cnt = lambda kind: sum(1 for r in erows if r["kind"] == kind)                      # noqa: E731
    rooms = room_rows(elements)
    lay = layer_rows(elements)
    types_ = type_rows(elements)
    checks = []

    def chk(what, a, b, tol, unit=""):
        checks.append(dict(check=what, takeoff=_r(a), reference=_r(b), difference=_r(a - b), tolerance=tol, unit=unit,
                           ok=abs(a - b) <= tol))
    nonctx = [e for e in elements if e.kind not in ("type", "storey")]
    chk("element count (by-type table vs model, all kinds)", sum(r["count"] for r in types_) + sum(
        1 for e in elements if e.kind in ("room", "floor", "ceiling")), len(nonctx), 0, "elements")
    chk("room net area: by-room table vs model rooms", sum(r["net_floor_area_m2"] or 0 for r in rooms), tot("room", "area_m2"), 1e-6, "m2")
    chk("room net area: floor-finish area vs room net area", sum(r["floor_finish_area_m2"] or 0 for r in rooms),
        sum(r["net_floor_area_m2"] or 0 for r in rooms), 0.001, "m2")
    chk("ceiling area vs room net area", sum(r["ceiling_area_m2"] or 0 for r in rooms), sum(r["net_floor_area_m2"] or 0 for r in rooms), 0.001, "m2")
    sch = S.room_schedule(elements)
    chk("room net area vs room schedule (documents.schedules)", sum(r["net_floor_area_m2"] or 0 for r in rooms),
        sum(float(r["net_area_m2"] or 0) for r in sch), 0.05, "m2")
    chk("room gross area vs room schedule", sum(r["gross_area_m2"] or 0 for r in rooms), sum(float(r["gross_area_m2"] or 0) for r in sch), 0.05, "m2")
    chk("door count vs door schedule", cnt("door"), len(S.door_schedule(elements)), 0)
    chk("window count vs window schedule", cnt("window"), len(S.window_schedule(elements)), 0)
    wall_layer_area = sum(r["area_m2"] for r in lay if r["element_kind"] == "wall" and r["function"] == "structure")
    chk("wall core layer area vs wall net face area", wall_layer_area, tot("wall", "area_m2"), 0.001, "m2")
    H = hosted(elements)
    exp_total, exp_rooms = 0.0, 0.0                     # independent: face area x number of finish layers on that side
    for w in (e for e in elements if e.kind == "wall"):
        face = wall_q(w, H.get(w.id, []))["NetSideArea"]
        for side in ("left", "right"):
            n = sum(1 for l in w.params.get("layers") or [] if l.get("side") == side)
            exp_total += face * n
            if (w.params["sides"].get(side) or {}).get("room"):
                exp_rooms += face * n
    wall_finish = sum(r["area_m2"] for r in lay if r["element_kind"] == "wall" and r["side"] in ("left", "right"))
    chk("wall finish layers (all layers, both sides) vs face area x layers per side", wall_finish, exp_total, 0.001, "m2")
    in_rooms = sum(r["area_m2"] for r in lay if r["element_kind"] == "wall" and r["side"] in ("left", "right") and r["room"] != EXTERIOR)
    chk("wall finish layers inside rooms vs face area x layers (sides with a room)", in_rooms, exp_rooms, 0.001, "m2")
    chk("wall surface in rooms (by-room table, one count per side) vs model", sum(r["wall_finish_area_m2"] for r in rooms),
        sum(wall_q(w, H.get(w.id, []))["NetSideArea"] for w in elements if w.kind == "wall"
            for sd in w.params["sides"].values() if sd.get("room")), 0.001, "m2")
    core_vol = sum(r["volume_m3"] or 0 for r in lay if r["element_kind"] == "wall" and r["function"] == "structure")
    chk("wall core volume (layers) vs wall net volume", core_vol, tot("wall", "volume_m3"), 0.001, "m3")
    slab_vol = sum(r["volume_m3"] or 0 for r in lay if r["element_kind"] == "slab")
    chk("slab structure volume (layers) vs slab net volume", slab_vol, tot("slab", "volume_m3"), 0.001, "m3")
    if dev_list is not None:
        chk("luminaires vs electrical device_list.csv", cnt("luminaire"), sum(1 for r in dev_list if r["family"] == "luminaire"), 0, "fittings")
    return checks


def takeoff(elements: list[DesignElement], dev_list: list[dict] | None = None) -> dict[str, list[dict]]:
    return dict(by_type=type_rows(elements), by_room=room_rows(elements), by_layer=layer_rows(elements),
                elements=element_rows(elements), reconciliation=reconcile(elements, dev_list))


def write_csv(rows: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


README = [
    "Quantity take-off, design D1 (no prices, no rates).",
    "Source: the design model (archpipe.model, schema archpipe-model/1), millimetres internally, metric outputs.",
    "Areas are net of openings where stated; wall 'area' is ONE face; both faces appear in the by-layer sheet.",
    "Structure volumes: wall and slab material is NOT authored in the model (spec gives a thickness only). Volumes are of the "
    "structural body; do not read them as concrete without confirming the structural design.",
    "Finish layers with no authored thickness (floor tile bed, suspended ceiling, exterior render) have an area and no volume.",
    "Skirting is not authored: 'skirting_candidate_m' is wall-side length less door and full-height openings, for you to use only if skirting is specified.",
    "Cable lengths are not here: they are the electrical lane's route estimates (tests/electrical/d1/cable_schedule.csv).",
    "Context elements (neighbouring volumes, the apartment above) are listed and flagged NOT OURS; do not price them.",
    "Reference: the 'reconciliation' sheet checks these totals against the model and the door/window/room schedules.",
]


def write_xlsx(tables: dict[str, list[dict]], path: Path):
    try:
        import openpyxl
        from openpyxl.styles import Font
    except ImportError as exc:                                          # loud, not a silent CSV-only result
        raise C.ExchangeError(["openpyxl is required for the XLSX take-off (pip install openpyxl)"]) from exc
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "README"
    for i, line in enumerate(README, 1):
        ws.cell(row=i, column=1, value=line)
    ws.column_dimensions["A"].width = 140
    for name, rows in tables.items():
        ws = wb.create_sheet(name)
        if not rows:
            continue
        cols = list(rows[0])
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([r[c] for c in cols])
        ws.freeze_panes = "A2"
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = min(60, max(10, len(c) + 2, *(len(str(r[c] if r[c] is not None else "")) for r in rows[:200])))
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))
