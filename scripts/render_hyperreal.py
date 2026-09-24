"""Ad-hoc driver for a --profile final render: photo textures + HDRI sky.

    python scripts/render_hyperreal.py --time day --samples 1024 --camera bed

Not part of run_bedroom.py's acceptance gate -- this is the manual/
presentation path while the material and lighting-profile system is being
tuned, so it deploys and runs Blender directly (same pattern as
export_bedroom_glb.py) rather than going through worker_entry.py's job
cache. Requires scripts/fetch_asset_library.py to have been run already.
"""
from __future__ import annotations
import argparse
import shlex
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from render_remote import _ssh
from workstation import deploy, digest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="ai-workstation")
    ap.add_argument("--input", type=Path, default=ROOT / "out/bedroom-render.json")
    ap.add_argument("--camera", default="bed", choices=["bed", "window", "overview"])
    ap.add_argument("--time", default="day",
                    choices=["day", "overcast", "night", "golden", "midday"])
    ap.add_argument("--samples", type=int, default=512)
    ap.add_argument("--res", default="1920x1200")
    ap.add_argument("--dof", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    if not a.input.is_file():
        ap.error(f"{a.input} not found -- run scripts/make_render_input.py first")
    out = a.out or ROOT / f"out/bedroom-hyperreal-{a.time}-{a.camera}.png"

    root, release, release_id = deploy(a.host)

    # Bind each light to the deployed IES asset by filename, the same
    # substitution worker_entry.py does -- without it, a filesystem path
    # baked into the local extract (this machine's or an old deploy's)
    # resolves to nothing on the remote box and build_scene.py silently
    # falls back to isotropic point lights: right total lumens, wrong beam
    # shape, which a validation run at 128 samples caught only by reading
    # its own printed "0 with measured IES photometry" note.
    import json as _json
    payload = _json.loads(a.input.read_text(encoding="utf-8"))
    for light in payload.get("lighting", []):
        name = light.get("ies_file")
        if not name or Path(name).name != name:
            ap.error(f"light {light.get('id')!r} has no deployable ies_file")
        remote_ies = f"{release}/assets/ies/{name}"
        if _ssh(a.host, f"test -f {shlex.quote(remote_ies)}").returncode:
            ap.error(f"{name} is not deployed under assets/ies on {a.host}")
        light["ies"] = remote_ies
    data = _json.dumps(payload).encode("utf-8")
    input_id = digest(data)
    remote_input = f"{root}/inputs/{input_id}.json"
    if _ssh(a.host, f"mkdir -p {shlex.quote(root + '/inputs')}").returncode:
        raise RuntimeError("could not create remote input directory")
    if _ssh(a.host, f"cat > {shlex.quote(remote_input)}", stdin_bytes=data).returncode:
        raise RuntimeError("could not transfer the extract")

    config_probe = _ssh(a.host, f'cat {shlex.quote(root)}/worker-environment.json')
    import json
    blender = json.loads(config_probe.stdout)["blender"]
    library = f"{root}/assets/library"
    remote_out = f"{root}/inputs/{input_id}_{a.time}_{a.camera}.png"
    script = f"{release}/src/archpipe/blender/build_scene.py"

    flags = (f"--extract {shlex.quote(remote_input)} --out {shlex.quote(remote_out)} "
            f"--interior --camera {a.camera} --profile final --time {a.time} "
            f"--samples {a.samples} --res {a.res} --target-lux 160")
    if a.dof:
        flags += " --dof"
    cmd = (f"ARCHPIPE_ASSET_LIBRARY={shlex.quote(library)} "
          f"{shlex.quote(blender)} -b -t 8 --python-exit-code 1 -P {shlex.quote(script)} -- {flags}")

    print(f"Rendering {a.camera}/{a.time} at {a.samples} samples, {a.res} ...")
    started = time.monotonic()
    result = _ssh(a.host, cmd, timeout=1800)
    elapsed = time.monotonic() - started
    stdout = result.stdout.decode(errors="replace")
    print(stdout)
    if result.returncode != 0 or "SCENE wrote" not in stdout:
        print(result.stderr.decode(errors="replace")[-4000:], file=sys.stderr)
        raise RuntimeError(f"remote render failed (exit {result.returncode})")

    fetch = _ssh(a.host, f"cat {shlex.quote(remote_out)}")
    if fetch.returncode != 0 or not fetch.stdout:
        raise RuntimeError("render succeeded but the image could not be fetched")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(fetch.stdout)
    print(f"\n{out}  ({len(fetch.stdout) // 1024} KB, {elapsed:.0f}s total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
