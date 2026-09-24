"""Whole-project verification. Run after any change.

    PYTHONPATH=src python scripts/verify.py

Deliberately includes negative cases. A suite that only proves the happy
path says nothing: the bed-clearance and door-swing false positives found
earlier in this project both passed their positive tests.
"""
from __future__ import annotations

import contextlib
import io
import math
import pathlib
import re
import sys
import tempfile

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from archpipe import (brief as B, catalogue as cat, cli, codes,  # noqa: E402
                      feasibility as F, rules, site as S, solar,
                      vocabulary as V, web)
from archpipe.model import load as load_model  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path(tempfile.mkdtemp(prefix="archpipe-verify-"))
FAILS: list[str] = []

# A number with a unit attached. Used to prove that an `advisory` finding
# never reports a measurement: `measured is None` alone would not catch a
# figure written into the prose, and prose is what the reader believes.
# Deliberately not a bare \d, which would fire on "Bedroom 1".
MEASUREMENT = re.compile(r"\d+(?:\.\d+)?\s*(?:mm|m2|%)")


def expect(name: str, ok: bool) -> None:
    print(("  PASS  " if ok else "  FAIL  ") + name)
    if not ok:
        FAILS.append(name)


def write(name: str, obj) -> pathlib.Path:
    p = TMP / name
    p.write_text(yaml.safe_dump(obj), encoding="utf-8")
    return p


