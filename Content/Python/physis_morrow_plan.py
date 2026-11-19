"""World plan for level 8, Morrow, the Valley Before Morning, on Earth (GAME_ROADMAP.md "Level 8"; Tools/morrow/README.md
is the contract).

Pure Python (no numpy, no unreal): the terrain generator, the map art, the editor tools, the scenario and the logic
scripts all read their places from here, so a number is typed once. Metres, Unreal axes: x north, y east, z up.

Morrow lies in a mountain valley about 1.1 km long (north-south) and 0.8 km wide, walled by peaks. The road comes in
over the south pass at the Pass Chapel (about 46 m), drops to the Mill House and its frozen pond, and crosses the
Gorge, the river's frozen cut from wall to wall, on the Ferry Bridge. North of it the town: Chapel Square, the
Schoolhouse in the west, the Glider Field on its bench in the east, the Telegraph House on its rock in the north-east.
The valley floor climbs gently north to the foot of Morrow Dam, an earth embankment whose stair climbs to the crest
(84 m) and the Hold; behind it the frozen reservoir lies among the peaks.

The Morning, Maren's mind (the Inner Installation), is built in the same level, an island in the mist 1.6 km north of
the dam, behind the peaks: its rooms stand in a row along x.
"""
import math

HALF_X, HALF_Y = 640.0, 480.0     # the height grid's half extents
CELL = 2.0
TILES_X, TILES_Y = 4, 3           # terrain tiles of 320 x 320 m
RIM = (566.0, 404.0)              # semi-axes of the walkable oval: beyond 0.93 of it the land climbs into peaks
RIM_START, RIM_END, RIM_RISE = .93, 1.25, 170.0
MAP_HALF = 920.0                  # the pause menu's shared map frame

# ---------------------------------------------------------------- the valley floor and the dam

PASS_X, PASS_Z = -560.0, 46.0     # the south pass
MILL_Z = 22.0                     # the valley floor at the Mill House
TOWN_Z = 18.0                     # at the Gorge
FOOT_X, FOOT_Z = 300.0, 32.0      # the dam's foot (its apron)
CREST_X0, CREST_X1, CREST_Z = 420.0, 436.0, 84.0   # the crest: from its downstream to its upstream edge, its top
ICE_Z = 80.0                      # the reservoir's frozen surface
LAKE_BED = 70.0


def floor_z(x):
    """The valley floor's height at x (before streets, the Gorge, the pads and the dam's embankment)."""
    pts = ((PASS_X, PASS_Z), (-300.0, MILL_Z), (-150.0, TOWN_Z), (250.0, 30.0), (FOOT_X, FOOT_Z))
    if x <= pts[0][0]:
        return PASS_Z + (pts[0][0] - x) * .05
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        if x <= bx:
            t = (x - ax) / (bx - ax)
            t = t * t * (3 - 2 * t)
            return az + (bz - az) * t
    return FOOT_Z


def dam_z(x):
    """The embankment and the crest: rises from the foot to the crest; past the crest the reservoir (its bed)."""
    if x <= FOOT_X:
        return None
    if x < CREST_X0:
        return FOOT_Z + (CREST_Z - FOOT_Z) * (x - FOOT_X) / (CREST_X0 - FOOT_X)
    if x <= CREST_X1:
        return CREST_Z
    return LAKE_BED


