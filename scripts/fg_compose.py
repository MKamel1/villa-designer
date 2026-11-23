"""FG: compose the rubric sheet (5 m row, 15 m row, close row) from blender_build.py `sheet` PNGs; optional --ref adds the reference photo
(for grading only; the --out of a compare image must NOT be committed). usage: fg_compose.py DIR TAG OUT.jpg [--ref REF.jpg]"""
import glob, sys
from PIL import Image, ImageDraw

d, tag, out = sys.argv[1:4]
ref = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else None
rows = [("5 m (cropped to 1.5x plant)", "d5p0"), ("15 m (cropped)", "d15p0"), ("close", "d1p6"), ("close", "d3p0")]
T = 480
sheet = Image.new("RGB", (4 * T, 3 * T), (40, 40, 40))
r = 0
for label, key in rows:
    fs = sorted(glob.glob("%s/%s_%s_az*.png" % (d, tag, key)))
    if not fs: continue
    for i, f in enumerate(fs[:4]):
        im = Image.open(f).convert("RGB"); im.thumbnail((T, T)); sheet.paste(im, (i * T, r * T))
    ImageDraw.Draw(sheet).text((6, r * T + 4), label, fill=(255, 255, 0))
    r += 1
    if r == 3: break
if ref:
    R = Image.open(ref).convert("RGB"); R.thumbnail((4 * T // 2, 3 * T // 2))
    big = Image.new("RGB", (4 * T + R.width + 10, 3 * T), (20, 20, 20)); big.paste(sheet, (0, 0)); big.paste(R, (4 * T + 10, 0)); sheet = big
sheet.save(out, quality=88)
