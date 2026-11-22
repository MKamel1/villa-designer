"""Landscape critics (method stage LD-C). Public API for LDG:

    critique(layout, vlm=False) -> list[Finding]   # criterion, severity, evidence, source, kind, calibrated flag
    plan_png(layout, path, view=None)              # the common plan renderer (fixed style, STYLE_VERSION)
    massing_png(layout, path, view=None)           # oblique clay bird's-eye (3D massing) through jobq
    verdict(findings) -> {critic: "fail"|"pass"}   # fail = any blocking/major finding with status fail

Critics work from the design artifact alone (layout + site layers + brief); no generator rationale is an input.
A finding's `calibrated` flag is read from knowledge/landscape/critic/calibration.json; only calibrated findings count.
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import Finding, KNOW
from .plan import plan_png, STYLE_VERSION
from .massing import massing_png

CRITICS = ("landscape-architect", "horticulturist", "user", "climate")


def _cal():
    f = KNOW / "critic/calibration.json"
    return json.loads(f.read_text())["criteria"] if f.exists() else {}


def critique(layout: dict, vlm: bool = False, vlm_host: str = "http://localhost:11434") -> list[Finding]:
    from . import computed as C
    out = C.architect(layout) + C.horticulturist(layout) + C.user(layout) + C.climate(layout)
    if vlm:
        from .vlm_plan import vlm_findings
        out += vlm_findings(layout, vlm_host)
    cal = _cal()
    for f in out:
        f.calibrated = bool(cal.get(f.criterion, {}).get("calibrated", False))
    return out


def verdict(findings) -> dict:
    v = {c: "pass" for c in CRITICS}
    for f in findings:
        if f.status == "fail" and f.severity in ("blocking", "major"): v[f.critic] = "fail"
    return v
