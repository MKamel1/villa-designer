"""Climate-based daylight: real skies from a weather file, lux at chosen hours, by daylight coefficients.

`daylight.py` gives the daylight factor (CIE overcast, time-independent). In a sunny climate that misses the sun,
so this module adds point-in-time illuminance (lux) under the sky the weather file records for each hour, by the
two-phase daylight-coefficient method: Radiance (rfluxmtx) computes each sensor's contribution from every sky patch
once per scene (Reinhart subdivision MF 2, 577 patches + ground); gendaymtx turns weather-file hours into sky
vectors (Perez all-weather model); dctimestep multiplies. Any hour, or a whole year, is then cheap.

Stated: the sun is spread over its sky patch (two-phase), so sun patches on the floor are softened and edges are
approximate; the room-average lux is what the method is good for. Hours are the weather file's standard time
(Egypt's summer clock time is one hour later). Orientation: a scene whose axes are not true north is handled by
rotating the sky (gendaymtx -r, counter-clockwise, west of north).

VALIDATION (validation_cases): (1) orientation: a vertical sensor facing the morning sun must receive more than
twice the irradiance of the one facing away, and vice versa in the afternoon (pre-registered 2x); (2) method: the
box room's mean lux by daylight coefficients within 20 % of a direct rtrace under the same hour's gendaylit sky
(pre-registered; two-phase sun smearing is the expected difference).
"""
from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path

from . import daylight as D
from .safe_io import save_bytes, save_json, save_text

MF = 2
DC_OPTS = ["-I+", "-y", "{n}", "-n", "30", "-ab", "5", "-ad", "4096", "-lw", "5e-5", "-c", "1"]
LUX_COEF = (47.4, 119.9, 11.6)          # 179 lm/W x CIE weights (0.265, 0.670, 0.065)
ORIENT_RATIO = 2.0                      # pre-registered 2026-09-26
METHOD_TOLERANCE = 0.20                 # pre-registered 2026-09-26

SKY_RECEIVER = ("#@rfluxmtx h=u u=Y\nvoid glow ground_glow\n0\n0\n4 1 1 1 0\nground_glow source ground\n0\n0\n"
                "4 0 0 -1 180\n#@rfluxmtx h=r{mf} u=Y\nvoid glow sky_glow\n0\n0\n4 1 1 1 0\nsky_glow source sky\n0\n0\n"
                "4 0 0 1 180\n")


def read_epw(path):
    """(header dict, rows) from an .epw or a zip holding one."""
    p = Path(path)
    if p.suffix == ".zip":
        z = zipfile.ZipFile(p)
        text = z.read([n for n in z.namelist() if n.endswith(".epw")][0]).decode("latin-1")
    else:
        text = p.read_text(encoding="latin-1")
    lines = text.splitlines()
    loc = lines[0].split(",")
    head = {"place": loc[1], "lat": float(loc[6]), "lon": float(loc[7]), "tz": float(loc[8]), "elev": float(loc[9])}
    rows = []
    for l in lines[8:]:
        f = l.split(",")
        if len(f) < 16:
            continue
        rows.append({"month": int(f[1]), "day": int(f[2]), "hour": int(f[3]), "dni": float(f[14]),
                     "dhi": float(f[15]), "ghi": float(f[13])})
    return head, rows


def wea_text(head, rows, stamps):
    """A Radiance .wea for (month, day, clock hour as a float) stamps: the weather file's hour whose interval holds
    the stamp (EPW hour h covers h-1..h). Radiance longitude and time zone are degrees WEST."""
    out = ["place %s" % head["place"].replace(" ", "_"), "latitude %.4f" % head["lat"],
           "longitude %.4f" % -head["lon"], "time_zone %.1f" % (-15 * head["tz"]), "site_elevation %.1f" % head["elev"],
           "weather_data_file_units 1"]
    by = {(r["month"], r["day"], r["hour"]): r for r in rows}
    for m, d, h in stamps:
        r = by[(m, d, int(h) + 1)]
        out.append("%d %d %.3f %.1f %.1f" % (m, d, h, r["dni"], r["dhi"]))
    return "\n".join(out) + "\n"


RUN_DC = """#!/bin/bash
# archpipe climate daylight job: daylight coefficients per case, then lux at the weather-file hours
set -euo pipefail
R="$HOME/archpipe/tools/radiance-6.0.1"
export PATH="$R/bin:$PATH" RAYPATH=".:$R/lib"
cd "$(dirname "$0")"
gendaymtx -m {mf} -r {rot} sky.wea > sky.mtx 2> gendaymtx.log
for d in $(cat order.txt); do
  ( cd "cases/$d"
    oconv scene.rad > scene.oct
    N=$(wc -l < points.txt)
    rfluxmtx $(sed "s/{{n}}/$N/" ../../dc_opts.txt) - ../../receiver.rad -i scene.oct < points.txt > dc.mtx 2> dc.log
    dctimestep dc.mtx ../../sky.mtx | rmtxop -fa -c {c} - > lux.txt
    if [ -s pit.txt ]; then                         # direct rtrace under point-in-time skies (method check)
      while read -r tag args; do
        gendaylit $args | xform -rz {rot} > sky_$tag.rad   # the same rotation as gendaymtx -r
        cat ../../sky_glow.rad >> sky_$tag.rad
        oconv sky_$tag.rad scene.rad > pit_$tag.oct
        rtrace {rt} -n 30 pit_$tag.oct < points.txt > pit_$tag.out
      done < pit.txt
    fi ) || echo "FAILED $d" >> errors.txt
  echo "done $d $(date +%T)" >> progress.txt
done
touch DONE
"""


