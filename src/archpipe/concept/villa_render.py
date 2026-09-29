"""D1 render scene (Phase 3/4): the design as a `villa-render/1` scene for the renderer (docs/villa-render-scene.md).

Everything the image shows comes from here, and every piece says what it is:
  - the SHELL is the daylight study's validated scene (`villa_daylight.scene`: walls with every opening placed = spec,
    slabs, columns, stair, ramp, deck and the whole context), re-materialised per room;
  - FINISHES per room (`FINISH`), chosen from the client's taste profile (knowledge/projects/villa-01/taste.json:
    warm contemporary, large-format stone, walnut, oak, boucle, brass, LED coves) — the questionnaire had no finishes
    answers, so they are ASSUMED and listed in every caption; walls and ceilings keep reflectance 0.80 / 0.85, the
    daylight study's assumption, except where stated (bathroom stone, cinema fabric, feature panels);
  - FALSE CEILINGS at 2.70 m and the coves (villa_lighting), FEATURE PANELS (walnut fluted TV wall, oak slatted
    headboard wall) and the GUARD round the stair opening (required, not yet in the Revit model) are DETAILS added
    here and labelled as such;
  - FURNITURE is villa_furnish3d (the checked layout); the assumed garden and
    outdoor teak lounge come from villa_landscape within the modeled yard;
  - LIGHTS are villa_lighting (verified iGuzzini products where bound, generic photometry otherwise, named);
  - DRESSING (plants, books, vases, art) is listed as dressing, not design.
Units metres, model axes, z absolute (GF FFL 0, basement FFL -3.0).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .. import daylight as D
from .. import villa_env as E
from . import revit_spec as RS
from . import villa_daylight as VD
from . import villa_furnish as F
from . import villa_furnish3d as F3
from . import villa_lighting as VL
from . import villa_r11 as R

LZ = {"B": -3.0, "GF": 0.0}
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "out" / "villa" / "render-d1"

# ------------------------------------------------------------------ materials (linear rgb; reflectance = target mean)
M = {
    "plaster-warm-white": dict(kind="principled", base_rgb=[0.80, 0.785, 0.755], reflectance=0.80,
                               roughness=0.85, note="warm white matt emulsion on smooth gypsum plaster (0.80); "
                                                    "the first version used a rough plaster photo-texture: painted "
                                                    "walls are smooth"),
    "ceiling-white": dict(kind="principled", base_rgb=[0.86, 0.85, 0.83], reflectance=0.85, roughness=0.95,
                          note="gypsum false ceiling, matt white (0.85)"),
    "travertine": dict(kind="principled", asset="Marble014", base_rgb=[0.66, 0.63, 0.57], reflectance=0.55,
                       roughness=0.35, tile_m=1.2, note="honed cream stone, large format (ASSUMED; the first "
                                                          "texture read pink)"),
    "oak-floor": dict(kind="principled", asset="oak_wood_planks", base_rgb=[0.45, 0.33, 0.22], reflectance=0.33,
                      roughness=0.5, tile_m=1.20, grain_axis="x",
                      note="light oak engineered planks (ASSUMED); Poly Haven oak_wood_planks, real scan 1.20 m"),
    "marble-ensuite": dict(kind="principled", asset="Marble020", base_rgb=[0.66, 0.60, 0.52], reflectance=0.58,
                           roughness=0.25, tile_m=1.2, note="warm cream marble, large format (ASSUMED)"),
    "marble-bath": dict(kind="principled", asset="Marble014", base_rgb=[0.70, 0.66, 0.58], reflectance=0.62,
                        roughness=0.3, tile_m=1.2, note="cream marble, large format (ASSUMED)"),
    "marble-white": dict(kind="principled", asset="Marble012", base_rgb=[0.78, 0.78, 0.76], reflectance=0.72,
                         roughness=0.18, tile_m=1.4, note="white veined stone worktops (ASSUMED)"),
    # Client (2026-09-28): "for all the wood in the villa use a more natural texture it looks annoyingly fake". The
    # ambientCG Wood0xx sets above were a repeating printed-looking stripe; replaced with Poly Haven scanned veneers
    # (CC0, ops/workstation/library-manifest.json). tile_m is each asset's own real-world scan size
    # (api.polyhaven.com/info/<id> "dimensions", already in metres/mm as published) so the grain repeats at the size
    # it was actually cut, not an assumed one. The old `contrast` field pulled the photo toward its own mean colour
    # to hide the previous texture's printed striping; these are real scans (not tileable-repeat placeholders), so
    # it is REMOVED here (full photographed contrast kept) -- I could not preview the rendered result on this
    # machine, so this is a judgement call, not a measured one; check the next render for busy/repeating grain
    # before a client review.
    "walnut": dict(kind="principled", asset="natural_walnut_veneer", base_rgb=[0.20, 0.11, 0.06], reflectance=0.12,
                   roughness=0.45, tile_m=1.00, grain_axis="z",
                   note="walnut veneer joinery (ASSUMED); Poly Haven natural_walnut_veneer, real scan 1.00 m"),
    "oak": dict(kind="principled", asset="white_oak_veneer", base_rgb=[0.52, 0.40, 0.27], reflectance=0.40,
                roughness=0.5, tile_m=0.50, grain_axis="z",
                note="light oak veneer (ASSUMED); Poly Haven white_oak_veneer (paler than door-oak, per its own "
                     "'light oak' note), real scan 0.50 m"),
    "greige-lacquer": dict(kind="principled", base_rgb=[0.46, 0.42, 0.37], reflectance=0.43, roughness=0.35,
                           note="matt greige lacquer kitchen fronts (ASSUMED)"),
    "boucle": dict(kind="principled", asset="Fabric082A", base_rgb=[0.74, 0.70, 0.64], reflectance=0.66,
                   roughness=0.95, tile_m=0.3, note="cream boucle upholstery (ASSUMED)"),
    "linen": dict(kind="principled", asset="Fabric036", base_rgb=[0.55, 0.50, 0.43], reflectance=0.48,
                  roughness=0.95, tile_m=0.3, note="oatmeal linen upholstery (ASSUMED)"),
    "sage-fabric": dict(kind="principled", asset="Fabric066", base_rgb=[0.40, 0.44, 0.36], reflectance=0.38,
                        roughness=0.95, tile_m=0.3, note="sage cotton (kids, ASSUMED)"),
    "charcoal-fabric": dict(kind="principled", asset="Fabric030", base_rgb=[0.07, 0.07, 0.07], reflectance=0.07,
                            roughness=0.95, tile_m=0.4, note="charcoal acoustic fabric (cinema walls and loveseat; "
                                                             "0.07, not the 0.80 wall assumption: a media room)"),
    "taupe-fabric": dict(kind="principled", asset="Fabric036", base_rgb=[0.33, 0.28, 0.23], reflectance=0.25,
                         roughness=0.95, tile_m=0.4, note="warm taupe acoustic fabric panels (cinema walls, 0.25; the "
                                                           "first choice, charcoal 0.07, left the room unreadable)"),
    "bedding-white": dict(kind="principled", asset="Fabric081C", base_rgb=[0.82, 0.81, 0.78], reflectance=0.78,
                          roughness=0.95, tile_m=0.18, note="white cotton bedding (dressing of the bed, ASSUMED weave scale)"),
    "throw-taupe": dict(kind="principled", asset="Fabric036", base_rgb=[0.34, 0.29, 0.25], reflectance=0.28,
                         roughness=0.92, tile_m=0.22, note="ASSUMED woven taupe bed throw, dressing"),
    "rug": dict(kind="principled", asset="Carpet016", base_rgb=[0.62, 0.58, 0.51], reflectance=0.55, roughness=1.0,
                tile_m=0.8, note="wool rug (ASSUMED)"),
    "leather-brown": dict(kind="principled", asset="Leather030", base_rgb=[0.14, 0.08, 0.05], reflectance=0.10,
                          roughness=0.5, tile_m=0.5, note="cognac leather (ASSUMED)"),
    "brass": dict(kind="principled", base_rgb=[0.80, 0.62, 0.34], reflectance=0.62, roughness=0.3, metallic=1.0,
                  note="brushed brass (flat, no texture held)"),
    "black-metal": dict(kind="principled", base_rgb=[0.03, 0.03, 0.03], reflectance=0.03, roughness=0.4,
                        metallic=1.0, note="black powder-coat metal"),
    "ceramic-white": dict(kind="principled", base_rgb=[0.85, 0.85, 0.84], reflectance=0.84, roughness=0.08,
                          note="glazed sanitary ceramic"),
    "screen-black": dict(kind="principled", base_rgb=[0.01, 0.01, 0.01], reflectance=0.01, roughness=0.05,
                         note="TV screen (off)"),
    "glass-clear": dict(kind="glass", base_rgb=[1, 1, 1], transmittance=0.70, interfaces=1, roughness=0.0,
                        note="clear double glazing, Tv 0.70 (Metric Handbook p. 9-8, the daylight study's value)"),
    "glass-guard": dict(kind="glass", base_rgb=[1, 1, 1], transmittance=0.85, interfaces=2, roughness=0.0,
                        note="laminated glass guard"),
    "glass-edge": dict(kind="principled", base_rgb=[0.58, 0.69, 0.65], reflectance=0.55,
                       roughness=0.12, note="ASSUMED polished laminated-glass exposed edge"),
    "opal-strip": dict(kind="principled", base_rgb=[0.88, 0.85, 0.78], reflectance=0.78,
                       roughness=0.32, note="ASSUMED opal diffuser over the designed cabinet LED strip"),
    "silvered-mirror": dict(kind="principled", base_rgb=[0.91, 0.92, 0.92], reflectance=0.92,
                            roughness=0.035, metallic=1.0, note="ASSUMED silvered glass vanity mirror"),
    "door-oak": dict(kind="principled", asset="oak_veneer_01", base_rgb=[0.52, 0.40, 0.27], reflectance=0.40,
                     roughness=0.5, tile_m=1.83, grain_axis="z",
                     note="flush oak veneer door, closed (ASSUMED); Poly Haven oak_veneer_01 (medium oak, not the "
                          "paler 'oak' joinery), real scan 1.83 m"),
    "render-exterior": dict(kind="principled", base_rgb=[0.65, 0.65, 0.65], reflectance=0.65,
                            roughness=0.85, note="neutral smooth mineral render on neighbouring buildings and apartment (ASSUMED)"),
    "paint-exterior-grey-green": dict(kind="principled", base_rgb=[0.590, 0.672, 0.605], reflectance=0.65,
                                       roughness=0.82, note="ASSUMED very light grey with a green cast (G/R 1.14: at 1.06 the tint vanished under the sun in the finals), smooth mineral exterior paint; stated reflectance 0.65; our exterior and boundary walls"),
    "paving": dict(kind="principled", asset="PavingStones146", base_rgb=[0.62, 0.58, 0.52], reflectance=0.45,
                   roughness=0.8, tile_m=2.0, note="light stone paving (garden terrace, ASSUMED)"),
    "garden-gravel": dict(kind="principled", asset="gravel_ground_01", base_rgb=[0.47, 0.43, 0.36],
                          reflectance=0.32, roughness=1.0, tile_m=2.0, note="ASSUMED gravel beds, CC0 scan"),
    "artificial-grass": dict(kind="principled", base_rgb=[0.18, 0.30, 0.12], reflectance=0.22,
                             roughness=0.95, note="ASSUMED drained artificial grass; client 2026-09-29"),
    "stepping-stone": dict(kind="principled", base_rgb=[0.62, 0.58, 0.50], reflectance=0.45,
                           roughness=0.85, note="ASSUMED flush honed sandstone stepping stones"),
    "trellis": dict(kind="principled", base_rgb=[0.16, 0.12, 0.08], reflectance=0.13,
                    roughness=0.7, note="ASSUMED timber wall trellis"),
    "bougainvillea-bract": dict(kind="principled", base_rgb=[0.58, 0.035, 0.25], reflectance=0.20,
                                roughness=0.85, note="ASSUMED procedural Bougainvillea glabra magenta bract mass"),
    "garden-pebbles": dict(kind="principled", asset="floor_pebbles_01", base_rgb=[0.48, 0.46, 0.41],
                           reflectance=0.36, roughness=0.9, tile_m=1.5, note="ASSUMED pebble path joints, CC0 scan"),
    "garden-sandstone": dict(kind="principled", asset="sandstone_cracks", base_rgb=[0.60, 0.52, 0.40],
                             reflectance=0.42, roughness=0.85, tile_m=1.0, note="ASSUMED raised sandstone planters"),
    "lawn": dict(kind="principled", asset="Grass004", base_rgb=[0.10, 0.16, 0.05], reflectance=0.12,
                 roughness=1.0, tile_m=2.0, note="lawn (ASSUMED)"),
    "outdoor-fabric": dict(kind="principled", asset="Fabric036", base_rgb=[0.62, 0.58, 0.50], reflectance=0.55,
                           roughness=0.95, tile_m=0.3, note="ASSUMED outdoor acrylic fabric (garden lounge)"),
    "teak": dict(kind="principled", asset="teak_veneer", base_rgb=[0.35, 0.22, 0.12], reflectance=0.22, roughness=0.6,
                 tile_m=1.00, grain_axis="x", note="ASSUMED teak frame (garden lounge); Poly Haven teak_veneer, real scan 1.00 m"),
    "alu-bronze": dict(kind="principled", base_rgb=[0.10, 0.09, 0.08], reflectance=0.09, roughness=0.35,
                       metallic=1.0, note="dark bronze anodised aluminium window and door frames (ASSUMED)"),
    "paint-white-satin": dict(kind="principled", base_rgb=[0.82, 0.81, 0.79], reflectance=0.80, roughness=0.35,
                              note="white satin paint (skirting, architraves)"),
    "white-paint-joinery": dict(kind="principled", base_rgb=[0.80, 0.79, 0.76], reflectance=0.78, roughness=0.4,
                                note="white painted joinery (bunk bed, shelving)"),
    # Curtains (client 2026-09-28): sheer + a heavy layer on a ceiling track in every bedroom/living-space window and
    # glazed garden door (see the `curtains` list below). "translucent" mixes the stated opaque colour with a
    # Translucent BSDF by `transmittance`; the ADR-0013 photo-texture pipeline in villa_scene.add_material was
    # extended to that kind so these keep a scanned weave like every other fabric here. tile_m is each asset's own
    # scanned physical size (api.polyhaven.com/info/<id> "dimensions"): a fine weave photographed close-up, so it
    # tiles many times across a curtain width -- unlike a wood veneer, a repeating weave is correct, not a defect.
    "curtain-sheer": dict(kind="translucent", asset="rough_linen", base_rgb=[0.86, 0.84, 0.79], reflectance=0.70,
                          transmittance=0.55, roughness=0.85, tile_m=0.27,
                          note="ASSUMED sheer linen curtain, transmittance 0.55 (daylight diffusion / daytime "
                               "privacy, open at the sides in every state); Poly Haven rough_linen, real scan 0.27 m"),
    # Notes avoid the words "dark"/"black" on purpose: render_qa.finish_matches_name treats either word in an
    # overridden material's note as a claim that the finish itself renders near-black (luminance <= 0.15, written
    # for "black-metal" / "dark bronze"). "Blackout" describes the lining's OPACITY (function), not its colour --
    # a taupe fabric matching the room -- and tripped that check as a false positive on the first render.
    "curtain-heavy": dict(kind="translucent", asset="crepe_satin", base_rgb=[0.40, 0.36, 0.31], reflectance=0.32,
                          transmittance=0.02, roughness=0.6, tile_m=0.266,
                          note="ASSUMED heavy curtain (bedrooms): opaque light-blocking lining, transmittance "
                               "0.02; Poly Haven crepe_satin, real scan 0.266 m"),
    "curtain-heavy-dimout": dict(kind="translucent", asset="crepe_satin", base_rgb=[0.40, 0.36, 0.31],
                                 reflectance=0.32, transmittance=0.10, roughness=0.6, tile_m=0.266,
                                 note="ASSUMED heavy curtain (living spaces): dim-out lining, transmittance 0.10 "
                                      "(fuller opacity reserved for bedrooms); Poly Haven crepe_satin, real scan "
                                      "0.266 m"),
}
M["oak-grain-x"] = dict(M["oak"], grain_axis="x", note="ASSUMED light oak veneer, grain along horizontal bed frame")
M["walnut-grain-x"] = dict(M["walnut"], grain_axis="x", note="ASSUMED walnut veneer, grain along horizontal tops and shelves")
# Client (2026-09-28): tread wood and the ensuite vanity front read as long smeared streaks, "annoyingly fake".
# Confirmed by archpipe.blender.grain.mapping_rotated_span (pure-Python, tests/test_render_standard.py): plain
# "walnut" (grain_axis="z") sends one of the tread top face's two sampled coordinates to the tread's own 60 mm
# thickness -- a single texel row, stretched across the whole 900 mm tread. grain_axis="y" does not (it is the
# rotation that instead sends the tread's 900 mm length to the image's own grain axis, so the wood now grains
# along the tread, at the veneer's real scan scale, not across it).
M["walnut-grain-y"] = dict(M["walnut"], grain_axis="y", note="ASSUMED walnut veneer, grain along the tread's "
                           "own 900 mm length (stair treads only; see mapping_rotated_span)")

# room -> (floor, wall, ceiling) finishes
PUBLIC_B = ("lounge", "lounge-nook", "stair-b", "hall-b", "entry-b", "family", "kitchen", "kitchen-island", "dining",
            "dining-side", "living", "bar-alcove", "dirty-kitchen", "pantry", "store-ramp")
FINISH = {r: ("travertine", "plaster-warm-white", "ceiling-white") for r in PUBLIC_B}
FINISH.update({
    "cinema": ("rug", "taupe-fabric", "ceiling-white"),
    "guest-wc": ("marble-bath", "marble-bath", "ceiling-white"),
    "family-bath": ("marble-bath", "marble-bath", "ceiling-white"),
    "parents-ensuite": ("marble-bath", "marble-bath", "ceiling-white"),     # Marble020 read pink
})
for r in ("landing-gf", "corridor", "gallery-end", "study-game", "kids-a", "kids-b", "parents-bed", "parents-entry",
          "parents-dressing", "parents-dressing-ext"):
    FINISH[r] = ("oak-floor", "plaster-warm-white", "ceiling-white")
UNDER_SOFFIT = ("cinema", "store-ramp", "guest-wc", "dirty-kitchen")   # ceiling = the ramp/deck soffit lining
# Curtains (client 2026-09-28): every window/glazed garden door in a room of one of these occupancies gets a
# curtain -- "bedrooms + living spaces". Kitchens ("kitchen"/"utility"), sanitary rooms ("wc"/"bathroom"/"ensuite")
# and circulation ("stair") are deliberately excluded even though some carry windows.
CURTAIN_OCC = ("bedroom", "living", "dining", "study")


# ------------------------------------------------------------------ geometry helpers
def box_faces(x0, y0, z0, x1, y1, z1):
    """Six outward CCW quads of an axis-aligned box."""
    return [[[x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [x1, y0, z0]],          # bottom (normal -z)
            [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]],          # top
            [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]],          # -y
            [[x1, y1, z0], [x0, y1, z0], [x0, y1, z1], [x1, y1, z1]],          # +y
            [[x0, y1, z0], [x0, y0, z0], [x0, y0, z1], [x0, y1, z1]],          # -x
            [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]]]          # +x


def quad_up(x0, y0, x1, y1, z):
    return [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]]


def quad_down(x0, y0, x1, y1, z):
    return [[x0, y0, z], [x0, y1, z], [x1, y1, z], [x1, y0, z]]


def disc_down(cx, cy, z, r, n=16):
    return [[[cx + r * math.cos(-2 * math.pi * k / n), cy + r * math.sin(-2 * math.pi * k / n), z] for k in range(n)]]


def sphere(cx, cy, cz, r, nu=16, nv=10):
    faces = []
    for j in range(nv):
        t0, t1 = math.pi * j / nv, math.pi * (j + 1) / nv
        for i in range(nu):
            p0, p1 = 2 * math.pi * i / nu, 2 * math.pi * (i + 1) / nu
            pts = []
            for t, p in ((t0, p0), (t1, p0), (t1, p1), (t0, p1)):
                pts.append([round(cx + r * math.sin(t) * math.cos(p), 5), round(cy + r * math.sin(t) * math.sin(p), 5),
                            round(cz + r * math.cos(t), 5)])
            uniq = [q for k, q in enumerate(pts) if q not in pts[:k]]
            if len(uniq) >= 3:
                faces.append(uniq)
    return faces


def _normal(pts):
    nx = ny = nz = 0.0
    for a, b in zip(pts, pts[1:] + pts[:1]):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / L, ny / L, nz / L


def _room_at(lay, x, y, z):
    lv = "B" if z < -0.05 else ("GF" if z < 2.85 else None)
    if lv is None:
        return None
    best = None
    for rid, r in lay["rooms"].items():
        if r["level"] != lv:
            continue
        x0, y0, x1, y1 = r["rect"]
        if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            if best is None or r.get("part_of") is None:
                best = rid
    return best


def _environment_face_sources():
    """Recover source IDs from the same environment prisms used by the daylight scene.

    The daylight Face has only a material tag; its source ID must be recovered
    from the authored geometry, not inferred from a face's position.
    """
    sources = {}
    for element in E.spec()["elements"]:
        if element.get("kind") != "box":
            continue
        faces = D.prism_z(VD._m(element["pts"]), element["z0"] / 1000,
                          element["z1"] / 1000, "context", "context", "context")
        for face in faces:
            sources[tuple(face.points)] = element["id"]
    return sources


# ------------------------------------------------------------------ the scene
def build(lay=None, views=None):
    lay = lay or R.design("D1")
    sp = RS.build(lay)
    meshes, notes = [], []
    mats = dict(M)

    views = views if views is not None else VIEWS(lay)
    doorway_cams = {v["id"]: v["camera"]["position"][:3] for v in views if v["camera"].get("reframed") == "doorway"}
    SOFT = {"boucle", "linen", "sage-fabric", "taupe-fabric", "charcoal-fabric", "bedding-white", "outdoor-fabric"}

    def mesh(mid, mat, faces, group, room=None, label=None, **kw):
        if group in ("furniture", "dressing") and "bevel_m" not in kw and mat not in ("glass-guard", "rug"):
            # real pieces have no knife edges: 4 mm on hard pieces, soft rounded edges on upholstery and bedding
            if mat in SOFT:
                kw.update(bevel_m=0.02, subdivide=1)
            else:
                kw.update(bevel_m=0.004)
        meshes.append(dict(id=mid, group=group, material=mat, room=room, label=label or mid, faces=faces, **kw))

    # ---- shell: the daylight scene's faces, re-materialised
    shell = VD.scene(lay)
    environment_sources = _environment_face_sources()
    stair_boxes = [[v / 1000.0 for v in b] for b in sp["stair"]]
    buckets = {}
    for f in shell.faces:
        pts = [list(p) for p in f.points]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        cz = sum(p[2] for p in pts) / len(pts)
        mat, room = None, None
        source = environment_sources.get(tuple(tuple(p) for p in f.points))
        boundary = source is not None and (source.startswith("fence-") or source == "yard-wall-ne")
        if any(all(b[0] - 1e-3 <= p[0] <= b[3] + 1e-3 and b[1] - 1e-3 <= p[1] <= b[4] + 1e-3 and
                   b[2] - 1e-3 <= p[2] <= b[5] + 1e-3 for p in pts) for b in stair_boxes):
            mat = "walnut-grain-y"                                # the floating treads: grain along the tread's length
        elif f.material == "glass":
            mat = "glass-clear"
        elif f.material == "door":
            n = _normal(pts)
            room = _room_at(lay, cx + 0.06 * n[0], cy + 0.06 * n[1], cz)
            mat = "door-oak"
            # a camera standing in this door's opening: the door is open for that view (its leaf is hidden there
            # and stated in the caption); every other view keeps it closed
            # the same storey only (a basement camera opened the ground-floor door above it)
            opened = [vid for vid, (px, py, pz) in doorway_cams.items()
                      if math.hypot(cx - px, cy - py) < 0.9 and abs(cz - (pz - 0.3)) < 1.5]
            if opened:
                room = "open-for:" + ",".join(opened)
        elif f.material in ("context", "white"):
            n = _normal(pts)
            inside = _room_at(lay, cx + 0.06 * n[0], cy + 0.06 * n[1], cz + 0.06 * n[2])
            # the kept beams and columns are context solids: inside a room they are plastered and painted
            mat = ("paint-exterior-grey-green" if boundary else
                   "plaster-warm-white" if inside in FINISH and source is not None and
                   source.startswith("beam-0-") else
                   "paint-exterior-grey-green" if source is not None and source.startswith("beam-0-") else
                   "paving" if source == "entrance-steps" else "render-exterior")
            room = inside if inside in FINISH else None
        elif f.material == "ground":
            mat = "paving"
        elif f.material in ("floor", "ceiling"):
            # by the face's real normal: the daylight scene's ramp prism carries its tags inverted (harmless in
            # Radiance, whose materials are two-sided; the cinema soffit rendered as floor stone)
            n = _normal(pts)
            if n[2] < -0.5:
                mat = "ceiling-white"
            elif n[2] > 0.5:
                above = _room_at(lay, cx, cy, cz + 0.1)
                mat = "travertine" if above in FINISH else "paving"
            else:
                mat = "paint-exterior-grey-green"   # exposed slab / ramp edge, ASSUMED painted finish
        elif _normal(pts)[2] < -0.5:                            # a downward face (the sloped ramp soffit over the
            mat = "ceiling-white"                               # cinema was dressed as wall fabric): a ceiling
        else:                                                    # "wall": our walls, columns, infills, rails
            n = _normal(pts)
            room = _room_at(lay, cx + 0.06 * n[0], cy + 0.06 * n[1], cz)
            mat = FINISH[room][1] if room in FINISH else "paint-exterior-grey-green"
        key = (mat, room if mat not in ("render-exterior", "paint-exterior-grey-green", "paving", "travertine", "ceiling-white", "glass-clear")
               else None, source)
        buckets.setdefault(key, []).append(pts)
    hide = {}
    for k, ((mat, room, source), faces) in enumerate(sorted(buckets.items(), key=lambda kv: (kv[0][0], kv[0][1] or "", kv[0][2] or ""))):
        grp = "context" if mat == "render-exterior" else "shell"
        if room and room.startswith("open-for:"):
            mid = "door-open-%03d" % k
            mesh(mid, mat, faces, grp, label="door leaf, open in " + room[9:], keep_object=True)
            for vid in room[9:].split(","):
                hide.setdefault(vid, []).append(mid)
            continue
        mesh("shell-%03d-%s" % (k, mat), mat, faces, grp, room=room, label=room or mat,
             source_id=source or "villa-shell")
    notes.append("ASSUMED exterior finish: our walls, ground-floor perimeter beams, exposed slab/ramp edges and boundary/fence walls use smooth very light grey-green mineral paint, reflectance 0.65. Entrance steps are paved; soffits are painted white. Neighbour and apartment context remains neutral mineral render; all exposed construction faces receive a stated finish.")
    for v in views:
        if v["id"] in hide:
            v["hide_meshes"] = hide[v["id"]]
            v.setdefault("caption_notes", []).append("Taken from the doorway with the door open (its leaf not shown).")

    # ---- per-room floor finishes (2 mm over the slab) and false ceilings / coves
    cove_rooms = {f.extra.get("cove_room") for f in VL.design(lay) if f.kind == "COVE" and f.extra.get("cove_room")}
    for rid, r in lay["rooms"].items():
        if rid not in FINISH:
            continue
        x0, y0, x1, y1 = F.clear_rect(lay, rid)
        z = LZ[r["level"]]
        if rid not in ("stair-b",):
            mesh("floor-" + rid, FINISH[rid][0], [quad_up(x0, y0, x1, y1, z + 0.002)], "shell", room=rid,
                 label=rid)
        if rid in UNDER_SOFFIT or rid in ("stair-b",):
            continue
        zc = z + VL.CEILING
        if rid in cove_rooms:
            b = VL.COVE_BAND
            ring = [quad_down(x0, y0, x1, y0 + b, zc), quad_down(x0, y1 - b, x1, y1, zc),
                    quad_down(x0, y0 + b, x0 + b, y1 - b, zc), quad_down(x1 - b, y0 + b, x1, y1 - b, zc)]
            lip = []                                              # the fascia hiding the strip, 80 mm
            for (xa, ya, xb, yb) in ((x0 + b, y0 + b, x1 - b, y0 + b), (x1 - b, y1 - b, x0 + b, y1 - b),
                                     (x0 + b, y1 - b, x0 + b, y0 + b), (x1 - b, y0 + b, x1 - b, y1 - b)):
                lip.append([[xa, ya, zc], [xb, yb, zc], [xb, yb, zc + 0.08], [xa, ya, zc + 0.08]])
            mesh("ceiling-" + rid, "ceiling-white", ring + lip, "shell", room=rid,
                 label="detail: cove ceiling (band at 2.70, field 2.80)")
        else:
            mesh("ceiling-" + rid, "ceiling-white", [quad_down(x0, y0, x1, y1, zc)], "shell", room=rid,
                 label="detail: false ceiling 2.70")
    notes.append("False ceilings at 2.70 m (plenum for the flush fittings; the daylight study assumed 2.80 m).")

    # ---- feature panels and the guard (details added here)
    it = {i["id"]: i for i in F.layout(lay)}
    L = F.clear_rect(lay, "lounge")
    tv = F.footprint(it["lounge-tv"])
    faces = []
    for k in range(int((tv[2] + 0.6 - (tv[0] - 0.6)) / 0.06)):
        xa = tv[0] - 0.6 + k * 0.06
        faces += box_faces(xa, L[3] - 0.04, LZ["B"], xa + 0.04, L[3], LZ["B"] + VL.CEILING)
    mesh("detail-tv-fluting", "walnut", faces, "furniture", room="lounge", label="detail: walnut fluted TV wall")
    PB = F.clear_rect(lay, "parents-bed")
    bed = F.footprint(it["pb-bed"])
    faces = []
    # only where the head wall is SOLID wall: the first run went 0.6 m past the bed each way and closed the
    # parents' entry opening and the dressing door (client: "Parent's room entrance is blocked")
    solid = [(w[0], w[2]) for w in F._walls(sp, "GF") if abs(w[3] - PB[1]) < 0.06 or abs(w[1] - PB[1]) < 0.06]
    for k in range(int((bed[2] + 0.9 - (bed[0] - 0.6)) / 0.05)):
        xa = bed[0] - 0.6 + k * 0.05
        if not any(a0 <= xa and xa + 0.03 <= a1 for a0, a1 in solid):
            continue
        faces += box_faces(xa, PB[1], 0.0, xa + 0.03, PB[1] + 0.03, 2.10)   # partial height (advisory M-HEADWALL)
    mesh("detail-headboard-slats", "oak", faces, "furniture", room="parents-bed",
         label="detail: oak slatted headboard wall")
    op = sp["gf_opening"]
    gz = 0.0
    guard = [[[op[0], op[3], gz], [op[2], op[3], gz], [op[2], op[3], gz + 1.1], [op[0], op[3], gz + 1.1]],
             [[op[2], op[1], gz], [op[2], op[3], gz], [op[2], op[3], gz + 1.1], [op[2], op[1], gz + 1.1]]]
    mesh("detail-stair-guard", "glass-guard", guard, "furniture", room="stair-gf",
         label="detail: 1.1 m glass guard at the stair opening (required; not yet in the Revit model)")
    # ASSUMED construction details: open risers remain visible between the steel members.
    treads = sorted(([v / 1000.0 for v in b] for b in sp["stair"] if b[5] - b[2] < 300), key=lambda b: b[0])
    wall_y = -28.671                         # party-wall face; the tread edge is at -28.421
    open_y = treads[0][4]
    for n, t in enumerate(treads):
        xa, ya, za, xb, yb, zb = t
        mesh("detail-stair-wall-stringer-%02d" % n, "black-metal",
             box_faces(xa, wall_y, za - 0.12, xb, ya + 0.025, za + 0.025), "fixture", room="stair-b",
             label="ASSUMED steel wall stringer and tread bearing; add to Revit")
        x = (xa + xb) / 2
        if n % 4 == 0:
            mesh("detail-stair-wall-rail-bracket-%02d" % n, "black-metal",
                 box_faces(x - 0.012, wall_y, zb + 0.87, x + 0.012, ya + 0.075, zb + 0.91),
                 "fixture", room="stair-b", label="ASSUMED wall handrail bracket; add to Revit")

    def sloped_member(mid, y0, y1, offset, depth, label, material="black-metal"):
        # A continuous prism follows the tread nosing line; its offset is measured from that line.
        first, last = treads[0], treads[-1]
        x0, x1 = (first[0] + first[3]) / 2, (last[0] + last[3]) / 2
        z0, z1 = first[5] + offset, last[5] + offset
        a = [x0, y0, z0 - depth]; b = [x1, y0, z1 - depth]
        c = [x1, y1, z1]; d = [x0, y1, z0]
        e = [x0, y1, z0 - depth]; f = [x1, y1, z1 - depth]
        g = [x1, y0, z1]; h = [x0, y0, z0]
        mesh(mid, material, [[a, b, f, e], [h, g, c, d], [a, h, d, e], [b, f, c, g],
                                  [a, b, g, h], [e, d, c, f]], "fixture", room="stair-b",
             label=label)

    sloped_member("detail-stair-open-stringer", open_y - 0.055, open_y - 0.025, -0.06, 0.15,
                  "ASSUMED continuous open-side steel stringer; add to Revit")
    sloped_member("detail-stair-wall-plate", wall_y + 0.23, wall_y + 0.26, -0.06, 0.15,
                  "ASSUMED continuous wall stringer plate behind tread bearings; add to Revit")
    glass_spec = next(b for b in sp["balustrades"] if b["id"] == "stair-open-glass")
    rail_spec = next(b for b in sp["balustrades"] if b["id"] == "stair-wall-handrail")
    profile = glass_spec["nosing_profile"]
    # Three-tread laminated panels, with an open top edge. The 12 mm sheet
    # and the steel shoe are ASSUMED pending structural glass sizing.
    for k in range(0, len(profile) - 1, 3):
        a, b = profile[k], profile[min(k + 3, len(profile) - 1)]
        y0, y1 = open_y - 0.05, open_y - 0.038
        lo, hi = -0.07, glass_spec["height_above_nosing"]
        face = lambda yy: [[a[0], yy, a[2] + lo], [b[0], yy, b[2] + lo],
                           [b[0], yy, b[2] + hi], [a[0], yy, a[2] + hi]]
        mesh("detail-stair-glass-%02d" % k, "glass-guard", [face(y0), face(y1)[::-1]],
             "fixture", room="stair-b", label="ASSUMED frameless laminated stair glass panel")
        mesh("detail-stair-glass-edge-%02d" % k, "glass-edge",
             [[[a[0], y0, a[2] + hi], [b[0], y0, b[2] + hi],
               [b[0], y1, b[2] + hi], [a[0], y1, a[2] + hi]]], "fixture", room="stair-b",
             label="ASSUMED visible polished laminated-glass top edge")
    sloped_member("detail-stair-glass-shoe", open_y - 0.065, open_y - 0.025, -0.04, 0.06,
                  "ASSUMED steel base shoe on open stringer")
    # on the bracket ends (wall_y + 0.325): the finished plaster beside the flight is at wall_y + 0.20 (-28.471),
    # and the old offset (+0.06..0.09) buried the rail inside it (round-2 finals, v11)
    sloped_member("detail-stair-wall-handrail", wall_y + 0.285, wall_y + 0.325, 0.922, 0.044,
                  "wall-side wood handrail %.2f m above nosings" % rail_spec["height_above_nosing"], "oak")
    notes.append("Details added for the render: fluted walnut TV wall, oak headboard slats, glass guard at the stair "
                 "opening, cove ceilings.")
    notes.append("ASSUMED stair fixings: steel base shoe on the stringer holds three-tread frameless laminated glass "
                 "panels with visible polished edges; glass thickness 12 mm awaits structural design. The wall-side "
                 "wood handrail uses steel brackets. Risers remain open; coordinate fixings in Revit.")

    # ---- furniture (the checked layout), materials by type and part
    from .. import furniture as FG
    it_all = {i["id"]: i for i in F.layout(lay)}
    GEN = {"bed_double": ("bed_double", 1.05), "bed_small_double": ("bed_double", 0.95),
           "wardrobe": ("wardrobe", None), "bedside_table": ("bedside_table", None)}
    GEN_MAT = {"archpipe oak": "oak", "archpipe warm linen": "linen", "archpipe ivory bedding": "bedding-white",
               "archpipe muted taupe throw": "linen", "archpipe dark metal": "black-metal"}
    generated = set()
    detailed = set()
    from . import villa_furniture_detail as FD
    gen_comps = {}
    for f in F3.spec(lay):
        src = it_all.get(f["mark"])
        if src is not None and src["type"] in GEN and not str(src["room"]).startswith("parents-dressing"):
            kind, hh = GEN[src["type"]]
            comps = generated_components(src, kind, hh)
            z = LZ[f["level"]]
            by = {}
            mattress_top_mm = max((v[2] for c in comps if c["name"].endswith(":mattress")
                                   for v in c["vertices_mm"]), default=0)
            for c in comps:
                part = c["name"].split(":")[1]
                if part in ("duvet", "throw_base", "throw_fold"):
                    continue                                    # the cloth duvet replaces the sculpted one
                triangles = c["triangles"]
                vertices = c["vertices_mm"]
                if part.startswith("pillow"):
                    # A rounded rectangular pillow with a lofted face. The
                    # generator's ellipsoid gave Kids B two flat discs.
                    xx = [v[0] for v in vertices]; yy = [v[1] for v in vertices]
                    xa, xb, ya, yb = min(xx), max(xx), min(yy), max(yy)
                    rings = [(xa + 28, xb - 28, ya + 24, yb - 24, mattress_top_mm, 36),
                             (xa, xb, ya, yb, mattress_top_mm + 32, 55),
                             (xa, xb, ya, yb, mattress_top_mm + 95, 55),
                             (xa + 55, xb - 55, ya + 48, yb - 48, mattress_top_mm + 135, 42)]
                    vertices, triangles = FG._loft_rings(rings, 8)
                vs = [[v[0] / 1000.0, v[1] / 1000.0, z + v[2] / 1000.0] for v in vertices]
                if part.startswith("pillow") and f["mark"] in ("pb-bed", "kb-bed"):
                    # The reference's loose pillows stand against the headboard.
                    # Lean the existing authored cushion within the bed envelope;
                    # the base remains seated on the mattress. Dressing only.
                    axis = 1 if src["rot"] in (0, 180) else 0
                    lo = min(v[axis] for v in vs)
                    hi = max(v[axis] for v in vs)
                    seat_z = min(v[2] for v in vs)
                    head_at_hi = src["rot"] in (180, 90)
                    for v in vs:
                        rise = (v[axis] - lo) / max(hi - lo, 1e-6)
                        v[2] += 0.16 * (rise if head_at_hi else 1 - rise)
                    lift = min(v[2] for v in vs) - seat_z
                    for v in vs:
                        v[2] -= lift
                mat = GEN_MAT.get(c["material"]["name"], "oak")
                if part.startswith("pillow") and f["mark"] in ("pb-bed", "kb-bed"):
                    mat = "sage-fabric"
                if mat == "oak" and part == "frame":
                    mat = "oak-grain-x"
                # Keep pillows separate so their curved edges can be smoothed
                # without subdividing the mattress or the hard bed frame.
                key = (mat, part) if part.startswith("pillow") else (mat, "body")
                by.setdefault(key, []).extend(
                    [[vs[t[0]], vs[t[1]], vs[t[2]]] for t in triangles])
            for k, ((mat, part), faces) in enumerate(by.items()):
                meshes.append(dict(id="furn-%s-%d" % (f["mark"], k), group="furniture", material=mat,
                                   room=f["room"], label=f["mark"] + (" dressing: pillow" if part.startswith("pillow") else ""),
                                   faces=faces, keep_object=True, subdivide=1 if part.startswith("pillow") else 0,
                                   bevel_m=0.003 if part.startswith("pillow") else 0))
            generated.add(f["mark"])
            gen_comps[f["mark"]] = comps
            continue
        z = LZ[f["level"]]
        # detailed render geometry inside the same checked envelope (villa_furniture_detail); boxes only where no
        # builder exists (shelving, screens, the shower tray)
        detail = None
        if "#" in f["mark"]:
            detail = FD.seat_parts(f, z)
        elif src is not None and FD.local_parts(src) is not None:
            detail = FD.world_parts(src, z)
            for name, b in zip(f["parts"], f["boxes"]):
                if name == "screen":
                    detail.setdefault("screen", []).extend(box_faces(b[0], b[1], z + b[2], b[3], b[4], z + b[5]))
        if detail is not None:
            by = {}
            for part, faces in detail.items():
                mat = part_material(f, part)
                if part in ("top", "shelf", "apron") and mat == "walnut":
                    mat = "walnut-grain-x"
                by.setdefault((mat, part if part == "microwave-glass" else "body"), []).extend(faces)
            for k, ((mat, component), faces) in enumerate(by.items()):
                meshes.append(dict(id="furn-%s-%d" % (f["mark"].replace("#", "-"), k), group="furniture",
                                   material=mat, room=f["room"], label=f["mark"].split("#")[0] +
                                   (" ASSUMED island microwave drawer front" if component == "microwave-glass" else ""),
                                   faces=faces,
                                   keep_object=True, subdivide=1 if mat in SOFT else 0,
                                   bevel_m=0.006 if mat in SOFT else 0.0015))
            detailed.add(f["mark"])
            continue
        parts = {}
        for name, b in zip(f["parts"], f["boxes"]):
            mat = part_material(f, name)
            if name in ("top", "shelf", "apron") and mat == "walnut":
                mat = "walnut-grain-x"
            parts.setdefault(mat, []).extend(box_faces(b[0], b[1], z + b[2], b[3], b[4], z + b[5]))
        for k, (mat, faces) in enumerate(parts.items()):
            mesh("furn-%s-%d" % (f["mark"].replace("#", "-"), k), mat, faces, "furniture", room=f["room"],
                 label=f["mark"].split("#")[0])
    # rugs (design: soft floor where people sit)
    for rid, anchor, (w, d) in (("lounge", "lounge-coffee", (3.1, 2.0)), ("living", "living-coffee", (2.6, 2.4)),
                                ("parents-bed", "pb-bed", (2.2, 2.6)), ("kids-a", "ka-bunk", (1.4, 2.0))):
        q = F.footprint(it[anchor])
        cx, cy = (q[0] + q[2]) / 2, (q[1] + q[3]) / 2
        z = LZ[lay["rooms"][rid]["level"]] + 0.012
        mesh("rug-" + rid, "rug", box_faces(cx - w / 2, cy - d / 2, z - 0.01, cx + w / 2, cy + d / 2, z), "furniture",
             room=rid, label="rug-" + rid)
    notes.append("Rugs in the lounge, garden living, parents' bedroom and kids room A (ASSUMED).")

    cloth = []
    # ---- dressing: clothes on the dressing rails, duvets and pillows on the beds (NOT design)
    import random
    rnd = random.Random(7)
    fabrics = ["linen", "boucle", "sage-fabric", "taupe-fabric", "bedding-white", "leather-brown"]
    for wid in ("pd-hang-1", "pd-hang-2"):
        q = F.footprint(it[wid])
        top = LZ["GF"] + it[wid]["h"] - 0.31
        cy = (q[1] + q[3]) / 2
        x = q[0] + 0.06
        k = 0
        while x < q[2] - 0.06:
            L = rnd.choice((0.75, 0.9, 1.05, 1.2))
            mesh("dress-clothes-%s-%d" % (wid, k), rnd.choice(fabrics),
                 box_faces(x, cy - 0.24, top - L, x + 0.035, cy + 0.24, top), "dressing", room=it[wid]["room"],
                 label="dressing: clothes")
            x += rnd.choice((0.05, 0.065, 0.08))
            k += 1
    for bid, duvet in (("pb-bed", "bedding-white"), ("kb-bed", "sage-fabric"), ("ka-bunk", "bedding-white")):
        b_ = it[bid]
        q = F.footprint(b_)
        z = LZ["GF"] + (0.40 if b_["h"] >= 1.5 else b_["h"])
        if b_["rot"] in (0, 180):
            head = q[1] if b_["rot"] == 0 else q[3]
            s_ = 1 if b_["rot"] == 0 else -1
            ya, yb_ = sorted((head + s_ * 0.55, (q[3] + 0.02) if s_ > 0 else (q[1] - 0.02)))
            dv = box_faces(q[0] - 0.03, ya, z, q[2] + 0.03, yb_, z + 0.07)
            n = 2 if q[2] - q[0] > 1.1 else 1
            wpil = (q[2] - q[0] - 0.1) / n
            pil = []
            for k in range(n):
                xa = q[0] + 0.05 + k * wpil
                ya2, yb2 = sorted((head + s_ * 0.08, head + s_ * 0.48))
                pil.append(box_faces(xa + 0.02, ya2, z, xa + wpil - 0.02, yb2, z + 0.14))
        else:
            head = q[0] if b_["rot"] == -90 else q[2]
            s_ = 1 if b_["rot"] == -90 else -1
            xa, xb = sorted((head + s_ * 0.55, (q[2] + 0.02) if s_ > 0 else (q[0] - 0.02)))
            dv = box_faces(xa, q[1] - 0.03, z, xb, q[3] + 0.03, z + 0.07)
            xa2, xb2 = sorted((head + s_ * 0.08, head + s_ * 0.48))
            pil = [box_faces(xa2, q[1] + 0.07, z, xb2, q[3] - 0.07, z + 0.14)]
        # the duvet is CLOTH, draped by the renderer onto the bed's own parts (render review: box duvets read as
        # rigid slabs). Its cut follows the bedroom standard (photoreal.cloth_bedding): from 0.55 m below the head
        # to 0.30 m OVER THE FOOT, mattress width + 0.30 m each side, so both the sides and the foot hang. The first
        # villa cut stopped 20 mm past the foot and the stiff lip stood out flat ("duvet flying on the end",
        # client 2026-09-27). A bunk's duvet stays 50 mm inside its frame on every side (the rail and posts).
        bunk = b_["h"] >= 1.5
        # 0.26 m drop (the bedroom's 0.30 was on a higher mattress): on these 0.48-0.53 m mattresses a 0.30 m drop on
        # two sides draped the foot corners to 30-50 mm off the floor (render_qa cloth_plausible, draft 12)
        over, foot_over = (-0.05, -0.05) if bunk else (0.26, 0.26)
        axis = "y" if b_["rot"] in (0, 180) else "x"
        if axis == "y":
            head = q[1] if b_["rot"] == 0 else q[3]
            foot = q[3] if b_["rot"] == 0 else q[1]
            a0, a1 = q[0], q[2]
        else:
            head = q[0] if b_["rot"] == -90 else q[2]
            foot = q[2] if b_["rot"] == -90 else q[0]
            a0, a1 = q[1], q[3]
        s_ = 1 if foot > head else -1
        start = head + s_ * 0.55
        mspan = sorted((head, foot))
        if bid in gen_comps:
            # the generated bed's own mattress top and pillow edge (it is built taller than the plan's h): the sheet
            # starts 20 mm beyond the pillows, 60 mm over the real mattress, never inside the pillows
            byname = {c["name"].split(":")[1]: c["vertices_mm"] for c in gen_comps[bid]}
            z = LZ["GF"] + max(v[2] for v in byname["mattress"]) / 1000.0
            k_ = 1 if axis == "y" else 0
            pil_edge = [v[k_] / 1000.0 for n_, vs in byname.items() if n_.startswith("pillow") for v in vs]
            start = (max(pil_edge) if s_ > 0 else min(pil_edge)) + s_ * 0.02
            # coverage is judged on the MATTRESS, not the footprint with its headboard zone (the check read 63 % of
            # the footprint where the duvet covered ~72 % of the mattress)
            mv = [v[k_] / 1000.0 for v in byname["mattress"]]
            mspan = [min(mv), max(mv)]
        end = foot + s_ * foot_over
        length, width = abs(end - start), (a1 - a0) + 2 * over
        mid_l, mid_w = (start + end) / 2, (a0 + a1) / 2
        center = [mid_w, mid_l] if axis == "y" else [mid_l, mid_w]
        size = [width, length] if axis == "y" else [length, width]
        pin = [axis, start, 0.03]
        cut = dict(foot_overhang_m=foot_over, side_overhang_m=over, head_to_pin_m=0.55)
        cloth.append(dict(id="duvet-" + bid, material=duvet, colliders=["furn-" + bid + "-", "furn-" + bid + "side-", "dress-pillow-" + bid],
                          center=center, size=size, z_start=round(z + 0.08, 3), pin=pin, frames=60, mass=0.4,
                          bending=0.6, loft=0.018, thickness=0.05, cut=cut, bunk=bunk, mattress_top=round(z, 3),
                          mattress_span=mspan, length_axis=axis,
                          label="dressing: duvet (cloth)"))
        if bid == "pb-bed":
            # The bedroom reference has a loose runner at the foot. It is
            # dressing, draped onto this bed's actual cloth duvet.
            throw_center = list(center)
            throw_center[1 if axis == "y" else 0] = foot - s_ * 0.38
            throw_size = [(a1 - a0) + 0.5, 0.55] if axis == "y" else [0.55, (a1 - a0) + 0.5]
            cloth.append(dict(id="throw-" + bid, material="throw-taupe", colliders=["cloth-duvet-" + bid],
                              center=throw_center, size=throw_size, z_start=round(z + 0.22, 3),
                              frames=40, mass=0.8, bending=4.0, thickness=0.012,
                              label="dressing: woven bed throw (cloth)"))
        if bunk:                                           # the upper bunk has its own duvet
            cloth.append(dict(id="duvet-" + bid + "-upper", material=duvet, colliders=["furn-" + bid + "-"],
                              center=center, size=size, z_start=round(LZ["GF"] + 1.40 + 0.08, 3), pin=pin,
                              frames=60, mass=0.4, bending=0.6, loft=0.018, thickness=0.05, cut=cut, bunk=True,
                              mattress_span=sorted((head, foot)), length_axis=axis,
                              mattress_top=round(LZ["GF"] + 1.40, 3), label="dressing: duvet (cloth)"))
        for k, pf in enumerate(pil if bid not in generated else []):
            mesh("dress-pillow-%s-%d" % (bid, k), "bedding-white", pf, "dressing", room=b_["room"],
                 label="dressing: pillow")
    notes.append("Dressing: clothes on the dressing rails, duvets and pillows on the beds (not design).")
    notes.append("ASSUMED furniture detailing: crowned sofa and chair cushions, rounded arms, exposed plinth and "
                 "legs, and the bunk ladder on its open side; product and fixing details require Revit coordination. "
                 "Rectangular lofted bed pillows are dressing, not specified products.")
    notes.append("ASSUMED joinery details: slim walnut frames and clear architectural glass on the library cabinets, "
                 "open timber shelves, upholstered daybed mattress and loose cushions, two ergonomic cinema task "
                 "chairs, microwave drawer in the island, and cleaning-storage doors below the folding counter. "
                 "Book props are labelled dressing; all builder vertices are checked against their authored envelopes.")
    notes.append("By day the basement rooms are shown with their ambient and accent lights at 50 % (a basement is "
                 "used with lights on by day); bathrooms by day have their lights on; other ground-floor day "
                 "views are daylight only.")

    # ASSUMED appliance stand-ins: all sit on checked worktops or within the scheduled tall column.
    def appliance(mid, support, lx, ly, z0, sx, sy, h, mat="black-metal"):
        item = it_all[support]
        wx, wy, _ = FD.to_world_point(item, lx, ly, 0, LZ[item["level"]])
        mesh(mid, mat, box_faces(wx - sx / 2, wy - sy / 2, LZ[item["level"]] + z0,
                                 wx + sx / 2, wy + sy / 2, LZ[item["level"]] + z0 + h),
             "fixture", room=item["room"], label="ASSUMED appliance: " + mid + "; add to Revit")

    def coffee_machine(mid, support, lx, ly):
        item = it_all[support]
        x, y, _ = FD.to_world_point(item, lx, ly, 0, LZ[item["level"]])
        floor = LZ[item["level"]] + 0.90
        shell_vertices, shell_tris = FG._loft_rings([
            (x-.075, x+.075, y-.09, y+.08, floor+.012, .022),
            (x-.085, x+.085, y-.09, y+.08, floor+.055, .026),
            (x-.085, x+.085, y-.09, y+.08, floor+.215, .026),
            (x-.060, x+.060, y-.077, y+.062, floor+.265, .025)], 8)
        mesh(mid + "-body", "black-metal",
             [[shell_vertices[i] for i in tri] for tri in shell_tris], "fixture", room=item["room"],
             label="ASSUMED rounded coffee machine housing; add to Revit", keep_object=True,
             bevel_m=0.003, subdivide=1)
        for suffix, material, bounds in (
            ("drip-tray", "black-metal", (x-.078, y+.075, floor, x+.078, y+.11, floor+.018)),
            ("spout", "brass", (x-.018, y+.072, floor+.115, x+.018, y+.108, floor+.145)),
            ("water-tank", "glass-guard", (x-.063, y-.108, floor+.055, x+.063, y-.088, floor+.235)),
        ):
            mesh(mid + "-" + suffix, material, box_faces(*bounds), "fixture", room=item["room"],
                 label="ASSUMED coffee machine " + suffix + "; add to Revit", bevel_m=0.005)

    coffee_machine("appliance-coffee-main", "k-run", 0.775, -0.14)
    coffee_machine("appliance-coffee-dirty", "dk-run", -0.90, 0)
    island = it_all["k-island"]
    hob = next((a, b) for kind, a, b in F3._local_modules(island) if kind == "hob")
    hx, hy, _ = FD.to_world_point(island, sum(hob) / 2, 0, 0, LZ["B"])
    # a DOWNDRAFT extractor behind the hob: a ceiling hood over the island shaded its task downlights (the in-scene
    # measurement read 117 lx of 500 on the prep side) and blocked the view across the kitchen
    ztop_i = LZ["B"] + island["h"]
    ax_ = 0 if island["rot"] in (0, 180) else 1
    back = -1 if island["rot"] in (0, 90) else 1
    if ax_ == 0:
        vent = box_faces(hx - 0.45, hy + back * 0.30 - 0.04, ztop_i, hx + 0.45, hy + back * 0.30 + 0.04, ztop_i + 0.012)
    else:
        vent = box_faces(hx + back * 0.30 - 0.04, hy - 0.45, ztop_i, hx + back * 0.30 + 0.04, hy + 0.45, ztop_i + 0.012)
    mesh("appliance-downdraft-island", "black-metal", vent, "fixture", room="kitchen",
         label="ASSUMED downdraft extractor behind the island hob; add to Revit")
    dirty = it_all["dk-run"]
    hob = next((a, b) for kind, a, b in F3._local_modules(dirty) if kind == "hob")
    hx, hy, _ = FD.to_world_point(dirty, sum(hob) / 2, 0, 0, LZ["B"])
    wall_y = F.clear_rect(lay, "dirty-kitchen")[3]   # finished wall face, not the room rect (the wall centre)
    # The duct terminates at the rendered soffit, which is lower under the
    # ramp than a room's nominal ceiling height.
    from . import render_support as SUP
    tris, owners = SUP._triangles([m for m in meshes if m["group"] in ("shell", "context")])
    soffit = SUP._Surfaces(tris, owners)
    hits = []
    for t in soffit.t[soffit.down & (soffit.lo[:, 0] <= hx) & (hx <= soffit.hi[:, 0]) &
                      (soffit.lo[:, 1] <= wall_y - 0.08) & (wall_y - 0.08 <= soffit.hi[:, 1])]:
        (ax, ay, az), (bx, by_, bz), (cx, cy, cz) = t
        px, py = hx, wall_y - 0.08
        den = (by_ - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        u = ((by_ - cy) * (px - cx) + (cx - bx) * (py - cy)) / den
        v = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / den
        if min(u, v, 1-u-v) >= -1e-6:
            zz = u*az + v*bz + (1-u-v)*cz
            if zz > -0.98:
                hits.append(zz)
    if not hits:
        raise ValueError("Dirty-kitchen hood has no rendered soffit above it")
    hood_top = min(hits)
    mesh("appliance-hood-dirty-canopy", "black-metal", box_faces(hx - 0.34, hy - 0.27, -1.05,
         hx + 0.34, wall_y, -0.98), "fixture", room="dirty-kitchen",
         label="ASSUMED wall cooker hood canopy; add to Revit")
    mesh("appliance-hood-dirty-chimney", "black-metal", box_faces(hx - 0.115, wall_y - 0.16, -0.98,
         hx + 0.115, wall_y, hood_top), "fixture", room="dirty-kitchen",
         label="ASSUMED cooker hood duct to rendered soffit; add to Revit")
    for basin_id in ("gwc-basin", "fb-basin", "pe-basin"):
        basin = it_all[basin_id]
        width = min(basin["w"] - 0.04, 0.78)
        back = -basin["d"] / 2
        bounds = F3.to_world(basin, (-width/2, back, basin["h"] + 0.20,
                                      width/2, back + 0.012, basin["h"] + 0.95))
        mesh("mirror-" + basin_id, "silvered-mirror",
             box_faces(bounds[0], bounds[1], LZ[basin["level"]] + bounds[2],
                       bounds[3], bounds[4], LZ[basin["level"]] + bounds[5]),
             "fixture", room=basin["room"], label="ASSUMED silvered wall mirror over " + basin_id + "; add to Revit")
    notes.append("ASSUMED deck-mounted brass bath mixer and spout, three silvered vanity mirrors, coffee machine "
                 "bodies with trays, spouts and water tanks, and dirty-kitchen canopy and duct; coordinate with Revit.")
    notes.append("ASSUMED kitchen products: two worktop coffee machines, island microwave drawer and "
                 "dirty-kitchen integrated fridge and oven (cleaning "
                 "storage moves below the folding counter), island downdraft extractor and dirty-kitchen wall hood. "
                 "Both run sinks and taps are procedural geometry. Product choices and services go into Revit.")

    # The shell cutter in villa_daylight has already removed the hatch from
    # BOTH faces of the shared wall. These are its visible jambs and shutter.
    for h in sp["hatches"]:
        z0, z1 = LZ[h["level"]] + h["sill"], LZ[h["level"]] + h["head"]
        xa, xb, yy = h["x0"], h["x1"], h["y"]
        for part, bounds in (("sill", (xa, yy - 0.05, z0 - 0.018, xb, yy + 0.05, z0)),
                             ("head", (xa, yy - 0.05, z1, xb, yy + 0.05, z1 + 0.018)),
                             ("left", (xa - 0.018, yy - 0.05, z0, xa, yy + 0.05, z1)),
                             ("right", (xb, yy - 0.05, z0, xb + 0.018, yy + 0.05, z1))):
            mesh("detail-hatch-" + part, "garden-sandstone", box_faces(*bounds), "shell",
                 label="ASSUMED stone pass-through " + part + " reveal")
        b = h["shutter_box"]
        mesh("detail-hatch-shutter-box", "greige-lacquer",
             box_faces(b[0], b[1], LZ[h["level"]] + b[2], b[3], b[4], LZ[h["level"]] + b[5]),
             "fixture", room="kitchen", label="ASSUMED roll-up shutter housing, raised open by day")
    for p in sp["pocket_buildouts"]:
        d = next(d for d in sp["doors"] if d.get("sliding") and d["level"] == p["level"])
        for k in range(d["leaf_count"]):
            x0, x1 = d["pocket_span"]
            y = d["y"] + (k - 1) * 0.026
            mesh("detail-pocket-panel-%d" % k, "door-oak",
                 box_faces(x0 + 0.01, y - 0.009, LZ[d["level"]] + 0.015,
                           x1 - 0.01, y + 0.009, LZ[d["level"]] + d["height"] - 0.015),
                 "fixture", room="dirty-kitchen", label="ASSUMED telescopic sliding leaf stowed in pocket")
        mesh("detail-pocket-track", "black-metal", box_faces(x0, d["y"] - 0.055,
             LZ[d["level"]] + d["height"], d["x"] + d["width"] / 2, d["y"] + 0.055,
             LZ[d["level"]] + d["height"] + 0.024), "fixture", room="dirty-kitchen",
             label="ASSUMED overhead telescopic pocket track")
    notes.append("ASSUMED hatch reveals and roll-up shutter housing: shutter raised for all current day views; "
                 "three 0.4 m sliding panels are stowed inside the 0.4 m west pocket, with an overhead track.")

    for fitting in sp["bath_fittings"]:
        fid = "detail-" + fitting["id"]
        if fitting["kind"] == "ceiling-rain-head":
            x, y, z = fitting["x"], fitting["y"], LZ[fitting["level"]] + fitting["z"]
            mesh(fid + "-drop", "brass", box_faces(x - 0.012, y - 0.012, z + 0.012,
                 x + 0.012, y + 0.012, VL.ceiling_z("GF", x=x, y=y, room=fitting["room"], lay=lay, spec=sp)),
                 "fixture", room=fitting["room"], label="ASSUMED ceiling rain-head drop")
            mesh(fid + "-plate", "brass", box_faces(x - 0.16, y - 0.16, z - 0.014,
                 x + 0.16, y + 0.16, z + 0.014), "fixture", room=fitting["room"],
                 label="ASSUMED ceiling rain-head plate")
        elif fitting["kind"] == "hand-shower":
            x, y, z = fitting["x"], fitting["y"], fitting["z"]
            mesh(fid + "-rail", "brass", box_faces(x - 0.012, y - 0.06, z - 0.35,
                 x + 0.012, y + 0.012, z + 0.45), "fixture", room=fitting["room"],
                 label="ASSUMED wall-mounted hand-shower rail")
            mesh(fid + "-head", "brass", box_faces(x - 0.045, y + 0.005, z + 0.21,
                 x + 0.045, y + 0.09, z + 0.31), "fixture", room=fitting["room"],
                 label="ASSUMED hand shower on sliding holder")
        else:
            mesh(fid, "glass-guard", [[[fitting["x0"], fitting["y"], fitting["sill"]],
                 [fitting["x1"], fitting["y"], fitting["sill"]],
                 [fitting["x1"], fitting["y"], fitting["head"]],
                 [fitting["x0"], fitting["y"], fitting["head"]]]], "fixture", room=fitting["room"],
                 label="ASSUMED fixed frameless bath screen, open entry at far end")
    for vent in sp["ventilation"]:
        x, y, z = vent["fan"]
        z += LZ[vent["level"]]
        end_y = vent["duct_route"][-1][1]
        mesh("detail-vent-" + vent["room"] + "-duct", "black-metal",
             box_faces(x - 0.055, min(y, end_y), z - 0.055,
                       x + 0.055, max(y, end_y), z + 0.055), "fixture", room=vent["room"],
             label="ASSUMED duct to outside: " + vent["room"])
        mesh("detail-vent-" + vent["room"] + "-grille", "alu-bronze",
             box_faces(x - 0.12, end_y - 0.012, z - 0.12,
                       x + 0.12, end_y + 0.012, z + 0.12), "fixture", room=vent["room"],
             label="ASSUMED external extract grille: " + vent["room"])
    notes.append("ASSUMED bath-fitting bodies and fixing details follow the specified rain head, hand shower rail "
                 "and fixed frameless screen. Guest WC and dirty-kitchen ducts terminate at external grilles; "
                 "the dirty-kitchen cooker hood is the specified extract source. Drip, flow and products remain "
                 "service selections, not render claims.")

    # ---- construction details (labelled): skirting on internal wall faces (cut at doors), frames on glazing,
    # architraves and handles on internal doors
    from . import revit_spec as RS2
    for lv in ("B", "GF"):
        zf = LZ[lv] + 0.002
        faces = []
        for (x0, y0, x1, y1) in F._walls(sp, lv):
            horiz = (x1 - x0) >= (y1 - y0)
            for side in (-1, 1):
                if horiz:
                    yy = y0 if side < 0 else y1
                    probe = _room_at(lay, (x0 + x1) / 2, yy + side * 0.1, zf + 0.5)
                    if probe in FINISH and FINISH[probe][1] == "plaster-warm-white":
                        a_, b_ = (yy - 0.012, yy) if side < 0 else (yy, yy + 0.012)
                        faces += box_faces(x0, a_, zf, x1, b_, zf + 0.08)
                else:
                    xx = x0 if side < 0 else x1
                    probe = _room_at(lay, xx + side * 0.1, (y0 + y1) / 2, zf + 0.5)
                    if probe in FINISH and FINISH[probe][1] == "plaster-warm-white":
                        a_, b_ = (xx - 0.012, xx) if side < 0 else (xx, xx + 0.012)
                        faces += box_faces(a_, y0, zf, b_, y1, zf + 0.08)
        mesh("detail-skirting-" + lv, "paint-white-satin", faces, "shell", label="detail: 80 mm painted skirting")
    frames = []
    for m in [m for m in meshes if m["material"] == "glass-clear"]:
        for face in m["faces"]:
            xs_ = [q[0] for q in face]
            ys_ = [q[1] for q in face]
            zs_ = [q[2] for q in face]
            fw = 0.05
            if max(xs_) - min(xs_) < 1e-3:                    # a pane in a y-z plane
                x_ = xs_[0]
                ya, yb, za, zb = min(ys_), max(ys_), min(zs_), max(zs_)
                for bx in ((ya, ya + fw, za, zb), (yb - fw, yb, za, zb), (ya, yb, za, za + fw), (ya, yb, zb - fw, zb)):
                    frames += box_faces(x_ - 0.03, bx[0], bx[2], x_ + 0.03, bx[1], bx[3])
                if yb - ya > 1.6:                                 # sliding panels meet at a mullion
                    mid = (ya + yb) / 2
                    frames += box_faces(x_ - 0.03, mid - fw / 2, za, x_ + 0.03, mid + fw / 2, zb)
            elif max(ys_) - min(ys_) < 1e-3:
                y_ = ys_[0]
                xa, xb, za, zb = min(xs_), max(xs_), min(zs_), max(zs_)
                for bx in ((xa, xa + fw, za, zb), (xb - fw, xb, za, zb), (xa, xb, za, za + fw), (xa, xb, zb - fw, zb)):
                    frames += box_faces(bx[0], y_ - 0.03, bx[2], bx[1], y_ + 0.03, bx[3])
                if xb - xa > 1.6:
                    mid = (xa + xb) / 2
                    frames += box_faces(mid - fw / 2, y_ - 0.03, za, mid + fw / 2, y_ + 0.03, zb)
    mesh("detail-window-frames", "alu-bronze", frames, "shell", label="detail: 50 mm aluminium frames (ASSUMED)")
    arch, handles = [], []
    for d in sp["doors"]:
        if d.get("garden") or d.get("sliding"):
            continue
        z0 = LZ[d["level"]] + 0.002
        h_ = d.get("height", 2.1)
        w_ = d["width"]
        axis = F._door_axis(d)
        for s_ in (-1, 1):
            if axis == "h":
                yy = d["y"] + s_ * 0.06
                for bx in ((d["x"] - w_ / 2 - 0.07, d["x"] - w_ / 2), (d["x"] + w_ / 2, d["x"] + w_ / 2 + 0.07)):
                    arch += box_faces(bx[0], min(yy, yy + s_ * 0.015), z0, bx[1], max(yy, yy + s_ * 0.015), z0 + h_ + 0.07)
                arch += box_faces(d["x"] - w_ / 2 - 0.07, min(yy, yy + s_ * 0.015), z0 + h_, d["x"] + w_ / 2 + 0.07,
                                  max(yy, yy + s_ * 0.015), z0 + h_ + 0.07)
                hx = d["x"] + w_ / 2 - 0.08
                handles += box_faces(hx - 0.07, min(d["y"], d["y"] + s_ * 0.07), z0 + 1.02, hx + 0.03,
                                     max(d["y"], d["y"] + s_ * 0.07), z0 + 1.04)
            else:
                xx = d["x"] + s_ * 0.06
                for by_ in ((d["y"] - w_ / 2 - 0.07, d["y"] - w_ / 2), (d["y"] + w_ / 2, d["y"] + w_ / 2 + 0.07)):
                    arch += box_faces(min(xx, xx + s_ * 0.015), by_[0], z0, max(xx, xx + s_ * 0.015), by_[1], z0 + h_ + 0.07)
                arch += box_faces(min(xx, xx + s_ * 0.015), d["y"] - w_ / 2 - 0.07, z0 + h_, max(xx, xx + s_ * 0.015),
                                  d["y"] + w_ / 2 + 0.07, z0 + h_ + 0.07)
                hy = d["y"] + w_ / 2 - 0.08
                handles += box_faces(min(d["x"], d["x"] + s_ * 0.07), hy - 0.07, z0 + 1.02, max(d["x"], d["x"] + s_ * 0.07),
                                     hy + 0.03, z0 + 1.04)
    mesh("detail-architraves", "paint-white-satin", arch, "shell", label="detail: 70 mm architraves")
    mesh("detail-door-handles", "brass", handles, "fixture", label="detail: lever handles")
    notes.append("Construction details added for the render: 80 mm skirting, 50 mm aluminium window frames and "
                 "mullions, 70 mm architraves and lever handles (not yet in the Revit model).")

    # ---- curtains (client 2026-09-28): sheer + a heavy layer on a ceiling track, whole villa. RULE: every window
    # and glazed garden door in a room whose occupancy is "bedroom", "living", "dining" or "study" gets curtains;
    # kitchens/dirty kitchen (occupancy "kitchen"/"utility"), bathrooms/WC (occupancy "wc"/"bathroom"/"ensuite") and
    # the stair void (no glazing) get none -- the client's "bedrooms + living spaces". Bedrooms get a blackout heavy
    # layer, living/dining/study a dim-out one (curtain-heavy / curtain-heavy-dimout, above). Geometry is built and
    # cloth-simulated in villa_scene.build_curtains (photoreal._grid/_simulate, the tested bedroom curtain ported
    # and made axis-general); this list is the authored contract it consumes and, like the cloth duvets, is NOT a
    # static mesh -- the float/passage guards never see it, so a dedicated test below checks the open state
    # directly against render_support.blocked_openings.
    curtains = []
    curtain_openings = ([dict(w, kind="window") for w in sp["windows"]] +
                        [dict(d, kind="garden-door") for d in sp["doors"] if d.get("garden")])
    curtain_counts = {}
    for o in curtain_openings:
        room = o["room"] if o["kind"] == "window" else next(r for r in o["rooms"] if r != "yard")
        occ = lay["rooms"][room]["occupancy"]
        if occ not in CURTAIN_OCC:
            continue
        axis = (o.get("span") or [None])[0]
        if axis not in ("h", "v"):
            continue
        rx0, ry0, rx1, ry1 = F.clear_rect(lay, room)
        rcx, rcy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
        sign = 1 if (rcy > o["y"] if axis == "h" else rcx > o["x"]) else -1
        # Lead review (draft render 1): the old track/panels were offset a few cm from the WINDOW LINE (o["x"]/
        # o["y"]), which sits inside the wall's own thickness -- still behind detail-window-frames (alu-bronze,
        # +-30 mm of that same line) and inside the reveal, so the closed curtain read as hanging inside the
        # window, split by the mullion. A ceiling-track curtain hangs on the ROOM side of the WALL, not the
        # glazing: `wall_face` is clear_rect's boundary on this side (the room's own clear-floor edge, already
        # inset past the wall's full thickness -- 0.20 m envelope / 0.05 m partition, F.clear_rect's own numbers,
        # not re-derived here), and villa_scene.build_curtains hangs the sheer 0.10 m and the heavy 0.15 m beyond
        # THAT face into the room.
        wall_face = (ry1 if sign < 0 else ry0) if axis == "h" else (rx1 if sign < 0 else rx0)
        level, width = o["level"], o["width"]
        floor_z = LZ[level]
        track_z = VL.ceiling_z(level, x=o["x"], room=room, y=o["y"], lay=lay, spec=sp)
        curtain_counts[room] = curtain_counts.get(room, 0) + 1
        cid = "curtain-%s-%02d" % (room, curtain_counts[room])
        bedroom = occ == "bedroom"
        # Lead review (draft render 2): a 0.14 m flat cap was a curtain that could not physically exist -- a pair
        # of panels for a 2.4-2.76 m door carries roughly double fullness (~5 m of fabric) and cannot gather into
        # 0.14 m. STACK_RATIO (0.18 x opening width, per side, sheer and heavy stacking together) is the ASSUMED
        # typical stacking allowance for pleated drapery -- not a cited standard, there isn't one for this. The
        # stack sits beyond the opening as far as the wall PIER allows (`pier_reach`, capped by revit_spec.REVEAL
        # so it never runs past the kept wall into the next opening or a corner); whatever more the ratio calls
        # for hangs in front of the glazing/frame instead (a real short-pier install: the stack partly overlaps
        # the glass edge). For a DOOR (garden/glazed; a window is never walked through, so it carries no passage
        # rule) that overlap is capped so the two stacks together still leave F.BODY (0.914 m, "card
        # mitton-path-of-travel-min: paths of travel at least 36 in") clear through the opening -- centred, since
        # none of this villa's garden-door spec entries mark an operable side.
        STACK_RATIO = 0.18
        pier_reach = round(min(0.18, RS.REVEAL - 0.02), 3)
        desired_stack = round(STACK_RATIO * width, 3)
        opening_kind = o["kind"]
        clear_width = None
        if opening_kind == "garden-door":
            max_overlap_each = max(0.0, (width - F.BODY) / 2)
            overlap = min(max(0.0, desired_stack - pier_reach), max_overlap_each)
            clear_width = round(width - 2 * overlap, 3)
        else:
            overlap = max(0.0, desired_stack - pier_reach)
        stack = round(pier_reach + overlap, 3)
        curtains.append(dict(
            id=cid, room=room, level=level, axis=axis, center=[o["x"], o["y"]], width=round(width, 3),
            floor_z=floor_z, track_z=round(track_z, 3), normal_sign=sign, wall_face=round(wall_face, 3),
            bedroom=bedroom, opening_kind=opening_kind,
            sheer_material="curtain-sheer", heavy_material="curtain-heavy" if bedroom else "curtain-heavy-dimout",
            open_stack_m=stack, open_pier_reach_m=pier_reach, closed_overlap_m=0.05,
            **({"open_clear_width_m": clear_width} if clear_width is not None else {}),
            # Floor-length regardless of sill height: a punched bedroom window's curtain still runs track-to-floor
            # (the norm in bedrooms/living rooms, not a curtain cut to the glass), so track_z/floor_z alone (not
            # the window's own sill/head) drive villa_scene.build_curtains' panel height.
            label="ASSUMED curtains: sheer + %s, ceiling track, floor-length" % ("blackout" if bedroom else "dim-out")))
        # The track: a slim ceiling-fixed rail spanning width + pier_reach m each side, centred 0.125 m beyond the
        # wall's inner face (mid-way through the sheer/heavy hanging band villa_scene uses) -- clear of the frame
        # and reveal, not offset from the glazing line. It already runs the full opening width, so no change is
        # needed for a stack that overlaps the glazing (that is fabric on the SAME rail, gathered further in).
        half = width / 2 + pier_reach
        z0, z1 = track_z - 0.03, track_z
        track_at = wall_face + sign * 0.125
        d0, d1 = sorted((track_at - 0.02, track_at + 0.02))
        if axis == "h":
            box = (o["x"] - half, d0, z0, o["x"] + half, d1, z1)
        else:
            box = (d0, o["y"] - half, z0, d1, o["y"] + half, z1)
        mesh("detail-" + cid + "-track", "black-metal", box_faces(*box), "fixture", room=room,
             label="detail: curtain ceiling track (ASSUMED)")
    nook = F.footprint(it_all["library-daybed"])
    ncx, nfront = (nook[0] + nook[2]) / 2, nook[3]
    curtains.append(dict(id="curtain-library-nook", room="bar-alcove", level="B", axis="h",
                         center=[ncx, nfront], width=round(nook[2] - nook[0] - 0.05, 3),
                         floor_z=LZ["B"] + 0.45, track_z=LZ["B"] + it_all["library-daybed"]["nook_top"] - 0.03,
                         normal_sign=1, wall_face=nfront - 0.10, bedroom=False, opening_kind="window",
                         sheer_material="curtain-sheer", heavy_material="curtain-heavy-dimout",
                         open_stack_m=round(0.18 * (nook[2] - nook[0] - 0.05), 3),
                         open_pier_reach_m=0.025, closed_overlap_m=0.05,
                         label="ASSUMED privacy curtain at daybed nook opening, open by day"))
    mesh("detail-curtain-library-nook-track", "black-metal",
         box_faces(nook[0] + 0.025, nfront - 0.012, LZ["B"] + 2.055,
                   nook[2] - 0.025, nfront + 0.012, LZ["B"] + 2.10), "fixture", room="bar-alcove",
         label="ASSUMED privacy-curtain track fixed to nook top")
    notes.append("ASSUMED daybed privacy curtain: sheer linen and dim-out on a track fixed to the nook top, "
                 "stacked open by day and heavy layer closed at night; fabric hangs to the mattress top.")
    notes.append("Curtains (client 2026-09-28): sheer linen (rough_linen, transmittance 0.55) + a heavy layer on a "
                 "ceiling track, every bedroom and living-space window and glazed garden door -- blackout "
                 "(transmittance 0.02) in bedrooms, dim-out (0.10) in living/dining/study. Kitchens, the dirty "
                 "kitchen, bathrooms/WC and the stair void have none. By day each side stacks to 0.18 x the "
                 "opening's width (ASSUMED typical stacking allowance for pleated drapery, not a cited standard): "
                 "as far beyond the opening as the wall pier allows, the rest overlapping the glazing edge, as a "
                 "short-pier install does -- for a garden/glazed door this is capped so the two stacks still leave "
                 "0.914 m clear to walk through (F.BODY, card mitton-path-of-travel-min); a window carries no such "
                 "cap. The heavy layer closes across the opening at night; the sheer layer stays open in both "
                 "states (its job is daytime diffusion, and the closed heavy layer already gives the night "
                 "blackout/dim-out). ASSUMED: track and stacking dimensions, not a specified product.")
    for v in views:
        if v["state"] == "exterior-dusk":
            continue
        suffixes = ("-heavy-closed",) if v["state"] == "day" else ("-heavy-open-l", "-heavy-open-r")
        hidden = [c["id"] + s for c in curtains for s in suffixes]
        if hidden:
            v.setdefault("hide_meshes", []).extend(hidden)

    from . import villa_landscape as LAND
    land_meshes, land_props, land_notes, _ = LAND.build(sp, lay)
    meshes.extend(land_meshes)
    notes.extend(land_notes)

    # ---- lights and fixture bodies
    VL.bind_products()
    lights = []
    ies_dir = OUT / "ies"
    for k in VL.KINDS:
        if k not in VL.PRODUCTS and VL.KINDS[k]["mount"] in ("recessed", "task-lamp"):
            p = ies_dir / "generic" / (k + ".ies")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(VL.generic_ies(VL.KINDS[k]["lm"], VL.KINDS[k]["beam"], k), encoding="utf-8")
    walls_by_level = {lv: F._walls(RS.build(lay), lv) for lv in ("B", "GF")}
    for f in VL.design(lay):
        k = VL.KINDS[f.kind]
        prod = VL.PRODUCTS.get(f.kind)
        cct = int(prod["cct"]) if prod else k["cct"]
        pinfo = ({"manufacturer": prod["manufacturer"], "code": prod["code"], "generic": False,
                  "substitute": prod["substitute"]} if prod else {"manufacturer": "generic", "code": f.kind,
                                                                  "generic": True})
        if k["mount"] == "recessed":
            ies = ("iguzzini/%s.ies" % prod["code"]) if prod else ("generic/%s.ies" % f.kind)
            lights.append(dict(id=f.id, room=f.room, layer=f.layer, type="ies", position=[f.x, f.y, f.z - 0.03],
                               aim=_unit(f.aim), spin_deg=0.0, ies=ies, lumens=round(f.lumens, 1), cct_k=cct, cri=90,
                               product=pinfo, dimmer=1.0))
            mesh("fix-" + f.id, "black-metal", disc_down(f.x, f.y, f.z - 0.0015, 0.0415), "fixture", room=f.room,
                 label="fitting " + f.id)
            mats.setdefault("lens-%d" % cct, dict(kind="emissive", base_rgb=[1, 1, 1], emission_lm_per_m2=40000.0,
                                                  cct_k=cct, note="visible lens glow (no light contribution)"))
            mesh("lens-" + f.id, "lens-%d" % cct, disc_down(f.x, f.y, f.z - 0.002, 0.018), "fixture",
                 room=f.room, label="fitting " + f.id,
                 visibility={"camera": True, "glossy": True, "diffuse": False, "shadow": False,
                             "transmission": False}, layer=f.layer)
        elif f.kind == "DESK":
            lights.append(dict(id=f.id, room=f.room, layer=f.layer, type="ies", position=[f.x, f.y, f.z - 0.03],
                               aim=[0.0, 0.0, -1.0], spin_deg=0.0, ies="generic/DESK.ies", lumens=round(f.lumens, 1),
                               cct_k=cct, cri=90, product=pinfo, dimmer=1.0))
            # a TABLE lamp on the desk it serves: weighted base on the desktop, a stem, the open shade (a hood over
            # the lamp, open below). The first version bracketed an arm to the nearest wall in y; over the kids'
            # desks that wall is the window, so the shades hung in the glass (client: "flying" objects).
            from .. import furniture as G_
            desk = next((i for i in F.layout(lay) if i["type"] == "desk" and i["level"] == f.level and
                         F.footprint(i)[0] <= f.x <= F.footprint(i)[2] and F.footprint(i)[1] <= f.y <= F.footprint(i)[3]),
                        None)
            if desk is None:
                raise ValueError(f.id + ": a desk lamp must stand on a desk")
            ztop = LZ[desk["level"]] + desk["h"]

            def cyl(cx_, cy_, r, z0, z1, seg=20):
                vv, tt = G_._cylinder(cx_, cy_, z0, z1, r, seg)
                return [[list(vv[i]) for i in t] for t in tt]
            # an arm lamp: the weighted base at the BACK of the desk, the stem, then an arm over the task point.
            # Draft 10's base stood ON the task point and shaded it (kids' desks measured 1 lx of 400).
            bx, by = {0: (0, -1), 180: (0, 1), -90: (-1, 0), 90: (1, 0)}[desk["rot"]]
            q_ = F.footprint(desk)
            reach = 0.28
            base_x = min(max(f.x + bx * reach, q_[0] + 0.09), q_[2] - 0.09)
            base_y = min(max(f.y + by * reach, q_[1] + 0.09), q_[3] - 0.09)
            top = f.z + 0.12
            arm = box_faces(min(base_x, f.x) - 0.007, min(base_y, f.y) - 0.007, top - 0.007,
                            max(base_x, f.x) + 0.007, max(base_y, f.y) + 0.007, top + 0.007)
            mesh("lamp-shade-" + f.id, "black-metal",
                 box_faces(f.x - 0.08, f.y - 0.08, f.z - 0.01, f.x + 0.08, f.y + 0.08, f.z + 0.05)[1:]
                 + cyl(f.x, f.y, 0.007, f.z + 0.05, top), "fixture", room=f.room, label="fitting " + f.id)
            mesh("lamp-arm-" + f.id, "black-metal",
                 cyl(base_x, base_y, 0.07, ztop, ztop + 0.015) + cyl(base_x, base_y, 0.007, ztop + 0.015, top + 0.007)
                 + arm, "fixture", room=f.room, label="fitting " + f.id + " (base, stem and arm)")
        elif f.kind == "VSCONCE":
            area = 4 * 0.06 * 0.5
            mname = "opal-vsconce-%d" % cct
            mats[mname] = dict(kind="emissive", base_rgb=[0.95, 0.93, 0.90],
                               emission_lm_per_m2=round(f.lumens / area, 1), cct_k=cct,
                               note="vertical opal sconce, %d lm (GENERIC)" % f.lumens)
            mesh("lamp-" + f.id, mname, box_faces(f.x - 0.03, f.y - 0.03, f.z - 0.25, f.x + 0.03, f.y + 0.03,
                                                  f.z + 0.25), "fixture", room=f.room, label="fitting " + f.id,
                 layer=f.layer)
            # its wall bracket: the design sets the tube 60 mm off the wall (to its axis); the first version left a
            # 30 mm air gap behind it
            ax_ = 1 if f.aim[0] > 0 else -1
            wall_x = f.x - ax_ * 0.06
            mesh("bracket-" + f.id, "brass", box_faces(min(wall_x, f.x - ax_ * 0.03), f.y - 0.015, f.z - 0.02,
                                                       max(wall_x, f.x - ax_ * 0.03), f.y + 0.015, f.z + 0.02),
                 "fixture", room=f.room, label="fitting " + f.id + " (bracket)")
        elif f.kind in ("PEN-GLOBE", "PEN-SMALL", "SCONCE", "WALL-READ"):
            r = k.get("diameter", 0.2) / 2
            area = 4 * math.pi * r * r
            mname = "opal-%s-%d" % (f.kind.lower(), cct)
            mats[mname] = dict(kind="emissive", base_rgb=[0.95, 0.93, 0.90], emission_lm_per_m2=round(f.lumens / area,
                                                                                                       1),
                               cct_k=cct, note="opal glass globe as a diffuse emitter, %d lm (GENERIC)" % f.lumens)
            cz = f.z + r if f.kind not in ("SCONCE", "WALL-READ") else f.z
            mesh("lamp-" + f.id, mname, sphere(f.x, f.y, cz, r), "fixture", room=f.room,
                 label="fitting " + f.id, layer=f.layer)
            if f.kind == "WALL-READ":
                wall_y = (F.footprint(it_all["library-daybed"])[1] if f.room == "bar-alcove" else
                          lay["rooms"]["parents-bed"]["rect"][1])
                mesh("bracket-" + f.id, "brass", box_faces(f.x - 0.012, wall_y, f.z - 0.012,
                     f.x + 0.012, f.y, f.z + 0.012), "fixture", room=f.room,
                     label="ASSUMED wall swing arm " + f.id)
            top = f.extra.get("hang_from")
            if top:
                zb = LZ[f.level] + top if top < 2.9 and f.level == "B" else top
                if f.level == "B":
                    zb = LZ["B"] + VL.CEILING if top > 0 else top
                mesh("cord-" + f.id, "black-metal", box_faces(f.x - 0.003, f.y - 0.003, cz + r, f.x + 0.003,
                                                              f.y + 0.003, zb), "fixture", room=f.room,
                     label="fitting " + f.id)
                mesh("canopy-" + f.id, "brass", box_faces(f.x - 0.05, f.y - 0.05, zb - 0.02, f.x + 0.05, f.y + 0.05,
                                                          zb), "fixture", room=f.room, label="fitting " + f.id)
        elif f.kind == "PEN-LIN":
            Lg = k["length"]
            zb = f.z
            mesh("lamp-body-" + f.id, "black-metal", box_faces(f.x - Lg / 2, f.y - 0.03, zb, f.x + Lg / 2, f.y + 0.03,
                                                              zb + 0.06), "fixture", room=f.room,
                 label="fitting " + f.id)
            mname = "led-lin-%d" % cct
            mats[mname] = dict(kind="emissive", base_rgb=[1, 1, 1], emission_lm_per_m2=round(
                f.lumens / ((Lg - 0.1) * 0.03), 1), cct_k=cct, note="linear pendant diffuser, %d lm (GENERIC)" %
                f.lumens)
            mesh("lamp-" + f.id, mname, [quad_down(f.x - Lg / 2 + 0.05, f.y - 0.015, f.x + Lg / 2 - 0.05,
                                                   f.y + 0.015, zb - 0.001)], "fixture", room=f.room,
                 label="fitting " + f.id, layer=f.layer)
            ceil = LZ["B"] + VL.CEILING
            for s in (-1, 1):
                mesh("wire-%s-%d" % (f.id, s), "black-metal", box_faces(f.x + s * 0.6 - 0.002, f.y - 0.002, zb + 0.06,
                                                                         f.x + s * 0.6 + 0.002, f.y + 0.002, ceil),
                     "fixture", room=f.room, label="fitting " + f.id)
        elif k["mount"] == "strip":
            lights.append(dict(id=f.id, room=f.room, layer=f.layer, type="line", position=[f.x, f.y, f.z],
                               aim=_unit(f.aim), size=[0.012, f.length], length_dir=list(f.along), spread_deg=120,
                               lumens=round(f.lumens, 1), cct_k=cct, cri=90, product=pinfo, dimmer=1.0))
            if f.kind == "BACK" and f.room == "bar-alcove":
                mesh("detail-cabinet-led-" + f.id, "opal-strip", box_faces(
                    f.x - f.length / 2, f.y - 0.04, f.z - 0.012,
                    f.x + f.length / 2, f.y + 0.006, f.z + 0.002), "fixture", room=f.room,
                    label="ASSUMED concealed LED strip behind library shelf books")
        elif k["mount"] == "wall-marker":
            w, h = 0.10, 0.04
            mname = "marker-%d" % cct
            mats[mname] = dict(kind="emissive", base_rgb=[1, 1, 1], emission_lm_per_m2=round(f.lumens / (w * h), 1),
                               cct_k=cct, note="recessed wall marker, %d lm (GENERIC)" % f.lumens)
            ay = f.aim[1]
            # flush on the wall face behind it (the design's offset left path markers 21 mm proud of the wall)
            faces_ = [w[3] if ay > 0 else w[1] for w in walls_by_level[f.level] if w[0] <= f.x <= w[2] and
                      abs((w[3] if ay > 0 else w[1]) - f.y) < 0.1]
            fy = min(faces_, key=lambda v: abs(v - f.y)) if faces_ else f.y
            yy = fy + (0.001 if ay > 0 else -0.001)
            face = [[f.x - w / 2, yy, f.z - h / 2], [f.x + w / 2, yy, f.z - h / 2], [f.x + w / 2, yy, f.z + h / 2],
                    [f.x - w / 2, yy, f.z + h / 2]]
            if ay < 0:
                face = face[::-1]
            mesh("marker-" + f.id, mname, [face], "fixture", room=f.room, label="fitting " + f.id, layer=f.layer)
    notes.append("Photometry: iGuzzini Laser Evo D75 (DL AAK3EW, DLN AAIIA6, ADJ AAHENX; verified LDTs); wall "
                 "washer positions use AAK3EW as a stated substitute; strips, pendants, sconces and markers are "
                 "GENERIC (named in each caption).")

    scene = {"schema": "villa-render/1", "id": "D1", "north": {"model_y_bearing_deg": 20.0},
             "library_root": "$HOME/archpipe/assets/library", "materials": mats, "meshes": meshes, "lights": lights,
             "props": props(lay) + land_props, "cloth": cloth, "curtains": curtains, "views": views,
             "exposure_mode": "set-metered", "exposure": EXPOSURE, "sky": {"day": "nishita",
                                           "evening": {"hdri": "belfast_sunset_puresky.exr", "horizontal_lux": 30.0},
                                           "night": {"hdri": "dikhololo_night.exr", "horizontal_lux": 0.3}},
             "measurement_maintenance_factor": VL.MF,
             "measurement_points": [dict(room=room, card=card, position=[x, y, z], label=label,
                                         required_lux=VL.card_value(card))
                                    for room, card, x, y, z, label in VL.task_points(lay)],
             "notes": notes + ["Furniture, joinery and sanitaryware are PROCEDURAL STAND-INS at the checked sizes "
                               "(products still to choose): shapes are not products. Pulls, taps, leg styles, sink "
                               "and cushion forms are ASSUMED details inside each checked envelope.",
                               "Finishes are ASSUMED from the taste profile (no finishes answers yet).",
                               "Dressing (plants, books, vases, art, pillows) is not design."]}
    _seat_recessed_on_soffit(scene)
    return scene


def _seat_recessed_on_soffit(scene):
    """Guard that the authored fittings and cords already reach the ceiling rendered above them."""
    from . import render_support as S
    import numpy as np
    shell = [m for m in scene["meshes"] if m["group"] in ("shell", "context")]
    tris, owner = S._triangles(shell)
    surf = S._Surfaces(tris, owner)
    by = {m["id"]: m for m in scene["meshes"]}
    moved = []
    for L in scene["lights"]:
        if ("fix-" + L["id"]) not in by:
            continue
        x, y, _ = L["position"]
        fix = by["fix-" + L["id"]]
        zf = fix["faces"][0][0][2]
        m = surf.down & (surf.lo[:, 0] <= x) & (x <= surf.hi[:, 0]) & (surf.lo[:, 1] <= y) & (y <= surf.hi[:, 1])
        above = []
        for t in surf.t[m]:
            (ax, ay, az), (bx, by_, bz), (cx, cy, cz) = t
            d = (by_ - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-12:
                continue
            l1 = ((by_ - cy) * (x - cx) + (cx - bx) * (y - cy)) / d
            l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / d
            if min(l1, l2, 1 - l1 - l2) < -1e-6:
                continue
            zz = l1 * az + l2 * bz + (1 - l1 - l2) * cz
            if zf - 0.02 < zz < zf + 0.6:
                above.append(zz)
        if not above:
            continue
        dz = min(above) - zf - 0.0015
        if abs(dz) < 0.012:
            continue
        moved.append("%s %+.0f mm" % (L["id"], dz * 1000))
    # A pendant cord must reach the actual ceiling above its canopy.
    for mid in [m["id"] for m in scene["meshes"] if m["id"].startswith("cord-")]:
        cord = by[mid]
        pts = [v for f in cord["faces"] for v in f]
        x = sum(v[0] for v in pts) / len(pts)
        y = sum(v[1] for v in pts) / len(pts)
        top = max(v[2] for v in pts)
        m = surf.down & (surf.lo[:, 0] <= x) & (x <= surf.hi[:, 0]) & (surf.lo[:, 1] <= y) & (y <= surf.hi[:, 1])
        above = []
        for t in surf.t[m]:
            (ax, ay, az), (bx, by_, bz), (cx, cy, cz) = t
            d = (by_ - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-12:
                continue
            l1 = ((by_ - cy) * (x - cx) + (cx - bx) * (y - cy)) / d
            l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / d
            if min(l1, l2, 1 - l1 - l2) < -1e-6:
                continue
            zz = l1 * az + l2 * bz + (1 - l1 - l2) * cz
            if zz > top - 0.02:
                above.append(zz)
        if not above or abs(min(above) - top) < 0.012:
            continue
        dz = min(above) - top
        moved.append("%s cord %+.0f mm" % (mid[5:], dz * 1000))
    if moved:
        raise ValueError("Lighting spec does not match rendered ceiling: " + ", ".join(moved))
    return moved


def _unit(v):
    L = math.sqrt(sum(c * c for c in v)) or 1.0
    return [round(c / L, 4) for c in v]


def in_door_opening(sp, lv, x, y, room):
    """(x, y) stands in the opening of one of `room`'s own doors: within its leaf width less 0.25 m each side (at 0.12 the jamb sat inside the near clip: a black band) and
    within 0.35 m of the wall line."""
    for d in sp["doors"]:
        if d["level"] != lv or d.get("garden") or room not in (d.get("rooms") or []):
            continue
        h = F._door_axis(d) == "h"
        along, across = (x - d["x"], y - d["y"]) if h else (y - d["y"], x - d["x"])
        if abs(along) <= d["width"] / 2 - 0.25 and abs(across) <= 0.35:
            return True
    return False


def frame(lay, pos, tgt, lv, subjects, sensor_mm, lens_mm):
    """Where a photographer with a 24 mm lens would stand to hold the view's subjects: the authored camera first;
    if any subject corner falls outside the frame, the standing point in the same room (0.30 m clear of walls and
    columns, 0.15 m clear of furniture) or in one of its door openings (0.12 m clear of the jambs) and the aim within +-20 deg of the authored one that keep the most of every
    subject in frame, nearest the authored point on ties. What still cannot fit is reported by the views guard."""
    sp = RS.build(lay)
    walls = F._walls(sp, lv) + F._columns()
    items = {i["id"]: i for i in F.layout(lay)}
    pieces = [F.footprint(i) for i in items.values() if i["level"] == lv]
    rooms = [r["rect"] for r in lay["rooms"].values() if r["level"] == lv]
    home_id = next((rid for rid, r in lay["rooms"].items() if r["level"] == lv and
                    r["rect"][0] <= pos[0] <= r["rect"][2] and r["rect"][1] <= pos[1] <= r["rect"][3]), None)
    home = lay["rooms"][home_id]["rect"] if home_id else None
    corners = [c for sid in subjects if sid in items for q in [F.footprint(items[sid])]
               for c in ((q[0], q[1]), (q[2], q[1]), (q[0], q[3]), (q[2], q[3]))]
    half = math.atan(sensor_mm / 2 / lens_mm)
    yaw0 = math.atan2(tgt[1] - pos[1], tgt[0] - pos[0])
    dist = math.hypot(tgt[0] - pos[0], tgt[1] - pos[1])

    def near(q, x, y, c):
        return q[0] - c < x < q[2] + c and q[1] - c < y < q[3] + c

    def ok(x, y):
        if any(near(q, x, y, 0.15) for q in pieces):
            return False
        if near(home, x, y, 0.0):
            return not any(near(q, x, y, 0.30) for q in walls)
        # or standing IN a door opening of the room (within its leaf width less 0.25 m each side (at 0.12 the jamb sat inside the near clip: a black band), within 0.35 m of
        # the wall line), as a photographer does in a small room; never behind a wall
        return in_door_opening(sp, lv, x, y, home_id)

    def miss(x, y, yaw):
        out = 0.0
        for qx, qy in corners:
            a = (math.atan2(qy - y, qx - x) - yaw + math.pi) % (2 * math.pi) - math.pi
            out += max(0.0, abs(a) - half)
        return out

    def widest(x, y, yaw):
        return max(abs((math.atan2(qy - y, qx - x) - yaw + math.pi) % (2 * math.pi) - math.pi) for qx, qy in corners)

    if not corners or home is None or miss(pos[0], pos[1], yaw0) == 0.0:
        return list(pos), list(tgt), False, (math.degrees(widest(pos[0], pos[1], yaw0)) if corners else 0.0)
    best = None
    x = home[0] - 0.3
    while x <= home[2] + 0.3:
        y = home[1] - 0.3
        while y <= home[3] + 0.3:
            if ok(x, y):
                for dyaw in range(-20, 21, 5):
                    yaw = yaw0 + math.radians(dyaw)
                    key = (round(miss(x, y, yaw), 3), math.hypot(x - pos[0], y - pos[1]) + abs(dyaw) / 100)
                    if best is None or key < best[0]:
                        best = (key, x, y, yaw)
            y += 0.1
        x += 0.1
    if best is None:
        return list(pos), list(tgt), False, math.degrees(widest(pos[0], pos[1], yaw0))
    _, x, y, yaw = best
    return ([round(x, 3), round(y, 3)], [round(x + dist * math.cos(yaw), 3), round(y + dist * math.sin(yaw), 3)],
            "doorway" if not near(home, x, y, 0.0) else True, math.degrees(widest(x, y, yaw)))


def generator_rotation(rot):
    """villa_furnish `rot` -> archpipe.furniture `rotation`. Both put the front at local +y and the back (a bed's
    headboard) at local -y; the generator turns anticlockwise. So 0 and 180 map to themselves, -90 (front +x) to 270
    and 90 (front -x) to 90. The first map swapped 0 and 180: the parents' bed rendered with its headboard at the
    foot and the duvet draped over it (client: "duvet flying on the end")."""
    return {0: 0, 180: 180, -90: 270, 90: 90}[rot]


def generated_components(src, kind, hh=None):
    from .. import furniture as FG
    return FG.build_furniture({"id": src["id"], "type": kind, "at": [src["cx"] * 1000, src["cy"] * 1000],
                               "size": [src["w"] * 1000, src["d"] * 1000],
                               "height": (hh or src["h"]) * 1000, "rotation": generator_rotation(src["rot"])})


def part_material(f, part):
    t, room = f["type"], f["room"]
    # detailed-builder parts (villa_furniture_detail): fittings share one finish across the house
    if part in ("handle", "tap", "pull"):
        return "brass"
    if part == "glass-door":
        return "glass-guard"
    if part in ("door-frame", "nook-side", "nook-top"):
        return "walnut"
    if part in ("mattress", "cushion") and t == "daybed_nook":
        return "linen"
    if part in ("gas-lift", "spoke", "caster", "arm-post"):
        return "black-metal"
    if part in ("seat-mesh", "back-mesh", "armrest"):
        return "charcoal-fabric"
    if part in ("hob", "oven-glass", "microwave-glass"):
        return "screen-black"
    if part == "sink":
        return "black-metal"
    if part == "leg" and (t.startswith("sofa") or t in ("armchair", "recliner")):
        return "black-metal"
    if f["type"] == "chair":
        return "walnut" if part in ("leg", "back") else "boucle"
    if f["type"] == "stool":
        return "leather-brown" if part == "seat" else "brass"
    if t.startswith("bed_"):
        if "mattress" in part:
            return "bedding-white"
        if room in ("kids-a", "kids-b"):
            return "white-paint-joinery" if part != "rail" else "white-paint-joinery"
        return "oak"
    if t.startswith("sofa") or t in ("armchair", "recliner"):
        if room == "cinema":
            return "charcoal-fabric"
        if room == "study-game":
            return "sage-fabric"
        return "boucle" if room in ("lounge", "living") and t.startswith("sofa") else "linen"
    if t == "coffee_table":
        return "walnut" if part != "leg" else "black-metal"
    if t in ("dining_6x",):
        return "walnut"
    if t == "desk":
        if part == "cable-tray":
            return "black-metal"
        return "walnut" if room in ("study-game", "parents-bed") else "oak"
    if t == "island":
        return "marble-white" if part == "worktop" else ("black-metal" if part == "plinth" else "walnut")
    if t == "base_run":
        if part == "worktop":
            return "marble-white"
        if part == "plinth":
            return "black-metal"
        return "greige-lacquer"
    if t in ("bookcase", "daybed_nook", "joinery_end_panel"):
        return "walnut"
    if t in ("pantry_shelving", "store_shelving"):
        return "white-paint-joinery"
    if t in ("wardrobe", "tall_column"):
        return "oak" if room not in ("dirty-kitchen",) else "greige-lacquer"
    if t in ("sideboard", "tv_unit", "bedside_table", "window_bench"):
        return "screen-black" if part == "screen" else "walnut"
    if t == "screen":
        return "screen-black"
    if t in ("wc",):
        return "ceramic-white" if part != "flush-plate" else "brass"
    if t in ("washbasin", "washbasin_double"):
        # "walnut" (grain_axis="z") is only safe when the visible front panel's WORLD normal happens to be Y (a
        # wall running along X); against an X-normal wall it sends the panel's own ~19 mm thickness into a
        # sampled coordinate instead (archpipe.blender.grain.mapping_rotated_span) -- the vanity smear (client
        # 2026-09-28, v12-ensuite.png). "walnut-grain-x" is identity rotation: no coordinate is ever rotated, so
        # it samples the true geometry on every wall orientation, not only some.
        return "ceramic-white" if part == "basin" else "walnut-grain-x"
    if t == "bath":
        return "ceramic-white"
    if t == "shower_walkin":
        return "glass-guard" if part == "glass" else ("marble-ensuite" if room == "parents-ensuite" else "marble-bath")
    if t in ("washer_dryer",):
        return "ceramic-white"
    if t in ("folding_counter",):
        return "marble-white" if part == "worktop" else "greige-lacquer"
    return "oak"


# ------------------------------------------------------------------ dressing
def props(lay):
    """Dressing (NOT design): placed on the checked furniture's tops or the floor beside it."""
    it = {i["id"]: i for i in F.layout(lay)}
    fp = {k: F.footprint(v) for k, v in it.items()}
    B, G = LZ["B"], LZ["GF"]
    out = []

    def add(pid, asset, x, y, z, rz=0.0, s=1.0, label=""):
        out.append({"id": pid, "asset": asset, "position": [round(x, 3), round(y, 3), round(z, 3)],
                    "rotation_deg": [0, 0, rz], "scale": s, "label": "dressing: " + (label or asset)})

    def c(k):
        q = fp[k]
        return (q[0] + q[2]) / 2, (q[1] + q[3]) / 2

    x, y = c("k-island")
    add("island-bowl", "wooden_bowl_01", x + 0.6, y + 0.1, B + it["k-island"]["h"], label="bowl on the island")
    x, y = c("dining-table")
    add("dining-vase", "ceramic_vase_01", x, y, B + it["dining-table"]["h"], label="vase on the table")
    x, y = c("dining-sideboard")
    add("sideboard-vase", "ceramic_vase_03", x - 0.5, y, B + it["dining-sideboard"]["h"], label="vase on the sideboard")
    add("sideboard-art", "hanging_picture_frame_01", x, fp["dining-sideboard"][1] + 0.02, B + 1.45, 0, 1.0,
        "art above the sideboard")
    x, y = c("lounge-coffee")
    add("lounge-books", "book_encyclopedia_set_01", x - 0.3, y, B + it["lounge-coffee"]["h"], label="books")
    add("lounge-plant", "pachira_aquatica_01", 4.3, -24.35, B, label="money tree in the corner by the street window")
    x, y = c("living-coffee")
    add("living-plant-table", "potted_plant_04", x + 0.3, y, B + it["living-coffee"]["h"],
        label="single potted table plant, 0.168 x 0.185 m footprint, 0.267 m tall")
    add("living-plant", "potted_plant_02", 22.1, -24.25, B, label="floor plant by the garden door")
    # Client round 2: the lit glass-door cabinets are for book display. Every shelf (tops at 0.102 plinth, then
    # 0.442/0.842/1.242/1.642 m, villa_furniture_detail._glass_bookcase) holds book sets 0.55 m wide, 0.24 m tall
    # (measured bounds_m), alternating full and half rows so the display reads curated, not stocked.
    n = 0
    for cab, full, half in (("library-cabinet-left", (0.05, 0.62), (0.30,)),
                            ("library-cabinet-right", (0.05, 0.90), (0.45,))):
        bk = fp[cab]
        for s, z in enumerate((0.080, 0.442, 0.842, 1.242, 1.642)):
            for dx in (full if s % 2 == 0 else half):
                add("library-books-%d" % n, "book_encyclopedia_set_01", bk[0] + dx, bk[1] + 0.16, B + z,
                    label="books on the library shelves")
                n += 1
    x, y = c("pb-bedside")
    add("bedside-books", "book_encyclopedia_set_01", x, y, G + it["pb-bedside"]["h"], label="books on the bedside")
    # plants where a person would put them (client: "consider if all the added plants are ... reasonable"): the
    # bedroom one moved out of the vanity chair's way into the window corner beside the vanity; the study one out of
    # the new low window into the corner beside the TV unit
    add("bedroom-plant", "potted_plant_01", fp["pb-vanity"][2] - 0.17, fp["pb-vanity"][3] + 0.32, G, s=0.58,
        label="single potted plant, 0.341 x 0.367 m footprint, 0.783 m tall")
    add("study-plant", "potted_plant_01", (fp["study-tv"][0] + fp["study-tv"][2]) / 2, fp["study-tv"][3] + 0.45, G,
        label="plant")
    for rid, sofa in (("lounge", "lounge-sofa"), ("living", "living-sofa")):
        x, y = c(sofa)
        add("pillows-" + rid, "throw_pillows_01", x, y - 0.05 if rid == "lounge" else y, B + 0.44,
            0 if rid == "lounge" else 0, label="throw pillows")
    return out


