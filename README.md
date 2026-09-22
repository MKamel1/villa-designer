# arch-pipeline

An AI-led villa design system: a staged method with checks attached, so
every piece of advice cites a source and reports achieved-versus-required
rather than an adjective.

**Source of truth:** once Revit is in place it is the only authored
artifact, and the text model becomes a generated extract that nothing
hand-edits ([ADR-0001](docs/decisions/ADR-0001-revit-as-source-of-truth.md),
[ADR-0002](docs/decisions/ADR-0002-extract-not-sync.md)). Until then the
YAML specs here are authored directly. Either way the design stays
readable as text, which is what makes it reviewable by both a human and
an agent — a `.rvt` is a binary blob neither can diff.

## Status

Stages 0–2 (brief, site, feasibility) run today with **no Revit and no
AutoCAD**. The AutoCAD drawing pipeline works end to end on Windows,
fully headless:

    spec/apartment.yaml  ->  DXF  ->  PNG preview
                                 ->  DWG  ->  plotted PDF  ->  PNG of the plot

Both PNGs have been checked visually. The second one matters: the DXF
preview never touches AutoCAD, the CTB or lineweights, so it proves
nothing about the plot.

Known caveat: SHX text plots as stroked vectors, so the PDF has no
selectable or searchable text. Switch `TEXT_FONT` in `layers.py` to a
TrueType font if that is wanted.

## Picking this up cold

- **An AI agent taking over** → [`docs/HANDOVER.md`](docs/HANDOVER.md),
  then [`CLAUDE.md`](CLAUDE.md) (loaded automatically each session).
  It includes the **VM test plan** — nothing here has run on the VM yet.
- **Rebuilding the environment** → [`docs/SETUP.md`](docs/SETUP.md) — it rebuilds this
environment from scratch, and records the failures worth not repeating
(chiefly: use **Revit 2025, not 2026** — see
[ADR-0008](docs/decisions/ADR-0008-revit-2025-not-2026.md)).

## The method

Design follows the **Villa Design Method** — eight decision-led stages
with quality gates and thirteen named backward loops. See
[`docs/method/villa-design-method.md`](docs/method/villa-design-method.md),
with the reasoning in [`docs/PRD.md`](docs/PRD.md) and the decision
record in [`docs/decisions/`](docs/decisions/).

    0 Intent -> 1 Ground -> 2 Fit -> 3 Order -> 4 Rooms
      -> 5 Systems -> 6 Substance -> 7 Proof

## Run

Method stages (no Autodesk, no Revit needed):

    python -m archpipe brief spec/villa-brief.yaml              # Stage 0
    python -m archpipe site  spec/villa-site.yaml               # Stage 1 + sun
    python -m archpipe fit   spec/villa-brief.yaml spec/villa-site.yaml   # Stage 2

Drawing and review (Stage 4 onward):

    python -m archpipe check  spec/apartment.yaml       # validate + schedule
    python -m archpipe design spec/apartment.yaml       # design review
    python -m archpipe build  spec/apartment.yaml       # DXF + PNG
    python -m archpipe build  spec/apartment.yaml --pdf # + DWG + plotted PDF
    python -m archpipe review spec/apartment.yaml       # rebuild the web sheet

Verification (53 checks, positive and negative):

    PYTHONPATH=src python scripts/verify.py

Every stage command **exits non-zero when its gate is closed**, so each
works as a gate in a script: `check` on a structural error, `design` on a
`violation`, `brief`/`site` on a blocked gate, `fit` when the brief does
not fit the plot.

Setup:

    python -m venv .venv
    .venv/Scripts/python -m pip install -r requirements.txt
    set PYTHONPATH=src

## Layers

- **L0 — the spec** (`spec/*.yaml`, `src/archpipe/model.py`).
  Millimetres. Walls as centrelines with a *type*; openings reference a
  *host* wall; rooms are closed boundary polygons. Deliberately
  BIM-shaped even though the renderer is 2D, because a later IFC or
  Revit renderer needs exactly these and retrofitting them is painful.
  Areas are always computed, never typed.

- **L1 — DXF renderer** (`render_dxf.py`). Pure Python via `ezdxf`. No
  licence, no AutoCAD process, runs on Linux. Walls are built as
  polygons and unioned with `shapely` before drawing, which is what
  makes junctions clean up automatically; openings are subtracted, so a
  reveal is a real hole in the poche rather than white paint on top.

- **L2 — headless AutoCAD** (`acad.py`). `accoreconsole.exe` for
  DXF→DWG and plotting to PDF. Windows only.

