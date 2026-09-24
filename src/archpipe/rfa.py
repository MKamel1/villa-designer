"""Read a Revit family's format version without opening Revit.

Revit families are **forward-compatible only**: a `.rfa` saved by Revit
2026 cannot be opened by 2025, and there is no downgrade path. That single
fact decides whether any downloaded family is usable, and it is why 3,237
families sitting on this machine under `RVT 2026\\Libraries` are dead
weight (ADR-0008).

Free family sites rarely state which release they published from. Opening
each one in Revit to find out is slow, and worse, **opening a family in a
newer Revit upgrades it on save** -- so a careless check can destroy the
thing being checked.

This reads the version straight out of the file. No Revit, no risk.

HOW IT WORKS

A `.rfa` is an OLE2 compound document (the same container as a legacy
`.doc`), recognisable by the magic bytes `D0 CF 11 E0 A1 B1 1A E1`.
Inside is a stream called `BasicFileInfo` holding UTF-16LE text such as:

    Revit Build: Autodesk Revit 2025 (Build: 25.0.2.419)
    Format: 2025

Rather than implement an OLE directory walker, this scans the file for
those UTF-16LE markers. That is deliberate: the layout of the compound
document has changed across releases while the marker text has not, and a
scan cannot be broken by a sector-size or FAT change. The cost is reading
a few hundred KB, which is nothing next to a Revit launch.

Newer releases may also wrap the family differently; if no marker is
found, `version()` returns None and says so rather than guessing, because
"unknown" and "compatible" must never be confused here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# The Revit release this project authors in (ADR-0011). A family must
# be saved by this release or earlier to load, because .rfa is
# forward-compatible only.
TARGET_REVIT = 2027

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# How much of the file to scan. BasicFileInfo sits near the front in every
# sample examined; 4 MB is generous and still fast.
SCAN_BYTES = 4 * 1024 * 1024

_FORMAT = re.compile(r"Format:\s*(\d{4})")
_BUILD = re.compile(r"Autodesk Revit[^\d]{0,40}(\d{4})")
_BUILD_NUM = re.compile(r"Build:\s*([\d.]+)")

# Families from around Revit 2010 and earlier carry no release year at
# all -- their BasicFileInfo reads `Revit Build: 20080602_1900`, a
# timestamp. Found on a coffee-machine family downloaded from a free
# library, which the reader first reported as "unknown".
_BUILD_DATE = re.compile(r"Revit Build:\s*((?:19|20)\d{2})(\d{2})(\d{2})_")


class RfaError(ValueError):
    pass


@dataclass(frozen=True)
class FamilyInfo:
    path: Path
    format_year: int | None
    build: str = ""
    product: str = ""
    is_ole: bool = True
    # True when the year came from a build TIMESTAMP rather than a stated
    # release, and is therefore an upper bound rather than exact.
    year_is_derived: bool = False

    def usable_in(self, target_year: int) -> bool | None:
        """Can this family be loaded into Revit `target_year`?

        Returns None when the version could not be determined. A caller
        must treat None as "find out", never as "yes" -- the whole reason
        this module exists is that the wrong answer here wastes a download
        or, worse, upgrades a file on open.
        """
        if self.format_year is None:
            return None
        return self.format_year <= target_year

    def describe(self, target_year: int = TARGET_REVIT) -> str:
        ok = self.usable_in(target_year)
        if ok is None:
            return (f"{self.path.name}: version UNKNOWN -- no BasicFileInfo "
                    f"marker found. Do not assume it loads; open it in a "
                    f"COPY if you must test.")
        verdict = "OK" if ok else "TOO NEW"
        detail = (f"saved by Revit {self.format_year} or earlier (derived "
                  f"from build date)" if self.year_is_derived
                  else f"saved by Revit {self.format_year}")
        if self.build:
            detail += f" (build {self.build})"
        return (f"{self.path.name}: {verdict} for Revit {target_year} -- "
                f"{detail}")


def _decode_utf16(chunk: bytes) -> str:
    """UTF-16LE text, tolerating the binary either side of it."""
    return chunk.decode("utf-16-le", errors="ignore")


def read(path: str | Path) -> FamilyInfo:
    p = Path(path)
    if not p.is_file():
        raise RfaError(f"not a file: {p}")

    with p.open("rb") as fh:
        head = fh.read(SCAN_BYTES)

    is_ole = head.startswith(OLE_MAGIC)

    # The marker is UTF-16LE, so decode on both byte alignments: a stream
    # can start at an odd offset and the text would then be unreadable on
    # the natural one.
    text = _decode_utf16(head) + "\n" + _decode_utf16(head[1:])

    fmt = _FORMAT.search(text)
    build_year = _BUILD.search(text)
    build_num = _BUILD_NUM.search(text)

    year = None
    derived = False
    if fmt:
        year = int(fmt.group(1))
    elif build_year:
        year = int(build_year.group(1))
    else:
        stamp = _BUILD_DATE.search(text)
        if stamp:
            # Autodesk builds ahead of the release it ships in, so a build
            # dated year Y belongs to release Y or Y+1. Take Y+1: for a
            # compatibility test the question is "is this at most the
            # target?", and overstating the release year is the safe
            # direction -- it can only make us reject something usable,
            # never accept something that will fail to load.
            year = int(stamp.group(1)) + 1
            derived = True
    # A plausibility band. Revit years run 2000-2099; anything else means
    # the regex matched something that was not a version.
    if year is not None and not (2000 <= year <= 2099):
        year = None

    return FamilyInfo(
        path=p, format_year=year, year_is_derived=derived,
        build=build_num.group(1) if build_num else "",
        product=build_year.group(0).strip() if build_year else "",
        is_ole=is_ole,
    )


def screen(paths, target_year: int = TARGET_REVIT) -> dict:
    """Sort a pile of downloads into usable, too new, and unknown."""
    out = {"ok": [], "too_new": [], "unknown": [], "unreadable": []}
    for path in paths:
        try:
            info = read(path)
        except (RfaError, OSError) as e:
            out["unreadable"].append((Path(path), str(e)))
            continue
        verdict = info.usable_in(target_year)
        out["ok" if verdict else "too_new" if verdict is False
            else "unknown"].append(info)
    return out


def verify(*, require_installed: bool = True) -> list[str]:
    """Check the reader against families of KNOWN version on this machine.

    Revit installs its own library under
    `C:\\ProgramData\\Autodesk\\RVT <year>\\Libraries`, and every family
    there was saved by that release. So the folder name is independent
    ground truth -- exactly the kind of check `CLAUDE.md` asks for, rather
    than testing the parser against its own output.
    """
    fails: list[str] = []

    # The compatibility logic must be tested whatever is installed. An
    # earlier version of this function only exercised it when a 2026
    # library happened to be present, and on a 2025-only machine it passed
    # having checked nothing -- a vacuous test, which is worse than none
    # because it reports PASS.
    probes = [
        (FamilyInfo(Path("newer.rfa"), 2028), 2027, False, "a newer family"),
        (FamilyInfo(Path("same.rfa"), 2027), 2027, True, "a same-year family"),
        (FamilyInfo(Path("older.rfa"), 2021), 2027, True, "an older family"),
        (FamilyInfo(Path("unknown.rfa"), None), 2027, None, "an unknown family"),
        # The 2025 -> 2027 move only widens what loads; nothing that worked
        # before stops working.
        (FamilyInfo(Path("was_ok.rfa"), 2025), 2027, True, "a 2025 family"),
    ]
    for info, target, want, label in probes:
        got = info.usable_in(target)
        if got is not want:
            fails.append(f"{label} in Revit {target}: got {got!r}, "
                         f"want {want!r}")
    # "Unknown" must never read as permission.
    if FamilyInfo(Path("u.rfa"), None).usable_in(TARGET_REVIT):
        fails.append("an unknown version was treated as usable")
    if "UNKNOWN" not in FamilyInfo(Path("u.rfa"), None).describe():
        fails.append("an unknown version must say so in words")

    # Then the parser itself, against families whose version is known from
    # the folder they were installed into -- independent ground truth
    # rather than the parser's own output.
    checked = 0
    for year in (2021, 2022, 2023, 2024, 2025, 2026, 2027):
        root = Path(rf"C:\ProgramData\Autodesk\RVT {year}\Libraries")
        if not root.is_dir():
            continue
        for f in sorted(root.rglob("*.rfa"))[:25]:
            checked += 1
            info = read(f)
            if info.format_year != year:
                fails.append(f"{f.name} lives under RVT {year} but reports "
                             f"{info.format_year}")
            if not info.is_ole:
                fails.append(f"{f.name} is not an OLE compound document")
    if checked == 0 and require_installed:
        fails.append("no installed families found to check the parser "
                     "against; the compatibility logic was still tested")
    return fails


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for a in sys.argv[1:]:
            print(read(a).describe())
    else:
        problems = verify()
        for p in problems:
            print("FAIL " + p)
        print("rfa: ALL PASS" if not problems else f"rfa: {len(problems)} FAILED")
        raise SystemExit(1 if problems else 0)
