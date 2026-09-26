"""The four stair options (stair_options.py) as complete two-storey layouts, for the Revit models and the client PDFs.

S1  U-stair in the old stair bay, dirty kitchen and guest WC mid-plan (concept A as of round 4)
S2  U-stair in the old stair bay, dirty kitchen and guest WC moved to the street end (recommended)
S3  U-stair in the street-end bay, the old opening infilled
S4  straight flight along the party wall; both core doors move

Rooms are rectangles in metres (Revit axes), as concept.villa; every layout passes villa.critique.
"""
from __future__ import annotations

from . import villa as V
from .villa import _layout, _room

YP, YE, YC, YK, X0, XR = V.YP, V.YE, V.YC, V.YK, V.X0, V.XR
SX0, SX1 = V.SX0, V.SX1


def _suite(bed_x0, dress_x0):
    return [_room("kids-bath-spacer", "GF", (0, 0, 0, 0), "store")][:0] + [
        _room("parents-bed", "GF", (bed_x0, YC, XR, YE), "bedroom", "parents' bedroom", suite=True, first=True),
        _room("parents-dressing", "GF", (dress_x0, YP, XR, YC), "dressing", "dressing", suite=True),
        _room("parents-ensuite", "GF", V.BUMP, "ensuite", "en-suite", suite=True)]


def _b_back(kitchen_x0, services_mid=True):
    """Kitchen, dining, garden living and rear store (the open half of the basement)."""
    rooms = [_room("dining", "B", (15.197, YP, 18.597, YE), "dining", "dining"),
             _room("living", "B", (18.597, YP, XR, YE), "living", "garden living"),
             _room("store-rear", "B", V.REAR_SHARE, "store", "store")]
    links = [("kitchen", "dining"), ("dining", "living"), ("living", "store-rear")]
    if services_mid:
        rooms += [_room("gallery", "B", (kitchen_x0, YP, 11.397, YK), "hall", "gallery"),
                  _room("kitchen", "B", (kitchen_x0, YK, 15.197, YE), "kitchen", "open kitchen"),
                  _room("dirty-kitchen", "B", (11.397, YP, 13.797, YK), "utility", "dirty kitchen"),
                  _room("guest-wc", "B", (13.797, YP, 15.197, YK), "wc", "guest WC")]
        links += [("gallery", "kitchen"), ("gallery", "dirty-kitchen"), ("dirty-kitchen", "kitchen"),
                  ("dining", "guest-wc")]
    else:
        rooms += [_room("kitchen", "B", (kitchen_x0, YP, 15.197, YE), "kitchen", "open kitchen")]
    return rooms, links


def s1():
    lay = V.concept_a()
    lay.update(id="S1", title="Option 1: U-stair in the old stair bay (services mid-plan)")
    return lay


def s2():
    """Services to the street end: dirty kitchen by the street window, guest WC and laundry in our half of the core's
    front end, an L-shaped entrance hall; the whole back of the basement opens to the garden."""
    gf, gl, ge = V._gf()
    b = [_room("dirty-kitchen", "B", (X0, YP, 5.9, YK), "utility", "dirty kitchen (street window)"),
         _room("laundry", "B", V.FRONT_SHARE, "utility", "laundry"),
         _room("hall-b", "B", (5.9, YP, SX1, YC), "entrance", "entrance hall"),
         _room("hall-b2", "B", (5.9, YC, SX0, YK), "hall", "hall"),
         _room("flex", "B", (X0, YK, SX0, YE), "study", "flex room"),
         _room("stair-b", "B", V.STAIR, "stair", "stair (U, to the GF)", ends=[["h", YC, SX0, SX0 + 0.9]])]
    bl = [("hall-b", "dirty-kitchen"), ("hall-b", "laundry"), ("hall-b", "hall-b2"),
          ("hall-b2", "flex"), ("hall-b", "stair-b"), ("hall-b", "kitchen")]
    back, backl = _b_back(SX1, services_mid=False)
    back = [r for r in back if r["id"] != "store-rear"] + [_room("guest-wc", "B", (V.REAR_SHARE[0], V.AX, 19.268, YP), "wc", "guest WC"), _room("store-rear", "B", (19.268, V.AX, XR, YP), "store", "store")]
    backl += [("dining", "guest-wc")]
    lay = _layout("S2", "Option 2: U-stair in the old stair bay, services at the street end (recommended)",
                  gf + b + back, gl + bl + backl, ge + [("hall-b", "B", "core-lobby-b")],
                  "As option 1 upstairs; in the basement the dirty kitchen, guest WC and laundry move to the street "
                  "end so the whole back of the basement, and the view from the entrance, open to the garden.")
    lay.update(stair="u", terrace=list(V.TERRACE))
    return lay


