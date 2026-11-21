"""LV: an independent LM-63 reader and flux integrator.

Deliberately shares no code with `archpipe.photometry`: it parses the text itself and integrates by resampling the
candela table to a 0.1 degree grid (linear in gamma, nearest-plane-pair linear in C) and summing I sin(gamma) dgamma dC.
Only photometric type C (vertical axis) is supported; anything else raises, never guesses.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass
class IesData:
    lamps: int
    lamp_lumens: float          # per lamp; -1 = absolute photometry
    multiplier: float
    ptype: int
    units: int
    opening: tuple              # width, length, height as written
    input_watts: float
    gamma: list                 # vertical angles
    cang: list                  # horizontal angles as written
    cd: list                    # cd[iC][iGamma], multiplier applied
    header: dict
    text_cct: float | None = None


def parse(text: str) -> IesData:
    lines = text.replace("\r", "").split("\n")
    header = {}
    i = 0
    for i, l in enumerate(lines):
        if l.upper().startswith("TILT"):
            break
        m = re.match(r"\[(\w+)\]\s*(.*)", l)
        if m:
            header[m.group(1).upper()] = (header.get(m.group(1).upper(), "") + " " + m.group(2)).strip()
    else:
        raise ValueError("no TILT line")
    if "NONE" not in lines[i].upper():
        raise ValueError("TILT other than NONE not supported")
    nums = [float(t) for t in re.split(r"[\s,]+", "\n".join(lines[i + 1:]).strip()) if t]
    lamps, lum, mult, nv, nh, ptype, units = nums[0], nums[1], nums[2], int(nums[3]), int(nums[4]), int(nums[5]), int(nums[6])
    w, l_, h = nums[7:10]
    # nums[10], nums[11] ballast factor / future use, nums[12] input watts
    watts = nums[12]
    p = 13
    gamma = nums[p:p + nv]
    p += nv
    cang = nums[p:p + nh]
    p += nh
    body = nums[p:]
    if len(body) != nv * nh:
        raise ValueError("candela table has %d values, expected %d" % (len(body), nv * nh))
    cd = [[v * mult for v in body[k * nv:(k + 1) * nv]] for k in range(nh)]
    cct = None
    m = re.search(r"CCT\s*(?:\w+/)?(\d{4})", " ".join(header.values()))
    if m:
        cct = float(m.group(1))
    return IesData(int(lamps), lum, mult, ptype, units, (w, l_, h), watts, gamma, cang, cd, header, cct)


def _full_planes(d: IesData):
    """Expand to explicit planes over C = 0..360 using the symmetry implied by the horizontal angle range."""
    c, cd = list(d.cang), d.cd
    if len(c) == 1:
        return [0.0, 360.0], [cd[0], cd[0]]
    lo, hi = c[0], c[-1]
    if lo == 0 and hi == 90:                        # quadrant symmetry
        pl = {a: v for a, v in zip(c, cd)}
        out = dict(pl)
        for a, v in pl.items():
            out[180 - a] = v
            out[180 + a] = v
            out[360 - a] = v
        keys = sorted(out)
    elif lo == 0 and hi == 180:                     # bilateral about the 0-180 plane
        out = {a: v for a, v in zip(c, cd)}
        for a, v in zip(c, cd):
            out[360 - a] = v
        keys = sorted(out)
    elif lo == 0 and hi == 360:
        out = {a: v for a, v in zip(c, cd)}
        keys = sorted(out)
    elif lo == 90 and hi == 270:                    # symmetric about 90-270
        out = {a: v for a, v in zip(c, cd)}
        for a, v in zip(c, cd):
            out[(180 - a) % 360] = v
        out[0.0] = out.get(0.0, out.get(360.0))
        keys = sorted(out)
        if 360.0 not in out:
            out[360.0] = out[0.0]
            keys = sorted(out)
    else:
        raise ValueError("unsupported horizontal angle range %s..%s" % (lo, hi))
    if keys[0] != 0 or keys[-1] != 360:
        out.setdefault(360.0, out.get(0.0))
        keys = sorted(out)
    return keys, [out[k] for k in keys]


def _interp(xs, ys, x):
    if x <= xs[0] or x >= xs[-1]:
        return ys[0] if x <= xs[0] else ys[-1]
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    t = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + t * (ys[hi] - ys[lo])


def candela(d: IesData, gamma_deg: float, c_deg: float) -> float:
    """Candela at (gamma, C); zero outside the tabulated vertical range."""
    if d.ptype != 1:
        raise ValueError("photometric type %d not supported (type C only)" % d.ptype)
    g0, g1 = d.gamma[0], d.gamma[-1]
    if gamma_deg < g0 - 1e-9 or gamma_deg > g1 + 1e-9:
        return 0.0
    keys, planes = _full_planes(d)
    c = c_deg % 360.0
    k = max(0, min(len(keys) - 2, next(i for i in range(len(keys) - 1) if keys[i + 1] > c) if c < 360 else len(keys) - 2))
    a = _interp(d.gamma, planes[k], gamma_deg)
    b = _interp(d.gamma, planes[k + 1], gamma_deg)
    t = (c - keys[k]) / (keys[k + 1] - keys[k])
    return a + t * (b - a)


def lumens(d: IesData, dg: float = 0.2, dc: float = 2.0) -> float:
    """Total flux = integral of I(gamma, C) sin(gamma) over the sphere (midpoint rule on a dg x dc grid)."""
    ng, nc = int(180 / dg), int(360 / dc)
    tot = 0.0
    for i in range(ng):
        g = (i + 0.5) * dg
        s = math.sin(math.radians(g))
        row = sum(candela(d, g, (j + 0.5) * dc) for j in range(nc))
        tot += row * s
    return tot * math.radians(dg) * math.radians(dc)


def beam_angles(d: IesData, level: float = 0.5):
    """Full beam angle (deg) where I falls to `level` x peak, per C plane (0, 90): twice the half-angle off the peak axis."""
    peak = max(candela(d, g * 0.25, c) for g in range(0, 721) for c in (0.0, 90.0, 180.0, 270.0))
    out = {}
    for c in (0.0, 90.0):
        half = []
        for side in (c, c + 180.0):
            g = 0.0
            while g < 179.9 and candela(d, g, side) >= level * peak:
                g += 0.05
            half.append(g)
        out[int(c)] = sum(half)
    return out, peak


def peak_cd(d: IesData) -> float:
    return max(max(r) for r in d.cd)
