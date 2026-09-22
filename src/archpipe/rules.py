"""Design review: check an L0 spec against published planning dimensions.

This is the critic, and it is the honest version of "AI as architect".
It does not invent layouts. It checks a layout against figures that have
a source, and reports each failure with the rule, the number, the
citation and the consequence -- so the advice can be argued with rather
than taken on trust.

Every rule declares four things, per the Villa Design Method's "Rule
classification" section:

    stage      the EARLIEST stage at which the rule is meaningful, which
               in practice means the earliest stage at which the model
               carries what the rule reads. A rule that fires before its
               decision is being made is noise.
    severity   violation (breaks a published minimum) / warning
               (recognised planning fault) / advisory (comfort, taste).
    kind       computed (a measurable geometric test) or advisory (a
               prompt raised for judgement, NEVER reported as a
               measurement). These are independent axes: CIRC-02 is a
               computed test whose severity is advisory.
    reference  Neufert figure, Alexander pattern, or named published
               practice. Required. A `code` clause is optional and comes
               from a loaded jurisdiction pack (see `codes.py`); with no
               pack loaded, findings are guidance and say so.

...and a **fix ladder**: remedies ordered cheapest-first, where cheapest
means "forces the design back least far". Each remedy names the stage it
returns to and the loop id where one of the method's thirteen named loops
applies. This is the method's first thrash control: most failures are
fixable in-stage, and saying so prevents needless backtracking.

Findings carry model coordinates so they can be pinned on the review
sheet next to the thing they are about.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from shapely.geometry import Point as ShpPoint, Polygon
from shapely.ops import unary_union

from . import catalogue as cat
from . import vocabulary as vocab
from .codes import CodePack
from .model import Furniture, Opening, Project, Room, Wall

# The occupancy groups come from the shared vocabulary. They used to be
# four literal sets in this file, which is how `hall` came to be absent
# from CIRCULATION while the brief used it as its only circulation term.
HABITABLE = vocab.HABITABLE
PRIVATE = vocab.PRIVATE
SANITARY = vocab.SANITARY
CIRCULATION = vocab.CIRCULATION

# The eight stages of the Villa Design Method.
STAGES = {
    0: "Intent", 1: "Ground", 2: "Fit", 3: "Order",
    4: "Rooms", 5: "Systems", 6: "Substance", 7: "Proof",
}

# The thirteen named backward loops. A remedy that sends the design back
# cites one of these ids, so "go and change the brief" is a named,
# budgeted path rather than an improvised retreat. Transcribed from
# docs/method/villa-design-method.md.
LOOPS = {
    "L1":  "Furniture won't fit; clearance or door swing fails -- Rooms to Order",
    "L2":  "Rooms only work at sizes exceeding the footprint -- Rooms to Fit",
    "L3":  "Can't hit lux or layering in this room shape -- Systems to Rooms",
    "L4":  "Wet areas don't stack; drainage can't route -- Systems to Order",
    "L5":  "Massing exceeds setbacks or overshadows itself -- Order to Ground",
    "L6":  "Circulation costs more area than the allowance assumed -- Order to Fit",
    "L7":  "Brief does not fit the plot -- Fit to Intent",
    "L8":  "Wall build-up eats internal dimension -- Substance to Rooms",
    "L9":  "Material can't take the fixing or build-up -- Substance to Systems",
    "L10": "The feel is wrong although every number passes -- Systems to Rooms/Order",
    "L11": "Site defeats a briefed requirement -- Ground to Intent",
    "L12": "Documentation exposes an unresolved junction -- Proof to Substance",
    "L13": "Client changes their mind -- any to Intent",
}

KINDS = ("computed", "advisory")
SEVERITIES = ("violation", "warning", "advisory")


@dataclass(frozen=True)
class Remedy:
    """One rung of a fix ladder.

    `returns_to` is the stage the design has to go back to. None means the
    remedy is available inside the stage that found the problem, which is
    the cheapest thing a finding can say.
    """
    action: str
    returns_to: int | None = None
    loop: str = ""
    cost: str = ""

    def __post_init__(self) -> None:
        if not self.action:
            raise ValueError("a remedy needs an action")
        if self.returns_to is not None and self.returns_to not in STAGES:
            raise ValueError(f"remedy {self.action!r}: stage {self.returns_to} "
                             f"is not one of {sorted(STAGES)}")
        if self.loop and self.loop not in LOOPS:
            raise ValueError(f"remedy {self.action!r}: {self.loop!r} is not a "
                             f"named loop ({', '.join(LOOPS)})")

    @property
    def rank(self) -> int:
        """Cost rank. 0 is in-stage; returning further back costs more."""
        return 0 if self.returns_to is None else 8 - self.returns_to

    @property
    def scope(self) -> str:
        if self.returns_to is None:
            return "in-stage"
        where = f"-> Stage {self.returns_to} ({STAGES[self.returns_to]})"
        return f"{where}, {self.loop}" if self.loop else where


@dataclass(frozen=True)
class Rule:
    """A rule's declaration, separate from the function that runs it.

    Holding this apart from the check means every finding can be stamped
    with stage, kind, reference and ladder from one place, so those cannot
    be forgotten on a new rule or drift between two findings of the same
    rule.
    """
    id: str
    title: str
    stage: int
    kind: str
    reference: str
    remedies: tuple = ()
    note: str = ""

    def __post_init__(self) -> None:
        if self.stage not in STAGES:
            raise ValueError(f"rule {self.id}: stage {self.stage} is not 0-7")
        if self.kind not in KINDS:
            raise ValueError(f"rule {self.id}: kind {self.kind!r} not one of "
                             f"{', '.join(KINDS)}")
        if not self.reference:
            raise ValueError(
                f"rule {self.id}: a rule must cite a reference. The framework "
                f"is ours; the standards never are.")
        if not self.remedies:
            raise ValueError(
                f"rule {self.id}: a finding with no fix ladder tells the "
                f"reader they have a problem and not what it costs to fix.")
        last = -1
        for r in self.remedies:
            if r.returns_to is not None and r.returns_to > self.stage:
                raise ValueError(
                    f"rule {self.id}: remedy returns to Stage {r.returns_to}, "
                    f"which is later than the rule's own Stage {self.stage}. "
                    f"A ladder goes backwards.")
            if r.rank < last:
                raise ValueError(
                    f"rule {self.id}: fix ladder is not cheapest-first -- "
                    f"{r.action!r} forces the design back further than the "
                    f"rung above it.")
            last = r.rank

    @property
    def stage_label(self) -> str:
        return f"Stage {self.stage} ({STAGES[self.stage]})"


@dataclass(frozen=True)
class Measured:
    """An achieved-versus-required pair, kept as numbers rather than prose.

    The project's standing instruction is to report "350 mm clear where 450
    is needed", never "a bit tight". Holding the pair structurally means a
    finding can be checked for honesty: an `advisory` rule is forbidden
    from carrying one at all, because a judgement prompt that arrives with
    a number attached reads as a measurement and is not one.
    """
    achieved: float
    required: float
    unit: str = "mm"

    def _fmt(self, v: float) -> str:
        return f"{v:.2f}" if self.unit == "m2" else f"{v:.0f}"

    def __str__(self) -> str:
        return (f"{self._fmt(self.achieved)} {self.unit} achieved, "
                f"{self._fmt(self.required)} {self.unit} required")

    @property
    def shortfall(self) -> float:
        return self.required - self.achieved


@dataclass
class Finding:
    rule: str
    severity: str          # violation | warning | advisory
    message: str
    where: str = ""        # room / wall / furniture id
    at: tuple | None = None   # (x, y) model mm, for pinning
    # Stamped from the rule's declaration by `_finding`, never by hand.
    reference: str = ""
    code: str = ""         # from a loaded jurisdiction pack; "" when none
    stage: int = -1
    kind: str = ""
    remedies: tuple = ()
    measured: Measured | None = None

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.rule}: unknown severity {self.severity!r}")
        if self.stage not in STAGES:
            raise ValueError(f"{self.rule}: finding carries no valid stage")
        if self.kind not in KINDS:
            raise ValueError(f"{self.rule}: finding carries no valid kind")
        if not self.reference:
            raise ValueError(f"{self.rule}: finding carries no reference")
        if not self.remedies:
            raise ValueError(f"{self.rule}: finding carries no fix ladder")
        if self.kind == "advisory" and self.measured is not None:
            raise ValueError(
                f"{self.rule}: an advisory finding must not carry a "
                f"measurement. Alexander's qualitative patterns forced into "
                f"pass/fail produce confident nonsense; that is what the "
                f"advisory kind exists to prevent.")

    @property
    def source(self) -> str:
        """The full citation: the reference, plus a code clause if one applies.

        Kept as the name the review sheet and the CLI already read, so the
        split into `reference` + `code` did not change what they print.
        """
        return f"{self.reference}\nCode: {self.code}" if self.code else self.reference

    @property
    def stage_label(self) -> str:
        return f"Stage {self.stage} ({STAGES[self.stage]})"

    def ladder_lines(self) -> list[str]:
        """The fix ladder as numbered lines, cheapest first."""
        out = []
        for i, r in enumerate(self.remedies, 1):
            line = f"{i}. {r.action}  [{r.scope}]"
            if r.cost:
                line += f"\n     cost: {r.cost}"
            out.append(line)
        return out

    def as_note(self, author: str = "Claude (design review)", level: str = "",
                created: str | None = None, room_name: str = "") -> dict:
        """Shape this finding as a review-sheet note row.

        `created` and `level` are not decoration: the sheet orders notes by
        `created` and scopes storage by `level`, so a row without them sorts
        unpredictably and can land in the wrong level's list.

        `stage`, `kind` and `remedies` are added as new keys; the keys the
        viewer already reads are untouched.
        """
        from datetime import datetime, timezone
        ladder = "\n".join(self.ladder_lines())
        return {
            "x": round(self.at[0]) if self.at else 0,
            "y": round(self.at[1]) if self.at else 0,
            "room": room_name or self.where,
            "roomId": self.where,
            "level": level,
            "author": author,
            "created": created or datetime.now(timezone.utc).isoformat(),
            "resolved": False,
            "rule": self.rule,
            "severity": self.severity,
            "stage": self.stage,
            "kind": self.kind,
            "remedies": [
                {"action": r.action, "returns_to": r.returns_to,
                 "loop": r.loop, "cost": r.cost, "scope": r.scope}
                for r in self.remedies
            ],
            "text": (f"[{self.severity.upper()} / {self.rule} / "
                     f"{self.stage_label} / {self.kind}] {self.message}\n"
                     f"Source: {self.source}\n"
                     f"Fix ladder (cheapest first):\n{ladder}"),
        }


def _finding(rule_id: str, severity: str, message: str, *, where: str = "",
             at=None, reference: str | None = None,
             measured: Measured | None = None) -> Finding:
    """Build a finding, stamping stage / kind / reference / ladder from the rule.

    `reference` overrides only to name a MORE specific figure from the same
    source -- the catalogue entry for the actual piece of furniture, say,
    rather than the rule's general citation. The rule always carries one,
    so a finding can never end up uncited.
    """
    r = RULES[rule_id]
    return Finding(
        rule=rule_id, severity=severity, message=message, where=where, at=at,
        reference=reference or r.reference, stage=r.stage, kind=r.kind,
        remedies=r.remedies, measured=measured,
    )


# --------------------------------------------------------------------------
# The rule declarations.
#
# STAGE ASSIGNMENT. The stage is the earliest stage at which the rule is
# meaningful -- which in practice is the earliest stage at which the model
# carries what the rule reads. Most are settled by the method document
# itself: its Stage 4 (Rooms) rule list names "minimum areas and
# proportion; furniture fit; clearance achieved-versus-required; furniture
# overlap; door swing arcs; circulation width by erosion; door clear
# widths; glazing ratio". Those are AREA-01, DIM-01, FURN-01/02/03,
# DOOR-01, DOOR-02, CIRC-03 and LIGHT-01, cited rather than judged.
#
# The Stage 3 (Order) three are sanitary provision, private-rooms-off-
# living and the entrance sequence: concept decisions, owned by the stage
# that decides zoning, the intimacy gradient and the circulation spine.
#
# FIX LADDERS are per rule, because the remedies genuinely differ: a door
# that cannot swing can be rehung on the other jamb, which is meaningless
# for a room that cannot get enough daylight. Rungs are ordered by how far
# back they force the design, and a rung that names no loop names none
# because the method has no loop for that path -- inventing one would be
# the same fault as inventing a clause number.
# --------------------------------------------------------------------------

_NEUFERT = "Neufert, Architects' Data"

RULES: dict[str, Rule] = {r.id: r for r in (
    # ---- Stage 3 (Order): the concept decisions ------------------------
    Rule(
        "SAN-01", "Sanitary accommodation present on the level", 3, "computed",
        f"{_NEUFERT} -- dwelling schedule: every dwelling requires sanitary "
        f"accommodation; near-universal code requirement",
        note="Stage 3, not Stage 4: whether a level has a WC at all is a "
             "zoning decision, settled when the plan's zones are set and "
             "before any room is dimensioned.",
        remedies=(
            Remedy("Subdivide, or borrow a corner from the largest room, to "
                   "form a WC compartment on this level.",
                   cost="1.4 m2 with a 700 mm door is the published minimum, "
                        "so it usually comes out of a circulation run or the "
                        "end of a large room."),
            Remedy("Re-zone the level so the wet rooms sit where a drainage "
                   "stack can serve them.",
                   cost="Still in-stage, Stage 3 owning zoning -- but it "
                        "re-opens the wet-area stacking decision that L4, the "
                        "method's most expensive loop, exists to catch early."),
            Remedy("Recompute feasibility: the level's area allowance did not "
                   "carry its sanitary provision.", 2, "L6",
                   cost="Order to Fit. L6 is the method's named path for an "
                        "area allowance that proves wrong at Stage 3."),
            Remedy("Change the brief so this level's use does not require its "
                   "own sanitary accommodation.", 0, "L7",
                   cost="The dwelling still needs one WC and one bathing "
                        "facility somewhere; this only moves which level "
                        "carries them."),
        ),
    ),
    Rule(
        "CIRC-01", "Private rooms not reached through a living space", 3,
        "computed",
        "Alexander, A Pattern Language -- 127 Intimacy Gradient; "
        f"{_NEUFERT} -- circulation: 900 mm minimum clear width in a dwelling",
        note="The intimacy gradient is a Stage 3 pattern and Stage 3 owns the "
             "circulation spine, decided before rooms are placed.",
        remedies=(
            Remedy("Insert a hall or lobby between the living space and the "
                   "private room.",
                   cost="Stage 3 is where this costs least; after the rooms "
                        "are dimensioned it costs walls."),
            Remedy("Re-zone so the private room opens off circulation that "
                   "already exists.",
                   cost="Free if the plan has a spine; this is what having "
                        "one is for."),
            Remedy("Recompute feasibility: a hall costs area the allowance "
                   "may not have carried.", 2, "L6",
                   cost="L6 exactly -- circulation costing more area than the "
                        "allowance assumed."),
        ),
    ),
    Rule(
        "CIRC-02", "Entrance has a threshold zone", 3, "computed",
        "Alexander, A Pattern Language -- 110 Main Entrance, 112 Entrance "
        "Transition, 130 Entrance Room; "
        f"{_NEUFERT} -- entrances: a draught lobby or threshold zone",
        note="Severity advisory, kind computed: whether the entrance opens "
             "into a circulation space is a topological test on the model, "
             "even though the consequence is comfort rather than a minimum.",
        remedies=(
            Remedy("Form a threshold zone inside the entrance with a screen, "
                   "a return wall or a coat run.",
                   cost="No extra room, and it buys back the shoes, coats and "
                        "keys problem."),
            Remedy("Add an entrance room or vestibule proper.",
                   cost="Costs a room's worth of area on the level."),
            Remedy("Recompute feasibility: a vestibule is circulation area "
                   "the allowance may not carry.", 2, "L6"),
        ),
    ),

    # ---- Stage 4 (Rooms): the method doc names each of these -----------
    Rule(
        "AREA-01", "Room meets its minimum floor area", 4, "computed",
        f"{_NEUFERT} -- minimum floor areas by room type",
        note="Meaningful against brief targets as early as Stage 2, but the "
             "implemented rule reads Room.area_m2 off a drawn polygon, which "
             "does not exist until Stage 4.",
        remedies=(
            Remedy("Swap the room's use with a larger room on the same level.",
                   cost="No wall moves; only the schedule changes."),
            Remedy("Move the partition, taking area from an adjoining room "
                   "that has surplus.", 3, "L1",
                   cost="Order owns wall position, so this re-opens the "
                        "zoning it was set by."),
            Remedy("Recompute feasibility: the rooms need more area than the "
                   "footprint allows.", 2, "L2",
                   cost="L2's own remedy -- the storey count, or the brief."),
        ),
    ),
    Rule(
        "DIM-01", "Habitable room is wide enough to be usable", 4, "computed",
        "General practice: below ~2.4 m a room will not take a bed plus "
        "circulation",
        remedies=(
            Remedy("Re-assign the use: a narrow room works as a store or "
                   "utility where it will not work as a habitable room.",
                   cost="The brief loses a habitable room unless another "
                        "takes its place."),
            Remedy("Move the partition to widen the room.", 3, "L1",
                   cost="The adjoining room loses the width."),
            Remedy("Recompute feasibility: if widening this room narrows its "
                   "neighbour below the same minimum, the plan depth is wrong "
                   "for this room count.", 2, "L2"),
        ),
    ),
    Rule(
        "DOOR-01", "Door clear width", 4, "computed",
        f"{_NEUFERT} -- doors: clear opening widths by room type",
        note="Only two rungs, and that is the honest length. A door is a "
             "component before it is a decision.",
        remedies=(
            Remedy("Widen the leaf to the required clear width.",
                   cost="A door schedule change; nothing else in the plan "
                        "moves."),
            Remedy("Move the opening, or the wall, where the wall cannot "
                   "carry a wider opening.", 3, "L1",
                   cost="Structure, a wall return or a stack is the usual "
                        "reason it cannot."),
        ),
    ),
    Rule(
        "FURN-01", "Furniture fits where it is placed", 4, "computed",
        f"Geometric clash against the wall solid; footprints from {_NEUFERT}",
        remedies=(
            Remedy("Move or rotate the piece clear of the wall."),
            Remedy("Specify a smaller piece.",
                   cost="The catalogue footprint is a published standard "
                        "size, not this project's choice -- changing it means "
                        "buying to a dimension."),
            Remedy("Resize the room or move the wall, if nothing fits against "
                   "any wall.", 3, "L1"),
        ),
    ),
    Rule(
        "FURN-02", "Furniture clearance achieved versus required", 4,
        "computed",
        f"{_NEUFERT} -- clearances by furniture type",
        note="The method document's own worked example of a fix ladder.",
        remedies=(
            Remedy("Move the furniture.",
                   cost="The clearance is blocked by something placed, not by "
                        "the room. Most clearance failures end here."),
            Remedy("Resize the room, or move the wall.", 3, "L1",
                   cost="Re-opens the zoning and the wall positions Stage 3 "
                        "settled."),
            Remedy("Change the brief: fewer or smaller pieces in this room.",
                   0, "L7",
                   cost="The most expensive rung, and the right one when the "
                        "room is being asked to hold more than it can."),
        ),
    ),
    Rule(
        "FURN-03", "Two pieces do not occupy the same floor", 4, "computed",
        f"Geometric clash between footprints; footprints from {_NEUFERT}",
        remedies=(
            Remedy("Move one of the two pieces.",
                   cost="Both are placements; nothing else is implicated."),
            Remedy("Drop one of them.",
                   cost="The room cannot hold both at their published sizes."),
            Remedy("Make the room bigger, if it genuinely has to hold both.",
                   3, "L1"),
        ),
    ),
    Rule(
        "DOOR-02", "Door leaf can swing", 4, "computed",
        f"{_NEUFERT} -- doors: the leaf must open through 90 degrees",
        note="Its second rung is unique to doors, which is why ladders are "
             "per rule: rehanging a leaf fixes nothing about daylight.",
        remedies=(
            Remedy("Move the furniture out of the arc."),
            Remedy("Rehang the leaf on the other jamb, or reverse the swing.",
                   cost="A door schedule change, not a plan change."),
            Remedy("Move the opening, or enlarge the room.", 3, "L1"),
        ),
    ),
    Rule(
        "LIGHT-01", "Glazing area against floor area", 4, "computed",
        f"{_NEUFERT} -- daylight: glazing area at least 1/8 of floor area in "
        f"habitable rooms",
        note="Stage 3 owns 'every habitable room has a daylight-capable "
             "aspect'; that rule is not implemented. What IS implemented is "
             "the 1/8 glazing ratio, which needs window sizes and so cannot "
             "fire before Stage 4.",
        remedies=(
            Remedy("Enlarge the window, or add a second one on the same "
                   "external wall."),
            Remedy("Swap the room with one that needs less daylight: which "
                   "room gets which aspect is a Stage 3 decision.", 3, "L1",
                   cost="Re-opens the response to orientation."),
            Remedy("Change the footprint shape: a plan too deep for daylight "
                   "to reach is a Stage 2 problem, not a window problem.",
                   2, "L2",
                   cost="Alexander 107 Wings of Light, which the method puts "
                        "at Stage 2 for this reason."),
        ),
    ),
    Rule(
        "CIRC-03", "A route of minimum width connects the room's doors", 4,
        "computed",
        f"{_NEUFERT} -- circulation: 900 mm minimum clear width in a dwelling",
        remedies=(
            Remedy("Move the furniture to open a route between the doors."),
            Remedy("Remove a piece.",
                   cost="The room is carrying more furniture than its floor "
                        "can route around."),
            Remedy("Move a door so the route does not cross the furniture "
                   "zone.", 3, "L1"),
            Remedy("Recompute feasibility: the room must carry both the "
                   "furniture and the route, and the circulation allowance "
                   "did not.", 2, "L6"),
        ),
    ),
    Rule(
        "VIEW-01", "Whether a window frames a view worth keeping", 4,
        "advisory",
        "Alexander, A Pattern Language -- 134 Zen View",
        note="The method document names 134 as its example of a pattern that "
             "must never be presented as measured: whether an outlook is "
             "worth framing is a judgement about a place, and no number in "
             "this model decides it. Fires once per level as a prompt, "
             "carries no measurement, and cannot fail.",
        remedies=(
            Remedy("Walk the windows on site, or in the model, and decide "
                   "room by room which outlook is worth framing and which is "
                   "worth screening.",
                   cost="Judgement, not arithmetic. This rung is the answer "
                        "in almost every case."),
            Remedy("Change which room gets which aspect, if a room worth a "
                   "view does not have one.", 3, "L1",
                   cost="Aspect is a Stage 3 decision, not a window size."),
            Remedy("Record it as a site fact instead: if no aspect carries a "
                   "view worth framing, the answer is to screen.", 1, "",
                   cost="Returns to Stage 1, where views to keep and to "
                        "screen are captured. The method names no loop for "
                        "Rooms to Ground, so this rung names none."),
        ),
    ),
)}


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------
def _room_poly(r: Room) -> Polygon:
    return Polygon(r.boundary)


def _wall_poly(p: Project, w: Wall) -> Polygon:
    t = p.wall_type(w.type).thickness
    left, right = w.face_offsets(t)
    L = w.length
    return Polygon([w.point_at(0, left), w.point_at(L, left),
                    w.point_at(L, right), w.point_at(0, right)])


def _walls_solid(p: Project, level: str):
    return unary_union([_wall_poly(p, w) for w in p.walls if w.level == level])


def _furniture_size(f: Furniture) -> tuple[float, float]:
    if f.size:
        return f.size
    t = cat.get(f.type)
    return (t.width, t.depth)


def _furniture_poly(f: Furniture) -> Polygon:
    w, d = _furniture_size(f)
    return Polygon(f.corners(w, d))


def room_containing(p: Project, x: float, y: float, level: str) -> Room | None:
    pt = ShpPoint(x, y)
    for r in p.rooms:
        if r.level == level and _room_poly(r).contains(pt):
            return r
    return None


def opening_sides(p: Project, o: Opening) -> tuple[Room | None, Room | None]:
    """The rooms either side of an opening. None means outside."""
    w = p.wall(o.host)
    t = p.wall_type(w.type).thickness
    probe = t / 2 + 150      # just clear of the wall face
    a = w.point_at(o.at, probe)
    b = w.point_at(o.at, -probe)
    return (room_containing(p, a[0], a[1], w.level),
            room_containing(p, b[0], b[1], w.level))


def opening_centre(p: Project, o: Opening) -> tuple[float, float]:
    return p.wall(o.host).point_at(o.at, 0)


def _min_area_key(occ: str) -> str | None:
    """The catalogue's minimum-area key for an occupancy, or None.

    None is the correct answer for most terms. A hall, a utility, a store,
    a dressing room and a garage are all declared occupancies with no
    published minimum area in Neufert, and inventing one so the table looks
    complete is exactly the failure this project exists to avoid. Being a
    known term and having a minimum are different things.
    """
    if occ in cat.MIN_AREA_M2:
        return occ
    return None


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------
def r_sanitary_present(p: Project, level: str) -> list[Finding]:
    rooms = [r for r in p.rooms if r.level == level]
    if any(r.occupancy in SANITARY for r in rooms):
        return []
    # Put the pin in the largest room, where the space would have to come from.
    biggest = max(rooms, key=lambda r: r.area_m2, default=None)
    return [_finding(
        "SAN-01", "violation",
        "No bathroom or WC on this level. A dwelling needs at least one WC and "
        "one bathing facility, and the WC must be reachable without passing "
        "through a bedroom.",
        where=biggest.id if biggest else "",
        at=biggest.centroid if biggest else None,
    )]


def r_room_min_area(p: Project, level: str) -> list[Finding]:
    out = []
    for r in (r for r in p.rooms if r.level == level):
        key = _min_area_key(r.occupancy)
        if not key:
            continue
        need, src = cat.MIN_AREA_M2[key]
        if r.area_m2 + 1e-6 < need:
            out.append(_finding(
                "AREA-01", "violation",
                f"{r.name} is {r.area_m2:.1f} m2, below the {need:.1f} m2 minimum "
                f"for a {r.occupancy}. It is short by {need - r.area_m2:.1f} m2.",
                where=r.id, at=r.centroid, reference=src,
                measured=Measured(r.area_m2, need, "m2"),
            ))
    return out


def r_room_min_width(p: Project, level: str) -> list[Finding]:
    need, src = cat.PLANNING["room_min_width"]
    out = []
    for r in (r for r in p.rooms if r.level == level):
        if r.occupancy not in HABITABLE:
            continue
        xs = [pt[0] for pt in r.boundary]
        ys = [pt[1] for pt in r.boundary]
        narrow = min(max(xs) - min(xs), max(ys) - min(ys))
        if narrow + 1e-6 < need:
            out.append(_finding(
                "DIM-01", "warning",
                f"{r.name} is only {narrow:.0f} mm across at its narrowest. "
                f"Below {need:.0f} mm a habitable room will not take furniture "
                f"plus a circulation route.",
                where=r.id, at=r.centroid, reference=src,
                measured=Measured(narrow, need, "mm"),
            ))
    return out


def r_door_clear_width(p: Project, level: str) -> list[Finding]:
    out = []
    for o in p.openings:
        w = p.wall(o.host)
        if w.level != level or o.kind != "door":
            continue
        a, b = opening_sides(p, o)
        external = a is None or b is None
        target = [r for r in (a, b) if r is not None]
        occ = target[0].occupancy if target else ""
        if external:
            need, src = cat.PLANNING["door_clear_entrance"]
            label = "a dwelling entrance"
        elif occ in ("wc", "bathroom", "shower_room"):
            need, src = cat.PLANNING["door_clear_wc"]
            label = "a WC or bathroom"
        else:
            need, src = cat.PLANNING["door_clear_habitable"]
            label = "a habitable room"
        if o.width + 1e-6 < need:
            out.append(_finding(
                "DOOR-01", "violation",
                f"Door {o.id} is {o.width:.0f} mm wide, below the {need:.0f} mm "
                f"minimum for {label}.",
                where=o.id, at=opening_centre(p, o), reference=src,
                measured=Measured(o.width, need, "mm"),
            ))
    return out


def r_private_room_access(p: Project, level: str) -> list[Finding]:
    """A bedroom or bathroom reached only through a living space."""
    out = []
    for r in (r for r in p.rooms if r.level == level and r.occupancy in PRIVATE):
        doors = []
        for o in p.openings:
            if o.kind != "door" or p.wall(o.host).level != level:
                continue
            a, b = opening_sides(p, o)
            if a is r or b is r:
                other = b if a is r else a
                doors.append((o, other))
        if not doors:
            continue
        via_habitable = [
            (o, other) for o, other in doors
            if other is not None and other.occupancy in (HABITABLE - {"bedroom"})
        ]
        via_circulation = [
            (o, other) for o, other in doors
            if other is not None and other.occupancy in CIRCULATION
        ]
        if via_habitable and not via_circulation:
            other = via_habitable[0][1]
            out.append(_finding(
                "CIRC-01", "warning",
                f"{r.name} is entered directly from {other.name}. With no hall, "
                f"the living space doubles as a circulation route: anyone reaching "
                f"{r.name} crosses it, which costs privacy, acoustic separation and "
                f"usable furniture wall.",
                where=r.id, at=opening_centre(p, via_habitable[0][0]),
            ))
    return out


def r_entrance_vestibule(p: Project, level: str) -> list[Finding]:
    out = []
    for o in p.openings:
        w = p.wall(o.host)
        if o.kind != "door" or w.level != level:
            continue
        a, b = opening_sides(p, o)
        if (a is None) == (b is None):
            continue                      # not an external door
        inner = a or b
        if inner is None:
            continue
        if inner.occupancy in CIRCULATION:
            continue
        out.append(_finding(
            "CIRC-02", "advisory",
            f"The entrance opens straight into {inner.name} with no vestibule or "
            f"threshold zone. There is nowhere for shoes, coats and keys, the room "
            f"is exposed to the door on opening, and heat is lost directly from the "
            f"main space.",
            where=inner.id, at=opening_centre(p, o),
        ))
    return out


def r_furniture_fits(p: Project, level: str) -> list[Finding]:
    """Footprint clashes with a wall, or falls outside every room."""
    out = []
    solid = _walls_solid(p, level)
    for f in (f for f in p.furniture if f.level == level):
        poly = _furniture_poly(f)
        t = cat.CATALOGUE.get(f.type)
        label = t.label if t else f.type
        if solid and poly.intersects(solid):
            overlap = poly.intersection(solid).area / 1e6
            if overlap > 1e-4:
                out.append(_finding(
                    "FURN-01", "violation",
                    f"{label} ({f.id}) overlaps a wall by {overlap:.2f} m2. "
                    f"It does not fit where it is placed.",
                    where=f.id, at=f.at,
                    reference=t.source if t else RULES["FURN-01"].reference,
                ))
    return out


def r_furniture_overlap(p: Project, level: str) -> list[Finding]:
    """Two pieces occupying the same floor. Checked separately from walls
    because a plan can look plausible while two items sit on top of each
    other -- and a blocked-clearance warning would otherwise mask it."""
    out = []
    pieces = [(f, _furniture_poly(f)) for f in p.furniture if f.level == level]
    for i in range(len(pieces)):
        for j in range(i + 1, len(pieces)):
            (fa, pa), (fb, pb) = pieces[i], pieces[j]
            hit = pa.intersection(pb)
            if hit.is_empty or hit.area <= 1000:
                continue
            la = cat.CATALOGUE.get(fa.type)
            lb = cat.CATALOGUE.get(fb.type)
            out.append(_finding(
                "FURN-03", "violation",
                f"{la.label if la else fa.type} ({fa.id}) and "
                f"{lb.label if lb else fb.type} ({fb.id}) overlap by "
                f"{hit.area / 1e6:.2f} m2. Two pieces cannot occupy the same floor.",
                where=f"{fa.id}/{fb.id}", at=hit.centroid.coords[0],
            ))
    return out


def _clearance_gap(f: Furniture, poly: Polygon, side: str, w: float, d: float,
                   amount: float, solid, others):
    """How much clear space a side actually has, and what is taking it.

    Returns (achieved_mm, blockers) or None when the side is unobstructed.
    Reporting the achieved gap matters: "350 mm where 450 is needed" is
    actionable, "blocked" is not.
    """
    rect = f.clearance_rect(side, w, d, amount)
    if not rect:
        return None
    zone = Polygon(rect)
    obstacles, blockers = [], []
    if solid is not None and not solid.is_empty:
        hit = zone.intersection(solid)
        if not hit.is_empty and hit.area > 1000:      # ignore hairline touches
            obstacles.append(hit)
            blockers.append("a wall")
    if others is not None and not others.is_empty:
        hit = zone.intersection(others)
        if not hit.is_empty and hit.area > 1000:
            obstacles.append(hit)
            blockers.append("other furniture")
    if not obstacles:
        return None
    achieved = min(poly.distance(o) for o in obstacles)
    return achieved, blockers, zone


def r_furniture_clearance(p: Project, level: str) -> list[Finding]:
    """The free space a piece needs is blocked by a wall or another piece."""
    out = []
    solid = _walls_solid(p, level)
    pieces = [(f, _furniture_poly(f)) for f in p.furniture if f.level == level]
    for f, poly in pieces:
        t = cat.CATALOGUE.get(f.type)
        if not t:
            continue
        w, d = _furniture_size(f)
        others = unary_union([q for g, q in pieces if g.id != f.id]) if len(pieces) > 1 else None

        for side, amount in t.clearance.items():
            got = _clearance_gap(f, poly, side, w, d, amount, solid, others)
            if not got:
                continue
            achieved, blockers, zone = got
            if achieved + 1 >= amount:
                continue
            out.append(_finding(
                "FURN-02", "warning",
                f"{t.label} ({f.id}) has {achieved:.0f} mm clear to its {side} "
                f"where {amount:.0f} mm is needed -- {' and '.join(blockers)} "
                f"{'is' if len(blockers) == 1 else 'are'} in the way.",
                where=f.id, at=zone.centroid.coords[0], reference=t.source,
                measured=Measured(achieved, amount, "mm"),
            ))

        # "at least one of these sides" -- only a finding if EVERY listed side fails.
        if t.clearance_any:
            sides, amount = t.clearance_any
            results = []
            for side in sides:
                got = _clearance_gap(f, poly, side, w, d, amount, solid, others)
                results.append(amount if got is None else got[0])
            if max(results) + 1 < amount:
                best = max(results)
                out.append(_finding(
                    "FURN-02", "warning",
                    f"{t.label} ({f.id}) needs {amount:.0f} mm access to at least one "
                    f"of its {'/'.join(sides)} sides; the best it has is {best:.0f} mm. "
                    f"It cannot be used or made up from either side.",
                    where=f.id, at=f.at, reference=t.source,
                    measured=Measured(best, amount, "mm"),
                ))
    return out


def _swing_sector(w: Wall, o: Opening) -> Polygon:
    """The quarter disc a door leaf actually sweeps.

    A full circle around the hinge would flag furniture behind the door and
    on the far side of the wall, neither of which the leaf can reach. The
    geometry mirrors render_dxf so the check matches what is drawn.
    """
    import math
    dx, dy = w.direction
    base = math.degrees(math.atan2(dy, dx))
    if o.swing == "left":
        hinge_at, start = o.at - o.width / 2, base
    else:
        hinge_at, start = o.at + o.width / 2, base + 90
    hinge = w.point_at(hinge_at, 0)
    pts = [hinge]
    for i in range(17):
        a = math.radians(start + 90 * i / 16)
        pts.append((hinge[0] + o.width * math.cos(a), hinge[1] + o.width * math.sin(a)))
    return Polygon(pts)


def r_door_swing_clear(p: Project, level: str) -> list[Finding]:
    """A door leaf that cannot open because furniture is in its arc."""
    out = []
    pieces = [(f, _furniture_poly(f)) for f in p.furniture if f.level == level]
    if not pieces:
        return out
    furn = unary_union([q for _, q in pieces])
    for o in p.openings:
        w = p.wall(o.host)
        if o.kind != "door" or w.level != level:
            continue
        arc = _swing_sector(w, o)
        hit = arc.intersection(furn)
        if hit.area > arc.area * 0.06:
            out.append(_finding(
                "DOOR-02", "warning",
                f"Door {o.id} cannot swing fully: furniture sits in its arc. "
                f"Either rehang it on the other jamb, change the swing direction, "
                f"or move the furniture.",
                where=o.id, at=opening_centre(p, o),
            ))
    return out


def r_daylight(p: Project, level: str) -> list[Finding]:
    ratio, src = cat.PLANNING["daylight_ratio"]
    glazing: dict[str, float] = {}
    for o in p.openings:
        w = p.wall(o.host)
        if o.kind != "window" or w.level != level:
            continue
        a, b = opening_sides(p, o)
        inner = a or b
        if inner is None:
            continue
        glazing[inner.id] = glazing.get(inner.id, 0.0) + (o.width * o.height) / 1e6
    out = []
    for r in (r for r in p.rooms if r.level == level and r.occupancy in HABITABLE):
        have = glazing.get(r.id, 0.0)
        need = r.area_m2 * ratio
        if have + 1e-9 < need:
            out.append(_finding(
                "LIGHT-01", "warning",
                f"{r.name} has {have:.2f} m2 of glazing against {need:.2f} m2 "
                f"required (1/8 of its {r.area_m2:.1f} m2 floor). "
                f"{'It has no window at all.' if have == 0 else 'Enlarge or add a window.'}",
                where=r.id, at=r.centroid, reference=src,
                measured=Measured(have, need, "m2"),
            ))
    return out


def r_circulation_width(p: Project, level: str) -> list[Finding]:
    """Can you actually walk between the doors of a room?

    Erodes the room's free space by half the minimum corridor width; if
    two doors of the same room end up in different connected pieces, no
    route of that width exists between them.
    """
    need, src = cat.PLANNING["corridor_min"]
    out = []
    pieces = [_furniture_poly(f) for f in p.furniture if f.level == level]
    furn = unary_union(pieces) if pieces else None

    for r in (r for r in p.rooms if r.level == level):
        free = _room_poly(r)
        if furn is not None:
            free = free.difference(furn)
        if free.is_empty:
            continue
        core = free.buffer(-need / 2)
        if core.is_empty:
            out.append(_finding(
                "CIRC-03", "warning",
                f"{r.name} has no route {need:.0f} mm wide anywhere once furniture "
                f"is placed. Nothing can be walked through.",
                where=r.id, at=r.centroid, reference=src,
            ))
            continue

        parts = [core] if core.geom_type == "Polygon" else list(core.geoms)
        access = []
        for o in p.openings:
            w = p.wall(o.host)
            if o.kind != "door" or w.level != level:
                continue
            a, b = opening_sides(p, o)
            if a is not r and b is not r:
                continue
            t = p.wall_type(w.type).thickness
            sign = 1 if a is r else -1
            pt = w.point_at(o.at, sign * (t / 2 + 250))
            access.append((o, ShpPoint(pt)))

        if len(access) < 2:
            continue
        idx = []
        for o, pt in access:
            owner = next((i for i, part in enumerate(parts)
                          if part.distance(pt) <= need), None)
            idx.append((o, owner))
        reached = {i for _, i in idx if i is not None}
        if len(reached) > 1 or any(i is None for _, i in idx):
            names = ", ".join(o.id for o, i in idx if i is None) or "some doors"
            out.append(_finding(
                "CIRC-03", "warning",
                f"In {r.name}, no continuous route {need:.0f} mm wide connects all "
                f"its doors once furniture is placed ({names} unreachable). "
                f"Someone crossing the room has to squeeze past furniture.",
                where=r.id, at=r.centroid, reference=src,
            ))
    return out


def r_view_judgement(p: Project, level: str) -> list[Finding]:
    """Pattern 134 Zen View, raised as a prompt and never as a measurement.

    The only `advisory` KIND in the library, and deliberately so. Whether an
    outlook is worth framing is a judgement about a place; the model knows
    that a window exists and nothing whatever about what is outside it. So
    this rule reports no number, cannot fail, and fires once per level
    rather than once per window -- a prompt repeated twelve times is noise,
    and noise is how a judgement gets clicked through.
    """
    windowed = set()
    for o in p.openings:
        if o.kind != "window" or p.wall(o.host).level != level:
            continue
        a, b = opening_sides(p, o)
        inner = a or b
        if inner is not None and inner.occupancy in HABITABLE:
            windowed.add(inner.id)
    if not windowed:
        return []
    rooms = [r for r in p.rooms if r.level == level and r.id in windowed]
    biggest = max(rooms, key=lambda r: r.area_m2)
    names = ", ".join(sorted(r.name for r in rooms))
    return [_finding(
        "VIEW-01", "advisory",
        f"Windows look out of {names}. Whether any of them frames something "
        f"worth keeping is a judgement this model cannot make: it knows a "
        f"window exists and nothing about what is outside it. Alexander's "
        f"claim in 134 is that a view on continuous display stops being seen, "
        f"so the question is which outlook to frame and which to screen -- "
        f"decided on site, not here.",
        where=biggest.id, at=biggest.centroid,
    )]


# The checks, in the order they run. RULES holds what each one declares.
CHECKS: tuple[Callable[[Project, str], list[Finding]], ...] = (
    r_sanitary_present,
    r_room_min_area,
    r_room_min_width,
    r_door_clear_width,
    r_private_room_access,
    r_entrance_vestibule,
    r_furniture_fits,
    r_furniture_overlap,
    r_furniture_clearance,
    r_door_swing_clear,
    r_daylight,
    r_circulation_width,
    r_view_judgement,
)

ORDER = {"violation": 0, "warning": 1, "advisory": 2}


def check_occupancies(p: Project) -> None:
    """Reject an occupancy the vocabulary does not know, loudly.

    This is the guard the shared vocabulary exists for. A term that is not
    declared matches no group, so the rule that should have caught it does
    not fire and the review comes back clean -- the worst possible failure
    for a checking tool. Raising here converts a silent pass into an error
    that names the room.
    """
    for r in p.rooms:
        vocab.require(r.occupancy, f"room {r.id!r} ({r.name})")


def review(p: Project, level: str | None = None, *,
           pack: CodePack | None = None,
           max_stage: int | None = None) -> list[Finding]:
    """Run every rule. Most severe first.

    `max_stage` reports only findings whose stage is at or before it, so a
    concept still at Stage 3 is not buried under room-resolution failures
    it is too early to answer. `pack` is a jurisdiction code pack; with
    none, findings carry no clause and the caller must say they are
    guidance rather than compliance (see `codes.disclaimer`).
    """
    check_occupancies(p)
    level = level or (p.levels[0].id if p.levels else "")
    out: list[Finding] = []
    for rule in CHECKS:
        out.extend(rule(p, level))
    if pack is not None:
        for f in out:
            f.code = pack.cite(f.rule)
    if max_stage is not None:
        out = [f for f in out if f.stage <= max_stage]
    out.sort(key=lambda f: (ORDER.get(f.severity, 9), f.rule, f.where))
    return out
