"""LDL pass 6: add the client's second Fab download (3 Megascans leaf/flower atlases + 1 olive FBX) to fab-manifest.json.
    python src/archpipe/landscape/plants/tools/fab_manifest_pass6.py
Listing facts are re-read from https://www.fab.com/i/listings/<uid> (no login) and cached in evidence/fab-listings.json.
The *_exr and *_ue_high folders are duplicates of the JPG archive (same Megascans id): recorded as `variants`, not new assets."""
import json, re, urllib.request
from pathlib import Path
import fab_manifest as FM   # run with the tools dir on sys.path (python -I src/.../tools/x.py puts it there)

P, FAB = FM.P, FM.FAB
UIDS = {"star_jasmine_pjycl2_4k": "6daae790-468e-4e2a-8394-4c27ed958e1d", "creeping_fig_ompjv0_4k": "adf6d6d2-0dc7-4784-a6be-3ee7f8c1828a",
        "bougainvillea_flower_phfeffeh2_4k": "134c08c4-471e-4902-ab3a-9d9ab77791cf", "olive_tree_source": "7e103045-81b6-41dd-82a8-5a1d1e276115"}
VARIANTS = {"star_jasmine_pjycl2_4k": ["star_jasmine_pjycl2_4k_exr"], "creeping_fig_ompjv0_4k": ["creeping_fig_ompjv0_4k_exr", "creeping_fig_ompjv0_4k_ue_high"],
            "bougainvillea_flower_phfeffeh2_4k": ["bougainvillea_flower_phfeffeh2_4k_exr"], "olive_tree_source": []}
KIND = {"star_jasmine_pjycl2_4k": "atlas_cutout_leaves", "bougainvillea_flower_phfeffeh2_4k": "atlas_cutout_flowers",
        "creeping_fig_ompjv0_4k": "atlas_tileable_wall_scan", "olive_tree_source": "3d_tree_game_optimised"}


def listing(uid):
    j = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://www.fab.com/i/listings/{uid}", headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
    maps = re.findall(r"Maps:</strong>(.*?)</p>", j["description"])
    return {"title": j["title"], "maps": sorted(maps[0].split()) if maps else [], "licenses": [l["slug"] for l in j["licenses"]],
            "price": [l["priceTier"]["price"] for l in j["licenses"]], "is_ai_forbidden": j.get("isAiForbidden"),
            "first_published": j.get("firstPublishedAt"), "seller": (j.get("user") or {}).get("sellerName"),
            "description_text": re.sub(r"<[^>]+>", " ", j["description"])[:600].strip()}


def main():
    ev = json.loads(FM.EV.read_text()); man = json.loads((P / "fab-manifest.json").read_text())
    for name, uid in UIDS.items():
        ev[uid] = listing(uid); d = FAB / "unzipped" / name
        zp = FAB / (name + ".zip")
        meta = next((json.loads(f.read_text()) for f in d.glob("*.json")), None)
        man["archives"][name] = {
            "kind": KIND[name], "megascans_id": meta["id"] if meta else None, "name": ev[uid]["title"],
            "latin_name_on_asset": ((meta or {}).get("semanticTags") or {}).get("latin_name") or None,
            "asset_tags_latin": [t for t in (meta or {}).get("tags", []) if t in ("trachelospermum jasminoides", "ficus pumila")],
            "scan_area_m": next((m["value"] for m in (meta or {}).get("meta", []) if m["key"] == "scanArea"), None),
            "quality_variant": "4k" if name.endswith("_4k") else "source_fbx", "zip": zp.name if zp.is_file() else None,
            "zip_sha256": FM.sha(zp) if zp.is_file() else None,
            "map_types_in_json": sorted({x["name"] for x in (meta or {}).get("maps", [])}),
            "listing_uid": uid, "listing_match": "uid supplied by the client with the download", "listing_url": f"https://www.fab.com/listings/{uid}",
            "listing_licences": ev[uid]["licenses"], "listing_price": ev[uid]["price"], "listing_seller": ev[uid]["seller"],
            "licence": "Fab Standard License", "licence_url": FM.LICENCE_URL, "licence_quote": FM.LICENCE_QUOTE,
            "variants": {v: {"zip_sha256": FM.sha(FAB / (v + ".zip")), "files": {f.name: FM.sha(f) for f in sorted((FAB / "unzipped" / v).rglob("*")) if f.is_file()}}
                         for v in VARIANTS[name] if (FAB / (v + ".zip")).is_file()},
            "files": {f.name: FM.sha(f) for f in sorted(d.iterdir()) if f.is_file()},
        }
    FM.EV.write_text(json.dumps(ev, indent=1) + "\n")
    (P / "fab-manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(len(man["archives"]), "archives")


if __name__ == "__main__":
    main()
