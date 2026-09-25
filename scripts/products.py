"""Product library: index sources, verify a pilot on the workstation, search.

    python scripts/products.py index                 # Poly Haven + ambientCG (appearances, CC0)
    python scripts/products.py pilot                 # download + check the pilot set on the workstation
    python scripts/products.py search --text walnut [--category surface] [--style japandi] [--all]
    python scripts/products.py show polyhaven:american_walnut_veneer
    python scripts/products.py status

The index lives in assets/user/products/index.sqlite (git-ignored); files live
on the workstation under ~/archpipe/library/. See src/archpipe/products/.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from archpipe import fetch  # noqa: E402
from archpipe.products import sources, store  # noqa: E402

# The first verified set, oversampling the villa-01 taste profile (walnut,
# oak, large stone, travertine, onyx, boucle, linen, leather, velvet, plaster,
# microcement, terrazzo) plus six models. marble_01 also runs a negative
# control: the same swatch with its base colour misread as Non-Color.
PILOT = ["polyhaven:american_walnut_veneer", "polyhaven:oak_veneer_01", "polyhaven:marble_01",
         "polyhaven:grey_cartago_01", "polyhaven:clay_plaster", "polyhaven:wool_boucle", "polyhaven:rough_linen",
         "polyhaven:brown_leather", "polyhaven:velour_velvet", "polyhaven:terrazzo_tiles",
         "ambientcg:Travertine001", "ambientcg:Onyx001", "ambientcg:Concrete012", "ambientcg:Marble004",
         "polyhaven:ceramic_vase_01", "polyhaven:brass_vase_01", "polyhaven:calathea_orbifolia_01",
         "polyhaven:sofa_02", "polyhaven:bar_chair_round_01", "polyhaven:desk_lamp_arm_01"]
NEGATIVE_CONTROL = {"polyhaven:marble_01"}


def _files(item: dict) -> list[dict]:
    """Exact files to fetch, with the md5/size the source publishes."""
    if item["source"] == "polyhaven":
        f = sources.polyhaven_files(item["key"])
        if item["data"]["asset_type"] == "texture":
            out = []
            for role, ours in (("Diffuse", "base"), ("Rough", "rough"), ("nor_gl", "normal"), ("Metal", "metal")):
                e = f.get(role, {}).get("2k", {}).get("jpg")
                if e:
                    out.append({"name": e["url"].rsplit("/", 1)[-1], "url": e["url"], "md5": e["md5"],
                                "size": e["size"], "role": ours})
            return out
        g = f["gltf"]["1k"]["gltf"]
        out = [{"name": g["url"].rsplit("/", 1)[-1], "url": g["url"], "md5": g["md5"], "size": g["size"]}]
        out += [{"name": name, "url": e["url"], "md5": e["md5"], "size": e["size"]} for name, e in g["include"].items()]
        return out
    a = json.loads(fetch.get_text(
        f"https://ambientcg.com/api/v2/full_json?id={item['key']}&include=downloadData", sources.CACHE))
    dls = a["foundAssets"][0]["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
    d = next(x for x in dls if x["attribute"] == "2K-JPG")
    return [{"name": d["fileName"], "url": d["downloadLink"], "size": d["size"]}]


def run_checks(items: list[dict], host: str = "ai-workstation", tag: str = "pilot") -> dict:
    """Fetch (or reuse) each item's files on the workstation, run the Pillow and Blender
    checks, and record the results in the index. items: id, source, key, asset_type,
    files [{name, url, md5?, size?, role?}], declared {real_size_mm|dimensions_mm|polycount}."""
    from workstation import _ssh, deploy, digest
    job = json.dumps({"items": items}).encode()
    root, release, _ = deploy(host)
    env = json.loads(_ssh(host, "cat " + shlex.quote(root + "/worker-environment.json")).stdout)
    jdir = f"{root}/products/{digest(job)[:16]}"
    _ssh(host, f"mkdir -p {shlex.quote(jdir)} && cat > {shlex.quote(jdir + '/job.json')}", stdin_bytes=job)
    cpu = ["env", "ARCHPIPE_RENDER_CPU=1"] if os.environ.get("ARCHPIPE_RENDER_CPU") else []
    steps = [
        [env["python"], f"{release}/scripts/products_worker.py", "fetch", "--job", f"{jdir}/job.json",
         "--lib", f"{root}/library", "--out", f"{jdir}/stage1.json"],
        cpu + [env["blender"], "-b", "--factory-startup", "-P", f"{release}/scripts/products_worker.py", "--",
         "render", "--job", f"{jdir}/stage1.json", "--out", f"{jdir}/stage2.json"],
    ]
    for cmd in steps:
        r = _ssh(host, shlex.join(cmd), timeout=7200)
        if r.returncode:
            raise RuntimeError((r.stdout + r.stderr).decode(errors="replace")[-4000:])
    stage = json.loads(_ssh(host, "cat " + shlex.quote(jdir + "/stage2.json")).stdout)
    report = {"items": [], "negative_control": []}
    for rec in stage["items"]:
        checks = list(rec["checks"])
        checks.append({"name": "license_open", "status": "passed", "measured": rec.get("license", "CC0"),
                       "detail": "licence recorded by the source for this asset"})
        size_key = "real_size_mm" if rec["asset_type"] == "texture" else "dimensions_mm"
        if rec["asset_type"] == "texture":
            checks.append({"name": "real_size_declared",
                           "status": "passed" if rec["declared"].get(size_key) else "not_checkable",
                           "measured": rec["declared"].get(size_key),
                           "detail": "tile size published by the source" if rec["declared"].get(size_key)
                           else "source publishes no tile size: scale must be set by hand and labelled"})
        checks.append({"name": "product_link", "status": "not_checkable",
                       "detail": "appearance asset: any product it stands for is a look-alike-proxy claim"})
        layer = store.record_checks(rec["id"], checks)
        report["items"].append({"id": rec["id"], "layer": layer,
                                "checks": {c["name"]: c["status"] for c in checks},
                                "albedo": rec.get("albedo", {}).get("mean"),
                                "rendered": rec.get("swatch", {}).get("rendered_mean")})
        if rec.get("negative_control_result"):
            report["negative_control"].append(dict(rec["negative_control_result"], id=rec["id"]))
    out = ROOT / "out" / f"products-{tag}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"stage": stage, "report": report}, indent=1), encoding="utf-8")
    return report


def pilot(host: str = "ai-workstation") -> dict:
    items = []
    for iid in PILOT:
        it = next(x for x in store.search(include_unverified=True, limit=100000) if x["id"] == iid)
        declared = {k: it["data"][k] for k in ("real_size_mm", "dimensions_mm", "polycount") if k in it["data"]}
        items.append({"id": iid, "source": it["source"], "key": it["key"], "asset_type": it["data"]["asset_type"],
                      "files": _files(it), "declared": declared, "negative_control": iid in NEGATIVE_CONTROL})
    return run_checks(items, host, "pilot")


# Runs on the workstation: one record per Megascans material folder, read from the zip's own JSON.
FAB_SCAN = r"""
import json, pathlib, re, zipfile
root = pathlib.Path.home() / "archpipe/library/fab"
out = []
for d in sorted(p for p in root.iterdir() if p.is_dir()):
    zs = sorted(d.glob("*_2k.zip")) or sorted(d.glob("*.zip"))
    if not zs:
        continue
    z = zs[0]
    meta = {}
    with zipfile.ZipFile(z) as zf:
        js = [n for n in zf.namelist() if n.endswith(".json")]
        if js:
            meta = json.loads(zf.read(js[0]))
    size = None
    ps = next((m.get("value") for m in meta.get("meta", []) if m.get("key") == "scanArea"), None)
    if isinstance(ps, str):
        m = re.match(r"\s*([\d.]+)\s*x\s*([\d.]+)\s*m", ps)
        if m:
            size = [float(m.group(1)) * 1000, float(m.group(2)) * 1000]
    out.append({"key": d.name, "zip": z.name, "size": z.stat().st_size, "name": meta.get("name") or d.name,
                "tags": meta.get("tags", []), "categories": meta.get("categories", []), "real_size_mm": size,
                "calibration": next((m.get("value") for m in meta.get("meta", []) if m.get("key") == "calibration"), None),
                "zips": sorted(p.name for p in d.glob("*.zip"))})
