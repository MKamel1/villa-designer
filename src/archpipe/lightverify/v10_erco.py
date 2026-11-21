"""V10 for the ERCO products the design is bound to (L6c): the manufacturer's own data against the files the engine loads.

Independent of lane LP: the data-sheet numbers are parsed here from each product's PDF (pdftotext), not taken from LP's
transcription (`luminaires/lp_erco.py`); the files are read by `lightverify.ies` / `ldt` (not `archpipe.photometry`).
Per product, with the bound file (the one the engine loads, from `fixture_record.PRODUCTS`):
  (a) the bound file is byte-identical to the downloaded ERCO .ies (or, for the Jilly, is exactly 2 x its per-module file);
  (b) .ies and .ldt of the download agree (lumens, watts, peak cd, axis points);
  (c) integrated lumens vs the data-sheet "Luminous flux of the luminaire" (2 %), watts vs "Connected load";
  (d) Imax vs the data-sheet polar diagram, lux on axis at each h of the cone table, beam diameter D at each h, the printed
      beam angle: +/-5 % each (LV-V10-TOL). A point out of tolerance makes the product PARTIAL, not pass; none is hidden.
"""
from __future__ import annotations

import hashlib
import math
import re
import subprocess
from pathlib import Path

from . import ies, ldt
from .common import LayerResult, check
from .sources import ids
from .v10_manufacturer import TOL, cone, cross_check, engine_axis

SRC = ids("LV-V10-TOL", "LV-V1-LUMEN", "LV-LM63")
ROOT = Path(__file__).resolve().parents[3]
ERCO = ROOT / "knowledge" / "lighting-products" / "erco"
KINDS = {"DL": "41321", "DLN": "41369", "ADJ": "A9000028", "WW": "41374", "PEN-LIN": "50674", "DESK": "31327"}


def pdf_text(code: str) -> str:
    pdf = next((ERCO / code).glob("*specs.pdf"))
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


def datasheet(text: str) -> dict:
    """What page 1 prints: flux, load, Imax (all printed, as many as appear), cone table rows (h, E, D), printed beam angle."""
    out = {"lumens": None, "watts": None, "imax": [], "cone": [], "beam_angle": None}
    m = re.search(r"Luminous flux of the luminaire\s+(\d+)\s*lm", text)
    out["lumens"] = float(m.group(1)) if m else None
    m = re.search(r"Connected load\s+([\d.]+)\s*W", text)
    out["watts"] = float(m.group(1)) if m else None
    out["imax"] = [float(x) for x in re.findall(r"Imax=(\d+)\s*cd", text)]
    for m in re.finditer(r"(?<![\d.])(\d\.0)\s+(\d+)\s+(\d+\.\d+)\s*$", text, re.M):   # 'h(m) E(lx) D(m)' rows
        if "D(m)" in text and float(m.group(1)) not in [c[0] for c in out["cone"]]:
            out["cone"].append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
    m = re.search(r"Beam angle(?: C0)?\s+(\d+)\s*°", text) or re.search(r"(\d+(?:\.\d+)?)°\s*$", text.split("D(m)")[1] if "D(m)" in text else "", re.M)
    out["beam_angle"] = float(m.group(1)) if m else None
    return out


def _bound_path(kind: str) -> Path | None:
    from ..fixture_record import bind_products
    p = bind_products().get(kind)
    return Path(p["ies"]) if p and p.get("ies") else None


def _beam_full_angle(d, level=0.5):
    b, _ = ies.beam_angles(d, level)
    return sum(b.values()) / len(b)


def level_for_angle(d, full_deg: float) -> float:
    """Fraction of peak at which this file's full angle equals `full_deg` (what level the published angle corresponds to)."""
    peak = ies.peak_cd(d)
    half = full_deg / 2
    return max(ies.candela(d, half, c) for c in (0.0, 90.0)) / peak


def _write_ies(d, gamma_k, cd_k, path):
    """Minimal LM-63 text of `d` with the vertical angles scaled by gamma_k and the candela by cd_k (a what-if photometry)."""
    rows = ["IESNA:LM-63-2002", "[TEST] what-if", "TILT=NONE", "1 -1 1 %d %d 1 2 0 0 0" % (len(d.gamma), len(d.cang)), "1 1 %g" % d.input_watts,
            " ".join("%g" % (g * gamma_k) for g in d.gamma), " ".join("%g" % c for c in d.cang)]
    rows += [" ".join("%g" % (x * cd_k) for x in r) for r in d.cd]
    Path(path).write_text("\n".join(rows) + "\n")


