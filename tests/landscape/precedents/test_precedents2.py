import hashlib, re
from pathlib import Path
import pytest
from archpipe.landscape import precedents as P
from archpipe.landscape.precedents import targets2 as T

ROOT = Path(__file__).resolve().parents[3]


def test_targets2_hash_recorded_and_content_intact():
    doc = (ROOT / "docs/lanes/LDP.md").read_text()
    sha = re.search(r"targets-2.json`, frozen .*?sha256 = ([0-9a-f]{64})", doc).group(1)
    f = P.DATA / "targets-2.json"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == sha
    assert P.check_frozen(f, sha) == []


def test_first_targets_untouched():
    doc = (ROOT / "docs/lanes/LDP.md").read_text()
    sha = re.search(r"sha256 = ([0-9a-f]{64})", doc).group(1)
    assert P.check_frozen(expected_file_sha256=sha) == []


def test_freeze2_refuses_overwrite():
    with pytest.raises(FileExistsError):
        T.freeze2("2099-01-01")


def test_new_sets_valid_and_unscaled_garden_has_no_plan_numerics():
    for s in ("south2", "north2"):
        gs = P.load(s)
        assert P.validate_set(gs) == []
        for g in gs:
            if not g["scaled_plan"]:
                for ps in g["passes"].values():
                    assert not set(ps) & set(P.PLAN_METRICS)


def test_thin_groups_stay_gap_and_every_range_has_n_ge_min():
    t = T.build_targets_2("x")
    assert t["groups"]["south2_only"]["metrics"]["trees_per_100m2"]["status"] == "GAP"  # negative: n too small
    for grp in t["groups"].values():
        for r in grp["metrics"].values():
            if r["status"] == "range":
                assert r["n_usable"] >= P.MIN_N
