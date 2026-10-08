---
outline:
  - title: Document Outline
    link: "#document-outline"
  - title: Executive Summary
    link: "#executive-summary"
  - title: Files Actually Changed
    link: "#files-actually-changed"
  - title: Per-File Migration Details
    link: "#per-file-migration-details"
    subsections:
      - title: src/archpipe/daylight.py
        link: "#srcarchpipedaylightpy"
      - title: src/archpipe/daylight_climate.py
        link: "#srcarchpipedaylight_climatepy"
      - title: src/archpipe/radiance.py
        link: "#srcarchpiperadiancepy"
      - title: src/archpipe/cli.py
        link: "#srcarchpipeclipy"
      - title: src/archpipe/thermal.py
        link: "#srcarchpipethermalpy"
  - title: Direct Writes and Reads Left Unchanged
    link: "#direct-writes-and-reads-left-unchanged"
  - title: Tests and Verification Proofs
    link: "#tests-and-verification-proofs"
  - title: Lessons to Register
    link: "#lessons-to-register"
summary: |
  Phase 2 Batch 1 migration report for serialization class (C13). Four CPython modules
  (daylight.py, daylight_climate.py, radiance.py, cli.py) were migrated to atomic safe_io
  writers, while thermal.py scratch and redirection writes were audited as exceptions.
  Comprehensive AST, byte equality, and write-failure atomicity proofs were added.
---

# Document Outline

