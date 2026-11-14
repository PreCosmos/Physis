"""World plan for level 4, Earth: the Wounded Grove (GAME_ROADMAP.md "Level 4"; Tools/grove/README.md is the contract).

Pure Python (no numpy, no unreal): the terrain generator, the map art, the editor tools, the scenario and the logic
scripts all read their places from here, so a number is typed once. Metres, Unreal axes: x north, y east, z up.

The valley: an oval basin about 1.1 km long (north-south) and 0.8 km wide, walled by cliffs. Physis arrives at the
Hollow in the south and walks north: the Reclaimed Road, the Field Camp, the Graft (where she learns Resonance Link),
the Gully (crossed only with the link), the Understory, then west to the Drowned Campus and the Weir (water) and east
through the High Canopy to the Relay (power), and last the Rift around the Heartwood, where the Deeproot Array stands.
"""
import math

HALF_X, HALF_Y = 640.0, 480.0     # the height grid's half extents
CELL = 2.0
TILES_X, TILES_Y = 4, 3           # terrain tiles of 320 x 320 m
WATER = 0.0                       # the lake's surface: the only water deep enough to swim in
RIM = (566.0, 404.0)              # semi-axes of the walkable oval: beyond 0.93 of it the land climbs into cliffs
RIM_START, RIM_END, RIM_RISE = .93, 1.25, 240.0
MAP_HALF = 920.0                  # the pause menu's shared map frame (as the Center's and the Conclave's)

# ---------------------------------------------------------------- landmarks (x, y)
HOLLOW = (-500.0, 30.0)           # the Divinity current's pool: where she arrives and leaves
HOLLOW_STILL = (-484.0, 46.0)     # the Hollow's Still Point, 20 m from the pool
OVERPASS = (-410.0, 108.0)        # the fallen overpass Burr holds up
OLD_TOWN = (-322.0, 268.0)
CAMP = (-250.0, 0.0)              # the Field Camp: Thessaly-4, Wick, the first intercom post
GRAFT = (-162.0, 40.0)            # the graft she listens to: Resonance Link
GULLY_X, GULLY_WAVE, GULLY_PERIOD = -112.0, 9.0, 80.0   # the Gully's centre line: x = GULLY_X + WAVE * sin(y / PERIOD + 1)
GULLY_FLOOR, GULLY_RIM, GULLY_DEPTH = 5.5, 8.0, 9.0     # half width of its floor and of its rims, and its depth
GULLY_CROSS_Y = 42.0              # where the trail meets it: the two link anchors stand here
GULLY_RAMP_Y = -300.0             # its only way out, up the south side
UNDERSTORY = (-40.0, 4.0)         # the mid valley's Still Point: the trails part here
QUAY = (28.0, -146.0)             # the Drowned Campus's quay, on the lake's east shore
LAKE = (60.0, -260.0, 125.0, 100.0)   # centre x, y and semi-axes: the flooded campus
LAKE_BED = -5.0
WEIR = (196.0, -262.0)            # the weir's middle; it runs along y, 56 m wide, the headpond north of it
WEIR_HALF = 28.0
WEIR_CREST = 12.0                 # its deck's height; the headpond stands at HEADPOND
HEADPOND = 10.6
WEIR_BANK = (WEIR[0] + 14.0, WEIR[1] + WEIR_HALF + 9.0)   # level ground at the deck's height, beyond its east end
FALLS = (430.0, -300.0)           # the waterfall on the north-west cliff
FALLS_POOL = (385.0, -272.0)
CANOPY_FOOT = (45.0, 195.0)       # where the climb into the great trees starts
GIANTS = ((70.0, 225.0, 12.0), (105.0, 262.0, 17.0), (145.0, 298.0, 21.0))   # great trees: x, y, platform height
RELAY = (185.0, 335.0)            # the relay mast, on its mesa
RELAY_TOP, RELAY_RADIUS = 62.0, 24.0
HEARTWOOD = (330.0, -20.0)        # the oldest tree, and the Deeproot Array round its foot
KNOLL_TOP, KNOLL_RADIUS = 44.0, 92.0
ARRAY_WALL = 72.0                 # the Array's ring wall (radius); its gate faces south (toward -x)
RIFT_IN, RIFT_OUT, RIFT_DEPTH, RIFT_WALL = 112.0, 128.0, 14.0, 2.5
WEST_BEARING, EAST_BEARING, SOUTH_BEARING, EXIT_BEARING = 237.0, 112.0, 180.0, 150.0   # degrees from +x toward +y, seen from the Heartwood
FORECOURT = (246.0, -20.0)        # the Still Point before the Array's gate, outside the ring wall (84 m from the trunk)
ROOT_COURT = (282.0, -20.0)       # the Still Point just inside the gate
ARENA = (378.0, -20.0)            # the Warden's ground, north of the trunk
ARENA_RADIUS = 21.0


