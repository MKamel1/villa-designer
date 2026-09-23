"""Cross-check the rendered lux grid against the analytical one.

    python scripts/compare_lux.py out/lux_direct.json

Two completely independent implementations of the same physics:

  * `archpipe.lighting` -- a closed-form inverse-square cosine sum over
    IES photometry, itself validated against hand calculation.
  * Cycles -- an unbiased path tracer, calibrated per ADR-0010.

They share no code. Nothing but the IES files and the room dimensions is
common between them. If they agree, the render is a faithful
representation of the lighting rather than a picture that resembles one,
which is the whole reason the analytical engine exists.

Compare only the DIRECT-component render (`--bounces 0`). A full
global-illumination render legitimately reads higher, because it includes
the bounced light the analytical engine cannot see; that difference is a
measurement of inter-reflection, not a disagreement, and
`--bounces 16` is how it is obtained.

Only points inside the room are compared. The probe plane spans the wall
bounds in a square frame, so it also covers the wall thickness and the
corners beyond the room -- real zeros, but not part of the room's grid.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from archpipe import photometry as ph
from archpipe.lighting import Luminaire, point_illuminance



def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rendered", type=Path)
    ap.add_argument("--extract", type=Path, default=Path("out/bedroom.json"))
    ap.add_argument("--inset", type=float, default=150.0,
                    help="ignore a band at the wall face, mm")
    a = ap.parse_args()

    rendered = json.loads(a.rendered.read_text(encoding="utf-8"))
    extract = json.loads(a.extract.read_text(encoding="utf-8"))
    boundary = extract['rooms'][0]['boundary']
    x0, x1 = min(p[0] for p in boundary), max(p[0] for p in boundary)
    y0, y1 = min(p[1] for p in boundary), max(p[1] for p in boundary)
    plane = rendered["working_plane_mm"]
    if rendered.get('bounces') != 0:
        print('Cannot compare reflected light with a direct-only calculation.')
        return 1

    ies_dir = ph.revit_ies_dir()
    if ies_dir is None:
        print("No local Revit IES library; cannot rebuild the scheme.")
        return 2

    scheme = []
    for fx in extract["lighting"]:
        scheme.append(Luminaire(
            fx["id"], ph.load(ies_dir / fx["ies_file"]),
            fx["at"][0], fx["at"][1], fx["mounting_height"],
            aim=float(fx.get("rotation") or 0.0),
            layer=fx.get("layer", "ambient"),
            output=float(fx.get("output") or 1.0)))

    # The render applies no maintenance factor -- it is an initial-condition
    # simulation of the fittings as specified. Compare like with like.
    # Furniture footprints, so occluded points can be separated out.
    #
    # The analytical engine has NO occlusion: it sums inverse-square
    # contributions and nothing casts a shadow. Cycles traces rays, so a
    # wardrobe blocks light. Comparing the two over a furnished room
    # therefore measures the shadows, not the agreement -- and the render
    # is the one that is right.
    blocks = []
    for fn in extract.get("furniture", []):
        if rendered.get('furniture_included') is False:
            break
        at, size = fn.get("at"), fn.get("size_mm")
        if not at or not size:
            continue
        hw, hd = float(size[0]) / 2.0, float(size[1]) / 2.0
        blocks.append((at[0] - hw, at[1] - hd, at[0] + hw, at[1] + hd))

    def shadowed(x, y, margin=350.0):
        """Inside or near a furniture footprint.

        The margin is generous on purpose: the penumbra of a box lit by a
        finite source extends beyond its plan outline, and the point of
        this split is to isolate CLEAN points, not to draw the shadow
        exactly.
        """
        for x0, y0, x1, y1 in blocks:
            if (x0 - margin) <= x <= (x1 + margin) and                (y0 - margin) <= y <= (y1 + margin):
                return True
        return False

    rows, clear = [], []
    for x, y, lux_r in rendered["points"]:
        if not (x0 + a.inset <= x <= x1 - a.inset and y0 + a.inset <= y <= y1 - a.inset):
            continue
        lux_a = point_illuminance(scheme, x, y, plane, maintenance_factor=1.0)
        rows.append((x, y, lux_a, lux_r))
        if not shadowed(x, y):
            clear.append((x, y, lux_a, lux_r))

    if not rows:
        print("No overlapping points to compare.")
        return 1

    tot_a = sum(r[2] for r in rows)
    tot_r = sum(r[3] for r in rows)
    n = len(rows)

    # Relative error is meaningless where the absolute value is tiny, so
    # report the absolute difference against the scene's peak as well.
    peak = max(max(r[2] for r in rows), max(r[3] for r in rows))
    diffs = [abs(r[3] - r[2]) for r in rows]
    worst = max(rows, key=lambda r: abs(r[3] - r[2]))

    print(f"Comparing {n} points inside the room "
          f"(plane {plane:.0f} mm, {a.inset:.0f} mm inset from the wall face)")
    print()
    print(f"  {'':22} {'analytical':>12} {'rendered':>12} {'diff':>9}")
    print(f"  {'average lux':22} {tot_a / n:>12.2f} {tot_r / n:>12.2f} "
          f"{100 * (tot_r - tot_a) / tot_a:>+8.2f}%")
    print(f"  {'maximum lux':22} {max(r[2] for r in rows):>12.2f} "
          f"{max(r[3] for r in rows):>12.2f}")
    print()
    print(f"  mean absolute difference   {sum(diffs) / n:>8.2f} lx "
          f"({100 * (sum(diffs) / n) / peak:.2f}% of peak)")
    print(f"  worst point                {max(diffs):>8.2f} lx at "
          f"({worst[0]:.0f}, {worst[1]:.0f}) -- "
          f"analytical {worst[2]:.1f}, rendered {worst[3]:.1f}")

    # Agreement where the light actually is: points above 10% of peak.
    def band(label, sample):
        bright = [r for r in sample if r[2] > 0.1 * peak]
        if not bright:
            return None
        ratios = sorted(r[3] / r[2] for r in bright if r[2] > 0)
        med = ratios[len(ratios) // 2]
        print(f"  {label} ({len(bright)} points): median ratio {med:.4f}, "
              f"range {ratios[0]:.4f}-{ratios[-1]:.4f}")
        return med

    med_all = band("over 10% of peak, ALL points", rows)
    med = med_all
    if rendered.get('furniture_included') is False:
        print('  Calibration probe excludes furniture; it does not verify furnished shadows.')
    if blocks:
        med = band("over 10% of peak, CLEAR of furniture", clear)
        print()
        print(f"  {len(rows) - len(clear)} of {len(rows)} points lie within "
              f"350 mm of a furniture footprint.")
        print("  The analytical engine models no occlusion, so those points "
              "are where")
        print("  the two MUST disagree. Agreement on the clear points is the "
              "real test.")
        if med is not None:
            print()
            if abs(med - 1.0) <= 0.05:
                print(f"  VERDICT: clear-point median {med:.4f} -- the render "
                      f"and the closed-form")
                print("  calculation agree to within 5% where nothing is in "
                      "the way.")
            else:
                print(f"  VERDICT: clear-point median {med:.4f} is outside "
                      f"5%; something other")
                print("  than shadowing differs.")
    # Never return success after printing a failed or unavailable verdict.
    # This is a pipeline gate, not merely an informational table.
    if med is None or abs(med - 1.0) > 0.05:
        print('  VERDICT: FAIL -- direct-light agreement outside 5% or unavailable')
        return 1
    print('  VERDICT: PASS -- direct-light median ratio within 5%')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
