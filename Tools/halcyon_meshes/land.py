"""The land of Port Halcyon (level 6, Earth): the height grid, the terrain tiles, the sea and the scatter.

The town climbs south from the sea on one long slope (plan.slope_z): 40 m at the Cliff Garden, about 3 m at the quays.
The Breach cuts the slope from wall to wall, its bottom flooded to sea level; the Drowned Quarter is a hollow of the
west waterfront below the sea; north of the waterfront the bed falls to plan.SEA_BED, with the headland of Lighthouse
Point in the north-east, the Mole running north to the Bastion's rock, and the bay's arms beyond the walkable oval
climbing into cliffs (open to the sea in the harbour mouth). Streets and pads are levelled.

Terrain vertices carry the ground's albedo (linear RGB): turf and earth on the slope, setts on the roads, grey rock
where it is steep, shingle and wrack along the waterline, a magenta stain where the forced sea has lain. The
material lays a scanned surface over it (physis_halcyon_tools: MI_HA_Ground).

Scatter rows are [x, y, z (cm), pitch, yaw, roll, sx, sy, sz], keyed by mesh name, ready for the level build's
instanced actors. Houses line the streets (the town), rubble, lamps and bollards the roads, wrecks the shallows.
"""
import functools
import json
import math
from pathlib import Path

from kit import *  # noqa: F401,F403
import physis_halcyon_plan as plan

HALF_X, HALF_Y, CELL = plan.HALF_X, plan.HALF_Y, plan.CELL
NX, NY = int(round(2 * HALF_X / CELL)) + 1, int(round(2 * HALF_Y / CELL)) + 1
TILE_X, TILE_Y = (NX - 1) // plan.TILES_X, (NY - 1) // plan.TILES_Y
SEED = 6106


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def sample(grid, x, y):
    """Bilinear sample of a (NX, NY) field at metres (arrays allowed)."""
    fx, fy = (np.asarray(x, np.float64) + HALF_X) / CELL, (np.asarray(y, np.float64) + HALF_Y) / CELL
    i, j = np.clip(np.floor(fx).astype(int), 0, NX - 2), np.clip(np.floor(fy).astype(int), 0, NY - 2)
    u, v = np.clip(fx - i, 0, 1), np.clip(fy - j, 0, 1)
    return grid[i, j] * (1 - u) * (1 - v) + grid[i + 1, j] * u * (1 - v) + grid[i, j + 1] * (1 - u) * v + grid[i + 1, j + 1] * u * v


def nz(x, y, seed, octaves, scale):
    f = fbm(x, y, seed, octaves, scale)
    return np.clip((f - f.mean()) / (2.5 * f.std() + 1e-9), -1.0, 1.0)


