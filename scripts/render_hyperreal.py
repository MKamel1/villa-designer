"""Presentation renders on the workstation: physical daylight, real finishes.

    python scripts/render_hyperreal.py --views door bedfoot window --lights off
    python scripts/render_hyperreal.py --views all --samples 2048 --res 1920x1200
    python scripts/render_hyperreal.py --when "2026-12-15 11:00" --views window

The sun is placed from the site in spec/villa-site.yaml (Cairo) with
archpipe.solar, on this machine, and handed to Blender as altitude/azimuth
because the scene script cannot import archpipe. Recipe and sources:
docs/decisions/ADR-0013-presentation-renders.md.

Not part of run_bedroom.py's acceptance gate; --measure never runs here.
Requires scripts/fetch_asset_library.py to have been run already.
"""
from __future__ import annotations
import argparse
import json
import shlex
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe import render_qa
from archpipe.solar import sun_position
from render_remote import _ssh
from workstation import deploy, digest

VIEWS = ["door", "bedfoot", "window", "desk", "wardrobe", "detail"]

# Stated conditions per time of day. Day: physical Nishita sun from the site
# plus a photographed view. Overcast and night: one photographed environment
# is both light and view, scaled to a stated horizontal illuminance.
TIMES = {
    "day":      dict(lights="off", hdri=None, lux=None, wb=5500.0),
    "overcast": dict(lights="off", hdri="tiergarten", lux=15000.0, wb=6500.0),
    "night":    dict(lights="on",  hdri="dikhololo_night", lux=0.3, wb=3200.0),  # camera tungsten preset
}
# If a render fails ONLY on these, the tone curve is the variable: retry once
# with the other look instead of hand-tuning per view (door vs bedfoot).
TONAL = {"highlight_clipping", "highlights_present", "shadows_present", "exposure_midtones"}
LOOKS = ["AgX - Medium High Contrast", "AgX - High Contrast"]


def save(path: Path, data: bytes, attempts: int = 10) -> None:
    """Write via a temp file and swap it in, retrying a Windows sharing lock.

    An image viewer or the search indexer holding the previous render made
    a plain overwrite fail with OSError 22 halfway through a batch.
    """
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    for i in range(attempts):
        try:
            tmp.replace(path)
            return
        except OSError:
            if i == attempts - 1:
                raise
            time.sleep(1.0)


