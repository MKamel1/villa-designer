"""Climate, cooling-load, overheating and daylight studies for window decisions.

Runs on the render workstation under the thermal environment
(requirements-thermal.txt: Ladybug Tools SDK) with EnergyPlus 25.2 from
OpenStudio 3.11.0 (ops/workstation/bootstrap.py --thermal). The laptop
submits jobs through scripts/workstation.py; nothing here runs in Revit.

A study is a single-zone "shoebox": one room with ONE exterior wall facing
a given azimuth, every other surface adiabatic (it adjoins conditioned
rooms). That isolates what the window decision controls: orientation,
window-to-wall ratio, shading depth and glass. It is a comparison tool.
It is not a whole-building energy model and not HVAC sizing. Room peak
loads go to the HVAC consultant as a starting point only.

EVERY ASSUMPTION IS A NAMED DEFAULT (ASSUMPTIONS below) and is echoed in
each result. Comfort thresholds are reported as diagnostic hour counts
until CIBSE TM59 / ASHRAE 55 are held and their criteria verified.
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

# Stated assumptions. A study may override any of them; the result records
# the values actually used. Sources for these defaults are NOT yet verified;
# they are typical design-stage inputs, labelled as such.
ASSUMPTIONS = {
    "room": {"width_m": 4.0, "depth_m": 5.0, "height_m": 3.0},
    "wall_u_w_m2k": 0.6,          # exterior wall target U-value
    "glass": {"u_w_m2k": 1.8, "shgc": 0.40, "vt": 0.60},  # double low-e, simple glazing system
    "people": 2, "people_w_each": 120,     # sensible+latent total per person (EnergyPlus activity)
    "lighting_w_m2": 4.0, "equipment_w_m2": 3.0,
    "infiltration_m3s_per_m2_facade": 0.0003,
    "cooling_setpoint_c": 24.0, "heating_setpoint_c": 20.0,
    "natural_ventilation": {"fraction_openable": 0.5, "min_indoor_c": 24.0, "max_outdoor_c": 28.0},
    "surface_films_m2k_w": 0.17,  # Rsi 0.13 + Rse 0.04 (ISO 6946 horizontal heat flow)
}
OUTPUTS = ("Zone Ideal Loads Supply Air Total Cooling Energy",
           "Zone Ideal Loads Supply Air Total Heating Energy",
           "Zone Operative Temperature",
           "Surface Window Transmitted Solar Radiation Energy",
           "Surface Outside Face Incident Solar Radiation Rate per Area",
           "Surface Outside Face Incident Beam Solar Radiation Rate per Area")


# ------------------------------------------------------------------ climate

def read_epw(path: Path) -> dict:
    """Plain parse of the fields the summaries use (independent of Ladybug)."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    loc = lines[0].split(",")
    rows = [l.split(",") for l in lines[8:] if l.count(",") > 30]
    return {"city": loc[1], "wmo": loc[5], "lat": float(loc[6]), "lon": float(loc[7]), "tz": float(loc[8]),
            "elev_m": float(loc[9]), "month": [int(r[1]) for r in rows], "hour": [int(r[3]) for r in rows],
            "db": [float(r[6]) for r in rows], "rh": [float(r[8]) for r in rows],
            "ghi": [float(r[13]) for r in rows], "dni": [float(r[14]) for r in rows],
            "dhi": [float(r[15]) for r in rows], "wdir": [float(r[20]) for r in rows],
            "wspd": [float(r[21]) for r in rows]}


