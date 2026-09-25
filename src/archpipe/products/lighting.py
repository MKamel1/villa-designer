"""Read-only view of the verified luminaire library as product records.

archpipe.luminaires keeps its own import, checks and index (flux vs LORL,
LDT vs manufacturer IES); this adapter only presents its verified rows in
the product shape so one search can list lighting beside other categories.
Nothing here writes to the luminaire library.
"""
from __future__ import annotations

from archpipe.luminaires import library as lib


def products(**filters) -> list[dict]:
    """Verified luminaire lamp sets as product dicts (kind 'product', category 'lighting')."""
    if not (lib.LIBRARY / "library.sqlite").is_file():
        return []
    out = []
    for r in lib.search(**filters):
        out.append({
            "id": f"luminaire:{r['manufacturer']}:{r['sku']}:{r['lamp_set']}", "kind": "product",
            "category": "lighting", "source": "luminaires", "key": f"{r['sku']}:{r['lamp_set']}",
            "name": r.get("name"), "brand": r["manufacturer"], "layer": "verified" if r["verified"] else "failed",
            "data": {"lumens": r.get("luminaire_lm"), "cct_k": r.get("cct_k"), "cri": r.get("cri_ra"),
                     "watts": r.get("watts"), "mount": r.get("mount"),
                     "dimensions_mm": [r.get("length_mm"), r.get("width_mm"), r.get("height_mm")],
                     "photometry": "manufacturer LDT (checked)"}})
    return out
