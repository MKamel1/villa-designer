"""L6c substitution loop: does a supplier's proposed luminaire do the job of a type in the villa lighting design?

    python -m archpipe.luminaires.substitute --tag DL --ies proposed.ies --datasheet proposed.pdf|points.json [--radiance]

(a) V1 / V10 on the proposed product (integrated lumens vs its stated lumens; every published point reproduced within 5 %);
(b) the proposal against the type's performance spec (`schedule.TYPE_SPEC`): lumens, beam, CCT, CRI, IP, dimming, size, glare;
(c) the affected rooms re-run with the proposal at the type's positions and aims: fast analytic first (direct light recomputed,
    inter-reflected light scaled by flux, on the frozen Radiance per-zone results of the design), Radiance with --radiance;
(d) ACCEPT / ACCEPT WITH DIMMING CHANGE / REJECT with every reason printed. Exit status: 0 accept, 3 accept with change, 1 reject.

A figure the supplier does not give is "missing", and a missing mandatory figure rejects (resubmit with it): nothing is assumed.
Datasheet input: a points.json (below) or a PDF (text layer; lumens, CCT, CRI, IP, Imax, dimming words are read and quoted).
    {"maker": "...", "code": "...", "name": "...", "url": "...",
     "claims": {"lumens": 1065, "watts": 14.4, "cct_k": 2700, "cri": 92, "r9": 60, "ip": "IP20", "dimming": "DALI-2",
                "flicker": "SVM<=0.4", "cutoff_deg": 40, "cutout_mm": 70, "finish": "white"},
     "points": [{"kind": "imax", "published": 1147, "source": "datasheet p1"}, {"kind": "lux_axis", "distance_m": 2, "published": 287}]}
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import schedule as SCH
from . import v10 as V10
from . import eulumdat

ROOT = Path(__file__).resolve().parents[3]
FROZEN = Path(os.environ.get("ARCHPIPE_L6C_RES") or ROOT / "knowledge/lighting/radiance-l6c")
ACCEPT, CHANGE, REJECT = "ACCEPT", "ACCEPT WITH DIMMING CHANGE", "REJECT"
CARD_BAND = 0.10          # average-gauged task cards: within +/-10 % (LA1) and <= 1.5x (LA2)
MIN_DRIVER = 0.05         # below this a zone is dimmed to the floor: reported as a reason to prefer a smaller product


# ------------------------------------------------------------------ inputs
def load_candidate(path: Path) -> tuple[str, dict]:
    """IES text (LDT converted) and what the file itself says about the product."""
    path = Path(path)
    if path.suffix.lower() == ".ldt":
        ld = eulumdat.load(path)
        return ld.to_ies_text(), dict(format="ldt", cct_k=ld.cct_k, cri=ld.cri_ra, lumens_header=ld.luminaire_flux(0))
    raw = path.read_bytes().decode("latin-1").lstrip("﻿")
    text = V10_text(raw)
    m = re.search(r"^TILT=NONE\s*\n\s*(\S+)\s+(\S+)\s+(\S+)", text, re.M)
    n, lm, mult = (float(m.group(i)) for i in (1, 2, 3)) if m else (1, -1, 1)
    return text, dict(format="ies", lumens_header=n * lm if lm > 0 else None, cct_k=None, cri=None)


def V10_text(raw: str) -> str:
    from ..lightcalc.radjob import radiance_safe_ies
    return radiance_safe_ies(raw)


_PDF_PATTERNS = {
    "lumens": r"(?:luminous flux(?: of the luminaire)?|luminaire flux|lumen output)\s*[:=]?\s*(\d[\d ,.]*)\s*lm",
    "cct_k": r"\b(2[0-9]{3}|3[0-9]{3})\s*K\b", "cri": r"\b(?:CRI|Ra)\s*[:=]?\s*(\d{2,3})\b", "ip": r"\b(IP\s?\d{2})\b",
    "imax": r"Imax\s*=?\s*(\d[\d.]*)\s*cd", "dimming": r"(DALI(?:-2)?|0-10\s?V|1-10\s?V|phase[- ]cut|triac|push[- ]?button|on-board dim)",
}


def read_datasheet(path: Path | None) -> dict:
    """Claims and published points from the supplier's datasheet (see module docstring)."""
    if path is None:
        return dict(claims={}, points=[], source="none")
    path = Path(path)
    if path.suffix.lower() == ".json":
        d = json.loads(path.read_text(encoding="utf-8"))
        return dict(maker=d.get("maker"), code=d.get("code"), name=d.get("name"), url=d.get("url"),
                    claims=d.get("claims", {}), points=d.get("points", []), source=str(path))
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout
    claims, points = {}, []
    for k, pat in _PDF_PATTERNS.items():
        m = re.search(pat, text, re.I)
        if not m:
            continue
        v = m.group(1)
        if k == "lumens":
            claims[k] = float(re.sub(r"[ ,]", "", v))
        elif k in ("cct_k", "cri"):
            claims[k] = float(v)
        elif k == "imax":
            points.append(dict(kind="imax", published=float(v), source="datasheet text 'Imax=%s cd'" % v))
        else:
            claims[k] = v.replace(" ", "")
    if "lumens" in claims:
        points.append(dict(kind="lumens", published=claims["lumens"], source="datasheet text"))
    return dict(claims=claims, points=points, source=str(path) + " (pdf text layer; verify the quoted values by eye)")


