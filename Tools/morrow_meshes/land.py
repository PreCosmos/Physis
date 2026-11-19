"""The land of Morrow (level 8, Earth): the height grid, the terrain tiles, the reservoir's ice and the scatter.

The valley floor (plan.floor_z) comes down from the south pass (46 m) to the Mill House (22 m) and the Gorge (18 m),
then climbs gently north to the dam's foot (32 m); the embankment rises from there to the crest (84 m), and behind it
the reservoir's bed lies under its ice (80 m). The Gorge cuts the floor from wall to wall, frozen at its bottom, with a
ramp out up its south side; the millpond is a shallow hollow under its own ice; the Telegraph House stands on a rock in
the north-east and the Glider Field on a bench in the east; beyond the walkable oval the land climbs into peaks on
every side. Streets and pads are levelled.

Terrain vertices carry the Grove ground shader's layer weights (colour and uv, see layers()), which Morrow's own copy
of it (physis_morrow_tools: M_MW_Ground) frosts on every face that looks up.

Scatter rows are [x, y, z (cm), pitch, yaw, roll, sx, sy, sz], keyed by mesh name, ready for the level build's
instanced actors. Halcyon's houses line the streets (frosted by their materials in Morrow), orchards of bare trees
the Orchard Road, rubble and boulders the open ground, firs the slopes.
"""
import functools
import json
import math
from pathlib import Path

from kit import *  # noqa: F401,F403
import physis_morrow_plan as plan

HALF_X, HALF_Y, CELL = plan.HALF_X, plan.HALF_Y, plan.CELL
NX, NY = int(round(2 * HALF_X / CELL)) + 1, int(round(2 * HALF_Y / CELL)) + 1
TILE_X, TILE_Y = (NX - 1) // plan.TILES_X, (NY - 1) // plan.TILES_Y
SEED = 8108


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


def _floor(X):
    return np.vectorize(plan.floor_z)(X)


