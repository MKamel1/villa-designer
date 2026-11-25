"""Lane LP: assemble knowledge/lighting-products/ and candidates.json from files that were really obtained.

Nothing here types a photometric value: lumens, watts, CCT, CRI come from the product's own LDT/IES;
published points are listed in PUBLISHED with the page they were read from. A figure not on the file or
datasheet stays None.
"""
from __future__ import annotations

from archpipe.safe_io import copy_file
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from archpipe import fixture_record as fr
from archpipe.luminaires import eulumdat as eu
from archpipe.luminaires import lp_erco, v10

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "knowledge/lighting-products"
SRC = ROOT / "assets/user/luminaires/iguzzini"       # iGuzzini files fetched by archpipe.luminaires.iguzzini
TODAY = time.strftime("%Y-%m-%d")

# code -> (kinds it could fill, url of the product page if known, published points read from the page)
PRODUCTS = {
    "LSEVO-AAK3EW": (["DL", "WW"], None, []),
    "LSEVO-AAIIA6": (["DLN"], None, []),
    "LSEVO-AAHENX": (["ADJ"], None, []),
    "LSEVO-AAKR2I": (["WW"], None, []),
    "ST49": (["COVE", "BACK", "NL", "TOE"], "https://www.iguzzini.com/en/st49/", []),
    # page https://www.iguzzini.com/en/st39/ read 2026-11-24: Maximum intensity 577 cd, 1780 lm per metre (title), 15 W/m, CRI 92, 2700 K, IP65 uncut
    "ST39": (["PCOVE"], "https://www.iguzzini.com/en/st39/",
             [v10.Point("imax", 577, source="product page 'Maximum intensity (cd)' 577"),
              v10.Point("lumens", 1780, source="product page '15W 1780lm (1.0 m)'")]),
    # page https://www.iguzzini.com/en/451g/ read 2026-11-21: Maximum intensity 5759 cd, beam F - Flood 34 deg,
    # 1957.5 lm system, 19.9 W, CRI 92, 3000 K, LOR 87
    "451G": ([], "https://www.iguzzini.com/en/451g/",
             [v10.Point("imax", 5759, source="product page 'Maximum intensity (cd)'"),
              v10.Point("beam_angle", 34, source="product page 'F - Flood 34°'"),
              v10.Point("lumens", 1957.5, source="product page '1957.5 lm system'")]),
}

# Where each maker stood when tried (2026-11-21). Every row is something observed, not assumed.
SOURCING_LOG = [
    dict(maker="ERCO", result="obtained (2nd run, real Chrome)", detail="scripted HTTP gets hit a Vercel checkpoint (not circumvented); a normal Chrome visit passes. Per-article datasheet PDF, LDT and IES come from download-service.erco.com, the same endpoint the page buttons call; 3 s pauses between requests."),
    dict(maker="Thorn", result="blocked", detail="thornlighting.com returned HTTP 403 to an automated request."),
    dict(maker="Signify", result="not retried", detail="the Signify file API refused unauthenticated requests and "
         "archpipe.luminaires.signify documents robots.txt disallowing automated access; not retried with the browser."),
    dict(maker="Zumtobel", result="not retried", detail="product pages offer 'LDT/IES Range Download' through "
         "JavaScript (data-type=ldt/ies, href '#'); no static file URL in the HTML."),
    dict(maker="Delta Light", result="pages load in Chrome; files not obtained", detail="family page (lunelle) loads "
         "(HTTP 200) but files and variant data are generated per reference by api.deltalight.com after JavaScript "
         "variant selection; not pursued in the 2nd run (ERCO took the time box); robots.txt crawl delay 10-20 s."),
    dict(maker="Astro", result="no photometry", detail="datasheet PDFs are public but state 'Lamp Dependent' for "
         "flux, CCT and CRI and the site links no IES/LDT file."),
    dict(maker="Lumenpulse", result="files public, datasheet lacks points", detail="IES zips download without "
         "login (checked: LCRS fixed-tilt zip) but the North-American spec sheet gives nominal beam angles and "
         "no measured lux/cd table in its text; not used."),
    dict(maker="iGuzzini", result="partial", detail="LDT/IES are static, robots-permitted URLs; family pages are "
         "rendered by JavaScript so product codes cannot be listed by a script; product pages publish Imax, flux, "
         "LOR and beam angle but no lux-at-distance cone table or datasheet PDF."),
    dict(maker="Flos / Reggiani / Wever & Ducre", result="not tried (flos.com home loads 200 in Chrome)",
         detail="wever-ducre.com did not connect; Flos and Reggiani only redirected on the first probe."),
]


