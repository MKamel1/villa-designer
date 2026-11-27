"""LA4 'lying, looking up' (L6d, LV finding 5): the one reclined sightline missed the bed downlight at 89 953 cd/m2 at 39.4 deg off the
vertical of a person lying on the pillow. Every bed of every bedroom now has the eye on each pillow looking straight up."""
import dataclasses

import pytest

from archpipe.lightcalc import villa as V
from archpipe.lightcalc import villa_checks as VC
from archpipe.lightcalc.checks import check_la4_luminance


@pytest.fixture(scope="module")
def villa():
    return V.Villa()


def _dl(villa, room):
    f = next(f for f in villa.fixtures if f.kind == "DL" and f.room == room)
    return V.fixture_placements(f)[0]


def test_every_bed_in_every_bedroom_has_lying_sightlines(villa):
    ids = [s["id"] for s in VC.bed_lying_sightlines(villa)]
    assert {i.split("-lying-up")[0] for i in ids} == {"pb-bed", "kb-bed", "ka-loft-1", "ka-loft-2"}   # FX 2026-11-25: two lofts replace the one bunk
    assert sum(i.startswith("pb-bed") for i in ids) == 2                  # a double bed: both pillows
    assert sum(i.startswith("ka-loft-1") for i in ids) == 1 and sum(i.startswith("ka-loft-2") for i in ids) == 1   # each loft has one declared head end (FX)
    assert all(s["dir"] == (0, 0, 1) and s["cards"] == ("L6-POLICY-LA4-bed-lying-looking-up",) for s in VC.bed_lying_sightlines(villa))


def test_todays_design_downlights_fail_where_the_single_reclined_sightline_passed(villa):
    """Positive: the L6c positions (parents' ambient DL, entry lobby DL, kids' B ambient DL) put 113-123 kcd/m2 into the pillow eye.
    The pre-existing sightline (toward the foot, 17 deg up) passed all of them: that is the gap."""
    sls = {s["id"]: s for s in VC.bed_lying_sightlines(villa)}
    base = _dl(villa, "parents-bed")
    cases = [(dataclasses.replace(base, id="old-bed-DL", position=(19.027, -25.191, 2.7)), "pb-bed-lying-up-min-y-p1", 118_000),
             (dataclasses.replace(base, id="old-entry-DL", position=(18.977, -26.981, 2.7)), "pb-bed-lying-up-min-y-p1", 122_000),
             (dataclasses.replace(base, id="old-kb-DL", position=(16.689, -25.856, 2.7)), "kb-bed-lying-up-min-x", 113_000)]
    for p, sid, approx_l in cases:
        r = check_la4_luminance("villa", [sls[sid]], [p])[0]
        assert r.status == "fail" and r.achieved == pytest.approx(approx_l, rel=0.05), (p.id, r.achieved)
        assert "L6-POLICY-LA4-bed-lying-looking-up" in r.source_ids
    old_reclined = {"id": "parents-bed-lying", "eye": (20.33, -26.191, 0.7), "dir": (0, 1, 0.3)}
    # the bed DL is 53.7 deg from that sightline (outside its 45 deg cone), so LA4 passed it although it is 89 953 cd/m2 at 39.4 deg off
    # the vertical of the lying eye (LV)
    assert check_la4_luminance("villa", [old_reclined], [cases[0][0]])[0].status == "pass"
    assert check_la4_luminance("villa", [dict(old_reclined, dir=(0, 0, 1))], [cases[0][0]])[0].achieved == pytest.approx(89_900, rel=0.02)


def test_the_design_passes_every_lying_sightline(villa):
    res = [r for r in VC.check_la4(villa, VC.bed_lying_sightlines(villa))]
    assert len(res) == 5 and all(r.status == "pass" for r in res), [(r.subject, r.achieved) for r in res if r.status != "pass"]
    assert all("L6-POLICY-LA4-bed-lying-looking-up" in r.source_ids for r in res)


def test_negative_a_downlight_outside_the_cone_or_shielded_stays_quiet(villa):
    """Negative: 2.3 m from the pillow (48 deg) is outside the cone; a shielded declared exception is excluded; the check does not fire on every DL."""
    sl = next(s for s in VC.bed_lying_sightlines(villa) if s["id"] == "pb-bed-lying-up-min-y-p1")
    base = _dl(villa, "parents-bed")
    far = dataclasses.replace(base, position=(sl["eye"][0] + 2.3, sl["eye"][1], 2.7))
    assert check_la4_luminance("villa", [sl], [far])[0].status == "pass"
    over = dataclasses.replace(base, position=(sl["eye"][0], sl["eye"][1], 2.7))
    assert check_la4_luminance("villa", [sl], [over])[0].status == "fail"                      # straight overhead is the worst case
    shielded = dataclasses.replace(over, meta={**over.meta, "shielded": True})
    assert check_la4_luminance("villa", [sl], [shielded])[0].status == "pass"


def test_every_card_used_exists():
    from archpipe.lightcalc.sources import CARDS
    assert CARDS["L6-POLICY-LA4-bed-lying-looking-up"].status == "policy"
