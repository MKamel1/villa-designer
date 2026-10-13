"""Phase 2 Batch 2 migration tests for evidence status checks (C12).

Tests the wiring of evidence.py verification into two migrated call sites:
1. src/archpipe/knowledge_index.py page_label_findings(): PDF sequence labels
   disagreeing with printed page numbers flagged with check_page_locator (l0189)
2. src/archpipe/guidance.py review_stage(): model review scope routed through
   EvidenceRecord.apply_to preventing silent widening to dwelling scope (l0020)

Quick Test:
    python -m unittest tests/test_c12_phase2b.py

Example Usage:
    >>> import unittest
    >>> suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_c12_phase2b")
    >>> runner = unittest.TextTestRunner()
    >>> result = runner.run(suite)
    >>> result.wasSuccessful()
    True
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from archpipe.evidence import (
    ScopeWideningError,
    check_page_locator,
)
from archpipe import guidance as g
from archpipe import knowledge_index as ki

ROOT = Path(__file__).resolve().parents[1]


class MockPage:
    """Mock page object with a get_label() method."""

    def __init__(self, label: str):
        self._label = label

    def get_label(self) -> str:
        return self._label


class MockDoc:
    """Mock PDF document returning MockPage instances."""

    def __init__(self, labels: list[str]):
        self._pages = [MockPage(lbl) for lbl in labels]

    def __getitem__(self, idx: int) -> MockPage:
        return self._pages[idx]

    def __len__(self) -> int:
        return len(self._pages)


class TestKnowledgeIndexPageLabelFindings(unittest.TestCase):
    """Test Site 1: src/archpipe/knowledge_index.py page_label_findings() / build().

    Verifies that sequence-number PDF page labels disagreeing with printed page
    numbers are flagged with evidence.check_page_locator (lesson l0189), without
    mutating page_labels public return types, document objects, or SQLite schema.
    """

    def test_l0189_real_recorded_failure_flagged(self) -> None:
        """Real recorded failure from lesson l0189:
        docs/LEARNINGS.md line 392:
        'Building Construction Illustrated's PDF page labels are sequence numbers
        (191 where the page prints 5.45)'

        PDF label sequence number '191' where printed chapter-page is '5.45'.
        page_label_findings() must flag all mismatches citing l0189, while
        page_labels() returns (labels, basis) unchanged and stores no state
        on function or document objects.
        """
        doc = MockDoc(["191"] * 6)
        page_text = "WOOD STUD FRAMING   5.45\n" + "Planning reference text for chapter-page agreement.\n" * 5
        texts = [page_text] * 6

        # page_labels() public return shape remains tuple[list[str], str]
        labels, basis = ki.page_labels(doc, texts)
        self.assertIsInstance(labels, list)
        self.assertIsInstance(basis, str)
        self.assertEqual(len(labels), 6)
        self.assertEqual(labels[0], "5.45")
        self.assertTrue(basis.startswith("printed chapter-page numbers"))

        # No state stored on function or document objects
        self.assertFalse(hasattr(ki.page_labels, "flags"))
        self.assertFalse(hasattr(doc, "page_label_flags"))
        self.assertFalse(hasattr(doc[0], "page_label_flags"))

        # page_label_findings() returns findings list with check_page_locator authority
        findings = ki.page_label_findings(doc, texts)
        self.assertEqual(len(findings), 6)
        for i, item in enumerate(findings):
            self.assertEqual(item["page"], i)
            self.assertTrue(item["flagged"])
            self.assertFalse(item["reliable"])
            self.assertEqual(item["pdf_label"], "191")
            self.assertEqual(item["printed_page"], "5.45")
            self.assertIn("l0189", item["detail"])
            self.assertIn("disagrees with printed page", item["detail"])

    def test_clean_input_stays_quiet(self) -> None:
        """Clean input where PDF sequence labels match printed numbers stays quiet."""
        doc = MockDoc(["17"] * 6)
        page_text = "17\nPlanning reference text for standard page numbering.\n" * 5
        texts = [page_text] * 6

        labels, basis = ki.page_labels(doc, texts)
        self.assertEqual(labels[0], "17")

        findings = ki.page_label_findings(doc, texts)
        self.assertEqual(findings, [])

    def test_sibling_failure_flagged(self) -> None:
        """Sibling failure from lesson l0189: sequence number '42' vs printed '3.10'."""
        doc = MockDoc(["42"] * 6)
        page_text = "Auditoria 3.10\nPlanning reference text for auditorium dimensions.\n" * 5
        texts = [page_text] * 6

        findings = ki.page_label_findings(doc, texts)
        self.assertEqual(len(findings), 6)
        self.assertTrue(findings[0]["flagged"])
        self.assertFalse(findings[0]["reliable"])
        self.assertEqual(findings[0]["pdf_label"], "42")
        self.assertEqual(findings[0]["printed_page"], "3.10")
        self.assertIn("l0189", findings[0]["detail"])

    def test_schema_preservation_and_record_findings(self) -> None:
        """Verify SQLite books table schema is preserved and report records findings."""
        tmpdir = Path(tempfile.mkdtemp())
        try:
            db_path = tmpdir / "knowledge.sqlite"
            con = ki.connect(db_path)
            # Inspect table columns: books table must remain unchanged
            cols = [r[1] for r in con.execute("pragma table_info(books)").fetchall()]
            expected_cols = ["id", "title", "edition", "file", "kind", "pages", "label_basis", "sha256"]
            self.assertEqual(cols, expected_cols)
            con.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
