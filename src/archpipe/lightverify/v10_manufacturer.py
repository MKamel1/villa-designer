"""V10 manufacturer photometric data.

For each bound product the manufacturer ships the same measurement twice (.ies and .ldt, iGuzzini lab, 2026-04-09):
  (a) both files, parsed by this lane's own readers, must agree (lumens, watts, peak cd, 5 axis points) within 1 %;
  (b) the file header states watts and lumens in the luminaire name ("12W 730lm"): integrated lumens must match within 2 %;
  (c) the data-sheet style numbers (axial illuminance at 1, 2, 3 m, beam diameter at 50 % and 10 % of the axial lux) are
      computed from the file here and reproduced by the engine's analytic path within 5 %;
  (d) any published data-sheet point in manufacturer-published.json is reproduced by the engine within 5 % (none could be
      obtained for these codes: the slot is there and the check reports not_evaluated while it is empty);
  (e) the published family lumen range (ArchDaily excerpt) contains the product, and efficacy is within the published maximum.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from . import ies, ldt
from .common import LayerResult, check
from .sources import CARDS, ids
from ..contracts import SourceCard

TOL = 0.05
CARDS["LV-V10-TOL"] = SourceCard("LV-V10-TOL", "archpipe lighting verification plan", "2026-11-21", "V10 pass bar", "",
                                 "published data-sheet point reproduced within 5 %", "policy", "docs/quality/LIGHTING-VERIFICATION.md")
SRC = ids("LV-V10-TOL", "LV-V1-LUMEN", "LV-LM63")
ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "assets" / "user" / "luminaires" / "iguzzini"
PUB = ROOT / "knowledge" / "lighting-verify" / "manufacturer-published.json"


def cone(d: ies.IesData, dist: float) -> dict:
    """Axial illuminance and beam diameters at `dist` for a downlight on the C0 plane (what a data-sheet cone lists)."""
    e0 = ies.candela(d, 0.0, 0.0) / dist ** 2
    out = {"E_axis_lx": e0}
    for lvl, key in ((0.5, "d50_m"), (0.1, "d10_m")):
        g = 0.0
        while g < 89.9:
            e = ies.candela(d, g, 0.0) * math.cos(math.radians(g)) ** 3 / dist ** 2
            if e < lvl * e0:
                break
            g += 0.05
        out[key] = 2 * dist * math.tan(math.radians(g))
    return out


def engine_axis(code: str, ies_path: Path, dist: float) -> float:
    from ..lightcalc.direct import Placement, direct_illuminance
    from ..photometry import load
    ph = load(str(ies_path))
    return direct_illuminance([Placement("p", ph, (0, 0, dist))], (0, 0, 0))


def run() -> LayerResult:
    L = LayerResult("V10")
    pub = json.loads(PUB.read_text())["products"]
    for code in ("LSEVO-AAK3EW", "LSEVO-AAIIA6", "LSEVO-AAHENX"):
        b = LIB / code
        ip = b / ("mfr_%s.ies" % code)
        itext = ip.read_text(errors="replace")
        di = ies.parse(itext)
        dl = ldt.parse((b / (code + ".ldt")).read_text(errors="replace"))
        li, ll = ies.lumens(di), ies.lumens(dl)
        rows = []

        def add(name, ok, msg, ach=None, req=None, unit=""):
            L.results.append(check("LV10", "pass" if ok else "fail", "%s/%s" % (code, name), SRC, achieved=ach, required=req, unit=unit, message=msg))
            rows.append((name, ok, msg))

        axis = [(g, c) for g in (0, 10, 20, 30) for c in (0.0, 90.0)]
        worst = max(abs(ies.candela(di, g, c) / max(1e-9, ies.candela(dl, g, c)) - 1) for g, c in axis if ies.candela(dl, g, c) > 50)
        ok = abs(li / ll - 1) < 0.01 and worst < 0.01 and abs(di.input_watts - dl.input_watts) < 0.05 and abs(ies.peak_cd(di) / ies.peak_cd(dl) - 1) < 0.01
        add("ies-vs-ldt", ok, ".ies %.1f lm / %.2f W / peak %.0f cd; .ldt %.1f lm / %.2f W / peak %.0f cd; worst axis-point difference %.2f %%"
            % (li, di.input_watts, ies.peak_cd(di), ll, dl.input_watts, ies.peak_cd(dl), 100 * worst), li, ll, "lm")
        lum = di.header.get("LUMINAIRE", "")
        m = re.search(r"(\d+(?:\.\d+)?)\s*W\s+(\d+)\s*lm", lum)
        if m:
            hw, hl = float(m.group(1)), float(m.group(2))
            add("header-stated", abs(li / hl - 1) < 0.02 and abs(hw - di.input_watts) < 0.1,
                "manufacturer header says %g W %g lm; integrated %.1f lm, file %.2f W" % (hw, hl, li, di.input_watts), li, hl, "lm")
        else:
            L.results.append(check("LV10", "not_evaluated", code + "/header-stated", (), message="no 'NW NNNlm' text in the file header"))
        for dist in (1.0, 2.0, 3.0):
            c = cone(di, dist)
            e_eng = engine_axis(code, ip, dist)
            add("axial-%gm" % dist, abs(e_eng / c["E_axis_lx"] - 1) < TOL,
                "from file %.0f lx, engine %.0f lx; beam dia. %.2f m at 50 %%, %.2f m at 10 %% of axial" % (c["E_axis_lx"], e_eng, c["d50_m"], c["d10_m"]),
                round(e_eng, 1), round(c["E_axis_lx"], 1), "lx")
            L.table.append(dict(code=code, dist=dist, **c, engine_lx=e_eng))
        p = pub[code]
        lo, hi = p["lumen_range_lm"]
        eff = li / di.input_watts
        if p.get("range_indicative_only"):
            L.results.append(check("LV10", "not_evaluated", code + "/published-family-range", (),
                                   message="family range is for a different variant (indicative only): %.0f lm vs %d-%d lm" % (li, lo, hi)))
        else:
          add("published-family-range", lo <= li <= hi and eff <= p["efficacy_max_lm_per_w"],
              "integrated %.0f lm (published family %d-%d lm), %.0f lm/W (published max %g)" % (li, lo, hi, eff, p["efficacy_max_lm_per_w"]), li, None, "lm")
        if p["datasheet_points"]:
            for pt in p["datasheet_points"]:
                e = engine_axis(code, ip, pt["distance_m"])
                add("published-%gm" % pt["distance_m"], abs(e / pt["E_lx"] - 1) <= TOL,
                    "published %g lx at %g m (%s), engine %.0f lx" % (pt["E_lx"], pt["distance_m"], pt.get("source", ""), e), e, pt["E_lx"], "lx")
        else:
            L.results.append(check("LV10", "not_evaluated", code + "/published-datasheet-points", (),
                                   message="no published data-sheet cone could be obtained for this code (see manufacturer-published.json)"))
    L.notes.append("manufacturer data-sheet cone points are NOT verified (not obtainable); .ies and .ldt of the same lab measurement are cross-checked instead")
    return L
