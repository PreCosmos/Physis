"""World plan for level 7, Hesper, the City of One Voice, on Arche (GAME_ROADMAP.md "Level 7"; Tools/hesper/README.md is
the contract).

Pure Python (no numpy, no unreal): the terrain generator, the map art, the editor tools, the scenario and the logic
scripts all read their places from here, so a number is typed once. Metres, Unreal axes: x north, y east, z up.

Hesper stands on a high plateau about 1.1 km long (north-south) and 0.8 km wide, on the line between Arche's day and
night. The sun sits on the western horizon for ever, so the plateau's west side is an edge, not a wall: the ground
falls away there into a haze two hundred metres deep, and the low sun comes in over it. The other sides climb into
cliffs. The ground rises gently north from the Sunward Stair (about 20 m) to the Concord (about 44 m). The Choir Wall,
a standing wall of Unison, crosses the plateau at x -150 from the edge to the east cliffs.
"""
import math

HALF_X, HALF_Y = 640.0, 480.0     # the height grid's half extents
CELL = 2.0
TILES_X, TILES_Y = 4, 3           # terrain tiles of 320 x 320 m
WATER = 0.0                       # unused: Hesper's pools are sheets at their own heights (POOLS)
RIM = (566.0, 404.0)              # semi-axes of the walkable oval: beyond 0.93 of it the land climbs into cliffs (or, west, falls)
RIM_START, RIM_END, RIM_RISE = .93, 1.25, 170.0
DROP = 240.0                      # how far the ground falls beyond the western edge
MAP_HALF = 920.0                  # the pause menu's shared map frame

# ---------------------------------------------------------------- the ground

SOUTH_X, SOUTH_Z = -560.0, 20.0   # the Sunward Stair's height
NORTH_X, NORTH_Z = 470.0, 44.0    # the Concord's dais


def rise_z(x):
    """The plateau's ground height at x (before the paths, the terraces and the Spire's rock)."""
    t = min(max((x - SOUTH_X) / (NORTH_X - SOUTH_X), 0.0), 1.0)
    return SOUTH_Z + (NORTH_Z - SOUTH_Z) * (t * t * (3 - 2 * t) * .35 + t * .65)


EDGE_Y, EDGE_WAVE, EDGE_PERIOD = -372.0, 14.0, 130.0   # the western edge: y = EDGE_Y + WAVE * sin(x / PERIOD + .9)


def edge_y(x):
    return EDGE_Y + EDGE_WAVE * math.sin(x / EDGE_PERIOD + .9)


# ---------------------------------------------------------------- landmarks (x, y)
STAIR = (-500.0, 20.0)            # the Sunward Stair: the Divinity current's pool, where she arrives and leaves
STAIR_STILL = (-484.0, 36.0)
HOUSE = (-290.0, 0.0)             # the House of Listeners: Aeon and the Serene of Hesper
HOUSE_STILL = (-304.0, -18.0)
TUNING = (-215.0, 34.0)           # the Tuning Court: Dissonance
WALL_X, WALL_WAVE, WALL_PERIOD = -150.0, 6.0, 120.0     # the Choir Wall's centre line: x = WALL_X + WAVE * sin(y / PERIOD + .6)
WALL_THICK, WALL_HIGH, WALL_PANEL = 6.0, 12.0, 12.0     # a panel of it: thickness (x), height, width (y)
MARKET = (-70.0, 10.0)            # the Bell Market: Still Point where the ways part
TERRACES = (30.0, -250.0)         # the Reed Terraces: stepped pools on the western edge
TERRACE_STILL = (-24.0, -150.0)
LOW_BELL = (70.0, -296.0)         # the first bell, on the lowest terrace
GALLERIES = (40.0, 250.0)         # the Amber Galleries
GALLERY_STILL = (-4.0, 170.0)
MID_BELL = (66.0, 286.0)          # the second bell, in the Galleries' middle court
SPIRE_ROCK = (262.0, 316.0, 34.0, 10.0)   # the Watch Spire's rock terrace: centre, radius of its top, height above the ground
SPIRE_STILL = (176.0, 240.0)
SPIRE = (276.0, 330.0)            # the tower itself (a landmark: nobody climbs it)
HIGH_BELL = (250.0, 300.0)        # the third bell, on the terrace before the tower
RAMP = ((200.0, 262.0), (238.0, 280.0))   # the ramp up the terrace's south-west side: foot, top
NAVE_SOUTH, NAVE_NORTH = 240.0, 360.0     # the Nave: the processional way to the Choir Gate along y 0
CONCORD = (440.0, 0.0)            # the Concord's court: centre, ring wall radius below
COURT_WALL = 70.0
ARENA_RADIUS = 32.0
HORN = (476.0, 0.0)               # the Concord's horn, at the court's north side
CHOIR_GATE = (CONCORD[0] - COURT_WALL, 0.0)
COURT_STILL = (CONCORD[0] - COURT_WALL + 12.0, 0.0)
NAVE_STILL = (226.0, -10.0)
HALL = (-330.0, 272.0)            # optional: the Hall of Withheld Votes
SEALED_TRACE = (-420.0, -170.0)   # sealed vaults for abilities learned elsewhere (both open already)
SEALED_WEAVE = (-40.0, 330.0)

