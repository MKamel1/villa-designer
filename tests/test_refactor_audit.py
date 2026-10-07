"""Tests for archpipe.refactor_audit: behaviour-preserving refactor audit.

Quick Test:
    python -m unittest tests/test_refactor_audit.py

Example Usage:
    >>> import unittest
    >>> from tests.test_refactor_audit import TestRefactorAudit
    >>> suite = unittest.TestLoader().loadTestsFromTestCase(TestRefactorAudit)
    >>> result = unittest.TextTestRunner().run(suite)
    >>> result.wasSuccessful()
    True
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.refactor_audit import Finding, audit_source, normalize_allowed


# Frozen real compare_lux main() body before/after reproducing the 2026-10-07 incident
OLD_COMPARE_LUX_SRC = """
def main() -> int:
    rendered = json.loads(a.rendered.read_text(encoding="utf-8"))
    extract = json.loads(a.extract.read_text(encoding="utf-8"))
    boundary = extract['rooms'][0]['boundary']
    x0, x1 = min(p[0] for p in boundary), max(p[0] for p in boundary)
    return 0
"""

NEW_COMPARE_LUX_DEFECT_SRC = """
def main() -> int:
    extract = json.loads(a.extract.read_text(encoding="utf-8"))
    boundary = extract['rooms'][0]['boundary']
    x0, x1 = min(p[0] for p in boundary), max(p[0] for p in boundary)
    return 0
"""

# Frozen real demo_bedroom_lighting harmless rename/move case
OLD_DEMO_BEDROOM_LIGHTING_SRC = """
IES = ph.revit_ies_dir()

def led_watts(p):
    return round(p.total_lumens / 95.0, 1)

def main() -> int:
    pendant = ph.load(IES / "PLD1A21.ies")
    return 0
"""

NEW_DEMO_BEDROOM_LIGHTING_SRC = """
def led_watts(p):
    return round(p.total_lumens / 95.0, 1)

def main() -> int:
    ies = ph.revit_ies_dir()
    pendant = ph.load(ies / "PLD1A21.ies")
    return 0
"""

# Translated siblings
OLD_SIBLING_DEFECT_SRC = """
def calculate_metrics() -> None:
    processed = parser.parse(data.read_text(encoding="utf-8"))
    summary = summarize(processed)
    return summary
"""

NEW_SIBLING_DEFECT_SRC = """
def calculate_metrics() -> None:
    summary = summarize(None)
    return summary
"""

OLD_SIBLING_HARMLESS_SRC = """
CONFIG_PATH = get_default_config()

def run() -> None:
    data = load_data(CONFIG_PATH)
    return data
"""

NEW_SIBLING_HARMLESS_SRC = """
def run() -> None:
    cfg = get_default_config()
    data = load_data(cfg)
    return data
"""

OLD_DROPPED_CALL_SRC = """
def main() -> int:
    res = compute_simulation()
    write_stage_result("compare-lux", record_path=record_path, exit_code=0)
    return 0
"""

NEW_DROPPED_CALL_SRC = """
def main() -> int:
    res = compute_simulation()
    return 0
