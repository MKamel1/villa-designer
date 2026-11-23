"""Write knowledge/landscape/plants/fab-manifest.json: sha256 of every file of the 27 Fab/Megascans archives
(binaries stay outside git), the archive/quality variant, the Megascans JSON facts (id, latin_name, tris), and the Fab listing.

    python -I src/archpipe/landscape/plants/tools/fab_manifest.py

Listing match: unique title -> that listing; several listings with one title (Taro, English Ivy, Sage, Lawn Grass) are
resolved only when the set of map types in the archive's own JSON equals exactly one listing's "Maps:" line, else
`listing_uid` is null and `listing_candidates` lists them (the archive does not name its listing; never guessed).
Listing JSONs come from https://www.fab.com/i/listings/<uid> (cached in evidence/fab-listings.json)."""
import hashlib, json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
P = ROOT / "knowledge/landscape/plants"
FAB = Path.home() / "archpipe/shared/assets/user/landscape/fab"
CAND = json.loads((P / "free-candidates-fab.json").read_text())["items"]
EV = P / "evidence/fab-listings.json"
LICENCE_URL = "https://www.fab.com/eula"
LICENCE_QUOTE = ("Fab Standard License (summary on the EULA page, not legally binding; the full EULA text is): "
                 "You may: Use the assets commercially or privately; Modify and adjust the assets in order to incorporate them "
                 "into your Projects; Commercially distribute your Projects with the Fab assets incorporated into it; "
                 "Use the assets with any compatible tools (usage is not limited to Unreal Engine). You may not: Resell or "
                 "redistribute the asset for free on a standalone basis or allow others to do the same. Both pricing tiers "
                 "(Personal and Professional) grant you the same scope of rights.")


PASS6 = {"star_jasmine_pjycl2_4k", "creeping_fig_ompjv0_4k", "bougainvillea_flower_phfeffeh2_4k", "olive_tree_source"} | {n + s for n in ("star_jasmine_pjycl2_4k", "creeping_fig_ompjv0_4k", "bougainvillea_flower_phfeffeh2_4k") for s in ("_exr", "_ue_high")}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def listings():
    if EV.is_file():
        return json.loads(EV.read_text())
    out = {}
    for uid in CAND:
        r = urllib.request.urlopen(urllib.request.Request(f"https://www.fab.com/i/listings/{uid}", headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
        j = json.loads(r)
        maps = re.findall(r"Maps:</strong>(.*?)</p>", j["description"])
        out[uid] = {"title": j["title"], "maps": sorted(maps[0].split()) if maps else [], "licenses": [l["slug"] for l in j["licenses"]],
                    "price": [l["priceTier"]["price"] for l in j["licenses"]], "is_ai_forbidden": j.get("isAiForbidden"),
                    "first_published": j.get("firstPublishedAt"), "seller": (j.get("user") or {}).get("sellerName")}
    EV.parent.mkdir(exist_ok=True)
    EV.write_text(json.dumps(out, indent=1) + "\n")
    return out


def main():
    L = listings()
    arch = {}
    for d in sorted((FAB / "unzipped").iterdir()):
        if not (d / ".." / ".." / (d.name + ".zip")).exists() or not next(d.glob("*.json"), None) or d.name in PASS6:
            continue          # pass-6 archives (atlases, olive, duplicates) are owned by fab_manifest_pass6.py
        js = next(d.glob("*.json"))
        meta = json.loads(js.read_text())
        quality = d.name.rsplit("_", 1)[1]            # high | raw | 4k | 8k
        mesh0 = sorted({(m["variation"], m["tris"]) for m in meta.get("models", []) if m.get("lod") == 0 and m.get("tier") == 0})
        mapset = sorted({x["name"] for x in meta.get("maps", []) if x.get("tier") == 0})
        cands = [u for u, v in L.items() if v["title"].lower() == meta["name"].lower()]
        match = [u for u in cands if sorted(m.lower() for m in L[u]["maps"]) == sorted(m.lower() for m in mapset)]
        uid = cands[0] if len(cands) == 1 else (match[0] if len(match) == 1 else None)
        files = {f.name: sha(f) for f in sorted(d.iterdir()) if f.is_file()}
        zp = FAB / (d.name + ".zip")
        arch[d.name] = {
            "kind": "surface" if meta["semanticTags"].get("asset_type") == "surface" else "3d_plant",
            "megascans_id": meta["id"], "name": meta["name"], "latin_name_on_asset": meta["semanticTags"].get("latin_name") or None,
            "quality_variant": quality, "zip": zp.name, "zip_sha256": sha(zp),
            "variations_lod0_tris": {v: t for v, t in mesh0},
            "map_types_in_json": mapset,
            "listing_uid": uid, "listing_match": "unique title" if len(cands) == 1 else "map-set equality (heuristic)" if uid else "ambiguous: several listings share the title and map set", "listing_url": f"https://www.fab.com/listings/{uid}" if uid else None,
            "listing_candidates": [f"https://www.fab.com/listings/{u}" for u in cands] if not uid else None,
            "licence": "Fab Standard License", "licence_url": LICENCE_URL, "licence_quote": LICENCE_QUOTE,
            "files": files,
        }
    doc = {"schema": "fab-manifest/1", "root": "~/archpipe/shared/assets/user/landscape/fab/ (unzipped/<archive>/); binaries are NOT in git",
           "checked": "2026-11-22", "licence_note": "the quoted text is the EULA page's own summary; the binding text is the full Fab EULA at the same URL",
           "listings_not_downloaded": sorted(f"{v['title']} {u}" for u, v in L.items() if u not in {a['listing_uid'] for a in arch.values()} and
                                             not any(f"/{u}" in " ".join(a["listing_candidates"] or []) for a in arch.values())),
           "archives": arch}
    (P / "fab-manifest.json").write_text(json.dumps(doc, indent=1) + "\n")
    for k, a in arch.items():
        print(k, a["listing_uid"] and a["listing_uid"][:8], len(a["files"]))
    print("not downloaded:", doc["listings_not_downloaded"])


if __name__ == "__main__":
    main()
