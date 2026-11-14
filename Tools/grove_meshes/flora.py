"""Vegetation of level 4, Earth: the Wounded Grove (the SM_GV_* meshes of Tools/grove/README.md). Pure numpy on kit.py.

The valley's broadleaf trees are one organism at every age (smooth grey bark when young, deeply furrowed when old, the
ovate leaves of the 'LBroadleaf' sheet): SM_GV_Sapling, Birch (a slender young stem turning gold), Beech (a tall
straight one), Oak (an old broad one), and the ancients, SM_GV_GiantTree and SM_GV_Heartwood. The fir on the rim
(SM_GV_Pine) is the one other tree.

How the meshes are made:
  - Wood is geometry: trunks are skinned rings whose radius carries the root flare, the ribs that run up from the
    buttresses, burls, branch collars and (on the ancients) the bark's furrows; limbs are grown order by order (_grow)
    and built as tapering tubes; the finest order are thin solid strands in the LEAF slot, so twigs never collide.
  - Foliage is cards from the scanned leaf sheets (sheets.sprays), their bases on the twigs. A card's vertex colour is
    a TINT on the photo (white: as scanned), darker inside the crown.
  - Bark is painted in the reference colour of the mesh's bark scan (looks.py), so the scan shows as it is; vertex
    colour only shades it (furrows, the ground, the underside of limbs) and stains it. Moss is real faces in the MOSS
    slot, swollen a little out of the bark.
  - Trees keep their trunk on the origin and their lowest point on z 0. North is +x: moss favours that side.
"""
from kit import *
from sheets import CELLS, sprays

unit = fl.unit
NORTH = 0.0                              # the azimuth moss favours (+x is north)
DEADWOOD = tone(BARK_GREY, 1.15)         # bare weathered wood: dead limbs, stubs, breaks
TWIG = tone(BARK_DARK, 1.1)              # the thin solid strands that carry the leaf cards (LEAF slot, untextured)
HEARTROT = tone(BARK_DARK, .55)          # the inside of a hollow or a break
BARK_STAIN = col(BARK_BROWN[0] * .72, BARK_BROWN[1] * 1.02, BARK_BROWN[2] * .55)   # algae on old bark: greener, darker


# ---------------------------------------------------------------- small tools

def MOSS_SLOT(part):
    return part.slots.index(MOSS)


