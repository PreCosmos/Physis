"""Level 5, Arche, the First Ones' Planet: the living fauna, Arche's native animals (the organic enemies).

Pure numpy on kit.py; never imports bpy. Check and look:

    python3 Tools/arche_meshes/check.py creatures --preview

The fiction: these animals are older than the city. They are creatures of crystal-bearing flesh that swim in the air
(near the Lens everything has half forgotten its weight), and the Lens's unweaving has maddened them: where it has
touched them their bodies show violet-lit fractures (GLOW, GLOW_VIGIL) with violet crystal breaking out of them,
among their own soft ice-blue bioluminescence (GLOW_SERENE). Each is one static mesh posed with life in it, hovers,
is centred on its bounds ('centre' pivot) and faces +x.

  SM_AE_Mote        0.8 m across   the swarm animal: a glass-backed sea-angel, two wing-fins, trailing tendrils
  SM_AE_Medusa      1.6 x 2.6 m    a drifting bell of crystal-flesh over a soft core, long stinging tendrils (ranged)
  SM_AE_Shellback   2.2 m long     a coiled shell of grown plates, a soft beaked head and short arms (armoured)
  SM_AE_Ray         3.2 m span     a sky-manta mid-stroke, whip tail, glowing gill slits (fast)
  SM_AE_Stalker     2.8 x 2.2 m    the eel-and-heron hunter: crystal crest, wide jaw, glowing throat, four fin-limbs
  SM_AE_Leviathan   9 x 4 m        the sky-whale: throat pleats, long fins, flukes, crystal barnacles, one great wound

Slots: SKIN 'CN_Bark' is hide (vertex colour is its albedo, countershaded: dark backs, pale bellies); ROCK is horn,
shell, beak, tooth and claw; CRYSTAL is the translucent flesh (bells, fin membranes) and the crystal growths; GLOW is
the light; LICHEN the Medusa's soft frills.

How the bodies are made: Body lofts a skin along a spine curve with a section that can differ above and below (so
backs keel and bellies sag), and answers at(t, th) with a point and a normal, so eyes, spots, crystals and fractures
sit on the skin. Fins and membranes are grids given real thickness (membrane, shell_pair), so they show from both
sides. fracture() walks a jagged, branching crack over any surface and scorch() darkens the hide round it.
"""
from kit import *

SKIN = 'CN_Bark'
unit = fl.unit
norm = np.linalg.norm
PI = math.pi


def V(*x):
    return np.array(x, np.float64)


def rgb(c):
    return np.asarray(c, np.float64)[..., :3]


def rgba(c):
    c = np.clip(rgb(c), 0.0, None)
    return np.concatenate([c, np.ones(c.shape[:-1] + (1,))], -1)


def lit(colour, k=1.0):
    """colour (one or an array) times shading k, as RGBA of at most 0.9 albedo."""
    k = np.asarray(k, np.float64)
    return rgba(np.minimum(rgb(colour) * (k[..., None] if k.ndim else k), .9))


def mx(a, b, t):
    """Blend of two colours (t a number or an array) as RGB."""
    t = np.asarray(t, np.float64)
    t = np.clip(t, 0, 1)[..., None] if t.ndim else float(np.clip(t, 0, 1))
    return rgb(a) * (1 - t) + rgb(b) * t


def light(colour, k=1.0):
    """A light's colour at brightness k (one or an array) for the GLOW slot."""
    k = np.asarray(k, np.float64)
    return rgba(rgb(colour) * (k[..., None] if k.ndim else k))


