"""The land of Kathodos (level 5, Arche): the height grid, the terrain tiles, the Cisterns' water and the scatter.

The basin is three tiers of 12 m (plan.TIER), each riser a 3 m run of cliff nobody climbs; the Great Chasm cuts the
Lower Tier from wall to wall; the Cisterns are a bowl of water on the Lower Tier's west side with the Mirror's island
in it; the Garden's pinnacle stands on the Middle Tier and the Galleries' mesa on the Upper; beyond the walkable oval
the land climbs 260 m into the rim. Roads and pads are levelled.

Terrain vertices carry the ground's albedo (linear RGB): pale dust on the flats, flagstone on the roads, dark blue
rock where it is steep, a violet-grey scar where the unweaving burnt the ground. The material lays a scanned rock
over it (physis_arche_tools: MI_AR_Ground), so the colour is the tint and the scan the detail.

Scatter rows are [x, y, z (cm), pitch, yaw, roll, sx, sy, sz], ready for the level build's instanced actors, keyed by
mesh name; a key 'Air:<mesh>' holds the unwoven stones that hang in the air (no collision, tag ArcheScar).
"""
import functools
import json
import math
from pathlib import Path

from kit import *  # noqa: F401,F403
import physis_arche_plan as plan

HALF_X, HALF_Y, CELL = plan.HALF_X, plan.HALF_Y, plan.CELL
NX, NY = int(round(2 * HALF_X / CELL)) + 1, int(round(2 * HALF_Y / CELL)) + 1
TILE_X, TILE_Y = (NX - 1) // plan.TILES_X, (NY - 1) // plan.TILES_Y
SEED = 5105
ISLE_TOP = plan.TIER[0] + 1.0


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
    """fbm brought to about -1..1 (the toolkit's fbm is neither centred nor of unit range)."""
    f = fbm(x, y, seed, octaves, scale)
    return np.clip((f - f.mean()) / (2.5 * f.std() + 1e-9), -1.0, 1.0)


