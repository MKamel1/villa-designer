"""Basement daylight options for the lounge and kitchen (G1 row CL2), cheapest first, with the effect on the mean daylight factor.

    PYTHONPATH=src python tests/design/daylight_options.py

Base figures are the validated Radiance run on D1 (out/villa/daylight/summary-r12.json, 'D1', white finishes, CIE overcast).
Everything that is not that run is an ESTIMATE and is labelled so:
  scale   : DF scales with glazed area for the same view of sky (Metric Handbook eq. 4: DF = T W theta M / [A (1 - R^2)]);
  analog  : the ratio between two measured runs of the project's mitigation study (summary.json, P3/P4 options) applied to D1.
No Radiance run of the changed D1 was made (Radiance is not installed on this machine).
"""
from __future__ import annotations

import json
from pathlib import Path

SUMMARY = Path(r"C:\Users\mmbka\arch-pipeline\out\villa\daylight")


def _rooms(name):
    d = json.loads((SUMMARY / name).read_text(encoding="utf-8"))
    return d["options"]


def group_df(df, area, members):
    num = sum(df[r] * area[r] for r in members)
    return num / sum(area[r] for r in members)


def table(areas):
    r12 = _rooms("summary-r12.json")["D1"]["rooms"]
    mit = _rooms("summary.json")
    df = {k: v["df"] for k, v in r12.items()}
    out = []
    lounge_g, kitchen_g = ("lounge", "lounge-nook", "family"), ("kitchen", "kitchen-island")
    base_l, base_k = group_df(df, areas, lounge_g), group_df(df, areas, kitchen_g)
    out.append(dict(option="0 as simulated (D1, white finishes)", kind="measured", lounge=round(base_l, 2),
                    kitchen=round(base_k, 2), cost="-", note="the L1 CL2 rows: lounge 0.59 %, kitchen 0.33 %"))
    # 1 widen the lounge street door to the whole column-free run (3.41 -> 3.71 m); the nook shares the opening
    k = 3.71 / 3.41
    d1 = dict(df, lounge=df["lounge"] * k, **{"lounge-nook": df["lounge-nook"] * k})
    out.append(dict(option="1 widen lounge street glazing 3.41 -> 3.71 m (IMPLEMENTED)", kind="estimate: scale by glazed area",
                    lounge=round(group_df(d1, areas, lounge_g), 2), kitchen=round(base_k, 2),
                    cost="lowest: a wider door leaf, no structure", note="the run is column-free up to 3.81 m; 50 mm reveal kept"))
    # 2 kitchen glazing in its own walls: none faces a garden
    out.append(dict(option="2 glazing in kitchen walls facing a garden", kind="not possible",
                    lounge=round(base_l, 2), kitchen=round(base_k, 2), cost="-",
                    note="no kitchen wall faces a garden: south is the dirty kitchen (hatch 1.3 m, sliding door 1.2 m, "
                         "column at 11.2), north is the party core, east is the open dining"))
    # 3 glass partition between kitchen and dirty kitchen: measured analog
    p3, p4 = mit["P3-glass"]["rooms"]["kitchen"]["df"] / mit["P3"]["rooms"]["kitchen"]["df"], \
        mit["P4-glass"]["rooms"]["kitchen"]["df"] / mit["P4"]["rooms"]["kitchen"]["df"]
    out.append(dict(option="3 glass partition kitchen / dirty kitchen", kind="analog: measured P3 and P4 glass-partition ratios",
                    lounge=round(base_l, 2), kitchen="%.2f-%.2f" % (base_k * min(p3, p4), base_k * max(p3, p4)),
                    cost="medium; mostly not buildable: the 3.7 m wall is the hatch, the sliding door and a column",
                    note="ratios %.2f (P4) to %.2f (P3); the pocket door is already open in the simulation" % (min(p3, p4), max(p3, p4))))
    # 4 rooflight in the GF terrace slab over the loggia
    out.append(dict(option="4 rooflight in the GF terrace slab over the loggia", kind="estimate: blocked sky",
                    lounge=round(base_l, 2), kitchen=round(base_k, 2), cost="medium",
                    note="the apartment's own terrace (villa_env apartment-above-front, z 3.0-4.1 m) sits directly above "
                         "the GF terrace: a rooflight would look at its underside, no gain; needs the apartment's slab"))
    # 5 slot (grating in ramp / deck / roof) along the east face: measured analog
    lp3 = mit["P3-slot"]["rooms"]["lounge"]["df"] / mit["P3"]["rooms"]["lounge"]["df"]
    lp4 = mit["P4-slot"]["rooms"]["lounge"]["df"] / mit["P4"]["rooms"]["lounge"]["df"]
    kp3 = mit["P3-slot"]["rooms"]["kitchen"]["df"] / mit["P3"]["rooms"]["kitchen"]["df"]
    kp4 = mit["P4-slot"]["rooms"]["kitchen"]["df"] / mit["P4"]["rooms"]["kitchen"]["df"]
    out.append(dict(option="5 0.9 m grated slot along the east face (the garden / terrace above)",
                    kind="analog: measured P3 and P4 slot ratios",
                    lounge="%.2f-%.2f" % (base_l * min(lp3, lp4), base_l * max(lp3, lp4)),
                    kitchen="%.2f-%.2f" % (base_k * min(kp3, kp4), base_k * max(kp3, kp4)),
                    cost="high: the extension rooms (cinema, store, WC, dirty kitchen) lose 0.9 m of depth, a drive-over "
                         "grating in ramp and deck, new glazed wall on the east face; a light well in effect (client: shade)",
                    note="not implemented: needs client sign-off; the cinema stays where it is (G1)"))
    return out


if __name__ == "__main__":
    from archpipe.model import load
    areas = {e.id[5:]: e.params["net_area_m2"] for e in load("D1") if e.kind == "room"}
    for row in table(areas):
        print("%-72s lounge %-10s kitchen %-10s [%s]" % (row["option"], row["lounge"], row["kitchen"], row["kind"]))
        print("    cost: %s | %s" % (row["cost"], row["note"]))
