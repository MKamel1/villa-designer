"""L1b: DXF -> SVG plus the model<->SVG transform, for browser review.

The transform is the point of this module. A pin dropped on a picture is
a sticky note; a pin that resolves to model millimetres is an annotation
anchored to geometry the spec knows about, so a comment can be traced to
the wall or room it is actually about.

ezdxf's SVG backend normalises output into a fixed coordinate space
(1e6 wide, height by page aspect), fits the render box into it and
centres it, with Y flipped. All of that is deterministic, so the mapping
can be computed rather than guessed -- and `verify_transform` checks it
against the rendered geometry instead of trusting the arithmetic.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.addons.drawing.recorder import Recorder
from ezdxf.math import BoundingBox2d

from .preview import NON_PLOTTING

OUTPUT_SPACE = 1_000_000.0


@dataclass(frozen=True)
class Transform:
    """Maps SVG user units <-> model millimetres.

        model_x = minx + (svg_x - ox) / s
        model_y = maxy - (svg_y - oy) / s
    """
    s: float        # SVG units per millimetre
    ox: float       # SVG x of model minx
    oy: float       # SVG y of model maxy
    minx: float
    maxy: float
    vb_w: float
    vb_h: float

    def to_model(self, sx: float, sy: float) -> tuple[float, float]:
        return (self.minx + (sx - self.ox) / self.s,
                self.maxy - (sy - self.oy) / self.s)

    def to_svg(self, mx: float, my: float) -> tuple[float, float]:
        return (self.ox + (mx - self.minx) * self.s,
                self.oy + (self.maxy - my) * self.s)


def _compute_transform(bbox: BoundingBox2d, page_w: float, page_h: float) -> Transform:
    minx, miny = bbox.extmin.x, bbox.extmin.y
    maxx, maxy = bbox.extmax.x, bbox.extmax.y
    mw, mh = maxx - minx, maxy - miny
    vb_w = OUTPUT_SPACE
    vb_h = OUTPUT_SPACE * page_h / page_w
    s = min(vb_w / mw, vb_h / mh)
    return Transform(
        s=s,
        ox=(vb_w - s * mw) / 2,
        oy=(vb_h - s * mh) / 2,
        minx=minx, maxy=maxy, vb_w=vb_w, vb_h=vb_h,
    )


def render_svg(dxf_path: str | Path, page_w: float = 420.0, page_h: float = 297.0,
               show_non_plotting: bool = False) -> tuple[str, Transform, dict]:
    """Return (svg_text, transform, meta) for a DXF."""
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    def keep(e) -> bool:
        return show_non_plotting or e.dxf.layer not in NON_PLOTTING

    ctx = RenderContext(doc)
    # Must be passed in: draw_layout resets the context's own layout
    # properties, so setting the background on ctx beforehand is silently
    # discarded. Without a light background ACI colour 7 resolves to white
    # and the walls render white-on-white -- an apparently blank plan.
    lp = LayoutProperties.from_layout(msp)
    lp.set_colors(bg="#FFFFFF")

    rec = Recorder()
    Frontend(ctx, rec).draw_layout(msp, finalize=True, filter_func=keep,
                                   layout_properties=lp)
    player = rec.player()

    bbox = player.bbox()
    if not bbox.has_data:
        raise ValueError(f"{dxf_path} produced no drawable geometry")

    backend = svg.SVGBackend()
    player.replay(backend)
    page = layout.Page(page_w, page_h, layout.Units.mm, layout.Margins.all(0))
    root = backend.get_xml_root_element(page, render_box=bbox)
    text = ET.tostring(root, encoding="unicode")

    tf = _compute_transform(bbox, page_w, page_h)
    meta = {
        "extents_mm": {
            "minx": bbox.extmin.x, "miny": bbox.extmin.y,
            "maxx": bbox.extmax.x, "maxy": bbox.extmax.y,
        },
        "size_mm": {"w": bbox.extmax.x - bbox.extmin.x,
                    "h": bbox.extmax.y - bbox.extmin.y},
        "transform": asdict(tf),
    }
    return text, tf, meta


def verify_transform(tolerance_mm: float = 1.0) -> dict:
    """Check the mapping on BOTH fit branches, tall and wide.

    `_compute_transform` takes `min(vb_w/mw, vb_h/mh)`. A portrait-ish
    plan is height-limited and a wide, shallow one is width-limited, and
    only exercising one of them leaves half the arithmetic untested --
    a wide villa plan would be the first thing to hit the other branch.
    """
    cases = {
        # 1.25 aspect against a 1.414 page -> height-limited
        "tall": (10000.0, 8000.0),
        # 5.0 aspect against a 1.414 page -> width-limited
        "wide": (20000.0, 4000.0),
    }
    out = {"ok": True, "cases": {}}
    for name, (w, h) in cases.items():
        r = _verify_case(w, h, tolerance_mm)
        out["cases"][name] = r
        out["ok"] = out["ok"] and r["ok"]
    out["worst_error_mm"] = max(c["worst_error_mm"] for c in out["cases"].values())
    return out


def _verify_case(w: float, h: float, tolerance_mm: float) -> dict:
    """Render two axis-aligned lines of known length, read their endpoints
    back out of the SVG path data, and confirm the inverse transform lands
    on the coordinates they were drawn at."""
    doc = ezdxf.new("R2018", setup=True)
    msp = doc.modelspace()
    msp.add_line((0, 0), (w, 0))
    msp.add_line((0, 0), (0, h))

    rec = Recorder()
    Frontend(RenderContext(doc), rec).draw_layout(msp, finalize=True)
    player = rec.player()
    bbox = player.bbox()
    backend = svg.SVGBackend()
    player.replay(backend)
    page = layout.Page(420, 297, layout.Units.mm, layout.Margins.all(0))
    text = ET.tostring(backend.get_xml_root_element(page, render_box=bbox),
                      encoding="unicode")
    tf = _compute_transform(bbox, 420, 297)

    # Path data is "M <x> <y> l <dx> <dy>" for each straight line.
    paths = re.findall(r'\sd="M\s+(-?[\d.]+)\s+(-?[\d.]+)\s+l\s+(-?[\d.]+)\s+(-?[\d.]+)',
                       text)
    if len(paths) < 2:
        raise AssertionError(f"expected 2 calibration paths, parsed {len(paths)}")

    results = []
    expected = {(0.0, 0.0), (w, 0.0), (0.0, h)}
    for x, y, dx, dy in paths:
        for sx, sy in ((float(x), float(y)),
                       (float(x) + float(dx), float(y) + float(dy))):
            mx, my = tf.to_model(sx, sy)
            nearest = min(expected, key=lambda p: abs(p[0] - mx) + abs(p[1] - my))
            err = max(abs(nearest[0] - mx), abs(nearest[1] - my))
            results.append({"svg": (sx, sy), "model": (round(mx, 3), round(my, 3)),
                            "nearest_expected": nearest, "error_mm": round(err, 6)})

    worst = max(r["error_mm"] for r in results)
    ok = worst <= tolerance_mm
    # Round-trip every point back through to_svg as well.
    rt = max(
        max(abs(a - b) for a, b in zip(r["svg"], tf.to_svg(*r["model"])))
        for r in results
    )
    limited_by = "width" if (tf.vb_w / (w)) <= (tf.vb_h / (h)) else "height"
    return {"ok": ok, "worst_error_mm": worst, "roundtrip_svg_units": round(rt, 6),
            "limited_by": limited_by, "points": results}


def write_bundle(dxf_path: str | Path, out_dir: str | Path,
                 stem: str = "plan") -> dict:
    """Write plan.svg + plan.json (transform + extents) for the web viewer."""
    text, tf, meta = render_svg(dxf_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{stem}.svg").write_text(text, encoding="utf-8")
    (out / f"{stem}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta
