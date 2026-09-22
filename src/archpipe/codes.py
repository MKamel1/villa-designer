"""Code clauses: the pluggable half of a citation.

Every rule in this project carries a **reference** -- a Neufert figure, an
Alexander pattern number, or named published practice. That is required,
and it is ours to state, because those sources are on the shelf and can be
argued with.

A **code clause** is a different kind of claim. It belongs to a
jurisdiction, it is enforceable, and this project has not chosen one
(PRD section 11, open question 1). So what ships here is the *mechanism*
for carrying clauses, and **no pack is loaded by default**. With no pack,
every output says plainly that the findings are design guidance and not a
statement of code compliance.

**There is no real clause number in this file and none should ever be
added to it.** A pack is data, supplied for a jurisdiction by someone who
has read that jurisdiction's code. An invented clause number is worse than
an absent one: absent, the reader knows to look it up; invented, they
believe they already have. `EXAMPLE_PACK` exists to exercise the
mechanism and is marked as an example everywhere it appears.

    from archpipe import codes, rules
    pack = codes.load("packs/somewhere.yaml")   # supplied, never invented
    findings = rules.review(project, pack=pack)

A pack file:

    id: somewhere-2019
    jurisdiction: "Somewhere"
    edition: "2019 edition, as amended"
    clauses:
      SAN-01: {clause: "...", title: "...", note: "..."}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class CodePackError(ValueError):
    """Raised when a pack is structurally invalid. Names the offender."""


@dataclass(frozen=True)
class Clause:
    """One jurisdiction's clause, backing one rule id."""
    rule: str
    clause: str            # the clause identifier, as that code prints it
    title: str = ""
    note: str = ""

    def cite(self, example: bool = False) -> str:
        bits = [f"EXAMPLE ONLY -- {self.clause}" if example else self.clause]
        if self.title:
            bits.append(self.title)
        if self.note:
            bits.append(self.note)
        return " -- ".join(bits)


@dataclass(frozen=True)
class CodePack:
    """A jurisdiction's clauses, keyed by rule id.

    `example` marks a pack whose clause identifiers are placeholders. It is
    not a comment: it changes what every citation and disclaimer says, so a
    demonstration can never be mistaken for a compliance claim.
    """
    id: str
    jurisdiction: str
    edition: str
    clauses: dict = field(default_factory=dict)
    example: bool = False

    def __post_init__(self) -> None:
        if not self.id:
            raise CodePackError("a code pack needs an id")
        if not self.jurisdiction:
            raise CodePackError(
                f"code pack {self.id!r} names no jurisdiction. A clause "
                f"without a jurisdiction cannot be checked or overridden.")
        for rule_id, c in self.clauses.items():
            if not isinstance(c, Clause):
                raise CodePackError(
                    f"code pack {self.id!r}: {rule_id!r} is not a Clause")
            if not c.clause:
                raise CodePackError(
                    f"code pack {self.id!r}: clause for {rule_id!r} is empty")

    def clause_for(self, rule_id: str) -> Clause | None:
        return self.clauses.get(rule_id)

    def cite(self, rule_id: str) -> str:
        """The citation string for a rule, or "" when this pack has none.

        A pack covering only some rules is normal, not an error: a code
        speaks to sanitary provision and stair geometry and says nothing
        at all about where a sofa sits.
        """
        c = self.clause_for(rule_id)
        return c.cite(self.example) if c else ""


GUIDANCE_ONLY = (
    "No code pack loaded. These findings are design GUIDANCE -- Neufert, "
    "Alexander and named published practice -- and are NOT a statement of "
    "code compliance. A local code always wins; where it is stricter, it "
    "governs. Load a jurisdiction pack to add clause citations."
)


def disclaimer(pack: CodePack | None) -> str:
    """What the output must say about the standing of its findings."""
    if pack is None:
        return GUIDANCE_ONLY
    if pack.example:
        return (
            f"Code pack {pack.id!r} ({pack.jurisdiction}) loaded. This pack is "
            f"an EXAMPLE of the mechanism: its clause identifiers are "
            f"placeholders, not real clauses, and prove nothing about "
            f"compliance anywhere. The findings remain design GUIDANCE, NOT "
            f"code compliance."
        )
    return (
        f"Code pack {pack.id!r} loaded: {pack.jurisdiction}, {pack.edition}. "
        f"Clauses shown are that pack's; the reference line remains the design "
        f"source. Whether the design complies is still the local authority's "
        f"to determine, not this tool's."
    )


def from_mapping(data: dict) -> CodePack:
    clauses = {}
    for rule_id, c in (data.get("clauses") or {}).items():
        if isinstance(c, str):
            c = {"clause": c}
        clauses[rule_id] = Clause(
            rule=rule_id, clause=str(c.get("clause", "")),
            title=str(c.get("title", "")), note=str(c.get("note", "")),
        )
    return CodePack(
        id=str(data.get("id", "")),
        jurisdiction=str(data.get("jurisdiction", "")),
        edition=str(data.get("edition", "")),
        clauses=clauses,
        example=bool(data.get("example", False)),
    )


def load(path: str | Path) -> CodePack:
    """Load a pack from YAML. `example` loads the built-in example pack."""
    if str(path) == "example":
        return EXAMPLE_PACK
    import yaml
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return from_mapping(data)


# --------------------------------------------------------------------------
# The example pack. Placeholders only.
#
# The jurisdiction names itself as not real, and every clause identifier is
# visibly a placeholder rather than anything resembling a clause number.
# The rules covered are the two that a building code anywhere does speak
# to -- sanitary provision and door widths on an escape route -- so the
# shape is realistic even though the content is not.
# --------------------------------------------------------------------------
EXAMPLE_PACK = CodePack(
    id="example",
    jurisdiction="EXAMPLE -- not a real jurisdiction",
    edition="not a real edition",
    example=True,
    clauses={
        "SAN-01": Clause(
            "SAN-01", "<clause id goes here>",
            "sanitary accommodation required in a dwelling",
            "placeholder showing where a real clause reference would sit"),
        "DOOR-01": Clause(
            "DOOR-01", "<clause id goes here>",
            "minimum clear opening width of a doorway",
            "placeholder showing where a real clause reference would sit"),
    },
)
