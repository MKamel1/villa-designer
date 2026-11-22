"""Principle 2: the parity checks must not reuse the generators' geometry. Fails if src/archpipe/parity imports them."""
import ast
from pathlib import Path

PARITY = Path(__file__).resolve().parents[2] / "src" / "archpipe" / "parity"
FORBIDDEN = ("revit_spec", "villa_daylight", "villa_render", "villa_env", "model.export", "model.geometry_", "model.spec_source",
             "model.fit_source", "model.passes", "geometry_net", "geometry_complete", "geometry_sizes", "geometry_doors",
             "geometry_existing", "concept")


def imports(path):
    tree = ast.parse(path.read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                yield a.name
        elif isinstance(n, ast.ImportFrom):
            base = ("." * n.level) + (n.module or "")
            yield base
            for a in n.names:
                yield f"{base}.{a.name}"


def test_no_parity_module_imports_a_generator():
    bad = []
    for p in sorted(PARITY.glob("*.py")):
        for name in imports(p):
            if any(tok in name for tok in FORBIDDEN):
                bad.append((p.name, name))
    assert not bad, f"parity checks must stay independent of the generators: {bad}"


def test_the_guard_itself_fails_on_a_forbidden_import(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("from archpipe.concept import revit_spec\n")
    assert any("revit_spec" in n for n in imports(f))
