"""Minimal EULUMDAT (.ldt) reader, a second manufacturer file format used to cross-check the .ies of the same product.

Layout (EULUMDAT spec as used by every lighting tool): 1 company, 2 Ityp, 3 Isym, 4 Mc, 5 Dc, 6 Ng, 7 Dg, 8-12 text,
13-25 dimensions/ratios (22 DFF, 23 LORL %, 24 conversion factor, 25 tilt), 26 number of lamp sets n, then per set
6 lines (number of lamps, type, TOTAL lamp lumens, colour, CRI, watts), 10 direct ratios, Mc C angles, Ng gamma angles,
then the intensity planes in cd per 1000 lamp lumens. Isym 0 stores Mc planes, 1 stores 1, 2 and 3 store Mc/2+1, 4 stores Mc/4+1.
Absolute candela = value x (total lamp lumens / 1000) x conversion factor (line 24); LORL is already inside the cd/klm of
a luminaire measured as a whole, so it is NOT applied again (checked against the .ies of the same product by test).
"""
from __future__ import annotations

from .ies import IesData


def parse(text: str) -> IesData:
    L = [l.strip() for l in text.replace("\r", "").split("\n")]
    isym, mc, dc, ng, dg = int(L[2]), int(L[3]), float(L[4]), int(L[5]), float(L[6])
    n = int(L[25])
    p = 26
    lamps, total_lm, watts = 0, 0.0, 0.0
    cct = None
    for _ in range(n):
        lamps += int(float(L[p]))
        total_lm += float(L[p + 2])
        watts += float(L[p + 5])
        import re
        m = re.search(r"(\d{4})", L[p + 3])
        cct = float(m.group(1)) if m else cct
        p += 6
    p += 10
    nums = [float(x) for x in " ".join(L[p:]).split()]
    cang = nums[:mc]
    gamma = nums[mc:mc + ng]
    body = nums[mc + ng:]
    planes = {0: mc, 1: 1, 2: mc // 2 + 1, 3: mc // 2 + 1, 4: mc // 4 + 1}[isym]
    if len(body) != planes * ng:
        raise ValueError("ldt: %d intensity values, expected %d x %d" % (len(body), planes, ng))
    k = total_lm / 1000.0 * float(L[23])
    cd = [[v * k for v in body[i * ng:(i + 1) * ng]] for i in range(planes)]
    if isym == 1:
        ca = [0.0]
    elif isym == 0:
        ca = cang
    elif isym == 2:
        ca = cang[:planes]                       # C0..C180 stored, mirror about the C0-C180 plane
    elif isym == 3:
        ca = cang[:planes]
    else:
        ca = cang[:planes]
    d = IesData(lamps, total_lm / max(1, lamps), 1.0, 1, 2, (0.0, 0.0, 0.0), watts, gamma, ca, cd, {}, cct)
    d.ldt_isym = isym
    return d
