"""Structures of Arche, the First Ones' Planet (level 5): the SM_AN_ architecture, weave pieces and props of the table
"Structures" in Tools/arche/README.md.

Pure numpy through kit (the Grove's kit over the Conclave's toolkit): check.py validates this module offline and
Tools/build_physis_arche.py builds it in Blender. Metres, Unreal axes (x forward, y right, z up); a mesh with a front
faces +x. Names, sizes and pivots are the README's table; CONTRACT at the end repeats them for check.py and FACTS holds
the numbers the placement code needs (walk surfaces, openings, light points).

How the First Ones' masonry is made here:
  - Every builder lays its mesh out in the contract's own frame (nothing is recentred afterwards, except the pieces
    with a 'centre' pivot), so a number in the table is a number in the code: the stair's landing is at exactly 12.0.
  - Stone is laid in long level courses of separate, chamfered blocks (course()): the joints are modelled V grooves a
    hand could feel, the blocks vary a little in tone and stand a centimetre out of true. Openings are tall, narrow and
    pointed: the blocks beside them are cut to the opening's curve. Walls are built plumb and then battered (warp()).
  - Walk surfaces are single continuous flat faces; what lies on them (inlay lines) is under 5 mm.
  - One thin line of electrum on every large piece, crystal where humans would set glass, and light in the right
    colour: ice blue for the Serene, violet for the Vigil's works, pearl gold for Reweave.
  - Vertex colour is the albedo under the slot's scanned surface. weather() puts the age in it from each vertex's
    place and normal: darker toward the ground and under ledges, blotches, runs down walls, lichen on tops and on the
    north side (-x), dust on flats. Faces are gridded so the weather has vertices to live on.
"""
from kit import *  # noqa: F401,F403

X, Y, Z = np.eye(3)
FACTS = {}                     # mesh name -> the numbers placement needs (filled by the builders)
_BUILDERS, _SIZES, _VARIANTS = [], {}, {}
NORTH = (-1.0, 0.0)            # a mesh's back is its lichen side


def mesh(name, size, variants=0, **spec):
    """Registers a builder and its contract row(s): size (x, y, z) in metres with 0 for any (a list of sizes when the
    builder has variants: it then takes the variant index and names its mesh name + index)."""
    def wrap(fn):
        _BUILDERS.append(fn)
        if variants:
            _VARIANTS[fn] = variants
            sizes = size if isinstance(size, list) else [size] * variants
            for k in range(variants):
                _SIZES['%s%d' % (name, k)] = dict(size=sizes[k], **spec)
        else:
            _SIZES[name] = dict(size=size, **spec)
        return fn
    return wrap


def arr(a):
    return np.asarray(a, np.float64)


def unit(v):
    return fl.unit(v)