# ---------------------------------------------------------------- landmarks (x, y)
CHAPEL = (-500.0, 0.0)            # the Pass Chapel: the Divinity current's pool, where she arrives and leaves
CHAPEL_STILL = (-484.0, 16.0)
MILL = (-290.0, -20.0)            # the Mill House: Edda, Corin and Pilgrim
MILL_STILL = (-304.0, -38.0)
POND = (-292.0, -60.0, 18.0)      # the millpond, west of the Mill House: centre and radius (frozen)
WHEEL = (-289.0, -35.6)           # the mill wheel on the house's west wall (its axle), and the miller Stilled beside it
MILLER = (-283.0, -39.0)
BENCH = (-272.0, -64.0)           # Edda's bench, on the pond's east bank: Sit With is taught here
GORGE_X, GORGE_WAVE, GORGE_PERIOD = -150.0, 8.0, 95.0   # the Gorge's centre line: x = GORGE_X + WAVE * sin(y / PERIOD + .6)
GORGE_FLOOR, GORGE_RIM = 8.0, 13.0                       # half width of its ice and of its rims (26 m across)
GORGE_BED = 6.0                   # its frozen floor's height
GORGE_CROSS_Y = 20.0              # the Ferry Bridge
GORGE_RAMP_Y = -260.0             # the ramp out of it, up the south side
SQUARE = (-70.0, 0.0)             # Chapel Square: Still Point where the ways part
SCHOOL = (40.0, -250.0)           # the Schoolhouse; Ada Fenn at its window
SCHOOL_STILL = (-24.0, -150.0)
FIELD = (40.0, 262.0)             # the Glider Field: its bench's centre
FIELD_RADIUS, FIELD_LIFT = 64.0, 8.0   # its radius and how far it stands above the valley floor
FIELD_STILL = (-4.0, 170.0)
ROCK = (250.0, 320.0, 30.0, 30.0)   # the Telegraph House's rock: centre, the radius of its top, its height above the floor
ROCK_STILL = (176.0, 240.0)
TELEGRAPH = (256.0, 328.0)        # the Telegraph House on the rock; Ines Okon at her key
STAIR_FOOT = (FOOT_X - 30.0, 0.0)  # the Dam Stair, from the apron up the embankment to the crest
STAIR_STILL = (240.0, -16.0)
STAIR_HALF = 5.0                  # the stair's half width
CREST = (428.0, 0.0)              # the crest; Maren Stilled on it, the Hold beside her
MAREN = (428.0, 14.0)
HOLD = (430.0, -46.0)             # the Hold: the intake tower on the crest
CREST_STILL = (428.0, 60.0)
ICEHOUSE = (-330.0, 272.0)        # optional: the Ice House
SEALED_TRACE = (-420.0, -210.0)   # sealed vaults for abilities learned elsewhere
SEALED_DISSONANCE = (-40.0, 300.0)

# ---------------------------------------------------------------- the Morning (Maren's mind)

INNER_Z = 150.0                   # the island's floor
INNER_KILL_Z = 60.0               # below this she has fallen off: back to the Morning's Still Point
KITCHEN = (1500.0, 0.0)           # the house: its kitchen (her way in; the Morning's Still Point)
KITCHEN_HALF = (7.0, 6.0, 3.0)    # half extents of its room (x, y) and its height
HALL = (1535.3, 0.0)             # the Long Hall: a corridor 56 m long along x, from the kitchen's door
HALL_HALF = (28.0, 2.4, 3.2)
FIELD_IN = (1610.0, 0.0, 44.0)    # the Field as she remembers it: centre and radius
CREST_IN = (1716.0, 0.0, 32.0)    # the Crest as she remembers it, where the Unrisen waits: centre and radius
INNER_STILL = (1497.0, -2.0)

# ---------------------------------------------------------------- regions: name -> (x, y, radius, blend)
REGIONS = {
    'The Pass Chapel': (-500.0, 0.0, 60.0, 30.0),
    'The Orchard Road': (-400.0, 10.0, 70.0, 40.0),
    'The Mill House': (-280.0, -30.0, 60.0, 30.0),
    'The Ice House': (-330.0, 272.0, 70.0, 30.0),
    'The Gorge': (-150.0, 20.0, 50.0, 30.0),
    'Chapel Square': (-70.0, 0.0, 70.0, 40.0),
    'The Schoolhouse': (40.0, -250.0, 100.0, 40.0),
    'The Glider Field': (40.0, 262.0, 90.0, 40.0),
    'The Telegraph House': (250.0, 320.0, 60.0, 30.0),
    'The Dam Stair': (330.0, 0.0, 70.0, 30.0),
    'The Crest': (428.0, 0.0, 70.0, 20.0),
}

# ---------------------------------------------------------------- streets: (name, kind, half width, points)
# 'road' is paved, 'lane' cobbles, 'path' trodden earth. The generator levels them and keeps scatter off them.
PATHS = (
    ('Orchard Road', 'road', 4.5, ((-492.0, 8.0), (-430.0, 24.0), (-360.0, 4.0), (-300.0, -18.0))),
    ('Mill Lane', 'lane', 3.0, ((-282.0, -14.0), (-240.0, -30.0), (-215.0, -40.0), (-190.0, -20.0), (-170.0, GORGE_CROSS_Y))),
    ('Ferry Road', 'road', 4.0, ((-130.0, GORGE_CROSS_Y), (-100.0, 12.0), (-70.0, 0.0))),
    ('Dam Road', 'road', 5.0, ((-70.0, 0.0), (0.0, -4.0), (120.0, 0.0), (240.0, 0.0), (STAIR_FOOT[0], 0.0))),
    ('School Lane', 'lane', 3.0, ((-70.0, 0.0), (-40.0, -70.0), (-24.0, -150.0), (30.0, -214.0), (64.0, -236.0))),
    ('Field Lane', 'lane', 3.5, ((-70.0, 0.0), (-30.0, 90.0), (-4.0, 170.0), (14.0, 206.0))),
    ('Telegraph Path', 'path', 2.5, ((86.0, 262.0), (150.0, 246.0), (176.0, 240.0), (222.0, 292.0))),
    ('Ice House Lane', 'lane', 2.5, ((-360.0, 4.0), (-370.0, 120.0), (-350.0, 220.0), (-334.0, 256.0))),
)

