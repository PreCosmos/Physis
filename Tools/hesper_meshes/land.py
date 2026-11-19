"""The land of Hesper (level 7, Arche): the height grid, the terrain tiles, the Reed Terraces' pools and the scatter.

The plateau rises gently north (plan.rise_z): about 20 m at the Sunward Stair, 44 m at the Concord's dais. Its west
side is an edge: beyond plan.edge_y the ground falls plan.DROP metres into haze, so the low sun comes in over it; the
other sides climb into cliffs beyond the walkable oval. The Reed Terraces step down toward the edge in four pools; the
Watch Spire stands on a rock terrace in the north-east with a ramp up its south-west side. Roads and pads are
levelled. The Choir Wall is not in the ground: it is Unison, placed by the scenario.

Terrain vertices carry the ground's albedo (linear RGB): warm dust on the flats, flagstone on the roads, red-brown
rock where it is steep, an amber burn where the Concord's tone is strongest. The material lays a scanned rock over it
(physis_hesper_tools: MI_HS_Ground), so the colour is the tint and the scan the detail.

Scatter rows are [x, y, z (cm), pitch, yaw, roll, sx, sy, sz], keyed by mesh name, ready for the level build's
instanced actors.
"""
import functools
import json
import math
from pathlib import Path

from kit import *  # noqa: F401,F403
import physis_hesper_plan as plan

HALF_X, HALF_Y, CELL = plan.HALF_X, plan.HALF_Y, plan.CELL
NX, NY = int(round(2 * HALF_X / CELL)) + 1, int(round(2 * HALF_Y / CELL)) + 1
TILE_X, TILE_Y = (NX - 1) // plan.TILES_X, (NY - 1) // plan.TILES_Y
SEED = 7107


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


def _pool_local(X, Y, pool):
    px, py, hx, hy, _, yaw = pool
    a = math.radians(yaw)
    lx = (X - px) * math.cos(a) + (Y - py) * math.sin(a)
    ly = -(X - px) * math.sin(a) + (Y - py) * math.cos(a)
    return np.maximum(np.abs(lx) / hx, np.abs(ly) / hy)      # 1 on the pool's rim


