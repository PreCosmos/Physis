"""The drum of the Conclave (level 3): the floor terrain, the lake, the three window strips, the upper lands,
the end caps, the Spine, the parapets at the walk limit, and the town and vegetation layout (scatter.json).
Pure numpy: Tools/build_physis_conclave.py builds and exports it in Blender; check.py validates it offline.

World-space meshes (their vertices are world metres; the level build places them at the origin):
SM_CD_Terrain_<i>_<j>, SM_CD_Water, SM_CD_Windows, SM_CD_UpperLandE / W, SM_CD_CapSouth / North,
SM_CD_ParapetW / E. SM_CD_SpineDim / SM_CD_SpineLit are one third of the Spine centred on the origin, placed
three times along the axis (y 0, z AXIS_Z) at x -533.3, 0 and +533.3.

The floor follows physis_conclave_plan: the drum circle plus a gentle undulation, terraced where people
built (Commons and Old Quarter pads of 2.5 m, Orchard Rim 3 m, Terraces 3.5 m, Foundry 4 m; every riser is a
ramp of about 30 degrees, so the whole floor is walkable), flat plazas, the lake bowl and its island, the
slag moat around the Foundry Pylon, cut-and-fill roads with level cross sections, and berms too steep to
walk beyond the walk limit and at the end caps. Cut and fill always stands at BATTER (30 degrees), which
keeps every apron walkable without the slope of the hill adding to it.

  write_height(out)   height.bin + height.json (Tools/conclave/README.md, Terrain)
  write_scatter(out)  scatter.json: houses, ruins, terrace walls, stairs, lamps, street furniture, orchards,
                      crops, hedges, trees, grass, flowers, reeds and lilies, clear of every keep-clear zone
  python3 drum.py [--out DIR]   offline: writes both and prints the height and scatter report
"""
import functools
import json
import math
import sys
from pathlib import Path

import numpy as np

from palette import (ASH, BLACK, BLUE_ICE, BLUE_PALE, CHARCOAL, GOLD, GOLD_PALE, GOLD_STRAW, GREEN_GRASS, GREEN_MOSS,
                     GREEN_PALE, IVORY,
                     LIGHT_BLUE, LIGHT_GOLD, LIGHT_WARM, LIGHT_WHITE, RED, RED_BRIGHT, RED_DEEP, SLATE, WHITE, WHITE_COOL,
                     WHITE_PURE, allowed, grey)
from toolkit import Part, arch, bevel_box, blur, box, cylinder, fbm, hexa, lathe, oriented, tube

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'Content/Python'))
import physis_conclave_plan as plan  # noqa: E402

R, AXIS_Z, FLOOR = plan.R, plan.AXIS_Z, plan.FLOOR
HALF_X, CELL, WATER, WALK = plan.HALF_X, plan.CELL, plan.WATER, plan.WALK_Y
HALF_Y = round(R * math.sin(plan.STRIP) / CELL) * CELL          # 350: the floor strip's edge, where the windows begin
NX, NY = int(round(2 * HALF_X / CELL)) + 1, int(round(2 * HALF_Y / CELL)) + 1   # 801 x 351
AXIS_X = np.linspace(-HALF_X, HALF_X, NX)
AXIS_Y = np.linspace(-HALF_Y, HALF_Y, NY)
BATTER = .58                    # every cut and fill (30 degrees): walkable even where the land also falls along it
PLAZA = FLOOR + .6              # the Commons' lowest level: the Orrery plaza and the main street
END_BERM = HALF_X - 17.0        # the end-cap berms start here (|x|)
BERM_FACE = 1.6                 # the steepest the side berm rises from the walk limit (58 degrees: unclimbable)

# Terraced regions: step height, riser width (horizontal, so step / riser stays near 30 degrees), the place a
# level passes through (or a height), and the lowest level (the Commons fills its street up to the plaza).
# The Old Quarter and the Foundry sit high on the slope, where 2.5 m steps would leave pads too narrow for a
# ruin or a workshop, so they step two and two-and-a-half wall heights at a time (two flights of stairs a riser).
# A place may carry a height offset: the Foundry Pylon's yard is a quarried yard cut 8.5 m into the slope, so
# its fill on the downhill side stays a few metres and ends before the Foundry road (a 30 degree batter on a
# 22 degree hillside runs out five times its height).
LISTENERS = (410.0, -235.0)             # the listeners' terrace above the orchards (their four stones)
TERRACED = (
    ('Commons', 2.5, 4.5, PLAZA, 0),
    ('Old Quarter', 5.0, 9.0, (480.0, 205.0), None),
    ('Orchard Rim', 3.0, 5.2, LISTENERS, None),
    ('Terraces', 3.5, 6.0, plan.TERRACE_PYLON, None),
    ('Foundry', 6.0, 10.5, plan.FOUNDRY_PYLON + (-8.5,), None),
)
TOWN = ('Commons', 'Old Quarter')        # regions laid out as streets of pads, walls and stairs

# Keep-clear zones for houses and scatter (README, Terrain), metres.
KEEP_CLEAR = (
    ('Wellspring', plan.WELL, 30.0), ('Orrery plaza', plan.ORRERY, 45.0), ('Archive', plan.ARCHIVE, 16.0),
    ('Mendery', plan.MENDERY, 12.0), ('Shrine', plan.SHRINE, 10.0), ('Patience', plan.PATIENCE, 8.0),
    ('Terrace Pylon', plan.TERRACE_PYLON, 22.0), ('Reservoir Pylon', plan.RESERVOIR_PYLON, 22.0),
    ('Foundry Pylon', plan.FOUNDRY_PYLON, 22.0), ('Spire', plan.SPIRE, 70.0), ('Docks arena', plan.DOCKS_ARENA, 60.0),
    # Set pieces the scenario stands beyond a single free spot (physis_conclave_scenario.py): the barricade ring that
    # closes the upper Terraces (TERRACE_RING 34 m round the pylon), the barricade ring round Ilex's workshop, the
    # Foundry's furnace row, the four Light Cache courts, the Old Quarter's light run lane (41 m of walls along x)
    # and the bell square. Scatter under them met their walls and barricades (harness, 2026-11-07).
    ('Terrace barricade ring', plan.TERRACE_PYLON, 38.0), ('Ilex workshop ring', (-25.0, 190.0), 18.0),
    ('Furnace row', (-100.0, 172.0), 20.0), ('Lane Cache court', (520.0, 240.0), 12.0),
    ('Quarter Cache court', (430.0, 135.0), 12.0), ('Orchard Cache court', (360.0, -150.0), 12.0),
    ('Terrace Cache court', (45.0, -250.0), 12.0), ('Light run', (575.0, 160.0), 26.0),
    ('Siegeframe hoard', (527.0, 115.0), 8.0),
)
GATE_ROAD = (-330.0, -280.0, 12.0)      # x from, x to, |y| below: the North Gate road
ROAD_MARGIN = 6.0
ROAD_VERGE = 7.6                        # roads are level this far from their centreline (stone, then a grass verge)
# Short streets that join the Old Quarter and Orchard Rim roads (which start 30 m off it) to the Spire road.
CONNECTORS = (((430.0, 0.0), (430.0, 30.0)), ((430.0, 0.0), (430.0, -30.0)))

# Flat pads under landmarks the scenario places: name, centre, radius of the flat part, and the terraced region
# whose level grid the pad snaps to (so it is flush with the pads around it).
PADS = (('Archive', plan.ARCHIVE, 13.0, 'Commons'), ('Mendery', plan.MENDERY, 9.0, 'Commons'),
        ('Shrine', plan.SHRINE, 6.5, 'Commons'), ('Patience', plan.PATIENCE, 7.0, 'Commons'),
        ('Listeners', LISTENERS, 12.0, 'Orchard Rim'))
MOAT_IN, MOAT_W, MOAT_DEPTH = 18.0, 10.0, 6.0
# Each moat wall falls over 3 m (72 degrees, still unclimbable): a wall narrower than the 2 m grid lands on whole
# cells and reads as a stepped polygon; spread over two cells the circle stays round. Radius and width are measured
# at half depth, so they keep the README's 18 and 10 m; the gap at the top is 13 m.
MOAT_EDGE = 1.5
FOUNDRY_APRON = 32.0                    # the flat yard, moat and apron around the Foundry Pylon
# Scatter keeps out of the Foundry's works, beyond the README's 22 m round the pylon: the yard, the moat and its
# apron, the south-west embankment where the scenario stands the crane's outer leg (34 m), the cable locks (35.5-38.5
# m) and a capsule (43 m), and the moat's exit notch, the only way out of the moat. A boulder there met a crane leg
# and half blocked the notch.
FOUNDRY_WORKS = 46.0
NOTCH_HALF, NOTCH_END = 3.2, MOAT_IN + MOAT_W + 30.0   # the notch trench: half width and its end (m north of the pylon)
# The apron's embankment on its downhill (west) side, 38.7 degrees: the Foundry road runs 15.7 m below the apron and
# only 19.4 m beyond its edge, so neither batter can reach the other at 30 degrees; the road's cut otherwise left an
# 8 m sheer terrain face there. 0.786 is the least slope that keeps every road verge level; still walkable (the
# character's floor limit is 44.8 degrees).
YARD_EMBANKMENT = .80
NOTCH_SLOPE = .58                       # the moat's exit ramp (30 degrees)
TERRACE_PYLON_PAD = 16.0
ISLAND_TOP, ISLAND_FLAT, ISLAND_FOOT = 3.0, 9.0, 26.0


# ---------------------------------------------------------------- small helpers

def sstep(a, b, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def drum_z(y):
    """The drum's bare circle under the floor (vectorised physis_conclave_plan.drum_z)."""
    y = np.clip(np.asarray(y, np.float64), -R + 1e-3, R - 1e-3)
    return AXIS_Z - np.sqrt(R * R - y * y)


def region_w(name, x, y):
    cx, cy, r, b = plan.REGIONS[name]
    return sstep(0, 1, 1 - (np.hypot(np.asarray(x) - cx, np.asarray(y) - cy) - r) / b)


def sample(grid, x, y):
    """Bilinear sample of a floor grid at world metres: the interpolation the Unreal side reads height.bin with."""
    fx = (np.asarray(x, np.float64) + HALF_X) / CELL
    fy = (np.asarray(y, np.float64) + HALF_Y) / CELL
    i = np.clip(np.floor(fx).astype(np.int64), 0, NX - 2)
    j = np.clip(np.floor(fy).astype(np.int64), 0, NY - 2)
    u, v = np.clip(fx - i, 0, 1), np.clip(fy - j, 0, 1)
    return grid[i, j] * (1 - u) * (1 - v) + grid[i + 1, j] * u * (1 - v) + grid[i, j + 1] * (1 - u) * v + grid[i + 1, j + 1] * u * v


def nearest_on(lines, x, y):
    """Distance from points to the nearest of several polylines, which polyline, and the arc length there."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    best, which, arc = np.full(x.shape, 1e18), np.zeros(x.shape, np.int64), np.zeros(x.shape)
    for k, line in enumerate(lines):
        s0 = 0.0
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy)
            t = np.clip(((x - ax) * dx + (y - ay) * dy) / (length * length), 0, 1)
            d = np.hypot(x - ax - t * dx, y - ay - t * dy)
            m = d < best
            best, which, arc = np.where(m, d, best), np.where(m, k, which), np.where(m, s0 + t * length, arc)
            s0 += length
    return best, which, arc


def cut_fill(h, d, level, r0):
    """Flat at level within r0 of a centre (d = distance), then cut and fill at BATTER until it meets the land."""
    k = BATTER * np.maximum(d - r0, 0)
    return np.clip(h, level - k, level + k)


def lake_metric(x, y):
    """Approximate signed distance (m) to the lake shore, negative over the water."""
    cx, cy, ax, ay = plan.LAKE
    ex, ey = (np.asarray(x) - cx) / ax, (np.asarray(y) - cy) / ay
    q = np.sqrt(ex * ex + ey * ey)
    g = np.sqrt((ex / ax) ** 2 + (ey / ay) ** 2) / np.maximum(q, 1e-9)
    return (q - 1) / np.maximum(g, 1e-9)


def lake_profile(d, x, y):
    """The lake's bed (black silt at -4 m) and its beach and bank (white sand, then 17 degrees up to the land)."""
    bed = -4.0 * sstep(0, 24, -d) + .35 * fbm(x, y, 21, 3, 1 / 30.0) * sstep(2, 12, -d)
    shore = 1.3 * sstep(-1, 9, d) + .30 * np.maximum(d - 7, 0)
    return np.where(d < 0, bed, shore)


def island_profile(x, y):
    ix, iy = plan.RESERVOIR_ISLAND
    r = np.hypot(np.asarray(x) - ix, np.asarray(y) - iy)
    return ISLAND_TOP - (ISLAND_TOP + 4.0) * sstep(ISLAND_FLAT, ISLAND_FOOT, r)


def in_gate_road(x, y):
    x0, x1, half = GATE_ROAD
    return (np.asarray(x) > x0) & (np.asarray(x) < x1) & (np.abs(np.asarray(y)) < half)


def in_foundry_works(x, y, pad=0.0):
    """True inside the Foundry's works (FOUNDRY_WORKS round the pylon, and the exit notch north of it), plus pad."""
    fx, fy = plan.FOUNDRY_PYLON
    along, across = np.asarray(x, np.float64) - fx, np.abs(np.asarray(y, np.float64) - fy)
    notch = (along > MOAT_IN - pad) & (along < NOTCH_END + pad) & (across < NOTCH_HALF + pad)
    return (np.hypot(along, across) < FOUNDRY_WORKS + pad) | notch


# ---------------------------------------------------------------- palette (vectorised palette.family)

def _srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= .0031308, c * 12.92, 1.055 * np.power(np.maximum(c, .0031308), 1 / 2.4) - .055)


def _linear(s):
    s = np.clip(s, 0, 1)
    return np.where(s <= .04045, s / 12.92, np.power((np.maximum(s, .04045) + .055) / 1.055, 2.4))


