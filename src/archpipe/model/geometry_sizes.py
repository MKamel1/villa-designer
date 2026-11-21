"""Sizes for elements the generators leave without one (plan row A14): luminaires, dressing items, plants.

Never invented. Each size comes from a named record and the element says which (`params.size_basis`):
  * product luminaire  -> luminous opening in its IES LM-63 file (the file does not give the housing);
  * dressing item      -> the asset glTF POSITION bounding box times the placed scale;
  * generic luminaire  -> a dimension written in its own requirement text ("D300", "1.6 m"), else left unsized;
  * plant              -> the garden palette's height of the species (placed height when authored, else the range).
IES files and glTF assets live outside git, so `refresh()` freezes what it read into data/derived-sizes.json (tracked,
with the sha256 of each source); the model reads that table and raises if it is missing. Re-run
`python -m archpipe.model.geometry_sizes --refresh` on a machine that has the libraries.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from ..contracts import DesignElement

ROOT = Path(__file__).resolve().parents[3]
TABLE = Path(__file__).resolve().parent / "data" / "derived-sizes.json"
PALETTE = ROOT / "knowledge" / "garden-palette.json"
UNIT_M = {1: 0.3048, 2: 1.0}          # LM-63 units type: 1 feet, 2 metres


class SizeDataError(RuntimeError):
    pass


def table() -> dict:
    if not TABLE.is_file():
        raise SizeDataError(f"derived size table missing: {TABLE} (run geometry_sizes --refresh on a machine with the libraries)")
    return json.loads(TABLE.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------ reading sources
def ies_opening(path: Path) -> dict:
    from .. import photometry
    ph = photometry.load(path)
    k = UNIT_M[ph.units_type] * 1000.0
    w, l, h = ph.width, ph.length, ph.height
    if w < 0 and l < 0:                                   # LM-63: negative width/length = circular, diameter |w|
        d = round(abs(w) * k, 1)
        return dict(size_mm=[d, d, round(abs(h) * k, 1)], shape="circular", basis=f"IES LM-63 luminous opening, diameter {d} mm")
    return dict(size_mm=[round(abs(w) * k, 1), round(abs(l) * k, 1), round(abs(h) * k, 1)], shape="rectangular",
                basis="IES LM-63 luminous opening")


def _mat(node: dict):
    import numpy as np
    if "matrix" in node:
        return np.array(node["matrix"]).reshape(4, 4).T
    t = np.eye(4)
    s = node.get("scale", [1, 1, 1])
    S = np.diag([*s, 1.0])
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    R = np.eye(4)
    R[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                 [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                 [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    t[:3, 3] = node.get("translation", [0, 0, 0])
    return t @ R @ S


def gltf_bbox(path: Path) -> list[float]:
    """Native bounding box [dx, dy_up, dz] in metres of a glTF's POSITION accessors, node transforms applied."""
    import numpy as np
    g = json.loads(path.read_text(encoding="utf-8"))
    pts = []

    def walk(i, parent):
        n = g["nodes"][i]
        m = parent @ _mat(n)
        if "mesh" in n:
            for prim in g["meshes"][n["mesh"]]["primitives"]:
                a = g["accessors"][prim["attributes"]["POSITION"]]
                lo, hi = a["min"], a["max"]
                for cx in (lo[0], hi[0]):
                    for cy in (lo[1], hi[1]):
                        for cz in (lo[2], hi[2]):
                            pts.append((m @ np.array([cx, cy, cz, 1.0]))[:3])
        for c in n.get("children", []):
            walk(c, m)

    for r in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4))
    if not pts:
        raise SizeDataError(f"{path}: no mesh positions")
    a = np.array(pts)
    d = a.max(0) - a.min(0)
    return [round(float(v), 4) for v in d]


