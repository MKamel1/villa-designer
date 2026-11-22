"""Pass-6 asset update (reproducible): add the 3 atlas-built climber panels and the Fab olive, graded from the sheets rendered by
atlas_panel.py / olive_preview.py (looked at), build the preview sheets and recompute the affected species rows.
    python -I src/archpipe/landscape/plants/tools/assets_pass6.py /tmp/ldl7
Atlases are not plants: a climber panel is built from the scan's cut-out leaves ("atlas-built"). It counts as drawable for the
CLIMBER use only (rubric rider recorded in `grade_scope`), never as a scanned plant."""
import json, sys
from pathlib import Path
from PIL import Image

R = Path(__file__).resolve().parents[5]
P = R / "knowledge/landscape/plants"
SRC = Path(sys.argv[1])
fm = json.loads((P / "fab-manifest.json").read_text())["archives"]
doc = json.loads((P / "assets.json").read_text())
ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


def sheet(files, out):
    ims = [Image.open(SRC / f).convert("RGB").resize((500, 500)) for f in files]
    s = Image.new("RGB", (1000, 1000))
    for i, im in enumerate(ims):
        s.paste(im, ((i % 2) * 500, (i // 2) * 500))
    s.save(P / "asset-previews" / out, quality=88)


A = SRC / "atlas"
common = dict(licence="Fab Standard License", author="Quixel (Megascans) via Fab", storage="shared", quality_variant="4k", texture_res="4K",
              grade_scope="climber panel only (atlas-built, not a scanned plant)", construction="atlas-built", use="climber-panel")
NEW = []
for sid, arch, title, grade, fit, maps, rat, ex in (
    ("star_jasmine_trellis", "star_jasmine_pjycl2_4k", "Star Jasmine (atlas-built trellis panel)", "B", "species", ["trachelospermum_jasminoides"],
     "Looked at: a 1.2 m x 2.1 m timber-trellis panel (bottom 0.1 m bare) of ~900 real scanned jasmine leaf cut-outs (15 of the atlas's 20; the 5 brown dead leaves dropped by colour) on six vine stems. At 5 m it is a dense, glossy evergreen vine on a trellis; at 15 m a green wall panel with the trellis lost. The leaves come out a little yellow-green and rounder than star jasmine's dark pointed leaves, and there are no flowers, so it reads as 'evergreen twining climber', right for jasmine's use, not as a botanical portrait. Grade holds for the climber use only; it is atlas-built, not a scanned plant.",
     {}),
    ("creeping_fig_wall", "creeping_fig_ompjv0_4k", "Creeping Fig (atlas-built wall panel)", "B", "species", ["ficus_pumila"],
     "Looked at: the Megascans tileable scan of a fig-covered wall (0.85 m, repeated 1.4 x 2.5) as a 1.2 m x 2.1 m flat cladding on a plain plaster wall with an irregular noise edge. At 5 m it reads as a dark-green close-pressed climber clinging flat to a wall (creeping fig's habit), with some brown stem and bare patches; the edge is soft. At 15 m a dark green rectangle. It has no depth (a texture on a plane), so it is only for a wall seen face-on; grade holds for the climber use only; atlas-built.",
     {}),
    ("bougainvillea_dressing", "bougainvillea_flower_phfeffeh2_4k", "Bougainvillea flower dressing over a climber panel (atlas-built)", "C", "genus", [],
     "Looked at: ten real scanned bract/flower cut-outs (0.25 m scan), ~1700 instances in 16 clumps of magenta over the jasmine foliage panel. The colour mass reads as a flowering bougainvillea on a trellis at 5 m and at 15 m, but only the flowers are bougainvillea: the foliage underneath is the jasmine atlas, and the bracts are small and uniform. Not accepted as drawable (the foliage is a stand-in, a look-alike); usable as a flower dressing on a panel that is the right species, e.g. over a real bougainvillea leaf panel if one is built.",
     {"grade_if_foliage_were_the_species": "B"}),
):
    m = fm[arch]
    a = dict(id=f"fab_{sid}", source=m["listing_url"], title=title, preview=f"asset-previews/fab_{sid}.jpg", manifest_key=f"fab/{arch}",
             megascans_id=m["megascans_id"], grade=grade, species_fit=fit, maps_to=maps, leaf_type="atlas_cutouts",
             rationale=rat, candidate_for=maps[0] if maps else "bougainvillea_glabra", size_m=[1.2, 0.2, 2.1],
             builder="src/archpipe/landscape/plants/atlas_panel.py", **{**common, **ex})
    if sid == "creeping_fig_wall":
        a["size_m"] = [1.2, 0.01, 2.1]
    sheet([f"atlas/{sid}_d5_az0.png", f"atlas/{sid}_d5_az45.png", f"atlas/{sid}_d15_az0.png", f"atlas/{sid}_close.png"], f"fab_{sid}.jpg")
    NEW.append(a)
m = fm["olive_tree_source"]; st = json.loads((SRC / "olive/olive.stats.json").read_text())
sheet(["olive/olive_d5_az0.png", "olive/olive_d5_az90.png", "olive/olive_d15_az0.png", "olive/olive_d25_az0.png"], "fab_olive_tree_source.jpg")
NEW.append(dict(
    id="fab_olive_tree_source", source=m["listing_url"], licence="Fab Standard License", author=m["listing_seller"] or "Fab seller (see listing)",
    title="Olive Tree for Italian Panorama", preview="asset-previews/fab_olive_tree_source.jpg", storage="shared", manifest_key="fab/olive_tree_source",
    quality_variant="source_fbx", triangles=st["tris"], size_m=st["size_m"], grade="B", use="single", species_fit="species", maps_to=["olea_europaea"],
    leaf_type="alpha_cards", texture_res="PNG maps (Olive D/N/AORM, Tronco D, Olivio N)", candidate_for="olea_europaea",
    rationale="Looked at: a game-optimised olive (9,998 triangles, FBX in cm x 0.01 = 9.8 x 9.9 x 7.3 m; listing says about 7 m) with a gnarled, hollowed multi-stem trunk and drooping silver-grey narrow-leaf sprays. At 5 m the trunk and leaf sprays are unmistakably olive; at 15 m and 25 m the open, airy canopy and trunk read as an old olive. The canopy is sparse (cut-out cards, thin at the edges), so it looks bare against a bright sky. Sourced height 6.1-9.1 m (NCSU) vs 7.3 m tall: right scale. LIBRARY ASSET ONLY: the design rejected olive for the south garden on space.",
    library_only="the garden design rejected olive for the south garden on space (docs/decisions/garden-brief-2026-11-22.md)"))
have = {a["id"] for a in doc["assets"]}
doc["assets"] = [a for a in doc["assets"] if a["id"] not in {n["id"] for n in NEW}] + NEW
by = {a["id"]: a for a in doc["assets"]}
for r in doc["species"]:
    cands = [a for a in doc["assets"] if r["slug"] in a.get("maps_to", []) and a["species_fit"] in ("species", "genus")]
    if not cands:
        continue
    b = min(cands, key=lambda a: (ORDER[a["grade"]], a["species_fit"] != "species"))
    if ORDER[b["grade"]] < ORDER.get(r.get("grade"), 9) or r.get("best_asset") is None:
        r.update(best_asset=b["id"], grade=b["grade"], drawable="drawable" if b["grade"] in ("A", "B") else "not drawable yet")
doc["fab_source"] = doc["fab_source"].replace("27 Quixel Megascans archives", "27 Quixel Megascans archives plus pass 6 (3 atlases, 1 olive)")
(P / "assets.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
print(sum(1 for r in doc["species"] if r["drawable"] == "drawable"), "drawable")
