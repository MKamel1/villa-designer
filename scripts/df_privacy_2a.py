"""Lane DF option 2A: option 2 (straight vestibule, no bump-out, no facade change) with SELF-CLOSING doors.
PROPOSAL ONLY. Reports the all-open / one-open sightline results and writes plan-2a.svg/png + results-2a.json.
Run: python scripts/df_privacy_2a.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_privacy_options as O
from df_privacy_options import *

DRESS_OPEN = box(19.477, -28.346, 19.577, -27.446)   # dressing doorway widened 0.80 -> 0.90 (north jamb moved 0.10 m)
def op2a():
    o = dict(O.opt_defs()["2"])
    o["title"] = "2A STRAIGHT VESTIBULE + SELF-CLOSING DOORS (no bump-out, no facade change)"
    o["cut"] = [SUITE_CUT, DRESS_OPEN]
    o["stor"] = [box(17.60, CY0, 18.60, CY0 + 0.20)]            # storage 0.30 -> 0.20 deep: removes the 0.702 pinch
    o["doors"] = [("sw", (17.55, -27.471), (17.55, -28.421), (18.40, -27.471)), ("sw", (19.577, -27.446), (19.477, -27.446), (20.377, -27.446)), ("pocket", 18.527, 19.427, -27.371)]
    o["note"] = "BOTH OPEN: FAILS (axis). ONE open: PASSES. Privacy rests on the closers + interlock, not geometry."
    o["extra"] = ["suite door 0.85 + dressing door 0.90, both self-closing; storage 0.20 deep", "pinch 0.80 m (was 0.702)"]
    return o

def scenarios(o):
    V = vps(o["cx"]); T = targets(); res = {}
    base = modelled(o)
    shut_suite = unary_union([base, box(17.45, -28.421, 17.55, -27.471)])
    shut_dress = unary_union([base, DRESS_OPEN])
    for k, s in (("both_open", base), ("suite_open_dressing_shut", shut_dress), ("dressing_open_suite_shut", shut_suite), ("both_shut", unary_union([shut_suite, shut_dress]))):
        c = check(s, V, T); res[k] = dict(viewpoints=len(V), seeing=len(c))
    return res, base, V

if __name__ == "__main__":
    o = op2a(); res, solid, V = scenarios(o)
    cnt = check(solid, V, targets()); R, bed, h1 = route_len(o, solid)
    ok, far = draw("2a", o, solid, R, cnt, V, bed, h1)
    res["route_m"] = R["length"]; res["narrowest_mm"] = round(R["widest_m"] * 1000)
    (OUT / "results-2a.json").write_text(json.dumps(res, indent=1)); print(res)