# ------------------------------------------------------------------ (a) V1 / V10
def check_inputs(ies_text: str, ds: dict, fmeta: dict) -> tuple[list[dict], dict]:
    rows = []
    claims = ds["claims"]
    stated = claims.get("lumens") or fmeta.get("lumens_header")
    src = "datasheet" if claims.get("lumens") else "file header"
    if not stated:
        rows.append(dict(id="V1", status="fail", reason="no lumen figure in the datasheet or the file header"))
        facts = {}
    else:
        r = V10.check_lumens(ies_text, float(stated))
        rows.append(dict(id="V1", status=r["status"], reason="integrated %.0f / %.0f lm (two routes) vs %s %.0f lm: %.1f %% (bar 2 %%)"
                                                             % (r["independent"], r["archpipe"], src, stated, 100 * r["worst_error"])))
        facts = dict(lumens=r["independent"])
    if claims.get("lumens") and fmeta.get("lumens_header") and abs(claims["lumens"] - fmeta["lumens_header"]) / claims["lumens"] > 0.05 \
            and fmeta["format"] == "ldt":
        rows.append(dict(id="V1", status="fail", reason="datasheet %.0f lm vs file header %.0f lm differ by more than 5 %%"
                                                        % (claims["lumens"], fmeta["lumens_header"])))
    pts = [V10.Point(p["kind"], float(p["published"]), p.get("distance_m"), p.get("source", "supplier datasheet"))
           for p in ds["points"] if p["kind"] != "lumens"]
    ph = V10.ph.parse(ies_text)
    res = [V10.reproduce(pt, ies_text, ph) for pt in pts]
    for r in res:
        rows.append(dict(id="V10", status=r["status"], reason="%s%s published %.4g vs file %.4g / %.4g (worst %.1f %%, bar 5 %%)"
                         % (r["kind"], "" if r["distance_m"] is None else " @%gm" % r["distance_m"], r["published"], r["engine"],
                            r["independent"], 100 * r["worst_error"])))
    if not res:
        rows.append(dict(id="V10", status="not_evaluated", reason="no published non-lumen point supplied (Imax, lux at a distance, "
                         "beam angle/diameter): the file's lumens are checked, its distribution is NOT checked against the maker's data"))
    t = V10.read_ies(ies_text)
    facts.update(beam=round(V10.beam_full_angle_independent(t), 1), imax=round(max(max(r) for r in t.cd), 1), watts=_watts(ies_text))
    return rows, facts


def _watts(text: str):
    m = re.search(r"^TILT=NONE\s*\n\s*(?:\S+\s+){10}\S+\s+\S+\s+(\S+)", text, re.M)
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


