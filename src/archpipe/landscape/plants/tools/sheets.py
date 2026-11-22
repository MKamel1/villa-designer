"""Montage <id>_d{5,15}_az{0,90,180,270}.png from asset_preview.py into asset-previews-style sheets.
    python -m archpipe.landscape.plants.tools.sheets OUT_DIR SHEET_DIR"""
import sys
from pathlib import Path
from PIL import Image
out, dst = Path(sys.argv[1]), Path(sys.argv[2]); dst.mkdir(parents=True, exist_ok=True)
for ids in sorted({p.name.rsplit('_d', 1)[0] for p in out.glob('*_d5_az0.png')}):
    try:
        tiles = [Image.open(out / f'{ids}_d{d}_az{a}.png').convert('RGB') for d in (5, 15) for a in (0, 90, 180, 270)]
    except FileNotFoundError:
        continue
    w, h = tiles[0].size
    s = Image.new('RGB', (4 * w, 2 * h))
    for i, t in enumerate(tiles): s.paste(t, ((i % 4) * w, (i // 4) * h))
    s.resize((4 * w * 3 // 4, 2 * h * 3 // 4)).save(dst / f'{ids}.jpg', quality=85)
