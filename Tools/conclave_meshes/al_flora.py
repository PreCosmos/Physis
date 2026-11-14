"""AL enemies and every plant of the Conclave (level 3): the SM_CE_* and SM_CV_* meshes of Tools/conclave/README.md.

Pure numpy through toolkit: check.py validates this module offline, Tools/build_physis_conclave.py builds it in
Blender.

The AL are the First Ones' automaton forces drawn as real machines: white enamelled and matte black plates over a
dark steel frame, split by seams, rolled at the edges and riveted, with articulated limbs and a red lens or core at
the front (+x) that reads as the weak point, because it is the brightest red on the unit. They hover, so their
pivot is the centre of their bounds: the scenario puts the origin at the hover height. The white plates are
CN_Lacquer, not CN_White: MI_CN_White carries marble veins, which would make a machine read as carved stone.

Plants stand on z 0; what lies on the ground or the water (litter, lily pads) or hangs from a wall (vines) keeps its
height above that pivot. Leaves, petals, blades, twigs and herbaceous stems are CN_Leaf (two-sided, never collides, and
swayed by the foliage material's wind, so a flower head never parts from its stem), so meadows and flower beds never
block the player; woody trunks and stems are CN_Bark, CN_Black or CN_White and collide.

Colour: every vertex holds a palette colour (palette.py). Shading a gold or a red too far turns it brown or
maroon, which the author's rule refuses, so all shading goes through tone() and shade(), which stop at the
darkest multiplier that keeps a colour in its family; and no face mixes two families, because a red-to-white
gradient across one face would render pink. Weathering lives in vertex colour: darker toward the ground and in
seams, crevices and the inside of crowns.
"""
import contextlib
import functools
import json
import math
import os
from pathlib import Path

import numpy as np

import toolkit
from palette import (ASH, BLACK, BLUE, BLUE_PALE, CHARCOAL, GOLD_DEEP, GOLD_GRASS, GOLD_STRAW, GREEN_GRASS, GREEN_LEAF,
                     GREEN_MOSS, GREEN_PALE, IVORY, LIGHT_BLUE, RED,
                     RED_BRIGHT, RED_DEEP, SLATE, WHITE, WHITE_COOL, WHITE_PURE, allowed, col)
from toolkit import Part, bevel_box, bezier, blob, frame, noise2, torus

TAU = 2 * math.pi
UP = np.array([0.0, 0.0, 1.0])
ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- colour that stays in the palette

_FLOORS = {}


def floor_of(colour):
    """The darkest shading multiplier that keeps colour in its palette family. Greys may go to black, but a gold
    turns brown and a red maroon below a certain value."""
    c = tuple(round(float(x), 4) for x in colour[:3])
    k = _FLOORS.get(c)
    if k is None:
        k = 0.0
        if not c[0] == c[1] == c[2]:
            k = 1.0
            while k > .03 and allowed([x * (k - .01) for x in c]):
                k -= .01
            k = min(1.0, k + .015)
        _FLOORS[c] = k
    return k


def _rgba(rgb):
    rgb = np.asarray(rgb, np.float64)
    return np.concatenate([rgb, np.ones(rgb.shape[:-1] + (1,))], -1)


def tone(colour, k=1.0):
    """colour times shading k (a number or an array), kept inside its family and at most 0.9 albedo."""
    c = np.asarray(colour, np.float64)[:3]
    lo = floor_of(c)
    hi = max(.9 / max(c.max(), 1e-6), 1.0) if c.max() <= .9 else 1.0
    k = np.clip(np.asarray(k, np.float64), lo, max(hi, lo))
    return _rgba(np.multiply.outer(k, c))


def glow(colour, k=1.0):
    """A light colour at brightness k (the glow material's emissive is the vertex colour), never so dim that a
    red light turns maroon."""
    c = np.asarray(colour, np.float64)[:3]
    return _rgba(np.multiply.outer(np.maximum(np.asarray(k, np.float64), floor_of(c)), c))


def mix(a, b, t):
    """Linear blend of two colours of one family (t a number or an array)."""
    a, b = np.asarray(a, np.float64)[:3], np.asarray(b, np.float64)[:3]
    t = np.asarray(t, np.float64)[..., None]
    return _rgba(a * (1 - t) + b * t)


def shade(part, k, start=0, keep=('CN_Glow',)):
    """Darkens every vertex from start by k (one per vertex: occlusion, grime), each colour within its own family.
    Vertices of faces in the keep slots (lights) keep their brightness."""
    cols = np.asarray(part.c[start:], np.float64)
    k = np.minimum(np.broadcast_to(np.asarray(k, np.float64), (len(cols),)), 1.0)
    lit_slots = [part.slots.index(s) for s in keep if s in part.slots]
    if lit_slots:
        lit = np.zeros(len(part.c), bool)
        for f, m in zip(part.f, part.m):
            if m in lit_slots:
                lit[f] = True
        k = np.where(lit[start:], 1.0, k)
    floors = np.array([floor_of(c) for c in cols])
    cols[:, :3] *= np.maximum(k, floors)[:, None]
    part.c[start:] = cols.tolist()


# ---------------------------------------------------------------- tessellation

# Round primitives (limb, ball, joint, ring, disc, prism, Hull.core) take their sides times this factor. The AL are built
# at AL_DETAIL (al_detail): they fill the screen in a fight, where their 6 to 16 sided limbs, rings and cores read as
# polygons. Plants are built at 1, so their triangle counts do not change.
_detail = 1.0
AL_DETAIL = 2.0


@contextlib.contextmanager
def detail(factor):
    """Builds every round primitive inside the block at factor times its sides."""
    global _detail
    before, _detail = _detail, factor
    try:
        yield
    finally:
        _detail = before


def sides_of(sides):
    return max(3, int(round(sides * _detail)))


def al_detail(builder):
    """An AL builder, run at AL_DETAIL."""
    @functools.wraps(builder)
    def build():
        with detail(AL_DETAIL):
            return builder()
    return build


# ---------------------------------------------------------------- geometry helpers

def unit(v):
    v = np.asarray(v, np.float64)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def basis(forward, up=(0, 0, 1)):
    """Rotation (columns forward, right, up) for parts built in a local frame of x forward, y right, z up. A
    proper rotation, so faces keep their outward winding."""
    f = unit(forward)
    u = np.asarray(up, np.float64)
    if abs(np.dot(f, unit(u))) > .98:
        u = np.array([1.0, 0, 0]) if abs(f[0]) < .9 else np.array([0, 0, 1.0])
    u = unit(u - f * np.dot(f, u))
    return np.stack([f, np.cross(u, f), u], 1)


def along(axis):
    """Rotation taking local z to axis: rings, discs and lenses are built around z."""
    a, b = frame(axis)
    return np.stack([a, b, unit(axis)], 1)


def place(part, start, rot=None, origin=(0, 0, 0)):
    """Moves every vertex added since start from its local frame: rot, then origin."""
    v = np.asarray(part.v[start:], np.float64)
    if rot is not None:
        v = v @ np.asarray(rot, np.float64).T
    part.v[start:] = (v + np.asarray(origin, np.float64)).tolist()


def _facing(verts, face, direction):
    """face wound so its front (Newell normal, robust for quads that are not quite planar) points along direction."""
    p = np.asarray(verts, np.float64)[face]
    n = np.cross(p, np.roll(p, -1, 0)).sum(0)
    return list(face) if np.dot(n, direction) >= 0 else list(face)[::-1]


def _transport(v, t0, t1):
    """v carried by the rotation that takes direction t0 to t1 (parallel transport of a tube's frame)."""
    axis = np.cross(t0, t1)
    s = np.linalg.norm(axis)
    if s < 1e-9:
        return v
    axis = axis / s
    ang = math.atan2(s, float(np.clip(np.dot(t0, t1), -1, 1)))
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * np.dot(axis, v) * (1 - math.cos(ang))


def limb(part, points, radii, colour, slot=0, sides=6, cap=True, smooth=True):
    """A tube along a polyline whose ring frame is carried along the curve, so a branch or cable that bends through
    vertical never twists or pinches (toolkit.tube re-picks its frame per point). colour: one, or one per point.
    The caps are separate flat faces so they do not smear the side shading."""
    sides = sides_of(sides)
    pts = np.asarray(points, np.float64)
    n = len(pts)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (n,))
    tang = unit(np.gradient(pts, axis=0))
    a = frame(tang[0])[0]
    ang = np.linspace(0, TAU, sides, endpoint=False)
    cs, sn = np.cos(ang)[:, None], np.sin(ang)[:, None]
    rings = []
    for i in range(n):
        if i:
            a = _transport(a, tang[i - 1], tang[i])
        a = unit(a - tang[i] * np.dot(a, tang[i]))
        rings.append(pts[i] + radii[i] * (cs * a + sn * np.cross(tang[i], a)))
    verts = np.concatenate(rings)
    faces = [[i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j]
             for i in range(n - 1) for j in range(sides)]
    cols = np.asarray(colour, np.float64)
    per_point = cols.ndim == 2 and len(cols) == n
    start = part.add(verts, faces, np.repeat(cols, sides, 0) if per_point else cols, slot, smooth)
    if cap:
        ends = np.concatenate([verts[:sides], verts[-sides:]])
        end_cols = np.concatenate([np.repeat(cols[:1], sides, 0), np.repeat(cols[-1:], sides, 0)]) if per_point else cols
        part.add(ends, [list(range(sides))[::-1], list(range(sides, 2 * sides))], end_cols, slot, False)
    return start


def _band(part, prof, ang, colour, slot, smooth=True):
    n = len(ang)
    verts = np.concatenate([np.stack([np.cos(ang) * r, np.sin(ang) * r, np.full(n, z)], 1) for r, z in prof])
    faces = [[i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j]
             for i in range(len(prof) - 1) for j in range(n)]
    return part.add(verts, faces, colour, slot, smooth)


def ring(part, profile, colour, slot=0, sides=16, rot=None, origin=(0, 0, 0), hard=True):
    """A closed solid of revolution around local z from a closed profile [(radius, z), ...] that never touches the
    axis: bezels, nozzles, barrels, collars. With hard, each profile segment is its own band, so machined corners
    stay crisp under smooth shading. The profile may run either way round."""
    prof = [tuple(map(float, q)) for q in profile]
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(prof, prof[1:] + prof[:1])) < 0:
        prof = prof[::-1]  # counter-clockwise in (r, z) puts every face's front outside the solid
    loop = prof + prof[:1]
    start = len(part.v)
    ang = np.linspace(0, TAU, sides_of(sides), endpoint=False)
    if hard:
        for a, b in zip(loop, loop[1:]):
            _band(part, [a, b], ang, colour, slot)
    else:
        _band(part, loop, ang, colour, slot)
    place(part, start, rot, origin)
    return start


def disc(part, centre, axis, r, colour, slot=0, sides=12, dome=0.0, rim=None):
    """A round fan facing along axis (glow fields, lamp faces, pads); rim gives the edge its own colour, for a
    light that falls off toward its edge."""
    sides = sides_of(sides)
    ang = np.linspace(0, TAU, sides, endpoint=False)
    local = np.concatenate([[(0.0, 0.0, dome)], np.stack([np.cos(ang) * r, np.sin(ang) * r, np.zeros(sides)], 1)])
    verts = local @ along(axis).T + np.asarray(centre, np.float64)
    cols = colour if rim is None else np.concatenate([np.asarray(colour, np.float64).reshape(1, -1),
                                                      np.tile(np.asarray(rim, np.float64), (sides, 1))])
    return part.add(verts, [[0, 1 + j, 1 + (j + 1) % sides] for j in range(sides)], cols, slot, True)


def ball(part, c, r, colour, slot=0, sides=8, squash=(1, 1, 1)):
    """A low UV sphere: ball joints, fruit, buds. Cheaper than an icosphere where it is small."""
    sides = sides_of(sides)
    rows = max(2, sides // 2)
    lat = np.linspace(-math.pi / 2, math.pi / 2, rows + 1)[1:-1]
    ang = np.linspace(0, TAU, sides, endpoint=False)
    rings = [np.stack([np.cos(ang) * math.cos(a), np.sin(ang) * math.cos(a), np.full(sides, math.sin(a))], 1) for a in lat]
    local = np.concatenate([[(0, 0, -1.0)]] + rings + [[(0, 0, 1.0)]]) * np.asarray(squash, np.float64) * r
    top = len(local) - 1
    faces = [[0, 1 + (j + 1) % sides, 1 + j] for j in range(sides)]
    for i in range(len(lat) - 1):
        faces += [[1 + i * sides + j, 1 + i * sides + (j + 1) % sides, 1 + (i + 1) * sides + (j + 1) % sides,
                   1 + (i + 1) * sides + j] for j in range(sides)]
    o = 1 + (len(lat) - 1) * sides
    faces += [[o + j, o + (j + 1) % sides, top] for j in range(sides)]
    return part.add(local + np.asarray(c, np.float64), faces, colour, slot, True)


def prism(part, base, tip, r, colour, slot=0, sides=6, tip_len=.3, smooth=False):
    """toolkit.prism (a pointed spike or crystal) at the current tessellation."""
    return toolkit.prism(part, base, tip, r, colour, slot, sides_of(sides), tip_len, smooth)


def obox(part, centre, half, colour, slot=0, bevel=.02, rot=None):
    """A bevelled box in any orientation (toolkit.bevel_box only yaws)."""
    start = bevel_box(part, (0, 0, 0), half, colour, slot, bevel)
    place(part, start, rot, centre)
    return start


def strut(part, a, b, w, h, colour, slot=0, up=(0, 0, 1), bevel=.01, pad=0.0):
    """A bevelled bar from a to b, w wide and h deep (limb segments, frame members, ribs)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    return obox(part, (a + b) / 2, (np.linalg.norm(b - a) / 2 + pad, w / 2, h / 2), colour, slot, bevel, basis(b - a, up))


def hinge(part, c, axis, r, length, colour, slot=0, sides=10):
    """A hinge pin: a short cylinder across a joint, so limbs read as articulated rather than bent."""
    c, d = np.asarray(c, np.float64), unit(axis)
    return limb(part, [c - d * length / 2, c + d * length / 2], r, colour, slot, sides)


def piston(part, a, b, r, sleeve, rod, slot=0, sides=8):
    """A hydraulic ram between a and b: a sleeve and a bright rod sliding out of it."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    limb(part, [a, a + (b - a) * .58], r, sleeve, slot, sides)
    limb(part, [a + (b - a) * .5, b], r * .55, rod, slot, sides)


def slab(part, outer, inner, colour, slot=0, rim=None, rim_slot=None, back=True, smooth=True):
    """A plate with real thickness between two matching point grids (nu x nv): armour panels, shields, fins,
    blades. Face, back and rim are separate vertex sets so the rim stays a crisp edge under smooth shading, and
    every face turns away from the plate. back=False leaves out the back where a core always hides it."""
    outer, inner = np.asarray(outer, np.float64), np.asarray(inner, np.float64)
    nu, nv = outer.shape[:2]
    lift = outer - inner
    flat_o, flat_i = outer.reshape(-1, 3), inner.reshape(-1, 3)
    faces_o, faces_i = [], []
    for u in range(nu - 1):
        for v in range(nv - 1):
            q = [u * nv + v, (u + 1) * nv + v, (u + 1) * nv + v + 1, u * nv + v + 1]
            d = lift[u:u + 2, v:v + 2].reshape(-1, 3).mean(0)
            faces_o.append(_facing(flat_o, q, d))
            faces_i.append(_facing(flat_i, q, -d))
    part.add(flat_o, faces_o, colour, slot, smooth)
    if back:
        part.add(flat_i, faces_i, colour, slot, smooth)
    loop = ([(u, 0) for u in range(nu)] + [(nu - 1, v) for v in range(1, nv)] +
            [(u, nv - 1) for u in range(nu - 2, -1, -1)] + [(0, v) for v in range(nv - 2, 0, -1)])
    mid = (outer + inner) / 2

    def inward(q):
        u, v = q
        return (u + (1 if u == 0 else -1 if u == nu - 1 else 0), v + (1 if v == 0 else -1 if v == nv - 1 else 0))
    m = len(loop)
    verts = np.concatenate([np.array([outer[q] for q in loop]), np.array([inner[q] for q in loop])])
    faces = []
    for i in range(m):
        a, b = loop[i], loop[(i + 1) % m]
        d = (mid[a] + mid[b]) / 2 - (mid[inward(a)] + mid[inward(b)]) / 2
        faces.append(_facing(verts, [i, (i + 1) % m, m + (i + 1) % m, m + i], d))
    part.add(verts, faces, colour if rim is None else rim, slot if rim_slot is None else rim_slot, False)


def fin(part, corners, thick, colour, slot=0, rim=None, rim_slot=None, taper=.45, n=(3, 3)):
    """A flat plate fin from four corners (root front, root back, tip back, tip front), thinning toward its
    trailing edge like a real vane."""
    rf, rb, tb, tf = (np.asarray(c, np.float64) for c in corners)
    nrm = unit(np.cross(rb - rf, tf - rf))
    us, vs = np.linspace(0, 1, n[0]), np.linspace(0, 1, n[1])
    grid = np.array([[(rf * (1 - u) + rb * u) * (1 - v) + (tf * (1 - u) + tb * u) * v for v in vs] for u in us])
    half = (thick / 2) * (1 - taper * us)[:, None, None] * (1 - .35 * vs)[None, :, None]
    slab(part, grid + nrm * half, grid - nrm * half, colour, slot, rim, rim_slot)


def rivets(part, points, normals, r, colour, slot=0):
    """Dome-headed rivets as six-sided studs: tiny, but they make a plate read as fastened."""
    pts = np.asarray(points, np.float64).reshape(-1, 3)
    nrm = unit(np.asarray(normals, np.float64).reshape(-1, 3))
    if not len(pts):
        return
    ang = np.linspace(0, TAU, 6, endpoint=False)
    verts, faces = [], []
    for i, (q, n) in enumerate(zip(pts, nrm)):
        a, b = frame(n)
        verts.extend((q - n * r * .3 + r * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b)).tolist())
        verts.append((q + n * r * .5).tolist())
        faces += [[i * 7 + j, i * 7 + (j + 1) % 6, i * 7 + 6] for j in range(6)]
    part.add(verts, faces, colour, slot, True)


def _spow(x, e):
    return np.sign(x) * np.abs(x) ** e


