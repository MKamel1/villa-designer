"""Export the bedroom scene as a glTF binary for an interactive web viewer.

    python scripts/export_bedroom_glb.py --out out/bedroom.glb

Deploys the current source to the workstation the same way workstation.py
does (so src/archpipe/blender/presentation.py travels with build_scene.py),
runs Blender headless with --export-glb --no-render (no Cycles device is
touched, so this does not need the graphics lock other jobs share), and
fetches the resulting .glb back over the same ssh pipe used elsewhere.

This is a one-off viewing aid, not a pipeline stage: it does not go through
worker.cached_job, so it is not part of run_bedroom.py's acceptance record.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from render_remote import _ssh
from workstation import deploy, digest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="ai-workstation")
    ap.add_argument("--input", type=Path, default=ROOT / "out/bedroom-render.json")
    ap.add_argument("--out", type=Path, default=ROOT / "out/bedroom.glb")
    a = ap.parse_args()

    if not a.input.is_file():
        ap.error(f"{a.input} not found -- run scripts/make_render_input.py first")

    root, release, release_id = deploy(a.host)

    config = json.loads(_ssh(a.host, f'cat {shlex.quote(root)}/worker-environment.json').stdout)
    blender = config["blender"]

    data = a.input.read_bytes()
    input_id = digest(data)
    remote_input = f"{root}/inputs/{input_id}.json"
    if _ssh(a.host, f"mkdir -p {shlex.quote(root + '/inputs')}").returncode:
        raise RuntimeError("could not create remote input directory")
    if _ssh(a.host, f"cat > {shlex.quote(remote_input)}", stdin_bytes=data).returncode:
        raise RuntimeError("could not transfer the extract")

    remote_glb = f"{root}/inputs/{input_id}.glb"
    script = f"{release}/src/archpipe/blender/build_scene.py"
    cmd = (f"{shlex.quote(blender)} -b -t 8 --python-exit-code 1 -P {shlex.quote(script)} -- "
           f"--extract {shlex.quote(remote_input)} --export-glb {shlex.quote(remote_glb)} --no-render")
    result = _ssh(a.host, cmd, timeout=600)
    stdout = result.stdout.decode(errors="replace")
    if result.returncode != 0 or "SCENE wrote glb" not in stdout:
        print(stdout[-4000:] + result.stderr.decode(errors="replace")[-2000:], file=sys.stderr)
        raise RuntimeError(f"remote export failed (exit {result.returncode})")

    fetch = _ssh(a.host, f"cat {shlex.quote(remote_glb)}")
    if fetch.returncode != 0 or not fetch.stdout:
        raise RuntimeError("export succeeded but the .glb could not be fetched")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(fetch.stdout)
    print(f"{a.out}  ({len(fetch.stdout) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
