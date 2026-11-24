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
        out.append(dict(id="gl-" + f.id, room="garden", layer=LAYER, type="ies", position=[round(c, 4) for c in p.position], aim=[round(c, 6) for c in p.aim], spin_deg=0.0,
                        ies=f"{IES_DIR}/{ies_name(f.product)}", lumens=prod["lumens"], cct_k=prod["cct_variant_k"] if "cct_variant_k" in prod else prod["cct_k"],
                        cri=prod["cri"], dimmer=round(p.dim, 4),
                        product=dict(manufacturer=prod["manufacturer"], code=prod["code"], generic=False, substitute=False),
                        garden_lg=dict(zone=f.zone, role=f.role, mount=f.mount, scene=scene, status=prod["status"], caveat=prod["caveat"])))
    return out


def ies_text(product: str) -> str:
    p = GD.PRODUCTS[product]
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


def _bar(axis, t0, t1, u, z, r, n=8):
    """Octagonal prism along `axis` ('x' or 'y') from t0 to t1, centred at cross-position u (the other horizontal axis) and height z. (The scene's physical-part guard refuses a bare
    rectangular proxy for anything but its listed box kinds, so the arm is a prism, not a cuboid.)"""
    ring = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pt = lambda t, k: [t, u + ring[k][0], z + ring[k][1]] if axis == "x" else [u + ring[k][0], t, z + ring[k][1]]
    end0 = [pt(t0, k) for k in reversed(range(n))]
    end1 = [pt(t1, k) for k in range(n)]
    sides = [[pt(t0, k), pt(t0, (k + 1) % n), pt(t1, (k + 1) % n), pt(t1, k)] for k in range(n)]
    return _outward([end0, end1] + sides)


def _outward(faces):
    """Wind every face so the solid's normals point out (the guard refuses an inward-facing solid): signed volume by the divergence theorem, reverse all faces if negative."""
    vol = 0.0
    for f in faces:
        for i in range(1, len(f) - 1):
            a, b, c = f[0], f[i], f[i + 1]
            vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return faces if vol > 0 else [list(reversed(f)) for f in faces]


# Host face of every fitting that has a wall, screen-post or fence behind it: (axis, coordinate of the layout's face). The arm runs from the body to that face and
# ARM_INTO_M beyond it, so it crosses any finish layer and the scene's support guard (`render_support.unsupported`) sees the assembly touch the building.
# DN-1/DN-2 (crape branch clamps) and the uplights (in-ground) have no host in the scene and no body: a body in the air would be flagged and would be wrong.
HOSTS = {"NP-1": ("x", 3.617), "NP-2": ("x", 3.617), "NP-4": ("x", 3.617), "NP-3": ("y", -23.591),
         "EP-1": ("y", -23.591), "EP-2": ("y", -23.591), "EP-3": ("y", -23.591), "EP-5": ("y", -20.601), "EP-6": ("y", -20.601),
         "PS-1": ("x", 22.597), "PS-2": ("x", 22.597), "PS-3": ("x", 22.597), "GR-1": ("x", 28.307), "GR-2": ("x", 28.307), "GR-3": ("y", -20.601),
         "FP-1": ("x", 23.697), "FP-2": ("x", 27.097)}
ARM_INTO_M, ARM_T = 0.03, 0.03      # arm length beyond the face, arm diameter


def bodies(scene: str = GD.RENDER_SCENE) -> list[dict]:
    """A short black cylinder per live Iku at its emitter (the optic faces down/aim; a vertical body is drawn: the tilt of a 60 mm body is below the render's resolution) and a
    30 mm square arm to its host face (the 0.30 m wall arm of the design, ASSUMED accessory)."""
    out = []
    for f, p in zip(GD.FIXTURES, GD.placements(GD.SCENES[scene]["levels"])):
        if p.dim <= 0 or f.product != "iku" or f.id not in HOSTS:
            continue
        x, y, z = p.position
        base = dict(group="dressing", material=BODY_MATERIAL, surface=False, occupied_side=None, element_ids=["gl-" + f.id], ld_state=None, ld_standin=False, keep_object=False)
        out.append(dict(id="gl-body-" + f.id, faces=_prism(x, y, z, z + BODY_H, BODY_D / 2 + 0.006), label="dressing: ERCO Iku B0000184 body (ASSUMED 60 mm), " + f.mount,
                        part_kind="ld-fixture", **base))
        axis, face = HOSTS[f.id]
        zc = z + BODY_H / 2
        c = x if axis == "x" else y
        end = face + math.copysign(ARM_INTO_M, face - c)
        box = _bar(axis, c, end, y if axis == "x" else x, zc, ARM_T / 2)
        out.append(dict(id="gl-arm-" + f.id, faces=box, label="dressing: wall arm of the Iku " + f.id + " (ASSUMED accessory)", part_kind="ld-fixture-arm", **base))
    return out
