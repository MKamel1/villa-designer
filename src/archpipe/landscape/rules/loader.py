"""Load and validate knowledge/landscape/rules/rules.json (schema: docs/lanes/LDK.md).

Fails closed: a rule without a resolvable source card, an advisory rule that carries a
number, or a computed rule backed only by `unverified` cards is a ValueError. Rules become
`archpipe.rules.Rule` objects, so the framework's own "must cite a reference" guard applies.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ...contracts import SourceCard
from ...rules import Remedy, Rule

RULES_JSON = Path(__file__).resolve().parents[4] / "knowledge/landscape/rules/rules.json"
SCHEMA = "landscape-rules/1"
WITHDRAWN_STATUS = "unverified — not used"
NUMERIC_KEYS = {"measurement", "params", "threshold", "value", "limit", "unit"}
APL_BOOK = "pattern-language"


def _remedies(fix: str) -> tuple[Remedy, ...]:
    # Cheapest first: fix inside the stage, then back to Order (L1), then back to Fit (L2).
    return (Remedy(fix),
            Remedy("Redraw this zone in the layout", 3, "L1"),
            Remedy("Give the zone more of the plot, or reduce what the brief asks of it", 2, "L2"))


class RuleSet:
    def __init__(self, data: dict):
        if data.get("schema") != SCHEMA:
            raise ValueError(f"rules.json schema {data.get('schema')!r} != {SCHEMA!r}")
        self.data = data
        self.sources: dict[str, SourceCard] = {}
        for s in data["sources"]:
            if s["id"] in self.sources:
                raise ValueError(f"duplicate source id {s['id']}")
            self.sources[s["id"]] = SourceCard(id=s["id"], document=s["document"], edition=s["edition"],
                                              locator=s["locator"], quote=s["quote"], value=s["value"],
                                              status=s["status"], url_or_path=s.get("book") or s.get("url", ""))
        self._check_pattern_cards()
        self.params: dict[str, dict] = {}
        self.rules: dict[str, Rule] = {}
        self.severity: dict[str, str] = {}
        self.source_ids: dict[str, tuple[str, ...]] = {}
        for r in data["rules"]:
            self._add(r, "computed", r["fix"])
            self.params[r["id"]] = r["params"]
            self.severity[r["id"]] = r["severity"]
        self.advisory_ids = []
        for a in data["advisory"]:
            if NUMERIC_KEYS & a.keys():
                raise ValueError(f"{a['id']}: an advisory rule carries no measurement")
            self._check_pattern_rule(a)
            self._add(a, "advisory", "Raise it with the designer as a judgement prompt; do not score it")
            self.advisory_ids.append(a["id"])
        self.gaps = {g["id"]: g for g in data["gaps"]}
        # Withdrawn rules cite a source we do not hold ("unverified - not used"). They are data for the
        # lead (what is missing), never Rule objects, so a critic cannot cite them.
        self.withdrawn = {w["id"]: w for w in data.get("withdrawn", [])}
        for w in self.withdrawn.values():
            if w.get("status") != WITHDRAWN_STATUS:
                raise ValueError(f"{w['id']}: withdrawn rules must have status {WITHDRAWN_STATUS!r}")
            if w["id"] in self.rules:
                raise ValueError(f"{w['id']}: both active and withdrawn")

    def _check_pattern_cards(self) -> None:
        """A Pattern Language cards name their pattern; the card id, number and role must agree, and the
        quote must sit on a page (the page-text guard in tests/ reads the PDF)."""
        for s in self.data["sources"]:
            if s.get("book") != APL_BOOK:
                continue
            n, role = s.get("pattern"), s.get("role")
            if not isinstance(n, int) or role not in ("problem", "therefore") or not s.get("pattern_name"):
                raise ValueError(f"{s['id']}: a Pattern Language card needs pattern (int), pattern_name and role")
            if s["id"] != f"APL-{n}-{role}":
                raise ValueError(f"{s['id']}: id does not match pattern {n} / {role}")
            if not s.get("quote") or not isinstance(s.get("pdf_page"), int):
                raise ValueError(f"{s['id']}: needs a quote and a pdf_page")
            if role == "therefore" and not isinstance(s.get("therefore_pdf_page"), int):
                raise ValueError(f"{s['id']}: a therefore card needs therefore_pdf_page")

    def _check_pattern_rule(self, a: dict) -> None:
        """AD-APL-n cites only pattern n's own cards, and is titled with the book's name for n."""
        m = re.fullmatch(r"AD-APL-(\d+)", a["id"])
        if not m:
            return
        n = int(m.group(1))
        for i in a.get("sources", ()):
            raw = next((s for s in self.data["sources"] if s["id"] == i), {})
            if raw.get("pattern") != n:
                raise ValueError(f"{a['id']}: source {i} is not a card of pattern {n}")
        names = {s["pattern_name"] for s in self.data["sources"] if s.get("pattern") == n}
        if a["title"] not in names:
            raise ValueError(f"{a['id']}: title {a['title']!r} is not the book's name for pattern {n} ({names})")

    def _add(self, r: dict, kind: str, fix: str) -> None:
        ids = tuple(r.get("sources", ()))
        if not ids:
            raise ValueError(f"{r['id']}: no source cards")
        for i in ids:
            if i not in self.sources:
                raise ValueError(f"{r['id']}: unknown source card {i}")
        if kind == "computed" and all(self.sources[i].status == "unverified" for i in ids):
            raise ValueError(f"{r['id']}: a computed rule cannot rest only on unverified sources")
        if r["id"] in self.rules:
            raise ValueError(f"duplicate rule id {r['id']}")
        self.source_ids[r["id"]] = ids
        self.rules[r["id"]] = Rule(id=r["id"], title=r["title"], stage=4, kind=kind,
                                   reference=r["reference"], remedies=_remedies(fix),
                                   evidence_refs=ids,
                                   evidence_status="unverified" if all(
                                       self.sources[i].status == "unverified" for i in ids) else "sourced")


def load(path: Path = RULES_JSON) -> RuleSet:
    return RuleSet(json.loads(Path(path).read_text(encoding="utf-8")))
