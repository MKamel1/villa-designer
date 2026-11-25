"""Build the reference-match mock-up scene: a COPY of the render-set scene.json plus the proposals.

    python scripts/refmatch_build.py out/RM/base/scene.json out/RM/mock/scene.json [room ...]

Geometry comes from the design model's own coordinates (see proposals.json `location`).
Nothing here edits the production scene or the design model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from archpipe.refmatch.mockup import Mockup, sphere_faces  # noqa: E402
from archpipe.scene_reproducibility import require_outward  # noqa: E402

GLOW = "rm-glow-2700"
Z_UP = (0.0, 0.0, 1.0)


def materials(m):
    # Look-alikes: colour from the maker's own swatch image (mean linear), CC0 texture where one is held.
    m.material("rm-stone-tafu", kind="principled", asset="Marble007", base_rgb=[0.36, 0.31, 0.26],
               reflectance=0.5, roughness=0.18, tile_m=2.4, contrast=0.55,
               note="LOOK-ALIKE (ambientCG Marble007, CC0) standing for Marazzi Grande Marble Look Tafu Lux RT MEP6; colour from maker image")
    m.material("rm-stone-frappuccino", kind="principled", asset="Marble007", base_rgb=[0.10, 0.07, 0.05],
               reflectance=0.4, roughness=0.15, tile_m=2.4, contrast=0.8,
               note="LOOK-ALIKE (ambientCG Marble007, CC0) standing for Marazzi Grande Marble Look Frappuccino Lux M0G3; colour from maker image")
    m.material(GLOW, kind="emissive", base_rgb=[1, 1, 1], emission_lm_per_m2=25000.0, cct_k=2700,
               note="visible LED glow of a proposed cove/halo/toe strip (the light itself is a lighting ask)")
    m.material("rm-glass-globe", kind="glass", base_rgb=[1, 1, 1], transmittance=0.85, interfaces=2, roughness=0.0,
               note="clear blown-glass globe (look-alike for Bocci 28 Series, Clear)")
    m.material("rm-opal", kind="emissive", base_rgb=[0.95, 0.93, 0.9], emission_lm_per_m2=9000.0, cct_k=2700,
               note="opal glass globe, lit (look-alike for Flos IC Lights S1 opal diffuser)")
    m.material("rm-cord", kind="principled", base_rgb=[0.02, 0.02, 0.02], reflectance=0.03, roughness=0.5, note="black cord")


def sphere(m, mid, room, material, c, r):
    faces = sphere_faces(*c, r, 18)
    require_outward(faces, mid)
    m.s["meshes"].append({"id": mid, "group": "furniture", "material": material, "room": room, "label": f"RM mock-up {mid}",
                          "faces": faces, "part_kind": "luminaire", "local_axes": ["x", "y", "z"], "basis": "refmatch-mockup"})
    m.added.append(mid)


def glow_light(m, lid, room, pos, aim, length, ldir, lm, width=0.012):
    m.line_light(lid, room, pos, aim, length, ldir, lm, width=width)


def living(m):
    R = "lounge"
    # 1. lounge TV wall: book-matched Tafu stone between walnut flutes; reveal halo; toe glow; top wash.
    m.remove_meshes("detail-tv-fluting")
    y0, y1 = -23.69, -23.65
    m.slats("rm-tv-flute-l", R, "walnut", "x", 0, 0, 4.40, 4.80, -3.0, -0.3, 0.04, 0.06, 0.04, y0, 1)
    m.slats("rm-tv-flute-r", R, "walnut", "x", 0, 0, 7.20, 7.56, -3.0, -0.3, 0.04, 0.06, 0.04, y0, 1)
    m.box("rm-tv-stone", R, "rm-stone-tafu", 4.80, 7.20, y0, y1, -3.0, -0.3, "Tafu Lux 2 x 120x278 book-matched")
    m.box("rm-tv-halo-t", R, GLOW, 5.10, 6.90, -23.74, -23.69, -1.36, -1.34)
    m.box("rm-tv-halo-b", R, GLOW, 5.10, 6.90, -23.74, -23.69, -2.46, -2.44)
    m.box("rm-tv-halo-l", R, GLOW, 5.09, 5.11, -23.74, -23.69, -2.46, -1.34)
    m.box("rm-tv-halo-r", R, GLOW, 6.89, 6.91, -23.74, -23.69, -2.46, -1.34)
    m.box("rm-tv-toe", R, GLOW, 5.0, 7.0, -24.0, -23.75, -2.93, -2.91)
    glow_light(m, "RM-LT-tv-halo", R, (6.0, -23.75, -1.4), (0, -1, 0), 1.8, (1, 0, 0), 70)
    glow_light(m, "RM-LT-tv-toe", R, (6.0, -23.9, -2.92), (0, 0, -1), 2.0, (1, 0, 0), 50)
    glow_light(m, "RM-LT-tv-wash", R, (6.0, -23.72, -0.33), (0, -0.25, -1), 2.4, (1, 0, 0), 220)
    # 2. garden living: stone panel in the library alcove frame + backlit edge; clear-glass pendant cluster.
    RL = "living"
    m.box("rm-alc-stone", RL, "rm-stone-tafu", 18.70, 20.64, -29.74, -29.70, -2.45, -0.95, "Tafu Lux alcove panel")
    m.box("rm-alc-glow-l", RL, GLOW, 18.70, 18.72, -29.70, -29.66, -2.45, -0.95)
    m.box("rm-alc-glow-r", RL, GLOW, 20.62, 20.64, -29.70, -29.66, -2.45, -0.95)
    glow_light(m, "RM-LT-alc-wash", RL, (19.67, -29.66, -0.97), (0, -0.3, -1), 1.9, (1, 0, 0), 140)
    cx, cy = 20.55, -26.0
    for i, (dx, dy, zb, r) in enumerate([(0, 0, -1.45, 0.085), (0.2, 0.1, -1.2, 0.07), (-0.2, -0.08, -1.3, 0.075),
                                         (0.08, -0.22, -1.0, 0.065), (-0.1, 0.2, -0.95, 0.06)]):
        c = (cx + dx, cy + dy, zb + r)
        sphere(m, f"rm-glb-{i}", RL, "rm-glass-globe", c, r)
        sphere(m, f"rm-glbc-{i}", RL, "rm-opal", c, r * 0.35)
        m.box(f"rm-glbw-{i}", RL, "rm-cord", c[0] - 0.003, c[0] + 0.003, c[1] - 0.003, c[1] + 0.003, c[2] + r, -0.27)
        glow_light(m, f"RM-LT-glb-{i}", RL, c, (0, 0, -1), 0.06, (1, 0, 0), 150, width=0.06)


def media(m):
    R = "cinema"
    xf = 9.18
    m.box("rm-cin-stone", R, "rm-stone-frappuccino", xf - 0.04, xf, -22.90, -20.65, -2.9, -1.1, "Frappuccino Lux book-matched")
    m.slats("rm-cin-flute", R, "walnut", "y", 0, 0, -23.55, -22.95, -2.9, -1.1, 0.04, 0.06, 0.04, xf - 0.04, -1)
    m.box("rm-cin-console", R, "walnut", 8.74, 9.18, -22.95, -20.62, -2.80, -2.45, "floating console")
    m.box("rm-cin-toe", R, GLOW, 8.78, 9.14, -22.9, -20.67, -2.83, -2.81)
    m.box("rm-cin-halo-t", R, GLOW, 9.02, 9.06, -22.76, -20.74, -1.46, -1.44)
    m.box("rm-cin-halo-b", R, GLOW, 9.02, 9.06, -22.76, -20.74, -2.58, -2.56)
    m.box("rm-cin-halo-l", R, GLOW, 9.02, 9.06, -22.76, -22.74, -2.58, -1.44)
    m.box("rm-cin-halo-r", R, GLOW, 9.02, 9.06, -20.76, -20.74, -2.58, -1.44)
    glow_light(m, "RM-LT-cin-halo", R, (9.05, -21.75, -1.5), (-1, 0, 0), 1.9, (0, 1, 0), 60)
    glow_light(m, "RM-LT-cin-toe", R, (9.0, -21.75, -2.82), (0, 0, -1), 2.2, (0, 1, 0), 50)
    glow_light(m, "RM-LT-cin-wash", R, (9.12, -21.78, -1.12), (-0.25, 0, -1), 2.2, (0, 1, 0), 150)


def bedroom(m):
    R = "parents-bed"
    m.remove_meshes("detail-headboard-slats")
    m.slats("rm-hb-slat", R, "walnut", "x", 0, 0, 19.10, 21.80, 0.0, 2.62, 0.024, 0.045, 0.03, -26.59, 1)
    m.box("rm-hb-glow-top", R, GLOW, 19.10, 21.80, -26.59, -26.45, 2.62, 2.65)
    glow_light(m, "RM-LT-hb-wash", R, (20.45, -26.5, 2.6), (0, 0.2, -1), 2.7, (1, 0, 0), 200)
    m.box("rm-bed-glow", R, GLOW, 19.62, 21.04, -26.0, -24.7, 0.03, 0.05)
    glow_light(m, "RM-LT-bed-under", R, (20.33, -25.6, 0.06), (0, 0, -1), 1.4, (1, 0, 0), 60)


def dining(m):
    R = "dining-side"
    y = -28.47
    m.box("rm-din-panel", R, "travertine", 15.50, 17.40, y, y + 0.025, -3.0, -0.3, "Gris Fleury taupe wall continuation")
    m.box("rm-din-cove", R, GLOW, 15.50, 17.40, y, y + 0.04, -0.34, -0.31)
    glow_light(m, "RM-LT-din-wash", R, (16.45, y + 0.05, -0.36), (0, 0.25, -1), 1.9, (1, 0, 0), 200)
    for i, x in enumerate((15.66, 17.24)):
        m.box(f"rm-scn-{i}", R, "black-metal", x - 0.05, x + 0.05, y, y + 0.1, -1.75, -1.60)
        glow_light(m, f"RM-LT-scn-up-{i}", R, (x, y + 0.04, -1.58), (0, 0.05, 1), 0.08, (1, 0, 0), 120, width=0.06)
        glow_light(m, f"RM-LT-scn-dn-{i}", R, (x, y + 0.04, -1.77), (0, 0.05, -1), 0.08, (1, 0, 0), 120, width=0.06)
    # replace the single linear pendant by a staggered opal-globe cluster over the table
    m.remove_meshes("lamp-PEN-LIN-dining-01", "lamp-body-PEN-LIN-dining-01", "wire-PEN-LIN-dining-01--1", "wire-PEN-LIN-dining-01-1")
    for i, (dx, dy, zb, r) in enumerate([(-0.6, 0.0, -1.3, 0.08), (-0.3, 0.1, -1.05, 0.08), (0.0, -0.05, -1.35, 0.08),
                                         (0.3, 0.1, -1.1, 0.08), (0.6, 0.0, -1.25, 0.08)]):
        c = (16.95 + dx, -25.9 + dy, zb + r)
        sphere(m, f"rm-dg-{i}", "dining", "rm-glass-globe", c, r)
        sphere(m, f"rm-dgc-{i}", "dining", "rm-opal", c, r * 0.4)
        m.box(f"rm-dgw-{i}", "dining", "rm-cord", c[0] - 0.003, c[0] + 0.003, c[1] - 0.003, c[1] + 0.003, c[2] + r, -0.3)
        glow_light(m, f"RM-LT-dg-{i}", "dining", c, (0, 0, -1), 0.06, (1, 0, 0), 200, width=0.06)


ROOMS = {"living": living, "media": media, "bedroom": bedroom, "dining": dining}

if __name__ == "__main__":
    src, dst, *rooms = sys.argv[1:]
    mk = Mockup.load(src)
    if rooms != ["none"]:
        materials(mk)
        for r in rooms or ROOMS:
            ROOMS[r](mk)
        # Keep the production view->group assignment and re-bind only the transport hash to the edited
        # geometry. The EV of each group is still metered at render time (set-metered), so brightness is
        # comparable with the production render but NOT identical (the new lights are not in the measured lamp population).
        from archpipe.exposure_groups import transport_digest
        mk.s["exposure_groups"]["transport_sha256"] = transport_digest(mk.s)
    mk.save(dst)
    print(dst, len(mk.added), "added")
