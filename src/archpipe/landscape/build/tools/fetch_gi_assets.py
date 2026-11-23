"""Fetch the free (CC0) Poly Haven textures lane GI uses for the production garden into the shared material library.

    python -I fetch_gi_assets.py [LIBRARY_MATERIALS_DIR]
Poly Haven: every asset is CC0 (https://polyhaven.com/license). Files are written with the library's own naming
(`<id>_Color.jpg`, `<id>_Roughness.jpg`, `<id>_NormalGL.jpg`) which `villa_scene.add_material` reads. Run once per machine."""
import json
import sys
import urllib.request
from pathlib import Path

TEXTURES = {"wood_chip_path": "mulch for the planting beds", "park_dirt": "bare soil / ground between built surfaces",
            "white_rough_plaster": "boundary-wall render"}
MAPS = {"Diffuse": "Color", "Rough": "Roughness", "nor_gl": "NormalGL"}


def _open(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "asset-fetch/1.0"}), timeout=120)


def fetch(lib: Path, res="2k"):
    for tid in TEXTURES:
        files = json.load(_open("https://api.polyhaven.com/files/" + tid))
        d = lib / tid
        d.mkdir(parents=True, exist_ok=True)
        for src, dst in MAPS.items():
            url = files[src][res]["jpg"]["url"]
            (d / ("%s_%s.jpg" % (tid, dst))).write_bytes(_open(url).read())
        print("fetched", tid, "->", d)


if __name__ == "__main__":
    fetch(Path(sys.argv[1] if len(sys.argv) > 1 else "~/archpipe/assets/library/materials").expanduser())
