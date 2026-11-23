"""Plant generator: a branching skeleton grown to the species' habit, then leaf cards on it. Pure numpy, no Blender.

generate(slug, seed, height_m, spread_m, state, lod) -> Plant. Deterministic: the same arguments give identical arrays.
Axes: +z up, base at the origin on the ground; climbers grow in the x-z plane and face +y (the garden side).

Skeleton rules (what makes it not a sea urchin): every axis is a polyline that bends by random jitter plus a tropism
toward the light (order 0) or toward gravity (outer orders), tapers by the pipe model (a child's radius is a fraction of
its parent's at the node), leaves its parent at a normally-distributed angle on a golden-angle azimuth, and is
pruned/curled back at the habit envelope so the outline is the species' rounded, arching or tiered form."""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import VERSION
from .species import SPECS, sourced_ranges

BANKS = json.loads((Path(__file__).resolve().parents[4] / "knowledge/landscape/foliage/banks.json").read_text())
GOLD = 2.399963   # golden angle, rad
UP = np.array([0.0, 0.0, 1.0])


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else UP.copy()


def rot(v, axis, ang):
    k = unit(axis)
    return v * math.cos(ang) + np.cross(k, v) * math.sin(ang) + k * np.dot(k, v) * (1 - math.cos(ang))


def perp(d):
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    return unit(np.cross(d, a))


def leaf_curve(base, d, length, arch, n=6):
    """Centre line of a leaf card: the blade axis bends downward by `arch` radians in total (gravity droop).
    Shared with the Blender builder so the measured bounding box is the built one. base,d (3,) -> pts (n,3)."""
    side = np.cross(d, UP)
    if np.linalg.norm(side) < 1e-6:
        side = np.array([1.0, 0, 0])
    side = unit(side)
    pts = [np.array(base, float)]
    for i in range(1, n):
        t = (i - 0.5) / (n - 1)
        pts.append(pts[-1] + rot(d, side, -arch * t) * (length / (n - 1)))
    return np.array(pts)


@dataclass
class Plant:
    species: str
    seed: int
    state: str
    height_m: float
    spread_m: float
    label: dict
    branches: list = field(default_factory=list)      # dicts: pts (n,3), radii (n,), kind, order
    leaves: dict = field(default_factory=dict)        # arrays: base,dir,normal (n,3); length,width,arch (n,); bank (list[str]); leaf (n,) idx; tint (n,3)
    flowers: dict = field(default_factory=dict)

    def bbox(self):
        pts = [b["pts"] for b in self.branches]
        if len(self.leaves.get("length", ())):
            L = self.leaves
            tips = np.array([leaf_curve(b, d, l, a)[-1] for b, d, l, a in zip(L["base"], L["dir"], L["length"], L["arch"])])
            pts += [L["base"], tips]
        a = np.concatenate(pts)
        return a.min(0), a.max(0)

    def digest(self):
        import hashlib
        h = hashlib.sha256()
        for b in self.branches:
            h.update(np.round(b["pts"], 5).tobytes())
        for k in ("base", "dir", "length"):
            h.update(np.round(self.leaves[k], 5).tobytes())
        return h.hexdigest()[:16]


