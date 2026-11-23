"""Species specs: habit class, leaf bank and leaf geometry for each generated species.

Height and spread RANGES are never stored here: they are read from knowledge/landscape/plants/plants.json (sourced; the
test checks every generated plant against them). What this file adds is OUR modelling choices, each marked `policy`:
the growth form, which leaf bank carries the leaf, and leaf size/density. Leaf lengths come from the plant record
where it states one (petrea, `leaf_len_source: sourced`) and otherwise are general botanical figures stated as policy."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLANTS_JSON = ROOT / "knowledge/landscape/plants/plants.json"

# fields: form, accepted (scientific name of the species), banks {bank: weight}, leaf_len (m, mean), len_sd (rel),
# wscale (card width multiplier on the scan's aspect), arr (arrangement), arch (leaf droop rad), tint (rgb multiplier on
# the scan colour), plus form-specific numbers. `flowers`: only where a client scan of that species exists.
SPECS = {
    "justicia_brandegeeana": dict(form="shrub", accepted="Justicia brandegeeana", banks={"star_jasmine": 1.0}, leaf_len=0.050,
        len_sd=0.2, wscale=0.95, arr="opposite", arch=0.25, colour=(66, 108, 44), stems=9, stem_elev=(50, 78), env_pow=1.0,
        leaf_zone=0.55, node=0.035, branch_p=0.45, jitter=0.16, leaf_len_source="policy"),
    "salvia_leucantha": dict(form="shrub", accepted="Salvia leucantha", banks={"ginger_lily": 1.0}, leaf_len=0.10, len_sd=0.18,
        wscale=0.42, arr="opposite", arch=0.3, colour=(112, 132, 98), stems=11, stem_elev=(72, 88), env_pow=1.0, leaf_zone=0.7,
        node=0.07, branch_p=0.15, jitter=0.05, leaf_len_source="policy"),
    "jasminum_sambac": dict(form="climber", accepted="Jasminum sambac", banks={"star_jasmine": 1.0}, leaf_len=0.065, len_sd=0.2,
        wscale=1.0, arr="opposite", arch=0.35, colour=(58, 100, 38), stems=4, leaf_zone=1.0, node=0.04, branch_p=0.55,
        jitter=0.12, thickness=0.22, leaf_len_source="policy"),
    "petrea_volubilis": dict(form="climber", accepted="Petrea volubilis", banks={"star_jasmine": 0.55, "ginger_lily": 0.45},
        leaf_len=0.15, len_sd=0.18, wscale=0.8, arr="opposite", arch=0.3, colour=(62, 100, 40), stems=4, leaf_zone=1.0,
        node=0.07, branch_p=0.45, jitter=0.12, thickness=0.30, leaf_len_source="sourced: plants.json foliage 'oblong-elliptic leaves 4-9 in' (NCSU)"),
    "vitis_vinifera": dict(form="climber", accepted="Vitis vinifera", banks={"palmate_grape": 1.0}, leaf_len=0.13, len_sd=0.2,
        wscale=1.0, arr="alternate", arch=0.4, colour=(88, 128, 46), stems=3, leaf_zone=1.0, node=0.09, branch_p=0.5,
        jitter=0.14, thickness=0.30, leaf_len_source="policy"),
    "trachelospermum_jasminoides": dict(form="climber", accepted="Trachelospermum jasminoides", banks={"star_jasmine": 1.0},
        leaf_len=0.06, len_sd=0.2, wscale=1.0, arr="opposite", arch=0.3, colour=(56, 94, 36), stems=4, leaf_zone=1.0,
        node=0.04, branch_p=0.55, jitter=0.12, thickness=0.20, leaf_len_source="policy"),
    "fatsia_japonica": dict(form="petioled", accepted="Fatsia japonica", banks={"palmate_fatsia": 1.0}, leaf_len=0.30, len_sd=0.18,
        wscale=1.0, arr="alternate", arch=0.35, colour=(58, 98, 44), stems=5, petiole=0.32, leaf_zone=0.7, jitter=0.05,node=0.11,
        leaf_len_source="policy"),
    "farfugium_japonicum": dict(form="basal", accepted="Farfugium japonicum", banks={"taro": 1.0}, leaf_len=0.19, len_sd=0.2,
        wscale=1.0, arr="alternate", arch=0.3, colour=(62, 100, 44), count=20, petiole=0.16, leaf_len_source="policy"),
    "acorus_gramineus": dict(form="strap", accepted="Acorus gramineus", banks={"cast_iron": 0.5, "ginger_lily": 0.5}, leaf_len=0.24,
        len_sd=0.2, wscale=0.07, arr="basal", arch=0.8, elev=(58, 86), colour=(86, 124, 52), count=90, leaf_len_source="policy"),
    "alpinia_zerumbet": dict(form="cane", accepted="Alpinia zerumbet", banks={"ginger_lily": 1.0}, leaf_len=0.55, len_sd=0.15,
        wscale=1.0, arr="alternate", arch=0.85, colour=(64, 104, 46), count=11, leaf_len_source="policy"),
    "lagerstroemia_indica": dict(form="tree", accepted="Lagerstroemia indica", banks={"star_jasmine": 1.0}, leaf_len=0.055,
        len_sd=0.2, wscale=0.9, arr="opposite", arch=0.3, colour=(78, 118, 46), stems=4, clear_stem=2.2, node=0.04, leaf_len_source="policy"),
}


def accepted_ok(slug, plants=None):
    """True when the spec's scientific name is the record's accepted name (guards typos in SPECS)."""
    rec = (plants or sourced())[slug]
    return SPECS[slug]["accepted"].split()[0] in rec["attributes"]["accepted_name"]["value"]["name"]


def sourced():
    return {r["slug"]: r for r in json.loads(PLANTS_JSON.read_text())["species"]}


def _rng_of(attr):
    if not attr or attr.get("status") == "GAP" or not isinstance(attr.get("value"), dict) or "min" not in attr["value"]:
        return None
    return float(attr["value"]["min"]), float(attr["value"]["max"])


def sourced_ranges(slug):
    """{'height': (min,max)|None, 'spread': (min,max)|None} from plants.json. None = a GAP in the source."""
    rec = sourced().get(slug)
    if rec is None:
        return dict(height=None, spread=None)
    a = rec["attributes"]
    return dict(height=_rng_of(a.get("height_m")), spread=_rng_of(a.get("spread_m")))
