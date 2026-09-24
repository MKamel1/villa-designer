"""Radiance adapter: real Revit geometry + explicit photometry -> a physical
lighting simulation independent of the analytical (`lighting.py`) and
Cycles-render (`blender/`) engines.

Called from `scripts/worker_entry.py`, on the Ubuntu compute node where
official Radiance 6.0 patch 1 is installed (ADR-0003). This module never
invokes Radiance itself during authoring on Windows -- every function that
shells out funnels through `_run`, so a test can replace it and every
argument list is built by a small, separately-testable function. Structured
argument lists only; `shell=True` and string-interpolated commands are never
used, and light asset names are resolved to basenames inside `ies_dir`
before touching the filesystem.

UNITS. The extract is millimetres (matching `blender/build_scene.py` and
`lighting.py`); Radiance geometry is metres. `mm()` is the single place that
conversion happens.

WHAT THIS MODULE ASSUMES, STATED RATHER THAN HIDDEN

* **Single level.** Fixture and furniture heights are read directly as
  "above this room's floor", matching `blender/build_scene.py`'s
  `build_lights`. A model whose walls span more than one level raises
  rather than silently picking one.
* **One axis-aligned rectangular room.** The rectilinear wall-minus-opening
  decomposition below only has to handle axis-aligned rectangles; anything
  else raises `RadianceError` naming what was found. `lighting.py`'s
  `lux_grid` handles arbitrary polygons because it depends on `shapely`;
  this module is asked to use the standard library only, so the room shape
  it accepts is deliberately narrower.
* **Reflectances are the stated constants in `REFLECTANCE`**, not derived
  from any Revit paint colour -- `blender/build_scene.py`'s own comment
  and CLAUDE.md's "Revit display colours are not measured reflectance" say
  why. A caller-supplied mesh's `material.rgb` is never read for physics.
* **Doors are opaque in BOTH scenes**, filled with the wall's own
  material rather than cut as a hole or modelled as a distinct leaf --
  a stated simplification (no door-mesh geometry is placed), applied to
  the electric-light scene too so a door is not, incorrectly, an open
  aperture that would leak ambient-bounce light between rooms it does not
  actually connect.
* **Windows get an assumed, stated glazing transmittance** (`GLAZING_
  TRANSMITTANCE`) converted to Radiance's `glass` transmissivity by the
  standard Tn -> transmissivity formula distributed with Radiance's own
  `glaze` utility. This is illustrative; no real product was measured.
* **The daylight sky is a normalised CIE overcast sky at a fixed, stated
  sun angle** (`SKY_ALTITUDE_DEG`/`SKY_AZIMUTH_DEG`), not a real place or
  date -- `gensky -ang` is used instead of `gensky month day time`
  specifically so no calendar date reads as a real site.
* **Optional caller-supplied geometry is PER ITEM, not a global key.** A
  furniture/casework item may carry its own `item['meshes']`; an opening
  may carry its own `opening['meshes']`. Each mesh is
  `{'vertices_mm': [[x,y,z],...], 'triangles': [[i,j,k],...],
  'material': {...}}` in world coordinates. An item without `meshes` falls
  back to its measured proxy box (`bbox_center_mm`/`at` + `size_mm`/
  `size`); an item with neither meshes nor enough fields for a box is
  reported by identity as missing geometry rather than silently dropped.
  An opening mesh's `material` carries `'transparency'` (0..100) and
  `'name'`; a mesh classifies as glazing if its transparency is nonzero or
  its name mentions "glass"/"glaz", and as an opaque frame otherwise. A
  window with meshes but none classifying as glazing, or with no meshes at
  all, falls back to a plain glazing rectangle spanning the opening; this
  fallback and any missing-geometry identities are disclosed in
  `simulate()`'s report. Revit's fixture-housing geometry is deliberately
  NOT added as an extra obstacle anywhere in this module: the IES
  photometry already represents that fixture's optics (the light already
  "knows" the housing blocks or diffuses it), so modelling the housing
  again would double-count it.

GLOSSARY. IES: Illuminating Engineering Society photometric file format
(`.ies`) describing a fixture's candela distribution. CIE: Commission
Internationale de l'Eclairage, the body whose overcast-sky and colour
conventions Radiance implements. RAYPATH: the environment variable
Radiance's own tools use at RUNTIME to find support files (`.cal`
calculation files, `source.rad`, etc.) inside `<install>/lib` -- distinct
from `ies2rad -l`, which is an OUTPUT option (see `ies2rad_argv`). cd:
candela. lx: lux. W/m2: watts per square metre, the unit `rtrace -I`
irradiance is reported in before `_lux()` converts it. `-ab`/`-ad`/`-aa`:
`rtrace`'s ambient-bounce count, ambient divisions and ambient accuracy,
which together control how finely diffuse interreflection is sampled.

PHOTOMETRIC CONVERSION. `rtrace -I+` returns irradiance as an RGB triplet
in W/m2. Radiance's own convention for recovering lux from that triplet is
documented in its `color.h` (`WHTEFFICACY = 179`; `CIE_rf/gf/bf =
0.265074126 / 0.670114631 / 0.064811243`, the "equal energy white 380-780nm"
luminous efficacy and CIE luminance weighting used throughout the toolkit).
`_lux()` below applies exactly that formula and nothing else.

RUNTIME LIBRARY SEARCH. Radiance tools resolve their own support files via
the `RAYPATH` environment variable, not any command-line option -- `_run`
below derives `<install>/lib` from the absolute path of the tool it is
about to execute and sets `RAYPATH=.:<install>/lib` in a COPY of the
process environment for that one child process, never touching the parent
process's own environment.

SINGLE-STOREY ONLY. `single_level_elevation_mm` does not merely reject a
room whose walls disagree on level -- it rejects any elevation other than
0. Furniture, fixtures and grid heights are all read as "above this room's
floor" with no per-level offset added back in, which only means what it
says when the floor sits at world Z=0; a room on an upper storey is
refused outright rather than silently mismeasured.

WHAT THIS MODULE DOES NOT CLAIM. No result here is a code-compliance or
uniformity ("EN 12464-1 U0") verdict -- see `docs/decisions/
ADR-0009-no-uniformity-verdict-from-direct-light.md`, whose reasoning
applies just as much to a bounce-limited Radiance run as to the direct-only
analytical engine: a finite ambient-bounce count is still an approximation
of "total" illuminance, and the report says so on every grid.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

MM_TO_M = 0.001

# Optical reflectance assumptions, stated rather than read from any Revit
# display colour. Identical to `blender/build_scene.py`'s REFLECTANCE, so
# the Radiance and Cycles engines describe the same assumed room.
REFLECTANCE = {"wall": 0.6, "floor": 0.25, "ceiling": 0.8, "furniture": 0.35}

WORKING_PLANE_MM = 850.0
SPACING_MM = 250.0
ROOM_INSET_MM = 150.0
MAINTENANCE_FACTOR = 0.8
AMBIENT_BOUNCES = (0, 4)          # direct-only, then direct + reflected

# Illustrative only -- see the module docstring. Not a measured product and
# not a real site.
GLAZING_TRANSMITTANCE = 0.75      # assumed clear double-glazing, normal Tn
GROUND_REFLECTANCE = 0.20         # exterior ground, distinct from the
                                   # interior floor's 0.25
SKY_ALTITUDE_DEG = 45.0
SKY_AZIMUTH_DEG = 0.0

# `gensky -B` sets horizontal diffuse IRRADIANCE in W/m2 (not lux); this is
# the stated normalisation target, chosen as a round number rather than any
# real climate figure. `-B` = target_lux / WHTEFFICACY (defined below).
SKY_TARGET_EXTERIOR_LUX = 10000.0
SKY_CHECK_TOLERANCE = 0.03

WORKERS_MIN, WORKERS_MAX = 1, 8
MIN_TIMEOUT_S, MAX_TIMEOUT_S = 30, 3600

REQUIRED_TOOLS = ("rtrace", "oconv", "ies2rad", "xform", "gensky",
                   "gendaylit", "rpict", "rcalc", "getinfo", "pvalue",
                   "pfilt", "genbox")

# Radiance photometric conversion, from src/common/color.h:
#   #define WHTEFFICACY   179.   /* equal energy white 380-780nm */
#   CIE_rf=.265074126  CIE_gf=.670114631  CIE_bf=.064811243
WHTEFFICACY = 179.0
CIE_RF, CIE_GF, CIE_BF = 0.265074126, 0.670114631, 0.064811243

# Isotropic-source synthetic physics check. Same fixture as
# `lighting.py.verify()`'s hand-calculated probe, at a distance chosen so
# the expected answer is a round number: E = I/d^2 = 1000/4 = 250 lx.
PHYSICS_CANDELA = 1000.0
PHYSICS_DISTANCE_M = 2.0
PHYSICS_TOLERANCE = 0.02

OPENING_FIT_TOLERANCE_MM = 1e-3


class RadianceError(RuntimeError):
    """A Radiance input we would not trust, or a check that failed."""


def mm(v: float) -> float:
    """Millimetres -> metres. The only place this conversion happens."""
    return float(v) * MM_TO_M


# --------------------------------------------------------------------- tools

@dataclass(frozen=True)
class Tools:
    """Resolved paths to every Radiance executable this module calls."""

    bin: dict
    lib: Path

    @classmethod
    def resolve(cls, install: Path) -> "Tools":
        install = Path(install).resolve()
        binmap = {}
        missing = []
        for name in REQUIRED_TOOLS:
            p = install / "bin" / name
            if p.is_file():
                binmap[name] = p
            else:
                missing.append(name)
        if missing:
            raise RadianceError(
                f"Radiance install at {install} is missing: {', '.join(missing)}")
        lib = install / "lib"
        if not lib.is_dir():
            raise RadianceError(f"Radiance install at {install} has no lib/ directory")
        return cls(bin=binmap, lib=lib)

    def __getitem__(self, name: str) -> Path:
        return self.bin[name]


def clamp_workers(n: int) -> int:
    """Bound process count to 1..8, whatever was asked for."""
    return max(WORKERS_MIN, min(WORKERS_MAX, int(n)))


def _timeout_for(work_units: int, *, base: int = 60, per_unit: float = 0.5) -> int:
    """A bounded, workload-scaled timeout. Never unbounded, never too short
    to let a real run finish."""
    return max(MIN_TIMEOUT_S, min(MAX_TIMEOUT_S, int(base + per_unit * work_units)))


def _child_env(tool_path: Path) -> dict:
    """A COPY of the process environment with `RAYPATH` set for one child,
    never a mutation of `os.environ` itself.

    `RAYPATH=.:<install>/lib` is how Radiance tools find their own support
    files (`.cal` calculation files, `source.rad`, etc.) at runtime -- NOT
    `ies2rad -l`, which is an output-location option (see
    `ies2rad_argv`'s docstring). `<install>/lib` is derived from the
    absolute path of the executable about to run (`<install>/bin/tool`),
    and `<install>/bin` is prepended to `PATH` so a tool that shells out to
    a sibling tool (as some Radiance scripts do) still finds it.
    """
    tool_path = Path(tool_path).resolve()
    install_bin = tool_path.parent
    install_lib = install_bin.parent / "lib"
    env = os.environ.copy()
    env["RAYPATH"] = os.pathsep.join([".", str(install_lib)])
    env["PATH"] = os.pathsep.join([str(install_bin), env.get("PATH", "")])
    return env


def _run(argv: list, *, cwd: Path, timeout: int, stdout_path: Path,
         stdin_path: Path | None = None) -> None:
    """Execute one Radiance tool as a structured argument list.

    Never `shell=True`; every element of `argv` is a plain string or
    `Path`, so nothing here can be reinterpreted by a shell. Standard
    output and standard error are captured to SEPARATE files -- several
    Radiance tools (`oconv`, `xform`, `gensky`) write their actual product
    to stdout the way a shell pipeline would redirect it, and merging
    stderr into that stream would silently corrupt a binary octree or
    splice a warning line into scene text. `stdout_path` is therefore not
    just a log; for those tools it IS the output file. A non-zero exit or
    a timeout raises with a tail of both streams -- silent partial output
    is the one outcome this function must not produce.
    """
    env = _child_env(Path(argv[0]))
    argv = [str(a) for a in argv]
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path = stdout_path.parent / (stdout_path.name + ".stderr.log")
    stdin = open(stdin_path, "rb") if stdin_path else subprocess.DEVNULL
    try:
        with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
            try:
                completed = subprocess.run(
                    argv, cwd=str(cwd), stdin=stdin, stdout=out, stderr=err,
                    timeout=timeout, env=env)
            except subprocess.TimeoutExpired as exc:
                raise RadianceError(
                    f"{argv[0]} timed out after {timeout}s: {' '.join(argv)}") from exc
    finally:
        if stdin is not subprocess.DEVNULL:
            stdin.close()
    if completed.returncode:
        out_tail = stdout_path.read_bytes()[-1000:].decode("utf-8", "replace")
        err_tail = stderr_path.read_bytes()[-1000:].decode("utf-8", "replace")
        raise RadianceError(
            f"{argv[0]} exited {completed.returncode}: {' '.join(argv)}\n"
            f"stdout: {out_tail}\nstderr: {err_tail}")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _require_file(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise RadianceError(f"expected a fresh, non-empty output at {path}, found nothing")
    return path


def _capture(path: Path) -> str:
    _require_file(path)
    return path.read_text()


# ------------------------------------------------------------- pure vectors

def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _scale(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def rect_polygon(origin, e_u, e_v, u0, v0, u1, v1, outward) -> list:
    """The four corners of an axis-in-a-plane rectangle, wound so its
    Radiance front face (right-hand rule on vertex order) matches
    `outward`.

    `origin` + `e_u`*u + `e_v`*v parameterises the plane; `outward` need
    only point roughly the right way, since only its sign against the
    default winding's normal is used.
    """
    p00 = _add(origin, _add(_scale(e_u, u0), _scale(e_v, v0)))
    p10 = _add(origin, _add(_scale(e_u, u1), _scale(e_v, v0)))
    p11 = _add(origin, _add(_scale(e_u, u1), _scale(e_v, v1)))
    p01 = _add(origin, _add(_scale(e_u, u0), _scale(e_v, v1)))
    pts = [p00, p10, p11, p01]
    normal = _cross(_sub(p10, p00), _sub(p01, p00))
    if _dot(normal, outward) < 0:
        pts.reverse()
    return pts


def polygon_normal(points: list) -> tuple:
    """Outward normal implied by a polygon's vertex order, for tests."""
    return _cross(_sub(points[1], points[0]), _sub(points[-1], points[0]))


# --------------------------------------------------------- rectangle-minus-hole

def rect_minus_rect(outer: tuple, hole: tuple) -> list:
    """`outer` (u0,v0,u1,v1) with `hole` clipped-and-subtracted, as up to 4
    axis-aligned rectangles: a picture-frame decomposition (bottom and top
    full-width strips, left and right strips at the hole's own height, so
    no piece overlaps another).

    Returns `[outer]` unchanged if `hole` does not overlap it.
    """
    ox0, oy0, ox1, oy1 = outer
    hx0 = max(hole[0], ox0); hx1 = min(hole[2], ox1)
    hy0 = max(hole[1], oy0); hy1 = min(hole[3], oy1)
    if hx0 >= hx1 or hy0 >= hy1:
        return [outer]
    pieces = []
    if hy0 > oy0:
        pieces.append((ox0, oy0, ox1, hy0))
    if hy1 < oy1:
        pieces.append((ox0, hy1, ox1, oy1))
    if hx0 > ox0:
        pieces.append((ox0, hy0, hx0, hy1))
    if hx1 < ox1:
        pieces.append((hx1, hy0, ox1, hy1))
    return pieces


def decompose_rect(outer: tuple, holes: list) -> list:
    """`outer` with every rectangle in `holes` removed, one at a time."""
    pieces = [outer]
    for hole in holes:
        pieces = [p for piece in pieces for p in rect_minus_rect(piece, hole)]
    return pieces


def _holes_overlap(holes: list) -> bool:
    for i, a in enumerate(holes):
        for b in holes[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                return True
    return False


# ------------------------------------------------------------------- .rad text

def _polygon_prim(material: str, name: str, points: list) -> str:
    coords = "\n".join(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}" for p in points)
    return f"{material} polygon {name}\n0\n0\n{3 * len(points)}\n{coords}\n"


def _plastic(name: str, reflectance: float) -> str:
    """An achromatic diffuse material at exactly `reflectance`.

    Equal R=G=B means the CIE-weighted luminance `_lux()` recovers is
    `reflectance` itself (the weights sum to 1.0), so "a 0.6 wall" reads
    back as 0.6 regardless of the conversion's channel weighting -- the
    same reasoning `blender/build_scene.py:surface()` uses for a stated
    reflectance under a tinted render, simplified here because no hue is
    being carried.
    """
    r = max(0.0, min(0.99, reflectance))
    return f"void plastic {name}\n0\n0\n5 {r} {r} {r} 0 0\n"


def _glass(name: str, transmissivity: float) -> str:
    t = max(0.0, min(1.0, transmissivity))
    return f"void glass {name}\n0\n0\n3 {t} {t} {t}\n"


def tn_to_transmissivity(tn: float) -> float:
    """Normal visible transmittance -> Radiance `glass` transmissivity.

    The standard conversion distributed with Radiance's `glaze` utility
    (Ward's daylighting scripts). `glass`'s parameter is NOT the physical
    transmittance -- Radiance derives the material's actual
    Fresnel-corrected transmittance from it internally -- which is why a
    stated Tn is converted rather than used directly.
    """
    if not 0.0 < tn <= 1.0:
        raise RadianceError(f"glazing transmittance must be in (0, 1], got {tn}")
    return (math.sqrt(0.8402528435 + 0.0072522239 * tn * tn) - 0.9166530661) / 0.0036261119 / tn


# ---------------------------------------------------------------- room/levels

def room_rectangle(room: dict) -> tuple:
    """The room boundary as an axis-aligned rectangle (x0,y0,x1,y1) mm, or
    raise -- this module supports exactly that shape, stated in the module
    docstring."""
    boundary = room.get("boundary") or []
    if len(boundary) != 4:
        raise RadianceError(
            f"room {room.get('id', room.get('name'))!r} has {len(boundary)} boundary "
            f"points; only a 4-point axis-aligned rectangular room is supported")
    xs = sorted({round(p[0], 3) for p in boundary})
    ys = sorted({round(p[1], 3) for p in boundary})
    if len(xs) != 2 or len(ys) != 2:
        raise RadianceError(
            f"room {room.get('id', room.get('name'))!r} boundary is not an "
            f"axis-aligned rectangle: x values {xs}, y values {ys}")
    return xs[0], ys[0], xs[1], ys[1]


def level_elevation_mm(data: dict, level_id) -> float:
    for lv in data.get("levels", []):
        if lv["id"] == level_id:
            return lv.get("elevation") or 0.0
    return 0.0


def single_level_elevation_mm(data: dict, room: dict) -> float:
    """Elevation shared by the room and every wall, or raise.

    Fixture/furniture heights are read as "above this floor" without their
    own level offset (matching `blender/build_scene.py:build_lights`),
    which only means what it says when everything is on one level.
    """
    ids = {room.get("level")} | {w.get("level") for w in data.get("walls", [])}
    ids.discard(None)
    elevations = {round(level_elevation_mm(data, i), 3) for i in ids} or {0.0}
    if len(elevations) > 1:
        raise RadianceError(
            f"room and walls span more than one level elevation {sorted(elevations)}; "
            f"multi-level geometry is not supported")
    elevation = elevations.pop() if elevations else 0.0
    if abs(elevation) > 1e-6:
        raise RadianceError(
            f"room is at elevation {elevation:.1f} mm; only a ground-floor-equivalent "
            f"elevation of 0 is supported -- furniture, fixture and grid heights are all "
            f"read as floor-relative with no per-level offset added back in")
    return elevation


# --------------------------------------------------------------- wall geometry

@dataclass(frozen=True)
class WallOpening:
    id: str
    kind: str
    u0: float
    v0: float
    u1: float
    v1: float


def _wall_openings(wall: dict, openings: list, length_mm: float, height_mm: float) -> list:
    out = []
    for o in openings:
        if o.get("host") != wall["id"]:
            continue
        width, height = o.get("width"), o.get("height")
        at, sill = o.get("at"), o.get("sill")
        if not width or not height or at is None or sill is None:
            raise RadianceError(f"opening {o.get('id')} is missing width/height/at/sill")
        u0, u1 = at - width / 2.0, at + width / 2.0
        v0, v1 = sill, sill + height
        tol = OPENING_FIT_TOLERANCE_MM
        if u0 < -tol or u1 > length_mm + tol or v0 < -tol or v1 > height_mm + tol:
            raise RadianceError(
                f"opening {o.get('id')} ({u0:.1f}..{u1:.1f}, {v0:.1f}..{v1:.1f} mm) "
                f"does not fit its host wall ({length_mm:.1f} x {height_mm:.1f} mm)")
        out.append(WallOpening(o["id"], o.get("kind", ""), u0, v0, u1, v1))
    holes = [(o.u0, o.v0, o.u1, o.v1) for o in out]
    if _holes_overlap(holes):
        raise RadianceError(f"overlapping openings on wall {wall['id']} are not supported")
    return out


def wall_polygons(wall: dict, openings: list, elevation_mm: float, *,
                  fill_doors: bool) -> tuple:
    """A wall's opaque geometry as a list of (points_m, material) plus the
    window openings actually cut, for the caller to glaze.

    Modelled as a true solid of the wall's real thickness: two faces (each
    with its own hole-minus-opening decomposition) plus reveal quads
    bridging them around every hole, so an oblique ray through a window is
    genuinely shadowed by the jamb rather than passing through a
    zero-thickness plane. `fill_doors` treats door-kind openings as solid
    wall instead of a hole -- the daylight scene's "doors are opaque"
    requirement -- by simply excluding them from the hole list. Wall end
    caps are not modelled: the extract's walls already extend past the
    room's corners to interlock (LEARNINGS.md, "DirectShape rotation"
    entry's neighbour on corner geometry), so an adjoining wall covers
    them.
    """
    x1, y1 = mm(wall["start"][0]), mm(wall["start"][1])
    x2, y2 = mm(wall["end"][0]), mm(wall["end"][1])
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-6:
        raise RadianceError(f"wall {wall['id']} has zero length")
    t = wall.get("thickness")
    h = wall.get("height")
    if not t or t <= 0 or not h or h <= 0:
        raise RadianceError(f"wall {wall['id']} needs a positive thickness and height")
    t, h = mm(t), mm(h)
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux                    # left-hand normal, matches build_scene.py

    length_mm = length / MM_TO_M
    height_mm = h / MM_TO_M
    all_openings = _wall_openings(wall, openings, length_mm, height_mm)
    windows = [o for o in all_openings if o.kind == "window"]
    holes_for_solid = (windows if fill_doors else all_openings)

    z0 = mm(elevation_mm)
    origin = (x1, y1, z0)
    e_u = (ux, uy, 0.0)
    e_v = (0.0, 0.0, 1.0)
    e_n = (nx, ny, 0.0)
    half_t = t / 2.0

    holes_m = [(mm(o.u0), mm(o.v0), mm(o.u1), mm(o.v1)) for o in holes_for_solid]
    polys = []
    for offset, outward in ((half_t, e_n), (-half_t, _scale(e_n, -1.0))):
        face_origin = _add(origin, _scale(e_n, offset))
        for u0, v0, u1, v1 in decompose_rect((0.0, 0.0, length, h), holes_m):
            polys.append((rect_polygon(face_origin, e_u, e_v, u0, v0, u1, v1, outward),
                         "wall"))

    for o in holes_for_solid:
        u0, v0, u1, v1 = mm(o.u0), mm(o.v0), mm(o.u1), mm(o.v1)
        # Left jamb (u=u0), right jamb (u=u1): plane spans thickness x height.
        for u, outward in ((u0, _scale(e_u, -1.0)), (u1, e_u)):
            reveal_origin = _add(origin, _add(_scale(e_u, u), _scale(e_n, -half_t)))
            polys.append((rect_polygon(reveal_origin, e_n, e_v, 0.0, v0, t, v1, outward),
                         "wall"))
        # Sill (v=v0), head/lintel (v=v1): plane spans thickness x width.
        for v, outward in ((v0, _scale(e_v, -1.0)), (v1, e_v)):
            reveal_origin = _add(origin, _add(_scale(e_v, v), _scale(e_n, -half_t)))
            polys.append((rect_polygon(reveal_origin, e_n, e_u, 0.0, u0, t, u1, outward),
                         "wall"))

    return polys, windows


def floor_polygon(x0, y0, x1, y1, elevation_mm) -> list:
    z = mm(elevation_mm)
    return rect_polygon((mm(x0), mm(y0), z), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                       0.0, 0.0, mm(x1 - x0), mm(y1 - y0), (0.0, 0.0, 1.0))


def ceiling_polygon(x0, y0, x1, y1, elevation_mm, height_mm) -> list:
    z = mm(elevation_mm + height_mm)
    return rect_polygon((mm(x0), mm(y0), z), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                       0.0, 0.0, mm(x1 - x0), mm(y1 - y0), (0.0, 0.0, -1.0))


def room_wall_height_mm(data: dict, room: dict) -> float:
    if room.get("ceiling_height"):
        return room["ceiling_height"]
    heights = {w.get("height") for w in data.get("walls", [])
              if w.get("level") == room.get("level") and w.get("height")}
    if len(heights) == 1:
        return heights.pop()
    raise RadianceError("room ceiling height cannot be determined "
                        "(no ceiling_height and walls disagree on height)")


# --------------------------------------------------------------- furniture

@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float  # mm

    def crosses(self, plane_mm: float) -> bool:
        return self.z0 <= plane_mm <= self.z1

    def contains_xy(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1


def _box_polygons(box: Box, material: str) -> list:
    x0, y0, z0 = mm(box.x0), mm(box.y0), mm(box.z0)
    x1, y1, z1 = mm(box.x1), mm(box.y1), mm(box.z1)
    faces = [
        ((x0, y0, z0), (1, 0, 0), (0, 1, 0), x1 - x0, y1 - y0, (0, 0, -1)),  # bottom
        ((x0, y0, z1), (1, 0, 0), (0, 1, 0), x1 - x0, y1 - y0, (0, 0, 1)),   # top
        ((x0, y0, z0), (1, 0, 0), (0, 0, 1), x1 - x0, z1 - z0, (0, -1, 0)),  # -y
        ((x0, y1, z0), (1, 0, 0), (0, 0, 1), x1 - x0, z1 - z0, (0, 1, 0)),   # +y
        ((x0, y0, z0), (0, 1, 0), (0, 0, 1), y1 - y0, z1 - z0, (-1, 0, 0)),  # -x
        ((x1, y0, z0), (0, 1, 0), (0, 0, 1), y1 - y0, z1 - z0, (1, 0, 0)),   # +x
    ]
    return [(rect_polygon(origin, e1, e2, 0.0, 0.0, s1, s2, outward), material)
            for origin, e1, e2, s1, s2, outward in faces]


def _finite_coord(v) -> bool:
    return (len(v) == 3
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v)
            and all(math.isfinite(c) for c in v))


def _mesh_polygons(mesh: dict, material: str) -> list:
    verts_raw = mesh.get("vertices_mm", [])
    tris = mesh.get("triangles", [])
    if not verts_raw or not tris:
        raise RadianceError("a mesh entry needs non-empty vertices_mm and triangles")
    for v in verts_raw:
        if not _finite_coord(v):
            raise RadianceError(f"mesh vertex {v!r} is not a finite (x, y, z) triple")
    verts = [(mm(v[0]), mm(v[1]), mm(v[2])) for v in verts_raw]
    out = []
    for tri in tris:
        if (len(tri) != 3
                or any(type(i) is not int or i < 0 or i >= len(verts) for i in tri)):
            raise RadianceError(
                f"mesh triangle {tri!r} references an out-of-range or non-integer vertex")
        pts = [verts[i] for i in tri]
        normal = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[0]))
        if _dot(normal, normal) < 1e-18:
            raise RadianceError(f"mesh triangle {tri!r} is degenerate (zero area)")
        out.append((pts, material))
    return out


