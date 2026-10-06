"""G1/G2 measured candidate and frozen physical failures; export remains fail closed."""
import copy
import json
from math import hypot
from pathlib import Path
import unittest
from unittest.mock import patch

from archpipe.concept import villa_landscape as L, revit_spec as RS, villa_r11 as R


class LandscapeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = R.design("D1")
        cls.spec = RS.build(cls.lay)
        cls.meshes, cls.props, cls.notes, cls.plan = L.review_candidate(cls.spec, cls.lay)
        cls.rooms = L.garden_level_rooms(cls.lay)
        cls.before = json.loads((Path(__file__).parent / "fixtures/garden-g1-before.json").read_text())
        cls.tree = next(p for p in cls.props if p.get("species") == "Plumeria rubra")
        cls.centred_tree = json.loads((Path(__file__).parent / "fixtures/garden-g2-tree-centred-before.json").read_text())
        cls.other_props = [p for p in cls.props if p is not cls.tree]

    def test_palette_has_exact_agreed_species_and_unverified_fields(self):
        data = L._plant_data()
        self.assertEqual(set(data), {"Aspidistra elatior", "Ixora coccinea", "Strelitzia reginae",
            "Callistemon citrinus", "Ursinia anthemoides", "Salvia rosmarinus Prostrata Group",
            "Aloe vera", "Plumeria rubra", "Trachelospermum jasminoides", "Bougainvillea glabra"})
        for row in data.values():
            self.assertEqual(row["egypt_performance"]["status"], "UNVERIFIED")
            self.assertEqual(row["root_behaviour_over_basement_slab"]["status"], "UNVERIFIED")
            for field in ("height", "spread", "light", "zones", "source_url"):
                self.assertIn("status", row[field])
        ixora = data["Ixora coccinea"]
        self.assertIsNone(ixora["spread"]["range_m"])
        self.assertEqual(ixora["placement_assumptions"]["spacing_spread"]["status"], "ASSUMED")
        self.assertTrue(ixora["placement_assumptions"]["spacing_spread"]["reason"])

    def test_palette_is_only_species_input_and_dimensions_follow_record(self):
        # A copied record changes placement; no constants or generated palette
        # can silently restore the prior height. Use an existing approved asset.
        record = json.loads(L.PALETTE.read_text())
        ixora = next(r for r in record["species"] if r["species"] == "Ixora coccinea")
        ixora["placement_assumptions"]["sf_ixora"]["contexts"]["landscape-west-mid-00"]["height_m"] = .7
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"palette.json"
            path.write_text(json.dumps(record))
            with patch.object(L, "PALETTE", path):
                _, props, _, _ = L.review_candidate(self.spec, self.lay)
        changed = next(p for p in props if p["id"] == "landscape-west-mid-00")
        mn, mx = L.PROP_BOUNDS[changed["asset"]]
        self.assertAlmostEqual(changed["scale"]*(mx[1]-mn[1]), .7)
        source = Path(L.__file__).read_text()
        for legacy in ("SPREAD =", "EXTRA_CARE", "CLUMP_SPREAD", "out/villa/round3/plant-palette.json"):
            self.assertNotIn(legacy, source)

    def test_species_fails_on_real_excluded_bauhinia_and_unknown_siblings(self):
        old = next(p for p in self.before["props"] if p["asset"] == "sf_bauhinia")
        self.assertTrue(L.species_violations([old]))
        for species in ("Bauhinia variegata", "Pennisetum setaceum", "Citrus limon", "unknown species"):
            with self.assertRaisesRegex(ValueError, "unknown or excluded"):
                L.require_species(species)
        with self.assertRaisesRegex(ValueError, "Bauhinia"):
            L._prop("excluded", "sf_bauhinia", (26.9, -27), L.GROUND, 2.9, "old")
        self.assertEqual(L.species_violations(self.meshes+self.props), [])
        mislabelled = dict(self.tree, species="Ixora coccinea")
        self.assertTrue(L.species_violations([mislabelled]))
        unnamed = dict(self.tree)
        del unnamed["species"]
        self.assertTrue(L.species_violations([unnamed]))

    def test_east_content_fires_on_real_prechange_and_stays_quiet(self):
        self.assertTrue(L.east_content_violations(self.before["meshes"], self.before["props"], self.before["objects"]))
        self.assertEqual(L.east_content_violations(self.meshes, self.props, self.plan["objects"]), [])
        self.assertEqual(len([p for p in self.props if p.get("species") == "Plumeria rubra"]), 1)
        old_bistro = next(p for p in self.before["props"] if p["asset"] == "outdoor_table_chair_set_01")
        # Guard finds an arbitrary ID by physical location, not old naming.
        sibling = dict(old_bistro, id="unrelated-new-furniture")
        self.assertTrue(L.east_content_violations(self.meshes, self.props+[sibling]))
        duplicate = dict(self.tree, id="second-tree")
        self.assertTrue(L.east_content_violations(self.meshes, self.props+[duplicate]))
        furniture = [p for p in self.props if p["asset"] in ("sf_egg_chair", "outdoor_table_chair_set_01")]
        self.assertEqual(len(furniture), 2)
        self.assertTrue(all(L._rect(p)[2] < L.EAST[0] for p in furniture))
        self.assertTrue(all("relocated from the east garden; client to confirm" in p["label"] for p in furniture))

    def test_trunk_centred_and_turf_does_not_cap_assumed_pit(self):
        self.assertEqual(self.tree["center"], self.plan["tree_pit"]["center"])
        self.assertAlmostEqual(self.tree["center"][0],L.EAST_CENTER[0])
        self.assertGreater(self.tree["center"][1],L.EAST_CENTER[1])
        ax, _, az = self.tree["asset_measurement"]["trunk_base_gltf_m"]
        self.assertAlmostEqual(self.tree["position"][0]+self.tree["scale"]*ax, self.tree["center"][0])
        self.assertAlmostEqual(self.tree["position"][1]-self.tree["scale"]*az, self.tree["center"][1])
        pit = next(m for m in self.meshes if m["part_kind"] == "tree-pit")
        self.assertIn("ASSUMED 1.2 m", pit["label"])
        for p in pit["faces"][0]:
            self.assertAlmostEqual(hypot(p[0]-self.tree["center"][0], p[1]-self.tree["center"][1]), .6)
        grass = next(m for m in self.meshes if m["id"] == "landscape-grass-east")
        # Actual pre-fix construction used a capped quad; freeze its vertices.
        capped = dict(grass, faces=[[[22.597,-29.915,-2.997],[28.557,-29.915,-2.997],
                                    [28.557,-23.591,-2.997],[22.597,-23.591,-2.997]]])
        self.assertTrue(any("covers the tree pit" in why for _,why in
            L.east_content_violations([capped,pit],self.props)))
        centred_canopy = L._prop("canopy-centred", "sf_frangipani", L.EAST_CENTER, L.GROUND, 4.6, "incorrect canopy anchor")
        centred_canopy.update(species="Plumeria rubra",center=L.EAST_CENTER)
        self.assertTrue(any("measured trunk" in why for _,why in
            L.east_content_violations(self.meshes,[centred_canopy])))

    def test_candidate_meshes_stay_in_yard_and_pass_physical_boundary(self):
        from archpipe.concept.physical_part import Part
        for mesh in self.meshes:
            for face in mesh["faces"]:
                for x,y,_ in face:
                    self.assertTrue(L.inside_yard(x,y),mesh["id"])
            Part(mesh["part_kind"],mesh["faces"],("x","y","z"),mesh["material"],
                 "authored-procedural",surface=mesh["surface"],occupied_side=mesh["occupied_side"])

    def test_dimensions_fail_on_real_old_frangipani_and_mutations(self):
        old = next(p for p in self.before["props"] if p["asset"] == "sf_frangipani")
        old = dict(old, species="Plumeria rubra")
        self.assertTrue(any("height" in why for _,why in L.dimension_violations([old])))
        self.assertEqual(L.dimension_violations(self.meshes+self.props), [])
        oversize = dict(self.tree,scale=self.tree["scale"]*2)
        self.assertTrue(L.dimension_violations([oversize]))
        stretch = dict(self.tree,scale=[self.tree["scale"],self.tree["scale"]*.8,self.tree["scale"]])
        self.assertTrue(L.dimension_violations([stretch]))
        branches = copy.deepcopy(next(m for m in self.meshes if m["part_kind"] == "climber-branch"))
        for face in branches["faces"]:
            for point in face:
                point[2] = L.GROUND + 2*(point[2]-L.GROUND)
        self.assertTrue(L.dimension_violations([branches]))

    def test_tree_scale_and_measured_asset_record(self):
        row = L.require_species("Plumeria rubra")
        evidence = row["appearance_measurements"]["sf_frangipani"]
        self.assertEqual(row["height"]["range_m"], [4.6,7.6])
        self.assertEqual(row["spread"]["range_m"], [4.6,7.6])
        bounds = evidence["native_gltf_y_up_bounds_m"]
        self.assertAlmostEqual(self.tree["scale"], 4.6/max(bounds["max"][i]-bounds["min"][i] for i in (0,2)))
        self.assertEqual(row["placement_assumptions"]["sf_frangipani"]["rendered_stage"]["value"], "young pruned tree")
        self.assertAlmostEqual(self.tree["scale"], evidence["scale"])
        self.assertIn("native_gltf_y_up_bounds_m",self.tree["asset_measurement"])
        self.assertEqual(evidence["status"],"MEASURED")
        self.assertEqual(evidence["licence"],"CC Attribution")

    def test_young_model_and_verified_mature_circle_clear_fence(self):
        self.assertEqual(L.canopy_violations([self.tree],mature=True), [])
        self.assertEqual(L.canopy_violations([self.tree]), [])
        self.assertEqual(L.extent_violations([self.tree],self.rooms), [])
        bounds = L.require_species("Plumeria rubra")["appearance_measurements"]["sf_frangipani"]["native_gltf_y_up_bounds_m"]
        old_scale = 4.6/(bounds["max"][1]-bounds["min"][1])
        old = dict(self.tree,scale=old_scale)
        self.assertTrue(L.canopy_violations([old]))
        self.assertTrue(L.canopy_violations([dict(old,rotation_deg=[0,0,90])]))
        moved = dict(self.tree,center=(L.EAST[2]-.5,L.EAST_CENTER[1]))
        self.assertTrue(L.canopy_violations([moved],mature=True))

    def test_export_refuses_real_low_branch_conflict_and_layers_follow_beds(self):
        self.assertEqual(self.plan["conflicts"], [])
        self.assertEqual(L.layer_violations(self.plan["plants"],self.plan["beds"]), [])
        self.assertNotIn("east", self.plan["beds"])
        # A real low branch must not be ignored merely because the prop is a tree.
        L.build(self.spec,self.lay)
        failed=copy.deepcopy(self.props)
        failed[next(i for i,p in enumerate(failed) if p["id"]==self.tree["id"])]=self.centred_tree
        self.assertIn((self.tree["id"],"door route living-east"),L.candidate_violations(self.meshes,failed,self.plan,self.lay))
        with patch.object(L,"review_candidate",return_value=(self.meshes,failed,self.notes,dict(self.plan,conflicts=[(self.tree["id"],"door route living-east")]))):
            with self.assertRaisesRegex(ValueError,"door route living-east"):
                L.build(self.spec,self.lay)
        self.assertFalse(any("UNRESOLVED garden guard" in n for n in self.notes))
        # Explicit data, rather than a hard-coded east waiver: an added bed
        # without planting has to fail regardless of its name or location.
        self.assertEqual(L.layer_violations(self.plan["plants"],{"new-border":(0,0,1,1)}),[("new-border",[])])

    def test_route_geometry_uses_actual_asset_below_passage_height(self):
        from archpipe.concept.route_geometry import prop_triangles
        triangles = prop_triangles(self.tree)
        self.assertAlmostEqual(float(triangles[:,:,2].min()), L.GROUND)
        bounds = L.require_species("Plumeria rubra")["appearance_measurements"]["sf_frangipani"]["native_gltf_y_up_bounds_m"]
        self.assertAlmostEqual(float(triangles[:,:,2].max())-L.GROUND,
                               (bounds["max"][1]-bounds["min"][1])*self.tree["scale"])
        low = copy.deepcopy(self.centred_tree)
        low["position"][2] -= .4
        self.assertIn((low["id"],"living-east"),L.route_violations([low]))
        # Diagnostic height-band proof only, never a floating scene placement.
        head_clear = copy.deepcopy(self.centred_tree)
        head_clear["position"][2] += .4
        self.assertEqual(L.route_violations([head_clear]), [])
        self.assertIn((self.tree["id"],"living-east"),L.route_violations([self.centred_tree]))
        self.assertEqual(L.route_violations([self.tree]), [])
        # The same rule is physical for a non-tree, with a long member whose
        # endpoints are outside a path but whose face crosses it.
        shelf = dict(id="renamed-overhead-member",faces=L._box(0,0,2.1,2,1,2.2))
        routes={"other":(.5,.2,1.5,.8)}
        self.assertEqual(L.route_violations([shelf],routes,{"other":0}), [])
        shelf["faces"]=L._box(0,0,1.9,2,1,2.0)
        self.assertEqual(L.route_violations([shelf],routes,{"other":0}),[(shelf["id"],"other")])

    def test_d4_whole_lawn_minimum_and_sibling_translation_search(self):
        from scripts.garden_tree_position import search_position
        from archpipe.concept.route_geometry import nearest_clear_translation
        import numpy as np
        answer = search_position()
        for got,need in zip(answer['center_m'],self.tree['center']):
            self.assertAlmostEqual(got,need,places=9)
        self.assertAlmostEqual(answer['distance_m'],.7222147136163092,places=9)
        self.assertLess(answer['distance_m']-answer['boundary_distance_m'],1.01e-6)
        nearer = copy.deepcopy(self.tree)
        nearer['position'][1] -= 1e-5
        self.assertIn((nearer['id'],'living-east'),L.route_violations([nearer]))
        # Different triangles, coordinates, route name and floor; no asset ids.
        triangles=np.array([[[7,4,3],[8,4,3],[7,5,3]]],float)
        result=nearest_clear_translation(triangles,(-3,-3,3,3),{'other':(7,4,8,5)},{'other':2})
        self.assertGreater(result['distance_m'],.7)
        clean=triangles+np.array(result['translation_m']+[0])
        item=dict(id='other-member',faces=clean.tolist())
        self.assertEqual(L.route_violations([item],{'other':(7,4,8,5)},{'other':2}),[])
        self.assertIsNone(nearest_clear_translation(triangles,(-.1,-.1,.1,.1),{'other':(7,4,8,5)},{'other':2}))
        high=triangles+np.array([0,0,3])
        self.assertEqual(nearest_clear_translation(high,(-3,-3,3,3),{'other':(7,4,8,5)},{'other':2})['distance_m'],0)

    def test_route_reader_node_chain_strided_buffer_and_cache_change_generalise(self):
        import os,struct,tempfile
        import numpy as np
        from archpipe.concept.route_geometry import asset_triangles
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"other-model.gltf";buffer=Path(tmp)/"geometry.bin"
            def write_blob(tip):
                buffer.write_bytes(b"pad!"+b"".join(struct.pack("<4f",*v,99) for v in
                    ((0,0,0),(tip,0,0),(0,1,0))))
            write_blob(1)
            data=dict(buffers=[dict(uri="geometry.bin",byteLength=52)],
                      bufferViews=[dict(buffer=0,byteOffset=4,byteLength=48,byteStride=16)],
                      accessors=[dict(bufferView=0,componentType=5126,count=3,type="VEC3")],
                      meshes=[dict(primitives=[dict(attributes=dict(POSITION=0))])],
                      nodes=[dict(translation=[2,0,4],children=[1]),dict(translation=[0,3,0],mesh=0)],
                      scenes=[dict(nodes=[0])],scene=0)
            path.write_text(json.dumps(data))
            np.testing.assert_allclose(asset_triangles(str(path))[0],[[2,-4,3],[3,-4,3],[2,-4,4]])
            before=buffer.stat().st_mtime_ns
            write_blob(2)
            os.utime(buffer,ns=(before+1000000000,before+1000000000))
            np.testing.assert_allclose(asset_triangles(str(path))[0],[[2,-4,3],[4,-4,3],[2,-4,4]])

    def test_g2_three_species_drifts_pots_and_solar_trellis_allocation(self):
        self.assertEqual(set(self.plan["beds"]), {"north","west"})
        for bed in self.plan["beds"]:
            for layer in ("back","mid","front"):
                drift=[p for p in self.plan["plants"] if p.get("bed")==bed and L.planting_layer(p)==layer]
                self.assertEqual(len(drift),3)
                self.assertEqual(len({p["species"] for p in drift}),1)
        by_id={m["id"]:m for m in self.meshes}
        self.assertEqual(by_id["landscape-climber-west"]["species"],"Trachelospermum jasminoides")
        self.assertEqual(by_id["landscape-climber-north"]["species"],"Bougainvillea glabra")
        self.assertGreater(len(L.direct_sun_hours(18.75,-20.641)),len(L.direct_sun_hours(-.123,-24.65)))
        pots=[m for m in self.meshes if m["part_kind"]=="planter" and "door-pot" in m["id"]]
        self.assertEqual(len(pots),6)
        for pot in pots:
            self.assertEqual(pot["material"],"terracotta-red-glaze")
            self.assertAlmostEqual(min(q[2] for f in pot["faces"] for q in f),L.GROUND)
            self.assertTrue(all(L._rect_overlap_area(L._mesh_rect(pot),bed)==0 for bed in self.plan["beds"].values()))
            self.assertTrue(any(p.get("bed")=="door-pot-"+pot["id"].removeprefix("landscape-door-pot-planter-").removesuffix("-body") for p in self.plan["plants"]))
        self.assertFalse(any("lemon-pot" in m["id"] or "top-tree-pot" in m["id"] or "top-planter-" in m["id"] for m in self.meshes))
        self.assertEqual(L.route_violations(self.other_props+self.plan["objects"]+[p for p in self.plan["plants"] if "faces" in p]), [])

    def test_old_native_jacaranda_enters_building(self):
        draft = dict(id="draft-north-jacaranda",asset="jacaranda_tree",position=[18.30,-21.55,L.GROUND],rotation_deg=[0,0,0],scale=1.0)
        self.assertTrue(any("building footprint" in why for _,why in L.extent_violations([draft])))
        self.assertEqual(L.extent_violations(self.other_props,self.rooms), [])

    def test_old_north_bed_enters_basement_room(self):
        draft = dict(id="draft-searsia",asset="searsia_lucida",position=[13.25,-21.65,L.GROUND+.38],rotation_deg=[0,0,0],scale=.7)
        self.assertTrue(any("dirty-kitchen" in why for _,why in L.extent_violations([draft],self.rooms)))
        self.assertEqual(L.object_extent_violations(self.plan["objects"],self.rooms), [])

    def test_each_climber_branch_stays_on_its_yard_side_trellis_frame(self):
        by_id={m["id"]:m for m in self.meshes}
        self.assertFalse(L.inside_yard(24.891,-20.32))
        self.assertFalse(L.inside_yard(-.39,-25.909))
        frame=by_id["landscape-trellis-west"]
        branches=by_id["landscape-climber-branches-west"]
        fp=[p for f in frame["faces"] for p in f]
        bp=[p for f in branches["faces"] for p in f]
        for axis in (0,1):
            self.assertTrue(all(min(p[axis] for p in fp)-1e-9 <= q[axis] <= max(p[axis] for p in fp)+1e-9 for q in bp))
        self.assertTrue(all(L.inside_yard(p[0],p[1]) for p in bp))

    def test_top_edge_and_rail_line(self):
        bad=dict(id="top-edge",asset="sf_hibiscus",position=[12.72,-21.7,0],rotation_deg=[0,0,0],scale=.7,zone="top")
        self.assertTrue(L.extent_violations([bad],self.rooms))
        self.assertTrue(L.object_extent_violations([dict(id="rail",zone="top",rect=(6.9,-22.5,7.4,-22.0))]))

    def test_g2_sun_screen_and_drift_upper_limit_fail_closed(self):
        west=dict(id="renamed-full-sun-shrub",bed="west",species="Callistemon citrinus",center=(.28,-29.3))
        north=dict(west,id="north-full-sun-shrub",bed="north",center=(18.75,-21.65))
        self.assertTrue(L.sunlight_violations([west]))
        self.assertEqual(L.sunlight_violations([north]), [])
        self.assertTrue(L.sunlight_violations([dict(west,species="Ursinia anthemoides")]))
        overcrowded=[dict(id=str(i),bed="west",layer="mid",species="Ixora coccinea") for i in range(6)]
        self.assertTrue(L.drift_violations(overcrowded))
        self.assertEqual(L.drift_violations(overcrowded[:5]), [])

    def test_real_clump_nonplanar_and_lighting_namespace_defects_cannot_recur(self):
        from archpipe.villa_render_contract import validate_scene
        from archpipe.concept import villa_render as VR
        old=json.loads((Path(__file__).parent/"fixtures/garden-g2-clump-before.json").read_text())
        def errors(mesh):
            scene=dict(schema="villa-render/1",id="clump-proof",north={"model_y_bearing_deg":0},
                       library_root="library",materials=VR.M,meshes=[mesh],lights=[],props=[],models=[],views=[])
            return validate_scene(scene)
        self.assertTrue(any("nonplanar" in e for e in errors(old)))
        self.assertTrue(any("unknown lighting layer" in e for e in errors(old)))
        clumps=[m for m in self.meshes if m["part_kind"]=="plant-clump"]
        for clump in clumps:
            self.assertNotIn("layer",clump)
            self.assertTrue(all(len(f)==3 for f in clump["faces"]))
            self.assertFalse(any("meshes[" in e for e in errors(clump)))
        renamed=dict(clumps[0],id="another-species-instance",layer="front")
        self.assertTrue(any("unknown lighting layer" in e for e in errors(renamed)))

    def test_procedural_clumps_have_recorded_size_and_mutations_fail(self):
        clumps=[m for m in self.meshes if m["part_kind"]=="plant-clump"]
        self.assertEqual(len(clumps),14)
        self.assertEqual(L.dimension_violations(clumps), [])
        for source in clumps[:2]:
            altered=copy.deepcopy(source)
            altered["id"]="other-botanical-clump"
            # Shared-coordinate references are copied into independent
            # mesh vertices before transformation: no repeated transform.
            altered["faces"]=[[[p[0],p[1],L.GROUND+2*(p[2]-L.GROUND)] for p in f] for f in altered["faces"]]
            self.assertTrue(L.dimension_violations([altered]))

    def test_route_real_furniture_footprint_and_quiet(self):
        sofa=dict(id="draft-teak-sofa",rect=(24,-26.25,26.1,-25.4))
        self.assertIn(("draft-teak-sofa","living-east"),L.route_violations([sofa]))
        self.assertEqual(L.route_violations(self.other_props+self.plan["objects"]), [])
        self.assertEqual(L.route_violations([dict(id="clear",rect=(26,-28,26.5,-27.5))]), [])
        for d in (d for d in self.spec["doors"] if d.get("garden")):
            self.assertTrue(any(x0-.001 <= d["x"] <= x1+.001 and y0-.001 <= d["y"] <= y1+.001 for x0,y0,x1,y1 in self.plan["paths"].values()),d)
        self.assertTrue(any(m["part_kind"]=="stepping-stone" and "living-east" in m["id"] for m in self.meshes))

    def test_spacing_real_three_tenths_spread_and_quiet(self):
        a=dict(id="a",bed="east",layer="mid",spread_m=.9,center=(27,-25))
        b=dict(id="b",bed="east",layer="mid",spread_m=.9,center=(27,-24.73))
        self.assertEqual(L.spacing_violations([a,b]),[("a","b",.27,.72)])
        self.assertEqual(L.spacing_violations(self.plan["plants"]), [])
        self.assertEqual(L.spacing_violations([a,dict(b,center=(27,-24.2))]), [])

    def test_drift_real_and_old_alternation_fails(self):
        draft=[dict(id="d-a",bed="west",layer="mid",species="Ixora coccinea"),dict(id="d-b",bed="west",layer="mid",species="Ixora coccinea")]
        self.assertEqual(L.drift_violations(draft),[("west","mid","Ixora coccinea",2)])
        self.assertEqual(L.drift_violations(self.plan["plants"]), [])

    def test_layers_real_and_old_single_row_bed_fails(self):
        draft=[dict(id="old-a",bed="north",layer="mid"),dict(id="old-b",bed="north",layer="mid"),dict(id="old-c",bed="north",layer="mid")]
        self.assertEqual(L.layer_violations(draft,beds=("north",)),[("north",["mid"])])
        clean=draft+[dict(id="back",bed="north",layer="back"),dict(id="front",bed="north",layer="front")]
        self.assertEqual(L.layer_violations(clean,beds=("north",)), [])

    def test_swing_envelope_and_quiet(self):
        swing=next(p for p in self.before["props"] if p["asset"]=="sf_egg_chair")
        x0,y0,x1,y1=L._rect(swing)
        chair=dict(id="draft-chair",rect=(x1+.05,y0,x1+.25,y1))
        self.assertTrue(L.swing_violations(swing,[chair]))
        self.assertEqual(L.swing_violations(swing,[swing]), [])
        self.assertIsNotNone(self.plan["swing"])
        self.assertEqual(L.swing_violations(self.plan["swing"],self.props+self.plan["objects"]+self.plan["plants"]+
            [dict(id="bed-"+name,rect=rect) for name,rect in self.plan["beds"].items()]), [])

    def test_bench_real_seat_height_and_old_slab_fails(self):
        self.assertEqual(L.bench_violations(self.props), [])
        old=L._prop("draft-old-bench","sf_wooden_bench",(10.70,-21.15),0.0,.48,"old scale",zone="top",yaw=90)
        self.assertTrue(L.bench_violations([old]))
        wrong=copy.deepcopy(next(p for p in self.props if p["asset"]=="sf_wooden_bench"))
        wrong["rotation_deg"]=[0,0,90]
        self.assertTrue(L.bench_violations([wrong]))

    def test_standin_real_and_old_mislabelled_tree_fails(self):
        draft=[dict(id="old-north-tree",asset="tree_small_02",label="dressing: Bauhinia variegata; nursery height 2.55 m ASSUMED")]
        self.assertTrue(L.standin_violations(draft))
        self.assertEqual(L.standin_violations(self.props), [])
        self.assertEqual(L.standin_violations([dict(draft[0],label="ASSUMED visual stand-in; Bauhinia variegata")]), [])


if __name__ == "__main__":
    unittest.main()
