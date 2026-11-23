"""V11 prep: a DIALux evo import package for three spaces, written to knowledge/lighting-verify/dialux/.

Spaces (engine clusters): B-open (dining + kitchen are inside this open plan: the whole volume must be modelled, as the
engine does, otherwise the light that crosses the open boundaries is missing), GF-family-bath, GF-parents-bed.
Per space: <cluster>/room.dxf (floor and ceiling outlines + vertical edges, metres), luminaires.csv, planes.csv,
reflectances.json, expected-engine.json (what the engine says: Em/Emin/U0 per plane for the 'full' scene) and ies/*.ies.
"""
from __future__ import annotations

from archpipe.safe_io import copy_file
import csv
import json
import shutil
from pathlib import Path

import ezdxf

from ..lightcalc.direct import aim_angles
from ..lightcalc.villa import MF, RHO, cluster_of

CLUSTERS = ("B-open", "GF-family-bath", "GF-parents-bed")
OUT = Path(__file__).resolve().parents[3] / "knowledge" / "lighting-verify" / "dialux"


def write_dxf(room, path: Path):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.M
    msp = doc.modelspace()
    poly = list(room.polygon)
    msp.add_lwpolyline(poly, close=True, dxfattribs={"layer": "FLOOR", "elevation": room.floor_z})
    msp.add_lwpolyline(poly, close=True, dxfattribs={"layer": "CEILING", "elevation": room.ceiling_z})
    for x, y in poly:
        msp.add_line((x, y, room.floor_z), (x, y, room.ceiling_z), dxfattribs={"layer": "WALL_EDGES"})
    doc.saveas(path)


def export(villa, results_dir: Path | None = None, out: Path = OUT) -> dict:
    from ..lightcalc import villa_report as VR
    planes = villa.planes()
    summary = {}
    for cl in CLUSTERS:
        d = out / cl
        (d / "ies").mkdir(parents=True, exist_ok=True)
        room = villa.cluster_room(cl)
        write_dxf(room, d / "room.dxf")
        rows = []
        for p in villa.cluster_placements(cl):
            if p.meta.get("ies_path"):
                name = Path(p.meta["ies_path"]).name
                copy_file(p.meta["ies_path"], d / "ies" / name)
            else:
                name = "generic-%s.ies" % p.meta.get("kind")
                (d / "ies" / name).write_text(p.meta["ies_text"], encoding="utf-8")
            tilt, az = aim_angles(p.aim)
            rows.append(dict(id=p.id, ies=name, x=round(p.position[0], 4), y=round(p.position[1], 4), z=round(p.position[2], 4),
                             aim_x=round(p.aim[0], 4), aim_y=round(p.aim[1], 4), aim_z=round(p.aim[2], 4),
                             tilt_from_nadir_deg=round(tilt, 2), tilt_azimuth_deg=round(az, 2), flux_scale=round(p.dim, 4),
                             zone=p.zone, layer=p.layer, generic=bool(p.meta.get("generic"))))
        with open(d / "luminaires.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        prow = [dict(id=pl.id, room=pl.room, z=pl.z, target_lux=pl.target, gauge=pl.gauge, scene=pl.scene,
                     polygon=json.dumps([[round(a, 4), round(b, 4)] for a, b in pl.polygon]))
                for pl in planes if cluster_of(pl.room) == cl]
        with open(d / "planes.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(prow[0]))
            w.writeheader()
            w.writerows(prow)
        (d / "reflectances.json").write_text(json.dumps(
            dict(floor=RHO["floor"], wall=RHO["wall"], ceiling=RHO["ceiling"], maintenance_factor=MF,
                 note="ASSUMED reflectances (0.80/0.85/0.33), closed room, no furniture; set every surface to these; no windows, no daylight"), indent=1))
        exp = {}
        jf = (results_dir / (cl + ".json")) if results_dir else None
        if jf and jf.exists():
            res = VR.ClusterRes.load(jf)
            for pl in prow:
                if pl["id"] in res.slices:
                    st = res.stats(pl["id"], VR.full_levels(res))
                    exp[pl["id"]] = dict(Em=round(st.em, 1), Emin=round(st.emin, 1), U0=round(st.u0, 3), n=st.n)
        (d / "expected-engine.json").write_text(json.dumps(
            dict(scene="full: every functional zone at 100 % of its luminaire flux_scale, night zones off", maintenance_factor=MF,
                 radiance_ab=res.ab if exp else None, planes=exp), indent=1))
        summary[cl] = dict(luminaires=len(rows), planes=len(prow), expected=len(exp))
    (out / "STEPS.md").write_text(STEPS, encoding="utf-8")
    return summary


STEPS = """# DIALux evo cross-check (V11) - one sitting on the laptop

Pass bar (docs/quality/LIGHTING-VERIFICATION.md): average illuminance Em within +/-10 %, Emin and U0 within +/-15 % of the
engine, on every plane below, in each of the three spaces. Spaces: `B-open` (contains the dining and kitchen planes),
`GF-family-bath`, `GF-parents-bed`.

For each space folder (`B-open/`, `GF-family-bath/`, `GF-parents-bed/`):

1. New project -> new room by importing `room.dxf` (metres; FLOOR and CEILING outlines at their elevations). If the importer
   keeps only 2D, draw the floor outline from FLOOR and set the room height to CEILING elevation minus FLOOR elevation. Walls straight, no windows, no doors, no furniture, no daylight.
2. Surfaces: ceiling 85 %, walls 80 %, floor 33 % (`reflectances.json`). Maintenance factor 0.80 on all luminaires.
3. Luminaires: import `ies/*.ies` as user photometry. Place one luminaire per row of `luminaires.csv` at (x, y, z) in the same
   coordinates (z absolute; the floor is `FLOOR` elevation). Aim with tilt `tilt_from_nadir_deg` toward azimuth `tilt_azimuth_deg`
   (0 deg = +x, counter-clockwise). Set the dimming of each luminaire to `flux_scale` x 100 % relative to the file's own lumens
   (the generic `generic-*.ies` files are already at their design flux: use `flux_scale` = 1 only if it is 1, else follow the column).
   Rows with `layer` = night or emergency are OFF.
4. Calculation surfaces: one per row of `planes.csv`: a horizontal plane at height `z` (absolute) over the polygon, grid about
   0.2-0.3 m, no border. Use the same names as `id`.
5. Run a full calculation (direct + indirect). Read Em, Emin and Emin/Em (U0) per plane into `results-dialux.json`
   as `{"<plane id>": {"Em": .., "Emin": .., "U0": ..}}` in the space folder.
6. Tell the lead; `python -m archpipe.lightverify.dialux_compare` (to be run on the workstation) reads these files against
   `expected-engine.json` and applies the pass bar.
"""
