"""Historic and synthetic reproductions of the Revit-caught defects (knowledge/parity/frozen, tests/data, tests/fixtures).

Each `repro_*` returns a dict row for the recall table:
  {row, source: historic | historic-reconstructed | synthetic | control, check, expect, got, detail}
`got` is what the independent check said ('fail'/'pass'); expect is what it must say. Nothing here is tuned after a run.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from . import checks as C
from .geom import box_tris
from .world import Element, World, world_from_boxes

ROOT = Path(__file__).resolve().parents[3]
FROZEN = ROOT / "knowledge" / "parity" / "frozen"
READBACK_TOL = 0.010     # the Revit read-back reports wall tops to 10 mm (two decimals of a metre)


def _j(name):
    p = FROZEN / name
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text())


def mm(b):
    return tuple(v / 1000 for v in b)


def prism_xz(top, thick, y0, y1):
    """Closed solid under a polyline top profile [(x,z)...] extruded along y; per-segment convex trapezoids (own code)."""
    tr = []
    for (xa, za), (xb, zb) in zip(top, top[1:]):
        q = [(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)]
        qb = [(x, y, z - thick) for x, y, z in q]
        for quad in (q, qb[::-1]):                    # top and bottom strips
            tr += [[quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]]
        for i in range(4):                             # four side faces of the segment slab
            a, b = i, (i + 1) % 4
            if i in (0, 2):
                tr += [[q[a], q[b], qb[b]], [q[a], qb[b], qb[a]]]
    # end caps
    for (x, z) in (top[0], top[-1]):
        c = [(x, y0, z), (x, y1, z), (x, y1, z - thick), (x, y0, z - thick)]
        tr += [[c[0], c[1], c[2]], [c[0], c[2], c[3]]]
    return np.array(tr, float)


def _row(row, source, check, expect, findings, detail="", extra=None):
    fails = [f for f in findings if f.status == "fail"]
    got = "fail" if fails else "pass"
    r = dict(row=row, source=source, check=check, expect=expect, got=got, ok=(got == expect), detail=detail,
             n_fail=len(fails), findings=[f.message for f in fails][:12])
    if extra:
        r.update(extra)
    return r


# ---------------------------------------------------------------- D01 / D02 stairs vs kept structure
def _env_boxes(env):
    b = {}
    for c in env["columns"]:
        if c["base"].startswith("GF"):
            b[f"column-{c['id']}"] = mm(c["bbox"])
            x = list(mm(c["bbox"])); x[2] -= 3.0; x[5] -= 3.0     # client: same structure on every floor (LEARNINGS 600-627)
            b[f"column-{c['id']}-B"] = tuple(x)
    for s in env["shapes"]:
        if s["id"].startswith("beam-0"):
            b[s["id"]] = mm(s["bbox"])
    for f in env["floors"]:
        if f["id"] in ("slab-GF",):
            b[f["id"]] = mm(f["bbox"])
    return b


def stair_world(opt_name, round_to=None):
    env, spec = _j("env-readback.json"), _j("stairs-spec.json")
    parts = next(o for o in spec["options"] if o["name"] == opt_name)["parts"]
    boxes = {f"stair-{p['what']}": mm(p["box"]) for p in parts}
    boxes.update(_env_boxes(env))
    if round_to:
        boxes = {k: tuple(round(v / round_to) * round_to for v in b) for k, b in boxes.items()}
    return world_from_boxes(boxes, f"stairs:{opt_name}")


REVIT_MAP = {1615163: "beam-0-e1", 1615162: "beam-0-e0", 1615037: "slab-GF", 1590377: "column-1590377", 1614989: "column-1590377-B"}


def repro_d01():
    rb = _j("stairs-readback.json")
    rows = []
    for o in rb["options"]:
        w = stair_world(o["name"])
        fs = C.k01_stair_structure(w, tol=C.TOL_EXACT, src="RV1-TOL-EXACT")
        ours = {tuple(f.element_ids) for f in fs if f.status == "fail"}
        want = {("stair-" + i["part"], REVIT_MAP[i["id"]]) for i in o["intersections"] if i["id"] in REVIT_MAP}
        miss = sorted(want - ours - {(b, a) for a, b in ours})
        hit = len(want) - len(miss)
        rows.append(dict(row="D01", source="historic", check="K01", option=o["name"], revit_pairs=len(want),
                         caught=hit, missed=miss, extra=len({p for p in ours if p not in want and (p[1], p[0]) not in want}),
                         ok=(not miss), expect="fail" if want else "pass", got="fail" if ours else "pass"))
    return rows


def _d02_world(round_to=None):
    """The lengthwise U ('along the party wall'): its half landing started at x 3977 (LEARNINGS 697-706); the frozen spec is the
    corrected 3997, so the defect state is reconstructed by moving the landing's x0 back to 3977."""
    w = stair_world("U-stair along the party wall", round_to)
    for k, e in w.elements.items():
        if k.startswith("stair-") and "half landing" in k and "headroom" not in k:
            b = list(e.box); b[0] = 3.977 if not round_to else round(3.977 / round_to) * round_to
            w.elements[k] = Element(k, [(k, "box", None, None, box_tris(tuple(b)))])
    return w


