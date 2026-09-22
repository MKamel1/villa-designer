"""Drawing standard: layers, lineweights, text and dimension styles.

Layer naming follows the common ISO 13567-derived convention used in
practice (agent-prefixed, element-keyed): A-WALL, A-DOOR, A-GLAZ, ...
Everything the standard governs lives here, so changing office
convention is a one-file edit rather than a hunt through the renderer.

Lineweights are in 1/100 mm, matching the DXF encoding: 50 == 0.50 mm.
"""
from __future__ import annotations

from dataclasses import dataclass

# ACI colours: 7=white/black, 8=dark grey, 9=light grey, 1=red, 3=green, 5=blue
WHITE, DGREY, LGREY, RED, GREEN, BLUE, CYAN, YELLOW = 7, 8, 9, 1, 3, 5, 4, 2


@dataclass(frozen=True)
class LayerDef:
    name: str
    color: int
    lineweight: int      # 1/100 mm
    linetype: str = "CONTINUOUS"
    plot: bool = True
    description: str = ""


LAYERS: tuple[LayerDef, ...] = (
    LayerDef("A-WALL",      WHITE, 50, description="Walls cut by the section plane"),
    LayerDef("A-WALL-PATT", DGREY, 9,  description="Wall poche / hatch"),
    LayerDef("A-DOOR",      GREEN, 25, description="Door leaves and swings"),
    LayerDef("A-GLAZ",      CYAN,  25, description="Windows and glazing"),
    LayerDef("A-ROOM-BDRY", LGREY, 9,  "ARCH-DASHED", plot=False,
             description="Room boundary polygons, non-plotting"),
    LayerDef("A-ROOM-IDEN", BLUE,  18, description="Room names, numbers and areas"),
    LayerDef("A-ANNO-DIMS", RED,   18, description="Dimensions"),
    LayerDef("A-ANNO-TEXT", WHITE, 18, description="General annotation"),
    LayerDef("A-GRID",      YELLOW, 9, "ARCH-CENTER", description="Structural grid"),
)

# Text heights in mm at 1:1 model scale. A 1:50 plan wants 2.5 mm on paper,
# so model height = paper height * scale denominator.
TEXT_PAPER_MM = {"room_name": 2.5, "room_area": 2.0, "dim": 2.5, "note": 2.5}

TEXT_STYLE = "ARCH"
TEXT_FONT = "isocp.shx"
DIM_STYLE = "ARCH-50"


def model_text_height(kind: str, scale_denom: float) -> float:
    """Model-space text height so it plots at the intended paper size."""
    return TEXT_PAPER_MM[kind] * scale_denom


def apply(doc, scale_denom: float = 50.0) -> None:
    """Create every layer, the text style and the dimension style on `doc`."""
    # Our own names, not DASHED/CENTER: ezdxf's setup=True defines those at
    # imperial-ish dash lengths that are invisible at millimetre scale.
    for name, pattern in _LT_PATTERNS.items():
        if name not in doc.linetypes:
            doc.linetypes.add(name, pattern=pattern, description=name)

    for ld in LAYERS:
        layer = doc.layers.add(ld.name) if ld.name not in doc.layers else doc.layers.get(ld.name)
        layer.color = ld.color
        layer.dxf.lineweight = ld.lineweight
        layer.dxf.linetype = ld.linetype
        layer.description = ld.description
        if not ld.plot:
            layer.dxf.plot = 0

    if TEXT_STYLE not in doc.styles:
        doc.styles.add(TEXT_STYLE, font=TEXT_FONT)

    if DIM_STYLE not in doc.dimstyles:
        ds = doc.dimstyles.add(DIM_STYLE)
        h = model_text_height("dim", scale_denom)
        ds.dxf.dimtxt = h              # text height
        ds.dxf.dimasz = h * 0.7        # arrow / tick size
        ds.dxf.dimexe = h * 0.5        # extension beyond dim line
        ds.dxf.dimexo = h * 0.4        # extension line offset from origin
        ds.dxf.dimgap = h * 0.3        # gap around text
        ds.dxf.dimtxsty = TEXT_STYLE
        ds.dxf.dimclrd = RED           # dim line colour
        ds.dxf.dimclre = RED           # extension line colour
        ds.dxf.dimclrt = RED           # text colour
        ds.dxf.dimdec = 0              # whole millimetres
        ds.dxf.dimlunit = 2            # decimal
        ds.dxf.dimtih = 0              # text aligned with dim line
        ds.dxf.dimtoh = 0
        ds.dxf.dimblk = "ARCHTICK"     # architectural tick, not arrowheads
        ds.dxf.dimscale = 1.0


_LT_PATTERNS = {
    # [total pattern length, dash, gap, ...] in model mm
    "ARCH-DASHED": [300.0, 200.0, -100.0],
    "ARCH-CENTER": [800.0, 600.0, -100.0, 50.0, -100.0],
}


# ---------------------------------------------------------------------------
# Sheet / paper space standard.  Appended for the A3 1:50 layout (sheet.py).
#
# Everything below lives in PAPER space, where one drawing unit is one
# millimetre on the sheet. Heights here are therefore final plotted sizes and
# must NOT be passed through model_text_height(), which multiplies by the
# plot scale.
# ---------------------------------------------------------------------------

SHEET_LAYERS: tuple[LayerDef, ...] = (
    LayerDef("A-SHET-BDER", WHITE, 70, description="Sheet frame / border, paper space"),
    LayerDef("A-SHET-TTLB", WHITE, 35, description="Title block linework, paper space"),
    LayerDef("A-SHET-TEXT", WHITE, 18, description="Title block and sheet text"),
    LayerDef("A-SHET-NORT", WHITE, 35, description="North arrow"),
    LayerDef("A-SHET-SCLE", WHITE, 25, description="Graphic scale bar"),
    LayerDef("A-SHET-VPRT", LGREY, 9, plot=False,
             description="Viewport boundary, non-plotting"),
)

# Plotted text heights in mm ON THE SHEET. No scale factor applies.
SHEET_TEXT_MM = {
    "caption": 1.8,    # the small field label inside a title block cell
    "field": 2.5,      # an ordinary field value
    "level": 3.0,
    "project": 3.5,
    "title": 5.0,      # the drawing title
    "sheet_no": 6.0,   # the sheet number, deliberately the loudest thing
    "north": 5.0,
}


def sheet_text_height(kind: str) -> float:
    """Paper-space text height in mm. Unlike model_text_height, no scaling."""
    return SHEET_TEXT_MM[kind]


def apply_sheet(doc) -> None:
    """Create the paper-space layers. Safe to call after (or without) apply()."""
    for ld in SHEET_LAYERS:
        layer = (doc.layers.add(ld.name) if ld.name not in doc.layers
                 else doc.layers.get(ld.name))
        layer.color = ld.color
        layer.dxf.lineweight = ld.lineweight
        layer.dxf.linetype = ld.linetype
        layer.description = ld.description
        layer.dxf.plot = 1 if ld.plot else 0

    if TEXT_STYLE not in doc.styles:
        doc.styles.add(TEXT_STYLE, font=TEXT_FONT)
