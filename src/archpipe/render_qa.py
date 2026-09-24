"""Automatic checks on a presentation render, so defects are not found by eye.

Each check exists because a real render shipped with that defect and a person
had to spot it (docs/LEARNINGS.md, "Presentation rendering"). Inputs:

* the `SCENE QA {...}` JSON line `build_scene.py` prints in the final
  profile, which describes what the scene actually contained;
* the rendered PNG, for what the camera actually saw.

    python -m archpipe.render_qa out/photoreal/x.png out/photoreal/x.log

Returns a report whose `passed` is False if any check FAILs. WARN is
reported but does not fail. Pure Python plus Pillow: runs anywhere, tested
without Blender in tests/test_render_qa.py.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

# Thresholds are deliberately loose: they catch a broken render, not taste.
CLIP_FAIL = 0.03          # >3% of pixels clipped in any channel
DARK_FAIL = 0.08          # >8% of pixels near black
CAST_FAIL = 0.06          # mid-tone mean chroma distance from neutral
# Local detail = mean |difference| between pixels 2 apart, on the 800-wide
# image. MEASURED on real renders: void sky gradient 0.0026, real garden
# view 0.0365. A global std-dev was tried first and failed: a smooth
# gradient has spread (0.038) with no content, so it passed the void.
WINDOW_MIN_DETAIL = 0.010
WINDOW_MAX_CLIP = 0.60    # a window mostly blown to white is a blank card
LEVEL_TOL_DEG = 0.5       # camera pitch away from level
CAD_SATURATION = 0.75     # max-min linear channel spread of an un-overridden material


def scene_qa_from_log(text: str) -> dict:
    for line in reversed(text.splitlines()):
        if line.startswith("SCENE QA "):
            return json.loads(line[len("SCENE QA "):])
    raise ValueError("no 'SCENE QA' line in the render log (not a --profile final render?)")


def _srgb_to_linear(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _pixels(img: Image.Image):
    small = img.convert("RGB")
    if small.width > 800:
        small = small.resize((800, round(800 * small.height / small.width)))
    flat = small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata()
    return small, [(r / 255.0, g / 255.0, b / 255.0) for r, g, b in flat]


def _luma(p):
    return 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]


def check(image_path, qa: dict) -> dict:
    img, px = _pixels(Image.open(image_path))
    w, h = img.size
    results = []

    def add(name, status, detail, lesson):
        results.append({"check": name, "status": status, "detail": detail, "lesson": lesson})

    # --- Image-only checks ---------------------------------------------------
    clipped = sum(1 for p in px if max(p) >= 0.995) / len(px)
    add("highlight_clipping", "FAIL" if clipped > CLIP_FAIL else "PASS",
        f"{clipped:.1%} of pixels clipped (limit {CLIP_FAIL:.0%})",
        "Sunlit white bedding blew out to pure white; expose for highlights.")
    dark = sum(1 for p in px if max(p) <= 0.01) / len(px)
    add("crushed_shadows", "FAIL" if dark > DARK_FAIL else "PASS",
        f"{dark:.1%} of pixels near black (limit {DARK_FAIL:.0%})",
        "A room lit by nothing (glass blocking daylight) renders near-black.")

    mids = [p for p in px if 0.25 < _luma(p) < 0.75]
    if mids:
        mr = sum(p[0] for p in mids) / len(mids)
        mg = sum(p[1] for p in mids) / len(mids)
        mb = sum(p[2] for p in mids) / len(mids)
        m = (mr + mg + mb) / 3.0
        cast = math.sqrt(((mr - m) ** 2 + (mg - m) ** 2 + (mb - m) ** 2) / 3.0)
        warm = "warm" if mr > mb else "cool"
        add("colour_cast", "FAIL" if cast > CAST_FAIL else "PASS",
            f"mid-tone cast {cast:.3f} ({warm}; limit {CAST_FAIL})",
            "Unbalanced 2700 K light rendered the whole room orange.")

    # --- Checks that need to know what the scene contained --------------------
    cam = qa.get("camera", {})
    if "pitch_deg" in cam:
        off = abs(cam["pitch_deg"] - 90.0)
        add("verticals_level", "FAIL" if off > LEVEL_TOL_DEG else "PASS",
            f"camera pitch {cam['pitch_deg']:.2f} deg (level = 90), shift_y {cam.get('shift_y', 0):.3f}",
            "A tilted camera made every wall lean; keep level and use lens shift.")

    lights = qa.get("lights", {})
    if lights.get("on"):
        missing = lights.get("count", 0) - lights.get("with_ies", 0)
        add("photometry_bound", "FAIL" if missing else "PASS",
            f"{lights.get('with_ies', 0)}/{lights.get('count', 0)} fixtures with measured IES",
            "An ad-hoc driver lost IES paths; fixtures fell back to isotropic points.")
    if lights.get("fallback_sun"):
        add("no_invented_light", "FAIL", "an invented fallback sun lit the scene",
            "A scene with its lights off must not silently gain a fake sun.")

    windows = qa.get("windows", [])
    sky = qa.get("sky", {})
    if sky.get("sun") and windows:
        add("glass_passes_daylight", "FAIL" if not qa.get("glass", {}).get("architectural") else "PASS",
            f"{qa.get('glass', {}).get('architectural', 0)} architectural glass material(s)",
            "Refractive glass blocks shadow rays: no sun entered the room.")
    for win in windows:
        rect = win.get("screen")          # [x0, y0, x1, y1] in 0..1, y up
        if not rect or rect[2] - rect[0] < 0.03 or rect[3] - rect[1] < 0.03:
            continue
        x0, x1 = int(rect[0] * w), int(rect[2] * w)
        y0, y1 = int((1 - rect[3]) * h), int((1 - rect[1]) * h)
        # Inset 12%: skip frame and reveal, sample the glazing itself.
        ix, iy = (x1 - x0) * 0.12, (y1 - y0) * 0.12
        box = (int(x0 + ix), int(y0 + iy), int(x1 - ix), int(y1 - iy))
        def L(x, y):
            r, g, b = img.getpixel((x, y))
            return _luma((r / 255, g / 255, b / 255))
        xs = range(max(0, box[0]), min(w, box[2]) - 2, 2)
        ys = range(max(0, box[1]), min(h, box[3]) - 2, 2)
        diffs, lum = [], []
        for x in xs:
            for y in ys:
                v = L(x, y)
                lum.append(v)
                diffs.append(abs(v - L(x + 2, y)) + abs(v - L(x, y + 2)))
        if not lum:
            continue
        detail = sum(diffs) / (2 * len(diffs))
        clip = sum(1 for v in lum if v >= 0.98) / len(lum)
        bad = detail < WINDOW_MIN_DETAIL or clip > WINDOW_MAX_CLIP
        add(f"window_view:{win.get('id', '?')[-6:]}", "FAIL" if bad else "PASS",
            f"local detail {detail:.4f} (min {WINDOW_MIN_DETAIL}), clipped {clip:.0%} (max {WINDOW_MAX_CLIP:.0%})",
            "The window showed a void, a white card or a mirror of the room instead of a view.")

    for mat in qa.get("materials", []):
        if mat.get("override") or mat.get("glass") or mat.get("photo"):
            continue
        if mat.get("saturation", 0) > CAD_SATURATION:
            add(f"cad_colour:{mat['name']}", "FAIL",
                f"linear colour spread {mat['saturation']:.2f} with no stated finish",
                "Revit shading colour [64,0,0] rendered as a pure-red lamp shade.")
    for mat in qa.get("textiles", []):
        if mat.get("reflectance") is None:
            add(f"textile_reflectance:{mat['name']}", "FAIL",
                "textile without an explicit presentation reflectance",
                "Ivory bedding rendered grey at the furniture-wide 0.35.")

    bed = qa.get("bedding")
    if bed:
        m0, m1 = bed["mattress_y"]
        d0, d1 = bed["duvet_y"]
        cover = max(0.0, min(m1, d1) - max(m0, d0)) / max(1e-6, m1 - m0)
        on_floor = bed["duvet_z_min"] < 0.05
        add("cloth_plausible", "FAIL" if (cover < 0.65 or on_floor) else "PASS",
            f"duvet covers {cover:.0%} of the mattress length (min 65%), "
            f"lowest point {bed['duvet_z_min']:.2f} m (min 0.05)",
            "A too-elastic, unpinned duvet slid 0.6 m and hung onto the floor.")

    if qa.get("white_balance") is False:
        add("white_balance_available", "WARN", "renderer cannot white-balance (Blender < 4.3)",
            "Orange cast came from the missing camera white balance.")

    return {"image": str(image_path), "passed": all(r["status"] != "FAIL" for r in results),
            "failed": [r["check"] for r in results if r["status"] == "FAIL"],
            "checks": results}


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        print("usage: python -m archpipe.render_qa <image.png> <render.log>", file=sys.stderr)
        return 2
    report = check(argv[0], scene_qa_from_log(Path(argv[1]).read_text(encoding="utf-8", errors="replace")))
    for r in report["checks"]:
        print(f"  {r['status']:4}  {r['check']:32} {r['detail']}")
    print("QA PASS" if report["passed"] else "QA FAIL: " + ", ".join(report["failed"]))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
