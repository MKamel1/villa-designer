"""Loader and validator for knowledge/landscape/site/*.json (schema in docs/lanes/LDS.md).

    python -m archpipe.landscape.site.check        # exit 0 = every layer valid

`load(name)` returns the parsed layer after validating it; `validate_all()` raises SiteDataError on the first problem.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from . import grid as G, model as M

DIR = Path(__file__).resolve().parents[4] / "knowledge" / "landscape" / "site"
SCHEMA = "lds-site/1"
NAMES = ("inventory", "sun", "privacy", "views", "wind", "checklist")
DAY_MAX_H = 14.5          # longest possible day at this latitude is ~13.9 h; anything above is a bug
WINDOW_H = {"summer_evening_17_20_standard_time": 3.0, "summer_evening_17_20_dst_clock": 3.0, "winter_day_10_15": 5.0}
WINDOW_PARENT = {"summer_evening_17_20_standard_time": "sun_hours_summer_solstice", "summer_evening_17_20_dst_clock": "sun_hours_summer_solstice",
                 "winter_day_10_15": "sun_hours_winter_solstice"}


class SiteDataError(ValueError):
    pass


def _need(cond, msg):
    if not cond:
        raise SiteDataError(msg)


def _grid_ok(d, name):
    _need(d.get("schema") == SCHEMA, "%s: schema %r != %r" % (name, d.get("schema"), SCHEMA))
    g = d.get("grid", {})
    for k in ("origin_m", "cell_m", "nx", "ny", "frame"):
        _need(g.get(k) == G.HEADER[k], "%s: grid %s %r differs from the shared grid %r" % (name, k, g.get(k), G.HEADER[k]))


def _arr(rows, name):
    _need(isinstance(rows, list) and len(rows) == G.NY and all(len(r) == G.NX for r in rows),
          "%s: layer is not %d rows x %d columns" % (name, G.NY, G.NX))
    return G.from_rows(rows)


def _gaps_ok(d, name):
    for g in d.get("gaps", []):
        _need(g.get("id") and g.get("text"), "%s: a gap without id/text" % name)


def validate(name, d, inv=None):
    _grid_ok(d, name)
    _gaps_ok(d, name)
    if name == "inventory":
        cls = np.array(d["cell_class"])
        _need(cls.shape == (G.NY, G.NX), "inventory: cell_class shape")
        _need(set(np.unique(cls)) <= set(M.CLASSES), "inventory: unknown class code")
        z = _arr(d["surface_z_m"], "inventory.surface_z_m")
        _need(np.array_equal(~np.isnan(z), np.isin(cls, M.ANALYSED)), "inventory: surface z must exist exactly on analysed classes")
        rects = [v["rect_m"] for v in d["zones"].values()]
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                _need(min(a[2], b[2]) - max(a[0], b[0]) <= 1e-6 or min(a[3], b[3]) - max(a[1], b[1]) <= 1e-6, "inventory: zones %r and %r overlap" % (a, b))
        for zn, v in d["zones"].items():
            x0, y0, x1, y1 = v["rect_m"]
            _need(abs(v["polygon_area_m2"] - (x1 - x0) * (y1 - y0)) < 0.02, "inventory: %s area disagrees with its rectangle" % zn)
            _need(y0 >= M.AXIS - 0.002, "inventory: %s lies on the sister plot (y < %.3f)" % (zn, M.AXIS))
        _need(d["gaps"], "inventory: gaps must be listed, never silently empty")
        return d
    inv = inv if inv is not None else json.loads((DIR / "inventory.json").read_text())
    analysed = np.isin(np.array(inv["cell_class"]), M.ANALYSED)

    def layer(rows, label):
        a = _arr(rows, label)
        _need(np.array_equal(~np.isnan(a), analysed), "%s: values must exist exactly on the inventory's analysed cells" % label)
        return a

    if name == "sun":
        loc = d["location"]
        _need("placeholder" in loc.get("placeholder_status", "").lower(), "sun: location must state the placeholder status loudly")
        L = {k: layer(v, "sun." + k) for k, v in d["layers"].items()}
        for k, a in L.items():
            _need(np.nanmin(a) >= 0 and np.nanmax(a) <= (WINDOW_H.get(k, DAY_MAX_H)) + 1e-9, "sun.%s: hours outside 0..%s" % (k, WINDOW_H.get(k, DAY_MAX_H)))
        for k, p in WINDOW_PARENT.items():
            _need(np.all(L[k][analysed] <= L[p][analysed] + 1e-9), "sun.%s exceeds its parent day total %s" % (k, p))
        _need(np.all(L["summer_evening_17_20_dst_clock"][analysed] >= 0), "sun: dst evening")
    elif name == "privacy":
        L = {k: layer(v, "privacy." + k) for k, v in d["layers"].items()}
        for k, a in L.items():
            _need(np.nanmin(a) >= 0, "privacy.%s negative count" % k)
        _need(np.nanmax(L["overlooking_eyes_street_standing"]) == 0, "privacy: the street fence is solid in the model; street viewers must see nothing")
        groups = [g for g in d["groups"] if g != "street"]
        for c in ("standing", "seated"):
            tot = sum(L["overlooking_eyes_%s_%s" % (g.replace("-", "_"), c)] for g in groups)
            _need(np.array_equal(np.nan_to_num(tot), np.nan_to_num(L["overlooking_eyes_any_" + c])), "privacy: 'any' is not the sum of its groups (%s)" % c)
        for b, v in d["boundaries"].items():
            top = v["existing_screen_top_z_m"]
            for s in v["segments"]:
                for c in ("standing", "seated"):
                    for z in s["required_top_z_" + c]:
                        # a sightline that is visible passes ABOVE an existing screen, so the screen it needs is higher than it
                        _need(z is None or top is None or z > top - 1e-6, "privacy.%s: a visible sightline crossing below the existing screen top %s" % (b, top))
    elif name == "views":
        n = layer(d["layers"]["rooms_seeing_cell"], "views.rooms_seeing_cell")
        per = [k for k in d["layers"] if k.startswith("seen_from_")]
        _need(np.nanmax(n) <= len(per), "views: more rooms see a cell than rooms exist")
        _need(np.array_equal(np.nan_to_num(sum(layer(d["layers"][k], k) for k in per)), np.nan_to_num(n)), "views: per-room layers do not sum to rooms_seeing_cell")
        for zn, picks in d["focal_point_candidates"].items():
            _need(zn in inv["zones"], "views: candidate in unknown zone %s" % zn)
    elif name == "wind":
        for sn, s in d["sets"].items():
            tot = sum(x["share_pct"] for x in s["sectors"]) + s["calm_pct"]
            _need(abs(tot - 100) < 0.6, "wind.%s: sector shares + calm = %.2f, not 100" % (sn, tot))
        _need(d["gaps"], "wind: the on-site gap must be listed")
    elif name == "checklist":
        _need(d["items"] and all(i["status"] in ("covered", "partial", "gap") for i in d["items"]), "checklist: bad status")
        _need(any(g["id"] == "C1" for g in d["gaps"]), "checklist: the unreachable Site Analysis book must be listed (C1)")
    return d


def load(name, directory: Path = DIR):
    d = json.loads((Path(directory) / (name + ".json")).read_text())
    inv = d if name == "inventory" else json.loads((Path(directory) / "inventory.json").read_text())
    return validate(name, d, inv)


def validate_all(directory: Path = DIR):
    return {n: load(n, directory) for n in NAMES}


if __name__ == "__main__":
    try:
        r = validate_all()
    except SiteDataError as e:
        print("INVALID:", e)
        sys.exit(1)
    print("LDS site layers valid:", ", ".join(r))
