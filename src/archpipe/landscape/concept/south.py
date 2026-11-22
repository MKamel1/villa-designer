"""South-garden structure candidates (stage LD-G step 3), composed from rule-derived module sizes.

Local frame (a, b) = (x - 22.597, y + 29.916); see site.py. Three organising ideas, two sister-line variants.
Nothing here is drawn freehand: positions are sampled, sizes come from the LDK parameters, and the LDK checks
decide what survives.
"""
from __future__ import annotations

import math
import random

from shapely.geometry import box

from . import site as S
from .geom import R, area, circle, largest_rect, rbox, rects_of, union


def carve(beds, cutter):
    """Remove `cutter` (a shapely geometry) from every bed; a bed split in two keeps both pieces."""
    out = []
    for b in beds:
        g = rbox(b["rect"]).difference(cutter)
        parts = [r for r in rects_of(g, 0.1)] if not g.is_empty else []
        for k, r in enumerate(parts):
            out.append({**b, "id": b["id"] if len(parts) == 1 else f"{b['id']}-{k}", "rect": r})
    return out

A, B = S.SA, S.SB
HOUSE_B1 = 6.325            # the house face runs b 0..6.325; beyond it the south garden opens to the east yard
DOOR_B = (2.585, 4.985)     # living door (2.4 m wide, centre b 3.785)
IDEAS = {"H": "Hearth court", "O": "Orchard room", "W": "Wall and floor"}
PIT_D = 0.9                 # flush fire-pit footprint (cover), our module
SEAT = 0.7                  # lounge chair module (m)


def table_for(n):
    return 0.6 * math.ceil(n / 2) + 0.3, 0.9        # length along b, width along a (our module: 0.6 m per place)


def _unit(ang):
    return "b" if abs(math.sin(ang)) < abs(math.cos(ang)) else "a"


def _fits(r, bad, gap=0.0):
    b = rbox(r)
    return all(b.distance(o) >= gap - 1e-9 for o in bad)


