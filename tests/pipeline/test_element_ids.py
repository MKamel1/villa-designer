"""Lane P2: element identity on scene meshes. Each rule has a positive and a negative case."""
import pytest

from archpipe.blender import element_ids as EID

IDS = {"furn-lounge-tv", "furn-cinema-desk", "furn-k-island", "lum-DL-lounge-01", "lum-PEN-LIN-dining-01",
       "fixture-gwc-rain-head", "plant-landscape-east-back-00", "garden-bed-north", "room-lounge", "stair-main",
       "wall-B-ext-00", "door-B-a-b", "furn-pd-hang-1"}


def quad(x0, y0, x1, y1, z0, z1):                     # a wall face in the plane y = y0
    return [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]]


def test_registry_exact_and_derived_faces_find_their_element():
    reg = EID.Registry()
    face = quad(0, 0, 4, 0, 0, 2.8)
    reg.add(face, "wall-B-ext-00")
    assert reg.lookup(face) == "wall-B-ext-00"
    backing = [[x, y - 0.001, z] for x, y, z in face]            # the 1 mm construction skin behind it
    assert reg.lookup(backing) == "wall-B-ext-00"


def test_registry_stays_quiet_for_faces_that_are_not_derived():
    reg = EID.Registry()
    reg.add(quad(0, 0, 4, 0, 0, 2.8), "wall-B-ext-00")
    assert reg.lookup(quad(0, 0.05, 4, 0.05, 0, 2.8)) is None    # 50 mm off the plane
    assert reg.lookup(quad(10, 0, 12, 0, 0, 2.8)) is None        # same plane, outside the face
    assert reg.lookup([[0, 0, 5], [4, 0, 5], [4, 1, 5], [0, 1, 5]]) is None


@pytest.mark.parametrize("mesh_id,expected", [
    ("furn-cinema-desk-chair-1-0", "furn-cinema-desk"), ("furn-k-island-stool-2-1", "furn-k-island"),
    ("lens-DL-lounge-01", "lum-DL-lounge-01"), ("wire-PEN-LIN-dining-01--1", "lum-PEN-LIN-dining-01"),
    ("detail-gwc-rain-head-drop", "fixture-gwc-rain-head"), ("landscape-east-back-00", "plant-landscape-east-back-00"),
    ("landscape-edging-north", "garden-bed-north"), ("ceiling-lounge", "room-lounge"),
    ("detail-stair-open-stringer", "stair-main"), ("mirror-k-island", "furn-k-island"),
])
def test_name_rules_resolve(mesh_id, expected):
    assert EID.resolve_name(mesh_id, IDS) == expected


@pytest.mark.parametrize("mesh_id", ["furn-nothing-0", "lens-DL-lounge-99", "rug-lounge", "detail-vent-guest-wc-grille",
                                     "landscape-g6-pergola-post-0", "ceiling-nowhere"])
def test_name_rules_do_not_invent_ids(mesh_id):
    assert EID.resolve_name(mesh_id, IDS) is None


def test_declare_builds_faces_by_element_and_skips_empty_runs():
    out = EID.declare([(0, 6, "door-B-a-b"), (6, 6, "door-B-a-c"), (6, 12, None), (12, 18, "door-B-a-b")])
    assert out == dict(element_ids=["door-B-a-b"], faces_by_element={"door-B-a-b": [*range(0, 6), *range(12, 18)]})
    assert EID.declare([(0, 0, "x")]) == {}


