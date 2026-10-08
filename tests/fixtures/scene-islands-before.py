"""Frozen starting-HEAD shared-vertex connectivity algorithm."""
def _islands(faces):
    """Faces grouped into connected parts (shared vertices, to 0.1 mm)."""
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    keys = []
    for f in faces:
        ks = [tuple(round(c * 10000) for c in v) for v in f]
        keys.append(ks[0])
        for k in ks[1:]:
            parent[find(ks[0])] = find(k)
    groups = {}
    for f, k in zip(faces, keys):
        groups.setdefault(find(k), []).append(f)
    return list(groups.values())
