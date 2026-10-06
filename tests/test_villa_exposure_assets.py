"""Selection-independent exposure and placed plant material regressions."""
import ast
import json
import os
from pathlib import Path
import unittest
from types import SimpleNamespace

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/archpipe/blender/villa_scene.py"


def load_function(name):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace[name]


class ExposureCohortTest(unittest.TestCase):
    def test_lock_is_independent_of_selected_views(self):
        # Retained interior cohort and daytime peers after duplicate-camera
        # retirement: subset selection must never change the state's lock.
        views = ([{"id": n, "exposure": "evening"} for n in
                  ("v12-ensuite", "v16-guest-wc", "v31-dressing-hers", "v32-dressing-his")]
                 + [{"id": n, "exposure": "day"} for n in
                    ("v17-dirty-kitchen", "v25-top-garden-gate", "v26-top-garden-north")])
        readings = {v["id"]: i for i, v in enumerate(views)}
        meter_views = load_function("exposure_meter_views")
        locks = load_function("exposure_locks")
        locks.__globals__["exposure_meter_views"] = meter_views
        meter = lambda view: (readings[view["id"]], 0.18)
        alone = locks(views, {"v12-ensuite"}, meter)
        peers = locks(views, {"v12-ensuite", "v16-guest-wc"}, meter)
        mixed = locks(views, {"v12-ensuite", "v17-dirty-kitchen"}, meter)
        self.assertEqual(alone[0]["evening"], peers[0]["evening"])
        self.assertEqual(alone[0]["evening"], mixed[0]["evening"])
        self.assertEqual(alone[2]["evening"], [v["id"] for v in views if v["exposure"] == "evening"])
        self.assertEqual(mixed[2]["day"], [v["id"] for v in views if v["exposure"] == "day"])
        self.assertEqual(peers[1]["v16-guest-wc"]["log_average"], 0.18)


class LavenderMaterialTest(unittest.TestCase):
    def test_actual_planter_asset_has_black_rgb_background_and_import_cutout(self):
        folder = ROOT / "out/villa/round3/stage-props/sf_lavender_clump"
        model = json.loads((folder / "model.gltf").read_text(encoding="utf-8"))
        material = model["materials"][0]
        self.assertEqual(material.get("alphaMode", "OPAQUE"), "OPAQUE")
        image = Image.open(folder / model["images"][0]["uri"])
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0))

    def test_import_rejects_missing_colour_and_accepts_coloured_material(self):
        validate = load_function("validate_imported_appearance")
        validate.__globals__["normalise_imported_material"] = load_function("normalise_imported_material")
        validate.__globals__["os"] = os
        validate.__globals__["bpy"] = SimpleNamespace(path=SimpleNamespace(abspath=lambda path: path))
        def mesh(materials):
            return SimpleNamespace(name="leaf", data=SimpleNamespace(materials=materials))
        with self.assertRaisesRegex(ValueError, "no render material"):
            validate([mesh([])], "mutated-plant")
        def material(colour):
            base = SimpleNamespace(links=[], is_linked=False, default_value=(*colour, 1))
            shader = SimpleNamespace(type="BSDF_PRINCIPLED", inputs={"Base Color": base})
            return SimpleNamespace(use_nodes=True, node_tree=SimpleNamespace(nodes=[shader]), name="leaf")
        with self.assertRaisesRegex(ValueError, "no base colour or texture"):
            validate([mesh([material((0, 0, 0))])], "mutated-plant")
        validate([mesh([material((0.2, 0.4, 0.1))])], "healthy-plant")
        missing_image = SimpleNamespace(packed_file=None, filepath="missing-base-colour.png")
        tex = SimpleNamespace(type="TEX_IMAGE", image=missing_image)
        base = SimpleNamespace(links=[SimpleNamespace(from_node=tex)], is_linked=True,
                               default_value=(1, 1, 1, 1))
        shader = SimpleNamespace(type="BSDF_PRINCIPLED", inputs={"Base Color": base})
        broken = SimpleNamespace(use_nodes=True, node_tree=SimpleNamespace(nodes=[shader]), name="leaf")
        with self.assertRaisesRegex(ValueError, "missing base colour texture"):
            validate([mesh([broken])], "mutated-plant")