class Hull:
    """A superellipsoid body around local x (its front is the +x pole), placed by rot and centre. e1 shapes the
    profile along x (below 1 boxier, above 1 pointed), e2 the cross-section; taper widens (y) and deepens (z) the
    front. Plates are cut from its surface as thick slabs with seams between them, over a dark core."""

    def __init__(self, centre, radii, e1=1.0, e2=1.0, rot=None, taper=(0.0, 0.0)):
        self.c = np.asarray(centre, np.float64)
        self.r = np.asarray(radii, np.float64)
        self.e1, self.e2 = e1, e2
        self.rot = np.eye(3) if rot is None else np.asarray(rot, np.float64)
        self.taper = taper

    def local(self, th, ph):
        th, ph = np.broadcast_arrays(np.asarray(th, np.float64), np.asarray(ph, np.float64))
        x = self.r[0] * _spow(np.cos(th), self.e1)
        s = _spow(np.sin(th), self.e1)
        fx = x / self.r[0]
        y = self.r[1] * s * _spow(np.cos(ph), self.e2) * (1 + self.taper[0] * fx)
        z = self.r[2] * s * _spow(np.sin(ph), self.e2) * (1 + self.taper[1] * fx)
        return np.stack([x, y, z], -1)

    def point(self, th, ph, depth=0.0):
        """Surface point at (th, ph), moved depth metres toward the centre (negative lifts it off)."""
        p = self.local(th, ph)
        if np.any(depth):
            p = p * (1 - np.asarray(depth, np.float64)[..., None] / np.maximum(np.linalg.norm(p, axis=-1, keepdims=True), 1e-9))
        return self.c + p @ self.rot.T

    def normal(self, th, ph):
        e = 1e-4
        n = unit(np.cross(self.point(th + e, ph) - self.point(th - e, ph), self.point(th, ph + e) - self.point(th, ph - e)))
        out = self.point(th, ph) - self.c
        return np.where((np.sum(n * out, -1) < 0)[..., None], -n, n)

    def core(self, part, colour, slot, depth=0.0, n=(10, 16)):
        """The closed body under the plates; seams show it, so it is dark. Poles are single vertices."""
        nu, nv = sides_of(n[0]), sides_of(n[1])
        th = np.linspace(0, math.pi, nu + 1)[1:-1]
        ph = np.linspace(0, TAU, nv, endpoint=False)
        T, P = np.meshgrid(th, ph, indexing='ij')
        verts = np.concatenate([self.point(0.0, 0.0, depth).reshape(1, 3), self.point(T, P, depth).reshape(-1, 3),
                                self.point(math.pi, 0.0, depth).reshape(1, 3)])
        last, faces = len(verts) - 1, []
        for j in range(nv):
            k = (j + 1) % nv
            faces.append([0, 1 + j, 1 + k])
            faces += [[1 + i * nv + j, 1 + (i + 1) * nv + j, 1 + (i + 1) * nv + k, 1 + i * nv + k] for i in range(nu - 2)]
            faces.append([1 + (nu - 2) * nv + j, last, 1 + (nu - 2) * nv + k])
        faces = [_facing(verts, f, verts[f].mean(0) - self.c) for f in faces]
        return part.add(verts, faces, colour, slot, True)

    def _span(self, a, b, n, thick, size):
        e = min(.2, 1.4 * thick / max(abs(b - a) * size, 1e-6))
        return np.concatenate([[a], np.linspace(a + (b - a) * e, b - (b - a) * e, max(n, 2)), [b]])

    def plate(self, part, th, ph, colour, slot, thick=.02, gap=.012, roll=.55, n=(2, 2), rim=None, rim_slot=None,
              lift=0.0, back=False, sag=.3, seal=2.2):
        """A plate over th = (from, to) and ph = (from, to) radians, inset by half the seam gap on every side, its
        border rolled toward the core so it reads as pressed armour rather than a cut shell. n is the least
        resolution; the grid is refined until no edge sags more than sag x thick below the true surface, because a
        flat facet across a curved plate would let the core show through it. Its edge runs down to seal x thick
        under the surface, past the core (1.5 x thick): a seam seen at a grazing angle then ends on the core instead
        of opening onto the plate's own underside, which has no faces when back is False and would show the sky
        through the unit. Returns the inset ranges, for rivets."""
        rm = float(np.mean(self.r))
        sm = max(abs(math.sin((th[0] + th[1]) / 2)), .25)
        dt, dp = gap / 2 / rm, gap / 2 / (rm * sm)
        t0, t1, p0, p1 = th[0] + dt, th[1] - dt, ph[0] + dp, ph[1] - dp
        n0, n1 = n
        for _ in range(10):
            us, vs = self._span(t0, t1, n0, thick, rm), self._span(p0, p1, n1, thick, rm * sm)
            Ui, Vi = np.meshgrid(us[1:-1], vs[1:-1], indexing='ij')
            P = self.point(Ui, Vi)
            eu = np.linalg.norm(self.point((Ui[:-1] + Ui[1:]) / 2, Vi[:-1]) - (P[:-1] + P[1:]) / 2, axis=-1).max()
            ev = np.linalg.norm(self.point(Ui[:, :-1], (Vi[:, :-1] + Vi[:, 1:]) / 2) - (P[:, :-1] + P[:, 1:]) / 2, axis=-1).max()
            if max(eu, ev) <= sag * thick:
                break
            if eu >= ev:
                n0 += 1
            else:
                n1 += 1
        U, V = np.meshgrid(us, vs, indexing='ij')
        border = np.zeros(U.shape, bool)
        border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
        depth = np.where(border, roll * thick, 0.0) - lift
        inner = np.where(border, max(seal * thick, thick - lift), thick - lift)
        slab(part, self.point(U, V, depth), self.point(U, V, inner), colour, slot, rim, rim_slot, back)
        return t0, t1, p0, p1

    def rivet_row(self, part, th, ph, count, r, colour, slot, lift=0.0):
        """count rivets along the line from (th[0], ph[0]) to (th[1], ph[1]) on the plate surface."""
        t = np.linspace(0, 1, count)
        T, P = th[0] + (th[1] - th[0]) * t, ph[0] + (ph[1] - ph[0]) * t
        rivets(part, self.point(T, P, -lift), self.normal(T, P), r, colour, slot)


# ---------------------------------------------------------------- AL: the First Ones' automaton forces

ENAMEL = 'CN_Lacquer'  # white plates: glossy enamel (CN_White's marble veins would read as stone on a machine)
AL_SLOTS = ('CN_Metal', 'CN_Black', ENAMEL, 'CN_Glow')
STEEL, STEEL_LIGHT, SOOT = SLATE, ASH, CHARCOAL
EDGE = tone(ASH, 1.5)  # bright worn steel: blade edges, piston rods
# The AL's red light, pure red (palette.py is not edited; this passes allowed()): exposure lifted LIGHT_RED's 6 % green
# and 4 % blue into coral and salmon on screen, and the glow material keeps a red light's red channel only.
GLOW_RED = col(1.0, .005, .004)
# Hover emitters and thrusters glow at this, far under a lens's 1.0, so the lens stays the brightest red on every unit.
EMITTER_GLOW = .15


def _ceramic(rng, wear=.16):
    """A white enamelled plate: each batch a little warmer or cooler, some more worn."""
    return tone(mix(WHITE_COOL, WHITE, rng.uniform(0, .7)), rng.uniform(1 - wear, 1.0))


def _black(rng):
    return tone(mix(BLACK, CHARCOAL, rng.uniform(0, .8)))


def lens(part, centre, axis, r, bright=1.0, level=2, sides=18, housing=SOOT):
    """A sensor lens: red light domed out of a steel bezel, brightest at its centre like a lit lens behind glass.
    It is the brightest red on every AL, so the player reads it as the weak point."""
    rot = along(axis)
    ring(part, [(r * .98, r * .2), (r * .98, -r * .45), (r * 1.45, -r * .45), (r * 1.52, r * .02), (r * 1.34, r * .3),
                (r * 1.08, r * .32)], tone(housing), 'CN_Metal', sides, rot, centre)
    start = len(part.v)
    blob(part, (0, 0, -r * .1), (r, r, r * .62), GLOW_RED, 'CN_Glow', level, 0.0, 0)
    v = np.asarray(part.v[start:])
    part.c[start:] = glow(GLOW_RED, bright * (1 - .55 * np.clip(np.hypot(v[:, 0], v[:, 1]) / r, 0, 1) ** 2)).tolist()
    place(part, start, rot, centre)


def emitter(part, centre, axis, r, bright=EMITTER_GLOW, colour=GLOW_RED, sides=16):
    """A hover emitter: a steel collar round a dim field of AL light, facing axis (down for lift)."""
    ring(part, [(r * .76, r * .14), (r * .76, -r * .3), (r * 1.0, -r * .34), (r * 1.07, 0.0), (r * .96, r * .2)],
         tone(STEEL), 'CN_Metal', sides, along(axis), centre)
    disc(part, np.asarray(centre, np.float64) - unit(axis) * r * .08, axis, r * .8, glow(colour, bright), 'CN_Glow', sides,
         -r * .12, glow(colour, bright * .45))


def nozzle(part, centre, axis, r, length, bright=EMITTER_GLOW, colour=GLOW_RED, sides=16):
    """A thruster bell with a dim glow at its throat; axis points the way the exhaust leaves."""
    L = length
    ring(part, [(r * .9, L), (r * .5, L * .2), (r * .62, -L * .05), (r * .86, L * .5), (r, L), (r * .95, L * 1.04)],
         tone(STEEL), 'CN_Metal', sides, along(axis), centre)
    disc(part, np.asarray(centre, np.float64) + unit(axis) * L * .24, axis, r * .52, glow(colour, bright), 'CN_Glow', sides,
         0.0, glow(colour, bright * .5))


def vent(part, centre, normal, up, w, h, slats=4, colour=SOOT):
    """A louvred vent proud of a hull: a dark frame and angled slats, normal pointing out of the surface."""
    rot = basis(normal, up)
    c = np.asarray(centre, np.float64)
    d = min(w, h) * .12
    obox(part, c, (d, w / 2, h / 2), tone(colour), 'CN_Metal', d * .4, rot)
    tilt = basis((1, 0, -.6), (0.6, 0, 1))
    for k in range(slats):
        z = -h / 2 + h * (k + .5) / slats
        obox(part, c + rot @ np.array([d * 1.1, 0, z]), (d * .35, w / 2 * .88, h / slats * .34), tone(STEEL, 1.4),
             'CN_Metal', d * .15, rot @ tilt)


def joint(part, c, r, colour=STEEL, sides=8):
    return ball(part, c, r, tone(colour), 'CN_Metal', sides)


def blade(part, curve, width, thick, side, colour=SOOT, edge=EDGE):
    """A blade along curve, width wide at each point, its spine thick and its cutting edge sharp, the steel
    brightening toward the honed edge. side is the blade plane's normal (the flat faces look along it)."""
    C = np.asarray(curve, np.float64)
    nu, nv = len(C), 4
    T = unit(np.gradient(C, axis=0))
    N = unit(np.asarray(side, np.float64) - T * (T @ np.asarray(side, np.float64))[:, None])
    Wd = unit(np.cross(N, T))
    s = np.linspace(0, 1, nv)
    width = np.broadcast_to(np.asarray(width, np.float64), (nu,))
    thick = np.broadcast_to(np.asarray(thick, np.float64), (nu,))
    mid = C[:, None, :] + Wd[:, None, :] * (width[:, None] * s[None, :])[..., None]
    half = (thick[:, None] * (1 - .92 * s[None, :] ** 1.4) / 2)[..., None]
    outer, inner = mid + N[:, None, :] * half, mid - N[:, None, :] * half
    cols = mix(colour, edge, np.tile(s ** 2, (nu, 1)))
    start = len(part.v)
    slab(part, outer, inner, tone(colour), 'CN_Metal', tone(colour), 'CN_Metal')
    # The honed edge: per-vertex steel brightness by distance across the blade (face and back only).
    grid = np.concatenate([cols.reshape(-1, 4), cols.reshape(-1, 4)])
    part.c[start:start + len(grid)] = grid.tolist()


def _finish_al(part, dark=.3):
    """Grime and shadow gather under a hovering machine; then the bounds are centred on the origin, where the
    scenario holds the hover height."""
    v = np.asarray(part.v, np.float64)
    lo, hi = v.min(0), v.max(0)
    shade(part, 1 - dark * (1 - (v[:, 2] - lo[2]) / max(hi[2] - lo[2], 1e-6)) ** 1.5)
    part.v = (v - (lo + hi) / 2).tolist()
    return part


def _deg(a, b):
    return math.radians(a), math.radians(b)


@al_detail
def al_mite():
    """Level 1: the smallest AL, a quick swarm drone. A riveted carapace over a big lens, mandibles framing the
    lens, six short legs folded under like an insect's, a hover emitter beneath."""
    rng = np.random.default_rng(301)
    p = Part('SM_CE_ALMite', AL_SLOTS)
    hull = Hull((0, 0, 0), (.19, .155, .115), .85, .8)
    t = .011
    hull.core(p, tone(SOOT), 'CN_Metal', t * 1.5, (8, 14))
    for th in ((.62, 1.3), (1.3, 1.95), (1.95, 2.7)):
        b = hull.plate(p, th, _deg(30, 150), _ceramic(rng), ENAMEL, t, .008, n=(3, 4))
        hull.rivet_row(p, (b[0] + .09,) * 2, (b[2] + .18, b[3] - .18), 4, .0045, tone(STEEL_LIGHT), 'CN_Metal')
        for ph in (_deg(-40, 30), _deg(150, 220)):
            hull.plate(p, th, ph, _black(rng), 'CN_Black', t, .008, n=(3, 2))
    hull.plate(p, (.85, 2.45), _deg(220, 320), tone(STEEL), 'CN_Metal', t, .01, n=(3, 3))
    lens(p, (.168, 0, .012), (1, 0, .06), .05, level=1, sides=14)
    for s in (-1, 1):
        root = np.array([.12, s * .08, -.05])
        joint(p, root, .02, sides=6)
        limb(p, bezier(root, root + (.08, s * .035, -.012), (.28, s * .07, -.07), (.33, s * .028, -.05), 7),
             np.linspace(.016, .003, 7), tone(SOOT), 'CN_Metal', 6)
        for i, x in enumerate((.07, -.03, -.12)):
            hip = np.array([x, s * .122, -.035])
            knee = np.array([x + .035 - i * .035, s * .245, .035])
            foot = np.array([x + .06 - i * .075, s * .272, -.135])
            joint(p, hip, .016, sides=6)
            strut(p, hip, knee, .022, .016, _black(rng), 'CN_Black', bevel=.004)
            joint(p, knee, .012, sides=6)
            limb(p, [knee, (knee + foot) / 2 + (0, s * .018, 0), foot], [.0095, .0075, .0018], tone(STEEL), 'CN_Metal', 5)
        limb(p, bezier((-.1, s * .045, .095), (-.17, s * .06, .12), (-.23, s * .085, .13), (-.285, s * .1, .15), 5),
             np.linspace(.005, .0018, 5), tone(SOOT), 'CN_Metal', 4)
    emitter(p, (-.02, 0, -.098), (0, 0, -1), .07, sides=14)
    nozzle(p, (-.178, 0, .01), (-1, 0, 0), .04, .05, sides=12)
    vent(p, (-.04, 0, .118), (0, 0, 1), (-1, 0, 0), .05, .05, 3)
    return _finish_al(p)


@al_detail
def al_lancer():
    """Level 2: a ranged drone slung over a long emitter, focusing rings down the barrel and a red bore at its
    muzzle; the lens that reads as its weak point sits above the emitter's root."""
    rng = np.random.default_rng(302)
    p = Part('SM_CE_ALLancer', AL_SLOTS)
    hull = Hull((-.2, 0, .04), (.34, .19, .16), .9, .75, taper=(-.25, -.15))
    t = .014
    hull.core(p, tone(SOOT), 'CN_Metal', t * 1.5, (10, 16))
    for th in ((.5, 1.05), (1.05, 1.6), (1.6, 2.15), (2.15, 2.75)):
        b = hull.plate(p, th, _deg(35, 145), _ceramic(rng), ENAMEL, t, .01, n=(3, 5))
        hull.rivet_row(p, (b[0] + .07,) * 2, (b[2] + .14, b[3] - .14), 5, .0055, tone(STEEL_LIGHT), 'CN_Metal')
        for ph in (_deg(-45, 35), _deg(145, 225)):
            hull.plate(p, th, ph, _black(rng), 'CN_Black', t, .01, n=(3, 3))
    hull.plate(p, (.8, 2.5), _deg(225, 315), tone(STEEL), 'CN_Metal', t, .012, n=(4, 3))
    lens(p, hull.point(.16, math.pi / 2, .012), (1, 0, .3), .045, level=2, sides=16)
    # The emitter, built along local z and laid along +x under the nose.
    rot, o = along((1, 0, 0)), np.array([-.02, 0, -.07])
    ring(p, [(.03, 0), (.078, 0), (.082, .13), (.052, .165), (.03, .165)], _black(rng), 'CN_Black', 16, rot, o)
    ring(p, [(.02, .1), (.036, .1), (.036, .56), (.02, .56)], tone(STEEL), 'CN_Metal', 14, rot, o)
    for z in (.24, .33, .42):
        ring(p, [(.034, z), (.05, z + .005), (.053, z + .022), (.05, z + .036), (.034, z + .04)], _ceramic(rng),
             ENAMEL, 16, rot, o)
    ring(p, [(.022, .53), (.05, .53), (.058, .6), (.049, .64), (.026, .64)], tone(STEEL, 1.3), 'CN_Metal', 16, rot, o)
    disc(p, o + (.6, 0, 0), (1, 0, 0), .024, glow(GLOW_RED, .75), 'CN_Glow', 10, 0, glow(GLOW_RED, .4))
    for k in range(6):
        a = k / 6 * TAU
        obox(p, o + (.075, math.cos(a) * .095, math.sin(a) * .095), (.05, .004, .016), tone(STEEL), 'CN_Metal', .002,
             basis((1, 0, 0), (0, math.cos(a), math.sin(a))))
    obox(p, (.06, 0, -.02), (.07, .05, .035), _black(rng), 'CN_Black', .01)
    for s in (-1, 1):
        fin(p, [(-.33, s * .12, .12), (-.52, s * .08, .1), (-.61, s * .31, .31), (-.47, s * .31, .31)], .014,
            _black(rng), 'CN_Black', tone(STEEL_LIGHT), 'CN_Metal')
        nozzle(p, (-.5, s * .06, .03), (-1, 0, 0), .045, .07, sides=12)
        emitter(p, (-.2, s * .09, -.105), (0, 0, -1), .045, sides=12)
    fin(p, [(-.3, 0, -.1), (-.52, 0, -.07), (-.6, 0, -.27), (-.49, 0, -.27)], .012, _black(rng), 'CN_Black',
        tone(STEEL_LIGHT), 'CN_Metal')
    limb(p, bezier((-.3, 0, .17), (-.36, 0, .2), (-.42, 0, .23), (-.47, 0, .255), 4), np.linspace(.006, .002, 4),
         tone(SOOT), 'CN_Metal', 4)
    vent(p, hull.point(1.6, math.radians(10), -.002), hull.normal(1.6, math.radians(10)), (0, 0, 1), .07, .05, 3)
    vent(p, hull.point(1.6, math.radians(170), -.002), hull.normal(1.6, math.radians(170)), (0, 0, 1), .07, .05, 3)
    return _finish_al(p)


def _shield(part, rng, side, z0, z1, centre_x=-.25, radius=.86, a0=14.0, a1=72.0, thick=.045):
    """One layer of a Bulwark's shield: a slab curved round the body and bulging in z, white ceramic with a steel
    rim and a row of rivets down its outer edge."""
    A = np.radians(np.linspace(a0, a1, 7))
    Z = np.linspace(z0, z1, 5)
    Ag, Zg = np.meshgrid(A, Z, indexing='ij')
    R = radius - .2 * (Zg / 1.0) ** 2

    def at(rr):
        return np.stack([centre_x + rr * np.cos(Ag), side * rr * np.sin(Ag), Zg], -1)
    slab(part, at(R + thick / 2), at(R - thick / 2), _ceramic(rng, .1), ENAMEL, tone(STEEL_LIGHT), 'CN_Metal')
    # A raised black band across the layer: shields were reinforced, and it breaks the big white face.
    Ab, Zb = np.meshgrid(A[1:-1], np.array([-.035, .035]) + (z0 + z1) / 2, indexing='ij')
    Rb = radius - .2 * Zb ** 2 + thick / 2

    def band(rr):
        return np.stack([centre_x + rr * np.cos(Ab), side * rr * np.sin(Ab), Zb], -1)
    slab(part, band(Rb + .02), band(Rb - .004), _black(rng), 'CN_Black', back=False)
    for a in (a0 + 3.5, a1 - 3.5):
        zz = np.linspace(z0 + .05, z1 - .05, 5)
        aa = np.full(5, math.radians(a))
        rr = radius - .2 * zz ** 2 + thick / 2
        rivets(part, np.stack([centre_x + rr * np.cos(aa), side * rr * np.sin(aa), zz], 1),
               np.stack([np.cos(aa), side * np.sin(aa), -.4 * zz], 1), .011, tone(STEEL_LIGHT), 'CN_Metal')
    mid = math.radians((a0 + a1) / 2)
    zc = (z0 + z1) / 2
    rr = radius - .2 * zc ** 2 - thick / 2
    return np.array([centre_x + rr * math.cos(mid), side * rr * math.sin(mid), zc])