def site():
    s = yaml.safe_load((ROOT / "spec/villa-site.yaml").read_text(encoding="utf-8"))
    loc = s.get("location", s)
    return (float(loc["latitude"]), float(loc["longitude"]),
            float(loc.get("utc_offset_hours", loc.get("utc_offset", 2))))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="ai-workstation")
    ap.add_argument("--input", type=Path, default=ROOT / "out/bedroom-render.json")
    ap.add_argument("--views", nargs="+", default=["door", "bedfoot", "window"])
    ap.add_argument("--time", choices=sorted(TIMES), default="day")
    ap.add_argument("--lights", choices=["on", "off"], default=None,
                    help="override the time-of-day preset")
    ap.add_argument("--when", default="2026-12-15 11:00",
                    help="local site date/time for the sun")
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--res", default="1600x1000")
    ap.add_argument("--wb", type=float, default=None)
    ap.add_argument("--exposure-bias", type=float, default=-0.4,
                    help="stops relative to the meter; negative keeps sun patches from clipping")
    ap.add_argument("--view-rotation", type=float, default=180.0)
    ap.add_argument("--look", default="AgX - Medium High Contrast",
                    help="AgX look, e.g. 'AgX - Medium High Contrast'; chosen by render_qa tonal checks")
    ap.add_argument("--no-cloth", action="store_true")
    ap.add_argument("--no-dress", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--allow-qa-fail", action="store_true",
                    help="still exit 0 when archpipe.render_qa finds a defect")
    ap.add_argument("--qa-break", default="",
                    help="re-create historical defects (glass,view) to prove QA catches them")
    a = ap.parse_args()
    preset = TIMES[a.time]
    a.lights = a.lights or preset["lights"]
    a.wb = a.wb or preset["wb"]
    views = VIEWS if a.views == ["all"] else a.views
    bad = [v for v in views if v not in VIEWS]
    if bad:
        ap.error(f"unknown view(s) {bad}; choose from {VIEWS} or 'all'")

    lat, lon, utc = site()
    local = datetime.strptime(a.when, "%Y-%m-%d %H:%M")
    sun = sun_position((local - timedelta(hours=utc)).replace(tzinfo=timezone.utc), lat, lon)
    print(f"Sun at ({lat}, {lon}) {a.when} local: altitude {sun.altitude:.1f}, "
          f"azimuth {sun.azimuth:.1f}")
    if sun.altitude <= 0 and a.time == "day":
        ap.error("the sun is down at that time; use --lights on or another --when")

    root, release, _ = deploy(a.host)
    payload = json.loads(a.input.read_text(encoding="utf-8"))
    for light in payload.get("lighting", []):
        name = light.get("ies_file")
        if not name or Path(name).name != name:
            ap.error(f"light {light.get('id')!r} has no deployable ies_file")
        light["ies"] = f"{release}/assets/ies/{name}"
    data = json.dumps(payload).encode("utf-8")
    input_id = digest(data)
    remote_input = f"{root}/inputs/{input_id}.json"
    _ssh(a.host, f"mkdir -p {shlex.quote(root + '/inputs')}")
    if _ssh(a.host, f"cat > {shlex.quote(remote_input)}", stdin_bytes=data).returncode:
        raise RuntimeError("could not transfer the extract")
    blender = json.loads(_ssh(a.host, f"cat {shlex.quote(root)}/worker-environment.json").stdout)["blender"]
    library = f"{root}/assets/library"
    script = f"{release}/src/archpipe/blender/build_scene.py"

    qa_failed = []
    for view in views:
        stamp = f"{a.time}-{view}" + (f"-{a.tag}" if a.tag else "")
        def render(look):
            remote_out = f"{root}/inputs/{input_id}_{stamp}.png"
            flags = (f"--extract {shlex.quote(remote_input)} --out {shlex.quote(remote_out)} "
                     f"--interior --profile final --photo-camera {view} "
                     f"--interior-lights {a.lights} --sun-alt {sun.altitude:.3f} "
                     f"--sun-az {sun.azimuth:.3f} --view-rotation {a.view_rotation} --time {a.time} "
                     f"--exposure-bias {a.exposure_bias} --samples {a.samples} --res {a.res} "
                     f"--look {shlex.quote(look)}")
            if a.wb:
                flags += f" --wb {a.wb}"
            if preset["hdri"]:
                flags += f" --hdri {preset['hdri']} --hdri-lux {preset['lux']}"
            if a.no_cloth:
                flags += " --no-cloth"
            if a.no_dress:
                flags += " --no-dress"
            cmd = (f"ARCHPIPE_ASSET_LIBRARY={shlex.quote(library)} "
                   f"ARCHPIPE_QA_BREAK={shlex.quote(a.qa_break)} {shlex.quote(blender)} "
                   f"-b -t 8 --python-exit-code 1 -P {shlex.quote(script)} -- {flags}")
            started = time.monotonic()
            res = _ssh(a.host, cmd, timeout=3600)
            stdout = res.stdout.decode(errors="replace")
            notes = [l for l in stdout.splitlines() if l.startswith(("SCENE", "Error", "Traceback"))
                     or "Error" in l]
            if res.returncode or "SCENE wrote" not in stdout:
                print("\n".join(notes[-40:]) or stdout[-4000:])
                print(res.stderr.decode(errors="replace")[-3000:], file=sys.stderr)
                raise RuntimeError(f"{view}: render failed (exit {res.returncode})")
            img = _ssh(a.host, f"cat {shlex.quote(remote_out)}").stdout
            out = ROOT / f"out/photoreal/bedroom-{stamp}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            save(out, img)
            save(out.with_suffix(".log"), stdout.encode("utf-8"))
            for l in notes:
                if l.startswith(("SCENE BEDDING", "SCENE METER", "SCENE WHITE", "SCENE SKY",
                                 "SCENE DRESSING", "SCENE PORTALS")):
                    print("   ", l[:400])
            print(f"{out}  {time.monotonic() - started:.0f}s")
            # Every render is checked by machine before anyone looks at it; each
            # check is a defect a person previously had to spot (LEARNINGS.md).
            report = render_qa.check(out, render_qa.scene_qa_from_log(stdout))
            out.with_suffix(".qa.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            for r in report["checks"]:
                if r["status"] != "PASS":
                    print(f"    QA {r['status']}: {r['check']} -- {r['detail']}")
            print("    QA PASS" if report["passed"] else "    QA FAIL: " + ", ".join(report["failed"]))
            return report

        report = render(a.look)
        failed = set(report["failed"])
        if failed and failed <= TONAL:
            other = next(l for l in LOOKS if l != a.look)
            print(f"    tonal-only failure {sorted(failed)}; retrying with look '{other}'")
            retry = render(other)
            if retry["passed"]:
                report = retry
        if not report["passed"]:
            qa_failed.append(view)
    if qa_failed and not a.allow_qa_fail:
        print(f"QA failed for {qa_failed}; see out/photoreal/*.qa.json", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