def _hsv(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    safe = np.maximum(d, 1e-12)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.select([mx == r, mx == g], [(g - b) / safe, 2 + (b - r) / safe], 4 + (r - g) / safe)
    h = np.where(d > 1e-12, (h / 6) % 1, 0) * 360
    return h, np.where(mx > 0, d / np.maximum(mx, 1e-12), 0), mx


def _rgb(h, s, v):
    h6 = (np.asarray(h) / 60.0) % 6
    i = np.floor(h6).astype(np.int64)
    f = h6 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    sel = [i == k for k in range(6)]
    r = np.select(sel, [v, q, p, p, t, v])
    g = np.select(sel, [t, v, v, q, p, p])
    b = np.select(sel, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)


def palette_mask(lin):
    """True where a linear colour passes palette.allowed (same thresholds, vectorised)."""
    h, s, v = _hsv(_srgb(np.asarray(lin, np.float64)[..., :3]))
    grey_ = (s < .12) | (v < .04)
    gold = (h >= 36) & (h <= 52) & (s >= .18) & (v >= .50)
    red = ((h >= 345) | (h <= 10)) & (s >= .55) & (v >= .30)
    blue = (h >= 188) & (h <= 222) & (s >= .10) & (s <= .68) & (v >= .58)
    green = (h >= 70) & (h <= 165) & (s >= .15) & (v >= .20)
    return grey_ | gold | red | blue | green


def snap(lin):
    """Pushes blended colours back into the palette: a gold, red, light blue or green stays in its family (saturation
    and value raised to the family's floor), anything between families or too dark to read as one becomes the grey
    of the same value. Blends of grass with white stone or black soil need this at their edges."""
    lin = np.asarray(lin, np.float64)
    h, s, v = _hsv(_srgb(lin[..., :3]))
    grey_ = s < .115
    gold = ~grey_ & (h >= 20) & (h <= 70) & (s >= .15) & (v >= .45)
    red = ~grey_ & ((h >= 325) | (h <= 18)) & (s >= .45) & (v >= .25)
    blue = ~grey_ & (h >= 170) & (h <= 240) & (v >= .50)
    green = ~grey_ & (h > 70) & (h < 170) & (s >= .10) & (v >= .14)
    h2, s2, v2 = h.copy(), s.copy(), v.copy()
    h2 = np.where(gold, np.clip(h, 37.5, 50.5), h2)
    s2 = np.where(gold, np.maximum(s, .19), s2)
    v2 = np.where(gold, np.maximum(v, .51), v2)
    h2 = np.where(red, np.where(h > 180, np.clip(h, 346.5, 360), np.clip(h, 0, 9)), h2)
    s2 = np.where(red, np.maximum(s, .56), s2)
    v2 = np.where(red, np.maximum(v, .31), v2)
    h2 = np.where(blue, np.clip(h, 189.5, 220.5), h2)
    s2 = np.where(blue, np.clip(s, .11, .67), s2)
    v2 = np.where(blue, np.maximum(v, .59), v2)
    h2 = np.where(green, np.clip(h, 71.5, 163.5), h2)
    s2 = np.where(green, np.maximum(s, .16), s2)
    v2 = np.where(green, np.maximum(v, .21), v2)
    s2 = np.where(grey_ | ~(gold | red | blue | green), np.minimum(s, .08), s2)
    out = _linear(_rgb(h2, s2, v2))
    bad = ~palette_mask(out)
    if bad.any():  # a rounding edge case: the grey of the same value always passes
        out[bad] = np.repeat(_linear(v[bad])[:, None], 3, 1)
    if lin.shape[-1] == 4:
        out = np.concatenate([out, lin[..., 3:]], -1)
    return out


def shade(colour, k):
    """A palette colour times k (grime, occlusion), kept in the palette."""
    c = np.array(colour[:3], np.float64) * k
    return tuple(snap(c[None])[0]) + (1.0,)


def mix(a, b, t):
    t = np.asarray(t, np.float64)[..., None]
    return np.asarray(a, np.float64)[..., :3] * (1 - t) + np.asarray(b, np.float64)[..., :3] * t


# ---------------------------------------------------------------- the streets of the town (stair lanes)

@functools.lru_cache(maxsize=1)
def people_points():
    """Where the scenario stands people, scan markers and tutorials: houses, walls, trees and rocks keep off them."""
    try:
        import physis_conclave_lore as lore
    except Exception:  # the plan alone is enough to lay out the land
        return ()
    pts = [tuple(p[5]) for p in lore.PEOPLE]
    pts += [tuple(s[3][:2]) for s in lore.CONCLAVE_SCANS]
    pts += [tuple(t[1]) for t in lore.CONCLAVE_TUTORIALS]
    return tuple((float(x), float(y)) for x, y in pts)


def _lane_clear(x, y0, y1, margin):
    ys = np.linspace(y0, y1, 64)
    xs = np.full_like(ys, x)
    for _, (zx, zy), zr in KEEP_CLEAR:
        if np.hypot(xs - zx, ys - zy).min() < zr + margin:
            return False
    for px, py in people_points():
        if np.hypot(xs - px, ys - py).min() < 5.0:
            return False
    return True


def stair_lanes():
    """Lanes climbing the town's pads across the contours, one flight of SM_CN_Stairs at every riser. Each lane is
    (region, side, x, |y| from, |y| to); side +1 climbs the east slope (+y), -1 the west. Spaced about 58 m
    apart, shifted off keep-clear zones and people so the stairs never land on them."""
    lanes = []
    for region, sides, x0, x1, spacing, y_lo, y_hi in (('Commons', (1, -1), -628.0, -318.0, 58.0, 50.0, 236.0),
                                                       ('Old Quarter', (1,), 384.0, 586.0, 52.0, 96.0, 296.0)):
        cx, cy, r, b = plan.REGIONS[region]
        for side in sides:
            x = x0 + (19.0 if side < 0 else 0.0)
            while x <= x1:
                # The lane stays inside the region's full weight (pads there are whole 2.5 m steps).
                ys = np.arange(y_lo, y_hi, 2.0)
                inside = ys[region_w(region, np.full_like(ys, x), side * ys) > .97]
                if len(inside) > 8 and _lane_clear(x, side * inside[0], side * inside[-1], 5.0):
                    lanes.append((region, side, x, float(inside[0]), float(inside[-1])))
                    x += spacing
                else:
                    x += 4.0
    return lanes


# ---------------------------------------------------------------- the height grid

def base_height(x, y):
    """The drum circle plus a gentle undulation, calmer along the middle and fading before the window frame."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    ay = np.abs(y)
    rough = (1 + .7 * sstep(140, 290, ay)) * (1 - sstep(300, 340, ay))
    und = 1.5 * fbm(x, y, 3, 5, 1 / 230.0) + .45 * fbm(x, y, 4, 3, 1 / 46.0)
    return drum_z(y) + und * rough


def terrace(hb, slope, origin, step, riser, lowest=None):
    """Steps hb into level pads every `step` metres; the riser between two pads is a straight ramp `riser` metres
    wide along the fall line (where the land is steeper than that, the slope is left as it is). Returns the
    stepped height, the level coordinate u (integer at the top of every riser) and the riser fraction."""
    u = (hb - origin) / step
    if lowest is not None:
        u = np.maximum(u, lowest)
    n = np.floor(u)
    t = u - n
    f = np.clip(riser * slope / step, .02, 1.0)
    ramp = np.clip((t - (1 - f)) / f, 0, 1)
    return origin + step * (n + ramp), u, ramp


def road_lines():
    """The plan's roads plus the two connectors, with half-widths: (points, half width, plan index or -1)."""
    lines = []
    for k, pts in enumerate(plan.PATHS):
        lines.append(([tuple(map(float, p)) for p in pts], 4.5 if k in (0, 7) else 3.5, k))
        if k == 7:
            lines += [([tuple(p) for p in c], 3.0, -1) for c in CONNECTORS]
    return lines


def _profiles(H, lines, plazas=()):
    """Each road's centreline height: the shaped land sampled every 2 m, smoothed over about 10 m, and pinned where
    a road starts or ends on another so junctions meet; at a plaza's level inside it, easing back to the land over
    25 m outside (the smoothing alone left a road 0.4 m off the plaza, which the plaza's batter then bent into a 20
    degree kink at its rim); never below the water. plazas: (x, y, level, radius)."""
    out = []
    kernel = np.exp(-.5 * (np.arange(-15, 16) / 5.0) ** 2)
    kernel /= kernel.sum()
    for pts, hw, _ in lines:
        P = np.array(pts)
        seg = np.hypot(*np.diff(P, axis=0).T)
        s = np.concatenate([[0], np.cumsum(seg)])
        ss = np.linspace(0, s[-1], max(2, int(s[-1] / 2.0) + 1))
        xs, ys = np.interp(ss, s, P[:, 0]), np.interp(ss, s, P[:, 1])
        z = sample(H, xs, ys)
        z = np.convolve(np.pad(z, 15, mode='edge'), kernel, mode='valid')
        pins = []
        for end in (0, -1):
            pin = z[end]
            for o in out:
                d, _, arc = nearest_on([o['pts']], np.array([xs[end]]), np.array([ys[end]]))
                if d[0] < 1.5:
                    pin = float(np.interp(arc[0], o['ss'], o['z']))
                    break
            pins.append(pin)
        a = ss / ss[-1]
        z = z + (pins[0] - z[0]) * (1 - a) + (pins[1] - z[-1]) * a
        for px, py, level, r0 in plazas:   # junctions inside a plaza stay matched: every road there takes its level
            k = 1 - sstep(r0, r0 + 25.0, np.hypot(xs - px, ys - py))
            z = z * (1 - k) + level * k
        out.append({'pts': pts, 'hw': hw, 'ss': ss, 'z': np.maximum(z, WATER + .4), 's': s})
    return out


def _apply_roads(H, X, Y, profiles):
    best = np.full(H.shape, 1e18)
    zr, hw = np.zeros(H.shape), np.zeros(H.shape)
    for o in profiles:
        s0 = 0.0
        for (ax, ay), (bx, by) in zip(o['pts'], o['pts'][1:]):
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy)
            t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (length * length), 0, 1)
            d = np.hypot(X - ax - t * dx, Y - ay - t * dy)
            m = d < best
            best = np.where(m, d, best)
            zr = np.where(m, np.interp(s0 + t * length, o['ss'], o['z']), zr)
            hw = np.where(m, o['hw'], hw)
            s0 += length
    # Level across the road and a flat verge (lamps and benches stand on it), then the batter.
    k = BATTER * np.maximum(best - np.maximum(hw + 3.0, ROAD_VERGE), 0)
    return np.clip(H, zr - k, zr + k), best, hw


def _shape():
    X, Y = np.meshgrid(AXIS_X, AXIS_Y, indexing='ij')
    ay = np.abs(Y)
    base = base_height(X, Y)
    gx, gy = np.gradient(blur(base, 2), CELL)
    slope = np.hypot(gx, gy)
    H = base.copy()
    G = {'X': X, 'Y': Y, 'base': base, 'terraces': {}}

    # Terraced regions: the stepped land blended into the drum by each region's weight.
    for name, step, riser, origin, lowest in TERRACED:
        org = origin if np.isscalar(origin) else float(base_height(np.array([origin[0]]), np.array([origin[1]]))[0]) + (origin[2] if len(origin) > 2 else 0.0)
        T, u, ramp = terrace(base, slope, org, step, riser, lowest)
        w = region_w(name, X, Y)
        H = H * (1 - w) + T * w
        G['terraces'][name] = {'u': u, 'ramp': ramp, 'w': w, 'origin': org, 'step': step, 'riser': riser}

    # The Foundry Pylon's yard: flat to the apron, then the slag moat cut 6 m into it.
    fx, fy = plan.FOUNDRY_PYLON
    rf = np.hypot(X - fx, Y - fy)
    lf = G['terraces']['Foundry']['origin']
    H = cut_fill(H, rf, lf, FOUNDRY_APRON)
    # Landmark pads at the town level nearest their centre; the Terrace Pylon on its top step.
    for name, (px, py), r0, region in PADS:
        t = G['terraces'][region]
        h0 = float(sample(H, px, py))
        level = t['origin'] + t['step'] * round((h0 - t['origin']) / t['step'])
        H = cut_fill(H, np.hypot(X - px, Y - py), level, r0)
    tx, ty = plan.TERRACE_PYLON
    H = cut_fill(H, np.hypot(X - tx, Y - ty), G['terraces']['Terraces']['origin'], TERRACE_PYLON_PAD)

    # The lake bowl and the island, then flat plazas (each at its mean height, the Orrery at the street level).
    dl = lake_metric(X, Y)
    H = np.minimum(H, lake_profile(dl, X, Y))
    H = np.where(dl < 0, np.maximum(H, island_profile(X, Y)), H)
    plazas, centres = [], []
    for (px, py), r0, level in ((plan.ORRERY, 45.0, PLAZA), (plan.WELL, 30.0, None), (plan.SPIRE, 60.0, None),
                                (plan.DOCKS_ARENA, 50.0, None)):
        d = np.hypot(X - px, Y - py)
        if level is None:
            level = float(H[d <= r0].mean())
        plazas.append((d, level, r0))
        centres.append((px, py, level, r0))
        H = cut_fill(H, d, level, r0)

    # Roads: cut and fill to their centreline, level across.
    lines = road_lines()
    profiles = _profiles(H, lines, centres)
    H, road_d, road_hw = _apply_roads(H, X, Y, profiles)

    # What the roads must not change: plazas exactly flat, the lake bowl, the island, the moat.
    for d, level, r0 in plazas:
        H = cut_fill(H, d, level, r0)
    H = np.minimum(H, lake_profile(dl, X, Y))
    H = np.where(dl < 0, np.maximum(H, island_profile(X, Y)), H)
    H = np.where(rf <= FOUNDRY_APRON, lf, H)          # the yard itself; its batter yields to the road below it
    H = np.maximum(H, lf - YARD_EMBANKMENT * np.maximum(rf - FOUNDRY_APRON, 0))   # ...down to the road at 38.7 deg
    moat = (sstep(MOAT_IN - MOAT_EDGE, MOAT_IN + MOAT_EDGE, rf) *
            (1 - sstep(MOAT_IN + MOAT_W - MOAT_EDGE, MOAT_IN + MOAT_W + MOAT_EDGE, rf)))
    H = np.where(rf < FOUNDRY_APRON, lf - MOAT_DEPTH * moat, H)
    # The moat's only way out: a ramp notch north (+x) up its outer wall, so a fall is not a trap. The inner
    # wall stays 6 m sheer all round, so the yard is reached only by the crane bridge (south-west).
    # It climbs at NOTCH_SLOPE until it meets the ground, through the apron and whatever lies beyond it.
    along, across = X - fx, np.abs(Y - fy)
    notch = (1 - sstep(2.2, NOTCH_HALF, across)) * (along > MOAT_IN + 4) * (along < NOTCH_END)
    ramp_z = lf - MOAT_DEPTH + NOTCH_SLOPE * np.maximum(along - MOAT_IN - MOAT_W, 0)
    H = np.where(notch > 0, H * (1 - notch) + np.minimum(H, ramp_z) * notch, H)

    # Beyond the walk limit a berm too steep to climb, back down to the window frame at the strip's edge; at
    # each end cap a berm too. Where the land at the limit lies far below the berm (the Foundry's terraces and its
    # yard, quarried 22 m into the slope), the berm rises from the limit as a rock face at BERM_FACE, which once
    # stood up as a sheer 25 m terrain wall behind the parapet. The face stays far too steep to climb, and by the
    # strip's edge it is above the berm everywhere, so the edge still meets the window frame.
    rim = drum_z(Y) + 16.0 * sstep(301, 315, ay) * (1 - sstep(332, HALF_Y, ay))
    j_east, j_west = int(round((WALK + HALF_Y) / CELL)), int(round((HALF_Y - WALK) / CELL))
    limit = np.where(Y > 0, H[:, j_east][:, None], H[:, j_west][:, None])
    berm = np.minimum(rim, limit + BERM_FACE * np.maximum(ay - WALK - .5, 0))
    w = sstep(299.5, 303.0, ay)
    H = H * (1 - w) + np.maximum(H, berm) * w
    H = np.where(ay >= 318, H * (1 - sstep(318, 324, ay)) + berm * sstep(318, 324, ay), H)
    H = H + 18.0 * sstep(END_BERM, HALF_X - 2.0, np.abs(X))

    G.update(H=H, slope_base=slope, road_d=road_d, road_hw=road_hw, profiles=profiles, lines=lines, lake_d=dl,
             moat=moat * (rf < FOUNDRY_APRON), plaza_levels=[(lv, r0) for _, lv, r0 in plazas], foundry_level=lf)
    return G


