"""Whole-building daylight: many rooms, many levels, any plan shape, under a CIE overcast sky (daylight factor).

`radiance.py` handles ONE axis-aligned rectangular room built from a Revit extract (electric light and a daylight
example). This module is the general scene engine it lacked (client 2026-09-26: "definitely useful to enhance and
make practical"):

  * solids: boxes, extruded plan polygons (any shape, holes allowed), extruded section profiles (a sloping ramp),
    each face with its own material (a slab is floor on top and ceiling underneath);
  * walls along ANY line (not only axis-aligned) with window / door / open-hole openings; windows glazed, doors
    closed (opaque) or glazed, stated per opening;
  * rooms as plan polygons on any level; sensor grids at working-plane height, inset from the walls, points inside
    the polygon only;
  * one Radiance job for many cases (options), run on the Ubuntu compute node, results per room: average,
    minimum, median daylight factor and uniformity.

Daylight factor: interior illuminance / unobstructed horizontal illuminance under the CIE standard overcast sky
(gensky -c), in per cent. The sky is normalised to 10 000 lx horizontal (-B 55.866 W/m2 x 179 lm/W), so
DF % = lux / 100.

WHAT IS ASSUMED, STATED: reflectances are the constants in MATERIALS (not measured finishes); glazing uses a stated
normal transmittance converted with radiance.tn_to_transmissivity; frames and dirt are not modelled (maintenance
factor 1, as a clean-glass simulation); furniture is absent. Geometry is metres, z up.

VALIDATION (validate_cases): an unobstructed sensor must read ~100 %, a closed box ~0 %, and a simple side-lit box
must agree with the Metric Handbook 7th ed. p. 9-8 eq. (4) average daylight factor within a tolerance fixed
before the run (VALIDATION_TOLERANCE). Results are diagnostic until all three pass.
"""
from __future__ import annotations

import io
import json
import math
import statistics
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

from .radiance import CIE_BF, CIE_GF, CIE_RF, WHTEFFICACY, tn_to_transmissivity

SKY_B = 55.866                 # W/m2 horizontal diffuse: 10 000 lx at 179 lm/W (gensky -B)
HORIZONTAL_LUX = 10000.0
RTRACE_OPTS = ["-I+", "-h-", "-w", "-ab", "5", "-ad", "2048", "-as", "1024", "-aa", "0.15", "-ar", "512",
               "-lw", "2e-4"]           # medium accuracy; RTRACE_FINE re-runs the box to show the answer is stable
RTRACE_FINE = ["-I+", "-h-", "-w", "-ab", "7", "-ad", "8192", "-as", "4096", "-aa", "0.08", "-ar", "1024",
               "-lw", "5e-5"]
VALIDATION_TOLERANCE = 0.30    # pre-registered 2026-09-26: Radiance vs the MH eq. (4) box, relative


@dataclass(frozen=True)
class Material:
    name: str
    kind: str                  # "plastic" (reflectance) or "glass" (normal transmittance)
    value: float

    def rad(self) -> str:
        if self.kind == "glass":
            t = tn_to_transmissivity(self.value)
            return f"void glass {self.name}\n0\n0\n3 {t:.4f} {t:.4f} {t:.4f}\n"
        if self.kind == "plastic":
            v = self.value
            return f"void plastic {self.name}\n0\n0\n5 {v:.3f} {v:.3f} {v:.3f} 0 0\n"
        raise ValueError(f"unknown material kind {self.kind}")


MATERIALS = {m.name: m for m in (
    Material("floor", "plastic", 0.20), Material("wall", "plastic", 0.50), Material("ceiling", "plastic", 0.70),
    Material("ground", "plastic", 0.20), Material("context", "plastic", 0.35), Material("door", "plastic", 0.40),
    Material("glass", "glass", 0.70))}           # 0.70: clear double glazing (Metric Handbook p. 9-8)


@dataclass
class Face:
    points: list                # [(x, y, z), ...] counter-clockwise seen from the side the normal points to
    material: str


