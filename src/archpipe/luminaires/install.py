"""Install a picked product into a design spec: one source of truth.

A spec lighting entry names a product and says where it goes:

    - id: LT-01
      at: [2100, 1800]
      mounting_height: 2699        # emitter height (check_bedroom measures it)
      rotation: 0
      product: {manufacturer: signify, sku: "911401840687", lamp_set: 0}

`resolve` fills in everything the product decides -- lumens, watts, colour
temperature, CRI, the IES file (exported from the manufacturer's LDT), the
Revit family and its size -- from the verified library. A hand-typed value
that disagrees with the product is an error, not an override: two sources
for one figure is how a render and a calculation drift apart.
"""
from __future__ import annotations

from pathlib import Path

from archpipe import photometry as ph
from archpipe.luminaires import library as lib

DERIVED = ("lumens", "watts", "kelvin", "cri", "ies", "family")


class InstallError(ValueError):
    pass


def ies_name(manufacturer: str, sku: str, lamp_set: int) -> str:
    return f"{manufacturer.lower()}-{lib._sku_clean(sku)}-ls{lamp_set}.ies"


def resolve(item: dict, *, library: Path = lib.LIBRARY, allow_unverified: bool = False,
            ies_dir: Path | None = None) -> dict:
    """Return a copy of the spec entry with the product's figures filled in."""
    prod = item.get("product")
    if not prod:
        return dict(item)
    mfr, sku, k = str(prod["manufacturer"]).lower(), str(prod["sku"]), int(prod.get("lamp_set", 0))
    row = lib.get(mfr, sku, k, library)
    if row is None:
        raise InstallError(f"{item.get('id')}: {mfr}/{sku} lamp set {k} is not in the library -- "
                           f"download its files (scripts/luminaires.py links {mfr} {sku}) and import them")
    if not row["verified"] and not allow_unverified:
        raise InstallError(f"{item.get('id')}: {mfr}/{sku} failed its checks: {row['flux_check']}; "
                           f"{row['pair_check']}; {row['sanity']}")
    folder = library / row["folder"]
    rfas = sorted(folder.glob("*.[rR][fF][aA]"))
    name = ies_name(mfr, sku, k)
    lib.export_ies(mfr, sku, k, (ies_dir or ph.PRODUCT_IES_DIR) / name, library)
    derived = {
        "lumens": row["lamp_lm"], "watts": row["watts"], "kelvin": row["cct_k"], "cri": row["cri_ra"],
        "ies": name, "family": str(rfas[0].resolve()) if rfas else None,
    }
    out = dict(item)
    clashes = []
    for key in DERIVED:
        typed = item.get(key)
        if typed is None:
            continue
        want = derived[key]
        same = (abs(float(typed) - float(want)) <= max(1.0, 0.005 * abs(float(want)))
                if isinstance(want, (int, float)) and want is not None else str(typed) == str(want))
        if not same:
            clashes.append(f"{key} {typed!r} in the spec, {want!r} from the product")
    if clashes:
        raise InstallError(f"{item.get('id')}: the spec contradicts {mfr}/{sku}: " + "; ".join(clashes)
                           + ". Delete the typed value; the product is the source.")
    if derived["family"] is None:
        raise InstallError(f"{item.get('id')}: {mfr}/{sku} has no Revit family in the library; "
                           f"download its Revit file (scripts/luminaires.py links {mfr} {sku})")
    out.update(derived)
    out["product"] = {"manufacturer": mfr, "sku": sku, "lamp_set": k, "name": row["name"],
                      "mount": row["mount"], "luminaire_lm": row["luminaire_lm"], "efficacy": row["efficacy"],
                      "beam_deg": row["beam_deg"], "size_mm": [row["length_mm"], row["width_mm"], row["height_mm"]],
                      "luminous_mm": [row["lum_length_mm"], row["lum_width_mm"]],
                      "checks": {"flux": row["flux_check"], "pair": row["pair_check"], "sanity": row["sanity"]},
                      "library_folder": row["folder"]}
    return out


def resolve_all(lighting: list[dict], **kw) -> list[dict]:
    return [resolve(item, **kw) for item in lighting]


def expectations(item: dict, requirement: dict | None = None) -> list[tuple[str, bool, str]]:
    """Does the installed product meet what the design asked of it?

    `requirement` is the design's ask, separate from the product: e.g.
    {kelvin: 3000, cri_min: 90, lumens: [600, 1000], beam: [30, 60], max_size_mm: 300}.
    Achieved versus required, never an adjective.
    """
    req = requirement or item.get("requirement") or {}
    p = item.get("product") or {}
    out = []
    if "kelvin" in req:
        out.append(("colour temperature", abs(float(item["kelvin"]) - req["kelvin"]) < 1,
                    f"{item['kelvin']:.0f} K vs {req['kelvin']} K"))
    if "cri_min" in req:
        ok = item.get("cri") is not None and float(item["cri"]) >= req["cri_min"]
        out.append(("colour rendering", ok, f"Ra {item.get('cri')} vs >= {req['cri_min']}"))
    if "lumens" in req:
        lo, hi = req["lumens"]
        lm = p.get("luminaire_lm")
        out.append(("luminaire flux", lm is not None and lo <= lm <= hi, f"{lm} lm vs {lo}-{hi} lm"))
    if "beam" in req:
        lo, hi = req["beam"]
        b = p.get("beam_deg")
        out.append(("beam (computed)", b is not None and lo <= b <= hi, f"{b} deg vs {lo}-{hi} deg"))
    if "max_size_mm" in req:
        size = max(p.get("size_mm") or [0])
        out.append(("size", size <= req["max_size_mm"], f"{size:.0f} mm vs <= {req['max_size_mm']} mm"))
    if "efficacy_min" in req:
        e = p.get("efficacy")
        out.append(("efficacy", e is not None and e >= req["efficacy_min"], f"{e} lm/W vs >= {req['efficacy_min']}"))
    out.append(("product files verified", all(str(v).startswith(("ok", "n/a")) for v in (p.get("checks") or {}).values()),
                "; ".join(f"{k}: {v}" for k, v in (p.get("checks") or {}).items())))
    return out


def load_spec(path) -> dict:
    """Read a design spec (YAML) with every product entry resolved.

    The one loader for the spec builder, the round-trip check and the render
    input, so all three see the same product figures.
    """
    import yaml
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if any(l.get("product") for l in spec.get("lighting", [])):
        spec["lighting"] = resolve_all(spec["lighting"])
    return spec
