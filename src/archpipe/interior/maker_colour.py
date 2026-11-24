"""Mean colour of a MAKER'S OWN swatch or product photo, in linear space (bpy-free; Pillow + numpy).

Two sampling modes: "swatch" (the whole image is the material) and "product" (a product photo on a plain backdrop:
only pixels that differ from the border colour count). Used by scripts/source_maker_colours.py; the guard that a chosen
product has a sourced colour lives in scripts/build_chosen.py and tests/interior/test_chosen.py.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

_Y = np.array([0.2126, 0.7152, 0.0722])


def _lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def _srgb(m):
    return np.where(m <= 0.0031308, m * 12.92, 1.055 * np.maximum(m, 0) ** (1 / 2.4) - 0.055)


def foreground_mask(a, tol=0.06):
    """True where an sRGB [0,1] HxWx3 image differs from its border backdrop colour by more than `tol` (max channel)."""
    h, w = a.shape[:2]
    k = max(2, min(h, w) // 40)
    border = np.concatenate([a[:k].reshape(-1, 3), a[-k:].reshape(-1, 3), a[:, :k].reshape(-1, 3), a[:, -k:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    return np.abs(a - bg).max(axis=2) > tol


def sample(path, mode="swatch", max_side=512):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):          # composite transparency onto mid grey instead of reading its hidden RGB
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    im.thumbnail((max_side, max_side))
    a = np.asarray(im, dtype=float) / 255.0
    if mode == "product":
        m = foreground_mask(a)
        if m.mean() < 0.02:
            raise ValueError(f"{path}: backdrop mask kept {m.mean():.1%} of the image; use mode 'swatch' or a better image")
    elif mode == "swatch":
        m = np.ones(a.shape[:2], bool)
    else:
        raise ValueError(mode)
    lin = _lin(a)[m]
    mean = lin.mean(0)
    y = lin @ _Y
    hx = "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in _srgb(mean))
    return dict(hex=hx, mean_linear=[round(float(v), 4) for v in mean], luma=round(float(mean @ _Y), 4),
                luma_cv=round(float(y.std() / max(y.mean(), 1e-9)), 3), coverage=round(float(m.mean()), 3))


def demo():
    a = np.full((100, 100, 3), 0.95)
    a[30:70, 30:70] = (0.8, 0.2, 0.2)
    Image.fromarray((a * 255).astype("uint8")).save("/tmp/_mc.png")
    prod, sw = sample("/tmp/_mc.png", "product"), sample("/tmp/_mc.png")
    assert prod["hex"] == "#cc3333" and prod["coverage"] < 0.2, prod     # backdrop excluded
    assert sw["luma"] > prod["luma"]                                     # swatch mode keeps the backdrop
    print("ok")


if __name__ == "__main__":
    demo()
