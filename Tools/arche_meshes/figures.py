"""Level 5, Arche, the First Ones' Planet: the First Ones, the Sunderer, crystals and items, the meshes of the table
"Figures, crystals and items" in Tools/arche/README.md.

Pure numpy on kit.py; never imports bpy. Check and look:

    python3 Tools/arche_meshes/check.py figures --preview

The First Ones' native form (first_one()): tall and slender; a dark core (ROCK) under pale, layered mineral plates
(STONE) that lap like folded strata, lifted at their lower edges so the core shows in the joints; a long smooth head
swept back, with no face, only one vertical seam of light (GLOW); a crown of thin slivers floating a hand's width off
the head; long arms and hands of three long fingers and a thumb (four digits); a mantle and a long skirt of heavy
cloth with modelled folds. The Serene wear pearl and indigo and their seam is ice blue; Aeon is the elder (taller, a
long pearl cloak, weathered plates, an electrum collar, two slivers of the crown missing); Maruth of the Vigil wears
violet over near-black enamel, with an alloy collar and pauldrons and a staff. People face +x and stand on z 0 with
their body's axis on the origin.
"""
from kit import *

unit, basis, along, place = fl.unit, fl.basis, fl.along, fl.place
ball, obox, glow = fl.ball, fl.obox, fl.glow
norm = np.linalg.norm

BLACK = col(.022, .024, .030)           # the AL's black frame (ALLOY slot)
CORE = col(.040, .044, .058)            # a First One's dark core (ROCK slot)


def V(*x):
    return np.array(x, np.float64)


def rgba(rgb):
    rgb = np.clip(np.asarray(rgb, np.float64), 0.0, None)
    return np.concatenate([rgb, np.ones(rgb.shape[:-1] + (1,))], -1)


def lit(colour, k):
    """colour (one, or an array of them) times shading k (an array), as RGBA at most 0.9."""
    c = np.asarray(colour, np.float64)[..., :3]
    return rgba(np.minimum(c * np.asarray(k, np.float64)[..., None], .9))


def blend(a, b, t):
    a, b = np.asarray(a, np.float64)[..., :3], np.asarray(b, np.float64)[..., :3]
    t = np.clip(np.asarray(t, np.float64), 0, 1)[..., None]
    return rgba(a * (1 - t) + b * t)


def wrap(th):
    return (np.asarray(th, np.float64) + math.pi) % TAU - math.pi


