"""Level 4, Earth, the Wounded Grove: the Hedge (enemies), the people, the link props and the gameplay props, the
SM_GE_*, SM_GP_* and SM_GN_* meshes of Tools/grove/README.md ("The Hedge, the people and gameplay props").

Pure numpy on kit.py (the Conclave's toolkit and al_flora's machine helpers); never imports bpy. Check and look:

    PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/grove_meshes/check.py machines --preview

Realism (author, 2026-11-10): these are built as engineered or grown objects, since scanned PBR textures are laid over
each slot and geometry and silhouette carry the rest. Round parts are tessellated by size (S(), a chord length per
builder), so nothing large reads as faceted.

  The grove's own things (link props, the root bridge) are living root-wood: fluted roots whose ridges twist along
  them (root()), fused into braids and knots, with burl knots and hair rootlets, round a glowing seed or core.
  Resonance is GLOW_LINK; a water flow GLOW_FLOW_WATER, a power flow GLOW_FLOW_POWER, the surge GLOW_LINK. Sources are
  at full brightness, receivers and relays at a quarter.
  Thornroot is forced Divinity: black-violet roots (THORN) with hooked thorns and magenta embers (GLOW_BLIGHT, .5).

Points gameplay needs (a core a beam attaches to, a lens, a palm) are recorded on each Part as marks (mark()), in the
mesh's own final coordinates; `python3 Tools/grove_meshes/machines.py` prints them all.
"""
import contextlib
import functools

from kit import *

unit, basis, along, place = fl.unit, fl.basis, fl.along, fl.place
ball, disc, obox, strut, slab, fin, Hull, glow = fl.ball, fl.disc, fl.obox, fl.strut, fl.slab, fl.fin, fl.Hull, fl.glow
norm = np.linalg.norm

DIM = .25          # a waiting receiver's or relay's core, against a source's 1.0
FLOWS = (('Water', GLOW_FLOW_WATER), ('Power', GLOW_FLOW_POWER), ('Surge', GLOW_LINK))


def V(*x):
    return np.array(x, np.float64)


def rgba(rgb):
    rgb = np.clip(np.asarray(rgb, np.float64), 0.0, None)
    return np.concatenate([rgb, np.ones(rgb.shape[:-1] + (1,))], -1)


# ---------------------------------------------------------------- tessellation by size

_CHORD = [.03]


@contextlib.contextmanager
def chord(length):
    """Round parts built inside the block get sides about `length` metres long (S())."""
    before, _CHORD[0] = _CHORD[0], length
    try:
        yield
    finally:
        _CHORD[0] = before


def S(r, lo=8, hi=48):
    """Sides for a round part of radius r at the current chord length."""
    return int(np.clip(round(TAU * abs(r) / _CHORD[0]), lo, hi))


def built(length):
    """A builder whose round parts are tessellated to `length` metre chords."""
    def wrap(builder):
        @functools.wraps(builder)
        def build(*args):
            with chord(length):
                return builder(*args)
        return build
    return wrap


# ---------------------------------------------------------------- marks and finishing

def mark(part, name, point):
    """Records a point gameplay needs on the part; the finishing helpers move it with the mesh."""
    if not hasattr(part, 'marks'):
        part.marks = {}
    part.marks[name] = np.asarray(point, np.float64)


def _moved(part, shift=(0, 0, 0), k=1.0):
    v = np.asarray(part.v, np.float64)
    part.v = ((v + np.asarray(shift, np.float64)) * k).tolist()
    part.marks = {name: (q + np.asarray(shift, np.float64)) * k for name, q in getattr(part, 'marks', {}).items()}
    return part


def stand(part, centre_xy=True, ground=True):
    """kit.finish() that carries the marks: lowest point to z 0, footprint centred on the origin."""
    v = np.asarray(part.v, np.float64)
    lo, hi = v.min(0), v.max(0)
    shift = (-(lo[0] + hi[0]) / 2 if centre_xy else 0.0, -(lo[1] + hi[1]) / 2 if centre_xy else 0.0, -lo[2] if ground else 0.0)
    return fl.card_normals(_moved(part, shift))


def fit_box(part, size):
    """Scales each axis so the bounds are exactly size (x, y, z; 0 leaves an axis alone), about the bounds' centre."""
    v = np.asarray(part.v, np.float64)
    lo, hi = v.min(0), v.max(0)
    k = np.array([s / max(h - l, 1e-9) if s else 1.0 for s, l, h in zip(size, lo, hi)])
    mid = (lo + hi) / 2
    part.v = ((v - mid) * k + mid).tolist()
    part.marks = {name: (q - mid) * k + mid for name, q in getattr(part, 'marks', {}).items()}
    return part


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


# ---------------------------------------------------------------- paths and swept solids

def spline(keys, n):
    """A smooth path through key points (Catmull-Rom), n samples; keys may have any number of columns."""
    P = np.asarray(keys, np.float64)
    m = len(P)
    t = np.linspace(0, m - 1, n)
    i = np.clip(np.floor(t).astype(int), 0, m - 2)
    u = (t - i)[:, None]
    p0, p1, p2, p3 = P[np.clip(i - 1, 0, m - 1)], P[i], P[i + 1], P[np.clip(i + 2, 0, m - 1)]
    return .5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2 + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


def even(path, n, *extras):
    """The path resampled to n points evenly spaced along its length (and any per-point extras with it), which
    takes the kinks out of a spline through unevenly spaced keys."""
    path = np.asarray(path, np.float64)
    seg = np.r_[0.0, np.cumsum(norm(np.diff(path, axis=0), axis=1))]
    at = np.linspace(0, seg[-1], n)
    out = [np.stack([np.interp(at, seg, path[:, k]) for k in range(path.shape[1])], 1)]
    for e in extras:
        e = np.asarray(e, np.float64)
        out.append(np.interp(at, seg, e) if e.ndim == 1 else np.stack([np.interp(at, seg, e[:, k]) for k in range(e.shape[1])], 1))
    return out[0] if not extras else out


def curve(keys, n, radii=None, dense=6):
    """A smooth, evenly sampled path of n points through keys; with radii (one per key), also the radii along it."""
    m = max(n * dense, 60)
    path = spline(keys, m)
    if radii is None:
        return even(path, n)
    return even(path, n, spline(np.asarray(radii, np.float64)[:, None], m)[:, 0])


def cyl(keys, alpha=0.0, direction=1.0, centre=(0, 0, 0)):
    """Points given round the z axis as (radius, turns, z), starting at angle alpha: roots winding round a stem."""
    k = np.asarray(keys, np.float64)
    a = alpha + direction * k[:, 1] * TAU
    return np.stack([k[:, 0] * np.cos(a), k[:, 0] * np.sin(a), k[:, 2]], 1) + np.asarray(centre, np.float64)


def _carry(v, t0, t1):
    """v carried by the rotation that takes direction t0 to t1 (parallel transport of a tube's frame)."""
    axis = np.cross(t0, t1)
    s = norm(axis)
    if s < 1e-9:
        return v
    axis = axis / s
    ang = math.atan2(s, float(np.clip(np.dot(t0, t1), -1, 1)))
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * np.dot(axis, v) * (1 - math.cos(ang))


def frames(pts, closed=False):
    """Tangents and two normals carried along a polyline without twisting (so a tube never pinches)."""
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
    """A tube along a polyline. radius: one, one per point, or one per vertex (points x sides). colour: one, one per
    point, or one per vertex. closed joins the last ring to the first (a loop). Returns the first vertex index."""
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    tang, A, B = frames(pts, closed)
    ang = np.linspace(0, TAU, sides, endpoint=False)
    rad = np.asarray(radius, np.float64)
    rad = np.full((n, sides), float(rad)) if rad.ndim == 0 else (np.repeat(rad[:, None], sides, 1) if rad.ndim == 1 else rad)
    verts = pts[:, None, :] + rad[..., None] * (np.cos(ang)[None, :, None] * A[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :])
    faces = [[i * sides + j, i * sides + (j + 1) % sides, ((i + 1) % n) * sides + (j + 1) % sides, ((i + 1) % n) * sides + j]
             for i in range(n if closed else n - 1) for j in range(sides)]
    cols = np.asarray(colour, np.float64)
    if cols.ndim == 3:
        cols = cols.reshape(-1, cols.shape[-1])
    elif cols.ndim == 2 and len(cols) == n:
        cols = np.repeat(cols, sides, 0)
    start = part.add(verts.reshape(-1, 3), faces, cols, slot, smooth)
    if cap and not closed:
        ends = np.concatenate([verts[0], verts[-1]])
        end_cols = np.concatenate([cols[:sides], cols[-sides:]]) if cols.ndim == 2 else cols
        part.add(ends, [list(range(sides))[::-1], list(range(sides, 2 * sides))], end_cols, slot, False)
    return start


def ears(poly):
    """Triangles (index triples) of a simple polygon [(u, v), ...] wound counter-clockwise, by ear clipping."""
    pts = np.asarray(poly, np.float64)
    idx = list(range(len(pts)))
    out = []

    def turn_(o, a, b):
        return (pts[a][0] - pts[o][0]) * (pts[b][1] - pts[o][1]) - (pts[a][1] - pts[o][1]) * (pts[b][0] - pts[o][0])
    while len(idx) > 3:
        m = len(idx)
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            if turn_(i0, i1, i2) <= 1e-14:
                continue
            if any(j not in (i0, i1, i2) and turn_(i0, i1, j) >= -1e-14 and turn_(i1, i2, j) >= -1e-14 and turn_(i2, i0, j) >= -1e-14
                   for j in idx):
                continue
            out.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    return out + [(idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1)]


def sweep(part, profile, colour, slot=0, a0=0.0, a1=TAU, sides=None, rot=None, origin=(0, 0, 0), hard=True, bands=None):
    """Revolves a closed profile [(radius, z), ...] round local z from angle a0 to a1 (radians, from local x toward
    local y): a ring when the arc is whole, else an arc closed by flat ends (hoods, collars, shield segments). With
    hard, each profile segment is its own band, so machined corners stay crisp. bands {segment index: (colour, slot)}
    recolours single segments of a profile listed counter-clockwise in (radius, z), which puts every front outside."""
    prof = [tuple(map(float, q)) for q in profile]
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(prof, prof[1:] + prof[:1])) < 0:
        if bands:
            raise ValueError('sweep: a profile with bands must be listed counter-clockwise')
        prof = prof[::-1]
    full = a1 - a0 >= TAU - 1e-6
    n = sides or max(3, int(round(S(max(r for r, _ in prof)) * (a1 - a0) / TAU)))
    ang = a0 + np.linspace(0, a1 - a0, n, endpoint=False) if full else np.linspace(a0, a1, n + 1)
    m = len(ang)
    start = len(part.v)
    cs, sn = np.cos(ang), np.sin(ang)

    def ring_(q):
        return np.stack([cs * q[0], sn * q[0], np.full(m, q[1])], 1)
    span = m if full else m - 1
    loop = prof + prof[:1]
    if hard:
        for i, (a, b) in enumerate(zip(loop, loop[1:])):
            c, s = (bands or {}).get(i, (colour, slot))
            part.add(np.concatenate([ring_(a), ring_(b)]), [[j, (j + 1) % m, m + (j + 1) % m, m + j] for j in range(span)], c, s, True)
    else:
        k = len(prof)
        part.add(np.concatenate([ring_(q) for q in prof]),
                 [[i * m + j, i * m + (j + 1) % m, ((i + 1) % k) * m + (j + 1) % m, ((i + 1) % k) * m + j]
                  for i in range(k) for j in range(span)], colour, slot, True)
    if not full:
        tris = ears(prof)
        for a, flip in ((a0, False), (a1, True)):
            pts = np.array([(math.cos(a) * r, math.sin(a) * r, z) for r, z in prof])
            part.add(pts, [t[::-1] if flip else t for t in tris], colour, slot, False)
    place(part, start, rot, origin)
    return start


def hoop(part, centre, axis, big, small, colour, slot=0, sides=None, section=8, a0=0.0, a1=TAU, rot=None):
    """A torus of radius big and tube radius small round axis (or in the frame rot, for an arc's angles)."""
    t = np.linspace(0, TAU, section, endpoint=False)
    return sweep(part, [(big + small * math.cos(a), small * math.sin(a)) for a in t], colour, slot, a0, a1, sides or S(big),
                 along(axis) if rot is None else rot, centre, hard=False)


def turn(part, profile, colour, slot=0, sides=None, rot=None, origin=(0, 0, 0), smooth=True, caps=(True, True)):
    """Revolves an open profile [(radius, z), ...] round local z. List it counter-clockwise round the solid's section
    (up the outside: the front is on the right of the way it runs). An end on the axis (radius 0) closes as a pole;
    another is closed with a flat disc when its caps flag is set. colour: one, or one per profile point."""
    prof = [(float(r), float(z)) for r, z in profile]
    n = sides or S(max(r for r, _ in prof))
    ang = np.linspace(0, TAU, n, endpoint=False)
    cols = np.asarray(colour, np.float64)
    per_point = cols.ndim == 2
    verts, vcols, first, faces = [], [], [], []
    for i, (r, z) in enumerate(prof):
        first.append(len(verts))
        ring_ = [(0.0, 0.0, z)] if r <= 1e-9 else np.stack([np.cos(ang) * r, np.sin(ang) * r, np.full(n, z)], 1).tolist()
        verts.extend(ring_)
        vcols.extend([cols[i] if per_point else cols] * len(ring_))
    for i in range(len(prof) - 1):
        a, b = first[i], first[i + 1]
        lo_pole, hi_pole = prof[i][0] <= 1e-9, prof[i + 1][0] <= 1e-9
        for j in range(n):
            k = (j + 1) % n
            if lo_pole and hi_pole:
                continue
            if lo_pole:
                faces.append([a, b + k, b + j])
            elif hi_pole:
                faces.append([a + j, a + k, b])
            else:
                faces.append([a + j, a + k, b + k, b + j])
    start = part.add(verts, faces, np.asarray(vcols), slot, smooth)
    for end, flag, order in ((0, caps[0], -1), (len(prof) - 1, caps[1], 1)):
        if flag and prof[end][0] > 1e-9:
            c = cols[end] if per_point else cols
            part.add(verts[first[end]:first[end] + n], [list(range(n))[::order]], c, slot, False)
    place(part, start, rot, origin)
    return start


def ease(t):
    """Smoothstep of t clipped to 0..1."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def skin(part, grid, colour, slot, toward, smooth=True):
    """A surface over a point grid (nu x nv x 3), wound so that its front faces `toward` (a direction). colour: one,
    or one per grid point (nu x nv x 4)."""
    g = np.asarray(grid, np.float64)
    nu, nv = g.shape[:2]
    faces = [[u * nv + v, (u + 1) * nv + v, (u + 1) * nv + v + 1, u * nv + v + 1] for u in range(nu - 1) for v in range(nv - 1)]
    q = g.reshape(-1, 3)[faces[len(faces) // 2]]
    if np.dot(np.cross(q, np.roll(q, -1, 0)).sum(0), toward) < 0:
        faces = [f[::-1] for f in faces]
    cols = np.asarray(colour, np.float64)
    return part.add(g.reshape(-1, 3), faces, cols.reshape(-1, cols.shape[-1]) if cols.ndim == 3 else cols, slot, smooth)


def aim(axis, up=(0, 0, 1)):
    """Rotation taking local z to axis and local x as near to up as it can be."""
    z = unit(axis)
    u = np.asarray(up, np.float64) - z * np.dot(up, z)
    if norm(u) < 1e-6:
        u = np.cross(z, (0, 1.0, 0)) if abs(z[1]) < .9 else np.cross(z, (1.0, 0, 0))
    u = unit(u)
    return np.stack([u, np.cross(z, u), z], 1)


# ---------------------------------------------------------------- living root-wood

BARK_RUB = mix(BARK_BROWN, BARK_GREY, .3)      # the crest of a ridge: dry, rubbed, a little grey


def root(part, pts, radii, seed=0, sides=12, ridges=4, twist=1.0, ridge=.22, lump=.08, colour=BARK_RUB, dark=BARK_DARK,
         ground=1.0, wet=.55, moss=0.0, cap=True, slot=BARK):
    """A living root along a polyline: a fluted section of unequal lobes whose ridges and furrows wind along it
    (`twist` whole turns, the wood's own twist), swollen and pinched as roots are; furrows dark, crests rubbed
    lighter, shaded underneath and damp toward the ground (down to `wet` at z 0, clear at `ground` m). moss greens
    what faces the sky (vertex colour only). Returns the first vertex index."""
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    R = np.broadcast_to(np.asarray(radii, np.float64), (n,))
    seg = np.r_[0.0, np.cumsum(norm(np.diff(pts, axis=0), axis=1))]
    tang, A, B = frames(pts)
    ang = np.linspace(0, TAU, sides, endpoint=False)
    rm = max(float(R.mean()), 1e-6)
    if ridges and sides >= 8:
        phase = twist * TAU * seg / max(seg[-1], 1e-9) + seed * 1.7
        warp = .3 * np.sin(ang + seed * 2.3) + .16 * np.sin(2 * ang + seed * 1.1)       # lobes of unequal width
        f = np.abs(np.sin(ridges * (ang[None, :] + warp[None, :] + phase[:, None]) / 2)) ** .6   # 0 in a furrow, 1 on a crest
        depth = ridge * (1 + .35 * np.sin(ang[None, :] + phase[:, None] * .7 + seed))
    else:
        f, depth = np.full((n, sides), .55), 0.0
    along_ = seg[:, None] / (rm * 3.2)
    bump = noise2(np.cos(ang)[None, :] * 1.3 + along_, np.sin(ang)[None, :] * 1.3 + seed * .61, seed + 11)
    rad = R[:, None] * (1 - depth + depth * f) * (1 + lump * bump)
    dirs = np.cos(ang)[None, :, None] * A[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :]
    verts = pts[:, None, :] + rad[..., None] * dirs
    k = (1 - .34 * np.clip(-dirs[..., 2], 0, 1)) * (wet + (1 - wet) * np.clip(verts[..., 2] / max(ground, 1e-6), 0, 1))
    k = k * (.9 + .13 * noise2(ang[None, :] * 2.2 + seed, seg[:, None] / rm * .9, seed + 7))
    g = (f ** 1.3)[..., None]
    rgb = (np.asarray(dark, np.float64)[:3] * (1 - g) + np.asarray(colour, np.float64)[:3] * g) * k[..., None]
    if moss:
        m = moss * np.clip(dirs[..., 2], 0, 1) ** 1.5 * np.clip(.4 + 1.2 * noise2(verts[..., 0] * 9 + seed, verts[..., 1] * 9, seed + 5), 0, 1)
        rgb = rgb * (1 - m[..., None]) + np.asarray(MOSS_GREEN[:3]) * m[..., None]
    cols = rgba(np.minimum(rgb, .9)).reshape(-1, 4)
    faces = [[i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j]
             for i in range(n - 1) for j in range(sides)]
    start = part.add(verts.reshape(-1, 3), faces, cols, slot, True)
    if cap:
        part.add(np.concatenate([verts[0], verts[-1]]), [list(range(sides))[::-1], list(range(sides, 2 * sides))],
                 np.concatenate([cols[:sides], cols[-sides:]]), slot, False)
    return start


def wander(path, rng, amount, waves=3.0):
    """The path pushed sideways by a smooth random wobble of up to `amount` metres, its ends held."""
    path = np.asarray(path, np.float64)
    n = len(path)
    t = np.linspace(0, 1, n)
    hold = np.sin(np.pi * t) ** .5
    off = np.zeros_like(path)
    for axis in range(3):
        ph, fr = rng.uniform(0, TAU, 2), rng.uniform(.7, 1.3, 2) * waves
        off[:, axis] = np.sin(t * fr[0] * TAU + ph[0]) + .5 * np.sin(t * fr[1] * 2.3 * TAU + ph[1])
    return path + off * (amount / 1.5) * hold[:, None]


def strand(part, rng, keys, radii, alpha, n, seed, sides=12, direction=1.0, wobble=.012, centre=(0, 0, 0), **kw):
    """One root wound round a vertical axis: keys (radius, turns, z) from angle alpha, radii one per key. Returns its
    path and radii (path[0] is its first key)."""
    dense = cyl(spline(keys, 260), alpha, direction, centre)
    path, rad = even(dense, n, spline(np.asarray(radii, np.float64)[:, None], 260)[:, 0])
    if wobble:
        path = wander(path, rng, wobble, 4.0)
    root(part, path, rad, seed, sides, **kw)
    return path, rad


def rootlets(part, rng, starts, dirs, length, radius, sag=.5, sides=5, fork=.4, ground=None, colour=None, limit=None):
    """Hair roots: thin tapering strands leaving `starts` along `dirs`, curling and sagging (sag 1 hangs straight
    down by the end); some fork. ground (a z) keeps them on the soil they creep over, limit within that radius of
    the z axis."""
    colour = tone(BARK_BROWN, .8) if colour is None else colour
    starts, dirs = np.atleast_2d(np.asarray(starts, np.float64)), np.atleast_2d(np.asarray(dirs, np.float64))

    def one(a, d, L, r, n_sides):
        side = unit(np.cross(d, UP) + rng.normal(0, .3, 3)) * rng.choice((-1.0, 1.0))
        keys = np.array([a, a + d * L * .35 + side * L * .14 - UP * L * sag * .08, a + d * L * .7 - side * L * .1 - UP * L * sag * .42,
                         a + d * L + side * L * .08 - UP * L * sag])
        path = curve(keys, 8)
        if ground is not None:
            path[:, 2] = np.maximum(path[:, 2], ground)
        if limit is not None:
            path[:, :2] *= np.minimum(1.0, (limit - r) / np.maximum(norm(path[:, :2], axis=1), 1e-9))[:, None]
        root(part, path, np.linspace(r, r * .1, 8), int(rng.integers(1000)), n_sides, 0, colour=colour, dark=colour, ground=.6)
        return path
    for a, d in zip(starts, dirs):
        L, r = length * rng.uniform(.6, 1.2), radius * rng.uniform(.7, 1.1)
        d = unit(d + rng.normal(0, .25, 3))
        path = one(a, d, L, r, sides)
        if rng.uniform() < fork:
            one(path[4], unit(unit(path[5] - path[3]) + rng.normal(0, .6, 3)), L * .45, r * .5, max(4, sides - 1))


def toes(part, rng, path, rad, limit, seed=0, hair=2, ground=-.03, moss=.2):
    """Where a root creeps over the soil (path[0] is its tip): a side root forks off it and hair rootlets leave it, all
    sinking into the ground and none reaching beyond `limit` from the axis."""
    low = np.nonzero(path[:, 2] < .1)[0]
    if len(low) < 5:
        return
    i = int(low[int(len(low) * rng.uniform(.45, .75))])
    out = unit(V(path[0][0] - path[i][0], path[0][1] - path[i][1], 0))
    side = np.cross(UP, out) * (1.0 if seed % 2 else -1.0)
    L = norm(path[0] - path[i]) * rng.uniform(.85, 1.1) + .06
    d = unit(out * .78 + side * .62)
    keys = np.array([path[i], path[i] + d * L * .3 + side * L * .06, path[i] + d * L * .66 - side * L * .07, path[i] + d * L])
    keys[1:, 2] = [max(path[i][2] * .5, 0.0), -.004, ground]
    sub, r = curve(keys, 12, [rad[i] * .6, rad[i] * .5, rad[i] * .33, rad[i] * .12])
    rho = np.maximum(norm(sub[:, :2], axis=1), 1e-9)
    sub[:, :2] *= np.minimum(1.0, (limit - r) / rho)[:, None]
    root(part, sub, r, seed * 7 + 3, 8, 2, .8, .2, ground=.9, moss=moss)
    for _ in range(hair):
        j = int(low[int(len(low) * rng.uniform(.1, .95))])
        o = unit(V(path[j][0], path[j][1], 0))
        s = np.cross(UP, o) * rng.choice((-1.0, 1.0))
        rootlets(part, rng, [path[j] - (0, 0, rad[j] * .5)], [unit(o * .4 + s)], rng.uniform(.08, .16), rad[j] * .3, .1, 5, ground=ground,
                 limit=limit)


def knot(part, centre, normal, r, seed=0, colour=BARK_RUB, dark=BARK_DARK):
    """A burl knot: the callus ring a root grows round a lost side shoot, with its dark eye."""
    rng = np.random.default_rng(1000 + seed)
    prof = [(r * 1.05, -r * .15), (r * .98, r * .16), (r * .78, r * .36), (r * .52, r * .42), (r * .34, r * .3), (r * .2, r * .12), (0, r * .04)]
    cols = [tone(colour, .8), tone(colour, .95), tone(colour, 1.1), tone(colour, 1.0), tone(dark, 1.2), tone(dark, .8), tone(dark, .6)]
    start = turn(part, prof, np.array(cols), BARK, max(8, S(r, 8, 16)), caps=(False, False))
    v = np.asarray(part.v[start:], np.float64)
    a = np.arctan2(v[:, 1], v[:, 0])
    v[:, :2] *= (1 + .16 * np.sin(a * 2 + rng.uniform(0, TAU)) + .1 * np.sin(a * 3 + rng.uniform(0, TAU)))[:, None]
    part.v[start:] = v.tolist()
    place(part, start, along(normal), centre)
    return start


def reaches(count, R, rng, offset=.25):
    """Ground angles and reaches for `count` roots round a prop of footprint radius R: the four nearest the axes reach
    the square of half-size R (so the footprint is the contract's and is centred), the others fall a little short."""
    alpha = (np.arange(count) + offset) / count * TAU
    reach = R * rng.uniform(.8, .95, count)
    for a in (0.0, .5 * math.pi, math.pi, 1.5 * math.pi):
        d = np.cos(alpha - a)
        k = int(np.argmax(d))
        reach[k] = R / d[k]
    return alpha, reach


def rope(part, centre, strands, spread, turns, radius, seed=0, sides=8, ridges=2, phase=0.0, **kw):
    """Roots twisted into a rope round a centre line: `strands` of them, each `spread` from the line, winding `turns`
    whole turns along it. radius: one, or one per point."""
    centre = np.asarray(centre, np.float64)
    tang, A, B = frames(centre)
    seg = np.r_[0.0, np.cumsum(norm(np.diff(centre, axis=0), axis=1))]
    frac = seg / max(seg[-1], 1e-9)
    spread = np.broadcast_to(np.asarray(spread, np.float64), (len(centre),))
    for j in range(strands):
        a = phase + j / strands * TAU + turns * TAU * frac
        path = centre + spread[:, None] * (np.cos(a)[:, None] * A + np.sin(a)[:, None] * B)
        root(part, path, radius, seed + j, sides, ridges, **kw)


def moss_clump(part, rng, centre, r, flat=.4):
    """A cushion of moss (the MOSS slot)."""
    blob(part, centre, r, vary(rng, mix(MOSS_GREEN, MOSS_DEEP, rng.uniform(0, .6)), .15), MOSS, 1, .3, int(rng.integers(1000000)),
         (1, rng.uniform(.7, 1.1), flat))

# ---------------------------------------------------------------- the link props (the grove's own: root-wood and light)

def _seed(part, centre, r, h, colour, bright=1.0, sides=24):
    """A resonance seed: a pointed, almond-shaped light, brightest round its waist."""
    prof = [(0, -h * .92), (r * .42, -h * .78), (r * .8, -h * .45), (r, -h * .05), (r * .93, h * .35), (r * .62, h * .72),
            (r * .27, h * .93), (0, h * 1.04)]
    k = [.72, .8, .92, 1.0, .97, .88, .78, .7]
    return turn(part, prof, np.array([glow(colour, bright * q) for q in k]), GLOW, sides, origin=centre)


def _core(part, kind, centre, r, colour, bright=1.0):
    """A flow's core. Its shape tells the flows apart as its colour does: water a drop, power a cut crystal, the surge
    (resonance itself) a seed like a link node's."""
    c = np.asarray(centre, np.float64)
    if kind == 0:
        prof = [(0, -r), (r * .5, -r * .87), (r * .87, -r * .5), (r, 0), (r * .9, r * .42), (r * .62, r * .82), (r * .3, r * 1.16), (0, r * 1.46)]
        k = [.75, .82, .92, 1.0, .97, .9, .8, .72]
        turn(part, prof, np.array([glow(colour, bright * q) for q in k]), GLOW, S(r, 16, 32), origin=c - (0, 0, r * .12))
    elif kind == 1:
        prof = [(0, -r * 1.3), (r * .94, -r * .3), (r * .94, r * .3), (0, r * 1.3)]
        turn(part, prof, np.array([glow(colour, bright * q) for q in (.7, 1.0, 1.0, .7)]), GLOW, 6, origin=c, smooth=False)
    else:
        _seed(part, c, r * .86, r * 1.28, colour, bright, S(r, 16, 32))


def _veins(part, keys, alphas, colour, bright, r=.008, direction=1.0, n=22):
    """Resonance running in the furrows between a stem's roots: thin lit threads, brightest at the top (keys run down)."""
    for a in alphas:
        path = even(cyl(spline(keys, 120), a, direction), n)
        pipe(part, path, np.linspace(r, r * .4, n), np.array([glow(colour, q) for q in np.linspace(bright, bright * .25, n)]), GLOW, 5, cap=False)


@built(.022)
def link_node():
    """A link anchor (radius 0.5, 1.3 tall): six roots creep in over the soil, wind into one stem, are tied by a
    seventh in a knot, and open into fingers that hold a resonance seed at (0, 0, 1.0)."""
    rng = np.random.default_rng(411)
    p = Part('SM_GN_LinkNode', (BARK, GLOW))
    count = 6
    alpha, reach = reaches(count, .5, rng)
    radii = [.012, .03, .043, .052, .057, .058, .056, .052, .046, .04, .034, .026, .017, .007]
    for k in range(count):
        top = 1.3 if k == 1 else rng.uniform(1.15, 1.27)
        lean = rng.uniform(-.04, .04)
        keys = [(reach[k], -.02 + lean, -.03), (reach[k] * .8, lean, .012), (reach[k] * .56, .03 + lean * .6, .035), (.17, .09, .12),
                (.105, .17, .26), (.086, .31, .42), (.085, .5, .58), (.09, .68, .72), (.128, .79, .84), (.19, .86, .95),
                (.215, .9, 1.05), (.2, .93, top - .13), (.15, .96, top - .04), (.11, .975, top)]
        path, rad = strand(p, rng, keys, np.array(radii) * rng.uniform(.92, 1.08), alpha[k], 46, k, 12, ridges=3, twist=1.6, ridge=.24,
                           lump=.1, ground=.9, moss=.25)
        toes(p, rng, path, rad, .5, k)
    # a dark heart inside the stem, so no gap between the roots shows the far side
    pipe(p, [(0, 0, .12), (0, 0, .5), (0, 0, .86)], [.11, .075, .085], tone(BARK_DARK, .5), BARK, 10)
    # the knot: a seventh root wound once and a quarter round the stem, its ends tucked under
    turns = np.linspace(-.12, 1.2, 40)
    tie = cyl(np.stack([.142 + .012 * np.sin(turns * 9), turns, .64 + .05 * turns + .014 * np.sin(turns * 5)], 1), .9)
    tie[:3] = cyl([(.2, -.2, .52), (.17, -.16, .58), (.15, -.14, .62)], .9)
    root(p, tie, np.r_[np.linspace(.012, .034, 4), np.full(31, .036), np.linspace(.034, .012, 5)], seed=17, sides=10, ridges=3,
         twist=3.0, ridge=.22, ground=.9)
    for a, z, r in ((2.3, .5, .034), (4.6, .36, .03), (.4, .3, .026)):
        d = V(math.cos(a), math.sin(a), 0)
        knot(p, d * .135 + (0, 0, z), d + (0, 0, .15), r, int(a * 10))
    # the calyx: short tongues of root that clasp the seed's foot
    for k in range(5):
        keys = [(.03, 0, .8), (.06, .02, .84), (.094, .04, .9), (.112, .06, .97), (.108, .08, 1.03)]
        root(p, even(cyl(spline(keys, 40), (k + .5) / 5 * TAU), 10), np.linspace(.024, .005, 10), seed=30 + k, sides=6, ridges=0, ground=.9)
    pipe(p, [(0, 0, .78), (0, 0, .86)], [.06, .05], tone(BARK_DARK, .7), BARK, 10)
    _seed(p, (0, 0, 1.0), .105, .16, GLOW_LINK)
    mark(p, 'core', (0, 0, 1.0))
    _veins(p, [(.1, .87, .9), (.104, .74, .78), (.103, .55, .62), (.103, .36, .46), (.108, .24, .34), (.11, .17, .26)],
           [(2 * k + .75) / count * TAU for k in range(3)], GLOW_LINK, .5)
    return p


@built(.03)
def link_source(kind):
    """A flow source (radius 0.8, 1.8 tall): eight roots wound into a stem that opens into a chalice, woven round its
    foot, with the flow's bright core standing open in it at (0, 0, 1.36). Water's fingers spill outward, power's stand
    straight, the surge's curl in."""
    name, colour = FLOWS[kind]
    rng = np.random.default_rng(420 + kind)
    p = Part('SM_GN_LinkSource' + name, (BARK, GLOW))
    count = 8
    direction = (1.0, -1.0, 1.0)[kind]
    alpha, reach = reaches(count, .8, rng)
    radii = [.015, .042, .06, .07, .074, .074, .072, .07, .064, .056, .05, .042, .032, .02, .008]
    core = V(0, 0, 1.36)
    tips = ((.05, .12, .17), (0.0, -.02, -.04), (.02, -.05, -.16))[kind]      # how the last three keys leave the rim
    fingers = []
    for k in range(count):
        top = 1.8 if k == 2 else rng.uniform(1.58, 1.77)
        lean = rng.uniform(-.03, .03)
        rim = rng.uniform(.5, .57)
        keys = [(reach[k], lean, -.03), (reach[k] * .78, lean + .01, .015), (reach[k] * .54, lean * .6 + .035, .05), (.27, .09, .17),
                (.17, .16, .35), (.13, .28, .53), (.125, .42, .7), (.135, .55, .86), (.2, .63, .98), (.33, .69, 1.08), (.46, .73, 1.2),
                (rim, .76, 1.36), (rim + tips[0], .78, top - .27), (rim + tips[1], .8, top - .11), (rim + tips[2], .81, top)]
        path, rad = strand(p, rng, keys, np.array(radii) * rng.uniform(.92, 1.08), alpha[k], 54, k, 12, direction,
                           wobble=(.03, .008, .018)[kind], ridges=3, twist=1.8, ridge=.24, lump=.1, ground=1.0, moss=.25)
        toes(p, rng, path, rad, .8, k)
        fingers.append(path)
    pipe(p, [(0, 0, .15), (0, 0, .5), (0, 0, .9)], [.16, .11, .12], tone(BARK_DARK, .5), BARK, 12)
    # the bowl: a dark lining, and three thin roots woven in and out of the fingers round its foot
    lining = [(0, .9), (.13, .93), (.25, 1.0), (.37, 1.1), (.455, 1.22), (.47, 1.25), (.44, 1.24), (.35, 1.13), (.23, 1.03), (.11, .97), (0, .95)]
    start = turn(p, lining, tone(BARK_DARK, .75), BARK, 32)
    v = np.asarray(p.v[start:], np.float64)
    a = np.arctan2(v[:, 1], v[:, 0])
    v[:, :2] *= (1 + .035 * np.sin(a * count + v[:, 2] * 9) + .03 * noise2(a * 3, v[:, 2] * 8, 5))[:, None]
    p.v[start:] = v.tolist()
    for i, (z, rho) in enumerate(((1.03, .27), (1.14, .4), (1.27, .505))):
        at = [f[int(np.argmin(np.abs(f[:, 2] - z)))] for f in fingers]
        ang0 = math.atan2(at[0][1], at[0][0])
        th = np.linspace(0, TAU * 1.04, 72)
        wave = np.cos(count / 2 * th + (math.pi if i % 2 else 0.0))
        loop = np.stack([(rho + .062 * wave) * np.cos(ang0 + th), (rho + .062 * wave) * np.sin(ang0 + th),
                         z + .012 * np.sin(th * 3 + i)], 1)
        root(p, loop, np.r_[.012, np.full(70, .021), .012], seed=40 + i, sides=8, ridges=2, twist=7.0, ridge=.2, ground=1.0)
    for a, z, r in ((2.1, .62, .045), (4.4, .45, .04), (.5, .36, .034), (5.6, .74, .036)):
        d = V(math.cos(a), math.sin(a), 0)
        knot(p, d * .19 + (0, 0, z), d + (0, 0, .15), r, int(a * 10))
    for k in range(5):
        keys = [(.04, 0, .96), (.1, .02, 1.02), (.17, .04, 1.1), (.215, .06, 1.2), (.21, .08, 1.3)]
        root(p, even(cyl(spline(keys, 40), (k + .5) / 5 * TAU, direction), 10), np.linspace(.03, .006, 10), seed=30 + k, sides=6, ridges=0, ground=1.0)
    _core(p, kind, core, .23, colour)
    mark(p, 'core', core)
    _veins(p, [(.135, .6, .92), (.142, .5, .8), (.14, .38, .65), (.143, .26, .5), (.16, .17, .36)],
           [(2 * k + .75) / count * TAU for k in range(4)], colour, .5, .011, direction)
    return p


def _brass(rng, k=1.0):
    """Old brass: dulled, verdigris starting in it."""
    return tone(mix(tone(BRASS_WARM, .7), VERDIGRIS, rng.uniform(.05, .3)), k)


@built(.028)
def link_receiver(kind):
    """A socket waiting for a flow (radius 0.7, 1.6 tall): six roots open into a cradle round the Just's brass fitting,
    a hoop the roots have grown through and a dish on a stem, with the flow's core, dim, at (0, 0, 1.06)."""
    name, colour = FLOWS[kind]
    rng = np.random.default_rng(430 + kind)
    p = Part('SM_GN_LinkReceiver' + name, (BARK, BRASS, GLOW))
    count = 6
    alpha, reach = reaches(count, .7, rng)
    radii = [.014, .038, .055, .064, .068, .068, .066, .06, .054, .048, .042, .034, .024, .009]
    core = V(0, 0, 1.06)
    for k in range(count):
        top = 1.6 if k == 4 else rng.uniform(1.44, 1.58)
        lean = rng.uniform(-.03, .03)
        keys = [(reach[k], lean, -.03), (reach[k] * .78, lean + .01, .015), (reach[k] * .54, lean * .6 + .03, .045), (.24, .08, .15),
                (.15, .14, .3), (.115, .24, .45), (.115, .34, .6), (.2, .4, .72), (.34, .44, .84), (.43, .47, 1.0), (.45, .49, 1.16),
                (.41, .51, top - .24), (.33, .53, top - .1), (.27, .54, top)]
        path, rad = strand(p, rng, keys, np.array(radii) * rng.uniform(.92, 1.08), alpha[k], 50, k, 12, ridges=3, twist=1.6, ridge=.24,
                           lump=.1, ground=1.0, moss=.25)
        toes(p, rng, path, rad, .7, k)
        # the ferrule the root has grown through, lugged to the hoop
        i = int(np.argmin(np.abs(path[:, 2] - 1.06)))
        t = unit(path[i + 1] - path[i - 1])
        hoop(p, path[i], t, rad[i] * 1.08, .013, _brass(rng), BRASS, 16, 6)
        inward = unit(V(-path[i][0], -path[i][1], 0))
        obox(p, path[i] + inward * (rad[i] + .02), (.03, .022, .016), _brass(rng, .9), BRASS, .005, basis(inward))
    pipe(p, [(0, 0, .12), (0, 0, .4), (0, 0, .66)], [.14, .1, .1], tone(BARK_DARK, .5), BARK, 12)
    # the brass: hoop, dish, stem and prongs
    sweep(p, [(.335, 1.02), (.378, 1.02), (.386, 1.03), (.386, 1.09), (.378, 1.1), (.335, 1.1), (.343, 1.06)], _brass(rng), BRASS, sides=40)
    ang = np.arange(12) / 12 * TAU
    fl.rivets(p, np.stack([.386 * np.cos(ang), .386 * np.sin(ang), np.full(12, 1.06)], 1), np.stack([np.cos(ang), np.sin(ang), np.zeros(12)], 1),
              .008, _brass(rng, 1.2), BRASS)
    turn(p, [(0, .845), (.07, .85), (.15, .875), (.205, .925), (.214, .94), (.196, .936), (.14, .896), (.065, .872), (0, .868)], _brass(rng), BRASS, 28)
    pipe(p, [(0, 0, .6), (0, 0, .86)], .028, _brass(rng, .9), BRASS, 12)
    for z in (.66, .8):
        sweep(p, [(.028, z), (.042, z + .004), (.042, z + .022), (.028, z + .026)], _brass(rng, 1.1), BRASS, sides=14)
    for k in range(3):
        a = (k + .25) / 3 * TAU
        d = V(math.cos(a), math.sin(a), 0)
        prong = curve([d * .2 + (0, 0, .93), d * .215 + (0, 0, 1.0), d * .2 + (0, 0, 1.07), d * .168 + (0, 0, 1.1)], 8)
        pipe(p, prong, np.linspace(.012, .008, 8), _brass(rng), BRASS, 6)
        strut(p, d * .21 + (0, 0, .94), d * .34 + (0, 0, 1.04), .022, .012, _brass(rng, .85), BRASS, bevel=.003)
    for a, z, r in ((2.4, .42, .04), (4.9, .3, .034), (.8, .5, .032)):
        d = V(math.cos(a), math.sin(a), 0)
        knot(p, d * .165 + (0, 0, z), d + (0, 0, .15), r, int(a * 10))
    _core(p, kind, core, .165, colour, DIM)
    mark(p, 'core', core)
    return p


def _lens(part, kind, centre, r, t, colour, bright):
    """A relay's lens, facing along x: round for water, six-sided for power, a pointed oval for the surge."""
    prof = [(0, -t), (r * .5, -t * .86), (r * .86, -t * .5), (r, 0), (r * .86, t * .5), (r * .5, t * .86), (0, t)]
    cols = np.array([glow(colour, bright * q) for q in (1.0, .95, .85, .7, .85, .95, 1.0)])
    start = turn(part, prof, cols, GLOW, 6 if kind == 1 else S(r, 20, 32), smooth=kind != 1)
    if kind == 2:
        v = np.asarray(part.v[start:], np.float64)
        v[:, 1] *= .84 * (1 - .42 * (np.abs(v[:, 0]) / r) ** 2)     # local x becomes world z: drawn to a point above and below
        v[:, 0] *= 1.2
        part.v[start:] = v.tolist()
    place(part, start, np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]]), centre)   # local z to world x, local x to world -z
    return start