# --------------------------------------------------------------------------------------------- skeleton
class Grower:
    def __init__(self, rng, env=None, jitter=0.1, seg=0.05):
        self.rng, self.env, self.jitter, self.seg = rng, env, jitter, seg
        self.out = []
        self.env_from = 0     # axes of lower order (trunks) ignore the habit envelope

    def inside(self, p):
        c, r, pw = self.env     # superellipsoid: pw 2 = ellipsoid, 4 = boxy (a climber filling its trellis panel)
        q = (p - c) / r
        return float(np.sum(np.abs(q) ** pw)) ** (1.0 / pw)

    def axis(self, p0, d0, length, r0, order, trop=0.0, grav=0.0, rtip=0.0015, taper=0.8, plane=None, wiggle=0.0, drift_max=None):
        """Grow one polyline axis; children are spawned by the caller from the returned branch."""
        rng, n = self.rng, max(2, int(length / self.seg))
        seg = length / n
        pts, dirs = [np.array(p0, float)], []
        d = unit(d0)
        for i in range(n):
            d = d + rng.normal(0, self.jitter, 3) + UP * (trop - grav) * 0.06
            if wiggle:
                d = d + np.array([math.sin(i * 0.7 + order) * wiggle, 0, 0])
            if plane is not None:
                d[1] = d[1] * 0.2          # stay on the support plane
            if self.env is not None and order >= self.env_from:
                e = self.inside(pts[-1])
                if e > 1.0:                # pull back inside the habit envelope; stop when far outside
                    c = self.env[0]
                    d = unit(d) * 0.6 + unit(c - pts[-1]) * 0.6 * min(1.5, e)
                    if e > 1.18 and i >= 2:
                        break
            if drift_max is not None:      # a trunk wanders but is held near its base (a pruned head sits over the stem)
                off = pts[-1][:2] - np.asarray(p0, float)[:2]
                if np.linalg.norm(off) > drift_max:
                    d = d - np.array([off[0], off[1], 0]) * 0.5 / max(np.linalg.norm(off), 1e-6)
            d = unit(d)
            pts.append(pts[-1] + d * seg); dirs.append(d)
        pts = np.array(pts)
        t = np.linspace(0, 1, len(pts))
        radii = rtip + (r0 - rtip) * (1 - t) ** taper
        b = dict(pts=pts, radii=radii, order=order, kind="stem")
        self.out.append(b)
        return b


def _children(rng, pts, radii, order, P):
    """Child specs at nodes of an axis: list of (node index, direction, length, radius)."""
    out = []
    n = len(pts) - 1
    if n < 3:
        return out
    d_all = np.gradient(pts, axis=0)
    az = rng.uniform(0, 2 * math.pi)
    for i in range(max(1, int(n * P.get("start", 0.2))), n):
        if rng.random() > P["p"][min(order, len(P["p"]) - 1)]:
            continue
        az += GOLD + rng.normal(0, 0.4)
        d = unit(d_all[i])
        ang = math.radians(np.clip(rng.normal(P["ang"][0], P["ang"][1]), 15, 85))
        side = rot(perp(d), d, az)
        cd = unit(d * math.cos(ang) + side * math.sin(ang))
        remaining = (n - i) / n
        L = P["len"][min(order, len(P["len"]) - 1)] * (0.5 + 0.7 * remaining) * rng.uniform(0.7, 1.15)
        r = radii[i] * P["rf"] * rng.uniform(0.8, 1.1)
        out.append((i, cd, L, r))
    return out


def grow_tree(g, rng, p0, d0, length, r0, order, P, trop, grav):
    b = g.axis(p0, d0, length, r0, order, trop=trop[min(order, len(trop) - 1)], grav=grav[min(order, len(grav) - 1)], taper=P.get("taper", 0.9),
               rtip=P.get("rtip", 0.0015), plane=P.get("plane"), wiggle=P.get("wiggle", 0))
    if order >= P["max_order"] or length < P["min_len"]:
        b["terminal"] = True
        return
    for i, cd, L, r in _children(rng, b["pts"], b["radii"], order, P):
        if L < P["min_len"] * 0.6 or r < P.get("rtip", 0.0015) * 0.8:
            continue
        grow_tree(g, rng, b["pts"][i], cd, L, r, order + 1, P, trop, grav)
    b.setdefault("terminal", False)


# --------------------------------------------------------------------------------------------- leaves
def _pick(rng, spec):
    names = list(spec["banks"]); w = np.array([spec["banks"][k] for k in names], float)
    return names[rng.choice(len(names), p=w / w.sum())]


