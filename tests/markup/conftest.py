import json
import shutil
from pathlib import Path

import pytest

from archpipe import model
from archpipe.documents import plans, sheetset
from archpipe.drawings2d import variants
from archpipe.markup import frames as F

try:
    import pymupdf as fitz
except ImportError:
    import fitz


@pytest.fixture(scope="session")
def els():
    return model.load("D1")


@pytest.fixture(scope="session")
def sheets(els, tmp_path_factory):
    """Real D1 plan sheets rendered by RV2's own code (A-111 furnished, A-121 lighting, A-101 GA)."""
    d = tmp_path_factory.mktemp("sheets")
    spec = sheetset.build("D1", elements=els)
    spec["levels"] = json.loads(Path(model.api.snapshot_path("D1")).read_text(encoding="utf-8")).get("levels", {})
    for s in spec["sheets"]:
        if s["no"] in ("A-101", "A-111", "A-121"):
            plans.render_plan(els, spec, s, d / ("%s-plan" % s["no"]), formats=("pdf", "png"), layers=variants.LAYERS[s["variant"]],
                              extras=variants.extras_for(s["variant"]))
    return d


@pytest.fixture(scope="session")
def frames_data():
    return F.record("D1")


@pytest.fixture
def root(tmp_path):
    return tmp_path / "requests"
