"""Shared helpers for the Revit-free exchange exports (IFC4, DXF): levels, datum, preflight.

Everything here works from `archpipe.model` DesignElement records (millimetres). Two datums exist (L2-model.md):
the scene datum (GF FFL = 0, B FFL = -3000) and the Revit datum (GF +1200, B -1800). The exchange files use the
REVIT datum, because that is what the spec levels "B -1.80" / "GF +1.20" mean to every recipient.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..contracts import DesignElement

DATUM_SHIFT_MM = 1200.0     # scene z + 1200 = Revit z

DEFAULT_LEVELS = {
    "B":    dict(ffl_scene_mm=-3000, ffl_revit_mm=-1800, slab_mm=200, name="Basement"),
    "GF":   dict(ffl_scene_mm=0, ffl_revit_mm=1200, slab_mm=200, name="Ground floor"),
    "L1":   dict(ffl_scene_mm=3000, ffl_revit_mm=4200, slab_mm=200, name="First floor (apartment, not ours)"),
    "ROOF": dict(ffl_scene_mm=6000, ffl_revit_mm=7200, slab_mm=200, name="Roof"),
    "SITE": dict(ffl_scene_mm=-3000, ffl_revit_mm=-1800, slab_mm=0, name="Site / garden ground"),
}
STOREY_LEVELS = ("B", "GF")           # the levels that carry elements and become IfcBuildingStorey
HOST_TOLERANCE_MM = 150.0             # L2: a door/window point lies within 150 mm of its host wall centreline


class ExchangeError(ValueError):
    """The model cannot be exported faithfully. Raised instead of dropping or guessing an element."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__(f"{len(self.problems)} problem(s): " + "; ".join(self.problems[:12])
                         + (" ..." if len(self.problems) > 12 else ""))


def load_levels(design: str = "D1", path: Path | str | None = None) -> dict:
    """The level table (scene vs Revit elevations) from the model JSON the elements were loaded from."""
    from ..model import api
    cands = [Path(path)] if path else [api.cache_path(design), api.snapshot_path(design)]
    for p in cands:
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data.get("levels"), dict):
                return data["levels"]
    return DEFAULT_LEVELS


def ffl(levels: dict, level: str) -> float:
    """Finished-floor elevation of `level` in the Revit datum, mm."""
    try:
        return float(levels[level]["ffl_revit_mm"])
    except KeyError:
        raise ExchangeError([f"unknown level {level!r}"]) from None


def scene_to_revit(z_scene: float) -> float:
    return float(z_scene) + DATUM_SHIFT_MM


def wall_line(w: DesignElement) -> tuple[tuple[float, float], tuple[float, float]]:
    p = w.params
    return (float(p["x0_mm"]), float(p["y0_mm"])), (float(p["x1_mm"]), float(p["y1_mm"]))


def wall_length(w: DesignElement) -> float:
    a, b = wall_line(w)
    return math.dist(a, b)


def wall_angle_deg(w: DesignElement) -> float:
    a, b = wall_line(w)
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def project_on_wall(w: DesignElement, xy: tuple[float, float]) -> tuple[float, float]:
    """(distance along the wall centreline from its start, perpendicular distance), both mm. Along may lie outside [0, L]."""
    (x0, y0), (x1, y1) = wall_line(w)
    L = math.dist((x0, y0), (x1, y1))
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    dx, dy = xy[0] - x0, xy[1] - y0
    return dx * ux + dy * uy, abs(-dx * uy + dy * ux)


