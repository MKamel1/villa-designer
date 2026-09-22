"""One command from spec to drawing set.

    python -m archpipe build spec/apartment.yaml          # DXF + PNG
    python -m archpipe build spec/apartment.yaml --pdf    # + DWG + plotted PDF
    python -m archpipe check spec/apartment.yaml          # validate only

`check` is deliberately separate and Autodesk-free: it is the fast gate
worth running on every spec edit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .model import SpecError, load


def _check(args) -> int:
    try:
        p = load(args.spec)
    except SpecError as e:
        print(f"SPEC ERROR: {e}", file=sys.stderr)
        return 1
    print(f"{p.name}  [{p.units}, {p.standard}]")
    for lvl in p.levels:
        rooms = [r for r in p.rooms if r.level == lvl.id]
        walls = [w for w in p.walls if w.level == lvl.id]
        total = sum(r.area_m2 for r in rooms)
        print(f"  {lvl.id} {lvl.name}: {len(walls)} walls, {len(rooms)} rooms, "
              f"{total:.2f} m2 net")
        for r in sorted(rooms, key=lambda r: -r.area_m2):
            print(f"      {r.name:22s} {r.area_m2:7.2f} m2")
    print(f"  openings: {len(p.openings)} "
          f"({sum(1 for o in p.openings if o.kind == 'door')} doors, "
          f"{sum(1 for o in p.openings if o.kind == 'window')} windows)")
    print("OK")
    return 0


def _build(args) -> int:
    from . import acad, preview as prev
    from .render_dxf import render

    try:
        p = load(args.spec)
    except SpecError as e:
        print(f"SPEC ERROR: {e}", file=sys.stderr)
        return 1

    outdir = Path(args.out)
    stem = Path(args.spec).stem
    levels = [args.level] if args.level else [l.id for l in p.levels]

    for lvl in levels:
        dxf = render(p, outdir / f"{stem}_{lvl}.dxf", level=lvl, scale=args.scale)
        print(f"DXF  {dxf}")
        png = prev.preview(dxf, outdir / f"{stem}_{lvl}.png")
        print(f"PNG  {png}")
        if args.pdf:
            dwg = acad.to_dwg(dxf, outdir / f"{stem}_{lvl}.dwg")
            print(f"DWG  {dwg}")
            pdf = acad.plot_pdf(dwg, outdir / f"{stem}_{lvl}.pdf")
            print(f"PDF  {pdf}")
            # The DXF preview never touches AutoCAD, so it proves nothing
            # about the plot. Rasterise what was actually plotted.
            chk = prev.rasterise_pdf(pdf, outdir / f"{stem}_{lvl}_plotted.png")
            print(f"CHK  {chk}")
    return 0


def _review(args) -> int:
    """Rebuild the web review sheet. Republish the result to keep its URL."""
    from .build_viewer import render_page

    try:
        p = load(args.spec)
    except SpecError as e:
        print(f"SPEC ERROR: {e}", file=sys.stderr)
        return 1

    stem = Path(args.spec).stem
    lvl = args.level or p.levels[0].id
    dxf = Path(args.out) / f"{stem}_{lvl}.dxf"
    if not dxf.exists():
        print(f"{dxf} not found -- run `build` first", file=sys.stderr)
        return 1

    page = render_page(args.spec, dxf, args.template,
                       Path(args.out) / "web" / "index.html", lvl)
    print(f"HTML {page}  ({page.stat().st_size // 1024} KB)")
    print("Publish it with the Artifact tool, passing the existing URL to keep it.")
    return 0


SEV_MARK = {"violation": "!!", "warning": " !", "advisory": "  "}


def _gate_report(stage: str, problems: list[str]) -> int:
    """Print a stage gate result. Non-zero exit means the gate is closed."""
    if not problems:
        print(f"\n{stage} gate: PASS")
        return 0
    print(f"\n{stage} gate: BLOCKED ({len(problems)})")
    for p in problems:
        print(f"  - {p}")
    return 1


def _brief(args) -> int:
    """Stage 0 (Intent): validate the brief and test its gate."""
    from . import brief as briefmod

    try:
        b = briefmod.load(args.brief)
    except (briefmod.BriefError, KeyError) as e:
        print(f"BRIEF ERROR: {e}", file=sys.stderr)
        return 2

    print(f"{b.name}")
    print(f"  household {b.household.size}"
          f"{', ageing in place' if b.household.ageing_in_place else ''}"
          f" | {b.levels_preferred} level(s) preferred")
    print(f"  hosting {b.living.hosting_frequency}, cooking {b.living.cooking},"
          f" {b.living.work_from_home} working from home")
    print()
    print("  Schedule of accommodation")
    for r in sorted(b.rooms, key=lambda r: -r.total_m2):
        count = f" x{r.count}" if r.count > 1 else ""
        print(f"    {r.priority:<6} {r.name + count:<22} {r.total_m2:7.1f} m2"
              f"  [{r.occupancy}]")
    print(f"    {'':<6} {'NET TOTAL':<22} {b.net_area_m2:7.1f} m2")
    by = b.net_area_by_priority()
    print(f"    {'':<6} {'':<22} "
          + "  ".join(f"{k}: {v:.0f}" for k, v in by.items()))
    return _gate_report("Stage 0 (Intent)", b.gate())


def _site(args) -> int:
    """Stage 1 (Ground): validate the site and study its orientation."""
    from . import site as sitemod

    try:
        s = sitemod.load(args.site)
    except (sitemod.SiteError, KeyError) as e:
        print(f"SITE ERROR: {e}", file=sys.stderr)
        return 2

    foot, fwhy = s.max_footprint_m2()
    floor, why = s.max_floor_area_m2()
    print(f"{s.name}  |  {s.location.city}  lat {s.location.latitude:.4f}")
    print(f"  plot area              {s.area_m2:8.1f} m2")
    print(f"  permitted footprint    {foot:8.1f} m2   ({fwhy})")
    print(f"  permitted floor area   {floor:8.1f} m2   ({why})")

    if not args.no_sun:
        print()
        print("  Orientation -- hours of direct sun on each aspect")
        print(f"    {'aspect':<8}{'summer':>9}{'equinox':>9}{'winter':>9}{'annual':>9}")
        for r in s.orientation_report():
            print(f"    {r['aspect']:<8}{r['summer_solstice']:>9.1f}"
                  f"{r['equinox_march']:>9.1f}{r['winter_solstice']:>9.1f}"
                  f"{r['annual_proxy']:>9.1f}")
        best = max(s.orientation_report(), key=lambda r: r["annual_proxy"])
        print(f"    -> best annual aspect: {best['aspect']}"
              f" ({best['annual_proxy']:.1f} h)")
    return _gate_report("Stage 1 (Ground)", s.gate())


def _fit(args) -> int:
    """Stage 2 (Fit): does the brief fit the ground?"""
    from . import brief as briefmod, feasibility, site as sitemod

    try:
        b = briefmod.load(args.brief)
        s = sitemod.load(args.site)
    except (briefmod.BriefError, sitemod.SiteError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    v = feasibility.assess(b, s, efficiency=args.efficiency, levels=args.levels)
    print(feasibility.report(v))
    return 0 if v.fits else 1


def _design(args) -> int:
    """Run the design rule library over a spec.

    `--stage N` reports only what is answerable by stage N, so a concept
    still at Stage 3 is not buried under room-resolution failures it is too
    early to fix. The exit contract is unchanged and applies to what is
    REPORTED: a suppressed later-stage violation does not fail the gate,
    because at that stage it is not yet a question.
    """
    import json as _json

    from . import codes, rules, vocabulary

    try:
        p = load(args.spec)
    except SpecError as e:
        print(f"SPEC ERROR: {e}", file=sys.stderr)
        return 1

    pack = None
    if args.code_pack:
        try:
            pack = codes.load(args.code_pack)
        except (codes.CodePackError, OSError) as e:
            print(f"CODE PACK ERROR: {e}", file=sys.stderr)
            return 2

    level = args.level or (p.levels[0].id if p.levels else "")
    try:
        every = rules.review(p, level, pack=pack)
    except vocabulary.UnknownOccupancy as e:
        print(f"SPEC ERROR: {e}", file=sys.stderr)
        return 2

    if args.stage is None:
        findings = every
    else:
        findings = [f for f in every if f.stage <= args.stage]

    print(f"{p.name} -- {level}: {len(findings)} findings")
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    print("  " + ", ".join(f"{n} {s}" for s, n in counts.items()) if counts
          else "  nothing to report")
    if args.stage is not None:
        held = len(every) - len(findings)
        print(f"  reporting Stage 0-{args.stage} "
              f"({rules.STAGES[args.stage]}) only; {held} later-stage "
              f"finding(s) not shown")
    # The standing of these findings, stated before any of them are read.
    print(f"  NOTE: {codes.disclaimer(pack)}")
    print()
    for f in findings:
        print(f"{SEV_MARK.get(f.severity, '  ')} [{f.rule} | {f.stage_label} | "
              f"{f.kind}] {f.message}")
        print(f"      reference: {f.reference}")
        if f.code:
            print(f"      code: {f.code}")
        if f.at:
            print(f"      at: {f.at[0]:.0f}, {f.at[1]:.0f} mm")
        print("      fix ladder (cheapest first):")
        for line in f.ladder_lines():
            for i, part in enumerate(line.split("\n")):
                print(f"        {part}" if i == 0 else f"     {part}")
        print()

    if args.notes:
        rows = [f.as_note() for f in findings]
        Path(args.notes).parent.mkdir(parents=True, exist_ok=True)
        Path(args.notes).write_text(_json.dumps(rows, indent=2), encoding="utf-8")
        print(f"wrote {len(rows)} note rows -> {args.notes}")

    # Violations fail the gate; warnings and advisories do not.
    return 1 if counts.get("violation") else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="archpipe")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="validate a spec, print the schedule")
    c.add_argument("spec")
    c.set_defaults(func=_check)

    b = sub.add_parser("build", help="render a spec to drawings")
    b.add_argument("spec")
    b.add_argument("--out", default="out")
    b.add_argument("--level", default=None, help="one level id (default: all)")
    b.add_argument("--scale", type=float, default=50.0, help="plot scale denominator")
    b.add_argument("--pdf", action="store_true", help="also produce DWG and plotted PDF")
    b.set_defaults(func=_build)

    r = sub.add_parser("review", help="rebuild the web review sheet from a spec")
    r.add_argument("spec")
    r.add_argument("--out", default="out")
    r.add_argument("--level", default=None)
    r.add_argument("--template", default="viewer/template.html")
    r.set_defaults(func=_review)

    d = sub.add_parser("design", help="run the design rule library over a spec")
    d.add_argument("spec")
    d.add_argument("--level", default=None)
    d.add_argument("--stage", type=int, default=None, choices=range(0, 8),
                   metavar="N",
                   help="report only findings meaningful by stage N (0-7); "
                        "without it, every stage is reported")
    d.add_argument("--code-pack", default=None, metavar="PATH",
                   help="jurisdiction code pack (YAML), or 'example' for the "
                        "built-in example. None by default: findings are then "
                        "guidance, not code compliance")
    d.add_argument("--notes", default=None,
                   help="also write findings as review-sheet note rows (JSON)")
    d.set_defaults(func=_design)

    # ---- Villa Design Method stages -----------------------------------
    br = sub.add_parser("brief", help="Stage 0 (Intent): validate the brief")
    br.add_argument("brief")
    br.set_defaults(func=_brief)

    si = sub.add_parser("site", help="Stage 1 (Ground): site and orientation")
    si.add_argument("site")
    si.add_argument("--no-sun", action="store_true",
                    help="skip the orientation study")
    si.set_defaults(func=_site)

    ft = sub.add_parser("fit", help="Stage 2 (Fit): does the brief fit the site?")
    ft.add_argument("brief")
    ft.add_argument("site")
    ft.add_argument("--efficiency", type=float, default=None,
                    help="net-to-gross ratio (default 0.78)")
    ft.add_argument("--levels", type=int, default=None)
    ft.set_defaults(func=_fit)

    args = ap.parse_args(argv)
    if getattr(args, "efficiency", None) is None and args.cmd == "fit":
        from .feasibility import DEFAULT_EFFICIENCY
        args.efficiency = DEFAULT_EFFICIENCY
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