# ---------------------------------------------------------------- terrain colour

def _colour(G):
    X, Y, H = G['X'], G['Y'], G['H']
    ay = np.abs(Y)
    gx, gy = np.gradient(H, CELL)
    slope = np.hypot(gx, gy)
    n1 = fbm(X, Y, 31, 4, 1 / 60.0)
    n2 = fbm(X, Y, 32, 3, 1 / 9.0)
    n3 = fbm(X, Y, 33, 4, 1 / 130.0)
    n4 = fbm(X, Y, 34, 3, 1 / 25.0)
    # Green grass (author, 2026-11-08; it was golden): deeper green in the low wet ground, a yellower green on the dry
    # upper slopes and the Orchard Rim.
    dry = np.clip(.35 + .9 * n3 + .5 * sstep(120, 290, ay) + .35 * region_w('Orchard Rim', X, Y), 0, 1)
    c = mix(GREEN_GRASS, GREEN_MOSS, dry * .85) * (.94 + .08 * n2)[..., None]
    c = mix(c, GREEN_PALE, .12 * np.clip(n4 * 2 - .3, 0, 1))
    # Crop terraces: black soil on the Terraces' pads (their grassy risers stay green).
    ter = G['terraces']['Terraces']
    soil_w = np.clip(ter['w'] * 1.4 - .3, 0, 1) * (ter['ramp'] < .02) * (G['road_d'] > G['road_hw'] + 1.5)
    c = mix(c, grey(.045) * (1 + .3 * n2)[..., None], soil_w * .95)
    # The Old Quarter: dark earth and grey rubble breaking up its overgrown lawns.
    oq = region_w('Old Quarter', X, Y)
    c = mix(c, grey(.05), oq * np.clip(n4 * 2.2 - .2, 0, 1) * .8)
    c = mix(c, grey(.22), oq * np.clip(n1 * 2.5 - .9, 0, 1) * .7)
    # The Foundry: black slag and soot with grey ash, everywhere it works. Its edge wanders about 20 m with the noise
    # (soot drifts and spoil heaps), so the district does not end in a drawn circle.
    fcx, fcy, fr, fb = plan.REGIONS['Foundry']
    fw = np.clip(sstep(0, 1, 1 - (np.hypot(X - fcx, Y - fcy) - fr + 24.0 * n1) / fb) * 1.6 - .4, 0, 1)
    slag = mix(grey(.018), grey(.17), np.clip(n4 * 2 + .1, 0, 1) * .6) * (1 + .25 * n2)[..., None]
    c = mix(c, slag, fw)
    c = mix(c, grey(.012), G['moat'])
    # The docks: grey metal deck in plates about 8 m square.
    dw = np.clip(region_w('Docks', X, Y) * 1.5 - .3, 0, 1)
    plate = .2 + .05 * np.sin(np.floor(X / 8.0) * 12.9898 + np.floor(Y / 8.0) * 78.233) ** 2
    c = mix(c, np.repeat(plate[..., None], 3, -1) * (1 + .12 * n2)[..., None], dw)
    # The lake: white sand at the shore and the island, black silt under the water.
    near_lake = G['lake_d'] < 60
    sand = (1 - sstep(.9, 1.6, H)) * sstep(-1.0, -.2, H) * near_lake
    c = mix(c, mix(IVORY, WHITE, .5 + .4 * n2), sand)
    silt = sstep(-.2, -1.2, H) * near_lake
    c = mix(c, grey(.03) * (1 + .4 * n2)[..., None], silt)
    # Steep ground: white and grey rock.
    rock = sstep(.62, .95, slope)
    rockc = mix(WHITE_COOL, ASH, np.clip(.5 + n4 * 1.4, 0, 1)) * (.7 + .15 * n2)[..., None]
    c = mix(c, rockc, rock)
    # Plazas, roads and the town's lanes: white stone, worn grey at the road edges.
    px, py = plan.ORRERY
    rp = np.hypot(X - px, Y - py)
    ring = .5 + .5 * np.cos(rp / 7.5 * 2 * math.pi)
    orrery = mix(WHITE, IVORY, ring * .6) * np.where(rp > 43.5, .72, 1.0)[..., None]
    plaza = 1 - sstep(44.5, 46.5, rp)
    c = mix(c, orrery, plaza)
    sx, sy = plan.SPIRE
    spire = 1 - sstep(58.5, 61.0, np.hypot(X - sx, Y - sy))
    c = mix(c, mix(WHITE_COOL, WHITE, .5 + .5 * n2), spire)
    road = 1 - sstep(G['road_hw'] - .4, G['road_hw'] + .6, G['road_d'])
    worn = mix(WHITE, ASH, .25 * sstep(G['road_hw'] - 2.0, G['road_hw'], G['road_d']) + .1 * np.clip(n4, 0, 1))
    c = mix(c, worn * (.9 + .08 * n2)[..., None], road * (1 - dw * .6))
    lane = (1 - sstep(1.2, 2.2, G['lane_d'])) * (1 - road)
    c = mix(c, mix(WHITE, IVORY, .3) * .92, lane)
    # Occlusion: darker in hollows and at the foot of every riser, gently on gold, freely on stone.
    cav = np.clip((H - blur(H, 3)) * .35, -.4, .15)
    goldish = np.clip(1 - rock - road - silt - sand - fw - dw, 0, 1)
    k = 1 + cav * (1 - .6 * goldish)
    c = c * np.clip(k, .55, 1.1)[..., None]
    out = np.ones(H.shape + (4,))
    out[..., :3] = snap(c)
    # What each cell is made of, for the layout (vegetation grows only on the golden grass).
    G['surface'] = {'road': road, 'lane': lane, 'plaza': np.maximum(plaza, spire), 'soil': soil_w, 'slag': np.maximum(fw, G['moat']),
                    'deck': dw, 'sand': sand, 'silt': silt, 'rock': rock}
    return out


_GRID = {}


def grid():
    """The floor: height (float32 metres) and colour on the 801 x 351 grid, plus the masks the layout reads."""
    if not _GRID:
        lanes = stair_lanes()
        G = _shape()
        G['lanes'] = lanes
        segs = [((x, side * y0), (x, side * y1)) for _, side, x, y0, y1 in lanes]
        G['lane_d'] = nearest_on(segs, G['X'], G['Y'])[0] if segs else np.full(G['H'].shape, 1e9)
        G['colour'] = _colour(G)
        G['H'] = G['H'].astype(np.float32)
        gx, gy = np.gradient(G['H'].astype(np.float64), CELL)
        G['slope'] = np.hypot(gx, gy)
        _GRID.update(G)
    return _GRID


def height_at(x, y):
    return sample(grid()['H'], x, y)


# ---------------------------------------------------------------- mesh helpers

def drum_point(x, theta, r=R):
    """A point on the drum's inner surface (theta radians: 0 straight down, growing toward +y), r from the axis."""
    return np.array([x, r * math.sin(theta), AXIS_Z - r * math.cos(theta)])


def axis_up(theta):
    """Unit vector from the drum's surface toward the axis: 'up' for anything standing on it."""
    return np.array([0.0, -math.sin(theta), math.cos(theta)])


def _merge(part, tmp, origin, forward, up):
    """Appends a temporary part built in local axes (x forward, y right, z up) placed by toolkit.oriented."""
    if not tmp.v:
        return
    v = oriented(np.asarray(tmp.v), origin, forward, up)
    _append(part, tmp, v, False)


def _append(part, tmp, verts, flip):
    base = len(part.v)
    part.v.extend(np.asarray(verts, np.float64).tolist())
    part.c.extend(tmp.c)
    for f, m, s in zip(tmp.f, tmp.m, tmp.s):
        f = [base + i for i in f]
        part.f.append(f[::-1] if flip else f)
        part.m.append(m)
        part.s.append(s)


def _map(part, tmp, matrix, offset):
    """Appends tmp transformed by a 3x3 matrix and offset; a mirroring matrix reverses the faces so they stay
    wound outward."""
    m = np.asarray(matrix, np.float64)
    v = np.asarray(tmp.v, np.float64) @ m.T + np.asarray(offset, np.float64)
    _append(part, tmp, v, np.linalg.det(m) < 0)


def _beam(part, a, b, width, depth, up, colour, slot, bevel=.1):
    """A bevelled beam whose outer face runs along a-b, `depth` deep toward up (the drum's ribs and frames)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    up = np.asarray(up, np.float64) / np.linalg.norm(up)
    tmp = Part(part.name, part.slots)
    bevel_box(tmp, (0, 0, 0), (np.linalg.norm(b - a) / 2, width / 2, depth / 2), colour, slot, bevel)
    _merge(part, tmp, (a + b) / 2 + up * depth / 2, b - a, up)


def _quad_facing(part, pts, want, colour, slot, smooth=False):
    """One quad wound so its front faces `want`."""
    pts = np.asarray(pts, np.float64)
    n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
    face = [0, 1, 2, 3] if np.dot(n, want) >= 0 else [3, 2, 1, 0]
    part.add(pts, [face], colour, slot, smooth)


def _solid(part, pts, faces, colour, slot, smooth=False):
    """A small closed solid from any faces: each face turned away from the solid's centre."""
    pts = np.asarray(pts, np.float64)
    centre = pts.mean(0)
    out = []
    for face in faces:
        n = np.cross(pts[face[1]] - pts[face[0]], pts[face[2]] - pts[face[0]])
        out.append(list(face) if np.dot(n, pts[face].mean(0) - centre) >= 0 else list(face)[::-1])
    part.add(pts, out, colour, slot, smooth)


def jitter_grey(rng, lo, hi):
    return grey(float(rng.uniform(lo, hi)))


# ---------------------------------------------------------------- terrain tiles and water

TILE_X, TILE_Y = (NX - 1) // plan.TILES_X, (NY - 1) // plan.TILES_Y   # 100 x 175 cells a tile


@functools.lru_cache(maxsize=1)
def vertex_normals():
    """Unit normals of the whole floor grid (central differences, Unreal axes), shape (NX, NY, 3)."""
    gx, gy = np.gradient(grid()['H'].astype(np.float64), CELL)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def terrain_tile(k):
    """SM_CD_Terrain_<i>_<j> (k = i * TILES_Y + j): one tile of the floor grid in world metres. Neighbouring tiles
    share their edge rows exactly, so the seams match. The Part carries `normals` from the whole grid, which the
    builder sets as custom normals: Blender would average only the tile's own faces at its edge, and where a seam
    crosses the moat or a terrace riser that turned the edge's normals by up to 18 degrees, a line in the light."""
    i, j = divmod(k, plan.TILES_Y)
    G = grid()
    xs, ys = slice(i * TILE_X, (i + 1) * TILE_X + 1), slice(j * TILE_Y, (j + 1) * TILE_Y + 1)
    px, py, ph, pc = G['X'][xs, ys], G['Y'][xs, ys], G['H'][xs, ys].astype(np.float64), G['colour'][xs, ys]
    mx, my = px.shape
    p = Part('SM_CD_Terrain_%d_%d' % (i, j), ('CN_Ground',))
    idx = np.arange(mx * my).reshape(mx, my)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    faces = np.stack([a, b, c, d], 1).tolist()   # counter-clockwise seen from above: fronts face up
    p.add(np.stack([px.ravel(), py.ravel(), ph.ravel()], 1), faces, pc.reshape(-1, 4), 0, True)
    p.normals = vertex_normals()[xs, ys].reshape(-1, 3)   # vertex order of p.v
    return p


def water():
    """SM_CD_Water: the lake's surface at the water level over the rectangle the README names."""
    p = Part('SM_CD_Water', ('CN_Water',))
    xs, ys = np.linspace(-70, 150, 45), np.linspace(-60, 100, 33)
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    idx = np.arange(gx.size).reshape(gx.shape)
    faces = np.stack([idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()], 1).tolist()
    p.add(np.stack([gx.ravel(), gy.ravel(), np.full(gx.size, WATER)], 1), faces, BLUE_ICE, 0, True)
    return p


# ---------------------------------------------------------------- the window strips

WINDOW_STRIPS = (30.0, 150.0, 270.0)        # first theta of each window strip, degrees
RIB_ARC, RIB_X = 7.5, 40.0                  # ribs every 7.5 degrees of arc, frames every 40 m along the drum


def windows():
    """SM_CD_Windows: the three long windows between the land strips. Light-blue glass panes between dark steel
    ribs: ribs along the drum every 7.5 degrees, frames around it every 40 m, heavier frames every 200 m and at
    the land edges, where the window meets the ground (its sill)."""
    p = Part('SM_CD_Windows', ('CN_Metal', 'CN_Glass'))
    rng = np.random.default_rng(3101)
    n_arc = int(round(math.degrees(plan.WINDOW) / RIB_ARC))
    xs = np.arange(-HALF_X, HALF_X + 1e-6, RIB_X)
    xs[0], xs[-1] = -HALF_X + 1.5, HALF_X - 1.5      # the end frames stand just inside the caps
    for t0 in WINDOW_STRIPS:
        th = [math.radians(t0 + RIB_ARC * k) for k in range(n_arc + 1)]
        for a in range(n_arc):
            mid = (th[a] + th[a + 1]) / 2
            for b in range(len(xs) - 1):
                pts = [drum_point(xs[b], th[a]), drum_point(xs[b + 1], th[a]), drum_point(xs[b + 1], th[a + 1]), drum_point(xs[b], th[a + 1])]
                tint = BLUE_PALE if rng.uniform() < .82 else WHITE_COOL
                _quad_facing(p, pts, axis_up(mid), tint, 1)
        for k, t in enumerate(th):
            sill = k in (0, n_arc)
            width, depth = (3.4, 4.8) if sill else (1.4, 2.6)
            for b in range(len(xs) - 1):
                tone = jitter_grey(rng, .045, .075) if sill else jitter_grey(rng, .06, .13)
                _beam(p, drum_point(xs[b], t), drum_point(xs[b + 1], t), width, depth, axis_up(t), tone, 0, .14)
        for b, x in enumerate(xs):
            major = b % 5 == 0 or b == len(xs) - 1
            width, depth = (2.8, 4.2) if major else (1.0, 2.0)
            for a in range(n_arc):
                tone = jitter_grey(rng, .04, .07) if major else jitter_grey(rng, .07, .14)
                _beam(p, drum_point(x, th[a]), drum_point(x, th[a + 1]), width, depth, axis_up((th[a] + th[a + 1]) / 2), tone, 0, .1)
    return p


