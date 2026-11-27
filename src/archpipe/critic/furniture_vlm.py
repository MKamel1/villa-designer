"""Vision-model question per furniture crop (lane SOFT). Stdlib + numpy + Pillow; talks to Ollama (critic/vlm.py).

    python -m archpipe.critic.furniture_vlm --scene scene.json [--soft] --render-dir DIR --views v02-garden-living,... \
        --out out.json [--model gemma4:12b]

One question per object (cushion, pillow, throw, furniture item) whose projected bounds lie wholly inside the view: the
crop is cut from the render, `furniture_realism.vlm_question` asked, evidence before score, temperature 0.

ADVISORY, NOT A GATE. Calibrated 2026-11-25 on the rigid cushions, the baked ones and a real scan (Poly Haven
throw_pillows_01), with gemma4:12b and qwen2.5vl:7b: an absolute "is it real" prompt scored everything 0 (scan
included); a three-observation rubric scored everything 2 (rigid cushion included); a pairwise comparison against the
scan always preferred the in-scene crop. None separates the defect from a good asset, so the gate is geometric
(`furniture_realism.check_scene`) and the VLM text is kept as a second opinion in the report.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np

from . import furniture_realism as F
from . import vlm

KIND = {"cushion": "scatter cushion", "pillow": "bed pillow", "throw": "folded throw blanket"}


def objects(scene):
    """{object id: (kind, world points)} for soft goods and visible furniture items."""
    items = {}
    for m in scene["meshes"]:
        if F.SOFT_ID.match(m["id"]):
            items[m["id"]] = (KIND[m["id"].split("-")[1]], [m])
            items[m["id"]][1][0]["_room"] = m.get("room")
        elif m["group"] == "furniture" and m["id"].startswith("furn-") and m.get("label") \
                and not m["label"].startswith(("ASSUMED", "stair")) \
                and m.get("part_kind") not in ("joinery-pull", "box-handle", "glass-pane"):
            items.setdefault(m["label"], (m["label"].replace("-", " "), []))[1].append(m)
    return {k: (kind, np.array([p for mm in ms for f in mm["faces"] for p in f], float), ms[0].get("room"))
            for k, (kind, ms) in items.items()}


def run(scene, render_dir, views, host, model, out_dir):
    out = []
    objs = objects(scene)
    by_view = {v["id"]: v for v in scene["views"]}
    for vid in views:
        png = Path(render_dir) / (vid + ".png")
        view = by_view[vid]
        for oid, (kind, pts, room) in objs.items():
            # only what the view is about: its subjects, and the soft goods of its own room (no occlusion test here)
            if not (oid in view.get("subjects", []) or (F.SOFT_ID.match(oid) and room == view.get("room"))):
                continue
            crop = F.crop_for(view, pts, png, Path(out_dir) / ("%s__%s.png" % (vid, oid)))
            if not crop:
                continue
            try:
                ans = vlm.chat(host, model, F.vlm_question(kind), [vlm.b64(crop)],
                               {"temperature": 0, "seed": 7, "num_predict": 400}, F.VLM_SCHEMA)
                ans["score"] = F.vlm_score(ans)
            except vlm.VlmUnavailable as e:
                ans = {"error": str(e)}
            out.append({"view": vid, "object": oid, "kind": kind, "crop": str(crop), **ans})
            print(vid, oid, ans.get("score"), flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--soft", action="store_true")
    ap.add_argument("--render-dir", required=True)
    ap.add_argument("--views", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="gemma4:12b")
    ap.add_argument("--host", default="http://localhost:11434")
    a = ap.parse_args(argv)
    scene = json.loads(Path(a.scene).read_text(encoding="utf-8"))
    if a.soft:
        from ..blender import soft_goods
        soft_goods.soften_scene(scene)
    crops = Path(a.out).with_suffix("")
    crops.mkdir(parents=True, exist_ok=True)
    rows = run(scene, a.render_dir, a.views.split(","), a.host, a.model, crops)
    Path(a.out).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
