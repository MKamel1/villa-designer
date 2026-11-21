"""LV: the workstation-built scene as plain triangles, for sensor-validity tests.

Sources (all read from the scene.json the render uses, nothing from the lighting engine):
  - `meshes`: every mesh whose `visibility.camera` is not False (stand-ins replaced by an imported model are hidden in
    the render and are therefore not geometry);
  - `props` and `models`: the glTF asset's per-primitive bounding boxes, placed the way `blender/villa_scene.import_props`
    places them (Y-up -> Z-up, XYZ-euler degrees, scale, plan position, then seated so the lowest corner is at position z).
    Assets are decoded to their real triangles; an asset that cannot be decoded falls back to per-primitive boxes (tagged `bbox`).

`vertical_hits` fires a ray straight up from a sensor and reports every distinct surface above it.
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from pathlib import Path

import numpy as np

CELL = 0.5
ON_SURFACE = 0.005          # a surface within 5 mm above a sensor is the surface the sensor sits on, not an occluder


def _rot_euler_xyz_deg(rx, ry, rz):
    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _node_matrix(n):
    if "matrix" in n:
        return np.array(n["matrix"], dtype=float).reshape(4, 4).T
    t = np.array(n.get("translation", [0, 0, 0]), dtype=float)
    q = n.get("rotation", [0, 0, 0, 1])
    s = np.array(n.get("scale", [1, 1, 1]), dtype=float)
    x, y, z, w = q
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4)
    M[:3, :3] = R * s
    M[:3, 3] = t
    return M


def gltf_boxes(path: Path):
    """[(R3x3, t3, lo3, hi3)]: per-primitive local boxes in Blender Z-up asset space (box = lo..hi in the frame R, t)."""
    g = json.loads(Path(path).read_text(encoding="utf-8"))
    yup = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=float)         # (x, y, z)_gltf -> (x, -z, y)_blender
    out = []

    def walk(i, parent):
        n = g["nodes"][i]
        M = parent @ _node_matrix(n)
        if "mesh" in n:
            for prim in g["meshes"][n["mesh"]]["primitives"]:
                acc = g["accessors"][prim["attributes"]["POSITION"]]
                out.append((yup @ M[:3, :3], yup @ M[:3, 3], np.array(acc["min"], float), np.array(acc["max"], float)))
        for c in n.get("children", []):
            walk(c, M)

    sc = g["scenes"][g.get("scene", 0)]
    for r in sc["nodes"]:
        walk(r, np.eye(4))
    return out


_CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _accessor(g, bins, i):
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    raw = bins[bv["buffer"]]
    dt, n = np.dtype(_CT[a["componentType"]]), _NC[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride") or dt.itemsize * n
    if stride == dt.itemsize * n:
        return np.frombuffer(raw, dtype=dt, count=a["count"] * n, offset=off).reshape(a["count"], n)
    return np.stack([np.frombuffer(raw, dtype=dt, count=n, offset=off + k * stride) for k in range(a["count"])])


def gltf_triangles(path: Path):
    """World-less triangles (n,3,3) of a glTF in Blender Z-up asset space (node transforms applied). Raises on
    anything but triangle lists, so an unsupported asset falls back to its boxes instead of silently vanishing."""
    path = Path(path)
    g = json.loads(path.read_text(encoding="utf-8"))
    bins = [(path.parent / b["uri"]).read_bytes() for b in g["buffers"]]
    yup = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=float)
    out = []

    def walk(i, parent):
        n = g["nodes"][i]
        M = parent @ _node_matrix(n)
        if "mesh" in n:
            for prim in g["meshes"][n["mesh"]]["primitives"]:
                if prim.get("mode", 4) != 4:
                    raise ValueError("non-triangle primitive")
                P = _accessor(g, bins, prim["attributes"]["POSITION"]).astype(float)
                P = (P @ M[:3, :3].T + M[:3, 3]) @ yup.T
                if "indices" in prim:
                    idx = _accessor(g, bins, prim["indices"]).reshape(-1).astype(np.int64)
                else:
                    idx = np.arange(len(P))
                out.append(P[idx[: len(idx) // 3 * 3]].reshape(-1, 3, 3))
        for c in n.get("children", []):
            walk(c, M)

    for r in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4))
    return np.concatenate(out)


def place_triangles(tris, position, rotation_deg, scale):
    """World triangles of an asset placed like import_props: scale, XYZ-euler, plan position, lowest vertex at position z."""
    s = np.array([scale] * 3 if isinstance(scale, (int, float)) else scale, dtype=float)
    Rz = _rot_euler_xyz_deg(*rotation_deg)
    P = (tris.reshape(-1, 3) * s) @ Rz.T
    P = P + np.array([position[0], position[1], position[2] - P[:, 2].min()])
    return P.reshape(-1, 3, 3)


def _box_tris(R, t, lo, hi):
    """12 triangles of the box lo..hi in frame (R, t); corners returned in world (asset) space."""
    cs = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    return (cs @ R.T + t)


_QUADS = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]


def _tris_from_corners(c):
    out = []
    for a, b, d, e in _QUADS:
        out += [(c[a], c[b], c[d]), (c[a], c[d], c[e])]
    return np.array(out)


def place_asset(boxes, position, rotation_deg, scale):
    """World triangles (n,3,3) of one placed asset, seated like import_props."""
    s = np.array([scale] * 3 if isinstance(scale, (int, float)) else scale, dtype=float)
    Rz = _rot_euler_xyz_deg(*rotation_deg)
    allc = []
    for R, t, lo, hi in boxes:
        c = _box_tris(R, t, lo, hi) * s
        allc.append(c @ Rz.T)
    bottom = min(c[:, 2].min() for c in allc)
    off = np.array([position[0], position[1], position[2] - bottom])
    return np.concatenate([_tris_from_corners(c + off) for c in allc])


class TriSet:
    """Triangles with an owner id and a flag; vertical-ray queries through a coarse XY cell index."""

    def __init__(self):
        self.tris, self.owner, self.kind = [], [], []
        self._built = False

    def add(self, tris, owner, kind="mesh"):
        tris = np.asarray(tris, dtype=float).reshape(-1, 3, 3)
        self.tris.append(tris)
        self.owner += [owner] * len(tris)
        self.kind += [kind] * len(tris)
        self._built = False

    def build(self):
        self.T = np.concatenate(self.tris) if self.tris else np.zeros((0, 3, 3))
        self.owner = np.array(self.owner, dtype=object)
        self.kind = np.array(self.kind, dtype=object)
        T = self.T
        self.lo, self.hi = T.min(axis=1), T.max(axis=1)
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        L = np.linalg.norm(n, axis=1)
        self.nz = np.where(L > 0, n[:, 2] / np.where(L > 0, L, 1), 0)
        self.cells = defaultdict(list)
        self.big = []
        ci0 = np.floor(self.lo[:, :2] / CELL).astype(int)
        ci1 = np.floor(self.hi[:, :2] / CELL).astype(int)
        for k in range(len(T)):
            if (ci1[k] - ci0[k]).max() > 6:
                self.big.append(k)
                continue
            for i in range(ci0[k, 0], ci1[k, 0] + 1):
                for j in range(ci0[k, 1], ci1[k, 1] + 1):
                    self.cells[(i, j)].append(k)
        self.big = np.array(self.big, dtype=int)
        self.cells = {k: np.array(v, dtype=int) for k, v in self.cells.items()}
        self._built = True

    def vertical_hits(self, x, y, z):
        """Distinct surfaces above (x, y, z): [(dz, owner, kind, normal_z)] sorted by dz, hits <= ON_SURFACE skipped
        (the surface the sensor sits on). Coincident hits of one owner (shared triangle edges) are merged."""
        if not self._built:
            self.build()
        idx = self.cells.get((int(math.floor(x / CELL)), int(math.floor(y / CELL))), np.zeros(0, int))
        if len(self.big):
            idx = np.concatenate([idx, self.big])
        if not len(idx):
            return []
        T = self.T[idx]
        ok = (self.hi[idx, 2] > z + ON_SURFACE)
        T, idx = T[ok], idx[ok]
        if not len(idx):
            return []
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
        good = np.abs(d) > 1e-12
        l1 = np.where(good, ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / np.where(good, d, 1), -1)
        l2 = np.where(good, ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / np.where(good, d, 1), -1)
        l3 = 1 - l1 - l2
        e = -1e-9
        inside = good & (l1 >= e) & (l2 >= e) & (l3 >= e)
        zh = l1 * a[:, 2] + l2 * b[:, 2] + l3 * c[:, 2]
        sel = inside & (zh > z + ON_SURFACE)
        seen, out = set(), []
        for k in np.nonzero(sel)[0]:
            key = (self.owner[idx[k]], round(float(zh[k]), 3))
            if key in seen:
                continue
            seen.add(key)
            out.append((float(zh[k] - z), self.owner[idx[k]], self.kind[idx[k]], float(self.nz[idx[k]])))
        return sorted(out)

    def surface_below(self, x, y, z, max_depth=0.5):
        """Highest upward-facing surface at or below z (within max_depth): (gap, owner) or None."""
        if not self._built:
            self.build()
        idx = self.cells.get((int(math.floor(x / CELL)), int(math.floor(y / CELL))), np.zeros(0, int))
        if len(self.big):
            idx = np.concatenate([idx, self.big])
        best = None
        if not len(idx):
            return None
        T = self.T[idx]
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
        good = np.abs(d) > 1e-12
        l1 = np.where(good, ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / np.where(good, d, 1), -1)
        l2 = np.where(good, ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / np.where(good, d, 1), -1)
        l3 = 1 - l1 - l2
        e = -1e-9
        inside = good & (l1 >= e) & (l2 >= e) & (l3 >= e) & (self.nz[idx] > 0.5)
        zh = l1 * a[:, 2] + l2 * b[:, 2] + l3 * c[:, 2]
        for k in np.nonzero(inside & (zh <= z + ON_SURFACE) & (zh >= z - max_depth))[0]:
            gap = float(z - zh[k])
            if best is None or gap < best[0]:
                best = (gap, str(self.owner[idx[k]]))
        return best


def load_scene(path, library_root: str | None = None) -> TriSet:
    """Build the TriSet from a villa scene.json (props and models need the glTF library: $HOME/archpipe/assets/library)."""
    s = json.loads(Path(path).read_text(encoding="utf-8"))
    ts = TriSet()
    for m in s["meshes"]:
        vis = m.get("visibility")
        if vis is not None and vis.get("camera") is False:
            continue
        tris = []
        for f in m["faces"]:
            for k in range(1, len(f) - 1):
                tris.append((f[0], f[k], f[k + 1]))
        if tris:
            ts.add(tris, m["id"], "mesh")
    lib = Path(os.path.expandvars((library_root or s.get("library_root") or "$HOME/archpipe/assets/library")))
    cache = {}
    missing = []
    for spec in list(s.get("props", [])) + list(s.get("models", [])):
        gl = lib / "props" / spec["asset"] / "model.gltf"
        if not gl.exists():
            missing.append(spec["id"])
            continue
        if spec["asset"] not in cache:
            try:
                cache[spec["asset"]] = ("tri", gltf_triangles(gl))
            except Exception:                       # unsupported encoding: conservative boxes, flagged `bbox`
                cache[spec["asset"]] = ("bbox", gltf_boxes(gl))
        kind, data = cache[spec["asset"]]
        rot = spec.get("rotation_deg", [0, 0, 0])
        sc = spec.get("scale", 1.0)
        tris = place_triangles(data, spec["position"], rot, sc) if kind == "tri" else place_asset(data, spec["position"], rot, sc)
        ts.add(tris, spec["id"], "mesh" if kind == "tri" else "bbox")
    ts.missing_assets = missing
    ts.build()
    return ts
