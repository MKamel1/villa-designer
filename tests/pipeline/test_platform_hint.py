"""Lane P: a receipt-input mismatch off the recording platform names the cause; the guard still raises."""
import sys
from unittest import mock

from archpipe.model import passes as P


def test_hint_added_off_linux():
    exc = ValueError("furniture fixed-room inputs changed; repeat review (changed sections: meshes)")
    with mock.patch.object(sys, "platform", "win32"):
        out = P.platform_hint(exc, "furniture-stage2")
    assert out is not exc and isinstance(out, ValueError)
    assert "changed sections: meshes" in str(out) and "ai-workstation" in str(out)


def test_no_hint_on_linux_or_other_errors():
    exc = ValueError("furniture fixed-room inputs changed")
    with mock.patch.object(sys, "platform", "linux"):
        assert P.platform_hint(exc, "furniture-stage2") is exc
    other = ValueError("reviewed furniture room camera changed")
    with mock.patch.object(sys, "platform", "win32"):
        assert P.platform_hint(other, "furniture-stage2") is other


def test_run_stage_still_raises_off_linux():
    def boom(*a):
        raise ValueError("parents bed fixed-room inputs changed")
    fake = P.Pass("x", "furniture", "concept.furniture_stage2:apply", ("scene",), returns_scene=True)
    with mock.patch.object(P, "PASSES", (fake,)), mock.patch("archpipe.concept.furniture_stage2.apply", boom), \
            mock.patch.object(sys, "platform", "win32"):
        try:
            P.run_stage("furniture", {}, {})
        except ValueError as exc:
            assert "x:" in str(exc) and "ai-workstation" in str(exc)
        else:
            raise AssertionError("guard must still raise")


def test_build_fails_fast_without_luminaire_library(tmp_path):
    import pytest
    from archpipe.concept import villa_render
    with mock.patch("archpipe.luminaires.library.LIBRARY", tmp_path):
        with pytest.raises(FileNotFoundError, match="assets/user"):
            villa_render.build()