def repro_d02():
    """Half landing at x 3977 against column 1590377's face at 3977.228 (sub-mm)."""
    w = _d02_world()
    ex = C.k01_stair_structure(w, tol=C.TOL_EXACT, src="RV1-TOL-EXACT")
    sc = C.k01_stair_structure(_d02_world(0.001))
    col = [f for f in ex if f.status == "fail" and "column" in f.subject]
    return dict(row="D02", source="historic-reconstructed", check="K01 exact", expect="fail", got="fail" if col else "pass", ok=bool(col),
                detail=("exact geometry: " + "; ".join(f.message[:150] for f in col[:2])) if col else "exact geometry found no column contact",
                scene_resolution=f"same boxes rounded to 1 mm (scene resolution), 2 mm tolerance: "
                                 f"{'FAIL' if any(f.status == 'fail' and 'column' in f.subject for f in sc) else 'PASS (not seen)'}")


# ---------------------------------------------------------------- D03 / D04 / D05 / D07 options-r7
def _r7():
    return _j("options-r7-readback.json")["options"], _j("options-r7-spec.json")


def r7_world(idx=0, prefix=False):
    """Walls (as built, z_top from the read-back), ramp, deck, doors/windows of an r7 option. `prefix` undoes the documented clamp."""
    ro, sp = _r7()
    o, s = ro[idx], sp[idx]
    boxes, tris = {}, {}
    base = {"B": -3.0, "GF": 0.0}
    for i, (rw, sw) in enumerate(zip(o["walls"], s["walls"])):
        lv = "B" if rw["level"].startswith("B") else "GF"
        t = sw["thickness"]
        z0 = base[lv]
        z1 = rw["z_top"]
        if prefix and lv == "B" and rw["x0"] == rw["x1"] and -23.6 < min(rw["y0"], rw["y1"]) and max(rw["y0"], rw["y1"]) < -20.5:
            z1 = z0 + 2.8                                   # LEARNINGS 659-683: cross walls skipped the clip: built 2.8 m tall
        if rw["x0"] == rw["x1"]:
            b = (rw["x0"] - t / 2, min(rw["y0"], rw["y1"]), z0, rw["x0"] + t / 2, max(rw["y0"], rw["y1"]), z1)
        else:
            b = (min(rw["x0"], rw["x1"]), rw["y0"] - t / 2, z0, max(rw["x0"], rw["x1"]), rw["y0"] + t / 2, z1)
        boxes[f"wall-{lv}-{i:02d}"] = b
    pk = s["parking2"]
    tris["slab-ramp"] = prism_xz([tuple(p) for p in pk["ramp"]["profile"]], pk["ramp"]["thick"], pk["ramp"]["y0"], pk["ramp"]["y1"])
    d = pk["deck"]
    boxes["slab-deck"] = (d["x0"], d["y0"], d["z_top"] - d["thick"], d["x1"], d["y1"], d["z_top"])
    w = world_from_boxes(boxes, f"r7:{o['id']}")
    for k, t in tris.items():
        w.elements[k] = Element(k, [(k, "box", None, None, t)])
    return w, o, s