def ring_point(bearing, radius, centre=HEARTWOOD):
    """A point at `radius` metres from the Heartwood on a bearing (degrees from +x toward +y)."""
    a = math.radians(bearing)
    return (centre[0] + math.cos(a) * radius, centre[1] + math.sin(a) * radius)


WEST_CROSSING = ring_point(WEST_BEARING, (RIFT_IN + RIFT_OUT) / 2)   # the root bridge (water)
EAST_CROSSING = ring_point(EAST_BEARING, (RIFT_IN + RIFT_OUT) / 2)   # the link chain from the gantry mast (power)
SOUTH_CROSSING = ring_point(SOUTH_BEARING, (RIFT_IN + RIFT_OUT) / 2)  # the root bridge that grows once the Warden falls
GATE = ring_point(SOUTH_BEARING, ARRAY_WALL)                          # the Array's gate, in the ring wall's south side
MAST = ring_point(EAST_BEARING, RIFT_OUT + 12.0)
RIFT_EXIT = ring_point(EXIT_BEARING, RIFT_OUT + 24.0)                # top of the ramp out of the Rift (outer side)


def gully_x(y):
    return GULLY_X + GULLY_WAVE * math.sin(y / GULLY_PERIOD + 1.0)


GULLY_SOUTH = (gully_x(GULLY_CROSS_Y) - GULLY_RIM - 3.0, GULLY_CROSS_Y)   # the anchors' banks
GULLY_NORTH = (gully_x(GULLY_CROSS_Y) + GULLY_RIM + 3.0, GULLY_CROSS_Y)

# ---------------------------------------------------------------- regions: name -> (x, y, radius, blend), as the Conclave's
REGIONS = {
    'The Hollow': (-500.0, 30.0, 60.0, 30.0),
    'The Reclaimed Road': (-405.0, 105.0, 80.0, 40.0),
    'Old Town': (-322.0, 268.0, 90.0, 40.0),
    'The Field Camp': (-250.0, 0.0, 60.0, 30.0),
    'The Understory': (-40.0, 4.0, 90.0, 50.0),
    'The Drowned Campus': (60.0, -250.0, 140.0, 40.0),
    'The Weir': (215.0, -262.0, 60.0, 30.0),
    'The High Canopy': (100.0, 255.0, 100.0, 50.0),
    'The Relay': (185.0, 335.0, 50.0, 20.0),
    'The Heartwood': (330.0, -20.0, 128.0, 30.0),
    'The Falls': (392.0, -276.0, 60.0, 30.0),
}

# ---------------------------------------------------------------- the land's broad heights: (x, y, height, reach)
# The floor is a smooth blend of these (Gaussian weights of the given reach), under the carving the generator adds.
HEIGHTS = (
    (-500.0, 30.0, 40.0, 110.0), (-405.0, 108.0, 37.0, 90.0), (-322.0, 268.0, 38.0, 110.0), (-250.0, 0.0, 33.0, 80.0),
    (-162.0, 40.0, 31.0, 60.0), (-380.0, -230.0, 46.0, 130.0), (-200.0, -200.0, 36.0, 110.0), (-200.0, 230.0, 36.0, 110.0),
    (-40.0, 4.0, 26.0, 80.0), (60.0, -260.0, 5.0, 120.0), (28.0, -146.0, 6.0, 40.0), (120.0, 60.0, 29.0, 90.0),
    (90.0, 250.0, 36.0, 100.0), (185.0, 335.0, 44.0, 70.0), (330.0, -20.0, 39.0, 150.0), (215.0, -292.0, 11.0, 45.0),
    (300.0, -282.0, 14.0, 50.0), (385.0, -272.0, 20.0, 40.0), (480.0, 100.0, 46.0, 120.0), (350.0, 250.0, 43.0, 110.0),
    (250.0, -150.0, 34.0, 60.0), (0.0, -120.0, 16.0, 50.0),
)

# ---------------------------------------------------------------- paths: (name, kind, half width, points)
# kind 'road' is broken asphalt, 'trail' trodden earth. The generator levels them and keeps scatter off them.
PATHS = (
    ('Reclaimed Road', 'road', 4.0, ((-490.0, 36.0), (-455.0, 72.0), (-410.0, 108.0), (-350.0, 96.0), (-300.0, 52.0), (-262.0, 14.0))),
    ('Old Town Spur', 'road', 3.5, ((-410.0, 108.0), (-392.0, 180.0), (-350.0, 240.0), (-318.0, 268.0))),
    ('Graft Trail', 'trail', 2.0, ((-245.0, 10.0), (-200.0, 30.0), (-165.0, 40.0), (GULLY_SOUTH[0], GULLY_CROSS_Y))),
    ('Understory Trail', 'trail', 2.0, ((GULLY_NORTH[0], GULLY_CROSS_Y), (-70.0, 20.0), (-40.0, 4.0))),
    ('West Trail', 'trail', 2.0, ((-40.0, 4.0), (-25.0, -70.0), (5.0, -120.0), (28.0, -146.0))),
    ('East Trail', 'trail', 2.0, ((-40.0, 4.0), (-10.0, 90.0), (25.0, 160.0), (45.0, 195.0))),
    ('North Trail', 'trail', 2.0, ((-40.0, 4.0), (40.0, 10.0), (120.0, -8.0), ring_point(SOUTH_BEARING, RIFT_OUT + 6.0))),
    ('Weir Path', 'trail', 1.8, (WEIR_BANK, (232.0, -190.0), (252.0, -148.0),
                                 ring_point(WEST_BEARING, RIFT_OUT + 3.0))),
    ('Service Road', 'road', 3.0, ((25.0, 160.0), (110.0, 130.0), (200.0, 125.0), (MAST[0] - 4.0, MAST[1] + 2.0))),
)

