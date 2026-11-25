"""Make the small JPGs for knowledge/refmatch/<room>/ and the local-only comparison sheets.

    python scripts/refmatch_sheet.py out/RM/cur out/RM/mock2

Committed (ours only): knowledge/refmatch/<room>/{cur,mock}_<view>.jpg and compare_<view>.jpg (current | mock-up).
Local only (NEVER committed): out/RM/sheets/<room>.jpg = current | mock-up | closest references, for showing the client.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REFDIR = ROOT.parent.parent / "lead" / "docs" / "brief" / "villa_01_guidelines_images"
W = 960
MAP = {  # room -> [(view, label)], closest references (ids)
    "living": ([("v03-street-lounge", "lounge TV wall"), ("v02-garden-living", "garden living")], ["image36", "image19", "image21"]),
    "media": ([("v08-cinema", "cinema")], ["image35", "image32", "image18"]),
    "bedroom": ([("n13-parents-day", "parents' bedroom, day"), ("v05-parents-bedroom", "parents' bedroom, dusk")], ["image7", "image6", "image5"]),
    "dining": ([("n01-dining-day", "dining"), ("n20-dining-side-day", "dining, party side")], ["image29", "image28", "image31"]),
}


def small(p, w=W):
    im = Image.open(p).convert("RGB")
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 * len(text) + 12, 20), fill=(0, 0, 0))
    d.text((6, 4), text, fill=(255, 255, 255))
    return im


def find_ref(i):
    for f in REFDIR.iterdir():
        if f.stem == i:
            return f


def main(cur, mock):
    for room, (views, refs) in MAP.items():
        out = ROOT / "knowledge" / "refmatch" / room
        out.mkdir(parents=True, exist_ok=True)
        rows = []
        for v, name in views:
            c, m = Path(cur) / f"{v}.png", Path(mock) / f"{v}.png"
            if not (c.exists() and m.exists()):
                continue
            ci, mi = small(c), small(m)
            ci.save(out / f"cur_{v}.jpg", quality=78)
            mi.save(out / f"mock_{v}.jpg", quality=78)
            pair = Image.new("RGB", (2 * W, ci.height))
            pair.paste(label(ci.copy(), f"{name}: current (production scene)"), (0, 0))
            pair.paste(label(mi.copy(), f"{name}: with proposals (mock-up copy)"), (W, 0))
            pair.save(out / f"compare_{v}.jpg", quality=78)
            rows.append(pair)
        if rows and REFDIR.exists():
            h = rows[0].height
            rr = []
            for i in refs:
                f = find_ref(i)
                if f:
                    im = Image.open(f).convert("RGB")
                    rr.append(label(im.resize((round(im.width * h / im.height), h)), f"reference {i}"))
            sheet = Image.new("RGB", (max(2 * W, sum(r.width for r in rr)), sum(r.height for r in rows) + (h if rr else 0)), (20, 20, 20))
            y = 0
            for r in rows:
                sheet.paste(r, (0, y)); y += r.height
            x = 0
            for r in rr:
                sheet.paste(r, (x, y)); x += r.width
            local = ROOT / "out" / "RM" / "sheets"
            local.mkdir(parents=True, exist_ok=True)
            sheet.save(local / f"{room}.jpg", quality=85)   # local only: contains reference images


if __name__ == "__main__":
    main(*sys.argv[1:3])
