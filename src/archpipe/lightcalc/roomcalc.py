"""Room calculation: task planes on polygon rooms, total light (Radiance), scenes, LA1-LA3 checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..contracts import CheckResult
from . import checks
from .direct import Placement
from .geometry import Point, grid_in_polygon
from .metrics import GridStats, grid_stats
from .radjob import RadJob, RadParams, Room, Sensor, execute, total_lux


@dataclass(frozen=True)
class Scene:
    """A lighting scene: dim level (0..1) per control zone. Zones not named are off (0), so a scene
    must list every zone it wants lit; `Scene.full(zones)` is everything at 100 %."""
    name: str
    levels: dict

    @staticmethod
    def full(zones, name="full") -> "Scene":
        return Scene(name, {z: 1.0 for z in zones})

    def level(self, zone: str) -> float:
        v = float(self.levels.get(zone, 0.0))
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"scene {self.name}: level {v} for zone {zone} outside 0..1")
        return v


@dataclass(frozen=True)
class TaskPlane:
    id: str
    polygon: tuple[Point, ...]
    z: float
    target_lux: float
    gauge: str = "average"          # 'average' | 'minimum'
    spacing: float | None = None    # None -> EN 12464-1 cell size
    border: float = 0.0
    u0_min: float | None = None


@dataclass
class RoomCalc:
    name: str
    room: Room
    placements: list[Placement]
    planes: list[TaskPlane]
    params: RadParams = field(default_factory=RadParams)
    mf: float = 0.8                  # maintenance factor (stated; applied once after the calculation)
    results: dict = field(default_factory=dict)
    _slices: dict = field(default_factory=dict)
    _grid_info: dict = field(default_factory=dict)

    def sensors(self) -> list[Sensor]:
        out: list[Sensor] = []
        for pl in self.planes:
            pts, dx, dy = grid_in_polygon(list(pl.polygon), spacing=pl.spacing, border=pl.border)
            self._slices[pl.id] = (len(out), len(out) + len(pts))
            self._grid_info[pl.id] = {"n": len(pts), "dx": dx, "dy": dy, "z": pl.z}
            out += [Sensor(x, y, pl.z) for x, y in pts]
        return out

    def run(self, workdir: Path, host: str | None = None) -> None:
        job = RadJob(self.name, self.room, self.placements, self.sensors(), self.params)
        self.results = execute(job, workdir, host=host)

    def values(self, plane_id: str, scene: Scene, *, ab: int | None = None, direct: bool = False) -> list[float]:
        """Maintained lux on a plane for a scene (ab=0 gives the direct-only component)."""
        a = 0 if direct else (ab if ab is not None else self.params.ab)
        lo, hi = self._slices[plane_id]
        tot = total_lux(self.results, {z: scene.level(z) for z in self.results}, ab=a, mf=self.mf)
        return tot[lo:hi]

    def stats(self, plane_id: str, scene: Scene, **kw) -> GridStats:
        return grid_stats(self.values(plane_id, scene, **kw))

    def convergence(self, plane_id: str, scene: Scene) -> float | None:
        """Em(ab) / Em(2 ab) - 1 where a doubled-bounce run exists (None otherwise)."""
        extra = [a for a in self.params.ab_extra if a > self.params.ab]
        if not extra:
            return None
        a = self.stats(plane_id, scene).em
        b = self.stats(plane_id, scene, ab=max(extra)).em
        return a / b - 1.0

    def checks(self, scene: Scene) -> list[CheckResult]:
        out: list[CheckResult] = []
        for pl in self.planes:
            st = self.stats(pl.id, scene)
            subj = f"{self.name}/{pl.id}/{scene.name}"
            out.append(checks.check_la1(subj, st.em, pl.target_lux, gauge=pl.gauge, emin=st.emin))
            out.append(checks.check_la2(subj, st.em, pl.target_lux))
            out += checks.check_la3(subj, st, u0_min=pl.u0_min)
        return out

    def report(self, scene: Scene) -> dict:
        rep = {"room": self.name, "scene": scene.name, "levels": dict(scene.levels), "maintenance_factor": self.mf,
               "radiance": {"ab": self.params.ab, "ab_extra": list(self.params.ab_extra)},
               "reflectances": {"floor": self.room.rho_floor, "wall": self.room.rho_wall,
                                "ceiling": self.room.rho_ceiling},
               "planes": {}}
        for pl in self.planes:
            st = self.stats(pl.id, scene)
            d = self.stats(pl.id, scene, direct=True)
            rep["planes"][pl.id] = {"target_lux": pl.target_lux, "z": pl.z, "grid": self._grid_info[pl.id],
                                    "total": st.to_dict(), "direct_only": d.to_dict(),
                                    "convergence_ab_vs_2ab": self.convergence(pl.id, scene)}
        return rep
