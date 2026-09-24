"""EULUMDAT (.ldt) reader, and conversion to the pipeline's IES photometry.

EULUMDAT is the European photometric format, and the one European and MENA
manufacturers publish first. Unlike an IES file it states the product: the
luminaire's own dimensions, its luminous area, and for each lamp set the
flux, colour temperature, colour rendering and wattage. A product library
built from LDT files therefore needs no hand-typed specification -- the
file IS the manufacturer's specification.

Field positions follow the EULUMDAT definition (Stockmar, 1990), numbered
here as its line numbers:

     1 company / databank     13-15 luminaire length (diameter), width, height mm
     2 Ityp                   16-21 luminous area length, width, heights C0/C90/C180/C270
     3 Isym (symmetry)        22 DFF %   23 LORL %   24 conversion factor   25 tilt
     4 Mc  5 Dc (C planes)    26 n lamp sets, then per set: number, type, total
     6 Ng  7 Dg (gamma)          flux lm, colour temperature, CRI group/index, watts
     8 report  9 name         then 10 direct ratios, Mc C angles, Ng gamma angles,
    10 number 11 file 12 date  and the intensities in cd/klm for the planes Isym needs.

Intensities are cd per 1000 lm of LAMP flux. The absolute candela for lamp
set k is value * flux_k / 1000 * conversion factor.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from archpipe import photometry as ph


class LDTError(ValueError):
    """An LDT file we could not read, with a reason worth reading."""


@dataclass(frozen=True)
class LampSet:
    count: int
    lamp_type: str
    flux_lm: float          # total lamp flux of the set
    cct: str                # as written: "3000", "2700-6500", "830"...
    cri: str                # as written: "80", "1B", ">90"...
    watts: float            # including control gear

    @property
    def cct_k(self) -> float | None:
        """Kelvin when the file states a single number, else None."""
        try:
            return float(self.cct.strip())
        except ValueError:
            return None

    @property
    def cri_ra(self) -> float | None:
        s = self.cri.strip().lstrip(">=")
        try:
            return float(s)
        except ValueError:
            return None


@dataclass(frozen=True)
class Eulumdat:
    company: str
    ityp: int
    isym: int
    mc: int
    dc: float
    ng: int
    dg: float
    report: str
    name: str
    number: str
    date: str
    size_mm: tuple[float, float, float]            # length (or diameter), width (0 = round), height
    luminous_mm: tuple[float, float]               # length (or diameter), width (0 = round)
    luminous_heights_mm: tuple[float, float, float, float]
    dff: float
    lorl: float
    conversion: float
    tilt: float
    lamp_sets: tuple[LampSet, ...]
    direct_ratios: tuple[float, ...]
    c_angles: tuple[float, ...]                    # all Mc planes as listed
    g_angles: tuple[float, ...]
    planes: dict = field(default_factory=dict)     # C angle -> tuple of cd/klm over g_angles
    source: Path | None = None

    # ------------------------------------------------------------------ facts
    @property
    def round(self) -> bool:
        return self.size_mm[1] <= 0

    def intensity_rel(self, c_deg: float, g_deg: float) -> float:
        """cd/klm in a direction, using the file's symmetry."""
        c = _fold_c(c_deg % 360.0, self.isym)
        cs = sorted(self.planes)
        g = float(g_deg)
        if g < self.g_angles[0] or g > self.g_angles[-1]:
            return 0.0
        if len(cs) == 1:
            return _interp(self.g_angles, self.planes[cs[0]], g)
        # A full circle is periodic: past the last plane, C360 is C0.
        lo = max((x for x in cs if x <= c), default=cs[0])
        hi = min((x for x in cs if x >= c), default=None)
        a = _interp(self.g_angles, self.planes[lo], g)
        if hi is None:
            if 0.0 not in self.planes:
                return a
            hi, b = 360.0, _interp(self.g_angles, self.planes[0.0], g)
        else:
            b = _interp(self.g_angles, self.planes[hi], g)
        return a if hi == lo else a + (b - a) * (c - lo) / (hi - lo)

    def integrated_rel_flux(self, steps: int = 360, azimuths: int = 72) -> float:
        """Flux of the distribution in lm per 1000 lm of lamp flux.

        Equals LORL x 10 for a consistent file -- the check this module's
        conversion is proven against.
        """
        total = 0.0
        for i in range(steps):
            a, b = math.pi * i / steps, math.pi * (i + 1) / steps
            g = math.degrees((a + b) / 2.0)
            mean = sum(self.intensity_rel(j * 360.0 / azimuths, g) for j in range(azimuths)) / azimuths
            total += mean * 2.0 * math.pi * math.sin((a + b) / 2.0) * (b - a)
        return total * self.conversion

    def luminaire_flux(self, lamp_set: int = 0) -> float:
        """Lumens leaving the luminaire for a lamp set (lamp flux x LORL)."""
        return self.lamp_sets[lamp_set].flux_lm * self.lorl / 100.0

    # ------------------------------------------------------------ conversion
    # MEASURED against the manufacturer's own IES for the same product
    # (Signify 911401840687, all three lamp sets): IES horizontal angle h is
    # EULUMDAT plane C = h + 90. Without the rotation the peak and the flux
    # agreed exactly while single directions differed by up to 34%; with it,
    # every direction agrees within 0.02%. The importer re-checks this on
    # every product shipped in both formats.
    IES_FROM_C_OFFSET_DEG = 90.0

    def horizontal_for_ies(self) -> tuple[float, ...]:
        """Horizontal angles in the IES (LM-63) symmetry convention.

        LM-63 carries symmetry in the angle range: one angle (round), 0-90
        (quadrants), 0-360 (none). A single-plane mirror moves to the 90-270
        plane under the 90-degree rotation, which the pipeline's reader does
        not fold, so single-mirror files are written as a full 0-360 file.
        """
        step = self.dc if self.dc > 0 else 360.0 / max(self.mc, 1)
        if self.isym == 1:
            return (0.0,)
        if self.isym == 4:
            return tuple(round(i * step, 6) for i in range(int(round(90.0 / step)) + 1))
        return tuple(round(i * step, 6) for i in range(int(round(360.0 / step)) + 1))

    def to_photometry(self, lamp_set: int = 0) -> ph.Photometry:
        """Absolute candela for one lamp set, as the pipeline's Photometry."""
        ls = self.lamp_sets[lamp_set]
        scale = ls.flux_lm / 1000.0 * self.conversion
        hs = self.horizontal_for_ies()
        cand = tuple(tuple(self.intensity_rel(h + self.IES_FROM_C_OFFSET_DEG, g) * scale for h in hs)
                     for g in self.g_angles)
        lum_len, lum_w = self.luminous_mm
        if lum_w <= 0:       # LM-63-2002: a round opening is written as negative width = length
            width = length = -lum_len / 1000.0
        else:
            width, length = lum_w / 1000.0, lum_len / 1000.0
        return ph.Photometry(
            name=self.name, lamps=1, lumens_per_lamp=ls.flux_lm, input_watts=ls.watts,
            vertical=tuple(self.g_angles), horizontal=hs, candela=cand,
            photometric_type=1, units_type=2, width=width, length=length,
            height=max(self.luminous_heights_mm) / 1000.0, source=self.source)

    def to_ies_text(self, lamp_set: int = 0, manufacturer: str = "") -> str:
        p = self.to_photometry(lamp_set)
        ls = self.lamp_sets[lamp_set]
        head = ["IESNA:LM-63-2002",
                f"[TEST] {self.report}",
                f"[MANUFAC] {manufacturer or self.company}",
                f"[LUMCAT] {self.number}",
                f"[LUMINAIRE] {self.name}",
                f"[LAMP] {ls.lamp_type}",
                f"[OTHER] converted from EULUMDAT by archpipe.luminaires.eulumdat, lamp set {lamp_set + 1}"
                f" of {len(self.lamp_sets)}; CCT {ls.cct}; CRI {ls.cri}",
                "TILT=NONE",
                f"1 {ls.flux_lm:.2f} 1 {len(p.vertical)} {len(p.horizontal)} 1 2 "
                f"{p.width:.4f} {p.length:.4f} {p.height:.4f}",
                f"1.0 1.0 {ls.watts:.2f}"]
        body = [_wrap(p.vertical), _wrap(p.horizontal)]
        for j in range(len(p.horizontal)):
            body.append(_wrap([p.candela[i][j] for i in range(len(p.vertical))]))
        return "\n".join(head + body) + "\n"


