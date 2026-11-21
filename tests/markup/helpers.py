import pymupdf as fitz
from archpipe.markup import frames as F


def mark(pdf_in, pdf_out, frames_data, no, level, x, y, text, kind="Text", author="Client", half_mm=0):
    """Put a PDF annotation at model (x, y) on the panel of `level` (placed through the frame: see test_frames for the
    independent check of the frame itself)."""
    fr = frames_data["sheets"][no]
    p = next(q for q in fr["panels"] if q["level"] == level)
    X, Y = F.model_to_page(fr, p, x, y)
    doc = fitz.open(str(pdf_in))
    pg = doc[0]
    if kind == "Square":
        r = fitz.Rect(X - half_mm * F.PT_PER_MM, Y - half_mm * F.PT_PER_MM, X + half_mm * F.PT_PER_MM, Y + half_mm * F.PT_PER_MM)
        a = pg.add_rect_annot(r)
    elif kind == "FreeText":
        a = pg.add_freetext_annot(fitz.Rect(X, Y, X + 60, Y + 14), text)
    else:
        a = pg.add_text_annot(fitz.Point(X, Y), text)
    a.set_info(content=text, title=author)
    a.update()
    doc.save(str(pdf_out))
    doc.close()
    return pdf_out


def red_rects(page, max_w=100):
    """Rects of the revision-red drawings (clouds), excluding the wide table."""
    return [d["rect"] for d in page.get_drawings() if d.get("color") and abs(d["color"][0] - 0.85) < 0.01 and d["color"][1] < 0.01 and d["rect"].width < max_w]
