"""Radiance total-light job for arbitrary polygon rooms (inter-reflection included).

`archpipe.radiance` handles one axis-aligned rectangle; this module handles any
planar polygon (convex or not) with per-surface-class reflectances, any sensor
list (task plane grid, cube-face grid, vertical eye sensors), and a separate
octree per control zone so a scene (dim level per zone) is a linear
recombination of per-zone results. Light transport is linear in source power,
so scene = sum(dim_z * E_z) is exact up to Monte-Carlo noise; dimming is
assumed to scale photometric output linearly (stated in every report).

Execution is split: this module only WRITES the job (stdlib; scene files,
points, run.sh) and PARSES the output. `execute()` runs the script locally
where Radiance is installed or over ssh on the compute node.
"""
from __future__ import annotations

import io
import json
import math
import os
import shlex
import shutil
import subprocess
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

from ..radiance import _lux, parse_rtrace_output
from .direct import Placement, aim_angles
from .geometry import Point, ccw, outward_edges

DEFAULT_HOST = "ai-workstation"
DEFAULT_RADHOME = "~/archpipe/tools/radiance-6.0.1"
DEFAULT_REMOTE_ROOT = "~/archpipe/scratch/L6"


@dataclass(frozen=True)
class Room:
    polygon: tuple[Point, ...]           # plan outline, metres
    floor_z: float = 0.0
    ceiling_z: float = 2.7
    rho_floor: float = 0.25
    rho_wall: float = 0.6
    rho_ceiling: float = 0.8
    boxes: tuple = ()                    # obstacles: (x0, y0, z0, x1, y1, z1, rho)


@dataclass(frozen=True)
class Sensor:
    x: float
    y: float
    z: float
    nx: float = 0.0
    ny: float = 0.0
    nz: float = 1.0


@dataclass
class RadParams:
    ab: int = 6
    ad: int = 2048
    ar: int = 32
    aa: float = 0.1
    as_: int = 1024
    lw: float = 1e-6
    lr: int = 12
    workers: int = 8
    ab_extra: tuple[int, ...] = ()       # extra bounce counts (convergence: e.g. 2*ab)


def _plastic(name: str, rho: float) -> str:
    r = max(0.0, min(0.99, rho))
    return f"void plastic {name}\n0\n0\n5 {r:.4f} {r:.4f} {r:.4f} 0 0\n"


def _poly(material: str, name: str, pts: list[tuple[float, float, float]]) -> str:
    coords = "\n".join(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}" for p in pts)
    return f"{material} polygon {name}\n0\n0\n{3 * len(pts)}\n{coords}\n"


def room_scene_text(room: Room) -> str:
    """Floor, ceiling, one quad per wall edge (any polygon), optional boxes."""
    poly = ccw(list(room.polygon))
    z0, z1 = room.floor_z, room.ceiling_z
    out = [_plastic("m_floor", room.rho_floor), _plastic("m_wall", room.rho_wall),
           _plastic("m_ceil", room.rho_ceiling)]
    out.append(_poly("m_floor", "floor", [(x, y, z0) for x, y in poly]))
    out.append(_poly("m_ceil", "ceiling", [(x, y, z1) for x, y in reversed(poly)]))
    for i, (a, b, _n) in enumerate(outward_edges(poly)):
        out.append(_poly("m_wall", f"wall{i}", [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]))
    for k, (bx0, by0, bz0, bx1, by1, bz1, rho) in enumerate(room.boxes):
        out.append(_plastic(f"m_box{k}", rho))
        faces = [
            [(bx0, by0, bz0), (bx1, by0, bz0), (bx1, by1, bz0), (bx0, by1, bz0)],
            [(bx0, by0, bz1), (bx0, by1, bz1), (bx1, by1, bz1), (bx1, by0, bz1)],
            [(bx0, by0, bz0), (bx0, by0, bz1), (bx1, by0, bz1), (bx1, by0, bz0)],
            [(bx1, by0, bz0), (bx1, by0, bz1), (bx1, by1, bz1), (bx1, by1, bz0)],
            [(bx1, by1, bz0), (bx1, by1, bz1), (bx0, by1, bz1), (bx0, by1, bz0)],
            [(bx0, by1, bz0), (bx0, by1, bz1), (bx0, by0, bz1), (bx0, by0, bz0)],
        ]
        for j, f in enumerate(faces):
            out.append(_poly(f"m_box{k}", f"box{k}_{j}", f))
    return "".join(out)


def xform_chain(p: Placement) -> list[str]:
    """xform args that place a ies2rad luminaire: spin about local z, tilt onto aim, azimuth, translate.
    Mirrors `Placement.rotation()` (spin, then ry(-tilt), then rz(azimuth))."""
    tilt, az = aim_angles(p.aim)
    args = []
    if abs(p.spin_deg) > 1e-12:
        args += ["-rz", f"{p.spin_deg:.6f}"]
    if tilt > 1e-9:
        args += ["-ry", f"{-tilt:.6f}", "-rz", f"{az:.6f}"]
    args += ["-t", f"{p.position[0]:.6f}", f"{p.position[1]:.6f}", f"{p.position[2]:.6f}"]
    return args


@dataclass
class RadJob:
    name: str
    room: Room | None
    placements: list[Placement]
    sensors: list[Sensor]
    params: RadParams = field(default_factory=RadParams)

    def zones(self) -> list[str]:
        return sorted({p.zone for p in self.placements})

    def ab_levels(self) -> list[int]:
        return sorted({0, self.params.ab, *self.params.ab_extra})

    # ------------------------------------------------------------- writing
    def prepare(self, workdir: Path) -> Path:
        wd = Path(workdir)
        wd.mkdir(parents=True, exist_ok=True)
        (wd / "points.txt").write_text(
            "".join(f"{s.x:.6f} {s.y:.6f} {s.z:.6f} {s.nx:.6f} {s.ny:.6f} {s.nz:.6f}\n" for s in self.sensors),
            encoding="utf-8", newline="\n")
        shell = room_scene_text(self.room) if self.room else ""
        (wd / "room.rad").write_text(shell or "# no room surfaces (free space)\n", encoding="utf-8", newline="\n")
        lines = ["set -e", 'cd "$(dirname "$0")"',
                 'export RAYPATH=".:$RADHOME/lib"', 'export PATH="$RADHOME/bin:$PATH"']
        ies_done: dict[str, str] = {}
        fx_by_zone: dict[str, list[str]] = {}
        for k, p in enumerate(self.placements):
            key = p.photometry.name + "|" + str(p.meta.get("ies_path") or p.photometry.source or "")
            if key not in ies_done:
                iesname = f"ies{len(ies_done):02d}"
                text = p.meta.get("ies_text")
                if text is None:
                    src = p.meta.get("ies_path") or p.photometry.source
                    if src is None:
                        raise ValueError(f"{p.id}: no ies_text/ies_path/source to hand to Radiance")
                    text = Path(src).read_text(encoding="utf-8", errors="replace")
                (wd / f"{iesname}.ies").write_text(text, encoding="utf-8", newline="\n")
                ies_done[key] = iesname
            iesname = ies_done[key]
            mult = p.dim
            tag = f"fx{k:03d}"
            lines.append(f"ies2rad -dm -t default -m {mult:.6f} -o {tag} {iesname}.ies > {tag}.log 2>&1")
            lines.append("xform " + " ".join(shlex.quote(a) for a in xform_chain(p)) + f" {tag}.rad > {tag}_p.rad")
            fx_by_zone.setdefault(p.zone, []).append(f"{tag}_p.rad")
        P = self.params
        for z in self.zones():
            files = " ".join(["room.rad"] + fx_by_zone[z])
            lines.append(f"oconv {files} > scene_{z}.oct")
            for ab in self.ab_levels():
                flags = (f"-I+ -h- -dt 0 -ab {ab} -ad {P.ad} -ar {P.ar} -aa {P.aa} -as {P.as_} "
                         f"-lw {P.lw:g} -lr {P.lr} -n {P.workers} -faa")
                lines.append(f"rtrace {flags} scene_{z}.oct < points.txt > out_{z}_ab{ab}.txt")
        lines.append("echo DONE > done.flag")
        (wd / "run.sh").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        meta = {"name": self.name, "zones": self.zones(), "ab_levels": self.ab_levels(),
                "n_sensors": len(self.sensors), "params": self.params.__dict__,
                "radiance_flags": "rtrace -I+ -h- -dt 0 (+ -ab/-ad/-ar/-aa/-as/-lw/-lr)"}
        (wd / "job.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        return wd / "run.sh"

    # ------------------------------------------------------------ parsing
    def parse(self, workdir: Path) -> dict[str, dict[int, list[float]]]:
        """zone -> ab -> lux per sensor (initial, MF = 1)."""
        wd = Path(workdir)
        res: dict[str, dict[int, list[float]]] = {}
        for z in self.zones():
            res[z] = {}
            for ab in self.ab_levels():
                rgb = parse_rtrace_output((wd / f"out_{z}_ab{ab}.txt").read_text(), len(self.sensors))
                res[z][ab] = [_lux(*c) for c in rgb]
        return res


# ---------------------------------------------------------------- execution

def have_local_radiance() -> bool:
    return shutil.which("rtrace") is not None and shutil.which("bash") is not None


def execute(job: RadJob, workdir: Path, *, host: str | None = None, radhome: str | None = None,
            remote_root: str = DEFAULT_REMOTE_ROOT, timeout: int = 1800) -> dict[str, dict[int, list[float]]]:
    """Write the job, run it, parse it. Local when Radiance is on PATH and host is None; else ssh."""
    wd = Path(workdir)
    job.prepare(wd)
    if host is None and have_local_radiance():
        env = dict(os.environ, RADHOME=radhome or str(Path(shutil.which("rtrace")).parent.parent))
        subprocess.run(["bash", str(wd / "run.sh")], check=True, env=env, timeout=timeout)
        return job.parse(wd)
    host = host or os.environ.get("ARCHPIPE_L6_SSH") or DEFAULT_HOST
    radhome = radhome or DEFAULT_RADHOME
    rdir = f"{remote_root}/{job.name}"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for f in wd.iterdir():
            if f.is_file() and not f.name.startswith("out_"):
                tf.add(f, arcname=f.name)
    cmd = (f"rm -rf {rdir} && mkdir -p {rdir} && tar xf - -C {rdir} && cd {rdir} && "
           f"RADHOME={radhome} bash run.sh")
    # '~' must be expanded by the remote shell: keep it unquoted.
    r = subprocess.run(["ssh", host, cmd], input=buf.getvalue(), capture_output=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f"remote Radiance run failed ({r.returncode}): {r.stderr.decode(errors='replace')[-1500:]}")
    got = subprocess.run(["ssh", host, f"tar cf - -C {rdir} $(cd {rdir} && ls out_*.txt *.log done.flag 2>/dev/null)"],
                         capture_output=True, timeout=300, check=True)
    with tarfile.open(fileobj=io.BytesIO(got.stdout), mode="r") as tf:
        tf.extractall(wd, filter="data")
    return job.parse(wd)


def total_lux(results: dict[str, dict[int, list[float]]], dims: dict[str, float] | None = None, *,
              ab: int, mf: float = 1.0) -> list[float]:
    """Combine per-zone results into a scene: sum_z dims[z] * E_z (dims default 1.0).
    NB: per-zone octrees already include each placement's own `dim`; `dims` is the extra scene factor."""
    zones = list(results)
    n = len(next(iter(results.values()))[ab])
    out = [0.0] * n
    for z in zones:
        f = 1.0 if dims is None else dims.get(z, 1.0)
        for i, v in enumerate(results[z][ab]):
            out[i] += f * v
    return [v * mf for v in out]