# ------------------------------------------------------------------ views
EXPOSURE = {  # PRE-REGISTERED (2026-09-27) before the first render; incident metering EV = log2(E * 100 / 250)
    "day": {"ev100": 8.0, "white_balance_k": 5500},          # interiors lit by daylight, ~100-600 lx
    "evening": {"ev100": 6.0, "white_balance_k": 3000},      # ADR-0013: lamps 3000 K      # interiors at dusk by their own light, ~100-300 lx
    "exterior-dusk": {"ev100": 4.0, "white_balance_k": 4300},
    # exteriors by day: their own locked state (draft finals: v19 on the interiors' day lock was blown out)
    "exterior-day": {"ev100": 14.0, "white_balance_k": 5500},
}


def VIEWS(lay=None):
    """The 14 views: the client's 8 (questionnaire) + 6 more. Camera at eye height 1.55 m (1.2 m for the seated
    cinema), level, framed on plan (check with scripts/villa_render_views.py)."""
    B, G = LZ["B"], LZ["GF"]
    day = "2026-10-15T10:30:00+03:00"
    dusk = "2026-10-15T18:35:00+03:00"
    V = []

    def v(vid, title, state, pos, tgt, lens, subjects, when=None, layers=None, dimmers=None, shift_y=0.0,
          room=None, final_only=False, seated=False, exposure=None):
        V.append({"id": vid, "title": title, "state": state, "when": when or (day if state == "day" else dusk),
                  "camera": {"position": pos, "target": tgt, "lens_mm": lens, "sensor_mm": 36, "shift_x": 0.0,
                             "shift_y": shift_y},
                  "resolution": [1920, 1280],
                  "layers_on": layers if layers is not None else (["ambient", "task", "accent", "decorative"]
                                                                  if state != "day" else []),
                  "dimmers": dimmers or {},
                  "exposure": exposure or (state if state in EXPOSURE else "day"),
                  "subjects": subjects, "samples": 1024, "room": room, "final_only": final_only,
                  "seated": seated})

    # Interior views are declared by INTENT (room + subjects); `render_views.choose` finds where a photographer
    # stands and aims (client 2026-09-27: some hand-typed cameras "are looking at the wrong direction and
    # uninformative"). Exteriors and the stair keep authored cameras. `final_only` views are skipped in review drafts
    # (client: "choose their locations, so we can generate them later ... not waste time producing them every time").
    BASEMENT_DAY = dict(layers=["ambient", "accent"], dimmers={"ambient": 0.5, "accent": 0.5})  # stated in captions
    I = None                                                   # chosen camera
    v("v01-kitchen-garden", "Kitchen island to the garden", "day", I, I, 24, ["k-island", "dining-table"],
      room="kitchen", **BASEMENT_DAY)
    v("v02-garden-living", "Garden living", "day", I, I, 24, ["living-sofa", "library-daybed"], room="living",
      **BASEMENT_DAY)
    v("v03-street-lounge", "Street lounge", "day", I, I, 24, ["lounge-sofa", "lounge-tv"], room="lounge",
      **BASEMENT_DAY)
    v("v04-study-deck", "GF study: desks at the windows", "day", I, I, 24, ["study-desk", "study-adult-desk"],
      room="study-game")
    v("v05-parents-bedroom", "Parents' bedroom", "evening", I, I, 24, ["pb-bed"], room="parents-bed",
      dimmers={"ambient": 0.3, "accent": 0.4, "task": 0.5})
    v("v06-kids-room", "Kids' room A", "day", I, I, 24, ["ka-bunk", "ka-desk-1"], room="kids-a")
    v("v07-terrace-dusk", "Garden and terrace at dusk", "exterior-dusk", [28.2, -21.2, B + 1.35], [21.0, -26.4, B + 1.35],
      24, ["landscape-sofa", "living-sofa"], shift_y=0.10, layers=["ambient", "task", "accent", "decorative"],
      dimmers={"ambient": 0.5, "task": 0.4})
    v("v08-cinema", "Cinema: seating and screen", "evening", I, I, 24, ["cinema-sofa", "cinema-tv"], room="cinema")
    v("v09-dining-evening", "Dining and island at night", "evening", I, I, 24, ["dining-table", "k-island"],
      room="dining", dimmers={"ambient": 0.35, "task": 0.5})
    v("v10-living-evening", "Garden living at night: cove and library", "evening", I, I, 24,
      ["library-daybed", "living-sofa"], room="living", dimmers={"ambient": 0.25, "task": 0.5})
    v("v11-stair-void", "The stair up to the globe cluster in the void", "evening", [10.45, -27.95, B + 1.45],
      [5.8, -27.95, B + 1.75], 14, ["stair-gf", "stair-b"], shift_y=0.30)
    v("v12-ensuite", "Parents' ensuite", "evening", I, I, 24, ["pe-bath", "pe-basin"], room="parents-ensuite",
      dimmers={"ambient": 0.5})
    v("v13-kids-b", "Kids' room B at bedtime", "evening", I, I, 24, ["kb-bed", "kb-desk"], room="kids-b")
    v("v14-dressing", "Parents' dressing", "evening", I, I, 24, ["pd-hang-1"], room="parents-dressing",
      dimmers={"ambient": 0.6})
    # client: "Did we render pictures for parent's bathroom, family bathroom, guest bathroom, dirt kitchen"
    # bathrooms are used with their lights on, day or night; stated in the caption like the basement by day
    BATH_DAY = dict(layers=["ambient", "task", "accent"], dimmers={})
    v("v15-family-bath", "Family bathroom", "day", I, I, 24, ["fb-basin", "fb-shower"], room="family-bath",
      **BATH_DAY)
    V[-1]["caption_notes"] = ["The WC is in the corner beside the door, below and outside this frame: no standing "
                              "point holds basin, shower and WC together (checked by render_views.choose)."]
    v("v16-guest-wc", "Guest WC", "evening", I, I, 24, ["gwc-basin", "gwc-wc"], room="guest-wc")
    v("v17-dirty-kitchen", "Dirty kitchen and laundry", "day", I, I, 24, ["dk-run", "dk-appliance-bank"], room="dirty-kitchen",
      **BASEMENT_DAY)
    # the rest of the ten more, for the final set (v15-v17 above are three of them)
    # a street elevation needs the site frontage modelled (from the street only the boundary wall showed, from the
    # front yard only the ramp enclosure): deferred; the study's other side instead
    v("v18-study-evening", "Study at night: sofa and TV from the desks", "evening", I, I, 24,
      ["study-sofa", "study-tv"], room="study-game", final_only=True, dimmers={"ambient": 0.4, "task": 0.6})
    v("v19-garden-facade", "Garden elevation by day", "day", [28.2, -31.0, B + 1.35], [20.0, -24.0, B + 1.35], 24,
      ["living-sofa"], final_only=True, shift_y=0.12, exposure="exterior-day")
    v("v20-kitchen-run", "Kitchen run and island at night", "evening", I, I, 24, ["k-run", "k-island"],
      room="kitchen", final_only=True, dimmers={"ambient": 0.4, "task": 0.8})
    v("v21-lounge-evening", "Street lounge at night", "evening", I, I, 24, ["lounge-sofa", "lounge-tv"],
      room="lounge", final_only=True, dimmers={"ambient": 0.3, "accent": 0.6})
    v("v22-parents-day", "Parents' bedroom by day", "day", I, I, 24, ["pb-bed", "pb-vanity"], room="parents-bed",
      final_only=True)
    # a windowless corridor is used with its lights on (first final, lights off by day: black)
    v("v23-gf-gallery", "Ground-floor corridor to the stair void", "day", [19.1, -28.02, G + 1.35],
      [8.9, -28.02, G + 1.35], 24, [], final_only=True, layers=["ambient", "accent"], dimmers={},
      exposure="evening")                      # lit by its lamps only: the lamp white balance, as a photographer would
    # the garden-level entrance gave no informative frame (a door leaf and a cabinet); the bar alcove instead
    v("v24-bar-alcove", "Library and daybed nook at night", "evening", I, I, 24, ["library-cabinet-left", "library-daybed", "library-cabinet-right"], room="living",
      final_only=True, dimmers={"ambient": 0.3, "accent": 0.8})
    # ADR-0013 part 8: 24 mm, a LEVEL camera at eye height 1.35 m (1.20 m seated), lens shift not tilt
    from . import render_views as RV
    sp_ = RS.build(lay)
    # floor-standing props (plants) as 0.5 m pieces, per storey, for the chooser's looming and clearance tests
    floor_props = [(pr["position"][0] - 0.25, pr["position"][1] - 0.25, pr["position"][0] + 0.25,
                    pr["position"][1] + 0.25, "B" if pr["position"][2] < -0.5 else "GF") for pr in props(lay)
                   if any(abs(pr["position"][2] - z_) < 0.02 for z_ in LZ.values())]
    for x in V:
        c = x["camera"]
        if x["state"] == "exterior-dusk" or x["id"] in ("v18-street-facade", "v19-garden-facade"):
            continue
        room = x.get("room")
        lvz = LZ[lay["rooms"][room]["level"]] if room else (LZ["B"] if c["position"][2] < -0.1 else LZ["GF"])
        eye = 1.20 if x.get("seated") else 1.35
        if room:
            got = RV.choose(lay, room, x["subjects"], lens_mm=24, sensor_mm=c["sensor_mm"], sp=sp_,
                            extra=floor_props)
            half24 = math.degrees(math.atan(c["sensor_mm"] / 2 / 24))
            if not got["subjects_in_frame"]:
                # client 2026-09-27: where 24 mm cannot hold the room's subjects from any standing point, 16 mm
                half16 = math.degrees(math.atan(c["sensor_mm"] / 2 / 16))
                got16 = RV.choose(lay, room, x["subjects"], lens_mm=16, sensor_mm=c["sensor_mm"], sp=sp_,
                                  extra=floor_props)
                if not got16["subjects_in_frame"]:
                    raise ValueError("%s: even 16 mm cannot hold %s" % (x["id"], x["subjects"]))
                c["lens_mm"] = 16
                c["lens_basis"] = ("widest subject corner %.1f deg off axis from the best standing point; 24 mm holds "
                                   "%.1f, 16 mm holds %.1f; at 16 mm widest %.1f deg" % (
                                       got["widest_deg"], half24, half16, got16["widest_deg"]))
                x.setdefault("caption_notes", []).append(
                    "Lens 16 mm, not the standard 24 mm: the room cannot hold its subjects at 24 mm from any standing "
                    "point (%s). Wider than the eye." % c["lens_basis"])
                got = got16
            else:
                c["lens_mm"] = 24
            c["position"] = got["position"] + [round(lvz + eye, 3)]
            c["target"] = got["target"] + [round(lvz + eye, 3)]
            c["shift_y"] = 0.0
            c["home_room"] = room
            inside = lay["rooms"][room]["rect"]
            # strictly inside, as render_views does: a point ON the room's edge stands in a door opening
            c["reframed"] = "doorway" if (RV._in_opening(sp_, lay["rooms"][room]["level"], got["position"][0],
                                                          got["position"][1], room) or
                                          not (inside[0] < got["position"][0] < inside[2] and
                                               inside[1] < got["position"][1] < inside[3])) else "chosen"
            continue
        # authored interior camera (the stair): level at eye height, framed by `frame`
        c["position"][2] = round(lvz + eye, 3)
        c["target"][2] = c["position"][2]
        c["lens_mm"] = 24
        c["shift_y"] = 0.12 if x["id"].startswith("v11") else 0.0
        c["home_room"] = next((rid for rid, r in lay["rooms"].items() if r["level"] == ("B" if lvz < -0.1 else "GF")
                               and r["rect"][0] <= c["position"][0] <= r["rect"][2]
                               and r["rect"][1] <= c["position"][1] <= r["rect"][3]), None)
        pos, tgt, moved, widest = frame(lay, c["position"][:2], c["target"][:2], "B" if lvz < -0.1 else "GF",
                                        x["subjects"], c["sensor_mm"], c["lens_mm"])
        c["position"][:2], c["target"][:2], c["reframed"] = pos, tgt, moved
    # sun per view (laptop side, archpipe.solar)
    from datetime import datetime
    from ..solar import sun_position
    import yaml
    site = yaml.safe_load((ROOT / "spec" / "villa-site.yaml").read_text(encoding="utf-8"))
    from datetime import timezone
    loc = site["location"]
    for x in V:                                   # Egypt summer time (+03:00) is written into each timestamp
        t = datetime.fromisoformat(x["when"]).astimezone(timezone.utc)
        s = sun_position(t, loc["latitude"], loc["longitude"])
        x["sun"] = {"altitude_deg": round(s.altitude, 2), "azimuth_true_deg": round(s.azimuth, 2)}
    return V


def write(path=None, views=None):
    scene = build(views=views)
    path = Path(path or OUT / "scene.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scene), encoding="utf-8")
    return path, scene
