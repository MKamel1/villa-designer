"""D1 furniture in 3D (Phase 2): each authored piece of `villa_furnish.layout` as procedural solids for the Revit
model, and the post-condition that checks the model's read-back against the plan.

No furniture families exist on this machine (the Revit Libraries hold 0 beds), so every piece is a DirectShape
built from boxes. The shapes are placeholders for the product models chosen later: they carry the checked
footprint and height, and enough form (a bed's mattress and headboard, a sofa's back and arms, a run's worktop and
plinth) to read in a plan and a massing render. They invent no size: every box lies inside the piece's footprint,
up to its height, except the parts named in ABOVE (a headboard, a wall-hung WC's flush plate, a TV screen, a
shower screen), and the chairs and stools, which are separate elements (`<id>#chair-n`) outside the table.

Frames: local x across the piece (right = +x), local y front = +y, z up from the storey's finished floor; world
mapping as in `villa_furnish` (`rot` 0 front +y, 180 front -y, -90 front +x, 90 front -x).
"""
from __future__ import annotations

from . import villa_furnish as F

# where a part may rise above the piece's checked height h (name -> why)
ABOVE = {"headboard": "a bed's headboard stands against the wall, above the mattress",
         "flush-plate": "a wall-hung WC's flush plate on the wall",
         "screen": "the TV screen above its unit / on the wall",
         "glass": "a walk-in shower's fixed glass screen",
         "wall-units": "wall cupboards over the tall wall's counters",
         "nook-side": "the daybed's tall joinery surround", "nook-top": "the daybed nook top"}

CATEGORY = {"base_run": "casework", "island": "casework", "tall_column": "casework", "pantry_shelving": "casework",
            "bookcase": "casework", "daybed_nook": "casework", "joinery_end_panel": "casework",
            "store_shelving": "casework", "under_stair_storage": "casework", "folding_counter": "casework",
            "wc": "plumbing", "washbasin": "plumbing", "washbasin_double": "plumbing", "bath": "plumbing",
            "shower_walkin": "plumbing", "washer_dryer": "equipment", "screen": "equipment"}

# parts of a storage body that are the stored belongings (dressing), not the joinery; kept out of the Revit payload
STORED_CONTENTS = {"folded-linens", "storage-box", "suitcase", "suitcase-handle", "vacuum-body", "vacuum-wand",
                   "tool-case"}
TALL_MODULES = {"fridge", "oven", "microwave", "tall"}
COUNTER_TOP = 0.90           # worktop height (the catalogue's run height)
PLINTH, PLINTH_SET = 0.10, 0.05
# advisory targets adopted from villa_01_guidelines.docx (K-SPLASH / K-UPPER, K-OVERHANG): sound practice
SPLASH = 0.60                # worktop to the underside of the wall units (units from 1.50 m)
OVERHANG = 0.025             # worktop beyond the cabinet face


def to_world(it, b):
    """A local box (x0, y0, z0, x1, y1, z1) -> world (x0, y0, z0, x1, y1, z1), z from the storey FFL."""
    x0, y0, z0, x1, y1, z1 = b
    cx, cy, r = it["cx"], it["cy"], it["rot"]
    if r == 0:
        xs, ys = (cx + x0, cx + x1), (cy + y0, cy + y1)
    elif r == 180:
        xs, ys = (cx - x1, cx - x0), (cy - y1, cy - y0)
    elif r == -90:
        xs, ys = (cx + y0, cx + y1), (cy - x1, cy - x0)
    else:
        xs, ys = (cx - y1, cx - y0), (cy + x0, cy + x1)
    return (round(xs[0], 4), round(ys[0], 4), round(z0, 4), round(xs[1], 4), round(ys[1], 4), round(z1, 4))


def _legs(W, D, z1, t=0.05, inset=0.03):
    a, b = W / 2 - inset, D / 2 - inset
    return [("leg", (sx * a - (t if sx > 0 else 0), sy * b - (t if sy > 0 else 0), 0,
                     sx * a + (0 if sx > 0 else t), sy * b + (0 if sy > 0 else t), z1))
            for sx in (-1, 1) for sy in (-1, 1)]


def _chair(xc, y0, y1, back_at_high_y, seat=0.46, back=0.85, w=0.44):
    """A dining / desk chair between y0 and y1 (local), its back on the far side."""
    parts = [("seat", (xc - w / 2, y0, seat - 0.04, xc + w / 2, y1, seat))]
    for sx in (-1, 1):
        for yy in (y0, y1 - 0.04):
            parts.append(("leg", (xc + sx * (w / 2 - 0.02) - 0.02, yy, 0, xc + sx * (w / 2 - 0.02) + 0.02, yy + 0.04,
                                  seat - 0.04)))
    yb = (y1 - 0.03, y1) if back_at_high_y else (y0, y0 + 0.03)
    parts.append(("back", (xc - w / 2, yb[0], seat, xc + w / 2, yb[1], back)))
    return parts


def _stool(xc, y0, y1, seat=0.65):
    c = (y0 + y1) / 2
    return [("base", (xc - 0.18, c - 0.18, 0, xc + 0.18, c + 0.18, 0.02)),
            ("post", (xc - 0.025, c - 0.025, 0.02, xc + 0.025, c + 0.025, seat - 0.05)),
            ("footrest", (xc - 0.15, c - 0.15, 0.25, xc + 0.15, c + 0.15, 0.27)),
            ("seat", (xc - 0.19, y0 + 0.01, seat - 0.05, xc + 0.19, y1 - 0.01, seat))]


