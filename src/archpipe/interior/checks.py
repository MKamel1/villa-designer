"""A+ interior checks I1-I4 (docs/quality/a-plus-interior-renders.md section B) as CheckResult records.

Every threshold here is POLICY (stated as ours in the criteria doc), carried as a SourceCard with
status "policy". A check that has nothing to evaluate reports not_evaluated, never pass.
"""
from __future__ import annotations

from archpipe.contracts import CheckResult, SourceCard
from archpipe.interior.concept import SURFACE_ROLES, Concept

LANE = "L4"
_DOC = "docs/quality/a-plus-interior-renders.md"

SOURCES = {
    "I1-policy": SourceCard(
        id="I1-policy", document="A+ interior criteria I1", edition="2026-11", locator="section B, I1",
        quote="One named concept; every room sheet cites it", value="no placed item matches a banned word",
        status="policy", url_or_path=_DOC),
    "I2-policy": SourceCard(
        id="I2-policy", document="A+ interior criteria I2", edition="2026-11", locator="section B, I2",
        quote="Every colour has an LRV. Declared ceiling/wall/floor bands match the lighting-calc inputs. "
              "Bands are POLICY", value="LRV present, 0-100; calc band within 10 LRV points of the palette",
        status="policy", url_or_path=_DOC),
    "I3-policy": SourceCard(
        id="I3-policy", document="A+ interior criteria I3", edition="2026-11", locator="section B, I3",
        quote="Per room: <=3 woods/stones and <=2 metals. 0 materials that are missing from the board",
        value="<=3 wood+stone, <=2 metals, 0 off-board materials", status="policy", url_or_path=_DOC),
    "I4-policy": SourceCard(
        id="I4-policy", document="A+ interior criteria I4", edition="2026-11", locator="section B, I4",
        quote="Sofa, cushion set and pendant are not repeated across spaces unless the concept says so",
        value="0 hero products repeated across rooms unless in concept.allowed_repeats", status="policy",
        url_or_path=_DOC),
}

LRV_BAND_TOLERANCE = 10.0          # POLICY: palette surface LRV vs lighting-calc input, in LRV points
MAX_WOOD_STONE = 3                 # POLICY (I3)
MAX_METAL = 2                      # POLICY (I3)
HERO_CATEGORIES = ("sofa", "cushion", "pendant")   # I4

# Used only when an item gives a bare material string with no kind; the concept's own board wins.
_KIND_WORDS = {
    "wood": ("oak", "walnut", "ash", "teak", "pine", "beech", "birch", "mahogany", "wood", "veneer", "rattan",
             "bamboo", "cedar"),
    "stone": ("marble", "travertine", "limestone", "granite", "stone", "terrazzo", "onyx", "slate", "quartzite",
              "sandstone", "basalt", "galala"),
    "metal": ("brass", "steel", "iron", "bronze", "copper", "aluminium", "aluminum", "chrome", "gold", "metal"),
}


def _kind_of(material, concept: Concept) -> tuple[str, str]:
    if isinstance(material, dict):
        name, kind = material["name"], material.get("kind")
    else:
        name, kind = material, None
    kind = kind or concept.material_kind(name)
    if not kind:
        low = name.lower()
        kind = next((k for k, words in _KIND_WORDS.items() if any(w in low for w in words)), "other")
    return name, kind


def _items(placed: dict[str, list[dict]]):
    for room, items in placed.items():
        for it in items:
            yield room, it


def check_i1(concept: Concept, placed: dict[str, list[dict]]) -> list[CheckResult]:
    """Concept coherence (script part): no placed item hits a banned word."""
    if not placed:
        return [CheckResult("I1", LANE, "not_evaluated", "all", message="no placed items given")]
    hits: dict[str, list[tuple[str, str]]] = {}
    for room, it in _items(placed):
        text = " ".join([it.get("name", ""), *map(str, it.get("tags", [])),
                         *[(m["name"] if isinstance(m, dict) else m) for m in it.get("materials", [])]]).lower()
        for b in concept.banned:
            if b and b in text:
                hits.setdefault(room, []).append((it.get("id", it.get("name", "?")), b))
    out = []
    for room in placed:
        h = hits.get(room, [])
        msg = (f"{len(h)} banned item(s) against concept '{concept.name}': "
               + "; ".join(f"{i} ~ '{b}'" for i, b in h)) if h else f"0 banned items against concept '{concept.name}'"
        out.append(CheckResult("I1", LANE, "fail" if h else "pass", room, achieved=len(h), required=0,
                               unit="banned items", message=msg, source_ids=("I1-policy",),
                               element_ids=tuple(i for i, _ in h)))
    return out


