"""LV: every threshold the verification layers use, as a SourceCard. All are `policy` (ours) or `std` unless a held
page supplies the value; the pass bars come from docs/quality/LIGHTING-VERIFICATION.md (the client-approved plan)."""
from __future__ import annotations

from ..contracts import SourceCard

_DOC = "docs/quality/LIGHTING-VERIFICATION.md"


def _p(id, locator, value, quote=""):
    return SourceCard(id, "archpipe lighting verification plan", "2026-11-21", locator, quote, value, "policy", _DOC)


CARDS = {c.id: c for c in [
    _p("LV-V1-LUMEN", "V1 pass bar", "integrated vs stated lumens within 2 %"),
    _p("LV-V1-SPEC", "V1 pass bar", "spec lumens/watts/CCT/beam equal the bound product (lm 2 %, W 0.1 W, CCT exact, beam 10 %)"),
    _p("LV-V2-POS", "V2 pass bar", "emitter inside its room, below its ceiling, within 10 mm of the model"),
    _p("LV-V3-CLEAR", "V3 pass bar", "no sensor inside or within 50 mm under an object; plane within 5 mm of its host surface"),
    _p("LV-V4-TOL", "V4 pass bar", "published CIE 171:2006 case within 5 % (the LA1 row)"),
    _p("LV-V5-ENG", "V5 pass bar", "direct agreement within 3 %, total within 10 % between independent engines"),
    _p("LV-V6-HAND", "V6 pass bar", "engine average within +/-25 % of the lumen-method estimate"),
    _p("LV-V7-CONV", "V7 pass bar", "change < 3 % when ab/ad and grid density are doubled"),
    _p("LV-V8-MUT", "V8 pass bar", "100 % of seeded errors flagged by at least one of V1-V7"),
    SourceCard("LV-LM63", "ANSI/IES LM-63 photometric file format", "2002", "format definition",
               "", "type C, candela x multiplier, lumens = integral of I dOmega", "std"),
    SourceCard("LV-CIE171-52", "CIE 171:2006 test case 5.2 (via DAU Iray validation report 2016, Table 7)", "2006",
               "case 5.2", "", "E = I cos(i)/d^2 at 10 points; table in knowledge/lighting/L6-reference-results.json",
               "std", "knowledge/lighting/L6-reference-results.json"),
]}


def ids(*keys: str) -> tuple:
    for k in keys:
        if k not in CARDS:
            raise KeyError(k)
    return tuple(keys)
