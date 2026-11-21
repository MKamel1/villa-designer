"""The client's existing building (omar.rvt), read from tracked frozen files in knowledge/existing/ (plan row U15/U16).

No Revit, no untracked `out/` file. Every file is checked against knowledge/existing/MANIFEST.json (sha256); a missing or
altered file raises `ExistingDataError` - the model never falls back silently (plan principle 1). A change to the
existing building comes from a new survey, which replaces these files and the manifest together.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parents[3] / "knowledge" / "existing"


class ExistingDataError(RuntimeError):
    pass


@lru_cache(maxsize=None)
def manifest() -> dict:
    p = DIR / "MANIFEST.json"
    if not p.is_file():
        raise ExistingDataError(f"existing-structure manifest missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _load(name: str):
    entry = manifest()["files"].get(name)
    if entry is None:
        raise ExistingDataError(f"{name} is not in the existing-structure manifest")
    p = DIR / name
    if not p.is_file():
        raise ExistingDataError(f"frozen existing-structure file missing: {p}")
    raw = p.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ExistingDataError(f"{name} does not match its manifest sha256 (edited or corrupt)")
    return json.loads(gzip.decompress(raw) if name.endswith(".gz") else raw)


def inventory() -> dict:
    return _load("omar-inventory.json")


def extract() -> dict:
    """The Revit 2027 extract of omar.rvt without mesh triangles (walls, openings, wall types, levels, site)."""
    return _load("omar-2027-extract.nomesh.json.gz")


def stairzone() -> dict:
    return _load("omar-stairzone.json.gz")


def wet_probe() -> dict:
    return _load("omar-wet.json")


def levels() -> list[dict]:
    return inventory()["levels"]


def slabs() -> list[dict]:
    """The three existing floor elements (whole-plot floors at Level 1; two are deleted in the design - see villa_env)."""
    return inventory()["floors"]


def kept_columns() -> list[dict]:
    """The existing structural columns: id, bbox (mm), name."""
    return inventory()["structural_columns"]


def match_column(x0: float, y0: float, x1: float, y1: float, tol_mm: float = 1.0) -> dict | None:
    """The existing column whose plan bbox equals the given rectangle within `tol_mm` (CAD and Revit differ by <0.5 mm)."""
    for c in kept_columns():
        (a, b, _), (p, q, _) = c["bbox"]["min"], c["bbox"]["max"]
        if max(abs(a - x0), abs(b - y0), abs(p - x1), abs(q - y1)) <= tol_mm:
            return c
    return None


def summary() -> dict:
    inv = inventory()
    return dict(columns=len(inv["structural_columns"]), floors=len(inv["floors"]), levels=len(inv["levels"]),
                grids=len(inv["grids"]), framing=len(inv.get("structural_framing", [])),
                walls=len(extract()["walls"]))
