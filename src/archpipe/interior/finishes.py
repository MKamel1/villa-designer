"""Finish palettes: real products, their labelled render look-alikes and the true texture scale.

A palette file (knowledge/products/finishes/<id>.json) lists items. Each item is a REAL product with a maker
source quote, an Egypt availability record (or a marked gap), and for rendered items a look-alike material that is
never presented as the product. NO PRICES: a price-like key anywhere in an item is a problem.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PALETTE_DIR = Path(__file__).resolve().parents[3] / "knowledge" / "products" / "finishes"
LOOKALIKE_LABEL = "look-alike-proxy"
OPEN_LICENCES = ("CC0", "CC-BY")
# A key that looks like money is refused wherever it appears (client rule 2026-11-20/22: no pricing).
_PRICE_KEY = re.compile(r"price|cost|egp|usd|eur|fee|tariff|quote_amount", re.I)
# Format-based goods: one look-alike image stands for ONE format unit (tile, slab, board), so the image is
# mapped at the format's long side. Fabrics and veneers with no format use the look-alike scan's published size.
# Painted or lacquered surfaces are rendered as a flat colour (LRV + stated colour): no look-alike image, no scale.
FLAT_SLOTS = ("wall-paint", "kitchen-front")
FORMAT_SLOTS = ("floor-living", "floor-gf", "floor-wet", "bath-tile", "worktop", "backsplash", "garden-paving")


def _keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}" if path else k, k
            yield from _keys(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _keys(v, f"{path}[{i}]")


def _mm(v) -> float | None:
    """A format side in mm: a number, or a published range such as '1750-2350' (the longest is used)."""
    if isinstance(v, (int, float)):
        return float(v) or None
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(v or ""))]
    return max(nums) if nums else None


def texture_scale_m(item: dict) -> tuple[float, str]:
    """(tile_m, basis): the real-world width in metres that one look-alike image covers.

    Derived from the PRODUCT, never typed: format long side for format goods; otherwise the look-alike's own
    published scan size (Poly Haven 'dimensions'). Raises ValueError when neither is known, so a scale is never
    assumed (this replaces RF's assumed 0.6 m policy).
    """
    fmt = (item.get("product") or {}).get("format_mm") or {}
    sides = [m for m in (_mm(fmt.get("w")), _mm(fmt.get("l"))) if m]
    scan = (item.get("lookalike") or {}).get("physical_scan_mm")
    scan_mm = (max(scan) if isinstance(scan, (list, tuple)) else scan) if scan else None
    # A format smaller than the scan (a 100 mm tile on a 2 m scan) would shrink the image to noise: the scan's own
    # published size is then the true scale and shows several tiles.
    if item.get("slot") in FORMAT_SLOTS and sides and not (scan_mm and max(sides) < scan_mm / 4):
        return max(sides) / 1000.0, "format-long-side"
    if scan:
        s = max(scan) if isinstance(scan, (list, tuple)) else scan
        return float(s) / 1000.0, "lookalike-scan-size"
    raise ValueError(f"{item.get('id')}: no product format and no published scan size; texture scale cannot be derived")


def item_problems(item: dict) -> list[str]:
    p: list[str] = []
    iid = item.get("id", "?")
    prod = item.get("product") or {}
    src = item.get("source") or {}
    if not prod.get("maker"):
        p.append(f"{iid}: product.maker missing")
    if not src.get("url") or not src.get("quote"):
        p.append(f"{iid}: maker source (url + verbatim quote) missing")
    for path, k in _keys(item):
        if _PRICE_KEY.search(k):
            p.append(f"{iid}: price-like key {path!r} (no pricing anywhere)")
    eg = item.get("egypt")
    if eg is None:
        p.append(f"{iid}: egypt record missing (give a supplier or mark the gap)")
    elif eg.get("available") is not True and not eg.get("gap"):
        p.append(f"{iid}: not confirmed in Egypt but no gap stated")
    elif eg.get("available") is True and not (eg.get("supplier") and eg.get("url")):
        p.append(f"{iid}: Egypt availability claimed without a supplier and url")
    la = item.get("lookalike")
    if la is not None:
        if la.get("label") != LOOKALIKE_LABEL:
            p.append(f"{iid}: look-alike not labelled {LOOKALIKE_LABEL!r}")
        if not any(str(la.get("licence", "")).startswith(l) for l in OPEN_LICENCES):
            p.append(f"{iid}: look-alike licence {la.get('licence')!r} is not CC0/CC-BY")
        if not la.get("url"):
            p.append(f"{iid}: look-alike url missing")
    elif item.get("group") == "hard" and item.get("slot") not in FLAT_SLOTS:
        p.append(f"{iid}: hard finish without a look-alike")
    if item.get("lookalike") is not None:
        try:
            texture_scale_m(item)
        except ValueError as e:
            p.append(str(e))
    lrv = prod.get("lrv")
    if lrv is not None and not (0 <= lrv <= 100):
        p.append(f"{iid}: lrv outside 0-100")
    if lrv is not None and not prod.get("lrv_source"):
        p.append(f"{iid}: lrv without lrv_source")
    return p


def load_palette(pid: str, root: Path = PALETTE_DIR) -> dict:
    return json.loads((root / f"{pid}.json").read_text(encoding="utf-8"))


def palette_problems(pal: dict) -> list[str]:
    out: list[str] = []
    ids = [i.get("id") for i in pal.get("items", [])]
    if len(ids) != len(set(ids)):
        out.append("duplicate item ids")
    for it in pal.get("items", []):
        out += item_problems(it)
    return out
