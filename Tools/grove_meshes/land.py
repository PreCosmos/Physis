"""The land of the Wounded Grove (level 4): the valley's height grid and terrain tiles, its water, the far mountains,
and the layout of everything that is scattered (trees, undergrowth, rocks, thornroot, cliff pieces).

Pure numpy; Tools/build_physis_grove.py turns the Parts into FBX and writes height.bin, height.json and scatter.json
to Art/Meshes/Grove. Every place comes from Content/Python/physis_grove_plan.py (metres; x north, y east, z up).

Terrain vertices do not carry an albedo: the ground material (physis_grove_tools.py, M_GRGround) blends photo-scanned
layers, and each vertex says how much of each it wants:
    colour R  meadow grass        colour G  trodden earth (trails, the camp)     colour B  gravel and sand (river, shores)
    colour A  1 - blight          uv u      asphalt (the old road)                uv v      moss and damp
What is left over is forest floor; rock comes from the slope, in the shader. albedo() gives the same layers as plain
colours for the map art and for previews.

Run alone for the height and scatter report (nothing written):
    PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/grove_meshes/land.py
"""
import functools
import json
from pathlib import Path

from kit import *  # noqa: F401,F403
import physis_grove_plan as plan

CELL = plan.CELL
HALF_X, HALF_Y = plan.HALF_X, plan.HALF_Y
NX, NY = int(round(2 * HALF_X / CELL)) + 1, int(round(2 * HALF_Y / CELL)) + 1     # 641 x 481
AXIS_X = np.linspace(-HALF_X, HALF_X, NX)
AXIS_Y = np.linspace(-HALF_Y, HALF_Y, NY)
TILE_X, TILE_Y = (NX - 1) // plan.TILES_X, (NY - 1) // plan.TILES_Y               # 160 x 160 cells a tile
WATER = plan.WATER
SEED = 4104
CLIFF_FOOT, CLIFF_TOP, CLIFF_RISE = .945, .975, 24.0      # the cliff band at the valley's edge (in rim units) and its height
RIVER_BED = (19.4, 10.0)                                   # the river's bed at the Falls pool and at the weir
POOL_LEVEL = 20.35
TAILWATER = (150.0, plan.WEIR[0] - 3.0, 27.0)              # x from, x to, half width: the lake reaches the weir's foot
WALK_SLOPE = 1.0                                           # tan of the steepest ground a character climbs (45 degrees)
CROSSING_LEVEL = 40.0                                      # both rims of the Rift where it is bridged
PATH_GRADE = .30                                           # the steepest a road or trail runs (17 degrees)


