"""Import the two independent measurement passes (cached outside the repo, no images committed) into
knowledge/landscape/precedents/{south,north}.json. Run once after the passes: python -m archpipe.landscape.precedents.build"""
import json
from pathlib import Path
from . import ANNOTATIONS, DATA, PLAN_METRICS, QUALITATIVE, validate_set

CACHE = Path.home() / "archpipe/shared/landscape-precedents"
KEEP = PLAN_METRICS + QUALITATIVE + ANNOTATIONS


def build(name):
    index = {g["id"]: g for g in json.loads((CACHE / name / "index.json").read_text())}
    passes = {p: {g["id"]: g for g in json.loads((CACHE / "measure" / f"{name}-{p}.json").read_text())["gardens"]} for p in "AB"}
    out = []
    for gid in passes["A"]:
        meta = index.get(gid) or next(v for k, v in index.items() if k.startswith(gid) or gid.startswith(k))
        out.append({
            "id": gid, "name": meta["name"], "designer": meta.get("designer"), "location": meta.get("location"),
            "year": meta.get("year"), "page_url": meta["page_url"], "plan_url": meta.get("plan_url"),
            "scaled_plan": bool(meta.get("has_scaled_plan")), "cache_dir": f"~/archpipe/shared/landscape-precedents/{name}/{gid}",
            "passes": {p: {k: v for k, v in passes[p].get(gid, {}).items() if k in KEEP and v is not None} for p in "AB"},
        })
    probs = validate_set(out)
    (DATA / f"{name}.json").write_text(json.dumps({"set": name, "gardens": out}, indent=1) + "\n")
    return len(out), probs


if __name__ == "__main__":
    for n in ("south", "north"):
        print(n, build(n))
