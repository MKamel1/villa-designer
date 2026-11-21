"""Cable sizing (EA5) and voltage drop (EA6): Ib <= In <= Iz = I_tab * correction factors.

Correction factors are applied per route *segment* (a stretch of the route with its own ambient,
grouping and thermal insulation). Within a segment the factors multiply; the cable must satisfy the
worst segment (method "segments", the method of the Whitfield worked example 4.1). Method
"product" multiplies the worst Ca, Cg and Ci of the whole route (more conservative).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import data

SQRT3 = math.sqrt(3.0)


@dataclass
class Segment:
    name: str
    length_m: float = 0.0
    ambient_c: float = 30.0
    group_circuits: int = 1        # circuits or multicore cables bunched together here
    insulation_mm: float = 0.0     # length buried in thermal insulation


@dataclass
class TableSpec:
    """Which ampacity table to read. kind: iec_b524 (method, material) | whit_t46/whit_t47 (col) | iec_c521_F."""
    kind: str
    method: str = "C"
    material: str = "Cu"
    col: str = "in_insulation_2"
    insulation: str = "PVC"        # PVC | XLPE_EPR (for Ca column)


def _key(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _csa_key(csa: float, rows: dict) -> str | None:
    for k in (_key(csa), f"{csa:.1f}", str(csa)):
        if k in rows:
            return k
    return None


def ampacity(spec: TableSpec, csa: float) -> float | None:
    """Tabulated current for one circuit at the reference ambient, or None if the table has no cell."""
    if spec.kind == "iec_b524":
        rows = data.table("ampacity_iec_b524_pvc_3loaded")["rows"][spec.material]
        k = _csa_key(csa, rows)
        return None if k is None else rows[k].get(spec.method)
    if spec.kind in ("whit_t46", "whit_t47"):
        t = data.table("bs7671_1992_whitfield_t46_single_core_pvc" if spec.kind == "whit_t46"
                       else "bs7671_1992_whitfield_t47_multicore_pvc")
        k = _csa_key(csa, t["rows"])
        return None if k is None else t["rows"][k][t["columns"].index(spec.col)]
    if spec.kind == "iec_c521_F":
        rows = data.table("ampacity_iec_c521_simplified_cu_F_3pvc")["rows"]
        k = _csa_key(csa, rows)
        return None if k is None else rows[k]
    raise ValueError(spec.kind)


def table_card(spec: TableSpec) -> str:
    return {"iec_b524": "EL-IEC-B524", "whit_t46": "EL-WHIT-T47", "whit_t47": "EL-WHIT-T47",
            "iec_c521_F": "EL-IEC-C521"}[spec.kind]


def ca_factor(ambient_c: float, insulation: str = "PVC") -> float:
    if ambient_c <= 30:
        return 1.0
    rows = data.table("ca_air_iec_b5214")["rows"]
    keys = sorted(int(k) for k in rows)
    k = next((x for x in keys if x >= ambient_c), None)          # next hotter row: conservative
    if k is None:
        return 0.0                                               # hotter than the table: no rating
    v = rows[str(k)][0 if insulation == "PVC" else 1]
    return 0.0 if v is None else v                               # source prints '-': insulation cannot be used there


def cg_factor(n: int) -> float:
    if n <= 1:
        return 1.0
    rows = data.table("cg_iec_b5217_bunched")["rows"]
    keys = sorted(int(k) for k in rows)
    k = next((x for x in keys if x >= n), keys[-1])
    return rows[str(k)]


def ci_factor(insulation_mm: float) -> float:
    if insulation_mm <= 0:
        return 1.0
    rows = data.table("ci_whitfield_t45")["rows"]
    keys = sorted(int(k) for k in rows)
    k = next((x for x in keys if x >= insulation_mm), keys[-1])
    return rows[str(k)]


def segment_factors(seg: Segment, insulation: str = "PVC") -> dict:
    ca, cg, ci = ca_factor(seg.ambient_c, insulation), cg_factor(seg.group_circuits), ci_factor(seg.insulation_mm)
    return {"Ca": ca, "Cg": cg, "Ci": ci, "product": ca * cg * ci}


def route_factor(segments: list[Segment], insulation: str = "PVC", combine: str = "segments") -> tuple[float, dict]:
    if not segments:
        return 1.0, {}
    per = {s.name: segment_factors(s, insulation) for s in segments}
    if combine == "segments":
        worst = min(per, key=lambda n: per[n]["product"])
        return per[worst]["product"], {"combine": combine, "worst_segment": worst, "segments": per}
    ca = min(v["Ca"] for v in per.values()); cg = min(v["Cg"] for v in per.values()); ci = min(v["Ci"] for v in per.values())
    return ca * cg * ci, {"combine": combine, "segments": per, "Ca": ca, "Cg": cg, "Ci": ci}


@dataclass
class SizeResult:
    ok: bool
    csa_mm2: float | None
    parallel: int
    i_tab_a: float | None
    factor: float
    iz_a: float | None            # corrected capacity of the whole circuit (parallel x tabulated x factor)
    ib_a: float
    in_a: float
    detail: dict = field(default_factory=dict)
    message: str = ""
    card_ids: tuple[str, ...] = ()


def size_cable(ib_a: float, in_a: float, segments: list[Segment], spec: TableSpec, *, parallel: int = 1,
               min_csa: float = 1.5, combine: str = "segments", extra_ok=None) -> SizeResult:
    """Smallest csa with Ib <= In <= Iz. `extra_ok(csa) -> bool` adds further limits (e.g. voltage drop)."""
    if in_a < ib_a - 1e-9:
        return SizeResult(False, None, parallel, None, 1.0, None, ib_a, in_a,
                          message=f"In {in_a} A below Ib {ib_a:.2f} A", card_ids=())
    factor, det = route_factor(segments, spec.insulation, combine)
    cards = (table_card(spec), "EL-IEC-B5214-CA", "EL-IEC-B5217-CG", "EL-WHIT-T45-CI")
    for csa in data.table("csa_ladder_mm2"):
        if csa < min_csa:
            continue
        i_tab = ampacity(spec, csa)
        if i_tab is None:
            continue
        iz = parallel * i_tab * factor
        if iz + 1e-9 >= in_a and (extra_ok is None or extra_ok(csa)):
            return SizeResult(True, csa, parallel, i_tab, factor, iz, ib_a, in_a, det,
                              f"Ib {ib_a:.2f} <= In {in_a:g} <= Iz {iz:.1f} A ({parallel} x {i_tab:g} A x {factor:.3f})", cards)
    return SizeResult(False, None, parallel, None, factor, None, ib_a, in_a, det,
                      "no tabulated size satisfies In <= Iz (and extra limits)", cards)


# ---- voltage drop ------------------------------------------------------------------------------
def _g30(csa: float) -> dict | None:
    rows = data.table("voltage_drop_g30_v_per_a_km_cu")["rows"]
    k = _csa_key(csa, rows)
    return None if k is None else rows[k]


def mv_per_a_m(csa: float, system: str, kind: str = "motor", source: str = "auto") -> tuple[float, str]:
    """(mV/A/m, card id). 1ph <= 16 mm2 uses the BS 7671:1992 multicore column (Whitfield T4.7), else Fig G30.
    G30 columns: lighting cos phi 1, motor cos phi 0.8 (conservative for LED, pf 0.9)."""
    if system == "1ph" and csa <= 16 and source == "auto":
        t = data.table("bs7671_1992_whitfield_t47_multicore_pvc")
        k = _csa_key(csa, t["rows"])
        if k is not None:
            return t["rows"][k][t["columns"].index("vd_2_mv_a_m")], "EL-WHIT-T47"
    g = _g30(csa)
    if g is None:
        raise KeyError(f"no voltage-drop cell for {csa} mm2")
    col = ("sp_" if system == "1ph" else "tp_") + ("light_1" if kind == "light" else "motor_08")
    return g[col], "EL-EIG-G30-VD"


def vd_volts(csa: float, ib_a: float, length_m: float, system: str, kind: str = "motor", parallel: int = 1,
             k_override: float | None = None, source: str = "auto") -> float:
    """Voltage drop in volts: phase-to-phase for 3ph, line-neutral for 1ph. Current per conductor = Ib / parallel."""
    k = k_override if k_override is not None else mv_per_a_m(csa, system, kind, source)[0]
    return k * (ib_a / parallel) * length_m / 1000.0


def vd_percent(v_drop: float, system: str, v_phase: float) -> float:
    return 100.0 * v_drop / (v_phase * SQRT3 if system == "3ph" else v_phase)


def phase_equivalent(v_drop: float, system: str) -> float:
    """3ph phase-to-phase drop -> phase-to-neutral so it can be added to a single-phase final circuit."""
    return v_drop / SQRT3 if system == "3ph" else v_drop


def vd_limit_pct(kind: str) -> float:
    t = data.table("voltage_drop_limits_pct")
    return t["lighting"] if kind == "lighting" else t["other"]