def repro_d03():
    out = []
    for idx in (0, 1):
        w, o, s = r7_world(idx, prefix=True)
        f = C.k02_wall_slab(w, tol=READBACK_TOL)
        bad = [x for x in f if x.status == "fail"]
        out.append(dict(row="D03", source="historic-reconstructed", check="K02", option=o["id"], expect="fail",
                        got="fail" if bad else "pass", ok=bool(bad), n_walls_flagged=len({x.element_ids[0] for x in bad}),
                        learnings_count=8 if o["id"] == "P3" else 9,
                        detail="; ".join(sorted({f"{x.element_ids[0]} +{x.achieved:.0f} mm" for x in bad}))[:300]))
        w2, _, _ = r7_world(idx, prefix=False)
        f2 = C.k02_wall_slab(w2, tol=READBACK_TOL)
        out.append(dict(row="D03-fixed", source="control", check="K02", option=o["id"], expect="pass",
                        got="fail" if any(x.status == "fail" for x in f2) else "pass",
                        ok=not any(x.status == "fail" for x in f2),
                        detail="; ".join(x.message[:120] for x in f2 if x.status == "fail")[:240]))
    return out


def _wall_axis(o, rd):
    """'h' if the wall carrying the opening runs along x (found from the read-back walls), else 'v'."""
    best = None
    for w in o["walls"]:
        if w["x0"] == w["x1"]:
            d, ax = abs(w["x0"] - rd["x"]), "v"
            ok = min(w["y0"], w["y1"]) - 0.2 <= rd["y"] <= max(w["y0"], w["y1"]) + 0.2
        else:
            d, ax = abs(w["y0"] - rd["y"]), "h"
            ok = min(w["x0"], w["x1"]) - 0.2 <= rd["x"] <= max(w["x0"], w["x1"]) + 0.2
        if ok and (best is None or d < best[0]):
            best = (d, ax)
    return best[1] if best else "h"


def _door_model(o, s, prefix):
    m, boxes = {}, {}
    for i, (rd, sd) in enumerate(zip(o["doors"], s["doors"])):
        lv = "B" if rd["level"].startswith("B") else "GF"
        z0 = {"B": -3.0, "GF": 0.0}[lv]
        h = rd["height"]
        if prefix and rd["x"] == 3.125 and abs(rd["y"] + 22.096) < 0.01:
            h = 2.10                                         # the stock leaf before door_fit (LEARNINGS 659-683)
        ax = sd["span"][0] if sd.get("span") else _wall_axis(o, rd)
        wd = rd["width"]
        did = f"door-{lv}-{i:02d}"
        if ax == "h":
            boxes[did] = (rd["x"] - wd / 2, rd["y"] - 0.05, z0, rd["x"] + wd / 2, rd["y"] + 0.05, z0 + h)
        else:
            boxes[did] = (rd["x"] - 0.05, rd["y"] - wd / 2, z0, rd["x"] + 0.05, rd["y"] + wd / 2, z0 + h)
        m[did] = dict(id=did, kind="door", level=lv, host="", params={})
    return m, boxes


def repro_d04():
    out = []
    for prefix in (True, False):
        w, o, s = r7_world(0, prefix=prefix)
        m, boxes = _door_model(o, s, prefix)
        for k, b in boxes.items():
            w.elements[k] = Element(k, [(k, "box", None, None, box_tris(b))])
        w.elements.pop("slab-GF-ceiling", None)
        # the GF slab soffit above the basement, as built (-0.2) plus the ramp/deck above the store
        w.elements["slab-GF"] = Element("slab-GF", [("s", "box", None, None, box_tris((3.617, -29.9, -0.2, 22.6, -20.6, 0.0)))])
        f = C.k04_door_soffit(w, m)
        bad = [x for x in f if x.status == "fail"]
        out.append(dict(row="D04" if prefix else "D04-fixed", source="historic-reconstructed" if prefix else "control",
                        check="K04", expect="fail" if prefix else "pass", got="fail" if bad else "pass",
                        ok=bool(bad) == prefix, detail="; ".join(x.message[:140] for x in bad)[:300]))
    return out


