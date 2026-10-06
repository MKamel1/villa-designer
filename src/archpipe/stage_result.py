"""Atomic stage-result contract and proof of completeness for pipeline stages.

Pattern: A stage reports success, or a later stage consumes an output,
without proof that the output is complete, current, and produced by this run.

Every stage writes a result record atomically (safe_io) with:
1. Inputs' content hashes (SHA-256) and sizes.
2. Code provenance (source hash, git HEAD, git dirty state).
3. Outputs' content hashes (SHA-256) and sizes.
4. Exit status (exit_code and status 'ok'/'fail').
5. Completeness check (all expected outputs present and non-empty).

A consumer must validate the record (fresh inputs, complete outputs, status ok)
before using outputs; any mismatch fails closed with the reason.
A script whose report says FAIL must exit non-zero (shared fail_closed helper).

Quick Test:
    from pathlib import Path
    import tempfile
    from archpipe.stage_result import write_stage_result, validate_stage_result

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        inp = p / "in.txt"
        inp.write_text("hello", encoding="utf-8")
        out = p / "out.txt"
        out.write_text("world", encoding="utf-8")
        rec = p / "stage.json"
        res = write_stage_result("demo", record_path=rec, inputs=[inp], outputs=[out])
        assert validate_stage_result(rec)[0] is True
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]
from archpipe.safe_io import load_json, save_json


class StageResultError(RuntimeError):
    """Base error for stage result contract violations."""


class StaleInputError(StageResultError):
    """Stage inputs are stale, modified, or missing."""


StaleStageError = StaleInputError


class IncompleteOutputError(StageResultError):
    """Stage outputs are missing, empty, or modified."""


class FailedStageError(StageResultError):
    """Stage reported failure or non-zero exit code."""


class CodeDriftError(StageResultError):
    """Code provenance does not match current repository code."""


def digest_file(path: Path | str) -> tuple[str, int]:
    """Return (sha256_hex, size_bytes) for a file.

    Raises FileNotFoundError if the file does not exist.
    """
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    h = hashlib.sha256()
    size = 0
    with p.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
            size += len(block)
    return h.hexdigest(), size


def compute_code_provenance(
    root: Path | str | None = None,
    code_paths: Iterable[Path | str] | None = None,
) -> dict:
    """Identify the source and repository provenance from which a stage executes.

    Follows the scene provenance hash pattern from archpipe.concept.villa_render.
    """
    root_path = Path(root or ROOT).resolve()
    if code_paths is None:
        inputs = sorted((root_path / "src/archpipe").rglob("*.py"))
        for extra in (
            "ops/workstation/library-manifest.json",
            "out/villa/round3/plant-palette.json",
            "spec/villa-site.yaml",
            "knowledge/library.json",
            "knowledge/projects/villa-01/brief-requirements.json",
            "knowledge/projects/villa-01/taste.json",
        ):
            target = root_path / extra
            if target.is_file():
                inputs.append(target)
    else:
        inputs = []
        for p in code_paths:
            resolved = Path(p) if Path(p).is_absolute() else root_path / p
            if resolved.is_file():
                inputs.append(resolved)
    h = hashlib.sha256()
    for path in sorted(inputs, key=lambda p: p.relative_to(root_path).as_posix()):
        if not path.is_file():
            continue
        name = path.relative_to(root_path).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(name).to_bytes(4, "big") + name)
        h.update(len(data).to_bytes(8, "big") + data)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root_path, capture_output=True, text=True)
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root_path, capture_output=True, text=True,
    )
    return {
        "source_hash": h.hexdigest(),
        "git_head": head.stdout.strip() if head.returncode == 0 else None,
        "git_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def _rel_path(path: Path | str, root: Path) -> str:
    p = Path(path).resolve()
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def build_file_manifest(
    paths: Iterable[Path | str],
    root: Path | None = None,
    require_exists: bool = True,
) -> dict[str, dict]:
    root_path = Path(root or ROOT).resolve()
    manifest = {}
    for p in sorted(paths, key=lambda x: str(x)):
        resolved = Path(p) if Path(p).is_absolute() else (root_path / p).resolve()
        key = _rel_path(resolved, root_path)
        if not resolved.is_file():
            if require_exists:
                raise FileNotFoundError(f"Required artifact does not exist: {resolved}")
            manifest[key] = {
                "path": str(resolved),
                "sha256": None,
                "size_bytes": 0,
                "exists": False,
            }
            continue
        sha, size = digest_file(resolved)
        manifest[key] = {
            "path": str(resolved),
            "sha256": sha,
            "size_bytes": size,
            "exists": True,
        }
    return manifest


def evaluate_completeness(
    expected_outputs: Iterable[Path | str],
    output_manifest: dict[str, dict],
    root: Path | None = None,
) -> dict:
    root_path = Path(root or ROOT).resolve()
    expected_keys = [_rel_path(p, root_path) for p in expected_outputs]
    missing = []
    empty = []
    for key in expected_keys:
        info = output_manifest.get(key)
        if not info or not info.get("exists", False):
            missing.append(key)
        elif (info.get("size_bytes") or 0) <= 0:
            empty.append(key)
    complete = len(missing) == 0 and len(empty) == 0
    return {
        "complete": complete,
        "expected_outputs": expected_keys,
        "missing_outputs": missing,
        "empty_outputs": empty,
    }


def write_stage_result(
    stage: str,
    *,
    record_path: Path | str,
    outputs: Iterable[Path | str],
    inputs: Iterable[Path | str] = (),
    expected_outputs: Iterable[Path | str] | None = None,
    exit_code: int = 0,
    status: str | None = None,
    root: Path | str | None = None,
    code_paths: Iterable[Path | str] | None = None,
    metadata: dict | None = None,
    started_utc: str | None = None,
    finished_utc: str | None = None,
) -> dict:
    """Atomically record the completed stage result, hashes, provenance, and completeness."""
    root_path = Path(root or ROOT).resolve()
    target_record = Path(record_path) if Path(record_path).is_absolute() else (root_path / record_path).resolve()
    target_record.parent.mkdir(parents=True, exist_ok=True)

    # Filter out target_record itself if callers passed it in outputs;
    # a stage result cannot record its own SHA-256 before being written to disk.
    def _is_target_record(p: Path | str) -> bool:
        res = Path(p) if Path(p).is_absolute() else (root_path / p).resolve()
        return res == target_record

    clean_outputs = [p for p in outputs if not _is_target_record(p)]
    if expected_outputs is None:
        clean_expected = clean_outputs
    else:
        clean_expected = [p for p in expected_outputs if not _is_target_record(p)]

    input_manifest = build_file_manifest(inputs, root=root_path, require_exists=True)
    output_manifest = build_file_manifest(clean_outputs, root=root_path, require_exists=False)

    completeness = evaluate_completeness(clean_expected, output_manifest, root=root_path)

    # Determine status and exit code
    if not completeness["complete"] and exit_code == 0:
        exit_code = 1
    if status is None:
        status = "ok" if (exit_code == 0 and completeness["complete"]) else "fail"
    elif not completeness["complete"] and status == "ok":
        status = "fail"

    provenance = compute_code_provenance(root_path, code_paths=code_paths)

    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = {
        "_metadata": {
            "description": f"Atomic stage result record for pipeline stage '{stage}'",
            "structure": "stage, status, exit_code, code_provenance, inputs, outputs, completeness, metadata",
            "total_items": len(output_manifest),
            "last_updated": now_utc,
        },
        "schema": "stage-result/1",
        "stage": stage,
        "status": status,
        "exit_code": exit_code,
        "started_utc": started_utc or now_utc,
        "finished_utc": finished_utc or now_utc,
        "code_provenance": provenance,
        "inputs": input_manifest,
        "outputs": output_manifest,
        "completeness": completeness,
        "metadata": metadata or {},
    }
    save_json(target_record, record, indent=2)
    return record


def validate_stage_result(
    record_or_path: dict | Path | str,
    *,
    root: Path | str | None = None,
    current_inputs: Iterable[Path | str] | None = None,
    check_code_provenance: bool = False,
    raise_on_error: bool = True,
) -> tuple[bool, str, dict]:
    """Validate that a stage result is fresh, complete, and successful.

    Fails closed with specific error if:
    1. Expected outputs are missing, 0 bytes, or modified (IncompleteOutputError).
    2. Input files have changed or are missing (StaleInputError / StaleStageError).
    3. Code provenance changed when check_code_provenance=True (CodeDriftError).
    4. The stage status is not 'ok' or exit_code != 0 (FailedStageError).
    """
    root_path = Path(root or ROOT).resolve()
    if isinstance(record_or_path, (str, Path)):
        rec_path = Path(record_or_path) if Path(record_or_path).is_absolute() else (root_path / record_or_path).resolve()
        if not rec_path.is_file():
            reason = f"Stage result record does not exist: {rec_path}"
            if raise_on_error:
                raise IncompleteOutputError(reason)
            return False, reason, {}
        record = load_json(rec_path)
    else:
        record = record_or_path

    stage_name = record.get("stage", "unnamed_stage")

    # 1. Completeness check
    completeness = record.get("completeness", {})
    if not completeness.get("complete", False):
        missing = completeness.get("missing_outputs", [])
        empty = completeness.get("empty_outputs", [])
        reason = f"Stage '{stage_name}' record is incomplete (missing: {missing}, empty: {empty})"
        if raise_on_error:
            raise IncompleteOutputError(reason)
        return False, reason, record

    outputs = record.get("outputs", {})
    for rel_path, out_info in outputs.items():
        expected_path = Path(out_info.get("path")) if out_info.get("path") else (root_path / rel_path)
        if not expected_path.is_file():
            reason = f"Stage '{stage_name}' output is missing on disk: {rel_path}"
            if raise_on_error:
                raise IncompleteOutputError(reason)
            return False, reason, record
        cur_sha, cur_size = digest_file(expected_path)
        if cur_size == 0:
            reason = f"Stage '{stage_name}' output is empty (0 bytes) on disk: {rel_path}"
            if raise_on_error:
                raise IncompleteOutputError(reason)
            return False, reason, record
        if cur_sha != out_info.get("sha256"):
            reason = (
                f"Stage '{stage_name}' output was modified on disk: {rel_path} "
                f"(recorded SHA: {out_info.get('sha256')}, current: {cur_sha})"
            )
            if raise_on_error:
                raise IncompleteOutputError(reason)
            return False, reason, record

    # 2. Input freshness check
    inputs = record.get("inputs", {})
    for rel_path, in_info in inputs.items():
        inp_path = Path(in_info.get("path")) if in_info.get("path") else (root_path / rel_path)
        if not inp_path.is_file():
            reason = f"Stage '{stage_name}' input missing on disk: {rel_path}"
            if raise_on_error:
                raise StaleInputError(reason)
            return False, reason, record
        cur_sha, _ = digest_file(inp_path)
        if cur_sha != in_info.get("sha256"):
            reason = (
                f"Stage '{stage_name}' input is stale / modified: {rel_path} "
                f"(recorded SHA: {in_info.get('sha256')}, current: {cur_sha})"
            )
            if raise_on_error:
                raise StaleInputError(reason)
            return False, reason, record

    # Check additional consumer-specified inputs if provided
    if current_inputs is not None:
        for p in current_inputs:
            rel = _rel_path(p, root_path)
            if rel not in inputs:
                reason = f"Stage '{stage_name}' was not executed with required input: {rel}"
                if raise_on_error:
                    raise StaleInputError(reason)
                return False, reason, record
            inp_path = (root_path / rel).resolve()
            if not inp_path.is_file():
                reason = f"Current input missing on disk: {rel}"
                if raise_on_error:
                    raise StaleInputError(reason)
                return False, reason, record
            cur_sha, _ = digest_file(inp_path)
            if cur_sha != inputs[rel].get("sha256"):
                reason = f"Current input differs from stage record: {rel}"
                if raise_on_error:
                    raise StaleInputError(reason)
                return False, reason, record

    # 3. Code provenance check (optional)
    if check_code_provenance:
        prov = record.get("code_provenance", {})
        current_prov = compute_code_provenance(root_path)
        if prov.get("source_hash") != current_prov.get("source_hash"):
            reason = (
                f"Stage '{stage_name}' code provenance mismatch: "
                f"recorded source hash {prov.get('source_hash')} != current {current_prov.get('source_hash')}"
            )
            if raise_on_error:
                raise CodeDriftError(reason)
            return False, reason, record

    # 4. Exit status and success check (specific reasons above take precedence)
    exit_code = record.get("exit_code", 0)
    status = record.get("status", "unknown")
    if exit_code != 0 or status != "ok":
        reason = f"Stage '{stage_name}' failed with exit code {exit_code} (status: {status})"
        if raise_on_error:
            raise FailedStageError(reason)
        return False, reason, record

    return True, "ok", record


def report_has_failure(report_or_verdict) -> tuple[bool, list[str]]:
    """Inspect a report, verdict, text or object and determine if it indicates failure.

    Returns (has_failure: bool, reasons: list[str]).
    """
    if report_or_verdict is None:
        return False, []
    if isinstance(report_or_verdict, bool):
        return (not report_or_verdict, ["Boolean verdict was False"] if not report_or_verdict else [])
    if isinstance(report_or_verdict, (int, float)):
        bad_count = int(report_or_verdict)
        return (bad_count > 0, [f"Failure count is {bad_count}"] if bad_count > 0 else [])
    if isinstance(report_or_verdict, str):
        if (
            re.search(r"\b(FAIL|FAILED)\b", report_or_verdict)
            or "VERDICT: FAIL" in report_or_verdict
            or "QA FAIL" in report_or_verdict
        ):
            return True, [f"Report text contains failure: {report_or_verdict.strip()[:200]}"]
        return False, []
    if isinstance(report_or_verdict, (list, tuple)):
        reasons = []
        for item in report_or_verdict:
            sub_fail, sub_reasons = report_has_failure(item)
            if sub_fail:
                reasons.extend(sub_reasons)
        return len(reasons) > 0, reasons
    if isinstance(report_or_verdict, dict):
        reasons = []
        if report_or_verdict.get("passed") is False:
            reasons.append("Field 'passed' is False")
        if report_or_verdict.get("exit_code", 0) != 0:
            reasons.append(f"Field 'exit_code' is non-zero ({report_or_verdict.get('exit_code')})")
        status = report_or_verdict.get("status")
        if status in ("FAIL", "FAILED", "fail", "failed", "DIAGNOSTIC", "error"):
            reasons.append(f"Status is '{status}'")
        failures = report_or_verdict.get("failures")
        if failures:
            reasons.append(f"Failures reported: {failures}")
        failed = report_or_verdict.get("failed")
        if failed:
            reasons.append(f"Failed items reported: {failed}")
        for chk in report_or_verdict.get("checks", []):
            if isinstance(chk, dict):
                if chk.get("passed") is False or chk.get("status") == "FAIL" or chk.get("pass") is False:
                    reasons.append(f"Check failed: {chk.get('check', chk)}")
        for v in report_or_verdict.get("verdicts", []):
            if isinstance(v, dict):
                if v.get("pass") is False or v.get("passed") is False or v.get("status") == "FAIL":
                    reasons.append(f"Verdict failed: {v.get('check', v)}")
        return len(reasons) > 0, reasons

    return False, []


def enforce_clean_verdict(
    report_or_verdict,
    *,
    message: str = "Stage report indicates FAIL",
    exit_code: int = 1,
) -> int:
    """Exit non-zero if the report or verdict contains any FAIL.

    Shared fail-closed helper preventing l0029 (script printing FAIL but returning 0).
    Returns 0 if clean.
    """
    failed, reasons = report_has_failure(report_or_verdict)
    if failed:
        detail = "; ".join(reasons) if reasons else message
        print(f"FAIL: {message} ({detail})", file=sys.stderr)
        sys.exit(exit_code)
    return 0


def fail_closed_exit(
    report_or_verdict,
    *,
    message: str = "Stage report indicates FAIL",
    exit_code: int = 1,
) -> int:
    """Alias for enforce_clean_verdict."""
    return enforce_clean_verdict(report_or_verdict, message=message, exit_code=exit_code)
