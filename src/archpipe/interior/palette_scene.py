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


CONTRAST_MIN, CONTRAST_MAX = 0.5, 2.0   # POLICY: how far the look-alike's pattern may be stretched to the maker's contrast


def lookalike_luma_cv(folder: Path) -> float:
    """Coefficient of variation of the look-alike colour map's luma (the pattern contrast the maker image is compared with)."""
    import numpy as np
    from PIL import Image
    f = sorted(folder.glob("*_Color.jpg"))[0]
    a = np.asarray(Image.open(f).convert("RGB").resize((256, 256)), dtype=float) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).reshape(-1, 3)
    y = lin @ np.array([0.2126, 0.7152, 0.0722])
    return float(y.std() / max(y.mean(), 1e-9))


def _hex_lin(h: str):
    h = h.lstrip("#")
    return [_srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)]


def load_colours(root: Path = finishes.PALETTE_DIR) -> dict:
    """id -> {hex, basis}: the stated product colour where the maker page does not give a render colour. ESTIMATES."""
    f = root / "render-colours.json"
    return json.loads(f.read_text())["colours"] if f.exists() else {}


# Soft-goods colour words -> sRGB hex. OUR ESTIMATES of what the maker's colour name looks like on a sofa; the look-alike
# image supplies only the weave, never the colour (a linen scan's own mean is sky blue). Longest phrase wins.
NAME_HEX = {"dark brown": "#4a3426", "dark green": "#3d4a36", "light brown": "#b8987a", "dark grey": "#4a4a48",
            "yellow-brown": "#b88a4a", "light beige": "#d9ccb4", "light grey-brown": "#b0a698", "light grey": "#c4c1ba",
            "grey-brown": "#8f8272", "dark beige": "#a89578", "unbleached": "#e6dfcf", "off-white": "#e6e0d2",
            "natural": "#c0aa84", "brown": "#6b4a35", "grey": "#8a8a88", "beige": "#c9b89a", "olive": "#6b6a3f",
            "taupe": "#a39786", "green": "#5a6a4a", "white": "#ece8e0", "cream": "#e4dac4"}


def name_hex(colour_name: str | None) -> str | None:
    low = (colour_name or "").lower()
    for k in sorted(NAME_HEX, key=len, reverse=True):
        if k in low:
            return NAME_HEX[k]
    return None


def item_spec(item: dict, library_root: Path, colours: dict | None = None) -> dict:
    colours = load_colours() if colours is None else colours
    la = item.get("lookalike")
    p = item["product"]
    lrv = p.get("lrv")
    hx = (colours.get(item["id"]) or {}).get("hex")
    if not hx and item.get("group") == "soft":
        hx = name_hex(p.get("colour_name"))
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
    out = dict(kind="principled", asset=la["id"], base_rgb=[round(c, 4) for c in base], reflectance=round(refl, 4),
               roughness=0.5, tile_m=round(tile_m, 4),
               note=f"LOOK-ALIKE ({la['maker_site']} {la['id']}, {la['licence']}) standing for {p.get('maker')} "
                    f"{p.get('range') or p.get('name')} {p.get('colour_code') or ''}; tile_m {tile_m} m from {basis}; "
                    f"colour {'from ' + ((colours.get(item['id']) or {}).get('basis') or 'the stated hex') if hx else 'the look-alike own mean'}"
                    f"{', reflectance = maker LRV ' + str(lrv) if lrv is not None else ''}")
    # veining/pattern contrast: draw the look-alike toward (or away from) its own mean so its luma spread matches the maker's image
    # (swatches only: a product photo's spread is its shading and backdrop, not the cloth's pattern)
    ent = colours.get(item["id"]) or {}
    cv_maker = ent.get("luma_cv") if ent.get("mode") == "swatch" else None
    if cv_maker and cv_maker > 0:
        out["contrast"] = round(min(CONTRAST_MAX, max(CONTRAST_MIN, cv_maker / max(lookalike_luma_cv(folder), 1e-6))), 3)
    return out


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
