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

JOB = "villa-df-r8"
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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    sys.exit({"run": run, "fetch": fetch}[cmd]())
