"""Daylight factor (CIE overcast) for the villa options, on the Ubuntu compute node.

    PYTHONPATH=src python scripts/villa_daylight.py run      # build scenes, push, start detached (setsid)
    PYTHONPATH=src python scripts/villa_daylight.py fetch    # when done: pull results, validate, write report JSON

Cases: the three validation scenes (archpipe.daylight.validation_cases), S1 (the basement's east face open) and S5
(east-yard blocks) as baselines, and the parking options P1-P4. Results are DIAGNOSTIC unless all three
validation checks pass.
"""
from __future__ import annotations

import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_remote import DEFAULT_HOST, _ssh                         # noqa: E402

from archpipe import daylight as D                                   # noqa: E402
from archpipe.concept import villa_daylight as VD                    # noqa: E402
from archpipe.concept import villa_options as VO                     # noqa: E402
from archpipe.concept import villa_parking as P                      # noqa: E402

JOB = "villa-df-r8b"
LOCAL = Path("out/villa/daylight") / JOB
REMOTE = f"$HOME/archpipe/daylight/{JOB}"


def cases():
    val, expect = D.validation_cases()
    out = dict(val)
    for lay in [VO.s1(), VO.s5()] + P.options():
        out[lay["id"]] = VD.scene(lay)
    return out, expect


def run(host=DEFAULT_HOST):
    if LOCAL.exists():
        shutil.rmtree(LOCAL)
    cs, expect = cases()
    tgz = D.write_job(cs, LOCAL, fine=["v-box"])
    (LOCAL / "expectation.json").write_text(json.dumps(expect), encoding="utf-8")
    res = _ssh(host, f'rm -rf "{REMOTE}" && mkdir -p "{REMOTE}" && tar xzf - -C "{REMOTE}"',
               stdin_bytes=tgz.read_bytes(), timeout=300)
    if res.returncode:
        raise SystemExit(res.stderr.decode(errors="replace"))
    # the subshell matters: "A && B > log &" backgrounds the whole list with ssh's stdout still attached, and ssh
    # then waits for the job to end (seen 2026-09-26)
    res = _ssh(host, f'cd "{REMOTE}" && (setsid nohup bash run.sh > run.log 2>&1 < /dev/null &) ; echo started')
    print(res.stdout.decode().strip(), "->", REMOTE, "cases:", ", ".join(cs))
    return 0


def fetch(host=DEFAULT_HOST):
    st = _ssh(host, f'cd "{REMOTE}" && ls DONE 2>/dev/null; cat errors.txt progress.txt 2>/dev/null; tail -3 run.log')
    text = st.stdout.decode()
    if "DONE" not in text:
        print("not finished yet:\n" + text)
        return 2
    res = _ssh(host, f'cd "{REMOTE}" && tar czf - cases/*/out.txt cases/*/rtrace.log run.log $(ls errors.txt 2>/dev/null)',
               timeout=300)
    with tarfile.open(fileobj=io.BytesIO(res.stdout), mode="r:gz") as tar:
        tar.extractall(LOCAL, filter="data")
    expect = json.loads((LOCAL / "expectation.json").read_text(encoding="utf-8"))
    results = {d.name: D.read_case(d) for d in sorted((LOCAL / "cases").iterdir()) if (d / "out.txt").exists()}
    val = D.validate(results, expect)
    report = {"validation": val, "expectation": expect, "results": results,
              "status": "validated" if val["all_pass"] else "DIAGNOSTIC (validation failed)"}
    out = LOCAL / "report.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(val, indent=1))
    print(out)
    return 0 if val["all_pass"] else 1


VIEW_JOB = "villa-views-r8"
EYE = -3.0 + 1.6                                   # basement FFL (model) + standing eye height
VIEWS = {                                          # the same four spots in every option (checked clear of walls)
    "1-hall-to-garden": D.View((10.2, -27.9, EYE), (1.0, 0.12, -0.08)),
    "2-middle-to-street": D.View((12.5, -25.8, EYE), (-1.0, 0.05, -0.08)),
    "3-dining-to-kitchen-east": D.View((18.3, -28.1, EYE), (-0.75, 0.66, -0.10)),
    "4-lounge-to-patio": D.View((6.5, -24.8, EYE), (-1.0, -0.30, -0.05)),
    "5-living-down-the-basement": D.View((22.0, -26.1, EYE), (-1.0, 0.0, -0.06), vh=80.0),   # the same in every layout
}
VIEW_NOTES = {"S1_1-hall-to-garden": "in S1 this spot faces a partition 1 m away: not comparable; use view 5"}


