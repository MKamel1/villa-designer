"""L6d: the design fixes found by LV's final verification of L6c: output fraction per zone and scene (pendant, island globes, night levels),
the dining pendant scaled to its table, the ADJ product chosen under the pessimistic reading of its beam, V10 status of every bound product."""
import json
from pathlib import Path

import pytest

from archpipe.concept import villa_lighting as VL
from archpipe.lightcalc import villa as V, villa_report as VR

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "knowledge" / "lighting" / "radiance-l6c"
LOW_BY_DESIGN = ("Night", "Film")          # orientation levels: intended at 10-15 %; their dimming floor is stated separately
FLOOR = 0.15


@pytest.fixture(scope="module")
def villa():
    return V.Villa()


def _fractions(villa):
    """(zone, scene) -> scene level x commissioned driver, from the design's own tables (the output fraction of the zone's rated output)."""
    drivers = VL._drivers()
    zones = {}
    for f in villa.fixtures:
        zones.setdefault((V.cluster_of(f.room), VL.zone_id(f)), VL.zone_layer(f))
    out = {}
    for (cl, z), layer in zones.items():
        for scene, spec in VL.SCENES.get(cl, {}).items():
            lv = 0.0
            for key, val in spec.items():
                if key.startswith("*"):
                    if layer == key[1:]:
                        lv = val
                elif z.endswith("-" + key.upper()) or z == key.upper():
                    lv = val
            if lv:
                out[(z, scene)] = lv * min(drivers.get(z, 1.0), 1.0) if z in drivers else lv
    return out


def test_every_zone_runs_at_15_percent_or_more_outside_the_night_and_film_scenes(villa):
    """LV 'output fraction' finding: the Jilly pendant ran at 3.9 % (Evening) / 6.1 % (Dinner) and the island globes at 14 % (Reading)."""
    low = {k: v for k, v in _fractions(villa).items() if v < FLOOR - 1e-9 and k[1] not in LOW_BY_DESIGN}
    assert not low, {k: round(v, 3) for k, v in low.items()}


def test_night_and_film_levels_stay_above_the_dimming_floor_of_the_spec(villa):
    """Night/Film at 10-15 % is intended; the datasheet floor of the one product zone (ERCO DL, 1-100 % CCR) and the 1 % the schedule demands of
    the generic night kinds are both below the lowest level used."""
    fr = _fractions(villa)
    night = {k: v for k, v in fr.items() if k[1] in LOW_BY_DESIGN}
    assert night and min(night.values()) >= 0.01
    assert min(night.values()) >= 0.0999


def test_guard_is_not_vacuous_the_old_pendant_and_globes_would_fail():
    """Negative: with the L6c numbers (Jilly driver 0.13, Evening 0.3, Dinner 0.47; globes 0.70 x Reading 0.2) the guard's own arithmetic is below 15 %."""
    assert 0.13 * 0.3 < FLOOR and 0.13 * 0.47 < FLOOR and 0.70 * 0.2 < FLOOR
    assert 0.50 * 0.40 > FLOOR and 0.50 * 0.32 > FLOOR and 0.70 * 0.22 > FLOOR - 0.0001      # the table pendant (RP65) and the globes now


def test_table_pendant_is_scaled_to_the_table(villa):
    """Client decision 2026-11-22: a decorative pendant scaled to the 1.8 m table (about 1.2 m, policy <= 2/3 of its length), 2700 K, CRI >= 90,
    DALI-2, no phase-cut, V10-verifiable (maker file + datasheet), at a driver <= 0.80."""
    f = next(f for f in villa.fixtures if f.kind == "PEN-LIN")
    tb = villa.fp["dining-table"]
    table_len = max(tb[2] - tb[0], tb[3] - tb[1])
    prod = dict(f.record.product)
    assert prod["code"] == "RP65" and prod["manufacturer"] == "iguzzini"
    size = f.record.definition.spec["length"]
    assert size == pytest.approx(f.length)
    assert table_len * 0.5 <= size <= table_len * 2 / 3                 # a centrepiece (>= half the table) within the policy (<= 2/3)
    row = json.loads((ROOT / "knowledge/lighting/products-frozen.json").read_text())["PEN-LIN"]
    assert row["cct"] == 2700 and row["cri"] >= 90 and row["v10"] == "pass" and "DALI-2" in row["dimming"] and "phase" not in row["dimming"].lower()
    src = json.loads((ROOT / "knowledge/lighting-products/iguzzini/RP65/source.json").read_text())
    assert src["v10"]["v10_status"] == "pass" and any(k.endswith(".ldt") for k in src["files"]) and any(k.endswith("product-page.txt") for k in src["files"])
    assert VL._drivers()["Z-B-DINING-TABLE-PENDANT"] <= 0.80