# Level ground: (x, y, radius, height or None for the land's own height there).
PADS = (
    (HOLLOW[0], HOLLOW[1], 28.0, None), (CAMP[0], CAMP[1], 34.0, None), (GRAFT[0], GRAFT[1], 14.0, None),
    (UNDERSTORY[0], UNDERSTORY[1], 18.0, None), (QUAY[0], QUAY[1], 15.0, 2.2), (CANOPY_FOOT[0], CANOPY_FOOT[1], 14.0, None),
    (OLD_TOWN[0], OLD_TOWN[1], 58.0, None), (FALLS_POOL[0], FALLS_POOL[1], 13.0, 20.0), (MAST[0], MAST[1], 9.0, None),
    (WEIR_BANK[0], WEIR_BANK[1], 10.0, WEIR_CREST),
)
# The river from the Falls to the headpond, and its bed's half width.
RIVER = ((FALLS_POOL[0], FALLS_POOL[1]), (340.0, -286.0), (290.0, -280.0), (252.0, -266.0), (WEIR[0] + 6.0, WEIR[1]))
RIVER_HALF = 6.0

# Where nothing grows and no house or tree is scattered (x, y, radius): set pieces the scenario stands up.
KEEP_CLEAR = (
    (HOLLOW[0], HOLLOW[1], 22.0), (HOLLOW_STILL[0], HOLLOW_STILL[1], 9.0), (OVERPASS[0], OVERPASS[1], 26.0),
    (CAMP[0], CAMP[1], 32.0), (GRAFT[0], GRAFT[1], 12.0), (GULLY_SOUTH[0], GULLY_SOUTH[1], 7.0),
    (GULLY_NORTH[0], GULLY_NORTH[1], 7.0), (UNDERSTORY[0], UNDERSTORY[1], 14.0), (QUAY[0], QUAY[1], 16.0),
    (CANOPY_FOOT[0], CANOPY_FOOT[1], 12.0), (RELAY[0], RELAY[1], RELAY_RADIUS + 4.0), (MAST[0], MAST[1], 9.0),
    (HEARTWOOD[0], HEARTWOOD[1], RIFT_OUT + 4.0), (WEIR[0] + 10.0, WEIR[1], 40.0), (FALLS_POOL[0], FALLS_POOL[1], 14.0),
    (RIFT_EXIT[0], RIFT_EXIT[1], 10.0), (WEST_CROSSING[0], WEST_CROSSING[1], 14.0), (EAST_CROSSING[0], EAST_CROSSING[1], 14.0),
    (SOUTH_CROSSING[0], SOUTH_CROSSING[1], 14.0),
) + tuple((x, y, 9.0) for x, y, _ in GIANTS)
# Where the wound shows: blighted ground, thornroot and dead trees (x, y, radius). The ground material fades it when
# the grove heals.
BLIGHT = ((HEARTWOOD[0], HEARTWOOD[1], 190.0), (WEIR[0] + 20.0, WEIR[1], 60.0), (RELAY[0] - 20.0, RELAY[1] - 20.0, 55.0),
          (GRAFT[0] + 40.0, GRAFT[1], 45.0), (OVERPASS[0] + 30.0, OVERPASS[1] + 10.0, 40.0))


def rim(x, y):
    """How far out of the valley a point is: 1 on the walkable oval's edge."""
    return math.hypot(x / RIM[0], y / RIM[1])


def in_lake(x, y, pad=0.0):
    cx, cy, ax, ay = LAKE
    return math.hypot((x - cx) / (ax + pad), (y - cy) / (ay + pad)) < 1.0


def in_gully(x, y, pad=0.0):
    return abs(x - gully_x(y)) < GULLY_RIM + pad


def in_rift(x, y, pad=0.0):
    r = math.hypot(x - HEARTWOOD[0], y - HEARTWOOD[1])
    return RIFT_IN - pad < r < RIFT_OUT + pad


def path_segments():
    """[(ax, ay, bx, by, half width, kind)] for every path segment."""
    out = []
    for _name, kind, half, points in PATHS:
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            out.append((ax, ay, bx, by, half, kind))
    return out