@al_detail
def al_bulwark():
    """Level 3: a heavy AL plated against the blade. Layered ceramic shields wrap its front on hinged, ram-driven
    arms and leave a slot where its red core shows."""
    rng = np.random.default_rng(303)
    p = Part('SM_CE_ALBulwark', AL_SLOTS)
    hull = Hull((-.15, 0, 0), (.48, .46, .72), .75, .7)
    t = .03
    hull.core(p, tone(SOOT), 'CN_Metal', t * 1.5, (12, 18))
    sectors = [(22.5, 67.5, 'w'), (67.5, 112.5, 'w'), (112.5, 157.5, 'w'), (-22.5, 22.5, 'k'), (157.5, 202.5, 'k'),
               (202.5, 247.5, 'k'), (247.5, 292.5, 'm'), (292.5, 337.5, 'k')]
    for th in ((.36, .9), (.9, 1.55), (1.55, 2.2), (2.2, 2.8)):
        for a, b, kind in sectors:
            colour, slot = {'w': (_ceramic(rng), ENAMEL), 'k': (_black(rng), 'CN_Black'), 'm': (tone(STEEL), 'CN_Metal')}[kind]
            box_ = hull.plate(p, th, _deg(a, b), colour, slot, t, .018)
            if kind == 'w':
                hull.rivet_row(p, (box_[0] + .05,) * 2, (box_[2] + .1, box_[3] - .1), 4, .009, tone(STEEL_LIGHT), 'CN_Metal')
    lens(p, (.31, 0, .04), (1, 0, 0), .12, level=2, sides=20)
    for zc in (-.28, .36):
        obox(p, (.3, 0, zc), (.03, .09, .05), _black(rng), 'CN_Black', .012)
    for s in (-1, 1):
        for z0, z1 in ((-1.0, -.38), (-.35, .35), (.38, 1.0)):
            inner = _shield(p, rng, s, z0, z1)
            body = np.array([.0, s * .36, (z0 + z1) / 2])
            hinge(p, body, (0, 0, 1), .045, .16, tone(STEEL))
            strut(p, body, inner, .07, .1, _black(rng), 'CN_Black', bevel=.015)
            hinge(p, inner + (-.03, -s * .02, 0), (0, 0, 1), .04, .14, tone(STEEL))
            piston(p, body + (-.05, 0, .09), inner + (-.05, -s * .03, .1), .022, tone(SOOT), EDGE, 'CN_Metal')
        emitter(p, (-.15, s * .22, -.69), (0, 0, -1), .16, sides=16)
        vent(p, hull.point(1.6, math.radians(0 if s > 0 else 180), -.004), hull.normal(1.6, math.radians(0 if s > 0 else 180)),
             (0, 0, 1), .16, .22, 5)
    for k, (x0, x1, h) in enumerate(((.05, -.25, .2), (-.28, -.5, .26), (-.53, -.7, .16))):
        z = .64 - .05 * k
        fin(p, [(x0, 0, z), (x1, 0, z - .02), (x1 - .06, 0, z + h), (x0 - .12, 0, z + h)], .03, _black(rng), 'CN_Black',
            tone(STEEL_LIGHT), 'CN_Metal')
    nozzle(p, (-.6, 0, .12), (-1, 0, 0), .12, .13, sides=18)
    for k in range(5):
        y = -.24 + k * .12
        fin(p, [(-.55, y, -.18), (-.55, y, -.42), (-.74, y, -.4), (-.72, y, -.2)], .016, tone(STEEL), 'CN_Metal', taper=.2)
    return _finish_al(p)


@al_detail
def echo_hunter():
    """Level 4: an AL that copied the Lightforms' speed: a long dart of black and white plates swept back into
    blade wings, light-blue light streaming down its seams and wing edges, a red seeker lens at its nose."""
    rng = np.random.default_rng(304)
    p = Part('SM_CE_EchoHunter', AL_SLOTS)
    hull = Hull((-.05, 0, 0), (.77, .17, .13), 1.05, .8, taper=(-.2, -.1))
    t = .012
    hull.core(p, tone(SOOT), 'CN_Metal', t * 1.5, (14, 16))
    for th in ((.3, .95), (.95, 1.6), (1.6, 2.25), (2.25, 2.8)):
        hull.plate(p, th, _deg(42, 138), _ceramic(rng, .08), ENAMEL, t, .014, n=(5, 4))
        for ph in (_deg(-42, 42), _deg(138, 222)):
            hull.plate(p, th, ph, _black(rng), 'CN_Black', t, .014, n=(5, 3))
        hull.plate(p, th, _deg(222, 318), _black(rng), 'CN_Black', t, .014, n=(5, 3))
    streak = glow(LIGHT_BLUE, .85)
    ths = np.linspace(.32, 2.75, 16)
    for ph in (math.radians(42), math.radians(138)):
        limb(p, hull.point(ths, np.full(16, ph), t * .35), np.linspace(.004, .0065, 16), streak, 'CN_Glow', 5)
    lens(p, hull.point(0.0, 0.0) + (-.012, 0, 0), (1, 0, 0), .04, level=2, sides=16)
    for s in (-1, 1):
        wing = [(.05, s * .13, -.01), (-.38, s * .15, -.015), (-.64, s * .47, -.06), (-.42, s * .47, -.06)]
        fin(p, wing, .02, _black(rng), 'CN_Black', tone(STEEL_LIGHT), 'CN_Metal', n=(3, 4))
        a, b = np.array(wing[0]), np.array(wing[3])
        limb(p, [a + (0, 0, .004) + (b - a) * k for k in np.linspace(.05, .97, 8)], .0055, glow(LIGHT_BLUE, .9), 'CN_Glow', 5)
        fin(p, [(.34, s * .06, 0), (.21, s * .08, 0), (.13, s * .19, -.02), (.2, s * .19, -.02)], .012, _ceramic(rng),
            ENAMEL, tone(STEEL_LIGHT), 'CN_Metal')
        boom = np.array([[-.36, s * .12, -.005], [-.6, s * .135, -.01], [-.78, s * .14, -.01]])
        limb(p, boom, [.03, .028, .026], _black(rng), 'CN_Black', 8)
        nozzle(p, boom[-1] + (-.01, 0, 0), (-1, 0, 0), .04, .07, .45, LIGHT_BLUE, sides=12)
    fin(p, [(-.25, 0, .1), (-.55, 0, .08), (-.71, 0, .25), (-.6, 0, .25)], .016, _ceramic(rng), ENAMEL,
        tone(STEEL_LIGHT), 'CN_Metal')
    limb(p, [np.array([-.27 - .33 * k, 0, .105 + .14 * k]) for k in np.linspace(.08, .95, 7)], .005, streak, 'CN_Glow', 5)
    fin(p, [(-.32, 0, -.1), (-.5, 0, -.09), (-.6, 0, -.2), (-.5, 0, -.2)], .012, _black(rng), 'CN_Black',
        tone(STEEL_LIGHT), 'CN_Metal')
    emitter(p, (-.1, 0, -.125), (0, 0, -1), .05, .3, LIGHT_BLUE, 12)
    return _finish_al(p, .2)


def _segment(part, rng, centre, axis, radius, length, white=True):
    """A ring of abdomen or tendril armour: a short hull with a ceramic or black shell over its core."""
    hull = Hull(centre, (length / 2, radius, radius), .7, .8, basis(axis, (1, 0, 0) if abs(unit(axis)[2]) > .7 else (0, 0, 1)))
    t = max(.01, radius * .12)
    hull.core(part, tone(SOOT), 'CN_Metal', t * 1.5, (6, 10))
    hull.plate(part, (.35, 2.8), _deg(-200, 20), _ceramic(rng) if white else _black(rng), ENAMEL if white else 'CN_Black',
               t, radius * .1, n=(3, 4))
    hull.plate(part, (.35, 2.8), _deg(20, 160), _black(rng), 'CN_Black', t, radius * .1, n=(3, 3))
    return hull


@al_detail
def al_reaver():
    """Level 4: a guard of the swarm. A hunched torso under heavy pauldrons, a narrow head with its red lens
    forward, mantis arms ending in long scythe blades, and a segmented tail that carries its hover emitter."""
    rng = np.random.default_rng(305)
    p = Part('SM_CE_ALReaver', AL_SLOTS)
    spine = unit((.38, 0, 1))
    torso = Hull((0, 0, .2), (.52, .4, .34), .82, .75, basis(spine, (1, 0, -.38)), taper=(.38, .22))
    t = .026
    torso.core(p, tone(SOOT), 'CN_Metal', t * 1.5, (12, 18))
    # Local +z of the torso faces the chest (world +x): sectors around the spine axis.
    for th in ((.32, .95), (.95, 1.65), (1.65, 2.4)):
        for a, b in ((55, 125), (125, 180), (0, 55)):
            box_ = torso.plate(p, th, _deg(a, b), _ceramic(rng), ENAMEL, t, .016)
            torso.rivet_row(p, (box_[0] + .05,) * 2, (box_[2] + .1, box_[3] - .1), 3, .008, tone(STEEL_LIGHT), 'CN_Metal')
        for a, b in ((180, 240), (240, 300), (300, 360)):
            torso.plate(p, th, _deg(a, b), _black(rng), 'CN_Black', t, .016)
    head = Hull((.42, 0, .8), (.2, .13, .115), .9, .8)
    head.core(p, tone(SOOT), 'CN_Metal', .018, (8, 14))
    head.plate(p, (.5, 2.6), _deg(25, 155), _ceramic(rng, .06), ENAMEL, .012, .01, n=(4, 4))
    for ph in (_deg(-50, 25), _deg(155, 230)):
        head.plate(p, (.5, 2.6), ph, _black(rng), 'CN_Black', .012, .01, n=(4, 3))
    lens(p, (.6, 0, .8), (1, 0, -.1), .055, level=2, sides=18)
    fin(p, [(.45, 0, .9), (.2, 0, .9), (.12, 0, 1.02), (.3, 0, .97)], .02, _black(rng), 'CN_Black', tone(STEEL_LIGHT), 'CN_Metal')
    for k in np.linspace(0, 1, 3):
        c = np.array([.17, 0, .66]) * (1 - k) + np.array([.3, 0, .76]) * k
        joint(p, c, .055, sides=8)
    for s in (-1, 1):
        pad = Hull((.08, s * .44, .62), (.24, .2, .15), .8, .75)
        pad.plate(p, (.3, 2.8), _deg(0, 180), _ceramic(rng), ENAMEL, .022, .01, n=(4, 4), back=True)
        prism(p, (.02, s * .5, .72), (-.1, s * .58, 1.2), .05, _black(rng), 'CN_Black', 5, .45)
        prism(p, (.14, s * .5, .7), (.08, s * .58, 1.02), .035, _black(rng), 'CN_Black', 5, .45)
        sh, el, wr = np.array([.12, s * .5, .46]), np.array([.32, s * .66, .02]), np.array([.74, s * .55, .44])
        joint(p, sh, .09, sides=10)
        strut(p, sh, el, .11, .13, _ceramic(rng), ENAMEL, bevel=.02)
        hinge(p, el, (0, 1, 0), .06, .16, tone(STEEL))
        strut(p, el, wr, .08, .1, _black(rng), 'CN_Black', bevel=.016)
        piston(p, sh + (.06, 0, -.08), el + (.06, 0, .06), .022, tone(SOOT), EDGE, 'CN_Metal')
        hinge(p, wr, (0, 1, 0), .05, .13, tone(STEEL))
        curve = bezier(wr, wr + (.34, 0, .06), (1.02, s * .46, -.25), (.82, s * .38, -.72), 12)
        blade(p, curve, np.linspace(.14, .012, 12) * np.sin(np.linspace(.6, 2.9, 12)) ** .4, np.linspace(.036, .01, 12),
              (0, s, 0))
        emitter(p, (-.04, s * .18, -.2), (0, 0, -1), .08, sides=14)
    # The tail: overlapping segments, each a little smaller and swept further back, like an insect's abdomen.
    prev = np.array([-.04, 0, -.18])
    for k in range(6):
        c = np.array([-.06 - .05 * k - .012 * k * k, 0, -.3 - .135 * k])
        r = .16 - .014 * k
        _segment(p, rng, c, c - prev, r, .2, white=k % 2 == 0)
        prev = c
    emitter(p, prev + (-.03, 0, -.1), (-.3, 0, -1), .09, sides=14)
    for k in range(4):
        z = .62 - .2 * k
        x = -.32 + .08 * k / 3
        fin(p, [(x, 0, z), (x - .02, 0, z - .14), (x - .2, 0, z - .1), (x - .18, 0, z + .02)], .02, _black(rng), 'CN_Black',
            tone(STEEL_LIGHT), 'CN_Metal')
    return _finish_al(p)


def _claw(part, rng, wrist, forward, spread, length, fingers=3, r=.05, knuckles=True):
    """A grapple: a palm block and curled fingers tipped with talons, opening along forward."""
    f = unit(forward)
    side = unit(np.cross(f, UP)) if abs(f[2]) < .9 else np.array([0, 1.0, 0])
    up = np.cross(side, f)
    obox(part, wrist + f * r * 1.2, (r * 1.3, r * 1.5, r * 1.1), _black(rng), 'CN_Black', r * .3, basis(f, up))
    for k in range(fingers):
        a = (k / max(fingers - 1, 1) - .5) * 2 * spread if fingers > 1 else 0.0
        root = wrist + f * r * 2.2 + side * math.sin(a) * r * 1.4 + up * math.cos(a) * r * .5
        out = unit(f + side * math.sin(a) * .9 + up * math.cos(a) * .25)
        mid = root + out * length * .55
        tip = mid + unit(f - up * .9 - out * .3) * length * .5
        if knuckles:
            joint(part, root, r * .55, sides=6)
        limb(part, [root, mid], [r * .45, r * .38], tone(SOOT), 'CN_Metal', 5, cap=False)
        joint(part, mid, r * .42, sides=6)
        prism(part, mid, tip, r * .36, tone(EDGE), 'CN_Metal', 5, .6)


def _arm(part, rng, sh, el, wr, r, white_upper=True, ram=True):
    """An articulated arm: shoulder ball, armoured upper arm, hinged elbow, forearm, and a ram across the elbow.
    One segment is white ceramic and the other black, white_upper choosing which."""
    sh, el, wr = (np.asarray(x, np.float64) for x in (sh, el, wr))
    axis = unit(np.cross(el - sh, wr - el))
    white, black = (_ceramic(rng), ENAMEL), (_black(rng), 'CN_Black')
    upper, lower = (white, black) if white_upper else (black, white)
    joint(part, sh, r * 1.25, sides=8)
    strut(part, sh, el, r * 1.25, r * 1.4, upper[0], upper[1], bevel=r * .22)
    hinge(part, el, axis, r * .75, r * 1.9, tone(STEEL), 10)
    strut(part, el, wr, r * .95, r * 1.05, lower[0], lower[1], bevel=r * .18)
    if ram:
        lift = unit(np.cross(axis, el - sh)) * r * .9
        piston(part, sh + (el - sh) * .2 + lift, el + lift * .8, r * .28, tone(SOOT), EDGE, 'CN_Metal', 6)


@al_detail
def al_siegeframe():
    """Level 5, end-game: a station-breaker. A long armoured frame behind a toothed cutter ring with the red core at
    its centre, four grapple arms for gripping hulls, and a bank of thrusters behind heat-sink fins."""
    rng = np.random.default_rng(306)
    p = Part('SM_CE_ALSiegeframe', AL_SLOTS)
    hull = Hull((-.32, 0, .1), (1.76, 1.0, .8), .65, .6, taper=(.08, .05))
    t = .065
    hull.core(p, tone(SOOT), 'CN_Metal', t * 1.5, (8, 16))
    sectors = [(40, 90, 'w'), (90, 140, 'w'), (8, 40, 'w'), (140, 172, 'w'), (-32, 8, 'k'), (172, 212, 'k'), (212, 328, 'm')]
    for th in ((.38, .95), (.95, 1.55), (1.55, 2.2), (2.2, 2.85)):
        for a, b, kind in sectors:
            colour, slot = {'w': (_ceramic(rng), ENAMEL), 'k': (_black(rng), 'CN_Black'), 'm': (tone(STEEL), 'CN_Metal')}[kind]
            box_ = hull.plate(p, th, _deg(a, b), colour, slot, t, .035, sag=1.1)
            if kind == 'w':
                hull.rivet_row(p, (box_[0] + .035,) * 2, (box_[2] + .07, box_[3] - .07), 3, .02, tone(STEEL_LIGHT), 'CN_Metal')
    # The frame: girders along the body and hoops across it, raised over the plates.
    for ph in (62, 118, 6, 174):
        hull.plate(p, (.45, 2.78), _deg(ph - 3.2, ph + 3.2), _black(rng), 'CN_Black', .08, .0, n=(6, 2), lift=.07, sag=1.4)
    for th in (1.25, 2.2):
        hull.plate(p, (th - .035, th + .035), _deg(-30, 210), tone(STEEL), 'CN_Metal', .08, .0, n=(2, 7), lift=.08, sag=1.4)
    # The breaching head.
    front = np.array([1.3, 0, .1])
    ring(p, [(.56, 0), (.8, 0), (.84, .2), (.74, .34), (.6, .32)], tone(STEEL), 'CN_Metal', 28, along((1, 0, 0)), front)
    for k in range(14):
        a = k / 14 * TAU
        d = np.array([0, math.cos(a), math.sin(a)])
        base = front + (.3, 0, 0) + d * .68
        prism(p, base, base + (.32, 0, 0) + d * .1, .07, tone(EDGE), 'CN_Metal', 4, .55)
    for k in range(4):
        a = k / 4 * TAU + math.pi / 4
        d = np.array([0, math.cos(a), math.sin(a)])
        strut(p, front + (.12, 0, 0) + d * .3, front + (.12, 0, 0) + d * .6, .08, .1, _black(rng), 'CN_Black',
              up=(1, 0, 0), bevel=.02)
    ring(p, [(.22, -.25), (.36, -.25), (.38, .1), (.33, .2), (.24, .18)], tone(SOOT), 'CN_Metal', 20, along((1, 0, 0)), front)
    lens(p, front + (.12, 0, 0), (1, 0, 0), .2, level=2, sides=16)
    # Grapple arms: two forward, two folded down like legs that grip a hull.
    for s in (-1, 1):
        _arm(p, rng, (.6, s * .98, -.12), (1.15, s * 1.6, -.32), (1.95, s * 1.32, -.55), .13)
        _claw(p, rng, np.array([1.95, s * 1.32, -.55]), (1, -s * .35, -.2), .7, .44, 3, .085, knuckles=False)
        _arm(p, rng, (-.75, s * 1.0, -.22), (-.3, s * 1.66, -.72), (.12, s * 1.42, -1.12), .11, ram=False)
        _claw(p, rng, np.array([.12, s * 1.42, -1.12]), (.3, -s * .2, -1), .6, .34, 2, .075, knuckles=False)
        emitter(p, (-.35, s * .42, -.68), (0, 0, -1), .3, sides=14)
    for y, z in ((0, .4), (-.46, -.02), (.46, -.02)):
        nozzle(p, (-2.02, y, z + .05), (-1, 0, 0), .26, .34, sides=12)
    for k in range(6):
        a = k / 6 * TAU + math.pi / 6
        d = np.array([0, math.cos(a), math.sin(a)])
        r0 = .6
        fin(p, [np.array([-1.7, 0, .1]) + d * r0, np.array([-2.08, 0, .1]) + d * r0, np.array([-2.18, 0, .1]) + d * (r0 + .3),
                np.array([-1.76, 0, .1]) + d * (r0 + .32)], .03, tone(STEEL), 'CN_Metal', tone(STEEL_LIGHT), 'CN_Metal', taper=.2)
    limb(p, bezier((-.7, .3, .86), (-.85, .32, 1.05), (-1.05, .34, 1.15), (-1.3, .38, 1.2), 5), np.linspace(.03, .01, 5),
         tone(SOOT), 'CN_Metal', 6)
    return _finish_al(p)


