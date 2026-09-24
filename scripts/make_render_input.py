"""Join the Revit extract with the spec's photometry, for lux and render.

    python scripts/make_render_input.py --ies-dir /home/x/archpipe/ies

Revit owns the GEOMETRY -- positions, mounting heights, openings, room
boundaries -- and `check_bedroom.py` proves it matches the spec exactly.
Revit does NOT reliably own the photometry: writes to a light family's
photometric parameters report success and then do not survive the save,
because third-party families carry a read-only Light Source Definition
that drives the photometric web (ADR-0012).

So the two are joined here, on the spec id that `build_bedroom.py` stamps
into Revit's Mark parameter and `extract_model.py` reads back. One
authored file, no drift, and a join key the model actually holds.

Anything that fails to join is reported and NOT silently defaulted. A
luminaire quietly given a stand-in photometric web would produce a heat
map and a render of a scheme nobody specified.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from archpipe import photometry as ph                        # noqa: E402
from archpipe.fixture_source import photometry_matches_fitting, source_point  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def luminous_size(ies_dir, name, fallback):
    """Smallest luminous opening dimension in mm, from the IES file.

    Blender models a point light's size as a SPHERE of this radius, and a
    594 x 24 mm strip is not a sphere. The smallest dimension is the
    conservative choice: a sphere of the LARGEST would be a bigger source
    than the fitting really is on two of three axes and would wash out the
    very distribution the IES file describes. The cost is that shadow
    penumbrae from linear fittings render slightly sharper than reality --
    a softness artefact, not an illuminance error.
    """
    if ies_dir is None:
        return fallback
    path = ph.find_ies(name, ies_dir)
    if not path.is_file():
        return fallback
    try:
        dims = [abs(v) * 1000.0 for v in ph.load(path).luminous_dimensions_m()]
        real = [v for v in dims if v > 0.5]
        return round(min(real), 1) if real else 0.0
    except Exception:
        return fallback


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--extract", type=Path,
                    default=ROOT / "out/bedroom-from-revit.json")
    ap.add_argument("--spec", type=Path, default=ROOT / "spec/bedroom-test.yaml")
    ap.add_argument("--ies-dir", required=True,
                    help="IES folder path ON THE RENDERING MACHINE")
    ap.add_argument("--out", type=Path, default=ROOT / "out/bedroom-render.json")
    a = ap.parse_args(argv)

    local_ies = ph.revit_ies_dir()
    got = json.loads(a.extract.read_text(encoding="utf-8"))
    from archpipe.luminaires.install import load_spec
    spec = load_spec(a.spec)          # picked products resolved from the library
    by_id = {l["id"]: l for l in spec.get("lighting", [])}

    joined, orphans, unmatched, no_source = [], [], [], []
    mismatch = {}
    for fx in got.get("lighting", []):
        key = fx.get("mark")
        s = by_id.get(key)
        if s is None:
            orphans.append({"family": fx.get("family"), "at": fx.get("at"),
                            "mark": key})
            continue
        # The light comes from where the fitting EMITS, measured from its
        # modelled geometry -- not from the family's insertion point. Using
        # the insertion height put a drum's source 243 mm below the drum and
        # a cone's 466 mm above its shade, in the render AND the lux engine,
        # which then agreed with each other (archpipe.fixture_source).
        src = source_point(fx.get("meshes"))
        if src is None:
            no_source.append(key)
            at, height, basis = fx["at"], fx.get("mounting_height"), "insertion point (unverified)"
        else:
            at, height, basis = [src[0], src[1]], src[2], src[3]
        # The file must describe THIS fitting: a strip file on a round drum
        # lights a drum as a strip. Reported, not failed: a recorded generic
        # substitution is still the scheme under review (the spec says so).
        try:
            problems = photometry_matches_fitting(
                [v * 1000.0 for v in ph.load(ph.find_ies(s["ies"], local_ies)).luminous_dimensions_m()],
                fx.get("meshes"))
        except Exception as exc:
            problems = ["IES not readable for the check: %s" % exc]
        if problems:
            mismatch[key] = problems
        joined.append({
            # Geometry from Revit, which is authoritative and verified.
            "id": key,
            "at": at,
            "mounting_height": height,
            "source_basis": basis,
            "insertion": {"at": fx["at"], "mounting_height": fx.get("mounting_height")},
            # The LUMINOUS opening, from the IES file -- not the family's
            # bounding box. Measured cost of confusing them: a linear
            # fitting whose IES declares 594 x 24 mm has a family bounding
            # box of 1219 mm, and using that as the light's radius turned a
            # thin strip into a 0.61 m sphere. The rendered peak beneath it
            # came out at 41% of the calculated value.
            "luminous_size_mm": luminous_size(local_ies, s["ies"],
                                              fx.get("luminous_size_mm")),
            # Orientation matters for an asymmetric fitting.
            "rotation": fx.get("rotation") or 0.0,
            "family": fx.get("family"),
            "meshes": fx.get('meshes', []),
            # Specification from the spec, which is the only authored copy.
            "ies": f"{a.ies_dir.rstrip('/')}/{s['ies']}",
            "ies_file": s["ies"],
            "lumens": s.get("lumens"),
            "kelvin": s.get("kelvin"),
            "watts": s.get("watts"),
            "layer": s.get("layer"),
            "output": 1.0,
        })
    matched = {j["id"] for j in joined}
    unmatched = [i for i in by_id if i not in matched]

    out = dict(got)
    out["lighting"] = joined
    out["source"] = "revit extract + spec photometry (scripts/make_render_input.py)"
    out["join"] = {"key": "Revit Mark parameter",
                   "matched": len(joined),
                   "orphan_fixtures": orphans,
                   "spec_items_not_in_model": unmatched,
                   "fixtures_without_source_geometry": no_source,
                   "photometry_fitting_mismatch": mismatch}

    # Room height, which the extract does not carry but the scene needs to
    # build a ceiling.
    rm = spec.get("room") or {}
    for r in out.get("rooms", []):
        r.setdefault("ceiling_height", rm.get("ceiling_height"))

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")

    print(f"{a.out}")
    print(f"  joined {len(joined)} of {len(got.get('lighting', []))} fixtures "
          f"on the Mark parameter")
    for j in joined:
        print(f"    {j['id']}  {j['ies_file']:<14} {j['lumens']:>5} lm  "
              f"{j['kelvin']}K  {j['watts']}W  source {[round(v) for v in j['at']]} h={j['mounting_height']:.0f} "
              f"({j['source_basis']}; insertion h={j['insertion']['mounting_height']})")
    if orphans:
        print(f"  {len(orphans)} fixture(s) in the model with no spec entry:")
        for o in orphans:
            print(f"    {o}")
    if unmatched:
        print(f"  {len(unmatched)} spec item(s) not found in the model: {unmatched}")
    for k, v in mismatch.items():
        print(f"  WARNING {k}: photometric file is not this fitting -- {'; '.join(v)}")
    if no_source:
        print(f"  {len(no_source)} fixture(s) with no source geometry, insertion point used: {no_source}")
    return 1 if (orphans or unmatched or no_source) else 0


if __name__ == "__main__":
    sys.exit(main())
