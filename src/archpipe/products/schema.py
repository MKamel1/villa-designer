"""Categories, record kinds, claims, check states and style tags."""
from __future__ import annotations

KINDS = ("product", "appearance")
LAYERS = ("catalogue", "verified", "failed")
CHECK_STATES = ("passed", "failed", "not_checkable")
CLAIMS = ("manufacturer-supplied", "scan-of-product", "look-alike-proxy")

# Category -> the fields a record of that category should carry. Missing
# fields make their checks not_checkable; they never pass by default.
CATEGORIES = {
    "surface": {"appearance": ("maps", "real_size_mm"),
                "product": ("size_mm", "thickness_mm", "finish", "colour", "lrv", "slip", "water_absorption")},
    "paint": {"product": ("colour_lab", "lrv", "finish")},
    "fabric": {"appearance": ("maps", "real_size_mm"), "product": ("composition", "martindale", "width_mm")},
    "furniture": {"appearance": ("model", "dimensions_mm"), "product": ("dimensions_mm", "materials")},
    "decor": {"appearance": ("model", "dimensions_mm"), "product": ("dimensions_mm",)},
    "plant": {"appearance": ("model", "dimensions_mm"), "product": ("species", "mature_size_mm", "water_need")},
    "sanitary": {"product": ("dimensions_mm", "mounting", "flow_l_min", "revit_family")},
    "kitchen": {"product": ("dimensions_mm", "mounting", "revit_family")},
    "glazing": {"product": ("u_w_m2k", "g_value", "vt", "max_panel_mm", "sightline_mm")},
    "door": {"product": ("dimensions_mm", "finish")},
    "lighting": {"product": ("lumens", "cct_k", "cri", "watts", "dimensions_mm", "photometry")},
}

# Words in a source's tags/categories/name -> category.
CATEGORY_WORDS = [
    ("plant", ("plant", "tree", "potted", "flower", "shrub", "grass")),
    ("fabric", ("fabric", "textile", "boucle", "linen", "velvet", "leather", "carpet", "rug", "wool", "cotton")),
    ("paint", ("paint", "painted plaster")),
    ("furniture", ("furniture", "chair", "sofa", "table", "bed", "stool", "ottoman", "pouf", "cabinet", "shelf", "desk")),
    ("decor", ("decor", "vase", "book", "bowl", "lamp", "frame", "clock", "pot", "candle", "sculpture", "cushion")),
    ("surface", ("wood", "marble", "stone", "travertine", "concrete", "plaster", "tile", "terrazzo", "granite",
                 "metal", "brass", "floor", "wall", "slate", "limestone", "veneer", "brick", "onyx", "quartzite")),
]

# Style tags used to OVERSAMPLE (knowledge/projects/<p>/taste.json weights),
# never to exclude. Attribute words -> styles they evidence.
STYLE_WORDS = {
    "warm_contemporary": ("walnut", "travertine", "limestone", "boucle", "linen", "oak", "microcement", "brass",
                          "marble", "slat", "fluted"),
    "japandi": ("oak", "ash", "paper", "rice", "tatami", "linen", "light wood", "bamboo", "clay"),
    "scandinavian": ("oak", "ash", "birch", "pine", "wool", "white", "felt"),
    "glam_luxury": ("marble", "onyx", "brass", "gold", "velvet", "emperador", "calacatta", "nero"),
    "warm_transitional": ("shaker", "brass", "navy", "leather", "walnut", "classic"),
    "rustic_modern": ("reclaimed", "rough", "barn", "beam", "slate", "stone"),
}


def categorise(words: list[str]) -> str | None:
    text = " ".join(w.lower() for w in words)
    for cat, keys in CATEGORY_WORDS:
        if any(k in text for k in keys):
            return cat
    return None


def styles_for(words: list[str]) -> list[str]:
    text = " ".join(w.lower() for w in words)
    return sorted(s for s, keys in STYLE_WORDS.items() if any(k in text for k in keys))


# Diffuse reflectance limits for a base-colour map, from Time-Saver Standards for Interior Design 2nd ed.
# p. 1636 "Material and Color Light Reflectances" (card tss-reflectance-table): the brightest diffuse finish
# is dull or flat white at 75-90 %; the darkest non-pile finish is ultramarine blue at 3.5 % (black ink 4 %,
# black walnut 5-15 %); pile fabrics go far lower (black velvet 1.8 %, black velour 0.4 %).
ALBEDO_MAX = 0.90
ALBEDO_MIN_HARD = 0.035
ALBEDO_MIN_PILE = 0.004
PILE_WORDS = ("velvet", "velour", "plush", "pile", "chenille")


