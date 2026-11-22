"""Validate and assemble the plant library.

Every species file (knowledge/landscape/plants/species/<slug>.json) holds the required attributes
(`REQUIRED`). Each attribute is either SOURCED (value + a complete source: id, https url,
access date, locator or quote) or an explicit GAP (reason + what was searched). A missing
attribute, a SOURCED one without a source, or an unknown status is an error. A GAP is valid:
the library never fills what it could not source (CLAUDE.md discipline 2).
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "knowledge" / "landscape" / "plants"

REQUIRED = (
    "accepted_name", "height_m", "spread_m", "growth_rate", "sun", "water", "heat", "drought",
    "alkaline_soil", "salt", "frost", "flowering", "foliage", "root_behaviour",
    "toxicity_people", "toxicity_fish", "litter", "maintenance", "egypt_availability",
)
LAYERS = {
    "canopy_tree", "small_fruit_tree", "palm", "screen_hedge", "climber", "flowering_shrub",
    "perennial", "groundcover_lawn", "grass", "tropical_foliage", "aquatic_marginal", "herb",
}
ENUMS = {
    "growth_rate": {"slow", "moderate", "fast"},
    "water": {"very_low", "low", "moderate", "high", "aquatic"},
    "heat": {"high", "moderate", "low"},
    "drought": {"high", "moderate", "low", "none"},
    "alkaline_soil": {"tolerant", "moderate", "intolerant"},
    "salt": {"high", "moderate", "low", "none"},
    "root_behaviour": {"benign", "moderate", "aggressive", "aquatic"},
    "toxicity_people": {"non_toxic", "mild", "toxic", "highly_toxic"},
    "toxicity_fish": {"non_toxic", "mild", "toxic", "highly_toxic"},
    "maintenance": {"low", "moderate", "high"},
}
# attribute -> key inside `value` holding the enum
ENUM_KEY = {"water": "hydrozone", "heat": "class", "drought": "class", "alkaline_soil": "class",
            "salt": "class", "root_behaviour": "class", "toxicity_people": "class",
            "toxicity_fish": "class", "maintenance": "level", "growth_rate": "class"}
STATUSES = {"SOURCED", "GAP", "NA", "POLICY"}
FOLIAGE_HABIT = {"evergreen", "semi_evergreen", "deciduous", "herbaceous"}
SITE_CLIMATE = {
    "weather_file": "EGY_QH_Cairo.West.AP.623680_TMYx.epw (nearest station, WMO 623680; typical year, not extremes)",
    "coordinates_status": "PLACEHOLDER: site coordinates in villa_env (30.040, 30.961) are the BRIEF maps link, "
                          "not a surveyed plot; station is 30.117N 30.917E, 151 m",
    "typical_year_min_c": 5.1, "typical_year_max_c": 43.9, "annual_rain_mm": 15,
    "days_max_above_30c": 154, "hours_at_or_below_0c": 0,
    "frost_floor_policy_c": 0.0,
}


class SpeciesError(ValueError):
    pass


def _check_source(attr: str, s) -> list[str]:
    errs = []
    if not isinstance(s, dict):
        return [f"{attr}: SOURCED needs a source object"]
    if not s.get("source_id"):
        errs.append(f"{attr}: source.source_id missing")
    url = s.get("url", "")
    if not (url.startswith("https://") or url.startswith("held:")):
        errs.append(f"{attr}: source.url must be https:// or held:<book>")
    try:
        _dt.date.fromisoformat(s.get("accessed", ""))
    except ValueError:
        errs.append(f"{attr}: source.accessed must be an ISO date")
    if not (s.get("quote") or s.get("locator")):
        errs.append(f"{attr}: source needs a quote or locator")
    if len(s.get("quote", "")) > 400:
        errs.append(f"{attr}: quote longer than 400 characters (summarise, do not copy)")
    return errs


def _check_value(attr: str, v) -> list[str]:
    errs = []
    if attr in ("height_m", "spread_m"):
        if not (isinstance(v, dict) and all(isinstance(v.get(k), (int, float)) for k in ("min", "max"))
                and 0 < v["min"] <= v["max"] <= 60):
            errs.append(f"{attr}: value needs numeric 0 < min <= max <= 60 (metres)")
    elif attr in ENUM_KEY:
        k = ENUM_KEY[attr]
        if not (isinstance(v, dict) and v.get(k) in ENUMS[attr]):
            errs.append(f"{attr}: value.{k} must be one of {sorted(ENUMS[attr])}")
    elif attr == "frost":
        if not (isinstance(v, dict) and (isinstance(v.get("min_temp_c"), (int, float))
                                        or re.fullmatch(r"\d{1,2}[ab]", str(v.get("usda_zone_min", ""))))):
            errs.append("frost: value needs min_temp_c (number) or usda_zone_min like '10a'")
    elif attr == "foliage":
        if not (isinstance(v, dict) and v.get("habit") in FOLIAGE_HABIT):
            errs.append(f"foliage: value.habit must be one of {sorted(FOLIAGE_HABIT)}")
    elif attr == "flowering":
        if not (isinstance(v, dict) and isinstance(v.get("months"), list) and isinstance(v.get("colours"), list)
                and all(isinstance(m, int) and 1 <= m <= 12 for m in v["months"])):
            errs.append("flowering: value needs months (1-12 ints) and colours (list); empty lists if none")
    elif attr == "sun":
        if not (isinstance(v, dict) and v.get("classes") and set(v["classes"]) <= {"full_sun", "part_shade", "shade"}):
            errs.append("sun: value.classes must be a non-empty subset of full_sun/part_shade/shade")
    elif attr == "accepted_name":
        if not (isinstance(v, dict) and v.get("name") and v.get("family")):
            errs.append("accepted_name: value needs name and family")
    elif attr == "litter":
        if not (isinstance(v, dict) and v.get("text")):
            errs.append("litter: value needs text (and leaf/fruit/flower classes where stated)")
    elif attr == "egypt_availability":
        if not (isinstance(v, dict) and v.get("text")):
            errs.append("egypt_availability: value needs text")
    return errs


def validate_species(rec: dict) -> list[str]:
    """Return a list of errors (empty = valid)."""
    errs: list[str] = []
    for k in ("slug", "layers", "pond_relevant", "attributes"):
        if k not in rec:
            errs.append(f"record missing {k}")
    if errs:
        return errs
    if not rec["layers"] or not set(rec["layers"]) <= LAYERS:
        errs.append(f"layers must be a non-empty subset of {sorted(LAYERS)}")
    at = rec["attributes"]
    for a in REQUIRED:
        if a not in at:
            errs.append(f"{a}: required attribute missing")
            continue
        o = at[a]
        st = o.get("status") if isinstance(o, dict) else None
        if st not in STATUSES:
            errs.append(f"{a}: status must be one of {sorted(STATUSES)}")
        elif st == "SOURCED":
            errs += _check_value(a, o.get("value"))
            errs += _check_source(a, o.get("source"))
        elif st == "GAP":
            if not o.get("reason"):
                errs.append(f"{a}: GAP needs a reason")
            if not o.get("searched"):
                errs.append(f"{a}: GAP needs 'searched' (what was looked at)")
        elif st == "NA":
            if not (a == "toxicity_fish" and not rec["pond_relevant"] and o.get("reason")):
                errs.append(f"{a}: NA is only allowed for toxicity_fish on a non-pond species, with a reason")
        elif st == "POLICY":
            if a != "egypt_availability" or not o.get("value", {}).get("text", "").startswith("unknown"):
                errs.append(f"{a}: POLICY status only for egypt_availability 'unknown — supplier check'")
    for d in rec.get("lead_decisions", []):
        if not (isinstance(d, dict) and d.get("factor") in ("frost", "heat", "alkaline_soil")
                and d.get("decision") == "accepted" and d.get("reason") and d.get("note")):
            errs.append("lead_decisions: each needs factor (frost/heat/alkaline_soil), decision 'accepted', reason and note")
    if rec["pond_relevant"] and at.get("toxicity_fish", {}).get("status") == "NA":
        errs.append("toxicity_fish: pond-relevant species cannot be NA")
    av = at.get("egypt_availability", {})
    if av.get("status") == "SOURCED" and av.get("source", {}).get("url", "").startswith("held:"):
        errs.append("egypt_availability: a held book cannot source Egyptian availability")
    return errs


def load_species(directory: Path = DATA / "species") -> dict[str, dict]:
    out, bad = {}, {}
    for p in sorted(Path(directory).glob("*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        e = validate_species(rec)
        if rec.get("slug") != p.stem:
            e.append(f"slug {rec.get('slug')!r} does not match file name {p.stem!r}")
        if e:
            bad[p.name] = e
        out[p.stem] = rec
    if bad:
        raise SpeciesError(json.dumps(bad, indent=1))
    return out


def site_viability(rec: dict, climate: dict = SITE_CLIMATE) -> dict:
    """Derived (never stored by hand). Per factor: pass / conditional / fail / unknown, then a verdict.

    Verdict: any fail -> not_viable; else any conditional -> viable_with_conditions; else any unknown
    (a GAP in frost, heat or alkaline-soil tolerance) -> unverified; else viable. A GAP is never read as
    a pass. Frost: hardy to <= the policy floor (0 C) passes; hardy only to 0..typical-year minimum
    (5.1 C) is conditional; needs warmer than that fails. Heat: class low fails, moderate is conditional.
    Alkaline soil: intolerant is conditional (site soil pH is untested). All thresholds are our policy
    (docs/lanes/LDL.md), not a published standard.
    """
    at, reasons = rec["attributes"], []
    f, h, a = at["frost"], at["heat"], at["alkaline_soil"]
    factors = {}
    if f["status"] != "SOURCED":
        factors["frost"] = "unknown"
        reasons.append("frost tolerance is a GAP")
    else:
        v = f["value"]
        t = v.get("min_temp_c")
        if t is None:
            # USDA zones: 10a lower bound is -1.1 C; each half-zone is 5 F = 2.78 C
            z = v["usda_zone_min"]
            t = round(-1.1 + (int(z[:-1]) - 10) * 5.56 + (2.78 if z[-1] == "b" else 0), 1)
        if t <= climate["frost_floor_policy_c"]:
            factors["frost"] = "pass"
        elif t <= climate["typical_year_min_c"]:
            factors["frost"] = "conditional"
            reasons.append(f"frost: hardy only to {t} C; typical-year minimum is {climate['typical_year_min_c']} C, floor policy {climate['frost_floor_policy_c']} C")
        else:
            factors["frost"] = "fail"
            reasons.append(f"frost: needs >= {t} C but typical-year minimum is {climate['typical_year_min_c']} C")
    if h["status"] != "SOURCED":
        factors["heat"] = "unknown"; reasons.append("heat tolerance is a GAP")
    elif h["value"]["class"] == "low":
        factors["heat"] = "fail"; reasons.append("heat: low tolerance; 154 days with daily max above 30 C")
    elif h["value"]["class"] == "moderate":
        factors["heat"] = "conditional"; reasons.append("heat: moderate tolerance; plant in afternoon shade or verify locally")
    else:
        factors["heat"] = "pass"
    if a["status"] != "SOURCED":
        factors["alkaline_soil"] = "unknown"; reasons.append("alkaline-soil tolerance is a GAP (site soil unmeasured)")
    elif a["value"]["class"] == "intolerant":
        factors["alkaline_soil"] = "conditional"; reasons.append("alkaline soil: intolerant; conditional on soil test (a professional item; site pH not tested)")
    else:
        factors["alkaline_soil"] = "pass"
    # Lead decisions (e.g. a client-chosen species): only a *conditional* factor can be accepted; a fail never is.
    for d in rec.get("lead_decisions", []):
        if factors.get(d["factor"]) == "conditional" and d.get("decision") == "accepted" and d.get("reason"):
            factors[d["factor"]] = "accepted"
            reasons.append(f"{d['factor']}: accepted by lead decision ({d['reason']})")
    vals = {("pass" if v == "accepted" else v) for v in factors.values()}
    verdict = ("not_viable" if "fail" in vals else "viable_with_conditions" if "conditional" in vals
               else "unverified" if "unknown" in vals else "viable")
    return {"verdict": verdict, "factors": factors, "reasons": reasons}


def placement_constraints(rec: dict) -> list[str]:
    """Derived placement rules from toxicity (people, fish). Never stored by hand."""
    at, out = rec["attributes"], []
    tp = at["toxicity_people"]
    if tp["status"] == "SOURCED" and tp["value"]["class"] in ("toxic", "highly_toxic"):
        out.append("away from seating and edibles (toxic to people per source)")
    tf = at["toxicity_fish"]
    if tf["status"] == "SOURCED" and tf["value"]["class"] in ("toxic", "highly_toxic"):
        out.append("not beside the koi pond (toxic to fish per source)")
    elif rec["pond_relevant"] and tf["status"] != "SOURCED":
        out.append("not beside the koi pond until sourced (fish toxicity is a GAP)")
    if rec.get("koi_pond_note"):
        out.append("not beside the koi pond: " + rec["koi_pond_note"])
    return out


def build_plants_json(directory: Path = DATA / "species", out: Path = DATA / "plants.json") -> dict:
    """Assemble plants.json from validated species files (raises on any invalid file)."""
    species = load_species(directory)
    rejected_p = DATA / "rejected.json"
    rejected = json.loads(rejected_p.read_text(encoding="utf-8")) if rejected_p.exists() else []
    qp = DATA / "quote-verification.json"   # written by verify_quotes; merged in so consumers see it
    qc = json.loads(qp.read_text(encoding="utf-8")) if qp.exists() else {}
    for slug, rec in species.items():
        for a, res in qc.get(slug, {}).items():
            rec["attributes"][a]["quote_check"] = res
    doc = {
        "schema": "plant-library/1",
        "site_climate": SITE_CLIMATE,
        "species": [dict(species[s], site_viability=site_viability(species[s]), placement_constraints=placement_constraints(species[s])) for s in sorted(species)],
        "rejected": rejected,
    }
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def main(argv: list[str]) -> int:
    """python -m archpipe.landscape.plants.library [species.json ...]  (no args: all species + rebuild plants.json)"""
    if not argv:
        try:
            doc = build_plants_json()
        except SpeciesError as e:
            print(e); return 1
        print(f"OK {len(doc['species'])} species; plants.json rebuilt"); return 0
    rc = 0
    for f in argv:
        e = validate_species(json.loads(Path(f).read_text(encoding="utf-8")))
        print(f, "OK" if not e else "\n  " + "\n  ".join(e)); rc |= bool(e)
    return rc


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
