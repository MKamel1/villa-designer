# Setup — rebuilding this environment on another machine

Written for the move to a Windows VM running on the Linux workstation
(`ai-workstation`), with the RTX 3090 passed through. Follow it top to
bottom on a fresh machine.

Everything here was established by running it, not from documentation.
Where something failed, the failure is recorded rather than smoothed over,
because the failures are the parts that will cost you time again.

---

## 0. What runs where

| Component | Host | Why |
|---|---|---|
| Revit, AutoCAD | **Windows** | Autodesk products have no Linux build, and Wine is not viable |
| Rule engine, brief/site/feasibility, solar | either | pure Python |
| Radiance (lighting simulation) | **Linux** | CPU-bound; the 32 cores are the point |
| Blender Cycles (renders) | **Linux or VM** | GPU-bound; wherever the 3090 is bound |
| git | both | the contract between them (ADR-0002/0003) |

Radiance is CPU-only, so it never contends with whatever holds the GPU.

---

## 1. Python side (works on Linux and Windows)

```bash
git clone https://github.com/MKamel1/villa-designer.git
cd villa-designer
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# .venv/bin/python -m pip install -r requirements.txt     # Linux
```

Built and tested on **Python 3.14.7**. Dependencies are pinned in
`requirements.txt`.

Verify immediately — this needs no Autodesk software at all:

```bash
PYTHONPATH=src python scripts/verify.py        # expect: ALL PASS (53 checks)
PYTHONPATH=src python -m archpipe fit spec/villa-brief.yaml spec/villa-site.yaml
```

If those pass, Stages 0–2 and the whole rule engine are working. Nothing
below is needed for them.

---

## 2. Revit — use 2025, not 2026

**This is the single most important finding to carry across.**

On the original machine, Revit **2026 could not be licensed** for
automated launch. The failure is slow and unhelpful, so it is worth
recognising:

- `pyrevit run` hangs for exactly 300 s on `manage licensing`, then
  `LicenseUpd(1) Adlsdk Error:(20) vendor:ADLM`
- `adlm-err.log` shows `VendorError=-8` against `licpath.lic`
- the pyRevit add-in never loads — Revit dies before reaching it

**Revit 2025 worked first time**, in ~17 s, with full API access and a
signed-in user. Both were installed side by side, so this is a
2026-specific problem on that machine, not a pyRevit fault. Try 2026 again
on the VM if you like, but start from 2025 so you have a working baseline.

Sign in to Revit interactively **once** before expecting automation to
work. The automated launch has no UI to complete a sign-in through.

### pyRevit

Version used: **6.5.5.26237** (per-user installer, no elevation needed).

```powershell
# installer from https://github.com/pyrevitlabs/pyRevit/releases
pyRevit_<version>_signed.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES
```

Then attach it and register this repo's extension:

```powershell
$pr = "$env:APPDATA\pyRevit-Master\bin\pyrevit.exe"
& $pr attach master default 2025          # note: `default`, not `--installed`
& $pr extensions paths add <repo>\revit    # the PARENT of archpipe.extension
& $pr attached                             # confirm it lists Revit 2025
```

In Revit: **pyRevit tab → Reload**. An `archpipe` tab appears with
**Model → Extract Model**.

---

## 3. Two Revit behaviours that will waste your time

**`pyrevit run <model.rvt>` does NOT open the model.** It takes a model
path as an argument and still hands the script a `UIApplication` with
`Documents.Count == 0` and `ActiveUIDocument == None`. Measured, not
assumed. `extract_model.py` therefore opens the document itself via
`Application.OpenDocumentFile`, which also makes it behave identically
from the ribbon button.

**`revit.doc` is `None` in the runner**, and returns None rather than
raising — so a `try/except` around it catches nothing and the next line
dies on `None.Title`. `resolve_doc()` handles all three contexts.

---

## 4. AutoCAD (optional — only for the DXF/DWG/sheet pipeline)

Needs **full AutoCAD**, not LT: only full ships `accoreconsole.exe`.
The path is discovered automatically (newest version under
`C:\Program Files\Autodesk`), or set `ARCHPIPE_ACCORECONSOLE`.

Three traps, all hit for real, documented in `src/archpipe/acad.py`:

1. An **invalid answer to a keyword prompt** wedges the process forever
   and ignores stdin EOF. `_run()` enforces a timeout and kills the child.
2. The `-PLOT` prompt sequence **differs between Model and a named
   layout** — the layout form has no `[Center]` offset option, so the
   Model script's `C` would wedge it.
3. A **relative script path** makes accoreconsole exit 0 in under a
   second having done nothing — indistinguishable from success.

---

## 5. Environment variables

All optional; each has a discovery fallback.

| Variable | Purpose |
|---|---|
| `ARCHPIPE_ACCORECONSOLE` | path to `accoreconsole.exe` |
| `ARCHPIPE_REVIT_TEMPLATE` | Revit metric project template (`.rte`) |
| `ARCHPIPE_MODEL` | model for `extract_model.py` to open |
| `ARCHPIPE_EXTRACT_OUT` | where the extract JSON is written |
| `ARCHPIPE_TEST_MODEL` | where `build_test_model.py` saves |
| `ARCHPIPE_PROBE_OUT` | where `probe.py` writes its result |

---

## 6. Proving the move worked

Run these in order. Each is a real check, not a smoke test.

```powershell
# 1. Python side, no Autodesk needed
PYTHONPATH=src python scripts/verify.py                # ALL PASS, 53 checks

# 2. Revit reachable from the command line
$env:ARCHPIPE_PROBE_OUT="$PWD\probe.json"
& $pr run "$PWDevit\probe.py" --revit=2025    # ABSOLUTE path
#    expect api_ok true, raw_revitapi_import true, a revit_username

# 3. Build a model of KNOWN dimensions, then extract it
$env:ARCHPIPE_TEST_MODEL="$PWD\test.rvt"
& $pr run revit\build_test_model.py --revit=2025
$env:ARCHPIPE_MODEL="$PWD\test.rvt"
$env:ARCHPIPE_EXTRACT_OUT="$PWD\test.model.json"
& $pr run "$PWDevit\extract_model.py" --revit=2025
```

**The script path must be ABSOLUTE.** `pyrevit run` passes it to Revit
verbatim, Revit's working directory is not the project folder, and a
relative path produces `TaskDialog "Can not find target file. Maybe
deleted?"` in the journal while the CLI exits 0 with an empty execution
log. Nothing anywhere says the script did not run.

Step 3 is the one that matters. The builder makes a rectangle of
**6000 × 4000 mm on wall centrelines**; the extract must report wall
lengths of exactly `[4000, 4000, 6000, 6000]` and a room area of
`(6000 − t) × (4000 − t)` for the template's wall thickness `t`.

On the original machine: `t = 200 mm`, room area **22.040 m²**, matching
exactly.

**Why this check and not "did it run":** Revit's internal units are
decimal feet. A units bug does not raise — it silently produces a model
304.8× wrong that looks entirely healthy. Checking against geometry whose
truth you control is the only way to catch it.

---

## 7. The Linux workstation

Reachable as `ai-workstation` (see `~/.ssh/config`). Measured spec:
Ubuntu 24.04, 32-core Ryzen 9 9950X, 91 GB RAM, RTX 3090 24 GB, 1.2 TB
free, Docker and Python 3.12 present. Blender and Radiance are **not**
installed yet.

For the VM: AMD-V and `/dev/kvm` are present, IOMMU is already active with
36 groups, and there are **two GPUs** — the RTX 3090 plus the 9950X's
integrated graphics. That is exactly the configuration passthrough wants:
host on the iGPU, 3090 to the guest. Unverified: whether the 3090 isolates
cleanly in its own IOMMU group, and how Autodesk activation behaves inside
a VM.

---

## 8. Known unfixed

- Dashed linetypes plot **solid** through the AutoCAD layout viewport.
  Narrowed to the plot path — the same geometry renders dashed in the web
  sheet. Cause not isolated.
- SHX text plots as stroked vectors, so PDFs have no selectable text.
  One-line change to a TrueType font in `layers.py`.
- The published web review sheet is still an early version and lacks the
  markup tools (ink, highlight, arrow, measure) and in-page AI chat.
- `spec/villa-brief.yaml` and `spec/villa-site.yaml` are **placeholders**.
  Latitude in particular drives every orientation figure.