@al_detail
def al_shepherd():
    """Boss: the command unit that herds the swarm, 7 m tall. A tall plated torso opened at the front like a ribcage
    round the red relay at its heart (held in a gimbal, the brightest light on it), a helmed head under a crown of
    antennae, long arms with a comms staff, and a lamellar skirt trailing segmented tendrils."""
    rng = np.random.default_rng(307)
    p = Part('SM_CE_ALShepherd', AL_SLOTS)
    upright = basis((0, 0, 1), (1, 0, 0))  # local x up, local z to the front (world +x): phi 90 faces forward
    torso = Hull((0, 0, .55), (1.5, 1.0, .82), .8, .75, upright, taper=(.18, .1))
    t = .05
    window = (.72, 1.9)
    for th in ((.3, .72), (.72, 1.3), (1.3, 1.9), (1.9, 2.5)):
        for a, b, kind in ((52, 128, 'w'), (128, 190, 'w'), (350, 412, 'w'), (190, 270, 'k'), (270, 350, 'k')):
            if a == 52 and window[0] - 1e-6 <= th[0] and th[1] <= window[1] + 1e-6:
                continue
            colour, slot = (_ceramic(rng), ENAMEL) if kind == 'w' else (_black(rng), 'CN_Black')
            box_ = torso.plate(p, th, _deg(a, b), colour, slot, t, .03, sag=1.1)
            if kind == 'w' and th[0] > .5:
                torso.rivet_row(p, (box_[0] + .035,) * 2, (box_[2] + .07, box_[3] - .07), 3, .022, tone(STEEL_LIGHT), 'CN_Metal')
    torso.plate(p, (2.5, 2.95), _deg(0, 360), _black(rng), 'CN_Black', t, .0, n=(2, 8))
    # The inner core. Its grid lines run along the window's edges, so the window is an exact hole in it, and a dark
    # socket runs from that hole back to a wall behind the relay: every line of sight through the window ends on a
    # front face (socket, gimbal, relay), never inside the torso, whose culled back faces would show the sky.
    depth = t * 1.5
    th_all = np.array([.393, window[0], 1.178, 1.571, window[1], 2.356, 2.749])
    ph_all = np.radians(np.r_[0.0, 25.71, 52.0, 77.14, 102.86, 128.0, np.arange(6, 14) * 360.0 / 14])
    nu, nv = len(th_all), len(ph_all)
    T, P = np.meshgrid(th_all, ph_all, indexing='ij')
    verts = np.concatenate([torso.point(0.0, 0.0, depth).reshape(1, 3), torso.point(T, P, depth).reshape(-1, 3),
                            torso.point(math.pi, 0.0, depth).reshape(1, 3)])
    rows, cols = (1, 2, 3), (2, 3, 4)  # the window's cells: theta .72 to 1.9, phi 52 to 128 degrees
    faces = []
    for j in range(nv):
        k = (j + 1) % nv
        faces.append([0, 1 + j, 1 + k])
        faces += [[1 + i * nv + j, 1 + (i + 1) * nv + j, 1 + (i + 1) * nv + k, 1 + i * nv + k] for i in range(nu - 1)
                  if not (i in rows and j in cols)]
        faces.append([1 + (nu - 1) * nv + j, len(verts) - 1, 1 + (nu - 1) * nv + k])
    p.add(verts, [_facing(verts, f, verts[f].mean(0) - torso.c) for f in faces], tone(SOOT), 'CN_Metal', True)
    heart = np.array([.22, 0, .85])
    back_x = -.3  # the socket's back wall, behind the whole gimbal
    edge = [(1, 2), (1, 3), (1, 4), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (2, 2)]
    th_e, ph_e = np.array([th_all[i] for i, _ in edge]), np.array([ph_all[j] for _, j in edge])
    lip = torso.point(th_e, ph_e, depth)  # the core's own hole-edge vertices, so no crack opens between them
    neck = torso.point(th_e, ph_e, depth + .1)
    floor = np.column_stack([np.full(len(edge), back_x), heart[1:] + (neck[:, 1:] - heart[1:]) * .86])
    m = len(edge)
    sv = np.concatenate([lip, neck, floor])
    walls = [[r * m + q, r * m + (q + 1) % m, (r + 1) * m + (q + 1) % m, (r + 1) * m + q] for r in (0, 1) for q in range(m)]
    toward_axis = [np.array([sv[f].mean(0)[0], heart[1], heart[2]]) - sv[f].mean(0) for f in walls]
    p.add(sv, [_facing(sv, f, d) for f, d in zip(walls, toward_axis)], tone(SOOT, .6), 'CN_Metal', False)
    wall = np.concatenate([floor, [(back_x - .06, heart[1], heart[2])]])
    p.add(wall, [_facing(wall, [q, (q + 1) % m, m], (1, 0, 0)) for q in range(m)], tone(SOOT, .5), 'CN_Metal', False)
    for i, k in enumerate(np.linspace(.98, 1.64, 3)):
        torso.plate(p, (k - .05, k + .05), _deg(48, 132), _ceramic(rng) if i % 2 else _black(rng),
                    ENAMEL if i % 2 else 'CN_Black', .06, .01, n=(2, 4), back=True, lift=.01)
    start = len(p.v)
    ball(p, heart, .3, GLOW_RED, 'CN_Glow', 14)
    v = np.asarray(p.v[start:]) - heart
    p.c[start:] = glow(GLOW_RED, .55 + .45 * np.clip(v[:, 0] / .3, 0, 1)).tolist()  # hottest where it faces the window
    # The gimbal: an outer ring facing the window, held by four struts from the back wall, a middle ring pivoting in
    # it and an inner ring round the relay. ring() revolves each ring's section, so a ring standing on its edge keeps
    # a true section (toolkit.torus re-picks its frame per point and twists where its path runs vertical).
    s = .028
    for radius, axis in ((.46, (1, 0, 0)), (.41, (0, 1, 0)), (.36, (0, 0, 1))):
        ring(p, [(radius + s, 0), (radius, s), (radius - s, 0), (radius, -s)], tone(STEEL_LIGHT), 'CN_Metal', 18,
             along(axis), heart, hard=False)
    for k in range(4):
        a = k / 4 * TAU + math.pi / 4
        d = np.array([0, math.cos(a), math.sin(a)])
        strut(p, heart + d * .46, np.array([back_x - .03, heart[1], heart[2]]) + d * .58, .05, .05, tone(STEEL), 'CN_Metal',
              up=(1, 0, 0), bevel=.01)
    # Head: a helm with a dim visor slit (the relay stays the brightest red), under a crown of antennae.
    head = Hull((.12, 0, 2.38), (.44, .46, .38), .85, .8)
    head.core(p, tone(SOOT), 'CN_Metal', .045, (8, 12))
    head.plate(p, (.62, 2.7), _deg(30, 150), _ceramic(rng, .06), ENAMEL, .03, .02, n=(3, 3))
    for ph in (_deg(-35, 30), _deg(150, 215)):
        head.plate(p, (.4, 2.7), ph, _black(rng), 'CN_Black', .03, .02, n=(3, 2))
    a = np.linspace(-.85, .85, 7)
    limb(p, np.stack([.12 + .43 * np.cos(a), .45 * np.sin(a), np.full(7, 2.36)], 1), .028, glow(GLOW_RED, .45), 'CN_Glow', 5)
    ring(p, [(.42, 2.0), (.62, 2.0), (.6, 2.12), (.46, 2.16)], tone(STEEL), 'CN_Metal', 16)
    torus(p, (.05, 0, 2.74), .4, .045, tone(STEEL), 'CN_Metal', 16, 4, axis='z')
    for k in range(10):
        a = k / 10 * TAU + .3
        front = math.cos(a) > .6
        tilt = math.radians(rng.uniform(22, 40) + (14 if front else 0))
        length = rng.uniform(.58, .76) * (.65 if front else 1.0)
        base = np.array([.05 + .4 * math.cos(a), .4 * math.sin(a), 2.74])
        d = np.array([math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)])
        limb(p, [base, base + d * length * .5, base + d * length], [.03, .02, .008], tone(SOOT), 'CN_Metal', 5)
        ball(p, base + d * length, .022, glow(GLOW_RED, .45), 'CN_Glow', 4)
    for s in (-1, 1):
        horn = bezier((.0, s * .4, 2.6), (.0, s * .75, 2.75), (-.05, s * 1.0, 3.05), (-.12, s * 1.08, 3.38), 6)
        limb(p, horn, np.linspace(.07, .015, 6), _black(rng), 'CN_Black', 6)
    # Shoulders, arms and the staff.
    for s in (-1, 1):
        pad = Hull((0, s * 1.04, 1.62), (.5, .46, .36), .8, .75)
        pad.core(p, tone(SOOT), 'CN_Metal', .06, (6, 10))
        pad.plate(p, (.35, 2.8), _deg(-10, 190), _ceramic(rng), ENAMEL, .04, .025, sag=1.1)
        wr = np.array([.55, s * 2.22, -.86])
        _arm(p, rng, (0, s * 1.2, 1.3), (.28, s * 1.96, .38), wr, .17, white_upper=False)
        _claw(p, rng, wr, (.25, 0, -1), .55, .4, 3, .08, knuckles=False)
    staff = bezier((.75, 2.12, .05), (.95, 2.3, .55), (.62, 2.42, .95), (.42, 2.2, .7), 7)
    limb(p, np.concatenate([[[.75, 2.12, -3.05]], staff]), np.r_[.05, np.linspace(.05, .03, 7)], _black(rng), 'CN_Black', 6)
    ring(p, [(.05, -1.4), (.085, -1.38), (.085, -1.28), (.05, -1.26)], tone(STEEL_LIGHT), 'CN_Metal', 8, None, (.75, 2.12, 0))
    ball(p, staff[-1], .06, glow(GLOW_RED, .5), 'CN_Glow', 8)
    # Lamellar skirt (rows of white and black plates) trailing segmented tendrils.
    ring(p, [(.42, -.72), (.66, -.72), (.66, -.92), (.42, -.95)], tone(STEEL), 'CN_Metal', 16)
    skirt = Hull((0, 0, -1.42), (.86, .76, .62), .85, .8, upright, taper=(.25, .2))
    skirt.core(p, tone(SOOT), 'CN_Metal', .06, (6, 12))
    for i, th in enumerate(((.25, .9), (.9, 1.55), (1.55, 2.3))):
        for k in range(4):
            a = k * 90 + (45 if i % 2 else 0)
            colour, slot = (_ceramic(rng), ENAMEL) if i % 2 == 0 else (_black(rng), 'CN_Black')
            skirt.plate(p, th, _deg(a, a + 90), colour, slot, .04, .03, lift=.025 * i, sag=1.1)
    for k in range(5):
        a = k / 5 * TAU + math.pi / 5
        prev = np.array([.3 * math.cos(a), .3 * math.sin(a), -2.0])
        sway = rng.uniform(-.3, .3, 2)
        for j in range(4):
            c = prev + np.array([sway[0] * .12, sway[1] * .12, -.3])
            r = .08 - .012 * j
            limb(p, [prev - (c - prev) * .12, c], [r, r * .8], _ceramic(rng) if j % 2 else _black(rng),
                 ENAMEL if j % 2 else 'CN_Black', 5)
            prev = c
        prism(p, prev, prev + np.array([sway[0] * .1, sway[1] * .1, -.3]), .035, tone(EDGE), 'CN_Metal', 5, .7)
    for s in (-1, 1):
        emitter(p, (0, s * .5, -.7), (0, s * .4, -1), .2, sides=10)
    return _finish_al(p, .22)


@al_detail
def al_anchor():
    """An AL holding station over a Reservoir buoy: a squat riveted dome on six clamp legs reaching down for the deck,
    a red lens at +x (the scenario turns it), the lock emitter mast on top and a hover emitter beneath. Its claw tips
    sit 0.43 m below the centre."""
    rng = np.random.default_rng(308)
    p = Part('SM_CE_Anchor', AL_SLOTS)
    upright = basis((0, 0, 1), (1, 0, 0))
    dome = Hull((0, 0, .02), (.3, .42, .42), .75, .9, upright)
    t = .022
    dome.core(p, tone(SOOT), 'CN_Metal', t * 1.5, (10, 18))
    for k in range(8):
        a = k * 45 + 22.5
        white = k % 2 == 0
        box_ = dome.plate(p, (.2, 1.2), _deg(a, a + 45), _ceramic(rng) if white else _black(rng), ENAMEL if white else 'CN_Black',
                          t, .014, n=(3, 3))
        dome.rivet_row(p, (box_[1] - .06,) * 2, (box_[2] + .08, box_[3] - .08), 3, .009, tone(STEEL_LIGHT), 'CN_Metal')
        dome.plate(p, (1.2, 1.75), _deg(a, a + 45), _black(rng), 'CN_Black', t, .014, n=(2, 3))
    lens(p, dome.point(1.0, math.pi / 2, .0), dome.normal(1.0, math.pi / 2), .065, level=2, sides=18)
    ring(p, [(.06, .28), (.1, .28), (.1, .34), (.07, .36), (.06, .36)], tone(STEEL), 'CN_Metal', 14)
    limb(p, [(0, 0, .3), (0, 0, .44)], .03, tone(SOOT), 'CN_Metal', 10)
    for z in (.37, .4):
        ring(p, [(.03, z), (.06, z + .005), (.06, z + .015), (.03, z + .02)], tone(STEEL_LIGHT), 'CN_Metal', 12)
    ball(p, (0, 0, .45), .035, glow(GLOW_RED, .6), 'CN_Glow', 10)
    for k in range(6):
        a = math.radians(30 + 60 * k)
        d = np.array([math.cos(a), math.sin(a), 0])
        root, knee = d * .36 + (0, 0, -.04), d * .55 + (0, 0, .06)
        ankle, tip = d * .6 + (0, 0, -.2), d * .47 + (0, 0, -.37)
        tang = np.cross(UP, d)
        hinge(p, root, tang, .035, .1, tone(STEEL))
        strut(p, root, knee, .06, .05, _ceramic(rng) if k % 2 else _black(rng), ENAMEL if k % 2 else 'CN_Black', bevel=.012)
        hinge(p, knee, tang, .03, .085, tone(STEEL))
        strut(p, knee, ankle, .05, .045, _black(rng), 'CN_Black', bevel=.01)
        joint(p, ankle, .028, sides=8)
        prism(p, ankle, tip, .026, tone(EDGE), 'CN_Metal', 5, .6)
        piston(p, d * .22 + (0, 0, .1), knee + (0, 0, .015), .014, tone(SOOT), EDGE, 'CN_Metal')
    ring(p, [(.08, -.2), (.3, -.2), (.31, -.14), (.26, -.1), (.08, -.1)], tone(STEEL), 'CN_Metal', 20)
    emitter(p, (0, 0, -.205), (0, 0, -1), .26, sides=18)
    return _finish_al(p)


# ---------------------------------------------------------------- vegetation: shared pieces

def pale(colour, toward, t):
    """colour blended toward a paler one by up to t, as far as the result stays in the palette: gold mixed with
    white passes through a cream the rule refuses, so the blend stops short of it."""
    for k in np.linspace(t, 0, 13):
        c = mix(colour, toward, k)
        if allowed(c[:3]):
            return c
    return tone(colour)


def blades(part, base, tip, width, root_col, tip_col, segs=3, rise=.7, twist=None, slot='CN_Leaf'):
    """Single grass-like blades, vectorised: each a strip from base curving over to tip, tapering to a one-triangle
    point. One side is enough because the foliage material is two-sided; the front faces outward, so light and
    the two-sided normal agree. root_col / tip_col: one colour or one per blade (same family: no cross-family
    gradient on a face)."""
    base, tip = np.atleast_2d(np.asarray(base, np.float64)), np.atleast_2d(np.asarray(tip, np.float64))
    n = len(base)
    width = np.broadcast_to(np.asarray(width, np.float64), (n,))
    span = tip - base
    h = np.maximum(span[:, 2], .02)
    ctrl = base + UP * (h * rise)[:, None] + span * np.array([.18, .18, 0])
    s = np.arange(segs) / segs
    S = s[None, :, None]
    P = (1 - S) ** 2 * base[:, None] + 2 * (1 - S) * S * ctrl[:, None] + S ** 2 * tip[:, None]
    out = span * np.array([1.0, 1.0, 0.0])
    out = np.where(np.linalg.norm(out, axis=1, keepdims=True) < 1e-6, np.array([1.0, 0, 0]), out)
    side = unit(np.cross(UP, unit(out)))
    if twist is not None:
        tw = np.asarray(twist, np.float64)[:, None] * s[None, :]
        side = side[:, None, :] * np.cos(tw)[..., None] + UP * np.sin(tw)[..., None] * .5
        side = unit(side)
    else:
        side = np.repeat(side[:, None, :], segs, 1)
    w = width[:, None] * (1 - s[None, :] ** 1.6) / 2
    left, right = P - side * w[..., None], P + side * w[..., None]
    rows = np.stack([left, right], 2).reshape(n, 2 * segs, 3)
    verts = np.concatenate([rows, tip[:, None, :]], 1).reshape(-1, 3)
    m = 2 * segs + 1
    faces = []
    for i in range(n):
        o = i * m
        faces += [[o + 2 * k, o + 2 * k + 1, o + 2 * k + 3, o + 2 * k + 2] for k in range(segs - 1)]
        faces.append([o + 2 * segs - 2, o + 2 * segs - 1, o + 2 * segs])
    rc, tc = (np.broadcast_to(np.asarray(c, np.float64)[..., :4], (n, 4)) for c in (root_col, tip_col))
    t = np.r_[np.repeat(s, 2), 1.0]
    cols = rc[:, None, :] * (1 - t)[None, :, None] + tc[:, None, :] * t[None, :, None]
    return part.add(verts, faces, cols.reshape(-1, 4), slot, True)


