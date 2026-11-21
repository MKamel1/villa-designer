"""Plan variants: which layers each plan sheet draws, and its legend / extra annotation."""
from __future__ import annotations

from archpipe.contracts import DesignElement

import json
from pathlib import Path

from archpipe.documents.plans import DOOR_COLOUR as plans_DOOR, WINDOW_COLOUR as plans_WINDOW

from . import layers as L

_LUX = Path(__file__).resolve().parents[1] / "documents" / "data" / "villa-after-rows.json"


def lux_rows(cels: list[DesignElement]) -> list[list[str]]:
    """Lux table rows (room, plane, scene, required, achieved, U0) from lane L6b's villa-after-rows.json (read, not re-derived).
    Gauge 'average' targets are met on Em, 'minimum' on Emin; the card id names the source of the target."""
    level = {e.room: e.level for e in cels if e.kind == "room"}
    name = {e.room: e.params["name"].split(" (")[0] for e in cels if e.kind == "room"}
    rows = []
    for r in json.loads(_LUX.read_text(encoding="utf-8")):
        ach = r["em"] if r["gauge"] == "average" else r["emin"]
        rows.append([level.get(r["room"], "?"), name.get(r["room"], r["room"])[:22], r["what"][:26], r["scene"],
                     "%s %g" % ("Em" if r["gauge"] == "average" else "Emin", r["target"]), "%.0f" % ach,
                     "%+.0f%%" % ((ach / r["target"] - 1) * 100), "%.2f" % r["u0"]])
    return sorted(rows)

LAYERS = {
    "ga": ("tags", "dims", "handing", "existing"),
    "furnished": ("furniture", "clearance", "opencolour", "tags", "handing", "existing"),
    "lighting": ("luminaires", "tags", "existing"),
    "colorfill": ("colorfill", "opencolour", "tags", "existing"),
}


def extras_for(variant: str, level: str = None):
    """Per-panel extras; the legend is drawn once (first panel) in the left column."""
    def extra(sh, geo, rep, cels: list[DesignElement], first: bool = True):
        level = rep["level"]
        x, y = 26.0, sh.paper[1] - 28.0
        coding = [(plans_DOOR, "door (leaf and swing)"), (plans_WINDOW, "window / glazing")] if variant in ("furnished", "colorfill") else []
        common = coding + [("?", "door handing is a judgement call: to confirm"), ("#d9c3f0", "kept existing column"),
                  ("#222222", "exterior wall"), ("#e8e8e8", "interior wall (hatched)")]
        if variant == "ga" and first:
            L.legend_box(sh, x, y, "Legend", common + [("Dnn", "door tag (circle)"), ("Wnn", "window tag (hexagon)"), ("Rnn", "room tag with net area")])
        elif variant == "furnished":
            n = sum(1 for e in cels if e.kind == "furniture" and e.level == level and e.params.get("type") != "dressing")
            rep["caption_note"] = "%d furniture items" % n
            if first:
                yb = L.legend_box(sh, x, y, "Legend", [("#fffdf5", "furniture and joinery (type name)"), ("#ffffff", "outline only: dressing props"),
                                                         ("#c8e6c9", "clearance zone (legacy catalogue, diagnostic: passages not verified)")] + common)
                by_room: dict[tuple, dict] = {}
                names_ = {e.room: e.params["name"].split(" (")[0] for e in cels if e.kind == "room"}
                for e in cels:
                    if e.kind == "furniture" and e.params.get("type") != "dressing":
                        d = by_room.setdefault((e.level, names_.get(e.room, e.room)), {})
                        t = e.params.get("type", "?").replace("_", " ")
                        d[t] = d.get(t, 0) + 1
                rows = [[lv, nm[:26], ", ".join("%s%s" % (t, " x%d" % c if c > 1 else "") for t, c in sorted(d.items()))[:78]]
                        for (lv, nm), d in sorted(by_room.items())]
                yb = L.text_table(sh, x, yb - 8, "Furniture by room", ["Lv", "room", "items"], rows, [9, 50, 150], size=8, pitch=5.6)
                import textwrap
                yb -= 6
                sh.text((x, yb), "Why it sits there (from the design model)", size=9, ha="left", weight="bold")
                yb -= 6
                shown = total = 0
                for e in sorted((e for e in cels if e.kind == "furniture" and e.params.get("why")), key=lambda e: (e.level, e.room)):
                    total += 1
                    lines = textwrap.wrap("%s %s: %s" % (e.level, e.params.get("type", "").replace("_", " "), e.params["why"]), 88)[:3]
                    if yb - 4.4 * len(lines) < 24:
                        continue
                    for ln in lines:
                        sh.text((x, yb), ln, size=7, ha="left")
                        yb -= 4.4
                    yb -= 1.2
                    shown += 1
                rep["why_shown"] = [shown, total]
                if shown < total:
                    sh.text((x, yb), "%d of %d rationales shown; the rest are in the model (furniture `why`)." % (shown, total), size=7, ha="left", color="#444444")
        elif variant == "lighting":
            if first:
                rows = [(k, "%s  %s" % (code, what)) for k, code, what in rep.get("luminaire_legend", [])]
                yb = L.legend_box(sh, x, y, "Luminaire types (mark, product code, description)", rows, label_dx=24)
                sh.text((x, yb - 3), "Drawn as seen from below (reflected), same orientation as the plan.", size=7, ha="left")
                sh.text((x, yb - 8), "CH = ceiling height above FFL.", size=7, ha="left")
            for c in cels:
                if c.kind == "ceiling" and c.level == level:
                    sh.text(sh.p(c.placement[0], c.placement[1] - 1100), "CH %.2f %s" % (c.params["height_mm"] / 1000.0, c.params["ceiling_kind"]),
                            size=7, color="#7a5a00", bg=True, z=9)
            if first:
                rows = lux_rows(cels)
                L.text_table(sh, x, yb - 16, "Illuminance: required vs achieved (lux)", ["Lv", "room", "plane", "scene", "required", "achieved", "diff", "U0"],
                             rows, [7, 30, 46, 14, 20, 17, 12, 10], pitch=4.2,
                             note="Computed by lane L6b (knowledge/lighting/villa-after-rows.json), not re-derived here. Required = card value.")
            rep["ceiling_height_tags"] = sum(1 for c in cels if c.kind == "ceiling" and c.level == level)
        elif variant == "colorfill" and first:
            tot: dict[tuple, float] = {}
            for r in cels:
                if r.kind == "room":
                    k = (r.params.get("occupancy", ""), r.level)
                    tot[k] = tot.get(k, 0.0) + r.params.get("net_area_m2", 0.0)
            occs = sorted({o for o, _ in tot})
            rows = [(L.OCC_COLOURS.get(o, "#f0f0f0"), "%s   B %.1f  /  GF %.1f m² net" % (o, tot.get((o, "B"), 0.0), tot.get((o, "GF"), 0.0)))
                    for o in occs]
            rows = coding + rows
            yb = L.legend_box(sh, x, y, "Room occupancy (net area per level)", rows)
            rows = sorted([r.level, r.params["name"].split(" (")[0][:30], r.params.get("occupancy", ""), "%.2f" % r.params.get("net_area_m2", 0.0)]
                          for r in cels if r.kind == "room")
            L.text_table(sh, x, yb - 8, "Rooms: net area", ["Lv", "room", "occupancy", "m²"], rows, [9, 70, 32, 20], size=9, pitch=6.0)
    return extra
