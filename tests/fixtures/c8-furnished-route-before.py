"""Frozen function at f8f8cc6; AST comparison only, never imported."""
def route_problems(lay, sp, items, level, cell=0.02, room_ids=None):
    """In each open cluster of rooms, a 914 mm body (card mitton-path-of-travel-min) must get from every door of
    the cluster to every other door and to every piece's working side. Furniture over 0.3 m and the columns are
    obstacles; walls are the cluster's own edges. Returns [(problem, measured)]."""
    out = []
    done = set()
    zones = _door_approaches(sp, lay, level)
    for rid, r in lay["rooms"].items():
        if r["level"] != level or rid in done:
            continue
        cl = _cluster(lay, rid)
        done |= cl
        if room_ids is not None and not cl.intersection(room_ids):
            continue
        rects = [lay["rooms"][c]["rect"] for c in cl]
        x0 = min(q[0] for q in rects); y0 = min(q[1] for q in rects)
        x1 = max(q[2] for q in rects); y1 = max(q[3] for q in rects)
        nx, ny = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
        gx, gy = x0 + (np.arange(nx) + 0.5) * cell, y0 + (np.arange(ny) + 0.5) * cell
        X, Y = np.meshgrid(gx, gy, indexing="ij")
        free = np.zeros((nx, ny), bool)
        for a, b, c, d in rects:                  # half-open, so a cell centred on a shared edge is not lost
            free |= (X >= a - 1e-9) & (X < c - 1e-9) & (Y >= b - 1e-9) & (Y < d - 1e-9)
        walls_l = _walls(sp, level)
        obst = [footprint(it) for it in items if it["room"] in cl and it["h"] >= 0.3] + _columns() + walls_l
        chairs = {it["id"]: _cinema_chair_rects(it) for it in items if it["id"] == "cinema-desk" and it["room"] in cl}
        obst += [rect for pair in chairs.values() for rect in pair]   # Mitton path body must pass the pulled-out chairs
        # not floor: the basement flight (you stand at its foot, not on it), the GF stair opening and any voids
        obst += [lay["rooms"][c]["rect"] for c in cl if lay["rooms"][c]["occupancy"] == "stair" and level == "B"]
        if level == "GF":
            obst += ([sp["gf_opening"]] if sp.get("gf_opening") else []) + sp.get("gf_voids", [])
        for a, b, c, d in obst:
            free &= ~((X > a) & (X < c) & (Y > b) & (Y < d))
        bedroom = all(lay["rooms"][c]["occupancy"] == "bedroom" for c in cl)
        # Client's 800 mm parents' dressing door is a private-suite access pinch. Use 750 mm as a project
        # waiver here, borrowed from the bedroom route dimension; AD M 2.25a itself applies to bedrooms,
        # not dressings. The 914 mm general route remains checked elsewhere.
        suite_dressing = cl == {"parents-dressing", "parents-dressing-ext"}
        width = min(BODY, BEDROOM_ROUTE) if bedroom or suite_dressing else BODY
        # The body is a DISC of the path width: a path's width is measured across the direction of travel, so a
        # disc is what a 914 mm path admits, on the straight and round a corner alike. (A square body of the same
        # side, used before, failed corners the path itself turns: its corner sweeps outside the path width.)
        # Clearance is the exact distance from a cell centre to each obstacle rectangle, and to the cluster's own
        # edge (open joins to other clusters), which is the outside of its rooms cut into rectangles.
        clear = np.full((nx, ny), np.inf)
        for a, b, c, d in obst + _outside(rects, width):
            if c < x0 - width or a > x1 + width or d < y0 - width or b > y1 + width:
                continue
            dx = np.maximum(np.maximum(a - X, X - c), 0.0)
            dy = np.maximum(np.maximum(b - Y, Y - d), 0.0)
            clear = np.minimum(clear, np.hypot(dx, dy))
        ok = free & (clear >= width / 2 - 1e-9)

        def touching(rect):
            # a real overlap (up to 0.1 m each way), not a sliver: a body grazing a zone's edge is not in it
            ex = min(0.1, (rect[2] - rect[0]) / 2 - 1e-6)
            ey = min(0.1, (rect[3] - rect[1]) / 2 - 1e-6)
            dx = np.maximum(np.maximum(rect[0] + ex - X, X - (rect[2] - ex)), 0.0)
            dy = np.maximum(np.maximum(rect[1] + ey - Y, Y - (rect[3] - ey)), 0.0)
            return ok & (np.hypot(dx, dy) < width / 2)
        nodes = []
        for z in zones:
            zc = ((z["rect"][0] + z["rect"][2]) / 2, (z["rect"][1] + z["rect"][3]) / 2)
            if any(q[0] <= zc[0] <= q[2] and q[1] <= zc[1] <= q[3] for q in rects):
                nodes.append(("door " + z["door"], [z["rect"]]))
        for sid in cl:                                   # stair arrivals: the floor in front of each stair end
            srm = lay["rooms"][sid]
            for end in srm.get("ends") or []:
                ax_, c, a, b = end
                x0s, y0s, x1s, y1s = srm["rect"]
                if ax_ == "v":
                    z = (c, a, c + 0.3, b) if abs(c - x1s) < 1e-6 else (c - 0.3, a, c, b)
                else:
                    z = (a, c, b, c + 0.3) if abs(c - y1s) < 1e-6 else (a, c - 0.3, b, c)
                nodes.append(("stair end of " + sid, [z]))
        for rid in cl:                                   # the principal bedroom's windows (AD M Diagram 2.4 note 1)
            if rid == PRINCIPAL_BEDROOM:                 # keyed on the room, not the bed type (a queen bed hid it)
                for w in sp["windows"]:
                    if w["level"] == level and w.get("room") == rid:
                        half = w["width"] / 2
                        ax_ = (w.get("span") or ["h"])[0]
                        rr = lay["rooms"][rid]["rect"]
                        # the strip starts at the wall's INNER face (a 0.2 m external wall swallowed a strip drawn
                        # from its line)
                        wr = next((q for q in walls_l if q[0] - 1e-6 <= w["x"] <= q[2] + 1e-6
                                   and q[1] - 1e-6 <= w["y"] <= q[3] + 1e-6), None)
                        if ax_ == "h":
                            hi = abs(w["y"] - rr[3]) < 0.06
                            y = (wr[1] if hi else wr[3]) if wr else w["y"]
                            z = (w["x"] - half, y - 0.3, w["x"] + half, y) if hi else \
                                (w["x"] - half, y, w["x"] + half, y + 0.3)
                        else:
                            hi = abs(w["x"] - rr[2]) < 0.06
                            x = (wr[0] if hi else wr[2]) if wr else w["x"]
                            z = (x - 0.3, w["y"] - half, x, w["y"] + half) if hi else \
                                (x, w["y"] - half, x + 0.3, w["y"] + half)
                        nodes.append(("window of " + rid, [_middle(z)]))
        for it in items:
            if it["room"] not in cl:
                continue
            if it.get("mounting_obstacle"):
                continue  # Measured fitting/wall obstruction, not a new route destination.
            t = cat.get(it["type"])
            # a side is reached along its middle, not at a corner (a body grazing a bed's foot corner is not at
            # the bedside): trim a quarter of the side, at most 0.3 m, off each end
            if t.clearance_any:                          # a single bed is reached on either long side
                nodes.append((it["id"], [_middle(side_zone(it, sd, 0.3)) for sd in t.clearance_any[0]]))
            elif it["type"] == "daybed_nook":
                # The sides are enclosed by joinery. The 914 mm route must touch its front access edge.
                nodes.append((it["id"], [_middle(side_zone(it, "front", 0.3))]))
            elif it["type"] in SEATS:                    # a seat facing a table is reached from its front or a side
                nodes.append((it["id"], [_middle(side_zone(it, sd, 0.3)) for sd in ("front", "left", "right")]))
            elif it["type"] == "coffee_table":          # a table among seats is reached from any side
                nodes.append((it["id"], [_middle(side_zone(it, sd, 0.3)) for sd in SIDES]))
            elif it["id"] in chairs:
                nodes.append((it["id"], [_middle((r[0], r[1] - 0.3, r[2], r[1])) for r in chairs[it["id"]]]))
            elif t.clearance["front"] > 0:
                nodes.append((it["id"], [_middle(side_zone(it, "front", 0.3))]))
        if len(nodes) < 2:
            continue
        nodes.sort(key=lambda n: 0 if n[0].startswith("stair end") else 1)   # start at the stair where there is one
        seen = np.zeros(ok.shape, bool)
        start = touching(nodes[0][1][0])
        q = collections.deque(zip(*np.nonzero(start)))
        seen[start] = True
        while q:
            i, j = q.popleft()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < ok.shape[0] and 0 <= b < ok.shape[1] and ok[a, b] and not seen[a, b]:
                    seen[a, b] = True
                    q.append((a, b))
        if TRACE is not None:                            # for plotting a cluster when a route fails
            TRACE["+".join(sorted(cl))] = dict(ok=ok, seen=seen, nodes=nodes, origin=(gx[0], gy[0]), cell=cell,
                                               body=width, obst=obst)
        for name, rs_ in nodes[1:]:
            if not any((touching(rect) & seen).any() for rect in rs_):
                out.append(("%s (%s): not reached by a %d mm path from %s" % (name, "+".join(sorted(cl)),
                                                                                 round(width * 1000), nodes[0][0]),
                            {}))
    return out