def rot(axis, deg):
    """Rotation matrix about 'x', 'y', 'z' or a vector, right-handed, degrees."""
    a = math.radians(deg)
    k = unit({'x': X, 'y': Y, 'z': Z}[axis] if isinstance(axis, str) else axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * (K @ K)


def cells(length, cell):
    return max(1, int(math.ceil(abs(length) / cell - 1e-6)))


def rgb(c, k=1.0):
    return np.clip(arr(c)[:3] * k, 0, None)


def k_of(colour, k):
    """colour times k as RGBA (no clamp but 0.9)."""
    c = np.minimum(arr(colour)[:3] * k, .9)
    return (c[0], c[1], c[2], 1.0)


# ---------------------------------------------------------------- moving and bending what was built

def place(p, start, R=None, t=(0, 0, 0)):
    """Turns (matrix R) then moves everything added since start."""
    v = arr(p.v[start:]).reshape(-1, 3)
    if R is not None:
        v = v @ arr(R).T
    p.v[start:] = (v + arr(t)).tolist()


def warp(p, start, fn):
    """Maps every vertex added since start through fn((n, 3) array) -> (n, 3) array."""
    v = arr(p.v[start:]).reshape(-1, 3)
    if len(v):
        p.v[start:] = arr(fn(v.copy())).tolist()


def batter(p, start, rate, axis=0, inner=0.0, z0=0.0):
    """Leans faces inward with height: what lies beyond `inner` on the axis is drawn toward it by rate per metre of
    height above z0 (as a share of its distance beyond). Inner faces stay plumb."""
    def fn(v):
        d = np.abs(v[:, axis]) - inner
        k = 1 - rate * np.maximum(v[:, 2] - z0, 0)
        v[:, axis] = np.where(d > 0, np.sign(v[:, axis]) * (inner + d * k), v[:, axis])
        return v
    warp(p, start, fn)


def tint(p, start, fn):
    """Multiplies the colours added since start by fn(vertices) (one factor or an RGB per vertex)."""
    v = arr(p.v[start:]).reshape(-1, 3)
    if not len(v):
        return
    c = arr(p.c[start:])
    k = arr(fn(v))
    c[:, :3] *= k[:, None] if k.ndim == 1 else k
    p.c[start:] = c.tolist()


def recolour(p, start, fn):
    """Sets the colours added since start to fn(vertices) -> (n, 3)."""
    v = arr(p.v[start:]).reshape(-1, 3)
    if len(v):
        c = arr(p.c[start:])
        c[:, :3] = fn(v)
        p.c[start:] = c.tolist()


# ---------------------------------------------------------------- geometry

def gquad(p, a, b, c, d, slot, colour, nu=1, nv=1, smooth=False):
    """A patch a-b-c-d (counter-clockwise seen from its front) of nu cells along a->b and nv along a->d."""
    a, b, c, d = (arr(q) for q in (a, b, c, d))
    s = np.linspace(0, 1, nu + 1)[:, None, None]
    t = np.linspace(0, 1, nv + 1)[None, :, None]
    pts = (a * (1 - s) + b * s) * (1 - t) + (d * (1 - s) + c * s) * t
    n = nv + 1
    faces = [[i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1] for i in range(nu) for j in range(nv)]
    return p.add(pts.reshape(-1, 3), faces, colour, slot, smooth)


def face(p, pts, slot, colour, toward=None, smooth=False):
    """One flat polygon, turned to face `toward` (a direction) when given."""
    pts = arr(pts)
    order = list(range(len(pts)))
    if toward is not None:
        n = np.cross(pts, np.roll(pts, -1, 0)).sum(0)
        if np.dot(n, toward) < 0:
            order = order[::-1]
    return p.add(pts, [order], colour, slot, smooth)


def fan(p, centre_pt, ring, slot, colour, toward, centre_colour=None):
    """A triangle fan from a centre to a closed ring of points, facing `toward`."""
    ring = arr(ring)
    n = len(ring)
    pts = np.concatenate([[arr(centre_pt)], ring])
    nrm = np.cross(ring[0] - pts[0], ring[1] - pts[0])
    flip = np.dot(nrm, toward) < 0
    faces = [[0, 1 + (j + 1) % n, 1 + j] if flip else [0, 1 + j, 1 + (j + 1) % n] for j in range(n)]
    cols = np.tile(arr(colour)[:3], (n + 1, 1))
    if centre_colour is not None:
        cols[0] = arr(centre_colour)[:3]
    return p.add(pts, faces, cols, slot, False)


_FACE = {(0, -1): 'x', (0, 1): 'X', (1, -1): 'y', (1, 1): 'Y', (2, -1): 'z', (2, 1): 'Z'}


def gbox(p, lo, hi, slot, colour, cell=1.0, bevel=.03, skip='', edge=.62):
    """An axis-aligned box between corners lo and hi with chamfered arrises, its faces gridded at about `cell` metres
    (one number or one per axis). skip: faces left out, of 'x' (the -x face), 'X' (+x), 'y', 'Y', 'z' (bottom), 'Z'
    (top); the faces round a skipped one run out to its plane unchamfered. The chamfers are darkened by `edge`: the
    joint between two blocks reads as a line. Every face has its own vertices."""
    lo, hi = arr(lo), arr(hi)
    lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
    cell3 = np.broadcast_to(arr(cell), (3,))
    e = np.minimum(bevel, (hi - lo) * .225) if bevel > 0 else np.zeros(3)
    on = {(a, s): _FACE[(a, s)] not in skip for a in range(3) for s in (-1, 1)}
    ext = {-1: lo, 1: hi}
    inn = {-1: lo + e * [on[(a, -1)] for a in range(3)], 1: hi - e * [on[(a, 1)] for a in range(3)]}
    n = [cells(inn[1][a] - inn[-1][a], cell3[a]) for a in range(3)]
    start = len(p.v)
    dark = k_of(colour, edge)
    for a in range(3):
        o0, o1 = (a + 1) % 3, (a + 2) % 3
        for s in (-1, 1):
            if not on[(a, s)]:
                continue
            q = []
            for u, w in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                c = np.zeros(3)
                c[a], c[o0], c[o1] = ext[s][a], inn[u][o0], inn[w][o1]
                q.append(c)
            if s > 0:
                gquad(p, q[0], q[1], q[2], q[3], slot, colour, n[o0], n[o1])
            else:
                gquad(p, q[0], q[3], q[2], q[1], slot, colour, n[o1], n[o0])
    if bevel <= 0:
        return start
    for a in range(3):
        b, k = (a + 1) % 3, (a + 2) % 3
        for sa in (-1, 1):
            for sb in (-1, 1):
                if not (on[(a, sa)] and on[(b, sb)]):
                    continue
                ends = []
                for sk in (-1, 1):
                    ca, cb = np.zeros(3), np.zeros(3)
                    ca[a], ca[b], ca[k] = ext[sa][a], inn[sb][b], inn[sk][k]
                    cb[a], cb[b], cb[k] = inn[sa][a], ext[sb][b], inn[sk][k]
                    ends.append((ca, cb))
                (a0, b0), (a1, b1) = ends
                out = np.zeros(3)
                out[a], out[b] = sa, sb
                if np.dot(np.cross(a1 - a0, b0 - a0), out) < 0:
                    a0, a1, b0, b1 = a1, a0, b1, b0
                gquad(p, a0, a1, b1, b0, slot, dark, n[k], 1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                sg = (sx, sy, sz)
                if not all(on[(a, sg[a])] for a in range(3)):
                    continue
                tri = []
                for a in range(3):
                    c = np.array([inn[sg[b]][b] for b in range(3)])
                    c[a] = ext[sg[a]][a]
                    tri.append(c)
                face(p, tri, slot, dark, arr(sg))
    return start


def bar(p, a, b, w, h, slot, colour, up=Z):
    """A rectangular bar from a to b, w wide (across) and h deep (along up)."""
    a, b = arr(a), arr(b)
    d = unit(b - a)
    side = unit(np.cross(arr(up), d))
    if not np.isfinite(side).all() or np.linalg.norm(side) < .5:
        side = unit(np.cross(X, d))
    u = np.cross(d, side)
    pts = [q + sy * side * w / 2 + sz * u * h / 2 for sz in (-1, 1) for sy in (-1, 1) for q in (a, b)]
    return hexa(p, pts, colour, slot)


def loft(p, rings, slot, colour, caps='', smooth=False, cap_colour=None, inward=False):
    """Sides between successive closed rings of matching points ((m, n, 3)), turned outward; caps: 'b' closes the
    first ring, 't' the last. colour: one, or one per ring ((m, 3 or 4)). inward: the faces look at the axis instead (a
    pit, a bowl)."""
    rings = arr(rings)
    m, n, _ = rings.shape
    faces = [[i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j] for i in range(m - 1) for j in range(n)]
    vol = 0.0
    c0 = rings.reshape(-1, 3).mean(0)
    flat = rings.reshape(-1, 3)
    for f in faces[::max(1, len(faces) // 64)]:
        q = flat[f]
        vol += np.dot(np.cross(q[1] - q[0], q[2] - q[0]) + np.cross(q[2] - q[0], q[3] - q[0]), q.mean(0) - c0)
    if (vol < 0) != inward:
        faces = [f[::-1] for f in faces]
    cols = arr(colour)
    if cols.ndim == 2 and len(cols) == m:
        cols = np.repeat(cols[:, :3], n, 0)
    start = p.add(flat, faces, cols, slot, smooth)
    cc = cap_colour if cap_colour is not None else (colour if arr(colour).ndim == 1 else arr(colour)[0])
    if 'b' in caps:
        face(p, rings[0], slot, cc if cap_colour is not None or arr(colour).ndim == 1 else arr(colour)[0], rings[0].mean(0) - rings[-1].mean(0))
    if 't' in caps:
        face(p, rings[-1], slot, cc if cap_colour is not None or arr(colour).ndim == 1 else arr(colour)[-1], rings[-1].mean(0) - rings[0].mean(0))
    return start


def ngon(r, sides, z=0.0, c=(0, 0), start=0.0, sy=1.0):
    a = start + np.linspace(0, TAU, sides, endpoint=False)
    return np.stack([c[0] + np.cos(a) * r, c[1] + np.sin(a) * r * sy, np.full(sides, float(z))], 1)


def turn(p, profile, slot, colour, sides=24, c=(0, 0, 0), axis='z', smooth=True, start=0.0):
    """lathe() about z, or about x (profile heights then run along +x)."""
    s = len(p.v)
    lathe(p, profile, colour, slot, sides, (0, 0, 0), smooth, start=start)
    place(p, s, rot('y', 90) if axis == 'x' else None, c)
    return s


def gem(p, c, r, half, slot, colour, axis=Z, sides=6, low=None, turn_by=0.0):
    """A faceted double-pointed crystal: a girdle of `sides` round c, points `half` along the axis and `low` (default
    half) against it."""
    c, ax = arr(c), unit(axis)
    a, b = frame(ax)
    ang = turn_by + np.linspace(0, TAU, sides, endpoint=False)
    ring = c + r * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b)
    pts = np.concatenate([ring, [c + ax * half, c - ax * (half if low is None else low)]])
    faces = [[j, (j + 1) % sides, sides] for j in range(sides)] + [[(j + 1) % sides, j, sides + 1] for j in range(sides)]
    return p.add(pts, faces, colour, slot, False)


def lamp(p, c, r, half, glow, axis=Z, band=.3, crystal=CRYSTAL_ICE, sides=6):
    """A light crystal: a glowing girdle (GLOW) between two crystal points (CRYSTAL)."""
    c, ax = arr(c), unit(axis)
    a, b = frame(ax)
    ang = np.linspace(0, TAU, sides, endpoint=False)
    ring = r * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b)
    lo, hi = c - ax * half * band + ring, c + ax * half * band + ring
    p.add(np.concatenate([lo, hi]), [[j, (j + 1) % sides, sides + (j + 1) % sides, sides + j] for j in range(sides)], glow, GLOW, False)
    p.add(np.concatenate([hi, [c + ax * half]]), [[j, (j + 1) % sides, sides] for j in range(sides)], crystal, CRYSTAL, False)
    p.add(np.concatenate([lo, [c - ax * half]]), [[(j + 1) % sides, j, sides] for j in range(sides)], crystal, CRYSTAL, False)


def const(u):
    return lambda z: np.full(np.shape(z), float(u))


def pointed(w, spring, apex):
    """Half width of a tall pointed opening w wide: plumb jambs to `spring`, closing to a point at `apex`."""
    def hw(z):
        s = np.clip((arr(z) - spring) / max(apex - spring, 1e-6), 0, 1)
        return w / 2 * (1 - s ** 1.7)
    return hw


def course(p, rng, along, u0, u1, t0, t1, z0, z1, openings=(), piece=(2.6, 4.4), cell=.8, bevel=.03, skip='',
           colour=STONE_PALE, slot=STONE, jig=(0.0, 0.0), ends=(None, None), spread=.07, edge=.62):
    """One level course of chamfered blocks from u0 to u1 along world 'x' or 'y', t0..t1 across, z0..z1 high. Blocks
    are `piece` metres long (a random length in the range). openings: (centre u, half-width fn of z, sill z, apex z):
    the course is left open there and the blocks beside it are cut to the opening's curve. ends: functions of z for a
    raked or curved end. jig: how far the two long faces stand out of true. skip as gbox's (the end letters only
    apply to the course's two ends)."""
    ax = 0 if along == 'x' else 1
    lows, highs = 'xy'[ax], 'XY'[ax]
    left = ends[0] or const(u0)
    act = sorted((o for o in openings if o[2] < z1 - 1e-6 and o[3] > z0 + 1e-6), key=lambda o: o[0])
    spans = []
    for uc, hw, _, _ in act:
        spans.append((left, (lambda z, uc=uc, hw=hw: uc - hw(z))))
        left = (lambda z, uc=uc, hw=hw: uc + hw(z))
    spans.append((left, ends[1] or const(u1)))
    zz = np.array([z0, z1])
    start = len(p.v)
    for si, (fa, fb) in enumerate(spans):
        ua, ub = float(np.min(fa(zz))), float(np.max(fb(zz)))
        if ub - ua < .04:
            continue
        n = max(1, int(round((ub - ua) / rng.uniform(*piece))))
        cuts = np.linspace(ua, ub, n + 1)
        if n > 1:
            cuts[1:-1] += rng.uniform(-.22, .22, n - 1) * (ub - ua) / n
        for k in range(n):
            sk = ''.join(ch for ch in skip if ch not in lows + highs)
            if si == 0 and k == 0 and lows in skip:
                sk += lows
            if si == len(spans) - 1 and k == n - 1 and highs in skip:
                sk += highs
            lo, hi = [0.0, 0.0, z0], [0.0, 0.0, z1]
            lo[ax], hi[ax] = cuts[k], cuts[k + 1]
            lo[1 - ax], hi[1 - ax] = t0 + rng.uniform(-1, 1) * jig[0], t1 + rng.uniform(-1, 1) * jig[1]
            s = gbox(p, lo, hi, slot, vary(rng, colour, spread), cell, bevel, sk, edge)
            v = arr(p.v[s:])
            z = np.clip(v[:, 2], z0, z1)
            f = (v[:, ax] - ua) / (ub - ua)
            a, b = fa(z), fb(z)
            v[:, ax] = a + f * (b - a)
            p.v[s:] = v.tolist()
    return start


def pane(p, along, uc, hw, zs, za, t, colour=CRYSTAL_ICE, slot=CRYSTAL, thick=.04):
    """The crystal that fills a pointed opening: a thin sheet at t across the wall."""
    ax = 0 if along == 'x' else 1
    w0 = float(np.max(hw(np.array([zs, za]))))
    lo, hi = [0.0, 0.0, zs], [0.0, 0.0, za]
    lo[ax], hi[ax] = uc - w0, uc + w0
    lo[1 - ax], hi[1 - ax] = t - thick / 2, t + thick / 2
    s = gbox(p, lo, hi, slot, colour, (.3, .3, .18), 0)

    def fn(v):
        v[:, ax] = uc + (v[:, ax] - uc) / w0 * np.maximum(hw(v[:, 2]), .006)
        return v
    warp(p, s, fn)
    tint(p, s, lambda v: .75 + .25 * (v[:, 2] - zs) / (za - zs))
    return s


def tiles(p, rng, A, B, C, D, tile=(.42, .5), lift=.035, colours=(TILE_DEEP, TILE_TEAL), slot=TILE):
    """A roof face laid in rows of glazed tiles: eave A->B, ridge D->C (A-D and B-C are its sides; C may equal D).
    Each row's lower edge stands `lift` proud of the row below, with its butt end modelled."""
    A, B, C, D = (arr(q) for q in (A, B, C, D))
    n = np.cross(B - A, (D + C) / 2 - (A + B) / 2)
    if n[2] < 0:
        A, B, C, D = B, A, D, C
        n = -n
    n = unit(n)
    rows = cells(np.linalg.norm((D + C) / 2 - (A + B) / 2), tile[1])
    c0, c1 = rgb(colours[0]), rgb(colours[1])
    u = unit(B - A)
    O = (A + B) / 2
    tw = tile[0]
    start = len(p.v)
    for j in range(rows):
        t0, t1 = j / rows, (j + 1) / rows
        L0, R0, L1, R1 = A + (D - A) * t0, B + (C - B) * t0, A + (D - A) * t1, B + (C - B) * t1
        l0, r0, l1, r1 = (L0 - O) @ u, (R0 - O) @ u, (L1 - O) @ u, (R1 - O) @ u
        P0, P1 = L0 - l0 * u, L1 - l1 * u + n * .004
        off = (j % 2) * tw / 2 + rng.uniform(-.04, .04)
        b = np.arange(math.floor((min(l0, l1) - off) / tw) * tw + off, max(r0, r1) + tw, tw)
        verts, faces, cols = [], [], []
        for b0, b1 in zip(b[:-1], b[1:]):
            a0, a1, e0, e1 = np.clip([b0, b1], l0, r0).tolist() + np.clip([b0, b1], l1, r1).tolist()
            wl, wh = a1 - a0 > 2e-3, e1 - e0 > 2e-3
            if not (wl or wh):
                continue
            mk = rng.uniform(0, 1) ** 2 * .55
            tc = (c0 * (1 - mk) + c1 * mk) * rng.uniform(.75, 1.15)
            k = len(verts)
            if wl and wh:
                verts += [P0 + a0 * u + n * lift, P0 + a1 * u + n * lift, P1 + e1 * u, P1 + e0 * u]
                cols += [tc * .8, tc * .8, tc, tc]
                faces.append([k, k + 1, k + 2, k + 3])
            elif wl:
                verts += [P0 + a0 * u + n * lift, P0 + a1 * u + n * lift, P1 + e0 * u]
                cols += [tc * .8, tc * .8, tc]
                faces.append([k, k + 1, k + 2])
            else:
                verts += [P0 + a0 * u + n * lift, P1 + e1 * u, P1 + e0 * u]
                cols += [tc * .8, tc, tc]
                faces.append([k, k + 1, k + 2])
            if wl:
                k = len(verts)
                verts += [P0 + a0 * u, P0 + a1 * u, P0 + a1 * u + n * lift, P0 + a0 * u + n * lift]
                cols += [tc * .45] * 4
                faces.append([k, k + 1, k + 2, k + 3])
        if verts:
            p.add(verts, faces, np.minimum(arr(cols), .9), slot, False)
    return start


def hip_roof(p, rng, x0, x1, hy, z0, z1, ridge, tile=(.42, .5), cap_slot=TILE, cap_colour=None):
    """A hipped tiled roof over the eave rectangle x0..x1 by -hy..hy at z0, its ridge along x (half length `ridge`
    about the middle, 0 for a pyramid) at z1, with rolled caps on the hips and the ridge."""
    cx = (x0 + x1) / 2
    r0, r1 = (cx - max(ridge, .03), 0, z1), (cx + max(ridge, .03), 0, z1)
    e = {(-1, -1): (x0, -hy, z0), (1, -1): (x1, -hy, z0), (1, 1): (x1, hy, z0), (-1, 1): (x0, hy, z0)}
    tiles(p, rng, e[(1, 1)], e[(-1, 1)], r0, r1, tile)
    tiles(p, rng, e[(-1, -1)], e[(1, -1)], r1, r0, tile)
    tiles(p, rng, e[(1, -1)], e[(1, 1)], r1, r1, tile)
    tiles(p, rng, e[(-1, 1)], e[(-1, -1)], r0, r0, tile)
    cc = cap_colour if cap_colour is not None else k_of(TILE_DEEP, .8)
    for (sx, sy), q in e.items():
        tube(p, [arr(q) + (0, 0, .03), arr(r1 if sx > 0 else r0) + (0, 0, .05)], .075, cc, cap_slot, 6)
    if ridge > .05:
        tube(p, [arr(r0) + (0, 0, .05), arr(r1) + (0, 0, .05)], .09, cc, cap_slot, 6)
    return r0, r1


def tile_lathe(p, rng, profile, sides, colours=(TILE_DEEP, TILE_TEAL), slot=TILE, c=(0, 0, 0)):
    """A turned surface laid in separate glazed tiles (profile as lathe()'s): every tile its own tone."""
    profile = arr(profile)
    ang = np.linspace(0, TAU, sides + 1)
    c0, c1 = rgb(colours[0]), rgb(colours[1])
    start = len(p.v)
    for (ra, za), (rb, zb) in zip(profile[:-1], profile[1:]):
        lo = np.stack([np.cos(ang) * ra, np.sin(ang) * ra, np.full(sides + 1, za)], 1) + arr(c)
        hi = np.stack([np.cos(ang) * rb, np.sin(ang) * rb, np.full(sides + 1, zb)], 1) + arr(c)
        mixk = rng.uniform(0, 1, sides)[:, None] ** 2 * .6
        tc = (c0 * (1 - mixk) + c1 * mixk) * rng.uniform(.7, 1.15, sides)[:, None]
        verts = np.concatenate([lo[:-1], lo[1:], hi[1:], hi[:-1]])
        i = np.arange(sides)
        p.add(verts, [[a, sides + a, 2 * sides + a, 3 * sides + a] for a in i], np.concatenate([tc] * 4), slot, False)
    return start


def lichen(p, rng, c, r, normal=Z, h=.006, n=9):
    """A lichen crust: a thin irregular patch lying on a face."""
    a, b = frame(normal)
    ang = np.linspace(0, TAU, n, endpoint=False) + rng.uniform(0, 1)
    rr = r * rng.uniform(.55, 1.0, n)
    c = arr(c) + unit(normal) * h
    ring = c + rr[:, None] * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b)
    col = mix(LICHEN_FROST, LICHEN_DEEP, rng.uniform(0, .6))
    fan(p, c, ring, LICHEN, k_of(col, .8), arr(normal), col)


def lichens(p, rng, x, y, z, count, r=(.12, .4), normal=Z):
    """Lichen crusts scattered on a flat: x and y are (lo, hi) ranges (or z, for a wall given by its normal)."""
    for _ in range(count):
        lichen(p, rng, (rng.uniform(*x) if np.ndim(x) else x, rng.uniform(*y) if np.ndim(y) else y, rng.uniform(*z) if np.ndim(z) else z),
               rng.uniform(*r), normal)


def chunk(p, rng, half, cuts=4, cell=.3, colour=STONE_PALE, keep=.15, depth=(.45, .8), allow=None):
    """A broken block: a chamfered box of half extents `half` cut by random planes (each vertex beyond a plane is
    drawn back onto it toward the block's centre, so the grid keeps its topology and nothing folds; the vertices just
    short of it slide along their face onto the cut's edge). The +x face is
    the dressed one: the planes lean away from it. Returns (start, planes) with planes as (normal, distance)."""
    half = arr(half)
    f0 = len(p.f)
    start = gbox(p, -half, half, STONE, colour, cell, .03, '', .75)
    v = arr(p.v[start:])
    axis = np.argmax(np.abs(v) / half, 1)
    m = np.zeros_like(v)                                     # the face each vertex lies on, by its normal
    m[np.arange(len(v)), axis] = np.sign(v[np.arange(len(v)), axis])
    reach = .7 * float(np.min(np.broadcast_to(arr(cell), (3,))))
    planes = []
    for k in range(cuts):
        for _ in range(40):
            n = unit(rng.normal(0, 1, 3))
            if allow is None or allow(n):
                break
        if allow is None:
            n[0] = min(n[0], keep)
            n = unit(n)
        d = rng.uniform(*depth) * float((np.abs(n) * half).sum())
        dv = v @ n
        beyond = dv > d
        # vertices just short of the plane slide along their own face onto the cut's edge, so the break runs through
        # vertices instead of zigzagging across the grid
        g = n - (m @ n)[:, None] * m
        gl = np.maximum(np.linalg.norm(g, axis=1), 1e-9)
        dist = (d - dv) / gl
        near = ~beyond & (dist < reach) & (gl > .25)
        v[near] += (g[near] / gl[near, None]) * dist[near, None]
        v[beyond] *= (d / dv[beyond])[:, None]
        m[beyond] = n
        planes.append((n, d))
    p.v[start:] = v.tolist()
    full = arr(p.v)
    for i in range(len(p.f) - 1, f0 - 1, -1):                # faces the cuts closed up
        q = full[p.f[i]]
        if np.linalg.norm(np.cross(q[1] - q[0], q[2] - q[0])) < 1e-9 and (len(q) == 3 or np.linalg.norm(np.cross(q[2] - q[0], q[3] - q[0])) < 1e-9):
            del p.f[i], p.m[i], p.s[i]
        elif len(q) == 4 and np.linalg.norm(np.cross(q[1] - q[0], q[2] - q[0])) < 1e-9:
            p.f[i] = [p.f[i][0], p.f[i][2], p.f[i][3]]
    return start, planes


def on_plane(v, plane, eps=1e-6):
    return np.abs(v @ plane[0] - plane[1]) < eps


def hull2(pts):
    """Convex hull of 2-D points, counter-clockwise."""
    pts = sorted(set(map(tuple, np.round(pts, 6))))
    if len(pts) < 3:
        return np.array(pts)

    def half(points):
        out = []
        for q in points:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (q[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (q[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(q)
        return out
    lower, upper = half(pts), half(pts[::-1])
    return np.array(lower[:-1] + upper[:-1])


def fracture(p, rng, start, planes, glow=GLOW_VIGIL, scorch=True, rough=.035, seed=0):
    """Dresses a chunk's cut faces as fractures: rough and dark, and the largest of them scorched and lit from within
    (a ragged GLOW patch on it, brightest at its heart)."""
    v = arr(p.v[start:])
    c = arr(p.c[start:])
    best, area = None, 0.0
    outlines = {}
    for i, pl in enumerate(planes):
        m = on_plane(v, pl)
        if m.sum() < 3:
            continue
        a, b = frame(pl[0])
        q = v[m]
        h = hull2(np.stack([q @ a, q @ b], 1))
        if len(h) < 3:
            continue
        ar = .5 * abs(np.sum(h[:, 0] * np.roll(h[:, 1], -1) - h[:, 1] * np.roll(h[:, 0], -1)))
        outlines[i] = (h, a, b)
        if ar > area:
            best, area = i, ar
    for i, pl in enumerate(planes):
        m = on_plane(v, pl)
        if not m.any():
            continue
        nz = .5 + .5 * noise2(v[m, 0] * 5.1 + v[m, 2] * 3.3 + i, v[m, 1] * 5.1 - v[m, 2] * 2.9, seed + 31 + i)
        if i == best and scorch:
            c[m, :3] = rgb(mix(STONE_DARK, CLOTH_VIOLET, .3)) * (.6 + .5 * nz[:, None])
        else:
            c[m, :3] = rgb(STONE_SHADE) * (.7 + .5 * nz[:, None])
            v[m] *= (1 - rough * nz)[:, None]
    p.v[start:] = v.tolist()
    p.c[start:] = c.tolist()
    if best is None:
        return None
    h, a, b = outlines[best]
    n, d = planes[best]
    mid = h.mean(0)
    k = 16
    ang = np.linspace(0, TAU, k, endpoint=False) + rng.uniform(0, 1)
    ring = []
    for t in ang:
        dr = np.array([math.cos(t), math.sin(t)])
        reach = 1e9
        for q0, q1 in zip(h, np.roll(h, -1, 0)):
            e = q1 - q0
            den = dr[0] * e[1] - dr[1] * e[0]
            if abs(den) < 1e-12:
                continue
            w = q0 - mid
            s = (w[0] * e[1] - w[1] * e[0]) / den
            u = (w[0] * dr[1] - w[1] * dr[0]) / den
            if s > 0 and -1e-9 <= u <= 1 + 1e-9:
                reach = min(reach, s)
        ring.append(mid + dr * reach * rng.uniform(.35, .82))
    ring = arr(ring)
    origin = n * (d + .008)
    pts = origin + ring[:, :1] * a + ring[:, 1:] * b
    fan(p, origin + mid[0] * a + mid[1] * b, pts, GLOW, k_of(glow, .45), n, glow)
    return n, d


# ---------------------------------------------------------------- weather and finishing

def normals_of(p):
    v = arr(p.v).reshape(-1, 3)
    n = np.zeros_like(v)
    by_len = {}
    for f in p.f:
        by_len.setdefault(len(f), []).append(f)
    for length, fs in by_len.items():
        F = np.asarray(fs, np.int64)
        Q = v[F]
        nrm = np.cross(Q, np.roll(Q, -1, 1)).sum(1)
        for j in range(length):
            np.add.at(n, F[:, j], nrm)
    return v, unit(n)


def weather(p, seed=0, ground=0.0, reach=2.2, lichen_k=.45, dust=.3, floor=.62, north=NORTH):
    """Ages the colours by place and normal. Stone and rock: blotches, damp darkening toward `ground` (None for what
    hovers), runs down walls, dark soffits, lichen on tops and the north side, dust on flats. Metal, tile and crystal:
    a little grime. Light keeps its colour."""
    v, n = normals_of(p)
    c = arr(p.c)
    slot = np.zeros(len(v), np.int64)
    for f, m in zip(p.f, p.m):
        for i in f:
            slot[i] = m
    names = np.array(p.slots)[slot]
    x, y, z = v.T
    nz = n[:, 2]
    b1 = .5 + .5 * noise2(x / 2.3 + z * .31 + 3.1, y / 2.3 - z * .27 + 7.7, seed + 1)
    b2 = .5 + .5 * noise2(x / .45 + z * 1.3, y / .45 - z * 1.1, seed + 2)
    g = np.clip(1 - (z - ground) / reach, 0, 1) if ground is not None else np.zeros(len(v))
    s = y * n[:, 0] - x * n[:, 1]
    wall = np.abs(nz) < .6
    st = np.maximum(0, noise2(s * 2.3 + seed * .71, z * .11 + 1.7, seed + 5)) * wall
    up = np.clip((nz - .5) / .4, 0, 1)
    facing = np.clip(n[:, 0] * north[0] + n[:, 1] * north[1], 0, 1)
    out = c[:, :3].copy()
    stone = (names == STONE) | (names == ROCK)
    k = (1 - .2 * b1 - .1 * b2) * (floor + (1 - floor) * (1 - g ** 1.5)) * (1 - .22 * st) * np.where(nz < -.6, .7, 1.0) * np.where(nz > .6, 1.05, 1.0)
    rgbs = out * k[:, None]
    m = lichen_k * (up * np.clip(noise2(x / 1.7 + 9.0, y / 1.7, seed + 8) * 1.6 - .2, 0, 1) * .7 +
                    (1 - up) * (facing * np.clip(b1 * 1.9 - .65, 0, 1) + .5 * g ** 2 * b2 * (.3 + facing)))
    m = np.clip(m, 0, .8)[:, None]
    lc = rgb(LICHEN_FROST) * (1 - .55 * b2[:, None]) + rgb(LICHEN_DEEP) * (.55 * b2[:, None])
    rgbs = rgbs * (1 - m) + lc * m
    dk = (dust * up * np.clip(noise2(x / 3.1 + 5.0, y / 3.1 + 2.0, seed + 9) * 1.3, 0, 1) * .55)[:, None]
    rgbs = rgbs * (1 - dk) + rgb(DUST) * dk
    out[stone] = rgbs[stone]
    metal = (names == ALLOY) | (names == ELECTRUM) | (names == ENAMEL)
    km = (1 - .2 * b1) * (1 - .12 * b2) * (1 - .15 * g) * np.where(nz < -.6, .8, 1.0) * (1 - .15 * st)
    out[metal] = (out * km[:, None])[metal]
    soft = (names == TILE) | (names == CRYSTAL) | (names == LICHEN) | (names == CLOTH)
    ks = (1 - .16 * b1) * (1 - .12 * g)
    out[soft] = (out * ks[:, None])[soft]
    lit = names == GLOW
    out[~lit] = np.clip(out[~lit], 0, .9)
    c[:, :3] = out
    p.c = c.tolist()


def done(p, seed=0, pivot='base', ground=0.0, facts=None, **kw):
    """Ends a builder: weathers the mesh, centres what hovers, checks that nothing sank under the pivot plane."""
    if pivot == 'centre':
        centre(p)
        ground = None
    weather(p, seed, ground, **kw)
    z = arr(p.v)[:, 2].min()
    if pivot == 'base' and abs(z) > .02:
        raise ValueError('%s: lowest point at z %.3f, the builder should stand it on z 0' % (p.name, z))
    if facts is not None:
        FACTS[p.name] = facts
    return p


# ---------------------------------------------------------------- shared pieces

def inlay(p, a, b, w=.05, proud=.006, normal=X, colour=ELECTRUM_PALE):
    """One straight line of electrum inlay from a to b on a face with the given normal."""
    n = unit(normal)
    return bar(p, a, b, w, 2 * proud, ELECTRUM, colour, up=n)


def column12(p, rng, c, R, h, band=True, upto=None, sides=12):
    """A First One column standing on c: a twelve-sided plinth 2R across, a slightly tapering twelve-sided shaft in
    drums, a plain flared head and its abacus (2R across) at height h, one electrum band under the head. upto cuts it
    off (no head) at that height. Returns the shaft radius at its top."""
    r0, r1 = .74 * R, .6 * R
    hp = .3 * R
    z_sh = hp + .22 * R
    zs = h - 1.5 * R
    zf = h - .36 * R
    base_c, joint_c = rgb(STONE_PALE), rgb(STONE_SHADE) * .7
    prof = [(R, 0, 1.0), (R, hp - .03, 1.0), (R - .03, hp, .8), (.87 * R, hp, .7), (.87 * R, hp + .1 * R, 1.0), (r0, z_sh, .9)]

    def r_at(z):
        t = np.clip((z - z_sh) / (zs - z_sh), 0, 1)
        return r0 + (r1 - r0) * t + .012 * R * math.sin(math.pi * t)
    nd = max(2, int(round((zs - z_sh) / (1.75 * R))))
    for k in range(nd):
        za, zb = z_sh + (zs - z_sh) * k / nd, z_sh + (zs - z_sh) * (k + 1) / nd
        tone_k = rng.uniform(.9, 1.06)
        if k:
            prof.append((r_at(za), za + .02, tone_k))
        for t in (.33, .66):
            zm = za + (zb - za) * t
            prof.append((r_at(zm), zm, tone_k))
        if k < nd - 1:
            prof += [(r_at(zb), zb - .02, tone_k), (r_at(zb) - .014, zb, -1)]
    prof.append((r1, zs, 1.0))
    for s_ in np.linspace(0, 1, 7)[1:]:
        prof.append((r1 + (.96 * R - r1) * s_ ** 2.3, zs + (zf - zs) * s_, 1.0))
    prof += [(R, zf + .025, .8), (R, h - .03, 1.02), (R - .03, h, .85)]
    top_r = None
    if upto is not None:
        keep = [q for q in prof if q[1] < upto - .03]
        top_r = r_at(upto)
        prof = keep + [(top_r, upto, 1.0)]
    cols = np.repeat(np.array([joint_c if q[2] < 0 else base_c * q[2] for q in prof]), sides, 0)
    lathe(p, [(q[0], q[1]) for q in prof], cols, STONE, sides, c, False)
    if upto is None:
        face(p, ngon(R - .03, sides, h) + arr(c) * (1, 1, 1) * (1, 1, 0) + (0, 0, c[2]), STONE, STONE_PALE, Z)
        if band:
            zb0, zb1 = zs - .95 * R, zs - .7 * R
            lathe(p, [(r_at(zb0), zb0), (r_at(zb0) + .016, zb0 + .012), (r_at(zb1) + .016, zb1 - .012), (r_at(zb1), zb1)], ELECTRUM_PALE,
                  ELECTRUM, sides, c, False)
    return top_r if upto is not None else r1


# ---------------------------------------------------------------- the weave pieces

@mesh('SM_AN_Span', (32.0, 6.0, 3.5), pivot='any', tol=.02)
def span():
    """The Sundered Span. A deck 32 m long whose top is one flat face at z 0, 5 m clear between two parapets 0.9 m
    high pierced with pointed slits; beneath it three parallel parabolic ribs of voussoirs spring from the two end
    blocks at z -2.6 and rise to meet the deck at mid-span, with spandrel posts and alloy ties between them."""
    rng = np.random.default_rng(5101)
    p = Part('SM_AN_Span', (STONE, ELECTRUM, ALLOY))
    s = gquad(p, (-16, -2.5, 0), (16, -2.5, 0), (16, 2.5, 0), (-16, 2.5, 0), STONE, STONE_PALE, 80, 12)
    worn = rgb(STONE_WORN) / rgb(STONE_PALE)
    tint(p, s, lambda v: 1 + (worn - 1) * (np.exp(-(v[:, 1] / 1.5) ** 2) * (.6 + .4 * noise2(v[:, 0] / 1.3, v[:, 1] / 1.3, 77)))[:, None])
    # the paving's joints, in colour only (the face stays flat): slabs 2 m long
    tint(p, s, lambda v: 1 - .16 * (np.abs(((v[:, 0] + 16) % 2.0) - 1.0) > .97))
    for x0 in np.arange(-16, 16, 4.0):                       # the deck's slabs: joints show on the fascia and the soffit
        gbox(p, (x0, -3, -.5), (x0 + 4, 3, 0), STONE, vary(rng, STONE_PALE, .06), (1.0, 1.0, .5), .035, 'Z')
    for sy in (-1, 1):
        t0, t1 = (2.5, 2.98) if sy > 0 else (-2.98, -2.5)
        slit = pointed(.16, .5, .72)
        openings = [(uc, slit, .2, .72) for uc in np.arange(-15, 15.1, 2.0)]
        course(p, rng, 'x', -16, 16, t0, t1, 0, .2, piece=(3.6, 4.4), cell=(1.0, .5, .2), skip='z')
        course(p, rng, 'x', -16, 16, t0, t1, .2, .72, openings, cell=(.5, .5, .13), bevel=.025, skip='')
        course(p, rng, 'x', -16, 16, t0 if sy > 0 else -3.0, 3.0 if sy > 0 else t1, .72, .9, piece=(3.6, 4.4), cell=(1.0, .5, .2), bevel=.04)
        inlay(p, (-15.9, 2.5 * sy, .1), (15.9, 2.5 * sy, .1), .035, .004, -Y * sy)
        inlay(p, (-15.9, 2.0 * sy, 0), (15.9, 2.0 * sy, 0), .08, .005, Z)

    def soffit(x):
        return -.78 - 1.82 * (x / 15.6) ** 2
    nv = 17
    for ry in (-2.0, 0.0, 2.0):
        cuts = np.linspace(-15.6, 15.6, nv + 1)
        for k in range(nv):
            s = gbox(p, (cuts[k], ry - .28, 0), (cuts[k + 1], ry + .28, .5), STONE, vary(rng, STONE_PALE, .08), (.95, .6, .5), .035)
            warp(p, s, lambda v: v + np.stack([0 * v[:, 0], 0 * v[:, 0], soffit(v[:, 0])], 1))
        for px in (6.6, 8.6, 10.6, 12.6, 14.4):
            for sx in (-1, 1):
                top = soffit(px) + .48
                if top < -.56:
                    gbox(p, (sx * px - .17, ry - .2, top), (sx * px + .17, ry + .2, -.47), STONE, vary(rng, STONE_SHADE, .08), .5, .03)
    for sx in (-1, 1):                                       # the springers
        gbox(p, (sx * 15.6, -3, -2.6), (sx * 16.0, 3, -.47), STONE, vary(rng, STONE_PALE, .05), .7, .04)
        gbox(p, (sx * 15.2, -3, -1.1), (sx * 15.62, 3, -.47), STONE, vary(rng, STONE_SHADE, .05), .7, .04)
    for px in (0.0, 4.4, 8.6, 12.6):                         # alloy ties through the three ribs
        for sx in ((1,) if px == 0 else (-1, 1)):
            zt = soffit(px) + .25
            tube(p, [(sx * px, -2.42, zt), (sx * px, 2.42, zt)], .045, ALLOY_SILVER, ALLOY, 8)
            for ry in (-2.0, 0.0, 2.0):
                for sy in (-1, 1):
                    bevel_box(p, (sx * px, ry + sy * .3, zt), (.1, .025, .1), ALLOY_DARK, ALLOY, .012)
    return done(p, 5101, 'any', None, facts=dict(deck_top=0.0, x=(-16.0, 16.0), clear_y=(-2.5, 2.5), parapet=.9, ribs_to=-2.6))


@mesh('SM_AN_Stair', (18.0, 9.0, 13.1), tol=.02)
def stair():
    """The grand stair, climbing toward +x: forty risers of 0.3 m on treads 0.4 m deep from the foot at x -9 to the
    landing (x 7 to 9, z 12.0 exactly), 8 m clear between two cheek walls laid in level courses under a raked coping
    0.8 m above the nosings (1.1 m above the landing), each ending at the foot in a pier with a crystal in its head.
    Solid: the cheeks run to the ground, the back and the bottom
    are closed."""
    rng = np.random.default_rng(5102)
    p = Part('SM_AN_Stair', (STONE, ELECTRUM, CRYSTAL))
    N, run, rise = 40, .4, .3
    prof = [(-9.0, 0.0)]
    for i in range(N):
        x, z = -9 + run * i, rise * (i + 1)
        prof += [(x, z - .02), (x + .02, z), (x + run, z)]
    prof += [(x_, 12.0) for x_ in (7.4, 7.8, 8.2, 8.6, 9.0)]
    prof = arr(prof)
    ny = 16
    ys = np.linspace(-4.0, 4.0, ny + 1)
    ys[0], ys[-1] = -4.02, 4.02                               # under the cheeks' inner faces, which stand a little out of true
    pts = np.stack([np.repeat(prof[:, 0], ny + 1), np.tile(ys, len(prof)), np.repeat(prof[:, 1], ny + 1)], 1)
    n = ny + 1
    faces = [[k * n + j, (k + 1) * n + j, (k + 1) * n + j + 1, k * n + j + 1] for k in range(len(prof) - 1) for j in range(ny)]
    s = p.add(pts, faces, STONE_PALE, STONE, False)
    worn = rgb(STONE_WORN) / rgb(STONE_PALE)

    def tread_tone(v):
        step = np.floor((v[:, 0] + 9.001) / run)
        wear = np.exp(-(v[:, 1] / 2.2) ** 2) * (.55 + .45 * noise2(v[:, 0] / .9, v[:, 1] / .9, 21))
        per = .93 + .12 * (noise2(step * 1.7, step * .3, 22) * .5 + .5)
        return (1 + (worn - 1) * wear[:, None]) * per[:, None]
    tint(p, s, tread_tone)
    gquad(p, (9, -4, 0), (9, 4, 0), (9, 4, 12), (9, -4, 12), STONE, k_of(STONE_SHADE, .9), 8, 12)        # the back, against the cliff
    gquad(p, (-9, -4.5, 0), (-9, 4.5, 0), (9, 4.5, 0), (9, -4.5, 0), STONE, k_of(STONE_SHADE, .6), 9, 9)   # the bottom

    def rake(z):
        return np.maximum(-9.0, (arr(z) - .95) / .75 - 9.0)
    levels = [0.0, .95] + [.95 + .6 * k for k in range(1, 21)]
    for sy in (-1, 1):
        t0, t1 = (4.0, 4.5) if sy > 0 else (-4.5, -4.0)
        jig = (.008, 0.0) if sy > 0 else (0.0, .008)
        for z0, z1 in zip(levels[:-1], levels[1:]):
            course(p, rng, 'x', -9, 9, t0, t1, z0, z1, ends=(rake, None), piece=(2.4, 3.8), cell=(.9, .5, .6), bevel=.03,
                   skip='z' if z0 == 0 else '', jig=jig)
        for x0 in np.arange(-9, 7, 2.0):                      # the raked coping, then its level run over the landing
            s = gbox(p, (x0, t0, 0), (x0 + 2, t1, .15), STONE, vary(rng, STONE_PALE, .05), (1.0, .5, .2), .035)
            warp(p, s, lambda v: v + np.stack([0 * v[:, 0], 0 * v[:, 0], .75 * (v[:, 0] + 9) + .95], 1))
        gbox(p, (7, t0, 12.95), (9, t1, 13.1), STONE, vary(rng, STONE_PALE, .05), (1.0, .5, .2), .035)
        # the foot pier: a block standing proud of the rake, a crystal set in its head
        gbox(p, (-9, t0, 0), (-8.25, t1, 1.75), STONE, vary(rng, STONE_PALE, .04), (.4, .5, .6), .04, 'z')
        gbox(p, (-9, t0, 1.75), (-8.25, t1, 1.92), STONE, vary(rng, STONE_PALE, .04), (.4, .5, .2), .05)
        inlay(p, (-9, sy * 4.25, .5), (-9, sy * 4.25, 1.6), .04, .005, -X)
        gem(p, (-8.625, sy * 4.25, 2.02), .13, .2, CRYSTAL, CRYSTAL_ICE, Z, 6, low=.12)
        # one raked line of inlay on the cheek's inner face, 0.45 m above the nosings
        yi = 4.0 * sy
        inlay(p, (-8.7, yi, .75 * .3 + 1.05), (6.9, yi, .75 * 15.9 + 1.05), .05, .005, -Y * sy)
        inlay(p, (6.9, yi, .75 * 15.9 + 1.05), (8.9, yi, .75 * 15.9 + 1.05), .05, .005, -Y * sy)
    return done(p, 5102, facts=dict(foot=(-9.0, 0.0), landing=dict(z=12.0, x=(7.0, 9.0)), clear_y=(-4.0, 4.0), risers=N, rise=rise, tread=run,
                                    cheek_top=13.1))


def slab_keel(p, rng, lo, hi, cuts, cell, depth):
    """The broken underside of a floating slab: a block from lo to hi (its top hidden in the slab above) whose lower
    edges and corners are cut away by fracture planes; its deepest point is drawn down to exactly lo's z."""
    lo, hi = arr(lo), arr(hi)
    mid, half = (lo + hi) / 2, (hi - lo) / 2
    s, planes = chunk(p, rng, half, cuts, cell, STONE_SHADE, depth=depth, allow=lambda n: n[2] < -.25 and abs(n[2]) < .9)
    v = arr(p.v[s:])
    c = arr(p.c[s:])
    for i, pl in enumerate(planes):
        m = on_plane(v, pl)
        nz = .5 + .5 * noise2(v[m, 0] * 3.1 + i, v[m, 1] * 3.1, 40 + i)
        c[m, :3] = rgb(STONE_SHADE) * (.55 + .5 * nz[:, None])
        v[m] *= (1 - .06 * nz)[:, None]
    low = v[:, 2] < -half[2] + 1e-6                          # the bed it was torn from: uneven
    v[low, 2] += .28 * half[2] * (.5 + .5 * noise2(v[low, 0] * 1.9, v[low, 1] * 1.9, 61)) * np.clip(noise2(v[low, 0] * .6 + 4, v[low, 1] * .6, 62) + .6, 0, 1)
    c[low, :3] = rgb(STONE_SHADE) * (.5 + .4 * (.5 + .5 * noise2(v[low, 0] * 3.3, v[low, 1] * 3.3, 63)))[:, None]
    zmin = v[:, 2].min()
    v[:, 2] = np.where(v[:, 2] < 0, v[:, 2] * (half[2] / -zmin), v[:, 2])
    p.v[s:] = (v + mid).tolist()
    p.c[s:] = c.tolist()
    return s


@mesh('SM_AN_StepSlab', (3.2, 3.2, .7), pivot='any', tol=.02)
def step_slab():
    """A floating stepping slab: a hexagonal paving stone 3.2 m across (drawn out a little on y so it fills 3.2 by
    3.2), its top one flat face at z 0 with a hexagon of inlay, a dressed edge course 0.26 m deep and under it the
    broken core of the pavement it was unwoven from."""
    rng = np.random.default_rng(5103)
    p = Part('SM_AN_StepSlab', (STONE, ELECTRUM))
    sy = 1.6 / (1.6 * math.sin(math.radians(60)))
    sub = 4

    def hexring(r, z, noise=0.0):
        corners = ngon(r, 6, z, sy=sy)
        pts = []
        for a, b in zip(corners, np.roll(corners, -1, 0)):
            for k in range(sub):
                pts.append(a + (b - a) * k / sub)
        pts = arr(pts)
        if noise:
            pts[:, :2] *= (1 + noise * rng.uniform(-1, 1, len(pts)))[:, None]
            pts[:, 2] += noise * .25 * rng.uniform(-1, 1, len(pts))
        return pts
    # the top: rings of one flat face
    top = [hexring(r, 0.0) for r in (1.56, 1.15, .6)]
    loft(p, top, STONE, STONE_PALE)
    fan(p, (0, 0, 0), top[-1], STONE, STONE_WORN, Z)
    loft(p, [hexring(1.6, -.04), hexring(1.56, 0.0)], STONE, k_of(STONE_PALE, .7))
    loft(p, [hexring(1.6, -.26), hexring(1.6, -.15), hexring(1.6, -.04)], STONE, STONE_PALE)
    under = [hexring(1.6, -.26), hexring(1.52, -.29), hexring(1.3, -.36, .05), hexring(.95, -.5, .1), hexring(.5, -.63, .16)]
    cols = [rgb(STONE_PALE) * .7, rgb(STONE_SHADE), rgb(STONE_SHADE) * .8, rgb(STONE_SHADE) * .65, rgb(STONE_DARK) * 1.6]
    loft(p, under, STONE, cols)
    fan(p, (.05, -.04, -.7), under[-1], STONE, k_of(STONE_DARK, 1.5), -Z)
    a, b = hexring(1.2, .005), hexring(1.14, .005)
    for j in range(len(a)):
        k = (j + 1) % len(a)
        face(p, [a[j], a[k], b[k], b[j]], ELECTRUM, ELECTRUM_PALE, Z)
    return done(p, 5103, 'any', None, facts=dict(top=0.0, across=3.2))


@mesh('SM_AN_Causeway', (9.0, 3.4, 1.0), pivot='any', tol=.02)
def causeway():
    """A causeway slab along x, 9 by 3.4 m: its top one flat face at z 0 with a line of inlay down each side, three
    dressed paving blocks 0.4 m deep and under them the broken bedding, to z -1.0."""
    rng = np.random.default_rng(5104)
    p = Part('SM_AN_Causeway', (STONE, ELECTRUM))
    s = gquad(p, (-4.5, -1.7, 0), (4.5, -1.7, 0), (4.5, 1.7, 0), (-4.5, 1.7, 0), STONE, STONE_PALE, 18, 8)
    worn = rgb(STONE_WORN) / rgb(STONE_PALE)
    tint(p, s, lambda v: 1 + (worn - 1) * (np.exp(-(v[:, 1] / 1.0) ** 2) * .8)[:, None])
    tint(p, s, lambda v: 1 - .16 * (np.abs(np.abs(v[:, 0]) - 1.5) < .02))
    for x0, x1 in ((-4.5, -1.5), (-1.5, 1.5), (1.5, 4.5)):
        gbox(p, (x0, -1.7, -.4), (x1, 1.7, 0), STONE, vary(rng, STONE_PALE, .06), (.75, .85, .4), .035, 'Z')
    slab_keel(p, rng, (-4.36, -1.58, -1.0), (4.36, 1.58, -.3), 12, .3, (.7, .95))
    for sy in (-1, 1):
        inlay(p, (-4.4, 1.35 * sy, 0), (4.4, 1.35 * sy, 0), .05, .005, Z)
    return done(p, 5104, 'any', None, facts=dict(top=0.0, x=(-4.5, 4.5), y=(-1.7, 1.7)))


@mesh('SM_AN_Bulwark', (.9, 4.5, 2.4), tol=.03)
def bulwark():
    """A cover wall along y, facing +x: five courses battered from 0.9 m at the foot to 0.5 m under the coping, a tall
    pointed slit through its middle filled with crystal, one line of inlay on each face."""
    rng = np.random.default_rng(5105)
    p = Part('SM_AN_Bulwark', (STONE, ELECTRUM, CRYSTAL, LICHEN))
    slit = pointed(.26, 1.5, 2.0)
    op = [(0.0, slit, 1.0, 2.0)]
    s = len(p.v)
    course(p, rng, 'y', -2.25, 2.25, -.45, .45, 0, .5, piece=(1.8, 2.6), cell=(.45, .6, .5), bevel=.035, skip='z')
    for z0 in (.5, 1.0, 1.5):
        course(p, rng, 'y', -2.2, 2.2, -.41, .41, z0, z0 + .5, op, piece=(1.4, 2.4), cell=(.45, .5, .17), jig=(.008, .008))
    course(p, rng, 'y', -2.25, 2.25, -.47, .47, 2.0, 2.4, piece=(2.0, 2.6), cell=(.45, .6, .4), bevel=.045)
    pane(p, 'y', 0.0, slit, 1.0, 2.0, 0.0, CRYSTAL_ICE)
    for sx in (-1, 1):
        for sy in (-1, 1):
            inlay(p, (.41 * sx, sy * .3, .76), (.41 * sx, sy * 2.15, .76), .04, .005, X * sx)
    batter(p, s, .44 / 2.4 * .9)
    lichens(p, rng, (-.2, .2), (-2.1, 2.1), 2.4, 7, (.05, .13))
    return done(p, 5105, reach=1.2)


@mesh('SM_AN_Shard', [(0, 1.2, 0), (0, 1.8, 0), (0, 2.4, 0), (0, 3.0, 0)], variants=4, pivot='centre', tol=.04)
def shard(k):
    """A drifting fragment of unwoven masonry: a block broken on every side but one. The dressed face (+x) keeps its
    chamfered arrises; the largest fracture is violet-scorched and lit from within."""
    rng = np.random.default_rng(5110 + k)
    size = (1.2, 1.8, 2.4, 3.0)[k]
    p = Part('SM_AN_Shard%d' % k, (STONE, GLOW))
    half = arr([(.3, .34, .3, .36)[k], .5, (.36, .3, .42, .34)[k]]) * size * 1.25
    for attempt in range(8):
        del p.v[:], p.f[:], p.c[:], p.m[:], p.s[:], p.uv[:]
        s, planes = chunk(p, rng, half, (4, 5, 5, 6)[k], size / 12, vary(rng, STONE_PALE, .06), depth=(.42, .78))
        if fracture(p, rng, s, planes, seed=k) is not None:
            break
    v = arr(p.v)
    ext = v.max(0) - v.min(0)
    p.v = (v * (size / ext[1])).tolist()
    return done(p, 5110 + k, 'centre', lichen_k=.25, dust=.15)


@mesh('SM_AN_Knot', (1.4, 1.4, 0), pivot='centre', tol=.04)
def knot():
    """The mark of something that can be rewoven: six stone slivers standing in a ring 1.4 m across round a
    pearl-gold core (GLOW_WEAVE) with a thin halo."""
    rng = np.random.default_rng(5120)
    p = Part('SM_AN_Knot', (STONE, GLOW))
    blob(p, (0, 0, 0), .17, GLOW_WEAVE, GLOW, 2, .06, 5, smooth=True)
    gem(p, (0, 0, 0), .11, .34, GLOW, k_of(GLOW_WEAVE, .8), Z, 6)
    torus(p, (0, 0, 0), .36, .012, k_of(GLOW_WEAVE, .7), GLOW, 36, 5)
    for j in range(6):
        a = TAU * j / 6
        r = .7 - .11
        c = arr([math.cos(a) * r, math.sin(a) * r, (.07 if j % 2 else -.07)])
        ax = unit(arr([math.cos(a) * .22, math.sin(a) * .22, 1.0]) + rng.normal(0, .06, 3))
        s = gem(p, c, .11, .34, STONE, vary(rng, STONE_PALE, .1), ax, 4, low=.24, turn_by=rng.uniform(0, 1))
        tint(p, s, lambda v: .7 + .3 * np.clip((np.hypot(v[:, 0], v[:, 1]) - .45) / .25, 0, 1))
    v = arr(p.v)
    ext = (v.max(0) - v.min(0))[:2]
    v[:, :2] *= 1.4 / ext
    p.v = v.tolist()
    return done(p, 5120, 'centre', lichen_k=.15, dust=.1)


# ---------------------------------------------------------------- columns, the arch, walls and the gate

@mesh('SM_AN_Column', (2.2, 2.2, 12.0), tol=.02)
def column_whole():
    """A First One column, 12 m: twelve-sided, slightly tapering, in six drums, a plain flared head, one electrum band."""
    rng = np.random.default_rng(5130)
    p = Part('SM_AN_Column', (STONE, ELECTRUM))
    column12(p, rng, (0, 0, 0), 1.1, 12.0)
    return done(p, 5130, reach=3.0)


@mesh('SM_AN_ColumnBroken', (2.4, 2.4, 4.5), tol=.04)
def column_broken():
    """The same column snapped between 3.4 and 4.5 m: a jagged break, violet-scorched, light still in its cracks, and
    two fallen pieces at its foot."""
    rng = np.random.default_rng(5131)
    p = Part('SM_AN_ColumnBroken', (STONE, GLOW))
    r = column12(p, rng, (0, 0, 0), 1.1, 12.0, upto=3.3)
    ang = np.linspace(0, TAU, 12, endpoint=False)
    jag = 3.98 + .46 * np.cos(ang - .5) + rng.uniform(-.13, .13, 12)       # a slanting break, splintered
    jag += 4.5 - jag.max()
    ring0 = ngon(r, 12, 3.3)
    ring1 = np.stack([np.cos(ang) * r * .985, np.sin(ang) * r * .985, jag], 1)
    scorch = rgb(mix(STONE_DARK, CLOTH_VIOLET, .3))
    loft(p, [ring0, ring1], STONE, [rgb(STONE_PALE), rgb(STONE_SHADE) * .8])
    ring2 = np.stack([np.cos(ang + .12) * r * .62, np.sin(ang + .12) * r * .62, 3.3 + (jag - 3.3) * .55 + rng.uniform(-.08, .08, 12)], 1)
    loft(p, [ring1, ring2], STONE, [scorch * 1.5, scorch], inward=True)
    mid = arr([.06, -.04, float(ring2[:, 2].min()) - .12])
    fan(p, mid, ring2, STONE, scorch * .8, Z)
    lift = arr([0, 0, .012])
    for j in (0, 3, 5, 8, 10):                               # light in the cracks of the break (along its creases)
        bar(p, ring1[j] * (.97, .97, 1) + lift, ring2[j] + lift, .05, .025, GLOW, k_of(GLOW_VIGIL, .9), up=Z)
        bar(p, ring2[j] + lift, mid + lift, .04, .025, GLOW, GLOW_VIGIL, up=Z)
    for c, h, yaw, sd in (((1.0, .35, .12), (.2, .24, .12), 12, 1), ((-.4, .97, .1), (.26, .2, .1), -6, 2), ((-1.0, -.55, .1), (.2, .22, .1), 8, 3),
                          ((.5, -.97, .09), (.22, .2, .09), -8, 4)):
        r2 = np.random.default_rng(5131 + sd)
        s, planes = chunk(p, r2, h, 5, .12, vary(rng, STONE_PALE, .06), depth=(.5, .8), allow=lambda n: n[2] > -.1)
        v = arr(p.v[s:])
        for i, pl in enumerate(planes):
            m = on_plane(v, pl)
            tint(p, s, lambda q, m=m: np.where(m, .62, 1.0))
        place(p, s, rot('z', yaw), c)
    return done(p, 5131, reach=2.5)


def arcs(hw, h, n=600):
    """A parabola from (-hw, 0) over (0, h) to (hw, 0) as a function of its arc-length share s (0..1) -> (y, z)."""
    y = np.linspace(-hw, hw, n)
    z = h * (1 - (y / hw) ** 2)
    d = np.concatenate([[0], np.cumsum(np.hypot(np.diff(y), np.diff(z)))])
    return (lambda s: (np.interp(s, d / d[-1], y), np.interp(s, d / d[-1], z))), d[-1]


@mesh('SM_AN_Arch', (3.0, 12.0, 13.0), tol=.02)
def first_arch():
    """The First Arch: a free-standing parabolic arch across y. Its opening is a parabola 6.5 m wide at the ground and
    10 m high (the passage runs along x); its back a parabola 11.8 m wide and 12.85 m high, so the ring is as thick
    at the crown as at the feet. Twenty-seven voussoirs and a keystone that stands proud to 13.0 with a crystal set
    in each face; an inner order stepped back; one line of inlay following the curve; two foot blocks 12 m apart."""
    rng = np.random.default_rng(5140)
    p = Part('SM_AN_Arch', (STONE, ELECTRUM, CRYSTAL, LICHEN))
    inner, li = arcs(3.25, 10.0)
    outer, lo_ = arcs(5.9, 12.85)
    L, T = (li + lo_) / 2, 2.8
    D = 1.42

    def bend(v):
        s = np.clip(v[:, 1] / L, 0, 1)
        yi, zi = inner(s)
        yo, zo = outer(s)
        u = v[:, 2] / T
        return np.stack([v[:, 0], yi + (yo - yi) * u, zi + (zo - zi) * u], 1)
    nv = 27
    cuts = np.linspace(0, L, nv + 1)
    s0 = len(p.v)
    for k in range(nv):
        key = k == nv // 2
        col = vary(rng, STONE_PALE, .07)
        # the inner order (0.7 m of the ring's thickness) stands 0.14 m back from the face
        s = gbox(p, (-D + .14, cuts[k], 0), (D - .14, cuts[k + 1], .72), STONE, col, (.75, .5, .4), .035)
        warp(p, s, bend)
        s = gbox(p, (-D - (.05 if key else 0), cuts[k], .7), (D + (.05 if key else 0), cuts[k + 1], T + (.15 if key else 0)), STONE, col,
                 (.75, .5, .75), .04)
        warp(p, s, bend)
    for sx in (-1, 1):                                       # the line of inlay, following the curve on both faces
        s = gbox(p, (sx * D - .004, .45, 1.72), (sx * D + .008 * sx, L - .45, 1.78), ELECTRUM, ELECTRUM_PALE, (1, .3, 1), 0)
        warp(p, s, bend)
    batter(p, s0, .02)
    zk = 12.0
    xk = (D + .05) * (1 - .02 * zk)
    for sx in (-1, 1):
        gem(p, (sx * xk, 0, zk), .17, .09, CRYSTAL, CRYSTAL_ICE, X * sx, 6, low=.02)
    for sy in (-1, 1):                                       # the foot blocks
        gbox(p, (-1.5, sy * 3.25, 0), (1.5, sy * 6.0, .7), STONE, vary(rng, STONE_PALE, .05), (.75, .7, .7), .05, 'z')
        lichens(p, rng, (-1.38, -1.2), (sy * 4.6 - 1.2, sy * 4.6 + 1.2), .7, 4, (.05, .11))
        lichens(p, rng, (1.2, 1.38), (sy * 4.6 - 1.2, sy * 4.6 + 1.2), .7, 3, (.05, .1))
    return done(p, 5140, reach=4.0, facts=dict(opening=dict(width=6.5, height=10.0), crown=13.0))


@mesh('SM_AN_Wall', (1.6, 12.0, 9.0), tol=.02)
def wall():
    """A court wall panel, 12 m along y, facing +x: a plinth course 1.6 m thick, ten long level courses battered to
    1.0 m under the coping, two tall pointed slits glazed with crystal, one line of inlay. Its two ends are plain cut
    planes at y -6 and 6, so panels stand side by side without a seam."""
    rng = np.random.default_rng(5150)
    p = Part('SM_AN_Wall', (STONE, ELECTRUM, CRYSTAL, LICHEN))
    slit = pointed(.42, 4.75, 5.5)
    ops = [(-3.0, slit, 3.25, 5.5), (3.0, slit, 3.25, 5.5)]
    s = len(p.v)
    course(p, rng, 'y', -6, 6, -.8, .8, 0, 1.0, piece=(3.4, 4.6), cell=(.8, 1.0, .5), bevel=.04, skip='zyY')
    for k in range(10):
        z0 = 1.0 + .75 * k
        course(p, rng, 'y', -6, 6, -.74, .74, z0, z0 + .75, ops, piece=(3.2, 5.6), cell=(.8, 1.0, .25 if 3 <= k < 6 else .75),
               skip='yY', jig=(.012, .012))
    course(p, rng, 'y', -6, 6, -.8, .8, 8.5, 9.0, piece=(2.8, 3.4), cell=(.8, 1.0, .5), bevel=.05, skip='yY')
    for uc in (-3.0, 3.0):
        pane(p, 'y', uc, slit, 3.25, 5.5, 0.0, CRYSTAL_ICE)
    for w, z0, z1 in ((.8, 0, 1.0), (.74, 1.0, 8.5), (.8, 8.5, 9.0)):          # the cut ends, closed
        gquad(p, (w, 6, z0), (-w, 6, z0), (-w, 6, z1), (w, 6, z1), STONE, STONE_SHADE, 2, cells(z1 - z0, .75))
        gquad(p, (-w, -6, z0), (w, -6, z0), (w, -6, z1), (-w, -6, z1), STONE, STONE_SHADE, 2, cells(z1 - z0, .75))
    for sx in (-1, 1):
        inlay(p, (.74 * sx, -6, 6.62), (.74 * sx, 6, 6.62), .06, .006, X * sx)
    batter(p, s, .375 / 9.0)
    lichens(p, rng, (-.4, .4), (-5.8, 5.8), 9.0, 14, (.08, .25))
    lichens(p, rng, (-.78, -.72), (-5.8, 5.8), 1.0, 8, (.04, .06))
    return done(p, 5150, reach=3.0, facts=dict(thick_foot=1.6, thick_top=1.0))


@mesh('SM_AN_GateFrame', (3.0, 16.0, 12.5), tol=.02)
def gate_frame():
    """The portal in the Lens Court's wall: two pylons 3 m wide and a lintel over an opening exactly 10 m wide (y -5
    to 5) and 10 m high, the passage along x. The pylons are laid in courses and lightly battered on their two
    faces; the lintel is a flat arch of nine blocks whose keystone stands proud and holds a crystal, under a cornice
    and a low attic with raked ends; alloy pilasters stand beside the opening on both faces, and a line of inlay runs
    up them and across the lintel."""
    rng = np.random.default_rng(5160)
    p = Part('SM_AN_GateFrame', (STONE, ALLOY, ELECTRUM, CRYSTAL, LICHEN))
    s = len(p.v)
    for sy in (-1, 1):
        y0, y1 = (5.0, 8.0) if sy > 0 else (-8.0, -5.0)
        course(p, rng, 'y', y0, y1, -1.5, 1.5, 0, 1.2, piece=(3.0, 3.1), cell=(.75, .75, .6), bevel=.045, skip='z')
        for k in range(11):
            z0 = 1.2 + .8 * k
            course(p, rng, 'y', y0, y1, -1.4, 1.4, z0, z0 + .8, piece=(1.3, 3.2), cell=(.95, 1.0, .8), jig=(.012, .012))
    cuts = np.linspace(-8, 8, 10)
    for k in range(9):                                       # the lintel's flat arch
        key = k == 4
        gbox(p, (-1.4 - (.06 if key else 0), cuts[k], 10.0), (1.4 + (.06 if key else 0), cuts[k + 1], 11.6), STONE,
             vary(rng, STONE_PALE, .07), (.95, .9, .8), .04)
    course(p, rng, 'y', -8, 8, -1.5, 1.5, 11.6, 12.0, piece=(3.0, 3.4), cell=(.75, 1.0, .4), bevel=.05)
    course(p, rng, 'y', -4.6, 4.6, -1.22, 1.22, 12.0, 12.5, piece=(2.8, 3.2), cell=(.8, 1.0, .5), bevel=.05,
           ends=(lambda z: -4.6 + (arr(z) - 12.0) * .9, lambda z: 4.6 - (arr(z) - 12.0) * .9))
    for sx in (-1, 1):
        for sy in (-1, 1):                                    # alloy pilasters beside the opening, inlay up their middles
            gbox(p, (sx * 1.4, sy * 5.02, 1.2), (sx * 1.45, sy * 5.5, 10.0), ALLOY, ALLOY_SILVER, (1, 1, 1.1), .012)
            inlay(p, (sx * 1.45, sy * 5.26, 1.3), (sx * 1.45, sy * 5.26, 9.9), .05, .006, X * sx)
            gbox(p, (sx * 1.4, sy * 5.0, 9.72), (sx * 1.47, sy * 5.56, 10.0), ALLOY, ALLOY_DARK, 1, .012)
            gbox(p, (sx * 1.4, sy * 5.0, 1.2), (sx * 1.47, sy * 5.56, 1.48), ALLOY, ALLOY_DARK, 1, .012)
        inlay(p, (sx * 1.4, -7.9, 10.8), (sx * 1.4, -.95, 10.8), .06, .006, X * sx)
        inlay(p, (sx * 1.4, .95, 10.8), (sx * 1.4, 7.9, 10.8), .06, .006, X * sx)
    batter(p, s, .018)
    for sx in (-1, 1):
        gem(p, (sx * 1.46 * (1 - .018 * 10.8), 0, 10.8), .34, .12, CRYSTAL, CRYSTAL_VIOLET, X * sx, 6, low=.02)
    lichens(p, rng, (-.75, .75), (-3.8, 3.8), 12.5, 9, (.08, .22))
    for sy in (-1, 1):
        lichens(p, rng, (-.9, .9), (min(sy * 4.9, sy * 7.7), max(sy * 4.9, sy * 7.7)), 12.0, 7, (.08, .25))
    return done(p, 5160, reach=3.5, facts=dict(opening=dict(y=(-5.0, 5.0), z=(0.0, 10.0)), pylons_y=(5.0, 8.0)))


@mesh('SM_AN_Veil', (.6, 10.0, 10.0), tol=.02)
def veil():
    """The Veil that fills the gate: a lattice of hard violet light, bars crossing on the diagonal with a crystal
    node at every crossing and a thin sheet of violet crystal behind them, in an alloy frame 10 by 10 m and 0.6 m
    deep."""
    rng = np.random.default_rng(5170)
    p = Part('SM_AN_Veil', (ALLOY, GLOW, CRYSTAL))
    fw = .32
    for y0, y1, z0, z1 in ((-5, 5, 0, fw), (-5, 5, 10 - fw, 10), (-5, -5 + fw, fw, 10 - fw), (5 - fw, 5, fw, 10 - fw)):
        gbox(p, (-.26, y0, z0), (.26, y1, z1), ALLOY, ALLOY_SILVER, (.6, 1.25, 1.2), .03)
    for y0, y1, z0, z1 in ((-5 + fw, 5 - fw, fw, fw + .06), (-5 + fw, 5 - fw, 10 - fw - .06, 10 - fw), (-5 + fw, -5 + fw + .06, fw, 10 - fw),
                           (5 - fw - .06, 5 - fw, fw, 10 - fw)):
        gbox(p, (-.1, y0, z0), (.1, y1, z1), GLOW, k_of(GLOW_VIGIL, .8), 3, 0)
    a = 5 - fw - .06
    step = 2 * a / 8                                        # crossings on a square grid turned 45 degrees
    for sgn in (-1, 1):
        for k in range(-7, 8):
            # the line y - sgn * (z - 5) = k * step, clipped to the square |y|, |z - 5| <= a
            c = k * step
            lo_t, hi_t = max(-a, -a - c if sgn > 0 else c - a), min(a, a - c if sgn > 0 else c + a)
            if hi_t - lo_t < .2:
                continue
            pa = (0, c + sgn * lo_t, 5 + lo_t)
            pb = (0, c + sgn * hi_t, 5 + hi_t)
            bar(p, pa, pb, .07, .07, GLOW, k_of(GLOW_VIGIL, rng.uniform(.8, 1.0)), up=X)
    for i in range(-7, 8):
        for j in range(-7, 8):
            if (i + j) % 2:
                continue
            y, z = i * step / 2 * 1.0, j * step / 2 * 1.0
            if abs(y) > a - .05 or abs(z) > a - .05:
                continue
            gem(p, (0, y, 5 + z), .13, .2, CRYSTAL, mix(CRYSTAL_VIOLET, CRYSTAL_ICE, rng.uniform(0, .5)), X, 4)
    for sx in (-1, 1):                                       # the sheet, seen from both sides
        q = [(-.02 * sx, -a * sx, 5 - a), (-.02 * sx, a * sx, 5 - a), (-.02 * sx, a * sx, 5 + a), (-.02 * sx, -a * sx, 5 + a)]
        s = gquad(p, q[1], q[0], q[3], q[2], CRYSTAL, CRYSTAL_VIOLET, 12, 12)
        tint(p, s, lambda v: .55 + .3 * noise2(v[:, 1] / 1.7, v[:, 2] / 1.7, 9) + .15 * np.abs(v[:, 2] - 5) / 5)
    for sy in (-1, 1):                                       # the frame's emitters: light at the four corners and mid-sides
        for z in (.16, 5.0, 9.84):
            for sx in (-1, 1):
                gem(p, (sx * .26, sy * 4.84, z), .09, .04, GLOW, GLOW_VIGIL, X * sx, 6, low=.01)
    return done(p, 5170, reach=1.0)


# ---------------------------------------------------------------- the Serene's buildings

HOUSES = (dict(hx=4.0, hy=3.5, zt=4.0, top=6.0, ridge=.75, seed=5180), dict(hx=3.0, hy=3.0, zt=5.0, top=7.5, ridge=0.0, seed=5181))


@mesh('SM_AN_House', [(8.0, 7.0, 6.0), (6.0, 6.0, 7.5)], variants=2, tol=.02)
def house(k):
    """A Serene dwelling: a battered stone cell (walls 0.6 m at the foot, 0.35 m under the eaves, plumb inside) round
    one open room, a tall pointed doorway 1.4 by 3 m on +x, pointed crystal windows in the other walls, a stone
    cornice and a hipped roof of blue glazed tile with a crystal finial, a small ice-blue light over the door.
    Variant 0 is the long house (8 by 7 by 6 m), variant 1 the tall cell (6 by 6 by 7.5 m, a pyramid roof)."""
    h = HOUSES[k]
    hx, hy, zt, top = h['hx'], h['hy'], h['zt'], h['top']
    rng = np.random.default_rng(h['seed'])
    p = Part('SM_AN_House%d' % k, (STONE, TILE, CRYSTAL, ELECTRUM, GLOW, LICHEN))
    t = .6
    xi, yi = hx - t, hy - t
    door = pointed(1.4, 2.0, 3.0)
    win = pointed(.55, 2.5, 3.5)
    high = pointed(.5, 3.5, 4.5)
    front = [(0.0, door, 0.0, 3.0)] + ([(0.0, high, 3.5, 4.5)] if k else [])
    side = [(-1.6, win, 1.5, 3.5), (1.6, win, 1.5, 3.5)] if k == 0 else [(0.0, win, 1.5, 3.5)]
    back = [(0.0, win, 1.5, 3.5)]
    levels = np.arange(0, zt + 1e-6, .5)
    s = len(p.v)
    for z0, z1 in zip(levels[:-1], levels[1:]):
        base = z0 == 0
        ex = .0 if base else .035                              # the plinth course stands proud
        kw = dict(piece=(1.8, 3.4), cell=(.7, .7, .17), bevel=.03, skip='z' if base else '')
        jg = .0 if base else .01
        course(p, rng, 'y', -hy + ex, hy - ex, xi, hx - ex, z0, z1, front, jig=(0, jg), **kw)
        course(p, rng, 'y', -hy + ex, hy - ex, -hx + ex, -xi, z0, z1, back, jig=(jg, 0), **kw)
        course(p, rng, 'x', -xi, xi, yi, hy - ex, z0, z1, side, jig=(0, jg), **dict(kw, skip=kw['skip'] + 'xX'))
        course(p, rng, 'x', -xi, xi, -hy + ex, -yi, z0, z1, side, jig=(jg, 0), **dict(kw, skip=kw['skip'] + 'xX'))
    rate = .42 / zt
    batter(p, s, rate, 0, xi)
    batter(p, s, rate, 1, yi)
    for uc, hw, zs, za in side:
        pane(p, 'x', uc, hw, zs, za, yi + .2, CRYSTAL_ICE)
        pane(p, 'x', uc, hw, zs, za, -yi - .2, CRYSTAL_ICE)
    pane(p, 'y', 0.0, win, 1.5, 3.5, -xi - .2, CRYSTAL_ICE)
    if k:
        pane(p, 'y', 0.0, high, 3.5, 4.5, xi + .2, CRYSTAL_VIOLET)
    # the floor: one flat face, 3 cm above the ground, running out through the doorway
    fs = gquad(p, (-xi, -yi, .03), (xi, -yi, .03), (xi, yi, .03), (-xi, yi, .03), STONE, STONE_WORN, cells(2 * xi, .8), cells(2 * yi, .8))
    gquad(p, (xi, -.7, .03), (hx - .005, -.7, .03), (hx - .005, .7, .03), (xi, .7, .03), STONE, STONE_WORN, 1, 2)
    gquad(p, (hx - .005, -.7, 0), (hx - .005, .7, 0), (hx - .005, .7, .03), (hx - .005, -.7, .03), STONE, STONE_SHADE, 2, 1)
    tint(p, fs, lambda v: .9 + .1 * noise2(v[:, 0] / .8, v[:, 1] / .8, 4))
    # the cornice (its underside is the room's ceiling) and the roof
    ox, oy = hx - .25 + .07, hy - .25 + .07
    gbox(p, (-ox, -oy, zt), (ox, oy, zt + .24), STONE, STONE_PALE, (.8, .8, .3), .04)
    for sx in (-1, 1):
        inlay(p, (sx * ox, -oy + .1, zt + .12), (sx * ox, oy - .1, zt + .12), .04, .005, X * sx)
    for sy in (-1, 1):
        inlay(p, (-ox + .1, sy * oy, zt + .12), (ox - .1, sy * oy, zt + .12), .04, .005, Y * sy)
    ex_, ey_ = hx - .08, hy - .08
    z_e, z_r = zt + .24, top - .28
    gbox(p, (-ex_, -ey_, z_e), (ex_, ey_, z_e + .07), TILE, k_of(TILE_DEEP, .7), 1.2, .02)
    r0, r1 = hip_roof(p, rng, -ex_, ex_, ey_, z_e + .07, z_r, h['ridge'], tile=(.36, .42))
    ends = [arr(r0), arr(r1)] if h['ridge'] > .05 else [(arr(r0) + arr(r1)) / 2]
    for q in ends:
        cylinder(p, (q[0], q[1], z_r - .02), .09, .12, ELECTRUM_PALE, ELECTRUM, 8, r2=.05)
        gem(p, (q[0], q[1], top - .1), .07, .1, CRYSTAL, CRYSTAL_ICE, Z, 6, low=.12)
    # the light over the door: a crystal in an electrum setting on the battered face
    zl = 3.42 if k == 0 else 3.25
    xl = hx - .035 - (t - .035) * rate * zl
    turn(p, [(.003, 0), (.12, 0), (.12, .03), (.09, .05), (.003, .05)], ELECTRUM, ELECTRUM_PALE, 10, (xl - .005, 0, zl), 'x', False)
    gem(p, (xl + .05, 0, zl), .075, .1, GLOW, GLOW_SERENE, X, 6, low=.01)
    lichens(p, rng, (-ox + .1, -ox + .9), (-oy + .2, oy - .2), zt + .24, 5, (.06, .14))
    return done(p, h['seed'], reach=1.6, facts=dict(door=dict(x=hx, width=1.4, height=3.0), floor=.03, room=dict(x=(-xi, xi), y=(-yi, yi), height=zt),
                                                     light=(round(xl + .05, 3), 0.0, zl)))


@mesh('SM_AN_Hall', (22.0, 14.0, 11.0), tol=.02)
def hall():
    """The Hearthold's hall: a podium of three steps (the floor one flat face at z 0.6; the steps run the whole +x
    side), a colonnade of twelve-sided columns on the front and both long sides, a battered back wall with three
    crystal slits, a stone entablature with one line of inlay, a coffer of cross beams, and a hipped roof of blue
    glazed tile to 11 m. Four ice-blue crystals hang under the beams."""
    rng = np.random.default_rng(5190)
    p = Part('SM_AN_Hall', (STONE, TILE, ELECTRUM, ALLOY, GLOW, CRYSTAL, LICHEN))
    FL = .6
    gbox(p, (-11, -7, 0), (11.0, 7, .2), STONE, vary(rng, STONE_PALE, .04), (1.1, 1.0, .2), .02, 'z')
    gbox(p, (-11, -7, .2), (10.6, 7, .4), STONE, vary(rng, STONE_PALE, .04), (1.1, 1.0, .2), .02)
    s = gbox(p, (-11, -7, .4), (10.2, 7, FL), STONE, STONE_PALE, (1.06, 1.0, .2), .02)
    worn = rgb(STONE_WORN) / rgb(STONE_PALE)
    tint(p, s, lambda v: np.where((v[:, 2] > FL - 1e-6)[:, None], 1 + (worn - 1) * (.35 + .5 * np.exp(-(v[:, 1] / 3.0) ** 2))[:, None], 1.0))
    for sy in (-1, 1):                                       # a border of inlay on the floor, inside the colonnade
        inlay(p, (-9.2, sy * 5.3, FL), (8.4, sy * 5.3, FL), .05, .005, Z)
    inlay(p, (8.4, -5.3, FL), (8.4, 5.3, FL), .05, .005, Z)
    inlay(p, (-9.2, -5.3, FL), (-9.2, 5.3, FL), .05, .005, Z)
    # columns: six across the front, six more down each side
    xs = [9.3, 6.15, 3.0, -.15, -3.3, -6.45]
    spots = [(9.3, y) for y in (-6.25, -3.75, -1.25, 1.25, 3.75, 6.25)] + [(x, sy * 6.25) for x in xs[1:] for sy in (-1, 1)]
    for x, y in spots:
        column12(p, rng, (x, y, FL), .62, 6.4)
    # the back wall and its two returns, battered outside
    slit = pointed(.5, 4.25, 5.71)
    ops = [(-3.6, slit, 2.06, 5.71), (0.0, slit, 2.06, 5.71), (3.6, slit, 2.06, 5.71)]
    s = len(p.v)
    for k in range(10):
        z0 = FL + .73 * k
        course(p, rng, 'y', -6.9, 6.9, -10.9, -9.75, z0, z0 + .73, ops, piece=(3.0, 5.0), cell=(.8, 1.0, .25 if 2 <= k < 7 else .73), jig=(.012, .012))
        for sy in (-1, 1):
            t0, t1 = (5.8, 6.9) if sy > 0 else (-6.9, -5.8)
            course(p, rng, 'x', -9.75, -7.9, t0, t1, z0, z0 + .73, piece=(1.9, 2.0), cell=(.95, .6, .73), jig=(.01, .01), skip='x')
    warp(p, s, lambda v: np.stack([np.where(v[:, 0] < -10.3, -10.3 + (v[:, 0] + 10.3) * (1 - .06 * (v[:, 2] - FL)), v[:, 0]), v[:, 1], v[:, 2]], 1))
    for uc, hw, zs, za in ops:
        pane(p, 'y', uc, hw, zs, za, -10.3, CRYSTAL_ICE)
    # the entablature: beams over the columns, a line of inlay on their outer faces
    zb0, zb1 = 7.0, 7.9
    course(p, rng, 'y', -6.9, 6.9, 8.7, 9.9, zb0, zb1, piece=(2.5, 2.5), cell=(.6, 1.25, .9), bevel=.04)
    inlay(p, (9.9, -6.8, 7.5), (9.9, 6.8, 7.5), .06, .006, X)
    for sy in (-1, 1):
        t0, t1 = (5.65, 6.9) if sy > 0 else (-6.9, -5.65)
        course(p, rng, 'x', -10.9, 8.7, t0, t1, zb0, zb1, piece=(3.15, 3.15), cell=(1.05, .65, .9), bevel=.04)
        inlay(p, (-10.8, sy * 6.9, 7.5), (9.8, sy * 6.9, 7.5), .06, .006, Y * sy)
    for x in xs[1:] + [-9.2]:                               # cross beams
        gbox(p, (x - .3, -5.65, 7.3), (x + .3, 5.65, 7.9), STONE, vary(rng, STONE_SHADE, .06), (.6, 1.4, .6), .035)
    # the eave slab (the ceiling inside), then the tiled roof
    gbox(p, (-11, -7, 7.9), (11, 7, 8.2), STONE, STONE_PALE, (1.1, 1.0, .3), .05)
    gbox(p, (-10.9, -6.9, 8.2), (10.9, 6.9, 8.27), TILE, k_of(TILE_DEEP, .7), 1.6, .02)
    r0, r1 = hip_roof(p, rng, -10.9, 10.9, 6.9, 8.27, 10.7, 4.3, tile=(.44, .5))
    for q in (r0, r1):
        cylinder(p, (q[0], q[1], 10.68), .14, .14, ELECTRUM_PALE, ELECTRUM, 8, r2=.07)
        gem(p, (q[0], q[1], 10.87), .08, .13, CRYSTAL, CRYSTAL_ICE, Z, 6, low=.1)
    # the Serene's lights
    lights = []
    for x in (6.15, 3.0, -.15, -3.3, -6.45):
        tube(p, [(x, 0, 7.3), (x, 0, 6.72)], .018, ALLOY_DARK, ALLOY, 6)
        torus(p, (x, 0, 6.7), .11, .016, ALLOY_SILVER, ALLOY, 12, 5)
        lamp(p, (x, 0, 6.52), .11, .3, GLOW_SERENE)
        lights.append((x, 0.0, 6.52))
    for _ in range(14):
        lichen(p, rng, (rng.uniform(10.75, 10.85), rng.uniform(-6.8, 6.8), .2), rng.uniform(.05, .12))
    return done(p, 5190, reach=2.0, facts=dict(floor=FL, floor_x=(-9.75, 10.2), floor_y=(-7.0, 7.0), steps='+x: two treads 0.4 m deep, risers 0.2 m',
                                               columns=spots, lights=lights, clear_height=6.7))


# ---------------------------------------------------------------- the Vigil's works

@mesh('SM_AN_Mirror', (2.5, 5.0, 7.0), tol=.03)
def mirror():
    """A great mirror, facing +x: a slightly dished disc of polished alloy 4.4 m across in an electrum rim, its centre
    4.6 m up, turning on a plumb axis inside an alloy gimbal ring that hangs by two trunnions (y -2.5 and 2.5) in a
    forked yoke on a stepped twelve-sided stone base 2.5 m across."""
    rng = np.random.default_rng(5200)
    p = Part('SM_AN_Mirror', (STONE, ALLOY, ELECTRUM))
    C = arr([0, 0, 4.6])
    lathe(p, [(1.25, 0), (1.25, .3), (1.21, .34), (1.0, .34), (1.0, .56), (.97, .6), (.45, .6)], STONE_PALE, STONE, 12, (0, 0, 0), False)
    face(p, ngon(.45, 12, .6), STONE, STONE_PALE, Z)
    lathe(p, [(.4, .6), (.4, .72), (.3, .8), (.22, 1.3), (.2, 1.9), (.28, 2.02), (.28, 2.14), (.2, 2.2), (.003, 2.2)], ALLOY_SILVER, ALLOY, 16)
    lathe(p, [(.31, .82), (.33, .86), (.33, .96), (.31, 1.0)], ELECTRUM_PALE, ELECTRUM, 16)
    # the yoke: a half ring under the gimbal from trunnion to trunnion
    a = np.linspace(math.pi, TAU, 33)
    ry = 2.4
    path = np.stack([np.zeros(33), np.cos(a) * ry, 4.6 + np.sin(a) * (ry + .04)], 1)
    for i in range(32):
        bar(p, path[i], path[i + 1], .26, .12, ALLOY, k_of(ALLOY_SILVER, .8 + .1 * (i % 2)), up=unit(arr([0, path[i][1], path[i][2] - 4.6])))
    for sy in (-1, 1):                                       # trunnions
        turn(p, [(.003, 0), (.16, 0), (.16, .1), (.1, .14), (.003, .14)], ALLOY, ALLOY_DARK, 12, (0, 0, 0), 'z', False)
        place(p, len(p.v) - 12 * 5, rot('x', -90 * sy), (0, sy * 2.36, 4.6))
        bevel_box(p, (0, sy * 2.4, 4.62), (.2, .1, .2), ALLOY_SILVER, ALLOY, .03)
    torus(p, C, 2.32, .08, ALLOY_SILVER, ALLOY, 56, 8, axis='x')                    # the gimbal ring
    for sz in (-1, 1):                                       # the disc's own pivots, top and bottom
        cylinder(p, (0, 0, 4.6 + sz * 2.2 - .06), .07, .12, ALLOY_DARK, ALLOY, 8)
    # the disc: front (dished, bright), rim, back
    bright = k_of(ALLOY_SILVER, 1.5)
    front = [(.003, .035)] + [(r, .035 + .075 * (r / 2.05) ** 2) for r in np.linspace(.25, 2.05, 9)]
    s = turn(p, front[::-1], ALLOY, bright, 56, C, 'x', True)
    tint(p, s, lambda v: .93 + .07 * np.cos(np.hypot(v[:, 1], v[:, 2] - 4.6) * 9))
    turn(p, [(2.05, -.09), (2.2, -.09), (2.2, .1), (2.16, .14), (2.09, .14), (2.05, .11)][::1], ELECTRUM, ELECTRUM_PALE, 56, C, 'x', True)
    back = [(2.05, -.09), (1.6, -.14), (.9, -.2), (.35, -.26), (.003, -.27)]
    turn(p, back[::-1], ELECTRUM, k_of(ELECTRUM_PALE, .62), 56, C, 'x', True)
    for j in range(8):                                       # ribs on the back
        t = TAU * j / 8 + .39
        d = arr([0, math.cos(t), math.sin(t)])
        bar(p, C + d * .3 + (-.26, 0, 0), C + d * 2.02 + (-.11, 0, 0), .07, .1, ELECTRUM, k_of(ELECTRUM_PALE, .8), up=-X)
    turn(p, [(.003, -.34), (.3, -.34), (.36, -.3)], ELECTRUM, ELECTRUM_PALE, 12, C, 'x', False)
    return done(p, 5200, reach=1.2, facts=dict(centre=(0.0, 0.0, 4.6), disc=4.4, faces='+x'))


@mesh('SM_AN_Lens', (9.0, 36.0, 40.0), tol=.02)
def lens():
    """The Sundering Lens, facing -x. Two great battered pylons of coursed stone (9 m deep at the foot, 32.5 m high)
    stand 26 m apart on a stepped base and clasp an alloy ring 30 m across, its centre 24 m up. In the ring a
    faceted crystal lens, thicker at the middle, round a violet core that shows on both faces; eight focusing vanes
    lean forward (-x) from the ring toward the beam's axis, each with a lit edge; cables run from the pylon heads
    to the ring's shoulders and stays from the base to its haunches; a crystal finial on the crown reaches 40 m."""
    rng = np.random.default_rng(5210)
    p = Part('SM_AN_Lens', (STONE, ALLOY, ELECTRUM, CRYSTAL, GLOW, LICHEN))
    C = arr([0, 0, 24.0])
    # the base: two steps between and under the pylons
    course(p, rng, 'y', -18, 18, -4.5, 4.5, 0, 1.5, piece=(4.0, 5.0), cell=(1.5, 1.3, .75), bevel=.06, skip='z')
    course(p, rng, 'y', -13.2, 13.2, -3.4, 3.4, 1.5, 3.0, piece=(3.6, 4.6), cell=(1.4, 1.3, .75), bevel=.06)
    course(p, rng, 'y', -9, 9, -2.2, 2.2, 3.0, 4.2, piece=(3.4, 4.4), cell=(1.1, 1.3, .6), bevel=.05)
    for sx in (-1, 1):
        inlay(p, (sx * 3.4, -13, 2.3), (sx * 3.4, 13, 2.3), .08, .008, X * sx)
    # the pylons
    HP = 31.0
    for sy in (-1, 1):
        s = len(p.v)
        y0, y1 = (13.0, 18.0) if sy > 0 else (-18.0, -13.0)
        for k in range(1, 31):
            z0 = 1.5 + (HP - 1.5) * (k - 1) / 30
            z1 = 1.5 + (HP - 1.5) * k / 30
            course(p, rng, 'x', -4.3, 4.3, y0, y1, z0, z1, piece=(3.4, 5.0), cell=(1.45, 1.25, 1.0), bevel=.045,
                   jig=(.015, .015) if 1 < k < 30 else (0, 0))
        # battered: the two faces (x) lean in to 2.3 m, the outer side (y) leans in by 1.4 m, the inner side is plumb

        def lean(v, sy=sy):
            t = np.clip((v[:, 2] - 1.5) / (HP - 1.5), 0, 1)
            v[:, 0] *= 1 - (1 - 2.3 / 4.3) * t
            out = (v[:, 1] * sy - 13.0) / 5.0
            v[:, 1] = sy * (13.0 + out * (5.0 - 1.4 * t))
            return v
        warp(p, s, lean)
        yc = sy * 14.8
        # the head: a cap course, an alloy crown and a light
        gbox(p, (-2.5, sy * 12.85, HP), (2.5, sy * 16.75, HP + .7), STONE, STONE_PALE, (1.25, 1.3, .7), .06)
        gbox(p, (-1.9, sy * 13.3, HP + .7), (1.9, sy * 16.3, HP + 1.1), ALLOY, ALLOY_SILVER, (1.0, 1.0, .4), .04)
        lamp(p, (0, yc, HP + 1.75), .34, .75, GLOW_VIGIL, crystal=CRYSTAL_VIOLET)
        for sx in (-1, 1):
            # a tall slit of violet light and a line of inlay up each face
            for z0, z1 in ((6.0, 12.0), (14.0, 19.0)):
                t0, t1 = (z0 - 1.5) / (HP - 1.5), (z1 - 1.5) / (HP - 1.5)
                xa, xb = 4.3 * (1 - .465 * t0), 4.3 * (1 - .465 * t1)
                ya, yb = sy * (13 + .5 * (5 - 1.4 * t0)), sy * (13 + .5 * (5 - 1.4 * t1))
                bar(p, (sx * (xa + .012), ya, z0), (sx * (xb + .012), yb, z1), .22, .03, GLOW, k_of(GLOW_VIGIL, .85), up=X * sx)
                bar(p, (sx * (xa + .008), ya, z0 - .15), (sx * (xb + .008), yb, z1 + .15), .46, .03, ALLOY, ALLOY_DARK, up=X * sx)
            t0, t1 = (26.0 - 1.5) / (HP - 1.5), (30.4 - 1.5) / (HP - 1.5)
            inlay(p, (sx * 4.3 * (1 - .465 * t0), sy * (13 + .5 * (5 - 1.4 * t0)), 26.0), (sx * 4.3 * (1 - .465 * t1), sy * (13 + .5 * (5 - 1.4 * t1)), 30.4),
                  .1, .012, X * sx)
            # the trunnion boss that holds the ring: alloy disc, electrum ring, a violet eye
            tb = (24.0 - 1.5) / (HP - 1.5)
            xf = 4.3 * (1 - .465 * tb)
            s2 = turn(p, [(2.3, 0), (2.3, .22), (2.1, .34), (1.3, .34)], ALLOY, ALLOY_SILVER, 24, (0, 0, 0), 'x', False)
            turn(p, [(1.3, .34), (1.3, .4), (1.05, .4), (1.05, .3)], ELECTRUM, ELECTRUM_PALE, 24, (0, 0, 0), 'x', False)
            turn(p, [(1.05, .3), (.6, .42), (.003, .46)], GLOW, k_of(GLOW_VIGIL, .9), 24, (0, 0, 0), 'x', False)
            place(p, s2, rot('z', 0 if sx > 0 else 180), (sx * (xf - .1), sy * 15.3, 24.0))
    # the ring
    ring = [(15, -.9), (15, .9), (14.6, 1.3), (13.2, 1.3), (12.8, 1.0), (12.8, -1.0), (13.2, -1.3), (14.6, -1.3), (15, -.9)]
    s = turn(p, ring, ALLOY, ALLOY_SILVER, 96, C, 'x', False)
    tint(p, s, lambda v: .86 + .14 * (np.floor((np.arctan2(v[:, 2] - 24, v[:, 1]) + math.pi) / TAU * 24) % 2))
    turn(p, [(12.8, -.55), (12.74, -.5), (12.74, .5), (12.8, .55)][::-1], ELECTRUM, ELECTRUM_PALE, 96, C, 'x', False)
    for j in range(24):                                      # clamps over the ring's joints
        t = TAU * (j + .5) / 24
        d = arr([0, math.cos(t), math.sin(t)])
        if abs(d[1]) > .97:
            continue
        s = gbox(p, (-1.42, -.32, 12.7), (1.42, .32, 15.12), ALLOY, ALLOY_DARK, (1.42, .64, 1.2), .05)
        place(p, s, rot('x', math.degrees(t) - 90), C)
    for sx in (-1, 1):
        torus(p, C + (sx * 1.32, 0, 0), 13.9, .07, k_of(GLOW_VIGIL, .8), GLOW, 96, 5, axis='x')
    # the crystal lens: two faceted faces
    K, R, TH = 10, 13.0, 1.55
    pts = {}
    for k in range(K + 1):
        cnt = max(1, 6 * k)
        for j in range(cnt):
            a = TAU * j / cnt + (.0 if k % 2 else .02)
            r = R * k / K
            bump = 0 if k in (0, K) else rng.uniform(-.14, .14)
            pts[(k, j)] = (r * math.cos(a), r * math.sin(a), TH * (1 - (r / R) ** 2) + .12 + bump, r / R)
    tris = []
    for k in range(K):
        for sct in range(6):
            lo_i = [(k, (sct * k + i) % max(1, 6 * k)) for i in range(k + 1)] if k else [(0, 0)]
            hi_i = [(k + 1, (sct * (k + 1) + i) % (6 * (k + 1))) for i in range(k + 2)]
            for i in range(k + 1):
                tris.append((hi_i[i], hi_i[i + 1], lo_i[i] if k else (0, 0)))
            for i in range(k):
                tris.append((lo_i[i], hi_i[i + 1], lo_i[i + 1]))
    for sx in (-1, 1):
        verts, faces, cols = [], [], []
        for t in tris:
            q = [arr([sx * pts[i][2], pts[i][0], 24 + pts[i][1]]) for i in t]
            nrm = np.cross(q[1] - q[0], q[2] - q[0])
            if nrm[0] * sx < 0:
                q = [q[0], q[2], q[1]]
            rr = np.mean([pts[i][3] for i in t])
            col = rgb(mix(mix(CRYSTAL_VIOLET, CRYSTAL_ICE, min(1, rr * 1.2)), CRYSTAL_CLEAR, rng.uniform(0, .35))) * rng.uniform(.62, 1.0)
            base = len(verts)
            verts += q
            cols += [col] * 3
            faces.append([base, base + 1, base + 2])
        p.add(verts, faces, np.minimum(arr(cols), .9), CRYSTAL, False)
        # the core and its filaments
        for j in range(6):
            a = TAU * j / 6 + .26
            ra, rb = 2.0, 7.4
            pa = (sx * (TH * (1 - (ra / R) ** 2) + .32), ra * math.cos(a), 24 + ra * math.sin(a))
            pb = (sx * (TH * (1 - (rb / R) ** 2) + .3), rb * math.cos(a), 24 + rb * math.sin(a))
            bar(p, pa, pb, .16, .06, GLOW, k_of(GLOW_VIGIL, .75), up=X * sx)
    blob(p, C, 1.0, GLOW_VIGIL, GLOW, 2, .05, 3, squash=(2.25, 2.1, 2.1))
    gem(p, C, 2.6, 2.75, GLOW, k_of(GLOW_VIGIL, .8), X, 8)
    # the focusing vanes, leaning forward from the ring
    for j in range(8):
        t = TAU * (j + .5) / 8
        d = arr([0, math.cos(t), math.sin(t)])
        a0, a1 = C + d * 14.3 + (-1.3, 0, 0), C + d * 10.2 + (-4.5 + .12, 0, 0)
        side = np.cross(d, X)
        up = unit(np.cross(a1 - a0, side))
        for (f0, f1, w0, w1) in ((0.0, .5, 1.5, 1.0), (.5, 1.0, 1.0, .36)):
            q0, q1 = a0 + (a1 - a0) * f0, a0 + (a1 - a0) * f1
            cs = [q + sy_ * side * w / 2 + sz * up * .11 for sz in (-1, 1) for sy_ in (-1, 1) for q, w in ((q0, w0), (q1, w1))]
            hexa(p, cs, k_of(ALLOY_SILVER, .95), ALLOY)
        bar(p, a0 - up * .13, a1 - up * .13, .12, .05, GLOW, k_of(GLOW_VIGIL, .9), up=up)
        bar(p, a0 + (a1 - a0) * .04 + up * .12, a0 + (a1 - a0) * .9 + up * .12, .1, .05, ELECTRUM, ELECTRUM_PALE, up=up)
        bevel_box(p, a0 + (.25, 0, 0), (.42, .5, .5), ALLOY_DARK, ALLOY, .06)
    # cables from the pylon heads to the ring's shoulders, stays from the base to its haunches
    for sy in (-1, 1):
        for sx in (-1, 1):
            head = arr([sx * 1.5, sy * 14.4, HP + .9])
            sh = C + arr([sx * 1.0, sy * 15 * math.sin(math.radians(24)), 15 * math.cos(math.radians(24)) - .1])
            mid = (head + sh) / 2 + (0, 0, -1.1)
            tube(p, bezier(head, mid, mid, sh, 12), .07, ALLOY_DARK, ALLOY, 6)
            bevel_box(p, sh, (.3, .3, .22), ALLOY_SILVER, ALLOY, .04)
            foot = arr([sx * 1.6, sy * 8.2, 4.2])
            hn = C + arr([sx * 1.0, sy * 15 * math.sin(math.radians(34)), -15 * math.cos(math.radians(34)) + .1])
            tube(p, [foot, hn], .11, ALLOY_SILVER, ALLOY, 8)
            bevel_box(p, foot + (0, 0, .12), (.4, .4, .14), ALLOY_DARK, ALLOY, .04)
            bevel_box(p, hn, (.3, .3, .22), ALLOY_SILVER, ALLOY, .04)
    # the crown
    gbox(p, (-1.0, -.9, 38.8), (1.0, .9, 39.3), ALLOY, ALLOY_DARK, 1, .06)
    gem(p, (0, 0, 39.55), .3, .45, CRYSTAL, CRYSTAL_VIOLET, Z, 6, low=.3)
    lichens(p, rng, (-4.3, -3.5), (-17.5, 17.5), 1.5, 14, (.12, .4))
    lichens(p, rng, (-3.3, -2.3), (-12.5, 12.5), 3.0, 10, (.12, .4))
    lichens(p, rng, (3.6, 4.3), (-17.5, 17.5), 1.5, 6, (.1, .25))
    return done(p, 5210, reach=6.0, floor=.7, facts=dict(centre=(0.0, 0.0, 24.0), ring=30.0, faces='-x', pylons_y=(13.0, 18.0), core_radius=2.6,
                                                         vane_tips_x=-4.38))


# ---------------------------------------------------------------- props

@mesh('SM_AN_Obelisk', (1.2, 1.2, 4.2), tol=.03)
def obelisk():
    """A record stele: a chamfered foot block 1.2 m square, four tapering faces with softened arrises, a line of
    inlay down the front and the back, an alloy collar and a crystal tip to 4.2 m."""
    rng = np.random.default_rng(5220)
    p = Part('SM_AN_Obelisk', (STONE, ELECTRUM, ALLOY, CRYSTAL))
    gbox(p, (-.6, -.6, 0), (.6, .6, .3), STONE, STONE_PALE, .4, .04, 'z')

    def sq(h, z, ch=.035):
        return arr([(h, -h + ch, z), (h, h - ch, z), (h - ch, h, z), (-h + ch, h, z), (-h, h - ch, z), (-h, -h + ch, z), (-h + ch, -h, z), (h - ch, -h, z)])
    zs = np.linspace(.3, 3.55, 9)
    hs = .43 + (.25 - .43) * (zs - .3) / 3.25
    loft(p, [sq(h, z) for h, z in zip(hs, zs)], STONE, [rgb(vary(rng, STONE_PALE, .05)) for _ in zs])
    loft(p, [sq(.265, 3.55, .03), sq(.265, 3.63, .03)], ALLOY, ALLOY_SILVER, caps='t')
    tip = sq(.235, 3.63, .03)
    fan(p, (0, 0, 4.2), tip, CRYSTAL, CRYSTAL_ICE, Z, CRYSTAL_CLEAR)
    for sx in (-1, 1):
        ha, hb = .43 + (.25 - .43) * (.9 - .3) / 3.25, .43 + (.25 - .43) * (3.2 - .3) / 3.25
        inlay(p, (sx * ha, 0, .9), (sx * hb, 0, 3.2), .04, .006, X * sx)
        for z in (1.2, 1.55, 1.9, 2.25, 2.6):                 # the record's rows: short strokes either side of the line
            hh = .43 + (.25 - .43) * (z - .3) / 3.25
            for sy in (-1, 1):
                inlay(p, (sx * hh, sy * .06, z), (sx * hh, sy * (hh - .09), z), .02, .005, X * sx)
    return done(p, 5220, reach=1.2)


@mesh('SM_AN_Lantern', (.7, .7, 3.2), tol=.04)
def lantern():
    """A First One street lantern: a twelve-sided stone foot, a slender alloy stem with one knop, and three alloy
    fingers holding a crystal whose girdle is the Serene's ice-blue light."""
    p = Part('SM_AN_Lantern', (STONE, ALLOY, GLOW, CRYSTAL))
    lathe(p, [(.35, 0), (.35, .1), (.33, .12), (.24, .12), (.24, .26), (.22, .28), (.07, .28)], STONE_PALE, STONE, 12, (0, 0, 0), False)
    lathe(p, [(.075, .28), (.06, .36), (.048, 1.2), (.075, 1.25), (.075, 1.31), (.045, 1.36), (.036, 2.36), (.07, 2.42), (.085, 2.5), (.003, 2.5)],
          ALLOY_SILVER, ALLOY, 10)
    for j in range(3):
        a = TAU * j / 3 + .5
        d = arr([math.cos(a), math.sin(a), 0])
        pts = bezier(d * .07 + (0, 0, 2.46), d * .26 + (0, 0, 2.56), d * .2 + (0, 0, 2.95), d * .06 + (0, 0, 3.02), 10)
        tube(p, pts, np.linspace(.02, .011, 10), ALLOY_SILVER, ALLOY, 6)
    lamp(p, (0, 0, 2.84), .105, .36, GLOW_SERENE, band=.28)
    return done(p, 5221, reach=.8, facts=dict(light=(0.0, 0.0, 2.84)))


@mesh('SM_AN_Pedestal', (1.5, 1.5, 1.1), tol=.03)
def pedestal():
    """A plain plinth: a foot course 1.5 m square, a battered die with one band of inlay, a chamfered cap. Flat top
    at 1.1 m."""
    rng = np.random.default_rng(5222)
    p = Part('SM_AN_Pedestal', (STONE, ELECTRUM))
    gbox(p, (-.75, -.75, 0), (.75, .75, .22), STONE, STONE_PALE, .4, .035, 'z')
    s = gbox(p, (-.63, -.63, .22), (.63, .63, .9), STONE, vary(rng, STONE_PALE, .05), .3, .03)
    for sgn in (-1, 1):
        inlay(p, (sgn * .63, -.6, .72), (sgn * .63, .6, .72), .035, .005, X * sgn)
        inlay(p, (-.6, sgn * .63, .72), (.6, sgn * .63, .72), .035, .005, Y * sgn)
    batter(p, s, .12, 0, 0, .22)
    batter(p, s, .12, 1, 0, .22)
    gbox(p, (-.72, -.72, .9), (.72, .72, 1.1), STONE, STONE_PALE, .36, .045)
    return done(p, 5222, reach=.8, facts=dict(top=1.1))


@mesh('SM_AN_Basin', (6.0, 6.0, 1.0), tol=.02)
def basin():
    """A round cistern basin 6 m across: a stone drum in twelve stones with a broad flat rim and a line of inlay, and
    inside it a lining of blue glazed tiles down to a slightly dished floor at z 0.16 to 0.2 (hollow: the water is
    placed separately)."""
    rng = np.random.default_rng(5223)
    p = Part('SM_AN_Basin', (STONE, TILE, ELECTRUM, LICHEN))
    prof = [(3.0, 0), (3.0, .26), (2.96, .3), (2.93, .3), (2.9, .62), (2.88, .93), (2.9, .96), (2.9, .985), (2.885, 1.0), (2.64, 1.0), (2.4, 1.0), (2.385, .985),
            (2.385, .9)]
    s = lathe(p, prof, STONE_PALE, STONE, 72, (0, 0, 0), True)
    tint(p, s, lambda v: np.where(np.abs(((np.arctan2(v[:, 1], v[:, 0]) / TAU * 12) % 1.0) - .5) > .485, .62, 1.0))
    tile_lathe(p, rng, [(2.385, .9), (2.37, .72), (2.35, .54), (2.33, .37), (2.31, .2)], 60)
    tile_lathe(p, rng, [(2.31, .2), (1.95, .19), (1.6, .18), (1.25, .175), (.9, .17), (.55, .165)], 36)
    tile_lathe(p, rng, [(.55, .165), (.28, .16), (.02, .16)], 12, (TILE_TEAL, TILE_DEEP))
    lathe(p, [(2.67, 1.0), (2.67, 1.004), (2.61, 1.004), (2.61, 1.0)], ELECTRUM_PALE, ELECTRUM, 72, (0, 0, 0), False)
    for _ in range(12):
        a = rng.uniform(math.pi * .55, math.pi * 1.45)
        r = rng.choice([rng.uniform(2.42, 2.58), rng.uniform(2.7, 2.86)])
        lichen(p, rng, (math.cos(a) * r, math.sin(a) * r, 1.0), rng.uniform(.04, .1))
    return done(p, 5223, reach=.9, facts=dict(rim=1.0, floor=.2, inner_radius=2.385, water_to=.85))


@mesh('SM_AN_VaultDoor', (1.0, 6.0, 6.0), tol=.02)
def vault_door():
    """A sealed vault door, 6 by 6 m, facing +x: one slab with a raised border and a sunk field, eight lines of inlay
    running from the border to a round lock at its middle: alloy and electrum rings round a faceted crystal boss."""
    rng = np.random.default_rng(5224)
    p = Part('SM_AN_VaultDoor', (STONE, ALLOY, ELECTRUM, CRYSTAL))
    gbox(p, (-.4, -2.6, .4), (.4, 2.6, 5.6), STONE, vary(rng, STONE_PALE, .03), (.4, .65, .65), .02)
    for y0, y1, z0, z1 in ((-3, 3, 0, .45), (-3, 3, 5.55, 6.0), (-3, -2.55, .45, 5.55), (2.55, 3, .45, 5.55)):
        gbox(p, (-.5, y0, z0), (.5, y1, z1), STONE, vary(rng, STONE_PALE, .05), (.5, .75, .75), .045, 'z' if z0 == 0 else '')
    Cc = arr([.4, 0, 3.0])
    turn(p, [(1.25, 0), (1.25, .06), (1.2, .1), (1.0, .1), (.97, .06)], ALLOY, ALLOY_SILVER, 40, Cc, 'x', False)
    turn(p, [(.97, .04), (.97, .075), (.8, .075), (.78, .04)], ELECTRUM, ELECTRUM_PALE, 40, Cc, 'x', False)
    turn(p, [(.78, .03), (.78, .06), (.7, .08)], ALLOY, ALLOY_DARK, 40, Cc, 'x', False)
    # the crystal boss: a low faceted dome
    rings = [(.7, .07, 12), (.42, .092, 12), (.18, .1, 6)]
    prev = None
    for r, h, n in rings:
        a = np.linspace(0, TAU, n, endpoint=False) + (.26 if n == 12 and r < .5 else 0)
        ring = np.stack([np.full(n, .4 + h), np.cos(a) * r, 3.0 + np.sin(a) * r], 1)
        if prev is not None and len(prev) == len(ring):
            for j in range(n):
                k = (j + 1) % n
                c = k_of(mix(CRYSTAL_ICE, CRYSTAL_VIOLET, rng.uniform(0, .6)), rng.uniform(.7, 1.0))
                face(p, [prev[j], prev[k], ring[j]], CRYSTAL, c, X)
                face(p, [prev[k], ring[k], ring[j]], CRYSTAL, k_of(c, .85), X)
        elif prev is not None:
            for j in range(n):
                c = k_of(mix(CRYSTAL_ICE, CRYSTAL_VIOLET, rng.uniform(0, .6)), rng.uniform(.7, 1.0))
                face(p, [prev[2 * j], prev[(2 * j + 1) % 12], ring[j]], CRYSTAL, c, X)
                face(p, [prev[(2 * j + 1) % 12], prev[(2 * j + 2) % 12], ring[(j + 1) % n]], CRYSTAL, k_of(c, .9), X)
                face(p, [prev[(2 * j + 1) % 12], ring[(j + 1) % n], ring[j]], CRYSTAL, k_of(c, .8), X)
        prev = ring
    fan(p, (.4 + .105, 0, 3.0), prev, CRYSTAL, CRYSTAL_ICE, X, CRYSTAL_CLEAR)
    for j in range(8):
        t = TAU * j / 8
        d = arr([0, math.cos(t), math.sin(t)])
        reach = 2.55 / max(abs(d[1]), abs(d[2])) - .02
        inlay(p, Cc + d * 1.27, Cc + d * reach, .05, .006, X)
    turn(p, [(1.42, 0), (1.42, .006), (1.36, .006), (1.36, 0)], ELECTRUM, ELECTRUM_PALE, 40, Cc, 'x', False)
    return done(p, 5224, reach=1.5, facts=dict(lock=(.5, 0.0, 3.0)))


@mesh('SM_AN_Bench', (.7, 2.4, .9), tol=.04)
def bench():
    """A stone bench along y, facing +x: a seat slab 0.46 m high on two blocks, a low raked back with a line of
    inlay."""
    rng = np.random.default_rng(5225)
    p = Part('SM_AN_Bench', (STONE, ELECTRUM))
    for sy in (-1, 1):
        gbox(p, (-.3, sy * .62, 0), (.28, sy * 1.0, .37), STONE, vary(rng, STONE_SHADE, .06), .3, .03, 'z')
    s = gbox(p, (-.35, -1.2, .36), (.35, 1.2, .46), STONE, vary(rng, STONE_PALE, .04), (.35, .4, .1), .03)
    tint(p, s, lambda v: np.where(v[:, 2] > .459, .86 + .14 * np.abs(np.cos(v[:, 1] * 1.9)), 1.0))
    s = gbox(p, (-.33, -1.14, .46), (-.2, 1.14, .9), STONE, vary(rng, STONE_PALE, .05), (.13, .4, .22), .03)
    inlay(p, (-.2, -1.05, .74), (-.2, 1.05, .74), .03, .004, X)
    warp(p, s, lambda v: np.stack([np.maximum(v[:, 0] - (v[:, 2] - .46) * .045, -.35), v[:, 1], v[:, 2]], 1))
    return done(p, 5225, reach=.6, facts=dict(seat=.46))


@mesh('SM_AN_Urn', (.9, .9, 1.3), tol=.04)
def urn():
    """A tall glazed urn (TILE): a small foot, a full shoulder, a narrow neck with an electrum band and a flared lip;
    its glaze deep blue, lighter where it thinned on the shoulder."""
    p = Part('SM_AN_Urn', (TILE, ELECTRUM))
    prof = [(.2, 0), (.22, .03), (.2, .07)]
    for t in np.linspace(0, 1, 13):
        z = .1 + .9 * t
        prof.append((.19 + .26 * math.sin(math.pi * min(1, t * 1.02) ** .8) ** 1.0 * (1 - .32 * t), z))
    prof += [(.165, 1.06), (.16, 1.12), (.18, 1.2), (.235, 1.28), (.24, 1.3), (.21, 1.3), (.17, 1.2), (.13, 1.1), (.13, .8), (.003, .78)]
    rmax = max(q[0] for q in prof)
    prof = [(r * (.45 / rmax) if .1 <= z <= 1.0 else r, z) for r, z in prof]
    s = lathe(p, prof, TILE_DEEP, TILE, 24)
    teal = rgb(TILE_TEAL) / rgb(TILE_DEEP)
    tint(p, s, lambda v: (1 + (teal - 1) * (np.clip((v[:, 2] - .45) / .5, 0, 1) * (.5 + .5 * noise2(np.arctan2(v[:, 1], v[:, 0]) * 2.5, v[:, 2] * 4, 3)) *
                                           (np.hypot(v[:, 0], v[:, 1]) > .14))[:, None] * .45))
    tint(p, s, lambda v: np.where((np.hypot(v[:, 0], v[:, 1]) < .14) & (v[:, 2] < 1.25), .35, 1.0))
    lathe(p, [(.165, 1.05), (.178, 1.06), (.172, 1.11), (.16, 1.12)], ELECTRUM_PALE, ELECTRUM, 24)
    lathe(p, [(.2, .07), (.208, .075), (.2, .1), (.19, .1)], ELECTRUM_PALE, ELECTRUM, 24)
    return done(p, 5226, reach=.5)


# ---------------------------------------------------------------- the module's meshes and their contract

MESHES = list(_BUILDERS)
VARIANTS = dict(_VARIANTS)
CONTRACT = dict(_SIZES)
