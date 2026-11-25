"""Scene triangles + an Embree ray caster for the walkthrough audit.

`scene.json` is ~1.4 GB, so it is read once by `extract()` into a compact npz cache
(triangles, element id per triangle, room per triangle, material class); later runs load only the cache.
Ray casting needs a BVH: `embreex` (Intel Embree wheel) is the only new dependency; numpy cannot do ~15 M
rays against 1.7 M triangles in reasonable time. Glass is a second scene so a ray can pass through it and report it.
"""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
import numpy as np

# material classes stored per triangle
OPAQUE, GLASS, IGNORE = 0, 1, 2
GROUPS = ['shell', 'dressing', 'fixture', 'ground', 'furniture', 'context']


def _material_class(mesh):
    mat = mesh.get('material') or ''
    if mat.startswith('marker'):
        return IGNORE
    if mat.startswith('glass'):
        return GLASS
    return OPAQUE


def extract(scene_path, cache_path):
    """Read scene.json once and write the npz cache. Peak RAM is the JSON object tree (~10x file size)."""
    scene = json.loads(Path(scene_path).read_text())
    tris, elem, room, cls, grp = [], [], [], [], []
    names, rooms = {}, {}
    def idx(table, key):
        return table.setdefault(key, len(table))
    for m in scene['meshes']:
        c = _material_class(m)
        if c == IGNORE:
            continue
        fe = {}
        for e, faces in (m.get('faces_by_element') or {}).items():
            for i in faces:
                fe[i] = e
        default = (m.get('element_ids') or [m['id']])[0] if not fe else m['id']
        ri = idx(rooms, m.get('room') or '')
        g = GROUPS.index(m['group']) if m.get('group') in GROUPS else 0
        for i, face in enumerate(m['faces']):
            e = idx(names, fe.get(i, default))
            for k in range(1, len(face) - 1):      # fan triangulation (faces are convex)
                tris.append((face[0], face[k], face[k + 1])); elem.append(e); room.append(ri); cls.append(c); grp.append(g)
    sha = hashlib.sha256(Path(scene_path).read_bytes()[:1 << 20]).hexdigest()[:12]
    # views carry the camera route; doors etc. are already baked into mesh faces (open_interior_doors)
    np.savez_compressed(cache_path,
        tris=np.asarray(tris, np.float32), elem=np.asarray(elem, np.int32), room=np.asarray(room, np.int32),
        cls=np.asarray(cls, np.int8), grp=np.asarray(grp, np.int8),
        elem_names=np.array(sorted(names, key=names.get)), room_names=np.array(sorted(rooms, key=rooms.get)),
        scene_head_sha=np.array(sha))
    return cache_path


class Geometry:
    """Opaque + glass Embree scenes over the same triangle table."""

    def __init__(self, tris, elem, room, cls, grp, elem_names, room_names):
        try:
            from embreex import rtcore_scene as rs
            from embreex.mesh_construction import TriangleMesh
        except ImportError:
            rs = None      # numpy brute force below: fine for test-sized scenes only
        self.tris, self.elem, self.room, self.cls, self.grp = tris, elem, room, cls, grp
        self.elem_names, self.room_names = list(elem_names), list(room_names)
        self._scenes = {}
        for kind in (OPAQUE, GLASS):
            sel = np.flatnonzero(cls == kind)
            self._scenes[kind] = None
            if len(sel) and rs is None:
                if len(sel) > 20000:
                    raise ImportError('embreex is required for scenes of this size (pip install embreex)')
                self._scenes[kind] = (None, sel)
            elif len(sel):
                sc = rs.EmbreeScene()
                TriangleMesh(sc, tris[sel].reshape(-1, 3).astype(np.float32),
                             np.arange(len(sel) * 3, dtype=np.int32).reshape(-1, 3))
                self._scenes[kind] = (sc, sel)

    @classmethod
    def load(cls, path):
        z = np.load(path)
        return cls(z['tris'], z['elem'], z['room'], z['cls'], z['grp'], z['elem_names'], z['room_names'])

    def cast(self, origins, dirs):
        """-> (dist, tri) of first opaque hit (inf, -1 if none), then (dist, tri) of first glass hit."""
        o = np.ascontiguousarray(origins, np.float32); d = np.ascontiguousarray(dirs, np.float32)
        n = len(o); out = {}
        for kind in (OPAQUE, GLASS):
            s = self._scenes[kind]
            if s is None:
                out[kind] = (np.full(n, np.inf, np.float32), np.full(n, -1))
                continue
            if s[0] is None:
                t, prim = _brute(self.tris[s[1]], o, d)
                hit = prim >= 0
                out[kind] = (t.astype(np.float32), np.where(hit, s[1][np.maximum(prim, 0)], -1))
                continue
            r = s[0].run(o, d, output=1)
            hit = r['primID'] >= 0
            out[kind] = (np.where(hit, r['tfar'], np.inf).astype(np.float32), np.where(hit, s[1][np.maximum(r['primID'], 0)], -1))
        return out[OPAQUE][0], out[OPAQUE][1], out[GLASS][0], out[GLASS][1]

    def tri_elem(self, tri):
        return np.where(tri >= 0, self.elem[np.maximum(tri, 0)], -1)


def _brute(tris, o, d, eps=1e-9):
    """Moller-Trumbore, every ray against every triangle. -> (t or inf, tri index or -1)."""
    o = o.astype(np.float64); d = d.astype(np.float64); T = tris.astype(np.float64)
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    best = np.full(len(o), np.inf); prim = np.full(len(o), -1)
    for k in range(len(T)):
        h = np.cross(d, e2[k]); a = h @ e1[k]
        ok = np.abs(a) > eps
        f = np.where(ok, 1. / np.where(ok, a, 1.), 0.)
        s = o - T[k, 0]; u = f * (s * h).sum(1)
        q = np.cross(s, e1[k]); v = f * (d * q).sum(1); t = f * (q @ e2[k])
        m = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6) & (t < best)
        best[m] = t[m]; prim[m] = k
    return best, prim