def _mesh_bbox(meshes: list) -> "Box | None":
    """A conservative world-mm bounding box spanning every vertex of every
    mesh, for occupied-cell exclusion when an item's meshes are the only
    geometry supplied (no `at`/`size_mm`)."""
    xs, ys, zs = [], [], []
    for m in meshes:
        for v in m.get("vertices_mm", []):
            xs.append(v[0]); ys.append(v[1]); zs.append(v[2])
    if not xs:
        return None
    return Box(min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _item_box(item: dict) -> "Box | None":
    at = item.get("bbox_center_mm") or item.get("at")
    size = item.get("size_mm") or item.get("size")
    if not at or not size:
        return None
    base = item.get("base_height_mm") or 0.0
    w = size[0]
    d = size[1] if len(size) > 1 else size[0]
    h = size[2] if len(size) > 2 else (item.get("height") or 750.0)
    if w <= 0 or d <= 0 or h <= 0:
        raise RadianceError(f"furniture {item.get('id')} has a non-positive dimension")
    return Box(at[0] - w / 2.0, at[1] - d / 2.0, base,
              at[0] + w / 2.0, at[1] + d / 2.0, base + h)


def furniture_geometry(data: dict) -> tuple:
    """Furniture as opaque obstacles, PER ITEM: `item['meshes']` if the
    extract carries them for that item, else its measured proxy box.

    Returns (polygons, boxes, proxy_count, missing_ids). `boxes` (world mm)
    is a CONSERVATIVE bounding-box occupancy filter for the grid-exclusion
    check regardless of geometry source -- even where real meshes are
    rendered, the box used to blank grid cells may exclude more than the
    mesh's actual footprint (e.g. a headboard's full bounding box versus
    its thinner cross-section); this is a stated approximation, not a
    furnished-room uniformity claim. `missing_ids` lists items that had
    neither meshes nor enough fields (`at`/`size_mm`) for a proxy box --
    they are silently absent from the rendered scene, and the caller must
    disclose that rather than claim complete coverage.
    """
    polys, boxes, proxy_count, missing = [], [], 0, []
    for item in data.get("furniture", []) + data.get("casework", []):
        meshes = item.get("meshes")
        box = _item_box(item)
        if box is None and meshes:
            box = _mesh_bbox(meshes)
        if box is not None:
            boxes.append(box)
        if meshes:
            for m in meshes:
                polys.extend(_mesh_polygons(m, "furniture"))
        elif box is not None:
            polys.extend(_box_polygons(box, "furniture"))
            proxy_count += 1
        else:
            missing.append(item.get("id"))
    if missing:
        raise RadianceError('Furniture has no measurable geometry: '+str(missing))
    return polys, boxes, proxy_count, missing


# ------------------------------------------------------------------ lights

def _validate_ies_name(name: str, ies_dir: Path) -> Path:
    if not name or Path(name).name != name:
        raise RadianceError(f"light asset name {name!r} is not a bare basename")
    path = (Path(ies_dir) / name).resolve()
    if not path.is_relative_to(Path(ies_dir).resolve()) or not path.is_file():
        raise RadianceError(f"light asset {name!r} is not a file inside {ies_dir}")
    return path


def ies2rad_argv(tools: Tools, ies_path: Path, output_factor: float,
                 out_prefix: Path) -> list:
    """`ies2rad -dm -t default` with an explicit output multiplier, exactly
    as specified: metres output (`-dm`), a stated neutral lamp type rather
    than trusting an unrecognised declared one, and no `-i` override -- the
    IES file's own crude luminous geometry is kept, which is what
    "finite luminous geometry" means here.

    `-o out_prefix` is an OUTPUT path prefix (`ies2rad` writes
    `<out_prefix>.rad`, referencing `<out_prefix>.dat` for its
    interpolated candela table) -- NOT a library search path. `out_prefix`
    must be an ABSOLUTE path inside the current job's own fixture/physics
    directory, so the `.rad`'s reference to its `.dat` still resolves once
    `oconv`/`rtrace` run from a different working directory. `-l` (which
    IS `ies2rad`'s own INSTALL-library-relative output convenience, not a
    runtime search path either) is deliberately not used here; runtime
    library search is `RAYPATH`, set per-process in `_child_env`."""
    return [tools["ies2rad"], "-dm", "-t", "default",
            "-m", f"{output_factor:.6f}", "-o", str(out_prefix), ies_path]


def xform_argv(tools: Tools, rad_path: Path, rotation_deg: float, xyz_m: tuple) -> list:
    """Rotate about the fixture's own local Z, THEN translate to its world
    position -- xform applies transformations in the order listed, so this
    order matters. No extra azimuth offset: Radiance's horizontal zero is
    already along the model's first axis, unlike Blender (see
    `blender/build_scene.py.IES_AZIMUTH_OFFSET_DEG`), so none is added
    here."""
    x, y, z = xyz_m
    return [tools["xform"], "-rz", f"{rotation_deg:.6f}",
            "-t", f"{x:.6f}", f"{y:.6f}", f"{z:.6f}", rad_path]


def convert_fixture(tools: Tools, ies_dir: Path, fixture: dict, elevation_mm: float,
                    workdir: Path, tag: str, *, run=_run) -> Path:
    """One fixture -> a placed `.rad` file: ies2rad, then xform. Both
    commands and their logs are recorded so a placement bug is diagnosable
    without rerunning."""
    name = fixture.get("ies_file")
    ies_path = _validate_ies_name(name, ies_dir)
    at = fixture.get("at")
    height = fixture.get("mounting_height")
    if not at or height is None:
        raise RadianceError(f"fixture {fixture.get('id')} needs at and mounting_height")
    output = float(fixture.get("output") if fixture.get("output") is not None else 1.0)
    if not 0.0 <= output <= 1.0:
        raise RadianceError(f"fixture {fixture.get('id')} output {output} outside 0..1")

    folder = (workdir / "fixtures" / tag).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    out_prefix = folder / tag
    raw = folder / f"{tag}.rad"
    run(ies2rad_argv(tools, ies_path, output, out_prefix), cwd=folder, timeout=_timeout_for(1),
        stdout_path=folder / "ies2rad.log")
    _require_file(raw)

    xyz_m = (mm(at[0]), mm(at[1]), mm(elevation_mm + height))
    placed = folder / f"{tag}_placed.rad"
    argv = xform_argv(tools, raw, float(fixture.get("rotation") or 0.0), xyz_m)
    run(argv, cwd=folder, timeout=_timeout_for(1), stdout_path=placed)
    _require_file(placed)
    return placed


# --------------------------------------------------------------------- grid

def grid_points(x0, y0, x1, y1, *, inset: float, spacing: float,
                plane_mm: float, boxes: list) -> tuple:
    """Cell-centred sample points inside the room, inset from the walls,
    with any cell whose (x, y) falls inside a box that crosses the working
    plane excluded -- "measured furniture as obstacles" for the grid too,
    not only for the raytracer.

    The cell count per axis is `ceil(interval / spacing)`, but the actual
    per-axis spacing used is `interval / count`, fitted so the last cell's
    centre is always strictly inside the inset interval -- `ceil` plus the
    REQUESTED spacing can place it outside, which the caller must not do.
    The fitted spacing is therefore <= the requested `spacing` and is
    reported back rather than silently substituted.

    Returns (points, excluded_count, total_before_exclusion, spacing_x_mm,
    spacing_y_mm).
    """
    if spacing <= 0:
        raise RadianceError("grid spacing must be positive")
    ix0, iy0, ix1, iy1 = x0 + inset, y0 + inset, x1 - inset, y1 - inset
    if ix1 <= ix0 or iy1 <= iy0:
        raise RadianceError(f"a {inset:.0f} mm inset leaves nothing to sample "
                            f"in a {x1 - x0:.0f} x {y1 - y0:.0f} mm room")
    nx = max(1, math.ceil((ix1 - ix0) / spacing - 1e-9))
    ny = max(1, math.ceil((iy1 - iy0) / spacing - 1e-9))
    dx = (ix1 - ix0) / nx
    dy = (iy1 - iy0) / ny
    crossing = [b for b in boxes if b.crosses(plane_mm)]
    points, excluded, total = [], 0, 0
    for j in range(ny):
        y = iy0 + (j + 0.5) * dy
        for i in range(nx):
            x = ix0 + (i + 0.5) * dx
            total += 1
            if any(b.contains_xy(x, y) for b in crossing):
                excluded += 1
                continue
            points.append((x, y))
    if not points:
        raise RadianceError("every grid cell was excluded by furniture; nothing to sample")
    return points, excluded, total, dx, dy


def rtrace_argv(tools: Tools, octree: Path, ambient_bounces: int, workers: int, *,
                ad: int = 512, ar: int = 16, aa: float = 0.15, as_: int = 128) -> list:
    """`-I+` (irradiance at the receiver's own position/normal), `-h-`
    (no header, so output is a plain stream of numbers), ASCII in and out
    via `-faa` (joined, per `rtrace`'s own syntax -- NOT `-f aa`, which
    `rtrace` does not accept as two tokens). Ambient bounces set to exactly
    what the caller asked for: `-ab 0` therefore measures direct light
    only; anything higher includes reflected light, which is what makes it
    comparable in kind (never in number -- ADR-0009) to the analytical
    engine's direct-only result. `ad`/`ar`/`aa`/`as_` are the ambient
    divisions/resolution/accuracy/samples the caller wants (defaults sized
    for a small room); the sky-normalisation check overrides them to
    resolve a much coarser, unobstructed hemisphere accurately."""
    return [tools["rtrace"], "-I+", "-h-", "-dt", "0", "-ab", str(ambient_bounces),
            "-ad", str(ad), "-ar", str(ar), "-aa", str(aa), "-as", str(as_),
            "-n", str(clamp_workers(workers)), "-faa", octree]


def _lux(r: float, g: float, b: float) -> float:
    """W/m2 RGB irradiance -> lux, via Radiance's own documented
    conversion (color.h: WHTEFFICACY=179, CIE_rf/gf/bf as above)."""
    return WHTEFFICACY * (CIE_RF * r + CIE_GF * g + CIE_BF * b)


def parse_rtrace_output(text: str, expected: int) -> list:
    try:
        values = [float(v) for v in text.split()]
    except ValueError as exc:
        raise RadianceError(f"rtrace output is not purely numeric: {exc}") from exc
    if len(values) != 3 * expected:
        raise RadianceError(
            f"rtrace returned {len(values)} numbers for {expected} points "
            f"(expected {3 * expected}); output is malformed or truncated")
    for v in values:
        if not math.isfinite(v) or v < 0.0:
            raise RadianceError(f"rtrace output contains a non-finite or negative "
                                f"irradiance value: {v!r}")
    return [(values[3 * i], values[3 * i + 1], values[3 * i + 2]) for i in range(expected)]


def oconv_argv(tools: Tools, rad_files: list) -> list:
    return [tools["oconv"]] + list(rad_files)


# --------------------------------------------------------------- sky (daylight)

def gensky_argv(tools: Tools, altitude_deg: float, azimuth_deg: float,
                ground_reflectance: float,
                target_lux: float = SKY_TARGET_EXTERIOR_LUX) -> list:
    """A normalised CIE overcast sky at a STATED, fixed sun angle --
    `-ang` rather than a calendar date, so nothing here reads as a real
    place or time. `-c` selects the standard CIE overcast distribution;
    the fixed `-ang` sun position only affects that distribution's
    (illustrative) azimuthal symmetry, not its normalisation.

    `-B` sets the sky's horizontal diffuse IRRADIANCE in W/m2 (gensky's
    own documented unit, NOT lux) -- `target_lux / WHTEFFICACY` converts
    the stated `target_lux` illuminance target into that irradiance figure
    via Radiance's own W/m2-to-lux constant, so the sky's overall
    brightness is pinned to a known value independent of the illustrative
    sun angle. `sky_check` verifies this actually lands on `target_lux`
    with an unobstructed sky-only octree.
    """
    b_wm2 = target_lux / WHTEFFICACY
    return [tools["gensky"], "-ang", f"{altitude_deg:.4f}", f"{azimuth_deg:.4f}",
            "-c", "-B", f"{b_wm2:.6f}", "-g", f"{ground_reflectance:.4f}"]


def sky_glow_text() -> str:
    """`gensky`'s own stdout defines the `skyfunc` brightness FUNCTION but
    not a visible glow/source primitive over the hemisphere -- exactly the
    two-part convention documented on `gensky`'s own man page and its
    example scripts. Appended after `gensky`'s stdout: a unit-white upper
    hemisphere glow (`sky_glow`, direction 0 0 1, the full `angle180` dome)
    samples the sky function; a separate `ground_glow` (direction 0 0 -1)
    is the stated ground-reflectance source, kept as its own distinct
    primitive so the two are never confused."""
    return (
        "\nskyfunc glow sky_glow\n0\n0\n4 1 1 1 0\n"
        "sky_glow source sky\n0\n0\n4 0 0 1 180\n"
        "skyfunc glow ground_glow\n0\n0\n4 1 1 1 0\n"
        "ground_glow source ground\n0\n0\n4 0 0 -1 180\n")


def sky_check(tools: Tools, sky_path: Path, workdir: Path, timeout: int, *,
             run=_run) -> dict:
    """Verify the normalised sky ACTUALLY produces `SKY_TARGET_EXTERIOR_LUX`
    on an unobstructed horizontal receiver, using a sky-ONLY octree (no
    room geometry) -- so this measures the sky definition itself, not
    anything about the room it will illuminate. Ambient integration is
    required to resolve the sky glow at all (`-ab 1`); `-ad 4096`/`-aa 0`
    are set high/exact enough to resolve a smooth, unobstructed hemisphere
    accurately rather than the small-room defaults `rtrace_argv` otherwise
    uses. Raises -- exactly like `physics_check` -- rather than ever
    returning `passed: False`; a discrepancy here means every downstream
    daylight lux figure is off by the same factor and must stop the run.
    """
    octree = workdir / "sky_only.oct"
    run(oconv_argv(tools, [sky_path]), cwd=workdir, timeout=timeout, stdout_path=octree)
    _require_file(octree)

    point = "0 0 0 0 0 1\n"
    points_path = _write(workdir / "sky_check_points.txt", point)
    out_path = workdir / "sky_check.out"
    run(rtrace_argv(tools, octree, 1, 1, ad=4096, aa=0.0), cwd=workdir, timeout=timeout,
        stdout_path=out_path, stdin_path=points_path)

    measured = _lux(*parse_rtrace_output(_capture(out_path), 1)[0])
    expected = SKY_TARGET_EXTERIOR_LUX
    relative_error = abs(measured - expected) / expected if expected else float("inf")
    result = {
        "expected_lux": expected, "measured_lux": measured,
        "relative_error": relative_error, "tolerance": SKY_CHECK_TOLERANCE,
        "passed": (relative_error <= SKY_CHECK_TOLERANCE
                  and math.isfinite(measured) and measured > 0.0),
        "method": ("gensky -B normalised to a stated exterior horizontal illuminance, "
                  "measured on a sky-only octree (no room geometry) with an "
                  "upward-facing receiver -- independent of the room scene it is "
                  "later composited into"),
    }
    if not result["passed"]:
        raise RadianceError(
            f"sky normalisation check failed: expected {expected:.0f} lx, measured "
            f"{measured!r} lx ({relative_error:.1%} off, tolerance "
            f"{SKY_CHECK_TOLERANCE:.0%})")
    return result


# ---------------------------------------------------------------- report I/O

def _write_grid_json(path: Path, points: list, lux: list, meta: dict) -> Path:
    rows = [[round(x, 1), round(y, 1), round(v, 3)] for (x, y), v in zip(points, lux)]
    payload = {**meta, "units": "mm, lux", "points": rows}
    return _write(path, json.dumps(payload, indent=2))


# ------------------------------------------------------------------- physics

def physics_check(tools: Tools, workdir: Path, timeout: int, *, run=_run) -> dict:
    """An isotropic 1000 cd source and a receiver 2.0 m directly below it:
    E = I/d^2 = 250 lx. Independent of every other code path in this
    module -- its own geometry, its own octree, its own rtrace call --
    because "output existence is insufficient" as a proof that the pipeline
    computes anything correct.

    The synthetic fixture declares candela at vertical angles 0/90/180 (a
    full sphere, all equal) so it is genuinely isotropic rather than only
    hemispherically uniform, and uses ABSOLUTE photometry (lumens/lamp =
    -1, matching `photometry.py`'s documented convention) plus `ies2rad -t
    default`'s documented NEUTRAL-white lamp type, removing lamp-table
    colour/efficacy ambiguity from the candela values themselves. The
    comparison tolerance (`PHYSICS_TOLERANCE`) is tight because both of
    those ambiguities are already removed by construction.
    """
    ies_text = "\n".join([
        "IESNA:LM-63-2002", "[TEST] archpipe synthetic isotropic", "TILT=NONE",
        "1 -1 1 3 1 1 2 0 0 0", "1 1 10", "0 90 180", "0",
        f"{PHYSICS_CANDELA} {PHYSICS_CANDELA} {PHYSICS_CANDELA}",
    ])
    folder = (workdir / "physics_check").resolve()
    folder.mkdir(parents=True, exist_ok=True)
    ies_path = _write(folder / "iso.ies", ies_text)

    out_prefix = folder / "iso"
    run(ies2rad_argv(tools, ies_path, 1.0, out_prefix), cwd=folder, timeout=timeout,
        stdout_path=folder / "ies2rad.log")
    raw = _require_file(folder / "iso.rad")

    octree = folder / "iso.oct"
    run(oconv_argv(tools, [raw]), cwd=folder, timeout=timeout, stdout_path=octree)
    _require_file(octree)

    point = f"0 0 {-PHYSICS_DISTANCE_M} 0 0 1\n"
    points_path = _write(folder / "points.txt", point)
    out_path = folder / "rtrace.out"
    run(rtrace_argv(tools, octree, 0, 1), cwd=folder, timeout=timeout, stdout_path=out_path,
        stdin_path=points_path)

    r, g, b = parse_rtrace_output(_capture(out_path), 1)[0]
    measured = _lux(r, g, b)
    expected = PHYSICS_CANDELA / (PHYSICS_DISTANCE_M ** 2)
    relative_error = abs(measured - expected) / expected if expected else float("inf")
    result = {"expected_lux": expected, "measured_lux": measured,
             "distance_m": PHYSICS_DISTANCE_M, "candela": PHYSICS_CANDELA,
             "relative_error": relative_error, "tolerance": PHYSICS_TOLERANCE,
             "passed": relative_error <= PHYSICS_TOLERANCE}
    if not result["passed"]:
        raise RadianceError(
            f"physics check failed: expected {expected:.2f} lx, measured "
            f"{measured:.2f} lx ({relative_error:.1%} off, tolerance "
            f"{PHYSICS_TOLERANCE:.0%})")
    return result


# -------------------------------------------------------------- orchestration

def _base_shell(data: dict, x0, y0, x1, y1, elevation_mm, ceiling_h_mm, *, fill_doors: bool):
    """Walls (with holes), floor and ceiling for the one supported room.
    Returns (polygons, [(wall, WallOpening), ...] for every window)."""
    polys = [(floor_polygon(x0, y0, x1, y1, elevation_mm), "floor"),
             (ceiling_polygon(x0, y0, x1, y1, elevation_mm, ceiling_h_mm), "ceiling")]
    windows = []
    for w in data.get("walls", []):
        wall_polys, wall_windows = wall_polygons(w, data.get("openings", []), elevation_mm,
                                                 fill_doors=False)
        polys.extend(wall_polys)
        windows.extend((w, o) for o in wall_windows)
    if fill_doors:
        walls={w['id']:w for w in data['walls']}
        for opening in data.get('openings',[]):
            if opening.get('kind')!='door':
                continue
            if opening.get('meshes'):
                for mesh in opening['meshes']:
                    polys.extend(_mesh_polygons(mesh,'wall'))
            else:
                wall=walls[opening['host']]
                dx,dy=wall['end'][0]-wall['start'][0],wall['end'][1]-wall['start'][1]
                length=math.hypot(dx,dy)
                u0,u1=opening['at']-opening['width']/2,opening['at']+opening['width']/2
                bottom=opening.get('sill') or 0
                origin=(mm(wall['start'][0]),mm(wall['start'][1]),mm(elevation_mm))
                polys.append((rect_polygon(origin,(dx/length,dy/length,0),(0,0,1),
                    mm(u0),mm(bottom),mm(u1),mm(bottom+opening['height']),
                    (-dy/length,dx/length,0)),'wall'))
    return polys, windows


def _materials_block() -> str:
    return "".join(_plastic(name, r) for name, r in REFLECTANCE.items())


def _rad_text(polys: list) -> str:
    return "".join(_polygon_prim(material, f"p{i}", pts)
                  for i, (pts, material) in enumerate(polys))


def electric_light_grid(data: dict, tools: Tools, ies_dir: Path, workdir: Path,
                        x0, y0, x1, y1, elevation_mm, ceiling_h_mm, workers: int,
                        *, run=_run) -> dict:
    """Two rtrace passes over the same octree: `-ab 0` (direct) and
    `-ab 4` (direct + up to 4 reflections). The maintenance factor is
    applied to each AFTER measurement, once -- never baked into the
    fixture output, matching `lighting.py`'s convention."""
    folder = (workdir / "electric").resolve()
    folder.mkdir(parents=True, exist_ok=True)

    shell_polys, _windows = _base_shell(data, x0, y0, x1, y1, elevation_mm, ceiling_h_mm,
                                       fill_doors=True)
    furn_polys, boxes, proxy_count, missing = furniture_geometry(data)
    window_polys=[]
    by_wall={wall['id']:wall for wall in data['walls']}
    for opening in data.get('openings',[]):
        if opening.get('kind')=='window':
            for mesh in opening.get('meshes',[]):
                window_polys.extend(_glazing_surface(mesh,by_wall[opening['host']])
                    if _classify_opening_mesh(mesh)=='glazing' else _mesh_polygons(mesh,'wall'))
    scene_path = _write(folder / "shell.rad",
                        _materials_block() + _glass('glazing',tn_to_transmissivity(GLAZING_TRANSMITTANCE))
                        + _rad_text(shell_polys + furn_polys + window_polys))

    fixture_paths = []
    for i, fx in enumerate(data.get("lighting", [])):
        placed = convert_fixture(tools, ies_dir, fx, elevation_mm, folder,
                                f"fx{i:02d}", run=run)
        fixture_paths.append(placed)
    if not fixture_paths:
        raise RadianceError("the extract carries no light fixtures to simulate")

    octree = folder / "scene.oct"
    run(oconv_argv(tools, [scene_path] + fixture_paths), cwd=folder,
        timeout=_timeout_for(len(fixture_paths)), stdout_path=octree)
    _require_file(octree)

    points, excluded, total, dx, dy = grid_points(x0, y0, x1, y1, inset=ROOM_INSET_MM,
                                                  spacing=SPACING_MM,
                                                  plane_mm=WORKING_PLANE_MM, boxes=boxes)
    plane_m = mm(WORKING_PLANE_MM)
    lines = "".join(f"{mm(x):.6f} {mm(y):.6f} {plane_m:.6f} 0 0 1\n" for x, y in points)
    points_path = _write(folder / "points.txt", lines)

    grids = {}
    for ab in AMBIENT_BOUNCES:
        out_path = folder / f"grid_ab{ab}.out"
        run(rtrace_argv(tools, octree, ab, workers), cwd=folder,
            timeout=_timeout_for(len(points)), stdout_path=out_path,
            stdin_path=points_path)
        rgb = parse_rtrace_output(_capture(out_path), len(points))
        lux = [_lux(*c) * MAINTENANCE_FACTOR for c in rgb]
        meta = {
            "ambient_bounces": ab,
            "working_plane_mm": WORKING_PLANE_MM,
            "spacing_mm_requested": SPACING_MM,
            "spacing_mm_x": round(dx, 3), "spacing_mm_y": round(dy, 3),
            "room_inset_mm": ROOM_INSET_MM, "maintenance_factor": MAINTENANCE_FACTOR,
            "workers": clamp_workers(workers), "fixtures": len(fixture_paths),
            "furniture_proxy_count": proxy_count, "furniture_missing_geometry": missing,
            "excluded_points": excluded, "total_cells": total,
            "coverage": (total - excluded) / total if total else 0.0,
            "note": ("Direct component only." if ab == 0 else
                     f"Direct plus up to {ab} diffuse reflections."
                     " Still not a total-illuminance/U0 verdict; see ADR-0009.")
            + " Maintenance factor applied once, after measurement.",
        }
        grid_path = _write_grid_json(folder / f"electric-ab{ab}-grid.json", points, lux, meta)
        grids[f"ab{ab}"] = {**meta, "artifact": str(grid_path),
                           "average_lux": sum(lux) / len(lux),
                           "minimum_lux": min(lux), "maximum_lux": max(lux)}
    return grids


def _classify_opening_mesh(mesh: dict) -> str:
    """`"glazing"` if the mesh's own material says it is transparent or is
    named like glass, else `"opaque"` (a frame, sash or similar) -- window
    frames are opaque even though they belong to a `kind: "window"`
    opening; only the pane itself is glazing."""
    material = mesh.get("material") or {}
    transparency = material.get("transparency") or 0
    name = str(material.get("name") or "").lower()
    is_glass = transparency > 0 or "glass" in name or "glaz" in name
    return "glazing" if is_glass else "opaque"


def _glazing_surface(mesh: dict, wall: dict) -> list:
    """One pane surface represents the assumed whole-window transmittance.

    A Revit glass solid has front/back triangles. Assigning Radiance glass
    to both would apply the declared window transmittance twice. Retain
    the outermost plane parallel to the host wall from the actual mesh.
    This rectangular-room adapter assumes planar vertical glazing.
    """
    polygons=_mesh_polygons(mesh,'glazing')
    dx,dy=wall['end'][0]-wall['start'][0],wall['end'][1]-wall['start'][1]
    length=math.hypot(dx,dy)
    normal=(-dy/length,dx/length,0)
    candidates=[]
    for points,material in polygons:
        face_normal=polygon_normal(points)
        magnitude=math.sqrt(_dot(face_normal,face_normal))
        if magnitude and abs(_dot(face_normal,normal))/magnitude>.999:
            depth=sum(_dot(p,normal) for p in points)/len(points)
            candidates.append((depth,(points,material)))
    if not candidates:
        raise RadianceError('Glazing needs a planar surface parallel to its host wall')
    outer=max(depth for depth,_ in candidates)
    return [polygon for depth,polygon in candidates if abs(depth-outer)<1e-6]


def daylight_example(data: dict, tools: Tools, workdir: Path, x0, y0, x1, y1,
                     elevation_mm, ceiling_h_mm, workers: int, *, run=_run) -> dict:
    """A single normalised-overcast-sky snapshot: explicitly illustrative
    (see module docstring), with the sky's own normalisation verified by
    `sky_check` on a sky-only octree before it is ever composited with
    room geometry."""
    folder = (workdir / "daylight").resolve()
    folder.mkdir(parents=True, exist_ok=True)

    shell_polys, windows = _base_shell(data, x0, y0, x1, y1, elevation_mm, ceiling_h_mm,
                                      fill_doors=True)
    furn_polys, boxes, proxy_count, missing = furniture_geometry(data)

    transmissivity = tn_to_transmissivity(GLAZING_TRANSMITTANCE)
    openings_by_id = {o.get("id"): o for o in data.get("openings", [])}
    glass_polys, frame_polys = [], []
    used_mesh_glazing = False
    for wall, o in windows:
        raw = openings_by_id.get(o.id, {})
        meshes = raw.get("meshes") or []
        glazing_meshes = [m for m in meshes if _classify_opening_mesh(m) == "glazing"]
        frame_meshes = [m for m in meshes if _classify_opening_mesh(m) == "opaque"]
        if glazing_meshes:
            used_mesh_glazing = True
            for m in glazing_meshes:
                glass_polys.extend(_glazing_surface(m,wall))
            for m in frame_meshes:
                frame_polys.extend(_mesh_polygons(m, "wall"))
            continue
        x1w, y1w = mm(wall["start"][0]), mm(wall["start"][1])
        x2w, y2w = mm(wall["end"][0]), mm(wall["end"][1])
        length = math.hypot(x2w - x1w, y2w - y1w)
        ux, uy = (x2w - x1w) / length, (y2w - y1w) / length
        origin = (x1w, y1w, mm(elevation_mm))
        glass_polys.append((rect_polygon(origin, (ux, uy, 0.0), (0.0, 0.0, 1.0),
                                        mm(o.u0), mm(o.v0), mm(o.u1), mm(o.v1),
                                        (0.0, 0.0, 1.0)), "glazing"))
    if windows and not glass_polys:
        raise RadianceError("windows present but no glazing geometry was built")

    materials = _materials_block() + _glass("glazing", transmissivity)
    scene_path = _write(folder / "shell.rad",
                        materials + _rad_text(shell_polys + furn_polys + glass_polys
                                              + frame_polys))

    sky_out = folder / "sky.rad"
    run(gensky_argv(tools, SKY_ALTITUDE_DEG, SKY_AZIMUTH_DEG, GROUND_REFLECTANCE),
        cwd=folder, timeout=_timeout_for(1), stdout_path=sky_out)
    sky_text = _capture(sky_out) + sky_glow_text()
    sky_path = _write(sky_out, sky_text)

    exterior_check = sky_check(tools, sky_path, folder, _timeout_for(1), run=run)

    octree = folder / "scene.oct"
    run(oconv_argv(tools, [scene_path, sky_path]), cwd=folder, timeout=_timeout_for(1),
        stdout_path=octree)
    _require_file(octree)

    points, excluded, total, dx, dy = grid_points(x0, y0, x1, y1, inset=ROOM_INSET_MM,
                                                  spacing=SPACING_MM,
                                                  plane_mm=WORKING_PLANE_MM, boxes=boxes)
    plane_m = mm(WORKING_PLANE_MM)
    lines = "".join(f"{mm(x):.6f} {mm(y):.6f} {plane_m:.6f} 0 0 1\n" for x, y in points)
    points_path = _write(folder / "points.txt", lines)
    out_path = folder / "grid.out"
    run(rtrace_argv(tools, octree, 4, workers), cwd=folder, timeout=_timeout_for(len(points)),
        stdout_path=out_path, stdin_path=points_path)
    lux = [_lux(*c) for c in parse_rtrace_output(_capture(out_path), len(points))]

    meta = {
        "illustrative": True, "site": "none -- normalised CIE overcast sky, not a real place",
        "sky_altitude_deg": SKY_ALTITUDE_DEG, "sky_azimuth_deg": SKY_AZIMUTH_DEG,
        "sky_target_exterior_lux": SKY_TARGET_EXTERIOR_LUX,
        "ground_reflectance": GROUND_REFLECTANCE,
        "glazing_transmittance_assumed": GLAZING_TRANSMITTANCE,
        "glazing_source": "single outer surface from extracted glazing mesh; whole-window transmittance applied once" if used_mesh_glazing else
                          "fallback rectangle from opening at/sill/width/height",
        "doors": "opaque extracted geometry where available; opaque planar fallback otherwise",
        "ambient_bounces": 4, "working_plane_mm": WORKING_PLANE_MM,
        "spacing_mm_requested": SPACING_MM,
        "spacing_mm_x": round(dx, 3), "spacing_mm_y": round(dy, 3),
        "room_inset_mm": ROOM_INSET_MM,
        "furniture_proxy_count": proxy_count, "furniture_missing_geometry": missing,
        "excluded_points": excluded, "total_cells": total,
        "coverage": (total - excluded) / total if total else 0.0,
        "exterior_check": exterior_check,
        "note": "No code-compliance or uniformity claim. Illustrative sky only. "
               "No direct solar source is modelled -- overcast sky only.",
    }
    grid_path = _write_grid_json(folder / "daylight-grid.json", points, lux, meta)
    return {**meta, "artifact": str(grid_path),
            "average_lux": sum(lux) / len(lux), "minimum_lux": min(lux),
            "maximum_lux": max(lux)}


def simulate(data: dict, folder: Path, install: Path, ies_dir: Path, workers: int = 8,
            *, run=_run) -> dict:
    """Full Radiance study for one joined Revit-geometry-plus-photometry
    extract: an independent physics check, a sky-normalisation check,
    electric-light grids at 0 and 4 ambient bounces, and an illustrative
    daylight-only example.

    WHAT THE LEAD MUST STILL VERIFY on the first real run:

    * The `-ab 4`/`-ad`/`-ar`/`-aa`/`-as` ambient parameters in
      `rtrace_argv` were chosen for a small room without being run; if the
      0- and 4-bounce grids disagree with intuition (4-bounce lower than
      0-bounce anywhere, say), raise `-ad`/`-as` first.
    * `xform`'s output is captured directly to the placed `.rad` file's
      path (`_run`'s `stdout_path`, no shell redirection) -- confirm that
      file is valid Radiance scene text.
    * `genbox` and `rpict`/`pvalue`/`pfilt`/`getinfo`/`gendaylit` are
      verified present (the install is checked for the full tool list the
      task specified) but not invoked: furniture/opening boxes are
      written as hand-built polygons instead of `genbox`, for exact
      control over hole-punching and outward-normal orientation that
      `genbox` does not offer; no image is rendered, so the picture-format
      tools are unused.
    * Real Revit tessellation can emit slivers close to, but not exactly
      at, degenerate; `_mesh_polygons`'s zero-area rejection uses an
      absolute cross-product-magnitude threshold that has not been tuned
      against real mesh data.
    """
    workers = clamp_workers(workers)
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    tools = Tools.resolve(Path(install))

    if data.get("units") != "mm":
        raise RadianceError(f"expected mm units, got {data.get('units')!r}")
    rooms = data.get("rooms") or []
    if len(rooms) != 1:
        raise RadianceError(f"expected exactly one room, found {len(rooms)}")
    room = rooms[0]
    x0, y0, x1, y1 = room_rectangle(room)
    elevation_mm = single_level_elevation_mm(data, room)
    ceiling_h_mm = room_wall_height_mm(data, room)

    started = time.perf_counter()
    physics = physics_check(tools, folder, _timeout_for(1), run=run)
    electric = electric_light_grid(data, tools, ies_dir, folder, x0, y0, x1, y1,
                                   elevation_mm, ceiling_h_mm, workers, run=run)
    daylight = daylight_example(data, tools, folder, x0, y0, x1, y1, elevation_mm,
                                ceiling_h_mm, workers, run=run)
    seconds = time.perf_counter() - started

    report = {
        "schema": 1, "source": data.get("source"), "room": room.get("name"),
        "room_bounds_mm": [x0, y0, x1, y1], "elevation_mm": elevation_mm,
        "ceiling_height_mm": ceiling_h_mm, "workers": workers, "seconds": seconds,
        "reflectance_assumptions": REFLECTANCE,
        "geometry_assumptions": [
            'Grid exclusions conservatively use measured furniture bounding boxes, not cross-sections.',
            'Photometric source geometry represents fixture optics; native display webs and housing do not add optical obstructions.',
            'Planar glazing uses one surface with assumed whole-window transmittance; frames retain extracted geometry.'
        ],
        "physics_check": physics, "electric": electric, "daylight": daylight,
        "no_compliance_claim": "No code-compliance or uniformity (EN 12464-1 U0) "
                               "verdict is made anywhere in this report.",
    }
    report_path = _write(folder / "radiance-report.json", json.dumps(report, indent=2))

    passed = bool(physics["passed"]) and bool(daylight["exterior_check"]["passed"])
    return {
        "passed": passed, "report": str(report_path), "seconds": seconds,
        "physics_check_passed": physics["passed"],
        "electric_ab0_average_lux": electric["ab0"]["average_lux"],
        "electric_ab4_average_lux": electric["ab4"]["average_lux"],
        "electric_ab0_grid": electric["ab0"]["artifact"],
        "electric_ab4_grid": electric["ab4"]["artifact"],
        "daylight_average_lux": daylight["average_lux"],
        "daylight_exterior_check_relative_error":
            daylight["exterior_check"]["relative_error"],
        "daylight_grid": daylight["artifact"],
        "no_compliance_claim": report["no_compliance_claim"],
    }
