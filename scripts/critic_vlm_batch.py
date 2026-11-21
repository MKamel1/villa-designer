"""Run the VLM half of the critic over a set of jpgs. Stdlib only; meant to run on the workstation:

    flock ~/archpipe/locks/graphics.lock python3 critic_vlm_batch.py --rubric rubric.json \
        --imgdir ~/archpipe/scratch/critic --bench bench_32.jpg --views v01,v05 --out results/tune1

Writes <out>/<view>.json per view (resumable: existing files are skipped unless --force).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path


def load_vlm(path: Path):
    spec = importlib.util.spec_from_file_location("critic_vlm", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["critic_vlm"] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubric", required=True)
    ap.add_argument("--vlm", default=str(Path(__file__).with_name("vlm.py")))
    ap.add_argument("--imgdir", required=True)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--views", required=True, help="comma-separated view prefixes, e.g. v01,v05")
    ap.add_argument("--titles", default="", help="json {view: title}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--criteria", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    vlm = load_vlm(Path(a.vlm))
    rubric = json.loads(Path(a.rubric).read_text(encoding="utf-8"))
    titles = json.loads(Path(a.titles).read_text(encoding="utf-8")) if a.titles else {}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for v in a.views.split(","):
        dest = out / f"{v}.json"
        if dest.exists() and not a.force:
            continue
        exact = Path(a.imgdir) / f"{v}.jpg"
        jpgs = [exact] if exact.exists() else sorted(Path(a.imgdir).glob(f"{v}-*.jpg"))
        if not jpgs:
            print("missing image for", v)
            continue
        t0 = time.time()
        print(v, jpgs[0].name, flush=True)
        try:
            res = vlm.score_view(a.host, rubric, str(jpgs[0]), a.bench, titles.get(v, ""),
                                 criteria=[c for c in a.criteria.split(",") if c] or None)
            status = "ok"
        except vlm.VlmUnavailable as e:
            res, status = {}, f"unavailable: {e}"
        dest.write_text(json.dumps({"view": v, "model": rubric["preregistration"]["model"],
                                    "rubric": rubric["version"], "status": status,
                                    "seconds": round(time.time() - t0, 1), "scores": res}, indent=1),
                        encoding="utf-8")
        print(f"  {status} {time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