@dataclass
class Scene:
    faces: list = field(default_factory=list)
    rooms: list = field(default_factory=list)   # [{"id", "z", "polygon": [(x, y)], "name", ...}]
    notes: list = field(default_factory=list)

    def add(self, faces):
        self.faces.extend(faces)
        return self


# ---- geometry primitives ------------------------------------------------------------------------------------------
def _signed_area(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly))) / 2.0


def ccw(poly):
    """The plan polygon counter-clockwise (seen from above)."""
    return list(poly) if _signed_area(poly) > 0 else list(reversed(poly))


def with_holes(outer, holes):
    """A single Radiance polygon for an outer ring with holes: each hole (clockwise) is joined to the outer ring
    through a seam, the standard way Radiance represents holes."""
    ring = ccw(outer)
    for h in holes:
        h = list(reversed(ccw(h)))                 # holes run the other way
        # join at the hole vertex closest to an outer vertex
        best = min(((i, j) for i in range(len(ring)) for j in range(len(h))),
                   key=lambda ij: math.dist(ring[ij[0]], h[ij[1]]))
        i, j = best
        ring = ring[:i + 1] + h[j:] + h[:j + 1] + ring[i:]
    return ring


def prism_z(poly, z0, z1, top="floor", bottom="ceiling", side="wall", holes=()):
    """A plan polygon (with optional holes) extruded from z0 to z1: top, bottom and side faces."""
    outer = ccw(poly)
    cap = with_holes(outer, holes)
    faces = [Face([(x, y, z1) for x, y in cap], top),
             Face([(x, y, z0) for x, y in reversed(cap)], bottom)]
    for ring, sign in [(outer, 1)] + [(list(reversed(ccw(h))), -1) for h in holes]:
        for k in range(len(ring)):
            (xa, ya), (xb, yb) = ring[k], ring[(k + 1) % len(ring)]
            faces.append(Face([(xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1)], side))
    return faces


