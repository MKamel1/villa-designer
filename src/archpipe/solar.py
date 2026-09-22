"""Solar position — the arithmetic behind every orientation rule.

Implements the NOAA solar position algorithm. No library and no service:
given latitude, longitude and a moment, the sun's altitude and azimuth
are closed-form trigonometry.

This module is deliberately small and heavily verified, because a wrong
azimuth does not announce itself -- it silently corrupts every rule about
orientation, glazing, shading and overshadowing downstream. See
`verify()` and the tests, which check against published reference values
rather than against this module's own output.

Conventions:
    azimuth   degrees clockwise from true north (0 = N, 90 = E, 180 = S)
    altitude  degrees above the horizon; negative means below
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class SunPosition:
    altitude: float      # degrees above horizon
    azimuth: float       # degrees clockwise from north
    declination: float   # degrees
    eot_minutes: float   # equation of time

    @property
    def is_up(self) -> bool:
        return self.altitude > 0


def _julian_day(dt: datetime) -> float:
    """Julian Day from a UTC datetime."""
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1))
            + d + b - 1524.5)


def sun_position(when: datetime, lat: float, lon: float) -> SunPosition:
    """Sun position for a UTC datetime at (lat, lon) in degrees.

    `lon` is positive east of Greenwich.
    """
    jd = _julian_day(when)
    t = (jd - 2451545.0) / 36525.0                     # Julian century

    # Geometric mean longitude and anomaly of the sun
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)

    mr = math.radians(m)
    c = (math.sin(mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
         + math.sin(2 * mr) * (0.019993 - 0.000101 * t)
         + math.sin(3 * mr) * 0.000289)

    true_long = l0 + c
    omega = 125.04 - 1934.136 * t
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    # Obliquity of the ecliptic, with the nutation correction
    eps0 = 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))

    decl = math.degrees(math.asin(
        math.sin(math.radians(eps)) * math.sin(math.radians(app_long))
    ))

    # Equation of time, in minutes
    y = math.tan(math.radians(eps / 2)) ** 2
    l0r = math.radians(l0)
    eot = 4 * math.degrees(
        y * math.sin(2 * l0r)
        - 2 * e * math.sin(mr)
        + 4 * e * y * math.sin(mr) * math.cos(2 * l0r)
        - 0.5 * y * y * math.sin(4 * l0r)
        - 1.25 * e * e * math.sin(2 * mr)
    )

    # True solar time -> hour angle. `when` is UTC, so no timezone term.
    minutes_utc = when.hour * 60 + when.minute + when.second / 60
    true_solar_minutes = (minutes_utc + eot + 4 * lon) % 1440
    hour_angle = true_solar_minutes / 4 - 180.0

    latr, declr, har = map(math.radians, (lat, decl, hour_angle))
    cos_zenith = (math.sin(latr) * math.sin(declr)
                  + math.cos(latr) * math.cos(declr) * math.cos(har))
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.degrees(math.acos(cos_zenith))
    altitude = 90.0 - zenith

    # Azimuth, clockwise from true north, exactly as the NOAA spreadsheet
    # branches it: the two cases meet continuously at solar noon.
    denom = math.cos(latr) * math.sin(math.radians(zenith))
    if abs(denom) < 1e-9:                     # sun at the zenith or the pole
        azimuth = 180.0
    else:
        cos_az = (math.sin(latr) * cos_zenith - math.sin(declr)) / denom
        cos_az = max(-1.0, min(1.0, cos_az))
        core = math.degrees(math.acos(cos_az))
        azimuth = (core + 180.0) % 360.0 if hour_angle > 0 else (540.0 - core) % 360.0

    return SunPosition(altitude, azimuth, decl, eot)


# Standard altitude at which sunrise/sunset is defined: the sun's upper
# limb touching the horizon, allowing for mean atmospheric refraction.
# Without it, computed times sit 5-8 minutes inside published almanac
# times -- which is exactly the discrepancy used to validate this module.
SUNRISE_ALTITUDE = -0.833


def sun_events(day: date, lat: float, lon: float,
               altitude: float = SUNRISE_ALTITUDE) -> dict:
    """Sunrise and sunset (UTC) for a day, by bisection on altitude.

    Returns {"sunrise": dt|None, "sunset": dt|None, "daylight_hours": float}.
    Either may be None inside a polar day or night, which is a real
    condition, not an error.
    """
    start = datetime(day.year, day.month, day.day)

    def alt(t: datetime) -> float:
        return sun_position(t, lat, lon).altitude - altitude

    events: dict = {"sunrise": None, "sunset": None}
    prev_t, prev = start, alt(start)
    for i in range(1, 24 * 60 + 1):
        t = start + timedelta(minutes=i)
        cur = alt(t)
        if (prev < 0) != (cur < 0):
            lo, hi = prev_t, t
            for _ in range(40):
                mid = lo + (hi - lo) / 2
                if (alt(lo) < 0) != (alt(mid) < 0):
                    hi = mid
                else:
                    lo = mid
            events["sunrise" if cur > 0 else "sunset"] = lo
        prev_t, prev = t, cur

    rise, set_ = events["sunrise"], events["sunset"]
    events["daylight_hours"] = (
        (set_ - rise).total_seconds() / 3600 if rise and set_ else
        (24.0 if prev > 0 else 0.0)
    )
    return events


def solar_noon(day: date, lat: float, lon: float) -> datetime:
    """UTC datetime of solar noon, iterated to convergence."""
    guess = datetime(day.year, day.month, day.day, 12, 0)
    for _ in range(3):
        eot = sun_position(guess, lat, lon).eot_minutes
        minutes = 720 - 4 * lon - eot
        guess = datetime(day.year, day.month, day.day) + timedelta(minutes=minutes)
    return guess


def day_arc(day: date, lat: float, lon: float, step_minutes: int = 30
            ) -> list[tuple[datetime, SunPosition]]:
    """Sun positions across one day, for a sun-path diagram."""
    start = datetime(day.year, day.month, day.day)
    out = []
    for i in range(0, 24 * 60, step_minutes):
        t = start + timedelta(minutes=i)
        out.append((t, sun_position(t, lat, lon)))
    return out


# Key dates for orientation analysis. Approximate by design: the solstice
# and equinox shift by a day between years, which does not matter for
# deciding which way a living room faces.
KEY_DATES = {
    "summer_solstice": (6, 21),
    "winter_solstice": (12, 21),
    "equinox_march": (3, 20),
    "equinox_september": (9, 22),
}


def verify() -> dict:
    """Check this module against physics and against published times.

    Kept in the module, not only in tests, because a wrong azimuth does
    not announce itself: it silently corrupts every orientation rule
    downstream. Run it after any change here.

    Checks, in order of what they would catch:
      1. Solar-noon azimuth is due south in the northern hemisphere and
         due north in the southern -- catches sign and convention errors.
      2. Equinox noon altitude equals 90 - |latitude| -- catches
         declination and hour-angle errors.
      3. Solstice noon altitude at the matching tropic is 90 -- catches
         obliquity errors.
      4. Sunrise/sunset for London match published almanac times within
         two minutes once refraction is applied.
    """
    results: list[dict] = []

    def check(name, got, want, tol, unit=""):
        ok = abs(got - want) <= tol
        results.append({"check": name, "got": round(got, 4), "want": want,
                        "tol": tol, "unit": unit, "ok": ok})

    # 1 + 2: equinox noon, both hemispheres
    for lat in (52.0, 40.0, 30.0):
        p = sun_position(solar_noon(date(2026, 3, 20), lat, 0.0), lat, 0.0)
        check(f"noon azimuth due south at {lat}N", p.azimuth, 180.0, 0.05, "deg")
        check(f"equinox noon altitude at {lat}N", p.altitude, 90.0 - lat, 0.1, "deg")
    for lat in (-33.9, -23.0):
        p = sun_position(solar_noon(date(2026, 3, 20), lat, 0.0), lat, 0.0)
        az = min(p.azimuth, 360.0 - p.azimuth)      # distance from due north
        check(f"noon azimuth due north at {abs(lat)}S", az, 0.0, 0.05, "deg")

    # 3: solstice at the tropics
    p = sun_position(solar_noon(date(2026, 6, 21), 23.4397, 0.0), 23.4397, 0.0)
    check("summer solstice noon altitude at Tropic of Cancer",
          p.altitude, 90.0, 0.05, "deg")
    p = sun_position(solar_noon(date(2026, 12, 21), -23.4397, 0.0), -23.4397, 0.0)
    check("winter solstice noon altitude at Tropic of Capricorn",
          p.altitude, 90.0, 0.05, "deg")

    # 4: published almanac times for London (UTC), with refraction applied
    LON_LAT, LON_LON = 51.5074, -0.1278
    for day, rise_utc, set_utc in (
        (date(2026, 6, 21), 3 + 44 / 60, 20 + 22 / 60),   # 04:44 / 21:22 BST
        (date(2026, 12, 21), 8 + 5 / 60, 15 + 54 / 60),   # 08:05 / 15:54 GMT
    ):
        ev = sun_events(day, LON_LAT, LON_LON)
        for key, want in (("sunrise", rise_utc), ("sunset", set_utc)):
            t = ev[key]
            got = t.hour + t.minute / 60 + t.second / 3600
            check(f"London {day} {key} (UTC)", got, want, 2 / 60, "h")

    return {"ok": all(r["ok"] for r in results), "checks": results}
