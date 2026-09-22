"""Illuminance: what the room will actually be like to be in.

Point-by-point lux over a working plane, from real IES photometry
(`photometry.py`), plus the metrics a scheme is judged on and a false-colour
map. Pure arithmetic -- it runs on the laptop in under a second and needs no
GPU and no renderer. ADR-0004 records why compliance is calculated rather
than rendered: a Cycles image is a picture of light, not a measurement of
it, and no client should be shown a pretty render as evidence of adequacy.

The unit convention follows the rest of the package: **millimetres** for all
geometry, degrees for angles, lux for illuminance. `photometry.py` works in
metres because the inverse-square law does; the conversion happens here, in
one place.

WHAT THIS MODULE IS CAREFUL ABOUT

*Maintained, not initial.* Lamps depreciate and luminaires collect dust.
Quoting the day-one figure overstates what the client lives with for the
next decade, so every result here is multiplied by a maintenance factor and
`LuxGrid` records which one. This is the standard convention: EN 12464-1
and the CIBSE/SLL Code for Lighting both specify *maintained* illuminance
as the design quantity.

*Direct light only.* This is a direct-illuminance calculation. It does not
model inter-reflection between surfaces, so in a light-coloured room it
**understates** the real result, typically by 10-25%. That is the safe
direction to be wrong in for a compliance check, and it is stated on every
result rather than buried here. A full radiosity/ray-traced answer is
Radiance's job, noted in the plan as a later addition.

*Point sources.* The inverse-square law treats a luminaire as a point,
which holds when the distance is at least five times the luminaire's
largest luminous dimension. Close under a long linear fitting it
overestimates. `LuxGrid.point_source_warnings()` reports where that
assumption is being strained instead of quietly returning a confident
number.

*No uniformity verdict.* EN 12464-1's U0 = Emin/Eavg is defined on **total
maintained** illuminance, inter-reflection included. Computing that ratio
from the direct component alone does not give a conservative U0; it gives a
different quantity, and it fails worst exactly where U0 is most sensitive.
Measured on the mock bedroom: Emin was 0.33 lx of direct light in the far
corner while the estimated inter-reflected component there is 32-54 lx --
about 100x larger. So the ratio was set almost entirely by light this
engine does not model.

The ratio is therefore exposed as `uniformity_direct`, named so that a
caller cannot mistake it for U0, and no rule adjudicates it. What this
calculation does support, and what the Stage 5 rules are built on:

    average illuminance over the room
    illuminance at named task points (bedside, desk)
    layer count            -- topology, no photometric uncertainty at all
    installed power density -- arithmetic, given a stated wattage

A real U0 waits for Radiance. `interreflected_estimate` gives a range for
the missing component so a room can still be discussed as "will this feel
gloomy", but it returns a RANGE precisely because it cannot decide a
verdict.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from .photometry import Photometry

MM_TO_M = 0.001

# Height of the horizontal plane illuminance is assessed on. 850 mm is the
# usual residential/task convention (desk and counter height); EN 12464-1
# assesses the task area, and for a bedroom the reading and dressing tasks
# both sit near this height. Floor level is used for circulation.
WORKING_PLANE_MM = 850.0

# Maintenance factor (the "light loss factor"): the ratio of maintained to
# initial illuminance, combining lamp lumen depreciation, luminaire dirt
# depreciation and room surface dirt. 0.80 is the ordinary figure for a
# clean domestic interior with LED sources on a normal cleaning cycle.
# Fluorescent or a dusty environment warrants less; this is deliberately
# not optimistic.
DEFAULT_MAINTENANCE_FACTOR = 0.80

# Grid spacing. 250 mm is much finer than any standard requires for a room
# this size, and `converged()` exists so the choice never has to be taken
# on trust.
DEFAULT_SPACING_MM = 250.0

# The distance-to-size ratio above which the point-source assumption is
# ordinarily accepted. Standard photometric practice.
POINT_SOURCE_RATIO = 5.0

# Lighting layers. The "no lone central fixture" rule turns on these: a
# single pendant in the ceiling rose lights a room evenly and flatly, and
# is the signature of an unconsidered scheme. Hospitality practice, and the
# WELL Building Standard's visual-lighting-design concept, both call for
# separately controlled layers.
LAYERS = ("ambient", "task", "accent", "decorative")


class LightingError(ValueError):
    pass


@dataclass(frozen=True)
class Luminaire:
    """One light fitting, placed.

    `x`, `y` are millimetres in the model frame; `z` is the height of the
    luminaire above the floor of its room, also millimetres. `aim` rotates
    an asymmetric distribution about the vertical axis, degrees
    anticlockwise. `output` scales the whole thing, for dimming or for a
    lamp swapped for a different lumen package.
    """

    id: str
    photometry: Photometry
    x: float
    y: float
    z: float
    aim: float = 0.0
    output: float = 1.0
    layer: str = "ambient"
    room: str = ""
    # Real circuit watts of the fitting as specified. Deliberately NOT
    # defaulted from the photometry: the IES files Revit ships are legacy
    # incandescent and T12 fluorescent, so their wattage describes a lamp
    # nobody would specify in 2026 while their distribution is still the
    # right shape. Leaving this None makes the scheme's load unreportable,
    # which is the honest outcome, rather than reporting a wrong number.
    watts: float | None = None

    def __post_init__(self) -> None:
        if self.layer not in LAYERS:
            raise LightingError(
                f"luminaire {self.id}: unknown layer {self.layer!r}; "
                f"expected one of {', '.join(LAYERS)}")
        if not 0.0 <= self.output <= 1.0:
            raise LightingError(
                f"luminaire {self.id}: output {self.output} is outside 0..1. "
                f"To specify a brighter lamp, change the photometry rather "
                f"than scaling past 100% -- otherwise the luminaire no "
                f"longer matches any real product.")
        if self.z <= 0:
            raise LightingError(
                f"luminaire {self.id}: mounting height must be above the "
                f"floor, got {self.z} mm")

    def illuminance_at(self, x: float, y: float, plane_z: float) -> float:
        """Direct illuminance in lux at a point on a horizontal plane.

        Returns 0.0 for a luminaire at or below the plane -- an uplighter
        contributes nothing directly downward, and the honest answer is
        zero rather than a sign error.
        """
        h_mm = self.z - plane_z
        if h_mm <= 0:
            return 0.0
        return self.output * self.photometry.illuminance_at(
            (x - self.x) * MM_TO_M, (y - self.y) * MM_TO_M,
            h_mm * MM_TO_M, aim=self.aim)


@dataclass(frozen=True)
class LuxGrid:
    """A computed illuminance field and the metrics drawn from it.

    Every lux value here is **maintained** and **direct-only** -- see the
    module docstring. `note` carries that caveat so a result cannot be
    passed to a client stripped of it.
    """

    room: str
    spacing: float
    working_plane: float
    maintenance_factor: float
    bounds: tuple[float, float, float, float]      # x0, y0, x1, y1 in mm
    points: tuple[tuple[float, float, float], ...]  # (x, y, lux), mm and lx
    luminaires: tuple[Luminaire, ...] = ()
    note: str = (
        "Maintained illuminance, direct component only. Inter-reflection is "
        "not modelled, so a light-coloured room will measure 10-25% higher "
        "than this. Values are therefore conservative.")

    # ----------------------------------------------------------- the metrics

    @property
    def values(self) -> tuple[float, ...]:
        return tuple(p[2] for p in self.points)

    @property
    def average(self) -> float:
        v = self.values
        return sum(v) / len(v) if v else 0.0

    @property
    def minimum(self) -> float:
        return min(self.values) if self.points else 0.0

    @property
    def maximum(self) -> float:
        return max(self.values) if self.points else 0.0

    @property
    def unlit_samples(self) -> int:
        """Samples receiving no direct light at all.

        Not a fault. A lensed downlight genuinely emits 0 cd beyond its
        cut-off angle, so a room corner outside every beam receives zero
        DIRECT light and is lit entirely by inter-reflection -- which this
        module does not model. Such a sample is outside the modelled
        domain, not dark.
        """
        return sum(1 for p in self.points if p[2] <= 0.0)

    # NO `uniformity` PROPERTY, DELIBERATELY.
    #
    # EN 12464-1 defines U0 = Emin/Eavg on **total maintained**
    # illuminance, which includes inter-reflection. A ratio computed from
    # the direct component alone is not a conservative U0 -- it is a
    # different quantity that merely resembles one, and it is worthless
    # for the specific reason that Emin is where the two diverge most.
    #
    # Measured on the mock bedroom: Emin came to 0.33 lx of direct light at
    # the far corner while the estimated inter-reflected component there is
    # 32-54 lx -- about 100x larger. So the ratio is set almost entirely by
    # a term this engine does not model. Note that gating on "is the
    # sample lit at all" does not rescue it: 0.33 lx passes that test and
    # is still swamped.
    #
    # Naming the quantity honestly is a stronger guard than any threshold,
    # because it makes the misuse visible at the call site instead of
    # depending on a number I would have to justify. A real U0 needs
    # inter-reflection modelled -- Radiance's job, per ADR-0004.

    @property
    def uniformity_direct(self) -> float:
        """Emin/Eavg of the DIRECT component only.

        **This is not EN 12464-1's U0 and must not be compared against its
        thresholds.** It is reported because a very low value is a useful
        signal that a scheme relies on inter-reflection to fill the room,
        which is worth a designer's attention. It is not a verdict.
        """
        a = self.average
        return self.minimum / a if a > 0 else 0.0

    @property
    def diversity_direct(self) -> float:
        """Emin/Emax of the direct component only. Same caveat as above."""
        m = self.maximum
        return self.minimum / m if m > 0 else 0.0

    def assessment_note(self) -> str:
        """What this grid can and cannot be used to judge, in words a client
        can read."""
        n, total = self.unlit_samples, len(self.points)
        lines = [
            "Valid from this calculation: average illuminance, and "
            "illuminance at named task points.",
            "NOT valid: uniformity (EN 12464-1 U0). That is defined on total "
            "illuminance including inter-reflection, which is not modelled "
            "here, and it is most sensitive to exactly the darkest points "
            "where the unmodelled light dominates.",
        ]
        if n:
            lines.append(
                f"{n} of {total} samples ({n / total:.0%}) receive no direct "
                f"light at all -- they lie outside every luminaire's beam and "
                f"are lit entirely by inter-reflection.")
        return " ".join(lines)

    # Installed load. The IES file's `input_watts` is a fact about the
    # FILE, and the files Revit ships are 1990s photometry -- incandescent
    # A21 and T12 fluorescent, 16-35 lm/W. Their DISTRIBUTIONS are
    # perfectly reusable and that is what we use them for, but reporting
    # their wattage as this scheme's load would describe a scheme nobody
    # would build. So real wattage must be stated on the Luminaire, and
    # `total_load` is None until it is.
    @property
    def total_load(self) -> float | None:
        if not self.luminaires:
            return None
        if any(l.watts is None for l in self.luminaires):
            return None
        return sum(l.watts * l.output for l in self.luminaires)

    @property
    def area_m2(self) -> float:
        """Grid area in m2 -- each sample owns one cell."""
        return len(self.points) * (self.spacing * MM_TO_M) ** 2

    @property
    def power_density(self) -> float | None:
        """W/m2, or None when any luminaire's real wattage is unstated.

        A useful cross-check once it is available: a domestic room lit well
        with LED lands around 3-6 W/m2, and much above 10 suggests either
        an inefficient specification or too many fittings. That heuristic
        is about LED, which is why it must not be applied to the wattages
        in legacy IES files -- doing so would fail every scheme built from
        the Revit library for a reason that is an artefact of the file.
        """
        load, a = self.total_load, self.area_m2
        if load is None or a <= 0:
            return None
        return load / a

    def layers_present(self) -> tuple[str, ...]:
        return tuple(sorted({l.layer for l in self.luminaires}))

    def point_source_warnings(self) -> tuple[str, ...]:
        """Luminaires whose size makes the point-source assumption shaky.

        Compares the shortest distance from the luminaire to any grid point
        against five times its largest luminous dimension.
        """
        out = []
        for l in self.luminaires:
            w, ln, h = l.photometry.luminous_dimensions_m()
            size = max(abs(w), abs(ln), abs(h))
            if size <= 0:
                continue                      # declared a point; nothing to check
            nearest = min(
                (math.dist((p[0], p[1], self.working_plane), (l.x, l.y, l.z))
                 for p in self.points), default=float("inf")) * MM_TO_M
            if nearest < POINT_SOURCE_RATIO * size:
                out.append(
                    f"{l.id}: nearest grid point is {nearest:.2f} m from a "
                    f"luminaire {size:.2f} m across (want >= "
                    f"{POINT_SOURCE_RATIO * size:.2f} m). Peak illuminance "
                    f"beneath it is overstated.")
        return tuple(out)

    def summary(self) -> str:
        pd = self.power_density
        # "Emin/Eavg(direct)" spelled out rather than "U0", so a figure
        # lifted out of this line into a report still carries its caveat.
        return (f"{self.room}: Eavg {self.average:.0f} lx, "
                f"Emin {self.minimum:.1f}, Emax {self.maximum:.0f}, "
                f"Emin/Eavg(direct only, NOT U0) "
                f"{self.uniformity_direct:.3f}, "
                f"{'load not stated' if pd is None else f'{pd:.1f} W/m2'}, "
                f"layers: {', '.join(self.layers_present()) or 'none'}")


# ------------------------------------------------------------------ the engine

def lux_grid(boundary: list[tuple[float, float]], luminaires: list[Luminaire],
             *, room: str = "", spacing: float = DEFAULT_SPACING_MM,
             working_plane: float = WORKING_PLANE_MM,
             maintenance_factor: float = DEFAULT_MAINTENANCE_FACTOR,
             border: float = 0.0) -> LuxGrid:
    """Compute maintained direct illuminance over a room's working plane.

    `boundary` is a closed-or-open polygon of (x, y) in millimetres.
    `border` insets the sampled area from the walls; the default of 0
    samples right to the wall line deliberately. EN 12464-1 excludes a
    border band when assessing a *task area*, but a dark corner by the
    wardrobe is a real defect an occupant will notice, and excluding it by
    default would hide exactly the finding worth making.

    Samples are placed at cell centres, so no sample ever lands exactly on
    the boundary where inside/outside is ambiguous.
    """
    if spacing <= 0:
        raise LightingError("grid spacing must be positive")
    if not 0.0 < maintenance_factor <= 1.0:
        raise LightingError(
            f"maintenance factor {maintenance_factor} must be in (0, 1]; "
            f"a value above 1 would claim the fitting gets brighter with age")
    if len(boundary) < 3:
        raise LightingError(f"room boundary needs at least 3 points, got "
                            f"{len(boundary)}")

    from shapely.geometry import Point, Polygon

    poly = Polygon(boundary)
    if not poly.is_valid:
        raise LightingError(
            f"room boundary for {room or 'room'} is not a simple polygon "
            f"(it self-intersects); a lux grid over it would be meaningless")
    if border > 0:
        poly = poly.buffer(-border)
        if poly.is_empty:
            raise LightingError(
                f"a border of {border:.0f} mm leaves nothing to sample in "
                f"{room or 'this room'}")

    x0, y0, x1, y1 = poly.bounds
    nx = max(1, int(math.ceil((x1 - x0) / spacing)))
    ny = max(1, int(math.ceil((y1 - y0) / spacing)))

    points: list[tuple[float, float, float]] = []
    for iy in range(ny):
        y = y0 + (iy + 0.5) * spacing
        for ix in range(nx):
            x = x0 + (ix + 0.5) * spacing
            if not poly.covers(Point(x, y)):
                continue
            lux = sum(l.illuminance_at(x, y, working_plane) for l in luminaires)
            points.append((x, y, lux * maintenance_factor))

    if not points:
        raise LightingError(
            f"no grid points fell inside {room or 'the room'} at "
            f"{spacing:.0f} mm spacing -- the boundary is smaller than one "
            f"cell, or its units are not millimetres")

    return LuxGrid(
        room=room, spacing=spacing, working_plane=working_plane,
        maintenance_factor=maintenance_factor,
        bounds=(x0, y0, x1, y1), points=tuple(points),
        luminaires=tuple(luminaires),
    )


def converged(boundary: list[tuple[float, float]], luminaires: list[Luminaire],
              *, spacing: float = DEFAULT_SPACING_MM, tolerance: float = 0.02,
              **kw) -> tuple[bool, float, float]:
    """Is the grid fine enough? Halve the spacing and see if the answer moves.

    Returns (converged, Eavg at `spacing`, Eavg at half `spacing`). Reciting
    a standard's grid formula proves nothing about a particular room; this
    measures the thing the formula is a proxy for.
    """
    coarse = lux_grid(boundary, luminaires, spacing=spacing, **kw)
    fine = lux_grid(boundary, luminaires, spacing=spacing / 2.0, **kw)
    a, b = coarse.average, fine.average
    drift = abs(a - b) / b if b > 0 else 0.0
    return drift <= tolerance, a, b


def point_illuminance(luminaires: list[Luminaire], x: float, y: float,
                      plane_z: float = WORKING_PLANE_MM, *,
                      maintenance_factor: float = DEFAULT_MAINTENANCE_FACTOR
                      ) -> float:
    """Maintained direct illuminance at one named point, in lux.

    This -- not uniformity -- is what a direct calculation genuinely
    supports. At a reading pillow or a desk the task fitting is close and
    aimed, so the direct component dominates and inter-reflection is a
    small correction in the conservative direction. A task-illuminance
    rule can therefore carry a measurement; a uniformity rule cannot.
    """
    return maintenance_factor * sum(
        l.illuminance_at(x, y, plane_z) for l in luminaires)


@dataclass(frozen=True)
class Surfaces:
    """Room surface reflectances, for the inter-reflection estimate.

    Defaults are the ordinary decorated-interior figures: a white ceiling,
    mid-toned walls and a timber or mid-carpet floor.
    """

    ceiling: float = 0.70
    walls: float = 0.50
    floor: float = 0.20


@dataclass(frozen=True)
class InterReflectedEstimate:
    """A RANGE for the inter-reflected component, with its reasoning.

    A range and not a number, deliberately. See `interreflected_estimate`.
    """

    low: float
    high: float
    area: float
    average_reflectance: float
    note: str

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2.0

    @property
    def spread(self) -> float:
        return self.high / self.low if self.low > 0 else float("inf")


def interreflected_estimate(grid: LuxGrid, width: float, depth: float,
                            height: float, *,
                            surfaces: Surfaces = Surfaces()
                            ) -> InterReflectedEstimate:
    """Estimate the inter-reflected illuminance, as a range. NOT for
    adjudication.

    The classical integrating-cavity result: flux F emitted into a cavity
    of total surface area A and average reflectance rho returns

        F*rho + F*rho^2 + ... = F*rho/(1 - rho)

    of inter-reflected flux to the surfaces, so the average added
    illuminance is `F*rho / (A*(1 - rho))`. This is the inter-reflected
    component of the classical lumen method, and it adds to the direct
    calculation without double counting -- the direct component is the
    first arrival, this is every arrival after it.

    WHY A RANGE, AND WHY IT MUST NOT DECIDE ANYTHING

    The formula's first bounce assumes flux lands on surfaces in
    proportion to their AREA. For a scheme of lensed downlights it does
    not: most flux goes to the floor, which has the lowest reflectance,
    while the area-weighted figure credits the ceiling with intercepting
    its area share. Measured on the mock bedroom, the two treatments give
    68 lx and 36 lx -- a factor of 1.9 on the term that would dominate any
    uniformity figure.

    So this returns both bounds. `high` is the area-weighted result;
    `low` weights the first bounce towards the floor, as a downlight scheme
    actually behaves. A metric with 1.9x uncertainty in its leading term
    cannot support a pass/fail with a measurement attached, which is why
    Stage 5's rules assess layer count, task illuminance and average
    illuminance instead. Uniformity waits for Radiance (ADR-0004).

    `width`, `depth` and `height` are the room's internal dimensions in
    millimetres.
    """
    w, d, h = width * MM_TO_M, depth * MM_TO_M, height * MM_TO_M
    if min(w, d, h) <= 0:
        raise LightingError("room dimensions must be positive")

    a_floor = a_ceiling = w * d
    a_walls = 2.0 * (w + d) * h
    area = a_floor + a_ceiling + a_walls

    rho = (a_floor * surfaces.floor + a_ceiling * surfaces.ceiling
           + a_walls * surfaces.walls) / area
    if rho >= 1.0:
        raise LightingError("average reflectance must be below 1.0")

    flux = sum(l.photometry.total_lumens * l.output for l in grid.luminaires)
    denom = area * (1.0 - rho)

    # Upper bound: first bounce weighted by area.
    high = flux * rho / denom
    # Lower bound: first bounce weighted towards the floor, as a downlight
    # scheme behaves. 75/20/5 floor/wall/ceiling is the split measured for
    # the mock bedroom's lensed and narrow-beam fittings.
    rho_first = 0.75 * surfaces.floor + 0.20 * surfaces.walls + 0.05 * surfaces.ceiling
    low = flux * rho_first / denom

    # Surface dirt depreciation is precisely what the maintenance factor
    # covers, and inter-reflection depends on surfaces staying clean more
    # than the direct component does. Applying it here keeps the estimate
    # on the same footing as the grid it would be added to.
    mf = grid.maintenance_factor
    low, high = low * mf, high * mf

    return InterReflectedEstimate(
        low=low, high=high, area=area, average_reflectance=rho,
        note=(f"Inter-reflected component estimated at {low:.0f}-{high:.0f} lx "
              f"(maintained) from {flux:.0f} lm into {area:.1f} m2 at average "
              f"reflectance {rho:.2f}. The spread is a factor of "
              f"{high / low if low > 0 else float('inf'):.1f}, because how "
              f"much first-bounce flux reaches the bright ceiling rather than "
              f"the dark floor is not known from the photometry alone. "
              f"Indicative of whether the room will feel gloomy; NOT a basis "
              f"for a uniformity verdict."),
    )


# ------------------------------------------------------------- false colour

# Stops for the heat map, in lux, with colours that stay distinguishable in
# greyscale print (increasing lightness then decreasing) and are not a
# red/green pair. A map without a numbered legend is decoration, so
# `heatmap_svg` always draws one.
_SCALE = (
    (0.0, "#08306b"), (50.0, "#2171b5"), (100.0, "#6baed6"),
    (150.0, "#c7e9c0"), (200.0, "#fdd835"), (300.0, "#fb8c00"),
    (500.0, "#b71c1c"),
)


def _colour(lux: float) -> str:
    stops = _SCALE
    if lux <= stops[0][0]:
        return stops[0][1]
    if lux >= stops[-1][0]:
        return stops[-1][1]
    for (v0, c0), (v1, c1) in zip(stops, stops[1:]):
        if v0 <= lux <= v1:
            t = 0.0 if v1 == v0 else (lux - v0) / (v1 - v0)
            return _mix(c0, c1, t)
    return stops[-1][1]


def _mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = (int(a[i:i + 2], 16) for i in (1, 3, 5))
    br, bg, bb = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (round(ar + (br - ar) * t),
                              round(ag + (bg - ag) * t),
                              round(ab + (bb - ab) * t))


def heatmap_svg(grid: LuxGrid, path: str | Path, *,
                boundary: list[tuple[float, float]] | None = None,
                scale: float = 0.05, target: tuple[float, float] | None = None
                ) -> Path:
    """Write a false-colour illuminance map as SVG.

    SVG rather than a raster: it stays inspectable, scales into the A3
    sheet without resampling, and adds no dependency. `scale` is px per mm.

    The Y axis is flipped, because model Y increases north while SVG Y
    increases down -- the same convention `render_dxf.py` uses, and getting
    it wrong mirrors the room silently.
    """
    x0, y0, x1, y1 = grid.bounds
    pad = 40.0
    # The caption is wrapped rather than allowed to run off the canvas. A
    # summary clipped at the right edge loses the caveat that is the whole
    # reason it is printed, and it loses it silently.
    caption = _wrap(grid.summary(), 78)
    footer = "Direct component only; inter-reflection not modelled, so " \
             "values are conservative."
    legend_h = 58.0 + 11.0 * (len(caption) + 1)
    w = max((x1 - x0) * scale + 2 * pad, 2 * pad + 6.0 * max(
        [len(footer)] + [len(l) for l in caption]))
    h = (y1 - y0) * scale + 2 * pad + legend_h
    cell = grid.spacing * scale

    def sx(x: float) -> float:
        return pad + (x - x0) * scale

    def sy(y: float) -> float:
        return pad + (y1 - y) * scale

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" '
        f'height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g shape-rendering="crispEdges">',
    ]
    for x, y, lux in grid.points:
        out.append(f'<rect x="{sx(x) - cell / 2:.2f}" y="{sy(y) - cell / 2:.2f}" '
                   f'width="{cell:.2f}" height="{cell:.2f}" '
                   f'fill="{_colour(lux)}"/>')
    out.append("</g>")

    if boundary:
        pts = " ".join(f"{sx(px):.2f},{sy(py):.2f}" for px, py in boundary)
        out.append(f'<polygon points="{pts}" fill="none" stroke="#111111" '
                   f'stroke-width="1.6"/>')

    for l in grid.luminaires:
        cx, cy = sx(l.x), sy(l.y)
        out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="4" '
                   f'fill="none" stroke="#111111" stroke-width="1.2"/>')
        out.append(f'<line x1="{cx - 6:.2f}" y1="{cy:.2f}" x2="{cx + 6:.2f}" '
                   f'y2="{cy:.2f}" stroke="#111111" stroke-width="1"/>')
        out.append(f'<line x1="{cx:.2f}" y1="{cy - 6:.2f}" x2="{cx:.2f}" '
                   f'y2="{cy + 6:.2f}" stroke="#111111" stroke-width="1"/>')

    # Legend: a colour ramp with real lux numbers on it.
    ly = h - legend_h + 16
    bar_w = min(w - 2 * pad, 320.0)
    steps = 64
    for i in range(steps):
        lux = _SCALE[0][0] + (_SCALE[-1][0] - _SCALE[0][0]) * i / (steps - 1)
        out.append(f'<rect x="{pad + bar_w * i / steps:.2f}" y="{ly:.2f}" '
                   f'width="{bar_w / steps + 0.6:.2f}" height="12" '
                   f'fill="{_colour(lux)}"/>')
    out.append(f'<rect x="{pad:.2f}" y="{ly:.2f}" width="{bar_w:.2f}" '
               f'height="12" fill="none" stroke="#666" stroke-width="0.6"/>')
    for frac, label in ((0.0, "0"), (0.2, "100"), (0.4, "200"),
                        (0.6, "300"), (1.0, "500+")):
        out.append(f'<text x="{pad + bar_w * frac:.2f}" y="{ly + 25:.2f}" '
                   f'font-family="sans-serif" font-size="9" '
                   f'text-anchor="middle" fill="#222">{label}</text>')
    out.append(f'<text x="{pad:.2f}" y="{ly - 5:.2f}" font-family="sans-serif" '
               f'font-size="10" fill="#222">Maintained illuminance (lux) at '
               f'{grid.working_plane:.0f} mm, MF {grid.maintenance_factor:.2f}'
               f'</text>')
    ty = ly + 42.0
    for line in caption:
        out.append(f'<text x="{pad:.2f}" y="{ty:.2f}" '
                   f'font-family="sans-serif" font-size="9" fill="#444">'
                   f'{_esc(line)}</text>')
        ty += 11.0
    out.append(f'<text x="{pad:.2f}" y="{ty:.2f}" font-family="sans-serif" '
               f'font-size="8" fill="#777">{_esc(footer)}</text>')
    if target:
        out.append(f'<text x="{pad + bar_w + 12:.2f}" y="{ly + 10:.2f}" '
                   f'font-family="sans-serif" font-size="9" fill="#222">'
                   f'target {target[0]:.0f}-{target[1]:.0f} lx</text>')
    out.append("</svg>")

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(out), encoding="utf-8")
    return p


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _wrap(text: str, width: int) -> list[str]:
    """Greedy word wrap. SVG has no text flow, so a caption that must stay
    readable has to be broken here."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


