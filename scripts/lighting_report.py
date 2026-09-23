"""Lighting report for a real extract: lux grid, task points, heat map.

    python scripts/lighting_report.py out/bedroom-render.json

Consumes what Revit actually built, joined with the spec's photometry by
`make_render_input.py`. The demo script that preceded this one carried the
scheme in its own source; this reads the model, so the numbers describe
the room that exists.

What it will and will not judge is settled by ADR-0009: average
illuminance, task-point illuminance, layer count and power density are
supported by a direct calculation; EN 12464-1 uniformity is not, and is
reported only as `Emin/Eavg (direct only)` under a name that cannot be
mistaken for U0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from archpipe import photometry as ph                       # noqa: E402
from archpipe.lighting import (Luminaire, Surfaces, converged,   # noqa: E402
                               heatmap_svg, interreflected_estimate,
                               lux_grid, point_illuminance)

ROOT = Path(__file__).resolve().parents[1]

# Bedroom targets. General 100-300 lx is ordinary residential practice; the
# reading band is 300-500 lx, a BAND and not a floor because a fitting can
# be too bright as easily as too dim (a 780 lm lamp 300 mm above a pillow
# measured 826 lx, roughly twice the top of the range).
TARGETS = {"bedroom": {"avg": (100.0, 300.0), "reading": (300.0, 500.0)}}


def build_scheme(data, ies_dir):
    lums, problems = [], []
    for fx in data.get("lighting", []):
        name = fx.get("ies_file")
        if not name:
            problems.append(f"{fx.get('id')}: no IES file named")
            continue
        path = ies_dir / name
        if not path.is_file():
            problems.append(f"{fx.get('id')}: {name} not found in {ies_dir}")
            continue
        at = fx.get("at")
        h = fx.get("mounting_height")
        if not at or h is None:
            problems.append(f"{fx.get('id')}: no position or mounting height")
            continue
        lums.append(Luminaire(
            fx["id"], ph.load(path), float(at[0]), float(at[1]), float(h),
            aim=float(fx.get("rotation") or 0.0),
            layer=fx.get("layer") or "ambient",
            watts=fx.get("watts"), room=fx.get("room") or ""))
    return lums, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", type=Path, nargs="?",
                    default=ROOT / "out/bedroom-render.json")
    ap.add_argument("--spacing", type=float, default=100.0)
    ap.add_argument("--out-svg", type=Path,
                    default=ROOT / "out/bedroom-lux-from-revit.svg")
    ap.add_argument("--json", type=Path,
                    default=ROOT / "out/bedroom-lighting.json")
    a = ap.parse_args(argv)

    data = json.loads(a.input.read_text(encoding="utf-8"))
    ies_dir = ph.revit_ies_dir()
    if ies_dir is None:
        print("No Revit IES library on this machine.")
        return 2

    rooms = data.get("rooms") or []
    if not rooms:
        print("The extract carries no rooms.")
        return 2
    room = rooms[0]
    boundary = [[float(p[0]), float(p[1])] for p in room["boundary"]]

    scheme, problems = build_scheme(data, ies_dir)
    for p in problems:
        print(f"  PROBLEM  {p}")
    if not scheme:
        print("No usable luminaires.")
        return 1

    grid = lux_grid(boundary, scheme, room=room.get("name") or "Room",
                    spacing=a.spacing)
    ok, coarse, fine = converged(boundary, scheme, spacing=a.spacing)

    xs = [p[0] for p in boundary]
    ys = [p[1] for p in boundary]
    w, d = max(xs) - min(xs), max(ys) - min(ys)
    h = float(room.get("ceiling_height") or 2700.0)
    irc = interreflected_estimate(grid, w, d, h, surfaces=Surfaces())

    print("LIGHTING REPORT  %s  (built and measured in Revit)"
          % room.get("name"))
    print(f"  {grid.summary()}")
    print(f"  {grid.assessment_note()}")
    print(f"  grid converged at {a.spacing:.0f} mm: {ok} "
          f"({coarse:.2f} -> {fine:.2f} lx at {a.spacing/2:.0f} mm)")
    print(f"  {irc.note}")
    print(f"  => total average, direct + estimate: "
          f"{grid.average + irc.low:.0f}-{grid.average + irc.high:.0f} lx")
    for wmsg in grid.point_source_warnings():
        print(f"  POINT-SOURCE  {wmsg}")

    # Task points come from the furniture, not from a hard-coded list: the
    # reading plane is above the pillow, wherever the bed actually is.
    tasks = []
    bed = next((f for f in data.get("furniture", [])
                if "BED" in (f.get("mark") or "").upper() and f.get("at")), None)
    for fn in data.get("furniture", []):
        mark = (fn.get("mark") or "").upper()
        at = fn.get("at")
        if not at:
            continue
        if "BST" in mark:
            # Reading happens on the PILLOW, not on the bedside table, so
            # the point is offset from the table towards the bed. Measured
            # directly beneath the fitting it read 4762 lx, which says more
            # about where the probe was than about the scheme -- and the
            # point-source warning already flagged that figure as
            # overstated at 300 mm.
            # The pillow sits BESIDE the table at the same head-of-bed
            # line, not diagonally towards the middle of the mattress. The
            # first version offset towards the bed centre and put the probe
            # half way down the duvet.
            rx, ry = at[0], at[1]
            if bed and bed.get("at"):
                rx = at[0] + (600.0 if bed["at"][0] > at[0] else -600.0)
            tasks.append((f"reading, pillow by {fn.get('mark')}", rx, ry, 900.0))
        elif "WRD" in mark:
            tasks.append(("wardrobe face", at[0], at[1], 850.0))
        elif "DSK" in mark:
            tasks.append(("desk top", at[0], at[1], 750.0))
    tasks.append(("floor, room centre", (max(xs) + min(xs)) / 2,
                  (max(ys) + min(ys)) / 2, 0.0))

    print()
    print("  TASK POINTS (what a direct calculation supports)")
    task_rows = []
    for label, tx, ty, tz in tasks:
        e = point_illuminance(scheme, tx, ty, tz)
        task_rows.append({"label": label, "at": [tx, ty, tz], "lux": round(e, 1)})
        print(f"    {label:<28} {e:>7.0f} lx  (at {tz:.0f} mm)")

    layers = grid.layers_present()
    reading = [r for r in task_rows if r["label"].startswith("reading")]
    tgt = TARGETS["bedroom"]
    verdicts = [
        ("layers >= 3", len(layers) >= 3, f"{len(layers)} ({', '.join(layers)})"),
        (f"average {tgt['avg'][0]:.0f}-{tgt['avg'][1]:.0f} lx",
         tgt["avg"][0] <= grid.average <= tgt["avg"][1],
         f"{grid.average:.0f} lx"),
        ("power density <= 10 W/m2",
         (grid.power_density or 0) <= 10.0,
         "not stated" if grid.power_density is None
         else f"{grid.power_density:.1f} W/m2"),
    ]
    for r in reading:
        verdicts.append((
            f"{r['label']} {tgt['reading'][0]:.0f}-{tgt['reading'][1]:.0f} lx",
            tgt["reading"][0] <= r["lux"] <= tgt["reading"][1],
            f"{r['lux']:.0f} lx"))

    print()
    print("  STAGE 5 CHECKS")
    failed = 0
    for label, ok_, measured in verdicts:
        if not ok_:
            failed += 1
        print(f"    {'PASS' if ok_ else 'FAIL'}  {label:<34} {measured}")
    print("    n/a   %-34s not assessed -- direct calculation only "
          "(ADR-0009)" % "uniformity")

    heatmap_svg(grid, a.out_svg, boundary=boundary, scale=0.09,
                target=tgt["avg"])
    print()
    print(f"  heat map -> {a.out_svg}")

    a.json.write_text(json.dumps({
        "room": room.get("name"),
        "source": data.get("source"),
        "average_lx": round(grid.average, 2),
        "minimum_lx": round(grid.minimum, 2),
        "maximum_lx": round(grid.maximum, 2),
        "emin_over_eavg_direct_only": round(grid.uniformity_direct, 5),
        "power_density_w_m2": (None if grid.power_density is None
                               else round(grid.power_density, 2)),
        "layers": list(layers),
        "interreflected_lx": [round(irc.low, 1), round(irc.high, 1)],
        "task_points": task_rows,
        "verdicts": [{"check": c, "pass": bool(o), "measured": m}
                     for c, o, m in verdicts],
    }, indent=2, sort_keys=True), encoding="utf-8")
    print(f"  data     -> {a.json}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
