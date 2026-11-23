"""Sample boards: each swatch is a true-scale window onto the look-alike map (same per-channel mean match to the
stated colour and LRV as the scene material). A 300 mm window; a 100 mm bar is drawn. Labelled as look-alikes.
Not a ray-traced render: the swatch is the scene's texture and scale without lighting.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import finishes, palette_scene as PS

PX_PER_MM = 1.6
WIN_MM = 300
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(sz, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, sz)


def swatch(item: dict, library_root: Path) -> Image.Image:
    spec = PS.item_spec(item, library_root)
    if not item.get("lookalike"):                      # flat finish: the stated colour at its LRV
        lin = np.array(spec["base_rgb"]) * 0 + np.array(spec["base_rgb"])
        srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
        return Image.new("RGB", (int(WIN_MM * PX_PER_MM),) * 2, tuple(int(round(c * 255)) for c in srgb))
    folder = Path(library_root) / "materials" / item["lookalike"]["id"]
    img = Image.open(sorted(folder.glob("*_Color.jpg"))[0]).convert("RGB")
    a = np.asarray(img, dtype=float) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    mean = lin.reshape(-1, 3).mean(0)
    refl, base = spec["reflectance"], np.array(spec["base_rgb"])
    target = base * refl / max(PS._lum(base), 1e-9)
    out = np.clip(lin * (target / np.maximum(mean, 1e-9)), 0, 1)
    srgb = np.where(out <= 0.0031308, out * 12.92, 1.055 * np.power(out, 1 / 2.4) - 0.055)
    full = Image.fromarray((srgb * 255).astype("uint8"))
    tile_mm = spec["tile_m"] * 1000
    win_src = int(round(full.width * WIN_MM / tile_mm))      # source pixels that span 300 mm of the real world
    size = int(WIN_MM * PX_PER_MM)
    # tile the source if the window is larger than one image (small formats), then crop
    reps = max(1, -(-win_src // full.width))
    big = Image.new("RGB", (full.width * reps, full.height * reps))
    for i in range(reps):
        for j in range(reps):
            big.paste(full, (i * full.width, j * full.height))
    return big.crop((0, 0, win_src, win_src)).resize((size, size), Image.LANCZOS)


def _hint_hex(it: dict) -> str:
    import re
    m = re.search(r"#[0-9a-fA-F]{6}", it.get("render_hint", ""))
    return m.group(0) if m else "#bbbbbb"


def chip(hexcol: str) -> Image.Image:
    size = int(WIN_MM * PX_PER_MM)
    return Image.new("RGB", (size, size), hexcol)


def _wrap(d, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def label_lines(it: dict) -> list[str]:
    p = it["product"]
    la = it.get("lookalike")
    fmt = p.get("format_mm") or {}
    ftxt = " x ".join(str(fmt[k]) for k in ("w", "l", "t") if fmt.get(k)) + " mm" if fmt else ""
    ls = [f"{it['slot']}  ({it.get('use', '')})",
          f"{p.get('maker')} - {p.get('range') or p.get('name')}",
          f"{p.get('colour_name') or ''} {p.get('colour_code') or ''}".strip(),
          " | ".join(x for x in (ftxt, p.get("finish"), f"LRV {p['lrv']}" if p.get("lrv") is not None else "") if x)]
    if la:
        tm, basis = finishes.texture_scale_m(it)
        ls.append(f"LOOK-ALIKE: {la['maker_site']} {la['id']} ({la['licence']}), not the product")
        ls.append(f"texture 1 image = {tm:.2f} m ({basis})")
    else:
        ls.append("flat colour (paint/lacquer), LRV-scaled; chip colour is an estimate" if it.get("slot") in finishes.FLAT_SLOTS
                  else "colour chip: estimate (" + str(it.get("render_hint", "")) + ")")
    eg = it.get("egypt") or {}
    ls.append("Egypt: " + (eg.get("supplier") or "GAP - " + str(eg.get("gap") or "unknown").split(". ")[0][:80]))
    return [l for l in ls if l.strip()]


def board(pal: dict, group: str, library_root: Path, out: Path, cols: int = 4) -> Path:
    items = [i for i in pal["items"] if i.get("group") == group and (i.get("lookalike") or i.get("render_hint")
                                                                       or i.get("slot") in finishes.FLAT_SLOTS)]
    sw = int(WIN_MM * PX_PER_MM)
    cw, ch = sw + 40, sw + 230
    rows = -(-len(items) // cols)
    title_h = 90
    im = Image.new("RGB", (cols * cw + 20, rows * ch + title_h + 20), (246, 243, 238))
    d = ImageDraw.Draw(im)
    d.text((20, 18), f"Palette {pal['palette']}: {pal['name']} - {group} finishes", fill=(30, 30, 30), font=_font(30, True))
    d.text((20, 58), "Swatches are 300 mm windows at true scale (bar = 100 mm). Textures are CC0 look-alikes, not the named products.",
           fill=(90, 90, 90), font=_font(15))
    for n, it in enumerate(items):
        x, y = 20 + (n % cols) * cw, title_h + (n // cols) * ch
        try:
            s = swatch(it, library_root) if (it.get("lookalike") or it.get("slot") in finishes.FLAT_SLOTS) else chip(_hint_hex(it))
        except Exception as e:  # a missing texture must show, not vanish
            s = Image.new("RGB", (sw, sw), (200, 60, 60)); ImageDraw.Draw(s).text((10, 10), "MISSING " + str(e)[:40], fill=(255, 255, 255))
        im.paste(s, (x, y))
        bar = int(100 * PX_PER_MM)
        d.rectangle([x + 8, y + sw - 18, x + 8 + bar, y + sw - 10], fill=(255, 255, 255), outline=(0, 0, 0))
        yy = y + sw + 8
        for i, l in enumerate(label_lines(it)):
            for w in _wrap(d, l, _font(13, i == 0), sw)[:2]:
                d.text((x, yy), w, fill=(20, 20, 20) if i < 2 else (70, 70, 70), font=_font(13, i == 0)); yy += 17
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out