def _shape():
    xs, ys = np.linspace(-HALF_X, HALF_X, NX), np.linspace(-HALF_Y, HALF_Y, NY)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    base = _floor(xs)[:, None] * np.ones((1, NY))
    # The dam: the embankment from its foot to the crest, the crest itself, then the reservoir's bed.
    up = np.clip((X - plan.FOOT_X) / (plan.CREST_X0 - plan.FOOT_X), 0.0, 1.0)
    embank = plan.FOOT_Z + (plan.CREST_Z - plan.FOOT_Z) * up
    lake = sstep(plan.CREST_X1, plan.CREST_X1 + 10.0, X)
    dam = np.where(X > plan.FOOT_X, embank * (1 - lake) + (plan.LAKE_BED + .8 * nz(X, Y, SEED + 5, 3, 1 / 60.0)) * lake, base)
    base = np.where(X > plan.FOOT_X, dam, base)
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
    # The Dam Stair: a straight cut up the embankment's middle, levelled across its width.
    stair = (1 - sstep(plan.STAIR_HALF, plan.STAIR_HALF + 4.0, np.abs(Y))) * sstep(plan.FOOT_X - 40.0, plan.FOOT_X - 20.0, X) * \
        (1 - sstep(plan.CREST_X1, plan.CREST_X1 + 2.0, X))
    level = np.maximum(np.maximum(1 - sstep(path_half, path_half + 6.0, path_d), pad), stair)
    rough = 1.0 * nz(X, Y, SEED, 4, 1 / 140.0) + .3 * nz(X, Y, SEED + 7, 4, 1 / 24.0)
    on_dam = sstep(plan.FOOT_X - 6.0, plan.FOOT_X + 6.0, X) * (1 - lake)
    H = base + rough * (1 - level) * (1 - .8 * on_dam) * (1 - lake)
    # The millpond: a shallow hollow under its ice.
    px, py, pr = plan.POND
    d = np.hypot(X - px, Y - py)
    hollow = 1 - sstep(pr - 2.0, pr + 4.0, d)
    H = H * (1 - hollow) + (plan.floor_z(px) - 1.2) * hollow
    # The Glider Field: a bench standing FIELD_LIFT above the floor, its skirt sloping down 22 m.
    fx, fy = plan.FIELD
    d = np.hypot(X - fx, Y - fy)
    bench = 1 - sstep(plan.FIELD_RADIUS, plan.FIELD_RADIUS + 22.0, d)
    top = plan.floor_z(fx) + plan.FIELD_LIFT
    H = np.maximum(H, H * (1 - bench) + (top + .4 * nz(X, Y, SEED + 17, 3, 1 / 30.0) * (1 - sstep(0, plan.FIELD_RADIUS, d))) * bench)
    # The Telegraph House's rock: a flat top with its foot on the floor; the Telegraph Path climbs a shoulder to it.
    rx, ry, rr, rh = plan.ROCK
    d = np.hypot(X - rx, Y - ry)
    rock_top = plan.floor_z(rx) + rh
    head = 1 - sstep(rr, rr + 20.0, d)
    H = np.maximum(H, H * (1 - head) + rock_top * head + 1.5 * nz(X, Y, SEED + 13, 3, 1 / 20.0) * head * sstep(rr - 4, rr + 10, d))
    spit_d = np.full(X.shape, np.inf)
    points = next(pts for name, _, _, pts in plan.PATHS if name == 'Telegraph Path')
    for (ax_, ay_), (bx_, by_) in zip(points, points[1:]):
        spit_d = np.minimum(spit_d, _segment_distance(X, Y, ax_, ay_, bx_, by_))
    shoulder = 1 - sstep(5.0, 14.0, spit_d)
    start = plan.floor_z(points[0][0]) + plan.FIELD_LIFT
    rise = start + (rock_top - start) * (1 - sstep(rr, rr + 150.0, d)) ** 1.3
    H = np.maximum(H, H * (1 - shoulder) + rise * shoulder)
    # The Gorge: a cut 26 m across from wall to wall, frozen at its bottom.
    gorge_x = plan.GORGE_X + plan.GORGE_WAVE * np.sin(Y / plan.GORGE_PERIOD + .6)
    gorge_d = np.abs(X - gorge_x)
    cut = 1 - sstep(plan.GORGE_FLOOR, plan.GORGE_RIM, gorge_d)
    H = H * (1 - cut) + (plan.GORGE_BED + .3 * nz(X, Y, SEED + 3, 3, 1 / 18.0)) * cut
    # The ramp: whoever falls into the Gorge walks out up a cut in its south wall (it leads only south).
    along = (gorge_x - plan.GORGE_FLOOR) - X
    band = 1 - sstep(3.5, 5.5, np.abs(Y - plan.GORGE_RAMP_Y))
    ramp = plan.GORGE_BED + .4 + np.clip(along, 0, None) * math.tan(math.radians(17.0))
    slip = band * (along > -1.0) * (along < 60.0)
    H = np.where(slip > 0, np.minimum(H, H * (1 - band) + ramp * band), H)
    # The peaks: beyond the walkable oval the land climbs on every side. The dam's ends are let into the slopes.
    rim = np.hypot(X / plan.RIM[0], Y / plan.RIM[1])
    climb = sstep(plan.RIM_START, plan.RIM_END, rim)
    ridges = 1 - np.abs(nz(X, Y, SEED + 11, 5, 1 / 80.0))
    H = H + plan.RIM_RISE * climb ** 1.4 * (.7 + .5 * ridges) + 40.0 * sstep(1.05, 1.6, rim)
    gx, gy = np.gradient(H, CELL)
    scar = np.zeros(X.shape)
    for sx, sy, radius in plan.SCAR:
        scar = np.maximum(scar, np.clip(1 - np.hypot(X - sx, Y - sy) / radius, 0, 1))
    return {'X': X, 'Y': Y, 'H': H.astype(np.float32), 'slope': np.hypot(gx, gy), 'path_d': path_d, 'path_half': path_half, 'road': road, 'pad': pad,
            'gorge_d': gorge_d, 'rim': rim, 'scar': scar, 'lake': lake, 'head': head, 'bench': bench, 'stair': stair, 'pond': hollow, 'dam': on_dam}


