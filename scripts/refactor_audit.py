"""Audit behaviour-preserving refactors against a git base reference.

    python scripts/refactor_audit.py --base HEAD~1

Fails closed (exit 1) on any un-allowed code removal.
Fails closed (exit 2) on preflight or unreadable input.

Quick Test:
    python scripts/refactor_audit.py --base HEAD

Example Usage:
    python scripts/refactor_audit.py --base origin/main scripts/compare_lux.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.execution_context import ContextError, project_context
from archpipe.refactor_audit import Finding, audit_source, normalize_allowed


def get_git_diff_py_files(base_ref: str) -> list[str]:
    """Return python files changed between base_ref and working tree."""
    cmd = ["git", "diff", "--name-only", base_ref, "--", "*.py"]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"git diff failed (exit {res.returncode}): {res.stderr.strip()}")
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def get_git_show_file(base_ref: str, rel_path: str) -> str:
    """Return old file content from base_ref, or empty string if file was added."""
    git_path = Path(rel_path).as_posix()
    cmd = ["git", "show", f"{base_ref}:{git_path}"]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if res.returncode != 0:
        # File may be newly created in working tree
        return ""
    return res.stdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="HEAD", help="Base git reference to compare against")
    ap.add_argument("--allow", type=Path, default=None, help="Path to JSON allowlist file")
    ap.add_argument("paths", nargs="*", type=Path, help="Specific python paths to audit")
    a = ap.parse_args(argv)

    try:
        project_context(
            ROOT,
            Path(__file__).resolve(),
            "refactor-audit",
        )
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2

    # Load allowlist if provided or default exists
    allowed_data = None
    if a.allow is not None:
        if not a.allow.exists():
            print(f"Allowlist file not found: {a.allow}", file=sys.stderr)
            return 2
        try:
            allowed_data = json.loads(a.allow.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Failed to read allowlist {a.allow}: {exc}", file=sys.stderr)
            return 2
    else:
        default_allow = ROOT / "spec/refactor-audit-allow.json"
        if default_allow.exists():
            try:
                allowed_data = json.loads(default_allow.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"Failed to read default allowlist: {exc}", file=sys.stderr)
                return 2

    try:
        allowed = normalize_allowed(allowed_data)
    except Exception as exc:
        print(f"Invalid allowlist: {exc}", file=sys.stderr)
        return 2

    # Determine files to audit
    try:
        if a.paths:
            py_files = [
                p.resolve().relative_to(ROOT).as_posix() if p.is_absolute() else p.as_posix()
                for p in a.paths
            ]
        else:
            py_files = get_git_diff_py_files(a.base)
    except Exception as exc:
        print(f"Failed to determine changed files: {exc}", file=sys.stderr)
        return 2

    if not py_files:
        print(f"No python files changed against {a.base}.")
        return 0

    all_findings: list[Finding] = []
    unallowed_removals: list[Finding] = []

    for rel_path in py_files:
        full_path = ROOT / rel_path
        try:
            old_src = get_git_show_file(a.base, rel_path)
            if full_path.exists():
                new_src = full_path.read_text(encoding="utf-8")
            else:
                new_src = ""
        except Exception as exc:
            print(f"Unreadable input for {rel_path}: {exc}", file=sys.stderr)
            return 2

        try:
            findings = audit_source(old_src, new_src, path=rel_path, allowed=allowed)
        except Exception as exc:
            print(f"Audit failed on {rel_path}: {exc}", file=sys.stderr)
            return 2

        for f in findings:
            all_findings.append(f)
            if f.is_removal:
                unallowed_removals.append(f)

    # Print summary
    print(f"Refactor Audit against {a.base}: {len(py_files)} files checked")
    for f in all_findings:
        tag = "REMOVAL" if f.is_removal else f.kind.upper()
        print(f"  [{tag:7}] {f}")

    if unallowed_removals:
        print(f"\nFAIL: {len(unallowed_removals)} un-allowed removal(s) found.", file=sys.stderr)
        return 1

    print("\nPASS: No un-allowed removals.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