def _shape():
    xs, ys = np.linspace(-HALF_X, HALF_X, NX), np.linspace(-HALF_Y, HALF_Y, NY)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    t = np.clip((X - plan.SOUTH_X) / (plan.NORTH_X - plan.SOUTH_X), 0.0, 1.0)
    base = plan.SOUTH_Z + (plan.NORTH_Z - plan.SOUTH_Z) * (t * t * (3 - 2 * t) * .35 + t * .65)
    # Streets and pads: how far each point is from the nearest, and how wide that one is.
    path_d, path_half, road = np.full(X.shape, np.inf), np.zeros(X.shape), np.zeros(X.shape, bool)
    for ax, ay, bx, by, half, kind in plan.path_segments():
        d = _segment_distance(X, Y, ax, ay, bx, by)
        nearer = d - half < path_d - path_half
        path_d, path_half = np.where(nearer, d, path_d), np.where(nearer, half, path_half)
        road = np.where(nearer, kind != 'trail', road)
    pad = np.zeros(X.shape)
    for px, py, radius, _ in plan.PADS:
        pad = np.maximum(pad, 1 - sstep(radius, radius + 8.0, np.hypot(X - px, Y - py)))
    level = np.maximum(1 - sstep(path_half, path_half + 6.0, path_d), pad)
    swell = 1.6 * nz(X, Y, SEED, 4, 1 / 160.0) + .4 * nz(X, Y, SEED + 7, 4, 1 / 26.0)
    H = base + swell * (1 - level)
    # The Reed Terraces: each pool a sunk basin with a flat floor 1.4 m under its own water, its banks sloped.
    pool_m = np.full(X.shape, 9.0)
    for pool in plan.POOLS:
        m = _pool_local(X, Y, pool)
        surface = plan.rise_z(pool[0]) + pool[4]
        floor = surface - 1.4
        dish = 1 - sstep(.92, 1.18, m)
        H = np.minimum(H, H * (1 - dish) + floor * dish)
        # the ground around a pool steps down with it, so the terraces read as steps toward the edge
        apron = (1 - sstep(1.0, 2.2, m)) * (1 - dish)
        H = H * (1 - apron) + np.minimum(H, surface + .5) * apron
        pool_m = np.minimum(pool_m, m)
    # The Watch Spire's rock: a flat-topped terrace with steep sides, and a ramp up its south-west side.
    sx, sy, sr, sh = plan.SPIRE_ROCK
    d = np.hypot(X - sx, Y - sy)
    top = plan.rise_z(sx) + sh
    rock = 1 - sstep(sr, sr + 7.0, d)
    H = np.maximum(H, H * (1 - rock) + top * rock + .8 * nz(X, Y, SEED + 13, 3, 1 / 12.0) * rock * sstep(sr - 3, sr + 6, d))
    (fx, fy), (tx, ty) = plan.RAMP
    ramp_d = _segment_distance(X, Y, fx - 4.0, fy - 2.0, tx + 4.0, ty + 2.0)
    along = np.clip(((X - fx) * (tx - fx) + (Y - fy) * (ty - fy)) / ((tx - fx) ** 2 + (ty - fy) ** 2), 0.0, 1.0)
    ramp_h = plan.rise_z(fx) + (top - plan.rise_z(fx)) * along
    band = (1 - sstep(3.0, 5.0, ramp_d))
    H = np.where(band > 0, H * (1 - band) + np.maximum(H * 0 + ramp_h, np.minimum(H, ramp_h)) * band, H)
    # The rim: beyond the walkable oval the land climbs into ridged cliffs, except west of the edge, where it falls.
    rim = np.hypot(X / plan.RIM[0], Y / plan.RIM[1])
    edge = plan.EDGE_Y + plan.EDGE_WAVE * np.sin(X / plan.EDGE_PERIOD + .9)
    beyond = edge - Y                       # metres past the western edge
    fall = sstep(0.0, 14.0, beyond)
    west = sstep(-60.0, 0.0, -Y - 200.0) * 0 + (Y < 0)
    ridges = 1 - np.abs(nz(X, Y, SEED + 11, 5, 1 / 80.0))
    climb = sstep(plan.RIM_START, plan.RIM_END, rim) * (1 - fall) * (1 - .9 * sstep(-80.0, -10.0, beyond) * west)
    H = H + plan.RIM_RISE * climb ** 1.4 * (.7 + .5 * ridges) + 20.0 * sstep(1.05, 1.6, rim) * (1 - fall)
    cliff = H - plan.DROP * fall ** .6 * (.85 + .3 * ridges) - 8.0 * sstep(0.0, 3.0, beyond)
    H = np.where(beyond > 0, cliff, H)
    gx, gy = np.gradient(H, CELL)
    scar = np.zeros(X.shape)
    for qx, qy, radius in plan.SCAR:
        scar = np.maximum(scar, np.clip(1 - np.hypot(X - qx, Y - qy) / radius, 0, 1))
    return {'X': X, 'Y': Y, 'H': H.astype(np.float32), 'slope': np.hypot(gx, gy), 'path_d': path_d, 'path_half': path_half, 'road': road,
            'pad': pad, 'rim': rim, 'scar': scar, 'pool': pool_m, 'rock': rock, 'beyond': beyond}


@functools.lru_cache(maxsize=1)
def grid():
    return _shape()


def height_at(x, y):
    return sample(grid()['H'].astype(np.float64), x, y)


def albedo():
    """(NX, NY, 3) linear colours of the ground."""
    G = grid()
    X, Y = G['X'], G['Y']
    tone_ = 1.0 + .12 * nz(X, Y, SEED + 21, 4, 1 / 40.0)
    c = np.array(DUST_WARM[:3]) * tone_[..., None]
    turf = sstep(.3, .7, .5 + .5 * nz(X, Y, SEED + 25, 3, 1 / 70.0))[..., None] * .35
    c = c * (1 - turf) + np.array(REED[:3]) * .8 * turf
    paved = (1 - sstep(G['path_half'] - .5, G['path_half'] + 1.5, G['path_d'])) * np.where(G['road'], 1.0, .45)
    c = c * (1 - paved[..., None]) + np.array(STONE_HONEY[:3]) * .82 * paved[..., None]
    scar = (G['scar'] * (.78 + .22 * nz(X, Y, SEED + 31, 3, 1 / 18.0)))[..., None] * .5
    c = c * (1 - scar) + np.array((.42, .26, .10)) * scar
    rock = sstep(.7, 1.2, G['slope'])[..., None]
    c = c * (1 - rock) + np.array(ROCK_RED[:3]) * 1.5 * rock
    wet = (1 - sstep(.98, 1.25, G['pool']))[..., None] * .55
    c = c * (1 - wet) + np.array((.12, .10, .07)) * wet
    deep = sstep(4.0, 60.0, G['beyond'])[..., None] * .5
    c = c * (1 - deep) + np.array(ROCK_PLUM[:3]) * deep
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


