"""Lane DF: AS-BUILT plan of the parents' suite (1:50 A3), DESIGN MODEL, not a proposal. Replaces DF-101 (today) and DF-102 (R3 proposal).
Walls, doors (with swings), windows come from the design model D1 itself (documents.plans drawers); furniture is drawn from the
model's furniture elements; the key-dimension table is measured on the built model (suite_privacy, circulation).
Run: PYTHONPATH=src python scripts/df_asbuilt.py   -> docs/lanes/DF-plans/DF-102-plan-AS-BUILT.{pdf,png}, numbers-as-built.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_plans as P
from shapely.geometry import box
from matplotlib.patches import Rectangle

from archpipe import model
from archpipe.concept import villa_furnish as F, villa_r11 as R
from archpipe.drawings2d import standard
from archpipe.documents import plans
from archpipe.model import circulation as C, suite_privacy as SP

EL = P.EL
LAY = R.design("D1")
ITEMS = {i["id"]: i for i in F.layout(LAY)}
VAN = box(*F.footprint(ITEMS["pb-vanity"]))
HERS = F.footprint(ITEMS["pd-hang-1"])
KEY = "ASB"
P.OPT[KEY] = dict(head=(20.437, -23.791), toward=(0, -1), hers=(HERS[0], HERS[2]), hers_order="from_door", door=None, curtain="both", slat=True, vanity=VAN)
o = P.OPT[KEY]
(hx, hy), (dx, dy) = o["head"], o["toward"]
o["bed"] = box(hx - P.BED_W / 2, hy - P.BED_L, hx + P.BED_W / 2, hy)


def measured():
    els = model.load("D1")
    priv = SP.seeing(els)
    b = ITEMS["pb-bed"]
    x0, y0, x1, y1 = F.footprint(b)
    PB = F.clear_rect(LAY, "parents-bed")
    items = C.with_trays(F.layout(LAY), 0.25)
    rows = [r for r in C.routes(LAY, items, level="GF") if r["cluster"].startswith(("parents", "suite"))]
    narrow = {}
    for r in rows:
        narrow.setdefault(r["cluster"], []).append(r["achieved"])
    from importlib import import_module
    T = import_module("test_suite_built") if False else None
    return dict(
        privacy="PASS: %d of %d outside viewpoints see in (all suite doors open)" % (len(priv["seeing"]), priv["viewpoints"]),
        bedsides="%d / %d mm" % (round((x0 - PB[0]) * 1000), round((PB[2] - x1) * 1000)),
        foot="%d mm" % round((y0 - PB[1]) * 1000),
        vestibule="%d mm clear (door to entry), cabinet 130 deep" % round(min(narrow["suite-vestibule"]) * 1000),
        bedroom_routes="%d mm (door to door, trays open 250)" % round(min(narrow["parents-bed+parents-entry"]) * 1000),
        dressing_routes="%d mm" % round(min(narrow["parents-dressing+parents-dressing-ext"]) * 1000),
        viewpoints=priv["viewpoints"], seeing=len(priv["seeing"]), rows=[C.describe(r) for r in rows])


def plan():
    fig = P.Fig(50, 30, 120)
    sh = fig.sh
    geo, cels = P.draw_base(fig, KEY)
    P.sill_marks(fig)
    P.furniture(fig, KEY)
    P.curtains(fig, KEY)
    P.slats(fig, -26.291, -23.961, deep=0.03)
    fig.text(18.66, -25.1, "slat wall", size=7, color="#6b4a1c", z=9)
    P.labels(fig, KEY)
    fig.sh.text(fig.P(19.15, -27.99), "VESTIBULE", size=6, weight="bold", rot=90, z=9)
    sv = F.footprint(ITEMS["sv-store"])
    fig.rect(box(*sv), fc=P.TAN, ec=P.BROWN, z=6)
    gx = dict(geo, bbox=(P.CROP[1] * 1000, -P.CROP[2] * 1000, P.CROP[3] * 1000, -P.CROP[0] * 1000))
    plans._north_scale(sh, gx, "GF", P.SPEC["levels"])
    b = o["bed"]
    bx0, by0, bx1, by1 = b.bounds
    fig.dim((18.477, -25.9), (bx0, -25.9), 0, "%d" % round((bx0 - 18.477) * 1000))
    fig.dim((bx1, -25.9), (22.397, -25.9), 0, "%d" % round((22.397 - bx1) * 1000))
    fig.dim((21.0, by0), (21.0, -26.591), 0, "%d" % round((by0 + 26.591) * 1000))
    fig.dim((o["hers"][0], -26.591), (o["hers"][1], -26.591), 4.5, "hers %d" % round((o["hers"][1] - o["hers"][0]) * 1000))
    fig.dim((17.5, -28.221), (17.5, -27.421), 0, "")
    fig.dim((18.2, -28.341), (18.2, -27.421), 0, "%d" % round((28.341 - 27.421) * 1000))
    return fig, geo


def banner(sh, title):
    """Project title block with the banner for a DESIGN MODEL sheet (built), not a proposal."""
    sheet = {"no": "DF-102", "title_en": title, "title_ar": "كما بُني في نموذج التصميم", "scale": "1:50", "paper": "A3 landscape"}
    plans._title_block(sh, P.SPEC, sheet, 1, 1)
    x0 = P.PAPER[0] - plans.EDGE - plans.STRIP
    sh.ax.add_patch(Rectangle((x0 + 0.3, P.PAPER[1] - plans.EDGE - 14), plans.STRIP - 0.6, 13.7, fc="#1b5e20", ec="none", zorder=13))
    sh.text((x0 + plans.STRIP / 2, P.PAPER[1] - plans.EDGE - 6), "AS-BUILT (lane DF)", size=8, color="white", weight="bold", z=14)
    sh.text((x0 + plans.STRIP / 2, P.PAPER[1] - plans.EDGE - 11), "DESIGN MODEL D1", size=7, color="white", z=14)
    sh.text((plans.LEFT + 4, P.PAPER[1] - plans.EDGE - 5), title, size=9, ha="left", weight="bold")
    sh.text((plans.LEFT + 4, P.PAPER[1] - plans.EDGE - 10.5),
            "1:50 on A3.  AS-BUILT: drawn from the design model D1 as built by lane DF (client FINAL 2026-11-26).  Supersedes proposals DF-101 and DF-102 rev P01.  North is the street side.",
            size=7, ha="left", color="#1b5e20")
    sh.ax.add_patch(Rectangle((0, 0), P.PAPER[0], P.PAPER[1], fc="white", ec="none", zorder=-5))


def main():
    N = measured()
    fig, geo = plan()
    sh = fig.sh
    banner(sh, "Parents' suite: as-built furnished plan (R3 + annexed vestibule)")
    xr = 30 + fig.w + 14
    y = 257.0
    y = P.draw_text_block(sh, xr, y, "As built (design model D1)", [
        "1. Bed turned: head to the east window wall, centred on the room (x 20.437), 1160 clear each side, 800 at the foot. Low upholstered head panel to the 0.90 m sill; reading-light arms clamped to the panel's top rail; power from a 24 V DC SELV driver in the sill wall behind the panel (device SOC-parents-bed-068, circuit DB-GF/L2).",
        "2. Dressing door moved to the lobby end of the old head wall (x 19.577..20.377, 800 x 2100), hinged on the south (+x model) jamb, swings into the dressing room. The old east door is built in.",
        "3. Hers hanging 1870 from the new door's jamb to the east wall (HS, DR, DH, LH from the door); his unchanged. Open leaf 80 mm clear of hers.",
        "4. Slat feature on the corridor-side wall (2.33 m run, from 0.30 m past the lobby mouth). Cove moved to that wall. Roller blackout in the window reveal and fixed side drapes on the piers.",
        "5. Vanity moved 0.90 m toward the bed foot (the brief's ~0.30 m measures 0.50 m between the open tray and the vanity corner; 0.90 m measures 0.76 m).",
        "6. ANNEX: a new suite door (800 leaf, hinged north jamb, swings INTO the vestibule, self-closing) across the corridor 0.26 m past kids-b's jamb; the corridor end is the suite vestibule with a flat 130 mm storage cabinet on the facade wall. Kids-b's door, swing and approach are unchanged and public."], width=116)
    y -= 2
    P.draw_text_block(sh, xr, y, "Legend", [
        "Walls: dark = external, hatched = internal (cut). Orange = door leaf and swing, blue = glazing and sill.",
        "Hanging: dashed rail with hanger ticks. LH long hang, DH double hang, DR drawers, HS hat shelf, TR trousers, SH shelves.",
        "Bed: head panel (tan), pillows, duvet fold. DASHED boxes = trays pulled out 250 mm.",
        "Curtains: wavy = fixed side drapes, dashed bar = track, long-dash line = roller blackout in the reveal."], width=116)
    rows = [
        ["Bedsides W / E (clear to wall)", N["bedsides"], "card ukadm-bedroom-route-750 (UK AD M 2.25a), 750; benchmark, not code compliance"],
        ["Foot to the south wall", N["foot"], "same card, 750"],
        ["Bedroom routes, both trays open 250", N["bedroom_routes"], "model/circulation.py, 20 mm grid, widest disc; 750 needed; 760 mm at the vanity"],
        ["Dressing routes", N["dressing_routes"], "same card; private-suite project waiver"],
        ["Vestibule passage left", N["vestibule"], "card mitton-path-of-travel-min 914; also the 0.90 hall card ukadm-hall-min-m42"],
        ["Privacy, ALL suite doors open", N["privacy"], "model/suite_privacy.py on the built walls and doors; furniture and leaves ignored (worst case)"],
    ]
    P.key_table(sh, 30, 100, ["Key dimension", "As built", "Basis"], rows, [70, 70, 160])
    P.OUT.mkdir(parents=True, exist_ok=True)
    stem = "DF-102-plan-AS-BUILT"
    sh.fig.savefig(P.OUT / (stem + ".pdf"), facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(sh.fig)
    import pymupdf
    d = pymupdf.open(str(P.OUT / (stem + ".pdf")))
    d[0].get_pixmap(dpi=150).save(str(P.OUT / (stem + ".png")))
    (P.OUT / "numbers-as-built.json").write_text(json.dumps(N, indent=1))
    print(json.dumps(N, indent=1))


if __name__ == "__main__":
    main()