# ---------------------------------------------------------------------- parse
def _num(s: str, what: str, line: int) -> float:
    try:
        return float(s.strip().replace(",", "."))
    except ValueError:
        raise LDTError(f"line {line}: {what} is not a number: {s!r}") from None


def parse(text: str, source: Path | None = None) -> Eulumdat:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(lines) < 42:
        raise LDTError(f"only {len(lines)} lines; not a EULUMDAT file")
    L = lambda n: lines[n - 1]          # the definition's 1-based line numbers
    ityp, isym = int(_num(L(2), "Ityp", 2)), int(_num(L(3), "Isym", 3))
    if isym not in (0, 1, 2, 3, 4):
        raise LDTError(f"line 3: symmetry indicator {isym} is not 0-4")
    mc, dc = int(_num(L(4), "Mc", 4)), _num(L(5), "Dc", 5)
    ng, dg = int(_num(L(6), "Ng", 6)), _num(L(7), "Dg", 7)
    if mc <= 0 or ng <= 0:
        raise LDTError(f"Mc={mc} Ng={ng}: no intensity table")
    n_sets = int(_num(L(26), "number of lamp sets", 26))
    if not 1 <= n_sets <= 50:
        raise LDTError(f"line 26: {n_sets} lamp sets is not plausible")
    sets, at = [], 27
    for _ in range(n_sets):
        sets.append(LampSet(count=int(_num(lines[at - 1], "lamp count", at)),
                            lamp_type=lines[at].strip(),
                            flux_lm=_num(lines[at + 1], "lamp flux", at + 2),
                            cct=lines[at + 2].strip(), cri=lines[at + 3].strip(),
                            watts=_num(lines[at + 4], "watts", at + 5)))
        at += 6
    nums = []
    for n, s in enumerate(lines[at - 1:], at):
        s = s.strip()
        if s:
            nums.append(_num(s, "table value", n))
    ratios, rest = nums[:10], nums[10:]
    c_angles, rest = rest[:mc], rest[mc:]
    g_angles, rest = rest[:ng], rest[ng:]
    first, count = _planes_stored(isym, mc)
    need = count * ng
    if len(rest) < need:
        raise LDTError(f"intensity table has {len(rest)} values; Isym {isym} with "
                       f"Mc {mc} and Ng {ng} needs {need}")
    if any(b < a for a, b in zip(g_angles, g_angles[1:])):
        raise LDTError("gamma angles are not ascending")
    planes = {}
    for k in range(count):
        c = c_angles[(first + k) % mc]
        planes[round(c, 6)] = tuple(rest[k * ng:(k + 1) * ng])
    if any(v < 0 for vals in planes.values() for v in vals):
        raise LDTError("negative luminous intensity")
    size = (_num(L(13), "length", 13), _num(L(14), "width", 14), _num(L(15), "height", 15))
    return Eulumdat(
        company=L(1).strip(), ityp=ityp, isym=isym, mc=mc, dc=dc, ng=ng, dg=dg,
        report=L(8).strip(), name=L(9).strip(), number=L(10).strip(), date=L(12).strip(),
        size_mm=size, luminous_mm=(_num(L(16), "luminous length", 16), _num(L(17), "luminous width", 17)),
        luminous_heights_mm=tuple(_num(L(n), "luminous height", n) for n in (18, 19, 20, 21)),
        dff=_num(L(22), "DFF", 22), lorl=_num(L(23), "LORL", 23),
        conversion=_num(L(24), "conversion factor", 24) or 1.0,  # falsy-ok: a 0 factor would zero every intensity
        tilt=_num(L(25), "tilt", 25), lamp_sets=tuple(sets), direct_ratios=tuple(ratios),
        c_angles=tuple(c_angles), g_angles=tuple(g_angles), planes=planes, source=source)


