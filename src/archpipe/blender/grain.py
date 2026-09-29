"""Pure-Python (no `bpy`) model of the wood-grain rotation `villa_scene.add_material` feeds into a Box-projected
Image Texture, so it can be checked by the unit-test suite without a Blender runtime.

Defect (client: stair treads v11-stair-void.png, ensuite vanity v12-ensuite.png -- wood read as long smeared
streaks, "annoyingly fake"): `add_material` redirects a material's grain by rotating the OBJECT coordinates fed
into a Box-projected `ShaderNodeTexImage` (`GRAIN_ROTATION_DEG`, previously inline in `villa_scene.add_material`).
Blender's Box projection picks *which pair* of the coordinate's three components it samples for a face from that
face's own, UNROTATED geometric normal -- it does not re-derive the pairing from the rotated vector. Rotating the
coordinate therefore does not rotate which two axes are read; it can instead point one of the two sampled
components at the face's own normal axis, which never varies across that face, so the whole face samples a
single texel column/row: a hard stretch, matching the observed streaking.

Confirmed 2026-09-28 against a real Blender 4.2.9 import on ai-workstation (`mathutils.Euler(rot,
'XYZ').to_matrix()`, matching `mapping_rotated_span` below exactly): a stair tread (280 x 900 x 60 mm, `stairs.py`
tread boxes) used `"walnut"` (`grain_axis="z"`), whose rotation sends the tread's own 60 mm thickness into one of
the two coordinates the top face's Box projection reads -- `mapping_rotated_span` returns a near-zero span for
that axis. `grain_axis="x"` (identity rotation -- no coordinate rotation at all, so Box projection samples
exactly the geometry it was designed for, with no possible axis mismatch) does not collapse on any face
orientation; it is the already-established, already-shipped pattern for this exact failure
(`"walnut-grain-x"`/`"oak-grain-x"`, "grain along horizontal tops and shelves") applied here to the stair treads
and, for the same zero-risk reason, to the washbasin/vanity front (villa_render.py `part_material`)."""
from __future__ import annotations

import math

# Mirrors villa_scene.add_material's `mapping.inputs["Rotation"].default_value` table, in degrees (villa_scene
# converts to radians with math.radians the same way `mapping_rotated_span` does below).
GRAIN_ROTATION_DEG = {"x": (0, 0, 0), "y": (0, 0, 90), "z": (0, 90, 0)}


def _euler_xyz_matrix(rx, ry, rz):
    """The 3x3 rotation matrix Blender's Mapping node builds for an Euler('XYZ') rotation, reproduced without
    `mathutils`: verified 2026-09-28 to match `mathutils.Euler((rx, ry, rz), 'XYZ').to_matrix()` on ai-workstation
    (Blender 4.2.9) for every (axis, rotation) pair `add_material` uses."""
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rx_m = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry_m = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz_m = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]

    def matmul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return matmul(rz_m, matmul(ry_m, rx_m))


# Which two of the rotated vector's components a Box-projected Image Texture reads as (U, V) on the face whose
# own geometric normal is this axis -- the same per-normal-axis pairing `villa_scene.triplanar_normal` already
# uses for its (deliberately hand-built, not Box-projection-based) normal-map triplanar. 0=X, 1=Y, 2=Z.
FACE_UV_AXES = {0: (1, 2), 1: (2, 0), 2: (0, 1)}


def mapping_rotated_span(grain_axis, half_extents_mm):
    """The (U, V) spans (same units as `half_extents_mm`) a Box-projected Image Texture samples on the DOMINANT
    face (normal to the box's thinnest axis -- its largest-area face, the one actually seen) of a box with the
    given (x, y, z) half-extents, after `add_material`'s grain_axis rotation. A span near zero means that
    coordinate is constant across the whole face: the texture reads one texel column/row, stretched -- the
    defect. `half_extents_mm` need not be in millimetres; any consistent unit works."""
    dims = list(half_extents_mm)
    normal_axis = min(range(3), key=lambda i: dims[i])
    other = [i for i in range(3) if i != normal_axis]
    rx, ry, rz = (math.radians(v) for v in GRAIN_ROTATION_DEG[grain_axis])
    rot = _euler_xyz_matrix(rx, ry, rz)
    face = []
    for s0 in (-1, 1):
        for s1 in (-1, 1):
            p = [0.0, 0.0, 0.0]
            p[normal_axis] = dims[normal_axis]
            p[other[0]] = s0 * dims[other[0]]
            p[other[1]] = s1 * dims[other[1]]
            face.append(tuple(p))
    mapped = [tuple(sum(rot[i][j] * c[j] for j in range(3)) for i in range(3)) for c in face]
    u_axis, v_axis = FACE_UV_AXES[normal_axis]
    span_u = max(m[u_axis] for m in mapped) - min(m[u_axis] for m in mapped)
    span_v = max(m[v_axis] for m in mapped) - min(m[v_axis] for m in mapped)
    return span_u, span_v
