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

W, D = 4200.0, 3600.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rendered", type=Path)
    ap.add_argument("--extract", type=Path, default=Path("out/bedroom.json"))
    ap.add_argument("--inset", type=float, default=150.0,
                    help="ignore a band at the wall face, mm")
    a = ap.parse_args()

    rendered = json.loads(a.rendered.read_text(encoding="utf-8"))
    extract = json.loads(a.extract.read_text(encoding="utf-8"))
    plane = rendered["working_plane_mm"]

    ies_dir = ph.revit_ies_dir()
    if ies_dir is None:
        print("No local Revit IES library; cannot rebuild the scheme.")
        return 2

    scheme = []
    for fx in extract["lighting"]:
        scheme.append(Luminaire(
            fx["id"], ph.load(ies_dir / fx["ies_file"]),
            fx["at"][0], fx["at"][1], fx["mounting_height"],
            layer=fx.get("layer", "ambient"),
            output=float(fx.get("output") or 1.0)))

    # The render applies no maintenance factor -- it is an initial-condition
    # simulation of the fittings as specified. Compare like with like.
    rows = []
    for x, y, lux_r in rendered["points"]:
        if not (a.inset <= x <= W - a.inset and a.inset <= y <= D - a.inset):
            continue
        lux_a = point_illuminance(scheme, x, y, plane, maintenance_factor=1.0)
        rows.append((x, y, lux_a, lux_r))

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
    bright = [r for r in rows if r[2] > 0.1 * peak]
    if bright:
        ratios = [r[3] / r[2] for r in bright if r[2] > 0]
        ratios.sort()
        print(f"  over 10% of peak ({len(bright)} points): "
              f"median ratio {ratios[len(ratios) // 2]:.4f}, "
              f"range {ratios[0]:.4f}-{ratios[-1]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