def terrain_tile(k):
    """SM_ST_Terrain_<i>_<j> (k = i * TILES_Y + j): one 320 m tile in world metres; neighbours share their edge rows."""
    i, j = divmod(k, plan.TILES_Y)
    G = grid()
    xs, ys = slice(i * TILE_X, (i + 1) * TILE_X + 1), slice(j * TILE_Y, (j + 1) * TILE_Y + 1)
    px, py, ph = G['X'][xs, ys], G['Y'][xs, ys], G['H'][xs, ys].astype(np.float64)
    colour = np.concatenate([_albedo()[xs, ys].reshape(-1, 3), np.ones((px.size, 1))], 1)
    p = Part('SM_ST_Terrain_%d_%d' % (i, j), (GROUND,))
    p.add(np.stack([px.ravel(), py.ravel(), ph.ravel()], 1), _grid_faces(*px.shape), colour, 0, True)
    p.normals = vertex_normals()[xs, ys].reshape(-1, 3)
    return p


def pool():
    """SM_ST_Pool: a unit sheet of water 2 m by 2 m, gridded, at z 0; the scenario stretches one over each pool."""
    p = Part('SM_ST_Pool', (WATER,))
    xs = np.linspace(-1.0, 1.0, 9)
    gx, gy = np.meshgrid(xs, xs, indexing='ij')
    p.add(np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], 1), _grid_faces(*gx.shape), col(.30, .26, .20), 0, True)
    return p


def haze():
    """SM_ST_Haze: the floor of the drop, 240 m down: a far sheet of dark ground under the western haze, so the
    abyss has a bottom where the fog thins."""
    p = Part('SM_ST_Haze', (GROUND,))
    xs, ys = np.arange(-1600.0, 1601.0, 100.0), np.arange(-3000.0, -300.0, 100.0)
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    z = -60.0 + 14.0 * nz(gx, gy, SEED + 51, 4, 1 / 300.0) + 40.0 * nz(gx, gy, SEED + 53, 3, 1 / 900.0)
    colour = np.concatenate([np.tile(np.array(ROCK_PLUM[:3]) * 1.2, (gx.size, 1)), np.ones((gx.size, 1))], 1)
    p.add(np.stack([gx.ravel(), gy.ravel(), z.ravel()], 1), _grid_faces(*gx.shape), colour, 0, True)
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


# The city's houses (mesh, half depth along x, half width along y): Kathodos's, standing with their fronts (+x) to the
# street.
HOUSES = (('SM_AN_House0', 4.0, 3.5), ('SM_AN_House1', 3.0, 3.0))


