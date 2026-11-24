"""Static prevention of implicit render-host inputs in scene-build code.

Blender entry points run on the render host; asset_route_generator is an
explicit host-only generator. Asset intake accepts declared file paths and
sources owns the separate held-book store. These boundaries are named, not
an exemption for the entire concept package. The scene's library_root string
declares a downstream location and does not read it during scene build.
"""
import ast
from pathlib import Path

# Named host boundaries (lane HY): modules that locate render-host tools or assets BY DESIGN. They
# are fetchers, previews, CLIs with host defaults, or verification engines, not the villa scene
# build the guard protects. landscape/build/planting.py is the exception to say aloud: the decided
# garden (GI) reads the host Fab/Sketchfab store at build time and falls back to labelled stand-ins
# when it is absent, so an empty-HOME build differs in garden-* materials and the furniture/bed
# receipts refuse it (tests/test_asset_route_geometry.py builds the previous garden instead).
HOST_BOUNDARIES = {
    "drawings2d/section.py": "locates the Blender executable",
    "interior/fetch_lookalike.py": "downloads look-alike materials into the host library",
    "landscape/build/planting.py": "reads the host garden-asset store; stand-in fallback (see above)",
    "landscape/build/tools/fetch_gi_assets.py": "downloads garden assets into the host library",
    "landscape/critic/massing.py": "locates the Blender executable",
    "landscape/plants/atlas_panel.py": "preview of host Fab downloads",
    "landscape/plants/olive_preview.py": "preview of a host Fab download",
    "landscape/plants/tools/fab_manifest.py": "indexes the host Fab downloads",
    "landscape/plants/tools/fetch_plants.py": "downloads plant assets into the host store",
    "landscape/plants/verify_quotes.py": "host certificate bundle for source checks",
    "landscape/precedents/build.py": "host cache of fetched precedents",
    "landscape/site/analyse.py": "host weather file default for the site study",
    "lightverify/__main__.py": "locates the host Radiance install",
    "lightverify/scene_geom.py": "independent lighting verifier reads the host prop library",
    "lightverify/v5_engines.py": "locates the Blender executable",
    "model/geometry_sizes.py": "generator CLI; asset roots are host defaults, overridable",
}


def source_findings(source, relative_path):
    """Return implicit host-input sites; also used with frozen/mutated sources."""
    path = Path(relative_path).as_posix()
    if path.startswith("blender/") or path in ("asset_route_generator.py", "build_input_guard.py") or path in HOST_BOUNDARIES:
        return []
    tree = ast.parse(source.lstrip("\ufeff"))
    parents = {id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
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
            parent = parents.get(id(node))
            hash_lookup = (isinstance(parent, ast.Subscript) and parent.slice is node and
                isinstance(parent.value, ast.Subscript) and
                isinstance(parent.value.slice, ast.Constant) and parent.value.slice.value == 'source_sha256')
            if ".gltf" in value and path != "asset_intake.py" and not hash_lookup:
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