class LeafSet:
    def __init__(self, spec, rng):
        self.spec, self.rng = spec, rng
        self.base, self.dir, self.nrm, self.len, self.wid, self.arch, self.bank, self.leaf, self.tint = [], [], [], [], [], [], [], [], []

    def add(self, base, d, normal, scale=1.0, arch=None, var=0.0):
        s, rng = self.spec, self.rng
        bank = _pick(rng, s)
        leaves = BANKS[bank]["leaves"]
        k = int(rng.integers(len(leaves)))
        rec = leaves[k]
        L = s["leaf_len"] * scale * math.exp(rng.normal(0, s["len_sd"]))
        W = L * rec["wid_px"] / rec["len_px"] * s["wscale"]
        v = rng.uniform(0.85, 1.12) * (1 + var)
        # vertex-colour multiplier (linear light) that turns the scan's mean colour into the species' stated leaf colour:
        # a luminance gain plus a hue correction clipped to 0.6-1.7x (the scans are very dark, blue is near zero there)
        c, m = np.array(s["colour"], float), np.array(BANKS[bank]["mean_rgb"], float) + 0.5
        y = lambda x: float(x @ [0.2126, 0.7152, 0.0722])
        hue = np.clip((c / y(c)) / (m / y(m)), 0.6, 1.7)
        tint = (y(c) / y(m) * hue * v) ** 2.2 * np.array([rng.uniform(0.94, 1.06), 1.0, rng.uniform(0.94, 1.06)])
        if BANKS[bank].get("synthetic_outline"):      # palmate: the petiole joins at the blade's centre, not its edge
            base = np.asarray(base, float) - unit(d) * L * 0.46
        self.base.append(base); self.dir.append(unit(d)); self.nrm.append(unit(normal)); self.len.append(L); self.wid.append(W)
        self.arch.append(s["arch"] * rng.uniform(0.6, 1.3) if arch is None else arch)
        self.bank.append(bank); self.leaf.append(k); self.tint.append(tint)

    def arrays(self):
        f = lambda a: np.array(a, float).reshape(-1, 3) if len(a) else np.zeros((0, 3))
        return dict(base=f(self.base), dir=f(self.dir), normal=f(self.nrm), length=np.array(self.len), width=np.array(self.wid),
                    arch=np.array(self.arch), bank=list(self.bank), leaf=np.array(self.leaf, int), tint=f(self.tint))


def leaf_frame(branch_dir, outward, rng, spec, phototropy=0.55):
    """Leaf direction (blade axis base->tip) and surface normal: leaf leaves the twig outward-and-up, the upper surface
    turns toward the sky (phototropism), the tip droops by `arch` in the builder."""
    d = unit(outward * 0.8 + branch_dir * 0.5 + UP * 0.25 + rng.normal(0, 0.18, 3))
    side = np.cross(d, UP)
    nrm = unit(np.cross(side, d)) if np.linalg.norm(side) > 1e-6 else UP
    nrm = unit(nrm * phototropy + UP * (1 - phototropy) + rng.normal(0, 0.12, 3))
    return d, nrm


def place_on_twigs(grower, spec, rng, ls, lod_keep, zone, min_order=1):
    for b in grower.out:
        if b["order"] < min_order:
            continue
        pts = b["pts"]
        n = len(pts)
        d_all = np.gradient(pts, axis=0)
        start = int(n * (1 - zone))
        step = max(1, int(round(spec["node"] / max(1e-6, np.linalg.norm(pts[1] - pts[0])))))
        az = rng.uniform(0, 2 * math.pi)
        for i in range(start, n, step):
            bd = unit(d_all[i])
            ring = 2 if spec["arr"] == "opposite" else 1
            az += (math.pi / 2 if ring == 2 else GOLD)
            for j in range(ring):
                if rng.random() > lod_keep:
                    continue
                out = rot(perp(bd), bd, az + j * math.pi)
                d, nrm = leaf_frame(bd, out, rng, spec)
                ls.add(pts[i] + out * 0.004, d, nrm)
        # terminal leaf pair/bud at the very tip
        if rng.random() < lod_keep:
            bd = unit(d_all[-1]); out = rot(perp(bd), bd, rng.uniform(0, 6.28))
            d, nrm = leaf_frame(bd, out * 0.3, rng, spec)
            ls.add(pts[-1], d, nrm, scale=0.8)


