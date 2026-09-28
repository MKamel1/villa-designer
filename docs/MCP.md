# Local Model Context Protocol tools

The Model Context Protocol (MCP) lets an assistant call typed operations
instead of reconstructing shell sequences. This server wraps the same
Python review and lighting engines used by the command-line pipeline.
No separate standards, model copy or agent arithmetic is introduced.

Install `.venv/Scripts/python -m pip install -r requirements-mcp.txt`.
Launch `.venv/Scripts/python scripts/archpipe_mcp.py` from the project.
It communicates over standard input/output; diagnostic logs use standard
error. The official Python library is pinned to the maintained 1.30 line.

| Operation | Result | Side effect |
|---|---|---|
| `project_status` | Full roadmap and last example evidence | Read only |
| `read_model` | Actual extracted geometry, finishes and markup | Read only |
| `review_model` | Cited findings, measured furniture and scope exclusions | Read only; dwelling scope is default |
| `catalogue_item` | Legacy diagnostic dimensions, source and verification status | Read only |
| `lighting_at` | Direct illuminance at a point in millimetres | Read only; no shadow or uniformity claim |
| `check_fixture_sources` | Each luminaire's measured emitter (Light Source apex or lens centre) against the spec height, and whether its IES file's opening matches the fitting | Read only; the insertion point is never the source. `passed` covers emitter height (25 mm); a photometry mismatch is reported, not failed |
| `search_books` | Full-text search over the held books and standards: printed page to cite (or EPUB section), snippet, figure-heavy flag | Read only; private index; no hit never means no rule |
| `lookup_book_term` | The dictionary: back-of-book index entries across every held book | Read only |
| `book_page` | Read held pages by PDF page, optionally rendering the page image for drawings | Read only; image written to the private store |
| `search_products` | Search the product library beyond luminaires (surfaces, fabrics, furniture, decor, plants): verified rows by default, with each check's passed / failed / not_checkable state | Read only; an appearance asset standing for a product is a look-alike-proxy unless linked |
| `search_luminaires` | Search real manufacturer luminaires: the verified library (pickable, figures from the LDT) or the wider catalogue with market availability (EG, AE, SA, GB) | Read only; catalogue rows are unverified until their files are imported |
| `propose_luminaires` | Two widely available products from different ranges for one lighting role, each confirmed live, or the constraint that excluded them | Reads one allowed product page per candidate; never downloads |
| `luminaire_alternates` | Verified replacements for a product: same mount and colour temperature, at least its CRI, flux within tolerance | Read only |
| `luminaire_download_links` | The manufacturer's own LDT/IES/Revit links for one product, for a person to open | Read only; never downloads (file servers may disallow automated access) |
| `check_render` | Automatic checks on a presentation render (window view, daylight through glass, photometry bound, level camera, colour cast, clipping, CAD colours, textiles, cloth) | Read only; passing means no *known* defect, so still look at the image |
| `propose_example_edit` | Before/after placement and invalidated stages | Writes a candidate under `out/proposals`; does not change current design |
| `run_bedroom_example` | Complete structured acceptance evidence | Rebuilds generated example outputs locally and renders on configured workstation |
| `run_workstation_job` | Compact result, reuse count, artifact directory and failures | Runs a bounded Ubuntu verification, view batch, bedroom proof, benchmark, parameter sweep or Radiance simulation |

`archpipe://method`, `archpipe://learnings` and `archpipe://compute` expose
the shared method, learning index and measured compute placement.
Model/file arguments stay inside the project root; there
is no arbitrary command tool. Rebuild is explicitly marked as a write
operation. Existing session authority still governs when it may be used.

`read_model` returns mesh counts and material names by default, alongside
measured dimensions and placement. Request `include_meshes=true` only when
coordinates are necessary; rendering consumes the referenced extract file
directly. `project_status` returns compact example evidence and whether it
still matches local inputs/artifacts; a read-only status call does not
probe the remote runtime.

## Fewer steps, with evidence

The normal rebuild is one tool call. `resume=true` is the default: reuse
only when input and artifact content hashes agree. A partial run can reuse
verified Revit output, while changed code/specification invalidates its
dependent stages. An exclusive lock prevents two writers. Failures return
the failed operation, logs and a failed acceptance record; never an old
success flag for a completed failing pipeline. A tool exception or nonzero
exit is a failed invocation, even if a previous acceptance file remains.
`scripts/run_bedroom.py --resume` provides the same behavior
without MCP.

The reuse check covers recorded project code, specification, generated
artifacts and the actual remote runtime. Worker manifests include application
binary hashes, Python packages, graphics driver and photometric assets.
Each job verifies its output hashes before reuse; failed or modified outputs
are recomputed in a fresh attempt directory. Documentation changes do not
invalidate otherwise identical render jobs. See [worker operations](ops/workstation-jobs.md)
for setup, bounds, locking and benchmark evidence.

