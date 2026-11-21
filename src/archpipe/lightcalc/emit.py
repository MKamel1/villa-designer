"""Turn the committed reference and smoke-run results into CheckResult records (out/checks/L6.json)."""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..contracts import CheckResult, write_results
from . import checks, ugr
from .sources import CARDS

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "knowledge" / "lighting" / "L6-reference-results.json"
DIN = ROOT / "knowledge" / "lighting" / "L6-dining-result.json"
TOL = 0.05          # LA1 row: "must reproduce the CIE 171:2006 cases within +/-5 %"


def reference_results() -> list[CheckResult]:
    d = json.loads(REF.read_text(encoding="utf-8"))
    out = []
    r52 = d["case_5_2"]
    for key, label in (("max_abs_err_radiance", "Radiance"), ("max_abs_err_analytic", "analytic")):
        e = r52[key]
        out.append(CheckResult("LA1", "L6", "pass" if e <= TOL else "fail", f"ref/CIE171-5.2/{label}", achieved=e * 100,
                               required=TOL * 100, unit="% max error",
                               message=(f"{label}: max |error| {e * 100:.3f} % over 10 points vs published E "
                                        f"(111.11 ... 49.39 lx); tolerance {TOL * 100:g} %"),
                               source_ids=("CIE171-2006-5.2-via-DAU",)))
    for row in d["case_5_8"]["rows"]:
        e = abs(row["err_vs_published"])
        out.append(CheckResult("LA1", "L6", "pass" if e <= TOL else "fail", f"ref/CIE171-5.8/rho={row['rho']}",
                               achieved=row["E_indirect_ab2"], required=row["published_Eav"], unit="lx",
                               message=(f"mean indirect E {row['E_indirect_ab2']:.1f} lx vs published Eav "
                                        f"{row['published_Eav']:.2f} lx ({row['err_vs_published'] * 100:+.2f} %); ab {row['ab']} vs "
                                        f"{row['ab2']} differ {row['convergence_ab_vs_2ab'] * 100:+.2f} %"),
                               source_ids=("CIE171-2006-5.8-via-DAU",)))
    # UGR reference checks (published tables) and the open item
    e6 = max(abs(ugr.flux_correction(lm) - v) for lm, v in ugr.SLL_T12_6.items())
    out.append(CheckResult("LA4", "L6", "pass" if e6 <= 0.06 else "fail", "ref/UGR/SLL-T12.6-flux-correction",
                           achieved=e6, required=0.06, unit="UGR points",
                           message=f"8 log10(flux/1000) vs the {len(ugr.SLL_T12_6)} printed correction values: max difference {e6:.3f}",
                           source_ids=("SLL-T12.6-UGR-flux-correction",)))
    rows = ugr.position_index_vs_sll_table_12_10()
    em = max(abs(r["rel_err"]) for r in rows)
    out.append(CheckResult("LA4", "L6", "pass" if em <= 0.08 else "fail", "ref/UGR/SLL-T12.10-position-index",
                           achieved=em * 100, required=8.0, unit="% max K error",
                           message=(f"K = pi/(4 p^2 D^2) from our Guth index vs {len(rows)} printed K cells: max |error| "
                                    f"{em * 100:.1f} %, mean {sum(abs(r['rel_err']) for r in rows) / len(rows) * 100:.1f} % "
                                    "(K ~ p^-2, so p within about half of that)"),
                           source_ids=("SLL-T12.10-UGR-K",)))
    out.append(CheckResult("LA4", "L6", "not_evaluated", "ref/UGR/CIE190-worked-example",
                           message=("CIE 190:2010 worked example (2H x 4H, disymmetric luminaire) not accessible (paywalled) and no "
                                    "held page prints a luminaire's photometry together with its UGR table; no manufacturer UGR table "
                                    "with its LDT was obtained. The +/-1 acceptance of LA4 is therefore NOT demonstrated.")))
    return out


def dining_results() -> list[CheckResult]:
    d = json.loads(DIN.read_text(encoding="utf-8"))
    out = []
    for r in d["checks"]:
        r = dict(r)
        r["source_ids"] = tuple(r["source_ids"])
        r["element_ids"] = tuple(r["element_ids"])
        out.append(CheckResult(**r))
    return out


def main() -> int:
    res = reference_results() + dining_results()
    p = write_results("L6", res, root=ROOT / "out" / "checks")
    q = write_results("L6", res, root=ROOT / "knowledge" / "lighting" / "checks")
    print(p, q, len(res), "results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
