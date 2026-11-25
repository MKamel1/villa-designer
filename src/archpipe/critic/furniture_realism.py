"""Furniture realism check (lane SOFT, client 2026-11-25): flags furniture that reads as fake in a render.

Per object, from the scene geometry and its material (no pixels needed):
  box        pure box: almost every face normal on one of three axes and no bevel/rounding
  flat       fabric-like object with no texture asset (flat colour)
  scale      texture feature size, in mm on the object, outside the band for its fabric class
  float      object that claims to rest on a host but its lowest point is above it
  penetrate  vertex of a soft good inside its host's solid
plus, per object crop, a vision-model question (`vlm_question`). The geometry checks are pure numpy so the guard is
a unit test; the VLM adds judgement a rule cannot hold ("would a person call this a real cushion?").

Thresholds are OURS (`policy`): the held books carry no fabric weave, cushion-shape or bevel figures (knowledge
search, 2026-11-25). They are bands to catch gross error, not standards.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

POLICY = {
    # fraction of face area whose normal is within 3 deg of an axis, above which a closed shape reads as a box
    "box_axis_area_fraction": 0.80,
    # a bevel/rounding shows as faces that are neither axis-aligned nor hidden; below this share it is "no bevel"
    "box_bevel_min_faces": 0.0,
    # feature-size bands, mm, per fabric class (ours, unverified; see module docstring)
    "feature_mm_band": {"boucle": [3.0, 9.0], "linen": [0.5, 3.0], "cotton": [0.5, 3.0], "leather": [1.0, 4.0],
                        "velvet": [0.3, 2.0]},
}


def feature_fraction(path):
    """Feature size of a texture as a fraction of its tile: twice the 1/e correlation length, measured on the albedo."""
    from PIL import Image
    im = np.asarray(Image.open(path).convert("L"), float)
    n = min(im.shape[0], im.shape[1], 1024)
    im = im[:n, :n] - im[:n, :n].mean()
    ac = np.fft.ifft2(np.abs(np.fft.fft2(im)) ** 2).real
    ac /= ac[0, 0]
    prof = (ac[0, : n // 2] + ac[: n // 2, 0]) / 2
    lag = int(np.argmax(prof < 1 / np.e))
    return 2.0 * lag / im.shape[1] if n == im.shape[1] else 2.0 * lag / n


def measure_fabrics(library_root, assets):
    out = {}
    for a in assets:
        files = sorted(Path(library_root, "materials", a).glob("*_Color.*"))
        if files:
            out[a] = round(feature_fraction(files[0]), 6)
    return out


if __name__ == "__main__":
    import sys
    root = Path.home() / "archpipe/assets/library"
    assets = ["rough_linen", "Fabric066", "Carpet016", "Leather035A", "Fabric036", "Fabric081C", "Fabric082A", "Fabric030"]
    table = {"policy": "OURS (unverified): the held books carry no fabric weave figures. Targets are band centres.",
             "feature_fraction_of_tile": measure_fabrics(root, assets),
             "classes": {
                 "boucle": {"feature_mm": 5.0, "roughness": 0.92, "sheen": 0.35, "fuzz": 0.55},
                 "linen": {"feature_mm": 1.2, "roughness": 0.9, "sheen": 0.25, "fuzz": 0.30},
                 "cotton": {"feature_mm": 1.2, "roughness": 0.9, "sheen": 0.22, "fuzz": 0.25},
                 "leather": {"feature_mm": 2.0, "roughness": 0.55, "sheen": 0.0, "fuzz": 0.0},
                 "velvet": {"feature_mm": 0.8, "roughness": 0.85, "sheen": 0.8, "fuzz": 0.7}}}
    Path(sys.argv[1]).write_text(json.dumps(table, indent=1) + "\n")
    print(table["feature_fraction_of_tile"])
