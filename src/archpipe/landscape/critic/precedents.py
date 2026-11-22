"""Known-good: the LDP scaled precedent plans re-drawn as `landscape-layout/1` layouts (coarse, by hand).

Procedure (stated so the limits are visible): each plan image in ~/archpipe/shared/landscape-precedents (not committed;
publisher copyright) was viewed on a contact sheet; the main outdoor spaces were read in sheet pixels and converted to
metres with the plan's own scale bar (`S` px/m below); plan-up is taken as client north. What is drawn: surfaces, the
walls/buildings that enclose each space, tree and planter positions and sizes, water, tables and fixed seats, paths where
the plan draws them. What is NOT known and is therefore invented as a stand-in: planting species (plans rarely label them), so
every planting group uses a layer stand-in species (flag `stand_in`), and the horticulture, user and climate critics are NOT
run on these layouts. Only the site-independent landscape-architect criteria are. Rough hand estimate; no CAD.
"""
from __future__ import annotations

import json

from .common import KNOW

OUT = KNOW / "critic/precedent-layouts"
STAND = {"canopy": ("Olea europaea", "large_tree"), "understorey": ("Punica granatum", "small_tree"), "shrub": ("Pittosporum tobira", "shrub"), "ground": ("Liriope muscari", "ground_cover")}


class Plan:
    def __init__(self, pid, name, s, ox=0, oy=0):
        self.s, self.ox, self.oy = s, ox, oy
        self.l = {"schema": "landscape-layout/1", "id": pid, "source": f"LDP precedent {pid}: {name} (re-drawn by hand from the scaled plan; see precedents.py)",
                  "stand_in_species": True, "zones": [], "paths": [], "tables": [], "seating": [], "planting_groups": [], "trees": [], "features": [],
                  "buildings": [], "walls": [], "screens": [], "canopies": [], "doors": [], "boundary": [], "paved_areas": [], "steps": [], "obstacles": []}
        self.n = 0

    def R(self, x0, y0, x1, y1):      # sheet px (right, down) -> model (x south = down, y east = right)
        f = lambda v, o: round((v - o) / self.s, 2)
        return [f(y0, self.oy), f(x0, self.ox), f(y1, self.oy), f(x1, self.ox)]

    def P(self, x, y): return [round((y - self.oy) / self.s, 2), round((x - self.ox) / self.s, 2)]

    def _id(self, k): self.n += 1; return f"{k}{self.n}"

    def zone(self, use, surface, r, **kw): self.l["zones"].append({"id": self._id("z"), "use": use, "surface": surface, "rect": self.R(*r), **kw})
    def building(self, r): self.l["buildings"].append(self.R(*r))
    def wall(self, r, h=3.0): self.l["walls"].append({"id": self._id("w"), "rect": self.R(*r), "height_m": h})
    def tree(self, c, d_px, form="large_tree"):
        sp = d_px / self.s; sp_sp, f = STAND["canopy" if form == "large_tree" else "understorey"]
        self.l["trees"].append({"id": self._id("t"), "species": sp_sp, "center": self.P(*c), "mature_spread_m": round(sp, 1), "form": f, "mature_height_m": round(sp * 1.2, 1)})
    def bed(self, r, mix):
        """mix: [(layer, count)] -> stand-in plants with the plan's drawn sizes unknown (library spread used)."""
        pl = [{"species": STAND[ly][0], "form": STAND[ly][1], "count": n, "stand_in": True} for ly, n in mix]
        self.l["planting_groups"].append({"id": self._id("b"), "rect": self.R(*r), "over_structure": False, "plants": pl})
    def table(self, c, d_px, seats): self.l["tables"].append({"id": self._id("tb"), "center": self.P(*c), "diameter_m": round(d_px / self.s, 1), "seats": seats})
    def feature(self, kind, c, d_px, **kw): self.l["features"].append({"id": self._id("f"), "kind": kind, "center": self.P(*c), "diameter_m": round(d_px / self.s, 1), **kw})
    def path(self, pts, w=1.2, cls="main"): self.l["paths"].append({"id": self._id("p"), "class": cls, "width_m": w, "polyline": [self.P(*q) for q in pts]})
    def door(self, c): self.l["doors"].append({"id": self._id("d"), "at": self.P(*c), "faces": "+x"})


def sme01():
    p = Plan("P-SME-01", "Domus Maya, Cyprus: central patio", 27.6, 305, 545)
    p.zone("lounge", "paving", (305, 545, 580, 735), label="patio")
    for r in ((300, 540, 310, 740), (575, 540, 585, 740), (300, 540, 585, 550), (300, 730, 585, 740)): p.wall(r)
    p.tree((417, 640), 62, "small_tree")
    p.feature("fountain", (417, 640), 70)
    p.l["seating"] += [{"id": "s1", "zone": "z1", "rect": p.R(500, 650, 535, 675), "seats": 2}]
    p.door((415, 545)); p.door((415, 735))
    return p.l


