"""Basement daylight in lux under Cairo's recorded skies (daylight only, no electric light), at four heights.

    PYTHONPATH=src python scripts/villa_climate.py run     # build, push, start detached on the compute node
    PYTHONPATH=src python scripts/villa_climate.py fetch   # pull, validate, write report.json

Hours: 09:30, 12:30 and 15:30 (weather-file standard time) on 21 March, 21 June and 21 December, from the Cairo
International Airport TMYx weather file (2011-2025). Heights above the basement floor: 0.05 (floor), 0.85
(work plane), 1.60 (standing eye) and 2.20 m. Options S1, S5, P3-P4 and the mitigation variants.
"""
from __future__ import annotations

import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_remote import DEFAULT_HOST, _ssh                          # noqa: E402

from archpipe import daylight as D                                    # noqa: E402
from archpipe import daylight_climate as C                            # noqa: E402
from archpipe.concept import villa_daylight as VD                     # noqa: E402
from archpipe.concept import villa_options as VO                      # noqa: E402
from archpipe.concept import villa_parking as P                       # noqa: E402

R11 = "r11" in sys.argv
JOB = "villa-lux-r11" if R11 else "villa-lux-r10"           # r10: straight stair only (P3-P5), headroom-sized slab opening, open study, variants
LOCAL = Path("out/villa/daylight") / JOB
REMOTE = f"$HOME/archpipe/daylight/{JOB}"
EPW = Path(r"C:/Users/mmbka/archpipe-sources/cairo-epw/EGY_QH_Cairo.Intl.AP.623660_TMYx.2011-2025.zip")
STAMPS = [(m, d, t) for m, d in ((3, 21), (6, 21), (12, 21)) for t in (9.5, 12.5, 15.5)]
HEIGHTS = (0.05, 0.85, 1.60, 2.20)
ROTATION = 20.0            # model -x (street face) is true azimuth 290: the sky turns 20 deg counter-clockwise
B_FFL = -3.0
# orientation check: (stamp index, facing that should get the sun, the facing opposite); model +x = true 110,
# -x = 290, +y = 20, -y = 200 (sun azimuths from archpipe.solar: 21 Jun 09:30 93, 15:30 275; 21 Dec 12:30 191)
ORIENT_EXPECT = [(3, "+x", "-x"), (5, "-x", "+x"), (7, "-y", "+y")]
PIT = [("mar1230", 3, 21, 12.5), ("dec0930", 12, 21, 9.5)]


def sensors_for(scene, rooms_level="B"):
    out = []
    for r in scene.rooms:
        if r.get("level") != rooms_level:
            continue
        for h in HEIGHTS:
            for x, y, _ in D.grid(dict(r, z=0.0), spacing=0.5, height=0.0, inset=0.3):
                out.append({"id": r["id"], "h": h, "x": round(x, 3), "y": round(y, 3), "z": round(B_FFL + h, 3),
                            "n": (0, 0, 1)})
    return out


def cases():
    cs = {"v-orient": C.orientation_case(ROTATION)}
    val, expect = D.validation_cases()
    box = val["v-box"]
    cs["v-box"] = (box, [{"id": "room", "h": 0.85, "x": x, "y": y, "z": z, "n": (0, 0, 1)}
                         for r in box.rooms for x, y, z in D.grid(r, **r.get("grid", {}))])
    for lay, v in VD.round_cases(R11):
        sc = VD.scene(lay, v)
        cs[lay["id"] if not v or lay.get("daylight_variant") == v else v["_case"]] = (sc, sensors_for(sc))
    return cs


def run(host=DEFAULT_HOST):
    if LOCAL.exists():
        shutil.rmtree(LOCAL)
    head, rows = C.read_epw(EPW)
    cs = cases()
    tgz = C.write_job(cs, LOCAL, head, rows, STAMPS, ROTATION, pit={"v-box": PIT})
    res = _ssh(host, f'rm -rf "{REMOTE}" && mkdir -p "{REMOTE}" && tar xzf - -C "{REMOTE}"',
               stdin_bytes=tgz.read_bytes(), timeout=300)
    if res.returncode:
        raise SystemExit(res.stderr.decode(errors="replace"))
    res = _ssh(host, f'cd "{REMOTE}" && (setsid nohup bash run.sh > run.log 2>&1 < /dev/null &) ; echo started')
    print(res.stdout.decode().strip(), "->", REMOTE, {k: len(v[1]) for k, v in cs.items()})
    return 0


def fetch(host=DEFAULT_HOST):
    st = _ssh(host, f'cd "{REMOTE}" && ls DONE 2>/dev/null; cat progress.txt errors.txt 2>/dev/null; tail -3 run.log')
    if "DONE" not in st.stdout.decode():
        print("not finished yet:\n" + st.stdout.decode())
        return 2
    res = _ssh(host, f'cd "{REMOTE}" && tar czf - cases/*/lux.txt cases/*/pit_*.out cases/*/dc.log run.log '
                     f'$(ls errors.txt 2>/dev/null)', timeout=600)
    with tarfile.open(fileobj=io.BytesIO(res.stdout), mode="r:gz") as tar:
        tar.extractall(LOCAL, filter="data")
    orient = C.check_orientation(C.read_lux(LOCAL / "cases" / "v-orient"), STAMPS, ORIENT_EXPECT)
    box_lux = C.read_lux(LOCAL / "cases" / "v-box")
    method = []
    for tag, m, d, h in PIT:
        k = STAMPS.index((m, d, h))
        dc = sum(row[k] for row in box_lux) / len(box_lux)
        pit = C.read_pit(LOCAL / "cases" / "v-box", tag)
        rt = sum(pit) / len(pit)
        rel = abs(dc - rt) / rt if rt else 1.0
        method.append({"hour": [m, d, h], "dc_mean_lux": round(dc), "rtrace_mean_lux": round(rt),
                       "relative": round(rel, 3), "tolerance": C.METHOD_TOLERANCE, "pass": rel <= C.METHOD_TOLERANCE})
    ok = all(o["pass"] for o in orient) and all(m["pass"] for m in method)
    results = {}
    for name in [c for c in cases() if not c.startswith("v-")]:
        sens = json.loads((LOCAL / "cases" / name / "sensors.json").read_text(encoding="utf-8"))["sensors"]
        lux = C.read_lux(LOCAL / "cases" / name)
        results[name] = {"sensors": [[s["id"], s["h"], s["x"], s["y"]] for s in sens],
                         "lux": [[round(v) for v in row] for row in lux]}
    report = {"status": "validated" if ok else "DIAGNOSTIC (validation failed)", "orientation": orient,
              "method": method, "stamps": STAMPS, "heights": HEIGHTS, "results": results}
    (LOCAL / "report.json").write_text(json.dumps(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "orientation": orient, "method": method}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit({"run": run, "fetch": fetch}[sys.argv[1] if len(sys.argv) > 1 else "run"]())