Run `scripts/test_mcp.py` to launch an actual client/server session, list
tools, read resources, exercise rules and check negative inputs. Run
`scripts/test_mcp.py --cached-run` after a successful pipeline run to check
the actual reuse operation with a 30-second response deadline. The test
rejects stale prerequisites rather than accidentally starting a rebuild.
Noninteractive child processes must not inherit the protocol input pipe.
Use `scripts/test_mcp.py --worker-batch` to exercise an actual three-view
Ubuntu batch through the same protocol; it may render when no matching
cache exists. This is separate from the native-model reuse test.
Run
`scripts/sync_agent_assets.py --check` to catch workflow adapter drift.

Project-local connection files are generated by
`scripts/configure_assistants.py`. They use this checkout's interpreter;
regenerate them after moving machines. New sessions must load the project
configuration. The current assistant session is not hot-attached merely
because these files exist.

## Integration boundary

The local server is separate from Autodesk Assistant's private MCP
implementation. `AddCustomServer` was discovered, but registration and
entitlements are not established. See
[the measured inventory](reference/revit-2027-mcp.md). Do not claim that
Revit's built-in Assistant is connected until a real call succeeds.

References: [official Python library](https://py.sdk.modelcontextprotocol.io/v1/),
[MCP server guidance](https://modelcontextprotocol.io/docs/develop/build-server),
[project skill discovery](https://learn.chatgpt.com/docs/build-skills),
[Codex agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Expert guidance operations

`stage_context(stage, project_path)` returns scoped project facts, decisions, missing inputs, evidence and deliverables. `lookup_evidence(query, stage, project_path, limit)` retrieves provenance-bearing paraphrases and precedent analysis. `review_stage(stage, project_path)` combines deterministic diagnostics and explicit qualitative review, source gaps, artifact freshness and client approval status. All are read-only; stages retain numbers 0 through 7. The default project is a fictional pilot. See [guidance records and limits](guidance/README.md). Numerical catalogue claims are unverified legacy diagnostics, not established published requirements.

## Whole-villa render operations (current command boundary)

The villa renderer is a sequence of one-command operations sharing the
`villa-render/1` scene contract. These are **command-line operations**:
`scripts/archpipe_mcp.py` does not currently expose named villa render
tools. Do not advertise them as callable Model Context Protocol operations
until wrappers and a live client/server test exist. See
[the scene contract](villa-render-scene.md), [ADR-0013](decisions/ADR-0013-presentation-renders.md)
for the current contract and review boundary.

| Operation | Command from repository root | Evidence and resume |
|---|---|---|
| Build scene | `PYTHONPATH=src .venv/Scripts/python.exe -c "from archpipe.concept import villa_render; print(villa_render.write()[0])"` | Writes the current D1 `out/villa/render-d1/scene.json`; rerun after layout, furniture, lighting, finish or view changes. The exporter defaults and mappings are still D1-specific. |
| Check views | `PYTHONPATH=src .venv/Scripts/python.exe scripts/villa_render_views.py` | Writes `views-plan.png`; exits nonzero for a subject footprint outside frame, camera collision or invalid doorway setup. Currently reads D1 layout and path. |
| Render draft | `PYTHONPATH=src .venv/Scripts/python.exe scripts/villa_render.py --scene out/villa/render-d1/scene.json --views review --samples 256 --res 960x640` (`review` = every view not marked final-only) | Driver validates the contract, deploys, fetches images and reports, runs applicable `render_qa`, writes captions. Inspect every image. |
| Render final | `PYTHONPATH=src .venv/Scripts/python.exe scripts/villa_render.py --scene out/villa/render-d1/scene.json --views all --samples 1024 --res 1920x1280` | Same checks and captions at the recorded final settings; visual critic review is still required. |
| Measure scene lighting | `PYTHONPATH=src .venv/Scripts/python.exe scripts/villa_render.py --views none --measure-lighting` | Fetches `lighting-measurements.json`; compare with the analytical design and remeasure after fixture moves. |
| Build review page | `PYTHONPATH=src .venv/Scripts/python.exe scripts/villa_review_page.py` | Current D1 page at `out/villa/render-d1/review/index.html`; reads render reports, captions, quality checks and measured lighting/daylight. It is not itself a design approval. |

For draft, final and lighting jobs, the driver hashes scene content,
renderer code, referenced photometry files and run options into a job
identifier. An identical rerun resumes the detached job or retrieves its
completed artifacts after a connection loss; changing inputs starts a new
job. The driver rejects a missing artifact and uses Blender's nonzero Python
exit code. A successful process or reused job is execution evidence only:
check the contract, the render quality reports, images and captions before
review or publication. The scene exporter, view checker and review page still
contain D1 paths and design identifiers; generalise those boundaries and test
another layout before offering a generic one-call MCP operation.
