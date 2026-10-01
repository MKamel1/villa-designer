"""Apply the lead's C2 phase 2d asset decisions to the authored manifest."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "ops/workstation/library-manifest.json"
manifest = json.loads(path.read_text(encoding="utf-8"))
entries = {entry["id"]: entry for entry in manifest["props"]}

sofa = entries["sf_minotti_sofa"]
sofa["size_override"] = {
    "reason": "Large garden-living sofa accepted at its measured 2.9586 m width; real footprint passes layout clearance checks despite Mitton & Nystuen Fig. 4.3 generic 2.49 m maximum.",
    "decided_by": "lead", "date": "2026-09-30",
}
sofa["use"] = "Minotti-style sofa (unidentified model), garden living"
sofa["credit"] = ("Minotti-style sofa (unidentified model), Sketchfab asset Sofa-minotti "
                  "by alejxbailey (https://sketchfab.com/3d-models/sofa-minotti-"
                  "e1422bbf699246b386f0ae6e37d9c635), CC Attribution")

gazania = entries["flower_gazania"]
gazania["placed_scale"] = round(0.25 / 0.3987, 8)
gazania["placed_scale_reason"] = (
    "villa_landscape._prop uniformly scales the measured 0.3987 m native clump "
    "to 0.25 m placed height; node inspection remains due on workstation")

proxy = entries["flower_heliophila"]
proxy["use"] = ("blue-flowered Plumbago auriculata look-alike proxy; "
                "Heliophila model is appearance only")
proxy["expected_size_range"]["reason"] = (
    "MOBOT Plumbago species card; the Heliophila mesh is an explicitly labelled "
    "blue-flowered look-alike proxy pending reviewed asset replacement.")

# Poly Haven's numbered indoor plant models do not identify botanical species.
# These are explicit design species with look-alike appearance proxies. Source
# pages show integrated pots; the workstation preview still has to assess fit.
indoor = {
    "potted_plant_01": (
        "Ficus lyrata", "indoor-floor-plant", [1.5, 8.0, 1.5],
        "https://www.rhs.org.uk/plants/7207/ficus-lyrata/details",
        "wavy-leaved potted floor tree look-alike proxy"),
    "potted_plant_02": (
        "Syngonium podophyllum", "indoor-floor-plant", [1.0, 2.5, 1.0],
        "https://www.rhs.org.uk/plants/17899/syngonium-podophyllum/details",
        "veined, variegated potted floor foliage look-alike proxy"),
    "potted_plant_04": (
        "Haworthiopsis attenuata", "indoor-table-plant", [.5, .5, .5],
        "https://www.rhs.org.uk/plants/504241/haworthiopsis-attenuata/details",
        "zebra haworthia potted table plant"),
}
for asset_id, (species, role, maxima, source, use) in indoor.items():
    entry = entries[asset_id]
    entry["role"] = role
    entry["species"] = species
    entry["contents"] = {"pot": True}
    entry["use"] = use
    entry["expected_size_range"] = {
        "min_m": [0, 0, 0], "max_m": maxima,
        "basis": "species", "source": source, "accessed": "2026-09-30",
        "reason": ("RHS mature species upper bounds; the numbered Poly Haven model is "
                   "a look-alike appearance proxy, not an identified species scan."),
    }

path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