def sample(idea: str, variant: str, rng: random.Random, P: dict) -> dict | None:
    """One structure candidate or None: sequential random packing, each piece checked against the rule distances.

    table 1.2 m clear of everything (LS-DINE-CLEAR); fire pit 1.5 m from every seat (LS-FIRE-SEAT) and 1.2 m
    from the table; lounge seats 1.2 m from the table; beds are obstacles for the table and the fire.
    """
    screened = variant == "screened"
    wm = rng.choice([0.3, 0.45, 0.6, 0.8, 1.0]) if screened else rng.choice([0.0, 0.0, 0.4])
    hw = rng.choice([0.0, 0.6, 0.7, 0.75])                         # east strip: herb / sun bed (0 = herbs go to the east yard)
    sbd = rng.choice([0.6, 0.8, 1.0, 1.2]) if idea != "O" else rng.choice([0.6, 0.8])
    n_d = rng.choice([4, 4, 5, 6])
    n_l = rng.choice([4, 6, 6, 8])
    L, W = table_for(n_d)
    beds = []
    if wm > 0:
        beds.append({"id": "bed-west", "rect": R(0, 0, A, wm), "role": "screen" if screened else "edge"})
    beds.append({"id": "bed-south", "rect": R(A - sbd, wm, A, B - hw), "role": "south"})
    if hw > 0:
        beds.append({"id": "bed-east", "rect": R(1.0, B - hw, A, B), "role": "herb"})
    if idea == "O":
        cw, cd = rng.choice([1.6, 2.0, 2.4]), rng.choice([1.6, 2.0, 2.4])
        cr = R(A - cd, wm, A, wm + cw) if rng.random() < .6 else R(A - cd, B - hw - cw, A, B - hw)
        beds.append({"id": "bed-corner", "rect": cr, "role": "orchard"})
    if idea == "O":
        cr_ = next(b["rect"] for b in beds if b["id"] == "bed-corner")
        beds = [b for b in beds if b["id"] == "bed-corner"] + carve([b for b in beds if b["id"] != "bed-corner"], rbox(cr_))
    bedshapes = [rbox(b["rect"]) for b in beds]
    house = box(-5, -5, 0, B + 5)
    fences = [box(A, -5, A + 5, B + 5), box(-5, B, A + 5, B + 5)]
    # --- table ---------------------------------------------------------------------------------
    a_t = rng.choice([1.65, 1.8, 1.95, 2.1, 2.25])                    # >= 0.45 + 1.2 from the house wall
    if idea == "O":
        b_t = rng.uniform(B - hw - 0.2 - L / 2 - 1.2, B - hw - 1.2 - L / 2 + 0.01)
    else:
        b_t = rng.uniform(wm + 1.2 + L / 2, wm + 2.6 + L / 2)
    tr = R(a_t - W / 2, b_t - L / 2, a_t + W / 2, b_t + L / 2)
    if not _fits(tr, bedshapes + [house], 1.2):
        return None
    zone_a1 = min(a_t + W / 2 + 1.2, A)
    wd = max(L + 2.4, math.ceil(P["LS-DINE-AREA"]["min_m2_per_seat"] * n_d / zone_a1 * 10) / 10)
    dining = R(0, b_t - wd / 2, zone_a1, b_t + wd / 2)
    _side = (lambda g: g.bounds[1] >= dining[3] - 1e-9) if idea != "O" else (lambda g: g.bounds[3] <= dining[1] + 1e-9)
    # --- fire pit: 1.2 m from the table, >= 2.45 m from beds and fences, >= 2.45 from the house -------
    pit = None
    for _ in range(40):
        ap, bp = rng.uniform(2.45, A - 2.45) if A - 2.45 > 2.45 else 2.6, rng.uniform(1.0, B - 2.45)
        ap = min(max(ap, 2.45), A - 2.45) if A - 2.45 >= 2.45 else 2.6
        pc = circle((ap, bp), PIT_D)
        if not _side(pc) or pc.distance(rbox(tr)) < 1.2 or any(pc.distance(o) < 2.0 for o in bedshapes + fences + [house]):
            continue
        pit = (ap, bp)
        break
    if pit is None:
        # relax the 2 m planting clearance to the 0.9 m clear-ground rule and keep the fence/house 2 m
        for _ in range(80):
            ap, bp = rng.uniform(2.0, 3.6), rng.uniform(1.0, B - 1.5)
            pc = circle((ap, bp), PIT_D)
            if not _side(pc) or pc.distance(rbox(tr)) < 1.2 or any(pc.distance(o) < 0.9 for o in bedshapes) or any(pc.distance(o) < 1.5 for o in fences + [house]):
                continue
            pit = (ap, bp)
            break
    if pit is None:
        return None
    pc = circle(pit, PIT_D)
    # --- lounge seats: sequential random packing ---------------------------------------------
    seat_gap = rng.choice([1.2, 1.35, 1.5])
    seats: list[dict] = []
    placed: list = []
    wall = None
    if idea == "W":
        wl = rng.choice([3.0, 3.5, 4.0, 5.0])
        on_south = rng.random() < .7
        w0 = rng.uniform(wm + 0.2, B - wl - 0.1) if on_south else rng.uniform(1.0, A - wl)
        wall = R(A - 0.45, w0, A, w0 + wl) if on_south else R(w0, B - 0.45, w0 + wl, B)
        if wall[3] > B + 1e-9 or wall[2] > A + 1e-9 or not (_fits(wall, [rbox(tr)], 1.2) and pc.distance(rbox(wall)) >= seat_gap):
            return None
        seats.append({"rect": wall, "seats": int(wl / 0.5), "wall": True})
        placed.append(rbox(wall))
        beds = carve(beds, rbox(wall))
        bedshapes = [rbox(b["rect"]) for b in beds]
    got = sum(s["seats"] for s in seats)
    tries = 0
    while got < n_l and tries < 600:
        tries += 1
        u2 = rng.random() < .4
        vert = rng.random() < .5
        w, h = (SEAT * (2 if u2 else 1), SEAT) if not vert else (SEAT, SEAT * (2 if u2 else 1))
        rr, th = rng.uniform(PIT_D / 2 + seat_gap + 0.3, PIT_D / 2 + seat_gap + 2.0), rng.uniform(0, 2 * math.pi)
        ca, cb = pit[0] + rr * math.cos(th), pit[1] + rr * math.sin(th)
        r = R(ca - w / 2, cb - h / 2, ca + w / 2, cb + h / 2)
        if r[0] < 0 or r[2] > A or r[1] < wm or r[3] > B:
            continue
        sh = rbox(r)
        if any(sh.intersects(b) for b in bedshapes) or sh.distance(pc) < seat_gap or sh.distance(rbox(tr)) < 1.2:
            continue
        if any(sh.distance(o) < 0.05 for o in placed) or sh.intersects(rbox(R(0, DOOR_B[0], 1.2, HOUSE_B1))):
            continue
        if (r[1] < dining[3] - 1e-9) if idea != "O" else (r[3] > dining[1] + 1e-9):      # lounge and dining stay side by side
            continue
        # a seat faces the fire: it must be closer to the pit than the table is (a lounge, not an overflow)
        if sh.distance(pc) > 3.6:
            continue
        seats.append({"rect": r, "seats": 2 if u2 else 1})
        placed.append(sh)
        got += 2 if u2 else 1
    if got < 4:
        return None
    xs = [s["rect"][0] for s in seats] + [s["rect"][2] for s in seats] + [pit[0] - PIT_D / 2, pit[0] + PIT_D / 2]
    ys = [s["rect"][1] for s in seats] + [s["rect"][3] for s in seats] + [pit[1] - PIT_D / 2, pit[1] + PIT_D / 2]
    lounge = R(max(min(xs) - 0.2, 0), max(min(ys) - 0.2, 0), min(max(xs) + 0.2, A), min(max(ys) + 0.2, B))
    if box(*lounge).intersection(rbox(dining)).area > 0.05:
        # separate the two rooms along the axis in which they are apart (the table zone keeps its area)
        if lounge[1] >= b_t:
            lounge[1] = max(lounge[1], dining[3])
        else:
            lounge[3] = min(lounge[3], dining[1])
        if lounge[1] >= lounge[3] or box(*lounge).intersection(rbox(dining)).area > 0.05:
            return None
    if min(lounge[2] - lounge[0], lounge[3] - lounge[1]) < 1.0:
        return None
    # --- quiet nook: a 2-seat bench, least overlooked of a few trial positions -------------------
    best, bestq = None, 1e9
    for _ in range(120):
        a0, b0 = rng.uniform(0.3, A - 1.5), rng.uniform(wm + 0.05, B - 1.45)
        qr = R(a0, b0, a0 + 1.4, b0 + 1.4)
        bench = R(a0 + 0.3, b0 + 0.1, a0 + 0.85, b0 + 1.3)
        qs = rbox(qr)
        if qs.intersects(rbox(dining)) or qs.intersects(box(*lounge)) or any(qs.distance(o) < 0.05 for o in placed) or rbox(bench).distance(rbox(tr)) < 1.2:
            continue
        if circle(pit, PIT_D).distance(qs) < 1.5 or any(qs.intersects(b) for b in bedshapes):
            continue
        e = S.eyes_total(M_(qr), "seated", screen_top_z=(S.FLOOR_Z + 2.1) if screened else None)
        if e < bestq:
            best, bestq = {"rect": qr, "bench": bench, "seats": 2}, e
    if idea == "O":
        c0 = next(b["rect"] for b in beds if b["id"] == "bed-corner")
        # nook sits just inside the orchard bed's open side
        qr = R(max(c0[0] - 1.5, dining[2] + 0.1), c0[1] + 0.2, max(c0[0] - 1.5, dining[2] + 0.1) + 1.4, c0[1] + 1.6)
        qs = rbox(qr)
        if not (qs.intersects(rbox(dining)) or qs.intersects(box(*lounge)) or any(qs.intersects(b) for b in bedshapes)
                or any(qs.distance(o) < 0.05 for o in placed) or circle(pit, PIT_D).distance(qs) < 1.5 or qs.distance(rbox(tr)) < 1.2):
            best = {"rect": qr, "bench": R(qr[0] + 0.3, qr[1] + 0.1, qr[0] + 0.85, qr[1] + 1.3), "seats": 2}
    if best is None:
        return None
    quiet = best
    # --- bbq stand place: 0.9 x 0.6 on hard floor, 0.9 m clear of everything -----------------------
    solids = bedshapes + [rbox(s["rect"]) for s in seats] + [rbox(tr), pc, rbox(quiet["bench"]), house] + fences
    bbq = None
    for _ in range(60):
        if rng.random() < .5:
            ba, bb, w, h = rng.uniform(0.3, A - 0.3), rng.uniform(wm + .45, B - .45), 0.6, 0.9
        else:
            ba, bb, w, h = rng.uniform(0.45, A - .45), rng.uniform(wm + .3, B - .3), 0.9, 0.6
        r = R(ba - w / 2, bb - h / 2, ba + w / 2, bb + h / 2)
        if r[0] < 0 or r[2] > A or r[1] < wm or r[3] > B:
            continue
        if _fits(r, solids[:-1], 0.95) and rbox(r).distance(rbox(tr)) >= 1.2:
            bbq = r
            break
    if bbq is None:
        return None
    # --- terracotta pot with a frangipani (client standing decisions), beside the nook ---------------------
    pots = []
    qr0 = quiet["rect"]
    for (pa, pb) in [(qr0[2] + 0.35, qr0[1] + 0.3), (qr0[0] - 0.35, qr0[1] + 0.3), (qr0[0] + 0.7, qr0[3] + 0.35), (qr0[0] + 0.7, qr0[1] - 0.35)]:
        pr_ = R(pa - 0.3, pb - 0.3, pa + 0.3, pb + 0.3)
        if pr_[0] < 0 or pr_[2] > A or pr_[1] < wm or pr_[3] > B:
            continue
        pb_ = rbox(pr_)
        if _fits(pr_, solids[:-1] + [rbox(bbq)], 0.1) and pb_.distance(rbox(tr)) >= 1.2 and pb_.distance(pc) >= 0.95 and not pb_.intersects(rbox(quiet["rect"])):
            pots.append({"species": "plumeria_rubra", "rect": pr_, "container": True})
            break
    trees = []
    if idea == "O":
        c = next(b["rect"] for b in beds if b["id"] == "bed-corner")
        trees.append({"species": "punica_granatum", "center": ((c[0] + c[2]) / 2, (c[1] + c[3]) / 2)})
    # H and W: the south beds are 0.6-1.2 m deep; no tree canopy fits (LDG-SPREAD), so no tree (0 per 100 m2, below the precedent range)
    cover_rooms = rng.choice([("dining",), ("dining", "lounge"), ("dining", "lounge", "quiet")])
    cover = []
    if "dining" in cover_rooms:
        cover.append(list(dining))
    if "lounge" in cover_rooms:
        cover.append(list(lounge))
    if "quiet" in cover_rooms:
        cover.append(list(quiet["rect"]))
    return {
        "idea": idea, "variant": variant,
        "params": {"wm": wm, "hw": hw, "sbd": sbd, "n_d": n_d, "n_l": n_l, "pit": (round(pit[0], 2), round(pit[1], 2))},
        "dining": dining, "table": {"center": (a_t, b_t), "size": (W, L), "seats": n_d}, "lounge": lounge, "seats": seats,
        "pit": {"center": pit, "d": PIT_D}, "bbq": bbq, "beds": beds, "quiet": quiet, "trees": trees, "cover": cover,
        "cover_rooms": cover_rooms, "pots": pots, "path": R(0, DOOR_B[0], 1.2, min(DOOR_B[1] + 0.9, HOUSE_B1)), "wm": wm, "hw": hw,
        "screen_top_h": 2.1 if screened else None,
    }


