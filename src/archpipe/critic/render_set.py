"""The final still-render set as data (knowledge/render-set/views.json) and its resolution to scene views.

`villa_render.py` is not ours (lane L6d), so the set is data: `resolve()` returns the `views` list that
`villa_render.write(views=...)` accepts; `scripts/villa_render_views.py --set` checks it. Pure geometry here:
no Blender, no GPU.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "knowledge/render-set/views.json"
DAY = "2026-10-15T10:30:00+03:00"
DUSK = "2026-10-15T18:35:00+03:00"
LZ = {"B": -3.0, "GF": 0.0}
MIN_INTERIOR_LENS = 24


def load(path: Path = DATA) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def problems(data: dict, rooms: dict) -> list[str]:
    """Static checks on the data: unique ids, purposes, 24 mm interiors, covers name real rooms."""
    out, seen = [], set()
    for e in data["views"]:
        vid = e["id"]
        if vid in seen:
            out.append(f"{vid}: duplicate id")
        seen.add(vid)
        if not e.get("purpose", "").strip():
            out.append(f"{vid}: no purpose")
        if not e.get("garden") and e.get("lens_mm", MIN_INTERIOR_LENS) < MIN_INTERIOR_LENS:
            out.append(f"{vid}: interior lens {e['lens_mm']} mm under {MIN_INTERIOR_LENS}")
        if not e.get("garden") and not e.get("covers"):
            out.append(f"{vid}: interior view covers no room")
        for r in e.get("covers", []):
            if r not in rooms:
                out.append(f"{vid}: covers unknown room {r}")
        if not e.get("reuse") and not e.get("room") and not e.get("camera"):
            out.append(f"{vid}: neither reuse, room nor camera")
    return out


def _in_wedge(cam: dict, x: float, y: float, reach: float = 14.0) -> bool:
    px, py = cam["position"][:2]
    tx, ty = cam["target"][:2]
    yaw = math.atan2(ty - py, tx - px)
    half = math.atan(cam["sensor_mm"] / 2 / cam["lens_mm"])
    d = math.hypot(x - px, y - py)
    if d > reach:
        return False
    if d < 1e-6:
        return True
    a = (math.atan2(y - py, x - px) - yaw + math.pi) % (2 * math.pi) - math.pi
    return abs(a) <= half


def coverage(views: list[dict], data: dict, rooms: dict) -> dict:
    """room -> list of interior view ids whose declared `covers` room lies inside the camera's field of view
    (any of the room's centre or corners, same storey, within 14 m). Declared-but-not-in-frame is dropped,
    so a wrong `covers` cannot claim a room."""
    by_id = {v["id"]: v for v in views}
    seen = {r: [] for r in rooms}
    for e in data["views"]:
        v = by_id.get(e["id"])
        if v is None or e.get("garden"):
            continue
        cam = v["camera"]
        if cam["lens_mm"] < MIN_INTERIOR_LENS:
            continue
        level = "B" if cam["position"][2] < -0.1 else "GF"
        for r in e.get("covers", []):
            x0, y0, x1, y1 = rooms[r]["rect"]
            if rooms[r]["level"] != level:
                continue
            pts = [((x0 + x1) / 2, (y0 + y1) / 2), (x0, y0), (x1, y0), (x0, y1), (x1, y1)]
            if any(_in_wedge(cam, *p) for p in pts):
                seen[r].append(e["id"])
    return seen


def resolve(data: dict, lay: dict, base_views: list[dict]) -> list[dict]:
    """Scene views for the set: `reuse` entries come from `base_views` (villa_render.VIEWS(lay)) unchanged;
    `room` entries get a 24 mm camera from render_views.choose (an unframed subject is an error: split the
    view, do not widen the lens)."""
    from ..concept import render_views as RV, revit_spec as RS
    from ..concept.authored_values import fill_defaults, override
    from ..concept.villa_render import sun_for_timestamp
    base = {v["id"]: v for v in base_views}
    sp = RS.build(lay)
    out = []
    for e in data["views"]:
        if e.get("reuse"):
            out.append(json.loads(json.dumps(base[e["id"]])))
            continue
        light = data["light"].get(e.get("light"), {})
        state = e["state"]
        layers = e.get("layers", light.get("layers", ["ambient", "task", "accent", "decorative"] if state != "day" else []))
        dimmers = dict(e.get("dimmers", light.get("dimmers", {})))
        if "camera" in e:      # authored standing point: x, y only; level and eye height from the entry
            room = None
            got = {"position": e["camera"]["position"], "target": e["camera"]["target"]}
            z = LZ[e["level"]] + 1.35
        else:
            room = e["room"]
            got = RV.choose(lay, room, e["subjects"], lens_mm=MIN_INTERIOR_LENS, sensor_mm=36, sp=sp, eye_m=1.35)
            if not got["subjects_in_frame"]:
                raise ValueError(f"{e['id']}: 24 mm cannot hold {e['subjects']} in {room}; split the view")
            z = LZ[lay["rooms"][room]["level"]] + 1.35
        c = {"position": got["position"] + [round(z, 3)], "target": got["target"] + [round(z, 3)],
             "lens_mm": MIN_INTERIOR_LENS, "sensor_mm": 36, "shift_x": 0.0, "shift_y": 0.0}
        c["overrides"] = [{"field": "position", "prior": None, "new": c["position"],
                           "reason": "room chooser positions the camera to include declared subjects"},
                          {"field": "target", "prior": None, "new": c["target"],
                           "reason": "room chooser aims the camera at declared subjects"}]
        if room is None:
            c["overrides"] = [{**o, "reason": "authored standing point (render-set data)"} for o in c["overrides"]]
            px, py = c["position"][:2]
            fill_defaults(c, {"reframed": False, "home_room": next(
                (k for k, r in lay["rooms"].items() if r["level"] == e["level"]
                 and r["rect"][0] <= px <= r["rect"][2] and r["rect"][1] <= py <= r["rect"][3]), None)})
        else:
            fill_defaults(c, {"home_room": room, "reframed": "chosen"})
        v = {"id": e["id"], "title": e["purpose"].split(" (")[0], "state": state,
             "when": DAY if state == "day" else DUSK, "camera": c, "resolution": [1920, 1280],
             "layers_on": layers, "dimmers": dimmers, "exposure": state, "subjects": e["subjects"],
             "samples": 1024, "room": room, "final_only": True, "seated": False,
             "set_purpose": e["purpose"]}
        if e.get("replaces"):
            v["caption_notes"] = [f"Replaces {e['replaces']} (camera reasons, L9P audit)."]
        import yaml
        loc = yaml.safe_load((ROOT / "spec/villa-site.yaml").read_text(encoding="utf-8"))["location"]
        v["sun"] = sun_for_timestamp(v["when"], loc)
        out.append(v)
    return out
