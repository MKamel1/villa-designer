"""Check the render views on plan BEFORE rendering (photoreal-render skill: choose framings with the projection
model, not by trial renders). Draws each camera's horizontal field of view over the furnished plan of its storey,
with its subjects, and reports subjects outside the field of view.

    PYTHONPATH=src python scripts/villa_render_views.py      # -> out/villa/render-d1/views-plan.png
"""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib.patches import Polygon, Rectangle                   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.concept import villa_furnish as F                      # noqa: E402
from archpipe.concept import villa_r11 as R                          # noqa: E402
from archpipe.concept import revit_spec as RS                        # noqa: E402
from archpipe.concept import villa_landscape as LAND                  # noqa: E402

OUT = ROOT / "out" / "villa" / "render-d1"


def hfov(v):
    w, h = v["resolution"]
    return 2 * math.degrees(math.atan(v["camera"]["sensor_mm"] / 2 / v["camera"]["lens_mm"]))  # sensor = width


def door_leaf_near(scene, px, py):
    """Whether the rendered scene actually has a door leaf at this camera (villa-render doorway guard)."""
    return any(m.get("material") == "door-oak" and
               any(abs(sum(p[0] for p in face) / len(face) - px) < 0.9 and
                   abs(sum(p[1] for p in face) / len(face) - py) < 0.9
                   for face in m["faces"])
               for m in scene["meshes"])


def subject_points(subject, scene):
    """Built mesh vertices plus actual transformed imported-prop vertices.

    Imported assets are subjects in their own right; no invisible mesh
    marker may stand in for a removed assembly or a rendered prop.
    """
    from archpipe.concept.route_geometry import prop_triangles
    points = [p for m in scene["meshes"]
              if m["id"] == subject or m["id"].startswith(subject) or m.get("label") == subject
              for face in m["faces"] for p in face]
    for prop in scene.get("props", []):
        if prop["id"] == subject or prop["id"].startswith(subject) or prop.get("label") == subject:
            points += prop_triangles(prop).reshape(-1,3).tolist()
    return points


def subject_footprint(subject, items, rooms, scene):
    """Plan bounds of a declared view subject, from furniture or matching built meshes."""
    if subject in items:
        return F.footprint(items[subject])
    if subject in rooms:
        return None  # stair void is a space, not a bounded furniture piece
    pts = subject_points(subject, scene)
    if pts:
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
    raise ValueError("unresolved view subject: " + subject)


def subject_mesh_frame_violations(view, scene, subject):
    """Project every built vertex through a level camera, including sensor-width lens shift.

    Horizontal coordinates span -0.5 to 0.5 sensor widths; vertical coordinates
    span half the image height/width ratio either side of the shifted centre.
    Returns failed frame edges; unresolved subjects fail closed.
    """
    points = subject_points(subject, scene)
    if not points:
        return ["unresolved built subject"]
    camera = view["camera"]
    px, py, pz = camera["position"]
    tx, ty, _ = camera["target"]
    yaw = math.atan2(ty-py, tx-px)
    vertical_half = view["resolution"][1] / view["resolution"][0] / 2
    failed = set()
    for x, y, z in points:
        forward = (x-px)*math.cos(yaw)+(y-py)*math.sin(yaw)
        if forward <= 0:
            failed.add("behind camera")
            continue
        right = (x-px)*math.sin(yaw)-(y-py)*math.cos(yaw)
        horizontal = camera["lens_mm"] / camera["sensor_mm"] * right/forward - camera.get("shift_x", 0)
        vertical = camera["lens_mm"] / camera["sensor_mm"] * (z-pz)/forward - camera.get("shift_y", 0)
        if abs(horizontal) > .5:
            failed.add("horizontal edge")
        if vertical < -vertical_half:
            failed.add("bottom edge")
        if vertical > vertical_half:
            failed.add("top edge")
    return sorted(failed)


def camera_proximity_violations(view, scene, items, clearance=1.0):
    """Return props and furniture closer than the required camera clearance in metres."""
    px, py, pz = view["camera"]["position"]
    level = "B" if pz < -0.1 else "GF"
    failures = []
    for prop in scene["props"]:
        if prop["asset"] not in LAND.PROP_BOUNDS:
            continue
        x0, y0, z0, x1, y1, z1 = LAND.prop_world_box(
            prop["asset"], prop["position"], prop.get("rotation_deg", [0, 0, 0]), prop["scale"])
        distance = math.sqrt(sum(d*d for d in (
            max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1), max(z0 - pz, 0, pz - z1))))
        if distance < clearance:
            failures.append((prop["id"], round(distance, 3)))
    for item in items.values():
        if item["level"] != level:
            continue
        x0, y0, x1, y1 = F.footprint(item)
        distance = math.hypot(max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1))
        if distance < clearance:
            failures.append((item["id"], round(distance, 3)))
    return failures


