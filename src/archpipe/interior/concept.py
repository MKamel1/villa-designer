"""The Concept record: one named design idea the whole interior is checked against."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Palette roles that feed the lighting calculation (ceiling / wall / floor reflectances).
SURFACE_ROLES = ("ceiling", "wall", "floor")


@dataclass
class PaletteColour:
    name: str
    role: str = "accent"                 # ceiling | wall | floor | joinery | textile | accent
    lrv: float | None = None             # light reflectance value 0-100 (manufacturer value or converted)
    lrv_source: str = ""                 # e.g. "Jotun colour page", "converted from Munsell value"
    paint_code: str = ""
    hex: str = ""
    product_id: str = ""                 # id in knowledge/products/eg-catalogue.json, if bought


@dataclass
class MaterialDef:
    name: str
    kind: str                            # wood | stone | metal | textile | ceramic | plaster | glass | other


@dataclass
class Concept:
    name: str
    statement: str
    palette: list[PaletteColour] = field(default_factory=list)
    materials: list[MaterialDef] = field(default_factory=list)
    banned: list[str] = field(default_factory=list)          # lower-case words; an item name/tag containing one is banned
    hero_products: dict[str, list[str]] = field(default_factory=dict)   # room -> catalogue product ids
    allowed_repeats: list[str] = field(default_factory=list)  # product ids the concept deliberately repeats (I4)

    def material_names(self) -> set[str]:
        return {m.name.lower() for m in self.materials}

    def material_kind(self, name: str) -> str | None:
        for m in self.materials:
            if m.name.lower() == name.lower():
                return m.kind
        return None


def load_concept(path: Path | str) -> Concept:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return Concept(
        name=d["name"], statement=d.get("statement", ""),
        palette=[PaletteColour(**c) for c in d.get("palette", [])],
        materials=[MaterialDef(**m) for m in d.get("materials", [])],
        banned=[b.lower() for b in d.get("banned", [])],
        hero_products=d.get("hero_products", {}), allowed_repeats=d.get("allowed_repeats", []))


def load_placed(path_or_dict) -> dict[str, list[dict]]:
    """room -> list of placed items. Accepts a path to JSON, or a dict.

    Shape: {"rooms": {"living": [{"id","name","category","product_id","materials":[...],
    "tags":[...]} ...]}}, or the bare room->items mapping. An item's "materials" are strings
    or {"name","kind"} dicts. The design model (lane L2) will feed the same shape.
    """
    d = json.loads(Path(path_or_dict).read_text(encoding="utf-8")) if isinstance(path_or_dict, (str, Path)) else path_or_dict
    return d.get("rooms", d)
