"""Adapter: an LDG concept package (south/north/east zone layouts + planting plans) -> one `landscape-layout/1` for
`plan_png`, `massing_png` and `critique`. Plant instances keep the positions LDG placed them at (`at`, spread from LDL)."""
from __future__ import annotations

KEYS = ("zones", "paths", "paved_areas", "tables", "seating", "planting_groups", "trees", "features", "obstacles", "buildings", "walls", "screens", "canopies", "doors")


def layout_of_package(pk: dict, zones=("south", "north", "east")) -> dict:
    """Pergolas come from LDG's `_cover` rects (south cover + the north quiet corner), which are not in the zone layouts."""
    from ..concept.assemble import covers_model
    out = {"schema": "landscape-layout/1", "id": f"concept-{pk.get('idea', '?')}"}
    for k in KEYS: out[k] = []
    for z in zones:
        L = pk[z]["layout"]
        for k in KEYS:
            out[k] += [dict(i) if isinstance(i, dict) else i for i in L.get(k, [])]
        beds = pk[z]["plan"]["beds"]
        for g in out["planting_groups"]:
            if g["id"] in beds:
                g["plants"] = [{"species": i["species"], "count": 1, "at": i["positions"][0], "drift": i.get("drift"), "form": f}
                               for i in beds[g["id"]]["instances"] for f in [{"canopy": "large_tree", "understorey": "small_tree", "climber": "shrub", "shrub": "shrub"}.get(i["layer"], "ground_cover")] if i.get("positions")]
    pergolas = covers_model(pk["south"]["cand"]) + ([pk["north"]["cand"]["quiet"]] if pk["north"]["cand"].get("quiet") else [])
    for r in pergolas:
        out["canopies"].append({"id": f"pergola-{len(out['canopies'])}", "kind": "pergola", "rect": list(r), "height_m": 3.0, "shade_fraction": 0.5})
    return out
