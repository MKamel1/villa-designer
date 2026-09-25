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


def pilot(host: str = "ai-workstation") -> dict:
    from workstation import _ssh, deploy, digest
    items = []
    for iid in PILOT:
        it = store.search(text=None, include_unverified=True, limit=100000)
        it = next(x for x in it if x["id"] == iid)
        declared = {k: it["data"][k] for k in ("real_size_mm", "dimensions_mm", "polycount") if k in it["data"]}
        items.append({"id": iid, "source": it["source"], "key": it["key"], "asset_type": it["data"]["asset_type"],
                      "files": _files(it), "declared": declared, "negative_control": iid in NEGATIVE_CONTROL})
    job = json.dumps({"items": items}).encode()
    root, release, _ = deploy(host)
    env = json.loads(_ssh(host, "cat " + shlex.quote(root + "/worker-environment.json")).stdout)
    jdir = f"{root}/products/{digest(job)[:16]}"
    _ssh(host, f"mkdir -p {shlex.quote(jdir)} && cat > {shlex.quote(jdir + '/job.json')}", stdin_bytes=job)
    steps = [
        [env["python"], f"{release}/scripts/products_worker.py", "fetch", "--job", f"{jdir}/job.json",
         "--lib", f"{root}/library", "--out", f"{jdir}/stage1.json"],
        [env["blender"], "-b", "--factory-startup", "-P", f"{release}/scripts/products_worker.py", "--",
         "render", "--job", f"{jdir}/stage1.json", "--out", f"{jdir}/stage2.json"],
    ]
    for cmd in steps:
        r = _ssh(host, shlex.join(cmd), timeout=3600)
        if r.returncode:
            raise RuntimeError((r.stdout + r.stderr).decode(errors="replace")[-4000:])
    stage = json.loads(_ssh(host, "cat " + shlex.quote(jdir + "/stage2.json")).stdout)
    report = {"items": [], "negative_control": []}
    for rec in stage["items"]:
        checks = list(rec["checks"])
        checks.append({"name": "license_open", "status": "passed", "measured": "CC0",
                       "detail": "source states CC0 for every asset"})
        size_key = "real_size_mm" if rec["asset_type"] == "texture" else "dimensions_mm"
        if rec["asset_type"] == "texture":
            checks.append({"name": "real_size_declared",
                           "status": "passed" if rec["declared"].get(size_key) else "not_checkable",
                           "measured": rec["declared"].get(size_key),
                           "detail": "tile size published by the source" if rec["declared"].get(size_key)
                           else "source publishes no tile size: scale must be set by hand and labelled"})
        checks.append({"name": "product_link", "status": "not_checkable",
                       "detail": "free appearance asset: any product it stands for is a look-alike-proxy claim"})
        layer = store.record_checks(rec["id"], checks)
        report["items"].append({"id": rec["id"], "layer": layer,
                                "checks": {c["name"]: c["status"] for c in checks},
                                "albedo": rec.get("albedo", {}).get("mean"),
                                "rendered": rec.get("swatch", {}).get("rendered_mean")})
        if rec.get("negative_control_result"):
            report["negative_control"].append(dict(rec["negative_control_result"], id=rec["id"]))
    out = ROOT / "out" / "products-pilot.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"stage": stage, "report": report}, indent=1), encoding="utf-8")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["index", "pilot", "search", "show", "status"])
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