def climate_summary(epw_path: Path) -> dict:
    """Monthly temperatures, degree-days, hot-hour counts, radiation, wind and noon sun."""
    w = read_epw(epw_path)
    n = len(w["db"])
    monthly = {}
    for m in range(1, 13):
        t = [x for x, mm in zip(w["db"], w["month"]) if mm == m]
        monthly[m] = {"mean_c": round(statistics.fmean(t), 1), "max_c": max(t), "min_c": min(t)}
    daily = [statistics.fmean(w["db"][i:i + 24]) for i in range(0, n, 24)]
    cdd18 = round(sum(max(0.0, d - 18.0) for d in daily))
    hdd18 = round(sum(max(0.0, 18.0 - d) for d in daily))
    sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def prevailing(months):
        c = {}
        for d, s, mm in zip(w["wdir"], w["wspd"], w["month"]):
            if mm in months and s > 0.5:
                k = sectors[int(((d + 22.5) % 360) // 45)]
                c[k] = c.get(k, 0) + 1
        tot = sum(c.values()) or 1
        return {k: round(v / tot, 2) for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:3]}

    noon = {}
    for label, doy in (("21 Jun", 172), ("21 Mar", 80), ("21 Dec", 355)):
        decl = 23.44 * math.sin(math.radians(360 / 365 * (doy - 81)))
        noon[label] = round(90 - abs(w["lat"] - decl), 1)
    return {
        "location": {k: w[k] for k in ("city", "wmo", "lat", "lon", "tz", "elev_m")},
        "monthly": monthly,
        "annual_mean_c": round(statistics.fmean(w["db"]), 1),
        "cooling_degree_days_18c": cdd18, "heating_degree_days_18c": hdd18,
        "hours_above_c": {str(k): sum(1 for x in w["db"] if x > k) for k in (26, 28, 32, 35)},
        "annual_ghi_kwh_m2": round(sum(w["ghi"]) / 1000),
        "prevailing_wind": {"summer (Jun-Aug)": prevailing({6, 7, 8}), "winter (Dec-Feb)": prevailing({12, 1, 2})},
        "noon_sun_altitude_deg": noon,
        "method": "Parsed from the EPW directly; degree-days from daily mean dry-bulb, base 18 C; "
                  "noon altitude from a cosine declination approximation (+/- 0.5 deg).",
    }


def stat_monthly_means(stat_path: Path) -> list[float] | None:
    """Monthly daily-average dry-bulb from the EnergyPlus weather converter's .stat file: an independent check."""
    in_section = False
    for line in Path(stat_path).read_text(encoding="latin-1").splitlines():
        if "Monthly Statistics for Dry Bulb temperatures" in line:
            in_section = True
            continue
        cells = [c.strip() for c in line.split("	")]
        if in_section and "Daily Avg" in cells:
            i = cells.index("Daily Avg")
            return [float(c) for c in cells[i + 1:i + 13]]
    return None


def hand_vertical_incident(epw_path: Path, azimuth_deg: float, albedo: float = 0.2) -> dict:
    """Annual solar radiation on a vertical surface, kWh/m2, by hand: NOAA sun
    position (archpipe.solar, checked against almanac values) + the EPW's
    direct-normal and diffuse-horizontal radiation.

    'beam' is model-free geometry and must match EnergyPlus closely. 'sky' and
    'ground' use an isotropic sky and ground; EnergyPlus uses the anisotropic
    Perez sky (measured 2026-09-24 on Cairo West: north sky diffuse 17 % lower,
    south 34 % higher than isotropic, beam within 0.7 %), so those two are
    reported, not asserted."""
    from datetime import datetime, timedelta
    from archpipe.solar import sun_position
    w = read_epw(epw_path)
    az = math.radians(azimuth_deg)
    beam = sky = ground = 0.0
    start = datetime(2017, 1, 1)
    for i, (dni, dhi, ghi) in enumerate(zip(w["dni"], w["dhi"], w["ghi"])):
        # EPW hour h covers (h-1, h] local standard time; use the mid-point, as UTC
        s = sun_position(start + timedelta(hours=i + 0.5 - w["tz"]), w["lat"], w["lon"])
        if s.altitude > 0:
            cos_inc = math.cos(math.radians(s.altitude)) * math.cos(math.radians(s.azimuth) - az)
            beam += dni * max(0.0, cos_inc)
        sky += dhi * 0.5
        ground += ghi * albedo * 0.5
    return {"beam": beam / 1000.0, "sky": sky / 1000.0, "ground": ground / 1000.0,
            "total": (beam + sky + ground) / 1000.0}


# ------------------------------------------------------------------ shoebox

def _merged(case: dict) -> dict:
    a = json.loads(json.dumps(ASSUMPTIONS))
    for k, v in case.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            a[k].update(v)
        else:
            a[k] = v
    return a


def shoebox(case: dict):
    """(honeybee Model, SimulationParameter, assumptions) for one room case.

    case: azimuth_deg (facade normal, 0 = north, clockwise), wwr (0-0.95),
    overhang_m (horizontal projection at the window head), mode 'cooled' or
    'free' (free-running with openable windows), plus any ASSUMPTIONS key.
    """
    from ladybug_geometry.geometry3d import Face3D, Point3D, Vector3D
    from honeybee.boundarycondition import boundary_conditions as bcs
    from honeybee.model import Model
    from honeybee.room import Room
    from honeybee.shade import Shade
    from honeybee_energy.construction.opaque import OpaqueConstruction
    from honeybee_energy.construction.window import WindowConstruction
    from honeybee_energy.hvac.idealair import IdealAirSystem
    from honeybee_energy.lib.schedules import schedule_by_identifier
    from honeybee_energy.load.equipment import ElectricEquipment
    from honeybee_energy.load.infiltration import Infiltration
    from honeybee_energy.load.lighting import Lighting
    from honeybee_energy.load.people import People
    from honeybee_energy.load.setpoint import Setpoint
    from honeybee_energy.material.glazing import EnergyWindowMaterialSimpleGlazSys
    from honeybee_energy.material.opaque import EnergyMaterial, EnergyMaterialNoMass
    from honeybee_energy.lib.scheduletypelimits import schedule_type_limit_by_identifier as stl
    from honeybee_energy.schedule.ruleset import ScheduleRuleset
    from honeybee_energy.simulation.parameter import SimulationParameter
    from honeybee_energy.ventcool.control import VentilationControl
    from honeybee_energy.ventcool.opening import VentilationOpening

    a = _merged(case)
    az = float(case.get("azimuth_deg", 180.0)) % 360
    wwr = float(case.get("wwr", 0.3))
    if not 0.0 < wwr <= 0.95:
        raise ValueError("wwr must be in (0, 0.95]")
    r = a["room"]
    room = Room.from_box("room", r["width_m"], r["depth_m"], r["height_m"])
    # The box's south-facing wall (normal -Y) is the facade; rotate the room so
    # that normal points at the requested azimuth. Clockwise-from-north azimuth
    # a has normal (sin a, cos a); from_box's -Y wall has azimuth 180.
    room.rotate_xy(180.0 - az, Point3D(0, 0, 0))
    target = Vector3D(math.sin(math.radians(az)), math.cos(math.radians(az)), 0)
    walls = [f for f in room.faces if abs(f.normal.z) < 0.5]
    facade = max(walls, key=lambda f: f.normal.dot(target))
    for f in room.faces:
        if f is not facade:
            f.boundary_condition = bcs.adiabatic
    facade.apertures_by_ratio(wwr)

    # constructions: layered mass wall with an insulation layer sized to the target U
    plaster = EnergyMaterial("plaster", 0.02, 0.70, 1600, 840)
    block = EnergyMaterial("concrete block", 0.20, 1.10, 1800, 840)
    r_ins = 1.0 / a["wall_u_w_m2k"] - a["surface_films_m2k_w"] - 0.02 / 0.70 * 2 - 0.20 / 1.10
    if r_ins <= 0:
        raise ValueError("wall U too high for the fixed mass layers")
    ins = EnergyMaterialNoMass("insulation", r_ins)
    wall = OpaqueConstruction("ext wall", [plaster, block, ins, plaster])
    facade.properties.energy.construction = wall
    g = a["glass"]
    glass = WindowConstruction("glass", [EnergyWindowMaterialSimpleGlazSys("sgs", g["u_w_m2k"], g["shgc"], g["vt"])])
    for ap in facade.apertures:
        ap.properties.energy.construction = glass

    over = float(case.get("overhang_m", 0.0))
    if over > 0:
        for ap in facade.apertures:
            pts = ap.geometry.vertices
            ztop = max(p.z for p in pts)
            top = sorted([p for p in pts if abs(p.z - ztop) < 1e-6], key=lambda p: (p.x, p.y))
            n = facade.normal * over
            p1, p2 = top[0], top[-1]
            ap.add_outdoor_shade(Shade(f"overhang_{ap.identifier}", Face3D(
                [p1, p2, p2.move(n), p1.move(n)])))

    fin = float(case.get("fin_m", 0.0))
    if fin > 0:   # vertical fins at both jambs, full window height (low east/west sun)
        for ap in facade.apertures:
            pts = ap.geometry.vertices
            zmin, zmax = min(q.z for q in pts), max(q.z for q in pts)
            along = facade.normal.cross(Vector3D(0, 0, 1)).normalize()
            ends = sorted(pts, key=lambda q: q.x * along.x + q.y * along.y)
            n = facade.normal * fin
            for i, e in enumerate((ends[0], ends[-1])):
                b, tp = Point3D(e.x, e.y, zmin), Point3D(e.x, e.y, zmax)
                ap.add_outdoor_shade(Shade(f"fin{i}_{ap.identifier}", Face3D([b, tp, tp.move(n), b.move(n)])))

    area = r["width_m"] * r["depth_m"]
    always = schedule_by_identifier("Always On")
    night = ScheduleRuleset.from_daily_values("bedroom occupancy",
                                              [1.0] * 7 + [0.2] * 15 + [1.0] * 2, schedule_type_limit=stl("Fractional"))
    evening = ScheduleRuleset.from_daily_values("evening lights", [0.0] * 18 + [1.0] * 5 + [0.0], schedule_type_limit=stl("Fractional"))
    act = ScheduleRuleset.from_constant_value("activity", a["people_w_each"], stl("Activity Level"))
    e = room.properties.energy
    e.people = People("people", a["people"] / area, night, act)
    e.lighting = Lighting("lighting", a["lighting_w_m2"], evening)
    e.electric_equipment = ElectricEquipment("equipment", a["equipment_w_m2"], always)
    e.infiltration = Infiltration("infiltration", a["infiltration_m3s_per_m2_facade"], always)
    mode = case.get("mode", "cooled")
    if mode == "cooled":
        cool = ScheduleRuleset.from_constant_value("cool", a["cooling_setpoint_c"], stl("Temperature"))
        heat = ScheduleRuleset.from_constant_value("heat", a["heating_setpoint_c"], stl("Temperature"))
        e.setpoint = Setpoint("setpoint", heat, cool)
        e.hvac = IdealAirSystem("ideal", economizer_type="NoEconomizer")
    elif mode == "free":
        nv = a["natural_ventilation"]
        for ap in facade.apertures:
            ap.is_operable = True
            ap.properties.energy.vent_opening = VentilationOpening(fraction_area_operable=nv["fraction_openable"])
        e.window_vent_control = VentilationControl(min_indoor_temperature=nv["min_indoor_c"],
                                                   max_outdoor_temperature=nv["max_outdoor_c"])
    else:
        raise ValueError("mode must be 'cooled' or 'free'")

    model = Model("shoebox", [room], units="Meters", tolerance=0.001, angle_tolerance=1.0)
    sim = SimulationParameter()
    sim.output.reporting_frequency = "Hourly"
    for o in OUTPUTS:
        sim.output.add_output(o)
    used = {k: a[k] for k in ASSUMPTIONS}
    used.update({"azimuth_deg": az, "wwr": wwr, "overhang_m": over, "fin_m": fin, "mode": mode,
                 "window_area_m2": round(sum(ap.area for ap in facade.apertures), 3),
                 "floor_area_m2": area, "wall_r_insulation_m2k_w": round(r_ins, 3)})
    return model, sim, used


def _quiet(log: Path, fn, *args, **kw):
    """Run fn with the process's stdout/stderr (inherited by EnergyPlus) sent to a log file,
    so a worker's structured JSON output stays clean."""
    import os
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    saved = os.dup(1), os.dup(2)
    with open(log, "ab") as f:
        os.dup2(f.fileno(), 1)
        os.dup2(f.fileno(), 2)
        try:
            return fn(*args, **kw)
        finally:
            os.dup2(saved[0], 1)
            os.dup2(saved[1], 2)
            os.close(saved[0])
            os.close(saved[1])


def run_case(case: dict, epw: Path, energyplus: Path, workdir: Path) -> dict:
    """Simulate one case for a full weather year and return its figures."""
    from honeybee_energy.config import folders
    from honeybee_energy.run import run_idf
    from ladybug.sql import SQLiteResult
    folders.energyplus_path = str(Path(energyplus).parent)
    model, sim, used = shoebox(case)
    ddy = Path(epw).with_suffix(".ddy")
    if ddy.is_file():   # ASHRAE 0.4 % cooling / 99.6 % heating design days from the weather file
        sim.sizing_parameter.add_from_ddy_996_004(str(ddy))
    else:
        sim.simulation_control.do_zone_sizing = False
        sim.simulation_control.do_system_sizing = False
        sim.simulation_control.do_plant_sizing = False
    workdir.mkdir(parents=True, exist_ok=True)
    idf = workdir / "in.idf"
    idf.write_text(sim.to_idf() + "\n\n" + model.to.idf(model), encoding="utf-8")
    sql, _, _, _, err = _quiet(workdir / "energyplus.log", run_idf, str(idf), str(epw), silent=True)
    log = Path(err).read_text(errors="replace") if err and Path(err).is_file() else ""
    # A fatal run still leaves an (empty) SQLite file: judge by the error log, never by the file.
    if not sql or not Path(sql).is_file() or "** Fatal **" in log.replace("  ", " ") or "Fatal error" in log:
        severe = [l.strip() for l in log.splitlines() if "Severe" in l or "Fatal" in l]
        raise RuntimeError("EnergyPlus failed: " + " | ".join(severe[:6]))
    res = SQLiteResult(sql)
    area = used["floor_area_m2"]

    # Ladybug converts EnergyPlus joules to kWh and W/m2 stays W/m2 (hourly steps);
    # the unit is asserted rather than assumed.
    def total_kwh(name):
        cols = res.data_collections_by_output_name(name)
        for c in cols:
            assert str(c.header.unit) == "kWh", (name, c.header.unit)
        return sum(sum(c.values) for c in cols)

    def hourly(name):
        cols = res.data_collections_by_output_name(name)
        return list(cols[0].values) if cols else []

    out = {"case": used}
    if used["mode"] == "cooled":
        cool = hourly("Zone Ideal Loads Supply Air Total Cooling Energy")
        out.update({
            "cooling_kwh_m2": round(total_kwh("Zone Ideal Loads Supply Air Total Cooling Energy") / area, 1),
            "heating_kwh_m2": round(total_kwh("Zone Ideal Loads Supply Air Total Heating Energy") / area, 1),
            "peak_cooling_w_m2": round(max(cool) * 1000.0 / area, 1) if cool else 0.0,  # kWh per hour -> W
        })
    top = hourly("Zone Operative Temperature")
    if top:
        out["operative_hours_above_c"] = {str(k): sum(1 for t in top if t > k) for k in (26, 28, 30)}
        out["max_operative_c"] = round(max(top), 1)
        if len(top) == 8760:
            # TM59 criteria on this shoebox. Our occupancy, gains and window-opening assumptions are
            # not TM59's prescribed profiles, so this is a TM59-criteria screen, not a TM59 assessment.
            out["tm59"] = tm59(top, read_epw(Path(epw))["db"], case.get("use", "bedroom"),
                               "mechanical" if used["mode"] == "cooled" else "natural")
            out["tm59"]["basis"] = "TM59:2026 criteria on archpipe shoebox assumptions (screen, not an assessment)"
    out["window_transmitted_solar_kwh"] = round(total_kwh("Surface Window Transmitted Solar Radiation Energy"), 1)
    inc = res.data_collections_by_output_name("Surface Outside Face Incident Solar Radiation Rate per Area")
    # apertures are named <wall>_Glz<n>; the opaque facade wall is the other exterior surface
    fac = [c for c in inc if "_GLZ" not in c.header.metadata.get("Surface", "").upper()]
    out["facade_incident_kwh_m2"] = round(max((sum(c.values) for c in fac), default=0.0) / 1000.0, 1)
    beam = [c for c in res.data_collections_by_output_name(
        "Surface Outside Face Incident Beam Solar Radiation Rate per Area")
        if "_GLZ" not in c.header.metadata.get("Surface", "").upper()]
    out["facade_beam_kwh_m2"] = round(max((sum(c.values) for c in beam), default=0.0) / 1000.0, 1)
    return out


# ------------------------------------------------------------------ TM59 (2026)
# CIBSE TM59:2026 section 2.4 and Table 2 (printed pages 9-11; cards tm59-*). Category II
# (ordinary dwellings). The running-mean outdoor temperature follows TM52 Eq. 2.2/2.3 as
# published in EN 16798-1 (alpha 0.8; TM52 itself is not held): cross-checked against
# Ladybug's independent implementation in tests/test_thermal.py.
TM59 = {"cat2_threshold_at_trm10": 25.1, "cat2_threshold_at_trm30": 31.7, "exceed_fraction": 0.03,
        "crit_b_tn_cat2": 27.0, "crit_b_max_nights": 4, "crit_c_c": 26.0,
        "living_hours": range(9, 22), "sleep": (23, 8)}
MAY1, OCT1 = 120, 273          # day-of-year index (0-based) of 1 May and 1 October, non-leap year


def running_mean_daily(daily_means: list[float], alpha: float = 0.8) -> list[float]:
    """Trm for every day: TM52 Eq. 2.3 seeds day 7 from the previous seven days, Eq. 2.2 recurses."""
    w = (1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2)
    trm = [None] * len(daily_means)
    trm[7] = sum(wi * daily_means[7 - 1 - i] for i, wi in enumerate(w)) / 3.8
    for d in range(8, len(daily_means)):
        trm[d] = (1 - alpha) * daily_means[d - 1] + alpha * trm[d - 1]
    return trm


def cat2_threshold(trm: float) -> float:
    lo, hi = TM59["cat2_threshold_at_trm10"], TM59["cat2_threshold_at_trm30"]
    t = min(max(trm, 10.0), 30.0)
    return lo + (hi - lo) * (t - 10.0) / 20.0


def tm59(operative: list[float], outdoor_db: list[float], use: str, ventilation: str) -> dict:
    """TM59 criteria for one room from 8760 hourly operative temperatures.

    use: "living" (living room, kitchen, home office) or "bedroom".
    ventilation: "natural" (criteria a and b) or "mechanical" (criteria c and b)."""
    assert len(operative) == len(outdoor_db) == 8760, "a full non-leap hourly year is required"
    days = [statistics.fmean(outdoor_db[24 * d:24 * d + 24]) for d in range(365)]
    trm = running_mean_daily(days)
    hours = [h for h in range(MAY1 * 24, OCT1 * 24)
             if use == "bedroom" or (h % 24) in TM59["living_hours"]]
    limit = math.floor(TM59["exceed_fraction"] * len(hours))
    out = {"use": use, "ventilation": ventilation, "occupied_hours": len(hours), "limit_hours": limit}
    if ventilation == "natural":
        # dT rounded to the nearest whole degree (TM52): dT >= 0.5 counts as 1 K
        n = sum(1 for h in hours if operative[h] - cat2_threshold(trm[h // 24]) >= 0.5)
        out["a"] = {"hours": n, "pass": n <= limit}
    else:
        n = sum(1 for h in hours if operative[h] > TM59["crit_c_c"])
        out["c"] = {"hours": n, "pass": n <= limit}
    if use == "bedroom":
        s, e = TM59["sleep"]
        nights = 0
        for d in range(MAY1, OCT1):
            span = list(range(24 * d + s, 24 * (d + 1) + e))
            span = [h for h in span if h < 8760]
            if statistics.fmean(operative[h] for h in span) > TM59["crit_b_tn_cat2"]:
                nights += 1
        out["b"] = {"nights": nights, "pass": nights <= TM59["crit_b_max_nights"]}
    out["pass"] = all(v["pass"] for k, v in out.items() if k in ("a", "b", "c"))
    return out


def window_study(base: dict, sweep: dict, epw: Path, energyplus: Path, workdir: Path) -> list[dict]:
    """Every combination of the sweep values, each simulated under identical assumptions."""
    import itertools
    keys = list(sweep)
    results = []
    for i, values in enumerate(itertools.product(*(sweep[k] for k in keys))):
        case = dict(base, **dict(zip(keys, values)))
        results.append(run_case(case, epw, energyplus, workdir / f"case{i:03d}"))
    return results


# ------------------------------------------------------------------ daylight

# Stated reflectances for the daylight model (typical design-stage values, not yet
# sourced to a card): walls 0.5, ceiling 0.8, floor 0.2, shading 0.35, ground 0.2.
DAYLIGHT_REFLECTANCE = {"wall": 0.5, "ceiling": 0.8, "floor": 0.2, "shade": 0.35, "ground": 0.2}
WORKPLANE_M = 0.85
# gensky -c -B 55.866 sets the overcast sky's horizontal diffuse irradiance to 55.866 W/m2,
# which is 10 000 lux at 179 lm/W, so daylight factor % = illuminance / 100.
SKY_B = 55.866


def daylight_factor(case: dict, radiance: Path, workdir: Path, grid_m: float = 0.5) -> dict:
    """Daylight factor on the work plane under the CIE overcast sky (Radiance rtrace).

    Also returns the simplified Lynes average daylight factor (Baker & Steemers p. 65),
    DF = W.theta.T.M / (A (1 - R)), theta = vertical angle of visible sky from the window
    centre in degrees (90 unobstructed), T = glass visible transmittance, M = 1 (clean)."""
    import os
    import subprocess
    from honeybee_radiance.modifier.material import Glass, Plastic
    from honeybee_radiance.writer import model_to_rad
    model, _, used = shoebox(case)
    room = model.rooms[0]
    ref = DAYLIGHT_REFLECTANCE
    mods = {"Wall": Plastic.from_single_reflectance("wall_m", ref["wall"]),
            "RoofCeiling": Plastic.from_single_reflectance("ceiling_m", ref["ceiling"]),
            "Floor": Plastic.from_single_reflectance("floor_m", ref["floor"])}
    glass = Glass.from_single_transmittance("glass_m", used["glass"]["vt"])
    shade = Plastic.from_single_reflectance("shade_m", ref["shade"])
    for f in room.faces:
        f.properties.radiance.modifier = mods[str(f.type)]
        for ap in f.apertures:
            ap.properties.radiance.modifier = glass
            for s in ap.outdoor_shades:
                s.properties.radiance.modifier = shade
    grid = room.properties.radiance.generate_sensor_grid(grid_m, offset=WORKPLANE_M)
    workdir.mkdir(parents=True, exist_ok=True)
    scene, mat = model_to_rad(model)
    sky = subprocess.run([str(radiance / "bin/gensky"), "-ang", "45", "0", "-c", "-B", str(SKY_B)],
                         capture_output=True, text=True, check=True).stdout
    g = ref["ground"]
    sky += ("\nskyfunc glow sky_glow 0 0 4 1 1 1 0\nsky_glow source sky 0 0 4 0 0 1 180\n"
            f"skyfunc glow ground_glow 0 0 4 {g} {g} {g} 0\nground_glow source ground 0 0 4 0 0 -1 180\n")
    (workdir / "scene.rad").write_text(sky + "\n" + mat + "\n" + scene)
    env = dict(os.environ, RAYPATH=f".:{radiance / 'lib'}")
    oct_ = workdir / "scene.oct"
    with oct_.open("wb") as o:
        subprocess.run([str(radiance / "bin/oconv"), str(workdir / "scene.rad")], stdout=o, check=True, env=env)
    pts_txt = "".join(f"{s.pos[0]} {s.pos[1]} {s.pos[2]} {s.dir[0]} {s.dir[1]} {s.dir[2]}\n" for s in grid.sensors)
    pts_txt += "0 0 100 0 0 1\n"     # far above the roof, facing up: must see the whole sky (DF 100 %)
    rt = subprocess.run([str(radiance / "bin/rtrace"), "-I", "-h", "-ab", "6", "-ad", "4096", "-as", "1024",
                         "-ar", "512", "-aa", "0.1", "-lw", "2e-4", str(oct_)],
                        input=pts_txt, capture_output=True, text=True, check=True, env=env).stdout
    vals = [179 * (0.265 * float(a) + 0.670 * float(b) + 0.065 * float(c))
            for a, b, c in (line.split()[:3] for line in rt.strip().splitlines())]
    df = [v / 100.0 for v in vals[:-1]]
    faces = room.faces
    a_total = sum(f.area for f in faces)
    w = sum(ap.area for f in faces for ap in f.apertures)
    refl = {"Wall": ref["wall"], "RoofCeiling": ref["ceiling"], "Floor": ref["floor"]}
    r_avg = sum(f.area * refl[str(f.type)] for f in faces) / a_total
    lynes = w * 90.0 * used["glass"]["vt"] / (a_total * (1 - r_avg))
    s = sorted(df)
    return {"case": used, "df_avg": round(statistics.fmean(df), 2), "df_median": round(s[len(s) // 2], 2),
            "df_min": round(s[0], 2), "points": len(df), "sky_check_df": round(vals[-1] / 100.0, 1),
            "lynes_adf_unobstructed": round(lynes, 2), "reflectance": ref, "workplane_m": WORKPLANE_M}