def leaves(part, base, direction, facing, length, width, colours, fold=.3, curl=.12, slot='CN_Leaf'):
    """Folded leaves, vectorised: each a diamond creased along its midrib (four vertices, two triangles), the
    cheapest shape that still catches light like a leaf. facing is roughly the upper surface's normal; the tip
    curls back from it a little. colours: one or one per leaf."""
    base = np.atleast_2d(np.asarray(base, np.float64))
    n = len(base)
    d = unit(np.broadcast_to(np.asarray(direction, np.float64), (n, 3)))
    f = np.broadcast_to(np.asarray(facing, np.float64), (n, 3))
    side = np.cross(d, f)
    bad = np.linalg.norm(side, axis=1) < 1e-6
    side[bad] = np.cross(d[bad], np.array([1.0, 0, 0]))
    side = unit(side)
    nrm = np.cross(side, d)
    L = np.broadcast_to(np.asarray(length, np.float64), (n,))[:, None]
    W = np.broadcast_to(np.asarray(width, np.float64), (n,))[:, None]
    tip = base + d * L - nrm * L * curl
    mid = base + d * L * .42
    left = mid - side * W + nrm * W * fold
    right = mid + side * W + nrm * W * fold
    verts = np.stack([base, left, tip, right], 1).reshape(-1, 3)
    o = np.arange(n) * 4
    faces = np.concatenate([np.stack([o, o + 2, o + 1], 1), np.stack([o, o + 3, o + 2], 1)]).tolist()
    cols = np.asarray(colours, np.float64)
    if cols.ndim == 2 and len(cols) == n:
        cols = np.repeat(cols, 4, 0)
    return part.add(verts, faces, cols, slot, True)


# ---------------------------------------------------------------- atlas cards (2026-11-07, the AAA pass)
# Foliage is drawn on cards textured from T_CN_LeafAtlas (Tools/conclave_textures/atlas.py), the way real-time foliage is
# made, instead of single folded leaves; a card is a whole twig, spray, clump or patch of litter. The atlas is 4 x 4
# cells (column, row), v down; this table is atlas.py's. Each card is its cell's cutout octagon from atlas.json (atlas.py
# writes it), so the mostly empty corners of a quad are not drawn, shaded or traced. Card vertices carry vertex-colour
# alpha CARD_ALPHA: M_CNFoliage masks them with the atlas and keeps solid geometry (fruit, flowers, stems, twigs) whole
# at alpha 1. A crown's cards take the whole crown's normals, so a canopy shades as one volume, not a cloud of planes.
ATLAS_GRID = 4
CELL_LEAF, CELL_BLOSSOM, CELL_GRASS, CELL_NEEDLE = (0, 0), (1, 0), (2, 0), (3, 0)
CELL_SWARD, CELL_SEED, CELL_HEDGE, CELL_SMALLLEAF = (0, 1), (1, 1), (2, 1), (3, 1)
CELL_LILY, CELL_REED, CELL_LITTER, CELL_MAPLE_A = (0, 2), (1, 2), (2, 2), (3, 2)
CELL_MAPLE_B, CELL_BLOSSOM2, CELL_ORCHARD, CELL_TWIGS = (0, 3), (1, 3), (2, 3), (3, 3)
CELL_INSET = .002          # of the atlas: a cell's uvs stop short of its edges, so mips never reach a neighbour
CARD_ALPHA = 0.0
QUAD = np.array([(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)])   # a whole cell: bottom left and right, top right and left
# A crown card's normal: the crown ellipsoid's gradient, world up and the card's own facing, in these parts. Each clump
# shading as its own sphere made neighbouring cards differ by 0.3 in N.L; one crown, with up, by under 0.1.
CROWN_NORMAL = (.55, .30, .15)
CANOPY_FOOT = .85          # shading at a canopy card's base (grass keeps cards()' .72): crowns read lit, not sooty
INNER_SHELL = .7           # cards deeper in a crown's shell than this take its inner colour


def cell_uv(cell, inset=CELL_INSET):
    """A cell's uv rectangle (u0, v0, u1, v1), image convention."""
    size = 1.0 / ATLAS_GRID
    u0, v0 = cell[0] * size + inset, cell[1] * size + inset
    return u0, v0, u0 + size - 2 * inset, v0 + size - 2 * inset


def _corners(points):
    """A convex outline without repeated or straight-through corners, so a fan over it has no empty triangle."""
    p = np.clip(np.asarray(points, np.float64), 0.0, 1.0)
    while len(p) > 3:
        before, after = p - np.roll(p, 1, 0), np.roll(p, -1, 0) - p
        turn = np.abs(before[:, 0] * after[:, 1] - before[:, 1] * after[:, 0])
        flat = (turn < 1e-8) | (np.linalg.norm(before, axis=1) < 1e-5)
        if not flat.any():
            break
        p = np.delete(p, int(np.argmax(flat)), 0)
    return p


@functools.lru_cache(maxsize=1)
def hulls():
    """Each atlas cell's cutout octagon, read once from Art/Textures/Conclave/atlas.json (atlas.py; the ATLAS_JSON
    environment variable names another file, for tests): {(column, row): corners in cell-local uv, u right, v down}.
    Empty when the file is missing: cards are then whole quads."""
    path = Path(os.environ.get('ATLAS_JSON') or ROOT / 'Art/Textures/Conclave/atlas.json')
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if data.get('grid') != ATLAS_GRID:
        raise ValueError('%s describes a %s x %s atlas, but the cell table here is %d x %d' %
                         (path, data.get('grid'), data.get('grid'), ATLAS_GRID, ATLAS_GRID))
    out = {}
    for key, points in data.get('cells', {}).items():
        corners = _corners(points)
        if len(corners) >= 3:
            out[tuple(int(k) for k in key.split(','))] = corners
    return out


def cards(part, base, grow, facing, width, height, cell, colours, crown=None, rng=None, foot=.72, slot='CN_Leaf',
          lean=0.0, shape='cutout', normal=None):
    """Atlas cards, vectorised: each its cell's cutout octagon (shape 'cutout', when atlas.json has one; else, or with
    shape 'quad', the whole cell) laid on a card whose bottom edge's middle sits at base and which rises height along
    grow, its face turned toward facing (projected off grow); the cell's bottom edge, where its twig or clump starts, is
    at base. colours: one RGB(A) or one per card; each card darkens to foot (a shading factor) at its bottom edge, so
    clumps are shadowed where they join the plant. lean bends the top edge back along facing (cupped sprays).
    Normals: normal (one per card, or one for all) if given; else crown = (centre, radii), the whole crown's
    (CROWN_NORMAL); else crown = a point the normals radiate from (ground cover: just below its root); else each card's
    own facing."""
    base = np.atleast_2d(np.asarray(base, np.float64))
    n = len(base)
    g = unit(np.broadcast_to(np.asarray(grow, np.float64), (n, 3)).copy())
    f = np.array(np.broadcast_to(np.asarray(facing, np.float64), (n, 3)), np.float64)
    f = f - g * np.sum(f * g, 1, keepdims=True)
    bad = np.linalg.norm(f, axis=1) < 1e-6
    if bad.any():
        f[bad] = np.cross(g[bad], np.array([1.0, 0, 0]))
        still = np.linalg.norm(f, axis=1) < 1e-6
        f[still] = np.cross(g[still], np.array([0, 1.0, 0]))
    f = unit(f)
    a = unit(np.cross(g, f))
    W = np.broadcast_to(np.asarray(width, np.float64), (n,))[:, None]
    H = np.broadcast_to(np.asarray(height, np.float64), (n,))[:, None]
    hull = hulls().get(tuple(cell)) if shape == 'cutout' else None
    if hull is None:
        hull = QUAD
    m = len(hull)
    mirror = (rng.uniform(0, 1, n) < .5) if rng is not None else np.zeros(n, bool)
    # A corner (hu, hv) of the cell lies at bottom left + across * hu + up * (1 - hv); a mirrored card flips hu.
    hu = np.where(mirror[:, None], 1 - hull[None, :, 0], hull[None, :, 0])
    across, up = a * W, g * H - f * H * lean
    verts = ((base - across / 2)[:, None] + across[:, None] * hu[..., None] + up[:, None] * (1 - hull[None, :, 1, None])).reshape(-1, 3)
    u0, v0, u1, v1 = cell_uv(cell)
    uv = np.tile(np.stack([u0 + hull[:, 0] * (u1 - u0), v0 + hull[:, 1] * (v1 - v0)], 1), (n, 1))
    # A fan over each card, counter-clockwise in its (across, up) plane, whose normal is f: so its front faces f. A
    # mirrored card's corners run the other way round.
    s, t = hull[:, 0], 1 - hull[:, 1]
    ccw = np.sum(s * np.roll(t, -1) - np.roll(s, -1) * t) > 0
    order = np.where((mirror != ccw)[:, None], np.arange(m), np.r_[0, np.arange(m - 1, 0, -1)])
    fan = np.array([(0, k, k + 1) for k in range(1, m - 1)])
    faces = (order[:, fan] + (np.arange(n) * m)[:, None, None]).reshape(-1, 3).tolist()
    cols = np.asarray(colours, np.float64)
    if cols.ndim == 1:
        cols = np.tile(cols, (n, 1))
    vcols = np.concatenate([tone(c, foot + (1 - foot) * (1 - hull[:, 1])) for c in cols])
    vcols[:, 3] = CARD_ALPHA
    start = part.add(verts, faces, vcols, slot, True, uv=uv)
    F = np.repeat(f, m, 0)
    if normal is not None:
        nrm = np.repeat(unit(np.broadcast_to(np.asarray(normal, np.float64), (n, 3))), m, 0)
    elif crown is None:
        nrm = F
    elif np.shape(crown) == (2, 3):
        centre, radii = np.asarray(crown, np.float64)
        w_crown, w_up, w_card = CROWN_NORMAL
        nrm = unit(w_crown * unit((verts - centre) / radii ** 2) + w_up * UP + w_card * F)
    else:
        nrm = unit(unit(verts - np.asarray(crown, np.float64)) * .8 + F * .2)
    if not hasattr(part, 'card_normals'):
        part.card_normals = []
    part.card_normals.append((start, nrm))
    return start


def leaf_cards(part, rng, pts, out, crown, count, size, colours, cell=CELL_LEAF, facing_up=.45, droop=.15, depth=None,
               normals=None, foot=CANOPY_FOOT):
    """count twig cards from points on a crown's shell, each rising outward from just inside it (out: the points'
    outward directions), faced up toward the light. colours (base, lit) of one family, lit on top and outside, or (base,
    lit, inner): cards deeper than INNER_SHELL in the shell (depth, from shell_points) take inner. Normals: one per point
    (normals) or the crown's (see cards())."""
    pick = rng.choice(len(pts), min(count, len(pts)), replace=False)
    p, d = np.asarray(pts)[pick], np.asarray(out)[pick]
    m = len(pick)
    grow = unit(d + rng.normal(0, .3, (m, 3)) + np.array([0, 0, -droop]))
    face = unit(d * (1 - facing_up) + UP * facing_up + rng.normal(0, .3, (m, 3)))
    h = rng.uniform(*size, m)
    light = np.clip(.5 + .5 * d[:, 2], 0, 1)
    tint = mix(colours[0], colours[1], rng.uniform(0, 1, m))
    if len(colours) > 2 and depth is not None:
        tint[np.asarray(depth)[pick] < INNER_SHELL] = _rgba(np.asarray(colours[2], np.float64)[:3])
    cols = np.array([tone(c, kk) for c, kk in zip(tint, .88 + .12 * light)])
    return cards(part, p - grow * h[:, None] * .35, grow, face, h * .95, h, cell, cols, crown, rng, foot,
                 normal=None if normals is None else np.asarray(normals)[pick])


def card_normals(part):
    """part.normals for a plant with cards: smooth (area-weighted) vertex normals for its solid geometry, canopy
    normals for its cards, so the FBX carries both (build_physis_conclave.py custom_normals)."""
    if not getattr(part, 'card_normals', None):
        return part
    v = np.asarray(part.v, np.float64)
    tris = [(f[0], f[k], f[k + 1]) for f in part.f for k in range(1, len(f) - 1)]
    t = np.asarray(tris, np.int64)
    fn = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    acc = np.zeros_like(v)
    for j in range(3):
        np.add.at(acc, t[:, j], fn)
    nrm = unit(acc)
    for start, n in part.card_normals:
        nrm[start:start + len(n)] = n
    part.normals = nrm.tolist()
    return part


def shell_points(rng, centre, radii, count, inner=.55, top_bias=.35):
    """Points scattered through the outer shell of an ellipsoid (leaf positions in a crown), a little denser on top
    where the light is; returns points, their outward unit directions and their depth in the shell (1 at its
    surface)."""
    d = rng.normal(0, 1, (count, 3))
    d[:, 2] = d[:, 2] * (1 - top_bias) + np.abs(d[:, 2]) * top_bias
    d = unit(d)
    depth = inner + (1 - inner) * rng.uniform(0, 1, count) ** .5
    return np.asarray(centre, np.float64) + d * np.asarray(radii, np.float64) * depth[:, None], d, depth


def crown_of(points, radius):
    """A tree's crown as one ellipsoid (centre, radii) for its cards' normals: centred on its outer branch tips, half
    their spread on each axis plus a clump's radius."""
    e = np.asarray(points, np.float64)
    return np.stack([e.mean(0), (e.max(0) - e.min(0)) / 2 + radius])


def bark(part, start, pts, radii, colour, sides, rng, ground=1.4, bands=0.0, under=.35, seed=0):
    """Recolours the limb added at start as bark: shaded under each branch and toward the ground, mottled by
    noise, with dark lenticel dashes when bands > 0 (birch-like white bark)."""
    pts = np.asarray(pts, np.float64)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (len(pts),))
    v = np.asarray(part.v[start:], np.float64)
    n = len(pts)
    sides = sides_of(sides)     # as limb() built it
    ring_of = np.r_[np.repeat(np.arange(n), sides), np.zeros(sides, int), np.full(sides, n - 1)][:len(v)]
    off = v - pts[ring_of]
    r = np.maximum(radii[ring_of], 1e-4)
    k = 1 - under * np.clip(-off[:, 2] / r, 0, 1)
    k *= .55 + .45 * np.clip(v[:, 2] / ground, 0, 1)
    ang = np.arctan2(off[:, 1], off[:, 0])
    k *= .9 + .12 * noise2(ang * 2.2 + seed, v[:, 2] * 3.0, seed + 7)
    if bands:
        dash = noise2(ang * 5.0 + seed, v[:, 2] * 26.0, seed + 11)
        k *= np.where(dash > 1 - bands, .38, 1.0)
    part.c[start:] = tone(colour, k).tolist()


def branch_limb(part, pts, radii, colour, slot, sides, rng, **kw):
    start = limb(part, pts, radii, colour, slot, sides, cap=True)
    bark(part, start, pts, radii, colour, sides, rng, **kw)
    return start


def _finish_plant(part, centre_xy=True, ground=True):
    """Stands the plant on z 0 (its lowest point; ground=False keeps its height, for what lies or floats a little
    above its pivot or hangs from a wall) with its footprint centred on the origin."""
    v = np.asarray(part.v, np.float64)
    lo, hi = v.min(0), v.max(0)
    shift = np.array([-(lo[0] + hi[0]) / 2 if centre_xy else 0.0, -(lo[1] + hi[1]) / 2 if centre_xy else 0.0,
                      -lo[2] if ground else 0.0])
    part.v = (v + shift).tolist()
    return card_normals(part)


# ---------------------------------------------------------------- ground cover: grass, wheat, flowers

SWARD_TILT = (25.0, 45.0)     # degrees from upright: the sward's strips lean out of the patch, as turf grows


def grass_gold():
    """A 1.8 m patch of green grass (golden until the author's 2026-11-08 change; the mesh keeps its contract name): seven clumps of tall blades crossed in stars, each its own height (0.3-0.75 m), a
    low sward over the whole patch between them (strips of short blades, each leaning out), and a few seed heads. About
    300 triangles of cutout cards, as the meadows instance it by the hundred thousand. Normals radiate from just below
    each clump and strip, so the patch shades like the lawn it stands in; the atlas shadows the roots and bleaches the
    tips."""
    rng = np.random.default_rng(401)
    p = Part('SM_CV_GrassGold', ('CN_Leaf',))

    def gold(count):
        return np.array([tone(mix(GREEN_GRASS, GREEN_MOSS, q), 1.0) for q in rng.uniform(.1, .6, count)])
    centres = [(0.0, 0.0)] + [(math.cos(a) * r, math.sin(a) * r) for a, r in
                              zip(np.arange(6) * TAU / 6 + rng.uniform(-.3, .3, 6), rng.uniform(.38, .58, 6))]
    for cx, cy in centres:
        count = 4
        az = rng.uniform(0, math.pi) + np.arange(count) * math.pi / count
        face = np.stack([np.cos(az), np.sin(az), np.zeros(count)], 1)
        lean = np.stack([-np.sin(az), np.cos(az), np.zeros(count)], 1) * rng.uniform(-.15, .15, (count, 1))
        h = rng.uniform(.3, .75) * rng.uniform(.82, 1.0, count)
        base = np.array([[cx, cy, 0.0]] * count) + rng.normal(0, .03, (count, 3)) * (1, 1, 0)
        cards(p, base, unit(UP + lean), face, h * 1.05, h, CELL_GRASS, gold(count), (cx, cy, -.6), rng)
    # The sward: each card a strip of short blades whose roots fill its width, bases anywhere in the patch.
    for _ in range(int(rng.integers(12, 17))):
        r, a = .6 * math.sqrt(rng.uniform()), rng.uniform(0, TAU)
        out = np.array([math.cos(a), math.sin(a), 0.0])
        tilt = math.radians(rng.uniform(*SWARD_TILT))
        base = out * r
        cards(p, base, UP * math.cos(tilt) + out * math.sin(tilt), out, rng.uniform(.6, .8), rng.uniform(.18, .3),
              CELL_SWARD, gold(1), base - (0, 0, .6), rng)
    for _ in range(int(rng.integers(2, 4))):
        cx, cy = centres[int(rng.integers(0, len(centres)))]
        a = rng.uniform(0, math.pi)
        h = rng.uniform(.55, .72)
        cards(p, (cx, cy, 0.0), unit(UP + rng.normal(0, .08, 3) * (1, 1, 0)), (math.cos(a), math.sin(a), 0.0), h * .5, h,
              CELL_SEED, gold(1), (cx, cy, -.6), rng)
    return _finish_plant(p)


def wheat():
    """A clump of ripe wheat, 1.1 m: stalks each with a leaf, nodding ears of four rows of spikelets with
    awns. Straw gold; the ears paler and brighter where the sun bleaches them."""
    rng = np.random.default_rng(402)
    p = Part('SM_CV_Wheat', ('CN_Leaf',))
    for k in range(11):
        a = rng.uniform(0, TAU)
        r = .07 * math.sqrt(rng.uniform(0, 1))
        base = np.array([math.cos(a) * r, math.sin(a) * r, 0])
        h = rng.uniform(.86, 1.0)
        lean = np.array([math.cos(a), math.sin(a), 0]) * rng.uniform(.03, .09)
        nod = unit(np.append(rng.normal(0, 1, 2), 0)) * .05
        stalk = bezier(base, base + (0, 0, h * .5), base + lean + (0, 0, h * .85), base + lean * 1.6 + nod + (0, 0, h), 4)
        cols = tone(GOLD_STRAW, np.linspace(.72, 1.0, 4))
        limb(p, stalk, np.linspace(.0045, .003, 4), cols, 'CN_Leaf', 3, cap=False)
        node = stalk[1] * .7 + stalk[2] * .3
        out = unit(np.array([math.cos(a + 1), math.sin(a + 1), 0]))
        L = rng.uniform(.2, .28)
        # Twisted along its length like a real flag leaf, so it is never seen only edge-on as a line.
        blades(p, node, node + out * L * .8 + UP * L * .25, .013, tone(GOLD_GRASS, .7), pale(GOLD_STRAW, IVORY, .2), 3, .5,
               [rng.uniform(.8, 1.4) * rng.choice((-1, 1))])
        top = stalk[-1]
        axis = unit(stalk[-1] - stalk[-2] + nod * 2)
        side = unit(np.cross(axis, UP + 1e-3))
        other = np.cross(axis, side)
        ear = tone(GOLD_STRAW, rng.uniform(1.05, 1.2))
        for i in range(6):
            q = top + axis * (.014 * i + .004)
            for s, dvec in ((1, side), (-1, -side)):
                spread = dvec if i % 2 == 0 else (other if s > 0 else -other)
                leaves(p, q, unit(axis * 1.0 + spread * .45), spread, .02, .0075, ear, .35, .0)
            if i % 2 == 0:
                blades(p, q + axis * .01, q + axis * .07 + side * .01 * (1 if i % 4 else -1), .002, ear,
                       pale(GOLD_STRAW, IVORY, .4), 2, .1)
    return _finish_plant(p)


