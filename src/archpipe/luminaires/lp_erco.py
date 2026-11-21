"""Lane LP: ERCO products from erco.com (public pages, real Chrome, 2026-11-21).

Files are copied byte-for-byte from the directory the browser downloaded them to (SRC, default /tmp/lpb/erco).
Every published point below was read from the product's own datasheet PDF (page 1) and carries its quote;
none is computed. Lumens are the datasheet 'Luminous flux of the luminaire'.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from archpipe.luminaires import eulumdat as eu
from archpipe.luminaires import v10

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "knowledge/lighting-products/erco"
SRC = Path(os.environ.get("LP_ERCO_SRC", "/tmp/lpb/erco"))
P = v10.Point
IMG = "datasheet p1 polar diagram 'Imax={}cd'"
LM = "datasheet p1 'Luminous flux of the luminaire {}lm'"


def _cone(art, rows, beam):
    """rows: (h_m, lux, D_m) read from the 'h(m) E(lx) D(m)' table on datasheet p1."""
    pts = [P("lux_axis", e, h, f"datasheet p1 cone table h={h} E={e}") for h, e, _ in rows]
    pts += [P("beam_diameter", d, h, f"datasheet p1 cone table h={h} D={d}") for h, _, d in rows]
    pts.append(P("beam_angle", beam, None, f"datasheet p1 cone table header '{beam}°'"))
    return pts


# code -> dict(kinds, name, page, stated lumens, file stem, points, extra)
PRODUCTS = {
    "41321.000": dict(kinds=["DL"], stem="41321-000", name="Quintessence Downlight, wide flood, 12.1 W 2700 K CRI 92, DALI",
        lm=1065, points=[P("imax", 1147, None, IMG.format(1147)), P("beam_angle", 56, None, "datasheet p1 'Beam angle C0 56°'"),
                         P("lumens", 1065, None, LM.format(1065))], ip="IP20", ugr=None, dim="DALI-2, 1-100 % CCR"),
    "41369.000": dict(kinds=["DLN"], stem="41369-000", name="Quintessence Downlight, extra wide flood, 12.1 W 2700 K CRI 92, DALI",
        lm=904, points=[P("imax", 535, None, IMG.format(535)), P("beam_angle", 89, None, "datasheet p1 'Beam angle C0 89°'"),
                        P("lumens", 904, None, LM.format(904))], ip="IP20", ugr=None, dim="DALI-2, 1-100 % CCR"),
    "A9000028": dict(kinds=["ADJ"], stem="A9000028", name="Optec New Spotlight M, narrow spot, 4.2 W 2700 K CRI 92, track, on-board dim",
        lm=304, points=[P("imax", 22846, None, IMG.format(22846)), P("lumens", 304, None, LM.format(304))] +
        _cone("A9000028", [(1, 22846, .08), (2, 5711, .16), (3, 2538, .25), (4, 1428, .33), (5, 914, .41)], 4.7),
        ip="IP20", ugr=None, dim="on-board rotary dim, 1-100 % CCR"),
    "A9001547": dict(kinds=["ADJ"], stem="A9001547", name="Optec New Spotlight L, narrow spot, 9.4 W 2700 K CRI 92, track, on-board dim",
        lm=855, points=[P("imax", 57848, None, IMG.format(57848)), P("lumens", 855, None, LM.format(855))] +
        _cone("A9001547", [(1, 57848, .09), (2, 14462, .17), (3, 6428, .26), (4, 3615, .35), (5, 2314, .44)], 5.0),
        ip="IP20", ugr=None, dim="on-board rotary dim, 1-100 % CCR"),
    "41374.000": dict(kinds=["WW"], stem="41374-000", name="Quintessence Lens wallwasher, 8.1 W 2700 K CRI 92, DALI",
        lm=399, points=[P("imax", 471, None, IMG.format(471)), P("lumens", 399, None, LM.format(399))],
        ip="IP20", ugr=None, dim="DALI-2, 1-100 % CCR"),
    "26141.000": dict(kinds=["WW"], stem="26141-000", name="Pantrac Lens wallwasher, 12.1 W 2700 K CRI 92, track, phase dimmable",
        lm=777, points=[P("imax", 1036, None, IMG.format(1036)), P("lumens", 777, None, LM.format(777))],
        ip="IP20", ugr=None, dim="phase dimmable + on-board dim, 1-100 % CCR_PWM"),
    "50674.000": dict(kinds=["PEN-LIN"], stem="50674-000", name="Jilly Pendant downlight 1500 mm, 2 x 11.2 W 2700 K CRI 92, DALI, UGR 19",
        lm=3558, points=[P("imax", 1055, None, IMG.format(1055) + " (printed for each of the two light emissions)"),
                         P("beam_angle", 86, None, "datasheet p1 'Beam angle C0 86°'")],
        ip="IP20", ugr="UGR 19 (datasheet p1); 'UGR glare evaluation C0 18'", dim="DALI-2, 1-100 % CCR",
        two_files=True),
    "31327.000": dict(kinds=["DESK"], stem="31327-000", name="Lucy Task light, wide beam, 9.4 W 2700 K CRI 92, on-board dim",
        lm=234, points=[P("imax", 454, None, IMG.format(454)), P("lumens", 234, None, LM.format(234))],
        ip="IP20", ugr=None, dim="push-button dimmer, 1-100 % CCR_PWM"),
    "B0000184": dict(kinds=[], exterior="terrace/step downlight", stem="B0000184",
        name="Iku Surface-mounted downlight IP65, 5 W 3000 K CRI 92 ('Version with 2700K or 3500K CRI 92 available on request')",
        lm=676, points=[P("imax", 815, None, IMG.format(815)), P("lumens", 676, None, LM.format(676))] +
        _cone("B0000184", [(1, 815, 1.03), (2, 204, 2.06), (3, 91, 3.09), (4, 51, 4.12), (5, 33, 5.15)], 54.5),
        ip="IP65, IK07", ugr=None, dim="DALI-2, 1-100 % CCR"),
    "35720.000": dict(kinds=[], exterior="bollard", stem="35720-000",
        name="Castor Bollard floor washlight IP65, 8.1 W 3000 K CRI 92 ('Version with 3000K CRI 97 or 2700K ... available on request')",
        lm=198, points=[P("imax", 135, None, IMG.format(135)), P("lumens", 198, None, LM.format(198))],
        ip="IP65, IK10", ugr=None, dim="switchable only (datasheet 'Dimming range --')"),
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def product(art: str) -> dict:
    d = PRODUCTS[art]
    code = art.replace(".000", "")
    dest = OUT / code
    dest.mkdir(parents=True, exist_ok=True)
    pre = f"erco-{d['stem']}-en"
    files = {}
    names = ([f"{pre}-specs.pdf"] + ([f"{pre}-ldt-{i}.ldt" for i in (1, 2)] + [f"{pre}-ies-{i}.ies" for i in (1, 2)]
             + ["erco-en-2026-11-21-19-02-21.zip", "erco-en-2026-11-21-19-02-24.zip"]   # the downloads as served
             if d.get("two_files") else [f"{pre}-ldt.ldt", f"{pre}-ies.ies"]))
    for n in names:
        src = SRC / n
        if not src.exists():
            src = ROOT / "knowledge/lighting-products/erco" / code / n   # already stored
        if src.resolve() != (dest / n).resolve():
            shutil.copyfile(src, dest / n)
        files[n] = dict(
            path=f"knowledge/lighting-products/erco/{code}/{n}", sha256=_sha(dest / n))
    ies = dest / (f"{pre}-ies-1.ies" if d.get("two_files") else f"{pre}-ies.ies")
    ldt = dest / (f"{pre}-ldt-1.ldt" if d.get("two_files") else f"{pre}-ldt.ldt")
    L = eu.load(ldt)
    ls = L.lamp_sets[0]
    stated = d["lm"] / 2 if d.get("two_files") else d["lm"]
    result = v10.check_product(ies, stated_lumens=stated, points=list(d["points"]))
    own = [r for r in result["points"] if r["kind"] != "lumens"]
    ok_l = result["lumens"]["status"] == "pass"
    status = ("pass" if ok_l and own and all(r["status"] == "pass" for r in own)
              else "partial" if ok_l and any(r["status"] == "pass" for r in own)
              else "fail")
    worst = max([result["lumens"]["worst_error"]] + [r["worst_error"] for r in result["points"] if r["status"] == "pass"])
    side = dict(code=code, maker="erco", name=d["name"], fetched=time.strftime("%Y-%m-%d"),
                product_url=f"https://www.erco.com/{art}" if "." in art else f"https://www.erco.com/{art}",
                download_service="https://download-service.erco.com/download/en?articleIds=%s&types=15|4|3&formattedId=false" % art,
                retrieval="real Chrome via Playwright; page requests only; public, no login",
                files=files, redistribution="ERCO offers these files publicly for lighting design; terms not separately read")
    (dest / "source.json").write_text(json.dumps(side, indent=1), encoding="utf-8")
    alias = {"pdf": files[names[0]], "ldt": files[ldt.name], "ies": files[ies.name]}
    return dict(code=code, maker="erco", name=d["name"], kinds=d["kinds"], exterior=d.get("exterior"),
                lumens=d["lm"], watts=float(ls.watts), cct_k=ls.cct_k, cri_ra=float(str(ls.cri).split("/")[-1]) if ls.cri else None,
                r9=None, dimming=d["dim"], flicker="datasheet: TLA SVM <= 0.1/0.4; PstLM <= 1 (as printed)", ip=d["ip"],
                ugr_cutoff=d["ugr"], egypt_or_eu="EU/UK/AU marks on datasheet; Egypt distributor not stated",
                v10_status=status, v10=result, worst_error_passing=worst, files=alias, all_files=files, urls=[side["product_url"]],
                notes=[], two_files=bool(d.get("two_files")))


def products() -> list:
    return [product(a) for a in PRODUCTS]


if __name__ == "__main__":
    for p in products():
        print(p["code"], p["v10_status"], p["worst_error_passing"], [(r["kind"], r["distance_m"], r["status"], r["worst_error"]) for r in p["v10"]["points"] if r["status"] != "pass"])
