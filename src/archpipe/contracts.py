"""Shared contracts for the parallel A+ lanes (docs/quality/PLAN.md section 5).

Every lane builds against these records so lanes never need to read each
other's code. Version changes only at wave boundaries; bump CONTRACT_VERSION
and note it in docs/quality/LANES.md.

Reuses `rules.Measured` for achieved-versus-required pairs and the existing
`codes.Clause` / `codes.CodePack` mechanism for jurisdiction clauses.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONTRACT_VERSION = "0.1"

# Status of a threshold's source (A-PLUS.md section 2).
SOURCE_STATUS = ("sourced", "std", "policy", "unverified")
# Outcome of one criterion check. "not_evaluated" is explicit: a check that
# could not run never reports pass (fail closed).
CHECK_STATUS = ("pass", "fail", "warn", "not_evaluated")


@dataclass(frozen=True)
class SourceCard:
    """One threshold's evidence: where a value comes from, verbatim."""
    id: str                 # e.g. "EG-ER-119-2008-art93"
    document: str           # "Executive Regulations of Law 119/2008 (Andersen EN translation)"
    edition: str
    locator: str            # article / clause / printed page
    quote: str              # verbatim text the value is taken from
    value: str              # the value as stated, with unit
    status: str             # one of SOURCE_STATUS
    url_or_path: str = ""

    def __post_init__(self) -> None:
        if self.status not in SOURCE_STATUS:
            raise ValueError(f"{self.id}: status {self.status!r} not in {SOURCE_STATUS}")
        if self.status == "sourced" and not self.quote.strip():
            raise ValueError(f"{self.id}: a sourced card needs a verbatim quote")


@dataclass
class CheckResult:
    """Outcome of one A+ criterion (ids from docs/quality/a-plus-*.md)."""
    criterion: str          # e.g. "EG4", "LA2", "R6", "EA6"
    lane: str               # e.g. "L1"
    status: str             # one of CHECK_STATUS
    subject: str            # what was checked: room id, view id, circuit id...
    achieved: float | None = None
    required: float | None = None
    unit: str = ""
    message: str = ""       # achieved-versus-required in words, never an adjective
    source_ids: tuple[str, ...] = ()
    element_ids: tuple[str, ...] = ()
    gate: bool = False      # True = legal/safety gate (failing caps grade at D)

    def __post_init__(self) -> None:
        if self.status not in CHECK_STATUS:
            raise ValueError(f"{self.criterion}: status {self.status!r} not in {CHECK_STATUS}")
        if self.status in ("pass", "fail") and not self.source_ids:
            raise ValueError(f"{self.criterion}/{self.subject}: a pass/fail needs a source card id")


@dataclass
class DesignElement:
    """One element of the design model (v0; owned by lane L2).

    Units: millimetres, model coordinates, z up, level-relative z.
    `kind` uses IFC-like names: wall, slab, door, window, stair, railing,
    room, column, beam, furniture, fixture, luminaire, device, plant.
    """
    id: str
    kind: str
    level: str                          # "B" (-1.80), "GF", "L1", "ROOF", "SITE"
    placement: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_deg: float = 0.0
    size: tuple[float, float, float] = (0.0, 0.0, 0.0)   # w, d, h bounding box
    host: str = ""                      # host element id (wall for a door, ceiling for a luminaire)
    room: str = ""                      # room id containing it
    product_id: str = ""                # products library id, "" when not chosen
    finish_codes: tuple[str, ...] = ()
    params: dict = field(default_factory=dict)   # kind-specific: riser, tread, guard height...


@dataclass
class LightingZone:
    """A control zone (published by L6, consumed by L7)."""
    id: str                 # e.g. "Z-GF-LIV-1"
    room: str
    layer: str              # ambient | task | accent | decorative | exterior | emergency
    luminaire_ids: tuple[str, ...]
    watts: float
    dimming: str            # dali2 | phase_cut | 0_10v | switched


@dataclass
class Circuit:
    """An electrical circuit (owned by L7)."""
    id: str                 # e.g. "DB-GF/L3"
    board: str
    kind: str               # lighting | socket | dedicated | elv
    load_ids: tuple[str, ...]
    design_current_a: float
    breaker_a: float
    rcd_ma: float | None
    cable_mm2: float
    length_m: float
    voltage_drop_pct: float


@dataclass
class RenderVerdict:
    """Critic verdict for one rendered view (owned by L3)."""
    view_id: str
    image: str
    lens_mm: float | None
    camera_height_m: float | None
    scores: dict            # criterion id ("R1".."R13") -> 0 | 1 | 2
    verdict: str            # pass | fail
    notes: dict = field(default_factory=dict)


def write_results(lane: str, results: list[CheckResult], root: Path | str = "out/checks") -> Path:
    """Write a lane's results to out/checks/<lane>.json (one file per lane, no shared edits)."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{lane}.json"
    payload = {"contract": CONTRACT_VERSION, "lane": lane,
               "results": [asdict(r) for r in results]}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_all_results(root: Path | str = "out/checks") -> list[CheckResult]:
    out: list[CheckResult] = []
    for p in sorted(Path(root).glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for r in data["results"]:
            r["source_ids"] = tuple(r.get("source_ids", ()))
            r["element_ids"] = tuple(r.get("element_ids", ()))
            out.append(CheckResult(**r))
    return out
