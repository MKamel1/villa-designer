"""Measure render-host assets into compact build input at declared precision.

Run with PYTHONPATH=src. Only the output record and manifest are written;
the asset library is read-only. Regenerating selected assets preserves others.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex

import numpy as np

from archpipe.asset_route_generator import asset_triangles
from archpipe.asset_route_record import ENCODING, MANIFEST, RECORD, POLICY, pack_array, geometry_digest, read_record, write_record
from archpipe.asset_framing_hull import framing_hull_vertices


def generate(library_root, assets, record_path=RECORD, manifest_path=MANIFEST, policy_path=POLICY):
    library_root, record_path, manifest_path = map(Path, (library_root, record_path, manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    record = (read_record(record_path) if record_path.exists()
              else dict(schema="asset-route-geometry/3", assets={}))
    if record["schema"] != "asset-route-geometry/3":
        if set(record["assets"]) - set(assets):
            raise ValueError("schema migration requires regenerating every recorded asset")
        record = dict(schema="asset-route-geometry/3", assets={})
    command = shlex.join(["python", "scripts/generate_asset_route_geometry.py",
                          "--library-root", str(library_root), "--policy", str(policy_path),
                          "--assets", *sorted(set(assets))])
    for asset in sorted(set(assets)):
        if Path(asset).name != asset or asset in (".", ".."):
            raise ValueError(f"invalid asset id: {asset}")
        entries = [p for p in manifest["props"] if p["id"] == asset]
        if len(entries) != 1:
            raise ValueError(f"asset {asset}: missing or duplicate manifest entry")
        model = library_root / "props" / asset / "model.gltf"
        source = model.read_bytes()
        gltf = json.loads(source)
        source_hash = hashlib.sha256(source).hexdigest()
        buffer_hashes = {b["uri"]: hashlib.sha256((model.parent / b["uri"]).read_bytes()).hexdigest()
                         for b in gltf["buffers"] if not b["uri"].startswith("data:")}
        triangles = asset_triangles(model)
        settings = policy["assets"][asset]
        minimum, maximum = settings["scale_range"]
        margin = policy["margin_m"]
        if not (0 < minimum <= maximum and margin >= 0):
            raise ValueError(f"asset {asset}: invalid scale range or margin")
        base = float(triangles[:,:,2].min())
        top = base + (2.0 + margin) / minimum
        # Framing reduction is independent of the exact walking topology.
        hull = framing_hull_vertices(triangles.reshape(-1,3))
        before = len(triangles)
        keep = triangles[:,:,2].min(axis=1) <= top
        vertices, first, inverse = np.unique(triangles[keep].reshape(-1,3), axis=0,
                                             return_index=True, return_inverse=True)
        order = np.argsort(first)
        remap = np.empty(len(order), dtype=int); remap[order] = np.arange(len(order))
        vertices = vertices[order]
        indices = remap[inverse].reshape(-1,3)
        # Numbering follows first use, retaining face order/winding and separate
        # original vertices even when their integer coordinates coincide.
        scene_step = settings.get("route_scene_step_m", 0)
        step = scene_step / maximum
        if not (0 <= scene_step <= .001):
            raise ValueError(f"asset {asset}: route precision exceeds one millimetre")
        dtype = "<i4" if step else "<f8"
        encoded = np.rint(vertices/step) if step else vertices
        if step and np.any(np.abs(encoded) > np.iinfo(np.int32).max):
            raise ValueError(f"asset {asset}: integer route coordinates overflow")
        vertex_blob = encoded.astype(dtype).tobytes()
        hull_blob = hull.astype("<f8").tobytes()
        index_blob = indices.astype("<u4").tobytes()
        delta_blob = np.diff(indices.ravel().astype(np.int64), prepend=0).astype("<i4").tobytes()
        row = dict(source_sha256=source_hash, buffer_sha256=buffer_hashes,
                   generator_command="PYTHONPATH=src " + command,
                   generated_at_utc=datetime.now(timezone.utc).isoformat(),
                   encoding=ENCODING, vertex_count=len(vertices), triangle_count=int(keep.sum()),
                   coordinate_dtype=dtype, native_step_m=step,
                   scene_error_bound_m=np.sqrt(3)*step*maximum/2,
                   hull_vertex_count=len(hull),
                   triangle_count_before=before, triangle_count_after=int(keep.sum()),
                   scale_range=[minimum, maximum], scale_mode=settings["scale_mode"],
                   walking_band_native=dict(base=base, top=top, height_m=2.0, margin_m=margin,
                                            margin_native=margin/minimum),
                   scale_basis=settings["basis"],
                   framing_vertices_reason="Unrounded 3D convex-hull vertices of full-height geometry preserve containment in every convex view frustum and plan extrema; route faces use their independent indexed vertex list",
                   scene_axes="native x, negative native z, native y; metres at scale one",
                   bounds_m=dict(min=triangles.min(axis=(0, 1)).tolist(), max=triangles.max(axis=(0, 1)).tolist()),
                   vertices=pack_array(vertex_blob, np.dtype(dtype).itemsize), indices=pack_array(delta_blob, 4),
                   framing_hull_vertices=pack_array(hull_blob, 8))
        row["geometry_sha256"] = geometry_digest(vertex_blob, index_blob, hull_blob, row)
        record["assets"][asset] = row
        entries[0]["source_sha256"] = source_hash
        entries[0]["geometry_buffer_sha256"] = buffer_hashes
        print(f"{asset}: {before} -> {keep.sum()} triangles, {len(vertices)} route vertices, "
              f"{len(hull)} framing vertices, error <= {row['scene_error_bound_m']*1000:.6f} mm")
    write_record(record_path, record, max_bytes=1500000)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"record: {record_path.stat().st_size} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root", required=True, type=Path)
    parser.add_argument("--assets", required=True, nargs="+")
    parser.add_argument("--policy", type=Path, default=POLICY)
    args = parser.parse_args()
    generate(args.library_root, args.assets, policy_path=args.policy)
