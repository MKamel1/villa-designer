"""Write a per-site D1 mounting inventory from the exported scene.

The scene has material names but generally no finish build-up thickness.
Consequently an unknown finished-face error remains blank, never zero.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "out/villa/render-d1/scene.json"
OUTPUT = ROOT / "docs/c4-mounting-inventory.csv"

SITE_KINDS = {
    "handrail", "rail-bracket", "wall-plate", "stair-stringer",
    "wall-panel", "downlight-trim", "wall-marker", "light-diffuser",
    "lamp-housing", "lamp-cord", "lamp-wire", "lamp-arm", "lamp-head",
    "rain-head", "riser-rail", "mirror-panel", "extract-valve",
    "fan-grille", "screen", "tv_unit", "wc", "washbasin", "shelf",
    "trellis", "climber", "climber-branch", "curtain-track", "drain",
    "hanging-rail", "joinery_end_panel", "led-strip", "shower-head",
    "light-lens", "light-bulb", "lamp-joint", "appliance-housing",
}


def bounds(mesh):
    points = [v for face in mesh["faces"] for v in face]
    if not points:
        return None
    return tuple((min(p[a] for p in points), max(p[a] for p in points)) for a in range(3))


def row(mesh):
    kind = mesh.get("part_kind") or ""
    mid = mesh["id"]
    b = bounds(mesh)
    state = "no declared finished host face"
    datum = ""
    note = "Finish build-up thickness and host binding absent; finished-face error cannot be measured."
    if kind == "handrail" and mid == "detail-stair-wall-handrail" and b:
        datum = round((b[1][0] - (-28.471)) * 1000, 1)
        state = "modeled plaster face known; host binding absent"
        note = "Nearest rail face projects 85 mm from the stated plaster face; historic buried state was corrected by an ad-hoc offset."
    elif kind == "downlight-trim":
        state = "finished ceiling height used; housing not exported"
        note = "Trim location can be checked against ceiling; housing depth and clear void are absent from this scene."
    elif kind == "extract-valve":
        datum = 3.0
        state = "finished ceiling height used; fixing depth implicit"
        note = "Top is 3 mm below the ceiling; body projects 3 to 12 mm into room."
    elif kind == "fan-grille":
        datum = 0.0
        state = "structural exterior face used"
        note = "Grille reaches modeled exterior face; exterior finish build-up is not stated."
    elif kind == "wall-marker":
        datum = 1.0
        state = "structural wall face used"
        note = "Visible marker plane is 1 mm proud of modeled wall; finish build-up is not stated."
    elif kind == "rain-head" and mid.endswith("-drop"):
        datum = 0.0
        state = "finished ceiling height used"
        note = "Drop reaches modeled finished ceiling; head elevation remains authored."
    elif kind == "rail-bracket" and mid.startswith("detail-") and "hand-shower" in mid:
        state = "structural wall bounds used"
        note = "Bracket endpoint is placed 20 mm inside the nearest structural wall bound; finish build-up is absent."
    elif kind == "trellis":
        state = "fixed world coordinates; host undeclared"
        note = "Boundary wall face and cladding build-up are not bound to the trellis."
    elif kind == "climber" or kind == "climber-branch":
        state = "derived from trellis; trellis host undeclared"
        note = "Climber follows the trellis frame, whose wall fixing has no declared finished face."
    elif kind == "mirror-panel":
        state = "derived from basin back; wall host undeclared"
        note = "Mirror back follows basin footprint, without a bound finished wall face."
    elif kind in {"wc", "washbasin", "screen", "tv_unit"}:
        state = "furnished item envelope; wall host undeclared"
        note = "Footprint is authored against clear room rectangle; finish thickness and fixing depth are not recorded."
    return {"site_id": mid, "room": mesh.get("room") or "", "part_kind": kind,
            "face_state": state, "datum_gap_mm": datum, "finished_face_error_mm": "",
            "measurement_note": note}


def main():
    scene = json.loads(SCENE.read_text(encoding="utf-8"))
    sites = [row(m) for m in scene["meshes"]
             if m.get("part_kind") in SITE_KINDS or m["id"].startswith("furn-")]
    # Art is often an imported prop/model rather than a procedural mesh.
    for group in ("props", "models"):
        for item in scene.get(group, []):
            label = (item.get("id", "") + " " + item.get("label", "")).lower()
            if "art" in label or "picture" in label or "frame" in label:
                sites.append({"site_id": item.get("id", ""), "room": item.get("room", ""),
                              "part_kind": "wall-art asset", "face_state": "asset placement; host undeclared",
                              "datum_gap_mm": "", "finished_face_error_mm": "",
                              "measurement_note": "Asset has no declared finished wall host or fixing plane."})
    sites.sort(key=lambda r: r["site_id"])
    with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(sites[0]))
        writer.writeheader()
        writer.writerows(sites)
    print(f"{len(sites)} scene components inventoried in {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
