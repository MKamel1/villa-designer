"""Turn a finish palette into scene.json material specs (finishes only; geometry and lights untouched).

Texture scale comes from finishes.texture_scale_m (product format), colour from the look-alike's own mean
(linear) rescaled to the product's LRV where the maker publishes one.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import finishes

# slot (or slot-variant id suffix) -> scene material names it overrides. Only finishes with a product behind them.
SLOT_TO_MATERIALS = {
    "floor-living": ["travertine"],
    "floor-gf": ["oak-floor"],
    "floor-wet": ["marble-wet"],
    "bath-tile": ["marble-bath", "marble-ensuite"],
    "worktop": ["marble-white"],
    "joinery-timber": ["walnut", "walnut-grain-x", "walnut-grain-y"],
    "joinery-light": ["oak", "oak-grain-x"],
    "door": ["door-oak"],
    "kitchen-front": ["greige-lacquer"],
    "wall-paint": ["plaster-warm-white"],
    "garden-paving": ["paving"],
}
GRAIN = {"walnut-grain-x": "x", "walnut-grain-y": "y", "walnut": "z", "oak": "z", "oak-grain-x": "x",
         "door-oak": "z", "oak-floor": "x"}


def _srgb_to_lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lum(rgb) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def lookalike_mean_linear(folder: Path):
    """Mean linear RGB of the look-alike's colour map (bpy-free; Pillow + numpy are in the venv)."""
    import numpy as np
    from PIL import Image
    f = sorted(folder.glob("*_Color.jpg"))[0]
    a = np.asarray(Image.open(f).convert("RGB").resize((256, 256)), dtype=float) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return [float(x) for x in lin.reshape(-1, 3).mean(0)]


def _hex_lin(h: str):
    h = h.lstrip("#")
    return [_srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)]


def load_colours(root: Path = finishes.PALETTE_DIR) -> dict:
    """id -> {hex, basis}: the stated product colour where the maker page does not give a render colour. ESTIMATES."""
    f = root / "render-colours.json"
    return json.loads(f.read_text())["colours"] if f.exists() else {}


def item_spec(item: dict, library_root: Path, colours: dict | None = None) -> dict:
    colours = load_colours() if colours is None else colours
    la = item.get("lookalike")
    p = item["product"]
    lrv = p.get("lrv")
    hx = (colours.get(item["id"]) or {}).get("hex")
    if la is None:                                   # flat finish (paint, lacquer): colour + LRV, no image
        if not hx:
            raise ValueError(f"{item['id']}: flat finish needs a render colour in render-colours.json")
        base = _hex_lin(hx)
        refl = lrv / 100.0 if lrv is not None else _lum(base)
        base = [min(1.0, c * refl / max(_lum(base), 1e-9)) for c in base]
        return dict(kind="principled", base_rgb=[round(c, 4) for c in base], reflectance=round(refl, 4), roughness=0.85,
                    note=f"flat colour for {p.get('maker')} {p.get('range') or p.get('name')} {p.get('colour_code') or ''} "
                         f"({'LRV ' + str(lrv) if lrv is not None else 'reflectance estimated from the colour'})")
    tile_m, basis = finishes.texture_scale_m(item)
    folder = Path(library_root) / "materials" / la["id"]
    mean = lookalike_mean_linear(folder)
    if hx:
        base = _hex_lin(hx)
        refl = lrv / 100.0 if lrv is not None else _lum(base)
        base = [min(1.0, c * refl / max(_lum(base), 1e-9)) for c in base]
    else:
        refl = lrv / 100.0 if lrv is not None else _lum(mean)
        k = refl / max(_lum(mean), 1e-9)
        base = [min(1.0, c * k) for c in mean] if lrv is not None else mean
    return dict(kind="principled", asset=la["id"], base_rgb=[round(c, 4) for c in base], reflectance=round(refl, 4),
                roughness=0.5, tile_m=round(tile_m, 4),
                note=f"LOOK-ALIKE ({la['maker_site']} {la['id']}, {la['licence']}) standing for {p.get('maker')} "
                     f"{p.get('range') or p.get('name')} {p.get('colour_code') or ''}; tile_m {tile_m} m from {basis}; "
                     f"colour {'from the stated hex (estimate)' if hx else 'the look-alike own mean'}"
                     f"{', reflectance = maker LRV ' + str(lrv) if lrv is not None else ''}")


def scene_names(item: dict) -> list[str]:
    """Scene material names this item stands in for (only the finishes the production scene actually draws)."""
    iid, slot = item["id"], item.get("slot", "")
    if slot in SLOT_TO_MATERIALS:
        return SLOT_TO_MATERIALS[slot]
    low = iid.lower()
    if "rug" in low and "living" in low:
        return ["rug"]
    if "throw" in low and "parents" in low:
        return ["throw-taupe"]
    if "cushion" in low and "parents" in low:
        return ["sage-fabric"]
    return []


def palette_materials(pal: dict, library_root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    colours = load_colours()
    for it in pal["items"]:
        names = scene_names(it)
        if not names:
            continue
        spec = item_spec(it, library_root, colours)
        for n in names:
            s = dict(spec)
            if n in GRAIN and "asset" in s:
                s["grain_axis"] = GRAIN[n]
            out.setdefault(n, s)
    return out


def write_palette_scene(base_scene: Path, palette: dict, out: Path, library_root: Path) -> dict:
    d = json.loads(Path(base_scene).read_text())
    ov = palette_materials(palette, library_root)
    for n, spec in ov.items():
        old = d["materials"][n]
        spec = dict(spec)
        # keep kind-specific fields the finish does not own
        for k in ("metallic",):
            if k in old:
                spec[k] = old[k]
        d["materials"][n] = spec
    d["id"] = f"{d.get('id', 'scene')}-palette-{palette['palette']}"
    Path(out).write_text(json.dumps(d))
    return ov
