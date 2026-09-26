"""One data file for the daylight viewer and the review: every option's basement, per room and per sensor.

    PYTHONPATH=src python scripts/villa_daylight_summary.py      # out/villa/daylight/summary.json

Sources (all validated runs): daylight factor (villa-df-r10), lux at 9 weather-file hours x 4 heights and the
annual 08:00-18:00 statistics (villa-lux-r8), the eye-level renders (views/). Benchmarks from held cards only.
"""
from __future__ import annotations

import io
import json
import statistics
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_remote import DEFAULT_HOST, _ssh                          # noqa: E402

from archpipe import daylight as D                                    # noqa: E402
from archpipe.concept import villa as V                               # noqa: E402
from archpipe.concept import villa_daylight as VD                     # noqa: E402
from archpipe.concept import villa_options as VO                      # noqa: E402
from archpipe.concept import villa_parking as P                       # noqa: E402

OUT = Path("out/villa/daylight")
DF_JOB, LUX_JOB = OUT / "villa-df-r10", OUT / "villa-lux-r10"
OPTIONS = ["S1", "S5", "P3", "P4", "P5"] + list(VD.VARIANTS)


def pull_annual():
    remote = "$HOME/archpipe/daylight/" + LUX_JOB.name
    res = _ssh(DEFAULT_HOST, f'cd "{remote}" && tar czf - cases/*/annual_stats.json', timeout=300)
    with tarfile.open(fileobj=io.BytesIO(res.stdout), mode="r:gz") as tar:
        tar.extractall(LUX_JOB, filter="data")


def main():
    if not (LUX_JOB / "cases" / "P3" / "annual_stats.json").exists():
        pull_annual()
    lux = json.loads((LUX_JOB / "report.json").read_text(encoding="utf-8"))
    df = json.loads((DF_JOB / "report.json").read_text(encoding="utf-8"))
    views = json.loads((OUT / "views" / "stats.json").read_text(encoding="utf-8"))
    lays = {l["id"]: (l, None) for l in [VO.s1(), VO.s5()] + P.options()}
    lays.update(VD.variant_layouts())
    bench = {k: V._card(k)[0] for k in ("sll-min-adf-bedroom", "sll-min-adf-living", "sll-min-adf-kitchen",
                                        "ies-udi-useful-min", "ies-udi-useful-max", "ies-sda-illuminance",
                                        "ies-sda-area-acceptable")}
    data = {"stamps": lux["stamps"], "heights": lux["heights"], "benchmarks": bench,
            "validation": {"df": df["validation"], "lux_orientation": lux["orientation"], "lux_method": lux["method"]},
            "views": views, "options": {}}
    for opt in OPTIONS:
        lay, var = lays[opt]
        sc_rooms = {r["id"]: r for r in VD.scene(lay, var).rooms}           # the variant's own room outlines
        rect = lambda rid: [f(p[i] for p in sc_rooms[rid]["polygon"]) for f, i in ((min, 0), (min, 1), (max, 0),  # noqa
                                                                                    (max, 1))]
        rooms = {rid: {"name": r["name"], "occ": r["occupancy"], "rect": rect(rid)}
                 for rid, r in lay["rooms"].items() if r["level"] == "B"}
        # daylight factor sensors (0.85 m)
        meta = json.loads((DF_JOB / "cases" / opt / "rooms.json").read_text(encoding="utf-8"))
        vals = [float(v) for v in (DF_JOB / "cases" / opt / "out.txt").read_text().split()]
        pts = [tuple(map(float, l.split()[:3])) for l in (DF_JOB / "cases" / opt / "points.txt").read_text().split("\n")
               if l.strip()]
        dfp = [[round(p[0], 2), round(p[1], 2), round(D.df_percent(*vals[3 * i:3 * i + 3]), 2)]
               for i, p in enumerate(pts) if abs(p[2] - (-3.0 + 0.85)) < 0.01]
        for rid, r in df["results"][opt]["rooms"].items():
            if rid in rooms:
                rooms[rid]["df"] = r["adf"]
        # lux sensors: id, h, x, y + 9 values; annual stats per sensor
        res = lux["results"][opt]
        ann = json.loads((LUX_JOB / "cases" / opt / "annual_stats.json").read_text(encoding="utf-8"))["sensors"]
        sens = []
        for (rid, h, x, y), row, a in zip(res["sensors"], res["lux"], ann):
            sens.append([rid, h, x, y, row, a])
        for rid in rooms:
            for h in lux["heights"]:
                ss = [s for s in sens if s[0] == rid and abs(s[1] - h) < 1e-6]
                if not ss:
                    continue
                key = "%.2f" % h
                rooms[rid].setdefault("lux", {})[key] = [round(statistics.mean(s[4][k] for s in ss))
                                                          for k in range(len(lux["stamps"]))]
                if abs(h - 0.85) < 1e-6:
                    rooms[rid]["sda300"] = round(100 * sum(1 for s in ss if s[5][0] >= 0.5) / len(ss))
                    rooms[rid]["udi_lt100"] = round(100 * statistics.mean(s[5][1] for s in ss))
                    rooms[rid]["udi_useful"] = round(100 * statistics.mean(s[5][2] for s in ss))
                    rooms[rid]["udi_gt2000"] = round(100 * statistics.mean(s[5][3] for s in ss))
                    rooms[rid]["annual_mean_lux"] = round(statistics.mean(s[5][4] for s in ss))
        title = lay["title"] + (" | variant: " + ", ".join("%s=%s" % kv for kv in sorted(var.items())) if var else "")
        data["options"][opt] = {"title": title, "variant": var or {}, "rooms": rooms, "df_points": dfp,
                                "lux_sensors": [[s[1], s[2], s[3]] + s[4] + [round(s[5][0] * 100)] for s in sens]}
    (OUT / "summary.json").write_text(json.dumps(data), encoding="utf-8")
    print(OUT / "summary.json", round((OUT / "summary.json").stat().st_size / 1e6, 2), "MB")
    for opt in OPTIONS:
        rs = data["options"][opt]["rooms"]
        keep = [k for k in ("lounge", "flex", "hall-b", "media", "kitchen", "kitchen-island", "dining", "dining-spine",
                            "living") if k in rs]
        print(opt, " | ".join("%s DF %.2f sDA %s%% UDI %s/%s/%s noon-Mar %s lx" % (
            k, rs[k].get("df", 0), rs[k].get("sda300"), rs[k].get("udi_lt100"), rs[k].get("udi_useful"),
            rs[k].get("udi_gt2000"), rs[k]["lux"]["0.85"][1] if "lux" in rs[k] else "-") for k in keep))


if __name__ == "__main__":
    main()
