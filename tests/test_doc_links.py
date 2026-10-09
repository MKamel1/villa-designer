"""Docs link check: absolute machine links and broken repo links fail; the real docs pass."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_doc_links", ROOT / "scripts/check_doc_links.py")
links = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(links)


class DocLinks(unittest.TestCase):
    def test_absolute_and_broken_links_fail_good_link_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "src").mkdir()
            (root / "src/real.py").write_text("x = 1\n", encoding="utf-8")
            doc = root / "docs/note.md"
            # Real case shape: agent reports linked into one machine's worktree.
            doc.write_text("[a](file:///C:/Users/someone/arch-pipeline-agy/src/real.py)\n"
                           "[b](../src/missing.py#L3)\n[c](../src/real.py#L1)\n"
                           "[d](https://example.org)\n[e](../out/generated.json)\n", encoding="utf-8")
            errors = links.check_file(doc, root)
            self.assertEqual(len(errors), 2, errors)
            self.assertTrue(any("absolute machine link" in e for e in errors))
            self.assertTrue(any("broken link ../src/missing.py" in e for e in errors))
            count, unresolved = links.fix_file(doc, root)
            self.assertEqual((count, unresolved), (1, []))
            self.assertIn("](../src/real.py)", doc.read_text(encoding="utf-8"))

    def test_real_docs_tree_has_no_link_errors(self):
        errors = [e for doc in links.docs() for e in links.check_file(doc)]
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
