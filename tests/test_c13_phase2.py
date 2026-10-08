"""Phase 2 Batch 1 migration tests for serialization boundary (C13).

Verifies that the five Phase 2 Batch 1 files route all persistent file
writes through the safe_io atomic publication boundary.

Quick Test:
    python -m unittest tests/test_c13_phase2.py

Example Usage:
    python -m unittest tests.test_c13_phase2.Phase2MigrationTests.test_ast_no_unlisted_direct_writes
"""
from __future__ import annotations

import ast
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from archpipe import daylight as DL
from archpipe import daylight_climate as DLC
from archpipe import deliverables as DELIV
from archpipe import radiance as RAD
from archpipe import safe_io

ROOT = Path(__file__).resolve().parents[1]

# Allowed direct file writes in the five Phase 2 Batch 1 files.
# Format: (relative_file_path, enclosing_function_name, call_type) -> reason
# Every entry MUST have an explicit rationale explaining why safe_io cannot or need not be used.
EXCEPTIONS: dict[tuple[str, str, str], str] = {
    # thermal.py: subprocess stdout handle for oconv in daylight_factor (same as daylight_grid)
    ("src/archpipe/thermal.py", "daylight_factor", "write_text"): "Temporary scratch scene file immediately read by Radiance oconv in the same function",
    ("src/archpipe/thermal.py", "daylight_factor", "open"): "Subprocess stdout redirection handle for oconv",
    # radiance.py: os.environ.copy() builds a child environment dictionary; not a file copy
    ("src/archpipe/radiance.py", "_child_env", "copy"): "Dictionary copy of os.environ, not a file write",
    # thermal.py: process log redirection via os.dup2 requires raw fd in append mode; safe_io has no append mode
    (
        "src/archpipe/thermal.py",
        "_quiet",
        "open",
    ): "Process log redirection via os.dup2 requires raw fd in append mode; safe_io has no append mode",
    # thermal.py: temporary scratch IDF file immediately read by EnergyPlus run_idf in the same function
    (
        "src/archpipe/thermal.py",
        "run_case",
        "write_text",
    ): "Temporary scratch IDF file immediately read by EnergyPlus run_idf in the same function",
    # radiance.py: stdout and stderr redirection handles for Radiance child processes in _run
    (
        "src/archpipe/radiance.py",
        "_run",
        "open",
    ): "Subprocess stdout and stderr redirection handles for Radiance child processes",
}

FILES_IN_BATCH = [
    ROOT / "src" / "archpipe" / "daylight.py",
    ROOT / "src" / "archpipe" / "daylight_climate.py",
    ROOT / "src" / "archpipe" / "thermal.py",
    ROOT / "src" / "archpipe" / "radiance.py",
    ROOT / "src" / "archpipe" / "cli.py",
]


