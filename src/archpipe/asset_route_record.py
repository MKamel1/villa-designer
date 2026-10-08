"""Tracked geometry at declared precision; no render-library access.

Framing hull vertices are exact float64 triples in native scene axes.
Walking triangles intersect a recorded band above the asset's lowest point.
Route vertices use lossless float64 or indexed integers at declared precision.
Byte shuffling, index deltas and LZMA compression are lossless; placement outside the recorded
scale range or walking band fails closed.
"""
import base64
from functools import lru_cache
import hashlib
import json
import gzip
import zlib
from pathlib import Path
import lzma

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "knowledge/asset-route-geometry.json.gz"
MANIFEST = ROOT / "ops/workstation/library-manifest.json"
GENERATOR = ("PYTHONPATH=src python scripts/generate_asset_route_geometry.py "
             "--library-root /path/to/render-host/library --assets")
ENCODING = "route-indexed-declared-precision-framing-hull/3"
POLICY = ROOT / "knowledge/asset-route-policy.json"


def pack_array(blob, width):
    """Group matching byte positions before compression; width is bytes/value."""
    shuffled = np.frombuffer(blob, dtype="u1").reshape(-1, width).T.copy().tobytes()
    return base64.b64encode(lzma.compress(shuffled)).decode("ascii")


def unpack_array(payload, width):
    shuffled = lzma.decompress(base64.b64decode(payload, validate=True))
    return np.frombuffer(shuffled, dtype="u1").reshape(width, -1).T.copy().tobytes()


def geometry_digest(vertices_blob, indices_blob, hull_blob, row):
    """Bind the exact payload to the safety metadata that permits pruning."""
    metadata = {key: row[key] for key in ("walking_band_native", "scale_range",
                "scale_mode", "triangle_count_before", "triangle_count_after", "bounds_m",
                "coordinate_dtype", "native_step_m", "scene_error_bound_m", "hull_vertex_count")}
    return hashlib.sha256(vertices_blob + indices_blob + hull_blob +
                          json.dumps(metadata, sort_keys=True).encode()).hexdigest()


def read_record(path=RECORD):
    path = Path(path)
    blob = path.read_bytes()
    if path.suffix == ".gz":
        blob = gzip.decompress(blob)
    return json.loads(blob)


def write_record(path, record, max_bytes=None):
    path = Path(path)
    blob = (json.dumps(record, sort_keys=True, separators=(",", ":"))+"\n").encode()
    blob = gzip.compress(blob, compresslevel=9, mtime=0) if path.suffix == ".gz" else blob
    if max_bytes is not None and len(blob) >= max_bytes:
        raise ValueError(f"route record needs {len(blob)} bytes; budget is below {max_bytes} bytes; "
                         "improve storage without dropping walking triangles or exceeding declared precision")
    path.write_bytes(blob)


@lru_cache(maxsize=4)
def _documents(record_path, manifest_path, signatures):
    return (read_record(record_path),
            json.loads(Path(manifest_path).read_text(encoding="utf-8")))


@lru_cache(maxsize=64)
def _decode(asset, record_path, manifest_path, signatures):
    record, manifest = _documents(record_path, manifest_path, signatures)
    if record["schema"] != "asset-route-geometry/3":
        raise ValueError("unsupported record schema")
    row = record["assets"][asset]
    entries = [p for p in manifest["props"] if p["id"] == asset]
    if len(entries) != 1:
        raise ValueError("missing or duplicate manifest entry")
    entry = entries[0]
    source_hash = row["source_sha256"]
    if (len(source_hash) != 64 or source_hash != entry.get("source_sha256")
            or row["buffer_sha256"] != entry.get("geometry_buffer_sha256")):
        raise ValueError("stale source hashes")
    if row["encoding"] != ENCODING or not row["generator_command"] or not row["generated_at_utc"]:
        raise ValueError("invalid record provenance or encoding")
    dtype = row["coordinate_dtype"]
    if dtype not in ("<f8", "<i4"):
        raise ValueError("unsupported coordinate precision")
    vertices_blob = unpack_array(row["vertices"], np.dtype(dtype).itemsize)
    delta_blob = unpack_array(row["indices"], 4)
    indices_blob = np.cumsum(np.frombuffer(delta_blob, dtype="<i4"), dtype=np.int64).astype("<u4").tobytes()
    hull_blob = unpack_array(row["framing_hull_vertices"], 8)
    if geometry_digest(vertices_blob, indices_blob, hull_blob, row) != row["geometry_sha256"]:
        raise ValueError("corrupt geometry")
    vertices = np.frombuffer(vertices_blob, dtype=dtype).reshape(row["vertex_count"], 3)
    step = row["native_step_m"]
    if dtype == "<i4":
        vertices = vertices.astype(float)*step
    hull = np.frombuffer(hull_blob, dtype="<f8").reshape(row["hull_vertex_count"], 3)
    indices = np.frombuffer(indices_blob, dtype="<u4").reshape(row["triangle_count"], 3)
    triangles = vertices[indices]
    if not len(triangles) or not len(hull) or not np.isfinite(vertices).all() or not np.isfinite(hull).all():
        raise ValueError("empty or non-finite geometry")
    triangles.setflags(write=False)
    vertices.setflags(write=False)
    hull.setflags(write=False)
    band = row["walking_band_native"]
    minimum, maximum = row["scale_range"]
    if not (0 < minimum <= maximum and band["margin_m"] >= 0
            and band["height_m"] == 2.0
            and band["top"] == band["base"] + (2.0 + band["margin_m"]) / minimum
            and row["triangle_count_before"] >= row["triangle_count_after"] == len(triangles)
            and row["scale_mode"] in ("uniform", "axiswise")
            and np.all(triangles[:,:,2].min(axis=1) <= band["top"] + step/2)
            and float(hull[:,2].min()) == band["base"]
            and 0 <= row["scene_error_bound_m"] <= .001
            and ((dtype == "<f8" and step == row["scene_error_bound_m"] == 0)
                 or (dtype == "<i4" and step > 0 and row["scene_error_bound_m"] ==
                     np.sqrt(3)*step*maximum/2))):
        raise ValueError("invalid walking band")
    return triangles, hull, row


def recorded_geometry(asset, record_path=None, manifest_path=None):
    """Fail closed on missing, stale or corrupt build input, with a remedy."""
    record_path = Path(record_path if record_path is not None else RECORD)
    manifest_path = Path(manifest_path if manifest_path is not None else MANIFEST)
    try:
        signatures = tuple((p.stat().st_mtime_ns, p.stat().st_size)
                           for p in (record_path, manifest_path))
        return _decode(asset, str(record_path), str(manifest_path), signatures)
    except (OSError, EOFError, OverflowError, ValueError, KeyError, TypeError, IndexError, lzma.LZMAError, zlib.error) as error:
        raise ValueError(f"asset {asset}: missing, stale or invalid tracked route geometry; "
                         f"on the render host run {GENERATOR} {asset} ({error})") from None


def recorded_triangles(asset, record_path=None, manifest_path=None):
    return recorded_geometry(asset, record_path, manifest_path)[0]
