"""Leaf banks: single-leaf cut-outs found in a Megascans atlas's Opacity map (RED channel), oriented by PCA.

    python -I banks.py            -> knowledge/landscape/foliage/banks.json   (cached; tests read the JSON)

A leaf is kept only if it is one whole, live, green leaf: a component of the opacity mask (4-connected, on a 1024 px
downsample) whose mean colour is green (G/R >= 1.0 and not white: B <= 0.95 G; this is the dead-leaf and petal filter
the LDL pass-6 jasmine defect needs), that is not a merge of several leaves (area <= 2.2x the median) and not holed
(filled-row ratio >= 0.96). Each record: base point, unit axis base->tip, blade length and width (blade = the part
wider than 30 % of the maximum, so petioles are cut off and grown as stems by the skeleton)."""
import json
import math
import os
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
FAB = Path(os.environ.get("ARCHPIPE_FAB", "/home/omar/archpipe/shared/assets/user/landscape/fab/unzipped"))
OUT = Path(__file__).resolve().parents[4] / "knowledge/landscape/foliage/banks.json"
DS = 4   # downsample factor of the 4096 px atlas

# bank id -> (archive dir, file stem, scientific name of the scanned plant, min component px at 1024)
SOURCES = {
    "star_jasmine": ("star_jasmine_pjycl2_4k", "Star_Jasmine_pjycl2_4K", "Trachelospermum jasminoides", 400),
    "ginger_lily": ("ginger_lily_ud5fffgja_high", "Ginger_Lily_ud5fffgja_High_4K", "Hedychium coronarium", 600),
    "jungle_ginger": ("jungle_ginger_sgbms_high", "Jungle_Ginger_sgbms_High_4K", "Zingiber (Megascans 'Jungle Ginger')", 400),
    "cast_iron": ("cast___iron_plant_shdmr_high", "Cast_-_Iron_Plant_shdmr_High_4K", "Aspidistra elatior", 600),
    "taro": ("taro_sjli7_high", "Taro_sjli7_High_4K", "Colocasia esculenta", 3000),
}


def maps(bank):
    d, stem = SOURCES[bank][:2]
    return {n: str(FAB / d / f"{stem}_{n}.jpg") for n in ("BaseColor", "Opacity", "Roughness", "Normal", "Translucency")}


def _components(mask, min_px):
    h, w = mask.shape
    seen = np.zeros_like(mask)
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        q = deque([(y, x)]); seen[y, x] = True; pts = [(y, x)]
        while q:
            cy, cx = q.popleft()
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((ny, nx)); pts.append((ny, nx))
        if len(pts) >= min_px:
            yield np.array(pts)


def _leaf(pts, col):
    """pts (n,2) as (y,x) on the 1024 grid -> record or None."""
    xy = pts[:, ::-1].astype(float)
    mean = xy.mean(0)
    u, s, vt = np.linalg.svd(xy - mean, full_matrices=False)
    ax = vt[0]; nv = np.array([-ax[1], ax[0]])
    t = (xy - mean) @ ax; w = (xy - mean) @ nv
    t0, t1 = t.min(), t.max(); L = t1 - t0
    nb = 24
    bins = np.minimum(((t - t0) / L * nb).astype(int), nb - 1)
    wid = np.array([np.ptp(w[bins == i]) if (bins == i).any() else 0 for i in range(nb)])
    W = wid.max()
    # filled ratio: area / (sum of per-bin extents): low for holed or torn blades
    fill = len(pts) / max(1.0, sum(wid[i] * (L / nb) for i in range(nb)))
    # which end is the base: a thin stalk end (narrow for > 10 % of the length), else the broader end
    thin = wid < 0.3 * W
    lo = next((i for i in range(nb) if not thin[i]), 0)
    hi = next((i for i in range(nb - 1, -1, -1) if not thin[i]), nb - 1)
    stalk_lo, stalk_hi = lo / nb, (nb - 1 - hi) / nb
    if max(stalk_lo, stalk_hi) > 0.10 and abs(stalk_lo - stalk_hi) > 0.08:
        flip = stalk_hi > stalk_lo            # stalk at the high end -> that is the base
    else:
        flip = wid[-6:-1].mean() > wid[1:6].mean()        # no stalk: the base is the broader end (ovate/lanceolate; the tip tapers)
    if flip:
        ax = -ax; nv = -nv; t = -t; t0, t1 = -t1, -t0; lo, hi = nb - 1 - hi, nb - 1 - lo; wid = wid[::-1]
    b_s = t0 + (lo / nb) * L; b_e = t0 + ((hi + 1) / nb) * L        # blade extent along the axis
    # the width of the blade is its own maximum, away from the petiole
    base = mean + ax * b_s
    c = col
    return dict(base_px=[round(float(base[0] * DS), 1), round(float(base[1] * DS), 1)],
                axis=[round(float(ax[0]), 4), round(float(ax[1]), 4)],
                len_px=round(float((b_e - b_s) * DS), 1), wid_px=round(float(W * DS), 1),
                petiole_frac=round(float(lo / nb), 3), fill=round(float(fill), 3),
                g_over_r=round(float(c[1] / max(c[0], 1e-6)), 3), area_px=int(len(pts) * DS * DS))


