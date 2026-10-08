"""The refactor audit reports removed guards without importing scene builders."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('refactor_audit', Path(__file__).parents[1]/'scripts/refactor_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class RefactorAudit(unittest.TestCase):
    def test_removed_nested_guard_test_import_and_constant_are_reported(self):
        source = "import copy\nLIMIT = 1\nclass Tests:\n def test_case(self):\n  assert LIMIT\n  if not LIMIT:\n   raise ValueError('closed')\n"
        findings = audit.removed(source, '')
        self.assertEqual({f['kind'] for f in findings}, {'import','constant','definition','assert','raise'})
        self.assertIn({'kind':'definition','item':'Tests.test_case'}, findings)

    def test_guard_relocated_to_helper_stays_present(self):
        before = "def guard(x):\n if x:\n  raise ValueError('closed')\n"
        after = "def guard(x):\n return helper(x)\ndef helper(x):\n if x:\n  raise ValueError('closed')\n"
        self.assertEqual(audit.removed(before, after), [])