def _stem_clump(p, rng, count, height, foliage):
    """Flower stems and a basal rosette of narrow leaves; returns each stem's top point and direction."""
    for k in range(8):
        a = k / 8 * TAU + rng.uniform(-.3, .3)
        out = np.array([math.cos(a), math.sin(a), 0])
        L = rng.uniform(.14, .22)
        blades(p, out * .01, out * L + UP * L * .35, rng.uniform(.018, .028), tone(foliage, .6), tone(foliage, 1.05), 3, .45)
    tops = []
    for k in range(count):
        a = rng.uniform(0, TAU)
        r = .07 * math.sqrt(rng.uniform(0, 1))
        base = np.array([math.cos(a) * r, math.sin(a) * r, 0])
        h = height * rng.uniform(.7, 1.0)
        lean = np.array([math.cos(a), math.sin(a), 0]) * rng.uniform(.04, .14)
        stem = bezier(base, base + (0, 0, h * .4), base + lean + (0, 0, h * .8), base + lean * 1.4 + (0, 0, h), 4)
        limb(p, stem, np.linspace(.0045, .003, 4), tone(foliage, np.linspace(.62, .95, 4)), 'CN_Leaf', 3, cap=False)
        node = stem[1] * .6 + stem[2] * .4
        side = unit(np.cross(UP, lean + 1e-4))
        blades(p, node, node + side * .07 + UP * .05, .014, tone(foliage, .75), tone(foliage), 2, .4)
        tops.append((stem[-1], unit(stem[-1] - stem[-2])))
    return tops


def _cup(p, centre, axis, petals, length, width, colour, cup=.45, rim=None, sides=4, twist=0.0):
    """A ring of petals round centre opening along axis: each petal a small fan with a rounded edge, cupped up by
    cup (0 flat, 1 upright). Built in the petal family's colour only."""
    rot = along(axis)
    verts, faces, cols = [], [], []
    for i in range(petals):
        a = i / petals * TAU + twist
        o = len(verts)
        half = math.pi / petals * width
        verts.append((rot @ np.array([math.cos(a) * length * .06, math.sin(a) * length * .06, 0])).tolist())
        cols.append(colour)
        for j in range(sides + 1):
            b = a - half + 2 * half * j / sides
            rr = length * (.82 + .18 * math.sin(math.pi * j / sides))
            loc = np.array([math.cos(b) * rr * math.cos(cup), math.sin(b) * rr * math.cos(cup), rr * math.sin(cup)])
            verts.append((rot @ loc).tolist())
            cols.append(colour if rim is None else rim)
        faces += [[o, o + 1 + j, o + 2 + j] for j in range(sides)]
    verts = np.asarray(verts) + np.asarray(centre, np.float64)
    return p.add(verts, faces, np.asarray(cols, np.float64), 'CN_Leaf', True)


def flowers_white():
    """A clump of oxeye daisies: white rays round a gold disc, on gold-dry stems over a rosette of narrow leaves."""
    rng = np.random.default_rng(403)
    p = Part('SM_CV_FlowersWhite', ('CN_Leaf',))
    for top, d in _stem_clump(p, rng, 8, .55, GREEN_LEAF):
        face = unit(d * .4 + UP + np.append(rng.normal(0, .25, 2), 0))
        _cup(p, top, face, 11, rng.uniform(.034, .042), .55, tone(WHITE_PURE, rng.uniform(.92, 1.0)), .12, None, 1,
             rng.uniform(0, 1))
        ball(p, top + face * .004, .013, tone(GOLD_DEEP, rng.uniform(.9, 1.05)), 'CN_Leaf', 5, (1, 1, .55))
    return _finish_plant(p)


def flowers_red():
    """A clump of field poppies: four broad red petals cupped round a black seed head, some buds still nodding."""
    rng = np.random.default_rng(404)
    p = Part('SM_CV_FlowersRed', ('CN_Leaf',))
    tops = _stem_clump(p, rng, 7, .6, GREEN_LEAF)
    for i, (top, d) in enumerate(tops):
        if i >= 5:
            bud = top + unit(d + np.array([.6, 0, -1.2])) * .02
            ball(p, bud, .014, tone(RED_DEEP, 1.2), 'CN_Leaf', 5, (1, 1, 1.4))
            continue
        face = unit(d * .3 + UP + np.append(rng.normal(0, .3, 2), 0))
        _cup(p, top, face, 4, rng.uniform(.035, .045), .95, tone(RED_BRIGHT, rng.uniform(.85, 1.0)), .5,
             tone(RED, rng.uniform(.9, 1.1)), 3, rng.uniform(0, 1))
        ball(p, top + face * .008, .008, tone(BLACK), 'CN_Leaf', 5, (1, 1, 1.2))
    return _finish_plant(p)


def flowers_blue():
    """A clump of flax: five light-blue petals in a shallow cup on wiry gold stems, a white eye at each centre."""
    rng = np.random.default_rng(405)
    p = Part('SM_CV_FlowersBlue', ('CN_Leaf',))
    for top, d in _stem_clump(p, rng, 7, .5, GREEN_LEAF):
        face = unit(d * .3 + UP + np.append(rng.normal(0, .3, 2), 0))
        _cup(p, top, face, 5, rng.uniform(.027, .033), .9, tone(BLUE, rng.uniform(.95, 1.04)), .3,
             tone(mix(BLUE, BLUE_PALE, .5)), 3, rng.uniform(0, 1))
        disc(p, top + face * .003, face, .006, tone(WHITE_PURE), 'CN_Leaf', 5)
    return _finish_plant(p)


# ---------------------------------------------------------------- shrubs and trees

def grow(rng, start, direction, length, radius, cfg, depth=0, out=None):
    """Grows a branch and, recursively, its children along it: a bezier that bends toward the light (cfg 'up'),
    tapering, with children set round it at golden-angle spacing. Returns {'wood': [(points, radii, depth)],
    'tips': [(point, direction, depth)]}."""
    if out is None:
        out = {'wood': [], 'tips': [], 'phase': rng.uniform(0, TAU)}
    d = unit(direction)
    n = cfg['segs'][depth]
    bend = unit(d + UP * cfg['up'][depth] + rng.normal(0, cfg['wiggle'], 3))
    end = np.asarray(start, np.float64) + bend * length
    pts = bezier(start, start + d * length * .38, end - bend * length * .33 + rng.normal(0, cfg['wiggle'] * length * .2, 3), end, n)
    r = radius * np.linspace(1, cfg['taper'][depth], n)
    out['wood'].append((pts, r, depth))
    if depth + 1 < len(cfg['segs']):
        k = cfg['children'][depth]
        t0 = cfg['t0'][depth]
        for i in range(k):
            t = t0 + (1 - t0) * (i + rng.uniform(.15, .85)) / k
            f = t * (n - 1)
            i0 = min(int(f), n - 2)
            w = f - i0
            p0 = pts[i0] * (1 - w) + pts[i0 + 1] * w
            tang = unit(pts[i0 + 1] - pts[i0])
            a, b = frame(tang)
            az = out['phase'] + i * 2.39996 + rng.uniform(-.35, .35)
            ang = rng.uniform(*cfg['spread'][depth])
            cd = math.cos(ang) * tang + math.sin(ang) * (math.cos(az) * a + math.sin(az) * b)
            rr = (r[i0] * (1 - w) + r[i0 + 1] * w) * cfg['child_r'][depth]
            grow(rng, p0, cd, length * rng.uniform(*cfg['ratio'][depth]), rr, cfg, depth + 1, out)
        out['phase'] += 1.3
    out['tips'].append((end, bend, depth))
    return out


def wood(part, rng, tree, colour, slot, sides, **kw):
    """Builds every branch of a grown tree as bark-coloured limbs, thinner wood with fewer sides."""
    for pts, r, depth in tree['wood']:
        branch_limb(part, pts, r, colour, slot, sides[min(depth, len(sides) - 1)], rng, seed=int(rng.integers(1000)), **kw)


def cluster(part, rng, centre, radius, count, colours, crown, size=(.07, .12), droop=.25, squash=.75):
    """A clump of foliage at a twig's end: twig cards over the outer shell of a squashed ball, lit on top and outside
    and darker inside (vertex colour), every card taking the whole crown's normals (crown: centre and radii). colours:
    (base, lit) of one family, or (base, lit, inner) for the cards deepest in the clump. Returns the shell points, under
    which fruit hangs."""
    c = np.asarray(centre, np.float64)
    radii = np.array([radius, radius, radius * squash])
    pts, out, depth = shell_points(rng, c, radii, count, .62)
    # One twig card stands for about five of the old single leaves; it is about four leaf lengths tall.
    n = max(5, count // 5)
    leaf_cards(part, rng, pts, out, crown, n, (size[0] * 3.6 * (1 + radius) / 2, size[1] * 3.6 * (1 + radius) / 2), colours,
               droop=droop, depth=depth)
    return pts


def rosettes(part, centres, normals, r, colours, cup=.35):
    """Blossoms: each a cupped five-petal fan (five triangles) facing along its normal."""
    C = np.atleast_2d(np.asarray(centres, np.float64))
    N = unit(np.atleast_2d(np.asarray(normals, np.float64)))
    R = np.broadcast_to(np.asarray(r, np.float64), (len(C),))
    verts, faces = [], []
    ang = np.linspace(0, TAU, 5, endpoint=False)
    for i, (c, n, rr) in enumerate(zip(C, N, R)):
        a, b = frame(n)
        rim = c + rr * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b) + n * rr * cup
        verts.append(c - n * rr * .1)
        verts.extend(rim)
        o = i * 6
        faces += [[o, o + 1 + j, o + 1 + (j + 1) % 5] for j in range(5)]
    cols = np.asarray(colours, np.float64)
    if cols.ndim == 2 and len(cols) == len(C):
        cols = np.repeat(cols, 6, 0)
    return part.add(np.asarray(verts), faces, cols, 'CN_Leaf', True)


def roots(part, rng, radius, count, colour, slot, reach=1.0, sides=5, **kw):
    """Root flare: buttresses running out from the trunk foot into the ground."""
    for k in range(count):
        a = k / count * TAU + rng.uniform(-.3, .3)
        d = np.array([math.cos(a), math.sin(a), 0])
        L = reach * rng.uniform(.7, 1.1)
        pts = bezier(d * radius * .2 + (0, 0, radius * 1.3), d * radius * .9 + (0, 0, radius * .7), d * L * .6 + (0, 0, radius * .25),
                     d * L + (0, 0, radius * .08), 5)
        branch_limb(part, pts, np.linspace(radius * .55, radius * .08, 5), colour, slot, sides, rng, **kw)


# Each tree's fit to its README height (_scale_to): its lowest point, its scale and its crown's shear back over the trunk,
# as measured from the whole tree, leaves included, when its wood was built and approved for collision (2026-11-07).
# The crowns have been rebuilt from other cards since; measuring the fit from them would move every trunk and limb by
# centimetres to a metre, and the wood collides.
TREE_FIT = {
    'SM_CV_TreeRed': (-0.02127316497265696, 0.9603357159774543, (-1.30903401657952, -0.1909839710471446)),
    'SM_CV_TreeWhite': (-0.026814701641125767, 1.2104732708774457, (0.8319895741949108, 1.0302607054397164)),
    'SM_CV_FruitTree': (-0.011881644654805335, 1.0502053536684077, (-0.06741330745026941, 0.38589186728403624)),
    'SM_CV_TreeBlack': (-0.013535108662266603, 0.9791546091350136, None),
}


def _scale_to(part, height, balance=True, fit=None):
    """Scales a grown plant to its contract height; with balance, shears the crown back over the trunk (the origin) so
    a crown that happened to grow lopsided does not hang a metre off its footprint. fit (lowest z, scale, shear) is
    taken instead of the plant's own bounds (TREE_FIT)."""
    v = np.asarray(part.v, np.float64)
    lo, scale, shear = fit if fit is not None else (v[:, 2].min(), None, None)
    v[:, 2] -= lo
    v *= height / v[:, 2].max() if scale is None else scale
    if balance:
        if shear is None:
            crown = v[v[:, 2] > height * .45]
            shear = (crown[:, :2].min(0) + crown[:, :2].max(0)) / 2
        v[:, :2] -= np.asarray(shear, np.float64)[None, :] * np.clip(v[:, 2:3] / (height * .7), 0, 1) ** 1.5
    part.v = v.tolist()


def card_tris(cell):
    """The triangles one card of the cell costs: its cutout's corners less two."""
    return len(hulls().get(tuple(cell), QUAD)) - 2


MOUND_UP = .3          # a shrub's or hedge's card normals: its mound's gradient plus this much of world up


def shrub():
    """A silver-leaved shrub, 1.2 m, like an elaeagnus or a laurel: a dense, lumpy mound of small-leaved white twigs on
    dark woody stems that branch low from one crown and show only at its foot. Leaves darken toward the inside and the
    underside, and every card takes the mound's normal (its gradient, turned up toward the light), so the bush shades as
    one mound rather than as a cloud of cards."""
    rng = np.random.default_rng(501)
    p = Part('SM_CV_Shrub', ('CN_Bark', 'CN_Leaf'))
    centre, radii = np.array([0.0, 0, .66]), np.array([.66, .6, .54])
    cfg = dict(segs=[4, 3], up=[.2, .15], wiggle=.15, taper=[.45, .35], children=[2, 0], t0=[.3, 1], spread=[(.5, .9)],
               ratio=[(.45, .62)], child_r=[.75])
    for k in range(5):
        a = k / 5 * TAU + rng.uniform(-.3, .3)
        lean = rng.uniform(.6, .95)
        t = grow(rng, np.array([math.cos(a) * .02, math.sin(a) * .02, 0]), (math.cos(a) * lean, math.sin(a) * lean, 1),
                 rng.uniform(.5, .62), .02, cfg)
        wood(p, rng, t, CHARCOAL, 'CN_Bark', [3, 3], ground=.45, under=.2)
    pts, out, depth = shell_points(rng, centre, radii, 520, .7, .25)
    # Broad bulges, so the mound's outline is lumpy like a real bush rather than an ellipsoid.
    bulge = 1 + .13 * noise2(out[:, 0] * 1.6 + out[:, 2] * .7, out[:, 1] * 1.6 - out[:, 2] * .7, 5)
    pts = centre + (pts - centre) * bulge[:, None]
    normals = unit(unit((pts - centre) / radii ** 2) + MOUND_UP * UP)
    leaf_cards(p, rng, pts, out, None, 260, (.25, .35), (WHITE_COOL, WHITE_PURE), CELL_SMALLLEAF, droop=.2, normals=normals)
    _scale_to(p, 1.2, balance=False)
    return _finish_plant(p)


HEDGE_CORE = ((0.0, 0.0, .62), (.38, .88, .45))   # the woody core: centre and half extents (its collision)
HEDGE_CLIP = ((0.0, 0.0, .65), (.5, 1.0, .55), .28)  # the clipped surface the leaves stand out of: centre, half extents, roundness
HEDGE_CARDS, HEDGE_SPRIGS = 600, 50
HEDGE_TRIS = 2950      # what the hedge may fill up to (check.py's budget is 3000): fewer cards when a cutout has more corners


def _superellipsoid(centre, half, e, nu=8, nv=16):
    """A closed rounded box (superellipsoid of roundness e: 1 an ellipsoid, toward 0 a box): vertices and faces wound
    outward, poles single vertices."""
    th = np.linspace(0, math.pi, nu + 1)[1:-1]
    ph = np.linspace(0, TAU, nv, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing='ij')
    hx, hy, hz = half
    ring = np.stack([_spow(np.sin(T), e) * _spow(np.cos(P), e) * hx, _spow(np.sin(T), e) * _spow(np.sin(P), e) * hy,
                     _spow(np.cos(T), e) * hz], -1).reshape(-1, 3)
    c = np.asarray(centre, np.float64)
    verts = np.concatenate([[c + (0, 0, hz)], ring + c, [c - (0, 0, hz)]])
    faces = []
    for j in range(nv):
        k = (j + 1) % nv
        faces.append([0, 1 + j, 1 + k])
        faces += [[1 + i * nv + j, 1 + (i + 1) * nv + j, 1 + (i + 1) * nv + k, 1 + i * nv + k] for i in range(nu - 2)]
        faces.append([1 + (nu - 2) * nv + j, len(verts) - 1, 1 + (nu - 2) * nv + k])
    return verts, [_facing(verts, f, verts[f].mean(0) - c) for f in faces]