def write_job(cases, folder, head, rows, stamps, rotation_deg, pit=None):
    """cases: {name: (Scene, sensors)} with sensors [{"id", "x", "y", "z", "n": (nx, ny, nz), ...}];
    pit: {case: [(tag, month, day, hour)]} point-in-time rtrace checks."""
    folder = Path(folder)
    (folder / "cases").mkdir(parents=True, exist_ok=True)
    save_text(folder / "receiver.rad", SKY_RECEIVER.format(mf=MF))
    save_text(folder / "sky_glow.rad", D.SKY_GLOW)
    save_text(folder / "sky.wea", wea_text(head, rows, stamps))
    save_text(folder / "dc_opts.txt", " ".join(DC_OPTS))
    save_text(folder / "run.sh", RUN_DC.format(mf=MF, rot=rotation_deg, c=" ".join(map(str, LUX_COEF)),
                                                 rt=" ".join(D.RTRACE_OPTS)))
    order = sorted(cases, key=lambda n: (not n.startswith("v-"), n))
    save_text(folder / "order.txt", "\n".join(order) + "\n")
    by = {(r["month"], r["day"], r["hour"]): r for r in rows}
    for name, (scene, sensors) in cases.items():
        d = folder / "cases" / name
        d.mkdir(parents=True, exist_ok=True)
        save_text(d / "scene.rad", D.scene_rad(scene))
        save_text(d / "points.txt", "\n".join("%.4f %.4f %.4f %.4f %.4f %.4f" % ((s["x"], s["y"], s["z"]) + tuple(s["n"]))
                                                for s in sensors) + "\n")
        save_json(d / "sensors.json", {"sensors": sensors, "stamps": stamps})
        lines = []
        for tag, m, dd, h in (pit or {}).get(name, []):
            r = by[(m, dd, int(h) + 1)]
            lines.append("%s %d %d %.3f -a %.4f -o %.4f -m %.1f -W %.1f %.1f" %
                         (tag, m, dd, h, head["lat"], -head["lon"], -15 * head["tz"], r["dni"], r["dhi"]))
        save_text(d / "pit.txt", "\n".join(lines) + ("\n" if lines else ""))
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(folder, arcname=".")
    tgz = folder.with_suffix(".tar.gz")
    save_bytes(tgz, buf.getvalue())
    return tgz


def read_lux(case_dir):
    """lux[sensor][stamp] from lux.txt (rmtxop ascii: a header, a blank line, then one row per sensor)."""
    text = (Path(case_dir) / "lux.txt").read_text()
    body = text.split("\n\n", 1)[1] if "\n\n" in text else text
    return [[float(v) for v in l.split()] for l in body.strip().split("\n") if l.strip()]


def read_pit(case_dir, tag):
    vals = [float(v) for v in (Path(case_dir) / ("pit_%s.out" % tag)).read_text().split()]
    return [LUX_COEF[0] * vals[i] + LUX_COEF[1] * vals[i + 1] + LUX_COEF[2] * vals[i + 2] for i in range(0, len(vals), 3)]


# ---- validation -----------------------------------------------------------------------------------------------------
def orientation_case(model_to_true_deg):
    """Open ground with four vertical sensors facing the model's +x, -x, +y, -y, 1.5 m up, far from anything."""
    s = D.Scene().add([D.Face([(-50, -50, 0), (50, -50, 0), (50, 50, 0), (-50, 50, 0)], "ground")])
    sensors = [{"id": k, "x": 0.0, "y": 0.0, "z": 1.5, "n": n}
               for k, n in (("+x", (1, 0, 0)), ("-x", (-1, 0, 0)), ("+y", (0, 1, 0)), ("-y", (0, -1, 0)))]
    return s, sensors


def check_orientation(lux, stamps, expect):
    """expect: [(stamp index, facing that should see the sun, facing opposite)]."""
    ids = ["+x", "-x", "+y", "-y"]
    out = []
    for k, sunny, shaded in expect:
        a, b = lux[ids.index(sunny)][k], lux[ids.index(shaded)][k]
        out.append({"stamp": stamps[k], "sunny": sunny, "lux_sunny": round(a), "shaded": shaded, "lux_shaded": round(b),
                    "pass": a > ORIENT_RATIO * max(b, 1.0)})
    return out
