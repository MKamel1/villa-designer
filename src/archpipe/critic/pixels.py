"""Pixel checks: R3 (vertical-edge deviation), R4 (subject exposure), R10 (edge bands, seams),
R12 (mid-tone colour cast). numpy + Pillow only (no OpenCV in the project venv).

Every check returns a dict {score, message, achieved, ...}; thresholds come from the rubric
`pixel` block and the POLICY cards, never from the caller's data.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

DEFAULTS = dict(
    analysis_width_px=960,
    clipped_level=0.985,
    crushed_luma=0.03,
    band_min_fraction=0.015,
    band_max_luma=0.03,
    band_max_std=0.02,
    seam_min_contrast=0.06,
    seam_coherence=0.70,
    seam_z=8.0,
    r3_gradient_percentile=97.0,
)


def load_rgb(path_or_image, width: int = 960) -> np.ndarray:
    im = path_or_image if isinstance(path_or_image, Image.Image) else Image.open(path_or_image)
    im = im.convert("RGB")
    if im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def luma(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


# ---------------------------------------------------------------- R4 subject mask
def subject_mask(shape, subjects, fallback_fraction=0.60, min_union=0.15):
    """Boolean mask (h, w). Union of subject screen boxes (y up, fractions, may run off frame);
    falls back to the central fallback_fraction rectangle when the union is missing or < min_union."""
    h, w = shape
    mask = np.zeros((h, w), bool)
    for s in subjects or []:
        box = s.get("screen")
        if not box or len(box) != 4:
            continue
        x0, y0, x1, y1 = box
        x0, x1 = max(0.0, min(1.0, x0)), max(0.0, min(1.0, x1))
        y0, y1 = max(0.0, min(1.0, y0)), max(0.0, min(1.0, y1))
        if x1 - x0 <= 0 or y1 - y0 <= 0:
            continue
        mask[int(round((1 - y1) * h)):int(round((1 - y0) * h)), int(round(x0 * w)):int(round(x1 * w))] = True
    basis = "subject boxes"
    if mask.mean() < min_union:
        mask[:] = False
        m = (1 - fallback_fraction) / 2
        mask[int(m * h):int((1 - m) * h), int(m * w):int((1 - m) * w)] = True
        basis = "central 60 % x 60 % fallback"
    return mask, basis


def check_r4(rgb: np.ndarray, subjects, p=DEFAULTS):
    mask, basis = subject_mask(rgb.shape[:2], subjects)
    px = rgb[mask]
    clipped = float((px.max(axis=1) >= p["clipped_level"]).mean())
    crushed = float((luma(px) <= p["crushed_luma"]).mean())
    ok = clipped <= 0.01 and crushed <= 0.02
    warn = clipped <= 0.03 and crushed <= 0.06
    score = 2 if ok else 1 if warn else 0
    return dict(score=score, achieved=max(clipped, crushed), clipped=clipped, crushed=crushed,
                mask_fraction=float(mask.mean()), basis=basis,
                message=f"subject mask ({basis}, {mask.mean():.0%} of frame): clipped {clipped:.1%} (limit 1 %), "
                        f"crushed {crushed:.1%} (limit 2 %)")


# ---------------------------------------------------------------- R12 colour cast
def check_r12(rgb: np.ndarray):
    """Mid-tone (luma 0.25-0.75) opponent excesses; render_qa cast magnitude kept for reference."""
    y = luma(rgb)
    mids = rgb[(y > 0.25) & (y < 0.75)]
    if len(mids) < 0.01 * y.size:
        return dict(score=None, achieved=None, message="fewer than 1 % mid-tone pixels: colour cast not evaluable")
    r, g, b = mids.mean(axis=0)
    cool = float(b - r)
    green = float(g - (r + b) / 2)
    cyan = float((g + b) / 2 - r)
    warm = float(r - b)
    m = (r + g + b) / 3
    cast = math.sqrt(((r - m) ** 2 + (g - m) ** 2 + (b - m) ** 2) / 3)
    # Amended on the tuning half (rubric amendments A1): warm rooms are normal, so warm uses the
    # render_qa cast magnitude (existing 0.10 fail limit); cool and cyan are the stricter limits.
    # Green is reported but does not score: foliage makes every garden view green.
    cool_ex, cyan_ex, warm_ex = max(cool, 0.0), max(cyan, 0.0), (cast if r > b else 0.0)
    if cool_ex <= 0.03 and cyan_ex <= 0.05 and warm_ex <= 0.09:
        s = 2
    elif cool_ex <= 0.06 and cyan_ex <= 0.08 and warm_ex <= 0.10:
        s = 1
    else:
        s = 0
    return dict(score=s, achieved=max(cool_ex, cyan_ex, warm_ex), cool=cool, green=green, cyan=cyan, warm=warm,
                cast=cast,
                message=f"mid-tone cool {cool:+.3f} green {green:+.3f} cyan {cyan:+.3f} warm {warm:+.3f} "
                        f"(limits: cool 0.03, cyan 0.05, warm cast 0.09; green informational)")


# ---------------------------------------------------------------- R10 edge bands and seams
def check_edge_bands(rgb: np.ndarray, p=DEFAULTS):
    """A band = contiguous run of near-solid very dark or very bright columns/rows from a frame edge,
    at least band_min_fraction of that dimension wide, while the frame centre is not itself dark."""
    y = luma(rgb)
    h, w = y.shape
    centre = y[h // 4:3 * h // 4, w // 4:3 * w // 4]
    found = {}
    if np.median(centre) < 0.08:       # whole frame dark: not a band, R4 owns that
        return dict(found=found, message="frame too dark to separate a band")

    def run(profile_mean, profile_std, n):
        k = 0
        for i in range(n):
            m, s = profile_mean[i], profile_std[i]
            dark = m <= p["band_max_luma"] and s <= p["band_max_std"]
            white = m >= 0.985 and s <= p["band_max_std"]
            if dark or white:
                k += 1
            else:
                break
        return k

    cm, cs = y.mean(axis=0), y.std(axis=0)
    rm, rs = y.mean(axis=1), y.std(axis=1)
    for side, k, n in (("left", run(cm, cs, w), w), ("right", run(cm[::-1], cs[::-1], w), w),
                       ("top", run(rm, rs, h), h), ("bottom", run(rm[::-1], rs[::-1], h), h)):
        if k / n >= p["band_min_fraction"]:
            found[side] = k / n
    return dict(found=found, message=("edge band: " + ", ".join(f"{s} {f:.1%}" for s, f in found.items()))
                if found else "no solid edge band")


def check_seam(rgb: np.ndarray, p=DEFAULTS):
    """Full-height hard discontinuity: a column where the same-sign luma step between neighbouring
    columns is >= seam_min_contrast on >= seam_coherence of the rows, and that is an outlier
    (robust z >= seam_z) against the other columns. Real wall corners rarely span the full height."""
    y = luma(rgb)
    # smooth lightly along columns so single bright/dark pixels do not dominate
    d = y[:, 2:] - y[:, :-2]                     # (h, w-2) step across 2 px
    out = []
    for sign in (1, -1):
        s = sign * d
        coherent = (s >= p["seam_min_contrast"]).mean(axis=0)
        med = np.median(coherent)
        mad = np.median(np.abs(coherent - med)) + 1e-3
        z = (coherent - med) / (1.4826 * mad)
        for x in np.where((coherent >= p["seam_coherence"]) & (z >= p["seam_z"]))[0]:
            out.append((int(x + 1), float(coherent[x])))
    # horizontal seams: same on rows
    dv = y[2:, :] - y[:-2, :]
    for sign in (1, -1):
        s = sign * dv
        coherent = (s >= p["seam_min_contrast"]).mean(axis=1)
        med = np.median(coherent)
        mad = np.median(np.abs(coherent - med)) + 1e-3
        z = (coherent - med) / (1.4826 * mad)
        for yy in np.where((coherent >= p["seam_coherence"]) & (z >= p["seam_z"]))[0]:
            out.append((-int(yy + 1), float(coherent[yy])))
    return dict(found=out, message=f"{len(out)} full-length hard seam(s)" if out else "no full-length seam")


def check_r10_pixel(rgb, p=DEFAULTS):
    bands = check_edge_bands(rgb, p)
    seam = check_seam(rgb, p)
    # Seams are informational: the pixel seam detector could not separate the v27 seam from real
    # wall edges on the tuning half (A2), so the VLM judges seams. Bands gate.
    n = len(bands["found"])
    score = 2 if n == 0 else 0
    return dict(score=score, achieved=float(n), bands=bands["found"], seams=seam["found"],
                message="; ".join([bands["message"], seam["message"]]))


# ---------------------------------------------------------------- R3 vertical-edge deviation
def _box_mean(a: np.ndarray, k: int) -> np.ndarray:
    n = 2 * k + 1
    c = np.pad(a, ((k, k), (k, k)), mode="edge").cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n])[:a.shape[0], :a.shape[1]] / (n * n)


def check_r3_pixels(rgb: np.ndarray, p=DEFAULTS, nbins: int = 6, min_support: int = 3000):
    """Lean of straight near-vertical edges. Structure tensor over 9x9 windows; keep pixels whose
    gradient is coherent (>0.9, i.e. a straight edge, not foliage) and within 8 deg of horizontal.
    Median gradient angle per column bin; only bins with >= min_support such pixels count. A level
    shift-corrected rectilinear camera keeps verticals vertical in every bin, so the largest |median|
    is the lean. Furniture that is itself slanted also shows up here (reported, not excused)."""
    y = luma(rgb)
    gx = (y[1:-1, 2:] - y[1:-1, :-2]) / 2
    gy = (y[2:, 1:-1] - y[:-2, 1:-1]) / 2
    jxx, jyy, jxy = _box_mean(gx * gx, 4), _box_mean(gy * gy, 4), _box_mean(gx * gy, 4)
    tr = jxx + jyy
    d = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4 * jxy ** 2, 0))
    coh = d / (tr + 1e-12)
    ang = 0.5 * np.degrees(np.arctan2(2 * jxy, jxx - jyy))
    sel = (coh > 0.9) & (np.sqrt(np.maximum(tr, 0)) > 0.03) & (np.abs(ang) <= 8)
    h, w = sel.shape
    xs = np.broadcast_to(np.arange(w), sel.shape)
    meds = []
    for i in range(nbins):
        m = sel & (xs >= i * w / nbins) & (xs < (i + 1) * w / nbins)
        if m.sum() >= min_support:
            meds.append(float(np.median(ang[m])))
    if not meds:
        return dict(score=None, achieved=None, message="too few straight vertical edges to measure lean")
    dev = max(abs(m) for m in meds)
    score = 2 if dev <= 0.5 else 1 if dev <= 1.5 else 0
    return dict(score=score, achieved=dev, bins=meds,
                message=f"straight vertical-edge lean {dev:.2f} deg over {len(meds)} column bins (limit 0.5)")



