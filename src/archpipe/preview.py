"""Fast PNG preview of a DXF. No Autodesk, no plotting round-trip.

Exists so a spec change can be eyeballed in about a second instead of
going through the accoreconsole plot, which takes tens of seconds.

The `bg` argument matters more than it looks: ezdxf maps ACI colour 7 to
white on a dark background and black on a light one. Rendering onto a
white figure without telling the frontend produces white-on-white walls,
i.e. an apparently empty drawing.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import ezdxf
from ezdxf.addons.drawing.matplotlib import qsave

# Layers carrying construction information rather than drawn output.
NON_PLOTTING = {"A-ROOM-BDRY", "DEFPOINTS"}


def preview(dxf_path: str | Path, png_path: str | Path, dpi: int = 120,
            show_non_plotting: bool = False) -> Path:
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    def keep(e) -> bool:
        return show_non_plotting or e.dxf.layer not in NON_PLOTTING

    out = Path(png_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    qsave(msp, str(out), bg="#FFFFFF", dpi=dpi, filter_func=keep)
    return out


def rasterise_pdf(pdf_path: str | Path, png_path: str | Path, dpi: int = 100,
                  page: int = 0) -> Path:
    """Render a plotted PDF back to PNG, so the plot can actually be checked.

    The DXF preview above never touches AutoCAD, the CTB or lineweights, so
    it does not verify the plot. This does. Note that SHX text arrives as
    stroked vectors, not selectable text -- switch the text style to a
    TrueType font if searchable PDF text is wanted.
    """
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    out = Path(png_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc[page].get_pixmap(dpi=dpi).save(str(out))
    return out