@functools.lru_cache(maxsize=1)
def grid():
    return _shape()


def height_at(x, y):
    return sample(grid()['H'].astype(np.float64), x, y)


@functools.lru_cache(maxsize=1)
def vertex_normals():
    gx, gy = np.gradient(grid()['H'].astype(np.float64), CELL)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def _grid_faces(mx, my):
    idx = np.arange(mx * my).reshape(mx, my)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    return np.stack([a, b, c, d], 1).tolist()      # counter-clockwise seen from above


def layers():
    """The ground's layer weights for the Grove's ground shader (Morrow's copy, M_MW_Ground): colour R meadow grass,
    G trodden earth, B gravel, A 1 - blight (here the Rime's stain); uv u asphalt (the roads), v moss and damp. What is
    left is forest floor; rock comes from the slope, in the shader."""
    G = grid()
    X, Y, H = G['X'], G['Y'], G['H'].astype(np.float64)
    half = np.where(np.isfinite(G['path_d']), G['path_half'], 1.0)
    on_path = 1 - sstep(half * .75, half + 1.6, G['path_d'])
    cracks = .5 + .5 * noise2(X / 3.1, Y / 3.1, SEED + 41)
    asphalt = on_path * G['road'] * sstep(.18, .5, cracks + .25 * (1 - sstep(half * .4, half, G['path_d'])))
    dirt = on_path * (~G['road']) + .5 * on_path * G['road'] * (1 - asphalt)
    worn = sstep(.55, .8, .5 + .5 * nz(X, Y, SEED + 23, 3, 1 / 26.0))
    dirt = np.clip(np.maximum(dirt, .7 * G['pad'] + .4 * worn), 0, 1)
    gravel = np.maximum(1 - sstep(plan.GORGE_FLOOR, plan.GORGE_RIM + 1.0, G['gorge_d']), G['stair'] * .8)
    gravel = np.clip(np.maximum(gravel, .9 * G['dam'] * (1 - G['stair'])), 0, 1)
    gravel = np.clip(np.maximum(gravel, G['lake']), 0, 1)
    meadow = sstep(.25, .6, .5 + .5 * nz(X, Y, SEED + 211, 3, 1 / 120.0))
    grass = np.clip((.6 + .4 * meadow) * (1 - gravel) * (1 - np.clip(dirt + asphalt, 0, 1)), 0, 1)
    damp = np.clip(G['pond'] + (1 - sstep(.0, 8.0, H - plan.TOWN_Z)) * .3, 0, 1)
    moss = np.clip(.5 * damp + .3 * sstep(.3, .8, G['slope']), 0, 1) * (1 - np.clip(dirt + asphalt, 0, 1))
    blight = np.clip(G['scar'] * .55 * (.6 + .4 * nz(X, Y, SEED + 31, 3, 1 / 16.0)), 0, 1)
    return {'grass': grass, 'dirt': dirt, 'gravel': gravel, 'asphalt': np.clip(asphalt, 0, 1), 'moss': moss, 'blight': blight}


@functools.lru_cache(maxsize=1)
def _layers():
    return layers()