def body(it):
    """The piece's own parts [(name, local box)], all inside the footprint (x in +-w/2, y in +-d/2)."""
    W, D, H, t = it["w"], it["d"], it["h"], it["type"]
    x0, x1, yb, yf = -W / 2, W / 2, -D / 2, D / 2
    if it["id"] == "library-daybed":
        # The separate full-height surround is part of the nook, while the mattress stays low.
        return [("base", (x0, yb, 0, x1, yf, 0.25)),
                ("mattress", (x0, yb + 0.025, 0.25, x1, yf - 0.025, H)),
                ("nook-side", (x0, yb, 0, x0 + 0.025, yf, it["nook_top"])),
                ("nook-side", (x1 - 0.025, yb, 0, x1, yf, it["nook_top"])),
                ("nook-top", (x0, yb, it["nook_top"] - 0.025, x1, yf, it["nook_top"]))]
    if t.startswith("bed_"):
        if H >= 1.5:                                                # a bunk bed
            p = [("post", (sx * W / 2 - (0.06 if sx > 0 else 0), sy * D / 2 - (0.06 if sy > 0 else 0), 0,
                           sx * W / 2 + (0 if sx > 0 else 0.06), sy * D / 2 + (0 if sy > 0 else 0.06), H))
                 for sx in (-1, 1) for sy in (-1, 1)]
            p += [("lower-frame", (x0, yb, 0.15, x1, yf, 0.25)), ("lower-mattress", (x0 + 0.03, yb + 0.06, 0.25,
                                                                                     x1 - 0.03, yf - 0.06, 0.4)),
                  ("upper-frame", (x0, yb, 1.15, x1, yf, 1.25)), ("upper-mattress", (x0 + 0.03, yb + 0.06, 1.25,
                                                                                     x1 - 0.03, yf - 0.06, 1.4)),
                  ("rail", (x1 - 0.04, yb + 0.5, 1.4, x1, yf - 0.06, H))]
            # The rail occupies +x; the ladder climbs the open -x side near
            # the foot. Its rails and treads stay within the checked box.
            la, lb = yf - 0.72, yf - 0.26
            p += [("ladder-stile", (x0, la, 0, x0 + 0.045, la + 0.045, 1.47)),
                  ("ladder-stile", (x0, lb - 0.045, 0, x0 + 0.045, lb, 1.47))]
            p += [("ladder-rung", (x0, la + 0.025, z, x0 + 0.065, lb - 0.025, z + 0.035))
                  for z in (0.32, 0.59, 0.86, 1.13)]
            return p
        return [("base", (x0, yb, 0.0, x1, yf, 0.25)),
                ("mattress", (x0 + 0.02, yb + 0.06, 0.25, x1 - 0.02, yf - 0.02, H)),
                ("headboard", (x0, yb, 0.0, x1, yb + 0.06, 1.05))]
    if t.startswith("sofa") or t in ("armchair", "recliner"):
        arm = 0.12 if t in ("armchair", "recliner") else 0.16
        return [("base", (x0 + arm, yb, 0.0, x1 - arm, yf, 0.22)),
                ("seat", (x0 + arm, yb + 0.22, 0.22, x1 - arm, yf, 0.44)),
                ("back", (x0 + arm, yb, 0.22, x1 - arm, yb + 0.22, H)),
                ("arm", (x0, yb, 0.0, x0 + arm, yf, 0.62)), ("arm", (x1 - arm, yb, 0.0, x1, yf, 0.62))]
    if t in ("coffee_table",):
        return [("top", (x0, yb, H - 0.05, x1, yf, H)), ("shelf", (x0 + 0.05, yb + 0.05, 0.1, x1 - 0.05, yf - 0.05,
                                                                   0.12))] + _legs(W, D, H - 0.05)
    if t == "under_stair_storage":
        from . import revit_spec as RS
        from . import villa_r11 as R
        parts = []
        treads = RS.build(R.design("D1"))["stair"] if it.get("soffit") == "stair" else []
        for kind, a, b in _local_modules(it):
            spans = []
            if treads:
                for box in treads:
                    xa = max(a, box[0] / 1000 - it["cx"])
                    xb = min(b, box[3] / 1000 - it["cx"])
                    if xb > xa + 1e-6:
                        spans.append((xa, xb, min(H, box[2] / 1000 - RS.LEVELS_Z["B"] - 0.05)))
            else:
                spans = [(a, b, H)]
            for xa, xb, top in spans:
                if top < 0.15:
                    continue
                width = xb - xa
                parts.extend([("plinth", (xa, yb, 0, xb, yf, 0.1)),
                              (kind + "-back", (xa, yb, 0.1, xb, yb + 0.018, top))])
                if top > 0.65:
                    parts.append((kind + "-shelf", (xa, yb + 0.02, min(0.55, top - 0.08),
                                                     xb, yf - 0.04, min(0.57, top - 0.06))))
                inner_a, inner_b = xa + 0.04, xb - width * 0.31
                if inner_b - inner_a > 0.07 and top > 0.40:
                    cy0, cy1 = yb + 0.07, yf - 0.08
                    if kind == "standing-access":
                        parts += [("vacuum-body", (inner_a + 0.06, cy0, 0.12, inner_a + 0.16, cy0 + 0.12,
                                                   min(top - 0.08, 0.56))),
                                  ("vacuum-wand", (inner_a + 0.10, cy0 + 0.045, 0.49,
                                                   inner_a + 0.125, cy0 + 0.07, min(top - 0.06, 1.25)))]
                    elif kind == "luggage":
                        parts += [("suitcase", (inner_a + 0.02, cy0, 0.12, inner_b - 0.02, cy1,
                                                 min(top - 0.08, 0.47))),
                                  ("suitcase-handle", (inner_a + 0.12, cy0 + 0.04, 0.47,
                                                        inner_b - 0.12, cy0 + 0.065, min(top - 0.06, 0.51)))]
                    else:
                        parts.append(("storage-box", (inner_a + 0.02, cy0, 0.10,
                                                       inner_b - 0.02, cy1, min(top - 0.08, 0.38))))
                        if top > 0.85:
                            parts.append(("folded-linens", (inner_a + 0.02, cy0, 0.57,
                                                             inner_b - 0.02, cy1, min(top - 0.07, 0.70))))
            if spans:
                # The back follows the stair in small spans, but each bay has two end panels.
                parts.append((kind + "-side", (a, yb, 0.1, a + 0.018, yf,
                                               min(top for xa, xb, top in spans if xa < a + 0.018))))
                parts.append((kind + "-side", (b - 0.018, yb, 0.1, b, yf,
                                               min(top for xa, xb, top in spans if xb > b - 0.018))))
                # One pocket per full bay. The stair profile divides the carcass into tread-sized
                # spans; adding a leaf in that inner loop produced ten tall visible strips.
                pocket_top = min(top for _, _, top in spans)
                parts.append(("sliding-door-pocketed", (b - 0.038, yb + 0.035, 0.1,
                                                        b - 0.020, yf - 0.055, pocket_top)))
        return parts
    if t in ("dining_6x", "desk"):
        return [("top", (x0, yb, H - 0.04, x1, yf, H))] + _legs(W, D, H - 0.04)
    if t == "island":                                               # carcass set back 300 mm under the seating side
        p = [("worktop", (x0, yb, H - 0.04, x1, yf, H)),
             ("plinth", (x0 + PLINTH_SET, yb + 0.3 + PLINTH_SET, 0, x1 - PLINTH_SET, yf - PLINTH_SET, PLINTH))]
        if it.get("waterfall_ends") == "both-short":
            # Same stone and full top depth on the two short x ends, floor to worktop.
            p += [("waterfall-end", (x0, yb, 0, x0 + 0.04, yf, H)),
                  ("waterfall-end", (x1 - 0.04, yb, 0, x1, yf, H))]
        for kind, a, b in _local_modules(it):
            p.append((kind, (a, yb + 0.3, PLINTH, b, yf, H - 0.04)))
            if kind == "single-induction" and it.get("downdraft_basis"):
                p.append(("single-induction-zone", (a + 0.02, -0.155, H - 0.006,
                                                    b - 0.02, 0.155, H)))
                p.append(("downdraft", (a, -0.34, H - 0.012, b, -0.26, H)))
        return p
    if t == "base_run":
        p = []
        tall_wall = H > COUNTER_TOP + 0.3
        for kind, a, b in _local_modules(it):
            if kind in TALL_MODULES and tall_wall:
                p.append((kind, (a, yb, 0, b, yf, H)))
                continue
            p += [("plinth", (a, yb, 0, b, yf - PLINTH_SET, PLINTH)),
                  (kind, (a, yb, PLINTH, b, yf - OVERHANG, COUNTER_TOP - 0.04)),   # worktop overhangs 25 mm
                  ("worktop", (a, yb, COUNTER_TOP - 0.04, b, yf, COUNTER_TOP))]
            if tall_wall:
                p.append(("wall-units", (a, yb, COUNTER_TOP + SPLASH, b, yb + 0.35, H)))
        return p
    if t in ("bookcase", "pantry_shelving", "store_shelving"):
        if t == "store_shelving" and it.get("soffit") == "ramp":
            from . import villa_parking as VP
            parts = []
            for kind, a, b in _local_modules(it):
                world = to_world(it, (a, yb, 0, b, yf, H))
                top = min(H, VP.clear_at(world[0]) - 0.05, VP.clear_at(world[3]) - 0.05)
                parts += [(kind + "-back", (a, yb, 0, b, yb + 0.02, top)),
                          (kind + "-base", (a, yb, 0.1, b, yf, 0.12)),
                          (kind + "-side", (a, yb, 0, a + 0.02, yf, top)),
                          (kind + "-side", (b - 0.02, yb, 0, b, yf, top))]
                if kind != "bikes":
                    for z in (0.55, 1.05):
                        if z + 0.02 < top:
                            parts.append((kind + "-shelf", (a, yb, z, b, yf, z + 0.02)))
                    parts.append(("suitcase" if kind == "luggage" else "storage-box",
                                  (a + 0.08, yb + 0.06, 0.12, b - 0.08, yf - 0.06, 0.48)))
                    if top > 1.35:
                        parts.append(("tool-case" if kind == "seasonal-boxes" else "storage-box",
                                      (a + 0.12, yb + 0.08, 1.07, b - 0.12, yf - 0.08, 1.31)))
                else:
                    parts.append(("bikes-hooks", (a + 0.05, yb, top - 0.2, b - 0.05, yb + 0.12, top - 0.15)))
            return parts
        p = [("back", (x0, yb, 0, x1, yb + 0.02, H)), ("side", (x0, yb, 0, x0 + 0.02, yf, H)),
             ("side", (x1 - 0.02, yb, 0, x1, yf, H))]
        n = max(2, int(H / 0.38))
        for k in range(n + 1):
            z = min(H - 0.02, k * H / n)
            p.append(("shelf", (x0 + 0.02, yb + 0.02, z, x1 - 0.02, yf, z + 0.02)))
        if it.get("glazing") == "glass-doors":
            p.extend([("glass-door", (x0 + 0.02, yf - 0.015, 0.04, -0.01, yf, H - 0.04)),
                      ("glass-door", (0.01, yf - 0.015, 0.04, x1 - 0.02, yf, H - 0.04))])
        return p
    if t == "wardrobe" and str(it.get("room", "")).startswith("parents-dressing"):   # open hanging, no doors
        if it.get("modules"):
            parts = [("plinth", (x0, yb, 0, x1, yf, PLINTH)),
                     ("top-boxes", (x0, yb, 2.1, x1, yf, H)),
                     ("hanger-storage", (x0, yb, 2.05, x1, yf, 2.1))]
            for kind, a, b in _local_modules(it):
                parts.extend([("divider", (a, yb, 0, a + 0.02, yf, H)),
                              ("back", (a, yb, 0, b, yb + 0.02, H))])
                if kind == "long-hang":
                    parts.append(("long-hang-rail", (a + 0.02, -0.01, 1.87, b - 0.02, 0.01, 1.90)))
                elif kind == "double-hang":
                    for z in (1.0, 1.95):
                        parts.append(("double-hang-rail", (a + 0.02, -0.01, z, b - 0.02, 0.01, z + 0.03)))
                elif kind == "drawers":
                    for index, label in enumerate(it["drawers"]):
                        z = 0.11 + index * 0.25
                        parts.append(("drawer-" + label, (a + 0.02, yb + 0.02, z, b - 0.02, yf, z + 0.23)))
                elif kind == "trousers-pullout":
                    parts.append(("trousers-pullout", (a + 0.02, yb + 0.02, 0.65, b - 0.02, yf, 0.72)))
                else:
                    for z in (0.5, 1.0, 1.5, 2.0):
                        parts.append((kind, (a + 0.02, yb + 0.02, z, b - 0.02, yf, z + 0.02)))
            return parts
        return [("back", (x0, yb, 0, x1, yb + 0.02, H)), ("side", (x0, yb, 0, x0 + 0.02, yf, H)),
                ("side", (x1 - 0.02, yb, 0, x1, yf, H)), ("plinth", (x0, yb, 0, x1, yf, PLINTH)),
                ("shelf", (x0, yb, H - 0.25, x1, yf, H - 0.23)), ("top", (x0, yb, H - 0.02, x1, yf, H)),
                ("rail", (x0 + 0.02, -0.01, H - 0.32, x1 - 0.02, 0.01, H - 0.30))]
    if t in ("wardrobe", "tall_column", "sideboard", "bedside_table", "washer_dryer", "folding_counter",
             "window_bench"):
        top = H if t != "folding_counter" else H - 0.04
        p = [("plinth", (x0 + PLINTH_SET, yb, 0, x1 - PLINTH_SET, yf - PLINTH_SET, min(PLINTH, top))),
             ("carcass", (x0, yb, min(PLINTH, top), x1, yf, top))]
        if t == "folding_counter":
            p.append(("worktop", (x0, yb, H - 0.04, x1, yf, H)))
        return p
    if t == "tv_unit":
        p = [("unit", (x0, yb, 0.1, x1, yf, H))]
        if it.get("screen_in"):
            sw = it["screen_in"] * 0.0254 * 16 / (337 ** 0.5)       # 16:9 width from the diagonal
            sh = sw * 9 / 16
            z0 = max(H + 0.1, 1.1 - sh / 2)
            p.append(("screen", (-sw / 2, yb, z0, sw / 2, yb + 0.05, z0 + sh)))
        return p
    if t == "screen":                                               # a wall TV: its top at h
        sh = W * 9 / 16
        return [("screen", (x0, yb, H - sh, x1, yf, H))]
    if t == "wc":                                                   # wall-hung pan
        return [("pan", (x0, yb, 0.12, x1, yf, H - 0.02)), ("seat", (x0 + 0.01, yb + 0.05, H - 0.02,
                                                                                    x1 - 0.01, yf, H)),
                ("flush-plate", (-0.12, yb, 0.95, 0.12, yb + 0.02, 1.12))]
    if t in ("washbasin", "washbasin_double"):
        return [("vanity", (x0, yb, 0.35, x1, yf, H - 0.05)), ("basin", (x0, yb, H - 0.05, x1, yf, H))]
    if t == "bath":
        r = 0.07
        return [("floor", (x0, yb, 0, x1, yf, 0.12)), ("rim", (x0, yb, 0.12, x1, yb + r, H)),
                ("rim", (x0, yf - r, 0.12, x1, yf, H)), ("rim", (x0, yb + r, 0.12, x0 + r, yf - r, H)),
                ("rim", (x1 - r, yb + r, 0.12, x1, yf - r, H))]
    if t == "shower_walkin":
        if it.get("wet_zone"):
            # The finish is recessed to finished-floor level. Drain is flush; no tray or screen.
            return [("wet-floor", (x0, yb, -0.006, x1, yf, 0)),
                    ("linear-drain", (x1 - 0.04, yb + 0.06, -0.006, x1 - 0.02, yf - 0.06, 0))]
        return [("tray", (x0, yb, 0, x1, yf, H)), ("glass", (x0 + W * 0.45, yf - 0.01, H, x1, yf, 2.0))]
    return [("block", (x0, yb, 0, x1, yf, H))]


