"""Keeps the VISUALISATION-ONLY sister-plot garden out of every production path.

The sister plot is not our land and not our design (garden brief 2026-11-22). A scene that carries it is flagged `visualisation_only`, every object of it is
tagged, and each production seam (export to the villa scene, the schedule, the element table, the checks, the receipts) refuses or filters it.
"""
from __future__ import annotations

VIS_PREFIX = "ld-vis-"
LABEL = "VISUALISATION ONLY: sister plot, not our land or design"


class VisualisationOnlyError(RuntimeError):
    pass


def is_vis(obj):
    return bool(obj.meta.get("visualisation_only")) or obj.id.startswith(VIS_PREFIX)


def has_vis(scene):
    return bool(getattr(scene, "visualisation_only", False)) or any(is_vis(o) for o in scene.objects)


def refuse(scene, where):
    """Raise when `scene` carries any visualisation-only object: call at the top of every production seam."""
    if has_vis(scene):
        raise VisualisationOnlyError("%s: the scene carries visualisation-only (sister plot) objects; they never enter %s" % (where, where))


def production_only(scene):
    """The same scene without any visualisation-only object (what schedules, quantities and checks may see)."""
    if not has_vis(scene):
        return scene
    from dataclasses import replace
    return replace(scene, objects=[o for o in scene.objects if not is_vis(o)], visualisation_only=False)
