"""Round 11 designs (client 2026-09-27): four distinct layouts on the settled base.

Settled (kept in all four): the straight stair along the party wall; the GF with the family bath beside the stair top,
the study open to the stair, the kids rooms beyond the bath; the cinema under the ramp; the lounge glazed floor to
beam across its whole street run; one car.

Client r11 brief:
  * the east-yard extension stops at the FIFTH east-face column (x 14.902-15.412; it ran to between the 5th and the
    6th): the extension ends on the column's far face, x 15.412. The deck carries one car (8.5 m from the ramp top;
    two cars in tandem need 9.8 m, card mh-garage-min-length x 2); beyond the car the roof over the rooms below is a
    PLANTED roof (not a deck): it keeps the kids room's window a normal window and shades the rooms under it;
  * the store in the rear share behind the garden living "looks like a waste": each design gives it a use;
  * dining and open kitchen shift toward the street (north) onto the column grid (col 4 x 11.2, col 5 x 14.9-15.4,
    col 6 x 18.4-18.9): each room then owns whole column bays and whole windows;
  * daylight by practical means only: floor-to-beam glazing on every basement face a lived-in room looks out of
    (no one sees in below the 4 m fence) and white finishes (fences, our walls and ceilings, reflectance 0.80,
    card tss-reflectance-table). No slot, no light well.

The four designs:
  D1 "Aligned"          - kitchen col 4-5, dining col 5-6 (east window), living col 6 to the garden; the rear store
                          becomes a bar / library alcove of the living with its own floor-to-beam garden window.
  D2 "Kitchen in light" - the kitchen takes the lit bay (col 5-6, east glazing), dining in the middle bay; the rear
                          store becomes a scullery off the kitchen and a garden WC under the ensuite above (one wet
                          stack); the room under the deck becomes laundry + store.
  D3 "Garden kitchen"   - kitchen and dining at the garden end (the brightest place), a sitting room in the lit bay
                          col 5-6, a family / TV room in the middle; the rear store becomes the dirty kitchen /
                          scullery right behind the kitchen, with a garden door; under the deck: laundry + store.
  D4 "Double height"    - D1's basement with the street lounge made double height: the GF study gives up its street
                          end (a void over the lounge, inside the kept perimeter beams) and becomes a gallery; the
                          GF street window and the deck door light the lounge from above. The rear store becomes a
                          garden WC + outdoor shower. Eccentric, and it needs the structural engineer (slab cut).
"""
from __future__ import annotations

from . import villa as V
from . import villa_parking as P
from .villa import _room

YP, YE, YK, YC, X0, XR, AX = V.YP, V.YE, V.YK, V.YC, V.X0, V.XR, V.AX
FE, FN = V.FENCE_E, V.FENCE_N
COL4, COL5, COL5_FAR, COL6 = 11.197, 14.902, 15.412, 18.367     # east-face column faces (CAD)
EXT_END = COL5_FAR
YS = round(YP + 1.2, 3)                                           # the straight stair's outer edge (-27.471)
XF = 9.657                                                        # the stair foot (stairs.party_flight_r8)
ENTRY = (14.134, 15.745)                                          # the second core lobby door (ENTRY_SEGMENTS)
RS_ = V.REAR_SHARE                                                # 17.268..22.597 x AX..YP
VOID_X1 = 5.6                                                     # D4: the lounge void, street face to x 5.6
DESIGNS = ("D1", "D2", "D3")          # round 12 (client): D1 kept; D2 redefined (kitchen to the lit bay); D3 kitchen
#                                       north. Round 11's D2 and D3 are superseded (git history); D4's void stays
#                                       available as design("D4") = D1 + the void.
TITLES = {"D1": "Aligned: kitchen bay 4-5, dining bay 5-6, garden living, bar alcove in the rear share",
          "D2": "Kitchen at the heart: working kitchen bay 4-5 opening to an island in the lit bay 5-6; living + "
                "dining at the garden",
          "D3": "Kitchen north: kitchen + breakfast at the street window, dirty kitchen beside it under the ramp; "
                "cinema under the deck; dining in the lit bay; living at the garden",
          "D4": "Double height: the street lounge open to the GF study above, garden WC + shower in the rear share"}


