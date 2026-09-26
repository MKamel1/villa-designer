"""Per-sensor annual daylight statistics from an rmtxop ascii lux matrix (rows = sensors, columns = hours).

Runs on the compute node with plain Python 3 (no numpy there), streaming one sensor row at a time:

    python3 daylight_annual_stats.py lux_annual.txt > stats.json

Per sensor: DA300 (share of hours >= 300 lux), UDI shares (< 100, 100-2000, > 2000 lux), mean lux. Thresholds are
the IES Lighting Handbook 10th ed. p. 14.47 values (cards ies-sda-illuminance, ies-udi-useful-min/-max).
"""
import json
import sys

DA, UDI_LO, UDI_HI = 300.0, 100.0, 2000.0


def stats(path):
    out = []
    with open(path) as fh:
        header = True
        for line in fh:
            if header:
                if not line.strip():
                    header = False
                continue
            v = [float(x) for x in line.split()]
            if not v:
                continue
            n = float(len(v))
            out.append([round(sum(1 for x in v if x >= DA) / n, 4),
                        round(sum(1 for x in v if x < UDI_LO) / n, 4),
                        round(sum(1 for x in v if UDI_LO <= x <= UDI_HI) / n, 4),
                        round(sum(1 for x in v if x > UDI_HI) / n, 4),
                        round(sum(v) / n, 1)])
    return {"columns": ["da300", "udi_lt100", "udi_100_2000", "udi_gt2000", "mean_lux"], "sensors": out}


if __name__ == "__main__":
    json.dump(stats(sys.argv[1]), sys.stdout)
