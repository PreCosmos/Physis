"""World plan for level 5, Arche, the First Ones' Planet: Kathodos, the city of the Descent (GAME_ROADMAP.md
"Level 5"; Tools/arche/README.md is the contract).

Pure Python (no numpy, no unreal): the terrain generator, the map art, the editor tools, the scenario and the logic
scripts all read their places from here, so a number is typed once. Metres, Unreal axes: x north, y east, z up.

Kathodos lies in an oval basin about 1.1 km long (north-south) and 0.8 km wide, walled by cliffs. It climbs north in
three tiers of 12 m: the Lower Tier (south, cut across by the Great Chasm), the Middle Tier and the Upper Tier, where
the Lens Court stands. Physis arrives at the Landing in the south and climbs: the Processional, the Hearthold (the
Serene's refuge, Aeon), the First Arch (Reweave), the Sundered Span over the Chasm, the Concourse, the First Stair to
the Middle Tier, then the three Mirrors (the Cisterns in the west, the Crystal Garden in the east, the Galleries'
mesa on the Upper Tier), the Second Stair, the Veil in the Lens Court's wall, and the Lens.
"""
import math

HALF_X, HALF_Y = 640.0, 480.0     # the height grid's half extents
CELL = 2.0
TILES_X, TILES_Y = 4, 3           # terrain tiles of 320 x 320 m
WATER = 0.0                       # the Cisterns' surface: the only water deep enough to swim in
RIM = (566.0, 404.0)              # semi-axes of the walkable oval: beyond 0.93 of it the land climbs into cliffs
RIM_START, RIM_END, RIM_RISE = .93, 1.25, 260.0
MAP_HALF = 920.0                  # the pause menu's shared map frame

# ---------------------------------------------------------------- the tiers
TIER = (8.0, 20.0, 32.0)          # ground level of the Lower, Middle and Upper Tier
TIER_RISE = 12.0
TIER2_X, TIER3_X = 90.0, 270.0    # the foot of each riser on the centre line (y 0)
TIER_WAVE, TIER_PERIOD = 7.0, 110.0
RISER = 3.0                       # horizontal run of a riser: far too steep to climb


def tier2_x(y):
    return TIER2_X + TIER_WAVE * math.sin(y / TIER_PERIOD + .4)


def tier3_x(y):
    return TIER3_X + TIER_WAVE * math.sin(y / TIER_PERIOD + 2.1)


# ---------------------------------------------------------------- landmarks (x, y)
LANDING = (-500.0, 20.0)          # the Divinity current's pool: where she arrives and leaves
LANDING_STILL = (-484.0, 36.0)
HEARTHOLD = (-290.0, 0.0)         # the Serene's refuge: Aeon, the keepers
HEARTHOLD_STILL = (-304.0, -18.0)
FIRST_ARCH = (-215.0, 30.0)       # where Aeon shows her how a thing remembers its shape: Reweave
CHASM_X, CHASM_WAVE, CHASM_PERIOD = -150.0, 10.0, 90.0   # the Great Chasm's centre line: x = CHASM_X + WAVE * sin(y / PERIOD + .6)
CHASM_FLOOR, CHASM_RIM, CHASM_DEPTH = 9.0, 13.0, 40.0    # half width of its floor and of its rims, and its depth
CHASM_CROSS_Y = 30.0              # the Sundered Span
CHASM_RAMP_Y = -320.0             # its only way out, up the south side
CONCOURSE = (-70.0, 10.0)         # the Lower Tier's Still Point north of the Chasm: the ways part here
STAIR1 = (TIER2_X + TIER_WAVE * math.sin(.4), 0.0)       # the First Stair's foot of riser (Lower to Middle Tier)
MIDDLE_STILL = (128.0, 10.0)
STAIR2 = (TIER3_X + TIER_WAVE * math.sin(2.1), 0.0)      # the Second Stair (Middle to Upper Tier)
UPPER_STILL = (296.0, 14.0)
CISTERNS = (20.0, -255.0, 78.0, 86.0)   # the Cisterns' water: centre x, y and semi-axes
CISTERN_BED = -5.0
CISTERN_ISLE = (20.0, -205.0, 13.0)      # the Mirror's island, near the east shore: centre and radius of its flat top (TIER[0] + 1)
CISTERN_SHORE = (14.0, -150.0)          # Still Point on the east shore
GARDEN = (170.0, 250.0)           # the Crystal Garden, on the Middle Tier
GARDEN_STILL = (140.0, 196.0)
PINNACLE = (188.0, 282.0, 9.0, 12.0)    # the Garden's Mirror: centre, radius of the flat top, height above the tier
MESA = (345.0, 262.0, 14.0, 18.0)       # the Galleries' mesa on the Upper Tier: centre, top radius, height above the tier
GALLERY_STILL = (310.0, 214.0)
COURT = (400.0, 0.0)              # the Lens Court's centre; its ring wall's radius below
COURT_WALL = 76.0
ARENA_RADIUS = 30.0
LENS = (452.0, 0.0)               # the Sundering Lens, at the Court's north side
OSSUARY = (-330.0, 272.0)         # optional: the Ossuary of Names
SEALED_TRACE = (-420.0, -210.0)   # sealed vaults for abilities learned elsewhere
SEALED_DISSONANCE = (150.0, -120.0)


