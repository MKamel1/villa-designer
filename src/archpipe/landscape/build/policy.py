"""Every dimension the build had to choose, in one place, each stated as ASSUMED (ours) or taken from the layout.

The layout (landscape-layout/1) fixes plan footprints, heights of pergolas / walls / screens, seat-wall height and the pond and
fire-pit specification. It does NOT fix construction detail. The values below are our choices for a PREVIEW; none is a published
standard and none may be quoted as one. Sizes of structure sections are for how the thing looks, not for structural design.
"""

GROUND_Z = -3.0            # model frame: the garden level (LDG: "one level, z -3.0"; concepts/villa_landscape.GROUND)
BUILDING_H = 6.0           # ASSUMED context-box height of the house (footprints carry none; same figure as LDC massing)

PAVER = dict(len=0.60, wid=0.30, thick=0.04, joint=0.008, bedding=0.06)   # ASSUMED; 0.6 x 0.3 running bond as the LDC plan style
GRAVEL_DEPTH = 0.05
BED_DEPTH = 0.05

POST = 0.10                # ASSUMED pergola post 100 x 100 (aluminium)
BEAM = (0.06, 0.20)        # ASSUMED beam width x depth
LOUVRE = dict(width=0.12, thick=0.02, pitch=0.16, tilt=35.0)   # ASSUMED fixed louvre blades
SCREEN_POST = (0.12, 0.10)  # ASSUMED trellis post (along, across)
SCREEN_BATTEN = 0.025
SCREEN_PITCH = 0.15
WALL_NOTE = "height from the layout (the LDS fence figure); construction not specified, shown as rendered masonry"

TABLE = dict(h=0.75, top=0.04, leg=0.06, inset=0.12)           # ASSUMED generic table
CHAIR = dict(seat=0.44, seat_h=0.45, back_h=0.88, off=0.30)    # ASSUMED generic chair, off = table edge to seat centre
SEAT_TOP = 0.05            # ASSUMED timber seat on the masonry seat wall (seat-wall height from the layout)

POND = dict(edge_lip=0.08, coping_h=0.10, grille_bar=0.006, grille_pitch=0.05, grille_top_below_water=0.04, grille_t=0.006, floor_t=0.10, wall_t=0.10)
# POND: section figures (slope 1:4, shelf, trench, freeboard) come from the layout `section`; these are only construction details, ASSUMED:
# 80 mm contrasting flush lip on a 100 mm coping, 100 mm walls and floor outside the water. Grille = welded mesh of 6 x 6 mm bars at 50 mm pitch (44 mm clear aperture), dark finish.
# POLICY, not a standard: the held sources say only 'rigid metal grille' (RoSPA, W-rospa-rigid-grille) and 'strong mesh ... carry a child' (Mid and West Wales FRS, W-pond-mawwfire-grille); neither gives an aperture, wire
# section or load (GAP-POND-GRILLE-LOAD). 50 mm is ours: fine enough to read as mesh and to stop a hand and a koi net, coarse enough to see the koi through. The supplier certifies the real mesh.
PIT = dict(cover_base_t=0.006, hole=0.80, liner_t=0.04, depth=0.50, cover_t=0.046, gap=0.003, flame_h=0.35)   # ASSUMED; cover lip from the layout
POT = dict(h=0.55, r_bottom=0.20, wall=0.03, soil_below_rim=0.0, plant_h=1.8)   # ASSUMED terracotta pot; potted frangipani size is a GAP
BBQ = dict(bowl_z0=0.55, bowl_z1=0.80, h=0.95)  # ASSUMED portable kettle BBQ on a stand

AGE_YEARS = 3
FRAC_FLOOR = 0.25          # policy: size fraction at planting
YEARS_TO_MATURE = {"fast": 5.0, "moderate": 8.0, "slow": 15.0, None: 8.0}   # ASSUMED from the sourced growth-rate class; no growth curve is held
YEARS_SMALL_FORMS = 3.0    # ASSUMED for ground cover / herbs / perennials / grasses
SMALL_FORMS = ("ground_cover", "herb", "perennial", "grass")
FOLIAGE_DEFAULT = (0.22, 0.42, 0.16)

ROOT_BARRIER = dict(depth=0.90, t=0.004, clear=0.15, above=0.0)   # ASSUMED: 0.9 m deep 4 mm HDPE-type sheet in a ring, top flush with the ground; no published depth is claimed
TREE_CLEAR_STEM = 0.35     # ASSUMED: a pruned umbrella canopy is clear of branches below this fraction of its height
CLIMBER = dict(reach=0.75, panel_t=0.03, lift=0.02, width_per_height=1.0, min_w=0.8)   # ASSUMED leaf panel: 30 mm thick, 20 mm off the face, width ~ height at age

# --- production integration (lane GI) ---
STAR_JASMINE_MIN_FROM_SEAT = 2.0   # POLICY: client 2026-11-22 puts star jasmine (irritant sap) AWAY from the seats and herbs; Arabian jasmine stays by them. 2.0 m = beyond sitting and arm's reach (ours, not a standard)
COPING = dict(thick=0.06, overhang=0.04)            # ASSUMED precast/stone cap on a rendered wall: 60 mm thick, 40 mm drip overhang each side
EDGING = dict(t=0.004, below=0.06, above=0.015)     # ASSUMED 4 mm steel bed edging: 15 mm proud of the ground, 60 mm in
SEAT_SLAT = dict(w=0.07, gap=0.012, overhang=0.015)   # ASSUMED hardwood seat slats, 70 mm with 12 mm gaps, along the bench
LEAF_CARD = dict(per_m2=520, depth=(0.015, 0.20), stems_per_m=1.6, stem_r=(0.004, 0.0065))   # ASSUMED leaf-card density (cards per m2 of climbed face), depth off the face, main stems per metre of panel width
STAR_JASMINE_ATLAS = dict(id="fab_star_jasmine_trellis", folder="star_jasmine_pjycl2_4k", prefix="Star_Jasmine_pjycl2_4K", scan_m=0.79)   # LDL pass 6: Megascans star jasmine, 20 real leaf cut-outs of 4-12 cm
