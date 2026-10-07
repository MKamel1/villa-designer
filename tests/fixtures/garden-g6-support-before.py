def unsupported(scene, lay=None):
    meshes = scene["meshes"]
    tris, owner = _triangles(meshes)
    S = _Surfaces(tris, owner)
    is_item = np.array([m["group"] in ITEM_GROUPS for m in meshes])
    glass = np.array([m["material"].startswith("glass") for m in meshes])
    building = (~is_item[owner]) & (~glass[owner])
    parts = {}
    for i, m in enumerate(meshes):
        if not is_item[i]:
            continue
        for k, faces in enumerate(_islands(m["faces"])):
            pts = np.array([p for f in faces for p in f], dtype=float)
            box = list(pts.min(axis=0)) + list(pts.max(axis=0))
            low = pts[pts[:, 2] <= box[2] + 0.005]
            parts[(i, k)] = (box, low[:: max(1, len(low) // 8)])
    ok = {}
    for (i, k), (b, low) in parts.items():
        # only the BUILDING grounds a group; resting on another piece only joins its group (the first version let a
        # lamp arm "rest" on its own shade while the shade hung from the arm: circular support)
        ok[(i, k)] = (any(S.meets(S.up & building, x, y, z) for x, y, z in low)
                      or S.meets(S.down & building, (b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[5])
                      or S.touches(building, b, FIX))
    keys = list(parts)
    parent = {k: k for k in keys}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    boxes = np.array([parts[k][0] for k in keys])
    for n, key in enumerate(keys):
        b = boxes[n]
        near = np.where(np.all(np.minimum(boxes[:, 3:], b[3:]) - np.maximum(boxes[:, :3], b[:3]) > -TOUCH, axis=1))[0]
        for j in near:
            if j != n:
                parent[find(key)] = find(keys[j])
    grounded = {find(k) for k in keys if ok[k]}
    out = [(meshes[i]["id"], [round(float(v), 3) for v in parts[(i, k)][0]]) for (i, k) in keys
           if find((i, k)) not in grounded]
    for p in scene.get("props", []):
        x, y, z = p["position"]
        if any(S.meets(S.up, x + dx, y + dy, z) for dx, dy in ((0, 0), (0.1, 0), (-0.1, 0), (0, 0.1), (0, -0.1))):
            continue
        if "art" in p["label"] and S.touches(building, [x - 0.05, y - 0.05, z, x + 0.05, y + 0.05, z + 0.5], 0.06):
            continue
        out.append((p["id"], p["position"]))
    return out