def polygon_area_mm2(poly) -> float:
    s = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def preflight(elements: list[DesignElement], levels: dict | None = None) -> list[str]:
    """Everything that would make an export silently drop or invent geometry, as a list of problems.

    Fail-loudly contract: exporters call `require_clean`; nothing is skipped because it is inconvenient.
    """
    problems: list[str] = []
    ids: dict[str, int] = {}
    for e in elements:
        ids[e.id] = ids.get(e.id, 0) + 1
    problems += [f"duplicate element id {i} (x{n})" for i, n in ids.items() if n > 1]
    by = {e.id: e for e in elements}
    if levels is not None:
        for e in elements:
            if e.level not in levels:
                problems.append(f"{e.id}: level {e.level!r} is not in the level table")
    if not any(e.kind == "wall" for e in elements):
        problems.append("model has no walls")
    for e in elements:
        p = e.params
        if e.kind == "room":
            poly = p.get("polygon_mm") or []
            if len(poly) < 3:
                problems.append(f"{e.id}: room has no polygon (need >= 3 vertices, got {len(poly)})")
            elif polygon_area_mm2(poly) <= 0:
                problems.append(f"{e.id}: room polygon has zero area")
            if not p.get("clear_height_mm"):
                problems.append(f"{e.id}: room has no clear_height_mm")
        elif e.kind == "wall":
            missing = [k for k in ("x0_mm", "y0_mm", "x1_mm", "y1_mm", "thickness_mm", "height_mm") if p.get(k) in (None, "")]
            if missing:
                problems.append(f"{e.id}: wall lacks {missing}")
            elif wall_length(e) <= 0 or p["thickness_mm"] <= 0 or p["height_mm"] <= 0:
                problems.append(f"{e.id}: wall has a non-positive length, thickness or height")
        elif e.kind in ("door", "window"):
            host = by.get(e.host)
            if not e.host:
                problems.append(f"{e.id}: {e.kind} has no host wall")
            elif host is None or host.kind != "wall":
                problems.append(f"{e.id}: host {e.host!r} is not a wall in the model")
            elif host.level != e.level:
                problems.append(f"{e.id}: host {e.host} is on level {host.level}, the {e.kind} on {e.level}")
            elif not any(k not in host.params for k in ("x0_mm",)):
                along, perp = project_on_wall(host, e.placement[:2])
                L = wall_length(host)
                if perp > HOST_TOLERANCE_MM + 1e-6:
                    problems.append(f"{e.id}: {perp:.0f} mm from host {e.host} centreline (> {HOST_TOLERANCE_MM:.0f})")
                if along < -HOST_TOLERANCE_MM or along > L + HOST_TOLERANCE_MM:
                    problems.append(f"{e.id}: lies {along:.0f} mm along host {e.host} of length {L:.0f}")
            if not p.get("width_mm") or not p.get("height_mm"):
                problems.append(f"{e.id}: {e.kind} has no width/height")
        elif e.kind == "stair":
            boxes = p.get("tread_boxes_mm")
            if not boxes:
                problems.append(f"{e.id}: stair has no tread_boxes_mm")
            elif len(boxes) != p.get("treads"):
                problems.append(f"{e.id}: {len(boxes)} tread boxes but treads = {p.get('treads')}")
            for k in ("risers", "treads", "riser_mm", "tread_mm"):
                if not p.get(k):
                    problems.append(f"{e.id}: stair lacks {k}")
        elif e.kind == "railing":
            if not p.get("guard_height_mm"):
                problems.append(f"{e.id}: railing has no guard_height_mm")
            if not (p.get("profile_mm") or (e.size[0] > 0)):
                problems.append(f"{e.id}: railing has neither a profile nor a length")
        elif e.kind in ("column", "beam") and not all(v > 0 for v in e.size):
            problems.append(f"{e.id}: {e.kind} has a non-positive size {e.size}")
        elif e.kind == "slab" and not (p.get("polygon_mm") or p.get("profile_xz_mm") or all(v > 0 for v in e.size)):
            problems.append(f"{e.id}: slab has no polygon, profile or size")
        elif e.kind == "context" and not all(v > 0 for v in e.size):
            problems.append(f"{e.id}: context element has a non-positive size {e.size}")
        elif e.kind == "garden" and len(p.get("polygon_mm") or []) < 3:
            problems.append(f"{e.id}: garden has no polygon")
    return problems


def require_clean(elements: list[DesignElement], levels: dict | None = None) -> None:
    problems = preflight(elements, levels)
    if problems:
        raise ExchangeError(problems)