"""


class TestRefactorAudit(unittest.TestCase):
    """Test suite for refactor audit verification and incident regression proofs."""

    def test_real_defect_compare_lux_finds_dropped_assignment_and_call(self) -> None:
        """The REAL defect: compare_lux main() body before/after.

        Reproduces the deleted line `rendered = json.loads(...)`.
        Must produce exactly one finding naming `rendered` and the `json.loads` call.
        """
        findings = audit_source(
            OLD_COMPARE_LUX_SRC,
            NEW_COMPARE_LUX_DEFECT_SRC,
            "scripts/compare_lux.py",
        )
        self.assertEqual(
            len(findings),
            1,
            f"Expected exactly 1 finding, got {len(findings)}: {findings}",
        )
        f = findings[0]
        self.assertTrue(f.is_removal)
        self.assertEqual(f.scope, "main")
        self.assertEqual(f.name, "rendered")
        self.assertEqual(f.call, "json.loads")
        self.assertIn("rendered", str(f))
        self.assertIn("json.loads", str(f))

    def test_real_harmless_case_demo_bedroom_lighting_is_quiet(self) -> None:
        """The real harmless case: module-level IES moved into main() as ies.

        Reported as moved/renamed (informational), producing no removal findings.
        """
        findings = audit_source(
            OLD_DEMO_BEDROOM_LIGHTING_SRC,
            NEW_DEMO_BEDROOM_LIGHTING_SRC,
            "scripts/demo_bedroom_lighting.py",
        )
        removals = [f for f in findings if f.is_removal]
        self.assertEqual(
            len(removals),
            0,
            f"Expected 0 removal findings for harmless rename/move, got: {removals}",
        )
        # Verify it was recorded as moved/renamed
        self.assertTrue(
            any(f.kind in ("moved", "renamed") and f.name == "IES" for f in findings),
            f"Expected IES to be reported as moved/renamed, got findings: {findings}",
        )

    def test_sibling_translated_defect_fires(self) -> None:
        """Sibling: a translated copy of the compare_lux defect produces one removal finding."""
        findings = audit_source(
            OLD_SIBLING_DEFECT_SRC,
            NEW_SIBLING_DEFECT_SRC,
            "scripts/calculate_metrics.py",
        )
        removals = [f for f in findings if f.is_removal]
        self.assertEqual(len(removals), 1)
        f = removals[0]
        self.assertEqual(f.name, "processed")
        self.assertEqual(f.call, "parser.parse")
        self.assertIn("processed", str(f))
        self.assertIn("parser.parse", str(f))

    def test_sibling_translated_harmless_rename_stays_quiet(self) -> None:
        """Sibling: a translated copy of the harmless rename/move produces no removal findings."""
        findings = audit_source(
            OLD_SIBLING_HARMLESS_SRC,
            NEW_SIBLING_HARMLESS_SRC,
            "scripts/run.py",
        )
        removals = [f for f in findings if f.is_removal]
        self.assertEqual(len(removals), 0)
        self.assertTrue(any(f.kind in ("moved", "renamed") for f in findings))

    def test_sibling_deleted_call_without_assignment_fires(self) -> None:
        """Sibling: a deleted call without an assignment (dropped write_stage_result)."""
        findings = audit_source(
            OLD_DROPPED_CALL_SRC,
            NEW_DROPPED_CALL_SRC,
            "scripts/compare_lux.py",
        )
        removals = [f for f in findings if f.is_removal]
        self.assertEqual(len(removals), 1)
        f = removals[0]
        self.assertEqual(f.kind, "removed_call")
        self.assertEqual(f.name, "write_stage_result")
        self.assertEqual(f.call, "write_stage_result")
        self.assertIn("write_stage_result", str(f))

    def test_allowed_removal_with_reason_stays_quiet(self) -> None:
        """An intentional removal declared in allowlist with a valid reason stays quiet."""
        allowed = {
            "scripts/compare_lux.py": {
                "rendered": "migrated to preflight input validation in commit 13726cc",
            }
        }
        findings = audit_source(
            OLD_COMPARE_LUX_SRC,
            NEW_COMPARE_LUX_DEFECT_SRC,
            "scripts/compare_lux.py",
            allowed=allowed,
        )
        removals = [f for f in findings if f.is_removal]
        self.assertEqual(len(removals), 0)
        self.assertTrue(any(f.kind == "allowed" and f.name == "rendered" for f in findings))

    def test_allowed_removal_without_reason_raises(self) -> None:
        """Allow declaration without an explicit reason fails closed."""
        allowed_empty = {
            "scripts/compare_lux.py": [
                {"name": "rendered", "reason": ""},
            ]
        }
        with self.assertRaises(ValueError):
            audit_source(
                OLD_COMPARE_LUX_SRC,
                NEW_COMPARE_LUX_DEFECT_SRC,
                "scripts/compare_lux.py",
                allowed=allowed_empty,
            )

        allowed_no_reason = {
            "scripts/compare_lux.py": ["rendered"],
        }
        with self.assertRaises(ValueError):
            audit_source(
                OLD_COMPARE_LUX_SRC,
                NEW_COMPARE_LUX_DEFECT_SRC,
                "scripts/compare_lux.py",
                allowed=allowed_no_reason,
            )

    def test_unparsable_source_raises(self) -> None:
        """Unparsable input fails closed by raising SyntaxError."""
        with self.assertRaises(SyntaxError):
            audit_source("def broken(:\n    pass", "def ok(): pass", "broken.py")

        with self.assertRaises(SyntaxError):
            audit_source("def ok(): pass", "def broken(:\n    pass", "broken.py")

    def test_scope_disappeared_reported(self) -> None:
        """A scope (function) that disappeared is reported as a removal finding."""
        old_src = """
def helper() -> int:
    return 42

def main() -> int:
    return helper()
"""
        new_src = """
def main() -> int:
    return 42
"""
        findings = audit_source(old_src, new_src, "test_scope.py")
        removals = [f for f in findings if f.is_removal]
        self.assertTrue(any(f.kind == "removed_scope" and f.name == "helper" for f in removals))


if __name__ == "__main__":
    unittest.main()
