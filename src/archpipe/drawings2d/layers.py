"""Plan layers drawn over the base plan (client frame): furniture, luminaires, colour fill, site context.

All functions take a `plans._Sheet` and elements already in the client frame (`orient.to_client`). Each returns the
legend items it used so a sheet can print an honest legend.
"""
from __future__ import annotations

import math

from matplotlib.patches import Circle, Polygon, Rectangle

from archpipe.contracts import DesignElement

from . import standard

OCC_COLOURS = {   # colour-fill by occupancy (C9); a house palette, not a standard
    "living": "#f6d9a8", "dining": "#f3c8b8", "kitchen": "#e8b4a0", "utility": "#d7c4b0", "bedroom": "#bcd8f2",
    "study": "#c9e2c4", "dressing": "#d4c7ee", "bathroom": "#b6e3e0", "ensuite": "#a7d8d6", "corridor": "#ececec",
    "landing": "#e2e2e2", "stair": "#d0d0d0", "hall": "#e6e0d2", "entrance": "#f2e4a6", "media": "#c8b8d8",
    "store": "#d9d9c4",
}


def rect_poly(cx: float, cy: float, w: float, d: float, rot_deg: float) -> list[tuple[float, float]]:
    a = math.radians(rot_deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + c * x - s * y, cy + s * x + c * y) for x, y in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]


def colour_fill(sh, rooms: list[DesignElement]) -> list[tuple[str, str]]:
    seen = {}
    for r in rooms:
        occ = r.params.get("occupancy", "")
        col = OCC_COLOURS.get(occ, "#f0f0f0")
        sh.ax.add_patch(Polygon([sh.p(*q) for q in r.params["polygon_mm"]], closed=True, fc=col, ec="none", zorder=1))
        seen[occ] = col
    return sorted(seen.items())


CLEAR_FC = "#c8e6c9"


def clearance_zones(sh, els: list[DesignElement], level: str, window=None) -> int:
    """Free-space zones beside each piece from the catalogue's per-side clearances (front = local +Y, as the catalogue defines).
    Legacy diagnostic values, unverified (catalogue.py header): the zones show what the old Revit sheets showed, they do not
    certify a passage. Pieces the catalogue does not know, and sides with 0 mm, draw nothing."""
    from archpipe import catalogue
    n = 0
    for e in els:
        if e.kind != "furniture" or e.level != level or e.params.get("type") == "dressing":
            continue
        try:
            ft = catalogue.get(e.params.get("type", ""))
        except KeyError:
            continue
        w, d = e.size[0], e.size[1]
        a = math.radians(e.rotation_deg)
        c_, s_ = math.cos(a), math.sin(a)
        for side, (ox, oy, zw, zd) in {"front": (0, d / 2, w, ft.clearance.get("front", 0)), "back": (0, -d / 2, w, ft.clearance.get("back", 0)),
                                       "left": (-w / 2, 0, ft.clearance.get("left", 0), d), "right": (w / 2, 0, ft.clearance.get("right", 0), d)}.items():
            amount = zd if side in ("front", "back") else zw
            if amount <= 0:
                continue
            sx, sy = (1 if side in ("front", "right") else -1), 0
            lx = ox + (sx * zw / 2 if side in ("left", "right") else 0)
            ly = oy + ((1 if side == "front" else -1) * zd / 2 if side in ("front", "back") else 0)
            cx = e.placement[0] + c_ * lx - s_ * ly
            cy = e.placement[1] + s_ * lx + c_ * ly
            sh.ax.add_patch(Polygon([sh.p(*q) for q in rect_poly(cx, cy, zw, zd, e.rotation_deg)], closed=True, fc=CLEAR_FC, ec="#4c8c4a",
                                    lw=standard.lw("fine", sh.scale), alpha=0.6, ls=(0, (4, 2)), zorder=2))
            n += 1
    return n


def furniture(sh, els: list[DesignElement], level: str, *, labels: bool = True, window=None) -> int:
    n = 0
    for e in els:
        if e.kind != "furniture" or e.level != level:
            continue
        if window and not (window[0] - e.size[0] <= e.placement[0] <= window[2] + e.size[0]
                           and window[1] - e.size[0] <= e.placement[1] <= window[3] + e.size[0]):
            continue
        typ = e.params.get("type", "")
        dress = typ == "dressing"
        poly = rect_poly(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg)
        sh.ax.add_patch(Polygon([sh.p(*q) for q in poly], closed=True, fc="none" if dress else "#fffdf5",
                                ec="#9a9a9a" if dress else "#7a5c2e", lw=standard.lw("fine" if dress else "proj", sh.scale),
                                zorder=3))
        if labels and not dress and min(e.size[0], e.size[1]) / sh.scale > 4:
            sh.text(sh.p(e.placement[0], e.placement[1]), typ.replace("_", " "), size=2.8, color="#5a431f", z=4)
        n += 1
    return n


LUM = {  # fixture_kind -> (symbol, description). Description comes from the element's own `what` at legend time.
    "DL": "dl", "DLN": "dl", "ADJ": "adj", "WW": "lin", "COVE": "lin", "BACK": "lin", "STEP": "pt", "TOE": "lin",
    "UC": "lin", "NL": "pt", "SCONCE": "wall", "PEN-GLOBE": "pen", "PEN-LIN": "lin", "SWING": "wall",
    "DESK": "pt", "STORE-BATTEN": "lin", "VANITY-LIN": "lin", "PATH": "pt", "WALL-READ": "wall", "RAIL": "lin",
    "VSTRIP": "lin", "MIRROR": "lin", "PCOVE": "lin",
}


