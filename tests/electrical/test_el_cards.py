"""Evidence checks: every sourced/std card quote and every table cell exists in the committed source snapshot."""
import json
import re
from pathlib import Path

import pytest

from archpipe.electrical import data

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "knowledge" / "electrical" / "source_snapshots"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ").replace("|", " ")).strip()


def snap(name: str) -> str:
    return norm((SNAP / name).read_text(encoding="utf-8"))


def _first_snapshot(c) -> list[str]:
    return [p.strip() for p in c.url_or_path.split(" ; ") if p.strip().startswith("knowledge/electrical/source_snapshots/")]


def test_every_card_has_valid_status_and_policy_cards_are_unquoted():
    for c in data.cards().values():
        assert c.status in ("sourced", "std", "policy", "unverified")
        if c.status in ("policy", "unverified"):
            assert c.quote == ""


@pytest.mark.parametrize("cid", [c.id for c in data.cards().values() if c.status in ("sourced", "std")])
def test_quote_is_verbatim_in_snapshot(cid):
    c = data.card(cid)
    assert c.quote.strip(), cid
    files = _first_snapshot(c)
    assert files, f"{cid} has no snapshot path"
    q = norm(c.quote)
    assert any(q in snap(Path(f).name) for f in files), f"{cid}: quote not found in {files}"


def _row_text(cells) -> str:
    return " ".join(str(x) for x in cells)


def test_g20_every_cell_matches_snapshot():
    text = snap("eig_general_method_cable_sizing.txt")
    t = data.table("ampacity_iec_b524_pvc_3loaded")
    n = 0
    for mat, rows in t["rows"].items():
        for csa, cols in rows.items():
            vals = [cols[m] for m in t["methods"]]
            s = " ".join("" if v is None else (f"{v:g}") for v in vals)
            assert re.sub(r"\s+", " ", s).strip() in text.replace("  ", " "), (mat, csa, s)
            n += len(vals)
    assert n > 200


def _src_rows(name: str, start: str, stop: str) -> dict:
    """first 'ROW: <key> | numbers...' line per key between two markers, as float lists (blank/'-' -> None)."""
    raw = (SNAP / name).read_text(encoding="utf-8").replace(" ", " ")
    seg = raw[raw.index(start):]
    seg = seg[: seg.index(stop)] if stop in seg else seg
    out = {}
    for ln in seg.splitlines():
        if ln.startswith("ROW: "):
            cells = [c.strip() for c in ln[5:].split("|")]
            if re.fullmatch(r"\d+(\.\d+)?", cells[0]) and cells[0] not in out:
                out[cells[0]] = [None if c in ("", "-") else float(c) for c in cells[1:]]
    return out


def test_g21_every_cell_matches_snapshot():
    src = _src_rows("eig_simplified_cable_sizing.txt", "Fig. G21", "Aluminium")
    ours = data.table("ampacity_iec_c521_simplified_cu_columns")["rows"]
    for csa, vals in ours.items():
        assert src[csa] == vals, csa


def test_g30_every_cell_matches_snapshot():
    src = _src_rows("eig_voltage_drop_steady.txt", "Fig. G30", "Examples")
    for csa, cols in data.table("voltage_drop_g30_v_per_a_km_cu")["rows"].items():
        assert src[csa][:6] == list(cols.values()), csa


def test_whitfield_tables_match_snapshot():
    text = snap("whitfield_Book_4_3_9_htm.txt").replace("18..0", "18.0")
    for name in ("bs7671_1992_whitfield_t46_single_core_pvc", "bs7671_1992_whitfield_t47_multicore_pvc"):
        for csa, vals in data.table(name)["rows"].items():
            s = f"{csa} " + " ".join(f"{v:.1f}" for v in vals)
            assert s in text, (name, s)


def test_correction_tables_match_snapshot():
    g = snap("eig_general_method_cable_sizing.txt")
    ca = _src_rows("eig_general_method_cable_sizing.txt", "Fig. G12", "Fig. G13")
    for t, cols in data.table("ca_air_iec_b5214")["rows"].items():
        assert ca[t][:2] == cols, t
    bunched = (1.00, 0.80, 0.70, 0.65, 0.60, 0.57, 0.54, 0.52, 0.50, 0.45, 0.41, 0.38)
    cg = data.table("cg_iec_b5217_bunched")["rows"]
    # the source also lists 5, 7 (all present) — compare the printed row with ours
    src_row = " ".join(f"{cg[k]:.2f}" for k in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "12", "16", "20"))
    assert src_row == " ".join(f"{v:.2f}" for v in bunched) and src_row in g
    ci = snap("whitfield_Book_4_3_6_htm.txt")
    for mm, f in data.table("ci_whitfield_t45")["rows"].items():
        assert (f"{mm} or more {f:.2f}" if mm == "500" else f"{mm} {f:.2f}") in ci, (mm, f)