class ImportedEmissionTest(unittest.TestCase):
    def fixture(self, *, texture=True, unlit=True):
        class Socket:
            def __init__(self, value=None):
                self.default_value, self.links = value, []
            @property
            def is_linked(self):
                return bool(self.links)
        class Node:
            def __init__(self, kind, name=None):
                self.type = kind
                self.name = name or kind
                self.inputs = {key: Socket((0, 0, 0, 1) if key in ("Color", "Base Color") else None)
                               for key in ("Surface", "Color", "Base Color", "Alpha", "Roughness", "Specular IOR Level", "Emission Strength")}
                self.outputs = {key: Socket() for key in ("Color", "Alpha", "Emission", "Shader", "BSDF")}
        class Nodes(list):
            def new(self, kind):
                node = Node("BSDF_PRINCIPLED" if kind == "ShaderNodeBsdfPrincipled" else kind)
                self.append(node)
                return node
        class Links:
            def new(self, source, target):
                target.links[:] = [SimpleNamespace(from_node=next(n for n in nodes if source in n.outputs.values()))]
        nodes = Nodes()
        tex = Node("TEX_IMAGE")
        tex.image = SimpleNamespace(depth=24, packed_file=True, filepath="texture.jpeg")
        if texture:
            nodes.append(tex)
        emit = Node("EMISSION")
        nodes.append(emit)
        output = Node("OUTPUT_MATERIAL")
        nodes.append(output)
        tree = SimpleNamespace(nodes=nodes, links=Links())
        tree.links.new(emit.outputs["Emission"], output.inputs["Surface"])
        if texture:
            tree.links.new(tex.outputs["Color"], emit.inputs["Color"])
        if unlit:
            for kind in ("LIGHT_PATH", "BSDF_TRANSPARENT", "MIX_SHADER"):
                nodes.append(Node(kind))
        class Material:
            def __init__(self):
                self.name, self.use_nodes, self.node_tree = "tex_u1_v1", True, tree
            def __setitem__(self, key, value):
                setattr(self, key, value)
        return SimpleNamespace(name="leaf", data=SimpleNamespace(materials=[Material()]))

    def validate(self):
        validate = load_function("validate_imported_appearance")
        validate.__globals__.update(normalise_imported_material=load_function("normalise_imported_material"),
                                    os=os, bpy=SimpleNamespace(path=SimpleNamespace(abspath=lambda p: p)))
        return validate

    def test_real_bougainvillea_unlit_pattern_converts(self):
        model = json.loads((ROOT / "out/villa/round3/stage-props/sf_bougainvillea/model.gltf").read_text())
        self.assertIn("KHR_materials_unlit", model["materials"][0]["extensions"])
        self.assertTrue(model["images"][0]["uri"].endswith("baseColor.jpeg"))
        mesh = self.fixture()
        notes = self.validate()([mesh], "sf_bougainvillea")
        self.assertEqual(len(notes), 1)
        self.assertEqual([n.type for n in mesh.data.materials[0].node_tree.nodes if n.type == "EMISSION"], [])
        self.assertIn("ASSUMED foliage", notes[0]["note"])

    def test_emission_only_foliage_converts_and_luminaire_keeps_emission(self):
        mesh = self.fixture(unlit=False)
        self.assertEqual(len(self.validate()([mesh], "plant")), 1)
        solid = self.fixture(texture=False, unlit=False)
        next(n for n in solid.data.materials[0].node_tree.nodes if n.type == "EMISSION").inputs["Color"].default_value = (0.3, 0.5, 0.1, 1)
        self.assertEqual(len(self.validate()([solid], "solid-colour-plant")), 1)
        lamp = self.fixture(unlit=False)
        self.validate()([lamp], "declared-lamp", "luminaire")
        self.assertTrue(any(n.type == "EMISSION" for n in lamp.data.materials[0].node_tree.nodes))

    def test_missing_colour_still_fails(self):
        with self.assertRaisesRegex(ValueError, "no supported colour shader"):
            self.validate()([self.fixture(texture=False)], "broken-plant")

    def test_principled_emission_requires_luminaire_declaration(self):
        mesh = self.fixture()
        mat = mesh.data.materials[0]
        mat.node_tree.nodes[:] = [n for n in mat.node_tree.nodes if n.type != "EMISSION"]
        shader = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Base Color"].default_value = (0.2, 0.3, 0.1, 1)
        shader.inputs["Emission Strength"].default_value = 1.0
        with self.assertRaisesRegex(ValueError, "retains emission"):
            self.validate()([mesh], "plant")
        self.validate()([mesh], "lamp", "luminaire")


if __name__ == "__main__":
    unittest.main()
