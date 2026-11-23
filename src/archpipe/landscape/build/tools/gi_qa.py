"""render_qa and captions for rendered garden views (the checks `scripts/villa_render.py` runs after a remote render, for a render done by the lane's own jobq command).

    python -m archpipe.landscape.build.tools.gi_qa SCENE.json RENDER_DIR
Writes <view>.qa.json and <view>.caption.json beside each <view>.png and prints one line per view: passed / failed checks. Exit 1 if any view fails.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))


KOI_MIN_FRAME_FRACTION = 0.004     # a koi whose box covers less of the frame than this is too small to be asked to show
KOI_MIN_ORANGE_PX_FRAC = 0.01      # of the visible koi boxes' pixels at least this share must be koi-orange (the asset is white with red-orange patches)


def koi_visible(report, png):
    """Guard found by the pond defect (2026-11-22: a floor under the water hid every koi; no check noticed). For each koi of the view's report whose screen box
    (x0, y0, x1, y1 as fractions, y from the bottom) is inside the frame and big enough, count koi-orange pixels in the box. -> dict(applies, orange_px, box_px, passed)."""
    from PIL import Image
    import numpy as np
    boxes = [p["screen"] for p in report.get("imported_props", []) if "koi" in p["id"] and p.get("in_frame") and p.get("screen")]
    im = np.asarray(Image.open(png).convert("RGB")).astype(float) / 255
    H, W = im.shape[:2]
    orange = box = 0
    for x0, y0, x1, y1 in boxes:
        x0, x1, y0, y1 = max(0.0, x0), min(1.0, x1), max(0.0, y0), min(1.0, y1)
        if (x1 - x0) * (y1 - y0) < KOI_MIN_FRAME_FRACTION:
            continue
        r = im[int((1 - y1) * H):max(int((1 - y0) * H), int((1 - y1) * H) + 1), int(x0 * W):max(int(x1 * W), int(x0 * W) + 1)]
        box += r.shape[0] * r.shape[1]
        orange += int(((r[..., 0] > 0.5) & (r[..., 1] < 0.55 * r[..., 0]) & (r[..., 2] < 0.45 * r[..., 0])).sum())
    return dict(applies=box > 0, orange_px=orange, box_px=box, passed=(box == 0) or orange >= KOI_MIN_ORANGE_PX_FRAC * box)


def main(scene_path, out):
    from villa_render import villa_qa_context, villa_qa_scope, villa_caption
    from archpipe.render_qa import check
    from archpipe.blender.element_ids import without_ids
    scene = without_ids(json.loads(Path(scene_path).read_text(encoding="utf-8")))
    views = {v["id"]: v for v in scene["views"]}
    bad = 0
    for png in sorted(Path(out).glob("*.png")):
        ident = png.stem
        report = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))
        qa_in = villa_qa_context(scene, views[ident], report)
        qa = check(png, qa_in)
        qa["scope"] = villa_qa_scope(qa, qa_in)
        koi = koi_visible(report, png)
        if koi["applies"]:
            qa["checks"].append(dict(check="koi_visible", passed=koi["passed"], detail=koi))
            qa["passed"] = qa["passed"] and koi["passed"]
        png.with_suffix(".qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
        png.with_suffix(".caption.json").write_text(json.dumps(villa_caption(scene, views[ident], report, qa), indent=2), encoding="utf-8")
        fails = [c["check"] for c in qa["checks"] if not c.get("passed", c.get("ok", True))]
        print("%-34s %s  failed: %s" % (ident, "PASS" if qa["passed"] else "FAIL", ", ".join(fails) or "-"))
        bad += not qa["passed"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