# --------------------------------------------------------------------------------------------- forms
def build_shrub(spec, rng, H, S, reach, state, lod_keep):
    rx, rz = max(0.05, S / 2 - reach), H * 0.55
    env = (np.array([0, 0, rz * 0.98 + 0.02]), np.array([rx, rx, rz]), 2)
    g = Grower(rng, env, spec["jitter"], seg=max(0.02, H / 28))
    P = dict(p=[0.5, spec["branch_p"], spec["branch_p"]], ang=(48, 14), len=[H * 0.6, H * 0.4, H * 0.22], rf=0.62, max_order=3, min_len=max(0.04, H * 0.06),
             start=0.25, rtip=max(0.0012, H * 0.0012), taper=0.9)
    for k in range(spec["stems"]):
        a = rng.uniform(0, 2 * math.pi); el = math.radians(rng.uniform(*spec["stem_elev"]))
        d0 = np.array([math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)])
        p0 = np.array([math.cos(a), math.sin(a), 0]) * rng.uniform(0.01, 0.06)
        grow_tree(g, rng, p0, d0, H * rng.uniform(0.85, 1.15), max(0.004, H * 0.012), 0, P, trop=[0.8, 0.2, 0.1], grav=[0.0, 0.2, 0.5])
    ls = LeafSet(spec, rng)
    place_on_twigs(g, spec, rng, ls, lod_keep, spec["leaf_zone"])
    return g, ls


def build_climber(spec, rng, H, S, reach, state, lod_keep):
    """Stems rise along the support plane (x-z), laterals run sideways-up; leaves hang facing +y."""
    hw = max(0.05, S / 2 - reach)
    th = spec["thickness"]
    env = (np.array([0, th * 0.5, H * 0.5]), np.array([hw, th * 0.6, H * 0.58]), 4)
    g = Grower(rng, env, spec["jitter"], seg=0.06)
    P = dict(p=[0.55, spec["branch_p"], spec["branch_p"]], ang=(62, 18), len=[H * 0.5, H * 0.3, 0.2], rf=0.6, max_order=3, min_len=0.12,
             start=0.15, rtip=0.0015, taper=0.7, plane=True, wiggle=0.03)
    for k in range(spec["stems"]):
        x0 = (k / max(1, spec["stems"] - 1) - 0.5) * hw * 1.2
        grow_tree(g, rng, np.array([x0, 0.02, 0.0]), np.array([rng.normal(0, 0.15), 0.05, 1.0]), H * rng.uniform(0.9, 1.1), 0.006, 0, P,
                  trop=[0.5, 0.3, 0.2], grav=[0.0, -0.1, 0.1 + spec.get("lax", 0.0)])     # lax: laterals sag and loop (grape, petrea) instead of lying on the trellis
    ls = LeafSet(spec, rng)
    if state == "leaf-off":             # a deciduous climber (grape) in winter: the same stems, no leaves
        return g, ls
    for b in g.out:
        pts = b["pts"]; n = len(pts)
        d_all = np.gradient(pts, axis=0)
        step = max(1, int(round(spec["node"] * 1.5 / 0.06)))
        for i in range(2, n, step):
            bd = unit(d_all[i])
            for j in range(2 if spec["arr"] == "opposite" else 1):
                if rng.random() > lod_keep * spec.get("keep", 0.8):
                    continue
                side = (-1 if j else 1) * (1 if spec["arr"] == "opposite" else rng.choice([-1, 1]))
                d = unit(np.array([side * rng.uniform(0.2, 0.9), rng.uniform(0.5, 1.0), -rng.uniform(0.0, 0.7)]) + rng.normal(0, 0.1, 3))
                nrm = unit(np.array([0, 1.0, 0.4]) + rng.normal(0, 0.15, 3))
                ls.add(pts[i], d, nrm)
    return g, ls


