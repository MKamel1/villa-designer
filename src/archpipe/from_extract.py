"""Turn a Revit extract into a `Project`, so the rule engine can review it.

The rule library was written against `spec/*.yaml` models loaded by
`model.load`. Revit is now the source of truth (ADR-0001), so the review
has to run on what Revit actually contains rather than on a parallel YAML
copy of it -- otherwise the thing being reviewed is not the thing being
built.

WHAT THIS DOES NOT DO

It does not invent. Where the extract has no answer the field is left at
its declared default and the omission is reported, because a rule that
silently checks a made-up number is worse than a rule that does not run.
`convert()` returns the project and a list of notes; the caller is
expected to show them.

THE THREE JOINS THAT MATTER

*Occupancy.* Revit rooms carry a name, not an occupancy, and the rule
engine dispatches on occupancy -- minimum areas, privacy, daylight all
turn on it. The name is matched against `vocabulary`, and a room whose
name means nothing to us is reported rather than guessed at.

*Furniture type.* The catalogue keys on a type (`bed_double`), and the
model carries a family name or a proxy id. A proxy stamped by
`build_bedroom.py` has the spec id in its Mark, which maps straight back;
a real family is matched on its name, and failing that reported.

*Opening `at`.* The extract measures along the wall CENTRELINE from its
start point. `model.Opening.at` means the same thing, so this is a pass
through -- but it is the field most likely to be silently redefined by a
future change, so it is stated here.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import vocabulary as V
from .catalogue import get as _cat_get
from .model import (Furniture, Level, MaterialLayer, Opening, Project, Room,
                    SpecError, Wall, WallType)

# Room-name fragments that imply an occupancy. Deliberately small: the
# point is to recognise what a designer typed, not to build a
# classifier. Anything unmatched is reported, never guessed.
NAME_TO_OCCUPANCY = (
    ("bedroom", "bedroom"), ("bed ", "bedroom"), ("master", "bedroom"),
    ("living", "living"), ("lounge", "living"), ("sitting", "living"),
    ("kitchen", "kitchen"), ("dining", "dining"),
    ("bath", "bathroom"), ("shower", "bathroom"),
    ("wc", "wc"), ("toilet", "wc"), ("cloak", "wc"),
    ("study", "study"), ("office", "study"),
    ("hall", "hall"), ("corridor", "hall"), ("landing", "hall"),
    ("utility", "utility"), ("laundry", "utility"),
    ("store", "store"), ("closet", "store"), ("pantry", "store"),
    ("dress", "dressing"), ("garage", "garage"),
)

# Furniture type from a family or proxy name, same principle.
NAME_TO_FURNITURE = (
    ("bed_double", "bed_double"), ("bed_single", "bed_single"),
    ("double bed", "bed_double"), ("bed", "bed_double"),
    ("bedside", "bedside_table"), ("nightstand", "bedside_table"),
    ("wardrobe", "wardrobe"), ("closet", "wardrobe"),
    ("desk", "desk"), ("chair", "chair"), ("stool", "chair"),
    ("table", "table"), ("sofa", "sofa"), ("wc", "wc"), ("basin", "basin"),
)


def _match(name: str, table) -> str:
    """Longest matching needle wins.

    First-match-wins is wrong here and quietly so: "bedside_table" contains
    "bed", so a bedside table was classified as a double bed, inherited a
    1600 x 2000 footprint, and produced three overlap violations against
    furniture that does not overlap anything.
    """
    low = (name or "").lower()
    best, best_len = "", 0
    for needle, value in table:
        if needle in low and len(needle) > best_len:
            best, best_len = value, len(needle)
    return best


@dataclass
class Conversion:
    project: Project
    notes: list

    @property
    def ok(self) -> bool:
        return not self.notes


def convert(data: dict, *, name: str = "") -> Conversion:
    """Extract dict -> (Project, notes)."""
    notes = []
    units = data.get("units")
    if units != "mm":
        raise SpecError(f"extract declares units {units!r}; millimetres are required")

    levels, by_uid = [], {}
    for lv in data.get("levels", []):
        ident = lv.get("id") or f"L{len(levels)}"
        obj = Level(id=ident, name=lv.get("name") or ident,
                    elevation=float(lv.get("elevation") or 0.0),
                    height=float(lv.get("height") or 2700.0))  # falsy-ok: a 0 mm storey is not a valid level
        levels.append(obj)
        by_uid[ident] = obj
    if not levels:
        notes.append("extract carries no levels; a default was created")
        levels = [Level(id="L0", name="Level 0", elevation=0.0, height=2700.0)]
        by_uid = {"L0": levels[0]}

    def level_of(uid):
        return uid if uid in by_uid else levels[0].id

    # Wall types, synthesised from the thicknesses actually present. The
    # extract carries a type NAME and a thickness; the layer build-up is
    # not extracted, so a single unnamed layer stands in and the note says
    # so rather than implying a specification we do not have.
    wall_types, seen = [], {}
    extracted_types = {t['id']: t for t in data.get('wall_types', [])}
    for w in data.get("walls", []):
        t = float(w.get("thickness") or 100.0)  # falsy-ok: a 0 mm wall is not valid geometry
        key = w.get('type') or f"WT-{t:g}"
        if key in seen:
            continue
        tid = key
        seen[key] = tid
        source = extracted_types.get(key, {})
        layers = tuple(MaterialLayer(material=l.get('material') or 'unspecified',
                                     thickness=float(l['thickness']))
                       for l in source.get('layers', []))
        if not layers:
            notes.append(f"wall type {tid}: layer build-up unavailable")
        wall_types.append(WallType(
            id=tid, thickness=t,
            layers=layers or (MaterialLayer(material="unspecified", thickness=t),),
            bearing=bool(source.get('bearing')),
            description=source.get('name') or 'from measured wall thickness'))

    walls = []
    for w in data.get("walls", []):
        t = round(float(w.get("thickness") or 100.0), 3)  # falsy-ok: a 0 mm wall is not valid geometry
        walls.append(Wall(
            id=w["id"], level=level_of(w.get("level")),
            type=seen[w.get('type') or f"WT-{t:g}"],
            start=(float(w["start"][0]), float(w["start"][1])),
            end=(float(w["end"][0]), float(w["end"][1]))))

    openings = []
    for o in data.get("openings", []):
        if o.get("at") is None:
            notes.append(f"opening {o.get('id')} has no position along its "
                         f"host wall and was skipped")
            continue
        openings.append(Opening(
            id=o["id"], host=o.get("host") or "", kind=o.get("kind") or "door",
            width=float(o.get("width") or 0.0),
            height=float(o.get("height") or 0.0),
            at=float(o["at"]), sill=float(o.get("sill") or 0.0),
            family=o.get("family") or ""))

    rooms = []
    for r in data.get("rooms", []):
        occ = _match(r.get("name") or "", NAME_TO_OCCUPANCY)
        if not occ:
            notes.append(
                f"room {r.get('name')!r} has no recognisable occupancy; every "
                f"rule that dispatches on occupancy is silent for it")
        elif not V.is_known(occ):
            notes.append(f"occupancy {occ!r} is not in the vocabulary")
            occ = ""
        bound = tuple((float(p[0]), float(p[1])) for p in r.get("boundary", []))
        if len(bound) < 3:
            notes.append(f"room {r.get('name')!r} has no usable boundary")
            continue
        rooms.append(Room(id=r["id"], level=level_of(r.get("level")),
                          name=r.get("name") or r["id"], boundary=bound,
                          occupancy=occ))

    furniture = []
    for f in data.get("furniture", []) + data.get("casework", []):
        at = f.get("bbox_center_mm") or f.get("at")
        if not at:
            notes.append(f"furniture {f.get('mark') or f.get('id')} has no "
                         f"position and was skipped")
            continue
        # `type_name` first: a proxy carries "PROXY bed_double" there, which
        # names the catalogue type outright. The Mark is a spec id like
        # FN-BST-L and names nothing.
        label = " ".join(str(f.get(k) or "") for k in
                         ("type_name", "family", "mark"))
        metadata = f.get('archpipe') or {}
        ftype = metadata.get('type') or _match(label, NAME_TO_FURNITURE)
        if not ftype:
            notes.append(
                f"furniture {(f.get('mark') or f.get('id'))!r} "
                f"({(f.get('type_name') or f.get('family') or '?')!r}) does "
                f"not map to any catalogue type; its clearances are not "
                f"being checked")
            ftype = 'unclassified'
        try:
            _cat_get(ftype)
        except KeyError:
            # Knowing what a thing IS and having a published clearance for
            # it are different. Inventing a figure here is the exact fault
            # `catalogue.py` exists to prevent.
            notes.append(
                f"furniture {(f.get('mark') or f.get('id'))!r} is a "
                f"{ftype!r}, which has no published clearance in the "
                f"catalogue -- physical collisions are checked, but no "
                f"type-specific access requirement is invented")
        # Preserve measured dimensions. Reverse quarter turns below so
        # the Project does not rotate an already rotated footprint twice.
        size = f.get('size_mm')
        if not size or min(size[:2]) <= 0:
            raise SpecError(f"furniture {f.get('mark') or f['id']}: measured footprint missing")
        room_id = ""
        for r in rooms:
            xs = [p[0] for p in r.boundary]
            ys = [p[1] for p in r.boundary]
            if min(xs) <= at[0] <= max(xs) and min(ys) <= at[1] <= max(ys):
                room_id = r.id
                break
        # A DirectShape bakes its rotation into its geometry and reports
        # none, so the proxy's NAME carries it: "PROXY bed_double @180".
        # Without it the clearance sides -- front, back, left, right, which
        # are defined in the piece's own frame -- are unknowable, and a bed
        # with its headboard against a wall reads as one with its foot
        # against it.
        rot = float(f.get("rotation") or 0.0)
        tn = str(f.get("type_name") or "")
        if "@" in tn:
            try:
                rot = float(tn.rsplit("@", 1)[1].strip())
            except ValueError:
                notes.append(f"proxy {tn!r} has an unreadable rotation suffix")
        # Bounding boxes are measured in world axes. Undo only quarter
        # turns, for which the local rectangle is recoverable exactly.
        # An arbitrary rotated box cannot be recovered from its world box.
        if f.get('size_local_mm'):
            size = f['size_local_mm']
        elif abs(rot / 90.0 - round(rot / 90.0)) < 1e-5:
            if round(rot / 90.0) % 2:
                size = [size[1], size[0]]
        else:
            raise SpecError(f"furniture {f.get('mark') or f['id']}: rotation {rot:g} "
                            "needs measured size_local_mm, not a world bounding box")
        accessory = metadata.get('accessory_to') or ''
        if accessory:
            notes.append(f"{f.get('mark') or f['id']} is a declared accessory to "
                         f"{accessory}; its parent's access check allows it, "
                         "while physical collisions remain checked")
        furniture.append(Furniture(
            id=f.get("mark") or f["id"], level=level_of(f.get("level")),
            type=ftype, at=(float(at[0]), float(at[1])),
            rotation=rot,
            size=(float(size[0]), float(size[1])) if size else None,
            room=room_id, accessory_to=accessory))

    project = Project(
        name=name or (rooms[0].name if rooms else "from Revit"),
        levels=tuple(levels), wall_types=tuple(wall_types),
        walls=tuple(walls), openings=tuple(openings),
        rooms=tuple(rooms), furniture=tuple(furniture))
    project.validate()
    return Conversion(project=project, notes=notes)