def smooth(e0, e1, x):
    t = np.clip((np.asarray(x, np.float64) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def rotv(v, axis, ang):
    """v turned by ang radians about axis (Rodrigues)."""
    v, k = np.asarray(v, np.float64), unit(axis)
    return v * math.cos(ang) + np.cross(k, v) * math.sin(ang) + k * np.sum(k * v, -1, keepdims=True) * (1 - math.cos(ang))


# The animals' colours: mixes of Arche's palette, cool greys and slate blues.
SLATE = mx(STONE_DARK, CLOTH_INDIGO, .28)            # a dark blue-slate back
SLATE_MID = mx(STONE_SHADE, CLOTH_INDIGO, .18)
DUSK = mx(ROCK_BLUE, CLOTH_VIOLET, .16)              # the darkest hide, a hint of violet
PALE = mx(CLOTH_PEARL, LICHEN_FROST, .18)            # bellies
PEARL = rgb(CLOTH_PEARL)
MAW = mx(CLOTH_VIOLET, ROCK_DEEP, .55)               # the inside of a mouth
SCORCH = np.array([.050, .034, .085])                # hide burnt by the unweaving
BONE = mx(DUST, CLOTH_PEARL, .5)
WHITE_VIOLET = mx(GLOW_VIGIL, GLOW_WHITE, .4)


# ---------------------------------------------------------------- curves and frames

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
    path = spline(keys, max(n * 6, 80))
    seg = np.r_[0.0, np.cumsum(norm(np.diff(path, axis=0), axis=1))]
    at = np.linspace(0, seg[-1], n)
    return np.stack([np.interp(at, seg, path[:, k]) for k in range(3)], 1)


def frames(pts, up=(0, 0, 1)):
    """Tangent T, side S and up U along a polyline; U starts nearest `up` and is carried without twisting.
    S = T x U: for a spine running back from the head (T = -x) with U up, S is the animal's right (+y)."""
    pts = np.asarray(pts, np.float64)
    T = unit(np.gradient(pts, axis=0))
    u = np.asarray(up, np.float64)
    if abs(np.dot(unit(u), T[0])) > .97:
        u = V(1, 0, 0) if abs(T[0][0]) < .9 else V(0, 1, 0)
    U = np.zeros_like(pts)
    for i in range(len(pts)):
        u = unit(u - T[i] * np.dot(u, T[i]))
        U[i] = u
    return T, np.cross(T, U), U


def prof(keys, t, soften=True):
    """A profile [(t, value), ...] sampled at t and softened a little."""
    k = np.asarray(keys, np.float64)
    v = np.interp(t, k[:, 0], k[:, 1])
    if soften and len(v) > 8:
        w = max(1, len(v) // 28)
        pad = np.r_[np.full(w, v[0]), v, np.full(w, v[-1])]
        v2 = np.convolve(pad, np.ones(2 * w + 1) / (2 * w + 1), 'valid')
        v2[0], v2[-1] = v[0], v[-1]
        v = v2
    return v


# ---------------------------------------------------------------- surfaces

def _oriented(verts, faces, out, uniform=False):
    """faces (triangles and quads) wound so their fronts lie along `out` (one direction per vertex). uniform: the
    faces already agree with each other (a regular grid), so they are turned all together or not at all, which
    keeps a tightly rolled or ruffled sheet consistent."""
    res = []
    for k in (3, 4):
        F = np.array([f for f in faces if len(f) == k], np.int64).reshape(-1, k)
        if not len(F):
            continue
        P = verts[F]
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]) if k == 3 else np.cross(P[:, 2] - P[:, 0], P[:, 3] - P[:, 1])
        flip = np.einsum('ij,ij->i', n, out[F].sum(1)) < 0
        if uniform:
            flip[:] = np.einsum('ij,ij->i', unit(n), unit(out[F].sum(1))).sum() < 0
        F[flip] = F[flip][:, ::-1]
        res += F.tolist()
    return res


def _grid_colours(colour, shape):
    c = np.asarray(colour, np.float64)
    if c.ndim == 1:
        c = np.broadcast_to(c, shape + (c.shape[-1],))
    elif c.ndim == 2:
        c = np.broadcast_to(c[:, None, :], shape + (c.shape[-1],))
    return rgba(c) if c.shape[-1] == 3 else c


def skin(part, grid, colour, slot, out, wrap=False, smooth_=True, uniform=False):
    """A surface over a point grid (nu x nv x 3) fronting `out` (one direction, or one per point)."""
    g = np.asarray(grid, np.float64)
    nu, nv = g.shape[:2]
    idx = np.arange(nu * nv).reshape(nu, nv)
    a, b = idx[:-1], idx[1:]
    if wrap:
        q = np.stack([a, b, np.roll(b, -1, 1), np.roll(a, -1, 1)], -1)
    else:
        q = np.stack([a[:, :-1], b[:, :-1], b[:, 1:], a[:, 1:]], -1)
    flat = g.reshape(-1, 3)
    o = np.broadcast_to(np.asarray(out, np.float64), g.shape).reshape(-1, 3)
    return part.add(flat, _oriented(flat, q.reshape(-1, 4).tolist(), o, uniform), _grid_colours(colour, (nu, nv)).reshape(nu * nv, -1), slot, smooth_)


def loft(part, rings, colour, slot, out=None, caps=(.5, .5), smooth_=True):
    """A closed skin over rings (n x m x 3). caps: how far each end's pole bulges, as a fraction of that ring's
    radius (None leaves the end open). out: the outward direction per point (by default away from each ring's
    middle)."""
    R = np.asarray(rings, np.float64)
    n, m = R.shape[:2]
    mid = R.mean(1)
    O = R - mid[:, None, :] if out is None else np.broadcast_to(np.asarray(out, np.float64), R.shape)
    C = _grid_colours(colour, (n, m))
    verts, outs, cols = [R.reshape(-1, 3)], [O.reshape(-1, 3)], [C.reshape(n * m, -1)]
    idx = np.arange(n * m).reshape(n, m)
    a, b = idx[:-1], idx[1:]
    faces = np.stack([a, b, np.roll(b, -1, 1), np.roll(a, -1, 1)], -1).reshape(-1, 4).tolist()
    count = n * m
    for end, bulge in ((0, caps[0]), (n - 1, caps[1])):
        if bulge is None:
            continue
        other = 1 if end == 0 else n - 2
        d = unit(mid[end] - mid[other]) if out is None else unit(O[end].mean(0))
        if out is not None and norm(O[end].mean(0)) < 1e-6:
            d = unit(mid[end] - mid[other])
        radius = norm(R[end] - mid[end], axis=1).mean()
        verts.append((mid[end] + d * bulge * radius)[None, :])
        outs.append(d[None, :])
        cols.append(C[end].mean(0)[None, :])
        faces += [[count, int(idx[end, j]), int(idx[end, (j + 1) % m])] for j in range(m)]
        count += 1
    verts, outs = np.concatenate(verts), np.concatenate(outs)
    return part.add(verts, _oriented(verts, faces, outs), np.concatenate(cols), slot, smooth_)


def pipe(part, pts, radius, colour, slot, sides=6, caps=(.6, .8), up=(0, 0, 1)):
    """A round limb or tendril along a polyline. radius and colour: one, or one per point."""
    pts = np.asarray(pts, np.float64)
    _, S, U = frames(pts, up)
    r = np.broadcast_to(np.asarray(radius, np.float64), (len(pts),))
    ang = np.linspace(0, TAU, sides, endpoint=False)
    rings = pts[:, None, :] + r[:, None, None] * (np.cos(ang)[None, :, None] * S[:, None, :] + np.sin(ang)[None, :, None] * U[:, None, :])
    return loft(part, rings, colour, slot, caps=caps)


def grid_normals(G):
    return unit(np.cross(np.gradient(G, axis=0), np.gradient(G, axis=1)))


def shell_pair(part, top, bot, ctop, cbot, slot, rim=None, wrap=False):
    """A solid between two matching grids (a fin, a membrane, a flat body): both faces and the rim between them, so
    it shows from every side."""
    top, bot = np.asarray(top, np.float64), np.asarray(bot, np.float64)
    d = top - bot
    d = np.where(norm(d, axis=-1, keepdims=True) > 1e-9, d, grid_normals(top))
    start = skin(part, top, ctop, slot, d, wrap, uniform=True)
    skin(part, bot, cbot, slot, -d, wrap, uniform=True)
    ct, cb = _grid_colours(ctop, top.shape[:2]), _grid_colours(cbot, top.shape[:2])
    mid = (top + bot) / 2
    edges = [(0, 1, None), (-1, -2, None)] + ([] if wrap else [(None, None, 0), (None, None, -1)])
    for e, inner, side in edges:
        if side is None:
            a, b, o = top[e], bot[e], mid[e] - mid[inner]
            ca, cb_ = ct[e], cb[e]
        else:
            a, b, o = top[:, side], bot[:, side], mid[:, side] - mid[:, 1 if side == 0 else -2]
            ca, cb_ = ct[:, side], cb[:, side]
        if rim is not None:
            ca = cb_ = np.broadcast_to(rgba(rim), ca.shape)
        skin(part, np.stack([a, b]), np.stack([ca, cb_]), slot, np.stack([o, o]), wrap and side is None, uniform=True)
    return start


def membrane(part, G, thick, ctop, cbot, slot, up=None, rim=None):
    """A thin fin over a middle surface G (nu x nv x 3) with real thickness (one number or nu x nv). The 'top' is
    the side of `up` when given. Returns the normals used."""
    G = np.asarray(G, np.float64)
    n = grid_normals(G)
    if up is not None and float(np.sum(n * np.asarray(up, np.float64))) < 0:
        n = -n
    t = np.broadcast_to(np.asarray(thick, np.float64), G.shape[:2])[..., None]
    shell_pair(part, G + n * t / 2, G - n * t / 2, ctop, cbot, slot, rim)
    return n


def membrane_start(part, *args, **kw):
    """membrane(), returning its first vertex instead of its normals."""
    start = len(part.v)
    membrane(part, *args, **kw)
    return start


class Surf:
    """A point grid as a surface: s(a, b) -> (point, unit normal) for a, b in 0..1 (b wraps when wrap is set)."""

    def __init__(self, G, N, wrap=False):
        self.G, self.N, self.wrap = np.asarray(G, np.float64), np.asarray(N, np.float64), wrap

    def __call__(self, a, b):
        nu, nv = self.G.shape[:2]
        x = float(np.clip(a, 0, 1)) * (nu - 1)
        i = min(int(x), nu - 2)
        fx = x - i
        if self.wrap:
            y = (b % 1.0) * nv
            j = int(y) % nv
            k = (j + 1) % nv
        else:
            y = float(np.clip(b, 0, 1)) * (nv - 1)
            j = min(int(y), nv - 2)
            k = j + 1
        fy = y - int(y) if self.wrap else y - j
        w = ((1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy)
        P = w[0] * self.G[i, j] + w[1] * self.G[i + 1, j] + w[2] * self.G[i, k] + w[3] * self.G[i + 1, k]
        N = w[0] * self.N[i, j] + w[1] * self.N[i + 1, j] + w[2] * self.N[i, k] + w[3] * self.N[i + 1, k]
        return P, unit(N)


class Body:
    """A soft body lofted along a spine. Sections are (super)ellipses whose half-width ry, upper radius up_r and
    lower radius dn_r are profiles [(t, metres), ...] along the spine (t 0 at the first key). Around a section th
    runs from -pi: th 0 is the side S (the animal's right for a head-to-tail spine), pi/2 the back, -pi/2 the
    belly. Shape the grid G (push) before bake(); then at(t, th) gives a point and normal on the skin."""

    def __init__(self, keys, n, m, ry, up_r, dn_r, up=(0, 0, 1), power=2.0):
        self.n, self.m = n, m
        self.c = curve(keys, n)
        self.T, self.S, self.U = frames(self.c, up)
        self.t = np.linspace(0, 1, n)
        self.th = np.linspace(-PI, PI, m, endpoint=False)
        self.ry, self.ru, self.rd = prof(ry, self.t), prof(up_r, self.t), prof(dn_r, self.t)
        cs, sn = np.cos(self.th), np.sin(self.th)
        e = 2.0 / power
        y, z = np.sign(cs) * np.abs(cs) ** e, np.sign(sn) * np.abs(sn) ** e
        rz = np.where(sn[None, :] >= 0, self.ru[:, None], self.rd[:, None])
        self.G = (self.c[:, None, :] + self.S[:, None, :] * (self.ry[:, None] * y[None, :])[..., None] +
                  self.U[:, None, :] * (rz * z[None, :])[..., None])
        self.TT, self.TH = np.meshgrid(self.t, self.th, indexing='ij')
        self.length = float(norm(np.diff(self.c, axis=0), axis=1).sum())
        self.bake()

    def push(self, d):
        """Moves the skin out (in, when negative) by d metres (n x m) from the spine."""
        self.G = self.G + unit(self.G - self.c[:, None, :]) * np.asarray(d, np.float64)[..., None]
        self.bake()

    def bake(self):
        du = np.gradient(self.G, axis=0)
        dv = (np.roll(self.G, -1, 1) - np.roll(self.G, 1, 1)) / 2
        n = unit(np.cross(du, dv))
        o = self.G - self.c[:, None, :]
        self.N = np.where(np.sum(n * o, -1, keepdims=True) < 0, -n, n)
        self.surf = Surf(self.G, self.N, True)

    def at(self, t, th):
        return self.surf(t, (th + PI) / TAU)

    def cp(self, t):
        """The spine's point at fraction t."""
        return np.array([np.interp(t * (self.n - 1), np.arange(self.n), self.c[:, k]) for k in range(3)])

    def vt(self):
        """The spine fraction of each vertex add() made (the rings, then the two poles)."""
        return np.r_[np.repeat(self.t, self.m), 0.0, 1.0]

    def ab(self, a, b):
        """The same surface with both parameters 0..1 (for fracture())."""
        return self.surf(a, b)

    def add(self, part, colour, slot=SKIN, caps=(.5, .5)):
        self.start = len(part.v)
        loft(part, self.G, colour, slot, caps=caps)
        self.end = len(part.v)
        return self.start


def mottle(P, scale, seed):
    """Blotchy noise -1..1 over points, about `scale` metres across."""
    P = np.asarray(P, np.float64)
    f = P.reshape(-1, 3)
    return noise2(f[:, 0] / scale + f[:, 2] * .37 / scale, f[:, 1] / scale - f[:, 2] * .41 / scale, seed).reshape(P.shape[:-1])


def hide(P, N, back, belly, seed=0, scale=.3, amount=.2, lo=-.45, hi=.4):
    """Countershaded hide: `back` where the skin faces up, `belly` where it faces down, mottled."""
    k = smooth(lo, hi, np.asarray(N, np.float64)[..., 2])
    c = mx(belly, back, k)
    c = c * (1 + amount * mottle(P, scale, seed) + .5 * amount * mottle(P, scale * .23, seed + 7))[..., None]
    return rgba(np.minimum(c, .9))


# ---------------------------------------------------------------- small organs

def orb(part, c, r, colour, slot, n=None, flat=1.0, level=2):
    """A smooth ball; with a normal n it is flattened along n by `flat` (a lens, a lid, a spot)."""
    v, f = toolkit.ICO[level]
    local = v * np.array([r, r, r * flat])
    if n is not None:
        local = local @ fl.along(unit(n)).T
    start = part.add(local + np.asarray(c, np.float64), f, colour, slot, True)
    _ride(part, start, c)
    return start


def spot(part, P, N, r, colour, level=1):
    """A light organ lying in the skin: a low lens of GLOW."""
    return orb(part, P - N * r * .05, r, colour, GLOW, N, .38, level)


def eye(part, P, N, r, iris, lid, pupil=True, slot=GLOW):
    """An eye in a lidded socket: a fold of hide, a lit ball, a dark slit pupil."""
    orb(part, P - N * r * .45, r * 1.6, lid, SKIN, N, .62)
    orb(part, P + N * r * .28, r, iris, slot, N, .9)
    if pupil:
        a, b = frame(N)
        local = toolkit.ICO[1][0] * np.array([r * .2, r * .55, r * .3])
        _ride(part, part.add(local @ np.stack([a, b, unit(N)], 1).T + P + N * r * .95, toolkit.ICO[1][1], lit(ROCK_DEEP, .6), SKIN, True), P)


def spike(part, base, tip, r, c0, c1, slot=CRYSTAL, sides=5, tip_len=.4):
    """A crystal (or tooth, or claw) from base to tip, c0 at its foot and c1 at its point."""
    start = prism(part, base, tip, r, c0, slot, sides, tip_len, False)
    cols = np.concatenate([np.tile(rgba(c0), (sides, 1)), np.tile(rgba(mx(c0, c1, .55)), (sides, 1)), rgba(c1)[None, :]])
    part.c[start:start + 2 * sides + 1] = cols.tolist()
    _ride(part, start, base)
    return start


def crystals(part, rng, P, N, size, count, violet=0.0, spread=.55, lean=None):
    """A little cluster of crystals grown out of the surface at P (normal N). violet: the share that the Lens has
    turned."""
    for k in range(count):
        d = unit(N + rng.normal(0, spread, 3) + (0 if lean is None else np.asarray(lean, np.float64)))
        if np.dot(d, N) < .2:
            d = unit(d + N)
        ln = size * rng.uniform(.45, 1.0) * (1.0 if k == 0 else .7)
        a, b = frame(N)
        foot = P + (a * rng.uniform(-1, 1) + b * rng.uniform(-1, 1)) * size * .12 * (k > 0) - N * ln * .12
        if rng.random() < violet:
            c0, c1 = mx(CRYSTAL_VIOLET, CLOTH_VIOLET, .45), mx(CRYSTAL_VIOLET, CRYSTAL_CLEAR, .35)
        else:
            c0, c1 = mx(CRYSTAL_ICE, TILE_TEAL, .35), mx(CRYSTAL_ICE, CRYSTAL_CLEAR, .5)
        spike(part, foot, foot + d * ln, ln * rng.uniform(.13, .2), lit(c0, .8), lit(c1, 1.0), CRYSTAL, int(rng.choice((5, 6))))


def trail(rng, start, d0, length, n=26, drift=(-.5, 0, -.8), stiff=1.2, curl=0.0, wobble=.25, waves=2.0):
    """The path of a tendril: it leaves start along d0, is drawn toward `drift`, wavers, and curls `curl` turns
    toward its tip."""
    p, h = np.asarray(start, np.float64).copy(), unit(d0)
    drift = unit(drift)
    axis = unit(np.cross(h, rng.normal(0, 1, 3)) + 1e-9)
    side = unit(np.cross(drift, rng.normal(0, 1, 3)) + 1e-9)
    phase = rng.uniform(0, TAU)
    step = length / (n - 1)
    pts = [p.copy()]
    for i in range(1, n):
        t = i / (n - 1)
        h = unit(h + drift * stiff * step / max(length, 1e-6) * 3 + side * wobble * math.cos(phase + t * TAU * waves) * 3.0 / n)
        if curl:
            h = rotv(h, axis, curl * TAU * 3 * t * t / (n - 1))
        p = p + h * step
        pts.append(p.copy())
    return np.array(pts)


def tendril(part, rng, start, d0, length, r0, c0, c1, n=26, sides=5, tip=None, tip_r=None, beads=0.0, bones=None, **kw):
    """A trailing tendril (hide), thinning from r0, coloured c0 to c1; tip: the colour of a light at its end.
    bones = (prefix, count, parent) gives it its own chain, rooted in the weights of what it grows from; the
    chain's bone names are left in part.rg.last."""
    pts = trail(rng, start, d0, length, n, **kw)
    t = np.linspace(0, 1, n)
    r = r0 * (1 - .82 * t ** .8)
    if beads:
        r = r * (1 + beads * np.maximum(np.sin(t * TAU * length / .11 + rng.uniform(0, 6)), 0) ** 4 * (t > .15))
    st = pipe(part, pts, r, lit(mx(c0, c1, t), 1.0), SKIN, sides)
    if bones is not None:
        rg = part.rg
        rg.last = rg.chain(bones[0], bones[2], pts[np.linspace(0, n - 1, bones[1] + 1).round().astype(int)])
        rg.bind_pipe(st, n, sides, rg.last, rg.rows(pts[:1])[0])
    if tip is not None:
        orb(part, pts[-1], tip_r or r0 * 1.5, light(tip, 1.0), GLOW, None, 1.0, 1)
    return pts


# ---------------------------------------------------------------- the Lens's wounds

def ridge(part, P, N, width, colour_mid, colour_edge, slot=GLOW, height=.3):
    """A raised seam along points P on a surface (normals N): its edges sink into the skin, its crest stands
    `height` widths proud. width: one per point."""
    P, N = np.asarray(P, np.float64), unit(N)
    w = np.broadcast_to(np.asarray(width, np.float64), (len(P),))[:, None]
    S = unit(np.cross(N, unit(np.gradient(P, axis=0))))
    k = len(P)
    verts = np.concatenate([P - S * w / 2 - N * w * .12, P + N * w * height, P + S * w / 2 - N * w * .12])
    faces = [[i, k + i, k + i + 1, i + 1] for i in range(k - 1)] + [[k + i, 2 * k + i, 2 * k + i + 1, k + i + 1] for i in range(k - 1)]
    cm, ce = np.broadcast_to(rgba(colour_mid), (k, 4)), np.broadcast_to(rgba(colour_edge), (k, 4))
    start = part.add(verts, _oriented(verts, faces, np.concatenate([N, N, N])), np.concatenate([ce, cm, ce]), slot, True)
    _ride(part, start)
    return start


def fracture(part, surf, a, b, psi, length, width, rng, branches=2, jag=.75, colour=None):
    """One of the Lens's fractures: a jagged, branching crack of violet light walked over surf(a, b) -> (P, N)
    from (a, b), heading psi (radians in the surface's a-b plane), `length` metres long. Returns every point and
    normal on it and its branches (for scorch() and shards())."""
    steps = int(rng.integers(6, 10))
    seg = length / steps
    fork = {steps // 3: 1, (2 * steps) // 3: 2}
    Ps, Ns, found = [], [], []
    for i in range(steps + 1):
        P, N = surf(a, b)
        Ps.append(P)
        Ns.append(N)
        if branches >= fork.get(i, 99):
            sub = psi + (1 if fork[i] == 1 else -1) * rng.choice((-1, 1)) * rng.uniform(.65, 1.15)
            found.append(fracture(part, surf, a, b, sub, length * rng.uniform(.35, .55), width * .6, rng, branches - 1, jag, colour))
        e = 1e-3
        ma = max(norm(surf(a + e, b)[0] - surf(a - e, b)[0]) / (2 * e), 1e-6)
        mb = max(norm(surf(a, b + e)[0] - surf(a, b - e)[0]) / (2 * e), 1e-6)
        ang = psi + (rng.uniform(.25, jag) if i % 2 else -rng.uniform(.25, jag))
        a += math.cos(ang) * seg / ma
        b += math.sin(ang) * seg / mb
    Ps, Ns = np.array(Ps), np.array(Ns)
    w = width * (.18 + .82 * np.sin(PI * np.linspace(0, 1, steps + 1)) ** .7) * rng.uniform(.75, 1.2, steps + 1)
    c = GLOW_VIGIL if colour is None else colour
    ridge(part, Ps, Ns, w, light(mx(c, GLOW_WHITE, .35), 1.0), light(c, .55))
    return np.concatenate([Ps] + [f[0] for f in found]), np.concatenate([Ns] + [f[1] for f in found])


wound = fracture


def scorch(part, start, end, nodes, radius, colour=SCORCH, strength=.85):
    """Darkens the vertices start..end toward `colour` within `radius` of the crack's points: the burnt margin of a
    fracture."""
    v = np.asarray(part.v[start:end], np.float64)
    if not len(v) or not len(nodes):
        return
    d = np.full(len(v), 1e9)
    for q in np.asarray(nodes, np.float64):
        d = np.minimum(d, norm(v - q, axis=1))
    t = (np.clip(1 - d / radius, 0, 1) ** 1.4 * strength)[:, None]
    c = np.asarray(part.c[start:end], np.float64)
    c[:, :3] = c[:, :3] * (1 - t) + np.asarray(colour, np.float64)[:3] * t
    part.c[start:end] = c.tolist()


def shards(part, rng, P, N, count, size, violet=1.0):
    """Violet crystal breaking out along a fracture."""
    for i in rng.choice(len(P), min(count, len(P)), replace=False):
        crystals(part, rng, P[i], N[i], size * rng.uniform(.6, 1.0), int(rng.integers(1, 4)), violet)


def fit(part, axis, size):
    """Centres the part on its bounds and scales it so its extent on `axis` is `size` metres."""
    before = np.asarray(part.v[0], np.float64)
    centre(part)
    v = np.asarray(part.v, np.float64)
    k = size / (v[:, axis].max() - v[:, axis].min())
    part.v = (v * k).tolist()
    centre(part)
    part.xf = (k, np.asarray(part.v[0], np.float64) - before * k)      # finished = built * k + shift (for the bones)
    return part


def turn_y(points, deg):
    """Points pitched by deg about y (positive tips +z toward +x)."""
    a = math.radians(deg)
    p = np.asarray(points, np.float64)
    x, z = p[..., 0] * math.cos(a) + p[..., 2] * math.sin(a), -p[..., 0] * math.sin(a) + p[..., 2] * math.cos(a)
    return np.stack([x, p[..., 1], z], -1)


def fan(root, outer, nv, arch=None, power=1.0):
    """The middle surface of a fin fanned from a root line to an outer edge (both nu x 3): nu x nv x 3."""
    root, outer = np.asarray(root, np.float64), np.asarray(outer, np.float64)
    v = np.linspace(0, 1, nv) ** power
    G = root[:, None, :] + (outer - root)[:, None, :] * v[None, :, None]
    if arch is not None:
        G = G + np.asarray(arch, np.float64) * (4 * v * (1 - v))[None, :, None]
    return G


# ---------------------------------------------------------------- skeletons, skin weights and animation
#
# Every builder also leaves part.rig, the data of a skeletal mesh (the exporter turns it into an armature):
#   'bones'   [(name, parent or None, head, tail), ...] in the finished mesh's space, parents first, 'Root' first
#   'index'   (n_vertices, 4) bone indices      'weight'  (n_vertices, 4) weights, each row summing to 1
#   'anims'   {'Swim': {'seconds', 'loop': True, 'pose'}, 'Strike': {'seconds': 1.3, 'loop': False, 'pose'}}
# pose(t) -> {bone: (rx, ry, rz)}: a rotation vector (axis times angle, radians, plain Rodrigues in mesh axes) that
# turns the bone about its own head, relative to its rest pose, in the frame carried by its already-posed parent.
# With these axes +ry about a bone that points forward tips it down (a jaw opens, a nose dips) and lifts one that
# points back (a tail rises); +rx lifts whatever lies to +y; +rz swings a forward-pointing bone toward +y.
#
# Weights come from the builder's own knowledge. A piece is bound as it is added: a body along its spine (by its
# rings' t), a tendril or limb along its own chain (by ring), a fin by projection onto its chain, each blending
# smoothly from bone to bone and into whatever it grows from at its root. Small things that ride on a surface
# (eyes, light organs, crystals, teeth, barnacles) register themselves in orb(), spike() and ridge() and, when the
# animal is finished, take the weights of the nearest bound vertex: rigid things as one piece from their foot,
# seams of light vertex by vertex.

class Rig:
    MAXB = 80

    def __init__(self, part):
        self.p, part.rg = part, self
        self.bones, self.ix, self.riders = [], {}, []
        self.W, self.bound = np.zeros((0, self.MAXB)), np.zeros(0, bool)
        self.last = []
        self.bone('Root', None, (0, 0, 0), (.2, 0, 0))

    def bone(self, name, parent, head, tail):
        assert name not in self.ix and (parent is None or parent in self.ix), name
        head, tail = np.asarray(head, np.float64), np.asarray(tail, np.float64)
        assert norm(tail - head) > 1e-6, name
        self.ix[name] = len(self.bones)
        self.bones.append([name, parent if self.bones else None, head, tail])
        if self.bones[-1][1] is None and len(self.bones) > 1:
            self.bones[-1][1] = 'Root'
        return name

    def chain(self, prefix, parent, joints):
        """Bones prefix1, prefix2 ... through the joints, each the child of the one before."""
        names = []
        for i in range(len(joints) - 1):
            names.append(self.bone('%s%d' % (prefix, i + 1), parent, joints[i], joints[i + 1]))
            parent = names[-1]
        return names

    def _grow(self):
        n = len(self.p.v)
        if n > len(self.W):
            self.W = np.concatenate([self.W, np.zeros((n - len(self.W), self.MAXB))])
            self.bound = np.concatenate([self.bound, np.zeros(n - len(self.bound), bool)])

    def row(self, weights):
        """{bone: weight} (or a row already) as one row."""
        if isinstance(weights, dict):
            r = np.zeros(self.MAXB)
            for name, w in weights.items():
                r[self.ix[name]] = w
            return r
        return np.asarray(weights, np.float64)

    def bind(self, idx, rows):
        """Gives vertices idx ((start, end) or indices) their weights: one {bone: w}, or one row each."""
        self._grow()
        idx = np.arange(idx[0], idx[1]) if isinstance(idx, tuple) else np.asarray(idx)
        rows = self.row(rows)
        rows = np.broadcast_to(rows, (len(idx), self.MAXB)).copy()
        self.W[idx] = rows / rows.sum(1, keepdims=True)
        self.bound[idx] = True

    def rows(self, pts, host=None):
        """The weights of the nearest bound vertex (within host = (start, end) when given) to each point."""
        self._grow()
        cand = np.flatnonzero(self.bound)
        if host is not None:
            cand = cand[(cand >= host[0]) & (cand < host[1])]
        V = np.asarray(self.p.v, np.float64)[cand]
        pts = np.asarray(pts, np.float64).reshape(-1, 3)
        near = np.concatenate([np.argmin(((pts[i:i + 256, None, :] - V[None, :, :]) ** 2).sum(-1), 1) for i in range(0, len(pts), 256)])
        return self.W[cand[near]]

    def stick(self, start, end=None, host=None):
        """Vertices start..end each take the weights of the bound vertex nearest them."""
        end = len(self.p.v) if end is None else end
        self.bind((start, end), self.rows(self.p.v[start:end], host))

    def chain_rows(self, s, names, root, pts=None, blend=.5, lead=.6):
        """Rows for vertices at chain coordinate s (0 at the chain's root, i at its i-th joint, len(names) at its
        tip): whole bones in the middle of each, smooth blends across the joints, and over the first `lead` of
        the first bone a blend out of `root` ({bone: w}, a row, or 'stick' / ('stick', host): the nearest bound
        vertex to each of pts)."""
        s = np.asarray(s, np.float64)
        k = len(names)
        u = [smooth(0, lead, s)] + [smooth(i - blend, i + blend, s) for i in range(1, k)] + [np.zeros_like(s)]
        if isinstance(root, str) or (isinstance(root, tuple) and root[0] == 'stick'):
            base = self.rows(pts, None if isinstance(root, str) else root[1])
        else:
            base = self.row(root)[None, :]
        rows = (1 - u[0])[:, None] * base
        for i, name in enumerate(names):
            rows[:, self.ix[name]] += u[i] - u[i + 1]
        return rows

    def spine_rows(self, t, ts, names, root):
        """Rows for a body's vertices at spine fractions t, for a chain whose joints lie at fractions ts (running
        either way along the spine from ts[0])."""
        order = np.argsort(ts)
        return self.chain_rows(np.interp(t, np.asarray(ts, np.float64)[order], np.arange(len(ts), dtype=np.float64)[order]), names, root)

    def bind_pipe(self, start, n, sides, names, root, at=None, caps=2):
        """Binds a pipe() of n rings to a chain; at: the ring index of each joint (evenly spread by default)."""
        k = len(names)
        at = np.linspace(0, n - 1, k + 1) if at is None else np.asarray(at, np.float64)
        ring = np.r_[np.repeat(np.arange(n), sides), [0, n - 1][:caps]]
        end = start + len(ring)
        self.bind((start, end), self.chain_rows(np.interp(ring, at, np.arange(k + 1.0)), names, root, self.p.v[start:end]))

    def bind_proj(self, start, end, joints, names, root, lead=.6):
        """Binds vertices start..end to a chain by where each projects onto the chain's joints."""
        J = np.asarray(joints, np.float64)
        v = np.asarray(self.p.v[start:end], np.float64)
        best, s = np.full(len(v), 1e18), np.zeros(len(v))
        for i in range(len(J) - 1):
            d = J[i + 1] - J[i]
            f = np.clip((v - J[i]) @ d / np.dot(d, d), -1.0 if i == 0 else 0.0, 1.0)
            dist = ((v - (J[i] + np.clip(f, 0, 1)[:, None] * d)) ** 2).sum(1)
            better = dist < best
            best, s = np.where(better, dist, best), np.where(better, i + f, s)
        self.bind((start, end), self.chain_rows(s, names, root, v, lead=lead))

    def ride(self, start, anchor=None, end=None):
        self.riders.append((start, len(self.p.v) if end is None else end, None if anchor is None else np.asarray(anchor, np.float64)))

    def finish(self, anims):
        """Resolves the riders, checks every vertex is bound, moves the bones into the finished mesh's space
        (fit() has recorded the scale and shift) and writes part.rig."""
        self._grow()
        riders = [r for r in self.riders if not self.bound[r[0]:r[1]].all()]
        rigid = [r for r in riders if r[2] is not None]
        got = {}
        k, off = self.p.xf                                         # anchors were recorded before fit() moved the mesh
        if rigid:
            rows = self.rows(np.array([r[2] for r in rigid]) * k + off)
            got.update({id(r): rows[i] for i, r in enumerate(rigid)})
        for r in riders:
            if r[2] is None:
                got[id(r)] = self.rows(self.p.v[r[0]:r[1]])
        for r in riders:
            self.bind((r[0], r[1]), got[id(r)])
        if not self.bound.all():
            raise ValueError('%s: %d vertices without weights, the first at %d' % (self.p.name, int((~self.bound).sum()), int(np.argmin(self.bound))))
        bones = [(name, parent, tuple((head * k + off).tolist()), tuple((tail * k + off).tolist())) for name, parent, head, tail in self.bones]
        bones[0] = ('Root', None, (0.0, 0.0, 0.0), (.2, 0.0, 0.0))
        W = self.W[:, :len(bones)]
        index = np.argsort(-W, 1)[:, :4]
        weight = np.take_along_axis(W, index, 1)
        weight = weight / weight.sum(1, keepdims=True)
        index = np.where(weight > 0, index, 0)
        self.p.rig = {'bones': bones, 'index': index.astype(np.int32), 'weight': weight, 'anims': anims}
        del self.p.rg
        return self.p


def _ride(part, start, anchor=None):
    if hasattr(part, 'rg'):
        part.rg.ride(start, anchor)


class Pose(dict):
    """Rotation vectors by bone, added up: turn(names, axis, angle) with one axis or one per bone, one angle or
    one per bone."""

    def turn(self, names, axis, ang):
        names = [names] if isinstance(names, str) else names
        axis = np.asarray(axis, np.float64)
        ang = np.broadcast_to(np.asarray(ang, np.float64), (len(names),))
        for i, name in enumerate(names):
            self[name] = self.get(name, np.zeros(3)) + (axis[i] if axis.ndim == 2 else axis) * ang[i]
        return self

    def done(self):
        return {k: (float(v[0]), float(v[1]), float(v[2])) for k, v in self.items() if np.any(v != 0)}     # a bone left out is at rest


def key(t, keys):
    """A track through (time, value) keys, eased between them."""
    if t <= keys[0][0]:
        return float(keys[0][1])
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            f = f * f * (3 - 2 * f)
            return float(v0 + (v1 - v0) * f)
    return float(keys[-1][1])


def wave(k, amp, phase, lag, grow=0.0):
    """Angles of a wave travelling down a chain of k bones."""
    return np.array([amp * (1 + grow * i) * math.sin(phase - lag * i) for i in range(k)])


def animations(seconds, swim, strike):
    """The two animations from swim(t) -> Pose (t already wrapped into the loop) and strike(t, pose) -> Pose, which
    adds to Swim's first pose and must add nothing at 0 and at 1.3 s."""
    return {'Swim': {'seconds': seconds, 'loop': True, 'pose': lambda t: swim(t % seconds).done()},
            'Strike': {'seconds': 1.3, 'loop': False, 'pose': lambda t: strike(min(max(t, 0.0), 1.3), swim(0.0)).done()}}


XA, YA, ZA = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)             # the mesh axes, for poses


# ================================================================ SM_AE_Mote

def mote():
    """SM_AE_Mote (0.8 m across its wing-fins): the swarm animal, a darting sea-angel. A small soft body bent
    mid-dart, a dome of clear crystal over its back with a line of light organs showing through, two wing-fins
    mid-stroke (the right raised, the left sweeping down), two head feelers, short trailing tendrils, two bright
    eye-spots, and one small violet fracture on its flank."""
    rng = np.random.default_rng(5101)
    p = Part('SM_AE_Mote', (SKIN, CRYSTAL, GLOW))
    rg = Rig(p)
    b = Body([V(.25, 0, .0), V(.12, 0, .03), V(-.04, .0, .03), V(-.18, .03, -.01), V(-.30, .08, -.07)], 34, 20,
             ry=[(0, .045), (.1, .078), (.3, .088), (.6, .058), (.85, .032), (1, .014)],
             up_r=[(0, .045), (.1, .08), (.3, .092), (.6, .06), (.85, .034), (1, .014)],
             dn_r=[(0, .04), (.1, .066), (.3, .074), (.6, .05), (.85, .028), (1, .012)])
    b.push(.004 * np.sin(b.TT * 70) * smooth(.45, .7, b.TT))                    # soft rings on the tail
    b.add(p, hide(b.G, b.N, SLATE_MID, PEARL, 3, .08, .16), caps=(.7, .8))
    rg.bone('Body', 'Root', b.cp(.45), b.cp(0))
    tail_ts = (.45, .64, .82, 1.0)
    tails = rg.chain('Tail', 'Body', [b.cp(t) for t in tail_ts])
    rg.bind((b.start, b.end), rg.spine_rows(b.vt(), tail_ts, tails, {'Body': 1}))
    # the glass back: a dome of crystal over the spine, and the light organs under it
    t = np.linspace(.1, .74, 20)
    idx = t * (b.n - 1)
    cc = np.stack([np.interp(idx, np.arange(b.n), b.c[:, k]) for k in range(3)], 1)
    ru = np.interp(idx, np.arange(b.n), b.ru)
    ry = np.interp(idx, np.arange(b.n), b.ry)
    s = np.sin(np.linspace(.15, PI - .15, 20)) ** .55
    ang = np.linspace(0, TAU, 14, endpoint=False)
    rings = (cc + V(0, 0, 1) * ru[:, None] * .42)[:, None, :] + (V(0, 1, 0)[None, None, :] * (ry * .8 * s)[:, None, None] * np.cos(ang)[None, :, None] +
                                                                  V(0, 0, 1)[None, None, :] * (ru * .92 * s)[:, None, None] * np.sin(ang)[None, :, None])
    tt = np.linspace(0, 1, 20)
    rg.stick(loft(p, rings, lit(mx(CRYSTAL_ICE, CRYSTAL_CLEAR, tt), 1.0), CRYSTAL, caps=(.3, .3)), None, (b.start, b.end))
    for k, tk in enumerate(np.linspace(.16, .68, 6)):
        P, N = b.at(tk, PI / 2)
        orb(p, P + N * .012, .013 - .001 * k, light(GLOW_SERENE, 1.0), GLOW, None, 1.0, 1)
    # wing-fins (clear membrane on three soft rays): right raised, left sweeping down
    wings, feelers, tends = [], [], []
    for side, lift, sweep in ((1, .24, -.02), (-1, -.10, -.10)):
        th = .45 if side > 0 else PI - .45
        root = np.array([b.at(tk, th)[0] - b.at(tk, th)[1] * .01 for tk in np.linspace(.2, .5, 9)])
        mid = root[4]
        tipv = V(sweep, side * .36, lift)
        st = len(p.v)
        outer = curve([root[0] + V(.07, side * .16, lift * .5), mid + tipv + V(.07, 0, 0), mid + tipv, mid + tipv * .8 + V(-.12, 0, -.03 * side),
                       root[-1] + V(-.10, side * .12, lift * .2)], 9)
        G = fan(root, outer, 8, V(0, 0, .035 if side > 0 else -.03))
        uu, vv = np.meshgrid(np.linspace(0, 1, 9), np.linspace(0, 1, 8), indexing='ij')
        c = lit(mx(mx(CRYSTAL_ICE, SLATE_MID, .25), CRYSTAL_CLEAR, vv), .95 + .05 * np.cos(uu * 25))
        membrane(p, G, .007 - .004 * vv, c, c, CRYSTAL, V(0, 0, 1))
        for u in (1, 4, 7):
            pipe(p, G[u, :7], np.linspace(.008, .003, 7), lit(mx(SLATE_MID, PEARL, np.linspace(.1, .8, 7)), 1.0), SKIN, 5)
        names = rg.chain('WingR' if side > 0 else 'WingL', 'Body', [G[4, 0], G[4, 4], G[4, 7]])
        rg.bind_proj(st, len(p.v), [G[4, 0], G[4, 4], G[4, 7]], names, ('stick', (b.start, b.end)), lead=.5)
        wings.append((side, names, unit(root[0] - root[-1])))
    # feelers on the head, tendrils from the tail
    for side in (1, -1):
        P, N = b.at(.03, PI / 2 - side * .7)
        tendril(p, rng, P - N * .01, unit(V(.7, side * .5, .6)), .12, .011, SLATE_MID, PEARL, 10, 5, bones=('FeelR' if side > 0 else 'FeelL', 1, 'Body'),
                drift=(1, side * .3, .1), stiff=.5, wobble=.1)
        feelers.append((side, rg.last))
    for k in range(5):
        th = -PI / 2 + (k - 2) * 1.1 + rng.uniform(-.2, .2)
        P, N = b.at(.86 + .02 * (k % 2), th)
        tendril(p, rng, P - N * .008, unit(N * .5 + V(-1, .25, -.2)), rng.uniform(.17, .30), .010, PEARL, mx(PEARL, CRYSTAL_ICE, .6), 16, 5,
                tip=GLOW_SERENE if k % 2 == 0 else None, tip_r=.011, bones=('Tend%d_' % k, 2, 'Tail3'),
                drift=(-1, .35, -.25), stiff=.8, curl=(.45 if k == 3 else 0), wobble=.3)
        tends.append(rg.last)
    # eye-spots
    for side in (1, -1):
        P, N = b.at(.085, PI / 2 - side * 1.05)
        N = unit(N + V(.5, 0, 0))
        orb(p, P - N * .008, .034, lit(DUSK, .7), SKIN, N, .6)
        orb(p, P + N * .006, .023, light(GLOW_SERENE, 1.0), GLOW, N, .8)
    # the fracture
    P, N = wound(p, b.ab, .42, .57, .25, .14, .012, rng, 1)
    scorch(p, b.start, b.end, P, .035)
    shards(p, rng, P, N, 2, .05)

    def swim(t):
        """2 s: the wing-fins flutter four beats (the outer half lagging), the tail flicks twice from side to
        side, tendrils stream and waver, the feelers twitch."""
        w = TAU * t / 2.0
        P = Pose()
        for side, names, ax in wings:
            P.turn(names, ax, [side * .62 * math.sin(4 * w), side * .5 * math.sin(4 * w - 1.1)])
        P.turn('Body', ZA, -.07 * math.sin(2 * w))
        P.turn(tails, ZA, wave(3, .2, 2 * w, .9, .6))
        P.turn(tails, YA, wave(3, .06, 4 * w, .9))
        for k, names in enumerate(tends):
            P.turn(names, ZA, wave(2, .3, 2 * w - 1.5 + k * .7, 1.1))
            P.turn(names, YA, wave(2, .25, 4 * w + k * 1.9, 1.0))
        for side, names in feelers:
            P.turn(names, YA, .22 * math.sin(2 * w + side))
            P.turn(names, ZA, side * .15 * math.sin(4 * w))
        return P

    def strike(t, P):
        """Gathers with both fins swept up and back and the tail cocked to one side; then the fins snap down and
        forward together, the tail whips across and the tendrils fling wide; eases back."""
        cock = key(t, [(0, 0), (.55, 1), (.6, 1), (.68, -1), (.82, -.6), (1.3, 0)])
        hit = key(t, [(0, 0), (.6, 0), (.68, 1), (.85, .6), (1.3, 0)])
        for side, names, ax in wings:
            P.turn(names, ax, [side * .85 * cock, side * .45 * cock])
            P.turn(names[0], ZA, side * (.35 * max(cock, 0) - .75 * hit))
        P.turn(tails, ZA, np.array([.3, .4, .5]) * cock)
        P.turn(tails, YA, np.array([-.15, -.2, -.2]) * max(cock, 0))
        for k, names in enumerate(tends):
            P.turn(names, ZA, (k - 2) * .35 * hit)
            P.turn(names, YA, np.array([.2, .3]) * cock)
        for side, names in feelers:
            P.turn(names, YA, -.5 * max(cock, 0) + .5 * hit)
        return P

    fit(p, 1, .8)
    return rg.finish(animations(2.0, swim, strike))


# ================================================================ SM_AE_Medusa

def medusa():
    """SM_AE_Medusa (1.6 m across the bell, 2.6 m tall with its tendrils): the ranged attacker. A bell of
    translucent crystal-flesh, thick at the crown and scalloped at the margin, tipped forward as it drifts; inside
    it a soft core with four ring organs of light and four frilled mouth-arms; from the margin a ring of long
    tendrils trailing back, some curled, each ending in a stinging light. A violet fracture has split one side of
    the bell."""
    rng = np.random.default_rng(5202)
    p = Part('SM_AE_Medusa', (SKIN, CRYSTAL, GLOW, LICHEN))
    rg = Rig(p)
    Rb, H, tilt = .80, .62, 14.0

    def outer(q, a):
        q, a = np.asarray(q, np.float64), np.asarray(a, np.float64)
        beta = q * 1.92
        r = Rb * np.sin(beta) ** .85 * (1 + .05 * np.cos(8 * a) * q ** 3 + .045 * np.cos(a - 1.1) * q + .02 * np.cos(3 * a + .7) * q)
        z = H * np.cos(beta) - .07 * (.5 + .5 * np.cos(16 * a + PI)) * q ** 8 + .03 * np.cos(a - 2.0) * q ** 2
        return np.stack([r * np.cos(a), r * np.sin(a), z], -1)

    def inner(q, a):
        P = outer(q, a)
        k = (np.asarray(q, np.float64) ** 7)[..., None]
        return P * V(.87, .87, .74) * (1 - k) + (P - unit(P) * .012) * k

    nq_o, nq_i, m = 22, 14, 64
    A = np.linspace(0, TAU, m, endpoint=False)
    qo, qi = np.linspace(.02, 1, nq_o), np.linspace(1, .05, nq_i)[1:]
    Go = turn_y(outer(qo[:, None], A[None, :]), tilt)
    Gi = turn_y(inner(qi[:, None], A[None, :]), tilt)
    rings = np.concatenate([Go, Gi])
    low = turn_y(V(0, 0, -.9), tilt)
    out = np.concatenate([Go - turn_y(V(0, 0, -.6), tilt), low - Gi])
    qq = np.concatenate([qo, qi])[:, None] * np.ones((1, m))
    shade = 1 + .08 * mottle(rings, .25, 5)
    c = mx(mx(CRYSTAL_ICE, CRYSTAL_CLEAR, .35), mx(CRYSTAL_ICE, TILE_TEAL, .3), qq ** 3) * shade[..., None]
    c[nq_o:] *= .8
    bell_start = len(p.v)
    loft(p, rings, lit(c, 1.0), CRYSTAL, out=out, caps=(.12, .3))
    bell_end = len(p.v)
    # the bell's bones: the crown, and eight radial bones that swing the margin in and out (the pulse)
    rg.bone('Bell', 'Root', turn_y(V(0, 0, .05), tilt), turn_y(V(0, 0, H), tilt))
    rims, rim_tan, rim_rad = [], [], []
    for k in range(8):
        a = (k + .5) * TAU / 8
        rims.append(rg.bone('Rim%d' % k, 'Bell', turn_y(outer(.3, a) * V(.9, .9, .9), tilt), turn_y(outer(1.0, a), tilt)))
        rim_tan.append(turn_y(V(-math.sin(a), math.cos(a), 0), tilt))
        rim_rad.append(turn_y(V(math.cos(a), math.sin(a), 0), tilt))
    rows = np.zeros((bell_end - bell_start, Rig.MAXB))
    nring = (nq_o + nq_i - 1) * m
    x = np.tile(A, nq_o + nq_i - 1) / TAU * 8 - .5
    f = smooth(0, 1, x - np.floor(x))
    share = smooth(.2, .58, qq.ravel())
    k0 = np.floor(x).astype(int) % 8
    rows[np.arange(nring), [rg.ix[rims[k]] for k in k0]] += share * (1 - f)
    rows[np.arange(nring), [rg.ix[rims[(k + 1) % 8]] for k in k0]] += share * f
    rows[:nring, rg.ix['Bell']] += 1 - share
    rows[nring:, rg.ix['Bell']] = 1
    rg.bind((bell_start, bell_end), rows)

    def bell(a, b):
        """The bell's outer surface: a 0..1 from crown to margin, b 0..1 round."""
        P = turn_y(outer(a, b * TAU), tilt)
        e = 2e-3
        n = np.cross(turn_y(outer(a + e, b * TAU), tilt) - turn_y(outer(a - e, b * TAU), tilt),
                     turn_y(outer(a, (b + e) * TAU), tilt) - turn_y(outer(a, (b - e) * TAU), tilt))
        n = unit(n)
        return P, (n if np.dot(n, P - low) > 0 else -n)

    # radial canals of light under the bell's skin, and eye-spots in the margin's notches
    for k in range(8):
        a = (k + .5) / 8
        pts = [bell(q, a + .006 * math.sin(q * 9 + k)) for q in np.linspace(.1, .93, 14)]
        ridge(p, [q[0] for q in pts], [q[1] for q in pts], np.linspace(.012, .022, 14), light(GLOW_SERENE, .8), light(GLOW_SERENE, .35))
    for k in range(8):
        P, N = bell(.985, k / 8)
        orb(p, P, .028, light(GLOW_SERENE, 1.0), GLOW, None, 1.0, 1)
    # the soft core: a stomach hanging under the crown, lobed, with a flared mouth
    keys = [turn_y(V(0, 0, z), tilt) for z in (.44, .2, -.05, -.3, -.52)]
    core = Body(keys, 30, 28, ry=[(0, .16), (.15, .30), (.4, .27), (.7, .13), (.9, .11), (1, .16)],
                up_r=[(0, .16), (.15, .30), (.4, .27), (.7, .13), (.9, .11), (1, .16)],
                dn_r=[(0, .16), (.15, .30), (.4, .27), (.7, .13), (.9, .11), (1, .16)], up=(1, 0, 0))
    core.push(.03 * np.cos(4 * core.TH) * np.sin(PI * core.TT) + .012 * np.sin(core.TT * 40) * smooth(.5, .8, core.TT))
    cc = mx(mx(SLATE_MID, CLOTH_VIOLET, .12), PEARL, smooth(.1, .8, core.TT)) * (1 + .15 * mottle(core.G, .12, 9))[..., None]
    core.add(p, lit(cc, 1.0), caps=(.4, -.5))
    rg.bone('Core', 'Bell', core.cp(0), core.cp(.5))
    rg.bone('Mouth', 'Core', core.cp(.5), core.cp(1))
    rg.bind((core.start, core.end), rg.spine_rows(core.vt(), (0, .5, 1.0), ['Core', 'Mouth'], {'Bell': 1}))
    for k in range(4):                                             # four ring organs of light round the crown of the core
        a = (k + .5) * TAU / 4
        st = len(p.v)
        torus(p, (0, 0, 0), .105, .022, light(GLOW_SERENE, .9), GLOW, sides=18, ring=6, arc=TAU * .8, start=a + PI + TAU * .1)
        fl.place(p, st, None, V(.33 * math.cos(a), .33 * math.sin(a), .285))
        p.v[st:] = turn_y(np.asarray(p.v[st:]), tilt).tolist()
        rg.bind((st, len(p.v)), {'Bell': 1})
    # four frilled mouth-arms
    mouth = turn_y(V(0, 0, -.5), tilt)
    arms, tends = [], []
    for k in range(4):
        a = k * TAU / 4 + .4
        d0 = turn_y(V(.5 * math.cos(a), .5 * math.sin(a), -1), tilt)
        nu, nv = 34, 7
        path = trail(rng, mouth + turn_y(V(.08 * math.cos(a), .08 * math.sin(a), .02), tilt), d0, rng.uniform(.75, 1.15), nu,
                     drift=(-.3, 0, -1), stiff=.8, wobble=.35, waves=1.5, curl=.12 * (k == 2))
        T, S, U = frames(path, unit(V(math.cos(a), math.sin(a), .3)))
        u = np.linspace(0, 1, nu)[:, None]
        v = np.linspace(-1, 1, nv)[None, :]
        w = .085 * (1 - .75 * u) * (.4 + .6 * np.sin(PI * np.clip(u * 1.2 + .12, 0, 1)) ** .5)
        ruf = np.sin(u * 30 + k) * np.abs(v) ** 1.5 * w * .8 + np.cos(u * 17 + v * 2) * w * .25
        G = path[:, None, :] + S[:, None, :] * (w * v)[..., None] + U[:, None, :] * ruf[..., None]
        c = lit(mx(mx(PEARL, LICHEN_FROST, .35), mx(CLOTH_PEARL, CRYSTAL_ICE, .5), np.abs(v) * np.ones_like(u)), 1.3 - .2 * u * np.ones_like(v))
        st = len(p.v)
        membrane(p, G, .014, c, c, LICHEN)
        joints = path[[0, 8, 16, 24, 33]]
        names = rg.chain('Arm%d_' % k, 'Mouth', joints)
        rg.bind_proj(st, len(p.v), joints, names, {'Mouth': 1})
        arms.append((names, turn_y(V(-math.sin(a), math.cos(a), 0), tilt), turn_y(V(math.cos(a), math.sin(a), 0), tilt)))
    # the wound: a fracture down one side of the bell (toward +x, +y), violet crystal breaking through it
    P, N = wound(p, bell, .30, .085, .12, .75, .05, rng, 2)
    scorch(p, bell_start, bell_end, P, .2, mx(CRYSTAL_VIOLET, CLOTH_VIOLET, .6), .8)
    shards(p, rng, P, N, 6, .22)
    # tendrils from the margin: long, trailing back and down, some curled; a stinging light at every tip
    count = 15
    for k in range(count):
        a = (k + rng.uniform(-.2, .2)) / count
        P, N = bell(.99, a)
        hurt = abs(((a - .085 + .5) % 1.0) - .5) < .12
        length = rng.uniform(1.0, 1.55) if k % 3 else rng.uniform(1.6, 1.9)
        curl = rng.uniform(.5, 1.1) if k in (2, 6, 9, 13) else 0.0
        if curl:
            length *= .8
        tendril(p, rng, P + N * .005 - V(0, 0, .02), unit(V(0, 0, -1) + N * .25), length, .02, mx(PEARL, CRYSTAL_ICE, .3),
                mx(PEARL, CRYSTAL_VIOLET if hurt else CRYSTAL_ICE, .7), 36, 5, tip=GLOW_VIGIL if hurt else GLOW_SERENE, tip_r=.038,
                beads=.9, bones=('T%d_' % k, 3, rims[int(a * 8) % 8]), drift=(-.38, 0, -1), stiff=1.0, curl=curl, wobble=.3,
                waves=rng.uniform(1.5, 3))
        tends.append((rg.last, turn_y(V(-math.sin(a * TAU), math.cos(a * TAU), 0), tilt), turn_y(V(math.cos(a * TAU), math.sin(a * TAU), 0), tilt), a))

    def squeeze(ph):
        """The pulse, 0 (open) to 1 (contracted): a quick squeeze, a slow opening."""
        return .5 - .5 * math.cos(ph + .7 * math.sin(ph))

    def swim(t):
        """3 s, two pulses: the bell's margin contracts quickly and opens slowly (a ripple running round it), the
        whole animal rocks, the core sways; every tendril trails a travelling wave, swinging in with the squeeze
        and streaming out behind it, and the mouth-arms billow."""
        w = TAU * t / 3.0
        P = Pose()
        P.turn('Bell', YA, .06 * math.sin(w)).turn('Bell', XA, .04 * math.sin(w + 1.3))
        for k, name in enumerate(rims):
            P.turn(name, rim_tan[k], -.12 + .40 * squeeze(2 * w - .25 * math.sin(k * TAU / 8)))
        P.turn('Core', YA, .09 * math.sin(2 * w - 1.0)).turn('Mouth', YA, .12 * math.sin(2 * w - 1.8)).turn('Mouth', XA, .08 * math.sin(w))
        for k, (names, tan, rad) in enumerate(arms):
            P.turn(names, tan, wave(4, .24, 2 * w - 1.6 + k * .6, 1.1, .3) - np.array([.12, .05, 0, 0]) * squeeze(2 * w - .8))
            P.turn(names, rad, wave(4, .16, w + k * 1.7, .9, .3))
        for k, (names, tan, rad, a) in enumerate(tends):
            sq = squeeze(2 * w - .25 * math.sin(a * TAU))
            late = squeeze(2 * w - .25 * math.sin(a * TAU) - 1.0)
            P.turn(names, tan, wave(3, .26, 2 * w - 1.2 - a * TAU, 1.4, .4) + np.array([-.30 * sq - .15 * late, .28 * late, .22 * late]))
            P.turn(names, rad, wave(3, .18, w + k * 2.4, 1.2, .4))
        return P

    def strike(t, P):
        """Gathers with the bell thrown wide open and the tendrils and mouth-arms drawn in beneath it; then the
        bell clenches hard and every tendril flares out and up and whips, its tip cracking a beat later; eases
        back."""
        gather = key(t, [(0, 0), (.5, 1), (.6, .9), (.67, 0), (1.3, 0)])
        hit = key(t, [(0, 0), (.58, 0), (.68, 1), (.82, .8), (1.3, 0)])
        crack = key(t, [(0, 0), (.64, 0), (.74, 1), (.92, .3), (1.3, 0)])
        for k, name in enumerate(rims):
            P.turn(name, rim_tan[k], -.30 * gather + .42 * hit)
        P.turn('Bell', YA, -.12 * gather + .15 * hit)
        for names, tan, rad in arms:
            P.turn(names, tan, np.array([.25, .25, .2, .2]) * gather + np.array([-.75, -.3, .15, .5]) * hit + np.array([0, -.2, -.4, -.7]) * crack)
        for k, (names, tan, rad, a) in enumerate(tends):
            P.turn(names, tan, np.array([.35, .4, .45]) * gather + np.array([-1.25, -.25, .55]) * hit + np.array([0, -.3, -1.1]) * crack)
            P.turn(names, rad, np.array([.1, .3, .5]) * (1 if k % 2 else -1) * crack)
        return P

    fit(p, 1, 1.6)
    return rg.finish(animations(3.0, swim, strike))


# ================================================================ SM_AE_Shellback

def shellback():
    """SM_AE_Shellback (2.2 m long): heavy and armoured. A coiled shell of overlapping grown plates (each lapping
    the next with a raised lip, crystal growing from the seams, a keel along its crown) from whose mouth a soft
    wrinkled head reaches forward under a leathery hood: lidded eyes, a hooked horn beak, and eight short arms,
    curling. One violet fracture runs across the plates of its right flank."""
    rng = np.random.default_rng(5303)
    p = Part('SM_AE_Shellback', (SKIN, ROCK, CRYSTAL, GLOW))
    rg = Rig(p)
    rg.bone('Shell', 'Root', V(0, 0, 0), V(0, 0, .4))
    phi1 = math.radians(-78)
    bgrow = math.log(2.9) / TAU
    r1, plates_per_turn, turns = .47, 15, 1.32
    nplates = int(round(plates_per_turn * turns))
    lips = rng.uniform(.055, .10, nplates + 1)
    lips[-1] = .09

    def shell_pt(phi, th, lip=0.0):
        """A point of the coil at angle phi along it and th round its section (th 0 is the keel)."""
        phi, th = np.asarray(phi, np.float64), np.asarray(th, np.float64)
        rc = r1 * np.exp(bgrow * (phi - phi1))
        rho = .92 * rc * (1 + lip)
        keel = 1 + .06 * np.exp(-(np.abs((th + PI) % TAU - PI) / .22) ** 2)
        rad = rc + rho * np.cos(th) * keel
        return np.stack([rad * np.cos(phi), 1.04 * rho * np.sin(th) * (1 + .03 * np.cos(5 * th)), rad * np.sin(phi)], -1)

    def lip_at(phi):
        s = (phi1 - phi) / (TAU / plates_per_turn)                 # plates counted back from the mouth
        j = int(np.clip(math.floor(s), 0, nplates - 1))
        f = 1 - (s - j)                                            # 0 at the plate's tucked start, 1 at its lip
        return lips[nplates - 1 - j] * max(f, 0.0) ** 1.6, f

    m = 36
    TH = np.linspace(-PI, PI, m, endpoint=False)
    rings, cols = [], []
    per = 6
    for j in range(nplates):
        pa = phi1 - (nplates - j) * TAU / plates_per_turn
        pb = pa + TAU / plates_per_turn
        tint = rng.uniform(.8, 1.05) * (1.12 if j % 2 else .9)
        for f in np.linspace(0, 1, per):
            phi = pa + (pb - pa) * (1e-3 + f * (1 - 2e-3))
            lip = lips[j] * f ** 1.6
            ring = shell_pt(phi, TH, lip)
            ring[:, 1] *= 1 + .012 * math.sin(j * 2.3)
            rings.append(ring)
            base = mx(mx(ROCK_BLUE, STONE_SHADE, .3 + .55 * np.exp(-(TH / 1.0) ** 2)), STONE_WORN, .8 * f ** 2.5)
            base = base * (.42 + .58 * smooth(0, .22, f)) * tint
            cols.append(base)
    t_end = V(-math.sin(phi1), 0, math.cos(phi1))
    for k, back in ((.88, .02), (.8, .3)):                         # the mouth's rim turns in, dark, behind the body
        mid_ = rings[-1].mean(0)
        rings.append(mid_ + (rings[-1] - mid_) * k - t_end * back)
        cols.append(np.tile(rgb(ROCK_DEEP) * .8, (m, 1)))
    rings, cols = np.array(rings), np.array(cols)
    cols = cols * (1 + .16 * mottle(rings, .22, 4) + .1 * mottle(rings, .05, 8))[..., None]
    cols = cols * (.72 + .28 * smooth(-.9, .3, unit(rings - rings.mean(1)[:, None, :])[..., 2]))[..., None]   # paler crown, darker belly
    shell_start = len(p.v)
    out = rings - rings.mean(1)[:, None, :]
    out[-3] = unit(out[-3])
    out[-2:] = t_end * .35 - unit(out[-2:])                        # the rim behind the lip faces forward and in
    loft(p, rings, lit(cols, 1.0), ROCK, out=out, caps=(.4, -.3))
    shell_end = len(p.v)
    rg.bind((shell_start, shell_end), {'Shell': 1})

    def shell(a, b):
        """The shell's surface for fracture(): a 0..1 along the last turn toward the mouth, b 0..1 round."""
        phi = phi1 - (1 - np.clip(a, 0, 1)) * TAU
        lip, _ = lip_at(phi - 1e-6)
        th = (b - .5) * TAU
        P = shell_pt(phi, th, lip)
        e = 1e-3
        n = unit(np.cross(shell_pt(phi + e, th, lip) - shell_pt(phi - e, th, lip), shell_pt(phi, th + e, lip) - shell_pt(phi, th - e, lip)))
        rc = r1 * math.exp(bgrow * (phi - phi1))
        mid = V(rc * math.cos(phi), 0, rc * math.sin(phi))
        return P, (n if np.dot(n, P - mid) > 0 else -n)

    # crystal growing from the seams between plates
    for j in range(nplates - 12, nplates):
        phi = phi1 - (nplates - j) * TAU / plates_per_turn
        for _ in range(int(rng.integers(1, 4))):
            th = rng.uniform(-1.9, 1.9)
            P, N = shell((phi - phi1) / TAU + 1 + .004, th / TAU + .5)
            crystals(p, rng, P, N, rng.uniform(.07, .17) * (1.3 if abs(th) < .5 else 1), int(rng.integers(2, 5)), 0.0, .5)
    # the fracture across the right flank's plates
    P, N = wound(p, shell, .55, .5 + .19, .15, .95, .05, rng, 2, .8)
    scorch(p, shell_start, shell_end, P, .14, SCORCH, .8)
    shards(p, rng, P, N, 7, .2)

    # the soft body: out of the shell's mouth, forward, the head lifted a little
    c1 = shell_pt(phi1, 0.0)
    c1 = V(r1 * math.cos(phi1), 0, r1 * math.sin(phi1))
    t1 = V(-math.sin(phi1), 0, math.cos(phi1))
    b = Body([c1 - t1 * .3, c1 + t1 * .1, c1 + V(.36, .0, .08), c1 + V(.58, .05, .11), c1 + V(.78, .08, .16)], 46, 30,
             ry=[(0, .40), (.3, .37), (.5, .27), (.7, .25), (.86, .27), (1, .19)],
             up_r=[(0, .36), (.3, .34), (.5, .25), (.7, .25), (.86, .26), (1, .17)],
             dn_r=[(0, .36), (.3, .33), (.5, .24), (.7, .21), (.86, .21), (1, .15)])
    b.push(.014 * np.sin(b.TT * 75) * smooth(.3, .45, b.TT) * (1 - smooth(.62, .74, b.TT)) + .012 * mottle(b.G, .09, 2))
    b.add(p, hide(b.G, b.N, mx(SLATE_MID, DUSK, .4), PALE, 6, .14, .22), caps=(.2, .55))
    neck_ts = (.30, .52, .75, 1.0)
    for name, parent, t0, t1 in (('Neck1', 'Shell', .30, .52), ('Neck2', 'Neck1', .52, .75), ('Head', 'Neck2', .75, 1.0)):
        rg.bone(name, parent, b.cp(t0), b.cp(t1))
    neck = ['Neck1', 'Neck2', 'Head']
    rg.bind((b.start, b.end), rg.spine_rows(b.vt(), neck_ts, neck, {'Shell': 1}))
    # the hood: a leathery shield over the head
    tu, tv = np.meshgrid(np.linspace(.36, .9, 16), np.linspace(.5, PI - .5, 15), indexing='ij')
    Gh = np.zeros(tu.shape + (3,))
    for i in range(tu.shape[0]):
        for j in range(tu.shape[1]):
            P, N = b.at(tu[i, j], tv[i, j])
            edge = min(math.sin(PI * i / (tu.shape[0] - 1)), math.sin(PI * j / (tu.shape[1] - 1))) ** .5
            Gh[i, j] = P + N * (.012 + .03 * edge)
    hc = lit(mx(DUSK, SLATE_MID, .5 + .5 * mottle(Gh, .06, 12)), 1.0)
    st = len(p.v)
    membrane(p, Gh, .035, hc, lit(DUSK, .6), SKIN, V(0, 0, 1))
    # the hood follows the neck beneath it at its rear and its own bone (hinged mid-way, on the head) at its lip
    rg.bone('Hood', 'Head', Gh[6, 7], Gh[-1, 7])
    hv = np.asarray(p.v[st:], np.float64)
    along_ = (hv - Gh[0, 7]) @ (Gh[-1, 7] - Gh[0, 7]) / np.dot(Gh[-1, 7] - Gh[0, 7], Gh[-1, 7] - Gh[0, 7])
    lipw = (.9 * smooth(.3, .85, along_))[:, None]
    rg.bind((st, len(p.v)), (1 - lipw) * rg.rows(hv, (b.start, b.end)) + lipw * rg.row({'Hood': 1})[None, :])
    # eyes
    for side in (1, -1):
        P, N = b.at(.80, .12 if side > 0 else PI - .12)
        eye(p, P, unit(N + V(.25, 0, .1)), .052, light(GLOW_SERENE, 1.0), lit(mx(DUSK, SLATE_MID, .3), 1.0))
    # the beak (horn): a hooked upper mandible and a shorter lower one, a little open
    tip = b.c[-1]
    fwd = unit(b.c[-1] - b.c[-4])
    upb = Body([tip - fwd * .08 + V(0, 0, .02), tip + fwd * .1 + V(0, 0, .04), tip + fwd * .25 + V(0, 0, -.01), tip + fwd * .33 + V(0, 0, -.12)], 16, 14,
               ry=[(0, .12), (.4, .10), (.8, .045), (1, .008)], up_r=[(0, .10), (.4, .09), (.8, .045), (1, .008)],
               dn_r=[(0, .03), (.5, .025), (1, .006)])
    upb.add(p, lit(mx(ROCK_BLUE, BONE, smooth(.2, 1, upb.TT) * .8 + .15 * (upb.TH > 0)), 1.0), ROCK, caps=(.2, .5))
    rg.bone('BeakU', 'Head', upb.c[0], upb.c[-1])
    rg.bind((upb.start, upb.end), {'BeakU': 1})
    lob = Body([tip - fwd * .08 + V(0, 0, -.07), tip + fwd * .07 + V(0, 0, -.10), tip + fwd * .17 + V(0, 0, -.10), tip + fwd * .22 + V(0, 0, -.06)], 12, 12,
               ry=[(0, .085), (.5, .06), (1, .008)], up_r=[(0, .025), (.5, .02), (1, .006)], dn_r=[(0, .06), (.5, .05), (1, .008)])
    lob.add(p, lit(mx(ROCK_BLUE, BONE, smooth(.2, 1, lob.TT) * .7), 1.0), ROCK, caps=(.2, .5))
    rg.bone('BeakL', 'Head', lob.c[0], lob.c[-1])
    rg.bind((lob.start, lob.end), {'BeakL': 1})
    arms = []
    # eight short arms round the beak, reaching and curling; light organs along them
    for k in range(8):
        a = (k + .5) * TAU / 8 + rng.uniform(-.12, .12)
        if abs(math.sin(a)) > .9 and math.sin(a) > 0:
            a += .35
        P, N = b.at(.93, a)
        length = rng.uniform(.34, .55) * (1.15 if math.sin(a) < 0 else .9)
        pts = trail(rng, P - N * .04, unit(fwd + N * .55), length, 22, drift=fwd + V(0, 0, -.25 if math.sin(a) < 0 else .1) + N * .2,
                    stiff=.5, curl=rng.uniform(.25, .6) * (1 if k % 3 else -.6), wobble=.2, waves=1.0)
        t = np.linspace(0, 1, 22)
        st = pipe(p, pts, .052 * (1 - .78 * t ** .9), lit(mx(mx(SLATE_MID, DUSK, .3), PALE, t * .8), 1 + .1 * np.sin(t * 40)), SKIN, 8)
        names = rg.chain('Arm%d_' % k, 'Head', pts[[0, 5, 10, 15, 21]])
        rg.bind_pipe(st, 22, 8, names, {'Head': 1})
        arms.append((names, unit(np.cross(fwd, N)), unit(N)))
        for q in (5, 9, 13, 16):
            d = unit(pts[q + 1] - pts[q - 1])
            n = unit(np.cross(d, np.cross(V(0, 0, -1) + fwd * .3, d)))
            spot(p, pts[q] + n * .052 * (1 - .78 * t[q] ** .9) * .9, n, .016 * (1 - .4 * t[q]), light(GLOW_SERENE, .9))

    def swim(t):
        """3 s: the neck and head nod and look from side to side, the hood's lip lifts and settles, the beak works,
        and the eight arms curl and reach in turn, a wave running out each one."""
        w = TAU * t / 3.0
        P = Pose()
        P.turn(neck, YA, [.10 * math.sin(w), .09 * math.sin(w - .8), .10 * math.sin(w - 1.6)])
        P.turn(neck, ZA, [.06 * math.sin(w + 1.0), .08 * math.sin(w + .4), .12 * math.sin(w - .3)])
        P.turn('Hood', YA, -.14 * (.5 + .5 * math.sin(w - 2.2)))
        P.turn('BeakL', YA, .16 * (.5 + .5 * math.sin(2 * w)))
        for k, (names, ax, out) in enumerate(arms):
            P.turn(names, ax, wave(4, .30, w - k * 2.4, 1.0, .3) + .08)
            P.turn(names, out, wave(4, .16, 2 * w + k * 1.3, .8, .3))
        return P

    def strike(t, P):
        """Gathers with the head lifted, the beak gaping and the arms thrown wide; then, for the ram, the arms curl
        in tight round the beak, the beak shuts, and the head is drawn down under the dropped hood; eases back."""
        gather = key(t, [(0, 0), (.5, 1), (.6, .9), (.67, 0), (1.3, 0)])
        tuck = key(t, [(0, 0), (.58, 0), (.68, 1), (.86, .9), (1.3, 0)])
        P.turn(neck, YA, np.array([-.16, -.16, -.12]) * gather + np.array([.38, .30, .22]) * tuck)
        P.turn('Hood', YA, -.22 * gather + .34 * tuck)
        P.turn('BeakL', YA, .40 * gather - .12 * tuck)
        P.turn('BeakU', YA, -.18 * gather)
        for names, ax, out in arms:
            P.turn(names, ax, np.array([.45, .3, .2, .1]) * gather - np.array([.55, .75, .85, .85]) * tuck)
        return P

    fit(p, 0, 2.2)
    return rg.finish(animations(3.0, swim, strike))


# ================================================================ SM_AE_Ray

def ray():
    """SM_AE_Ray (3.2 m wingspan, 2.4 m long): the fast one, a sky-manta. One sleek flattened body whose wings
    are mid-stroke (the right tip raised, the left sweeping down, the trailing edges lagging and rippling), a narrow
    head with two scrolled head-fins and eye-spots, glowing gill slits above and below, a line of lights along each
    wing, a whip tail with a small fin at its root and a crystal sting. A violet fracture crosses the right wing."""
    rng = np.random.default_rng(5404)
    p = Part('SM_AE_Ray', (SKIN, CRYSTAL, GLOW))
    rg = Rig(p)
    nu, nv = 36, 105
    s = np.linspace(-1, 1, nv)
    u = .5 - .5 * np.cos(np.linspace(0, PI, nu))                    # chord fraction, finer at both edges
    a = np.abs(s)
    snout = .34 * np.exp(-(s / .085) ** 2)
    le = .58 - 1.0 * a ** 1.35 + snout
    chord = 1.1 * (1 - a ** 1.7) ** .9 + .04 + snout
    X = le[None, :] - u[:, None] * chord[None, :]
    half = 1.78
    ang = np.where(s > 0, .82 * a ** 1.25, -.5 * a ** 1.1 - .3 * a ** 3)       # the wing's slope across the span
    ds = np.gradient(s) * half
    y = np.cumsum(np.cos(ang) * ds)
    z = np.cumsum(np.sin(ang) * np.sign(s) * ds)
    y, z = y - y[nv // 2], z - z[nv // 2]
    lag = -.16 * (u[:, None] ** 1.6) * np.sin(ang)[None, :] + .03 * np.sin(8 * s + 1.0)[None, :] * (u[:, None] ** 2) * a[None, :]
    Zm = z[None, :] + lag
    Y = np.broadcast_to(y[None, :], X.shape)
    af = (u ** .5) * (1 - u) ** .95 / .39
    tb = .30 * np.exp(-(s / .2) ** 2)
    tw = .08 * (1 - a) ** .75 + .012
    th_ = (tb + tw)[None, :] * af[:, None] + .006
    top = np.stack([X, Y, Zm + .64 * th_], -1)
    bot = np.stack([X, Y, Zm - .36 * th_], -1)
    # hide: a dark back with paler shoulder patches and dusky tips; a pale belly, dark toward the tips and the mouth
    S2, U2 = np.meshgrid(s, u, indexing='xy')
    patch = smooth(.25, .7, mottle(top, .35, 3) * .5 + .5) * np.exp(-((np.abs(S2) - .3) / .2) ** 2) * np.exp(-((U2 - .3) / .22) ** 2)
    ctop = mx(mx(SLATE, DUSK, .3 + .5 * np.abs(S2) ** 2), mx(STONE_SHADE, LICHEN_FROST, .3), .75 * patch)
    ctop = ctop * (1 + .14 * mottle(top, .12, 5))[..., None]
    cbot = mx(PEARL * .95, SLATE_MID, smooth(.55, 1.0, np.abs(S2)) * .7 + .25 * smooth(.4, .9, mottle(bot, .2, 8) * .5 + .5))
    cbot = mx(cbot, MAW, np.exp(-(S2 / .07) ** 2) * np.exp(-((U2 - .035) / .03) ** 2))        # the mouth, under the snout
    body_start = len(p.v)
    shell_pair(p, top, bot, lit(ctop, 1.0), lit(cbot, 1.0), SKIN)
    body_end = len(p.v)
    upper = Surf(top, grid_normals(top) * np.sign(np.sum(grid_normals(top)[nu // 2, nv // 2] * V(0, 0, 1))))
    under = Surf(bot, -upper.N * 0 + grid_normals(bot) * -np.sign(np.sum(grid_normals(bot)[nu // 2, nv // 2] * V(0, 0, 1))))

    def ua(uf):                                                    # chord fraction -> the grid's row parameter
        return float(np.interp(uf, u, np.linspace(0, 1, nu)))

    def sb(sf):
        return (sf + 1) / 2

    # bones: the body, the head, and five down each wing (joints along the 40 % chord line)
    mid = (top + bot) / 2

    def mid_at(uf, sf):
        return (upper(ua(uf), sb(sf))[0] + under(ua(uf), sb(sf))[0]) / 2
    rg.bone('Body', 'Root', mid_at(.6, 0), mid_at(.25, 0))
    rg.bone('Head', 'Body', mid_at(.2, 0), mid_at(0, 0))
    span = (.1, .28, .46, .64, .82, 1.0)
    wingR = rg.chain('WingR', 'Body', [mid_at(.4, q) for q in span])
    wingL = rg.chain('WingL', 'Body', [mid_at(.4, -q) for q in span])
    sc = np.interp(a, span, np.arange(6.0))
    rows = np.where((s > 0)[:, None], rg.chain_rows(sc, wingR, {'Body': 1}, lead=.7), rg.chain_rows(sc, wingL, {'Body': 1}, lead=.7))
    headw = ((1 - smooth(.07, .17, a))[None, :] * (1 - smooth(.12, .28, u))[:, None])[..., None]
    rows = (1 - headw) * rows[None, :, :] + headw * rg.row({'Head': 1})
    rows = rows.reshape(nu * nv, -1)
    rg.bind((body_start, body_start + nu * nv), rows)
    rg.bind((body_start + nu * nv, body_start + 2 * nu * nv), rows)
    rg.stick(body_start + 2 * nu * nv, body_end, (body_start, body_start + 2 * nu * nv))
    slope_r = np.diff(np.r_[0.0, [.82 * q ** 1.25 for q in (.19, .37, .55, .73, .91)]])          # how the rest pose bends each wing
    slope_l = np.diff(np.r_[0.0, [.5 * q ** 1.1 + .3 * q ** 3 for q in (.19, .37, .55, .73, .91)]])
    headfins = []

    # eyes at the sides of the head, on stalked folds
    for side in (1, -1):
        P, N = upper(ua(.13), sb(side * .085))
        eye(p, P - N * .012, unit(N * .5 + V(.35, side, 0)), .042, light(GLOW_SERENE, 1.0), lit(DUSK, .9))
    # head-fins: two scrolled lobes either side of the mouth
    for side in (1, -1):
        P0, _ = upper(ua(.02), sb(side * .075))
        path = curve([P0 + V(-.06, 0, -.04), P0 + V(.12, side * .02, -.06), P0 + V(.24, -side * .01, -.12), P0 + V(.28, -side * .05, -.2)], 12)
        t = np.linspace(0, 1, 12)[:, None]
        v = np.linspace(-1, 1, 7)[None, :]
        w = .085 * (1 - .55 * t)
        scroll = 1.1 * t + .5                                       # the lobe rolls inward toward its tip
        G = path[:, None, :] + (V(0, 0, 1)[None, None, :] * (w * v * np.cos(scroll * v * .9))[..., None] +
                                V(0, -side, 0)[None, None, :] * (w * (1 - np.cos(scroll * v)) * .8)[..., None])
        c = lit(mx(SLATE, PEARL, .5 + .5 * np.sin(scroll * v) * np.ones_like(t)), 1.0)
        st = len(p.v)
        membrane(p, G, .022 - .012 * t * np.ones_like(v), lit(mx(SLATE, DUSK, .3), 1.0), lit(PALE, .85), SKIN, V(0, side, 0))
        names = rg.chain('HeadFinR' if side > 0 else 'HeadFinL', 'Head', path[[0, 6, 11]])
        rg.bind_proj(st, len(p.v), path[[0, 6, 11]], names, {'Head': 1})
        headfins.append((side, names))
    # gill slits of light: five pairs beneath, three above behind the eyes
    for side in (1, -1):
        for k in range(5):
            uf, s0 = .2 + .05 * k, side * (.10 + .012 * k)
            pts = [under(ua(uf + .012 * q), sb(s0 + side * .085 * q)) for q in np.linspace(0, 1, 7)]
            ridge(p, [q[0] for q in pts], [q[1] for q in pts], .026 * np.sin(np.linspace(.25, PI - .25, 7)), light(GLOW_SERENE, 1.0), light(GLOW_SERENE, .4))
        for k in range(3):
            uf, s0 = .25 + .055 * k, side * (.15 + .008 * k)
            pts = [upper(ua(uf + .02 * q), sb(s0 + side * .055 * q)) for q in np.linspace(0, 1, 6)]
            ridge(p, [q[0] for q in pts], [q[1] for q in pts], .022 * np.sin(np.linspace(.3, PI - .3, 6)), light(GLOW_SERENE, 1.0), light(GLOW_SERENE, .4))
        for k in range(9):                                          # a line of lights out along the wing
            sf = side * (.2 + .085 * k)
            P, N = upper(ua(.5 + .012 * k), sb(sf))
            spot(p, P, N, .024 - .0014 * k, light(GLOW_SERENE, .9))
    # small crystal nodes along the spine
    for k, uf in enumerate((.3, .42, .54, .66, .76)):
        P, N = upper(ua(uf), sb(.0))
        crystals(p, rng, P, N, .11 - .012 * k, 2, 0.0, .3, lean=(-.8, 0, 0))
    # the whip tail, from inside the body's rear; a small fin at its root, a sting at its end
    Pr, _ = upper(ua(.7), sb(0))
    Pr = Pr - V(0, 0, .05)
    tail = curve([Pr, Pr + V(-.38, .0, -.01), Pr + V(-.75, .10, .05), Pr + V(-1.0, .24, .0), Pr + V(-1.22, .22, -.14), Pr + V(-1.36, .08, -.20)], 44)
    tt = np.linspace(0, 1, 44)
    tail_start = pipe(p, tail, .062 * (1 - tt) ** 1.3 + .006, lit(mx(SLATE, DUSK, tt), 1 + .1 * np.sin(tt * 90)), SKIN, 8, caps=(.3, .8))
    tail_at = (6, 12, 19, 26, 32, 38, 43)
    tails = rg.chain('Tail', 'Body', tail[list(tail_at)])
    rg.bind_pipe(tail_start, 44, 8, tails, {'Body': 1}, tail_at)
    tail_end = len(p.v)
    d = unit(tail[-1] - tail[-3])
    spike(p, tail[-1] - d * .02, tail[-1] + d * .16, .016, lit(mx(CRYSTAL_ICE, TILE_TEAL, .3), .9), lit(CRYSTAL_CLEAR, 1.0), CRYSTAL, 5, .7)
    orb(p, tail[-1], .02, light(GLOW_SERENE, 1.0), GLOW, None, 1.0, 1)
    root = tail[10:19]
    outer = root + V(-.06, 0, 0) + V(0, 0, 1)[None, :] * (.13 * np.sin(np.linspace(.15, PI, 9)) ** .8)[:, None] + V(-1, 0, 0)[None, :] * np.linspace(0, .09, 9)[:, None]
    G = fan(root, outer, 5)
    rg.stick(membrane_start(p, G, .012, lit(mx(SLATE, DUSK, .5), 1.0), lit(mx(SLATE, DUSK, .5), 1.0), SKIN), None, (tail_start, tail_end))
    # the fracture across the right wing, and a lesser one under the left
    P, N = wound(p, upper, ua(.28), sb(.3), 1.25, .85, .045, rng, 2)
    P2, N2 = wound(p, under, ua(.45), sb(-.45), -1.9, .45, .03, rng, 1)
    scorch(p, body_start, body_end, np.concatenate([P, P2]), .13)
    shards(p, rng, P, N, 6, .17)

    def swim(t):
        """2.4 s, two wingbeats: each beat runs out the wing from root to tip, the trailing edge lagging the stroke;
        the wings are eased toward level from their modelled mid-stroke so the two beat alike; the head dips against
        the beat, the head-fins furl and open, and the tail follows in a slow vertical wave."""
        w = TAU * t / 2.4
        P = Pose()
        beat = wave(5, 1.0, 2 * w, .75) * np.array([.24, .24, .27, .30, .34])
        twist = -.11 * np.array([math.cos(2 * w - .75 * i) for i in range(5)])
        P.turn(wingR, XA, -.7 * slope_r + beat).turn(wingR, YA, twist)
        P.turn(wingL, XA, -.7 * slope_l - beat).turn(wingL, YA, twist)
        P.turn('Body', YA, .05 * math.sin(2 * w + 1.2))
        P.turn('Head', YA, .08 * math.sin(2 * w + 2.6))
        for side, names in headfins:
            P.turn(names, YA, wave(2, .22, 2 * w - .6, .9)).turn(names, ZA, side * .18 * (.5 + .5 * math.sin(w + side)))
        P.turn(tails, YA, wave(6, .09, 2 * w - 1.8, .8, .25)).turn(tails, ZA, wave(6, .06, w, .7, .25))
        return P

    def strike(t, P):
        """Gathers with both wings drawn high and the tail cocked out to its right; then the wings clap down hard,
        the head-fins fling open and the tail lashes across to the left; eases back."""
        wing = key(t, [(0, 0), (.5, 1), (.6, .95), (.68, -1), (.82, -.75), (1.3, 0)])
        lash = key(t, [(0, 0), (.5, .8), (.6, 1), (.69, -1.3), (.84, -.7), (1.3, 0)])
        hit = key(t, [(0, 0), (.6, 0), (.68, 1), (.85, .6), (1.3, 0)])
        up = np.array([.34, .4, .44, .46, .48]) * max(wing, 0) + np.array([.2, .24, .26, .28, .3]) * min(wing, 0)
        P.turn(wingR, XA, up).turn(wingL, XA, -up)
        P.turn('Head', YA, -.18 * max(wing, 0) + .12 * hit)
        P.turn(tails, ZA, np.array([.16, .2, .24, .28, .3, .3]) * lash)
        P.turn(tails, YA, np.array([.05, .06, .08, .08, .08, .08]) * max(lash, 0))
        for side, names in headfins:
            P.turn(names[0], ZA, side * .6 * hit).turn(names, YA, np.array([-.3, -.4]) * hit)
        return P

    fit(p, 1, 3.2)
    return rg.finish(animations(2.4, swim, strike))


# ================================================================ SM_AE_Stalker

def stalker():
    """SM_AE_Stalker (2.8 m long, 2.2 m tall): the territorial hunter, eel and heron. A long body mid-undulation;
    the neck drawn back in an S and the head held high and forward; a wide gulper's jaw agape on needle teeth, its
    throat lit violet; a crest of crystal spines from the crown down the back; an eel's fin fringing the tail; four
    long fin-limbs trailing beneath it (a clawed ray and a web of clear membrane each); a lateral line of blue
    lights; and the most violet fracturing of all the animals: neck, both flanks, back and tail."""
    rng = np.random.default_rng(5505)
    p = Part('SM_AE_Stalker', (SKIN, ROCK, CRYSTAL, GLOW))
    rg = Rig(p)
    b = Body([V(1.02, 0, .66), V(.84, .02, .74), V(.60, .05, .60), V(.46, .06, .30), V(.26, .02, .04), V(-.12, -.09, -.02),
              V(-.52, -.04, .10), V(-.92, .12, .06), V(-1.28, .24, -.10), V(-1.58, .18, -.30)], 110, 30,
             ry=[(0, .095), (.07, .088), (.17, .07), (.27, .085), (.36, .165), (.5, .16), (.64, .12), (.78, .08), (.9, .045), (1, .014)],
             up_r=[(0, .085), (.07, .09), (.17, .08), (.27, .10), (.36, .19), (.5, .185), (.64, .14), (.78, .095), (.9, .055), (1, .016)],
             dn_r=[(0, .075), (.07, .085), (.17, .075), (.27, .10), (.36, .185), (.5, .165), (.64, .12), (.78, .08), (.9, .045), (1, .014)])
    fold = .006 * np.sin(b.TT * 230) * (.4 + .6 * (np.sin(b.TH) < 0)) * smooth(.1, .16, b.TT) * (1 - smooth(.27, .33, b.TT))       # folds where the neck bends
    b.push(fold + .008 * mottle(b.G, .12, 3) + .006 * np.sin(b.TT * 160) * smooth(.7, .8, b.TT))
    bars = .5 + .5 * np.sin(b.TT * 75 + 2.5 * np.sin(b.TH * 2))
    c = rgb(hide(b.G, b.N, mx(SLATE, DUSK, .5), PALE, 4, .16, .2)) * (1 - .22 * bars * smooth(-.2, .6, b.N[..., 2]))[..., None]
    b.add(p, lit(c, 1.0), caps=(.6, .8))
    # bones: the chest; the neck and head forward of it; the back and tail behind it
    rg.bone('Chest', 'Root', b.cp(.46), b.cp(.30))
    neck_ts = (.30, .24, .18, .12, .06, 0.0)
    neck = rg.chain('Neck', 'Chest', [b.cp(t) for t in neck_ts[:5]]) + [rg.bone('Head', 'Neck4', b.cp(.06), b.cp(0) + V(.1, 0, 0))]
    tail_ts = (.46, .56, .66, .76, .86, 1.0)
    tails = []
    for i, name in enumerate(('Back1', 'Back2', 'Tail1', 'Tail2', 'Tail3')):
        tails.append(rg.bone(name, tails[-1] if tails else 'Chest', b.cp(tail_ts[i]), b.cp(tail_ts[i + 1])))
    vt = b.vt()
    rg.bind((b.start, b.end), np.where((vt < .38)[:, None], rg.spine_rows(vt, neck_ts, neck, {'Chest': 1}), rg.spine_rows(vt, tail_ts, tails, {'Chest': 1})))

    def spine_bone(t):
        """The spine bone that holds most of the skin at t."""
        row = rg.spine_rows(np.array([t]), neck_ts, neck, {'Chest': 1})[0] if t < .38 else rg.spine_rows(np.array([t]), tail_ts, tails, {'Chest': 1})[0]
        return rg.bones[int(np.argmax(row))][0]
    # ---- the head: wide jaws agape from the skull's front, the throat lit
    hinge = b.c[0] + V(-.07, 0, -.01)
    d_up, d_lo = unit(V(1, 0, .16)), unit(V(1, .02, -.52))
    L = .56
    upper = Body([hinge, hinge + d_up * L * .35 + V(0, 0, .015), hinge + d_up * L * .75, hinge + d_up * L + V(0, 0, -.03)], 26, 20,
                 ry=[(0, .10), (.3, .135), (.6, .12), (.88, .06), (1, .015)], up_r=[(0, .08), (.3, .06), (.7, .035), (1, .012)],
                 dn_r=[(0, .02), (.5, .016), (1, .008)], power=2.4)
    lower = Body([hinge + V(0, 0, -.03), hinge + d_lo * L * .35 + V(0, 0, -.03), hinge + d_lo * L * .72, hinge + d_lo * L * .95 + V(0, 0, .03)], 26, 20,
                 ry=[(0, .10), (.3, .13), (.6, .115), (.88, .055), (1, .014)], up_r=[(0, .02), (.5, .016), (1, .008)],
                 dn_r=[(0, .10), (.25, .11), (.55, .06), (1, .012)], power=2.4)
    for jaw, inside in ((upper, upper.TH < -.12), (lower, (lower.TH > .12) & (lower.TH < PI - .12))):
        jc = rgb(hide(jaw.G, jaw.N, mx(SLATE, DUSK, .5), PALE, 4, .16, .2))
        jc = np.where(inside[..., None], mx(MAW, CLOTH_VIOLET, .5 * (1 - jaw.TT))[...], jc)
        jaw.add(p, lit(jc, 1.0), caps=(.3, .6))
    rg.bone('Jaw', 'Head', hinge + V(0, 0, -.03), lower.c[-1])
    rg.bind((upper.start, upper.end), {'Head': 1})
    rg.bind((lower.start, lower.end), {'Jaw': 1})
    rg.bind((orb(p, hinge + V(.05, 0, -.035), .075, light(WHITE_VIOLET, 1.0), GLOW, None, 1.0, 2), len(p.v)), {'Head': 1})      # the throat
    pts = [lower.at(t, PI / 2) for t in np.linspace(.12, .7, 9)]
    ridge(p, [q[0] for q in pts], [q[1] for q in pts], np.linspace(.07, .02, 9), light(WHITE_VIOLET, .9), light(GLOW_VIGIL, .5), height=.25)
    pts = [upper.at(t, -PI / 2) for t in np.linspace(.12, .6, 8)]
    ridge(p, [q[0] for q in pts], [q[1] for q in pts], np.linspace(.06, .02, 8), light(GLOW_VIGIL, .8), light(GLOW_VIGIL, .4), height=.25)
    for jaw, th_e, sign, n_t in ((upper, -.13, -1, 10), (lower, .13, 1, 9)):                          # needle teeth
        for side in (1, -1):
            for k in range(n_t):
                t = .2 + .78 * (k + rng.uniform(-.2, .2)) / n_t
                P, N = jaw.at(t, th_e if side > 0 else PI - th_e)
                i = int(t * (jaw.n - 1))
                dv = unit(jaw.U[i] * sign + jaw.S[i] * side * .12 - jaw.T[i] * .3 * 0 + jaw.T[i] * -.25)
                ln = rng.uniform(.035, .075) * (1.25 if k in (n_t - 2, 3) else 1)
                spike(p, P - dv * .012, P + dv * ln, .011, lit(BONE, .75), lit(BONE, 1.1), ROCK, 4, .75)
    # eyes: the right one turned violet
    for side in (1, -1):
        P, N = b.at(.03, .62 if side > 0 else PI - .62)
        eye(p, P, unit(N + V(.4, 0, .1)), .03, light(GLOW_VIGIL if side > 0 else GLOW_SERENE, 1.0), lit(DUSK, .8))
    # ---- the crest: crystal spines from the crown down the back, leaning to the tail
    crest = {}
    for k, t in enumerate(np.linspace(.015, .86, 46)):
        t = t + rng.uniform(-.004, .004)
        P, N = b.at(t, PI / 2 + rng.uniform(-.12, .12))
        i = int(t * (b.n - 1))
        big = .12 + .16 * math.exp(-((t - .40) / .13) ** 2) + .16 * math.exp(-((t - .02) / .035) ** 2) + .05 * math.exp(-((t - .7) / .1) ** 2)
        ln = big * rng.uniform(.7, 1.1)
        d = unit(N + b.T[i] * rng.uniform(.5, .9) + b.S[i] * rng.uniform(-.15, .15))
        vio = rng.random() < (.55 if .3 < t < .62 or t < .08 else .2)
        c0 = mx(CRYSTAL_VIOLET, CLOTH_VIOLET, .4) if vio else mx(CRYSTAL_ICE, TILE_TEAL, .4)
        c1 = mx(CRYSTAL_VIOLET, CRYSTAL_CLEAR, .4) if vio else mx(CRYSTAL_ICE, CRYSTAL_CLEAR, .6)
        st = spike(p, P - d * ln * .12, P + d * ln, ln * rng.uniform(.085, .12) + .004, lit(c0, .8), lit(c1, 1.0), CRYSTAL, 5, .55)
        ci = min(int(t / .875 * 16), 15)                            # sixteen crest bones down the back lift the spines
        if ci not in crest:
            tc = (ci + .5) * .875 / 16
            Pc, Nc = b.at(tc, PI / 2)
            crest[ci] = (rg.bone('Crest%d' % ci, spine_bone(tc), Pc - Nc * .03, Pc + Nc * .15), b.S[int(tc * (b.n - 1))].copy())
        rg.bind((st, len(p.v)), {crest[ci][0]: 1})
    crest = [crest[k] for k in sorted(crest)]
    # ---- the tail's fin: an eel's fringe above and below
    for sgn, th0, hmax in ((1, PI / 2, .17), (-1, -PI / 2, .12)):
        ts = np.linspace(.66, .995, 26)
        root = np.array([b.at(t, th0)[0] - b.at(t, th0)[1] * .008 for t in ts])
        nrm = np.array([b.at(t, th0)[1] for t in ts])
        tang = np.array([b.T[int(t * (b.n - 1))] for t in ts])
        q = np.linspace(0, 1, 26)
        hgt = hmax * np.sin(PI * q ** .8 * .97 + .03) ** .7 + .05 * q ** 3
        outer = root + nrm * hgt[:, None] + tang * (hgt * .9 + .16 * q ** 4)[:, None]
        G = fan(root, outer, 6)
        vv = np.linspace(0, 1, 6)[None, :] * np.ones((26, 1))
        G = G + b.S[-1][None, None, :] * (.03 * np.sin(q * 14 + sgn)[:, None] * vv)[..., None]
        c = lit(mx(mx(CRYSTAL_ICE, SLATE_MID, .3), mx(CRYSTAL_ICE, CRYSTAL_VIOLET, .5), vv), .9 + .1 * np.cos(q * 60)[:, None])
        rg.stick(membrane_start(p, G, .012 - .008 * vv, c, c, CRYSTAL), None, (b.start, b.end))
    # ---- four fin-limbs: a long clawed ray and its web, trailing beneath
    limbs = ((.40, 1, [V(.02, .30, -.22), V(-.16, .38, -.62), V(-.40, .30, -.98), V(-.62, .20, -1.24)], .30),
             (.40, -1, [V(.10, -.26, -.28), V(.06, -.40, -.66), V(-.10, -.36, -1.02), V(-.20, -.22, -1.32)], .28),
             (.60, 1, [V(-.06, .24, -.20), V(-.26, .30, -.50), V(-.50, .22, -.74), V(-.74, .16, -.86)], .22),
             (.61, -1, [V(-.04, -.22, -.24), V(-.16, -.32, -.56), V(-.36, -.30, -.84), V(-.50, -.16, -1.04)], .22))
    legs = []
    for li, (t0, side, offs, web) in enumerate(limbs):
        P0, N0 = b.at(t0, -.5 if side > 0 else PI + .5)
        st = len(p.v)
        n = 32
        path = curve([P0 - N0 * .04] + [P0 + o for o in offs], n)
        t = np.linspace(0, 1, n)
        r = .042 * (1 - t) ** .8 + .007 + .012 * np.exp(-((t - .33) / .05) ** 2)                 # a knuckle at the elbow
        pipe(p, path, r, lit(mx(mx(SLATE, DUSK, .4), PALE, .15 + .5 * t), 1 + .08 * np.sin(t * 50)), SKIN, 8)
        d = unit(path[-1] - path[-3])
        spike(p, path[-1] - d * .02, path[-1] + d * .11 + V(.02, 0, -.01), .012, lit(ROCK_DEEP, 1.0), lit(BONE, .9), ROCK, 4, .8)
        for q in (-.5, .5):
            dq = unit(d + V(0, q, 0) * .6 + V(.3, 0, 0))
            spike(p, path[-2] - dq * .015, path[-2] + dq * .07, .009, lit(ROCK_DEEP, 1.0), lit(BONE, .9), ROCK, 4, .8)
        k0 = 5
        A = path[k0:]
        q = np.linspace(0, 1, n - k0)
        back = unit(V(-1, -side * .25, .28))
        wd = web * np.sin(PI * q ** .75 * .93 + .04) ** .8
        B = A + back[None, :] * wd[:, None]
        G = fan(A, B, 7)
        vv = np.linspace(0, 1, 7)[None, :] * np.ones((n - k0, 1))
        G = G + V(0, side, 0)[None, None, :] * (.025 * np.sin(q * 11 + t0 * 9)[:, None] * vv + .03 * 4 * vv * (1 - vv))[..., None]
        c = lit(mx(mx(CRYSTAL_ICE, SLATE_MID, .35), mx(CRYSTAL_ICE, CRYSTAL_VIOLET, .45), vv), .9 + .1 * np.cos(q * 45)[:, None])
        membrane(p, G, .011 - .007 * vv, c, c, CRYSTAL)
        for f in (.3, .6):                                          # two finer rays through the web
            i = int(f * (n - k0 - 1))
            pipe(p, np.linspace(A[i], B[i] * .95 + A[i] * .05, 6) + V(0, side, 0) * .03 * (4 * np.linspace(0, .95, 6) * (1 - np.linspace(0, .95, 6)))[:, None],
                 np.linspace(.011, .004, 6), lit(mx(SLATE_MID, PALE, .4), 1.0), SKIN, 5)
        joints = path[[0, 10, 20, 31]]
        names = rg.chain(('LimbFR', 'LimbFL', 'LimbRR', 'LimbRL')[li], 'Chest' if li < 2 else 'Back1', joints)
        rg.bind_proj(st, len(p.v), joints, names, ('stick', (b.start, b.end)), lead=.5)
        legs.append((side, names))
    # ---- the lateral line of lights
    for side in (1, -1):
        for k, t in enumerate(np.linspace(.09, .9, 22)):
            P, N = b.at(t, (.02 if side > 0 else PI - .02) + .1 * math.sin(k))
            spot(p, P, N, .016 + .008 * math.exp(-((t - .42) / .15) ** 2), light(GLOW_SERENE, .85))
    # ---- the fractures: neck, right flank (the great one), left flank, back, tail, upper jaw
    nodes, norms = [], []
    for (a0, b0, psi, ln, w, br) in ((.12, .62, .5, .34, .028, 1), (.34, .56, .2, .95, .05, 2), (.40, .33, -.3, .55, .04, 2),
                                     (.52, .82, .35, .5, .035, 1), (.70, .45, .1, .42, .028, 1), (.47, .10, .25, .5, .035, 1)):
        P, N = wound(p, b.ab, a0, b0, psi, ln, w, rng, br)
        shards(p, rng, P, N, max(2, int(ln * 9)), .16 + .1 * (ln > .8))
        nodes.append(P)
    scorch(p, b.start, b.end, np.concatenate(nodes), .1)
    P, N = wound(p, upper.ab, .25, .68, .1, .26, .022, rng, 1)
    scorch(p, upper.start, upper.end, P, .05)
    shards(p, rng, P, N, 2, .08)

    def swim(t):
        """3 s: the neck sways from side to side in a slow wave while the head counters to keep its aim; the jaw
        hangs half shut and works; a ripple of lifting spines runs down the crest; the four fin-limbs paddle in
        turn (front right, rear left, front left, rear right); the back and tail undulate like an eel's, twice."""
        w = TAU * t / 3.0
        P = Pose()
        P.turn(neck[:4], ZA, wave(4, .13, w, .7)).turn(neck[:4], YA, wave(4, .07, 2 * w + .5, .6))
        P.turn('Head', ZA, -.2 * math.sin(w - 1.6)).turn('Head', YA, .07 * math.sin(2 * w - 1.5))
        P.turn('Jaw', YA, -.2 + .1 * math.sin(2 * w))
        P.turn('Chest', ZA, .04 * math.sin(2 * w + 1.2))
        P.turn(tails, ZA, wave(5, .15, 2 * w, 1.0, .35)).turn(tails, YA, wave(5, .04, w + 1.0, .8))
        for i, (name, ax) in enumerate(crest):
            P.turn(name, ax, .10 + .2 * math.sin(w - .4 * i))
        for i, (side, names) in enumerate(legs):
            ph = 2 * w + (0, PI, PI / 2, 3 * PI / 2)[i]
            P.turn(names, YA, wave(3, .26, ph, .9, .3)).turn(names, XA, side * wave(3, .10, ph + 1.2, .9))
        return P

    def strike(t, P):
        """Gathers by rearing: the chest lifts, the neck draws up and back, the crest bristles, the limbs reach
        forward and the tail coils; then the neck snaps forward and down with the jaw wide, the limbs are thrown
        back, and the jaw slams shut just after the reach; eases back."""
        rear = key(t, [(0, 0), (.5, 1), (.6, 1.05), (.69, -1), (.82, -.8), (1.3, 0)])
        up = max(rear, 0)
        jaw = key(t, [(0, 0), (.35, -.25), (.58, .3), (.69, .32), (.76, -.45), (.95, -.4), (1.3, 0)])
        P.turn('Chest', YA, -.14 * up + .06 * min(rear, 0))
        P.turn(neck[:4], YA, np.array([-.24, -.26, -.2, -.1]) * up + np.array([-.26, -.28, -.26, -.2]) * min(rear, 0))
        P.turn('Head', YA, .5 * up - .25 * min(rear, 0) * 0 + .15 * min(rear, 0))
        P.turn('Jaw', YA, jaw)
        for i, (name, ax) in enumerate(crest):
            P.turn(name, ax, .45 * up + .2 * min(rear, 0))
        for i, (side, names) in enumerate(legs):
            P.turn(names, YA, np.array([-.4, -.3, -.2]) * up - np.array([.5, .4, .3]) * min(rear, 0))
            P.turn(names[0], XA, side * .25 * up)
        P.turn(tails, ZA, np.array([.12, .2, .26, .3, .34]) * up + np.array([.1, .14, .16, .16, .16]) * min(rear, 0))
        P.turn(tails, YA, np.array([.05, .08, .1, .1, .1]) * rear)
        return P

    fit(p, 0, 2.8)
    return rg.finish(animations(3.0, swim, strike))


# ================================================================ SM_AE_Leviathan

def leviathan():
    """SM_AE_Leviathan (9 m long, 4 m tall): the sky-whale, huge and slow. A great tapering body in a slow bend,
    head low and tail rising; a pleated throat under a long jaw line; small lidded eyes behind the mouth's corners;
    knobs on the brow; long pectoral fins with knuckled leading edges (the right swept down, the left spread wide);
    a low dorsal fin and a ridge of knuckles to the flukes; barnacle-like cones of horn on its back with crystal
    growing out of them; bioluminescent spots strewn along both flanks; and on its right flank one great violet
    wound: a torn hollow lit from within, cracks running out of it, violet crystal breaking through."""
    rng = np.random.default_rng(5606)
    p = Part('SM_AE_Leviathan', (SKIN, ROCK, CRYSTAL, GLOW))
    rg = Rig(p)
    n, m = 106, 120
    b = Body([V(4.25, 0, -.30), V(3.0, 0, -.08), V(1.5, 0, .12), V(0, 0, .12), V(-1.5, .10, .02), V(-2.8, .26, .10), V(-3.7, .40, .42),
              V(-4.35, .48, .86)], n, m,
             ry=[(0, .34), (.03, .62), (.1, .95), (.22, 1.18), (.38, 1.25), (.55, 1.05), (.7, .70), (.82, .38), (.92, .20), (1, .13)],
             up_r=[(0, .22), (.03, .46), (.1, .78), (.22, 1.02), (.38, 1.15), (.55, 1.0), (.7, .74), (.82, .47), (.92, .31), (1, .17)],
             dn_r=[(0, .30), (.03, .60), (.1, 1.02), (.22, 1.27), (.38, 1.15), (.55, .90), (.7, .60), (.82, .40), (.92, .28), (1, .17)])
    TT, TH = b.TT, b.TH
    side_th = np.where(np.cos(TH) >= 0, TH, np.where(TH > 0, PI - TH, -PI - TH))      # th folded onto the right side
    mouth_th = -.10 - .30 * np.sin(PI * np.clip(TT / .2, 0, 1)) ** 1.3 + .34 * smooth(.14, .2, TT)
    in_mouth = TT < .2
    rad = b.ry[:, None]
    mline = np.exp(-(((side_th - mouth_th) * rad) / .055) ** 2) * in_mouth * smooth(0, .015, TT)
    below = (side_th < mouth_th - .05)
    pleat_w = smooth(.02, .06, TT) * (1 - smooth(.42, .56, TT)) * below * smooth(.0, .12, (mouth_th - .05 - side_th)) * (TH < 0)
    pleat = (.5 + .5 * np.cos(30 * (TH + PI / 2))) ** 3
    wt, wth = .50, .62                                             # the great wound's middle (t, th), on the right flank
    wx = (TT - wt) * b.length
    wy = (TH - wth - .25 * (TT - wt) * 3) * rad
    gash = np.exp(-((wx / .78) ** 2 + (wy / .21) ** 2) ** 1.3)
    b.push(-.06 * mline + .03 * mline * 0 - .045 * pleat * pleat_w - .2 * gash + .035 * mottle(b.G, .9, 2) + .012 * mottle(b.G, .22, 6) +
           .05 * np.exp(-((TT - .86) / .1) ** 2) * np.maximum(np.sin(TT * 260), 0) * np.exp(-((TH - PI / 2) / .4) ** 2))
    c = rgb(hide(b.G, b.N, mx(SLATE, ROCK_BLUE, .45), mx(PEARL, STONE_PALE, .3) * .93, 4, 1.1, .16, -.55, .25))
    scars = smooth(.62, .8, mottle(b.G * V(.35, 1, 1), .22, 21) * .5 + .5) * smooth(-.2, .5, b.N[..., 2])
    c = mx(c, mx(STONE_SHADE, LICHEN_FROST, .3), .4 * scars)
    c = c * (1 - .42 * pleat * pleat_w)[..., None] * (1 - .7 * mline)[..., None]
    c = mx(c, SCORCH, np.clip(gash * 1.6, 0, 1) * .92)
    b.add(p, lit(c, 1.0), caps=(.55, .3))

    def flank(side, t, th):
        return b.at(t, th if side > 0 else PI - th)

    # bones: the chest; neck and head forward of it; back and tail behind; and the lower jaw, hinged at the corners of
    # the mouth, which takes the skin under the mouth line and, fading back to the chest, the pleated throat (so the
    # throat stretches when the jaw drops)
    rg.bone('Chest', 'Root', b.cp(.5), b.cp(.3))
    rg.bone('Neck', 'Chest', b.cp(.30), b.cp(.18))
    rg.bone('Head', 'Neck', b.cp(.18), b.cp(0))
    head_ts, heads = (.30, .18, 0.0), ['Neck', 'Head']
    tail_ts, tails = (.5, .62, .74, .86, 1.0), []
    for i, name in enumerate(('Back1', 'Back2', 'Tail1', 'Tail2')):
        tails.append(rg.bone(name, tails[-1] if tails else 'Chest', b.cp(tail_ts[i]), b.cp(tail_ts[i + 1])))
    hinge = (flank(1, .2, .05)[0] + flank(-1, .2, .05)[0]) / 2
    rg.bone('Jaw', 'Head', hinge, b.cp(0) + V(0, 0, -.45))
    vt = b.vt()
    rows = np.where((vt < .4)[:, None], rg.spine_rows(vt, head_ts, heads, {'Chest': 1}), rg.spine_rows(vt, tail_ts, tails, {'Chest': 1}))
    line = np.where(TT < .2, np.minimum(mouth_th, .05), .05 - (TT - .2) * 7)
    jaw_w = smooth(-.03, .03, line - side_th) * (1 - smooth(.17, .42, TT))
    jaw_w = np.r_[jaw_w.ravel(), 0.0, 0.0][:, None]
    rg.bind((b.start, b.end), (1 - jaw_w) * rows + jaw_w * rg.row({'Jaw': 1})[None, :])

    # eyes, small, behind the corners of the mouth; knobs on the brow
    for side in (1, -1):
        P, N = flank(side, .2, .16)
        eye(p, P, N, .075, lit(ROCK_DEEP, .8), lit(mx(SLATE, DUSK, .5), .9), False, SKIN)
        spot(p, P + N * .09 + V(.015, 0, .02), N, .022, light(GLOW_SERENE, 1.0))
    for k in range(16):
        t, th = rng.uniform(.012, .14), PI / 2 + rng.uniform(-1.0, 1.0)
        P, N = b.at(t, th)
        orb(p, P - N * .02, rng.uniform(.05, .09), lit(mx(SLATE, STONE_SHADE, rng.uniform(.2, .6)), 1.0), SKIN, N, .7, 1)

    def blade(path, chord, width, thick, ctop, cbot, up, nu=11, knobs=0.0, lead=.32):
        """A long fin: sections along `path`, each `width` wide along `chord` (leading edge first) and an aerofoil
        `thick` deep."""
        nvv = len(path)
        v = np.linspace(0, 1, nvv)
        uu = .5 - .5 * np.cos(np.linspace(0, PI, nu))
        ch = unit(np.broadcast_to(np.asarray(chord, np.float64), path.shape))
        w = width * (1 + knobs * np.sin(v * 34) * (v < .92))
        G = path[None, :, :] - ch[None, :, :] * ((uu[:, None] - lead) * w[None, :])[..., None]
        lead_knob = knobs * np.sin(v * 34)[None, :] * w[None, :] * np.exp(-(uu[:, None] / .15) ** 2) * .5
        G = G + ch[None, :, :] * lead_knob[..., None]
        af = (uu ** .5) * (1 - uu) ** .9 / .4
        t = thick[None, :] * af[:, None] + .012
        nrm = grid_normals(G)
        if float(np.sum(nrm * np.asarray(up, np.float64))) < 0:
            nrm = -nrm
        topg, botg = G + nrm * t[..., None] * .55, G - nrm * t[..., None] * .45
        ct = rgb(ctop) * (1 + .15 * mottle(topg, .35, 31))[..., None]
        cb = rgb(cbot) * (1 + .12 * mottle(botg, .35, 32))[..., None]
        shell_pair(p, topg, botg, lit(ct, 1.0), lit(cb, 1.0), SKIN)
        return topg, nrm

    back_c, belly_c = mx(SLATE, ROCK_BLUE, .45), mx(PEARL, STONE_PALE, .3) * .9
    # pectoral fins: the right swept down and back, the left spread wide and a little raised
    pecs, flukes = [], []
    for side, offs in ((1, [V(-.25, .7, -.55), V(-.85, 1.25, -1.25), V(-1.6, 1.55, -1.8), V(-2.3, 1.6, -2.05)]),
                       (-1, [V(-.2, -1.0, -.30), V(-.7, -1.8, -.38), V(-1.4, -2.4, -.25), V(-2.0, -2.65, .0)])):
        P0, N0 = flank(side, .27, -.62)
        path = curve([P0 - N0 * .35] + [P0 + o for o in offs], 30)
        v = np.linspace(0, 1, 30)
        width = .78 * (1 - v ** 2.4) ** .7 * (.7 + .3 * smooth(0, .25, v)) + .05
        st = len(p.v)
        topg, nrm = blade(path, V(-1, 0, .12 * side), width, .2 * (1 - v) ** .8 + .03, back_c, belly_c, V(0, 0, 1), knobs=.05)
        names = rg.chain('PecR' if side > 0 else 'PecL', 'Chest', path[[0, 10, 20, 29]])
        rg.bind_proj(st, len(p.v), path[[0, 10, 20, 29]], names, ('stick', (b.start, b.end)), lead=.5)
        pecs.append((side, names))
        for k in range(5):                                          # lights along the fin
            i = 6 + 5 * k
            spot(p, topg[4, i], nrm[4, i] * np.sign(np.dot(nrm[4, i], topg[4, i] - (topg[4, i] - nrm[4, i]))), .05 - .005 * k, light(GLOW_SERENE, .85))
    # the flukes: two swept lobes on the tail stock, one tip lifting, the other falling
    E, Tt, Ss, Uu = b.c[-1], b.T[-1], b.S[-1], b.U[-1]
    for side, curl in ((1, .32), (-1, -.22)):
        v = np.linspace(0, 1, 24)
        path = (E - Tt * .25)[None, :] + Ss[None, :] * (side * 1.75 * v)[:, None] + Tt[None, :] * (.2 * v + .8 * v ** 2.2)[:, None] + Uu[None, :] * (curl * v ** 1.8)[:, None]
        width = .95 * (1 - v) ** .75 + .07
        st = len(p.v)
        blade(path, -Tt, width, .14 * (1 - v) + .025, back_c, mx(belly_c, back_c, .35), Uu, nu=9, lead=.25)
        names = rg.chain('FlukeR' if side > 0 else 'FlukeL', 'Tail2', path[[0, 12, 23]])
        rg.bind_proj(st, len(p.v), path[[0, 12, 23]], names, ('stick', (b.start, b.end)), lead=.5)
        flukes.append((side, names))
    # the dorsal fin, low and hooked
    ts = np.linspace(.6, .7, 12)
    root = np.array([b.at(t, PI / 2)[0] - b.at(t, PI / 2)[1] * .05 for t in ts])
    q = np.linspace(0, 1, 12)
    path = np.array([root.mean(0) + b.at(.65, PI / 2)[1] * h + b.T[int(.65 * (n - 1))] * (.1 + .55 * (max(h, 0) / .5) ** 1.6) for h in np.linspace(-.05, .5, 10)])
    st = len(p.v)
    blade(path, -b.T[int(.65 * (n - 1))], .62 * (1 - np.linspace(0, 1, 10) ** 1.5) ** .8 + .05, .1 * (1 - np.linspace(0, 1, 10)) + .03, back_c, back_c,
          V(0, 1, 0), nu=7, lead=.4)
    rg.bind((st, len(p.v)), rg.rows(b.at(.65, PI / 2)[0][None, :], (b.start, b.end))[0])      # the dorsal fin rides the back as one piece
    # barnacle cones of horn on the back, crystal growing out of them
    for k in range(13):
        t, th = rng.uniform(.1, .6), PI / 2 + rng.uniform(-.85, .85)
        if abs(t - wt) < .12 and th < PI / 2 - .2:
            th = PI - th
        P0, N0 = b.at(t, th)
        near = abs(t - wt) < .16 and th < PI / 2 + .3
        for j in range(int(rng.integers(3, 7))):
            a_, b_ = frame(N0)
            off = (a_ * rng.normal(0, .16) + b_ * rng.normal(0, .16)) * (j > 0)
            P, N = b.at(t + float(off[0]) * -1 / b.length, th + float(np.dot(off, b.S[int(t * (n - 1))])) / 1.1)
            r = rng.uniform(.07, .15) * (1.3 if j == 0 else 1)
            h = r * rng.uniform(.7, 1.2)
            ang = np.linspace(0, TAU, 9, endpoint=False)
            fr = fl.along(N)
            prof_ = ((1.0, -.25), (.92, .2), (.66, .75), (.5, 1.0), (.36, .8), (.3, .45))
            rr = np.array([[(np.cos(x) * q0 * r * (1 + .12 * math.sin(3 * x + j)), np.sin(x) * q0 * r, q1 * h) for x in ang] for q0, q1 in prof_])
            cc = np.array([lit(mx(ROCK_BLUE, STONE_WORN, w_), 1.0) for w_ in (.15, .3, .55, .7, .3, .1)])
            rr = rr @ fr.T + P
            oo = unit(rr - rr.mean(1)[:, None, :])
            oo[3] = oo[3] + N
            oo[4:] = N * 1.2 - oo[4:]                               # the crater's wall faces in and up
            _ride(p, loft(p, rr, cc, ROCK, out=oo, caps=(None, -.3)), P)
            if rng.random() < .75:
                crystals(p, rng, P + N * h * .45, N, r * rng.uniform(2.2, 4.2), int(rng.integers(1, 4)), .8 if near else .05, .35)
    # bioluminescent spots along both flanks: a main line and a scatter
    for side in (1, -1):
        for k in range(30):
            t = .1 + .78 * k / 29
            th = .22 - .25 * t + .06 * math.sin(k * 1.7)
            if side > 0 and gash[int(t * (n - 1)), int(((th + PI) / TAU) * m) % m] > .05:
                continue
            P, N = flank(side, t, th)
            spot(p, P, N, rng.uniform(.05, .085) * (1 - .4 * t), light(GLOW_SERENE, .9))
        for k in range(26):
            t, th = rng.uniform(.14, .8), rng.uniform(-.5, .75)
            if side > 0 and gash[int(t * (n - 1)), int(((th + PI) / TAU) * m) % m] > .03:
                continue
            P, N = flank(side, t, th)
            spot(p, P, N, rng.uniform(.022, .045), light(GLOW_SERENE, .8))
    # the great wound: light in the torn hollow, cracks running out, violet crystal breaking through
    a0, b0 = wt, (wth + PI) / TAU
    nodes, norms = [], []
    for da, psi, ln, w, br in ((-.075, .18, 1.5, .2, 0), (-.06, .5, .9, .1, 1), (.0, -.4, .8, .09, 1), (.05, 1.3, 1.1, .08, 2), (-.03, -1.5, 1.0, .08, 2),
                               (.07, .1, 1.0, .08, 1), (-.08, 2.7, .9, .08, 1), (-.02, 1.8, .7, .06, 1)):
        P, N = wound(p, b.ab, a0 + da, b0 + .012 * (da * 30), psi, ln, w, rng, br, .6)
        nodes.append(P)
        norms.append(N)
    nodes, norms = np.concatenate(nodes), np.concatenate(norms)
    scorch(p, b.start, b.end, nodes, .3, SCORCH, .8)
    shards(p, rng, nodes, norms, 22, .5)
    fluke_span = unit(b.S[-1])

    def swim(t):
        """4 s, one slow stroke: a vertical wave travels from the chest down the back and tail and out through the
        flukes (which pitch and curl after it); the head nods against it; the long fins sweep down and up, their
        tips trailing; the jaw eases open a little and closes."""
        w = TAU * t / 4.0
        P = Pose()
        P.turn(tails, YA, wave(4, .11, w, .85, .45)).turn(tails, ZA, wave(4, .03, w + 1.0, .8))
        P.turn(heads, YA, [.045 * math.sin(w + 2.4), .06 * math.sin(w + 1.8)])
        P.turn('Jaw', YA, .07 + .06 * math.sin(w - .6))
        for side, names in flukes:
            P.turn(names, YA, [.22 * math.sin(w - 3.2), .18 * math.sin(w - 4.0)])
            P.turn(names, XA, [side * .08 * math.sin(w - 3.4), side * .14 * math.sin(w - 4.2)])
        for side, names in pecs:
            P.turn(names, XA, side * wave(3, .27, w + .6 + (0 if side > 0 else .9), .8, .25))
            P.turn(names, ZA, -side * wave(3, .09, w - .5, .8))
            P.turn(names, YA, wave(3, .07, w + 2.0, .8))
        return P

    def strike(t, P):
        """Gathers with the head lifting, the jaw starting to drop, the tail raised and the fins drawn up; then the
        jaw gapes wide (the throat stretching with it) as the upper head lifts away, the tail and flukes drive
        down, and the fins flare out and forward; eases back."""
        gather = key(t, [(0, 0), (.5, 1), (.6, 1), (.68, 0), (1.3, 0)])
        hit = key(t, [(0, 0), (.58, 0), (.69, 1), (.85, .85), (1.3, 0)])
        P.turn('Jaw', YA, .28 * gather + .72 * hit)
        P.turn(heads, YA, np.array([-.05, -.07]) * gather + np.array([-.08, -.14]) * hit)
        P.turn(tails, YA, np.array([.06, .09, .12, .14]) * gather - np.array([.09, .13, .17, .2]) * hit)
        for side, names in flukes:
            P.turn(names, YA, np.array([.25, .2]) * gather - np.array([.4, .35]) * hit)
            P.turn(names[1], XA, side * .25 * hit)
        for side, names in pecs:
            P.turn(names, XA, side * (np.array([.18, .12, .1]) * gather + np.array([.42, .2, .12]) * hit))
            P.turn(names[0], ZA, -side * (.42 * hit - .12 * gather))
        return P

    fit(p, 0, 9.0)
    return rg.finish(animations(4.0, swim, strike))


# ---------------------------------------------------------------- the module's meshes and their contract

MESHES = [mote, medusa, shellback, ray, stalker, leviathan]

CONTRACT = {
    'SM_AE_Mote': {'size': (0, .8, 0), 'tol': .1, 'pivot': 'centre'},              # 0.8 m across its wing-fins
    'SM_AE_Medusa': {'size': (0, 1.6, 2.6), 'tol': .1, 'pivot': 'centre'},         # the bell 1.6 m across; 2.6 m tall
    'SM_AE_Shellback': {'size': (2.2, 0, 0), 'tol': .1, 'pivot': 'centre'},        # 2.2 m long
    'SM_AE_Ray': {'size': (2.4, 3.2, 0), 'tol': .1, 'pivot': 'centre'},            # 2.4 m long, 3.2 m wingspan
    'SM_AE_Stalker': {'size': (2.8, 0, 2.2), 'tol': .1, 'pivot': 'centre'},        # 2.8 m long, 2.2 m tall
    'SM_AE_Leviathan': {'size': (9.0, 0, 4.0), 'tol': .1, 'pivot': 'centre'},      # 9 m long, 4 m tall
}


if __name__ == '__main__':
    import check
    for _part in check.builds(sys.modules[__name__]):
        _v = np.asarray(_part.v)
        print('%s  %d tris  %s .. %s' % (_part.name, _part.triangles(), np.round(_v.min(0), 3).tolist(), np.round(_v.max(0), 3).tolist()))
