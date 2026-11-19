"""World plan for level 6, Halcyon, the Drowned Harbour, on Earth (GAME_ROADMAP.md "Level 6"; Tools/halcyon/README.md
is the contract).

Pure Python (no numpy, no unreal): the terrain generator, the map art, the editor tools, the scenario and the logic
scripts all read their places from here, so a number is typed once. Metres, Unreal axes: x north, y east, z up.

Port Halcyon lies on a bay about 1.1 km long (north-south) and 0.8 km wide. The town climbs south from the water in
one long slope: the Cliff Garden at the top (about 40 m), the High Street, the Signal House and the Clocktower in the
upper town, the Breach (the flooded cut where the sea came through, from wall to wall), the Market Steps, and the
waterfront: the Drowned Quarter in the west (streets under the sea), the Cannery Yards in the east, Lighthouse Point
on the north-east headland. The Mole runs north from the waterfront out to Bastion Halcyon on its rock in the harbour
mouth, inside the ring of the Held Sea. Sea level is z 0.
"""
import math

HALF_X, HALF_Y = 640.0, 480.0     # the height grid's half extents
CELL = 2.0
TILES_X, TILES_Y = 4, 3           # terrain tiles of 320 x 320 m
WATER = 0.0                       # sea level: the bay, the Drowned Quarter and the Breach
SEA_BED = -9.0
RIM = (566.0, 404.0)              # semi-axes of the walkable oval: beyond 0.93 of it the land climbs into cliffs
RIM_START, RIM_END, RIM_RISE = .93, 1.25, 150.0
MAP_HALF = 920.0                  # the pause menu's shared map frame

# ---------------------------------------------------------------- the slope of the town

TOP_X, TOP_Z = -560.0, 40.0       # the Cliff Garden's height
SHORE_X, SHORE_Z = 120.0, 2.6     # the waterfront's quay level, and the line along which land gives way to sea
SHORE_WAVE, SHORE_PERIOD = 18.0, 160.0


def shore_x(y):
    """Where the quays end and the sea begins, along the line y."""
    return SHORE_X + SHORE_WAVE * math.sin(y / SHORE_PERIOD + .8)


def slope_z(x):
    """The town's ground height at x on its long slope (before streets, the Breach and the waterfront)."""
    t = min(max((x - TOP_X) / (SHORE_X - TOP_X), 0.0), 1.0)
    return TOP_Z + (SHORE_Z - TOP_Z) * (t * (1.4 - .4 * t))


# ---------------------------------------------------------------- landmarks (x, y)
GARDEN = (-500.0, 20.0)           # the Cliff Garden: the Divinity current's pool, where she arrives and leaves
GARDEN_STILL = (-484.0, 36.0)
SIGNAL = (-290.0, 0.0)            # the Signal House: Kairos and the Wise
SIGNAL_STILL = (-304.0, -18.0)
CLOCK = (-215.0, 34.0)            # the Clocktower: Trace Reading
BREACH_X, BREACH_WAVE, BREACH_PERIOD = -150.0, 8.0, 95.0   # the Breach's centre line: x = BREACH_X + WAVE * sin(y / PERIOD + .6)
BREACH_FLOOR, BREACH_RIM = 8.0, 13.0                         # half width of its water and of its rims (26 m across)
BREACH_CROSS_Y = 30.0             # the Harbour Bridge (only in the past)
BREACH_STEPS_Y = -260.0           # the steps out of it, up the south side
STEPS = (-70.0, 10.0)             # the Market Steps: Still Point where the ways part
QUARTER = (40.0, -250.0, 92.0, 104.0)   # the Drowned Quarter's flooded ground: centre x, y and semi-axes
QUARTER_STILL = (-24.0, -150.0)
HARBOURMASTER = (60.0, -300.0)    # the first echo, on the harbourmaster's office roof
YARDS = (40.0, 250.0)             # the Cannery Yards
YARDS_STILL = (-4.0, 170.0)
FOREMAN = (80.0, 300.0)           # the second echo, in the crane's cab
POINT = (250.0, 320.0, 36.0, 15.0)   # Lighthouse Point: the headland's centre, the radius of its top and its height
POINT_STILL = (176.0, 240.0)
LIGHTHOUSE = (262.0, 330.0)       # the third echo, at the lamp
MOLE_SOUTH = (shore_x(0.0) - 6.0, 0.0)
BASTION = (440.0, 0.0)            # the Bastion's rock in the harbour mouth: centre and radius below
ROCK_RADIUS = 58.0
HELD_RADIUS = 78.0                # the Held Sea's standing walls
SEA_GATE = (BASTION[0] - HELD_RADIUS, 0.0)
MOLE_STILL = (shore_x(0.0) + 30.0, -10.0)
COURT = (BASTION[0] + 6.0, 0.0)   # the Undertow's chamber, an open court in the Bastion
COURT_RADIUS = 32.0
MOLE_TOP = 3.0                    # the breakwater's walking surface
ROCK_TOP = 3.0
LIBRARY = (-330.0, 272.0)         # optional: the Drowned Library
SEALED_WEAVE = (-420.0, -210.0)   # sealed vaults for abilities learned elsewhere
SEALED_DISSONANCE = (-40.0, 300.0)


