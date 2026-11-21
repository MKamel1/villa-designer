"""Emit contracts.CheckResult records for criteria EA1-EA15 from a Design (lane L7)."""
from __future__ import annotations

import re
from collections import Counter

from ..contracts import CheckResult
from . import placement, reference_cases, zones
from .circuits import Design
from .demand import phase_balance
from .schedule import schedule_rows, sld_svg

LANE = "L7"
TABLE_CARD = {"iec_b524": "EL-IEC-B524", "whit_t47": "EL-WHIT-T47", "whit_t46": "EL-WHIT-T47", "iec_c521_F": "EL-IEC-C521"}


def _r(crit, status, subject, message, sources=(), achieved=None, required=None, unit="", gate=False, elements=()):
    return CheckResult(crit, LANE, status, subject, achieved, required, unit, message, tuple(sources), tuple(elements), gate)


def run_checks(d: Design, svg: str | None = None) -> list[CheckResult]:
    h = d.house
    R: list[CheckResult] = []

    # EA1 provision (policy) -------------------------------------------------------------------
    for room in h.rooms:
        need = Counter()
        why = {}
        for kind, n, reason in placement.provision_requirements(h, room):
            need[kind] += n
            why.setdefault(kind, []).append(reason)
        miss = []
        for kind, n in need.items():
            have = placement.provision_count(d.devices, room.id, kind)
            if have < n:
                miss.append(f"{kind}: {have} < {n} ({'; '.join(why[kind])})")
        R.append(_r("EA1", "fail" if miss else "pass", room.id,
                    ("missing " + "; ".join(miss)) if miss else f"all {sum(need.values())} carded minima met ({', '.join(f'{k} {v}' for k, v in need.items())})",
                    ["EL-POL-PLACEMENT"], sum(1 for k, n in need.items() if placement.provision_count(d.devices, room.id, k) >= n), len(need), "kinds"))
    R.append(_r("EA1", "not_evaluated", "recall", "recall against >= 3 engineer-marked rooms not run: no engineer markup available; EA1 rules are policy cards"))

    # EA2 zones --------------------------------------------------------------------------------
    viol = placement.validate_devices(h, d.devices)
    for room in (r for r in h.rooms if r.kind == "bathroom"):
        vs = [v for v in viol if v.room == room.id and v.severity == "fail" and v.rule.startswith("EA2")]
        ws = [v for v in viol if v.room == room.id and v.severity == "warn"]
        n_dev = sum(1 for x in d.devices if x.room == room.id)
        R.append(_r("EA2", "fail" if vs else "pass", room.id,
                    "; ".join(f"{v.device}: {v.message}" for v in vs) if vs else f"{n_dev} devices checked against zones 0-2; no socket-outlet or fixed device in a zone",
                    ["EL-701-ZONE0", "EL-701-ZONE1", "EL-701-ZONE2"], len(vs), 0, "violations", gate=True, elements=[v.device for v in vs]))
        for v in ws:
            R.append(_r("EA2", "warn", f"{room.id}/{v.device}", v.message, [v.card], gate=False, elements=[v.device]))
        serving = [c for c in d.circuits if room.id in c.rooms]
        bad = [c.id for c in serving if not (c.rcd_ma and c.rcd_ma <= 30)]
        R.append(_r("EA2", "fail" if bad else "pass", f"{room.id}/rcd", f"circuits serving the room: {', '.join(c.id for c in serving)}; 30 mA RCD missing on {bad}" if bad
                    else f"all {len(serving)} circuits serving the room are on 30 mA RCDs", ["EL-701-RCD", "EL-EIG-Q7-RCD"], len(bad), 0, "circuits", gate=True))

    # EA3 circuits -----------------------------------------------------------------------------
    zone_circuits: dict[str, list[str]] = {}
    for c in d.circuits:
        for z in c.zone_ids:
            zone_circuits.setdefault(z, []).append(c.id)
        if c.kind == "lighting":
            R.append(_r("EA3", "pass" if c.ib_a <= 10.0 + 1e-9 else "fail", c.id, f"lighting Ib {c.ib_a:.2f} A vs 10 A; zones {', '.join(c.zone_ids)}",
                        ["EL-POL-CIRCUITS"], c.ib_a, 10.0, "A", elements=c.zone_ids))
    for z in h.zones:
        n = len(zone_circuits.get(z.id, []))
        R.append(_r("EA3", "pass" if n == 1 else "fail", z.id, f"control zone on {n} circuit(s): {zone_circuits.get(z.id, [])}", ["EL-POL-CIRCUITS"], n, 1, "circuits"))
    for e in h.equipment:
        n = sum(1 for c in d.circuits if c.kind == "dedicated" and e.id in c.load_ids)
        R.append(_r("EA3", "pass" if n == 1 else "fail", e.id, f"dedicated equipment on {n} dedicated circuit(s)", ["EL-POL-CIRCUITS"], n, 1, "circuits"))

    # EA4 max demand ---------------------------------------------------------------------------
    f = d.feeder
    mb = h.supply.main_breaker_a
    status = "pass" if (mb is None or f["ib_a"] <= mb) else "fail"
    R.append(_r("EA4", status, "installation",
                f"connected {d.demand.connected_a:.1f} A -> max demand {d.demand.total_a:.1f} A single-phase equiv. = {d.demand.kva:.1f} kVA at {h.supply.v_phase:g} V; "
                f"worst-phase line current {f['ib_a']:.1f} A vs main breaker {mb} A. Diversity: Whitfield Table 6.2 (household column, 16th-ed. reprint of the OSG percentages); "
                f"IET OSG Appendix A itself not obtained",
                ["EL-WHIT-T62-DIV", "EL-EIG-A14-DIV"], f["ib_a"], mb, "A"))
    for rc in reference_cases.run():
        if rc.criterion == "EA4":
            R.append(_r("EA4", "pass" if rc.ok else "fail", f"REF {rc.name}: {rc.quantity}", f"expected {rc.expected:g} {rc.unit}, achieved {rc.achieved:.4g} (error {rc.error_pct:.2f} % <= {rc.tol_pct:g} %)",
                        [rc.card], rc.achieved, rc.expected, rc.unit))

    # EA5 sizing -------------------------------------------------------------------------------
    for c in d.circuits:
        sz = c.size
        ok = bool(sz and sz.ok and c.ib_a <= c.in_a + 1e-9)
        cards = ["EL-IEC-B5214-CA", "EL-IEC-B5217-CG", "EL-WHIT-T45-CI"] + [TABLE_CARD.get(c.spec.kind, "EL-WHIT-T47")] if c.spec else ["EL-WHIT-T47"]
        R.append(_r("EA5", "pass" if ok else "fail", c.id,
                    (f"Ib {c.ib_a:.2f} <= In {c.in_a:g} <= Iz {sz.iz_a:.1f} A (csa {c.csa_mm2:g} mm2; {sz.detail.get('worst_segment', '')} factor {sz.factor:.3f})" if ok else "no compliant size"),
                    cards, sz.iz_a if sz else None, c.in_a, "A", gate=True))
    fs = f["size"]
    R.append(_r("EA5", "pass" if fs.ok else "fail", "incomer", f"Ib {f['ib_a']:.1f} <= In {f['in_a']:g} <= Iz {fs.iz_a:.1f} A, {fs.csa_mm2} mm2 (3 loaded PVC, method C, {h.supply.feeder_ambient_c:g} C)" if fs.ok else "no size",
                ["EL-IEC-B524", "EL-IEC-B5214-CA"], fs.iz_a, f["in_a"], "A", gate=True))
    for rc in reference_cases.run():
        if rc.criterion == "EA5":
            R.append(_r("EA5", "pass" if rc.ok else "fail", f"REF {rc.name}: {rc.quantity}", f"expected {rc.expected:g} {rc.unit}, achieved {rc.achieved:g}", [rc.card], rc.achieved, rc.expected, rc.unit))

    # EA6 voltage drop ---------------------------------------------------------------------------
    for c in d.circuits:
        R.append(_r("EA6", "pass" if c.vd_total_pct <= c.vd_limit_pct + 1e-9 and c.size and c.size.ok else "fail", c.id,
                    f"{c.vd_total_pct:.2f} % from the origin (incomer {100 * f['vd_ph_v'] / h.supply.v_phase:.2f} % + circuit {c.vd_pct:.2f} %) vs {c.vd_limit_pct:g} %",
                    ["EL-IEC-G521-VDLIM", "EL-WHIT-T47", "EL-EIG-G30-VD"], c.vd_total_pct, c.vd_limit_pct, "%"))
    for rc in reference_cases.run():
        if rc.criterion == "EA6":
            R.append(_r("EA6", "pass" if rc.ok else "fail", f"REF {rc.name}: {rc.quantity}", f"expected {rc.expected:g} {rc.unit}, achieved {rc.achieved:.4g} (error {rc.error_pct:.2f} %)", [rc.card], rc.achieved, rc.expected, rc.unit))

    # EA7 fault protection -------------------------------------------------------------------------
    s = h.supply
    for c in d.circuits:
        card = "EL-IEC-4-41-TT-F13" if s.earthing == "TT" else "EL-IEC-4-41-TN-F19"
        if s.earthing == "TT":
            if s.ra_ohm is None:
                R.append(_r("EA7", "not_evaluated", c.id, "TT: electrode resistance RA not measured/confirmed"))
                continue
            volts = s.ra_ohm * (c.rcd_ma or 0) / 1000.0
            ok = c.rcd_ma is not None and volts <= 50.0 and c.disconnect_s is not None and c.disconnect_s <= (c.disconnect_limit_s or 0)
            R.append(_r("EA7", "pass" if ok else "fail", c.id, f"{c.protection_note}; limit {c.disconnect_limit_s} s ({s.v_phase:g} V TT final circuit). RA {s.ra_ohm:g} ohm: {s.ra_note or 'provenance not stated'}", [card, "EL-IEC-TT-RA", "EL-IEC-RCD-TIMES-F14"], volts, 50.0, "V", gate=True))
        else:
            if s.ze_ohm is None:
                R.append(_r("EA7", "not_evaluated", c.id, "TN: external loop impedance Ze not known"))
                continue
            ok = c.disconnect_s is not None and c.disconnect_s <= (c.disconnect_limit_s or 0)
            R.append(_r("EA7", "pass" if ok else "fail", c.id, c.protection_note, [card, "EL-EIG-H28-CURVES"], c.zs_ohm, None, "ohm", gate=True))

    # EA8 RCD ---------------------------------------------------------------------------------------
    for c in d.circuits:
        ok = c.rcd_ma is not None and c.rcd_ma <= 30 and c.rcd_type in ("A", "F", "B")
        R.append(_r("EA8", "pass" if ok else "fail", c.id, f"{c.kind} circuit: {c.rcd_ma} mA Type {c.rcd_type}", ["EL-EIG-Q7-RCD", "EL-POL-RCD"], c.rcd_ma, 30.0, "mA", gate=True))

    # EA9, EA10, EA14, EA15: not evaluated here -------------------------------------------------------
    R.append(_r("EA9", "not_evaluated", "installation", "SPD Type 2 is drawn on the SLD; the IEC 62305-2 lightning risk calculation is not part of this engine"))
    R.append(_r("EA10", "not_evaluated", "installation", "electrode RA must be measured/confirmed with the utility; main bonding and test points are not modelled"))
    R.append(_r("EA14", "not_evaluated", "installation", "Revit read-back not in scope of the engine proof (E-12 is a later step)"))
    R.append(_r("EA15", "not_evaluated", "installation", "ELV and fire detection layout is not in this engine (E-10)"))

    # EA11 phase balance ------------------------------------------------------------------------------
    if s.phases == 3:
        ok, dev = phase_balance(d.phase_loads, 0.10)
        R.append(_r("EA11", "pass" if ok else "fail", "installation", f"phase loads (sum Ib) {', '.join(f'{k} {v:.1f} A' for k, v in d.phase_loads.items())}; worst deviation {100 * dev:.1f} % of mean",
                    ["EL-POL-PHASEBAL"], 100 * dev, 10.0, "%"))
    else:
        R.append(_r("EA11", "not_evaluated", "installation", "single-phase supply: no phase balance to check"))

    # EA12 boards and SLD -------------------------------------------------------------------------------
    svg = svg if svg is not None else sld_svg(d)
    rows = {r["circuit"] for r in schedule_rows(d)}
    in_svg = set(re.findall(r'<g id="([^"]+)">', svg))
    miss = [c.id for c in d.circuits if c.id not in rows or c.id not in in_svg]
    R.append(_r("EA12", "fail" if miss else "pass", "schedule=SLD=model", f"{len(d.circuits)} circuits in model, {len(rows)} in schedule, {len(in_svg)} in SLD; missing {miss}",
                ["EL-POL-SPARE"], len(d.circuits) - len(miss), len(d.circuits), "circuits"))
    spare = d.ways - len(d.circuits)
    R.append(_r("EA12", "pass" if spare / d.ways >= 0.2 else "fail", "spare ways", f"{spare} of {d.ways} ways spare ({100 * spare / d.ways:.0f} %)", ["EL-POL-SPARE"], 100 * spare / d.ways, 20.0, "%"))

    # EA13 lighting coordination ---------------------------------------------------------------------------
    lum_zone = Counter(l.zone for l in h.luminaires)
    lum_by_id = {l.id: l for l in h.luminaires}
    for l in h.luminaires:
        zs = [z.id for z in h.zones if l.id in z.luminaire_ids]
        if len(zs) != 1:
            R.append(_r("EA13", "fail", l.id, f"luminaire in {len(zs)} zones", ["EL-POL-CIRCUITS"], len(zs), 1, "zones"))
    for c in (c for c in d.circuits if c.kind == "lighting"):
        w_lum = sum(lum_by_id[i].watts for i in c.load_ids)
        R.append(_r("EA13", "pass" if abs(w_lum - c.watts) <= 1.0 and all(i in lum_by_id for i in c.load_ids) else "fail", c.id,
                    f"circuit {c.watts:.0f} W vs sum of {len(c.load_ids)} luminaires {w_lum:.0f} W", ["EL-POL-CIRCUITS"], c.watts, w_lum, "W"))
    unc = [l.id for l in h.luminaires if not any(l.id in c.load_ids for c in d.circuits if c.kind == "lighting")]
    R.append(_r("EA13", "fail" if unc else "pass", "all luminaires", f"{len(h.luminaires)} luminaires, {len(unc)} without a circuit {unc[:5]}", ["EL-POL-CIRCUITS"], len(unc), 0, "luminaires"))
    return R
