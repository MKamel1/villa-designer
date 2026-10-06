"""Freeze real all-vertex framing results for portable hull regression tests.

Only the explicitly supplied library is read. --check compares the tracked
fixture and hull-only consumer against fresh all-vertex results without writes.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shlex
import sys
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from archpipe.asset_route_generator import asset_triangles
from archpipe.asset_route_record import recorded_geometry
from scripts.villa_render_views import subject_mesh_frame_violations

PROOF = ROOT / "tests/fixtures/asset-framing-real.json"


def measure(library_root):
    library_root = Path(library_root)
    proof = dict(schema="asset-framing-proof/1", generator_command="PYTHONPATH=src " +
                 shlex.join(["python", "scripts/generate_asset_framing_proof.py", "--library-root", str(library_root)]), assets={})
    for asset in ("sf_frangipani", "sf_egg_chair"):
        model = library_root/"props"/asset/"model.gltf"
        source = model.read_bytes(); gltf = json.loads(source)
        triangles = asset_triangles(model)
        vertices = np.unique(triangles.reshape(-1,3),axis=0)
        _, hull, row = recorded_geometry(asset)
        if hashlib.sha256(source).hexdigest() != row["source_sha256"] or {
            b["uri"]: hashlib.sha256((model.parent/b["uri"]).read_bytes()).hexdigest()
            for b in gltf["buffers"] if not b["uri"].startswith("data:")
        } != row["buffer_sha256"]:
            raise ValueError(f"{asset}: source differs from tracked hull provenance")
        if not all(np.any(np.all(vertices==point,axis=1)) for point in hull):
            raise ValueError(f"{asset}: hull contains an invented point")
        scale = sum(row["scale_range"])/2
        yaw = math.radians(23); c,s = math.cos(yaw),math.sin(yaw)
        matrix = np.array([[c,s,0],[-s,c,0],[0,0,1]])
        placed = vertices*scale@matrix
        placed[:,2] -= row["walking_band_native"]["base"]*scale
        position = [0,0,0]
        position[:2] = (-((placed.min(axis=0)+placed.max(axis=0))/2)[:2]).tolist()
        placed += position
        z = float((placed[:,2].min()+placed[:,2].max())/2)
        view = dict(resolution=[1600,1000], camera=dict(position=[0,-10,z],target=[0,0,z],sensor_mm=36,lens_mm=24))
        projected = (placed[:,2]-z)*24/36/(placed[:,1]+10)
        prop = dict(id="proof-asset",asset=asset,position=position,scale=scale,rotation_deg=[0,0,23])
        cases = {}
        for name, change in [("in-frame", {}),
            ("clipped-top",dict(shift_y=float(projected.max()-.3125-.001))),
            ("clipped-bottom",dict(shift_y=float(projected.min()+.3125+.001))),
            ("clipped-horizontal",dict(shift_x=2)),
            ("behind-camera",dict(target=[0,-20,z]))]:
            camera = copy.deepcopy(view); camera["camera"].update(change)
            with patch("scripts.villa_render_views.subject_points",return_value=placed.tolist()):
                full = subject_mesh_frame_violations(camera,{},"proof-asset")
            subset = subject_mesh_frame_violations(camera,dict(meshes=[],props=[prop]),"proof-asset")
            if subset != full or bool(full) != (name != "in-frame"):
                raise ValueError(f"{asset}/{name}: hull and all-vertex framing disagree")
            cases[name] = dict(view=camera,all_vertex_result=full)
        proof["assets"][asset] = dict(source_sha256=row["source_sha256"],buffer_sha256=row["buffer_sha256"],
            full_vertex_count=len(vertices),prop=prop,cases=cases)
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root",required=True,type=Path)
    parser.add_argument("--check",action="store_true")
    args = parser.parse_args()
    result = measure(args.library_root)
    if args.check:
        if result["assets"] != json.loads(PROOF.read_text())["assets"]:
            raise SystemExit("tracked all-vertex proof is stale")
        print("Real frangipani and swing: hull and all-vertex results match all ten cameras")
    else:
        PROOF.write_text(json.dumps(result,indent=2)+"\n")