# The Reed Terraces' pools: (x, y, half x, half y, surface z above the local ground's level, yaw): stepped down westward.
POOLS = ((40.0, -200.0, 26.0, 16.0, -1.2, 8.0), (60.0, -244.0, 24.0, 18.0, -2.4, -6.0), (24.0, -270.0, 22.0, 14.0, -3.0, 14.0),
         (78.0, -318.0, 20.0, 14.0, -4.2, 0.0))


def wall_x(y):
    return WALL_X + WALL_WAVE * math.sin(y / WALL_PERIOD + .6)


# ---------------------------------------------------------------- regions: name -> (x, y, radius, blend)
REGIONS = {
    'The Sunward Stair': (-500.0, 20.0, 60.0, 30.0),
    'The Long Terrace': (-400.0, 30.0, 70.0, 40.0),
    'The House of Listeners': (-290.0, 0.0, 60.0, 30.0),
    'The Hall of Withheld Votes': (-330.0, 272.0, 70.0, 30.0),
    'The Choir Wall': (-150.0, 30.0, 50.0, 30.0),
    'The Bell Market': (-70.0, 10.0, 70.0, 40.0),
    'The Reed Terraces': (40.0, -250.0, 100.0, 40.0),
    'The Amber Galleries': (40.0, 250.0, 100.0, 40.0),
    'The Watch Spire': (250.0, 310.0, 60.0, 30.0),
    'The Nave': (300.0, 0.0, 70.0, 30.0),
    'The Concord': (440.0, 0.0, 70.0, 20.0),
}

# ---------------------------------------------------------------- paths: (name, kind, half width, points)
# 'road' is paved (pale flagstones), 'trail' trodden dust. The generator levels them and keeps scatter off them.
PATHS = (
    ('Long Terrace', 'road', 5.0, ((-492.0, 26.0), (-430.0, 44.0), (-360.0, 22.0), (-300.0, 2.0))),
    ('Tuning Way', 'road', 4.0, ((-282.0, 6.0), (-240.0, 26.0), (-215.0, 34.0), (-174.0, 30.0))),
    ('Market Way', 'road', 4.0, ((-126.0, 30.0), (-100.0, 22.0), (-70.0, 10.0))),
    ('Nave Road', 'road', 5.0, ((-70.0, 10.0), (60.0, 4.0), (160.0, 0.0), (NAVE_SOUTH, 0.0), (CHOIR_GATE[0] - 4.0, 0.0))),
    ('Reed Walk', 'trail', 3.0, ((-70.0, 10.0), (-40.0, -70.0), (-24.0, -150.0), (20.0, -190.0))),
    ('Gallery Walk', 'road', 3.5, ((-70.0, 10.0), (-30.0, 90.0), (-4.0, 170.0), (30.0, 230.0))),
    ('Spire Path', 'trail', 2.5, ((30.0, 230.0), (110.0, 236.0), (176.0, 240.0), RAMP[0])),
    ('Hall Lane', 'trail', 2.5, ((-360.0, 22.0), (-370.0, 120.0), (-350.0, 220.0), (-332.0, 262.0))),
)

