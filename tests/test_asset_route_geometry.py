"""Real absent-library reproduction and portable tracked-geometry proofs."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from archpipe import asset_route_record as records
from archpipe.build_input_guard import build_input_findings, source_findings
from archpipe.concept import route_geometry as geometry, villa_render as VR

ROOT = Path(__file__).resolve().parents[1]


class AssetRouteGeometry(unittest.TestCase):
    def test_frozen_ec0bc39_fails_with_empty_home_and_scene_now_builds(self):
        frozen_path = ROOT / "tests/fixtures/route_geometry_ec0bc39.py"
        spec = importlib.util.spec_from_file_location("frozen_route_geometry", frozen_path)
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        prop = json.loads((ROOT / "tests/fixtures/garden-g2-tree-centred-before.json").read_text())
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, HOME=home):
            self.assertFalse((Path.home() / "archpipe/assets/library").exists())
            with self.assertRaisesRegex(FileNotFoundError, "sf_frangipani"):
                old.prop_triangles(prop)
            triangles = geometry.prop_triangles(prop)
            self.assertGreater(len(triangles), 40000)
            self.assertLess(len(triangles), 82691)
            scene = VR.build(views=[])
            self.assertTrue(scene["meshes"])
            # Every placed landscape prop, not just the overlapping tree.
            garden = [p for p in scene["props"] if p["id"].startswith("landscape-")]
            self.assertTrue(garden)
            for item in garden:
                self.assertGreater(len(records.recorded_triangles(item["asset"])), 0)

    def test_missing_stale_corrupt_record_and_manifest_fail_closed(self):
        original = records.read_record()
        manifest = json.loads(records.MANIFEST.read_text())
        asset = "sf_frangipani"
        with tempfile.TemporaryDirectory() as tmp:
            record_path, manifest_path = Path(tmp)/"record.json", Path(tmp)/"manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            def rejects(record, changed_manifest=manifest):
                record_path.write_text(json.dumps(record))
                manifest_path.write_text(json.dumps(changed_manifest))
                with self.assertRaisesRegex(ValueError, "asset sf_frangipani:.*generate_asset_route_geometry.py"):
                    records.recorded_triangles(asset, record_path, manifest_path)
            with self.assertRaisesRegex(ValueError, "generate_asset_route_geometry.py"):
                records.recorded_triangles(asset, record_path, manifest_path)
            missing = copy.deepcopy(original); del missing["assets"][asset]
            rejects(missing)
            stale = copy.deepcopy(original); stale["assets"][asset]["source_sha256"] = "0"*64
            rejects(stale)
            with patch.object(records, "RECORD", record_path), patch.object(records, "MANIFEST", manifest_path):
                with self.assertRaisesRegex(ValueError, "sf_frangipani:.*generate_asset_route_geometry.py"):
                    VR.build(views=[])
            stale = copy.deepcopy(manifest)
            next(p for p in stale["props"] if p["id"] == asset)["geometry_buffer_sha256"] = {}
            rejects(original, stale)
            corrupt = copy.deepcopy(original); corrupt["assets"][asset]["vertices"] = "broken"
            rejects(corrupt)
            corrupt = copy.deepcopy(original); corrupt["assets"][asset]["framing_hull_vertices"] = "broken"
            rejects(corrupt)
            corrupt = copy.deepcopy(original); corrupt["assets"][asset]["native_step_m"] = .002
            rejects(corrupt)
            compressed=Path(tmp)/"record.json.gz"
            records.write_record(compressed,original)
            compressed.write_bytes(compressed.read_bytes()[:-20])
            with self.assertRaisesRegex(ValueError,"sf_frangipani:.*generate_asset_route_geometry.py"):
                records.recorded_triangles(asset,compressed,manifest_path)
            self.assertGreater(len(records.recorded_triangles(asset)), 0)

    def test_missing_nonoverlapping_placed_asset_fails_closed(self):
        from archpipe.concept import villa_landscape as L
        prop = dict(id="renamed-clear-prop", asset="sf_wooden_bench", position=[100,100,0], scale=1)
        record = records.read_record(); del record["assets"][prop["asset"]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"record.json"; path.write_text(json.dumps(record))
            with patch.object(records, "RECORD", path):
                with self.assertRaisesRegex(ValueError, "sf_wooden_bench:.*generate_asset_route_geometry.py"):
                    L.route_violations([prop])

    def test_generator_lossless_sibling_full_height_and_buffer_hash(self):
        from scripts.generate_asset_route_geometry import generate
        from archpipe.asset_route_generator import asset_triangles
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root/"props/renamed-sibling"; folder.mkdir(parents=True)
            # Node transforms, coordinates beyond the walking height and external buffer.
            (folder/"shape.bin").write_bytes(struct.pack("<9f", 0,0,0, 1,0,0, 0,3.25,0))
            gltf = dict(buffers=[dict(uri="shape.bin",byteLength=36)],
                        bufferViews=[dict(buffer=0,byteLength=36)],
                        accessors=[dict(bufferView=0,componentType=5126,count=3,type="VEC3")],
                        meshes=[dict(primitives=[dict(attributes=dict(POSITION=0))])],
                        nodes=[dict(mesh=0,translation=[2,1,4])],scenes=[dict(nodes=[0])],scene=0)
            model = folder/"model.gltf"; model.write_text(json.dumps(gltf))
            manifest = root/"manifest.json"; manifest.write_text(json.dumps(dict(props=[dict(id="renamed-sibling")])))
            record = root/"record.json"
            policy = root/"policy.json"
            policy.write_text(json.dumps(dict(margin_m=.41, assets={"renamed-sibling":
                dict(scale_range=[.5,2], scale_mode="uniform", basis="transformed sibling proof")})))
            generate(root, ["renamed-sibling"], record, manifest, policy)
            actual = records.recorded_triangles("renamed-sibling", record, manifest)
            np.testing.assert_array_equal(actual, asset_triangles(model))
            self.assertGreater(actual[:,:,2].max()-actual[:,:,2].min(), 2)
            with patch.object(records, "RECORD", record), patch.object(records, "MANIFEST", manifest):
                placed = geometry.prop_triangles(dict(asset="renamed-sibling",position=[7,8,-3],scale=.5,rotation_deg=[0,0,90]))
            np.testing.assert_allclose(placed[0], [[9,9,-3],[9,9.5,-3],[9,9,-1.375]])
            # Editing only an external buffer and regenerating changes the provenance.
            before = json.loads(manifest.read_text())["props"][0]["geometry_buffer_sha256"]
            (folder/"shape.bin").write_bytes(struct.pack("<9f", 0,0,0, 2,0,0, 0,3.25,0))
            generate(root, ["renamed-sibling"], record, manifest, policy)
            self.assertNotEqual(before, json.loads(manifest.read_text())["props"][0]["geometry_buffer_sha256"])

    def test_exact_band_boundary_and_scale_range_generalise(self):
        from scripts.generate_asset_route_geometry import generate
        from archpipe.asset_route_generator import asset_triangles
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root/"props/other-branch"; folder.mkdir(parents=True)
            # Native Y is height: crossing triangle, just inside and just above.
            points = [(0,0,0),(1,0,0),(0,3.25,0),
                      (0,2.40999,0),(1,2.40999,0),(0,2.40999,1),
                      (0,2.41001,0),(1,2.41001,0),(0,2.41001,1)]
            blob = np.array(points,dtype="<f4").tobytes()
            (folder/"shape.bin").write_bytes(blob)
            gltf = dict(buffers=[dict(uri="shape.bin",byteLength=len(blob))],
                        bufferViews=[dict(buffer=0,byteLength=len(blob))],
                        accessors=[dict(bufferView=0,componentType=5126,count=9,type="VEC3")],
                        meshes=[dict(primitives=[dict(attributes=dict(POSITION=0))])],
                        nodes=[dict(mesh=0,translation=[2,1,4])],scenes=[dict(nodes=[0])],scene=0)
            model=folder/"model.gltf"; model.write_text(json.dumps(gltf))
            manifest=root/"manifest.json"; manifest.write_text(json.dumps(dict(props=[dict(id="other-branch")])))
            record=root/"record.json"; policy=root/"policy.json"
            policy.write_text(json.dumps(dict(margin_m=.41, assets={"other-branch":
                dict(scale_range=[1,2],scale_mode="uniform",basis="boundary test")})))
            generate(root,["other-branch"],record,manifest,policy)
            triangles,vertices,row=records.recorded_geometry("other-branch",record,manifest)
            raw=asset_triangles(model)
            np.testing.assert_array_equal(triangles,raw[:2])
            np.testing.assert_array_equal(vertices.min(axis=0),raw.min(axis=(0,1)))
            np.testing.assert_array_equal(vertices.max(axis=0),raw.max(axis=(0,1)))
            self.assertLess(len(vertices),len(np.unique(raw.reshape(-1,3),axis=0)))
            self.assertEqual(row["triangle_count_before"],3)
            self.assertEqual(row["triangle_count_after"],2)
            self.assertEqual(row["walking_band_native"]["top"],3.41)
            with patch.object(records,"RECORD",record), patch.object(records,"MANIFEST",manifest):
                prop=dict(asset="other-branch",position=[7,8,-3],scale=1)
                self.assertEqual(len(geometry.prop_triangles(prop)),2)
                self.assertAlmostEqual(geometry.prop_framing_points(prop)[:,2].max(),.25)
                for scale in (.99999,2.00001,-1,0,[1,1,1],float("nan")):
                    with self.subTest(scale=scale), self.assertRaisesRegex(ValueError,"recorded range"):
                        geometry.prop_triangles(dict(prop,scale=scale))
                for scale in (1,2):
                    self.assertEqual(len(geometry.prop_triangles(dict(prop,scale=scale))),2)
                with self.assertRaisesRegex(ValueError,"exceeds recorded band"):
                    geometry.prop_triangles(prop,walking_top_m=-.58)

    def test_real_scale_and_lowering_outside_band_fail_closed(self):
        from archpipe.concept import villa_landscape as L
        prop=json.loads((ROOT/"tests/fixtures/garden-g2-tree-centred-before.json").read_text())
        for asset in ("sf_frangipani","sf_ixora"):
            _,_,row=records.recorded_geometry(asset)
            for scale in (row["scale_range"][0]-.00001,row["scale_range"][1]+.00001):
                with self.assertRaisesRegex(ValueError,"recorded range"):
                    geometry.prop_triangles(dict(prop,asset=asset,scale=scale))
        prop["position"][2]-=1
        with self.assertRaisesRegex(ValueError,"exceeds recorded band"):
            L.route_violations([prop])

    def test_record_storage_contract(self):
        record=records.read_record()
        self.assertEqual(sum(row["triangle_count_before"] for row in record["assets"].values()),456334)
        self.assertEqual(sum(row["triangle_count_after"] for row in record["assets"].values()),421178)
        self.assertLess(records.RECORD.stat().st_size,1500000)
        for asset in record["assets"]:
            triangles,_,row=records.recorded_geometry(asset)
            self.assertTrue(np.all(triangles[:,:,2].min(axis=1)<=row["walking_band_native"]["top"]+row["native_step_m"]/2))
            self.assertLessEqual(row["scene_error_bound_m"],.001)
        self.assertEqual(records.recorded_geometry("sf_frangipani")[2]["scene_error_bound_m"],0)

    def test_size_budget_refuses_real_record_before_writing(self):
        record=records.read_record()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"record.json.gz"
            path.write_bytes(b"previous input")
            with self.assertRaisesRegex(ValueError,"budget"):
                records.write_record(path,record,max_bytes=1000000)
            self.assertEqual(path.read_bytes(),b"previous input")
            records.write_record(path,record,max_bytes=1500000)
            self.assertEqual(records.read_record(path),record)

    def test_real_hull_only_matches_all_vertex_frame_results(self):
        from scripts.villa_render_views import subject_mesh_frame_violations
        proof=json.loads((ROOT/"tests/fixtures/asset-framing-real.json").read_text())
        for asset,item in proof["assets"].items():
            _,hull,row=records.recorded_geometry(asset)
            self.assertEqual(row["source_sha256"],item["source_sha256"])
            self.assertEqual(row["buffer_sha256"],item["buffer_sha256"])
            self.assertLess(len(hull),item["full_vertex_count"])
            for name,case in item["cases"].items():
                with self.subTest(asset=asset,camera=name):
                    result=subject_mesh_frame_violations(case["view"],dict(meshes=[],props=[item["prop"]]),"proof-asset")
                    self.assertEqual(result,case["all_vertex_result"])
                    self.assertEqual(bool(result),name!="in-frame")

    def test_hull_degenerate_and_transformed_siblings_generalise(self):
        from archpipe.asset_framing_hull import framing_hull_vertices
        points=np.array([[0,0,0],[2,0,0],[0,2,0],[0,0,2],[.25,.25,.25],[0,0,0]],float)
        hull=framing_hull_vertices(points)
        self.assertEqual(len(hull),4)
        # Compare every linear halfspace, including near-boundary clipping.
        rng=np.random.default_rng(419)
        for transform in (np.eye(3),np.array([[2,.1,0],[0,.8,.2],[.1,0,1.5]])):
            all_points=points@transform+np.array([17,-23,8])
            subset=hull@transform+np.array([17,-23,8])
            for normal in rng.normal(size=(50,3)):
                extreme=float((all_points@normal).max())
                for offset in (-1e-9,0,1e-9):
                    self.assertEqual(bool(np.all(all_points@normal<=extreme+offset)),
                                     bool(np.all(subset@normal<=extreme+offset)))
        self.assertEqual(len(framing_hull_vertices(points[:3])),3)
        self.assertEqual(len(framing_hull_vertices([[0,0,0],[1,1,1],[2,2,2]])),2)
        self.assertEqual(len(framing_hull_vertices([[1,2,3],[1,2,3]])),1)

    def test_quantised_branch_one_mm_inside_stays_detected(self):
        from scripts.generate_asset_route_geometry import generate
        from archpipe.concept import villa_landscape as landscape
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"props/thin-branch";folder.mkdir(parents=True)
            maximum=1.7
            # Two separate branches: one 1 mm below, one 1 mm above the
            # 2 m envelope at the maximum scale; base triangle is far away.
            points=np.array([(10,0,10),(11,0,10),(10,0,11),
                (0,1.999/maximum,0),(1,1.999/maximum,0),(0,1.999/maximum,1),
                (0,2.001/maximum,0),(1,2.001/maximum,0),(0,2.001/maximum,1)],dtype="<f4")
            blob=points.tobytes();(folder/"shape.bin").write_bytes(blob)
            gltf=dict(buffers=[dict(uri="shape.bin",byteLength=len(blob))],
                bufferViews=[dict(buffer=0,byteLength=len(blob))],
                accessors=[dict(bufferView=0,componentType=5126,count=9,type="VEC3")],
                meshes=[dict(primitives=[dict(attributes=dict(POSITION=0))])],
                nodes=[dict(mesh=0)],scenes=[dict(nodes=[0])],scene=0)
            (folder/"model.gltf").write_text(json.dumps(gltf))
            manifest=root/"manifest.json";manifest.write_text(json.dumps(dict(props=[dict(id="thin-branch")])))
            policy=root/"policy.json";policy.write_text(json.dumps(dict(margin_m=.41,assets={"thin-branch":
                dict(scale_range=[1,maximum],scale_mode="uniform",basis="precision proof",route_scene_step_m=.001)})))
            record=root/"record.json.gz";generate(root,["thin-branch"],record,manifest,policy)
            with patch.object(records,"RECORD",record),patch.object(records,"MANIFEST",manifest):
                prop=dict(id="renamed-branch",asset="thin-branch",position=[7,8,3],scale=maximum)
                placed=geometry.prop_triangles(prop)
                prop["rect"]=[*placed[:,:,:2].min(axis=(0,1)),*placed[:,:,:2].max(axis=(0,1))]
                self.assertLess(placed[1,:,2].max(),5)
                self.assertGreater(placed[2,:,2].min(),5)
                self.assertEqual(landscape.route_violations([prop],{"other":(7.2,7,8,7.8)},{"other":3}),[("renamed-branch","other")])
                outside=dict(id="outside-branch",faces=placed[2:3].tolist())
                self.assertEqual(landscape.route_violations([outside],{"other":(7.2,7,8,7.8)},{"other":3}),[])
                raw=points.reshape(3,3,3)[:,:,[0,2,1]].astype(float);raw[:,:,1]*=-1
                error=np.linalg.norm((records.recorded_triangles("thin-branch")-raw)*maximum,axis=2)
                self.assertLessEqual(error.max(),records.recorded_geometry("thin-branch")[2]["scene_error_bound_m"])
                # Integer storage preserves every face, original vertex identity,
                # winding and order; it does not merge quantised coincidences.
                row=records.recorded_geometry("thin-branch")[2]
                self.assertEqual(row["vertex_count"],len(np.unique(raw.reshape(-1,3),axis=0)))
                np.testing.assert_array_equal(records.recorded_triangles("thin-branch"),
                    np.rint(raw/row["native_step_m"])*row["native_step_m"])
                # Reject excessive error even with a freshly bound payload digest.
                document=records.read_record(record);row=document["assets"]["thin-branch"]
                row["scene_error_bound_m"]=.00101
                vertex_blob=records.unpack_array(row["vertices"],4)
                indices=np.cumsum(np.frombuffer(records.unpack_array(row["indices"],4),dtype="<i4"),dtype=np.int64).astype("<u4").tobytes()
                row["geometry_sha256"]=records.geometry_digest(vertex_blob,indices,records.unpack_array(row["framing_hull_vertices"],8),row)
                records.write_record(record,document)
                with self.assertRaisesRegex(ValueError,"thin-branch:.*generate_asset_route_geometry.py"):
                    records.recorded_geometry("thin-branch")

    def test_static_guard_real_old_path_siblings_and_clean_build(self):
        frozen = (ROOT/"tests/fixtures/route_geometry_ec0bc39.py").read_text()
        self.assertTrue(source_findings(frozen, "concept/route_geometry.py"))
        siblings = ["from pathlib import Path as P\nx=P.home()/'assets/library/props'/'model.gltf'\nx.read_bytes()",
                    "from archpipe.asset_route_generator import asset_triangles as load\nload(p)",
                    "import os\nx=os.path.expanduser('~/archpipe/assets/library/props/model.gltf')"]
        for sibling in siblings:
            self.assertTrue(source_findings(sibling, "concept/renamed_consumer.py"))
        self.assertEqual(source_findings('library_root="$HOME/archpipe/assets/library"', "concept/villa_render.py"), [])
        self.assertEqual(build_input_findings(), [])
