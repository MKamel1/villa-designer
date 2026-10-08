"""Villa environment model: write the spec, check Revit's read-back against it, draw the site plan.

    PYTHONPATH=src python scripts/villa_env.py spec    # out/villa/env-spec.json
    (run revit/build_villa_env.py in Revit 2027; see its docstring)
    PYTHONPATH=src python scripts/villa_env.py check [--readback <path>]   # read-back vs the spec; exit 1 on mismatch
    PYTHONPATH=src python scripts/villa_env.py plan    # out/villa/env-site-plan.pdf/.png from the READ-BACK geometry
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe import villa_env as V
from archpipe.execution_context import ContextError, project_context

OUT = Path("out/villa")
TOL = 2.0     # mm


def _bbox_of(pts, z0, z1):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [min(xs), min(ys), z0, max(xs), max(ys), z1]


def check(spec: dict | None = None, rb: dict | None = None) -> list[str]:
    spec = spec or json.loads((OUT / "env-spec.json").read_text(encoding="utf-8"))
    rb = rb or json.loads((OUT / "env-readback.json").read_text(encoding="utf-8"))
    bad = []
    got_levels = {l["name"]: l["z"] for l in rb["levels"]}
    for l in spec["levels"]:
        if abs(got_levels.get(l["name"], 1e9) - l["z"]) > TOL:
            bad.append("level %s: %s vs %s" % (l["name"], got_levels.get(l["name"]), l["z"]))
    s = rb["site"]
    if abs(s["latitude"] - V.LATITUDE) > 1e-5 or abs(s["longitude"] - V.LONGITUDE) > 1e-5:
        bad.append("site location %s, %s" % (s["latitude"], s["longitude"]))
    if abs(((s["street_facade_azimuth"] - V.STREET_FACADE_AZIMUTH) + 180) % 360 - 180) > 0.1:
        bad.append("street facade azimuth %.2f, want %.1f" % (s["street_facade_azimuth"], V.STREET_FACADE_AZIMUTH))
    shapes = {x["id"]: x for x in rb["shapes"]}
    for e in spec["elements"]:
        got = shapes.get(e["id"])
        want = _bbox_of(e["pts"], e["z0"], e["z1"])
        if got is None or got["bbox"] is None:
            bad.append("missing %s" % e["id"])
        elif max(abs(a - b) for a, b in zip(got["bbox"], want)) > TOL:
            bad.append("%s bbox %s vs %s" % (e["id"], [round(v) for v in got["bbox"]], want))
    floors = {f["id"]: f for f in rb["floors"]}
    zs = {l["name"]: l["z"] for l in spec["levels"]}
    for sl in spec["slabs"]:
        got = floors.get(sl["id"])
        want_area = V.polygon_area(sl["pts"])
        if got is None:
            bad.append("missing slab %s" % sl["id"])
            continue
        if abs(got["area_m2"] - want_area) > 0.05:
            bad.append("slab %s area %.2f vs %.2f" % (sl["id"], got["area_m2"], want_area))
        if abs(got["bbox"][5] - zs[sl["level"]]) > TOL:
            bad.append("slab %s top %.0f vs %s" % (sl["id"], got["bbox"][5], zs[sl["level"]]))
    cols = rb["columns"]
    if len(cols) != 27:
        bad.append("columns: %d, want 9 x 3 storeys" % len(cols))
    for want_base, z0, z1 in (("B -1.80", V.B, V.GF), ("GF +1.20", V.GF, V.APT), ("APT +4.20 (not ours)", V.APT, V.ROOF)):
        row = [c for c in cols if c["base"] == want_base]
        if len(row) != 9:
            bad.append("%d columns based on %s, want 9" % (len(row), want_base))
        for c in row:
            if abs(c["bbox"][2] - z0) > TOL or abs(c["bbox"][5] - z1) > TOL:
                bad.append("column %s spans %.0f..%.0f, want %d..%d" % (c["id"], c["bbox"][2], c["bbox"][5], z0, z1))
        plan = sorted((round(c["bbox"][0]), round(c["bbox"][1])) for c in row)
        cad = sorted((x0, y0) for x0, y0, _, _ in V.COLUMNS)
        if row and any(abs(a[0] - b[0]) > TOL or abs(a[1] - b[1]) > TOL for a, b in zip(plan, cad)):
            bad.append("columns on %s do not sit on the CAD positions" % want_base)
    return bad


def plan():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle
    spec = json.loads((OUT / "env-spec.json").read_text(encoding="utf-8"))
    rb = json.loads((OUT / "env-readback.json").read_text(encoding="utf-8"))
    shapes = {x["id"]: x for x in rb["shapes"]}
    floors = {f["id"]: f for f in rb["floors"]}
    fig, ax = plt.subplots(figsize=(16.5, 11.7))          # A3 landscape

    def rect(bb, **kw):
        ax.add_patch(Rectangle((bb[0] / 1000, bb[1] / 1000), (bb[3] - bb[0]) / 1000, (bb[4] - bb[1]) / 1000, **kw))

    # polygons from the spec, drawn only when the built floor exists (read-back)
    for sl in spec["slabs"]:
        if sl["id"] in floors and sl["id"].startswith("yard"):
            ax.add_patch(Polygon([(x / 1000, y / 1000) for x, y in sl["pts"]], closed=True,
                                 fc="#d8e8c8" if sl["id"] == "yard-ours" else "#eeeeee", ec="#6a8a50", lw=0.8))
    if "slab-GF" in floors:
        ax.add_patch(Polygon([(x / 1000, y / 1000) for x, y in spec["footprint"]], closed=True, fc="#f4d9b0",
                             ec="k", lw=1.5, label="our villa (B + GF)"))
    if "slab-GF-front" in floors:
        rect(floors["slab-GF-front"]["bbox"], fc="#f9ead2", ec="k", lw=0.8, hatch="//")
    for sid, x in shapes.items():
        bb = x["bbox"]
        if bb is None:
            continue
        if sid.startswith("fence"):
            rect(bb, fc="#555555", ec="none")
        elif sid in ("neighbour-east", "neighbour-rear", "neighbour-rear-east", "sister"):
            rect(bb, fc="#c9c9d9", ec="#555577", lw=1)
            ax.text((bb[0] + bb[3]) / 2000, (bb[1] + bb[4]) / 2000, "%s\n%.1f m high" % (sid, (bb[5] - bb[2]) / 1000),
                    ha="center", va="center", fontsize=8)
        elif sid == "street":
            rect(bb, fc="#bbbbbb", ec="none")
            ax.text((bb[0] + bb[3]) / 2000, (bb[1] + bb[4]) / 2000, "STREET  +-0.00\n(width assumed)",
                    rotation=90, ha="center", va="center", fontsize=9)
        elif sid.endswith("-GF") or sid in ("core-shaft", "entrance-steps"):
            shaft = sid == "core-shaft"
            rect(bb, fc="#9ec5e8" if shaft else "#fbe3c8", ec="#8a6a40", lw=0.8, hatch="xx" if shaft else None)
            label = sid.replace("-GF", "").replace("core-", "")
            ax.text((bb[0] + bb[3]) / 2000, (bb[1] + bb[4]) / 2000, label, ha="center", va="center", fontsize=6,
                    rotation=0 if bb[3] - bb[0] > 2000 else 90)
        elif "-w" in sid and sid.split("-z")[-1] == "0":
            rect(bb, fc="#3060c0", ec="none")
    for c in rb["columns"]:
        if c["base"] == "GF +1.20":
            rect(c["bbox"], fc="k", ec="none")
    # true north arrow, from the READ-BACK azimuth of the street facade (model -x)
    az = rb["site"]["street_facade_azimuth"]
    # model -x (angle 180 deg) has azimuth az; azimuth grows clockwise, so true north is at angle az - 180
    theta = math.radians(az - 180.0)
    vx, vy = math.cos(theta), math.sin(theta)
    ox, oy = 30.0, -12.0
    ax.annotate("", xy=(ox + 2.5 * vx, oy + 2.5 * vy), xytext=(ox, oy), arrowprops=dict(arrowstyle="-|>", lw=2))
    ax.text(ox + 3.2 * vx, oy + 3.2 * vy, "N", ha="center", va="center", fontsize=14, weight="bold")
    px0, py0, px1, py1 = spec["plot"]
    ax.set_title("Villa environment model (read back from Revit): plot %.2f x %.2f m, sunken yard -1.80, fence top "
                 "+2.20, street facade faces %.0f deg" % ((px1 - px0) / 1000, (py1 - py0) / 1000, az), fontsize=11)
    ax.set_aspect("equal")
    ax.set_xlim(px0 / 1000 - 12, 53)
    ax.set_ylim(py0 / 1000 - 1, -4)
    ax.set_xlabel("model x (m)  -- plot-north (street) is left, rear is right")
    ax.set_ylabel("model y (m)  -- plot-east is up, sister villa below")
    ax.grid(alpha=0.2)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / ("env-site-plan." + ext), dpi=150, bbox_inches="tight")
    return OUT / "env-site-plan.pdf"


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv
    cmd = argv[1] if len(argv) > 1 else "spec"
    if cmd not in ("spec", "check", "plan"):
        raise SystemExit(__doc__)
    inputs = []
    modules = []
    if cmd == "check":
        rb_path = Path(argv[argv.index("--readback") + 1]) if "--readback" in argv else OUT / "env-readback.json"
        inputs = [OUT / "env-spec.json", rb_path]
    elif cmd == "plan":
        inputs = [OUT / "env-spec.json", OUT / "env-readback.json"]
        modules = ["matplotlib"]
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "villa-env",
            inputs=inputs,
            output=OUT,
            modules=modules,
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    if cmd == "spec":
        print(V.write(OUT / "env-spec.json"))
        return 0
    if cmd == "check":                   # check [--readback <path>]: the default is out/villa/env-readback.json
        rb = None
        if "--readback" in argv:
            path = Path(argv[argv.index("--readback") + 1])
            rb = json.loads(path.read_text(encoding="utf-8"))
            print("read-back:", path)
        bad = check(rb=rb)
        for b in bad:
            print("FAIL", b)
        print("ENV CHECK:", "PASS" if not bad else "%d FAIL" % len(bad))
        return 1 if bad else 0
    if cmd == "plan":
        print(plan())
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
