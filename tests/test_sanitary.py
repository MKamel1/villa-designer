"""SAN-01 per UK AD G 4.8 / M4(1) and 5.6: positive and negative cases."""
import unittest

from archpipe import model, rules


def _p(rooms, entrance_on="L00"):
    levels = (model.Level("L00", "L00", 0, 3000), model.Level("L01", "L01", 3300, 3000))
    rs, walls, ops = [], [], []
    for i, (lv, occ) in enumerate(rooms):
        x = 5000 * i
        rs.append(model.Room(f"R{i}", lv, occ, ((x, 0), (x + 4000, 0), (x + 4000, 4000), (x, 4000)), occ))
    # an external door on the entrance storey: wall along y=0 under the first room on that level
    first = next(r for r in rs if r.level == entrance_on)
    x0 = first.boundary[0][0]
    walls.append(model.Wall("W", entrance_on, "EXT", (x0, -150), (x0 + 4000, -150)))
    ops.append(model.Opening("D", "W", "door", 1000, 2100, 2000))
    wt = (model.WallType("EXT", 300.0, (), True, ""),)
    return model.Project("t", levels=levels, wall_types=wt, walls=tuple(walls), openings=tuple(ops), rooms=tuple(rs))


def _msgs(p):
    return [f.message for lv in ("L00", "L01") for f in rules.r_sanitary_present(p, lv)]


class SanitaryTests(unittest.TestCase):
    def test_wc_on_entrance_storey_and_bathroom_upstairs_is_quiet(self):
        self.assertEqual(_msgs(_p([("L00", "hall"), ("L00", "wc"), ("L01", "bathroom")])), [])

    def test_upper_storey_without_wc_is_not_a_finding(self):
        self.assertEqual(_msgs(_p([("L00", "hall"), ("L00", "bathroom"), ("L01", "bedroom")])), [])

    def test_no_wc_on_entrance_storey_fails(self):
        m = _msgs(_p([("L00", "hall"), ("L01", "bathroom")]))
        self.assertEqual(sum("entrance storey" in x for x in m), 1)

    def test_no_bathroom_anywhere_fails(self):
        m = _msgs(_p([("L00", "hall"), ("L00", "wc")]))
        self.assertEqual(sum("No bathroom" in x for x in m), 1)

    def test_entrance_storey_without_habitable_rooms_may_use_principal_storey(self):
        # AD M 1.17a: entrance storey has only a hall; living and the WC are upstairs -> compliant
        self.assertEqual(sum("entrance storey" in x for x in _msgs(_p([("L00", "hall"), ("L01", "living"), ("L01", "wc"),
                                                                       ("L01", "bathroom")]))), 0)
        # ...but a WC on neither the principal nor the entrance storey is still a finding
        self.assertEqual(sum("entrance storey" in x for x in _msgs(_p([("L00", "hall"), ("L01", "living")]))), 1)

    def test_habitable_entrance_storey_still_needs_its_own_wc(self):
        m = _msgs(_p([("L00", "hall"), ("L00", "living"), ("L01", "wc"), ("L01", "bathroom")]))
        self.assertEqual(sum("entrance storey" in x for x in m), 1)

    def test_entrance_storey_follows_the_external_door(self):
        # entrance on L01 (e.g. a sloping site): the WC must be there, not on L00
        m = _msgs(_p([("L01", "hall"), ("L00", "wc"), ("L00", "bathroom")], entrance_on="L01"))
        self.assertEqual(sum("entrance storey" in x for x in m), 1)


if __name__ == "__main__":
    unittest.main()