def _lines(name):
    return [l.strip() for l in (SNAP / name).read_text(encoding="utf-8").replace(" ", " ").splitlines()]


def test_disconnection_times_match_snapshot_rows():
    tt = " ".join(_lines("eig_tt_practical.txt"))
    tn = " ".join(_lines("eig_tn_disconnection.txt"))
    for r in data.table("disconnection_s")["rows"]:
        lo, hi = r["uo_gt"], r["uo_le"]
        band = f"{lo} < Uo ≤ {hi} | " if hi < 1e8 else f"Uo > {lo} | "
        assert f"{band}{r['tt']:g}" in tt, band
        assert f"{band}{r['tn']:g}" in tn, band


def test_curves_rcd_and_ra_in_snapshots():
    cb = snap("eig_cb_characteristics.txt")
    assert "type B 3 In ≤ Im ≤ 5 In" in cb and "type C 5 In ≤ Im ≤ 10 In" in cb and "type D10 In ≤ Im ≤ 20 In" in cb
    tt = snap("eig_tt_principle.txt")
    for idn, ra in data.table("tt_ra_max_ohm")["rows"].items():
        assert f"{ra} Ω" in tt
    f14 = {l.split(" | ", 1)[0]: l for l in _lines("eig_tt_practical.txt") if l.startswith("ROW: Domestic")}
    assert "ROW: Domestic | Instantaneous | 0.3 | 0.15 | 0.04 | 0.04" in f14.values()
    rows = data.table("rcd_max_time_s_domestic_instantaneous")["rows"]
    assert (rows["1"], rows["2"], rows["5"]) == (0.3, 0.15, 0.04)


def test_voltage_drop_limits_and_a11_match_snapshot():
    mx = _lines("eig_max_voltage_drop.txt")
    t = data.table("voltage_drop_limits_pct")
    assert f"ROW: A low-voltage service connection from a LV public power distribution network | {t['lighting']:g}% | {t['other']:g}%" in mx
    dv = _lines("eig_diversity.txt")
    for lo, hi, ks in data.table("diversity_eig_a11_apartments")["rows"]:
        label = f"{lo} to {hi}" if hi < 1e5 else f"{lo} and more"
        assert f"ROW: {label} | {ks:g}" in dv, label


def _render(rule: dict) -> str:
    k = rule["kind"]
    if k == "total_pct":
        return "100%" if rule["p"] == 1.0 else f"{round(rule['p'] * 100)}% total demand"
    if k == "first_plus":
        return f"100% up to {rule['first']} A + {round(rule['rest'] * 100)}% balance"
    if k == "cooker":
        return f"{rule['first']} A + {round(rule['rest'] * 100)}% balance + {rule['socket_a']} A for socket"
    a, b, c = (round(x * 100) for x in rule["w"])
    if b == c:
        return f"100%X + {b}%(Y+Z)"
    return f"100%X + {b}%Y + {c}%Z"


def test_whitfield_table_6_2_every_rule_matches_snapshot():
    lines = [l.strip(" |") for l in _lines("whitfield_Figures_Tab6_2_htm.txt")]
    lines = [l for l in lines if l]
    labels = {"lighting": "Lighting", "heating_power": "Heating and power", "cooker": "Cookers", "motors": "Motors (but not lifts)",
              "inst_wh": "Instantaneous water heaters", "thermo_wh": "Thermostatic water heaters", "standard": "Standard circuits",
              "sockets": "Sockets and stationary equip."}
    cols = ["household", "shop", "hotel"]
    t = data.table("diversity_whitfield_t62")["premises"]
    checked = 0
    for cat, label in labels.items():
        i = lines.index(label)
        got = lines[i + 1:i + 4]
        if cat == "motors":                       # household cell is blank in the source
            got = [None] + lines[i + 1:i + 3]
        for col, text in zip(cols, got):
            if text is None:
                assert cat not in t[col]
                continue
            assert _render(t[col][cat]) == text, (cat, col, text)
            checked += 1
    assert checked == 23


def test_reference_case_expected_values_appear_in_their_snapshots():
    from archpipe.electrical import reference_cases
    wanted = {"EL-EX-WHIT-6.1": ["486.2", "162 A"], "EL-EX-WHIT-6.2": ["29.5"], "EL-EX-WHIT-4.1": ["32.4", "43 A"], "EL-EX-WHIT-4.5": ["1.28", "105m"],
              "EL-EX-EIG-A12": ["69 kVA", "100A"], "EL-EX-EIG-WEX": ["0.73", "2 x 240", "2 x 120", "1 x 95", "0.12", "0.47", "0.13"],
              "EL-EX-EIG-G32": ["10.1", "4.4"]}
    for cid, toks in wanted.items():
        text = " ".join(snap(Path(f).name) for f in _first_snapshot(data.card(cid)))
        for t in toks:
            assert t in text or t.replace(" ", "") in text.replace(" ", ""), (cid, t)
    assert {rc.card for rc in reference_cases.run()} <= set(wanted)
