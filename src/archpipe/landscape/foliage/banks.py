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
GEN = OUT.parent / "generated"
DS = 4   # downsample factor of the 4096 px atlas

# bank id -> (archive dir, file stem, scientific name of the scanned plant, min component px at 1024)
SOURCES = {
    "star_jasmine": ("star_jasmine_pjycl2_4k", "Star_Jasmine_pjycl2_4K", "Trachelospermum jasminoides", 400),
    "ginger_lily": ("ginger_lily_ud5fffgja_high", "Ginger_Lily_ud5fffgja_High_4K", "Hedychium coronarium", 600),
    "jungle_ginger": ("jungle_ginger_sgbms_high", "Jungle_Ginger_sgbms_High_4K", "Zingiber (Megascans 'Jungle Ginger')", 400),
    "cast_iron": ("cast___iron_plant_shdmr_high", "Cast_-_Iron_Plant_shdmr_High_4K", "Aspidistra elatior", 600),
    "taro": ("taro_sjli7_high", "Taro_sjli7_High_4K", "Colocasia esculenta", 3000),
    # client Fab downloads 2026-11-22 (assets_manifest.json). 5th field: opening radius (px at 1024) that cuts a leaflet
    # off the twig/rachis it touches in a sprig atlas; 0 for atlases of separate leaves
    "australian_laurel": ("australian_laurel_pf5hkss2_4k", "Australian_Laurel_pf5hkss2_4K", "Pittosporum undulatum", 400, 0),
    "weeping_fig": ("weeping_fig_pbxka2_4k", "Weeping_Fig_pbxkA2_4K", "Ficus benjamina", 150, 2),
    "grape_vine": ("common_grape_vine_qhmj12_4k", "Common_Grape_Vine_qhmj12_4K", "Vitis vinifera", 1200, 0),
    "tree_philodendron": ("tree_philodendron_qirh62_4k", "Tree_Philodendron_qirh62_4K", "Thaumatophyllum bipinnatifidum", 1500, 0),
    "elephant_ear": ("elephant_ear_qhnhw2_4k", "Elephant_Ear_qhnhW2_4K", "Alocasia (Megascans 'Elephant Ear')", 10000, 0),
    "african_flag": ("african_flag_okyefdhh2_4k", "African_Flag_okyefdhh2_4K", "Hedychium/Canna-type strap (Megascans 'African Flag')", 600, 0),
    "chinese_wisteria": ("chinese_wisteria_qfgfw2_4k", "Chinese_Wisteria_qfgfW2_4K", "Wisteria sinensis", 120, 2),
}


def maps(bank):
    d, stem = SOURCES[bank][:2]
    return {n: str(FAB / d / f"{stem}_{n}.jpg") for n in ("BaseColor", "Opacity", "Roughness", "Normal", "Translucency")}


def _erode(m, r):
    for _ in range(r):
        m = m.copy(); m[1:] &= m[:-1].copy(); m[:-1] &= m[1:].copy(); m[:, 1:] &= m[:, :-1].copy(); m[:, :-1] &= m[:, 1:].copy()
    return m