def terrain_tile(k):
    """SM_OT_Terrain_<i>_<j> (k = i * TILES_Y + j): one 320 m tile in world metres; neighbours share their edge rows.
    Colour and uv carry the layer weights (layers()); `normals` are the whole grid's, so seams shade as one."""
    i, j = divmod(k, plan.TILES_Y)
    G, L = grid(), _layers()
    xs, ys = slice(i * TILE_X, (i + 1) * TILE_X + 1), slice(j * TILE_Y, (j + 1) * TILE_Y + 1)
    px, py, ph = G['X'][xs, ys], G['Y'][xs, ys], G['H'][xs, ys].astype(np.float64)
    weights = np.stack([L['grass'][xs, ys], L['dirt'][xs, ys], L['gravel'][xs, ys], 1 - L['blight'][xs, ys]], -1).reshape(-1, 4)
    uv = np.stack([L['asphalt'][xs, ys], L['moss'][xs, ys]], -1).reshape(-1, 2)
    p = Part('SM_OT_Terrain_%d_%d' % (i, j), (GROUND,))
    p.add(np.stack([px.ravel(), py.ravel(), ph.ravel()], 1), _grid_faces(*px.shape), weights, 0, True, uv=uv)
    p.normals = vertex_normals()[xs, ys].reshape(-1, 3)
    return p


def lake():
    """SM_OT_Lake: the reservoir's surface at plan.ICE_Z, a sheet from the crest's upstream edge to the far shore (the
    peaks hide it wherever they stand above it). The level wears it in ice (MorrowScar) and in water once the Lull
    stops (a second actor, MorrowBloom). Pivot at world origin."""
    p = Part('SM_OT_Lake', (WATER,))
    xs = np.arange(plan.CREST_X1 - 2.0, HALF_X + 300.1, 6.0)
    ys = np.arange(-HALF_Y - 200.0, HALF_Y + 200.1, 6.0)
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    p.add(np.stack([gx.ravel(), gy.ravel(), np.full(gx.size, plan.ICE_Z)], 1), _grid_faces(*gx.shape), ICE, 0, True)
    return p


def gorge_ice():
    """SM_OT_GorgeIce: the frozen river along the Gorge's bottom, a strip 18 m wide following its line from wall to
    wall, 5 cm above the bed (it only shows the ice; the ground under it carries her). Pivot at world origin."""
    p = Part('SM_OT_GorgeIce', (CRYSTAL,))
    ys = np.arange(-HALF_Y, HALF_Y + .1, 4.0)
    us = np.linspace(-plan.GORGE_FLOOR - .5, plan.GORGE_FLOOR + .5, 7)
    verts = []
    for y in ys:
        cx = plan.gorge_x(y)
        for u in us:
            verts.append((cx + u, y, float(height_at(cx + u, y)) + .05))
    p.add(np.array(verts), _grid_faces(len(ys), len(us)), ICE, 0, True)
    # The strip runs along y, so its quads wind the other way: turn them.
    p.f = [face[::-1] for face in p.f]
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


# Halcyon's houses (mesh, half depth along x, half width along y): they stand with their fronts (+x) to the street.
HOUSES = (('SM_HN_House0', 4.0, 3.5), ('SM_HN_House1', 3.2, 3.0), ('SM_HN_House2', 4.0, 3.5), ('SM_HN_House3', 4.5, 4.0))


