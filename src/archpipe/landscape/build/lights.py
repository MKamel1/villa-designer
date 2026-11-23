"""Garden lights of the decided layout for the production scene (lane LG).

The design lives in `lightcalc.garden` (positions, products, scene levels, every check). This module only turns it into scene records:
one `ies` light per fitting at the levels of `garden.RENDER_SCENE`, a small black body per fitting, and the IES files the render job needs.
"""
from __future__ import annotations

import math
from pathlib import Path

from ...lightcalc import garden as GD

LAYER = "evening-garden"
IES_DIR = "garden"                 # relative to the scene's ies directory
BODY_MATERIAL = "black-metal"      # the production scene's own material
BODY_D, BODY_H = 0.076, 0.060      # Iku: 76 mm round opening (its IES); body height ASSUMED 60 mm (datasheet dimensions not transcribed)


def ies_name(product: str) -> str:
    return f"{GD.PRODUCTS[product]['code'].lower()}.ies"


def lights(scene: str = GD.RENDER_SCENE) -> list[dict]:
    """Scene light records. `lumens` is the product's rated flux, `dimmer` the scene level (the renderer multiplies them), so a view can still dim the layer."""
    levels = GD.SCENES[scene]["levels"]
    out = []
    for f, p in zip(GD.FIXTURES, GD.placements(levels)):
        if p.dim <= 0:
            continue
        prod = GD.PRODUCTS[f.product]
        generic = f.product != "iku"
        out.append(dict(id="gl-" + f.id, room="garden", layer=LAYER, type="ies", position=[round(c, 4) for c in p.position], aim=[round(c, 6) for c in p.aim], spin_deg=0.0,
                        ies=f"{IES_DIR}/{ies_name(f.product)}", lumens=prod["lumens"], cct_k=prod["cct_variant_k"] if "cct_variant_k" in prod else prod["cct_k"],
                        cri=prod["cri"], dimmer=round(p.dim, 4),
                        product=dict(manufacturer=prod["manufacturer"], code=prod["code"], generic=generic, **({} if generic else dict(substitute=False))),
                        garden_lg=dict(zone=f.zone, role=f.role, mount=f.mount, scene=scene, status=prod["status"], caveat=prod["caveat"])))
    return out


def ies_text(product: str) -> str:
    p = GD.PRODUCTS[product]
    if p["ies"] is None:
        return GD.up_assumed_ies()
    return Path(p["ies"]).read_text(encoding="utf-8", errors="replace").lstrip("﻿")


def write_ies(light: dict, target: Path) -> None:
    """Write the IES a `garden/...` light names (called by the scene writer next to the scene file)."""
    code = light["product"]["code"]
    key = next(k for k, v in GD.PRODUCTS.items() if v["code"] == code)
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    Path(target).write_text(ies_text(key), encoding="utf-8", newline="\n")


def _prism(cx, cy, z0, z1, r, n=12):
    ring = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    top = [[x, y, z1] for x, y in ring]
    bot = [[x, y, z0] for x, y in reversed(ring)]
    sides = [[[ring[i][0], ring[i][1], z0], [ring[(i + 1) % n][0], ring[(i + 1) % n][1], z0], [ring[(i + 1) % n][0], ring[(i + 1) % n][1], z1], [ring[i][0], ring[i][1], z1]] for i in range(n)]
    return [top, bot] + sides


def bodies(scene: str = GD.RENDER_SCENE) -> list[dict]:
    """One short black cylinder per live Iku at its emitter (the optic faces down/aim; a vertical body is drawn: the tilt of a 60 mm body is below the render's resolution)."""
    out = []
    for f, p in zip(GD.FIXTURES, GD.placements(GD.SCENES[scene]["levels"])):
        if p.dim <= 0 or f.product != "iku":
            continue
        x, y, z = p.position
        out.append(dict(id="gl-body-" + f.id, group="dressing", material=BODY_MATERIAL, faces=_prism(x, y, z, z + BODY_H, BODY_D / 2 + 0.006),
                        label="dressing: ERCO Iku B0000184 body (ASSUMED 60 mm), " + f.mount, part_kind="ld-fixture", surface=False, occupied_side=None, element_ids=["gl-" + f.id],
                        ld_state=None, ld_standin=False, keep_object=False))
    return out