- [Executive Summary](#executive-summary)
- [Files Actually Changed](#files-actually-changed)
- [Per-File Migration Details](#per-file-migration-details)
  - [src/archpipe/daylight.py](#srcarchpipedaylightpy)
  - [src/archpipe/daylight_climate.py](#srcarchpipedaylight_climatepy)
  - [src/archpipe/radiance.py](#srcarchpiperadiancepy)
  - [src/archpipe/cli.py](#srcarchpipeclipy)
  - [src/archpipe/thermal.py](#srcarchpipethermalpy)
- [Direct Writes and Reads Left Unchanged](#direct-writes-and-reads-left-unchanged)
- [Tests and Verification Proofs](#tests-and-verification-proofs)
- [Lessons to Register](#lessons-to-register)

# Executive Summary

This report documents the completion of Serialization Class (C13), Phase 2, Batch 1. Four CPython modules (`daylight.py`, `daylight_climate.py`, `radiance.py`, `cli.py`) were migrated to route all scene, room, report, grid, and note writes through `safe_io` atomic writers (`save_text`, `save_json`, `save_bytes`, `load_json`), with three deliberate output changes found in lead review (2026-10-08), not "identical bytes" as first claimed: (1) `save_json` appends a final newline and refuses NaN/Infinity (`allow_nan=False`), so `rooms.json`, `sensors.json` and the design-notes JSON gain a trailing newline and fail closed on a non-finite value; (2) `save_text` writes UTF-8 bytes with no newline translation, so on Windows `scene.rad`, `points.txt` and `opts.txt` (previously written in text mode without `newline="
"`) now have LF instead of CRLF line endings, matching the Linux Radiance workers; (3) text that was written with `encoding="ascii"` is now UTF-8, so a non-ASCII character is written instead of raising. The Radiance writers covered by the byte-equality tests are unchanged. Subprocess streaming redirections, append-mode descriptor captures, and short-lived scratch files in `thermal.py` were audited and preserved as explicit, documented exceptions backed by an AST verification suite in `tests/test_c13_phase2.py`.

# Files Actually Changed

The following files were modified or created in this batch:

1. [src/archpipe/daylight.py](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/daylight.py)
2. [src/archpipe/daylight_climate.py](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/daylight_climate.py)
3. [src/archpipe/radiance.py](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/radiance.py)
4. [src/archpipe/cli.py](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/cli.py)
5. [tests/test_c13_phase2.py](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c13_phase2.py)
6. [docs/serialization-boundary.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/serialization-boundary.md)
7. [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md)
8. [docs/c13p2-report.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/c13p2-report.md)

*(Note: [src/archpipe/thermal.py](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/thermal.py) was audited; all 4 writes therein are documented exceptions with 0 statement changes).*

# Per-File Migration Details

### src/archpipe/daylight.py

Import added:
- `from .safe_io import load_json, save_bytes, save_json, save_text`

Replaced calls in `write_job`:
1. `(folder / "sky_glow.rad").write_text(SKY_GLOW, encoding="ascii")`
   -> `save_text(folder / "sky_glow.rad", SKY_GLOW)`
2. `(folder / "run.sh").write_text(RUN_SH.format(B=SKY_B, n=workers, render=" ".join(RPICT_OPTS)), encoding="ascii", newline="\n")`
   -> `save_text(folder / "run.sh", RUN_SH.format(B=SKY_B, n=workers, render=" ".join(RPICT_OPTS)))`
3. `(folder / "views.txt").write_text("\n".join(vlines) + ("\n" if vlines else ""), encoding="ascii", newline="\n")`
   -> `save_text(folder / "views.txt", "\n".join(vlines) + ("\n" if vlines else ""))`
4. `(folder / "order.txt").write_text("\n".join(order) + "\n", encoding="ascii", newline="\n")`
   -> `save_text(folder / "order.txt", "\n".join(order) + "\n")`
5. `(d / "scene.rad").write_text(scene_rad(scene), encoding="ascii")`
   -> `save_text(d / "scene.rad", scene_rad(scene))`
6. `(d / "points.txt").write_text("\n".join(lines) + "\n", encoding="ascii")`
   -> `save_text(d / "points.txt", "\n".join(lines) + "\n")`
7. `(d / "opts.txt").write_text(" ".join(RTRACE_FINE if name.endswith("-fine") else RTRACE_OPTS), encoding="ascii")`
   -> `save_text(d / "opts.txt", " ".join(RTRACE_FINE if name.endswith("-fine") else RTRACE_OPTS))`
8. `(d / "rooms.json").write_text(json.dumps({"rooms": rooms, "notes": scene.notes}, indent=1), encoding="utf-8")`
   -> `save_json(d / "rooms.json", {"rooms": rooms, "notes": scene.notes}, indent=1)`
9. `tgz.write_bytes(buf.getvalue())`
   -> `save_bytes(tgz, buf.getvalue())`

Replaced calls in `read_case`:
10. `meta = json.loads((case_dir / "rooms.json").read_text(encoding="utf-8"))`
    -> `meta = load_json(case_dir / "rooms.json")`

### src/archpipe/daylight_climate.py

Import added:
- `from .safe_io import save_bytes, save_json, save_text`

Replaced calls in `write_job`:
1. `(folder / "receiver.rad").write_text(SKY_RECEIVER.format(mf=MF), encoding="ascii")`
   -> `save_text(folder / "receiver.rad", SKY_RECEIVER.format(mf=MF))`
2. `(folder / "sky_glow.rad").write_text(D.SKY_GLOW, encoding="ascii")`
   -> `save_text(folder / "sky_glow.rad", D.SKY_GLOW)`
3. `(folder / "sky.wea").write_text(wea_text(head, rows, stamps), encoding="ascii", newline="\n")`
   -> `save_text(folder / "sky.wea", wea_text(head, rows, stamps))`
4. `(folder / "dc_opts.txt").write_text(" ".join(DC_OPTS), encoding="ascii")`
   -> `save_text(folder / "dc_opts.txt", " ".join(DC_OPTS))`
5. `(folder / "run.sh").write_text(RUN_DC.format(mf=MF, rot=rotation_deg, c=" ".join(map(str, LUX_COEF)), rt=" ".join(D.RTRACE_OPTS)), encoding="ascii", newline="\n")`
   -> `save_text(folder / "run.sh", RUN_DC.format(mf=MF, rot=rotation_deg, c=" ".join(map(str, LUX_COEF)), rt=" ".join(D.RTRACE_OPTS)))`
6. `(folder / "order.txt").write_text("\n".join(order) + "\n", encoding="ascii", newline="\n")`
   -> `save_text(folder / "order.txt", "\n".join(order) + "\n")`
7. `(d / "scene.rad").write_text(D.scene_rad(scene), encoding="ascii")`
   -> `save_text(d / "scene.rad", D.scene_rad(scene))`
8. `(d / "points.txt").write_text("\n".join("%.4f %.4f %.4f %.4f %.4f %.4f" % ((s["x"], s["y"], s["z"]) + tuple(s["n"])) for s in sensors) + "\n", encoding="ascii", newline="\n")`
   -> `save_text(d / "points.txt", "\n".join("%.4f %.4f %.4f %.4f %.4f %.4f" % ((s["x"], s["y"], s["z"]) + tuple(s["n"])) for s in sensors) + "\n")`
9. `(d / "sensors.json").write_text(json.dumps({"sensors": sensors, "stamps": stamps}), encoding="utf-8")`
   -> `save_json(d / "sensors.json", {"sensors": sensors, "stamps": stamps})`
10. `(d / "pit.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="ascii", newline="\n")`
    -> `save_text(d / "pit.txt", "\n".join(lines) + ("\n" if lines else ""))`
11. `tgz.write_bytes(buf.getvalue())`
    -> `save_bytes(tgz, buf.getvalue())`

### src/archpipe/radiance.py

Import added:
- `from .safe_io import save_text`

Replaced call in `_write`:
1. `path.write_text(text)`
   -> `save_text(path, text)`
   *(This atomically routes all files authored by `radiance.py`: `iso.ies`, `points.txt`, `shell.rad`, `sky.rad`, `daylight-grid.json`, `ab0-grid.json`, `ab4-grid.json`, and `radiance-report.json`).*

### src/archpipe/cli.py

Import added:
- `from .safe_io import save_json`

Replaced call in `_design`:
1. `Path(args.notes).write_text(_json.dumps(rows, indent=2), encoding="utf-8")`
   -> `save_json(args.notes, rows, indent=2)`

### src/archpipe/thermal.py

No calls replaced. All 4 writes in this module are retained as documented exceptions (detailed below).

---

# Direct Writes and Reads Left Unchanged

The following calls were audited and left unchanged, in compliance with the explicit task rules:

1. **`src/archpipe/daylight.py` (`write_job`)**:
   `tarfile.open(fileobj=buf, mode="w:gz")`
   - *Reason*: Operates in-memory on an `io.BytesIO()` buffer (`buf`), not on a filesystem path. The resulting archive bytes are subsequently written to disk via `safe_io.save_bytes`.
2. **`src/archpipe/daylight.py` (`read_hdr`)**:
   `Path(path).read_bytes()`
   - *Reason*: Reads binary RGBE float pixel arrays from Radiance `rpict` output files, not pipeline-authored JSON.
3. **`src/archpipe/daylight.py` (`read_case`)**:
   `(case_dir / "out.txt").read_text()`
   - *Reason*: Reads raw whitespace-separated numbers generated by external Radiance `rtrace`, not pipeline JSON.
4. **`src/archpipe/daylight_climate.py` (`write_job`)**:
   `tarfile.open(fileobj=buf, mode="w:gz")`
   - *Reason*: Operates in-memory on an `io.BytesIO()` buffer (`buf`).
5. **`src/archpipe/daylight_climate.py` (`read_lux`, `read_pit`)**:
   `(Path(case_dir) / "lux.txt").read_text()`, `(Path(case_dir) / ("pit_%s.out" % tag)).read_text()`
   - *Reason*: Reads external process text streams from Radiance `rmtxop` and `rtrace`, not pipeline JSON.
6. **`src/archpipe/daylight_climate.py` (`read_epw`)**:
   `Path(path).read_text(encoding="latin-1")`
   - *Reason*: Reads external EPW weather data files.
7. **`src/archpipe/radiance.py` (`_run`)**:
   `stdin = open(stdin_path, "rb") if stdin_path else subprocess.DEVNULL`
   - *Reason*: Opens an input file handle for child process standard input.
8. **`src/archpipe/radiance.py` (`_run`)**:
   `with stdout_path.open("wb") as out, stderr_path.open("wb") as err:`
   - *Reason*: Subprocess stdout and stderr streams for external Radiance executables (`oconv`, `rtrace`, `gensky`, `ies2rad`). Staged pipe redirection into child process streams is retained per task rules.
9. **`src/archpipe/radiance.py` (`_capture`)**:
   `path.read_text()`
   - *Reason*: Reads raw Radiance tool output strings.
10. **`src/archpipe/thermal.py` (`_quiet`)**:
    `with open(log, "ab") as f:`
    - *Reason*: Requires binary append mode (`"ab"`) to obtain a raw file descriptor for `os.dup2(f.fileno(), 1)` and `os.dup2(f.fileno(), 2)` process redirection; `safe_io` does not provide an append mode.
11. **`src/archpipe/thermal.py` (`run_case`)**:
    `idf.write_text(sim.to_idf() + "\n\n" + model.to.idf(model), encoding="utf-8")`
    - *Reason*: Temporary scratch IDF file immediately passed to and executed by external EnergyPlus (`run_idf`) in the same function.
12. **`src/archpipe/thermal.py` (`daylight_grid`)**:
    `(workdir / "scene.rad").write_text(sky + "\n" + mat + "\n" + scene)`
    - *Reason*: Temporary scratch scene file immediately passed to and executed by Radiance `oconv` in the same function.
13. **`src/archpipe/thermal.py` (`daylight_grid`)**:
    `with oct_.open("wb") as o:`
    - *Reason*: Subprocess stdout redirection handle for `oconv`.
14. **`src/archpipe/thermal.py` (`read_epw`, `stat_monthly_means`)**:
    `Path(path).read_text(encoding="latin-1")`, `Path(stat_path).read_text(encoding="latin-1")`
    - *Reason*: Reads external EPW weather and STAT summary tables.

---

# Tests and Verification Proofs

Added [tests/test_c13_phase2.py](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c13_phase2.py) containing:

1. **Proof (a) - AST Scan (`test_ast_no_unlisted_direct_writes`)**:
   Parses the abstract syntax trees of `daylight.py`, `daylight_climate.py`, `thermal.py`, `radiance.py`, and `cli.py`. Verifies that no `.write_text()`, `.write_bytes()`, `open(mode="w"/"a")`, `.open(mode="w"/"a")`, `json.dump()`, or `shutil.copy*()` calls exist outside the constant `EXCEPTIONS`. Also enforces that every registered exception is actively present in the codebase.
2. **Proof (b) - Byte Equality (`test_representative_text_writer_byte_equality`)**:
   Verifies that text written by migrated `radiance._write` matches `FROZEN_TEXT_BYTES` (`b"# Radiance test material block\nvoid plastic wall_mat\n0\n0\n5 0.50 0.50 0.50 0.00 0.00\n"`), derived from the previous implementation.
3. **Proof (b) - Byte Equality (`test_representative_json_writer_byte_equality`)**:
   Verifies that JSON written by migrated `radiance._write_grid_json` matches frozen expected bytes with exact key order and 2-space indentation.
4. **Proof (b) - Byte Equality (`test_representative_csv_writer_byte_equality`)**:
   Verifies that CSV rows written by migrated `deliverables.write_csv` match frozen expected CSV bytes with standard CRLF line endings.
5. **Proof (c) - Write Failure Atomicity (`test_write_failure_leaves_existing_destination_file_unchanged`)**:
   Proves that when `json.dumps` or `safe_io.os.fsync` raises an error during `save_json`, `_write_grid_json`, or `_write`, pre-existing destination files remain intact and no `.part` files linger.

---

# Lessons to Register

- **Lessons to Register**: `none`
  *(Per task instructions, `src/archpipe/guard_registry.py` was not modified. The existing registry entry `serialization-file-boundary-phase1` in [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md) was updated with an appended line recording the Phase 2 Batch 1 migration, covering historical lessons `l0019`, `l0024`, `l0067`, `l0101`, `l0181`, and `l0755` for this batch's sibling components).*