def build_tree(spec, rng, H, S, reach, state, lod_keep, lean=(0.0, 0.0)):
    """Pruned multi-stem shade tree: 3-5 stems, clear to `clear_stem`, then forking limbs, round-headed crown."""
    cs = spec["clear_stem"]
    hw = S / 2 - reach * 0.5      # same skeleton in both states: leaf-off is the leaf-on tree with the leaves removed
    cz = cs + (H - cs) * 0.5
    env = (np.array([lean[0], lean[1], cz]), np.array([hw, hw, (H - cs) * 0.56]), 2.6)
    g = Grower(rng, env, 0.07, seg=0.09)
    g.env_from = 1
    P = dict(p=[0.6, 0.55, 0.45, 0.4, 0.35, 0.3], ang=(44, 14), len=[1.7, 1.2, 0.8, 0.55, 0.36, 0.25], rf=0.66, max_order=6, min_len=0.08, start=0.3, rtip=0.0012, taper=0.85)
    for k in range(spec["stems"]):
        a = 2 * math.pi * k / spec["stems"] + rng.normal(0, 0.3)
        p0 = np.array([math.cos(a), math.sin(a), 0]) * 0.12
        lean_v = np.array([lean[0], lean[1], 0]) / max(cs, 1) * rng.uniform(0.6, 1.0)
        d0 = unit(np.array([math.cos(a) * 0.12, math.sin(a) * 0.12, 1.0]) + lean_v)
        # trunk: clear stem, slightly sinuous; its children (the crown limbs) start above the clear height
        trunk = g.axis(p0, d0, H * 0.95, 0.07, 0, trop=0.6, grav=0, taper=0.7, rtip=0.01, drift_max=max(0.3, hw * 0.38))
        trunk["terminal"] = False
        pts = trunk["pts"]
        for i in range(len(pts)):
            if pts[i][2] < cs * 0.92:
                continue
            if rng.random() > 0.55:
                continue
            ang = math.radians(rng.uniform(25, 58)); az = rng.uniform(0, 2 * math.pi)
            dd = unit(trunk["pts"][min(i + 1, len(pts) - 1)] - pts[i])
            side = rot(perp(dd), dd, az)
            cd = unit(dd * math.cos(ang) + side * math.sin(ang))
            grow_tree(g, rng, pts[i], cd, rng.uniform(1.0, 1.9), trunk["radii"][i] * 0.62, 1, P, trop=[0.5, 0.45, 0.3, 0.2, 0.1, 0.05], grav=[0, 0, 0.1, 0.3, 0.4, 0.5])
    ls = LeafSet(spec, rng)
    if state == "leaf-on":
        place_on_twigs(g, spec, rng, ls, lod_keep, 0.9, min_order=3)
    return g, ls


def build_basal(spec, rng, H, S, reach, state, lod_keep):
    """Leaves on petioles from a crown (farfugium)."""
    g = Grower(rng, None)
    ls = LeafSet(spec, rng)
    hw = max(0.05, S / 2 - spec["leaf_len"] * 0.5)
    for k in range(spec["count"]):
        a = k * GOLD + rng.normal(0, 0.2)
        r_h = hw * math.sqrt((k + 1) / spec["count"]) * rng.uniform(0.7, 1.0)
        top_z = max(H * 0.45, H * (0.55 + 0.45 * (1 - (k + 1) / spec["count"])) * rng.uniform(0.7, 1.0) - spec["leaf_len"] * 0.3)
        out = np.array([math.cos(a), math.sin(a), 0])
        p0 = out * 0.015
        top = out * r_h + np.array([0, 0, top_z])
        mid = (p0 + top) / 2 + out * r_h * 0.15 + np.array([0, 0, top_z * 0.15])
        t = np.linspace(0, 1, 7)[:, None]
        pts = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t ** 2 * top + rng.normal(0, 0.003, (7, 3))
        g.out.append(dict(pts=pts, radii=np.linspace(0.0035, 0.0018, 7), order=1, kind="petiole", terminal=True))
        dtop = unit(pts[-1] - pts[-2])
        d = unit(out * 0.8 - UP * 0.15 + rng.normal(0, 0.1, 3))
        ls.add(pts[-1], d, unit(UP * 0.85 + out * 0.4), scale=rng.uniform(0.7, 1.15))
    return g, ls