print(json.dumps(out))
"""


def fab(host: str = "ai-workstation") -> dict:
    """Index and verify the Megascans materials downloaded from Fab into ~/archpipe/library/fab/."""
    from archpipe.products import schema
    from workstation import _ssh
    r = _ssh(host, "python3 -", stdin_bytes=FAB_SCAN.encode())
    rows = json.loads(r.stdout)
    items, records = [], []
    for x in rows:
        words = x["tags"] + x["categories"] + [x["name"]]
        records.append({"id": f"fab:{x['key']}", "kind": "appearance", "category": schema.categorise(words) or "surface",
                        "source": "fab", "key": x["key"], "name": x["name"], "brand": "Quixel Megascans",
                        "license": "Fab Standard License (Professional tier, $0)", "url": None, "tags": x["tags"],
                        "styles": schema.styles_for(words),
                        "data": {"asset_type": "texture", "real_size_mm": x["real_size_mm"], "files": x["zips"],
                                 "calibration": x["calibration"]}})
        items.append({"id": f"fab:{x['key']}", "source": "fab", "key": x["key"], "asset_type": "texture",
                      "license": "Fab Standard License (Professional)",
                      "files": [{"name": x["zip"], "url": "local:already-downloaded", "size": x["size"]}],
                      "declared": {"real_size_mm": x["real_size_mm"]} if x["real_size_mm"] else {}})
    store.upsert_items(records)
    store.set_coverage("fab", len(records), len(records))
    return run_checks(items, host, "fab")


SKETCHFAB_SCAN = r"""
import json, pathlib
root = pathlib.Path.home() / "archpipe/library/sketchfab"
out = []
for d in sorted(p for p in root.iterdir() if p.is_dir() and (p / "meta.json").is_file()):
    m = json.loads((d / "meta.json").read_text())
    out.append(dict(m, size=(d / "model.zip").stat().st_size))