def sstep(a, b, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def sample(grid, x, y):
    """Bilinear sample of a grid on (AXIS_X, AXIS_Y) at metres (vectorised)."""
    fx = np.clip((np.asarray(x, np.float64) + HALF_X) / CELL, 0, NX - 1.001)
    fy = np.clip((np.asarray(y, np.float64) + HALF_Y) / CELL, 0, NY - 1.001)
    i, j = fx.astype(np.int64), fy.astype(np.int64)
    u, v = fx - i, fy - j
    return grid[i, j] * (1 - u) * (1 - v) + grid[i + 1, j] * u * (1 - v) + grid[i, j + 1] * (1 - u) * v + grid[i + 1, j + 1] * u * v


def densify(points, step=1.0):
    """A polyline resampled about every `step` metres: (points, arc length of each)."""
    pts = np.asarray(points, np.float64)
    out, arc, total = [pts[0]], [0.0], 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        length = float(np.linalg.norm(b - a))
        n = max(1, int(np.ceil(length / step)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
            arc.append(total + length * k / n)
        total += length
    return np.array(out), np.array(arc)


def stamp(points, values, reach):
    """For every grid vertex within `reach` metres of a polyline's samples: (distance to the nearest sample, that
    sample's value). Elsewhere distance is inf."""
    dist = np.full((NX, NY), np.inf)
    val = np.zeros((NX, NY))
    r = int(np.ceil(reach / CELL)) + 1
    for (px, py), value in zip(points, values):
        i0, j0 = int(round((px + HALF_X) / CELL)), int(round((py + HALF_Y) / CELL))
        ia, ib, ja, jb = max(i0 - r, 0), min(i0 + r + 1, NX), max(j0 - r, 0), min(j0 + r + 1, NY)
        if ia >= ib or ja >= jb:
            continue
        d = np.hypot(AXIS_X[ia:ib, None] - px, AXIS_Y[None, ja:jb] - py)
        window, values_window = dist[ia:ib, ja:jb], val[ia:ib, ja:jb]
        closer = d < window
        window[closer] = d[closer]
        values_window[closer] = value
    return dist, val


def smooth_along(values, width):
    kernel = np.ones(width) / width
    padded = np.concatenate([np.full(width // 2, values[0]), values, np.full(width - width // 2 - 1, values[-1])])
    return np.convolve(padded, kernel, mode='valid')


# ---------------------------------------------------------------- the height field

def _base(X, Y):
    """The broad land: a Gaussian blend of the plan's heights, with two octaves of undulation."""
    num = np.full(X.shape, 36.0 * 2e-3)
    den = np.full(X.shape, 2e-3)
    for x, y, h, reach in plan.HEIGHTS:
        w = np.exp(-((X - x) ** 2 + (Y - y) ** 2) / (2 * reach * reach))
        num += w * h
        den += w
    H = num / den
    H += 3.2 * fbm(X, Y, SEED, 4, 1 / 190.0) + 1.0 * fbm(X, Y, SEED + 31, 3, 1 / 46.0)
    return H


def _gully_x(Y):
    return plan.GULLY_X + plan.GULLY_WAVE * np.sin(Y / plan.GULLY_PERIOD + 1.0)


def _limit_grade(z, arc, grade):
    """A path's profile with no step steeper than `grade` (rise over run): highs are cut down, from both ends."""
    z = np.array(z, np.float64)
    step = np.diff(arc) * grade
    for k in range(1, len(z)):
        z[k] = min(z[k], z[k - 1] + step[k - 1])
    for k in range(len(z) - 2, -1, -1):
        z[k] = min(z[k], z[k + 1] + step[k])
    return z


def _shape():
    X, Y = np.meshgrid(AXIS_X, AXIS_Y, indexing='ij')
    H = _base(X, Y)
    hx, hy = plan.HEARTWOOD
    wx, wy = plan.WEIR
    R = np.hypot(X - hx, Y - hy)

    # The Heartwood's knoll and the Relay's mesa.
    H = H + (plan.KNOLL_TOP - H) * (1 - sstep(plan.KNOLL_RADIUS, plan.RIFT_IN - 2.0, R))
    mesa = np.hypot(X - plan.RELAY[0], Y - plan.RELAY[1])
    H = H + (plan.RELAY_TOP - H) * (1 - sstep(plan.RELAY_RADIUS, plan.RELAY_RADIUS + 9.0, mesa))

    # The valley's edge: a cliff band, then the mountain.
    rim = np.hypot(X / plan.RIM[0], Y / plan.RIM[1])
    ridges = 1 - np.abs(fbm(X, Y, SEED + 77, 4, 1 / 150.0))
    H = H + CLIFF_RISE * sstep(CLIFF_FOOT, CLIFF_TOP, rim) * (.8 + .4 * noise2(X / 37.0, Y / 37.0, SEED + 5) ** 2)
    H = H + plan.RIM_RISE * sstep(.96, plan.RIM_END, rim) ** 1.2 * (.75 + .35 * ridges)

    # Level ground for the set pieces.
    for x, y, radius, level in plan.PADS:
        d = np.hypot(X - x, Y - y)
        if level is None:
            level = float(H[d < radius * .6].mean())
        H = H + (level - H) * (1 - sstep(radius, radius + 9.0, d))

    # The river: from the Falls pool down its bed to the headpond behind the weir.
    rpts, rarc = densify(plan.RIVER, 1.0)
    bed = RIVER_BED[0] + (RIVER_BED[1] - RIVER_BED[0]) * rarc / rarc[-1]
    river_d, river_z = stamp(rpts, bed, 26.0)
    w = 1 - sstep(plan.RIVER_HALF * .7, plan.RIVER_HALF + 13.0, river_d)
    H = np.where(np.isfinite(river_d), np.minimum(H, H + (river_z - H) * w), H)
    pond = (1 - sstep(plan.WEIR_HALF - 6.0, plan.WEIR_HALF + 2.0, np.abs(Y - wy))) * sstep(wx + 1.0, wx + 4.0, X) * (1 - sstep(wx + 44.0, wx + 60.0, X))
    H = np.minimum(H, H + (RIVER_BED[1] - H) * pond)
    pool = np.hypot(X - plan.FALLS_POOL[0], Y - plan.FALLS_POOL[1])
    H = np.minimum(H, H + (RIVER_BED[0] - H) * (1 - sstep(8.0, 13.0, pool)))

    # The lake (the Drowned Campus) and the tailwater below the weir.
    cx, cy, ax, ay = plan.LAKE
    lake = np.hypot((X - cx) / ax, (Y - cy) / ay)
    bowl = WATER + plan.LAKE_BED * np.clip(1 - lake ** 2.4, 0, 1) - .25
    shore = WATER - .25 + 1.6 * sstep(1.0, 1.10, lake)
    H = np.where(lake < 1.0, bowl, H + (shore - H) * (1 - sstep(1.10, 1.42, lake)) * (lake >= 1.0))
    tail = (1 - sstep(TAILWATER[2] - 5.0, TAILWATER[2] + 3.0, np.abs(Y - wy))) * sstep(TAILWATER[0] - 12.0, TAILWATER[0] + 6.0, X) * (X < wx - 3.0)
    H = np.minimum(H, H + (WATER - 1.6 - H) * tail)
    foot = (np.abs(X - wx) < 4.5) & (np.abs(Y - wy) < plan.WEIR_HALF + 1.0)
    H = np.where(foot, WATER + .3, H)                                         # the weir stands on this sill
    # The weir's east bank stands at the deck's height (the lake's shore would pull it down).
    bx, by = plan.WEIR_BANK
    H = H + (plan.WEIR_CREST - H) * (1 - sstep(9.0, 17.0, np.hypot(X - bx, Y - by))) * (X > wx - 2.0)

    # The crossings: both rims of the Rift at one height on the three bearings where it is bridged, and both banks of
    # the Gully where its bridge will grow, so a level deck meets level ground at each end. Done before the paths (their
    # profiles then run up to the crossings) and again after them (their levelling must not move a crossing).
    gx = _gully_x(Y)
    gd = np.abs(X - gx)
    gully_level = float(sample(H, plan.gully_x(plan.GULLY_CROSS_Y), plan.GULLY_CROSS_Y))

    def crossings(H):
        for bearing in (plan.WEST_BEARING, plan.EAST_BEARING, plan.SOUTH_BEARING):
            a = np.radians(bearing)
            radial = (X - hx) * np.cos(a) + (Y - hy) * np.sin(a)
            lateral = np.abs(-(X - hx) * np.sin(a) + (Y - hy) * np.cos(a))
            w = (1 - sstep(5.0, 11.0, lateral)) * sstep(plan.RIFT_IN - 28.0, plan.RIFT_IN - 13.0, radial) * (1 - sstep(plan.RIFT_OUT + 9.0, plan.RIFT_OUT + 27.0, radial))
            H = H + (CROSSING_LEVEL - H) * w
        w = (1 - sstep(5.0, 11.0, np.abs(Y - plan.GULLY_CROSS_Y))) * (1 - sstep(plan.GULLY_RIM + 9.0, plan.GULLY_RIM + 26.0, gd))
        return H + (gully_level - H) * w
    H = crossings(H)

    # Roads and trails: each levelled across its width along a smoothed profile of the land it crosses, never
    # steeper than PATH_GRADE (the land is cut where it must be).
    path_d = np.full(X.shape, np.inf)
    path_half = np.zeros(X.shape)
    road = np.zeros(X.shape, bool)
    soft = blur(H, 3)
    for _name, kind, half, points in plan.PATHS:
        pts, arc = densify(points, 1.0)
        z = _limit_grade(smooth_along(sample(soft, pts[:, 0], pts[:, 1]), 31), arc, PATH_GRADE)
        d, target = stamp(pts, z, half + 7.0)
        w = 1 - sstep(half + .5, half + 6.0, d)
        H = H + (target - H) * w
        closer = d < path_d
        path_d[closer] = d[closer]
        path_half[closer] = half
        road[closer] = kind == 'road'
    H = crossings(H)

    # The Gully: a dry gorge across the whole valley, with one ramp out on its south side.
    rim_h = blur(H, 3)
    gully = (1 - sstep(plan.GULLY_FLOOR, plan.GULLY_RIM, gd)) * (1 - sstep(CLIFF_FOOT - .012, CLIFF_FOOT + .012, rim))   # it ends at the cliffs
    H = H - plan.GULLY_DEPTH * gully
    ramp_len = 26.0
    along = np.clip((X - (gx - plan.GULLY_RIM - ramp_len)) / (ramp_len + plan.GULLY_RIM - plan.GULLY_FLOOR + 2.0), 0, 1)
    across = 1 - sstep(3.5, 5.5, np.abs(Y - plan.GULLY_RAMP_Y))
    on_ramp = across * (X > gx - plan.GULLY_RIM - ramp_len) * (X < gx - plan.GULLY_FLOOR + 2.0)
    H = H + ((rim_h - plan.GULLY_DEPTH * along) - H) * on_ramp

    # The Rift: a ring gorge round the Heartwood, with one ramp out on its outer side.
    ring = sstep(plan.RIFT_IN, plan.RIFT_IN + plan.RIFT_WALL, R) * (1 - sstep(plan.RIFT_OUT - plan.RIFT_WALL, plan.RIFT_OUT, R))
    rim_h = blur(H, 3)
    H = H - plan.RIFT_DEPTH * ring
    ea = np.radians(plan.EXIT_BEARING)
    ex, ey = np.cos(ea), np.sin(ea)
    radial = (X - hx) * ex + (Y - hy) * ey
    lateral = np.abs(-(X - hx) * ey + (Y - hy) * ex)
    ramp_len = 28.0
    climb = np.clip((radial - (plan.RIFT_OUT - plan.RIFT_WALL - 1.0)) / ramp_len, 0, 1)
    on_ramp = (1 - sstep(3.5, 5.5, lateral)) * (radial > plan.RIFT_OUT - plan.RIFT_WALL - 1.0) * (radial < plan.RIFT_OUT + ramp_len - 2.0)
    H = H + ((rim_h - plan.RIFT_DEPTH * (1 - climb)) - H) * on_ramp

    return {'X': X, 'Y': Y, 'H': H, 'rim': rim, 'R': R, 'lake': lake, 'gully_d': gd, 'gully': gully, 'ring': ring,
            'path_d': path_d, 'path_half': path_half, 'road': road, 'river_d': river_d, 'pond': pond, 'mesa': mesa}


def _circles(X, Y, rows, pad=0.0):
    """1 inside any (x, y, radius) circle, falling to 0 over `pad` metres outside it."""
    out = np.zeros(X.shape)
    for x, y, radius in rows:
        d = np.hypot(X - x, Y - y)
        out = np.maximum(out, 1 - sstep(radius, radius + max(pad, 1e-6), d))
    return out


def _layers(G):
    """The ground's layer weights and the masks the layout reads."""
    X, Y, H = G['X'], G['Y'], G['H']
    gx, gy = np.gradient(H, CELL)
    slope = np.hypot(gx, gy)
    inside = G['rim'] < CLIFF_FOOT
    # Forest and glade: mostly forest, with meadows where a slow noise opens it and round the places people use.
    glade = sstep(.30, .52, fbm(X, Y, SEED + 211, 3, 1 / 150.0))
    used = _circles(X, Y, [(x, y, r * .8) for x, y, r, _ in plan.PADS], 14.0)
    forest = np.clip(1 - np.maximum(glade, used), 0, 1) * inside
    blight = np.zeros(X.shape)
    for x, y, radius in plan.BLIGHT:
        d = np.hypot(X - x, Y - y)
        blight = np.maximum(blight, (1 - sstep(radius * .45, radius, d)))
    blight = np.clip(blight * (.55 + .7 * (.5 + .5 * noise2(X / 23.0, Y / 23.0, SEED + 9))), 0, 1)
    wet = np.maximum(1 - sstep(4.0, 30.0, G['river_d']), 1 - sstep(1.0, 1.35, G['lake']))
    wet = np.maximum(wet, np.maximum(G['gully'], G['ring']))
    # gravel and sand: the river's bed, the lake's shore and bed, the pool
    gravel = np.maximum(1 - sstep(plan.RIVER_HALF * .8, plan.RIVER_HALF + 5.0, G['river_d']), 1 - sstep(1.02, 1.16, G['lake']))
    gravel = np.maximum(gravel, G['pond'])
    gravel = np.maximum(gravel, G['gully'] * .7)
    half = np.where(np.isfinite(G['path_d']), G['path_half'], 1.0)
    on_path = 1 - sstep(half * .75, half + 1.6, G['path_d'])
    cracks = .5 + .5 * noise2(X / 3.1, Y / 3.1, SEED + 41)
    asphalt = on_path * G['road'] * sstep(.18, .5, cracks + .25 * (1 - sstep(half * .4, half, G['path_d'])))
    dirt = on_path * (~G['road']) + .55 * on_path * G['road'] * (1 - asphalt)
    dirt = np.maximum(dirt, .8 * _circles(X, Y, [(plan.CAMP[0], plan.CAMP[1], 16.0), (plan.GRAFT[0], plan.GRAFT[1], 6.0),
                                                  (plan.UNDERSTORY[0], plan.UNDERSTORY[1], 7.0)], 9.0))
    grass = np.clip(np.maximum(glade, used * .8) * (1 - .8 * blight), 0, 1) * (1 - gravel) * inside
    grass = grass * (1 - np.clip(dirt + asphalt, 0, 1))
    moss = np.clip(wet * .8 + .35 * forest * (.5 + .5 * noise2(X / 31.0, Y / 31.0, SEED + 53)) + .5 * sstep(.25, .7, slope) * forest, 0, 1)
    moss = moss * (1 - np.clip(dirt + asphalt + gravel, 0, 1)) * (1 - blight)
    # The Array's court is paved by the scenario's own pieces; the ground under it is bare, blighted earth.
    court = G['R'] < plan.ARRAY_WALL + 2.0
    grass = np.where(court, 0.0, grass)
    dirt = np.where(court, np.maximum(dirt, .6), dirt)
    return {'slope': slope, 'forest': forest, 'glade': glade, 'blight': blight, 'wet': wet, 'gravel': np.clip(gravel, 0, 1),
            'asphalt': np.clip(asphalt, 0, 1), 'dirt': np.clip(dirt, 0, 1), 'grass': np.clip(grass, 0, 1), 'moss': moss,
            'inside': inside, 'on_path': on_path}


_GRID = {}


def grid():
    """The valley floor: heights (metres), layer weights and masks on the 641 x 481 grid."""
    if not _GRID:
        G = _shape()
        G.update(_layers(G))
        G['H'] = G['H'].astype(np.float32)
        _GRID.update(G)
    return _GRID


def height_at(x, y):
    return sample(grid()['H'], x, y)


# Plain colours of the layers, for the map art and previews (the game uses scanned textures instead).
LAYER_COLOURS = {'forest': (.070, .060, .034), 'grass': (.095, .170, .045), 'dirt': (.150, .110, .070), 'gravel': (.300, .280, .240),
                 'asphalt': (.050, .050, .054), 'moss': (.060, .110, .030), 'blight': (.050, .030, .050), 'rock': (.210, .205, .195)}


def albedo():
    """(NX, NY, 3) linear colours of the ground as the layers would paint it."""
    G = grid()
    c = np.empty(G['H'].shape + (3,))
    c[:] = LAYER_COLOURS['forest']
    for name in ('moss', 'grass', 'gravel', 'dirt', 'asphalt'):
        w = G[name][..., None]
        c = c * (1 - w) + np.array(LAYER_COLOURS[name]) * w
    c = c * (1 - G['blight'][..., None] * .75) + np.array(LAYER_COLOURS['blight']) * G['blight'][..., None] * .75
    rock = sstep(.75, 1.15, G['slope'])[..., None]
    return c * (1 - rock) + np.array(LAYER_COLOURS['rock']) * rock


# ---------------------------------------------------------------- terrain tiles, water, the backdrop

@functools.lru_cache(maxsize=1)
def vertex_normals():
    gx, gy = np.gradient(grid()['H'].astype(np.float64), CELL)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def _grid_faces(mx, my):
    idx = np.arange(mx * my).reshape(mx, my)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    return np.stack([a, b, c, d], 1).tolist()      # counter-clockwise seen from above


def terrain_tile(k):
    """SM_GT_Terrain_<i>_<j> (k = i * TILES_Y + j): one 320 m tile in world metres; neighbours share their edge rows.
    Colour and uv carry the layer weights (module docstring); `normals` are the whole grid's, so seams shade as one."""
    i, j = divmod(k, plan.TILES_Y)
    G = grid()
    xs, ys = slice(i * TILE_X, (i + 1) * TILE_X + 1), slice(j * TILE_Y, (j + 1) * TILE_Y + 1)
    px, py, ph = G['X'][xs, ys], G['Y'][xs, ys], G['H'][xs, ys].astype(np.float64)
    weights = np.stack([G['grass'][xs, ys], G['dirt'][xs, ys], G['gravel'][xs, ys], 1 - G['blight'][xs, ys]], -1).reshape(-1, 4)
    uv = np.stack([G['asphalt'][xs, ys], G['moss'][xs, ys]], -1).reshape(-1, 2)
    p = Part('SM_GT_Terrain_%d_%d' % (i, j), (GROUND,))
    p.add(np.stack([px.ravel(), py.ravel(), ph.ravel()], 1), _grid_faces(*px.shape), weights, 0, True, uv=uv)
    p.normals = vertex_normals()[xs, ys].reshape(-1, 3)
    return p


def _sheet(name, x0, x1, y0, y1, z, step=4.0):
    p = Part(name, (WATER_SLOT,))
    xs, ys = np.arange(x0, x1 + step * .5, step), np.arange(y0, y1 + step * .5, step)
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    p.add(np.stack([gx.ravel(), gy.ravel(), np.full(gx.size, z)], 1), _grid_faces(*gx.shape), WATER_COLOUR, 0, True)
    return p


WATER_SLOT = WATER if isinstance(WATER, str) else 'CN_Water'    # kit.WATER is the slot name; plan.WATER the level
WATER_SLOT = 'CN_Water'
WATER = plan.WATER
WATER_COLOUR = col(.30, .42, .40)


def lake():
    """SM_GT_Lake: the lake's surface at z 0, over the flooded campus and the tailwater below the weir."""
    cx, cy, ax, ay = plan.LAKE
    return _sheet('SM_GT_Lake', cx - ax - 12, plan.WEIR[0] - 2.0, cy - ay - 12, cy + ay + 12, plan.WATER)


def headpond():
    """SM_GT_Headpond: the water held behind the weir."""
    wx, wy = plan.WEIR
    return _sheet('SM_GT_Headpond', wx + 2.0, wx + 62.0, wy - plan.WEIR_HALF - 3.0, wy + plan.WEIR_HALF + 3.0, plan.HEADPOND, 3.0)


def river():
    """SM_GT_River: the stream from the Falls pool to the headpond, a ribbon 0.3 m over its bed, and the pool."""
    p = Part('SM_GT_River', (WATER_SLOT,))
    pts, arc = densify(plan.RIVER, 2.0)
    bed = RIVER_BED[0] + (RIVER_BED[1] - RIVER_BED[0]) * arc / arc[-1]
    level = np.maximum(bed + .32, plan.HEADPOND)
    tang = np.gradient(pts, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    side = np.stack([-tang[:, 1], tang[:, 0]], 1)
    half = plan.RIVER_HALF * .86
    left, right = pts - side * half, pts + side * half
    verts = np.concatenate([np.column_stack([left, level]), np.column_stack([right, level])])
    n = len(pts)
    faces = [[k, k + 1, n + k + 1, n + k] for k in range(n - 1)]
    faces = [f if np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]])[2] > 0 else f[::-1] for f in faces]
    uv = np.concatenate([np.column_stack([np.zeros(n), arc / 12.0]), np.column_stack([np.ones(n), arc / 12.0])])
    p.add(verts, faces, WATER_COLOUR, 0, True, uv=uv % 1.0 if False else uv)
    ang = np.linspace(0, TAU, 28, endpoint=False)
    disc = np.column_stack([plan.FALLS_POOL[0] + np.cos(ang) * 12.5, plan.FALLS_POOL[1] + np.sin(ang) * 12.5, np.full(28, POOL_LEVEL)])
    centre = np.array([[plan.FALLS_POOL[0], plan.FALLS_POOL[1], POOL_LEVEL]])
    p.add(np.concatenate([centre, disc]), [[0, 1 + k, 1 + (k + 1) % 28] for k in range(28)], WATER_COLOUR, 0, True)
    return p


def falls_line():
    """Where the waterfall leaves the cliff: (lip x, y, z) above the pool, found by walking from the pool toward
    plan.FALLS until the land stands 30 m over the pool."""
    px, py = plan.FALLS_POOL
    d = np.array([plan.FALLS[0] - px, plan.FALLS[1] - py])
    d /= np.linalg.norm(d)
    for step in np.arange(8.0, 140.0, 1.0):
        x, y = px + d[0] * step, py + d[1] * step
        h = float(height_at(x, y))
        if h > POOL_LEVEL + 30.0:
            return (x, y, h), d
    return (plan.FALLS[0], plan.FALLS[1], float(height_at(*plan.FALLS))), d


def falls():
    """SM_GT_Falls: the waterfall, three overlapping sheets from the lip down to the pool, in world metres. uv v runs
    down the fall (the material scrolls along it)."""
    (lx, ly, lz), d = falls_line()
    px, py = plan.FALLS_POOL
    side = np.array([-d[1], d[0]])
    p = Part('SM_GT_Falls', (WATER_SLOT,))
    reach = np.hypot(lx - px, ly - py) - 7.0
    for k, (offset, width, lift) in enumerate(((0.0, 7.0, 0.0), (-2.2, 4.5, .6), (2.6, 3.8, 1.0))):
        n = 22
        t = np.linspace(0, 1, n)
        out = reach * (1 - t * .92) + lift          # distance from the pool's centre: the sheet arcs outward as it falls
        z = lz + .2 - (lz + .2 - POOL_LEVEL) * t ** 1.7
        centre = np.column_stack([px + d[0] * out + side[0] * offset, py + d[1] * out + side[1] * offset, z])
        w = width * (.5 + .1 * t)
        left = centre - np.column_stack([side[0] * w, side[1] * w, np.zeros(n)])
        right = centre + np.column_stack([side[0] * w, side[1] * w, np.zeros(n)])
        verts = np.concatenate([left, right])
        faces = [[i, n + i, n + i + 1, i + 1] for i in range(n - 1)] + [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)]
        uv = np.concatenate([np.column_stack([np.full(n, k * .3), t * 3.0]), np.column_stack([np.full(n, k * .3 + .7), t * 3.0])])
        p.add(verts, faces, col(.75, .80, .82), 0, True, uv=uv)
    return p


def backdrop():
    """SM_GT_Backdrop: the mountains beyond the valley, from the terrain grid's edge out to 4 km: forested slopes
    rising to rock. Vertex colour is their albedo (the far haze is the level's fog). No collision."""
    G = grid()
    H = G['H'].astype(np.float64)
    segs, rings = 160, 13
    ang = np.linspace(0, TAU, segs, endpoint=False)
    ca, sa = np.cos(ang), np.sin(ang)
    # the grid's rectangle along each bearing, 6 m inside its edge, so the two overlap
    edge = np.minimum((HALF_X - 6.0) / np.maximum(np.abs(ca), 1e-6), (HALF_Y - 6.0) / np.maximum(np.abs(sa), 1e-6))
    t = np.linspace(0, 1, rings) ** 1.7
    verts, cols = [], []
    for k in range(rings):
        r = edge + (4000.0 - edge) * t[k]
        x, y = ca * r, sa * r
        far = 260.0 + 420.0 * (1 - np.abs(fbm(x, y, SEED + 303, 5, 1 / 900.0))) * sstep(0, .5, t[k]) * (1 - .5 * t[k])
        near = sample(H, np.clip(x, -HALF_X, HALF_X), np.clip(y, -HALF_Y, HALF_Y))
        z = near + (far - near) * sstep(0.0, .22, t[k])
        z = z - 700.0 * sstep(.82, 1.0, t[k])
        verts.append(np.column_stack([x, y, z]))
        rocky = sstep(330.0, 520.0, z) * (.5 + .5 * noise2(x / 160.0, y / 160.0, SEED + 3))
        base = np.array([.030, .055, .026]) * (1 - rocky[:, None]) + np.array([.20, .20, .19]) * rocky[:, None]
        cols.append(np.column_stack([base * (.8 + .4 * noise2(x / 90.0, y / 90.0, SEED + 8))[:, None], np.ones(segs)]))
    v = np.concatenate(verts)
    faces = [[k * segs + j, k * segs + (j + 1) % segs, (k + 1) * segs + (j + 1) % segs, (k + 1) * segs + j]
             for k in range(rings - 1) for j in range(segs)]
    p = Part('SM_GT_Backdrop', (ROCK,))
    p.add(v, faces, np.clip(np.concatenate(cols), 0, .9), 0, True)
    return p


# ---------------------------------------------------------------- scatter layout
# {name: [[x_cm, y_cm, z_cm, pitch, yaw, roll, scale], ...]}. Names starting SM_GV_ are instanced vegetation classes
# (physis_grove_tools maps each class to its meshes, scanned or generated); 'Bloom:<mesh>' rows are shown only once the
# grove is healed; 'Cliff:<where>' rows are places for cliff pieces (scale = the wall's height in metres, yaw = the
# way the rock face looks).

def _row(x, y, z, yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
    return [round(float(x) * 100, 1), round(float(y) * 100, 1), round(float(z) * 100, 1), round(float(pitch), 2), round(float(yaw), 2),
            round(float(roll), 2), round(float(scale), 3)]


class _Layout:
    def __init__(self):
        self.G = grid()
        G = self.G
        X, Y = G['X'], G['Y']
        clear = _circles(X, Y, plan.KEEP_CLEAR, 0.0) > 0
        half = np.where(np.isfinite(G['path_d']), G['path_half'], 0.0)
        self.no_tree = (clear | (G['path_d'] < half + 3.5) | (G['lake'] < 1.08) | (G['gully_d'] < plan.GULLY_RIM + 2.5) |
                        ((G['R'] > plan.RIFT_IN - 3.0) & (G['R'] < plan.RIFT_OUT + 3.0)) | (G['R'] < plan.ARRAY_WALL + 4.0) |
                        (G['river_d'] < plan.RIVER_HALF + 3.0) | (G['pond'] > .05) | (G['mesa'] < plan.RELAY_RADIUS + 10.0))
        self.no_plant = (clear | (G['path_d'] < half + .8) | (G['lake'] < 1.02) | (G['gully_d'] < plan.GULLY_FLOOR) |
                         (G['ring'] > .5) | (G['R'] < plan.ARRAY_WALL + 1.0) | (G['river_d'] < plan.RIVER_HALF * .8) | (G['pond'] > .3))
        self.rows = {}

    def put(self, name, x, y, yaw, scale, sink=0.0, pitch=0.0, roll=0.0):
        z = sample(self.G['H'], x, y) - sink
        rows = self.rows.setdefault(name, [])
        for k in range(len(x)):
            rows.append(_row(x[k], y[k], z[k], yaw[k], pitch if np.isscalar(pitch) else pitch[k], roll if np.isscalar(roll) else roll[k], scale[k]))

    def candidates(self, rng, cell, x0=-HALF_X + 8, x1=HALF_X - 8, y0=-HALF_Y + 8, y1=HALF_Y - 8):
        """One jittered point per `cell` metre square: a blue-noise-like cover."""
        xs, ys = np.arange(x0, x1, cell), np.arange(y0, y1, cell)
        gx, gy = np.meshgrid(xs, ys, indexing='ij')
        return (gx + rng.uniform(.1, .9, gx.shape) * cell).ravel(), (gy + rng.uniform(.1, .9, gy.shape) * cell).ravel()

    def at(self, field, x, y):
        return sample(self.G[field].astype(np.float64) if not isinstance(field, np.ndarray) else field.astype(np.float64), x, y)


def _trees(L):
    G = L.G
    rng = np.random.default_rng(SEED + 1)
    x, y = L.candidates(rng, 8.5)
    rim = np.hypot(x / plan.RIM[0], y / plan.RIM[1])
    slope = L.at('slope', x, y)
    forest = L.at('forest', x, y)
    blocked = L.at(L.no_tree, x, y) > .01
    blight = L.at('blight', x, y)
    # inside the valley: by the forest's density; on the mountain above the cliff: sparser, wherever a tree could stand
    inside = rim < CLIFF_FOOT - .012
    above = (rim > CLIFF_TOP + .02) & (slope < 1.35)
    chance = np.where(inside, .25 + .72 * forest, np.where(above, .5, 0.0)) * (slope < np.where(inside, .85, 1.35))
    keep = (rng.uniform(0, 1, len(x)) < chance) & ~blocked
    x, y, rim, slope, blight, inside = x[keep], y[keep], rim[keep], slope[keep], blight[keep], inside[keep]
    wet = L.at('wet', x, y)
    north = np.clip((x + 200.0) / 600.0, 0, 1)
    canopy = np.exp(-((x - plan.REGIONS['The High Canopy'][0]) ** 2 + (y - plan.REGIONS['The High Canopy'][1]) ** 2) / (2 * 120.0 ** 2))
    w = np.stack([
        .55 - .3 * north + .5 * canopy,                                   # Oak
        .40 + .25 * np.clip(slope, 0, .6) + .4 * canopy,                  # Beech
        .12 + .7 * north + 1.6 * (~inside) + .5 * np.clip(slope - .3, 0, 1),   # Pine
        .16 + .7 * wet + .25 * (L.at('glade', x, y) > .3),                # Birch
    ], 1)
    w = np.clip(w, 0.02, None)
    pick = (rng.uniform(0, 1, len(x))[:, None] > np.cumsum(w / w.sum(1, keepdims=True), 1)).sum(1).clip(0, 3)
    names = np.array(['SM_GV_Oak', 'SM_GV_Beech', 'SM_GV_Pine', 'SM_GV_Birch'])[pick]
    dead = inside & (rng.uniform(0, 1, len(x)) < blight * .75)
    names = np.where(dead, 'SM_GV_Snag', names)
    scale = rng.uniform(.82, 1.28, len(x)) * (1 + .35 * canopy) * np.where(blight > .4, .85, 1.0)
    yaw = rng.uniform(0, 360, len(x))
    for name in sorted(set(names.tolist())):
        m = names == name
        L.put(str(name), x[m], y[m], yaw[m], scale[m], sink=.25 + .5 * slope[m])
    return x, y


def _understory(L, tree_x, tree_y):
    G = L.G
    rng = np.random.default_rng(SEED + 2)

    def spread(name, cell, chance, scale=(.8, 1.25), sink=.03, limit_slope=.9, mask=None, tilt=0.0):
        x, y = L.candidates(rng, cell)
        ok = (np.hypot(x / plan.RIM[0], y / plan.RIM[1]) < CLIFF_FOOT - .004) & (L.at('slope', x, y) < limit_slope)
        ok &= L.at(L.no_plant if mask is None else mask, x, y) < .01
        ok &= rng.uniform(0, 1, len(x)) < chance(x, y)
        x, y = x[ok], y[ok]
        n = len(x)
        L.put(name, x, y, rng.uniform(0, 360, n), rng.uniform(scale[0], scale[1], n), sink,
              rng.uniform(-tilt, tilt, n) if tilt else 0.0, rng.uniform(-tilt, tilt, n) if tilt else 0.0)
        return x, y
    f = lambda name: (lambda x, y: L.at(name, x, y))   # noqa: E731
    spread('SM_GV_Sapling', 11.0, lambda x, y: .10 + .25 * f('glade')(x, y) * f('forest')(x, y) + .2 * (f('on_path')(x, y) > .05), mask=L.no_tree)
    spread('SM_GV_Bush', 6.5, lambda x, y: (.10 + .30 * f('forest')(x, y) + .15 * f('wet')(x, y)) * (1 - .7 * f('blight')(x, y)), mask=L.no_tree)
    spread('SM_GV_Fern', 2.6, lambda x, y: (.06 + .50 * f('forest')(x, y) * (.4 + .6 * f('moss')(x, y))) * (1 - f('blight')(x, y)))
    spread('SM_GV_Grass', 1.7, lambda x, y: (.10 * f('forest')(x, y) + .92 * f('grass')(x, y)) * (1 - f('blight')(x, y) * .9))
    spread('SM_GV_Flowers', 3.2, lambda x, y: .34 * f('grass')(x, y) * (1 - f('blight')(x, y)))
    spread('SM_GV_Rock0', 21.0, lambda x, y: .16 + .5 * (f('slope')(x, y) > .45) + .3 * f('wet')(x, y), (.6, 1.7), .35, 1.2, L.no_tree, 6.0)
    spread('SM_GV_Rock1', 27.0, lambda x, y: .12 + .5 * (f('slope')(x, y) > .5), (.7, 1.8), .3, 1.3, L.no_tree, 5.0)
    lx, ly = spread('SM_GV_Log', 34.0, lambda x, y: .42 * f('forest')(x, y), (.8, 1.3), .12, .5, L.no_tree, 3.0)
    spread('SM_GV_Thorn', 8.0, lambda x, y: .75 * np.clip(f('blight')(x, y) - .25, 0, 1), (.7, 1.5), .15, 1.0, L.no_tree)
    spread('Bloom:SM_GV_Flowers', 3.0, lambda x, y: .5 * np.clip(f('blight')(x, y) - .2, 0, 1))
    spread('Bloom:SM_GV_Fern', 4.0, lambda x, y: .35 * np.clip(f('blight')(x, y) - .2, 0, 1))
    # mushrooms beside the logs
    if len(lx):
        k = rng.integers(1, 4, len(lx))
        mx = np.repeat(lx, k) + rng.normal(0, 1.4, k.sum())
        my = np.repeat(ly, k) + rng.normal(0, 1.4, k.sum())
        L.put('SM_GV_Mushrooms', mx, my, rng.uniform(0, 360, len(mx)), rng.uniform(.7, 1.5, len(mx)))
    # thornroot along both rims of the Rift
    hx, hy = plan.HEARTWOOD
    for radius, count in ((plan.RIFT_IN - 5.0, 62), (plan.RIFT_OUT + 5.0, 74)):
        a = np.linspace(0, TAU, count, endpoint=False) + rng.uniform(-.03, .03, count)
        x, y = hx + np.cos(a) * radius, hy + np.sin(a) * radius
        keep = np.ones(count, bool)
        for bx, by in (plan.WEST_CROSSING, plan.EAST_CROSSING, plan.SOUTH_CROSSING, plan.RIFT_EXIT, plan.MAST):
            keep &= np.hypot(x - bx, y - by) > 17.0
        L.put('SM_GV_Thorn', x[keep], y[keep], np.degrees(a[keep]) + rng.uniform(-40, 40, keep.sum()), rng.uniform(.9, 1.6, keep.sum()), .15)


def _water_plants(L):
    G = L.G
    rng = np.random.default_rng(SEED + 3)
    cx, cy, ax, ay = plan.LAKE
    x, y = L.candidates(rng, 2.2, cx - ax - 8, cx + ax + 8, cy - ay - 8, cy + ay + 8)
    h = sample(G['H'].astype(np.float64), x, y)
    belts = .5 + .5 * noise2(x / 17.0, y / 17.0, SEED + 61)
    clear = L.at(_circles(G['X'], G['Y'], plan.KEEP_CLEAR, 0.0), x, y) < .01
    reeds = (h > -.7) & (h < .25) & (belts > .55) & (rng.uniform(0, 1, len(x)) < .6) & clear
    L.rows.setdefault('SM_GV_Reeds', []).extend(_row(a, b, max(c, plan.WATER - .5), rng.uniform(0, 360), 0, 0, rng.uniform(.8, 1.3))
                                                for a, b, c in zip(x[reeds], y[reeds], h[reeds]))
    lily = (h > -2.2) & (h < -.6) & (belts < .4) & (rng.uniform(0, 1, len(x)) < .32) & clear
    L.rows.setdefault('SM_GV_Lily', []).extend(_row(a, b, plan.WATER + .02, rng.uniform(0, 360), 0, 0, rng.uniform(.8, 1.4))
                                               for a, b in zip(x[lily], y[lily]))


def _cliffs(L):
    """Places for cliff pieces: the valley's edge, both walls of the Gully and of the Rift, and the Relay's mesa."""
    G = L.G
    H = G['H'].astype(np.float64)
    rows = L.rows
    # the valley's edge, along the middle of the cliff band, facing in
    band = (CLIFF_FOOT + CLIFF_TOP) / 2
    count = 190
    a = np.linspace(0, TAU, count, endpoint=False)
    x, y = np.cos(a) * plan.RIM[0] * band, np.sin(a) * plan.RIM[1] * band
    nx, ny = -np.cos(a) / plan.RIM[0], -np.sin(a) / plan.RIM[1]
    yaw = np.degrees(np.arctan2(ny, nx))
    foot = sample(H, np.cos(a) * plan.RIM[0] * (CLIFF_FOOT - .01), np.sin(a) * plan.RIM[1] * (CLIFF_FOOT - .01))
    rows['Cliff:rim'] = [_row(x[k], y[k], foot[k], yaw[k], 0, 0, CLIFF_RISE + 6.0) for k in range(count)]
    # the Gully's two walls
    ys = np.arange(-388.0, 389.0, 9.0)
    out = []
    for side in (-1, 1):
        gx = plan.GULLY_X + plan.GULLY_WAVE * np.sin(ys / plan.GULLY_PERIOD + 1.0) + side * (plan.GULLY_FLOOR + plan.GULLY_RIM) / 2
        for k, yy in enumerate(ys):
            if np.hypot(gx[k] / plan.RIM[0], yy / plan.RIM[1]) > CLIFF_FOOT or (side < 0 and abs(yy - plan.GULLY_RAMP_Y) < 8.0):
                continue
            top = float(sample(H, gx[k] + side * 4.0, yy))
            out.append(_row(gx[k], yy, top - plan.GULLY_DEPTH, 0.0 if side < 0 else 180.0, 0, 0, plan.GULLY_DEPTH + 1.0))
    rows['Cliff:gully'] = out
    # the Rift's two walls
    hx, hy = plan.HEARTWOOD
    out = []
    for radius, facing, count in ((plan.RIFT_IN + plan.RIFT_WALL / 2, 0.0, 78), (plan.RIFT_OUT - plan.RIFT_WALL / 2, 180.0, 90)):
        for a in np.linspace(0, TAU, count, endpoint=False):
            x, y = hx + np.cos(a) * radius, hy + np.sin(a) * radius
            if facing and abs(((np.degrees(a) - plan.EXIT_BEARING + 180) % 360) - 180) < 4.0:
                continue
            edge = radius - 5.0 if not facing else radius + 5.0
            top = float(sample(H, hx + np.cos(a) * edge, hy + np.sin(a) * edge))
            out.append(_row(x, y, top - plan.RIFT_DEPTH, np.degrees(a) + facing, 0, 0, plan.RIFT_DEPTH + 1.0))
    rows['Cliff:rift'] = out
    # the mesa
    out = []
    for a in np.linspace(0, TAU, 22, endpoint=False):
        radius = plan.RELAY_RADIUS + 4.5
        x, y = plan.RELAY[0] + np.cos(a) * radius, plan.RELAY[1] + np.sin(a) * radius
        if np.hypot(x / plan.RIM[0], y / plan.RIM[1]) > CLIFF_FOOT + .01:
            continue
        foot = float(sample(H, plan.RELAY[0] + np.cos(a) * (radius + 6.0), plan.RELAY[1] + np.sin(a) * (radius + 6.0)))
        out.append(_row(x, y, foot, np.degrees(a), 0, 0, plan.RELAY_TOP - foot + 1.0))
    rows['Cliff:mesa'] = out


def layout():
    L = _Layout()
    tx, ty = _trees(L)
    _understory(L, tx, ty)
    _water_plants(L)
    _cliffs(L)
    return dict(sorted(L.rows.items()))


def write_height(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    G = grid()
    meta = {'half_x': HALF_X, 'half_y': HALF_Y, 'cell': CELL, 'nx': NX, 'ny': NY, 'water': plan.WATER,
            'headpond': plan.HEADPOND, 'pool': POOL_LEVEL, 'falls_lip': [round(float(v), 2) for v in falls_line()[0]],
            'regions': {k: list(v) for k, v in plan.REGIONS.items()},
            'paths': [[list(map(float, p)) for p in points] for _n, _k, _h, points in plan.PATHS]}
    (out / 'height.json').write_text(json.dumps(meta, indent=1))
    (out / 'height.bin').write_bytes(np.ascontiguousarray(G['H'], dtype='<f4').tobytes())
    return meta


def write_scatter(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = layout()
    (out / 'scatter.json').write_text(json.dumps(rows, separators=(',', ':')))
    return rows


# ---------------------------------------------------------------- report

def triangle_slopes(H):
    a, b, c, d = H[:-1, :-1], H[1:, :-1], H[1:, 1:], H[:-1, 1:]
    worst = np.zeros(a.shape)
    for dzx, dzy in (((b - a), (c - b)), ((c - d), (d - a)), ((b - a), (d - a)), ((c - d), (c - b))):
        worst = np.maximum(worst, np.hypot(dzx, dzy) / CELL)
    return worst


def report(rows=None, out=print):
    """The figures the land is judged by: heights at the landmarks, path grades, the gorges' widths and depths, the
    lake, the cliff band, and the scatter counts."""
    G = grid()
    H = G['H'].astype(np.float64)
    stats = {'height_min_max': (round(float(H.min()), 1), round(float(H.max()), 1))}
    marks = {}
    for name in ('HOLLOW', 'HOLLOW_STILL', 'OVERPASS', 'OLD_TOWN', 'CAMP', 'GRAFT', 'GULLY_SOUTH', 'GULLY_NORTH', 'UNDERSTORY', 'QUAY',
                 'CANOPY_FOOT', 'RELAY', 'MAST', 'WEST_CROSSING', 'EAST_CROSSING', 'SOUTH_CROSSING', 'RIFT_EXIT', 'FORECOURT', 'GATE',
                 'ROOT_COURT', 'HEARTWOOD', 'ARENA', 'FALLS_POOL'):
        x, y = getattr(plan, name)[:2]
        marks[name] = round(float(sample(H, x, y)), 2)
    stats['heights'] = marks
    stats['giants'] = [round(float(sample(H, x, y)), 2) for x, y, _ in plan.GIANTS]
    grades = {}
    for name, _kind, _half, points in plan.PATHS:
        pts, arc = densify(points, 2.0)
        z = sample(H, pts[:, 0], pts[:, 1])
        grades[name] = (round(float(np.degrees(np.arctan(np.abs(np.diff(z) / np.diff(arc)).max()))), 1), round(float(arc[-1])), round(float(z.min()), 1), round(float(z.max()), 1))
    stats['path_max_grade_deg_length_zmin_zmax'] = grades
    # the Gully at the crossing and the Rift on four bearings: rim to rim width and depth
    y = plan.GULLY_CROSS_Y
    xs = np.arange(plan.gully_x(y) - 20, plan.gully_x(y) + 20, .25)
    z = sample(H, xs, np.full(len(xs), y))
    low = xs[z < z.max() - plan.GULLY_DEPTH / 2]
    stats['gully_width_depth_at_crossing'] = (round(float(low[-1] - low[0]), 1), round(float(z.max() - z.min()), 1))
    rift = {}
    for bearing in (plan.WEST_BEARING, plan.EAST_BEARING, plan.SOUTH_BEARING, 0.0):
        r = np.arange(plan.RIFT_IN - 10, plan.RIFT_OUT + 10, .25)
        a = np.radians(bearing)
        z = sample(H, plan.HEARTWOOD[0] + np.cos(a) * r, plan.HEARTWOOD[1] + np.sin(a) * r)
        low = r[z < max(z[0], z[-1]) - plan.RIFT_DEPTH / 2]
        rift[int(bearing)] = (round(float(low[-1] - low[0]), 1), round(float(max(z[0], z[-1]) - z.min()), 1), round(float(z[0]), 1), round(float(z[-1]), 1))
    stats['rift_width_depth_inner_outer_rim'] = rift
    stats['lake_bed_min'] = round(float(H[G['lake'] < 1].min()), 2)
    tri = np.degrees(np.arctan(triangle_slopes(H)))
    slope = np.zeros(H.shape)
    slope[:-1, :-1] = tri
    band = (G['rim'] > CLIFF_FOOT + .008) & (G['rim'] < CLIFF_TOP - .008)
    stats['cliff_band_slope_deg_p05_median'] = (round(float(np.percentile(slope[band], 5)), 1), round(float(np.median(slope[band])), 1))
    lip, _ = falls_line()
    stats['falls_lip'] = tuple(round(float(v), 1) for v in lip)
    walls = (G['gully'] > .02) & (G['gully'] < .98) | (G['ring'] > .02) & (G['ring'] < .98)
    walk = (G['rim'] < CLIFF_FOOT - .01) & ~walls & (G['lake'] > 1.0) & (G['mesa'] > plan.RELAY_RADIUS + 12) & (G['river_d'] > 20)
    stats['share_of_valley_too_steep_to_walk'] = round(float((slope[walk] > 45).mean()), 4)
    if rows is not None:
        stats['scatter'] = {k: len(v) for k, v in rows.items()}
        stats['scatter_total'] = sum(len(v) for v in rows.values())
    for k, v in stats.items():
        out('  %-40s %s' % (k, v))
    return stats


MESHES = [terrain_tile, lake, headpond, river, falls, backdrop]
VARIANTS = {terrain_tile: plan.TILES_X * plan.TILES_Y}
_TILE = {'size': (2 * HALF_X / plan.TILES_X, 2 * HALF_Y / plan.TILES_Y, 0), 'tol': .01, 'pivot': 'any'}
CONTRACT = {'SM_GT_Terrain_%d_%d' % (i, j): _TILE for i in range(plan.TILES_X) for j in range(plan.TILES_Y)}
CONTRACT.update({'SM_GT_Lake': {'pivot': 'any'}, 'SM_GT_Headpond': {'pivot': 'any'}, 'SM_GT_River': {'pivot': 'any'},
                 'SM_GT_Falls': {'pivot': 'any'}, 'SM_GT_Backdrop': {'pivot': 'any'}})

def picture(path, rows=None, size=None):
    """A plan view of the land for checking it by eye: the layers' plain colours, hill-shaded, water in blue, and (with
    rows) a dot for every tree. North is up, east right; one pixel per grid cell."""
    G = grid()
    H = G['H'].astype(np.float64)
    gx, gy = np.gradient(H, CELL)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    light = np.array([.45, -.5, .74])
    shade = np.clip(n @ (light / np.linalg.norm(light)), 0, 1)
    c = albedo() * (.35 + 1.5 * shade[..., None]) * 2.2
    wet = (H < plan.WATER) | (G['pond'] > .5) & (H < plan.HEADPOND)
    c[wet] = np.array([.05, .16, .22]) * (.6 + .4 * shade[wet][:, None]) * 2
    if rows:
        tint = {'SM_GV_Oak': (.03, .12, .02), 'SM_GV_Beech': (.07, .16, .03), 'SM_GV_Pine': (.01, .06, .03), 'SM_GV_Birch': (.35, .28, .04),
                'SM_GV_Snag': (.25, .22, .2), 'SM_GV_Thorn': (.5, .05, .3)}
        for name, colour in tint.items():
            for row in rows.get(name, ()):
                i, j = int(round((row[0] / 100 + HALF_X) / CELL)), int(round((row[1] / 100 + HALF_Y) / CELL))
                if 1 <= i < NX - 1 and 1 <= j < NY - 1:
                    c[i - 1:i + 2, j - 1:j + 2] = colour
    srgb = np.where(c <= .0031308, c * 12.92, 1.055 * np.clip(c, 0, 1) ** (1 / 2.4) - .055)
    image = (np.clip(srgb, 0, 1) * 255).astype(np.uint8)[::-1]        # row 0 is the north edge; columns run east
    png(path, np.ascontiguousarray(image))


if __name__ == '__main__':
    import sys
    import time
    start = time.time()
    rows = layout()
    report(rows)
    if '--png' in sys.argv:
        out = ROOT / 'Saved/Grove/land.png'
        picture(out, rows)
        print('picture', out)
    print('%.1f s' % (time.time() - start))
