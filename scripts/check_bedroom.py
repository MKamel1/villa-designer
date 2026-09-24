"""Compare what Revit actually built against what the spec asked for.

    python scripts/check_bedroom.py

Closes the loop that matters: `spec/bedroom-test.yaml` -> Revit ->
`extract_model.py` -> here. Reports **achieved versus required**, never an
adjective (CLAUDE.md discipline 3).

Building the room is not the same as building the right room. Revit works
in decimal feet and a units error does not raise; a wall named wrongly
puts the window in a different elevation; a rotation dropped silently
turns a 1200 x 600 wardrobe into a 600 x 1200 one. Each of those produces
a model that opens perfectly and is wrong, so each is checked against a
number that was written down before the model existed.

Exit code is non-zero when anything disagrees, so this can gate a build.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOL_MM = 1.0          # far below drawing tolerance; we expect exact
TOL_M2 = 0.001


class Check:
    def __init__(self) -> None:
        self.rows: list[tuple[bool, str, str]] = []

    def eq(self, label: str, got, want, tol: float = TOL_MM) -> None:
        if got is None:
            self.rows.append((False, label, "missing -- expected %s" % (want,)))
            return
        if isinstance(want, (list, tuple)):
            ok = (len(got) == len(want)
                  and all(abs(float(a) - float(b)) <= tol for a, b in zip(got, want)))
            detail = "%s vs %s" % ([round(float(v), 1) for v in got], list(want))
        else:
            ok = abs(float(got) - float(want)) <= tol
            detail = "%.3f vs %.3f" % (float(got), float(want))
        self.rows.append((ok, label, detail))

    def true(self, label: str, ok: bool, detail: str = "") -> None:
        self.rows.append((bool(ok), label, detail))

    def note(self, label: str, detail: str = "") -> None:
        """A measured difference that is information, not a failure.

        Used where the spec holds an ASSUMPTION rather than an
        instruction: the footprint of a real family is whatever the
        manufacturer made it, so a mismatch is a finding to carry into the
        clearance checks, not a build error. Reported with both numbers,
        never as an adjective.
        """
        self.rows.append((None, label, detail))

    def report(self) -> int:
        bad = notes = 0
        for ok, label, detail in self.rows:
            if ok is None:
                notes += 1
                mark = "NOTE"
            elif ok:
                mark = "PASS"
            else:
                bad += 1
                mark = "FAIL"
            print("  %s  %-52s %s" % (mark, label, detail))
        print()
        print("  %d checks, %d failed, %d noted"
              % (len(self.rows) - notes, bad, notes))
        return bad


def nearest(items, at, tol=TOL_MM):
    """The item whose `at` matches, or None. Matching by position rather
    than by order, because the extract sorts by UniqueId and the spec does
    not."""
    for it in items:
        p = it.get("at")
        if p and len(p) >= 2 and abs(p[0] - at[0]) <= tol and abs(p[1] - at[1]) <= tol:
            return it
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", type=Path, default=ROOT / "spec/bedroom-test.yaml")
    ap.add_argument("--extract", type=Path,
                    default=ROOT / "out/bedroom-from-revit.json")
    a = ap.parse_args(argv)

    if not a.extract.is_file():
        print("No extract at %s -- run build_bedroom.py then extract_model.py"
              % a.extract)
        return 2

    spec = yaml.safe_load(a.spec.read_text(encoding="utf-8"))
    got = json.loads(a.extract.read_text(encoding="utf-8"))
    c = Check()
    rm = spec["room"]
    w, d, t = float(rm["width"]), float(rm["depth"]), float(rm["wall_thickness"])

    print("SPEC -> REVIT -> EXTRACT")
    print("  spec:    %s" % a.spec.name)
    print("  extract: %s" % a.extract.name)
    print()

    # ---- the room ------------------------------------------------------
    rooms = got.get("rooms") or []
    c.true("exactly one room extracted", len(rooms) == 1, "%d" % len(rooms))
    if rooms:
        room = rooms[0]
        c.eq("room area", room.get("area_m2"), w * d / 1e6, TOL_M2)
        c.true("room name carried through",
               room.get("name") == spec.get("name"),
               "%r vs %r" % (room.get("name"), spec.get("name")))
        b = room.get("boundary") or []
        if b:
            xs = [p[0] for p in b]
            ys = [p[1] for p in b]
            c.eq("room boundary width", max(xs) - min(xs), w)
            c.eq("room boundary depth", max(ys) - min(ys), d)

    # ---- walls ---------------------------------------------------------
    walls = got.get("walls") or []
    c.true("four walls", len(walls) == 4, "%d" % len(walls))
    lengths = sorted(round(
        ((x["end"][0] - x["start"][0]) ** 2 + (x["end"][1] - x["start"][1]) ** 2) ** 0.5, 3)
        for x in walls)
    c.eq("wall centreline lengths", lengths,
         sorted([d + t, d + t, w + t, w + t]))
    c.true("one wall thickness, as specified",
           {x.get("thickness") for x in walls} == {t},
           str({x.get("thickness") for x in walls}))

    # ---- openings ------------------------------------------------------
    for op in spec.get("openings", []):
        found = None
        for o in got.get("openings", []):
            if (o.get("kind") == op["kind"]
                    and abs(float(o.get("width") or 0) - float(op["width"])) <= TOL_MM):
                found = o
                break
        c.true("%s (%s) present" % (op["id"], op["kind"]), found is not None)
        if found:
            c.eq("  %s width" % op["id"], found.get("width"), op["width"])
            c.eq("  %s height" % op["id"], found.get("height"), op["height"])
            c.eq("  %s sill" % op["id"], found.get("sill"), op.get("sill") or 0)
            # `at` is measured along the wall centreline, which begins half
            # a thickness before the room's corner.
            c.eq("  %s position along its wall" % op["id"],
                 found.get("at"), float(op["at"]) + t / 2.0)

    # ---- furniture -----------------------------------------------------
    furn = got.get("furniture") or []
    c.true("every furniture item extracted",
           len(furn) == len(spec.get("furniture", [])),
           "%d of %d" % (len(furn), len(spec.get("furniture", []))))
    for fn in spec.get("furniture", []):
        item = nearest(furn, fn["at"])
        c.true("%s (%s) at its specified position" % (fn["id"], fn["type"]),
               item is not None, "" if item else "nothing at %s" % (fn["at"],))
        if item:
            actual_rotation = item.get('rotation')
            if '@' in item.get('type_name', ''):
                actual_rotation = float(item['type_name'].rsplit('@', 1)[1])
            want_rotation = float(fn.get('rotation') or 0)
            delta = None if actual_rotation is None else ((actual_rotation - want_rotation + 180) % 360 - 180)
            c.eq('  %s rotation error (degrees)' % fn['id'], delta, 0, 0.01)
            if (fn.get('proxy') or fn.get('detail')) and fn.get('height'):
                c.eq('  %s measured height' % fn['id'], (item.get('size_mm') or [0,0,None])[2], fn['height'])
            if fn.get('detail'):
                c.true('  %s has actual saved detailed meshes' % fn['id'],
                       bool(item.get('meshes')) and not item.get('is_proxy'))
        if item and item.get("size_mm") and fn.get("size"):
            # A rotation of 90 degrees swaps the plan footprint. Checking
            # the ROTATED size is the point: a dropped rotation is
            # invisible in the position and changes every clearance.
            rot = float(fn.get("rotation") or 0.0) % 180.0
            want = list(fn["size"])
            if abs(rot - 90.0) < 1.0:
                want = [want[1], want[0]]
            is_proxy = bool(fn.get("proxy") or fn.get('detail'))
            if is_proxy:
                # We built the box, so it must be exactly the size asked
                # for. Anything else is a build error.
                c.eq("  %s footprint (rotation applied)" % fn["id"],
                     item["size_mm"][:2], want, 2.0)
            else:
                # A real family is whatever the manufacturer made it. The
                # spec figure was an assumption, and the DIFFERENCE is the
                # thing worth knowing: a 555 mm chair checked against a
                # 500 mm assumption passes clearances it should not.
                act = item["size_mm"][:2]
                delta = [round(act[0] - want[0], 1), round(act[1] - want[1], 1)]
                if max(abs(delta[0]), abs(delta[1])) <= 2.0:
                    c.true("  %s footprint matches the assumed size" % fn["id"],
                           True, "%s" % ([round(v, 1) for v in act],))
                else:
                    c.note("  %s real family differs from the assumption"
                           % fn["id"],
                           "%s vs assumed %s  (delta %s mm) -- clearance "
                           "checks must use the real figure"
                           % ([round(v, 1) for v in act], want, delta))

    # ---- lighting ------------------------------------------------------
    lights = got.get("lighting") or []
    c.true("every luminaire extracted",
           len(lights) == len(spec.get("lighting", [])),
           "%d of %d" % (len(lights), len(spec.get("lighting", []))))
    for lt in spec.get("lighting", []):
        item = nearest(lights, lt["at"])
        c.true("%s (%s) at its specified position" % (lt["id"], lt.get("layer")),
               item is not None, "" if item else "nothing at %s" % (lt["at"],))
        if item:
            c.eq('  %s mounting height' % lt['id'], item.get('mounting_height'), lt['mounting_height'])
            actual_rotation = float(item.get('rotation') or 0)
            want_rotation = float(lt.get('rotation') or 0)
            c.eq('  %s rotation error' % lt['id'],
                 (actual_rotation-want_rotation+180)%360-180, 0, 0.01)
            vertices = [p for mesh in item.get('meshes',[])
                        if mesh.get('geometry_role') != 'light_source_symbol' for p in mesh['vertices_mm']]
            c.true('  %s has saved fixture geometry' % lt['id'], bool(vertices))
            if vertices:
                c.true('  %s housing fits inside room plan' % lt['id'],
                    min(p[0] for p in vertices)>=-TOL_MM and max(p[0] for p in vertices)<=w+TOL_MM and
                    min(p[1] for p in vertices)>=-TOL_MM and max(p[1] for p in vertices)<=d+TOL_MM)
        if item and lt.get("family"):
            stem = Path(lt["family"]).stem.lower()
            c.true("  %s is the family the spec named" % lt["id"],
                   (item.get("family") or "").lower() in stem
                   or stem.startswith((item.get("family") or "x").lower()),
                   item.get("family") or "-")

    bad = c.report()
    if bad:
        print("  The model Revit built does not match the spec.")
    else:
        print("  Revit built exactly what the spec asked for.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