def test_dining_cards_are_met_by_the_pendant_alone(villa):
    """The decorative fitting meets both cards without a separate downlight: Dinner table 100 lx and the homework end (Day) 200 lx, from the Radiance
    results with the drivers applied (the scene levels are the design's own)."""
    res = VR.ClusterRes.load(RES / "B-open.json")
    from archpipe.lightcalc.villa_report import scene_levels
    for pid, scene, card in (("dining-table", "Dinner", 100), ("homework-end", "Day", 200)):
        pl = next(p for p in villa.planes() if p.id == pid)
        em = res.stats(pid, scene_levels(res, VL.SCENES["B-open"], scene)).em
        assert em >= card * 0.99, (pid, scene, em)
    assert not [f for f in villa.fixtures if f.room == "dining" and f.kind in ("DL", "DLN")]      # no downlight was needed


def test_every_bound_product_is_v10_pass():
    frozen = json.loads((ROOT / "knowledge/lighting/products-frozen.json").read_text())
    assert {k: v["v10"] for k, v in frozen.items()} == {k: "pass" for k in frozen}, {k: v["v10"] for k, v in frozen.items() if v["v10"] != "pass"}
    assert frozen["ADJ"]["code"] == "A9003138" and frozen["PEN-LIN"]["code"] == "RP65"


class _Narrow:
    """A beam k times narrower than the file: (A) Imax kept (flux falls), (B) flux kept (peak up by 1/k^2)."""
    def __init__(self, ph, k, keep_flux):
        self.ph, self.k, self.s = ph, k, (1 / k ** 2 if keep_flux else 1.0)

    def intensity(self, g, c):
        return self.ph.intensity(g / self.k, c) * self.s

    def __getattr__(self, n):
        return getattr(self.ph, n)


@pytest.mark.parametrize("keep_flux", [False, True])
def test_armchair_card_is_met_at_or_below_080_under_the_pessimistic_beam(villa, keep_flux):
    """LV V10: with the file's beam 20 % wider than published, a literal published beam must still leave the armchair at <= 0.80 driver."""
    import dataclasses
    from archpipe.lightcalc.direct import direct_illuminance
    from archpipe.lightcalc.geometry import grid_in_polygon
    res = VR.ClusterRes.load(RES / "B-open.json")
    pl = next(p for p in villa.planes() if p.id == "armchair")
    lev = VR.scene_levels(res, VL.SCENES["B-open"], pl.scene)
    zone = "Z-B-LOUNGE-ARMCHAIR-READING"
    applied = VL._drivers()[zone]
    others = res.stats(pl.id, dict(lev, **{zone: 0.0})).em
    mine = res.stats(pl.id, {zone: lev[zone]}).em            # at the driver the run contained
    adj = [p for p in villa.cluster_placements("B-open") if p.meta.get("kind") == "ADJ" and p.zone == zone]
    assert adj, "the armchair zone holds an ADJ"
    pts, _, _ = grid_in_polygon(list(pl.polygon), spacing=0.05, border=0.0)
    nominal = sum(direct_illuminance(adj, (x, y, pl.z)) for x, y in pts) / len(pts)
    pess = [dataclasses.replace(p, photometry=_Narrow(p.photometry, 0.8, keep_flux)) for p in adj]
    narrow = sum(direct_illuminance(pess, (x, y, pl.z)) for x, y in pts) / len(pts)
    needed = applied * (pl.target - others) / (mine * narrow / nominal)
    assert 0 < needed <= 0.80, (needed, narrow / nominal)