# ------------------------------------------------------------------ (b) performance spec
def _ip_num(s):
    m = re.search(r"IP\s?(\d{2})", str(s or ""), re.I)
    return int(m.group(1)) if m else None


def check_spec(tag: str, ds: dict, facts: dict, fmeta: dict, ref_lm: float) -> list[dict]:
    spec = SCH.spec_for_tag(tag)
    c = ds["claims"]
    rows = []

    def add(item, status, reason):
        rows.append(dict(id="SPEC:" + item, status=status, reason=reason))

    lm = facts.get("lumens")
    if lm:
        lo, hi = ref_lm * (1 - SCH.LM_BAND), ref_lm * (1 + SCH.LM_BAND)
        add("lumens", "pass" if lo <= lm <= hi else "note",
            "%.0f lm vs reference %.0f lm (+/-%d %% = %.0f-%.0f)%s" % (lm, ref_lm, 100 * SCH.LM_BAND, lo, hi,
                                                                       "" if lo <= lm <= hi else ": outside the band, the room re-run decides"))
    want_beam = spec["beam"][0]
    if want_beam and facts.get("beam") is not None:
        tol = max(SCH.BEAM_TOL * want_beam, 2.0)
        ok = abs(facts["beam"] - want_beam) <= tol
        add("beam", "pass" if ok else "fail", "beam %.1f deg (file, 50 %% angle) vs %g +/-%.1f deg" % (facts["beam"], want_beam, tol))
    elif facts.get("beam") is not None:
        add("beam", "note", "spec has no single beam angle (%s); file beam %.1f deg: the room re-run decides" % (spec["beam"][1], facts["beam"]))
    cct = c.get("cct_k") or fmeta.get("cct_k")
    if cct is None:
        add("cct", "missing", "CCT not stated (need %d K +/- %d K)" % (spec["cct"], SCH.CCT_TOL_K))
    else:
        add("cct", "pass" if abs(float(cct) - spec["cct"]) <= SCH.CCT_TOL_K else "fail", "%d K vs %d K +/- %d K" % (cct, spec["cct"], SCH.CCT_TOL_K))
    cri = c.get("cri") or fmeta.get("cri")
    if cri is None:
        add("cri", "missing", "CRI not stated (need >= %d)" % SCH.CRI_MIN)
    else:
        add("cri", "pass" if float(cri) >= SCH.CRI_MIN else "fail", "CRI %g vs >= %d" % (cri, SCH.CRI_MIN))
    if c.get("r9") is None:
        add("r9", "note", "R9 not stated (we ask R9 >= %d where the maker gives it)" % SCH.R9_MIN)
    else:
        add("r9", "pass" if float(c["r9"]) >= SCH.R9_MIN else "fail", "R9 %g vs >= %d" % (c["r9"], SCH.R9_MIN))
    need_ip = _ip_num(spec["ip"])
    got_ip = _ip_num(c.get("ip"))
    if need_ip and need_ip > 20:
        add("ip", "missing" if got_ip is None else ("pass" if got_ip >= need_ip else "fail"),
            "%s vs >= IP%d" % (c.get("ip") or "not stated", need_ip))
    dim = str(c.get("dimming") or "")
    want = spec["dimming"].lower()
    ok_tokens = [t for t in ("dali", "on-board", "push", "0-10", "switched") if t in want]
    if not dim:
        add("dimming", "missing", "dimming protocol not stated (need: %s)" % spec["dimming"])
    elif "phase" in dim.lower() or "triac" in dim.lower():
        add("dimming", "fail", "phase-cut dimming offered; the design's controls are DALI-2/on-board (%s)" % spec["dimming"])
    else:
        add("dimming", "pass" if any(t in dim.lower() for t in ok_tokens) else "fail", "%s vs %s" % (dim, spec["dimming"]))
    if spec["mount"].startswith("recessed") and c.get("cutout_mm") is None:
        add("cutout", "missing", "cut-out size not stated (state it so the ceiling drawing can be checked)")
    if c.get("flicker"):
        add("flicker", "note", "flicker stated: %s (we ask %s)" % (c["flicker"], SCH.FLICKER))
    else:
        add("flicker", "note", "flicker not stated (we ask %s)" % SCH.FLICKER)
    return rows


