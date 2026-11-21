"""Metadata checks R1 (lens), R2 (camera height) and the metadata half of R3 (pitch).

Input is the per-view render json written next to each png (finals-2026-10-15/v*.json).
Every function returns (score 0|1|2 | None, message, achieved). None = not_evaluated.
"""
from __future__ import annotations

import json
from pathlib import Path

FLOOR_DATUMS_M = (-3.0, 0.0)     # basement ground / upper floor in model z; see rubric card POLICY-R2


def find_camera(meta: dict) -> dict | None:
    """The camera block lives at exposure_rule_measurement.view_input.camera; search defensively."""
    def walk(o):
        if isinstance(o, dict):
            if "lens_mm" in o and "position" in o:
                return o
            for v in o.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o[:50]:
                r = walk(v)
                if r:
                    return r
        return None
    return walk(meta)


def load_view(png: str | Path) -> dict:
    """Load the camera/subject metadata beside a png. Missing json -> empty dict."""
    p = Path(png).with_suffix(".json")
    if not p.exists():
        return {}
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {"camera": find_camera(meta), "subjects": meta.get("subjects", []),
            "pitch_deg": meta.get("camera_pitch_deg"), "resolution": meta.get("resolution"),
            "imported_models": meta.get("imported_models", []), "title": meta.get("title"),
            "state": meta.get("state"), "exposure_group": meta.get("exposure_group")}


def check_r1(camera: dict | None):
    if not camera or camera.get("lens_mm") is None:
        return None, "lens not recorded", None
    lens = float(camera["lens_mm"])
    if 24 <= lens <= 35:
        return 2, f"{lens:g} mm is inside 24-35 mm", lens
    reasons = [o.get("reason", "") for o in camera.get("overrides", []) if o.get("field") == "lens_mm"]
    reason = camera.get("lens_reason") or (reasons[0] if reasons else "")
    if 16 <= lens < 24:
        if reason:
            return 1, f"{lens:g} mm is wider than 24 mm; written reason: {reason}", lens
        return 0, f"{lens:g} mm has no written reason (16-20 mm needs one)", lens
    return 0, f"{lens:g} mm is outside 16-35 mm", lens


def camera_height_m(camera: dict, datums=FLOOR_DATUMS_M) -> float | None:
    try:
        z = float(camera["position"][2])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    below = [d for d in datums if d <= z + 0.3]
    return z - max(below) if below else None


def check_r2(camera: dict | None):
    if not camera:
        return None, "camera not recorded", None
    h = camera_height_m(camera)
    if h is None:
        return None, "no floor datum below the camera", None
    if 1.1 <= h <= 1.6:
        return 2, f"eye height {h:.2f} m (limit 1.1-1.6 m)", h
    if 0.9 <= h <= 1.8:
        return 1, f"eye height {h:.2f} m is outside 1.1-1.6 m by up to 0.2 m", h
    return 0, f"eye height {h:.2f} m is outside 0.9-1.8 m", h


def check_r3_meta(camera: dict | None, pitch_deg):
    """Pitch from the camera: position z against target z when both exist, else camera_pitch_deg."""
    import math
    pitch = None
    if camera and "target" in camera and "position" in camera:
        p, t = camera["position"], camera["target"]
        horiz = math.hypot(t[0] - p[0], t[1] - p[1])
        if horiz > 1e-6:
            pitch = math.degrees(math.atan2(t[2] - p[2], horiz))
    if pitch is None and pitch_deg is not None:
        pitch = float(pitch_deg)
    if pitch is None:
        return None, "pitch not recorded", None
    a = abs(pitch)
    if a <= 0.5:
        return 2, f"pitch {pitch:.2f} deg (limit 0.5)", a
    if a <= 1.5:
        return 1, f"pitch {pitch:.2f} deg exceeds 0.5 deg", a
    return 0, f"pitch {pitch:.2f} deg exceeds 1.5 deg", a
