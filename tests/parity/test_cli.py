from archpipe.parity import run_d1


def test_missing_scene_exits_2(tmp_path, capsys):
    assert run_d1.main(["--scene", str(tmp_path / "none.json"), "--ifc", str(tmp_path / "none.ifc")]) == 2
    assert "missing scene input" in capsys.readouterr().err


def test_missing_ifc_exits_2(tmp_path, capsys):
    s = tmp_path / "s.json"; s.write_text("{}")
    assert run_d1.main(["--scene", str(s), "--ifc", str(tmp_path / "none.ifc")]) == 2
    assert "missing ifc input" in capsys.readouterr().err