def breach_x(y):
    return BREACH_X + BREACH_WAVE * math.sin(y / BREACH_PERIOD + .6)


BRIDGE_SOUTH = (breach_x(BREACH_CROSS_Y) - BREACH_RIM, BREACH_CROSS_Y)
BRIDGE_NORTH = (breach_x(BREACH_CROSS_Y) + BREACH_RIM, BREACH_CROSS_Y)
# Its bed and its water: deep enough to swim in, never to stand in.
BREACH_BED = -6.0

# ---------------------------------------------------------------- regions: name -> (x, y, radius, blend)
REGIONS = {
    'The Cliff Garden': (-500.0, 20.0, 60.0, 30.0),
    'The High Street': (-400.0, 30.0, 70.0, 40.0),
    'The Signal House': (-290.0, 0.0, 60.0, 30.0),
    'The Drowned Library': (-330.0, 272.0, 70.0, 30.0),
    'The Breach': (-150.0, 30.0, 50.0, 30.0),
    'The Market Steps': (-70.0, 10.0, 70.0, 40.0),
    'The Drowned Quarter': (40.0, -250.0, 110.0, 40.0),
    'The Cannery Yards': (40.0, 250.0, 100.0, 40.0),
    'Lighthouse Point': (250.0, 320.0, 60.0, 30.0),
    'The Mole': (260.0, 0.0, 70.0, 30.0),
    'Bastion Halcyon': (440.0, 0.0, 78.0, 20.0),
}

# ---------------------------------------------------------------- streets: (name, kind, half width, points)
# 'road' is paved (setts), 'lane' cobbles, 'path' trodden earth. The generator levels them and keeps scatter off them.
PATHS = (
    ('High Street', 'road', 5.0, ((-492.0, 26.0), (-430.0, 44.0), (-360.0, 22.0), (-300.0, 2.0))),
    ('Clock Lane', 'road', 4.0, ((-282.0, 6.0), (-240.0, 26.0), (-215.0, 34.0), (BRIDGE_SOUTH[0] - 4.0, BREACH_CROSS_Y))),
    ('Harbour Road', 'road', 4.0, ((BRIDGE_NORTH[0] + 4.0, BREACH_CROSS_Y), (-100.0, 22.0), (-70.0, 10.0))),
    ('Mole Road', 'road', 5.0, ((-70.0, 10.0), (0.0, 4.0), (MOLE_SOUTH[0] - 4.0, 0.0))),
    ('Quarter Lane', 'lane', 3.0, ((-70.0, 10.0), (-40.0, -70.0), (-24.0, -150.0))),
    ('Cannery Row', 'lane', 3.5, ((-70.0, 10.0), (-30.0, 90.0), (-4.0, 170.0), (30.0, 230.0))),
    ('Point Path', 'path', 2.5, ((30.0, 230.0), (110.0, 230.0), (176.0, 240.0), (220.0, 290.0))),
    ('Library Lane', 'lane', 2.5, ((-360.0, 22.0), (-370.0, 120.0), (-350.0, 220.0), (-332.0, 262.0))),
)

