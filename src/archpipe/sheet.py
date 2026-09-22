"""A3 paper-space sheet: frame, title block, north arrow, scale bar.

Plotting model-space extents "fitted to A3" produces a drawing that is
correct and unmeasurable: nothing on it is at a stated scale, so a reader
cannot put a rule on it. A real drawing is a *sheet* -- a paper-space
layout at 1:1, containing a viewport that shows the model at a declared
scale, inside a title block that states that scale.

Everything in this module is in PAPER space, where one drawing unit is
one millimetre on the sheet. That is the whole trick:

    the viewport shows `view_height` model mm across `height` paper mm,
    so the scale is height / view_height

and 1:50 is therefore `view_height = 50 * height`. There is no "scale"
attribute on a VIEWPORT to set -- AutoCAD derives the number it shows in
the Properties palette from exactly that ratio. Plot the layout at 1:1
(not "fit") and the ratio survives onto the paper; see
`acad.plot_layout_pdf`.

The sheet is built for the full-bleed A3 paper size, so paper-space
(0,0) is the corner of the sheet itself. With a bordered paper size the
printable area is smaller than the paper and the frame drawn here would
be clipped.
"""
from __future__ import annotations

import datetime as _dt
import getpass
from dataclasses import dataclass, replace
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.enums import TextEntityAlignment

from . import layers as std

# No spaces and no colon: script lines fed to accoreconsole treat
# whitespace as Enter, so "A3 - 1:50" would answer three prompts.
LAYOUT_NAME = "A3-1-50"

PAPER: tuple[float, float] = (420.0, 297.0)   # A3 landscape, millimetres

# Frame inset from the paper edge: wider on the left for binding.
MARGIN_LEFT, MARGIN_EDGE = 20.0, 10.0

# Title block, bottom right, measured from the frame's bottom-right corner.
TB_WIDTH, TB_HEIGHT = 180.0, 70.0

# Clear space kept between the viewport and the frame / title block.
VP_GAP = 4.0


class SheetError(RuntimeError):
    """The drawing does not fit the sheet at the requested scale."""


@dataclass(frozen=True)
class TitleBlock:
    """Everything the title block states. Populated from L0 where it exists."""
    project: str
    title: str
    level: str
    scale: str
    units: str
    sheet_size: str
    date: str
    drawn_by: str
    revision: str
    sheet_number: str


@dataclass(frozen=True)
class SheetInfo:
    """What was actually built, so the caller can assert on it."""
    layout: str
    paper: tuple[float, float]
    scale_denom: float
    viewport_centre: tuple[float, float]     # paper mm
    viewport_size: tuple[float, float]       # paper mm
    view_centre: tuple[float, float]         # model mm
    view_height: float                       # model mm across the viewport
    model_extents: tuple[float, float, float, float]   # minx, miny, maxx, maxy
    required_paper: tuple[float, float]      # model extents at the scale, mm

    @property
    def measured_scale(self) -> float:
        """Denominator implied by the geometry. Must equal `scale_denom`."""
        return self.view_height / self.viewport_size[1]


def title_block_from(project=None, level: str | None = None, *,
                     scale_denom: float = 50.0, **overrides) -> TitleBlock:
    """Build the title block content, taking what L0 offers and defaulting the rest.

    `project` is a model.Project or None. Anything in `overrides` wins, so a
    caller can set the sheet number and revision without touching the spec.
    """
    level_name = level or ""
    if project is not None:
        for lvl in getattr(project, "levels", ()):
            if level is None or lvl.id == level:
                level_name = f"{lvl.id}  {lvl.name}"
                break

    tb = TitleBlock(
        project=getattr(project, "name", "Untitled Project"),
        title="GENERAL ARRANGEMENT PLAN",
        level=level_name or "-",
        scale=f"1:{scale_denom:g}",
        units=getattr(project, "units", "mm"),
        sheet_size="A3",
        date=_dt.date.today().isoformat(),
        drawn_by=getpass.getuser().upper(),
        revision="A",
        sheet_number="A-101",
    )
    unknown = set(overrides) - set(tb.__dataclass_fields__)
    if unknown:
        raise TypeError(f"unknown title block field(s): {sorted(unknown)}")
    return replace(tb, **{k: v for k, v in overrides.items() if v is not None})


# ---------------------------------------------------------------------------
# drawing helpers -- all coordinates are paper millimetres
# ---------------------------------------------------------------------------

