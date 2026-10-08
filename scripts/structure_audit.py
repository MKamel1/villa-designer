"""Compare public/guard structure to a Git base without importing project code.

Reports removed definitions, imports, assertions, raises, uppercase constants,
test files and frozen fixtures. A report needs human justification; exit zero
means the comparison completed, not that removals are approved.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def inventory(source):
    tree = ast.parse(source)
    result = {name: set() for name in ('definition', 'import', 'assert', 'raise', 'constant')}

    def walk(nodes, parents=()):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = '.'.join((*parents, node.name))
                result['definition'].add(name)
                walk(node.body, (*parents, node.name))
            else:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        result['import'].add((node.module + '.' if isinstance(node, ast.ImportFrom) and node.module else '') + alias.name)
                elif isinstance(node, ast.Assert):
                    result['assert'].add(ast.dump(node, include_attributes=False))
                elif isinstance(node, ast.Raise):
                    result['raise'].add(ast.dump(node, include_attributes=False))
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        for child in ast.walk(target):
                            if isinstance(child, ast.Name) and child.id.isupper():
                                result['constant'].add('.'.join((*parents, child.id)))
                # Walk compound statements without conflating nested definitions.
                for _, value in ast.iter_fields(node):
                    if isinstance(value, list):
                        walk([child for child in value if isinstance(child, ast.stmt)], parents)
    walk(tree.body)
    return result


def removed(before, after):
    old, new = inventory(before), inventory(after)
    return [{'kind': kind, 'item': item} for kind in old for item in sorted(old[kind]-new[kind])]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    args = parser.parse_args()
    base = git('rev-parse', '--verify', args.base+'^{commit}').decode().strip()
    paths = git('diff', '--name-only', '-z', base).decode().split('\0')
    findings = []
    for name in filter(None, paths):
        path = ROOT / name
        try:
            before = git('show', base+':'+name).decode()
        except subprocess.CalledProcessError:
            continue  # Added file has no removal to compare.
        if not path.exists():
            findings.append(dict(path=name, kind='file', item='deleted'))
        elif path.suffix == '.py':
            findings.extend(dict(path=name, **row) for row in removed(before, path.read_text()))
    print(json.dumps(dict(base=base, removals=findings), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