def ease(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- paths and tubes

def spline(keys, n):
    """A smooth path through key points (Catmull-Rom), n samples."""
    P = np.asarray(keys, np.float64)
    m = len(P)
    t = np.linspace(0, m - 1, n)
    i = np.clip(np.floor(t).astype(int), 0, m - 2)
    u = (t - i)[:, None]
    p0, p1, p2, p3 = P[np.clip(i - 1, 0, m - 1)], P[i], P[i + 1], P[np.clip(i + 2, 0, m - 1)]
    return .5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2 + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def curve(keys, n):
    """A smooth path of n points evenly spaced along its length through keys."""
    path = spline(keys, max(n * 6, 60))
    seg = np.r_[0.0, np.cumsum(norm(np.diff(path, axis=0), axis=1))]
    at = np.linspace(0, seg[-1], n)
    return np.stack([np.interp(at, seg, path[:, k]) for k in range(path.shape[1])], 1)


def _carry(v, t0, t1):
    axis = np.cross(t0, t1)
    s = norm(axis)
    if s < 1e-9:
        return v
    axis = axis / s
    ang = math.atan2(s, float(np.clip(np.dot(t0, t1), -1, 1)))
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * np.dot(axis, v) * (1 - math.cos(ang))


def frames(pts, closed=False):
    """Tangents and two normals carried along a polyline without twisting."""
    pts = np.asarray(pts, np.float64)
    tang = unit(np.roll(pts, -1, 0) - np.roll(pts, 1, 0)) if closed else unit(np.gradient(pts, axis=0))
    a = frame(tang[0])[0]
    A = np.zeros_like(pts)
    for i in range(len(pts)):
        if i:
            a = _carry(a, tang[i - 1], tang[i])
        a = unit(a - tang[i] * np.dot(a, tang[i]))
        A[i] = a
    return tang, A, np.cross(tang, A)


def pipe(part, pts, radius, colour, slot=0, sides=8, cap=True, smooth=True, closed=False):
    """A tube along a polyline. radius: one or one per point. colour: one or one per point."""
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    tang, A, B = frames(pts, closed)
    ang = np.linspace(0, TAU, sides, endpoint=False)
    rad = np.broadcast_to(np.asarray(radius, np.float64), (n,))
    verts = pts[:, None, :] + rad[:, None, None] * (np.cos(ang)[None, :, None] * A[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :])
    faces = [[i * sides + j, i * sides + (j + 1) % sides, ((i + 1) % n) * sides + (j + 1) % sides, ((i + 1) % n) * sides + j]
             for i in range(n if closed else n - 1) for j in range(sides)]
    cols = np.asarray(colour, np.float64)
    if cols.ndim == 2:
        cols = np.repeat(cols, sides, 0)
    start = part.add(verts.reshape(-1, 3), faces, cols, slot, smooth)
    if cap and not closed:
        for ring_, c, order in ((verts[0], cols[:sides] if cols.ndim == 2 else cols, -1), (verts[-1], cols[-sides:] if cols.ndim == 2 else cols, 1)):
            if rad[0 if order < 0 else -1] > 1e-6:
                part.add(ring_, [list(range(sides))[::order]], c, slot, False)
    return start


def hoop(part, centre, axis, big, small, colour, slot=0, sides=24, section=6, squash=1.0):
    """A torus round axis (squash flattens it across the second frame axis: an oval ring)."""
    a, b = frame(axis)
    t = np.linspace(0, TAU, sides, endpoint=False)
    path = np.asarray(centre, np.float64) + big * (np.cos(t)[:, None] * a + squash * np.sin(t)[:, None] * b)
    return pipe(part, path, small, colour, slot, section, closed=True)


def revolve(part, profile, colour, slot=0, sides=16, rot=None, origin=(0, 0, 0), smooth=True, caps=(True, True)):
    """Revolves an open profile [(radius, z), ...] round local z, listed up the outside. An end on the axis closes as
    a pole; another is closed by a flat disc when its caps flag is set. colour: one, or one per profile point."""
    prof = [(float(r), float(z)) for r, z in profile]
    ang = np.linspace(0, TAU, sides, endpoint=False)
    cols = np.asarray(colour, np.float64)
    per = cols.ndim == 2
    verts, vcols, first, faces = [], [], [], []
    for i, (r, z) in enumerate(prof):
        first.append(len(verts))
        ring_ = [(0.0, 0.0, z)] if r <= 1e-9 else np.stack([np.cos(ang) * r, np.sin(ang) * r, np.full(sides, z)], 1).tolist()
        verts.extend(ring_)
        vcols.extend([cols[i] if per else cols] * len(ring_))
    for i in range(len(prof) - 1):
        a, b = first[i], first[i + 1]
        lo, hi = prof[i][0] <= 1e-9, prof[i + 1][0] <= 1e-9
        for j in range(sides):
            k = (j + 1) % sides
            if lo and hi:
                continue
            faces.append([a, b + k, b + j] if lo else [a + j, a + k, b] if hi else [a + j, a + k, b + k, b + j])
    start = part.add(verts, faces, np.asarray(vcols), slot, smooth)
    for end, flag, order in ((0, caps[0], -1), (len(prof) - 1, caps[1], 1)):
        if flag and prof[end][0] > 1e-9:
            part.add(verts[first[end]:first[end] + sides], [list(range(sides))[::order]], cols[end] if per else cols, slot, False)
    place(part, start, rot, origin)
    return start


# ---------------------------------------------------------------- surfaces, sheets and plates

def skin(part, grid, colour, slot, out, smooth=True, wrap_v=False):
    """A surface over a point grid (nu x nv x 3), each face wound to front `out` (one direction, or one per point).
    Collapsed edges become triangles. colour: one, or one per grid point."""
    g = np.asarray(grid, np.float64)
    nu, nv = g.shape[:2]
    flat = g.reshape(-1, 3)
    o = np.broadcast_to(np.asarray(out, np.float64), g.shape).reshape(-1, 3)
    faces = []
    for u in range(nu - 1):
        for v in range(nv if wrap_v else nv - 1):
            w = (v + 1) % nv
            q = [u * nv + v, (u + 1) * nv + v, (u + 1) * nv + w, u * nv + w]
            q = [i for k, i in enumerate(q) if np.abs(flat[i] - flat[q[k - 1]]).max() > 1e-7]
            if len(q) < 3:
                continue
            P = flat[q]
            n = np.cross(P, np.roll(P, -1, 0)).sum(0)
            if norm(n) < 1e-11 or norm(np.cross(P[1] - P[0], P[2] - P[0])) < 1e-11:
                continue
            faces.append(q[::-1] if np.dot(n, o[q].sum(0)) < 0 else q)
    cols = np.asarray(colour, np.float64)
    return part.add(flat, faces, cols.reshape(-1, cols.shape[-1]) if cols.ndim == 3 else cols, slot, smooth)


def cap(part, ring_, direction, colour, slot):
    P = np.asarray(ring_, np.float64)
    f = list(range(len(P)))
    if np.dot(np.cross(P, np.roll(P, -1, 0)).sum(0), direction) < 0:
        f = f[::-1]
    return part.add(P, [f], colour, slot, False)


def grid_normals(G, toward):
    """Unit normals of a point grid, turned to the side of `toward` (one direction per point)."""
    n = np.cross(np.gradient(G, axis=0), np.gradient(G, axis=1))
    ln = norm(n, axis=-1, keepdims=True)
    t = unit(toward)
    n = np.where(ln > 1e-12, n / np.maximum(ln, 1e-12), t)
    return np.where(np.sum(n * t, -1, keepdims=True) < 0, -n, n)


def sheet(part, outer, inner, colour, slot, back=None, rim=None, wrap_v=False, smooth=True, hollow=False):
    """A plate or cloth with thickness between two matching grids: face, back (its own colour when given) and a
    crisp rim. hollow leaves the back out, where a core always hides it."""
    outer, inner = np.asarray(outer, np.float64), np.asarray(inner, np.float64)
    d = outer - inner
    start = skin(part, outer, colour, slot, d, smooth, wrap_v)
    if not hollow:
        skin(part, inner, colour if back is None else back, slot, -d, smooth, wrap_v)
    mid = (outer + inner) / 2
    if rim is None:
        c = np.asarray(colour, np.float64)
        rim = lit(c.reshape(-1, c.shape[-1]).mean(0), np.float64(.7))
    edges = [(outer[0], inner[0], mid[0] - mid[1], wrap_v), (outer[-1], inner[-1], mid[-1] - mid[-2], wrap_v)]
    if not wrap_v:
        edges += [(outer[:, 0], inner[:, 0], mid[:, 0] - mid[:, 1], False), (outer[:, -1], inner[:, -1], mid[:, -1] - mid[:, -2], False)]
    for a, b, o, w in edges:
        skin(part, np.stack([a, b]), rim, slot, np.stack([o, o]), False, w)
    return start


def plate(part, fn, u, w, colour, slot=None, lift=(.003, .012), thick=.006, tongue=0.0, n=(5, 6), wear=.08, seed=0, rim=None):
    """A plate lying on the surface fn(U, W) -> (points, centres) over u = (from, to), w = (from, to): tucked under
    its neighbour at u[0] and lifted at u[1] (lift, metres off the surface at each end), so plates lap like strata
    and the dark core shows in the joint. tongue lengthens the middle of its free edge. Vertex colour: darker where it
    is tucked, lighter on its worn border."""
    slot = STONE if slot is None else slot
    s = np.linspace(0, 1, n[0])[:, None]
    q = np.linspace(0, 1, n[1])[None, :]
    W = w[0] + (w[1] - w[0]) * q + 0 * s
    U = u[0] + (u[1] + tongue * np.sin(np.pi * q) ** .8 - u[0]) * s
    P, C = fn(U, W)
    N = grid_normals(P, P - C)
    d = lift[0] + (lift[1] - lift[0]) * s ** 1.4 + 0 * q
    border = np.zeros(d.shape)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = 1.0
    k = (.80 + .22 * s) * (1 + wear * border) * (1 + .06 * noise2(P[..., 0] * 37 + P[..., 2] * 21, P[..., 1] * 37 - P[..., 2] * 17, seed + 5))
    return sheet(part, P + N * d[..., None], P + N * np.maximum(d - thick, -.003)[..., None], lit(colour, k), slot,
                 rim=lit(colour, np.float64(.6)) if rim is None else rim, hollow=True)


def capsule(a, b, r0, r1, face):
    """The surface of a tapering limb from a to b as fn(U, W): U along it (0..1), W the angle from `face`."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    ax = unit(b - a)
    A = unit(np.asarray(face, np.float64) - ax * np.dot(face, ax))
    B = np.cross(ax, A)

    def fn(U, W):
        U, W = np.broadcast_arrays(np.asarray(U, np.float64), np.asarray(W, np.float64))
        C = a + (b - a) * U[..., None]
        r = (r0 + (r1 - r0) * U)[..., None]
        return C + r * (np.cos(W)[..., None] * A + np.sin(W)[..., None] * B), C
    return fn


class Body:
    """A body by height: rows (z, half-width, front depth, back depth, x centre), superellipse sections, softened
    between rows. Angles run from the front (+x, 0) toward +y."""

    def __init__(self, rows, power=2.0, soft=.03):
        r = np.asarray(sorted(map(tuple, rows)), np.float64)
        self.z = np.linspace(r[0, 0], r[-1, 0], 400)
        rad = max(1, int(soft / max(self.z[1] - self.z[0], 1e-9)))
        ker = np.ones(2 * rad + 1) / (2 * rad + 1)
        self.cols = [np.convolve(np.pad(np.interp(self.z, r[:, 0], r[:, k]), rad, mode='edge'), ker, mode='valid') for k in range(1, 5)]
        self.e = 2.0 / power

    def dims(self, z):
        return [np.interp(z, self.z, c) for c in self.cols]

    def point(self, th, z, off=0.0, k=1.0):
        th, z = np.broadcast_arrays(np.asarray(th, np.float64), np.asarray(z, np.float64))
        hw, fr, bk, cx = self.dims(z)
        c, s = np.cos(th), np.sin(th)
        x = np.where(c >= 0, fr, bk) * np.sign(c) * np.abs(c) ** self.e
        y = hw * np.sign(s) * np.abs(s) ** self.e
        k = k + off / np.maximum(np.hypot(x, y), 1e-6)
        return np.stack([cx + x * k, y * k, z], -1)

    def centre(self, z):
        z = np.asarray(z, np.float64)
        return np.stack([self.dims(z)[3], np.zeros_like(z), z], -1)

    def fn(self, U, W):
        """As a plate surface: U is the height, W the angle."""
        U, W = np.broadcast_arrays(np.asarray(U, np.float64), np.asarray(W, np.float64))
        return self.point(W, U), self.centre(U)


def band(part, path, width, thick, out, colour, slot, rim=None):
    """A flat strap along a path, its face turned toward `out`."""
    path = np.asarray(path, np.float64)
    tang = unit(np.gradient(path, axis=0))
    o = np.broadcast_to(np.asarray(out, np.float64), path.shape)
    o = unit(o - tang * np.sum(o * tang, 1, keepdims=True))
    side = np.cross(tang, o)
    w = np.broadcast_to(np.asarray(width, np.float64), (len(path),))[:, None] / 2
    outer = np.stack([path - side * w + o * thick / 2, path + side * w + o * thick / 2], 1)
    sheet(part, outer, outer - o[:, None, :] * thick, colour, slot, rim=rim)


def graft(part, other, rot=None, origin=(0, 0, 0), mirror_y=False):
    """Appends another Part (same slot names): mirrored in its own y when asked (faces re-wound), turned, moved."""
    v = np.asarray(other.v, np.float64)
    if mirror_y:
        v = v * np.array([1.0, -1.0, 1.0])
    if rot is not None:
        v = v @ np.asarray(rot, np.float64).T
    base = len(part.v)
    part.v.extend((v + np.asarray(origin, np.float64)).tolist())
    part.c.extend(other.c)
    part.uv.extend([None] * len(other.v))
    index = [part.slots.index(q) for q in other.slots]
    for f, m, sm in zip(other.f, other.m, other.s):
        g = [base + i for i in f]
        part.f.append(g[::-1] if mirror_y else g)
        part.m.append(index[m])
        part.s.append(sm)
    return base


# ---------------------------------------------------------------- finishing

def vertex_normals(part):
    v = np.asarray(part.v, np.float64)
    tri = np.array([(f[0], f[k], f[k + 1]) for f in part.f for k in range(1, len(f) - 1)], np.int64)
    fn = np.cross(v[tri[:, 1]] - v[tri[:, 0]], v[tri[:, 2]] - v[tri[:, 0]])
    acc = np.zeros_like(v)
    for j in range(3):
        np.add.at(acc, tri[:, j], fn)
    return unit(acc)


def vertex_slots(part):
    out = np.zeros(len(part.v), np.int64)
    for f, m in zip(part.f, part.m):
        out[f] = m
    return out


def weather(part, seed=0, span=1.0, under=.22, dirt=.12, streak=.12, lichen=0.0, dust=0.0, pits=0.0, soft=.4,
            skip=(GLOW, CRYSTAL), gentle=(CLOTH, ELECTRUM)):
    """Vertex-colour weathering (span: the object's size, which scales the patterns): under darkens toward the
    ground and on undersides; dirt is blotchy grime; streak is runs down the sides; pits speckle stone dark; lichen
    greys the stone that faces the sky in patches; dust pales tops. Lights and crystal keep their colours, cloth and
    electrum take `soft` of it."""
    v = np.asarray(part.v, np.float64)
    cols = np.asarray(part.c, np.float64)
    nrm = vertex_normals(part)
    vs = vertex_slots(part)
    amount = np.ones(len(v))
    amount[np.isin(vs, [part.slots.index(s) for s in skip if s in part.slots])] = 0.0
    amount[np.isin(vs, [part.slots.index(s) for s in gentle if s in part.slots])] = soft
    hard = np.isin(vs, [part.slots.index(s) for s in (STONE, ROCK, ENAMEL) if s in part.slots]).astype(np.float64)
    lo, hi = v.min(0), v.max(0)
    h = np.clip((v[:, 2] - lo[2]) / max(hi[2] - lo[2], 1e-6), 0, 1)
    x, y, z = (v / max(span, 1e-6)).T
    k = (1 - under * ((1 - h) ** 2 * .5 + .5 * np.clip(-nrm[:, 2], 0, 1))) * (1 - dirt * (.5 + .5 * noise2(x * 6 + z * 2.3, y * 6 - z * 2.6, seed + 3)))
    run = np.clip(noise2(x * 31 + 3.1, y * 31, seed + 5) * 1.7 - .3, 0, 1) * (1 - np.abs(nrm[:, 2])) ** 2
    k = k * (1 - streak * run)
    if pits:
        k = k * (1 - pits * hard * np.clip(noise2(x * 90 + z * 40, y * 90 - z * 55, seed + 7) * 2 - .9, 0, 1))
    rgb = cols[:, :3] * (1 - amount[:, None] * (1 - k[:, None]))

    def tint(rgb, m, colour):
        m = np.clip(m * amount, 0, 1)[:, None]
        return rgb * (1 - m) + np.asarray(colour, np.float64)[:3] * m
    if lichen:
        patch = np.clip(noise2(x * 11 + 5, y * 11 + z * 6, seed + 15) + lichen * 1.5 - .75, 0, 1)
        rgb = tint(rgb, hard * np.clip(nrm[:, 2] * .8 + .45, 0, 1) * patch * 1.2, mix(LICHEN_FROST, LICHEN_DEEP, .25))
    if dust:
        rgb = tint(rgb, dust * np.clip(nrm[:, 2], 0, 1) ** 2, DUST)
    cols[:, :3] = np.where(amount[:, None] > 0, np.minimum(rgb, .9), cols[:, :3])
    part.c = cols.tolist()


def stand(part, height=None):
    """Lowest point to z 0 (the body's axis stays on the origin), scaled about the origin to `height` when given."""
    v = np.asarray(part.v, np.float64)
    v[:, 2] -= v[:, 2].min()
    if height:
        v *= height / v[:, 2].max()
    part.v = v.tolist()
    return part


def fit(part, axis, size):
    """Centres the part on its bounds and scales it so that its extent along axis (0, 1, 2) is size."""
    v = np.asarray(part.v, np.float64)
    lo, hi = v.min(0), v.max(0)
    part.v = ((v - (lo + hi) / 2) * (size / (hi - lo)[axis])).tolist()
    return part


# ---------------------------------------------------------------- crystal

def crystal(part, base, axis, r, length, rng, c0, c1, slot=None, tip=.22, taper=.1, edge=None, core=None, segs=2, chamfer=.09):
    """A hexagonal crystal from base along axis: six unequal faces, narrow bright chamfers on its edges, a pointed
    termination whose apex sits off the axis. c0 is its colour at the foot, c1 at the point; edge the chamfers'
    colour (default: toward clear). core (a glow colour) puts a slim prism of light inside it. Returns its apex."""
    slot = CRYSTAL if slot is None else slot
    base, ax = np.asarray(base, np.float64), unit(axis)
    A, B = frame(ax)
    ang = (np.arange(6) + rng.uniform(-.14, .14, 6)) * TAU / 6 + rng.uniform(0, TAU)
    rad = r * rng.uniform(.8, 1.0, 6)
    corners = np.stack([rad * np.cos(ang), rad * np.sin(ang)], 1)
    poly = []
    for k in range(6):
        poly.append(corners[k] + (corners[k - 1] - corners[k]) * chamfer)
        poly.append(corners[k] + (corners[(k + 1) % 6] - corners[k]) * chamfer)
    poly = np.array(poly)
    apex = base + ax * length + (A * rng.uniform(-.3, .3) + B * rng.uniform(-.3, .3)) * r
    shaft = length * (1 - tip)
    ts = np.linspace(0, 1, segs + 1)
    rings = np.array([base + ax * shaft * t + (poly[:, :1] * A + poly[:, 1:] * B) * (1 - taper * t) for t in ts])
    c0, c1 = np.asarray(c0, np.float64)[:3], np.asarray(c1, np.float64)[:3]
    clear = np.asarray(CRYSTAL_CLEAR if edge is None else edge, np.float64)[:3]
    bright = slot == GLOW
    for j in range(12):
        k = (j + 1) % 12
        narrow = j % 2 == 0
        jit = 1.0 if bright else rng.uniform(.86, 1.0)

        def shade_(t):
            c = c0 * (1 - t) + c1 * t
            if narrow:
                c = c * .35 + clear * .65
            return rgba(c * jit if bright else np.minimum(c * jit, .9))
        verts, cols, faces = [], [], []
        for i, t in enumerate(ts):
            verts += [rings[i, j], rings[i, k]]
            cols += [shade_(t ** 1.3 * .8)] * 2
            if i:
                faces.append([2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i])
        verts.append(apex)
        cols.append(shade_(1.0))
        faces.append([2 * segs, 2 * segs + 1, 2 * segs + 2])
        part.add(verts, faces, np.array(cols), slot, False)
    part.add(rings[0], [list(range(12))[::-1]], rgba(c0 * (1.0 if bright else .7)), slot, False)
    if core is not None:
        prism(part, base + ax * length * .04, base + ax * length * .82, r * .28, core, GLOW, 6, .35)
    return apex


# ---------------------------------------------------------------- the First Ones

def hand(part, rng, wrist, fdir, back, size, curl, spread, thumb, stone, plate_slot=None, right=False):
    """A First One's hand at `wrist`: fingers along fdir, the back of the hand toward `back`. A dark palm under two
    lapped plates, three long fingers of three faceted phalanges on dark knuckles, and a long thumb (on local +y for
    a left hand; a right hand is the mirror image). curl: radians a joint, per finger. Returns the palm's centre."""
    s = size
    slot = STONE if plate_slot is None else plate_slot
    h = Part('hand', part.slots)
    xs = np.array([-.012, .012, .045, .08, .094]) * s
    hw = np.array([.021, .025, .034, .036, .030]) * s
    ht = np.array([.015, .015, .014, .011, .008]) * s
    a = np.linspace(0, TAU, 12, endpoint=False)
    rings = np.array([[(x, w * np.sign(np.cos(q)) * abs(np.cos(q)) ** .7, t * np.sign(np.sin(q)) * abs(np.sin(q)) ** .7) for q in a] for x, w, t in zip(xs, hw, ht)])
    skin(h, rings, CORE, ROCK, rings - np.stack([rings[..., 0], 0 * rings[..., 1], 0 * rings[..., 2]], -1), True, True)
    cap(h, rings[0], (-1, 0, 0), CORE, ROCK)
    cap(h, rings[-1], (1, 0, 0), CORE, ROCK)
    obox(h, V(.036, 0, .0165) * s, V(.036, .029, .0042) * s, stone(), slot, .003 * s)
    obox(h, V(.066, 0, .0195) * s, V(.019, .032, .0036) * s, stone(), slot, .0025 * s, basis((1, 0, -.12)))
    hoop(h, V(-.004, 0, 0) * s, (1, 0, 0), .0235 * s, .0065 * s, stone(), slot, 12, 6, squash=.72)
    lengths = np.array([.064, .050, .041])
    for i in range(3):
        f = (.96, 1.1, .98)[i]
        fan = (1 - i) * spread
        joint = V(.094, (1 - i) * .0235, 0) * s
        ang = 0.0
        for k in range(3):
            ang += curl[i] * (.85, 1.0, .8)[k]
            d = unit(V(math.cos(ang) * math.cos(fan), math.sin(fan), -math.sin(ang)))
            tip = joint + d * lengths[k] * f * s
            rr = (.0098, .0086, .0074)[k] * s
            ball(h, joint, rr * .98, CORE, ROCK, 8)
            c = stone()
            if k < 2:
                pipe(h, [joint + d * rr * .55, tip - d * rr * .45], [rr * 1.05, rr * .9], c, slot, 6, smooth=False)
            else:
                pipe(h, [joint + d * rr * .55, joint + d * lengths[k] * f * s * .68, tip], [rr * 1.05, rr * .82, rr * .22], c, slot, 6, smooth=False)
            joint = tip
    joint = V(.022, .034, -.005) * s
    ang = 0.0
    for k in range(3):
        ang += thumb * (.8, .9, .7)[k]
        d = unit(V(.72 * math.cos(ang), .62 - .25 * k * thumb, -math.sin(ang) - .12))
        tip = joint + d * (.05, .042, .036)[k] * s
        rr = (.0108, .0094, .008)[k] * s
        ball(h, joint, rr * .98, CORE, ROCK, 8)
        if k < 2:
            pipe(h, [joint + d * rr * .55, tip - d * rr * .45], [rr * 1.05, rr * .9], stone(), slot, 6, smooth=False)
        else:
            pipe(h, [joint + d * rr * .55, joint + (tip - joint) * .68, tip], [rr * 1.05, rr * .82, rr * .22], stone(), slot, 6, smooth=False)
        joint = tip
    f, b = unit(fdir), np.asarray(back, np.float64)
    b = unit(b - f * np.dot(b, f))
    rot = np.stack([f, np.cross(b, f), b], 1)
    graft(part, h, rot, wrist, right)
    return np.asarray(wrist, np.float64) + rot @ (V(.05, 0, -.016) * s)


def arm(part, rng, sh, el, wr, stone, plate_slot=None, r=.036):
    """Shoulder to wrist: a dark core, an elbow ball, and long lapped plates whose free ends lift toward the hand."""
    sh, el, wr = (np.asarray(q, np.float64) for q in (sh, el, wr))
    out = V(0, np.sign(sh[1]) or 1.0, 0)
    pipe(part, [sh, el], [r * .86, r * .74], CORE, ROCK, 12)
    ball(part, el, r * .92, CORE, ROCK, 12)
    pipe(part, [el, wr], [r * .76, r * .56], CORE, ROCK, 12)
    up = capsule(sh, el, r * .9, r * .78, out)
    for i, (u0, u1) in enumerate(((.1, .52), (.46, .9))):
        for j in range(3):
            w0 = j * TAU / 3 + i * .5 + .1
            plate(part, up, (u0, u1), (w0, w0 + TAU / 3 - .2), stone(), plate_slot, (.002, .011), .006, .05, (5, 6), seed=i * 3 + j)
    fo = capsule(el, wr, r * .8, r * .6, out)
    for i, (u0, u1) in enumerate(((.07, .4), (.34, .68), (.62, .93))):
        for j in range(3):
            w0 = j * TAU / 3 + i * .7 - .3
            plate(part, fo, (u0, u1), (w0, w0 + TAU / 3 - .22), stone(), plate_slot, (.002, .010 - .002 * i), .0055, .04, (5, 6), seed=10 + i * 3 + j)
    cup = capsule(el - unit(el - sh) * r, el + unit(wr - el) * r, r * 1.02, r * 1.02, unit(el - (sh + wr) / 2))
    plate(part, cup, (.1, .9), (-1.2, 1.2), stone(), plate_slot, (.004, .008), .006, 0.0, (5, 7), seed=31)


def sliver(part, base, up, out, length, width, thick, colour, slot=None, bow=.012):
    """One sliver of the crown: a thin blade, pointed at both ends, its flat toward `out`."""
    slot = STONE if slot is None else slot
    base, up = np.asarray(base, np.float64), unit(up)
    out = unit(np.asarray(out, np.float64) - up * np.dot(out, up))
    side = np.cross(up, out)
    st = np.array([0, .05, .18, .4, .68, .9, 1.0])
    wf = np.array([.05, .42, .88, 1.0, .72, .3, .04])
    cen = np.array([base + up * length * t + out * bow * math.sin(math.pi * t) for t in st])
    rings = np.array([[c + out * thick * f, c + side * width * f, c - out * thick * f, c - side * width * f] for c, f in zip(cen, wf)])
    k = .82 + .2 * st
    skin(part, rings, lit(colour, np.repeat(k[:, None], 4, 1)), slot, rings - cen[:, None, :], False, True)
    cap(part, rings[0], -up, colour, slot)
    cap(part, rings[-1], up, colour, slot)


HEAD_PROFILE = np.array([(0, .34), (.07, .55), (.18, .76), (.36, .93), (.56, 1.0), (.74, .95), (.86, .8), (.94, .58), (.985, .3), (1.0, 0.0)])


def head_fn(height=.45, wide=.086, front=.096, rear=.12, sweep=.1):
    """The long head in its own frame (its underside on z 0, its top swept back) as fn(T, PHI): T up it (0..1), PHI
    from the front."""
    dense = spline(HEAD_PROFILE, 200)

    def fn(T, PHI):
        T, PHI = np.broadcast_arrays(np.asarray(T, np.float64), np.asarray(PHI, np.float64))
        rho = np.where(T >= 1 - 1e-9, 0.0, np.clip(np.interp(T, dense[:, 0], dense[:, 1]), 0, 1.02))
        c, s = np.cos(PHI), np.sin(PHI)
        e = 2 / 2.35
        cx = -sweep * T ** 1.7
        x = cx + np.where(c >= 0, front, rear) * rho * np.sign(c) * np.abs(c) ** e
        y = wide * rho * np.sign(s) * np.abs(s) ** e
        z = height * T
        return np.stack([x, y, z], -1), np.stack([cx, 0 * y, z], -1)
    return fn


def build_head(part, rng, stone, light, crown, sliver_colour, rigid=False, elder=False):
    """Head, seam of light, back plates and crown in the head's own frame (the caller places it)."""
    fn = head_fn()
    T = (.5 - .5 * np.cos(np.linspace(0, math.pi, 34)))[:, None]
    t0, t1, w0 = .13, .84, .07
    wsm = np.where((T > t0) & (T < t1), w0 * np.sin(math.pi * np.clip((T - t0) / (t1 - t0), 0, 1)) ** .55, 0.0)
    U = np.linspace(0, 1, 45)[None, :]
    PHI = wsm + U * (TAU - 2 * wsm)
    P, C = fn(T + 0 * U, PHI)
    base = np.asarray(stone())[:3]
    k = (.93 + .1 * T + 0 * U) * (1 + .04 * noise2(P[..., 1] * 30 + P[..., 2] * 9, P[..., 2] * 30, 77))
    k = k * (1 - .25 * np.exp(-((PHI - wsm) / .06) ** 2) * (wsm > 0) - .25 * np.exp(-((TAU - wsm - PHI) / .06) ** 2) * (wsm > 0))
    skin(part, P, lit(base, k), STONE, P - C, True)
    cap(part, P[0, :-1], (0, 0, -1), CORE, ROCK)
    # the seam: dark walls down to a floor of light
    rows = np.where(wsm[:, 0] > 0)[0]
    rows = np.r_[rows[0] - 1, rows, rows[-1] + 1]
    L, R = P[rows, 0], P[rows, -1]
    N = grid_normals(P, P - C)
    nl, nr = N[rows, 0], N[rows, -1]
    depth = .006
    Li, Ri = L - nl * depth, R - nr * depth
    M, _ = fn(T[rows, 0], 0.0)
    M = M - unit(nl + nr) * depth * 1.05
    skin(part, np.stack([L, Li]), tone(CORE, .6), ROCK, np.stack([M - L, M - L]), False)
    skin(part, np.stack([R, Ri]), tone(CORE, .6), ROCK, np.stack([M - R, M - R]), False)
    q = np.linspace(0, 1, len(rows))
    bright = .78 + .22 * np.sin(math.pi * q) ** .5
    gc = np.stack([glow(light, bright * .9), glow(light, bright), glow(light, bright * .9)])
    skin(part, np.stack([Li, M, Ri]), gc, GLOW, V(1, 0, 0), True)
    # the back plates: the skull's layers
    for (ta, tb, pa, pb, d) in ((.30, .975, 78, 282, .0065), (.52, .99, 118, 242, .0125)):
        Tg, Pg = np.meshgrid(np.linspace(ta, tb, 12), np.radians(np.linspace(pa, pb, 22)), indexing='ij')
        Q, Cq = fn(Tg, Pg)
        Nq = grid_normals(Q, Q - Cq)
        c = np.asarray(stone())[:3]
        kk = (.9 + .12 * Tg) * (1 + .05 * noise2(Q[..., 1] * 40, Q[..., 2] * 40, 79))
        kk[0, :] *= 1.08
        sheet(part, Q + Nq * d, Q + Nq * (d - .0075), lit(c, kk), STONE, rim=lit(c, np.float64(.55)))
    # the crown: slivers floating a hand's width off the head, round its back and sides
    n = len(crown)
    for i, present in enumerate(crown):
        if not present:
            continue
        a = math.radians(180 + (i - (n - 1) / 2) * (196.0 / (n - 1)))
        side_ = abs(i - (n - 1) / 2) / ((n - 1) / 2)
        tq = .5 if rigid else .56 - .06 * side_
        q0, c0 = fn(tq, a)
        out = unit(V(math.cos(a), math.sin(a) * 1.1, 0))
        length = (.33 if rigid else .34 - .1 * side_ ** 1.5) * (rng.uniform(.8, 1.0) if elder else 1.0)
        up_ = unit(V(0, 0, 1) + (0 if rigid else .06) * out + V(-.0 if rigid else -.1, 0, 0))
        b = q0 + out * .088 + V(0, 0, .0 if rigid else .02 * (1 - side_))
        sliver(part, b, up_, out, length, .021 if not rigid else .018, .0065, sliver_colour(), bow=0.0 if rigid else .004)


def first_one(name, height, seed, pose, crown, kind='serene'):
    """A First One in the native form, built at about 2.3 m and scaled to `height`. kind: 'serene' (a keeper),
    'elder' (Aeon) or 'vigil' (Maruth). pose: 'folded', 'lantern', 'tablet', 'open', 'staff'."""
    rng = np.random.default_rng(seed)
    elder, vigil = kind == 'elder', kind == 'vigil'
    slots = [STONE, ROCK, CLOTH, GLOW]
    slots += [ELECTRUM] if elder else [ALLOY]
    if vigil:
        slots += [ENAMEL, CRYSTAL]
    if pose == 'tablet':
        slots += [CRYSTAL]
    p = Part(name, slots)
    light = GLOW_VIGIL if vigil else GLOW_SERENE
    metal, metal_slot = (tone(ELECTRUM_PALE, .92), ELECTRUM) if elder else (tone(ALLOY_SILVER, 1.05), ALLOY)
    if elder:
        s_base, s_alt = mix(STONE_PALE, STONE_WORN, .7), STONE_SHADE
    elif vigil:
        s_base, s_alt = mix(STONE_PALE, STONE_SHADE, .45), STONE_DARK
    else:
        s_base, s_alt = tone(mix(STONE_PALE, CRYSTAL_CLEAR, .22), 1.08), STONE_PALE

    def stone(w=.1):
        return tone(mix(s_base, s_alt, rng.uniform(0, .38 if elder else .25)), rng.uniform(1 - w, 1.0))

    def armour():
        return tone(mix(ENAMEL_NIGHT, CLOTH_VIOLET, rng.uniform(.02, .12)), rng.uniform(1.0, 1.5))
    body_plate, body_slot = (armour, ENAMEL) if vigil else (stone, STONE)
    if elder:
        c_skirt, c_trim, c_mantle, c_line, c_lining, c_panel = CLOTH_INDIGO, tone(CLOTH_PEARL, .9), tone(CLOTH_PEARL, 1.06), tone(ELECTRUM_PALE, .78), tone(CLOTH_INDIGO, 1.3), tone(CLOTH_PEARL, 1.0)
    elif vigil:
        c_skirt, c_trim, c_mantle, c_line, c_lining, c_panel = col(.035, .03, .06), CLOTH_VIOLET, CLOTH_VIOLET, tone(ALLOY_SILVER, .8), col(.05, .035, .09), tone(CLOTH_VIOLET, .8)
    else:
        c_skirt, c_trim, c_mantle, c_line, c_lining, c_panel = tone(CLOTH_PEARL, 1.04), CLOTH_INDIGO, tone(CLOTH_INDIGO, 1.25), CLOTH_PEARL, tone(CLOTH_INDIGO, .7), tone(CLOTH_INDIGO, 1.15)

    # ---- the skirt: heavy cloth to the ground, its folds deepening toward the hem
    skirt = Body([(0, .335, .30, .375, -.02), (.06, .318, .285, .345, -.016), (.3, .272, .236, .272, -.01), (.6, .218, .182, .2, 0),
                  (.9, .176, .14, .15, 0), (1.1, .146, .112, .12, 0), (1.22, .128, .1, .105, 0)], soft=.05)

    def skirt_fold(th, z):
        a = .105 * np.clip((1.16 - z) / 1.16, 0, 1) ** 1.15 * (1 - .8 * np.exp(-(wrap(th) / .45) ** 2))
        w = .58 * np.cos(11 * th + .5 * np.sin(2.6 * z + seed)) + .27 * np.cos(19 * th + 1.3 + 1.2 * z) + .15 * np.cos(31 * th + 2.1 - z)
        return a, w
    nth = 106 if elder else 104
    zs = np.r_[0.0, .014, .07, .088, .104, np.linspace(.18, 1.22, 24 if elder else 20)]
    Zg, Tg = np.meshgrid(zs, np.linspace(0, TAU, nth, endpoint=False), indexing='ij')
    a, w = skirt_fold(Tg, Zg)
    G = skirt.point(Tg, Zg, k=1 + a * w + .012 * (Zg < .02))
    k = 1 - 3.2 * a * np.clip(-w, 0, 1) + 1.0 * a * np.clip(w, 0, 1) + .05 * noise2(Tg * 23, Zg * 31, seed)
    k = k * (.8 + .2 * np.clip(Zg / .5, 0, 1))
    cols = np.where(((Zg < .075) | ((Zg > .085) & (Zg < .11)))[..., None], lit(c_trim, k), lit(c_skirt, k))
    cols = blend(cols, DUST, (.2 if elder or vigil else .3) * np.clip((.3 - Zg) / .3, 0, 1) ** 1.6 * (.6 + .4 * noise2(Tg * 9, Zg * 14, seed + 1)))
    skin(p, G, cols, CLOTH, G - skirt.centre(Zg), True, True)
    low = np.stack([G[0], np.tile(V(-.02, 0, 0), (nth, 1))])
    skin(p, low, lit(c_skirt, np.float64(.25)), CLOTH, V(0, 0, -1), False, True)

    # ---- the hanging panel down the front, the sash, its knot and tails
    pw = .082
    pz = np.r_[np.linspace(1.18, .44, 16), .40, .36, .32, .29]
    wz = pw * np.clip((pz - .27) / .13, .04, 1.0) ** .8
    yq = np.array([-1, -.84, -.72, -.36, 0, .36, .72, .84, 1.0])
    Zp, Yq = np.meshgrid(pz, yq, indexing='ij')
    Yp = Yq * wz[:, None]
    Tp = np.arcsin(np.clip(Yp / skirt.dims(Zp)[0], -1, 1))
    a, w = skirt_fold(Tp, Zp)
    outer = skirt.point(Tp, Zp, .016, 1 + a * w)
    kk = (.86 + .14 * np.clip((Zp - .3) / .9, 0, 1)) * (1 + .05 * noise2(Yp * 60, Zp * 40, seed + 2))
    stripe = (np.abs(Yq) > .7) & (np.abs(Yq) < .9)
    sheet(p, outer, skirt.point(Tp, Zp, .006, 1 + a * w), np.where(stripe[..., None], lit(c_line, kk), lit(c_panel, kk)), CLOTH, rim=lit(c_panel, np.float64(.6)))
    Zs, Ts = np.meshgrid(np.linspace(1.115, 1.215, 6), np.linspace(0, TAU, 56, endpoint=False), indexing='ij')
    ripple = .004 * np.cos((Zs - 1.115) / .1 * math.pi * 3 + 2 * np.sin(3 * Ts))
    so = skirt.point(Ts, Zs, .022 + ripple)
    sheet(p, so, skirt.point(Ts, Zs, .004), lit(c_trim, .86 + 18 * ripple), CLOTH, rim=lit(c_trim, np.float64(.6)), wrap_v=True)
    knot = skirt.point(.62, 1.165, .034)
    ball(p, knot, .026, tone(c_trim, .9), CLOTH, 10, (1, 1, .85))
    for dy, ln in ((.012, .36), (.04, .27)):
        path = curve([knot, knot + V(.012, dy, -.08), knot + V(.022, dy * 1.6, -ln * .6), knot + V(.03, dy * 1.9, -ln)], 9)
        band(p, path, np.linspace(.036, .05, 9), .005, unit(V(.75, .66, 0)), tone(c_trim, .95), CLOTH)
    revolve(p, [(0, .012), (.014, .011), (.03, .004), (.034, 0)][::-1], metal, metal_slot, 14, along((1, 0, 0)), skirt.point(0, 1.165, .024), caps=(True, False))

    # ---- the torso: a dark core, plates lapped like strata
    torso = Body([(1.14, .106, .086, .086, 0), (1.24, .098, .08, .08, 0), (1.34, .124, .1, .095, 0), (1.46, .16, .12, .11, 0),
                  (1.56, .186, .126, .116, 0), (1.63, .19, .112, .106, 0), (1.69, .12, .08, .08, 0)], power=2.3, soft=.02)
    Zg, Tg = np.meshgrid(np.linspace(1.14, 1.69, 16), np.linspace(0, TAU, 36, endpoint=False), indexing='ij')
    G = torso.point(Tg, Zg)
    skin(p, G, lit(CORE, .7 + .3 * np.clip((Zg - 1.14) / .3, 0, 1)), ROCK, G - torso.centre(Zg), True, True)
    for z in (1.185, 1.215, 1.245):                                # the waist's joint rings
        Tr = np.linspace(0, TAU, 28, endpoint=False)
        pipe(p, torso.point(Tr, np.full(28, z), .004), .0075, body_plate(), body_slot, 6, closed=True)
    for i, (z1, z0) in enumerate(((1.27, 1.37), (1.355, 1.455), (1.44, 1.545), (1.53, 1.64), (1.625, 1.69))):
        cuts = np.radians(np.array([-30, 30, 82, 138, 222, 278]) + (0 if i % 2 == 0 else 26))
        for j in range(6):
            w0, w1 = cuts[j], cuts[(j + 1) % 6] + (TAU if j == 5 else 0)
            plate(p, torso.fn, (z0, z1), (w0 + .035, w1 - .035), body_plate(), body_slot, (.003, .017), .008, -.022, (6, 9), seed=40 + i * 6 + j)

    # ---- arms and hands, by pose
    def limb(side, el, wr, fdir, back, curl, spread=.08, thumb=.35):
        sh = V(0, side * .19, 1.612)
        arm(p, rng, sh, el, wr, body_plate if vigil else stone, body_slot if vigil else STONE)
        return hand(p, rng, np.asarray(wr, np.float64) + unit(np.asarray(wr) - np.asarray(el)) * .012, fdir, back, 1.0, curl, spread, thumb, stone, right=side > 0)
    if pose == 'folded':
        limb(1, V(.05, .268, 1.25), V(.158, .085, 1.365), V(.04, -1, .46), V(1, .1, .15), (.22, .28, .34), .05, .3)
        limb(-1, V(.05, -.268, 1.25), V(.186, -.085, 1.345), V(.02, 1, .46), V(1, -.1, .15), (.2, .26, .32), .05, .3)
    elif pose == 'lantern':
        wr = V(.31, .228, 1.3)
        limb(1, V(.07, .266, 1.235), wr, V(1, 0, -.12), V(0, .12, 1), (1.05, 1.1, 1.15), .02, .7)
        limb(-1, V(.0, -.276, 1.24), V(.05, -.264, .875), V(.12, 0, -1), V(.1, -1, 0), (.28, .34, .4), .06, .3)
        lantern(p, wr + V(.092, 0, -.03), metal, metal_slot, light)
    elif pose == 'tablet':
        n_, d_ = unit(V(.57, 0, .82)), unit(V(.82, 0, -.57))
        C = V(.31, 0, 1.3)
        for s_ in (1, -1):
            limb(s_, V(.03, s_ * .268, 1.25), C - d_ * .135 - n_ * .034 + V(0, s_ * .1, 0), d_ + V(0, -s_ * .1, 0), -n_, (.08, .1, .12), .1, .25)
        tablet(p, np.stack([V(0, 1, 0), np.cross(n_, V(0, 1, 0)), n_], 1), C, .42, stone(), metal, metal_slot)
    elif pose == 'open':
        for s_ in (1, -1):
            limb(s_, V(.05, s_ * .272, 1.25), V(.27, s_ * .305, 1.13), V(.86, s_ * .3, -.12), V(-.12, s_ * .3, -1), (.1, .13, .18), .2, .2)
    else:                                                        # 'staff': the right hand on a tall staff, the left at rest
        wr = V(.25, .345, 1.34)
        limb(1, V(.06, .272, 1.24), wr, V(1, -.1, .12), V(.1, 1, 0), (1.0, 1.05, 1.1), .02, .75)
        limb(-1, V(.0, -.276, 1.24), V(.04, -.266, .875), V(.1, 0, -1), V(.1, -1, 0), (.5, .55, .6), .03, .5)
        staff(p, rng, V(wr[0] + .085, wr[1] - .036, 0), 2.24, metal, metal_slot)

    # ---- the mantle: hung from the collar over the shoulders, open at the front, long at the back
    mant = Body([(.10, .37, .31, .42, -.01), (.6, .335, .25, .34, -.02), (1.0, .315, .205, .265, -.01), (1.2, .306, .185, .225, 0),
                 (1.38, .3, .168, .195, 0), (1.5, .29, .152, .172, 0), (1.6, .272, .134, .144, 0), (1.645, .228, .112, .122, 0),
                 (1.675, .13, .085, .092, 0), (1.70, .085, .07, .075, 0), (1.725, .068, .06, .064, 0)], power=2.2, soft=.02)
    z_top = 1.722
    z_front, z_back = (.86, .1) if elder else (1.3, .8) if vigil else (1.37, .93)
    u = np.r_[0, .012, .028, np.linspace(.055, .945, 70 if elder else 54), .972, .988, 1.0]
    g = np.r_[np.linspace(0, .13, 8)[:-1], np.linspace(.13, .93, 32 if elder else 22), .955, .98, 1.0]
    Gg, Ug = np.meshgrid(g, u, indexing='ij')
    Sg = np.abs(2 * Ug - 1)
    Zg = z_top - (z_top - (z_back + (z_front - z_back) * Sg ** 2.4)) * Gg
    op = np.radians(np.interp(Zg, [1.3, 1.45, 1.62, 1.72], [74, 62, 42, 26]))
    Tg = op + Ug * (TAU - 2 * op)
    amp = .11 if elder else .075
    a = amp * np.clip((1.57 - Zg) / .45, 0, 1) ** 1.2
    w = .55 * np.cos(9 * Tg + .6 * np.sin(3 * Zg + seed)) + .3 * np.cos(16 * Tg + 1 + 1.4 * Zg) + .15 * np.cos(27 * Tg + 2.2)
    outer = mant.point(Tg, Zg, k=1 + a * w)
    N = grid_normals(outer, outer - mant.centre(Zg))
    k = 1 - 4.2 * a * np.clip(-w, 0, 1) + 1.2 * a * np.clip(w, 0, 1) + .05 * noise2(Tg * 19, Zg * 27, seed + 4)
    edge = (Ug < .029) | (Ug > .971) | (Gg > .954)
    line = ((Ug > .05) & (Ug < .075)) | ((Ug > .925) & (Ug < .95)) | ((Gg > .9) & (Gg < .935))
    cols = np.where(edge[..., None], lit(c_trim if not vigil else tone(CLOTH_VIOLET, .55), k), np.where(line[..., None], lit(c_line, k), lit(c_mantle, k)))
    if elder:
        cols = blend(cols, DUST, .3 * np.clip((.5 - Zg) / .5, 0, 1) ** 1.5)
    sheet(p, outer, outer - N * .007, cols, CLOTH, back=lit(c_lining, .7 * k), rim=lit(c_mantle, np.float64(.6)))

    # ---- the neck, the collar
    pipe(p, [(0, 0, 1.66), (.006, 0, 1.75), (.014, 0, 1.85)], [.05, .044, .04], CORE, ROCK, 14)
    for z in (1.765, 1.792, 1.819):
        hoop(p, (.008 + (z - 1.75) * .08, 0, z), (0, 0, 1), .043, .0085, stone(), STONE, 16, 6)

    def collar_fn(rise, r0=.07, r1=.16):
        def fn(U, W):
            U, W = np.broadcast_arrays(np.asarray(U, np.float64), np.asarray(W, np.float64))
            r = r0 + (r1 - r0) * U
            z = 1.728 + rise * U - (.075 * U + .03 * U * U if rise == 0 else 0)
            C = np.stack([0 * U, 0 * U, z], -1)
            return C + np.stack([r * np.cos(W) * .92, r * np.sin(W) * 1.38 if rise == 0 else r * np.sin(W) * 1.12, 0 * U], -1), C - V(0, 0, .2 if rise == 0 else -0.0)
        return fn
    if elder:                                                    # the electrum collar: a standing ring and nine lapped leaves
        start = fl.ring(p, [(.058, 1.715), (.074, 1.712), (.071, 1.772), (.059, 1.772)], metal, ELECTRUM, 28)
        v = np.asarray(p.v[start:])
        v[:, 1] *= 1.1
        p.v[start:] = v.tolist()
        for j in range(9):
            w0 = j * TAU / 9 + TAU / 18
            plate(p, collar_fn(0), (.0, .9), (w0 + .03, w0 + TAU / 9 - .03), tone(ELECTRUM_PALE, rng.uniform(.8, .98)), ELECTRUM, (.004, .012), .006, .12, (6, 7), seed=60 + j,
                  rim=tone(ELECTRUM_PALE, .5))
        obox(p, (.158, 0, 1.6), (.004, .026, .026), metal, ELECTRUM, .003, basis((1, 0, .25)) @ np.array([[1, 0, 0], [0, .7071, -.7071], [0, .7071, .7071]]))
    elif vigil:                                                  # the high armoured collar, and pauldron plates over the mantle
        for j, (w0, w1) in enumerate(((.62, 1.75), (1.8, 2.85), (2.9, TAU - 2.9), (TAU - 2.85, TAU - 1.8), (TAU - 1.75, TAU - .62))):
            plate(p, collar_fn(.2, .078, .125), (0.0, 1.0 if j in (1, 2, 3) else .7), (w0, w1), tone(ALLOY_SILVER, rng.uniform(.62, .8)), ALLOY, (.004, .004), .007, .0, (7, 8), seed=60 + j,
                  rim=tone(ALLOY_SILVER, .4))
        hoop(p, (0, 0, 1.727), (0, 0, 1), .08, .012, tone(ALLOY_SILVER, .6), ALLOY, 28, 6, squash=1.12)
        for s_ in (1, -1):
            for i, (za, zb, lift) in enumerate(((1.665, 1.6, .03), (1.62, 1.535, .022), (1.56, 1.46, .016))):
                c0 = math.radians(90) * s_
                plate(p, mant.fn, (za, zb), (c0 - .62 + .06 * i, c0 + .62 - .06 * i), tone(ALLOY_SILVER, rng.uniform(.6, .78)), ALLOY, (lift * .5, lift), .008, -.03, (6, 10),
                      seed=70 + i, rim=tone(ALLOY_SILVER, .38))
        revolve(p, [(0, .012), (.014, .011), (.026, .004), (.03, 0)][::-1], tone(ALLOY_SILVER, .8), ALLOY, 12, along((1, 0, 0)), V(.075, 0, 1.7), caps=(True, False))
    else:                                                        # a rolled cloth collar and a clasp
        hoop(p, (0, 0, 1.722), (0, 0, 1), .074, .017, tone(c_trim, 1.1), CLOTH, 28, 8, squash=1.08)
        revolve(p, [(0, .012), (.012, .011), (.024, .004), (.028, 0)][::-1], metal, metal_slot, 12, along((1, 0, -.2)), V(.082, 0, 1.712), caps=(True, False))

    # ---- the head and the crown
    h0 = len(p.v)
    build_head(p, rng, lambda: stone(.05), light, crown, lambda: stone(.14), rigid=vigil, elder=elder)
    pitch = 6.0 if elder else (-2.0 if vigil else 2.0)
    q = math.radians(pitch)
    place(p, h0, np.array([[math.cos(q), 0, math.sin(q)], [0, 1, 0], [-math.sin(q), 0, math.cos(q)]]), V(.022, 0, 1.815))

    weather(p, seed, 2.3, under=.16, dirt=.2 if elder else .1, streak=.2 if elder else .08, lichen=.3 if elder else 0.0, pits=.3 if elder else .1,
            dust=.1 if elder else .03)
    return stand(p, height)


def lantern(part, top, metal, slot, light):
    """A hand lantern hung from `top` (the middle of its carrying ring): a crystal of light in three metal fingers."""
    top = np.asarray(top, np.float64)
    hoop(part, top, (0, 1, 0), .03, .0048, metal, slot, 16, 6)
    pipe(part, [top - V(0, 0, .03), top - V(0, 0, .075)], .0045, metal, slot, 6)
    zt = top[2] - .075
    o = V(top[0], top[1], 0)
    revolve(part, [(.04, zt - .046), (.056, zt - .042), (.05, zt - .03), (.014, zt - .004), (0, zt)], metal, slot, 14, origin=o, caps=(True, False))
    rng = np.random.default_rng(5)
    crystal(part, o + V(0, 0, zt - .05), (0, 0, -1), .037, .2, rng, glow(light, .95), glow(light, .8), GLOW, tip=.4, taper=.25, edge=GLOW_WHITE)
    for k in range(3):
        a = k * TAU / 3 + .4
        e = V(math.cos(a), math.sin(a), 0)
        path = curve([o + e * .05 + V(0, 0, zt - .044), o + e * .06 + V(0, 0, zt - .13), o + e * .04 + V(0, 0, zt - .22), o + e * .008 + V(0, 0, zt - .275)], 9)
        pipe(part, path, np.linspace(.0052, .0036, 9), metal, slot, 6)
    ball(part, o + V(0, 0, zt - .282), .011, metal, slot, 8)


def staff(part, rng, foot, length, metal, slot):
    """Maruth's staff, upright from `foot`: a slender alloy shaft with bands, three claws and a small violet crystal."""
    foot = np.asarray(foot, np.float64)
    z = np.array([0, .02, .06, length - .32, length - .3])
    pipe(part, foot + np.stack([0 * z, 0 * z, z], 1), [.006, .014, .0125, .0115, .016], tone(metal, .8), slot, 10)
    for h in (.09, .6, 1.2, 1.5, length - .34):
        fl.ring(part, [(.0125, -.012), (.019, -.009), (.019, .009), (.0125, .012)], metal, slot, 12, origin=foot + V(0, 0, h))
    zc = length - .3
    crystal(part, foot + V(0, 0, zc + .02), (0, 0, 1), .03, .2, rng, CRYSTAL_VIOLET, mix(CRYSTAL_VIOLET, CRYSTAL_CLEAR, .5), CRYSTAL, tip=.4, taper=.05, core=glow(GLOW_VIGIL, .8))
    for k in range(3):
        a = k * TAU / 3 + .3
        e = V(math.cos(a), math.sin(a), 0)
        path = curve([foot + e * .012 + V(0, 0, zc - .01), foot + e * .05 + V(0, 0, zc + .03), foot + e * .046 + V(0, 0, zc + .1), foot + e * .03 + V(0, 0, zc + .16)], 8)
        pipe(part, path, np.linspace(.0062, .003, 8), metal, slot, 6)


def tablet(part, rot, origin, length, stone_colour, metal, metal_slot, inlay=None):
    """A record tablet: a stone leaf (its length along local x, its face toward local z) with a crystal inlay and a
    line of metal down its midrib. No writing: the record is in the crystal."""
    start = len(part.v)
    half_w, t = length * .26, length * .028
    s = np.linspace(0, 1, 21)[:, None]
    q = np.linspace(-1, 1, 11)[None, :]
    w = half_w * np.sin(math.pi * np.clip(.04 + .92 * s, 0, 1)) ** .62 * (1.08 - .3 * s)
    X = (s - .5) * length + 0 * q
    Y = w * q
    dome = t * (1 - .55 * np.abs(q) ** 2.5) * (.55 + .45 * np.sin(math.pi * s) ** .5)
    k = (.9 + .1 * (1 - np.abs(q))) * (1 + .06 * noise2(X * 40, Y * 40, 3))
    sheet(part, np.stack([X, Y, dome], -1), np.stack([X, Y, -dome], -1), lit(stone_colour, k), STONE, rim=lit(stone_colour, np.float64(.7)))
    cc = mix(CRYSTAL_ICE, CRYSTAL_CLEAR, .3) if inlay is None else inlay
    for x, r in ((-.02 * length, .085), (.2 * length, .04), (-.24 * length, .04)):
        r = r * length
        z = t * .99
        part.add([(x - r * 1.5, 0, z), (x, -r, z), (x + r * 1.5, 0, z), (x, r, z), (x, 0, z + r * .55)], [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]],
                 np.array([cc, cc, cc, cc, tone(CRYSTAL_CLEAR, 1.0)]), CRYSTAL, False)
    for x0, x1 in ((-.43, -.33), (.3, .44)):
        obox(part, ((x0 + x1) / 2 * length, 0, t * .93), ((x1 - x0) / 2 * length, .004 * length / .42, .003), metal, metal_slot, .001)
    place(part, start, rot, origin)


def aeon():
    """SM_AP_Aeon (2.45 m): the elder, hands folded before the chest; a long pearl cloak, an electrum collar, two
    slivers of the crown missing."""
    return first_one('SM_AP_Aeon', 2.45, 811, 'folded', (1, 1, 0, 1, 1, 0, 1), 'elder')


def serene(variant):
    """SM_AP_Serene0..2: keepers. 0 holds a lantern (2.3 m), 1 a tablet (2.1 m), 2 has open hands (2.2 m)."""
    pose, height, crown = (('lantern', 2.3, (1,) * 6), ('tablet', 2.1, (1,) * 5), ('open', 2.2, (1,) * 7))[variant]
    return first_one('SM_AP_Serene%d' % variant, height, 821 + variant, pose, crown, 'serene')


def vigil():
    """SM_AP_Vigil (2.35 m): Maruth, Lens-keeper of the Vigil: violet over near-black enamel, an armoured alloy
    collar and pauldrons, a full rigid crown, a violet seam, one hand on a tall staff."""
    return first_one('SM_AP_Vigil', 2.35, 831, 'staff', (1,) * 7, 'vigil')


# ---------------------------------------------------------------- the Sunderer

def sunderer():
    """SM_AE_Sunderer (about 8 m across, 9 m tall): the Lens's AL command frame. A great ring of white enamel plates
    on a black frame round a hub that carries the violet eye at +x under a brow; four long unweaving arms from the
    ring, each ending in three crystal tines round a violet emitter; a crest of three vanes, a keel with a down-
    pointing tine; red AL signal lights on ring, elbows and vanes; and at its back (-x) the exposed crystal heart in
    an open cage, which reads as the vulnerable part. Centred on its bounds (it hovers)."""
    rng = np.random.default_rng(905)
    p = Part('SM_AE_Sunderer', (ENAMEL, ALLOY, GLOW, CRYSTAL, RED))
    X = V(1, 0, 0)
    rx = along(X)

    def white(w=.12):
        return tone(ENAMEL_WHITE, rng.uniform(1 - w, 1.06))
    bare = tone(ALLOY_SILVER, .7)
    dark = tone(ALLOY_DARK, .7)

    def signal(c, n_, r=.07):
        c, n_ = np.asarray(c, np.float64), unit(n_)
        fl.ring(p, [(r * 1.0, -r * .4), (r * 1.5, -r * .4), (r * 1.5, r * .25), (r * 1.0, r * .35)], BLACK, ALLOY, 12, along(n_), c)
        revolve(p, [(r, 0), (r * .8, r * .5), (r * .4, r * .8), (0, r * .9)], np.array([glow(GLOW_AL, q) for q in (.6, .8, 1, 1)]), GLOW, 12, along(n_), c, caps=(False, False))

    # ---- the hub: a black body, enamel plates in three bands
    R3 = V(1.25, 1.6, 1.6)

    def hub(Aa, Bb):
        Aa, Bb = np.broadcast_arrays(np.asarray(Aa, np.float64), np.asarray(Bb, np.float64))
        P = np.stack([R3[0] * np.cos(Aa), R3[1] * np.sin(Aa) * np.cos(Bb), R3[2] * np.sin(Aa) * np.sin(Bb)], -1)
        return P, 0 * P
    Ag, Bg = np.meshgrid(np.linspace(.45, 2.62, 22), np.linspace(0, TAU, 48, endpoint=False), indexing='ij')
    G = hub(Ag, Bg)[0] * .97
    skin(p, G, BLACK, ALLOY, G, True, True)
    for i, (a0, a1) in enumerate(((.74, 1.2), (1.24, 1.76), (1.8, 2.3))):
        n_sec = 8
        for j in range(n_sec):
            b0 = (j + .5 * (i % 2)) * TAU / n_sec
            plate(p, hub, (a0, a1), (b0 + .04, b0 + TAU / n_sec - .04), white(), ENAMEL, (.05, .05), .05, 0.0, (6, 7), wear=.04, seed=i * 8 + j, rim=tone(ENAMEL_WHITE, .45))
    for j in range(8):                                             # red lights round the hub's waist
        b = (j + .5) * TAU / 8
        q, _ = hub(1.5, b)
        if j % 2 == 0:
            signal(q * 1.035, q, .06)

    # ---- the great eye
    fl.ring(p, [(.98, .96), (1.2, .9), (1.24, 1.06), (1.08, 1.2), (.96, 1.16)], white(.05), ENAMEL, 56, rx)
    fl.ring(p, [(.64, 1.12), (.98, 1.1), (.98, 1.17), (.66, 1.2)], BLACK, ALLOY, 48, rx)
    for k in range(18):                                            # the iris's blades
        a = k * TAU / 18
        e = rx @ V(math.cos(a), math.sin(a), 0)
        t_ = rx @ V(-math.sin(a), math.cos(a), 0)
        obox(p, X * 1.2 + e * .81, (.022, .15, .05), dark, ALLOY, .008, np.stack([X, unit(e + t_ * .45), np.cross(X, unit(e + t_ * .45))], 1))
    lat = np.linspace(0, 1, 9)
    revolve(p, [(.66 * math.sin(q * math.pi / 2), 1.14 + .2 * math.cos(q * math.pi / 2)) for q in lat[::-1]],
            np.array([glow(GLOW_VIGIL, .5 + .5 * (1 - q) ** .7) for q in lat[::-1]]), GLOW, 40, rx, caps=(False, False))
    hoop(p, X * 1.325, X, .2, .022, BLACK, ALLOY, 24, 6)
    hoop(p, X * 1.26, X, .46, .014, BLACK, ALLOY, 36, 6)

    def brow_fn(U, W):
        U, W = np.broadcast_arrays(np.asarray(U, np.float64), np.asarray(W, np.float64))
        r = 1.3 - .12 * U
        C = np.stack([.75 + .95 * U, 0 * U, 0 * U], -1)
        return C + np.stack([0 * U, r * np.cos(W), r * np.sin(W)], -1), C
    plate(p, brow_fn, (0.0, .9), (math.radians(28), math.radians(152)), white(.05), ENAMEL, (.02, .02), .07, .22, (7, 16), wear=.04, rim=tone(ENAMEL_WHITE, .45))
    for b in (40, 140):
        q, _ = brow_fn(.5, math.radians(b))
        signal(q + unit(q - V(q[0], 0, 0)) * .03, q - V(q[0], 0, 0), .055)

    # ---- the ring: a black frame, twelve armour segments wrapped over its front, rim and back
    R, x0 = 2.75, -.1
    fl.ring(p, [(2.5, -.36), (2.98, -.36), (2.98, .36), (2.5, .36), (2.44, .2), (2.44, -.2)], BLACK, ALLOY, 96, rx, X * x0)
    sec = np.array([(2.58, .37), (2.96, .385), (3.045, .3), (3.045, -.3), (2.96, -.385), (2.58, -.37)])
    seg = np.r_[0, np.cumsum(norm(np.diff(sec, axis=0), axis=1))]
    seg /= seg[-1]

    def ring_fn(U, W):
        U, W = np.broadcast_arrays(np.asarray(U, np.float64), np.asarray(W, np.float64))
        r, x = np.interp(U, seg, sec[:, 0]), np.interp(U, seg, sec[:, 1])
        return (np.stack([x0 + x, r * np.cos(W), r * np.sin(W)], -1), np.stack([x0 + 0 * x, R * np.cos(W), R * np.sin(W)], -1))
    for j in range(12):
        b0 = j * TAU / 12 + TAU / 24
        plate(p, ring_fn, (0.0, 1.0), (b0 + .022, b0 + TAU / 12 - .022), white(), ENAMEL, (.035, .035), .05, 0.0, (17, 9), wear=.04, seed=30 + j, rim=tone(ENAMEL_WHITE, .45))
        bm = b0 + TAU / 24
        e = V(0, math.cos(bm), math.sin(bm))
        if j % 3 != 1:
            signal(X * (x0 + .425) + e * 2.77, X, .075)
        else:                                                      # the unit's red band
            Bq = np.linspace(b0 + .05, b0 + TAU / 12 - .05, 8)
            for r0, r1 in ((2.66, 2.73),):
                o = np.array([[(x0 + .43, r * math.cos(b), r * math.sin(b)) for b in Bq] for r in (r0, r1)])
                sheet(p, o, o - V(.02, 0, 0), tone(AL_RED, 1.0), RED, rim=tone(AL_RED, .6))
        fl.rivets(p, [X * (x0 + .425) + V(0, math.cos(b), math.sin(b)) * r for b in (b0 + .06, b0 + TAU / 12 - .06) for r in (2.64, 2.9)], X, .028, bare, ALLOY)
    # ---- spokes from hub to ring, each with a fairing and a conduit
    spokes = [math.radians(d) for d in (90, 270, 38, 142, 218, 322)]
    for b in spokes:
        e = V(0, math.cos(b), math.sin(b))
        fl.strut(p, e * 1.45 + X * x0, e * 2.52 + X * x0, .34, .3, BLACK, ALLOY, up=X, bevel=.04)
        obox(p, e * 2.0 + X * (x0 + .17), (.42, .12, .03), white(), ENAMEL, .02, np.stack([e, np.cross(X, e), X], 1))
        t_ = np.cross(X, e)
        pipe(p, curve([e * 1.4 + t_ * .26 + X * (x0 - .1), e * 1.95 + t_ * .3 + X * (x0 - .2), e * 2.5 + t_ * .24 + X * (x0 - .1)], 8), .045, dark, ALLOY, 8)

    # ---- the four unweaving arms
    def s_arm(sh, el, wr, aim_at, k):
        sh, el, wr = V(*sh), V(*el), V(*wr)
        ua, fa = unit(el - sh), unit(wr - el)
        hinge = unit(np.cross(ua, fa))
        radial = unit(V(0, sh[1], sh[2]))
        pipe(p, [sh - hinge * .36, sh + hinge * .36], .36, BLACK, ALLOY, 28)
        for sg in (-1, 1):
            pipe(p, [sh + sg * hinge * .36, sh + sg * hinge * .45], [.31, .24], white(), ENAMEL, 28)
            fl.rivets(p, [sh + sg * hinge * .41 + (rx @ V(math.cos(a), math.sin(a), 0)) * .0 + _perp(hinge, a) * .27 for a in np.arange(8) * TAU / 8], sg * hinge, .028, bare, ALLOY)
        pipe(p, [sh, el], [.2, .17], BLACK, ALLOY, 18)
        up = capsule(sh, el, .2, .17, radial)
        plate(p, up, (.2, .86), (-1.35, 1.35), white(), ENAMEL, (.06, .06), .05, .0, (7, 10), wear=.04, seed=k, rim=tone(ENAMEL_WHITE, .45))
        plate(p, up, (.26, .8), (math.pi - 1.1, math.pi + 1.1), white(), ENAMEL, (.05, .05), .045, .0, (6, 8), wear=.04, seed=k + 1, rim=tone(ENAMEL_WHITE, .45))
        side = np.cross(ua, radial)
        a_, b_ = sh + ua * .25 + side * .3, el - ua * .3 + side * .26
        pipe(p, [a_, a_ + (b_ - a_) * .58], .07, dark, ALLOY, 10)
        pipe(p, [a_ + (b_ - a_) * .5, b_], .04, bare, ALLOY, 8)
        ball(p, el, .28, BLACK, ALLOY, 20)
        pipe(p, [el - hinge * .31, el + hinge * .31], .2, dark, ALLOY, 20)
        for sg in (-1, 1):
            pipe(p, [el + sg * hinge * .31, el + sg * hinge * .37], [.24, .18], white(), ENAMEL, 20)
            signal(el + sg * hinge * .375, sg * hinge, .075)
        pipe(p, [el, wr], [.16, .115], BLACK, ALLOY, 16)
        face = unit(radial + X * .3)
        fo = capsule(el, wr, .16, .115, face)
        for i, (u0, u1) in enumerate(((.1, .38), (.36, .64), (.62, .87))):
            plate(p, fo, (u0, u1), (-1.25, 1.25), white(), ENAMEL, (.035, .075), .04, .03, (6, 9), wear=.04, seed=k + 3 + i, rim=tone(ENAMEL_WHITE, .45))
        plate(p, fo, (.14, .84), (math.pi - .8, math.pi + .8), white(), ENAMEL, (.04, .04), .035, .0, (7, 6), wear=.04, seed=k + 7, rim=tone(ENAMEL_WHITE, .45))
        Ur = np.linspace(.895, .935, 2)[:, None] + 0 * np.linspace(0, TAU, 20)[None, :]
        Wr = 0 * Ur + np.linspace(0, TAU, 20, endpoint=False)[None, :]
        Pq, Cq = fo(Ur, Wr)
        sheet(p, Pq + unit(Pq - Cq) * .035, Pq, tone(AL_RED, 1.0), RED, rim=tone(AL_RED, .6), wrap_v=True)
        Pc, Cc = fo(np.linspace(.12, .95, 12), np.full(12, 1.75))
        pipe(p, Pc + unit(Pc - Cc) * .05, .02, np.array([glow(GLOW_VIGIL, q) for q in np.linspace(.25, .8, 12)]), GLOW, 6)
        d = unit(V(*aim_at) - wr)
        pipe(p, [wr - d * .16, wr + d * .04, wr + d * .2], [.15, .2, .25], BLACK, ALLOY, 20)
        fl.ring(p, [(.25, -.05), (.3, -.03), (.3, .05), (.25, .06)], white(), ENAMEL, 24, along(d), wr + d * .2)
        fl.disc(p, wr + d * .21, d, .2, glow(GLOW_VIGIL, 1.0), GLOW, 20, dome=.07, rim=glow(GLOW_VIGIL, .45))
        A_, B_ = frame(d)
        for j in range(3):
            a = j * TAU / 3 + k
            e = A_ * math.cos(a) + B_ * math.sin(a)
            base = wr + d * .1 + e * .2
            td = unit(d + e * .07)
            crystal(p, base, td, .115, rng.uniform(1.7, 1.95), rng, CRYSTAL_VIOLET, mix(CRYSTAL_VIOLET, CRYSTAL_CLEAR, .7), tip=.3, taper=.3, core=glow(GLOW_VIGIL, .7))
            fl.strut(p, wr + e * .26 - d * .05, base + td * .5 + e * .1, .09, .06, BLACK, ALLOY, up=e, bevel=.015)
            obox(p, base + td * .52 + e * .06, (.05, .07, .06), dark, ALLOY, .012, np.stack([td, np.cross(e, td), e], 1))
    for k, (sy, sz) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        j = rng.uniform(-.12, .12, 4)
        if sz > 0:
            s_arm((x0 - .05, sy * 2.42, 1.9), (-.75 + j[0], sy * 3.72, 3.05 + j[1]), (2.35 + j[2], sy * 2.55, 2.1 + j[3]), (4.6, sy * 1.5, 1.2), 10 * k)
        else:
            s_arm((x0 - .05, sy * 2.42, -1.9), (-.75 + j[0], sy * 3.6, -2.95 + j[1]), (2.25 + j[2], sy * 2.45, -2.0 + j[3]), (4.6, sy * 1.4, -1.1), 10 * k)

    # ---- the crest: three vanes on the ring's crown
    for b, top, c0 in ((90, 4.42, .1), (72, 3.95, 0), (108, 3.95, 0)):
        e = V(0, math.cos(math.radians(b)), math.sin(math.radians(b)))
        fl.fin(p, [X * (x0 + .34) + e * 3.0, X * (x0 - .5) + e * 3.0, X * (x0 - .62) + e * top, X * (x0 - .28) + e * (top - .12)], .12, white(), ENAMEL,
               BLACK, ALLOY, taper=.4, n=(4, 6))
        fl.strut(p, X * (x0 - .1) + e * 2.95, X * (x0 - .3) + e * (top - .8), .1, .2, BLACK, ALLOY, up=np.cross(X, e), bevel=.02)
        signal(X * (x0 - .44) + e * (top + .02), e, .06)
    # ---- the keel: a plated spine under the ring, a violet ring and a down-pointing tine
    kt, kb = V(x0, 0, -2.95), V(x0, 0, -4.3)
    pipe(p, [kt, (kt + kb) / 2, kb], [.42, .3, .17], BLACK, ALLOY, 24)
    kf = capsule(kt, kb, .43, .18, X)
    for i, (u0, u1) in enumerate(((.03, .48), (.44, .9))):
        for j in range(4):
            w0 = j * TAU / 4 + i * .78 + .08
            plate(p, kf, (u0, u1), (w0, w0 + TAU / 4 - .16), white(), ENAMEL, (.03, .07), .04, .05, (6, 7), wear=.04, seed=80 + i * 4 + j, rim=tone(ENAMEL_WHITE, .45))
    hoop(p, kb + V(0, 0, .12), (0, 0, 1), .27, .035, glow(GLOW_VIGIL, .8), GLOW, 24, 6)
    crystal(p, kb + V(0, 0, .05), (0, 0, -1), .12, .5, rng, CRYSTAL_VIOLET, CRYSTAL_ICE, tip=.5, taper=.2, core=glow(GLOW_VIGIL, .7))
    for sy in (-1, 1):
        fl.fin(p, [V(x0 + .3, sy * .36, -3.0), V(x0 - .35, sy * .36, -3.0), V(x0 - .5, sy * 1.05, -3.75), V(x0 - .2, sy * .95, -3.7)], .08, white(), ENAMEL, BLACK, ALLOY,
               taper=.4, n=(3, 4))

    # ---- the heart at its back: crystals growing from a bowl of violet light, in an open cage
    fl.ring(p, [(.78, -1.26), (1.04, -1.2), (1.08, -.98), (.8, -.94)], BLACK, ALLOY, 40, rx)
    lat = np.linspace(0, 1, 6)
    revolve(p, [(.8 * q, 1.0 + .12 * (1 - q * q)) for q in lat[::-1]], np.array([glow(GLOW_VIGIL, .55 + .45 * (1 - q)) for q in lat[::-1]]), GLOW, 28, along(-X),
            caps=(False, False))
    crystal(p, V(-1.02, 0, 0), -X, .4, 1.95, rng, CRYSTAL_VIOLET, mix(CRYSTAL_ICE, CRYSTAL_CLEAR, .4), tip=.28, taper=.18, core=glow(GLOW_VIGIL, .9), segs=3)
    for j in range(6):
        a = j * TAU / 6 + .3
        e = V(0, math.cos(a), math.sin(a))
        crystal(p, V(-1.03, 0, 0) + e * .46, unit(-X + e * rng.uniform(.3, .55)), rng.uniform(.15, .23), rng.uniform(.8, 1.35), rng, CRYSTAL_VIOLET,
                mix(CRYSTAL_VIOLET, CRYSTAL_ICE, rng.uniform(.3, .9)), tip=.3, taper=.15, core=glow(GLOW_VIGIL, .7))
    for j in range(6):
        a = j * TAU / 6
        e = V(0, math.cos(a), math.sin(a))
        path = curve([-X * 1.15 + e * .95, -X * 1.6 + e * 1.12, -X * 2.2 + e * .95, -X * 2.62 + e * .58], 12)
        pipe(p, path, np.linspace(.07, .045, 12), BLACK, ALLOY, 8)
        obox(p, -X * 1.62 + e * 1.16, (.16, .07, .03), white(), ENAMEL, .012, np.stack([-X, np.cross(e, -X), e], 1))
    hoop(p, -X * 1.62, X, 1.12, .045, BLACK, ALLOY, 40, 6)
    hoop(p, -X * 2.62, X, .58, .05, BLACK, ALLOY, 28, 6)
    for b in (38, 142, 218, 322):                                  # conduits from the heart to the arms' shoulders
        e = V(0, math.cos(math.radians(b)), math.sin(math.radians(b)))
        path = curve([-X * 1.2 + e * 1.0, -X * 1.1 + e * 1.7, -X * .62 + e * 2.4, -X * .46 + e * 2.9], 12)
        pipe(p, path, .075, dark, ALLOY, 10)
        pipe(p, path + X * -.08, .018, np.array([glow(GLOW_VIGIL, q) for q in np.linspace(.7, .2, 12)]), GLOW, 5, cap=False)
    fit(p, 2, 9.0)
    weather(p, 905, 9.0, under=.18, dirt=.12, streak=.2, skip=(GLOW, CRYSTAL), gentle=(RED,))
    return p


def _perp(axis, a):
    A, B = frame(axis)
    return A * math.cos(a) + B * math.sin(a)


# ---------------------------------------------------------------- crystals

def _foot(p, rng, seed, size, offset=(0, 0, 0), yaw=0.0):
    r = fl.rock('foot', ROCK, seed, (ROCK_BLUE, ROCK_PALE), size, strata=.12)
    merge(p, r, offset, yaw)


def _cluster(name, height, seed, count, spread, foot, great=False):
    rng = np.random.default_rng(seed)
    p = Part(name, (CRYSTAL, ROCK, GLOW))
    fw, fh = foot
    _foot(p, rng, seed, (fw, fw * .82, fh))
    for k in range(3 if great else 2):
        a = rng.uniform(0, TAU)
        _foot(p, rng, seed + 1 + k, (fw * rng.uniform(.4, .6), fw * rng.uniform(.35, .5), fh * rng.uniform(.5, .8)),
              (math.cos(a) * fw * .36, math.sin(a) * fw * .3, 0), rng.uniform(0, 360))
    z0 = fh * .35
    lean = unit(V(rng.uniform(-.08, .08), rng.uniform(-.08, .08), 1))
    hue = rng.uniform(0, 1)

    def colours(t):
        deep = mix(CRYSTAL_VIOLET, CRYSTAL_ICE, np.clip(hue + rng.uniform(-.35, .35), 0, 1))
        return tone(deep, rng.uniform(.5, .7)), mix(deep, CRYSTAL_CLEAR, rng.uniform(.3, .7))
    c0, c1 = colours(0)
    r_main = height * (.085 if great else .1)
    core = glow(GLOW_SERENE if hue > .5 else GLOW_VIGIL, .75)
    crystal(p, V(0, 0, z0), lean, r_main, height - z0, rng, c0, c1, tip=.16 if great else .22, taper=.14, core=core, segs=6 if great else 3)
    if great:                                                     # spires grown against the great one, and bright seams of light up it
        for a, rr, ln in ((.6, .62, .66), (2.7, .5, .5), (4.4, .42, .36)):
            e = V(math.cos(a), math.sin(a), 0)
            c0, c1 = colours(0)
            crystal(p, V(0, 0, z0 * .8) + e * r_main * .9, unit(lean + e * .07), r_main * rr, height * ln, rng, c0, c1, tip=.2, taper=.1, core=core, segs=4)
        for a in (1.6, 3.6, 5.5):
            e = V(math.cos(a), math.sin(a), 0)
            zz = np.linspace(fh * .9, height * .7, 10)
            path = V(0, 0, 0) + lean[None, :] * (zz[:, None] - z0) + V(0, 0, z0) + e * r_main * (1 - .14 * (zz[:, None] - z0) / (height * .84)) * .93
            pipe(p, path, np.linspace(.07, .02, 10), np.array([glow(GLOW_SERENE, q) for q in np.linspace(.9, .3, 10)]), GLOW, 4, smooth=False)
    for k in range(count):
        a = k * TAU / count + rng.uniform(-.4, .4)
        e = V(math.cos(a), math.sin(a), 0)
        rank = rng.uniform(.25, .75) ** 1.2 * (1 - .3 * k / count)
        tilt = rng.uniform(.15, .75) * spread
        ln = height * rank * (.42 if great else .9)
        base = V(0, 0, z0 * rng.uniform(.4, 1.0)) + e * (fw * rng.uniform(.08, .3))
        c0, c1 = colours(0)
        crystal(p, base, unit(V(0, 0, 1) + e * tilt), max(ln * rng.uniform(.085, .13), .02), ln, rng, c0, c1, tip=rng.uniform(.18, .3), taper=rng.uniform(.05, .2),
                core=core if rank > .4 else None)
    for k in range(5 if great else 4):                            # small seed crystals of light in the rock's cracks
        a = rng.uniform(0, TAU)
        e = V(math.cos(a), math.sin(a), 0)
        base = e * fw * rng.uniform(.2, .34) + V(0, 0, fh * rng.uniform(.3, .55))
        crystal(p, base, unit(V(0, 0, 1) + e * rng.uniform(.5, 1.2)), height * .012 + .012, height * rng.uniform(.05, .08) + .05, rng, core, core, GLOW, tip=.4, edge=GLOW_WHITE)
    ao(p, 0, fh * 1.6, .62, keep=(GLOW, CRYSTAL))
    v = np.asarray(p.v, np.float64)
    v[:, 2] -= v[:, 2].min()
    p.v = (v * (height / v[:, 2].max())).tolist()
    return finish(p, normals=False)


def crystal_cluster(variant):
    """SM_AV_Crystal0..2 (1.5, 2.5 and 4 m): hexagonal crystals, ice blue to violet, growing from a rock foot, a slim
    light in their cores and seed crystals of light in the rock's cracks."""
    height, count, spread, foot = ((1.5, 9, 1.0, (1.1, .42)), (2.5, 12, .85, (1.7, .6)), (4.0, 15, .7, (2.6, .9)))[variant]
    return _cluster('SM_AV_Crystal%d' % variant, height, 931 + variant, count, spread, foot)


def crystal_great():
    """SM_AV_CrystalGreat (18 m): the Garden's landmark: one great spire with three grown against it, a ring of lesser
    crystals at its foot, seams of ice-blue light up its flanks."""
    return _cluster('SM_AV_CrystalGreat', 18.0, 941, 16, .8, (8.5, 2.6), great=True)


# ---------------------------------------------------------------- items

def cache():
    """SM_AN_Cache (0.9 across): a geode split in two: rough rock outside, a pale rind, and a hollow lined with small
    bright crystals round a seed of light."""
    rng = np.random.default_rng(951)
    p = Part('SM_AN_Cache', (ROCK, CRYSTAL, GLOW))

    def half(nrm, origin, seed):
        h = Part('half', p.slots)
        R0 = .3
        Ag, Bg = np.meshgrid(np.linspace(0, math.pi / 2, 10), np.linspace(0, TAU, 28, endpoint=False), indexing='ij')
        D = np.stack([np.sin(Ag) * np.cos(Bg), np.sin(Ag) * np.sin(Bg), -np.cos(Ag)], -1)
        bump = 1 + .1 * noise2(D[..., 0] * 3 + D[..., 2] * 2, D[..., 1] * 3 - D[..., 2], seed) + .04 * noise2(D[..., 0] * 9, D[..., 1] * 9 + D[..., 2] * 5, seed + 1)
        O = D * (R0 * bump)[..., None]
        k = (.6 + .4 * np.sin(Ag)) * (1 + .12 * noise2(D[..., 0] * 7, D[..., 1] * 7, seed + 2))
        skin(h, O, lit(mix(ROCK_BLUE, ROCK_PALE, .3), k * 1.2), ROCK, D, True, True)
        rim_o = O[-1]
        b = Bg[-1]
        rings = [rim_o]
        for f, dz in ((.9, .012), (.78, .008), (.7, -.02)):
            rings.append(np.stack([np.cos(b) * R0 * f, np.sin(b) * R0 * f, np.full(28, dz)], 1))
        rc = np.array([lit(c, np.full(28, 1.0)) for c in (mix(ROCK_BLUE, ROCK_PALE, .4), tone(ROCK_PALE, 1.5), tone(mix(ROCK_PALE, CRYSTAL_VIOLET, .35), 1.2), ROCK_DEEP)])
        skin(h, np.array(rings), rc, ROCK, V(0, 0, 1), False, True)
        Ai, Bi = np.meshgrid(np.linspace(math.pi / 2, 0, 7), np.linspace(0, TAU, 28, endpoint=False), indexing='ij')
        Di = np.stack([np.sin(Ai) * np.cos(Bi), np.sin(Ai) * np.sin(Bi), -np.cos(Ai)], -1)
        I = Di * R0 * .7 * np.array([1, 1, .8]) + V(0, 0, -.02)
        skin(h, I, lit(mix(ROCK_DEEP, CRYSTAL_VIOLET, .2), .6 + .5 * np.cos(Ai)), ROCK, -Di, True, True)
        for _ in range(34):
            a, b_ = rng.uniform(.15, 1.45), rng.uniform(0, TAU)
            d = V(math.sin(a) * math.cos(b_), math.sin(a) * math.sin(b_), -math.cos(a))
            base = d * R0 * .7 * np.array([1, 1, .8]) + V(0, 0, -.02)
            c = mix(CRYSTAL_VIOLET, CRYSTAL_ICE, rng.uniform(0, 1))
            crystal(h, base, unit(-d + V(0, 0, .5) + rng.uniform(-.25, .25, 3)), rng.uniform(.016, .034), rng.uniform(.05, .13), rng, tone(c, .7), mix(c, CRYSTAL_CLEAR, .6),
                    tip=.4, segs=1)
        for _ in range(5):
            b_ = rng.uniform(0, TAU)
            crystal(h, V(math.cos(b_) * .06, math.sin(b_) * .06, -.17), unit(V(math.cos(b_) * .3, math.sin(b_) * .3, 1)), .02, rng.uniform(.07, .11), rng, glow(GLOW_SERENE, .9),
                    glow(GLOW_SERENE, .7), GLOW, tip=.4, segs=1, edge=GLOW_WHITE)
        graft(p, h, along(nrm), origin)
    half(V(.3, -.35, 1), V(0, -.24, -.1), 3)
    half(V(.7, .45, .6), V(-.1, .3, .12), 9)
    fit(p, 1, .9)
    grime(p, 0, .12, .2, 951, keep=(GLOW, CRYSTAL))
    return p


def chime():
    """SM_AN_Chime (0.6 across): a Serene wind chime: six alloy tubes of different lengths on a ring, hung on cords
    from a loop, a striker disc in the middle and a crystal sail under it."""
    rng = np.random.default_rng(961)
    p = Part('SM_AN_Chime', (ALLOY, CLOTH, CRYSTAL))
    silver = tone(ALLOY_SILVER, 1.0)
    cord = tone(CLOTH_INDIGO, 1.6)
    apex = V(0, 0, .25)
    hoop(p, apex + V(0, 0, .022), (0, 1, 0), .02, .0038, silver, ALLOY, 14, 6)
    hoop(p, V(0, 0, .1), (0, 0, 1), .11, .0065, silver, ALLOY, 36, 8)
    for k in range(3):
        a = k * TAU / 3 + .5
        pipe(p, [apex, V(.11 * math.cos(a), .11 * math.sin(a), .105)], .0022, cord, CLOTH, 5)
    for k in range(6):
        a = k * TAU / 6
        e = V(math.cos(a), math.sin(a), 0)
        ln = .15 + .028 * ((k * 5) % 6) + rng.uniform(0, .01)
        top = e * .11 + V(0, 0, .058)
        pipe(p, [e * .11 + V(0, 0, .096), top - V(0, 0, .012)], .0018, cord, CLOTH, 5)
        fl.ring(p, [(.0085, 0), (.0118, 0), (.0118, ln), (.0085, ln)], tone(ALLOY_SILVER, rng.uniform(.85, 1.05)), ALLOY, 12, origin=top - V(0, 0, ln))
        pipe(p, [top - V(.012, 0, .012), top + V(.012, 0, -.012)], .0016, tone(ALLOY_SILVER, .6), ALLOY, 4)
    pipe(p, [apex, V(0, 0, -.2)], .0018, cord, CLOTH, 5)
    revolve(p, [(0, -.058), (.03, -.056), (.04, -.05), (.03, -.044), (0, -.042)], tone(ALLOY_SILVER, .9), ALLOY, 20)
    crystal(p, V(0, 0, -.2), (0, 0, -1), .03, .13, rng, CRYSTAL_ICE, CRYSTAL_CLEAR, tip=.6, taper=.0)
    crystal(p, V(0, 0, -.205), (0, 0, 1), .03, .03, rng, CRYSTAL_ICE, CRYSTAL_CLEAR, tip=.9, taper=.0)
    return fit(p, 2, .6)


def tablet_item():
    """SM_AN_Tablet (0.6 across): a record tablet, upright, its face toward +x: a stone leaf with a crystal inlay
    and a broken line of electrum down its midrib."""
    p = Part('SM_AN_Tablet', (STONE, CRYSTAL, ELECTRUM))
    tablet(p, np.stack([V(0, 0, 1), V(0, -1, 0), V(1, 0, 0)], 1), (0, 0, 0), .6, mix(STONE_PALE, STONE_WORN, .4), tone(ELECTRUM_PALE, .9), ELECTRUM)
    weather(p, 971, .6, under=.1, dirt=.16, streak=.1, pits=.2, skip=(GLOW, CRYSTAL))
    return fit(p, 2, .6)


def seedstone():
    """SM_AN_Seedstone (0.5 across): a seed-crystal: a smooth egg of clear crystal round a pearl-gold core (GLOW_WEAVE)
    with fine threads of the same light reaching toward the shell."""
    rng = np.random.default_rng(981)
    p = Part('SM_AN_Seedstone', (CRYSTAL, GLOW))
    t = .5 - .5 * np.cos(np.linspace(0, math.pi, 25))
    prof = [(.178 * math.sin(math.pi * q) ** .85 * (1.12 - .3 * q) if 0 < q < 1 else 0.0, -.25 + .5 * q) for q in t]
    revolve(p, prof, np.array([mix(tone(CRYSTAL_CLEAR, .82), CRYSTAL_CLEAR, q) for q in t]), CRYSTAL, 40)
    crystal(p, V(0, 0, -.03), (0, 0, 1), .05, .13, rng, glow(GLOW_WEAVE, 1.0), glow(GLOW_WEAVE, .85), GLOW, tip=.6, taper=.1, edge=GLOW_WHITE)
    crystal(p, V(0, 0, -.03), (0, 0, -1), .05, .09, rng, glow(GLOW_WEAVE, 1.0), glow(GLOW_WEAVE, .7), GLOW, tip=.8, taper=.1, edge=GLOW_WHITE)
    for _ in range(7):
        d = unit(rng.normal(0, 1, 3))
        path = curve([V(0, 0, 0), d * .05 + rng.uniform(-.015, .015, 3), d * .1 + rng.uniform(-.02, .02, 3) + V(0, 0, -.01)], 6)
        pipe(p, path, np.linspace(.004, .001, 6), np.array([glow(GLOW_WEAVE, q) for q in np.linspace(.9, .3, 6)]), GLOW, 4)
    return fit(p, 2, .5)


# ---------------------------------------------------------------- the module's meshes and their contract

MESHES = [aeon, serene, vigil, sunderer, crystal_cluster, crystal_great, cache, chime, tablet_item, seedstone]
VARIANTS = {serene: 3, crystal_cluster: 3}


def _person(height):
    return {'size': (0, 0, height), 'tol': .01, 'pivot': 'base'}


CONTRACT = {
    'SM_AP_Aeon': _person(2.45),
    'SM_AP_Serene0': _person(2.3),
    'SM_AP_Serene1': _person(2.1),
    'SM_AP_Serene2': _person(2.2),
    'SM_AP_Vigil': _person(2.35),
    'SM_AE_Sunderer': {'size': (0, 8.0, 9.0), 'tol': .06, 'pivot': 'centre'},      # about 8 m across (y), 9 m tall
    'SM_AV_Crystal0': {'size': (0, 0, 1.5), 'tol': .02, 'pivot': 'base'},
    'SM_AV_Crystal1': {'size': (0, 0, 2.5), 'tol': .02, 'pivot': 'base'},
    'SM_AV_Crystal2': {'size': (0, 0, 4.0), 'tol': .02, 'pivot': 'base'},
    'SM_AV_CrystalGreat': {'size': (0, 0, 18.0), 'tol': .02, 'pivot': 'base'},
    'SM_AN_Cache': {'size': (0, .9, 0), 'tol': .02, 'pivot': 'centre'},             # 0.9 m across its largest dimension
    'SM_AN_Chime': {'size': (0, 0, .6), 'tol': .02, 'pivot': 'centre'},
    'SM_AN_Tablet': {'size': (0, 0, .6), 'tol': .02, 'pivot': 'centre'},
    'SM_AN_Seedstone': {'size': (0, 0, .5), 'tol': .02, 'pivot': 'centre'},
}


if __name__ == '__main__':
    import check
    for _part in check.builds(sys.modules[__name__]):
        _v = np.asarray(_part.v)
        print('%s  %d tris  %s .. %s' % (_part.name, _part.triangles(), np.round(_v.min(0), 3).tolist(), np.round(_v.max(0), 3).tolist()))