def dominant_foreground_props(view, scene, minimum_angle_deg=25.0):
    """Flag a tall specimen pot that occupies a large part of the horizontal view."""
    px, py = view["camera"]["position"][:2]
    tx, ty = view["camera"]["target"][:2]
    yaw = math.atan2(ty-py, tx-px)
    half = math.radians(hfov(view) / 2)
    failures = []
    for prop in scene["props"]:
        # Low border planting is an intended subject of the north-garden view.
        if prop["asset"] not in ("sf_lemon_tree", "sf_olive_old"):
            continue
        x0, y0, _, x1, y1, _ = LAND.prop_world_box(
            prop["asset"], prop["position"], prop.get("rotation_deg", [0, 0, 0]), prop["scale"])
        cx, cy = (x0+x1)/2, (y0+y1)/2
        center_angle = (math.atan2(cy-py, cx-px)-yaw+math.pi) % (2*math.pi)-math.pi
        if abs(center_angle) > half or math.hypot(cx-px, cy-py) > 5:
            continue
        angles = [(math.atan2(y-py, x-px)-yaw+math.pi) % (2*math.pi)-math.pi
                  for x in (x0, x1) for y in (y0, y1)]
        span = math.degrees(max(angles)-min(angles))
        if span >= minimum_angle_deg:
            failures.append((prop["id"], round(span, 1)))
    return failures


def under_stair_occlusion_violation(view):
    """A v29 camera east of the first tread looks through the flight at the joinery."""
    x, y = view["camera"]["position"][:2]
    return y <= -27.471


def storage_front_occlusions(view, items, parts_by_id=None):
    """Return each open bay whose interior-centre sightline crosses a storage front."""
    from archpipe.concept import villa_furnish3d as F3
    camera = view["camera"]["position"]
    blocked = []
    for item in items.values():
        if item["type"] != "under_stair_storage" or item["id"] not in view["subjects"]:
            continue
        parts = (parts_by_id or {}).get(item["id"], F3.body(item))
        for kind, _ in item["modules"]:
            backs = [F3.to_world(item, box) for name, box in parts if name == kind + "-back"]
            if not backs:
                blocked.append((item["id"], kind, "missing bay"))
                continue
            x0, x1 = min(box[0] for box in backs), max(box[3] for box in backs)
            y0, y1 = min(box[1] for box in backs), max(box[4] for box in backs)
            target = ((x0 + x1) / 2, y1 + (item["d"] - (y1 - y0)) * 0.55,
                      -3.0 + min(0.45, min(box[5] for box in backs) - 0.15))
            for name, box in parts:
                if not name.startswith("sliding-door"):
                    continue
                bounds = F3.to_world(item, box)
                # A face-on panel still crowds the opening even if one centre ray
                # threads past it. The old depiction left 28% of every tread bay closed.
                if (bounds[3] - bounds[0] > 0.05 and bounds[1] > y1 + 0.15 and
                        min(bounds[3], x1) - max(bounds[0], x0) > 0.05):
                    blocked.append((item["id"], kind, name + " spans opening"))
                    break
                bounds = (bounds[0], bounds[1], bounds[2] - 3.0,
                          bounds[3], bounds[4], bounds[5] - 3.0)
                near, far = 0.0, 1.0
                for axis in range(3):
                    delta = target[axis] - camera[axis]
                    if abs(delta) < 1e-10:
                        if not bounds[axis] <= camera[axis] <= bounds[axis + 3]:
                            near, far = 1.0, 0.0
                            break
                        continue
                    lo = (bounds[axis] - camera[axis]) / delta
                    hi = (bounds[axis + 3] - camera[axis]) / delta
                    near, far = max(near, min(lo, hi)), min(far, max(lo, hi))
                if near < far and 0.001 < near < 0.999:
                    blocked.append((item["id"], kind, name))
                    break
    return blocked