def M_(r):
    return S.rect_to_model(r)


def floor_of(c) -> "box":
    """Paved floor = the garden rectangle minus beds and the quiet nook is paved (a pad) so it stays."""
    g = box(0, 0, A, B)
    g = g.difference(union([rbox(b["rect"]) for b in c["beds"]]))
    return g


def standing_zone(c):
    d = rbox(c["dining"]).union(box(*c["lounge"]))
    free = floor_of(c).difference(d.buffer(0.0)).difference(rbox(c["quiet"]["rect"]).buffer(0.05)).difference(
        union([rbox(s["rect"]).buffer(0.3) for s in c["seats"]]))
    r = largest_rect(free, 0.1)
    if not r or area(r) < 3.9:
        return None
    return r


def event_capacity(c, per_person):
    """People standing at an event when furniture stays: free paved area / 1.3 m2 (LS-STAND-AREA)."""
    floor = floor_of(c)
    occ = union([rbox(s["rect"]).buffer(0.1) for s in c["seats"]] +
                [box(c["table"]["center"][0] - c["table"]["size"][0] / 2 - 0.5, c["table"]["center"][1] - c["table"]["size"][1] / 2 - 0.5,
                     c["table"]["center"][0] + c["table"]["size"][0] / 2 + 0.5, c["table"]["center"][1] + c["table"]["size"][1] / 2 + 0.5),
                 circle(c["pit"]["center"], PIT_D + 0.6)])
    return floor.difference(occ).area / per_person