- **L1b — web review sheet** (`web.py`, `viewer_data.py`, `build_viewer.py`,
  `viewer/template.html`). DXF → SVG, published as a claude.ai artifact
  with pan/zoom, a live cursor readout in millimetres, a scale bar, and
  pinned review notes stored in the artifact's shared database.

  The load-bearing part is the **model↔SVG transform**. A pin resolves to
  model millimetres and, by point-in-polygon against the L0 room
  boundaries, to the room it landed in — so a note reads "Bedroom 1 at
  5700, 2500 mm", not "pixel 412, 308". `web.verify_transform()` checks
  the mapping against geometry at known coordinates rather than trusting
  the arithmetic; it currently lands within 0.01 mm (SVG path rounding).

  Notes are read back with the `ArtifactData` tool, so client feedback
  arrives as structured rows — coordinates, room id, author, text — that
  can be acted on directly, not as markup entities to be parsed out of a
  DWG.

  **The page is not Claude-dependent.** Storage sits behind a `NoteStore`
  interface with three backends — `ClaudeDbStore` (the artifact database),
  `LocalStore` (localStorage) and `RestStore` (any HTTP endpoint) —
  selected at boot, falling back rather than throwing when no platform is
  present. Verified: served as a plain static file with `window.claude`
  undefined, the plan renders, a pin resolves to its room and
  millimetre coordinates, and a note survives a reload.

  Export emits one self-describing JSON object — `format`, `version`,
  `units`, `coordinates`, `extents_mm`, `transform`, `transform_doc`,
  `rooms`, `notes` — so **another AI system can interpret the coordinates
  without this page**. It is copy-to-clipboard and a visible textarea, not
  a download link, because a published artifact's sandbox makes
  script-driven downloads inert.

- **Stage 0–2** (`brief.py`, `site.py`, `solar.py`, `feasibility.py`).
  The brief and the site as data, and the check that they are compatible.

  `brief.py` makes the brief machine-readable, which buys something no
  generic checker has: the design can be checked **against the brief**,
  not only against standards — "you asked for four bedrooms, the plan has
  three".

  `solar.py` implements the NOAA solar position algorithm. No library, no
  service. It is **verified, not assumed**: `solar.verify()` runs 14
  checks — solar-noon azimuth due south in the northern hemisphere and
  due north in the southern, equinox noon altitude equal to 90 − |lat|,
  solstice noon altitude of 90° at the matching tropic, and London
  sunrise/sunset within two minutes of published almanac times once the
  −0.833° refraction allowance is applied. A wrong azimuth does not
  announce itself; it silently corrupts every orientation rule.

  `feasibility.py` answers Stage 2 in arithmetic, before anything is
  drawn, and returns a **cut ladder** — the concessions needed to fit,
  cheapest first. Note the net/gross distinction: room areas in a brief
  are net, permitted area is gross, and comparing them directly
  over-cuts by about a quarter.

