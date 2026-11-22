"""Adapter: Scene -> (meshes, props) in the shape the production villa scene already carries (`scene["meshes"]`, `scene["props"]`).

Not wired into villa_render (lane L6d owns it); this is the seam the integration lane calls. Meshes are one per (object, material) so each
carries one finish; `element_ids` is declared (P2 'declared' basis), and the id embeds the ld-* id (P2 'generator-name' basis too).
"""
from __future__ import annotations

from . import guard


def _faces(part):
    v = part.verts
    return [[[float(x) for x in v[i]] for i in f] for f in part.faces]


def to_villa_scene(scene, state="closed"):
    guard.refuse(scene, "the production villa scene")
    meshes, props = [], []
    for o in scene.select(state):
        by = {}
        for p in o.parts:
            by.setdefault(p.material.split("#")[0], []).extend(_faces(p))
        for mat, faces in by.items():
            mid = o.id if len(by) == 1 else "%s.%s" % (o.id, mat)
            meshes.append(dict(id=mid, group="ground" if o.kind in ("paving", "path", "gravel", "ground", "bed") else "dressing", material=mat, faces=faces,
                               label=o.label, part_kind=o.kind, surface=o.kind in ("paving", "path", "gravel", "ground", "bed"), occupied_side=None,
                               element_ids=[o.id], ld_state=o.state, ld_standin=o.standin))
        if o.asset:
            a = o.asset
            props.append(dict(id=o.id, asset=a["asset_id"], gltf=a["gltf"], scale_to_height_m=a["bounds"][5] - a["bounds"][2], base_at=a["at"], rotation_deg=[0, 0, a.get("yaw_deg", 0.0)], placement=dict(mode=a.get("mode", "height"), scale_xyz=a.get("scale_xyz"), box_m=a.get("box_m"), length_m=a.get("length_m"), tiles=a.get("tiles")),
                              zone="lower", label=o.label, element_ids=[o.id], grade=a["grade"], licence=a["licence"], author=a["author"], source=a["source"]))
    return meshes, props
