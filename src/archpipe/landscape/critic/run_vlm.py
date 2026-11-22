"""Score plan images (and photos) with the local VLM, one criterion per call. Reuses archpipe.critic.vlm (not edited).

    python -m archpipe.landscape.critic.run_vlm --split tuning|held_out|photos [--only ID,ID] [--host URL]

Writes knowledge/landscape/critic/runs/<split>/<item>.json. GPU: run through jobq (see docs/lanes/LDC.md).
"""
from __future__ import annotations

import argparse
import io
import json
import time

from PIL import Image

from ...critic import vlm as V
from . import plan, seeds
from .common import KNOW
from .d1 import load as load_d1

RUNS = KNOW / "critic/runs"
SOUTH_VIEW = [14, -31, 29.5, -19.5]
FINALS = "/home/omar/archpipe/shared/laptop-out/villa/finals-2026-10-15"
D1_VIEWS = ["v19", "v25", "v26", "v27", "v28", "v36", "v37", "v39", "v40"]


def jpg_b64(path, px=1280):
    import base64
    im = Image.open(path).convert("RGB"); im.thumbnail((px, px))
    b = io.BytesIO(); im.save(b, "JPEG", quality=90)
    return base64.b64encode(b.getvalue()).decode()


def layout_for(item):
    if item == "D1-current": return load_d1(), SOUTH_VIEW
    if item == "base": return seeds.base(), SOUTH_VIEW
    if item.startswith("P-"):
        return json.loads((KNOW / f"critic/precedent-layouts/{item}.json").read_text()), None
    return seeds.make(item), SOUTH_VIEW


def plan_path(item):
    d = KNOW / "critic/plans"; d.mkdir(parents=True, exist_ok=True)
    return d / f"{item}.png"


def photo_items():
    import glob, os
    cal = json.loads((KNOW / "precedents/calibration.json").read_text())
    good = []
    for side in ("south", "north"):
        for g in cal["known_good"][side]["gardens"]:
            for p in g["photos"]: good.append(("good", os.path.expanduser(p)))
    bad = [("bad", sorted(glob.glob(f"{FINALS}/{v}-*.png"))[0]) for v in D1_VIEWS]
    return good + bad


def score(host, model, opts, prompt, img_b64):
    r = V.chat(host, model, prompt, [img_b64], opts, V.SCORE_SCHEMA, False)
    return V.clean_score(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--only")
    ap.add_argument("--host", default="http://localhost:11434")
    a = ap.parse_args(argv)
    rub = json.loads((KNOW / "critic/rubric.json").read_text())
    if a.split == "held_out" and not rub["version"].startswith("frozen"):
        raise SystemExit("held_out is scored only with a frozen rubric (rubric.version starts with 'frozen')")
    out = RUNS / a.split; out.mkdir(parents=True, exist_ok=True)
    opts = rub["options"]; model = rub["model"]
    if a.split == "photos":
        items = [(f"{k}-{i:02d}", k, p) for i, (k, p) in enumerate(photo_items())]
        crits = {k: v for k, v in rub["photo_criteria"].items()}
        pre = "You are a strict but fair landscape architect. Judge this garden image on the single criterion below. 2 = clearly met or the problem is minor; 1 = clearly visible problem; 0 = severe, obvious. If not sure score 2. Reply JSON only: {\"evidence\": \"<=40 words\", \"score\": 0|1|2}."
    else:
        ids = rub["split"]["bad"][a.split] + rub["split"]["good"][a.split]
        items = []
        for i in ids:
            lay, view = layout_for(i)
            pp = plan_path(i); plan.plan_png(lay, str(pp), view=view)
            items.append((i, "bad" if i in rub["split"]["bad"][a.split] else "good", str(pp)))
        crits = {k: v["prompt"] for k, v in rub["criteria"].items()}
        pre = rub["preamble"]
    if a.only: items = [t for t in items if t[0] in a.only.split(",")]
    for iid, label, path in items:
        f = out / f"{iid}.json"
        if f.exists(): continue
        img = jpg_b64(path); res = {}
        t0 = time.time()
        for c, text in crits.items():
            res[c] = score(a.host, model, opts, pre + "\n\nCriterion: " + text, img)
        f.write_text(json.dumps({"item": iid, "label": label, "image": str(path), "rubric": rub["version"], "model": model, "scores": res}, indent=1))
        print(iid, label, {k: v.get("score") for k, v in res.items()}, f"{time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
