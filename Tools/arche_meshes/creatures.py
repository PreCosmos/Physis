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
    return part.add(local + np.asarray(c, np.float64), f, colour, slot, True)


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
        part.add(local @ np.stack([a, b, unit(N)], 1).T + P + N * r * .95, toolkit.ICO[1][1], lit(ROCK_DEEP, .6), SKIN, True)


def spike(part, base, tip, r, c0, c1, slot=CRYSTAL, sides=5, tip_len=.4):
    """A crystal (or tooth, or claw) from base to tip, c0 at its foot and c1 at its point."""
    start = prism(part, base, tip, r, c0, slot, sides, tip_len, False)
    cols = np.concatenate([np.tile(rgba(c0), (sides, 1)), np.tile(rgba(mx(c0, c1, .55)), (sides, 1)), rgba(c1)[None, :]])
    part.c[start:start + 2 * sides + 1] = cols.tolist()
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


def tendril(part, rng, start, d0, length, r0, c0, c1, n=26, sides=5, tip=None, tip_r=None, beads=0.0, **kw):
    """A trailing tendril (hide), thinning from r0, coloured c0 to c1; tip: the colour of a light at its end."""
    pts = trail(rng, start, d0, length, n, **kw)
    t = np.linspace(0, 1, n)
    r = r0 * (1 - .82 * t ** .8)
    if beads:
        r = r * (1 + beads * np.maximum(np.sin(t * TAU * length / .11 + rng.uniform(0, 6)), 0) ** 4 * (t > .15))
    pipe(part, pts, r, lit(mx(c0, c1, t), 1.0), SKIN, sides)
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
    return part.add(verts, _oriented(verts, faces, np.concatenate([N, N, N])), np.concatenate([ce, cm, ce]), slot, True)


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
    centre(part)
    v = np.asarray(part.v, np.float64)
    v *= size / (v[:, axis].max() - v[:, axis].min())
    part.v = v.tolist()
    return centre(part)


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


# ================================================================ SM_AE_Mote

def mote():
    """SM_AE_Mote (0.8 m across its wing-fins): the swarm animal, a darting sea-angel. A small soft body bent
    mid-dart, a dome of clear crystal over its back with a line of light organs showing through, two wing-fins
    mid-stroke (the right raised, the left sweeping down), two head feelers, short trailing tendrils, two bright
    eye-spots, and one small violet fracture on its flank."""
    rng = np.random.default_rng(5101)
    p = Part('SM_AE_Mote', (SKIN, CRYSTAL, GLOW))
    b = Body([V(.25, 0, .0), V(.12, 0, .03), V(-.04, .0, .03), V(-.18, .03, -.01), V(-.30, .08, -.07)], 34, 20,
             ry=[(0, .045), (.1, .078), (.3, .088), (.6, .058), (.85, .032), (1, .014)],
             up_r=[(0, .045), (.1, .08), (.3, .092), (.6, .06), (.85, .034), (1, .014)],
             dn_r=[(0, .04), (.1, .066), (.3, .074), (.6, .05), (.85, .028), (1, .012)])
    b.push(.004 * np.sin(b.TT * 70) * smooth(.45, .7, b.TT))                    # soft rings on the tail
    b.add(p, hide(b.G, b.N, SLATE_MID, PEARL, 3, .08, .16), caps=(.7, .8))
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
    loft(p, rings, lit(mx(CRYSTAL_ICE, CRYSTAL_CLEAR, tt), 1.0), CRYSTAL, caps=(.3, .3))
    for k, tk in enumerate(np.linspace(.16, .68, 6)):
        P, N = b.at(tk, PI / 2)
        orb(p, P + N * .012, .013 - .001 * k, light(GLOW_SERENE, 1.0), GLOW, None, 1.0, 1)
    # wing-fins (clear membrane on three soft rays): right raised, left sweeping down
    for side, lift, sweep in ((1, .24, -.02), (-1, -.10, -.10)):
        th = .45 if side > 0 else PI - .45
        root = np.array([b.at(tk, th)[0] - b.at(tk, th)[1] * .01 for tk in np.linspace(.2, .5, 9)])
        mid = root[4]
        tipv = V(sweep, side * .36, lift)
        outer = curve([root[0] + V(.07, side * .16, lift * .5), mid + tipv + V(.07, 0, 0), mid + tipv, mid + tipv * .8 + V(-.12, 0, -.03 * side),
                       root[-1] + V(-.10, side * .12, lift * .2)], 9)
        G = fan(root, outer, 8, V(0, 0, .035 if side > 0 else -.03))
        uu, vv = np.meshgrid(np.linspace(0, 1, 9), np.linspace(0, 1, 8), indexing='ij')
        c = lit(mx(mx(CRYSTAL_ICE, SLATE_MID, .25), CRYSTAL_CLEAR, vv), .95 + .05 * np.cos(uu * 25))
        membrane(p, G, .007 - .004 * vv, c, c, CRYSTAL, V(0, 0, 1))
        for u in (1, 4, 7):
            pipe(p, G[u, :7], np.linspace(.008, .003, 7), lit(mx(SLATE_MID, PEARL, np.linspace(.1, .8, 7)), 1.0), SKIN, 5)
    # feelers on the head, tendrils from the tail
    for side in (1, -1):
        P, N = b.at(.03, PI / 2 - side * .7)
        tendril(p, rng, P - N * .01, unit(V(.7, side * .5, .6)), .12, .011, SLATE_MID, PEARL, 10, 5, drift=(1, side * .3, .1), stiff=.5, wobble=.1)
    for k in range(5):
        th = -PI / 2 + (k - 2) * 1.1 + rng.uniform(-.2, .2)
        P, N = b.at(.86 + .02 * (k % 2), th)
        tendril(p, rng, P - N * .008, unit(N * .5 + V(-1, .25, -.2)), rng.uniform(.17, .30), .010, PEARL, mx(PEARL, CRYSTAL_ICE, .6), 16, 5,
                tip=GLOW_SERENE if k % 2 == 0 else None, tip_r=.011, drift=(-1, .35, -.25), stiff=.8, curl=(.45 if k == 3 else 0), wobble=.3)
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
    return fit(p, 1, .8)


