"""Run explicitly named test modules with the managed Windows temp adapter."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from run_tests import _accessible_mkdtemp


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modules',nargs='+',help='Explicit test module names, e.g. test_mounting_scene')
    args=parser.parse_args()
    if any(not name.startswith('test_') or not (ROOT/'tests'/(name+'.py')).is_file() for name in args.modules):
        parser.error('Each argument must name an existing test module; discovery is not allowed')
    os.environ['NO_COLOR']='1'
    if os.name=='nt':
        path=ROOT/'out/tmp';path.mkdir(parents=True,exist_ok=True)
        tempfile.tempdir=str(path);tempfile.mkdtemp=_accessible_mkdtemp
    suite=unittest.defaultTestLoader.loadTestsFromNames(args.modules)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