# Level ground: (x, y, radius, height or None for the floor's own height there).
PADS = (
    (CHAPEL[0], CHAPEL[1], 28.0, None), (MILL[0], MILL[1], 34.0, None), (BENCH[0], BENCH[1], 12.0, None),
    (SQUARE[0], SQUARE[1], 24.0, None), (SCHOOL_STILL[0], SCHOOL_STILL[1], 12.0, None), (FIELD_STILL[0], FIELD_STILL[1], 12.0, None),
    (ROCK_STILL[0], ROCK_STILL[1], 12.0, None), (ICEHOUSE[0], ICEHOUSE[1], 30.0, None), (SCHOOL[0], SCHOOL[1], 46.0, None),
    (STAIR_STILL[0], STAIR_STILL[1], 12.0, None),
)

# Where nothing is scattered (x, y, radius): set pieces the scenario stands up.
KEEP_CLEAR = (
    (CHAPEL[0], CHAPEL[1], 24.0), (CHAPEL_STILL[0], CHAPEL_STILL[1], 9.0), (MILL[0], MILL[1], 36.0), (POND[0], POND[1], POND[2] + 6.0),
    (BENCH[0], BENCH[1], 12.0), (WHEEL[0], WHEEL[1], 10.0), (SQUARE[0], SQUARE[1], 22.0), (SCHOOL_STILL[0], SCHOOL_STILL[1], 12.0),
    (SCHOOL[0], SCHOOL[1], 50.0), (FIELD_STILL[0], FIELD_STILL[1], 10.0), (FIELD[0], FIELD[1], FIELD_RADIUS + 4.0),
    (ROCK[0], ROCK[1], 44.0), (ROCK_STILL[0], ROCK_STILL[1], 10.0), (ICEHOUSE[0], ICEHOUSE[1], 34.0),
    (SEALED_TRACE[0], SEALED_TRACE[1], 12.0), (SEALED_DISSONANCE[0], SEALED_DISSONANCE[1], 12.0), (STAIR_STILL[0], STAIR_STILL[1], 10.0),
)
# Where the Rime is thickest (x, y, radius): the ground is frosted magenta-white; it clears when the Lull stops.
SCAR = ((CREST[0], CREST[1], 170.0), (GORGE_X, GORGE_CROSS_Y, 50.0), (SCHOOL[0], SCHOOL[1], 60.0), (POND[0], POND[1], 34.0))


def rim(x, y):
    """How far out of the valley a point is: 1 on the walkable oval's edge."""
    return math.hypot(x / RIM[0], y / RIM[1])


def gorge_x(y):
    return GORGE_X + GORGE_WAVE * math.sin(y / GORGE_PERIOD + .6)


def in_gorge(x, y, pad=0.0):
    return abs(x - gorge_x(y)) < GORGE_RIM + pad


def in_pond(x, y, pad=0.0):
    return math.hypot(x - POND[0], y - POND[1]) < POND[2] + pad


def on_dam(x, y, pad=0.0):
    """On the embankment's face, the crest or the reservoir (north of the dam's foot)."""
    return x > FOOT_X - pad


def in_lake(x, y, pad=0.0):
    return x > CREST_X1 + pad


BRIDGE_SOUTH = (gorge_x(GORGE_CROSS_Y) - GORGE_RIM, GORGE_CROSS_Y)
BRIDGE_NORTH = (gorge_x(GORGE_CROSS_Y) + GORGE_RIM, GORGE_CROSS_Y)
KEEPER = (BRIDGE_SOUTH[0] - 6.0, GORGE_CROSS_Y - 6.0)   # the bridge keeper, Stilled at the bridge's south head


def path_segments():
    out = []
    for _name, kind, half, points in PATHS:
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            out.append((ax, ay, bx, by, half, kind))
    return out
