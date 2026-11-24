"""Generate knowledge/products/finishes/chosen.json: the client's chosen finish mix (2026-11-23).

Run: PYTHONPATH=src python scripts/build_chosen.py [--library-root DIR]
The file is generated and never hand-edited (tests/interior/test_chosen.py re-derives it).
"""
import argparse
import json
from pathlib import Path

from archpipe.interior import finishes, palette_scene

DECISION = "docs/decisions/interior-presentation-2026-11-22.md#client-palette-choice-2026-11-23-a-mix"
KITCHEN_ROOMS = ["kitchen", "kitchen-island", "dirty-kitchen"]
BASEMENT = ["lounge", "lounge-nook", "stair-b", "hall-b", "entry-b", "family", "kitchen", "kitchen-island", "dining",
            "dining-side", "living", "bar-alcove", "dirty-kitchen", "pantry", "store-ramp"]
GF = ["landing-gf", "corridor", "gallery-end", "study-game", "kids-a", "kids-b", "parents-bed", "parents-entry",
      "parents-dressing", "parents-dressing-ext"]
WET = ["guest-wc", "family-bath", "parents-ensuite"]
PARENTS = ["parents-bed", "parents-entry", "parents-dressing", "parents-dressing-ext", "parents-ensuite"]

# slot id -> (palette item id, scene materials it drives, applies_to, who decided)
HARD = {
    "floor-basement": ("C-floor-living", ["travertine"], dict(rooms=BASEMENT, note="every basement room except the cinema"), "client"),
    "floor-gf": ("C-floor-gf", ["oak-floor"], dict(rooms=GF), "lead-confirmed"),
    "floor-wet": ("C-floor-wet", ["marble-wet"], dict(rooms=WET, parts=["shower wet-floor"]), "lead-confirmed"),
    "wall-tile-wet": ("C-bath-tile", ["marble-bath", "marble-ensuite"], dict(rooms=WET, parts=["shower walls"]), "lead-confirmed"),
    "wall-paint-main": ("B-wall-paint", ["plaster-warm-white"], dict(rooms=BASEMENT + GF), "lead-confirmed (basement); lead decision (GF, see decisions)"),
    "wall-feature-parents": ("C-wall-paint", ["fin-wall-feature"], dict(rooms=["parents-bed"], parts=["the head wall behind the bed (whole wall face, door openings excepted)"]), "lead-confirmed"),
    "worktop": ("B-worktop", ["marble-white"], dict(rooms=KITCHEN_ROOMS, parts=["island worktop and waterfall ends", "base-run worktop", "laundry folding counter worktop"]), "client"),
    "backsplash": ("B-backsplash", [], dict(rooms=[]), "client"),
    "kitchen-front": ("B-kitchen-front", ["greige-lacquer"], dict(rooms=KITCHEN_ROOMS, parts=["base-run fronts", "dirty-kitchen tall units"]), "client"),
    "kitchen-joinery": ("B-joinery-light", ["fin-kitchen-joinery", "fin-kitchen-joinery-x"], dict(rooms=KITCHEN_ROOMS, parts=["island carcass"]), "client"),
    "joinery-timber": ("C-joinery-timber", ["walnut", "walnut-grain-x", "walnut-grain-y"], dict(rooms=BASEMENT + GF, parts=["TV wall, sideboards, bookcases, bedside tables, vanities, parents' wardrobes, stair treads and handrail"]), "client (parents' bedroom) / lead-confirmed (rest)"),
    "joinery-light": ("C-joinery-light", ["oak", "oak-grain-x"], dict(rooms=GF, parts=["wardrobes, desks, bed frames, headboard slats"]), "lead-confirmed"),
    "door": ("C-door", ["door-oak"], dict(rooms=BASEMENT + GF, parts=["interior door leaves"]), "lead-confirmed"),
}
NO_GEOMETRY = {"backsplash": "the design model holds no backsplash zone or element (only the K-SPLASH 600 mm clearance target, "
                              "and wall units exist only where a tall wall run is authored): reported, not invented"}
UNAPPLIED_SOFT = ("open-shelf", "wardrobe-garment")      # chosen C, but the scene has no such dressing assets to colour
GRAIN_AXIS = dict(palette_scene.GRAIN, **{"fin-kitchen-joinery": "z", "fin-kitchen-joinery-x": "x"})
SOFT_ROOMS = {"living-sofa": ["living"], "lounge-sofa": ["lounge"], "study-sofa": ["study-game"], "cinema-sofa": ["cinema"],
              "library-daybed": ["bar-alcove"], "parents-bed": ["parents-bed"], "living": ["living"], "lounge": ["lounge"],
              "parents-bedroom": ["parents-bed"]}

