"""Furniture front axes in glTF's horizontal X/Z plane and Blender's X/Y plane."""
from __future__ import annotations

import math

FRONTS = {"+X": 0.0, "-X": 180.0, "+Z": -90.0, "-Z": 90.0}


def model_yaw(layout_yaw: float, front_axis: str) -> float:
    """Blender's glTF importer maps native +Z to scene -Y."""
    if front_axis == "none":
        return float(layout_yaw)
    if front_axis not in FRONTS:
        raise ValueError("directional furniture requires front_axis (+X, -X, +Z, or -Z)")
    return float(layout_yaw) + 90.0 - FRONTS[front_axis]


def check_model_orientation(model: dict, tolerance_deg: float = 1.0) -> None:
    axis = model.get("front_axis")
    if axis == "none":
        return
    yaw = model["rotation_deg"][2]
    target = model["layout_rotation_deg"]
    error = (yaw - model_yaw(target, axis) + 180.0) % 360.0 - 180.0
    if not math.isfinite(error) or abs(error) > tolerance_deg:
        raise ValueError(f"{model['id']}: front-axis yaw misses layout front by {error:.3f} degrees")