def albedo_limits(category: str | None, name: str | None) -> tuple[float, float]:
    """(lowest, highest) plausible mean diffuse reflectance for a material's base-colour map."""
    pile = (category == "fabric") and any(w in (name or "").lower() for w in PILE_WORDS)
    return (ALBEDO_MIN_PILE if pile else ALBEDO_MIN_HARD), ALBEDO_MAX



# ---------------------------------------------------------------------------
# Egypt-buyable product record (lane L4, A+ criterion I5). Additive: nothing
# above changes. A record is a plain dict (JSON in knowledge/products/
# eg-catalogue.json). A field that is not on the product page is None / empty
# and its name is listed in "missing"; a value is never invented.
# ---------------------------------------------------------------------------
EG_CATEGORIES = ("sofa", "armchair", "dining_table", "dining_chair", "bed", "wardrobe", "rug", "pendant",
                 "lamp", "outdoor_furniture", "terracotta_pot", "tile_stone", "paint", "sanitary", "kitchen",
                 "other")
EG_PRICE_MAX_AGE_DAYS = 90      # POLICY, a-plus-interior-renders.md I5
SKU_BASES = ("page-labelled", "url-embedded")   # url-embedded = id taken from the product URL, not a labelled SKU
ASSET_MATCH = ("exact", "look-alike")

# Fields every fully specified record carries (I5 needs sku, supplier, price, lead time).
EG_REQUIRED_FOR_PRICED = ("sku", "supplier", "url", "price_egp", "price_date")
EG_FIELDS = ("id", "category", "name", "brand", "sku", "sku_basis", "supplier", "url", "price_egp", "price_date",
             "price_note", "lead_time", "options", "lrv", "dimensions_mm", "asset_3d", "missing", "notes")


def eg_record_problems(rec: dict) -> list[str]:
    """Structural problems of one Egypt catalogue record (empty list = well-formed)."""
    p: list[str] = []
    for k in ("id", "category", "name", "url"):
        if not rec.get(k):
            p.append(f"{k} missing")
    if rec.get("category") and rec["category"] not in EG_CATEGORIES:
        p.append(f"category {rec['category']!r} not in EG_CATEGORIES")
    if rec.get("sku") and rec.get("sku_basis") not in SKU_BASES:
        p.append("sku given without sku_basis")
    price = rec.get("price_egp")
    if price is not None and (not isinstance(price, (int, float)) or price <= 0):
        p.append("price_egp must be a positive number or None")
    if price is not None and not rec.get("price_date"):
        p.append("price without price_date")
    dims = rec.get("dimensions_mm")
    if dims is not None:
        if not isinstance(dims, dict) or not any(dims.get(a) for a in ("w", "d", "h")):
            p.append("dimensions_mm must be {w,d,h} with at least one value, or None")
    a3 = rec.get("asset_3d")
    if a3 is not None:
        if not (a3.get("url") and a3.get("licence") and a3.get("match") in ASSET_MATCH):
            p.append("asset_3d needs url, licence and match in ASSET_MATCH")
    if rec.get("lrv") is not None and not (0 <= rec["lrv"] <= 100):
        p.append("lrv outside 0-100")
    # Pricing is optional (client scope change 2026-11-20): price_egp / price_date / lead_time may be empty
    # without being declared. Specification fields that are empty must be declared in "missing".
    declared = set(rec.get("missing") or [])
    for k in ("sku", "supplier", "dimensions_mm"):
        if not rec.get(k) and k not in declared:
            p.append(f"{k} empty but not listed in missing")
    return p


def eg_fully_priced(rec: dict) -> bool:
    """True if the record could stand as a priced FF&E row (sku, supplier, url, price + date)."""
    return all(rec.get(k) for k in EG_REQUIRED_FOR_PRICED)


def eg_fully_specified(rec: dict) -> bool:
    """True if the record can drive a model and a take-off: SKU, Egypt supplier, URL and the dimensions its
    category needs (W, D, H; rugs and tiles W, D only; paint needs an LRV instead of a size)."""
    if not (rec.get("sku") and rec.get("supplier") and rec.get("url")):
        return False
    cat = rec.get("category")
    if cat == "paint":
        return rec.get("lrv") is not None
    d = rec.get("dimensions_mm") or {}
    axes = ("w", "d") if cat in ("rug", "tile_stone") else ("w", "d", "h")
    return all(d.get(a) for a in axes)


def eg_price_age_days(rec: dict, today: str) -> int | None:
    from datetime import date
    if not rec.get("price_date"):
        return None
    return (date.fromisoformat(today) - date.fromisoformat(rec["price_date"])).days
