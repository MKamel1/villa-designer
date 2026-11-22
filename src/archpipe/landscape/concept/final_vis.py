"""Visualisation layout: the south garden reflected about the west line onto the sister plot. FOR VIEWING ONLY.

It is not our land and not our design: every element carries `visualisation_only: true`, ids are prefixed `vis-`, and nothing in the checks, schedules or quantities ever reads this file
(`assert_excluded` guards the main layout and `merge_for_view` is the only consumer, for images). The sister plot's real shape, house and boundary are unknown and are not drawn.
"""
from __future__ import annotations

import copy

from . import site as S
from .ty_core import A, B, KEYS

LINE_Y = S.SY0                                  # the west line (b = 0)
SOUTH_KEYS = ("zones", "paved_areas", "planting_groups", "seating", "tables", "features", "trees", "paths", "canopies", "obstacles", "seatwalls")
LABEL = "VISUALISATION ONLY: sister plot, not our land or design"


def fy(y):
    return round(2 * LINE_Y - y, 3)


def _rect(r):
    return [r[0], fy(r[3]), r[2], fy(r[1])]


def _mirror(o):
    o = copy.deepcopy(o)
    if o.get("id"):
        o["id"] = "vis-" + o["id"]
    for k in ("rect", "bbox"):
        if k in o and isinstance(o[k], list) and len(o[k]) == 4:
            o[k] = _rect(o[k])
    if "center" in o:
        o["center"] = [o["center"][0], fy(o["center"][1])]
    if "polyline" in o:
        o["polyline"] = [[p[0], fy(p[1])] for p in o["polyline"]]
    if "at" in o and isinstance(o["at"], list):
        o["at"] = [o["at"][0], fy(o["at"][1])]
    if "plants" in o:
        o["plants"] = [{**p, "at": [p["at"][0], fy(p["at"][1])], "visualisation_only": True} for p in o["plants"]]
    if "zone" in o and isinstance(o["zone"], str):
        o["zone"] = "vis-" + o["zone"]
    o["visualisation_only"] = True
    return o


def in_south(o):
    for k in ("rect", "center", "at"):
        v = o.get(k)
        if v is None:
            continue
        x, y = (v[0], v[1]) if k != "rect" else ((v[0] + v[2]) / 2, (v[1] + v[3]) / 2)
        return x >= S.SX0 - 1e-6 and LINE_Y - 1e-6 <= y <= LINE_Y + B + 1e-6
    return o.get("polyline") is not None and all(p[0] >= S.SX0 and p[1] >= LINE_Y for p in o["polyline"])


def mirror(L):
    """The mirror image of the south-garden contents of `L`, tagged and renamed. The shared fire pit and the west screen sit ON the line and are not copied."""
    V = {k: [] for k in KEYS}
    for k in SOUTH_KEYS:
        for o in L.get(k, []):
            if k == "features" and o.get("kind") == "firepit":
                continue
            if k == "obstacles" and not o["id"].startswith("pot"):
                continue
            if k == "seatwalls" or in_south(o):
                V[k].append(_mirror(o))
    # one labelled zone over the mirrored garden so the label appears in every drawing that shows it
    V["zones"].append({"id": "vis-label-zone", "use": "other", "rect": [S.SX0, fy(LINE_Y + B), S.SX0 + A, LINE_Y], "surface": "paving", "enclosure_height_m": 4.0,
                       "label": LABEL, "visualisation_only": True})
    out = {"schema": "landscape-layout/1", "frame": "model metres", "visualisation_only": True, "label": LABEL, "buildings": [], "meta": {"visualisation_only": True, "reflected_about": "west line y=%.3f" % LINE_Y, "note": LABEL}}
    out.update(V)
    return out


def tagged_everywhere(V):
    """True when every dict element in every list of the visualisation layout carries visualisation_only: true."""
    return all(o.get("visualisation_only") is True for k in KEYS for o in V.get(k, []))


def has_vis(L):
    """Recursive: does the layout contain any visualisation_only flag or vis- id? (the main layout must not)"""
    def walk(x):
        if isinstance(x, dict):
            if x.get("visualisation_only") or str(x.get("id", "")).startswith("vis-"):
                return True
            return any(walk(v) for v in x.values())
        if isinstance(x, list):
            return any(walk(v) for v in x)
        return False
    return walk(L)


def assert_excluded(L):
    if has_vis(L):
        raise AssertionError("visualisation elements leaked into the design layout")


def merge_for_view(L, V):
    """Main design + visualisation for IMAGES ONLY. Never pass the result to checks, schedules or quantities."""
    M = copy.deepcopy(L)
    for k in KEYS:
        M[k] = M.get(k, []) + V.get(k, [])
    M["meta"] = dict(M.get("meta", {}), view_includes_visualisation_only=True)
    return M