def _grow(pts, within, r, shape):
    """Dilate a component's points by r (4-neighbour) but only into the original mask: undoes the erosion."""
    m = np.zeros(shape, bool); m[pts[:, 0], pts[:, 1]] = True
    for _ in range(r):
        n = m.copy(); n[1:] |= m[:-1]; n[:-1] |= m[1:]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]
        m = n & within
    return np.argwhere(m)


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
    d, stem, sci, min_px = SOURCES[bank][:4]
    open_px = SOURCES[bank][4] if len(SOURCES[bank]) > 4 else 0
    p = maps(bank)
    o = np.asarray(Image.open(p["Opacity"]).split()[0].resize((1024, 1024), Image.BILINEAR))
    mask = o > 100
    col = np.asarray(Image.open(p["BaseColor"]).convert("RGB").resize((1024, 1024), Image.BILINEAR)).astype(float)
    comps = list(_components(_erode(mask, open_px) if open_px else mask, min_px // 1))
    if open_px:
        comps = [_grow(c, mask, open_px, mask.shape) for c in comps]
    areas = np.array([len(c) for c in comps]); med = float(np.median(areas))
    leaves, dropped, sums, kept = [], {"merged": 0, "dead_or_white": 0, "holed": 0, "tiny": 0}, [], []
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
        leaves.append(r); sums.append(mc * len(c)); kept.append(c)
    if leaves:     # ragged fragments: a strap blade much shorter than its siblings is a torn piece, not a leaf; a card > 2.2x the median length is a stem or a fused pair
        ml = float(np.median([l["len_px"] for l in leaves]))
        keep = [i for i, l in enumerate(leaves) if 0.45 * ml <= l["len_px"] <= 2.2 * ml or len(leaves) < 4]
        dropped["ragged_or_oversize"] = len(leaves) - len(keep)
        leaves = [leaves[i] for i in keep]; sums = [sums[i] for i in keep]; kept = [kept[i] for i in keep]
    if len(SOURCES[bank]) > 4 and leaves:     # isolation: a card whose box also holds another kept leaf would show it twice (sprig atlases)
        lab = np.zeros((1024, 1024), np.int32)
        for i, c in enumerate(kept):
            lab[c[:, 0], c[:, 1]] = i + 1
        ok = []
        for i, l in enumerate(leaves):
            bx, by = l["base_px"][0] / DS, l["base_px"][1] / DS; ax, ay = l["axis"]; L, W = l["len_px"] / DS, l["wid_px"] / DS * 1.2
            y0, y1 = int(max(0, by - L - W)), int(min(1024, by + L + W)); x0, x1 = int(max(0, bx - L - W)), int(min(1024, bx + L + W))
            yy, xx = np.mgrid[y0:y1, x0:x1]
            t = (xx - bx) * ax + (yy - by) * ay; n = -(xx - bx) * ay + (yy - by) * ax
            inside = (t >= 0) & (t <= L) & (np.abs(n) <= W / 2)
            sub = lab[y0:y1, x0:x1][inside]
            other = ((sub > 0) & (sub != i + 1)).sum()
            if other <= 0.04 * max(1, (sub == i + 1).sum()):
                ok.append(i)
        dropped["not_isolated"] = len(leaves) - len(ok)
        leaves = [leaves[i] for i in ok]; sums = [sums[i] for i in ok]; kept = [kept[i] for i in ok]
    mean_rgb = (np.sum(sums, axis=0) / sum(l["area_px"] / DS / DS for l in leaves)).round(1).tolist()
    maps_ = {k: v for k, v in p.items()}
    if len(SOURCES[bank]) > 4:      # client 2026-11-22 atlases: keep only the chosen leaves opaque, so a card never shows a neighbour or a twig
        m = np.zeros((1024, 1024), bool)
        for c in kept:
            m[c[:, 0], c[:, 1]] = True
        full = np.kron(m, np.ones((DS, DS), bool))
        for _ in range(DS):       # the 1024 mask is a block approximation: grow it to the true 4096 edge (opacity decides the edge)
            n = full.copy(); n[1:] |= full[:-1]; n[:-1] |= full[1:]; n[:, 1:] |= full[:, :-1]; n[:, :-1] |= full[:, 1:]; full = n
        red = np.asarray(Image.open(p["Opacity"]).split()[0])
        GEN.mkdir(exist_ok=True)
        z = Image.fromarray((red * full).astype(np.uint8))
        z = Image.merge("RGB", (z, Image.new("L", z.size, 0), Image.new("L", z.size, 0)))
        z.save(GEN / f"{bank}_Opacity.jpg", quality=95)
        maps_["Opacity"] = str(GEN / f"{bank}_Opacity.jpg")
    return dict(mean_rgb=mean_rgb, scientific_name=sci, atlas=f"{d}/{stem}", maps=maps_, leaves=leaves, dropped=dropped)


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