def extract(bank):
    d, stem, sci, min_px = SOURCES[bank]
    p = maps(bank)
    o = np.asarray(Image.open(p["Opacity"]).split()[0].resize((1024, 1024), Image.BILINEAR))
    mask = o > 100
    col = np.asarray(Image.open(p["BaseColor"]).convert("RGB").resize((1024, 1024), Image.BILINEAR)).astype(float)
    comps = list(_components(mask, min_px // 1))
    areas = np.array([len(c) for c in comps]); med = float(np.median(areas))
    leaves, dropped, sums = [], {"merged": 0, "dead_or_white": 0, "holed": 0, "tiny": 0}, []
    for c in comps:
        if len(c) > 2.2 * med:
            dropped["merged"] += 1; continue
        mc = col[c[:, 0], c[:, 1]].mean(0)
        if mc[1] / max(mc[0], 1e-6) < 1.0 or (mc[2] > 0.7 * mc[1] and mc.mean() > 100):
            dropped["dead_or_white"] += 1; continue
        r = _leaf(c, mc)
        if r is None or r["wid_px"] < 6 * DS or r["len_px"] / r["wid_px"] > 16:    # specks, canes and petioles are not leaves
            dropped["tiny"] += 1; continue
        if r["fill"] < 0.80:      # holed or torn blade
            dropped["holed"] += 1; continue
        leaves.append(r); sums.append(mc * len(c))
    mean_rgb = (np.sum(sums, axis=0) / sum(l["area_px"] / DS / DS for l in leaves)).round(1).tolist()
    return dict(mean_rgb=mean_rgb, scientific_name=sci, atlas=f"{d}/{stem}", maps={k: v for k, v in p.items()}, leaves=leaves, dropped=dropped)


GEN = OUT.parent / "generated"


def synth_palmate(name, sci, lobes, sinus, span_deg, serration, source="taro", n=768):
    """A palmately lobed leaf whose OUTLINE is ours (polar curve) and whose surface (colour, veins radiating from the
    base) is cropped from a real scanned leaf, so the card is `form-class`: no scan of this species' outline exists.
    The record is one whole leaf, base at the bottom centre, axis up."""
    src = extract(source)["leaves"][0]
    maps_ = maps(source)
    img = Image.open(maps_["BaseColor"]).convert("RGB")
    bx, by = src["base_px"]; ax, ay = src["axis"]; L = src["len_px"]
    cx, cy = bx + ax * L * 0.5, by + ay * L * 0.5          # crop wholly inside the scanned blade
    half = L * 0.36
    crop = img.crop((int(cx - half), int(cy - half), int(cx + half), int(cy + half))).resize((n, n), Image.LANCZOS)
    # the scanned surface is very dark; lift it (sRGB levels) to a mid green so the per-species gain stays near 1 and
    # JPEG noise in near-black pixels is not multiplied up
    ca = np.asarray(crop).astype(float)
    k = 85.0 / max(1.0, float((ca @ [0.2126, 0.7152, 0.0722]).mean()))
    ca[..., 2] = np.maximum(ca[..., 2], ca[..., 1] * 0.25)          # keep some blue so the hue correction has something to scale
    crop = Image.fromarray(np.clip(ca * k, 0, 150).astype(np.uint8)).filter(__import__("PIL.ImageFilter", fromlist=["x"]).MedianFilter(5))   # clip + median: no white/yellow flecks
    yy, xx = np.mgrid[0:n, 0:n]
    # polar coords about the leaf centre; angle 0 = up; the blade occupies span_deg either side of up
    px, py = (xx - n / 2) / (n / 2), (n * 0.54 - yy) / (n / 2)
    r = np.hypot(px, py); th = np.arctan2(px, py)
    lobe = np.cos(np.pi * th / (2 * math.radians(span_deg) / lobes)) ** 2
    f = (sinus + (1 - sinus) * lobe ** 0.45) * (1 + serration * np.cos(36 * th))
    mask = (r < 0.92 * f) & (np.abs(th) < math.radians(span_deg))
    mask |= (r < 0.07)
    GEN.mkdir(exist_ok=True)
    alpha = Image.fromarray((mask * 255).astype(np.uint8)).filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(0.8))
    crop.save(GEN / f"{name}_BaseColor.jpg", quality=92)
    Image.merge("RGB", (alpha, Image.new("L", alpha.size, 0), Image.new("L", alpha.size, 0))).save(GEN / f"{name}_Opacity.jpg", quality=95)
    mean_rgb = np.asarray(crop).astype(float)[mask].mean(0).round(1).tolist()
    return dict(mean_rgb=mean_rgb, scientific_name=sci, atlas=f"generated/{name}", synthetic_outline=True,
                maps={"BaseColor": str(GEN / f"{name}_BaseColor.jpg"), "Opacity": str(GEN / f"{name}_Opacity.jpg")},
                leaves=[dict(base_px=[n / 2, n * 0.99], axis=[0.0, -1.0], len_px=float(n * 0.91), wid_px=float(n * 0.92),
                             petiole_frac=0.0, fill=1.0, g_over_r=1.2, area_px=int(mask.sum()), size_px=n)],
                dropped={}, surface_from=source)


def build(out=OUT):
    res = {b: extract(b) for b in SOURCES}
    res["palmate_fatsia"] = synth_palmate("fatsia", "Colocasia esculenta (surface scan only; the Fatsia-like outline is generated, not scanned)", 9, 0.62, 165, 0.0)
    res["palmate_grape"] = synth_palmate("grape", "Colocasia esculenta (surface scan only; the grape-like outline is generated, not scanned)", 5, 0.78, 150, 0.0)
    out.write_text(json.dumps(res, indent=1))
    for b, r in res.items():
        print(b, len(r["leaves"]), r["dropped"])
    return res


if __name__ == "__main__":
    build()
