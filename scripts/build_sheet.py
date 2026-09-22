"""Build the A3 1:50 sheet from a spec, plot it, and verify the scale.

    python scripts/build_sheet.py spec/apartment.yaml

Does the whole chain and then proves the result rather than assuming it:

    spec -> DXF (+ paper-space layout) -> DWG -> plotted PDF -> PNG
                                                            -> measured mm

The measurement is the point. "Plotted at 1:50" is a claim about paper
distance, so it is checked by measuring a known model distance in the PDF's
own vector geometry -- 10300 mm over the external wall faces must occupy
206.0 mm of paper -- not by trusting that the viewport maths held all the
way through AutoCAD.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from archpipe import acad, preview, sheet  # noqa: E402
from archpipe.model import load  # noqa: E402

PT_PER_MM = 72.0 / 25.4


def measure_pdf(pdf: Path) -> dict:
    """Page size and the widest/tallest vector path on the page, in paper mm."""
    import pymupdf

    doc = pymupdf.open(str(pdf))
    page = doc[0]
    widths: list[tuple[float, float]] = []
    for d in page.get_drawings():
        r = d["rect"]
        widths.append((r.width / PT_PER_MM, r.height / PT_PER_MM))
    widths.sort(key=lambda wh: -wh[0] * wh[1])
    return {
        "page_mm": (page.rect.width / PT_PER_MM, page.rect.height / PT_PER_MM),
        "paths": len(widths),
        "largest": widths[:8],
    }


def main(argv: list[str]) -> int:
    spec = Path(argv[0] if argv else "spec/apartment.yaml").resolve()
    root = Path(__file__).resolve().parents[1]
    out = root / "out"
    p = load(spec)
    level = argv[1] if len(argv) > 1 else p.levels[0].id
    stem = spec.stem

    src_dxf = out / f"{stem}_{level}.dxf"
    if not src_dxf.exists():
        raise SystemExit(f"{src_dxf} not found -- run `python -m archpipe build` first")

    sheet_dxf, info = sheet.add_sheet_to_dxf(
        src_dxf, out / f"{stem}_{level}_sheet.dxf", p, level=level,
        sheet_number="A-101", revision="A",
    )
    print(f"DXF  {sheet_dxf}")
    print(f"     layout {info.layout}  viewport {info.viewport_size[0]:.1f} x "
          f"{info.viewport_size[1]:.1f} mm  view height {info.view_height:.1f} mm")
    print(f"     viewport scale = 1:{info.measured_scale:g}")
    print(f"     model extents {info.model_extents} -> "
          f"{info.required_paper[0]:.1f} x {info.required_paper[1]:.1f} mm on paper")

    dwg = acad.to_dwg(sheet_dxf, out / f"{stem}_{level}_sheet.dwg")
    print(f"DWG  {dwg}")

    pdf = acad.plot_layout_pdf(dwg, out / f"{stem}_{level}_sheet.pdf", info.layout,
                               log=out / "_plot_layout.log")
    print(f"PDF  {pdf}")

    png = preview.rasterise_pdf(pdf, out / f"{stem}_{level}_sheet.png", dpi=150)
    print(f"PNG  {png}")

    m = measure_pdf(pdf)
    print(f"\npage {m['page_mm'][0]:.2f} x {m['page_mm'][1]:.2f} mm, "
          f"{m['paths']} vector paths")
    print("largest path bounding boxes (paper mm):")
    for w, h in m["largest"]:
        print(f"    {w:8.2f} x {h:8.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
