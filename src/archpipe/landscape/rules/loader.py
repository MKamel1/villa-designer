"""Load and validate knowledge/landscape/rules/rules.json (schema: docs/lanes/LDK.md).

Fails closed: a rule without a resolvable source card, an advisory rule that carries a
number, or a computed rule backed only by `unverified` cards is a ValueError. Rules become
`archpipe.rules.Rule` objects, so the framework's own "must cite a reference" guard applies.
"""
from __future__ import annotations

import json
from pathlib import Path

from ...contracts import SourceCard
from ...rules import Remedy, Rule

RULES_JSON = Path(__file__).resolve().parents[4] / "knowledge/landscape/rules/rules.json"
SCHEMA = "landscape-rules/1"


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
                                              status=s["status"], url_or_path=s.get("book", ""))
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
            if "measurement" in a or "params" in a:
                raise ValueError(f"{a['id']}: an advisory rule carries no measurement")
            self._add(a, "advisory", "Raise it with the designer as a judgement prompt; do not score it")
            self.advisory_ids.append(a["id"])
        self.gaps = {g["id"]: g for g in data["gaps"]}

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