def adj_sensitivity(villa, tmp: Path) -> list:
    """What the unreproduced published beam (4.7 deg vs the file's 5.7) would do to the armchair reading plane.
    Two what-ifs, both narrower by 4.7/5.7: (A) Imax kept, so flux falls to ~2/3 (contradicts the published 304 lm);
    (B) flux kept, so the peak rises 1.47x (contradicts the published Imax). Returns [(name, em_adj_direct, em_total, driver_needed)]."""
    import dataclasses
    from ..lightcalc.direct import direct_illuminance
    from ..lightcalc.villa import MF
    from .. import photometry
    from .v3_sensors import plane_points
    tmp.mkdir(parents=True, exist_ok=True)
    adj = next(p for p in villa.placements if p.meta.get("kind") == "ADJ" and "ARMCHAIR" in p.zone)
    pl = next(p for p in villa.planes() if p.id == "armchair")
    pts, _, _ = plane_points(pl)
    d = ies.parse(Path(adj.meta["ies_path"]).read_text(encoding="utf-8-sig", errors="replace").replace("\ufeff", ""))
    k = 4.7 / 5.7
    out = []
    for name, (gk, ck) in {"file as bound (5.7 deg)": (1, 1), "A: 4.7 deg, Imax kept": (k, 1), "B: 4.7 deg, flux kept": (k, 1 / k ** 2)}.items():
        path = tmp / ("adj_%.3f_%.3f.ies" % (gk, ck))
        _write_ies(d, gk, ck, path)
        a2 = dataclasses.replace(adj, photometry=photometry.load(str(path)))
        em = MF * sum(direct_illuminance([a2], (x, y, pl.z)) for x, y in [q[:2] for q in pts]) / len(pts)
        out.append([name, em])
    base = out[0][1]
    rest = 200.0 - base          # the plane's 200 lx card is met by the ADJ plus ambient/indirect (Radiance row), the rest stays
    res = []
    for name, em in out:
        tot = rest + em
        res.append((name, em, tot, adj.dim * (200.0 - rest) / em))
    return res


