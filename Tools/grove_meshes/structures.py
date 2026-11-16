"""Structures of the Wounded Grove (level 4, Earth): the SM_GN_ buildings and large props of Tools/grove/README.md.

Pure numpy through kit (the Conclave's toolkit and al_flora): check.py validates this module offline and
Tools/build_physis_grove.py builds it in Blender. Metres, Unreal axes (x forward, y right, z up); a mesh with a front
faces +x. Names, sizes, pivots, walk heights and openings are the README's table; CONTRACT at the end repeats the sizes
for check.py and FACTS holds the numbers the placement code needs (walk surfaces, doorways, light points), written by
the builders themselves so they cannot drift from the geometry.

How these are made to read as real (author, 2026-11-10: AAA, as realistic as possible):
  - Construction logic. Concrete is cast in lifts and panels with rustication grooves, chamfered arrises, copings with
    drips, tie holes, spalled corners with their bars showing. Steel is rolled sections (I, channel, angle, tube),
    plates with bolts, base plates on anchor bolts, handrails with stanchions, mid rail and toe board at 1.1 m,
    caged ladders, conduit and cable trays. Nothing floats: every part sits on, hangs from or is bolted to another.
  - Every builder lays its mesh out in the contract's own frame (no recentring afterwards), so a number in the table
    is a number in the code: a roof "at z 9.0" has its walk surface at exactly 9.0.
  - Walk surfaces are single continuous flat faces; what stands on them (moss, bolts, cover strips) is under 3 cm.
  - Vertex colour is the base albedo under the slot's scanned texture: paint() and age() put the weather in it (damp
    and darkening toward the ground, stains under ledges and fixings, rust blooms, moss films on tops and the shaded
    side), from each vertex's position and normal. Large faces are gridded so the weather has vertices to live on.
"""
from kit import *  # noqa: F401,F403

X, Y, Z = np.eye(3)
GREY = (.5, .5, .5, 1.0)       # placeholder albedo of geometry that paint() colours afterwards
FACTS = {}                     # mesh name -> the numbers placement needs (filled by the builders)
_BUILDERS, _SIZES = [], {}


def mesh(name, size, **spec):
    """Registers a builder and its contract row: size (x, y, z) in metres with 0 for any, and pivot, tol, top as
    check.py reads them."""
    def wrap(fn):
        _BUILDERS.append(fn)
        _SIZES[name] = dict(size=size, **spec)
        return fn
    return wrap


def V3(*a):
    return np.array(a, np.float64)


def unit(v):
    return fl.unit(v)


def rot(axis, deg):
    """Rotation matrix about 'x', 'y', 'z' or a vector, right-handed, degrees (about z: +x toward +y)."""
    a = math.radians(deg)
    k = unit({'x': X, 'y': Y, 'z': Z}[axis] if isinstance(axis, str) else axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * (K @ K)


def cells(length, cell):
    return max(1, int(math.ceil(abs(length) / cell - 1e-6)))


# ---------------------------------------------------------------- colour: materials as functions of place and normal

def _rgb(c):
    return np.asarray(c, np.float64)[:3]


def _out(c):
    c = np.clip(np.asarray(c, np.float64), 0.0, .9)
    return np.concatenate([c, np.ones((len(c), 1))], 1)


def _pn(P, N):
    P = np.asarray(P, np.float64).reshape(-1, 3)
    N = np.broadcast_to(np.asarray(N, np.float64), P.shape)
    return P, N, P[:, 0], P[:, 1], P[:, 2]


def concrete(seed=0, base=CONCRETE_PALE, stain=CONCRETE_STAIN, ground=0.0, damp=2.0, blot=.4, streak=.28, moss=.3,
             tide=None, ledges=(), north=(-1.0, 0.0), k=1.0, soffit=.7):
    """Weathered concrete: blotchy staining, damp rising from the ground, rain streaks down walls (heaviest under the
    ledges given as (z, reach)), a moss film on tops, at damp feet and on the `north` side; tide = a water line (dark
    and green below it, a pale scum line just above)."""
    base, stain, dark = _rgb(base), _rgb(stain), _rgb(CONCRETE_DARK)
    mg, md = _rgb(MOSS_GREEN), _rgb(MOSS_DEEP)

    def f(P, N):
        P, N, x, y, z = _pn(P, N)
        nz = N[:, 2]
        wall = np.abs(nz) < .6
        s = y * N[:, 0] - x * N[:, 1]
        b1 = .5 + .5 * noise2(x / 2.7 + z * .23 + 3.1, y / 2.7 - z * .19 + 7.7, seed + 1)
        b2 = .5 + .5 * noise2(x / .6 + z * 1.3, y / .6 - z * 1.1, seed + 2)
        g = np.clip(1 - (z - ground) / damp, 0, 1)
        st = np.maximum(0, noise2(s * 2.3 + seed * .71, z * .11 + 1.7, seed + 5))
        t = blot * (.65 * b1 + .35 * b2) + .5 * g ** 1.5 + np.where(wall, streak * st * (.5 + .5 * b1), 0)
        for zl, reach in ledges:
            d = zl - z
            t = t + np.where(wall & (d > -.02), .55 * np.exp(-np.maximum(d, 0) / reach) * (.4 + .6 * st), 0)
        t = np.clip(t, 0, 1)[:, None]
        c = base * (1 - t) + stain * t
        shade = k * (1 - .25 * g ** 2) * np.where(nz < -.6, soffit, 1.0) * np.where(nz > .6, 1.05, 1.0)
        up = np.clip((nz - .5) / .4, 0, 1)
        facing = np.clip(N[:, 0] * north[0] + N[:, 1] * north[1], 0, 1)
        m = moss * (up * np.clip(noise2(x / 1.9 + 9.0, y / 1.9, seed + 8) * 1.5 + .2, 0, 1) +
                    (1 - up) * (g ** 1.3 * (.35 + .65 * b2) * (.45 + .9 * facing) + .5 * facing * np.clip(b1 * 1.6 - .7, 0, 1)))
        if tide is not None:
            under = np.clip((tide + .25 - z) / .5, 0, 1)
            line = np.exp(-((z - tide - .45) / .22) ** 2) * (1 - up)
            c = c * (1 - .55 * under[:, None]) + dark * (.55 * under[:, None])
            m = np.maximum(m, .55 * under * (.5 + .5 * b2))
            c = c + (base * 1.12 - c) * (.45 * line)[:, None]
        m = np.clip(m, 0, .85)[:, None]
        mc = mg * (1 - b1[:, None] * .7) + md * (b1[:, None] * .7)
        return _out((c * (1 - m) + mc * m) * shade[:, None])
    return f


def steel(seed=0, base=STEEL_GREY, rust=.3, ground=0.0, damp=1.0, k=1.0, grime=.25, streak=.2, moss=0.0):
    """Weathered steel or painted plate: rust blooming where noise, damp and runs gather (rust = how much, 0..1),
    grime, darker soffits. For paint and enamel pass the paint's colour as base and a low rust."""
    base, r0, r1 = _rgb(base), _rgb(RUST_ORANGE), _rgb(RUST_DARK)
    mg = _rgb(MOSS_GREEN)

    def f(P, N):
        P, N, x, y, z = _pn(P, N)
        nz = N[:, 2]
        s = y * N[:, 0] - x * N[:, 1]
        b1 = .5 + .5 * noise2(x / 1.3 + z * .45 + 5.5, y / 1.3 - z * .4 + 2.2, seed + 11)
        b2 = .5 + .5 * noise2(x / .21 + z * 2.3, y / .21 - z * 1.9, seed + 12)
        g = np.clip(1 - (z - ground) / damp, 0, 1)
        st = np.maximum(0, noise2(s * 3.7 + seed * .37, z * .23, seed + 13)) * (np.abs(nz) < .6)
        r = np.clip((.62 * b1 + .38 * b2 + .5 * g ** 2 + .35 * st - (1 - rust)) / .22, 0, 1)[:, None]
        c = base * (1 - r) + (r0 * (1 - b2[:, None]) + r1 * b2[:, None]) * r
        shade = k * (1 - grime * b1) * (1 - .22 * g ** 2) * np.where(nz < -.6, .78, 1.0) * (1 - streak * st * (1 - r[:, 0]))
        if moss:
            m = (moss * np.clip((nz - .5) / .4, 0, 1) * np.clip(b1 * 1.6 - .5, 0, 1))[:, None]
            c = c * (1 - m) + mg * m
        return _out(c * shade[:, None])
    return f


def flat(colour, k=1.0):
    c = _rgb(colour) * k

    def f(P, N):
        return _out(np.tile(c, (len(np.asarray(P).reshape(-1, 3)), 1)))
    return f


# ---------------------------------------------------------------- painting what was built

def mark(p):
    """Where the part stands now: paint() and age() work on everything added after a mark."""
    return len(p.v), len(p.f)


def normals_of(p, m):
    """Vertices added since mark m and their area-weighted normals."""
    v0, f0 = m
    v = np.asarray(p.v[v0:], np.float64).reshape(-1, 3)
    n = np.zeros_like(v)
    by_len = {}
    for f in p.f[f0:]:
        by_len.setdefault(len(f), []).append(f)
    for length, fs in by_len.items():
        F = np.asarray(fs, np.int64) - v0
        Q = v[F]
        nrm = np.cross(Q, np.roll(Q, -1, 1)).sum(1)
        for j in range(length):
            np.add.at(n, F[:, j], nrm)
    return v, unit(n)


def _kept(p, m, keep):
    v0, f0 = m
    lit = np.zeros(len(p.v) - v0, bool)
    ks = [p.slots.index(s) for s in keep if s in p.slots]
    if ks:
        for f, mm in zip(p.f[f0:], p.m[f0:]):
            if mm in ks:
                lit[np.asarray(f) - v0] = True
    return lit


def paint(p, m, fn, keep=(GLOW, GLASS, LEAF)):
    """Colours everything added since mark m with material fn(points, normals), except faces of the keep slots."""
    v, n = normals_of(p, m)
    if not len(v):
        return
    cols = np.asarray(fn(v, n), np.float64)
    lit = _kept(p, m, keep)
    if lit.any():
        cols[lit] = np.asarray(p.c[m[0]:], np.float64)[lit]
    p.c[m[0]:] = cols.tolist()


def age(p, m, seed=0, ground=0.0, reach=1.2, floor=.6, grime=.22, streak=.12, rust=0.0, moss=0.0, scale=.9,
        keep=(GLOW, GLASS, LEAF)):
    """Weathers colours given at build time (livery, timber): darkening toward the ground, blotches, runs down
    vertical faces, rust blooms (rust 0..1) and a moss film on tops and damp feet (moss 0..1)."""
    v, n = normals_of(p, m)
    if not len(v):
        return
    c = np.asarray(p.c[m[0]:], np.float64)
    lit = _kept(p, m, keep)
    x, y, z = v.T
    nz = n[:, 2]
    b1 = .5 + .5 * noise2(x / scale + z * .37 / scale, y / scale - z * .41 / scale, seed + 3)
    b2 = .5 + .5 * noise2(x / (.22 * scale) + z * 2, y / (.22 * scale) - z * 2, seed + 4)
    g = np.clip(1 - (z - ground) / reach, 0, 1)
    s = y * n[:, 0] - x * n[:, 1]
    st = np.maximum(0, noise2(s * 4.1 + seed, z * .25, seed + 5)) * (np.abs(nz) < .6)
    k = (floor + (1 - floor) * (1 - g)) * (1 - grime * b1) * (1 - streak * st) * np.where(nz < -.6, .8, 1.0)
    rgb = c[:, :3]
    if rust:
        r = np.clip((.6 * b1 + .4 * b2 + .45 * g ** 2 + .3 * st - (1 - rust)) / .2, 0, 1)[:, None] * .9
        rgb = rgb * (1 - r) + (_rgb(RUST_ORANGE) * (1 - b2[:, None]) + _rgb(RUST_DARK) * b2[:, None]) * r
    if moss:
        up = np.clip((nz - .5) / .4, 0, 1)
        mm = np.clip(moss * (up * np.clip(b1 * 1.7 - .35, 0, 1) + (1 - up) * g ** 1.5 * b2), 0, .85)[:, None]
        rgb = rgb * (1 - mm) + (_rgb(MOSS_GREEN) * (1 - b1[:, None] * .6) + _rgb(MOSS_DEEP) * b1[:, None] * .6) * mm
    rgb = np.clip(rgb * k[:, None], 0, .9)
    c[~lit, :3] = rgb[~lit]
    p.c[m[0]:] = c.tolist()


def shade(p, m, k):
    """Multiplies the colours added since mark m by k."""
    c = np.asarray(p.c[m[0]:], np.float64)
    if len(c):
        c[:, :3] *= k
        p.c[m[0]:] = c.tolist()


def place(p, m, R=None, t=(0, 0, 0)):
    """Turns (matrix R) then moves everything added since mark m."""
    fl.place(p, m[0] if isinstance(m, tuple) else m, R, t)


# ---------------------------------------------------------------- geometry: gridded faces and solids

def gquad(p, a, b, c, d, slot, nu=1, nv=1, colour=GREY, smooth=False):
    """A patch a-b-c-d (counter-clockwise seen from its front) of nu cells along a->b and nv along a->d."""
    a, b, c, d = (np.asarray(q, np.float64) for q in (a, b, c, d))
    s = np.linspace(0, 1, nu + 1)[:, None, None]
    t = np.linspace(0, 1, nv + 1)[None, :, None]
    pts = (a * (1 - s) + b * s) * (1 - t) + (d * (1 - s) + c * s) * t
    n = nv + 1
    faces = [[i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1] for i in range(nu) for j in range(nv)]
    return p.add(pts.reshape(-1, 3), faces, colour, slot, smooth)


def face(p, pts, slot, toward=None, colour=GREY, smooth=False):
    """One flat polygon, turned to face `toward` (a direction) when given."""
    pts = np.asarray(pts, np.float64)
    order = list(range(len(pts)))
    if toward is not None:
        n = np.cross(pts, np.roll(pts, -1, 0)).sum(0)
        if np.dot(n, toward) < 0:
            order = order[::-1]
    return p.add(pts, [order], colour, slot, smooth)


def gface(p, a, b, c, d, slot, cell=1.0, toward=None, colour=GREY):
    """gquad with its cell count from a cell size, turned to face `toward` when given."""
    a, b, c, d = (np.asarray(q, np.float64) for q in (a, b, c, d))
    if toward is not None and np.dot(np.cross(b - a, d - a) + np.cross(c - b, a - b), toward) < 0:
        b, d = d, b
    return gquad(p, a, b, c, d, slot, cells(np.linalg.norm(b - a), cell), cells(np.linalg.norm(d - a), cell), colour)


_FACE = {(0, -1): 'x', (0, 1): 'X', (1, -1): 'y', (1, 1): 'Y', (2, -1): 'z', (2, 1): 'Z'}


def gbox(p, lo, hi, slot, cell=1.0, bevel=.02, skip='', colour=GREY):
    """An axis-aligned box between corners lo and hi with chamfered arrises, its faces gridded at about `cell` metres.
    skip: faces left out, of 'x' (the -x face), 'X' (+x), 'y', 'Y', 'z' (bottom), 'Z' (top); the faces round a
    skipped one run out to its plane unchamfered, so a box that stands on the ground starts at exactly its lo z."""
    lo, hi = np.asarray(lo, np.float64), np.asarray(hi, np.float64)
    lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
    e = np.minimum(bevel, (hi - lo) * .225) if bevel > 0 else np.zeros(3)
    on = {(a, s): _FACE[(a, s)] not in skip for a in range(3) for s in (-1, 1)}
    ext = {-1: lo, 1: hi}                                                          # a face's own plane
    inn = {-1: lo + e * [on[(a, -1)] for a in range(3)], 1: hi - e * [on[(a, 1)] for a in range(3)]}   # where its neighbours stop
    n = [cells(inn[1][a] - inn[-1][a], cell) for a in range(3)]
    start = len(p.v)

    def pt(coords):
        return np.array([coords[0], coords[1], coords[2]], np.float64)
    for a in range(3):
        o0, o1 = (a + 1) % 3, (a + 2) % 3
        for s in (-1, 1):
            if not on[(a, s)]:
                continue
            q = []
            for u, w in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                c = [0.0, 0.0, 0.0]
                c[a], c[o0], c[o1] = ext[s][a], inn[u][o0], inn[w][o1]
                q.append(pt(c))
            if s > 0:
                gquad(p, q[0], q[1], q[2], q[3], slot, n[o0], n[o1], colour)
            else:
                gquad(p, q[0], q[3], q[2], q[1], slot, n[o1], n[o0], colour)
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
                    ca, cb = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
                    ca[a], ca[b], ca[k] = ext[sa][a], inn[sb][b], inn[sk][k]
                    cb[a], cb[b], cb[k] = inn[sa][a], ext[sb][b], inn[sk][k]
                    ends.append((pt(ca), pt(cb)))
                (a0, b0), (a1, b1) = ends
                out = np.zeros(3)
                out[a], out[b] = sa, sb
                if np.dot(np.cross(a1 - a0, b0 - a0), out) < 0:
                    a0, a1, b0, b1 = a1, a0, b1, b0
                gquad(p, a0, a1, b1, b0, slot, n[k], 1, colour)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                sg = (sx, sy, sz)
                if not all(on[(a, sg[a])] for a in range(3)):
                    continue
                tri = []
                for a in range(3):
                    c = [inn[sg[b]][b] for b in range(3)]
                    c[a] = ext[sg[a]][a]
                    tri.append(pt(c))
                face(p, tri, slot, np.array(sg, np.float64), colour)
    return start


def gprism(p, base, top, slot, cell=1.0, caps='bt', colour=GREY, smooth=False):
    """A solid between two polygons with matching corners (base and top, any winding): its sides gridded at about
    `cell` metres, its ends closed as caps says ('b' the base, 't' the top)."""
    base, top = np.asarray(base, np.float64), np.asarray(top, np.float64)
    axis = top.mean(0) - base.mean(0)
    if np.dot(np.cross(base, np.roll(base, -1, 0)).sum(0), axis) < 0:
        base, top = base[::-1], top[::-1]
    n = len(base)
    start = len(p.v)
    for k in range(n):
        a, b, c, d = base[k], base[(k + 1) % n], top[(k + 1) % n], top[k]
        gquad(p, a, b, c, d, slot, cells(np.linalg.norm(b - a), cell), cells(np.linalg.norm(d - a), cell), colour, smooth)
    if 't' in caps:
        if n == 4:
            gquad(p, top[0], top[1], top[2], top[3], slot, cells(np.linalg.norm(top[1] - top[0]), cell),
                  cells(np.linalg.norm(top[3] - top[0]), cell), colour)
        else:
            p.add(top, [list(range(n))], colour, slot, False)
    if 'b' in caps:
        if n == 4:
            gquad(p, base[0], base[3], base[2], base[1], slot, cells(np.linalg.norm(base[3] - base[0]), cell),
                  cells(np.linalg.norm(base[1] - base[0]), cell), colour)
        else:
            p.add(base, [list(range(n))[::-1]], colour, slot, False)
    return start


def sheet(p, o, u, v, L, H, T, slot=CONCRETE, holes=(), mask=None, ju=(), jv=(), sub=1.2, groove=(.02, .012),
          arris=.015, back=True, rim='lrbt', ragged=0.0, rng=None, ties=None, fn=None, colour=GREY):
    """A wall or slab with real thickness. Its front lies in the plane through o spanned by unit vectors u and v (front
    normal u x v: for a wall facing +x, u = +y and v = +z), L by H metres, T thick behind the front. holes: rectangles
    (u0, u1, v0, v1) cut through it, with reveals. mask(uc, vc) is False where a panel is missing (broken walls). ju,
    jv: joints along u and v where a V-groove (groove = (width, depth)) is cut between neighbouring panels: formwork
    lifts, panel and expansion joints. Panels larger than `sub` are split without a joint so weathering has vertices.
    rim: the outer edges that get an edge face (l: u = 0, r: u = L, b: v = 0, t: v = H); free edges are chamfered
    by `arris`. ragged: how far free top corners may drop (broken tops; needs rng). ties = (du, dv, r): formwork tie
    holes as dark dots on that grid. fn: the material that paints it (before the tie holes go on). Returns (U, V,
    solid) for whoever dresses the wall."""
    o, u, v = np.asarray(o, np.float64), unit(u), unit(v)
    f = np.cross(u, v)
    gw, gd = groove

    def lines(total, edges, joints):
        pts = {0.0: False, round(float(total), 4): False}
        for e in edges:
            if 1e-3 < e < total - 1e-3:
                pts.setdefault(round(float(e), 4), False)
        for j in joints:
            if 1e-3 < j < total - 1e-3:
                pts[round(float(j), 4)] = True
        keys = sorted(pts)
        out, flag = [], []
        for a, b in zip(keys, keys[1:]):
            out.append(a)
            flag.append(pts[a])
            k = cells(b - a, sub)
            for i in range(1, k):
                out.append(a + (b - a) * i / k)
                flag.append(False)
        out.append(keys[-1])
        flag.append(False)
        return np.array(out), flag
    U, JU = lines(L, [e for hh in holes for e in hh[:2]], ju)
    V, JV = lines(H, [e for hh in holes for e in hh[2:4]], jv)
    nu, nv = len(U) - 1, len(V) - 1
    uc, vc = (U[:-1] + U[1:]) / 2, (V[:-1] + V[1:]) / 2
    hole = np.zeros((nu, nv), bool)
    for hh in holes:
        hole |= ((uc > hh[0]) & (uc < hh[1]))[:, None] & ((vc > hh[2]) & (vc < hh[3]))[None, :]
    solid = ~hole
    if mask is not None:
        for i in range(nu):
            for j in range(nv):
                if solid[i, j] and not mask(uc[i], vc[j]):
                    solid[i, j] = False
    VN = np.tile(V[None, :], (nu + 1, 1))
    if ragged and rng is not None:
        for i in range(nu + 1):
            for j in range(1, nv + 1):
                near = [k for k in (i - 1, i) if 0 <= k < nu]
                below = [solid[k, j - 1] for k in near]
                blocked = [hole[k, j - 1] for k in near] + ([solid[k, j] or hole[k, j] for k in near] if j < nv else [])
                if any(below) and not any(blocked):
                    VN[i, j] -= rng.uniform(0, 1) * min(ragged, .8 * (V[j] - V[j - 1]))
    verts, faces = [], []

    def P(a, b, d=0.0):
        return o + u * a + v * b - f * d

    def quad(q, toward):
        q = np.asarray(q)
        n = np.cross(q[1] - q[0], q[2] - q[0]) + np.cross(q[2] - q[0], q[3] - q[0])
        if np.linalg.norm(n) < 1e-12:
            return
        base = len(verts)
        verts.extend(q if np.dot(n, toward) >= 0 else q[::-1])
        faces.append([base, base + 1, base + 2, base + 3])
    for i in range(nu):
        for j in range(nv):
            if not solid[i, j]:
                continue
            u0, u1 = U[i], U[i + 1]
            b00, b10, b11, b01 = VN[i, j], VN[i + 1, j], VN[i + 1, j + 1], VN[i, j + 1]
            spec = {}
            for key, ii, jj, joint in (('l', i - 1, j, JU[i]), ('r', i + 1, j, JU[i + 1]), ('b', i, j - 1, JV[j]), ('t', i, j + 1, JV[j + 1])):
                if 0 <= ii < nu and 0 <= jj < nv:
                    if solid[ii, jj]:
                        spec[key] = (gw / 2, gd, False) if joint and gd > 0 else None
                    else:
                        spec[key] = (arris, arris, True)
                else:
                    spec[key] = (arris, arris, True) if key in rim else None
            il, ir, ib, it = (spec[k][0] if spec[k] else 0.0 for k in 'lrbt')
            F = [(u0 + il, b00 + ib), (u1 - ir, b10 + ib), (u1 - ir, b11 - it), (u0 + il, b01 - it)]
            D = [(u0, b00), (u1, b10), (u1, b11), (u0, b01)]
            quad([P(*q) for q in F], f)
            for key, (k0, k1), out in (('b', (0, 1), -v), ('r', (1, 2), u), ('t', (2, 3), v), ('l', (3, 0), -u)):
                if spec[key] is None:
                    continue
                _inset, dp, edge = spec[key]
                if dp > 0:
                    quad([P(*F[k0]), P(*F[k1]), P(*D[k1], dp), P(*D[k0], dp)], f + out * .5)
                if edge and T > dp:
                    quad([P(*D[k0], dp), P(*D[k1], dp), P(*D[k1], T), P(*D[k0], T)], out)
            if back:
                quad([P(*q, T) for q in D], -f)
    m0 = mark(p)
    if verts:
        p.add(verts, faces, colour, slot, False)
        if fn is not None:
            paint(p, m0, fn)
    if ties:
        du, dv, r = ties
        pts = []
        for a in np.arange(du / 2, L, du):
            for b in np.arange(dv / 2, H, dv):
                i, j = int(np.searchsorted(U, a) - 1), int(np.searchsorted(V, b) - 1)
                if 0 <= i < nu and 0 <= j < nv and solid[i, j] and min(a - U[i], U[i + 1] - a, b - V[j], VN[i, j + 1] - b, VN[i + 1, j + 1] - b) > r * 2.5:
                    pts.append(P(a, b))
        dots(p, pts, f, r, slot, tone(CONCRETE_DARK, .55))
    return U, V, solid


def dots(p, pts, normal, r, slot, colour, sides=6, lift=.002):
    """Flat round marks just proud of a surface: tie holes, drain mouths, plugs."""
    pts = np.asarray(pts, np.float64).reshape(-1, 3)
    if not len(pts):
        return
    n = unit(normal)
    a, b = frame(n)
    ang = np.linspace(0, TAU, sides, endpoint=False)
    ring = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
    verts = (pts[:, None, :] + n * lift + r * ring[None]).reshape(-1, 3)
    p.add(verts, [[i * sides + j for j in range(sides)] for i in range(len(pts))], colour, slot, False)


def turn(p, profile, slot, sides=16, c=(0, 0, 0), axis=Z, colour=GREY, hard=True, arc=TAU, start=0.0):
    """A surface of revolution around `axis` through c from a profile [(radius, height), ...] listed counter-clockwise
    in the (radius, height) half-plane (up the outside, in over the top), so its faces look outward. hard: every
    profile segment is its own band, with crisp edges between bands."""
    m = len(p.v)
    prof = [tuple(map(float, q)) for q in profile]
    if hard:
        for a, b in zip(prof, prof[1:]):
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1e-9:
                lathe(p, [a, b], colour, slot, sides, (0, 0, 0), True, arc, start)
    else:
        lathe(p, prof, colour, slot, sides, (0, 0, 0), True, arc, start)
    fl.place(p, m, None if np.allclose(unit(axis), Z) else fl.along(axis), c)
    return m


def disc(p, c, r, slot, axis=Z, sides=16, colour=GREY, r_in=0.0):
    """A flat disc (or ring, with r_in) facing along axis."""
    a, b = frame(axis)
    ang = np.linspace(0, TAU, sides, endpoint=False)
    ring = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
    c = np.asarray(c, np.float64)
    if r_in <= 0:
        return p.add(c + r * ring, [list(range(sides))], colour, slot, False)
    verts = np.concatenate([c + r_in * ring, c + r * ring])
    return p.add(verts, [[j, sides + j, sides + (j + 1) % sides, (j + 1) % sides] for j in range(sides)], colour, slot, False)


# ---------------------------------------------------------------- geometry: steel sections and fixings

def _axes(a, b, up=Z):
    """(forward, side, up) of a member from a to b: up as near to `up` as it can be, side = up x forward."""
    f = unit(np.asarray(b, np.float64) - np.asarray(a, np.float64))
    w = np.asarray(up, np.float64)
    if abs(np.dot(unit(w), f)) > .97:
        w = X if abs(f[0]) < .9 else Y
    s = unit(np.cross(w, f))
    return f, s, np.cross(f, s)


def bar(p, a, b, w, h, slot, up=Z, colour=GREY):
    """A rectangular member from a to b, w wide (across) and h deep (along up): flats, rails, plates, timbers."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    _f, s, t = _axes(a, b, up)
    pts = [(a if xb == 0 else b) + s * (w / 2 if yb else -w / 2) + t * (h / 2 if zb else -h / 2)
           for zb in (0, 1) for yb in (0, 1) for xb in (0, 1)]
    return hexa(p, pts, colour, slot)


def ibeam(p, a, b, depth, width, slot, up=Z, colour=GREY, tf=None, tw=None):
    """A rolled I or H section from a to b, depth along up."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    _f, _s, t = _axes(a, b, up)
    tf = tf or max(.012, depth * .07)
    tw = tw or max(.008, depth * .045)
    m = len(p.v)
    for sg in (-1, 1):
        off = t * sg * (depth - tf) / 2
        bar(p, a + off, b + off, width, tf, slot, t, colour)
    bar(p, a, b, tw, depth - 2 * tf, slot, t, colour)
    return m


def channel(p, a, b, depth, width, slot, up=Z, toes=1, colour=GREY, t=None):
    """A rolled channel from a to b: web `depth` along up, flanges `width` toward side * toes (side = up x forward)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    _f, s, w = _axes(a, b, up)
    t = t or max(.008, depth * .06)
    m = len(p.v)
    bar(p, a, b, t, depth, slot, w, colour)
    for sg in (-1, 1):
        off = w * sg * (depth - t) / 2 + s * toes * (width / 2)
        bar(p, a + off, b + off, width, t, slot, w, colour)
    return m


def angle(p, a, b, size, slot, d1, d2, colour=GREY, t=None):
    """A rolled angle from a to b, its legs reaching `size` along the directions d1 and d2 from the heel line a-b."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    f = unit(b - a)
    t = t or max(.006, size * .1)
    m = len(p.v)
    for e, o in ((d1, d2), (d2, d1)):
        e = unit(np.asarray(e, np.float64) - f * np.dot(e, f))
        o = unit(np.asarray(o, np.float64) - f * np.dot(o, f))
        off = e * size / 2 + o * t / 2
        bar(p, a + off, b + off, size, t, slot, o, colour)
    return m


def pipe(p, pts, r, slot, sides=12, colour=GREY, cap=True):
    """A round member through the points (a tube, a rod, a cable), its section carried along the path."""
    return fl.limb(p, pts, r, colour, slot, sides, cap)


def arc_pts(c, r, a0, a1, e0, e1, n=8):
    """Points on an arc around c in the plane of unit vectors e0, e1, from angle a0 to a1 (degrees)."""
    t = np.radians(np.linspace(a0, a1, n))
    return np.asarray(c, np.float64) + r * (np.cos(t)[:, None] * np.asarray(e0, np.float64) + np.sin(t)[:, None] * np.asarray(e1, np.float64))


def bolts(p, pts, normal, r, slot, colour=GREY, h=None, washer=True):
    """Hexagon bolt heads or nuts seated on a surface (one normal for all), each on a washer."""
    pts = np.asarray(pts, np.float64).reshape(-1, 3)
    if not len(pts):
        return
    n = unit(normal)
    a, b = frame(n)
    h = h or r * .8
    ang = np.linspace(0, TAU, 6, endpoint=False)
    ring = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
    verts, faces = [], []
    for q in pts:
        k = len(verts)
        verts.extend(q + r * ring)
        verts.extend(q + n * h + r * .9 * ring)
        faces += [[k + j, k + (j + 1) % 6, k + 6 + (j + 1) % 6, k + 6 + j] for j in range(6)]
        faces.append([k + 6 + j for j in range(6)])
    p.add(verts, faces, colour, slot, False)
    if washer:
        dots(p, pts, n, r * 1.5, slot, colour, 8, max(.0015, r * .12))


def flange(p, c, axis, r_pipe, r, t, slot, n_bolts=8, colour=GREY, sides=16):
    """A bolted pipe flange pair around `axis` at c: two discs and a ring of bolts through them."""
    axis = unit(axis)
    turn(p, [(r_pipe, -t), (r, -t), (r, t), (r_pipe, t)], slot, sides, c, axis, colour)
    a, b = frame(axis)
    ang = np.linspace(0, TAU, n_bolts, endpoint=False) + .2
    ring = (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b) * (r_pipe + r) / 2
    br = min(.03, (r - r_pipe) * .28)
    c = np.asarray(c, np.float64)
    bolts(p, c + ring + axis * t, axis, br, slot, colour, washer=False)
    bolts(p, c + ring - axis * t, -axis, br, slot, colour, washer=False)


def plate(p, poly, thick, slot, colour=GREY):
    """A flat plate cut to a polygon (gussets, brackets, fins), `thick` through, centred on the polygon's plane."""
    poly = np.asarray(poly, np.float64)
    n = unit(np.cross(poly, np.roll(poly, -1, 0)).sum(0))
    return gprism(p, poly - n * thick / 2, poly + n * thick / 2, slot, 99.0, 'bt', colour)


def handrail(p, pts, slot=STEEL, h=1.1, spacing=1.5, toe=.12, colour=GREY, inward=None, base=True, r=.021, ends=(True, True)):
    """An industrial guard rail along a polyline of points on the deck: tube stanchions on bolted base plates at no more
    than `spacing`, a top rail at h (1.1 m), a mid rail at half that and a toe board (toe = its height, 0 for none)
    on the `inward` side of the stanchions. ends: whether the first and last points get a stanchion."""
    pts = [np.asarray(q, np.float64) for q in pts]
    posts = []
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        n = cells(np.linalg.norm(b - a), spacing)
        for i in range(n + 1 if k == len(pts) - 2 else n):
            posts.append((a + (b - a) * i / n, unit(b - a)))
    if not ends[0]:
        posts = posts[1:]
    if not ends[1]:
        posts = posts[:-1]
    for q, d in posts:
        pipe(p, [q, q + Z * h], r, slot, 8, colour, cap=False)
        if base:
            side = np.cross(Z, d)
            bar(p, q - d * .07 + Z * .006, q + d * .07 + Z * .006, .14, .012, slot, Z, colour)
            bolts(p, [q + d * sx * .05 + side * sy * .05 + Z * .012 for sx in (-1, 1) for sy in (-1, 1)], Z, .009, slot, colour, washer=False)
    for z, rr in ((h, r), (h * .5, r * .8)):
        pipe(p, [q + Z * z for q in pts], rr, slot, 8, colour)
    if toe:
        for a, b in zip(pts, pts[1:]):
            d = unit(b - a)
            side = np.cross(Z, d) if inward is None else unit(np.asarray(inward, np.float64) - d * np.dot(inward, d))
            off = side * (r + .004) + Z * (toe / 2 + .01)
            bar(p, a + off, b + off, .006, toe, slot, Z, colour)


def ladder(p, foot, height, out, slot=STEEL, width=.45, standoff=.2, cage_from=2.3, cage=True, extend=1.1, colour=GREY):
    """A fixed access ladder up a wall: foot = where its centre line meets the wall at the bottom, out = the unit
    direction away from the wall. Flat stringers on stand-off brackets, rungs at 0.3 m, and from cage_from a safety
    cage of hoops and straps; the stringers run `extend` above the top to step through."""
    foot, out = np.asarray(foot, np.float64), unit(out)
    side = np.cross(Z, out)
    top = height + extend
    for s in (-1, 1):
        q = foot + out * standoff + side * s * width / 2
        bar(p, q, q + Z * top, .06, .012, slot, side, colour)
        for z in np.arange(.5, height, 1.6):
            bar(p, q + Z * z - out * standoff, q + Z * z, .05, .01, slot, Z, colour)
    for z in np.arange(.3, height + .01, .3):
        q = foot + out * standoff + Z * z
        pipe(p, [q - side * width / 2, q + side * width / 2], .011, slot, 6, colour, cap=False)
    if cage and top > cage_from + .5:
        r = .36
        c0 = foot + out * (standoff + r)
        hoops = np.arange(cage_from, top + .01, .9)
        for z in hoops:
            arc = arc_pts(c0 + Z * z, r, -115, 115, out, side, 11)
            for a, b in zip(arc, arc[1:]):
                bar(p, a, b, .05, .006, slot, Z, colour)
            for s in (-1, 1):
                bar(p, arc[0 if s < 0 else -1], foot + out * standoff + side * s * width / 2 + Z * z, .05, .006, slot, Z, colour)
        for ang in (-90, -45, 0, 45, 90):
            d = out * math.cos(math.radians(ang)) + side * math.sin(math.radians(ang))
            bar(p, c0 + d * r + Z * hoops[0], c0 + d * r + Z * hoops[-1], .04, .005, slot, d, colour)


def conduit(p, pts, wall, slot=STEEL, r=.016, every=.9, colour=GREY):
    """An electrical conduit along a wall (wall = the wall's outward normal), held by saddle clips."""
    pts = [np.asarray(q, np.float64) for q in pts]
    pipe(p, pts, r, slot, 6, colour)
    wall = unit(wall)
    for a, b in zip(pts, pts[1:]):
        n = cells(np.linalg.norm(b - a), every)
        d = unit(b - a)
        for i in range(n):
            q = a + (b - a) * (i + .5) / n
            bar(p, q - d * .012 - wall * r, q + d * .012 - wall * r, r * 4.4, .004, slot, wall, colour)
            bar(p, q - d * .012, q + d * .012, r * 2.3, r * 2.2, slot, wall, colour)


def bulkhead(p, c, normal, slot=STEEL, glow=GLOW_AMBER, r=.11, k=1.0, colour=STEEL_DARK):
    """A bulkhead light on a wall at c: a cast back box, a lens (GLOW) and a guard of two bars."""
    c, n = np.asarray(c, np.float64), unit(normal)
    turn(p, [(r * 1.25, 0), (r * 1.25, .05), (r * 1.05, .07)], slot, 12, c, n, colour)
    m = len(p.v)
    fl.ball(p, (0, 0, 0), r, tone(glow, k), GLOW, 10, (1, 1, .62))
    fl.place(p, m, fl.along(n), c + n * .06)
    a, b = frame(n)
    for d in (a, b):
        arc = arc_pts(c + n * .06, r * 1.08, 0, 180, d, n, 7)
        pipe(p, arc, .006, slot, 4, colour, cap=False)


def streaks(p, rng, pts, normal, length=(.4, 1.2), width=(.04, .1), colour=RUST_ORANGE, slot=RUST, fade=.5):
    """Run-off stains below fixings: thin tapering strips hung from the points, 3 mm off the surface whose outward
    normal is given, darkening to `fade` of their colour at their pointed tails (the colour stays in its own slot's
    range: a tinted scan blows out under a colour far brighter than the slot's reference)."""
    n = unit(normal)
    side = unit(np.cross(Z, n)) if abs(n[2]) < .95 else X
    down = np.cross(n, side)
    down = down if down[2] < 0 else -down
    top, tail = _rgb(colour), _rgb(colour) * fade
    for q in np.asarray(pts, np.float64).reshape(-1, 3):
        L, w = rng.uniform(*length), rng.uniform(*width)
        q = q + n * .003
        mid = q + down * L * .45 + side * rng.normal(0, .01)
        end = q + down * L + side * rng.normal(0, .02)
        verts = [q - side * w / 2, q + side * w / 2, mid + side * w * .32, mid - side * w * .32, end]
        cols = [top * rng.uniform(.7, 1), top * rng.uniform(.7, 1), (top + tail) / 2, (top + tail) / 2, tail]
        faces = [fl._facing(verts, [0, 1, 2, 3], n), fl._facing(verts, [3, 2, 4], n)]
        p.add(verts, faces, _out(cols), slot, False)


def rebar(p, rng, base, direction, length, slot=RUST, r=.011, droop=.35, bend=.25):
    """A reinforcing bar torn out of broken concrete: from base along direction, bent and sagging."""
    base, d = np.asarray(base, np.float64), unit(direction)
    j = rng.normal(0, bend, 3)
    mid = base + d * length * .5 + j * length * .2
    end = base + d * length + j * length * .5 - Z * droop * length * rng.uniform(.3, 1)
    cols = _out([_rgb(RUST_DARK) * 1.1, _rgb(RUST_ORANGE) * rng.uniform(.6, .9), _rgb(RUST_ORANGE) * rng.uniform(.5, .8)])
    fl.limb(p, [base - d * .03, mid, end], r, cols, slot, 5)


def rubble(p, rng, c, rx, ry, count, size=(.15, .5), slot=CONCRETE, z0=0.0, colour=GREY):
    """Tumbled broken concrete round c: angular blocks half bedded in the ground at z0."""
    for _ in range(count):
        a, rr = rng.uniform(0, TAU), rng.uniform(0, 1) ** .7
        s = rng.uniform(*size, 3) * np.array([1.3, 1.0, .7])
        q = np.array([c[0] + math.cos(a) * rx * rr, c[1] + math.sin(a) * ry * rr, z0 + s[2] * rng.uniform(.1, .45)])
        R = rot(rng.normal(0, 1, 3), rng.uniform(0, 60)) @ rot('z', rng.uniform(0, 360))
        corners = np.array([[sx, sy, sz] for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)], np.float64) * s / 2
        corners = corners * rng.uniform(.75, 1.1, (8, 1))
        pts = corners @ R.T + q
        pts[:, 2] = np.maximum(pts[:, 2], z0)
        hexa(p, pts, colour, slot)


# ---------------------------------------------------------------- growth: moss and what took the ruins back

def moss_patch(p, rng, c, r, h=.022, normal=Z, n=9):
    """A low cushion of moss on a surface at c (MOSS), under 3 cm so a walk surface stays one."""
    c, nrm = np.asarray(c, np.float64), unit(normal)
    a, b = frame(nrm)
    ang = np.linspace(0, TAU, n, endpoint=False) + rng.uniform(0, TAU)
    rr = r * (1 + rng.uniform(-.3, .3, n))
    spoke = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
    outer = c + spoke * rr[:, None] + nrm * .004
    inner = c + spoke * (rr * .55)[:, None] + nrm * (h * rng.uniform(.6, 1, n))[:, None]
    verts = np.concatenate([[c + nrm * h], inner, outer])
    faces = [[0, 1 + j, 1 + (j + 1) % n] for j in range(n)]
    faces += [[1 + j, 1 + n + j, 1 + n + (j + 1) % n, 1 + (j + 1) % n] for j in range(n)]
    t = rng.uniform(0, .6)
    cols = np.concatenate([np.tile(tone(mix(MOSS_GREEN, MOSS_DEEP, t), 1.1), (1 + n, 1)), np.tile(tone(mix(MOSS_GREEN, MOSS_DEEP, .8), .9), (n, 1))])
    p.add(verts, faces, cols, MOSS, True)


def moss_line(p, rng, a, b, out, w=.14, h=.025, climb=0.0, step=.3, wall=None):
    """Moss gathered along an edge or the foot of a wall from a to b, spreading `out` (a unit direction on the surface)
    by about w; climb: how far it creeps up the wall that stands behind it (wall: that wall's own up direction, when it
    is battered)."""
    a, b, out = np.asarray(a, np.float64), np.asarray(b, np.float64), unit(out)
    n = cells(np.linalg.norm(b - a), step) + 1
    t = np.linspace(0, 1, n)[:, None]
    line = a + (b - a) * t
    up = unit(np.cross(b - a, out))
    up = up if up[2] >= -1e-9 else -up
    rows = []
    if climb:
        rows.append(line + (up if wall is None else unit(wall)) * (climb * rng.uniform(.25, 1, (n, 1))) + out * .012)
    rows += [line + out * .015 + up * .012, line + out * (w * .5) + up * (h * rng.uniform(.6, 1, (n, 1))),
             line + out * (w * rng.uniform(.7, 1.3, (n, 1))) + up * .004]
    verts = np.concatenate(rows)
    faces = []
    for r_ in range(len(rows) - 1):
        for i in range(n - 1):
            faces.append(fl._facing(verts, [r_ * n + i, r_ * n + i + 1, (r_ + 1) * n + i + 1, (r_ + 1) * n + i], up + out))
    k = .5 + .5 * noise2(verts[:, 0] * 2.1 + verts[:, 2], verts[:, 1] * 2.1, int(rng.integers(0, 999)))
    cols = fl.mix(MOSS_GREEN, MOSS_DEEP, k * .8)
    p.add(verts, faces, cols, MOSS, True)


def tuft(p, rng, c, h=.4, w=.4, n=3, colours=(GRASS, GRASS_DRY), cell=None):
    """A grass tuft: n crossed atlas cards standing at c (LEAF: never collides)."""
    ang = rng.uniform(0, math.pi) + np.arange(n) * math.pi / n
    facing = np.stack([np.cos(ang), np.sin(ang), np.zeros(n)], 1)
    grow = unit(Z + rng.normal(0, .12, (n, 3)) * np.array([1, 1, 0]))
    cols = np.array([vary(rng, mix(colours[0], colours[1], rng.uniform(0, .55)), .15) for _ in range(n)])
    fl.cards(p, np.tile(np.asarray(c, np.float64), (n, 1)), grow, facing, w * rng.uniform(.8, 1.2, n), h * rng.uniform(.8, 1.2, n),
             cell or fl.CELL_GRASS, cols, rng=rng)


def sprig(p, rng, base, h=.8, leaves=8, colours=(LEAF_GREEN, LEAF_LIGHT), bark=BARK_BROWN, r=.012, size=.28):
    """A seedling tree or woody weed: a thin stem (BARK) carrying leaf cards (LEAF)."""
    base = np.asarray(base, np.float64)
    lean = rng.normal(0, .12, 3) * np.array([1, 1, 0])
    pts = [base, base + lean * h * .5 + Z * h * .5, base + lean * h + Z * h]
    fl.limb(p, pts, [r, r * .7, r * .35], tone(bark, np.array([.8, 1.0, 1.1])), BARK, 5)
    t = rng.uniform(.35, 1.0, leaves)
    at = np.array([pts[0] + (pts[2] - pts[0]) * q for q in t])
    ang = rng.uniform(0, TAU, leaves)
    outw = np.stack([np.cos(ang), np.sin(ang), np.zeros(leaves)], 1)
    cols = np.array([vary(rng, mix(colours[0], colours[1], rng.uniform(0, 1)), .15) for _ in range(leaves)])
    fl.cards(p, at, unit(outw + Z * rng.uniform(.3, .9, (leaves, 1))), unit(Z * .8 + outw * .4), size * rng.uniform(.8, 1.2, leaves),
             size * rng.uniform(.8, 1.2, leaves), fl.CELL_LEAF if size > .2 else fl.CELL_SMALLLEAF, cols, rng=rng, foot=.8)


def ivy(p, rng, o, u, normal, w, h, count, colours=(LEAF_DEEP, LEAF_GREEN), size=.42):
    """Ivy on a wall: leaf cards lying almost flat on the wall's face over the patch from o, w along u and h up."""
    o, u, n = np.asarray(o, np.float64), unit(u), unit(normal)
    a, b = rng.uniform(0, w, count), h * rng.uniform(0, 1, count) ** 1.6
    base = o + u * a[:, None] + Z * b[:, None] + n * .03
    grow = unit(Z + u * rng.normal(0, .5, (count, 1)) + n * .12)
    cols = np.array([vary(rng, mix(colours[0], colours[1], rng.uniform(0, 1)), .2) for _ in range(count)])
    fl.cards(p, base, grow, n, size * rng.uniform(.7, 1.3, count), size * rng.uniform(.7, 1.3, count), fl.CELL_LEAF, cols, rng=rng, foot=.8)


def done(p, pivot='base', facts=None):
    """Ends a builder: checks that nothing sank under the pivot plane (the builders lay their meshes out in the contract's
    frame, so nothing is moved here) and files the mesh's placement facts."""
    z = np.asarray(p.v, np.float64)[:, 2].min()
    if pivot == 'base' and abs(z) > .02:
        raise ValueError('%s: lowest point at z %.3f, the builder should stand it on z 0' % (p.name, z))
    if hasattr(p, 'card_normals'):
        del p.card_normals     # hard surfaces keep their own face normals; the few weed cards shade by their facing
    if facts is not None:
        FACTS[p.name] = facts
    return p


# ---------------------------------------------------------------- shared pieces

def hoop(p, c, R, r, slot, axis=Z, sides=32, ring=8, colour=GREY, a0=0.0, a1=360.0):
    """A ring of radius R and tube radius r round `axis` at c (a hand-wheel's rim, a sheave, a rail hoop), or the arc
    of it from a0 to a1 degrees, measured from frame(axis)'s first vector; its section never pinches."""
    full = a1 - a0 >= 360 - 1e-6
    e0, e1 = frame(axis)
    n = unit(axis)
    th = np.radians(np.linspace(a0, a1, sides, endpoint=False) if full else np.linspace(a0, a1, sides + 1))
    ph = np.linspace(0, TAU, ring, endpoint=False)
    rad = np.cos(th)[:, None] * e0 + np.sin(th)[:, None] * e1
    verts = (np.asarray(c, np.float64) + (R + r * np.cos(ph))[None, :, None] * rad[:, None, :] + (r * np.sin(ph))[None, :, None] * n).reshape(-1, 3)
    nt = len(th)
    faces = [[i * ring + j, ((i + 1) % nt) * ring + j, ((i + 1) % nt) * ring + (j + 1) % ring, i * ring + (j + 1) % ring]
             for i in range(nt if full else nt - 1) for j in range(ring)]
    start = p.add(verts, faces, colour, slot, True)
    if not full:
        ends = np.concatenate([verts[:ring], verts[-ring:]])
        p.add(ends, [list(range(ring)), list(range(ring, 2 * ring))[::-1]], colour, slot, False)
    return start


def dish(p, c, axis, r, depth, fn, frame_fn, slot=PAINT, sides=24, feed=True):
    """A parabolic antenna: its vertex at c, opening along axis, radius r and depth `depth`; a rolled rim, and (feed) a
    horn held at the focus by three struts."""
    axis, c = unit(axis), np.asarray(c, np.float64)
    k = depth / r ** 2
    rs = np.linspace(.05, 1, 7) * r
    m = mark(p)
    turn(p, [(q, k * q * q) for q in rs], slot, sides, c, axis, hard=False)
    turn(p, [(r, depth), (r + .025, depth), (r + .025, depth + .03), (r - .01, depth + .03)], slot, sides, c, axis)
    turn(p, [(q, k * q * q + .012) for q in rs[::-1]], slot, sides, c, axis, hard=False)
    disc(p, c, rs[0], slot, -axis, 8)
    disc(p, c + axis * (k * rs[0] ** 2 + .012), rs[0], slot, axis, 8)
    paint(p, m, fn)
    if feed:
        m = mark(p)
        focus = c + axis * min(r * r / (4 * depth), depth + .45)
        a, b = frame(axis)
        for t in np.radians((90, 210, 330)):
            pipe(p, [c + (a * math.cos(t) + b * math.sin(t)) * r * .96 + axis * depth, focus], .012, STEEL, 6)
        turn(p, [(.008, -.16), (.09, -.16), (.09, -.14), (.05, 0)], STEEL, 12, focus, axis)
        paint(p, m, frame_fn)


def ngon(c, r, sides, z, start=0.0):
    """Corners of a regular polygon of circumradius r around (c[0], c[1]) at height z; start in degrees from +x."""
    a = math.radians(start) + np.linspace(0, TAU, sides, endpoint=False)
    return np.stack([c[0] + np.cos(a) * r, c[1] + np.sin(a) * r, np.full(sides, float(z))], 1)


def annulus(p, r0, r1, z, slot, a0=0.0, a1=TAU, na=24, nr=1, thick=0.0, c=(0, 0), colour=GREY):
    """A flat ring or sector (angles in radians) facing up at height z, gridded in polar cells; thick gives it an
    outer and inner edge (and end faces, for a sector) going down."""
    full = a1 - a0 >= TAU - 1e-6
    ang = np.linspace(a0, a1, na + 1)
    rad = np.linspace(r0, r1, nr + 1)
    verts = np.array([(c[0] + math.cos(a) * r, c[1] + math.sin(a) * r, z) for a in ang for r in rad])
    n = nr + 1
    faces = [[i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j] for i in range(na) for j in range(nr)]
    start = p.add(verts, faces, colour, slot, False)
    if thick:
        for r, sign in ((r1, 1), (r0, -1)):
            if r <= 1e-6:
                continue
            ring = np.array([(c[0] + math.cos(a) * r, c[1] + math.sin(a) * r, z) for a in ang])
            v2 = np.concatenate([ring, ring - Z * thick])
            m = na + 1
            fs = [[i, m + i, m + i + 1, i + 1] if sign > 0 else [i, i + 1, m + i + 1, m + i] for i in range(na)]
            p.add(v2, fs, colour, slot, True)
        if not full:
            for a, sign in ((a0, -1), (a1, 1)):
                d = V3(math.cos(a), math.sin(a), 0)
                o = V3(c[0], c[1], z)
                face(p, [o + d * r0, o + d * r1, o + d * r1 - Z * thick, o + d * r0 - Z * thick], slot, V3(-d[1], d[0], 0) * sign, colour)
    return start


def catmull(pts, n=6):
    """A smooth path through the points (Catmull-Rom), n steps per span."""
    q = np.asarray(pts, np.float64)
    q = np.concatenate([[2 * q[0] - q[1]], q, [2 * q[-1] - q[-2]]])
    out = []
    for i in range(1, len(q) - 2):
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(.5 * ((2 * q[i]) + (-q[i - 1] + q[i + 1]) * t + (2 * q[i - 1] - 5 * q[i] + 4 * q[i + 1] - q[i + 2]) * t * t +
                             (-q[i - 1] + 3 * q[i] - 3 * q[i + 1] + q[i + 2]) * t ** 3))
    out.append(q[-2])
    return np.array(out)


def graphite(seed, rust=.16):
    return steel(seed, JUST_GRAPHITE, rust, grime=.15, streak=.1)


def bone(seed, rust=.1):
    return steel(seed, JUST_BONE, rust, grime=.3, streak=.3)


def orange(seed, rust=.12):
    return steel(seed, JUST_ORANGE, rust, grime=.25, streak=.25)


def olive(seed, rust=.14):
    return steel(seed, JUST_OLIVE, rust, grime=.25, streak=.2)


def galv(seed, rust=.28):
    return steel(seed, STEEL_GREY, rust)


def rusty(seed):
    return steel(seed, mix(RUST_ORANGE, RUST_DARK, .4), 0.0, grime=.45, streak=.25)


def copper(seed, patina=.35):
    """Copper bus bar: bright where it is rubbed, brown elsewhere, verdigris where water sits."""
    base, green = _rgb(COPPER), _rgb(VERDIGRIS)

    def f(P, N):
        P, N, x, y, z = _pn(P, N)
        b1 = .5 + .5 * noise2(x / .5 + z * 1.1, y / .5 - z, seed + 31)
        b2 = .5 + .5 * noise2(x / .12, y / .12 + z * 3, seed + 32)
        g = np.clip((.6 * b1 + .4 * b2 - (1 - patina)) / .2, 0, 1)[:, None]
        c = base * (.55 + .45 * b2[:, None]) * (1 - g) + green * (.6 + .3 * b1[:, None]) * g
        return _out(c * np.where(N[:, 2] < -.6, .75, 1.0)[:, None])
    return f


def armour(p, o, u, v, L, H, nu, nv, fn, t=.06, stand=.02, gap=.014, pitch=.45, bolt=.016, slot=PAINT, bolt_fn=None, cell=.55):
    """Armour cladding on the plane through o spanned by unit vectors u and v (it faces u x v): nu by nv thick
    chamfered plates standing `stand` off the surface with dark seams between them, bolted round their edges at about
    `pitch`. fn paints the plates, bolt_fn the bolts."""
    u, v = unit(u), unit(v)
    f = np.cross(u, v)
    R = np.stack([u, v, f], 1)
    o = np.asarray(o, np.float64)
    m = mark(p)
    pts = []
    w, h = L / nu, H / nv
    e = .07
    for i in range(nu):
        for j in range(nv):
            gbox(p, (i * w + gap / 2, j * h + gap / 2, stand), ((i + 1) * w - gap / 2, (j + 1) * h - gap / 2, stand + t), slot, cell, .012, 'z')
            for a0, b0, a1, b1 in ((e, e, w - e, e), (w - e, e, w - e, h - e), (w - e, h - e, e, h - e), (e, h - e, e, e)):
                n = cells(math.hypot(a1 - a0, b1 - b0), pitch)
                for k in range(n):
                    pts.append((i * w + a0 + (a1 - a0) * k / n, j * h + b0 + (b1 - b0) * k / n, stand + t))
    place(p, m, R, o)
    paint(p, m, fn)
    if bolt:
        m = mark(p)
        bolts(p, np.asarray(pts) @ R.T + o, f, bolt, STEEL if STEEL in p.slots else slot)
        paint(p, m, bolt_fn or steel(7, STEEL_GREY, .35))


def louvre(p, o, u, w, h, fn, slot=STEEL, slats=6, depth=.06):
    """A louvred vent on a wall: o = its bottom-left corner seen from outside, u along the wall; it faces u x Z."""
    o, u = np.asarray(o, np.float64), unit(u)
    f = np.cross(u, Z)
    m = mark(p)
    for a0, a1, b0, b1 in ((0, w, 0, 0), (0, w, h, h), (0, 0, 0, h), (w, w, 0, h)):
        bar(p, o + u * a0 + Z * b0 + f * depth / 2, o + u * a1 + Z * b1 + f * depth / 2, .04, depth, slot, f)
    tilt = unit(f * .7 + Z * .7)
    for k in range(slats):
        q = o + Z * (h * (k + .5) / slats) + f * depth * .5
        bar(p, q + u * .02, q + u * (w - .02), h / slats * 1.15, .006, slot, tilt)
    paint(p, m, fn)
    q = o + f * .004
    face(p, [q, q + u * w, q + u * w + Z * h, q + Z * h], slot, f, tone(STEEL_DARK, .35))


def steel_door(p, o, u, w, h, fn, frame_fn, slot=PAINT, frame_slot=STEEL, t=.05, vent=True):
    """A steel personnel door closed in a wall: o = the opening's bottom-left corner seen from outside, u along the
    wall; it faces u x Z. A pressed frame, the leaf with two stiffening pans, hinges, a lever handle, a kick plate."""
    o, u = np.asarray(o, np.float64), unit(u)
    f = np.cross(u, Z)
    R = np.stack([u, Z, f], 1)
    m = mark(p)
    for lo, hi in (((-.07, 0, -.04), (0, h + .07, .03)), ((w, 0, -.04), (w + .07, h + .07, .03)), ((0, h, -.04), (w, h + .07, .03))):
        gbox(p, lo, hi, frame_slot, 9, .008)
    for k in range(3):
        turn(p, [(.014, -.06), (.014, .06)], frame_slot, 8, (.0, h * (.15 + .35 * k), .035), Y)
    gbox(p, (w - .16, h * .47, t - .02), (w - .1, h * .47 + .16, t + .012), frame_slot, 9, .004)
    pipe(p, [(w - .13, h * .47 + .11, t + .01), (w - .13, h * .47 + .11, t + .06), (w - .27, h * .47 + .11, t + .06)], .011, frame_slot, 8)
    place(p, m, R, o)
    paint(p, m, frame_fn)
    m = mark(p)
    gbox(p, (.006, .012, -.02), (w - .006, h - .006, t - .02), slot, .6, .006)
    for b0, b1 in ((.2, .47), (.53, .92)):
        gbox(p, (.12, h * b0, t - .02), (w - .12, h * b1, t - .012), slot, .5, .006, 'z')
    gbox(p, (.02, .03, t - .02), (w - .02, .22, t - .016), frame_slot, 9, .002, 'z')
    place(p, m, R, o)
    paint(p, m, fn)
    if vent:
        louvre(p, o + u * (w * .25) + Z * (h * .25) + f * (t - .012), u, w * .5, h * .12, frame_fn, frame_slot, 4, .02)


# ================================================================ the Deeproot Array
# One livery on every piece: a concrete base to PLINTH, graphite steel, and the bone-white armoured band between
# BAND heights carrying the signal-orange stripe at STRIPE, so wall, gate frame, tower and bunker line up.
BAND = (4.5, 7.5)
STRIPE = (6.75, 7.05)
PLINTH = 2.4


@mesh('SM_GN_ArrayWall', (1.6, 12.0, 9.0))
def array_wall():
    """The Array's perimeter wall, one 12 m panel along y, facing +x (outward). A battered concrete base cast in two
    lifts; six tapered plate-girder ribs on bolted base plates; a steel skin between them; the bone-white armoured
    band (4.5 to 7.5 m) with the orange stripe; a tie beam with cranked anti-climb arms and sensor wires on top."""
    rng = np.random.default_rng(2601)
    p = Part('SM_GN_ArrayWall', (CONCRETE, STEEL, PAINT, RUST, MOSS, GLOW))
    conc = concrete(11, damp=1.4, ledges=((PLINTH, .9),), moss=.35)
    gra, ora = graphite(12), orange(14)
    ribs = (-5, -3, -1, 1, 3, 5)
    # the base: front battered from x .62 at the ground to .45 at its top, back plumb at -0.8
    batter = V3(-.17, 0, PLINTH)
    sheet(p, (.62, -6, 0), Y, batter, 12, np.linalg.norm(batter), 0, CONCRETE, ju=(3, 6, 9), jv=(1.2,), back=False, rim='',
          ties=(1.0, .6, .016), fn=conc)
    sheet(p, (-.8, 6, 0), -Y, Z, 12, PLINTH, 0, CONCRETE, ju=(3, 6, 9), jv=(1.2,), back=False, rim='', ties=(1.0, .6, .016), fn=conc)
    m = mark(p)
    gquad(p, (-.8, -6, PLINTH), (.45, -6, PLINTH), (.45, 6, PLINTH), (-.8, 6, PLINTH), CONCRETE, 2, 12)
    for s in (-1, 1):
        face(p, [(-.8, s * 6, 0), (.62, s * 6, 0), (.45, s * 6, PLINTH), (-.8, s * 6, PLINTH)], CONCRETE, s * Y)
    paint(p, m, conc)
    nb = unit(V3(PLINTH, 0, .17))
    for y in (-4.5, -1.5, 1.5, 4.5):       # weep pipes and what runs out of them
        xf = .62 - .17 * .5 / PLINTH
        m = mark(p)
        pipe(p, [(xf - .1, y, .5), (xf + .05, y, .49)], .035, RUST, 10)
        paint(p, m, rusty(15))
        streaks(p, rng, [(xf, y, .47)], nb, (.32, .46), (.08, .13), MOSS_DEEP, MOSS)
    # the ribs: welded plate girders, 0.92 m deep at the base plate and 0.34 at the top, stiffened every metre
    z0, z1 = PLINTH + .03, 8.6

    def xb(z):
        return -.62 + .57 * (z - z0) / (z1 - z0)
    m = mark(p)
    for y in ribs:
        plate(p, [(xb(z0), y, z0), (.29, y, z0), (.29, y, z1), (xb(z1), y, z1)], .02, STEEL)
        bar(p, (.289, y, z0), (.289, y, z1), .30, .022, STEEL, X)
        bar(p, (xb(z0), y, z0), (xb(z1), y, z1), .30, .022, STEEL, X)
        for z in (3.45, 4.5, 5.55, 6.6, 7.65):
            for s in (-1, 1):
                bar(p, (xb(z) + .02, y + s * .08, z), (.275, y + s * .08, z), .14, .012, STEEL)
        gbox(p, (-.74, y - .27, PLINTH), (.42, y + .27, z0), STEEL, 9, .006, 'z')
        bolts(p, [(x, y + s * .2, z0) for x in (-.68, -.3, .06) for s in (-1, 1)], Z, .022, STEEL, h=.035)
        for s in (-1, 1):
            plate(p, [(-.3, y + s * .012, z0), (-.3, y + s * .24, z0), (-.3, y + s * .012, z0 + .32)], .012, STEEL)
    paint(p, m, gra)
    # the skin, its stiffeners and vents, and the flashing that throws water clear of the base plates
    sheet(p, (.13, -6, z0), Y, Z, 12, z1 - z0, .03, STEEL, jv=(1.05,), groove=(.012, .004), sub=1.0, rim='lr', fn=gra)
    m = mark(p)
    for z in (3.0, 3.95):
        angle(p, (.13, -6, z), (.13, 6, z), .07, STEEL, X, -Z)
    bar(p, (.30, -6, PLINTH + .12), (.30, 6, PLINTH + .12), .39, .006, STEEL, unit(V3(.2, 0, .34)))
    for z in (3.3, 5.3, 7.3):
        channel(p, (.10, -6, z), (.10, 6, z), .14, .06, STEEL, Z)
    paint(p, m, gra)
    for yc in (-2, 2):
        louvre(p, (.135, yc - .5, 3.2), Y, 1.0, .55, gra)
    m = mark(p)
    for z in (2.72, 2.8):
        conduit(p, [(.08, y, z) for y in np.linspace(-6, 6, 7)], -X, STEEL, .018, 1.0)
    for y in (-3, 3):
        gbox(p, (-.02, y + .2, 2.62), (.1, y + .42, 2.9), STEEL, 9, .008)
        conduit(p, [(.02, y + .31, 2.62), (.02, y + .31, PLINTH + .01)], -X, STEEL, .016, .12)
    paint(p, m, galv(16, .22))
    # the armoured band and the stripe
    bays = [(-6 + .006, -5 - .17)] + [(a + .17, a + 2 - .17) for a in ribs[:-1]] + [(5 + .17, 6 - .006)]
    for k, (ya, yb) in enumerate(bays):
        armour(p, (.13, ya, BAND[0]), Y, Z, yb - ya, BAND[1] - BAND[0], 1, 2, bone(13 + k), t=.07, stand=.02)
    m = mark(p)
    for ya, yb in bays:
        gbox(p, (.22, ya + .02, STRIPE[0]), (.226, yb - .02, STRIPE[1]), PAINT, .6, .002, 'x')
    for y in ribs:
        gbox(p, (.30, y - .15, STRIPE[0]), (.304, y + .15, STRIPE[1]), PAINT, 9, .001, 'x')
    paint(p, m, ora)
    # the top: tie beam, anti-climb arms, three sensor wires
    m = mark(p)
    gbox(p, (-.1, -6, z1), (.32, 6, z1 + .22), STEEL, 1.0, .012)
    a0, a1 = V3(.26, 0, z1 + .2), V3(.76, 0, 8.965)
    for y in ribs:
        bar(p, a0 + Y * y, a1 + Y * y, .08, .05, STEEL)
        plate(p, [(.2, y, z1 + .22), (.5, y, z1 + .22), (.5, y, z1 + .29)], .012, STEEL)
    for t in (.3, .62, .94):
        q = a0 + (a1 - a0) * t + Z * .036
        pipe(p, [q + Y * y for y in np.linspace(-6, 6, 7)], .011, STEEL, 6)
    paint(p, m, gra)
    for y in (-3, 3):
        bulkhead(p, (.30, y, 8.15), X, STEEL, GLOW_AMBER, .085)
    # weather that is geometry: moss at the feet and on the ledge, rust from the plate bolts
    moss_line(p, rng, (.62, -6, 0), (.62, 6, 0), X, .06, .025, climb=.2, wall=batter)
    moss_line(p, rng, (-.8, 6, 0), (-.8, -6, 0), -X, .07, .025, climb=.32)
    for _ in range(9):
        moss_patch(p, rng, (rng.uniform(-.76, -.3), rng.uniform(-5.9, 5.9), PLINTH), rng.uniform(.07, .18))
    pts = [(.2205, rng.uniform(*bays[int(rng.integers(0, 7))]), z) for z in (BAND[0] + .08, 6.07, 6.07, BAND[0] + .08, 6.07) for _ in range(3)]
    streaks(p, rng, pts, X, (.25, .8), (.03, .07), RUST_ORANGE, RUST)
    return done(p, facts=dict(front='+x', plinth_top=PLINTH, band=BAND, stripe=STRIPE, ribs_y=ribs, top=9.0,
                              lights=[(.39, -3, 8.15), (.39, 3, 8.15)]))


@mesh('SM_GN_ArrayGate', (1.2, 8.0, 8.5))
def array_gate():
    """The Array's gate leaf: one armoured slab 8 m wide and 8.5 m high (box collision in the game). Outside (+x): a
    graphite frame holding eight bone-white armour plates, and across the middle a dark panel with orange chevrons
    pointing in at the lock, whose amber lens is the gate's one light; lock rods run up and down the centre seam.
    Inside (-x): the welded frame itself, braced, with shoot bolts, an access hatch and a small repeater light."""
    rng = np.random.default_rng(2602)
    p = Part('SM_GN_ArrayGate', (STEEL, PAINT, RUST, GLOW))
    gra, ora = graphite(21), orange(23)
    zc = 4.25
    m = mark(p)
    gbox(p, (-.42, -4, 0), (.42, 4, 8.5), STEEL, 1.0, .03)
    gbox(p, (.42, -4, 0), (.57, 4, .5), STEEL, 1.0, .02, 'x')
    gbox(p, (.42, -4, 8.0), (.57, 4, 8.5), STEEL, 1.0, .02, 'x')
    for s in (-1, 1):
        gbox(p, (.42, s * 3.7, .5), (.57, s * 4, 8.0), STEEL, 1.0, .02, 'x')
    gbox(p, (.42, -3.7, 3.1), (.47, 3.7, 5.4), STEEL, .8, .01, 'x')
    for y0, y1 in ((-4, -3.7), (3.7, 4), (-1.45, -1.15), (1.15, 1.45)):
        gbox(p, (-.57, y0, 0), (-.42, y1, 8.5), STEEL, 1.0, .02, 'X')
    levels = ((0, .3), (2.15, 2.4), (4.1, 4.4), (6.1, 6.35), (8.2, 8.5))
    for za, zb in levels:
        gbox(p, (-.56, -3.7, za), (-.42, 3.7, zb), STEEL, 1.0, .02, 'X')
    for s in (-1, 1):
        for (_, za), (zb, _) in zip(levels, levels[1:]):
            lo, hi = (za, zb) if za < zc else (zb, za)
            bar(p, (-.46, s * 1.45, lo), (-.46, s * 3.7, hi), .16, .08, STEEL, X)
        for z in (2.275, 6.225):          # shoot bolts into the frame's jambs
            gbox(p, (-.62, s * 2.2, z - .13), (-.56, s * 3.3, z + .13), STEEL, 9, .012, 'X')
            pipe(p, [(-.6, s * 3.0, z), (-.6, s * 3.985, z)], .07, STEEL, 16)
    gbox(p, (-.455, -.6, .65), (-.42, .6, 1.85), STEEL, .6, .008, 'X')
    bolts(p, [(-.455, y, z) for y in (-.52, 0, .52) for z in (.73, 1.25, 1.77)], -X, .02, STEEL)
    pipe(p, [(-.455, -.2, 1.45), (-.52, -.2, 1.45), (-.52, .2, 1.45), (-.455, .2, 1.45)], .014, STEEL, 8)
    # the lock: a bolted boss round the lens, and rods along the centre seam in guide brackets
    turn(p, [(.82, 0), (.82, .09), (.72, .13), (.36, .13), (.36, .07), (.25, .07)], STEEL, 32, (.47, 0, zc), X)
    bolts(p, [(.60, .54 * math.cos(t), zc + .54 * math.sin(t)) for t in np.linspace(0, TAU, 12, endpoint=False) + .26], X, .032, STEEL)
    for za, zb in ((.5, 3.1), (5.4, 8.0)):
        gbox(p, (.53, -.06, za), (.585, .06, zb), STEEL, .8, .012, 'x')
        for z in np.linspace(za + .3, zb - .3, 3):
            gbox(p, (.53, -.14, z - .07), (.6, .14, z + .07), STEEL, 9, .01, 'x')
            bolts(p, [(.6, s * .1, z) for s in (-1, 1)], X, .016, STEEL)
    turn(p, [(.3, 0), (.3, .05), (.24, .08), (.15, .08)], STEEL, 20, (-.57, 0, zc), -X)
    paint(p, m, gra)
    for za, zb, sd in ((.5, 3.1, 31), (5.4, 8.0, 32)):
        armour(p, (.42, -3.7, za), Y, Z, 7.4, zb - za, 4, 2, bone(sd), t=.1, stand=.01, pitch=.42, bolt=.02)
    m = mark(p)
    run, wid = .8, .3
    for s in (-1, 1):
        for ya in (1.2, 1.85, 2.5):
            for up in (-1, 1):
                plate(p, [(.485, s * ya, zc), (.485, s * (ya + wid), zc), (.485, s * (ya + wid + run), zc + up * run),
                          (.485, s * (ya + run), zc + up * run)], .03, PAINT)
    paint(p, m, ora)
    fl.disc(p, (.545, 0, zc), X, .25, tone(GLOW_AMBER, 1.0), GLOW, 24, dome=.05, rim=tone(GLOW_AMBER, .55))
    fl.disc(p, (-.652, 0, zc), -X, .15, tone(GLOW_AMBER, 1.0), GLOW, 16, dome=.03, rim=tone(GLOW_AMBER, .55))
    pts = [(.531, rng.uniform(-3.5, 3.5), 3.06) for _ in range(9)] + [(.531, rng.uniform(-3.5, 3.5), 1.78) for _ in range(5)]
    streaks(p, rng, pts, X, (.3, 1.0), (.03, .08), RUST_ORANGE, RUST)
    streaks(p, rng, [(.471, rng.uniform(-3.5, 3.5), 5.38) for _ in range(6)], X, (.3, .7), (.03, .06), RUST_DARK, RUST)
    return done(p, facts=dict(lock_light=(.6, 0, zc), back_light=(-.66, 0, zc), leaf=dict(x=(-.6, .6), y=(-4, 4), z=(0, 8.5))))


@mesh('SM_GN_ArrayGateFrame', (3.0, 12.0, 10.5))
def array_gate_frame():
    """The portal round the gate: two pylons and a lintel, 12 m wide like a wall panel, 3 m deep. The opening is
    8.0 m wide (y -4 to 4) and 8.5 m high, the passage along x, with a slot 1.32 m wide and 0.12 m deep up both jambs
    and across the soffit for the leaf. Pylons: concrete to the wall's plinth height, then graphite casing carrying the
    wall's armoured band and stripe on both faces. Lintel: a box girder with bone plates, a row of amber lamps under
    them and a sensor eye in the middle; a cap with a drip on top. A steel threshold ties the pylons at the ground."""
    rng = np.random.default_rng(2603)
    p = Part('SM_GN_ArrayGateFrame', (CONCRETE, STEEL, PAINT, RUST, MOSS, GLOW))
    conc = concrete(31, damp=1.4, ledges=((PLINTH, .9),))
    gra, ora = graphite(32), orange(34)
    SL, SD, XC = .66, .12, 1.44
    lamps = []
    for s in (-1, 1):
        m = mark(p)
        for za, zb, sk in ((0, 1.2, 'z'), (1.2, PLINTH, '')):
            gbox(p, (SL, s * 4, za), (1.5, s * 6, zb), CONCRETE, .6, .025, sk)
            gbox(p, (-1.5, s * 4, za), (-SL, s * 6, zb), CONCRETE, .6, .025, sk)
            gbox(p, (-SL, s * (4 + SD), za), (SL, s * 6, zb), CONCRETE, .6, .025, sk + 'xX')
        paint(p, m, conc)
        m = mark(p)
        gbox(p, (SL, s * 4, PLINTH), (XC, s * 6, 8.5), STEEL, .9, .02, 'zZ')
        gbox(p, (-XC, s * 4, PLINTH), (-SL, s * 6, 8.5), STEEL, .9, .02, 'zZ')
        gbox(p, (-SL, s * (4 + SD), PLINTH), (SL, s * 6, 8.5), STEEL, .9, .02, 'zZxX')
        for sx in (-1, 1):                     # pilasters at the casing's corners and the girts between them, bolted on
            x = sx * (XC + .028)
            for y in (4.13, 5.87):
                bar(p, (x, s * y, PLINTH), (x, s * y, 8.5), .24, .056, STEEL, X)
                bolts(p, [(sx * (XC + .056), s * y, z) for z in np.arange(PLINTH + .3, 8.4, .6)], sx * X, .018, STEEL)
            for z in (3.2, 4.1, 8.0):
                bar(p, (sx * (XC + .02), s * 4.25, z), (sx * (XC + .02), s * 5.75, z), .14, .04, STEEL, X)
            gbox(p, (sx * XC, s * 4.3, PLINTH - .02), (sx * (XC + .05), s * 5.7, PLINTH + .1), STEEL, 9, .01)     # base angle on the concrete
            bolts(p, [(sx * (XC + .05), s * y, PLINTH + .04) for y in (4.5, 5.0, 5.5)], sx * X, .02, STEEL)
        paint(p, m, gra)
        m = mark(p)                           # wear plates lining the slot
        gbox(p, (-.5, s * (4 + SD), .1), (.5, s * (4 + SD - .012), 8.45), STEEL, .9, .003)
        paint(p, m, galv(33, .2))
        ya, yb = (4.08, 5.94) if s > 0 else (-5.94, -4.08)
        armour(p, (XC, ya, BAND[0]), Y, Z, yb - ya, 3.0, 1, 2, bone(35), t=.07, stand=.02)
        armour(p, (-XC, yb, BAND[0]), -Y, Z, yb - ya, 3.0, 1, 2, bone(36), t=.07, stand=.02)
        m = mark(p)
        gbox(p, (XC + .09, ya + .02, STRIPE[0]), (XC + .096, yb - .02, STRIPE[1]), PAINT, .6, .002, 'x')
        gbox(p, (-XC - .096, ya + .02, STRIPE[0]), (-XC - .09, yb - .02, STRIPE[1]), PAINT, .6, .002, 'X')
        gbox(p, (XC, s * 4, PLINTH + .1), (XC + .008, s * 4.07, 4.4), PAINT, .8, .002, 'x')      # hazard edge of the jamb
        paint(p, m, ora)
        bulkhead(p, (1.5, s * 5, 2.05), X, STEEL, GLOW_AMBER, .1)
        lamps.append((1.6, s * 5.0, 2.05))
        m = mark(p)
        conduit(p, [(1.517, s * 5, 1.93), (1.517, s * 5, .04)], X, STEEL, .016, .6)
        paint(p, m, galv(38))
        moss_line(p, rng, (1.5, s * 4, 0), (1.5, s * 6, 0), X, .05, .025, climb=.18)
        moss_line(p, rng, (-1.5, s * 6, 0), (-1.5, s * 4, 0), -X, .06, .025, climb=.3)
        for _ in range(4):
            moss_patch(p, rng, (rng.choice((-1.47, 1.47)), s * rng.uniform(4.1, 5.9), PLINTH), .05)
        pts = [(XC + .091, s * rng.uniform(4.2, 5.8), z) for z in (BAND[0] + .08, 6.07, BAND[0] + .08)]
        streaks(p, rng, pts, X, (.3, .8), (.03, .07), RUST_ORANGE, RUST)
    # the lintel: two beams and a web over the slot, bone plates on the outside, stiffeners inside
    m = mark(p)
    gbox(p, (SL, -6, 8.5), (XC, 6, 10.3), STEEL, 1.0, .02, 'Z')
    gbox(p, (-XC, -6, 8.5), (-SL, 6, 10.3), STEEL, 1.0, .02, 'Z')
    gbox(p, (-SL, -6, 8.5 + SD), (SL, 6, 10.3), STEEL, 1.0, .02, 'ZxX')
    gbox(p, (-1.5, -6, 10.3), (1.5, 6, 10.5), STEEL, 1.0, .03)
    for y in np.arange(-5, 5.01, 2.0):
        bar(p, (-XC - .04, y, 8.5), (-XC - .04, y, 10.3), .14, .08, STEEL, X)
    for yc in (-3.0, -1.5, 0.0, 1.5, 3.0):
        gbox(p, (XC, yc - .45, 8.58), (XC + .12, yc + .45, 8.8), STEEL, 9, .012, 'x')
    for yc in (-2.25, 2.25):
        gbox(p, (-XC - .12, yc - .45, 8.58), (-XC, yc + .45, 8.8), STEEL, 9, .012, 'X')
    turn(p, [(.34, 0), (.34, .1), (.27, .16), (.15, .16)], STEEL, 24, (XC + .08, 0, 9.47), X)
    paint(p, m, gra)
    for yc in (-3.0, -1.5, 0.0, 1.5, 3.0):
        gbox(p, (XC + .12, yc - .38, 8.62), (XC + .135, yc + .38, 8.76), GLOW, 9, .004, 'x', tone(GLOW_AMBER, .9))
        lamps.append((XC + .14, yc, 8.69))
    for yc in (-2.25, 2.25):
        gbox(p, (-XC - .135, yc - .38, 8.62), (-XC - .12, yc + .38, 8.76), GLOW, 9, .004, 'X', tone(GLOW_AMBER, .9))
    fl.disc(p, (XC + .245, 0, 9.47), X, .15, tone(GLOW_AMBER, 1.0), GLOW, 20, dome=.04, rim=tone(GLOW_AMBER, .5))
    armour(p, (XC, -5.9, 9.0), Y, Z, 11.8, .95, 6, 1, bone(39), t=.06, stand=.02)
    m = mark(p)                               # the threshold the leaf closes on
    gbox(p, (-.75, -4.11, 0), (.75, 4.11, .04), STEEL, 1.0, .008, 'z')
    paint(p, m, steel(37, STEEL_GREY, .3, ground=-2.0))
    return done(p, facts=dict(opening=dict(y=(-4.0, 4.0), z=(.04, 8.5)), passage='along x', depth=(-1.5, 1.5), leaf_at=(0, 0, 0),
                              slot=dict(x=(-SL, SL), depth=SD), band=BAND, stripe=STRIPE, lamps=lamps, eye=(XC + .25, 0, 9.47)))


def insulator(p, c, axis, r, n, pitch, slot=TILE, colour=None, sides=16):
    """A ceramic insulator: n sheds of radius r on a core, stacked along axis from c."""
    colour = colour if colour is not None else tone(mix(JUST_BONE, CONCRETE_PALE, .45), .95)
    prof = [(r * .45, 0.0)]
    for k in range(n):
        z = k * pitch
        prof += [(r, z + pitch * .25), (r * .98, z + pitch * .45), (r * .45, z + pitch * .95)]
    prof.append((r * .45, n * pitch))
    return turn(p, prof, slot, sides, c, axis, colour, hard=False)


def floor_z(p, m, z=0.0):
    """Keeps everything added since mark m at or above z (roots, rubble and moss that meet the ground)."""
    v = np.asarray(p.v[m[0]:], np.float64)
    if len(v):
        v[:, 2] = np.maximum(v[:, 2], z)
        p.v[m[0]:] = v.tolist()


def root(p, rng, pts, radii, colour=BARK_BROWN, sides=8, n=5):
    """A root or woody stem (BARK) along a smooth path through the points, radii given at the first and last point
    (or one per point); it never dips under z 0."""
    path = catmull(pts, n)
    radii = np.interp(np.linspace(0, 1, len(path)), np.linspace(0, 1, len(np.atleast_1d(radii))), np.atleast_1d(radii))
    m = mark(p)
    fl.branch_limb(p, path, radii, colour, BARK, sides, rng, ground=1.2, seed=int(rng.integers(0, 99)))
    floor_z(p, m)


@mesh('SM_GN_ArrayTower', (4.0, 4.0, 15.0))
def array_tower():
    """An emitter tower of the Array. An octagonal concrete footing 4 m across; a tapering eight-sided steel pylon in
    four flanged lifts, with the wall's bone band and orange stripe round it, a door housing at the front (+x), a
    caged ladder up the back and a cable trunk up one side; a service platform at 11 m; then the emitter: a ring of
    eight copper-edged fins round an insulated neck, and the amber crown (light at (0, 0, 14.05)) under a finial."""
    rng = np.random.default_rng(2604)
    p = Part('SM_GN_ArrayTower', (CONCRETE, STEEL, PAINT, BRASS, TILE, RUST, MOSS, GLOW))
    conc = concrete(41, damp=1.0, moss=.4)
    gra, ora = graphite(42), orange(44)
    k8 = 1 / math.cos(math.pi / 8)

    def ring8(ap, z):
        return ngon((0, 0), ap * k8, 8, z, 22.5)

    def ap(z):
        return 1.2 - .65 * (z - 1.2) / 9.8
    m = mark(p)
    for za, zb, aa, ab in ((0, .6, 2.0, 2.0), (.6, 1.16, 1.9, 1.9), (1.16, 1.2, 1.9, 1.86)):
        gprism(p, ring8(aa, za), ring8(ab, zb), CONCRETE, .7, 't')
    paint(p, m, conc)
    levels = (1.2, 3.65, 6.1, 8.55, 11.0)
    m = mark(p)
    for za, zb in zip(levels, levels[1:]):
        gprism(p, ring8(ap(za), za), ring8(ap(zb), zb), STEEL, .7, '')
    for z in levels:
        lo = z if z == levels[0] else z - .03
        gprism(p, ring8(ap(z) + .09, lo), ring8(ap(z) + .09, lo + .06), STEEL, 9, 'bt')
        for k in range(8):
            a = math.radians(k * 45)
            d, t = V3(math.cos(a), math.sin(a), 0), V3(-math.sin(a), math.cos(a), 0)
            w = ap(z) * math.tan(math.pi / 8)
            bolts(p, [d * (ap(z) + .045) + t * s * w * .5 + Z * (lo + .06) for s in (-1, 1)], Z, .024 if z == levels[0] else .016, STEEL, h=.03)
    # the door housing at the front and the cable trunk up the +y face
    gbox(p, (1.0, -.52, 1.2), (1.34, .52, 3.35), STEEL, .7, .02, 'xz')
    gbox(p, (1.0, -.6, 3.35), (1.4, .6, 3.41), STEEL, 9, .01)
    for x in (.56, .62, .68):
        q0, q1 = V3(-x + .62, ap(1.3) + .035, 1.26), V3((-x + .62) * .5, ap(10.9) + .035, 10.9)
        pipe(p, [q0 + (q1 - q0) * t for t in np.linspace(0, 1, 6)], .028, STEEL, 8)
    for z in np.arange(1.9, 10.6, 1.25):
        bar(p, (-.12, ap(z) + .07, z), (.12, ap(z) + .07, z), .05, .012, STEEL, Y)
    # the platform: seven deck plates on brackets (the eighth bay is the ladder's hatch), a guard rail round them
    for k in range(8):
        a = math.radians(k * 45)
        d = V3(math.cos(a), math.sin(a), 0)
        plate(p, [d * .58 + Z * 10.93, d * 1.46 + Z * 10.93, d * .6 + Z * 10.25], .012, STEEL)
        if k != 4:
            a0, a1 = a - math.pi / 8, a + math.pi / 8
            c0, c1 = V3(math.cos(a0), math.sin(a0), 0) * k8, V3(math.cos(a1), math.sin(a1), 0) * k8
            gprism(p, [c0 * .55 + Z * 10.94, c0 * 1.5 + Z * 10.94, c1 * 1.5 + Z * 10.94, c1 * .55 + Z * 10.94],
                   [c0 * .55 + Z * 11.0, c0 * 1.5 + Z * 11.0, c1 * 1.5 + Z * 11.0, c1 * .55 + Z * 11.0], STEEL, .6)
    rail = [V3(math.cos(a), math.sin(a), 0) * 1.46 * k8 + Z * 11.0 for a in np.radians(np.arange(202.5, 518, 45.0))]
    handrail(p, rail, STEEL, 1.1, 1.3, .1)
    # the emitter's neck, hoops and crown collar
    turn(p, [(.55, 11.0), (.55, 11.22), (.34, 11.36), (.34, 13.3), (.52, 13.45), (.52, 13.6), (.62, 13.6), (.62, 13.72), (.5, 13.8), (.12, 13.8)],
         STEEL, 24)
    turn(p, [(.12, 13.8), (.07, 14.45), (.028, 14.96), (.006, 15.0)], STEEL, 12, hard=False)
    for z, rr in ((12.0, 1.24), (12.8, 1.39)):
        torus(p, (0, 0, z), rr, .026, GREY, STEEL, 40, 6)
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        d = V3(math.cos(a), math.sin(a), 0)
        plate(p, [d * .34 + Z * 11.5, d * 1.2 + Z * 11.75, d * 1.42 + Z * 12.95, d * .34 + Z * 13.25], .05, STEEL)
        bar(p, d * .57 + Z * 13.72, d * .56 + Z * 14.3, .06, .04, STEEL, d)
    paint(p, m, gra)
    m = mark(p)
    ladder(p, (0, 0, 0), 9.72, -X, STEEL)
    place(p, m, rot('y', math.degrees(math.atan(.65 / 9.8))), (-ap(1.25), 0, 1.25))
    paint(p, m, galv(45, .3))
    steel_door(p, (1.34, -.38, 1.26), Y, .76, 1.95, bone(46, .14), gra)
    # the band and the stripe, on all eight faces
    vz = 1 / math.hypot(1, .65 / 9.8)
    for k in range(8):
        a = math.radians(k * 45)
        d, t = V3(math.cos(a), math.sin(a), 0), V3(-math.sin(a), math.cos(a), 0)
        v = unit(d * (-.65 / 9.8) + Z)
        o = d * ap(BAND[0]) + t * -.3 + Z * BAND[0]
        if k == 4:
            continue                      # the ladder's face stays bare
        armour(p, o, t, v, .6, 3.0 / vz, 1, 2, bone(47 + k), t=.05, stand=.02, pitch=.4, bolt=.014)
        m = mark(p)
        gbox(p, (.02, (STRIPE[0] - BAND[0]) / vz, .07), (.58, (STRIPE[1] - BAND[0]) / vz, .076), PAINT, .4, .002, 'z')
        place(p, m, np.stack([t, v, np.cross(t, v)], 1), o)
        paint(p, m, ora)
    # copper on the fins' leading edges, the insulators they stand off, the amber crown
    m = mark(p)
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        d = V3(math.cos(a), math.sin(a), 0)
        bar(p, d * 1.215 + Z * 11.75, d * 1.435 + Z * 12.95, .09, .035, BRASS, d)
        bar(p, d * .56 + Z * 14.3, d * .5 + Z * 14.42, .07, .05, BRASS, d)
    paint(p, m, copper(48, .3))
    for z in (11.42, 12.25, 13.0):
        insulator(p, (0, 0, z), Z, .47, 3, .075, sides=24)
    torus(p, (0, 0, 14.05), .5, .07, tone(GLOW_AMBER, 1.0), GLOW, 32, 8)
    fl.ball(p, (0, 0, 14.05), .2, tone(GLOW_AMBER, .8), GLOW, 16)
    for k in (1, 3, 6):
        a = math.radians(k * 45 + 10)
        moss_line(p, rng, V3(math.cos(a - .3), math.sin(a - .3), 0) * 2.0 * k8, V3(math.cos(a + .3), math.sin(a + .3), 0) * 2.0 * k8,
                  V3(math.cos(a), math.sin(a), 0), .05, .025, climb=.2)
    for _ in range(7):
        a = rng.uniform(0, TAU)
        moss_patch(p, rng, (math.cos(a) * 1.7, math.sin(a) * 1.7, .6 if rng.uniform() < .5 else 1.2), rng.uniform(.06, .14))
    for a in np.radians((0, 90, 225, 315)):
        d = V3(math.cos(a), math.sin(a), 0)
        streaks(p, rng, [d * (ap(6.0) + .001) + np.cross(Z, d) * rng.uniform(-.2, .2) + Z * 6.05], d, (.3, .7), (.03, .06))
    return done(p, facts=dict(light=(0, 0, 14.05), footing_across=4.0, platform_z=11.0, door='+x', ladder='-x', band=BAND, stripe=STRIPE, top=15.0))


@mesh('SM_GN_CoreDais', (12.0, 12.0, 1.2))
def core_dais():
    """The Array's core coupling: a round dais of three 0.2 m steps (radii 6.0, 5.4, 4.8) whose top, at z 0.6, is
    twelve bone-white plates inside an orange ring; three copper bus bars on ceramic stand-offs run out from the socket
    ring over the steps at 90, 210 and 330 degrees; the socket ring (outer radius 1.5, top at z 1.2) holds brass
    contacts round a well 0.9 m in radius whose floor is at z 0.3."""
    p = Part('SM_GN_CoreDais', (CONCRETE, STEEL, PAINT, BRASS, TILE, GLOW))
    conc = concrete(51, damp=.5, moss=.15, blot=.5)
    gra = graphite(54)
    m = mark(p)
    turn(p, [(6.0, 0), (6.0, .2), (5.4, .2), (5.4, .4), (4.8, .4), (4.8, .58)], CONCRETE, 72)
    annulus(p, 1.4, 4.8, .58, CONCRETE, na=72, nr=3)
    paint(p, m, conc)
    m = mark(p)
    for r, z in ((6.0, .2), (5.4, .4), (4.8, .6)):                 # steel nosings on the steps
        turn(p, [(r + .006, z - .04), (r + .006, z + .002), (r - .05, z + .002)], STEEL, 72)
    turn(p, [(1.5, .58), (1.5, 1.08), (1.42, 1.2), (1.0, 1.2), (1.0, .78), (.9, .78), (.9, .3)], STEEL, 48)
    disc(p, (0, 0, .3), .9, STEEL, Z, 48)
    for k in range(6):
        R = rot('z', k * 60 + 30)
        mm = mark(p)
        gbox(p, (1.5, -.16, .7), (1.58, .16, 1.0), STEEL, 9, .012, 'x')
        bolts(p, [(1.58, s * .1, z) for s in (-1, 1) for z in (.78, .92)], X, .02, STEEL)
        place(p, mm, R)
    for k in range(3):
        mm = mark(p)
        turn(p, [(.1, 0), (.1, .025), (.075, .04)], STEEL, 12, (1.21, 0, 1.2))
        place(p, mm, rot('z', k * 120 + 30))
    paint(p, m, gra)
    for k in range(12):
        m = mark(p)
        annulus(p, 1.56, 4.5, .6, PAINT, math.radians(k * 30) + .003, math.radians(k * 30 + 30) - .003, 6, 3, .02)
        paint(p, m, bone(55 + k, .06))
    m = mark(p)
    annulus(p, 4.52, 4.78, .6, PAINT, na=72, thick=.02)
    paint(p, m, orange(56, .08))
    for k in range(3):
        R = rot('z', 90 + k * 120)
        m = mark(p)
        for y in (-.07, .07):
            bar(p, (1.45, y, .735), (4.75, y, .735), .11, .03, BRASS)
            bar(p, (4.74, y, .735), (6.0, y, .275), .11, .03, BRASS)
            bar(p, (6.0, y, .285), (6.0, y, 0), .11, .03, BRASS, X)
        place(p, m, R)
        paint(p, m, copper(52 + k, .3))
        m = mark(p)
        for x in (2.0, 2.9, 3.8, 4.6):
            bar(p, (x, -.17, .757), (x, .17, .757), .08, .014, STEEL)
            bolts(p, [(x, s * .15, .764) for s in (-1, 1)], Z, .014, STEEL)
        place(p, m, R)
        paint(p, m, gra)
        for x in (2.0, 2.9, 3.8, 4.6):
            for y in (-.07, .07):
                q = R @ V3(x, y, .6)
                insulator(p, q, Z, .05, 2, .06, sides=12)
    m = mark(p)
    for k in range(6):
        mm = mark(p)
        gbox(p, (.74, -.13, .36), (.9, .13, .72), BRASS, 9, .015, 'X')
        place(p, mm, rot('z', k * 60))
    paint(p, m, steel(57, BRASS_WARM, 0.0, grime=.3))
    lights = []
    for k in range(3):
        q = rot('z', k * 120 + 30) @ V3(1.21, 0, 1.24)
        fl.disc(p, q, Z, .07, tone(GLOW_AMBER, 1.0), GLOW, 12, dome=.02, rim=tone(GLOW_AMBER, .6))
        lights.append(tuple(np.round(q, 3)))
    return done(p, facts=dict(steps=((6.0, .2), (5.4, .4), (4.8, .6)), deck_z=.6, deck_r=(1.5, 4.8), socket=dict(centre=(0, 0), well_r=.9, well_floor=.3,
                              ring_r=1.5, ring_top=1.2), bus_bars_deg=(90, 210, 330), bus_bar_top=.75, lights=lights))


@mesh('SM_GN_Conduit', (14.0, 2.4, 3.0))
def conduit_run():
    """Three heavy pipes (0.6 m bore, bone enamel, flanged every 3.6 m) on three concrete saddles with steel straps,
    along x at y -0.78, 0, 0.78 and axis height 1.3; at +x they turn down through elbows into a thrust block and the
    ground. A gate valve with an orange handwheel on the middle pipe, a gauge, a small service line alongside; and the
    grove's roots gripping them: one hugging all three, one coiled round a pipe, one arching over to z 3."""
    rng = np.random.default_rng(2606)
    p = Part('SM_GN_Conduit', (CONCRETE, STEEL, PAINT, RUST, BARK, MOSS))
    conc = concrete(61, damp=.8, moss=.45)
    gra = graphite(62, .22)
    ys, zc, r = (-.78, 0.0, .78), 1.3, .3
    for k, y in enumerate(ys):
        pts = [(x, y, zc) for x in np.linspace(-7, 5.5, 11)] + list(arc_pts((5.5, y, zc - .75), .75, 90, 0, X, Z, 9))[1:] + [(6.25, y, .28)]
        m = mark(p)
        pipe(p, pts, r, PAINT, 24)
        paint(p, m, bone(63 + k, .2))
        m = mark(p)
        turn(p, [(r + .004, -.15), (r + .004, .15)], PAINT, 24, (-6.2, y, zc), X)
        paint(p, m, orange(66))
    m = mark(p)
    for y in ys:
        for x in (-6.95, -3.6, 0.0, 3.6, 5.5):
            if not (y == 0.0 and x == -3.6):
                flange(p, (x, y, zc), X, r, r + .13, .028, STEEL, 12, sides=24)
    for x in (-5.4, -1.8, 1.8):                                     # straps over each pipe, bolted to the saddle
        for y in ys:
            arc = arc_pts((x, y, zc), r + .006, 0, 180, Y, Z, 11)
            for a, b in zip(arc, arc[1:]):
                bar(p, a, b, .09, .008, STEEL, (a + b) / 2 - V3(x, y, zc))
            for s in (-1, 1):
                q = V3(x, y + s * (r + .006), zc)
                bar(p, q, V3(q[0], q[1], 1.06), .09, .008, STEEL, Y)
                gbox(p, (x - .045, q[1] - .01 * s, 1.06), (x + .045, q[1] + s * .085, 1.075), STEEL, 9, .003)
                bolts(p, [(x, q[1] + s * .05, 1.075)], Z, .016, STEEL)
    # the gate valve on the middle pipe
    for x in (-3.02, -2.38):
        flange(p, (x, 0, zc), X, r, r + .13, .028, STEEL, 12, sides=24)
    fl.ball(p, (-2.7, 0, zc), .4, GREY, STEEL, 20, (.8, 1, 1))
    turn(p, [(.2, 0), (.2, .4), (.27, .4), (.27, .46), (.09, .46), (.09, .8), (.028, .8), (.028, 1.2)], STEEL, 20, (-2.7, 0, zc + .28))
    pipe(p, [(.9, -.78, zc + r - .02), (.9, -.78, zc + r + .2)], .02, STEEL, 8)
    turn(p, [(.1, 0), (.1, .045), (.085, .055), (.0, .055)], STEEL, 20, (.9, -.8, zc + r + .29), -Y)
    pipe(p, [(x, 1.1, 1.12) for x in np.linspace(-7, 5.9, 8)] + [(5.9, 1.1, .4)], .032, STEEL, 10)
    paint(p, m, gra)
    m = mark(p)
    torus(p, (-2.7, 0, zc + 1.45), .3, .022, GREY, PAINT, 28, 8)
    for a in np.radians((0, 90, 180, 270)):
        pipe(p, [(-2.7, 0, zc + 1.45), (-2.7 + .3 * math.cos(a), .3 * math.sin(a), zc + 1.45)], .014, PAINT, 6)
    turn(p, [(.06, -.04), (.06, .04), (0.0, .04)], PAINT, 12, (-2.7, 0, zc + 1.45))
    paint(p, m, orange(67, .25))
    disc(p, (.9, -.857, zc + r + .29), .08, PAINT, -Y, 20, tone(JUST_BONE, .9))
    m = mark(p)
    for x in (-5.4, -1.8, 1.8):
        gbox(p, (x - .45, -1.2, 0), (x + .45, 1.2, .25), CONCRETE, .6, .03, 'z')
        gbox(p, (x - .3, -1.14, .25), (x + .3, 1.14, 1.06), CONCRETE, .5, .03, 'z')
    gbox(p, (5.7, -1.2, 0), (7.0, 1.2, .42), CONCRETE, .5, .03, 'z')
    paint(p, m, conc)
    # the roots
    root(p, rng, [(-4.3, 1.14, 0), (-4.3, 1.17, .55), (-4.25, 1.13, 1.2), (-4.2, .8, 1.74), (-4.18, .4, 1.5), (-4.15, 0, 1.73), (-4.13, -.4, 1.5),
                  (-4.1, -.8, 1.74), (-4.05, -1.13, 1.2), (-4.0, -1.17, .55), (-4.0, -1.14, 0)], (.13, .1, .09, .1, .13), sides=10)
    coil = [(-1.15, 1.14, 0), (-1.15, 1.16, .5)] + [(-.9 + 1.9 * t, .78 + (r + .07) * math.cos(a), zc + (r + .07) * math.sin(a))
                                                      for t, a in zip(np.linspace(0, 1, 15), np.radians(np.linspace(-40, 560, 15)))]
    root(p, rng, coil, (.09, .07, .045), BARK_DARK, 8, 4)
    root(p, rng, [(3.0, -1.1, 0), (3.02, -1.1, .6), (3.2, -1.0, 1.5), (3.55, -.5, 2.45), (3.9, .1, 2.86), (4.2, .65, 2.4), (4.42, 1.02, 1.3),
                  (4.55, 1.1, .5), (4.55, 1.1, 0)], (.15, .12, .1, .12, .14), sides=10)
    root(p, rng, [(3.9, .1, 2.8), (3.84, .04, 2.2), (3.78, 0, 1.62), (3.4, -.05, 1.63), (2.7, .05, 1.64)], (.06, .035), BARK_DARK, 6)
    root(p, rng, [(6.62, -1.12, 0), (6.6, -1.1, .45), (6.42, -.5, .93), (6.3, .2, 1.0), (6.5, .9, .62), (6.66, 1.12, 0)], (.09, .07, .09), sides=8)
    root(p, rng, [(-4.15, 0, 1.72), (-3.7, .06, 1.64), (-3.2, -.04, 1.72)], (.05, .025), BARK_DARK, 6)
    for x, y, z in ((-5.4, .4, 1.06), (-1.8, -.4, 1.06), (1.8, 1.0, 1.06), (6.4, -.8, .42), (6.6, .5, .42), (-5.4, -1.0, 1.06)):
        moss_patch(p, rng, (x + rng.uniform(-.15, .15), y, z), rng.uniform(.08, .15))
    for x in (-6.0, -2.0, .8, 2.8, 4.6):
        moss_patch(p, rng, (x, ys[int(rng.integers(0, 3))], zc + r - .006), rng.uniform(.1, .16), .02)
    for x in (-5.4, -1.8, 1.8):
        moss_line(p, rng, (x + .45, -1.2, 0), (x + .45, 1.2, 0), X, .05, .025, climb=.15)
    streaks(p, rng, [(x, y - .3 * .5, zc - .26) for x in (-3.6, 0.0, 3.6) for y in (ys[0],)], -Y, (.2, .5), (.04, .07), RUST_ORANGE, RUST)
    return done(p, facts=dict(pipes_y=ys, axis_z=zc, bore_r=r, open_end_x=-7.0, down_at_x=6.25, saddles_x=(-5.4, -1.8, 1.8), valve=(-2.7, 0, zc + 1.45)))


@mesh('SM_GN_Bunker', (9.0, 7.0, 4.6))
def bunker():
    """The Array's control bunker: a blast-hardened block 9 x 7 m with its corners cut at 45 degrees, walls to 3.3 m,
    a sloped glacis up to the roof at 4.0 and an armoured cupola, vents and an aerial reaching 4.6. In the front (+x)
    the blast-door opening, 2.2 m wide (y -1.1 to 1.1) and 2.6 m high: a reveal 0.65 m deep, the leaf's slot (x 3.55
    to 3.85, with its pocket in the +y jamb), and behind it a recess 1.6 m deep with an inner door, where a person can
    stand. A slit window with armoured glass beside the door, a blast vent on the -y wall, cable entries on the +y
    wall, and the bone-white band (2.75 to 3.25 m) with the orange stripe all round."""
    rng = np.random.default_rng(2607)
    p = Part('SM_GN_Bunker', (CONCRETE, STEEL, PAINT, GLASS, RUST, MOSS, GLOW))
    WALL, ROOF = 3.3, 4.0
    BB, BS = (2.75, 3.25), (3.06, 3.16)
    conc = concrete(71, damp=1.3, ledges=((WALL, .8), (BB[0], .6)), moss=.4)
    inner = concrete(72, base=CONCRETE_STAIN, damp=1.0, moss=.08, k=.85)
    gra = graphite(73)
    plan = [(4.5, -2.7), (4.5, 2.7), (3.7, 3.5), (-3.7, 3.5), (-4.5, 2.7), (-4.5, -2.7), (-3.7, -3.5), (3.7, -3.5)]
    top = [(3.8, -2.41), (3.8, 2.41), (3.41, 2.8), (-3.41, 2.8), (-3.8, 2.41), (-3.8, -2.41), (-3.41, -2.8), (3.41, -2.8)]
    DX0, DX1, RX = 3.55, 3.85, 1.95
    for k in range(8):
        a, b = V3(*plan[k], 0), V3(*plan[(k + 1) % 8], 0)
        L = float(np.linalg.norm(b - a))
        u = (b - a) / L
        nj = max(1, round(L / 2.3))
        sheet(p, a, u, Z, L, WALL, .65, CONCRETE, holes=((1.6, 3.8, 0, 2.6), (.35, 1.25, 1.5, 1.8)) if k == 0 else (),
              ju=[L * i / nj for i in range(1, nj)], jv=(1.1, 2.2), back=False, rim='', ties=(.9, .55, .016), fn=conc)
    m = mark(p)
    gprism(p, [V3(*q, WALL) for q in plan], [V3(*q, ROOF) for q in top], CONCRETE, .8, '')
    gquad(p, (-3.41, -2.41, ROOF), (3.41, -2.41, ROOF), (3.41, 2.41, ROOF), (-3.41, 2.41, ROOF), CONCRETE, 8, 6)
    for s in (-1, 1):
        gface(p, (-3.41, s * 2.41, ROOF), (3.41, s * 2.41, ROOF), (3.41, s * 2.8, ROOF), (-3.41, s * 2.8, ROOF), CONCRETE, .9, Z)
        gface(p, (s * 3.41, -2.41, ROOF), (s * 3.8, -2.41, ROOF), (s * 3.8, 2.41, ROOF), (s * 3.41, 2.41, ROOF), CONCRETE, .9, Z)
        for t in (-1, 1):
            face(p, [(s * 3.41, t * 2.41, ROOF), (s * 3.8, t * 2.41, ROOF), (s * 3.41, t * 2.8, ROOF)], CONCRETE, Z)
    paint(p, m, conc)
    # inside the opening: the leaf's slot with its pocket, and the recess behind it
    m = mark(p)
    gface(p, (RX, -1.1, 0), (DX1, -1.1, 0), (DX1, -1.1, 2.6), (RX, -1.1, 2.6), CONCRETE, .6, Y)
    gface(p, (RX, 1.1, 0), (DX0, 1.1, 0), (DX0, 1.1, 2.6), (RX, 1.1, 2.6), CONCRETE, .6, -Y)
    gface(p, (DX0, 1.7, 0), (DX1, 1.7, 0), (DX1, 1.7, 2.6), (DX0, 1.7, 2.6), CONCRETE, .6, -Y)
    gface(p, (DX0, 1.1, 0), (DX0, 1.7, 0), (DX0, 1.7, 2.6), (DX0, 1.1, 2.6), CONCRETE, .6, X)
    gface(p, (DX1, 1.1, 0), (DX1, 1.7, 0), (DX1, 1.7, 2.6), (DX1, 1.1, 2.6), CONCRETE, .6, -X)
    gface(p, (DX0, 1.1, 2.6), (DX1, 1.1, 2.6), (DX1, 1.7, 2.6), (DX0, 1.7, 2.6), CONCRETE, .6, -Z)
    gface(p, (RX, -1.1, 2.6), (DX1, -1.1, 2.6), (DX1, 1.1, 2.6), (RX, 1.1, 2.6), CONCRETE, .6, -Z)
    gface(p, (RX, -1.1, 0), (RX, 1.1, 0), (RX, 1.1, 2.6), (RX, -1.1, 2.6), CONCRETE, .6, X)
    face(p, [(3.86, -2.35, 1.5), (3.86, -1.45, 1.5), (3.86, -1.45, 1.8), (3.86, -2.35, 1.8)], CONCRETE, X)
    paint(p, m, inner)
    m = mark(p)
    fz = steel(74, STEEL_GREY, .3, ground=-2.0)
    gbox(p, (RX, -1.1, 0), (DX0 - .02, 1.1, .03), STEEL, .7, .004, 'z')
    gbox(p, (DX1 + .02, -1.1, 0), (4.5, 1.1, .03), STEEL, .7, .004, 'z')
    gbox(p, (DX0 - .02, -1.1, 0), (DX1 + .02, 1.7, .006), STEEL, .7, .001, 'z')
    for y in (-2.35, -1.45):                  # the slit's steel frame round its glass block
        gbox(p, (4.1, y - .03, 1.47), (4.2, y + .03, 1.83), STEEL, 9, .006)
    for z in (1.5, 1.8):
        gbox(p, (4.1, -2.35, z - .03), (4.2, -1.45, z + .03), STEEL, 9, .006)
    paint(p, m, fz)
    face(p, [(4.15, -2.32, 1.53), (4.15, -1.48, 1.53), (4.15, -1.48, 1.77), (4.15, -2.32, 1.77)], GLASS, X, tone(GLASS_GREEN, .45))
    steel_door(p, (RX, -.45, .03), Y, .9, 2.0, bone(75, .15), gra)
    bulkhead(p, (2.75, 0, 2.6), -Z, STEEL, GLOW_AMBER, .1, .8)
    # the band and the stripe
    for k in range(8):
        a, b = V3(*plan[k], BB[0]), V3(*plan[(k + 1) % 8], BB[0])
        L = float(np.linalg.norm(b - a))
        u = (b - a) / L
        armour(p, a + u * .04, u, Z, L - .08, BB[1] - BB[0], max(1, round(L / 1.35)), 1, bone(76 + k), t=.05, stand=.015, pitch=.4, bolt=.014)
        m = mark(p)
        gbox(p, (.02, BS[0] - BB[0], .065), (L - .1, BS[1] - BB[0], .07), PAINT, .6, .002, 'z')
        place(p, m, np.stack([u, Z, np.cross(u, Z)], 1), a + u * .04)
        paint(p, m, orange(77))
    # roof: the cupola, two mushroom vents, a hatch, the aerial
    m = mark(p)
    turn(p, [(.75, 0), (.75, .22), (.62, .42), (.32, .54), (.05, .56)], STEEL, 28, (-1.6, 0, ROOF))
    disc(p, (-1.6, 0, ROOF + .56), .05, STEEL, Z, 12)
    bolts(p, [(-1.6 + .68 * math.cos(a), .68 * math.sin(a), ROOF + .225) for a in np.linspace(0, TAU, 10, endpoint=False)], Z, .03, STEEL)
    for a in np.radians((0, 90, 180, 270)):
        d = V3(math.cos(a), math.sin(a), 0)
        bar(p, V3(-1.6, 0, ROOF + .33) + d * .69 - np.cross(Z, d) * .16, V3(-1.6, 0, ROOF + .33) + d * .69 + np.cross(Z, d) * .16, .06, .05, STEEL, d)
    for y in (-1.6, 1.6):
        turn(p, [(.16, 0), (.16, .32), (.34, .3), (.34, .36), (.2, .5), (.04, .52)], STEEL, 20, (2.1, y, ROOF))
        disc(p, (2.1, y, ROOF + .52), .04, STEEL, Z, 8)
    gbox(p, (.1, -1.75, ROOF), (.9, -.95, ROOF + .07), STEEL, 9, .012, 'z')
    bolts(p, [(x, y, ROOF + .07) for x in (.18, .82) for y in (-1.67, -1.03)], Z, .02, STEEL)
    pipe(p, [(.35, -1.35, ROOF + .09), (.35, -1.35, ROOF + .13), (.65, -1.35, ROOF + .13), (.65, -1.35, ROOF + .09)], .014, STEEL, 8)
    turn(p, [(.07, 0), (.07, .1), (.02, .12), (.012, .6)], STEEL, 10, (-3.0, 2.0, ROOF))
    paint(p, m, gra)
    # the blast vent, the cable entries, the door's lamp and control box, step irons to the roof
    louvre(p, (-.6, -3.5, 1.85), X, 1.2, .5, gra)
    m = mark(p)
    bar(p, (-.7, -3.58, 2.44), (.7, -3.58, 2.44), .2, .012, STEEL, unit(V3(0, -.5, .85)))
    gbox(p, (-3.0, 3.5, .55), (-2.0, 3.53, 1.2), STEEL, 9, .006, 'y')
    bolts(p, [(x, 3.53, z) for x in (-2.94, -2.06) for z in (.62, 1.13)], Y, .018, STEEL)
    for x in (-2.8, -2.6, -2.4, -2.2):
        pipe(p, [(x, 3.5, .9), (x, 3.66, .9), (x, 3.72, .87), (x, 3.75, .8), (x, 3.75, 0)], .045, STEEL, 10)
        turn(p, [(.06, 0), (.06, .03)], STEEL, 10, (x, 3.53, .9), Y)
    gbox(p, (4.5, 1.33, 1.15), (4.58, 1.57, 1.5), STEEL, 9, .01, 'x')
    conduit(p, [(4.515, 1.45, 1.5), (4.515, 1.45, 2.13)], X, STEEL, .014, .3)
    for z in np.arange(.45, 3.2, .3):
        pipe(p, [(-4.5, 1.6, z), (-4.63, 1.6, z), (-4.63, 2.0, z), (-4.5, 2.0, z)], .012, STEEL, 6, cap=False)
    paint(p, m, galv(78, .32))
    bulkhead(p, (4.5, 1.45, 2.25), X, STEEL, GLOW_AMBER, .09)
    # moss, and what runs down from the band and the vents
    for k in range(8):
        a, b = V3(*plan[k], 0), V3(*plan[(k + 1) % 8], 0)
        if k == 0:
            for a2, b2 in ((a, V3(4.5, -1.1, 0)), (V3(4.5, 1.1, 0), b)):
                moss_line(p, rng, a2, b2, X, .05, .025, climb=.2)
        else:
            moss_line(p, rng, a, b, unit(np.cross(b - a, Z)), .06, .025, climb=.35 if k in (3, 4, 5) else .2)
    for _ in range(16):
        q = V3(rng.uniform(-3.6, 3.6), rng.uniform(-2.6, 2.6), ROOF)
        if np.hypot(q[0] + 1.6, q[1]) > .95 and not (0 < q[0] < 1.0 and -1.85 < q[1] < -.85) and abs(q[0] - 2.1) > .45:
            moss_patch(p, rng, q, rng.uniform(.08, .22))
    streaks(p, rng, [(4.5, rng.uniform(-2.5, 2.5), BB[0] - .01) for _ in range(5)], X, (.3, .8), (.03, .07))
    streaks(p, rng, [(rng.uniform(-3.4, 3.4), -3.5, BB[0] - .01) for _ in range(4)] + [(-.3, -3.5, 1.84), (.4, -3.5, 1.84)], -Y, (.3, .8), (.03, .07))
    streaks(p, rng, [(rng.uniform(-3.4, 3.4), 3.5, BB[0] - .01) for _ in range(4)], Y, (.3, .8), (.03, .07))
    return done(p, facts=dict(door_opening=dict(face_x=4.5, y=(-1.1, 1.1), z=(0, 2.6)), leaf_at=((DX0 + DX1) / 2, 0, 0), leaf_slot_x=(DX0, DX1),
                              pocket='+y (y 1.1 to 1.7 is modelled)', recess=dict(x=(RX + .08, DX0), y=(-1.1, 1.1), z=(.03, 2.6)), roof_z=ROOF,
                              band=BB, stripe=BS, window=dict(y=(-2.35, -1.45), z=(1.5, 1.8)), lamp=(4.6, 1.45, 2.25), top=4.6))


@mesh('SM_GN_BunkerDoor', (.3, 2.2, 2.6))
def bunker_door():
    """The bunker's blast door, a sliding leaf 2.2 m wide, 2.6 m high and 0.3 m through, standing on z 0, centred:
    a welded plate in a graphite frame with two bone-white panels, an orange stripe, a spoked locking wheel, an
    armoured-glass port and an amber lock lamp on the outside (+x); ribs and a pull bar on the inside."""
    p = Part('SM_GN_BunkerDoor', (STEEL, PAINT, GLASS, GLOW))
    gra = graphite(81)
    m = mark(p)
    gbox(p, (-.1, -1.1, 0), (.1, 1.1, 2.6), STEEL, .6, .012)
    for y0, y1 in ((-1.1, -.98), (.98, 1.1)):
        gbox(p, (.1, y0, 0), (.14, y1, 2.6), STEEL, .7, .008, 'x')
    for z0, z1 in ((0, .12), (1.24, 1.36), (2.48, 2.6)):
        gbox(p, (.1, -.98, z0), (.139, .98, z1), STEEL, .7, .008, 'x')
    for y in (-.6, 0, .6):
        gbox(p, (-.14, y - .04, .05), (-.1, y + .04, 2.55), STEEL, .7, .008, 'X')
    for z in (.05, 1.3, 2.47):
        gbox(p, (-.139, -1.05, z), (-.1, 1.05, z + .08), STEEL, .7, .008, 'X')
    pipe(p, [(-.14, .75, 1.0), (-.148, .75, 1.0), (-.148, .75, 1.5), (-.14, .75, 1.5)], .014, STEEL, 8)
    hoop(p, (.135, 0, 1.3), .2, .014, STEEL, X, 24, 8)
    for a in np.radians((90, 210, 330)):
        pipe(p, [(.135, 0, 1.3), (.135, .2 * math.cos(a), 1.3 + .2 * math.sin(a))], .01, STEEL, 6)
    turn(p, [(.05, 0), (.05, .045), (.0, .045)], STEEL, 12, (.1, 0, 1.3), X)
    turn(p, [(.11, 0), (.11, .03), (.075, .03)], STEEL, 16, (.14, 0, 2.0), X)
    bolts(p, [(.17, .092 * math.cos(a), 2.0 + .092 * math.sin(a)) for a in np.linspace(0, TAU, 6, endpoint=False)], X, .009, STEEL, washer=False)
    turn(p, [(.05, 0), (.05, .02), (.035, .02)], STEEL, 12, (.14, .55, 1.3), X)
    paint(p, m, gra)
    for z0, z1, sd in ((.12, 1.24, 82), (1.36, 2.48, 83)):
        armour(p, (.1, -.98, z0), Y, Z, 1.96, z1 - z0, 1, 1, bone(sd), t=.025, stand=.004, pitch=.36, bolt=.011)
    m = mark(p)
    gbox(p, (.129, -.96, 1.6), (.133, .96, 1.7), PAINT, .5, .001, 'x')
    paint(p, m, orange(84))
    disc(p, (.172, 0, 2.0), .073, GLASS, X, 16, tone(GLASS_GREEN, .5))
    fl.disc(p, (.162, .55, 1.3), X, .034, tone(GLOW_AMBER, 1.0), GLOW, 10, dome=.008, rim=tone(GLOW_AMBER, .6))
    return done(p, facts=dict(size=(.3, 2.2, 2.6), front='+x', lock_lamp=(.165, .55, 1.3)))


def split(fn_a, fn_b, x0):
    """A material that is fn_a where x < x0 and fn_b beyond (the dry and the wetted side of one face)."""
    def f(P, N):
        P = np.asarray(P, np.float64).reshape(-1, 3)
        return np.where((P[:, 0] >= x0)[:, None], fn_b(P, N), fn_a(P, N))
    return f


def window(p, o, u, w, h, fn, rng, depth=.12, bar=.045, nx=2, ny=1, glass=.7, slot=STEEL, back=.35, back_slot=CONCRETE):
    """A steel-framed window set `depth` back in an opening: o = the opening's bottom-left corner on the wall's face
    seen from outside, u along the wall; it faces u x Z. nx by ny lights, each keeping its glass with probability
    `glass` and otherwise a few shards in the frame; back: a dark panel that far behind the face (the unlit room)."""
    o, u = np.asarray(o, np.float64), unit(u)
    f = np.cross(u, Z)
    R = np.stack([u, Z, f], 1)
    m = mark(p)
    d0, d1 = -depth - .05, -depth
    for lo, hi in (((0, 0, d0), (w, bar, d1)), ((0, h - bar, d0), (w, h, d1)), ((0, bar, d0), (bar, h - bar, d1)), ((w - bar, bar, d0), (w, h - bar, d1))):
        gbox(p, lo, hi, slot, 9, .006)
    for i in range(1, nx):
        gbox(p, (w * i / nx - bar * .4, bar, d0), (w * i / nx + bar * .4, h - bar, d1), slot, 9, .004)
    for j in range(1, ny):
        gbox(p, (bar, h * j / ny - bar * .4, d0 + .006), (w - bar, h * j / ny + bar * .4, d1 - .006), slot, 9, .004)
    gbox(p, (-.03, -.035, d1), (w + .03, .0, .04), slot, 9, .006)           # a pressed steel sill with a drip
    place(p, m, R, o)
    paint(p, m, fn)
    zc = (d0 + d1) / 2
    gc = tone(GLASS_GREEN, .45)
    for i in range(nx):
        for j in range(ny):
            a0, a1 = w * i / nx + (bar if i == 0 else bar * .4), w * (i + 1) / nx - (bar if i == nx - 1 else bar * .4)
            b0, b1 = h * j / ny + (bar if j == 0 else bar * .4), h * (j + 1) / ny - (bar if j == ny - 1 else bar * .4)
            if rng.uniform() < glass:
                q = np.array([(a0, b0, zc), (a1, b0, zc), (a1, b1, zc), (a0, b1, zc)])
                p.add(q @ R.T + o, [[0, 1, 2, 3]], vary(rng, gc, .15), GLASS, False)
                continue
            for _ in range(int(rng.integers(1, 4))):
                t0, t1 = np.sort(rng.uniform(0, 1, 2))
                reach = rng.uniform(.15, .5)
                edge = int(rng.integers(0, 4))
                if edge < 2:
                    b = b0 if edge == 0 else b1
                    q = [(a0 + (a1 - a0) * t0, b, zc), (a0 + (a1 - a0) * t1, b, zc), (a0 + (a1 - a0) * (t0 + t1) / 2, b + (b1 - b0) * reach * (1 if edge == 0 else -1), zc)]
                else:
                    a = a0 if edge == 2 else a1
                    q = [(a, b0 + (b1 - b0) * t0, zc), (a, b0 + (b1 - b0) * t1, zc), (a + (a1 - a0) * reach * (1 if edge == 2 else -1), b0 + (b1 - b0) * (t0 + t1) / 2, zc)]
                q = np.array(q)
                p.add(q @ R.T + o, [fl._facing(q, [0, 1, 2], Z)], vary(rng, gc, .2), GLASS, False)
    if back:
        q = np.array([(0, 0, -back), (w, 0, -back), (w, h, -back), (0, h, -back)])
        p.add(q @ R.T + o, [[0, 1, 2, 3]], tone(CONCRETE_DARK, .35), back_slot, False)


# ================================================================ the Weir

WEIR_DECK, WEIR_POND, WEIR_SILL, WEIR_MASS = 12.0, 10.6, 5.0, 11.6
WEIR_BAYS = (-9.0, 0.0, 9.0)
WEIR_PIERS = ((-15.5, -12.5), (-5.5, -3.5), (3.5, 5.5), (12.5, 15.5))


def _weir_pier(p, ya, yb, fn, fn_up, slot_a, slot_b):
    """One pier between y ya and yb: flanks with lift joints and (where a gate runs) a slot 0.5 m wide and 0.25 deep
    from the sill to the top, a pointed cutwater upstream, a raked and rounded tail downstream."""
    D, S = WEIR_DECK, WEIR_MASS
    yc, w = (ya + yb) / 2, (yb - ya) / 2
    X0, X1, RAKE, G0, G1, GD = -3.3, 3.0, 10.235, 2.15, 2.65, .25
    lifts = [z for z in np.arange(1.5, RAKE, 1.5)]
    both = split(fn, fn_up, 2.62)
    for y, sg, has in ((ya, 1, slot_a), (yb, -1, slot_b)):
        u = sg * X
        o = V3(X0 if sg > 0 else X1, y, 0)
        a0, a1 = (G0 - X0, G1 - X0) if sg > 0 else (X1 - G1, X1 - G0)
        sheet(p, o, u, Z, X1 - X0, RAKE, GD, CONCRETE, holes=[(a0, a1, WEIR_SILL, RAKE)] if has else (), jv=lifts, back=False, rim='',
              ties=(1.05, .75, .018), fn=both)
        sheet(p, (-2 if sg > 0 else 2, y, RAKE), u, Z, 4, S - RAKE, 0, CONCRETE, back=False, rim='', fn=fn)
        b0, b1 = (G0 - 2, G1 - 2) if sg > 0 else (X1 - G1, X1 - G0)
        sheet(p, (2 if sg > 0 else X1, y, RAKE), u, Z, 1, D - RAKE, GD, CONCRETE, holes=[(b0, b1, 0, D - RAKE)] if has else (), back=False, rim='', fn=fn_up)
        m = mark(p)
        face(p, [(X0, y, RAKE), (-2, y, RAKE), (-2, y, S)], CONCRETE, -sg * Y)
        paint(p, m, fn)
        if has:
            yi = y + sg * GD
            m = mark(p)
            gface(p, (G0, yi, WEIR_SILL), (G1, yi, WEIR_SILL), (G1, yi, D), (G0, yi, D), CONCRETE, 1.2, -sg * Y)
            paint(p, m, both)
            m = mark(p)
            for xa, xb in ((G0 - .09, G0), (G1, G1 + .09)):
                gbox(p, (xa, y - sg * .012, WEIR_SILL), (xb, y, D), RUST, 1.5, .003)
            paint(p, m, rusty(97))
    m = mark(p)
    face(p, [(2, ya, D), (3, ya, D), (4, yc, D), (3, yb, D), (2, yb, D)], CONCRETE, Z)
    gface(p, (X0, ya, RAKE), (-2, ya, S), (-2, yb, S), (X0, yb, RAKE), CONCRETE, 1.2, Z)
    base = [(X0, ya), (-3.8, yc - .6 * w), (-4.0, yc), (-3.8, yc + .6 * w), (X0, yb)]
    gprism(p, [V3(x, y, 0) for x, y in base], [V3(x, y, S + (x + 2) * 1.05) for x, y in base], CONCRETE, 1.3, 't')
    paint(p, m, fn)
    m = mark(p)
    gface(p, (3, ya, 0), (4, yc, 0), (4, yc, D), (3, ya, D), CONCRETE, 1.3, V3(1, -1, 0))
    gface(p, (4, yc, 0), (3, yb, 0), (3, yb, D), (4, yc, D), CONCRETE, 1.3, V3(1, 1, 0))
    paint(p, m, fn_up)


def _weir_bay(p, rng, yc, fn):
    """The spillway of one bay (an ogee from the gate's sill at z 5 down to a flip lip at the toe, with baffle blocks),
    and its gate: a vertical-lift leaf of skin plate upstream on seven horizontal girders, closed on the sill."""
    y0, y1 = yc - 3.5, yc + 3.5
    prof = [(3.0, 3.2), (2.9, 4.6), (2.75, 5.0), (2.0, 5.0), (1.2, 4.75), (.2, 4.0), (-.9, 2.9), (-2.0, 1.85), (-2.9, 1.2), (-3.5, .95), (-3.85, 1.05), (-4.0, 1.25)]
    ys = np.linspace(y0, y1, 7)
    n = len(ys)
    m = mark(p)
    p.add([(x, y, z) for x, z in prof for y in ys], [[i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j]
                                                      for i in range(len(prof) - 1) for j in range(n - 1)], GREY, CONCRETE, True)
    gface(p, (-4.0, y0, 0), (-4.0, y1, 0), (-4.0, y1, 1.25), (-4.0, y0, 1.25), CONCRETE, 1.2, -X)
    gface(p, (3.0, y0, 0), (3.0, y1, 0), (3.0, y1, 3.2), (3.0, y0, 3.2), CONCRETE, 1.2, X)
    for y in np.linspace(y0 + .6, y1 - .6, 6):
        gbox(p, (-3.45, y - .26, .9), (-2.92, y + .26, 1.6), CONCRETE, .6, .03, 'z')
    paint(p, m, fn)
    # the gate
    ga, gb = y0 - .2, y1 + .2
    m = mark(p)
    gbox(p, (2.6, ga, WEIR_SILL), (2.622, gb, 11.0), RUST, .9, .004)
    for z in (5.22, 5.9, 6.7, 7.65, 8.75, 9.95, 10.88):
        ibeam(p, (2.39, ga, z), (2.39, gb, z), .42, .2, RUST, X)
    for y in (ga + .1, gb - .1):
        gbox(p, (2.18, y - .1, WEIR_SILL), (2.6, y + .1, 11.0), RUST, 1.2, .006)
    for y in np.linspace(ga, gb, 7)[1:-1]:
        bar(p, (2.39, y, WEIR_SILL + .05), (2.39, y, 10.95), .4, .012, RUST, Y)
    gbox(p, (2.16, ga + .2, WEIR_SILL - .0), (2.2, gb - .2, WEIR_SILL + .08), RUST, 1.2, .004)         # the bottom seal's clamp bar
    for y in (yc - 2.3, yc + 2.3):
        plate(p, [(2.28, y, 11.0), (2.52, y, 11.0), (2.52, y, 11.26), (2.4, y, 11.36), (2.28, y, 11.26)], .03, RUST)
        bolts(p, [(2.4, y + .015, 11.2)], Y, .03, RUST, washer=False)
    paint(p, m, steel(98 + int(yc), mix(RUST_ORANGE, RUST_DARK, .35), 0.0, ground=4.0, damp=2.5, grime=.5, streak=.4))


def _weir_hoist(p, yc, ya, yb, fn):
    """The gate's twin-stem screw hoist: a beam of two channels between the pier heads, a bevel gearbox with a stem
    cover over each lifting point, a line shaft between them and a drive unit in the middle whose input shaft
    points at the deck (where the hand-wheel stand goes)."""
    D = WEIR_DECK
    m = mark(p)
    for x, toes in ((2.25, 1), (2.55, -1)):
        channel(p, (x, ya, D + .12), (x, yb, D + .12), .24, .09, STEEL, Z, toes)
    for y in np.arange(ya + .5, yb - .2, 1.3):
        bar(p, (2.2, y, D + .245), (2.6, y, D + .245), .14, .01, STEEL)
    for y in (ya + .25, yb - .25):
        gbox(p, (2.1, y - .22, D), (2.7, y + .22, D + .012), STEEL, 9, .003, 'z')
        bolts(p, [(x, y + sy * .16, D + .012) for x in (2.14, 2.66) for sy in (-1, 1)], Z, .018, STEEL)
    for y in (yc - 2.3, yc + 2.3):
        pipe(p, [(2.4, y, 11.3), (2.4, y, D + .3)], .045, STEEL, 12)
        gbox(p, (2.2, y - .2, D + .25), (2.6, y + .2, D + .62), STEEL, 9, .02)
        bolts(p, [(x, y + sy * .15, D + .62) for x in (2.26, 2.54) for sy in (-1, 1)], Z, .014, STEEL)
        turn(p, [(.1, 0), (.1, .05), (.07, .05), (.07, 1.08), (.085, 1.08), (.085, 1.13), (.02, 1.13)], STEEL, 16, (2.4, y, D + .62))
        disc(p, (2.4, y, D + 1.75), .02, STEEL, Z, 8)
    gbox(p, (2.14, yc - .28, D + .25), (2.66, yc + .28, D + .74), STEEL, 9, .025)
    bolts(p, [(x, yc + sy * .2, D + .74) for x in (2.22, 2.58) for sy in (-1, 1)], Z, .016, STEEL)
    pipe(p, [(2.4, yc - 2.1, D + .44), (2.4, yc + 2.1, D + .44)], .028, STEEL, 10)
    for y in (yc - 1.2, yc + 1.2):
        gbox(p, (2.3, y - .06, D + .25), (2.5, y + .06, D + .5), STEEL, 9, .01)
    pipe(p, [(2.14, yc, D + .5), (1.99, yc, D + .5)], .035, STEEL, 10)
    gbox(p, (1.96, yc - .03, D + .47), (2.0, yc + .03, D + .53), STEEL, 9, .004)
    paint(p, m, fn)


def _weir_tower(p, s, rng, lamps):
    """A gate tower on the deck at y 14 * s: a concrete house 3.2 x 3.0 m and 5 m high (roof at z 17.0) on the
    upstream half of the deck, its door facing the walkway (-x), windows on the other three sides."""
    D = WEIR_DECK
    y0, y1 = (12.5, 15.5) if s > 0 else (-15.5, -12.5)
    x0, x1, T, H = 0.0, 3.2, .25, 4.72
    fn = concrete(96 + s, ground=D - 1.5, damp=3.0, moss=.3, north=(1.0, 0.0), ledges=((D + H, 1.0),))
    frame = galv(99, .4)
    walls = ((V3(x0, y1, D), -Y, 3.0, [(1.05, 1.95, 0, 2.05)]), (V3(x1, y0, D), Y, 3.0, [(.7, 2.3, 1.3, 2.4)]),
             (V3(x1, y1, D), -X, 3.2, [(1.0, 2.2, 1.3, 2.4)]), (V3(x0, y0, D), X, 3.2, [(1.0, 2.2, 1.3, 2.4)]))
    for k, (o, u, L, holes) in enumerate(walls):
        sheet(p, o, u, Z, L, H, T, CONCRETE, holes=holes, jv=(1.5, 3.0), back=False, rim='', ties=(1.0, .75, .016), fn=fn)
        a0, a1, b0, b1 = holes[0]
        if k == 0:
            f = np.cross(u, Z)
            steel_door(p, o + u * (a0 + .07) - f * .1, u, a1 - a0 - .14, b1 - .07, olive(100 + s, .3), frame)
        else:
            window(p, o + u * a0 + Z * b0, u, a1 - a0, b1 - b0, frame, rng, nx=3 if a1 - a0 > 1.4 else 2, glass=.55)
    m = mark(p)
    gbox(p, (x0 - .25, y0 - .25, D + H), (x1 + .25, y1 + .25, 17.0), CONCRETE, 1.0, .03)
    paint(p, m, fn)
    yd = (y0 + y1) / 2
    bulkhead(p, (x0, yd + .8, D + 2.25), -X, STEEL, GLOW_AMBER, .09)
    lamps.append((x0 - .1, yd + .8, D + 2.25))
    m = mark(p)
    conduit(p, [(x0 - .015, yd + .8, D + 2.13), (x0 - .015, yd + .8, D + .02)], -X, STEEL, .014, .7)
    yp = y1 - .12 if s > 0 else y0 + .12                              # rainwater pipe down the outer corner of the door face
    pipe(p, [(x0 - .3, yp, D + H + .02), (x0 - .3, yp, D + H - .15), (x0 - .07, yp, D + H - .4), (x0 - .07, yp, D + .12), (x0 - .2, yp, D + .04)], .045, STEEL, 10)
    for z in (D + .9, D + 2.3, D + 3.7):
        bar(p, (x0 - .07, yp - .07, z), (x0 - .07, yp + .07, z), .05, .1, STEEL, X)
    paint(p, m, frame)


@mesh('SM_GN_Weir', (8.0, 56.0, 17.0))
def weir():
    """The weir: 56 m of concrete along y, +x upstream. A walkable deck 4 m wide (x -2 to 2) at z 12.0 from end to
    end, guard rails on both edges. In the middle three sluice bays 7 m wide (centred on y -9, 0, 9) between piers with
    cutwaters: in each a closed vertical-lift gate on a sill at z 5, an ogee spillway down to baffle blocks at the toe,
    and on the pier heads beside the deck a twin-stem screw hoist. Two gate towers stand on the upstream half of the
    deck at y -14 and 14 (x 0 to 3.2, roofs at z 17.0), leaving the downstream 2 m free. Either side, a gravity
    wall battered downstream, cast in 1.5 m lifts, runs out to y -28 and 28; the headpond stands at about z 10.6."""
    rng = np.random.default_rng(2610)
    p = Part('SM_GN_Weir', (CONCRETE, STEEL, RUST, PAINT, GLASS, MOSS, BARK, LEAF, GLOW))
    D, S = WEIR_DECK, WEIR_MASS
    conc = concrete(91, damp=3.5, streak=.42, moss=.4, north=(1.0, 0.0), ledges=((S, 1.5),))
    wet = concrete(92, damp=3.5, streak=.3, moss=.5, north=(1.0, 0.0), tide=WEIR_POND)
    spill = concrete(95, damp=6.0, streak=.5, moss=.6, blot=.6, north=(1.0, 0.0), k=.88)
    slope = V3(2.15, 0, S)
    H = float(np.linalg.norm(slope))
    nface = unit(V3(-S, 0, 2.15))
    for s in (-1, 1):                                               # the wings
        y0, y1 = (15.5, 28.0) if s > 0 else (-28.0, -15.5)
        sheet(p, (-4.0, y1, 0), -Y, slope, 12.5, H, 0, CONCRETE, ju=(6.25,), jv=np.arange(1.5, H, 1.5), back=False, rim='',
              ties=(1.25, .75, .018), fn=conc)
        sheet(p, (1.85, y0, 0), Y, Z, 12.5, S, 0, CONCRETE, ju=(6.25,), jv=np.arange(1.5, S, 1.5), back=False, rim='', fn=wet)
        m = mark(p)
        ye = y1 if s > 0 else y0
        gface(p, (-4.0, ye, 0), (1.85, ye, 0), (1.85, ye, S), (-1.85, ye, S), CONCRETE, 1.5, s * Y)
        paint(p, m, conc)
    deck = concrete(94, ground=D - 6, moss=.3, blot=.5, ledges=((D, .3),))
    sheet(p, (-2, -28, D), X, Y, 4, 56, D - S, CONCRETE, jv=sorted(28 + y for ab in WEIR_PIERS for y in ab), sub=1.34, groove=(.02, .01), arris=.02, fn=deck)
    for k, (ya, yb) in enumerate(WEIR_PIERS):
        _weir_pier(p, ya, yb, conc, wet, k > 0, k < 3)
    hoist = galv(93, .35)
    for k, yc in enumerate(WEIR_BAYS):
        _weir_bay(p, rng, yc, spill)
        _weir_hoist(p, yc, max(yc - 4.0, -12.45), min(yc + 4.0, 12.45), steel(93 + k, JUST_OLIVE, .3, ground=D - 1))
        m = mark(p)                                                  # deck beams under the slab, on bearing shelves
        for x in (-1.5, 1.5):
            gbox(p, (x - .2, yc - 3.5, S - .7), (x + .2, yc + 3.5, S), CONCRETE, 1.2, .02, 'Z')
            for y in (yc - 3.5, yc + 3.5):
                gbox(p, (x - .3, y - .12 if y > yc else y, S - 1.0), (x + .3, y if y > yc else y + .12, S - .7), CONCRETE, 9, .02)
        paint(p, m, deck)
        m = mark(p)                                                  # the plate the hand-wheel stand bolts to
        gbox(p, (.5, yc - 1.2, D), (1.9, yc + 1.2, D + .008), STEEL, .7, .003, 'z')
        bolts(p, [(x, yc + sy * 1.1, D + .008) for x in (.6, 1.8) for sy in (-1, 1)], Z, .014, STEEL, washer=False)
        paint(p, m, steel(101, STEEL_GREY, .3, ground=D - 3))
    lamps = []
    for s in (-1, 1):
        _weir_tower(p, s, rng, lamps)
    # guard rails: the downstream edge from end to end, the upstream edge between and beyond the towers
    m = mark(p)
    handrail(p, [(-1.93, y, D) for y in np.linspace(-28, 28, 9)], STEEL, 1.1, 1.5, .12, inward=X)
    for a, b in ((-28.0, -15.5), (-12.5, 12.5), (15.5, 28.0)):
        handrail(p, [(1.93, y, D) for y in np.linspace(a, b, max(2, int(round((b - a) / 6.25)) + 1))], STEEL, 1.1, 1.5, .12, inward=-X)
    paint(p, m, steel(102, STEEL_GREY, .3, ground=D, damp=.8))
    # scuppers through the downstream fascia and what they leave on the face below
    for y in np.arange(-26.5, 27, 3.5):
        if any(a - .4 < y < b + .4 for a, b in WEIR_PIERS):
            continue
        m = mark(p)
        pipe(p, [(-1.95, y, D - .26), (-2.14, y, D - .3)], .04, RUST, 10)
        paint(p, m, rusty(103))
        if abs(y) > 15.5:
            zt = 10.4
            streaks(p, rng, [V3(-4.0 + 2.15 * zt / S, y, zt) + nface * .0], nface, (1.5, 4.0), (.12, .25), MOSS_DEEP, MOSS)
    # moss in the lift joints and at the feet, weeds on the ledges
    for s in (-1, 1):
        y0, y1 = (15.5, 28.0) if s > 0 else (-28.0, -15.5)
        down = -unit(slope)
        for zj in (1.5, 3.0, 6.0, 9.0):
            t = zj / S
            a, b = sorted(rng.uniform(y0 + .3, y1 - .3, 2))
            moss_line(p, rng, V3(-4.0 + 2.15 * t, a, zj), V3(-4.0 + 2.15 * t, b, zj), down, .1, .03)
        moss_line(p, rng, (-4.0, y1, 0), (-4.0, y0, 0), -X, .06, .03, climb=.5, wall=slope)
        for _ in range(3):
            zj = float(rng.choice((3.0, 4.5, 6.0, 7.5)))
            q = V3(-4.0 + 2.15 * zj / S, rng.uniform(y0 + .5, y1 - .5), zj) + nface * .02
            sprig(p, rng, q, rng.uniform(.5, 1.1), 7, (LEAF_GREEN, LEAF_GOLD), BARK_BIRCH if rng.uniform() < .5 else BARK_BROWN)
            tuft(p, rng, q + Y * rng.uniform(-.8, .8), .35, .4)
    for ya, yb in WEIR_PIERS:
        for _ in range(3):
            moss_patch(p, rng, (rng.uniform(2.2, 3.0), rng.uniform(ya + .2, yb - .2), D), rng.uniform(.08, .2))
        x = rng.uniform(-3.2, -2.3)
        tuft(p, rng, (x, rng.uniform(ya + .3, yb - .3), S + (x + 2) * 1.05), .4, .45)
    for yc in WEIR_BAYS:
        for _ in range(3):
            tuft(p, rng, (rng.uniform(-3.9, -3.5), yc + rng.uniform(-3.2, 3.2), 1.0), .45, .5, colours=(GRASS, LEAF_LIGHT))
    for _ in range(26):
        moss_patch(p, rng, (rng.choice((-1.8, 1.8)) + rng.uniform(-.12, .12), rng.uniform(-27.5, 27.5), D), rng.uniform(.06, .16), .018)
    return done(p, facts=dict(
        deck=dict(x=(-2.0, 2.0), y=(-28.0, 28.0), z=D, rails_x=(-1.93, 1.93), ends_open=True),
        towers=[dict(x=(0.0, 3.2), y=(s * 12.5, s * 15.5), roof_z=17.0, door=(0.0, s * 14.0, D), free_x=(-1.9, 0.0)) for s in (-1, 1)],
        bays=[dict(y=(yc - 3.5, yc + 3.5), gate_x=2.4, gate_z=(WEIR_SILL, 11.0), wheel_pad=(1.2, yc, D), drive_shaft=(1.98, yc, D + .5)) for yc in WEIR_BAYS],
        piers_y=WEIR_PIERS, upstream='+x', pond_level=WEIR_POND, sill_z=WEIR_SILL, toe_x=-4.0, lamps=lamps))


@mesh('SM_GN_SluiceWheel', (1.2, 2.2, 2.4))
def sluice_wheel():
    """A manual sluice-gate actuator: a hand-wheel 2 m across (signal orange, facing +x) on a worm-gear housing on a
    fabricated pedestal bolted down through a base plate; behind, a vertical shaft drops to a bevel box whose output
    stub leaves at the back (-x) 0.5 m above the floor, with a coupling flange."""
    p = Part('SM_GN_SluiceWheel', (STEEL, PAINT, BRASS))
    oli, ora, st = olive(111, .28), orange(112, .25), galv(113, .4)
    zc = 1.3
    m = mark(p)
    gbox(p, (-.45, -.4, 0), (.45, .4, .03), STEEL, 9, .006, 'z')
    bolts(p, [(sx * .37, sy * .32, .03) for sx in (-1, 1) for sy in (-1, 1)], Z, .022, STEEL, h=.035)
    pipe(p, [(-.3, 0, .64), (-.3, 0, .97)], .03, STEEL, 12)
    pipe(p, [(-.42, 0, .5), (-.6, 0, .5)], .035, STEEL, 12)
    turn(p, [(.035, 0), (.085, 0), (.085, .022), (.035, .022)], STEEL, 16, (-.585, 0, .5), X)
    pipe(p, [(.3, 0, zc), (.5, 0, zc)], .04, STEEL, 12)
    paint(p, m, st)
    m = mark(p)
    gbox(p, (-.15, -.17, .03), (.2, .17, .95), PAINT, .5, .02, 'z')
    for sy in (-1, 1):
        plate(p, [(0, sy * .17, .03), (0, sy * .36, .03), (0, sy * .17, .4)], .012, PAINT)
    for sx, x in ((-1, -.15), (1, .2)):
        plate(p, [(x, 0, .03), (x + sx * .22, 0, .03), (x, 0, .4)], .012, PAINT)
    gbox(p, (-.22, -.3, .95), (.3, .3, zc), PAINT, .5, .025, 'Z')
    turn(p, [(.02, 0), (.3, 0), (.3, .52), (.02, .52)], PAINT, 28, (-.22, 0, zc), X)
    turn(p, [(.25, 0), (.25, .03), (.16, .03), (.16, .1), (.02, .1)], PAINT, 24, (.3, 0, zc), X)
    bolts(p, [(.33, .21 * math.cos(a), zc + .21 * math.sin(a)) for a in np.linspace(0, TAU, 8, endpoint=False)], X, .016, PAINT)
    gbox(p, (-.42, -.14, .36), (-.18, .14, .64), PAINT, 9, .02)
    bolts(p, [(-.3 + sx * .08, sy * .1, .64) for sx in (-1, 1) for sy in (-1, 1)], Z, .012, PAINT)
    paint(p, m, oli)
    m = mark(p)
    turn(p, [(.07, 0), (.07, .05), (.02, .05)], BRASS, 16, (.04, 0, zc + .3))
    turn(p, [(.03, 0), (.03, .07), (.02, .08)], BRASS, 10, (-.1, .15, zc + .26))
    paint(p, m, steel(114, BRASS_WARM, 0.0, grime=.35))
    m = mark(p)
    hoop(p, (.44, 0, zc), 1.0, .034, PAINT, X, 48, 10)
    turn(p, [(.04, 0), (.12, 0), (.12, .16), (.04, .16)], PAINT, 20, (.36, 0, zc), X)
    for a in np.radians(np.arange(0, 360, 60) + 30):
        d = V3(0, math.cos(a), math.sin(a))
        pipe(p, [V3(.44, 0, zc) + d * .11, V3(.44, 0, zc) + d * .99], .024, PAINT, 10)
    q = V3(.44, 0, zc) + V3(0, math.cos(math.radians(30)), math.sin(math.radians(30)))
    pipe(p, [q, q + X * .15], .028, PAINT, 12)
    paint(p, m, ora)
    return done(p, facts=dict(wheel_centre=(.44, 0, zc), wheel_radius=1.0, front='+x', output_shaft=(-.6, 0, .5)))


@mesh('SM_GN_RelayTower', (9.0, 9.0, 30.0))
def relay_tower():
    """The relay: a lattice mast on a plinth. A raft 9 x 9 m; an equipment house 6.4 m square with a steel door (+x),
    louvres and a caged ladder (-x); its roof is the deck, 7 x 7 m at z 6.0, guard-railed all round but for the
    ladder's gap (-x, y -0.45 to 0.45). From the deck a square mast of bolted angles tapers from 3 m at its base plates
    to 1 m at z 26 and stands on to 28.2, with a caged ladder up its -x face, four dishes, two cross-arms hung with
    insulator strings and conductor stubs, and at the top an amber beacon (light at (0, 0, 28.8)) and a rod to z 30."""
    rng = np.random.default_rng(2620)
    p = Part('SM_GN_RelayTower', (CONCRETE, STEEL, PAINT, TILE, RUST, MOSS, GLOW))
    DK, W, H0, H1 = 6.0, 3.2, .4, 5.7
    conc = concrete(121, damp=2.0, ledges=((H1, 1.0),), moss=.35)
    gal = steel(122, STEEL_GREY, .3, ground=DK, damp=1.0)
    low = steel(123, STEEL_GREY, .32, ground=H0)
    gra = graphite(124)
    m = mark(p)
    gbox(p, (-4.5, -4.5, 0), (4.5, 4.5, H0), CONCRETE, 1.0, .04, 'z')
    paint(p, m, conc)
    walls = ((V3(W, -W, H0), Y, [(2.65, 3.75, 0, 2.15)]), (V3(-W, W, H0), -Y, []), (V3(W, W, H0), -X, [(2.2, 3.4, 2.6, 3.3)]),
             (V3(-W, -W, H0), X, [(2.2, 3.4, 2.6, 3.3)]))
    for k, (o, u, holes) in enumerate(walls):
        sheet(p, o, u, Z, 2 * W, H1 - H0, .3, CONCRETE, holes=holes, ju=(W,), jv=(1.5, 3.0, 4.5), back=False, rim='', ties=(1.07, .75, .018), fn=conc)
        f = np.cross(u, Z)
        if k == 0:
            steel_door(p, o + u * 2.72 - f * .12, u, .96, 2.08, bone(125, .16), gra)
            m = mark(p)
            gbox(p, (W, -.85, H0 + 2.3), (W + .55, .85, H0 + 2.38), STEEL, .6, .01)
            for y in (-.75, .75):
                plate(p, [(W, y, H0 + 2.3), (W + .5, y, H0 + 2.3), (W, y, H0 + 1.95)], .01, STEEL)
            paint(p, m, low)
        elif holes:
            louvre(p, o + u * 2.2 + Z * 2.6 - f * .16, u, 1.2, .7, low, STEEL, 7)
    deck = concrete(126, ground=DK - 6, moss=.3, blot=.5)
    sheet(p, (-3.5, -3.5, DK), X, Y, 7, 7, DK - H1, CONCRETE, ju=(3.5,), jv=(3.5,), sub=1.2, groove=(.015, .008), arris=.02, fn=deck)
    m = mark(p)
    R = 3.43
    handrail(p, [(-R, -.45, DK), (-R, -R, DK), (R, -R, DK), (R, R, DK), (-R, R, DK), (-R, .45, DK)], STEEL, 1.1, 1.4, .12)
    paint(p, m, gal)
    m = mark(p)
    ladder(p, (-W, 0, H0), DK - H0, -X, STEEL, standoff=.45)
    paint(p, m, low)
    # the mast
    levels = [6.0, 9.0, 12.0, 15.0, 18.0, 20.5, 23.0, 24.8, 26.0, 27.1, 28.2]

    def half(z):
        return 1.5 - (z - 6) / 20 if z < 26 else .5
    corners = ((1, 1), (-1, 1), (-1, -1), (1, -1))
    m = mark(p)
    for za, zb in zip(levels, levels[1:]):
        ha, hb = half(za), half(zb)
        size = .16 if za < 18 else .12
        for sx, sy in corners:
            angle(p, (sx * ha, sy * ha, za), (sx * hb, sy * hb, zb), size, STEEL, (-sx, 0, 0), (0, -sy, 0))
        for k in range(4):
            (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
            n = unit(V3(ax + bx, ay + by, 0))
            A0, B0, A1, B1 = V3(ax * ha, ay * ha, za), V3(bx * ha, by * ha, za), V3(ax * hb, ay * hb, zb), V3(bx * hb, by * hb, zb)
            for a, b, off in ((A0, B1, .012), (B0, A1, -.012)):
                d = unit(b - a)
                angle(p, a + n * off + d * .12, b + n * off - d * .12, .07 if za < 18 else .055, STEEL, np.cross(n, d), -n)
    for z in levels:
        h = half(z)
        for k in range(4):
            (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
            n = unit(V3(ax + bx, ay + by, 0))
            A, B = V3(ax * h, ay * h, z), V3(bx * h, by * h, z)
            angle(p, A, B, .08, STEEL, -Z, -n)
            for a, t in ((A, unit(B - A)), (B, unit(A - B))):                 # gusset plates where the bracing meets a leg
                g = min(.34, h * .5)
                plate(p, [a + n * .014 + t * q[0] + Z * q[1] for q in ((0, -.2), (g, -.2), (g, .04), (.12, .28), (0, .28))], .01, STEEL)
                bolts(p, [a + n * .019 + t * q[0] + Z * q[1] for q in ((.06, -.12), (.06, .16), (g - .07, -.1))], n, .012, STEEL, washer=False)
    for z in (12.0, 18.0, 23.0):                                             # plan bracing
        h = half(z)
        bar(p, (-h, -h, z - .02), (h, h, z - .02), .06, .008, STEEL)
        bar(p, (-h, h, z - .04), (h, -h, z - .04), .06, .008, STEEL)
    for sx, sy in corners:                                                   # base plates on anchor bolts
        gbox(p, (sx * 1.5 - .3, sy * 1.5 - .3, DK), (sx * 1.5 + .3, sy * 1.5 + .3, DK + .03), STEEL, 9, .006, 'z')
        bolts(p, [(sx * 1.5 + qx * .22, sy * 1.5 + qy * .22, DK + .03) for qx in (-1, 1) for qy in (-1, 1)], Z, .024, STEEL, h=.04)
        plate(p, [(sx * 1.5, sy * (1.5 - .02), DK + .03), (sx * (1.5 - .26), sy * (1.5 - .02), DK + .03), (sx * 1.5, sy * (1.5 - .02), DK + .32)], .012, STEEL)
        plate(p, [(sx * (1.5 - .02), sy * 1.5, DK + .03), (sx * (1.5 - .02), sy * (1.5 - .26), DK + .03), (sx * (1.5 - .02), sy * 1.5, DK + .32)], .012, STEEL)
    for z in (15.0, 23.0):                                                   # rest platforms inside the mast
        h = half(z) - .1
        gbox(p, (-h + .5, -h, z), (h, h, z + .008), STEEL, .6, .002)
    gbox(p, (-.62, -.62, 28.2), (.62, .62, 28.24), STEEL, 9, .006)
    pipe(p, [(0, 0, 28.24), (0, 0, 28.62)], .05, STEEL, 10)
    for a in np.radians((0, 60, 120)):
        d = V3(math.cos(a), math.sin(a), 0)
        pipe(p, arc_pts((0, 0, 28.8), .2, 0, 180, d, Z, 9), .008, STEEL, 4, cap=False)
        pipe(p, arc_pts((0, 0, 28.8), .2, 0, -180, d, Z, 9), .008, STEEL, 4, cap=False)
    pipe(p, [(.4, .4, 28.24), (.4, .4, 30.0)], .012, STEEL, 6)
    for sx, sy in ((1, 1), (-1, -1)):                                        # feeder cables down two legs
        pipe(p, [(sx * (half(z) - .1), sy * (half(z) - .05), z) for z in (26.0, 20.5, 15.0, 9.0, 6.02)], .025, STEEL, 6)
    paint(p, m, gal)
    m = mark(p)
    ladder(p, (0, 0, 0), 20.0, -X, STEEL, standoff=.25)
    place(p, m, rot('y', math.degrees(math.atan(1 / 20))), (-1.52, 0, DK))
    paint(p, m, gal)
    fl.ball(p, (0, 0, 28.8), .16, tone(GLOW_AMBER, 1.0), GLOW, 14)
    # dishes on pipe mounts
    for (z, face_n, aim, r, depth, drum) in ((16.5, X, V3(1, 0, 0), 1.1, .36, False), (19.2, Y, V3(-.3, 1, 0), .9, .3, False),
                                             (22.0, -Y, V3(.2, -1, 0), .6, .2, True), (24.2, X, V3(1, .4, 0), .55, .2, True)):
        h = half(z)
        aim = unit(aim)
        base = face_n * h + Z * z
        c = base + face_n * .5
        m = mark(p)
        t = np.cross(Z, face_n)
        pipe(p, [base + t * h * .9 + Z * .5, base + t * h * .9 - Z * .5], .045, STEEL, 10)
        pipe(p, [base - t * h * .9 + Z * .5, base - t * h * .9 - Z * .5], .045, STEEL, 10)
        for dz in (-.35, .35):
            pipe(p, [base - t * h * .9 + Z * dz, base + t * h * .9 + Z * dz], .035, STEEL, 8)
            pipe(p, [base + Z * dz, c + Z * dz * .3], .03, STEEL, 8)
        turn(p, [(.1, -.12), (.1, .02), (.02, .02)], STEEL, 12, c, aim)
        paint(p, m, gal)
        dish(p, c, aim, r, depth, bone(127, .14), gal, feed=not drum)
        if drum:                                                             # a shrouded dish under a flat radome
            m = mark(p)
            turn(p, [(r + .025, depth), (r + .025, depth + .28), (.02, depth + .3)], PAINT, 24, c, aim)
            paint(p, m, bone(128, .1))
    # cross-arms, insulator strings, what is left of the conductors
    for z, tip in ((20.5, 4.25), (24.8, 3.4)):
        h = half(z)
        for s in (-1, 1):
            m = mark(p)
            for x0 in (-h * .7, h * .7):
                A, B, C, D = V3(x0, s * h, z - .4), V3(0, s * tip, z - .07), V3(0, s * tip, z + .07), V3(x0, s * h, z + .4)
                plate(p, [A, B, C, D], .012, STEEL)
                nrm = unit(np.cross(B - A, D - A))
                bar(p, A, B, .09, .012, STEEL, np.cross(unit(B - A), nrm))
                bar(p, D, C, .09, .012, STEEL, np.cross(unit(C - D), nrm))
            for q in (.3, .6):
                yy = s * (h + (tip - h) * q)
                bar(p, (-h * .7 * (1 - q), yy, z), (h * .7 * (1 - q), yy, z), .06, .01, STEEL)
            gbox(p, (-.05, s * tip - .06, z - .2), (.05, s * tip + .06, z + .09), STEEL, 9, .008)
            paint(p, m, gal)
            insulator(p, (0, s * tip, z - .2), -Z, .13, 8, .15, sides=14)
            m = mark(p)
            e = V3(0, s * tip, z - 1.4)
            gbox(p, e - V3(.12, .05, .1), e + V3(.12, .05, 0), STEEL, 9, .008)
            run = [e + V3(.1, 0, -.05), e + V3(.9, 0, -.12), e + V3(1.9, 0, -.32), e + V3(2.5, 0, -1.0), e + V3(2.62, 0, -2.4)]
            cut = [e + V3(-.1, 0, -.05), e + V3(-1.2, 0, -.12), e + V3(-2.4, 0, -.34), e + V3(-3.5, 0, -.72), e + V3(-4.35, 0, -1.2)]
            pipe(p, catmull(run if s > 0 else [q * V3(-1, 1, 1) for q in run], 4), .016, STEEL, 6)
            pipe(p, catmull(cut if s > 0 else [q * V3(-1, 1, 1) for q in cut], 4), .016, STEEL, 6)
            paint(p, m, steel(129, STEEL_DARK, .2))
    # two equipment cabinets on the deck
    for k, (x0, x1) in enumerate(((1.9, 2.55), (2.6, 3.25))):
        m = mark(p)
        gbox(p, (x0, 2.35, DK), (x1, 3.1, DK + .1), STEEL, 9, .01, 'z')
        paint(p, m, gal)
        m = mark(p)
        gbox(p, (x0 + .02, 2.38, DK + .1), (x1 - .02, 3.08, DK + 1.55), PAINT, .5, .012, 'z')
        gbox(p, (x0 + .06, 2.36, DK + .16), (x1 - .06, 2.38, DK + 1.5), PAINT, .5, .006, 'Y')
        gbox(p, (x0 - .01, 2.33, DK + 1.55), (x1 + .01, 3.11, DK + 1.6), PAINT, 9, .01)
        paint(p, m, bone(130 + k, .14))
        m = mark(p)
        pipe(p, [(x1 - .12, 2.35, DK + .85), (x1 - .12, 2.33, DK + .85), (x1 - .12, 2.33, DK + .98)], .01, STEEL, 6)
        paint(p, m, gra)
    m = mark(p)
    conduit(p, [(1.95, 3.14, DK + .25), (1.6, 3.14, DK + .25), (1.6, 1.62, DK + .25)], Y, STEEL, .02, .6)
    paint(p, m, gal)
    for a, b, out in (((4.5, -4.5, 0), (4.5, 4.5, 0), X), ((-4.5, 4.5, 0), (-4.5, -4.5, 0), -X), ((4.5, 4.5, 0), (-4.5, 4.5, 0), Y), ((-4.5, -4.5, 0), (4.5, -4.5, 0), -Y)):
        moss_line(p, rng, a, b, out, .05, .025, climb=.2)
    for a, b, out in (((W, -W, H0), (W, -.6, H0), X), ((W, .6, H0), (W, W, H0), X), ((-W, W, H0), (-W, .5, H0), -X), ((W, W, H0), (-W, W, H0), Y),
                      ((-W, -W, H0), (W, -W, H0), -Y)):
        moss_line(p, rng, a, b, out, .1, .025, climb=.3)
    for _ in range(12):
        q = rng.uniform(-4.3, 4.3, 2)
        if max(abs(q)) > W + .15:
            moss_patch(p, rng, (q[0], q[1], H0), rng.uniform(.08, .2))
    for _ in range(10):
        q = rng.uniform(-3.3, 3.3, 2)
        if max(abs(q)) > 2.0 and not (q[0] > 1.7 and q[1] > 2.2):
            moss_patch(p, rng, (q[0], q[1], DK), rng.uniform(.06, .15), .016)
    streaks(p, rng, [(W, rng.uniform(-3, 3), H1 - .02) for _ in range(4)], X, (.5, 1.4), (.05, .1), RUST_DARK, RUST)
    streaks(p, rng, [(rng.uniform(-3, 3), -W, H1 - .02) for _ in range(4)], -Y, (.5, 1.4), (.05, .1), RUST_DARK, RUST)
    return done(p, facts=dict(deck=dict(z=DK, x=(-3.5, 3.5), y=(-3.5, 3.5), rails=3.43, gap=dict(side='-x', y=(-.45, .45))),
                              mast_legs=1.5, mast_base_plates=1.8, mast_ladder=dict(x=(-2.5, -1.5), y=(-.45, .45)),
                              cabinets=dict(x=(1.9, 3.25), y=(2.33, 3.11), top=DK + 1.6),
                              clear='the ring between the mast (out to 1.8) and the rails (3.43): 1.6 m wide, less the mast ladder and the cabinets',
                              beacon=(0, 0, 28.8), top=30.0, door='+x at ground', plinth_ladder='-x'))


@mesh('SM_GN_Capacitor', (2.4, 1.6, 2.6))
def capacitor():
    """A capacitor bank on a skid: an open graphite rack of twenty bone-white cans in two tiers, each with two ceramic
    bushings joined by copper bus bars; risers at the -x end up to the main bars, which ride on three post insulators
    along the top and end in terminal lugs at z 2.6; at the front (+x) the control cabinet: a door with the orange
    stripe, a plain hazard triangle, a louvre and an amber lamp."""
    p = Part('SM_GN_Capacitor', (STEEL, PAINT, BRASS, TILE, GLOW))
    gra, cu = graphite(141, .2), copper(142, .25)
    m = mark(p)
    for y in (-.62, .62):
        channel(p, (-1.2, y, .06), (1.2, y, .06), .12, .06, STEEL, Z, 1 if y < 0 else -1)
    for x in (-1.1, -.25, .6, 1.12):
        bar(p, (x, -.62, .09), (x, .62, .09), .08, .06, STEEL)
    for x in (-1.15, -.3, .55):
        for sy in (-1, 1):
            angle(p, (x, sy * .72, .12), (x, sy * .72, 1.9), .06, STEEL, (1 if x < 0 else -1, 0, 0), (0, -sy, 0))
    for z in (.2, 1.02, 1.9):
        for sy in (-1, 1):
            angle(p, (-1.15, sy * .72, z), (.55, sy * .72, z), .05, STEEL, (0, -sy, 0), (0, 0, -1))
        for x in (-1.15, -.3, .55):
            bar(p, (x, -.72, z - .02), (x, .72, z - .02), .05, .04, STEEL)
    for sy in (-1, 1):
        for z in (.62, 1.45):
            bar(p, (-1.15, sy * .74, z), (.55, sy * .74, z), .04, .006, STEEL, Y)
    paint(p, m, gra)
    for z0 in (.2, 1.02):
        for sy in (-1, 1):
            for i in range(5):
                x = -1.0 + i * .33
                m = mark(p)
                gbox(p, (x - .125, sy * .36 - .17, z0), (x + .125, sy * .36 + .17, z0 + .5), PAINT, .4, .015)
                gbox(p, (x - .135, sy * .36 - .18, z0 + .2), (x + .135, sy * .36 + .18, z0 + .23), PAINT, 9, .004)
                paint(p, m, bone(143 + i, .12))
                for dy in (-.08, .08):
                    insulator(p, (x, sy * .36 + dy, z0 + .5), Z, .034, 2, .05, sides=10)
            m = mark(p)
            for dy in (-.08, .08):
                y = sy * .36 + dy
                bar(p, (-1.1, y, z0 + .615), (.42, y, z0 + .615), .03, .008, BRASS)
                bolts(p, [(-1.0 + i * .33, y, z0 + .619) for i in range(5)], Z, .009, BRASS, washer=False)
            paint(p, m, cu)
    m = mark(p)
    for y in (-.44, -.28, .28, .44):
        bar(p, (-1.1, y, .8), (-1.1, y, 2.0), .03, .008, BRASS, X)
    bar(p, (-1.1, -.46, 2.0), (-1.1, .46, 2.0), .008, .04, BRASS, Z)
    bar(p, (-1.1, 0, 2.0), (-1.1, 0, 2.31), .06, .01, BRASS, X)
    for y in (-.05, .05):
        bar(p, (-1.12, y, 2.3), (.5, y, 2.3), .012, .07, BRASS, Z)
        bar(p, (.45, y, 2.3), (.45, y, 2.58), .012, .07, BRASS, X)
        bolts(p, [(.45, y + (.006 if y > 0 else -.006), 2.52)], Y if y > 0 else -Y, .014, BRASS, washer=False)
    paint(p, m, cu)
    for x in (-.9, -.3, .3):
        insulator(p, (x, 0, 1.9), Z, .075, 4, .09, sides=14)
        m = mark(p)
        gbox(p, (x - .1, -.1, 1.88), (x + .1, .1, 1.9), STEEL, 9, .004)
        gbox(p, (x - .04, -.09, 2.26), (x + .04, .09, 2.34), STEEL, 9, .006)
        paint(p, m, gra)
    m = mark(p)
    gbox(p, (.6, -.6, .12), (1.18, .6, 1.95), PAINT, .5, .012, 'z')
    gbox(p, (.58, -.63, 1.95), (1.2, .63, 1.99), PAINT, 9, .008)
    gbox(p, (1.18, -.52, .2), (1.195, .52, 1.87), PAINT, .5, .006, 'x')
    paint(p, m, bone(150, .14))
    m = mark(p)
    gbox(p, (1.195, -.5, 1.62), (1.198, .5, 1.72), PAINT, 9, .001, 'x')
    plate(p, [(1.197, -.12, .95), (1.197, .12, .95), (1.197, 0, 1.16)], .004, PAINT)
    paint(p, m, orange(151))
    louvre(p, (1.195, -.35, .3), Y, .7, .25, gra, STEEL, 5, .03)
    m = mark(p)
    pipe(p, [(1.195, .42, .95), (1.23, .42, .95), (1.23, .42, 1.15), (1.195, .42, 1.15)], .008, STEEL, 6)
    for z in (.45, 1.6):
        turn(p, [(.012, -.05), (.012, .05)], STEEL, 8, (1.2, -.52, z))
    turn(p, [(.05, 0), (.05, .015), (.036, .015)], STEEL, 12, (1.195, .38, 1.45), X)
    paint(p, m, gra)
    fl.disc(p, (1.212, .38, 1.45), X, .034, tone(GLOW_AMBER, 1.0), GLOW, 10, dome=.01, rim=tone(GLOW_AMBER, .6))
    age(p, (0, 0), 152, reach=.5, floor=.75, grime=.12, streak=.08)
    return done(p, facts=dict(front='+x', lamp=(1.22, .38, 1.45), terminals=[(.45, -.05, 2.58), (.45, .05, 2.58)]))


@mesh('SM_GN_Mast', (3.0, 3.0, 16.0))
def ropeway_mast():
    """A ropeway gantry mast: an A-frame of two H-section legs across y, stayed by two more along x, on four concrete
    footings; ties and bracing between the legs; a work platform at z 13.3 reached by a caged ladder; and at the head
    a sheave 1.6 m across (axis y, centre z 15.0) between cheek plates, under a guard hoop, with what is left of the
    haul rope: one end cut short toward -x, the other hanging frayed on the +x side."""
    rng = np.random.default_rng(2622)
    p = Part('SM_GN_Mast', (CONCRETE, STEEL, PAINT, RUST, MOSS))
    conc = concrete(161, damp=.8, moss=.4)
    gra = graphite(162, .22)
    HEAD, Z0 = 14.2, .48
    feet = ((0, -1.2), (1.2, 0), (0, 1.2), (-1.2, 0))
    m = mark(p)
    for x, y in feet:
        gbox(p, (x - .3, y - .3, 0), (x + .3, y + .3, .45), CONCRETE, .5, .03, 'z')
    paint(p, m, conc)

    def leg(k, z):
        x, y = feet[k]
        t = (z - Z0) / (HEAD - Z0)
        return V3(x * (1 - .75 * t), y * (1 - .75 * t), z)
    m = mark(p)
    for k, (x, y) in enumerate(feet):
        ibeam(p, leg(k, Z0), leg(k, HEAD), .2, .16, STEEL, X if x == 0 else Y)
        gbox(p, (x - .22, y - .22, .45), (x + .22, y + .22, Z0), STEEL, 9, .006, 'z')
        bolts(p, [(x + sx * .16, y + sy * .16, Z0) for sx in (-1, 1) for sy in (-1, 1)], Z, .02, STEEL, h=.035)
    levels = (Z0 + .2, 3.6, 7.0, 10.4, 13.2)
    for i, z in enumerate(levels):
        for k in range(4):
            a, b = leg(k, z), leg((k + 1) % 4, z)
            if i:
                angle(p, a, b, .07, STEEL, -Z, unit(-(a + b) * V3(1, 1, 0)))
            if i < len(levels) - 1:
                c = leg((k + 1) % 4, levels[i + 1]) if (i + k) % 2 else leg(k, levels[i + 1])
                s = b if (i + k) % 2 == 0 else a
                n = unit((a + b) * V3(1, 1, 0))
                bar(p, (s if (i + k) % 2 == 0 else a) + n * .0, c, .06, .008, STEEL, n)
    # the head: a cap plate, cheeks, axle, sheave, guard
    gbox(p, (-.5, -.45, HEAD), (.5, .45, HEAD + .04), STEEL, 9, .008)
    for sy in (-1, 1):
        plate(p, [(-.35, sy * .22, HEAD + .04), (.35, sy * .22, HEAD + .04), (.13, sy * .22, 15.16), (-.13, sy * .22, 15.16)], .025, STEEL)
        turn(p, [(.05, 0), (.11, 0), (.11, .05), (.05, .05)], STEEL, 16, (0, sy * .235, 15.0), sy * Y)
        for sx in (-1, 1):
            plate(p, [(sx * .3, sy * .22, HEAD + .04), (sx * .3, sy * .42, HEAD + .04), (sx * .3, sy * .22, HEAD + .4)], .012, STEEL)
    pipe(p, [(0, -.32, 15.0), (0, .32, 15.0)], .05, STEEL, 12)
    hoop(p, (0, 0, 15.0), .74, .05, STEEL, Y, 48, 8)
    for sy in (-1, 1):
        disc(p, (0, sy * .055, 15.0), .84, STEEL, sy * Y, 48, r_in=.66)
        disc(p, (0, sy * .045, 15.0), .84, STEEL, -sy * Y, 48, r_in=.66)
    turn(p, [(.05, -.09), (.13, -.09), (.13, .09), (.05, .09)], STEEL, 16, (0, 0, 15.0), Y)
    for a in np.radians(np.arange(0, 360, 60)):
        d = V3(math.cos(a), 0, math.sin(a))
        bar(p, V3(0, 0, 15.0) + d * .12, V3(0, 0, 15.0) + d * .7, .09, .02, STEEL, Y)
    for sy in (-1, 1):
        arc = arc_pts((0, sy * .12, 15.0), .95, 50, 130, X, Z, 9)
        pipe(p, [V3(.36, sy * .12, HEAD + .04)] + list(arc) + [V3(-.36, sy * .12, HEAD + .04)], .016, STEEL, 6)
    # the work platform and its access
    PZ = 13.3
    gbox(p, (-.9, -.75, PZ - .04), (.9, .75, PZ), STEEL, .6, .004)
    for y in (-.7, .7):
        channel(p, (-.9, y, PZ - .11), (.9, y, PZ - .11), .14, .05, STEEL, Z, 1 if y < 0 else -1)
    handrail(p, [(-.87, -.2, PZ), (-.87, .72, PZ), (.87, .72, PZ), (.87, -.72, PZ), (-.87, -.72, PZ)], STEEL, 1.05, 1.0, .1, base=False)
    paint(p, m, gra)
    m = mark(p)
    ladder(p, (-.9, -.47, 0), PZ, -X, STEEL, width=.42, standoff=.2)
    for z in (3.6, 7.0, 10.4):
        q = leg(3, z)
        bar(p, (-1.1, -.26, z), q, .04, .04, STEEL)
    paint(p, m, galv(163, .3))
    m = mark(p)                                                      # the signal band on the two A-legs
    for k in (0, 2):
        ibeam(p, leg(k, 2.0), leg(k, 2.5), .206, .166, PAINT, X)
    paint(p, m, orange(164, .2))
    m = mark(p)
    top = list(arc_pts((0, 0, 15.0), .8, 105, 75, X, Z, 5))
    cut = [V3(-1.45, 0, 15.44)] + top
    pipe(p, cut, .022, RUST, 8)
    hang = catmull(top[-1:] + [V3(.8, 0, 15.6), V3(1.2, 0, 15.42), V3(1.4, 0, 14.9), V3(1.44, 0, 13.7)], 5)
    pipe(p, hang, .022, RUST, 8)
    for k in range(5):                                               # the frayed end
        e = hang[-1]
        pipe(p, [e, e + V3(rng.normal(0, .03), rng.normal(0, .03), -.12), e + V3(rng.normal(0, .07), rng.normal(0, .07), -.3)], .006, RUST, 4)
    paint(p, m, steel(165, STEEL_DARK, .5, ground=-9))
    for x, y in feet:
        moss_patch(p, rng, (x + rng.uniform(-.15, .15), y + rng.uniform(-.15, .15), .45), .1)
        d = unit(V3(x, y, 0))
        t = np.cross(Z, d)
        moss_line(p, rng, V3(x, y, 0) + d * .3 - t * .3, V3(x, y, 0) + d * .3 + t * .3, d, .05, .025, climb=.15)
    return done(p, facts=dict(sheave=dict(centre=(0, 0, 15.0), radius=.8, axis='y'), rope_line_z=15.8, rope_runs='along x',
                              platform=dict(z=PZ, x=(-.9, .9), y=(-.75, .75)), feet=feet, top=16.0))


@mesh('SM_GN_TreePlatform', (12.0, 12.0, 0), pivot='any')
def tree_platform():
    """A timber deck round a great trunk; pivot at the deck's top (z 0), centred on the trunk. Sixteen sectors of
    tangential boards between an inner apothem of 3.0 m and an outer of 6.0 (corners at 3.06 and 6.12), on radial
    joists, rim joists and blocking, held by sixteen knee braces down to a chocked steel collar at z -2.5. Posts 1.1 m
    high round the edge carry three ropes; the bays on +x and -x are open (2.3 m between posts) and their posts stand
    2.3 m high with a lantern each."""
    rng = np.random.default_rng(2630)
    p = Part('SM_GN_TreePlatform', (BARK, STEEL, CLOTH, MOSS, LEAF, GLOW))
    N, R0, R1, TH = 16, 3.0, 6.0, .045
    half = math.pi / N
    tn, cs = math.tan(half), math.cos(half)

    def wood(lo=0.0, hi=.35):
        return vary(rng, mix(WOOD_OLD, WOOD_PALE, rng.uniform(lo, hi)), .16)
    m = mark(p)
    nb = 20
    bw = (R1 - R0) / nb
    for k in range(N):
        th = k * TAU / N
        d, t = V3(math.cos(th), math.sin(th), 0), V3(-math.sin(th), math.cos(th), 0)
        for j in range(nb):
            r0, r1 = R0 + j * bw + .002, R0 + (j + 1) * bw - .002
            hexa(p, [d * r + t * (s * (r * tn - .003)) + Z * z for z in (-TH, 0) for s in (-1, 1) for r in (r0, r1)], wood(), BARK)
        ds = V3(math.cos(th + half), math.sin(th + half), 0)                     # the seam between this sector and the next
        bar(p, ds * (R0 / cs + .02) - Z * (TH + .09), ds * (R1 / cs - .02) - Z * (TH + .09), .07, .18, BARK, colour=wood(0, .15))
        bar(p, d * (R0 + .04) - Z * (TH + .07), d * (R1 - .04) - Z * (TH + .07), .06, .14, BARK, colour=wood(0, .15))
        for ap, w, h in ((R1 - .03, .05, .2), (R0 + .03, .05, .2), (4.5, .05, .14)):
            bar(p, d * ap - t * (ap * tn) - Z * (TH + h / 2 + .001), d * ap + t * (ap * tn) - Z * (TH + h / 2 + .001), w, h, BARK, colour=wood(0, .2))
        foot = ds * 3.03 - Z * 2.5
        bar(p, ds * 5.2 - Z * (TH + .2), foot, .1, .1, BARK, colour=wood(0, .12))
        ts = np.cross(Z, ds)
        bar(p, foot - ts * .26 - Z * .02, foot + ts * .26 - Z * .02, .14, .2, BARK, colour=wood(0, .1))          # the chock the brace bears on
    age(p, m, 171, ground=-9.0, grime=.3, streak=.0, moss=.3, scale=1.3)
    # steel: the collar's two bands with their tightening bolts, cleats and bolts at both ends of every brace
    m = mark(p)
    for z in (-2.44, -2.6):
        ring = [V3(math.cos(a), math.sin(a), 0) * (3.12 / cs) + Z * z for a in np.arange(N + 1) * TAU / N]
        for a, b in zip(ring, ring[1:]):
            bar(p, a, b, .006, .07, STEEL, Z)
    for k in range(N):
        ds = V3(math.cos(k * TAU / N + half), math.sin(k * TAU / N + half), 0)
        ts = np.cross(Z, ds)
        for s in (-1, 1):
            bolts(p, [ds * 5.2 + ts * s * .055 - Z * (TH + .2), ds * 3.1 + ts * s * .055 - Z * 2.43], ts * s, .012, STEEL)
            plate(p, [ds * 5.02 + ts * s * .052 - Z * (TH + .18), ds * 5.36 + ts * s * .052 - Z * (TH + .18), ds * 5.36 + ts * s * .052 - Z * (TH + .01),
                      ds * 5.2 + ts * s * .052 - Z * (TH + .01)], .006, STEEL)
    for a in (half * 2, math.pi + half * 2):
        d = V3(math.cos(a), math.sin(a), 0)
        t = np.cross(Z, d)
        for z in (-2.44, -2.6):
            pipe(p, [d * 3.16 - t * .12 + Z * z, d * 3.16 + t * .12 + Z * z], .012, STEEL, 6)
            gbox(p, d * 3.16 - t * .03 + Z * (z - .025) - .025, d * 3.16 + t * .03 + Z * (z + .025) + .025, STEEL, 9, .004)
    paint(p, m, steel(172, STEEL_GREY, .45, ground=-9))
    # posts, ropes, lashings
    posts = []
    for k in range(N):
        a = k * TAU / N
        tall = k in (0, 1, N // 2, N // 2 + 1)
        posts.append((a - half, (R1 / cs) - .075, tall))
        if k not in (0, N // 2):
            posts.append((a, R1 - .06, False))
    posts.sort(key=lambda q: q[0])
    m = mark(p)
    lanterns = []
    for a, r, tall in posts:
        d = V3(math.cos(a), math.sin(a), 0)
        hgt = 2.3 if tall else 1.1
        bar(p, d * r - Z * .26, d * r + Z * hgt, .09, .09, BARK, d, colour=wood(.05, .3))
        hexa(p, [d * r + np.cross(Z, d) * (sy * .055) + d * (sx * .055) + Z * (hgt + (.012 if sz else 0) - (0 if sz else 0)) for sz in (0, 1) for sy in (-1, 1) for sx in (-1, 1)],
             wood(0, .1), BARK)
        if tall:
            arm = d * (r - .32) + Z * (hgt - .12)
            bar(p, d * r + Z * (hgt - .12), arm, .05, .05, BARK, colour=wood(0, .2))
            lanterns.append(tuple(np.round(arm - Z * .32, 3)))
    age(p, m, 173, ground=-9.0, grime=.3, streak=.15, moss=.2)
    m = mark(p)
    rope = _rgb(ROPE)
    for i, (a, r, tall) in enumerate(posts):
        a2, r2, _ = posts[(i + 1) % len(posts)]
        d, d2 = V3(math.cos(a), math.sin(a), 0), V3(math.cos(a2), math.sin(a2), 0)
        gap = abs(math.remainder(a2 - a, TAU)) > half * 1.5
        for hz in (1.02, .68, .34):
            hoop(p, d * r + Z * hz, .062, .012, CLOTH, Z, 8, 5, colour=_out([rope * rng.uniform(.6, .9)])[0])
            if not gap:
                A, B = d * r + Z * hz, d2 * r2 + Z * hz
                pts = [A + (B - A) * q - Z * (.05 * math.sin(math.pi * q)) for q in np.linspace(0, 1, 5)]
                pipe(p, pts, .011, CLOTH, 6, colour=_out([rope * rng.uniform(.7, 1.0)])[0])
    age(p, m, 174, ground=-9.0, grime=.25, streak=0.0)
    for q in lanterns:                                                # four lanterns: a hook, a caged warm light
        q = V3(*q)
        m = mark(p)
        pipe(p, [q + Z * .32, q + Z * .16], .005, STEEL, 4)
        turn(p, [(.07, .12), (.02, .16)], STEEL, 8, q)
        turn(p, [(.02, -.12), (.07, -.1), (.07, -.085)], STEEL, 8, q)
        for a in np.radians((0, 90, 180, 270)):
            pipe(p, [q + V3(math.cos(a) * .066, math.sin(a) * .066, -.09), q + V3(math.cos(a) * .066, math.sin(a) * .066, .12)], .004, STEEL, 4)
        paint(p, m, steel(175, STEEL_DARK, .3, ground=-9))
        fl.ball(p, q + Z * .01, .05, tone(GLOW_WARM, 1.0), GLOW, 10, (1, 1, 1.5))
    for _ in range(14):
        a, r = rng.uniform(0, TAU), rng.uniform(R0 + .15, R1 - .4)
        moss_patch(p, rng, (math.cos(a) * r, math.sin(a) * r, 0), rng.uniform(.08, .2), .012)
    n = 12
    a, r = rng.uniform(0, TAU, n), rng.uniform(R0 + .2, R1 - .5, n)
    g = rng.uniform(0, TAU, n)
    fl.cards(p, np.stack([np.cos(a) * r, np.sin(a) * r, np.full(n, .008)], 1), np.stack([np.cos(g), np.sin(g), np.zeros(n)], 1), Z,
             rng.uniform(.35, .6, n), rng.uniform(.35, .6, n), fl.CELL_LITTER, np.array([vary(rng, mix(LEAF_GOLD, LEAF_RUSSET, rng.uniform(0, 1)), .2) for _ in range(n)]),
             rng=rng, foot=1.0)
    gy = (R1 / cs - .075) * math.sin(half)
    return done(p, pivot='any', facts=dict(deck_z=0.0, inner_apothem=R0, outer_apothem=R1, corner_radii=(round(R0 / cs, 3), round(R1 / cs, 3)), sectors=N,
                                           gaps=[dict(side='+x', y=(-round(gy - .045, 3), round(gy - .045, 3))), dict(side='-x', y=(-round(gy - .045, 3), round(gy - .045, 3)))],
                                           post_height=1.1, rope_heights=(1.02, .68, .34), braces_to=-2.5, collar_z=(-2.64, -2.4), lowest=-2.64, lanterns=lanterns))


# ================================================================ the Drowned Campus
# The blocks stand on the lake bed, 5 m under the water: CAMPUS_WATER is the water line their stains are painted to.
CAMPUS_WATER = 5.0


def coping(p, lo, hi, fn, t=.07, over=.04, piece=1.0, slot=CONCRETE):
    """Precast coping stones on a wall whose box is lo..hi (axis-aligned): they overhang both faces and are jointed
    about every `piece` along the wall's length."""
    lo, hi = np.asarray(lo, np.float64), np.asarray(hi, np.float64)
    ax = 0 if hi[0] - lo[0] > hi[1] - lo[1] else 1
    L = hi[ax] - lo[ax]
    n = cells(L, piece)
    m = mark(p)
    for i in range(n):
        c0, c1 = [lo[0] - over, lo[1] - over, hi[2]], [hi[0] + over, hi[1] + over, hi[2] + t]
        c0[ax], c1[ax] = lo[ax] + L * i / n + .004, lo[ax] + L * (i + 1) / n - .004
        gbox(p, c0, c1, slot, .6, .012)
    paint(p, m, fn)


def downpipe(p, top, z_bottom, out, fn, r=.05, slot=STEEL):
    """A rainwater pipe down a wall from a hopper head at `top` (a point on the wall's face) to z_bottom, on stand-off
    brackets; out = the wall's outward normal."""
    top, out = np.asarray(top, np.float64), unit(out)
    side = np.cross(Z, out)
    c = top + out * (r + .03)
    m = mark(p)
    ring = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    gprism(p, [c - Z * .26 + side * sx * .065 + out * so * .065 for sx, so in ring], [c + side * sx * .16 + out * so * .1 for sx, so in ring], slot, 9)
    pipe(p, [c - Z * .26, V3(c[0], c[1], z_bottom + .3), V3(c[0], c[1], z_bottom + .12) + out * .06, V3(c[0], c[1], z_bottom + .04) + out * .2], r, slot, 10)
    for z in np.arange(z_bottom + 1.0, top[2] - .5, 1.8):
        q = V3(c[0], c[1], z)
        bar(p, q - side * (r + .03) - out * r, q + side * (r + .03) - out * r, .05, .012, slot, Z)
        bar(p, q - out * (r + .03), q - out * r * .5, .03, .03, slot, Z)
    paint(p, m, fn)


def ahu(p, x0, y0, x1, y1, z, h, fn, frame_fn):
    """A roof-top air-handling unit standing at height z: a panelled casing on a channel skid, a louvred intake on
    its +x end, a fan cowl and a rain cap on top."""
    yc = (y0 + y1) / 2
    m = mark(p)
    for y in (y0 + .1, y1 - .1):
        channel(p, (x0 - .05, y, z + .06), (x1 + .05, y, z + .06), .12, .05, STEEL, Z, 1 if y < yc else -1)
    turn(p, [(.3, 0), (.3, .2), (.35, .2), (.35, .24), (.03, .29)], STEEL, 20, ((x0 + x1) / 2 - .35, yc, z + h + .03))
    disc(p, ((x0 + x1) / 2 - .35, yc, z + h + .32), .03, STEEL, Z, 8)
    paint(p, m, frame_fn)
    m = mark(p)
    gbox(p, (x0, y0, z + .12), (x1, y1, z + h), PAINT, .6, .015, 'z')
    n = cells(x1 - x0, .8)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        gbox(p, (x - .025, y0 - .012, z + .12), (x + .025, y0, z + h), PAINT, 9, .003, 'Y')
        gbox(p, (x - .025, y1, z + .12), (x + .025, y1 + .012, z + h), PAINT, 9, .003, 'y')
    gbox(p, (x0 - .03, y0 - .03, z + h), (x1 + .03, y1 + .03, z + h + .03), PAINT, .8, .008)
    paint(p, m, fn)
    louvre(p, (x1, y0 + .15, z + .32), Y, (y1 - y0) - .3, h - .6, frame_fn, STEEL, 8)


def vent_stack(p, c, r, h, fn, slot=STEEL):
    """A vent pipe through a roof at c with a conical cowl."""
    m = mark(p)
    turn(p, [(r * 1.5, 0), (r * 1.5, .06), (r, .06), (r, h), (r * 1.9, h - .05), (r * 1.9, h), (r * 1.2, h + .18), (.02, h + .22)], slot, 14, c)
    disc(p, V3(*c) + Z * (h + .22), .02, slot, Z, 6)
    paint(p, m, fn)


def rooflight(p, x0, y0, x1, y1, z, fn, frame_fn, rng):
    """A ridged rooflight on a concrete upstand at height z: glass in steel glazing bars (a pane or two gone)."""
    ym, zr = (y0 + y1) / 2, z + .66
    m = mark(p)
    gbox(p, (x0, y0, z), (x1, y1, z + .3), CONCRETE, .8, .015, 'z')
    paint(p, m, fn)
    m = mark(p)
    n = cells(x1 - x0 - .1, .6)
    xs = np.linspace(x0 + .05, x1 - .05, n + 1)
    pipe(p, [(xs[0], ym, zr), (xs[-1], ym, zr)], .02, STEEL, 6)
    for s, y in ((-1, y0 + .05), (1, y1 - .05)):
        bar(p, (xs[0], y, z + .31), (xs[-1], y, z + .31), .04, .03, STEEL)
        for x in xs:
            bar(p, (x, y, z + .32), (x, ym, zr), .025, .03, STEEL, Z)
    paint(p, m, frame_fn)
    gc = tone(GLASS_GREEN, .5)
    for s, y in ((-1, y0 + .05), (1, y1 - .05)):
        for a, b in zip(xs, xs[1:]):
            if rng.uniform() < .8:
                face(p, [(a + .012, y, z + .325), (b - .012, y, z + .325), (b - .012, ym, zr - .01), (a + .012, ym, zr - .01)], GLASS, V3(0, s, 1), vary(rng, gc, .15))
    for x, sx in ((xs[0], -1), (xs[-1], 1)):
        face(p, [(x, y0 + .05, z + .32), (x, y1 - .05, z + .32), (x, ym, zr)], GLASS, sx * X, gc)


def _lab_block(p, rng, hx, hy, floors, roof, seed, bay=4.0, glass=.6):
    """A framed research block of half extents hx, hy with its roof slab's top at `roof`: four facades of infill wall
    with a window to every bay and storey (floors = the floor levels), set between pilasters on the column lines and
    bands at the slab edges; a roof slab jointed every 2 m. Returns (the concrete material, the frame's)."""
    ledges = tuple((f - .45, .9) for f in floors[1:]) + ((roof - .5, 1.0),)
    conc = concrete(seed, damp=2.5, tide=CAMPUS_WATER, ledges=ledges, moss=.35, streak=.35)
    frame = steel(seed + 1, STEEL_GREY, .4, ground=CAMPUS_WATER - 1.5, damp=2.0)
    inner = {(1, 0): 'x', (-1, 0): 'X', (0, 1): 'y', (0, -1): 'Y'}
    for o, u, L in ((V3(hx, -hy, 0), Y, 2 * hy), (V3(-hx, hy, 0), -Y, 2 * hy), (V3(hx, hy, 0), -X, 2 * hx), (V3(-hx, -hy, 0), X, 2 * hx)):
        nb = int(round(L / bay))
        holes = [(i * bay + .6, (i + 1) * bay - .6, fz + .9, fz + 2.5) for i in range(nb) for fz in floors]
        sheet(p, o, u, Z, L, roof, .3, CONCRETE, holes=holes, sub=1.0, back=False, rim='', fn=conc)
        f = np.cross(u, Z)
        sk = inner[(int(round(f[0])), int(round(f[1])))]
        m = mark(p)
        for i in range(nb + 1):
            a0, a1 = max(i * bay - .22, 0), min(i * bay + .22, L)
            gbox(p, o + u * a0, o + u * a1 + f * .08 + Z * roof, CONCRETE, 1.0, .02, sk + 'z')
        for z0, z1 in [(fz - .45, fz) for fz in floors if fz >= .45] + [(roof - .5, roof)]:
            gbox(p, o + Z * z0, o + u * L + f * .1 + Z * z1, CONCRETE, 1.0, .02, sk)
        paint(p, m, conc)
        for a0, a1, b0, b1 in holes:
            window(p, o + u * a0 + Z * b0, u, a1 - a0, b1 - b0, frame, rng, depth=.14, nx=3, ny=2, glass=glass if b0 > CAMPUS_WATER else .85, back=.5)
    top = concrete(seed + 2, ground=roof - 8, moss=.4, blot=.55)
    sheet(p, (-hx, -hy, roof), X, Y, 2 * hx, 2 * hy, .3, CONCRETE, ju=np.arange(2, 2 * hx, 2.0), jv=np.arange(2, 2 * hy, 2.0), sub=1.0,
          groove=(.012, .006), back=False, rim='', fn=top)
    return conc, frame, top


@mesh('SM_GN_Lab0', (16.0, 12.0, 0))        # the block is 9 m to its roof; the parapet (9.9) and the roof plant (10.7) stand above it
def lab0():
    """The flooded research block: a two-storey concrete frame over a plinth, 16 x 12 m, strip windows in steel
    frames. Its flat roof is a walk surface at exactly z 9.0 inside a parapet 0.25 m thick and 0.9 m high (coping at
    9.9) with a 3 m gap in the middle of the +x side (y -1.5 to 1.5), where a threshold plate takes a catwalk. Roof
    plant stands along the -x half: two air handlers, a hatch, vents and a rooflight; the +x half is clear."""
    rng = np.random.default_rng(2640)
    p = Part('SM_GN_Lab0', (CONCRETE, STEEL, PAINT, GLASS, RUST, MOSS, BARK, LEAF))
    hx, hy, RF, PH, PT = 8.0, 6.0, 9.0, .83, .25
    conc, frame, top = _lab_block(p, rng, hx, hy, (2.0, 5.5), RF, 181)
    par = concrete(184, ground=RF - .6, damp=1.2, moss=.4, ledges=((RF + PH, .5),))
    runs = [((hx - PT, -hy, RF), (hx, -1.5, RF + PH)), ((hx - PT, 1.5, RF), (hx, hy, RF + PH)), ((-hx, -hy, RF), (-hx + PT, hy, RF + PH)),
            ((-hx + PT, -hy, RF), (hx - PT, -hy + PT, RF + PH)), ((-hx + PT, hy - PT, RF), (hx - PT, hy, RF + PH))]
    for lo, hi in runs:
        m = mark(p)
        gbox(p, lo, hi, CONCRETE, .8, .015, 'z')
        paint(p, m, par)
        coping(p, lo, hi, par)
    m = mark(p)                                                     # the threshold in the gap, and the gate's old posts
    gbox(p, (hx - .5, -1.5, RF), (hx, 1.5, RF + .008), STEEL, .6, .003, 'z')
    for s in (-1, 1):
        gbox(p, (hx - .2, s * 1.5, RF), (hx - .12, s * 1.42, RF + 1.1), STEEL, 9, .006, 'z')
        turn(p, [(.016, -.05), (.016, .05)], STEEL, 8, (hx - .16, s * 1.4, RF + .9))
    paint(p, m, steel(185, STEEL_GREY, .4, ground=RF))
    grey = steel(186, mix(JUST_BONE, STEEL_GREY, .5), .22, ground=RF, damp=.6)
    rf = steel(187, STEEL_GREY, .4, ground=RF, damp=.6)
    plant = [('air handler', (-6.8, -4.6, -4.4, -3.2, 1.7)), ('air handler', (-6.8, 2.6, -4.4, 4.0, 1.7)), ('hatch', (-2.2, -5.2, -1.2, -4.2, .34)),
             ('rooflight', (2.6, 3.4, 5.0, 4.7, .66)), ('vents', (-3.4, 4.5, -2.3, 4.9, 1.15)), ('vent', (1.38, -5.22, 1.62, -4.98, 1.15))]
    ahu(p, -6.8, -4.6, -4.4, -3.2, RF, 1.35, grey, rf)
    ahu(p, -6.8, 2.6, -4.4, 4.0, RF, 1.35, grey, rf)
    for c in ((-3.2, 4.7, RF), (-2.5, 4.7, RF), (1.5, -5.1, RF)):
        vent_stack(p, c, .1, .9, rf)
    rooflight(p, 2.6, 3.4, 5.0, 4.7, RF, par, rf, rng)
    m = mark(p)
    gbox(p, (-2.2, -5.2, RF), (-1.2, -4.2, RF + .26), CONCRETE, .6, .015, 'z')
    paint(p, m, par)
    m = mark(p)
    gbox(p, (-2.24, -5.24, RF + .26), (-1.16, -4.16, RF + .32), STEEL, .6, .01)
    pipe(p, [(-1.9, -4.7, RF + .32), (-1.9, -4.7, RF + .37), (-1.5, -4.7, RF + .37), (-1.5, -4.7, RF + .32)], .012, STEEL, 6)
    for y in (-5.0, -4.4):
        turn(p, [(.02, -.07), (.02, .07)], STEEL, 8, (-2.25, y, RF + .29), Y)
    conduit(p, [(-7.72, y, RF + .25) for y in np.linspace(-2.9, 2.3, 4)], X, STEEL, .02, 1.0)
    paint(p, m, rf)
    downpipe(p, (hx + .1, -hy + .45, RF - .55), .1, X, frame)
    downpipe(p, (-hx - .1, hy - .45, RF - .55), .1, -X, frame)
    # what grows: moss along the parapet's foot and on the roof, weeds in the corners, ivy over the -y front
    for a, b, out in (((-hx + PT, -hy + PT, RF), (hx - PT, -hy + PT, RF), Y), ((hx - PT, hy - PT, RF), (-hx + PT, hy - PT, RF), -Y),
                      ((-hx + PT, hy - PT, RF), (-hx + PT, -hy + PT, RF), X), ((hx - PT, -hy + PT, RF), (hx - PT, -1.5, RF), -X), ((hx - PT, 1.5, RF), (hx - PT, hy - PT, RF), -X)):
        moss_line(p, rng, a, b, out, .16, .02, climb=.25)
    for _ in range(36):
        q = V3(rng.uniform(-7.5, 7.5), rng.uniform(-5.5, 5.5), RF)
        if not any(b[0] - .2 < q[0] < b[2] + .2 and b[1] - .2 < q[1] < b[3] + .2 for _n, b in plant):
            moss_patch(p, rng, q, rng.uniform(.08, .28), .016)
    for q in ((-7.5, -5.5), (7.45, 5.5), (-7.5, 5.4), (7.4, -5.5), (-4.2, 4.3), (-7.0, -2.9)):
        tuft(p, rng, (q[0], q[1], RF), rng.uniform(.3, .5), .45)
    sprig(p, rng, (-7.45, 5.45, RF), 1.2, 9, (LEAF_GREEN, LEAF_GOLD), BARK_BIRCH)
    ivy(p, rng, (-3.0, -hy - .1, CAMPUS_WATER + .2), X, -Y, 6.5, 4.4, 46)
    streaks(p, rng, [(hx + .1, rng.uniform(-5.5, 5.5), RF - .52) for _ in range(5)], X, (.5, 1.6), (.05, .12), RUST_DARK, RUST)
    streaks(p, rng, [(rng.uniform(-7.5, 7.5), hy + .1, RF - .52) for _ in range(6)], Y, (.5, 1.6), (.05, .12), RUST_DARK, RUST)
    return done(p, facts=dict(roof_z=RF, walk=dict(x=(-hx + PT, hx - PT), y=(-hy + PT, hy - PT)), parapet=dict(top=RF + PH + .07, thick=PT),
                              gap=dict(side='+x', y=(-1.5, 1.5), x=hx), plant=plant, clear='everything with x > -4 except the rooflight (x 2.6..5.0, y 3.4..4.7) and one vent at (1.5, -5.1)',
                              water_line=CAMPUS_WATER, floors=(2.0, 5.5)))


@mesh('SM_GN_Lab1', (12.0, 12.0, 0))
def lab1():
    """The taller block: three storeys of the same frame, 12 x 12 m, its flat roof a walk surface at exactly z 11.0
    with only a kerb 0.15 m high round its edge (a catwalk can land anywhere). In the -x -y corner the stair-head hut
    (3.2 x 2.8 m, 2.75 high, its door facing +x); beside the -x +y corner a triangular lattice aerial mast to z 18.0
    with two stays; an air handler and vents along the -y side."""
    rng = np.random.default_rng(2641)
    p = Part('SM_GN_Lab1', (CONCRETE, STEEL, PAINT, GLASS, RUST, MOSS, BARK, LEAF))
    h, RF = 6.0, 11.0
    conc, frame, top = _lab_block(p, rng, h, h, (.5, 4.0, 7.5), RF, 191)
    par = concrete(194, ground=RF - .6, damp=1.2, moss=.4)
    rf = steel(197, STEEL_GREY, .4, ground=RF, damp=.6)
    grey = steel(196, mix(JUST_BONE, STEEL_GREY, .5), .22, ground=RF, damp=.6)
    m = mark(p)
    for lo, hi in (((h - .3, -h, RF), (h, h, RF + .15)), ((-h, -h, RF), (-h + .3, h, RF + .15)), ((-h + .3, -h, RF), (h - .3, -h + .3, RF + .15)),
                   ((-h + .3, h - .3, RF), (h - .3, h, RF + .15))):
        gbox(p, lo, hi, CONCRETE, .8, .02, 'z')
    paint(p, m, par)
    # the stair-head hut
    HX0, HX1, HY0, HY1, HH = -5.3, -2.1, -5.3, -2.5, 2.5
    hut = concrete(195, ground=RF - .8, damp=1.5, moss=.35, ledges=((RF + HH, .7),))
    walls = ((V3(HX1, HY0, RF), Y, HY1 - HY0, [(.95, 1.85, 0, 2.05)]), (V3(HX0, HY1, RF), -Y, HY1 - HY0, []),
             (V3(HX1, HY1, RF), -X, HX1 - HX0, [(1.1, 2.1, 1.2, 1.9)]), (V3(HX0, HY0, RF), X, HX1 - HX0, []))
    for k, (o, u, L, holes) in enumerate(walls):
        sheet(p, o, u, Z, L, HH, .22, CONCRETE, holes=holes, jv=(1.25,), sub=.9, back=False, rim='', ties=(.9, .62, .014), fn=hut)
        f = np.cross(u, Z)
        if k == 0:
            steel_door(p, o + u * 1.02 - f * .1, u, .76, 1.98, olive(198, .3), rf)
        elif holes:
            louvre(p, o + u * 1.1 + Z * 1.2 - f * .1, u, 1.0, .7, rf, STEEL, 7)
    m = mark(p)
    gbox(p, (HX0 - .2, HY0 - .2, RF + HH), (HX1 + .2, HY1 + .2, RF + HH + .25), CONCRETE, .8, .025)
    paint(p, m, hut)
    downpipe(p, (HX1, HY1 - .2, RF + HH - .05), RF, X, rf, .04)
    # the aerial mast: three tube legs laced with rod, on a pad, stayed twice
    MX, MY, MB, MT = -4.4, 3.8, RF + .3, 18.0
    m = mark(p)
    gbox(p, (MX - .45, MY - .45, RF), (MX + .45, MY + .45, MB), CONCRETE, .5, .02, 'z')
    for q in ((-2.6, 3.8), (-4.4, 5.35)):
        gbox(p, (q[0] - .2, q[1] - .2, RF), (q[0] + .2, q[1] + .2, RF + .2), CONCRETE, 9, .015, 'z')
    paint(p, m, par)
    m = mark(p)
    legs = [V3(MX + .32 * math.cos(a), MY + .32 * math.sin(a), 0) for a in np.radians((90, 210, 330))]
    for q in legs:
        pipe(p, [q + Z * MB, q + Z * (MT - 1.2)], .028, STEEL, 8)
        gbox(p, q + V3(-.07, -.07, MB), q + V3(.07, .07, MB + .012), STEEL, 9, .003, 'z')
    zs = np.arange(MB + .3, MT - 1.25, .55)
    for i, z in enumerate(zs):
        for k in range(3):
            a, b = legs[k], legs[(k + 1) % 3]
            pipe(p, [a + Z * z, b + Z * z], .01, STEEL, 5, cap=False)
            if i < len(zs) - 1:
                pipe(p, [(a if i % 2 else b) + Z * z, (b if i % 2 else a) + Z * zs[i + 1]], .009, STEEL, 5, cap=False)
    pipe(p, [(MX, MY, MT - 1.3), (MX, MY, MT)], .02, STEEL, 8)
    pipe(p, [(MX - .32, MY - .16, MT - 2.6), (MX - .62, MY - .16, MT - 2.6), (MX - .62, MY - .16, MT - .9)], .012, STEEL, 6)
    for z in (15.6, 16.6):
        gbox(p, (MX + .3, MY - .42, z), (MX + .42, MY - .2, z + .85), STEEL, 9, .01)
    for q in ((-2.6, 3.8), (-4.4, 5.35)):
        pipe(p, [(q[0], q[1], RF + .2), (MX + (q[0] - MX) * .08, MY + (q[1] - MY) * .08, 14.6)], .014, STEEL, 6)
    paint(p, m, rf)
    dish(p, (MX + .1, MY + .38, 14.9), V3(.4, 1, 0), .42, .14, grey, rf)
    ahu(p, 1.6, -5.0, 4.0, -3.6, RF, 1.35, grey, rf)
    for c in ((4.9, -4.3, RF), (0.6, 4.9, RF), (1.3, 4.9, RF)):
        vent_stack(p, c, .1, .9, rf)
    plant = [('hut', (HX0 - .2, HY0 - .2, HX1 + .2, HY1 + .2, HH + .25)), ('mast', (MX - .45, MY - .45, MX + .45, MY + .45, MT - RF)),
             ('stay pads', (-2.8, 3.6, -2.4, 4.0, .2)), ('stay pad', (-4.6, 5.15, -4.2, 5.55, .2)), ('air handler', (1.6, -5.0, 4.0, -3.6, 1.7)),
             ('vents', (.5, 4.8, 1.4, 5.0, 1.15)), ('vent', (4.8, -4.4, 5.0, -4.2, 1.15))]
    for _ in range(30):
        q = V3(rng.uniform(-5.6, 5.6), rng.uniform(-5.6, 5.6), RF)
        if not any(b[0] - .2 < q[0] < b[2] + .2 and b[1] - .2 < q[1] < b[3] + .2 for _n, b in plant):
            moss_patch(p, rng, q, rng.uniform(.08, .28), .016)
    for a, b, out in (((-h + .3, -h + .3, RF), (h - .3, -h + .3, RF), Y), ((h - .3, h - .3, RF), (-h + .3, h - .3, RF), -Y),
                      ((HX1 + .0, HY0, RF), (HX1 + .0, HY1, RF), X), ((HX0, HY1, RF), (HX1, HY1, RF), Y)):
        moss_line(p, rng, a, b, out, .14, .02, climb=.12 if abs(a[1]) > 5 or abs(a[0]) > 5 else .3)
    for q in ((5.5, 5.5), (-5.5, 1.0), (5.55, -5.5), (-1.9, -5.5), (3.0, 5.5)):
        tuft(p, rng, (q[0], q[1], RF), rng.uniform(.3, .5), .45)
    sprig(p, rng, (5.5, 5.45, RF), 1.0, 8, (LEAF_GREEN, LEAF_GOLD), BARK_BROWN)
    ivy(p, rng, (h + .1, -4.5, CAMPUS_WATER + .2), Y, X, 5.5, 5.4, 44)
    streaks(p, rng, [(rng.uniform(-5.5, 5.5), -h - .1, RF - .52) for _ in range(5)], -Y, (.5, 1.6), (.05, .12), RUST_DARK, RUST)
    streaks(p, rng, [(-h - .1, rng.uniform(-5.5, 5.5), RF - .52) for _ in range(5)], -X, (.5, 1.6), (.05, .12), RUST_DARK, RUST)
    return done(p, facts=dict(roof_z=RF, walk=dict(x=(-h, h), y=(-h, h)), kerb=dict(height=.15, width=.3), hut=dict(x=(HX0 - .2, HX1 + .2), y=(HY0 - .2, HY1 + .2), top=RF + HH + .25,
                              door=(HX1, (HY0 + .95 + HY0 + 1.85) / 2, RF)), mast=dict(at=(MX, MY), top=MT, light=(MX, MY, MT)), plant=plant, water_line=CAMPUS_WATER,
                              floors=(.5, 4.0, 7.5), top=MT))


QUAY_WATER = 3.8      # the quay's top stands 2.2 m over the lake (physis_grove_plan.PADS), so the water line is at local z 3.8


@mesh('SM_GN_Quay', (1.4, 12.0, 6.0))
def quay():
    """A 12 m length of quay wall along y, facing +x (the water): mass concrete cast in 1.5 m lifts, its top a walk
    surface 1.4 m wide (x -0.7 to 0.7) at exactly z 6.0, edged with a steel nosing. On the face: three timber fenders
    on steel brackets, two mooring rings, a ladder of rungs at y 5 and a drain; algae to the water line (local z 3.8)."""
    rng = np.random.default_rng(2650)
    p = Part('SM_GN_Quay', (CONCRETE, STEEL, RUST, BARK, MOSS, LEAF))
    T = 6.0
    conc = concrete(201, damp=2.0, tide=QUAY_WATER, moss=.45, streak=.4, north=(1.0, 0.0), ledges=((T, .8),))
    back = concrete(202, damp=6.0, moss=.3, k=.8)
    sheet(p, (.7, -6, 0), Y, Z, 12, T - .1, 0, CONCRETE, ju=(3, 6, 9), jv=(1.5, 3.0, 4.5), back=False, rim='', ties=(1.0, .75, .018), fn=conc)
    sheet(p, (-.7, 6, 0), -Y, Z, 12, T, 0, CONCRETE, jv=(1.5, 3.0, 4.5), back=False, rim='', fn=back)
    top = concrete(203, ground=T - 8, moss=.45, blot=.55)
    sheet(p, (-.7, -6, T), X, Y, 1.3, 12, 0, CONCRETE, jv=(3, 6, 9), sub=.7, groove=(.014, .007), back=False, rim='', fn=top)
    m = mark(p)
    for s in (-1, 1):
        gface(p, (-.7, s * 6, 0), (.7, s * 6, 0), (.7, s * 6, T), (-.7, s * 6, T), CONCRETE, 1.5, s * Y)
    paint(p, m, back)
    m = mark(p)                                                        # the nosing: its top is part of the walk surface
    gbox(p, (.6, -6, T - .1), (.712, 6, T), STEEL, .8, .006, 'xz')
    paint(p, m, steel(204, STEEL_GREY, .5, ground=T - 9))
    fen = []
    m = mark(p)
    for y in (-4.0, 0.0, 4.0):                                         # fenders: a timber on two brackets
        hexa(p, [(.71 + (.1 if xb else 0), y + (.1 if yb else -.1), 2.5 + 3.2 * zb) for zb in (0, 1) for yb in (0, 1) for xb in (0, 1)],
             vary(rng, WOOD_OLD, .15), BARK)
        fen.append(y)
    age(p, m, 205, ground=QUAY_WATER - .6, reach=1.2, floor=.5, grime=.3, moss=.4)
    m = mark(p)
    for y in fen:
        for z in (2.9, 5.3):
            gbox(p, (.7, y - .16, z - .06), (.822, y + .16, z + .06), RUST, 9, .006, 'x')
            bolts(p, [(.822, y + sy * .13, z) for sy in (-1, 1)], X, .016, RUST)
    rings = []
    for y in (-2.0, 2.0):                                              # mooring rings on their eye plates
        gbox(p, (.7, y - .13, 5.0), (.725, y + .13, 5.3), RUST, 9, .005, 'x')
        bolts(p, [(.725, y + sy * .09, z) for sy in (-1, 1) for z in (5.05, 5.25)], X, .014, RUST)
        hoop(p, (.76, y, 5.2), .035, .014, RUST, Y, 12, 6)
        hoop(p, (.79, y, 5.06), .11, .016, RUST, X, 20, 6)
        rings.append((.79, y, 5.06))
    for z in np.arange(2.6, 5.85, .3):                                 # the ladder: rungs let into the wall
        pipe(p, [(.7, 4.78, z), (.82, 4.78, z), (.82, 5.22, z), (.7, 5.22, z)], .012, RUST, 6, cap=False)
    pipe(p, [(.62, -5.0, 4.4), (.78, -5.0, 4.38)], .05, RUST, 12)
    paint(p, m, steel(206, mix(RUST_ORANGE, RUST_DARK, .4), 0.0, ground=QUAY_WATER - 1, damp=2.0, grime=.45))
    streaks(p, rng, [(.7, -5.0, 4.33)], X, (.6, 1.0), (.1, .16), MOSS_DEEP, MOSS)
    streaks(p, rng, [(.7, y + rng.uniform(-.1, .1), 4.98) for y in (-2.0, 2.0)] + [(.7, y, 2.83) for y in fen], X, (.4, .9), (.04, .09))
    moss_line(p, rng, (-.7, 6, T), (-.7, -6, T), X, .16, .02)
    for _ in range(9):
        moss_patch(p, rng, (rng.uniform(-.6, .35), rng.uniform(-5.8, 5.8), T), rng.uniform(.06, .16), .014)
    for y in (-5.2, -1.3, 3.1):
        tuft(p, rng, (-.48, y, T), rng.uniform(.25, .4), .3)
    for zj in (4.5, 3.0):
        a, b = sorted(rng.uniform(-5.5, 5.5, 2))
        moss_line(p, rng, (.7, a, zj), (.7, b, zj), -Z, .1, .025)
    return done(p, facts=dict(top_z=T, top=dict(x=(-.7, .712), y=(-6.0, 6.0)), faces='+x', water_line=QUAY_WATER, mooring_rings=rings,
                              ladder=dict(y=5.0, z=(2.6, 5.8)), fenders_y=fen))


@mesh('SM_GN_Walkway', (8.0, 2.0, 1.4), pivot='any')
def walkway():
    """An 8 m steel catwalk span along x; pivot at the deck's top centre (the walk surface is z 0, from x -4 to 4).
    Two channel stringers 1.8 m apart, cross angles every metre and flat plan bracing under eight chequer plates
    (the deck, y -0.88 to 0.88); a guard rail each side on side-mounted stanchions: top rail at 1.1 m, a mid rail and
    a toe board."""
    p = Part('SM_GN_Walkway', (STEEL,))
    st = steel(211, STEEL_GREY, .32, ground=-6)
    m = mark(p)
    for s in (-1, 1):
        channel(p, (-4, s * .9, -.131), (4, s * .9, -.131), .25, .09, STEEL, Z, s)
    for x in np.arange(-3.5, 3.6, 1.0):
        angle(p, (x, -.89, -.008), (x, .89, -.008), .07, STEEL, X, -Z)
    for i, x in enumerate(np.arange(-4, 3.9, 2.0)):
        a, b = (x, -.82, -.2), (x + 2, .82, -.2)
        if i % 2:
            a, b = (x, .82, -.2), (x + 2, -.82, -.2)
        bar(p, a, b, .06, .008, STEEL)
    for x in (-4, 4):
        angle(p, (x, -.9, -.006), (x, .9, -.006), .08, STEEL, -np.sign(x) * X, -Z)
    for x0 in range(-4, 4):
        gbox(p, (x0 + .003, -.88, -.006), (x0 + .997, .88, 0), STEEL, .5, .002)
        bolts(p, [(x0 + dx, sy * .84, 0) for dx in (.08, .92) for sy in (-1, 1)], Z, .011, STEEL, h=.004, washer=False)
    for s in (-1, 1):
        handrail(p, [(x, s * .94, -.006) for x in (-3.96, -1.3, 1.3, 3.96)], STEEL, 1.106, 1.4, .12, inward=-s * Y, base=False)
        for x in np.linspace(-3.96, 3.96, 7):
            gbox(p, (x - .05, s * .905, -.2), (x + .05, s * .96, -.03), STEEL, 9, .004)
            bolts(p, [(x, s * .96, z) for z in (-.16, -.07)], s * Y, .011, STEEL, washer=False)
    paint(p, m, st)
    return done(p, pivot='any', facts=dict(deck_z=0.0, x=(-4.0, 4.0), deck_y=(-.88, .88), rails_y=(-.94, .94), rail_height=1.1, underside=-.26))


@mesh('SM_GN_Tank', (8.0, 8.0, 7.0), tol=.2)
def tank():
    """A storage tank 8 m across on a concrete ring: four courses of riveted plate with lapped seams, a flat roof that
    is a walk surface at exactly z 7.0 (radius 4.0), a caged ladder up the -x side, an outlet with a gate valve and an
    overflow pipe on the +y side; on the roof a manhole, a vent and a gauge. Rust rises to the water line (z 5)."""
    rng = np.random.default_rng(2652)
    p = Part('SM_GN_Tank', (CONCRETE, STEEL, RUST, MOSS))
    R, T, B = 4.0, 7.0, .35
    conc = concrete(221, damp=1.0, moss=.4, tide=CAMPUS_WATER)
    shell = steel(222, STEEL_GREY, .38, ground=CAMPUS_WATER - 1.2, damp=1.7, streak=.3)
    m = mark(p)
    turn(p, [(R + .28, 0), (R + .28, B - .04), (R + .24, B), (R - .2, B)], CONCRETE, 64)
    paint(p, m, conc)
    courses = np.linspace(B, T, 5)
    m = mark(p)
    for i, (za, zb) in enumerate(zip(courses, courses[1:])):
        zs = np.linspace(za, zb, 3)
        turn(p, [(R, z) for z in zs], STEEL, 64, hard=False)
        turn(p, [(R, zb - .06), (R + .008, zb - .06), (R + .008, zb + (.0 if i == 3 else .06)), (R, zb + (.0 if i == 3 else .06))], STEEL, 64)
        for a in np.arange(6) * TAU / 6 + i * .37:                      # the course's butt straps, staggered from course to course
            d = V3(math.cos(a), math.sin(a), 0)
            bar(p, d * (R + .003) + Z * za, d * (R + .003) + Z * zb, .12, .008, STEEL, d)
    turn(p, [(R, B), (R + .07, B), (R + .07, B + .012), (R + .012, B + .1), (R, B + .1)], STEEL, 64)       # the bottom angle
    paint(p, m, shell)
    m = mark(p)
    ang = np.arange(126) * TAU / 126
    for z in list(courses[1:-1] - .03) + list(courses[1:-1] + .03) + [T - .03, B + .05]:
        pts = np.stack([np.cos(ang) * (R + .008), np.sin(ang) * (R + .008), np.full(len(ang), z)], 1)
        fl.rivets(p, pts, np.stack([np.cos(ang), np.sin(ang), np.zeros(len(ang))], 1), .012, GREY, STEEL)
    paint(p, m, shell)
    roof = steel(223, STEEL_GREY, .42, ground=T - 9, moss=.35)
    m = mark(p)
    disc(p, (0, 0, T), .5, STEEL, Z, 16)
    annulus(p, .5, R + .008, T, STEEL, na=64, nr=5)
    paint(p, m, roof)
    m = mark(p)
    for a in np.arange(8) * TAU / 8 + .2:                               # the roof plates' lap seams
        bar(p, V3(math.cos(a), math.sin(a), 0) * .5 + Z * (T + .003), V3(math.cos(a), math.sin(a), 0) * (R - .02) + Z * (T + .003), .07, .006, STEEL)
    turn(p, [(.14, 0), (.14, .42), (.24, .4), (.24, .44), (.1, .5), (.02, .5)], STEEL, 16, (0, 0, T))
    turn(p, [(.45, 0), (.45, .05), (.4, .07), (.02, .07)], STEEL, 24, (2.2, -1.2, T))
    bolts(p, [(2.2 + .4 * math.cos(a), -1.2 + .4 * math.sin(a), T + .055) for a in np.linspace(0, TAU, 10, endpoint=False)], Z, .014, STEEL, washer=False)
    pipe(p, [(2.05, -1.2, T + .07), (2.05, -1.2, T + .12), (2.35, -1.2, T + .12), (2.35, -1.2, T + .07)], .012, STEEL, 6)
    g = V3(math.cos(math.radians(200)), math.sin(math.radians(200)), 0) * (R - .25)
    gbox(p, g + V3(-.1, -.1, T), g + V3(.1, .1, T + .45), STEEL, 9, .012, 'z')
    paint(p, m, roof)
    m = mark(p)
    ladder(p, (-R - .008, 0, B), T - B, -X, STEEL, standoff=.22, extend=.95)
    paint(p, m, steel(224, STEEL_GREY, .4, ground=CAMPUS_WATER - 1.2, damp=1.7))
    m = mark(p)                                                         # outlet and valve, overflow
    pipe(p, [(.6, R - .05, 1.0), (.6, R + .5, 1.0)], .15, STEEL, 20)
    flange(p, (.6, R + .14, 1.0), Y, .15, .23, .02, STEEL, 8, sides=20)
    fl.ball(p, (.6, R + .52, 1.0), .22, GREY, STEEL, 16)
    turn(p, [(.1, 0), (.1, .3), (.13, .3), (.13, .34), (.025, .34), (.025, .62)], STEEL, 14, (.6, R + .52, 1.15))
    hoop(p, (.6, R + .52, 1.77), .16, .014, STEEL, Z, 20, 6)
    for a in np.radians((0, 90, 180, 270)):
        pipe(p, [(.6, R + .52, 1.77), (.6 + .16 * math.cos(a), R + .52 + .16 * math.sin(a), 1.77)], .009, STEEL, 5)
    pipe(p, [(.6, R + .7, 1.0)] + list(arc_pts((.6, R + .7, .7), .3, 0, 90, Z, Y, 7))[1:] + [(.6, R + 1.0, .35), (.6, R + 1.0, 0)], .15, STEEL, 20)
    pipe(p, [(-.8, R - .05, T - .5), (-.8, R + .14, T - .5), (-.8, R + .2, T - .6), (-.8, R + .2, .9), (-.8, R + .32, .7)], .06, STEEL, 12)
    for z in (1.6, 3.4, 5.2):
        bar(p, (-.8, R, z), (-.8, R + .2, z), .05, .012, STEEL, Z)
    paint(p, m, shell)
    streaks(p, rng, [(math.cos(a) * (R + .01), math.sin(a) * (R + .01), float(z)) for a, z in zip(rng.uniform(0, TAU, 16), rng.choice(courses[1:-1] - .07, 16))],
            X, (.4, 1.2), (.05, .12))
    for _ in range(14):
        a, r = rng.uniform(0, TAU), rng.uniform(.6, R - .3)
        moss_patch(p, rng, (math.cos(a) * r, math.sin(a) * r, T), rng.uniform(.08, .25), .014)
    for a0 in (.4, 2.1, 3.9, 5.2):
        d0, d1 = V3(math.cos(a0), math.sin(a0), 0), V3(math.cos(a0 + .35), math.sin(a0 + .35), 0)
        moss_line(p, rng, d0 * (R + .28), d1 * (R + .28), unit(d0 + d1), .05, .025, climb=.2)
    return done(p, facts=dict(roof_z=T, roof_radius=R, ladder='-x (stringers at x -4.23, y +-0.225, to z 7.95)', water_line=CAMPUS_WATER,
                              on_roof=[('vent', (0, 0), .24, .5), ('manhole', (2.2, -1.2), .45, .12), ('gauge', (round(g[0], 2), round(g[1], 2)), .14, .45)],
                              outlet_valve=(.6, R + .52, 1.77)))


# ================================================================ the Reclaimed Road and Old Town

def column(p, c, hx, hy, z0, z1, fn, rng, chamfer=.04, lifts=(), spalls=(), cell=.6, cap=True, slot=CONCRETE):
    """A rectangular concrete column on (c[0], c[1]) from z0 to z1 with half sizes hx, hy: chamfered arrises, a V-groove
    at each lift joint, and spalls = [(corner, za, zb, depth)] where a corner (0: +x -y, then counter-clockwise) has
    broken away to the reinforcement, which shows: the corner bar and the links round it (RUST)."""
    zs = {round(z0, 4): 0.0, round(z1, 4): 0.0}
    for z in np.arange(z0, z1, cell):
        zs.setdefault(round(float(z), 4), 0.0)
    for z in lifts:
        zs[round(z - .014, 4)], zs[round(z, 4)], zs[round(z + .014, 4)] = 0.0, .012, 0.0
    for _k, za, zb, _d in spalls:
        for z in np.linspace(za, zb, max(4, int((zb - za) / .12))):
            zs.setdefault(round(float(z), 4), 0.0)
    stations = sorted(zs)
    corners = ((1, -1, X, Y), (1, 1, Y, -X), (-1, 1, -X, -Y), (-1, -1, -Y, X))
    wob = rng.uniform(0, 9, 4)

    def cut(k, z):
        ck = chamfer
        for kk, za, zb, depth in spalls:
            if kk == k and za < z < zb:
                t = (z - za) / (zb - za)
                ck += depth * math.sin(math.pi * t) ** .6 * (.72 + .28 * math.sin(z * 9 + wob[k]))
        return ck
    rings = []
    for z in stations:
        g = zs[z]
        ring = []
        for k, (sx, sy, din, dout) in enumerate(corners):
            q = V3(c[0] + sx * (hx - g), c[1] + sy * (hy - g), z)
            ck = min(cut(k, z), min(hx, hy) * .8)
            ring += [q - din * ck, q + dout * ck]
        rings.append(ring)
    verts = np.array(rings).reshape(-1, 3)
    faces = [[i * 8 + j, i * 8 + (j + 1) % 8, (i + 1) * 8 + (j + 1) % 8, (i + 1) * 8 + j] for i in range(len(stations) - 1) for j in range(8)]
    m = mark(p)
    p.add(verts, faces, GREY, slot, False)
    if cap:
        p.add(rings[-1], [list(range(8))], GREY, slot, False)
    paint(p, m, fn)
    cols = np.asarray(p.c[m[0]:m[0] + len(verts)], np.float64)
    for i, z in enumerate(stations):                                   # the broken faces are darker and rust-stained
        for k in range(4):
            deep = cut(k, z) - chamfer
            if deep > .03:
                f = min(1.0, deep / .12)
                for j in (2 * k, 2 * k + 1):
                    cols[i * 8 + j, :3] = cols[i * 8 + j, :3] * (1 - .45 * f) * (1 - .25 * f) + _rgb(RUST_DARK) * .25 * f
    p.c[m[0]:m[0] + len(verts)] = cols.tolist()
    for k, za, zb, depth in spalls:
        if depth < .13:
            continue
        sx, sy, _din, _dout = corners[k]
        q = V3(c[0] + sx * (hx - .065), c[1] + sy * (hy - .065), 0)
        a, b = za + .12 * (zb - za), zb - .12 * (zb - za)
        fl.limb(p, [q + Z * a, q + Z * (a + b) / 2 + V3(sx, sy, 0) * .015, q + Z * b], .014,
                _out([_rgb(RUST_DARK), _rgb(RUST_ORANGE) * .8, _rgb(RUST_DARK)]), RUST, 6)
        for z in np.arange(a + .08, b, .2):
            ck = cut(k, z)
            if ck > .13:
                o = V3(c[0] + sx * hx, c[1] + sy * hy, z)
                fl.limb(p, [o - X * sx * (ck + .01) - Y * sy * .045, o - X * sx * .05 - Y * sy * .045, o - X * sx * .045 - Y * sy * .05,
                            o - X * sx * .045 - Y * sy * (ck + .01)], .005, _out([_rgb(RUST_ORANGE) * .7])[0], RUST, 4)


def asphalt(seed):
    """Old road surface: grey-black, paler where it is worn to the stone, a green film where water sits."""
    base, pale, mg = _rgb(ASPHALT), _rgb(CONCRETE_STAIN) * .3, _rgb(MOSS_DEEP) * .6

    def f(P, N):
        P, N, x, y, z = _pn(P, N)
        b1 = .5 + .5 * noise2(x / 1.9 + 3.3, y / 1.9, seed + 41)
        b2 = .5 + .5 * noise2(x / .35, y / .35, seed + 42)
        t = np.clip(.7 * b1 + .5 * b2 - .45, 0, 1)[:, None]
        c = base * (.8 + .35 * b2[:, None]) * (1 - t) + pale * t
        m = np.clip(noise2(x / 1.4 + 7.7, y / 1.4, seed + 43) * 1.4 - .5, 0, .6)[:, None] * (N[:, 2:3] > .5)
        return _out(c * (1 - m) + mg * m)
    return f


def girder(p, x0, x1, y, z, slot=CONCRETE, cell=1.0):
    """A precast I-girder along x from x0 to x1 on the line y, its soffit at z: 0.9 m deep, bottom flange 0.65 m,
    web 0.2, top flange 0.5, with the haunches of its casting."""
    prof = [(-.325, 0), (.325, 0), (.325, .15), (.1, .3), (.1, .72), (.25, .8), (.25, .9), (-.25, .9), (-.25, .8), (-.1, .72), (-.1, .3), (-.325, .15)]
    gprism(p, [(x0, y + a, z + b) for a, b in prof], [(x1, y + a, z + b) for a, b in prof], slot, cell, '')
    for x, sx in ((x0, -1), (x1, 1)):
        for part in ([0, 1, 2, 3, 10, 11], [10, 3, 4, 9], [9, 4, 5, 6, 7, 8]):
            face(p, [(x, y + prof[i][0], z + prof[i][1]) for i in part], slot, sx * X)


def barrier(p, x0, x1, y_out, s, z, slot=CONCRETE, cell=1.0):
    """A length of F-shape concrete parapet along x standing on z: its outer face at y_out, the road toward s * y."""
    prof = [(0, 0), (.4, 0), (.4, .08), (.25, .33), (.2, .85), (0, .85)]
    gprism(p, [(x0, y_out + s * a, z + b) for a, b in prof], [(x1, y_out + s * a, z + b) for a, b in prof], slot, cell, 'bt')


@mesh('SM_GN_Overpass', (26.0, 10.0, 8.5))
def overpass():
    """The fallen overpass. A viaduct along x, 10 m wide, on bents of two columns (y -5 to -4 and 4 to 5) under a
    cap beam whose soffit is at z 5.0: the road passes along x between the columns, 8 m wide (y -4 to 4). The span from
    x -13 to 1 stands: four precast girders, diaphragms, a deck slab under asphalt, F-shape parapets, the stump of a
    lamp standard reaching z 8.5. The next span has come down. Its -y half, two girders under their strip of deck
    (y -5 to 0), lies as a ramp from the ground at x 12.9 up to its raised end at x 2.2, where the soffit of the
    girder on y -3.5 is exactly 3.3 m above the point (4, -3.5): Burr's hands; under that end the ground is clear
    from x 2.5 to 5.5, y -5 to -2. Its +y half broke up: a girder and slab pieces lie along y 4 to 5, so the lane
    y 0.3 to 3.9 stays open to x 13, past the one column of the far bent still standing with a stub of its cap."""
    rng = np.random.default_rng(2660)
    p = Part('SM_GN_Overpass', (CONCRETE, ROCK, PAINT, STEEL, RUST, MOSS, BARK, LEAF))
    CAP0, CAP1, SOF, GT, SL, AS = 5.0, 6.0, 6.15, 7.05, 7.27, 7.33
    GY = (-3.5, -1.17, 1.17, 3.5)
    XA, XB, XC = -12.3, .3, 12.3
    conc = concrete(231, damp=2.5, streak=.4, moss=.35, ledges=((GT, 1.2), (CAP0, .8)))
    road = asphalt(232)
    line = steel(233, ROAD_PAINT, 0.0, ground=-9, grime=.45)
    spalls = {(XA, -1): [(0, .5, 1.5, .2)], (XA, 1): [(1, 2.2, 3.0, .16)], (XB, -1): [(3, .3, 1.2, .18), (0, 3.6, 4.4, .15)], (XB, 1): [(2, .6, 1.9, .22)]}
    for xb in (XA, XB):
        for s in (-1, 1):
            column(p, (xb, s * 4.5), .55, .5, 0, CAP0, conc, rng, lifts=(1.7, 3.4), spalls=spalls[(xb, s)])
        m = mark(p)
        gbox(p, (xb - .7, -5, CAP0), (xb + .7, 5, CAP1), CONCRETE, .7, .04)
        for y in GY:
            for sx in (-1, 1):
                gbox(p, (xb + sx * .35 - .25, y - .3, CAP1), (xb + sx * .35 + .25, y + .3, CAP1 + .12), CONCRETE, 9, .015, 'z')
        paint(p, m, conc)
        m = mark(p)
        for y in GY:
            for sx in (-1, 1):
                gbox(p, (xb + sx * .35 - .2, y - .26, CAP1 + .12), (xb + sx * .35 + .2, y + .26, SOF), ROCK, 9, .004, 'z')
        paint(p, m, flat(ASPHALT, .7))
    m = mark(p)
    for y in GY:
        girder(p, -12.85, .25, y, SOF)
    for a0, a1, z0 in ((-12.78, -12.52, 6.35), (-6.4, -6.2, 6.5), (-.02, .24, 6.35)):
        for ya, yb in zip(GY, GY[1:]):
            gbox(p, (a0, ya + .1, z0), (a1, yb - .1, GT), CONCRETE, .7, .02, 'Z')
    paint(p, m, conc)

    def edge(y):
        return .25 + .9 * (.5 + .5 * float(noise2(y * .8, 3.3, 7)))
    deck = concrete(235, ground=-9, moss=.3, blot=.5)
    sheet(p, (-13, -5, SL), X, Y, 14.3, 10, SL - GT, CONCRETE, mask=lambda u, v: u - 13 < edge(v - 5), sub=.8, arris=.02, fn=deck)

    def hole(x, y, seed=9):
        return float(noise2(x * .45, y * .45, seed)) > .82          # where the wearing course has lifted off the slab
    sheet(p, (-13, -4.6, AS), X, Y, 13.2, 9.2, AS - SL, ROCK, mask=lambda u, v: not hole(u - 13, v - 4.6), sub=.8, arris=.02, back=False, fn=road)
    m = mark(p)
    for x in np.arange(-13, .1, 1.0):
        for y in (-4.3, 4.3):
            if not hole(x + .5, y):
                gbox(p, (x, y - .06, AS), (x + 1.0, y + .06, AS + .004), PAINT, 9, .001, 'z')
        if int(x) % 6 < 3 and not hole(x + .5, 0):
            gbox(p, (x, -.06, AS), (x + 1.0, .06, AS + .004), PAINT, 9, .001, 'z')
    paint(p, m, line)
    m = mark(p)
    for a, b in ((-13, -9.5), (-9.5, -6), (-6, -2.5), (-2.5, 1.0)):
        barrier(p, a + .01, b - .01, -5, 1, SL)
        if b < 0:
            barrier(p, a + .01, b - .01 - (1.2 if b > -3 else 0), 5, -1, SL)
    paint(p, m, concrete(236, ground=SL - .8, damp=1.6, moss=.4, streak=.35))
    m = mark(p)                                                         # steel: the joint at the bent, a rail, the lamp stump
    gbox(p, (.06, -4.6, AS - .02), (.2, 4.6, AS + .003), STEEL, .8, .003)
    for x in np.arange(-12.6, .9, 1.75):
        bar(p, (x, -4.9, SL + .85), (x, -4.9, SL + 1.1), .06, .012, STEEL, X)
    pipe(p, [(x, -4.9, SL + 1.1) for x in np.linspace(-12.9, .9, 6)], .03, STEEL, 10)
    gbox(p, (-7.7, 4.72, SL + .85), (-7.3, 4.98, SL + .87), STEEL, 9, .004, 'z')
    bolts(p, [(-7.5 + sx * .15, 4.85 + sy * .09, SL + .87) for sx in (-1, 1) for sy in (-1, 1)], Z, .016, STEEL)
    pipe(p, [(-7.5, 4.85, SL + .87), (-7.5, 4.85, 8.3), (-7.56, 4.9, 8.4), (-7.8, 5.0, 8.43)], .07, STEEL, 14)
    paint(p, m, steel(237, STEEL_GREY, .45, ground=SL - .5, damp=1.2))
    downpipe(p, (XA, -5.0, 6.9), 2.4, -Y, steel(238, STEEL_GREY, .5, ground=1.0, damp=3.0), .06)
    for y in np.arange(-4.7, 4.71, .55):                                 # the slab's torn edge: bars, and a piece still hanging by them
        e = edge(y)
        for dz in (-.05, -.17):
            if rng.uniform() < .8:
                rebar(p, rng, (e - .02, y, SL + dz), X, rng.uniform(.35, 1.0), droop=.6)
    m = mark(p)
    gbox(p, (-.6, -.45, -.11), (.6, .45, .11), CONCRETE, .5, .02)
    place(p, m, rot('z', 12) @ rot('y', 62), (1.75, 2.1, 6.45))
    paint(p, m, conc)
    for y in (1.8, 2.2, 2.45):
        fl.limb(p, [(edge(y) - .05, y, SL - .1), (1.3, y, 7.0), (1.48, y - .1, 6.9)], .011, _out([_rgb(RUST_DARK)])[0], RUST, 5)
    # ---- the fallen half-span, built on its own length and laid down
    Lp, x_raise = 11.4, 2.2
    lo, hi = math.radians(10), math.radians(30)
    for _ in range(50):                                                 # the pitch that seats its far end on the ground
        th = (lo + hi) / 2
        if 3.25 + (4 - x_raise) * math.tan(th) - Lp * math.sin(th) > 0:
            lo = th
        else:
            hi = th
    z_raise = 3.3 + (4 - x_raise) * math.tan(th)
    Rf, Tf = rot('y', math.degrees(th)), V3(x_raise, 0, z_raise)

    def laid(build, fn):
        mm = mark(p)
        build()
        place(p, mm, Rf, Tf)
        if fn is not None:
            paint(p, mm, fn)

    def to_world(q):
        return Rf @ np.asarray(q, np.float64) + Tf

    def fedge(a):
        return 4.7 + .45 * float(noise2(a * .7, 1.7, 5))

    def piece_concrete():
        for y in GY[:2]:
            girder(p, 0, Lp, y, 0.0)
        for a0, a1, z0 in ((0, .25, .2), (5.6, 5.8, .35), (Lp - .25, Lp, .2)):
            gbox(p, (a0, GY[0] + .1, z0), (a1, GY[1] - .1, .9), CONCRETE, .6, .02, 'Z')
        sheet(p, (0, -5, 1.12), X, Y, Lp, 5.3, .22, CONCRETE, mask=lambda u, v: v < fedge(u), ju=(6.9,), groove=(.06, .04), sub=.8, arris=.02)
        for a, b in ((.3, 3.6), (7.4, 10.6)):
            barrier(p, a, b, -5, 1, 1.12)
    laid(piece_concrete, concrete(239, damp=1.6, streak=.3, moss=.45, blot=.5))
    laid(lambda: sheet(p, (0, -4.6, 1.18), X, Y, Lp, 4.2, .06, ROCK, mask=lambda u, v: not hole(u + 3, v - 4.6, 12) and v < fedge(u) - .5, sub=.8, arris=.02, back=False),
         asphalt(240))

    def piece_lines():
        for a in np.arange(.2, Lp - 1, 1.0):
            if not hole(a + 3.5, -4.3, 12):
                gbox(p, (a, -4.36, 1.18), (a + 1.0, -4.24, 1.184), PAINT, 9, .001, 'z')
    laid(piece_lines, line)
    for a in np.arange(.3, Lp, .5):                                      # bars along its torn inner edge and at both ends
        if rng.uniform() < .7:
            rebar(p, rng, to_world((a, -5 + fedge(a) - .03, 1.0)), Y, rng.uniform(.3, .9), droop=.5)
    for y in np.arange(-4.8, -.4, .4):
        if rng.uniform() < .8:
            rebar(p, rng, to_world((0.02, y, 1.02)), Rf @ -X, rng.uniform(.25, .7), droop=.5)
    burr = to_world(((4 - x_raise) / math.cos(th), GY[0], 0.0))
    # ---- the far bent: one column standing with a stub of its cap, the other a stump under the fallen deck
    column(p, (XC, 4.5), .55, .5, 0, CAP0, conc, rng, lifts=(1.7, 3.4), spalls=[(3, 1.0, 2.4, .2), (2, 3.5, 4.5, .17)])
    column(p, (XC, -4.5), .55, .5, 0, 1.0, conc, rng, spalls=[(1, .3, 1.0, .25), (0, .5, 1.0, .2)])
    m = mark(p)
    gbox(p, (XC - .7, 2.2, CAP0), (XC + .7, 5, CAP1), CONCRETE, .7, .04)
    for y in GY[3:]:
        gbox(p, (XC - .35 - .25, y - .3, CAP1), (XC - .35 + .25, y + .3, CAP1 + .12), CONCRETE, 9, .015, 'z')
    paint(p, m, conc)
    for x in np.arange(XC - .55, XC + .56, .22):
        for z in (CAP0 + .1, CAP1 - .1):
            rebar(p, rng, (x, 2.22, z), -Y, rng.uniform(.4, 1.1), droop=.6)
    for q in ((XC - .3, -4.2), (XC + .25, -4.7), (XC + .1, -4.3), (XC - .35, -4.75)):
        rebar(p, rng, (q[0], q[1], .95), Z, rng.uniform(.3, .7), droop=.9, bend=.5)
    # ---- what is left of the +y half: a girder on its side in two lengths, slab pieces, rubble
    for x0, L, yaw in ((3.6, 3.8, 1.5), (7.9, 2.6, -2.0)):
        m = mark(p)
        girder(p, 0, L, 0, 0)
        place(p, m, rot('z', yaw) @ rot('x', 90), (x0, 4.95, .325))
        paint(p, m, conc)
        for sx, xe in ((-1, x0), (1, x0 + L)):
            for dy in (.1, .45, .8):
                rebar(p, rng, (xe, 4.95 - dy, .3), sx * X, rng.uniform(.2, .5), droop=.8)
    for (cx, cy, cz), (sx, sy), R in (((5.2, 4.5, .78), (2.0, .9), rot('y', -8) @ rot('z', 3)), ((9.2, 4.48, .8), (1.3, .86), rot('x', 6) @ rot('z', -4)),
                                      ((11.25, 4.5, .72), (1.5, .9), rot('y', -52))):
        m = mark(p)
        gbox(p, (-sx / 2, -sy / 2, -.11), (sx / 2, sy / 2, .11), CONCRETE, .5, .02)
        place(p, m, R, (cx, cy, cz))
        paint(p, m, conc)
        m = mark(p)
        gbox(p, (-sx / 2 + .03, -sy / 2 + .03, .11), (sx / 2 - .05, sy / 2 - .03, .17), ROCK, .5, .01, 'z')
        place(p, m, R, (cx, cy, cz))
        paint(p, m, road)
    m = mark(p)
    rubble(p, rng, (12.15, -2.5), .75, 2.1, 30, (.15, .5))
    rubble(p, rng, (8.9, 4.45), 1.9, .42, 16, (.12, .35))
    rubble(p, rng, (XC - .2, -4.45), .6, .45, 10, (.12, .3))
    rubble(p, rng, (1.3, 4.5), .5, .4, 8, (.1, .3))
    paint(p, m, concrete(241, damp=1.0, moss=.5, blot=.6, k=.9))
    # ---- what grows
    for xb, s in ((XA, -1), (XA, 1), (XB, 1), (XC, 1)):
        moss_line(p, rng, (xb - .55, s * 4.0, 0), (xb + .55, s * 4.0, 0), -s * Y, .06, .025, climb=.3)
        moss_line(p, rng, (xb - .55, s * 5.0, 0), (xb + .55, s * 5.0, 0), s * Y, .05, .025, climb=.4)
    for _ in range(18):
        x, y = rng.uniform(-12.8, 0), rng.uniform(-4.5, 4.5)
        if not hole(x, y):
            moss_patch(p, rng, (x, y, AS), rng.uniform(.1, .3), .016)
    for _ in range(14):
        a, y = rng.uniform(.5, Lp - .5), rng.uniform(-4.5, -.9)
        if not hole(a + 3, y, 12):
            moss_patch(p, rng, to_world((a, y, 1.18)), rng.uniform(.1, .3), .016, Rf @ Z)
    for q in ((-11.5, -4.4, AS), (-8.2, 4.4, AS), (-4.0, -4.45, AS), (-1.2, 4.3, AS), (-6.0, 1.0, AS), (-.6, -2.0, AS)):
        tuft(p, rng, q, rng.uniform(.3, .5), .45)
    for a, y in ((6.9, -3.6), (6.9, -1.9), (6.95, -.8), (10.4, -2.5), (9.3, -4.3), (3.0, -4.5), (10.9, -1.0)):
        tuft(p, rng, to_world((a, y, 1.14)), rng.uniform(.3, .55), .45)
    sprig(p, rng, to_world((10.7, -3.3, 1.14)), 1.1, 9, (LEAF_GREEN, LEAF_GOLD), BARK_BIRCH)
    sprig(p, rng, (12.5, -1.0, .1), 1.4, 10, (LEAF_GREEN, LEAF_LIGHT), BARK_BROWN)
    sprig(p, rng, (8.4, 4.4, .5), .9, 8, (LEAF_GREEN, LEAF_GOLD), BARK_BROWN)
    ivy(p, rng, (-10.5, -5.03, 5.3), X, -Y, 6.0, 2.6, 34)
    streaks(p, rng, [(XB - .7, y + rng.uniform(-.2, .2), CAP1 - .02) for y in GY] + [(XA - .7, y, CAP1 - .02) for y in GY[1:3]], -X, (.4, .9), (.06, .12), RUST_DARK, RUST)
    streaks(p, rng, [(XA + .7, GY[0], CAP1 - .02), (XA + .7, GY[3], CAP1 - .02)], X, (.4, .9), (.06, .12), RUST_DARK, RUST)
    return done(p, facts=dict(
        road=dict(along='x', y=(-4.0, 4.0), under_span_x=(-13.0, 1.0), clear_under_caps=CAP0, clear_under_girders=SOF, caps_x=((XA - .7, XA + .7), (XB - .7, XB + .7)),
                  open_lane_beyond=dict(x=(1.0, 13.0), y=(.3, 3.9)), far_cap_stub=dict(x=(XC - .7, XC + .7), y=(2.2, 5.0), soffit=CAP0)),
        burr=dict(point=(4.0, -3.5), soffit_z=round(float(burr[2]), 4), clear=dict(x=(2.5, 5.5), y=(-5.0, -2.0)), girder_y=(-3.825, -3.175),
                  slab_soffit_above_girder_soffit=round(.9 * math.cos(th), 3)),
        fallen=dict(pitch_deg=round(math.degrees(th), 3), raised_end_x=x_raise, raised_end_soffit_z=round(z_raise, 3), far_end_x=round(x_raise + Lp * math.cos(th), 3),
                    y=(-5.0, -.3), top_at_raised_end=round(float(to_world((0, -3, 1.18))[2]), 3), top_at_far_end=round(float(to_world((Lp, -3, 1.18))[2]), 3)),
        deck=dict(z=AS, x=(-13.0, .2), y=(-4.6, 4.6)), columns=[(XA, -4.5), (XA, 4.5), (XB, -4.5), (XB, 4.5), (XC, 4.5)], top=8.5))


def broken(profile, rng, rough=.3):
    """A broken wall's top as a function of the distance along it: straight runs between the given (distance, height)
    points, roughened."""
    us, hs = np.array([q[0] for q in profile], np.float64), np.array([q[1] for q in profile], np.float64)
    ph = rng.uniform(0, 100)
    return lambda u: float(np.interp(u, us, hs) + rough * (math.sin(u * 2.3 + ph) * .6 + math.sin(u * 5.9 + ph * 2) * .4))


def ruin_wall(p, rng, o, u, L, top, fn, holes=(), T=.25, joints=(), sub=.8, rim='lr', bars=.35):
    """A broken concrete wall from o along u (it faces u x Z), L long, standing up to top(distance): its openings
    cut through, its top ragged, and reinforcing bars standing out of the break here and there (bars = how often)."""
    H = max(top(a) for a in np.linspace(0, L, 80)) + .2
    out = sheet(p, o, u, Z, L, H, T, CONCRETE, holes=holes, mask=lambda a, b: b < top(a), jv=joints, sub=sub, ragged=.35, rng=rng, rim=rim, fn=fn)
    o, u = np.asarray(o, np.float64), unit(u)
    f = np.cross(u, Z)
    full = max(top(a) for a in np.linspace(0, L, 80))
    for a in np.arange(.3, L - .2, .45):
        t = top(a)
        if rng.uniform() < bars and .5 < t < full - .25 and not any(h[0] - .1 < a < h[1] + .1 and h[2] - .2 < t < h[3] + .5 for h in holes):
            rebar(p, rng, o + u * a - f * (T * rng.choice((.25, .75))) + Z * (t - .45), Z + u * rng.normal(0, .25), rng.uniform(.5, 1.0), droop=.5, bend=.35)
    return out


def solid_stair(p, x0, x1, y0, dy, n, rise, run, fn):
    """Mass concrete steps between x0 and x1 from y0, climbing along y (dy = 1 or -1): n treads, tread i's top at
    (i + 1) * rise, the flight carried solid to the ground."""
    m = mark(p)
    for i in range(n):
        ya, yb = y0 + dy * i * run, y0 + dy * (i + 1) * run
        gbox(p, (x0, ya, 0), (x1, yb, (i + 1) * rise), CONCRETE, .6, .012, 'z' + ('' if i == n - 1 else ('y' if dy < 0 else 'Y')))
    paint(p, m, fn)


@mesh('SM_GN_Ruin0', (12.0, 10.0, 11.0))
def ruin0():
    """A three-storey concrete shell, 12 x 10 m: a frame of columns with infill walls and window openings, whole to
    11 m along its -y side and broken down toward +y, where the building lies open. In the +x front a doorway 2.4 m
    wide (y -1.2 to 1.2) and 3.0 m high leads onto the open ground floor (slab at z 0.15, four interior columns).
    The first floor (3.65) survives over the -y half, the second (7.15) and the roof (10.65) only in the +x -y corner."""
    rng = np.random.default_rng(2670)
    p = Part('SM_GN_Ruin0', (CONCRETE, STEEL, RUST, MOSS, BARK, LEAF, GLASS))
    conc = concrete(251, damp=2.5, streak=.45, moss=.4, blot=.5, ledges=((3.4, .9), (6.9, .9), (10.4, .9)))
    F0, F1, F2, F3 = .15, 3.65, 7.15, 10.65
    win = [(1.1, 2.6), (4.6, 6.1), (8.1, 9.6)]
    tops = dict(front=broken([(0, 11.0), (3.0, 10.8), (5.0, 8.0), (7.5, 7.4), (10, 5.0)], rng), back=broken([(0, 6.0), (3, 7.4), (6, 10.3), (10, 11.0)], rng),
                south=broken([(0, 11.0), (4, 10.5), (8, 10.9), (12, 11.0)], rng, .15), north=broken([(0, 5.0), (3, 3.6), (6, 1.9), (9, 4.2), (12, 6.0)], rng))
    fb = [(c - .8, c + .8, a, b) for c in (1.79, 8.21) for a, b in win] + [(4.2, 5.8, a, b) for a, b in win[1:]]
    sb = [(c - .9, c + .9, a, b) for c in (2.13, 6.0, 9.87) for a, b in win]
    ruin_wall(p, rng, (6, -5, 0), Y, 10, tops['front'], conc, fb + [(3.8, 6.2, 0, 3.0)], joints=(3.5, 7.0, 10.5))
    ruin_wall(p, rng, (-6, 5, 0), -Y, 10, tops['back'], conc, fb + [(4.2, 5.8, 1.1, 2.6)], joints=(3.5, 7.0, 10.5))
    ruin_wall(p, rng, (-6, -5, 0), X, 12, tops['south'], conc, sb, joints=(3.5, 7.0, 10.5))
    ruin_wall(p, rng, (6, 5, 0), -X, 12, tops['north'], conc, sb, joints=(3.5, 7.0, 10.5))
    # the frame: perimeter columns as high as the wall beside them, four inside
    cols = [((5.82, -4.82), 11.0, [(1, 6.0, 7.2, .16)]), ((5.82, -1.6), 10.9, [(3, .4, 1.4, .2)]), ((5.82, 1.6), 8.3, [(2, 4.2, 5.3, .18)]), ((5.82, 4.82), 5.5, [(3, 1.2, 2.2, .2)]),
            ((-5.82, -4.82), 11.0, []), ((-5.82, -1.6), 9.2, [(0, 7.5, 8.6, .18)]), ((-5.82, 1.6), 7.7, [(1, .5, 1.6, .2)]), ((-5.82, 4.82), 6.4, []),
            ((-1.93, -4.82), 11.0, [(1, 2.0, 3.0, .15)]), ((1.93, -4.82), 11.0, []), ((1.93, 4.82), 3.1, [(3, .6, 1.8, .22)]), ((-1.93, 4.82), 5.0, [(0, 2.8, 4.0, .2)]),
            ((-1.93, -1.6), 4.7, [(0, .4, 1.3, .18)]), ((1.93, -1.6), 10.4, [(2, 4.4, 5.6, .16)]), ((1.93, 1.6), 3.7, [(1, .5, 1.5, .2)]), ((-1.93, 1.6), 2.3, [(2, .9, 2.0, .24)])]
    for c, h, sp in cols:
        column(p, c, .2, .2, 0, h, conc, rng, chamfer=.025, spalls=sp, cell=.7)
        if h < 10.9:
            for q in ((-.12, -.12), (.12, -.12), (.12, .12), (-.12, .12)):
                if rng.uniform() < .8:
                    rebar(p, rng, (c[0] + q[0], c[1] + q[1], h - .05), Z, rng.uniform(.3, .8), droop=.6, bend=.4)
    # floors
    flr = concrete(252, damp=.6, moss=.45, blot=.6)
    sheet(p, (-5.75, -4.75, F0), X, Y, 11.5, 9.5, .15, CONCRETE, ju=(3.8, 7.7), jv=(3.2, 6.4), groove=(.03, .012), sub=1.0, back=False, rim='', fn=flr)
    m = mark(p)
    gbox(p, (5.75, -1.2, 0), (6.02, 1.2, F0), CONCRETE, .6, .012, 'zx')
    paint(p, m, flr)
    up = concrete(253, ground=-9, moss=.4, blot=.55, ledges=())

    def e1(u):
        return 5.2 + .8 * float(noise2(u * .6, 2.2, 11))
    sheet(p, (-5.75, -4.75, F1), X, Y, 11.5, 9.5, .25, CONCRETE, mask=lambda u, v: v < e1(u) and not (5.0 < u < 7.4 and 2.4 < v < 4.2), sub=.8, arris=.02, rim='', fn=up)
    sheet(p, (-5.75, -4.75, F2), X, Y, 11.5, 9.5, .25, CONCRETE, mask=lambda u, v: u > 5.3 + .5 * float(noise2(v * .7, 5.5, 12)) and v < 3.5 + .5 * float(noise2(u * .7, 1.5, 13)),
          sub=.8, arris=.02, rim='', fn=up)
    sheet(p, (-5.75, -4.75, F3), X, Y, 11.5, 9.5, .22, CONCRETE, mask=lambda u, v: u > 8.3 + .4 * float(noise2(v * .7, 7.5, 14)) and v < 2.5 + .4 * float(noise2(u * .7, 3.5, 15)),
          sub=.8, arris=.02, rim='', fn=up)
    m = mark(p)                                                         # beams under what is left of the floors
    for z, runs in ((F1 - .25, (((-5.6, -1.75), (5.6, -1.45)), ((-2.08, -4.7), (-1.78, .3)), ((1.78, -4.7), (2.08, .5)), ((-5.6, -4.7), (-5.3, .2)), ((5.3, -4.7), (5.6, .4)))),
                    (F2 - .25, (((-.2, -1.75), (5.6, -1.45)), ((1.78, -4.7), (2.08, -1.3)), ((5.3, -4.7), (5.6, -1.2)))), (F3 - .22, (((2.6, -1.75), (5.6, -1.45)), ((5.3, -4.7), (5.6, -2.2))))):
        for (x0, y0), (x1, y1) in runs:
            gbox(p, (x0, y0, z - .45), (x1, y1, z), CONCRETE, .8, .02, 'Z')
    paint(p, m, conc)
    for u in np.arange(.4, 11.2, .5):                                   # the floors' torn edges
        if rng.uniform() < .6:
            rebar(p, rng, (-5.75 + u, -4.75 + e1(u) - .05, F1 - rng.choice((.06, .19))), Y, rng.uniform(.3, .9), droop=.6)
    for v in np.arange(.3, 3.4, .45):
        if rng.uniform() < .7:
            rebar(p, rng, (-.4, -4.75 + v, F2 - .1), -X, rng.uniform(.3, .9), droop=.6)
            rebar(p, rng, (2.55, -4.75 + v * .7, F3 - .1), -X, rng.uniform(.3, .8), droop=.6)
    # a length of the first floor hinged down on its bars, and the rubble of the +y side
    m = mark(p)
    gbox(p, (-1.7, -1.4, -.125), (1.7, 1.4, .125), CONCRETE, .7, .02)
    place(p, m, rot('x', -34), (-3.6, 1.75, 2.45))
    paint(p, m, up)
    for x in (-5.0, -4.2, -3.3, -2.4):
        fl.limb(p, [(x, .45, F1 - .1), (x, .62, F1 - .14), (x, .75, 3.25)], .011, _out([_rgb(RUST_DARK)])[0], RUST, 5)
    m = mark(p)
    rubble(p, rng, (3.6, 3.5), 1.7, 1.1, 34, (.15, .55), z0=F0)
    rubble(p, rng, (-3.8, 3.4), 1.5, .9, 22, (.15, .5), z0=F0)
    rubble(p, rng, (.5, 5.25), 2.6, .3, 14, (.12, .35))
    rubble(p, rng, (-.9, 2.6), .9, .7, 10, (.12, .4), z0=F0)
    paint(p, m, concrete(254, damp=1.0, moss=.5, blot=.6, k=.92))
    # steel that stayed: the door's frame, three window frames, a downpipe
    rf = steel(255, STEEL_GREY, .6, ground=0, damp=3.0)
    m = mark(p)
    for y in (-1.2, 1.2):
        angle(p, (5.99, y, F0), (5.99, y, 3.0), .07, STEEL, X, -np.sign(y) * Y)
    angle(p, (5.99, -1.2, 3.0), (5.99, 1.2, 3.0), .07, STEEL, X, -Z)
    paint(p, m, rf)
    window(p, (6.0, -5 + .99, 4.6), Y, 1.6, 1.5, rf, rng, depth=.1, nx=2, ny=2, glass=.25, back=0)
    window(p, (-6 + 1.23, -5.0, 1.1), X, 1.8, 1.5, rf, rng, depth=.1, nx=2, ny=2, glass=.2, back=0)
    window(p, (-6 + 5.1, -5.0, 4.6), X, 1.8, 1.5, rf, rng, depth=.1, nx=2, ny=2, glass=.3, back=0)
    downpipe(p, (6.0, -4.55, 10.2), 3.0, X, rf, .05)
    # what grows
    for a, b, out in (((6, -5, 0), (6, -1.2, 0), X), ((6, 1.2, 0), (6, 5, 0), X), ((-6, 5, 0), (-6, -5, 0), -X), ((-6, -5, 0), (6, -5, 0), -Y), ((6, 5, 0), (-6, 5, 0), Y)):
        moss_line(p, rng, a, b, out, .06, .025, climb=.35)
    for _ in range(22):
        moss_patch(p, rng, (rng.uniform(-5.5, 5.5), rng.uniform(-4.5, 4.5), F0), rng.uniform(.1, .3), .016)
    for _ in range(10):
        moss_patch(p, rng, (rng.uniform(-5.4, 5.4), rng.uniform(-4.5, -.2), F1), rng.uniform(.1, .3), .016)
    for q in ((-5.3, 4.2, F0), (5.3, 4.3, F0), (2.2, 4.4, F0), (-2.6, 3.9, F0), (-5.4, -4.4, F0), (4.9, -4.4, F1), (-4.8, -.6, F1), (.6, .0, F1), (4.6, -3.9, F2)):
        tuft(p, rng, q, rng.uniform(.3, .55), .5)
    sprig(p, rng, (3.2, 3.2, F0 + .3), 1.6, 12, (LEAF_GREEN, LEAF_LIGHT), BARK_BROWN, .02, .34)
    sprig(p, rng, (-3.0, -.4, F1), 1.2, 9, (LEAF_GREEN, LEAF_GOLD), BARK_BIRCH)
    sprig(p, rng, (-4.6, 3.6, F0 + .25), 1.0, 8, (LEAF_GREEN, LEAF_GOLD), BARK_BROWN)
    ivy(p, rng, (-5.6, -5.03, 0), X, -Y, 7.0, 8.5, 70)
    ivy(p, rng, (6.03, -4.8, 0), Y, X, 2.6, 6.0, 30)
    for q in p.v:              # leaf cards that droop under the ground plane stop at it
        q[2] = max(q[2], 0.0)
    return done(p, facts=dict(doorway=dict(face_x=6.0, y=(-1.2, 1.2), z=(0, 3.0)), ground_floor=dict(z=F0, x=(-5.75, 5.75), y=(-4.75, 4.75)),
                              interior_columns=[(-1.93, -1.6), (1.93, -1.6), (1.93, 1.6), (-1.93, 1.6)], first_floor=dict(z=F1, y=(-4.75, 0.0), hole=dict(x=(-.75, 1.65), y=(-2.35, -.55))),
                              second_floor=dict(z=F2, x=(0.0, 5.75), y=(-4.75, -1.5)), open_side='+y', rubble=[(3.6, 3.5), (-3.8, 3.4), (-.9, 2.6)], top=11.0))


@mesh('SM_GN_Ruin1', (9.0, 9.0, 7.0))
def ruin1():
    """A two-storey corner ruin, 9 x 9 m: the -x and -y walls stand, 7 m high at their corner and broken down along
    their lengths; of the other two only footings and stubs remain, so it is entered from +x and +y. Inside the corner
    a first-floor slab with its top at exactly z 3.4 (x -4.25 to about 1, y -4.25 to -0.2) on beams and two columns,
    reached by a flight of mass concrete stairs along the -x wall: 1.6 m wide (x -4.25 to -2.65), eighteen risers of
    0.189 m, starting at y 4.39 and climbing toward -y to land on the slab's edge at y -0.2."""
    rng = np.random.default_rng(2671)
    p = Part('SM_GN_Ruin1', (CONCRETE, RUST, MOSS, BARK, LEAF))
    conc = concrete(261, damp=2.2, streak=.45, moss=.4, blot=.5, ledges=((3.15, .9),))
    SL, N = 3.4, 18
    rise, run = SL / N, .27
    y_foot = -.2 + (N - 1) * run
    t_w = broken([(0, 1.6), (2.5, 3.9), (5, 5.6), (7.5, 6.8), (9, 7.0)], rng)
    t_s = broken([(0, 7.0), (2, 6.6), (4.5, 5.2), (6.5, 3.6), (9, 1.2)], rng)
    ruin_wall(p, rng, (-4.5, 4.5, 0), -Y, 9, t_w, conc, [(5.6, 6.8, 1.0, 2.4), (5.4, 6.6, 4.4, 5.8), (7.3, 8.3, 4.4, 5.8)], joints=(3.3,))
    ruin_wall(p, rng, (-4.5, -4.5, 0), X, 9, t_s, conc, [(1.3, 2.5, 1.0, 2.4), (4.0, 5.2, 1.0, 2.4), (1.3, 2.5, 4.4, 5.8), (3.9, 5.1, 4.4, 5.8)], joints=(3.3,))
    ruin_wall(p, rng, (4.5, -4.5, 0), Y, 9, broken([(0, 1.3), (1.5, .8), (2.9, .5), (3.0, -1), (6.4, -1), (6.5, .5), (7.5, .9), (9, .5)], rng, .1), conc, bars=.5)
    ruin_wall(p, rng, (4.5, 4.5, 0), -X, 9, broken([(0, .5), (2.0, .25), (5.2, .2), (6.5, .9), (9, 1.4)], rng, .12), conc, bars=.5)
    # the slab, its beams and columns
    up = concrete(262, ground=-9, moss=.45, blot=.55)

    def edge(v):
        return 5.0 + .45 * float(noise2(v * .8, 4.4, 21))
    sheet(p, (-4.25, -4.25, SL), X, Y, 5.9, 4.05, .25, CONCRETE, mask=lambda u, v: u < max(edge(v), 1.7 if v > 3.2 else 0), sub=.8, arris=.02, rim='', fn=up)
    m = mark(p)
    for (x0, y0), (x1, y1) in (((-4.2, -.5), (.9, -.2)), ((.45, -4.2), (.75, -.2)), ((-2.8, -4.2), (-2.5, -.5)), ((-4.2, -2.4), (.5, -2.1))):
        gbox(p, (x0, y0, SL - .7), (x1, y1, SL - .25), CONCRETE, .8, .02, 'Z')
    paint(p, m, conc)
    column(p, (.6, -.35), .18, .18, 0, SL - .7, conc, rng, chamfer=.025, spalls=[(0, .5, 1.5, .2)], cap=False)
    column(p, (-2.65, -.35), .18, .18, 0, SL - .7, conc, rng, chamfer=.025, spalls=[(1, 1.6, 2.4, .16)], cap=False)
    column(p, (.6, -4.3), .18, .18, 0, SL - .7, conc, rng, chamfer=.025, cap=False)
    for v in np.arange(.3, 3.3, .45):
        if rng.uniform() < .75:
            rebar(p, rng, (-4.25 + edge(v) - .04, -4.25 + v, SL - rng.choice((.06, .19))), X, rng.uniform(.3, .9), droop=.6)
    # the stairs along the -x wall, and what is left of their rail
    solid_stair(p, -4.25, -2.65, y_foot, -1, N - 1, rise, run, concrete(263, damp=1.2, moss=.45, blot=.5))
    m = mark(p)
    handrail(p, [(-2.72, y_foot - run * (i + .5), rise * (i + 1)) for i in (0, 5, 10)], RUST, 1.0, 1.4, 0, base=False)
    paint(p, m, rusty(264))
    m = mark(p)
    rubble(p, rng, (2.6, 2.6), 1.4, 1.2, 26, (.15, .5))
    rubble(p, rng, (3.2, -3.2), 1.0, 1.0, 16, (.15, .45))
    rubble(p, rng, (-.8, 3.9), 1.6, .5, 12, (.12, .4))
    paint(p, m, concrete(265, damp=1.0, moss=.5, blot=.6, k=.92))
    for a, b, out, c in (((-4.5, 4.5, 0), (-4.5, -4.5, 0), -X, .4), ((-4.5, -4.5, 0), (4.5, -4.5, 0), -Y, .35), ((-4.25, 4.3, 0), (-4.25, y_foot, 0), X, .2),
                         ((-2.6, -4.25, 0), (4.2, -4.25, 0), Y, .3)):
        moss_line(p, rng, a, b, out, .06, .025, climb=c)
    for _ in range(9):
        moss_patch(p, rng, (rng.uniform(-4.1, .6), rng.uniform(-4.1, -.5), SL), rng.uniform(.08, .25), .016)
    for i in (1, 4, 8, 13):
        moss_patch(p, rng, (rng.uniform(-4.1, -2.9), y_foot - run * (i + .5), rise * (i + 1)), .09, .012)
    for q in ((-3.9, -3.9, SL), (.3, -3.8, SL), (3.9, 3.8, 0), (1.5, 1.0, 0), (-1.8, 2.6, 0), (3.6, -1.0, 0), (-4.0, 4.1, 0)):
        tuft(p, rng, q, rng.uniform(.3, .55), .5)
    sprig(p, rng, (2.4, 2.7, .25), 1.5, 11, (LEAF_GREEN, LEAF_LIGHT), BARK_BROWN, .02, .34)
    sprig(p, rng, (-.2, -3.6, SL), .9, 8, (LEAF_GREEN, LEAF_GOLD), BARK_BIRCH)
    ivy(p, rng, (-4.2, -4.53, 0), X, -Y, 5.5, 5.5, 50)
    ivy(p, rng, (-4.53, 1.0, 0), -Y, -X, 4.5, 4.6, 36)
    for q in p.v:              # leaf cards that droop under the ground plane stop at it
        q[2] = max(q[2], 0.0)
    return done(p, facts=dict(slab=dict(z=SL, x=(-4.25, .75), y=(-4.25, -.2), edge='ragged on +x, about x 0.75 +- 0.45; open (no rail) on its +x and +y edges'),
                              stairs=dict(x=(-4.25, -2.65), foot_y=round(y_foot, 3), head_y=-.2, risers=N, rise=round(rise, 4), tread=run, climbs='-y', width=1.6),
                              columns=[(.6, -.35), (-2.65, -.35), (.6, -4.3)], walls='-x and -y stand; +x and +y are stubs under 1.4 m with a gap on +x from y -1.5 to 1.9', top=7.0))


# ================================================================ the Field Camp
# Thessaly-4's camp: the prefab shelter the survey was issued, and the glasshouse she has kept going for forty years.
# Both are entered: floors are single flat faces, the doorways are open, the inner faces are modelled.

def film(fn, seed, amount=.5, north=(1.0, 0.0), ground=0.0, reach=.9, ramp=None):
    """The material fn under a green film: algae and moss on tops (in blotches), on the side that faces `north` and
    low down where the damp rises (amount 0..1). ramp = (x0, x1): the film on tops thickens from x0 toward x1 (a
    roof's shaded end)."""
    mg, md = _rgb(MOSS_GREEN), _rgb(MOSS_DEEP)

    def f(P, N):
        c = np.array(fn(P, N), np.float64)
        P, N, x, y, z = _pn(P, N)
        b1 = .5 + .5 * noise2(x / 1.1 + z * .3 + 4.0, y / 1.1 - z * .3, seed + 21)
        b2 = .5 + .5 * noise2(x / .25 + z, y / .25 - z, seed + 22)
        up = np.clip((N[:, 2] - .4) / .5, 0, 1)
        facing = np.clip(N[:, 0] * north[0] + N[:, 1] * north[1], 0, 1)
        g = np.clip(1 - (z - ground) / reach, 0, 1)
        top = np.clip(b1 * 1.8 - .55, 0, 1)
        if ramp is not None:
            t = np.clip((x - ramp[0]) / (ramp[1] - ramp[0]), 0, 1)
            top = np.clip(top * (.2 + 1.2 * t ** 1.3) + .5 * t ** 2 * b2, 0, 1)
        m = amount * (up * top + (1 - up) * (g ** 1.5 * (.3 + .7 * b2) * (.5 + .8 * facing) + .45 * facing * np.clip(b1 * 1.7 - .8, 0, 1)))
        m = np.clip(m, 0, .8)[:, None]
        c[:, :3] = c[:, :3] * (1 - m) + (mg * (1 - .6 * b2[:, None]) + md * (.6 * b2[:, None])) * m
        return c
    return f


def cloth(p, grid, colour, t=.006, slot=CLOTH):
    """A sheet of canvas through a grid of points (grid[i][j]; its front is the side from which i then j run
    counter-clockwise), with a back face t behind it so both sides show."""
    g = np.asarray(grid, np.float64)
    ni, nj = g.shape[:2]
    pts = g.reshape(-1, 3)
    faces = [[i * nj + j, (i + 1) * nj + j, (i + 1) * nj + j + 1, i * nj + j + 1] for i in range(ni - 1) for j in range(nj - 1)]
    n = unit(np.cross(g[-1, 0] - g[0, 0], g[0, -1] - g[0, 0]))
    p.add(pts, faces, colour, slot, True)
    p.add(pts - n * t, [f[::-1] for f in faces], colour, slot, True)


def glazing(p, rng, o, u, v, w, h, nx, ny, fn, keep=.7, bar_w=.03, bar_d=.045, tint=.45, skip=(), foot=0.0, slot=STEEL):
    """Glazing bars and old glass on the rectangle from o, w along u and h along v (it faces u x v; the members round
    it are the caller's): nx by ny panes. A pane keeps its glass with probability keep, is otherwise broken to shards
    left in its bars, or gone. skip: panes (i, j) left out altogether. foot: how green the lowest row's glass has
    gone at its bottom edge (0..1). Returns {(i, j): 'whole' | 'broken' | 'gone'}."""
    o, u, v = np.asarray(o, np.float64), unit(u), unit(v)
    f = np.cross(u, v)
    m = mark(p)
    for i in range(1, nx):
        a = o + u * (w * i / nx)
        bar(p, a, a + v * h, bar_w, bar_d, slot, f)
    for j in range(1, ny):
        a = o + v * (h * j / ny)
        bar(p, a, a + u * w, bar_w * .8, bar_d * .6, slot, f)
    paint(p, m, fn)
    gc, algae = tone(GLASS_GREEN, tint), mix(tone(GLASS_GREEN, tint), MOSS_DEEP, .6)
    e = bar_w / 2
    state = {}

    def at(a, b):
        return o + u * a + v * b + f * .006
    for i in range(nx):
        for j in range(ny):
            if (i, j) in skip:
                continue
            a0, a1 = w * i / nx + e, w * (i + 1) / nx - e
            b0, b1 = h * j / ny + e * .8, h * (j + 1) / ny - e * .8
            r = rng.uniform()
            c = vary(rng, gc if rng.uniform() < .75 else mix(gc, MOSS_DEEP, .45), .18)
            if r < keep:
                low = mix(c, algae, foot * rng.uniform(.5, 1)) if j == 0 and foot else c
                p.add([at(a0, b0), at(a1, b0), at(a1, b1), at(a0, b1)], [[0, 1, 2, 3]], [low, low, c, c], GLASS, False)
                state[(i, j)] = 'whole'
                continue
            state[(i, j)] = 'gone'
            if r > keep + (1 - keep) * .55:
                continue
            state[(i, j)] = 'broken'
            for _ in range(int(rng.integers(1, 4))):
                t0, t1 = np.sort(rng.uniform(0, 1, 2))
                reach, edge = rng.uniform(.15, .5), int(rng.integers(0, 4))
                if edge < 2:
                    b = b0 if edge == 0 else b1
                    q = [(a0 + (a1 - a0) * t0, b), (a0 + (a1 - a0) * t1, b), (a0 + (a1 - a0) * (t0 + t1) / 2, b + (b1 - b0) * reach * (1 if edge == 0 else -1))]
                else:
                    a = a0 if edge == 2 else a1
                    q = [(a, b0 + (b1 - b0) * t0), (a, b0 + (b1 - b0) * t1), (a + (a1 - a0) * reach * (1 if edge == 2 else -1), b0 + (b1 - b0) * (t0 + t1) / 2)]
                pts = [at(*qq) for qq in q]
                p.add(pts, [fl._facing(pts, [0, 1, 2], f)], c, GLASS, False)
    return state


def flowerpot(p, rng, c, r, h, soil=True, R=None, seed=0):
    """A clay pot standing at c (R tips it over): CONCRETE in terracotta, with a rolled rim; soil = filled (MOSS)."""
    m = mark(p)
    prof = [(r * .62, 0), (r * .92, h * .8), (r * 1.06, h * .8), (r * 1.06, h), (r * .93, h), (r * .88, h * .86)]
    turn(p, prof if soil else prof + [(r * .58, .02)], CONCRETE, 12)
    disc(p, (0, 0, 0), r * .62, CONCRETE, -Z, 12)
    if not soil:
        disc(p, (0, 0, .02), r * .58, CONCRETE, Z, 12)
    paint(p, m, flat(mix(RUST_ORANGE, SAND, .35), rng.uniform(.7, 1.0)))
    age(p, m, seed, ground=0.0, reach=h, floor=.7, grime=.3, moss=.5, scale=.25)
    if soil:
        disc(p, (0, 0, h * .86), r * .88, MOSS, Z, 12, tone(mix(SOIL, SOIL_DARK, rng.uniform(0, 1)), 1.0))
    place(p, m, R, c)


@mesh('SM_GN_Shelter', (6.0, 4.5, 3.2))
def shelter():
    """The camp's prefab field shelter, door to +x. A body 4.8 x 4.0 m (x -2.7 to 2.1, y -2 to 2) of olive sandwich
    panels in a steel frame on a skid base, its floor at z 0.12; a low ribbed gable roof (eaves 2.45, ridge 3.0 along
    x, gutters to y +-2.25) carrying solar panels on both slopes over its -x two thirds (one is gone), bare and
    mossy toward +x, with a vent cowl to 3.2. In the +x end the door opening, 1.3 m wide (y -0.65 to 0.65) and 2.25 m
    high above the floor, no leaf (a canvas flap is tied back beside it), a deck-plate ramp down to the ground
    (x 2.12 to 2.78) and a canvas awning on a tube frame out to x 3.0. A window in each long wall, a vent and a
    battery cabinet on the back (-x, to x -2.98). Inside: lined walls and ceiling, a bench with seed trays under a
    grow lamp along -y, shelving on the back wall, a camp cot along +y; the middle is clear."""
    rng = np.random.default_rng(2681)
    p = Part('SM_GN_Shelter', (PAINT, STEEL, TILE, CLOTH, GLASS, RUST, MOSS, LEAF, GLOW))
    X0, X1, HY, T, FL = -2.7, 2.1, 2.0, .08, .12
    EAVE, RIDGE, RT = 2.45, 3.0, .05
    DY, DH = .65, 2.25
    DT = FL + DH
    H = EAVE - FL
    ta = (RIDGE - EAVE) / HY
    ca, sa = 1 / math.hypot(1, ta), ta / math.hypot(1, ta)
    skin = film(steel(301, JUST_OLIVE, .12, ground=FL, damp=1.1, grime=.38, streak=.4), 302, .55, ground=FL)
    trim = film(steel(303, tone(JUST_OLIVE, .8), .17, ground=FL, damp=1.1, grime=.35, streak=.3), 302, .45, ground=FL)
    lining = steel(304, mix(JUST_BONE, CONCRETE_STAIN, .4), .1, ground=FL, damp=.8, k=.8, grime=.35, streak=.3)
    frame_fn = steel(305, STEEL_GREY, .32, ground=0, damp=.8)
    inside = steel(306, STEEL_GREY, .24, ground=FL, damp=.4)
    fixings = []                                   # (point, outward normal) of rivets, for the runs below them

    def roofline(y):
        return RIDGE - ta * abs(y)

    # ---- the skid base and the floor
    m = mark(p)
    gbox(p, (X1 - .12, -HY - .02, 0), (X1 + .02, HY + .02, FL), STEEL, .6, .01, 'z')
    gbox(p, (X0 - .02, -HY - .02, 0), (X0 + .12, HY + .02, FL), STEEL, .6, .01, 'z')
    for s in (-1, 1):
        ya, yb = sorted((s * (HY + .02), s * (HY - .12)))
        gbox(p, (X0 + .12, ya, 0), (X1 - .12, yb, FL), STEEL, .6, .01, 'z')
    paint(p, m, film(steel(308, STEEL_DARK, .5, ground=0, damp=.25, k=1.6), 309, .6, ground=0, reach=.2))
    m = mark(p)
    gquad(p, (X0 + .13, -HY + .13, FL), (X1 - .13, -HY + .13, FL), (X1 - .13, HY - .13, FL), (X0 + .13, HY - .13, FL), PAINT, 9, 8)   # to the rails' top faces, over their chamfers
    paint(p, m, steel(310, col(.16, .17, .15), .0, ground=-9, grime=.5, streak=0))
    pts = [(x, s * (HY + .02), FL * .5) for s in (-1, 1) for x in np.arange(X0 + .2, X1, .4)]
    for s in (-1, 1):
        bolts(p, [q for q in pts if q[1] * s > 0], s * Y, .013, RUST, tone(RUST_ORANGE, .8))
    for sx, x in ((1, X1 + .02), (-1, X0 - .02)):
        bolts(p, [(x, y, FL * .5) for y in np.arange(-1.8, 1.81, .4) if sx < 0 or abs(y) > .8], sx * X, .013, RUST, tone(RUST_ORANGE, .8))

    # ---- walls: an outer and an inner skin, cover strips on the panel joints, a head rail
    def wall(a, b, holes=(), strips=(), fn=skin):
        a, b = V3(*a), V3(*b)
        L = float(np.linalg.norm(b - a))
        u = (b - a) / L
        f = np.cross(u, Z)
        sheet(p, a, u, Z, L, H, T / 2, PAINT, holes=holes, sub=.6, back=False, rim='', arris=.006, fn=fn)
        sheet(p, b - f * T, -u, Z, L, H, T / 2, PAINT, holes=[(L - q[1], L - q[0], q[2], q[3]) for q in holes], sub=.8, back=False,
              rim='', arris=.006, fn=lining)
        R = np.stack([u, Z, f], 1)
        m = mark(p)
        riv = []
        for s in strips:
            gbox(p, (s - .03, 0, 0), (s + .03, H - .1, .008), PAINT, .5, .003, 'z')
            riv += [(s, zz, .008) for zz in np.arange(.14, H - .15, .4)]
        cuts = sorted((hh[0] - .07, hh[1] + .07) for hh in holes if hh[3] > H - .15)      # the head rail stops at a doorway's frame
        for u0, u1 in zip([0.0] + [c[1] for c in cuts], [c[0] for c in cuts] + [L]):
            gbox(p, (u0, H - .1, 0), (u1, H - .01, .014), PAINT, .6, .004, 'z')
            riv += [(q, H - .055, .014) for q in np.arange(u0 + .2, u1 - .1, .4)]
        place(p, m, R, a)
        paint(p, m, trim)
        riv = np.asarray(riv) @ R.T + a
        bolts(p, riv, f, .009, RUST, tone(RUST_ORANGE, .75), washer=False)
        fixings.extend((q, f) for q in riv)

    WIN = {-1: (1.5, 2.7, 1.18, 1.88), 1: (2.3, 3.5, 1.18, 1.88)}
    wall((X1, -HY, FL), (X1, HY, FL), [(HY - DY - .02, HY + DY + .02, 0, DH + .02)], (1.0, 3.0))
    wall((X0, HY, FL), (X0, -HY, FL), (), (1.0, 2.0, 3.0))
    wall((X0, -HY, FL), (X1, -HY, FL), [WIN[-1]], (1.2, 3.0, 3.6))
    wall((X1, HY, FL), (X0, HY, FL), [WIN[1]], (1.2, 2.0, 3.8))
    ys = np.linspace(-HY, HY, 11)
    for xo, sg, fn in ((X1, 1, skin), (X1 - T, -1, lining), (X0, -1, skin), (X0 + T, 1, lining)):
        m = mark(p)
        for ya, yb in zip(ys, ys[1:]):
            for z0, z1 in ((0.0, .5), (.5, 1.0)):
                q = [(xo, ya, EAVE + (roofline(ya) - EAVE) * z0), (xo, yb, EAVE + (roofline(yb) - EAVE) * z0),
                     (xo, yb, EAVE + (roofline(yb) - EAVE) * z1), (xo, ya, EAVE + (roofline(ya) - EAVE) * z1)]
                q = [q[k] for k in range(4) if k == 0 or np.linalg.norm(np.subtract(q[k], q[k - 1])) > 1e-6]
                if len(q) > 3 and np.linalg.norm(np.subtract(q[0], q[-1])) < 1e-6:
                    q = q[:-1]
                if len(q) >= 3:
                    face(p, q, PAINT, sg * X)
        paint(p, m, fn)
    m = mark(p)                                     # corner posts
    for sx, xc in ((1, X1), (-1, X0)):
        for sy in (-1, 1):
            xa, xb = sorted((xc + sx * .015, xc - sx * .095))
            ya, yb = sorted((sy * (HY + .015), sy * (HY - .095)))
            gbox(p, (xa, ya, FL), (xb, yb, EAVE - .012), STEEL, .6, .012, 'z')
    paint(p, m, frame_fn)

    # ---- the doorway: a pressed frame, a threshold, the tied-back flap, the ramp
    m = mark(p)
    for sy in (-1, 1):
        ya, yb = sorted((sy * DY, sy * (DY + .07)))
        gbox(p, (X1 - T - .012, ya, FL), (X1 + .022, yb, DT), STEEL, .6, .008, 'z')
    gbox(p, (X1 - T - .012, -DY - .07, DT), (X1 + .022, DY + .07, DT + .07), STEEL, .6, .008)
    gbox(p, (X1 - .13, -DY, FL), (X1 + .02, DY, FL + .006), STEEL, .5, .002, 'z')
    for z in (FL + .35, FL + 1.15, FL + 1.95):      # the leaf's hinge pins, left on the +y jamb
        turn(p, [(0, -.05), (.014, -.05), (.014, .05), (0, .05)], STEEL, 8, (X1 + .034, DY + .035, z))
    RX = 2.78
    gface(p, (X1 + .02, -.75, FL), (RX, -.75, .012), (RX, .75, .012), (X1 + .02, .75, FL), STEEL, .33, V3(.1, 0, 1))
    for sy in (-1, 1):
        face(p, [(X1 + .02, sy * .75, 0), (RX, sy * .75, 0), (RX, sy * .75, .012), (X1 + .02, sy * .75, FL)], STEEL, sy * Y)
    face(p, [(RX, -.75, 0), (RX, .75, 0), (RX, .75, .012), (RX, -.75, .012)], STEEL, X)
    rn = unit(V3(FL - .012, 0, RX - X1 - .02))
    for x in np.arange(X1 + .1, RX - .03, .09):
        z = FL + (.012 - FL) * (x - X1 - .02) / (RX - X1 - .02)
        bar(p, (x, -.7, z + .002), (x, .7, z + .002), .018, .005, STEEL, rn)
    paint(p, m, steel(311, STEEL_GREY, .45, ground=0, damp=.5))
    m = mark(p)
    flap = mix(CANVAS, JUST_OLIVE, .45)
    zs = np.linspace(DT + .02, FL + .22, 9)
    pipe(p, [(X1 + .1 + .012 * math.sin(k * 2.1), -DY - .17 + .015 * math.cos(k * 1.7), z) for k, z in enumerate(zs)],
         [.05, .075, .095, .1, .06, .1, .12, .115, .09], CLOTH, 10, [tone(flap, .8 + .2 * math.sin(k * 2.3) ** 2) for k in range(9)])
    hoop(p, (X1 + .1, -DY - .17, zs[4]), .062, .009, CLOTH, Z, 12, 6, tone(ROPE, .7))
    age(p, m, 312, ground=FL, reach=1.6, floor=.6, grime=.3, streak=.25, moss=.25)

    # ---- the roof: two ribbed slopes, lined beneath, with purlins; the solar array; ridge, gutters, a vent
    SL = 2.14 / ca
    XA, XB = X0 - .1, X1 + .08
    roof = film(steel(313, STEEL_GREY, .29, ground=EAVE - .3, damp=.5, grime=.3), 314, .8, ground=-9, ramp=(-.4, 2.2))
    alu = steel(315, mix(STEEL_GREY, JUST_BONE, .3), .12, ground=-9, grime=.3)

    def cells_fn(P, N):                             # solar cells: dark blue, dulled by dust and droppings
        P, N, x, y, z = _pn(P, N)
        b1 = .5 + .5 * noise2(x / .7 + 2.0, y / .7 + z, 316)
        b2 = .5 + .5 * noise2(x / .13, y / .13, 317)
        dust = (.35 * np.clip(b1 * 1.6 - .5, 0, 1) * (.5 + .5 * b2))[:, None]
        return _out(_rgb(SOLAR) * (1.05 - .3 * b2)[:, None] * (1 - dust) + _rgb(CONCRETE_STAIN) * .5 * dust)
    PANELS = (-2.55, -1.52, -.49)
    panels = []
    for s in (1, -1):
        R = np.stack([s * X, V3(0, s * ca, -sa), V3(0, s * sa, ca)], 1)
        o = V3(0, 0, RIDGE)
        la, lb = sorted((s * XA, s * XB))
        m = mark(p)
        gbox(p, (la, 0, 0), (lb, SL, RT), STEEL, .4, .008, 'z')
        for xr in np.linspace(la + .06, lb - .06, 14):
            gbox(p, (xr - .02, .02, RT), (xr + .02, SL - .01, RT + .03), STEEL, .6, .006, 'z')
        place(p, m, R, o)
        paint(p, m, roof)
        m = mark(p)
        gface(p, (la, 0, 0), (lb, 0, 0), (lb, SL, 0), (la, SL, 0), PAINT, .6, -Z)
        place(p, m, R, o)
        paint(p, m, lining)
        m = mark(p)
        ia, ib = sorted((s * (X0 + T), s * (X1 - T)))
        for sp in (.72, 1.45):
            gbox(p, (ia, sp - .025, -.06), (ib, sp + .025, 0), STEEL, .8, .006, 'Z')
        place(p, m, R, o)
        paint(p, m, inside)
        m = mark(p)
        ra, rb = sorted((s * (PANELS[0] - .06), s * (PANELS[-1] + 1.06)))
        for sr in (.6, 1.6):
            gbox(p, (ra, sr - .02, RT + .03), (rb, sr + .02, RT + .05), STEEL, .7, .004)
        tops = []
        for k, x0 in enumerate(PANELS):
            if s > 0 and k == 2:                    # this one was taken away: its rails stand empty
                continue
            a, b = sorted((s * x0, s * (x0 + 1.0)))
            gbox(p, (a, .3, RT + .05), (b, 1.9, RT + .085), STEEL, .8, .006)
            tops.append((a, b))
            panels.append(dict(x=(x0, x0 + 1.0), side='+y' if s > 0 else '-y'))
        place(p, m, R, o)
        paint(p, m, alu)
        m = mark(p)
        for a, b in tops:
            gface(p, (a + .025, .325, RT + .087), (b - .025, .325, RT + .087), (b - .025, 1.875, RT + .087), (a + .025, 1.875, RT + .087), TILE, .27, Z)
        place(p, m, R, o)
        paint(p, m, cells_fn)
    m = mark(p)
    zc = RIDGE + .1
    angle(p, (XA - .02, 0, zc), (XB + .02, 0, zc), .17, STEEL, V3(0, ca, -sa), V3(0, -ca, -sa))
    for s in (-1, 1):
        channel(p, (XA, s * 2.2, EAVE - .09), (XB, s * 2.2, EAVE - .09), .09, .06, STEEL, Y, -1)
        for x in np.arange(XA + .3, XB, .9):         # gutter brackets off the head rail
            bar(p, (x, s * (HY + .01), EAVE - .1), (x, s * 2.2, EAVE - .1), .025, .006, STEEL, Z)
    paint(p, m, roof)
    m = mark(p)
    gbox(p, (X0 + T, -.035, RIDGE - .11), (X1 - T, .035, RIDGE - .012), STEEL, .8, .006)      # the ridge beam inside
    for s in (-1, 1):                                # and a wall plate closing each long wall's head against the lining
        ya, yb = sorted((s * (HY - T - .04), s * (HY - T + .012)))
        gbox(p, (X0 + T, ya, EAVE - .06), (X1 - T, yb, EAVE + .021), STEEL, .8, .006)
    paint(p, m, inside)
    vz = roofline(.8) + RT / ca - .01
    vent_stack(p, (1.35, .8, vz), .07, 3.2 - .22 - vz, frame_fn)
    for s in (-1, 1):
        downpipe(p, (-2.2, s * HY, EAVE - .1), .06, s * Y, frame_fn, .032)

    # ---- the awning: a tube frame off a wall plate, struts, old canvas with a scalloped valance
    AW, AX, AZ0, AZ1 = 1.0, 2.975, 2.65, 2.44          # the valance hangs to 2.31: clear of the doorway's 2.37 for anyone walking in
    b0, b1 = V3(X1 + .045, 0, AZ0), V3(AX, 0, AZ1)
    m = mark(p)
    gbox(p, (X1, -AW - .05, AZ0 - .04), (X1 + .02, AW + .05, AZ0 + .04), STEEL, .6, .005, 'x')
    for q in (b0, b1):
        pipe(p, [q - Y * AW, q + Y * AW], .016, STEEL, 8)
    for sy in (-1, 0, 1):
        pipe(p, [b0 + Y * sy * AW, b1 + Y * sy * AW], .016 if sy else .012, STEEL, 8)
    for sy in (-1, 1):
        foot = V3(X1, sy * AW, 1.95)
        gbox(p, foot - V3(0, .04, .06), foot + V3(.015, .04, .06), STEEL, 9, .004, 'x')
        pipe(p, [foot + X * .015, b0 + (b1 - b0) * .78 + Y * sy * AW], .012, STEEL, 6)
    paint(p, m, frame_fn)
    bolts(p, [(X1 + .02, y, AZ0) for y in np.linspace(-AW, AW, 6)], X, .012, RUST, tone(RUST_ORANGE, .8))
    m = mark(p)
    canvas = mix(CANVAS, JUST_OLIVE, .5)
    ni, nj = 7, 11
    grid = np.zeros((ni, nj, 3))
    for i in range(ni):
        for j in range(nj):
            t, sy = i / (ni - 1), 2 * j / (nj - 1) - 1
            grid[i, j] = b0 + (b1 - b0) * t + Y * sy * AW + Z * (.02 - .075 * math.sin(math.pi * t) * (1 - min(abs(sy) * 2 % 2, 2 - abs(sy) * 2 % 2) ** 2 * .6))
    cloth(p, grid, canvas)
    yv = np.linspace(-AW, AW, 2 * 8 + 1)
    val = np.array([[(AX + .02, y, AZ1 + .02), (AX + .024, y, AZ1 - (.08 if k % 2 == 0 else .13))] for k, y in enumerate(yv)])
    cloth(p, np.swapaxes(val, 0, 1)[::-1], canvas, .004)
    age(p, m, 318, ground=1.2, reach=1.6, floor=.72, grime=.38, streak=.25, moss=.6, scale=.6)

    # ---- windows, the door's lamp, the back wall's vent and battery cabinet
    for s, (u0, u1, v0, v1) in WIN.items():
        a, u = (V3(X0, -HY, FL), X) if s < 0 else (V3(X1, HY, FL), -X)
        window(p, a + u * u0 + Z * v0, u, u1 - u0, v1 - v0, frame_fn, rng, depth=.012, bar=.035, nx=2, ny=1, glass=.75, back=0)
    bulkhead(p, (X1, .95, 2.0), X, STEEL, GLOW_AMBER, .08, .7)
    m = mark(p)
    conduit(p, [(X1 + .014, .95, 2.1), (X1 + .014, .95, EAVE - .12)], X, STEEL, .012, .3)
    paint(p, m, frame_fn)
    louvre(p, (X0, .25, 2.52), -Y, .5, .28, frame_fn, STEEL, 5, .05)
    m = mark(p)
    gbox(p, (X0 - .24, -1.6, .55), (X0, -.9, 1.5), PAINT, .35, .012, 'X')
    gbox(p, (X0 - .252, -1.56, .6), (X0 - .24, -.94, 1.46), PAINT, .35, .004, 'X')
    gbox(p, (X0 - .28, -1.63, 1.5), (X0, -.87, 1.522), PAINT, .4, .006, 'X')
    paint(p, m, trim)
    m = mark(p)
    for z in (.75, 1.3):
        turn(p, [(0, -.05), (.012, -.05), (.012, .05), (0, .05)], STEEL, 8, (X0 - .256, -1.56, z))
    pipe(p, [(X0 - .252, -1.0, .98), (X0 - .275, -1.0, .98), (X0 - .275, -1.0, 1.1), (X0 - .252, -1.0, 1.1)], .008, STEEL, 6)
    conduit(p, [(X0 - .016, -1.25, 1.522), (X0 - .016, -1.25, EAVE - .12)], -X, STEEL, .016, .3)
    conduit(p, [(X0 - .016, -1.4, .55), (X0 - .016, -1.4, FL + .02)], -X, STEEL, .016, .3)
    paint(p, m, frame_fn)

    # ---- inside: the bench with its seed trays and grow lamp, shelving, the cot
    BX0, BX1, BY0, BY1, BT = -2.2, .4, -HY + T + .02, -1.3, FL + .9
    m = mark(p)
    for x in (BX0 + .03, (BX0 + BX1) / 2, BX1 - .03):
        for y in (BY0 + .03, BY1 - .03):
            gbox(p, (x - .02, y - .02, FL), (x + .02, y + .02, BT - .04), STEEL, .5, .004, 'zZ')
    for y in (BY0 + .03, BY1 - .03):
        gbox(p, (BX0, y - .012, BT - .11), (BX1, y + .012, BT - .04), STEEL, .7, .004)
        gbox(p, (BX0, y - .012, FL + .2), (BX1, y + .012, FL + .25), STEEL, .7, .004)
    gbox(p, (BX0 + .01, BY0 + .02, FL + .25), (BX1 - .01, BY1 - .02, FL + .265), STEEL, .5, .004)
    paint(p, m, inside)
    m = mark(p)
    gbox(p, (BX0 - .03, BY0, BT - .04), (BX1 + .03, BY1 + .03, BT), PAINT, .35, .008)
    paint(p, m, steel(319, mix(JUST_BONE, JUST_OLIVE, .35), .12, ground=BT - .3, damp=.3, grime=.45, k=.85))
    trays = []
    for k, x in enumerate((-1.78, -1.12, -.46)):
        m = mark(p)
        gbox(p, (x - .28, -1.83, BT), (x + .28, -1.45, BT + .06), PAINT, 9, .008, 'z')
        paint(p, m, flat(JUST_GRAPHITE, 1.6))
        gface(p, (x - .262, -1.812, BT + .05), (x + .262, -1.812, BT + .05), (x + .262, -1.468, BT + .05), (x - .262, -1.468, BT + .05), MOSS, .14, Z,
              tone(mix(SOIL, SOIL_DARK, .4), 1.0))
        for _ in range(11 if k < 2 else 4):
            q = (x + rng.uniform(-.23, .23), rng.uniform(-1.79, -1.49), BT + .05)
            tuft(p, rng, q, rng.uniform(.07, .16), rng.uniform(.08, .13), 2, (LEAF_LIGHT, LEAF_GREEN), fl.CELL_SMALLLEAF)
        trays.append((x, -1.64, BT + .05))
    m = mark(p)                                     # a tool box and a tin on the bench, two crates under it
    gbox(p, (-.05, -1.8, BT), (.33, -1.55, BT + .16), PAINT, .2, .01, 'z')
    gbox(p, (-.06, -1.81, BT + .16), (.34, -1.54, BT + .19), PAINT, .2, .008)
    for xa, xb, h in ((BX0 + .12, BX0 + .78, .36), (BX0 + .95, BX0 + 1.5, .3)):
        gbox(p, (xa, BY0 + .05, FL + .265), (xb, BY1 - .06, FL + .265 + h), PAINT, .25, .012, 'z')
        gbox(p, (xa - .012, BY0 + .04, FL + .265 + h), (xb + .012, BY1 - .05, FL + .3 + h), PAINT, .25, .008)
    paint(p, m, steel(320, JUST_OLIVE, .16, ground=FL, damp=.5, grime=.4, k=.9))
    m = mark(p)
    pipe(p, [(.13, -1.675, BT + .19), (.13, -1.675, BT + .22), (.15, -1.675, BT + .22)], .008, STEEL, 6)
    turn(p, [(.06, 0), (.06, .14), (.05, .15), (.02, .15)], STEEL, 12, (-2.05, -1.5, BT))
    disc(p, (-2.05, -1.5, BT + .15), .02, STEEL, Z, 8)
    GZ = BT + .74                                    # the grow lamp: a hood hung from the ceiling over the trays
    gbox(p, (-2.05, -1.74, GZ), (-.2, -1.54, GZ + .05), STEEL, .6, .008)
    for x in (-1.85, -.4):
        pipe(p, [(x, -1.64, GZ + .05), (x, -1.64, roofline(1.64) - .002)], .004, STEEL, 4, cap=False)
    pipe(p, [(-2.05, -1.64, GZ + .03), (-2.3, -1.64, GZ + .03), (-2.4, -1.75, GZ - .1), (-2.5, -HY + T + .012, GZ - .25), (-2.5, -HY + T + .012, FL + .5)], .006, STEEL, 5)
    paint(p, m, inside)
    gface(p, (-2.03, -1.72, GZ - .002), (-.22, -1.72, GZ - .002), (-.22, -1.56, GZ - .002), (-2.03, -1.56, GZ - .002), GLOW, 9, -Z, tone(GLOW_WARM, .9))
    SX0, SX1, SY0, SY1 = X0 + T + .02, -2.2, -1.0, 1.1
    SHZ = (FL + .3, FL + .8, FL + 1.3, FL + 1.8)
    m = mark(p)
    for y in (SY0 + .018, SY1 - .018):
        for x in (SX0 + .018, SX1 - .018):
            gbox(p, (x - .018, y - .018, FL), (x + .018, y + .018, FL + 2.0), STEEL, .6, .004, 'z')
    for z in SHZ:
        gbox(p, (SX0, SY0, z - .02), (SX1, SY1, z), STEEL, .5, .004)
    for a, b in (((SX0 + .004, SY0, FL + .3), (SX0 + .004, SY1, FL + 1.8)), ((SX0 + .004, SY1, FL + .3), (SX0 + .004, SY0, FL + 1.8))):
        bar(p, a, b, .025, .004, STEEL, X)
    paint(p, m, inside)
    kit_cols = (JUST_OLIVE, mix(JUST_BONE, STEEL_GREY, .4), tone(JUST_OLIVE, .7), mix(JUST_ORANGE, RUST_DARK, .5))
    for zi, z in enumerate(SHZ):
        y = SY0 + .07
        while y < SY1 - .3:
            kind = rng.uniform()
            if kind < .5:
                w, h = rng.uniform(.25, .45), rng.uniform(.14, .3)
                m = mark(p)
                gbox(p, (SX0 + .03, y, z), (SX1 - .03, y + w, z + h), PAINT, .25, .008, 'z')
                gbox(p, (SX0 + .022, y - .008, z + h), (SX1 - .022, y + w + .008, z + h + .025), PAINT, .25, .006)
                paint(p, m, steel(321 + int(y * 50) + zi, kit_cols[int(rng.integers(0, 4))], .12, ground=z, damp=.3, grime=.4, k=.9))
                y += w + rng.uniform(.04, .12)
            elif kind < .8:
                r, h = rng.uniform(.05, .085), rng.uniform(.16, .26)
                m = mark(p)
                xc = (SX0 + SX1) / 2 + rng.uniform(-.08, .08)
                turn(p, [(r, 0), (r, h), (r * .7, h + .015), (r * .7, h + .04)], STEEL, 12, (xc, y + r, z))
                disc(p, (xc, y + r, z + h + .04), r * .7, STEEL, Z, 12)
                paint(p, m, steel(350 + zi, STEEL_GREY, .3, ground=z, damp=.3))
                y += 2 * r + rng.uniform(.03, .1)
            else:
                w, r = rng.uniform(.3, .5), rng.uniform(.055, .075)
                m = mark(p)
                pipe(p, [((SX0 + SX1) / 2, y, z + r), ((SX0 + SX1) / 2, y + w, z + r)], r, CLOTH, 10, vary(rng, mix(CANVAS, (JUST_OLIVE, TARP_OCHRE)[int(rng.integers(0, 2))], .5), .15))
                age(p, m, 360 + zi, ground=z, reach=.3, floor=.75, grime=.3)
                y += w + rng.uniform(.04, .12)
    CX0, CX1, CY0, CY1, CZ = -2.3, -.35, 1.22, HY - T - .03, FL + .38
    m = mark(p)
    for y in (CY0, CY1):
        pipe(p, [(CX0, y, CZ), (CX1, y, CZ)], .014, STEEL, 8)
    for x in (CX0 + .1, (CX0 + CX1) / 2, CX1 - .1):
        pipe(p, [(x, CY0, CZ), (x, CY0 + .07, FL + .014), (x, CY1 - .07, FL + .014), (x, CY1, CZ)], .012, STEEL, 6)
    paint(p, m, inside)
    m = mark(p)
    grid = np.array([[(CX0 + (CX1 - CX0) * i / 8, CY0 + (CY1 - CY0) * j / 4, CZ + .014 - .045 * math.sin(math.pi * j / 4) * (.6 + .4 * math.sin(math.pi * i / 8)))
                      for j in range(5)] for i in range(9)])
    cloth(p, grid, mix(CANVAS, JUST_OLIVE, .3))
    gbox(p, (CX0 + .08, CY0 + .07, CZ - .025), (CX0 + .55, CY1 - .07, CZ + .07), CLOTH, .16, .025, colour=mix(TARP_OCHRE, CANVAS, .45))
    age(p, m, 370, ground=FL, reach=.5, floor=.8, grime=.4, scale=.5)

    # ---- forty years: runs under the fixings, moss at the foot and on the roof's north end, grass, ivy
    pick = rng.choice(len(fixings), 26, replace=False)
    for k in pick:
        q, f = fixings[k]
        if q[2] > .7:
            streaks(p, rng, [q - Z * .012], f, (.2, .7), (.025, .05))
    streaks(p, rng, [(x, -HY, FL + 1.14) for x in (X0 + 1.52, X0 + 2.68)] + [(X0 + 1.2, -HY, EAVE - .11)], -Y, (.3, .8), (.03, .06))
    streaks(p, rng, [(X1 - 2.32, HY, FL + 1.14), (X1 - 3.48, HY, FL + 1.14), (.9, HY, EAVE - .11)], Y, (.3, .8), (.03, .06))
    streaks(p, rng, [(X0 - .24, -1.5, .55), (X0 - .24, -1.05, .55)], -X, (.15, .4), (.03, .05))
    streaks(p, rng, [(X1, s * (AW + .03), AZ0 - .04) for s in (-1, 1)] + [(X1, s * AW, 1.89) for s in (-1, 1)], X, (.25, .6), (.03, .05))
    for a, b, out, climb in (((X1 + .02, -HY - .02, 0), (X1 + .02, -.78, 0), X, .1), ((X1 + .02, .78, 0), (X1 + .02, HY + .02, 0), X, .1),
                             ((X0 - .02, -HY - .02, 0), (X1 + .02, -HY - .02, 0), -Y, .06), ((X1 + .02, HY + .02, 0), (X0 - .02, HY + .02, 0), Y, .06),
                             ((X0 - .02, HY + .02, 0), (X0 - .02, -HY - .02, 0), -X, .05)):
        moss_line(p, rng, a, b, out, .055, .025, climb=climb)
    for _ in range(64):
        x = XB - .1 - abs(rng.normal(0, .8))
        s = rng.choice((-1, 1))
        yy = rng.uniform(.2, 2.05)
        if x < .62 or (s > 0 and abs(x - 1.35) < .2 and abs(yy - .8) < .2):
            continue
        moss_patch(p, rng, (x, s * yy, roofline(yy) + RT / ca), rng.uniform(.03, .085), .018, V3(0, s * sa, ca), 7)
    for s in (-1, 1):
        moss_line(p, rng, (.3, s * 2.165, EAVE - .082), (XB - .05, s * 2.165, EAVE - .082), s * Y, .05, .03, step=.25)
    for _ in range(18):
        side = int(rng.integers(0, 4))
        t = rng.uniform(-1, 1)
        q = [(X1 + .08, t * HY), (X0 - .07, t * HY), (t * 2.4 - .3, HY + .07), (t * 2.4 - .3, -HY - .07)][side]
        if side == 0 and abs(q[1]) < .95 or side == 1 and -1.7 < q[1] < -.8:
            continue
        tuft(p, rng, (q[0], q[1], 0), rng.uniform(.22, .45), rng.uniform(.25, .38))
    ivy(p, rng, (X0 - .03, .5, 0), Y, -X, 1.45, 2.1, 26, size=.36)
    ivy(p, rng, (X0 + .05, HY + .03, 0), X, Y, 1.2, 1.6, 16, size=.34)
    for q in p.v:              # leaf cards that droop under the ground plane stop at it
        q[2] = max(q[2], 0.0)
    return done(p, facts=dict(
        door=dict(face_x=X1, centre=(X1, 0.0, FL), y=(-DY, DY), z=(FL, DT), width=2 * DY, height=DH, leaf='none: an open doorway'),
        floor_z=FL, ramp=dict(x=(X1 + .02, RX), y=(-.75, .75), z=(FL, .012)),
        interior=dict(x=(X0 + T, X1 - T), y=(-HY + T, HY - T), ceiling='2.45 at the walls to 3.0 under the ridge (a ridge beam down to 2.89)'),
        clear=dict(x=(-2.15, X1 - T), y=(-1.25, 1.17), z=(FL, 2.6)), stand=[(.9, 0.0, FL), (-.6, -.2, FL), (-1.5, .2, FL)],
        bench=dict(x=(BX0 - .03, BX1 + .03), y=(BY0, BY1 + .03), top=BT, trays=trays, lamp_z=GZ),
        shelving=dict(x=(SX0, SX1), y=(SY0, SY1), shelves_z=SHZ, top=FL + 2.0), cot=dict(x=(CX0, CX1), y=(CY0, CY1), top=CZ),
        windows=dict(minus_y=dict(x=(X0 + 1.5, X0 + 2.7), z=(FL + 1.18, FL + 1.88)), plus_y=dict(x=(X1 - 3.5, X1 - 2.3), z=(FL + 1.18, FL + 1.88))),
        awning=dict(x=(X1, 3.0), y=(-AW, AW), underside=round(AZ1 - .13, 3)), lamp=(X1 + .08, .95, 2.0), cabinet=dict(x=(X0 - .28, X0), y=(-1.63, -.87), z=(.55, 1.52)),
        eaves_z=EAVE, ridge_z=RIDGE, solar=panels, top=3.2))


@mesh('SM_GN_Greenhouse', (9.0, 6.0, 4.2))
def greenhouse():
    """The camp's glasshouse, 9 x 6 m on a concrete slab (top at z 0.05), door to +x. A dwarf wall 0.6 m high carries
    seven steel portal ribs at 1.45 m (posts to the eaves at 2.4, rafters to the ridge at 4.08 along x, tie rods at
    2.46) and glazing bars with old glass, some of it broken or gone; a roof vent stands open on each slope. In the +x
    gable the doorway, 1.5 m wide (y -0.75 to 0.75) and 2.3 m high, its sliding leaf run open along the outside toward
    +y. Inside, an aisle 1.7 m wide along x between four raised beds (kerbs 0.42 m high) of saplings, a potting bench
    across the -x end, a water butt by the door, irrigation pipes hung from the rafters over the beds."""
    rng = np.random.default_rng(2682)
    p = Part('SM_GN_Greenhouse', (CONCRETE, STEEL, GLASS, RUST, BRASS, MOSS, BARK, LEAF))
    HX, HY, FL, PL, EV, RG = 4.5, 3.0, .05, .6, 2.4, 4.08
    GX, GY, PT = 4.35, 2.85, .18
    PX, PY = HX - .06, HY - .06
    DY, DT = .75, 2.35
    ta = (RG - EV) / GY
    ca, sa = 1 / math.hypot(1, ta), ta / math.hypot(1, ta)
    RL = math.hypot(GY, RG - EV)
    conc = concrete(381, damp=1.0, moss=.55, blot=.5, streak=.35, north=(1.0, 0.0))
    rf = steel(382, STEEL_GREY, .55, ground=0, damp=3.2)
    bars = steel(383, mix(STEEL_GREY, JUST_BONE, .3), .5, ground=0, damp=3.0)
    rust = rusty(384)
    xs = np.linspace(-GX, GX, 7)
    BAY = float(xs[1] - xs[0])

    def rafter_z(y):
        return RG - ta * abs(y)

    # ---- the slab and the dwarf wall with its steel sill
    sheet(p, (-HX, -HY, FL), X, Y, 2 * HX, 2 * HY, FL, CONCRETE, ju=np.arange(1.5, 8.9, 1.5), jv=(HY - .8, HY + .8), groove=(.02, .008), sub=.75,
          back=False, rim='lrbt', arris=.012, fn=concrete(380, damp=.6, moss=.5, blot=.6))
    runs = [((-PX, -PY), (PX, -PY), 'tlr'), ((PX, PY), (-PX, PY), 'tlr'), ((-PX, PY - PT), (-PX, -PY + PT), 't'),
            ((PX, -PY + PT), (PX, -DY - .06), 'tr'), ((PX, DY + .06), (PX, PY - PT), 'tl')]
    for a, b, rim in runs:
        a, b = V3(*a, FL), V3(*b, FL)
        L = float(np.linalg.norm(b - a))
        sheet(p, a, (b - a) / L, Z, L, PL - FL, PT, CONCRETE, ju=np.arange(1.48, L - .5, 1.48), sub=.5, back=True, rim=rim, fn=conc)
    m = mark(p)
    for s in (-1, 1):
        ya, yb = sorted((s * (PY + .02), s * (PY - PT - .02)))
        gbox(p, (-PX - .02, ya, PL), (PX + .02, yb, PL + .03), STEEL, .7, .008)
    gbox(p, (-PX - .02, -PY + PT + .02, PL), (-PX + PT + .02, PY - PT - .02, PL + .03), STEEL, .7, .008)
    for ya, yb in ((-PY + PT + .02, -DY - .06), (DY + .06, PY - PT - .02)):
        gbox(p, (PX - PT - .02, ya, PL), (PX + .02, yb, PL + .03), STEEL, .7, .008)
    paint(p, m, rf)

    # ---- the ribs: posts on base plates, rafters, knee plates, eave and ridge members, tie rods
    m = mark(p)
    anchor, knee = [], []
    for i, x in enumerate(xs):
        for s in (-1, 1):
            ibeam(p, (x, s * GY, PL + .04), (x, s * GY, EV), .09, .06, STEEL, Y)
            ibeam(p, (x, s * GY, EV), (x, 0, RG), .09, .06, STEEL, Z)
            gbox(p, (x - .07, s * GY - .075, PL + .03), (x + .07, s * GY + .075, PL + .042), STEEL, 9, .003, 'z')
            anchor += [(x + sx * .05, s * GY + sy * .055, PL + .042) for sx in (-1, 1) for sy in (-1, 1)]
            yk = s * (GY - .045)
            tri = [(x, yk, EV - .42), (x, yk, EV - .02), (x, s * (GY - .6), rafter_z(GY - .6) - .06)]
            plate(p, tri, .008, STEEL)
            knee.append([np.mean(tri, 0) + (np.asarray(q) - np.mean(tri, 0)) * .55 for q in tri])
    for s in (-1, 1):
        ya, yb = sorted((s * (GY - .045), s * (GY + .045)))
        gbox(p, (-GX - .03, ya, EV - .05), (GX + .03, yb, EV + .04), STEEL, 1.0, .008)
        gbox(p, (-GX, ya + .01, PL + .042), (GX, yb - .01, PL + .08), STEEL, 1.0, .006)
    gbox(p, (-GX - .03, -.035, RG - .075), (GX + .03, .035, RG + .045), STEEL, 1.0, .008)
    angle(p, (-GX - .05, 0, RG + .075), (GX + .05, 0, RG + .075), .1, STEEL, V3(0, ca, -sa), V3(0, -ca, -sa))
    for x in (-GX - .03, GX + .03):                   # finials on the gable peaks
        turn(p, [(.03, 0), (.03, .02), (.012, .035), (.028, .06), (.03, .075), (.01, .1), (.004, .125)], STEEL, 8, (x * .995, 0, RG - .005))
        disc(p, (x * .995, 0, RG + .12), .004, STEEL, Z, 8)
    for s in (-1, 1):
        channel(p, (-GX - .06, s * 2.945, EV - .02), (GX + .06, s * 2.945, EV - .02), .09, .06, STEEL, Y, -1)
        pipe(p, [(-GX - .02, s * 2.945, EV - .03), (-GX - .02, s * 2.945, EV - .12), (-GX - .02, s * 2.975, EV - .22)], .03, STEEL, 8)
    paint(p, m, rf)
    bolts(p, anchor, Z, .011, RUST, tone(RUST_ORANGE, .8))
    for sx in (-1, 1):
        bolts(p, [q + sx * X * .004 for tri in knee for q in tri], sx * X, .011, RUST, tone(RUST_ORANGE, .8), washer=False)
    m = mark(p)
    for x in xs[1:-1]:
        pipe(p, [(x, -GY + .04, EV + .06), (x, GY - .04, EV + .06)], .011, RUST, 6)
        pipe(p, [(x, 0, EV + .06), (x, 0, RG - .075)], .008, RUST, 5, cap=False)
        turn(p, [(0, -.06), (.02, -.06), (.02, .06), (0, .06)], RUST, 6, (x, 0, EV + .06), Y)
    paint(p, m, rust)

    # ---- glass: the long walls and the roof, bay by bay; two roof vents propped open
    WZ, WH = PL + .08, EV - .05 - PL - .08
    VENTS = {(-1, 2), (1, 4)}
    panes = dict(whole=0, broken=0, gone=0)

    def tally(st):
        for v in st.values():
            panes[v] += 1
    for i in range(6):
        w = BAY - .07
        for s in (-1, 1):
            u = -s * X
            x0 = xs[i + 1] - .035 if s > 0 else xs[i] + .035
            tally(glazing(p, rng, (x0, s * GY, WZ), u, Z, w, WH, 3, 2, bars, keep=.74, foot=.8))
            v = V3(0, -s * ca, sa)
            o = V3(x0, s * GY, EV) + v * .07
            h = RL - .07 - .06
            vent = (s, i) in VENTS
            tally(glazing(p, rng, o, u, v, w, h, 3, 3, bars, keep=.68, skip={(k, 2) for k in range(3)} if vent else ()))
            if vent:
                f = np.cross(u, v)
                hl, th = h / 3, math.radians(24)
                v2 = unit(v * math.cos(th) - f * math.sin(th))
                top = o + v * h
                o2 = top - v2 * hl
                f2 = np.cross(u, v2)
                m = mark(p)
                for a, b in ((o2, o2 + u * w), (top, top + u * w), (o2, top), (o2 + u * w, top + u * w)):
                    bar(p, a, b, .035, .04, STEEL, f2)
                paint(p, m, bars)
                tally(glazing(p, rng, o2, u, v2, w, hl, 3, 1, bars, keep=.85))
                m = mark(p)
                pipe(p, [o + v * (h - hl) + u * w * .5, o2 + u * w * .5], .006, RUST, 5)
                paint(p, m, rust)

    # ---- the gables: posts, a transom at the eaves, glass below it and in the triangle above
    def gable(x, sg, posts, doorway):
        u = sg * Y
        m = mark(p)
        for y in posts[1:-1]:
            if doorway and abs(abs(y) - DY - .03) < 1e-6:
                gbox(p, (x - .05, y - .03, FL), (x + .05, y + .03, EV), STEEL, .6, .008, 'z')
            else:
                ibeam(p, (x, y, PL + .04), (x, y, EV), .09, .06, STEEL, X)
        gbox(p, (x - .04, -GY, (DT if doorway else EV - .04)), (x + .04, GY, EV + .04), STEEL, 1.0, .008)
        for ya, yb in zip(posts, posts[1:]):
            if doorway and ya < 0 < yb:
                continue
            gbox(p, (x - .02, ya, PL + .042), (x + .02, yb, PL + .08), STEEL, 1.0, .006)
        yt = np.linspace(-GY, GY, 13)
        for y in yt[1:-1]:
            if rafter_z(y) - EV > .2:
                bar(p, (x, y, EV + .04), (x, y, rafter_z(y) - .04), .03, .045, STEEL, sg * X)
        paint(p, m, rf)
        for ya, yb in zip(posts, posts[1:]):
            if doorway and ya < 0 < yb:
                continue
            w = yb - ya - .07
            o = (x, ya + .035, WZ) if sg > 0 else (x, yb - .035, WZ)
            tally(glazing(p, rng, o, u, Z, w, WH, max(2, round(w / .5)), 2, bars, keep=.74, foot=.8))
        gc = tone(GLASS_GREEN, .45)
        for ya, yb in zip(yt, yt[1:]):
            r = rng.uniform()
            c = vary(rng, gc if rng.uniform() < .7 else mix(gc, MOSS_DEEP, .45), .18)
            q = [(x + sg * .006, ya + .016, EV + .05), (x + sg * .006, yb - .016, EV + .05)]
            q += [(x + sg * .006, yy, rafter_z(yy) - .075) for yy in (yb - .016, ya + .016) if rafter_z(yy) - .075 > EV + .06]
            if len(q) < 3 or r > .78:
                panes['gone'] += 1
                continue
            face(p, q, GLASS, sg * X, c)
            panes['whole'] += 1
    gable(GX, 1, [-GY, -DY - .03, DY + .03, GY], True)
    gable(-GX, -1, [-GY, -.95, .95, GY], False)

    # ---- the sliding door: its track over the doorway, the leaf run open toward +y, a floor guide
    LX, LY0, LY1, LZ0, LZ1 = PX + .03, DY + .05, DY + 1.65, FL + .03, DT + .01     # the leaf runs clear of the dwarf wall's face
    m = mark(p)
    gbox(p, (PX, -DY - .1, DT + .03), (PX + .06, LY1 + .05, DT + .1), STEEL, .8, .006)
    for y in (-DY, 0, DY + .03, 1.6, LY1):
        gbox(p, (GX, y - .025, DT + .1), (PX + .05, y + .025, DT + .112), STEEL, 9, .003)
    gbox(p, (PX + .004, LY0, FL), (PX + .052, LY1, FL + .018), STEEL, .8, .004, 'z')
    for y0, y1 in ((LY0, LY0 + .05), (LY1 - .05, LY1), ((LY0 + LY1) / 2 - .02, (LY0 + LY1) / 2 + .02)):
        gbox(p, (LX - .02, y0, LZ0), (LX + .02, y1, LZ1), STEEL, .7, .006)
    for z0, z1 in ((LZ0, LZ0 + .09), (.86, .92), (LZ1 - .06, LZ1)):
        gbox(p, (LX - .019, LY0 + .05, z0), (LX + .019, LY1 - .05, z1), STEEL, .7, .006)
    for y in (LY0 + .25, LY1 - .25):
        gbox(p, (LX - .008, y - .03, LZ1), (LX + .008, y + .03, DT + .05), STEEL, 9, .003)
        turn(p, [(0, -.012), (.03, -.012), (.03, .012), (0, .012)], STEEL, 10, (LX, y, DT + .06), X)
    pipe(p, [(LX + .018, LY0 + .025, 1.0), (LX + .03, LY0 + .025, 1.03), (LX + .03, LY0 + .025, 1.22), (LX + .018, LY0 + .025, 1.25)], .008, STEEL, 6)
    paint(p, m, rf)
    m = mark(p)
    gbox(p, (LX - .005, LY0 + .05, LZ0 + .09), (LX + .005, LY1 - .05, .86), RUST, .3, .001, 'yYzZ')
    paint(p, m, rust)
    for y0 in (LY0 + .05, (LY0 + LY1) / 2 + .02):
        tally(glazing(p, rng, (LX, y0, .92), Y, Z, (LY1 - LY0) / 2 - .07, LZ1 - .06 - .92, 1, 2, bars, keep=.62, bar_w=.024, bar_d=.03))

    # ---- raised beds: precast kerbs, mounded soil, rows of saplings on canes, weeds
    KT, KH = .1, .42
    bedc = concrete(385, damp=.6, moss=.6, blot=.55, k=.95, north=(1.0, 0.0))
    beds = []
    for s in (-1, 1):
        for bi, (xa, xb) in enumerate(((-3.4, -.25), (.25, 3.2))):
            ya, yb = sorted((s * .85, s * 2.72))
            m = mark(p)
            for y0 in (ya, yb - KT):
                gbox(p, (xa, y0, FL), (xb, y0 + KT, FL + KH), CONCRETE, .5, .015, 'z')
            for x0 in (xa, xb - KT):
                gbox(p, (x0, ya + KT, FL), (x0 + KT, yb - KT, FL + KH), CONCRETE, .5, .015, 'z')
            paint(p, m, bedc)
            sd = 390 + bi + (2 if s > 0 else 0)

            def soil_z(x, y, xa=xa, xb=xb, ya=ya, yb=yb, sd=sd):
                tx, ty = (x - xa - KT) / (xb - xa - 2 * KT), (y - ya - KT) / (yb - ya - 2 * KT)
                hump = np.sin(np.pi * np.clip(ty, 0, 1)) ** .7 * np.clip(np.minimum(tx, 1 - tx) * 8, 0, 1)
                return FL + .3 + .035 * noise2(x * 2.3, y * 2.3, sd) + .055 * hump
            nxs, nys = cells(xb - xa - 2 * KT, .2), cells(yb - ya - 2 * KT, .2)
            gx, gy = np.meshgrid(np.linspace(xa + KT, xb - KT, nxs + 1), np.linspace(ya + KT, yb - KT, nys + 1), indexing='ij')
            gz = soil_z(gx, gy)
            k1 = .5 + .5 * noise2(gx * 1.4 + 3.0, gy * 1.4, sd + 5)
            k2 = .5 + .5 * noise2(gx * 6.0, gy * 6.0, sd + 6)
            green = np.clip(k1 * 2.2 - 1.35, 0, 1) * .7
            sc = fl.mix(mix(SOIL, RUST_DARK, .3), SOIL_DARK, np.clip(.25 + .3 * k1 + .55 * k2, 0, 1).ravel())
            sc[:, :3] = sc[:, :3] * (1 - green.ravel()[:, None]) + _rgb(mix(MOSS_GREEN, MOSS_DEEP, .4)) * green.ravel()[:, None]
            n = nys + 1
            p.add(np.stack([gx, gy, gz], -1).reshape(-1, 3), [[i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1] for i in range(nxs) for j in range(nys)],
                  sc, MOSS, True)
            beds.append(dict(x=(xa, xb), y=(ya, yb), kerb_top=FL + KH, soil_z=FL + .34))
            for x in np.arange(xa + .42, xb - .3, .56):
                for off, hh in ((.42, (.55, 1.0)), (1.02, (.8, 1.35)), (1.55, (.9, 1.6))):
                    q = V3(x + rng.normal(0, .07), s * (.85 + off) + rng.normal(0, .06), 0)
                    q[2] = float(soil_z(q[0], q[1])) - .02
                    r, h = rng.uniform(), rng.uniform(*hh)
                    h = min(h, rafter_z(q[1]) - q[2] - .75)
                    if r < .1:
                        continue
                    if rng.uniform() < .55:        # a cane and its tie
                        cane = q + V3(.03, .02, 0)
                        pipe(p, [cane, cane + V3(rng.normal(0, .02), rng.normal(0, .02), h * rng.uniform(.75, 1.05))], .006, BARK, 5, tone(WOOD_PALE, rng.uniform(.5, .8)))
                    if r < .2:                      # one that did not take: a bare whip
                        fl.limb(p, [q, q + V3(.03, -.02, h * .5), q + V3(.08, .0, h * .8)], [.01, .007, .003], tone(BARK_GREY, .7), BARK, 5)
                        continue
                    gold = rng.uniform() < .22
                    cols = (LEAF_GREEN, LEAF_GOLD) if gold else (LEAF_GREEN, LEAF_LIGHT)
                    bark = BARK_BIRCH if gold else (BARK_BROWN if rng.uniform() < .6 else BARK_GREY)
                    sprig(p, rng, q, h, int(7 + h * 7), cols, bark, .011 + .008 * h, .22 + .08 * h)
                    if h > .8:                      # a second flush lower down fills the young crown
                        sprig(p, rng, q + Z * h * .3, h * .55, int(5 + h * 5), cols, bark, .007, .2 + .06 * h)
            for _ in range(9):
                q = V3(rng.uniform(xa + .2, xb - .2), rng.uniform(ya + .18, yb - .18), 0)
                q[2] = float(soil_z(q[0], q[1])) - .01
                tuft(p, rng, q, rng.uniform(.15, .4), rng.uniform(.25, .4), 3, (GRASS, LEAF_LIGHT) if rng.uniform() < .6 else (GRASS, GRASS_DRY))
    # the one that got away: a young tree in the back bed on -y, up under the glass
    q = V3(-2.5, -1.35, FL + .33)
    fl.limb(p, [q, q + V3(.05, .03, .8), q + V3(-.04, .08, 1.6), q + V3(.02, .02, 2.25)], [.04, .03, .02, .008], tone(BARK_BROWN, np.array([.8, 1.0, 1.05, 1.1])), BARK, 7)
    for dz, h, lean in ((.7, 1.1, (.5, .2)), (1.0, 1.0, (-.4, .35)), (1.3, .9, (.2, -.45)), (1.55, .75, (-.3, -.2)), (1.7, .7, (.1, .3))):
        b = q + V3(.03, .05, dz)
        sprig(p, rng, b + V3(lean[0] * .15, lean[1] * .15, 0), h, 12, (LEAF_GREEN, LEAF_LIGHT), BARK_BROWN, .014, .34)

    # ---- the potting bench across the -x end, pots, trays, a copper can; the water butt and spare pots by the door
    PX0, PX1, PW, PTOP = -4.2, -3.6, 1.3, FL + .85
    m = mark(p)
    for x in (PX0 + .03, PX1 - .03):
        for y in (-PW + .03, 0, PW - .03):
            angle(p, (x, y, FL), (x, y, PTOP - .02), .04, STEEL, X if x < -3.9 else -X, Y if y <= 0 else -Y)
        gbox(p, (x - .02, -PW, PTOP - .08), (x + .02, PW, PTOP - .02), STEEL, .8, .004)
        gbox(p, (x - .015, -PW, FL + .22), (x + .015, PW, FL + .26), STEEL, .8, .004)
    for k in range(6):
        x = PX0 + .05 + k * (PX1 - PX0 - .1) / 5
        gbox(p, (x - .04, -PW - .02, PTOP - .02), (x + .04, PW + .02, PTOP), STEEL, .6, .004)
    for k in range(4):
        x = PX0 + .08 + k * (PX1 - PX0 - .16) / 3
        gbox(p, (x - .05, -PW + .02, FL + .26), (x + .05, PW - .02, FL + .275), STEEL, .6, .004)
    paint(p, m, steel(386, STEEL_GREY, .5, ground=FL, damp=1.2))
    on_bench = []
    for k, (y, r, h) in enumerate(((-1.12, .11, .2), (-.86, .09, .16), (-.62, .075, .13), (-.42, .075, .13), (.45, .1, .18), (.72, .12, .22), (1.08, .085, .15), (-.72, .07, .12))):
        x = PX0 + (.2 if k < 7 else .46) + rng.uniform(-.03, .03)
        full = rng.uniform() < .75
        flowerpot(p, rng, (x, y, PTOP), r, h, full, seed=400 + k)
        on_bench.append((x, y, PTOP))
        if full and rng.uniform() < .8:
            if rng.uniform() < .5:
                sprig(p, rng, (x, y, PTOP + h * .84), rng.uniform(.25, .5), 6, (LEAF_GREEN, LEAF_LIGHT), BARK_BROWN, .006, .17)
            else:
                tuft(p, rng, (x, y, PTOP + h * .84), rng.uniform(.14, .26), .2, 3, (LEAF_LIGHT, GRASS))
    flowerpot(p, rng, (PX1 - .16, 1.0, PTOP + .08), .09, .17, False, rot('y', 96) @ rot('z', 40), seed=410)
    for y in (-.1, .22):                             # seed trays
        m = mark(p)
        gbox(p, (PX0 + .08, y - .13, PTOP), (PX0 + .5, y + .13, PTOP + .05), STEEL, 9, .006, 'z')
        paint(p, m, steel(387, STEEL_DARK, .3, ground=PTOP, damp=.2, k=1.5))
        gface(p, (PX0 + .095, y - .115, PTOP + .042), (PX0 + .485, y - .115, PTOP + .042), (PX0 + .485, y + .115, PTOP + .042), (PX0 + .095, y + .115, PTOP + .042),
              MOSS, .13, Z, tone(mix(SOIL, SOIL_DARK, .5), 1.0))
        for _ in range(9):
            tuft(p, rng, (PX0 + rng.uniform(.12, .46), y + rng.uniform(-.09, .09), PTOP + .042), rng.uniform(.06, .14), .1, 2, (LEAF_LIGHT, LEAF_GREEN), fl.CELL_SMALLLEAF)
    m = mark(p)                                      # the watering can
    cc = V3(PX1 - .18, -.2, PTOP)
    turn(p, [(.095, 0), (.105, .02), (.105, .2), (.095, .22), (.07, .225)], BRASS, 14, cc)
    disc(p, cc + Z * .225, .07, BRASS, Z, 14)
    pipe(p, [cc + V3(0, .09, .05), cc + V3(0, .2, .16), cc + V3(0, .3, .27)], [.02, .015, .012], BRASS, 8)
    turn(p, [(.012, 0), (.035, .03), (.0, .034)], BRASS, 8, cc + V3(0, .3, .27), unit(V3(0, .1, .11)))
    pipe(p, arc_pts(cc + Z * .225, .075, 0, 180, -Y, Z, 8), .008, BRASS, 6)
    paint(p, m, copper(388, .45))
    for x, y, n in ((PX0 + .2, -.9, 5), (PX0 + .22, -.55, 3), (PX0 + .42, -.75, 4), (3.72, -2.35, 6), (3.98, -2.1, 4), (3.6, -2.05, 2)):
        z0 = FL + .275 if x < 0 else FL
        for k in range(n):
            flowerpot(p, rng, (x, y, z0 + k * .045), .1, .18, False, seed=420 + k)
    flowerpot(p, rng, (3.95, -2.5, FL + .095), .1, .18, False, rot('x', 88) @ rot('z', 20), seed=430)
    BUTT = (3.75, 2.25)
    m = mark(p)
    turn(p, [(.28, 0), (.29, .02), (.29, .3), (.305, .31), (.305, .33), (.29, .34), (.29, .62), (.305, .63), (.305, .65), (.29, .66), (.29, .93), (.3, .95), (.27, .95), (.27, .8)],
         STEEL, 20, (BUTT[0], BUTT[1], FL))
    paint(p, m, film(steel(389, STEEL_GREY, .45, ground=FL, damp=.9), 389, .5, ground=FL, reach=.6))
    disc(p, (BUTT[0], BUTT[1], FL + .82), .27, STEEL, Z, 20, tone(mix(STEEL_DARK, MOSS_DEEP, .5), .5))

    # ---- irrigation: two galvanised lines hung from the rafters over the beds, brass nozzles, a riser with its valve
    IZ, IY = 2.22, 1.75
    m = mark(p)
    lines = {1: [(-4.1, IY, IZ), (3.3, IY, IZ)], -1: [(-4.1, -IY, IZ), (1.05, -IY, IZ), (1.5, -IY - .02, IZ - .06), (1.9, -IY - .04, IZ - .3), (2.15, -IY - .05, IZ - .62)]}
    for s, pts in lines.items():
        pipe(p, pts, .019, STEEL, 8)
        for x in xs[1:5]:
            turn(p, [(.019, -.03), (.026, -.03), (.026, .03), (.019, .03)], STEEL, 8, (x + .2, s * IY, IZ), X)
    RYV = 2.45
    pipe(p, [(-4.1, -IY, IZ), (-4.1, RYV, IZ), (-4.1, RYV, FL + .22), (-4.3, RYV, FL + .22)], .019, STEEL, 8)
    paint(p, m, steel(391, STEEL_GREY, .4, ground=-2, damp=1.0))
    m = mark(p)
    for s in (-1, 1):
        for x in xs[1:6]:
            if lines[s][1][0] > x - .01:
                pipe(p, [(x, s * IY, IZ + .017), (x, s * IY, rafter_z(IY) - .04)], .004, RUST, 4, cap=False)
    paint(p, m, rust)
    m = mark(p)
    nozzles = []
    for s in (-1, 1):
        for x in np.arange(-3.7, lines[s][1][0] - .1, .74):
            pipe(p, [(x, s * IY, IZ - .017), (x, s * IY, IZ - .05)], .008, BRASS, 6)
            turn(p, [(.016, -.012), (.016, 0), (.006, .0)], BRASS, 6, (x, s * IY, IZ - .05))
            nozzles.append((float(x), s * IY, IZ - .06))
    vc = V3(-4.1, RYV, 1.05)
    turn(p, [(.019, -.06), (.036, -.06), (.036, .06), (.019, .06)], BRASS, 10, vc)
    for z in (-.06, .06):
        turn(p, [(.019, z - .012), (.05, z - .012), (.05, z + .012), (.019, z + .012)], BRASS, 10, vc)
    pipe(p, [vc, vc + X * .11], .01, BRASS, 6)
    hoop(p, vc + X * .11, .06, .008, BRASS, X, 16, 6)
    for a in np.radians((0, 120, 240)):
        pipe(p, [vc + X * .11, vc + X * .11 + (Y * math.cos(a) + Z * math.sin(a)) * .06], .005, BRASS, 4, cap=False)
    tap = V3(-4.1, RYV, .55)
    pipe(p, [tap, tap + X * .09, tap + V3(.12, 0, -.04)], .013, BRASS, 6)
    pipe(p, [tap + V3(.06, 0, .0), tap + V3(.06, 0, .05), tap + V3(.06, .04, .05)], .006, BRASS, 5)
    paint(p, m, steel(392, tone(BRASS_WARM, .45), .0, ground=-9, grime=.5))

    # ---- what the years did: runs, moss, broken glass on the floor, weeds, ivy
    for s in (-1, 1):
        streaks(p, rng, [(rng.uniform(-4.2, 4.2), s * PY, PL - .005) for _ in range(7)], s * Y, (.15, .45), (.03, .07))
        moss_line(p, rng, (-PX * s, s * PY, FL), (PX * s, s * PY, FL), s * Y, .05, .025, climb=.22)
        moss_line(p, rng, (-HX * s, s * HY, 0), (HX * s, s * HY, 0), s * Y, .055, .025, climb=.04)
        moss_line(p, rng, (xs[0] + 1.0, s * 2.915, EV - .012), (xs[0] + 5.2, s * 2.915, EV - .012), s * Y, .05, .03, step=.25)
        for xa, xb in ((-3.4, -.25), (.25, 3.2)):
            moss_line(p, rng, (xa if s > 0 else xb, s * .85, FL), (xb if s > 0 else xa, s * .85, FL), -s * Y, .06, .02, climb=.1)
    streaks(p, rng, [(-PX, rng.uniform(-2.6, 2.6), PL - .005) for _ in range(5)], -X, (.15, .45), (.03, .07))
    streaks(p, rng, [(PX, y, PL - .005) for y in (-2.3, -1.4, 1.2, 2.1)], X, (.15, .45), (.03, .07))
    moss_line(p, rng, (-PX, PY, FL), (-PX, -PY, FL), -X, .05, .025, climb=.2)
    moss_line(p, rng, (-HX, HY, 0), (-HX, -HY, 0), -X, .055, .025, climb=.04)
    for ya, yb in ((-HY, -DY - .1), (DY + .1, HY)):
        moss_line(p, rng, (HX, ya, 0), (HX, yb, 0), X, .055, .025, climb=.04)
    for k in range(24):                              # moss cushions, most of them in the lee of the kerbs
        y = rng.uniform(-.5, .5) if k < 5 else rng.choice((-1, 1)) * (.85 - rng.uniform(.04, .22))
        moss_patch(p, rng, (rng.uniform(-3.5, 4.2), y, FL), rng.uniform(.03, .08), .014, n=7)
    for _ in range(10):
        q = (rng.uniform(-4.2, 4.2), rng.choice((-1, 1)) * rng.uniform(2.86, 2.92), PL + .03)
        moss_patch(p, rng, q, rng.uniform(.04, .08), .02, n=7)
    gc = tone(GLASS_GREEN, .4)
    for _ in range(22):                              # fallen glass, flat on the floor
        c = V3(rng.uniform(-3.4, 4.1), rng.choice((-1, 1)) * rng.uniform(.3, .82), FL + .004)
        a0 = rng.uniform(0, TAU)
        pts = [c + rng.uniform(.03, .12) * V3(math.cos(a0 + k * TAU / 3 + rng.normal(0, .3)), math.sin(a0 + k * TAU / 3 + rng.normal(0, .3)), 0) for k in range(3)]
        p.add(pts, [fl._facing(pts, [0, 1, 2], Z)], vary(rng, gc, .2), GLASS, False)
    for _ in range(26):
        side = int(rng.integers(0, 4))
        t = rng.uniform(-1, 1)
        q = [(HX + .03, t * HY), (-HX - .03, t * HY), (t * HX, HY + .03), (t * HX, -HY - .03)][side]
        if side == 0 and abs(q[1]) < 1.0:
            continue
        tuft(p, rng, (q[0], q[1], 0), rng.uniform(.25, .5), rng.uniform(.22, .34))
    for q in ((-3.5, .8), (-.1, -.83), (.1, .84), (3.3, -.9), (3.4, 1.4), (4.1, -1.2), (-3.5, -2.6), (-4.1, 1.9), (3.3, 2.6), (-.05, 2.3), (0, -2.2)):
        tuft(p, rng, (q[0], q[1], FL), rng.uniform(.2, .4), rng.uniform(.25, .4))
    ivy(p, rng, (-4.3, -GY - .05, PL - .05), X, -Y, 3.0, 2.3, 46)
    ivy(p, rng, (-4.3, -PY - .03, 0), X, -Y, 2.4, .6, 12, size=.34)
    ivy(p, rng, (-GX - .06, 2.75, PL - .05), -Y, -X, 2.5, 2.7, 38)
    ivy(p, rng, (-PX - .03, 2.8, 0), -Y, -X, 2.0, .6, 10, size=.34)
    ivy(p, rng, (xs[3] - .25, GY - .09, FL + .4), X, -Y, .55, 2.4, 18, size=.3)
    ivy(p, rng, (xs[1] - .25, -GY + .09, FL + .4), X, Y, .5, 1.9, 12, size=.3)
    for q in p.v:              # leaf cards that droop under the ground plane stop at it
        q[2] = max(q[2], 0.0)
    return done(p, facts=dict(
        door=dict(face_x=GX, centre=(GX, 0.0, FL), y=(-DY, DY), z=(FL, DT), width=2 * DY, height=round(DT - FL, 3),
                  leaf=dict(x=round(LX, 3), y=(LY0, round(LY1, 3)), z=(LZ0, LZ1), state='slid open along the outside of the +x gable'), plinth_x=(round(PX - PT, 3), PX)),
        floor_z=FL, slab=dict(x=(-HX, HX), y=(-HY, HY)), interior=dict(x=(round(-PX + PT, 3), round(PX - PT, 3)), y=(round(-PY + PT, 3), round(PY - PT, 3))),
        aisle=dict(x=(PX1 + .05, round(PX - PT, 3)), y=(-.85, .85), z=(FL, EV + .04), width=1.7), stand=[(2.6, 0.0, FL), (0.0, 0.0, FL), (-2.4, 0.0, FL)],
        beds=beds, bench=dict(x=(PX0, PX1), y=(-PW, PW), top=PTOP, pots=on_bench), butt=dict(centre=(BUTT[0], BUTT[1], FL), r=.3, top=FL + .95),
        tree=(-2.5, -1.35), irrigation=dict(y=(-IY, IY), z=IZ, nozzles=nozzles, valve=(-4.1, RYV, 1.05)), tie_rods_z=EV + .06,
        plinth_top=PL, eaves_z=EV, ridge_z=RG, ribs_x=[float(x) for x in xs], vents=[dict(side='+y' if s > 0 else '-y', bay=i) for s, i in sorted(VENTS)],
        panes=panes, top=4.2))


# ---------------------------------------------------------------- the module's meshes and their contract

MESHES = list(_BUILDERS)
CONTRACT = dict(_SIZES)
