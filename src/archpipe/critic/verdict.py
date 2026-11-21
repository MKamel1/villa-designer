"""Combine deterministic checks and VLM scores into a RenderVerdict and CheckResult records.

Rules (rubric.json 'scoring', policy): scores 0/1/2; a 0 on a gating criterion of a hero view is a
hard fail; two or more gating 1s escalate to FAIL; a criterion that did not run is not_evaluated,
and a missing VLM makes the verdict fail (fail closed), never pass.
"""
from __future__ import annotations

import json
from pathlib import Path

from archpipe import contracts

from . import meta as meta_mod
from . import pixels

LANE = "L3"
ROOT = Path(__file__).resolve().parents[3]
RUBRIC_PATH = ROOT / "knowledge" / "critic" / "rubric.json"

DETERMINISTIC = ("R1", "R2", "R3", "R4", "R10", "R12")
VLM_CRITERIA = ("R5", "R7", "R8", "R9", "R10", "R11", "R13")
ALWAYS_GATING = {"R1", "R2", "R3", "R4", "R10", "R12"}
SOURCE = {c: f"POLICY-{c}" for c in ("R1", "R2", "R3", "R4", "R10", "R12")}
SOURCE.update({c: "POLICY-VLM" for c in ("R5", "R7", "R8", "R9", "R11", "R13")})


def load_rubric(path: str | Path = RUBRIC_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def deterministic_scores(png: str | Path, view: dict | None = None, rgb=None) -> dict:
    """{criterion: {score, message, achieved}} from camera metadata and pixels."""
    view = view if view is not None else meta_mod.load_view(png)
    rgb = rgb if rgb is not None else pixels.load_rgb(png)
    out: dict = {}
    s, msg, ach = meta_mod.check_r1(view.get("camera"))
    out["R1"] = dict(score=s, message=msg, achieved=ach)
    s, msg, ach = meta_mod.check_r2(view.get("camera"))
    out["R2"] = dict(score=s, message=msg, achieved=ach)
    s, msg, ach = meta_mod.check_r3_meta(view.get("camera"), view.get("pitch_deg"))
    meta_r3 = dict(score=s, message=msg, achieved=ach)
    px_r3 = pixels.check_r3_pixels(rgb)
    scores = [x["score"] for x in (meta_r3, px_r3) if x["score"] is not None]
    out["R3"] = dict(score=min(scores) if scores else None,
                     message=f"{meta_r3['message']}; {px_r3['message']}",
                     achieved=max([x["achieved"] for x in (meta_r3, px_r3) if x["achieved"] is not None], default=None))
    r4 = pixels.check_r4(rgb, view.get("subjects"))
    out["R4"] = dict(score=r4["score"], message=r4["message"], achieved=r4["achieved"])
    r10 = pixels.check_r10_pixel(rgb)
    out["R10"] = dict(score=r10["score"], message=r10["message"], achieved=r10["achieved"], seams=r10["seams"][:3])
    r12 = pixels.check_r12(rgb)
    out["R12"] = dict(score=r12["score"], message=r12["message"], achieved=r12["achieved"])
    return out


def merge(det: dict, vlm: dict | None, rubric: dict) -> dict:
    """Merge into one {criterion: {score, source, message}}. R10 = min(pixel, VLM). Criteria that did
    not run carry score None."""
    merged: dict = {}
    for c, d in det.items():
        merged[c] = dict(d, source="pixels/metadata")
    if vlm is not None:
        for c, v in vlm.items():
            if c == "R10":
                parts = [x for x in (merged["R10"]["score"], v.get("score")) if x is not None]
                merged["R10"] = dict(merged["R10"], score=min(parts) if parts else None,
                                     message=merged["R10"]["message"] + " | VLM: " + str(v.get("evidence", "")),
                                     vlm=v.get("score"), source="pixels+vlm")
            else:
                merged[c] = dict(score=v.get("score"), message=str(v.get("evidence", v.get("error", ""))),
                                 source="vlm", per_order=v.get("per_order"))
    for c in VLM_CRITERIA:
        if c not in merged:
            merged[c] = dict(score=None, message="vlm not run", source="vlm")
    merged["R6"] = dict(score=None, message="texel density needs UV and camera scripts; out of scope for the image critic",
                        source="out_of_scope")
    return merged


def decide(merged: dict, gating: set[str] | None = None, hero: bool = True, vlm_ok: bool = True) -> tuple[str, dict]:
    """Return (verdict, notes). `gating` = criteria that count (default: deterministic + all VLM)."""
    gating = set(gating) if gating is not None else set(ALWAYS_GATING) | set(VLM_CRITERIA)
    zeros = sorted(c for c in gating if merged.get(c, {}).get("score") == 0)
    warns = sorted(c for c in gating if merged.get(c, {}).get("score") == 1)
    missing = sorted(c for c in gating if merged.get(c, {}).get("score") is None)
    reasons = []
    if hero and zeros:
        reasons.append(f"score 0 on {', '.join(zeros)} (hero view)")
    if len(warns) >= 2:
        reasons.append(f"{len(warns)} WARNs ({', '.join(warns)}) escalate to FAIL")
    if not vlm_ok:
        reasons.append("VLM unavailable: fail closed")
    elif missing:
        reasons.append(f"not evaluated: {', '.join(missing)} (fail closed)")
    verdict = "fail" if reasons else "pass"
    return verdict, dict(zeros=zeros, warns=warns, not_evaluated=missing, reasons=reasons,
                         gating=sorted(gating), hero=hero)


def build_verdict(view_id: str, image: str, view: dict, merged: dict, verdict: str, notes: dict) -> contracts.RenderVerdict:
    cam = view.get("camera") or {}
    return contracts.RenderVerdict(
        view_id=view_id, image=str(image), lens_mm=cam.get("lens_mm"),
        camera_height_m=merged.get("R2", {}).get("achieved"),
        scores={c: v["score"] for c, v in sorted(merged.items(), key=lambda kv: int(kv[0][1:]))},
        verdict=verdict,
        notes=dict(notes, messages={c: v.get("message", "") for c, v in merged.items()}))


def check_results(view_id: str, merged: dict, gating: set[str]) -> list[contracts.CheckResult]:
    """One CheckResult per criterion. score 2 -> pass, 1 -> warn, 0 -> fail, None -> not_evaluated."""
    out = []
    for c, v in sorted(merged.items(), key=lambda kv: int(kv[0][1:])):
        s = v.get("score")
        status = {2: "pass", 1: "warn", 0: "fail"}.get(s, "not_evaluated")
        if status == "fail" and c not in gating:
            status = "warn"                      # non-gating criteria never fail the view
        out.append(contracts.CheckResult(
            criterion=c, lane=LANE, status=status, subject=view_id,
            achieved=float(s) if s is not None else None, required=2.0, unit="score 0-2",
            message=f"{v.get('source')}: {v.get('message', '')}"[:600],
            source_ids=(SOURCE.get(c, "POLICY-VLM"),) if status in ("pass", "fail") else (SOURCE.get(c, "POLICY-VLM"),),
            gate=False))
    return out
