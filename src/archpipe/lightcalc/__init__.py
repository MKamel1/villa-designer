"""Lighting calculation engine (lane L6): polygon rooms, Radiance total light, scenes, checks.

Pure standard library apart from the imports of `archpipe.photometry` / `archpipe.radiance`
helpers. See docs/lanes/L6-lighting-engine.md.
"""
from .direct import Placement, direct_illuminance  # noqa: F401
from .metrics import GridStats, grid_stats  # noqa: F401