def _rect(psp, x0: float, y0: float, x1: float, y1: float, layer: str):
    return psp.add_lwpolyline(
        [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
        dxfattribs={"layer": layer},
    )


def _text(psp, s: str, at: tuple[float, float], height: float, layer: str,
          align=TextEntityAlignment.LEFT):
    return psp.add_text(
        s, height=height,
        dxfattribs={"layer": layer, "style": std.TEXT_STYLE},
    ).set_placement(at, align=align)


def _cell(psp, x0: float, y0: float, x1: float, y1: float,
          caption: str, value: str, value_kind: str = "field") -> None:
    """One title block field: small caption top-left, value below it."""
    pad = 2.0
    _text(psp, caption, (x0 + pad, y1 - pad - std.sheet_text_height("caption")),
          std.sheet_text_height("caption"), "A-SHET-TEXT")
    _text(psp, value, (x0 + pad, y0 + pad + 0.6),
          std.sheet_text_height(value_kind), "A-SHET-TEXT")


def _draw_frame(psp) -> tuple[float, float, float, float]:
    """Sheet border. Returns the frame rectangle (x0, y0, x1, y1)."""
    w, h = PAPER
    x0, y0 = MARGIN_LEFT, MARGIN_EDGE
    x1, y1 = w - MARGIN_EDGE, h - MARGIN_EDGE
    _rect(psp, x0, y0, x1, y1, "A-SHET-BDER")
    return x0, y0, x1, y1


def _draw_title_block(psp, frame: tuple[float, float, float, float],
                      tb: TitleBlock) -> tuple[float, float, float, float]:
    """ISO-style title block in the bottom right. Returns its rectangle."""
    _, fy0, fx1, _ = frame
    x0, y0 = fx1 - TB_WIDTH, fy0
    x1, y1 = fx1, fy0 + TB_HEIGHT

    _rect(psp, x0, y0, x1, y1, "A-SHET-TTLB")

    # Five rows, bottom up. The two lowest are split into three columns.
    rows = [y0, y0 + 15, y0 + 27, y0 + 39, y0 + 53, y1]
    for y in rows[1:-1]:
        psp.add_line((x0, y), (x1, y), dxfattribs={"layer": "A-SHET-TTLB"})

    third = TB_WIDTH / 3
    cols = [x0, x0 + third, x0 + 2 * third, x1]
    for y_lo, y_hi in ((rows[0], rows[1]), (rows[1], rows[2])):
        for x in cols[1:-1]:
            psp.add_line((x, y_lo), (x, y_hi), dxfattribs={"layer": "A-SHET-TTLB"})
    # The level cell shares row 2 with the sheet size cell.
    psp.add_line((cols[1], rows[2]), (cols[1], rows[3]),
                 dxfattribs={"layer": "A-SHET-TTLB"})

    _cell(psp, cols[0], rows[0], cols[1], rows[1], "DRAWN BY", tb.drawn_by)
    _cell(psp, cols[1], rows[0], cols[2], rows[1], "DATE", tb.date)
    _cell(psp, cols[2], rows[0], cols[3], rows[1], "SHEET No.", tb.sheet_number,
          "sheet_no")

    _cell(psp, cols[0], rows[1], cols[1], rows[2], "SCALE", tb.scale)
    _cell(psp, cols[1], rows[1], cols[2], rows[2], "UNITS", tb.units)
    _cell(psp, cols[2], rows[1], cols[3], rows[2], "REV", tb.revision)

    _cell(psp, cols[0], rows[2], cols[1], rows[3], "SHEET SIZE", tb.sheet_size)
    _cell(psp, cols[1], rows[2], cols[3], rows[3], "LEVEL", tb.level, "level")

    _cell(psp, x0, rows[3], x1, rows[4], "DRAWING TITLE", tb.title, "title")
    _cell(psp, x0, rows[4], x1, rows[5], "PROJECT", tb.project, "project")
    return x0, y0, x1, y1


def _draw_north(psp, cx: float, cy: float, r: float = 11.0) -> None:
    """Conventional half-filled north point with an N above it."""
    psp.add_circle((cx, cy), r, dxfattribs={"layer": "A-SHET-NORT"})

    tip = (cx, cy + r * 0.78)
    waist = (cx, cy - r * 0.35)
    left = (cx - r * 0.34, cy - r * 0.72)
    right = (cx + r * 0.34, cy - r * 0.72)
    # Solid west half, open east half -- reads as a direction, not a diamond.
    psp.add_solid([tip, left, waist, waist], dxfattribs={"layer": "A-SHET-NORT"})
    psp.add_lwpolyline([tip, right, waist], close=True,
                       dxfattribs={"layer": "A-SHET-NORT"})

    _text(psp, "N", (cx, cy + r + 1.5), std.sheet_text_height("north"),
          "A-SHET-NORT", align=TextEntityAlignment.BOTTOM_CENTER)


def _bar_metres(scale_denom: float) -> tuple[float, int]:
    """Pick a round division (metres) and a count giving a 70-120 mm bar."""
    for step in (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0):
        for count in (10, 8, 6, 5, 4):
            paper = step * 1000.0 * count / scale_denom
            if 70.0 <= paper <= 120.0:
                return step, count
    return 1.0, 5


def _draw_scale_bar(psp, x0: float, y0: float, scale_denom: float) -> float:
    """Alternating graphic scale bar with its left end at (x0, y0). Returns width."""
    step_m, count = _bar_metres(scale_denom)
    seg = step_m * 1000.0 / scale_denom          # one division, paper mm
    h = 3.0
    label_h = std.sheet_text_height("caption")

    for i in range(count):
        xa, xb = x0 + i * seg, x0 + (i + 1) * seg
        if i % 2 == 0:
            psp.add_solid([(xa, y0), (xb, y0), (xa, y0 + h), (xb, y0 + h)],
                          dxfattribs={"layer": "A-SHET-SCLE"})
        else:
            _rect(psp, xa, y0, xb, y0 + h, "A-SHET-SCLE")
    _rect(psp, x0, y0, x0 + count * seg, y0 + h, "A-SHET-SCLE")

    # Label every other division so the numbers never collide.
    for i in range(0, count + 1, 2):
        val = i * step_m
        s = f"{val:g}" if i < count else f"{val:g} m"
        _text(psp, s, (x0 + i * seg, y0 - label_h - 1.5), label_h,
              "A-SHET-SCLE", align=TextEntityAlignment.BOTTOM_CENTER)

    _text(psp, f"SCALE  1:{scale_denom:g}", (x0, y0 + h + 2.0),
          std.sheet_text_height("field"), "A-SHET-SCLE")
    return count * seg


def _model_extents(msp) -> tuple[float, float, float, float]:
    ext = bbox.extents(msp, fast=False)
    if not ext.has_data:
        raise SheetError("model space is empty -- nothing to put in the viewport")
    return (ext.extmin.x, ext.extmin.y, ext.extmax.x, ext.extmax.y)


# ---------------------------------------------------------------------------
# the sheet
# ---------------------------------------------------------------------------

def add_sheet(doc, project=None, *, level: str | None = None,
              name: str = LAYOUT_NAME, scale_denom: float = 50.0,
              device: str = "DWG To PDF.pc3",
              paper_name: str = "ISO full bleed A3 (420.00 x 297.00 MM)",
              strict: bool = True, **title_fields) -> SheetInfo:
    """Add an A3 paper-space layout showing model space at 1:`scale_denom`.

    Replaces the layout if it already exists, so rebuilding is idempotent.
    Raises SheetError if the model does not fit the viewport at that scale;
    pass strict=False to plot it anyway and accept the clipping.
    """
    std.apply_sheet(doc)
    tb = title_block_from(project, level, scale_denom=scale_denom, **title_fields)

    if name in doc.layouts:
        doc.layouts.delete(name)
    psp = doc.layouts.new(name)
    psp.page_setup(size=PAPER, margins=(0, 0, 0, 0), units="mm",
                   scale=(1, 1), name=name, device=device)
    # page_setup composes its own paper name; use the one AutoCAD knows so the
    # layout opens on the right sheet in the GUI as well as under -PLOT.
    psp.dxf_layout.dxf.paper_size = paper_name

    # page_setup creates the overall paper-space viewport (id 1) covering the
    # whole sheet. It is not a drawing viewport and must be left alone.
    frame = _draw_frame(psp)
    tb_rect = _draw_title_block(psp, frame, tb)

    fx0, fy0, fx1, fy1 = frame
    vx0, vx1 = fx0 + VP_GAP, fx1 - VP_GAP
    vy0, vy1 = tb_rect[3] + VP_GAP, fy1 - VP_GAP
    vw, vh = vx1 - vx0, vy1 - vy0

    minx, miny, maxx, maxy = _model_extents(doc.modelspace())
    need = ((maxx - minx) / scale_denom, (maxy - miny) / scale_denom)
    if strict and (need[0] > vw + 1e-6 or need[1] > vh + 1e-6):
        raise SheetError(
            f"model is {need[0]:.1f} x {need[1]:.1f} mm on paper at "
            f"1:{scale_denom:g} but the viewport is only {vw:.1f} x {vh:.1f} mm. "
            f"Use a smaller scale, a larger sheet, or strict=False."
        )

    view_centre = ((minx + maxx) / 2, (miny + maxy) / 2)
    psp.add_viewport(
        center=((vx0 + vx1) / 2, (vy0 + vy1) / 2),
        size=(vw, vh),
        view_center_point=view_centre,
        view_height=vh * scale_denom,     # <- the scale, and the only place it lives
        dxfattribs={"layer": "A-SHET-VPRT"},
    )
    _rect(psp, vx0, vy0, vx1, vy1, "A-SHET-VPRT")

    _draw_north(psp, fx1 - 25.0, fy1 - 32.0)
    _draw_scale_bar(psp, fx0 + 10.0, fy0 + 22.0, scale_denom)

    return SheetInfo(
        layout=name, paper=PAPER, scale_denom=scale_denom,
        viewport_centre=((vx0 + vx1) / 2, (vy0 + vy1) / 2),
        viewport_size=(vw, vh), view_centre=view_centre,
        view_height=vh * scale_denom,
        model_extents=(minx, miny, maxx, maxy), required_paper=need,
    )


def add_sheet_to_dxf(dxf_in: str | Path, dxf_out: str | Path, project=None, *,
                     level: str | None = None, scale_denom: float = 50.0,
                     **kwargs) -> tuple[Path, SheetInfo]:
    """Read a rendered DXF, add the sheet layout, write it out again."""
    doc = ezdxf.readfile(str(dxf_in))
    info = add_sheet(doc, project, level=level, scale_denom=scale_denom, **kwargs)
    out = Path(dxf_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out)
    return out, info
