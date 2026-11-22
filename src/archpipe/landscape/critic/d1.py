"""The current D1 garden, enriched for the critics (read-only import of the garden code, like LDK's adapter).

Adds what the LDK snapshot drops: path rectangles, plant positions (`at`, `count` 1) and the plot's walls.
`python -m archpipe.landscape.critic.d1 --write` refreshes knowledge/landscape/critic/d1-layout.json
(the snapshot the tests use, so they need no model build)."""
from __future__ import annotations

import json
import sys

from .common import KNOW

SNAP = KNOW / "critic/d1-layout.json"


def build() -> dict:
    from ...concept import revit_spec as RS, villa_landscape as VL, villa_r11 as R
    from ..rules.current_garden import build as ldk_build
    lay = R.design("D1")
    _, _, _, plan = VL.review_candidate(RS.build(lay), lay)
    d = ldk_build()
    d["id"] = "D1-current"
    paths = {p["id"]: p for p in d["paths"]}
    for pid, r in plan["paths"].items():
        paths[pid]["rect"] = [round(v, 3) for v in r]
    groups = {g["id"]: g for g in d["planting_groups"]}
    for g in groups.values(): g["plants"] = []
    pal = {s["species"]: s for s in json.loads(VL.PALETTE.read_text())["species"]}
    for p in plan["plants"]:
        if p.get("planting_layer") == "tree" or "center" not in p: continue
        gid = next((g for g in ("bed-" + p["bed"], p["bed"]) if g in groups), None)
        if gid is None: continue
        hr = (pal.get(p["species"], {}).get("height") or {}).get("range_m")
        form = None if not hr else ("ground_cover" if hr[1] <= 0.5 else "shrub")
        groups[gid]["plants"].append({"species": p["species"], "form": form, "at": [round(p["center"][0], 3), round(p["center"][1], 3)], "spread_m": p["spread_m"]})
    inv = json.loads((KNOW / "site/inventory.json").read_text())
    d["walls"] = [{"id": e["id"], "rect": e["rect_m"], "height_m": e["z_m"][1] - e["z_m"][0]}
                  for e in inv["structure"] if e["id"].startswith(("fence-", "yard-wall"))]
    from . import site
    d["doors"] = [{"id": o["id"], "at": list(o["at"]), "faces": o["faces"], "room": o["room"], "width_m": o["width_m"]} for o in site.doors()]
    return d


def load() -> dict:
    return json.loads(SNAP.read_text(encoding="utf-8"))


if __name__ == "__main__":
    if "--write" in sys.argv:
        SNAP.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(SNAP)