def _front():
    """The street end, the same in every design: lounge (with the alcove under the stair's top landing), stair,
    pantry in the front share."""
    return [_room("lounge", "B", (X0, YS, XF, YE), "living", "lounge (street window floor to beam)"),
            _room("lounge-nook", "B", (X0, YP, 5.177, YS), "living", "lounge (under the stair's top landing)",
                  part_of="lounge"),
            _room("stair-b", "B", (5.177, YP, XF, YS), "stair", "stair (straight, to the GF)",
                  ends=[["v", XF, YP + 0.25, YS]]),
            _room("pantry", "B", V.FRONT_SHARE, "store", "pantry / store")]


FRONT_LINKS = [("lounge", "lounge-nook"), ("lounge-nook", "pantry"), ("lounge", "cinema"), ("cinema", "store-ramp")]


def _under(uses):
    """Rooms under the ramp and the deck to the fifth column: store (low end), cinema (under the ramp), then `uses`
    [(id, occupancy, name, x0, x1)] under the deck."""
    rooms = [_room("store-ramp", "B", (FN, YE, P.X_LOW, FE), "store", "store under the ramp (1.45-2.0 m clear)",
                   ext=True),
             _room("cinema", "B", (P.X_LOW, YE, P.SX1, FE), "media", "cinema (under the ramp; 2.0-2.65 m ceiling)",
                   ext=True)]
    rooms += [_room(i, "B", (a, YE, b, FE), o, n, ext=True) for i, o, n, a, b in uses]
    return rooms


def _basement(d):
    if d == "D3":
        return _basement_north()
    b = _front()
    links = list(FRONT_LINKS)
    if d == "D2":
        return _basement_heart(b, links)
    hall = _room("hall-b", "B", (XF, YP, COL4, YK), "hall", "hall at the stair foot")
    entry = _room("entry-b", "B", (ENTRY[0], YP, ENTRY[1], YK), "entrance", "entrance (second core lobby)")
    if d in ("D1", "D4"):
        b += [hall, entry,
              _room("family", "B", (XF, YK, COL4, YE), "living", "family / TV corner (open to the lounge)",
                    part_of="lounge"),
              _room("kitchen", "B", (COL4, YK, COL5, YE), "kitchen", "open kitchen (column bay 4-5)"),
              _room("kitchen-island", "B", (COL4, YP, ENTRY[0], YK), "kitchen", "open kitchen (island)"),
              _room("dining", "B", (COL5, YK, COL6, YE), "dining", "dining (column bay 5-6, east window)"),
              _room("dining-side", "B", (ENTRY[1], YP, COL6, YK), "dining", "dining (party side)", part_of="dining"),
              _room("living", "B", (COL6, YP, XR, YE), "living", "garden living")]
        links += [("lounge", "family"), ("hall-b", "stair-b"), ("hall-b", "family"), ("hall-b", "kitchen-island"),
                  ("family", "kitchen"), ("kitchen", "kitchen-island"), ("kitchen-island", "entry-b"),
                  ("kitchen", "dining"), ("entry-b", "dining-side"),
                  ("dining", "dining-side"), ("dining", "living"), ("dining-side", "living"),
                  ("family", "guest-wc"), ("kitchen", "dirty-kitchen")]
        under = [("guest-wc", "wc", "guest WC (under the deck)", P.SX1, P.GUEST_WC_END),
                 ("dirty-kitchen", "utility", "dirty kitchen + laundry (full-height window at the end)",
                  P.GUEST_WC_END, EXT_END)]
        if d == "D1":
            b.append(_room("bar-alcove", "B", RS_, "living", "bar / library alcove (floor-to-beam garden window)", part_of="living"))
            links += [("living", "bar-alcove")]
        else:
            b += [_room("garden-wc", "B", (V.BUMP[0], AX, XR, YP), "wc", "garden WC + outdoor shower (under the ensuite; "
                        "a garden door fits the 1.14 m run)"),
                  _room("store-rear", "B", (RS_[0], AX, V.BUMP[0], YP), "store", "garden store (furniture, cushions)")]
            links += [("living", "garden-wc"), ("dining-side", "store-rear")]
    return b + _under(under), links


