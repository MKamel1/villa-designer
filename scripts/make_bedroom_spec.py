"""Convert the bedroom spec from YAML to JSON for the Revit side.

    python scripts/make_bedroom_spec.py --out out/bedroom-spec.json

`spec/bedroom-test.yaml` stays the authored file. `revit/build_bedroom.py`
runs in IronPython 2.7 inside Revit, where PyYAML is not available, so it
reads JSON. This is a format conversion and nothing else -- no defaults are
invented here, because a value that appears in the JSON but not the YAML
would be a second place to author the design (ADR-0002).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ROOM = ("width", "depth", "ceiling_height", "wall_thickness")


def convert(src: Path) -> dict:
    spec = yaml.safe_load(src.read_text(encoding="utf-8"))
    room = spec.get("room") or {}
    missing = [k for k in REQUIRED_ROOM if room.get(k) is None]
    if missing:
        raise SystemExit(f"{src}: room is missing {', '.join(missing)}")

    # Openings are positioned along a named wall. A typo here would put the
    # hole in a different wall and every daylight figure downstream would
    # describe a different room, so the names are checked rather than
    # trusted.
    sides = {"north", "south", "east", "west"}
    for op in spec.get("openings", []):
        if op.get("host") not in sides:
            raise SystemExit(
                f"{src}: opening {op.get('id')} names host {op.get('host')!r}; "
                f"expected one of {', '.join(sorted(sides))}")
        if not (0 < float(op["at"]) < float(
                room["width"] if op["host"] in ("north", "south") else room["depth"])):
            raise SystemExit(
                f"{src}: opening {op.get('id')} at {op['at']} mm falls outside "
                f"its host wall")

    # Everything must sit inside the room. Catching it here is cheaper than
    # discovering it as a silently-misplaced element in Revit.
    for item in list(spec.get("furniture", [])) + list(spec.get("lighting", [])):
        x, y = item["at"]
        if not (0 <= x <= room["width"] and 0 <= y <= room["depth"]):
            raise SystemExit(
                f"{src}: {item.get('id')} at ({x}, {y}) is outside the "
                f"{room['width']} x {room['depth']} mm room")
    return spec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", type=Path,
                    default=ROOT / "spec/bedroom-test.yaml")
    ap.add_argument("--out", type=Path, default=ROOT / "out/bedroom-spec.json")
    a = ap.parse_args(argv)

    spec = convert(a.spec)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(spec, indent=2, sort_keys=True),
                     encoding="utf-8")
    r = spec["room"]
    print(f"{a.out}")
    print(f"  {r['width']} x {r['depth']} mm internal, ceiling "
          f"{r['ceiling_height']} mm, walls {r['wall_thickness']} mm")
    print(f"  {len(spec.get('openings', []))} openings, "
          f"{len(spec.get('furniture', []))} furniture, "
          f"{len(spec.get('lighting', []))} luminaires")
    return 0


if __name__ == "__main__":
    sys.exit(main())
