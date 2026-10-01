"""Apply reviewed C2 species and size evidence to the asset manifest.

Run from the repository root. No geometry, layout or camera is changed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ops/workstation/library-manifest.json"
PALETTE = ROOT / "out/villa/round3/plant-palette.json"

# Placed species, read from villa_landscape.build and its plant/door-pot loops.
PLACED = {
    "sf_bauhinia": "Bauhinia variegata", "sf_frangipani": "Plumeria rubra",
    "sf_lemon_tree": "Citrus limon", "sf_bottlebrush": "Callistemon citrinus",
    "sf_ixora": "Ixora coccinea", "sf_bougainvillea": "Bougainvillea glabra",
    "sf_lavender_clump": "Lavandula angustifolia 'Hidcote'",
    "sf_garden_flower_clump": "Bellis perennis",
    "flower_heliophila": "Plumbago auriculata",  # explicit blue-flowered look-alike proxy
    "sf_hibiscus": "Hibiscus rosa-sinensis",
    "flower_ursinia": "Ursinia anthemoides",
    "flower_gazania": "Gazania rigens", "sf_olive_old": "Olea europaea",
}

# Height and spread maxima in metres. None means the held species card has no
# numerical claim for that axis. Clump spread is explicitly ASSUMED in
# villa_landscape.CLUMP_SPREAD, and is not recast as a single-plant citation.
SIZE = {
    "Plumeria rubra": (7.62, 7.62),
    "Citrus limon": (None, 4.6), "Callistemon citrinus": (8, 4),
    "Ixora coccinea": (1.8288, 1.524), "Bougainvillea glabra": (8, 4),
    "Lavandula angustifolia 'Hidcote'": (.6, .75),
    "Bellis perennis": (.1524, .2286),
    "Hibiscus rosa-sinensis": (3.7, None),
    "Gazania rigens": (.3048, .3048), "Olea europaea": (9, 9),
    "Bauhinia variegata": (12.192, 10.668),
    "Ursinia anthemoides": (.5, .5),
    "Plumbago auriculata": (2.1336, 3.048),
}
EXTRA = {
    "Citrus limon": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=286755",
    "Callistemon citrinus": "https://www.rhs.org.uk/plants/2687/callistemon-citrinus/details",
    "Plumeria rubra": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?kempercode=d451",
    "Ixora coccinea": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=286675",
    "Bellis perennis": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=277170",
    "Gazania rigens": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=277558",
    "Bauhinia variegata": "https://ask.ifas.ufl.edu/st092",
    "Ursinia anthemoides": "https://www.rhs.org.uk/plants/161741/ursinia-anthemoides/details",
}
ASSUMED = {
    "decor-small": ([0, 0, 0], [1.5, 1.5, 1.5]),
    "wall-art": ([0, 0, 0], [3, 3, .5]),
    "boulder": ([0, 0, 0], [5, 5, 5]),
    "planter": ([0, 0, 0], [4, 3, 4]),
    "rug": ([0, 0, 0], [10, .3, 10]),
    "bistro-set": ([0, 0, 0], [5, 2, 5]),
    "egg-swing": ([0, 0, 0], [3, 3, 3]),
    "bench-outdoor": ([0, 0, 0], [5, 2, 5]),
    "task-lamp": ([0, 0, 0], [2, 2, 2]),
    "bedding": ([0, 0, 0], [3, 2, 3]),
}


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    palette = json.loads(PALETTE.read_text(encoding="utf-8"))
    cards = {card["botanical_name"]: card for group in palette["categories"].values()
             for card in group if isinstance(card, dict) and card.get("botanical_name")}
    for entry in manifest["props"]:
        role, asset = entry["role"], entry["id"]
        if role in ASSUMED:
            low, high = ASSUMED[role]
            entry["expected_size_range"] = {"min_m": low, "max_m": high,
                "basis": "ASSUMED", "reason": "Provisional intake envelope: no held role-size lesson or published product dimensions; review measured model and preview."}
        if asset in PLACED:
            species = PLACED[asset]
            entry["species"] = species
            if species not in SIZE:
                if entry.get("expected_size_range", {}).get("basis") == "species":
                    entry.pop("expected_size_range")
                continue  # supplementary care card has no mature-size figure
            height, spread = SIZE[species]
            if asset in {"sf_garden_flower_clump", "flower_gazania", "sf_lavender_clump", "flower_ursinia"}:
                spread = None  # multi-plant clump or maintained nursery form
            source = EXTRA[species] if species in EXTRA else cards[species]["source_url"]
            entry["expected_size_range"] = {
                "min_m": [0 if spread is not None else None, 0 if height is not None else None, 0 if spread is not None else None],
                "max_m": [spread, height, spread], "basis": "species", "source": source,
                "reason": "Species mature-size ceiling; nursery size may be smaller. Landscape-maintained or clump spread is ASSUMED where noted in villa_landscape.py."}
            if species == "Callistemon citrinus":
                entry["expected_size_range"]["min_m"] = [2.5, 4, 2.5]
            if species == "Plumeria rubra":
                entry["expected_size_range"]["min_m"] = [4.572, 4.572, 4.572]
            if asset in {"sf_bauhinia", "flower_ursinia"}:
                entry["expected_size_range"]["accessed"] = "2026-09-30"
            if asset == "sf_bauhinia":
                entry["expected_size_range"]["published_size"] = (
                    "UF/IFAS ENH251/ST092: height 20-40 ft; spread 25-35 ft")
            if asset == "flower_ursinia":
                entry["expected_size_range"]["min_m"][1] = .1
                entry["expected_size_range"]["published_size"] = (
                    "RHS: max height 0.1-0.5 m; max spread 0.1-0.5 m; "
                    "multi-plant clump width is checked against spacing")
        if asset == "sf_chelsea_bed":
            entry["expected_size_range"] = {"min_m": [1.05, .95, 2.14], "max_m": [2, 1.03, 2.24],
                "basis": "product", "source": "https://www.bertosalotti.it/letto_moderno/letto-matrimoniale-imbottito-con-contenitore-chelsea.html"}
        if asset == "sf_kidschair_oak":
            entry["expected_size_range"] = {"min_m": [.51, .80, .485], "max_m": [.51, .80, .485],
                "basis": "product", "source": "https://www.fredericia.com/product/soborg-wood-base-3050-3050224856"}
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