# room -> (floor slot, wall slot); retained rooms keep their design finish (reason recorded)
RETAINED = {
    "cinema": dict(floor="wool carpet 'rug' (design)", wall="taupe acoustic fabric (design)",
                   reason="a media room: acoustic fabric walls and carpet are the room's function, not a palette slot"),
    "stair-gf": dict(floor="no finish layer (stair void)", wall="shell structure paint (not in the FINISH table)",
                     reason="stair void and gallery edge: the shell carries the finish; unchanged by the client's choice"),
}


def rooms_table():
    t = {}
    for r in BASEMENT:
        t[r] = dict(zone="basement", floor="floor-basement", wall="wall-paint-main")
    for r in GF:
        t[r] = dict(zone="parents-suite" if r in PARENTS else "ground-floor", floor="floor-gf", wall="wall-paint-main")
    t["parents-bed"]["feature_wall"] = "wall-feature-parents"
    for r in WET:
        t[r] = dict(zone="wet-room", floor="floor-wet", wall="wall-tile-wet")
    for r, d in RETAINED.items():
        t[r] = dict(zone="basement" if r == "cinema" else "ground-floor", floor="retained", wall="retained", retained=d)
    return t


def build(library_root: Path) -> dict:
    pal = {p: finishes.load_palette(p) for p in "ABC"}
    items = {p: {i["id"]: i for i in pal[p]["items"]} for p in pal}
    colours = palette_scene.load_colours()
    slots = {}

    def add(sid, iid, scene, applies, who, **extra):
        pid = iid[0]
        item = items[pid][iid]
        s = dict(palette=pid, item_id=iid, group=item["group"], item=item, scene_materials=scene, applies_to=applies,
                 decided_by=who, **extra)
        if scene:
            spec = palette_scene.item_spec(item, library_root, colours)
            if "asset" in spec:
                # a grain axis only where the stand-in had one (veneers, planks); stone and tile have none: forcing "z" onto a floor
                # smeared the Gris Fleury image into stripes (v33 draft, 2026-11-23)
                if scene[0] in GRAIN_AXIS:
                    spec["grain_axis"] = GRAIN_AXIS[scene[0]]
            s["render"] = spec
            s["texture_scale"] = (dict(zip(("tile_m", "basis"), finishes.texture_scale_m(item))) if item.get("lookalike")
                                  else dict(tile_m=None, basis="flat colour (painted or laminated, no image)"))
        slots[sid] = s

    for sid, (iid, scene, applies, who) in HARD.items():
        add(sid, iid, scene, applies, who, **({"no_geometry": NO_GEOMETRY[sid]} if sid in NO_GEOMETRY else {}))
    for it in pal["C"]["items"]:
        if it["group"] != "soft":
            continue
        sid = it["id"][2:]
        if sid.startswith(UNAPPLIED_SOFT) or it["slot"] in UNAPPLIED_SOFT or sid.startswith("object") or sid.startswith("book") or sid.startswith("garment"):
            add(sid, it["id"], [], dict(rooms=[]), "client (palette C, 'other soft furnishings')",
                no_geometry="chosen as palette C; the scene has no open-shelf object, book or garment asset to colour")
            continue
        key = sid.split("-", 1)[1].rsplit("-", 1)[0] if sid[-1].isdigit() else sid.split("-", 1)[1]
        add(sid, it["id"], ["fin-" + sid], dict(rooms=SOFT_ROOMS[key], furniture=key), "client (palette C)")
    return dict(schema=1, decision=DECISION, decided="2026-11-23", palettes_used=["B", "C"],
                note="GENERATED by scripts/build_chosen.py from knowledge/products/finishes/{B,C}.json; no prices anywhere. "
                     "Look-alikes are CC0 render proxies, never the product.",
                slots=slots, rooms=rooms_table())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--library-root", type=Path, default=Path.home() / "archpipe/assets/library")
    ap.add_argument("--out", type=Path, default=finishes.PALETTE_DIR / "chosen.json")
    a = ap.parse_args()
    ch = build(a.library_root)
    a.out.write_text(json.dumps(ch, indent=1, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    print("wrote", a.out, len(ch["slots"]), "slots,", len(ch["rooms"]), "rooms")
