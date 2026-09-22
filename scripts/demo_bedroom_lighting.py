"""The mock bedroom's lighting scheme, on real Revit photometry.

Bedroom from the approved plan: 4200 x 3600 mm internal, 2700 ceiling.
Three deliberate layers so the "no lone central fixture" rule passes, and
the negative case (delete the layers) can be shown to fail.

The IES files supply DISTRIBUTIONS. Their wattages are 1990s incandescent
and T12 fluorescent (16-35 lm/W), so wattage is restated from a modern LED
efficacy rather than taken from the file.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from archpipe import photometry as ph
from archpipe.lighting import (Luminaire, Surfaces, lux_grid, heatmap_svg,
                               converged, point_illuminance,
                               interreflected_estimate)

IES = ph.revit_ies_dir()
if IES is None:
    raise SystemExit("No Revit IES library found. It ships with the "
                     "base install at C:/ProgramData/Autodesk/RVT "
                     "<year>/IES and needs no content-library download.")
W, D, CEILING = 4200.0, 3600.0, 2700.0
ROOM = [(0.0, 0.0), (W, 0.0), (W, D), (0.0, D)]
LED_EFFICACY = 95.0          # lm/W, an ordinary good LED fitting in 2026

pendant = ph.load(IES / "PLD1A21.ies")      # 8" aperture pendant, 2780 lm
bedside = ph.load(IES / "EWL2A19.ies")      # metal lamphead, 780 lm, 17 deg
strip   = ph.load(IES / "LGLled.ies")       # narrow LED, 1008 lm, 10 deg


def led_watts(p):
    """Wattage the same lumen package would draw as a modern LED fitting."""
    return round(p.total_lumens / LED_EFFICACY, 1)


print("FITTINGS  (Revit 2025 IES library -- already on disk, no download)")
print(f"  {'role':18} {'lumens':>7} {'file W':>7} {'file lm/W':>10} "
      f"{'LED W':>7}  file")
for tag, p in (("ambient pendant", pendant), ("task    bedside", bedside),
               ("accent  wardrobe", strip)):
    e = p.efficacy
    print(f"  {tag:18} {p.total_lumens:>7.0f} {p.input_watts:>7.0f} "
          f"{'n/a' if e is None else f'{e:.0f}':>10} "
          f"{led_watts(p):>7.1f}  {p.source.name}")

scheme = [
    Luminaire("LT-01", pendant, W / 2, D / 2, 2400.0, layer="ambient",
              room="bedroom", watts=led_watts(pendant)),
    Luminaire("LT-02", bedside, 1100.0, 3300.0, 1200.0, layer="task",
              room="bedroom", watts=led_watts(bedside)),
    Luminaire("LT-03", bedside, 3100.0, 3300.0, 1200.0, layer="task",
              room="bedroom", watts=led_watts(bedside)),
    Luminaire("LT-04", strip, 400.0, 1800.0, 2400.0, layer="accent",
              room="bedroom", watts=led_watts(strip)),
]

out = Path(__file__).resolve().parents[1] / "out"

print()
print("THREE-LAYER SCHEME (as specified)")
g = lux_grid(ROOM, scheme, room="Bedroom 01", spacing=100.0)
print(" ", g.summary())
print(f"  {g.assessment_note()}")
ok, coarse, fine = converged(ROOM, scheme, spacing=100.0)
print(f"  grid converged at 100 mm: {ok} (Eavg {coarse:.2f} -> {fine:.2f} "
      f"at 50 mm)")
irc = interreflected_estimate(g, W, D, CEILING, surfaces=Surfaces())
print(f"  {irc.note}")
print(f"  => total average illuminance, direct + estimate: "
      f"{g.average + irc.low:.0f}-{g.average + irc.high:.0f} lx")
heatmap_svg(g, out / "bedroom-lux-3layer.svg", boundary=ROOM, scale=0.09,
            target=(100.0, 150.0))
print("  -> out/bedroom-lux-3layer.svg")

print()
print("TASK POINTS (what a direct calculation genuinely supports)")
tasks = [("reading, left pillow",  1100.0, 3150.0, 900.0),
         ("reading, right pillow", 3100.0, 3150.0, 900.0),
         ("floor, room centre",    2100.0, 1800.0,   0.0),
         ("wardrobe door face",     400.0, 1800.0, 850.0)]
for label, tx, ty, tz in tasks:
    e = point_illuminance(scheme, tx, ty, tz)
    print(f"  {label:24} {e:>6.0f} lx  (at {tz:.0f} mm)")

print()
print("NEGATIVE CASE: pendant only (the lone central fixture)")
g1 = lux_grid(ROOM, [scheme[0]], room="Bedroom 01 (pendant only)",
              spacing=100.0)
print(" ", g1.summary())
print(f"  reading at left pillow: "
      f"{point_illuminance([scheme[0]], 1100.0, 3150.0, 900.0):.0f} lx")
heatmap_svg(g1, out / "bedroom-lux-pendant-only.svg", boundary=ROOM,
            scale=0.09, target=(100.0, 150.0))
print("  -> out/bedroom-lux-pendant-only.svg")

print()
print("WHAT THE STAGE 5 RULES WILL ASSESS")
print("  (layer count, task illuminance and average lux -- NOT uniformity)")
for label, grid, lums in (("3 layers", g, scheme),
                          ("pendant only", g1, [scheme[0]])):
    layers = grid.layers_present()
    reading = point_illuminance(lums, 1100.0, 3150.0, 900.0)
    verdicts = [
        (f"layers >= 3", len(layers) >= 3, f"{len(layers)} ({', '.join(layers)})"),
        ("bedroom Eavg 100-300 lx", 100.0 <= grid.average <= 300.0,
         f"{grid.average:.0f} lx"),
        # A BAND, not a floor. A floor would pass a fitting that is far
        # too bright, which is the same error as adjudicating a metric
        # the engine cannot support -- one layer up.
        ("reading task 300-500 lx", 300.0 <= reading <= 500.0,
         f"{reading:.0f} lx"),
        ("power density <= 10 W/m2", (grid.power_density or 0) <= 10.0,
         f"{grid.power_density:.1f} W/m2"),
        ("uniformity", None, "not assessed -- direct calculation only"),
    ]
    print(f"  {label}:")
    for name, passed, measured in verdicts:
        mark = "n/a " if passed is None else ("PASS" if passed else "FAIL")
        print(f"      {mark}  {name:26} {measured}")
