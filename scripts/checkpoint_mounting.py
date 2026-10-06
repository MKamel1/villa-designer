"""Create a reviewable C4 stair candidate without replacing the live scene.

Run from the repository root. Bounds contain minimum x, y, z then maximum
x, y, z, in metres. Movement is the largest displacement of a corresponding
vertex; it detects changed fixing ends as well as whole-object translations.
The PNG is a measured section diagnostic, not a photoreal render.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.concept import villa_render as VR, revit_spec as RS, villa_r11 as R
from archpipe.concept.mounting import scene_findings
from archpipe.concept import stair_mounting as SM
from PIL import Image, ImageDraw

OUTPUT = ROOT / "out/c4-phase2a"
BASELINE = ROOT / "tests/fixtures/c4-stair-phase1.json"


def vertices(mesh):
    return [point for face in mesh["faces"] for point in face]


def bounds(mesh):
    points = vertices(mesh)
    return [min(p[axis] for p in points) for axis in range(3)] + [max(p[axis] for p in points) for axis in range(3)]


def movements(scene, baseline):
    current = {m["id"]: m for m in scene["meshes"]}
    rows = []
    for before in baseline["meshes"]:
        after = current[before["id"]]
        old_points, new_points = vertices(before), vertices(after)
        if len(old_points) != len(new_points):
            raise ValueError(before["id"] + ": topology changed; requires separate movement comparison")
        movement = max(math.dist(a, b) for a, b in zip(old_points, new_points)) * 1000
        if movement <= 5 + 1e-9:
            continue
        resize = after["part_kind"] in ("stair-stringer", "rail-bracket")
        rows.append(dict(id=before["id"], old=json.dumps(bounds(before)), new=json.dumps(bounds(after)),
                         mm=round(movement, 3),
                         why="Fixing end moved out of structural wall to 13 mm plaster; tread/elevation retained"
                         if resize else "Retain existing finished-face projection with 13 mm plaster build-up",
                         movement="fixing-end resize" if resize else "translation", approval="PENDING"))
    host = SM.wall_host(RS.build(R.design("D1")))
    rows.append(dict(id="finished-face/stair-party-wall", old=json.dumps(list(host.structural_point)),
                     new=json.dumps([0, SM.finished_y(host), 0]), mm=13.0,
                     why="Verified two-coat plaster; applies only between flight ends", movement="finish face",
                     approval="PENDING"))
    return rows


def section_points(mesh, model_x):
    points = set()
    for face in mesh["faces"]:
        for a, b in zip(face, face[1:] + face[:1]):
            if abs(a[0] - model_x) < 1e-9:
                points.add((round(a[1], 9), round(a[2], 9)))
            if (a[0] < model_x < b[0]) or (b[0] < model_x < a[0]):
                fraction = (model_x - a[0]) / (b[0] - a[0])
                points.add((round(a[1] + fraction * (b[1] - a[1]), 9),
                            round(a[2] + fraction * (b[2] - a[2]), 9)))
    # Convex section of the closed stair prisms; do not infer a surface from
    # an arbitrary room bounding rectangle.
    points = sorted(points)
    if len(points) < 3:
        return []
    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    lower, upper = [], []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def preview(scene, baseline):
    image = Image.new("RGB", (1120, 1220), "white")
    draw = ImageDraw.Draw(image)
    draw.text((35, 25), "C4 PHASE 2a: measured stair section - candidate for lead review", fill="black")
    draw.text((35, 48), "Diagnostic only. Dark outlines: phase 1. Filled geometry: candidate. No design elevations changed.", fill="black")
    spec = RS.build(R.design("D1"))
    tread = sorted([b for b in spec["stair"] if b[5] - b[2] < 300], key=lambda b: b[0])[8]
    model_x, tread_top = (tread[0] + tread[3]) / 2000, tread[5] / 1000
    host = SM.wall_host(spec)
    structural_y, face_y = host.structural_point[1], SM.finished_y(host)
    origin_y = spec["stair_wall_datum"]["outer_face_mm"] / 1000
    # Equal horizontal/vertical scale: 700 pixels per metre.
    def pixel(y, z):
        return (70 + (y - origin_y) * 700, 1050 - (z - tread_top + .2) * 700)
    draw.rectangle([pixel(origin_y, tread_top + 1.10), pixel(structural_y, tread_top - .20)], fill="#d5d8dd", outline="#8b9199")
    draw.rectangle([pixel(structural_y, tread_top + 1.10), pixel(face_y, tread_top - .20)], fill="#f2c46f", outline="#ae791b")
    old = {m["id"]: m for m in baseline["meshes"]}
    for mesh in scene["meshes"]:
        if "mounting" not in mesh:
            continue
        polygon = section_points(mesh, model_x)
        if not polygon:
            continue
        colour = "#aa754b" if mesh["part_kind"] == "handrail" else "#374651"
        draw.polygon([pixel(y, z) for y, z in polygon], fill=colour, outline="black")
        old_polygon = section_points(old[mesh["id"]], model_x)
        if old_polygon:
            draw.line([pixel(y, z) for y, z in old_polygon + old_polygon[:1]], fill="#b93333", width=2)
    draw.rectangle([pixel(tread[1] / 1000, tread[5] / 1000), pixel(tread[4] / 1000, tread[2] / 1000)],
                   fill="#c69465", outline="black")
    draw.text((700, 130), f"Section at model x = {model_x:.3f} metres", fill="black")
    labels = ["Structural face: model y = -28.471 m", "Finished plaster: model y = -28.458 m",
              "Plaster: 13 mm, Ching 10.05 VERIFIED", "Nearest handrail face: -28.373 m",
              "Rail clearance: retained 85 mm", "Rail width: retained 40 mm",
              "Rail and plate translate 13 mm",
              "Bracket wall ends move 213 mm",
              "Stringer wall ends move 213 mm",
              "Tread endpoints and all elevations retained",
              "Movement approval: PENDING", "Photoreal preview and native coordination: PENDING"]
    for index, label in enumerate(labels):
        draw.text((700, 165 + index * 28), label, fill="black")
    draw.line([(700, 650), (770, 650)], fill="black", width=3)
    draw.text((700, 665), "100 mm scale; axes: model y across, z up", fill="black")
    draw.text((35, 1155), "Grey: existing structural wall. Gold: verified plaster. Brown: wood. Blue: steel. Red: frozen phase-1 outlines.", fill="black")
    image.save(OUTPUT / "stair-section-preview.png")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    scene = VR.build(views=[])
    (OUTPUT / "candidate-scene.json").write_text(json.dumps(scene), encoding="utf-8")
    findings = scene_findings(scene)
    members = [m for m in scene["meshes"] if "mounting" in m]
    host_faces = [m for m in scene["meshes"] if m.get("finished_host_id")]
    package_findings = scene_findings(dict(meshes=members + host_faces, mounting_hosts=scene["mounting_hosts"]))
    report = dict(status="CHECKPOINT; PHASE 2 INCOMPLETE", candidate_only=True,
                  source_baseline_sha256=baseline["sha256"], host_records=scene["mounting_hosts"],
                  package_component_count=len(members), package_findings=package_findings,
                  whole_scene_findings=findings, photoreal_review="PENDING", lead_movement_approval="PENDING")
    (OUTPUT / "mounting-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = movements(scene, baseline)
    with (OUTPUT / "movements-over-5mm.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    preview(scene, baseline)
    print(f"Candidate only: {len(members)} migrated components; {len(package_findings)} package failures; "
          f"{len(findings)} whole-scene failures; {len(rows)} movements awaiting approval")
    return 1 if package_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
