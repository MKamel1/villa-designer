"""Plan variants: which layers each plan sheet draws, and its legend / extra annotation."""
from __future__ import annotations

from archpipe.contracts import DesignElement

from . import layers as L

LAYERS = {
    "ga": ("tags", "dims", "handing", "existing"),
    "furnished": ("furniture", "tags", "handing", "existing"),
    "lighting": ("luminaires", "tags", "existing"),
    "colorfill": ("colorfill", "tags", "existing"),
}


def extras_for(variant: str, level: str):
    def extra(sh, geo, rep, cels: list[DesignElement]):
        x, y = 26.0, sh.paper[1] - 24.0
        common = [("?", "door handing is a judgement call: to confirm"), ("#d9c3f0", "kept existing column"),
                  ("#222222", "exterior wall"), ("#e8e8e8", "interior wall (hatched)")]
        if variant == "ga":
            L.legend_box(sh, x, y, "Legend", common + [("D01", "door tag"), ("W01", "window tag"), ("R01", "room tag")])
        elif variant == "furnished":
            rows = [("#fffdf5", "furniture and joinery (type name)"), ("#ffffff", "outline only: dressing props")] + common
            n = {}
            for e in cels:
                if e.kind == "furniture" and e.level == level and e.params.get("type") != "dressing":
                    n[e.params.get("type", "")] = n.get(e.params.get("type", ""), 0) + 1
            yb = L.legend_box(sh, x, y, "Legend", rows)
            sh.text((x, yb - 3), "Furniture on this level: %d items" % sum(n.values()), size=4.4, ha="left")
        elif variant == "lighting":
            rep_l = rep.get("luminaire_legend", [])
            rows = [(k, "%s  %s" % (code, what)) for k, code, what in rep_l]
            yb = L.legend_box(sh, x, y, "Luminaire types (mark, product code, description)", rows, size=3.6)
            sh.text((x, yb - 3), "Drawn as seen from below (reflected), same orientation as the plan. CH = ceiling height above FFL.",
                    size=4, ha="left")
            for c in cels:
                if c.kind == "ceiling" and c.level == level:
                    sh.text(sh.p(c.placement[0], c.placement[1] - 1100), "CH %.2f %s" % (c.params["height_mm"] / 1000.0, c.params["ceiling_kind"]),
                            size=3.6, color="#7a5a00", bg=True, z=9)
            rep["ceiling_height_tags"] = sum(1 for c in cels if c.kind == "ceiling" and c.level == level)
        elif variant == "colorfill":
            tot: dict[str, float] = {}
            for r in cels:
                if r.kind == "room" and r.level == level:
                    tot[r.params.get("occupancy", "")] = tot.get(r.params.get("occupancy", ""), 0.0) + r.params.get("net_area_m2", 0.0)
            rows = [(col, "%s  %.1f m² net" % (occ, tot.get(occ, 0.0))) for occ, col in rep.get("colour_legend", [])]
            L.legend_box(sh, x, y, "Room occupancy (net area on this level)", rows, size=4.2)
    return extra
