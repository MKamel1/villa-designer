"""Draw a top-down diagnostic of exported furniture placements and front arrows."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def draw(scene_path: Path, output: Path, room: str = "living") -> Path:
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    models = [m for m in scene["models"] if m.get("room") == room and m["front_axis"] != "none"]
    if not models:
        raise ValueError("no directional furniture in " + room)
    for model in models:
        from archpipe.furniture_orientation import check_model_orientation
        check_model_orientation(model)
    xs = [m["position"][0] for m in models]
    ys = [m["position"][1] for m in models]
    x0, x1 = min(xs) - 2, max(xs) + 2
    y0, y1 = min(ys) - 2, max(ys) + 2
    width, height = 1200, 850
    scale = min((width - 160) / (x1 - x0), (height - 160) / (y1 - y0))
    image = Image.new("RGB", (width, height), "#f6f3eb")
    pen = ImageDraw.Draw(image)
    def screen(x, y):
        return (width / 2 + (x - (x0 + x1) / 2) * scale,
                height / 2 - (y - (y0 + y1) / 2) * scale)
    for model in models:
        cx, cy = model["position"][:2]
        w, d = model["footprint_w"], model["footprint_d"]
        yaw = math.radians(model["rotation_deg"][2])
        corners = []
        for dx, dy in ((-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2)):
            corners.append(screen(cx + dx*math.cos(yaw)-dy*math.sin(yaw),
                                  cy + dx*math.sin(yaw)+dy*math.cos(yaw)))
        color = "#c9d9cc" if "sofa" in model["id"] else "#d5c5aa"
        pen.polygon(corners, fill=color, outline="#324c47", width=3)
        sx, sy = screen(cx, cy)
        front_yaw = math.radians(model["layout_rotation_deg"])
        ex, ey = screen(cx - math.sin(front_yaw)*min(d*0.45, 0.55),
                        cy + math.cos(front_yaw)*min(d*0.45, 0.55))
        pen.line((sx, sy, ex, ey), fill="#bf4b32", width=8)
        pen.ellipse((ex-9, ey-9, ex+9, ey+9), fill="#bf4b32")
        pen.text((sx + 12, sy + 12), model["id"].removeprefix("model-"), fill="#233e39")
    pen.text((40, 28), "Garden-living furniture orientation | red arrow = layout front", fill="#233e39")
    pen.text((40, height - 42), "Top-down scene diagnostic; model envelopes shown, not a photoreal render", fill="#596b66")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


if __name__ == "__main__":
    print(draw(ROOT / "out/villa/render-d1/scene.json",
               ROOT / "out/villa/render-d1/preview-r3b1-orientation.png"))