def ring_point(bearing, radius, centre=COURT):
    a = math.radians(bearing)
    return (centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius)


GATE = ring_point(180.0, COURT_WALL)                 # the Veil, in the wall's south side
COURT_STILL = ring_point(180.0, COURT_WALL - 12.0)   # just inside it
MIRRORS = {'west': (CISTERN_ISLE[0], CISTERN_ISLE[1]), 'east': (PINNACLE[0], PINNACLE[1]), 'north': (MESA[0], MESA[1])}


def chasm_x(y):
    return CHASM_X + CHASM_WAVE * math.sin(y / CHASM_PERIOD + .6)


SPAN_SOUTH = (chasm_x(CHASM_CROSS_Y) - CHASM_RIM, CHASM_CROSS_Y)
SPAN_NORTH = (chasm_x(CHASM_CROSS_Y) + CHASM_RIM, CHASM_CROSS_Y)

# ---------------------------------------------------------------- regions: name -> (x, y, radius, blend)
REGIONS = {
    'The Landing': (-500.0, 20.0, 60.0, 30.0),
    'The Processional': (-400.0, 30.0, 70.0, 40.0),
    'The Hearthold': (-290.0, 0.0, 60.0, 30.0),
    'The Ossuary': (-330.0, 272.0, 70.0, 30.0),
    'The Great Chasm': (-150.0, 30.0, 50.0, 30.0),
    'The Concourse': (-70.0, 10.0, 70.0, 40.0),
    'The Cisterns': (20.0, -255.0, 110.0, 40.0),
    'The Middle Tier': (150.0, 0.0, 70.0, 40.0),
    'The Crystal Garden': (170.0, 250.0, 100.0, 40.0),
    'The Galleries': (335.0, 250.0, 70.0, 30.0),
    'The Lens Court': (400.0, 0.0, 76.0, 20.0),
}

# ---------------------------------------------------------------- paths: (name, kind, half width, points)
# 'road' is paved (pale flagstones), 'trail' trodden dust. The generator levels them and keeps scatter off them.
PATHS = (
    ('Processional', 'road', 5.0, ((-492.0, 26.0), (-430.0, 44.0), (-360.0, 22.0), (-300.0, 2.0))),
    ('Arch Way', 'road', 4.0, ((-282.0, 6.0), (-240.0, 24.0), (-215.0, 30.0), (SPAN_SOUTH[0] - 4.0, CHASM_CROSS_Y))),
    ('Span Way', 'road', 4.0, ((SPAN_NORTH[0] + 4.0, CHASM_CROSS_Y), (-100.0, 22.0), (-70.0, 10.0))),
    ('Stair Way', 'road', 4.5, ((-70.0, 10.0), (0.0, 4.0), (STAIR1[0] - 18.0, 0.0))),
    ('Cistern Way', 'trail', 2.5, ((-70.0, 10.0), (-40.0, -70.0), (0.0, -130.0), (14.0, -150.0))),
    ('Middle Way', 'road', 4.5, ((STAIR1[0] + 6.0, 0.0), (128.0, 6.0), (200.0, 2.0), (STAIR2[0] - 18.0, 0.0))),
    ('Garden Way', 'trail', 2.5, ((128.0, 10.0), (140.0, 100.0), (140.0, 196.0), (170.0, 240.0))),
    ('Upper Way', 'road', 4.5, ((STAIR2[0] + 6.0, 0.0), (300.0, 2.0), (GATE[0] - 4.0, 0.0))),
    ('Gallery Way', 'trail', 2.5, ((296.0, 14.0), (300.0, 110.0), (310.0, 214.0), (328.0, 244.0))),
    ('Ossuary Way', 'trail', 2.5, ((-360.0, 22.0), (-370.0, 120.0), (-350.0, 220.0), (-332.0, 262.0))),
)

# Level ground: (x, y, radius, height or None for the tier's own height there).
PADS = (
    (LANDING[0], LANDING[1], 28.0, None), (HEARTHOLD[0], HEARTHOLD[1], 42.0, None), (FIRST_ARCH[0], FIRST_ARCH[1], 14.0, None),
    (CONCOURSE[0], CONCOURSE[1], 20.0, None), (MIDDLE_STILL[0], MIDDLE_STILL[1], 16.0, None), (UPPER_STILL[0], UPPER_STILL[1], 16.0, None),
    (CISTERN_SHORE[0], CISTERN_SHORE[1], 12.0, None), (GARDEN_STILL[0], GARDEN_STILL[1], 12.0, None),
    (GALLERY_STILL[0], GALLERY_STILL[1], 12.0, None), (COURT[0], COURT[1], COURT_WALL + 6.0, None), (OSSUARY[0], OSSUARY[1], 30.0, None),
    (STAIR1[0] - 12.0, 0.0, 14.0, None), (STAIR1[0] + 10.0, 0.0, 10.0, None), (STAIR2[0] - 12.0, 0.0, 14.0, None),
    (STAIR2[0] + 10.0, 0.0, 10.0, None),
)

# Where nothing is scattered (x, y, radius): set pieces the scenario stands up.
KEEP_CLEAR = (
    (LANDING[0], LANDING[1], 22.0), (LANDING_STILL[0], LANDING_STILL[1], 9.0), (HEARTHOLD[0], HEARTHOLD[1], 44.0),
    (FIRST_ARCH[0], FIRST_ARCH[1], 14.0), (SPAN_SOUTH[0] - 6.0, SPAN_SOUTH[1], 12.0), (SPAN_NORTH[0] + 6.0, SPAN_NORTH[1], 12.0),
    (CONCOURSE[0], CONCOURSE[1], 16.0), (STAIR1[0], 0.0, 26.0), (STAIR2[0], 0.0, 26.0), (MIDDLE_STILL[0], MIDDLE_STILL[1], 12.0),
    (UPPER_STILL[0], UPPER_STILL[1], 12.0), (CISTERN_SHORE[0], CISTERN_SHORE[1], 12.0), (CISTERN_ISLE[0], CISTERN_ISLE[1], 16.0),
    (GARDEN_STILL[0], GARDEN_STILL[1], 10.0), (PINNACLE[0], PINNACLE[1], 22.0), (MESA[0], MESA[1], 30.0),
    (GALLERY_STILL[0], GALLERY_STILL[1], 10.0), (COURT[0], COURT[1], COURT_WALL + 10.0), (OSSUARY[0], OSSUARY[1], 28.0),
    (SEALED_TRACE[0], SEALED_TRACE[1], 12.0), (SEALED_DISSONANCE[0], SEALED_DISSONANCE[1], 12.0),
)
# Where the unweaving shows: scorched, violet-veined ground (x, y, radius). It fades when the Lens goes dark.
SCAR = ((COURT[0], COURT[1], 150.0), (chasm_x(CHASM_CROSS_Y), CHASM_CROSS_Y, 60.0), (STAIR1[0], 0.0, 40.0), (STAIR2[0], 0.0, 40.0),
        (GARDEN[0], GARDEN[1], 50.0))


def rim(x, y):
    """How far out of the basin a point is: 1 on the walkable oval's edge."""
    return math.hypot(x / RIM[0], y / RIM[1])


def tier_of(x, y):
    """0, 1 or 2: the tier a point stands on (ignoring the risers' 3 m)."""
    return (1 if x > tier2_x(y) else 0) + (1 if x > tier3_x(y) else 0)


def in_water(x, y, pad=0.0):
    cx, cy, ax, ay = CISTERNS
    return math.hypot((x - cx) / (ax + pad), (y - cy) / (ay + pad)) < 1.0


def in_chasm(x, y, pad=0.0):
    return abs(x - chasm_x(y)) < CHASM_RIM + pad


def on_riser(x, y, pad=4.0):
    return abs(x - tier2_x(y) - RISER / 2) < RISER / 2 + pad or abs(x - tier3_x(y) - RISER / 2) < RISER / 2 + pad


def path_segments():
    out = []
    for _name, kind, half, points in PATHS:
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            out.append((ax, ay, bx, by, half, kind))
    return out