def _basement_heart(b, links):
    """Round 12 D2 (client: the kitchen in the lit bay, the living keeps the garden): one long family kitchen from
    col 4 to col 6 - the working side (cooking wall, tall storage, the door to the dirty kitchen under the deck) in
    bay 4-5, the island and breakfast table in the lit bay 5-6 at the east window - open to the living + dining at
    the garden. The street lounge becomes the family / TV room."""
    b[0] = dict(b[0], name="family / TV lounge (street window floor to beam)")
    b += [_room("hall-b", "B", (XF, YP, COL4, YK), "hall", "hall at the stair foot"),
          _room("entry-b", "B", (ENTRY[0], YP, ENTRY[1], YK), "entrance", "entrance (second core lobby)"),
          _room("family", "B", (XF, YK, COL4, YE), "living", "family / TV (open to the lounge)", part_of="lounge"),
          _room("kitchen-work", "B", (COL4, YK, COL5, YE), "kitchen", "kitchen: cooking wall (door to the dirty "
                "kitchen)"),
          _room("kitchen-store", "B", (COL4, YP, ENTRY[0], YK), "kitchen", "kitchen: tall storage wall"),
          _room("kitchen", "B", (COL5, YK, COL6, YE), "kitchen", "kitchen: island + breakfast (lit bay, east window)"),
          _room("kitchen-side", "B", (ENTRY[1], YP, COL6, YK), "kitchen", "kitchen (party side)", part_of="kitchen"),
          _room("living", "B", (COL6, YP, XR, YE), "living", "garden living + dining"),
          _room("bar-alcove", "B", RS_, "living", "bar / library alcove (garden window)", part_of="living")]
    links += [("lounge", "family"), ("hall-b", "stair-b"), ("hall-b", "family"), ("hall-b", "kitchen-store"),
              ("family", "kitchen-work"), ("kitchen-work", "kitchen-store"), ("kitchen-store", "entry-b"),
              ("kitchen-work", "kitchen"), ("entry-b", "kitchen-side"), ("kitchen", "kitchen-side"),
              ("kitchen", "living"), ("kitchen-side", "living"), ("living", "bar-alcove"),
              ("family", "guest-wc"), ("kitchen-work", "dirty-kitchen")]
    under = [("guest-wc", "wc", "guest WC (under the deck)", P.SX1, P.GUEST_WC_END),
             ("dirty-kitchen", "utility", "dirty kitchen + laundry (full-height window at the end)",
              P.GUEST_WC_END, EXT_END)]
    return b + _under(under), links


