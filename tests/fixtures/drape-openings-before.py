"""Frozen pre-optimisation opening review, replayed against real garments."""
import numpy as np
from archpipe.concept.render_support import ITEM_GROUPS, _islands

def blocked_openings(scene, lay=None, *, specification=None):
    """Every door must be passable: no furniture, dressing or render detail inside a door's passage (its clear width
    less 20 mm, 0.35 m either side of the wall line, from 50 mm to 2.0 m above the floor). Found after the client saw
    the parents' entrance closed by a slatted headboard panel that also covered the dressing door."""
    from . import revit_spec as RS
    from . import villa_furnish as F
    from . import villa_r11 as R
    from .villa_render import LZ
    lay = lay or R.design("D1")
    sp = RS.build(lay) if specification is None else specification
    out = []
    parts = []
    for m in scene["meshes"]:
        if m["group"] not in ITEM_GROUPS or "handle" in m["id"]:
            continue
        for faces in _islands(m["faces"]):
            pts = np.array([p for f in faces for p in f], dtype=float)
            parts.append((m["id"], pts.min(axis=0), pts.max(axis=0)))
    # doorless openings: where two rooms of a storey share an edge and no wall stands on it (the parents' entry)
    openings = []
    rooms = [(rid, r) for rid, r in lay["rooms"].items()]
    for i, (ra, a_) in enumerate(rooms):
        for rb, b_ in rooms[i + 1:]:
            if a_["level"] != b_["level"]:
                continue
            A, B = a_["rect"], b_["rect"]
            walls = F._walls(sp, a_["level"])
            for horiz, line, s0, s1 in (
                    (True, A[3], max(A[0], B[0]), min(A[2], B[2])) if abs(A[3] - B[1]) < 0.02 else (None,) * 4,
                    (True, A[1], max(A[0], B[0]), min(A[2], B[2])) if abs(A[1] - B[3]) < 0.02 else (None,) * 4,
                    (False, A[2], max(A[1], B[1]), min(A[3], B[3])) if abs(A[2] - B[0]) < 0.02 else (None,) * 4,
                    (False, A[0], max(A[1], B[1]), min(A[3], B[3])) if abs(A[0] - B[2]) < 0.02 else (None,) * 4):
                if horiz is None or s1 - s0 < 0.6:
                    continue
                run = []
                v = s0 + 0.025
                while v < s1:
                    x, y = (v, line) if horiz else (line, v)
                    free = not any(w[0] - 0.01 <= x <= w[2] + 0.01 and w[1] - 0.06 <= y <= w[3] + 0.06 for w in walls)                         if horiz else not any(w[0] - 0.06 <= x <= w[2] + 0.06 and w[1] - 0.01 <= y <= w[3] + 0.01
                                              for w in walls)
                    if free:
                        run.append(v)
                    elif run:
                        openings.append((a_["level"], horiz, line, run[0], run[-1], ra + "/" + rb))
                        run = []
                    v += 0.05
                if run:
                    openings.append((a_["level"], horiz, line, run[0], run[-1], ra + "/" + rb))
    for lv, horiz, line, v0, v1, name in openings:
        # a PASSAGE is 0.6-1.6 m wide; wider shared edges are zones of one open-plan space, not openings
        if not 0.6 <= v1 - v0 + 0.05 <= 1.6:
            continue
        z0 = LZ[lv]
        lo = np.array([v0, line - 0.35, z0 + 0.05]) if horiz else np.array([line - 0.35, v0, z0 + 0.05])
        hi = np.array([v1, line + 0.35, z0 + 2.0]) if horiz else np.array([line + 0.35, v1, z0 + 2.0])
        for mid, a, b in parts:
            # the furnished-plan route check (villa_furnish, 914 mm body) already clears furniture in passages; it
            # cannot see render-only details or hanging fixtures, which is how the slat panel closed the entry
            if not (mid.startswith("detail-") or mid.split("-")[0] in ("lamp", "cord", "canopy", "fix", "bracket")):
                continue
            if mid.startswith("detail-stair-") and "stair-" in name:
                continue  # the stringers and handrails define the stair edge and its access, not a room passage
            if np.all(np.minimum(b, hi) - np.maximum(a, lo) > 0.005):
                out.append((mid, "opening %s" % name))
    for d in sp["doors"]:
        h = F._door_axis(d) == "h"
        hw = d["width"] / 2 - 0.02
        z0 = LZ[d["level"]]
        lo = np.array([d["x"] - hw, d["y"] - 0.35, z0 + 0.05]) if h else np.array([d["x"] - 0.35, d["y"] - hw, z0 + 0.05])
        hi = np.array([d["x"] + hw, d["y"] + 0.35, z0 + 2.0]) if h else np.array([d["x"] + 0.35, d["y"] + hw, z0 + 2.0])
        for mid, a, b in parts:
            if np.all(np.minimum(b, hi) - np.maximum(a, lo) > 0.005):
                out.append((mid, "door %s at (%.2f, %.2f)" % ("/".join(d.get("rooms") or []), d["x"], d["y"])))
    return sorted(set(out))