# ------------------------------------------------------------------ (c) the rooms
def _patched_villa(tag_kind: str, ies_path: Path, rated_lm: float, watts, cct, drivers_path: Path | None):
    """A Villa whose `tag_kind` is bound to the proposal (PRODUCTS patched before design() so drivers become dimmers)."""
    from .. import fixture_record as FR
    from ..concept import villa_lighting as VL
    from ..lightcalc.villa import Villa
    FR.bind_products()
    saved = copy.deepcopy(FR.PRODUCTS.get(tag_kind))
    if ies_path is not None:
        FR.PRODUCTS[tag_kind] = dict(manufacturer="proposed", code="proposed", ies=str(ies_path), lm=float(rated_lm), watts=watts,
                                     cct=float(cct or 2700), beam=None, what="proposed substitute", substitute=True)
    old_env = os.environ.get("ARCHPIPE_ZONE_DRIVERS")
    if drivers_path:
        os.environ["ARCHPIPE_ZONE_DRIVERS"] = str(drivers_path)
    try:
        return Villa()
    finally:
        if old_env is None:
            os.environ.pop("ARCHPIPE_ZONE_DRIVERS", None)
        else:
            os.environ["ARCHPIPE_ZONE_DRIVERS"] = old_env
        if ies_path is not None:
            if saved is None:
                FR.PRODUCTS.pop(tag_kind, None)
            else:
                FR.PRODUCTS[tag_kind] = saved


def _flux(p) -> float:
    return p.dim * p.photometry.integrated_flux()


def analytic_rerun(kind: str, tag: str, ies_path: Path, rated_lm: float, watts, cct, frozen: Path = FROZEN) -> dict:
    """Fast estimate on the frozen per-zone Radiance results: direct light of the affected fittings recomputed analytically
    (inverse square, same sensors), their inter-reflected light scaled by the flux ratio, everything else untouched."""
    from ..concept.villa_lighting import SCENES, zone_id
    from ..lightcalc import villa_report as VR, villa_tune as VT
    from ..lightcalc.direct import direct_illuminance
    from ..lightcalc.villa import CLUSTERS, cluster_of, fixture_placements

    old_v = _patched_villa(kind, None, 0, None, None, None)
    new_v = _patched_villa(kind, ies_path, rated_lm, watts, cct, None)
    planes = old_v.planes()
    clusters = sorted({cluster_of(f.room) for f in old_v.fixtures if f.kind == kind})
    if not clusters:
        return dict(status="unused", clusters=[], rows=[], message="type %s has no fitting in the design" % tag)
    old_res, new_res = {}, {}
    ids = {f.id for f in old_v.fixtures if f.kind == kind and tag_matches(tag, f, old_v)}
    for cl in clusters:
        path = frozen / (cl + ".json")
        if not path.exists():
            raise FileNotFoundError("frozen Radiance results for %s not found at %s (run villa_run, or set ARCHPIPE_L6C_RES)" % (cl, path))
        res = VR.ClusterRes.load(path)
        calc = old_v.calc(cl, planes, fast=True)
        sensors = calc.sensors()
        pts = [(s.x, s.y, s.z) for s in sensors]
        new_by_id = {f.id: f for f in new_v.fixtures}
        zones = copy.deepcopy(res.zones)
        for z in {zone_id(f) for f in old_v.fixtures if f.id in ids and cluster_of(f.room) == cl}:
            mine = [f for f in old_v.fixtures if f.id in ids and zone_id(f) == z]
            zone_old = [p for f in old_v.fixtures if zone_id(f) == z for p in fixture_placements(f)]
            old_p = [p for f in mine for p in fixture_placements(f)]
            new_p = [p for f in mine for p in fixture_placements(new_by_id[f.id])]
            phi_zone, phi_old, phi_new = sum(map(_flux, zone_old)), sum(map(_flux, old_p)), sum(map(_flux, new_p))
            ab = str(res.ab)
            tot, d0 = zones[z][ab], zones[z]["0"]
            for key in zones[z]:
                arr = zones[z][key]
                zones[z][key] = [t + (direct_illuminance(new_p, q) - direct_illuminance(old_p, q)) * (1 if key == "0" else 1)
                                 + ((tot[i] - d0[i]) * (phi_old / phi_zone) * (phi_new / phi_old - 1) if key != "0" and phi_old > 0 else 0.0)
                                 for i, (t, q) in enumerate(zip(arr, pts))]
        old_res[cl] = res
        new_res[cl] = VR.ClusterRes(res.name, res.mf, res.slices, zones, res.zone_watts, res.zone_layer, res.ab, res.ab2)
    return dict(status="ok", clusters=clusters, old=old_res, new=new_res, planes=planes, fixtures=old_v.fixtures, ids=ids,
                scenes=SCENES, tunable=lambda r: {z for z, lay in r.zone_layer.items()
                                                   if lay == "task" or z.endswith(("-ISLAND-PENDANTS", "-TABLE-PENDANT"))})