def load(path: str | Path) -> Eulumdat:
    p = Path(path)
    raw = p.read_bytes()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return parse(raw.decode(enc), source=p)
        except UnicodeDecodeError:
            continue
    raise LDTError("undecodable")


# --------------------------------------------------------------------- helpers
def _planes_stored(isym: int, mc: int) -> tuple[int, int]:
    """(index of the first stored C plane, number of stored planes)."""
    if isym == 0:
        return 0, mc
    if isym == 1:
        return 0, 1
    if isym == 2:
        return 0, mc // 2 + 1
    if isym == 3:                        # C270 .. C0 .. C90
        return (3 * mc) // 4, mc // 2 + 1
    return 0, mc // 4 + 1                # isym 4: C0 .. C90


def _fold_c(c: float, isym: int) -> float:
    """Map any C angle onto a stored plane under the file's symmetry."""
    if isym == 1:
        return 0.0
    if isym == 2:                        # mirror about C0-C180
        return 360.0 - c if c > 180.0 else c
    if isym == 3:                        # mirror about C90-C270
        return (180.0 - c) % 360.0 if 90.0 < c < 270.0 else c
    if isym == 4:                        # both
        c = 360.0 - c if c > 180.0 else c
        return 180.0 - c if c > 90.0 else c
    return c


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            span = xs[i] - xs[i - 1]
            f = 0.0 if span <= 0 else (x - xs[i - 1]) / span
            return ys[i - 1] + (ys[i] - ys[i - 1]) * f
    return ys[-1]


def _wrap(values, per_line: int = 10) -> str:
    vals = [f"{v:.2f}" for v in values]
    return "\n".join(" ".join(vals[i:i + per_line]) for i in range(0, len(vals), per_line))