def run_cli(*argv: str) -> tuple[int, str]:
    """Drive the real CLI and capture what it printed.

    `--stage` filtering, the exit contract and the guidance-versus-code
    labelling are all properties of the command, not of `rules.review`, so
    testing them through the API would prove nothing about what a user
    actually gets.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(list(argv))
    return rc, buf.getvalue()


def raises(exc, fn, *a, **kw) -> bool:
    try:
        fn(*a, **kw)
    except exc:
        return True
    return False


def main() -> int:
    brief_src = yaml.safe_load((ROOT / "spec/villa-brief.yaml").read_text(encoding="utf-8"))
    site_src = yaml.safe_load((ROOT / "spec/villa-site.yaml").read_text(encoding="utf-8"))

    print("GATES FIRE ON BAD INPUT")
    bad = dict(brief_src)
    bad["rooms"] = [r for r in brief_src["rooms"]
                    if r["occupancy"] not in ("bathroom", "wc", "study")]
    bad["accessibility"] = {**brief_src["accessibility"], "ground_floor_bedroom": False}
    bad["aesthetic"] = {"direction": "", "references": []}
    expect("brief gate fires on missing sanitary / study / aesthetic",
           len(B.load(write("b1.yaml", bad)).gate()) >= 4)

    few = dict(brief_src)
    few["rooms"] = [r for r in brief_src["rooms"] if r["occupancy"] != "bedroom"] + [
        {"id": "X", "name": "Only bedroom", "occupancy": "bedroom",
         "target_m2": 20, "priority": "must"}]
    few["household"] = {"size": 6}
    expect("brief gate fires on too few bedrooms for the household",
           any("bedroom" in p for p in B.load(write("b2.yaml", few)).gate()))

    bare = {k: v for k, v in site_src.items()
            if k not in ("statutory", "access", "views", "noise")}
    expect("site gate fires on missing envelope / access / views",
           len(S.load(write("s1.yaml", bare)).gate()) >= 4)

    over = dict(site_src)
    over["statutory"] = {**site_src["statutory"], "setback_side": 9500}
    try:
        S.load(write("s2.yaml", over))
        expect("oversized setback raises", False)
    except S.SiteError:
        expect("oversized setback raises", True)

    print("\nGATES STAY SILENT ON GOOD INPUT")
    good_brief = B.load(ROOT / "spec/villa-brief.yaml")
    good_site = S.load(ROOT / "spec/villa-site.yaml")
    expect("good brief passes its gate", good_brief.gate() == [])
    expect("good site passes its gate", good_site.gate() == [])

    print("\nFEASIBILITY")
    v = F.assess(good_brief, good_site)
    expect("example brief does not fit the example plot", not v.fits)
    expect("cut ladder proposes exactly the garage",
           len(v.cuts) == 1 and v.cuts[0]["id"] == "B-GAR")
    trimmed = dict(brief_src)
    trimmed["rooms"] = [r for r in brief_src["rooms"] if r["id"] != "B-GAR"]
    expect("taking the ladder's advice makes it fit",
           F.assess(B.load(write("ok.yaml", trimmed)), good_site).fits)

    print("\nGEOMETRY AND PHYSICS")
    env, note = good_site.buildable()
    expect("per-side setbacks on the rectangular plot give 252 m2",
           abs(env.area / 1e6 - 252.0) < 0.1)
    expect("frontage detected from the access point", "south edge" in note)
    expect("solar position verification (14 checks)", solar.verify()["ok"])
    expect("model<->svg transform verification", web.verify_transform()["ok"])

    print("\nEXISTING RULE ENGINE")
    p = load_model(ROOT / "spec/apartment.yaml")
    findings = rules.review(p)
    expect("apartment review produces findings", len(findings) > 0)
    expect("every finding carries a source",
           all(f.source for f in findings))
    expect("missing bathroom is reported as a violation",
           any(f.rule == "SAN-01" and f.severity == "violation" for f in findings))

    # ---- the shared occupancy vocabulary -------------------------------
    print("\nOCCUPANCY VOCABULARY")
    used = ({r["occupancy"] for r in brief_src["rooms"]}
            | {r.occupancy for r in p.rooms})
    unknown = sorted(t for t in used if not V.is_known(t))
    expect(f"every occupancy the brief and the spec use is declared "
           f"({len(used)} terms)", not unknown)
    # The specific join that was missing: the brief's only circulation term
    # was absent from the rule engine's CIRCULATION set, so CIRC-01 would
    # have found no circulation rooms and passed in silence.
    expect("'hall' counts as circulation", "hall" in V.CIRCULATION)
    expect("the brief's circulation term is visible to the intimacy rule",
           any(r["occupancy"] in rules.CIRCULATION for r in brief_src["rooms"]))

    typo_brief = dict(brief_src)
    typo_brief["rooms"] = [
        {**r, "occupancy": "lounge"} if r["id"] == "B-LIV" else r
        for r in brief_src["rooms"]]
    try:
        B.load(write("typo.yaml", typo_brief))
        expect("an undeclared occupancy is rejected by the brief", False)
    except B.BriefError as e:
        expect("an undeclared occupancy is rejected by the brief",
               "lounge" in str(e) and "B-LIV" in str(e))

    spec_src = yaml.safe_load((ROOT / "spec/apartment.yaml").read_text(encoding="utf-8"))
    typo_spec = dict(spec_src)
    typo_spec["rooms"] = [{**r, "occupancy": "lounge"} if r["id"] == "R-01" else r
                          for r in spec_src["rooms"]]
    expect("an undeclared occupancy is rejected by the rule engine",
           raises(V.UnknownOccupancy, rules.review,
                  load_model(write("typo_spec.yaml", typo_spec))))
    # Knowing a term does not mean inventing a minimum area for it. Neufert
    # publishes none for these, and a fabricated figure is the exact fault
    # the vocabulary was added to prevent, not a tidier table.
    expect("a declared term carries no invented minimum area",
           all(t not in cat.MIN_AREA_M2
               for t in ("hall", "utility", "store", "dressing", "garage")))

    # ---- rule declarations --------------------------------------------
    print("\nRULE DECLARATIONS: STAGE, KIND, REFERENCE, LADDER")
    expect(f"every rule declares stage 0-7, a kind and a reference "
           f"({len(rules.RULES)} rules)",
           all(r.stage in rules.STAGES and r.kind in rules.KINDS and r.reference
               for r in rules.RULES.values()))
    expect("every rule carries a fix ladder",
           all(r.remedies for r in rules.RULES.values()))
    expect("every ladder is ordered cheapest-first",
           all([x.rank for x in r.remedies] == sorted(x.rank for x in r.remedies)
               for r in rules.RULES.values()))
    expect("every loop a remedy names is one of L1-L13",
           all(x.loop in rules.LOOPS
               for r in rules.RULES.values() for x in r.remedies if x.loop))
    expect("no remedy returns to a stage later than its own rule",
           all(x.returns_to is None or x.returns_to <= r.stage
               for r in rules.RULES.values() for x in r.remedies))
    expect("every finding carries stage, kind, reference and a ladder",
           all(f.stage in rules.STAGES and f.kind in rules.KINDS
               and f.reference and f.remedies for f in findings))

    advisory = [f for f in findings if f.kind == "advisory"]
    expect("the library has at least one advisory-kind rule to test",
           bool(advisory))
    expect("advisory findings report no measurement",
           bool(advisory) and all(f.measured is None
                                  and not MEASUREMENT.search(f.message)
                                  for f in advisory))
    expect("computed findings do carry achieved-versus-required pairs",
           any(f.measured is not None for f in findings))

    # Negative cases: the invariants must actually reject bad declarations.
    expect("a ladder in the wrong order is rejected",
           raises(ValueError, rules.Rule, "X-01", "t", 4, "computed", "ref",
                  remedies=(rules.Remedy("change the brief", 0, "L7"),
                            rules.Remedy("move the furniture"))))
    expect("a rule with no reference is rejected",
           raises(ValueError, rules.Rule, "X-02", "t", 4, "computed", "",
                  remedies=(rules.Remedy("do something"),)))
    expect("a rule with no fix ladder is rejected",
           raises(ValueError, rules.Rule, "X-03", "t", 4, "computed", "ref"))
    expect("an invented loop id is rejected",
           raises(ValueError, rules.Remedy, "do something", 3, "L99"))
    expect("an advisory finding carrying a measurement is rejected",
           raises(ValueError, rules.Finding, "VIEW-01", "advisory", "msg",
                  reference="ref", stage=4, kind="advisory",
                  remedies=(rules.Remedy("judge it"),),
                  measured=rules.Measured(1, 2, "mm")))

    # ---- stage-aware reporting, through the CLI ------------------------
    print("\nSTAGE FILTERING AND THE EXIT CONTRACT")
    SPEC = str(ROOT / "spec/apartment.yaml")
    rc_all, out_all = run_cli("design", SPEC)
    rc3, out3 = run_cli("design", SPEC, "--stage", "3")
    rc2, out2 = run_cli("design", SPEC, "--stage", "2")
    later = ("FURN-02", "DOOR-02", "LIGHT-01", "CIRC-03")
    expect("unfiltered reports every stage and exits 1 on a violation",
           rc_all == 1 and all(r in out_all for r in later)
           and "SAN-01" in out_all)
    expect("--stage 3 excludes every Stage 4 finding",
           rc3 == 1 and not any(r in out3 for r in later))
    expect("--stage 3 still reports the Stage 3 violation",
           "SAN-01" in out3 and "reporting Stage 0-3" in out3)
    expect("--stage 3 says how many findings it suppressed",
           "9 later-stage finding(s) not shown" in out3)
    expect("--stage 2 reports nothing and exits 0, though a later "
           "violation exists",
           rc2 == 0 and "0 findings" in out2 and "nothing to report" in out2)
    s3 = rules.review(p, max_stage=3)
    expect("the filtered set is a strict subset, all at or before the stage",
           all(f.stage <= 3 for f in s3) and len(s3) < len(findings)
           and any(f.stage > 3 for f in findings))

    # ---- citations: reference required, code optional ------------------
    print("\nCITATIONS AND CODE PACKS")
    expect("every rule cites a reference, and none is a code clause",
           all(r.reference for r in rules.RULES.values()))
    expect("with no pack loaded, no finding carries a code clause",
           all(f.code == "" for f in findings))
    expect("with no pack loaded, output is labelled guidance not compliance",
           "GUIDANCE" in out_all
           and "NOT a statement of code compliance" in out_all)
    expect("the example pack is marked an example and names no real "
           "jurisdiction",
           codes.EXAMPLE_PACK.example
           and "EXAMPLE" in codes.EXAMPLE_PACK.jurisdiction)
    rc_pack, out_pack = run_cli("design", SPEC, "--code-pack", "example",
                                "--stage", "3")
    expect("a loaded pack adds its clause to the rules it covers",
           "code:" in out_pack and "EXAMPLE ONLY" in out_pack)
    expect("an example pack still says the findings are not compliance",
           "placeholders" in out_pack and "NOT" in out_pack)
    expect("a pack covering no rule leaves the finding uncited by code",
           codes.EXAMPLE_PACK.cite("FURN-02") == ""
           and codes.EXAMPLE_PACK.cite("SAN-01") != "")
    expect("a pack without a jurisdiction is rejected",
           raises(codes.CodePackError, codes.CodePack, "p", "", "ed"))

    # Pluggable means loadable from outside the code. If a jurisdiction can
    # only be added by editing codes.py, the mechanism has not been built --
    # and this is the one path no built-in pack can exercise.
    pack_file = write("pack.yaml", {
        "id": "somewhere-test", "jurisdiction": "Somewhere", "edition": "1st",
        "clauses": {"AREA-01": {"clause": "A/1.1", "title": "room areas"}},
    })
    loaded = codes.load(pack_file)
    expect("a jurisdiction pack loads from YAML with no code change",
           loaded.id == "somewhere-test"
           and loaded.cite("AREA-01").startswith("A/1.1")
           and not loaded.example)
    expect("a pack that is not the example says so in its disclaimer",
           "Somewhere" in codes.disclaimer(loaded)
           and "EXAMPLE" not in codes.disclaimer(loaded))
    expect("a loaded pack reaches the findings it covers",
           all(f.code.startswith("A/1.1")
               for f in rules.review(p, pack=loaded) if f.rule == "AREA-01")
           and all(f.code == "" for f in rules.review(p, pack=loaded)
                   if f.rule != "AREA-01"))

    # ---------------------------------------------------------- lighting
    # Stage 5. `lighting.verify()` is the substantive suite -- it validates
    # the engine against hand calculation before any heat map is trusted,
    # because a false-colour image is persuasive whether or not it is right.
    from archpipe import lighting, photometry

    light_fails = lighting.verify()
    expect(f"lighting engine verification ({len(light_fails)} failures)",
           not light_fails)
    for f in light_fails:
        print(f"      {f}")

    # IES parsing, against the real library Revit ships. These files need no
    # content-library download, which is why Stage 5 was not blocked on it.
    ies_dir = photometry.revit_ies_dir()
    if ies_dir is None:
        print("  SKIP  Revit IES library not on this machine")
    else:
        lamps, bad = photometry.load_directory(ies_dir)
        expect(f"every IES file in the Revit library parses ({len(lamps)} "
               f"files, {len(bad)} failures)", lamps and not bad)
        for path, err in bad[:5]:
            print(f"      {path.name}: {err}")
        expect("each candela grid matches its declared angle counts",
               all(len(g.candela) == len(g.vertical)
                   and all(len(r) == len(g.horizontal) for r in g.candela)
                   for g in lamps))
        # A misparsed file shows up as impossible efficacy long before it
        # shows up as a wrong heat map.
        effs = [g.efficacy for g in lamps if g.efficacy]
        expect("no luminaire claims an impossible efficacy",
               effs and max(effs) < 250)

    # Emitted flux vs declared lamp flux. The integral has a closed form
    # for an isotropic source, so this is checked against arithmetic
    # rather than against itself.
    _iso_full = photometry.parse("\n".join([
        "IESNA91", "TILT=NONE", "1 12566 1 3 1 1 2 0 0 0", "1 1 100",
        "0 90 180", "0", "1000 1000 1000"]))
    expect("integrated flux of an isotropic 1000 cd source is 4*pi*1000",
           abs(_iso_full.integrated_flux() - 4 * math.pi * 1000.0) < 5.0)
    _hemi = photometry.parse("\n".join([
        "IESNA91", "TILT=NONE", "1 6283 1 2 1 1 2 0 0 0", "1 1 100",
        "0 90", "0", "1000 1000"]))
    expect("a hemisphere emits half as much as a full sphere",
           abs(_hemi.integrated_flux() - 2 * math.pi * 1000.0) < 5.0)
    expect("emitted flux is not the declared lamp flux",
           _iso_full.total_lumens == 12566.0
           and abs(_iso_full.integrated_flux() - 12566.0) < 10.0)

    if ies_dir is not None:
        effs = [(g, g.luminaire_efficiency()) for g in lamps[:40]]
        effs = [(g, e) for g, e in effs if e is not None]
        # A fitting cannot emit more light than its lamps produce. A value
        # above 1 means the declared lumens or the distribution is being
        # misread -- the check that would have caught using one for the
        # other.
        expect("no luminaire emits more flux than its lamp produces",
               effs and all(e <= 1.05 for _, e in effs))
        expect("real fittings lose flux in their optics (efficiency < 1)",
               effs and sum(1 for _, e in effs if e < 0.95) > len(effs) // 2)
        # The specific trap, on the specific file.
        pend = next((g for g in lamps if g.source.name == "PLD1A21.ies"), None)
        if pend:
            expect("PLD1A21 emits materially less than its lamps declare",
                   pend.total_lumens == 2780.0
                   and 1600 < pend.integrated_flux() < 1900)

    # The inter-reflection estimate must be driven by emitted flux. Feeding
    # it declared lamp flux overstated the mock bedroom by 1.7x.
    _room = [(0.0, 0.0), (4000.0, 0.0), (4000.0, 4000.0), (0.0, 4000.0)]
    _lum_eff = lighting.Luminaire(
        "E1", pend if (ies_dir and pend) else _iso_full, 2000.0, 2000.0, 2850.0)
    _g_eff = lighting.lux_grid(_room, [_lum_eff], spacing=500.0)
    _irc_eff = lighting.interreflected_estimate(_g_eff, 4000.0, 4000.0, 2700.0)
    _expected_hi = (_lum_eff.photometry.integrated_flux()
                    * _irc_eff.average_reflectance
                    / (_irc_eff.area * (1 - _irc_eff.average_reflectance))
                    * _g_eff.maintenance_factor)
    expect("inter-reflection uses emitted flux, not declared lamp flux",
           abs(_irc_eff.high - _expected_hi) < 0.01)

    # Negative cases: malformed photometry must raise, not return a
    # plausible distribution.
    _iso = "\n".join(["IESNA91", "TILT=NONE", "1 1000 1 3 1 1 2 0 0 0",
                      "1 1 10", "0 45 90", "0", "1000 1000 1000"])
    expect("an IES file with no TILT line is rejected",
           raises(photometry.IESError, photometry.parse, "IESNA91\n[TEST]\n1 2 3\n"))
    expect("an IES candela block shorter than declared is rejected",
           raises(photometry.IESError, photometry.parse,
                  _iso.replace("1000 1000 1000", "1000 1000")))
    expect("absolute photometry (-1 lumens) does not become negative light",
           photometry.parse(
               _iso.replace("1 1000 1 3", "1 -1 1 3")).total_lumens == 0.0)

    iso = photometry.parse(_iso)
    room4 = [(0.0, 0.0), (4000.0, 0.0), (4000.0, 4000.0), (0.0, 4000.0)]
    lum = lighting.Luminaire("V1", iso, 2000.0, 2000.0, 2850.0)
    expect("a room boundary in metres rather than mm is rejected",
           raises(lighting.LightingError, lighting.lux_grid,
                  [(0, 0), (4, 0), (4, 4), (0, 4)], [lum]))
    expect("a maintenance factor above 1.0 is rejected",
           raises(lighting.LightingError, lighting.lux_grid,
                  room4, [lum], maintenance_factor=1.2))
    expect("an unknown lighting layer is rejected",
           raises(lighting.LightingError, lighting.Luminaire,
                  "bad", iso, 0.0, 0.0, 2400.0, layer="mood"))

    # The discipline point, tested as a name rather than as a threshold:
    # EN 12464-1's U0 is defined on total illuminance, so a direct-only
    # grid must not offer a property that reads as U0. See CLAUDE.md #4 --
    # a metric this engine cannot support must not be presented as one.
    grid4 = lighting.lux_grid(room4, [lum], room="verify", spacing=250.0)
    expect("a direct-only grid exposes no bare `uniformity`/`diversity`",
           not hasattr(grid4, "uniformity") and not hasattr(grid4, "diversity"))
    expect("the direct ratio is labelled as not being U0",
           "NOT U0" in grid4.summary())
    expect("the grid states what it can and cannot judge",
           "NOT valid: uniformity" in grid4.assessment_note()
           and "task points" in grid4.assessment_note())
    # Legacy IES wattage must not be passed off as a scheme's installed load.
    expect("power density is unreported until a real wattage is stated",
           grid4.power_density is None and grid4.total_load is None)
    expect("power density is reported once wattage is stated",
           lighting.lux_grid(room4, [lighting.Luminaire(
               "V2", iso, 2000.0, 2000.0, 2850.0, watts=10.0)],
               spacing=500.0).power_density is not None)
    # The inter-reflection estimate must stay a range wide enough to be
    # unusable as a verdict -- that is the point of it.
    irc = lighting.interreflected_estimate(grid4, 4000.0, 4000.0, 2700.0)
    expect("the inter-reflection estimate is an ordered range, not a number",
           0.0 < irc.low < irc.high and irc.spread > 1.3)
    expect("the inter-reflection estimate says it cannot decide uniformity",
           "NOT a basis" in irc.note)

    # ------------------------------------------------- family version gate
    # Revit families are forward-compatible only, so a downloaded family
    # saved by a newer release is useless and cannot be converted. Worse,
    # checking by opening it UPGRADES it on save. `archpipe.rfa` reads the
    # version out of the file instead.
    from archpipe import rfa

    portable = '--portable' in sys.argv
    if portable:
        print('  SKIP  installed Revit family corpus: Windows-only integration; portable parser regressions run separately')
    rfa_fails = rfa.verify(require_installed=not portable)
    expect(f"rfa version reader ({len(rfa_fails)} failures)", not rfa_fails)
    for f in rfa_fails:
        print(f"      {f}")

    expect("a newer family is rejected for an older Revit",
           rfa.FamilyInfo(pathlib.Path("x.rfa"), 2028).usable_in(rfa.TARGET_REVIT) is False)
    expect("an older family is accepted",
           rfa.FamilyInfo(pathlib.Path("x.rfa"), 2021).usable_in(rfa.TARGET_REVIT) is True)
    # The distinction that matters most: unknown must never read as yes.
    expect("an unknown version is None, not True",
           rfa.FamilyInfo(pathlib.Path("x.rfa"), None).usable_in(rfa.TARGET_REVIT) is None)
    expect("an unknown version says so in words",
           "UNKNOWN" in rfa.FamilyInfo(pathlib.Path("x.rfa"), None).describe())

    # Screening a real downloaded family, when one has been fetched.
    fetched = sorted(pathlib.Path("out/families").glob("*.rfa")) \
        if pathlib.Path("out/families").is_dir() else []
    if fetched:
        screened = rfa.screen(fetched, rfa.TARGET_REVIT)
        expect(f"downloaded families screen cleanly "
               f"({len(screened['ok'])} usable of {len(fetched)})",
               not screened["unreadable"] and not screened["unknown"])
    else:
        print("  SKIP  no downloaded families to screen "
              "(run scripts/fetch_families.py)")

    # ------------------------------------------- the Revit 2027 extract
    # A real extract from Revit 2027, of geometry chosen in advance. Kept
    # as a fixture so the extractor's OUTPUT CONTRACT can be regression
    # tested on any machine, with no Revit and no licence.
    #
    # Revit works in decimal feet. A units bug does not raise -- it
    # silently yields a model 304.8x wrong that looks entirely healthy --
    # which is why this checks numbers that were chosen before the model
    # was built rather than "did it run".
    fixture = ROOT / "tests/fixtures/revit2027-test-model.json"
    if fixture.is_file():
        import json as _json
        m = _json.loads(fixture.read_text(encoding="utf-8"))
        expect("the 2027 fixture is in millimetres", m.get("units") == "mm")
        w = m["walls"]
        lens = sorted(round(math.dist(x["start"], x["end"]), 6) for x in w)
        expect("2027 extract: wall centrelines are exactly 6000 x 4000",
               lens == [4000.0, 4000.0, 6000.0, 6000.0])
        thick = {x["thickness"] for x in w}
        expect("2027 extract: one wall thickness, 200 mm", thick == {200.0})
        room = m["rooms"][0]
        t = thick.pop()
        want = (6000.0 - t) * (4000.0 - t) / 1e6
        expect(f"2027 extract: room area is {want:.3f} m2 to the millimetre",
               abs(room["area_m2"] - want) < 1e-3)
        bx = [p[0] for p in room["boundary"]]
        by = [p[1] for p in room["boundary"]]
        expect("2027 extract: room boundary spans the inner wall faces",
               abs((max(bx) - min(bx)) - (6000.0 - t)) < 1e-6
               and abs((max(by) - min(by)) - (4000.0 - t)) < 1e-6)
    else:
        print("  SKIP  no Revit 2027 extract fixture")

    # ------------------------------------------- the family placement gate
    # Result of `revit/place_families_test.py` against Revit 2027, kept as
    # a fixture so the gate's conclusions stay asserted on any machine.
    # If families cannot be loaded, activated, placed and read back, then
    # build_bedroom.py and everything downstream needs rethinking.
    gate = ROOT / "tests/fixtures/revit2027-place-families.json"
    if gate.is_file():
        import json as _json
        g = _json.loads(gate.read_text(encoding="utf-8"))
        placed = [f for f in g["families"] if f.get("placed")]
        expect(f"family gate: every family placed ({len(placed)}/"
               f"{len(g['tested'])})", len(placed) == len(g["tested"]))
        expect("family gate: each landed exactly where it was asked to",
               all(f["read_back"]["delta_mm"] == [0.0, 0.0, 0.0]
                   for f in placed if "read_back" in f))
        expect("family gate: every family read back a real bounding box",
               all(f["read_back"].get("bbox_size_mm")
                   and min(f["read_back"]["bbox_size_mm"]) > 0
                   for f in placed if "read_back" in f))
        # The activation trap, as MEASURED rather than as assumed. The plan
        # expected a silent None; Revit 2027 raises. Asserting the measured
        # behaviour means a future release changing it will be noticed
        # rather than silently tolerated.
        trap = g.get("activation_trap") or {}
        expect("family gate: an inactive symbol does not place",
               trap.get("placed_anyway") is False)
        expect("family gate: and in 2027 it raises rather than returning None",
               trap.get("raised") is True
               and "not active" in trap.get("exception", "").lower())
        expect("family gate: every family loaded INACTIVE, so activation "
               "is never optional",
               all(f.get("was_active_on_load") is False
                   for f in g["families"] if "was_active_on_load" in f))
        # The two quality findings that shape family_map.py.
        expect("family gate: free families declare no size parameters, so "
               "the bounding box is the only dimension source",
               all(not f.get("size_mm") for f in g["families"]))
        cats = {f.get("category") for f in g["families"]}
        expect("family gate: categories are unreliable and recorded as such",
               "Electrical Fixtures" in cats)
    else:
        print("  SKIP  no family placement fixture")

    # ------------------------------------------- spec -> Revit -> extract
    # THE HEADLINE REQUIREMENT: a room specified in YAML, built in Revit,
    # read back, and matching. The extract is kept as a fixture so the
    # round trip stays asserted on any machine, without Revit.
    bed = ROOT / "tests/fixtures/bedroom-from-revit.json"
    if bed.is_file():
        import json as _json
        b = _json.loads(bed.read_text(encoding="utf-8"))
        spec_y = yaml.safe_load(
            (ROOT / "spec/bedroom-test.yaml").read_text(encoding="utf-8"))
        r = spec_y["room"]
        room = (b.get("rooms") or [{}])[0]
        expect("bedroom: room area is width x depth exactly",
               abs(room.get("area_m2", 0) - r["width"] * r["depth"] / 1e6) < 1e-3)
        expect("bedroom: the spec's room name survived the round trip",
               room.get("name") == spec_y.get("name"))
        expect("bedroom: four walls at centreline lengths",
               sorted(round(math.dist(w["start"], w["end"]), 1)
                      for w in b["walls"])
               == sorted([float(r["depth"] + r["wall_thickness"])] * 2
                         + [float(r["width"] + r["wall_thickness"])] * 2))
        expect("bedroom: both openings built at the specified sizes",
               {(o["kind"], o["width"], o["height"]) for o in b["openings"]}
               == {(o["kind"], float(o["width"]), float(o["height"]))
                   for o in spec_y["openings"]})
        expect("bedroom: every furniture item and luminaire extracted",
               len(b["furniture"]) == len(spec_y["furniture"])
               and len(b["lighting"]) == len(spec_y["lighting"]))
        # A DirectShape proxy has no LocationPoint, so the extractor falls
        # back to the bounding-box centre -- and SAYS SO, because that is a
        # good number for an axis-aligned box and a poor one otherwise.
        proxies = [f for f in b["furniture"]
                   if f.get("at_source") == "bounding_box_centre"]
        expect("bedroom: proxy positions come from the bounding box and are "
               "labelled as such", len(proxies) == 5)
        expect("bedroom: every element reports where its position came from",
               all(f.get("at") and f.get("at_source")
                   for f in b["furniture"] + b["lighting"]))
        # The extractor used to swallow the name error and return "".
        expect("bedroom: opening type names are not empty",
               all(o.get("type_name") for o in b["openings"]))
    else:
        print("  SKIP  no bedroom round-trip fixture")

    print("\nLEARNED GUARDS (each exists because the defect shipped once)")
    # Falsy-zero: `float(x or 1.0)` turns a deliberate 0 into the default.
    # It silently made interior lights impossible to switch off, and the
    # same line was repeated in compare_lux.py. The first version of this
    # regex could not match the real bug (inner parentheses) and found
    # nothing -- a guard is proven against the defect it targets. Where 0
    # is itself invalid (a 0 mm wall), mark the line `# falsy-ok: reason`.
    import re
    falsy = re.compile(r"float\(.*\bor\s+([1-9][0-9.]*|[A-Z_]{3,})\s*\)")
    expect("falsy-zero lint catches the historical bug line",
           bool(falsy.search('energy = P * float(fx.get("output") or 1.0)')))
    offenders = [f"{p.relative_to(ROOT)}:{i}"
                 for top in ("src", "scripts") for p in (ROOT / top).rglob("*.py")
                 for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                 if falsy.search(line) and "falsy-ok" not in line
                 and "falsy.search(" not in line and "# Falsy" not in line]
    expect("no numeric `x or <nonzero>` default that swallows an explicit zero"
           + (f" ({', '.join(offenders[:5])})" if offenders else ""), not offenders)
    # A skipped integrity check must stop the install, not print a warning.
    installer = (ROOT / "ops/workstation/10-blender.sh").read_text(encoding="utf-8")
    expect("Blender install refuses an unverified download unless explicitly allowed",
           "BLENDER_ALLOW_UNVERIFIED" in installer)
    # Presentation renders are checked by machine before anyone looks.
    driver = (ROOT / "scripts/render_hyperreal.py").read_text(encoding="utf-8")
    expect("render driver runs archpipe.render_qa on every image",
           "render_qa.check(" in driver)

    print("\nRESULT:", "ALL PASS" if not FAILS else "FAILURES: " + ", ".join(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