# ---------------------------------------------------------------- the upper lands

UPPER_LANDS = (('SM_CD_UpperLandE', 90.0, 5101), ('SM_CD_UpperLandW', 210.0, 5202))
FIELD_KINDS = (  # weight, colour, slot-free name; fields read as patches of colour at 700-1400 m
    (.31, 'wheat'), (.24, 'pasture'), (.11, 'straw'), (.13, 'fallow'), (.06, 'poppy'), (.05, 'blossom'), (.10, 'orchard'))


def _house_local(rng, slots_part, width, depth, wall, rise, lit):
    """A small white house with a red gable roof in local axes (ground z 0, front +x): walls and gables as one
    pentagonal prism, two roof slabs with overhang, sometimes a chimney and lit windows."""
    t = Part(slots_part.name, slots_part.slots)
    w2, d2 = width / 2, depth / 2
    ring = [(-w2, 0), (w2, 0), (w2, wall), (0, wall + rise), (-w2, wall)]
    pts = [(x, y, z) for x in (-d2, d2) for (y, z) in ring]
    faces = [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]] + [[i, (i + 1) % 5, 5 + (i + 1) % 5, 5 + i] for i in range(1, 5)]
    _solid(t, pts, faces, shade(WHITE, rng.uniform(.88, 1.0)), 'CN_White')   # no floor face: it stands in the ground
    o, th = .45, .22
    slope = rise / w2
    for side in (-1, 1):
        c = []
        for top in (0, 1):
            for yb in (0, 1):
                for xb in (0, 1):
                    x = -(d2 + o) if xb == 0 else d2 + o
                    y = 0.0 if yb == 0 else side * (w2 + o)
                    z = wall + rise if yb == 0 else wall - o * slope
                    c.append((x, y, z + (th if top else 0)))
        hexa(t, c, shade(RED, rng.uniform(.85, 1.0)), 'CN_Red')
    if rng.uniform() < .45:
        cx = rng.uniform(-d2 * .5, d2 * .5)
        box(t, (cx, w2 * .45, wall + rise * .55 + .7), (.35, .35, .9), shade(WHITE, .8), 'CN_White')
    if lit:
        for k in range(2):
            y0 = (-w2 * .45) if k == 0 else (w2 * .2)
            t.add([(d2 + .03, y0, wall * .35), (d2 + .03, y0 + w2 * .3, wall * .35), (d2 + .03, y0 + w2 * .3, wall * .65), (d2 + .03, y0, wall * .65)],
                  [[0, 1, 2, 3]], LIGHT_WARM if rng.uniform() < .6 else LIGHT_GOLD, 'CN_Glow', False)
    return t


def _tree_local(part, rng, kind, size):
    """A distant tree in local axes: a short dark trunk and a faceted canopy (gold-free: red, white or black)."""
    t = Part(part.name, part.slots)
    trunk = size * .35
    tube(t, [(0, 0, -.3), (0, 0, trunk)], size * .05, shade(CHARCOAL, 1.0), 'CN_Black', 4, cap=False)
    sides = 6
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + rng.uniform(0, 1)
    if kind == 'conifer':
        r, lo, hi = size * .28, trunk * .6, size * 1.15
        ring = [(math.cos(a) * r, math.sin(a) * r, lo) for a in ang]
        pts = ring + [(0, 0, hi), (0, 0, lo - .2)]
        colour = shade(CHARCOAL, rng.uniform(.8, 1.6))
    else:
        r, mid = size * .42, trunk + size * .38
        ring = [(math.cos(a) * r * rng.uniform(.85, 1.1), math.sin(a) * r * rng.uniform(.85, 1.1), mid + rng.uniform(-.3, .3)) for a in ang]
        pts = ring + [(0, 0, mid + size * .42), (0, 0, trunk * .8)]
        colour = {'red': shade(RED_DEEP, rng.uniform(.85, 1.25)), 'white': shade(WHITE_PURE, rng.uniform(.9, 1.0)),
                  'fruit': shade(WHITE, rng.uniform(.9, 1.05))}[kind]
    faces = [[i, (i + 1) % sides, sides] for i in range(sides)] + [[(i + 1) % sides, i, sides + 1] for i in range(sides)]
    _solid(t, pts, faces, colour, 'CN_Leaf')
    return t