def box(x0, y0, z0, x1, y1, z1, material="context", top=None, bottom=None):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return prism_z([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, top or material, bottom or material, material)


def prism_section(profile, axis, a0, a1, material="context", top=None):
    """A section profile [(u, z), ...] extruded along `axis` ('x' or 'y') from a0 to a1: u is the other plan axis.
    Used for a sloping ramp or an infill whose top follows it."""
    prof = profile if _signed_area(profile) > 0 else list(reversed(profile))

    def p3(u, z, a):
        return (u, a, z) if axis == "y" else (a, u, z)

    a0, a1 = sorted((a0, a1))
    near = [p3(u, z, a0) for u, z in prof]
    far = [p3(u, z, a1) for u, z in reversed(prof)]
    # orientation: for axis 'y' the u-z plane seen from -y is x-right z-up, so the CCW profile faces -y
    faces = ([Face(near, material), Face(far, material)] if axis == "y"
             else [Face(list(reversed(near)), material), Face(list(reversed(far)), material)])
    for k in range(len(prof)):
        (ua, za), (ub, zb) = prof[k], prof[(k + 1) % len(prof)]
        quad = [p3(ua, za, a0), p3(ua, za, a1), p3(ub, zb, a1), p3(ub, zb, a0)]
        faces.append(Face(quad if axis == "y" else list(reversed(quad)), top if (top and zb > za - 1e-9 and
                                                                                 abs(ub - ua) > 1e-9) else material))
    return faces


def wall(p0, p1, z0, height, thickness, openings=(), material="wall"):
    """A wall on the centreline p0 -> p1 (any direction), with openings: dicts {offset (m from p0 to the opening's
    start), width, sill, head, kind: 'window' | 'glazed' (glazed door) | 'door' (closed, opaque) | 'hole'}.
    The solid parts are boxes in the wall's own frame; glazing is a pane in the wall's centre plane."""
    (xa, ya), (xb, yb) = p0, p1
    L = math.hypot(xb - xa, yb - ya)
    if L < 1e-6:
        return []
    ux, uy = (xb - xa) / L, (yb - ya) / L
    nx, ny = -uy, ux
    t = thickness / 2

    def quad(u0, u1, v0, v1, w):                      # a face at offset w across the wall
        return [(xa + ux * u0 + nx * w, ya + uy * u0 + ny * w, z0 + v0),
                (xa + ux * u1 + nx * w, ya + uy * u1 + ny * w, z0 + v0),
                (xa + ux * u1 + nx * w, ya + uy * u1 + ny * w, z0 + v1),
                (xa + ux * u0 + nx * w, ya + uy * u0 + ny * w, z0 + v1)]

    def solid(u0, u1, v0, v1):
        if u1 - u0 < 1e-6 or v1 - v0 < 1e-6:
            return []
        c = [(xa + ux * u + nx * w, ya + uy * u + ny * w) for u, w in ((u0, -t), (u1, -t), (u1, t), (u0, t))]
        return prism_z(c, z0 + v0, z0 + v1, material, material, material)

    ops = sorted((dict(o) for o in openings), key=lambda o: o["offset"])
    faces, u = [], 0.0
    for o in ops:
        a, b = max(0.0, o["offset"]), min(L, o["offset"] + o["width"])
        if b <= a:
            continue
        faces += solid(u, a, 0.0, height)
        faces += solid(a, b, 0.0, max(0.0, o.get("sill", 0.0)))
        faces += solid(a, b, min(height, o["head"]), height)
        v0, v1 = max(0.0, o.get("sill", 0.0)), min(height, o["head"])
        if o["kind"] in ("window", "glazed"):
            faces.append(Face(quad(a, b, v0, v1, 0.0), "glass"))   # ONE pane: Radiance glass is two-sided;
            #                                                        a second coincident pane would square T
        elif o["kind"] == "door":                     # closed leaf: the opening filled, door-coloured
            faces += [Face(f.points, "door") for f in solid(a, b, v0, v1)]
        u = max(u, b)
    faces += solid(u, L, 0.0, height)
    return faces


# ---- rooms and sensors ------------------------------------------------------------------------------------------------
def inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def _edge_distance(pt, poly):
    best = 1e9
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy or 1e-12
        s = max(0.0, min(1.0, ((pt[0] - x1) * dx + (pt[1] - y1) * dy) / L2))
        best = min(best, math.hypot(pt[0] - x1 - s * dx, pt[1] - y1 - s * dy))
    return best


def grid(room, spacing=0.5, height=0.85, inset=0.3):
    """Sensor points over a room polygon at working-plane height, `inset` m clear of its edges; a room too small
    for the inset gets a single point at its centroid."""
    poly = room["polygon"]
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    pts = []
    nx, ny = int((max(xs) - min(xs)) / spacing) + 1, int((max(ys) - min(ys)) / spacing) + 1
    ox = min(xs) + (max(xs) - min(xs) - (nx - 1) * spacing) / 2
    oy = min(ys) + (max(ys) - min(ys) - (ny - 1) * spacing) / 2
    for i in range(nx):
        for j in range(ny):
            p = (ox + i * spacing, oy + j * spacing)
            if inside(p, poly) and _edge_distance(p, poly) >= inset - 1e-9:
                pts.append((p[0], p[1], room["z"] + height))
    if not pts:
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        pts = [(cx, cy, room["z"] + height)]
    return pts


# ---- Radiance text -------------------------------------------------------------------------------------------------
def scene_rad(scene: Scene) -> str:
    used = sorted({f.material for f in scene.faces})
    out = [MATERIALS[m].rad() for m in used]
    for k, f in enumerate(scene.faces):
        pts = " ".join(f"{x:.4f} {y:.4f} {z:.4f}" for x, y, z in f.points)
        out.append(f"{f.material} polygon f{k}\n0\n0\n{3 * len(f.points)} {pts}\n")
    return "".join(out)


SKY_GLOW = ("skyfunc glow sky_glow\n0\n0\n4 1 1 1 0\nsky_glow source sky\n0\n0\n4 0 0 1 180\n"
            "skyfunc glow ground_glow\n0\n0\n4 1 1 1 0\nground_glow source ground\n0\n0\n4 0 0 -1 180\n")

RUN_SH = """#!/bin/bash
# archpipe daylight job: CIE overcast daylight factor for every case folder
set -euo pipefail
R="$HOME/archpipe/tools/radiance-6.0.1"
export PATH="$R/bin:$PATH" RAYPATH=".:$R/lib"
cd "$(dirname "$0")"
gensky -ang 45 0 -c -B {B} > sky.rad
cat sky_glow.rad >> sky.rad
for d in $(cat order.txt) ; do                     # validation cases first: a broken setup shows early
  ( cd "cases/$d" && oconv ../../sky.rad scene.rad > scene.oct && \\
    rtrace $(cat opts.txt) -n {n} scene.oct < points.txt > out.txt 2> rtrace.log ) || echo "FAILED $d" >> errors.txt
  echo "done $d $(date +%T)" >> progress.txt
done
touch DONE
"""


def write_job(cases: dict, folder: Path, workers: int = 30, fine=()) -> Path:
    """One folder per case (scene.rad, points.txt, rooms.json, opts.txt), plus the sky and run.sh; returns a
    .tar.gz. Cases named in `fine` are repeated as '<name>-fine' at RTRACE_FINE (a convergence check). Validation
    cases (names starting 'v-') run first."""
    cases = dict(cases)
    for name in fine:
        cases[name + "-fine"] = cases[name]
    folder = Path(folder)
    (folder / "cases").mkdir(parents=True, exist_ok=True)
    (folder / "sky_glow.rad").write_text(SKY_GLOW, encoding="ascii")
    (folder / "run.sh").write_text(RUN_SH.format(B=SKY_B, n=workers), encoding="ascii", newline="\n")
    order = sorted(cases, key=lambda n: (not n.startswith("v-"), n))
    (folder / "order.txt").write_text("\n".join(order) + "\n", encoding="ascii", newline="\n")
    for name, scene in cases.items():
        d = folder / "cases" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "scene.rad").write_text(scene_rad(scene), encoding="ascii")
        rooms, lines = [], []
        for r in scene.rooms:
            pts = grid(r, **r.get("grid", {}))
            rooms.append(dict({k: v for k, v in r.items() if k != "polygon"}, polygon=[list(p) for p in r["polygon"]],
                              first=len(lines), count=len(pts)))
            lines += [f"{x:.4f} {y:.4f} {z:.4f} 0 0 1" for x, y, z in pts]
        (d / "points.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
        (d / "opts.txt").write_text(" ".join(RTRACE_FINE if name.endswith("-fine") else RTRACE_OPTS),
                                    encoding="ascii")
        (d / "rooms.json").write_text(json.dumps({"rooms": rooms, "notes": scene.notes}, indent=1), encoding="utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(folder, arcname=".")
    tgz = folder.with_suffix(".tar.gz")
    tgz.write_bytes(buf.getvalue())
    return tgz


def df_percent(r, g, b):
    return WHTEFFICACY * (CIE_RF * r + CIE_GF * g + CIE_BF * b) / HORIZONTAL_LUX * 100.0


def read_case(case_dir: Path) -> dict:
    """Per-room daylight factor from a finished case folder."""
    meta = json.loads((case_dir / "rooms.json").read_text(encoding="utf-8"))
    vals = [float(v) for v in (case_dir / "out.txt").read_text().split()]
    n = sum(r["count"] for r in meta["rooms"])
    if len(vals) != 3 * n:
        raise RuntimeError(f"{case_dir.name}: {len(vals)} numbers for {n} points")
    df = [df_percent(*vals[3 * i:3 * i + 3]) for i in range(n)]
    out = {}
    for r in meta["rooms"]:
        v = df[r["first"]:r["first"] + r["count"]]
        avg = sum(v) / len(v)
        out[r["id"]] = {"name": r.get("name", r["id"]), "level": r.get("level"), "points": len(v),
                        "adf": round(avg, 2), "min": round(min(v), 2), "median": round(statistics.median(v), 2),
                        "uniformity": round(min(v) / avg, 2) if avg > 0 else 0.0}
    return {"rooms": out, "notes": meta.get("notes", [])}


# ---- validation cases ---------------------------------------------------------------------------------------------
def mh_adf(T, W, theta_deg, A, R, M=1.0):
    """Metric Handbook 7th ed. p. 9-8 eq. (4): df = T x W x theta x M / [A (1 - R^2)] per cent."""
    return T * W * theta_deg * M / (A * (1 - R * R))


def validation_cases():
    """Three scenes with known answers: open ground (DF ~100 %), a closed box (~0 %), a side-lit box room compared
    with the Metric Handbook formula. Returns {name: Scene} and the formula's expectation for the box."""
    ground = Scene().add([Face([(-50, -50, 0), (50, -50, 0), (50, 50, 0), (-50, 50, 0)], "ground")])
    ground.rooms = [{"id": "open", "z": 0.0, "polygon": [(-1, -1), (1, -1), (1, 1), (-1, 1)],
                     "grid": {"spacing": 1.0, "inset": 0.0}}]
    W, D, H = 4.0, 5.0, 2.8                                 # room 4 m wide (window wall) x 5 m deep x 2.8 m
    t = 0.2

    def room(openings):
        s = Scene().add([Face([(-50, -50, -t), (50, -50, -t), (50, 50, -t), (-50, 50, -t)], "ground")])
        s.add(box(0, 0, -t, W, D, 0, "floor", top="floor"))                  # slab: floor on top
        s.add(box(0, 0, H, W, D, H + t, "ceiling", bottom="ceiling"))        # roof: ceiling underneath
        s.add(wall((0, 0), (W, 0), 0, H, t, openings))                      # window wall faces -y (open)
        s.add(wall((W, 0), (W, D), 0, H, t))
        s.add(wall((W, D), (0, D), 0, H, t))
        s.add(wall((0, D), (0, 0), 0, H, t))
        s.rooms = [{"id": "room", "z": 0.0, "polygon": [(t / 2, t / 2), (W - t / 2, t / 2), (W - t / 2, D - t / 2),
                                                          (t / 2, D - t / 2)], "grid": {"spacing": 0.25, "inset": 0.0}}]
        return s
    ww, wh, sill = 2.0, 1.5, 0.9
    lit = room([{"offset": (W - ww) / 2, "width": ww, "sill": sill, "head": sill + wh, "kind": "window"}])
    dark = room([])
    wi, di, hi = W - t, D - t, H                            # interior (to the wall faces)
    area = 2 * (wi * di) + 2 * (wi * hi) + 2 * (di * hi)
    floor_, ceil_, walls_ = wi * di, wi * di, area - 2 * wi * di
    R = (floor_ * MATERIALS["floor"].value + ceil_ * MATERIALS["ceiling"].value +
         walls_ * MATERIALS["wall"].value) / area
    expect = mh_adf(MATERIALS["glass"].value, ww * wh, 90.0, area, R)
    return {"v-open": ground, "v-dark": dark, "v-box": lit}, {"v-box": round(expect, 2), "R": round(R, 3),
                                                              "A": round(area, 2)}


def validate(results: dict, expectation: dict) -> dict:
    """The three checks; all must pass before any other number from the same run is reported as more than
    diagnostic."""
    op = results["v-open"]["rooms"]["open"]["adf"]
    dk = results["v-dark"]["rooms"]["room"]["adf"]
    bx = results["v-box"]["rooms"]["room"]["adf"]
    ex = expectation["v-box"]
    rel = abs(bx - ex) / ex
    checks = {"open ground ~100 %": {"value": op, "pass": abs(op - 100) <= 3},
              "closed box ~0 %": {"value": dk, "pass": dk <= 0.05},
              "box vs Metric Handbook eq. (4)": {"radiance": bx, "formula": ex, "relative": round(rel, 3),
                                                 "tolerance": VALIDATION_TOLERANCE,
                                                 "pass": rel <= VALIDATION_TOLERANCE}}
    if "v-box-fine" in results:                       # the working settings against fine ones: the answer is stable
        fn = results["v-box-fine"]["rooms"]["room"]["adf"]
        d = abs(bx - fn) / fn if fn else 1.0
        checks["medium vs fine ambient settings (box)"] = {"medium": bx, "fine": fn, "relative": round(d, 3),
                                                            "tolerance": 0.10, "pass": d <= 0.10}
    return {"checks": checks, "all_pass": all(c["pass"] for c in checks.values())}