def hedge():
    """A trimmed hedge, 1 x 2 x 1.2 m, of small red leaves: a clipped mat of leafy cards standing a little out of a
    rounded box, sprigs proud of the clipping here and there, a red skin behind them seen only through the gaps, and a
    dark woody core inside that gives it collision; its bare stems show at the foot as on real hedges."""
    rng = np.random.default_rng(502)
    p = Part('SM_CV_Hedge', ('CN_Black', 'CN_Bark', 'CN_Leaf'))
    core_c, core_h = (np.asarray(v, np.float64) for v in HEDGE_CORE)
    obox(p, core_c, core_h, tone(CHARCOAL), 'CN_Black', .05)
    for k in range(5):
        y = -.72 + k * .36 + rng.uniform(-.05, .05)
        x = rng.uniform(-.2, .2)
        pts = [(x, y, 0), (x * 1.2, y, .12), (x * 1.3 + rng.uniform(-.05, .05), y, .3)]
        branch_limb(p, pts, [.03, .026, .022], CHARCOAL, 'CN_Bark', 5, rng, ground=.3, under=.1)
    # The backstop: a near-box skin 5 cm round the core, so the core's corners never show through it, and red, so the
    # gaps between the cards read as deep foliage (RED_DEEP rendered maroon).
    verts, faces = _superellipsoid(core_c, core_h + .05, .12)
    mottle = .85 + .15 * noise2(verts[:, 0] * 7 + verts[:, 1] * 4, verts[:, 2] * 7, 23)
    p.add(verts, faces, tone(RED, mottle), 'CN_Leaf', True)
    # Points spread evenly by area over the clipped surface: sample the box's faces (the top weighted up, it is clipped
    # densest), then pull each point onto the rounded surface along its ray from the centre.
    clip_c, half, e = np.asarray(HEDGE_CLIP[0], np.float64), np.asarray(HEDGE_CLIP[1], np.float64), HEDGE_CLIP[2]

    def surface(n):
        faces_ax = [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1)]
        area = np.array([half[1] * half[2], half[1] * half[2], half[0] * half[2], half[0] * half[2], half[0] * half[1] * 1.6])
        pick = rng.choice(len(faces_ax), n, p=area / area.sum())
        q = rng.uniform(-1, 1, (n, 3)) * half
        for i, (ax, sgn) in enumerate(faces_ax):
            q[pick == i, ax] = sgn * half[ax]
        q[:, 2] = np.maximum(q[:, 2], -half[2] + .08)
        q = q * np.sum(np.abs(q / half) ** (2 / e), 1)[:, None] ** (-e / 2)
        nrm = unit(np.sign(q) * np.abs(q / half) ** (2 / e - 1) / half)
        tang = unit(rng.normal(0, 1, (n, 3)) + UP * .6)   # shoots on a clipped hedge still grow upward
        tang = unit(tang - nrm * np.sum(tang * nrm, 1, keepdims=True))
        return q + clip_c, nrm, tang

    def colours(pos, n):
        k = .85 + .15 * np.clip((pos[:, 2] - .1) / 1.1, 0, 1)    # a little darker toward the ground
        return np.array([tone(c, kk) for c, kk in zip(mix(RED, RED_BRIGHT, rng.uniform(0, 1, n)), k)])
    # The mat: cards standing 25-50 degrees out of the clipping, as many as the budget holds.
    room = HEDGE_TRIS - p.triangles() - HEDGE_SPRIGS * card_tris(CELL_SMALLLEAF)
    n = min(HEDGE_CARDS, room // card_tris(CELL_HEDGE))
    pos, nrm, tang = surface(n)
    tilt = np.radians(rng.uniform(25, 50, n))[:, None]
    grow_ = unit(tang * np.cos(tilt) + nrm * np.sin(tilt))
    h = rng.uniform(.22, .32, n)
    cards(p, pos - nrm * .04, grow_, nrm, h, h, CELL_HEDGE, colours(pos, n), rng=rng, foot=.8,
          normal=unit(nrm + MOUND_UP * UP))
    # Sprigs: shoots the shears missed, standing 5-15 cm proud of the clipping on the top and sides.
    pos, nrm, tang = surface(HEDGE_SPRIGS)
    grow_ = unit(nrm * .85 + tang * .3 + UP * .2)
    sink = .08
    h = (rng.uniform(.05, .15, HEDGE_SPRIGS) + sink) / np.sum(grow_ * nrm, 1)
    cards(p, pos - nrm * sink, grow_, unit(np.cross(grow_, tang)), h * .7, h, CELL_SMALLLEAF, colours(pos, HEDGE_SPRIGS),
          rng=rng, foot=.8, normal=unit(nrm + MOUND_UP * UP))
    return _finish_plant(p)


# The broadleaf trees' crowns (E8 of the 2026-11-07 review). True: real leaf scale on fine twigs, every card's base on the
# wood. False: clumps of cards on crown shells (cluster()). The editor's frame-time gate decides which stays: the twigs
# stay only if they cost the base pass under 1.5 ms. Either way the wood, which collides, is the same.
BRANCHLET_CANOPIES = True
TREE_TRIS = 11800          # what a tree may fill up to (check.py's budget is 12000): fewer cards when a cutout has more corners
TWIGS_ALONG = 6            # twigs along the outer 40 % of each finest branch (and one at its tip)
TWIGS_AT_TIP = 3           # twigs at each tip one level in
TWIG_LENGTH, TWIG_RADIUS = (.3, .6), (.008, .015)     # metres, final size


def crown_from(tips, clumps):
    """A tree's whole crown (crown_of) from the tips its clumps grow at; clumps: radius range by tip depth."""
    return crown_of([e for e, _, _ in tips], np.mean([sum(clumps[depth]) / 2 for _, _, depth in tips]))


def _along(points, t):
    """The point and unit direction at arc fraction t along a polyline."""
    pts = np.asarray(points, np.float64)
    arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    s = t * arc[-1]
    i = int(np.clip(np.searchsorted(arc, s, side='right') - 1, 0, len(pts) - 2))
    w = (s - arc[i]) / max(arc[i + 1] - arc[i], 1e-9)
    return pts[i] * (1 - w) + pts[i + 1] * w, unit(pts[i + 1] - pts[i])


def twig_crown(part, rng, wood_, tips, last, crown, scale, twig_colour, cells, count, size, colours):
    """A broadleaf crown at real leaf scale: fine twigs (solid CN_Leaf strands, which sway with the leaves and never
    collide) along the outer 40 % of the finest branches (depth last), at their tips and at the tips one level in, each
    carrying cards whose bases sit on it and which grow on along it, outward and a little up. wood_ and tips: the grown
    tree's (grow()); crown: (centre, radii) for the cards' normals; scale: the tree's fit scale, so twigs and cards take
    their sizes in final metres; cells: the atlas cells the cards take at random; colours: (base, lit, inner) as
    leaf_cards takes them; count: the cards wanted, fewer if the tree would pass TREE_TRIS. Returns the twigs' tips, for
    fruit to hang under."""
    centre, radii = crown
    anchors = []
    for pts, _, depth in wood_:
        if depth == last:
            anchors += [_along(pts, t) for t in np.r_[rng.uniform(.6, 1.0, TWIGS_ALONG), 1.0]]
    for e, d, depth in tips:
        if depth == last - 1:
            anchors += [(e, unit(d))] * TWIGS_AT_TIP
    twigs = []
    for q, d in anchors:
        a, b = frame(d)
        spin, ang = rng.uniform(0, TAU), math.radians(rng.uniform(30, 60))
        way = unit(d * math.cos(ang) + (a * math.cos(spin) + b * math.sin(spin)) * math.sin(ang) + UP * .15)
        length = rng.uniform(*TWIG_LENGTH) / scale
        line = np.array([q, q + way * length * .5 - UP * length * .04, q + way * length])
        r = rng.uniform(*TWIG_RADIUS) / scale
        limb(part, line, [r, r * .7, r * .4], twig_colour, 'CN_Leaf', 3, cap=False)
        twigs.append(line)
    count = min(count, (TREE_TRIS - part.triangles()) // max(card_tris(c) for c in cells))
    on = np.arange(count) % len(twigs)
    base = np.array([_along(twigs[k], t)[0] for k, t in zip(on, rng.uniform(.3, 1.0, count))])
    along = np.array([unit(twigs[k][-1] - twigs[k][0]) for k in on])
    outward = unit(base - centre)
    grow_ = unit(.6 * along + .3 * outward + .1 * UP + rng.normal(0, .15, (count, 3)))
    face = unit(outward * .55 + UP * .45 + rng.normal(0, .3, (count, 3)))
    h = rng.uniform(*size, count) / scale
    tint = mix(colours[0], colours[1], rng.uniform(0, 1, count))
    if len(colours) > 2:
        tint[np.linalg.norm((base - centre) / radii, axis=1) < INNER_SHELL] = _rgba(np.asarray(colours[2], np.float64)[:3])
    cols = np.array([tone(c, k) for c, k in zip(tint, .88 + .12 * np.clip(.5 + .5 * outward[:, 2], 0, 1))])
    cell_of = rng.integers(0, len(cells), count)
    for i, cell in enumerate(cells):
        mine = cell_of == i
        if mine.any():
            cards(part, base[mine], grow_[mine], face[mine], h[mine] * .95, h[mine], cell, cols[mine], crown, rng, CANOPY_FOOT)
    return np.array([line[-1] for line in twigs])


RED_CLUMPS = {3: (.85, 1.05), 2: (.6, .75)}       # clump radii by tip depth (cluster crowns)
WHITE_CLUMPS = {3: (.65, .85), 2: (.65, .85)}
FRUIT_CLUMPS = {2: (.5, .62), 1: (.38, .46)}


def tree_red():
    """A red-crowned tree, 10 m (a maple in autumn): furrowed black bark, a short trunk forking into spreading limbs,
    and a broad crown of red leaves on fine black twigs (BRANCHLET_CANOPIES; else clumps of leaf cards), bright where the
    light reaches and deep red inside."""
    rng = np.random.default_rng(503)
    p = Part('SM_CV_TreeRed', ('CN_Bark', 'CN_Leaf'))
    cfg = dict(segs=[8, 6, 4, 3], up=[.1, .32, .22, .15], wiggle=.12, taper=[.55, .45, .4, .35], children=[4, 3, 2],
               t0=[.55, .35, .45], spread=[(.55, .85), (.45, .8), (.4, .8)], ratio=[(.62, .78), (.55, .7), (.5, .62)],
               child_r=[.6, .62, .65])
    t = grow(rng, np.zeros(3), (.06, -.04, 1), 4.6, .3, cfg)
    wood(p, rng, t, CHARCOAL, 'CN_Bark', [10, 6, 5, 3], ground=2.0)
    roots(p, rng, .3, 5, CHARCOAL, 'CN_Bark', 1.0, ground=2.0)
    tips = [tip for tip in t['tips'] if tip[2] >= 2]
    crown = crown_from(tips, RED_CLUMPS)
    colours = (RED, RED_BRIGHT, RED_DEEP)
    fit = TREE_FIT[p.name]
    if BRANCHLET_CANOPIES:
        twig_crown(p, np.random.default_rng(503 + 1000), t['wood'], t['tips'], 3, crown, fit[1], CHARCOAL,
                   (CELL_MAPLE_A, CELL_MAPLE_B), 1100, (.45, .7), colours)
    else:
        for e, d, depth in tips:
            if depth == 3:
                cluster(p, rng, e + d * .25 + (0, 0, .1), rng.uniform(*RED_CLUMPS[3]), 60, colours, crown, (.2, .3), .3)
            else:
                cluster(p, rng, e + (0, 0, .05), rng.uniform(*RED_CLUMPS[2]), 28, colours, crown, (.18, .26), .3)
    _scale_to(p, 10.0, fit=fit)
    return _finish_plant(p, False)


def tree_white():
    """A white tree in blossom, 9 m: pale bark marked with dark lenticel dashes like a birch, three leaders from a
    low fork, and clouds of white five-petalled blossom with a few young leaves on pale twigs (BRANCHLET_CANOPIES; else
    clumps of blossom cards)."""
    rng = np.random.default_rng(504)
    p = Part('SM_CV_TreeWhite', ('CN_Bark', 'CN_Leaf'))
    cfg = dict(segs=[7, 6, 4, 3], up=[.15, .45, .3, .2], wiggle=.1, taper=[.6, .45, .4, .35], children=[3, 3, 2],
               t0=[.7, .35, .45], spread=[(.35, .6), (.45, .8), (.45, .85)], ratio=[(.85, 1.0), (.5, .66), (.48, .6)],
               child_r=[.72, .6, .62])
    t = grow(rng, np.zeros(3), (-.04, .05, 1), 2.6, .26, cfg)
    wood(p, rng, t, IVORY, 'CN_Bark', [10, 6, 5, 3], ground=1.5, bands=.16, under=.3)
    roots(p, rng, .26, 4, IVORY, 'CN_Bark', .8, ground=1.5, bands=.1)
    tips = [tip for tip in t['tips'] if tip[2] >= 2]
    crown = crown_from(tips, WHITE_CLUMPS)
    fit = TREE_FIT[p.name]
    if BRANCHLET_CANOPIES:
        twig_crown(p, np.random.default_rng(504 + 1000), t['wood'], t['tips'], 3, crown, fit[1], IVORY,
                   (CELL_BLOSSOM2, CELL_BLOSSOM), 1000, (.4, .6), (WHITE_PURE, IVORY))
    else:
        for e, d, depth in tips:
            c = e + d * .2 + (0, 0, .08)
            r = rng.uniform(*WHITE_CLUMPS[depth])
            # No filler ball inside: blossom this sparse cannot hide one, and a solid ball among the flowers reads as a
            # stone caught in the tree; the crown is lacy instead, as blossom is, and the budget goes to more flowers.
            pts, out, depth_ = shell_points(rng, c, (r, r, r * .78), 36, .62)
            leaf_cards(p, rng, pts, out, crown, 9, (.7, .95), (WHITE_PURE, IVORY), CELL_BLOSSOM, .5, .1, depth=depth_)
            cluster(p, rng, c, r * .9, 10, (IVORY, WHITE_COOL), crown, (.08, .12), .2)
    _scale_to(p, 9.0, fit=fit)
    return _finish_plant(p, False)


def fruit_tree():
    """An orchard tree, 5 m: a short trunk limewashed white below its first fork as orchards do, dark bark above,
    an open vase of scaffold limbs, silver-white leaves on pale twigs (BRANCHLET_CANOPIES; else clumps of leaf cards)
    and gold fruit hanging under them. An open orchard crown shows sky between its leaves."""
    rng = np.random.default_rng(505)
    p = Part('SM_CV_FruitTree', ('CN_White', 'CN_Bark', 'CN_Leaf'))
    trunk = bezier((0, 0, 0), (.03, 0, .4), (.06, .02, .8), (.05, .03, 1.15), 5)
    branch_limb(p, trunk[:4], np.linspace(.17, .145, 4), tone(WHITE_PURE, .92), 'CN_White', 9, rng, ground=.8, under=.15)
    branch_limb(p, trunk[2:], np.linspace(.15, .13, 3), CHARCOAL, 'CN_Bark', 9, rng, ground=1.0)
    roots(p, rng, .17, 4, tone(WHITE_PURE, .92), 'CN_White', .5, ground=.8)
    cfg = dict(segs=[6, 4, 3], up=[.55, .3, .2], wiggle=.12, taper=[.5, .45, .4], children=[3, 2], t0=[.4, .45],
               spread=[(.45, .8), (.45, .8)], ratio=[(.55, .7), (.5, .62)], child_r=[.62, .62])
    tips, branches = [], []
    for k in range(4):
        a = k / 4 * TAU + rng.uniform(-.25, .25)
        d = np.array([math.cos(a) * .85, math.sin(a) * .85, 1])
        t = grow(rng, trunk[-1] - (0, 0, .05), d, rng.uniform(1.6, 1.9), .1, cfg)
        wood(p, rng, t, CHARCOAL, 'CN_Bark', [7, 5, 3], ground=1.0)
        tips += [(e, dd, depth) for e, dd, depth in t['tips'] if depth >= 1]
        branches += t['wood']
    crown = crown_from([tip for tip in tips if tip[2] >= 2], FRUIT_CLUMPS)
    fit = TREE_FIT[p.name]
    if BRANCHLET_CANOPIES:
        ends = twig_crown(p, np.random.default_rng(505 + 1000), branches, tips, 2, crown, fit[1], IVORY, (CELL_ORCHARD,), 650,
                          (.32, .48), (WHITE_COOL, WHITE_PURE))
        fruit = [q - UP * .07 / fit[1] for q in ends[np.random.default_rng(505 + 2000).permutation(len(ends))]]
    else:
        fruit = []
        for e, d, depth in tips:
            c = e + d * .12 + (0, 0, .06)
            if depth == 2:
                pts = cluster(p, rng, c, rng.uniform(*FRUIT_CLUMPS[2]), 58, (WHITE_COOL, WHITE_PURE), crown, (.11, .15), .3)
                under = pts[pts[:, 2] < c[2] - .12]
                fruit += [q - (0, 0, .08) for q in under[:2]]
            else:
                cluster(p, rng, c, rng.uniform(*FRUIT_CLUMPS[1]), 32, (WHITE_COOL, WHITE_PURE), crown, (.11, .14), .3)
    for q in fruit[:34]:
        ball(p, q, rng.uniform(.045, .055), tone(GOLD_DEEP, rng.uniform(.88, 1.05)), 'CN_Leaf', 6, (1, 1, .92))
    _scale_to(p, 5.0, fit=fit)
    return _finish_plant(p, False)


CONE_UP = .3           # the conifer's normals: its cone's, plus this much of world up


def tree_black():
    """A black conifer, 12 m, like a spruce: a straight tapering trunk and whorls of branches that droop and turn up at
    the tips (the wood, which collides), each branch carrying alternate side shoots under shelves of needle sprays;
    short shoots between the whorls, dead twiglets over the bare lowest spears and a leader of upturned sprays
    (_conifer_foliage)."""
    rng = np.random.default_rng(506)
    p = Part('SM_CV_TreeBlack', ('CN_Bark', 'CN_Leaf'))
    H = 12.0
    z = np.linspace(0, H, 15)
    trunk = np.stack([.06 * np.sin(z * .7), .05 * np.cos(z * .5) - .05, z], 1)
    branch_limb(p, trunk, np.linspace(.34, .025, 15), CHARCOAL, 'CN_Bark', 9, rng, ground=2.0)
    roots(p, rng, .34, 5, CHARCOAL, 'CN_Bark', .9, ground=2.0)
    branches, whorls = [], []
    zc, i = 1.4, 0
    while zc < H - .8:
        f = (zc - 1.4) / (H - 2.2)
        L = 3.1 * (1 - f) ** 1.1 + .35
        count = 5 if f < .65 else 4
        base_c = np.array([.06 * math.sin(zc * .7), .05 * math.cos(zc * .5) - .05, zc])
        for k in range(count):
            az = i * .87 + k * TAU / count + rng.uniform(-.25, .25)
            out = np.array([math.cos(az), math.sin(az), 0])
            sag = .26 * L * (1 - .5 * f)
            pts = bezier(base_c, base_c + out * L * .35 - UP * sag * .2, base_c + out * L * .75 - UP * sag,
                         base_c + out * L + UP * (-.6 * sag + .1 * L), 6)
            branch_limb(p, pts[::2].tolist() + [pts[-1].tolist()], np.linspace(.03 + .025 * L, .008, 4), CHARCOAL, 'CN_Bark',
                        4 if f < .5 else 3, rng, ground=2.0, under=.15)
            # The six sprays the branch first carried drew these numbers here; drawing them still keeps every later
            # whorl (the wood, which collides) where it stood.
            for _ in range(6):
                rng.normal(0, .12, 3)
                rng.uniform(.3, 1.0)
                rng.uniform(0, 1, 1)
            branches.append((pts, L, f))
        whorls.append((zc, L))
        zc += .52 + rng.uniform(-.05, .08)
        i += 1
    _conifer_foliage(p, trunk, branches, whorls, H)
    _scale_to(p, H, balance=False, fit=TREE_FIT[p.name])
    return _finish_plant(p, False)


def _conifer_foliage(p, trunk, branches, whorls, height):
    """The black conifer's foliage, from a generator of its own (the wood keeps its numbers), all CN_Leaf: on every
    whorl branch 4-8 alternate side shoots (thin solid strands) each under a needle spray, the branch's own sprays in
    shelves above and below them drooping at the tip, a short shoot or two between the whorls, dead twiglets over the
    lowest whorls' bare spears, and a leader of upturned sprays. Greys only: slate to ash where lit, charcoal to slate
    inside, a tenth of the tips frosted white. Normals follow a cone round the trunk (the crown's radius at each height
    over the tree's height), turned up by CONE_UP."""
    rng = np.random.default_rng(506 + 1000)
    zs = trunk[:, 2]
    sprays = []    # base, grow, facing, width, height, lean, cell, colour, crown radius there

    def axis(z):
        return np.array([np.interp(z, zs, trunk[:, 0]), np.interp(z, zs, trunk[:, 1]), z])

    def spray(base, grow_, length, radius, cell, tip, lean=.15, side=0.0):
        u = rng.uniform()
        if u < .06:            # a tenth or so of the sprays are missing or short: an irregular outline
            return
        h = length * (.55 if u < .13 else 1.0)
        radial = np.linalg.norm((base - axis(base[2]))[:2])
        if tip and rng.uniform() < .1:
            colour = tone(WHITE_COOL, rng.uniform(.8, .95))
        elif radial < .45 * radius:
            colour = tone(mix(CHARCOAL, SLATE, rng.uniform(0, 1)))
        else:
            colour = tone(mix(SLATE, ASH, rng.uniform(0, 1)))
        side_dir = unit(np.cross(UP, grow_) + 1e-9)
        face = unit(UP + side_dir * side + rng.normal(0, .1, 3))
        sprays.append((base, grow_, face, h * .55, h, lean, cell, colour, radius))
    lowest = whorls[1][0] if len(whorls) > 1 else whorls[0][0]
    for pts, L, f in branches:
        cell = CELL_TWIGS if pts[0][2] <= lowest + 1e-6 else CELL_NEEDLE
        shoots = int(np.clip(round(4 + 4 * L / 3.45), 4, 8))
        for j, t in enumerate(np.linspace(.22, .92, shoots) + rng.uniform(-.03, .03, shoots)):
            q, d = _along(pts, float(np.clip(t, 0, 1)))
            side = unit(np.cross(UP, d)) * (1 if j % 2 else -1)
            ang = math.radians(rng.uniform(45, 60))
            way = unit(d * math.cos(ang) + side * math.sin(ang) - UP * .1)
            length = rng.uniform(.3, .5) * L
            r = rng.uniform(.006, .01)
            limb(p, [q, q + way * length], [r, r * .6], CHARCOAL, 'CN_Leaf', 3, cap=False)
            spray(q, unit(way + UP * .08), length * 1.1, L, cell, t > .7, rng.uniform(.15, .3), .2 * (1 if j % 2 else -1))
        # The branch's own sprays: a shelf above the shoots and one below, and its drooping tip.
        for t, lift, scale_ in ((.3, .05, .5), (.62, -.05, .42)):
            q, d = _along(pts, t)
            spray(q + UP * lift, d, scale_ * L, L, cell, False)
        q, d = _along(pts, .78)
        spray(q, unit(d + UP * .05), .3 * L + .25, L, cell, True, .35)
    # Short shoots between the whorls.
    for (z0, L0), (z1, L1) in zip(whorls, whorls[1:]):
        for _ in range(int(rng.integers(1, 3))):
            zz = z0 + (z1 - z0) * rng.uniform(.3, .7)
            az = rng.uniform(0, TAU)
            out = np.array([math.cos(az), math.sin(az), 0.0])
            q = axis(zz)
            length = rng.uniform(.3, .6) * (L0 + L1) / 2 * .6
            way = unit(out + UP * .15)
            limb(p, [q, q + way * length], [.008, .005], CHARCOAL, 'CN_Leaf', 3, cap=False)
            spray(q + way * length * .2, way, length, (L0 + L1) / 2, CELL_NEEDLE, True, .2)
    # The leader: upturned sprays round the trunk's top.
    for k in range(int(rng.integers(2, 4))):
        az = k * TAU / 3 + rng.uniform(-.4, .4)
        out = np.array([math.cos(az), math.sin(az), 0.0])
        spray(axis(height - .65) + out * .03, unit(UP + out * .15), rng.uniform(.9, 1.1), .35, CELL_NEEDLE, True, .05)
    for cell in (CELL_NEEDLE, CELL_TWIGS):
        mine = [s for s in sprays if s[6] == cell]
        if not mine:
            continue
        base = np.array([s[0] for s in mine])
        radial = unit((base - np.array([axis(z) for z in base[:, 2]])) * (1, 1, 0) + 1e-9)
        a = np.arctan(np.array([s[8] for s in mine]) / height)[:, None]
        normal = unit(radial * np.cos(a) + UP * (np.sin(a) + CONE_UP))
        for lean in sorted({s[5] for s in mine}):
            pick = [k for k, s in enumerate(mine) if s[5] == lean]
            cards(p, base[pick], np.array([mine[k][1] for k in pick]), np.array([mine[k][2] for k in pick]),
                  np.array([mine[k][3] for k in pick]), np.array([mine[k][4] for k in pick]), cell,
                  np.array([mine[k][7] for k in pick]), rng=rng, foot=CANOPY_FOOT, lean=lean, normal=normal[pick])


# ---------------------------------------------------------------- vines, rocks, water plants

def vines():
    """A curtain of vines, 2 m wide, hanging 3 m from its top stem (a creeper in autumn, its leaves red): black woody
    strands of varied length curling at their ends, leaves alternating along them, darker toward the wall behind
    (-x), which the curtain's flat back is built to sit against."""
    rng = np.random.default_rng(601)
    p = Part('SM_CV_Vines', ('CN_Black', 'CN_Leaf'))
    ys = np.linspace(-1.0, 1.0, 11)
    top = np.stack([.04 + .03 * np.sin(ys * 5), ys, 2.94 + .04 * np.sin(ys * 3.3 + 1)], 1)
    branch_limb(p, top, .028, CHARCOAL, 'CN_Black', 6, rng, ground=3.0, under=.3)
    for k in range(12):
        y0 = -.95 + k * 1.9 / 11 + rng.uniform(-.05, .05)
        q0 = np.array([.04, y0, 2.93])
        length = rng.uniform(1.3, 2.9) if k % 3 else 2.9
        sway = rng.uniform(-.35, .35)
        strand = bezier(q0, q0 + (.06, sway * .2, -length * .3), q0 + (.1, sway * .7, -length * .7),
                        q0 + (.12 + rng.uniform(0, .1), sway + rng.uniform(-.15, .15), -length), 7)
        strand[:, 2] = np.maximum(strand[:, 2], .02)
        branch_limb(p, strand, np.linspace(.014, .005, 7), CHARCOAL, 'CN_Black', 3, rng, ground=3.0, under=.2)
        n = int(length / .14)
        t = np.linspace(.04, .98, n)
        idx = t * 6
        i0 = np.minimum(idx.astype(int), 5)
        w = (idx - i0)[:, None]
        pos = strand[i0] * (1 - w) + strand[i0 + 1] * w
        side = np.where((np.arange(n) % 2 == 0)[:, None], np.array([0, 1.0, 0]), np.array([0, -1.0, 0]))
        d = unit(side * .8 + np.array([.5, 0, -.45]) + rng.normal(0, .25, (n, 3)))
        face = unit(np.array([1.0, 0, .25]) + rng.normal(0, .3, (n, 3)))
        L = rng.uniform(.08, .13, n)
        cols = mix(RED_DEEP, RED_BRIGHT, rng.uniform(0, 1, n))
        k_ = .7 + .3 * np.clip(pos[:, 0] / .2, 0, 1)
        leaves(p, pos, d, face, L, L * .6, np.array([tone(c, kk) for c, kk in zip(cols, k_)]), .35, .15)
    n = 36
    i0 = rng.integers(0, 10, n)
    w = rng.uniform(0, 1, (n, 1))
    pos = top[i0] * (1 - w) + top[i0 + 1] * w + (0, 0, .02)
    d = unit(np.array([.6, 0, -.3]) + rng.normal(0, .5, (n, 3)))
    L = rng.uniform(.09, .14, n)
    leaves(p, pos, d, unit(np.array([1.0, 0, .5])), L, L * .6, mix(RED_DEEP, RED, rng.uniform(0, 1, n)), .35, .1)
    v = np.asarray(p.v, np.float64)
    v[:, 0] = np.maximum(v[:, 0], -.1)  # keep the back flat to the wall
    p.v = v.tolist()
    return _finish_plant(p)


def hull3(points):
    """Convex hull of 3-D points (incremental): triangles wound outward. Enough for a few dozen points."""
    P = np.asarray(points, np.float64)
    c = P[:4].mean(0)
    faces = [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]

    def outward(f):
        n = np.cross(P[f[1]] - P[f[0]], P[f[2]] - P[f[0]])
        return f if np.dot(n, P[f[0]] - c) > 0 else [f[0], f[2], f[1]]
    faces = [outward(f) for f in faces]
    for i in range(4, len(P)):
        seen = [f for f in faces if np.dot(np.cross(P[f[1]] - P[f[0]], P[f[2]] - P[f[0]]), P[i] - P[f[0]]) > 1e-9]
        if not seen:
            continue
        edges = {}
        for f in seen:
            for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                edges[e] = edges.get(e, 0) + 1
        horizon = [e for e in edges if (e[1], e[0]) not in edges]
        faces = [f for f in faces if f not in seen] + [[e[0], e[1], i] for e in horizon]
    return faces


def rock(name, slot, seed, colours, size=(2.0, 1.55, 1.1), strata=0.0):
    """A boulder as real rock breaks: the convex hull of a jittered cloud of points (its fracture facets) on a flat
    bedding face, each facet subdivided and displaced by position-dependent noise (so neighbouring facets stay
    crack-free) and kept as its own smoothing set, so its edges stay crisp while its face weathers. Vertex colour
    darkens toward the ground and lightens on exposed edges and tops; strata when asked."""
    rng = np.random.default_rng(seed)
    p = Part(name, (slot,))
    half = np.asarray(size, np.float64) / 2
    d = unit(rng.normal(0, 1, (34, 3)))
    cloud = d * half * rng.uniform(.78, 1.0, (34, 1))
    cloud[:, 2] = np.maximum(cloud[:, 2], -half[2] * .55)  # the bedding face it rests on
    tris = hull3(cloud)
    centre = cloud.mean(0)
    n = 4
    bary = [(i, j) for i in range(n + 1) for j in range(n + 1 - i)]
    lo_z = cloud[:, 2].min()
    for f in tris:
        A, B, C = cloud[f]
        idx = {}
        verts = []
        for i, j in bary:
            idx[i, j] = len(verts)
            verts.append(A + (B - A) * i / n + (C - A) * j / n)
        verts = np.array(verts)
        edge = np.array([min(i, j, n - i - j) == 0 for i, j in bary])
        radial = unit(verts - centre)
        bump = .045 * noise2(verts[:, 0] * 2.3 + verts[:, 2], verts[:, 1] * 2.3 - verts[:, 2], seed) + \
            .015 * noise2(verts[:, 0] * 7, verts[:, 1] * 7 + verts[:, 2] * 3, seed + 1)
        verts = verts + radial * (bump * np.mean(size))[:, None]
        verts = np.where(edge[:, None], verts - radial * .012 * np.mean(size), verts)  # worn, slightly rounded edges
        faces = []
        for i in range(n):
            for j in range(n - i):
                faces.append([idx[i, j], idx[i + 1, j], idx[i, j + 1]])
                if i + j < n - 1:
                    faces.append([idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]])
        nrm = np.cross(B - A, C - A)
        faces = [_facing(verts, q, nrm) for q in faces]
        hgt = np.clip((verts[:, 2] - lo_z) / (2 * half[2]), 0, 1)
        k = (.58 + .42 * np.clip(hgt * 1.5, 0, 1)) * np.where(edge, 1.06, 1.0)
        k *= .9 + .1 * noise2(verts[:, 0] * 3 + verts[:, 2] * 2, verts[:, 1] * 3, seed + 3)
        k *= .92 + .08 * max(0.0, float(unit(nrm)[2]))
        if strata:
            k *= 1 - strata * (np.sin(verts[:, 2] * 17 + 2 * noise2(verts[:, 0], verts[:, 1], seed + 5)) > .6)
        base, alt = colours
        cols = mix(base, alt, np.clip(.5 + .5 * noise2(verts[:, 0] * 1.3, verts[:, 1] * 1.3 + verts[:, 2], seed + 9), 0, 1))
        p.add(verts, faces, np.array([tone(cc, kk) for cc, kk in zip(cols, k)]), slot, True)
    return _finish_plant(p)


def rock_white():
    """A white boulder (limestone): pale and slightly warm, faint strata, grey in its hollows."""
    return rock('SM_CV_RockWhite', 'CN_White', 701, (WHITE, IVORY), strata=.12)


def rock_black():
    """A black boulder (basalt): dark grey, darker in its hollows, a little paler on its upper faces."""
    return rock('SM_CV_RockBlack', 'CN_Black', 702, (SLATE, CHARCOAL), (1.9, 1.7, 1.2))


def reeds():
    """A clump of common reed, 1.4 m, in summer green (author, 2026-11-08; it was autumn gold): green stems with long
    arching leaves, the tallest carrying pale straw plumes that droop to one side."""
    rng = np.random.default_rng(801)
    p = Part('SM_CV_Reeds', ('CN_Leaf',))
    for k in range(20):
        a = rng.uniform(0, TAU)
        r = .16 * math.sqrt(rng.uniform(0, 1))
        base = np.array([math.cos(a) * r, math.sin(a) * r, 0])
        h = rng.uniform(1.0, 1.42) * (1 - .2 * r / .16)
        lean = np.array([math.cos(a), math.sin(a), 0]) * rng.uniform(.03, .12) * h
        stem = bezier(base, base + (0, 0, h * .4), base + lean * .6 + (0, 0, h * .8), base + lean + (0, 0, h), 4)
        limb(p, stem, np.linspace(.0065, .0035, 4), tone(GREEN_GRASS, np.linspace(.75, 1.05, 4)), 'CN_Leaf', 3, cap=False)
        for j in range(2 if k % 2 else 1):
            node = stem[1] * (1 - .4 * j) + stem[2] * .4 * j
            out = unit(np.array([math.cos(a + 2.1 * j + 1), math.sin(a + 2.1 * j + 1), 0]))
            L = rng.uniform(.35, .55)
            blades(p, node, node + out * L * .6 + UP * L * .35, .018, tone(GREEN_LEAF, .85), tone(GREEN_PALE, .95), 3, .55)
        if h > 1.0:
            top = stem[-1]
            droop = unit(np.array([math.cos(a + .5), math.sin(a + .5), 0]))
            ends = top + droop * rng.uniform(.06, .1) - UP * rng.uniform(.06, .14) + rng.normal(0, .025, (6, 3))
            starts = np.repeat([top], 6, 0) - np.outer(np.linspace(0, .12, 6), UP)
            blades(p, starts, ends + UP * .04, .02, pale(GOLD_STRAW, IVORY, .3), pale(GOLD_STRAW, IVORY, .45), 2, .2)
    return _finish_plant(p)


def lily():
    """Water lilies, placed at the water surface (z 0): round light-blue-white pads with their notch and a faint cupped
    rim, floating a centimetre clear of the water plane so the two never fight for depth; two white flowers of three
    petal rings round gold stamens, and a closed bud whose stem stub reaches z 0."""
    rng = np.random.default_rng(802)
    p = Part('SM_CV_Lily', ('CN_Leaf',))
    pads = [((0, 0), .36), ((.55, .3), .3), ((-.42, .42), .27), ((.2, -.55), .33), ((-.55, -.25), .24)]
    for (x, y), r in pads:
        a0 = rng.uniform(0, TAU)
        ang = a0 + np.linspace(.18, TAU - .18, 20)
        rim = np.stack([x + np.cos(ang) * r, y + np.sin(ang) * r, .016 + .012 * np.sin(ang * 3 + a0) ** 2], 1)
        midr = np.stack([x + np.cos(ang) * r * .55, y + np.sin(ang) * r * .55, np.full(20, .012)], 1)
        c = np.array([[x + math.cos(a0) * r * .08, y + math.sin(a0) * r * .08, .01]])
        verts = np.concatenate([c, midr, rim])
        faces = [[0, 1 + j, 2 + j] for j in range(19)]
        faces += [[1 + j, 21 + j, 22 + j, 2 + j] for j in range(19)]
        faces = [_facing(verts, f, UP) for f in faces]
        base = mix(BLUE_PALE, WHITE_COOL, rng.uniform(0, .5))
        cols = np.concatenate([tone(base, .78).reshape(1, 4), np.tile(tone(base, .9), (20, 1)), np.tile(tone(base, 1.0), (20, 1))])
        p.add(verts, faces, cols, 'CN_Leaf', True)
    for (x, y), size in (((.05, .02), 1.0), ((-.4, .38), .8)):
        c = np.array([x, y, .026])
        for ring_i, (count, length, cup) in enumerate(((8, .12, .35), (8, .1, .7), (6, .075, 1.05))):
            _cup(p, c + (0, 0, .01 * ring_i), UP, count, length * size, .8, tone(WHITE_PURE, .92 + .03 * ring_i), cup, None, 3,
                 ring_i * .4)
        ball(p, c + (0, 0, .035 * size), .022 * size, tone(GOLD_DEEP), 'CN_Leaf', 6, (1, 1, .7))
    bud = np.array([.48, -.18, .0])
    limb(p, [bud, bud + (0, 0, .05)], .008, tone(BLUE_PALE, .8), 'CN_Leaf', 4, cap=False)
    ball(p, bud + (0, 0, .09), .03, tone(WHITE_PURE, .9), 'CN_Leaf', 6, (1, 1, 1.6))
    return _finish_plant(p)


# ---------------------------------------------------------------- the module's meshes and their contract

MESHES = [al_mite, al_lancer, al_bulwark, echo_hunter, al_reaver, al_siegeframe, al_shepherd, al_anchor,
          grass_gold, wheat, flowers_white, flowers_red, flowers_blue, shrub, hedge, tree_white, tree_red, tree_black,
          fruit_tree, vines, rock_white, rock_black, reeds, lily]


def _al(x, y, z):
    return {'size': (x, y, z), 'tol': .15, 'pivot': 'centre'}


def _plant(x, y, z, tol=.15):
    return {'size': (x, y, z), 'tol': tol, 'pivot': 'base'}


# Sizes in metres (x by y by z). The README's number for each AL is its largest dimension; the others are the
# design's. For plants the README height (and the hedge's footprint) is checked; 0 leaves an axis free where the
# crown's spread is the design's, not gameplay's. Rocks are built at 2 m and may be scattered at 0.5-1.5x (1-3 m).
CONTRACT = {
    'SM_CE_ALMite': _al(.6, .57, .29),
    'SM_CE_ALLancer': _al(1.2, .63, .58),
    'SM_CE_ALBulwark': _al(1.37, 1.68, 2.0),
    'SM_CE_EchoHunter': _al(1.6, .94, .45),
    'SM_CE_ALReaver': _al(1.79, 1.48, 2.4),
    'SM_CE_ALSiegeframe': _al(5.0, 3.5, 2.73),
    'SM_CE_ALShepherd': _al(1.68, 4.79, 7.0),
    'SM_CE_Anchor': _al(1.2, 1.2, .86),
    'SM_CV_GrassGold': _plant(1.8, 1.8, .6),   # a patch of clumps since the 2026-11-07 cards
    'SM_CV_Wheat': _plant(0, 0, 1.1),
    'SM_CV_FlowersWhite': _plant(.45, .45, .55),
    'SM_CV_FlowersRed': _plant(.4, .4, .6),
    'SM_CV_FlowersBlue': _plant(.42, .42, .52),
    'SM_CV_Shrub': _plant(0, 0, 1.2),
    'SM_CV_Hedge': _plant(1.0, 2.0, 1.2),
    'SM_CV_TreeWhite': _plant(0, 0, 9.0),
    'SM_CV_TreeRed': _plant(0, 0, 10.0),
    'SM_CV_TreeBlack': _plant(0, 0, 12.0),
    'SM_CV_FruitTree': _plant(0, 0, 5.0),
    'SM_CV_Vines': _plant(.32, 2.2, 3.0),
    'SM_CV_RockWhite': _plant(2.0, 0, 0, .5),
    'SM_CV_RockBlack': _plant(2.0, 0, 0, .5),
    'SM_CV_Reeds': _plant(0, 0, 1.4),
    'SM_CV_Lily': _plant(1.6, 1.55, .14),
}
