"""Generated-foliage library: the interface the build lanes (LDB/GI) place from, labels, schedule rows.

    plant_for(slug, oid, height_m, spread_m, state)   -> generate.Plant   (seed = stable hash of the element id, as
                                                          planting.pick_variant does for Fab variations)
    label / caption / validate_label                  -> the honest labelling (fidelity species|form-class)
    schedule(layout)                                  -> one row per species in the layout
    python -m archpipe.landscape.foliage.library bake  (atlas RGBA bake)  |  manifest  (library.json + schedule.json)

Same contract as a graded asset: built at the sourced/layout size (height_m, spread_m), base on the ground at the
origin, a stable seed per element id. Inside Blender call `blender_build.build_plant(plant)`; portable form: glb."""
import json
import sys
import zlib
from pathlib import Path

from . import VERSION
from .generate import BANKS, SPECS, default_size, generate
from .species import ROOT, accepted_ok, sourced_ranges  # noqa: F401

LAYOUT = ROOT / "knowledge/landscape/concept/final/layout-final.json"
OUT = ROOT / "knowledge/landscape/foliage"
SHARED = Path("/home/omar/archpipe/shared/assets/generated/foliage")
REQUIRED = ("species", "accepted_name", "generator_version", "seed", "state", "atlas_used", "atlas_species", "fidelity", "construction", "caption")

# planting sizes for library demos where the layout gives none (policy: inside the sourced range; climbers sized to
# the 2.1 m trellis screens of the layout)
DEMO = {"jasminum_sambac": (2.1, 1.0), "petrea_volubilis": (2.1, 1.0), "vitis_vinifera": (2.1, 1.0),
        "trachelospermum_jasminoides": (2.1, 1.2), "fatsia_japonica": (2.0, 1.2), "alpinia_zerumbet": (2.7, 1.5),
        "lagerstroemia_indica": (4.5, 4.0), "pittosporum_tobira": (2.4, 1.5)}


class LabelError(ValueError):
    pass


def seed_of(oid):
    return zlib.crc32(str(oid).encode()) % 100000


def plant_for(slug, oid, height_m=None, spread_m=None, state="leaf-on", lod=0, lean=(0.0, 0.0)):
    return generate(slug, seed_of(oid), height_m, spread_m, state, lod, lean)


def validate_label(label):
    """Raise LabelError unless the label is complete and honest: `species` fidelity needs every atlas to be that species."""
    miss = [k for k in REQUIRED if k not in label or label[k] in (None, "", [])]
    if miss:
        raise LabelError("label missing " + ",".join(miss))
    if label["fidelity"] not in ("species", "form-class"):
        raise LabelError("fidelity must be species|form-class, got %r" % label["fidelity"])
    want = " ".join(label["accepted_name"].split()[:2])
    same = [" ".join(a.split()[:2]) == want for a in label["atlas_species"]]
    if label["fidelity"] == "species" and not all(same):
        raise LabelError("fidelity 'species' claimed for %s but the leaf scan is %s" % (want, "/".join(label["atlas_species"])))
    if label["fidelity"] == "form-class" and "form-class" not in label["caption"]:
        raise LabelError("a form-class plant's caption must say form-class")
    return True


def caption(label, close_up=False):
    """The only text a render caption may use. A form-class plant is never captioned as the named species."""
    validate_label(label)
    if label["fidelity"] == "species":
        return "%s (generated from a leaf scan of the species)" % label["accepted_name"]
    return ("generated form-class plant, stands in for %s" % label["accepted_name"]) if not close_up else \
        "generated form-class plant (leaf scan: %s), not the species" % ", ".join(label["atlas_species"])


def bake_rgba(size=2048):
    """RGBA atlases for glb: BaseColor rgb + Opacity (red channel) as alpha. Written to SHARED/atlas (not the repo)."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    d = SHARED / "atlas"; d.mkdir(parents=True, exist_ok=True)
    for b, r in BANKS.items():
        c = Image.open(r["maps"]["BaseColor"]).convert("RGB").resize((size, size), Image.LANCZOS)
        a = Image.open(r["maps"]["Opacity"]).split()[0].resize((size, size), Image.LANCZOS)
        c.putalpha(a); c.save(d / ("rgba_%s.png" % b))
    return d


def _layout_species():
    L = json.loads(LAYOUT.read_text())
    out = {}
    for g in L["planting_groups"]:
        for p in g["plants"]:
            out.setdefault(p["species"], []).append(p["spread_m"])
    for t in L["trees"]:
        out.setdefault(t["species"], []).append(t.get("mature_spread_m"))
    return out


def schedule(grades=None):
    """One row per generated species used in the layout: count, size, fidelity, caption, grade. Species with a graded
    scan asset (aspidistra, pennisetum...) are not generated and not listed."""
    grades = grades or json.loads((OUT / "grades.json").read_text())
    lay = _layout_species()
    rows = []
    for slug in sorted(SPECS):
        if slug not in lay and slug not in ("trachelospermum_jasminoides", "alpinia_zerumbet", "pittosporum_tobira"):
            continue
        p = plant_for(slug, slug + "#demo", *(DEMO.get(slug) or (None, None)))
        spreads = [s for s in lay.get(slug, []) if s]
        rows.append(dict(species=slug, in_layout=slug in lay, count=len(lay.get(slug, [])), layout_spread_m=[min(spreads), max(spreads)] if spreads else None,
                         fidelity=p.label["fidelity"], caption=caption(p.label), close_up_caption=caption(p.label, True),
                         atlas_used=p.label["atlas_used"], atlas_species=p.label["atlas_species"], generator_version=VERSION,
                         leaf_len_source=p.label["leaf_len_source"], grade=grades.get(slug, {}).get("grade"), sheet=grades.get(slug, {}).get("sheet")))
    return rows


def manifest():
    rows = schedule()
    (OUT / "schedule.json").write_text(json.dumps(rows, indent=1))
    lib = {s: dict(accepted_name=SPECS[s]["accepted"], form=SPECS[s]["form"], banks=list(SPECS[s]["banks"]), sourced=sourced_ranges(s),
                   demo_size_m=list(DEMO.get(s) or default_size(s)), states=["leaf-on", "leaf-off"] if SPECS[s]["form"] == "tree" else ["leaf-on"],
                   interface="plant_for(slug, element_id, height_m, spread_m, state) -> Plant; blender_build.build_plant(Plant)") for s in sorted(SPECS)}
    (OUT / "library.json").write_text(json.dumps(dict(generator_version=VERSION, species=lib), indent=1))
    return rows


if __name__ == "__main__":
    {"bake": lambda: print(bake_rgba()), "manifest": lambda: print(len(manifest()), "rows")}[sys.argv[1]]()
