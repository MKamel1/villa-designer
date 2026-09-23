# End-to-end capability test: one bedroom, spec to render

## Context

Before committing to the real villa, prove the whole chain on the
smallest useful thing: **one bedroom, specified in text, built in Revit,
then drawn, furnished, painted, lit, rendered and reviewed.** If a
capability does not survive this, it will not survive a villa.

The client's framing, taken as a hard requirement: *"you prepare a mock
spec and you must be able to build it in Revit — a project requirement we
must pass with flying flags."* So **spec → Revit is the headline
capability**, not a convenience.

Two client decisions shape this:

- **2D comes from Revit native views only.** The DXF/A3 pipeline we built
  and verified is not exercised here.
- **Revit is also the communication surface.** The client is happy to
  open Revit to review, and asked that if Revit can carry revision
  clouds, text and highlights, we use it rather than the web sheet. It
  can — and crucially the API can *read those back*, so markup becomes a
  channel the agent can answer, not just a picture.

### Environment as measured today

| | |
|---|---|
| Laptop | Core Ultra 7 258V, 8C/8T, 32 GB, Arc 140V iGPU, **40 GB disk free** |
| Workstation | RTX 3090 **free and on the nvidia driver**, 32 threads, 85 GB RAM, 956 GB free |
| VM | stopped — no longer holding the GPU |
| Blender / Radiance | **both absent** on the workstation |

## The blocker: content, not licensing

**ADR-0008's open question is now answered.** Revit 2026 did not fail for
an unexplained reason — the client's entitlement covers **2025 only**.
The 300 s hang and `Adlsdk Error:(20)` were an unlicensed product
behaving badly, not a bug to chase. ADR-0008 should be updated to say so;
"root cause not isolated" is no longer true.

That closes one question and leaves a sharper one:

- Revit **2025** — automation verified working, but only 446 families,
  almost all annotation and structural. **No doors, windows, furniture or
  light fixtures at all.**
- Revit **2026** — 3,237 metric families sitting on this disk, and
  unusable: no entitlement, and families are **forward-compatible only**,
  so they could not be loaded into a 2025 project even with one.

So the bedroom cannot be furnished or lit until 2025 has content.

### Task 0 — get the content (client action, ~2 GB)

The official library is a separate download, not part of the installer:

> Autodesk Account → **All Products and Services** → Revit →
> **View Details** → **Libraries** under Available Downloads → pick the
> **2025** content package. It arrives as an installer that places the
> families in the right folders automatically.

For metric work take the **UK English** and/or **International English**
packages, not US Imperial. The current `Libraries\English\US` folder is
the imperial-flavoured stub, which is part of why it looks empty.

I cannot do this — it needs the client's Autodesk sign-in.

**Worth knowing:** Revit 2021.1+ also has a **Load Autodesk Family**
command that pulls default families from Autodesk's cloud on demand, with
no local library. Useful as a stopgap for a few pieces, but it is a UI
command rather than an API call, so it does not help automation.

### Beyond the default library

The Autodesk library covers doors, windows, generic furniture and
lighting — enough for this test. For villa-grade furniture it is plain.
Free manufacturer content is available from **BIMobject**, **BIMsmith**,
**BIM Library** and similar; each download is per-item and usually needs
a free account, so it suits picking specific pieces later rather than
bulk acquisition now.

Plan for the default library first, and treat manufacturer content as a
quality upgrade once the pipeline is proven.

Geometry, rooms and openings-as-voids work today without any of it.

---

## The mock spec

`spec/bedroom-test.yaml` — chosen to exercise rules rather than to be
pretty:

- 4200 × 3600 mm internal, 2700 ceiling
- window on the **south** wall, 1500 × 1400, sill 900
- door on the **east** wall, 900 × 2100
- furniture: double bed, two bedside tables, wardrobe, desk + chair
- materials: painted walls, timber floor, plaster ceiling
- lighting: ceiling pendant **plus** two bedside lamps **plus** a wardrobe
  strip — deliberately three layers, so the "no lone central fixture"
  rule passes and its negative case can be tested by deleting two

