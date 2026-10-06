"""Static prevention of implicit render-host inputs in scene-build code.

Blender entry points run on the render host; asset_route_generator is an
explicit host-only generator. Asset intake accepts declared file paths and
sources owns the separate held-book store. These boundaries are named, not
an exemption for the entire concept package. The scene's library_root string
declares a downstream location and does not read it during scene build.
"""
import ast
from pathlib import Path


def source_findings(source, relative_path):
    """Return implicit host-input sites; also used with frozen/mutated sources."""
    path = Path(relative_path).as_posix()
    if path.startswith("blender/") or path in ("asset_route_generator.py", "build_input_guard.py"):
        return []
    tree = ast.parse(source.lstrip("\ufeff"))
    docstrings = {id(node.value) for node in ast.walk(tree)
                  if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                  and isinstance(node.value.value, str)}
    findings = []
    for node in ast.walk(tree):
        reason = None
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
            if any("asset_route_generator" in name or "asset_triangles" in name for name in names):
                reason = "raw asset reader imported into build code"
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
            if name == "asset_triangles":
                reason = "raw asset triangles read at build time"
            elif (name == "home" or (name == "expanduser" and any(
                    isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                    and arg.value.startswith("~") for arg in node.args))) and path != "sources.py":
                reason = "implicit HOME input in build code"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            value = node.value.replace("\\", "/").lower()
            if ".gltf" in value and path != "asset_intake.py":
                reason = "raw glTF path in build code"
            elif ("assets/library" in value and node.value != "$HOME/archpipe/assets/library") or value in ("home", "userprofile"):
                if path != "sources.py":
                    reason = "implicit render-host library path in build code"
        if reason:
            findings.append(f"{path}:{node.lineno}: {reason}")
    return findings


def build_input_findings(source_root=None):
    root = Path(source_root) if source_root is not None else Path(__file__).resolve().parent
    return [finding for path in sorted(root.rglob("*.py"))
            for finding in source_findings(path.read_text(encoding="utf-8"), path.relative_to(root))]