def _segment_distance(X, Y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((X - ax) * dx + (Y - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0.0, 1.0)
    return np.hypot(X - (ax + t * dx), Y - (ay + t * dy))


def _shape():
    xs, ys = np.linspace(-HALF_X, HALF_X, NX), np.linspace(-HALF_Y, HALF_Y, NY)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    t2 = plan.TIER2_X + plan.TIER_WAVE * np.sin(Y / plan.TIER_PERIOD + .4)
    t3 = plan.TIER3_X + plan.TIER_WAVE * np.sin(Y / plan.TIER_PERIOD + 2.1)
    tiers = plan.TIER[0] + plan.TIER_RISE * (sstep(0, plan.RISER, X - t2) + sstep(0, plan.RISER, X - t3))
    riser_d = np.minimum(np.abs(X - t2 - plan.RISER / 2), np.abs(X - t3 - plan.RISER / 2))
    # Roads, trails and pads: how far each point is from the nearest, and how wide that one is.
    path_d, path_half, road = np.full(X.shape, np.inf), np.zeros(X.shape), np.zeros(X.shape, bool)
    for ax, ay, bx, by, half, kind in plan.path_segments():
        d = _segment_distance(X, Y, ax, ay, bx, by)
        nearer = d - half < path_d - path_half
        path_d, path_half = np.where(nearer, d, path_d), np.where(nearer, half, path_half)
        road = np.where(nearer, kind == 'road', road)
    pad = np.zeros(X.shape)
    for px, py, radius, _ in plan.PADS:
        pad = np.maximum(pad, 1 - sstep(radius, radius + 8.0, np.hypot(X - px, Y - py)))
    level = np.maximum(1 - sstep(path_half, path_half + 6.0, path_d), pad)
    # The ground between: long swells and small roughness, none of it on the levelled ground.
    rough = 1.5 * nz(X, Y, SEED, 4, 1 / 150.0) + .45 * nz(X, Y, SEED + 7, 4, 1 / 28.0)
    H = tiers + rough * (1 - level) * (1 - .7 * (1 - sstep(0, 14.0, riser_d)))
    # The Garden's pinnacle and the Galleries' mesa: flat-topped stacks with sheer sides.
    px, py, pr, ph = plan.PINNACLE
    stack = 1 - sstep(pr, pr + 5.0, np.hypot(X - px, Y - py))
    H = H * (1 - stack) + (plan.TIER[1] + ph) * stack
    mx, my, mr, mh = plan.MESA
    mesa = 1 - sstep(mr, mr + 6.0, np.hypot(X - mx, Y - my))
    H = H * (1 - mesa) + (plan.TIER[2] + mh) * mesa
    # The Great Chasm.
    chasm_x = plan.CHASM_X + plan.CHASM_WAVE * np.sin(Y / plan.CHASM_PERIOD + .6)
    chasm_d = np.abs(X - chasm_x)
    chasm = 1 - sstep(plan.CHASM_FLOOR, plan.CHASM_RIM, chasm_d)
    H = H - plan.CHASM_DEPTH * chasm + chasm * .8 * nz(X, Y, SEED + 3, 3, 1 / 20.0)
    # The Cisterns: a bowl whose banks slope from the tier down to the water and on to the bed; the island in it.
    cx, cy, ax, ay = plan.CISTERNS
    m = np.hypot((X - cx) / ax, (Y - cy) / ay)
    bank = sstep(1.0, 1.26, m)
    bed = sstep(.62, 1.0, m)
    bowl = np.where(m >= 1.0, -0.4 + (plan.TIER[0] + .4) * bank, plan.CISTERN_BED + (plan.CISTERN_BED * -1 - .4) * bed)
    inside = 1 - sstep(1.22, 1.3, m)
    H = H * (1 - inside) + bowl * inside
    ix, iy, ir = plan.CISTERN_ISLE
    isle = 1 - sstep(ir, ir + 4.0, np.hypot(X - ix, Y - iy))
    H = H * (1 - isle) + ISLE_TOP * isle
    # The rim: beyond the walkable oval the land climbs, ridged.
    rim = np.hypot(X / plan.RIM[0], Y / plan.RIM[1])
    climb = sstep(plan.RIM_START, plan.RIM_END, rim)
    ridges = 1 - np.abs(nz(X, Y, SEED + 11, 5, 1 / 90.0))
    H = H + plan.RIM_RISE * climb ** 1.4 * (.7 + .5 * ridges) + 30.0 * sstep(1.05, 1.6, rim)
    gx, gy = np.gradient(H, CELL)
    scar = np.zeros(X.shape)
    for sx, sy, radius in plan.SCAR:
        scar = np.maximum(scar, np.clip(1 - np.hypot(X - sx, Y - sy) / radius, 0, 1))
    return {'X': X, 'Y': Y, 'H': H.astype(np.float32), 'slope': np.hypot(gx, gy), 'path_d': path_d, 'path_half': path_half, 'road': road, 'pad': pad,
            'riser_d': riser_d, 'chasm_d': chasm_d, 'cistern': m, 'rim': rim, 'scar': scar, 'stack': np.maximum(stack, mesa), 'isle': isle}


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
    c = np.array(DUST[:3]) * tone_[..., None]
    paved = (1 - sstep(G['path_half'] - .5, G['path_half'] + 1.5, G['path_d'])) * np.where(G['road'], 1.0, .45)
    c = c * (1 - paved[..., None]) + np.array(STONE_WORN[:3]) * paved[..., None]
    scar = (G['scar'] * (.78 + .22 * nz(X, Y, SEED + 31, 3, 1 / 18.0)))[..., None] * .6
    c = c * (1 - scar) + np.array((.20, .17, .26)) * scar
    rock = sstep(.7, 1.2, G['slope'])[..., None]
    c = c * (1 - rock) + np.array(ROCK_BLUE[:3]) * 1.5 * rock
    deep = sstep(0.0, plan.CHASM_RIM, plan.CHASM_RIM - G['chasm_d'])[..., None] * .45
    c = c * (1 - deep) + np.array(ROCK_DEEP[:3]) * deep
    wet = (1 - sstep(.98, 1.12, G['cistern']))[..., None] * .5
    c = c * (1 - wet) + np.array((.10, .14, .17)) * wet
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
    """SM_AT_Terrain_<i>_<j> (k = i * TILES_Y + j): one 320 m tile in world metres; neighbours share their edge rows."""
    i, j = divmod(k, plan.TILES_Y)
    G = grid()
    xs, ys = slice(i * TILE_X, (i + 1) * TILE_X + 1), slice(j * TILE_Y, (j + 1) * TILE_Y + 1)
    px, py, ph = G['X'][xs, ys], G['Y'][xs, ys], G['H'][xs, ys].astype(np.float64)
    colour = np.concatenate([_albedo()[xs, ys].reshape(-1, 3), np.ones((px.size, 1))], 1)
    p = Part('SM_AT_Terrain_%d_%d' % (i, j), (GROUND,))
    p.add(np.stack([px.ravel(), py.ravel(), ph.ravel()], 1), _grid_faces(*px.shape), colour, 0, True)
    p.normals = vertex_normals()[xs, ys].reshape(-1, 3)
    return p


def cistern():
    """SM_AT_Cistern: the Cisterns' surface at z 0, a sheet over the whole bowl (the banks hide its edge)."""
    cx, cy, ax, ay = plan.CISTERNS
    p = Part('SM_AT_Cistern', (WATER,))
    xs, ys = np.arange(cx - ax - 8, cx + ax + 8.1, 4.0), np.arange(cy - ay - 8, cy + ay + 8.1, 4.0)
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    p.add(np.stack([gx.ravel(), gy.ravel(), np.full(gx.size, plan.WATER)], 1), _grid_faces(*gx.shape), col(.20, .34, .42), 0, True)
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


def layout():
    G = grid()
    H = G['H'].astype(np.float64)
    rng = np.random.default_rng(SEED)
    keep = _clear(G)
    walk = G['rim'] < .9
    busy = keep | (G['path_d'] < G['path_half'] + 2.5) | (G['chasm_d'] < plan.CHASM_RIM + 3.0) | (G['cistern'] < 1.1) | (G['riser_d'] < 5.0) | \
        (G['stack'] > .02)
    rows = {}

    def pick(mask, x, y):
        return sample(mask.astype(np.float64), x, y) > .5

    def candidates(cell, x0=-HALF_X + 8, x1=HALF_X - 8, y0=-HALF_Y + 8, y1=HALF_Y - 8):
        xs, ys = np.arange(x0, x1, cell), np.arange(y0, y1, cell)
        gx, gy = np.meshgrid(xs, ys, indexing='ij')
        return (gx + rng.uniform(.1, .9, gx.shape) * cell).ravel(), (gy + rng.uniform(.1, .9, gy.shape) * cell).ravel()

    def put(name, x, y, scale, sink=0.0, yaw=None, lift=0.0, tilt=0.0):
        z = sample(H, x, y) - sink + lift
        out = rows.setdefault(name, [])
        for k in range(len(x)):
            out.append(_row(x[k], y[k], z[k] if np.ndim(z) else z, rng.uniform(0, 360) if yaw is None else yaw[k], rng.uniform(-tilt, tilt),
                            rng.uniform(-tilt, tilt), scale[k]))

    # Crystals: thick in the Garden, along the risers' feet and the Chasm's rims, thin elsewhere.
    x, y = candidates(5.5)
    garden = np.clip(1 - np.hypot(x - plan.GARDEN[0], y - plan.GARDEN[1]) / 120.0, 0, 1)
    edge = np.clip(1 - sample(G['riser_d'], x, y) / 16.0, 0, 1) * .5 + np.clip(1 - (sample(G['chasm_d'], x, y) - plan.CHASM_RIM) / 14.0, 0, 1) * .35
    # Groves: some ninety clumps over the whole city, so no stretch of ground is bare (author, 2026-11-17: the level
    # felt empty). A clump is thick at its middle and thins over 14 m.
    groves = rng.uniform((-HALF_X + 30, -HALF_Y + 30), (HALF_X - 30, HALF_Y - 30), (90, 2))
    near = np.min(np.hypot(x[:, None] - groves[None, :, 0], y[:, None] - groves[None, :, 1]), 1)
    chance = .10 + .75 * garden ** 1.3 + edge * .5 + .7 * np.exp(-(near / 11.0) ** 2)
    ok = pick(walk & ~busy, x, y) & (rng.uniform(0, 1, len(x)) < chance) & (sample(G['slope'], x, y) < .5)
    x, y = x[ok], y[ok]
    kind = rng.choice(3, len(x), p=(.5, .33, .17))
    for k in range(3):
        sel = kind == k
        put('SM_AV_Crystal%d' % k, x[sel], y[sel], rng.uniform(.9, 1.6, sel.sum()) * (1 + 1.1 * np.exp(-(near[ok][sel] / 9.0) ** 2)), sink=.15, tilt=7.0)
    # The great crystals: a ring of landmarks in the Garden, and two sentinels below the First Stair.
    great = [(plan.GARDEN[0] + math.cos(a) * r, plan.GARDEN[1] + math.sin(a) * r) for a, r in
             ((0.3, 46), (1.5, 62), (2.6, 40), (3.7, 66), (4.9, 50), (5.8, 74))] + [(40.0, 60.0), (44.0, -64.0), (-380.0, -150.0)]
    # ... and one standing in the heart of every third grove.
    great += [(gx, gy) for gx, gy in groves[::3] if pick(walk & ~busy, np.array([gx]), np.array([gy]))[0]]
    gx_, gy_ = np.array([p[0] for p in great]), np.array([p[1] for p in great])
    put('SM_AV_CrystalGreat', gx_, gy_, rng.uniform(.8, 1.25, len(great)), sink=.6, tilt=5.0)
    # Fallen and standing columns along the roads: the Processional keeps its avenue, the rest is broken.
    for name, kind, half, points in plan.PATHS:
        if kind != 'road':
            continue
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            length = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / length, (by - ay) / length
            for k in range(int(length // 22.0)):
                for side in (-1, 1):
                    d = 11.0 + k * 22.0
                    x_, y_ = ax + ux * d - uy * side * (half + 3.2), ay + uy * d + ux * side * (half + 3.2)
                    if keep[int(round((x_ + HALF_X) / CELL)), int(round((y_ + HALF_Y) / CELL))] or abs(x_ - plan.chasm_x(y_)) < plan.CHASM_RIM + 4 or \
                            plan.on_riser(x_, y_, 6.0):
                        continue
                    whole = name == 'Processional' or rng.uniform() < .35
                    put('SM_AN_Column' if whole else 'SM_AN_ColumnBroken', np.array([x_]), np.array([y_]), np.array([1.0]), sink=.2,
                        yaw=np.array([math.degrees(math.atan2(uy, ux))]))
                if k % 2 == 0:
                    side = 1 if (k // 2) % 2 else -1
                    d = 22.0 * k + 22.0
                    x_, y_ = ax + ux * d - uy * side * (half + 1.6), ay + uy * d + ux * side * (half + 1.6)
                    if d < length and not keep[int(round((x_ + HALF_X) / CELL)), int(round((y_ + HALF_Y) / CELL))] and \
                            abs(x_ - plan.chasm_x(y_)) > plan.CHASM_RIM + 4 and not plan.on_riser(x_, y_, 6.0):
                        put('SM_AN_Lantern', np.array([x_]), np.array([y_]), np.array([1.0]), sink=.05, yaw=np.array([0.0]))
    # Boulders and stones (scanned), most under the risers and in the open ground.
    x, y = candidates(11.0)
    ok = pick(walk & ~busy, x, y) & (rng.uniform(0, 1, len(x)) < .16 + .3 * np.clip(1 - sample(G['riser_d'], x, y) / 20.0, 0, 1))
    x, y = x[ok], y[ok]
    big = rng.uniform(0, 1, len(x)) < .3
    put('SM_GS_Boulder', x[big], y[big], rng.uniform(.8, 2.2, big.sum()), sink=.35, tilt=10.0)
    put('SM_GS_Stone', x[~big], y[~big], rng.uniform(1.0, 3.0, (~big).sum()), sink=.1, tilt=14.0)
    # Frost grass: thin tufts on the open ground, none on stone.
    x, y = candidates(3.2)
    ok = pick(walk & ~busy, x, y) & (rng.uniform(0, 1, len(x)) < .2 * (.8 + .8 * nz(x, y, SEED + 41, 3, 1 / 45.0))) & (sample(G['slope'], x, y) < .4) & \
        (sample(G['scar'], x, y) < .35)
    put('SM_GV_Grass', x[ok], y[ok], rng.uniform(.7, 1.3, ok.sum()), sink=.02)
    # The risers are the city's own retaining walls: battered panels 12 m wide following each riser's line from rim
    # to rim, stepping aside for the grand stairs (9 m wide on the centre line). Each stands on the lower tier and
    # is stretched to the 12 m rise plus a low parapet.
    for tier_x, level in ((plan.tier2_x, plan.TIER[0]), (plan.tier3_x, plan.TIER[1])):
        for side in (-1.0, 1.0):
            y_ = side * (4.5 + 5.9)
            while abs(y_) < HALF_Y - 20:
                x_ = tier_x(y_) + .1      # its face just in front of the riser's foot, hiding the rock slope behind it
                if plan.rim(x_, y_) < .99:
                    lean = math.degrees(math.atan2(tier_x(y_ + 3.0) - tier_x(y_ - 3.0), 6.0))
                    rows.setdefault('SM_AN_Wall', []).append(_row(x_, y_, level - .5, 180.0 - lean, scale=(1.0, 1.0, 1.42)))
                y_ += side * 11.8
    # The unwoven stones that hang in the air: over every sundered place, and a thin drift over the whole city.
    air = []
    clouds = [(plan.chasm_x(plan.CHASM_CROSS_Y), plan.CHASM_CROSS_Y, 34.0, 70, 2.0, 26.0), (plan.STAIR1[0] - 6, 0.0, 22.0, 46, 8.0, 30.0),
              (plan.STAIR2[0] - 6, 0.0, 22.0, 46, 8.0, 30.0), (plan.COURT[0], plan.COURT[1], 70.0, 150, 14.0, 70.0),
              (plan.GARDEN[0], plan.GARDEN[1], 80.0, 90, 10.0, 46.0), (plan.CISTERN_ISLE[0], plan.CISTERN_ISLE[1] + 22, 26.0, 40, 5.0, 22.0),
              (plan.MESA[0] - 14, plan.MESA[1] - 16, 26.0, 40, 6.0, 34.0)]
    for cx_, cy_, radius, count, low, high in clouds:
        for _ in range(count):
            a, r = rng.uniform(0, math.tau), radius * math.sqrt(rng.uniform())
            x_, y_ = cx_ + math.cos(a) * r, cy_ + math.sin(a) * r
            ground = max(float(height_at(x_, y_)), plan.TIER[0])
            air.append((x_, y_, ground + rng.uniform(low, high)))
    x, y = candidates(34.0)
    ok = pick(walk, x, y)
    for x_, y_ in zip(x[ok], y[ok]):
        air.append((x_, y_, max(float(height_at(x_, y_)), plan.TIER[0]) + rng.uniform(18.0, 60.0)))
    for x_, y_, z_ in air:
        rows.setdefault('Air:SM_AN_Shard%d' % rng.integers(0, 4), []).append(
            _row(x_, y_, z_, rng.uniform(0, 360), rng.uniform(-40, 40), rng.uniform(-40, 40), rng.uniform(.6, 2.4)))
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
    for name in ('LANDING', 'HEARTHOLD', 'FIRST_ARCH', 'SPAN_SOUTH', 'SPAN_NORTH', 'CONCOURSE', 'STAIR1', 'MIDDLE_STILL', 'STAIR2', 'UPPER_STILL',
                 'CISTERN_SHORE', 'GARDEN_STILL', 'GALLERY_STILL', 'COURT', 'GATE', 'LENS', 'OSSUARY'):
        x, y = getattr(plan, name)[:2]
        out('  %-14s (%7.1f, %7.1f) z %6.1f' % (name, x, y, float(height_at(x, y))))
    if rows is not None:
        out('scatter: ' + ', '.join('%s %d' % (k, len(v)) for k, v in rows.items()))


MESHES = [terrain_tile, cistern]
VARIANTS = {terrain_tile: plan.TILES_X * plan.TILES_Y}
_TILE = {'size': (2 * HALF_X / plan.TILES_X, 2 * HALF_Y / plan.TILES_Y, 0), 'tol': .01, 'pivot': 'any'}
CONTRACT = {'SM_AT_Terrain_%d_%d' % (i, j): _TILE for i in range(plan.TILES_X) for j in range(plan.TILES_Y)}
CONTRACT['SM_AT_Cistern'] = {'pivot': 'any'}