def s3():
    """U-stair in the street-end bay (x 3.977-6.077); the old stair bay becomes a room upstairs and downstairs."""
    st = (X0, YC, 6.077, YE)
    gf = [_room("stair-gf", "GF", st, "stair", "stair (U, from the basement)", ends=[["h", YC, 5.077, 6.077]]),
          _room("corridor", "GF", (X0, YP, 19.527, YC), "corridor", "hall"),
          _room("study-game", "GF", (6.077, YC, SX1, YE), "study", "study / game room"),
          _room("kids-a", "GF", (SX1, YC, 12.827, YE), "bedroom", "kids bedroom A"),
          _room("kids-b", "GF", (12.827, YC, 16.427, YE), "bedroom", "kids bedroom B"),
          _room("family-bath", "GF", (16.427, YC, 18.427, YE), "bathroom", "family bathroom")] + _suite(18.427, 19.527)
    gl = [("corridor", "stair-gf"), ("corridor", "study-game"), ("corridor", "kids-a"), ("corridor", "kids-b"),
          ("corridor", "family-bath"), ("corridor", "parents-bed"), ("parents-bed", "parents-dressing"),
          ("parents-dressing", "parents-ensuite")]
    b = [_room("stair-b", "B", st, "stair", "stair (U, to the GF)", ends=[["h", YC, 3.977, 4.977]]),
         _room("hall-b", "B", (X0, YP, SX1, YC), "entrance", "entrance hall"),
         _room("laundry", "B", V.FRONT_SHARE, "utility", "laundry"),
         _room("dirty-kitchen", "B", (6.077, YC, 8.2, YE), "utility", "dirty kitchen"),
         _room("flex", "B", (8.2, YC, 11.7, YE), "study", "flex room")]
    bl = [("hall-b", "stair-b"), ("hall-b", "laundry"), ("hall-b", "dirty-kitchen"),
          ("hall-b", "flex")]
    back = [_room("kitchen", "B", (11.7, YP, 15.197, YE), "kitchen", "open kitchen"),
            _room("gallery", "B", (SX1, YP, 11.7, YC), "hall", "gallery"),
            _room("dining", "B", (15.197, YP, 18.597, YE), "dining", "dining"),
            _room("living", "B", (18.597, YP, XR, YE), "living", "garden living"),
            _room("guest-wc", "B", (V.REAR_SHARE[0], V.AX, 19.268, YP), "wc", "guest WC"), _room("store-rear", "B", (19.268, V.AX, XR, YP), "store", "store")]
    backl = [("hall-b", "gallery"), ("gallery", "kitchen"), ("kitchen", "dining"), ("dining", "living"),
             ("living", "store-rear"), ("dining", "guest-wc")]
    lay = _layout("S3", "Option 3: U-stair in the street-end bay", gf + b + back, gl + bl + backl,
                  [("corridor", "GF", "core-entrance"), ("hall-b", "B", "core-lobby-b")],
                  "The stair moves to the street-end bay; the old stair bay becomes the study upstairs and the dirty "
                  "kitchen downstairs. Needs a new slab opening at the street end and the old one infilled.")
    lay.update(stair="u-front", terrace=list(V.TERRACE))
    return lay


def s4():
    """Straight flight along the party wall (x 4.877-9.357), top landing at the street end clear of column 1590377;
    both core doors move (basement: second lobby; GF: onto the top landing)."""
    ys = round(YP + 1.2, 3)                  # flight zone edge
    yg = round(YP + 2.3, 3)                  # GF gallery edge beside the void
    foot_cover = 8.357                       # GF floor over the foot end (headroom)
    gf = [_room("landing-gf", "GF", (X0, YP, 4.877, yg), "landing", "stair landing (core door)"),
          _room("stair-gf", "GF", (4.877, YP, foot_cover, yg), "stair", "stair void + gallery",
                ends=[["v", 4.877, YP + 0.25, ys]]),
          _room("corridor", "GF", (foot_cover, YP, 19.527, YC), "corridor", "hall"),
          _room("hall-gf", "GF", (foot_cover, YC, foot_cover + 0.0001, yg), "corridor", "x")][:3] + [
          _room("study-game", "GF", (X0, yg, foot_cover, YE), "study", "study / game room"),
          _room("kids-a", "GF", (foot_cover, YC, 12.2, YE), "bedroom", "kids bedroom A"),
          _room("kids-b", "GF", (12.2, YC, 16.0, YE), "bedroom", "kids bedroom B"),
          _room("family-bath", "GF", (16.0, YC, 18.0, YE), "bathroom", "family bathroom")] + _suite(18.0, 19.527)
    gl = [("landing-gf", "stair-gf"), ("stair-gf", "corridor"), ("stair-gf", "study-game"), ("corridor", "kids-a"),
          ("corridor", "kids-b"), ("corridor", "family-bath"), ("corridor", "parents-bed"),
          ("parents-bed", "parents-dressing"), ("parents-dressing", "parents-ensuite")]
    yd = -26.271                             # passage / hall depth beside the flight
    b = [_room("utility-lobby", "B", (X0, YP, 4.877, ys), "hall", "utility lobby (under the top landing)"),
         _room("stair-b", "B", (4.877, YP, 9.357, ys), "stair", "stair (straight, to the GF)",
               ends=[["v", 9.357, YP + 0.25, ys]]),
         _room("laundry", "B", V.FRONT_SHARE, "utility", "laundry"),
         _room("passage-b", "B", (X0, ys, 9.357, yd), "corridor", "passage"),
         _room("dirty-kitchen", "B", (X0, yd, 5.817, YE), "utility", "dirty kitchen (street window)"),
         _room("flex", "B", (5.817, yd, 9.357, YE), "study", "flex room"),
         _room("hall-b", "B", (9.357, YP, 11.397, yd), "hall", "hall at the stair foot"),
         _room("kitchen", "B", (9.357, yd, 15.197, YE), "kitchen", "open kitchen"),
         _room("kitchen-island", "B", (11.397, YP, 13.6, yd), "hall", "open kitchen (island zone)"),
         _room("entry-b", "B", (13.6, YP, 15.197, yd), "entrance", "entrance (second core lobby)"),
         _room("dining", "B", (15.197, YP, 18.597, YE), "dining", "dining"),
         _room("living", "B", (18.597, YP, XR, YE), "living", "garden living"),
         _room("guest-wc", "B", (V.REAR_SHARE[0], V.AX, 19.268, YP), "wc", "guest WC"),
         _room("store-rear", "B", (19.268, V.AX, XR, YP), "store", "store")]
    bl = [("hall-b", "stair-b"), ("hall-b", "passage-b"), ("passage-b", "dirty-kitchen"), ("passage-b", "flex"),
          ("passage-b", "utility-lobby"), ("utility-lobby", "laundry"), ("hall-b", "kitchen"),
          ("hall-b", "kitchen-island"), ("kitchen-island", "entry-b"), ("kitchen-island", "kitchen"),
          ("entry-b", "kitchen"), ("kitchen", "dining"), ("dining", "living"), ("dining", "guest-wc"),
          ("living", "store-rear")]
    lay = _layout("S4", "Option 4: straight flight along the party wall", gf + b, gl + bl,
                  [("landing-gf", "GF", "core-entrance"), ("entry-b", "B", "core-lobby-b2")],
                  "A straight flight against the blind party wall; the facade stays free for rooms. Needs a new "
                  "3.4 m slab opening along the party wall, the old one infilled, and both core doors moved.")
    lay.update(stair="party-fixed", terrace=list(V.TERRACE))
    return lay


