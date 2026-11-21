"""L6b: independent floor-illuminance check for box-shaped clusters: patch radiosity (8 x 8 patches per face, exact
point-to-point form factors, no occluders) driven by the analytic direct light of the same placements.

It shares no code with Radiance, and it is the check that explained the parents' dressing room: the closed-form lumen
method (uniform inter-reflection) says 615 lx there, but in a tall narrow room (room index 0.43) the floor sees mostly
walls and gets 377 lx from this solver, which Radiance reproduces (378 lx). Use it where the lumen method disagrees.
"""
from __future__ import annotations

import numpy as np

from .direct import direct_illuminance


def floor_mean_lux(room, placements, mf: float = 1.0, n: int = 8) -> float:
    """Mean maintained illuminance on the floor of the bounding box of `room` (a Room), `placements` at their dims."""
    xs, ys = [p[0] for p in room.polygon], [p[1] for p in room.polygon]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), room.floor_z, room.ceiling_z
    faces = [((x0, y0, z0), (x1 - x0, 0, 0), (0, y1 - y0, 0), (0, 0, 1), room.rho_floor),
             ((x0, y0, z1), (x1 - x0, 0, 0), (0, y1 - y0, 0), (0, 0, -1), room.rho_ceiling),
             ((x0, y0, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0), (0, 1, 0), room.rho_wall),
             ((x0, y1, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0), (0, -1, 0), room.rho_wall),
             ((x0, y0, z0), (0, y1 - y0, 0), (0, 0, z1 - z0), (1, 0, 0), room.rho_wall),
             ((x1, y0, z0), (0, y1 - y0, 0), (0, 0, z1 - z0), (-1, 0, 0), room.rho_wall)]
    C, N, A, R = [], [], [], []
    for P, U, V, nrm, rho in faces:
        for i in range(n):
            for j in range(n):
                C.append(np.array(P) + (i + .5) / n * np.array(U) + (j + .5) / n * np.array(V))
                N.append(nrm)
                A.append(np.linalg.norm(np.cross(U, V)) / n / n)
                R.append(rho)
    C, N, A, R = np.array(C), np.array(N, float), np.array(A), np.array(R)
    Ed = np.array([direct_illuminance(placements, tuple(c + 1e-3 * m), tuple(m)) for c, m in zip(C, N)])
    D = C[None] - C[:, None]
    r2 = (D ** 2).sum(-1) + 1e-12
    r = np.sqrt(r2)
    F = np.clip((D * N[:, None]).sum(-1) / r, 0, None) * np.clip(-(D * N[None]).sum(-1) / r, 0, None) * A[None] / (np.pi * r2)
    np.fill_diagonal(F, 0)
    B = np.linalg.solve(np.eye(len(C)) - R[:, None] * F, R * Ed)
    E = Ed + F @ B
    return float(mf * E[: n * n].mean())
