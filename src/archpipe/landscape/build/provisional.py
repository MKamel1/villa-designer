"""PROVISIONAL composition used only to exercise the shade-tree and root-barrier builders until lane LDG delivers pruned trees in the layout.

It is NOT a design: it adds one pruned umbrella tree and its planting pit to a copy of a layout. Never used for a client-facing result once the
layout itself declares its trees (`trees[].pruned`, `trees[].root_barrier`).
"""
from __future__ import annotations

import copy


def _minus(r, h):
    """Rect r minus rect h as up to four rects."""
    x0, y0, x1, y1 = r
    a0, b0, a1, b1 = max(h[0], x0), max(h[1], y0), min(h[2], x1), min(h[3], y1)
    if a0 >= a1 or b0 >= b1:
        return [list(r)]
    out = [[x0, y0, x1, b0], [x0, b1, x1, y1], [x0, b0, a0, b1], [a1, b0, x1, b1]]
    return [q for q in out if q[2] - q[0] > 1e-6 and q[3] - q[1] > 1e-6]


def with_shade_tree(layout, species="olea_europaea", at=(26.2, -24.55), spread=3.4, height=3.6):
    L = copy.deepcopy(layout)
    x, y = at
    hole = (x - 0.6, y - 0.6, x + 0.6, y + 0.6)
    paved = []
    for pa in L["paved_areas"]:                      # the planting pit is cut out of the paving it stands in
        for k, q in enumerate(_minus(pa["rect"], hole)):
            paved.append(dict(pa, id=pa["id"] if k == 0 else "%s-cut%d" % (pa["id"], k), rect=q))
    L["paved_areas"] = paved
    L["planting_groups"].append(dict(id="ldb-prov-treepit", rect=[x - 0.6, y - 0.6, x + 0.6, y + 0.6], over_structure=False, plants=[], role="provisional shade-tree pit"))
    L["trees"].append(dict(id="ldb-prov-shade-tree", species=species, center=[x, y], form="small_tree", over_structure=False, mature_spread_m=spread, mature_height_m=height,
                           pruned=dict(spread_m=spread, height_m=height, clear_stem_m=1.9), root_barrier=True, trace=["PROVISIONAL"]))
    return L