def layout():
    G = grid()
    H = G['H'].astype(np.float64)
    rng = np.random.default_rng(SEED)
    keep = _clear(G)
    walk = (G['rim'] < .9) & (G['beyond'] < -6.0)
    busy = keep | (G['path_d'] < G['path_half'] + 2.5) | (G['pool'] < 1.3) | (G['rock'] > .02) | (G['beyond'] > -8.0)
    rows = {}
    taken = []

    def pick(mask, x, y):
        return sample(mask.astype(np.float64), x, y) > .5

    def free(x, y, r):
        return all(math.hypot(x - tx, y - ty) > r + tr for tx, ty, tr in taken)

    def blocked(x, y, pad):
        return bool(keep[int(round((x + HALF_X) / CELL)) % NX, int(round((y + HALF_Y) / CELL)) % NY]) or plan.on_wall(x, y, pad) or \
            plan.off_edge(x, y, pad + 6.0) or plan.in_pool(x, y, pad) or plan.on_rock(x, y, pad) or plan.rim(x, y) > .9

    def candidates(cell, x0=-HALF_X + 8, x1=HALF_X - 8, y0=-HALF_Y + 8, y1=HALF_Y - 8):
        xs, ys = np.arange(x0, x1, cell), np.arange(y0, y1, cell)
        gx, gy = np.meshgrid(xs, ys, indexing='ij')
        return (gx + rng.uniform(.1, .9, gx.shape) * cell).ravel(), (gy + rng.uniform(.1, .9, gy.shape) * cell).ravel()

    def put(name, x, y, scale, sink=0.0, yaw=None, tilt=0.0):
        z = sample(H, x, y) - sink
        out = rows.setdefault(name, [])
        for k in range(len(x)):
            out.append(_row(x[k], y[k], z[k] if np.ndim(z) else z, rng.uniform(0, 360) if yaw is None else yaw[k], rng.uniform(-tilt, tilt),
                            rng.uniform(-tilt, tilt), scale[k] if np.ndim(scale) else scale))

    # The city: houses along both sides of every road, fronts to the street, gaps between them.
    for name, kind, half, points in plan.PATHS:
        if kind != 'road' or name == 'Nave Road':
            continue
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            length = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / length, (by - ay) / length
            for side in (-1, 1):
                d = 6.0
                while d < length - 6.0:
                    mesh, hx, hy = HOUSES[rng.integers(0, len(HOUSES))]
                    d += hy
                    off = half + 4.0 + hx
                    x_, y_ = ax + ux * d - uy * side * off, ay + uy * d + ux * side * off
                    face = math.degrees(math.atan2(-ux * side, uy * side))
                    if not blocked(x_, y_, hx + 2.0) and free(x_, y_, max(hx, hy)) and rng.uniform() < .62:
                        ground = min(float(sample(H, x_ - hx * .7, y_)), float(sample(H, x_ + hx * .7, y_)), float(sample(H, x_, y_ - hy * .7)),
                                     float(sample(H, x_, y_ + hy * .7)))
                        rows.setdefault(mesh, []).append(_row(x_, y_, ground - .4, face))
                        taken.append((x_, y_, max(hx, hy) * .95))
                    d += hy + (rng.uniform(5.0, 12.0) if rng.uniform() < .35 else 1.0)
    # Columns and lanterns along the roads: the Nave keeps its whole avenue, the rest is broken here and there.
    for name, kind, half, points in plan.PATHS:
        if kind != 'road':
            continue
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            length = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / length, (by - ay) / length
            for k in range(int(length // 20.0)):
                d = 10.0 + k * 20.0
                for side in (-1, 1):
                    x_, y_ = ax + ux * d - uy * side * (half + 2.6), ay + uy * d + ux * side * (half + 2.6)
                    if blocked(x_, y_, 1.0) or not free(x_, y_, .8):
                        continue
                    whole = name == 'Nave Road' or rng.uniform() < .45
                    put('SM_AN_Column' if whole else 'SM_AN_ColumnBroken', np.array([x_]), np.array([y_]), 1.0, sink=.2,
                        yaw=np.array([math.degrees(math.atan2(uy, ux))]))
                    taken.append((x_, y_, 1.0))
                if k % 2 == 0:
                    side = 1 if (k // 2) % 2 else -1
                    x_, y_ = ax + ux * (d + 10) - uy * side * (half + 1.2), ay + uy * (d + 10) + ux * side * (half + 1.2)
                    if d + 10 < length and not blocked(x_, y_, 1.0) and free(x_, y_, .5):
                        put('SM_AN_Lantern', np.array([x_]), np.array([y_]), 1.0, sink=.05, yaw=np.array([0.0]))
    # Crystals in clumps over the open ground (Arche's, warmed by their material), thickest round the Galleries and
    # the Spire's rock; great crystals here and there as landmarks.
    x, y = candidates(6.0)
    clumps = rng.uniform((-HALF_X + 40, -HALF_Y + 60), (HALF_X - 40, HALF_Y - 30), (70, 2))
    near = np.min(np.hypot(x[:, None] - clumps[None, :, 0], y[:, None] - clumps[None, :, 1]), 1)
    rockside = np.clip(1 - np.abs(np.hypot(x - plan.SPIRE_ROCK[0], y - plan.SPIRE_ROCK[1]) - plan.SPIRE_ROCK[2] - 10.0) / 12.0, 0, 1)
    chance = .05 + .7 * np.exp(-(near / 10.0) ** 2) + .5 * rockside
    ok = pick(walk & ~busy, x, y) & (rng.uniform(0, 1, len(x)) < chance) & (sample(G['slope'], x, y) < .5)
    ok &= np.array([free(a, b, 1.2) for a, b in zip(x, y)], bool)
    x, y = x[ok], y[ok]
    kind = rng.choice(3, len(x), p=(.5, .33, .17))
    for k in range(3):
        sel = kind == k
        put('SM_AV_Crystal%d' % k, x[sel], y[sel], rng.uniform(.9, 1.6, sel.sum()), sink=.15, tilt=7.0)
    great = [(gx, gy) for gx, gy in clumps[::4] if pick(walk & ~busy, np.array([gx]), np.array([gy]))[0]]
    if great:
        put('SM_AV_CrystalGreat', np.array([g[0] for g in great]), np.array([g[1] for g in great]), rng.uniform(.8, 1.2, len(great)), sink=.6, tilt=5.0)
    # Boulders and stones (scanned), most toward the cliffs and the edge.
    x, y = candidates(11.0)
    ok = pick(walk & ~busy, x, y) & (rng.uniform(0, 1, len(x)) < .12 + .3 * np.clip((sample(G['rim'], x, y) - .7) / .2, 0, 1))
    ok &= np.array([free(a, b, 1.0) for a, b in zip(x, y)], bool)
    x, y = x[ok], y[ok]
    big = rng.uniform(0, 1, len(x)) < .3
    put('SM_GS_Boulder', x[big], y[big], rng.uniform(.8, 2.0, big.sum()), sink=.35, tilt=10.0)
    put('SM_GS_Stone', x[~big], y[~big], rng.uniform(1.0, 2.8, (~big).sum()), sink=.1, tilt=14.0)
    # Dry grass on the open ground, thick round the pools (the reed beds).
    x, y = candidates(3.0)
    reeds = np.clip(1 - (sample(G['pool'], x, y) - 1.3) / 1.2, 0, 1)
    ok = pick(walk & ~busy | (G['pool'] < 2.4) & (G['pool'] > 1.25), x, y) & \
        (rng.uniform(0, 1, len(x)) < .22 * (.8 + .8 * nz(x, y, SEED + 41, 3, 1 / 45.0)) + .7 * reeds) & (sample(G['slope'], x, y) < .45)
    put('SM_GV_Grass', x[ok], y[ok], rng.uniform(.7, 1.3, ok.sum()) * (1 + reeds[ok] * .8), sink=.02)
    # The western edge's parapet: panels 12 m long along the edge, 2.5 m in from it, from rim to rim.
    x_ = -HALF_X + 40.0
    while x_ < HALF_X - 40.0:
        y_ = plan.edge_y(x_) + 2.5
        if plan.rim(x_, y_) < 1.02:
            heading = math.degrees(math.atan2(plan.edge_y(x_ + 3.0) - plan.edge_y(x_ - 3.0), 6.0))
            rows.setdefault('SM_SN_Parapet', []).append(_row(x_, y_, float(height_at(x_, y_ + 1.5)) - .3, heading))
        x_ += 11.9
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
    for name in ('STAIR', 'HOUSE', 'TUNING', 'MARKET', 'TERRACE_STILL', 'LOW_BELL', 'GALLERY_STILL', 'MID_BELL', 'SPIRE_STILL', 'HIGH_BELL',
                 'SPIRE', 'NAVE_STILL', 'CHOIR_GATE', 'CONCORD', 'HORN', 'HALL', 'SEALED_TRACE', 'SEALED_WEAVE'):
        x, y = getattr(plan, name)[:2]
        out('  %-14s (%7.1f, %7.1f) z %6.1f' % (name, x, y, float(height_at(x, y))))
    for k, (x, y, *_r) in enumerate(plan.POOLS):
        out('  pool %d        (%7.1f, %7.1f) z %6.1f, water %6.1f' % (k, x, y, float(height_at(x, y)), plan.rise_z(x) + _r[2]))
    if rows is not None:
        out('scatter: ' + ', '.join('%s %d' % (k, len(v)) for k, v in rows.items()))


MESHES = [terrain_tile, pool, haze]
VARIANTS = {terrain_tile: plan.TILES_X * plan.TILES_Y}
_TILE = {'size': (2 * HALF_X / plan.TILES_X, 2 * HALF_Y / plan.TILES_Y, 0), 'tol': .01, 'pivot': 'any'}
CONTRACT = {'SM_ST_Terrain_%d_%d' % (i, j): _TILE for i in range(plan.TILES_X) for j in range(plan.TILES_Y)}
CONTRACT['SM_ST_Pool'] = {'pivot': 'any'}
CONTRACT['SM_ST_Haze'] = {'pivot': 'any'}
