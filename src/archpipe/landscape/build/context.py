"""Neighbour and site context for previews of OUR design, taken from the environment model (`archpipe.villa_env`, mm, same model frame as the layout).

Shown: our house massing at its modelled height, the sister villa massing and its core, the east / rear neighbours (12 m, plot mirrored ASSUMED in villa_env),
the street slab, and the plot boundary fences that the layout's own walls do not already cover. Never shown: any detail the model does not hold (the sister plot's
garden, windows' glass, planting). The sister's yard is drawn as a neutral labelled ground, not as a garden. Heights are villa_env's (basement -3.0, roof +6.0).
"""
from __future__ import annotations

from shapely.geometry import box as sbox
from shapely.ops import unary_union

from ... import villa_env as V

PICK = {  # villa_env element id -> (material, what)
    "sister": ("ctx", "sister villa + its apartment, mirrored massing (BRIEF)"),
    "sister-front": ("ctx", "sister's terrace, mirrored"),
    "core-B-shared": ("ctx", "shared basement core"),
    "neighbour-east": ("ctx", "east neighbour massing, 12 m (BRIEF), plot mirrored ASSUMED"),
    "neighbour-rear": ("ctx", "rear neighbour massing, 12 m (BRIEF), plot mirrored ASSUMED"),
    "neighbour-rear-east": ("ctx", "rear-east neighbour massing, 12 m, ASSUMED"),
    "street": ("ctx-street", "street slab at +-0.00, width ASSUMED 10 m"),
    "fence-street": ("wall-render", "plot fence, 4.00 m from basement (BRIEF)"),
    "fence-east": ("wall-render", "plot fence, 4.00 m from basement (BRIEF)"),
    "fence-rear": ("wall-render", "plot fence, 4.00 m from basement (BRIEF)"),
    "fence-west": ("wall-render", "plot fence, 4.00 m from basement (BRIEF)"),
}
GROUND_NOTE = ("neutral ground outside our yard: the model holds the street, the neighbour massing and the plot fence only; the sister yard is a slab with no garden. "
               "It is a labelled neutral surface, not surveyed ground.")


def _rect(e):
    xs = [p[0] for p in e["pts"]]; ys = [p[1] for p in e["pts"]]
    return [min(xs) / 1000, min(ys) / 1000, max(xs) / 1000, max(ys) / 1000]


def site_context(walls=()):
    """-> list of ctx boxes (rect, z0, z1, material, label). `walls` = layout wall rects: a plot fence they already cover is cut away, the rest (the sister half) is kept."""
    els = {e["id"]: e for e in V.spec()["elements"]}
    cover = unary_union([sbox(*w) for w in walls] or [sbox(0, 0, 0, 0)])
    out = []
    for eid, (mat, what) in PICK.items():
        e = els[eid]
        r = _rect(e)
        geo = sbox(*r).difference(cover) if eid.startswith("fence") else sbox(*r)
        parts = [g for g in (geo.geoms if hasattr(geo, "geoms") else [geo]) if g.area > 1e-4]
        for k, g in enumerate(parts):
            out.append(dict(id="ctx-site-%s%s" % (eid, "" if k == 0 else "-%d" % k), rect=list(g.bounds), z0=e["z0"] / 1000, z1=e["z1"] / 1000, material=mat,
                            label="context from villa_env '%s': %s" % (eid, what)))
    return out


def ground_plan():
    """(plot rect, axis y) in metres: ours is y > axis, the sister yard y < axis; both inside the plot (fence outer faces)."""
    p = V.plot()
    return [v / 1000 for v in p], V.AXIS_Y / 1000


def house_height(g):
    """Our house stacks basement -3.0, GF, apartment, roof +6.0 in villa_env (not the 6 m the build assumed before)."""
    return V.ROOF / 1000 - g