# ================================================================ SM_AE_Medusa

def medusa():
    """SM_AE_Medusa (1.6 m across the bell, 2.6 m tall with its tendrils): the ranged attacker. A bell of
    translucent crystal-flesh, thick at the crown and scalloped at the margin, tipped forward as it drifts; inside
    it a soft core with four ring organs of light and four frilled mouth-arms; from the margin a ring of long
    tendrils trailing back, some curled, each ending in a stinging light. A violet fracture has split one side of
    the bell."""
    rng = np.random.default_rng(5202)
    p = Part('SM_AE_Medusa', (SKIN, CRYSTAL, GLOW, LICHEN))
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
    for k in range(4):                                             # four ring organs of light round the crown of the core
        a = (k + .5) * TAU / 4
        st = len(p.v)
        torus(p, (0, 0, 0), .105, .022, light(GLOW_SERENE, .9), GLOW, sides=18, ring=6, arc=TAU * .8, start=a + PI + TAU * .1)
        fl.place(p, st, None, V(.33 * math.cos(a), .33 * math.sin(a), .285))
        p.v[st:] = turn_y(np.asarray(p.v[st:]), tilt).tolist()
    # four frilled mouth-arms
    mouth = turn_y(V(0, 0, -.5), tilt)
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
        membrane(p, G, .014, c, c, LICHEN)
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
                beads=.9, drift=(-.38, 0, -1), stiff=1.0, curl=curl, wobble=.3, waves=rng.uniform(1.5, 3))
    fit(p, 1, 1.6)
    return p


# ================================================================ SM_AE_Shellback