Deliberate test hooks: the double bed needs 750 mm access on **both**
sides (Neufert), and the wardrobe needs 750 mm to open. A 4200 × 3600
room makes that tight enough to be a real check rather than a formality.

## Pipeline, and what each step proves

| # | Step | Proves | Status |
|---|---|---|---|
| 1 | spec YAML → Revit model | **the headline requirement** | to build |
| 2 | extract → `model.json` | the bridge holds with real content | works, needs materials |
| 3 | rule review on the extract | the critic runs on Revit data | works |
| 4 | Revit views → sheet → PDF | native 2D deliverable | to build |
| 5 | Revit 3D view | 3D in the authoring tool | to build |
| 6 | lux grid + heat map | lighting **compliance** (arithmetic, ADR-0004) | to build |
| 7 | extract → Blender → Cycles render | cross-machine GPU rendering | to build |
| 8 | Revit markup → extract | **communication as data** | to build |

## What gets built

**`revit/family_inventory.py`** — index the installed library. Walks the
content folders, reads each family's category and type names, and writes
`docs/families.json`. Without this the agent is guessing filenames; with
it, "a double bed" resolves to a real `.rfa` and a real type.

**`src/archpipe/family_map.py`** — bind our catalogue to real families.
`catalogue.py` already knows a `bed_double` is 1600 × 2000 needing 750 mm
both sides (Neufert). This maps that to the family and type that actually
exists, and **flags a mismatch** when the chosen family's real dimensions
differ from the catalogue's assumption — otherwise every clearance check
downstream is measuring a fiction.

**`revit/place_families_test.py`** — the "prove we can use them" check,
separate from the bedroom so a failure is diagnosable. For one door, one
window and one furniture item: load the family, **activate the symbol**,
place it (hosted for door/window), re-extract, and confirm the position
and dimensions come back matching what was asked for.

> The activation step is the trap. A family symbol that is loaded but not
> activated returns `None` from placement **without raising**. It reads
> as "nothing happened" rather than as an error.

**`revit/build_bedroom.py`** — spec → Revit. Extends the verified
`build_test_model.py` (which already creates levels, walls and a room to
known dimensions). Adds: family loading, hosted door and window
placement, furniture placement, material creation and assignment, light
fixture placement. Runs via `pyrevit run`, already proven.

**`revit/extract_model.py`** — add **materials** (surface finish per
wall/floor/ceiling, needed for both "paint" and render) and **markup**
(`OST_TextNotes`, `OST_RevisionClouds`) with their positions, so client
comments come back as structured data.

**`revit/export_views.py`** — create floor plan, reflected ceiling plan,
two elevations, one section and a 3D view; place them on a sheet; export
PDF. Revit 2022+ has a native `PDFExportOptions` API.

**`src/archpipe/lighting.py`** — point-by-point illuminance from IES
photometry: inverse-square with cosine correction over a working-plane
grid. Outputs average, min, max, **uniformity (Emin/Eavg)** and a
false-colour heat map. Pure Python, runs on the laptop, no GPU.
**Validate against a hand-calculable single fixture before trusting any
heat map.**

**`src/archpipe/blender/build_scene.py`** — the bridge. Reads the extract
and builds geometry procedurally in Blender: walls extruded from
centreline + thickness + height, floors from room boundaries, apertures
cut from openings, furniture as placed proxies, materials from the
extract, lights from the fixture list. No FBX round-trip — the extract is
already text, git-synced and platform-neutral.

**`scripts/render_remote.py`** — dispatch to `ai-workstation` over SSH:
push the extract, run headless Blender (`blender -b -P build_scene.py`),
pull the image back.

**Rules** — add the Stage 5 lighting family: ≥3 layers in key rooms, fail
a lone central fixture, lux targets (bedroom 100–200 lx), uniformity
≥ 0.4, colour-temperature consistency, CRI ≥ 90. Every one cited, per
`CLAUDE.md`.

## Workstation changes — the house rules

The client has offered sudo and asked that any change be made "neatly, in
an organised, documented fashion". Taking that seriously:

- **Every change to `ai-workstation` is scripted, not typed.** Scripts
  live in `ops/workstation/` in this repo, so the machine can be rebuilt
  from the repo rather than from memory.