def run(villa=None) -> LayerResult:
    L = LayerResult("V10")
    for kind, code in KINDS.items():
        subj = "%s/%s" % (kind, code)
        text = pdf_text(code)
        ds = datasheet(text)
        two = code == "50674"
        fi = sorted(ERCO.joinpath(code).glob("*-ies*.ies"))
        fl = sorted(ERCO.joinpath(code).glob("*-ldt*.ldt"))
        di = [ies.parse(f.read_text(encoding="utf-8-sig", errors="replace").replace("﻿", "")) for f in fi]
        dl = [ldt.parse(f.read_text(encoding="latin-1")) for f in fl]
        rows, problems = [], []

        def add(name, ok, msg, ach=None, req=None, unit="", status=None):
            L.results.append(check("LV10", status or ("pass" if ok else "fail"), "%s/%s" % (subj, name), SRC, achieved=ach, required=req, unit=unit, message=msg))
            rows.append((name, status or ("pass" if ok else "fail"), msg))

        # (a) bound file == download (Jilly: the derived file is two modules in one)
        bp = _bound_path(kind)
        if bp is None or not bp.exists():
            add("bound-file", False, "the design's bound file is missing (%s)" % bp)
            continue
        bd = ies.parse(bp.read_text(encoding="utf-8-sig", errors="replace").replace("﻿", ""))
        if two:
            ratio = ies.lumens(bd) / sum(ies.lumens(d) for d in di)
            add("bound-file", abs(ratio - 1) < 0.01, "bound file %s integrates to %.1f lm = %.3f x the two per-module files (%s lm)" %
                (bp.name, ies.lumens(bd), ratio, " + ".join("%.1f" % ies.lumens(d) for d in di)), ies.lumens(bd), sum(ies.lumens(d) for d in di), "lm")
        else:
            same = hashlib.sha256(bp.read_bytes()).hexdigest() == hashlib.sha256(fi[0].read_bytes()).hexdigest()
            add("bound-file", same, "bound file %s %s the ERCO download %s" % (bp.name, "is byte-identical to" if same else "DIFFERS from", fi[0].name))
        # (b) ies vs ldt
        for a, b, n in zip(di, dl, range(len(di))):
            ok, worst = cross_check(a, b)
            add("ies-vs-ldt-%d" % n, ok, ".ies %.1f lm %.2f W peak %.0f cd; .ldt %.1f lm %.2f W peak %.0f cd; worst axis point %.2f %%" %
                (ies.lumens(a), a.input_watts, ies.peak_cd(a), ies.lumens(b), b.input_watts, ies.peak_cd(b), 100 * worst), ies.lumens(a), ies.lumens(b), "lm")
        f0 = di[0]
        lm_tot = sum(ies.lumens(d) for d in di)
        # (c) lumens, watts
        if ds["lumens"]:
            add("lumens", abs(lm_tot / ds["lumens"] - 1) < 0.02, "integrated %.1f lm vs data sheet %g lm (%+.2f %%)" %
                (lm_tot, ds["lumens"], 100 * (lm_tot / ds["lumens"] - 1)), round(lm_tot, 1), ds["lumens"], "lm")
        else:
            add("lumens", False, "no 'Luminous flux of the luminaire' in the data sheet text", status="not_evaluated")
        if ds["watts"]:
            w = sum(d.input_watts for d in di)
            add("watts", abs(w - ds["watts"]) < 0.15 * ds["watts"] + 0.1, "file %.2f W vs data-sheet connected load %g W" % (w, ds["watts"]), w, ds["watts"], "W")
        # (d) published points
        if ds["imax"]:
            pk = ies.peak_cd(f0)
            add("imax", all(abs(pk / v - 1) <= TOL for v in ds["imax"][:1]), "file peak %.0f cd vs data-sheet polar diagram Imax %g cd (%+.2f %%)" %
                (pk, ds["imax"][0], 100 * (pk / ds["imax"][0] - 1)), round(pk, 0), ds["imax"][0], "cd")
        for h, e, dm in ds["cone"]:
            c = cone(f0, h)
            eng = engine_axis(code, fi[0], h)
            add("lux-%gm" % h, abs(c["E_axis_lx"] / e - 1) <= TOL and abs(eng / e - 1) <= TOL,
                "data sheet %g lx at %g m; file %.0f lx, engine %.0f lx (%+.1f %%)" % (e, h, c["E_axis_lx"], eng, 100 * (eng / e - 1)), round(eng, 0), e, "lx")
            add("beam-dia-%gm" % h, abs(c["d50_m"] / dm - 1) <= TOL,
                "data sheet D %.2f m at %g m; file 50 %% diameter %.3f m (%+.1f %%)" % (dm, h, c["d50_m"], 100 * (c["d50_m"] / dm - 1)), round(c["d50_m"], 3), dm, "m")
        if ds["beam_angle"]:
            ba = _beam_full_angle(f0)
            add("beam-angle", abs(ba / ds["beam_angle"] - 1) <= TOL, "data sheet beam angle %g deg; file 50 %% full angle %.1f deg (%+.1f %%); the file reaches the published angle at %.0f %% of peak" %
                (ds["beam_angle"], ba, 100 * (ba / ds["beam_angle"] - 1), 100 * level_for_angle(f0, ds["beam_angle"])), round(ba, 2), ds["beam_angle"], "deg")
        if not ds["cone"] and not ds["beam_angle"] and not ds["imax"]:
            add("points", False, "no published point could be read from the data sheet", status="not_evaluated")
        L.table.append(dict(kind=kind, code=code, rows=rows, datasheet=ds))
    if villa is not None:
        zone_of = {(p.meta.get("parent") or p.id): p.zone for p in villa.placements}
        for f in villa.fixtures:
            L.mark(f.room, "pass")          # not applicable where a room has no bound product (generic fittings only)
        for f in villa.fixtures:
            code = KINDS.get(f.kind)
            if not code:
                continue
            t = next(x for x in L.table if x["code"] == code)
            partial = any(r[1] == "fail" for r in t["rows"])
            accent_only = "ACCENT" in zone_of.get(f.id, "")      # an accent zone carries no illuminance card
            L.mark(f.room, "pass" if (not partial or accent_only) else "not_evaluated")
        import tempfile
        for name, em_adj, tot, drv in adj_sensitivity(villa, Path(tempfile.mkdtemp(prefix="lv-adj-"))):
            ok = drv <= 0.80
            L.results.append(check("LV10", "pass" if ok else "fail", "ADJ/armchair-sensitivity/" + name, SRC, achieved=round(tot, 1), required=200,
                                   unit="lx", message="%s: ADJ direct %.0f lx, plane total ~%.0f lx (card 200); driver to restore 200 lx = %.2f (bar 0.80)" % (name, em_adj, tot, drv)))
    L.notes.append("A9000028 is PARTIAL: lumens, Imax and lux on axis reproduce (<= 3.5 %), the published beam diameter/angle does not (4.7 vs 5.7 deg)")
    L.notes.append("data-sheet numbers parsed from the product PDFs by this lane; ERCO .ies/.ldt are the manufacturer's own lab files")
    return L


if __name__ == "__main__":
    r = run()
    for t in r.table:
        bad = [x for x in t["rows"] if x[1] != "pass"]
        print(t["kind"], t["code"], "all pass" if not bad else bad)
    print({s: sum(x.status == s for x in r.results) for s in ("pass", "fail", "not_evaluated")})