# Level ground: (x, y, radius, height or None for the plateau's own height there).
PADS = (
    (STAIR[0], STAIR[1], 28.0, None), (HOUSE[0], HOUSE[1], 42.0, None), (TUNING[0], TUNING[1], 16.0, None),
    (MARKET[0], MARKET[1], 22.0, None), (TERRACE_STILL[0], TERRACE_STILL[1], 12.0, None), (GALLERY_STILL[0], GALLERY_STILL[1], 12.0, None),
    (SPIRE_STILL[0], SPIRE_STILL[1], 12.0, None), (HALL[0], HALL[1], 30.0, None), (GALLERIES[0], GALLERIES[1], 62.0, None),
    (CONCORD[0], CONCORD[1], COURT_WALL + 6.0, None), (NAVE_STILL[0], NAVE_STILL[1], 12.0, None),
)

# Where nothing is scattered (x, y, radius): set pieces the scenario stands up.
KEEP_CLEAR = (
    (STAIR[0], STAIR[1], 24.0), (STAIR_STILL[0], STAIR_STILL[1], 9.0), (HOUSE[0], HOUSE[1], 44.0), (TUNING[0], TUNING[1], 18.0),
    (MARKET[0], MARKET[1], 18.0), (TERRACE_STILL[0], TERRACE_STILL[1], 12.0), (LOW_BELL[0], LOW_BELL[1], 16.0),
    (GALLERY_STILL[0], GALLERY_STILL[1], 10.0), (GALLERIES[0], GALLERIES[1], 58.0), (SPIRE_STILL[0], SPIRE_STILL[1], 10.0),
    (SPIRE_ROCK[0], SPIRE_ROCK[1], SPIRE_ROCK[2] + 24.0), (CONCORD[0], CONCORD[1], COURT_WALL + 12.0), (NAVE_STILL[0], NAVE_STILL[1], 10.0),
    (HALL[0], HALL[1], 34.0), (SEALED_TRACE[0], SEALED_TRACE[1], 12.0), (SEALED_WEAVE[0], SEALED_WEAVE[1], 12.0),
) + tuple((x, y, max(hx, hy) + 6.0) for x, y, hx, hy, _, _ in POOLS)
# Where the Concord's tone has burnt amber into the ground (x, y, radius). It fades when the Concord stops.
SCAR = ((CONCORD[0], CONCORD[1], 150.0), (wall_x(30.0), 30.0, 50.0), (300.0, 0.0, 70.0), (LOW_BELL[0], LOW_BELL[1], 30.0),
        (MID_BELL[0], MID_BELL[1], 30.0), (HIGH_BELL[0], HIGH_BELL[1], 30.0))


def rim(x, y):
    """How far out of the plateau a point is: 1 on the walkable oval's edge."""
    return math.hypot(x / RIM[0], y / RIM[1])


def off_edge(x, y, pad=0.0):
    """West of the plateau's edge (over the drop)."""
    return y < edge_y(x) + pad


def in_pool(x, y, pad=0.0):
    for px, py, hx, hy, _, yaw in POOLS:
        a = math.radians(yaw)
        lx, ly = (x - px) * math.cos(a) + (y - py) * math.sin(a), -(x - px) * math.sin(a) + (y - py) * math.cos(a)
        if abs(lx) < hx + pad and abs(ly) < hy + pad:
            return True
    return False


def on_wall(x, y, pad=0.0):
    return abs(x - wall_x(y)) < WALL_THICK / 2 + pad


def on_rock(x, y, pad=0.0):
    return math.hypot(x - SPIRE_ROCK[0], y - SPIRE_ROCK[1]) < SPIRE_ROCK[2] + 8.0 + pad


def wall_panels():
    """The Choir Wall's panels: (x, y, yaw) centres from the western edge to the eastern rim, WALL_PANEL apart."""
    out = []
    y = edge_y(WALL_X) - 2.0
    while rim(wall_x(y), y) < 1.0:
        a = -math.degrees(math.atan2(wall_x(y + 1.0) - wall_x(y - 1.0), 2.0))   # the panel's local y along the wall
        out.append((wall_x(y), y, a))
        y += WALL_PANEL
    return out


def path_segments():
    out = []
    for _name, kind, half, points in PATHS:
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            out.append((ax, ay, bx, by, half, kind))
    return out
