"""Generate a small authored villa scene and optionally render it remotely."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.photometry import load as load_ies
from archpipe.safe_io import copy_file, save_bytes
from archpipe.villa_render_contract import validate_scene


def box(ident, bounds, material, group="shell", room="test-room", label=""):
    x0, y0, z0, x1, y1, z1 = bounds
    v = [(x0,y0,z0), (x1,y0,z0), (x1,y1,z0), (x0,y1,z0),
         (x0,y0,z1), (x1,y0,z1), (x1,y1,z1), (x0,y1,z1)]
    faces = [(3,2,1,0), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]
    return {"id": ident, "group": group, "material": material, "room": room,
            "label": label, "faces": [[list(v[i]) for i in face] for face in faces]}


def make_scene(folder: Path, ies_source: Path | None = None) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    ies_dir = folder / "ies"
    ies_dir.mkdir(exist_ok=True)
    source = ies_source or next((path for path in (
        ROOT / "assets/ies/Downlight_LED.IES",
        Path("C:/ProgramData/Autodesk/RVT 2027/IES/Downlight_LED.IES"),
        Path.home() / "archpipe/assets/ies/Downlight_LED.IES") if path.is_file()),
        Path("C:/ProgramData/Autodesk/RVT 2027/IES/Downlight_LED.IES"))
    if not source.is_file():
        raise FileNotFoundError(source)
    copy_file(source, ies_dir / "Downlight_LED.IES")
    photometry = load_ies(ies_dir / "Downlight_LED.IES")
    flux = photometry.integrated_flux()
    z = 2.55
    analytic_lux = photometry.intensity(0) / (z*z)
    materials = {
        "wall": {"kind": "principled", "base_rgb": [0.65, 0.65, 0.65], "reflectance": 0.65, "roughness": 0.85},
        "floor": {"kind": "principled", "base_rgb": [0.3, 0.3, 0.3], "reflectance": 0.3, "roughness": 0.8},
        "ceiling": {"kind": "principled", "base_rgb": [0.8, 0.8, 0.8], "reflectance": 0.8, "roughness": 0.9},
        "glass": {"kind": "glass", "base_rgb": [0.9, 0.95, 1], "transmittance": 0.7, "roughness": 0.02},
        "furniture": {"kind": "principled", "base_rgb": [0.4, 0.25, 0.16], "reflectance": 0.28, "roughness": 0.65},
        "lens": {"kind": "emissive", "base_rgb": [1, 1, 1], "emission_lm_per_m2": 1000, "cct_k": 3000},
    }
    meshes = [box("floor", (0,0,-.1,4,5,0), "floor"),
              box("ceiling", (0,0,2.7,4,5,2.8), "ceiling"),
              box("wall-west", (-.1,0,0,0,5,2.7), "wall"),
              box("wall-south", (0,-.1,0,4,0,2.7), "wall"),
              box("wall-north", (0,5,0,4,5.1,2.7), "wall"),
              box("wall-east-left", (4,0,0,4.1,1.25,2.7), "wall"),
              box("wall-east-right", (4,3.75,0,4.1,5,2.7), "wall"),
              box("wall-east-sill", (4,1.25,0,4.1,3.75,.8), "wall"),
              box("wall-east-head", (4,1.25,2.2,4.1,3.75,2.7), "wall"),
              box("window-glass", (4.04,1.25,.8,4.045,3.75,2.2), "glass", "fixture", label="Window"),
              box("table", (1.3,1.8,0.7,2.8,3.3,0.78), "furniture", "furniture", label="table"),
              box("downlight-lens", (1.97,2.47,2.55,2.03,2.53,2.56), "lens", "fixture")]
    base_view = {"when": "2026-10-15T15:30:00+03:00", "resolution": [640,400],
                 "layers_on": ["ambient", "task"], "dimmers": {}, "subjects": ["table"], "samples": 64}
    def view(ident, state, position, target, layers, exposure):
        return {**base_view, "id": ident, "title": ident, "state": state,
                "sun": {"altitude_deg": 32.1, "azimuth_true_deg": 231},
                "camera": {"position": position, "target": target, "lens_mm": 24,
                           "sensor_mm": 36, "shift_x": 0, "shift_y": 0},
                "layers_on": layers, "exposure": exposure}
    scene = {"schema": "villa-render/1", "id": "synthetic-selftest",
             "north": {"model_y_bearing_deg": 20},
             "library_root": "$HOME/archpipe/assets/library", "materials": materials,
             "meshes": meshes,
             "lights": [{"id": "DL-1", "room": "test-room", "layer": "ambient", "type": "ies",
                         "position": [2,2.5,z], "aim": [0,0,-1], "spin_deg": 0,
                         "ies": "Downlight_LED.IES", "lumens": flux, "cct_k": 3000, "cri": 90,
                         "product": {"manufacturer": "Autodesk", "code": "Downlight_LED", "generic": True},
                         "dimmer": 1.0},
                        {"id": "STRIP-1", "room": "test-room", "layer": "task", "type": "area",
                         "position": [1,2.5,2.5], "aim": [0,0,-1], "size": [.03,1.2],
                         "length_dir": [0,1,0], "spread_deg": 120, "lumens": 400,
                         "cct_k": 3000, "cri": 90, "product": {"manufacturer": "generic", "code": "strip", "generic": True},
                         "dimmer": 1.0}],
             "views": [view("day", "day", [1,1,1.5], [2.5,2.8,1.2], ["ambient", "task"], "day"),
                       view("evening", "evening", [1,1,1.5], [2.5,2.8,1.2], ["ambient", "task"], "evening"),
                       view("evening-control", "evening", [1.05,1,1.5], [2.55,2.8,1.2], ["ambient", "task"], "evening")],
             "exposure": {"day": {"ev100": 14.5, "white_balance_k": 5500},
                          "evening": {"ev100": 5.5, "white_balance_k": 3200}},
             "sky": {"day": "nishita", "evening": {"hdri": "belfast_sunset_puresky.exr", "horizontal_lux": 400}},
             "notes": ["Synthetic geometry and generic Autodesk IES; this is a capability test, not a villa design."]}
    errors = validate_scene(scene)
    if errors:
        raise ValueError("\n".join(errors))
    save_bytes(folder / "scene.json", json.dumps(scene, indent=2).encode("utf-8"))
    save_bytes(folder / "analytic.json", json.dumps({"ies": str(source), "integrated_lumens": flux,
        "nadir_candela": photometry.intensity(0), "floor_distance_m": z,
        "direct_floor_lux": analytic_lux, "probe_status": "pending Blender measurement",
        "exposure_lock_status": "pending two evening renders"}, indent=2).encode("utf-8"))
    return scene


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "out/villa/render-selftest")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--host", default="ai-workstation")
    ap.add_argument("--ies-source", type=Path)
    a = ap.parse_args()
    scene = make_scene(a.out, a.ies_source)
    print(json.dumps({"scene": str(a.out / "scene.json"), "views": [v["id"] for v in scene["views"]]}))
    if a.run:
        from PIL import Image
        from villa_render import run
        result = run(a.out / "scene.json", "all", 64, "640x400", a.host, a.out / "ies", calibrate=True)
        cal = result["calibration"]
        if cal["relative_error"] > 0.10:
            raise AssertionError("IES lux mismatch exceeds 10%: " + str(cal))
        if not cal["emissive_sphere"]["within_10_percent"]:
            raise AssertionError("Emissive sphere lux mismatch exceeds 10%: " + str(cal["emissive_sphere"]))
        def table_luminance(ident):
            report = json.loads((a.out / (ident + ".json")).read_text(encoding="utf-8"))
            screen = next(s["screen"] for s in report["subjects"] if s["id"] == "table")
            with Image.open(a.out / (ident + ".png")) as img:
                w, h = img.size
                # Interior half of the table's projected bounding rectangle.
                x0, y0, x1, y1 = screen
                rect = (int(w*(0.75*x0+0.25*x1)), int(h*(1-(0.25*y0+0.75*y1))),
                        int(w*(0.25*x0+0.75*x1)), int(h*(1-(0.75*y0+0.25*y1))))
                pixels = list(img.convert("RGB").crop(rect).getdata())
                return sum((0.2126*r+0.7152*g+0.0722*b)/255 for r,g,b in pixels)/len(pixels)
        first = table_luminance("evening")
        second = table_luminance("evening-control")
        fraction = abs(first-second)/max(first, second, 1e-9)
        proof = {"direct_floor_lux_analytic": cal["analytic_direct_lux"],
                 "direct_floor_lux_blender": cal["blender_direct_lux"],
                 "direct_lux_relative_error": cal["relative_error"],
                 "emissive_sphere": cal["emissive_sphere"],
                 "white_card_display_luminance": cal["white_card_display_luminance"],
                 "white_card_middle_grey_passed": abs(cal["white_card_display_luminance"]-0.5) <= 0.1,
                 "ev100": [json.loads((a.out / (v+".json")).read_text(encoding="utf-8"))["ev100"]
                             for v in ("evening", "evening-control")],
                 "table_display_luminance": [first, second], "table_difference_fraction": fraction,
                 "exposure_lock_passed": fraction <= 0.05}
        save_bytes(a.out / "selftest-report.json", json.dumps(proof, indent=2).encode("utf-8"))
        print(json.dumps({**result, "proof": proof}, indent=2))
        if not proof["exposure_lock_passed"]:
            raise AssertionError("Locked exposure same-surface brightness differs by more than 5%")
        if not proof["white_card_middle_grey_passed"]:
            raise AssertionError("White card did not render at expected middle grey")


if __name__ == "__main__":
    main()