def _segment_distance(X, Y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((X - ax) * dx + (Y - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0.0, 1.0)
    return np.hypot(X - (ax + t * dx), Y - (ay + t * dy))


def _shape():
    xs, ys = np.linspace(-HALF_X, HALF_X, NX), np.linspace(-HALF_Y, HALF_Y, NY)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    t = np.clip((X - plan.TOP_X) / (plan.SHORE_X - plan.TOP_X), 0.0, 1.0)
    town = plan.TOP_Z + (plan.SHORE_Z - plan.TOP_Z) * (t * (1.4 - .4 * t))
    town = np.where(X < plan.TOP_X, plan.TOP_Z + (plan.TOP_X - X) * .05, town)
    # The waterfront: past the shore line the quay wall drops to the sea bed.
    shore = plan.SHORE_X + plan.SHORE_WAVE * np.sin(Y / plan.SHORE_PERIOD + .8)
    sea = sstep(-1.0, 3.0, X - shore)
    bed = plan.SEA_BED - 3.0 * sstep(0, 250.0, X - shore) + 1.2 * nz(X, Y, SEED + 5, 3, 1 / 60.0)
    base = town * (1 - sea) + bed * sea
    # Streets and pads: how far each point is from the nearest, and how wide that one is.
    path_d, path_half, road = np.full(X.shape, np.inf), np.zeros(X.shape), np.zeros(X.shape, bool)
    for ax, ay, bx, by, half, kind in plan.path_segments():
        d = _segment_distance(X, Y, ax, ay, bx, by)
        nearer = d - half < path_d - path_half
        path_d, path_half = np.where(nearer, d, path_d), np.where(nearer, half, path_half)
        road = np.where(nearer, kind != 'path', road)
    pad = np.zeros(X.shape)
    for px, py, radius, _ in plan.PADS:
        pad = np.maximum(pad, 1 - sstep(radius, radius + 8.0, np.hypot(X - px, Y - py)))
    level = np.maximum(1 - sstep(path_half, path_half + 6.0, path_d), pad)
    rough = 1.2 * nz(X, Y, SEED, 4, 1 / 140.0) + .35 * nz(X, Y, SEED + 7, 4, 1 / 24.0)
    H = base + rough * (1 - level) * (1 - sea)
    # The Drowned Quarter: a hollow of the waterfront under the sea, its streets 1 to 2 m down.
    cx, cy, ax, ay = plan.QUARTER
    m = np.hypot((X - cx) / ax, (Y - cy) / ay)
    hollow = 1 - sstep(.92, 1.12, m)
    H = H * (1 - hollow) + (-1.6 - .9 * sstep(.2, 1.0, 1 - m) + .3 * nz(X, Y, SEED + 9, 3, 1 / 30.0)) * hollow
    # Lighthouse Point: a headland with a flat top, its foot in the sea.
    px, py, pr, ph = plan.POINT
    d = np.hypot(X - px, Y - py)
    head = 1 - sstep(pr, pr + 22.0, d)
    H = np.maximum(H, H * (1 - head) + ph * head + 1.5 * nz(X, Y, SEED + 13, 3, 1 / 20.0) * head * sstep(pr - 4, pr + 10, d))
    # The spit: the Point Path's last stretch runs out along a shingle bank that rises to the headland.
    spit_d = np.full(X.shape, np.inf)
    points = next(pts for name, _, _, pts in plan.PATHS if name == 'Point Path')
    for (ax_, ay_), (bx_, by_) in zip(points, points[1:]):
        spit_d = np.minimum(spit_d, _segment_distance(X, Y, ax_, ay_, bx_, by_))
    spit = (1 - sstep(6.0, 16.0, spit_d)) * sstep(-20.0, 10.0, X - shore)
    spit_h = 2.8 + (ph - 2.8) * (1 - sstep(pr, pr + 70.0, d)) ** 1.5
    H = np.maximum(H, H * (1 - spit) + spit_h * spit)
    sea = sea * (1 - spit) * (1 - head)
    # The Bastion's rock and the Mole (the Mole's own mesh is its walking surface; the ground under it is a low bank).
    rock = 1 - sstep(plan.ROCK_RADIUS - 4.0, plan.ROCK_RADIUS + 6.0, np.hypot(X - plan.BASTION[0], Y - plan.BASTION[1]))
    H = H * (1 - rock) + plan.ROCK_TOP * rock
    mole = (1 - sstep(4.0, 9.0, np.abs(Y))) * sstep(plan.MOLE_SOUTH[0] - 8, plan.MOLE_SOUTH[0], X) * (1 - sstep(plan.SEA_GATE[0], plan.SEA_GATE[0] + 8, X))
    H = np.maximum(H, H * (1 - mole) + (plan.MOLE_TOP - 1.2) * mole)
    # The Breach: a cut 26 m across from wall to wall, flooded to sea level.
    breach_x = plan.BREACH_X + plan.BREACH_WAVE * np.sin(Y / plan.BREACH_PERIOD + .6)
    breach_d = np.abs(X - breach_x)
    cut = 1 - sstep(plan.BREACH_FLOOR, plan.BREACH_RIM, breach_d)
    H = H * (1 - cut) + (plan.BREACH_BED + .8 * nz(X, Y, SEED + 3, 3, 1 / 18.0)) * cut
    # The slipway: whoever falls into the Breach walks out up a ramp cut into its south wall (it leads only south).
    along = (breach_x - plan.BREACH_FLOOR) - X
    band = 1 - sstep(3.5, 5.5, np.abs(Y - plan.BREACH_STEPS_Y))
    ramp = plan.BREACH_BED + 6.6 + np.clip(along, 0, None) * math.tan(math.radians(17.0))
    slip = band * (along > -1.0) * (along < 80.0)
    H = np.where(slip > 0, np.minimum(H, H * (1 - band) + ramp * band), H)
    # The bay's arms: beyond the walkable oval the land climbs into cliffs, except in the harbour mouth (north, |y| <
    # 150), which stays open sea out to the horizon.
    rim = np.hypot(X / plan.RIM[0], Y / plan.RIM[1])
    mouth = sstep(250.0, 420.0, X) * (1 - sstep(130.0, 190.0, np.abs(Y)))
    climb = sstep(plan.RIM_START, plan.RIM_END, rim) * (1 - mouth)
    ridges = 1 - np.abs(nz(X, Y, SEED + 11, 5, 1 / 80.0))
    H = H + plan.RIM_RISE * climb ** 1.4 * (.7 + .5 * ridges) + 20.0 * sstep(1.05, 1.6, rim) * (1 - mouth)
    gx, gy = np.gradient(H, CELL)
    scar = np.zeros(X.shape)
    for sx, sy, radius in plan.SCAR:
        scar = np.maximum(scar, np.clip(1 - np.hypot(X - sx, Y - sy) / radius, 0, 1))
    return {'X': X, 'Y': Y, 'H': H.astype(np.float32), 'slope': np.hypot(gx, gy), 'path_d': path_d, 'path_half': path_half, 'road': road, 'pad': pad,
            'breach_d': breach_d, 'quarter': m, 'rim': rim, 'scar': scar, 'sea': sea, 'head': head, 'mouth': mouth}


@functools.lru_cache(maxsize=1)
def grid():
    return _shape()


def height_at(x, y):
    return sample(grid()['H'].astype(np.float64), x, y)


def albedo():
    """(NX, NY, 3) linear colours of the ground."""
    G = grid()
    X, Y, H = G['X'], G['Y'], G['H'].astype(np.float64)
    tone_ = 1.0 + .14 * nz(X, Y, SEED + 21, 4, 1 / 40.0)
    turf = np.array((.070, .085, .040)) * tone_[..., None]
    earth = np.array((.160, .140, .110))
    worn = sstep(.2, .8, nz(X, Y, SEED + 23, 3, 1 / 22.0) * .5 + .5)[..., None]
    c = turf * (1 - worn * .6) + earth * worn * .6
    paved = (1 - sstep(G['path_half'] - .5, G['path_half'] + 1.5, G['path_d'])) * np.where(G['road'], 1.0, .55)
    c = c * (1 - paved[..., None]) + np.array(LIME_WORN[:3]) * .75 * paved[..., None]
    rock = sstep(.6, 1.1, G['slope'])[..., None]
    c = c * (1 - rock) + np.array(ROCK_GREY[:3]) * 1.3 * rock
    # The waterline: shingle and wrack from 1.5 m above the sea down, dark wet ground below it.
    tide = (1 - sstep(.0, 2.5, H))[..., None]
    c = c * (1 - tide) + np.array(SAND_W[:3]) * .8 * tide
    wet = (1 - sstep(-1.0, .6, H))[..., None]
    c = c * (1 - wet) + np.array((.07, .07, .055)) * wet
    scar = (G['scar'] * (.75 + .25 * nz(X, Y, SEED + 31, 3, 1 / 16.0)))[..., None] * .45
    c = c * (1 - scar) + np.array((.22, .08, .18)) * scar
    deep = sstep(0.0, plan.BREACH_RIM, plan.BREACH_RIM - G['breach_d'])[..., None] * .5
    c = c * (1 - deep) + np.array(ROCK_GREY[:3]) * .7 * deep
    return np.clip(c, 0.0, .9)


@functools.lru_cache(maxsize=1)
def vertex_normals():
    gx, gy = np.gradient(grid()['H'].astype(np.float64), CELL)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def _grid_faces(mx, my):
    idx = np.arange(mx * my).reshape(mx, my)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    return np.stack([a, b, c, d], 1).tolist()      # counter-clockwise seen from above


@functools.lru_cache(maxsize=1)
def _albedo():
    return albedo()


def layers():
    """The ground's layer weights for the Grove's ground shader (M_GRGround, which Earth shares): colour R meadow
    grass, G trodden earth, B gravel and shingle, A 1 - blight; uv u asphalt (the setts of the roads read as old
    asphalt), v moss and damp. What is left is forest floor; rock comes from the slope, in the shader."""
    G = grid()
    X, Y, H = G['X'], G['Y'], G['H'].astype(np.float64)
    half = np.where(np.isfinite(G['path_d']), G['path_half'], 1.0)
    on_path = 1 - sstep(half * .75, half + 1.6, G['path_d'])
    cracks = .5 + .5 * noise2(X / 3.1, Y / 3.1, SEED + 41)
    asphalt = on_path * G['road'] * sstep(.18, .5, cracks + .25 * (1 - sstep(half * .4, half, G['path_d'])))
    dirt = on_path * (~G['road']) + .5 * on_path * G['road'] * (1 - asphalt)
    worn = sstep(.55, .8, .5 + .5 * nz(X, Y, SEED + 23, 3, 1 / 26.0))
    dirt = np.clip(np.maximum(dirt, .7 * G['pad'] + .4 * worn), 0, 1)
    gravel = np.maximum(1 - sstep(.5, 3.0, H), G['sea'])
    gravel = np.maximum(gravel, 1 - sstep(plan.BREACH_FLOOR, plan.BREACH_RIM + 1.0, G['breach_d']))
    gravel = np.clip(gravel, 0, 1)
    meadow = sstep(.25, .6, .5 + .5 * nz(X, Y, SEED + 211, 3, 1 / 120.0))
    grass = np.clip((.55 + .45 * meadow) * (1 - gravel) * (1 - np.clip(dirt + asphalt, 0, 1)), 0, 1)
    wet = 1 - sstep(1.0, 6.0, H)
    moss = np.clip(.7 * wet + .3 * sstep(.3, .8, G['slope']), 0, 1) * (1 - np.clip(dirt + asphalt, 0, 1))
    blight = np.clip(G['scar'] * .6 * (.6 + .4 * nz(X, Y, SEED + 31, 3, 1 / 16.0)), 0, 1)
    return {'grass': grass, 'dirt': dirt, 'gravel': gravel, 'asphalt': np.clip(asphalt, 0, 1), 'moss': moss, 'blight': blight}


@functools.lru_cache(maxsize=1)
def _layers():
    return layers()


def terrain_tile(k):
    """SM_HT_Terrain_<i>_<j> (k = i * TILES_Y + j): one 320 m tile in world metres; neighbours share their edge rows.
    Colour and uv carry the layer weights (layers()); `normals` are the whole grid's, so seams shade as one."""
    i, j = divmod(k, plan.TILES_Y)
    G, L = grid(), _layers()
    xs, ys = slice(i * TILE_X, (i + 1) * TILE_X + 1), slice(j * TILE_Y, (j + 1) * TILE_Y + 1)
    px, py, ph = G['X'][xs, ys], G['Y'][xs, ys], G['H'][xs, ys].astype(np.float64)
    weights = np.stack([L['grass'][xs, ys], L['dirt'][xs, ys], L['gravel'][xs, ys], 1 - L['blight'][xs, ys]], -1).reshape(-1, 4)
    uv = np.stack([L['asphalt'][xs, ys], L['moss'][xs, ys]], -1).reshape(-1, 2)
    p = Part('SM_HT_Terrain_%d_%d' % (i, j), (GROUND,))
    p.add(np.stack([px.ravel(), py.ravel(), ph.ravel()], 1), _grid_faces(*px.shape), weights, 0, True, uv=uv)
    p.normals = vertex_normals()[xs, ys].reshape(-1, 3)
    return p


def sea():
    """SM_HT_Sea: the sea at z 0, a sheet from the town's waterline out to the horizon (6 km), finer near the land;
    the terrain hides it wherever the ground stands above the water."""
    p = Part('SM_HT_Sea', (WATER,))
    xs = np.concatenate([np.arange(-HALF_X, HALF_X + .1, 8.0), np.arange(HALF_X + 50.0, 6000.0, 250.0)])
    ys = np.concatenate([np.arange(-4000.0, -HALF_Y, 250.0), np.arange(-HALF_Y, HALF_Y + .1, 8.0), np.arange(HALF_Y + 250.0, 4000.1, 250.0)])
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    p.add(np.stack([gx.ravel(), gy.ravel(), np.full(gx.size, plan.WATER)], 1), _grid_faces(*gx.shape), col(.10, .14, .13), 0, True)
    return p


# ---------------------------------------------------------------- scatter

def _row(x, y, z, yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
    s = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    return [round(float(x) * 100, 1), round(float(y) * 100, 1), round(float(z) * 100, 1), round(float(pitch), 2), round(float(yaw), 2),
            round(float(roll), 2), round(float(s[0]), 3), round(float(s[1]), 3), round(float(s[2]), 3)]


def _clear(G):
    X, Y = G['X'], G['Y']
    keep = np.zeros(X.shape, bool)
    for x, y, radius in plan.KEEP_CLEAR:
        keep |= np.hypot(X - x, Y - y) < radius
    return keep


# The town's houses (mesh, half depth along x, half width along y): they stand with their fronts (+x) to the street.
HOUSES = (('SM_HN_House0', 4.0, 3.5), ('SM_HN_House1', 3.2, 3.0), ('SM_HN_House2', 4.0, 3.5), ('SM_HN_House3', 4.5, 4.0))


def layout():
    G = grid()
    H = G['H'].astype(np.float64)
    rng = np.random.default_rng(SEED)
    keep = _clear(G)
    walk = (G['rim'] < .9) | ((G['mouth'] > .5) & (G['rim'] < 1.4))
    dry = H > .4
    busy = keep | (G['path_d'] < G['path_half'] + 2.5) | (G['breach_d'] < plan.BREACH_RIM + 3.0) | (G['quarter'] < 1.05) | (G['sea'] > .02) | \
        (G['head'] > .5)
    rows = {}
    taken = []      # (x, y, radius): houses and big props, so nothing lands inside another

    def pick(mask, x, y):
        return sample(mask.astype(np.float64), x, y) > .5

    def free(x, y, r):
        return all(math.hypot(x - tx, y - ty) > r + tr for tx, ty, tr in taken)

    def blocked(x, y, pad):
        return bool(keep[int(round((x + HALF_X) / CELL)) % NX, int(round((y + HALF_Y) / CELL)) % NY]) or plan.in_breach(x, y, pad) or \
            plan.in_sea(x, y, 2.0) or plan.rim(x, y) > .9

    def candidates(cell, x0=-HALF_X + 8, x1=HALF_X - 8, y0=-HALF_Y + 8, y1=HALF_Y - 8):
        xs, ys = np.arange(x0, x1, cell), np.arange(y0, y1, cell)
        gx, gy = np.meshgrid(xs, ys, indexing='ij')
        return (gx + rng.uniform(.1, .9, gx.shape) * cell).ravel(), (gy + rng.uniform(.1, .9, gy.shape) * cell).ravel()

    def put(name, x, y, scale, sink=0.0, yaw=None, lift=0.0, tilt=0.0, z=None):
        zz = sample(H, x, y) - sink + lift if z is None else z
        out = rows.setdefault(name, [])
        for k in range(len(x)):
            out.append(_row(x[k], y[k], zz[k] if np.ndim(zz) else zz, rng.uniform(0, 360) if yaw is None else yaw[k], rng.uniform(-tilt, tilt),
                            rng.uniform(-tilt, tilt), scale[k] if np.ndim(scale) else scale))

    # The town: terraces of houses along both sides of every road and lane, fronts to the street, gaps for alleys.
    for name, kind, half, points in plan.PATHS:
        if kind == 'path':
            continue
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            length = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / length, (by - ay) / length
            for side in (-1, 1):
                d = 4.0
                while d < length - 4.0:
                    mesh, hx, hy = HOUSES[rng.integers(0, len(HOUSES))]
                    d += hy
                    off = half + 2.0 + hx
                    x_, y_ = ax + ux * d - uy * side * off, ay + uy * d + ux * side * off
                    face = math.degrees(math.atan2(-ux * side, uy * side))   # the front (+x of the mesh) looks back at the street
                    if not blocked(x_, y_, hx + 2.0) and free(x_, y_, max(hx, hy)) and rng.uniform() < .86:
                        ground = min(float(sample(H, x_ - hx * .7, y_)), float(sample(H, x_ + hx * .7, y_)), float(sample(H, x_, y_ - hy * .7)),
                                     float(sample(H, x_, y_ + hy * .7)))
                        rows.setdefault(mesh, []).append(_row(x_, y_, ground - .4, face))
                        taken.append((x_, y_, max(hx, hy) * .95))
                    d += hy + (rng.uniform(3.0, 6.0) if rng.uniform() < .2 else .4)
    # Lamps and bollards along the roads.
    for name, kind, half, points in plan.PATHS:
        if kind != 'road':
            continue
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            length = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / length, (by - ay) / length
            for k in range(int(length // 18.0)):
                side = 1 if k % 2 else -1
                d = 9.0 + k * 18.0
                x_, y_ = ax + ux * d - uy * side * (half + .8), ay + uy * d + ux * side * (half + .8)
                if not blocked(x_, y_, 3.0) and free(x_, y_, .5):
                    put('SM_HN_Lamp', np.array([x_]), np.array([y_]), 1.0, sink=.05, yaw=np.array([math.degrees(math.atan2(uy, ux))]))
    # Trees and bushes in the gardens behind the houses, and grass over the open ground.
    x, y = candidates(9.0)
    ok = pick(walk & ~busy & dry, x, y) & (rng.uniform(0, 1, len(x)) < .32) & (sample(G['slope'], x, y) < .45)
    ok &= np.array([free(a, b, 1.5) for a, b in zip(x, y)], bool)
    x, y = x[ok], y[ok]
    kind = rng.choice(4, len(x), p=(.36, .22, .3, .12))
    for k, (mesh, lo, hi) in enumerate((('SM_GV_Bush', .7, 1.4), ('SM_GV_Birch', .6, .9), ('SM_GV_Sapling', .8, 1.3), ('SM_GV_Snag', .6, 1.0))):
        sel = kind == k
        put(mesh, x[sel], y[sel], rng.uniform(lo, hi, sel.sum()), sink=.2, tilt=3.0)
    x, y = candidates(3.0)
    ok = pick(walk & ~busy & dry, x, y) & (rng.uniform(0, 1, len(x)) < .45 * (.7 + .6 * nz(x, y, SEED + 41, 3, 1 / 45.0))) & (sample(G['slope'], x, y) < .5)
    put('SM_GV_Grass', x[ok], y[ok], rng.uniform(.6, 1.2, ok.sum()), sink=.02)
    # Rubble (the scanned stones) where houses fell, thickest near the Breach and on the waterfront.
    x, y = candidates(10.0)
    near = np.clip(1 - np.abs(x - plan.BREACH_X) / 80.0, 0, 1) + np.clip(1 - np.abs(x - plan.SHORE_X) / 60.0, 0, 1)
    ok = pick(walk & ~busy, x, y) & (rng.uniform(0, 1, len(x)) < .12 + .35 * near)
    ok &= np.array([free(a, b, 1.0) for a, b in zip(x, y)], bool)
    x, y = x[ok], y[ok]
    big = rng.uniform(0, 1, len(x)) < .25
    put('SM_GS_Boulder', x[big], y[big], rng.uniform(.5, 1.4, big.sum()), sink=.3, tilt=12.0)
    put('SM_GS_Stone', x[~big], y[~big], rng.uniform(1.0, 2.6, (~big).sum()), sink=.1, tilt=16.0)
    # The shallows of the Drowned Quarter: roofs and walls of the houses that stand in the water, and wrecks.
    cx, cy, ax, ay = plan.QUARTER
    for k in range(70):
        a, r = rng.uniform(0, math.tau), math.sqrt(rng.uniform(.04, .85))
        x_, y_ = cx + math.cos(a) * ax * r, cy + math.sin(a) * ay * r
        if math.hypot(x_ - plan.HARBOURMASTER[0], y_ - plan.HARBOURMASTER[1]) < 22 or not free(x_, y_, 4.5):
            continue
        mesh, hx, hy = HOUSES[rng.integers(0, len(HOUSES))]
        rows.setdefault(mesh, []).append(_row(x_, y_, float(height_at(x_, y_)) - .6, rng.choice((0.0, 90.0, 180.0, 270.0)) + rng.uniform(-8, 8)))
        taken.append((x_, y_, max(hx, hy)))
    for k in range(14):
        x_, y_ = rng.uniform(plan.SHORE_X + 20, 380.0), rng.uniform(-360.0, 360.0)
        if abs(y_) < 30 or math.hypot(x_ - plan.POINT[0], y_ - plan.POINT[1]) < 70 or not free(x_, y_, 6.0):
            continue
        rows.setdefault('SM_HN_Boat', []).append(_row(x_, y_, -.9, rng.uniform(0, 360), rng.uniform(-12, 12), rng.uniform(-25, 25)))
        taken.append((x_, y_, 6.0))
    # The sea wall along the waterfront: quay panels 12 m wide following the shore line, west and east of the Mole.
    for side in (-1.0, 1.0):
        y_ = side * 12.0
        while abs(y_) < HALF_Y - 30:
            x_ = plan.shore_x(y_) - .6
            hollow = math.hypot((x_ - cx) / (ax + 10), (y_ - cy) / (ay + 10)) < 1.0
            if plan.rim(x_, y_) < .97 and not hollow and math.hypot(x_ - plan.POINT[0], y_ - plan.POINT[1]) > plan.POINT[2] + 18:
                lean = math.degrees(math.atan2(plan.shore_x(y_ + 3.0) - plan.shore_x(y_ - 3.0), 6.0))
                rows.setdefault('SM_HN_Quay', []).append(_row(x_, y_, plan.SEA_BED + 2.0, -lean, scale=(1.0, 1.0, 1.0)))
            y_ += side * 11.9
    return dict(sorted(rows.items()))


def write_height(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    meta = {'half_x': HALF_X, 'half_y': HALF_Y, 'cell': CELL, 'nx': NX, 'ny': NY, 'water': plan.WATER,
            'regions': {k: list(v) for k, v in plan.REGIONS.items()}}
    (out / 'height.json').write_text(json.dumps(meta, indent=1))
    (out / 'height.bin').write_bytes(np.ascontiguousarray(grid()['H'], dtype='<f4').tobytes())
    return meta


def write_scatter(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = layout()
    (out / 'scatter.json').write_text(json.dumps(rows, separators=(',', ':')))
    return rows


def report(rows=None, out=print):
    G = grid()
    H = G['H'].astype(np.float64)
    out('land %d x %d, heights %.1f to %.1f m' % (NX, NY, H.min(), H.max()))
    for name in ('GARDEN', 'SIGNAL', 'CLOCK', 'BRIDGE_SOUTH', 'BRIDGE_NORTH', 'STEPS', 'QUARTER_STILL', 'HARBOURMASTER', 'YARDS_STILL', 'YARDS',
                 'FOREMAN', 'POINT_STILL', 'LIGHTHOUSE', 'MOLE_SOUTH', 'SEA_GATE', 'BASTION', 'LIBRARY'):
        x, y = getattr(plan, name)[:2]
        out('  %-14s (%7.1f, %7.1f) z %6.1f' % (name, x, y, float(height_at(x, y))))
    if rows is not None:
        out('scatter: ' + ', '.join('%s %d' % (k, len(v)) for k, v in rows.items()))


MESHES = [terrain_tile, sea]
VARIANTS = {terrain_tile: plan.TILES_X * plan.TILES_Y}
_TILE = {'size': (2 * HALF_X / plan.TILES_X, 2 * HALF_Y / plan.TILES_Y, 0), 'tol': .01, 'pivot': 'any'}
CONTRACT = {'SM_HT_Terrain_%d_%d' % (i, j): _TILE for i in range(plan.TILES_X) for j in range(plan.TILES_Y)}
CONTRACT['SM_HT_Sea'] = {'pivot': 'any'}