def test_attach_strip_roundtrip_and_coverage():
    reg = EID.Registry()
    wall = quad(0, 0, 4, 0, 0, 2.8)
    reg.add(wall, "wall-B-ext-00")
    scene = dict(meshes=[
        dict(id="shell-001-x", group="shell", faces=[wall, quad(9, 9, 10, 9, 0, 1)]),
        dict(id="lens-DL-lounge-01", group="fixture", faces=[wall] * 2),
        dict(id="detail-skirting-B", group="shell", faces=[wall] * 3),
        dict(id="rug-lounge", group="furniture", faces=[wall]),
        dict(id="ceiling-lounge", group="shell", faces=[wall])])
    original = [dict(m) for m in scene["meshes"]]
    EID.attach(scene, reg, IDS, {"detail-skirting-B": EID.declare([(0, 1, "room-lounge"), (1, 3, "room-lounge")])})
    m = {x["id"]: x for x in scene["meshes"]}
    assert m["shell-001-x"]["element_ids"] == ["wall-B-ext-00"] and m["shell-001-x"]["faces_by_element"] == {"wall-B-ext-00": [0]}
    assert m["lens-DL-lounge-01"]["element_ids"] == ["lum-DL-lounge-01"]
    assert m["detail-skirting-B"]["element_id_basis"] == "declared"
    assert m["rug-lounge"]["element_ids"] == [] and m["rug-lounge"]["element_id_basis"] == "unresolved"
    assert m["ceiling-lounge"]["element_ids"] == ["room-lounge"]      # not mistaken for the coincident wall face
    cov = EID.coverage(scene["meshes"], IDS)
    assert cov["shell"] == dict(meshes=3, faces=6, with_id=5, with_model_id=5)    # 1 of the 2 shell-001 faces is untracked
    assert cov["furniture"]["with_id"] == 0
    for mesh in scene["meshes"]:
        EID.strip(mesh)
    assert scene["meshes"] == original


def test_faces_of_returns_only_the_elements_faces():
    wall, other = quad(0, 0, 4, 0, 0, 2.8), quad(9, 9, 10, 9, 0, 1)
    scene = dict(meshes=[dict(id="a", faces=[wall, other], element_ids=["w1", "w2"], faces_by_element={"w1": [0], "w2": [1]}),
                         dict(id="b", faces=[wall], element_ids=["w1"])])
    assert [(m["id"], f) for m, f in EID.faces_of(scene, "w1")] == [("a", [wall]), ("b", [wall])]
    assert EID.faces_of(scene, "w3") == []


def test_replay_refuses_a_shell_whose_call_order_changed():
    from archpipe.concept import revit_spec as RS, villa_r11 as R
    lay = R.design("D1")
    sp = RS.build(lay)
    with pytest.raises(ValueError, match="Scene.add calls"):
        EID.shell_owners(type("S", (), {"faces": []})(), [(0, 0)], sp, lay)


def test_real_shell_every_face_has_an_owner_inside_its_element():
    """Independent check on D1: wall faces lie in the wall's footprint, door/window faces in their opening."""
    from archpipe.concept import revit_spec as RS, villa_r11 as R, villa_daylight as VD
    from archpipe.model import spec_source as SS
    lay = R.design("D1")
    sp = RS.build(lay)
    with EID.trace_adds() as calls:
        shell = VD.scene(lay)
    owners = EID.shell_owners(shell, calls, sp, lay)
    assert len(owners) == len(shell.faces) and all(owners)
    walls = {e.id: e for e in SS.walls(sp)}
    openings = {e.id: e for e in SS.doors(sp, list(walls.values())) + SS.windows(sp, list(walls.values()))}
    assert openings and any(o in openings for o in owners)
    for face, owner in zip(shell.faces, owners):
        if owner in walls:
            p = walls[owner].params
            t = p["thickness_mm"] / 2000 + 0.01
            x0, x1 = sorted((p["x0_mm"] / 1000, p["x1_mm"] / 1000))
            y0, y1 = sorted((p["y0_mm"] / 1000, p["y1_mm"] / 1000))
            assert all(x0 - t <= q[0] <= x1 + t and y0 - t <= q[1] <= y1 + t for q in face.points), owner
        if owner in openings:
            o = openings[owner]
            assert face.material in ("door", "glass"), owner
            assert abs(face.points[0][0] - o.placement[0] / 1000) < o.size[0] / 1000 + 0.2 or \
                abs(face.points[0][1] - o.placement[1] / 1000) < o.size[0] / 1000 + 0.2, owner


def test_contract_ignores_the_new_fields():
    from archpipe import villa_render_contract as C
    plain = dict(id="m", group="shell", material="paint", faces=[[[0, 0, 0]]])
    tagged = dict(plain, element_ids=["wall-B-ext-00"], faces_by_element={"wall-B-ext-00": [0]}, element_id_basis="declared")
    assert C.mesh_batch_key(plain, "diffuse") == C.mesh_batch_key(tagged, "diffuse")
