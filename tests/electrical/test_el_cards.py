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


def test_disconnection_and_curves_in_snapshots():
    raw = snap("eig_fig_F13_F19_raw.txt")
    for r in data.table("disconnection_s")["rows"]:
        assert f"{r['tn']:g}" in raw and f"{r['tt']:g}" in raw
    cb = snap("eig_cb_characteristics.txt")
    assert "type B 3 In ≤ Im ≤ 5 In" in cb and "type C 5 In ≤ Im ≤ 10 In" in cb and "type D10 In ≤ Im ≤ 20 In" in cb
    tt = snap("eig_tt_principle.txt")
    for idn, ra in data.table("tt_ra_max_ohm")["rows"].items():
        assert f"{ra} Ω" in tt
