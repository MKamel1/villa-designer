"""Fail-closed static guard for raw unit conversion literals.

Scans Python sources in src/archpipe, revit, and scripts for unallowlisted
unit conversion literals (304.8, 0.3048, 3.28084, 25.4) using the tokenize module.
Only NUMBER tokens that are operands of multiplication or division (*, /, //, *=, /=)
are flagged. Comments, docstrings, string literals, and bare coordinates (e.g. -25.4)
stay quiet.

New conversions must go through the typed boundary in src/archpipe/units.py.
Existing historical conversion sites must be registered in
knowledge/unit-conversion-allowlist.json with migration targets.

Unreadable files, unreadable directories, untokenizable files, or invalid allowlists raise
UnreadableInputError (fail closed).

Quick Test:
    python -c "from archpipe.units_guard import check_units_guard; check_units_guard()"

Example Usage:
    >>> from archpipe.units_guard import findings, check_units_guard
    >>> results = findings()
    >>> len(results)
    0
    >>> check_units_guard()
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import re
import tokenize
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

RAW_LITERAL_REGEX = re.compile(
    r"(?<![0-9.])(?:304\.8|0\.3048|3\.28084|25\.4)(?![0-9.])"
)

TARGET_CONVERSION_VALUES: tuple[float, ...] = (304.8, 0.3048, 3.28084, 25.4)
CONVERSION_OPERATORS: frozenset[str] = frozenset({"*", "/", "//", "*=", "/="})


class UnreadableInputError(FileNotFoundError, ValueError):
    """Raised when an audit input file or directory is missing, unreadable, or invalid.

    Subclasses both FileNotFoundError (an OSError) and ValueError for caller compatibility.
    """
    pass


class UnitsConversionError(ValueError):
    """Raised when unallowlisted unit conversion literals are detected in source code."""
    pass


def _matches_conversion_literal(token_str: str) -> str | None:
    """Check if token_str represents one of the target conversion numbers.

    Returns the canonical matched string ('304.8', '0.3048', '3.28084', '25.4')
    if matched within floating point tolerance, or None otherwise.
    """
    try:
        val = float(token_str)
    except (ValueError, TypeError):
        return None
    for target in TARGET_CONVERSION_VALUES:
        if abs(val - target) < 1e-9:
            return str(target)
    return None


def _load_allowlist(allowlist_path: Path | str | None) -> set[tuple[str, str]]:
    """Load and parse the unit conversion allowlist file.

    Returns a set of (normalized_relative_path, stripped_line_text) tuples.
    Raises UnreadableInputError if the allowlist is missing, unreadable, or corrupt.
    """
    path = (
        Path(allowlist_path).resolve()
        if allowlist_path is not None
        else (ROOT / "knowledge/unit-conversion-allowlist.json")
    )

    if not path.exists():
        raise UnreadableInputError(f"Allowlist file not found: {path}")
    if not path.is_file():
        raise UnreadableInputError(f"Allowlist path is not a file: {path}")

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception as exc:
        raise UnreadableInputError(f"Failed to read or parse allowlist {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise UnreadableInputError(f"Allowlist root must be a JSON object, got {type(data).__name__}")

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise UnreadableInputError("Allowlist 'entries' field must be a list")

    allowed: set[tuple[str, str]] = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise UnreadableInputError(f"Allowlist entry at index {idx} is not an object: {entry!r}")
        if "file" not in entry or "line_text" not in entry:
            raise UnreadableInputError(f"Allowlist entry at index {idx} missing 'file' or 'line_text': {entry!r}")
        file_norm = Path(str(entry["file"])).as_posix()
        line_norm = str(entry["line_text"]).strip()
        allowed.add((file_norm, line_norm))

    return allowed


def findings(
    root: Path | str | None = None,
    allowlist_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Scan source code for raw unit conversion literals outside the typed boundary.

    Parses each Python file with the tokenize module and inspects only NUMBER tokens.
    Flags a conversion literal only when it is an operand of multiplication or division
    (*, /, //, *=, /=). Bare coordinates, comments, docstrings, and ordinary strings stay quiet.

    Args:
        root: Root directory to scan. If None, defaults to repository root.
        allowlist_path: Path to unit-conversion-allowlist.json. If None, defaults
            to knowledge/unit-conversion-allowlist.json.

    Returns:
        List of finding dictionaries with keys:
            - 'file': Relative path from root
            - 'line_number': 1-indexed line number
            - 'line_text': Full text of the offending line
            - 'matched_literal': The matched raw literal string

    Raises:
        UnreadableInputError: If any target file or directory is missing, corrupt,
            unreadable, or cannot be tokenized.
    """
    r_path = Path(root).resolve() if root is not None else ROOT

    if not r_path.exists():
        raise UnreadableInputError(f"Target root directory not found: {r_path}")
    if not r_path.is_dir():
        raise UnreadableInputError(f"Target root is not a directory: {r_path}")

    allowed = _load_allowlist(allowlist_path)

    # Determine paths to scan
    scan_targets: list[Path] = []
    src_archpipe = r_path / "src/archpipe"
    if src_archpipe.is_dir():
        # Standard repository structure: scan src/archpipe, revit, scripts
        for subdir_name in ("src/archpipe", "revit", "scripts"):
            sub = r_path / subdir_name
            if sub.exists():
                if not sub.is_dir():
                    raise UnreadableInputError(f"Subdirectory target is not a directory: {sub}")
                scan_targets.append(sub)
    else:
        # Non-standard or test fixture tree: scan root directory directly
        scan_targets.append(r_path)

    py_files: list[Path] = []
    for target in scan_targets:
        try:
            for item in target.rglob("*.py"):
                if item.is_file():
                    py_files.append(item)
        except OSError as exc:
            raise UnreadableInputError(f"Failed to scan directory {target}: {exc}") from exc

    results: list[dict[str, Any]] = []

    for py_file in sorted(py_files):
        # Exclude the single typed boundary itself
        if py_file.name == "units.py" and py_file.parent.name == "archpipe":
            continue

        try:
            content_bytes = py_file.read_bytes()
        except OSError as exc:
            raise UnreadableInputError(f"Unreadable file encountered: {py_file} ({exc})") from exc

        try:
            tokens = list(tokenize.tokenize(io.BytesIO(content_bytes).readline))
        except Exception as exc:
            raise UnreadableInputError(f"Failed to tokenize file {py_file}: {exc}") from exc

        # Filter out comments, non-logical newlines, and encoding tokens when finding neighbours
        sig_tokens = [
            tok
            for tok in tokens
            if tok.type not in (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING)
        ]

        rel_path = py_file.relative_to(r_path).as_posix()
        reported_lines: set[int] = set()

        for idx, tok in enumerate(sig_tokens):
            if tok.type != tokenize.NUMBER:
                continue

            matched_lit = _matches_conversion_literal(tok.string)
            if not matched_lit:
                continue

            prev_tok = sig_tokens[idx - 1] if idx > 0 else None
            next_tok = sig_tokens[idx + 1] if idx + 1 < len(sig_tokens) else None

            is_operand = False
            if prev_tok is not None and prev_tok.string in CONVERSION_OPERATORS:
                is_operand = True
            elif next_tok is not None and next_tok.string in CONVERSION_OPERATORS:
                is_operand = True
            elif (
                prev_tok is not None
                and prev_tok.string in ("+", "-")
                and idx >= 2
                and sig_tokens[idx - 2].string in CONVERSION_OPERATORS
            ):
                is_operand = True

            if not is_operand:
                continue

            line_idx = tok.start[0]
            if line_idx in reported_lines:
                continue

            raw_line = tok.line
            stripped = raw_line.strip()
            if (rel_path, stripped) in allowed:
                continue

            reported_lines.add(line_idx)
            results.append(
                {
                    "file": rel_path,
                    "line_number": line_idx,
                    "line_text": raw_line.rstrip("\r\n"),
                    "matched_literal": matched_lit,
                }
            )

    return results


def check_units_guard(
    root: Path | str | None = None,
    allowlist_path: Path | str | None = None,
) -> None:
    """Fail closed if any unallowlisted raw unit conversion literals are detected.

    Args:
        root: Root directory to scan. If None, defaults to repository root.
        allowlist_path: Path to allowlist. If None, defaults to knowledge/unit-conversion-allowlist.json.

    Raises:
        UnitsConversionError: If one or more unallowlisted literals are found.
        UnreadableInputError: If any input file, allowlist, or directory cannot be read or tokenized.
    """
    found = findings(root=root, allowlist_path=allowlist_path)
    if found:
        lines = [
            f"Found {len(found)} unallowlisted unit conversion literal(s) outside src/archpipe/units.py:"
        ]
        for f in found:
            lines.append(
                f"  - {f['file']}:{f['line_number']} [{f['matched_literal']}]: {f['line_text'].strip()}"
            )
        lines.append(
            "\nAll unit conversions must route through src/archpipe/units.py, or be documented "
            "in knowledge/unit-conversion-allowlist.json for Phase 2 migration."
        )
        raise UnitsConversionError("\n".join(lines))
