"""The published worked examples the engine must reproduce (inputs and expected values are the source's own).

`run()` returns one record per case with expected, achieved, tolerance and the card id; the same cases are
asserted in tests/electrical/test_el_reference_cases.py and written into out/checks/L7.json.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import data
from .demand import DemandItem, apartment_diversity, max_demand
from .sizing import Segment, TableSpec, phase_equivalent, size_cable, vd_percent, vd_volts


@dataclass
class RefCase:
    name: str
    criterion: str
    card: str
    quantity: str
    expected: float
    achieved: float
    tol_pct: float          # allowed relative error (%)
    unit: str

    @property
    def error_pct(self) -> float:
        return 100.0 * abs(self.achieved - self.expected) / abs(self.expected) if self.expected else 0.0

    @property
    def ok(self) -> bool:
        return self.error_pct <= self.tol_pct + 1e-9


def run() -> list[RefCase]:
    out: list[RefCase] = []
    kw = lambda p: p * 1000.0 / 240.0
    items = [DemandItem(f"w6-{i}", "thermo_wh", kw(6)) for i in range(2)] + [DemandItem(f"w3-{i}", "thermo_wh", kw(3)) for i in range(7)]
    items += [DemandItem(f"iw-{i}", "inst_wh", kw(3)) for i in range(2)]
    items += [DemandItem("ck-a", "cooker", kw(6)), DemandItem("ck-b", "cooker", kw(6)), DemandItem("ck-c", "cooker", kw(4))]
    items += [DemandItem("disch", "lighting", kw(12), multiplier=1.8)] + [DemandItem(f"ring{i}", "sockets", 30.0) for i in range(8)]
    r = max_demand(items, "shop", 240.0)
    out.append(RefCase("Whitfield Example 6.1 (shop, 3-phase)", "EA4", "EL-EX-WHIT-6.1", "total single-phase current", 486.2, r.total_a, 2.0, "A"))
    out.append(RefCase("Whitfield Example 6.1 (shop, 3-phase)", "EA4", "EL-EX-WHIT-6.1", "three-phase line current", 162.0, r.line_a_3ph, 2.0, "A"))
    r2 = max_demand([DemandItem("cooker", "cooker", 14000 / 240.0, socket_on_cooker=True)], "household", 240.0)
    out.append(RefCase("Whitfield Example 6.2 (cooker 14 kW + socket)", "EA4", "EL-EX-WHIT-6.2", "cooker demand", 29.5, r2.total_a, 2.0, "A"))
    ks = apartment_diversity(25)
    out.append(RefCase("Schneider EIG A12 (25 flats x 6 kVA)", "EA4", "EL-EX-EIG-A12", "apparent power", 69.0, 150 * ks, 2.0, "kVA"))
    out.append(RefCase("Schneider EIG A12 (25 flats x 6 kVA)", "EA4", "EL-EX-EIG-A12", "rising-main current", 100.0, 150 * ks * 1000 / (400 * math.sqrt(3)), 2.0, "A"))

    spec = TableSpec("whit_t47", col="in_insulation_2")
    roof = Segment("roof", 10, ambient_c=50)
    eight = size_cable(12.5, 15, [roof, Segment("cavity", 0.05, group_circuits=8, insulation_mm=50)], spec)
    four = size_cable(12.5, 15, [roof, Segment("cavity", 0.05, group_circuits=4, insulation_mm=50)], spec)
    out.append(RefCase("Whitfield Example 4.1 (50 C roof space, 8 bunched)", "EA5", "EL-EX-WHIT-4.1", "csa", 10.0, eight.csa_mm2 or 0.0, 0.0, "mm2"))
    out.append(RefCase("Whitfield Example 4.1 (two bunches of four)", "EA5", "EL-EX-WHIT-4.1", "csa", 6.0, four.csa_mm2 or 0.0, 0.0, "mm2"))
    out.append(RefCase("Whitfield Example 4.5 (6 mm2, 12.5 A, 14 m)", "EA6", "EL-EX-WHIT-4.5", "voltage drop", 1.28, vd_volts(6, 12.5, 14, "1ph"), 1.0, "V"))
    for name, ib, ir, par, csa in (("C1", 909, 920, 2, 240), ("C3", 526, 526, 2, 120), ("C7", 238, 238, 1, 95)):
        s = size_cable(ib, ir, [], TableSpec("iec_c521_F"), parallel=par)
        out.append(RefCase(f"Schneider worked example cable {name} (method F, 3 PVC)", "EA5", "EL-EX-EIG-WEX", "csa per conductor", float(csa), s.csa_mm2 or 0.0, 0.0, "mm2"))
    v = [vd_volts(240, 909, 5, "3ph", "motor", 2), vd_volts(120, 526, 20, "3ph", "motor", 2), vd_volts(95, 238, 5, "3ph", "motor")]
    vp = [vd_percent(x, "3ph", 400 / math.sqrt(3)) for x in v]
    for nm, exp, got in zip(("C1", "C3", "C7"), (0.12, 0.47, 0.13), vp):
        out.append(RefCase(f"Schneider Fig G72 cable {nm}", "EA6", "EL-EX-EIG-WEX", "voltage drop", exp, got, 5.0, "%"))
    out.append(RefCase("Schneider Fig G72 total at C7", "EA6", "EL-EX-EIG-WEX", "voltage drop", 0.73, sum(vp), 2.0, "%"))
    feeder = vd_volts(70, 150, 50, "3ph", "light", source="g30")
    final = vd_volts(2.5, 20, 20, "1ph", "light", source="g30")
    tot = phase_equivalent(feeder, "3ph") + final
    out.append(RefCase("Schneider Example 2 (feeder + lighting circuit)", "EA6", "EL-EX-EIG-G32", "voltage drop", 10.1, tot, 1.0, "V"))
    out.append(RefCase("Schneider Example 2 (feeder + lighting circuit)", "EA6", "EL-EX-EIG-G32", "voltage drop", 4.4, 100 * tot / 230, 2.0, "%"))
    for rc in out:
        assert data.card(rc.card).status == "sourced"
    return out
