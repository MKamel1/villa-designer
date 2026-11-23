"""FG: sha256 manifest of the client-downloaded Fab zips + Poly Haven textures -> knowledge/landscape/foliage/assets_manifest.json"""
import hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
FAB = Path("/home/omar/archpipe/shared/assets/user/landscape/fab")
PH = Path("/home/omar/archpipe/shared/assets/user/landscape/polyhaven-tex")
DL = (ROOT / "knowledge/landscape/foliage/DOWNLOADS.md").read_text()
FABLIC = "Fab: Quixel Megascans, licences Personal+Professional, price 0.0 (listing API 2026-11-22); Fab EULA: commercial/private use, any tool, no standalone redistribution (zips not in git)"
NEW = ["australian_laurel_pf5hkss2_4k", "spotted_laurel_pecjs2_4k", "weeping_fig_pbxka2_4k", "common_grape_vine_qhmj12_4k",
       "tree_philodendron_qirh62_4k", "elephant_ear_qhnhw2_4k", "african_flag_okyefdhh2_4k", "chinese_wisteria_qfgfw2_4k",
       "spotted_laurel_sfdik_high", "spotted_laurel_sfdik_raw", "banyan_bark_tfhjaeju_4k", "banyan_bark_tfhjaeju_8k",
       "banyan_bark_tfhjaeju_4k_ue_high", "mulch_omsvgjp0_4k_ue_high", "soil_mulch_sfwnbgba_4k_ue_high"]
# DOWNLOADS.md row label (case-insensitive) -> listing URL
LABEL = {"australian_laurel": "Australian Laurel", "spotted_laurel": "Spotted Laurel", "weeping_fig": "Weeping Fig",
         "common_grape_vine": "Common Grape Vine", "tree_philodendron": "Tree Philodendron", "elephant_ear": "Elephant Ear",
         "african_flag": "African Flag", "chinese_wisteria": "Chinese Wisteria", "banyan_bark": "Banyan Bark",
         "mulch": "**Mulch**", "soil_mulch": "Soil Mulch"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def url(name):
    if "sfdik" in name:
        return "https://www.fab.com/listings/ebbd5efc-9069-4ae1-a766-c5627cb21f34"   # the 3D-model listing named in DOWNLOADS.md A.2
    key = re.sub(r"_[a-z0-9]{5,9}(_(4k|8k|high|raw)(_ue_high|_exr)?)?$", "", name)
    key = next((k for k in sorted(LABEL, key=len, reverse=True) if name.startswith(k)), None)
    m = re.search(r"\|\s*\*?\*?%s\*?\*?[^|]*\|[^|]*?(https://\S+?)[\s)|]" % re.escape(LABEL[key].strip("*")), DL) if key else None
    return m.group(1) if m else None


def main():
    items = {}
    for n in NEW:
        z = FAB / (n + ".zip")
        items[n] = dict(zip=str(z), sha256=sha(z), bytes=z.stat().st_size, listing_url=url(n), licence=FABLIC)
    for n in ("bark_platanus", "sakura_bark"):
        fs = sorted((PH / n).rglob("*.jpg"))
        items[n] = dict(dir=str(PH / n), files={f.name: sha(f) for f in fs}, listing_url="https://polyhaven.com/a/" + n,
                        licence="CC0 (polyhaven.com/license)")
    out = ROOT / "knowledge/landscape/foliage/assets_manifest.json"
    out.write_text(json.dumps(items, indent=1)); print(len(items), "items")
    for k, v in items.items(): print(k, v.get("listing_url"))


if __name__ == "__main__":
    main()