def shellback():
    """SM_AE_Shellback (2.2 m long): heavy and armoured. A coiled shell of overlapping grown plates (each lapping
    the next with a raised lip, crystal growing from the seams, a keel along its crown) from whose mouth a soft
    wrinkled head reaches forward under a leathery hood: lidded eyes, a hooked horn beak, and eight short arms,
    curling. One violet fracture runs across the plates of its right flank."""
    rng = np.random.default_rng(5303)
    p = Part('SM_AE_Shellback', (SKIN, ROCK, CRYSTAL, GLOW))
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
    # the hood: a leathery shield over the head
    tu, tv = np.meshgrid(np.linspace(.36, .9, 16), np.linspace(.5, PI - .5, 15), indexing='ij')
    Gh = np.zeros(tu.shape + (3,))
    for i in range(tu.shape[0]):
        for j in range(tu.shape[1]):
            P, N = b.at(tu[i, j], tv[i, j])
            edge = min(math.sin(PI * i / (tu.shape[0] - 1)), math.sin(PI * j / (tu.shape[1] - 1))) ** .5
            Gh[i, j] = P + N * (.012 + .03 * edge)
    hc = lit(mx(DUSK, SLATE_MID, .5 + .5 * mottle(Gh, .06, 12)), 1.0)
    membrane(p, Gh, .035, hc, lit(DUSK, .6), SKIN, V(0, 0, 1))
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
    lob = Body([tip - fwd * .08 + V(0, 0, -.07), tip + fwd * .07 + V(0, 0, -.10), tip + fwd * .17 + V(0, 0, -.10), tip + fwd * .22 + V(0, 0, -.06)], 12, 12,
               ry=[(0, .085), (.5, .06), (1, .008)], up_r=[(0, .025), (.5, .02), (1, .006)], dn_r=[(0, .06), (.5, .05), (1, .008)])
    lob.add(p, lit(mx(ROCK_BLUE, BONE, smooth(.2, 1, lob.TT) * .7), 1.0), ROCK, caps=(.2, .5))
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
        pipe(p, pts, .052 * (1 - .78 * t ** .9), lit(mx(mx(SLATE_MID, DUSK, .3), PALE, t * .8), 1 + .1 * np.sin(t * 40)), SKIN, 8)
        for q in (5, 9, 13, 16):
            d = unit(pts[q + 1] - pts[q - 1])
            n = unit(np.cross(d, np.cross(V(0, 0, -1) + fwd * .3, d)))
            spot(p, pts[q] + n * .052 * (1 - .78 * t[q] ** .9) * .9, n, .016 * (1 - .4 * t[q]), light(GLOW_SERENE, .9))
    return fit(p, 0, 2.2)


# ================================================================ SM_AE_Ray

def ray():
    """SM_AE_Ray (3.2 m wingspan, 2.4 m long): the fast one, a sky-manta. One sleek flattened body whose wings
    are mid-stroke (the right tip raised, the left sweeping down, the trailing edges lagging and rippling), a narrow
    head with two scrolled head-fins and eye-spots, glowing gill slits above and below, a line of lights along each
    wing, a whip tail with a small fin at its root and a crystal sting. A violet fracture crosses the right wing."""
    rng = np.random.default_rng(5404)
    p = Part('SM_AE_Ray', (SKIN, CRYSTAL, GLOW))
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
        membrane(p, G, .022 - .012 * t * np.ones_like(v), lit(mx(SLATE, DUSK, .3), 1.0), lit(PALE, .85), SKIN, V(0, side, 0))
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
    pipe(p, tail, .062 * (1 - tt) ** 1.3 + .006, lit(mx(SLATE, DUSK, tt), 1 + .1 * np.sin(tt * 90)), SKIN, 8, caps=(.3, .8))
    d = unit(tail[-1] - tail[-3])
    spike(p, tail[-1] - d * .02, tail[-1] + d * .16, .016, lit(mx(CRYSTAL_ICE, TILE_TEAL, .3), .9), lit(CRYSTAL_CLEAR, 1.0), CRYSTAL, 5, .7)
    orb(p, tail[-1], .02, light(GLOW_SERENE, 1.0), GLOW, None, 1.0, 1)
    root = tail[10:19]
    outer = root + V(-.06, 0, 0) + V(0, 0, 1)[None, :] * (.13 * np.sin(np.linspace(.15, PI, 9)) ** .8)[:, None] + V(-1, 0, 0)[None, :] * np.linspace(0, .09, 9)[:, None]
    G = fan(root, outer, 5)
    membrane(p, G, .012, lit(mx(SLATE, DUSK, .5), 1.0), lit(mx(SLATE, DUSK, .5), 1.0), SKIN)
    # the fracture across the right wing, and a lesser one under the left
    P, N = wound(p, upper, ua(.28), sb(.3), 1.25, .85, .045, rng, 2)
    P2, N2 = wound(p, under, ua(.45), sb(-.45), -1.9, .45, .03, rng, 1)
    scorch(p, body_start, body_end, np.concatenate([P, P2]), .13)
    shards(p, rng, P, N, 6, .17)
    return fit(p, 1, 3.2)


# ================================================================ SM_AE_Stalker