- **Design review** (`rules.py`, `catalogue.py`). The critic. It does not
  invent layouts; it checks one against published planning dimensions and
  reports each failure with the rule, the number, the citation and the
  consequence — so the advice can be argued with rather than taken on
  trust.

  Severity is `violation` (breaks a published minimum) / `warning`
  (recognised planning fault) / `advisory` (comfort or preference).
  Findings carry model coordinates, so `--notes` emits them straight
  into the review sheet as pinned notes.

  `catalogue.py` holds furniture footprints and the clearance each piece
  demands, **each entry citing its source** — mostly Neufert,
  *Architects' Data*, with trade practice marked as such. These are
  design guidance, not code: where a local code is stricter it wins, and
  a jurisdiction layer should override these values rather than edit
  them.

  Current rules: sanitary accommodation present; room minimum areas;
  minimum habitable room width; door clear widths; private rooms reached
  only through living space; entrance without a vestibule; furniture
  clashing with walls; furniture overlapping furniture; blocked
  clearance (reported as achieved-vs-required, e.g. "350 mm where 450 is
  needed"); obstructed door swings; daylight at 1/8 of floor area; and a
  circulation check that erodes the room's free space by half the
  minimum corridor width and tests whether the doors remain connected.

- **L3 — BIM.** Not built. See below.

Drawing standard lives entirely in `layers.py` — layer names,
lineweights, text and dimension styles. Changing office convention is a
one-file edit.

## Three accoreconsole traps

All three were hit for real here, so they are recorded in `acad.py` too:

1. An **invalid answer to a keyword prompt** puts the command into a
   re-prompt loop (`Yes or No, please.`) that **blocks forever** and
   ignores stdin EOF. A script that merely runs out of lines mid-command
   usually aborts cleanly; it is the invalid answer that wedges it.
   `_run()` therefore enforces a timeout and kills the child, because
   `subprocess`'s own `TimeoutExpired` leaves it orphaned.

2. The `-PLOT` prompt sequence depends on the output device. With a PDF
   plotter there is **no** "write the plot to a file?" prompt — it goes
   straight to the filename — and there **is** a shade-plot prompt after
   lineweights. Getting this wrong causes trap 1.

3. Given a **relative script path**, accoreconsole neither runs the
   script nor reports an error: it exits 0 in under a second having done
   nothing, which is indistinguishable from success. `_run()` resolves
   and existence-checks both paths first. This one briefly produced a
   false "no hang" result while testing trap 1.

The sequence in `acad.py` was captured by running the command and
reading the transcript, not from documentation. If it hangs after an
AutoCAD upgrade, re-capture it the same way: run with stdout redirected
to a file and read where it stopped.

## Sheets

`scripts/build_sheet.py` produces a **true 1:50 A3 sheet** with an ISO
title block, frame, north arrow and graphic scale bar (`sheet.py`,
`acad.plot_layout_pdf`).

The scale is exact and verified from the DXF, not asserted: the viewport
is 199 mm of paper showing 9950 mm of model, so 1:50.0000, and the
10300 mm external width plots at 206.00 mm.

Two things worth knowing:

- Plotting a **named layout** uses a different `-PLOT` prompt sequence
  from Model. The plot area is `Layout` (not `Limits`), the offset
  prompt has **no** `[Center]` option — so `plot_pdf`'s `C` would wedge
  the process here — and three prompts appear that Model never asks.
  Captured empirically; see `acad.plot_layout_pdf`.
- `to_dwg` now deletes the target first. `SAVEAS` over an existing file
  asks "overwrite?", which no script line answers, and that wedges
  accoreconsole — trap 1 again, found by hitting it.

**Known cosmetic defect:** dashed linetypes (clearance zones, room
boundaries) plot **solid** through the layout viewport. The `ARCH-DASHED`
definition in the DXF is correct (300 total, 200 dash, 100 gap) and the
layer carries it, and `$PSLTSCALE` is now 0, but the dashes still do not
appear in the plotted PDF. The same geometry DOES render dashed in the
web review sheet, so the fault is in the AutoCAD plot path, not in the
linetype definition or the geometry. Cause not isolated beyond that. Impact is low — the zones
remain legible by line weight — but it is unfixed, not fixed.

## What is deliberately not done yet

- **No sheet layout or title block.** The PDF is model-space extents
  fitted to A3, not a true 1:50 sheet. This is the next thing to build
  for output that looks professional rather than merely correct.
- **No dimension strings** beyond two overall dimensions. Running
  dimensions to openings and grid lines are not generated.
- **Wall junctions** are handled by polygon union, which is right for
  the common cases here but has not been tested on non-orthogonal walls
  or walls of differing thickness meeting at acute angles.
- **No BIM.** L0 carries the data an IFC/Revit renderer needs, but
  nothing consumes it yet.

## Revit

Revit has no local headless mode — there is no `revitcoreconsole`.
Automation means one of:

1. pyRevit / Dynamo / a C# add-in running inside a licensed, open Revit
   GUI session. Scripts are written here, run there.
2. APS Design Automation for Revit — genuinely headless, runs in
   Autodesk's cloud, bills credits, needs an entitlement.
3. Skip Revit: emit IFC with `IfcOpenShell` (free, pure Python, runs on
   Linux) and let Revit import it.

Option 3 is a real deliverable but **not** a substitute for a native
Revit model: an imported IFC arrives as generic geometry, not native
parametric walls with Revit's type system, schedules and tags.

## Sharing the review sheet — a real constraint

An artifact that declares the `db` capability (or the full `comments`
capability) is **organization-internal and cannot be shared by public
link**. Everyone who reads or writes it must be a signed-in member of
the owner's organization, and only viewers at "can interact" or above
write shared data.

So the review sheet as built works for you and for collaborators you
grant access to. It does **not** work for an arbitrary external client
handed a link. Two ways out when that day comes:

1. Grant the client access to the artifact ("Can interact" or above).
   Simplest, needs them signed in to claude.ai.
2. Rebuild the note layer on `comments: {composer_only: true,
   customAnchors: true}`, which keeps the artifact publicly shareable.
   The shell then renders the threads and the page only positions the
   pins; page-invented anchor names are not kept under that form, so
   pins must anchor to real DOM elements and carry their location in the
   compose `label`/`detail`. Read `comments.d.ts` before attempting it.

## Two machines

Windows is required for anything Autodesk-touching (L2, and any Revit
work). L0 and L1 are pure Python and run fine on Linux, as would the
IFC path — which makes the Ubuntu box the natural home for BIM
experiments and for CI on the spec.