def luminaires(sh, els: list[DesignElement], level: str, rep: dict | None = None) -> list[tuple[str, str, str]]:
    """Symbols plus type tags. Legend rows: (kind, product code or '-', what). Tags: every non-DL fixture; DL/DLN carry
    one tag per room with the count so a ceiling of 12 downlights is not 12 labels."""
    legend: dict[str, tuple[str, str]] = {}
    first_in_room: dict[tuple[str, str], int] = {}
    counts: dict[tuple[str, str], int] = {}
    mine = [e for e in els if e.kind == "luminaire" and e.level == level]
    for e in mine:
        counts[(e.room, e.params["fixture_kind"])] = counts.get((e.room, e.params["fixture_kind"]), 0) + 1
    for e in mine:
        k = e.params["fixture_kind"]
        sym = LUM.get(k, "pt")
        x, y = e.placement[0], e.placement[1]
        c = sh.p(x, y)
        lw = standard.lw("proj", sh.scale)
        if sym in ("dl", "adj", "pen"):
            r = max(0.9, (e.size[0] / 2) / sh.scale)
            sh.ax.add_patch(Circle(c, r, fc="white" if sym != "pen" else "#fff3c4", ec="#b8860b", lw=lw, zorder=5))
            sh.line((c[0] - r, c[1]), (c[0] + r, c[1]), lw=lw * 0.6, color="#b8860b", z=5)
            if sym == "dl":
                sh.line((c[0], c[1] - r), (c[0], c[1] + r), lw=lw * 0.6, color="#b8860b", z=5)
            if sym == "adj":
                al = e.params.get("aim") or [0, 0, -1]
                sh.line(c, (c[0] + al[0] * 3, c[1] + al[1] * 3), lw=lw, color="#b8860b", z=5)
        elif sym == "lin":
            ln = (e.params.get("length_mm") or 600) / sh.scale
            al = e.params.get("along") or [1, 0, 0]
            hx, hy = al[0] * ln / 2, al[1] * ln / 2
            sh.line((c[0] - hx, c[1] - hy), (c[0] + hx, c[1] + hy), lw=lw * 2.2, color="#b8860b", z=5)
        elif sym == "wall":
            sh.ax.add_patch(Polygon([(c[0], c[1] + 1.1), (c[0] - 1.1, c[1] - 0.8), (c[0] + 1.1, c[1] - 0.8)], closed=True,
                                    fc="#fff3c4", ec="#b8860b", lw=lw, zorder=5))
        else:
            sh.ax.add_patch(Circle(c, 0.7, fc="#b8860b", ec="#b8860b", lw=lw, zorder=5))
        ph = e.params.get("photometry") or {}
        legend.setdefault(k, (ph.get("code") or "-", e.params.get("what", "")))
        key = (e.room, k)
        first_in_room.setdefault(key, 0)
        first_in_room[key] += 1
        tag = None
        if k in ("DL", "DLN"):
            if first_in_room[key] == 1:
                tag = "%s ×%d" % (k, counts[key])
        else:
            tag = k
        if tag:
            sh.text((c[0] + 2.2, c[1] + 1.8), tag, size=2.7, color="#7a5a00", z=6, ha="left")
            if rep is not None:
                rep.setdefault("luminaire_tags", []).append({"id": e.id, "tag": tag})
    return sorted((k, v[0], v[1]) for k, v in legend.items())


def legend_box(sh, x: float, y: float, title: str, rows: list[tuple[str, str]], *, w: float = 62, size: float = 7.0, label_dx: float = 7.0) -> float:
    """Paper-mm legend: title then (swatch colour or text, label) rows. Returns the y below the box."""
    sh.text((x, y), title, size=9, ha="left", weight="bold")
    y -= 6
    for sw, label in rows:
        if sw.startswith("#"):
            sh.ax.add_patch(Rectangle((x, y - 1.8), 5, 3.6, fc=sw, ec="k", lw=0.2, zorder=6))
        else:
            sh.text((x + (2.5 if label_dx <= 7 else 0.0), y), sw, size=size, z=7, ha="center" if label_dx <= 7 else "left")
        sh.text((x + label_dx, y), label, size=size, ha="left")
        y -= 4.8
    return y


def text_table(sh, x: float, y: float, title: str, header: list[str], rows: list[list[str]], widths: list[float], *,
               size: float = 7.0, pitch: float = 4.4, note: str = "") -> float:
    """Paper-mm table in the left column of a sheet (cells are cut to their column width). Returns the y below it."""
    sh.text((x, y), title, size=9, ha="left", weight="bold")
    y -= 5.5
    cx = x
    for h, w in zip(header, widths):
        sh.text((cx, y), h, size=size, ha="left", color="#333333")      # headers are not bold: bold = room names (sheetqa reads that)
        cx += w
    sh.line((x, y - 2.0), (x + sum(widths), y - 2.0), lw=0.3)
    y -= pitch + 0.6
    for r in rows:
        cx = x
        for c, w in zip(r, widths):
            sh.text((cx, y), str(c)[: max(3, int(w / (size * 0.26)))], size=size, ha="left")
            cx += w
        y -= pitch
    if note:
        sh.text((x, y - 1), note, size=size, ha="left", color="#444444")
        y -= pitch + 1
    return y
