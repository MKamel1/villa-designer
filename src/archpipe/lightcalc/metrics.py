"""Grid statistics: Em, Emin, Emax, U0, max:avg, avg:min (IES 33.3.4 / EN 12464-1 vocabulary)."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class GridStats:
    n: int
    em: float
    emin: float
    emax: float
    u0: float          # Emin / Em
    max_avg: float     # Emax / Em
    avg_min: float     # Em / Emin (inf when Emin == 0)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["avg_min"] = None if d["avg_min"] == float("inf") else d["avg_min"]
        return d


def grid_stats(values: list[float]) -> GridStats:
    if not values:
        raise ValueError("empty grid")
    em = sum(values) / len(values)
    lo, hi = min(values), max(values)
    return GridStats(
        n=len(values), em=em, emin=lo, emax=hi,
        u0=(lo / em) if em > 0 else 0.0,
        max_avg=(hi / em) if em > 0 else 0.0,
        avg_min=(em / lo) if lo > 0 else float("inf"),
    )