def build_petioled(spec, rng, H, S, reach, state, lod_keep):
    """Fatsia: a few stout leaning stems; leaves on long petioles in a crown at the top and along the upper stem."""
    g = Grower(rng, None, 0.05, seg=0.08)
    ls = LeafSet(spec, rng)
    hw = max(0.05, S / 2 - spec["leaf_len"] * 0.45)
    for k in range(spec["stems"]):
        a = 2 * math.pi * k / spec["stems"] + rng.normal(0, 0.5)
        lean = rng.uniform(0.05, 0.2)
        h_k = H * rng.uniform(0.8, 1.0)
        d0 = unit(np.array([math.cos(a) * lean, math.sin(a) * lean, 1.0]))
        st = g.axis(np.array([math.cos(a), math.sin(a), 0]) * 0.05, d0, h_k, 0.022, 0, trop=0.2, taper=0.45, rtip=0.014)
        st["terminal"] = False
        pts = st["pts"]; n = len(pts)
        az = rng.uniform(0, 6.28)
        for i in range(int(n * (1 - spec["leaf_zone"])), n):
            for _ in range(3 if i > n - 3 else 1):
                az += GOLD
                out = np.array([math.cos(az), math.sin(az), 0])
                up_frac = (i / n)
                plen = spec["petiole"] * rng.uniform(0.7, 1.2) * (0.6 + 0.6 * up_frac) * (spec["leaf_len"] / 0.3) ** 0.5 + 0.12
                lat = min(plen * 0.8, hw)
                top = pts[i] + out * lat + np.array([0, 0, plen * rng.uniform(0.25, 0.6)])
                mid = (pts[i] + top) / 2 + np.array([0, 0, plen * 0.3])
                t = np.linspace(0, 1, 6)[:, None]
                pp = (1 - t) ** 2 * pts[i] + 2 * (1 - t) * t * mid + t ** 2 * top
                g.out.append(dict(pts=pp, radii=np.linspace(0.006, 0.004, 6), order=1, kind="petiole", terminal=True))
                ls.add(pp[-1], unit(out * 0.75 - UP * 0.3 + rng.normal(0, 0.1, 3)), unit(UP * 0.85 + out * 0.45), scale=rng.uniform(0.75, 1.1), arch=0.3)
    return g, ls


def build_strap(spec, rng, H, S, reach, state, lod_keep):
    """Clumping strap leaves arching from a crown (acorus): each blade a long thin card with a downward arch."""
    g = Grower(rng, None)
    ls = LeafSet(spec, rng)
    hw = S / 2
    for k in range(spec["count"]):
        a = k * GOLD + rng.normal(0, 0.15)
        el = math.radians(rng.uniform(*spec.get('elev', (66, 88))))
        out = np.array([math.cos(a), math.sin(a), 0])
        d = np.array([out[0] * math.cos(el), out[1] * math.cos(el), math.sin(el)])
        # length chosen so the arched tip lands near the sourced height and spread
        L = H * rng.uniform(0.9, 1.2) * 1.15
        ls.add(out * 0.01, d, unit(np.cross(np.cross(d, UP), d) + UP * 0.1), scale=L / spec["leaf_len"], arch=spec["arch"] * rng.uniform(0.7, 1.2))
    return g, ls


def build_cane(spec, rng, H, S, reach, state, lod_keep):
    """Alpinia: leafy canes (pseudostems) with distichous long leaves."""
    g = Grower(rng, None, 0.02, seg=0.1)
    ls = LeafSet(spec, rng)
    for k in range(spec["count"]):
        a = k * GOLD
        r0 = rng.uniform(0.03, S * 0.22)
        h_k = H * rng.uniform(0.75, 1.0)
        base = np.array([math.cos(a) * r0, math.sin(a) * r0, 0])
        d0 = unit(np.array([math.cos(a) * 0.12, math.sin(a) * 0.12, 1.0]))
        st = g.axis(base, d0, h_k, 0.014, 0, trop=0.1, taper=0.4, rtip=0.008)
        st["terminal"] = False
        pts = st["pts"]; n = len(pts)
        az = rng.uniform(0, 6.28)
        for i in range(int(n * 0.12), n):
            az += math.pi + rng.normal(0, 0.15)         # distichous: two ranks
            out = np.array([math.cos(az), math.sin(az), 0])
            d = unit(out * rng.uniform(0.6, 1.0) + UP * rng.uniform(0.35, 0.8))
            ls.add(pts[i], d, unit(UP * 0.7 + out * 0.3), scale=1.0 - 0.25 * (1 - i / n), arch=spec["arch"] * rng.uniform(0.6, 1.2))
    return g, ls


FORMS = dict(shrub=build_shrub, climber=build_climber, tree=build_tree, basal=build_basal, petioled=build_petioled, strap=build_strap, cane=build_cane)


