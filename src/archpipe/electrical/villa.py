"""Adapter: the L2 design model (archpipe.model.load("D1")) -> electrical.model.House.

Everything the model does not carry is an explicit, flagged assumption (House.flags), never silent:
  - door hinge/latch side: not in the model, chosen by policy (hinge at the end of the opening nearer the wall corner);
  - bed head side: derived from the wall the bed stands against;
  - luminaire watts for strips, pendants and lamps (63 of 136): flux / 90 lm/W placeholder;
  - lighting control zones: provisional, one per room and layer, until lane L6b publishes knowledge/lighting/zones-d1.json;
  - equipment: knowledge/electrical/d1-equipment-assumed.json (status "assumed");
  - board positions: pantry (main board), stair-foot hall (basement board), stair-head gallery (ground-floor board).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .. import contracts
from .. import model as design_model
from .model import Board, Door, Equipment, Furniture, House, Luminaire, Room, Supply
from .placement import Device, room_walls, slide_on_wall


def placement_clear(h, level, x, y, z) -> bool:
    from .placement import clearance
    return clearance(h, level, x, y, z)[0]

ROOT = Path(__file__).resolve().parents[3]
EQUIPMENT_JSON = ROOT / "knowledge" / "electrical" / "d1-equipment-assumed.json"
ZONES_JSON = ROOT / "knowledge" / "lighting" / "zones-d1.json"
EFFICACY_LM_PER_W = 90.0          # placeholder where the model has no watts (policy, flagged)
LEVEL_Z_MM = {"B": -3000.0, "GF": 0.0, "SITE": -3000.0}      # finished floor, scene datum (L2-model.md)
KIND_BY_OCC = {"ensuite": "bathroom"}
FURN_KIND = {"bed_single": "bed", "bed_small_double": "bed", "bed_double": "bed", "desk": "desk", "tv_unit": "tv", "screen": "tv",
             "sofa_2seat": "sofa", "sofa_3seat": "sofa", "sofa_4seat": "sofa", "base_run": "worktop", "folding_counter": "worktop",
             "island": "island", "shower_walkin": "shower", "bath": "bath"}
BOARD_PLACES = {"MDB": ("pantry", "S", 0.5, "B", 40.0), "DB-B": ("hall-b", "S", 0.5, "B", 40.0), "DB-GF": ("gallery-end", "S", 0.5, "GF", 50.0)}
NON_ROOMS = {"core", "yard", "deck"}


def _rect(poly) -> tuple[float, float, float, float]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return (min(xs), min(ys), max(xs), max(ys))


def _furn_rect(e) -> tuple[float, float, float, float]:
    w, d = e.size[0], e.size[1]
    if int(round(abs(e.rotation_deg))) % 180 == 90:
        w, d = d, w
    cx, cy = e.placement[0], e.placement[1]
    return (cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)


def _pick_wall(room: Room, rect, kind: str, flags: list, fid: str) -> tuple[str, float]:
    """(wall name, gap mm) of the wall a piece stands against. Beds: the wall at one of the short ends (head wall)."""
    walls = room_walls(room)
    gaps = {n: w.gap(rect) for n, w in walls.items()}
    if kind == "bed":
        long_x = (rect[2] - rect[0]) >= (rect[3] - rect[1])
        head = {n: g for n, g in gaps.items() if abs(walls[n].n[0] if long_x else walls[n].n[1]) > 0.9}
        if head and min(head.values()) <= 600.0:
            n = min(head, key=head.get)
            return n, head[n]
        n = min(gaps, key=lambda k: (gaps[k], -walls[k].length))
        flags.append(f"{fid}: bed head side is not authored and no short end is within 600 mm of a wall; bedside sockets sit at both ends of the wall it stands along ({n})")
        return n, gaps[n]
    n = min(gaps, key=lambda k: (gaps[k], -walls[k].length))
    return n, gaps[n]


def _door_records(els, rooms: dict[str, Room], flags: list) -> list[Door]:
    out: list[Door] = []
    assumed = 0
    for e in els:
        if e.kind != "door":
            continue
        width = float(e.params.get("width_mm") or e.size[0])
        x, y = e.placement[0], e.placement[1]
        garden = bool(e.params.get("garden"))
        for rid in e.params.get("rooms", []):
            r = rooms.get(rid)
            if r is None or rid in NON_ROOMS:
                continue
            best = None
            for n, w in room_walls(r).items():
                dep = abs(w.depth_of(x, y))
                al = w.along_of(x, y)
                if dep <= 200.0 and -1.0 <= al <= w.length + 1.0 and (best is None or dep < best[0]):
                    best = (dep, n, w, al)
            if best is None:
                flags.append(f"{e.id}: door centre ({x:.0f}, {y:.0f}) is not on any wall of {rid}; no switch placed for it")
                continue
            _, n, w, al = best
            off = al - width / 2
            hinge_known = "hinge" in e.params
            if hinge_known:
                hinge = str(e.params["hinge"])
            else:
                hinge = "start" if off <= w.length - (off + width) else "end"   # hinge near the corner: latch on the open side
                assumed += 1
            out.append(Door(f"{e.id}@{rid}", rid, n, off, width, hinge, hinge_known, garden, str(e.params.get("operation") or "hinged")))
    flags.append(f"door hinge/latch side is not in the model: {assumed} of {len(out)} door-room records use the policy 'hinge at the end of the opening nearer the corner, switch at the latch (open) side'. "
                 "Wall-mounted switches beside glazed garden doors are not placed.")
    return out


def _provisional_zones(lums: list[Luminaire]) -> list[contracts.LightingZone]:
    by: dict[tuple[str, str, str], list[Luminaire]] = {}
    for l in lums:
        by.setdefault((l.room, l.layer or "ambient", l.zone), []).append(l)
    zs = []
    for (room, layer, _), ls in sorted(by.items()):
        zid = f"Z-PROV-{room}-{layer}"
        for l in ls:
            l.zone = zid
        zs.append(contracts.LightingZone(zid, room, layer, tuple(l.id for l in ls), round(sum(l.watts for l in ls), 2), "switched"))
    return zs


def _published_zones(lums: list[Luminaire]) -> list[contracts.LightingZone] | None:
    """L6b's zones-d1.json, if present: [{id, room, layer, luminaire_ids, watts, dimming}] or {"zones": [...]}."""
    if not ZONES_JSON.exists():
        return None
    raw = json.loads(ZONES_JSON.read_text(encoding="utf-8"))
    raw = raw["zones"] if isinstance(raw, dict) else raw
    byid = {l.id: l for l in lums}
    # L6b's zone watts are the commissioned (dimmed) driver output; a set-point is programming, not a limit, so circuits are sized on
    # the rated luminaire watts when those are higher (upper bound). EA13 then equals circuit W = sum of luminaire W.
    zs = [contracts.LightingZone(z["id"], z["room"], z["layer"], tuple(z["luminaire_ids"]),
                                 max(float(z["watts"]), round(sum(byid[i].watts for i in z["luminaire_ids"] if i in byid), 2)), z["dimming"]) for z in raw]
    for z, rz in zip(zs, raw):
        members = [byid[i] for i in z.luminaire_ids if i in byid]
        have = sum(m.watts for m in members)
        if members and have > 0 and float(rz["watts"]) > have + 0.05:
            # INT2 (L6c): a generic strip's model W is flux/efficacy, a placeholder; L6c sizes its driver (Z-B-STAIR-B-ACCENT 7.1 W vs
            # 4.39 W). The published W is the better figure, so the luminaires carry it (pro rata) and circuit W = sum of luminaire W (EA13).
            for m in members:
                m.watts = round(m.watts * float(rz["watts"]) / have, 4)
        for i in z.luminaire_ids:
            if i in byid:
                byid[i].zone = z.id
    return zs