# ----------------------------------------------------------------- self-check

def verify() -> list[str]:
    """Validate the engine against hand calculation before any heat map is
    trusted. Returns a list of failures; empty means good.

    The plan is explicit that this comes first: a false-colour image is
    persuasive whether or not it is right.
    """
    from .photometry import parse

    fails: list[str] = []

    def chk(label: str, got: float, want: float, tol: float) -> None:
        if abs(got - want) > tol:
            fails.append(f"{label}: got {got!r}, want {want!r} (+/-{tol})")

    # An isotropic 1000 cd source, so every expected value is calculable
    # by hand from E = I*h/d^3.
    iso = parse("\n".join([
        "IESNA:LM-63-2002", "[TEST] synthetic isotropic", "TILT=NONE",
        "1 1000 1 3 1 1 2 0 0 0", "1 1 10", "0 45 90", "0",
        "1000 1000 1000"]), name="iso-1000cd")

    # 4000 x 4000 mm room, one luminaire dead centre at 2850 mm, working
    # plane 850 -> mounting height above the plane is exactly 2000 mm.
    room = [(0.0, 0.0), (4000.0, 0.0), (4000.0, 4000.0), (0.0, 4000.0)]
    lum = Luminaire("L1", iso, 2000.0, 2000.0, 2850.0)

    # Directly below: E = I/h^2 = 1000/4 = 250 lx, times MF.
    direct = lum.illuminance_at(2000.0, 2000.0, WORKING_PLANE_MM)
    chk("isotropic directly below (250 lx)", direct, 250.0, 1e-9)

    # Maintenance factor must be applied exactly once.
    g = lux_grid(room, [lum], room="test", spacing=250.0,
                 maintenance_factor=0.80)

    # The brightest SAMPLE is not 250 x 0.80 = 200 lx, and it should not be.
    # Samples sit at cell centres (125, 375, ... 3875 mm), so with the
    # fitting at 2000 mm -- a cell corner -- the nearest sample is offset
    # 125 mm in both x and y. Hand calculation for that point:
    #   r = 125*sqrt(2) = 176.8 mm, h = 2000 mm, E = I*h/d^3 * MF
    # This is worth asserting precisely rather than loosely: a test that
    # accepted 200 lx here would also accept a grid that had quietly
    # snapped its samples onto the luminaire.
    _r = 0.125 * math.sqrt(2.0)
    _d = math.hypot(_r, 2.0)
    chk("brightest sample matches hand calculation",
        g.maximum, 1000.0 * 2.0 / _d ** 3 * 0.80, 1e-6)
    if g.maximum > 250.0 * 0.80:
        fails.append(f"brightest sample {g.maximum:.2f} lx exceeds the value "
                     f"directly beneath the fitting ({250.0 * 0.80:.2f} lx)")
    if not 0.99 <= g.maintenance_factor / 0.80 <= 1.01:
        fails.append("grid did not record its maintenance factor")

    # Grid geometry: a 4 m square at 250 mm must give 16 x 16 = 256 samples.
    if len(g.points) != 256:
        fails.append(f"expected 256 samples in a 4x4 m room at 250 mm, "
                     f"got {len(g.points)}")

    # The dimmest point is a corner. Nearest sample centre to (0,0) is
    # (125,125): dx = dy = 1875 mm, h = 2000 mm.
    r = math.hypot(1.875, 1.875)
    d = math.hypot(r, 2.0)
    chk("corner lux matches hand calculation",
        g.minimum, 1000.0 * 2.0 / d ** 3 * 0.80, 0.01)

    # Metric identities. The isotropic source reaches every corner, so this
    # grid reaches every corner.
    if g.unlit_samples:
        fails.append(f"isotropic grid should be fully lit, but "
                     f"{g.unlit_samples} samples got no direct light")
    chk("Emin/Eavg direct", g.uniformity_direct, g.minimum / g.average, 1e-12)
    chk("Emin/Emax direct", g.diversity_direct, g.minimum / g.maximum, 1e-12)
    if not g.minimum <= g.average <= g.maximum:
        fails.append("min <= avg <= max violated")

    # The module must not expose a bare `uniformity`/`diversity`. EN 12464-1
    # defines U0 on total illuminance; offering that name on a direct-only
    # grid invites a rule to adjudicate it, which is the failure this
    # design exists to prevent. Naming is the guard, so the name is tested.
    for attr in ("uniformity", "diversity"):
        if hasattr(g, attr):
            fails.append(
                f"LuxGrid exposes `{attr}`. A direct-only calculation must "
                f"not offer a name that reads as EN 12464-1's U0; use "
                f"`{attr}_direct`, which carries the caveat at the call site.")
    if "NOT U0" not in g.summary():
        fails.append("summary() must mark the ratio as not being U0")
    note = g.assessment_note()
    if "NOT valid: uniformity" not in note:
        fails.append("assessment_note must state that uniformity is not "
                     "assessable from a direct-only calculation")
    if "task points" not in note:
        fails.append("assessment_note must state what IS valid")

    # A luminaire with a hard cut-off leaves samples outside its beam with
    # zero DIRECT light. Those samples are outside the modelled domain, not
    # dark, and the grid must say so plainly while keeping the metrics that
    # remain valid.
    cutoff = parse("\n".join([
        "IESNA91", "[TEST] hard cut-off at 30 degrees", "TILT=NONE",
        "1 1500 1 4 1 1 2 0 0 0", "1 1 15",
        "0 10 20 30", "0", "2000 1800 900 100"]), name="cutoff-30deg")
    gc = lux_grid(room, [Luminaire("C1", cutoff, 2000.0, 2000.0, 2850.0)],
                  room="cut-off", spacing=250.0)
    if gc.unlit_samples == 0:
        fails.append("a 30-degree cut-off fitting lit every corner of a "
                     "4x4 m room; the test probe is wrong")
    else:
        if f"{gc.unlit_samples} of" not in gc.assessment_note():
            fails.append("assessment_note must count the samples receiving "
                         "no direct light")
        if gc.average <= 0:
            fails.append("average illuminance must remain valid and positive "
                         "even where the ratio metrics do not")
        chk("minimum is exactly zero outside the beam", gc.minimum, 0.0, 0.0)
        chk("direct ratio is zero when Emin is zero",
            gc.uniformity_direct, 0.0, 0.0)
        try:
            gc.summary()
        except (TypeError, ValueError) as e:
            fails.append(f"summary() raised on a partly-unlit grid: {e}")

    # Legacy wattage must not be invented. The IES files Revit ships are
    # incandescent and T12; reporting their wattage as a scheme's load
    # would fail every scheme for an artefact of the file.
    if g.total_load is not None or g.power_density is not None:
        fails.append("load and power density must be None until a real "
                     "wattage is stated on every luminaire")
    lit = Luminaire("W1", iso, 2000.0, 2000.0, 2850.0, watts=12.0)
    gw = lux_grid(room, [lit], spacing=500.0)
    chk("stated wattage is used", gw.total_load, 12.0, 1e-9)
    chk("power density = W / grid area", gw.power_density,
        12.0 / gw.area_m2, 1e-9)
    # Dimming must scale the load as well as the light.
    gd = lux_grid(room, [Luminaire("W2", iso, 2000.0, 2000.0, 2850.0,
                                   watts=12.0, output=0.5)], spacing=500.0)
    chk("dimming scales the load", gd.total_load, 6.0, 1e-9)

    # Task illuminance: the metric a direct calculation does support.
    chk("point_illuminance matches the grid's own arithmetic",
        point_illuminance([lum], 2000.0, 2000.0, maintenance_factor=0.80),
        250.0 * 0.80, 1e-9)

    # The inter-reflection estimate must come back as an ordered range
    # wide enough to make clear it cannot adjudicate anything.
    irc = interreflected_estimate(g, 4000.0, 4000.0, 2700.0)
    if not 0.0 < irc.low < irc.high:
        fails.append(f"inter-reflection estimate is not an ordered positive "
                     f"range: {irc.low} .. {irc.high}")
    if irc.spread < 1.3:
        fails.append(f"the estimate's spread ({irc.spread:.2f}x) understates "
                     f"how uncertain the first-bounce split is; the bedroom "
                     f"measurement was 1.9x")
    if "NOT a basis" not in irc.note:
        fails.append("the estimate must say in words that it cannot decide "
                     "a uniformity verdict")
    # Doubling installed flux must double the inter-reflected component.
    irc2 = interreflected_estimate(
        lux_grid(room, [lum, lum], spacing=500.0), 4000.0, 4000.0, 2700.0)
    chk("inter-reflection is linear in flux", irc2.high, irc.high * 2.0, 1e-6)

    # A lone central NARROW-BEAM fitting must fail a uniformity test. If it
    # did not, the engine could not tell a good scheme from a bad one and
    # every downstream rule would be worthless.
    #
    # The beam matters, and the isotropic source above is the wrong probe:
    # it throws light sideways as hard as downward and scores U0 0.42 in
    # this room, which is genuinely not bad. Asserting that *any* single
    # central fitting fails would be asserting something untrue. A real
    # downlight is what makes a lone central fixture a defect, so that is
    # what gets tested.
    spot = parse("\n".join([
        "IESNA91", "[TEST] synthetic narrow beam", "TILT=NONE",
        "1 1500 1 5 1 1 2 0 0 0", "1 1 15",
        "0 10 20 30 90", "0",
        "2000 1800 900 100 0"]), name="spot-30deg")
    gs = lux_grid(room, [Luminaire("S1", spot, 2000.0, 2000.0, 2850.0)],
                  room="lone spot", spacing=250.0)
    if gs.uniformity_direct >= 0.4:
        fails.append(f"a lone central narrow-beam downlight scored "
                     f"Emin/Eavg {gs.uniformity_direct:.2f} on the direct "
                     f"component; it should come out far below 0.4")

    # Four fittings on a regular grid must beat one in the middle. This is
    # the whole argument for layered lighting, so it had better hold.
    quad = [Luminaire(f"Q{i}", iso, x, y, 2850.0)
            for i, (x, y) in enumerate(
                [(1000.0, 1000.0), (3000.0, 1000.0),
                 (1000.0, 3000.0), (3000.0, 3000.0)])]
    gq = lux_grid(room, quad, room="quad", spacing=250.0)
    if gq.uniformity_direct <= g.uniformity_direct:
        fails.append(f"four spread fittings ({gq.uniformity_direct:.2f}) did "
                     f"not beat one central fitting "
                     f"({g.uniformity_direct:.2f}) on Emin/Eavg")

    # Superposition: illuminance adds linearly.
    single = lux_grid(room, [quad[0]], spacing=500.0).values
    pair = lux_grid(room, [quad[0], quad[0]], spacing=500.0).values
    if any(abs(2 * a - b) > 1e-9 for a, b in zip(single, pair)):
        fails.append("illuminance is not additive; superposition broken")

    # Inverse square through the full stack, not just the photometry.
    high = Luminaire("H", iso, 2000.0, 2000.0, 850.0 + 4000.0)
    chk("doubling height quarters the lux",
        high.illuminance_at(2000.0, 2000.0, WORKING_PLANE_MM),
        direct / 4.0, 1e-9)

    # Convergence: 250 mm must already be fine enough.
    ok, coarse, fine = converged(room, quad, spacing=250.0)
    if not ok:
        fails.append(f"250 mm grid not converged: Eavg {coarse:.1f} vs "
                     f"{fine:.1f} at 125 mm")

    # An uplighter below the plane contributes nothing downward, and must
    # not come back negative.
    up = Luminaire("U", iso, 2000.0, 2000.0, 400.0)
    chk("luminaire below the working plane gives 0",
        up.illuminance_at(2000.0, 2000.0, WORKING_PLANE_MM), 0.0, 0.0)

    # Bad input must raise rather than return a plausible number.
    for label, fn in (
        ("self-intersecting boundary", lambda: lux_grid(
            [(0, 0), (4000, 4000), (4000, 0), (0, 4000)], [lum])),
        ("negative spacing", lambda: lux_grid(room, [lum], spacing=-1)),
        ("maintenance factor > 1", lambda: lux_grid(
            room, [lum], maintenance_factor=1.5)),
        ("two-point boundary", lambda: lux_grid([(0, 0), (1, 1)], [lum])),
        ("metres mistaken for mm", lambda: lux_grid(
            [(0, 0), (4, 0), (4, 4), (0, 4)], [lum])),
    ):
        try:
            fn()
            fails.append(f"{label} was accepted; it should raise")
        except LightingError:
            pass

    try:
        Luminaire("bad", iso, 0.0, 0.0, 2400.0, layer="mood")
        fails.append("an unknown lighting layer was accepted")
    except LightingError:
        pass

    # Point-source honesty: a 1.2 m linear fitting 2 m above the plane
    # must be flagged, because 2 m < 5 x 1.2 m.
    linear = parse("\n".join([
        "IESNA91", "TILT=NONE", "1 3000 1 3 1 1 2 0.1 1.2 0", "1 1 30",
        "0 45 90", "0", "900 900 900"]), name="linear-1.2m")
    gl = lux_grid(room, [Luminaire("LIN", linear, 2000.0, 2000.0, 2850.0)],
                  spacing=250.0)
    if not gl.point_source_warnings():
        fails.append("a 1.2 m linear fitting 2 m above the plane was not "
                     "flagged as straining the point-source assumption")

    return fails


if __name__ == "__main__":
    import sys
    problems = verify()
    for p in problems:
        print(f"FAIL  {p}")
    print("lighting: ALL PASS" if not problems
          else f"lighting: {len(problems)} FAILED")
    sys.exit(1 if problems else 0)
