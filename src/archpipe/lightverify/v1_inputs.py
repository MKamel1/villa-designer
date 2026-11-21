"""V1 input integrity: does every bound luminaire emit what the design says it emits?

For each luminaire *type* in the design: integrate the candela table independently (`lightverify.ies`) and compare with
the lumens the engine actually uses (fixture record), the product record, the kind spec, and the file header.
For each *instance*: the flux the engine will emit (its scale x my integral of the file it loads) must equal the record.
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from . import ies
from .common import LayerResult, check
from .sources import ids

LUMEN_TOL = 0.02
WATT_TOL = 0.1
BEAM_TOL = 0.10
SRC = ids("LV-V1-LUMEN", "LV-V1-SPEC", "LV-LM63")


def _beam(d):
    b, _ = ies.beam_angles(d)
    return sum(b.values()) / len(b)


def _pct(a, b):
    return (a - b) / b if b else float("inf")


def kind_rows(v) -> list[dict]:
    """One row per fixture kind: all the numbers side by side, plus the problems found."""
    by_kind = defaultdict(list)
    for f in v.fixtures:
        by_kind[f.kind].append(f)
    place = defaultdict(list)
    by_id = {f.id: f for f in v.fixtures}
    for p in v.placements:
        place[by_id[p.meta.get("parent") or p.id].kind].append(p)
    rows = []
    for kind, fs in sorted(by_kind.items()):
        f0 = fs[0]
        rec = f0.record
        spec = dict(rec.definition.requirement)
        prod = dict(rec.product) if rec.product else None
        row = dict(kind=kind, n=len(fs), mount=spec.get("mount"), spec_lm=spec.get("lm"), spec_lm_per_m=spec.get("lm_per_m"),
                   spec_beam=spec.get("beam"), spec_cct=spec.get("cct"), product=None, problems=[], generic=prod is None)
        if prod:
            d = ies.parse(Path(prod["ies"]).read_text(encoding="utf-8", errors="replace"))
            integ = ies.lumens(d)
            row.update(product="%s/%s" % (prod["manufacturer"], prod["code"]), product_lm=prod["lm"], file_lamp_lm=d.lamp_lumens * d.lamps,
                       integrated_lm=integ, integ_vs_product_pct=100 * _pct(integ, prod["lm"]),
                       file_watts=d.input_watts, product_watts=prod.get("watts"), file_cct=d.text_cct, product_cct=prod.get("cct"),
                       computed_beam=_beam(d), product_beam=prod.get("beam"), ptype=d.ptype,
                       lor=integ / (d.lamp_lumens * d.lamps) if d.lamp_lumens > 0 else None)
            pr = row["problems"]
            if abs(_pct(integ, prod["lm"])) > LUMEN_TOL:
                pr.append("integrated %.1f lm vs product %.1f lm (%.1f %%)" % (integ, prod["lm"], 100 * _pct(integ, prod["lm"])))
            if spec.get("lm") is not None and abs(_pct(spec["lm"], prod["lm"])) > LUMEN_TOL:
                pr.append("spec %s lm vs product %.1f lm" % (spec["lm"], prod["lm"]))
            if d.input_watts and prod.get("watts") is not None and abs(d.input_watts - prod["watts"]) > WATT_TOL:
                pr.append("file %.2f W vs product %.2f W" % (d.input_watts, prod["watts"]))
            if d.text_cct is not None and spec.get("cct") and d.text_cct != spec["cct"]:
                pr.append("file CCT %s vs spec %s" % (d.text_cct, spec["cct"]))
            if prod.get("cct") is not None and spec.get("cct") and prod["cct"] != spec["cct"]:
                pr.append("product CCT %s vs spec %s" % (prod["cct"], spec["cct"]))
            if spec.get("beam") and abs(_pct(row["computed_beam"], spec["beam"])) > BEAM_TOL:
                pr.append("computed beam %.1f vs spec %s deg" % (row["computed_beam"], spec["beam"]))
            if prod.get("beam") and abs(_pct(row["computed_beam"], prod["beam"])) > BEAM_TOL:
                pr.append("computed beam %.1f vs product %s deg" % (row["computed_beam"], prod["beam"]))
            if d.ptype != 1:
                pr.append("photometric type %d" % d.ptype)
        else:
            # generic: integrate the text the engine builds for each placement and compare with the record's flux
            ps = [p for p in place[kind] if p.meta.get("ies_text")]
            by_parent = defaultdict(float)
            for p in ps:
                by_parent[p.meta.get("parent") or p.id] += ies.lumens(ies.parse(p.meta["ies_text"]), 0.5, 5)
            worst = 0.0
            for f in fs:
                want = f.record.flux_lm
                got = by_parent.get(f.id)
                if got is None:
                    row["problems"].append("%s: no generic photometry text" % f.id)
                    continue
                worst = max(worst, abs(_pct(got, want)))
            row.update(integrated_lm=sum(by_parent.values()) / max(1, len(fs)), record_lm=sum(f.record.flux_lm for f in fs) / len(fs),
                       integ_vs_product_pct=100 * worst, watts_note="assumed 90 lm/W")
            if worst > LUMEN_TOL:
                row["problems"].append("generic photometry integrates %.1f %% away from the record flux" % (100 * worst))
            if "lm" in spec and abs(_pct(fs[0].record.flux_lm, spec["lm"])) > LUMEN_TOL and fs[0].lm is None:
                row["problems"].append("record %.0f lm vs spec %s lm" % (fs[0].record.flux_lm, spec["lm"]))
        row["overrides"] = [(f.id, round(f.record.flux_lm, 1), f.record.definition.spec.get("lm", f.record.definition.spec.get("lm_per_m")),
                             f.extra.get("dimmer")) for f in fs if f.lm is not None or f.extra.get("dimmer") is not None]
        rows.append(row)
    return rows


def instance_problems(v) -> dict:
    """fixture id -> list of problems for product-bound instances: engine flux (its scale x my integral) vs record."""
    by_id = {f.id: f for f in v.fixtures}
    out = defaultdict(list)
    cache = {}
    for p in v.placements:
        f = by_id[p.meta.get("parent") or p.id]
        if p.meta.get("generic"):
            continue
        path = p.meta["ies_path"]
        if path not in cache:
            cache[path] = ies.lumens(ies.parse(Path(path).read_text(encoding="utf-8", errors="replace")), 0.5, 5)
        emitted = cache[path] * p.dim
        if abs(_pct(emitted, f.record.flux_lm)) > LUMEN_TOL:
            out[f.id].append("engine emits %.1f lm, record says %.1f lm" % (emitted, f.record.flux_lm))
    return out


def check_inputs(v) -> LayerResult:
    L = LayerResult("V1")
    rows = kind_rows(v)
    L.table = rows
    for r in rows:
        status = "fail" if r["problems"] else "pass"
        msg = ("%s: integrated %.1f lm, %s" % (r["kind"], r.get("integrated_lm", 0),
               "bound " + r["product"] + " %.1f lm" % r["product_lm"] if r["product"] else "generic (assumed, not a product)"))
        if r["problems"]:
            msg += "; " + "; ".join(r["problems"])
        L.results.append(check("LV1", status, "kind:" + r["kind"], SRC, achieved=round(r.get("integrated_lm", 0), 1),
                               required=r.get("product_lm") or r.get("record_lm"), unit="lm", message=msg))
    bad = instance_problems(v)
    for fid, pr in bad.items():
        L.results.append(check("LV1", "fail", fid, SRC, message="; ".join(pr)))
    bad_kinds = {r["kind"] for r in rows if r["problems"]}
    by_id = {f.id: f for f in v.fixtures}
    for f in v.fixtures:
        L.mark(f.room, "fail" if (f.kind in bad_kinds or f.id in bad) else "pass")
    # generic share of each room's lumens: reported, not failed
    share = defaultdict(lambda: [0.0, 0.0])
    for f in v.fixtures:
        share[f.room][0] += f.record.flux_lm
        if not f.record.product:
            share[f.room][1] += f.record.flux_lm
    L.notes.append({room: round(g / t, 3) if t else 0.0 for room, (t, g) in share.items()})
    return L