def repro_d05():
    """Control: the frozen as-built openings (after the fix) stay clear of every kept column. Synthetic: the defect, an opening
    centred on the wall run over the real column 1590377 box, and a ramp door on the column at x 7.0 (LEARNINGS 708-713; the pre-fix
    openings were not frozen)."""
    env = _j("env-readback.json")
    out = []
    cols = {k: b for k, b in _env_boxes(env).items() if k.startswith("column") and not k.endswith("-B")}
    for idx in (0, 1):
        w, o, s = r7_world(idx)
        m, boxes = _door_model(o, s, False)
        for k, b in {**boxes, **{f"column{k[6:]}-B": v for k, v in _env_boxes(env).items() if k.startswith("column") and k.endswith("-B")}}.items():
            w.elements[k] = Element(k, [(k, "box", None, None, box_tris(b))])
        f = C.k03_opening_column(w, tol=C.TOL_EXACT, src="RV1-TOL-EXACT")
        out.append(dict(row="D05-asbuilt", source="control", check="K03", option=o["id"], expect="pass",
                        got="fail" if any(x.status == "fail" for x in f) else "pass", ok=not any(x.status == "fail" for x in f),
                        detail="; ".join(x.message[:120] for x in f if x.status == "fail")[:240] or f[0].message))
    c = cols["column-1590377"]            # 3617.228..3977.228 x, -28670.66..-28160.66 y, GF
    door = (c[0] + 0.05, c[1] + 0.05, c[2], c[0] + 0.85, c[1] + 0.15, c[2] + 2.1)       # a 0.8 m entrance door run over the column
    w = world_from_boxes({"column-1590377": c, "door-GF-entrance": door})
    f = C.k03_opening_column(w, tol=C.TOL_EXACT, src="RV1-TOL-EXACT")
    out.append(dict(row="D05", source="synthetic", check="K03", option="entrance over column 1590377", expect="fail",
                    got="fail" if any(x.status == "fail" for x in f) else "pass", ok=any(x.status == "fail" for x in f),
                    detail="; ".join(x.message[:120] for x in f if x.status == "fail")[:240]))
    return out


def repro_d07():
    ro, sp = _r7()
    env = _j("env-readback.json")
    out = []
    for idx in (0, 1):
        o, s = ro[idx], sp[idx]
        w = world_from_boxes({k: b for k, b in _env_boxes(env).items() if k.startswith("beam")})
        w.elements["slab-GF"] = Element("slab-GF", [("s", "box", None, None, box_tris((3.617, -31.3, -0.2, 22.6, -23.5, 0.0)))])
        d = s["parking2"]["deck"]
        w.elements["slab-deck"] = Element("slab-deck", [("s", "box", None, None, box_tris((d["x0"], d["y0"], d["z_top"] - d["thick"], d["x1"], d["y1"], d["z_top"])))])
        for n_, r_ in enumerate(s.get("roofs", [])):
            k_ = f"slab-infill-{n_}"
            w.elements[k_] = Element(k_, [("s", "box", None, None, box_tris((r_[0], r_[1], -0.35, r_[2], r_[3], 0.0)))])
        model = {}
        for rw, sw in zip(o["windows"], s["windows"]):
            if not sw.get("full_height"):
                continue
            ax, wd = (sw["span"][0] if sw.get("span") else _wall_axis(o, rw)), rw["width"]
            z0 = -3.0 + rw["sill"]
            k = f"window-B-{rw['room']}"
            # glass pane from the read-back's own width/sill/height
            b = ((rw["x"] - wd / 2, rw["y"] - 0.01, z0, rw["x"] + wd / 2, rw["y"] + 0.01, z0 + rw["height"]) if ax == "h"
                 else (rw["x"] - 0.01, rw["y"] - wd / 2, z0, rw["x"] + 0.01, rw["y"] + wd / 2, z0 + rw["height"]))
            w.elements[k] = Element(k, [(k, "box", "glass-clear", "glass-pane", box_tris(b))])
            model[k] = dict(id=k, kind="window", level="B", host="", params=dict(full_height=True))
        f = C.k06_glazing_to_beam(w, model, allow=0.15)
        bad = [x for x in f if x.status == "fail"]
        out.append(dict(row="D07", source="historic", check="K06", option=o["id"], expect="fail" if idx == 0 else "(info)",
                        got="fail" if bad else "pass", ok=bool(bad) if idx == 0 else True,
                        detail="; ".join(x.message[:150] for x in f)[:300]))
    return out


