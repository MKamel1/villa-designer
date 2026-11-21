"""The D1 scene's post-construction passes as data (phase 2 of lane L2).

`villa_render._build` used to call ~14 patch passes inline, in a fixed order, each mutating the scene. The order,
inputs, knowledge files and purpose of each pass are now one record in PASSES; `villa_render` runs the stages through
`run_stage`. The calls, their order and their arguments are exactly the previous inline code, so the scene output is
byte-identical. A pass is retired by deleting its record once its effect is in the model data (see docs/lanes/L2-model.md).

Argument tokens (resolved at call time, inside the pass's own context manager):
    scene, lay, sp, finish                         the build's values
    lighting                                       villa_lighting.design(lay)  (re-derived per call, as before)
    furniture                                      the layout items (list)
    clear_rects                                    {room: villa_furnish.clear_rect(lay, room)}
    approvals:<file>                               knowledge/<file> as an explicit authority path
"""
from __future__ import annotations

import importlib
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Pass:
    id: str
    stage: str
    call: str                      # "<module relative to archpipe>:<function>"
    args: tuple = ("scene", "lay")
    input_revision: bool | None = None     # run inside sanitary_relocation.input_revision(<value>)
    returns_scene: bool = False
    knowledge: tuple = ()          # knowledge/ files the pass reads (row-level authority)
    changes: str = ""


PASSES: tuple[Pass, ...] = (
    # ---- stage "mounting": C4 fixture mounting, lead approvals, exterior and sanitary corrections
    Pass("c4-fitting-migrate", "mounting", "concept.fitting_mounting:migrate", ("scene", "lay", "sp", "finish"),
         changes="bind fittings to measured wall/ceiling hosts; bounded (<=5 mm) moves; proposals recorded as movements"),
    Pass("c4-bc-approvals", "mounting", "concept.mounting_resume:apply_approvals", ("scene",),
         knowledge=("c4-bc-approvals.json",), changes="apply the lead-approved proposed faces of package b/c rows"),
    Pass("c4-guest-fixes", "mounting", "concept.mounting_resume:guest_fixes", ("scene", "sp"),
         changes="guest WC handset, hose and sconce corrections"),
    Pass("c4-vanity-emitters", "mounting", "fixture_record:reconcile_vanity_emitters", ("scene", "lighting"),
         input_revision=False, changes="current lighting records replace the historical C4 vanity pair placements"),
    Pass("c4-ceiling-migrate", "mounting", "concept.ceiling_mounting:migrate", ("scene", "lay"),
         knowledge=("finish-build-ups.json",), changes="package d: finite finished ceilings and construction-void targets"),
    Pass("c4-d-lead-approvals", "mounting", "concept.mounting_resume:apply_approvals",
         ("scene", "approvals:c4-d-lead-approvals.json"), knowledge=("c4-d-lead-approvals.json",),
         changes="apply the lead-approved package d rows"),
    Pass("garden-g6-mount", "mounting", "concept.garden_g6:mount", ("scene", "lay"),
         knowledge=("garden-palette.json",), changes="G6 south garden construction mounted on measured supports"),
    Pass("c4-support-migrate", "mounting", "concept.support_mounting:migrate", ("scene", "lay"),
         changes="package e: support datums and rigid generated assemblies"),
    Pass("c4-e-lead-review", "mounting", "concept.exterior_mounting:apply_lead_review", ("scene",),
         knowledge=("c4-e-lead-approvals.json",), changes="exterior supports, lead-reviewed rows (<=300 mm search)"),
    Pass("c4-final-mounting", "mounting", "concept.final_mounting:apply", ("scene", "lay"),
         knowledge=("c4-final-approvals.json",), changes="final lead-authorised C4 candidate corrections"),
    Pass("wc-slides", "mounting", "concept.wc_slides:apply", ("scene", "lay"),
         changes="bounded same-wall WC slides; fronts, sides, doors re-reviewed"),
    Pass("sanitary-family", "mounting", "concept.sanitary_relocation:apply_family", ("scene", "lay"),
         changes="client 2026-10-05 sanitary family relocation (rigid moves between finished hosts)"),
    Pass("vanity-decision", "mounting", "concept.villa_render:apply_vanity_decision", ("scene", "lighting"),
         input_revision=False, changes="client's current vanity decision replaces the retired fittings"),
    # ---- stage "assembly": finishes, shell completion and late garden assemblies
    Pass("finish-layers", "assembly", "concept.finish_layers:build", ("scene", "clear_rects"),
         knowledge=("finish-build-ups.json",), changes="skirting, floor and wall finish layers per room"),
    Pass("complete-shell", "assembly", "concept.construction_solids:complete_shell", ("scene",),
         changes="close the construction shell solids"),
    Pass("garden-swing", "assembly", "concept.garden_swing:mount", ("scene", "lay"),
         changes="balcony-suspended swing"),
    Pass("garden-g4d", "assembly", "concept.garden_g4d:integrate", ("scene",),
         changes="north-court finishes and shielded evening uplights"),
    # ---- stage "furniture": measured furniture and bed replacements (return the scene)
    Pass("furniture-stage2", "furniture", "concept.furniture_stage2:apply", ("scene", "lay", "sp", "furniture"),
         returns_scene=True, knowledge=("furniture-stage2.json.gz",),
         changes="activate measured, previewed furniture replacements against the frozen room evidence"),
    Pass("parents-bed", "furniture", "concept.parents_bed:apply", ("scene", "lay", "sp", "furniture"),
         returns_scene=True, knowledge=("parents-bed.json.gz",), changes="parents source-bed omission"),
)


def stage(name: str) -> tuple[Pass, ...]:
    return tuple(p for p in PASSES if p.stage == name)


def _resolve(token: str, ctx: dict):
    if token.startswith("approvals:"):
        return ROOT / "knowledge" / token.split(":", 1)[1]
    if token == "lighting":
        from ..concept import villa_lighting as VL
        return VL.design(ctx["lay"])
    if token == "clear_rects":
        from ..concept import villa_furnish as F
        return {room: F.clear_rect(ctx["lay"], room) for room in ctx["lay"]["rooms"]}
    if token == "furniture":
        return list(ctx["furniture"])          # a fresh list per call, as `list(it_all.values())` was
    return ctx[token]


def run_stage(name: str, scene, ctx: dict):
    """Run a stage's passes in order; returns the (possibly replaced) scene."""
    ctx = dict(ctx)
    for p in stage(name):
        mod, fn = p.call.split(":")
        func = getattr(importlib.import_module("archpipe." + mod), fn)
        ctx["scene"] = scene
        if p.input_revision is None:
            cm = nullcontext()
        else:
            from ..concept.sanitary_relocation import input_revision
            cm = input_revision(p.input_revision)
        with cm:
            out = func(*[_resolve(a, ctx) for a in p.args])
        if p.returns_scene:
            scene = out
    return scene


def inventory() -> list[dict]:
    """Machine-readable pass table for docs and other lanes."""
    return [dict(id=p.id, stage=p.stage, call=p.call, knowledge=list(p.knowledge), changes=p.changes,
                 input_revision=p.input_revision) for p in PASSES]
