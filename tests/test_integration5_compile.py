"""Native source parses without executing Autodesk-dependent module code."""
import ast
from pathlib import Path
import unittest

class NativeProbeCompile(unittest.TestCase):
    def test_real_helper_and_frozen_bad_escape(self):
        source=Path('revit/probe_product_family.py').read_text()
        tree=ast.parse(source)
        helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_ascii')
        namespace={'basestring':str}
        exec(compile(ast.Module(body=[helper],type_ignores=[]),'native-helper','exec'),namespace)
        self.assertEqual(namespace['_ascii']({'a':['Registered ®']}),{'a':['Registered \\u00ae']})
        with self.assertRaises(SyntaxError):
            compile(source.replace('r"\\u%04x"','"\\u%04x"'),'frozen-real-bad-escape','exec')