def refresh(ies_root: Path, assets_root: Path, elements: list[DesignElement], out: Path = TABLE) -> dict:
    """Read every product IES and dressing asset the model references and freeze the result."""
    lum, assets = {}, {}
    for e in elements:
        if e.kind == "luminaire" and e.product_id and e.product_id not in lum:
            mfr, code = e.product_id.split("/", 1)
            hits = sorted(ies_root.glob(f"**/{mfr}/{code}/{code}.ies")) + sorted(ies_root.glob(f"**/{mfr}/{code}.ies"))
            if not hits:
                raise SizeDataError(f"no IES file for {e.product_id} under {ies_root}")
            lum[e.product_id] = dict(ies_opening(hits[0]), sha256=hashlib.sha256(hits[0].read_bytes()).hexdigest())
        elif e.kind in ("furniture", "plant") and e.product_id and e.product_id not in assets:
            p = assets_root / e.product_id / "model.gltf"
            if p.is_file():
                dx, dy, dz = gltf_bbox(p)
                assets[e.product_id] = dict(size_mm=[round(dx * 1000, 1), round(dz * 1000, 1), round(dy * 1000, 1)],
                                            basis="glTF POSITION bounding box (w, d, h = x, z, y-up), native scale",
                                            sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    t = dict(schema="derived-sizes/1", luminaires=dict(sorted(lum.items())), assets=dict(sorted(assets.items())))
    out.write_text(json.dumps(t, indent=1), encoding="utf-8")
    return t


# ------------------------------------------------------------------------------------------------ applying
_D = re.compile(r"\bD(\d{2,4})\b")
_LEN = re.compile(r"(\d+(?:\.\d+)?)\s*m\b(?!m)")


def _text_dims(what: str) -> tuple[list[float] | None, str]:
    m = _D.search(what)
    if m:
        d = float(m.group(1))
        return [d, d, 0.0], f"authored in the requirement text ('D{m.group(1)}'): diameter; height not given"
    m = _LEN.search(what)
    if m:
        return [round(float(m.group(1)) * 1000, 1), 0.0, 0.0], f"authored in the requirement text ('{m.group(0)}'): length; section not given"
    return None, ""


def _palette_heights() -> dict[str, dict]:
    out = {}
    for sp in json.loads(PALETTE.read_text(encoding="utf-8"))["species"]:
        h = sp.get("height", {}).get("range_m")
        placed = [a["height"]["range_m"] for a in (sp.get("placement_assumptions") or {}).values() if a.get("height")]
        out[sp["species"]] = dict(range_m=h, placed_m=placed[0] if placed else None)
    return out


def apply(elements: list[DesignElement]) -> list[DesignElement]:
    """Fill sizes in place where the element has none; always set params.size_basis. Returns the same list."""
    t = table()
    pal = _palette_heights()
    for e in elements:
        zero = not any(e.size)
        if e.kind == "luminaire":
            if e.product_id:
                rec = t["luminaires"].get(e.product_id)
                if rec is None:
                    raise SizeDataError(f"{e.id}: product {e.product_id} missing from the derived size table")
                e.size = tuple(rec["size_mm"])
                e.params["size_basis"] = rec["basis"] + "; housing depth and trim not in the file"
            elif e.size[0] > 0:
                e.params["size_basis"] = "authored run length (strip); section not authored"
            else:
                dims, basis = _text_dims(e.params.get("what", ""))
                e.size = tuple(dims) if dims else e.size
                e.params["size_basis"] = basis or "not derivable: generic fixture, no bound product, no dimension in the requirement"
        elif e.kind == "furniture" and e.params.get("type") == "dressing":
            rec = t["assets"].get(e.product_id)
            sc = e.params.get("scale", 1.0)
            if rec and isinstance(sc, (int, float)):
                e.size = tuple(round(v * sc, 1) for v in rec["size_mm"])
                e.params["size_basis"] = f"{rec['basis']}, times placed scale {sc}"
            else:
                e.params["size_basis"] = "not derivable: asset not in the derived size table"
        elif e.kind == "furniture":
            e.params["size_basis"] = "authored in the furniture layout" + ("" if not zero else " (a zero extent is authored: flush tray)")
        elif e.kind == "plant":
            h = pal.get(e.params.get("species", ""))
            if h and h["placed_m"]:
                e.size = (e.size[0], e.size[1], round(h["placed_m"][1] * 1000, 1))
                e.params.update(height_m=h["placed_m"][1], size_basis="garden palette: placed height of the species (ASSUMED within the verified range)")
            elif h and h["range_m"]:
                e.params.update(height_range_m=list(h["range_m"]),
                                size_basis="garden palette height range of the species; no placed height authored, so size height stays 0")
            else:
                e.params["size_basis"] = "not derivable: species not in the garden palette"
    return elements


def unsized(elements: list[DesignElement]) -> list[str]:
    return [e.id for e in elements if e.kind in ("luminaire", "plant", "furniture") and not e.size[0] and not e.size[2]
            and not (e.kind == "luminaire" and e.size[0])]


if __name__ == "__main__":
    import argparse
    from . import api
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--ies-root", default=str(Path.home() / "archpipe/data/assets/user/luminaires"))
    ap.add_argument("--assets-root", default=str(Path.home() / "archpipe/assets/library/props"))
    a = ap.parse_args()
    if a.refresh:
        t = refresh(Path(a.ies_root), Path(a.assets_root), api.load("D1"))
        print(len(t["luminaires"]), "luminaire products,", len(t["assets"]), "assets")
