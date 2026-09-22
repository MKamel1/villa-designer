"""Inject the plan payload into the review-sheet template.

Kept separate from the template so the HTML stays readable and the page
is reproducible: re-run this after any spec change and republish.
"""
from __future__ import annotations

import json
from pathlib import Path

from .viewer_data import build

PLACEHOLDER = "__VIEWER_DATA__"
SVG_SLOT = "<!--SVG-->"


def render_page(spec_path: str | Path, dxf_path: str | Path,
                template: str | Path, out_path: str | Path,
                level: str | None = None) -> Path:
    data = build(spec_path, dxf_path, level)
    svg_text = data.pop("svg")

    html = Path(template).read_text(encoding="utf-8")
    if PLACEHOLDER not in html or SVG_SLOT not in html:
        raise ValueError("template is missing a required slot")

    # `</script` inside a JSON string would close the host <script> tag early.
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")

    html = html.replace(SVG_SLOT, svg_text)
    html = html.replace(PLACEHOLDER, payload)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
