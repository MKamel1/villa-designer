"""Animated door leaves for the walkthrough: state series, leaf footprint and camera clearance.

A leaf's state s is 1 when open (the pose the scene is built in by flythrough.open_interior_doors) and 0 when closed (as authored). The leaf turns about its
hinge by signed_open_deg * s, so the same record drives the audit (flyaudit.geometry.Geometry.animate), the admission here and Blender (blender/walkthrough.py).
Records: element, leaf_id, hinge [x, y], signed_open_deg, closed_faces; schedule: close_start, close_end, open_start, open_end (frame indices).
"""
from __future__ import annotations
import math
import numpy as np


def smoothstep(u):
    u = np.clip(u, 0., 1.)
    return u*u*(3.-2.*u)


def state_series(sched, n):
    """Leaf state per frame: 1, eased down to 0 over close_start..close_end, 0 until open_start, eased back to 1 over open_start..open_end."""
    f = np.arange(n, dtype=float)
    down = smoothstep((f-sched['close_start'])/max(1, sched['close_end']-sched['close_start']))
    up = smoothstep((f-sched['open_start'])/max(1, sched['open_end']-sched['open_start']))
    return 1.-down+up*down


def leaf_rect(rec):
    """Closed leaf footprint: (centre-line start u0 along the leaf from the hinge, length, thickness, unit direction hinge->free end, normal) in plan."""
    pts = np.array([v for face in rec['closed_faces'] for v in face], float); lo, hi = pts.min(0), pts.max(0)
    hinge = np.asarray(rec['hinge'], float); along_x = (hi[0]-lo[0]) >= (hi[1]-lo[1])
    length = (hi[0]-lo[0]) if along_x else (hi[1]-lo[1]); width = (hi[1]-lo[1]) if along_x else (hi[0]-lo[0])
    centre = (lo[:2]+hi[:2])/2; free = np.array([hi[0] if abs(hinge[0]-lo[0]) < abs(hinge[0]-hi[0]) else lo[0], centre[1]]) if along_x else np.array([centre[0], hi[1] if abs(hinge[1]-lo[1]) < abs(hinge[1]-hi[1]) else lo[1]])
    u = free-hinge; u /= np.linalg.norm(u)
    return length, width, u, np.array([-u[1], u[0]])


def leaf_polygon(rec, s, grow=0.):
    """Plan polygon (4 corners) of the leaf at state s (grown by `grow` metres all round)."""
    length, width, u, nrm = leaf_rect(rec); h = np.asarray(rec['hinge'], float); psi = math.radians(rec['signed_open_deg'])*s
    c, sn = math.cos(psi), math.sin(psi); R = np.array([[c, -sn], [sn, c]]); u2, n2 = R@u, R@nrm
    a, b = length+grow, width/2+grow
    return np.array([h-u2*grow+n2*b, h+u2*a+n2*b, h+u2*a-n2*b, h-u2*grow-n2*b])


def distance_to_leaf(rec, s, xy):
    """Distance (m) from a plan point to the leaf rectangle at state s (0 inside)."""
    length, width, u, nrm = leaf_rect(rec); h = np.asarray(rec['hinge'], float); psi = math.radians(rec['signed_open_deg'])*s
    c, sn = math.cos(psi), math.sin(psi); u2 = np.array([c*u[0]-sn*u[1], sn*u[0]+c*u[1]]); n2 = np.array([-u2[1], u2[0]])
    d = np.asarray(xy, float)-h; a, b = d@u2, d@n2
    return math.hypot(max(-a, 0., a-length), max(abs(b)-width/2, 0.))


def attach(path, records, schedules):
    """Write path['door_anim'] and the per-frame leaf state frame['doors'] (only the frames where a leaf is not fully open). Mutates and returns path."""
    n = len(path['frames']); anim = []
    for rec in records:
        sch = schedules[rec['element']]; s = state_series(sch, n)
        anim.append(dict(rec, schedule=sch, note=rec.get('note', '')))
        for i, v in enumerate(s):
            if v < 1.-1e-9:
                path['frames'][i].setdefault('doors', {})[rec['element']] = round(float(v), 5)
    path['door_anim'] = anim
    return path


def clearance_findings(path, clearance_m, margin_frames=0):
    """Frames where the camera is nearer than `clearance_m` to an animated leaf at that frame's state (a leaf that is fully open is judged by the standing admission)."""
    out = []
    for rec in path.get('door_anim', []):
        el = rec['element']
        for f in path['frames']:
            s = f.get('doors', {}).get(el, 1.)
            if s >= 1.-1e-9:
                continue
            d = distance_to_leaf(rec, s, f['camera']['position'][:2])
            if d < clearance_m:
                out.append((f['index'], el, round(float(d), 3)))
    return out


def pivot_transform(rec, state):
    """Object transform that turns a leaf built in its OPEN pose to `state` about the hinge: (rotation about z in radians, (x, y) translation).
    A vertex v goes to R v + t. state 1 is the identity, state 0 maps the open leaf back onto the closed leaf as authored (Blender's pose_door uses this)."""
    psi = -math.radians(rec['signed_open_deg'])*(1.-state); c, s = math.cos(psi), math.sin(psi); hx, hy = rec['hinge']
    return psi, (hx-(hx*c-hy*s), hy-(hx*s+hy*c))
