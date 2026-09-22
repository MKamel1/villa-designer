"""Stage 2 (Fit): does the brief fit the ground?

The cheapest check in the whole project. A brief that never fitted the
plot is normally discovered after weeks of drawing; here it is arithmetic
on two YAML files, and it runs before anything is drawn at all.

The gate is binary and blunt on purpose: **the brief fits, or the brief
changes.**
"""
from __future__ import annotations

from dataclasses import dataclass

from .brief import Brief
from .site import Site

# Net-to-gross efficiency for a house: gross includes circulation and the
# area consumed by wall thickness, which a schedule of accommodation never
# counts. General practice puts circulation at 10-15% and walls at 8-12%
# of gross, so net:gross lands around 0.75-0.82. 0.78 is the midpoint and
# is deliberately not optimistic -- an optimistic figure here produces a
# scheme that fails at Stage 4, which is the expensive place to find out.
DEFAULT_EFFICIENCY = 0.78
EFFICIENCY_SOURCE = ("General practice: circulation 10-15% and wall thickness "
                     "8-12% of gross floor area in a dwelling")


@dataclass
class Verdict:
    fits: bool
    net_m2: float
    gross_needed_m2: float
    permitted_m2: float
    binding: str
    footprint_needed_m2: float
    footprint_permitted_m2: float
    footprint_binding: str
    levels: int
    efficiency: float
    headroom_m2: float          # permitted minus needed; negative means over
    notes: list[str]
    cuts: list[dict]            # how to get within budget, cheapest first

    @property
    def over_by_m2(self) -> float:
        return max(0.0, -self.headroom_m2)


def assess(brief: Brief, site: Site, efficiency: float = DEFAULT_EFFICIENCY,
           levels: int | None = None) -> Verdict:
    """Test the brief against the site's permitted envelope."""
    if not 0.4 <= efficiency <= 1.0:
        raise ValueError(f"efficiency {efficiency} is outside a sane range")

    levels = levels or brief.levels_preferred
    net = brief.net_area_m2
    gross = net / efficiency

    permitted, binding = site.max_floor_area_m2()
    foot_permitted, foot_binding = site.max_footprint_m2()
    foot_needed = gross / levels

    notes: list[str] = []
    headroom = permitted - gross
    fits = headroom >= 0

    if foot_needed > foot_permitted:
        fits = False
        notes.append(
            f"Footprint is the problem, not total area: {foot_needed:.0f} m2 "
            f"per level is needed but only {foot_permitted:.0f} m2 is "
            f"permitted. More storeys would fix it if the height limit allows.")
        if site.statutory.max_storeys:
            need_levels = -(-gross // foot_permitted)   # ceil
            if need_levels > site.statutory.max_storeys:
                notes.append(
                    f"Even at the {site.statutory.max_storeys}-storey limit "
                    f"this needs {need_levels:.0f} storeys.")

    if site.statutory.height_limit and site.statutory.max_storeys:
        per_storey = site.statutory.height_limit / site.statutory.max_storeys
        if per_storey < 3000:
            notes.append(
                f"Height limit allows only {per_storey:.0f} mm per storey at "
                f"the permitted storey count -- tight once floor build-up and "
                f"services are taken off.")

    return Verdict(
        fits=fits, net_m2=net, gross_needed_m2=gross, permitted_m2=permitted,
        binding=binding, footprint_needed_m2=foot_needed,
        footprint_permitted_m2=foot_permitted, footprint_binding=foot_binding,
        levels=levels, efficiency=efficiency, headroom_m2=headroom,
        notes=notes,
        # The deficit is a GROSS figure; room areas in the brief are NET.
        # Dropping a room of net area A frees A/efficiency of gross, so the
        # net cut required is the gross deficit scaled by efficiency.
        # Comparing the two directly would over-cut by about a quarter.
        cuts=_cut_ladder(brief, max(0.0, -headroom) * efficiency, efficiency),
    )


def _cut_ladder(brief: Brief, deficit_net_m2: float,
                efficiency: float) -> list[dict]:
    """How to get within budget, cheapest concession first.

    The Stage 2 instance of cheapest-fix-first: drop `nice` before
    `should`, and never propose cutting a `must` without saying so.

    `deficit_net_m2` is in NET terms, matching the brief's room areas.
    """
    if deficit_net_m2 <= 0:
        return []

    ladder: list[dict] = []
    remaining = deficit_net_m2
    for priority in ("nice", "should"):
        rooms = sorted((r for r in brief.rooms if r.priority == priority),
                       key=lambda r: -r.total_m2)
        for r in rooms:
            if remaining <= 0:
                break
            overshoot = r.total_m2 - remaining
            entry = {
                "action": "drop",
                "priority": priority,
                "room": r.name,
                "id": r.id,
                "saves_m2": round(r.total_m2, 1),
                "saves_gross_m2": round(r.total_m2 / efficiency, 1),
                "cost": f"loses a '{priority}' requirement",
            }
            # A cut that overshoots by most of a room is worth naming: the
            # honest alternative is to shrink rather than delete.
            if overshoot > 0 and overshoot > 0.4 * r.total_m2:
                entry["cost"] += (
                    f"; this alone overshoots by {overshoot:.0f} m2, so "
                    f"shrinking it by {remaining:.0f} m2 would also do")
            ladder.append(entry)
            remaining -= r.total_m2

    if remaining > 0:
        ladder.append({
            "action": "shrink",
            "priority": "must",
            "room": "the 'must' list",
            "id": "",
            "saves_m2": round(remaining, 1),
            "saves_gross_m2": round(remaining / efficiency, 1),
            "cost": (f"still {remaining:.0f} m2 (net) over after dropping "
                     f"every optional room. The 'must' list itself has to "
                     f"shrink, or the plot is wrong for this brief."),
        })
    return ladder


def report(v: Verdict) -> str:
    """A readable Stage 2 report."""
    lines = []
    verdict = "FITS" if v.fits else "DOES NOT FIT"
    lines.append(f"Stage 2 (Fit): {verdict}")
    lines.append("")
    lines.append(f"  requested net area      {v.net_m2:8.1f} m2")
    lines.append(f"  gross needed            {v.gross_needed_m2:8.1f} m2  "
                 f"(net / {v.efficiency:.2f} efficiency)")
    lines.append(f"  permitted floor area    {v.permitted_m2:8.1f} m2  "
                 f"({v.binding})")
    lines.append(f"  headroom                {v.headroom_m2:+8.1f} m2")
    lines.append("")
    lines.append(f"  footprint needed        {v.footprint_needed_m2:8.1f} m2  "
                 f"over {v.levels} level(s)")
    lines.append(f"  footprint permitted     {v.footprint_permitted_m2:8.1f} m2  "
                 f"({v.footprint_binding})")
    for n in v.notes:
        lines.append("")
        lines.append(f"  ! {n}")
    if v.cuts:
        lines.append("")
        lines.append(f"  To fit, cheapest concession first "
                     f"(short by {v.over_by_m2:.0f} m2 gross = "
                     f"{v.over_by_m2 * v.efficiency:.0f} m2 net):")
        for c in v.cuts:
            lines.append(f"    - {c['action']} {c['room']} "
                         f"({c['saves_m2']} m2 net, {c['saves_gross_m2']} m2 gross)")
            lines.append(f"        {c['cost']}")
    lines.append("")
    lines.append(f"  efficiency source: {EFFICIENCY_SOURCE}")
    return "\n".join(lines)