def _ra(group_index: str):
    """LDT writes '1A/97' (CRI group / index); the number after the slash is Ra."""
    m = re.search(r"(\d+)\s*$", group_index)
    return float(m.group(1)) if m else None


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _product(code: str) -> dict:
    kinds, url, points = PRODUCTS[code]
    src = SRC / code
    dest = OUT / "iguzzini" / code
    dest.mkdir(parents=True, exist_ok=True)
    ldt = next(src.glob("*.ldt"))
    ies = next(src.glob("mfr_*"))
    files = {}
    for kind, f in (("ldt", ldt), ("ies", ies)):
        name = f"{code}.{kind}"
        copy_file(f, dest / name)
        files[kind] = dict(path=f"knowledge/lighting-products/iguzzini/{code}/{name}", sha256=_sha(dest / name))
    L = eu.load(dest / f"{code}.ldt")
    ls = L.lamp_sets[0]
    text = (dest / f"{code}.ies").read_text(encoding="latin-1")
    name = re.search(r"\[LUMINAIRE\](.*)", text).group(1).strip()
    stated = float(re.findall(r"(\d+(?:\.\d+)?)\s*lm\b", name)[-1])
    pts = list(points)
    result = v10.check_product(dest / f"{code}.ies", stated_lumens=stated, points=pts)
    own = [r for r in result["points"] if r["kind"] != "lumens"]
    status = ("pass" if result["lumens"]["status"] == "pass" and own and all(r["status"] == "pass" for r in own)
              else "fail" if result["status"] == "fail"
              else "lumens-only" if result["lumens"]["status"] == "pass" else "not_evaluated")
    dim = "phase-cut (trailing and leading edge)" if "Phase cut" in name else None
    side = dict(code=code, maker="iguzzini", name=name, fetched=TODAY if url else None,
                product_url=url, files=files, redistribution=(
                    "iGuzzini serves these LDT/IES files publicly for design use; terms not separately read"),
                origin_note=None if url else
                "imported 2026-09-27 by archpipe.luminaires.iguzzini inbox; product page URL not recorded")
    (dest / "source.json").write_text(json.dumps(side, indent=1), encoding="utf-8")
    return dict(
        code=code, maker="iguzzini", name=name, kinds=kinds, lumens=stated, watts=float(ls.watts),
        beam_deg=None if L.isym == 2 or not re.search(r"Flood|Medium|Spot|Narrow", name) else round(
            v10.beam_full_angle_independent(v10.read_ies(text)), 1),
        beam_note="computed from the file (50 % of axis), not published", cct_k=ls.cct_k, cri_ra=_ra(ls.cri),
        r9=None, dimming=dim, flicker=None, ip=None, ugr_cutoff=None, egypt_or_eu=None,
        v10_status=status, v10=result, files=files, urls=[u for u in [url] if u],
        notes=[], watts_note="LDT lamp-set watts")


# role notes: what each product does NOT meet for its kind (from fixture_record.KINDS)
def _notes(p: dict) -> list:
    notes = []
    for k in p["kinds"]:
        spec = fr.KINDS[k]
        if "lm_per_m" in spec and p["lumens"] < spec["lm_per_m"]:
            notes.append(f"{k}: {p['lumens']:.0f} lm/m is below the kind's {spec['lm_per_m']} lm/m; needs more run or "
                         "is a different brightness class")
        if "lm" in spec and spec["lm"] and abs(p["lumens"] - spec["lm"]) / spec["lm"] > 0.35:
            notes.append(f"{k}: {p['lumens']:.0f} lm is far from the kind's {spec['lm']} lm")
        if p["cct_k"] and p["cct_k"] != spec["cct"]:
            notes.append(f"{k}: file CCT {p['cct_k']:.0f} K, kind wants {spec['cct']} K")
    if p["code"] in PAIR_FAILED:
        notes.append("library pair check: LDT and manufacturer IES disagree (" + PAIR_FAILED[p["code"]] +
                     "); the IES integrates to the stated lumens, the LDT is not trusted")
    if p["code"] == "LSEVO-AAK3EW" and "WW" in p["kinds"]:
        notes.append("WW: a flood downlight grazing from 0.3 m, a substitute, not a wall washer")
    return notes


# from the PRODUCT_CHOICE comment in fixture_record.py (lane L6b's library import, 2026-09)
PAIR_FAILED = {"ST49": "59.8 % flux", "ST39": "96.3 % worst direction", "LSEVO-AAKR2I": "100 %, asymmetric"}


def build() -> dict:
    prods = [_product(c) for c in PRODUCTS] + lp_erco.products()
    for p in prods:
        p["notes"] = _notes(p)
    by_kind = {}
    for k in fr.KINDS:
        cands = [p for p in prods if k in p["kinds"]]
        rank = {"pass": 0, "partial": 1, "lumens-only": 2, "not_evaluated": 3, "fail": 4}
        by_kind[k] = sorted(cands, key=lambda p: rank[p["v10_status"]])
    ref = [_slim(p) for p in prods if not p["kinds"]]
    out = dict(generated=TODAY, reference_products_no_kind=ref, note="V10 'pass' needs the integrated lumens within 2 % AND at least one published "
               "non-lumen point reproduced within 5 % by both routes. 'lumens-only' means the file's flux matches "
               "the figure in the manufacturer's product name but no measured point was obtainable.",
               sourcing_log=SOURCING_LOG, kinds={k: [_slim(p) for p in v] for k, v in by_kind.items()})
    (OUT / "candidates.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def _slim(p):
    return {k: v for k, v in p.items() if k != "kinds"}


if __name__ == "__main__":
    r = build()
    for k, v in r["kinds"].items():
        print(k, [(p["code"], p["v10_status"]) for p in v])
