"""SourceCards for every threshold the parity checks use (all `policy`: ours, stated as ours)."""
from __future__ import annotations

from ..contracts import SourceCard


def _p(i, doc, value, why):
    return SourceCard(id=i, document=doc, edition="RV1 2026-11-21", locator="docs/lanes/RV1-checks.md",
                      quote="", value=value, status="policy", url_or_path=why)


CARDS = {c.id: c for c in [
    _p("RV1-TOL-SCENE", "RV1 policy: scene resolution tolerance", "2 mm",
       "Scene vertices are rounded to 1 mm (P-pipeline); two rounded surfaces can disagree by 2 mm."),
    _p("RV1-TOL-EXACT", "RV1 policy: exact-geometry tolerance", "0.05 mm",
       "Used on unrounded model/box geometry (D02); a contact is a clash only above this."),
    _p("RV1-TOL-FIT", "RV1 policy: built-vs-modelled size/position", "10 mm",
       "Scene rounding is 1 mm; glass and leaf extents were measured to agree with the model to 3 mm, so 10 mm is a deliberate margin."),
    _p("RV1-TOL-AREA", "RV1 policy: area agreement with the frozen Revit rooms", "1 %",
       "Frozen Revit net areas differ from the concept estimate by up to 1.9 % (LEARNINGS 630-646); 1 % separates them."),
    _p("RV1-SOFFIT-CLEAR", "RV1 policy: door head clearance", ">= 0 mm",
       "A door leaf plus frame must fit under the soffit above it (D04: 2.10 m door under a 1.91 m soffit)."),
    _p("RV1-GLAZE-HEAD", "RV1 policy: full-height glazing head allowance", "<= 150 mm",
       "Gap between glass head and the beam/soffit above for windows modelled full-height (D07)."),
    _p("RV1-HEADROOM", "RV1 policy: stair headroom", ">= 2000 mm vertical above each nosing",
       "Policy figure for the sampled vertical clearance; the published stair headroom card is held by L1, not restated here."),
    _p("RV1-GUARD", "RV1 policy: guard at drop edges", "built height >= modelled guard_height_mm",
       "The modelled height is the intended side; the published minimum is L1's (docs/lanes/L1-safety-report-D1.md)."),
    _p("RV1-MOUNT", "RV1 policy: wall-mounted fitting contact", "<= 10 mm to host face",
       "A fitting standing off its host wall by more than 10 mm is not mounted."),
    _p("RV1-TOL-CAT", "RV1 policy: bbox vs catalogue figure", "5 % or 10 mm", "Requested family size vs built bounding box (D09); ours."),
    _p("RV1-ENV", "RV1 policy: environment agreement", "2 mm (frozen Revit read-back is 0.001 mm)",
       "LEARNINGS 568-582 compared shapes within 2 mm."),
]}


def _load_published():
    """Published cards are read from the held card file, never retyped."""
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / "knowledge" / "eg" / "best-practice-cards.json"
    if not p.exists():
        raise FileNotFoundError(p)
    d = json.loads(p.read_text())
    for c in (d["cards"] if "cards" in d else d):
        if c["id"] in ("ukadk-stair-headroom-min", "ukadk-guarding-height-external"):
            CARDS[c["id"]] = SourceCard(**{k: c[k] for k in ("id", "document", "edition", "locator", "quote", "value", "status")},
                                        url_or_path=str(p.relative_to(p.parents[2])))


_load_published()


def card(i):
    return CARDS[i]