def stalker():
    """SM_AE_Stalker (2.8 m long, 2.2 m tall): the territorial hunter, eel and heron. A long body mid-undulation;
    the neck drawn back in an S and the head held high and forward; a wide gulper's jaw agape on needle teeth, its
    throat lit violet; a crest of crystal spines from the crown down the back; an eel's fin fringing the tail; four
    long fin-limbs trailing beneath it (a clawed ray and a web of clear membrane each); a lateral line of blue
    lights; and the most violet fracturing of all the animals: neck, both flanks, back and tail."""
    rng = np.random.default_rng(5505)
    p = Part('SM_AE_Stalker', (SKIN, ROCK, CRYSTAL, GLOW))
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
    orb(p, hinge + V(.05, 0, -.035), .075, light(WHITE_VIOLET, 1.0), GLOW, None, 1.0, 2)             # the throat
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
        spike(p, P - d * ln * .12, P + d * ln, ln * rng.uniform(.085, .12) + .004, lit(c0, .8), lit(c1, 1.0), CRYSTAL, 5, .55)
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
        membrane(p, G, .012 - .008 * vv, c, c, CRYSTAL)
    # ---- four fin-limbs: a long clawed ray and its web, trailing beneath
    limbs = ((.40, 1, [V(.02, .30, -.22), V(-.16, .38, -.62), V(-.40, .30, -.98), V(-.62, .20, -1.24)], .30),
             (.40, -1, [V(.10, -.26, -.28), V(.06, -.40, -.66), V(-.10, -.36, -1.02), V(-.20, -.22, -1.32)], .28),
             (.60, 1, [V(-.06, .24, -.20), V(-.26, .30, -.50), V(-.50, .22, -.74), V(-.74, .16, -.86)], .22),
             (.61, -1, [V(-.04, -.22, -.24), V(-.16, -.32, -.56), V(-.36, -.30, -.84), V(-.50, -.16, -1.04)], .22))
    for t0, side, offs, web in limbs:
        P0, N0 = b.at(t0, -.5 if side > 0 else PI + .5)
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
    fit(p, 0, 2.8)
    return p


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
    for side, offs in ((1, [V(-.25, .7, -.55), V(-.85, 1.25, -1.25), V(-1.6, 1.55, -1.8), V(-2.3, 1.6, -2.05)]),
                       (-1, [V(-.2, -1.0, -.30), V(-.7, -1.8, -.38), V(-1.4, -2.4, -.25), V(-2.0, -2.65, .0)])):
        P0, N0 = flank(side, .27, -.62)
        path = curve([P0 - N0 * .35] + [P0 + o for o in offs], 30)
        v = np.linspace(0, 1, 30)
        width = .78 * (1 - v ** 2.4) ** .7 * (.7 + .3 * smooth(0, .25, v)) + .05
        topg, nrm = blade(path, V(-1, 0, .12 * side), width, .2 * (1 - v) ** .8 + .03, back_c, belly_c, V(0, 0, 1), knobs=.05)
        for k in range(5):                                          # lights along the fin
            i = 6 + 5 * k
            spot(p, topg[4, i], nrm[4, i] * np.sign(np.dot(nrm[4, i], topg[4, i] - (topg[4, i] - nrm[4, i]))), .05 - .005 * k, light(GLOW_SERENE, .85))
    # the flukes: two swept lobes on the tail stock, one tip lifting, the other falling
    E, Tt, Ss, Uu = b.c[-1], b.T[-1], b.S[-1], b.U[-1]
    for side, curl in ((1, .32), (-1, -.22)):
        v = np.linspace(0, 1, 24)
        path = (E - Tt * .25)[None, :] + Ss[None, :] * (side * 1.75 * v)[:, None] + Tt[None, :] * (.2 * v + .8 * v ** 2.2)[:, None] + Uu[None, :] * (curl * v ** 1.8)[:, None]
        width = .95 * (1 - v) ** .75 + .07
        blade(path, -Tt, width, .14 * (1 - v) + .025, back_c, mx(belly_c, back_c, .35), Uu, nu=9, lead=.25)
    # the dorsal fin, low and hooked
    ts = np.linspace(.6, .7, 12)
    root = np.array([b.at(t, PI / 2)[0] - b.at(t, PI / 2)[1] * .05 for t in ts])
    q = np.linspace(0, 1, 12)
    path = np.array([root.mean(0) + b.at(.65, PI / 2)[1] * h + b.T[int(.65 * (n - 1))] * (.1 + .55 * (max(h, 0) / .5) ** 1.6) for h in np.linspace(-.05, .5, 10)])
    blade(path, -b.T[int(.65 * (n - 1))], .62 * (1 - np.linspace(0, 1, 10) ** 1.5) ** .8 + .05, .1 * (1 - np.linspace(0, 1, 10)) + .03, back_c, back_c,
          V(0, 1, 0), nu=7, lead=.4)
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
            loft(p, rr, cc, ROCK, out=oo, caps=(None, -.3))
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
    fit(p, 0, 9.0)
    return p


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
