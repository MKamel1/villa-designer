"""Check links in docs/**/*.md: no machine-specific absolute paths, no broken repo links.

    python scripts/check_doc_links.py            # check, exit 1 on errors
    python scripts/check_doc_links.py --fix      # rewrite absolute links to repo-relative ones

Agent-written docs carried links such as file:///C:/Users/<user>/arch-pipeline-agy/src/...,
which break in every other checkout (the Linux workstation, GitHub). http(s) links are
not fetched. Invalid launch contexts exit 2.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

LINK = re.compile(r"\]\((?P<target>[^)\s]+)\)")
BARE_FILE_URL = re.compile(r"(?<!\()file:///[^\s)>\]`]+")
ABSOLUTE = re.compile(r"^(?:file:///|[A-Za-z]:[\\/]|/home/|/Users/|/tmp/)")
# Repo-relative remainder of an absolute path inside any arch-pipeline checkout.
CHECKOUT = re.compile(r"arch-pipeline(?:-[a-z0-9]+)?[\\/](?P<rest>.+)$", re.IGNORECASE)


def _split_anchor(target: str) -> tuple[str, str]:
    path, sep, anchor = target.partition("#")
    return path, sep + anchor


def _repo_relative(target: str) -> str | None:
    """Repo path for an absolute link into an arch-pipeline checkout, else None."""
    path, _ = _split_anchor(target)
    path = path.replace("file:///", "").replace("%20", " ")
    match = CHECKOUT.search(path.replace("\\", "/"))
    return match.group("rest") if match else None


def check_file(doc: Path, root: Path = ROOT) -> list[str]:
    """Errors for one markdown file (absolute links, missing relative targets)."""
    errors = []
    text = doc.read_text(encoding="utf-8", errors="replace")
    targets = [m.group("target") for m in LINK.finditer(text)] + BARE_FILE_URL.findall(text)
    for target in targets:
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        rel = doc.relative_to(root).as_posix()
        if ABSOLUTE.match(target):
            errors.append(f"{rel}: absolute machine link {target}")
            continue
        path, _ = _split_anchor(target)
        resolved = (doc.parent / path.replace("%20", " ")).resolve()
        # Generated outputs (out/) and machine-local data are not in git.
        if resolved.is_relative_to(root / "out"):
            continue
        if path and not resolved.exists():
            errors.append(f"{rel}: broken link {target}")
    return errors


def fix_file(doc: Path, root: Path = ROOT) -> tuple[int, list[str]]:
    """Rewrite absolute checkout links to relative ones; return (count, unresolved)."""
    text = doc.read_text(encoding="utf-8", errors="replace")
    unresolved = []
    count = 0

    def relative_for(target: str) -> str | None:
        rest = _repo_relative(target)
        if rest is None:
            return None
        _, anchor = _split_anchor(target)
        file_part = rest.split("#")[0]
        if not (root / file_part).exists():
            return None
        return os.path.relpath(root / file_part, doc.parent).replace("\\", "/") + anchor

    def link_sub(match):
        nonlocal count
        target = match.group("target")
        if not ABSOLUTE.match(target):
            return match.group(0)
        new = relative_for(target)
        if new is None:
            unresolved.append(target)
            return match.group(0)
        count += 1
        return "](" + new + ")"

    def bare_sub(match):
        nonlocal count
        new = relative_for(match.group(0))
        if new is None:
            unresolved.append(match.group(0))
            return match.group(0)
        count += 1
        return new

    text = LINK.sub(link_sub, text)
    text = BARE_FILE_URL.sub(bare_sub, text)
    if count:
        doc.write_text(text, encoding="utf-8")
    return count, unresolved


def docs(root: Path = ROOT) -> list[Path]:
    return sorted((root / "docs").rglob("*.md"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fix", action="store_true", help="rewrite absolute checkout links to relative ones")
    a = ap.parse_args(argv)
    from archpipe.execution_context import ContextError, project_context
    try:
        project_context(ROOT, Path(__file__).resolve(), "check-doc-links")
    except ContextError as exc:
        print("PREFLIGHT FAILED: " + str(exc), file=sys.stderr)
        return 2
    if a.fix:
        total = 0
        for doc in docs():
            count, unresolved = fix_file(doc)
            total += count
            for target in unresolved:
                print(f"unresolved: {doc.relative_to(ROOT).as_posix()}: {target}")
        print(f"rewrote {total} links")
    errors = [e for doc in docs() for e in check_file(doc)]
    for error in errors:
        print(error)
    print(f"{len(errors)} link errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