def main():
    scene = json.loads((OUT / "scene.json").read_text(encoding="utf-8"))
    lay = R.design("D1")
    items = {i["id"]: i for i in F.layout(lay)}
    views = scene["views"]
    n = len(views)
    cols = 4
    rows = (n + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 6, rows * 3.6))
    problems = []
    for ax, v in zip(axs.flat, views):
        cam = v["camera"]
        lv = "B" if cam["position"][2] < -0.1 else "GF"
        for rid, r in lay["rooms"].items():
            if r["level"] == lv:
                x0, y0, x1, y1 = r["rect"]
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#f3efe6", ec="0.6", lw=0.4))
        for it in items.values():
            if it["level"] == lv:
                q = F.footprint(it)
                ax.add_patch(Rectangle((q[0], q[1]), q[2] - q[0], q[3] - q[1], fc="#cfc6b6", ec="0.3", lw=0.3))
        px, py = cam["position"][:2]
        # The one-metre exterior clearance is calibrated on the v26/v28 canopy/pot
        # failures. Compact interior view selection has its own 0.15 m clearance rule.
        if v["id"].startswith(("v25-", "v26-", "v27-", "v28-", "v36-")):
            for near_id, distance in camera_proximity_violations(v, scene, items):
                problems.append("%s: camera %.2f m from %s (need >= 1.0 m)" % (v["id"], distance, near_id))
        if v["id"].startswith("v28-"):
            for prop_id, span in dominant_foreground_props(v, scene):
                problems.append("%s: foreground %s fills %.1f degrees of frame" % (v["id"], prop_id, span))
        if v["id"].startswith("v29-") and under_stair_occlusion_violation(v):
            problems.append(v["id"] + ": stair flight hides the storage joinery from this camera")
        if v["id"].startswith("v29-"):
            for item_id, bay, front in storage_front_occlusions(v, items):
                problems.append("%s: %s %s interior centre blocked by %s" % (v["id"], item_id, bay, front))
        tx, ty = cam["target"][:2]
        pz = cam["position"][2] - (-3.0 if lv == "B" else 0.0)
        # the camera must stand in the open: not inside a piece (two draft views were inside wardrobes and rendered
        # black), not within 0.2 m of a wall or column
        for it in items.values():
            q = F.footprint(it)
            if it["level"] == lv and q[0] - 0.05 < px < q[2] + 0.05 and q[1] - 0.05 < py < q[3] + 0.05 and                     pz < it["h"] + 0.3:
                problems.append("%s: camera inside or on %s" % (v["id"], it["id"]))
        from archpipe.concept import villa_render as VR
        sp_ = RS.build(lay)
        doorway = cam.get("reframed") == "doorway" and VR.in_door_opening(sp_, lv, px, py, cam.get("home_room"))
        if doorway and not v.get("hide_meshes"):
            # The telescopic kitchen leaves are rendered inside their side pocket.
            # Only require a hidden leaf when one actually spans this opening.
            leaf_here = door_leaf_near(scene, px, py)
            if leaf_here:
                problems.append("%s: camera in a doorway but its door is not opened for the view" % v["id"])
        for q in ([] if doorway else F._walls(sp_, lv) + F._columns()):
            if q[0] - 0.2 < px < q[2] + 0.2 and q[1] - 0.2 < py < q[3] + 0.2:
                problems.append("%s: camera within 0.2 m of a wall or column %s" % (v["id"], [round(t, 2) for t in q]))
        yaw = math.atan2(ty - py, tx - px)
        half = math.radians(hfov(v) / 2)
        R_ = 9
        wedge = [(px, py), (px + R_ * math.cos(yaw - half), py + R_ * math.sin(yaw - half)),
                 (px + R_ * math.cos(yaw + half), py + R_ * math.sin(yaw + half))]
        ax.add_patch(Polygon(wedge, fc="#ffcc00", alpha=0.25, ec="#cc9900"))
        ax.plot([px], [py], "ro", ms=4)
        for s in v["subjects"]:
            if s in items and items[s]["type"] == "wc" or v["id"].startswith(("v07-", "v19-", "v25-", "v26-", "v27-", "v28-", "v36-")):
                for edge in subject_mesh_frame_violations(v, scene, s):
                    problems.append("%s: built %s crosses %s" % (v["id"], s, edge))
            try:
                q = subject_footprint(s, items, lay["rooms"], scene)
            except ValueError as e:
                problems.append("%s: %s" % (v["id"], e))
                continue
            if q is not None:
                cx, cy = (q[0] + q[2]) / 2, (q[1] + q[3]) / 2
                # the WHOLE subject must be in frame, every footprint corner: checking only its centre passed views
                # that showed a corner of the ensuite and half a bed once the lens went to 24 mm (client: "limited
                # coverage")
                worst = 0.0
                # Imported/constructed garden subjects use their actual vertices;
                # empty corners of an asymmetric canopy box are not geometry.
                actual = subject_points(s, scene) if s not in items else []
                projected = [(p[0],p[1]) for p in actual] if actual else (
                    (q[0], q[1]), (q[2], q[1]), (q[0], q[3]), (q[2], q[3]))
                for qx, qy in projected:
                    ang = math.atan2(qy - py, qx - px) - yaw
                    ang = (ang + math.pi) % (2 * math.pi) - math.pi
                    worst = max(worst, abs(ang))
                ok = worst <= half
                ax.plot([cx], [cy], "g^" if ok else "kx", ms=6)
                if not ok:
                    problems.append("%s: %s not wholly in frame (a corner %.0f deg off axis, half-FOV %.0f)"
                                    % (v["id"], s, math.degrees(worst), math.degrees(half)))
        ax.set_title("%s  %s  %.0f mm (HFOV %.0f)" % (v["id"], lv, cam["lens_mm"], hfov(v)), fontsize=7)
        ax.set_aspect("equal")
        xs = [r["rect"][0] for r in lay["rooms"].values()] + [r["rect"][2] for r in lay["rooms"].values()]
        ax.set_xlim(min(min(xs) - 0.5, px - 0.5), max(29, px + 0.5))
        ax.set_ylim(min(-31.5, py - 0.5), max(-20.0, py + 0.5))
        ax.tick_params(labelsize=5)
    for ax in list(axs.flat)[n:]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "views-plan.png", dpi=110)
    print(OUT / "views-plan.png")
    for p in problems:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