# Level ground: (x, y, radius, height or None for the slope's own height there).
PADS = (
    (GARDEN[0], GARDEN[1], 28.0, None), (SIGNAL[0], SIGNAL[1], 40.0, None), (CLOCK[0], CLOCK[1], 14.0, None),
    (STEPS[0], STEPS[1], 22.0, None), (QUARTER_STILL[0], QUARTER_STILL[1], 12.0, None), (YARDS_STILL[0], YARDS_STILL[1], 12.0, None),
    (POINT_STILL[0], POINT_STILL[1], 12.0, None), (LIBRARY[0], LIBRARY[1], 30.0, None), (YARDS[0], YARDS[1], 60.0, None),
)

# Where nothing is scattered (x, y, radius): set pieces the scenario stands up.
KEEP_CLEAR = (
    (GARDEN[0], GARDEN[1], 24.0), (GARDEN_STILL[0], GARDEN_STILL[1], 9.0), (SIGNAL[0], SIGNAL[1], 42.0),
    (CLOCK[0], CLOCK[1], 16.0), (BRIDGE_SOUTH[0] - 6.0, BRIDGE_SOUTH[1], 12.0), (BRIDGE_NORTH[0] + 6.0, BRIDGE_NORTH[1], 12.0),
    (STEPS[0], STEPS[1], 18.0), (QUARTER_STILL[0], QUARTER_STILL[1], 12.0), (HARBOURMASTER[0], HARBOURMASTER[1], 20.0),
    (YARDS_STILL[0], YARDS_STILL[1], 10.0), (YARDS[0], YARDS[1], 54.0), (FOREMAN[0], FOREMAN[1], 20.0), (POINT[0], POINT[1], 40.0),
    (POINT_STILL[0], POINT_STILL[1], 10.0), (MOLE_SOUTH[0], MOLE_SOUTH[1], 20.0), (LIBRARY[0], LIBRARY[1], 34.0),
    (SEALED_WEAVE[0], SEALED_WEAVE[1], 12.0), (SEALED_DISSONANCE[0], SEALED_DISSONANCE[1], 12.0),
)
# Where the forced sea has stained the ground magenta (x, y, radius). It fades when the Undertow stops.
SCAR = ((BASTION[0], BASTION[1], 150.0), (breach_x(BREACH_CROSS_Y), BREACH_CROSS_Y, 50.0), (MOLE_SOUTH[0] + 60.0, 0.0, 70.0))


def rim(x, y):
    """How far out of the bay a point is: 1 on the walkable oval's edge."""
    return math.hypot(x / RIM[0], y / RIM[1])


def in_sea(x, y, pad=0.0):
    """North of the waterfront, or in the Drowned Quarter: water (the Bastion's rock and the Mole excepted)."""
    if x > shore_x(y) - pad:
        return not on_mole(x, y, -pad) and not on_spit(x, y, -pad) and math.hypot(x - BASTION[0], y - BASTION[1]) > ROCK_RADIUS + pad and \
            math.hypot(x - POINT[0], y - POINT[1]) > POINT[2] + 14.0 + pad
    cx, cy, ax, ay = QUARTER
    return math.hypot((x - cx) / (ax + pad), (y - cy) / (ay + pad)) < 1.0


def on_spit(x, y, pad=0.0):
    """On the shingle bank the Point Path runs along out to the headland."""
    points = next(pts for name, _, _, pts in PATHS if name == 'Point Path')
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
        if math.hypot(x - ax - t * (bx - ax), y - ay - t * (by - ay)) < 7.0 + pad:
            return True
    return False


def on_mole(x, y, pad=0.0):
    return MOLE_SOUTH[0] - 2.0 < x < SEA_GATE[0] + 4.0 and abs(y) < 5.0 + pad


def in_breach(x, y, pad=0.0):
    return abs(x - breach_x(y)) < BREACH_RIM + pad


def path_segments():
    out = []
    for _name, kind, half, points in PATHS:
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            out.append((ax, ay, bx, by, half, kind))
    return out
