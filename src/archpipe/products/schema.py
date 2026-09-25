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

