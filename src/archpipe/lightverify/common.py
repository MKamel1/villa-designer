"""LV: shared result plumbing. A layer returns a LayerResult: CheckResults plus a per-room status used by the report."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import CheckResult

LANE = "LV"


@dataclass
class LayerResult:
    layer: str
    results: list = field(default_factory=list)
    rooms: dict = field(default_factory=dict)     # room -> "pass" | "fail" | "not_evaluated"
    table: list = field(default_factory=list)     # rows for the report
    notes: list = field(default_factory=list)

    def room_status(self, room: str) -> str:
        return self.rooms.get(room, "not_evaluated")

    def mark(self, room: str, status: str):
        """Worst status wins: fail > not_evaluated > pass."""
        order = {"pass": 0, "not_evaluated": 1, "fail": 2}
        cur = self.rooms.get(room)
        if cur is None or order[status] > order[cur]:
            self.rooms[room] = status


def check(criterion, status, subject, sources, **kw) -> CheckResult:
    return CheckResult(criterion, LANE, status, subject, source_ids=tuple(sources), **kw)
