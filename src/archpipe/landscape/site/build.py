"""Build every LDS layer into knowledge/landscape/site/*.json (and the plan PNGs).

    PYTHONPATH=src python -m archpipe.landscape.site.build [--no-png]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

from ... import villa_env as E
from . import analyse as A, grid as G, model as M, raycast as RC

OUT = Path(__file__).resolve().parents[4] / "knowledge" / "landscape" / "site"
SCHEMA = "lds-site/1"

# ---- coverage of the held checklist: Time-Saver Standards for Landscape Architecture 2nd ed., section 220 pp.220-3/4/5
CHECKLIST_SOURCE = ("Harris & Dines, Time-Saver Standards for Landscape Architecture, 2nd ed. (1997), sec. 220 'Site analysis and "
                    "assessment', pp. 220-3 to 220-4 (the data 'typically collected and analyzed for the site'); 220-5 (Site Improvements)")
CHECKLIST = [
    ("climate zone characteristics", "partial", "wind.json (held TMYx, Cairo West AP) and sun.json; temperature/precipitation not analysed here (thermal lanes own them)"),
    ("geographical latitude and solar access", "covered", "sun.json: measured hours per 0.25 m cell on three dates + the two use windows"),
    ("wind patterns", "partial", "wind.json: station rose by season/time window; site microclimate and lee zones NOT modelled (GAP W1)"),
    ("topography", "covered", "inventory.json: levels, ramp profile, garden floor -3.0; no survey of falls inside the yard (GAP S3)"),
    ("soil characteristics", "gap", "no soil data held; needs a site test (outside the method, LANDSCAPE-METHOD limits)"),
    ("groundwater and surface runoff", "gap", "no drainage falls, gullies or water table in the model (GAP S2); needs survey"),
    ("vegetation (existing)", "gap", "no existing vegetation inventory: the plot is a new build; the current garden is a proposal and is excluded"),
    ("adjacent land uses", "covered", "privacy.json: neighbours east and rear (12 m, ASSUMED windows like ours), sister villa, apartment above, street"),
    ("circulation", "partial", "inventory.json: connected ground components and the openings onto each; the gate and entrance route into the garden are not modelled (GAP S4)"),
    ("utility infrastructure", "partial", "inventory.json services: only the two extract-fan discharges are in the model; no AC condensers, meters, bins, hose bibs, drains (GAP S1)"),
    ("views out and overlooking in", "covered", "views.json, privacy.json"),
    ("fixed structure", "covered", "inventory.json structure list (fences, yard wall, building, steps block, terrace slab, ramp/deck/roof, neighbours)"),
]
GAPS = [
    ("S1", "Services outside the building: AC condensers, electricity/water meters, bins, hose bibs, gullies/drains. The model holds none (only two extract-fan duct discharges under the east strip). Needs the client's/MEP drawings."),
    ("S2", "Surface drainage: falls, gullies, soakaway and water table are not in the model; the yard floor is a flat slab at -3.0."),
    ("S3", "Ground levels inside the yard are flat by model; real falls, paving build-ups and any steps between garden areas are unknown."),
    ("S4", "The street gate, its route and the entrance-steps profile are not modelled: the street fence is solid and the shared steps are one solid block (z -1.2..0). Street/steps privacy results are therefore a bound, and the north garden's access from the street is unknown."),
    ("S5", "Neighbour buildings and their windows are ASSUMED (12 m, windows 'like ours', mirrored plots; villa_env ASSUMPTIONS, client-confirmed as assumptions, not surveyed). So are the apartment's windows (GF repeated +3 m) and the sister's openings (mirror)."),
    ("S6", "Site latitude/longitude: sun layers use villa_env (client maps link, resolved 2026-09-25) - plot-level but not surveyed. spec/villa-site.yaml holds city-level PLACEHOLDER values; sensitivity is reported in sun.json."),
    ("S7", "Egypt's summer clock (DST, UTC+3) is not in any held source here. 'Summer evening 17:00-20:00' is given on the project's standard time AND as the same clock hours read on a DST clock; the client should say which they mean."),
    ("W1", "Wind: only the TMYx station record (Cairo West AP, nearest station, ADR-0017). No on-site measurement, no urban/lee modelling, no CFD. Time-Saver 220-12 gives qualitative shelterbelt rules (lee zone 4-6 H) only."),
    ("C1", "The held 'Site Analysis' book, 'A Pattern Language' and BR 209 are not reachable on this workstation (the knowledge index is empty and no copy is on disk). The checklist is mapped to Time-Saver sec. 220 instead; the book's own checklist pages are NOT cited. Re-run the mapping where the index exists."),
    ("C2", "Plants, pergola, pots, furniture and the current garden's beds/paths are excluded from every layer (they are the thing being designed). Canopy shade from existing planting does not exist yet."),
]


def _hdr(name, extra=None):
    return dict(schema=SCHEMA, layer=name, grid=G.HEADER, generated_by="archpipe.landscape.site.build", **(extra or {}))


def _write(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (name + ".json")).write_text(json.dumps(obj, separators=(",", ":")) + "\n", encoding="utf-8")


def _stats(a, mask):
    v = a[mask & ~np.isnan(a)]
    return dict(cells=int(len(v)), mean=round(float(v.mean()), 2), min=float(v.min()), max=float(v.max()),
                pct_cells_zero=round(100 * float((v == 0).mean()), 1)) if len(v) else None


def components(cls):
    """4-connected components of open ground (class ground / covered) -> list of (cells, zones)."""
    from collections import deque
    ground = np.isin(cls, (1, 2))
    seen = np.zeros_like(ground)
    zi = M.zone_of_cells()
    names = list(M.ZONES)
    out = []
    for j in range(G.NY):
        for i in range(G.NX):
            if ground[j, i] and not seen[j, i]:
                q = deque([(j, i)]); seen[j, i] = True; cells = []
                while q:
                    a, b = q.popleft(); cells.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        c, d = a + da, b + db
                        if 0 <= c < G.NY and 0 <= d < G.NX and ground[c, d] and not seen[c, d]:
                            seen[c, d] = True; q.append((c, d))
                out.append(dict(area_m2=round(len(cells) * G.CELL ** 2, 2), zones=sorted({names[zi[a, b]] for a, b in cells})))
    return sorted(out, key=lambda c: -c["area_m2"])


def inventory(cls, zs):
    zi = M.zone_of_cells()
    ops = M.our_openings()
    zones = {}
    for k, (name, (x0, y0, x1, y1, note)) in enumerate(M.ZONES.items()):
        m = zi == k
        zones[name] = dict(
            rect_m=[round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)], note=note,
            polygon_area_m2=round((x1 - x0) * (y1 - y0), 2),
            cell_area_by_class_m2={M.CLASSES[c]: round(float((m & (cls == c)).sum()) * G.CELL ** 2, 2) for c in M.CLASSES if (m & (cls == c)).any()},
            surface_z_m=[round(float(np.nanmin(zs[m])), 3), round(float(np.nanmax(zs[m])), 3)] if np.isfinite(zs[m]).any() else None,
            openings=[dict(id=o["id"], room=o["room"], level=o["level"], kind=o["kind"], width_m=o["w"], sill_m=o["sill"], head_m=round(o["head"], 3),
                           centre_m=[round(o["f"] if o["n"][0] else o["c"], 3), round(o["f"] if o["n"][1] else o["c"], 3)],
                           faces=["-x", "+x", "-y", "+y"][[(-1, 0), (1, 0), (0, -1), (0, 1)].index(tuple(o["n"]))])
                      for o in ops if M.opening_zone(o, zone_idx=zi) == name])
    env = E.spec()
    structure = []
    for e in env["elements"]:
        if e["category"] == "Windows" or e["id"].startswith(("beam-", "core-", "sister-core")):
            continue
        xs = [p[0] / 1000 for p in e["pts"]]; ys = [p[1] / 1000 for p in e["pts"]]
        structure.append(dict(id=e["id"], rect_m=[round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)],
                              z_m=[e["z0"] / 1000, e["z1"] / 1000], note=e["note"]))
    for s in env["slabs"]:
        if s["id"] in ("slab-GF-front",):
            xs = [p[0] / 1000 for p in s["pts"]]; ys = [p[1] / 1000 for p in s["pts"]]
            structure.append(dict(id=s["id"], rect_m=[min(xs), min(ys), max(xs), max(ys)], z_m=[-0.2, 0.0], note=s["note"]))
    structure.append(dict(id="car-ramp", rect_m=[round(M.X0I, 3), round(M.BAR[3], 3), 6.877, round(M.Y1I, 3)], z_m=[-1.2, 0.0],
                          note="car ramp, profile %s (revit_spec parking2)" % M.RAMP_PROFILE))
    structure.append(dict(id="parking-deck", rect_m=[6.877, round(M.BAR[3], 3), 12.777, round(M.Y1I, 3)], z_m=[-0.35, 0.0], note="deck over the basement extension, top 0.0"))
    structure.append(dict(id="extension-roof", rect_m=[12.777, round(M.BAR[3], 3), 15.412, round(M.Y1I, 3)], z_m=[-0.2, 0.0], note="extension roof, top 0.0"))
    services = [dict(id=v["id"], kind=v["kind"], at_m=[v["duct_route"][-1][0], v["duct_route"][-1][1]], z_m=v["duct_route"][-1][2],
                     discharge=v["discharge"], zone_above="under east-deck/east-roof (discharges inside the 0.25 m gap to the east fence, below the deck)")
                for v in __import__("archpipe.concept.revit_spec", fromlist=["build"]).build(
                    __import__("archpipe.concept.villa_r11", fromlist=["design"]).design("D1"))["ventilation"]]
    comp = components(cls)
    return _hdr("inventory", dict(
        classes={str(k): v for k, v in M.CLASSES.items()},
        cell_class=[[int(v) for v in row] for row in cls],
        surface_z_m=G.to_rows(zs),
        zones=zones,
        levels=[dict(name=n, z_m=z / 1000) for n, z in E.LEVELS] + [dict(name="garden floor (yard slab, level 'B -1.80' of the brief)", z_m=M.GROUND_Z)],
        steps_and_changes_of_level=[
            "No steps or ramp join the sunken garden (z -3.0) to the deck/roof (0.0) or the street (-1.2) inside the zones: the model holds none.",
            "East strip rises along the car ramp z -1.2 .. 0.0 over x -0.123..6.877 (structure, not a walking route).",
            "Shared entrance steps (street -1.2 to GF 0.0) occupy x -0.123..3.617, y to -28.671 inside our half of the core strip (modelled as one solid block).",
            "Yard wall NE, 1.40 m above the garden floor (top z -1.6), y -23.841..-23.591, separates the north court from the east strip.",
        ],
        structure=structure, services=services,
        connected_ground=comp,
        not_ours="Everything with y < %.3f (the villa axis; the sister plot and its yard) is NOT ours; there is NO fence on that line (villa_env ASSUMPTIONS)." % M.AXIS,
        placeholders="Plot geometry is the client CAD/Revit export (measured); neighbours, apartment openings and sister openings are ASSUMED (see gaps S5).",
        gaps=[dict(id=i, text=t) for i, t in GAPS if i.startswith("S")]))


def main(png=True):
    t0 = time.time()
    cls, zs = M.classify()
    zi = M.zone_of_cells()
    inv = inventory(cls, zs); _write("inventory", inv)
    print("inventory", round(time.time() - t0), "s")

    lay = A.sun_layers(cls, zs)
    alt = A.sun_layers(cls, zs, lat=30.050, lon=31.000)            # spec/villa-site.yaml city-level PLACEHOLDER
    sens = {k: dict(max_abs_diff_h=round(float(np.nanmax(abs(lay[k] - alt[k]))), 2), mean_abs_diff_h=round(float(np.nanmean(abs(lay[k] - alt[k]))), 3)) for k in lay}
    zstats = {z: {k: _stats(a, zi == i) for k, a in lay.items()} for i, z in enumerate(M.ZONES)}
    sun = _hdr("sun", dict(
        method="Direct beam from each cell centre 0.05 m above its surface to the sun, against the opaque enclosure triangles used by concept/garden_sun.py (building, fences, yard wall, neighbours 12 m, sister, apartment, steps block, slabs); glass excluded; plants, pergola, furniture absent. NOAA solar position (archpipe.solar). 15-minute steps, sampled at mid-interval, each sunlit sample = 0.25 h.",
        time_basis="local STANDARD time = UTC+2 (as garden_sun). 'dst_clock' = the same clock hours read on a UTC+3 clock (gap S7).",
        location=dict(latitude=E.LATITUDE, longitude=E.LONGITUDE, source="villa_env.py: client maps link resolved 2026-09-25 - plot-level, NOT surveyed",
                      placeholder_status="spec/villa-site.yaml holds 30.050/31.000 'city-level' EXAMPLE values; they are placeholders and are NOT used. Sensitivity (see sensitivity_vs_yaml_placeholder) is small.",
                      model_y_true_bearing_deg=20, street_facade_azimuth_deg=290),
        dates=A.DATES,
        units="hours of direct sun (shade = window length minus sun)",
        windows={"summer_evening_17_20_standard_time": "17:00-20:00 standard time, 3 h, 21 June", "summer_evening_17_20_dst_clock": "17:00-20:00 on a UTC+3 clock = 16:00-19:00 standard, 3 h, 21 June",
                 "winter_day_10_15": "10:00-15:00, 5 h, 21 December"},
        layers={k: G.to_rows(a, 2) for k, a in lay.items()},
        zone_stats=zstats, sensitivity_vs_yaml_placeholder=sens,
        sanity=sanity(cls, zs, lay),
        gaps=[dict(id=i, text=t) for i, t in GAPS if i in ("S6", "S7", "C2")]))
    _write("sun", sun)
    print("sun", round(time.time() - t0), "s")

    V, groups, play, req = A.privacy(cls, zs)
    pz = {z: {k: round(float(np.nanmean(a[zi == i][~np.isnan(a[zi == i])] > 0)) * 100, 1) if (~np.isnan(a[zi == i])).any() else None
              for k, a in play.items() if k.endswith("standing")} for i, z in enumerate(M.ZONES)}
    anyc = play["overlooking_eyes_any_standing"]
    eyes_stats = {z: dict(min=int(np.nanmin(anyc[zi == i])), median=float(np.nanmedian(anyc[zi == i])), max=int(np.nanmax(anyc[zi == i])),
                          cells_with_fewer_than_5_eyes_pct=round(100 * float((anyc[zi == i][~np.isnan(anyc[zi == i])] < 5).mean()), 1))
                  for i, z in enumerate(M.ZONES)}
    priv = _hdr("privacy", dict(
        eyes_any_standing_stats_by_zone=eyes_stats,
        method="Straight sightline from each viewer eye point to a target point above each analysed cell; blocked by the opaque enclosure. Counts are eye points with a clear sightline. Conservative: no field-of-view limit (a viewer may lean to the glass), glass transparent.",
        eye_heights_m=dict(standing=M.EYE_STANDING, seated=M.EYE_SEATED, source="Time-Saver Standards for Landscape Architecture 2nd ed., p.340-4 note 3 (fig. 340-8, p.340-7): 1525 mm standing, 1125 mm sitting (US average adult; Egyptian adults may be shorter, which only lowers sightlines slightly)"),
        viewers=[dict(id=v["id"], group=v["group"], eye_m=[round(x, 3) for x in v["eye"]], source=v["source"]) for v in V],
        groups=groups,
        layers={k: G.to_rows(a, 0) for k, a in play.items()},
        pct_cells_overlooked_by_zone_standing=pz,
        boundaries=A.boundary_table(req),
        reading="required_top_z_*: the screen TOP (absolute z; garden floor is -3.0; existing fences top at +1.0) at the boundary that blocks every visible sightline crossing that 0.5 m segment to a target in that distance band behind the line (bands in distance_bands_m). A screen of top T protects a band only if T >= its value; FARTHER bands need TALLER screens (a downward sightline from an upper window grazes any screen and lands far behind it), so for upper-storey viewers a boundary screen cannot shield seats set back from it: overhead or near-seat cover is needed. by_group splits the value per viewer group. null = no visible sightline crosses there (nothing to block).",
        gaps=[dict(id=i, text=t) for i, t in GAPS if i in ("S4", "S5")]))
    _write("privacy", priv)
    print("privacy", round(time.time() - t0), "s")

    po, nr, pr = A.views(cls, zs, M.our_openings())
    cand = A.focal_candidates(nr, pr, zi, cls)
    vw = _hdr("views", dict(
        method="From each exterior opening of a garden-facing room (living, dining, lounge, kitchen, dirty kitchen, study, bedrooms), three eye points 1.0 m inside the opening plane (centre and +-w/4); a cell counts as seen when the sightline to its seated-eye-height point passes through the opening aperture and is not blocked outside. Eye: seated 1.125 m (standing 1.525 m in the kitchens), Time-Saver p.340-4.",
        per_opening=po, layers=dict(rooms_seeing_cell=G.to_rows(nr, 0), **{"seen_from_" + r: G.to_rows(a, 0) for r, a in pr.items()}),
        focal_point_candidates=cand,
        reading="Candidates are where the most rooms look: places to put something worth seeing. They are not a design; the concept stage decides. Bedrooms count like any room.",
        gaps=[dict(id="S8", text="No door opens from the dirty kitchen to the east yard in the model (only a window), and the lounge, study and bedroom windows facing the north court / roof are blocked by the terrace slab or give no ground view; see per_opening cells_seen.")]))
    _write("views", vw)
    wd = _hdr("wind", dict(
        source="Cairo West AP, WMO 623680, TMYx weather file held at ~/archpipe/weather (nearest station, ADR-0017; 10 m, open terrain). Hours are local standard time, hour-ending.",
        bearing_note="from_bearing_true = direction the wind blows FROM, degrees clockwise from TRUE north. Client sides face true bearings: north(street) 290, east 20, south 110, west 200 (site-orientation.json). share_by_client_side_pct = share of hours blowing from within +-45 deg of that side.",
        sets=A.wind(), gaps=[dict(id=i, text=t) for i, t in GAPS if i == "W1"]))
    _write("wind", wd)
    _write("checklist", _hdr("checklist", dict(
        source=CHECKLIST_SOURCE,
        items=[dict(item=i, status=s, where=w) for i, s, w in CHECKLIST],
        gaps=[dict(id=i, text=t) for i, t in GAPS])))
    print("done", round(time.time() - t0), "s")
    if png:
        from . import plots
        plots.all_plots()


def sanity(cls, zs, lay):
    """Our 15-min results at the points earlier garden studies quote, next to what they quoted."""
    def pt(x, y, z):
        o = np.array([[x, y, z + 0.05]])
        out = {}
        for k, d in A.DATES.items():
            _, lit = A.sunlit_matrix(d, o)
            out[k] = round(float(lit.sum()) * A.STEP_MIN / 60, 2)
        return out
    from ...concept import garden_sun as GS
    st = GS.default_study()

    def hourly(x, y, z):
        return [len(st.hours(x, y, z, d)) for d in A.DATES.values()]
    xl = [float(x) for x in np.linspace(24.55, 26.85, 5)]
    hm = np.mean([hourly(x, -20.65, -2.9) for x in xl], axis=0)
    qm = np.mean([[pt(x, -20.65, -2.9)[k] for k in A.DATES] for x in xl], axis=0)
    zi = M.zone_of_cells()
    return {
        "g4_north_trellis_wall_x-0.06_y-24.0_z-2.90": dict(
            quoted_G4_report="1.50 / 1.00 / 1.17 h (June / March / December), 10-minute midpoints", ours_15min=pt(-0.06, -24.0, -2.90)),
        "g6_loquat_run_east_wall_y-20.65_x24.55-26.85_z-2.9": dict(
            quoted_G6_report="east boundary of the south garden, five root-height points: mean 6.4 / 3.0 / 2.4 h (June / March / December), hourly",
            ours_hourly_project_code_mean=[round(float(v), 2) for v in hm], ours_15min_mean=[round(float(v), 2) for v in qm]),
        "g2_report": "'North has only four/five hours [June], East has nine sampled hours' at the then-authored plant positions",
        "ours_june_max_by_zone": {z: round(float(np.nanmax(lay["sun_hours_summer_solstice"][zi == i])), 2) for i, z in enumerate(M.ZONES)},
        "ours_june_mean_by_zone": {z: round(float(np.nanmean(lay["sun_hours_summer_solstice"][zi == i])), 2) for i, z in enumerate(M.ZONES)},
    }


if __name__ == "__main__":
    main(png="--no-png" not in sys.argv)
