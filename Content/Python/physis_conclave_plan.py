"""World plan for level 3, the Conclave: shared by Tools/build_physis_conclave.py (Blender) and the
Unreal side (physis_conclave_tools.py, physis_conclave_scenario.py). Pure Python, no imports from
either host.

Units are metres unless a name ends in _CM. Axes follow Unreal: x north along the drum's axis, y east,
z up. The drum is a cylinder of radius R around the line (y 0, z AXIS_Z); Physis walks the bottom land
strip, which follows the circle, so the ground rises gently to either side. Water stands at z 0, the
convention of the Center, so the shared swimming and enemy-hover rules work unchanged.

The map frame is the Center's (MAP_HALF 920 m around the origin, north up), so the pause menu's
markers use the same transform in both levels.
"""
import math

R = 700.0                 # drum radius
FLOOR = 6.0               # height of the floor strip's lowest line (y 0) above the water
AXIS_Z = R + FLOOR        # the Spine runs along the axis
HALF_X = 800.0            # end caps at x = +-HALF_X
STRIP = math.radians(30)  # the floor land strip spans +-30 degrees around the bottom
WINDOW = math.radians(60)  # each window strip is 60 degrees wide; land and window strips alternate
WALK_Y = 300.0            # the playable floor ends here; a berm and parapet close it
CELL = 2.0                # terrain grid resolution
TILES_X, TILES_Y = 8, 2
WATER = 0.0
MAP_HALF_CM = 92000.0


def drum_z(y):
    """Height of the drum's inner surface (the bare circle) at lateral offset y, for |y| < R."""
    y = max(-R + 1e-3, min(R - 1e-3, y))
    return AXIS_Z - math.sqrt(R * R - y * y)


# Regions: name -> (x, y, radius, blend). Heights follow the drum circle plus each region's shaping in
# the Blender height(); the Unreal side reads the exported grid (height.bin) and never recomputes it.
REGIONS = {
    'Wellspring': (-740, 0, 45, 30),
    'Commons': (-470, 0, 175, 60),
    'Terraces': (-60, -215, 135, 50),
    'Reservoir': (40, 20, 115, 40),
    'Foundry': (-40, 215, 130, 50),
    'Spire': (360, 0, 60, 40),
    'Old Quarter': (480, 205, 120, 50),
    'Orchard Rim': (400, -205, 130, 50),
    'Docks': (705, 0, 85, 30),
}

# Roads (polylines of (x, y)): the main road from the Wellspring through the Commons, the three
# district roads, the roads north to the Spire, and the Spire road to the docks.
PATHS = (
    ((-760, 0), (-700, 0), (-600, 0), (-470, 0), (-360, 0), (-250, 0)),
    ((-250, 0), (-170, -90), (-110, -170), (-60, -215)),
    ((-250, 0), (-170, 90), (-110, 170), (-40, 215)),
    ((-250, 0), (-150, -10), (-75, -20)),
    ((-60, -215), (60, -205), (180, -150), (290, -60), (330, 0)),
    ((-40, 215), (80, 205), (200, 150), (300, 60), (330, 0)),
    ((120, 60), (220, 40), (300, 15)),
    ((330, 0), (420, 0), (520, 0), (630, 0), (700, 0)),
    ((430, 30), (450, 120), (480, 205)),
    ((430, -30), (420, -120), (400, -205)),
)
# Road half widths: the main road (0) and the Spire road to the docks (7) are the wide ones. Two short connectors join
# the Old Quarter and Orchard Rim roads (which start 30 m off it) to the Spire road. Copies of drum.road_lines() and
# drum.CONNECTORS (drum.py keeps its own until it is next rebuilt); M_CNGround draws every road from road_segments().
WIDE_ROADS, WIDE_HALF, ROAD_HALF = (0, 7), 4.5, 3.5
CONNECTORS = (((430.0, 0.0), (430.0, 30.0)), ((430.0, 0.0), (430.0, -30.0)))
CONNECTOR_HALF = 3.0

# Places the scenario and the generator agree on (metres).
WELL = (-752.0, 0.0)           # the current pool home to the Center
COMMONS_PLAZA = (-470.0, 0.0)
ORRERY = (-470.0, 0.0)
ARCHIVE = (-420.0, 120.0)
MENDERY = (-520.0, -110.0)
SHRINE = (-560.0, 95.0)
PATIENCE = (-430.0, 52.0)
TERRACE_PYLON = (-20.0, -268.0)
RESERVOIR_ISLAND = (60.0, 45.0)
RESERVOIR_PYLON = (60.0, 45.0)
FOUNDRY_PYLON = (10.0, 270.0)
SPIRE = (360.0, 0.0)
DOCKS_ARENA = (700.0, 0.0)
LAKE = (40.0, 20.0, 95.0, 70.0)   # centre x, y and the lake's half lengths along x and y (an ellipse)
# Paved plazas: centre and radius (the Blender build levels and whitens the same two).
PLAZAS = ((ORRERY, 45.0), (SPIRE, 60.0))


def road_lines():
    """Every road as (points, half width) in drum.road_lines() order: the plan's paths with the two connectors after
    path 7."""
    lines = []
    for k, pts in enumerate(PATHS):
        lines.append(([tuple(map(float, p)) for p in pts], WIDE_HALF if k in WIDE_ROADS else ROAD_HALF))
        if k == 7:
            lines += [([tuple(p) for p in c], CONNECTOR_HALF) for c in CONNECTORS]
    return lines


def road_segments():
    """Every road segment as (ax, ay, bx, by, half width, arc0), in road_lines() order; arc0 is the length along the
    segment's road from its first point to the segment's start."""
    out = []
    for pts, half in road_lines():
        arc = 0.0
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            out.append((ax, ay, bx, by, half, arc))
            arc += math.hypot(bx - ax, by - ay)
    return out


def path_gap(x, y):
    """Distance in metres from (x, y) to the nearest road."""
    best = 1e18
    for line in PATHS:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(dx * dx + dy * dy, 1e-9)))
            best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def in_lake(x, y, margin=0.0):
    cx, cy, ax, ay = LAKE
    return ((x - cx) / (ax + margin)) ** 2 + ((y - cy) / (ay + margin)) ** 2 < 1.0