# --------------------------------------------------------------------------------------------- public
def label_of(slug, spec, seed, state, banks_used):
    sci = BANKS[next(iter(banks_used))]["scientific_name"] if banks_used else None
    species_ok = len(banks_used) == 1 and not any(BANKS[b].get("synthetic_outline") for b in banks_used) and all(BANKS[b]["scientific_name"].split()[:2] == spec["accepted"].split()[:2] for b in banks_used)
    genus = all(BANKS[b]["scientific_name"].split()[0] == spec["accepted"].split()[0] and not BANKS[b].get("synthetic_outline") for b in banks_used)
    return dict(
        atlas_match="species" if species_ok else "genus" if genus else "none",     # genus: the scanned plant is the same genus, a different species (form-class)
        species=slug, accepted_name=spec["accepted"], generator_version=VERSION, seed=int(seed), state=state,
        atlas_used=sorted(banks_used), atlas_species=sorted({BANKS[b]["scientific_name"] for b in banks_used}),
        fidelity="species" if species_ok else "form-class",
        construction="generated", leaf_len_source=spec["leaf_len_source"],
        caption=("generated %s (leaf scan: %s)" % (spec["accepted"], ", ".join(sorted({BANKS[b]["scientific_name"] for b in banks_used})))) if species_ok
        else ("generated form-class plant standing in for %s (leaf scan: %s; not the species)" % (spec["accepted"], ", ".join(sorted({BANKS[b]["scientific_name"] for b in banks_used})))))


def default_size(slug):
    r = sourced_ranges(slug)
    h = sum(r["height"]) / 2 if r["height"] else None
    s = sum(r["spread"]) / 2 if r["spread"] else None
    return h, s


def generate(slug, seed=0, height_m=None, spread_m=None, state="leaf-on", lod=0, lean=(0.0, 0.0), clear_stem=None):
    spec = SPECS[slug]
    if clear_stem is not None:          # lane GI: a tree at an age keeps the layout's clear-stem proportion (the spec's figure is for the full-size tree)
        spec = dict(spec, clear_stem=float(clear_stem))
    h0, s0 = default_size(slug)
    H = float(height_m or h0 or 1.0)
    S = float(spread_m or s0 or H)
    rng = np.random.default_rng([int(seed), abs(hash(slug)) % 1000 if False else sum(map(ord, slug))])
    keep = (1.0, 0.5, 0.25)[lod]
    reach = spec["leaf_len"] * 0.6 if spec["form"] in ("shrub", "climber", "tree") else 0.0
    fn = FORMS[spec["form"]]
    if spec["form"] == "tree":
        g, ls = fn(spec, rng, H, S, reach, state, keep, lean)
    else:
        g, ls = fn(spec, rng, H, S, reach, state, keep)
    # leaf scale compensation when thinned (lod): bigger leaves keep the mass
    arr = ls.arrays()
    if lod and len(arr["length"]):
        arr["length"] = arr["length"] * (1 + 0.35 * lod); arr["width"] = arr["width"] * (1 + 0.35 * lod)
    plant = Plant(slug, int(seed), state, H, S, {}, g.out, arr)
    _fit(plant, spec)
    plant.label = label_of(slug, spec, seed, state, set(arr["bank"]) or set(spec["banks"]))
    return plant


def _fit(plant, spec):
    """Scale positions (not leaf sizes) so the measured bounding box matches the target height and spread; 6 passes."""
    for _ in range(6):
        lo, hi = plant.bbox()
        ext = hi - lo
        spread = max(ext[0], ext[1]) if spec["form"] != "climber" else ext[0]
        fz = plant.height_m / max(ext[2], 1e-6)
        fx = plant.spread_m / max(spread, 1e-6)
        if abs(fz - 1) < 0.02 and abs(fx - 1) < 0.02:
            break
        if spec["form"] in ("strap",):       # no skeleton: the blades themselves are the plant
            plant.leaves["length"] = plant.leaves["length"] * fz; plant.leaves["width"] = plant.leaves["width"] * fz
            d = plant.leaves["dir"].copy(); d[:, :2] *= fx                # too wide -> steeper blades, too narrow -> flatter
            plant.leaves["dir"] = d / np.linalg.norm(d, axis=1)[:, None]
            continue
        for b in plant.branches:
            b["pts"] = b["pts"] * np.array([fx, fx if spec["form"] != "climber" else 1.0, fz])
        plant.leaves["base"] = plant.leaves["base"] * np.array([fx, fx if spec["form"] != "climber" else 1.0, fz])
    # ground the plant: lowest point z = 0, centred on its base
    lo, hi = plant.bbox()
    off = np.array([0, 0, -lo[2]])
    for b in plant.branches:
        b["pts"] = b["pts"] + off
    plant.leaves["base"] = plant.leaves["base"] + off
