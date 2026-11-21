"""Unified Glare Rating, CIE 117 basic formula.

    UGR = 8 log10( (0.25 / Lb) * sum_i( L_i^2 * omega_i / p_i^2 ) ),   Lb = E_ind / pi

(SLL Code eq. 12.16, printed p. 206; IES HB10 eq. 10.35, p. 10.35, same form.)

Position index. The IES HB10 print of eq. 10.36 (p. 10.35) is NOT used: it gives p = 10.36 on the line of
sight (the equation number has been typeset into the formula) and drops the linear/quadratic terms in alpha, so
it cannot be a Guth index (p must be 1 at sigma = 0). The Guth form implemented here is the CIE 117 one,

    ln p = [35.2 - 0.31889 tau - 1.22 exp(-2 tau/9)] 1e-3 sigma + [21 + 0.26667 tau - 0.002963 tau^2] 1e-5 sigma^2

with sigma = angle between the line of sight and the direction to the source, tau = twist angle between the
vertical plane through the line of sight and the plane through the line of sight and the source. These
coefficients are NOT printed legibly in a held page; they were validated against SLL Table 12.10's K column
(K = pi / (4 p^2 D^2), printed p. 209) -- see `position_index_vs_sll_table_12_10()` -- which constrains p to a
few percent but is not a primary source. Status: validated-not-sourced.
"""
from __future__ import annotations

import math

from .direct import Placement, luminance_toward, _dot, _norm

VALID_OMEGA = (0.0003, 0.1)   # sr, IES HB10 10.9.2: the formula's stated range of validity


def guth_position_index(sigma_deg: float, tau_deg: float) -> float:
    s, t = sigma_deg, tau_deg
    ln_p = ((35.2 - 0.31889 * t - 1.22 * math.exp(-2.0 * t / 9.0)) * 1e-3 * s
            + (21.0 + 0.26667 * t - 0.002963 * t * t) * 1e-5 * s * s)
    return math.exp(ln_p)


def sigma_tau(eye, view_dir, target) -> tuple[float, float]:
    """(sigma, tau) in degrees of `target` as seen from `eye` looking along `view_dir`."""
    e = _norm(tuple(view_dir))
    u = _norm(tuple(target[i] - eye[i] for i in range(3)))
    cs = max(-1.0, min(1.0, _dot(u, e)))
    sigma = math.degrees(math.acos(cs))
    z = (0.0, 0.0, 1.0)
    zp = tuple(z[i] - _dot(z, e) * e[i] for i in range(3))
    up = tuple(u[i] - cs * e[i] for i in range(3))
    nz, nu = math.sqrt(_dot(zp, zp)), math.sqrt(_dot(up, up))
    if nz < 1e-9 or nu < 1e-9:
        return sigma, 0.0
    tau = math.degrees(math.acos(max(-1.0, min(1.0, _dot(zp, up) / (nz * nu)))))
    return sigma, tau


def background_luminance(e_ind_lux: float) -> float:
    return e_ind_lux / math.pi


def ugr(eye, view_dir, placements: list[Placement], lb: float, *, max_sigma_deg: float = 90.0) -> dict:
    """UGR at an observer from flat luminous openings. Returns {'ugr', 'terms', 'warnings'}.

    L = I / A_projected toward the eye (opening normal = aim); omega = A_projected / d^2 (point approximation of
    the solid angle; flagged where omega leaves 0.0003-0.1 sr). Sources behind the observer
    (sigma > max_sigma_deg) are excluded. ugr is None when nothing contributes or Lb <= 0.
    """
    if lb <= 0:
        return {"ugr": None, "terms": [], "warnings": ["Lb <= 0"]}
    terms, warns, total = [], [], 0.0
    for p in placements:
        L, a, d = luminance_toward(p, eye)
        if L <= 0:
            continue
        sigma, tau = sigma_tau(eye, view_dir, p.position)
        if sigma > max_sigma_deg:
            continue
        omega = a / (d * d)
        pi_ = guth_position_index(sigma, tau)
        t = L * L * omega / (pi_ * pi_)
        total += t
        if not (VALID_OMEGA[0] <= omega <= VALID_OMEGA[1]):
            warns.append(f"{p.id}: omega {omega:.5f} sr outside the formula's range {VALID_OMEGA}")
        terms.append({"id": p.id, "L_cd_m2": L, "omega_sr": omega, "sigma_deg": sigma, "tau_deg": tau, "p": pi_,
                      "term": t})
    if total <= 0:
        return {"ugr": None, "terms": terms, "warnings": warns + ["no source contributes"]}
    return {"ugr": 8.0 * math.log10(0.25 / lb * total), "terms": terms, "warnings": warns}


