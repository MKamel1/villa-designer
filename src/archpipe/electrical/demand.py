"""Maximum demand (EA4): diversity applied per circuit category (Whitfield Table 6.2) and EIG A11/A14."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import data

SQRT3 = math.sqrt(3.0)


@dataclass
class DemandItem:
    id: str
    cat: str            # lighting | heating_power | cooker | inst_wh | thermo_wh | standard | sockets | motors | ac | ev
    current_a: float    # design current Ib (A) at the single-phase voltage
    socket_on_cooker: bool = False
    multiplier: float = 1.0   # e.g. 1.8 for discharge lighting control-gear/pf allowance (Whitfield 6.1)


@dataclass
class DemandResult:
    total_a: float                     # sum of single-phase equivalent currents after diversity
    by_cat: dict = field(default_factory=dict)
    line_a_3ph: float = 0.0            # balanced 3-phase line current = total / 3
    kva: float = 0.0                   # total_a x v_phase / 1000
    connected_a: float = 0.0
    card_ids: tuple[str, ...] = ("EL-WHIT-T62-DIV", "EL-EIG-A14-DIV")


def _cat_demand(rule: dict, items: list[DemandItem]) -> float:
    cur = sorted((i.current_a * i.multiplier for i in items), reverse=True)
    kind = rule["kind"]
    if kind == "total_pct":
        return rule["p"] * sum(cur)
    if kind == "ranked":
        w = rule["w"]
        return sum(c * (w[0] if n == 0 else w[1] if n == 1 else w[2]) for n, c in enumerate(cur))
    if kind == "first_plus":
        tot = sum(cur)
        return min(tot, rule["first"]) + rule["rest"] * max(0.0, tot - rule["first"])
    if kind == "cooker":      # one demand per appliance (each cooker is its own item group)
        d = 0.0
        for it in items:
            c = it.current_a * it.multiplier
            d += min(c, rule["first"]) + rule["rest"] * max(0.0, c - rule["first"]) + (rule["socket_a"] if it.socket_on_cooker else 0.0)
        return d
    raise ValueError(kind)


def max_demand(items: list[DemandItem], premises: str = "household", v_phase: float = 230.0) -> DemandResult:
    rules = data.table("diversity_whitfield_t62")["premises"][premises]
    by_cat, total, connected = {}, 0.0, 0.0
    for cat in sorted({i.cat for i in items}):
        grp = [i for i in items if i.cat == cat]
        if cat not in rules:
            raise KeyError(f"no diversity rule for category {cat!r} in premises {premises!r}")
        d = _cat_demand(rules[cat], grp)
        conn = sum(i.current_a * i.multiplier for i in grp)
        by_cat[cat] = {"connected_a": conn, "demand_a": d, "n": len(grp)}
        total += d
        connected += conn
    return DemandResult(total, by_cat, total / 3.0, total * v_phase / 1000.0, connected)


def apartment_diversity(n_consumers: int) -> float:
    for lo, hi, ks in data.table("diversity_eig_a11_apartments")["rows"]:
        if lo <= n_consumers <= hi:
            return ks
    return 1.0


def phase_balance(loads_by_phase: dict[str, float], tol: float = 0.10) -> tuple[bool, float]:
    """(within tolerance, worst deviation from the mean as a fraction)."""
    vals = list(loads_by_phase.values())
    mean = sum(vals) / len(vals)
    dev = max(abs(v - mean) for v in vals) / mean if mean > 0 else 0.0
    return dev <= tol + 1e-12, dev