@built(.022)
def link_relay(kind):
    """A relay (radius 0.45, 1.4 tall): four roots wind up a stem and part into two ropes that stand as an eye, cross
    above it like a tied knot and end in two horns; the eye holds a dim lens of the flow's colour at (0, 0, 1.02),
    facing along x."""
    name, colour = FLOWS[kind]
    rng = np.random.default_rng(440 + kind)
    p = Part('SM_GN_LinkRelay' + name, (BARK, GLOW))
    alpha, reach = reaches(4, .45, rng, .12)
    eye, big = V(0, 0, 1.02), .27
    radii = [.012, .032, .046, .052, .054, .054, .052] + [.05] * 7 + [.046, .04, .028, .009]
    for k in range(4):
        g = -1.0 if k < 2 else 1.0                 # which side of the eye this root takes (where its turn up the stem leaves it)
        j = k % 2                                  # its place in that side's rope of two
        lean = rng.uniform(-.03, .03)
        foot = cyl([(reach[k], lean, -.03), (reach[k] * .76, lean + .01, .014), (reach[k] * .5, lean * .6 + .04, .045), (.16, .12, .14),
                    (.085, .26, .3), (.07, .46, .46), (.065, .62, .6)], alpha[k])
        ring_ = []
        for psi in np.linspace(-1.25, 1.95, 9):
            tw = 2.4 * (psi + 1.25) + j * math.pi
            out = V(0, g * math.cos(psi), math.sin(psi))
            c = eye + out * big
            if psi > 1.5:                           # past the crossing: the horn rises on the far side
                c = eye + V(0, g * math.cos(psi) * big * 1.15, big * (1.0 + .34 * (psi - 1.5)))
            ring_.append(c + (V(1.0, 0, 0) * math.cos(tw) + out * math.sin(tw)) * .03 + V(.034 * g, 0, 0) * max(0.0, math.sin(psi)) ** 3)
        top = 1.4 if k == 0 else rng.uniform(1.3, 1.38)
        horn = [ring_[-1] + V(.0, -g * .03, .05), V(ring_[-1][0] * .5, -g * rng.uniform(.14, .2), top)]
        path, rad = curve(np.concatenate([foot, ring_, horn]), 60, radii)
        path = wander(path, rng, .008, 5.0)
        root(p, path, rad * rng.uniform(.93, 1.05), k, 12, 3, 2.2, .24, .1, ground=.9, moss=.2)
        toes(p, rng, path, rad, .45, k, hair=1)
    pipe(p, [(0, 0, .1), (0, 0, .4), (0, 0, .7)], [.09, .06, .05], tone(BARK_DARK, .5), BARK, 10)
    # a tie round the stem under the eye
    turns = np.linspace(-.1, 1.15, 34)
    tie = cyl(np.stack([.118 + .008 * np.sin(turns * 9), turns, .52 + .04 * turns], 1), 2.2)
    root(p, tie, np.r_[np.linspace(.01, .026, 4), np.full(26, .028), np.linspace(.026, .01, 4)], seed=19, sides=8, ridges=2, twist=3.0,
         ground=.9)
    knot(p, (.1, -.04, .34), (1, -.4, .2), .03, 3)
    knot(p, (-.09, .06, .44), (-1, .5, .2), .026, 5)
    # the lens, held in the eye by tendrils from the ropes
    _lens(p, kind, eye, .165, .05, colour, DIM)
    mark(p, 'core', eye)
    for k in range(6):
        a = (k + .5) / 6 * TAU
        d = V(0, math.cos(a), math.sin(a))
        s = np.cross(d, (1.0, 0, 0))
        hold = curve([eye + d * (big - .03), eye + d * (big - .08) + s * .02, eye + d * .2 - s * .012, eye + d * .158], 7)
        root(p, hold, np.linspace(.013, .005, 7), 50 + k, 5, 0, ground=.9)
    return p

# ---------------------------------------------------------------- the root bridge

BRIDGE_LENGTH, BRIDGE_WIDTH, BRIDGE_CROWN = 20.0, 3.0, .5


@built(.05)
def root_bridge():
    """A bridge of living roots along x (20 x 4 x 3 m). Its pivot is the deck's top centre: the deck is one unbroken
    strip, x -10..10 and y -1.5..1.5, whose top is z 0 at both ends and rises smoothly (sin squared) to its crown at
    mid-span, never above +0.5. The strip is nine roots grown side to side: rounded crests 1.5 to 4 cm above shallow
    creases, no hole or step anywhere. Under it run two ropes of three roots and a keel root that plunge into the banks
    at both ends, lashed to it by ties; beside it stand railings, a rope of two roots on posts with crossed stays,
    0.75 m above the deck at mid-span and sinking to the ground at the ends."""
    rng = np.random.default_rng(451)
    p = Part('SM_GN_RootBridge', (BARK, MOSS))
    L, W = BRIDGE_LENGTH, BRIDGE_WIDTH
    nx, lobes = 101, 9
    x = np.linspace(-L / 2, L / 2, nx)
    s = (x + L / 2) / L
    fade = ease((L / 2 - np.abs(x)) / .8)
    w = rng.uniform(.75, 1.3, lobes)[None, :] * (1 + .27 * np.sin(x[:, None] * rng.uniform(.25, .6, lobes)[None, :] + rng.uniform(0, TAU, lobes)[None, :])
                                                + .13 * np.sin(x[:, None] * rng.uniform(.9, 1.5, lobes)[None, :] + rng.uniform(0, TAU, lobes)[None, :]))
    w = w / w.sum(1, keepdims=True) * W
    crease = np.concatenate([np.full((nx, 1), -W / 2), -W / 2 + np.cumsum(w, 1)], 1)
    crease[:, -1] = W / 2
    crest = (.031 + .014 * np.sin(x[:, None] * rng.uniform(.5, 1.1, lobes)[None, :] + rng.uniform(0, TAU, lobes)[None, :])) * fade[:, None]
    H = BRIDGE_CROWN - float(crest.max())
    arc = H * np.sin(np.pi * s) ** 2

    def deck(xs):
        return H * np.sin(np.pi * (np.asarray(xs, np.float64) + L / 2) / L) ** 2
    # ---- the deck's top: four columns to a root (crease, shoulder, crest, shoulder), so creases stay crisp
    hump = np.array([0.0, .82, 1.0, .82])
    ny = lobes * 4 + 1
    Y, Z, F = np.zeros((nx, ny)), np.zeros((nx, ny)), np.zeros((nx, ny))
    for k in range(lobes):
        for j in range(4):
            Y[:, k * 4 + j] = crease[:, k] + (crease[:, k + 1] - crease[:, k]) * j / 4
            Z[:, k * 4 + j] = arc + crest[:, k] * hump[j]
            F[:, k * 4 + j] = hump[j]
    Y[:, -1], Z[:, -1] = W / 2, arc
    X = np.repeat(x[:, None], ny, 1)
    g = F[..., None] ** 1.2
    worn = (np.exp(-(Y / .8) ** 2) * F * .45)[..., None]                 # the trodden middle, on the crests
    mossy = ((1 - F) * np.clip((np.abs(Y) - .55) / .8, 0, 1) * np.clip(.5 + noise2(X * 1.3, Y * 4, 3), 0, 1) * .7)[..., None]
    rgb = np.asarray(BARK_DARK[:3]) * (1 - g) + np.asarray(BARK_RUB[:3]) * g
    rgb = rgb * (1 - worn) + np.asarray(WOOD_OLD[:3]) * 1.1 * worn
    rgb = rgb * (1 - mossy) + np.asarray(MOSS_DEEP[:3]) * mossy
    skin(p, np.stack([X, Y, Z], -1), rgba(rgb * (.88 + .14 * noise2(X * 2.1, Y * 6, 9))[..., None]), BARK, (0, 0, 1))
    mark(p, 'deck_crown', (0.0, 0.0, float(Z.max())))
    mark(p, 'deck_min', (-L / 2, -W / 2, 0.0))
    mark(p, 'deck_max', (L / 2, W / 2, float(Z.max())))
    # ---- its flanks and belly (every second station): the same nine roots seen from below
    xb, ab, cb = x[::2], arc[::2], crease[::2]
    thick = .27 + .07 * np.sin(xb[:, None] * rng.uniform(.3, .8, lobes)[None, :] + rng.uniform(0, TAU, lobes)[None, :])
    rows, shade_ = [], []
    for i in range(len(xb)):
        loop = [(W / 2, 0.0, .8), (W / 2 + .05, -.09, .75), (W / 2 + .01, -.2, .6)]
        for k in range(lobes - 1, -1, -1):
            loop.append(((cb[i, k] + cb[i, k + 1]) / 2, -thick[i, k], .62))
            if k:
                loop.append((cb[i, k], -.17, .34))
        loop += [(-W / 2 - .01, -.2, .6), (-W / 2 - .05, -.09, .75), (-W / 2, 0.0, .8)]
        rows.append([(xb[i], y, ab[i] + dz) for y, dz, _ in loop])
        shade_.append([q for _, _, q in loop])
    belly, shade_ = np.array(rows), np.array(shade_)
    skin(p, belly, rgba(np.asarray(BARK_RUB[:3]) * (shade_ * (.85 + .2 * noise2(belly[..., 0] * 1.7, belly[..., 1] * 3, 4)))[..., None]),
         BARK, (0, 0, -1))
    for i, sign in ((0, -1), (-1, 1)):
        tris = ears(np.stack([-belly[i][:, 1], belly[i][:, 2]], 1))
        p.add(belly[i], [t if sign < 0 else t[::-1] for t in tris], tone(BARK_DARK, .6), BARK, False)
    # ---- what carries it: two ropes and a keel, plunging into the banks
    low = -1.5

    def line(y0, drop, sag, splay, n=80, wave=.05, ph=0.0):
        xs = np.linspace(-9.88, 9.88, n)
        e = ease((np.abs(xs) - 7.4) / 2.4) ** 2
        z = (deck(xs) - drop - sag * np.sin(np.pi * (xs + L / 2) / L)) * (1 - e) + low * e
        return np.stack([xs, y0 * (1 + splay * e) + wave * np.sin(xs * .9 + ph) * (1 - e), z], 1)
    under = dict(colour=tone(BARK_RUB, .82), dark=tone(BARK_DARK, .8), wet=1.0)
    carriers = []
    for side in (-1, 1):
        centre = line(side * .95, .52, .14, .45, ph=side * 1.3)
        carriers.append(centre)
        rope(p, centre, 3, .13, 8.5 * side, np.r_[.07, np.full(78, .118), .07], 60 + 5 * side, 8, 2, twist=5.0, ridge=.2, **under)
    keel = line(0.0, .66, .1, 0.0, wave=.09, ph=.4)
    root(p, keel, np.r_[.1, np.full(78, .19), .1] * (1 + .12 * np.sin(np.linspace(0, 40, 80))), 71, 12, 4, 6.0, .24, **under)
    for k, xt in enumerate(np.arange(-7.0, 7.1, 2.0)):
        a = float(deck(xt))
        wob = rng.uniform(-.12, .12, 7)
        keys = [(xt + wob[0], -1.6, a + .04), (xt + wob[1], -1.54, a - .42), (xt + wob[2], -.95, a - .86), (xt + wob[3], 0, a - .93),
                (xt + wob[4], .95, a - .86), (xt + wob[5], 1.54, a - .42), (xt + wob[6], 1.6, a + .04)]
        root(p, curve(keys, 24), np.r_[.03, np.full(22, .05), .03], 80 + k, 8, 2, 3.0, .2, **under)
    hang = [carriers[int(rng.integers(2))][int(rng.integers(22, 58))] + V(rng.uniform(-.2, .2), rng.uniform(-.1, .1), -.2) for _ in range(16)]
    rootlets(p, rng, hang, np.tile(V(0, 0, -1.0), (16, 1)), .75, .022, .25, 5, fork=.5)
    # ---- the railings: a rope on posts, crossed stays between them
    def rail_at(xs, side):
        xs = np.asarray(xs, np.float64)
        return np.stack([xs, side * (1.78 + .04 * np.sin(xs * .7 + side)),
                         deck(xs) + .06 + .72 * ease((L / 2 - .1 - np.abs(xs)) / 2.6) + .03 * np.sin(xs * 1.3 + side * 2)], -1)
    wood = dict(wet=1.0, moss=.3)
    posts = np.arange(-8.0, 8.1, 2.0)
    for side in (-1, 1):
        rope(p, rail_at(np.linspace(-9.9, 9.9, 70), side), 2, .06, 12.0 * side, np.r_[.03, np.full(68, .066), .03], 90 + side, 7, 2,
             twist=4.0, ridge=.2, **wood)
        feet, heads = [], []
        for k, xp in enumerate(posts):
            a, lean = float(deck(xp)), rng.uniform(-.12, .12)
            head = rail_at(xp + lean, side)
            foot = V(xp, side * 1.63, a - .1)
            keys = [(xp - lean * .5, side * 1.36, a - .34), foot, (xp + lean * .3, side * 1.74, a + (head[2] - a) * .45), head - (0, 0, .03)]
            root(p, curve(keys, 12), np.linspace(.08, .05, 12), 100 + 10 * k + side, 8, 2, 1.5, .22, **wood)
            turns = np.linspace(0, 1.3, 10)
            wrap = head + np.stack([.16 * (turns - .65), .13 * np.cos(turns * TAU + 1.0), .13 * np.sin(turns * TAU + 1.0)], 1)
            root(p, wrap, np.linspace(.034, .012, 10), 200 + k, 5, 0, **wood)
            feet.append(foot + V(0, side * .06, .12))
            heads.append(head)
        for k in range(len(posts) - 1):
            for a, b in ((feet[k], heads[k + 1]), (feet[k + 1], heads[k])):
                mid = (a + b) / 2 + V(0, side * rng.uniform(-.03, .05), -.06)
                root(p, curve([a, mid, b], 7), np.linspace(.034, .024, 7), 300 + k, 6, 0, **wood)
        for xm in rng.uniform(-8.5, 8.5, 7):
            c = rail_at(xm, side)
            moss_clump(p, rng, c + V(0, 0, .1), rng.uniform(.1, .15), .45)
        for xm in rng.uniform(-9.0, 9.0, 8):
            moss_clump(p, rng, V(xm, side * 1.47, float(deck(xm)) + .012), rng.uniform(.07, .11), .32)
    return p

# ---------------------------------------------------------------- thornroot (forced Divinity)

EMBER = .5         # thornroot's magenta embers, against a lens's or a source's 1.0


def thorn(part, base, direction, length, r, hook=None, sides=5):
    """A thorn: a cone standing on base along direction, hooked toward `hook` near its point; dark at the root, pale
    horn at the point."""
    base, d = np.asarray(base, np.float64), unit(direction)
    h = frame(d)[0] if hook is None else np.asarray(hook, np.float64) - d * np.dot(hook, d)
    h = unit(h) if norm(h) > 1e-6 else frame(d)[0]
    pts = [base - d * r * .6, base + d * length * .3, base + d * length * .68 + h * length * .07, base + d * length + h * length * .24]
    cols = [tone(THORN), mix(THORN, THORN_PALE, .35), mix(THORN, THORN_PALE, .85), tone(THORN_PALE, 1.5)]
    pipe(part, pts, [r * 1.2, r * .8, r * .42, r * .03], np.array(cols), BARK, sides, cap=False)


def thorny(part, rng, path, rad, every, length, toward=None, sides=5, skip=.06):
    """Thorns along a root: one about every `every` metres, standing off its bark at any angle round it (leaning toward
    `toward` when given), raked toward the root's tip and hooked back, larger on thicker wood."""
    path, rad = np.asarray(path, np.float64), np.broadcast_to(np.asarray(rad, np.float64), (len(path),))
    seg = np.r_[0.0, np.cumsum(norm(np.diff(path, axis=0), axis=1))]
    tang, A, B = frames(path)
    at = seg[-1] * skip + rng.uniform(0, every)
    big = max(float(rad.max()), 1e-6)
    while at < seg[-1] * (1 - skip * .5):
        i = int(np.clip(np.searchsorted(seg, at), 1, len(path) - 1))
        a = rng.uniform(0, TAU)
        out = A[i] * math.cos(a) + B[i] * math.sin(a)
        if toward is not None:
            out = unit(out + np.asarray(toward, np.float64) * rng.uniform(.3, 1.1))
            out = unit(out - tang[i] * np.dot(out, tang[i]))
        L = length * rng.uniform(.6, 1.2) * (.45 + .75 * rad[i] / big)
        thorn(part, path[i] + out * rad[i] * .8, out * .94 + tang[i] * .34, L, L * .17, -tang[i] - UP * .3, sides)
        at += every * rng.uniform(.6, 1.5)


