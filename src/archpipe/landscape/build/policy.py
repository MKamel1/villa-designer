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

POND = dict(edge_lip=0.08, coping_h=0.10, grille_bar=0.02, grille_pitch=0.10, grille_top_below_water=0.04, grille_t=0.03, floor_t=0.10, wall_t=0.10)
# POND: section figures (slope 1:4, shelf, trench, freeboard) come from the layout `section`; these are only construction details, ASSUMED:
# 80 mm contrasting flush lip on a 100 mm coping, 100 mm walls and floor outside the water, grille bars 20 x 30 mm at 100 mm.
PIT = dict(cover_base_t=0.006, hole=0.80, liner_t=0.04, depth=0.50, cover_t=0.046, gap=0.003, flame_h=0.35)   # ASSUMED; cover lip from the layout
POT = dict(h=0.55, r_bottom=0.20, wall=0.03, soil_below_rim=0.05, plant_h=1.8)   # ASSUMED terracotta pot; potted frangipani size is a GAP
BBQ = dict(bowl_z0=0.55, bowl_z1=0.80)  # ASSUMED portable kettle BBQ on a stand

AGE_YEARS = 3
FRAC_FLOOR = 0.25          # policy: size fraction at planting
YEARS_TO_MATURE = {"fast": 5.0, "moderate": 8.0, "slow": 15.0, None: 8.0}   # ASSUMED from the sourced growth-rate class; no growth curve is held
YEARS_SMALL_FORMS = 3.0    # ASSUMED for ground cover / herbs / perennials / grasses
SMALL_FORMS = ("ground_cover", "herb", "perennial", "grass")
FOLIAGE_DEFAULT = (0.22, 0.42, 0.16)

ROOT_BARRIER = dict(depth=0.90, t=0.004, clear=0.15, above=0.0)   # ASSUMED: 0.9 m deep 4 mm HDPE-type sheet in a ring, top flush with the ground; no published depth is claimed
TREE_CLEAR_STEM = 0.35     # ASSUMED: a pruned umbrella canopy is clear of branches below this fraction of its height
CLIMBER = dict(reach=0.75, panel_t=0.03, lift=0.02, width_per_height=1.0, min_w=0.8)   # ASSUMED leaf panel: 30 mm thick, 20 mm off the face, width ~ height at age
