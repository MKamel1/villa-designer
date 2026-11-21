import hashlib, json
from pathlib import Path
from archpipe.luminaires import lp_erco, v10

ROOT = Path(__file__).resolve().parents[2]


def test_stored_files_match_source_sha():
    for sj in (ROOT / "knowledge/lighting-products").glob("*/*/source.json"):
        for f in json.loads(sj.read_text())["files"].values():
            assert hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() == f["sha256"], f["path"]


def test_erco_pass_and_known_beam_fail():
    c = json.loads((ROOT / "knowledge/lighting-products/candidates.json").read_text())
    by = {p["code"]: p for k in c["kinds"].values() for p in k}
    assert by["41321"]["v10_status"] == "pass" and by["A9001547"]["v10_status"] == "partial"


def test_wrong_published_value_fails():
    ies = ROOT / "knowledge/lighting-products/erco/41321/erco-41321-000-en-ies.ies"
    bad = v10.check_product(ies, stated_lumens=1065, points=[v10.Point("imax", 1300)])
    assert bad["status"] == "fail"