def render(host=DEFAULT_HOST):
    """Eye-level basement renders of every option under the same overcast sky (no daylight-factor points)."""
    job = VIEW_JOB + ("-" + "-".join(sys.argv[2:]) if sys.argv[2:] else "")
    local, remote = LOCAL.parent / job, f"$HOME/archpipe/daylight/{job}"
    if local.exists():
        shutil.rmtree(local)
    cs = {}
    for lay in [VO.s1(), VO.s5()] + P.options():
        sc = VD.scene(lay)
        sc.rooms = []
        cs[lay["id"]] = sc
    only = [v for v in VIEWS if v in sys.argv[2:]] or list(VIEWS)     # render: all views, or those named
    tgz = D.write_job(cs, local, views={c: {v: VIEWS[v] for v in only} for c in cs})
    res = _ssh(host, f'rm -rf "{remote}" && mkdir -p "{remote}" && tar xzf - -C "{remote}"',
               stdin_bytes=tgz.read_bytes(), timeout=300)
    if res.returncode:
        raise SystemExit(res.stderr.decode(errors="replace"))
    res = _ssh(host, f'cd "{remote}" && (setsid nohup bash run.sh > run.log 2>&1 < /dev/null &) ; echo started')
    print(res.stdout.decode().strip(), "->", remote, len(cs) * len(VIEWS), "renders")
    return 0


def fetch_views(host=DEFAULT_HOST):
    """Pull the renders; write a fixed-exposure PNG and a false-colour luminance PNG for each."""
    import numpy as np
    from PIL import Image
    job = VIEW_JOB + ("-" + "-".join(sys.argv[2:]) if sys.argv[2:] else "")
    local, remote = LOCAL.parent / job, f"$HOME/archpipe/daylight/{job}"
    st = _ssh(host, f'cd "{remote}" && ls DONE 2>/dev/null; tail -2 progress.txt 2>/dev/null')
    if "DONE" not in st.stdout.decode():
        print("not finished yet:\n" + st.stdout.decode())
        return 2
    res = _ssh(host, f'cd "{remote}" && tar czf - cases/*/*.hdr', timeout=600)
    with tarfile.open(fileobj=io.BytesIO(res.stdout), mode="r:gz") as tar:
        tar.extractall(local, filter="data")
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import colormaps
    out = LOCAL.parent / "views"
    out.mkdir(exist_ok=True)
    sp = out / "stats.json"
    stats = json.loads(sp.read_text(encoding="utf-8"))["images"] if sp.exists() else {}
    for hdr in sorted((local / "cases").glob("*/*.hdr")):
        rgb = D.read_hdr(hdr)
        name = "%s_%s" % (hdr.parent.name, hdr.stem)
        Image.fromarray(D.tonemap_fixed(rgb)).save(out / (name + ".jpg"), quality=88)
        lum = D.luminance(rgb)
        fc = (colormaps["inferno"](np.clip(np.log10(np.maximum(lum, 1.0)) / np.log10(300.0), 0, 1))[..., :3] * 255)
        Image.fromarray(fc.astype(np.uint8)).save(out / (name + "_fc.jpg"), quality=88)
        stats[name] = {"median_cd_m2": round(float(np.median(lum)), 1), "p90_cd_m2": round(float(np.percentile(lum, 90)), 1)}
    (out / "stats.json").write_text(json.dumps({"white_cd_m2": 150, "falsecolour": "log scale 1-300 cd/m2 (inferno)",
                                                "views": {k: list(map(list, [v.vp, v.vd])) for k, v in VIEWS.items()},
                                                "images": stats, "notes": VIEW_NOTES}, indent=1), encoding="utf-8")
    print(out, len(stats), "images")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    sys.exit({"run": run, "fetch": fetch, "render": render, "fetch-views": fetch_views}[cmd]())
