"""Stage 1 (Ground): what the site dictates before a line is drawn.

Orientation is the single highest-leverage decision in a house -- it
drives glazing, shading and outdoor space more than anything else -- so it
is fixed here, from the sun path, rather than discovered during layout.

All plan geometry is millimetres in project coordinates, consistent with
`model.py`. `north_angle` relates project north to true north, so the
drawing can sit square on the page while the analysis stays truthful.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml
from shapely.geometry import Polygon

from . import solar


class SiteError(ValueError):
    """Raised when site data is structurally invalid."""


Point = tuple[float, float]

# Compass sectors used for reporting an aspect, centred on the bearing.
SECTORS = (
    ("N", 0), ("NE", 45), ("E", 90), ("SE", 135),
    ("S", 180), ("SW", 225), ("W", 270), ("NW", 315),
)


def compass(bearing: float) -> str:
    b = bearing % 360
    return min(SECTORS, key=lambda s: min(abs(b - s[1]), 360 - abs(b - s[1])))[0]


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    city: str = ""
    utc_offset_hours: float = 0.0


@dataclass(frozen=True)
class Statutory:
    """The envelope the authority permits. All lengths mm."""
    setback_front: float = 0.0
    setback_rear: float = 0.0
    setback_side: float = 0.0
    height_limit: float = 0.0
    max_storeys: int = 0
    plot_ratio: float = 0.0        # total floor area / plot area
    site_coverage: float = 0.0     # footprint / plot area

    @property
    def max_setback(self) -> float:
        return max(self.setback_front, self.setback_rear, self.setback_side)


@dataclass(frozen=True)
class Neighbour:
    id: str
    boundary: tuple[Point, ...]
    height: float = 0.0


@dataclass(frozen=True)
class Bearing:
    """A direction-bound observation: a view, a noise source, a wind."""
    id: str
    bearing: float          # degrees clockwise from TRUE north
    quality: str = ""       # good | poor | screen
    source: str = ""
    severity: str = ""
    note: str = ""


@dataclass
class Site:
    name: str
    location: Location
    north_angle: float = 0.0        # true-north bearing of project +Y, degrees
    boundary: tuple[Point, ...] = ()
    statutory: Statutory = field(default_factory=Statutory)
    access: Point | None = None
    neighbours: tuple[Neighbour, ...] = ()
    views: tuple[Bearing, ...] = ()
    noise: tuple[Bearing, ...] = ()
    wind: tuple[Bearing, ...] = ()
    spot_levels: tuple[tuple[Point, float], ...] = ()

    # ---- geometry -----------------------------------------------------
    @property
    def polygon(self) -> Polygon:
        if len(self.boundary) < 3:
            raise SiteError("site boundary needs at least 3 points")
        return Polygon(self.boundary)

    @property
    def area_m2(self) -> float:
        return self.polygon.area / 1e6

    def _as_axis_rectangle(self) -> tuple[float, float, float, float] | None:
        """(minx, miny, maxx, maxy) if the plot is an axis-aligned rectangle.

        Worth detecting: it is the common case for a plot, and it is the
        only case where per-side setbacks can be applied without guessing
        which edge is the frontage.
        """
        pts = list(self.boundary)
        if len(pts) == 5 and pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) != 4:
            return None
        xs = sorted({round(p[0], 6) for p in pts})
        ys = sorted({round(p[1], 6) for p in pts})
        if len(xs) != 2 or len(ys) != 2:
            return None
        corners = {(round(p[0], 6), round(p[1], 6)) for p in pts}
        if corners != {(x, y) for x in xs for y in ys}:
            return None
        return xs[0], ys[0], xs[1], ys[1]

    def buildable(self) -> tuple[Polygon, str]:
        """The polygon left after setbacks, plus a note on how it was derived.

        Per-side setbacks need a frontage. For an axis-aligned rectangular
        plot with a known access point the frontage is unambiguous -- it is
        the edge the access sits on -- so the real per-side setbacks are
        applied. Otherwise this falls back to a uniform inward buffer of
        the LARGEST setback, which is conservative but can understate the
        envelope badly enough to change a feasibility verdict. The note
        always says which path was taken.
        """
        s = self.statutory
        if s.max_setback <= 0:
            return self.polygon, "no setbacks applied"

        rect = self._as_axis_rectangle()
        if rect is not None and self.access is not None:
            minx, miny, maxx, maxy = rect
            ax, ay = self.access
            # Which edge does the access sit on? Nearest wins.
            edges = {"south": abs(ay - miny), "north": abs(ay - maxy),
                     "west": abs(ax - minx), "east": abs(ax - maxx)}
            front = min(edges, key=edges.get)
            opposite = {"south": "north", "north": "south",
                        "west": "east", "east": "west"}[front]

            inset = {"south": s.setback_side, "north": s.setback_side,
                     "west": s.setback_side, "east": s.setback_side}
            inset[front] = s.setback_front
            inset[opposite] = s.setback_rear

            x0, y0 = minx + inset["west"], miny + inset["south"]
            x1, y1 = maxx - inset["east"], maxy - inset["north"]
            if x1 <= x0 or y1 <= y0:
                raise SiteError(
                    f"setbacks consume the entire plot "
                    f"(front {s.setback_front:.0f}, rear {s.setback_rear:.0f}, "
                    f"side {s.setback_side:.0f} mm)")
            env = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            return env, (f"per-side setbacks on a rectangular plot; "
                         f"frontage taken as the {front} edge from the access point")

        env = self.polygon.buffer(-s.max_setback)
        if env.is_empty:
            raise SiteError(
                f"setback of {s.max_setback:.0f} mm consumes the entire plot")
        why = ("no access point given" if self.access is None
               else "plot is not an axis-aligned rectangle")
        return env, (f"uniform inward buffer of {s.max_setback:.0f} mm "
                     f"(largest setback) because {why}; this UNDERSTATES the "
                     f"envelope -- give per-side setbacks a frontage to refine")

    def max_footprint_m2(self) -> tuple[float, str]:
        """Permitted footprint: the binding constraint of setbacks and coverage."""
        env, note = self.buildable()
        by_setback = env.area / 1e6
        if self.statutory.site_coverage > 0:
            by_coverage = self.area_m2 * self.statutory.site_coverage
            if by_coverage < by_setback:
                return by_coverage, f"site coverage {self.statutory.site_coverage:.0%} binds"
        return by_setback, f"setbacks bind ({note})"

    def max_floor_area_m2(self) -> tuple[float, str]:
        """Permitted total floor area across all storeys."""
        foot, why = self.max_footprint_m2()
        s = self.statutory
        candidates = []
        if s.max_storeys:
            candidates.append((foot * s.max_storeys,
                               f"{s.max_storeys} storeys x footprint ({why})"))
        if s.plot_ratio > 0:
            candidates.append((self.area_m2 * s.plot_ratio,
                               f"plot ratio {s.plot_ratio}"))
        if not candidates:
            return foot, f"footprint only, no storey or ratio limit given ({why})"
        return min(candidates, key=lambda c: c[0])

    # ---- orientation --------------------------------------------------
    def true_bearing(self, project_bearing: float) -> float:
        """Convert a bearing in project coordinates to a true bearing."""
        return (project_bearing + self.north_angle) % 360.0

    def facade_sun_hours(self, true_facing: float, day: date,
                         step_minutes: int = 10) -> float:
        """Hours of direct sun on a facade facing `true_facing`, on `day`.

        A vertical facade is lit while the sun is above the horizon and
        within 90 degrees of the facade normal. Self-shading and
        neighbouring masses are NOT considered here -- this is the
        available resource, not the delivered one.
        """
        lat, lon = self.location.latitude, self.location.longitude
        lit = 0
        for _, p in solar.day_arc(day, lat, lon, step_minutes):
            if not p.is_up:
                continue
            delta = abs((p.azimuth - true_facing + 180) % 360 - 180)
            if delta < 90:
                lit += 1
        return lit * step_minutes / 60.0

    def orientation_report(self, year: int | None = None) -> list[dict]:
        """Sun hours on each of the eight aspects, at the key dates.

        This is the evidence behind 'put the living room here'.
        """
        year = year or date.today().year
        days = {k: date(year, m, d) for k, (m, d) in solar.KEY_DATES.items()}
        out = []
        for name, bearing in SECTORS:
            row = {"aspect": name, "true_bearing": bearing}
            for label, d in days.items():
                row[label] = round(self.facade_sun_hours(bearing, d), 1)
            row["annual_proxy"] = round(
                (row["summer_solstice"] + row["winter_solstice"]
                 + 2 * row["equinox_march"]) / 4, 1)
            out.append(row)
        return out

    def daylight(self, day: date) -> dict:
        return solar.sun_events(day, self.location.latitude,
                                self.location.longitude)

    # ---- validation ---------------------------------------------------
    def validate(self) -> None:
        if len(self.boundary) < 3:
            raise SiteError("site boundary needs at least 3 points")
        if not (-90 <= self.location.latitude <= 90):
            raise SiteError(f"latitude {self.location.latitude} out of range")
        if not (-180 <= self.location.longitude <= 180):
            raise SiteError(f"longitude {self.location.longitude} out of range")
        if self.polygon.area <= 0:
            raise SiteError("site boundary encloses no area")
        self.buildable()      # raises if setbacks consume the plot

    def gate(self) -> list[str]:
        """Stage 1 gate: is the ground understood well enough to design on?"""
        problems = []
        s = self.statutory
        if s.max_setback <= 0 and s.site_coverage <= 0 and s.plot_ratio <= 0:
            problems.append(
                "No statutory envelope given (setbacks, site coverage or plot "
                "ratio). Feasibility cannot be tested against anything.")
        if not s.max_storeys and not s.plot_ratio:
            problems.append(
                "Neither a storey limit nor a plot ratio is given, so total "
                "permitted floor area is unknown.")
        if self.access is None:
            problems.append("No access point. Arrival sequence and parking "
                            "cannot be planned.")
        if not self.views and not self.noise:
            problems.append(
                "No views or noise sources recorded. Orientation would be "
                "decided on sun alone, ignoring half the inputs.")
        return problems


# ---------------------------------------------------------------------------
def _pt(v) -> Point:
    return (float(v[0]), float(v[1]))


def _bearings(items, kind) -> tuple[Bearing, ...]:
    return tuple(
        Bearing(b.get("id", f"{kind}-{i+1}"), float(b["bearing"]),
                b.get("quality", ""), b.get("source", ""),
                b.get("severity", ""), b.get("note", ""))
        for i, b in enumerate(items or [])
    )


def load(path: str | Path) -> Site:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    loc = data.get("location", {})
    st = data.get("statutory", {})

    s = Site(
        name=data.get("name", "Untitled site"),
        location=Location(
            latitude=float(loc["latitude"]),
            longitude=float(loc["longitude"]),
            city=loc.get("city", ""),
            utc_offset_hours=float(loc.get("utc_offset_hours", 0)),
        ),
        north_angle=float(data.get("north_angle", 0)),
        boundary=tuple(_pt(p) for p in data.get("boundary", [])),
        statutory=Statutory(
            setback_front=float(st.get("setback_front", 0)),
            setback_rear=float(st.get("setback_rear", 0)),
            setback_side=float(st.get("setback_side", 0)),
            height_limit=float(st.get("height_limit", 0)),
            max_storeys=int(st.get("max_storeys", 0)),
            plot_ratio=float(st.get("plot_ratio", 0)),
            site_coverage=float(st.get("site_coverage", 0)),
        ),
        access=_pt(data["access"]) if data.get("access") else None,
        neighbours=tuple(
            Neighbour(n.get("id", f"N-{i+1}"),
                      tuple(_pt(p) for p in n.get("boundary", [])),
                      float(n.get("height", 0)))
            for i, n in enumerate(data.get("neighbours", []) or [])
        ),
        views=_bearings(data.get("views"), "V"),
        noise=_bearings(data.get("noise"), "NS"),
        wind=_bearings(data.get("wind"), "W"),
        spot_levels=tuple(
            (_pt(p["at"]), float(p["z"])) for p in data.get("spot_levels", []) or []
        ),
    )
    s.validate()
    return s
