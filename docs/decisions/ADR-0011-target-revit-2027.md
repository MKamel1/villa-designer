# ADR-0011 — Target Revit 2027

- **Status:** accepted
- **Date:** 2026-09-22
- **Supersedes:** ADR-0008 (target Revit 2025, not 2026)
- **Client decision:** "yes move to 2027"

## Context

ADR-0008 settled on Revit 2025 because the client's entitlement covered
2025 only and 2026 failed at licensing — a 300 s hang on
`manage licensing`, then `Adlsdk Error:(20)`.

The client has since installed **Revit 2027 (27.0.4.412, build
20260907_1515, branch RELEASE_2027.3)** and reports it licensed and
working on the same student entitlement. That reopens the version choice,
so it was measured rather than assumed.

## What was verified before deciding

| Check | Revit 2025 | Revit 2027 |
|---|---|---|
| pyRevit 6.5.5 attaches | yes | yes |
| `pyrevit run` executes a script | yes | yes |
| `api_ok`, `raw_revitapi_import` | yes | yes |
| Signed-in user reported | yes | yes |
| Run time | 38 s | 36 s |
| .NET runtime | 8.0.31 | **10.0.9** |
| Licensing hang | none | **none** |

**The known-geometry test passes identically.** `build_test_model.py`
made the 6000 × 4000 mm rectangle in 2027 and `extract_model.py` read it
back:

```
wall lengths   [4000.0, 4000.0, 6000.0, 6000.0]   exact
wall thickness 200.0 mm
boundary span  5800.0 x 3800.0 mm                 exact
room area      22.040 m2   expected 22.040   delta 0.000000
```

That is the same figure the original machine produced on 2025. The units
boundary holds: Revit works in decimal feet and a conversion bug does not
raise, it silently yields a model 304.8× wrong, which is why this check
is against geometry chosen in advance rather than "did it run".

## Decision

**Target Revit 2027.** Keep 2025 attached as a fallback; nothing is
uninstalled.

## Why, beyond "it works"

**Revit 2027 ships a Model Context Protocol implementation.** The
Assistant is built on the official SDK (`ModelContextProtocol` 1.0.0.0,
loaded at runtime on .NET 10). Measured by reflection, not inferred:
78 tool classes exist, 6 are public. Full inventory in
`docs/reference/revit-2027-mcp.md`.

The private set covers a large part of this project's remaining build
list — `CreateSheetTool`, `CreatePlanViewsTool`, `CreateSectionViewTool`,
`CreateViewPortsTool`, `ExportViewsToPdfTool`, eight schedule tools,
`ColorRoomTool`. And `Autodesk.Assistant.ServerRegistry` exposes
`AddCustomServer` with an `ICustomTransportServer` interface, which is
the route by which archpipe's own rule and lighting engines could be
registered as tools the Revit assistant calls.

None of that is available on 2025.

## What the move does NOT buy

**No content.** Revit 2027's library is identical to 2025's: 446
families, **0 doors, 0 beds**, 1,328 family templates, 141 IES files.
The content problem is unchanged and the third-party route
(`scripts/fetch_families.py`, screened by `archpipe.rfa`) still applies.

## Consequences

- **One-way door.** `.rfa` and `.rvt` are forward-compatible only, so a
  model authored in 2027 can never be opened in 2025. Accepted
  deliberately; the client confirmed the move.
- The 28 downloaded families (Revit 2009–2022 format) all load in 2027.
  Moving the target forward only widens what is compatible, so nothing
  that worked before stops working. `archpipe.rfa.TARGET_REVIT` is now
  2027 and `verify()` tests that explicitly.
- `photometry.REVIT_IES_DIRS` prefers 2027's IES folder; all 141 files
  parse from it. IES is plain text and version-independent, so this was
  never at risk.
- `docs/SETUP.md` and `CLAUDE.md` now instruct 2027.
- ADR-0008's *reasoning* stands as history — the 2026 failure really was
  an entitlement gap — but its conclusion is superseded.

## One thing that nearly went wrong

The first 2027 run exited 0 with an empty execution log and no output,
which looked exactly like a 2027 incompatibility. Running the same script
against 2025 as a control failed identically, which is the only reason it
was not recorded as one.

The real cause was in Revit's journal:

```
, "ScriptSource" , "revit\probe.py"
TaskDialog "Can not find target file. Maybe deleted?"
```

`pyrevit run` passes the script path verbatim and Revit's working
directory is not the project folder. **The path must be absolute.** Same
class as the `accoreconsole` relative-path trap in `acad.py`: the tool
reports success having done nothing.

A journal line `API_ERROR { Assembly version conflict ... pyRevitRunner.dll }`
appears on **both** versions and is not fatal. Do not chase it.