- **One script per concern**, each idempotent and safe to re-run.
- **A running log** at `docs/ops/workstation-changes.md`: what changed,
  when, why, and how to undo it.
- **Nothing installed outside a package manager** without saying so.
  Radiance will need a source build if we get to it — that goes in
  `/opt`, documented, not scattered.
- **Ask before anything destructive or system-wide**; sudo being
  available is not the same as it being mine to spend.

First entries will be: install Blender, pin its version, and confirm
headless GPU rendering on the 3090.

## Order of work

**Client, in parallel with everything below:** download the Revit 2025
content library (Task 0).

1. **Blender bridge on the laptop** — build a scene from the *existing*
   verified extract and render on CPU. Needs no Revit content and no
   workstation, so it starts immediately.
2. **Blender on the workstation** — same scene on the 3090, via
   `ops/workstation/`. Proves the cross-machine path and gives a real
   speed comparison against the laptop's Arc iGPU.
3. **Family inventory + placement test** — the moment content lands.
   Index it, then prove one door, one window and one furniture item can
   be loaded, activated, placed and read back.
4. **`build_bedroom.py`** — the headline capability.
5. Extract materials + markup.
6. Revit views → sheet → PDF.
7. Lighting engine, validated against hand calculation.
8. Full run, end to end, reviewed.

Steps 1–2 are unblocked now. Step 3 is the gate: if families cannot be
placed programmatically, steps 4–8 need rethinking, so it is deliberately
small and tested on its own rather than discovered inside the bedroom
build.

## Verification

Each step gets a check that would **fail if the step were silently
wrong**, not merely absent:

- **Content actually usable** (the gate): after the library installs,
  `family_inventory.py` must find doors, windows, beds, wardrobes and
  light fixtures by category — not just count `.rfa` files. Then one of
  each must load, activate, place and read back with the right position.
  A family that "places" but returns `None` is the expected failure mode.
- **Catalogue vs reality**: `family_map.py` must flag any family whose
  real dimensions differ from the Neufert figure in `catalogue.py`. A
  1800 mm-wide bed checked against a 1600 mm assumption would pass
  clearances it should fail.
- **Geometry**: room area from the extract must equal the spec's
  4200 × 3600 within a millimetre. The existing 6000 × 4000 test already
  proves the units boundary; this repeats it on real content.
- **Openings**: window sill/head from the extract must match the spec.
  Revit works in decimal feet — a units error does not raise.
- **Furniture**: the rule engine must report clearance
  achieved-versus-required, and the negative case (bed pushed against a
  wall) must fire.
- **Lighting**: validate the lux engine against a hand-calculable single
  fixture at known mounting height before any heat map is trusted; then
  the three-layer scheme must pass and deleting the bedside lamps must
  fail the layer rule.
- **Render**: image produced on the workstation, pulled back, and
  visually compared against the Revit 3D view — they should show the same
  room.
- **Markup**: add a revision cloud and a text note in Revit, re-extract,
  and confirm both come back with position and text.
- `scripts/verify.py` stays green throughout (53 checks).

## Risks

1. **Revit 2025 content** gates everything furnished or lit. Route A is a
   client download; route B is work I can do but yields crude geometry.
2. **Family placement API** — hosted doors and windows need the family
   symbol *activated* before placement, and an inactive symbol returns
   `None` rather than raising. A classic silent failure.
3. **Laptop disk: 40 GB free.** The client can add space; until then keep
   renders and large models on the workstation, not here.
4. **Blender's Python API is version-sensitive** — pin it and match the
   version across laptop and workstation, or the same scene script will
   behave differently on each.
5. **Radiance is not in apt** (`Candidate: (none)`) — a source build when
   we need it. Not required for this test: Blender covers rendering and
   the lux grid covers compliance (ADR-0004).
6. **Crude families would flatter nothing.** If route B is used, say so
   plainly when showing renders rather than letting box furniture read as
   a design proposal.

## Out of scope for this test

Multi-room coordination, stairs, the villa brief and site, dirty-DWG
ingest, Radiance, and the web review sheet's markup tools — the client
has asked to try Revit as the communication surface first.
