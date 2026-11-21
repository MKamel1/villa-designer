"""Fail if a lane branch writes outside the paths it owns (ops/lanes.yaml).

    python scripts/lane_guard.py L3            # compares HEAD with origin/integ/aplus
    python scripts/lane_guard.py L3 --base main

Exit 0 = clean, 1 = violation, 2 = usage/config error.
"""
from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_lanes() -> tuple[str, dict[str, list[str]]]:
    # Tiny parser for the fixed shape of ops/lanes.yaml (no PyYAML dependency).
    base, lanes, cur = "integ/aplus", {}, None
    for raw in (ROOT / "ops" / "lanes.yaml").read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("base:"):
            base = line.split(":", 1)[1].strip()
        elif line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            cur = line.strip()[:-1]
            lanes[cur] = []
        elif line.strip().startswith("- ") and cur:
            lanes[cur].append(line.strip()[2:].strip().strip('"'))
    return base, lanes


def allowed(path: str, globs: list[str], lane: str) -> bool:
    if path == f"docs/lessons/{lane}.md":
        return True
    for g in globs:
        if g.endswith("/**") and path.startswith(g[:-3] + "/"):
            return True
        if fnmatch.fnmatch(path, g):
            return True
    return False


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    lane = argv[0]
    base_cfg, lanes = load_lanes()
    base = argv[argv.index("--base") + 1] if "--base" in argv else f"origin/{base_cfg}"
    if lane not in lanes:
        print(f"unknown lane {lane!r}; known: {', '.join(lanes)}")
        return 2
    out = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                         cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stderr.strip())
        return 2
    bad = [p for p in out.stdout.split() if not allowed(p, lanes[lane], lane)]
    if bad:
        print(f"lane {lane} wrote outside its ownership ({len(bad)} files):")
        for p in bad:
            print(f"  {p}")
        return 1
    print(f"lane {lane}: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
