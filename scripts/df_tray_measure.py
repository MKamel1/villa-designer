"""Pull-out trays of the parents' joinery bed: what projects when closed and open, and what is left at the two doors.

usage: PYTHONPATH=src python scripts/df_tray_measure.py   (prints a table; the same numbers are asserted in tests/model/test_circulation.py)
Open tray = a pseudo-item (the pulled-out box), run through model/circulation.py exactly like furniture."""
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_furnish3d as F3
from archpipe.furniture import JOINERY_BED as J
from archpipe.model import circulation as C
from archpipe.model.circulation import tray_boxes, with_trays

LAY = F.R.design("D1")


def entry_and_dressing(items):
    rs = {(r["frm"], r["to"]): r for r in C.routes(LAY, items=items, dressed=False) if "parents-bed" in r["cluster"]}
    return {"entry approach": rs[("door corridor/parents-entry", "its own approach")]["achieved"],
            "dressing approach": rs[("door parents-bed/parents-dressing", "its own approach")]["achieved"],
            "entry -> dressing route": next(v["achieved"] for k, v in rs.items() if k[1].startswith("door corridor") and k[0].startswith("door parents-bed/parents-dressing"))}


if __name__ == "__main__":
    base = F.layout(LAY)
    bed = next(i for i in base if i["id"] == "pb-bed")
    fp = F.footprint(bed)
    print("bed footprint", [round(v, 3) for v in fp])
    spec = next(s for s in F3.spec(LAY, base) if s["mark"] == "pb-bed")
    e = spec["envelope"]
    print("closed: bed parts envelope x %.3f..%.3f y %.3f..%.3f; beyond footprint: %.0f mm" %
          (e[0], e[3], e[1], e[4], 1000 * max(fp[0] - e[0], e[3] - fp[2], fp[1] - e[1], e[4] - fp[3], 0)))
    for pull in (0.0, J["tray_pull_m"]):
        items = with_trays(base, pull)
        tb = tray_boxes(base, pull)
        print("pull %.2f m: west tray x %.3f..%.3f, east tray x %.3f..%.3f, y %.3f..%.3f" % (pull, tb["w"][0], tb["w"][2], tb["e"][0], tb["e"][2], tb["w"][1], tb["w"][3]))
        for k, v in entry_and_dressing(items).items():
            print("   %-26s %.3f m" % (k, v))