def flux_correction(lamp_lumens: float) -> float:
    """UGR correction for total lamp flux relative to the 1000 lm table basis: 8 log10(Phi/1000) (SLL eq. 12.3)."""
    return 8.0 * math.log10(lamp_lumens / 1000.0)


# ------------------------------------------------------------------ published reference data

# SLL Code Table 12.6 (printed p. 198), "Tabulated values of correction factor": lamp flux -> correction (as printed).
SLL_T12_6 = {100: -8.0, 200: -5.6, 300: -4.2, 400: -3.2, 500: -2.4, 600: -1.8, 700: -1.2, 800: -0.8, 900: -0.4,
             1000: 0.0, 1100: 0.3, 1200: 0.6, 1300: 0.9, 1400: 1.2, 1500: 1.4, 1600: 1.6, 1700: 1.8, 1800: 2.0,
             1900: 2.2, 2000: 2.4, 2100: 2.6, 2200: 2.7, 2300: 2.9, 2400: 3.0, 2500: 3.2, 2600: 3.3, 2700: 3.5,
             2800: 3.6, 2900: 3.7, 3000: 3.8, 3100: 3.9, 3200: 4.0, 3300: 4.1, 3400: 4.3, 3500: 4.4, 3600: 4.5,
             3700: 4.5, 3800: 4.6, 3900: 4.7, 4000: 4.8, 4100: 4.9, 4200: 5.0, 4300: 5.1, 4400: 5.1, 4500: 5.2,
             4600: 5.3, 4700: 5.4, 4800: 5.4, 4900: 5.5}

# SLL Code Table 12.10 (printed pp. 210-211), standard array, H = 2 m: (xT/H, yR/H) -> K. 27 cells transcribed.
SLL_T12_10_K = {
    (0.5, 1.5): 0.00412, (0.5, 2.5): 0.00541, (0.5, 3.5): 0.00473, (0.5, 4.5): 0.00386, (0.5, 5.5): 0.00308,
    (0.5, 6.5): 0.00243, (0.5, 7.5): 0.00197, (0.5, 8.5): 0.00163, (0.5, 9.5): 0.00137,
    (1.5, 1.5): 0.00155, (1.5, 2.5): 0.00294, (1.5, 3.5): 0.00329, (1.5, 4.5): 0.00292, (1.5, 5.5): 0.00249,
    (1.5, 6.5): 0.00209, (1.5, 7.5): 0.00177, (1.5, 8.5): 0.00150,
    (2.5, 4.5): 0.00183, (2.5, 5.5): 0.00176, (2.5, 6.5): 0.00159, (2.5, 7.5): 0.00140, (2.5, 8.5): 0.00124,
    (3.5, 4.5): 0.00105, (3.5, 5.5): 0.00115, (3.5, 6.5): 0.00113, (3.5, 7.5): 0.00106, (3.5, 8.5): 0.00099,
}


def position_index_vs_sll_table_12_10(H: float = 2.0) -> list[dict]:
    """Compare K = pi/(4 p^2 D^2) computed from our Guth index with the published K, cell by cell."""
    rows = []
    for (xt, yr), k_pub in SLL_T12_10_K.items():
        x, y = xt * H, yr * H
        D = math.sqrt(x * x + y * y + H * H)
        sigma = math.degrees(math.acos(y / D))
        tau = math.degrees(math.atan2(x, H))
        p = guth_position_index(sigma, tau)
        k = math.pi / (4 * p * p * D * D)
        rows.append({"xT_H": xt, "yR_H": yr, "K_published": k_pub, "K_computed": k, "rel_err": k / k_pub - 1,
                     "p": p, "sigma": sigma, "tau": tau})
    return rows