def sme05():
    p = Plan("P-SME-05", "The Avli Houses, Cyprus: hexagon court", 23.6, 225, 380)
    p.zone("lounge", "paving", (225, 380, 505, 545), label="court")
    for r in ((195, 205, 545, 370), (195, 545, 515, 730), (195, 370, 225, 545), (505, 370, 545, 545)): p.building(r)
    p.feature("pond", (437, 465), 100)
    p.table((310, 445), 28, 4)
    p.tree((350, 510), 55, "small_tree"); p.tree((255, 405), 40, "small_tree")
    p.bed((140, 130, 195, 420), [("shrub", 4), ("understorey", 2), ("ground", 6)]); p.bed((545, 130, 635, 420), [("shrub", 4), ("understorey", 2), ("ground", 6)])
    p.bed((195, 730, 520, 800), [("shrub", 6), ("ground", 8)])
    p.wall((130, 130, 135, 800)); p.wall((630, 130, 635, 800)); p.wall((130, 795, 635, 800))
    return p.l


def sme08():
    p = Plan("P-SME-08", "Hanging Home, Malta: lawn, planter and dining deck", 26.0, 1085, 150)
    p.zone("other", "lawn", (1085, 215, 1250, 350), label="lawn")
    p.zone("dining", "paving", (1325, 210, 1470, 280), label="dining deck")
    p.zone("other", "planting", (1255, 285, 1560, 350), label="planter")
    p.tree((1285, 315), 55, "small_tree"); p.tree((1350, 315), 55, "small_tree"); p.tree((1430, 320), 70, "small_tree"); p.tree((1530, 315), 55, "small_tree")
    p.table((1398, 245), 30, 6)
    for r in ((1085, 145, 1710, 155), (1075, 350, 1580, 358)): p.wall(r, 3.0)
    p.building((1185, 55, 1550, 210))
    p.bed((1255, 330, 1560, 350), [("ground", 8), ("shrub", 4)])
    return p.l


def sau02():
    p = Plan("P-SAU-02", "Garland Garden, New Farm: circular lawn garden", 26.8, 1010, 80)
    p.zone("lounge", "lawn", (1260, 105, 1400, 245), label="round lawn")
    p.zone("quiet", "paving", (1375, 190, 1450, 250), label="sunken seat")
    p.zone("other", "paving", (1060, 215, 1200, 295), label="side court")
    p.bed((1210, 80, 1430, 108), [("shrub", 4), ("understorey", 2), ("ground", 8)]); p.bed((1075, 265, 1380, 295), [("shrub", 5), ("ground", 8)])
    p.bed((1250, 230, 1330, 265), [("shrub", 3), ("ground", 5)])
    p.tree((1380, 75), 70); p.tree((1090, 95), 45, "small_tree")
    p.wall((1010, 78, 1700, 84), 2.0); p.wall((1010, 295, 1450, 300), 2.0); p.building((1455, 100, 1710, 270))
    p.path([(1450, 215), (1400, 215)], 1.2, "main"); p.path([(1200, 255), (1260, 235)], 1.0, "secondary")
    return p.l


def sau01():
    p = Plan("P-SAU-01", "Tropic of Preston, Melbourne: courtyard house, planted garden with pond", 26.0, 105, 85)
    p.zone("lounge", "paving", (310, 85, 665, 200), label="pond terrace")
    p.zone("other", "paving", (105, 200, 660, 335), label="garden court")
    p.feature("pond", (500, 145), 200)
    for r in ((105, 80, 835, 88), (105, 565, 835, 573), (105, 80, 112, 573)): p.wall(r, 2.4)
    p.building((190, 400, 430, 560)); p.building((430, 380, 630, 560)); p.building((710, 85, 835, 440)); p.building((105, 85, 305, 195))
    for c, d in (((200, 280), 120), ((360, 310), 100), ((530, 255), 130), ((420, 195), 90)): p.tree(c, d, "large_tree" if d > 100 else "small_tree")
    p.bed((105, 200, 330, 400), [("shrub", 6), ("understorey", 2), ("ground", 10)]); p.bed((310, 90, 470, 195), [("shrub", 5), ("ground", 8)])
    p.bed((630, 100, 700, 330), [("shrub", 4), ("ground", 6)]); p.bed((650, 440, 830, 560), [("shrub", 5), ("understorey", 2), ("ground", 8)])
    p.door((430, 380))
    return p.l


def sau04():
    p = Plan("P-SAU-04", "Subiaco oval courtyard, Perth", 42.5, 1020, 30)
    p.zone("lounge", "lawn", (1200, 35, 1370, 600), label="oval court")
    p.zone("other", "paving", (1050, 235, 1200, 385), label="patio")
    p.zone("dining", "paving", (1050, 710, 1480, 790), label="entry deck")
    p.tree((1300, 90), 60, "small_tree"); p.tree((1435, 105), 55, "small_tree"); p.tree((1220, 385), 160)
    for r in ((1018, 28, 1530, 36), (1018, 865, 1530, 873), (1018, 28, 1026, 873), (1522, 28, 1530, 873)): p.wall(r, 2.0)
    p.building((1050, 395, 1200, 700)); p.building((1385, 195, 1500, 700)); p.building((1050, 35, 1205, 235))
    p.bed((1030, 800, 1520, 860), [("shrub", 6), ("ground", 10)])
    p.path([(1225, 790), (1225, 870)], 1.5, "main")
    return p.l