class _WriteCallVisitor(ast.NodeVisitor):
    """AST visitor to locate direct file writing operations."""

    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.scope_stack: list[str] = []
        self.direct_writes: list[tuple[str, str, str, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Call(self, node: ast.Call):
        scope = self.scope_stack[-1] if self.scope_stack else "<module>"
        call_type: str | None = None

        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in ("write_text", "write_bytes"):
                call_type = attr
            elif attr == "open":
                # Check receiver is not tarfile or zipfile
                receiver = ""
                if isinstance(node.func.value, ast.Name):
                    receiver = node.func.value.id
                if receiver not in ("tarfile", "zipfile"):
                    mode = self._extract_mode(node)
                    if mode and any(m in mode for m in ("w", "a", "x")):
                        call_type = "open"
            elif attr in ("copy", "copy2", "copyfile", "copytree"):
                call_type = attr
            elif attr == "dump":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "json":
                    call_type = "json.dump"

        elif isinstance(node.func, ast.Name):
            if node.func.id == "open":
                mode = self._extract_mode(node)
                if mode and any(m in mode for m in ("w", "a", "x")):
                    call_type = "open"

        if call_type is not None:
            self.direct_writes.append((self.rel_path, scope, call_type, node.lineno))

        self.generic_visit(node)

    def _extract_mode(self, node: ast.Call) -> str | None:
        # Check keyword args (open(..., mode=...)) first
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
        # Check positional args: for Path.open(mode), mode is args[0]; for builtin open(path, mode), mode is args[1]
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if any(m in arg.value for m in ("r", "w", "a", "x")):
                    return arg.value
        return None


class Phase2MigrationTests(unittest.TestCase):
    """Tests for Phase 2 Batch 1 migration onto safe_io."""

    def test_ast_no_unlisted_direct_writes(self):
        """Proof (a): AST check that the 5 files have no unlisted direct file writes."""
        unlisted: list[str] = []
        seen_exceptions: set[tuple[str, str, str]] = set()

        for file_path in FILES_IN_BATCH:
            self.assertTrue(file_path.is_file(), f"Expected batch file {file_path} exists")
            rel_path = file_path.resolve().relative_to(ROOT).as_posix()
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel_path)

            visitor = _WriteCallVisitor(rel_path)
            visitor.visit(tree)

            for path_str, func_name, call_type, lineno in visitor.direct_writes:
                key = (path_str, func_name, call_type)
                if key in EXCEPTIONS:
                    seen_exceptions.add(key)
                else:
                    unlisted.append(f"{path_str}:{lineno} in {func_name}() direct write '{call_type}'")

        if unlisted:
            self.fail("Found unlisted direct file writes outside allowed exceptions:\n" + "\n".join(unlisted))

        # Ensure all registered exceptions were actually accounted for
        missing_exceptions = set(EXCEPTIONS.keys()) - seen_exceptions
        self.assertEqual(
            missing_exceptions,
            set(),
            f"Registered exceptions were not observed in AST: {missing_exceptions}",
        )

    def test_representative_text_writer_byte_equality(self):
        """Proof (b) text writer: bytes written through migrated radiance._write equal frozen bytes."""
        sample_rad_text = (
            "# Radiance test material block\n"
            "void plastic wall_mat\n"
            "0\n0\n"
            "5 0.50 0.50 0.50 0.00 0.00\n"
        )
        # Frozen expected bytes derived from reading the old code:
        # old radiance._write did path.write_text(text) which produces UTF-8 encoded text
        frozen_expected_bytes = (
            b"# Radiance test material block\n"
            b"void plastic wall_mat\n"
            b"0\n0\n"
            b"5 0.50 0.50 0.50 0.00 0.00\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "materials.rad"
            RAD._write(target, sample_rad_text)
            written_bytes = target.read_bytes()
            self.assertEqual(written_bytes, frozen_expected_bytes)

    def test_representative_json_writer_byte_equality(self):
        """Proof (b) JSON writer: bytes written through migrated radiance._write_grid_json equal frozen bytes."""
        points = [(100.0, 200.0)]
        lux = [250.123]
        meta = {"room": "Bed", "spacing_mm": 500}

        # Frozen expected bytes derived from reading the old code:
        # rows = [[100.0, 200.0, 250.123]]
        # payload = {"room": "Bed", "spacing_mm": 500, "units": "mm, lux", "points": rows}
        # json.dumps(payload, indent=2) with Python standard library dictionary ordering
        frozen_expected_json_bytes = (
            b'{\n'
            b'  "room": "Bed",\n'
            b'  "spacing_mm": 500,\n'
            b'  "units": "mm, lux",\n'
            b'  "points": [\n'
            b'    [\n'
            b'      100.0,\n'
            b'      200.0,\n'
            b'      250.123\n'
            b'    ]\n'
            b'  ]\n'
            b'}'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "grid.json"
            RAD._write_grid_json(target, points, lux, meta)
            written_bytes = target.read_bytes()
            self.assertEqual(written_bytes, frozen_expected_json_bytes)

    def test_representative_csv_writer_byte_equality(self):
        """Proof (b) CSV writer: bytes written through deliverables.write_csv equal frozen bytes."""
        rows = [{"id": "R1", "name": "Living", "area_m2": 24.5}]
        # Frozen expected bytes from standard CSV writer with CRLF line endings
        frozen_expected_csv_bytes = b"id,name,area_m2\r\nR1,Living,24.5\r\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "rooms.csv"
            DELIV.write_csv(rows, target)
            written_bytes = target.read_bytes()
            self.assertEqual(written_bytes, frozen_expected_csv_bytes)

    def test_write_failure_leaves_existing_destination_file_unchanged(self):
        """Proof (c): Serializer or write failure leaves existing destination file unchanged."""
        original_bytes = b'{"pre_existing": "intact_data_do_not_overwrite"}'

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "test_output.json"
            dest.write_bytes(original_bytes)

            # Test 1: Serializer raises error during save_json
            with patch("json.dumps", side_effect=RuntimeError("serialization exploded")):
                with self.assertRaises(RuntimeError):
                    safe_io.save_json(dest, {"new": "corrupted_content"})

            # Destination file must be completely untouched
            self.assertEqual(dest.read_bytes(), original_bytes)
            # No leftover .part files in destination folder
            self.assertEqual(list(dest.parent.glob("*.part")), [])

            # Test 2: Serializer error during radiance._write_grid_json
            with patch("json.dumps", side_effect=RuntimeError("grid serializer exploded")):
                with self.assertRaises(RuntimeError):
                    RAD._write_grid_json(dest, [(0, 0)], [100.0], {"meta": "failed"})

            self.assertEqual(dest.read_bytes(), original_bytes)
            self.assertEqual(list(dest.parent.glob("*.part")), [])

            # Test 3: Interrupted write during radiance._write staging
            with patch.object(safe_io.os, "fsync", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    RAD._write(dest, "new rad scene")

            self.assertEqual(dest.read_bytes(), original_bytes)
            self.assertEqual(list(dest.parent.glob("*.part")), [])


if __name__ == "__main__":
    unittest.main()
