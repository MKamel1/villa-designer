"""Frozen starting-HEAD face triangulation and owner ordering."""
def _triangles(meshes):
    tris, owner = [], []
    for i, m in enumerate(meshes):
        for f in m["faces"]:
            ts = [(f[0], f[k], f[k + 1]) for k in range(1, len(f) - 1)] if len(f) <= 4 else _ear_clip(f)
            tris.extend(ts)
            owner.extend([i] * len(ts))
    return np.array(tris, dtype=float).reshape(-1, 3, 3), np.array(owner, dtype=int)
