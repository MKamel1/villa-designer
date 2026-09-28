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
         "wall-units": "wall cupboards over the tall wall's counters"}

CATEGORY = {"base_run": "casework", "island": "casework", "tall_column": "casework", "pantry_shelving": "casework",
            "store_shelving": "casework", "folding_counter": "casework",
            "wc": "plumbing", "washbasin": "plumbing", "washbasin_double": "plumbing", "bath": "plumbing",
            "shower_walkin": "plumbing", "washer_dryer": "equipment", "screen": "equipment"}

TALL_MODULES = {"fridge", "oven", "tall"}
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
    if t in ("dining_6x", "desk"):
        return [("top", (x0, yb, H - 0.04, x1, yf, H))] + _legs(W, D, H - 0.04)
    if t == "island":                                               # carcass set back 300 mm under the seating side
        p = [("worktop", (x0, yb, H - 0.04, x1, yf, H)),
             ("plinth", (x0 + PLINTH_SET, yb + 0.3 + PLINTH_SET, 0, x1 - PLINTH_SET, yf - PLINTH_SET, PLINTH))]
        for kind, a, b in _local_modules(it):
            p.append((kind, (a, yb + 0.3, PLINTH, b, yf, H - 0.04)))
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
        p = [("back", (x0, yb, 0, x1, yb + 0.02, H)), ("side", (x0, yb, 0, x0 + 0.02, yf, H)),
             ("side", (x1 - 0.02, yb, 0, x1, yf, H))]
        n = max(2, int(H / 0.38))
        for k in range(n + 1):
            z = min(H - 0.02, k * H / n)
            p.append(("shelf", (x0 + 0.02, yb + 0.02, z, x1 - 0.02, yf, z + 0.02)))
        return p
    if t == "wardrobe" and str(it.get("room", "")).startswith("parents-dressing"):   # open hanging, no doors
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
    if it.get("chairs"):
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
        n = max(1, int(W // 0.9))
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
