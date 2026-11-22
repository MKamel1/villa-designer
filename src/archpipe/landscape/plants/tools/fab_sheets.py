"""Compose fab_preview.py renders into one sheet per archive.
    python -m archpipe.landscape.plants.tools.fab_sheets RENDER_DIR SHEET_DIR
plant: row 1 single plant 5 m az 0/90/180/270; row 2 same at 15 m; row 3 3 m x 3 m drift 5 m az0/az90, 15 m az0/az90;
       row 4 near views (single plant, drift).
lawn:  row 1 continuous surface 5 m az0/az90, 15 m az0/az90; row 2 instanced patches likewise; row 3 near views (surface, patches)."""
import sys
from pathlib import Path
from PIL import Image
out, dst = Path(sys.argv[1]), Path(sys.argv[2]); dst.mkdir(parents=True, exist_ok=True)
for st in sorted(out.glob("*.stats.json")):
    sid = st.name[:-len(".stats.json")]
    lawn = '"kind": "lawn"' in st.read_text()
    if lawn:
        names = [f"{sid}_su_d{d}_az{a}" for d in (5, 15) for a in (0, 90)] + [f"{sid}_dr_d{d}_az{a}" for d in (5, 15) for a in (0, 90)] + [f"{sid}_su_close", f"{sid}_dr_close"]
    else:
        names = [f"{sid}_s_d{d}_az{a}" for d in (5, 15) for a in (0, 90, 180, 270)] + [f"{sid}_dr_d{d}_az{a}" for d in (5, 15) for a in (0, 90)] + [f"{sid}_s_close", f"{sid}_dr_close"]
    tiles = [Image.open(out / f"{n}.png").convert("RGB") for n in names]
    w, h = tiles[0].size
    rows = (len(tiles) + 3) // 4
    s = Image.new("RGB", (4 * w, rows * h), (255, 255, 255))
    for i, t in enumerate(tiles):
        s.paste(t, ((i % 4) * w, (i // 4) * h))
    s.resize((4 * w * 3 // 4, rows * h * 3 // 4)).save(dst / f"{sid}.jpg", quality=85)
