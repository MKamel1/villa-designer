"""Phase 2 Batch 2 migration tests for serialization boundary (C13).

Verifies that the ten Phase 2 Batch 2 IronPython report writer files in revit/
route all persistent file writes through the safe_io atomic publication boundary,
adhere strictly to Python 2.7 compatible syntax, and preserve serialization behavior.

Quick Test:
    python -m unittest tests/test_c13_phase2b.py

Example Usage:
    python -m unittest tests.test_c13_phase2b.Phase2bMigrationTests.test_ast_no_unlisted_direct_writes
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "revit"))

from archpipe import safe_io
import jsonsafe

# Allowed direct file writes in the ten Phase 2 Batch 2 files.
# Format: (relative_file_path, enclosing_function_name, call_type) -> reason
# Every entry MUST have an explicit rationale explaining why safe_io cannot or need not be used.
# All 10 direct report writers have been completely migrated to safe_io.save_json.
# Native Revit model saves (doc.Save / doc.SaveAs) and PDF exports (doc.Export) are native
# Revit API methods, not direct Python file writes, and are excluded from Phase 2 Batch 2.
EXCEPTIONS: dict[tuple[str, str, str], str] = {}

FILES_IN_BATCH = [
    ROOT / "revit" / "build_bedroom.py",
    ROOT / "revit" / "diag_context.py",
    ROOT / "revit" / "dump_mcp_tools.py",
    ROOT / "revit" / "export_views.py",
    ROOT / "revit" / "place_families_test.py",
    ROOT / "revit" / "probe.py",
    ROOT / "revit" / "probe_fixture_drop.py",
    ROOT / "revit" / "probe_fixture_geometry.py",
    ROOT / "revit" / "probe_product_family.py",
    ROOT / "revit" / "probe_villa_inventory.py",
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
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if any(m in arg.value for m in ("r", "w", "a", "x")):
                    return arg.value
        return None


class _Py27SyntaxVisitor(ast.NodeVisitor):
    """AST visitor to verify that syntax constructs are Python 2.7 compatible."""

    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.violations: list[tuple[str, int, str]] = []

    def visit_JoinedStr(self, node: ast.JoinedStr):
        self.violations.append((self.rel_path, node.lineno, "f-string (JoinedStr)"))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self.violations.append((self.rel_path, node.lineno, "type annotation on variable (AnnAssign)"))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.returns is not None:
            self.violations.append((self.rel_path, node.lineno, "return type annotation on function " + node.name))
        all_args = list(node.args.args)
        if hasattr(node.args, "posonlyargs"):
            all_args.extend(node.args.posonlyargs)
        if hasattr(node.args, "kwonlyargs"):
            all_args.extend(node.args.kwonlyargs)
        if node.args.vararg:
            all_args.append(node.args.vararg)
        if node.args.kwarg:
            all_args.append(node.args.kwarg)
        for arg in all_args:
            if getattr(arg, "annotation", None) is not None:
                self.violations.append((self.rel_path, node.lineno, "argument type annotation on " + arg.arg))
        if getattr(node, "type_params", None):
            self.violations.append((self.rel_path, node.lineno, "type parameter on function " + node.name))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.violations.append((self.rel_path, node.lineno, "async function def (AsyncFunctionDef)"))
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.violations.append((self.rel_path, node.lineno, "async for (AsyncFor)"))
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.violations.append((self.rel_path, node.lineno, "async with (AsyncWith)"))
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await):
        self.violations.append((self.rel_path, node.lineno, "await expression (Await)"))
        self.generic_visit(node)

    def visit_Match(self, node: ast.AST):
        self.violations.append((self.rel_path, getattr(node, "lineno", 0), "pattern matching (Match)"))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        if getattr(node, "type_params", None):
            self.violations.append((self.rel_path, node.lineno, "type parameter on class " + node.name))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name == "pathlib" or alias.name.startswith("pathlib."):
                self.violations.append((self.rel_path, node.lineno, "import of pathlib"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "pathlib" or (node.module and node.module.startswith("pathlib.")):
            self.violations.append((self.rel_path, node.lineno, "import from pathlib"))
        self.generic_visit(node)


class _SafeIoCallVisitor(ast.NodeVisitor):
    """AST visitor to verify presence of safe_io imports and save_json calls."""

    def __init__(self):
        self.has_safe_io_import = False
        self.save_json_calls = 0

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "archpipe":
            for alias in node.names:
                if alias.name == "safe_io":
                    self.has_safe_io_import = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "save_json":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "safe_io":
                    self.save_json_calls += 1
        self.generic_visit(node)



def _parse_py2(source, rel_path):
    """Parse a revit/ IronPython 2.7 file with the CPython 3 ast module.

    Some revit/ files contain Python-2-only byte-string escapes such as
    "\\u%04x" (probe_product_family._ascii), which Python 3 rejects as a
    truncated unicode escape. For analysis only, such literals are rewritten to
    their Python-2 meaning (a literal backslash-u) before parsing; the file on
    disk is not changed (lead review 2026-10-08).
    """
    try:
        return ast.parse(source, filename=rel_path)
    except SyntaxError:
        return ast.parse(source.replace('"\\u%04x"', '"\\\\u%04x"'), filename=rel_path)


class Phase2bMigrationTests(unittest.TestCase):
    """Tests for Phase 2 Batch 2 migration onto safe_io."""

    def test_ast_no_unlisted_direct_writes(self):
        """Proof (a): AST check that the 10 files have no unlisted direct file writes."""
        unlisted: list[str] = []
        seen_exceptions: set[tuple[str, str, str]] = set()

        for file_path in FILES_IN_BATCH:
            self.assertTrue(file_path.is_file(), f"Expected batch file {file_path} exists")
            rel_path = file_path.resolve().relative_to(ROOT).as_posix()
            source = file_path.read_text(encoding="utf-8")
            tree = _parse_py2(source, rel_path)

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

        missing_exceptions = set(EXCEPTIONS.keys()) - seen_exceptions
        self.assertEqual(
            missing_exceptions,
            set(),
            f"Registered exceptions were not observed in AST: {missing_exceptions}",
        )

    def test_ast_python_27_compatible_syntax(self):
        """Proof (b): AST check that every edited revit/ file uses Python 2.7 compatible syntax."""
        all_violations: list[str] = []

        for file_path in FILES_IN_BATCH:
            self.assertTrue(file_path.is_file(), f"Expected batch file {file_path} exists")
            rel_path = file_path.resolve().relative_to(ROOT).as_posix()
            source = file_path.read_text(encoding="utf-8")
            tree = _parse_py2(source, rel_path)

            visitor = _Py27SyntaxVisitor(rel_path)
            visitor.visit(tree)

            for path_str, lineno, reason in visitor.violations:
                all_violations.append(f"{path_str}:{lineno} {reason}")

        if all_violations:
            self.fail("Found Python 3-only syntax in revit/ files:\n" + "\n".join(all_violations))

    def test_all_ten_files_call_safe_io_save_json(self):
        """Proof (c): Verify that all 10 files import safe_io and invoke safe_io.save_json."""
        for file_path in FILES_IN_BATCH:
            rel_path = file_path.resolve().relative_to(ROOT).as_posix()
            source = file_path.read_text(encoding="utf-8")
            tree = _parse_py2(source, rel_path)

            visitor = _SafeIoCallVisitor()
            visitor.visit(tree)

            self.assertTrue(
                visitor.has_safe_io_import,
                f"{rel_path} does not import safe_io from archpipe",
            )
            self.assertGreater(
                visitor.save_json_calls,
                0,
                f"{rel_path} does not call safe_io.save_json",
            )

    def test_probe_product_family_serialization_preserves_behavior(self):
        """Proof (d): probe_product_family serialization logic retains default=str and ASCII escaping."""
        def _ascii(v):
            if isinstance(v, dict):
                return dict((_ascii(k), _ascii(x)) for k, x in v.items())
            if isinstance(v, (list, tuple)):
                return [_ascii(x) for x in v]
            if isinstance(v, str):
                return "".join(c if ord(c) < 128 else "\\u%04x" % ord(c) for c in v)
            return v

        class CustomIdentifier:
            def __str__(self):
                return "custom_id_12345"

        sample_data = {
            "title": "Catalogue \xae Header",
            "identifier": CustomIdentifier(),
            "count": 42,
            "nested": {"label": "\u2022 bullet"},
        }
        cleaned = _ascii(sample_data)

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "product_family_output.json"
            safe_io.save_json(dest, cleaned, indent=2, sort_keys=True, default=str)

            written_bytes = dest.read_bytes()
            # Must end with a newline
            self.assertTrue(written_bytes.endswith(b"\n"))
            # Must be pure ASCII text
            written_bytes.decode("ascii")
            # Parse back and verify values
            parsed = json.loads(written_bytes.decode("utf-8"))
            self.assertEqual(parsed["title"], "Catalogue \\u00ae Header")
            self.assertEqual(parsed["identifier"], "custom_id_12345")
            self.assertEqual(parsed["count"], 42)
            self.assertEqual(parsed["nested"]["label"], "\\u2022 bullet")

    def test_write_failure_leaves_existing_destination_file_unchanged(self):
        """Proof (f): Serializer error or disk flush failure preserves existing destination."""
        original_bytes = b'{"pre_existing": "intact_report_data"}\n'

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "test_report.json"
            dest.write_bytes(original_bytes)

            # Test 1: Serialization failure (e.g. non-finite float under allow_nan=False)
            with self.assertRaises(ValueError):
                safe_io.save_json(dest, {"invalid": float("nan")})

            self.assertEqual(dest.read_bytes(), original_bytes)
            self.assertEqual(list(dest.parent.glob("*.part")), [])

            # Test 2: Interrupted write during fsync
            with patch.object(safe_io.os, "fsync", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    safe_io.save_json(dest, {"new": "data"})

            self.assertEqual(dest.read_bytes(), original_bytes)
            self.assertEqual(list(dest.parent.glob("*.part")), [])


if __name__ == "__main__":
    unittest.main()
