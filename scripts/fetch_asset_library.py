"""Deploy and run ops/workstation/fetch_asset_library.py on the workstation.

    python scripts/fetch_asset_library.py

Downloads the CC0 material/HDRI/prop set named in
ops/workstation/library-manifest.json directly onto the render workstation
(never routed through this machine) into a location OUTSIDE the versioned
release tree ($HOME/archpipe/assets/library), so it is fetched once and
persists across every future deploy rather than being re-uploaded with
every code change the way the small IES set is.
"""
from __future__ import annotations
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from render_remote import _ssh
from workstation import deploy


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "ai-workstation"
    root, release, release_id = deploy(host)
    manifest = f"{release}/ops/workstation/library-manifest.json"
    script = f"{release}/ops/workstation/fetch_asset_library.py"
    library = f"{root}/assets/library"
    cmd = f"python3 {shlex.quote(script)} {shlex.quote(manifest)} {shlex.quote(library)}"
    result = _ssh(host, cmd, timeout=1800)
    out = result.stdout.decode(errors="replace")
    err = result.stderr.decode(errors="replace")
    print(out)
    if result.returncode != 0:
        print(err, file=sys.stderr)
        raise SystemExit(result.returncode)
    if err.strip():
        print(err, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
