import copy
import unittest

from archpipe.landscape.plants import library as L
import json
import tempfile
from pathlib import Path

from archpipe.landscape.plants.assets import gltf_untextured_share, load_assets, validate_assets, validate_manifest


class AssetTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.slugs = load_assets(), list(L.load_species())

    def test_shipped_table_valid(self):
        self.assertEqual(validate_assets(self.doc, self.slugs), [])

    def test_every_species_has_a_row_and_unmatched_ones_are_not_drawable(self):
        rows = {r["slug"]: r for r in self.doc["species"]}
        self.assertEqual(set(rows), set(self.slugs))
        self.assertGreater(sum(r["drawable"] == "not drawable yet" for r in rows.values()), 50)

    def test_drawable_without_a_good_asset_fails(self):
        d = copy.deepcopy(self.doc)
        row = next(r for r in d["species"] if r["drawable"] == "not drawable yet")
        row["drawable"] = "drawable"
        self.assertTrue(any("without a grade A/B" in e for e in validate_assets(d, self.slugs)))

    def test_good_asset_marked_not_drawable_fails(self):
        d = copy.deepcopy(self.doc)
        next(r for r in d["species"] if r["slug"] == "jacaranda_mimosifolia")["drawable"] = "not drawable yet"
        self.assertTrue(any("marked not drawable" in e for e in validate_assets(d, self.slugs)))

    def test_grade_c_asset_never_makes_a_species_drawable(self):
        rows = {r["slug"]: r for r in self.doc["species"]}
        self.assertEqual(rows["olea_europaea"]["grade"], "C")
        self.assertEqual(rows["olea_europaea"]["drawable"], "not drawable yet")

    def test_look_alike_cannot_map_to_species_and_missing_preview_fails(self):
        d = copy.deepcopy(self.doc)
        a = next(x for x in d["assets"] if x["species_fit"] == "look-alike")
        a["maps_to"] = ["olea_europaea"]; a["preview"] = "asset-previews/nope.jpg"
        e = " ".join(validate_assets(d, self.slugs))
        self.assertIn("look-alike", e); self.assertIn("preview file missing", e)

    def test_grade_without_looked_at_fails(self):
        d = copy.deepcopy(self.doc)
        d["assets"][0]["rationale"] = "fine"
        self.assertTrue(any("Looked at" in e for e in validate_assets(d, self.slugs)))


class PassTwoGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.slugs = load_assets(), list(L.load_species())

    def test_misnamed_jacaranda_is_a_look_alike_that_maps_to_nothing(self):
        a = next(x for x in self.doc["assets"] if x["id"] == "jacaranda_tree")
        self.assertEqual(a["misnamed_as"], "jacaranda_mimosifolia"); self.assertEqual(a["maps_to"], [])
        d = copy.deepcopy(self.doc); next(x for x in d["assets"] if x["id"] == "jacaranda_tree")["maps_to"] = ["jacaranda_mimosifolia"]
        self.assertTrue(any("misnamed" in e for e in validate_assets(d, self.slugs)))

    def test_untextured_asset_above_grade_d_fails(self):
        d = copy.deepcopy(self.doc)
        a = next(x for x in d["assets"] if x["id"] == "skf_fd421074"); self.assertEqual(a["grade"], "D")
        a["grade"] = "B"
        self.assertTrue(any("renders white" in e for e in validate_assets(d, self.slugs)))

    def test_untextured_share_measured_from_gltf(self):
        with tempfile.TemporaryDirectory() as t:
            bare, tex = Path(t, "bare.gltf"), Path(t, "tex.gltf")
            bare.write_text(json.dumps({"materials": [{"pbrMetallicRoughness": {"metallicFactor": 0}}]}))
            tex.write_text(json.dumps({"materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}]}))
            self.assertEqual(gltf_untextured_share(bare), 1.0)
            self.assertEqual(gltf_untextured_share(tex), 0.0)   # negative: a textured asset is not flagged
            sg = Path(t, "sg.gltf")   # spec-gloss export (PlantCatalog, Treeit): colour lives in the extension
            sg.write_text(json.dumps({"materials": [
                {"extensions": {"KHR_materials_pbrSpecularGlossiness": {"diffuseTexture": {"index": 0}}}},
                {"extensions": {"KHR_materials_pbrSpecularGlossiness": {"diffuseFactor": [0.0, 0.1, 0.0, 1.0]}}}]}))
            self.assertEqual(gltf_untextured_share(sg), 0.0)
            bare_sg = Path(t, "bsg.gltf")
            bare_sg.write_text(json.dumps({"materials": [{"extensions": {"KHR_materials_pbrSpecularGlossiness": {"glossinessFactor": 0.4}}}]}))
            self.assertEqual(gltf_untextured_share(bare_sg), 1.0)
        banana = Path.home() / "archpipe/library/sketchfab/fd4210743fb644d0a2c5452637ffc5d4/gltf/scene.gltf"
        if banana.is_file():
            self.assertEqual(gltf_untextured_share(banana), 1.0)

    def test_non_free_licence_fails(self):
        d = copy.deepcopy(self.doc); d["assets"][0]["licence"] = "Royalty Free Store License"
        self.assertTrue(any("not a free licence" in e for e in validate_assets(d, self.slugs)))

    def test_shared_assets_are_pinned_in_the_manifest(self):
        m = json.loads((L.DATA / "asset-manifest.json").read_text(encoding="utf-8"))
        fab = json.loads((L.DATA / "fab-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_manifest(self.doc, m, fab), [])
        m2 = copy.deepcopy(m); k = next(iter(m2["assets"])); m2["assets"][k][0]["sha256"] = "abc"
        self.assertTrue(validate_manifest(self.doc, m2, fab))
        self.assertTrue(validate_manifest(self.doc, {"assets": {}}, fab))

    def test_manifest_hashes_match_the_files_when_the_store_exists(self):
        import hashlib
        base = Path.home() / "archpipe/shared/assets/user/landscape"
        if not (base / "polyhaven").is_dir():
            self.skipTest("shared asset store not on this machine")
        m = json.loads((L.DATA / "asset-manifest.json").read_text(encoding="utf-8"))
        for key, files in m["assets"].items():
            if not (base / key).is_dir():
                continue
            for f in files:
                self.assertEqual(hashlib.sha256((base / key / f["file"]).read_bytes()).hexdigest(), f["sha256"], f["file"])

    def test_ixora_asset_no_longer_maps_to_a_species(self):
        self.assertEqual(next(x for x in self.doc["assets"] if x["id"] == "sf_ixora")["maps_to"], [])
    def test_gazania_is_drawable_only_via_a_drift_test(self):
        a = next(x for x in self.doc["assets"] if x["id"] == "ph_flower_gazania")
        self.assertIn("DRIFT TEST", a["rationale"]); self.assertTrue((L.DATA / a["drift_preview"]).is_file())

    def test_placed_assets_match_sourced_height_and_inconsistent_scale_fails(self):
        sp = L.load_species()
        placed = [a for a in self.doc["assets"] if "placement_scale" in a]
        self.assertGreaterEqual(len(placed), 2)
        for a in placed:
            h = sp[a["maps_to"][0]]["attributes"]["height_m"]["value"]
            self.assertTrue(h["min"] <= a["placed_height_m"] <= h["max"], a["id"])
        d = copy.deepcopy(self.doc)
        next(x for x in d["assets"] if x["id"] == "skf3_d0248242")["placement_scale"] = 1.0
        self.assertTrue(any("placed_height_m" in e for e in validate_assets(d, self.slugs)))

    def test_papyrus_is_drawable_only_after_placement_scale(self):
        row = next(r for r in self.doc["species"] if r["slug"] == "cyperus_papyrus")
        self.assertEqual((row["grade"], row["drawable"]), ("B", "drawable"))
        self.assertIn("placement scale", next(x for x in self.doc["assets"] if x["id"] == "skf3_d0248242")["rationale"])


if __name__ == "__main__":
    unittest.main()


class FabAssets(unittest.TestCase):
    """LDL pass 5: the 27 Quixel Megascans archives from Fab (Fab Standard License, binaries outside git)."""

    @classmethod
    def setUpClass(cls):
        cls.doc, cls.slugs = load_assets(), list(L.load_species())
        cls.fab = json.loads((L.DATA / "fab-manifest.json").read_text(encoding="utf-8"))
        cls.assets = [a for a in cls.doc["assets"] if a["id"].startswith("fab_")]

    def test_every_archive_is_an_asset_and_pinned(self):
        self.assertEqual(len(self.assets), 27)
        self.assertEqual({a["manifest_key"][4:] for a in self.assets}, set(self.fab["archives"]))
        self.assertFalse([e for e in validate_manifest(self.doc, {"assets": {}}, self.fab) if e.startswith("fab_")])
        self.assertTrue(all("Fab Standard License" in a["licence_quote"] and "Resell or redistribute" in a["licence_quote"] for a in self.fab["archives"].values()))

    def test_unpinned_fab_asset_fails(self):
        f = copy.deepcopy(self.fab); k = next(iter(f["archives"])); f["archives"][k]["files"][next(iter(f["archives"][k]["files"]))] = "abc"
        self.assertTrue(any("64-hex" in e for e in validate_manifest(self.doc, {"assets": {}}, f)))
        f = copy.deepcopy(self.fab); del f["archives"][k]
        self.assertTrue(any("no fab-manifest entry" in e for e in validate_manifest(self.doc, {"assets": {}}, f)))

    def test_fab_hashes_match_the_store_when_present(self):
        import hashlib
        base = Path.home() / "archpipe/shared/assets/user/landscape/fab"
        if not (base / "unzipped").is_dir():
            self.skipTest("fab store not on this machine")
        for stem, ar in self.fab["archives"].items():
            for name in list(ar["files"])[:3]:                       # three files per archive keeps this under a few seconds
                self.assertEqual(hashlib.sha256((base / "unzipped" / stem / name).read_bytes()).hexdigest(), ar["files"][name], f"{stem}/{name}")

    def test_wrong_scale_scan_cannot_be_graded_b(self):
        rows = {r["slug"]: r for r in self.doc["species"]}
        for slug in ("rosmarinus_officinalis", "livistona_chinensis"):          # 0.35 m scan vs 1.5 m sourced; 1.5 m juvenile vs 8-12 m
            self.assertEqual((rows[slug]["grade"], rows[slug]["drawable"]), ("C", "not drawable yet"), slug)
        d = copy.deepcopy(self.doc)
        next(a for a in d["assets"] if a["id"] == "fab_rosemary_vgvoacmia_high")["grade"] = "B"
        self.assertTrue(any("wrong scale" in e for e in validate_assets(d, self.slugs)))

    def test_new_species_are_drawable_only_with_an_ab_asset(self):
        rows = {r["slug"]: r for r in self.doc["species"]}
        for slug in ("hedychium_coronarium", "zamia_furfuracea", "salvia_officinalis", "hedera_helix", "aloe_vera", "aspidistra_elatior", "colocasia_esculenta"):
            self.assertEqual(rows[slug]["drawable"], "drawable", slug)
            self.assertTrue(rows[slug]["best_asset"].startswith(("fab_", "skf", "sf_", "ph_")))
        for slug in ("vinca_minor", "epipremnum_aureum", "zingiber_officinale", "canna_x_generalis"):
            self.assertEqual(rows[slug]["drawable"], "not drawable yet", slug)

    def test_lawn_is_a_surface_and_maps_to_no_species(self):
        lawns = [a for a in self.assets if a["use"] == "surface"]
        self.assertEqual(len(lawns), 5)
        for a in lawns:
            self.assertEqual((a["maps_to"], a["species_fit"]), ([], "none"))
            self.assertIn("DRIFT TEST", a["rationale"])

    def test_every_fab_sheet_was_looked_at_and_high_beats_raw_on_cost(self):
        for a in self.assets:
            self.assertTrue(a["rationale"].startswith("Looked at:") and (L.DATA / a["preview"]).is_file(), a["id"])
        by = {a["id"]: a for a in self.assets}
        for stem in ("oregano_umkhceeia", "rosemary_vgvoacmia", "aloe_vera_ve4tbbrha"):
            hi, raw = by[f"fab_{stem}_high"], by[f"fab_{stem}_raw"]
            self.assertLessEqual(hi["triangles"], raw["triangles"] * 1.05)
            self.assertLess(hi["render_seconds"]["single_sheet"], raw["render_seconds"]["single_sheet"])

    def test_megascans_single_channel_maps_are_red_only_and_the_importer_reads_the_red_channel(self):
        """Defect (pass 5): Opacity/Roughness/Gloss/AO JPGs keep their data in the RED channel (G, B ~ 0). Read as colour
        (luminance) the leaves came out ~20 % opaque and ghostly. Guard: measure the real archive, and require the importer
        to route those maps through red()."""
        import re
        src = (Path(__file__).resolve().parents[3] / "src/archpipe/landscape/plants/megascans_mat.py").read_text(encoding="utf-8")
        for name in ("Opacity", "Roughness", "Gloss", "Displacement"):
            self.assertRegex(src, r"red\(nt, \w+\)", name)
        self.assertNotRegex(src, r'nt\.links\.new\(o\.outputs\["Color"\], mo\.inputs\[0\]\)')      # the pre-fix wiring
        d = Path.home() / "archpipe/shared/assets/user/landscape/fab/unzipped/cast___iron_plant_shdmr_high"
        f = d / "Cast_-_Iron_Plant_shdmr_High_4K_Opacity.jpg"
        if not f.is_file():
            self.skipTest("fab store not on this machine")
        from PIL import Image
        im = Image.open(f).convert("RGB").resize((256, 256))
        r, g, b = (sum(c.getdata()) / 65536 for c in im.split())
        self.assertGreater(r, 20); self.assertLess(g, 2); self.assertLess(b, 2)

