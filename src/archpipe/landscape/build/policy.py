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

POND = dict(shelf_w=0.25, shelf_below_water=0.15, edge_lip=0.08, lip_t=0.04, grille_bar=0.02, grille_pitch=0.10,
            grille_top_below_water=0.04, floor_t=0.10, wall_t=0.10)  # ASSUMED; the safety-shelf width is GAP-POND-EDGE-SAFETY
PIT = dict(hole=0.80, liner_t=0.04, depth=0.50, cover_t=0.046, gap=0.003, flame_h=0.35)   # ASSUMED; cover lip from the layout
POT = dict(h=0.55, r_bottom=0.20, wall=0.03, soil_below_rim=0.05, plant_h=1.8)   # ASSUMED terracotta pot; potted frangipani size is a GAP
BBQ = dict(bowl_z0=0.55, bowl_z1=0.80)  # ASSUMED portable kettle BBQ on a stand

AGE_YEARS = 3
FRAC_FLOOR = 0.25          # policy: size fraction at planting
YEARS_TO_MATURE = {"fast": 5.0, "moderate": 8.0, "slow": 15.0, None: 8.0}   # ASSUMED from the sourced growth-rate class; no growth curve is held
YEARS_SMALL_FORMS = 3.0    # ASSUMED for ground cover / herbs / perennials / grasses
SMALL_FORMS = ("ground_cover", "herb", "perennial", "grass")
FOLIAGE_DEFAULT = (0.22, 0.42, 0.16)