def sau05():
    p = Plan("P-SAU-05", "Courtyard House, Paddington: garden court and green roof", 29.4, 290, 490)
    p.zone("lounge", "paving", (290, 495, 465, 560), label="garden court")
    p.zone("other", "planting", (290, 600, 465, 650), label="green roof")
    p.tree((333, 523), 52, "small_tree")
    for r in ((188, 490, 193, 655), (460, 490, 465, 655), (188, 490, 465, 497)): p.wall(r, 6.0)
    p.building((190, 570, 460, 655)); p.building((465, 490, 590, 655))
    p.bed((295, 495, 330, 560), [("ground", 6), ("shrub", 2)]); p.bed((380, 495, 460, 505), [("ground", 6)])
    p.door((380, 570))
    return p.l


def s204():
    p = Plan("P-S2-04", "Claremont front courtyard, Perth", 43.5, 1035, 30)
    p.zone("lounge", "paving", (1035, 80, 1300, 250), label="lounge deck")
    p.zone("other", "paving", (1230, 190, 1330, 340), label="entry paving")
    p.bed((1035, 40, 1330, 110), [("shrub", 5), ("understorey", 2), ("ground", 6)]); p.bed((1000, 100, 1090, 220), [("shrub", 4), ("understorey", 1), ("ground", 5)])
    p.bed((1240, 40, 1345, 190), [("shrub", 4), ("ground", 6)])
    p.tree((1015, 165), 60, "small_tree"); p.tree((1320, 90), 45, "small_tree")
    p.wall((1030, 250, 1235, 258), 3.0); p.wall((1230, 335, 1380, 343), 3.0); p.building((1030, 250, 1040, 300))
    p.door((1265, 340)); p.door((1340, 340))
    return p.l


def s220():
    p = Plan("P-S2-20", "Small London back garden with pergola dining, 1:75 planting plan (scale derived: 1:75 at A3 over the raster width, no scale bar)", 28.5, 50, 40)
    p.zone("dining", "paving", (110, 160, 235, 285), label="dining")
    p.zone("other", "lawn", (60, 285, 255, 300), label="")
    p.l["zones"] = p.l["zones"][:1]
    p.wall((48, 40, 56, 300), 1.8); p.wall((265, 40, 272, 300), 1.8); p.wall((48, 40, 272, 47), 1.8); p.building((50, 300, 272, 425))
    p.bed((56, 47, 110, 285), [("shrub", 5), ("understorey", 4), ("ground", 12)]); p.bed((236, 47, 265, 285), [("shrub", 3), ("ground", 10)])
    p.bed((110, 47, 236, 90), [("shrub", 4), ("ground", 6)])
    p.tree((150, 30), 100); p.tree((237, 270), 90)
    p.l["canopies"].append({"id": "pergola", "kind": "pergola", "canopy": True, "rect": p.R(110, 160, 235, 285), "height_m": 2.5, "shade_fraction": 0.6})
    p.door((165, 300))
    return p.l


def sme02():
    p = Plan("P-SME-02", "MV024 Residence, Limassol: lawn court", 48.6, 1065, 55)
    p.zone("lounge", "lawn", (1085, 270, 1360, 520), label="lawn")
    p.zone("dining", "paving", (1420, 435, 1510, 475), label="terrace")
    for c, d in (((1270, 520), 110), ((1510, 520), 55), ((1620, 470), 55)): p.tree(c, d, "large_tree" if d > 100 else "small_tree")
    p.bed((1060, 270, 1090, 545), [("shrub", 5), ("ground", 10)]); p.bed((1090, 535, 1590, 565), [("shrub", 6), ("ground", 12)])
    p.wall((1055, 55, 1060, 575), 2.5); p.wall((1055, 570, 1640, 585), 2.5); p.wall((1625, 55, 1635, 585), 2.5)
    p.building((1140, 140, 1560, 270)); p.building((1365, 270, 1560, 500))
    p.door((1440, 470))
    return p.l


ALL = {"P-SME-01": sme01, "P-SME-05": sme05, "P-SME-08": sme08, "P-SAU-02": sau02, "P-SAU-01": sau01, "P-SAU-04": sau04,
       "P-SAU-05": sau05, "P-S2-04": s204, "P-S2-20": s220, "P-SME-02": sme02}


def save_all():
    OUT.mkdir(parents=True, exist_ok=True)
    for k, f in ALL.items(): (OUT / f"{k}.json").write_text(json.dumps(f(), indent=1) + "\n")