def _basement_north():
    """Round 12 D3 (client: open to an option with the kitchen on the north side): kitchen + breakfast at the street
    end behind the 3.4 m floor-to-beam window, a glazed door to the sunken patio, the larder under the stair landing
    and the pantry beside it, and the dirty kitchen + laundry right next to it under the ramp. The cinema moves under
    the deck (2.65 m clear everywhere). Middle: family / TV; lit bay 5-6: dining; garden: living."""
    b = [_room("kitchen", "B", (X0, YS, XF, YE), "kitchen", "kitchen + breakfast (street window floor to beam)"),
         _room("kitchen-nook", "B", (X0, YP, 5.177, YS), "kitchen", "larder (under the stair's top landing)",
               part_of="kitchen"),
         _room("stair-b", "B", (5.177, YP, XF, YS), "stair", "stair (straight, to the GF)",
               ends=[["v", XF, YP + 0.25, YS]]),
         _room("pantry", "B", V.FRONT_SHARE, "store", "pantry / store (off the larder)"),
         _room("hall-b", "B", (XF, YP, ENTRY[0], YK), "hall", "hall (stair foot to the second core door)"),
         _room("entry-b", "B", (ENTRY[0], YP, ENTRY[1], YK), "entrance", "entrance (second core lobby)"),
         _room("family", "B", (XF, YK, COL5, YE), "living", "family / TV (middle)"),
         _room("dining", "B", (COL5, YK, COL6, YE), "dining", "dining (lit bay 5-6, east window)"),
         _room("dining-side", "B", (ENTRY[1], YP, COL6, YK), "dining", "dining (party side)", part_of="dining"),
         _room("living", "B", (COL6, YP, XR, YE), "living", "garden living"),
         _room("bar-alcove", "B", RS_, "living", "bar / library alcove (garden window)", part_of="living")]
    links = [("kitchen", "kitchen-nook"), ("kitchen-nook", "pantry"), ("kitchen", "family"),
             ("hall-b", "stair-b"), ("hall-b", "family"), ("hall-b", "entry-b"), ("entry-b", "dining-side"),
             ("family", "dining"), ("dining", "dining-side"), ("dining", "living"), ("dining-side", "living"),
             ("living", "bar-alcove"), ("kitchen", "dirty-kitchen"), ("dirty-kitchen", "store-ramp"),
             ("dirty-kitchen", "store-top"), ("family", "guest-wc"), ("family", "cinema")]
    rooms = [_room("store-ramp", "B", (FN, YE, P.X_LOW, FE), "store", "store under the ramp (1.45-2.0 m clear)",
                   ext=True),
             _room("dirty-kitchen", "B", (P.X_LOW, YE, 7.2, FE), "utility", "dirty kitchen + laundry (under the "
                   "ramp, beside the kitchen)", ext=True),
             _room("store-top", "B", (7.2, YE, P.SX1, FE), "store", "store (under the ramp top)", ext=True),
             _room("guest-wc", "B", (P.SX1, YE, P.GUEST_WC_END, FE), "wc", "guest WC (under the deck)", ext=True),
             _room("cinema", "B", (P.GUEST_WC_END, YE, EXT_END, FE), "media", "cinema (under the deck; 2.65 m "
                   "clear; full-height end window with a blackout blind)", ext=True)]
    return b + rooms, links


def _gf(d):
    lay = P.option("straight", 1)
    gf = [dict(r) for r in lay["rooms"].values() if r["level"] == "GF"]
    links = [l for l in lay["links"] if lay["rooms"][l[0]]["level"] == "GF"]
    if d == "D4":
        out = []
        for r in gf:
            if r["id"] == "study-game":
                x0, y0, x1, y1 = r["rect"]
                out.append(dict(r, rect=[VOID_X1, y0, x1, y1], name="study gallery (over the double-height lounge; "
                                "sliding door to the deck)"))
                out.append(_room("study-void", "GF", (x0, y0, VOID_X1, y1), "study",
                                 "void over the lounge (balustrade)", part_of="study-game", void=True, open=True))
            else:
                out.append(r)
        gf = out
        links = links + [("study-game", "study-void")]
    return gf, links, [e for e in lay["entries"] if e[1] == "GF"], lay


def design(d):
    gf, gl, ge, base = _gf(d)
    b, bl = _basement(d)
    under = [r for r in b if r.get("ext")]
    deck_end = round(P.RAMP_X1 + P.CARS[1], 3)                   # the car's deck; planted roof beyond it
    lay = V._layout(d, "Design %s - %s" % (d, TITLES[d]), gf + b, gl + bl, ge + [("entry-b", "B", "core-lobby-b2")],
                    TITLES[d])
    if d == "D1":
        from .authored_values import override
        override(lay["rooms"]["guest-wc"], "occupancy", "bathroom",
                 "client 2026-09-29: open walk-in shower changes guest WC to bathroom")
        override(lay["rooms"]["guest-wc"], "name", "guest bathroom (under the deck)",
                 "client 2026-09-29: guest room now includes a shower")
    lay.update({k: base[k] for k in ("stair", "terrace", "deck_door", "north_patio")})
    lay.update(extension=[list(r["rect"]) for r in under],
               basement_full_height=("east",),         # round 12: north + east; garden doors as round 10
               daylight_variant={"white": True},
               parking2=dict(base["parking2"], deck=[P.RAMP_X1, YE, deck_end, FE],
                             roof_beyond_deck=[deck_end, YE, EXT_END, FE], roof_beyond_planted=True))
    return lay


def designs(ids=DESIGNS):
    return [design(d) for d in ids]
