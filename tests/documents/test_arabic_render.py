"""Arabic on the produced sheets: glyph order and joining against an independent layout (PIL + libraqm).

Reference = the same font laid out by raqm and rasterised by PIL. Candidate = the sheet's own text path
(`plans._Sheet.text`) rasterised through the real PDF with PyMuPDF. Same font, same size: correct text overlaps the
reference (IoU high); reversed or unjoined text does not.
"""
import numpy as np
import pytest
from matplotlib import font_manager as fm
from PIL import Image, ImageFont

from archpipe.documents import plans

TEXTS = ["مسقط الدور الأرضي المفروش", "غرفة نوم الوالدين", "حمام العائلة"]
FONT = fm.findfont("DejaVu Sans")                    # first family on the sheets; carries the Arabic glyphs
PX = 80                                            # reference size in px; the sheet text is drawn at the same em


def _crop(a):
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _iou(a, b):
    h, w = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    pa, pb = np.zeros((h, w), bool), np.zeros((h, w), bool)
    pa[:a.shape[0], :a.shape[1]], pb[:b.shape[0], :b.shape[1]] = a, b
    return (pa & pb).sum() / (pa | pb).sum()


def reference(text):
    f = ImageFont.truetype(FONT, PX, layout_engine=ImageFont.Layout.RAQM)
    im = Image.new("L", (PX * len(text), PX * 2), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(im).text((10, 10), text, font=f, fill=255, direction="rtl", language="ar")
    return _crop(np.asarray(im) > 128)


def candidate(text, tmp_path, transform=lambda s: s):
    import pymupdf
    sh = plans._Sheet(0, 0, 0, 0, paper=(300.0, 40.0))
    sh.text((150, 20), transform(text), size=40)           # the sheets' own text path
    p = tmp_path / "t.pdf"
    sh.fig.savefig(p)
    pix = pymupdf.open(str(p))[0].get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
    return _crop(np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w) < 128)


def _score(text, got):
    ref = np.asarray(Image.fromarray(reference(text).astype(np.uint8) * 255).resize((got.shape[1], got.shape[0]))) > 128
    return _iou(ref, got)


@pytest.mark.parametrize("text", TEXTS)
def test_sheet_text_matches_raqm_reference(text, tmp_path):
    assert _score(text, candidate(text, tmp_path)) > 0.7, "Arabic glyph order or joining differs from the raqm layout"


@pytest.mark.parametrize("text", TEXTS)
def test_reversed_text_is_caught(text, tmp_path):
    """Negative test on the real defect (text fed in the wrong order): the same comparison must reject it."""
    assert _score(text, candidate(text, tmp_path, transform=lambda s: s[::-1])) < 0.45