def tag_matches(tag: str, f, v) -> bool:
    """A fitting belongs to a type tag: the kind, and for a split kind (PEN-GLOBE-A) the same rated-lumen group."""
    from . import schedule
    kind = tag if tag in schedule.TYPE_SPEC else tag.rsplit("-", 1)[0]
    if f.kind != kind:
        return False
    if tag == kind:
        return True
    row = next((r for r in schedule.build_schedule(v.fixtures) if r["tag"] == tag), None)
    return bool(row) and VL_zone(f) in row["zones"]


def VL_zone(f):
    from ..concept.villa_lighting import zone_id
    return zone_id(f)


def judge_rooms(rr: dict) -> tuple[list[dict], dict, dict]:
    """Rows (per task plane, base vs proposal at the same drivers vs proposal re-driven), the new driver table and V12."""
    from ..lightcalc import villa_report as VR, villa_tune as VT
    from ..lightcalc.villa import cluster_of
    from ..concept.villa_lighting import _drivers, zone_id
    drivers = _drivers()
    rows, reasons = [], {}
    planes = rr["planes"]
    new_drv = {}
    tunable = set()
    for cl in rr["clusters"]:
        tunable |= rr["tunable"](rr["old"][cl])
    mine = {zone_id(f) for f in rr["fixtures"] if f.id in rr["ids"]}
    solve_set = tunable & mine
    res_new = rr["new"]
    d_abs, _rows = VT.solve(res_new, [p for p in planes if cluster_of(p.room) in rr["clusters"]], rr["scenes"], solve_set,
                            applied=drivers) if solve_set else ({}, [])
    # solve() returns ABSOLUTE drivers for the zones it moved; a zone not reached keeps its driver
    for z in solve_set:
        new_drv[z] = d_abs.get(z, drivers.get(z, 1.0))
    for cl in rr["clusters"]:
        ps = [p for p in planes if cluster_of(p.room) == cl]
        base = {r["plane"]: r for r in VR.plane_rows(rr["old"][cl], ps, rr["scenes"].get(cl, {}))}
        same = {r["plane"]: r for r in VR.plane_rows(rr["new"][cl], ps, rr["scenes"].get(cl, {}))}
        # re-driven: scale the affected zones' contribution by new/old driver via level scaling
        for p in ps:
            b, s = base[p.id], same[p.id]
            lev = VR.scene_levels(rr["new"][cl], rr["scenes"].get(cl, {}), p.scene) if p.scene in rr["scenes"].get(cl, {}) else VR.full_levels(rr["new"][cl])
            adj = {z: L * (new_drv[z] / max(drivers.get(z, 1.0), 1e-9) if z in new_drv else 1.0) for z, L in lev.items()}
            em2 = rr["new"][cl].stats(p.id, adj).em
            rows.append(dict(plane=p.id, room=p.room, scene=p.scene, gauge=p.gauge, target=p.target, base=b["em"], same=s["em"], redriven=em2))
    return rows, new_drv, drivers


def _ok(row, key):
    t, e = row["target"], row[key]
    return e >= t * (1 - CARD_BAND) if row["gauge"] == "minimum" else (1 - CARD_BAND) * t <= e <= (1 + CARD_BAND) * t and e <= 1.5 * t