# ---------------------------------------------------------------- D08 fixtures through / off the ceiling (bedroom pre-fix meshes)
def repro_d08():
    d = json.loads((ROOT / "tests" / "data" / "bedroom-fixture-meshes-pre-fix.json").read_text())
    out = []
    ceiling = 2.700
    # LEARNINGS l0095: LT-02 spec 2000 mm; the family put the fitting at 2242.8 mm (242.8 mm offset). LT-03 and LT-05 are the same family.
    for lt, want in (("LT-02", 2.000), ("LT-03", 2.000), ("LT-05", 2.000)):
        parts = [p for p in d[lt] if p["geometry_role"] == "physical"]
        t = np.concatenate([_tri_from_vertices(p["vertices_mm"]) for p in parts])
        w = world_from_boxes({"slab-bedroom": (-1, -1, ceiling, 6, 6, ceiling + 0.1)})
        w.elements[f"lum-{lt}"] = Element(f"lum-{lt}", [(lt, "fixture", None, None, t)])
        # place the slab over the fitting
        c = t.reshape(-1, 3).mean(0)
        w.elements["slab-bedroom"] = Element("slab-bedroom", [("s", "box", None, None, box_tris((c[0] - 1, c[1] - 1, ceiling, c[0] + 1, c[1] + 1, ceiling + 0.1)))])
        m = {f"lum-{lt}": dict(id=f"lum-{lt}", kind="luminaire", level="GF", placement=[0, 0, want * 1000], params=dict(mount="pendant"))}
        f = C.k07_fixture_ceiling(w, m)
        bad = [x for x in f if x.status == "fail"]
        out.append(dict(row="D08", source="historic", check="K07", subject=lt, expect="fail", got="fail" if bad else "pass",
                        ok=bool(bad), detail="; ".join(x.message[:170] for x in f)[:260]))
    # LT-01 l0096: spec height pushed the cone shade top to 2717 mm through the 2700 mm ceiling (numbers from LEARNINGS, no mesh frozen)
    t = box_tris((0.0, 0.0, 2.250, 0.4, 0.4, 2.717))
    w = world_from_boxes({"slab-bedroom": (-1, -1, 2.700, 2, 2, 2.8)})
    w.elements["lum-LT-01"] = Element("lum-LT-01", [("LT-01", "fixture", None, None, t)])
    m = {"lum-LT-01": dict(id="lum-LT-01", kind="luminaire", level="GF", placement=[0, 0, 2250.0], params=dict(mount="pendant"))}
    f = C.k07_fixture_ceiling(w, m)
    out.append(dict(row="D08", source="synthetic", check="K07", subject="LT-01 shade top 2717 vs ceiling 2700 (LEARNINGS l0096)", expect="fail",
                    got="fail" if any(x.status == "fail" for x in f) else "pass", ok=any(x.status == "fail" for x in f),
                    detail="; ".join(x.message[:160] for x in f)[:240]))
    return out


def _tri_from_vertices(v):
    """A frozen vertex cloud (mm, no connectivity) as the 12 triangles of its bounding box, in metres."""
    a = np.array(v, float).reshape(-1, 3) / 1000
    return box_tris((*a.min(0), *a.max(0)))


# ---------------------------------------------------------------- D09 family bbox vs figure
def _inch(s):
    ft = re.findall(r"(\d+)'", s)
    ins = re.findall(r"(\d+(?:\.\d+)?)\"", s)
    return None


def parse_figures(type_name):
    """Dimensions in the Revit type name, e.g. 2'-4"W x 2'-8"D, 16" Dia, 2.5" x 4" x 6'-0" -> mm list ([] if none)."""
    out = []
    for tok in re.split(r"\s*x\s*", type_name):
        m = re.search(r"(?:(\d+)'-?)?\s*(\d+(?:\.\d+)?)?\"?", tok)
        ft = re.match(r"\s*(\d+)'(?:-(\d+(?:\.\d+)?)\")?", tok)
        if ft:
            out.append((int(ft.group(1)) * 12 + float(ft.group(2) or 0)) * 25.4)
            continue
        inch = re.match(r"\s*(?:Pendant\s*)?(\d+(?:\.\d+)?)\"", tok)
        if inch:
            out.append(float(inch.group(1)) * 25.4)
    return out


def repro_d09():
    f = _j_fixture("revit2027-place-families.json")
    items = []
    for fam in f["families"]:
        rb = fam["read_back"]
        figs = parse_figures(rb["type"])
        if not figs:
            continue
        items.append((fam["family_name"], rb["bbox_size_mm"], figs))
    res = C.k08_bbox_vs_figure_partial(items)
    bad = [x for x in res if x.status == "fail"]
    return dict(row="D09", source="historic", check="K08", expect="fail (families whose bbox does not match their stated size)",
                got="fail" if bad else "pass", ok=bool(bad), n_families=len(items), n_flagged=len(bad),
                detail="; ".join(x.message[:130] for x in res)[:500])


def _j_fixture(name):
    p = ROOT / "tests" / "fixtures" / name
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text())