def _local_modules(it):
    out, pos = [], -it["w"] / 2
    for kind, w in it.get("modules", []):
        out.append((kind, pos, pos + w))
        pos += w
    if not out:
        out = [("carcass", -it["w"] / 2, it["w"] / 2)]
    return out


def extras(it):
    """Separate elements beside the piece: dining chairs, island stools, desk chairs [(suffix, parts)]. Placed as the
    furnished plan draws them (scripts/villa_furnish_pdf.py)."""
    W, D = it["w"], it["d"]
    out = []
    if it.get("chairs") and it["type"].startswith("dining"):
        n = it["chairs"] // 2
        for k in range(n):
            xc = -W / 2 + (k + 0.5) * W / n
            out.append(("chair-%d" % (2 * k + 1), _chair(xc, D / 2 + 0.05, D / 2 + 0.5, True)))
            out.append(("chair-%d" % (2 * k + 2), _chair(xc, -D / 2 - 0.5, -D / 2 - 0.05, False)))
    if it.get("stools"):
        for k in range(it["stools"]):
            xc = -W / 2 + (k + 0.5) * W / it["stools"]
            out.append(("stool-%d" % (k + 1), _stool(xc, -D / 2 - 0.05, -D / 2 + 0.35)))
    if it["type"] == "desk":
        n = it.get("chairs", max(1, int(W // 0.9)))
        for k in range(n):
            xc = -W / 2 + (k + 0.5) * W / n
            out.append(("chair-%d" % (k + 1), _chair(xc, D / 2 - 0.15, D / 2 + 0.3, True)))
    return out


def spec(lay=None, items=None):
    """The furniture for the Revit build: one element per piece and per chair / stool, world boxes in metres with z
    from the storey FFL, the element's declared envelope, and its category."""
    items = items or F.layout(lay)
    out = []
    for it in items:
        parts = [(n, to_world(it, b)) for n, b in body(it)]
        out.append({"mark": it["id"], "level": it["level"], "type": it["type"], "room": it["room"],
                    "category": CATEGORY.get(it["type"], "furniture"), "boxes": [b for _, b in parts],
                    "parts": [n for n, _ in parts], "envelope": _env([b for _, b in parts]),
                    "footprint": [round(v, 4) for v in F.footprint(it)], "h": it["h"]})
        for suf, ps in extras(it):
            bs = [to_world(it, b) for _, b in ps]
            out.append({"mark": it["id"] + "#" + suf, "level": it["level"], "type": "chair" if "chair" in suf else
                        "stool", "room": it["room"], "category": "furniture", "boxes": bs, "parts": [n for n, _ in ps],
                        "envelope": _env(bs), "footprint": None, "h": None})
    return out


def _env(bs):
    return [round(min(b[0] for b in bs), 4), round(min(b[1] for b in bs), 4), round(min(b[2] for b in bs), 4),
            round(max(b[3] for b in bs), 4), round(max(b[4] for b in bs), 4), round(max(b[5] for b in bs), 4)]


TOL = 0.005        # PRE-REGISTERED 2026-09-27 before the first build: as-built boxes within 5 mm of the spec


def round2_elements(sp):
    """World-space Revit solids from the approved detail fields. Sizes absent from the intent are labelled ASSUMED."""
    from . import revit_spec as RS
    out = []

    def add(mark, category, box, room=None, comment="", profile=None):
        row = dict(mark=mark, category=category, bbox=[round(v, 4) for v in box], room=room,
                   comments=comment)
        if profile is not None:
            row["profile"] = profile
        out.append(row)

    for p in sp.get("pocket_buildouts", []):
        z = RS.LEVELS_Z[p["level"]]
        y0 = p["y"] if p["extra_side"] == "dirty-kitchen" else p["y"] - p["thickness"]
        add(p["id"], "Walls", [p["x0"], y0, z, p["x1"], y0 + p["thickness"], z + p["height"]],
            comment="pocket buildout; thickness %.3f m" % p["thickness"])
    for h in sp.get("hatches", []):
        z = RS.LEVELS_Z[h["level"]]
        b = h["shutter_box"]
        add(h["id"] + "-shutter", "Generic Models", [b[0], b[1], z + b[2], b[3], b[4], z + b[5]],
            comment=h["closure"])
    for rail in sp.get("balustrades", []):
        pts = rail["nosing_profile"]
        thickness = rail.get("thickness_m")
        assumed = thickness is None
        if assumed:
            thickness = 0.02 if rail["side"] == "open" else 0.04
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            z = RS.LEVELS_Z[rail["level"]]
            profile = [[a[0], z + a[2]], [b[0], z + b[2]],
                       [b[0], z + b[2] + rail["height_above_nosing"]],
                       [a[0], z + a[2] + rail["height_above_nosing"]]]
            y = a[1]
            y0, y1 = (y - thickness, y) if rail["side"] == "open" else (y, y + thickness)
            add("%s-%02d" % (rail["id"], i + 1), "Generic Models",
                [min(a[0], b[0]), y0, min(v[1] for v in profile), max(a[0], b[0]), y1,
                 max(v[1] for v in profile)], room="stair-b", comment="%s; %sthickness %.3f m%s" %
                (rail["material"], "ASSUMED visual " if assumed else "", thickness,
                 "; structural size pending" if assumed else ""), profile=profile)
    for f in sp.get("bath_fittings", []):
        z = RS.LEVELS_Z[f["level"]]
        if f["kind"] == "fixed-frameless-glass":
            box = [f["x0"], f["y"] - 0.01, z + f["sill"], f["x1"], f["y"] + 0.01, z + f["head"]]
            comment = "fixed bath screen; transmittance 0.91; ior 1.52; ASSUMED 20 mm representation thickness"
        elif f["kind"] == "ceiling-rain-head":
            box = [f["x"] - 0.1, f["y"] - 0.1, z + f["z"] - 0.02,
                   f["x"] + 0.1, f["y"] + 0.1, z + f["z"]]
            comment = "rain head; ASSUMED 200 mm representation diameter"
        elif f["kind"] == "linear-drain":
            box = [f["x0"], f["y0"], z - 0.006, f["x1"], f["y1"], z]
            comment = "flush linear drain; open level-access wet zone, no upstand or enclosure; " + f["basis"]
        else:
            add(f["id"] + "-rail", "Generic Models",
                [f["x"] - 0.015, f["y"] - 0.015, z + f["z"] - 0.4,
                 f["x"] + 0.015, f["y"] + 0.015, z + f["z"] + 0.1], f["room"],
                "hand shower rail; ASSUMED representation size")
            add(f["id"] + "-head", "Generic Models",
                [f["x"] - 0.05, f["y"] - 0.03, z + f["z"] + 0.04,
                 f["x"] + 0.05, f["y"] + 0.03, z + f["z"] + 0.1], f["room"],
                "hand shower head; ASSUMED representation size")
            continue
        add(f["id"], "Generic Models", box, f["room"], comment)
    for vent in sp.get("ventilation", []):
        z = RS.LEVELS_Z[vent["level"]]
        x, y, h = vent["fan"]
        x2, y2, h2 = vent["duct_route"][-1]
        note = "%s; %.1f l/s; card %s" % (vent["kind"], vent["rate_ls"], vent["card"])
        add(vent["id"] + "-fan", "Mechanical Equipment",
            [x - 0.05, y - 0.05, z + h - 0.05, x + 0.05, y + 0.05, z + h + 0.05], vent["room"],
            note + "; ASSUMED 100 mm representation size")
        add(vent["id"] + "-duct", "Ducts",
            [min(x, x2) - 0.04, min(y, y2) - 0.04, z + min(h, h2) - 0.04,
             max(x, x2) + 0.04, max(y, y2) + 0.04, z + max(h, h2) + 0.04],
            comment=note + "; ASSUMED 80 mm representation width")
        add(vent["id"] + "-grille", "Mechanical Equipment",
            [x2 - 0.06, y2 - 0.02, z + h2 - 0.06, x2 + 0.06, y2 + 0.02, z + h2 + 0.06],
            comment=note + "; external grille; ASSUMED 120 mm representation size")
    return out


def round3_elements(sp, lay=None):
    """Nook lights, dressing modules and soffit cut storage as separately measurable solids."""
    from . import revit_spec as RS
    from . import villa_lighting as L
    lay = lay or F.R.design("D1")
    out = []

    def add(mark, category, level, box, comments):
        z = RS.LEVELS_Z[level]
        out.append(dict(mark=mark, category=category,
                        bbox=[round(v + (z if k in (2, 5) else 0), 4) for k, v in enumerate(box)],
                        comments=comments))

    for light in L.design(lay):
        if light.room != "bar-alcove" or light.kind not in ("SWING", "DLN"):
            continue
        z = light.z - RS.LEVELS_Z[light.level]
        if light.kind == "SWING":
            x, y = light.extra["wall_plate"]
            side = light.extra["mount_side"]
            outward = -1 if side == "left" else 1
            add(light.id + "-plate", "Lighting Fixtures", light.level,
                [min(x, x - outward * .012), y - .06, z - .06,
                 max(x, x - outward * .012), y + .06, z + .06],
                "SWING side-panel wall plate; articulated reach 0.6 m")
            add(light.id + "-arm", "Lighting Fixtures", light.level,
                [min(x, light.x) - .012, min(y, light.y) - .012, z - .012,
                 max(x, light.x) + .012, max(y, light.y) + .19, z + .012],
                "SWING articulated arm; reach 0.6 m")
            add(light.id + "-head", "Lighting Fixtures", light.level,
                [light.x - .06, light.y - .06, z - .06, light.x + .06, light.y + .06, z + .06],
                "SWING rotating head; emitter at spec position")
        else:
            add(light.id, "Lighting Fixtures", light.level,
                [light.x - .0375, light.y - .0375, z, light.x + .0375, light.y + .0375, z + .025],
                "DLN recessed nook downlight; emitter at spec position")

    for it in F.layout(lay):
        if it["id"] in ("pd-hang-1", "pd-hang-2"):
            for index, (kind, a, b) in enumerate(_local_modules(it), 1):
                box = to_world(it, (a, -it["d"] / 2 + .03, .10, b, it["d"] / 2 - .03, 2.05))
                add("%s-module-%02d" % (it["id"], index), "Casework", it["level"], box,
                    "owner %s; kind %s" % (it["partner"], kind))
        if it["type"] in ("under_stair_storage", "store_shelving") and it.get("soffit"):
            # stored belongings are render dressing, not construction: they never go to Revit
            for index, (kind, box) in enumerate([pb for pb in body(it) if pb[0] not in STORED_CONTENTS], 1):
                add("%s-body-%03d" % (it["id"], index), "Casework", it["level"], to_world(it, box),
                    "%s; %s; soffit %s" % (it["type"], kind, it["soffit"]))
    return out


def round3_postcondition(sp, rb, lay=None):
    """Compare every new native element's tag, category and world box to the authored D1 spec."""
    expected = sp["round3_elements"] if "round3_elements" in sp else round3_elements(sp, lay)
    got = {}
    for row in rb.get("round3_details", []):
        got.setdefault(row.get("mark") or row.get("spec_id"), []).append(row)
    problems = []
    for item in expected:
        mark = item["mark"]
        rows = got.get(mark, [])
        if len(rows) != 1:
            problems.append("%s: built %d times" % (mark, len(rows)))
            continue
        row = rows[0]
        if row.get("mark") != mark:
            problems.append("%s: Mark missing or differs" % mark)
        if row.get("category") != item["category"]:
            if not (item["category"] == "Lighting Fixtures" and row.get("category") == "Generic Models" and
                    "fixture kind " in (row.get("comments") or "")):
                problems.append("%s: category differs" % mark)
        comment = row.get("comments") or ""
        if comment != item["comments"] and comment != item["comments"] + "; fixture kind " + mark.split("-")[0]:
            problems.append("%s: Comments differ" % mark)
        box = row.get("bbox_mm") or []
        if len(box) != 6 or max(abs(a / 1000 - b) for a, b in zip(box, item["bbox"])) > TOL + 1e-8:
            problems.append("%s: world bbox more than 5 mm from spec" % mark)
    for mark in set(got) - {x["mark"] for x in expected}:
        problems.append("%s: unplanned round-3 detail" % mark)
    furniture_spec = {x["mark"]: x for x in sp.get("furniture", [])}
    furniture_got = {}
    for row in rb.get("furniture", []):
        furniture_got.setdefault(row.get("mark"), []).append(row)
    for mark in ("lounge-armchair", "stair-flight-store", "stair-landing-store", "store-shelves"):
        item = furniture_spec.get(mark)
        rows = furniture_got.get(mark, [])
        if item is None or len(rows) != 1:
            problems.append("%s: furniture missing from spec or built %d times" % (mark, len(rows)))
            continue
        row = rows[0]
        if row.get("category") != item["category"] or item["type"] not in (row.get("comments") or ""):
            problems.append("%s: furniture category or Comments differ" % mark)
        box = row.get("bbox_mm") or []
        from . import revit_spec as RS
        z = RS.LEVELS_Z[item["level"]]
        wanted = [v + (z if k in (2, 5) else 0) for k, v in enumerate(item["envelope"])]
        if len(box) != 6 or max(abs(a / 1000 - b) for a, b in zip(box, wanted)) > TOL + 1e-8:
            problems.append("%s: furniture world bbox more than 5 mm from spec" % mark)
    for row in rb.get("furniture", []) + rb.get("round3_details", []):
        if "curtain" in (row.get("mark") or "").lower() or (row.get("mark") == "library-daybed" and
                                                          "curtain" in (row.get("comments") or "").lower()):
            problems.append("library nook curtain still built")
    return problems


def round2_postcondition(sp, rb, lay):
    """Measured detail boxes, opening and sliding leaf; 5 mm on each face and no column/room escape."""
    from .. import villa_env as E
    from . import revit_spec as RS
    expected = round2_elements(sp)
    got = {}
    problems = []
    for row in rb.get("details", []):
        got.setdefault(row.get("mark"), []).append(row)
    for item in expected:
        mark = item["mark"]
        rows = got.get(mark, [])
        if len(rows) != 1:
            problems.append("%s: built %d times" % (mark, len(rows)))
            continue
        row = rows[0]
        if row.get("category") != item["category"]:
            problems.append("%s: category %s, expected %s" % (mark, row.get("category"), item["category"]))
        if row.get("comments") != item["comments"]:
            problems.append("%s: Comments differ from approved detail" % mark)
        if len(row.get("bbox_mm", [])) != 6:
            problems.append("%s: missing measured world bbox" % mark)
            continue
        b = [v / 1000.0 for v in row["bbox_mm"]]
        if max(abs(a - c) for a, c in zip(b, item["bbox"])) > TOL + 1e-8:
            problems.append("%s: world bbox more than 5 mm from spec" % mark)
        room = item["room"]
        if room:
            rect = lay["rooms"][room]["rect"]
            if b[0] < rect[0] - TOL or b[1] < rect[1] - TOL or b[3] > rect[2] + TOL or b[4] > rect[3] + TOL:
                problems.append("%s: leaves room %s" % (mark, room))
        for col in E.COLUMNS:
            x0, y0, x1, y1 = [v / 1000.0 for v in col]
            if min(b[3], x1) - max(b[0], x0) > 0.001 and min(b[4], y1) - max(b[1], y0) > 0.001:
                problems.append("%s: intersects structural column" % mark)
                break
    for mark in set(got) - {x["mark"] for x in expected}:
        problems.append("%s: unplanned detail" % mark)
    hatch = sp["hatches"][0]
    # an Opening has no Mark parameter in Revit 2027; the builder records the spec id beside the element id
    openings = [x for x in rb.get("hatches", []) if (x.get("mark") or x.get("spec_id")) == hatch["id"]]
    if len(openings) != 1:
        problems.append("%s: opening built %d times" % (hatch["id"], len(openings)))
    else:
        op = openings[0]
        box = op.get("bbox_mm", [])
        z = RS.LEVELS_Z[hatch["level"]]
        line = op.get("host_line_mm", [])
        host_matches = (len(line) == 2 and all(len(p) == 2 for p in line) and
                        all(abs(p[1] / 1000.0 - hatch["y"]) <= TOL for p in line) and
                        min(p[0] for p in line) / 1000.0 <= hatch["x0"] + TOL and
                        max(p[0] for p in line) / 1000.0 >= hatch["x1"] - TOL)
        # Revit 2027 names a wall opening's category "Rectangular Straight Wall Opening" and gives it no Mark or
        # Comments parameters (measured 2026-09-28); the closure is then carried by the shutter-box detail.
        tagless = op.get("mark") is None and op.get("comments") is None
        if (op.get("category") not in ("Openings", "Rectangular Straight Wall Opening") or
                (not tagless and op.get("comments") != hatch["closure"]) or
                op.get("host_wall") != op.get("expected_host_wall") or
                not host_matches or len(box) != 6 or max(abs(box[k] / 1000.0 - v) for k, v in
                                     ((0, hatch["x0"]), (3, hatch["x1"]), (2, z + hatch["sill"]),
                                      (5, z + hatch["head"]))) > TOL):
            problems.append("%s: wrong wall or opening extent" % hatch["id"])
    doors = [d for d in rb.get("doors", []) if set(d.get("rooms") or []) == {"kitchen", "dirty-kitchen"}]
    if len(doors) != 1 or doors[0].get("width") is None or abs(doors[0]["width"] - 1.2) > TOL:
        problems.append("kitchen/dirty-kitchen door: built width differs from 1.2 m")
    elif (doors[0].get("mark") != "kitchen-dirty-sliding" or doors[0].get("category") != "Doors" or
          "telescopic-pocket-3" not in (doors[0].get("comments") or "") or
          len(doors[0].get("bbox_mm") or []) != 6):
        problems.append("kitchen/dirty-kitchen door: Mark, category, Comments or bbox missing")
    suite = next(d for d in sp["doors"] if set(d["rooms"]) == {"parents-bed", "parents-dressing"})
    suite_rows = [d for d in rb.get("doors", []) if set(d.get("rooms") or []) == set(suite["rooms"])]
    if len(suite_rows) != 1:
        problems.append("parents' dressing door: built %d times" % len(suite_rows))
    else:
        door = suite_rows[0]
        point = door.get("point_mm") or []
        if (door.get("category") != "Doors" or len(door.get("bbox_mm") or []) != 6 or
                door.get("width") is None or abs(door["width"] - suite["width"]) > TOL or
                len(point) != 2 or abs(point[0] / 1000.0 - suite["x"]) > TOL):
            problems.append("parents' dressing door: category, box, width or x differs from spec")
    for window in (w for w in sp["windows"] if w.get("room") == "study-game"):
        mark = "window-study-game-%.3f-%.3f" % (window["x"], window["y"])
        rows = [w for w in rb.get("windows", []) if w.get("mark") == mark]
        if len(rows) != 1:
            problems.append("%s: built %d times" % (mark, len(rows)))
            continue
        row = rows[0]
        if (row.get("category") != "Windows" or len(row.get("bbox_mm") or []) != 6 or
                row.get("sill") is None or row.get("height") is None or row.get("width") is None or
                abs(row["sill"] - window["sill"]) > TOL or
                abs(row["height"] - window["height"]) > TOL or
                abs(row["width"] - window["width"]) > TOL):
            problems.append("%s: category, box or size differs from low-sill spec" % mark)
    new_furniture = {"library-cabinet-left", "library-cabinet-right", "library-daybed", "library-end-panel",
                     "cinema-desk", "cinema-desk#chair-1", "cinema-desk#chair-2", "dk-appliance-bank", "dk-fold",
                     "k-island", "stair-flight-store", "stair-landing-store", "store-shelves",
                     "pd-hang-1", "pd-hang-2"}
    furniture_spec = {x["mark"]: x for x in sp.get("furniture", [])}
    furniture_built = {x["mark"]: x for x in rb.get("furniture", [])}
    for mark in new_furniture:
        item, row = furniture_spec.get(mark), furniture_built.get(mark)
        if item is None or row is None:
            problems.append("%s: approved furniture missing from spec or read-back" % mark)
            continue
        if not row.get("comments"):
            problems.append("%s: Comments missing" % mark)
        world = row.get("bbox_mm") or []
        if len(world) != 6:
            problems.append("%s: measured world bbox missing" % mark)
        else:
            z = RS.LEVELS_Z[item["level"]]
            wanted = [item["envelope"][k] + (z if k in (2, 5) else 0) for k in range(6)]
            if max(abs(world[k] / 1000.0 - wanted[k]) for k in range(6)) > TOL + 1e-8:
                problems.append("%s: world bbox more than 5 mm from spec" % mark)
        b = row["bbox"]
        room = item["room"]
        rects = [lay["rooms"][rid]["rect"] for rid in F._cluster(lay, room)]
        if not F._inside((b[0], b[1], b[3], b[4]), rects):
            problems.append("%s: leaves room %s" % (mark, room))
        for col in E.COLUMNS:
            x0, y0, x1, y1 = [v / 1000.0 for v in col]
            if min(b[3], x1) - max(b[0], x0) > 0.001 and min(b[4], y1) - max(b[1], y0) > 0.001:
                problems.append("%s: intersects structural column" % mark)
                break
    return problems


def postcondition(spec_items, readback, lay=None):
    """Compare the model's read-back ([{mark, category, bbox: [x0, y0, z0, x1, y1, z1]}], z from the storey FFL)
    with the spec, then re-run every furniture check on the AS-BUILT footprints. Returns a list of problems."""
    probs = []
    got = {}
    for r in readback:
        got.setdefault(r["mark"], []).append(r)
    for s in spec_items:
        rs = got.get(s["mark"], [])
        if len(rs) != 1:
            probs.append("%s: built %d times" % (s["mark"], len(rs)))
            continue
        r = rs[0]
        dev = max(abs(a - b) for a, b in zip(r["bbox"], s["envelope"]))
        if dev > TOL:
            probs.append("%s: as built %s vs spec %s (%.0f mm off)" % (s["mark"], r["bbox"], s["envelope"],
                                                                       dev * 1000))
        if r.get("category") and r["category"] != s["category"]:
            probs.append("%s: category %s, spec %s" % (s["mark"], r["category"], s["category"]))
    for m in set(got) - {s["mark"] for s in spec_items}:
        probs.append("%s: in the model, not in the spec" % m)
    # the plan checks again, on what was built: each piece's as-built footprint replaces the authored one
    lay = lay or F.R.design("D1")
    built = []
    by = {r["mark"]: r for r in readback}
    for it in F.layout(lay):
        r = by.get(it["id"])
        if r is None:
            continue
        s = next(x for x in spec_items if x["mark"] == it["id"])
        fp = s["footprint"]
        b = r["bbox"]
        # the body's plan box is the envelope less the parts allowed outside the footprint (none in plan)
        w_, d_ = (b[3] - b[0], b[4] - b[1]) if it["rot"] in (0, 180) else (b[4] - b[1], b[3] - b[0])
        built.append(dict(it, cx=(b[0] + b[3]) / 2, cy=(b[1] + b[4]) / 2, w=w_, d=d_))
        if abs(fp[0] - b[0]) > TOL or abs(fp[2] - b[3]) > TOL or abs(fp[1] - b[1]) > TOL or abs(fp[3] - b[4]) > TOL:
            probs.append("%s: as-built plan box leaves its checked footprint" % it["id"])
    res = F.check(built, lay)
    for k, v in res.items():
        if v["status"] != "pass":
            probs += ["as built, %s: %s" % (k, p) for p in v["problems"]]
    return probs
