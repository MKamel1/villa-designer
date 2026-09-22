"""Stage 0 (Intent): the brief, captured as data rather than prose.

Making the brief machine-readable buys one specific thing: the design can
later be checked **against the brief**, not only against standards.
"You asked for four bedrooms; the plan has three." "Master suite target
25 m2, actual 18." A generic checker cannot say either.

The gate for Stage 0 is that the brief is specific enough that a drawing
could contradict it. `Brief.gate()` tests exactly that.

Filled by interview, not by handing the client a form.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import vocabulary as vocab


class BriefError(ValueError):
    """Raised when a brief is structurally invalid. Names the offender."""


PRIORITIES = ("must", "should", "nice")
COOKING = ("minimal", "everyday", "enthusiast", "entertaining")
HOSTING = ("never", "occasional", "monthly", "weekly")


@dataclass(frozen=True)
class Occupant:
    id: str
    role: str                 # adult | child | teen | guest | staff
    age: int | None = None
    notes: str = ""


@dataclass(frozen=True)
class RoomRequirement:
    """One line of the schedule of accommodation."""
    id: str
    name: str
    occupancy: str            # a term declared in archpipe.vocabulary
    target_m2: float
    priority: str = "must"
    count: int = 1
    level_preference: str = ""      # "ground" | "upper" | "" for either
    notes: str = ""

    @property
    def total_m2(self) -> float:
        return self.target_m2 * self.count

    def validate(self) -> None:
        # The occupancy has to be a term the rules also know. An undeclared
        # term is not a harmless label: it matches no group, so the rules
        # that should test the room never fire and the review passes in
        # silence.
        try:
            vocab.require(self.occupancy, f"room {self.id!r}")
        except vocab.UnknownOccupancy as e:
            raise BriefError(str(e)) from None
        if self.priority not in PRIORITIES:
            raise BriefError(
                f"room {self.id!r}: priority {self.priority!r} not one of "
                f"{', '.join(PRIORITIES)}")
        if self.target_m2 <= 0:
            raise BriefError(f"room {self.id!r}: target_m2 must be positive")
        if self.count < 1:
            raise BriefError(f"room {self.id!r}: count must be at least 1")


@dataclass(frozen=True)
class Household:
    size: int
    growth_expected: bool = False
    ageing_in_place: bool = False
    pets: tuple[str, ...] = ()


@dataclass(frozen=True)
class Living:
    """How the household actually lives -- the part that changes a plan."""
    hosting_frequency: str = "occasional"
    typical_guests: int = 0
    overnight_guests: bool = False
    cooking: str = "everyday"
    work_from_home: int = 0          # people needing a real workspace
    noise_sensitivity: str = "normal"   # low | normal | high

    def validate(self) -> None:
        if self.hosting_frequency not in HOSTING:
            raise BriefError(f"living.hosting_frequency {self.hosting_frequency!r} "
                             f"not one of {', '.join(HOSTING)}")
        if self.cooking not in COOKING:
            raise BriefError(f"living.cooking {self.cooking!r} not one of "
                             f"{', '.join(COOKING)}")


@dataclass(frozen=True)
class Accessibility:
    step_free_entry: bool = False
    wheelchair: bool = False
    ground_floor_bedroom: bool = False
    ground_floor_wc: bool = True


@dataclass(frozen=True)
class Aesthetic:
    direction: str = ""
    references: tuple[str, ...] = ()     # paths to taste-board images
    must_have: tuple[str, ...] = ()
    must_avoid: tuple[str, ...] = ()


@dataclass
class Brief:
    name: str
    household: Household
    living: Living
    rooms: tuple[RoomRequirement, ...] = ()
    levels_preferred: int = 2
    privacy_gradient: tuple[str, ...] = ()
    storage_bulk_m3: float = 0.0
    accessibility: Accessibility = field(default_factory=Accessibility)
    aesthetic: Aesthetic = field(default_factory=Aesthetic)
    budget_note: str = ""

    # ---- derived ------------------------------------------------------
    @property
    def net_area_m2(self) -> float:
        """Sum of requested room areas. Excludes walls and circulation."""
        return sum(r.total_m2 for r in self.rooms)

    def net_area_by_priority(self) -> dict[str, float]:
        out = {p: 0.0 for p in PRIORITIES}
        for r in self.rooms:
            out[r.priority] += r.total_m2
        return out

    def rooms_of(self, occupancy: str) -> list[RoomRequirement]:
        return [r for r in self.rooms if r.occupancy == occupancy]

    def count_of(self, occupancy: str) -> int:
        return sum(r.count for r in self.rooms_of(occupancy))

    # ---- validation ---------------------------------------------------
    def validate(self) -> None:
        seen: set[str] = set()
        for r in self.rooms:
            if r.id in seen:
                raise BriefError(f"duplicate room requirement id {r.id!r}")
            seen.add(r.id)
            r.validate()
        self.living.validate()
        if self.household.size < 1:
            raise BriefError("household.size must be at least 1")
        if self.levels_preferred < 1:
            raise BriefError("levels_preferred must be at least 1")

    def gate(self) -> list[str]:
        """Stage 0 gate: is this brief specific enough to be contradicted?

        Returns a list of reasons it is not. Empty means the gate passes.
        These are not style notes -- each one names something the design
        could not later be checked against.
        """
        problems = []
        if not self.rooms:
            problems.append(
                "No schedule of accommodation. Without target areas, "
                "feasibility cannot be tested and no plan can be checked "
                "against the brief.")
        if self.net_area_m2 <= 0:
            problems.append("Total requested area is zero.")
        if not any(r.occupancy == "bedroom" for r in self.rooms):
            problems.append("No bedrooms requested.")
        if not any(r.occupancy in vocab.SANITARY for r in self.rooms):
            problems.append(
                "No bathroom or WC requested. A dwelling needs sanitary "
                "accommodation; requesting none makes the schedule invalid "
                "rather than minimal.")
        beds = self.count_of("bedroom")
        if beds and beds * 2 < self.household.size:
            problems.append(
                f"{beds} bedroom(s) for a household of {self.household.size}. "
                f"Either the bedroom count or the household size is wrong.")
        if self.household.ageing_in_place and not self.accessibility.ground_floor_bedroom:
            problems.append(
                "Ageing in place is intended but no ground-floor bedroom is "
                "required. These contradict each other.")
        if self.living.work_from_home > 0 and not self.rooms_of("study"):
            problems.append(
                f"{self.living.work_from_home} person(s) work from home but no "
                f"study or workspace is in the schedule.")
        if not self.aesthetic.direction and not self.aesthetic.references:
            problems.append(
                "No aesthetic direction and no reference images. Nothing to "
                "judge a proposal's look against.")
        return problems


# ---------------------------------------------------------------------------
def load(path: str | Path) -> Brief:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    hh = data.get("household", {})
    lv = data.get("living", {})
    ac = data.get("accessibility", {})
    ae = data.get("aesthetic", {})

    b = Brief(
        name=data.get("name", "Untitled brief"),
        household=Household(
            size=int(hh.get("size", 1)),
            growth_expected=bool(hh.get("growth_expected", False)),
            ageing_in_place=bool(hh.get("ageing_in_place", False)),
            pets=tuple(hh.get("pets", []) or ()),
        ),
        living=Living(
            hosting_frequency=lv.get("hosting_frequency", "occasional"),
            typical_guests=int(lv.get("typical_guests", 0)),
            overnight_guests=bool(lv.get("overnight_guests", False)),
            cooking=lv.get("cooking", "everyday"),
            work_from_home=int(lv.get("work_from_home", 0)),
            noise_sensitivity=lv.get("noise_sensitivity", "normal"),
        ),
        rooms=tuple(
            RoomRequirement(
                r["id"], r["name"], r["occupancy"], float(r["target_m2"]),
                r.get("priority", "must"), int(r.get("count", 1)),
                r.get("level_preference", ""), r.get("notes", ""),
            )
            for r in data.get("rooms", [])
        ),
        levels_preferred=int(data.get("levels_preferred", 2)),
        privacy_gradient=tuple(data.get("privacy_gradient", []) or ()),
        storage_bulk_m3=float(data.get("storage_bulk_m3", 0)),
        accessibility=Accessibility(
            step_free_entry=bool(ac.get("step_free_entry", False)),
            wheelchair=bool(ac.get("wheelchair", False)),
            ground_floor_bedroom=bool(ac.get("ground_floor_bedroom", False)),
            ground_floor_wc=bool(ac.get("ground_floor_wc", True)),
        ),
        aesthetic=Aesthetic(
            direction=ae.get("direction", ""),
            references=tuple(ae.get("references", []) or ()),
            must_have=tuple(ae.get("must_have", []) or ()),
            must_avoid=tuple(ae.get("must_avoid", []) or ()),
        ),
        budget_note=data.get("budget_note", ""),
    )
    b.validate()
    return b