def thorn_root(part, rng, path, rad, seed, sides=10, every=.3, length=.26, toward=None, **kw):
    """A thornroot: a black-violet root with its thorns."""
    root(part, path, rad, seed, sides, 3 if sides >= 9 else 2, kw.pop('twist', 2.0), .24, .1, colour=THORN_PALE, dark=THORN, **kw)
    if every:
        thorny(part, rng, path, rad, every, length, toward)


def ember(part, rng, centre, r, bright=EMBER):
    """An ember of forced Divinity: a lumpy magenta coal, hottest at its heart."""
    start = blob(part, centre, r, GLOW_BLIGHT, GLOW, 1, .3, int(rng.integers(100000)), (1, rng.uniform(.8, 1.3), rng.uniform(.9, 1.5)))
    v = np.asarray(part.v[start:], np.float64) - np.asarray(centre, np.float64)
    part.c[start:] = glow(GLOW_BLIGHT, bright * (1.15 - .5 * np.clip(norm(v, axis=1) / (r * 1.3), 0, 1))).tolist()


def _thorn_barrier(name, D, W, H, seed, sparse=1.0):
    """A wall of thornroot along y, D deep, W wide and H high, standing on z 0: a dense heart of fused stumps (so the box
    the game gives it for collision is filled and nothing shows through below about 0.45 of its height), thorned stems
    rising out of the ground on both faces, arches and lashings woven across them, embers in the crevices. sparse spaces the thorns and lashings out (the taller cage, to stay in budget)."""
    rng = np.random.default_rng(seed)
    p = Part(name, (BARK, GLOW))
    # ---- the heart: thick stumps packed side to side along the wall, so close that they fuse, round a thin dark
    # ---- web that closes whatever chink is left between them
    ny_, nz_ = int(W * 5) + 1, 9
    yy = np.linspace(-W / 2 + .2, W / 2 - .2, ny_)
    ends = ease((W / 2 - np.abs(yy)) / .9) ** .5
    top = H * np.clip(.4 + .05 * noise2(yy * .9, yy * 0 + .3, seed), .3, .46) * ends
    v = np.linspace(0, 1, nz_)
    Yg, Zg = np.repeat(yy[:, None], nz_, 1), top[:, None] * v[None, :]
    t = D * (.07 + .03 * noise2(Yg * 2.1, Zg * 2.1, seed + 3)) * (1 - .9 * v[None, :] ** 3) * (.25 + .75 * ends[:, None])
    sway = D * .05 * noise2(Yg * .6, Zg * .5, seed + 4)
    slab(p, np.stack([sway + t, Yg, Zg], -1), np.stack([sway - t, Yg, Zg], -1), tone(THORN, .6), BARK, tone(THORN, .6), BARK)
    fat = min(1.0, D / 1.2)
    stumps = int(round(W / .34))
    for k in range(stumps):
        y0 = -W / 2 + .3 + k * (W - .6) / (stumps - 1) + rng.uniform(-.05, .05)
        edge = ease((W / 2 - abs(y0)) / .8) ** .5
        tall = H * rng.uniform(.46, .74) * (.55 + .45 * edge)
        r0 = rng.uniform(.2, .28) * fat * (.75 + .25 * edge)
        x0 = (1.0 if k % 2 else -1.0) * D * rng.uniform(.04, .14)
        keys = np.stack([x0 + rng.uniform(-.06, .06, 4) * D, np.clip(y0 + np.cumsum(np.r_[0, rng.uniform(-.12, .12, 3)]), -W / 2 + r0, W / 2 - r0),
                         tall * np.array([-.01, .35, .72, 1.0])], 1)
        path, rad = curve(keys, max(9, int(tall / .32)), [r0, r0 * .92, r0 * .7, r0 * .08])
        thorn_root(p, rng, path, rad, seed + 200 + k, 10 if sparse <= 1.2 else 8, .5 * sparse, .26, None, ground=1.2, wet=.55)
    # ---- stems out of the ground, alternately on the front and the back face
    count = int(round(W * 2.3))
    reach = D / 2 - .05
    stems = []
    for k in range(count):
        face = 1.0 if k % 2 else -1.0
        y0 = -W / 2 + .22 + k * (W - .44) / (count - 1) + rng.uniform(-.1, .1)
        tall = H * (rng.uniform(.6, .97) if k != count // 2 else 1.0)
        r0 = rng.uniform(.13, .2) * min(1.0, D / 1.2) * (1.15 if tall > H * .85 else 1.0)
        ys = y0 + np.cumsum(np.r_[0, rng.uniform(-.38, .38, 5)])
        ys = np.clip(ys, -W / 2 + r0, W / 2 - r0)
        xs = face * reach * np.array([.55, .7, .5, .62, .4, .2]) + rng.uniform(-.08, .08, 6) * D
        keys = np.stack([xs, ys, tall * np.array([-.008, .16, .4, .64, .85, 1.0])], 1)
        n = max(12, int(tall / .3))
        path, rad = curve(keys, n, [r0, r0 * .92, r0 * .78, r0 * .58, r0 * .32, r0 * .06])
        thorn_root(p, rng, path, rad, seed + k, 10, .26 * sparse, .3, V(face, 0, .25), ground=1.2, wet=.6)
        stems.append((path, rad, face))
    # ---- arches: brambles that leave the ground, bow over and root again
    for k in range(int(round(W * .75))):
        face = 1.0 if k % 2 else -1.0
        ya = rng.uniform(-W / 2 + .4, W / 2 - .4)
        span = rng.uniform(1.4, 3.0) * rng.choice((-1.0, 1.0))
        yb = float(np.clip(ya + span, -W / 2 + .3, W / 2 - .3))
        apex = H * rng.uniform(.28, .78)
        x0 = face * reach * rng.uniform(.6, .85)
        keys = [(x0, ya, -.02), (x0 * 1.05, ya + (yb - ya) * .16, apex * .7), (x0 * .9, (ya + yb) / 2, apex), (x0 * 1.05, yb - (yb - ya) * .16, apex * .66),
                (x0, yb, -.02)]
        r0 = rng.uniform(.07, .11)
        path, rad = curve(keys, max(14, int(apex * 2 / .3)), [r0, r0 * .95, r0 * .8, r0 * .62, r0 * .3])
        thorn_root(p, rng, path, rad, seed + 50 + k, 8, .24 * sparse, .22, V(face, 0, .2), ground=1.2, wet=.6)
    # ---- lashings: thinner roots drawn across both faces
    for k in range(int(round(W * H * .42 / sparse ** 2))):
        face = 1.0 if k % 2 else -1.0
        ya = rng.uniform(-W / 2 + .3, W / 2 - .3)
        yb = float(np.clip(ya + rng.uniform(1.0, 2.4) * rng.choice((-1.0, 1.0)), -W / 2 + .2, W / 2 - .2))
        za = rng.uniform(.15, .8) * H * .85
        zb = float(np.clip(za + rng.uniform(-.9, .9), .1, H * .8))
        x0 = face * reach * rng.uniform(.5, .8)
        keys = [(x0 * .6, ya, za), (x0, ya + (yb - ya) * .3, za + (zb - za) * .3 + rng.uniform(-.15, .15)), (x0 * .95, ya + (yb - ya) * .7, za + (zb - za) * .7),
                (x0 * .5, yb, zb)]
        r0 = rng.uniform(.04, .06)
        path, rad = curve(keys, 10, [r0 * .6, r0, r0 * .9, r0 * .4])
        thorn_root(p, rng, path, rad, seed + 90 + k, 6, .22 * sparse, .15, V(face, 0, .1), wet=1.0)
    # ---- embers in the crevices, and forced light crawling up some stems
    for _ in range(int(round(W * H * .55 / sparse))):
        j, i = int(rng.integers(1, ny_ - 1)), int(rng.integers(1, nz_ - 1))
        face = rng.choice((-1.0, 1.0))
        ember(p, rng, V(face * D * rng.uniform(.2, .34), Yg[j, i], Zg[j, i] * 1.3 + .15), rng.uniform(.045, .09), EMBER * rng.uniform(.8, 1.2))
    for path, rad, face in stems[::3]:
        n = len(path)
        a, b = int(n * .12), int(n * .7)
        side = unit(np.cross(unit(path[b] - path[a]), V(0, 1.0, 0)))
        side = side if side[0] * face > 0 else -side
        vein = path[a:b] + side * (rad[a:b, None] * .96)
        pipe(p, vein, np.linspace(.016, .006, b - a), np.array([glow(GLOW_BLIGHT, q) for q in np.linspace(EMBER * .8, EMBER * .3, b - a)]), GLOW, 5, cap=False)
    fit_box(p, (D, W, H))
    return stand(p)


@built(.05)
def thorn_wall():
    """Thornroot barrier along y, 1.2 x 8 x 4.2 m (Settle dissolves it)."""
    return _thorn_barrier('SM_GN_ThornWall', 1.2, 8.0, 4.2, 461)


@built(.05)
def thorn_cage():
    """A taller thorn wall section along y, 1.5 x 10 x 7 m."""
    return _thorn_barrier('SM_GN_ThornCage', 1.5, 10.0, 7.0, 462, 1.7)


@built(.03)
def thorn_knot():
    """A knot of thornroot round an ember heart (the blade breaks it), 1.0 m across, centred on its heart."""
    rng = np.random.default_rng(463)
    p = Part('SM_GN_ThornKnot', (BARK, GLOW))
    t = np.linspace(0, TAU, 96, endpoint=False)
    big, small = .215, .105
    knot_ = np.stack([(big + small * np.cos(3 * t)) * np.cos(2 * t), (big + small * np.cos(3 * t)) * np.sin(2 * t), small * 1.25 * np.sin(3 * t)], 1)
    knot_ = np.concatenate([knot_, knot_[:3]])                     # closed: the ends run through each other
    rad = .072 * (1 + .16 * np.sin(np.linspace(0, 9 * TAU, len(knot_))))
    thorn_root(p, rng, knot_, rad, 463, 12, .16, .2, wet=1.0, twist=5.0)
    a = np.linspace(0, TAU * 1.03, 44)
    loop = np.stack([.3 * np.cos(a), .3 * np.sin(a) * .5 + .02 * np.sin(a * 3), .3 * np.sin(a) * .86], 1)
    thorn_root(p, rng, loop, np.r_[.03, np.full(42, .05), .03], 464, 9, .15, .15, wet=1.0, twist=4.0)
    for k in range(5):                                             # loose ends curling off the knot
        a0 = rng.uniform(0, TAU)
        d = unit(V(math.cos(a0), math.sin(a0), rng.uniform(-.6, .6)))
        s = unit(np.cross(d, UP))
        keys = [d * .2, d * .33 + s * .06, d * .4 + s * .15 + UP * .04, d * .4 + s * .25 + UP * .1]
        path, r = curve(keys, 9, [.045, .038, .026, .008])
        thorn_root(p, rng, path, r, 470 + k, 7, .12, .12, wet=1.0)
    ember(p, rng, (0, 0, 0), .15, 1.0)
    for _ in range(7):
        d = unit(rng.normal(0, 1, 3))
        ember(p, rng, d * rng.uniform(.17, .26), rng.uniform(.025, .045), EMBER)
    mark(p, 'heart', (0, 0, 0))
    v = np.asarray(p.v, np.float64)
    return _moved(p, (0, 0, 0), 1.0 / float((v.max(0) - v.min(0)).max()))       # the heart stays on the origin

# ---------------------------------------------------------------- the Just's machines: engineered parts
# The Hedge and the people are built as machines that could work: a dark load-bearing frame, enamel plates over it
# with real gaps and chipped, rolled edges (plate()), hydraulic rams with clevis pins (ram()), hinge pins in bosses
# (pivot()), fasteners, lifting eyes, hatches, louvred vents, cable looms in clamps, serial plates as plain shapes,
# lift fans with intakes and guards. Livery: bone-white enamel (PAINT), graphite frames (STEEL), one signal-orange
# stripe a unit, amber light. The lens at a unit's front is its brightest light (LENS), so it reads as the weak
# point; every other emitter runs at EMIT.

LENS, EMIT = 1.0, .3
GRAPHITE = tone(JUST_GRAPHITE)
FRAME = tone(STEEL_DARK)
BARE = tone(STEEL_GREY)                    # bare weathered steel
BRIGHT = tone(STEEL_GREY, 2.1)             # ground or rubbed steel: piston rods, pin heads, blade edges, handles
ORANGE = tone(JUST_ORANGE)
RUBBER = tone(JUST_GRAPHITE, .7)           # cable sheath, hose, seals (on PAINT: not a metal)
CHIP = mix(STEEL_DARK, RUST_DARK, .45)     # what shows where enamel has chipped off an edge
SENSOR = tone(JUST_GRAPHITE, .45)          # the dark glass of a secondary sensor (glossy PAINT stands for it)


def bone(rng, wear=.14):
    """A bone-white enamelled plate: each a little warmer or greyer, some more worn."""
    return tone(mix(JUST_BONE, CONCRETE_PALE, rng.uniform(0, .4)), rng.uniform(1 - wear, 1.0))


def _deg(a, b):
    return math.radians(a), math.radians(b)


def _span(a, b, n, thick, size):
    e = min(.2, 1.4 * thick / max(abs(b - a) * size, 1e-6))
    return np.concatenate([[a], np.linspace(a + (b - a) * e, b - (b - a) * e, max(n, 2)), [b]])


def plate(part, hull, th, ph, colour, slot=PAINT, thick=.02, gap=.012, roll=.55, n=(2, 2), lift=0.0, back=False, sag=.3,
          seal=2.2, chip=.6, seed=0):
    """fl.Hull.plate with weathering in it: a plate over th and ph (radians) of the hull, inset by half the seam gap,
    its border rolled toward the core; the enamel is faintly mottled and chipped along that rolled edge, where the
    dark steel shows (chip is how much, PAINT only). Returns the inset ranges, for fasteners."""
    rm = float(np.mean(hull.r))
    sm = max(abs(math.sin((th[0] + th[1]) / 2)), .25)
    dt, dp = gap / 2 / rm, gap / 2 / (rm * sm)
    t0, t1, p0, p1 = th[0] + dt, th[1] - dt, ph[0] + dp, ph[1] - dp
    n0, n1 = n
    for _ in range(12):
        us, vs = _span(t0, t1, n0, thick, rm), _span(p0, p1, n1, thick, rm * sm)
        Ui, Vi = np.meshgrid(us[1:-1], vs[1:-1], indexing='ij')
        P = hull.point(Ui, Vi)
        eu = norm(hull.point((Ui[:-1] + Ui[1:]) / 2, Vi[:-1]) - (P[:-1] + P[1:]) / 2, axis=-1).max()
        ev = norm(hull.point(Ui[:, :-1], (Vi[:, :-1] + Vi[:, 1:]) / 2) - (P[:, :-1] + P[:, 1:]) / 2, axis=-1).max()
        if max(eu, ev) <= sag * thick:
            break
        if eu >= ev:
            n0 += 1
        else:
            n1 += 1
    U, W = np.meshgrid(us, vs, indexing='ij')
    border = np.zeros(U.shape, bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    depth = np.where(border, roll * thick, 0.0) - lift
    inner = np.where(border, max(seal * thick, thick - lift), thick - lift)
    outer = hull.point(U, W, depth)
    q = outer / rm
    rgb = np.asarray(colour, np.float64)[:3] * (1 + .06 * noise2(q[..., 0] * 9 + seed, q[..., 1] * 9 + q[..., 2] * 7, seed + 3))[..., None]
    if chip and slot == PAINT:
        c = chip * np.clip(.35 + .9 * noise2(q[..., 0] * 23 + seed * 3.1, q[..., 1] * 23 - q[..., 2] * 19, seed + 9), 0, 1)
        c = np.where(border, c, 0.0)[..., None]
        rgb = rgb * (1 - c) + np.asarray(CHIP[:3]) * c
    slab(part, outer, hull.point(U, W, inner), rgba(np.minimum(rgb, .9)).reshape(-1, 4), slot, tone(colour, .5), slot, back)
    return t0, t1, p0, p1


def bolts(part, points, normals, r, colour=None, slot=STEEL):
    """Hex bolt heads (r to a corner, chamfered) standing on points along normals."""
    pts = np.asarray(points, np.float64).reshape(-1, 3)
    nrm = unit(np.broadcast_to(np.asarray(normals, np.float64), pts.shape).reshape(-1, 3))
    ang = np.linspace(0, TAU, 6, endpoint=False)
    verts, faces = [], []
    for i, (q, n) in enumerate(zip(pts, nrm)):
        a, b = frame(n)
        hexa_ = r * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b)
        verts.extend((q + hexa_ - n * r * .1).tolist())
        verts.extend((q + hexa_ + n * r * .6).tolist())
        verts.extend((q + hexa_ * .78 + n * r * .74).tolist())
        o = i * 18
        faces += [[o + j, o + (j + 1) % 6, o + 6 + (j + 1) % 6, o + 6 + j] for j in range(6)]
        faces += [[o + 6 + j, o + 6 + (j + 1) % 6, o + 12 + (j + 1) % 6, o + 12 + j] for j in range(6)]
        faces.append([o + 12 + j for j in range(6)])
    if verts:
        part.add(verts, faces, BARE if colour is None else colour, slot, False)


def studs(part, points, normals, r, colour=None, slot=STEEL):
    """Dome-headed rivets or quarter-turn fasteners (fl.rivets)."""
    pts = np.asarray(points, np.float64).reshape(-1, 3)
    fl.rivets(part, pts, np.broadcast_to(np.asarray(normals, np.float64), pts.shape), r, BARE if colour is None else colour, slot)


def ram(part, a, b, r, pin=None, stroke=.56, body=None, slot=STEEL):
    """A hydraulic cylinder from pin a to pin b: an eye, cheeks and a cross pin at each end, the barrel with its end
    cap, gland and hose port, and the bright rod. pin is the pins' axis (any perpendicular when not given)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    L = norm(b - a)
    d = (b - a) / L
    ax = frame(d)[0] if pin is None else np.asarray(pin, np.float64)
    ax = unit(ax - d * np.dot(ax, d))
    s = S(r, 8, 24)
    m = max(8, s * 2 // 3)
    for q in (a, b):
        pipe(part, [q - ax * r * 1.3, q + ax * r * 1.3], r * .4, BRIGHT, STEEL, max(6, s // 2))
        pipe(part, [q - ax * r * .5, q + ax * r * .5], r * .85, GRAPHITE, STEEL, m)
        for sg in (-1, 1):
            pipe(part, [q + ax * sg * r * .62, q + ax * sg * r * .86], r, FRAME, STEEL, m)
    e0, e1 = a + d * r * .8, a + d * L * stroke
    pipe(part, [e0, e1], r, FRAME if body is None else body, slot, s)
    rot = along(d)
    sweep(part, [(r * .96, 0), (r * 1.2, 0), (r * 1.2, r * .5), (r * .96, r * .5)], GRAPHITE, STEEL, sides=s, rot=rot, origin=e1 - d * r * .5)
    sweep(part, [(r * .96, 0), (r * 1.14, 0), (r * 1.14, r * .36), (r * .96, r * .36)], GRAPHITE, STEEL, sides=s, rot=rot, origin=e0)
    pipe(part, [e1, b - d * r * .7], r * .5, BRIGHT, STEEL, m)
    side = np.cross(d, ax)
    port = e0 + d * r * .9 + side * r * .95
    pipe(part, [port, port + side * r * .5], r * .26, BRIGHT, STEEL, 6)


def pivot(part, c, axis, r, length, colour=None):
    """A hinge: a boss across the joint, the pin's bright heads proud of it on both sides, each with its retaining bolt."""
    c, d = np.asarray(c, np.float64), unit(axis)
    s = S(r, 8, 32)
    pipe(part, [c - d * length / 2, c + d * length / 2], r, GRAPHITE if colour is None else colour, STEEL, s)
    for sg in (-1, 1):
        e = c + d * sg * length / 2
        pipe(part, [e, e + d * sg * r * .2], r * .66, BRIGHT, STEEL, max(8, s * 2 // 3))
        bolts(part, [e + d * sg * r * .2], [d * sg], r * .24)


def lug(part, c, normal, r, across=None):
    """A lifting eye: a ring standing on a welded pad; `across` is the ring's own axis."""
    c, n = np.asarray(c, np.float64), unit(normal)
    a = frame(n)[0] if across is None else unit(np.asarray(across, np.float64) - n * np.dot(across, n))
    obox(part, c + n * r * .1, (r * .12, r * .5, r * 1.15), FRAME, STEEL, r * .05, basis(n, np.cross(n, a)))
    hoop(part, c + n * r * 1.02, a, r, r * .22, BARE, STEEL, S(r, 12, 24), 6)


def louvre(part, centre, normal, up, w, h, slats=5, colour=None):
    """A louvred vent proud of a surface: a frame round a dark throat, slats raked down and out. normal points out of
    the surface, up along the vent's height."""
    rot = basis(normal, up)
    c = np.asarray(centre, np.float64)
    d = min(w, h) * .14
    obox(part, c, (d * .5, w / 2, h / 2), tone(JUST_GRAPHITE, .6), STEEL, d * .2, rot)
    bar = d * .55
    for sg in (-1, 1):
        obox(part, c + rot @ V(d * .35, sg * (w / 2 + bar * .4), 0), (d * .7, bar, h / 2 + bar * 1.4), FRAME, STEEL, bar * .3, rot)
        obox(part, c + rot @ V(d * .35, 0, sg * (h / 2 + bar * .4)), (d * .7, w / 2 + bar * 1.4, bar), FRAME, STEEL, bar * .3, rot)
    tilt = basis((1, 0, -.75), (.75, 0, 1))
    for k in range(slats):
        z = -h / 2 + h * (k + .5) / slats
        obox(part, c + rot @ V(d * .75, 0, z), (d * .55, w / 2 * .98, h / slats * .16), BARE if colour is None else colour, STEEL, d * .08, rot @ tilt)


def loom(part, path, r, n=3, clamps=3, colour=None):
    """A cable loom along a path: n cables in a bundle (rubber sheathed), held down by steel clamps with a bolt each."""
    path = np.asarray(path, np.float64)
    tang, A, B = frames(path)
    for k in range(n):
        a = k / n * TAU + .5
        off = (A * math.cos(a) + B * math.sin(a)) * (r * 1.02 if n > 1 else 0.0)
        pipe(part, path + off, r, RUBBER if colour is None or k else colour, PAINT, 6)
    big = r * (2.15 if n > 1 else 1.15)
    if clamps:
        for i in np.linspace(0, len(path) - 1, clamps + 2)[1:-1].round().astype(int):
            sweep(part, [(big - r * .25, -r * 1.1), (big + r * .3, -r * 1.1), (big + r * .3, r * 1.1), (big - r * .25, r * 1.1)], BARE, STEEL,
                  sides=10, rot=aim(tang[i], A[i]), origin=path[i])
            bolts(part, [path[i] + B[i] * (big + r * .3)], [B[i]], r * .5)


def hose(part, path, r, colour=None):
    """A hydraulic hose with a crimped ferrule at each end."""
    path = np.asarray(path, np.float64)
    pipe(part, path, r, RUBBER if colour is None else colour, PAINT, 8)
    for a, b in ((path[0], path[1]), (path[-1], path[-2])):
        d = unit(b - a)
        pipe(part, [a - d * r * .3, a + d * r * 2.4], r * 1.3, BRIGHT, STEEL, 8)


def tag(part, centre, normal, up, w=.05, h=.03):
    """A serial plate: a small bare-metal plate riveted at its corners, embossed with plain bars (no text)."""
    rot = basis(normal, up)
    c = np.asarray(centre, np.float64)
    t = min(w, h) * .05
    obox(part, c + rot @ V(t, 0, 0), (t, w / 2, h / 2), tone(STEEL_GREY, 1.7), STEEL, t * .5, rot)
    studs(part, [c + rot @ V(t * 2, sy * w * .42, sz * h * .38) for sy in (-1, 1) for sz in (-1, 1)], rot[:, 0], min(w, h) * .06)
    for i, (y0, y1) in enumerate(((-.3, .3), (-.3, .1), (-.3, .22))):
        obox(part, c + rot @ V(t * 2.2, (y0 + y1) / 2 * w, h * (.2 - .2 * i)), (t * .4, (y1 - y0) / 2 * w, h * .04), GRAPHITE, STEEL, t * .2, rot)


def eye(part, centre, axis, r, up=(0, 0, 1), bright=LENS, colour=GLOW_AMBER, bezel=None, hood=0.0, fasteners=0, name='lens'):
    """The amber lens: a lit glass dome, brightest at its centre, behind an iris ring in a graphite socket. bezel (a
    colour) adds an enamel ring round it, with `fasteners` round that; hood (radians either side of up) a visor over
    it. Marks the lens's front on the part under `name`."""
    c, ax = np.asarray(centre, np.float64), unit(axis)
    rot = aim(ax, up)
    s = S(r * 1.4, 14, 48)
    sweep(part, [(r * .98, r * .2), (r * .98, -r * .55), (r * 1.3, -r * .55), (r * 1.36, 0), (r * 1.26, r * .26), (r * 1.08, r * .3)],
          GRAPHITE, STEEL, sides=s, rot=rot, origin=c)
    if bezel is not None:
        sweep(part, [(r * 1.36, -r * .55), (r * 1.7, -r * .55), (r * 1.76, -r * .16), (r * 1.66, r * .08), (r * 1.4, r * .12)], bezel, PAINT,
              sides=s, rot=rot, origin=c)
        if fasteners:
            a = (np.arange(fasteners) + .5) / fasteners * TAU
            studs(part, np.stack([np.cos(a) * r * 1.56, np.sin(a) * r * 1.56, np.full(fasteners, r * .1)], 1) @ rot.T + c, ax, r * .07)
    if hood:
        sweep(part, [(r * 1.78, -r * .5), (r * 1.98, -r * .5), (r * 1.98, r * .85), (r * 1.9, r), (r * 1.8, r * .9)],
              GRAPHITE if bezel is None else bezel, STEEL if bezel is None else PAINT, -hood, hood, rot=rot, origin=c)
    sweep(part, [(r * .8, r * .12), (r * .98, r * .12), (r * .98, r * .2), (r * .84, r * .22)], BARE, STEEL, sides=s, rot=rot, origin=c)
    lat = np.linspace(math.pi / 2, 0, max(6, S(r, 8, 48) // 4))        # the dome, from its rim up to its pole
    turn(part, [(r * .86 * math.sin(q), -r * .08 + r * .56 * math.cos(q)) for q in lat],
         np.array([glow(colour, bright * (1 - .5 * math.sin(q) ** 2)) for q in lat]), GLOW, s, rot, c, caps=(False, False))
    mark(part, name, c + ax * r * .48)


def sensor(part, centre, axis, r):
    """A secondary sensor: a dark glass dome in a steel bezel."""
    c = np.asarray(centre, np.float64)
    rot = along(axis)
    s = S(r * 1.3, 10, 24)
    sweep(part, [(r * .96, r * .18), (r * .96, -r * .4), (r * 1.3, -r * .4), (r * 1.34, 0), (r * 1.2, r * .24), (r * 1.04, r * .26)], BARE, STEEL,
          sides=s, rot=rot, origin=c)
    turn(part, [(r * .96, -r * .05), (r * .8, r * .2), (r * .5, r * .36), (0, r * .42)], SENSOR, PAINT, s, rot, c, caps=(False, False))


def rotor(part, rng, c, axis, R, blades=5, shell=None, guard=True, forward=(1, 0, 0), depth=None):
    """A ducted lift fan: a duct with a rolled intake lip (enamel outside, dark inside), three stator vanes holding the
    motor pod and its spinner, twisted blades in cuffs, and a wire guard over the intake. axis points the way it
    lifts, which is the intake's side."""
    c, ax = np.asarray(c, np.float64), unit(axis)
    rot = aim(ax, forward)
    h = R * .5 if depth is None else depth
    w = R * .08
    s = S(R, 20, 48)
    sweep(part, [(R, -h * .5), (R + w * .7, -h * .5), (R + w * 1.3, h * .1), (R + w * 1.15, h * .42), (R + w * .45, h * .5), (R, h * .4)],
          GRAPHITE if shell is None else shell, PAINT, sides=s, rot=rot, origin=c, bands={5: (GRAPHITE, STEEL), 0: (FRAME, STEEL)})
    turn(part, [(0, -h * .62), (R * .15, -h * .52), (R * .2, -h * .18), (R * .2, h * .1), (R * .13, h * .3), (0, h * .4)], GRAPHITE, STEEL,
         S(R * .2, 10, 24), rot, c)
    for k in range(3):
        a = (k + .5) / 3 * TAU
        u = rot @ V(math.cos(a), math.sin(a), 0)
        strut(part, c + u * R * .17 - ax * h * .3, c + u * R * 1.01 - ax * h * .3, R * .03, h * .3, FRAME, STEEL, up=ax, bevel=R * .008)
    spin = rng.uniform(0, TAU)
    rr, cv = np.linspace(R * .2, R * .955, 5), np.linspace(-.5, .5, 3)
    pitch, ch = np.radians(np.linspace(38, 14, 5)), np.linspace(R * .24, R * .15, 5)
    for k in range(blades):
        a = spin + k / blades * TAU
        u, t = rot @ V(math.cos(a), math.sin(a), 0), rot @ V(-math.sin(a), math.cos(a), 0)
        cdir = t[None, :] * np.cos(pitch)[:, None] + ax[None, :] * np.sin(pitch)[:, None]
        ndir = -t[None, :] * np.sin(pitch)[:, None] + ax[None, :] * np.cos(pitch)[:, None]
        mid = c + ax * h * .1 + u[None, :] * rr[:, None]
        P = mid[:, None, :] + cdir[:, None, :] * (ch[:, None] * cv[None, :])[..., None]
        half = (R * .016 * (1 - np.abs(cv))[None, :] * np.linspace(1, .6, 5)[:, None])[..., None]
        slab(part, P + ndir[:, None, :] * half, P - ndir[:, None, :] * half, FRAME, STEEL, BARE, STEEL)
        pipe(part, [c + ax * h * .1 + u * R * .12, c + ax * h * .1 + u * R * .24], R * .034, BARE, STEEL, 8)
    if guard:
        top = c + ax * h * .56
        hoop(part, top, ax, (R + w * .5) * .5, R * .012, BARE, STEEL, max(12, s // 2), 5)
        hoop(part, top - ax * h * .06, ax, (R + w * .5) * .97, R * .012, BARE, STEEL, s, 5)
        for k in range(6):
            a = (k + .25) / 6 * TAU
            u = rot @ V(math.cos(a), math.sin(a), 0)
            pipe(part, [top + u * R * .05 + ax * h * .04, top + u * (R + w * .5) * .5, top + u * (R + w * .5) * .97 - ax * h * .06], R * .01, BARE,
                 STEEL, 4, cap=False)
        ball(part, top + ax * h * .04, R * .06, FRAME, STEEL, 8)


def thruster(part, c, axis, r, length, bright=EMIT, colour=GLOW_AMBER, guard=False):
    """A thrust nozzle: a bell on a gimbal collar with four trim links, sooted inside and heat-stained toward its lip,
    a dim glow in its throat; guard adds a hoop on stays behind the lip. axis points the way the exhaust leaves."""
    c, ax = np.asarray(c, np.float64), unit(axis)
    rot = along(ax)
    L = length
    s = S(r, 14, 40)
    hot = mix(STEEL_GREY, RUST_DARK, .45)
    sweep(part, [(r * .88, L), (r * .5, L * .2), (r * .62, -L * .05), (r * .86, L * .5), (r, L), (r * .95, L * 1.04)], BARE, STEEL, sides=s,
          rot=rot, origin=c, bands={0: (tone(JUST_GRAPHITE, .6), STEEL), 3: (hot, STEEL), 4: (hot, STEEL)})
    sweep(part, [(r * .6, -L * .16), (r * .82, -L * .16), (r * .82, L * .08), (r * .6, L * .08)], GRAPHITE, STEEL, sides=s, rot=rot, origin=c)
    for k in range(4):
        a = (k + .5) / 4 * TAU
        u = rot @ V(math.cos(a), math.sin(a), 0)
        pipe(part, [c + u * r * .8 - ax * L * .04, c + u * r * .96 + ax * L * .62], r * .035, BRIGHT, STEEL, 5)
    disc(part, c + ax * L * .24, ax, r * .5, glow(colour, bright * .8), GLOW, s, 0.0, glow(colour, bright * .3))
    if guard:
        hoop(part, c + ax * L * 1.22, ax, r * 1.04, r * .035, BARE, STEEL, s, 5)
        for k in range(3):
            a = (k + .2) / 3 * TAU
            u = rot @ V(math.cos(a), math.sin(a), 0)
            pipe(part, [c + u * r * .98 + ax * L * .9, c + u * r * 1.04 + ax * L * 1.22], r * .03, BARE, STEEL, 4)


def field(part, c, axis, r, bright=EMIT, colour=GLOW_AMBER, shell=None, coils=8):
    """A hover field unit: a housing ring (an enamel band round it when shell is given), coil blocks round the inside
    of its throat, and a dim concave field face. axis points the way the field pushes (down, for lift)."""
    c, ax = np.asarray(c, np.float64), unit(axis)
    rot = along(ax)
    s = S(r, 16, 48)
    sweep(part, [(r * .74, r * .16), (r * .74, -r * .3), (r * .98, -r * .36), (r * 1.08, -r * .1), (r * 1.08, r * .08), (r * .96, r * .22)],
          GRAPHITE, STEEL, sides=s, rot=rot, origin=c)
    if shell is not None:
        sweep(part, [(r * 1.08, -r * .1), (r * 1.15, -r * .08), (r * 1.15, r * .06), (r * 1.08, r * .08)], shell, PAINT, sides=s, rot=rot, origin=c)
    for k in range(coils):
        a = (k + .5) / coils * TAU
        u = rot @ V(math.cos(a), math.sin(a), 0)
        obox(part, c + u * r * .66 + ax * r * .02, (r * .07, r * .13, r * .09), BARE, STEEL, r * .02, basis(u, ax))
    disc(part, c - ax * r * .1, ax, r * .74, glow(colour, bright), GLOW, s, -r * .14, glow(colour, bright * .45))


def hatch(part, hull, th, ph, colour, thick, seed=0, handle=True):
    """An access hatch on a hull: a panel proud of the plates round it, a fastener in each corner, a pull handle."""
    b = plate(part, hull, th, ph, colour, PAINT, thick, thick * .5, n=(3, 3), lift=thick * .9, seed=seed)
    dt, dp = (b[1] - b[0]) * .12, (b[3] - b[2]) * .12
    T, P = np.array([b[0] + dt, b[0] + dt, b[1] - dt, b[1] - dt]), np.array([b[2] + dp, b[3] - dp, b[2] + dp, b[3] - dp])
    studs(part, hull.point(T, P, -thick * .9), hull.normal(T, P), thick * .5)
    if handle:
        t_at = b[1] - dt * 2.2
        ends = [hull.point(t_at, b[2] + (b[3] - b[2]) * q, -thick * .9) for q in (.36, .64)]
        out = hull.normal(t_at, (b[2] + b[3]) / 2) * thick * 1.6
        pipe(part, [ends[0], ends[0] + out, ends[1] + out, ends[1]], thick * .3, BRIGHT, STEEL, 6)


def arm(part, rng, sh, el, wr, w, anchor=None, covers=True):
    """An articulated arm: shoulder at sh, elbow pin at el, wrist at wr. Box booms w across (the forearm lighter) with
    enamel covers bolted on both cheeks, a hinge pin through the elbow, a ram across it, and a ram from `anchor` (a
    point on the body) to the upper boom. Returns the elbow's hinge axis and the forearm's direction."""
    sh, el, wr = (np.asarray(q, np.float64) for q in (sh, el, wr))
    hinge_ = unit(np.cross(el - sh, wr - el))
    for a, b, ww in ((sh, el, w), (el, wr, w * .8)):
        f, L = unit(b - a), norm(b - a)
        up = unit(np.cross(f, hinge_))
        strut(part, a, b, ww, ww * 1.08, FRAME, STEEL, up=up, bevel=ww * .14)
        if covers:
            mid = (a + b) / 2
            for sg in (-1, 1):
                obox(part, mid + hinge_ * sg * ww * .53, (L * .33, ww * .05, ww * .38), bone(rng), PAINT, ww * .03, basis(f, up))
                studs(part, [mid + hinge_ * sg * ww * .585 + f * dx * L * .29 + up * dz * ww * .27 for dx in (-1, 1) for dz in (-1, 1)],
                      hinge_ * sg, ww * .05)
    pivot(part, el, hinge_, w * .55, w * 1.5)
    up_arm, fore = unit(np.cross(unit(el - sh), hinge_)), unit(wr - el)
    up_fore = unit(np.cross(fore, hinge_))
    ram(part, sh + (el - sh) * .3 + up_arm * w * .8, el + fore * norm(wr - el) * .3 + up_fore * w * .65, w * .16, pin=hinge_)
    if anchor is not None:
        ram(part, anchor, sh + (el - sh) * .6 - up_arm * w * .7, w * .19, pin=hinge_)
    return hinge_, fore


def weather(part, seed=0, span=1.0, under=.28, dirt=.12, streak=.16, rust=0.0, moss=0.0, dust=0.0, start=0,
            skip=(GLOW, LEAF, GLASS, CLOTH, MOSS, BARK)):
    """Vertex-colour weathering of everything added since `start` (span: the object's size, which scales the
    patterns): under darkens toward the underside, where soot and shadow gather; dirt is blotchy grime; streak is rain
    runs down the sides, rust-brown on enamel; rust blooms in patches, denser low down; moss greens what faces the sky
    in patches, where water sits; dust pales it. Lights, cloth and plants keep their colours."""
    v = np.asarray(part.v, np.float64)
    cols = np.asarray(part.c, np.float64)
    nrm = vertex_normals(part)
    vs = vertex_slots(part)
    live = ~np.isin(vs, [part.slots.index(s) for s in skip if s in part.slots])
    live[:start] = False
    paint = vs == (part.slots.index(PAINT) if PAINT in part.slots else -1)
    lo, hi = v[start:].min(0), v[start:].max(0)
    h = np.clip((v[:, 2] - lo[2]) / max(hi[2] - lo[2], 1e-6), 0, 1)
    x, y, z = (v / max(span, 1e-6)).T
    k = (1 - under * (1 - h) ** 1.5 * (.6 + .4 * np.clip(-nrm[:, 2], 0, 1))) * (1 - dirt * (.5 + .5 * noise2(x * 5 + z * 1.9, y * 5 - z * 2.1, seed + 3)))
    run = np.clip(noise2(x * 27 + 3.1, y * 27, seed + 5) * 1.7 - .3, 0, 1) * (1 - np.abs(nrm[:, 2])) ** 2 * (.45 + .55 * (1 - h))
    rgb = cols[:, :3] * np.where(live, k * (1 - streak * run), 1.0)[:, None]

    def tint(rgb, amount, colour):
        m = np.where(live, np.clip(amount, 0, 1), 0.0)[:, None]
        c = np.asarray(colour, np.float64)
        return rgb * (1 - m) + (c[:3] if c.ndim == 1 else c[:, :3]) * m
    rgb = tint(rgb, streak * 1.4 * run * paint, RUST_DARK)
    if rust:
        patch = np.clip(noise2(x * 8 + 11 + z * 3, y * 8 - z * 5, seed + 9) + rust * 1.6 - 1.0, 0, 1) * (.5 + .5 * (1 - h))
        mott = (.5 + .5 * noise2(x * 40, y * 40 + z * 31, seed + 12))[:, None]
        rgb = tint(rgb, patch * 1.4, np.asarray(RUST_ORANGE[:3]) * mott + np.asarray(RUST_DARK[:3]) * (1 - mott))
    if moss:
        rgb = tint(rgb, np.clip((nrm[:, 2] - .3) / .7, 0, 1) * np.clip(noise2(x * 9 + 5, y * 9 + z * 4, seed + 15) + moss * 1.5 - .8, 0, 1) * 1.3,
                   mix(MOSS_GREEN, MOSS_DEEP, .4))
    if dust:
        rgb = tint(rgb, dust * np.clip(nrm[:, 2], 0, 1) ** 2, ROCK_WARM)
    cols[:, :3] = np.where(live[:, None], np.minimum(rgb, .9), cols[:, :3])
    part.c = cols.tolist()


def hover(part, size, seed=0, **kw):
    """Finishes a unit of the Hedge: scaled so that its largest dimension is `size` (the contract's number), its bounds
    centred on the origin, where the scenario holds the hover height, then weathered."""
    v = np.asarray(part.v, np.float64)
    lo, hi = v.min(0), v.max(0)
    _moved(part, -(lo + hi) / 2, size / float((hi - lo).max()))
    weather(part, seed, size, **kw)
    return part

# ---------------------------------------------------------------- the Hedge (SM_GE_*): hovering, centred, facing +x

@built(.006)
def wasp():
    """SM_GE_Wasp (0.7 m): a small quick flier. A plated thorax with a sensor head on a gimbal collar, an abdomen of
    five overlapping segments curled under to its stinger emitter (the third segment is the unit's orange band), two
    ducted lift fans on stub pylons, landing skids."""
    rng = np.random.default_rng(501)
    p = Part('SM_GE_Wasp', (STEEL, PAINT, GLOW))
    t = .008
    thorax = Hull((.04, 0, .02), (.155, .1, .092), .9, .85)
    thorax.core(p, GRAPHITE, STEEL, t * 1.5, (16, 32))
    for i, th in enumerate(((.5, 1.18), (1.18, 1.9), (1.9, 2.62))):
        b = plate(p, thorax, th, _deg(32, 148), bone(rng), PAINT, t, .006, n=(4, 6), seed=i)
        thorax.rivet_row(p, (b[0] + .07,) * 2, (b[2] + .16, b[3] - .16), 5, .0032, BARE, STEEL)
        for ph in (_deg(-34, 32), _deg(148, 214)):
            plate(p, thorax, th, ph, bone(rng), PAINT, t, .006, n=(4, 3), seed=i + 5)
    for th0 in (.85, 1.5, 2.2):                                  # frame ribs across the belly
        plate(p, thorax, (th0 - .05, th0 + .05), _deg(214, 326), FRAME, STEEL, t, 0.0, n=(2, 6), lift=t * .3)
    hatch(p, thorax, (1.3, 1.78), _deg(66, 114), bone(rng, .05), t * .5, 3)
    grip = [thorax.point(2.28, math.radians(a)) for a in (66, 114)]
    pipe(p, [grip[0], grip[0] + (0, 0, .024), grip[1] + (0, 0, .024), grip[1]], .0038, BRIGHT, STEEL, 8)   # the carrying handle, rubbed bright
    for a in (0.0, math.pi):
        louvre(p, thorax.point(1.56, a, -t * .2), thorax.normal(1.56, a), (0, 0, 1), .05, .026, 4)
    tag(p, thorax.point(.82, math.radians(-8), -t * .15), thorax.normal(.82, math.radians(-8)), (0, 0, 1), .03, .018)
    # ---- the sensor head
    head = Hull((.222, 0, .004), (.07, .068, .06), .9, .85)
    head.core(p, GRAPHITE, STEEL, .008, (12, 24))
    plate(p, head, (.75, 2.5), _deg(22, 158), bone(rng, .06), PAINT, .006, .005, n=(4, 6), seed=11)
    for ph in (_deg(-42, 22), _deg(158, 222)):
        plate(p, head, (.9, 2.4), ph, bone(rng), PAINT, .006, .005, n=(3, 3), seed=12)
    sweep(p, [(.03, 0), (.047, 0), (.05, .012), (.047, .024), (.03, .024)], GRAPHITE, STEEL, rot=along((1, 0, 0)), origin=(.146, 0, .008))
    eye(p, (.284, 0, 0), (1, 0, -.06), .034, bezel=bone(rng, .05), hood=1.25, fasteners=8)
    for s_ in (-1, 1):
        a = math.radians(-22 if s_ > 0 else 202)
        sensor(p, head.point(.72, a, -.001), head.normal(.72, a), .011)
        whip = curve([head.point(2.0, math.radians(90 - s_ * 32)), V(.17, s_ * .05, .1), V(.11, s_ * .075, .135), V(.05, s_ * .09, .15)], 9)
        pipe(p, whip, np.linspace(.003, .0012, 9), GRAPHITE, STEEL, 5)
        ball(p, whip[-1], .0035, BRIGHT, STEEL, 6)
    # ---- the abdomen: segments along a curl, each a shell over a dark core, worked by two rams from the thorax
    spine = bezier(V(-.1, 0, .015), V(-.27, 0, .06), V(-.44, 0, -.05), V(-.345, 0, -.215), 61)
    tang = unit(np.gradient(spine, axis=0))
    at, seg_r = [.1, .29, .49, .69, .87], [.068, .082, .078, .062, .044]
    for k, (q, r) in enumerate(zip(at, seg_r)):
        i = int(round(q * 60))
        d = tang[i]
        hull = Hull(spine[i], (.0525 if k < 4 else .045, r, r), .7, .8, basis(d, V(d[2], 0, -d[0])))
        hull.core(p, GRAPHITE, STEEL, r * .16, (8, 24))
        plate(p, hull, (.34, 2.8), _deg(-28, 208), ORANGE if k == 2 else bone(rng), PAINT, r * .1, r * .08, n=(4, 8), seed=20 + k)
        plate(p, hull, (.5, 2.64), _deg(208, 332), FRAME, STEEL, r * .1, r * .08, n=(3, 4))
    ball(p, (-.1, 0, .014), .034, GRAPHITE, STEEL, 16)
    for s_ in (-1, 1):
        a, b = V(-.06, s_ * .084, .028), V(-.21, s_ * .092, .045)
        ram(p, a, b, .0055, pin=(0, 0, 1))
        obox(p, a - (0, s_ * .012, 0), (.012, .012, .009), FRAME, STEEL, .003)
        obox(p, b - (0, s_ * .012, 0), (.012, .012, .009), FRAME, STEEL, .003)
    belly = [spine[i] - V(tang[i][2], 0, -tang[i][0]) * (float(np.interp(i / 60, at, seg_r)) + .004) for i in range(5, 56, 5)]
    loom(p, np.array([V(-.04, 0, -.064)] + belly), .0034, 2, 3)
    # ---- the stinger emitter
    e, d = spine[-1], tang[-1]
    sweep(p, [(.012, 0), (.03, 0), (.034, .02), (.026, .05), (.012, .05)], GRAPHITE, STEEL, rot=along(d), origin=e - d * .012)
    pipe(p, [e + d * .03, e + d * .105], .011, FRAME, STEEL, 12)
    for z in (.05, .064, .078):
        hoop(p, e + d * z, d, .0145, .004, BARE, STEEL, 16, 6)
    pipe(p, [e + d * .1, e + d * .122], .0085, glow(GLOW_AMBER, EMIT * 1.2), GLOW, 10)
    prism(p, e + d * .118, e + d * .2, .0065, BRIGHT, STEEL, 6, .8)
    mark(p, 'stinger', e + d * .2)
    # ---- the lift fans on their pylons, and the skids
    for s_ in (-1, 1):
        ax = unit(V(0, s_ * .2, 1))
        hub, R = V(.035, s_ * .262, .1), .105
        rotor(p, rng, hub, ax, R, 5, bone(rng))
        inn = unit(V(0, -s_, 0) - ax * np.dot(ax, V(0, -s_, 0)))        # toward the body, in the fan's plane
        wall = hub + inn * (R + .008)
        shoulder = thorax.point(1.42, math.radians(90 - s_ * 50), .004)
        strut(p, shoulder, wall, .05, .014, bone(rng), PAINT, up=ax, bevel=.004)
        pipe(p, [thorax.point(1.5, math.radians(90 - s_ * 84)), wall - ax * .02], .0045, FRAME, STEEL, 6)
        loom(p, curve([shoulder + V(-.03, 0, .006), (shoulder + wall) / 2 + V(-.032, 0, .012), wall + V(-.03, 0, .01) + ax * .01], 8), .0028, 1, 1)
        pivot(p, wall - inn * .004, V(1, 0, 0), .009, .07)
        skid = curve([V(.09, s_ * .05, -.05), V(.11, s_ * .078, -.118), V(.03, s_ * .082, -.124), V(-.05, s_ * .078, -.118), V(-.06, s_ * .05, -.045)], 14)
        pipe(p, skid, .004, BARE, STEEL, 6)
    return hover(p, .7, 501)


@built(.008)
def lancet():
    """SM_GE_Lancet (1.3 m): ranged. A long lance slung under a slim hull: a bolted breech with two recoil rams, a
    finned barrel root, a barrel banded like a ranging rod (one band is the unit's orange) and a four-edged lance head
    round the emitter. The amber lens is the hull's nose, above the barrel. Four swept stabiliser fins with trim tabs
    round a guarded thruster, canards, side intakes, two hover pods on outriggers."""
    rng = np.random.default_rng(502)
    p = Part('SM_GE_Lancet', (STEEL, PAINT, GLOW))
    t = .011
    hull = Hull((-.28, 0, .075), (.36, .105, .09), .78, .8, taper=(-.22, -.12))
    hull.core(p, GRAPHITE, STEEL, t * 1.5, (20, 28))
    for i, th in enumerate(((.62, 1.08), (1.08, 1.58), (1.58, 2.1), (2.1, 2.66))):
        b = plate(p, hull, th, _deg(35, 145), bone(rng), PAINT, t, .008, n=(4, 6), seed=i)
        hull.rivet_row(p, (b[0] + .05,) * 2, (b[2] + .14, b[3] - .14), 5, .0045, BARE, STEEL)
        for ph in (_deg(-40, 35), _deg(145, 220)):
            plate(p, hull, th, ph, bone(rng), PAINT, t, .008, n=(4, 3), seed=i + 7)
    plate(p, hull, (.66, 2.62), _deg(86.5, 93.5), FRAME, STEEL, t, 0.0, n=(8, 2), lift=t * .8)      # the spine: a frame rib along the top
    plate(p, hull, (.8, 2.5), _deg(222, 318), FRAME, STEEL, t, .01, n=(5, 4))
    hatch(p, hull, (1.14, 1.5), _deg(46, 80), bone(rng, .05), t * .5, 4)
    tag(p, hull.point(1.34, math.radians(-12), -t * .15), hull.normal(1.34, math.radians(-12)), (0, 0, 1), .045, .026)
    for a in (0.0, math.pi):
        louvre(p, hull.point(2.0, a, -t * .2), hull.normal(2.0, a), (0, 0, 1), .1, .036, 5)
    lug(p, hull.point(1.75, math.pi / 2, -t * .8), (0, 0, 1), .014, (0, 1, 0))
    whip = curve([hull.point(2.3, math.radians(70)), V(-.56, .05, .2), V(-.66, .06, .27), V(-.74, .06, .3)], 9)
    pipe(p, whip, np.linspace(.004, .0015, 9), GRAPHITE, STEEL, 5)
    # ---- the lens: the hull's nose
    eye(p, (.05, 0, .078), (1, 0, .03), .036, bezel=bone(rng, .05), hood=1.15, fasteners=8)
    sweep(p, [(.064, -.02), (.085, -.075), (.092, -.075), (.07, -.018)], GRAPHITE, STEEL, rot=along((1, 0, .03)), origin=(.05, 0, .078))
    for s_ in (-1, 1):
        sensor(p, (.03, s_ * .05, .03), (1, s_ * .5, -.5), .012)
    # ---- the lance, built along x under the hull
    o = V(-.3, 0, -.07)
    rot = along((1, 0, 0))

    def at(z, y=0.0, up=0.0):
        return o + V(z, y, up)
    obox(p, at(.05), (.085, .056, .05), FRAME, STEEL, .012)
    for s_ in (-1, 1):
        obox(p, at(.05, s_ * .058), (.07, .005, .04), bone(rng), PAINT, .003)
        bolts(p, [at(.05 + dx, s_ * .063, dz) for dx in (-.055, .055) for dz in (-.028, .028)], (0, s_, 0), .006)
    strut(p, at(.05, 0, .045), at(.05, 0, .095), .09, .05, GRAPHITE, STEEL, up=(0, 1, 0), bevel=.008)       # the breech hangs from the hull
    sweep(p, [(.03, .1), (.066, .1), (.07, .16), (.05, .2), (.03, .2)], GRAPHITE, STEEL, rot=rot, origin=o)
    for z in (.212, .228, .244):
        sweep(p, [(.024, z), (.046, z), (.046, z + .006), (.024, z + .006)], BARE, STEEL, rot=rot, origin=o)
    pipe(p, [at(.18), at(.92)], [.026, .02], FRAME, STEEL, S(.026, 16, 32))
    sweep(p, [(.025, .262), (.052, .262), (.052, .284), (.025, .284)], GRAPHITE, STEEL, rot=rot, origin=o)   # the rams' collar
    sweep(p, [(.024, .298), (.044, .298), (.044, .32), (.024, .32)], BARE, STEEL, rot=rot, origin=o)        # the hanger's clamp
    strut(p, at(.309, 0, .04), at(.309, 0, .1), .03, .02, FRAME, STEEL, up=(1, 0, 0), bevel=.005)
    for z0, z1, colour in ((.34, .46, bone(rng)), (.52, .62, ORANGE), (.68, .8, bone(rng))):
        rb = .026 - .006 * (z0 - .18) / .74 + .0006
        sweep(p, [(rb, z0), (rb + .009, z0 + .006), (rb + .009, z1 - .006), (rb, z1)], colour, PAINT, rot=rot, origin=o)
    sweep(p, [(.019, .885), (.034, .89), (.034, .91), (.019, .915)], glow(GLOW_AMBER, EMIT * 1.3), GLOW, rot=rot, origin=o)
    sweep(p, [(.019, .86), (.04, .86), (.04, .885), (.019, .885)], GRAPHITE, STEEL, rot=rot, origin=o)
    prism(p, at(.91), at(1.2), .04, BRIGHT, STEEL, 4, .8)
    mark(p, 'muzzle', at(1.2))
    for s_ in (-1, 1):
        ram(p, at(.1, s_ * .072), at(.273, s_ * .05), .009, pin=(0, 0, 1))
        obox(p, at(.1, s_ * .06), (.014, .012, .012), FRAME, STEEL, .003)
    loom(p, np.array([at(.12, 0, -.05)] + [at(z, 0, -.026 - .004) for z in np.linspace(.2, .86, 9)]), .0038, 2, 4)
    loom(p, curve([V(-.43, .035, .0), V(-.4, .04, -.03), V(-.36, .04, -.05), V(-.33, .04, -.06)], 7), .004, 2, 1)
    # ---- stabilisers: four swept fins with trim tabs round the thruster, and two canards
    thruster(p, (-.62, 0, .075), (-1, 0, 0), .05, .08, guard=True)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        d = V(0, math.cos(a), math.sin(a))
        c0, c1, c2, c3 = V(-.44, 0, .075), V(-.63, 0, .075), V(-.74, 0, .075), V(-.6, 0, .075)
        fin(p, [c0 + d * .085, c1 + d * .062, c2 + d * .33, c3 + d * .33], .014, bone(rng), PAINT, BARE, STEEL, n=(4, 4))
        fin(p, [c1 + d * .2 - (.012, 0, 0), c1 + d * .2 - (.055, 0, 0), c2 + d * .32 - (.05, 0, 0), c2 + d * .32 - (.004, 0, 0)], .008, FRAME, STEEL,
            BARE, STEEL, taper=.2, n=(2, 3))
        pipe(p, [c1 + d * .19 - (.008, 0, 0), c2 + d * .325 - (.002, 0, 0)], .0045, BARE, STEEL, 6)
        strut(p, c0 + d * .07 + (-.02, 0, 0), c1 + d * .055, .012, .03, GRAPHITE, STEEL, up=d, bevel=.003)       # the root fillet
    for s_ in (-1, 1):
        fin(p, [V(-.02, s_ * .075, .078), V(-.12, s_ * .088, .078), V(-.15, s_ * .2, .07), V(-.08, s_ * .2, .07)], .01, bone(rng), PAINT, BARE, STEEL)
        # the hover pods on their outriggers
        pod = V(-.33, s_ * .165, -.02)
        strut(p, V(-.33, s_ * .09, .04), pod + (0, -s_ * .03, .012), .035, .016, GRAPHITE, STEEL, bevel=.004)
        field(p, pod, (0, 0, -1), .042, shell=bone(rng))
        turn(p, [(.045, .008), (.04, .024), (.02, .034), (0, .036)], bone(rng), PAINT, 20, origin=pod, caps=(False, False))
    return hover(p, 1.3, 502)


@built(.02)
def burl():
    """SM_GE_Burl (2.0 m): heavy. A ball of overlapping enamel scales, like a bud: six rows hinged at their bases to the
    dark frame, each row's raised tips lapping the row in front, round a small amber lens at the front pole (one row's
    tips are the unit's orange band; one scale is lost, and the frame and a loom show). An engine deck at the back
    (thruster, vents), a hover field unit beneath, lifting eyes on top."""
    rng = np.random.default_rng(503)
    p = Part('SM_GE_Burl', (STEEL, PAINT, GLOW))
    body = Hull((0, 0, 0), (1.0, .98, .94), 1.0, 1.0)
    body.core(p, GRAPHITE, STEEL, .012, (24, 48))
    rows = [(.34, .86, 6), (.72, 1.26, 9), (1.1, 1.64, 11), (1.48, 2.02, 11), (1.86, 2.4, 10), (2.24, 2.74, 8)]     # tip, base (theta), scales
    tk, lift, lost = .034, .1, (4, 4)
    gap_at = None
    for i, (t_tip, t_base, count) in enumerate(rows):
        us = np.array([0, .25, .5, .7, .74, .88, 1.0]) if i == 3 else np.array([0, .28, .56, .8, 1.0])
        U, W = np.meshgrid(us, np.linspace(-1, 1, 5), indexing='ij')
        border = np.zeros(U.shape, bool)
        border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
        half = math.pi / count * 1.1
        for k in range(count):
            pc = (k + .5 * (i % 2)) / count * TAU
            tm = (t_tip + t_base) / 2
            if math.sin(tm) * math.sin(pc) < -.86:               # the hover unit's place
                continue
            if (i, k) == lost:
                gap_at = pc
                continue
            TH = t_base + (t_tip - t_base) * U * (1 - .16 * W ** 2 * U)
            PH = pc + W * half * (1 - .5 * U ** 2.4)
            up = lift * rng.uniform(.8, 1.15) * U ** 1.6 * (1 - .22 * W ** 2)
            outer = body.point(TH, PH, -(up + tk))
            rgb = np.tile(np.asarray(bone(rng))[:3], U.shape + (1,))
            if i == 3:
                rgb[U >= .74] = ORANGE[:3]
            chip = np.where(border, .6 * np.clip(.35 + .9 * noise2(outer[..., 0] * 23 + k, outer[..., 1] * 23 - outer[..., 2] * 19, 9 + i), 0, 1), 0.0)[..., None]
            rgb = rgb * (1 - chip) + np.asarray(CHIP[:3]) * chip
            slab(p, outer, body.point(TH, PH, -up), rgba(rgb).reshape(-1, 4), PAINT, BARE, STEEL)
            for q in (-.45, .45):                                 # hinge knuckles at the base, a fastener above each
                a, b = (body.point(t_base + .012, pc + (q + d) * half, -.02) for d in (-.13, .13))
                pipe(p, [a, b], .022, FRAME, STEEL, 8)
            T2, P2 = np.full(2, t_base + (t_tip - t_base) * .16), pc + np.array([-.45, .45]) * half
            studs(p, body.point(T2, P2, -(tk + lift * .05)), body.normal(T2, P2), .014)
    # ---- the lost scale: frame ribs, a loom and a junction box where it sat
    t_tip, t_base, count = rows[lost[0]]
    for d in (-.5, .5):
        plate(p, body, (t_tip + .06, t_base - .02), (gap_at + d * .2 - .025, gap_at + d * .2 + .025), FRAME, STEEL, .03, 0.0, n=(4, 2), lift=.03)
    loom(p, body.point(np.linspace(t_tip + .1, t_base - .04, 7), np.full(7, gap_at + .02), -.03), .012, 3, 2)
    c = body.point((t_tip + t_base) / 2, gap_at - .13, -.035)
    obox(p, c, (.035, .06, .08), FRAME, STEEL, .01, basis(body.normal((t_tip + t_base) / 2, gap_at - .13), (1, 0, 0)))
    # ---- the lens in its collar at the front pole
    plate(p, body, (.2, .44), (0.0, TAU), bone(rng, .06), PAINT, .03, .012, n=(2, 24), seed=3)
    eye(p, (.985, 0, 0), (1, 0, 0), .11, bezel=bone(rng, .05), fasteners=12)
    for a in (30, 150, 270):
        sensor(p, body.point(.33, math.radians(a), -.03), body.normal(.33, math.radians(a)), .028)
    # ---- the engine deck at the back
    plate(p, body, (2.78, 3.0), (0.0, TAU), FRAME, STEEL, .03, 0.0, n=(2, 20))
    thruster(p, (-.97, 0, 0), (-1, 0, 0), .2, .22, guard=True)
    for a in (45, 135, 225, 315):
        ar = math.radians(a)
        louvre(p, body.point(2.84, ar, -.032), body.normal(2.84, ar), V(0, math.cos(ar), math.sin(ar)), .16, .085, 4)
    tag(p, body.point(2.84, math.radians(90), -.034), body.normal(2.84, math.radians(90)), (0, 0, 1), .09, .05)
    # ---- lift: the field unit under it; lifting eyes between the scales on top
    sweep(p, [(.2, -.88), (.36, -.88), (.36, -1.0), (.2, -1.0)], GRAPHITE, STEEL)
    field(p, (0, 0, -1.03), (0, 0, -1), .3, shell=bone(rng), coils=10)
    for th in (1.26, 1.64):
        lug(p, body.point(th + .02, math.pi / 2, -.03), body.normal(th + .02, math.pi / 2), .05, (0, 1, 0))
    return hover(p, 2.0, 503)


def _stave(part, rng, rot, origin, width, z0, z1, thick, point=0.0, foot=0.0, band=None, crown=.012, seed=0):
    """A stave: a pressed enamelled plank standing in the local y-z plane and facing local +x, crowned across its
    face, its top drawn to a point `point` high (0: cut square), its foot cut in over `foot`. band (z from, to) is
    painted signal orange. Muddied toward the foot, chipped along its edges and at the point."""
    lo, hi = z0 + foot, z1 - point
    rows = {round(z0, 4), round(lo, 4), round(hi, 4), round(z1, 4)}
    rows |= {round(float(z), 4) for z in np.arange(lo + .2, hi - .05, .2)}
    if band:
        rows |= {round(z, 4) for z in (band[0] - .003, band[0], band[1], band[1] + .003) if lo < z < hi}
    if point:
        rows.add(round(z1 - point * .45, 4))
    zs = np.array(sorted(rows))
    wf = np.ones(len(zs))
    if foot:
        wf = np.where(zs < lo, .72 + .28 * (zs - z0) / foot, wf)
    if point:
        wf = np.where(zs > hi, np.interp(zs, [hi, z1 - point * .45, z1], [1.0, .55, .1]), wf)
    ys = np.array([-.5, -.25, 0, .25, .5])
    Y = wf[:, None] * width * ys[None, :]
    Z = np.repeat(zs[:, None], 5, 1)
    front = thick / 2 + crown * wf[:, None] * (1 - (2 * ys[None, :]) ** 2)
    outer = np.stack([front, Y, Z], -1) @ rot.T + origin
    inner = np.stack([np.full(Y.shape, -thick / 2), Y, Z], -1) @ rot.T + origin
    base = np.asarray(bone(rng))[:3]
    k = (.78 + .22 * ease((Z - z0) / .5)) * (.95 + .08 * noise2(Y * 9 + seed * 3.3, Z * 4, seed + 2))
    rgb = base[None, None, :] * k[..., None]
    if band:
        rgb[(Z >= band[0] - 1e-6) & (Z <= band[1] + 1e-6)] = ORANGE[:3]
    chip = np.zeros(Y.shape)
    chip[:, 0] = chip[:, -1] = .55
    chip *= np.clip(.3 + noise2(Z * 14 + seed, Y * 3, seed + 5), 0, 1)
    if point:
        chip = np.maximum(chip, .5 * np.clip((Z - (z1 - point * .5)) / (point * .5), 0, 1))
    rgb = rgb * (1 - chip[..., None]) + np.asarray(CHIP[:3]) * chip[..., None]
    slab(part, outer, inner, rgba(rgb).reshape(-1, 4), PAINT, tone(base, .5), PAINT)


@built(.012)
def palisade():
    """SM_GE_Palisade (1.9 m tall): a tall shield of seven pointed staves bolted to two curved rails, carried ahead of
    the body on four hinged arms with rams; the three middle staves are cut through to leave a slit, and the amber lens
    looks through it from the end of a boom. One orange band is painted across the staves. Behind: a plated body, two
    guarded thrusters, a hover field unit."""
    rng = np.random.default_rng(504)
    p = Part('SM_GE_Palisade', (STEEL, PAINT, GLOW))
    ctr, R, tk = V(-.3, 0, 0), .8, .044
    tops, feet = [.72, .86, .95, .98, .95, .86, .72], [-.74, -.84, -.9, -.92, -.9, -.84, -.74]
    slit, rails = (.1, .24), (-.5, .6)
    for k in range(7):
        a = math.radians((k - 3) * 15.0)
        out, tan_ = V(math.cos(a), math.sin(a), 0), V(-math.sin(a), math.cos(a), 0)
        rot, origin = np.stack([out, tan_, UP], 1), ctr + V(math.cos(a), math.sin(a), 0) * R
        pieces = [(feet[k], slit[0], 0.0, .05), (slit[1], tops[k], .14, 0.0)] if 2 <= k <= 4 else [(feet[k], tops[k], .14, .05)]
        for z0, z1, point, foot in pieces:
            _stave(p, rng, rot, origin, .2, z0, z1, tk, point, foot, (-.3, -.18), seed=k)
        for z in rails:
            bolts(p, [origin + out * (tk / 2 + .008) + tan_ * s_ * .05 + UP * z for s_ in (-1, 1)], out, .013)
    for z in rails:
        sweep(p, [(R - .085, z - .032), (R - tk / 2 - .002, z - .032), (R - tk / 2 - .002, z + .032), (R - .085, z + .032)], FRAME, STEEL,
              math.radians(-50), math.radians(50), sides=40, origin=ctr)
    for s_ in (-1, 1):                                             # lifting eyes on the upper rail's ends
        a = math.radians(47.0) * s_
        lug(p, ctr + V(math.cos(a), math.sin(a), 0) * (R - .055) + UP * (rails[1] + .032), (0, 0, 1), .028, V(math.cos(a), math.sin(a), 0))
    # ---- the body behind the shield
    body = Hull((-.42, 0, 0), (.34, .33, .42), .72, .7)
    t = .02
    body.core(p, GRAPHITE, STEEL, t * 1.5, (16, 32))
    for i, th in enumerate(((.55, 1.2), (1.2, 1.9), (1.9, 2.6))):
        for j, ph in enumerate((_deg(-28, 28), _deg(28, 90), _deg(90, 152), _deg(152, 208))):
            b = plate(p, body, th, ph, bone(rng), PAINT, t, .012, n=(3, 3), seed=i * 4 + j)
            if j in (1, 2):
                body.rivet_row(p, (b[0] + .06,) * 2, (b[2] + .1, b[3] - .1), 4, .007, BARE, STEEL)
        plate(p, body, th, _deg(208, 332), FRAME, STEEL, t, .012, n=(3, 4))
    hatch(p, body, (1.3, 1.8), _deg(100, 142), bone(rng, .05), t * .5, 5)
    for a in (0.0, math.pi):
        louvre(p, body.point(1.55, a, -t * .2), body.normal(1.55, a), (0, 0, 1), .16, .1, 5)
    for th in (1.2, 1.9):
        lug(p, body.point(th, math.pi / 2, -t * .2), (0, 0, 1), .03, (0, 1, 0))
    tag(p, body.point(2.2, math.radians(15), -t * .15), body.normal(2.2, math.radians(15)), (0, 0, 1), .07, .04)
    for s_ in (-1, 1):
        thruster(p, (-.73, s_ * .14, .06), (-1, 0, 0), .075, .1, guard=True)
    sweep(p, [(.12, -.36), (.2, -.36), (.2, -.44), (.12, -.44)], GRAPHITE, STEEL, origin=(-.42, 0, 0))
    field(p, (-.42, 0, -.46), (0, 0, -1), .19, shell=bone(rng))
    # ---- the lens on its boom, looking through the slit
    strut(p, (-.12, 0, .17), (.37, 0, .17), .09, .07, FRAME, STEEL, bevel=.012)
    obox(p, (.12, 0, .209), (.2, .04, .006), bone(rng), PAINT, .003)
    studs(p, [(.12 + dx, dy, .215) for dx in (-.18, 0, .18) for dy in (-.03, .03)], (0, 0, 1), .006)
    pivot(p, (.375, 0, .17), (0, 1, 0), .034, .15)
    eye(p, (.44, 0, .17), (1, 0, 0), .055, bezel=bone(rng, .05), hood=1.3, fasteners=8)
    for s_ in (-1, 1):
        strut(p, (.39, s_ * .06, .17), (.42, s_ * .17, .17), .028, .028, FRAME, STEEL, bevel=.006)
        sensor(p, (.436, s_ * .17, .17), (1, 0, 0), .02)
    loom(p, curve([(-.1, .045, .2), (.05, .058, .185), (.2, .058, .185), (.34, .05, .19)], 8), .006, 2, 2)
    # ---- the arms: body pivot, boom with its cover, rail pivot, and a ram to swing each
    for s_ in (-1, 1):
        for z in rails:
            a = math.radians(34.0) * s_
            out = V(math.cos(a), math.sin(a), 0)
            hand = ctr + out * (R - .125) + UP * z
            sh = V(-.2, s_ * .3, z * .7)
            pivot(p, sh, (0, 0, 1), .04, .12)
            strut(p, sh, hand, .07, .05, FRAME, STEEL, bevel=.01)
            obox(p, (sh + hand) / 2 + (0, 0, .028), (norm(hand - sh) * .3, .028, .005), bone(rng), PAINT, .003, basis(hand - sh))
            pivot(p, hand, (0, 0, 1), .032, .1)
            obox(p, hand + out * .03, (.03, .03, .03), FRAME, STEEL, .008, np.stack([out, np.cross(UP, out), UP], 1))
            ram(p, V(-.3, s_ * .2, z * .7), sh + (hand - sh) * .6 - V(0, s_ * .02, 0), .016, pin=(0, 0, 1))
    return hover(p, 1.9, 504)


@built(.016)
def thresher():
    """SM_GE_Thresher (2.5 m across its arms): a guard. An upright plated drum with the unit's orange band round its
    waist, the amber lens in its front; on top a rotor crown, six scimitar blades in cuffs on a hub with its swashplate
    and pitch links; at its flanks two arms (shoulder bearing, boom, elbow pin, forearm, wrist clamp, rams and hoses)
    that each carry a long scythe blade. A power pack and a guarded thruster behind, a hover field unit on a tail cone."""
    rng = np.random.default_rng(505)
    p = Part('SM_GE_Thresher', (STEEL, PAINT, GLOW))
    upright = basis((0, 0, 1), (1, 0, 0))      # local x up; phi 90 degrees faces forward (+x), 0 is -y, 180 is +y
    body = Hull((0, 0, 0), (.52, .36, .34), .8, .8, upright)
    t = .022
    body.core(p, GRAPHITE, STEEL, t * 1.5, (20, 36))
    sectors = [(-10, 50), (50, 130), (130, 190), (190, 250), (250, 290), (290, 350)]
    for i, th in enumerate(((.45, 1.2), (1.2, 1.74))):
        for j, (a, b) in enumerate(sectors):
            bx = plate(p, body, th, _deg(a, b), bone(rng), PAINT, t, .012, n=(3, 3), seed=i * 6 + j)
            if i == 0:
                body.rivet_row(p, (bx[1] - .06,) * 2, (bx[2] + .1, bx[3] - .1), 4, .007, BARE, STEEL)
    plate(p, body, (1.74, 1.9), (0.0, TAU), ORANGE, PAINT, t, .012, n=(2, 28), seed=40)
    for a, b in sectors:
        plate(p, body, (1.9, 2.6), _deg(a, b), FRAME, STEEL, t, .012, n=(3, 3))
    for a in (20, 160, 270):
        ar = math.radians(a)
        louvre(p, body.point(2.25, ar, -t * .2), body.normal(2.25, ar), (0, 0, 1), .16, .1, 5)
    hatch(p, body, (.62, 1.06), _deg(140, 180), bone(rng, .05), t * .5, 6)
    tag(p, body.point(1.48, math.radians(40), -t * .15), body.normal(1.48, math.radians(40)), (0, 0, 1), .07, .04)
    n_eye = body.normal(1.22, math.pi / 2)
    eye(p, body.point(1.22, math.pi / 2) - n_eye * .012, n_eye, .095, bezel=bone(rng, .05), hood=1.2, fasteners=10)
    for a in (76, 104):
        sensor(p, body.point(1.63, math.radians(a), -t * .1), body.normal(1.63, math.radians(a)), .026)
    # ---- the rotor crown: mast, swashplate with its three servos, hub, six blades in cuffs with pitch links
    top = .5
    pipe(p, [(0, 0, top - .05), (0, 0, .78)], .05, FRAME, STEEL, S(.05, 12, 24))
    sweep(p, [(.05, top - .02), (.17, top - .02), (.17, top + .012), (.05, top + .04)], GRAPHITE, STEEL)
    ang = (np.arange(8) + .5) / 8 * TAU
    bolts(p, np.stack([.135 * np.cos(ang), .135 * np.sin(ang), np.full(8, top + .016)], 1), (0, 0, 1), .012)
    sweep(p, [(.05, .6), (.126, .6), (.126, .622), (.05, .622)], BARE, STEEL)
    sweep(p, [(.05, .628), (.118, .628), (.118, .652), (.05, .652)], FRAME, STEEL)
    for k in range(3):
        a = k / 3 * TAU + .5
        ram(p, (.135 * math.cos(a), .135 * math.sin(a), top + .03), (.105 * math.cos(a), .105 * math.sin(a), .6), .011)
    sweep(p, [(.03, .72), (.1, .72), (.1, .8), (.03, .8)], GRAPHITE, STEEL)
    turn(p, [(.1, .8), (.085, .83), (.05, .852), (0, .86)], bone(rng, .05), PAINT, 24, caps=(False, False))
    for s_ in (-1, 1):
        lug(p, (-.02, s_ * .22, body.point(.48, 0.0)[2] + .0), (0, 0, 1), .03, (1, 0, 0))
    span = np.linspace(0, 1, 12)
    for k in range(6):
        a = k / 6 * TAU + .26
        u, tn = V(math.cos(a), math.sin(a), 0), V(-math.sin(a), math.cos(a), 0)
        pipe(p, [u * .09 + (0, 0, .76), u * .25 + (0, 0, .76)], .034, BARE, STEEL, 12)
        pipe(p, [u * .1 + tn * .05 + (0, 0, .652), u * .2 + tn * .045 + (0, 0, .752)], .006, BRIGHT, STEEL, 5)
        obox(p, u * .2 + tn * .035 + (0, 0, .76), (.02, .02, .012), FRAME, STEEL, .004, np.stack([u, tn, UP], 1))
        spine = np.array([u * (.22 + .72 * q) - tn * (.05 + .2 * q * q) + (0, 0, .76 + .14 * q ** 1.5) for q in span])
        fl.blade(p, spine, (.13 + .06 * np.sin(2.6 * span)) * (1 - span ** 3.5) + .012, np.linspace(.022, .006, 12), (0, 0, 1), FRAME, BRIGHT)
    # ---- the scythe arms
    for s_ in (-1, 1):
        sh, el, wr = V(0, s_ * .39, .16), V(.1, s_ * .93, -.2), V(.52, s_ * 1.1, .02)
        side = V(0, s_, 0)
        pivot(p, sh - side * .03, side, .1, .13)
        sweep(p, [(.1, 0), (.155, 0), (.155, .03), (.1, .03)], FRAME, STEEL, rot=along(side), origin=sh - side * .1)
        ang = (np.arange(8) + .5) / 8 * TAU
        bolts(p, sh - side * .07 + np.stack([.13 * np.cos(ang), np.zeros(8), .13 * np.sin(ang)], 1), side, .012)
        hinge_ = unit(np.cross(el - sh, wr - el))
        for a, b, w, h, cover in ((sh, el, .15, .16, .34), (el, wr, .115, .125, .32)):
            f = unit(b - a)
            up = unit(np.cross(f, hinge_))
            strut(p, a, b, w, h, FRAME, STEEL, up=up, bevel=.018)
            mid = (a + b) / 2
            for sg in (-1, 1):                                    # enamel covers on both cheeks of the boom
                obox(p, mid + hinge_ * sg * (w / 2 + .004), (norm(b - a) * cover, .006, h * .36), bone(rng), PAINT, .004, basis(f, up) @ np.eye(3))
            studs(p, [mid + hinge_ * (w / 2 + .011) + f * dx * norm(b - a) * cover * .88 + up * dz * h * .26 for dx in (-1, 1) for dz in (-1, 1)],
                  hinge_, .008)
        pivot(p, el, hinge_, .082, .23)
        up_arm = unit(np.cross(unit(el - sh), hinge_))
        ram(p, V(-.02, s_ * .3, -.22), sh + (el - sh) * .62 - up_arm * .1, .028, pin=(1, 0, 0))
        fore = unit(wr - el)
        up_fore = unit(np.cross(fore, hinge_))
        ram(p, sh + (el - sh) * .3 + up_arm * .12, el + fore * .2 + up_fore * .095, .023, pin=hinge_)
        hose(p, curve([sh + V(.03, 0, .1), sh + (el - sh) * .5 + up_arm * .09 + hinge_ * .04, el + up_arm * .12, el + fore * .22 + up_fore * .07 + hinge_ * .03], 12), .009)
        # the wrist: a turning collar and a clamp bolted over the blade's tang
        sweep(p, [(.06, -.045), (.092, -.045), (.092, .045), (.06, .045)], GRAPHITE, STEEL, rot=along(fore), origin=wr)
        flat = unit(V(0, .45, -.9 * s_))                          # the blade's flat
        grip = np.stack([fore, np.cross(flat, fore), flat], 1)
        obox(p, wr + fore * .1, (.08, .1, .03), FRAME, STEEL, .01, grip)
        for sg in (-1, 1):
            bolts(p, [wr + fore * (.1 + dx) + flat * sg * .03 for dx in (-.045, 0, .045)], flat * sg, .014)
        edge = bezier(wr + fore * .12, wr + V(.42, s_ * .04, .1), V(1.2, s_ * .62, -.12), V(1.02, s_ * .2, -.72), 16)
        q = np.linspace(0, 1, 16)
        fl.blade(p, edge, np.interp(q, [0, .25, .7, 1], [.15, .25, .17, .015]), np.linspace(.038, .009, 16), flat, BARE, BRIGHT)
        pipe(p, edge[:11], np.linspace(.021, .009, 11), GRAPHITE, STEEL, 8)
    # ---- behind and below: the power pack, the thruster, the hover unit on its tail cone
    obox(p, (-.33, 0, .02), (.09, .2, .22), FRAME, STEEL, .02)
    louvre(p, (-.425, 0, .08), (-1, 0, 0), (0, 0, 1), .28, .16, 6)
    for s_ in (-1, 1):
        pipe(p, [(-.36, s_ * .12, .22), (-.38, s_ * .13, .36)], [.03, .026], BARE, STEEL, 12)
        hoop(p, (-.38, s_ * .13, .36), (-.14, s_ * .07, 1), .027, .006, GRAPHITE, STEEL, 12, 5)
    thruster(p, (-.36, 0, -.33), (-1, 0, -.35), .085, .11, guard=True)
    turn(p, [(.14, -.76), (.2, -.62), (.27, -.47)], GRAPHITE, STEEL, 32, caps=(True, False))
    for k in range(6):
        a = k / 6 * TAU
        strut(p, (.15 * math.cos(a), .15 * math.sin(a), -.75), (.275 * math.cos(a), .275 * math.sin(a), -.47), .03, .02, FRAME, STEEL,
              up=(math.cos(a), math.sin(a), .4), bevel=.005)
    field(p, (0, 0, -.79), (0, 0, -1), .15, shell=bone(rng))
    loom(p, curve([(-.3, .1, -.2), (-.2, .16, -.42), (-.1, .13, -.6), (-.05, .1, -.74)], 10), .008, 3, 2)
    return hover(p, 2.5, 505)


@built(.01)
def emitter():
    """SM_GE_Emitter (1.2 m): a fixed shield emitter, a target for the sidearm. The amber core (the brightest light,
    on the mesh's centre) sits in a collar that clamps a cluster of dimly lit prisms, six fanned forward and six back;
    the collar hangs by four spokes in the inner ring of a gimbal, whose outer ring turns in a yoke with a motor on each
    trunnion; under the yoke a drum and a hover field unit hold it in place. One orange band round the collar."""
    rng = np.random.default_rng(506)
    p = Part('SM_GE_Emitter', (STEEL, PAINT, GLOW))
    ax = along((1, 0, 0))                       # local x is world y, local y world z, local z world x: rings face x
    sweep(p, [(.47, -.035), (.53, -.035), (.545, 0), (.53, .035), (.47, .035), (.455, 0)], GRAPHITE, STEEL, sides=48, rot=ax)
    for k in range(4):
        a0 = math.radians(45 + 90 * k - 28)
        sweep(p, [(.545, -.034), (.562, -.03), (.562, .03), (.545, .034)], bone(rng), PAINT, a0, a0 + math.radians(56), sides=10, rot=ax)
    sweep(p, [(.385, -.028), (.425, -.028), (.435, 0), (.425, .028), (.385, .028)], bone(rng), PAINT, sides=48, rot=ax)
    for s_ in (-1, 1):
        pivot(p, (0, 0, s_ * .45), (0, 0, 1), .034, .075)
        pivot(p, (0, s_ * .59, 0), (0, 1, 0), .045, .13)
        pipe(p, [(0, s_ * .665, 0), (0, s_ * .76, 0)], .058, FRAME, STEEL, 20)                # the pitch motors
        sweep(p, [(.03, 0), (.062, 0), (.062, .012), (.03, .012)], BARE, STEEL, sides=20, rot=along((0, s_, 0)), origin=(0, s_ * .76, 0))
        loom(p, curve([(0, s_ * .72, -.06), (.0, s_ * .7, -.2), (0, s_ * .58, -.42), (0, s_ * .3, -.62), (0, s_ * .14, -.68)], 12)
             + V(.04, 0, 0), .007, 2, 3)
    pipe(p, [(0, 0, .535), (0, 0, .62)], .045, FRAME, STEEL, 16)                             # the yaw motor on the crown
    hoop(p, (0, 0, .58), (0, 0, 1), .047, .006, BARE, STEEL, 16, 5)
    # ---- the yoke under the rings, its drum and hover unit
    sweep(p, [(.615, -.032), (.675, -.032), (.675, .032), (.615, .032)], FRAME, STEEL, math.pi, TAU, sides=40, rot=ax)
    for a0, a1 in ((math.pi + .22, 1.5 * math.pi - .2), (1.5 * math.pi + .2, TAU - .22)):
        sweep(p, [(.675, -.028), (.688, -.024), (.688, .024), (.675, .028)], bone(rng), PAINT, a0, a1, sides=14, rot=ax)
    pipe(p, [(0, 0, -.66), (0, 0, -.84)], .17, FRAME, STEEL, 32)
    sweep(p, [(.17, -.8), (.182, -.795), (.182, -.715), (.17, -.71)], bone(rng), PAINT, sides=32)
    for a in (0.0, math.pi):
        louvre(p, (.176 * math.cos(a), 0, -.755), (math.cos(a), 0, 0), (0, 0, 1), .12, .05, 4)
    tag(p, (0, .183, -.755), (0, 1, 0), (0, 0, 1), .07, .04)
    field(p, (0, 0, -.86), (0, 0, -1), .16, shell=bone(rng))
    # ---- the core in its collar, the prisms, the spokes
    start = ball(p, (0, 0, 0), .14, GLOW_AMBER, GLOW, 28)
    v = np.asarray(p.v[start:], np.float64)
    p.c[start:] = glow(GLOW_AMBER, LENS * (.82 + .18 * np.clip(v[:, 0] / .14, -1, 1))).tolist()
    mark(p, 'lens', (.14, 0, 0))
    mark(p, 'core', (0, 0, 0))
    sweep(p, [(.165, -.045), (.212, -.045), (.22, 0), (.212, .045), (.165, .045)], bone(rng, .06), PAINT, sides=36, rot=ax)
    sweep(p, [(.214, -.02), (.2262, -.016), (.2262, .016), (.214, .02)], ORANGE, PAINT, sides=36, rot=ax)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        d = V(0, math.cos(a), math.sin(a))
        strut(p, d * .212, d * .392, .03, .022, FRAME, STEEL, up=(1, 0, 0), bevel=.005)
        bolts(p, [d * .19 + V(sg * .047, 0, 0) for sg in (-1, 1)], [V(sg, 0, 0) for sg in (-1, 1)], .011)
    for front in (True, False):
        for k in range(6):
            a = k / 6 * TAU + (.3 if front else .82)
            d = V(0, math.cos(a), math.sin(a))
            axis = unit(V(1.0, 0, 0) + d * .32) if front else unit(V(-1.0, 0, 0) + d * .42)
            base = d * .158 + axis * .02
            L, r = (.42, .05) if front else (.27, .04)
            start = prism(p, base, base + axis * L, r, GLOW_AMBER, GLOW, 6, .35)
            v = np.asarray(p.v[start:], np.float64)
            p.c[start:] = glow(GLOW_AMBER, EMIT * (.8 - .55 * np.clip((v - base) @ axis / L, 0, 1))).tolist()
            pipe(p, [base - axis * .012, base + axis * .03], r * 1.12, BARE, STEEL, 6)       # the ferrule its root sits in
    for k, z in enumerate((-.075, -.105, -.135)):                                           # cooling plates behind the core
        r = .12 - .018 * k
        sweep(p, [(.03, z), (r, z), (r, z + .012), (.03, z + .012)], BARE, STEEL, sides=24, rot=ax)
    pipe(p, [(-.05, 0, 0), (-.17, 0, 0)], .034, GRAPHITE, STEEL, 12)
    loom(p, curve([(-.16, 0, .02), (-.14, .05, .16), (-.06, .08, .3), (-.03, .06, .385)], 9), .006, 2, 1)
    return hover(p, 1.2, 506)


def _tower_shield(part, rng, centre, normal, width, height, thick):
    """A Warden's arm shield, facing `normal`: a heater-shaped slab bowed round its height, enamel with a steel rim,
    two raised bands across it, fasteners down both edges, and its mounting rails behind."""
    c = np.asarray(centre, np.float64)
    rot = basis(normal)                                    # local x out of the face, y across, z up
    us, zs = np.linspace(-1, 1, 9), np.linspace(-.5, .5, 15) * height
    wf = np.interp(zs / height, [-.5, -.34, -.1, .36, .5], [.22, .7, 1.0, 1.0, .8])
    Y, Z = wf[:, None] * us[None, :] * width / 2, np.repeat(zs[:, None], 9, 1)
    bow = width * .09 * (1 - us[None, :] ** 2) * wf[:, None] + height * .02 * (1 - (2 * Z / height) ** 2)
    chip = np.zeros(Y.shape)
    chip[:, 0] = chip[:, -1] = chip[0, :] = chip[-1, :] = .6
    chip *= np.clip(.3 + noise2(Z * 3 + c[1], Y * 3, 7), 0, 1)
    base = np.asarray(bone(rng))[:3]
    rgb = base * (1 + .06 * noise2(Y * 2.1, Z * 2.1, 3))[..., None] * (1 - chip[..., None]) + np.asarray(CHIP[:3]) * chip[..., None]
    outer = np.stack([bow + thick / 2, Y, Z], -1) @ rot.T + c
    slab(part, outer, np.stack([bow - thick / 2, Y, Z], -1) @ rot.T + c, rgba(rgb).reshape(-1, 4), PAINT, BARE, STEEL)
    for zb in (-.12, .27):                                  # raised bands across the face
        z2 = np.array([zb - .03, zb + .03]) * height
        w2 = np.interp(z2 / height, [-.5, -.34, -.1, .36, .5], [.22, .7, 1.0, 1.0, .8])
        Y2, Z2 = w2[:, None] * us[None, :] * width / 2 * .98, np.repeat(z2[:, None], 9, 1)
        b2 = width * .09 * (1 - us[None, :] ** 2) * w2[:, None] + height * .02 * (1 - (2 * Z2 / height) ** 2) + thick / 2
        slab(part, np.stack([b2 + thick * .3, Y2, Z2], -1) @ rot.T + c, np.stack([b2 - .01, Y2, Z2], -1) @ rot.T + c, FRAME, STEEL)
    for col in (1, 7):
        studs(part, outer[2:13, col], rot[:, 0], thick * .2)
    for sg in (-1, 1):                                      # the rails it is carried by
        strut(part, c + rot @ V(-thick * 1.2, sg * width * .2, -height * .3), c + rot @ V(-thick * 1.2, sg * width * .2, height * .34), thick * .9,
              thick * 1.4, FRAME, STEEL, up=rot[:, 0], bevel=thick * .15)
    strut(part, c + rot @ V(-thick * 1.9, -width * .24, 0), c + rot @ V(-thick * 1.9, width * .24, 0), thick * 1.1, thick * 1.2, FRAME, STEEL,
          up=rot[:, 0], bevel=thick * .15)


def _prism_head(part, rng, c, axis, r):
    """An emitter head: a dim amber core in an enamel collar that clamps six prisms fanned forward, on a finned motor."""
    c, ax = np.asarray(c, np.float64), unit(axis)
    rot = along(ax)
    ball(part, c, r * .62, glow(GLOW_AMBER, EMIT), GLOW, S(r * .62, 12, 28))
    sweep(part, [(r * .72, -r * .22), (r * .95, -r * .22), (r, 0), (r * .95, r * .22), (r * .72, r * .22)], bone(rng), PAINT, rot=rot, origin=c)
    for k in range(6):
        a = k / 6 * TAU + .3
        d = rot @ V(math.cos(a), math.sin(a), 0)
        axis_k = unit(ax + d * .3)
        base = c + d * r * .7 + axis_k * r * .1
        L = r * 1.9
        start = prism(part, base, base + axis_k * L, r * .22, GLOW_AMBER, GLOW, 6, .35)
        v = np.asarray(part.v[start:], np.float64)
        part.c[start:] = glow(GLOW_AMBER, EMIT * (.8 - .55 * np.clip((v - base) @ axis_k / L, 0, 1))).tolist()
        pipe(part, [base - axis_k * r * .06, base + axis_k * r * .14], r * .25, BARE, STEEL, 6)
    pipe(part, [c - ax * r * .2, c - ax * r * 1.3], [r * .6, r * .5], GRAPHITE, STEEL, S(r * .6, 12, 28))
    for z in (.5, .72, .94):
        sweep(part, [(r * .5, -r * z), (r * .78, -r * z), (r * .78, -r * (z + .07)), (r * .5, -r * (z + .07))], BARE, STEEL, rot=rot, origin=c)


@built(.06)
def warden():
    """SM_GE_Warden (7.5 m tall): the boss. An armoured torso on a slewing ring over a banded stem and a ring base (a
    railed catwalk on six hover field units); the great amber eye high in its chest at +x, under a brow; a collar of
    five shield segments on brackets and rams round its front, carrying the unit's orange band; two lower arms with
    tower shields, two upper arms with prism emitter heads; a crown of nine fins round a dim amber ring. At its back
    (-x) a window in the armour bares the coupling: a copper coil, bus bars on insulators and conduits (BRASS slot) round
    a core of resonance-green light, which reads as the vulnerable part."""
    rng = np.random.default_rng(507)
    p = Part('SM_GE_Warden', (STEEL, PAINT, GLOW, BRASS))
    upright = basis((0, 0, 1), (1, 0, 0))      # local x up; phi 90 degrees is +x (front), 0 is -y, 180 is +y, 270 is -x (back)
    torso = Hull((0, 0, .6), (1.75, 1.36, 1.16), .72, .68, upright, taper=(.24, .16))
    t = .05
    torso.core(p, GRAPHITE, STEEL, t * 1.5, (28, 56))
    bands_ = ((.42, .9), (.9, 1.4), (1.4, 1.9), (1.9, 2.4), (2.4, 2.82))
    sectors = ((-20, 20), (20, 60), (60, 120), (120, 160), (160, 200), (200, 240), (240, 300), (300, 340))
    for i, th in enumerate(bands_):
        for j, (a, b) in enumerate(sectors):
            if (j == 2 and i in (0, 1)) or (j == 6 and i == 2):       # the eye's place; the coupling's window
                continue
            colour, slot = bone(rng), PAINT
            bx = plate(p, torso, th, _deg(a, b), colour, slot, t, .03, n=(3, 3), sag=.12, seed=i * 8 + j)
            for th_r in (bx[0] + .04, bx[1] - .04):
                torso.rivet_row(p, (th_r,) * 2, (bx[2] + .07, bx[3] - .07), 4, .02, BARE, STEEL)

    def side(th, phi_deg, depth=0.0):
        return torso.point(th, math.radians(phi_deg), depth)

    def out(th, phi_deg):
        return torso.normal(th, math.radians(phi_deg))
    for phi in (40, 140):
        hatch(p, torso, (2.0, 2.3), _deg(phi - 14, phi + 14), bone(rng, .05), t * .5, phi)
    for phi in (0, 180, 222, 318):
        louvre(p, side(2.15, phi, -t * .2), out(2.15, phi), (0, 0, 1), .5, .3, 6)
    tag(p, side(1.62, 62, -t * .15), out(1.62, 62), (0, 0, 1), .26, .15)
    for phi in (30, 150):
        lug(p, side(.6, phi, -t * .2), out(.6, phi), .09, (1, 0, 0))
    for k in range(9):                                            # rungs up its left back, for whoever served it
        th = 2.55 - k * .16
        a, b = side(th, 215, -.02), side(th, 229, -.02)
        n_ = out(th, 222) * .14
        pipe(p, [a, a + n_, b + n_, b], .02, BARE, STEEL, 6)
    # ---- the great eye
    ec = side(1.05, 90) - V(.1, 0, 0)
    eye(p, ec, (1, 0, -.1), .46, bezel=bone(rng, .05), hood=1.2, fasteners=16)
    for phi, th in ((48, 1.0), (132, 1.0), (52, 1.32), (128, 1.32)):
        sensor(p, side(th, phi, -t * .3), out(th, phi), .075)
    # ---- the collar: five shield segments round the front, each on two brackets and a ram
    for k in range(5):
        mid = math.radians((k - 2) * 40.0)
        a0, a1 = mid - math.radians(18), mid + math.radians(18)
        sweep(p, [(1.72, -.6), (1.84, -.6), (1.93, -.05), (1.9, .44), (1.8, .52), (1.72, .46)], bone(rng), PAINT, a0, a1, sides=10,
              bands={0: (BARE, STEEL), 3: (BARE, STEEL)})
        sweep(p, [(1.917, .16), (1.932, .165), (1.921, .335), (1.906, .34)], ORANGE, PAINT, a0 + .01, a1 - .01, sides=10)
        aa = np.linspace(a0 + .05, a1 - .05, 6)
        for z, r in ((.38, 1.905), (-.5, 1.86)):
            studs(p, np.stack([r * np.cos(aa), r * np.sin(aa), np.full(6, z)], 1), np.stack([np.cos(aa), np.sin(aa), np.zeros(6)], 1), .022)
        for da in (-10.0, 10.0):
            phi = math.degrees(mid) + da
            root_ = side(1.86, 90 + phi)
            u = V(math.cos(math.radians(phi)), math.sin(math.radians(phi)), 0)
            tip = u * 1.7 + (0, 0, root_[2] + .05)
            strut(p, root_, tip, .12, .1, FRAME, STEEL, bevel=.02)
            pivot(p, tip, np.cross(UP, u), .06, .17)
        u = V(math.cos(mid), math.sin(mid), 0)
        ram(p, side(2.14, 90 + math.degrees(mid), .02), u * 1.7 + (0, 0, .24), .045, pin=np.cross(UP, u))
    # ---- arms: shoulder bearings, then the shield arms (low) and the emitter arms (high)
    for s_ in (-1, 1):
        for sh, el, wr, w, anchor in ((V(.15, s_ * 1.46, .2), V(1.0, s_ * 2.28, -.35), V(1.75, s_ * 2.25, .15), .32, V(0, s_ * 1.05, -.6)),
                                      (V(-.05, s_ * 1.56, 1.72), V(-.1, s_ * 2.36, 2.5), V(.62, s_ * 2.56, 2.86), .28, V(-.3, s_ * 1.1, 1.0))):
            lateral = V(0, s_, 0)
            pivot(p, sh - lateral * .14, lateral, w * .95, w * 1.2)
            sweep(p, [(w * .95, 0), (w * 1.4, 0), (w * 1.4, w * .22), (w * .95, w * .22)], FRAME, STEEL, rot=along(lateral), origin=sh - lateral * (w * .75 + .14))
            ang = (np.arange(10) + .5) / 10 * TAU
            bolts(p, sh - lateral * (w * .53 + .14) + np.stack([w * 1.18 * np.cos(ang), np.zeros(10), w * 1.18 * np.sin(ang)], 1), lateral, w * .07)
            hinge_, fore = arm(p, rng, sh, el, wr, w, anchor)
            hose(p, curve([sh + V(.05, 0, w * .9), (sh + el) / 2 + V(0, 0, w * 1.1), el + V(0, 0, w * 1.0), el + fore * .5 + V(0, 0, w * .7)], 12), w * .08)
            pivot(p, wr, hinge_, w * .42, w * 1.25)
            cap = Hull(sh + lateral * .12, (w * 1.75, w * 1.6, w * 1.75), .8, .8, basis(lateral, (0, 0, 1)))     # the pauldron over the bearing
            for q, (a, b) in enumerate(((20, 90), (90, 160))):
                bx = plate(p, cap, (.3, 1.5), _deg(a, b), bone(rng), PAINT, t, .03, n=(3, 3), sag=.12, back=True, seed=70 + q)
                cap.rivet_row(p, (bx[1] - .08,) * 2, (bx[2] + .1, bx[3] - .1), 4, .02, BARE, STEEL)
            if w > .3:
                _tower_shield(p, rng, wr + V(.27, s_ * .06, 0), V(1, s_ * .4, 0), 1.5, 2.9, .12)
            else:
                _prism_head(p, rng, wr + V(.32, 0, 0), (1, 0, -.15), .3)
    # ---- the crown
    sweep(p, [(.62, 2.12), (.94, 2.12), (.94, 2.26), (.62, 2.3)], GRAPHITE, STEEL)
    ang = (np.arange(18) + .5) / 18 * TAU
    bolts(p, np.stack([.86 * np.cos(ang), .86 * np.sin(ang), np.full(18, 2.265)], 1), (0, 0, 1), .028)
    turn(p, [(.62, 2.3), (.5, 2.42), (.25, 2.5), (0, 2.52)], bone(rng, .05), PAINT, 32, caps=(False, False))
    hoop(p, (0, 0, 2.4), (0, 0, 1), .43, .05, glow(GLOW_AMBER, EMIT), GLOW, 36, 8)
    for k in range(9):
        a = k / 9 * TAU + .35
        u = V(math.cos(a), math.sin(a), 0)
        fin(p, [u * .98 + (0, 0, 2.22), u * .4 + (0, 0, 2.3), u * .8 + (0, 0, 3.5), u * 1.14 + (0, 0, 3.75)], .09, bone(rng), PAINT, BARE, STEEL,
            taper=.3, n=(4, 5))
        strut(p, u * .92 + (0, 0, 2.27), u * 1.0 + (0, 0, 2.95), .05, .05, FRAME, STEEL, up=u, bevel=.01)
        pipe(p, [u * .6 + (0, 0, 2.5), u * .86 + (0, 0, 3.42)], .022, glow(GLOW_AMBER, EMIT * .9), GLOW, 6)
    # ---- the exposed coupling in the back window
    cc = side(1.65, 270, .02)
    back = V(-1.0, 0, 0)
    rb = along(back)
    for phi in (243, 297):                                        # frame ribs at the window's sides
        plate(p, torso, (1.42, 1.88), _deg(phi - 1.6, phi + 1.6), FRAME, STEEL, .09, 0.0, n=(5, 2), lift=.06)
    sweep(p, [(.3, -.02), (.6, -.02), (.6, .05), (.3, .05)], GRAPHITE, STEEL, rot=rb, origin=cc, sides=40)
    hoop(p, cc + back * .16, back, .42, .075, COPPER, BRASS, 44, 10)
    for k in range(16):                                           # the coil's windings
        a = (k + .5) / 16 * TAU
        d = rb @ V(math.cos(a), math.sin(a), 0)
        hoop(p, cc + back * .16 + d * .42, np.cross(back, d), .088, .013, tone(COPPER, .8 + .3 * (k % 2)), BRASS, 12, 5)
    for k in range(4):                                            # bus bars on ceramic insulators
        a = math.radians(45 + 90 * k)
        d = rb @ V(math.cos(a), math.sin(a), 0)
        strut(p, cc + back * .16 + d * .5, cc + back * .1 + d * .82, .09, .03, tone(COPPER, .9), BRASS, up=back, bevel=.006)
        for z in (.0, .035, .07):
            sweep(p, [(.03, z), (.07, z), (.075, z + .014), (.07, z + .028), (.03, z + .028)], bone(rng, .05), PAINT, rot=rb, origin=cc + d * .82, sides=14)
        bolts(p, [cc + back * .125 + d * .82], back, .03, tone(COPPER, 1.1), BRASS)
    start = ball(p, cc + back * .2, .2, GLOW_LINK, GLOW, 32)
    v = np.asarray(p.v[start:], np.float64)
    p.c[start:] = glow(GLOW_LINK, .92 - .22 * np.clip((v[:, 0] - (cc[0] - .2)) / .2, 0, 1)).tolist()
    mark(p, 'coupling', cc + back * .2)
    for axis_ in ((0, 1, 0), (0, 0, 1), (0, .7, .7)):             # a copper cage round the core
        hoop(p, cc + back * .2, axis_, .245, .014, tone(COPPER, 1.1), BRASS, 28, 5)
    hoop(p, cc + back * .055, back, .2, .02, glow(GLOW_LINK, .4), GLOW, 28, 5)
    for s_ in (-1, 1):                                            # conduits down the back to the base, resonance leaking along them
        keys = [cc + V(-.12, s_ * .34, -.34), V(-1.2, s_ * .4, -.75), V(-1.12, s_ * .4, -1.25), V(-.98, s_ * .36, -1.9), V(-.96, s_ * .34, -2.95)]
        path = curve(keys, 22)
        pipe(p, path, .07, tone(COPPER, .85), BRASS, 12)
        pipe(p, path[2:] + V(-.075, 0, 0), .014, np.array([glow(GLOW_LINK, q) for q in np.linspace(.45, .15, 20)]), GLOW, 5, cap=False)
        for i in (4, 10, 16):
            tg = unit(path[i + 1] - path[i - 1])
            sweep(p, [(.07, -.04), (.095, -.04), (.095, .04), (.07, .04)], BARE, STEEL, rot=along(tg), origin=path[i], sides=12)
        hose(p, curve([cc + V(.0, s_ * .5, -.5), cc + V(-.22, s_ * .56, -.7), cc + V(-.2, s_ * .5, -1.05), cc + V(-.1, s_ * .56, -1.3)], 10), .035)
    # ---- the slewing ring, the stem and its bands
    sweep(p, [(.7, -1.24), (1.22, -1.24), (1.22, -1.05), (.7, -1.05)], GRAPHITE, STEEL)
    ang = (np.arange(24) + .5) / 24 * TAU
    bolts(p, np.stack([1.1 * np.cos(ang), 1.1 * np.sin(ang), np.full(24, -1.052)], 1), (0, 0, 1), .034)
    pipe(p, [(0, 0, -3.3), (0, 0, -1.1)], .72, FRAME, STEEL, 44)
    for k, z0 in enumerate((-2.78, -2.34, -1.9, -1.46)):
        for q in range(4):
            a0 = q * math.pi / 2 + .04 + k * .3
            sweep(p, [(.725, z0), (.87, z0 + .04), (.9, z0 + .34), (.745, z0 + .38)], bone(rng), PAINT, a0, a0 + math.pi / 2 - .08, sides=12)
    for k in range(7):                                            # rungs up the stem's back
        z = -3.0 + k * .28
        pipe(p, [(-.88, -.2, z), (-1.04, -.2, z), (-1.04, .2, z), (-.88, .2, z)], .02, BARE, STEEL, 6)
    for a in (1.1, 2.4, 3.9, 5.2):
        loom(p, cyl(np.stack([np.full(10, .93), np.linspace(0, .12, 10), np.linspace(-3.05, -1.25, 10)], 1), a), .03, 3, 3)
    # ---- the ring base: a frame ring, deck plates and a rail on top, bumpers round it, six hover units under it
    sweep(p, [(1.4, -3.7), (2.0, -3.7), (2.12, -3.55), (2.12, -3.3), (2.0, -3.15), (1.4, -3.15), (1.32, -3.3), (1.32, -3.55)], GRAPHITE, STEEL, sides=64)
    for k in range(12):
        a0 = k * TAU / 12 + .035
        sweep(p, [(1.44, -3.15), (2.0, -3.15), (2.0, -3.105), (1.44, -3.105)], bone(rng), PAINT, a0, a0 + TAU / 12 - .07, sides=6)
    for k in range(6):
        a0 = k * TAU / 6 + .06
        sweep(p, [(2.12, -3.52), (2.21, -3.5), (2.21, -3.35), (2.12, -3.33)], bone(rng), PAINT, a0, a0 + TAU / 6 - .12, sides=12)
        a = (k + .5) * TAU / 6
        field(p, (1.72 * math.cos(a), 1.72 * math.sin(a), -3.72), (0, 0, -1), .27, shell=bone(rng))
    gate = .3                                                      # the rail is open at the back, where the rungs come up
    for z in (-2.62, -2.14):
        hoop(p, (0, 0, z), (0, 0, 1), 2.04, .026, BARE, STEEL, 56, 6, math.pi + gate, 3 * math.pi - gate, rot=np.eye(3))
    for a in np.linspace(math.pi + gate, 3 * math.pi - gate, 17):
        pipe(p, [(2.04 * math.cos(a), 2.04 * math.sin(a), -3.11), (2.04 * math.cos(a), 2.04 * math.sin(a), -2.14)], .024, BARE, STEEL, 6)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        u = V(math.cos(a), math.sin(a), 0)
        strut(p, u * 1.38 + (0, 0, -3.36), u * .62 + (0, 0, -2.62), .3, .4, FRAME, STEEL, bevel=.05)
        ram(p, u * 1.36 + np.cross(UP, u) * .3 + (0, 0, -3.2), u * .78 + np.cross(UP, u) * .24 + (0, 0, -2.2), .07, pin=np.cross(UP, u))
    return hover(p, 7.5, 507, under=.2)


@built(.035)
def harrow():
    """SM_GE_Harrow (5.0 m wide): end-game. A heavy, low, plated hull with three amber lenses in its face (the great one
    in the middle, one at each front corner) inside the unit's orange band, and slung under its front on a three-point
    linkage a harrow: a toolbar with two swept wings that fold on hinges and rams, three rows of bars, and forty-seven
    spring tines, each a clamp, a coil and a hooked shank with a share. Two guarded thrusters, exhaust stacks and a tow
    hitch behind; hover field units under the hull and at the wing tips."""
    rng = np.random.default_rng(508)
    p = Part('SM_GE_Harrow', (STEEL, PAINT, GLOW))
    hull = Hull((-.2, 0, .45), (1.35, 1.05, .62), .62, .58)
    t = .045
    hull.core(p, GRAPHITE, STEEL, t * 1.5, (24, 44))
    for i, th in enumerate(((.62, 1.1), (1.1, 1.6), (1.6, 2.12), (2.12, 2.66))):
        for j, (a, b) in enumerate(((-28, 38), (38, 90), (90, 142), (142, 208))):
            bx = plate(p, hull, th, _deg(a, b), bone(rng), PAINT, t, .024, n=(3, 3), sag=.14, seed=i * 4 + j)
            hull.rivet_row(p, (bx[0] + .045,) * 2, (bx[2] + .06, bx[3] - .06), 5, .016, BARE, STEEL)
        plate(p, hull, th, _deg(208, 332), FRAME, STEEL, t, .024, n=(3, 5), sag=.14)
    plate(p, hull, (.5, .62), _deg(-28, 208), ORANGE, PAINT, t, .024, n=(2, 16), sag=.14, seed=31)
    plate(p, hull, (.17, .5), (0.0, TAU), FRAME, STEEL, t, .02, n=(2, 24), sag=.14)
    # ---- the three lenses and their sensors
    eye(p, hull.point(0.0, 0.0) - V(.07, 0, 0), (1, 0, -.04), .2, bezel=bone(rng, .05), hood=1.2, fasteners=12)
    for phi, name in ((0.0, 'lens_right'), (math.pi, 'lens_left')):
        n_ = hull.normal(.86, phi)
        eye(p, hull.point(.86, phi) - n_ * .03, unit(n_ + V(1.1, 0, 0)), .125, bezel=bone(rng, .05), hood=1.2, fasteners=10, name=name)
        for dphi in (-.28, .28):
            sensor(p, hull.point(1.08, phi + dphi, -t * .5), hull.normal(1.08, phi + dphi), .04)
    for phi in (250, 290):
        sensor(p, hull.point(.36, math.radians(phi), -t * .4), hull.normal(.36, math.radians(phi)), .045)
    # ---- the deck: hatches, lifting eyes, the intake, masts; vents, a serial plate and rungs on the flanks
    hatch(p, hull, (1.2, 1.5), _deg(50, 82), bone(rng, .05), t * .5, 1)
    hatch(p, hull, (1.72, 2.02), _deg(98, 130), bone(rng, .05), t * .5, 2)
    for th in (1.1, 2.12):
        for phi in (62, 118):
            lug(p, hull.point(th, math.radians(phi), -t * .2), hull.normal(th, math.radians(phi)), .06, (1, 0, 0))
    obox(p, (-.95, 0, 1.0), (.32, .4, .1), FRAME, STEEL, .03)
    louvre(p, (-.63, 0, 1.01), (1, 0, .25), (0, 0, 1), .7, .14, 4)
    for phi in (4, 176):
        louvre(p, hull.point(1.86, math.radians(phi), -t * .2), hull.normal(1.86, math.radians(phi)), (0, 0, 1), .5, .26, 6)
    tag(p, hull.point(1.36, math.radians(-12), -t * .15), hull.normal(1.36, math.radians(-12)), (0, 0, 1), .2, .12)
    for k in range(4):
        th = 2.2 + k * .1
        a, b = hull.point(th, math.radians(-6), -.02), hull.point(th, math.radians(-6), -.02) + V(0, 0, 0)
        a, b = hull.point(2.36, math.radians(-20 + k * 13), -.02), hull.point(2.56, math.radians(-20 + k * 13), -.02)
        n_ = hull.normal(2.46, math.radians(-20 + k * 13)) * .1
        pipe(p, [a, a + n_, b + n_, b], .016, BARE, STEEL, 6)
    for s_ in (-1, 1):
        whip = curve([V(-1.0, s_ * .62, .95), V(-1.06, s_ * .64, 1.15), V(-1.16, s_ * .66, 1.3), V(-1.3, s_ * .68, 1.38)], 9)
        pipe(p, whip, np.linspace(.014, .005, 9), GRAPHITE, STEEL, 6)
        # ---- behind: thrusters, stacks
        thruster(p, (-1.5, s_ * .5, .5), (-1, 0, 0), .26, .3, guard=True)
        pipe(p, [(-1.12, s_ * .78, .86), (-1.2, s_ * .8, 1.12), (-1.3, s_ * .8, 1.2)], [.07, .065, .06], BARE, STEEL, 14)
        hoop(p, (-1.3, s_ * .8, 1.2), (-.8, 0, .6), .062, .012, GRAPHITE, STEEL, 14, 5)
        obox(p, (-1.6, s_ * .09, .12), (.1, .02, .08), FRAME, STEEL, .01)            # the tow hitch's cheeks
    pipe(p, [(-1.64, -.14, .12), (-1.64, .14, .12)], .03, BRIGHT, STEEL, 10)
    for x in (.45, -.85):
        sweep(p, [(.22, -.14), (.4, -.14), (.4, -.22), (.22, -.22)], GRAPHITE, STEEL, origin=(x, 0, 0))
        field(p, (x, 0, -.25), (0, 0, -1), .36, shell=bone(rng), coils=10)
    # ---- the harrow: toolbar, wings, bars
    zb = -.5

    def at(row, y, dz=0.0):
        return V(1.4 - .4 * row - .12 * max(abs(y) - 1.2, 0.0), y, zb + dz)
    spans = ((-1.17, 1.17), (-2.42, -1.27), (1.27, 2.42))
    for y0, y1 in spans:
        strut(p, at(0, y0), at(0, y1), .18, .18, FRAME, STEEL, bevel=.025)
        obox(p, (at(0, y0) + at(0, y1)) / 2 + V(.092, 0, 0), (.006, abs(y1 - y0) * .42, .06), bone(rng), PAINT, .004,
             basis(V(1, 0, 0) if y0 * y1 < 0 else V(1, .12 * np.sign(y0), 0)))
        for row in (1, 2):
            pipe(p, [at(row, y0), at(row, y1)], .055, FRAME, STEEL, 14)
    for y in (-2.25, -1.5, -1.0, 0.0, 1.0, 1.5, 2.25):
        strut(p, at(0, y, .1), at(2, y, .1) - V(.1, 0, 0), .1, .08, FRAME, STEEL, bevel=.015)
        for row in (1, 2):                                        # U-bolts holding the bars under the arms
            hoop(p, at(row, y), (0, 1, 0), .068, .012, BARE, STEEL, 12, 5)
    for s_ in (-1, 1):
        pivot(p, at(0, s_ * 1.22, .14), (1, 0, 0), .07, .34)       # the wing's fold hinge
        for y in (1.14, 1.3):
            obox(p, at(0, s_ * y, .1), (.1, .03, .1), FRAME, STEEL, .012)
        strut(p, at(0, s_ * .75, .08), at(0, s_ * .75, .44), .1, .1, FRAME, STEEL, up=(1, 0, 0), bevel=.015)
        ram(p, at(0, s_ * .75, .4), at(0, s_ * 1.8, .16), .045, pin=(1, 0, 0))
        obox(p, at(0, s_ * 1.8, .1), (.06, .05, .05), FRAME, STEEL, .012)
        # the wing tip: an end plate with its skid, and a hover unit under a cap
        tip = (at(0, s_ * 2.47) + at(2, s_ * 2.47)) / 2
        obox(p, tip + V(0, 0, -.06), (.56, .02, .26), bone(rng), PAINT, .012)
        studs(p, [tip + V(dx, s_ * .022, dz) for dx in (-.5, -.25, 0, .25, .5) for dz in (-.28, .16)], (0, s_, 0), .014)
        strut(p, tip + V(-.5, 0, -.34), tip + V(.56, 0, -.34), .05, .05, BARE, STEEL, bevel=.012)
        pod = at(1.5, s_ * 2.08, .16)
        field(p, pod, (0, 0, -1), .2, shell=bone(rng))
        turn(p, [(.215, .04), (.19, .1), (.1, .15), (0, .16)], bone(rng), PAINT, 28, origin=pod, caps=(False, False))
        # ---- the three-point linkage: lower links with their lift rams
        a, b = V(.78, s_ * .55, -.02), at(0, s_ * .55, .1) - V(.07, 0, 0)
        strut(p, a, b, .12, .1, FRAME, STEEL, bevel=.02)
        pivot(p, a, (0, 1, 0), .06, .18)
        pivot(p, b, (0, 1, 0), .055, .17)
        ram(p, V(.98, s_ * .78, .16), (a + b) / 2 + V(0, s_ * .1, .02), .05, pin=(0, 1, 0))
        obox(p, (a + b) / 2 + V(0, s_ * .07, 0), (.05, .03, .05), FRAME, STEEL, .01)
    strut(p, at(0, 0, .08), at(0, 0, .46), .12, .1, FRAME, STEEL, up=(1, 0, 0), bevel=.015)
    ram(p, V(1.02, 0, .12), at(0, 0, .42), .05, pin=(0, 1, 0))      # the top link
    loom(p, curve([V(.9, .2, -.02), V(1.1, .22, -.2), V(1.3, .2, -.36), at(0, .3, .1)], 9), .02, 3, 2)
    # ---- the tines: a clamp on the bar, a coil, a hooked shank and its share
    for row in range(3):
        ys = np.arange(-2.4, 2.41, .32) if row != 1 else np.arange(-2.24, 2.25, .32)
        for y in ys:
            if 1.17 < abs(y) < 1.27:
                continue
            x, _, z = at(row, float(y), -.09 if row == 0 else -.055)
            obox(p, (x, y, z + .05), (.075, .04, .06), FRAME, STEEL, .012)
            bolts(p, [(x + .078, y, z + .06)], (1, 0, 0), .016)
            keys = [(x, y, z), (x - .08, y + .008, z - .05), (x - .02, y + .018, z - .17), (x + .06, y + .028, z - .09), (x, y + .036, z - .02),
                    (x - .1, y + .036, z - .11), (x - .2, y + .036, z - .29), (x - .21, y + .036, z - .49), (x - .1, y + .036, z - .65),
                    (x + .08, y + .036, z - .7), (x + .24, y + .036, z - .67)]
            path = curve(keys, 26)
            pipe(p, path, np.linspace(.021, .016, 26), mix(STEEL_DARK, STEEL_GREY, rng.uniform(.2, .7)), STEEL, 6)
            d = unit(path[-1] - path[-2])
            prism(p, path[-1] - d * .04, path[-1] + d * .12, .036, BRIGHT, STEEL, 4, .7)
    return hover(p, 5.0, 508)

# ---------------------------------------------------------------- the people (SM_GP_*): machines, but persons
# They stand on z 0, facing +x (their right hand is on +y). Built to be talked to up close: limbs are a dark frame
# cover under enamel plates with seams (limb_shell()), joints are pins in bosses, hands have three phalanges to a
# finger (hand()). Their marks give the head for the talk icon.

def spin(axis, degrees):
    """Rotation by `degrees` about an axis (right-handed)."""
    a = unit(axis)
    q = math.radians(degrees)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(q) * K + (1 - math.cos(q)) * K @ K


def turned(part, start, rot, about):
    """Turns every vertex added since `start` by rot about the point `about`."""
    v = np.asarray(part.v[start:], np.float64) - np.asarray(about, np.float64)
    part.v[start:] = (v @ np.asarray(rot, np.float64).T + np.asarray(about, np.float64)).tolist()


def casing(part, rows, colour, slot=PAINT, power=2.6, sides=32, centre=(0.0, 0.0), shade=None):
    """A closed shell whose horizontal sections are superellipses through rows (z, half-width, front depth, back
    depth): a chest, a pelvis, a housing. shade(points) scales the colour per vertex."""
    rows = sorted(rows)
    th = np.linspace(-math.pi, math.pi, sides, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    e = 2.0 / power
    G = np.array([np.stack([np.where(c >= 0, f, b) * np.sign(c) * np.abs(c) ** e + centre[0], hw * np.sign(s) * np.abs(s) ** e + centre[1],
                            np.full(sides, z)], -1) for z, hw, f, b in rows])
    n = len(rows)
    faces = [[i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j] for i in range(n - 1) for j in range(sides)]
    base = np.asarray(colour, np.float64)
    cols = np.tile(base, (n * sides, 1))
    if shade is not None:
        cols[:, :3] *= np.asarray(shade(G.reshape(-1, 3)), np.float64)[:, None]
    start = part.add(G.reshape(-1, 3), faces, cols, slot, True)
    part.add(np.concatenate([G[0], G[-1]]), [list(range(sides))[::-1], list(range(sides, 2 * sides))], np.concatenate([cols[:sides], cols[-sides:]]), slot, False)
    return start


def pod(part, a, b, r, colour, slot=PAINT, sides=14, flat=1.0, face=(1, 0, 0), ends=(1.0, 1.0)):
    """An egg-shaped casing from a to b, r across (flat squeezes it along `face`; ends swell or shrink its two ends)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    start = ball(part, (0, 0, 0), 1.0, colour, slot, sides, (r * flat, r, norm(b - a) / 2))
    v = np.asarray(part.v[start:], np.float64)
    v[:, :2] *= np.where(v[:, 2] < 0, ends[0], ends[1])[:, None] ** np.clip(np.abs(v[:, 2]) / (norm(b - a) / 2), 0, 1)[:, None]
    part.v[start:] = v.tolist()
    place(part, start, aim(b - a, face), (a + b) / 2)
    return start


def limb_shell(part, rng, a, b, r, face, plates, e=(.78, .9), wide=1.0, thick=None, colour=None, wear=.14, seed=0, rivet=0.0):
    """A limb segment from a to b as the Just build them: a dark cover over the frame and enamel plates on it with
    seams between. plates are (th0, th1, ph0, ph1) in degrees on the segment's own hull: theta runs from b's end (0)
    to a's (180), phi 90 faces `face`; a fifth entry makes the plate rusted iron (RUST). wide scales it across `face`.
    Returns the hull."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    hull = Hull((a + b) / 2, (norm(b - a) / 2, r * wide, r), e[0], e[1], basis(b - a, face))
    t = r * .13 if thick is None else thick
    hull.core(part, GRAPHITE, STEEL, t * 1.5, (max(6, S(norm(b - a) / 2, 6, 10)), S(r, 10, 20)))
    for k, pl in enumerate(plates):
        t0, t1, p0, p1 = pl[:4]
        if len(pl) > 4:                                           # a plate rusted through its paint
            c, slot = tone(mix(RUST_ORANGE, RUST_DARK, rng.uniform(0, .6))), RUST
        else:
            c, slot = colour() if callable(colour) else (bone(rng, wear) if colour is None else colour), PAINT
        bx = plate(part, hull, _deg(t0, t1), _deg(p0, p1), c, slot, t, t * .5, n=(3, 3), sag=.25, seed=seed + k)
        if rivet:
            hull.rivet_row(part, (bx[0] + .12,) * 2, (bx[2] + .2, bx[3] - .2), 3, rivet, BARE, STEEL)
    return hull


def graft(part, other, rot=None, origin=(0, 0, 0), mirror_y=False):
    """Appends another Part's geometry (same slot names): mirrored in its own y first when asked (faces re-wound), then
    turned by rot and moved to origin."""
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


def hand(part, rng, wrist, rot, size=1.0, curl=(.3, .35, .4, .5), thumb=.5, spread=.1, shell=None, pad=None, pad_slot=PAINT, right=False,
         pad_thick=.004):
    """A mechanical hand at `wrist`. rot's columns are its frame: x along the fingers, z out of the back of the hand,
    y toward the thumb of a left hand (a right hand is the mirror image: its thumb is on -y). A palm block with an
    enamel back plate and a pad, four fingers of three phalanges on knuckle pins (curl: radians a joint, index to
    little; spread fans them), and a two-jointed thumb. pad_thick (times size) is the pad's thickness: at 0.022 a flat
    hand's pad stands proud of the wrist and every finger, so a load bears on it alone. Returns the centre of the
    pad's face."""
    s = size
    h = Part('hand', part.slots)
    shell = bone(rng, .1) if shell is None else shell
    pad = RUBBER if pad is None else pad

    def at(x, y, z):
        return V(x, y, z) * s
    sweep(h, [(.02 * s, -.012 * s), (.03 * s, -.012 * s), (.032 * s, 0), (.03 * s, .012 * s), (.02 * s, .012 * s)], BARE, STEEL, sides=S(.03 * s, 12, 24),
          rot=along((1, 0, 0)), origin=at(.004, 0, 0))
    ball(h, at(0, 0, 0), .022 * s, GRAPHITE, STEEL, S(.022 * s, 10, 20))
    obox(h, at(.06, 0, 0), (.045 * s, .041 * s, .014 * s), GRAPHITE, STEEL, .006 * s)
    obox(h, at(.058, 0, .0155), (.038 * s, .036 * s, .004 * s), shell, PAINT, .003 * s)
    obox(h, at(.06, 0, -.014 - pad_thick / 2), (.04 * s, .036 * s, pad_thick / 2 * s), pad, pad_slot, min(.0015, pad_thick * .2) * s)
    studs(h, [at(.058 + dx, dy, .0195) for dx in (-.03, .03) for dy in (-.028, .028)], (0, 0, 1), .003 * s)
    lengths = np.array([.042, .028, .022])
    for i in range(4):
        f = (1.0, 1.08, 1.0, .82)[i]
        fan = (1.5 - i) * spread
        joint = at(.105, (1.5 - i) * .0205, 0)
        ang = 0.0
        for k in range(3):
            ang += curl[i] * (.9, 1.0, .8)[k]
            d = unit(V(math.cos(ang), math.sin(fan) * .35, -math.sin(ang)))
            tip = joint + d * lengths[k] * f * s
            rr = (.0092, .0084, .0076)[k] * s
            pipe(h, [joint - V(0, rr * 1.25, 0), joint + V(0, rr * 1.25, 0)], rr * 1.12, GRAPHITE, STEEL, 8)        # the knuckle pin
            pipe(h, [joint + d * rr * .4, tip - d * rr * .3], [rr, rr * .92], shell if k < 2 else BARE, PAINT if k < 2 else STEEL, 8)
            joint = tip
        ball(h, joint, .0078 * s, pad, pad_slot, 8)
    joint = at(.035, .044, -.004)
    ang = 0.0
    for k in range(2):
        ang += thumb * (1.0, .8)[k]
        d = unit(V(.75 * math.cos(ang), .62, -math.sin(ang)))
        tip = joint + d * (.04, .03)[k] * s
        rr = (.0105, .009)[k] * s
        ball(h, joint, rr * 1.2, GRAPHITE, STEEL, 8)
        pipe(h, [joint + d * rr * .4, tip - d * rr * .3], [rr, rr * .9], shell if k == 0 else BARE, PAINT if k == 0 else STEEL, 8)
        joint = tip
    ball(h, joint, .0086 * s, pad, pad_slot, 8)
    graft(part, h, rot, wrist, right)
    return np.asarray(wrist, np.float64) + np.asarray(rot, np.float64) @ (V(.06, 0, -.014 - pad_thick) * s)


def band(part, path, width, thick, out, colour, slot=CLOTH, rim=None):
    """A flat strap along a path, `width` across and `thick` through, its face turned toward `out` (one direction, or
    one per point): straps, ties, tails, belts."""
    path = np.asarray(path, np.float64)
    n = len(path)
    tang = unit(np.gradient(path, axis=0))
    o = np.broadcast_to(np.asarray(out, np.float64), path.shape)
    o = unit(o - tang * np.sum(o * tang, 1, keepdims=True))
    side = np.cross(tang, o)
    w = np.broadcast_to(np.asarray(width, np.float64), (n,))[:, None] / 2
    outer = np.stack([path - side * w + o * thick / 2, path + side * w + o * thick / 2], 1)
    inner = np.stack([path - side * w - o * thick / 2, path + side * w - o * thick / 2], 1)
    slab(part, outer, inner, colour, slot, tone(colour, .8) if rim is None else rim, slot)


def soft_eye(part, c, axis, r, up=(0, 0, 1), bright=.55, lid=1.2, lid_colour=None, bezel=None, bezel_slot=BRASS):
    """A person's eye: a soft amber dome (brightest at its centre, well under a sentry's lens) in a bezel, under a thin
    enamel lid that gives the face its look (lid: radians either side of up; 0 for none)."""
    c, ax = np.asarray(c, np.float64), unit(axis)
    rot = aim(ax, up)
    s = S(r * 1.4, 12, 28)
    sweep(part, [(r * .98, r * .1), (r * .98, -r * .5), (r * 1.34, -r * .5), (r * 1.4, 0), (r * 1.3, r * .3), (r * 1.08, r * .34)],
          tone(BRASS_WARM, .75) if bezel is None else bezel, bezel_slot, sides=s, rot=rot, origin=c)
    lat = np.linspace(math.pi / 2, 0, 6)
    turn(part, [(r * math.sin(q), -r * .05 + r * .5 * math.cos(q)) for q in lat],
         np.array([glow(GLOW_AMBER, bright * (1 - .4 * math.sin(q) ** 2)) for q in lat]), GLOW, s, rot, c, caps=(False, False))
    if lid:
        sweep(part, [(r * 1.4, -r * .3), (r * 1.62, -r * .3), (r * 1.62, r * .5), (r * 1.52, r * .62), (r * 1.4, r * .5)],
              tone(JUST_BONE, .9) if lid_colour is None else lid_colour, PAINT, -lid, lid, rot=rot, origin=c)


@built(.012)
def thessaly():
    """SM_GP_Thessaly (1.78 m): Thessaly-4, the Just's field botanist. A slender robot of bone-white plates worn grey
    over a dark frame; a round head, tilted a little, with two soft amber eyes under thin lids, a loupe pushed up at
    her right temple and an aerial on her left ear; a canvas field apron (bib, skirt with hanging folds, hems, a
    pocket of tools, a neck strap on brass rings, a waist tie in a bow); her right forearm is a pruning multi-tool
    (bypass blades, a folded saw, a probe); her left hand, palm up, holds a seedling with its roots wrapped; moss and
    a sprout on her left shoulder. Feet on z 0; marks: head (its centre), head_top, eyes."""
    rng = np.random.default_rng(601)
    p = Part('SM_GP_Thessaly', (PAINT, STEEL, CLOTH, GLOW, MOSS, BRASS, LEAF))
    upright = basis((0, 0, 1), (1, 0, 0))      # local x up; phi 90 degrees faces +x, 0 is -y, 180 is +y, 270 the back
    brass = tone(BRASS_WARM, .75)

    def worn(w=.16):
        return tone(mix(JUST_BONE, CONCRETE_STAIN, rng.uniform(.18, .42)), rng.uniform(1 - w, 1.0))
    # ---- legs
    for s_ in (-1, 1):
        y = s_ * .087
        hip, knee, ankle = V(0, s_ * .085, .93), V(.012, s_ * .088, .5), V(0, y, .085)
        obox(p, (.035, y, .014), (.115, .043, .014), RUBBER, PAINT, .008)
        pod(p, (.03, y, .05), (.15, y, .04), .042, worn(), PAINT, 16, .7, (0, 0, 1))
        obox(p, (-.052, y, .042), (.03, .036, .028), GRAPHITE, STEEL, .01)
        obox(p, (.0, y, .066), (.06, .034, .01), worn(), PAINT, .005, basis((1, 0, -.22)))
        ball(p, ankle, .032, GRAPHITE, STEEL, 14)
        pivot(p, ankle, (0, 1, 0), .02, .086)
        limb_shell(p, rng, knee, ankle, .043, (1, 0, 0), [(14, 166, 35, 145), (28, 150, 215, 325)], colour=worn, seed=10)
        ram(p, (-.04, y, .34), (-.052, y, .075), .0065, pin=(0, 1, 0))
        ball(p, knee, .04, GRAPHITE, STEEL, 16)
        pivot(p, knee, (0, 1, 0), .026, .106)
        pod(p, knee + V(.034, 0, -.045), knee + V(.04, 0, .05), .036, worn(), PAINT, 14, .45, (1, 0, 0))
        limb_shell(p, rng, hip, knee, .054, (1, 0, 0), [(22, 158, 28, 152), (22, 158, 208, 332)], colour=worn, seed=14)
        ball(p, hip, .05, GRAPHITE, STEEL, 16)
        pivot(p, hip + V(0, s_ * .03, 0), (0, 1, 0), .03, .08)
    # ---- pelvis, the waist's bellows, the chest
    pelvis = Hull((0, 0, .965), (.078, .132, .1), .7, .75, upright)
    pelvis.core(p, GRAPHITE, STEEL, .012, (10, 28))
    for k, ph in enumerate(((-38, 38), (38, 142), (142, 218), (218, 322))):
        plate(p, pelvis, (.55, 2.5), _deg(*ph), worn(), PAINT, .008, .006, n=(3, 4), sag=.25, seed=20 + k)
    pipe(p, [(0, 0, 1.02), (0, 0, 1.125)], .072, GRAPHITE, STEEL, 24)
    for z in (1.035, 1.058, 1.081, 1.104):
        sweep(p, [(.07, z), (.092, z + .004), (.092, z + .018), (.07, z + .022)], RUBBER, PAINT, sides=28)
    for s_ in (-1, 1):
        ram(p, (-.072, s_ * .05, 1.0), (-.088, s_ * .056, 1.2), .007, pin=(0, 1, 0))
    chest = Hull((0, 0, 1.275), (.178, .162, .112), .7, .75, upright, taper=(.22, .12))
    chest.core(p, GRAPHITE, STEEL, .012, (16, 36))
    for i, th in enumerate(((.5, 1.25), (1.25, 2.05), (2.05, 2.62))):
        for j, ph in enumerate(((20, 88), (92, 160), (-22, 20), (160, 202), (202, 268), (272, 338))):
            bx = plate(p, chest, th, _deg(*ph), worn(), PAINT, .008, .006, n=(3, 3), sag=.25, seed=30 + i * 6 + j)
            if j >= 4 and i < 2:
                chest.rivet_row(p, (bx[0] + .1,) * 2, (bx[2] + .14, bx[3] - .14), 3, .003, BARE, STEEL)
    # the pack between her shoulder blades, its looms to the neck, the spine's cover plates
    obox(p, (-.128, 0, 1.3), (.03, .075, .095), GRAPHITE, STEEL, .012)
    obox(p, (-.16, 0, 1.3), (.004, .066, .086), worn(), PAINT, .003)
    louvre(p, (-.165, 0, 1.325), (-1, 0, 0), (0, 0, 1), .09, .05, 5)
    tag(p, (-.1645, 0, 1.245), (-1, 0, 0), (0, 0, 1), .05, .028)
    studs(p, [(-.1645, sy * .058, 1.3 + sz * .078) for sy in (-1, 1) for sz in (-1, 1)], (-1, 0, 0), .0035)
    for s_ in (-1, 1):
        loom(p, curve([(-.13, s_ * .05, 1.39), (-.11, s_ * .055, 1.44), (-.07, s_ * .045, 1.475), (-.035, s_ * .03, 1.5)], 8), .005, 2, 1)
    for k in range(4):
        z = 1.19 - k * .055
        obox(p, (-.1 + .012 * k, 0, z), (.012, .024, .022), worn(), PAINT, .005)
    # ---- neck
    pipe(p, [(0, 0, 1.44), (.005, 0, 1.56)], .034, GRAPHITE, STEEL, 16)
    for z in (1.47, 1.495, 1.52):
        hoop(p, (.003, 0, z), (0, 0, 1), .038, .009, RUBBER, PAINT, 20, 6)
    sweep(p, [(.045, 1.44), (.078, 1.436), (.084, 1.456), (.05, 1.47)], worn(.08), PAINT, sides=28)
    for s_ in (-1, 1):
        ram(p, (-.02, s_ * .05, 1.455), (-.012, s_ * .042, 1.565), .0045, pin=(1, 0, 0))
    # ---- head (built upright, then tilted on the neck)
    h0 = len(p.v)
    hc = V(.012, 0, 1.648)
    head = Hull(hc, (.106, .096, .1), .95, .95)
    head.core(p, GRAPHITE, STEEL, .008, (16, 32))
    plate(p, head, (.88, 2.95), _deg(28, 152), worn(.1), PAINT, .007, .005, n=(5, 6), sag=.2, seed=50)
    for k, ph in enumerate((_deg(-58, 28), _deg(152, 238))):
        plate(p, head, (.88, 2.75), ph, worn(.1), PAINT, .007, .005, n=(5, 4), sag=.2, seed=51 + k)
    plate(p, head, (.92, 2.6), _deg(238, 302), worn(.1), PAINT, .007, .005, n=(4, 3), sag=.2, seed=53)
    plate(p, head, (.1, .85), (0.0, TAU), SENSOR, PAINT, .006, .004, n=(3, 28), lift=-.003, sag=.2, chip=0)
    sensor(p, head.point(0.0, 0.0) - V(.004, 0, 0), (1, 0, 0), .011)
    eyes = []
    for ph in (14, 166):
        c = head.point(.5, math.radians(ph), .002)
        soft_eye(p, c, unit(head.normal(.5, math.radians(ph)) + V(.7, 0, 0)), .0195, bright=.55, lid=1.15, lid_colour=worn(.06), bezel=brass)
        eyes.append(c)
    for k in range(3):
        th = .5 + .085 * k
        n_ = head.normal(th, math.radians(270))
        obox(p, head.point(th, math.radians(270), .001), (.002, .017 - .0035 * k, .0024), BARE, STEEL, .0008, basis(n_, (0, 1, 0)) @ spin((1, 0, 0), 90))
    for s_, ph in ((1, 0.0), (-1, math.pi)):
        c, n_ = head.point(math.pi / 2, ph, .002), head.normal(math.pi / 2, ph)
        turn(p, [(.034, 0), (.034, .008), (.026, .014), (0, .016)], worn(.08), PAINT, 24, along(n_), c, caps=(False, False))
        bolts(p, [c + n_ * .015], n_, .007, brass, BRASS)
        if s_ < 0:                                                # the aerial on her left ear
            whip = curve([c + n_ * .012 + V(-.012, 0, .02), c + V(-.014, -.02, .07), c + V(-.018, -.024, .12)], 7)
            pipe(p, [c + n_ * .01 + V(-.012, 0, 0), c + n_ * .012 + V(-.012, 0, .02)], .0045, BARE, STEEL, 6)
            pipe(p, whip, np.linspace(.003, .0015, 7), GRAPHITE, STEEL, 5)
            ball(p, whip[-1], .0045, brass, BRASS, 8)
        else:                                                     # the loupe pushed up at her right temple
            at = head.point(1.02, math.radians(52)) + head.normal(1.02, math.radians(52)) * .024
            pipe(p, curve([c + n_ * .014 + V(.01, 0, .012), c + n_ * .02 + V(.03, 0, .04), at + n_ * .006 + V(-.02, 0, -.012), at + V(-.004, .002, -.016)], 8),
                 .0028, brass, BRASS, 6)
            look = unit(head.normal(1.02, math.radians(52)) + V(.5, 0, .3))
            hoop(p, at, look, .017, .0034, brass, BRASS, 18, 6)
            turn(p, [(.0155, -.002), (.0155, .002), (.01, .0035), (0, .0045)], SENSOR, PAINT, 16, along(look), at, caps=(True, False))
    tilt = spin((1, 0, 0), 6) @ spin((0, 0, 1), -5)
    nod = V(.004, 0, 1.555)
    turned(p, h0, tilt, nod)
    mark(p, 'head', tilt @ (hc - nod) + nod)
    mark(p, 'head_top', tilt @ (hc + V(0, 0, .1) - nod) + nod)
    mark(p, 'eyes', tilt @ ((eyes[0] + eyes[1]) / 2 - nod) + nod)
    # ---- right arm (+y): shoulder, upper arm, and the pruning multi-tool for a forearm
    sh, el, m = V(-.005, .205, 1.41), V(0, .228, 1.13), V(.058, .225, .935)
    ball(p, sh, .046, GRAPHITE, STEEL, 16)
    cap = Hull(sh + V(0, .012, .012), (.062, .06, .058), .8, .8, basis((0, 1, 0), (0, 0, 1)))
    plate(p, cap, (.3, 1.75), _deg(-10, 190), worn(), PAINT, .007, .005, n=(3, 5), back=True, sag=.25, seed=60)
    limb_shell(p, rng, sh, el, .037, (0, 1, 0), [(18, 162, 20, 160), (25, 155, 200, 340)], colour=worn, seed=61)
    ball(p, el, .034, GRAPHITE, STEEL, 14)
    pivot(p, el, (0, 1, 0), .022, .088)
    limb_shell(p, rng, el, m, .034, (0, 1, 0), [(20, 160, 20, 160), (20, 160, 200, 340)], colour=worn, seed=63)
    f = unit(m - el)
    flat = V(0, 1.0, 0)
    u = np.cross(flat, f)
    pipe(p, [m - f * .012, m + f * .045], .04, GRAPHITE, STEEL, 24)
    sweep(p, [(.04, .012), (.0445, .014), (.0445, .03), (.04, .032)], brass, BRASS, sides=24, rot=along(f), origin=m)
    pv = m + f * .08
    obox(p, m + f * .058, (.03, .011, .015), FRAME, STEEL, .004, np.stack([f, flat, np.cross(f, flat)], 1))
    fl.blade(p, bezier(pv - f * .028, pv + f * .03 + u * .012, pv + f * .088 + u * .016, pv + f * .128, 10), np.linspace(.024, .004, 10),
             np.linspace(.005, .0015, 10), flat, BARE, BRIGHT)
    f2 = spin(flat, 30) @ f
    u2 = np.cross(flat, f2)
    fl.blade(p, bezier(pv - f2 * .024, pv + f2 * .03 - u2 * .016, pv + f2 * .08 - u2 * .028, pv + f2 * .116 - u2 * .012, 10), np.linspace(.02, .008, 10),
             np.linspace(.006, .003, 10), -flat, BARE, BRIGHT)
    for sg in (-1, 1):
        bolts(p, [pv + flat * sg * .005], flat * sg, .008, brass, BRASS)
    ram(p, m + f * .01 - u * .034, pv + f2 * .012 - u2 * .012, .0055, pin=flat)
    # the saw folded back along the forearm, and the probe
    q = np.linspace(0, 1, 17)
    back = m + flat * .043 - f * (.005 + .15 * q)[:, None]
    teeth = np.where(np.arange(17) % 2 == 0, .0, .0045)[:, None]
    lo_, hi_ = back - u * (.004 + teeth), back + u * .014
    slab(p, np.stack([lo_ + flat * .001, hi_ + flat * .001], 1), np.stack([lo_ - flat * .001, hi_ - flat * .001], 1), BARE, STEEL, BRIGHT, STEEL)
    bolts(p, [m + flat * .0445 + u * .004], flat, .007, brass, BRASS)
    prism(p, m + f * .03 - flat * .034, m + f * .17 - flat * .04, .0055, BRIGHT, STEEL, 6, .5)
    hose(p, curve([el + V(-.03, .0, -.03), el + f * .09 + V(-.045, 0, 0), m - f * .03 + V(-.04, 0, 0), m + f * .01 - u * .03], 9), .0045)
    # ---- left arm (-y): bent, the hand held out palm up
    sh, el, wr = V(-.005, -.205, 1.41), V(-.035, -.238, 1.135), V(.158, -.165, 1.1)
    ball(p, sh, .046, GRAPHITE, STEEL, 16)
    cap = Hull(sh + V(0, -.012, .012), (.062, .06, .058), .8, .8, basis((0, -1, 0), (0, 0, 1)))
    plate(p, cap, (.3, 1.75), _deg(-10, 190), worn(), PAINT, .007, .005, n=(3, 5), back=True, sag=.25, seed=70)
    limb_shell(p, rng, sh, el, .037, (0, -1, 0), [(18, 162, 20, 160), (25, 155, 200, 340)], colour=worn, seed=71)
    ball(p, el, .034, GRAPHITE, STEEL, 14)
    pivot(p, el, unit(np.cross(el - sh, wr - el)), .022, .088)
    limb_shell(p, rng, el, wr, .033, (0, 0, 1), [(18, 162, 20, 160), (22, 158, 200, 340)], colour=worn, seed=73)
    fore = unit(wr - el)
    palm = hand(p, rng, wr + fore * .012, aim((0, 0, -1), (.9, .42, .06)), 1.0, (.22, .28, .34, .42), .3, shell=worn())
    # ---- moss where the rain sits on her left shoulder, and a sprout in it
    for _ in range(7):
        moss_clump(p, rng, sh + V(rng.uniform(-.035, .03), rng.uniform(-.045, .01), .062 + rng.uniform(-.008, .006)), rng.uniform(.014, .026), .55)
    for _ in range(3):
        moss_clump(p, rng, V(-.06 + rng.uniform(-.02, .02), -.1 + rng.uniform(-.03, .03), 1.452), rng.uniform(.012, .02), .5)
    sprout = sh + V(-.01, -.03, .068)
    fl.leaves(p, np.tile(sprout, (3, 1)) + rng.uniform(-.004, .004, (3, 3)), [(.3, -.5, 1), (-.5, -.2, 1), (.1, .4, 1)], (0, 0, 1), [.03, .026, .022], .008,
              np.array([LEAF_LIGHT, LEAF_GREEN, LEAF_LIGHT]))
    # ---- the seedling in her palm: roots in a wrap of sacking tied with twine
    ball_ = palm + V(0, 0, .036)
    blob(p, ball_, .036, tone(TARP_OCHRE, .8), CLOTH, 2, .12, 5, (1, 1, .9))
    hoop(p, ball_ + V(0, 0, .012), (0, .15, 1), .034, .0028, tone(ROPE, 1.0), CLOTH, 16, 5)
    stem = curve([ball_ + V(0, 0, .03), ball_ + V(.006, .004, .08), ball_ + V(.0, .01, .13), ball_ + V(-.006, .012, .17)], 9)
    pipe(p, stem, np.linspace(.0042, .0018, 9), tone(GRASS, .9), LEAF, 5)
    lb = np.array([stem[i] for i in (3, 3, 5, 5, 7, 7, 8)])
    ld = np.array([(1, .3, .5), (-1, -.2, .5), (.2, 1, .5), (-.3, -1, .5), (.8, -.6, .6), (-.7, .6, .6), (.1, .1, 1)], np.float64)
    fl.leaves(p, lb, ld, (0, 0, 1), np.array([.05, .048, .044, .046, .036, .034, .03]), np.array([.014, .014, .012, .013, .01, .01, .009]),
              np.array([LEAF_GREEN, LEAF_LIGHT, LEAF_GREEN, LEAF_GREEN, LEAF_LIGHT, LEAF_LIGHT, LEAF_LIGHT]))
    # ---- the apron
    rows_ = np.array([(.54, .2, .178), (.7, .186, .162), (.9, .16, .132), (1.0, .15, .12), (1.07, .13, .106), (1.16, .137, .114), (1.25, .158, .126),
                      (1.34, .172, .132), (1.375, .17, .13)])

    def apron(theta, z, off=0.0, folds=True):
        theta, z = np.broadcast_arrays(np.asarray(theta, np.float64), np.asarray(z, np.float64))
        hw, fr = np.interp(z, rows_[:, 0], rows_[:, 1]), np.interp(z, rows_[:, 0], rows_[:, 2])
        c, s = np.cos(theta), np.sin(theta)
        x = np.where(c >= 0, fr, fr * .95) * np.sign(c) * np.abs(c) ** (2 / 2.6)
        y = hw * np.sign(s) * np.abs(s) ** (2 / 2.6)
        k = 1.0
        if folds:
            k = 1 + .075 * np.clip((1.07 - z) / .53, 0, 1) ** 1.3 * (.7 * np.cos(9.5 * theta + .4) + .3 * np.cos(17 * theta + 1.3))
        rad = np.maximum(np.hypot(x, y), 1e-6)
        return np.stack([x * k + off * x / rad, y * k + off * y / rad, z], -1)

    def reach(z):                                                   # how far round her the cloth goes at each height
        return np.radians(np.interp(z, [.54, 1.045, 1.095, 1.375], [104.0, 100.0, 74.0, 40.0]))
    canvas, hemmed = np.asarray(tone(CANVAS, 1.12))[:3], np.asarray(tone(CANVAS, .96))[:3]

    def cloth(P, base=canvas):
        z = P[..., 2]
        soil = np.clip((.95 - z) / .42, 0, 1) ** 1.4 * np.clip(.55 + .6 * noise2(P[..., 1] * 14, z * 9, 4), 0, 1) * .55
        fade = 1 + .08 * np.clip((z - 1.1) / .25, 0, 1) + .05 * noise2(P[..., 1] * 30, z * 30, 8)
        rgb = base * fade[..., None]
        return rgba(rgb * (1 - soil[..., None]) + np.asarray(mix(SOIL, CANVAS, .35)[:3]) * soil[..., None]).reshape(-1, 4)
    zs = np.r_[np.linspace(.54, 1.02, 15), 1.045, 1.07, 1.095, np.linspace(1.13, 1.375, 8)]
    us = np.linspace(-1, 1, 43)
    Zg, Ug = np.meshgrid(zs, us, indexing='ij')
    Tg = Ug * reach(Zg)
    outer = apron(Tg, Zg, .003)
    slab(p, outer, apron(Tg, Zg, -.003), cloth(outer), CLOTH, tone(CANVAS, .7), CLOTH)
    for z0, z1 in ((.54, .568), (1.348, 1.375)):                    # the hem, and the bib's top band
        Z2, U2 = np.meshgrid(np.array([z0, z1]), us, indexing='ij')
        o2 = apron(U2 * reach(Z2), Z2, .0068)
        slab(p, o2, apron(U2 * reach(Z2), Z2, .003), cloth(o2, hemmed), CLOTH, tone(CANVAS, .7), CLOTH)
    for sg in (-1, 1):                                              # the turned edges down both sides
        Z2, U2 = np.meshgrid(zs, np.array([.945, 1.0]) * sg, indexing='ij')
        o2 = apron(U2 * reach(Z2), Z2, .0068)
        slab(p, o2, apron(U2 * reach(Z2), Z2, .003), cloth(o2, hemmed), CLOTH, tone(CANVAS, .7), CLOTH)
    # the pocket and what she keeps in it
    Zp, Tp = np.meshgrid(np.linspace(.74, .93, 7), np.radians(np.linspace(-50, -16, 9)), indexing='ij')
    across = np.clip(np.sin(np.pi * (Tp - Tp.min()) / (Tp.max() - Tp.min())), 0, 1) ** .5
    bulge = .013 * np.clip(np.sin(np.pi * (Zp - .74) / .19), 0, 1) ** .6 * across + .0045
    o2 = apron(Tp, Zp, bulge + .0035)
    slab(p, o2, apron(Tp, Zp, .0035), cloth(o2, np.asarray(tone(CANVAS, .93)[:3])), CLOTH, tone(CANVAS, .7), CLOTH)
    Z2, T2 = np.meshgrid(np.array([.905, .93]), np.radians(np.linspace(-50, -16, 9)), indexing='ij')
    o2 = apron(T2, Z2, .012 + .009 * np.clip(np.sin(np.pi * (T2 - T2.min()) / (T2.max() - T2.min())), 0, 1) ** .5)
    slab(p, o2, apron(T2, Z2, .0075), cloth(o2, hemmed), CLOTH, tone(CANVAS, .7), CLOTH)
    mouth = apron(np.radians(-33), .93, .012)
    pipe(p, [mouth + V(-.004, .018, -.05), mouth + V(.002, .022, .075)], .011, tone(JUST_OLIVE, 1.1), PAINT, 10)          # a trowel's handle
    pipe(p, [mouth + V(.002, .022, .058), mouth + V(.002, .022, .07)], .0125, BARE, STEEL, 10)
    for dy in (-.03, -.018):
        pipe(p, curve([mouth + V(-.002, dy, -.04), mouth + V(.004, dy - .003, .03), mouth + V(.012, dy - .008, .065)], 6), .0045, tone(TARP_OCHRE, .9), PAINT, 6)
    for k in range(3):
        obox(p, mouth + V(.0, -.045 - .011 * k, .035), (.0012, .0065, .045), tone(FLOWER_WHITE, .8), PAINT, .0008, spin((1, 0, 0), -6 - 7 * k))
    # the waist tie, its bow and tails at her back, a ball of twine at her right hip
    Z2, T2 = np.meshgrid(np.array([1.045, 1.07, 1.095]), np.linspace(-math.pi, math.pi, 49), indexing='ij')
    o2 = apron(T2, Z2, .0095, False)
    slab(p, o2, apron(T2, Z2, .0045, False), cloth(o2, np.asarray(tone(CANVAS, .8)[:3])), CLOTH, tone(CANVAS, .65), CLOTH)
    knot_ = apron(math.pi, 1.07, .016, False)
    ball(p, knot_, .013, tone(CANVAS, .8), CLOTH, 10)
    for sg in (-1, 1):
        a = np.linspace(0, TAU, 14, endpoint=False)
        loop = knot_ + np.stack([-.008 - .006 * np.cos(2 * a), sg * (.012 + .03 * (1 - np.cos(a))), .018 * np.sin(a)], 1)
        pipe(p, loop, .0048, tone(CANVAS, .82), CLOTH, 6, closed=True)
        band(p, curve([knot_, knot_ + V(-.012, sg * .02, -.05), knot_ + V(-.02, sg * .03, -.11), knot_ + V(-.014, sg * .036, -.165)], 8), .02, .003,
             (-1, 0, 0), tone(CANVAS, .82))
    hang = apron(math.radians(96), 1.045, .012, False)
    pipe(p, [hang, hang + V(0, .004, -.05)], .0022, tone(ROPE, 1.0), CLOTH, 5)
    blob(p, hang + V(0, .006, -.078), .028, tone(ROPE, .95), CLOTH, 2, .06, 9)
    for k in range(3):
        hoop(p, hang + V(0, .006, -.078), unit(V(.3 * k - .3, .2, 1)), .0285, .0022, tone(ROPE, 1.1), CLOTH, 14, 4)
    # the neck strap over both shoulders on its brass rings
    corners = [apron(reach(1.375) * sg, 1.37, .005, False) for sg in (1, -1)]
    strap = curve([corners[0], V(.075, .075, 1.425), V(.02, .064, 1.466), V(-.04, .045, 1.478), V(-.073, 0, 1.47), V(-.04, -.045, 1.478), V(.02, -.064, 1.466),
                   V(.075, -.075, 1.425), corners[1]], 26)
    band(p, strap, .022, .004, unit(strap - V(0, 0, 1.38)), tone(CANVAS, .84))
    for c in corners:
        hoop(p, c + V(.003, 0, .012), (1, 0, 0), .012, .0026, brass, BRASS, 14, 5)
    weather(p, 601, 1.78, under=.2, dirt=.14, streak=.2, moss=.22, dust=.15)
    v = np.asarray(p.v, np.float64)
    return _moved(p, (0, 0, -v[:, 2].min()), 1.78 / float(v[:, 2].max() - v[:, 2].min()))


def fern(part, rng, base, lean=(0, 0, 1), count=6, length=.5):
    """A fern rooted at base: fronds arching out of a crown (leaning toward `lean`), each a rachis with paired pinnae
    that shorten toward its tip. Solid leaves on the LEAF slot."""
    base, lean = np.asarray(base, np.float64), np.asarray(lean, np.float64)
    B, D, Ln, Wd, C = [], [], [], [], []
    for k in range(count):
        a = k / count * TAU + rng.uniform(-.3, .3)
        out = unit(V(math.cos(a), math.sin(a), 0) + lean * .5)
        L = length * rng.uniform(.65, 1.1)
        rach = curve([base, base + out * L * .3 + UP * L * .42, base + out * L * .7 + UP * L * .46, base + out * L + UP * L * .12], 12)
        pipe(part, rach, np.linspace(L * .016, L * .004, 12), tone(GRASS, .8), LEAF, 4)
        tg = unit(np.gradient(rach, axis=0))
        for i in range(1, 12):
            q = i / 11
            w = L * .22 * math.sin(math.pi * min(q * 1.2, 1.0)) ** .7 * (1 - .55 * q) + L * .02
            side = unit(np.cross(tg[i], UP))
            for sg in (-1, 1):
                B.append(rach[i])
                D.append(unit(side * sg + tg[i] * .45 - UP * .12))
                Ln.append(w)
                Wd.append(w * .26)
                C.append(tone(mix(LEAF_GREEN, LEAF_LIGHT, rng.uniform(0, 1)), .8 + .2 * q))
    fl.leaves(part, np.array(B), np.array(D), (0, 0, 1), np.array(Ln), np.array(Wd), np.array(C))


BURR_PALM = 3.3        # the height his palms bear the slab at (README)


@built(.02)
def burr():
    """SM_GP_Burr (3.3 m as he kneels): the old Mechanoid loader who has held a fallen slab up for years. His right
    knee is down on its pad, his left foot planted ahead; a barrel chest leaning into the load, a pack with two
    stacks and a tank on his back; both arms raised, elbows forward, forearms upright with twin rams, and both hands
    flat, palms up, their load pads' faces exactly at z 3.3 (marks palm_right, palm_left: the pads' centres; nothing
    stands higher). A bowed head with one amber eye, the other dead. Enamel gone to cream, plates rusted through
    (RUST), moss where rain sits, ferns on a shoulder, his pack and his shin."""
    rng = np.random.default_rng(602)
    p = Part('SM_GP_Burr', (PAINT, STEEL, RUST, MOSS, LEAF, GLOW))
    upright = basis((0, 0, 1), (1, 0, 0))

    def old(w=.2):
        return tone(mix(JUST_BONE, TARP_OCHRE, rng.uniform(.12, .3)), rng.uniform(1 - w, .95))

    def olive():
        return tone(JUST_OLIVE, rng.uniform(.9, 1.2))

    def rusty():
        return tone(mix(RUST_ORANGE, RUST_DARK, rng.uniform(0, .6)))
    Hl, Kl, Al = V(-.1, -.42, 1.15), V(.72, -.5, 1.2), V(.62, -.5, .24)
    Hr, Kr, Ar = V(-.1, .42, 1.15), V(.3, .5, .2), V(-.78, .52, .28)
    # ---- left leg: the foot planted ahead
    limb_shell(p, rng, Hl, Kl, .24, (0, 0, 1), [(20, 160, 25, 155), (22, 158, 205, 335, 'rust')], colour=old, seed=1, rivet=.012)
    ball(p, Kl, .2, GRAPHITE, STEEL, 24)
    pivot(p, Kl, (0, 1, 0), .12, .52)
    pod(p, Kl + V(.15, 0, -.14), Kl + V(.2, 0, .16), .19, old(), PAINT, 18, .4, (1, 0, .3))
    limb_shell(p, rng, Kl, Al, .2, (1, 0, 0), [(15, 165, 30, 150), (25, 155, 210, 330)], colour=old, seed=3, rivet=.012)
    ball(p, Al, .15, GRAPHITE, STEEL, 20)
    pivot(p, Al, (0, 1, 0), .09, .42)
    obox(p, (.72, -.5, .07), (.37, .2, .07), rusty(), RUST, .03)
    pod(p, (.74, -.5, .16), (1.1, -.5, .12), .19, old(), PAINT, 18, .55, (0, 0, 1))
    obox(p, (.42, -.5, .17), (.1, .17, .09), GRAPHITE, STEEL, .03)
    obox(p, (.66, -.5, .21), (.16, .15, .03), olive(), PAINT, .012, basis((1, 0, -.25)))
    ram(p, V(.22, -.5, .96), V(.5, -.5, .56), .05, pin=(0, 1, 0))
    ram(p, V(-.34, -.42, 1.4), V(.26, -.46, 1.43), .045, pin=(0, 1, 0))
    # ---- right leg: the knee down on its pad, the shin along the ground, toes dug in behind
    limb_shell(p, rng, Hr, Kr, .24, (1, 0, .45), [(20, 160, 25, 155), (22, 158, 205, 335)], colour=old, seed=5, rivet=.012)
    ball(p, Kr, .2, GRAPHITE, STEEL, 24)
    pivot(p, Kr, (0, 1, 0), .12, .52)
    obox(p, (.44, .5, .07), (.13, .17, .07), RUBBER, PAINT, .03)
    limb_shell(p, rng, Kr, Ar, .2, (0, 0, 1), [(15, 165, 25, 155, 'rust'), (25, 155, 205, 335)], colour=old, seed=7, rivet=.012)
    ball(p, Ar, .15, GRAPHITE, STEEL, 20)
    pivot(p, Ar, (0, 1, 0), .09, .42)
    strut(p, Ar + V(-.04, 0, -.04), V(-1.06, .52, .11), .36, .15, rusty(), RUST, up=(.4, 0, 1), bevel=.03)
    obox(p, (-1.1, .52, .05), (.1, .19, .05), GRAPHITE, STEEL, .02)
    ram(p, V(-.04, .5, .96), V(-.28, .52, .34), .05, pin=(0, 1, 0))
    # ---- pelvis and hip bearings
    pelvis = Hull(V(-.1, 0, 1.22), (.32, .6, .44), .7, .7, upright)
    pelvis.core(p, GRAPHITE, STEEL, .04, (12, 36))
    for k, ph in enumerate(((-40, 40), (40, 140), (140, 220), (220, 320))):
        bx = plate(p, pelvis, (.55, 2.5), _deg(*ph), old(), PAINT, .03, .02, n=(3, 4), sag=.2, seed=10 + k)
        pelvis.rivet_row(p, (bx[0] + .08,) * 2, (bx[2] + .1, bx[3] - .1), 5, .014, BARE, STEEL)
    for s_, H in ((-1, Hl), (1, Hr)):
        side = V(0, s_, 0)
        pivot(p, H + side * .17, side, .2, .3)
        sweep(p, [(.2, 0), (.3, 0), (.3, .04), (.2, .04)], FRAME, STEEL, rot=along(side), origin=H + side * .2)
        ang = (np.arange(8) + .5) / 8 * TAU
        bolts(p, H + side * .24 + np.stack([.25 * np.cos(ang), np.zeros(8), .25 * np.sin(ang)], 1), side, .022)
    # ---- the chest, leaning into the load
    lean = unit(V(.14, 0, 1))
    fwd = np.cross(V(0, 1.0, 0), lean)
    chest = Hull(V(.03, 0, 1.9), (.62, .84, .58), .7, .7, basis(lean, (1, 0, 0)), taper=(.25, .15))
    t = .04
    chest.core(p, GRAPHITE, STEEL, t * 1.5, (20, 44))
    sectors = ((55, 125), (15, 55), (125, 165), (-25, 15), (165, 205), (205, 245), (295, 335), (245, 295))
    for i, th in enumerate(((.5, 1.15), (1.15, 1.85), (1.85, 2.55))):
        for j, (a, b) in enumerate(sectors):
            if (i == 2 and j in (3, 5)) or (i == 1 and j == 6):
                colour, slot = rusty(), RUST
            else:
                colour, slot = (olive() if j == 7 else old()), PAINT
            bx = plate(p, chest, th, _deg(a, b), colour, slot, t, .024, n=(3, 3), sag=.15, seed=20 + i * 8 + j)
            chest.rivet_row(p, (bx[0] + .05,) * 2, (bx[2] + .08, bx[3] - .08), 4, .016, BARE, STEEL)
    c, n_ = chest.point(1.5, math.pi / 2, -t * .1), chest.normal(1.5, math.pi / 2)
    face_ = basis(n_, lean)
    faded = tone(mix(JUST_ORANGE, JUST_BONE, .25), .85)
    for sg in (-1, 1):                                             # the Just's stripe, a chevron on his chest plate
        obox(p, c + face_ @ V(.006, sg * .13, 0), (.008, .17, .035), faded, PAINT, .004, face_ @ spin((1, 0, 0), sg * 32))
    for ph in (0, 180):
        louvre(p, chest.point(1.5, math.radians(ph), -t * .2), chest.normal(1.5, math.radians(ph)), lean, .34, .22, 6)
    hatch(p, chest, (2.0, 2.4), _deg(62, 100), old(), t * .5, 9)
    tag(p, chest.point(2.1, math.radians(118), -t * .15), chest.normal(2.1, math.radians(118)), lean, .16, .09)
    for ph in (62, 118):
        lug(p, chest.point(.62, math.radians(ph), -t * .2), chest.normal(.62, math.radians(ph)), .06, (0, 1, 0))
    for s_ in (-1, 1):                                             # rams between pelvis and chest: he is braced
        ram(p, V(.22, s_ * .42, 1.3), V(.36, s_ * .5, 1.78), .045, pin=(0, 1, 0))
        ram(p, V(-.42, s_ * .36, 1.34), V(-.46, s_ * .44, 1.86), .045, pin=(0, 1, 0))
    # ---- the pack on his back: louvres, two stacks, a tank, looms to the shoulders
    pack = np.stack([fwd, V(0, 1.0, 0), lean], 1)
    pc = V(-.62, 0, 1.98)
    obox(p, pc, (.2, .46, .36), olive(), PAINT, .04, pack)
    for dy in (-.22, .22):
        louvre(p, pc + pack @ V(-.2, dy, .06), -fwd, lean, .34, .3, 7)
    studs(p, [pc + pack @ V(-.202, sy * .42, sz * .32) for sy in (-1, 1) for sz in (-1, 1)], -fwd, .018)
    for s_ in (-1, 1):
        pipe(p, [(-.76, s_ * .3, 2.3), (-.84, s_ * .32, 2.6), (-.9, s_ * .32, 2.74)], [.08, .075, .07], rusty(), RUST, 18)
        hoop(p, (-.9, s_ * .32, 2.74), (-.4, 0, 1), .072, .014, GRAPHITE, STEEL, 18, 6)
        loom(p, curve([pc + V(.0, s_ * .4, .3), V(-.4, s_ * .6, 2.42), V(-.16, s_ * .78, 2.46), V(.0, s_ * .82, 2.36)], 10), .022, 3, 2)
    pipe(p, [(-.84, -.36, 1.7), (-.84, .36, 1.7)], .13, old(), PAINT, 24)
    for dy in (-.24, .24):
        hoop(p, (-.84, dy, 1.7), (0, 1, 0), .135, .014, BARE, STEEL, 24, 5)
    # ---- neck and the bowed head: one eye lit, one dead
    pipe(p, [V(.12, 0, 2.36), V(.25, 0, 2.52)], .16, GRAPHITE, STEEL, 24)
    for q in (.3, .62):
        hoop(p, V(.12, 0, 2.36) * (1 - q) + V(.25, 0, 2.52) * q, (.13, 0, .16), .17, .03, RUBBER, PAINT, 24, 6)
    hc = V(.33, 0, 2.63)
    hrot = basis((1, 0, -.3))
    look_, crown_ = hrot[:, 0], hrot[:, 2]
    head = Hull(hc, (.27, .27, .22), .7, .7, hrot)
    head.core(p, GRAPHITE, STEEL, .03, (14, 32))
    plate(p, head, (.95, 2.9), _deg(25, 155), old(), PAINT, .025, .016, n=(4, 5), sag=.15, seed=50)
    for k, ph in enumerate((_deg(-55, 25), _deg(155, 235))):
        plate(p, head, (.95, 2.7), ph, old(), PAINT, .025, .016, n=(4, 4), sag=.15, seed=51 + k)
    plate(p, head, (1.0, 2.5), _deg(235, 305), rusty(), RUST, .025, .016, n=(3, 3), sag=.15)
    plate(p, head, (.12, .9), (0.0, TAU), SENSOR, PAINT, .02, .012, n=(3, 24), lift=-.01, sag=.15, chip=0)
    plate(p, head, (.5, .98), _deg(18, 162), old(), PAINT, .03, 0.0, n=(3, 8), lift=.035, sag=.15, back=True, seed=54)     # the heavy brow
    lit, dead = math.radians(166), math.radians(14)
    soft_eye(p, head.point(.52, lit, .004), unit(head.normal(.52, lit) + look_ * .8), .055, crown_, .75, 1.0, old(), BARE, STEEL)
    sensor(p, head.point(.52, dead, .004), unit(head.normal(.52, dead) + look_ * .8), .05)
    mark(p, 'eye', head.point(.52, lit, -.02))
    louvre(p, head.point(.62, math.radians(270), -.005), head.normal(.62, math.radians(270)), V(0, 1.0, 0), .07, .2, 4)
    for s_ in (-1, 1):
        pivot(p, hc + V(-.06, s_ * .26, -.08), (0, 1, 0), .07, .06)
    mark(p, 'head', hc)
    mark(p, 'head_top', hc + crown_ * .22)
    # ---- the arms that hold the slab
    shoulders = {}
    for s_ in (-1, 1):
        sh, el, wr = V(.08, s_ * .95, 2.32), V(.6, s_ * 1.12, 2.44), V(.5, s_ * .95, BURR_PALM - .036 * 3.4)
        side = V(0, s_, 0)
        shoulders[s_] = sh
        pivot(p, sh, side, .24, .34)
        cap = Hull(sh + V(0, s_ * .06, .1), (.36, .36, .3), .8, .8, basis(side, (0, 0, 1)))
        for q, (a, b) in enumerate(((15, 90), (90, 165))):
            bx = plate(p, cap, (.3, 1.6), _deg(a, b), old(), PAINT, .035, .02, n=(3, 3), sag=.15, back=True, seed=60 + q)
            cap.rivet_row(p, (bx[1] - .08,) * 2, (bx[2] + .1, bx[3] - .1), 4, .016, BARE, STEEL)
        limb_shell(p, rng, sh, el, .2, (0, s_ * .5, 1), [(18, 162, 25, 155), (22, 158, 205, 335, 'rust')], colour=old, seed=62, rivet=.012)
        hinge_ = unit(np.cross(el - sh, wr - el))
        ball(p, el, .17, GRAPHITE, STEEL, 22)
        pivot(p, el, hinge_, .1, .44)
        limb_shell(p, rng, el, wr, .165, (1, 0, 0), [(15, 165, 30, 150), (20, 160, 210, 330)], colour=old, seed=64, rivet=.01)
        ram(p, V(.12, s_ * .74, 1.78), sh + (el - sh) * .55 + V(0, 0, -.2), .05, pin=(1, 0, 0))
        ram(p, sh + (el - sh) * .2 + V(0, 0, .2), el + (wr - el) * .3 + V(-.17, 0, 0), .045, pin=hinge_)
        for dx in (-.19, .19):
            ram(p, el + V(dx, s_ * .02, .1), wr + V(dx * .8, 0, -.12), .04, pin=(0, 1, 0))
        hose(p, curve([sh + V(-.1, 0, .2), (sh + el) / 2 + V(-.06, s_ * .16, .22), el + V(.0, s_ * .18, .12), el + (wr - el) * .5 + V(.02, s_ * .17, 0)], 12), .022)
        palm = hand(p, rng, wr, aim((0, 0, -1), V(-1.0, -s_ * .25, 0)), 3.4, (0, 0, 0, 0), 0.0, .12, shell=old(), right=s_ > 0, pad_thick=.022)
        mark(p, 'palm_right' if s_ > 0 else 'palm_left', palm)
    # ---- moss where the rain sits, and ferns
    def cushion(c, spread, count, r=(.05, .1), flat=.45):
        for _ in range(count):
            moss_clump(p, rng, np.asarray(c, np.float64) + rng.uniform(-1, 1, 3) * np.asarray(spread, np.float64), rng.uniform(*r), flat)
    for s_ in (-1, 1):
        cushion(shoulders[s_] + V(0, s_ * .06, .39), (.2, .16, .02), 9 if s_ > 0 else 6)
    cushion(hc + crown_ * .21 + V(-.04, 0, 0), (.12, .14, .015), 6, (.04, .07))
    cushion(head.point(.52, dead, -.03), (.03, .03, .03), 3, (.025, .04), .7)
    cushion(pc + V(-.02, 0, .37), (.14, .36, .01), 8)
    cushion((Hl + Kl) / 2 + V(0, 0, .25), (.3, .08, .015), 7)
    cushion((Kr + Ar) / 2 + V(0, 0, .21), (.36, .07, .015), 7)
    cushion(V(.8, -.5, .3), (.16, .1, .015), 4, (.04, .07))
    cushion(V(-.84, 0, 1.84), (.02, .3, .01), 4, (.04, .06))
    fern(p, rng, shoulders[1] + V(-.06, .1, .38), (0, .5, .3), 7, .5)
    fern(p, rng, pc + V(-.04, -.26, .36), (-.4, -.2, .3), 6, .42)
    fern(p, rng, V(-.3, .66, .36), (-.1, .6, .2), 6, .4)
    fern(p, rng, V(.02, -.56, 1.36), (.2, -.6, .2), 5, .3)
    weather(p, 602, 3.3, under=.3, dirt=.2, streak=.3, rust=.5, moss=.55, dust=.2)
    v = np.asarray(p.v, np.float64)
    if abs(v[:, 2].max() - BURR_PALM) > .002 or abs(v[:, 2].min()) > .02:
        raise ValueError('Burr stands %.3f .. %.3f m: his palms must be the top, at %.1f' % (v[:, 2].min(), v[:, 2].max(), BURR_PALM))
    return p


# ---------------------------------------------------------------- the module's meshes and their contract

MESHES = [link_node, link_source, link_receiver, link_relay, root_bridge, thorn_wall, thorn_cage, thorn_knot,
          wasp, lancet, burl, palisade, thresher, emitter, warden, harrow,
          thessaly, burr]
VARIANTS = {link_source: 3, link_receiver: 3, link_relay: 3}


def _flows(prefix, spec):
    return {prefix + name: dict(spec) for name, _ in FLOWS}


# Sizes in metres (x by y by z; 0 leaves an axis free). The link props are built in place, never re-centred, so their
# cores stay on the z axis at the heights their docstrings give.
def _hedge(x=0, y=0, z=0):
    """A unit of the Hedge: centred on its bounds, its largest dimension (the README's number) on the axis given."""
    return {'size': (x, y, z), 'tol': .02, 'pivot': 'centre'}


CONTRACT = {
    'SM_GE_Wasp': _hedge(x=.7, y=.7),
    'SM_GE_Lancet': _hedge(x=1.3),
    'SM_GE_Burl': _hedge(x=2.0),
    'SM_GE_Palisade': _hedge(z=1.9),
    'SM_GE_Thresher': _hedge(y=2.5),
    'SM_GE_Emitter': _hedge(y=1.2),
    'SM_GE_Warden': _hedge(z=7.5),
    'SM_GE_Harrow': _hedge(y=5.0),
    'SM_GP_Thessaly': {'size': (0, 0, 1.78), 'tol': .01, 'pivot': 'base'},
    'SM_GP_Burr': {'size': (0, 0, 3.3), 'tol': .005, 'pivot': 'base', 'top': 3.3},
    'SM_GN_LinkNode': {'size': (1.0, 1.0, 1.3), 'pivot': 'base'},
    **_flows('SM_GN_LinkSource', {'size': (1.6, 1.6, 1.8), 'pivot': 'base'}),
    **_flows('SM_GN_LinkReceiver', {'size': (1.4, 1.4, 1.6), 'pivot': 'base'}),
    **_flows('SM_GN_LinkRelay', {'size': (.9, .9, 1.4), 'pivot': 'base'}),
    'SM_GN_RootBridge': {'size': (20.0, 4.0, 3.0), 'pivot': 'any'},     # the pivot is the deck's top centre
    'SM_GN_ThornWall': {'size': (1.2, 8.0, 4.2), 'pivot': 'base'},
    'SM_GN_ThornCage': {'size': (1.5, 10.0, 7.0), 'pivot': 'base'},
    'SM_GN_ThornKnot': {'size': (1.0, 0, 0), 'pivot': 'centre'},       # 1.0 m across its largest dimension
}


if __name__ == '__main__':
    import check
    for _part in check.builds(sys.modules[__name__]):
        _v = np.asarray(_part.v)
        print('%s  %d tris  %s .. %s' % (_part.name, _part.triangles(), np.round(_v.min(0), 3).tolist(), np.round(_v.max(0), 3).tolist()))
        for _name, _q in getattr(_part, 'marks', {}).items():
            print('    %-16s %s' % (_name, np.round(_q, 3).tolist()))