def options():
    return [s1(), s2(), s3(), s4()]


POD_FLEX = (X0, YE, SX0, V.FENCE_E)                  # street end of the east yard, built to the fence
POD_DIRTY = (9.30, YE, 12.40, round(YE + 2.0, 3))     # opposite the open kitchen; 0.99 m service path to the fence


def s5():
    """Client 2026-09-26: keep the basement's full width clear; put the closed rooms in single-storey blocks in the
    east yard (roof at the GF floor, below the fence top and the GF sills). Laundry and guest WC already sit in our
    halves of the core's two ends, outside the bar."""
    gf, gl, ge = V._gf()
    b = [_room("hall-b", "B", (X0, YP, SX1, YC), "entrance", "entrance hall"),
         _room("lounge", "B", (X0, YC, SX0, YE), "living", "family / TV lounge (open)"),
         _room("stair-b", "B", V.STAIR, "stair", "stair (U, to the GF)", ends=[["h", YC, SX0, SX0 + 0.9]]),
         _room("laundry", "B", V.FRONT_SHARE, "utility", "laundry"),
         _room("kitchen", "B", (SX1, YP, 15.197, YE), "kitchen", "open kitchen"),
         _room("dining", "B", (15.197, YP, 18.597, YE), "dining", "dining"),
         _room("living", "B", (18.597, YP, XR, YE), "living", "garden living"),
         _room("guest-wc", "B", (V.REAR_SHARE[0], V.AX, 19.268, YP), "wc", "guest WC"),
         _room("store-rear", "B", (19.268, V.AX, XR, YP), "store", "store"),
         _room("flex", "B", POD_FLEX, "study", "flex room (east-yard block)"),
         _room("dirty-kitchen", "B", POD_DIRTY, "utility", "dirty kitchen (east-yard block)")]
    bl = [("hall-b", "stair-b"), ("hall-b", "lounge"), ("hall-b", "laundry"), ("hall-b", "kitchen"),
          ("lounge", "flex"), ("kitchen", "dirty-kitchen"), ("kitchen", "dining"), ("dining", "living"),
          ("dining", "guest-wc"), ("living", "store-rear")]
    lay = _layout("S5", "Option 5: full-width open basement, closed rooms in east-yard blocks",
                  gf + b, gl + bl, ge + [("hall-b", "B", "core-lobby-b")],
                  "The basement bar stays open across its full width from the stair to the garden; the flex room and "
                  "the dirty kitchen move into single-storey blocks in the east yard (roofs at street +1.20, under "
                  "the fence top and the GF sills); laundry and guest WC sit in our halves of the core ends.")
    lay.update(stair="u", terrace=list(V.TERRACE), extension=[list(POD_FLEX), list(POD_DIRTY)])
    return lay


def options():                                   # noqa: F811  (round 6: the client's east-yard idea added)
    return [s1(), s2(), s3(), s4(), s5()]
