"""Validation of the design model (DesignElement v0 plus the L2 semantics documented in docs/lanes/L2-model.md)."""
from __future__ import annotations

import math

from ..contracts import DesignElement

SCHEMA = "archpipe-model/1"
REVISION = 2        # additive: storey, floor, ceiling, type kinds; layers, handing, sizes, net areas (lane M)
KINDS = ("room", "wall", "slab", "door", "window", "stair", "railing", "column", "beam", "furniture", "fixture",
         "luminaire", "device", "plant", "garden", "context", "storey", "floor", "ceiling", "type")
LEVELS = ("B", "GF", "L1", "ROOF", "SITE")

# params every element of a kind must carry (checked for presence, not for value).
REQUIRED_PARAMS = {
    "room": ("polygon_mm", "area_m2", "clear_height_mm", "occupancy"),
    "wall": ("thickness_mm", "height_mm", "x0_mm", "y0_mm", "x1_mm", "y1_mm"),
    "door": ("width_mm", "height_mm"),
    "window": ("width_mm", "height_mm", "sill_mm"),
    "stair": ("risers", "treads", "riser_mm", "tread_mm", "width_mm"),
    "railing": ("guard_height_mm",),
    "luminaire": ("photometry", "flux_lm", "fixture_kind"),
    "plant": ("species",),
    "furniture": ("type",),
    "storey": ("elevation_scene_mm", "ours"),
    "floor": ("finish_code", "polygon_mm", "layers"),
    "ceiling": ("ceiling_kind", "polygon_mm", "height_mm", "height_min_mm", "height_max_mm", "layers"),
    "type": ("for_kind", "shared", "occurrences"),
}
# kinds whose occurrences must reference a shared type (params.type_id), once the model is complete
TYPED = ("door", "window", "furniture", "luminaire")


def _finite(seq) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in seq)


def validate(elements: list[DesignElement]) -> list[str]:
    """Return a list of problems; empty means the model is well formed."""
    errs: list[str] = []
    ids: dict[str, int] = {}
    for e in elements:
        ids[e.id] = ids.get(e.id, 0) + 1
    errs += [f"duplicate id {i} x{n}" for i, n in ids.items() if n > 1]
    rooms = {e.id[5:] for e in elements if e.kind == "room"}
    for e in elements:
        if not e.id:
            errs.append("element with empty id")
        if e.kind not in KINDS:
            errs.append(f"{e.id}: unknown kind {e.kind!r}")
        if e.level not in LEVELS:
            errs.append(f"{e.id}: unknown level {e.level!r}")
        if len(e.placement) != 3 or not _finite(e.placement):
            errs.append(f"{e.id}: placement must be three finite numbers")
        if len(e.size) != 3 or not _finite(e.size):
            errs.append(f"{e.id}: size must be three finite numbers")
        if any(v < 0 for v in e.size):
            errs.append(f"{e.id}: negative size")
        for p in REQUIRED_PARAMS.get(e.kind, ()):
            if p not in e.params:
                errs.append(f"{e.id}: {e.kind} lacks param {p!r}")
        if e.host and e.host not in ids:
            errs.append(f"{e.id}: host {e.host!r} is not an element")
        if e.room and e.kind != "room" and e.room not in rooms and e.room not in ("", "yard", "garden"):
            errs.append(f"{e.id}: room {e.room!r} is not a room element")
    return errs
