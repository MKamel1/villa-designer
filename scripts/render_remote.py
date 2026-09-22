"""Render an extract on ai-workstation's GPU, from the laptop.

The laptop authors (Revit, rules, drawings); the workstation renders.
Nothing binary crosses -- the extract is text and the scene is rebuilt at
the far end, so this works between Windows and Linux without a shared
filesystem or a file format negotiation (ADR-0003).

    python scripts/render_remote.py out/model.json --out render.png
    python scripts/render_remote.py out/model.json --samples 512 --cpu

Requires an ssh host alias (default `ai-workstation`) with key auth, and
Blender installed by `ops/workstation/10-blender.sh`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_HOST = "ai-workstation"
REMOTE_DIR = "$HOME/archpipe/scene"
REMOTE_BLENDER = "$HOME/opt/blender/blender"
SCENE_SCRIPT = Path(__file__).resolve().parents[1] / "src/archpipe/blender/build_scene.py"


class RenderError(RuntimeError):
    pass


def _ssh(host: str, command: str, stdin_bytes: bytes | None = None,
         capture: bool = True, timeout: int = 900) -> subprocess.CompletedProcess:
    argv = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, command]
    return subprocess.run(argv, input=stdin_bytes,
                          capture_output=capture, timeout=timeout)


def _push(host: str, local: Path, remote: str) -> None:
    """Copy a file by piping it over ssh.

    scp would work, but piping avoids depending on scp's path quoting
    behaving the same way from Git Bash, PowerShell and a Linux shell.
    """
    data = local.read_bytes()
    # Double quotes, not shlex.quote: these paths contain $HOME, and
    # single-quoting would send it to the shell as a literal. The paths
    # are module constants, not user input, so this is safe.
    res = _ssh(host, f'cat > "{remote}"', stdin_bytes=data)
    if res.returncode != 0:
        raise RenderError(f"failed to push {local.name}: "
                          f"{res.stderr.decode(errors='replace')[:300]}")


def render(extract: Path, out: Path, *, host: str = DEFAULT_HOST,
           samples: int = 128, resolution: str = "1280x720",
           gpu: bool = True, timeout: int = 900) -> dict:
    if not extract.is_file():
        raise RenderError(f"extract not found: {extract}")
    if not SCENE_SCRIPT.is_file():
        raise RenderError(f"scene script missing: {SCENE_SCRIPT}")

    _ssh(host, f"mkdir -p {REMOTE_DIR}")
    _push(host, SCENE_SCRIPT, f"{REMOTE_DIR}/build_scene.py")
    _push(host, extract, f"{REMOTE_DIR}/model.json")

    flags = f"--samples {samples} --res {resolution}" + ("" if gpu else " --cpu")
    cmd = (f"cd {REMOTE_DIR} && {REMOTE_BLENDER} -b -P build_scene.py -- "
           f"--extract model.json --out remote_render.png {flags}")

    started = time.monotonic()
    res = _ssh(host, cmd, timeout=timeout)
    elapsed = time.monotonic() - started
    stdout = res.stdout.decode(errors="replace")

    # Blender exits 0 on some scene errors, so trust the script's own
    # markers rather than the return code alone.
    scene_lines = [l.strip() for l in stdout.splitlines() if "SCENE" in l]
    if res.returncode != 0 or not any("wrote" in l for l in scene_lines):
        detail = "\n".join(scene_lines) or stdout[-800:]
        raise RenderError(f"remote render failed (exit {res.returncode}):\n{detail}")

    fetch = _ssh(host, f"cat {REMOTE_DIR}/remote_render.png")
    if fetch.returncode != 0 or not fetch.stdout:
        raise RenderError("render succeeded but the image could not be fetched")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(fetch.stdout)

    return {"out": out, "seconds": elapsed, "bytes": len(fetch.stdout),
            "log": scene_lines}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("extract", type=Path, help="model.json from the Revit extract")
    ap.add_argument("--out", type=Path, default=Path("out/render.png"))
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--cpu", action="store_true", help="force CPU rendering")
    args = ap.parse_args(argv)

    try:
        r = render(args.extract, args.out, host=args.host, samples=args.samples,
                   resolution=args.res, gpu=not args.cpu)
    except (RenderError, subprocess.TimeoutExpired) as e:
        print(f"RENDER ERROR: {e}", file=sys.stderr)
        return 1

    for line in r["log"]:
        print(f"  {line}")
    print(f"\n{r['out']}  ({r['bytes'] // 1024} KB, {r['seconds']:.1f}s "
          f"including transfer)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
