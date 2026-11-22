"""Preview-only scene: our garden plus the sister plot's garden MIRRORED across the west line (layout-visualisation.json), for viewing.

Never a production artefact: every sister object is tagged `visualisation_only`, the scene is flagged, its renders carry a red VISUALISATION ONLY band in every image
and may only be written under a directory named `visualisation`. See guard.py for the production-side refusals.
"""
from __future__ import annotations

from pathlib import Path

from shapely.geometry import box as sbox

from . import build as B
from . import elements as E
from . import guard
from . import policy as P

R = E.R


def build_visualisation(layout, vis_layout, age=P.AGE_YEARS, season="summer", **kw):
    """-> Scene(visualisation_only=True): `layout`'s production objects + the mirrored sister garden (ids ld-vis-*) + the sister half of the shared fire pit."""
    if not vis_layout.get("visualisation_only"):
        raise ValueError("not a visualisation layout: visualisation_only is not set")
    ours = B.build_scene(layout, age=age, season=season, **kw)
    sis = B.build_scene(vis_layout, age=age, season=season, **kw)
    extra = []
    pitf = next((f for f in layout.get("features", []) if f.get("kind") == "firepit"), None)
    half = ours.spec.get("pit_half")
    if pitf and half:
        ax, sg = half
        r = pitf["diameter_m"] / 2
        cx, cy = pitf["center"]
        disc = sbox(cx - r, cy - r, cx + r, cy + r)
        grid = max((R(a["rect"]) for a in vis_layout.get("paved_areas", [])), key=lambda q: sbox(*q).intersection(disc).area, default=None)
        extra = E.firepit("ld-vis-" + pitf["id"], "vis-" + pitf["id"], pitf, ours.ground_z, half=(ax, -sg), grid_rect=grid)
    objs = list(ours.objects)
    for o in sis.objects + extra:
        o.meta["visualisation_only"] = True
        o.label = "VISUALISATION ONLY (sister plot): " + o.label
        if not o.id.startswith(guard.VIS_PREFIX):
            o.id = guard.VIS_PREFIX + o.id[3:] if o.id.startswith("ld-") else guard.VIS_PREFIX + o.id
        objs.append(o)
    ids = [(o.id, o.state) for o in objs]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate element ids in the visualisation scene")
    sc = B.Scene(objs, ours.context, ours.schedule, ours.warnings + ["sister plot: " + w for w in sis.warnings], age, ours.ground_z, "visualisation", dict(ours.spec, sister_objects=len(sis.objects) + len(extra)),
                 season, True)
    return sc


def stamp_band(jpg, text=guard.LABEL):
    """Burn a red band with the label into the top and bottom of an image (PIL). Every visualisation image carries it."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(jpg).convert("RGB")
    w, h = im.size
    bh = max(34, h // 18)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(bh * 0.55))
    except OSError:
        font = ImageFont.load_default()
    for y0 in (0, h - bh):
        d.rectangle([0, y0, w, y0 + bh], fill=(200, 16, 16))
        tw = d.textlength(text, font=font)
        d.text(((w - tw) / 2, y0 + bh * 0.2), text, fill=(255, 255, 255), font=font)
    im.save(jpg, quality=92)
    return jpg


def band_present(jpg):
    """True when the top and bottom rows of the image are the red band (independent pixel test used by the tests and the guard)."""
    from PIL import Image
    im = Image.open(jpg).convert("RGB")
    w, h = im.size
    def red(y):
        px = [im.getpixel((x, y)) for x in range(2, w, max(1, w // 40))]
        return sum(1 for r, g, b in px if r > 150 and g < 60 and b < 60) / len(px) > 0.8
    return red(2) and red(h - 3)