def _upper_land(name, t0, seed):
    """SM_CD_UpperLandE / W: a land strip overhead, facing the axis. Fields in patches of gold, black fallow, red
    and white flowers, orchards; white roads and lanes; villages of white houses with red roofs at the crossings
    and farmsteads among the fields; avenues, woods and orchard rows. Modelled to read at 700-1400 m."""
    p = Part(name, ('CN_Ground', 'CN_White', 'CN_Red', 'CN_Leaf', 'CN_Black', 'CN_Glow'))
    rng = np.random.default_rng(seed)
    span = math.radians(math.degrees(plan.STRIP) * 2)
    tc = math.radians(t0) + span / 2
    S = R * span / 2                                   # half the strip's arc length (366.5 m)
    lanes = [x + rng.uniform(-14, 14) for x in np.arange(-720.0, 721.0, 160.0)]
    rings = (-190.0, 190.0)
    S_ROAD, S_SIDE, X_LANE = 4.0, 2.5, 2.5

    def relief(x, s):
        x, s = np.asarray(x, np.float64), np.asarray(s, np.float64)
        berm = 14.0 * sstep(300, 335, np.abs(s)) * (1 - sstep(345, S, np.abs(s)))
        ends = 16.0 * sstep(HALF_X - 20, HALF_X - 2, np.abs(x))
        return 3.0 * fbm(x, s + seed, 7, 4, 1 / 210.0) * (1 - sstep(330, S, np.abs(s))) + berm + ends

    def point(x, s, lift=0.0):
        th = tc + s / R
        r = R - float(relief(x, s)) - lift
        return np.array([x, r * math.sin(th), AXIS_Z - r * math.cos(th)]), th

    xg = set(np.round(np.arange(-HALF_X, HALF_X + 1e-6, 20.0), 3))
    for lx in lanes:
        xg |= {round(lx - X_LANE, 3), round(lx + X_LANE, 3)}
    xg = np.array(sorted(xg))
    sg = set(np.round(np.linspace(-S, S, 61), 3))
    sg |= {-S_ROAD, S_ROAD} | {round(r + d, 3) for r in rings for d in (-S_SIDE, S_SIDE)}
    sg = np.array(sorted(sg))
    # Fields: each parcel between lanes and roads is cut into strips along the grid lines.
    edges_x = [-HALF_X] + lanes + [HALF_X]
    kinds = np.array([k for _, k in FIELD_KINDS])
    weights = np.array([w for w, _ in FIELD_KINDS])

    def field_of(x, s):
        px = int(np.searchsorted(edges_x, x))
        band = int(np.searchsorted((-S, rings[0], 0.0, rings[1], S), s))
        h = (px * 92821 + band * 68917 + seed * 131) % 1000003
        width = (2 + h % 3) * 20.0
        depth = (2 + (h // 7) % 3) * R * span / 60
        fx = int((x - edges_x[max(px - 1, 0)]) // width)
        fs = int((s + S) // depth)
        r2 = np.random.default_rng(h * 31 + fx * 7919 + fs * 104729)
        return kinds[np.searchsorted(np.cumsum(weights) / weights.sum(), r2.uniform())], r2.uniform()

    def on_road(x, s):
        if abs(s) < S_ROAD or any(abs(abs(s) - abs(r)) < S_SIDE and np.sign(s) == np.sign(r) for r in rings):
            return True
        return abs(s) < 300 and any(abs(x - lx) < X_LANE for lx in lanes)

    field_colour = {'wheat': (GOLD_STRAW, .92, 1.04), 'pasture': (GREEN_GRASS, .9, 1.05), 'straw': (GOLD_PALE, .82, .92),
                    'fallow': (CHARCOAL, .8, 1.3), 'poppy': (RED, .9, 1.15), 'blossom': (WHITE_PURE, .85, .95),
                    'orchard': (GREEN_GRASS, .95, 1.08)}
    orchards = []
    for a in range(len(xg) - 1):
        for b in range(len(sg) - 1):
            x0, x1, s0, s1 = xg[a], xg[a + 1], sg[b], sg[b + 1]
            xm, sm = (x0 + x1) / 2, (s0 + s1) / 2
            if on_road(xm, sm):
                colour = shade(WHITE, rng.uniform(.82, .95))
            elif abs(sm) > 300 or abs(xm) > HALF_X - 20:
                colour = shade(WHITE_COOL if rng.uniform() < .5 else ASH, rng.uniform(.6, 1.0))   # rock on the berms
            else:
                kind, u = field_of(xm, sm)
                base, lo, hi = field_colour[kind]
                colour = shade(base, lo + (hi - lo) * u)
                if kind == 'orchard':
                    orchards.append((x0, x1, s0, s1))
            corners = [point(x0, s0)[0], point(x1, s0)[0], point(x1, s1)[0], point(x0, s1)[0]]
            _quad_facing(p, corners, axis_up(tc + sm / R), colour, 'CN_Ground', True)

    def put(local, x, s, facing):
        if abs(x) > HALF_X - 24:                      # nothing stands in the end berm or through a cap
            return
        pos, th = point(x, s)
        up = axis_up(th)
        tangent = np.array([0.0, math.cos(th), math.sin(th)])
        fwd = np.array([1.0, 0, 0]) * math.cos(facing) + tangent * math.sin(facing)
        _merge(p, local, pos - up * .3, fwd, up)

    def house(x, s, facing):
        lit = rng.uniform() < .55
        local = _house_local(rng, p, rng.uniform(6, 9.5), rng.uniform(5, 8), rng.uniform(3.6, 5.8), rng.uniform(2.2, 3.4), lit)
        put(local, x, s, facing)

    # Villages at every other lane's crossing with the main road; farmsteads among the fields.
    for k, lx in enumerate(lanes):
        if k % 2 == seed % 2:
            continue
        for side in (-1, 1):
            for x in np.arange(lx - 72, lx + 73, 13.0):
                if abs(x - lx) < 9:
                    continue
                for row in (11.0, 25.0):
                    if rng.uniform() < .78:
                        house(x + rng.uniform(-2, 2), side * (row + rng.uniform(-1.5, 1.5)), math.pi / 2 * (-side) + rng.uniform(-.05, .05))
            for s in np.arange(-84, 85, 12.0):
                if abs(s) < 34:
                    continue
                if rng.uniform() < .7:
                    house(lx + side * (10 + rng.uniform(-1, 1.5)), s + rng.uniform(-2, 2), (0.0 if side < 0 else math.pi) + rng.uniform(-.05, .05))
    for _ in range(46):
        x, s = rng.uniform(-760, 760), rng.uniform(-280, 280)
        if on_road(x, s) or min(abs(x - lx) for lx in lanes) < 14 or abs(s) < 14:
            continue
        facing = rng.uniform(0, 2 * math.pi)
        for n in range(int(rng.integers(1, 4))):
            house(x + n * 11 * math.cos(facing + 1.6), s + n * 11 * math.sin(facing + 1.6), facing)

    def tree(x, s, kind, size):
        put(_tree_local(p, rng, kind, size), x, s, rng.uniform(0, 2 * math.pi))

    # Avenues of red trees along the main road, orchard rows, woods of black conifers and red groves.
    for x in np.arange(-780, 781, 15.0):
        for side in (-1, 1):
            if rng.uniform() < .8 and not on_road(x, side * 7.5) and min(abs(x - lx) for lx in lanes) > 6:
                tree(x + rng.uniform(-2, 2), side * 7.5, 'red', rng.uniform(7, 10))
    for x0, x1, s0, s1 in orchards:   # one tree a grid cell reads as rows at this distance
        tree((x0 + x1) / 2 + rng.uniform(-2, 2), (s0 + s1) / 2 + rng.uniform(-1, 1), 'fruit', rng.uniform(4.5, 5.5))
    for _ in range(20):
        cx, cs = rng.uniform(-760, 760), rng.uniform(-290, 290)
        kind = 'conifer' if rng.uniform() < .55 else ('red' if rng.uniform() < .7 else 'white')
        for _ in range(int(rng.integers(16, 34))):
            x, s = cx + rng.normal(0, 22), cs + rng.normal(0, 16)
            if abs(s) < 296 and abs(x) < HALF_X - 22 and not on_road(x, s):
                tree(x, s, kind, rng.uniform(8, 12))
    return p


def upper_land_e():
    return _upper_land(*UPPER_LANDS[0])


def upper_land_w():
    return _upper_land(*UPPER_LANDS[1])


# ---------------------------------------------------------------- the end caps

CAP_RINGS = (120.0, 220.0, 330.0, 450.0, 580.0)


def _cap(name, x_cap, inward, north):
    """SM_CD_CapSouth / North: the drum's end walls, discs of radius R around the axis. Built in the cap's own
    axes (the disc in local x-y, local x = world y, local y = height above the axis; local z = depth into the
    drum), then turned into place. Black and white plating in concentric bands, raised steel rings and spokes,
    rows of gold and light-blue lights, a hub where the Spine meets the cap (the north cap's is the Spindle, with
    its docking arms), and at the floor a docking bay (north) or the Wellspring's white arch (south). The disc
    reaches the drum circle, so its bottom closes the floor behind the end berm."""
    slots = ('CN_Metal', 'CN_White', 'CN_Gold', 'CN_Glow') + (('CN_Black',) if north else ())
    p = Part(name, slots)
    t = Part(name, slots)
    rng = np.random.default_rng(7700 + int(north))
    hub = 150.0 if north else 60.0
    radii = (hub,) + tuple(r for r in CAP_RINGS if r > hub + 40) + (R,)
    # The back plate behind everything (so no seam shows space), facing into the drum.
    lathe(t, [(R, 0.0)] + [(r, 0.0) for r in reversed(radii[:-1])], shade(CHARCOAL, .9), 'CN_Metal', 144)
    # Plating: panels in each band between the rings, black or white, grimier toward the floor.
    white_share = .35 if north else .62
    for band in range(len(radii) - 1):
        ra, rb = radii[band] + 3.5, radii[band + 1] - 3.5
        n_sec = 12 * (band + 1)
        for k in range(n_sec):
            a0, a1 = 2 * math.pi * k / n_sec, 2 * math.pi * (k + 1) / n_sec
            gap = .5
            white = rng.uniform() < white_share
            depth = rng.uniform(.6, 1.8)
            sub = max(1, int(math.ceil((a1 - a0) * (ra + rb) / 2 / 40.0)))
            for m in range(sub):
                b0 = a0 + (a1 - a0) * m / sub + (gap / ra if m == 0 else 0)
                b1 = a0 + (a1 - a0) * (m + 1) / sub - (gap / ra if m == sub - 1 else 0)
                low = .5 * (math.sin(b0) + math.sin(b1))                    # -1 at the floor
                grime = .72 + .28 * (1 + low) / 2
                colour = shade(WHITE if white else SLATE, grime * rng.uniform(.9, 1.05))
                pts = [(r * math.cos(a), r * math.sin(a), z) for z in (.05, depth) for a in (b0, b1) for r in (ra + gap, rb - gap)]
                hexa(t, pts, colour, 'CN_White' if white else 'CN_Metal')
    # Raised rings (chamfered box sections) and spokes between them.
    for k, r in enumerate(radii[:-1]):
        w, d = (6.0, 4.5) if k else (9.0, 7.0)
        prof = [(r + w / 2, 0), (r + w / 2, d - .8), (r + w / 2 - .8, d), (r - w / 2 + .8, d), (r - w / 2, d - .8), (r - w / 2, 0)]
        lathe(t, prof, GOLD if k == 0 else shade(SLATE, rng.uniform(.6, .9)), 'CN_Gold' if k == 0 else 'CN_Metal', 144)
    lathe(t, [(R, 9.0), (R - 1.2, 10.0), (R - 12, 10.0), (R - 12, 0)], shade(CHARCOAL, 1.2), 'CN_Metal', 192)   # the rim
    for k in range(12):
        a = 2 * math.pi * (k + .5) / 12
        for band in range(len(radii) - 1):
            ra, rb = radii[band] + 3.0, radii[band + 1] - (12.0 if band == len(radii) - 2 else 3.0)
            length = rb - ra
            box(t, ((ra + rb) / 2 * math.cos(a), (ra + rb) / 2 * math.sin(a), 2.6), (length / 2, 3.5, 2.6), shade(SLATE, .8), 'CN_Metal', math.degrees(a))
    # Lights: a row on every ring, gold and light blue by turns; larger light-blue ones where spokes cross rings.
    for k, r in enumerate(radii[1:-1]):
        colour = LIGHT_GOLD if k % 2 == 0 else LIGHT_BLUE
        for m in range(72):
            a = 2 * math.pi * (m + .25) / 72
            box(t, (r * math.cos(a), r * math.sin(a), 4.7), (.7, .9, .25), colour, 'CN_Glow', math.degrees(a))
        for m in range(12):
            a = 2 * math.pi * (m + .5) / 12
            box(t, (r * math.cos(a), r * math.sin(a), 5.4), (1.8, 1.8, .3), LIGHT_BLUE, 'CN_Glow', math.degrees(a))
    for m in range(96):
        a = 2 * math.pi * m / 96
        box(t, ((R - 6) * math.cos(a), (R - 6) * math.sin(a), 10.2), (1.0, 1.4, .25), LIGHT_GOLD if m % 2 else LIGHT_BLUE, 'CN_Glow', math.degrees(a))
    # The hub where the Spine meets the cap.
    if north:
        spindle = [(150, 0), (150, 12), (128, 16), (118, 44), (90, 50), (78, 92), (52, 98), (44, 128), (22, 134), (12, 142)]
        lathe(t, spindle, shade(SLATE, .7), 'CN_Metal', 64)
        for z, r in ((14.0, 139.0), (52.0, 86.0), (100.0, 49.0)):
            lathe(t, [(r + 1.5, z - 1.2), (r + 1.5, z + 1.2)], GOLD, 'CN_Gold', 64)
            for m in range(36):
                a = 2 * math.pi * m / 36
                box(t, ((r + 1.7) * math.cos(a), (r + 1.7) * math.sin(a), z), (.3, 1.2, .8), LIGHT_BLUE, 'CN_Glow', math.degrees(a))
        for k in range(6):
            a = 2 * math.pi * k / 6 + math.pi / 6
            ca, sa = math.cos(a), math.sin(a)
            box(t, (ca * 150, sa * 150, 70), (34, 4, 4), shade(SLATE, .9), 'CN_Metal', math.degrees(a))       # docking arm
            box(t, (ca * 186, sa * 186, 70), (6, 14, 9), shade(WHITE, .85), 'CN_White', math.degrees(a))      # its cradle
            box(t, (ca * 193, sa * 193, 70), (.4, 9, 1.2), LIGHT_GOLD, 'CN_Glow', math.degrees(a))
        lathe(t, [(14.5, 140), (14.5, 146), (7.2, 146)], GOLD, 'CN_Gold', 32)    # the collar the Spine runs into
    else:
        lathe(t, [(60, 0), (60, 9), (50, 13), (44, 30), (22, 34), (12, 38)], shade(WHITE, .9), 'CN_White', 48)
        lathe(t, [(45.5, 22), (45.5, 26)], GOLD, 'CN_Gold', 48)
        lathe(t, [(13.5, 37), (13.5, 42), (7.2, 42)], GOLD, 'CN_Gold', 32)
        for m in range(24):
            a = 2 * math.pi * m / 24
            box(t, (46 * math.cos(a), 46 * math.sin(a), 18), (.4, 2.0, 1.2), LIGHT_GOLD, 'CN_Glow', math.degrees(a))
    # At the floor (local y = height above the axis: the floor is near y = -R).
    floor_y = FLOOR - AXIS_Z
    if north:
        # A docking bay above the end berm: a black frame, its lit interior, gold lights along the frame.
        y0, y1, half = floor_y + 26.0, floor_y + 92.0, 70.0
        box(t, (0, (y0 + y1) / 2, 2.2), (half, (y1 - y0) / 2, .15), shade(LIGHT_BLUE, .35), 'CN_Glow')   # proud of the plating
        for (cx, cy, hx, hy) in ((0, y1 + 4, half + 8, 4), (0, y0 - 3, half + 8, 3), (-half - 4, (y0 + y1) / 2, 4, (y1 - y0) / 2 + 7),
                                 (half + 4, (y0 + y1) / 2, 4, (y1 - y0) / 2 + 7)):
            bevel_box(t, (cx, cy, 6.0), (hx, hy, 6.0), shade(CHARCOAL, 1.1), 'CN_Black', .6)
        for m in range(29):
            x = -half + m * (2 * half / 28)
            box(t, (x, y1 + 4, 12.3), (.8, .8, .3), LIGHT_GOLD, 'CN_Glow')
            box(t, (x, y0 - 3, 12.3), (.8, .8, .3), LIGHT_BLUE, 'CN_Glow')
        for m in range(1, 6):
            x = -half + m * (2 * half / 6)
            box(t, (x, (y0 + y1) / 2, 3.8), (1.2, (y1 - y0) / 2, 1.4), shade(SLATE, .6), 'CN_Metal')    # bay ribs
    else:
        # The Wellspring's backdrop: a white arch in relief over the garden, gold lights in its soffit.
        arch_t = Part(name, slots)
        arch(arch_t, (0, 0, 0), 90.0, 80.0, 9.0, 8.0, shade(WHITE, .95), 'CN_White', 0, 20)
        for k in range(16):
            a = math.pi * (k + .5) / 16
            box(arch_t, (0, -math.cos(a) * 44.4, 35 + math.sin(a) * 44.4), (4.2, .6, .6), LIGHT_GOLD, 'CN_Glow')
        # arch local (x depth, y across, z up) -> cap local (x across, y up, z depth); a rotation, winding kept
        _map(t, arch_t, [[0, 1, 0], [0, 0, 1], [1, 0, 0]], (0, floor_y + 18.0, 4.0))
        for side in (-1, 1):
            bevel_box(t, (side * 49.5, floor_y + 18 + 20, 4.0), (5.5, 20.0, 4.0), shade(WHITE, .9), 'CN_White', .4)
    # cap local -> world: x = cap plane + depth inward, y = local x, z = axis + local y.
    _map(p, t, [[0, 0, inward], [1, 0, 0], [0, 1, 0]], (x_cap, 0.0, AXIS_Z))
    return p


def cap_south():
    return _cap('SM_CD_CapSouth', -HALF_X, 1.0, False)


def cap_north():
    return _cap('SM_CD_CapNorth', HALF_X, -1.0, True)


# ---------------------------------------------------------------- the Spine

SPINE_THIRD = 2 * HALF_X / 3        # 533.3 m


def _spine(name, glow):
    """One third of the Spine along local x, centred on the origin: a glowing core in steel collars every 40 m
    (and one at each end, so the thirds meet at a doubled joint), held by eight rails. SpineDim's core is a dull
    grey glow, SpineLit's white."""
    p = Part(name, ('CN_Glow', 'CN_Metal'))
    t = Part(name, p.slots)
    half = SPINE_THIRD / 2
    cylinder(t, (0, 0, -half), 5.6, SPINE_THIRD, glow, 'CN_Glow', 32)
    rng = np.random.default_rng(9 if glow == LIGHT_WHITE else 8)
    stations = list(np.arange(-240.0, 240.1, 40.0)) + [-half + 1.6, half - 1.6]
    for z in stations:
        tone = shade(SLATE, rng.uniform(.45, .8))
        prof = [(5.4, z - 1.6), (6.5, z - 1.6), (7.0, z - 1.1), (7.0, z + 1.1), (6.5, z + 1.6), (5.4, z + 1.6)]   # inner edge in the core
        lathe(t, prof, tone, 'CN_Metal', 32)
        for m in range(8):
            a = 2 * math.pi * (m + .5) / 8
            box(t, (6.95 * math.cos(a), 6.95 * math.sin(a), z), (.1, .45, .45), shade(CHARCOAL, 1.0), 'CN_Metal', math.degrees(a))
    for m in range(8):
        a = 2 * math.pi * m / 8
        tube(t, [(6.15 * math.cos(a), 6.15 * math.sin(a), -half), (6.15 * math.cos(a), 6.15 * math.sin(a), half)], .32,
             shade(CHARCOAL, 1.3), 'CN_Metal', 6)
    # built along local z; turn it to lie along x (a rotation about y, so the winding is kept)
    _map(p, t, [[0, 0, 1], [0, 1, 0], [-1, 0, 0]], (0, 0, 0))
    return p


def spine_dim():
    return _spine('SM_CD_SpineDim', grey(.15))


def spine_lit():
    return _spine('SM_CD_SpineLit', LIGHT_WHITE)


# ---------------------------------------------------------------- the parapets at the walk limit

PARAPET_BAY = 4.8


def _rail(part, a, b, y, half, lo, hi, chamfer, colour):
    """A stone rail from post to post following the ground: (x, z) ends a and b, `half` its half width about y, lo and
    hi its bottom and top above the ends' z, its long edges chamfered (a sharp block under PBR light reads as CG)."""
    c = chamfer
    section = [(-half + c, lo), (half - c, lo), (half, lo + c), (half, hi - c), (half - c, hi), (-half + c, hi),
               (-half, hi - c), (-half, lo + c)]
    pts = [(x, y + v, z + w) for x, z in (a, b) for v, w in section]
    n = len(section)
    faces = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)] + [list(range(n)), list(range(n, 2 * n))]
    _solid(part, pts, faces, colour, 0)


def _parapet(name, y):
    """SM_CD_ParapetW / E: a white stone balustrade along y = -/+ WALK on the terrain: posts with caps every 4.8 m,
    a plinth and a handrail that follow the ground, five turned balusters a bay. Its stone darkens toward the
    ground. Collides (the import gives it collision)."""
    p = Part(name, ('CN_White',))
    G = grid()
    reach = END_BERM - 3.0
    n = int(round(2 * reach / PARAPET_BAY))
    xs = np.linspace(-reach, reach, n + 1)
    g = sample(G['H'].astype(np.float64), xs, np.full_like(xs, y))
    rng = np.random.default_rng(int(abs(y)) + (1 if y > 0 else 0))

    def stone(k):
        return shade(IVORY if rng.uniform() < .4 else WHITE, k * rng.uniform(.94, 1.0))
    for k, (x, z) in enumerate(zip(xs, g)):
        bevel_box(p, (x, y, z + .45), (.25, .25, .75), stone(.86), 0, .03)
        bevel_box(p, (x, y, z + 1.27), (.31, .31, .07), stone(.97), 0, .025)
        if k == n:
            break
        x1, z1 = xs[k + 1], g[k + 1]
        a, b = x + .25, x1 - .25
        za = z + (z1 - z) * (a - x) / (x1 - x)
        zb = z + (z1 - z) * (b - x) / (x1 - x)
        for lo, hi, half, tone in ((-.3, .22, .22, .8), (1.04, 1.2, .17, .98)):
            _rail(p, (a, za), (b, zb), y, half, lo, hi, .03, stone(tone))
        for m in range(5):
            bx = a + (b - a) * (m + .5) / 5
            bz = za + (zb - za) * (m + .5) / 5
            lathe(p, [(.075, .22), (.11, .4), (.07, .72), (.065, 1.04)], stone(.92), 0, 6, (bx, y, bz))
    return p


def parapet_w():
    return _parapet('SM_CD_ParapetW', -WALK)


def parapet_e():
    return _parapet('SM_CD_ParapetE', WALK)


# ---------------------------------------------------------------- the town and the vegetation (scatter.json)

# Footprints (length along the mesh's front +x, width), metres: keep-clear, spacing and the audit use them.
FOOTPRINT = {'SM_CN_House0': (7, 9), 'SM_CN_House1': (6, 6), 'SM_CN_House2': (8, 12), 'SM_CN_House3': (8, 8),
             'SM_CN_Ruin0': (7, 9), 'SM_CN_Ruin1': (6, 6), 'SM_CN_TerraceWall': (.6, 12), 'SM_CN_Stairs': (4.5, 3),
             'SM_CN_Lamp': (1, 1), 'SM_CN_Bench': (.6, 2), 'SM_CN_Planter': (1, 2), 'SM_CN_Banner': (1, 1),
             'SM_CV_Hedge': (1, 2)}
HOUSES = (('SM_CN_House0', .30), ('SM_CN_House1', .24), ('SM_CN_House2', .18), ('SM_CN_House3', .28))
RUINS = (('SM_CN_Ruin0', .55), ('SM_CN_Ruin1', .45))
WATER_PLANTS = ('SM_CV_Reeds', 'SM_CV_Lily')
FLOWERS = ('SM_CV_FlowersWhite', 'SM_CV_FlowersRed', 'SM_CV_FlowersBlue')


def _row(x, y, z, yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
    return [round(float(x) * 100, 1), round(float(y) * 100, 1), round(float(z) * 100, 1), round(float(pitch), 1),
            round(float(yaw) % 360.0, 1), round(float(roll), 1), round(float(scale), 3)]


def footprint_points(x, y, yaw, length, width, grow=0.0):
    """Corners, edge middles and centre of a footprint turned by yaw degrees (Unreal: +x toward +y)."""
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    a, b = length / 2 + grow, width / 2 + grow
    pts = [(x + u * c - v * s, y + u * s + v * c) for u in (-a, 0, a) for v in (-b, 0, b)]
    return np.array([p[0] for p in pts]), np.array([p[1] for p in pts])


def nearest_point(lines, x, y):
    """The nearest point on a set of polylines to (x, y) and its distance."""
    best, bp = 1e18, (x, y)
    for line in lines:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            px, py = ax + t * dx, ay + t * dy
            d = math.hypot(x - px, y - py)
            if d < best:
                best, bp = d, (px, py)
    return bp, best


@functools.lru_cache(maxsize=1)
def _road_polylines():
    return tuple(tuple(pts) for pts, _, _ in road_lines())


def road_gap(xs, ys):
    """Exact distance (m) from points to the nearest road centreline: the plan's roads and the connectors."""
    return nearest_on(_road_polylines(), xs, ys)[0]


def clear(G, xs, ys, road=ROAD_MARGIN + .05, zone_pad=.05, lake_pad=1.0, people=0.0):
    """True where points honour the README's keep-clear rules: inside the walk limit and off the end berms, outside
    every keep-clear zone and the Foundry's works (plus zone_pad), more than `road` from every road, off the North
    Gate road, out of the lake (unless lake_pad is None), and `people` metres from where people, scans and tutorials
    stand. Placement keeps 5 cm more than the audit, so rounding a row to 0.1 cm never crosses a line."""
    xs, ys = np.atleast_1d(np.asarray(xs, np.float64)), np.atleast_1d(np.asarray(ys, np.float64))
    ok = (np.abs(ys) <= WALK - .6) & (np.abs(xs) <= END_BERM - 1.0)
    for _, (zx, zy), zr in KEEP_CLEAR:
        ok &= np.hypot(xs - zx, ys - zy) > zr + zone_pad
    ok &= ~in_foundry_works(xs, ys, zone_pad)
    if road is not None:
        d = sample(G['road_d'], xs, ys)
        # The grid's distance is bilinear between cells, which overshoots the true distance by up to ~0.1 m round a
        # road's end or the outside of a bend (a grass tuft stood 5.98 m from the Old Quarter road's end), so
        # points just past the margin are measured exactly.
        near = ok & (d > road) & (d < road + 1.0)
        if near.any():
            d = d.copy()
            d[near] = road_gap(xs[near], ys[near])
        ok &= d > road
    ok &= ~in_gate_road(xs, ys)
    if lake_pad is not None:
        ok &= lake_metric(xs, ys) > lake_pad
    if people > 0:
        for px, py in people_points():
            ok &= np.hypot(xs - px, ys - py) > people
    return ok


OCC = .5   # occupancy cell (m): narrower than the thinnest footprint, the 0.6 m terrace wall


class _Layout:
    """Rows per mesh plus a 0.5 m occupancy grid, so trees, rocks, hedges and furniture never stand in a house or a
    wall. A cell is taken when its centre lies in a footprint; on the 1 m grid this used to be, a 0.6 m wall whose
    line fell between cell centres took none, and shrubs, rocks and trees grew through dozens of them.
    Each cell remembers who took it first (1 for anything, a building's own number for a building and its garden
    margin), so the hedges and plants of a house's garden may stand in its margin and nowhere else's."""

    def __init__(self):
        self.G = grid()
        self.H = self.G['H'].astype(np.float64)
        self.rows = {}
        self.occ = np.zeros((int(round(2 * HALF_X / OCC)), int(round(2 * HALF_Y / OCC))), np.int32)
        self.owners = 1
        self.rng = np.random.default_rng(20261106)
        self.roads = [line for line, _, _ in road_lines()]

    def owner(self):
        """A new owner number for a building."""
        self.owners += 1
        return self.owners

    def add(self, mesh, x, y, z, yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
        self.rows.setdefault(mesh, []).append(_row(x, y, z, yaw, pitch, roll, scale))

    def h(self, x, y):
        return sample(self.H, x, y)

    def _window(self, x, y, yaw, a, b):
        r = math.hypot(a, b) + OCC
        i0, i1 = max(int(math.floor((x - r + HALF_X) / OCC)), 0), min(int(math.ceil((x + r + HALF_X) / OCC)), self.occ.shape[0])
        j0, j1 = max(int(math.floor((y - r + HALF_Y) / OCC)), 0), min(int(math.ceil((y + r + HALF_Y) / OCC)), self.occ.shape[1])
        if i0 >= i1 or j0 >= j1:
            return None, None
        cx = (np.arange(i0, i1) + .5) * OCC - HALF_X
        cy = (np.arange(j0, j1) + .5) * OCC - HALF_Y
        CX, CY = np.meshgrid(cx, cy, indexing='ij')
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        u, v = (CX - x) * c + (CY - y) * s, -(CX - x) * s + (CY - y) * c
        return (slice(i0, i1), slice(j0, j1)), (np.abs(u) <= a) & (np.abs(v) <= b)

    def free(self, x, y, yaw, length, width, grow=0.0, own=0):
        """True when no cell of the footprint is taken, except by `own` (a building, for what grows in its garden)."""
        sl, inside = self._window(x, y, yaw, length / 2 + grow, width / 2 + grow)
        if sl is None:
            return False
        cells = self.occ[sl][inside]
        return not ((cells != 0) & (cells != own)).any()

    def mark(self, x, y, yaw, length, width, grow=0.0, owner=1, take=0):
        """Takes the footprint's free cells for `owner` (first come keeps a cell, so no one frees another's); `take`
        also claims that building's margin cells, as a plant in its garden does."""
        sl, inside = self._window(x, y, yaw, length / 2 + grow, width / 2 + grow)
        if sl is not None:
            region = self.occ[sl]
            region[inside & ((region == 0) | (region == take))] = owner

    def free_points(self, xs, ys):
        i = np.clip(((np.asarray(xs) + HALF_X) / OCC).astype(np.int64), 0, self.occ.shape[0] - 1)
        j = np.clip(((np.asarray(ys) + HALF_Y) / OCC).astype(np.int64), 0, self.occ.shape[1] - 1)
        return self.occ[i, j] == 0

    def pick(self, kinds):
        w = np.array([k[1] for k in kinds])
        return kinds[int(self.rng.choice(len(kinds), p=w / w.sum()))][0]

    def candidates(self, x0, x1, y0, y1, spacing):
        xs, ys = np.arange(x0, x1, spacing), np.arange(y0, y1, spacing)
        X, Y = np.meshgrid(xs, ys, indexing='ij')
        X = X.ravel() + self.rng.uniform(-.45, .45, X.size) * spacing
        Y = Y.ravel() + self.rng.uniform(-.45, .45, Y.size) * spacing
        order = self.rng.permutation(X.size)
        return X[order], Y[order]


# -- streets: lamps along every road, and the Commons' furniture

def _lamps(L):
    """SM_CN_Lamp every 30 m along each road, sides taking turns, 7 m from the centreline, facing the road."""
    for line in L.roads:
        P = np.array(line)
        seg = np.hypot(*np.diff(P, axis=0).T)
        s = np.concatenate([[0], np.cumsum(seg)])
        side = 1
        for arc in np.arange(15.0, s[-1] - 5.0, 30.0):
            k = min(int(np.searchsorted(s, arc, side='right')) - 1, len(seg) - 1)
            t = (arc - s[k]) / seg[k]
            cx, cy = P[k] + (P[k + 1] - P[k]) * t
            dx, dy = (P[k + 1] - P[k]) / seg[k]
            nx, ny = -dy * side, dx * side
            x, y = cx + nx * 7.0, cy + ny * 7.0
            side = -side
            if not clear(L.G, x, y, zone_pad=1.0, people=2.0)[0] or float(sample(L.G['slope'], x, y)) > .35:
                continue
            if not L.free(x, y, 0, 1.2, 1.2, .5):
                continue
            L.add('SM_CN_Lamp', x, y, float(L.h(x, y)), math.degrees(math.atan2(-ny, -nx)))
            L.mark(x, y, 0, 1.2, 1.2, .3)


def _furniture(L):
    """Benches and planters round the rim of the Orrery plaza and along the Commons' main street, banners on poles
    at the plaza's entrances and down the street. All face the plaza or the road."""
    G, rng = L.G, L.rng
    ox, oy = plan.ORRERY

    def put(mesh, x, y, yaw, flat=.08):
        length, width = FOOTPRINT[mesh]
        xs, ys = footprint_points(x, y, yaw, length, width, .3)
        if not clear(G, xs, ys, zone_pad=.5, people=2.5).all():
            return False
        hs = L.h(xs, ys)
        if hs.max() - hs.min() > flat or not L.free(x, y, yaw, length, width, .4):
            return False
        L.add(mesh, x, y, float(hs.min()), yaw)
        L.mark(x, y, yaw, length, width, .2)
        return True
    for k in range(30):
        a = 2 * math.pi * (k + .5) / 30
        r = 47.0 if k % 2 == 0 else 48.2
        x, y = ox + r * math.cos(a), oy + r * math.sin(a)
        toward = math.degrees(math.atan2(oy - y, ox - x))
        put('SM_CN_Bench' if k % 2 == 0 else 'SM_CN_Planter', x, y, toward)
    for k in range(8):
        a = 2 * math.pi * (k + .5) / 8
        put('SM_CN_Banner', ox + 50.5 * math.cos(a), oy + 50.5 * math.sin(a), math.degrees(a) + 180)
    street = plan.PATHS[0]
    for (ax, ay), (bx, by) in zip(street, street[1:]):
        length = math.hypot(bx - ax, by - ay)
        dx, dy = (bx - ax) / length, (by - ay) / length
        for arc in np.arange(8.0, length, 15.0):
            x0, y0 = ax + dx * arc, ay + dy * arc
            if region_w('Commons', x0, y0) < .9:
                continue
            for side in (-1, 1):
                nx, ny = -dy * side, dx * side
                toward = math.degrees(math.atan2(-ny, -nx))
                slot = int(round(arc / 15.0)) % 4
                if slot == 1:
                    put('SM_CN_Bench', x0 + nx * 8.2, y0 + ny * 8.2, toward)
                elif slot == 3 and rng.uniform() < .8:
                    put('SM_CN_Planter', x0 + nx * 8.4, y0 + ny * 8.4, toward)
                elif slot == 2 and side > 0 or slot == 0 and side < 0:
                    put('SM_CN_Banner', x0 + nx * 9.0, y0 + ny * 9.0, toward)


# -- the terraces of the town: walls along the pad edges, stairs up the lanes, houses and ruins on the pads

def _crests(G, region):
    """The top edge of every riser in a terraced region, found where the level coordinate u passes an integer:
    {(side, k): array of y per grid column (nan where that riser is absent)}."""
    t = G['terraces'][region]
    u = t['u']
    mid = NY // 2
    out = {}
    for side in (1, -1):
        U = u[:, mid:] if side > 0 else u[:, mid::-1]
        ys = AXIS_Y[mid:] if side > 0 else AXIS_Y[mid::-1]
        lo, hi = np.floor(U[:, :-1]), np.floor(U[:, 1:])
        for i, j in zip(*np.nonzero(hi > lo)):
            k = int(hi[i, j])
            frac = (k - U[i, j]) / max(U[i, j + 1] - U[i, j], 1e-9)
            y = ys[j] + side * CELL * frac
            arr = out.setdefault((side, k), np.full(NX, np.nan))
            if np.isnan(arr[i]):
                arr[i] = y
    return out


def _terrace_walls(L, region, broken=0.0):
    """SM_CN_TerraceWall along the top edge of every riser, in 12 m runs on a common grid so they meet end to end.
    Each wall faces down the slope with its front at the riser's top and stands 1.0 m above the upper pad (a
    garden wall over the grassy ramp; the rest of it sits in the bank), stopping short of lanes, roads, zones and
    people. The Old Quarter's are broken: runs missing, sunk and askew."""
    G, rng = L.G, L.rng
    t = G['terraces'][region]
    crest = _crests(G, region)
    for (side, k), ys in sorted(crest.items()):
        for x_a in np.arange(-HALF_X, HALF_X - 12, 12.0):
            i0 = int(round((x_a + HALF_X) / CELL))
            col = ys[i0:i0 + 7]
            if len(col) < 7 or np.isnan(col).any() or np.abs(np.diff(col)).max() > 1.2:
                continue
            xa, xb, ya, yb = x_a, x_a + 12.0, col[0], col[-1]
            length = math.hypot(xb - xa, yb - ya)
            if length > 12.5:
                continue
            dx, dy = (xb - xa) / length, (yb - ya) / length
            ux, uy = -dy * side, dx * side                      # up the slope
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            if t['w'][i0 + 3, int(round((my + HALF_Y) / CELL))] < .97:
                continue
            upper = float(L.h(mx + ux * 1.2, my + uy * 1.2))
            lower = float(L.h(mx - ux * t['riser'] * .7, my - uy * t['riser'] * .7))
            if abs(upper - (t['origin'] + t['step'] * k)) > .2 or upper - lower < 1.2:
                continue
            yaw = math.degrees(math.atan2(-uy, -ux)) + (rng.uniform(-2.5, 2.5) if broken else 0.0)
            px, py = footprint_points(mx + ux * .3, my + uy * .3, yaw, .6, 12.0)
            # The lane test runs the wall's whole length every 0.5 m: its corners and middle alone (6 m apart) let a
            # wall stand across a lane, at the head of its stairs.
            run = np.linspace(-6.0, 6.0, 25)
            lx, ly = mx + ux * .3 + run * dx, my + uy * .3 + run * dy
            if not clear(G, px, py, zone_pad=1.0, people=3.0).all() or sample(G['lane_d'], lx, ly).min() < 2.6:
                continue
            if broken and rng.uniform() < broken:
                continue
            z = upper - 1.5 - (rng.uniform(0, .7) if broken else 0.0)
            L.add('SM_CN_TerraceWall', mx + ux * .3, my + uy * .3, z, yaw)
            L.mark(mx + ux * .3, my + uy * .3, yaw, .6, 12.0)


def _stairs(L, region):
    """SM_CN_Stairs on every riser a lane crosses: one flight per 2.5 m of step, climbing the ramp from its foot
    (the flight's footprint is the ramp's width), facing up the slope."""
    G = L.G
    t = G['terraces'][region]
    crest = _crests(G, region)
    flights = int(round(t['step'] / 2.5))
    run = t['riser'] / flights
    for reg, side, xl, y0, y1 in G['lanes']:
        if reg != region:
            continue
        fi = (xl + HALF_X) / CELL
        i = int(math.floor(fi))
        for (s, k), ys in sorted(crest.items()):
            if s != side or i + 1 >= NX or np.isnan(ys[i]) or np.isnan(ys[i + 1]):
                continue
            yc = ys[i] + (ys[i + 1] - ys[i]) * (fi - i)
            if not (y0 - 1 <= abs(yc) <= y1 + 1):
                continue
            top = float(L.h(xl, yc + side * 1.2))
            bottom = float(L.h(xl, yc - side * (t['riser'] + 1.2)))
            if abs(top - (t['origin'] + t['step'] * k)) > .25 or abs(top - t['step'] - bottom) > .3:
                continue
            for m in range(flights):
                y = yc - side * (t['riser'] - (m + .5) * run)
                xs, ys_ = footprint_points(xl, y, side * 90.0, run, 3.0)
                if not clear(G, xs, ys_, zone_pad=.5, people=2.0).all():
                    break
                L.add('SM_CN_Stairs', xl, y, top - t['step'] + 2.5 * m, side * 90.0)
                L.mark(xl, y, side * 90.0, run, 3.0, .4)


def _buildings(L, region, kinds, flat_tol, jitter, sink, target):
    """Houses (or ruins) on a region's pads: each faces the nearest road, sits whole on one pad with a garden
    margin, stays 6 m from every road, off lanes, zones and people, and keeps 3 m from its neighbours."""
    G, rng = L.G, L.rng
    cx, cy, r, b = plan.REGIONS[region]
    X, Y = L.candidates(cx - r - b, cx + r + b, -WALK, WALK, 2.5)
    keep = (region_w(region, X, Y) > .95) & clear(G, X, Y, road=ROAD_MARGIN + 3, zone_pad=3.5, people=6.0)
    placed = []
    for x, y in zip(X[keep], Y[keep]):
        mesh = L.pick(kinds)
        length, width = FOOTPRINT[mesh]
        (px, py), _ = nearest_point(L.roads, x, y)
        yaw = math.degrees(math.atan2(py - y, px - x)) + rng.uniform(-jitter, jitter)
        xs, ys = footprint_points(x, y, yaw, length, width, .9)
        hs = L.h(xs, ys)
        if hs.max() - hs.min() > flat_tol:
            continue
        fx, fy = footprint_points(x, y, yaw, length, width, .3)
        if not clear(G, fx, fy, zone_pad=.5, people=6.0).all() or sample(G['lane_d'], fx, fy).min() < 3.0:
            continue
        if not L.free(x, y, yaw, length, width, 1.0):      # a 1 m garden to a wall, 2.4 m to the next house
            continue
        L.add(mesh, x, y, float(hs.min()) - sink, yaw)     # a ruin on uneven ground is half buried on its high side
        owner = L.owner()
        L.mark(x, y, yaw, length, width, 1.4, owner)
        placed.append((mesh, x, y, yaw, owner))
        if len(placed) >= target:
            break
    return placed


def _gardens(L, houses):
    """Around each house: hedges along a side of its front garden, shrubs and flowers in it, a white blossom tree
    behind or beside it."""
    G, rng = L.G, L.rng
    for mesh, x, y, yaw, own in houses:   # what grows in a house's garden may stand in its margin (own)
        length, width = FOOTPRINT[mesh]
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        if rng.uniform() < .7:
            side = rng.choice((-1, 1))
            row = []
            for n in range(int(rng.integers(2, 4))):
                u, v = length / 2 + 1.2 + n * 2.0, side * (width / 2 + .9)
                hx, hy = x + u * c - v * s, y + u * s + v * c
                fx, fy = footprint_points(hx, hy, yaw + 90, 1.0, 2.0, .1)
                if not (clear(G, fx, fy, zone_pad=.5, people=2.0).all() and L.free(hx, hy, yaw + 90, 1.0, 2.0, .2, own)
                        and abs(float(L.h(hx, hy)) - float(L.h(x, y))) < .3):
                    break   # the hedge runs unbroken from the house, as far as it can
                row.append((hx, hy))
            for hx, hy in row:   # tested whole before any is marked, so its own segments do not stop it
                L.add('SM_CV_Hedge', hx, hy, float(L.h(hx, hy)) - .05, yaw + 90)
                L.mark(hx, hy, yaw + 90, 1.0, 2.0, .1, take=own)
        for _ in range(int(rng.integers(1, 4))):
            # 1 m out from the front wall at least: a 1.4 m shrub nearer than that grows into the house. Each plant
            # is tested at its own size plus half a cell, so it cannot reach a wall between two cell centres.
            u, v = length / 2 + rng.uniform(1.0, 2.6), rng.uniform(-width / 2, width / 2)
            sx, sy = x + u * c - v * s, y + u * s + v * c
            kind = 'SM_CV_Shrub' if rng.uniform() < .55 else FLOWERS[int(rng.integers(0, 3))]
            scale = rng.uniform(.8, 1.15)
            size = (1.3 if kind == 'SM_CV_Shrub' else .5) * scale
            if clear(G, sx, sy, people=1.5)[0] and L.free(sx, sy, 0, size, size, OCC / 2, own):
                L.add(kind, sx, sy, float(L.h(sx, sy)) - .05, rng.uniform(0, 360), 0, 0, scale)
                L.mark(sx, sy, 0, size, size, take=own)
        if rng.uniform() < .5:
            u, v = -(length / 2 + rng.uniform(3.0, 4.5)), rng.uniform(-width / 2, width / 2)
            tx, ty = x + u * c - v * s, y + u * s + v * c
            if (clear(G, tx, ty, zone_pad=2.0, people=3.0)[0] and L.free(tx, ty, 0, 3.0, 3.0, own=own)
                    and float(sample(G['slope'], tx, ty)) < .4):
                L.add('SM_CV_TreeWhite', tx, ty, float(L.h(tx, ty)) - .25, rng.uniform(0, 360), 0, 0, rng.uniform(.75, 1.0))
                L.mark(tx, ty, 0, 2.0, 2.0, take=own)


def _vines(L, ruins):
    """SM_CV_Vines against the walls of the Old Quarter's ruins, hanging from their broken tops to the ground."""
    rng = L.rng
    for mesh, x, y, yaw, _ in ruins:
        length, width = FOOTPRINT[mesh]
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        for _ in range(int(rng.integers(1, 4))):
            if rng.uniform() < .5:
                u, v = rng.choice((-1, 1)) * (length / 2 + .12), rng.uniform(-width / 2 + 1, width / 2 - 1)
                out = yaw if u > 0 else yaw + 180
            else:
                u, v = rng.uniform(-length / 2 + 1, length / 2 - 1), rng.choice((-1, 1)) * (width / 2 + .12)
                out = yaw + (90 if v > 0 else -90)
            vx, vy = x + u * c - v * s, y + u * s + v * c
            L.add('SM_CV_Vines', vx, vy, float(L.h(vx, vy)), out, 0, 0, rng.uniform(.85, 1.15))


# -- fields and orchards

def _wheat(L):
    """SM_CV_Wheat in rows on the black soil of the crop terraces, with fallow gaps and paths every 30 m."""
    G, rng = L.G, L.rng
    ter = G['terraces']['Terraces']
    cx, cy, r, b = plan.REGIONS['Terraces']
    xs, ys = np.arange(cx - r - b, cx + r + b, 1.7), np.arange(-WALK, 0, 1.5)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    X = X.ravel() + rng.uniform(-.3, .3, X.size)
    Y = Y.ravel() + rng.uniform(-.2, .2, Y.size)
    soil = sample(G['surface']['soil'], X, Y) > .8
    # a cell's whole neighbourhood is pad (keeps rows off the riser edges)
    edge = np.maximum.reduce([sample(ter['ramp'], X + dx, Y + dy) for dx, dy in ((0, 1.0), (0, -1.0), (1.0, 0), (-1.0, 0))])
    fallow = fbm(X, Y, 61, 3, 1 / 40.0) > .32
    paths = np.abs(((X + 9.0) % 30.0) - 15.0) < 1.5
    ok = soil & (edge < .01) & ~fallow & ~paths & clear(G, X, Y, zone_pad=.5) & L.free_points(X, Y)
    for x, y in zip(X[ok], Y[ok]):
        L.add('SM_CV_Wheat', x, y, float(L.h(x, y)) - .05, rng.uniform(0, 360), rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(.85, 1.15))


def _orchards(L):
    """SM_CV_FruitTree in rows along the Orchard Rim's pads, 6 m apart, two rows where a pad is wide enough; the
    listeners' terrace above them is left open for their stones."""
    G, rng = L.G, L.rng
    t = G['terraces']['Orchard Rim']
    cx, cy, r, b = plan.REGIONS['Orchard Rim']
    for x in np.arange(cx - r - b, cx + r + b, 6.0):
        for y in np.arange(-WALK + 2, 0, 1.0):
            fx, fy = x + rng.uniform(-.4, .4), y
            if t['w'][int(round((fx + HALF_X) / CELL)), int(round((fy + HALF_Y) / CELL))] < .8:
                continue
            if math.hypot(fx - LISTENERS[0], fy - LISTENERS[1]) < 20.0:
                continue
            # on a pad, at least 2 m from its edges up and down the slope
            hs = L.h(np.array([fx, fx, fx]), np.array([fy - 2.0, fy, fy + 2.0]))
            if hs.max() - hs.min() > .05:
                continue
            if not clear(G, fx, fy, zone_pad=3.0, people=3.0)[0] or not L.free(fx, fy, 0, 4.0, 4.6):
                continue
            L.add('SM_CV_FruitTree', fx, fy, float(hs[1]) - .2, rng.uniform(0, 360), 0, 0, rng.uniform(.85, 1.1))
            L.mark(fx, fy, 0, 2.0, 2.0, .3)
            L.mark(fx, fy, 0, 1.0, 4.6)           # a row: the next tree up the slope waits for the next pad


# -- trees, shrubs and rocks over the open land

def _ground_mask(L, X, Y, slope_max=.55):
    """Where open vegetation may grow: golden grass (not stone, soil, slag, deck, sand, rock), not too steep."""
    S = L.G['surface']
    stone = np.maximum.reduce([sample(S[k], X, Y) for k in ('road', 'lane', 'plaza', 'soil', 'slag', 'deck', 'sand', 'silt', 'rock')])
    return (stone < .2) & (sample(L.G['slope'], X, Y) < slope_max)


def _trees(L):
    G, rng = L.G, L.rng
    X, Y = L.candidates(-HALF_X, HALF_X, -WALK, WALK, 6.0)
    ok = _ground_mask(L, X, Y, .5) & clear(G, X, Y, road=ROAD_MARGIN + 2.0, zone_pad=3.0, lake_pad=6.0, people=3.0)
    ay = np.abs(Y)
    commons = region_w('Commons', X, Y)
    oq = region_w('Old Quarter', X, Y)
    orchard = region_w('Orchard Rim', X, Y)
    terr = region_w('Terraces', X, Y)
    lake = lake_metric(X, Y)
    well = np.hypot(X - plan.WELL[0], Y - plan.WELL[1])
    clump = fbm(X, Y, 71, 4, 1 / 90.0)
    p_black = np.clip((ay - 230) / 60, 0, 1) * .3 + np.clip(clump - .25, 0, 1) * .4
    p_red = np.clip(clump + .1, 0, 1) * .14 + oq * .35 + .1 * sstep(40, 10, lake - 10) * (lake < 50)
    p_white = .03 + .35 * (well < 60) + .12 * (lake < 45)
    # Few trees among the town's houses; its upper terraces are gardens again.
    damp = (1 - .85 * commons * (1 - sstep(105, 145, ay))) * (1 - .9 * orchard) * (1 - .8 * terr)
    p_white = p_white + .22 * commons * sstep(105, 145, ay)
    u = rng.uniform(0, 1, X.size)
    for k in np.nonzero(ok)[0]:
        x, y = X[k], Y[k]
        pb, pr, pw = p_black[k] * damp[k], p_red[k] * damp[k], p_white[k] * damp[k]
        if u[k] < pb:
            mesh, scale = 'SM_CV_TreeBlack', rng.uniform(.8, 1.25)
        elif u[k] < pb + pr:
            mesh, scale = 'SM_CV_TreeRed', rng.uniform(.8, 1.2)
        elif u[k] < pb + pr + pw:
            mesh, scale = 'SM_CV_TreeWhite', rng.uniform(.8, 1.15)
        else:
            continue
        if not L.free(x, y, 0, 3.0, 3.0, 1.0):
            continue
        L.add(mesh, x, y, float(L.h(x, y)) - .35, rng.uniform(0, 360), rng.uniform(-2, 2), rng.uniform(-2, 2), scale)
        L.mark(x, y, 0, 2.4, 2.4)
    # An avenue of red trees down the Commons' main street and the docks road, between the lamps.
    for index in (0, 7):
        line = plan.PATHS[index]
        for (ax, ay_), (bx, by) in zip(line, line[1:]):
            length = math.hypot(bx - ax, by - ay_)
            dx, dy = (bx - ax) / length, (by - ay_) / length
            for arc in np.arange(0.0, length, 30.0):
                for side in (-1, 1):
                    x, y = ax + dx * arc - dy * side * 11.0, ay_ + dy * arc + dx * side * 11.0
                    if clear(G, x, y, road=ROAD_MARGIN + 2.0, zone_pad=3.0, people=3.0)[0] and L.free(x, y, 0, 3.0, 3.0, 1.0):
                        L.add('SM_CV_TreeRed', x, y, float(L.h(x, y)) - .35, rng.uniform(0, 360), 0, 0, rng.uniform(.85, 1.05))
                        L.mark(x, y, 0, 2.4, 2.4)


def _shrubs_rocks(L):
    G, rng = L.G, L.rng
    X, Y = L.candidates(-HALF_X, HALF_X, -WALK, WALK, 4.0)
    S = G['surface']
    slope = sample(G['slope'], X, Y)
    ok = clear(G, X, Y, zone_pad=1.0, lake_pad=2.0, people=2.0) & L.free_points(X, Y)
    grassy = _ground_mask(L, X, Y, .6)
    u = rng.uniform(0, 1, X.size)
    oq = region_w('Old Quarter', X, Y)
    fw = sample(S['slag'], X, Y)
    shrub = grassy & ok & (u < .022 + .045 * (np.abs(Y) > 200) + .08 * oq)
    # Shrubs and rocks are tested and marked by their whole footprint (SM_CV_Shrub 1.4 m, the rocks about 1.9 x 1.4
    # m at scale 1), not their centre alone, so a boulder never stands in a wall, a stair or a tree.
    for x, y in zip(X[shrub], Y[shrub]):
        scale = rng.uniform(.7, 1.3)
        if not L.free(x, y, 0, 1.3 * scale, 1.3 * scale, OCC / 2):
            continue
        L.add('SM_CV_Shrub', x, y, float(L.h(x, y)) - .1, rng.uniform(0, 360), 0, 0, scale)
        L.mark(x, y, 0, 1.3 * scale, 1.3 * scale)
    rocky = ok & ~shrub & (sample(G['road_d'], X, Y) > ROAD_MARGIN + 1)
    p_rock = .006 + .3 * np.clip(slope - .35, 0, 1) + .05 * (np.abs(Y) > 285) + .035 * oq + .04 * fw
    rock = rocky & (rng.uniform(0, 1, X.size) < p_rock) & (slope < 1.1)
    for x, y in zip(X[rock], Y[rock]):
        black = rng.uniform() < .25 + .5 * float(sample(S['slag'], x, y)) + .3 * float(region_w('Old Quarter', x, y))
        yaw, scale = rng.uniform(0, 360), rng.uniform(.5, 1.5)
        if not L.free(x, y, yaw, 2.0 * scale, 1.5 * scale, .3):
            continue
        L.add('SM_CV_RockBlack' if black else 'SM_CV_RockWhite', x, y, float(L.h(x, y)) - .25, yaw,
              rng.uniform(-8, 8), rng.uniform(-8, 8), scale)
        L.mark(x, y, yaw, 2.0 * scale, 1.5 * scale)


# -- grass, flowers, the lake

def _grass_flowers(L, grass=200000, flowers=16000):
    # 40000 tufts over the 750000 m2 of lawn was one per 19 m2: specks, not grass. 200000 (about 30 MB of instance
    # data; 316000 candidates pass before the occupancy test) is about 0.27 per m2, thickest on the roads' grass verges
    # where the camera is; the lawn between them is carried by M_CNGround's grass detail.
    G, rng = L.G, L.rng
    X, Y = L.candidates(-HALF_X, HALF_X, -WALK, WALK, 1.1)
    ok = _ground_mask(L, X, Y, .7) & clear(G, X, Y, lake_pad=1.5) & L.free_points(X, Y)
    commons = region_w('Commons', X, Y)
    verge = 1 - sstep(ROAD_VERGE, 25.0, sample(G['road_d'], X, Y))
    density = (1 - .3 * commons) * (1 - .3 * region_w('Orchard Rim', X, Y)) * (.55 + .45 * np.clip(fbm(X, Y, 81, 3, 1 / 50.0) + .6, 0, 1))
    density = np.clip(density * (.65 + .7 * verge), 0, 1)
    pick = ok & (rng.uniform(0, 1, X.size) < density)
    idx = np.nonzero(pick)[0]
    gi = idx[:grass]
    for k in gi:
        x, y = X[k], Y[k]
        L.add('SM_CV_GrassGold', x, y, float(L.h(x, y)) - .04, rng.uniform(0, 360), rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(.75, 1.35))
    # Flowers in drifts of one colour: meadows round the Wellspring and the lake, the Commons' verges, the orchards.
    FX, FY = L.candidates(-HALF_X, HALF_X, -WALK, WALK, 2.6)
    ok = _ground_mask(L, FX, FY, .5) & clear(G, FX, FY, lake_pad=2.0) & L.free_points(FX, FY)
    drift = fbm(FX, FY, 91, 3, 1 / 32.0)
    near = (np.hypot(FX - plan.WELL[0], FY - plan.WELL[1]) < 90) * 1.0 + (lake_metric(FX, FY) < 50) * .6 + region_w('Orchard Rim', FX, FY) * .5
    p = np.clip(drift * 1.6 - .05, 0, 1) * (.35 + near)
    pick = np.nonzero(ok & (rng.uniform(0, 1, FX.size) < p))[0][:flowers]
    tone = fbm(FX, FY, 92, 2, 1 / 70.0)
    lo, hi = np.quantile(tone[pick], (1 / 3, 2 / 3)) if len(pick) else (0, 0)   # even thirds of white, red, blue
    for k in pick:
        x, y = FX[k], FY[k]
        mesh = FLOWERS[0] if tone[k] < lo else (FLOWERS[1] if tone[k] < hi else FLOWERS[2])
        L.add(mesh, x, y, float(L.h(x, y)) - .03, rng.uniform(0, 360), 0, 0, rng.uniform(.8, 1.2))


def _lake_plants(L):
    """SM_CV_Reeds along the shallows and the wet sand; SM_CV_Lily in drifts on the water (z at the surface)."""
    G, rng = L.G, L.rng
    cx, cy, ax, ay = plan.LAKE
    X, Y = L.candidates(cx - ax - 12, cx + ax + 12, cy - ay - 12, cy + ay + 12, 1.0)
    d = lake_metric(X, Y)
    Hs = L.h(X, Y)
    off = clear(G, X, Y, lake_pad=None) & (sample(G['road_d'], X, Y) > ROAD_MARGIN + 4)
    band = np.clip(fbm(X, Y, 101, 3, 1 / 24.0) * 2 + .5, 0, 1)
    reeds = off & (Hs > WATER - .7) & (Hs < WATER + .35) & (rng.uniform(0, 1, X.size) < .85 * band)
    for x, y in zip(X[reeds], Y[reeds]):
        L.add('SM_CV_Reeds', x, y, float(L.h(x, y)) - .1, rng.uniform(0, 360), rng.uniform(-5, 5), rng.uniform(-5, 5), rng.uniform(.75, 1.25))
    lily = off & (d < -4) & (Hs < WATER - .6) & (Hs > WATER - 2.8) & (rng.uniform(0, 1, X.size) < .6 * np.clip(fbm(X, Y, 102, 3, 1 / 18.0) * 2.5 + .1, 0, 1))
    for x, y in zip(X[lily], Y[lily]):
        L.add('SM_CV_Lily', x, y, WATER, rng.uniform(0, 360), 0, 0, rng.uniform(.7, 1.3))


def layout():
    """The whole scatter: {mesh name: [[x_cm, y_cm, z_cm, pitch, yaw, roll, scale], ...]}."""
    L = _Layout()
    _lamps(L)
    _furniture(L)
    for region in TOWN:
        _terrace_walls(L, region, broken=.3 if region == 'Old Quarter' else 0.0)
        _stairs(L, region)
    houses = _buildings(L, 'Commons', HOUSES, .12, 3.0, .02, 400)
    ruins = _buildings(L, 'Old Quarter', RUINS, .6, 6.0, .2, 60)
    _gardens(L, houses)
    _vines(L, ruins)
    _orchards(L)
    _wheat(L)
    _trees(L)
    _shrubs_rocks(L)
    _lake_plants(L)
    _grass_flowers(L)
    return dict(sorted(L.rows.items()))


def audit(rows):
    """Keep-clear violations per mesh: rows inside a keep-clear zone, within 6 m of a road, on the North Gate road,
    in the lake (water plants excepted), past the walk limit or in an end berm. Buildings and walls are tested over
    their footprint. Must be empty."""
    G = grid()
    bad = {}
    for mesh, rs in rows.items():
        if not rs:
            continue
        a = np.asarray(rs, np.float64)
        x, y, yaw = a[:, 0] / 100, a[:, 1] / 100, a[:, 4]
        water = mesh in WATER_PLANTS
        if mesh in FOOTPRINT and FOOTPRINT[mesh][1] > 1.5:
            length, width = FOOTPRINT[mesh]
            ok = np.ones(len(a), bool)
            for k in range(len(a)):
                xs, ys = footprint_points(x[k], y[k], yaw[k], length, width)
                ok[k] = clear(G, xs, ys, road=ROAD_MARGIN, zone_pad=0.0, lake_pad=None if water else 0.0).all()
        else:
            ok = clear(G, x, y, road=ROAD_MARGIN, zone_pad=0.0, lake_pad=None if water else 0.0)
            if water:
                ok &= lake_metric(x, y) < 12
        if (~ok).any():
            bad[mesh] = int((~ok).sum())
    return bad


def write_height(out):
    """height.bin (little-endian float32, index i * ny + j, i along x) and height.json, as the README says."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    G = grid()
    meta = {'half_x': HALF_X, 'half_y': HALF_Y, 'cell': CELL, 'nx': NX, 'ny': NY, 'water': WATER,
            'regions': {k: list(v) for k, v in plan.REGIONS.items()},
            'paths': [[list(map(float, p)) for p in line] for line in plan.PATHS]}
    (out / 'height.json').write_text(json.dumps(meta, indent=1))
    (out / 'height.bin').write_bytes(np.ascontiguousarray(G['H'], dtype='<f4').tobytes())
    return meta


def write_scatter(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = layout()
    (out / 'scatter.json').write_text(json.dumps(rows, separators=(',', ':')))
    return rows


# ---------------------------------------------------------------- report (offline checks of the floor and layout)

def triangle_slopes(H):
    """Steepest of the four triangles a grid cell can be split into (either diagonal), degrees, per cell: the
    ground the character actually stands on, without central differences smearing slopes across a kink."""
    a, b, c, d = H[:-1, :-1], H[1:, :-1], H[1:, 1:], H[:-1, 1:]     # (i, j), (i+1, j), (i+1, j+1), (i, j+1)
    tris = (((b - a), (c - b)), ((c - d), (d - a)), ((b - a), (d - a)), ((c - d), (c - b)))
    worst = np.zeros(a.shape)
    for dzx, dzy in tris:
        worst = np.maximum(worst, np.hypot(dzx, dzy) / CELL)
    return np.degrees(np.arctan(worst))


def report(rows=None, out=print):
    """Height and layout figures the build is judged by: heights, road grades, plaza flatness, the moat, the
    island, the steepest walkable ground, scatter counts and keep-clear violations."""
    G = grid()
    H = G['H'].astype(np.float64)
    X, Y = G['X'], G['Y']
    tri = triangle_slopes(H)
    slope = np.zeros(H.shape)
    slope[:-1, :-1] = tri
    stats = {'height_min': float(H.min()), 'height_max': float(H.max())}
    grades = [math.degrees(math.atan(np.abs(np.diff(o['z']) / np.diff(o['ss'])).max())) for o in G['profiles']]
    cross = slope[G['road_d'] < G['road_hw'] - 1.0]
    stats['road_grade_max_deg'] = round(max(grades), 2)
    stats['road_surface_slope_max_deg'] = round(float(cross.max()), 2)
    flat = {}
    for name, (px, py), r0 in (('Orrery', plan.ORRERY, 45.0), ('Wellspring', plan.WELL, 30.0), ('Spire', plan.SPIRE, 60.0),
                               ('Docks', plan.DOCKS_ARENA, 50.0)):
        m = np.hypot(X - px, Y - py) <= r0
        flat[name] = (round(float(H[m].min()), 3), round(float(H[m].max() - H[m].min()), 4))
    stats['plazas_level_and_range'] = flat
    fx, fy = plan.FOUNDRY_PYLON
    lf = G['foundry_level']
    widths, depths = [], []
    for a in np.radians(np.arange(15, 346, 5)):               # all round but the exit notch (north, +x)
        r = np.arange(10, FOUNDRY_APRON, .25)
        h = sample(H, fx + r * np.cos(a), fy + r * np.sin(a))
        inside = r[h < lf - MOAT_DEPTH / 2]
        widths.append(inside[-1] - inside[0] + .25)
        depths.append(lf - h.min())
    stats['moat_inner_r_width_depth'] = (MOAT_IN, round(float(np.median(widths)), 2), round(float(np.median(depths)), 2))
    stats['moat_width_min_max'] = (round(float(min(widths)), 2), round(float(max(widths)), 2))
    ix, iy = plan.RESERVOIR_ISLAND
    ri = np.hypot(X - ix, Y - iy)
    shore = ri[(ri < 30) & (np.abs(H - WATER) < .3)]
    stats['island_top_m'] = round(float(H[ri < 30].max()), 3)
    stats['island_shore_radius_m'] = round(float(np.median(shore)), 1)
    stats['lake_bed_min_m'] = round(float(H[G['lake_d'] < 0].min()), 2)
    # Walkable ground: inside the walk limit, off the end berms, and not a cell that spans part of a moat wall or the
    # notch's trench (a cell is judged by all four of its corners, so one just past a wall's lip is still checked).
    m = G['moat']
    corners = (m[:-1, :-1], m[1:, :-1], m[:-1, 1:], m[1:, 1:])
    walls = np.zeros(H.shape, bool)
    walls[:-1, :-1] = (np.maximum.reduce(corners) > 1e-3) & (np.minimum.reduce(corners) < 1 - 1e-3)
    walk = (np.abs(Y) < WALK - 2) & (np.abs(X) < END_BERM - 3) & ~walls
    walk &= ~((X - fx > MOAT_IN) & (X - fx < NOTCH_END) & (np.abs(Y - fy) < NOTCH_HALF + 2))
    stats['walkable_slope_max_deg'] = round(float(slope[walk].max()), 2)
    # Cells only (tri has no padding row, whose zeros once read as a flat berm at x 800).
    stats['berm_slope_min_deg'] = round(float(tri[:, ((np.abs(AXIS_Y) > 304) & (np.abs(AXIS_Y) < 312))[:-1]].min()), 1)
    stats['window_edge_height'] = (round(float(H[:, -1][np.abs(AXIS_X) < END_BERM].max()), 3), round(float(drum_z(HALF_Y)), 3))
    if rows is not None:
        stats['scatter'] = {k: len(v) for k, v in rows.items()}
        stats['scatter_total'] = sum(len(v) for v in rows.values())
        stats['keep_clear_violations'] = audit(rows)
    for k, v in stats.items():
        out('  %-28s %s' % (k, v))
    return stats


MESHES = [terrain_tile, water, windows, upper_land_e, upper_land_w, cap_south, cap_north, spine_dim, spine_lit, parapet_w, parapet_e]
VARIANTS = {terrain_tile: plan.TILES_X * plan.TILES_Y}
_TILE = {'size': (2 * HALF_X / plan.TILES_X, 2 * HALF_Y / plan.TILES_Y, 0), 'tol': .01, 'pivot': 'any'}
CONTRACT = {'SM_CD_Terrain_%d_%d' % (i, j): _TILE for i in range(plan.TILES_X) for j in range(plan.TILES_Y)}
CONTRACT.update({
    'SM_CD_Water': {'size': (220, 160, 0), 'tol': .01, 'pivot': 'any'},
    'SM_CD_Windows': {'size': (2 * HALF_X, 2 * R, R + R * math.cos(math.radians(WINDOW_STRIPS[0]))), 'tol': .02, 'pivot': 'any'},
    'SM_CD_UpperLandE': {'size': (2 * HALF_X, R / 2, R * math.cos(math.radians(30))), 'tol': .05, 'pivot': 'any'},
    'SM_CD_UpperLandW': {'size': (2 * HALF_X, R / 2, R * math.cos(math.radians(30))), 'tol': .05, 'pivot': 'any'},
    'SM_CD_CapSouth': {'size': (0, 2 * R, 2 * R), 'tol': .01, 'pivot': 'any'},
    'SM_CD_CapNorth': {'size': (0, 2 * R, 2 * R), 'tol': .01, 'pivot': 'any'},
    'SM_CD_SpineDim': {'size': (SPINE_THIRD, 14, 14), 'tol': .02, 'pivot': 'centre'},
    'SM_CD_SpineLit': {'size': (SPINE_THIRD, 14, 14), 'tol': .02, 'pivot': 'centre'},
    'SM_CD_ParapetW': {'size': (2 * (END_BERM - 3), .6, 0), 'tol': .05, 'pivot': 'any'},
    'SM_CD_ParapetE': {'size': (2 * (END_BERM - 3), .6, 0), 'tol': .05, 'pivot': 'any'},
})


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Write height.bin/json and scatter.json offline and print the report.')
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[2] / 'Art/Meshes/Conclave'))
    args = ap.parse_args()
    write_height(args.out)
    rows = write_scatter(args.out)
    print('wrote', args.out)
    report(rows)