def _smooth(x, lo, hi):
    t = np.clip((np.asarray(x, np.float64) - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _wrap(a):
    """An angle difference folded into -pi..pi."""
    return (np.asarray(a, np.float64) + math.pi) % TAU - math.pi


def _dim(colour, k):
    """colour (one, or one per vertex) times the shading k (one per vertex), as RGBA of at most .9."""
    c = np.asarray(colour, np.float64)
    k = np.asarray(k, np.float64)
    out = np.ones(k.shape + (4,))
    out[..., :3] = np.minimum(c[..., :3] * k[..., None], .9)
    return out


def _lerp(a, b, t):
    """Blend of two colours or colour arrays (..., 4) by t (...)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    t = np.asarray(t, np.float64)[..., None]
    out = a[..., :4] * (1 - t) + b[..., :4] * t
    out[..., 3] = 1.0
    return out


def _ring_noise(x, y, seed, period):
    """toolkit.noise2 that repeats after `period` lattice cells along x: a pattern that meets itself round a trunk."""
    x, y = np.broadcast_arrays(np.asarray(x, np.float64), np.asarray(y, np.float64))
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    period = int(period)

    def h(a, b):
        n = (np.mod(a, period) * 374761393 + b * 668265263 + seed * 2147483647) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
    return (h(xi, yi) * (1 - u) * (1 - v) + h(xi + 1, yi) * u * (1 - v) + h(xi, yi + 1) * (1 - u) * v + h(xi + 1, yi + 1) * u * v) * 2 - 1


def _furrows(th, z, seed, around, tall, width=.5):
    """Furrowed bark round a trunk as a height field, 0 in a furrow to 1 on a ridge's back: the furrows are where a
    noise stretched along the trunk crosses zero, so they run up it, wander and join. around: ridges round the trunk;
    tall: metres a furrow runs before it wanders off."""
    n = _ring_noise(th / TAU * around, z / tall, seed, around) + .5 * _ring_noise(th / TAU * around * 2, z / tall * 1.9 + 7.3, seed + 1, around * 2)
    return _smooth(np.abs(n), 0.0, width)


def _fit(part, size):
    """Scales the part about its bounds' centre to the contract's size on every axis given (0 leaves an axis alone)."""
    v = np.asarray(part.v, np.float64)
    lo, hi = v.min(0), v.max(0)
    k = np.array([s / max(h - l, 1e-9) if s else 1.0 for s, l, h in zip(size, lo, hi)])
    part.v = ((v - (lo + hi) / 2) * k + (lo + hi) / 2).tolist()
    return part


def _skin(part, rings, cols, slot=BARK, smooth=True):
    """Skins a stack of closed rings (each (m, 3), wound counter-clockwise seen from the stack's far end) into one
    surface. A ring may have half the vertices of the one before it (its vertex j over the other's 2j): that band is
    stitched with triangles, so a trunk can be finer at eye level than aloft. cols: one (m, 4) per ring. Returns the
    first vertex and the first face added."""
    v0, f0 = len(part.v), len(part.f)
    start = np.cumsum([0] + [len(r) for r in rings])
    faces = []
    for i in range(len(rings) - 1):
        a, b, m, n = int(start[i]), int(start[i + 1]), len(rings[i]), len(rings[i + 1])
        if m == n:
            j = np.arange(m)
            k = (j + 1) % m
            faces += np.stack([a + j, a + k, b + k, b + j], 1).tolist()
        elif m == 2 * n:
            j = np.arange(n)
            k = (j + 1) % n
            faces += np.stack([a + 2 * j, a + 2 * j + 1, b + j], 1).tolist()
            faces += np.stack([a + 2 * j + 1, b + k, b + j], 1).tolist()
            faces += np.stack([a + 2 * j + 1, a + (2 * j + 2) % m, b + k], 1).tolist()
        else:
            raise ValueError('a ring of %d vertices over one of %d' % (n, m))
    part.add(np.concatenate(rings), faces, np.concatenate(cols), slot, smooth)
    return v0, f0


def _sheet(part, grid, cols, slot=BARK, smooth=True):
    """An open (n, m) grid of vertices as quads, their fronts on the side of (step along m) x (step along n)."""
    v0, f0 = len(part.v), len(part.f)
    n, m = grid.shape[:2]
    i, j = np.meshgrid(np.arange(n - 1), np.arange(m - 1), indexing='ij')
    q = (i * m + j).ravel()
    part.add(grid.reshape(-1, 3), np.stack([q, q + 1, q + m + 1, q + m], 1).tolist(), cols.reshape(-1, 4), slot, smooth)
    return v0, f0


def _moss(part, v0, f0, w, push=None, depth=.03, seed=0, under=None):
    """Lays moss on the len(w) vertices from v0 by weight w (0..1 each): their colour blends to moss, they swell out by
    up to `depth` m along `push` (one direction per vertex), and the faces from f0 on whose corners average over one
    half take the MOSS slot, so the moss is its own surface with a soft stained edge on the bark round it. under: the
    colour the surface below was painted from; the moss keeps that surface's shading (it is as dark in a crevice)."""
    w = np.clip(np.asarray(w, np.float64).ravel(), 0, 1)
    n = len(w)
    v = np.asarray(part.v[v0:v0 + n], np.float64)
    c = np.asarray(part.c[v0:v0 + n], np.float64)
    patch = np.clip(.55 + .45 * noise2(v[:, 0] * 2.3 + v[:, 2] * 1.1, v[:, 1] * 2.3 - v[:, 2] * .7, seed + 41), 0, 1)
    lit = np.clip((c[:, :3] / np.asarray(under, np.float64)[:3]).mean(1), .3, 1.1) if under is not None else np.ones(n)
    green = _dim(MOSS_GREEN, (.52 + .4 * patch) * (.35 + .65 * lit) * (.7 + .3 * _smooth(w, .45, .95)))
    c[:, :3] = c[:, :3] * (1 - w[:, None]) + green[:, :3] * w[:, None]
    part.c[v0:v0 + n] = c.tolist()
    if push is not None:
        part.v[v0:v0 + n] = (v + np.asarray(push, np.float64).reshape(n, 3) * (w * depth)[:, None]).tolist()
    slot = part.slots.index(MOSS)
    for i in range(f0, len(part.f)):
        f = part.f[i]
        if min(f) >= v0 and max(f) < v0 + n and sum(w[q - v0] for q in f) > .5 * len(f):
            part.m[i] = slot


def _spline(pts, radii, m, lead=1.0):
    """m points along the smooth (Catmull-Rom) curve through pts, with the radii carried along; lead over 1 sets them
    closer together toward the start, where a limb's collar is."""
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    u = np.linspace(0, 1, m) ** lead * (n - 1)
    i = np.clip(np.floor(u).astype(int), 0, n - 2)
    f = (u - i)[:, None]
    p0, p1, p2, p3 = pts[np.clip(i - 1, 0, n - 1)], pts[i], pts[i + 1], pts[np.clip(i + 2, 0, n - 1)]
    out = .5 * (2 * p1 + (p2 - p0) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f ** 2 + (3 * p1 - p0 - 3 * p2 + p3) * f ** 3)
    return out, np.interp(u, np.arange(n), np.asarray(radii, np.float64))


def _limb(part, pts, radii, sides, colour, seed=0, slot=BARK, under=.3, cap=True, collar=0.0, streak=.14, shade=1.0, ground=0.0):
    """A limb in bark: a tube (fl.limb) shaded under its belly, streaked along its run, and darker toward the ground
    within `ground` m of it. collar swells its foot into a branch collar. Returns its first vertex and face, each
    vertex's unit offset from the limb's axis and the ring it belongs to."""
    pts = np.asarray(pts, np.float64)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (len(pts),)).copy()
    if collar:
        arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
        radii = radii * (1 + collar * np.exp(-arc / max(1.5 * radii[0], 1e-6)))
    f0 = len(part.f)
    v0 = fl.limb(part, pts, radii, colour, slot, sides, cap=cap)
    n, sides = len(pts), fl.sides_of(sides)
    v = np.asarray(part.v[v0:], np.float64)
    ring = np.r_[np.repeat(np.arange(n), sides), np.zeros(sides, int), np.full(sides, n - 1)][:len(v)]
    column = np.arange(len(v)) % sides
    off = v - pts[ring]
    r = np.maximum(radii[ring], 1e-6)
    k = shade * (1 - under * np.clip(-off[:, 2] / r, 0, 1)) * (1 - streak / 2 + streak * noise2(column * 1.7 + seed * .37, ring * .45 + seed * .11, seed + 7))
    if ground:
        k = k * (.7 + .3 * np.clip(v[:, 2] / ground, 0, 1))
    part.c[v0:] = _dim(colour, k).tolist()
    return v0, f0, off / r[:, None], ring


def _strands(part, a, b, ra, rb, colours, slot=LEAF, sides=3):
    """Thin straight sticks from a to b (one per row), built in one go: the finest twigs, which sway with the leaves
    and never collide."""
    a, b = np.atleast_2d(np.asarray(a, np.float64)), np.atleast_2d(np.asarray(b, np.float64))
    n = len(a)
    d = unit(b - a)
    ref = np.where((np.abs(d[:, 2]) < .95)[:, None], UP, np.array([1.0, 0.0, 0.0]))
    u = unit(np.cross(ref, d))
    w = np.cross(d, u)
    ang = np.arange(sides) / sides * TAU
    ring = np.cos(ang)[None, :, None] * u[:, None, :] + np.sin(ang)[None, :, None] * w[:, None, :]
    lo = a[:, None, :] + ring * np.broadcast_to(np.asarray(ra, np.float64), (n,))[:, None, None]
    hi = b[:, None, :] + ring * np.broadcast_to(np.asarray(rb, np.float64), (n,))[:, None, None]
    o = (np.arange(n) * 2 * sides)[:, None]
    j = np.arange(sides)[None, :]
    k = (j + 1) % sides
    faces = np.stack([o + j, o + k, o + sides + k, o + sides + j], -1).reshape(-1, 4).tolist()
    cols = np.asarray(colours, np.float64)
    if cols.ndim == 2:
        cols = np.repeat(cols, 2 * sides, 0)
    return part.add(np.concatenate([lo, hi], 1).reshape(-1, 3), faces, cols, slot, True)


def _break(part, rng, centre, direction, radius, colour, sides=10, slot=BARK, depth=1.0):
    """The torn end of a snapped limb or stem at `centre`, facing `direction`: a ragged rim of standing splinters
    round a dark, rotten heart."""
    centre, d = np.asarray(centre, np.float64), unit(direction)
    a, b = frame(d)
    ang = np.arange(sides) / sides * TAU
    ring = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
    jag = rng.uniform(.15, 1.0, sides) ** 2 * depth * radius * 1.7
    rim = centre + ring * radius
    crest = centre + ring * radius * rng.uniform(.6, .9, (sides, 1)) + d * jag[:, None]
    pit = centre + ring * radius * .3 + d * radius * .08
    verts = np.concatenate([rim, crest, pit, [centre - d * radius * .4]])
    faces = []
    for j in range(sides):
        k = (j + 1) % sides
        faces += [[j, k, sides + k, sides + j], [sides + j, sides + k, 2 * sides + k, 2 * sides + j], [2 * sides + j, 2 * sides + k, 3 * sides]]
    cols = np.concatenate([_dim(colour, np.full(sides, .9)), _dim(DEADWOOD, rng.uniform(.9, 1.25, sides)),
                           _dim(HEARTROT, np.full(sides, 1.3)), _dim(HEARTROT, np.ones(1))])
    return part.add(verts, faces, cols, slot, False)


# ---------------------------------------------------------------- growing wood

def _at(cfg, key, depth, default=0.0):
    v = cfg.get(key, default)
    return v[min(depth, len(v) - 1)] if isinstance(v, list) else v


def _grow(rng, start, direction, length, radius, cfg, depth=0, out=None):
    """Grows a branch and, order by order, its children (fl.grow's scheme, with an old tree's habits). cfg holds one
    value per order (a list) or one for all:
      segs      points along a branch                 up      how far it turns toward the light
      wiggle    its random lean                       kink    sideways wander, as a fraction of its length (elbows)
      sag       how far its end hangs, per length     taper   its end radius over its foot radius
      children  how many it carries                   t0      where along it they start
      spread    their angle off it (radians, a range) ratio   their length over its own (a range)
      child_r   their radius over its radius there    lift    how far they lean up
      fall      how much longer the lowest child is than the highest (0: all alike)
      splay     how much wider the lowest child stands off it than the highest
    Returns {'wood': [(points, radii, order)], 'tips': [(point, direction, order)]}."""
    if out is None:
        out = {'wood': [], 'tips': [], 'phase': rng.uniform(0, TAU)}
    start = np.asarray(start, np.float64)
    d = unit(direction)
    n = _at(cfg, 'segs', depth)
    wiggle = _at(cfg, 'wiggle', depth)
    bend = unit(d + UP * _at(cfg, 'up', depth) + rng.normal(0, wiggle, 3))
    end = start + bend * length
    pts = bezier(start, start + d * length * .38, end - bend * length * .33 + rng.normal(0, wiggle * length * .2, 3), end, n)
    t = np.linspace(0, 1, n)
    kink = _at(cfg, 'kink', depth)
    if kink:
        a, b = frame(bend)
        for axis, f in ((a, rng.uniform(1.0, 1.8)), (b, rng.uniform(1.5, 2.6))):
            ph = rng.uniform(0, TAU)
            pts = pts + axis * ((np.sin(t * math.pi * f + ph) - math.sin(ph)) * kink * length * .5)[:, None]
    sag = _at(cfg, 'sag', depth)
    if sag:
        pts[:, 2] -= sag * length * t ** 2
    r = radius * (1 - (1 - _at(cfg, 'taper', depth, .4)) * t ** _at(cfg, 'taper_power', depth, 1.0))
    out['wood'].append((pts, r, depth))
    count = _at(cfg, 'children', depth, 0) if depth + 1 < len(cfg['segs']) else 0
    if count:
        t0, fall = _at(cfg, 't0', depth, .3), _at(cfg, 'fall', depth, 0.0)
        for i in range(count):
            pos = (i + rng.uniform(.15, .85)) / count
            f = (t0 + (1 - t0) * pos) * (n - 1)
            i0 = min(int(f), n - 2)
            w = f - i0
            p0 = pts[i0] * (1 - w) + pts[i0 + 1] * w
            tang = unit(pts[i0 + 1] - pts[i0])
            a, b = frame(tang)
            az = out['phase'] + i * 2.39996 + rng.uniform(-.35, .35)
            ang = rng.uniform(*_at(cfg, 'spread', depth)) * (1 + _at(cfg, 'splay', depth) * (.5 - pos))
            cd = unit(math.cos(ang) * tang + math.sin(ang) * (math.cos(az) * a + math.sin(az) * b) + UP * _at(cfg, 'lift', depth))
            rr = (r[i0] * (1 - w) + r[i0 + 1] * w) * _at(cfg, 'child_r', depth, .6)
            _grow(rng, p0, cd, length * rng.uniform(*_at(cfg, 'ratio', depth)) * (1 + fall * (.5 - pos)), rr, cfg, depth + 1, out)
        out['phase'] += 1.3
    out['tips'].append((pts[-1], unit(pts[-1] - pts[-2]), depth))
    return out


def _twigs(wood, orders, tip=1.0):
    """The straight pieces of the branches of the given orders, as (starts, ends, weights): where leaf cards may sit.
    A piece weighs its length, and more toward its branch's tip (tip: how much more at the very end)."""
    a, b, w = [], [], []
    for pts, _, depth in wood:
        if depth in orders:
            pts = np.asarray(pts, np.float64)
            n = len(pts) - 1
            a.append(pts[:-1])
            b.append(pts[1:])
            w.append(np.linalg.norm(np.diff(pts, axis=0), axis=1) * (1 + tip * (np.arange(n) + .5) / n))
    return np.concatenate(a), np.concatenate(b), np.concatenate(w)


# What a far version keeps (the SpeedTree way: fewer, larger cards). Per level of detail 0..3: one card in CARD_STEP is
# kept, CARD_SIZE times as long (level 3 instead spreads CARD_FAR cards through the crown at that size), so the crown
# keeps its volume, density and colour while its triangles fall.
CARD_STEP = (1, 2, 6, 0)
CARD_SIZE = (1.0, 1.35, 2.2, 3.75)


def _lod_name(name, lod):
    return name + ('_LOD%d' % lod if lod else '')


def _leaf_set(rng, twigs, crown, count, length, tint=(.92, .95, .88), cloud=0.0, flat=.5, droop=.1, facing_up=.55, tip=.8, inner=.5,
              keep=None, gold=None):
    """count leaf cards for a crown, as arrays: their bases on the twigs (starts, ends, weights) or, with cloud, within
    that many metres of them (the twiglets a card stands for), each growing on along its twig, sideways and outward, its
    face to the light. tint is the photo's tint in full light; cards deeper in the crown (centre, radii) darken to
    `inner`. gold: (tint, share) turns that share of the cards. keep: a test (points -> bools) every card's base and
    tip must pass. Returns {'base', 'grow', 'face', 'size', 'tint', 'crown'}: _lay() lays them at a level of detail."""
    a, b, w = twigs
    pick = rng.choice(len(a), count, p=w / w.sum())
    along = unit(b - a)[pick]
    base = a[pick] + (b - a)[pick] * (rng.uniform(0, 1, count) ** tip)[:, None]
    centre, radii = np.asarray(crown[0], np.float64), np.asarray(crown[1], np.float64)
    off = rng.normal(0, 1, (count, 3))
    off = unit(off - along * np.sum(off * along, 1, keepdims=True))
    if cloud:
        base = base + off * (cloud * np.sqrt(rng.uniform(0, 1, count)))[:, None]
    out = unit((base - centre) / radii)
    side = unit(np.cross(along, UP) + 1e-9) * rng.choice((-1.0, 1.0), count)[:, None]
    grow = unit(along * .5 + side * flat * rng.uniform(.4, 1.0, (count, 1)) + off * (.6 if cloud else .25) + out * .25 +
                UP * (.1 - droop) + rng.normal(0, .15, (count, 3)))
    face = unit(UP * facing_up + out * (1 - facing_up) + rng.normal(0, .25, (count, 3)))
    size = rng.uniform(length[0], length[1], count)
    depth = np.linalg.norm((base - centre) / radii, axis=1)
    k = (inner + (1 - inner) * np.clip(depth, 0, 1) ** 1.5) * (.9 + .1 * out[:, 2]) * rng.uniform(.86, 1.06, count)
    cols = k[:, None] * np.asarray(tint, np.float64)[None, :3]
    if gold is not None:
        turned = rng.uniform(0, 1, count) < gold[1]
        cols[turned] = k[turned, None] * np.asarray(gold[0], np.float64)[None, :3] * rng.uniform(.85, 1.1, (int(turned.sum()), 1))
    if keep is not None:
        ok = keep(base) & keep(base + grow * size[:, None])
        base, grow, face, size, cols = base[ok], grow[ok], face[ok], size[ok], cols[ok]
    return {'base': base, 'grow': grow, 'face': face, 'size': size, 'tint': cols, 'crown': (centre, radii)}


def _spread(points, count):
    """count of the points, chosen far from each other (farthest-point sampling): an even cover of a crown."""
    points = np.asarray(points, np.float64)
    chosen = [int(np.argmax(points[:, 2]))]
    far = np.linalg.norm(points - points[chosen[0]], axis=1)
    for _ in range(min(count, len(points)) - 1):
        chosen.append(int(np.argmax(far)))
        far = np.minimum(far, np.linalg.norm(points - points[chosen[-1]], axis=1))
    return np.array(chosen)


def _lay(part, sheet, leaf, lod=0, cells=('twig',), bend=.12, seed=0, far=300):
    """Lays a leaf set (_leaf_set) as cards of a scanned sheet at a level of detail: all of them, or one in CARD_STEP at
    CARD_SIZE times the length (each grown about its own middle, so the crown's bounds hold), or at level 3 `far` of
    them, spread evenly, at 3.75 times. Every card takes the whole crown's normals. Returns the cards laid."""
    n = len(leaf['base'])
    if not n:
        return 0
    pick = np.arange(0, n, CARD_STEP[lod]) if CARD_STEP[lod] else _spread(leaf['base'] + leaf['grow'] * leaf['size'][:, None] * .5, far)
    size = leaf['size'][pick] * CARD_SIZE[lod]
    if 'cap' in leaf:        # where the crown is narrow (a fir's top) a far card may not outgrow it
        size = np.maximum(np.minimum(size, leaf['cap'][pick]), leaf['size'][pick])
    grow = leaf['grow'][pick]
    base = leaf['base'][pick] - grow * ((size - leaf['size'][pick]) * .5)[:, None]
    if lod:                  # a larger card that would stand out of the full crown's box is slid back into it: the bounds hold
        ends = np.concatenate([leaf['base'], leaf['base'] + leaf['grow'] * leaf['size'][:, None]])
        lo, hi = ends.min(0), ends.max(0)
        tip = base + grow * size[:, None]
        wide = max((c[2] - c[0]) / (c[3] - c[1]) if c[4] in ('bottom', 'top') else (c[3] - c[1]) / (c[2] - c[0]) for c in (CELLS[sheet][n_] for n_ in cells))
        pad = ((size - leaf['size'][pick]) * wide * .4)[:, None]         # and so does its greater width
        base = base - np.maximum(np.maximum(base, tip) + pad - hi, 0) - np.minimum(np.minimum(base, tip) - pad - lo, 0)
    sprays(part, sheet, base, grow, leaf['face'][pick], size, leaf['tint'][pick], cells=cells, rng=np.random.default_rng(seed + 977),
           crown=leaf['crown'], bend=bend)
    return len(pick)


# ---------------------------------------------------------------- the ancients' trunks and roots

def _bole(part, zs, counts, radius, axis, ribs, bumps, bark, colour, seed=0, ground=3.0, moss=None, moss_depth=.05):
    """A great trunk: rings at heights zs of counts vertices each (a count may halve from one ring to the next), round
    the axis(z) -> (x, y), of mean radius radius(z), carrying
      ribs   (azimuth, amp(z), width(z), twist): swellings that run up the trunk (the buttresses' roots, old fused stems)
      bumps  (azimuth, z, amp, width in azimuth, width in z): burls, branch collars, hollows (negative)
      bark   {'field': f(azimuths, z) -> 0 in a furrow .. 1 on a ridge, 'depth': f(z) -> the furrows' depth in metres}
    all as geometry. Vertex colour shades the furrows, the bays between the ribs, the hollows and the foot.
    moss: f(azimuths, z, ridge, rib) -> weights. Returns {'z', 'r' (one array of radii per ring), 'axis'}."""
    rings, cols, weights, push, radii = [], [], [], [], []
    for z, m in zip(zs, counts):
        th = np.arange(m) / m * TAU
        rib = np.zeros(m)
        for az, amp, width, twist in ribs:
            a_ = amp(z)
            if a_:
                rib += a_ * np.exp(-(_wrap(th - az - twist * z) / width(z)) ** 2)
        lump = np.zeros(m)
        for az, z0, amp, w_az, w_z in bumps:
            dz = (z - z0) / w_z
            if abs(dz) < 3:
                lump += amp * math.exp(-dz * dz) * np.exp(-(_wrap(th - az) / w_az) ** 2)
        f = bark['field'](th, z)
        r = radius(z) + rib - rib.mean() + lump + bark['depth'](z) * (f - .65)
        c = axis(z)
        out = np.stack([np.cos(th), np.sin(th), np.zeros(m)], 1)
        rings.append(np.array([c[0], c[1], z]) + out * r[:, None])
        radii.append(r)
        ridge = (rib - rib.min()) / max(rib.max() - rib.min(), 1e-6)          # 0 in the bays between the ribs, 1 on a rib
        low = 1 - float(_smooth(z, 0, ground * 2))
        k = (.7 + .3 * float(_smooth(z, 0, ground))) * (.66 + .38 * f) * (1 - .22 * low * (1 - ridge))
        k = k * (.93 + .1 * noise2(th * 7 + seed, z * .3 + np.zeros(m), seed + 7)) * (1 - .5 * _smooth(-lump, .25, 1.2))
        cols.append(_dim(colour, k))
        if moss is not None:
            weights.append(moss(th, z, f, ridge))
            push.append(out)
    v0, f0 = _skin(part, rings, cols)
    if moss is not None:
        _moss(part, v0, f0, np.concatenate(weights), np.concatenate(push), moss_depth, seed, colour)
    return {'z': np.asarray(zs, np.float64), 'r': radii, 'axis': axis}


def _bole_radius(bole, az, z):
    """The trunk's radius at an azimuth and height (the nearest ring's)."""
    i = int(np.argmin(np.abs(bole['z'] - z)))
    r = bole['r'][i]
    return float(r[int(round(az / TAU * len(r))) % len(r)])


# The section of a buttress wall: heights up one face as a fraction of the crest's (the crest itself, 1, is shared),
# for each level of detail.
_WALL_Q = (np.array([0, .02, .05, .09, .14, .2, .27, .35, .44, .54, .64, .74, .83, .9, .95, .985]),
           np.array([0, .04, .1, .2, .35, .54, .74, .9, .97]), np.array([0, .08, .3, .62, .9]), np.array([0, .3, .8]))


def _wall(part, az, r_trunk, r_out, high, colour, seed=0, foot=1.15, mid=.42, top=.17, sway=.1, stations=40, power=1.8, tail=.12,
          fold=.15, wave=2.3, furrow=.14, grain=.55, moss=.5, inset=1.5, climb=3.0, lod=0):
    """A buttress root: a wall standing on z 0 that leaves the trunk `high` m up it (where the trunk's surface is at
    r_trunk; the wall starts `inset` m inside that, its crest still climbing by `climb` m per metre, so it merges as a
    flange) and runs out to r_out, where it is a low root diving into the ground. Its crest falls in a concave sweep
    (power) to a long tail; its line wanders by `sway` radians; the plank itself waves (fold, every `wave` m), folds
    run down its faces and its bark is furrowed along its run (furrow m deep, ridges every `grain` m of height). foot,
    mid and top are its half thicknesses. It darkens toward the trunk and the ground; moss lies on its crest and its
    north face. lod thins its stations and its section. Returns its line on the ground (stations, 2) and its crest
    heights."""
    rng = np.random.default_rng(seed + 9000)     # its own draws: a far version that leaves a wall out grows the same tree
    b, ph = rng.uniform(-1, 1), rng.uniform(0, TAU)
    stations = max(6, int(round(stations * (1.0, .55, .3, .2)[lod])))
    s = np.linspace(0, 1, stations) ** 1.1
    rho = r_trunk - inset + (r_out - r_trunk + inset) * s
    dev = sway * (b * s ** 2 + (1 - abs(b)) * .7 * np.sin(2.4 * math.pi * s + ph) * s)
    line = rho[:, None] * np.stack([np.cos(az + dev), np.sin(az + dev)], 1)
    tang = unit(np.gradient(line, axis=0))
    lat = np.stack([tang[:, 1], -tang[:, 0]], 1)                      # the wall's right-hand side: tangent x up
    u = np.clip((rho - r_trunk) / (r_out - r_trunk), 0, 1)            # 0 where it leaves the trunk, 1 at the root's end
    crest = high * (1 - u) ** power * (1 - tail) + high * tail * (1 - u) ** .6 + .12 + np.clip(r_trunk - rho, 0, None) * climb
    crest = crest * (1 + .07 * np.sin(s * 11 + ph)) * (1 + .05 * np.sin(s * 23 + 2 * ph)) * (1 + .1 * noise2(rho * .9, rho * 0 + seed, seed + 2))
    side = _WALL_Q[lod]
    q = np.r_[side, 1.0, side[::-1]]
    sign = np.r_[-np.ones(len(side)), 0.0, np.ones(len(side))]
    thin = s ** .8
    join = 1 + 1.4 * np.exp(-u * 7.0)                                  # the wall flows out of the trunk: thick where they join
    t_foot, t_mid, t_top = foot * (1 - .62 * thin) * (1 + .3 * (join - 1)), mid * (1 - .55 * thin) * join, top * (1 - .4 * thin) * join
    half = t_top[:, None] + (t_mid - t_top)[:, None] * (1 - q[None, :]) ** .8 + (t_foot - t_mid)[:, None] * (1 - q[None, :]) ** 5
    half = half * np.sqrt(np.clip(1 - np.clip((q - .9) / .1, 0, 1) ** 2, 0, 1))[None, :]
    Z = q[None, :] * crest[:, None]
    # the plank waves as a whole; folds run down each face from the crest; the bark is furrowed along its run
    wob = fold * np.sin(TAU * rho[:, None] / wave + ph + 1.6 * q[None, :]) * (.35 + .65 * np.sin(math.pi * q[None, :] ** .7)) * (1 - .6 * s[:, None])
    drape = fold * .9 * noise2(rho[:, None] / wave * 2.3 + sign[None, :] * 31.7 + q[None, :] * .8, q[None, :] * 1.3 + seed, seed + 5) * np.abs(sign)[None, :] * (1 - .5 * s[:, None])
    n = noise2(rho[:, None] * .45 + sign[None, :] * 17.3, q[None, :] * high / grain + seed * .7, seed + 3) + \
        .5 * noise2(rho[:, None] * .9 + sign[None, :] * 9.1, q[None, :] * high / grain * 1.9 + 3.3, seed + 4)
    ridge = _smooth(np.abs(n), 0.0, .5)
    L = sign[None, :] * (half + drape + (furrow if lod < 2 else 0.0) * (ridge - .65) * np.abs(sign)[None, :] * (1 - .5 * s[:, None])) + wob
    grid = np.concatenate([line[:, None, :] + lat[:, None, :] * L[..., None], Z[..., None]], -1)
    near = _smooth(rho, r_trunk, r_trunk + 3.0)[:, None]
    k = (.7 + .3 * _smooth(Z, 0, 3.0)) * (.66 + .38 * ridge) * (.78 + .22 * near) * (1 + .08 * _smooth(q, .8, 1.0))[None, :]
    k = k * (.93 + .1 * noise2(rho[:, None] * 1.3, Z * 1.1 + sign[None, :] * 5, seed + 7))
    v0, f0 = _sheet(part, grid, _dim(colour, k))
    tip = grid[-1]                                                     # the root's end: closed with a fan
    part.add(np.concatenate([tip, [tip.mean(0) + np.r_[tang[-1] * .25, -.05]]]),
             [[j, j + 1, len(tip)] for j in range(len(tip) - 1)], _dim(colour, np.full(len(tip) + 1, .7)), BARK, True)
    if moss:
        normal = np.concatenate([lat[:, None, :] * sign[None, :, None], np.zeros((stations, len(q), 1))], -1)
        north = normal[..., 0] * math.cos(NORTH) + normal[..., 1] * math.sin(NORTH)
        patch = noise2(rho[:, None] * .5 + seed, q[None, :] * 2.2 + sign[None, :] * 3, seed + 11)
        on_crest = _smooth(q, .6, .93)[None, :] * _smooth(patch, -.15, .4)
        on_face = _smooth(north, .15, .7) * _smooth(q, .03, .3)[None, :] * _smooth(patch, .1, .6)
        w = np.clip(np.maximum(on_crest, on_face) * (.8 + .6 * moss), 0, 1) * _smooth(crest, .25, .9)[:, None]
        push = normal + np.r_[0, 0, .6] * _smooth(q, .6, 1.0)[None, :, None]
        _moss(part, v0, f0, w, unit(push + 1e-9), .06 if lod < 2 else 0.0, seed, colour)
    return line, crest


def _root(part, start, heading, length, radius, colour, seed=0, limit=None, wander=.6, sides=7, rings=20, forks=1):
    """A surface root: it leaves `start` (x, y, z) heading `heading` radians and runs along the ground, half sunk in it,
    snaking, swelling and thinning, ducking under and coming up again, and dives at its end; it may fork. limit: the
    farthest from the axis it may reach (it turns along that circle instead of crossing it). Its line comes from its
    seed alone, so a far version with fewer rings, sides and forks keeps the same root."""
    rng = np.random.default_rng(seed + 7000)
    points = 11
    xy = [np.asarray(start[:2], np.float64)]
    h, turn, step = heading, rng.uniform(-wander, wander), length / (points - 1)
    heads = [h]
    for _ in range(1, points):
        h += turn * .2 + rng.normal(0, wander * .32)
        q = xy[-1] + step * np.array([math.cos(h), math.sin(h)])
        if limit is not None and np.hypot(*q) > limit:
            q = q / np.hypot(*q) * limit
            h = math.atan2(q[1], q[0]) + math.copysign(math.pi / 2, turn)
        xy.append(q)
        heads.append(h)
    t = np.linspace(0, 1, points)
    r = radius * (.12 + .88 * (1 - t) ** .8) * (1 + .22 * np.sin(t * rng.uniform(9, 15) + rng.uniform(0, TAU)) * t)
    z = start[2] * (1 - t) ** 3 + r * (.2 + .55 * np.sin(t * rng.uniform(6, 11) + rng.uniform(0, TAU)) * np.minimum(t * 3, 1) - 1.3 * t ** 3)
    P, R = _spline(np.c_[np.array(xy), z], r, rings)
    _limb(part, P, R, sides, colour, seed, under=.15, ground=max(.6, radius * 2))
    for k in range(forks):
        j = int(rng.uniform(.3, .65) * (points - 1))
        side, turn_, share = rng.choice((-1, 1)), rng.uniform(.5, 1.1), rng.uniform(.35, .6)
        if r[j] > .08:
            _root(part, (xy[j][0], xy[j][1], z[j]), heads[j] + side * turn_, length * share * (1 - t[j]) + 4 * radius, r[j] * .7, colour,
                  seed + 17 + k, limit, wander, max(4, sides - 2), max(6, rings * 2 // 3), 0)


# ---------------------------------------------------------------- the Heartwood

def heartwood(lod=0):
    """SM_GV_Heartwood, 88 m: the oldest stem of the grove. A bole 8.5 m in radius at z 3 and 5 m at z 40, ribbed, folded
    and furrowed, a hollow at its north foot; nine buttress roots like walls, flanges that climb the bole and reach 17 m
    from the axis (nothing beyond 17.5 m below z 6), lesser ones in four bays, the widest bay facing north (+x); roots
    snaking over the ground between and beyond them. Great limbs from z 38 in four tiers, the lowest reaching 30 m out,
    and a crown 37 m in radius. It is wounded: one limb of the lowest tier (west, -y), one of the second (east, +y) and
    the leader are dead and bare, the leader standing out of the crown's top as a stag's head.
    lod 1 and 2 are its far versions (SM_GV_Heartwood_LOD1, _LOD2): the same tree with simpler wood and fewer, larger
    leaf cards."""
    rng = np.random.default_rng(4401)            # the tree's shape: the same draws at every level of detail
    fine = np.random.default_rng(4402)           # what a far version may leave out
    p = Part(_lod_name('SM_GV_Heartwood', lod), (BARK, LEAF, MOSS))
    bark = BARK_BROWN
    RZ = np.array([0, 1, 3, 6, 10, 16, 24, 32, 40, 46, 52, 58, 63.0])
    RR = np.array([9.7, 9.1, 8.5, 8.0, 7.5, 6.9, 6.2, 5.6, 5.0, 4.6, 4.1, 3.5, 3.0])

    def radius(z):
        return float(np.interp(z, RZ, RR))

    def axis(z):
        lean = float(_smooth(z, 6, 64)) ** 1.2
        wave = .35 * math.sin(z * .09) * float(_smooth(z, 6, 20))
        return np.array([.9 * lean + wave, -.5 * lean + .6 * wave])
    # --- the buttresses: azimuth (degrees from +x toward +y), reach, height where they leave the bole
    WALLS = ((28, 17.0, 11.5), (68, 14.6, 8.8), (105, 16.8, 12.8), (148, 13.4, 7.4), (186, 17.0, 10.8), (222, 15.6, 9.5),
             (262, 12.6, 6.8), (300, 17.0, 12.2), (332, 16.2, 10.1))
    MINOR = ((47, 12.6, 3.4), (128, 12.0, 2.8), (203, 13.0, 3.8), (282, 11.8, 2.6))      # lesser buttresses, in every other bay
    # --- the great limbs: height, azimuth, elevation (degrees), length, radius at the foot, dead
    LIMBS = ((38.5, 12, 9, 29, 2.1, 0), (40.0, 76, 13, 28, 2.0, 0), (39.2, 138, 8, 30, 2.15, 0), (41.0, 204, 12, 28, 1.95, 0),
             (38.8, 263, 10, 27, 2.05, 1), (40.6, 322, 14, 28, 1.95, 0),
             (45.5, 44, 28, 25, 1.75, 0), (47.0, 108, 32, 22, 1.7, 1), (46.2, 170, 26, 26, 1.8, 0), (48.0, 232, 33, 24, 1.65, 0),
             (45.8, 292, 29, 25, 1.75, 0), (47.4, 350, 31, 24, 1.7, 0),
             (52.0, 20, 44, 22, 1.5, 0), (53.5, 92, 48, 21, 1.45, 0), (52.6, 160, 43, 22, 1.55, 0), (54.2, 236, 50, 21, 1.4, 0),
             (53.0, 305, 46, 22, 1.5, 0),
             (58.5, 60, 70, 20, 1.55, 0), (59.5, 150, 74, 21, 1.6, 0), (59.0, 245, 68, 20, 1.5, 0), (60.5, 330, 80, 27.5, 1.45, 1))
    ribs = []
    for deg, _, hk in WALLS:     # each wall runs on up the bole as a rib
        ribs.append((math.radians(deg),
                     lambda z, hk=hk: 1.7 * (1 - .35 * z / hk) if z <= hk else 1.1 * math.exp(-(z - hk) / 16.0),
                     lambda z, hk=hk: .13 + .08 * float(_smooth(z, 0, hk * 1.3)) + .12 * float(_smooth(z, hk, 46)),
                     rng.uniform(-.0025, .0025)))
    for deg, _, hk in MINOR:
        ribs.append((math.radians(deg), lambda z, hk=hk: .8 * math.exp(-(z / (hk * 1.6)) ** 2), lambda z: .1, rng.uniform(-.003, .003)))
    for _ in range(26):          # the bole's own folds: old stems fused, leaning a little with the grain
        zc, zs_, amp, wide = rng.uniform(2, 52), rng.uniform(8, 20), rng.uniform(.25, .65) * rng.choice((-1, 1)), rng.uniform(.05, .11)
        ribs.append((rng.uniform(0, TAU), lambda z, zc=zc, zs_=zs_, amp=amp: amp * math.exp(-((z - zc) / zs_) ** 2),
                     lambda z, wide=wide: wide, rng.uniform(-.006, .006)))
    bumps = [(rng.uniform(0, TAU), rng.uniform(1.5, 34), rng.uniform(.3, .7), rng.uniform(.07, .14), rng.uniform(1.0, 2.2)) for _ in range(8)]
    bumps.append((NORTH, 2.4, -1.5, .12, 2.6))                        # the hollow at the north foot
    for z, deg, _, _, r, _ in LIMBS:                                  # a shoulder under every great limb
        bumps.append((math.radians(deg), z - .7 * r, .5 * r, 1.25 * r / radius(z), 1.5 * r))

    def field(th, z):
        th = th + .004 * z
        f = _furrows(th, z, 4411, 56, 4.5)
        if z > 36:
            f = f + (_furrows(th, z, 4412, 28, 5.0) - f) * float(_smooth(z, 36, 41))
        if z > 50:
            f = f + (_furrows(th, z, 4413, 14, 6.0) - f) * float(_smooth(z, 50, 54))
        return f

    def moss_on(th, z, f, ridge):
        north = .5 + .5 * np.cos(th - NORTH)
        patch = _ring_noise(th / TAU * 14, z / 3.5, 4421, 14)
        speck = _ring_noise(th / TAU * 40, z / 1.3 + 5.0, 4422, 40)
        return _smooth(north ** 1.5 * (1 - float(_smooth(z, 2, 24))) * .6 + .5 * patch + .2 * speck - .2 * (1 - f), .6, .9)
    zs = [0, .3, .65, 1.05, 1.5, 2.0, 2.55, 3.15, 3.8, 4.5, 5.3, 6.2, 7.2, 8.3, 9.5, 10.8, 12.2, 13.8, 15.6, 17.6, 19.8, 22.2, 24.8, 27.6,
          30.6, 33.8, 37.0, 40.0, 42.5, 45.0, 47.5, 50.0, 52.5, 55.0, 57.5, 60.0, 62.0][::(1, 2, 4)[lod]]
    most = (256, 128, 32)[lod]
    counts = [most if z <= 40 else most // 2 if z <= 53 or lod == 2 else most // 4 for z in zs]
    deep = (1.0, .6, 0.0)[lod]
    bole = _bole(p, zs, counts, radius, axis, ribs, bumps,
                 {'field': field, 'depth': lambda z: deep * float(np.interp(z, [0, 10, 40, 60], [.42, .42, .3, .14]))}, bark, 4401, 3.5, moss_on,
                 .07 if lod < 2 else 0.0)
    top, m = axis(zs[-1]), counts[-1]
    start = len(p.v) - m
    p.add([[top[0], top[1], zs[-1] + .9]], [], _dim(bark, np.ones(1)), BARK)
    for j in range(m):
        p.f.append([start + j, start + (j + 1) % m, len(p.v) - 1])
        p.m.append(0)
        p.s.append(True)
    # --- the buttress walls, and the roots that run on from them and between them
    lines = []
    for i, (deg, reach, high) in enumerate(WALLS):
        az = math.radians(deg)
        lines.append(_wall(p, az, _bole_radius(bole, az, high) - .2, reach, high, bark, 4430 + i, foot=rng.uniform(1.0, 1.25),
                           sway=rng.uniform(.07, .12), moss=.5 + .4 * (.5 + .5 * math.cos(az - NORTH)), lod=lod)[0])
    for i, (deg, reach, high) in enumerate(MINOR):
        az = math.radians(deg)
        if lod < 2:
            lines.append(_wall(p, az, _bole_radius(bole, az, high) - .2, reach, high, bark, 4470 + i, foot=.75, mid=.3, top=.13, sway=.14,
                               stations=28, moss=.5 + .4 * (.5 + .5 * math.cos(az - NORTH)), lod=lod)[0])
    if lod < 2:
        forks, sides, rings = (1, 7, 22) if lod == 0 else (0, 5, 10)
        for i, line in enumerate(lines):     # toes: roots leaving the walls' feet at an angle
            for k in range(2 if i < len(WALLS) else 1):
                j = int(fine.uniform(.55, .85) * (len(line) - 1))
                r = fine.uniform(.3, .5)
                heading = math.atan2(line[j][1], line[j][0]) + (1 if k else -1) * fine.uniform(.5, 1.0)
                _root(p, (line[j][0], line[j][1], r * .4), heading, fine.uniform(3.5, 6.5), r, bark, 4450 + 2 * i + k, 17.1, sides=sides, rings=rings, forks=forks)
        walls = np.radians([w[0] for w in WALLS])
        lesser = np.radians([w[0] for w in MINOR])
        for i in range(len(walls)):          # the bays without a lesser buttress (the north bay too): roots from the bole's foot
            a0, a1 = walls[i], walls[(i + 1) % len(walls)] + (TAU if i == len(walls) - 1 else 0)
            if np.any((lesser > a0) & (lesser < a1)):
                continue
            for f in (.25, .75) if a1 - a0 > .8 else (.36, .66):
                az = a0 + (a1 - a0) * f + fine.uniform(-.05, .05)
                r0 = _bole_radius(bole, az % TAU, .3) - 1.2
                r = fine.uniform(.38, .6)
                _root(p, (r0 * math.cos(az), r0 * math.sin(az), r * .4), az + fine.uniform(-.3, .3), fine.uniform(5.0, 8.0), r, bark,
                      4480 + 3 * i + int(f * 10), 17.1, sides=sides, rings=rings, forks=forks)
    # --- the limbs: grown the same at every level, built as far as the level shows
    live = dict(segs=[0, 13, 9, 5, 4], up=[0, .12, .28, .25, .2], wiggle=.09, kink=[0, .045, .06, .06, .05], sag=[0, .03, 0, 0, 0],
                taper=[0, .2, .28, .35, .4], children=[0, 6, 4, 3], t0=[0, .2, .22, .3], spread=[0, (.6, 1.0), (.5, .95), (.5, .9)],
                ratio=[0, (.34, .5), (.4, .55), (.38, .52)], child_r=[0, .5, .55, .55], lift=[0, .14, .1, .05], fall=.5)
    bare = dict(live, children=[0, 3, 3, 2], kink=[0, .06, .08, .08, .08], ratio=[0, (.3, .45), (.35, .5), (.3, .45)], taper=[0, .3, .35, .4, .4])
    rings1, sides1 = ((26, 14), (14, 9), (8, 6))[lod]
    twigs, strands, dead_strands = [], [], []
    for z, deg, elev, length, r, is_dead in LIMBS:
        az, el = math.radians(deg), math.radians(elev)
        c = axis(z)
        out = np.array([math.cos(az), math.sin(az), 0.0])
        t = _grow(rng, np.array([c[0], c[1], z]) + out * radius(z) * .45, out * math.cos(el) + UP * math.sin(el), length, r,
                  bare if is_dead else live, 1)
        colour = DEADWOOD if is_dead else bark
        for pts, rad, depth in t['wood']:
            seed = int(fine.integers(1 << 20))
            if depth == 1:
                P, R = _spline(pts, rad, rings1, 1.3)
                v0, f0, off, ring = _limb(p, P, R, sides1, colour, seed, collar=.35, cap=not is_dead or lod == 2)
                if is_dead and lod < 2:
                    _break(p, fine, P[-1], P[-1] - P[-2], R[-1], colour, sides1)
                elif lod < 2:    # moss along the limb's back, thinning toward its end
                    w = _smooth(off[:, 2], .3, .85) * _smooth(noise2(ring * .35 * 26 / rings1 + seed, off[:, 0] * 1.5, seed), -.45, .25) * \
                        (1 - _smooth(ring / (rings1 - 1.0), .5, .95))
                    _moss(p, v0, f0, w, off, .06, seed, colour)
            elif depth == 2 and lod == 0:
                P, R = _spline(pts, rad, 10, 1.2)
                _limb(p, P, R, 7, colour, seed, collar=.3, cap=not is_dead)
                if is_dead:
                    _break(p, fine, P[-1], P[-1] - P[-2], R[-1], colour, 7)
            elif depth == 2 and (lod == 1 or is_dead):
                P, R = _spline(pts, rad, 6 if lod == 1 else 4, 1.2)
                _limb(p, P, R, 5 if lod == 1 else 3, colour, seed, collar=.3)
            elif depth == 3 and lod == 0:
                _limb(p, pts, rad, 4, colour, seed, collar=.25)
            elif depth == 3 and lod == 1:
                _limb(p, pts[::2], rad[::2], 3, colour, seed)
            elif depth == 4 and lod == 0:
                (dead_strands if is_dead else strands).append((pts[0], pts[-1], rad[0], rad[-1] * .5))
        if not is_dead:
            twigs += [w_ for w_ in t['wood'] if w_[2] >= 3]
        elif lod < 2:            # a dead limb's last twigs: bare sticks off its finest wood
            for pts, rad, depth in t['wood']:
                if depth >= 3:
                    for _ in range(4 if lod == 0 else 2):
                        q, d = fl._along(pts, fine.uniform(.25, 1.0))
                        way = unit(d + fine.normal(0, .6, 3) + UP * fine.uniform(-.5, .3))
                        dead_strands.append((q, q + way * fine.uniform(.8, 2.4), .035, .012))
    for group, colour in ((strands, TWIG), (dead_strands, tone(DEADWOOD, .8))):
        if group:
            a, b, ra, rb = (np.array([s[k] for s in group]) for k in range(4))
            _strands(p, a, b, ra, rb, colour)
    # --- the crown
    ends = np.array([w_[0][-1] for w_ in twigs])
    lo, hi = ends.min(0), ends.max(0)
    leaf = _leaf_set(np.random.default_rng(4403), _twigs(twigs, (3, 4), 1.5), ((lo + hi) / 2, (hi - lo) / 2 + 2.0), 40000, (1.9, 2.7),
                     cloud=1.7, inner=.45, droop=.15)
    _lay(p, 'LBroadleaf', leaf, lod, bend=.15, seed=4401)
    # --- fit: the crown is stretched so the stag's head tops out at 88 m; nothing below the ground
    v = np.asarray(p.v, np.float64)
    high = v[:, 2] > 40
    v[high, 2] = 40 + (v[high, 2] - 40) * (88.0 - 40) / (v[:, 2].max() - 40)
    v[:, 2] = np.maximum(v[:, 2], 0.0)
    p.v = v.tolist()
    return finish(p, centre_xy=False)


# ---------------------------------------------------------------- the great trees

def giant_tree(lod=0):
    """SM_GV_GiantTree, 46 m: one of the grove's ancient stems, grown as a column (a kauri's habit). A bole 2.6 m in
    radius at z 1.5, ribbed and furrowed, that stays within 2.9 m of the axis from z 8 to z 24, where the timber
    platforms ring it (the limbs' feet too: they leave the bole at 22 m but climb inside that radius until they are
    above z 24, then sweep out); seven buttress roots reaching 5.5 m from the axis; a crown 16 m in radius from limbs in
    four tiers, with no leaves within 7.5 m of the axis below z 25. Moss on its north side (+x): the bole's lower
    half, the buttresses' crests and north faces, the limbs' backs.
    lod 1 to 3 are its far versions (SM_GV_GiantTree_LOD1.._LOD3)."""
    rng = np.random.default_rng(4301)            # the tree's shape: the same draws at every level of detail
    fine = np.random.default_rng(4302)           # what a far version may leave out
    p = Part(_lod_name('SM_GV_GiantTree', lod), (BARK, LEAF, MOSS))
    bark = BARK_BROWN
    RZ = np.array([0, .6, 1.5, 4, 8, 16, 22, 24, 27, 30, 33, 36, 38.0])
    RR = np.array([3.1, 2.82, 2.6, 2.48, 2.4, 2.25, 2.12, 2.08, 1.9, 1.6, 1.25, .9, .72])

    def radius(z):
        return float(np.interp(z, RZ, RR))

    def axis(z):
        lean = float(_smooth(z, 22, 40))
        return np.array([.25 * lean + .05 * math.sin(z * .21) * float(_smooth(z, 2, 9)), -.18 * lean])
    WALLS = ((15, 5.5, 5.0), (70, 4.8, 3.8), (118, 5.3, 4.6), (170, 4.6, 3.4), (222, 5.5, 5.2), (270, 5.0, 4.2), (318, 4.7, 3.6))
    # the limbs: height, azimuth, elevation (degrees), turn (cfg 'up': negative sweeps a steep limb outward), length, radius
    LIMBS = ((22.0, 40, 66, -.58, 13.5, .68), (22.6, 112, 64, -.55, 13.0, .64), (23.2, 186, 67, -.6, 14.0, .7), (22.3, 258, 65, -.56, 12.8, .62),
             (23.5, 328, 66, -.58, 13.4, .66),
             (26.2, 78, 60, -.4, 11.6, .54), (27.0, 150, 58, -.36, 12.0, .56), (27.6, 224, 61, -.42, 11.2, .52), (26.6, 296, 59, -.38, 11.8, .55),
             (30.6, 10, 62, -.2, 9.6, .44), (31.4, 100, 64, -.22, 9.2, .42), (32.0, 196, 61, -.18, 10.0, .45), (31.0, 282, 63, -.2, 9.4, .43),
             (35.0, 50, 76, 0.0, 7.8, .38), (35.6, 170, 74, 0.0, 8.2, .4), (36.2, 290, 78, 0.0, 7.6, .36))
    ribs = []
    for deg, _, hk in WALLS:     # each buttress runs on up the bole as a low rib
        ribs.append((math.radians(deg),
                     lambda z, hk=hk: .5 * (1 - .4 * z / hk) if z <= hk else .3 * math.exp(-(z - hk) / 7.0),
                     lambda z, hk=hk: .16 + .1 * float(_smooth(z, 0, hk * 1.3)) + .14 * float(_smooth(z, hk, 24)),
                     rng.uniform(-.004, .004)))
    for _ in range(14):          # folds of the bole itself
        zc, zs_, amp, wide = rng.uniform(1, 30), rng.uniform(5, 12), rng.uniform(.05, .12) * rng.choice((-1, 1)), rng.uniform(.09, .2)
        ribs.append((rng.uniform(0, TAU), lambda z, zc=zc, zs_=zs_, amp=amp: amp * math.exp(-((z - zc) / zs_) ** 2),
                     lambda z, wide=wide: wide, rng.uniform(-.01, .01)))
    bumps = [(rng.uniform(0, TAU), rng.uniform(.8, 6.5), rng.uniform(.1, .22), rng.uniform(.12, .22), rng.uniform(.4, .8)) for _ in range(5)]
    for z, deg, _, _, _, r in LIMBS:                                  # the swelling where each limb leaves the bole
        bumps.append((math.radians(deg), z + 2.6, .42 * r, 1.3 * r / radius(z + 2.6), 2.2 * r))

    def field(th, z):
        return _furrows(th + .012 * z, z, 4311, 40, 2.4)

    def moss_on(th, z, f, ridge):
        north = .5 + .5 * np.cos(th - NORTH)
        patch = _ring_noise(th / TAU * 9, z / 2.2, 4321, 9)
        speck = _ring_noise(th / TAU * 26, z / .8 + 5.0, 4322, 26)
        return _smooth(north ** 1.5 * (1 - .75 * float(_smooth(z, 4, 26))) * .7 + .42 * patch + .2 * speck - .2 * (1 - f), .58, .9)
    zs = np.r_[0, .25, .55, .9, 1.3, 1.75, 2.25, 2.8, 3.4, 4.0, np.arange(4.6, 26.01, .6), 27.0, 28.2, 29.5, 31.0, 32.5, 34.0, 35.5, 37.0]
    step = (1, 2, 4, 8)[lod]
    zs = np.r_[zs[:-1:step], zs[-1]]
    most = (160, 80, 40, 5)[lod]
    counts = [most if z <= 26.1 or lod == 3 else most // 2 if z <= 31.2 or lod == 2 else most // 4 for z in zs]
    deep = (1.0, .6, 0.0, 0.0)[lod]
    bole = _bole(p, zs, counts, radius, axis, ribs if lod < 3 else [], bumps if lod < 3 else [],
                 {'field': field, 'depth': lambda z: deep * float(np.interp(z, [0, 26, 37], [.1, .09, .05]))}, bark, 4301, 2.0, moss_on,
                 .04 if lod < 2 else 0.0)
    if MOSS_SLOT(p) not in p.m:                  # a far version always keeps a little of the moss: the same slots at every level
        north = [i for i, f in enumerate(p.f) if np.mean([p.v[q][0] for q in f]) > 1.0 and np.mean([p.v[q][2] for q in f]) < 14]
        for i in north[:max(1, len(north) // 2)]:
            p.m[i] = MOSS_SLOT(p)
    top, m = axis(zs[-1]), counts[-1]
    start = len(p.v) - m
    p.add([[top[0], top[1], zs[-1] + .5]], [], _dim(bark, np.ones(1)), BARK)
    for j in range(m):
        p.f.append([start + j, start + (j + 1) % m, len(p.v) - 1])
        p.m.append(0)
        p.s.append(True)
    # --- the buttresses and the roots
    lines = []
    for i, (deg, reach, high) in enumerate(WALLS):
        az = math.radians(deg)
        foot, sway = rng.uniform(.38, .46), rng.uniform(.08, .14)
        if lod < 3:
            lines.append(_wall(p, az, _bole_radius(bole, az, high) - .08, reach, high, bark, 4330 + i, foot=foot, mid=.16, top=.07, sway=sway,
                               stations=20, wave=1.0, fold=.06, furrow=.05, grain=.22, inset=.7,
                               moss=.5 + .45 * (.5 + .5 * math.cos(az - NORTH)), lod=lod)[0])
    if lod < 2:
        forks, sides, rings = (1, 6, 18) if lod == 0 else (0, 4, 8)
        for i, line in enumerate(lines):
            j = int(fine.uniform(.55, .85) * (len(line) - 1))
            r = fine.uniform(.1, .17)
            heading = math.atan2(line[j][1], line[j][0]) + fine.choice((-1, 1)) * fine.uniform(.5, 1.0)
            _root(p, (line[j][0], line[j][1], r * .4), heading, fine.uniform(1.4, 2.6), r, bark, 4350 + i, 5.42, sides=sides, rings=rings, forks=forks)
        walls = np.radians([w[0] for w in WALLS])
        for i in range(len(walls)):
            a0, a1 = walls[i], walls[(i + 1) % len(walls)] + (TAU if i == len(walls) - 1 else 0)
            az = a0 + (a1 - a0) * fine.uniform(.35, .65)
            r0 = _bole_radius(bole, az % TAU, .25) - .4
            r = fine.uniform(.12, .2)
            _root(p, (r0 * math.cos(az), r0 * math.sin(az), r * .4), az + fine.uniform(-.3, .3), fine.uniform(1.6, 2.6), r, bark, 4360 + i,
                  5.42, sides=sides, rings=rings, forks=forks)
    # --- the limbs: grown the same at every level, built as far as the level shows
    cfg = dict(segs=[0, 12, 8, 5, 4], up=[0, 0, .28, .25, .2], wiggle=.08, kink=[0, .035, .06, .06, .05], sag=[0, .03, 0, 0, 0],
               taper=[0, .22, .3, .35, .4], children=[0, 5, 4, 3], t0=[0, .38, .25, .3], spread=[0, (.6, 1.0), (.5, .95), (.5, .9)],
               ratio=[0, (.38, .52), (.4, .55), (.4, .55)], child_r=[0, .5, .55, .55], lift=[0, .12, .1, .05], fall=.5)
    rings1, sides1 = ((22, 12), (12, 8), (7, 5), (0, 0))[lod]
    twigs, strands = [], []
    for z, deg, elev, turn, length, r in LIMBS:
        az, el = math.radians(deg), math.radians(elev)
        c = axis(z)
        out = np.array([math.cos(az), math.sin(az), 0.0])
        t = _grow(rng, np.array([c[0], c[1], z]) + out * radius(z) * .22, out * math.cos(el) + UP * math.sin(el), length, r,
                  dict(cfg, up=[0, turn, .28, .25, .2]), 1)
        for pts, rad, depth in t['wood']:
            seed = int(fine.integers(1 << 20))
            if depth == 1 and lod < 3:
                P, R = _spline(pts, rad, rings1, 1.3)
                v0, f0, off, ring = _limb(p, P, R, sides1, bark, seed, collar=.3)
                if lod < 2:      # moss along the limb's back
                    w = _smooth(off[:, 2], .3, .85) * _smooth(noise2(ring * .35 * 22 / rings1 + seed, off[:, 0] * 1.5, seed), -.4, .3) * \
                        (1 - _smooth(ring / (rings1 - 1.0), .55, .95))
                    _moss(p, v0, f0, w, off, .03, seed, bark)
            elif depth == 2 and lod < 2:
                P, R = _spline(pts, rad, (9, 5)[lod], 1.2)
                _limb(p, P, R, (6, 4)[lod], bark, seed, collar=.3)
            elif depth == 3 and lod == 0:
                _limb(p, pts, rad, 3, bark, seed, collar=.25)
            elif depth == 3 and lod == 1:
                _limb(p, pts[::2], rad[::2], 3, bark, seed)
            elif depth == 4 and lod == 0:
                strands.append((pts[0], pts[-1], rad[0], rad[-1] * .5))
        twigs += [w_ for w_ in t['wood'] if w_[2] >= 3]
    if strands:
        a, b, ra, rb = (np.array([s[k] for s in strands]) for k in range(4))
        _strands(p, a, b, ra, rb, TWIG)
    # --- the crown: no leaves in the platforms' space
    ends = np.array([w_[0][-1] for w_ in twigs])
    lo, hi = ends.min(0), ends.max(0)
    leaf = _leaf_set(np.random.default_rng(4303), _twigs(twigs, (3, 4), 1.5), ((lo + hi) / 2, (hi - lo) / 2 + 1.2), 14500, (1.1, 1.55),
                     cloud=.8, inner=.45, droop=.15, keep=lambda q: (np.hypot(q[:, 0], q[:, 1]) > 7.5) | (q[:, 2] > 25.0))
    _lay(p, 'LBroadleaf', leaf, lod, bend=.15, seed=4301, far=1200)
    # --- fit: the crown is stretched so the tree tops out at 46 m (the bole below z 24 is left as built)
    v = np.asarray(p.v, np.float64)
    high = v[:, 2] > 24
    v[high, 2] = 24 + (v[high, 2] - 24) * (46.0 - 24) / (v[:, 2].max() - 24)
    v[:, 2] = np.maximum(v[:, 2], 0.0)
    p.v = v.tolist()
    return finish(p, centre_xy=False)


# ---------------------------------------------------------------- the grove's common stems

def _fit_tree(tree, height, balance=True):
    """Scales a grown skeleton so its highest tip stands at `height` and (balance) shears its crown back over its foot,
    so a crown that grew lopsided does not hang off its trunk. Returns the scale."""
    k = height / max(e[2] for e, _, _ in tree['tips'])
    tips = np.array([e for e, _, _ in tree['tips']]) * k
    high = tips[tips[:, 2] > height * .45]
    shear = (high[:, :2].min(0) + high[:, :2].max(0)) / 2 if balance and len(high) else np.zeros(2)

    def fix(q):
        q = np.asarray(q, np.float64) * k
        q[..., :2] -= shear * np.clip(q[..., 2:3] / (height * .7), 0, 1) ** 1.5
        return q
    tree['wood'] = [(fix(pts), r * k, depth) for pts, r, depth in tree['wood']]
    tree['tips'] = [(fix(e), d, depth) for e, d, depth in tree['tips']]
    return k


def _top_out(part, height, hold=.45):
    """Stretches what stands above `hold` of the height so the top is exactly `height`; nothing dips under z 0."""
    v = np.asarray(part.v, np.float64)
    z0 = height * hold
    up = v[:, 2] > z0
    v[up, 2] = z0 + (v[up, 2] - z0) * (height - z0) / (v[:, 2].max() - z0)
    v[:, 2] = np.maximum(v[:, 2], 0.0)
    part.v = v.tolist()


def _stain(colour):
    """A bark colour under algae: greener and darker (the scan is tinted by vertex colour over this bark's own colour)."""
    return col(colour[0] * .72, colour[1] * 1.02, colour[2] * .55)


def _stem(part, pts, radii, sides, colour, seed=0, rings=14, flare=(), swell=.3, lumps=.035, ground=1.5, stain=.4, burls=()):
    """A common tree's trunk: level rings along its line, closer together at the foot, where it swells into the root
    flare (swell) and toward each root (flare: their azimuths); a little out of round (lumps), with burls (height,
    azimuth, size). Darker toward the ground, stained green on its north side near it."""
    P, R = _spline(pts, radii, rings, 1.7)
    th = np.arange(sides) / sides * TAU
    z, r0 = P[:, 2], R[0]
    rr = R[:, None] * (1 + swell * np.exp(-z[:, None] / (1.3 * r0)) + lumps * _ring_noise(th[None, :] / TAU * 5, z[:, None] / (3 * r0), seed, 5))
    for az in flare:
        rr = rr + r0 * .55 * np.exp(-(_wrap(th - az) / .42) ** 2)[None, :] * (np.clip(1 - z / (2.8 * r0), 0, 1) ** 2)[:, None]
    for bz, az, size in burls:
        rr = rr + size * np.exp(-((z[:, None] - bz) / (size * 2.2)) ** 2) * np.exp(-(_wrap(th - az) / max(size * 2.2 / r0, .2)) ** 2)[None, :]
    rings_ = [np.c_[P[i, 0] + rr[i] * np.cos(th), P[i, 1] + rr[i] * np.sin(th), np.full(sides, z[i])] for i in range(len(P))]
    k = (.74 + .26 * _smooth(z, 0, ground))[:, None] * (.93 + .1 * _ring_noise(th[None, :] / TAU * 9, z[:, None] * 1.3, seed + 7, 9))
    green = stain * ((.5 + .5 * np.cos(th - NORTH)) ** 2)[None, :] * (1 - _smooth(z, .2, 2.0 + 4 * r0))[:, None] * \
        _smooth(_ring_noise(th[None, :] / TAU * 6, z[:, None] * .9 + 3.0, seed + 9, 6), -.5, .4)
    cols = _lerp(_dim(colour, k), _dim(_stain(colour), k), green)
    _skin(part, rings_, list(cols))
    first = len(part.v) - sides
    part.add([P[-1] + (0, 0, R[-1] * .3)], [[first + j - len(part.v), first + (j + 1) % sides - len(part.v), 0] for j in range(sides)],
             _dim(colour, np.ones(1)), BARK)


def _broadleaf(spec, lod=0):
    """One of the grove's common stems from its spec (the dicts below), at a level of detail: the trunk (order 0) as a
    flared stem with surface roots, the limbs of each order as tapering tubes with collars, the last order as thin
    twig strands (LEAF, never colliding), and the crown as scanned leaf sprays on the outer branches. The far versions
    grow the same skeleton and keep one card in two, six, or a spread few hundred, each larger."""
    rng = np.random.default_rng(spec['seed'])            # the tree's shape: the same draws at every level of detail
    fine = np.random.default_rng(spec['seed'] + 1)
    p = Part(_lod_name(spec['name'], lod), (BARK, LEAF))
    bark, height, cfg = spec['bark'], spec['height'], spec['cfg']
    last = len(cfg['segs']) - 1
    length, radius = spec['trunk']
    t = _grow(rng, np.zeros(3), (spec['lean'][0], spec['lean'][1], 1.0), length, radius, cfg)
    _fit_tree(t, height - spec['top'], spec.get('balance', True))
    roots = rng.uniform(0, TAU) + np.arange(spec['roots']) * TAU / spec['roots'] + rng.uniform(-.3, .3, spec['roots'])
    burls = [(rng.uniform(.5, 2.5), rng.uniform(0, TAU), rng.uniform(.04, .09)) for _ in range(spec.get('burls', 0))]
    pts, rad, _ = t['wood'][0]
    r0 = rad[0]
    sides = spec['sides']
    _stem(p, pts, rad, (sides[0], max(8, sides[0] * 3 // 5), 6, 5)[lod], bark, spec['seed'], (len(pts) * 2, len(pts), 8, 6)[lod],
          roots if lod < 3 else (), spec.get('swell', .3), spec.get('lumps', .035), 1.2 + 2 * r0, burls=burls if lod < 2 else ())
    if lod < 2:
        for i, az in enumerate(roots):
            r = r0 * fine.uniform(.34, .46)
            _root(p, (r0 * .7 * math.cos(az), r0 * .7 * math.sin(az), r * .6), az + fine.uniform(-.2, .2), r0 * fine.uniform(1.8, 3.0) + .15, r, bark,
                  spec['seed'] + 20 + i, wander=.3, sides=6 if lod == 0 else 4, rings=12 if lod == 0 else 6, forks=0)
    strands = []
    for pts, rad, depth in t['wood'][1:]:
        seed = int(fine.integers(1 << 20))
        if depth == last:
            if lod == 0:
                strands.append((pts[0], pts[-1], rad[0], max(rad[-1] * .5, .003)))
        elif depth == 1 and lod < 3:
            P, R = _spline(pts, rad, (len(pts) * 2, len(pts), 5)[lod], 1.3)
            _limb(p, P, R, (sides[1], max(5, sides[1] * 2 // 3), 5)[lod], bark, seed, collar=.3)
        elif depth == 2 and lod < 2:
            P, R = _spline(pts, rad, (len(pts) + 3, 5)[lod], 1.2)
            _limb(p, P, R, (sides[2], 4)[lod], bark, seed, collar=.25)
        elif depth >= 3 and lod == 0:
            _limb(p, pts, rad, sides[3], bark, seed, collar=.2)
        elif depth >= 3 and lod == 1:
            _limb(p, pts[::2] if len(pts) > 3 else pts[[0, -1]], rad[::2] if len(pts) > 3 else rad[[0, -1]], 3, bark, seed)
    if strands:
        a, b, ra, rb = (np.array([s_[k] for s_ in strands]) for k in range(4))
        _strands(p, a, b, ra, rb, TWIG)
    outer = [w for w in t['wood'] if w[2] >= last - 1]
    ends = np.array([w[0][-1] for w in outer])
    lo, hi = ends.min(0), ends.max(0)
    leaf = _leaf_set(np.random.default_rng(spec['seed'] + 2), _twigs(outer, (last - 1, last), 1.5), ((lo + hi) / 2, (hi - lo) / 2 + spec['card'][1] * .6),
                     spec['cards'], spec['card'], spec.get('tint', (.92, .95, .88)), spec.get('cloud', .2), spec.get('flat', .5),
                     spec.get('droop', .1), spec.get('facing_up', .55), inner=spec.get('inner', .5), gold=spec.get('gold'))
    _lay(p, 'LBroadleaf', leaf, lod, ('twig',), spec.get('bend', .12), spec['seed'], spec.get('far', 320))
    if lod == 0 and spec.get('singles'):         # single leaves at their true size, where a young stem shows each one
        count, size = spec['singles']
        single = _leaf_set(np.random.default_rng(spec['seed'] + 3), _twigs(outer, (last - 1, last), .5), leaf['crown'], count, size,
                           spec.get('tint', (.92, .95, .88)), 0.0, 1.0, .25, .6, tip=1.0, inner=spec.get('inner', .5))
        _lay(p, 'LBroadleaf', single, 0, ('leaf_a', 'leaf_b', 'leaf_c'), 0.0, spec['seed'] + 3)
    _top_out(p, height)
    return finish(p, centre_xy=False)


# An old broad stem: a short thick bole, heavy low scaffold limbs that spread wide and wander, a crown as broad as it
# is tall. Its bark is the old, furrowed kind (the BOakGrey scan).
OAK = dict(name='SM_GV_Oak', seed=4201, height=14.0, top=.55, bark=BARK_BROWN, trunk=(4.3, .5), lean=(.05, -.03), roots=6, burls=3,
           sides=(20, 10, 6, 4), swell=.38, lumps=.05, cards=9000, card=(.62, .92), cloud=.25, far=340,
           cfg=dict(segs=[10, 9, 7, 5, 3], up=[.05, .2, .2, .18, .1], wiggle=.12, kink=[0, .06, .07, .07, .05], sag=[0, .04, .02, 0, 0],
                    taper=[.55, .3, .35, .4, .5], children=[5, 4, 4, 4], t0=[.5, .25, .25, .3],
                    spread=[(.85, 1.25), (.5, .9), (.5, .9), (.5, .9)], ratio=[(1.0, 1.3), (.42, .6), (.42, .58), (.4, .55)],
                    child_r=[.55, .55, .58, .55], lift=[.05, .12, .1, .05], fall=.4))
# A tall straight stem: a smooth columnar bole clear of limbs for a third of its height, steep limbs, a high domed
# crown whose sprays lie in layers.
BEECH = dict(name='SM_GV_Beech', seed=4202, height=18.0, top=.5, bark=BARK_GREY, trunk=(15.8, .36), lean=(.015, .01), roots=5, burls=1, balance=False,
             sides=(18, 8, 5, 4), swell=.32, lumps=.025, cards=8000, card=(.6, .88), cloud=.25, flat=.8, facing_up=.68, tint=(.98, 1.0, .86), far=340,
             cfg=dict(segs=[12, 8, 6, 5, 3], up=[.0, .22, .2, .18, .1], wiggle=.035, kink=[.006, .04, .05, .06, .05], sag=[0, .03, 0, 0, 0],
                      taper=[.16, .3, .35, .4, .5], taper_power=[1.3, 1, 1, 1, 1], children=[12, 3, 3, 2], t0=[.36, .25, .25, .3],
                      spread=[(.7, 1.0), (.5, .9), (.5, .9), (.5, .9)], ratio=[(.25, .33), (.42, .6), (.42, .58), (.42, .55)],
                      child_r=[.4, .55, .58, .55], lift=[.05, .1, .08, .05], fall=.5, splay=[.5, 0, 0, 0]))
# A slender young stem, leaning a little, its fine branches hanging at their ends and its leaves turning gold.
BIRCH = dict(name='SM_GV_Birch', seed=4203, height=11.0, top=.4, bark=tone(BARK_GREY, 1.12), trunk=(9.6, .12), lean=(.11, .05), roots=4,
             sides=(14, 6, 4, 3), swell=.3, lumps=.02, cards=7500, card=(.46, .66), cloud=.18, droop=.3, tint=(.95, .9, .6),
             gold=((1.0, .8, .35), .7), far=300,
             cfg=dict(segs=[12, 7, 5, 3], up=[.03, .32, -.1, -.3], wiggle=.06, kink=[.02, .05, .06, .05], sag=[0, .03, .05, .08],
                      taper=[.15, .3, .4, .5], taper_power=[1.2, 1, 1, 1], children=[11, 4, 3], t0=[.3, .25, .3],
                      spread=[(.55, .9), (.5, .9), (.5, .9)], ratio=[(.17, .29), (.42, .6), (.45, .6)],
                      child_r=[.4, .55, .55], lift=[.12, 0, -.1], fall=.6))
# A young one, 3 m: a whip of a stem and a few thin branches, leaves at their true size.
SAPLING = dict(name='SM_GV_Sapling', seed=4204, height=3.0, top=.22, bark=tone(BARK_GREY, 1.1), trunk=(2.75, .03), lean=(.06, -.04), roots=3,
               sides=(10, 5, 3, 3), swell=.35, lumps=.02, cards=120, card=(.38, .5), cloud=.03, singles=(170, (.075, .11)),
               tint=(.98, 1.0, .9), inner=.8, far=40,
               cfg=dict(segs=[10, 6, 3], up=[.02, .35, .2], wiggle=.07, kink=[.02, .04, .04], taper=[.2, .35, .5], children=[8, 3],
                        t0=[.3, .3], spread=[(.6, .95), (.5, .9)], ratio=[(.18, .34), (.4, .6)], child_r=[.45, .55], lift=[.1, .05], fall=.5))


def oak(lod=0):
    """SM_GV_Oak, 14 m: an old broad stem (OAK). lod 1 to 3: its far versions."""
    return _broadleaf(OAK, lod)


def beech(lod=0):
    """SM_GV_Beech, 18 m: a tall straight stem (BEECH). lod 1 to 3: its far versions."""
    return _broadleaf(BEECH, lod)


def birch(lod=0):
    """SM_GV_Birch, 11 m: a slender young stem turning gold (BIRCH). lod 1 to 3: its far versions."""
    return _broadleaf(BIRCH, lod)


def sapling(lod=0):
    """SM_GV_Sapling, 3 m: a young stem (SAPLING). lod 1 and 2: its far versions."""
    return _broadleaf(SAPLING, lod)


def snag():
    """SM_GV_Snag, 9 m: a dead stem of the grove, as the blight leaves them. The trunk has snapped at about 7.5 m and
    ends in splinters, one of them a spire; its limbs are bare, wandering and hanging a little, half of them broken
    short, the rest ending in a few stiff branches. Bark only: weathered grey wood, darker where bark still clings and
    under the limbs."""
    rng = np.random.default_rng(4205)
    p = Part('SM_GV_Snag', (BARK,))
    wood = tone(BARK_GREY, .9)
    cfg = dict(segs=[11, 8, 5, 3], up=[.02, .08, .1, .05], wiggle=.12, kink=[.025, .08, .09, .08], sag=[0, .07, .04, 0], taper=[.5, .32, .4, .5],
               children=[9, 3, 3], t0=[.28, .3, .35], spread=[(.8, 1.3), (.5, 1.0), (.5, 1.0)], ratio=[(.26, .5), (.4, .62), (.4, .6)],
               child_r=[.42, .55, .55], lift=[0, .05, 0], fall=.6)
    t = _grow(rng, np.zeros(3), (.07, .04, 1.0), 7.6, .34, cfg)
    pts, rad, _ = t['wood'][0]
    roots = rng.uniform(0, TAU) + np.arange(4) * TAU / 4 + rng.uniform(-.3, .3, 4)
    _stem(p, pts, rad, 18, wood, 4205, 22, roots, .34, .05, 1.6, .25, [(rng.uniform(1, 5), rng.uniform(0, TAU), rng.uniform(.05, .1)) for _ in range(3)])
    lean = unit(pts[-1] - pts[-2])
    _break(p, rng, pts[-1], lean, rad[-1] * 1.05, wood, 18, 1.6)
    a, b = frame(lean)                                           # the spire: the last standing sliver of the stem
    foot = pts[-1] + a * rad[-1] * .55
    _limb(p, [foot - lean * .3, foot + lean * .5 + a * .03, foot + lean * 1.25 + a * .1 + b * .05], [.085, .06, .012], 5, tone(DEADWOOD, 1.1), 7, under=.1)
    for i, az in enumerate(roots):
        r = rad[0] * rng.uniform(.34, .45)
        _root(p, (rad[0] * .7 * math.cos(az), rad[0] * .7 * math.sin(az), r * .6), az + rng.uniform(-.2, .2), rad[0] * rng.uniform(2.0, 3.2), r, wood,
              4225 + i, wander=.3, sides=6, rings=12, forks=0)
    cut = 0                                                      # of the limb being built: where it is broken (0: whole)
    for pts, rad, depth in t['wood'][1:]:
        seed = int(rng.integers(1 << 20))
        shade = rng.uniform(.62, 1.08)                           # some limbs still dark with bark, some bleached
        if depth == 1:
            cut = rng.uniform(.3, .6) if rng.uniform() < .5 else 0
            if cut:
                keep = max(3, int(cut * len(pts)))
                P, R = _spline(pts[:keep], rad[:keep], keep * 2, 1.3)
                _limb(p, P, R, 8, wood, seed, collar=.35, shade=shade, cap=False)
                _break(p, rng, P[-1], P[-1] - P[-2], R[-1], wood, 8, 1.4)
            else:
                P, R = _spline(pts, rad, len(pts) * 2, 1.3)
                _limb(p, P, R, 8, wood, seed, collar=.35, shade=shade)
        elif not cut:
            if depth == 2:
                P, R = _spline(pts, rad, len(pts) + 3, 1.2)
                _limb(p, P, R, 6, wood, seed, collar=.25, shade=shade)
            else:
                _limb(p, pts, np.maximum(rad, .008), 4, wood, seed, shade=shade)
    grime(p, 0, .3, .8, 4205)
    _top_out(p, 9.0, .6)
    return finish(p, centre_xy=False, normals=False)


# ---------------------------------------------------------------- the fir of the rim

def pine(lod=0):
    """SM_GV_Pine, 20 m: the one tree of the valley that is not the grove: a fir of the rim. A straight dark stem, bare
    for its lowest third but for the stubs of dead whorls; above, whorls of five branches every half metre or so, the
    low ones drooping with upturned tips and the high ones rising, each a flat fan of alternate branchlets (thin
    strands) carrying the 'LFir' sheet's sprays, most lying flat in their tier, some hanging. lod 1 to 3: its far
    versions (SM_GV_Pine_LOD1.._LOD3)."""
    rng = np.random.default_rng(4206)            # the tree's shape: the same draws at every level of detail
    fine = np.random.default_rng(4207)
    p = Part(_lod_name('SM_GV_Pine', lod), (BARK, LEAF))
    bark, H, foot = BARK_DARK, 20.0, 6.3
    zt = np.linspace(0, H - .25, 18)
    line = np.c_[.07 * np.sin(zt * .45 + 1) * _smooth(zt, 0, 6), .05 * np.sin(zt * .33) * _smooth(zt, 0, 6), zt]
    rad = .27 * (1 - zt / H) ** .9 + .012
    roots = rng.uniform(0, TAU) + np.arange(5) * TAU / 5 + rng.uniform(-.3, .3, 5)
    _stem(p, line, rad, (16, 10, 6, 5)[lod], bark, 4206, (26, 14, 8, 6)[lod], roots if lod < 3 else (), .35, .02, 2.0, .25)
    if lod < 2:
        for i, az in enumerate(roots):
            r = fine.uniform(.09, .12)
            _root(p, (.19 * math.cos(az), .19 * math.sin(az), r * .6), az + fine.uniform(-.2, .2), fine.uniform(.7, 1.1), r, bark, 4226 + i,
                  wander=.3, sides=6 if lod == 0 else 4, rings=10 if lod == 0 else 5, forks=0)

    def axis(z):
        return np.array([np.interp(z, zt, line[:, 0]), np.interp(z, zt, line[:, 1]), z])
    base, grow, face, size, tint, strands = [], [], [], [], [], []

    def spray(q, g, length, light, hang=False):
        out = unit((q - axis(q[2])) * (1, 1, 0) + 1e-9)
        base.append(q)
        grow.append(unit(g * .6 + out * .2 - UP * .6) if hang else g)
        face.append(unit(UP * .45 + out * .9 + rng.normal(0, .2, 3)) if hang else unit(UP + rng.normal(0, .22, 3)))
        size.append(length)
        tint.append(np.array([.9, .95, .88]) * (.5 + .5 * light) * rng.uniform(.88, 1.06))
    # --- the dead whorls of the bare stem: stubs
    for z in (2.6, 3.7, 4.7, 5.6):
        for j in range(3):
            az = z * 2.1 + j * TAU / 3 + rng.uniform(-.4, .4)
            out = np.array([math.cos(az), math.sin(az), 0.0])
            length, c = rng.uniform(.25, 1.1), axis(z + rng.uniform(-.15, .15))
            if lod < 2:
                tip = c + out * (length + .2) - UP * length * rng.uniform(.1, .35)
                _limb(p, [c, (c + tip) / 2 + UP * .03, tip], [.028, .022, .014], 5 if lod == 0 else 3, tone(bark, 1.3), int(fine.integers(1 << 20)))
    # --- the living whorls
    z, k = foot, 0
    while z < H - 1.0:
        f = (z - foot) / (H - 1.0 - foot)                        # 0 at the crown's foot, 1 at its top
        reach = 3.7 * (1 - f) ** .85 + .3
        count = 5 if f < .7 else 4
        for j in range(count):
            az = k * 1.1 + j * TAU / count + rng.uniform(-.22, .22)
            el = math.radians(-14 + 40 * f + rng.uniform(-6, 6))
            L = reach * rng.uniform(.85, 1.08)
            c, out = axis(z + rng.uniform(-.06, .06)), np.array([math.cos(az), math.sin(az), 0.0])
            way = out * math.cos(el) + UP * math.sin(el)
            end = c + out * L * math.cos(el) + UP * (L * math.sin(el) + .1 * L - .05 * L * (1 - f))
            pts = bezier(c, c + way * L * .35, end - out * L * .3 - UP * .12 * L, end, 6)
            r = .02 + .011 * L
            seed = int(fine.integers(1 << 20))
            if lod == 0:
                _limb(p, pts, np.linspace(r, .006, 6), 5, bark, seed, collar=.3)
            elif lod == 1:
                _limb(p, pts[[0, 2, 5]], [r, r * .6, .008], 4, bark, seed)
            elif lod == 2:
                _limb(p, pts[[0, 5]], [r, .01], 3, bark, seed, cap=False)
            lets = int(np.clip(round(3 + 3.2 * L), 3, 14))
            for i, t in enumerate(np.linspace(.16, .93, lets) + rng.uniform(-.02, .02, lets)):
                q, d = fl._along(pts, float(t))
                side = unit(np.cross(UP, d)) * (1 if i % 2 else -1)
                ang = math.radians(rng.uniform(48, 64))
                run = unit(d * math.cos(ang) + side * math.sin(ang) - UP * .08)
                bl = (.5 * L * (1 - .62 * t) + .22) * rng.uniform(.85, 1.1)
                strands.append((q, q + run * bl, .011, .004))
                stations = max(2, int(bl / .25))
                for u in np.linspace(.22, 1.0, stations):
                    at = q + run * bl * u
                    light = .45 * t + .55 * u
                    if u > .99:
                        spray(at, run, rng.uniform(.6, .85) * (1 - .2 * t), light, rng.uniform() < .25)
                    else:
                        cross = unit(np.cross(UP, run))
                        for sgn in (-1, 1):
                            g = unit(run * .57 + cross * sgn * .82 - UP * rng.uniform(0, .25))
                            spray(at, g, rng.uniform(.52, .8) * (1 - .2 * t), light * .9, rng.uniform() < .2)
            spray(pts[-1], unit(pts[-1] - pts[-2]), rng.uniform(.6, .85), 1.0)
        z += (.78 - .28 * f) * rng.uniform(.9, 1.12)
        k += 1
    top = axis(H - .5)                                           # the leader
    for j in range(5):
        az = j * TAU / 5 + rng.uniform(-.3, .3)
        spray(top - UP * .25 * (j % 2), unit(np.array([math.cos(az) * .6, math.sin(az) * .6, 1.0])), rng.uniform(.5, .7), 1.0)
    if lod == 0:
        a, b, ra, rb = (np.array([s_[k_] for s_ in strands]) for k_ in range(4))
        _strands(p, a, b, ra, rb, tone(bark, 1.2))
    leaf = {'base': np.array(base), 'grow': np.array(grow), 'face': np.array(face), 'size': np.array(size), 'tint': np.array(tint),
            'crown': (np.array([0.0, 0.0, (foot + H) / 2 - 1.0]), np.array([4.3, 4.3, (H - foot) / 2 + 1.5]))}
    leaf['cap'] = 1.1 * np.hypot(leaf['base'][:, 0], leaf['base'][:, 1]) + .9
    _lay(p, 'LFir', leaf, lod, ('spray_a', 'spray_b', 'spray_c', 'spray_d'), .08, 4206, 480)
    _top_out(p, H)
    return finish(p, centre_xy=False)


# ---------------------------------------------------------------- the module's meshes and their contract

def _versions(builder, levels):
    """A builder and its far versions as builders of their own (builder(lod)), named so check.py and lookdev.py can
    pick them."""
    out = [builder]
    for lod in levels:
        def far(lod=lod):
            return builder(lod)
        far.__name__ = '%s_lod%d' % (builder.__name__, lod)
        out.append(far)
    return out


MESHES = [*_versions(heartwood, (1, 2)), *_versions(giant_tree, (1, 2, 3)), *_versions(oak, (1, 2, 3)), *_versions(beech, (1, 2, 3)),
          *_versions(birch, (1, 2, 3)), *_versions(pine, (1, 2, 3)), *_versions(sapling, (1, 2)), snag]


def _tree(height):
    return {'size': (0, 0, height), 'tol': .02, 'pivot': 'any'}


CONTRACT = {
    'SM_GV_Heartwood': _tree(88.0),
    'SM_GV_GiantTree': _tree(46.0),
    'SM_GV_Oak': _tree(14.0),
    'SM_GV_Beech': _tree(18.0),
    'SM_GV_Birch': _tree(11.0),
    'SM_GV_Pine': _tree(20.0),
    'SM_GV_Sapling': _tree(3.0),
    'SM_GV_Snag': _tree(9.0),
}