def layout():
    G = grid()
    H = G['H'].astype(np.float64)
    rng = np.random.default_rng(SEED)
    keep = _clear(G)
    walk = G['rim'] < .9
    busy = keep | (G['path_d'] < G['path_half'] + 2.5) | (G['gorge_d'] < plan.GORGE_RIM + 3.0) | (G['pond'] > .05) | (G['head'] > .5) | \
        (G['bench'] > .5) | (G['stair'] > .05) | (G['dam'] > .02)
    rows = {}
    taken = []      # (x, y, radius): houses and big props, so nothing lands inside another

    def pick(mask, x, y):
        return sample(mask.astype(np.float64), x, y) > .5

    def free(x, y, r):
        return all(math.hypot(x - tx, y - ty) > r + tr for tx, ty, tr in taken)

    def blocked(x, y, pad):
        return bool(keep[int(round((x + HALF_X) / CELL)) % NX, int(round((y + HALF_Y) / CELL)) % NY]) or plan.in_gorge(x, y, pad) or \
            plan.on_dam(x, y, pad) or plan.in_pond(x, y, pad) or plan.rim(x, y) > .9 or \
            math.hypot(x - plan.FIELD[0], y - plan.FIELD[1]) < plan.FIELD_RADIUS + pad or math.hypot(x - plan.ROCK[0], y - plan.ROCK[1]) < plan.ROCK[2] + 16 + pad

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

    # The town: houses along both sides of the town's roads and lanes north of the Gorge, and a hamlet by the mill.
    for name, kind, half, points in plan.PATHS:
        if kind == 'path' or name == 'Orchard Road':
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
                    sparse = .55 if name in ('Dam Road', 'Ice House Lane') and (ax > 60 or ay > 100) else .82
                    if not blocked(x_, y_, hx + 2.0) and free(x_, y_, max(hx, hy)) and rng.uniform() < sparse:
                        ground = min(float(sample(H, x_ - hx * .7, y_)), float(sample(H, x_ + hx * .7, y_)), float(sample(H, x_, y_ - hy * .7)),
                                     float(sample(H, x_, y_ + hy * .7)))
                        rows.setdefault(mesh, []).append(_row(x_, y_, ground - .4, face))
                        taken.append((x_, y_, max(hx, hy) * .95))
                    d += hy + (rng.uniform(4.0, 9.0) if rng.uniform() < .3 else .5)
    # Lamps along the roads.
    for name, kind, half, points in plan.PATHS:
        if kind != 'road':
            continue
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            length = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / length, (by - ay) / length
            for k in range(int(length // 22.0)):
                side = 1 if k % 2 else -1
                d = 11.0 + k * 22.0
                x_, y_ = ax + ux * d - uy * side * (half + .8), ay + uy * d + ux * side * (half + .8)
                if not blocked(x_, y_, 3.0) and free(x_, y_, .5):
                    put('SM_HN_Lamp', np.array([x_]), np.array([y_]), 1.0, sink=.05, yaw=np.array([math.degrees(math.atan2(uy, ux))]))
    # The orchards: rows of bare trees either side of the Orchard Road, frosted, a few fallen out of line.
    orchard = next(pts for name, _, _, pts in plan.PATHS if name == 'Orchard Road')
    for (ax, ay), (bx, by) in zip(orchard, orchard[1:]):
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        for side in (-1, 1):
            for row in range(4):
                off = 10.0 + row * 7.0
                d = 3.0 + rng.uniform(0, 3)
                while d < length:
                    x_, y_ = ax + ux * d - uy * side * off + rng.uniform(-.6, .6), ay + uy * d + ux * side * off + rng.uniform(-.6, .6)
                    if not blocked(x_, y_, 2.0) and free(x_, y_, 1.6) and rng.uniform() < .85:
                        mesh = 'SM_GV_Snag' if rng.uniform() < .7 else 'SM_GV_Sapling'
                        put(mesh, np.array([x_]), np.array([y_]), rng.uniform(.55, .8), sink=.2, tilt=4.0)
                        taken.append((x_, y_, 1.2))
                    d += 6.5
    # Firs and birches on the lower slopes and in the gardens; frosted grass over the open ground.
    x, y = candidates(8.0)
    slope_ok = sample(G['slope'], x, y) < .55
    edge = sample(G['rim'], x, y)
    ok = (pick(walk & ~busy, x, y) | ((edge > .82) & (edge < .97))) & ~pick(busy, x, y) & slope_ok
    ok &= rng.uniform(0, 1, len(x)) < (.18 + .6 * np.clip((edge - .75) / .2, 0, 1))
    ok &= np.array([free(a, b, 1.8) and not blocked(a, b, 1.0) or plan.rim(a, b) > .85 and not plan.on_dam(a, b, 4.0) for a, b in zip(x, y)], bool)
    x, y = x[ok], y[ok]
    kind = rng.choice(4, len(x), p=(.42, .2, .26, .12))
    for k, (mesh, lo, hi) in enumerate((('SM_GV_Pine', .7, 1.2), ('SM_GV_Birch', .6, .9), ('SM_GV_Bush', .7, 1.3), ('SM_GV_Snag', .6, 1.0))):
        sel = kind == k
        put(mesh, x[sel], y[sel], rng.uniform(lo, hi, sel.sum()), sink=.2, tilt=3.0)
    x, y = candidates(3.0)
    ok = pick(walk & ~busy, x, y) & (rng.uniform(0, 1, len(x)) < .42 * (.7 + .6 * nz(x, y, SEED + 41, 3, 1 / 45.0))) & (sample(G['slope'], x, y) < .5)
    put('SM_GV_Grass', x[ok], y[ok], rng.uniform(.5, 1.0, ok.sum()), sink=.02)
    # Boulders and stones: fallen from the peaks, thickest at the valley's edges and in the Gorge.
    x, y = candidates(10.0)
    near = np.clip((sample(G['rim'], x, y) - .7) / .25, 0, 1) + np.clip(1 - np.abs(x - plan.GORGE_X) / 60.0, 0, 1) * .5
    ok = pick(walk & ~busy, x, y) & (rng.uniform(0, 1, len(x)) < .08 + .35 * near)
    ok &= np.array([free(a, b, 1.0) for a, b in zip(x, y)], bool)
    x, y = x[ok], y[ok]
    big = rng.uniform(0, 1, len(x)) < .3
    put('SM_GS_Boulder', x[big], y[big], rng.uniform(.6, 1.6, big.sum()), sink=.3, tilt=12.0)
    put('SM_GS_Stone', x[~big], y[~big], rng.uniform(1.0, 2.6, (~big).sum()), sink=.1, tilt=16.0)
    # The dam's riprap: big stones along the embankment's foot and its flanks.
    for k in range(160):
        y_ = rng.uniform(-HALF_Y, HALF_Y)
        if abs(y_) < plan.STAIR_HALF + 4.0 or plan.rim(plan.FOOT_X, y_) > .97:
            continue
        x_ = plan.FOOT_X + rng.uniform(-4.0, 8.0)
        put('SM_GS_Boulder', np.array([x_]), np.array([y_]), rng.uniform(.8, 1.5), sink=.5, tilt=20.0)
    return dict(sorted(rows.items()))


def write_height(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    meta = {'half_x': HALF_X, 'half_y': HALF_Y, 'cell': CELL, 'nx': NX, 'ny': NY, 'water': plan.ICE_Z,
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
    for name in ('CHAPEL', 'MILL', 'BENCH', 'POND', 'BRIDGE_SOUTH', 'BRIDGE_NORTH', 'SQUARE', 'SCHOOL', 'FIELD', 'ROCK', 'TELEGRAPH', 'STAIR_FOOT',
                 'CREST', 'HOLD', 'ICEHOUSE'):
        x, y = getattr(plan, name)[:2]
        out('  %-14s (%7.1f, %7.1f) z %6.1f' % (name, x, y, float(height_at(x, y))))
    if rows is not None:
        out('scatter: ' + ', '.join('%s %d' % (k, len(v)) for k, v in rows.items()))


MESHES = [terrain_tile, lake, gorge_ice]
VARIANTS = {terrain_tile: plan.TILES_X * plan.TILES_Y}
_TILE = {'size': (2 * HALF_X / plan.TILES_X, 2 * HALF_Y / plan.TILES_Y, 0), 'tol': .01, 'pivot': 'any'}
CONTRACT = {'SM_OT_Terrain_%d_%d' % (i, j): _TILE for i in range(plan.TILES_X) for j in range(plan.TILES_Y)}
CONTRACT['SM_OT_Lake'] = {'pivot': 'any'}
CONTRACT['SM_OT_GorgeIce'] = {'pivot': 'any'}