print(json.dumps(out))
"""


def sketchfab(host: str = "ai-workstation") -> dict:
    """Index and verify the Sketchfab models (CC0 / CC-BY) downloaded to ~/archpipe/library/sketchfab/."""
    from archpipe.products import schema
    from workstation import _ssh
    rows = json.loads(_ssh(host, "python3 -", stdin_bytes=SKETCHFAB_SCAN.encode()).stdout)
    fixes = json.loads((ROOT / "knowledge/products/sketchfab-scale-fixes.json").read_text(encoding="utf-8"))["models"]
    items, records = [], []
    for m in rows:
        words = (m.get("tags") or []) + (m.get("categories") or []) + [m.get("name") or ""]
        records.append({"id": f"sketchfab:{m['uid']}", "kind": "appearance",
                        "category": schema.categorise(words) or "decor", "source": "sketchfab", "key": m["uid"],
                        "name": m.get("name"), "brand": None, "license": m.get("licence"), "url": m.get("url"),
                        "tags": m.get("tags") or [], "styles": schema.styles_for(words),
                        "data": {"asset_type": "model", "author": m.get("author"), "attribution": m.get("attribution"),
                                 "faces": m.get("faces"),
                                 "scale_applied": (fixes.get(f"sketchfab:{m['uid']}") or {}).get("scale")}})
        items.append({"id": f"sketchfab:{m['uid']}", "source": "sketchfab", "key": f"{m['uid']}/gltf",
                      "asset_type": "model", "license": m.get("licence"),
                      "files": [{"name": "../model.zip", "url": "local:already-downloaded", "size": m["size"]}],
                      "declared": {}, "scale": (fixes.get(f"sketchfab:{m['uid']}") or {}).get("scale")})
    store.upsert_items(records)
    store.set_coverage("sketchfab", len(records), len(records))
    return run_checks(items, host, "sketchfab")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["index", "pilot", "fab", "sketchfab", "search", "show", "status"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--text")
    ap.add_argument("--category")
    ap.add_argument("--style")
    ap.add_argument("--kind")
    ap.add_argument("--all", action="store_true", help="include unverified catalogue rows")
    ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args(argv)
    if a.cmd == "index":
        t, m = sources.polyhaven("textures"), sources.polyhaven("models")
        store.upsert_items(t + m)
        store.set_coverage("polyhaven", len(t) + len(m), len(t) + len(m))
        acg, total = sources.ambientcg()
        store.upsert_items(acg)
        store.set_coverage("ambientcg", total, len(acg))
        print(f"  polyhaven {len(t)} textures + {len(m)} models; ambientcg {len(acg)} of {total} materials")
        return 0 if len(acg) >= total else 1
    if a.cmd == "pilot":
        rep = pilot()
        for r in rep["items"]:
            bad = [k for k, v in r["checks"].items() if v == "failed"]
            print(f"  {r['layer']:9s} {r['id']:40s} " + (f"FAILED {bad}" if bad else ""))
        for n in rep["negative_control"]:
            print(f"  negative control {n['id']}: base colour as Non-Color rendered {n['rendered_mean']:.3f}, "
                  f"{'caught' if n['caught'] else 'NOT CAUGHT'}")
        ok = all(n["caught"] for n in rep["negative_control"])
        return 0 if ok else 1
    if a.cmd in ("fab", "sketchfab"):
        rep = fab() if a.cmd == "fab" else sketchfab()
        bad = [r for r in rep["items"] if r["layer"] != "verified"]
        print(f"  {len(rep['items']) - len(bad)} verified, {len(bad)} not")
        for r in bad:
            print(f"  {r['layer']:9s} {r['id']:45s} {[k for k, v in r['checks'].items() if v == 'failed']}")
        return 0
    if a.cmd == "search":
        rows = store.search(kind=a.kind, category=a.category, text=a.text, style=a.style,
                            include_unverified=a.all, limit=a.limit)
        for r in rows:
            print(f"  {r['layer']:9s} {r['id']:45s} {r['category'] or '':9s} {','.join(r['styles'])}")
        print(f"  ({len(rows)} rows)")
        return 0
    if a.cmd == "show":
        r = next((x for x in store.search(include_unverified=True, limit=100000) if x["id"] == a.id), None)
        print(json.dumps(dict(r or {}, checks=store.checks_for(a.id)), indent=2))
        return 0 if r else 1
    print(json.dumps(store.counts(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
