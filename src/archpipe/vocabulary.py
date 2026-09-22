"""The occupancy vocabulary: one list of room uses, shared by every stage.

Why this module exists. `brief.py` (Stage 0) and `rules.py` (Stages 3-4)
each grew a private idea of what a room can be. The brief says `hall`;
the rule engine's CIRCULATION set knew `corridor`, `lobby`, `landing`,
`vestibule` and `entrance` -- and never `hall`. Nothing joined the two,
so nothing failed. The moment brief-compliance runs, the intimacy
gradient rule (CIRC-01, Alexander 127) would have found zero circulation
rooms and passed in silence.

**A rule that cannot fail is worse than a rule that is missing**, because
a green result is read as evidence. So the terms are declared once, here,
and both sides import them.

An unknown term is an error, never a quiet non-match. `require()` raises
rather than letting a typo fall through a set-membership test, which is
the failure mode above in miniature: `hal` would simply never be
circulation.

Groups, not a hierarchy. A bedroom is habitable AND private; a bathroom
is sanitary AND private but NOT habitable -- it carries no daylight ratio
and no minimum width here. Membership is declared per term rather than
derived from a tree, because the exceptions are the whole point.

The empty string is a deliberate exception: `model.Room.occupancy`
defaults to `""` for an unlabelled room, so `""` is accepted and belongs
to no group. That is a visible gap in a spec, not a typo -- the spec says
plainly that the room has no declared use, and no group rule tests it.
"""
from __future__ import annotations

from dataclasses import dataclass

# The groups a rule can ask about. Adding one here means teaching the
# rules what to do with it, so the list is short on purpose.
GROUPS = ("habitable", "private", "sanitary", "circulation", "service")

UNSPECIFIED = ""


class UnknownOccupancy(ValueError):
    """Raised for an occupancy term the vocabulary does not know.

    Names the offender and lists the alternatives, because the realistic
    cause is a typo or a term invented in a YAML file, and both are fixed
    by seeing the list.
    """


@dataclass(frozen=True)
class Occupancy:
    term: str
    label: str
    groups: frozenset
    note: str = ""


def _o(term: str, label: str, *groups: str, note: str = "") -> Occupancy:
    for g in groups:
        if g not in GROUPS:
            raise ValueError(f"occupancy {term!r}: unknown group {g!r}")
    return Occupancy(term, label, frozenset(groups), note)


OCCUPANCIES: dict[str, Occupancy] = {o.term: o for o in (
    # ---- habitable -----------------------------------------------------
    _o("living", "Living room", "habitable"),
    _o("dining", "Dining room", "habitable"),
    _o("kitchen", "Kitchen", "habitable"),
    _o("study", "Study / workspace", "habitable",
       note="Habitable: a room worked in all day needs daylight and width."),
    _o("bedroom", "Bedroom", "habitable", "private"),
    _o("bedroom_single", "Bedroom, single", "habitable", "private",
       note="Sizing variant. catalogue.MIN_AREA_M2 carries a separate 8.0 m2 "
            "minimum for it, so it is reachable as an occupancy and is a term "
            "here rather than a lookup key only."),
    # ---- sanitary ------------------------------------------------------
    # Sanitary rooms are private but NOT habitable: no daylight ratio, no
    # minimum habitable width. Neufert gives them their own minimum areas.
    _o("bathroom", "Bathroom", "sanitary", "private"),
    _o("ensuite", "Ensuite", "sanitary", "private"),
    _o("shower_room", "Shower room", "sanitary", "private"),
    _o("wc", "WC", "sanitary", "private"),
    # ---- circulation ---------------------------------------------------
    # `hall` is the term the brief uses and the term the rule engine was
    # missing. It is first in this block for that reason.
    _o("hall", "Hall", "circulation"),
    _o("corridor", "Corridor", "circulation"),
    _o("landing", "Landing", "circulation"),
    _o("lobby", "Lobby", "circulation"),
    _o("vestibule", "Vestibule", "circulation"),
    _o("entrance", "Entrance", "circulation"),
    _o("stair", "Stair", "circulation"),
    # ---- private, non-habitable ----------------------------------------
    _o("dressing", "Dressing room", "private",
       note="Private but not habitable: it is entered from a bedroom and is "
            "not lived in, so it carries no daylight ratio. It IS private, so "
            "reaching it through a living space is the same fault CIRC-01 "
            "reports for a bedroom."),
    # ---- service / back of house ---------------------------------------
    _o("utility", "Utility", "service"),
    _o("store", "Store", "service"),
    _o("garage", "Garage", "service"),
)}


def is_known(term: str) -> bool:
    """True for a declared term or for the empty (unlabelled) occupancy."""
    return term == UNSPECIFIED or term in OCCUPANCIES


def require(term: str, where: str = "") -> Occupancy | None:
    """Return the declared occupancy, or raise. `""` returns None.

    `where` names the offending room so the message points at the line to
    fix rather than at the vocabulary.
    """
    if term == UNSPECIFIED:
        return None
    try:
        return OCCUPANCIES[term]
    except KeyError:
        prefix = f"{where}: " if where else ""
        raise UnknownOccupancy(
            f"{prefix}unknown occupancy {term!r}. Known terms: "
            f"{', '.join(sorted(OCCUPANCIES))}. Add it to "
            f"archpipe.vocabulary if it is a real use; an occupancy that is "
            f"not declared here is matched by no rule and would pass in "
            f"silence."
        ) from None


def in_group(group: str) -> frozenset:
    """Every term in a group, as a set the rules can test membership against."""
    if group not in GROUPS:
        raise ValueError(f"unknown occupancy group {group!r}; "
                         f"known: {', '.join(GROUPS)}")
    return frozenset(o.term for o in OCCUPANCIES.values() if group in o.groups)


def groups_of(term: str, where: str = "") -> frozenset:
    o = require(term, where)
    return o.groups if o else frozenset()


# The named sets the rule engine reads. Derived from the declarations
# above so a term can never be in the table but out of its own group.
HABITABLE = in_group("habitable")
PRIVATE = in_group("private")
SANITARY = in_group("sanitary")
CIRCULATION = in_group("circulation")
SERVICE = in_group("service")
