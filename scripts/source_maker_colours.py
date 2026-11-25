"""Take the render colour of every CHOSEN product from the maker's own image or published colour data.

Run: PYTHONPATH=src python scripts/source_maker_colours.py [--cache DIR]
For each chosen item the maker's swatch/product photo is downloaded (cache only; images are the makers', never committed),
its mean colour sampled in linear space (archpipe.interior.maker_colour) and written to
knowledge/products/finishes/render-colours.json with the image URL, its sha256 and the sampling mode.
Never tint by eye: a chosen product with no entry here fails scripts/build_chosen.py and tests/interior/test_chosen.py.
"""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path

from archpipe.interior import maker_colour

OUT = Path(__file__).resolve().parents[1] / "knowledge/products/finishes/render-colours.json"
CHOSEN = OUT.with_name("chosen.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# item id -> (image url, mode) for hard finishes (a swatch is the material). Soft goods resolve og:image of the product page.
SWATCH = {
    "C-floor-living": ("https://www.marazzi.it/app/uploads/collezioni/mystone-gris-fleury-mlgy/marazzi_mystone_gris_fleury_mlgy-800x400.jpg", "swatch"),
    "C-floor-gf": ("https://res.cloudinary.com/havwoods-global/image/upload/ar_1.4429824561403508,c_fill,g_center,w_1479/f_auto/q_auto/v1721144786/image_%7C_hw7470_%7C_panel_%7C_photo.jpg", "swatch"),
    "C-floor-wet": ("https://www.marazzigroup.com/app/uploads/collezioni/mystone-limestone20-m7sq/marazzi_mystone_limestone20_m7sq.jpg", "swatch"),
    "C-bath-tile": ("https://www.marazzigroup.com/app/uploads/collezioni/grande-marble-look-m0g3/marazzi_grande_marble_look_m0g3-800x800.jpg", "swatch"),
    "B-kitchen-front": ("https://res.cloudinary.com/dozlb75sf/image/upload/v1679331548/FENIX%20Colours/Thumb/FENIX_0719_BEIGE_LUXOR_thumb_eloyrz.jpg", "swatch"),
    # EGGER: Q1180_RO is the edging colour-matched to H1180; its own page image is a narrow end-grain strip, so the Halifax Oak board
    # decor image (H1180 ST37) on the maker's CDN stands for it
    "B-joinery-light": ("https://cdn.egger.com/img/pim/8854365372446/8854523117598/original.png", "swatch"),
    "C-joinery-light": ("https://cdn.egger.com/img/pim/8854365372446/8854523117598/original.png", "swatch"),
    "C-joinery-timber": ("https://cdn.egger.com/img/pim/8860203974686/8860204007454/original.png", "swatch"),
    # R (client references 2026-11-24): Marazzi Grande Marble Look swatches from the maker's own collection page; the brass is the maker's
    # finish chip 727 (Gessi finiturethumb)
    "R-worktop": ("https://www.marazzigroup.com/app/uploads/collezioni/grande-marble-look-m7gf/marazzi_grande_marble_look_m7gf-400x800.jpg", "swatch"),
    "R-backsplash": ("https://www.marazzigroup.com/app/uploads/collezioni/grande-marble-look-m7gf/marazzi_grande_marble_look_m7gf-400x800.jpg", "swatch"),
    "R-bath-panel": ("https://www.marazzigroup.com/app/uploads/collezioni/grande-marble-look-m7gf/marazzi_grande_marble_look_m7gf-400x800.jpg", "swatch"),
    "R-floor-ensuite": ("https://www.marazzigroup.com/app/uploads/collezioni/grande-marble-look-m0zk/marazzi_grande_marble_look_m0zk-400x800.jpg", "swatch"),
    "R-brass-bath-mixer": ("https://gessistorage.azureedge.net/finiturethumb/727.jpg", "swatch"),   # Gessi's own finish chip 727 (the product photo's mean is shading and highlights: #9d9376, Y 0.29)
    "A-joinery-timber": ("https://cdn.egger.com/img/pim/8854421438494/8854545432606/original.png", "swatch"),   # H3734 ST9 decor, the image the maker page offers as its Download
    "B-worktop": ("https://assetstools.cosentino.com/api/v1/bynder/color/CKC/detalle/CKC-thumb.jpg?w=700&h=700&auto=compress%2Cformat", "swatch"),
    "B-backsplash": ("https://assetstools.cosentino.com/api/v1/bynder/color/CKC/detalle/CKC-thumb.jpg?w=700&h=700&auto=compress%2Cformat", "swatch"),
    # Rizzoli titles: the publisher's own cover image (Penguin Random House cover service, linked from the Rizzoli page)
    "C-book-wearstler-evocative": ("https://images.penguinrandomhouse.com/cover/9780847866038", "product"),
    "C-book-wearstler-synchronicity": ("https://images.penguinrandomhouse.com/cover/9780847873425", "product"),
    "C-book-van-duysen-private": ("https://images.penguinrandomhouse.com/cover/9780847899555", "product"),
    "C-book-loyzaga": ("https://images.penguinrandomhouse.com/cover/9780847873678", "product"),
    # UNIQLO's og:image for these two is a model photo; the product page's own colour chip is the garment cloth
    "C-garment-merino-olive": ("https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/469426/chip/goods_56_469426_chip.jpg", "swatch"),
    "C-garment-linen-trouser": ("https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/463857/chip/goods_57_463857_chip.jpg", "swatch"),
}
# Dulux publishes the hex on the colour page ("Hex #f9f1e1"); no image to sample.
PUBLISHED_HEX = {"B-wall-paint": "#f9f1e1", "C-wall-paint": "#8b8074"}
EXTRA = Path(__file__).with_name("maker_swatches_extra.json")   # id -> [url, mode] for makers needing a manual route


def fetch(url, dest):
    subprocess.run(["curl", "-sL", "-m", "60", "-A", UA, "-o", str(dest), url], check=True)
    if not dest.stat().st_size:
        raise RuntimeError("empty download " + url)


def og_image(page, cache):
    f = cache / (hashlib.md5(page.encode()).hexdigest()[:10] + ".html")
    fetch(page, f)
    t = f.read_text(errors="ignore")
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', t) or \
        re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', t)
    return m.group(1).replace("&amp;", "&") if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(Path.home() / ".cache/archpipe-maker-images"))
    ap.add_argument("--only", nargs="*", help="resample only these item ids (leaves every other entry untouched)")
    a = ap.parse_args()
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    chosen = json.loads(CHOSEN.read_text())["slots"]
    items = [s["item"] for s in chosen.values()]
    items += [i for i in json.loads(OUT.with_name("R.json").read_text())["items"] if i["id"] not in {x["id"] for x in items}]   # R before it is chosen
    swatch = dict(SWATCH, **(json.loads(EXTRA.read_text()) if EXTRA.exists() else {}))
    doc = json.loads(OUT.read_text())
    items += [i for i in json.loads(OUT.with_name("A.json").read_text())["items"] if i["id"] == "A-joinery-timber" and i["id"] not in {x["id"] for x in items}]
    for it in items:
        iid, page = it["id"], it["source"]["url"]
        if a.only and iid not in a.only:
            continue
        if iid in PUBLISHED_HEX:
            doc["colours"][iid] = dict(hex=PUBLISHED_HEX[iid], basis="maker page publishes this hex (Dulux colour page 'Hex' row)",
                                       url=page, mode="published-hex", sampled=str(date.today()))
            continue
        url, mode = swatch.get(iid) or (og_image(page, cache), "product")
        if not url:
            print("NO IMAGE", iid, page)
            continue
        f = cache / (hashlib.md5(url.encode()).hexdigest()[:10] + ".img")
        if not f.exists():
            fetch(url, f)
        r = maker_colour.sample(f, mode)
        doc["colours"][iid] = dict(hex=r["hex"], basis=f"maker image, mean linear colour, mode {mode}", url=url, page=page,
                                   mode=mode, image_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),
                                   mean_linear=r["mean_linear"], luma=r["luma"], luma_cv=r["luma_cv"], coverage=r["coverage"],
                                   sampled=str(date.today()))
        print(f"{iid:36} {r['hex']} Y={r['luma']:.3f} cv={r['luma_cv']:.2f} cov={r['coverage']:.2f} {mode}")
    doc["note"] = ("Render colours of the CHOSEN products, sampled from the maker's own image (or the maker's published hex): "
                   "scripts/source_maker_colours.py. Entries whose basis is 'estimate...' are palette-board items that were not chosen.")
    OUT.write_text(json.dumps(doc, indent=1) + "\n")


if __name__ == "__main__":
    main()
