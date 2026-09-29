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


def subject_footprint(subject, items, rooms, scene):
    """Plan bounds of a declared view subject, from furniture or matching built meshes."""
    if subject in items:
        return F.footprint(items[subject])
    if subject in rooms:
        return None  # stair void is a space, not a bounded furniture piece
    pts = [p for m in scene["meshes"]
           if m["id"] == subject or m["id"].startswith(subject) or m.get("label") == subject
           for face in m["faces"] for p in face]
    if pts:
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)
    raise ValueError("unresolved view subject: " + subject)


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
                for qx, qy in ((q[0], q[1]), (q[2], q[1]), (q[0], q[3]), (q[2], q[3])):
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
        ax.set_xlim(min(xs) - 0.5, 29)
        ax.set_ylim(-31.5, -20.0)
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