def check_i2(concept: Concept, calc_inputs: dict[str, float] | None = None) -> list[CheckResult]:
    """Palette LRV completeness; optionally the ceiling/wall/floor bands against the lighting-calc inputs.

    calc_inputs: {"ceiling": 70, "wall": 50, "floor": 20} in LRV points (0-100) or reflectance (0-1].
    """
    if not concept.palette:
        return [CheckResult("I2", LANE, "not_evaluated", concept.name, message="palette is empty")]
    missing = [c.name for c in concept.palette if c.lrv is None]
    bad = [c.name for c in concept.palette if c.lrv is not None and not 0 <= c.lrv <= 100]
    parts = []
    if missing:
        parts.append(f"{len(missing)} colour(s) without LRV: {', '.join(missing)}")
    if bad:
        parts.append(f"{len(bad)} LRV outside 0-100: {', '.join(bad)}")
    out = [CheckResult(
        "I2", LANE, "fail" if parts else "pass", f"{concept.name}/palette",
        achieved=len(concept.palette) - len(missing) - len(bad), required=len(concept.palette),
        unit="colours with valid LRV",
        message="; ".join(parts) or f"all {len(concept.palette)} palette colours carry an LRV",
        source_ids=("I2-policy",), element_ids=tuple(missing + bad))]
    if calc_inputs is None:
        out.append(CheckResult("I2", LANE, "not_evaluated", f"{concept.name}/bands",
                               message="no lighting-calc inputs supplied, so ceiling/wall/floor bands not compared"))
        return out
    for role in SURFACE_ROLES:
        subject = f"{concept.name}/{role}"
        if role not in calc_inputs:
            out.append(CheckResult("I2", LANE, "not_evaluated", subject, message=f"calc input for {role} absent"))
            continue
        want = calc_inputs[role] * 100 if calc_inputs[role] <= 1 else calc_inputs[role]
        cols = [c for c in concept.palette if c.role == role and c.lrv is not None]
        if not cols:
            out.append(CheckResult("I2", LANE, "fail", subject, required=want, unit="LRV",
                                   message=f"calc uses {want:g} for {role} but the palette declares no {role} colour with an LRV",
                                   source_ids=("I2-policy",)))
            continue
        nearest = min(cols, key=lambda c: abs(c.lrv - want))
        dev = abs(nearest.lrv - want)
        out.append(CheckResult("I2", LANE, "pass" if dev <= LRV_BAND_TOLERANCE else "fail", subject,
                               achieved=dev, required=LRV_BAND_TOLERANCE, unit="LRV points off calc input",
                               message=f"{role}: calc {want:g}, nearest palette LRV {nearest.lrv:g} "
                                       f"({dev:g} points apart, limit {LRV_BAND_TOLERANCE:g})",
                               source_ids=("I2-policy",)))
    return out


def check_i3(concept: Concept, placed: dict[str, list[dict]]) -> list[CheckResult]:
    """Per room: <=3 distinct woods/stones, <=2 metals, 0 materials missing from the concept board."""
    if not placed:
        return [CheckResult("I3", LANE, "not_evaluated", "all", message="no placed items given")]
    board = concept.material_names()
    out = []
    for room, items in placed.items():
        seen: dict[str, str] = {}
        for it in items:
            for m in it.get("materials", []):
                name, kind = _kind_of(m, concept)
                seen[name.lower()] = kind
        if not seen:
            out.append(CheckResult("I3", LANE, "not_evaluated", room, message="no materials declared on the room's items"))
            continue
        ws = sorted(n for n, k in seen.items() if k in ("wood", "stone"))
        mt = sorted(n for n, k in seen.items() if k == "metal")
        off = sorted(n for n in seen if n not in board)
        probs = []
        if len(ws) > MAX_WOOD_STONE:
            probs.append(f"{len(ws)} woods/stones ({', '.join(ws)}), max {MAX_WOOD_STONE}")
        if len(mt) > MAX_METAL:
            probs.append(f"{len(mt)} metals ({', '.join(mt)}), max {MAX_METAL}")
        if off:
            probs.append(f"{len(off)} not on the board ({', '.join(off)})")
        out.append(CheckResult("I3", LANE, "fail" if probs else "pass", room,
                               achieved=len(probs), required=0, unit="breached limits",
                               message="; ".join(probs) if probs else f"{len(ws)} woods/stones, {len(mt)} metals, 0 off-board",
                               source_ids=("I3-policy",), element_ids=tuple(ws + mt + off) if probs else ()))
    return out


def _signature(it: dict) -> str:
    if it.get("product_id"):
        return f"p:{it['product_id']}"
    mats = tuple(sorted((m["name"] if isinstance(m, dict) else m).lower() for m in it.get("materials", [])))
    return f"n:{it.get('name', '').strip().lower()}|{mats}"


def check_i4(concept: Concept, placed: dict[str, list[dict]]) -> list[CheckResult]:
    """No clone heroes: a sofa, cushion set or pendant (same product, or same name + materials) in 2+ rooms."""
    if not placed:
        return [CheckResult("I4", LANE, "not_evaluated", "all", message="no placed items given")]
    where: dict[tuple[str, str], dict[str, list[str]]] = {}
    for room, it in _items(placed):
        cat = it.get("category", "")
        if cat not in HERO_CATEGORIES:
            continue
        where.setdefault((cat, _signature(it)), {}).setdefault(room, []).append(it.get("id", it.get("name", "?")))
    if not where:
        return [CheckResult("I4", LANE, "not_evaluated", "all",
                            message="no sofa, cushion or pendant items in the placed list")]
    clones = {k: v for k, v in where.items()
              if len(v) > 1 and not (k[1].startswith("p:") and k[1][2:] in concept.allowed_repeats)}
    out = []
    for (cat, sig), rooms in clones.items():
        out.append(CheckResult("I4", LANE, "fail", f"{cat}:{sig}", achieved=len(rooms), required=1,
                               unit="rooms using it",
                               message=f"{cat} '{sig}' appears in {len(rooms)} rooms: {', '.join(sorted(rooms))}",
                               source_ids=("I4-policy",), element_ids=tuple(i for v in rooms.values() for i in v)))
    if not clones:
        out.append(CheckResult("I4", LANE, "pass", "all", achieved=0, required=0, unit="cloned heroes",
                               message=f"{len(where)} distinct hero item(s) (sofa/cushion/pendant); none repeated across rooms",
                               source_ids=("I4-policy",)))
    return out


def run_checks(concept: Concept, placed: dict[str, list[dict]],
               calc_inputs: dict[str, float] | None = None) -> list[CheckResult]:
    return check_i1(concept, placed) + check_i2(concept, calc_inputs) + check_i3(concept, placed) + check_i4(concept, placed)
