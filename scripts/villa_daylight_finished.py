"""D1 daylight AS FINISHED AND FURNISHED: the render scene's own faces and reflectances in Radiance, beside the
round-12 D1 case (walls/ceilings 0.80 'white' variant, floor 0.20, ceilings 2.80, empty), so the renders and the
daylight analysis describe the same building (docs/D1-CONTINUATION.md: reconcile render-only finishes and
ceilings with the daylight analysis).

    PYTHONPATH=src python scripts/villa_daylight_finished.py run      # deploy + start on the workstation
    PYTHONPATH=src python scripts/villa_daylight_finished.py fetch    # pull, validate, compare per room

The same validated Radiance method and settings as scripts/villa_daylight.py (validation cases included).
Excluded from the finished case: fittings, dressing and emitters (daylight only). Included: furniture, false
ceilings and coves, feature panels, the stair guard, per-room floor/wall finishes, glass Tv 0.70.
"""
import io
import json
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from archpipe.execution_context import ContextError, project_context  # noqa: E402
from render_remote import DEFAULT_HOST, _ssh                         # noqa: E402

from archpipe import daylight as D                                   # noqa: E402
from archpipe.concept import villa_daylight as VD                    # noqa: E402
from archpipe.concept import villa_r11 as R                          # noqa: E402
from archpipe.concept import villa_render as VR                      # noqa: E402

JOB = "villa-df-d1-finished"
LOCAL = ROOT / "out" / "villa" / "daylight" / JOB
REMOTE = f"$HOME/archpipe/daylight/{JOB}"


def finished_scene():
    lay = R.design("D1")
    scene = VR.build(lay)
    s = D.Scene(notes=["D1 as finished and furnished: render scene faces and reflectances (villa_render.M)",
                       "fittings, dressing and emitters excluded; glass Tv 0.70"])
    for name, m in scene["materials"].items():
        key = "fin-" + name
        if m["kind"] == "glass":
            D.MATERIALS[key] = D.Material(key, "glass", float(m.get("transmittance", 0.7)))
        elif m["kind"] == "principled":
            D.MATERIALS[key] = D.Material(key, "plastic", float(m.get("reflectance", 0.5)))
    for mesh in scene["meshes"]:
        if mesh["group"] in ("fixture", "dressing"):
            continue
        key = "fin-" + mesh["material"]
        if key not in D.MATERIALS:
            continue
        s.add([D.Face([tuple(p) for p in f], key) for f in mesh["faces"]])
    s.rooms = VD.scene(lay).rooms
    return s


def run(host=DEFAULT_HOST):
    if LOCAL.exists():
        shutil.rmtree(LOCAL)
    val, expect = D.validation_cases()
    lay = R.design("D1")
    cases = dict(val)
    cases["D1"] = VD.scene(lay, lay.get("daylight_variant"))
    cases["D1-finished"] = finished_scene()
    tgz = D.write_job(cases, LOCAL, fine=["v-box"])
    (LOCAL / "expectation.json").write_text(json.dumps(expect), encoding="utf-8")
    res = _ssh(host, f'rm -rf "{REMOTE}" && mkdir -p "{REMOTE}" && tar xzf - -C "{REMOTE}"',
               stdin_bytes=tgz.read_bytes(), timeout=600)
    if res.returncode:
        raise SystemExit(res.stderr.decode(errors="replace"))
    res = _ssh(host, f'cd "{REMOTE}" && (setsid nohup bash run.sh > run.log 2>&1 < /dev/null &) ; echo started')
    print(res.stdout.decode().strip(), "->", REMOTE, "cases:", ", ".join(cases))
    return 0


def fetch(host=DEFAULT_HOST):
    st = _ssh(host, f'cd "{REMOTE}" && ls DONE 2>/dev/null; tail -3 run.log')
    if "DONE" not in st.stdout.decode():
        print("not finished yet:\n" + st.stdout.decode())
        return 2
    res = _ssh(host, f'cd "{REMOTE}" && tar czf - cases/*/out.txt run.log', timeout=600)
    with tarfile.open(fileobj=io.BytesIO(res.stdout), mode="r:gz") as tar:
        tar.extractall(LOCAL, filter="data")
    expect = json.loads((LOCAL / "expectation.json").read_text(encoding="utf-8"))
    results = {d.name: D.read_case(d) for d in sorted((LOCAL / "cases").iterdir()) if (d / "out.txt").exists()}
    val = D.validate(results, expect)
    rows = []
    a, b = results.get("D1", {}), results.get("D1-finished", {})
    for room in sorted(set(a.get("rooms", {})) | set(b.get("rooms", {}))):
        ra, rb = a.get("rooms", {}).get(room, {}), b.get("rooms", {}).get(room, {})
        rows.append({"room": room, "adf_study": ra.get("adf"), "adf_finished": rb.get("adf"), "median_study": ra.get("median"), "median_finished": rb.get("median")})
    report = {"validation": val, "rooms": rows,
              "status": "validated" if val["all_pass"] else "DIAGNOSTIC (validation failed)"}
    (LOCAL / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1)[:4000])
    return 0 if val["all_pass"] else 1


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        cmd = sys.argv[1]  # raises IndexError exactly as before
    else:
        cmd = args[0]
    if cmd not in ("run", "fetch"):
        return {"run": run, "fetch": fetch}[cmd]()
    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "villa-daylight-finished",
            output=LOCAL.parent,
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    return {"run": run, "fetch": fetch}[cmd]()


if __name__ == "__main__":
    sys.exit(main())