def load_villa(model_path=None, equipment_path: Path | str = EQUIPMENT_JSON) -> House:
    els = design_model.load("D1", path=model_path) if model_path else design_model.load("D1")
    flags: list[str] = []
    rooms: dict[str, Room] = {}
    for e in els:
        if e.kind != "room":
            continue
        p = e.params
        poly = tuple((float(a), float(b)) for a, b in p["polygon_mm"])
        occ = p.get("occupancy", "")
        rooms[e.room] = Room(e.room, KIND_BY_OCC.get(occ, "living" if occ in ("living", "media") else occ), _rect(poly), e.level,
                             float(p.get("clear_height_mm") or 2700.0), poly, str(p.get("name", "")), tuple(p.get("open_to", [])))  # falsy-ok: a 0 mm clear height is not a room
    # kitchen-like rooms keep the engine's special kind
    for rid, occ in (("kitchen", "kitchen"), ("kitchen-island", "kitchen")):
        if rid in rooms:
            rooms[rid].kind = occ
    nonrect = [r.id for r in rooms.values() if len(r.poly) != 4]
    flags.append(f"room geometry: {len(rooms)} rooms from the model polygons; {len(nonrect)} are not 4-vertex rectangles. The polygon-edge branch of the placement is exercised by an L-shaped test room, not by D1")

    doors = _door_records(els, rooms, flags)

    # fixtures -> shower/bath data
    heads = {e.params.get("over"): e for e in els if e.kind == "fixture" and e.params.get("fixture_kind") == "ceiling-rain-head"}
    furniture: list[Furniture] = []
    skipped = 0
    for e in els:
        if e.kind != "furniture" or e.room not in rooms:
            continue
        t = e.params.get("type", "")
        kind = FURN_KIND.get(t)
        if kind is None:
            skipped += 1
            continue
        r = rooms[e.room]
        rect = _furn_rect(e)
        wall, gap = _pick_wall(r, rect, kind, flags, e.id)
        params: dict = {"model_type": t, "gap_mm": round(gap, 1)}
        if kind in ("shower", "bath"):
            over = next((k for k in heads if k and e.id == "furn-" + k), None)
            head = heads.get(over) if over else None
            params["head_h_mm"] = float(head.placement[2]) if head else 2250.0
            if kind == "bath":
                params.update(has_basin=True, rim_mm=float(e.size[2] or 550.0))  # falsy-ok: a 0 mm bath rim means "not modelled"; 550 is the stated default
            elif e.size[2] > 0:                       # shower with a low tray
                params.update(has_basin=True, rim_mm=float(e.size[2]))
            else:                                     # wet-zone shower, no tray: zones from the fixed outlet
                params["has_basin"] = False
                if head:
                    params["outlet_xy"] = [head.placement[0], head.placement[1]]
            flags.append(f"{e.id}: wet-area zone data from the model ({'tray rim ' + str(params.get('rim_mm')) + ' mm' if params['has_basin'] else 'no tray, outlet at the rain head'}; head height {params['head_h_mm']:.0f} mm)")
        elif kind in ("worktop",) and gap > 300.0:
            continue
        elif kind == "sofa" and gap > 1200.0:
            flags.append(f"{e.id}: sofa stands {gap:.0f} mm from the nearest wall; no end sockets placed (floor box to decide with the interior design)")
            continue
        furniture.append(Furniture(e.id, e.room, kind, rect, wall, params))

    # luminaires and provisional zones
    lums: list[Luminaire] = []
    derived = 0
    for e in els:
        if e.kind != "luminaire":
            continue
        w = e.params.get("watts")
        if not w:
            w = round(float(e.params.get("flux_lm") or 0.0) / EFFICACY_LM_PER_W, 2)
            derived += 1
        lums.append(Luminaire(e.id, e.room, float(w), "", (e.placement[0], e.placement[1]), str(e.params.get("layer", ""))))
    flags.append(f"luminaire watts: {derived} of {len(lums)} luminaires have no watts in the model (strips, pendants, lamps); derived as flux_lm / {EFFICACY_LM_PER_W:g} lm/W, a placeholder for lane L6b to replace")
    pub = _published_zones(lums)
    if pub is None:
        zones = _provisional_zones(lums)
        flags.append(f"lighting zones are PROVISIONAL: knowledge/lighting/zones-d1.json (lane L6b) was not available; {len(zones)} zones derived as one per room and layer")
    else:
        zones = pub
        _raw = json.loads(ZONES_JSON.read_text(encoding="utf-8"))
        raw_w = {z["id"]: float(z["watts"]) for z in (_raw["zones"] if isinstance(_raw, dict) else _raw)}
        up = sum(1 for z in zones if z.watts > raw_w[z.id] + 0.05)
        flags.append(f"lighting zones from knowledge/lighting/zones-d1.json (lane L6b): {len(zones)} zones; {up} sized on rated luminaire W above the published commissioned W")

    # equipment (assumed)
    eq = json.loads(Path(equipment_path).read_text(encoding="utf-8"))
    anchors = {k: tuple(v["xy"]) for k, v in eq["anchors"].items()}
    site_rooms: dict[str, Room] = {}
    equipment: list[Equipment] = []
    extra: list[Device] = []
    plot = (-123.0, -29916.0, 28557.0, -20601.0)
    for rec in eq["equipment"]:
        xy = anchors.get(rec.get("anchor", ""))
        room = rec["room"]
        if rec.get("external"):
            if room not in site_rooms:
                x, y = xy
                site_rooms[room] = Room(room, "outdoor", (x - 1000.0, y - 1000.0, x + 1000.0, y + 1000.0), "SITE", 0.0, name=room)
        equipment.append(Equipment(rec["id"], room, rec["kind"], rec["kw"], rec.get("pf", 1.0), rec.get("cat", "standard"), False,
                                   rec.get("name", ""), bool(rec.get("external")), rec.get("board", ""), xy, rec.get("status", ""), rec.get("reason", ""), float(rec.get("extra_length_m", 0.0))))
        if rec.get("external"):
            extra.append(Device(f"FCU-{room}-{rec['id']}", "fcu", room, xy[0], xy[1], 1200.0, "E11-external-equipment-point", rec["id"], {"basis": "anchor " + rec["anchor"]}))
    gx = [anchors[g["anchor"]] for g in eq["garden_sockets"]]
    site_rooms["site-garden"] = Room("site-garden", "outdoor", plot, "SITE", 0.0, name="garden")
    for g, (x, y) in zip(eq["garden_sockets"], gx):
        extra.append(Device(f"SOC-site-garden-{g['id']}", "socket", "site-garden", x, y, 400.0, "E11-garden-socket", "", {"ip": "IP66", "rcd": "30 mA", "basis": g["reason"]}))
    all_rooms = list(rooms.values()) + list(site_rooms.values())

    s = eq["supply"]
    # wall elements and window/door boxes for the device clearance post-condition
    wall_segs = [{"level": e.level, "x0": e.params["x0_mm"], "y0": e.params["y0_mm"], "x1": e.params["x1_mm"], "y1": e.params["y1_mm"], "t": e.params["thickness_mm"], "id": e.id}
                 for e in els if e.kind == "wall"]
    openings = []
    for e in els:
        if e.kind not in ("window", "door"):
            continue
        span = e.params.get("span") or []
        horiz = (span[0] == "h") if span else (int(round(e.rotation_deg)) % 180 == 0)
        w = float(e.params.get("width_mm") or e.size[0])
        x, y = e.placement[0], e.placement[1]
        if e.kind == "window":
            z0 = float(e.params.get("sill_mm") or 0.0)
            z1 = z0 + float(e.params.get("height_mm") or e.size[2])
        else:
            z0, z1 = 0.0, float(e.params.get("height_mm") or 2100.0)  # falsy-ok: a 0 mm element height is not an element; 2100 is the stated default
        box = (x - w / 2, y - 150.0, x + w / 2, y + 150.0) if horiz else (x - 150.0, y - w / 2, x + 150.0, y + w / 2)
        openings.append({"id": e.id, "kind": e.kind, "level": e.level, "x0": box[0], "y0": box[1], "x1": box[2], "y1": box[3], "z0": z0, "z1": z1})
    mdb_x, mdb_y = anchors["gate"]
    sup = Supply(s["v_phase"], s["phases"], s["earthing"], None, None, (mdb_x, mdb_y), s["feeder_length_m"], s["feeder_ambient_c"],
                 s["roof_ambient_c"], s["drop_m"], None, s["premises"], s["ra_note"])
    flags.append("boards: MDB in the pantry (B), DB-B at the stair-foot hall (B), DB-GF at the stair-head gallery (GF), stacked so the riser is about 3 m; "
                 "meter position and utility cabinet at the street fence are assumptions to confirm")
    flags.append("routes: Manhattan distance x 1.15 through all the circuit's load points (nearest-neighbour chain) plus 3 m of vertical drops (the engine has no wall/slab routing); sub-board feeders add the 3 m storey rise and 3 m of drops")
    # storey areas for the ADB alarm-grade rule (net room polygons; gross adds the wall plan area of the level)
    areas: dict[str, dict] = {}
    for lvl in ("B", "GF"):
        net = sum(abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2.0) / 1e6
                  for p in (r.poly for r in rooms.values() if r.level == lvl))
        wl = sum(e.size[0] * e.size[1] for e in els if e.kind == "wall" and e.level == lvl) / 1e6
        areas[lvl] = {"net": round(net, 1), "walls": round(wl, 1), "gross": round(net + wl, 1)}
    flags.append("storey areas for the alarm grade (net rooms + wall plan): " + ", ".join(f"{k} {v['gross']} m2 (net {v['net']})" for k, v in areas.items()))
    x0, y0, x1, y1 = plot
    site = {"cctv": {"gate": anchors["gate"], "deck": anchors["deck"],
                     "corner-nw": (x0 + 800, y1 + 800 - 0), "corner-sw": (x0 + 800, y0 + 800), "corner-ne": (x1 - 800, y1 - 800), "corner-se": (x1 - 800, y0 + 800)},
            "intercom_gate": anchors["gate"], "intercom_monitors": ["hall-b", "corridor", "parents-bed"]}
    # corners are named by side, not by compass (the client calls the street side north)
    site["cctv"] = {"gate": anchors["gate"], "deck": anchors["deck"], "corner-street-a": (x0 + 800, y0 + 800), "corner-street-b": (x0 + 800, y1 - 800),
                    "corner-rear-a": (x1 - 800, y0 + 800), "corner-rear-b": (x1 - 800, y1 - 800)}
    flags.append("CCTV, intercom and AP positions are layout proposals from the plot fences, the gate anchor and room centroids; the plot is the fence-bounded rectangle x -123..28557, y -29916..-20601 mm")
    h = House("D1", all_rooms, doors, furniture, lums, zones, equipment, sup, [], extra,
              {"lighting_pack": "level", "lighting_target_a": 2.0, "socket_pack": "cluster", "storey_area_m2": areas, "storeys_above_ground": 1, "garden_ap_xy": anchors["garden-living-e"], "site_points": site, "supply_extra": {k: s[k] for k in ("single_phase_limit_a", "single_phase_limit_note")}},
              flags, dict(LEVEL_Z_MM))
    h.provisional_zones = pub is None
    h.wall_segs, h.openings = wall_segs, openings
    # floor footprints no floor box may sit in: every model furniture box with a size, and the stair
    for e in els:
        if e.kind == "furniture" and e.size[0] > 0 and e.size[1] > 0 and e.params.get("type") != "dressing":
            fx0, fy0, fx1, fy1 = _furn_rect(e)
            h.keepouts.append({"id": e.id, "level": e.level, "x0": fx0, "y0": fy0, "x1": fx1, "y1": fy1})
        elif e.kind == "stair":
            h.keepouts.append({"id": e.id, "level": e.level, "x0": e.placement[0] - e.size[0] / 2, "y0": e.placement[1] - e.size[1] / 2,
                               "x1": e.placement[0] + e.size[0] / 2, "y1": e.placement[1] + e.size[1] / 2})
    # boards: on a clear stretch of a wall of the chosen room (slid along the wall if the first choice hits an opening)
    boards: list[Board] = []
    for bid, (rid, wall, frac, lvl, amb) in BOARD_PLACES.items():
        rw = room_walls(rooms[rid])
        order = [wall] + sorted((n for n in rw if n != wall), key=lambda n: -rw[n].length)
        pt, why = None, "no clear stretch"
        for wn in order:                          # a board is 600 mm wide: both ends and the middle must be on a wall element and clear of openings
            w = rw[wn]
            a0 = w.length * frac
            for k in range(0, 40):
                for sgn in ((1,) if k == 0 else (1, -1)):
                    a = a0 + sgn * k * 150.0
                    if 300.0 <= a <= w.length - 300.0 and all(placement_clear(h, rooms[rid].level, *w.point(a + dx), 1500.0) for dx in (-300.0, 0.0, 300.0)):
                        pt = w.point(a)
                        why = (f"wall {wn}" if wn != wall else "") + (f" moved {k * 150} mm" if k else "")
                        why = (why.strip() + " to get a 600 mm clear stretch") if why.strip() else ""
                        break
                if pt:
                    break
            if pt:
                break
        if pt is None:
            raise ValueError(f"no clear wall position for board {bid} in {rid}: {why}")
        if why:
            flags.append(f"board {bid}: {why}")
        boards.append(Board(bid, lvl, pt, None if bid == "MDB" else "MDB", rid, amb))
    h.boards = boards
    h.supply.board_xy = boards[0].xy
    return h