def _worse(row, key) -> bool:
    """The proposal breaks a card the design met, or moves a card the design already missed further from its target."""
    if _ok(row, key):
        return False
    return _ok(row, "base") or abs(row[key] / row["target"] - 1) > abs(row["base"] / row["target"] - 1) + 0.02


# ------------------------------------------------------------------ driver
def run(tag: str, ies: Path, datasheet: Path | None, radiance: bool = False, out: Path | None = None, frozen: Path = FROZEN) -> dict:
    kind = tag if tag in SCH.TYPE_SPEC else tag.rsplit("-", 1)[0]
    spec = SCH.spec_for_tag(tag)
    ies_text, fmeta = load_candidate(ies)
    ds = read_datasheet(datasheet)
    work = Path(out or tempfile.mkdtemp(prefix="substitute-"))
    work.mkdir(parents=True, exist_ok=True)
    ies_file = work / "proposed.ies"
    ies_file.write_text(ies_text, encoding="utf-8")
    report = dict(tag=tag, proposed=dict(maker=ds.get("maker"), code=ds.get("code"), name=ds.get("name"), file=str(ies), datasheet=ds["source"]),
                  reference=spec["ref"][:1], checks=[], rooms=[], reasons=[])
    rows, facts = check_inputs(ies_text, ds, fmeta)
    ref_lm = _ref_lm(kind)
    rows += check_spec(tag, ds, facts, fmeta, ref_lm)
    report["checks"] = rows
    hard = [r for r in rows if r["status"] in ("fail", "missing")]
    rated = facts.get("lumens") or ds["claims"].get("lumens")
    watts = ds["claims"].get("watts") or facts.get("watts")
    cct = ds["claims"].get("cct_k") or fmeta.get("cct_k") or spec["cct"]
    verdict = REJECT
    if rated:
        rr = analytic_rerun(kind, tag, ies_file, rated, watts, cct, frozen)
        report["clusters"] = rr["clusters"]
        if rr["status"] == "ok":
            prow, new_drv, old_drv = judge_rooms(rr)
            report["rooms"] = prow
            report["drivers"] = {z: dict(old=old_drv.get(z), new=round(v, 3)) for z, v in new_drv.items()}
            over = {z: v for z, v in new_drv.items() if v > SCH.HEADROOM + 1e-9}
            floor = {z: v for z, v in new_drv.items() if v < MIN_DRIVER}
            bad_same = [r for r in prow if _worse(r, "same")]
            new_bad_planes = [r for r in prow if _worse(r, "redriven")]
            if hard:
                pass
            elif not bad_same:
                verdict = ACCEPT
            elif not new_bad_planes and not over and not floor:
                verdict = CHANGE
            for r in new_bad_planes:
                report["reasons"].append("plane %s (%s): %.0f lx vs card %g, even with its zones re-driven" % (r["plane"], r["scene"], r["redriven"], r["target"]))
            for z, v in over.items():
                report["reasons"].append("zone %s would need %.2f of maximum output (V12 limit %.2f): not enough lumens" % (z, v, SCH.HEADROOM))
            for z, v in floor.items():
                report["reasons"].append("zone %s would be dimmed to %.2f of output (< %.2f): the product is oversized" % (z, v, MIN_DRIVER))
    else:
        report["reasons"].append("no lumen figure: cannot size the zones")
    for r in hard:
        report["reasons"].append("%s: %s" % (r["id"], r["reason"]))
    if verdict == REJECT and not report["reasons"]:
        report["reasons"].append("see failed checks")
    report["verdict"] = verdict
    report["radiance"] = None
    if radiance and verdict != REJECT:
        report["radiance"] = radiance_final(kind, ies_file, rated, watts, cct, report.get("drivers", {}), work, report["clusters"])
    (work / "substitute-report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    return report


def _ref_lm(kind: str) -> float:
    from .. import fixture_record as FR
    p = FR.bind_products().get(kind)
    return float(p["lm"]) if p else float(FR.KINDS[kind].get("lm") or FR.KINDS[kind].get("lm_per_m"))


def radiance_final(kind, ies_file, rated, watts, cct, drivers, work, clusters) -> dict:
    """Full Radiance run of the affected clusters with the proposal and the re-solved drivers (ab 12, minutes per cluster)."""
    from ..lightcalc import villa_run, villa_report as VR
    from ..lightcalc.villa import cluster_of
    from ..concept.villa_lighting import SCENES, _drivers
    table = dict(_drivers())
    table.update({z: d["new"] for z, d in drivers.items()})
    tpath = work / "zone-drivers.json"
    tpath.write_text(json.dumps(table), encoding="utf-8")
    v = _patched_villa(kind, ies_file, rated, watts, cct, tpath)
    os.environ.setdefault("ARCHPIPE_L6_LOCAL", "1")
    villa_run.run_all(v, "substitute", work / "radiance", only=clusters, fast=True)
    planes = v.planes()
    rows = []
    for cl in clusters:
        res = VR.ClusterRes.load(work / "radiance" / "substitute" / (cl + ".json"))
        rows += VR.plane_rows(res, [p for p in planes if cluster_of(p.room) == cl], SCENES.get(cl, {}))
    return dict(rows=[dict(plane=r["plane"], scene=r["scene"], target=r["target"], em=round(r["em"], 1), gauge=r["gauge"]) for r in rows])


def render(rep: dict) -> str:
    L = ["SUBSTITUTION CHECK  type %s  proposed: %s %s" % (rep["tag"], rep["proposed"].get("maker") or "?", rep["proposed"].get("code") or "?"),
         "reference: %s" % ("; ".join("%s %s" % (r["maker"], r["code"]) for r in rep["reference"]) or "none (performance spec only)"), ""]
    L.append("(a) inputs and (b) performance spec")
    for r in rep["checks"]:
        L.append("  [%-13s] %-13s %s" % (r["status"], r["id"], r["reason"]))
    if rep["rooms"]:
        L += ["", "(c) rooms re-run (fast analytic on the frozen Radiance zones; clusters: %s)" % ", ".join(rep["clusters"]),
              "  %-22s %-8s %7s %9s %9s %9s" % ("plane", "scene", "card", "design", "proposal", "re-driven")]
        for r in rep["rooms"]:
            L.append("  %-22s %-8s %7g %9.0f %9.0f %9.0f%s" % (r["plane"], r["scene"], r["target"], r["base"], r["same"], r["redriven"],
                                                               " (min)" if r["gauge"] == "minimum" else ""))
        for z, d in rep.get("drivers", {}).items():
            if d["old"] is None or abs(d["new"] - d["old"]) > 0.005:
                L.append("  driver %-40s %s -> %.2f" % (z, "%.2f" % d["old"] if d["old"] is not None else "full", d["new"]))
    if rep.get("radiance"):
        L += ["", "(c') Radiance (ab 12): " + ", ".join("%s %.0f/%g" % (r["plane"], r["em"], r["target"]) for r in rep["radiance"]["rows"]
                                                       if r["gauge"] == "average")]
    L += ["", "VERDICT: %s" % rep["verdict"]] + ["  - " + r for r in rep["reasons"]]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tag", required=True, help="type tag from the schedule, e.g. DL, ADJ, PEN-GLOBE-A")
    ap.add_argument("--ies", required=True, help="the proposed product's IES or LDT file")
    ap.add_argument("--datasheet", help="datasheet PDF or a points.json (see the module docstring)")
    ap.add_argument("--radiance", action="store_true", help="also run Radiance on the affected rooms (final check; minutes)")
    ap.add_argument("--out", help="working directory for the report (default: a temp dir)")
    a = ap.parse_args(argv)
    rep = run(a.tag, Path(a.ies), Path(a.datasheet) if a.datasheet else None, a.radiance, Path(a.out) if a.out else None)
    print(render(rep))
    return {ACCEPT: 0, CHANGE: 3}.get(rep["verdict"], 1)


if __name__ == "__main__":
    sys.exit(main())
