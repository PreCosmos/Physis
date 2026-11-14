"""Architecture of the Conclave (level 3): the Commons' houses, the Archive, the Orrery, the Mendery, the
listeners' Shrine, the market stall, street furniture, terrace walls and stairs, the North Gate, the
Wellspring garden and the Old Quarter's ruins. Pure numpy over toolkit and palette; the Blender entry
point (Tools/build_physis_conclave.py) builds and exports them, and check.py validates them offline.

Contract: Tools/conclave/README.md (names, sizes, slots). Every mesh faces +x and stands on z 0 with its
footprint centred on the origin. The town is Mediterranean meeting observatory: whitewashed lime render
(CN_Plaster) with light grey limestone dressings (bevelled quoins, cornices and string courses, sills and
surrounds), deep window reveals with frames and a room behind the glass, panelled lacquer doors, red
barrel-tile roofs, black iron railings, gold metal and light-blue glass and glaze. The Archive is white
marble throughout. Vertex colour is the albedo and carries the ageing (rising damp, rain stains, soot),
always inside the palette: paint() never darkens a gold, red or blue past the shade where it would leave
its family.
"""
import math

import numpy as np

import toolkit as tk
from palette import (ASH, BLACK, BLUE, BLUE_ICE, BLUE_PALE, CHARCOAL, GOLD, GOLD_DEEP, GOLD_GRASS, GOLD_PALE, GOLD_STRAW,
                     IVORY, LIGHT_BLUE, LIGHT_GOLD, LIGHT_WARM, RED, RED_BRIGHT, RED_DEEP, SLATE, WHITE, WHITE_COOL,
                     WHITE_PURE, allowed, grey)
from toolkit import Part, bevel_box, blob, box, hexa, lathe, noise2, torus, tube

UP = np.array([0., 0., 1.])

# README ceilings ("x by y by <=z"): the CONTRACT holds the ceiling as its z, so check.py also refuses a
# building more than 15% under it, and finish() refuses one over it.
CEILING = {'SM_CN_House0': 11.0, 'SM_CN_House1': 13.0, 'SM_CN_House2': 9.0, 'SM_CN_House3': 10.0,
           'SM_CN_Ruin0': 8.0, 'SM_CN_Ruin1': 7.0}

# Dressed stone (quoins, sills, surrounds, lintels, mouldings, voussoirs, piers) is light grey limestone, so it reads
# against the whitewashed render (WHITE_PURE on CN_Plaster): IVORY dressings were within 5 % of the walls and vanished
# into them. Each stone's own tint darkens it a little further.
LIMESTONE = grey(.68)

# The room behind a window's glass (it was a flush black plane, which read as a hole): at most ROOM_DEPTH deep behind
# the frame and ROOM_CLEAR short of the wall's nearer end, so a corner window's room keeps clear of the next wall's,
# never shallower than ROOM_MIN. Its edges sit TUCK behind the reveals they meet, so no slit opens at the joint and the
# two never share a plane.
ROOM_DEPTH, ROOM_CLEAR, ROOM_MIN, TUCK = .8, .15, .25, .003
# Where another part of the building stands closer behind a wall than a room would reach (house 2's loggia), the room
# stops ROOM_GAP short of it.
ROOM_GAP = .02


# ---------------------------------------------------------------- colour, kept inside the palette

_FLOORS = {}


def floor_of(rgb):
    """The darkest shading multiplier that keeps rgb in its palette family: gold darkened too far reads
    brown, red reads maroon and light blue reads navy, while the greys may go all the way to black."""
    key = tuple(round(float(x), 5) for x in rgb[:3])
    if key not in _FLOORS:
        base, m = np.array(key), 1.0
        while m > .011 and allowed(tuple(base * (m - .01))):
            m -= .01
        _FLOORS[key] = m + .004
    return _FLOORS[key]


def paint(rgb, mult):
    """Per-vertex colours: rgb darkened by mult (ageing, occlusion), clamped to rgb's family."""
    m = np.clip(np.asarray(mult, np.float64).reshape(-1), floor_of(rgb), 1.0)
    out = np.ones((len(m), 4))
    out[:, :3] = np.asarray(rgb[:3], np.float64)[None, :] * m[:, None]
    return out


def tint(rgb, m):
    """One colour darkened by m within its family: the per-stone, per-tile, per-board variation."""
    m = min(max(float(m), floor_of(rgb)), 1.0)
    return (rgb[0] * m, rgb[1] * m, rgb[2] * m, 1.0)


def shader(rgb, fn):
    """A toolkit shade callback that never darkens rgb out of its family."""
    lo = floor_of(rgb)
    return lambda v: np.clip(fn(np.asarray(v, np.float64)), lo, 1.0)


def weather(v, seed, damp=.26, rise=.75, stain=.06, level=.97, ground=0.0):
    """Stone and plaster ageing per vertex: rising damp and splash grime toward the ground, broad rain
    stains and a fine mottle. A multiplier on albedo (1 is clean)."""
    v = np.asarray(v, np.float64).reshape(-1, 3)
    h = np.maximum(v[:, 2] - ground, 0)
    s = v[:, 0] * .83 + v[:, 1] * .57
    m = level - damp * np.exp(-h / rise)
    m = m + stain * noise2(s / 2.1, v[:, 2] / 3.3, seed) + stain * .45 * noise2(s / .55, v[:, 2] / .8, seed + 11)
    return np.clip(m, 0, 1)


def scorch(v, seed, strength=.75, base=.9, top=None):
    """Fire damage for the Old Quarter: soot blooms from noise, heaviest high on the walls where the
    roofs burned and low where rubble smouldered; whites darken to greys (never off the palette)."""
    v = np.asarray(v, np.float64).reshape(-1, 3)
    s = v[:, 0] * .71 + v[:, 1] * .7
    bloom = np.clip(.5 + .7 * noise2(s / 1.7, v[:, 2] / 1.3, seed) + .3 * noise2(s / .5, v[:, 2] / .45, seed + 3), 0, 1)
    high = np.clip((v[:, 2] - 2.0) / 4.0, 0, 1) if top is None else np.clip(1 - (top - v[:, 2]) / 2.5, 0, 1)
    m = base * (1 - strength * bloom * (.45 + .55 * high)) - .22 * np.exp(-np.maximum(v[:, 2], 0) / .6)
    return np.clip(m, .06, 1)


# ---------------------------------------------------------------- low-level geometry

def add(p, verts, faces, colours, slot, smooth=False):
    """Part.add for a vertex pool that may hold unused points (the cell grids): drops them, so no loose
    vertices reach the FBX."""
    verts = np.asarray(verts, np.float64).reshape(-1, 3)
    cols = np.asarray(colours, np.float64)
    used = sorted({i for f in faces for i in f})
    if not used:
        return None
    remap = {old: new for new, old in enumerate(used)}
    faces = [[remap[i] for i in f] for f in faces]
    return p.add(verts[used], faces, cols[used] if cols.ndim == 2 else cols, slot, smooth)


def newell(pts):
    """Area-weighted normal of a planar polygon (robust where the first three points are nearly in line)."""
    pts = np.asarray(pts, np.float64)
    return .5 * np.cross(pts, np.roll(pts, -1, 0)).sum(0)


def poly(p, pts, want, colour, slot, smooth=False):
    """One convex polygon turned to face along want. colour: one colour or one per point."""
    pts = np.asarray(pts, np.float64)
    cols = np.asarray(colour, np.float64)
    if np.dot(newell(pts), want) < 0:
        pts = pts[::-1]
        if cols.ndim == 2:
            cols = cols[::-1]
    return p.add(pts, [list(range(len(pts)))], cols, slot, smooth)


def fill_lines(lines, step):
    """Sorted grid lines with extra lines so no gap is wider than step (vertex colour needs vertices)."""
    out = [lines[0]]
    for a, b in zip(lines, lines[1:]):
        if b - a < 1e-6:
            continue
        k = max(1, int(math.ceil((b - a) / step - 1e-9)))
        out += [a + (b - a) * t / k for t in range(1, k + 1)]
    return np.array(out)


def sweep3(p, pts, dirs, normal, section, colour, slot, closed=True, mult=None, smooth=False):
    """Sweeps a moulding section along a world path: plinths, string courses, cornices, copings.
    pts: path points (counter-clockwise about normal), dirs: the direction (per point) a section's out
    moves it, scaled so mitred corners stay square; section: [(out, h)] listed with the solid on the left."""
    pts, dirs, normal = np.asarray(pts, np.float64), np.asarray(dirs, np.float64), np.asarray(normal, np.float64)
    K = len(section)
    verts = np.array([pt + o * d + h * normal for pt, d in zip(pts, dirs) for o, h in section])
    faces = []
    M = len(pts)
    for m in range(M if closed else M - 1):
        m2 = (m + 1) % M
        for k in range(K - 1):
            faces.append([m * K + k, m2 * K + k, m2 * K + k + 1, m * K + k + 1])
    cols = paint(colour, mult(verts) if mult else np.ones(len(verts)))
    return p.add(verts, faces, cols, slot, smooth)


def rect_ring(cx, cy, hx, hy, step=1.2):
    """A rectangle around (cx, cy), counter-clockwise from above, subdivided every step metres (so the
    moulding carries vertex colour), with mitre directions at the corners."""
    corners = [((hx, hy), (1, 1)), ((-hx, hy), (-1, 1)), ((-hx, -hy), (-1, -1)), ((hx, -hy), (1, -1))]
    pts, dirs = [], []
    for k in range(4):
        (ax, ay), da = corners[k]
        (bx, by), _ = corners[(k + 1) % 4]
        side = np.array([bx - ax, by - ay], np.float64)
        n = int(max(1, math.ceil(np.linalg.norm(side) / step)))
        outward = np.array([side[1], -side[0]]) / np.linalg.norm(side)
        for t in range(n):
            pts.append((cx + ax + side[0] * t / n, cy + ay + side[1] * t / n, 0.0))
            dirs.append((da[0], da[1], 0.0) if t == 0 else (outward[0], outward[1], 0.0))
    return np.array(pts), np.array(dirs)


def ring_moulding(p, x0, x1, y0, y1, z, section, colour, slot='CN_White', seed=0, step=2.0, mult=None):
    """A moulding run all round a rectangular building at height z."""
    pts, dirs = rect_ring((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2, step)
    pts[:, 2] = z
    return sweep3(p, pts, dirs, UP, section, colour, slot, True, mult or (lambda v: weather(v, seed, damp=.1, stain=.05)))


# Moulding sections (out, h) in metres, solid on the left: base course, string course, eaves cornice,
# parapet coping, window surround. Each ends back at the wall.
PLINTH = [(0, 0), (.07, 0), (.07, .36), (.04, .42), (0, .42)]
STRING = [(0, 0), (.035, .01), (.06, .05), (.06, .12), (.03, .16), (0, .16)]
CORNICE = [(0, 0), (.04, .02), (.06, .08), (.1, .1), (.12, .15), (.24, .2), (.27, .24), (.29, .3), (.29, .34), (0, .34)]
COPING = [(0, 0), (.04, 0), (.04, .07), (.02, .1), (-.02, .1), (-.04, .07), (-.04, 0)]


# ---------------------------------------------------------------- walls with openings

class Wall:
    """A wall's surface coordinates: u along it (left to right seen from outside), v up, d into it.
    Flat (outer-face origin o, outward normal n), or round (a drum of radius r around o, u measured
    along the circumference from angle a0), so windows, doors and arches fit houses and the Archive
    alike."""

    def __init__(self, o=(0, 0, 0), n=(1, 0, 0), r=None, a0=0.0):
        self.o = np.asarray(o, np.float64)
        n = np.asarray(n, np.float64)
        self.n = n / np.linalg.norm(n)
        self.U = np.cross(UP, self.n)
        self.r, self.a0 = r, a0

    def at(self, u, v, d=0.0):
        u, v, d = np.broadcast_arrays(np.asarray(u, np.float64), np.asarray(v, np.float64), np.asarray(d, np.float64))
        if self.r is None:
            return self.o + u[..., None] * self.U + v[..., None] * UP - d[..., None] * self.n
        a = self.a0 + u / self.r
        rr = self.r - d
        return np.stack([self.o[0] + rr * np.cos(a), self.o[1] + rr * np.sin(a), self.o[2] + v], -1)

    def normal(self, u):
        if self.r is None:
            return self.n
        a = self.a0 + u / self.r
        return np.array([math.cos(a), math.sin(a), 0.])

    def tangent(self, u):
        if self.r is None:
            return self.U
        a = self.a0 + u / self.r
        return np.array([-math.sin(a), math.cos(a), 0.])

    def yaw(self, u):
        n = self.normal(u)
        return math.degrees(math.atan2(n[1], n[0]))

    def dir(self, u, du=0., dv=0., dn=0.):
        return du * self.tangent(u) + dv * UP + dn * self.normal(u)


def wbox(p, w, u0, u1, v0, v1, d0, d1, colour, slot, bevel=.02, shade=None):
    """A box in wall coordinates (d into the wall, negative stands proud): sills, lintels, panels."""
    uc = (u0 + u1) / 2
    c = w.at(uc, (v0 + v1) / 2, (d0 + d1) / 2)
    h = (abs(d1 - d0) / 2, abs(u1 - u0) / 2, abs(v1 - v0) / 2)
    if bevel:
        return bevel_box(p, c, h, colour, slot, bevel, w.yaw(uc), shade)
    return box(p, c, h, colour, slot, w.yaw(uc), shade)


def wpoly(p, w, uvd, colour, slot, out=1.0, smooth=False):
    """A polygon given in wall coordinates, facing out of the wall (out=1) or into it (out=-1)."""
    uvd = np.asarray(uvd, np.float64)
    pts = w.at(uvd[:, 0], uvd[:, 1], uvd[:, 2])
    return poly(p, pts, w.normal(float(uvd[:, 0].mean())) * out, colour, slot, smooth)


def wsweep(p, w, path, section, colour, slot, closed=True, mult=None, smooth=False):
    """Sweeps a section along a path in a wall's surface: architraves, window and door frames.
    path: [(u, v, du, dv)] counter-clockwise seen from outside, (du, dv) the mitred outward offset;
    section: [(out, h)], h outward from the wall face, the solid on the left."""
    K = len(section)
    verts = np.array([w.at(u + o * du, v + o * dv, -h) for (u, v, du, dv) in path for o, h in section]).reshape(-1, 3)
    M = len(path)
    faces = []
    for m in range(M if closed else M - 1):
        m2 = (m + 1) % M
        for k in range(K - 1):
            faces.append([m * K + k, m2 * K + k, m2 * K + k + 1, m * K + k + 1])
    cols = paint(colour, mult(verts) if mult else np.ones(len(verts)))
    return p.add(verts, faces, cols, slot, smooth)


def rect_path(u0, u1, v0, v1, bottom=True):
    """Counter-clockwise round an opening (seen from outside); without its bottom for frames on a sill."""
    if bottom:
        return [(u1, v0, 1, -1), (u1, v1, 1, 1), (u0, v1, -1, 1), (u0, v0, -1, -1)]
    return [(u1, v0, 1, 0), (u1, v1, 1, 1), (u0, v1, -1, 1), (u0, v0, -1, 0)]


def arch_path(u0, u1, v0, spring, n=10, bottom=True):
    """Counter-clockwise round a round-headed opening: up the right jamb, over the arch, down the left."""
    r, uc = (u1 - u0) / 2, (u0 + u1) / 2
    path = [(u1, v0, 1, -1) if bottom else (u1, v0, 1, 0), (u1, spring, 1, 0)]
    for k in range(1, n):
        t = math.pi * k / n
        path.append((uc + r * math.cos(t), spring + r * math.sin(t), math.cos(t), math.sin(t)))
    path += [(u0, spring, -1, 0), (u0, v0, -1, -1) if bottom else (u0, v0, -1, 0)]
    return path


def outline(u0, u1, v0, v1, spring=None, inset=0.0, n=10):
    """The (u, v) outline of an opening, inset, counter-clockwise: glass, backings, glow panes."""
    if spring is None:
        return [(u0 + inset, v0 + inset), (u1 - inset, v0 + inset), (u1 - inset, v1 - inset), (u0 + inset, v1 - inset)]
    r, uc = (u1 - u0) / 2 - inset, (u0 + u1) / 2
    pts = [(u0 + inset, v0 + inset), (u1 - inset, v0 + inset)]
    pts += [(uc + r * math.cos(math.pi * k / n), spring + r * math.sin(math.pi * k / n)) for k in range(n + 1)]
    return pts


def wall_cells(p, w, length, height, colour, slot='CN_White', openings=(), reveal=.25, thick=None, top=None,
               cell=1.0, vcell=None, seed=0, v0=0.0, inner=None, mult=None, edge_mult=None, wrap=False, ends=(True, True),
               top_edge=True, extra_u=(), inner_mult=None):
    """A wall surface (u 0..length, v v0..height) as a grid of cells with holes for openings
    (u0, u1, v0, v1[, spring]) and their reveals, darker as they deepen. thick=None: a house wall, outer
    face only: the interior is never seen because every opening is closed by a window, door or backing.
    thick=t: a free-standing or ruined wall, both faces and every exposed edge. top(u): a ruined wall's
    broken top, which snaps to the cell courses as masonry breaks along its joints. ends: whether a solid
    wall's start and end faces show (not where they meet another wall face, which would z-fight);
    top_edge: whether its top does. A round-headed opening's reveal stops at its spring; arch_head()
    makes the rest."""
    if isinstance(ends, bool):
        ends = (ends, ends)
    us, vs = {0.0, float(length)} | {float(x) for x in extra_u if 0 < x < length}, {float(v0), float(height)}
    for op in openings:
        us |= {float(op[0]), float(op[1])}
        vs |= {float(op[2]), float(op[3])}
        if len(op) > 4 and op[4] is not None:
            vs.add(float(op[4]))
    us = fill_lines(sorted(x for x in us if -1e-9 <= x <= length + 1e-9), cell)
    vs = fill_lines(sorted(x for x in vs if v0 - 1e-9 <= x <= height + 1e-9), vcell or cell)
    nu, nv = len(us) - 1, len(vs) - 1
    uc, vc = (us[:-1] + us[1:]) / 2, (vs[:-1] + vs[1:]) / 2
    solid = np.ones((nu, nv), bool)
    hole = -np.ones((nu, nv), int)
    for k, op in enumerate(openings):
        inside = (uc[:, None] > op[0]) & (uc[:, None] < op[1]) & (vc[None, :] > op[2]) & (vc[None, :] < op[3])
        solid &= ~inside
        hole[inside] = k
    broken = np.zeros((nu, nv), bool)
    if top is not None:
        tops = np.array([top(x) for x in uc])
        broken = vc[None, :] >= tops[:, None]
        solid &= ~broken
    grid = w.at(us[:, None], vs[None, :], 0.0).reshape(-1, 3)

    def gi(i, j):
        return i * (nv + 1) + j
    faces = [[gi(i, j), gi(i + 1, j), gi(i + 1, j + 1), gi(i, j + 1)] for i in range(nu) for j in range(nv) if solid[i, j]]
    m = mult(grid) if mult else weather(grid, seed)
    add(p, grid, faces, paint(colour, m), slot)
    depth = reveal if thick is None else thick
    if thick is not None:
        back = w.at(us[:, None], vs[None, :], thick).reshape(-1, 3)
        faces = [[gi(i, j), gi(i, j + 1), gi(i + 1, j + 1), gi(i + 1, j)] for i in range(nu) for j in range(nv) if solid[i, j]]
        m_back = inner_mult(back) if inner_mult else (mult(back) if mult else weather(back, seed + 5)) * .82
        add(p, back, faces, paint(inner or colour, m_back), slot)
    # Exposed edges: reveals round openings, and for solid walls the ends and the broken top.
    ev, ef, ec = [], [], []

    def edge(corners_uvd, want, colour_mult):
        c = np.array(corners_uvd, np.float64)
        pts = w.at(c[:, 0], c[:, 1], c[:, 2])
        if np.dot(newell(pts), want) < 0:
            pts, c = pts[::-1], c[::-1]
        base = len(ev)
        ev.extend(pts)
        ef.append([base, base + 1, base + 2, base + 3])
        mm = (edge_mult(pts) if edge_mult else weather(pts, seed + 9)) * (1 - colour_mult * c[:, 2] / max(depth, 1e-6))
        ec.extend(mm)

    def open_side(i2, j2, j, side_v):
        """Whether the neighbour cell is open, and so the side between them shows."""
        if wrap:
            i2 %= nu
        if i2 < 0 or i2 >= nu or j2 >= nv:
            if thick is None:
                return False
            if j2 >= nv:
                return bool(top_edge)
            return bool(ends[0] if i2 < 0 else ends[1])
        if j2 < 0:
            return False
        if solid[i2, j2]:
            return False
        k = hole[i2, j2]
        if k >= 0 and len(openings[k]) > 4 and openings[k][4] is not None and side_v > openings[k][4] - 1e-6:
            return False  # inside a round head: arch_head() builds that reveal
        if k < 0 and not broken[i2, j2]:
            return False
        return k >= 0 or thick is not None
    shade = .32 if thick is None else .18
    for i in range(nu):
        for j in range(nv):
            if not solid[i, j]:
                continue
            ua, ub, va, vb = us[i], us[i + 1], vs[j], vs[j + 1]
            if open_side(i - 1, j, j, va):
                edge([(ua, va, 0), (ua, vb, 0), (ua, vb, depth), (ua, va, depth)], -w.tangent(ua), shade)
            if open_side(i + 1, j, j, va):
                edge([(ub, va, 0), (ub, vb, 0), (ub, vb, depth), (ub, va, depth)], w.tangent(ub), shade)
            if open_side(i, j - 1, j, va - 1e-3):
                edge([(ua, va, 0), (ub, va, 0), (ub, va, depth), (ua, va, depth)], -UP, shade)
            if open_side(i, j + 1, j, vb):
                edge([(ua, vb, 0), (ub, vb, 0), (ub, vb, depth), (ua, vb, depth)], UP, shade * .5)
    if ef:
        add(p, ev, ef, paint(colour, np.array(ec)), slot)
    return us, vs


def arch_head(p, w, u0, u1, spring, depth, colour, slot='CN_White', n=10, seed=0, front=True, intrados=True, back=False):
    """Closes a round-headed opening cut as a rectangle (u0..u1, up to spring + half its width): fills the
    wall face in the two corners above the arch, builds the curved reveal (the intrados), and for a wall
    open on both sides (arcades) fills the corners of its back face too."""
    r, uc = (u1 - u0) / 2, (u0 + u1) / 2
    top = spring + r
    arc = [(uc + r * math.cos(math.pi * k / n), spring + r * math.sin(math.pi * k / n)) for k in range(n + 1)]
    half = n // 2
    for on, d, out in ((front, 0.0, 1.0), (back, depth, -1.0)):
        if not on:
            continue
        for corner, seg in (((u1, top), arc[:half + 1]), ((u0, top), arc[half:])):
            for a, b in zip(seg, seg[1:]):
                xyz = w.at([corner[0], a[0], b[0]], [corner[1], a[1], b[1]], d)
                wpoly(p, w, [(corner[0], corner[1], d), (a[0], a[1], d), (b[0], b[1], d)],
                      paint(colour, weather(xyz, seed) * (.85 if out < 0 else 1.0)), slot, out=out)
    if not intrados:
        return
    verts, faces = [], []
    for k, (a, b) in enumerate(zip(arc, arc[1:])):
        quad = np.array([w.at(a[0], a[1], 0), w.at(b[0], b[1], 0), w.at(b[0], b[1], depth), w.at(a[0], a[1], depth)])
        mid = np.array([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2])
        want = w.dir((a[0] + b[0]) / 2, uc - mid[0], spring - mid[1])
        if np.dot(newell(quad), want) < 0:
            quad = quad[::-1]
        faces.append([len(verts), len(verts) + 1, len(verts) + 2, len(verts) + 3])
        verts.extend(quad)
    verts = np.array(verts)
    d = np.array([np.dot(v - w.at(uc, spring, 0), w.normal(uc)) for v in verts])
    add(p, verts, faces, paint(colour, weather(verts, seed) * (1 - .3 * np.clip(-d / max(depth, 1e-6), 0, 1))), slot)


# ---------------------------------------------------------------- windows, doors, shutters, balconies

def louvred_leaf(p, w, u0, u1, v0, v1, h0, colour, rng, slot='CN_Lacquer', hinge=None):
    """One louvred shutter leaf whose back stands h0 out from the wall face (negative: inside the reveal):
    a frame of stiles and rails, sloped slats, two iron hinges on the hinge side (u0 or u1). The slats
    form a closed sawtooth, so the leaf shows its depth and needs nothing behind it."""
    t, st = .034, .05
    paint_c = tint(colour, rng.uniform(.88, 1.0))
    d_front, d_back = -(h0 + t), -h0
    wsweep(p, w, rect_path(u0, u1, v0, v1), [(0, h0), (0, h0 + t), (-st, h0 + t), (-st, h0 + .008)], paint_c, slot)
    a, b = u0 + st, u1 - st
    lo, hi = v0 + st, v1 - st
    n = max(2, int((hi - lo) / .1))
    pitch = (hi - lo) / n
    verts, faces = [], []
    for k in range(n):
        y0 = lo + pitch * k
        front_lo = w.at([a, b], [y0, y0], [d_front + .006] * 2)
        back_hi = w.at([b, a], [y0 + pitch, y0 + pitch], [d_back - .004] * 2)
        front_hi = w.at([a, b], [y0 + pitch, y0 + pitch], [d_front + .006] * 2)
        base = len(verts)
        verts.extend([front_lo[0], front_lo[1], back_hi[0], back_hi[1]])
        faces.append([base, base + 1, base + 2, base + 3])
        base = len(verts)
        verts.extend([back_hi[1], back_hi[0], front_hi[1], front_hi[0]])
        faces.append([base, base + 1, base + 2, base + 3])
    verts = np.array(verts)
    fixed = []
    for f in faces:
        q = verts[f]
        want = w.normal((a + b) / 2) + (UP * .1 if (f[0] // 4) % 2 == 0 else -UP)
        fixed.append(f if np.dot(newell(q), want) >= 0 else f[::-1])
    p.add(verts, fixed, tint(paint_c, .82), slot, False)
    if hinge is not None:
        for v in (v0 + .16, v1 - .16):
            wbox(p, w, hinge - .035, hinge + .035, v - .018, v + .018, d_front - .006, d_back + .004, CHARCOAL, 'CN_Metal', 0)


def window(p, w, op, rng, kind='glass', reveal=.24, frame=BLACK, frame_slot='CN_Black', sill=True, surround=True,
           stone=LIMESTONE, lintel=False, shutters=None, mullion=True, transom=None, stone_slot='CN_White', seed=0, glow=None,
           length=None, clear=None):
    """A window in a wall opening op=(u0, u1, v0, v1[, spring]): frame and mullions at the back of the
    reveal, glazing over a room (dark or lamp-lit, or with a drawn curtain; or closed shutters instead), a
    projecting stone sill, an architrave (surround) or a lintel with its keystone, all three in the stone
    colour, and louvred shutters folded back on the wall. length: the wall's, whose ends bound how deep the
    room may reach (None for a drum that closes on itself); clear: how far behind the wall's face the
    building is free, where another of its parts stands nearer than a room reaches (None: nothing does).
    glow: the lamp colour the caller fixed for a lit window, which then draws none (see below)."""
    u0, u1, v0, v1 = op[:4]
    spring = op[4] if len(op) > 4 else None
    uc = (u0 + u1) / 2
    fd, bar = .07, .055
    path = rect_path(u0, u1, v0, v1) if spring is None else arch_path(u0, u1, v0, spring)
    h_front = -reveal + fd
    if kind != 'closed':
        section = [(0, h_front), (-bar, h_front), (-bar, -reveal)]
        wsweep(p, w, path, section, tint(frame, rng.uniform(.9, 1.0)), frame_slot)
        inner = outline(u0, u1, v0, v1, spring, bar)
        glass_h = -reveal + fd * .45
        # The room draws from a generator of its own, seeded from this window, and the draws of the flat card or back
        # plane it replaced are kept: houses collide, and every piece drawn after a window keeps its place.
        own = np.random.default_rng([int(seed) & 0xFFFFFFFF] + [int(round(c * 1000)) & 0xFFFFFFFF for c in w.at(uc, v0, 0.0)])
        nearer_end = min(u0, length - u1) if length is not None else math.inf
        depth = max(ROOM_MIN, min(ROOM_DEPTH, nearer_end - ROOM_CLEAR))
        if clear is not None:
            depth = min(depth, clear - reveal - ROOM_GAP)
        head = v1 if spring is None else spring + (u1 - u0) / 2
        if kind == 'lit':
            if glow is None:
                rng.uniform()  # the card's lamp colour
            rng.uniform(.55, .85)  # and its brightness
            glass = tint(BLUE_PALE if own.uniform() < .7 else WHITE_COOL, own.uniform(.85, 1))
        else:
            glass = tint(BLUE_PALE if rng.uniform() < .7 else WHITE_COOL, rng.uniform(.85, 1))
            rng.uniform(.6, 1.0)  # the back plane's tone
        wpoly(p, w, [(a, b, -glass_h) for a, b in inner], glass, 'CN_Glass')
        room(p, w, u0, u1, v0, head, reveal, depth, own, kind == 'lit')
        if kind == 'curtain':
            drape = rng.uniform(.35, .6) * (u1 - u0 - 2 * bar)
            left = rng.uniform() < .5
            ca, cb = (u0 + bar, u0 + bar + drape) if left else (u1 - bar - drape, u1 - bar)
            folds = 7
            pts = [(ca + (cb - ca) * k / folds, (.009 if k % 2 else -.009)) for k in range(folds + 1)]
            verts = []
            for (cu, dd) in pts:
                verts += [w.at(cu, v0 + bar, reveal - .012 + dd), w.at(cu, (spring or v1) - bar, reveal - .012 + dd)]
            faces = [[2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1] for k in range(folds)]
            verts = np.array(verts)
            faces = [f if np.dot(newell(verts[f]), w.normal(uc)) >= 0 else f[::-1] for f in faces]
            p.add(verts, faces, tint(WHITE_PURE, rng.uniform(.8, .95)), 'CN_Cloth', True)
        if mullion and (u1 - u0) > .7:
            top = spring if spring is not None else v1
            wbox(p, w, uc - .024, uc + .024, v0 + bar, top - (0 if spring is not None else bar), -h_front + .012, -h_front + fd * .8, frame, frame_slot, 0)
        if transom is not None and spring is None:
            tv = v0 + (v1 - v0) * transom
            wbox(p, w, u0 + bar, u1 - bar, tv - .024, tv + .024, -h_front + .012, -h_front + fd * .8, frame, frame_slot, 0)
    else:
        colour = shutters if shutters is not None else BLACK
        half = (u1 - u0) / 2
        top = v1 if spring is None else spring
        louvred_leaf(p, w, u0 + .005, u0 + half - .003, v0 + .005, top - .005, -reveal + .02, colour, rng)
        louvred_leaf(p, w, u0 + half + .003, u1 - .005, v0 + .005, top - .005, -reveal + .02, colour, rng)
        if spring is not None:
            wpoly(p, w, [(a, b, reveal - .01) for a, b in outline(u0, u1, spring - .01, spring + (u1 - u0) / 2, spring - .01)], CHARCOAL, 'CN_Black')
    dressed = tint(stone, rng.uniform(.88, 1.0))
    stone_shade = shader(dressed, lambda v: weather(v, seed + 3, damp=.12, stain=.05))
    if sill:
        stone_sill(p, w, u0 - .08, u1 + .08, v0 - .075, v0 + .012, -.065, reveal - fd, dressed, stone_slot, seed)
    if surround and not lintel:
        section = [(.13, 0), (.13, .02), (.115, .035), (0, .035), (0, 0)]
        p_path = rect_path(u0, u1, v0 + (.012 if sill else 0), v1, bottom=not sill) if spring is None else \
            arch_path(u0, u1, v0 + (.012 if sill else 0), spring, bottom=not sill)
        wsweep(p, w, p_path, section, dressed, stone_slot, closed=not sill,
               mult=lambda v: weather(v, seed + 4, damp=.1, stain=.05))
    if lintel:
        top = v1 if spring is None else spring + (u1 - u0) / 2
        wbox(p, w, u0 - .16, u1 + .16, top, top + .2, -.03, .15, dressed, stone_slot, .015, stone_shade)
        wbox(p, w, uc - .09, uc + .09, top - .03, top + .25, -.055, .15, tint(dressed, .95), stone_slot, .012)
    if shutters is not None and kind != 'closed':
        sw = .14 if surround and not lintel else .02
        leaf = (u1 - u0) / 2 + .01
        top = v1 if spring is None else spring
        louvred_leaf(p, w, u0 - sw - leaf, u0 - sw, v0 + .01, top, .012, shutters, rng, hinge=u0 - sw)
        louvred_leaf(p, w, u1 + sw, u1 + sw + leaf, v0 + .01, top, .012, shutters, rng, hinge=u1 + sw)


def room(p, w, u0, u1, v0, v1, reveal, depth, rng, lit):
    """The room seen through a window's glass (the opening u0..u1, v0..v1 of wall w, its frame's back at reveal): a
    back wall depth further in, a floor, a ceiling and two sides, all facing in, ten triangles. Half the rooms hold a
    dark piece of furniture against the back wall. Lit, the ceiling and the back wall glow as a lamp-lit room's do.
    rng is the window's own generator. The room lies inside the building's closed shell, so it changes no collision
    a player can reach."""
    ua, ub, va, vb = u0 - TUCK, u1 + TUCK, v0 - TUCK, v1 + TUCK
    d0, d1 = reveal - .01, reveal + depth  # from under the reveals' ends, so no slit shows where they meet

    def face(corners, want, colour, slot):
        c = np.asarray(corners, np.float64)
        poly(p, w.at(c[:, 0], c[:, 1], c[:, 2]), want, colour, slot)
    walls = tint(WHITE, rng.uniform(.55, .75))
    face([(ua, va, d1), (ub, va, d1), (ub, vb, d1), (ua, vb, d1)], w.normal((u0 + u1) / 2),
         tint(LIGHT_WARM, .08) if lit else walls, 'CN_Glow' if lit else 'CN_White')
    face([(ua, va, d0), (ub, va, d0), (ub, va, d1), (ua, va, d1)], UP, grey(ASH[0] * rng.uniform(.9, 1.1)), 'CN_White')
    face([(ua, vb, d0), (ub, vb, d0), (ub, vb, d1), (ua, vb, d1)], -UP,
         tint(LIGHT_WARM, .25) if lit else tint(WHITE, .6), 'CN_Glow' if lit else 'CN_White')
    for u, inward in ((ua, 1.0), (ub, -1.0)):
        face([(u, va, d0), (u, vb, d0), (u, vb, d1), (u, va, d1)], inward * w.tangent(u), tint(walls, .85), 'CN_White')
    if rng.uniform() < .5:
        # A cupboard or chest: its back and foot meet the wall and the floor, so only its front, top and ends are built.
        width = (u1 - u0) * rng.uniform(.35, .7)
        fa = u0 + (u1 - u0 - width) * rng.uniform()
        fb, top = fa + width, va + (v1 - v0) * rng.uniform(.25, .6)
        front = d1 - depth * rng.uniform(.3, .55)
        dark = tint(SLATE, rng.uniform(.45, 1.0))
        face([(fa, va, front), (fb, va, front), (fb, top, front), (fa, top, front)], w.normal((fa + fb) / 2), dark, 'CN_Black')
        face([(fa, top, front), (fb, top, front), (fb, top, d1), (fa, top, d1)], UP, tint(dark, .85), 'CN_Black')
        for u, outward in ((fa, -1.0), (fb, 1.0)):
            face([(u, va, front), (u, top, front), (u, top, d1), (u, va, d1)], outward * w.tangent(u), tint(dark, .9), 'CN_Black')


def stone_sill(p, w, u0, u1, v0, v1, d0, d1, colour, slot='CN_White', seed=0):
    """A window sill: a stone slab whose top falls toward its front edge to shed rain, so its nosing
    catches the light like a real sill's, darker where water runs off it."""
    pts = []
    for zb in (0, 1):
        for yb in (0, 1):
            for xb in (0, 1):
                u = u0 if xb == 0 else u1
                d = d0 if yb == 0 else d1
                v = v1 - (.014 if (zb and yb == 0) else 0) if zb else v0 + (.01 if yb == 0 else 0)
                pts.append(w.at(u, v, d))
    pts = np.array(pts)
    hexa(p, pts, paint(colour, weather(pts, seed, damp=.05, stain=.05) * np.where(np.arange(8) % 4 < 2, .9, 1.0)), slot)


def door(p, w, op, rng, colour=RED, reveal=.3, transom=.0, panels=(2, 3), double=False, knocker=False,
         surround=LIMESTONE, hood=False, frame=BLACK, seed=0, glazed=False, lit=False):
    """A panelled lacquer door in op=(u0, u1, v0, v1): casing, raised panels, gold lever handles and a
    knocker, a transom light over a dark or lit hall, a stone threshold, an architrave and an optional
    hood on consoles."""
    u0, u1, v0, v1 = op[:4]
    uc = (u0 + u1) / 2
    bar = .075
    section = [(0, -reveal + .09), (-bar + .015, -reveal + .09), (-bar, -reveal + .075), (-bar, -reveal)]
    wsweep(p, w, rect_path(u0, u1, v0, v1), section, tint(frame, .95), 'CN_Black')
    leaf_top = v1 - bar - (transom if transom else 0)
    leaf_front, leaf_back = reveal - .075, reveal - .02
    leaves = [(u0 + bar, uc - .004), (uc + .004, u1 - bar)] if double else [(u0 + bar, u1 - bar)]
    lacquer = tint(colour, rng.uniform(.9, 1.0))
    for la, lb in leaves:
        wbox(p, w, la, lb, v0 + .01, leaf_top, leaf_front, leaf_back, lacquer, 'CN_Lacquer', .01)
        cols, rows = panels
        if double:
            cols = 1
        st, rail_lo, rail = .11, .22, .1
        pw = (lb - la - st * (cols + 1)) / cols
        ph = (leaf_top - v0 - rail_lo - rail * rows) / rows
        for i in range(cols):
            for j in range(rows):
                pa = la + st + i * (pw + st)
                pb = v0 + rail_lo + j * (ph + rail)
                if glazed and j == rows - 1:
                    wpoly(p, w, [(pa, pb, leaf_front + .004), (pa + pw, pb, leaf_front + .004), (pa + pw, pb + ph, leaf_front + .004), (pa, pb + ph, leaf_front + .004)],
                          tint(LIGHT_WARM, .7) if lit else tint(BLUE_PALE, .9), 'CN_Glow' if lit else 'CN_Glass')
                    continue
                raised_panel(p, w, pa, pa + pw, pb, pb + ph, leaf_front, tint(lacquer, .97))
    handles = [(uc - .09, -1), (uc + .09, 1)] if double else [(u1 - bar - .1, 1)]
    for hu, s in handles:
        wbox(p, w, hu - .025, hu + .025, v0 + 1.0, v0 + 1.16, leaf_front - .012, leaf_front, GOLD, 'CN_Gold', .006)
        lever = [w.at(hu, v0 + 1.11, leaf_front - .05), w.at(hu - s * .12, v0 + 1.11, leaf_front - .055)]
        tube(p, [w.at(hu, v0 + 1.11, leaf_front - .01), lever[0]], .009, GOLD, 'CN_Gold', 6, True)
        tube(p, lever, .011, GOLD, 'CN_Gold', 6, True)
    if knocker:
        kc = w.at(uc if not double else uc - .3, v0 + 1.5, leaf_front - .03)
        n = w.normal(uc)
        ring = [kc + .065 * (math.cos(t) * w.tangent(uc) + math.sin(t) * UP) for t in np.linspace(0, 2 * math.pi, 11)]
        tube(p, ring, .011, GOLD_PALE, 'CN_Gold', 4, False)
        bevel_box(p, kc + UP * .072 + n * .012, (.014, .03, .022), GOLD, 'CN_Gold', .006, w.yaw(uc))
    if transom:
        tv = leaf_top
        wbox(p, w, u0 + bar, u1 - bar, tv, tv + .06, reveal - .09, reveal - .02, frame, 'CN_Black', 0)
        glass = [(u0 + bar, tv + .06), (u1 - bar, tv + .06), (u1 - bar, v1 - bar), (u0 + bar, v1 - bar)]
        if lit:
            wpoly(p, w, [(a, b, reveal - .05) for a, b in glass], tint(LIGHT_WARM, .75), 'CN_Glow')
        else:
            wpoly(p, w, [(a, b, reveal - .05) for a, b in glass], BLUE_PALE, 'CN_Glass')
            wpoly(p, w, [(a, b, reveal + .004) for a, b in glass], CHARCOAL, 'CN_Black')
    stone = tint(surround if surround is not None else LIMESTONE, rng.uniform(.88, 1.0))
    stone_shade = shader(stone, lambda v: weather(v, seed + 6, damp=.2, stain=.05))
    wbox(p, w, u0 - .06, u1 + .06, v0 - .06, v0 + .012, -.06, reveal - .02, tint(stone, .9), 'CN_White', .012, stone_shade)
    if surround is not None:
        section = [(.16, 0), (.16, .03), (.14, .05), (.05, .05), (.03, .035), (0, .035), (0, 0)]
        wsweep(p, w, rect_path(u0, u1, v0 + .012, v1, bottom=False), section, stone, 'CN_White', closed=False,
               mult=lambda v: weather(v, seed + 7, damp=.22, stain=.05))
    if hood:
        top = v1 + .16
        wbox(p, w, u0 - .4, u1 + .4, top + .05, top + .2, -.42, .02, stone, 'CN_White', .02, stone_shade)
        wbox(p, w, u0 - .33, u1 + .33, top, top + .05, -.34, .02, tint(stone, .94), 'CN_White', .012)
        for cu in (u0 - .26, u1 + .26):
            ca, cb = cu - .07, cu + .07
            pts = [w.at(ca, top - .5, 0.02), w.at(cb, top - .5, 0.02), w.at(ca, top - .5, -.08), w.at(cb, top - .5, -.08),
                   w.at(ca, top, 0.02), w.at(cb, top, 0.02), w.at(ca, top, -.36), w.at(cb, top, -.36)]
            hexa(p, [pts[0], pts[1], pts[2], pts[3], pts[4], pts[5], pts[6], pts[7]], stone, 'CN_White')


def raised_panel(p, w, a0, a1, b0, b1, d_face, colour, rise=.014, margin=.035):
    """A raised field on a door leaf whose face is at depth d_face: a chamfer rising from the leaf to a
    flat field, the shadow line that makes a panelled door read."""
    h = -d_face
    wsweep(p, w, rect_path(a0, a1, b0, b1), [(0, h), (-margin, h + rise)], colour, 'CN_Lacquer')
    wpoly(p, w, [(x, y, d_face - rise) for x, y in outline(a0, a1, b0, b1, None, margin)], colour, 'CN_Lacquer')


def steps_up(p, w, u0, u1, height, count, rng, run=.32, colour=IVORY, seed=0):
    """Stone steps in front of a wall up to a door sill at height: each a solid bevelled block."""
    rise = height / count
    for k in range(count):
        out = run * (count - k)
        wbox(p, w, u0 - .05 * (count - k), u1 + .05 * (count - k), k * rise, (k + 1) * rise, -out, .05,
             tint(colour, rng.uniform(.85, .97)), 'CN_White', .02, shader(colour, lambda v: weather(v, seed + k, damp=.3, rise=.35)))


def railing(p, pts, height, rng, colour=CHARCOAL, spacing=.11, slot='CN_Metal', finial=None):
    """A black iron railing along a polyline of base points: posts at the corners, a flat top rail, a
    bottom rail and square balusters; finial: a gold knob on each corner post."""
    pts = np.asarray(pts, np.float64)
    iron = tint(colour, rng.uniform(.8, 1.0))
    for a, b in zip(pts, pts[1:]):
        seg = b - a
        L = np.linalg.norm(seg[:2])
        n = max(1, int(L / spacing))
        for k in range(1, n):
            q = a + seg * k / n
            tube(p, [q + UP * .06, q + UP * (height - .03)], .008, iron, slot, 4, False)
        tube(p, [a + UP * .06, b + UP * .06], .014, iron, slot, 4, False)
        tube(p, [a + UP * (height - .015), b + UP * (height - .015)], .024, iron, slot, 4, True)
        tube(p, [a + UP * (height - .12), b + UP * (height - .12)], .01, iron, slot, 4, False)
    for q in pts:
        tube(p, [q, q + UP * height], .022, iron, slot, 6, True)
        if finial is not None:
            blob(p, q + UP * (height + .035), .035, finial, 'CN_Gold', 1, .04, 3)


def balcony(p, w, u0, u1, v_floor, depth, rng, stone=LIMESTONE, iron=CHARCOAL, seed=0, finial=None):
    """A stone balcony slab on three moulded consoles, with a black iron railing."""
    st = tint(stone, rng.uniform(.88, .97))
    wbox(p, w, u0, u1, v_floor - .17, v_floor, -depth, .1, st, 'CN_White', .025, shader(st, lambda v: weather(v, seed, damp=0, stain=.06)))
    wbox(p, w, u0 + .04, u1 - .04, v_floor - .23, v_floor - .17, -depth + .05, .05, tint(st, .9), 'CN_White', .015)
    for cu in (u0 + .22, u1 - .22):
        top, bot = v_floor - .23, v_floor - .62
        ca, cb = cu - .08, cu + .08
        pts = [w.at(ca, bot, .02), w.at(cb, bot, .02), w.at(ca, bot, -.1), w.at(cb, bot, -.1),
               w.at(ca, top, .02), w.at(cb, top, .02), w.at(ca, top, -depth + .12), w.at(cb, top, -depth + .12)]
        hexa(p, pts, tint(st, .93), 'CN_White')
    inset = .05
    base = [w.at(u0 + inset, v_floor, 0.0), w.at(u0 + inset, v_floor, -depth + inset), w.at(u1 - inset, v_floor, -depth + inset), w.at(u1 - inset, v_floor, 0.0)]
    railing(p, base, 1.0, rng, iron, finial=finial)


# ---------------------------------------------------------------- building pieces

def quoin_block(p, cx, cy, sx, sy, ax, ay, z0, z1, colour, seed, pr=.03, c=.026):
    """One dressed corner stone wrapping a building corner (cx, cy) whose faces point sx along x and sy
    along y: it runs ax back along the y-facing wall and ay back along the x-facing wall and stands pr
    proud of both. Only its visible faces are built, with chamfers on every edge that shows, so the
    joints between courses read as V grooves."""
    def P(a, b, z):
        return (cx + sx * a, cy + sy * b, z)
    X, Y = np.array([sx, 0., 0.]), np.array([0., sy, 0.])
    za, zb = z0 + c, z1 - c
    faces = [
        ([P(-ax, pr, za), P(pr - c, pr, za), P(pr - c, pr, zb), P(-ax, pr, zb)], Y),
        ([P(pr - c, pr, za), P(pr, pr - c, za), P(pr, pr - c, zb), P(pr - c, pr, zb)], X + Y),
        ([P(pr, pr - c, za), P(pr, -ay, za), P(pr, -ay, zb), P(pr, pr - c, zb)], X),
        ([P(-ax, pr, zb), P(pr - c, pr, zb), P(pr - c, pr - c, z1), P(-ax, pr - c, z1)], Y + UP),
        ([P(pr - c, pr, zb), P(pr, pr - c, zb), P(pr - c, pr - c, z1)], X + Y + UP),
        ([P(pr, pr - c, zb), P(pr, -ay, zb), P(pr - c, -ay, z1), P(pr - c, pr - c, z1)], X + UP),
        ([P(-ax, pr, za), P(pr - c, pr, za), P(pr - c, pr - c, z0), P(-ax, pr - c, z0)], Y - UP),
        ([P(pr - c, pr, za), P(pr, pr - c, za), P(pr - c, pr - c, z0)], X + Y - UP),
        ([P(pr, pr - c, za), P(pr, -ay, za), P(pr - c, -ay, z0), P(pr - c, pr - c, z0)], X - UP),
        ([P(-ax, 0, z0), P(-ax, pr - c, z0), P(-ax, pr, za), P(-ax, pr, zb), P(-ax, pr - c, z1), P(-ax, 0, z1)], -X),
        ([P(0, -ay, z0), P(pr - c, -ay, z0), P(pr, -ay, za), P(pr, -ay, zb), P(pr - c, -ay, z1), P(0, -ay, z1)], -Y),
        # Flat tops and bottoms: the ledges where a long stone overhangs a short one.
        ([P(-ax, 0, z1), P(0, 0, z1), P(0, pr - c, z1), P(-ax, pr - c, z1)], UP),
        ([P(0, -ay, z1), P(pr - c, -ay, z1), P(pr - c, pr - c, z1), P(0, pr - c, z1)], UP),
        ([P(-ax, 0, z0), P(0, 0, z0), P(0, pr - c, z0), P(-ax, pr - c, z0)], -UP),
        ([P(0, -ay, z0), P(pr - c, -ay, z0), P(pr - c, pr - c, z0), P(0, pr - c, z0)], -UP),
    ]
    verts, out = [], []
    for pts, want in faces:
        pts = np.array(pts, np.float64)
        if np.dot(newell(pts), want) < 0:
            pts = pts[::-1]
        out.append(list(range(len(verts), len(verts) + len(pts))))
        verts.extend(pts)
    verts = np.array(verts)
    p.add(verts, out, paint(colour, weather(verts, seed, damp=.3, stain=.04)), 'CN_White', False)


def quoins(p, x0, x1, y0, y1, z0, z1, rng, colour=LIMESTONE, long=.56, short=.3, course=.46, seed=0, skip=(), tops=None):
    """Dressed-stone quoins up each corner, alternating long and short faces course by course. skip:
    corner indices left bare; tops: per-corner heights where a ruined corner stops."""
    n = max(1, int(round((z1 - z0) / course)))
    hgt = (z1 - z0) / n
    for ci, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        if ci in skip:
            continue
        cx, cy = (x1 if sx > 0 else x0), (y1 if sy > 0 else y0)
        for k in range(n):
            if tops is not None and z0 + hgt * (k + 1) > tops[ci] + 1e-6:
                break
            ax, ay = (long, short) if (k + ci) % 2 else (short, long)
            quoin_block(p, cx, cy, sx, sy, ax, ay, z0 + hgt * k + .003, z0 + hgt * (k + 1) - .003,
                        tint(colour, rng.uniform(.84, .98)), seed + k)


def house_walls(x0, x1, y0, y1):
    """The four walls of a rectangular building, keyed front (+x), right (+y), back, left."""
    return {'front': (Wall((x1, y0, 0), (1, 0, 0)), y1 - y0), 'right': (Wall((x1, y1, 0), (0, 1, 0)), x1 - x0),
            'back': (Wall((x0, y1, 0), (-1, 0, 0)), y1 - y0), 'left': (Wall((x0, y0, 0), (0, -1, 0)), x1 - x0)}


def gable_end(p, w, length, ze, lift, rise, colour, seed, slot='CN_White'):
    """The triangle of plaster closing a gable wall from the cornice up under the roof slabs."""
    pts = [(0, ze, 0), (length, ze, 0), (length, ze + lift, 0), (length / 2, ze + lift + rise, 0), (0, ze + lift, 0)]
    xyz = w.at(np.array(pts)[:, 0], np.array(pts)[:, 1], 0)
    wpoly(p, w, pts, paint(colour, weather(xyz, seed, damp=0)), slot)


def barrel_tiles(p, origin, down, along, length_down, a0, a1, rng, pitch=.33, course=.46, r=.108, miss=0.0, slip=0.0,
                 colour=RED, eave=.05, top=0.0, holes=None):
    """Mediterranean cover tiles on a roof plane: half-round tiles in rows running down the slope, each
    course lapping the one below, so the roof shows its courses and the shadowed channels between rows.
    origin: the top edge of the plane (s 0, a 0); down, along: unit vectors in it (normal = down x along
    points up out of the roof); s runs to length_down at the eave, a from a0 to a1. miss and slip break
    and shift tiles (ruins); holes(s, a) -> True drops a tile."""
    origin, down, along = (np.asarray(x, np.float64) for x in (origin, down, along))
    normal = np.cross(down, along)
    normal /= np.linalg.norm(normal)
    prof = np.array([(-1, 0), (-.62, .74), (.62, .74), (1, 0)])
    rows = max(1, int((a1 - a0) / pitch))
    pa = (a1 - a0) / rows
    lap = .09
    sv, sf, sc, bv, bf, bc = [], [], [], [], [], []
    for j in range(rows):
        ac = a0 + pa * (j + .5)
        s_lo = length_down + eave
        k = 0
        while s_lo > top + .02:
            s_hi = max(top, s_lo - course - lap)
            k += 1
            this_lo = s_lo
            s_lo -= course
            if miss and rng.uniform() < miss:
                continue
            if holes is not None and holes(this_lo, ac):
                continue
            phi = rng.normal(0, .012) + (rng.normal(0, .15) if slip and rng.uniform() < slip else 0)
            dd = math.cos(phi) * down + math.sin(phi) * along
            aa = -math.sin(phi) * down + math.cos(phi) * along
            jit = ac + rng.normal(0, .008)
            scale = rng.uniform(.95, 1.05) * r
            lift = .024 + rng.uniform(-.003, .004)
            centre = origin + along * jit
            ring_lo = [centre + dd * this_lo + aa * (x * scale) + normal * (y * scale + (lift if y > 0 else 0)) for x, y in prof]
            ring_hi = [centre + dd * s_hi + aa * (x * scale * .88) + normal * (y * scale * .88 + .002) for x, y in prof]
            tone = rng.uniform(.72, 1.0) * (.88 if k <= 1 else 1.0)
            c = tint(RED_DEEP, rng.uniform(.8, 1.0)) if rng.uniform() < .07 else tint(colour, tone)
            base = len(sv)
            sv.extend(ring_hi + ring_lo)
            for q in range(3):
                sf.append([base + q, base + 4 + q, base + 4 + q + 1, base + q + 1])
            sc.extend([tint(c, .92)] * 4 + [c] * 4)
            base = len(bv)
            bv.extend(ring_lo[::-1])
            bf.append([base, base + 1, base + 2, base + 3])
            bc.extend([tint(c, .7)] * 4)
    if sf:
        p.add(np.array(sv), sf, np.array(sc), 'CN_Red', True)
        p.add(np.array(bv), bf, np.array(bc), 'CN_Red', False)


def ridge_caps(p, a, b, slope, rng, colour=RED, w=.17, length=.42):
    """Ridge capping along a ridge from a to b (both on the slab tops' meeting line): larger half-round
    tiles, each lapping the next, closed at the first one's open end."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    axis = b - a
    L = np.linalg.norm(axis)
    axis /= L
    side = np.cross(UP, axis)
    prof = [(-w, -w * slope + .065), (-.68 * w, .1), (0, .158), (.68 * w, .1), (w, -w * slope + .065)]
    n = max(1, int(math.ceil(L / (length - .06))))
    step = L / n
    verts, faces, cols, ends, end_f, end_c = [], [], [], [], [], []
    for k in range(n):
        s0, s1 = k * step - .02, (k + 1) * step + .04
        s0, s1 = max(0, s0), min(L, s1)
        c = tint(colour, rng.uniform(.7, .95))
        lift = .012 * (k % 2)
        ring_a = [a + axis * s0 + side * x + UP * (z + lift) for x, z in prof]
        ring_b = [a + axis * s1 + side * x * 1.04 + UP * (z * 1.04 + lift + .01) for x, z in prof]
        base = len(verts)
        verts.extend(ring_a + ring_b)
        for q in range(4):
            faces.append([base + q, base + q + 1, base + 5 + q + 1, base + 5 + q])
        cols.extend([c] * 10)
        for ring in ([ring_a, ring_b] if k == 0 else [ring_b]):
            base = len(ends)
            ends.extend(ring)
            end_f.append(list(range(base, base + 5)))
            end_c.extend([tint(c, .75)] * 5)
    verts = np.array(verts)
    faces = [f if np.dot(newell(verts[f]), UP) >= 0 else f[::-1] for f in faces]
    p.add(verts, faces, np.array(cols), 'CN_Red', True)
    ends = np.array(ends)
    end_f = [f if np.dot(newell(ends[f]), axis if i else -axis) >= 0 else f[::-1] for i, f in enumerate(end_f)]
    p.add(ends, end_f, np.array(end_c), 'CN_Red', False)


def gable_roof(p, x0, x1, y0, y1, ze, rise, rng, ov=.42, ovg=.3, slab=.14, lift=.18, miss=0.0, slip=0.0, slopes=(1, -1),
               ridge=True, holes=None, pitch=.33, course=.46):
    """A red barrel-tile roof over x0..x1 by y0..y1 with its ridge along y: two slabs with real thickness
    and overhang, tile courses on both, ridge caps. Eaves at ze (the cornice top); the slabs
    rest lift above it. Returns (ridge top z, slope) for chimneys and gables."""
    xc, hd = (x0 + x1) / 2, (x1 - x0) / 2
    k = rise / hd
    th = math.atan(k)
    cs, sn = math.cos(th), math.sin(th)
    zr = ze + lift + rise
    Y0, Y1 = y0 - ovg, y1 + ovg
    for side in slopes:
        xe = xc + side * (hd + ov)
        zedge = zr - (hd + ov) * k
        nrm = np.array([side * sn, 0, cs])
        pts = []
        for zb in (0, 1):
            for yb in (0, 1):
                for xb in (0, 1):
                    q = np.array([xc if xb == 0 else xe, Y0 if yb == 0 else Y1, zr if xb == 0 else zedge])
                    pts.append(q if zb else q - slab * nrm)
        hexa(p, pts, tint(RED_DEEP, .55), 'CN_Red')
        down = np.array([side * cs, 0, -sn])
        along = np.array([0, side, 0.])
        origin = np.array([xc, 0, zr])
        barrel_tiles(p, origin, down, along, (hd + ov) / cs, -Y1 if side < 0 else Y0, -Y0 if side < 0 else Y1, rng,
                     pitch=pitch, course=course, miss=miss, slip=slip, holes=holes)
    if ridge:
        ridge_caps(p, (xc, Y0, zr), (xc, Y1, zr), k, rng)
    return zr, k


def chimney(p, x, y, z0, z1, rng, w=.6, d=.48, seed=0):
    """A plastered chimney stack with a moulded collar, a pierced cap of four piers under a small tiled
    saddle, and soot toward its mouth."""
    white = tint(WHITE_PURE, rng.uniform(.9, 1.0))
    soot = shader(white, lambda v: weather(v, seed, damp=0, stain=.06) * (1 - .55 * np.clip((v[:, 2] - z1 + 1.1) / 1.1, 0, 1)))
    # The stack runs up through its collar; its top is the sooted flue mouth seen between the cap's piers.
    bevel_box(p, (x, y, (z0 + z1 - .46) / 2), (w / 2, d / 2, (z1 - .46 - z0) / 2), white, 'CN_Plaster', .03, shade=soot)
    pts, dirs = rect_ring(x, y, w / 2, d / 2, 2.0)
    pts[:, 2] = z1 - .55
    sweep3(p, pts, dirs, UP, [(0, 0), (.04, .01), (.05, .06), (.03, .09), (0, .09)], tint(white, .8), 'CN_White')
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(p, (x + sx * (w / 2 - .07), y + sy * (d / 2 - .07), z1 - .3), (.07, .07, .16), tint(white, .62), 'CN_White', .015)
    bevel_box(p, (x, y, z1 - .1), (w / 2 + .06, d / 2 + .06, .04), tint(white, .55), 'CN_White', .015)
    for s in (-1, 1):
        pts = []
        for zb in (0, 1):
            for yb in (0, 1):
                for xb in (0, 1):
                    xx = x if xb == 0 else x + s * (w / 2 + .1)
                    zz = z1 + .1 if xb == 0 else z1 - .04
                    pts.append((xx, y + (-1 if yb == 0 else 1) * (d / 2 + .1), zz + (.035 if zb else 0)))
        hexa(p, pts, tint(RED, rng.uniform(.6, .85)), 'CN_Red')


def parapet(p, x0, x1, y0, y1, z0, height, rng, colour=WHITE_PURE, t=.24, seed=0, deck=ASH):
    """A flat roof terrace: a stone deck and a plastered parapet with a moulded limestone coping and two
    gold rain spouts."""
    white = tint(colour, rng.uniform(.9, 1.0))
    for (cx, cy, hx, hy) in (((x0 + x1) / 2, y1 - t / 2, (x1 - x0) / 2, t / 2), ((x0 + x1) / 2, y0 + t / 2, (x1 - x0) / 2, t / 2),
                             (x1 - t / 2, (y0 + y1) / 2, t / 2, (y1 - y0) / 2 - t), (x0 + t / 2, (y0 + y1) / 2, t / 2, (y1 - y0) / 2 - t)):
        bevel_box(p, (cx, cy, z0 + height / 2), (hx, hy, height / 2), white, 'CN_Plaster', .02,
                  shade=shader(white, lambda v: weather(v, seed, damp=0, stain=.07)))
    pts, dirs = rect_ring((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 + .03, (y1 - y0) / 2 + .03, 1.5)
    pts[:, 2] = z0 + height
    sweep3(p, pts, dirs, UP, [(0, -.04), (.03, -.04), (.03, .04), (0, .07), (-t - .06, .07), (-t - .06, -.02)], tint(LIMESTONE, .92), 'CN_White')
    p.add([(x0 + t, y0 + t, z0 + .02), (x1 - t, y0 + t, z0 + .02), (x1 - t, y1 - t, z0 + .02), (x0 + t, y1 - t, z0 + .02)], [[0, 1, 2, 3]],
          paint(deck, [.95, .85, 1.0, .9]), 'CN_White')
    for sy in (y0 + 1.2, y1 - 1.2):
        tube(p, [(x0 + .1, sy, z0 + .12), (x0 - .3, sy, z0 + .07)], .045, GOLD_DEEP, 'CN_Gold', 8, True)


# ---------------------------------------------------------------- houses

def plan_windows(length, bays, sill, head, width, door_bay=None, door=None, margin=0.0):
    """Openings for a storey: windows centred in equal bays between end piers of width margin (wide
    enough that open shutters clear the quoins), one bay given to a door."""
    out = []
    for b in range(bays):
        c = margin + (length - 2 * margin) * (b + .5) / bays
        if b == door_bay and door is not None:
            dw, dv0, dv1, kind = door
            out.append((kind, (c - dw / 2, c + dw / 2, dv0, dv1)))
        else:
            out.append(('win', (c - width / 2, c + width / 2, sill, head)))
    return out


def fit(p, w, ops, rng, style, seed, length=None, clear=None):
    """Fills a wall's openings with windows, doors and French doors in the house's style. length: the wall's,
    which bounds the rooms behind its windows; clear(op): how deep the building is free behind that opening,
    or None (window())."""
    for k, (kind, op) in enumerate(ops):
        s = seed + 13 * k
        free = clear(op) if clear is not None else None
        if kind == 'win':
            roll = rng.uniform()
            state = 'lit' if roll < style.get('lit', .18) else 'curtain' if roll < .36 else 'closed' if roll < .44 else 'glass'
            shut = style.get('shutters') if rng.uniform() < style.get('shutter_rate', .6) else None
            window(p, w, op, rng, state, style.get('reveal', .24), style['frame'], style.get('frame_slot', 'CN_Black'),
                   surround=not style.get('lintel', False), stone=style['stone'], lintel=style.get('lintel', False),
                   shutters=shut, transom=.68 if (op[3] - op[2]) > 1.35 else None, seed=s, length=length, clear=free)
        elif kind == 'french':
            window(p, w, op, rng, 'lit' if rng.uniform() < .3 else 'glass', style.get('reveal', .24), style['frame'],
                   style.get('frame_slot', 'CN_Black'), sill=False, stone=style['stone'], shutters=style.get('shutters'),
                   transom=.8, seed=s, length=length, clear=free)
        elif kind == 'door':
            door(p, w, op, rng, style['door'], .3, transom=.42 if (op[3] - op[2]) > 2.6 else 0.0, knocker=True,
                 surround=style['stone'], hood=style.get('hood', False), seed=s, lit=rng.uniform() < .4)
        elif kind == 'backdoor':
            door(p, w, op, rng, BLACK, .26, panels=(2, 2), surround=style['stone'], seed=s)


def finish(p):
    """Drops material slots no face uses (which fittings a house gets is drawn from its seed, and an
    unused slot imports as a stray material in Unreal), and refuses a building over its README ceiling
    (check.py refuses one well under it)."""
    used = sorted(set(p.m))
    remap = {old: new for new, old in enumerate(used)}
    p.slots = [p.slots[i] for i in used]
    p.m = [remap[i] for i in p.m]
    lo, hi = p.bounds()
    limit = CEILING.get(p.name)
    if limit is not None and hi[2] > limit + 1e-6:
        raise ValueError('%s is %.2f m tall, over its %.1f m ceiling' % (p.name, hi[2], limit))
    return p


# Every slot a building may use; finish() keeps the ones it does.
ALL_SLOTS = ('CN_White', 'CN_Plaster', 'CN_Black', 'CN_Lacquer', 'CN_Metal', 'CN_Gold', 'CN_Red', 'CN_Blue', 'CN_Cloth', 'CN_Leaf',
             'CN_Glow', 'CN_Glass', 'CN_Water')


def house(k):
    """The Commons' four house types (README sizes): 0 a two-storey house with a balcony, 1 a tower house
    with an observatory dome, 2 a long house over a front arcade, 3 a corner shop with a roof terrace and
    pergola. Each draws its own colours and window states from its seed."""
    p = Part('SM_CN_House%d' % k, ALL_SLOTS)
    rng = np.random.default_rng(3100 + k)
    (_house0, _house1, _house2, _house3)[k](p, rng, 3100 + k)
    return finish(p)


def _house0(p, rng, seed):
    x0, x1, y0, y1 = -3.0, 2.6, -4.15, 4.15
    plinth, floor1, eave_wall = .45, 3.95, 6.95
    style = {'frame': BLACK, 'stone': LIMESTONE, 'shutters': BLUE, 'door': RED, 'shutter_rate': .7}
    walls = house_walls(x0, x1, y0, y1)
    L = y1 - y0
    front = plan_windows(L, 3, 1.35, 2.95, 1.0, 1, (1.2, plinth, 3.35, 'door'), .65) + \
        plan_windows(L, 3, 4.75, 6.25, .95, 1, (1.2, floor1, 6.3, 'french'), .65)
    back = plan_windows(L, 3, 1.35, 2.85, .9, 0, (1.0, plinth, 2.75, 'backdoor'), .65) + plan_windows(L, 3, 4.75, 6.15, .9, margin=.65)
    side = plan_windows(x1 - x0, 1, 1.4, 2.9, .9) + plan_windows(x1 - x0, 1, 4.8, 6.2, .9)
    plan = {'front': front, 'back': back, 'right': side, 'left': side}
    rise = 1.6
    ze = eave_wall + CORNICE[-1][1]
    _shell(p, walls, plan, rng, style, seed, WHITE_PURE, eave_wall, ze, rise, plinth, (floor1 - .2,))
    quoins(p, x0, x1, y0, y1, plinth, eave_wall, rng, seed=seed)
    w, _ = walls['front']
    balcony(p, w, L / 2 - 1.3, L / 2 + 1.3, floor1, .8, rng, seed=seed)
    steps_up(p, w, L / 2 - .8, L / 2 + .8, plinth, 2, rng, seed=seed)
    zr, slope = gable_roof(p, x0, x1, y0, y1, ze, rise, rng)
    chimney(p, x0 + 1.0, y0 + 1.1, zr - 1.2, zr + 1.05, rng, seed=seed)


def _shell(p, walls, plan, rng, style, seed, colour, eave_wall, ze, rise, plinth, strings, gables=True, flat=False):
    """Rendered walls (CN_Plaster) with their openings filled, the limestone base course, string courses
    and eaves cornice; and, for a pitched roof, the gable triangles. Front and back walls run up behind
    the cornice into the roof so no slit opens under the slabs."""
    lift = .18
    for name, (w, L) in walls.items():
        ops = plan.get(name, [])
        top = eave_wall + .02 if (flat or name in ('right', 'left')) else ze + lift - .02
        wall_cells(p, w, L, top, colour, slot='CN_Plaster', openings=[op for _, op in ops], reveal=style.get('reveal', .24),
                   seed=seed + len(name))
        fit(p, w, ops, rng, style, seed + 7 * len(name), L)
        if gables and not flat and name in ('right', 'left'):
            gable_end(p, w, L, ze, lift - .05, rise, colour, seed, slot='CN_Plaster')
    x0 = min(w.o[0] for w, _ in walls.values())
    x1 = max(w.o[0] for w, _ in walls.values())
    y0 = min(w.o[1] for w, _ in walls.values())
    y1 = max(w.o[1] for w, _ in walls.values())
    stone = style['stone']
    ring_moulding(p, x0, x1, y0, y1, 0.0, [(0, 0), (.07, 0), (.07, plinth - .06), (.04, plinth), (0, plinth)], tint(stone, .86), seed=seed,
                  mult=lambda v: weather(v, seed + 1, damp=.32, rise=.3))
    for z in strings:
        ring_moulding(p, x0, x1, y0, y1, z, STRING, tint(stone, .93), seed=seed + 2)
    ring_moulding(p, x0, x1, y0, y1, eave_wall, CORNICE, tint(stone, .95), seed=seed + 3)




# ---------------------------------------------------------------- more pieces: domes, columns, paving, foliage, awnings

def revolve(p, profile, colour, slot, sides=24, c=(0, 0, 0), smooth=True, arc=2 * math.pi, start=0.0, mult=None):
    """toolkit.lathe with per-vertex colour (glazed tiles, weathered stone): revolves [(radius, z)] listed
    bottom to top around z through c."""
    profile = np.asarray(profile, np.float64)
    full = arc >= 2 * math.pi - 1e-6
    n = sides if full else sides + 1
    ang = start + np.linspace(0, arc, n, endpoint=not full)
    verts = np.concatenate([np.stack([np.cos(ang) * r, np.sin(ang) * r, np.full(n, z)], 1) for r, z in profile]) + np.asarray(c, np.float64)
    faces = []
    for i in range(len(profile) - 1):
        for j in range(sides):
            k = (j + 1) % n
            faces.append([i * n + j, i * n + k, (i + 1) * n + k, (i + 1) * n + j])
    return p.add(verts, faces, paint(colour, mult(verts) if mult else np.ones(len(verts))), slot, smooth)


def tuscan(p, x, y, z0, h, r, rng, colour=LIMESTONE, sides=12, seed=0):
    """A Tuscan column h tall: square plinth, torus base, a shaft that tapers with a little entasis,
    echinus and abacus."""
    st = tint(colour, rng.uniform(.86, .96))
    age = lambda v: weather(v, seed, damp=.3, rise=.5, stain=.05)
    bevel_box(p, (x, y, z0 + .07), (r * 1.42, r * 1.42, .07), st, 'CN_White', .015, shade=shader(st, age))
    revolve(p, [(r * 1.3, z0 + .14), (r * 1.33, z0 + .19), (r * 1.2, z0 + .24), (r * 1.04, z0 + .28)], st, 'CN_White', sides, (x, y, 0), mult=age)
    top = z0 + h - .3
    prof = [(r * (1 - .12 * t + .035 * math.sin(math.pi * t)), z0 + .28 + (top - z0 - .28) * t) for t in np.linspace(0, 1, 5)]
    revolve(p, prof, st, 'CN_White', sides, (x, y, 0), mult=age)
    revolve(p, [(r * .88, top), (r * .93, top + .05), (r * 1.22, top + .15), (r * 1.3, top + .19)], st, 'CN_White', sides, (x, y, 0), mult=age)
    bevel_box(p, (x, y, top + .245), (r * 1.45, r * 1.45, .055), tint(st, .97), 'CN_White', .012)


def paving(p, x0, x1, y0, y1, z, size, rng, colour=WHITE, slot='CN_White', joint=.012, seed=0, under=SLATE):
    """Stone paving: slabs in running courses with their own tones, over a dark bed that shows in the
    joints."""
    verts, faces, cols = [], [], []
    nx = max(1, int(round((x1 - x0) / size)))
    sx = (x1 - x0) / nx
    row = 0
    x = x0
    while x < x1 - 1e-6:
        x2 = min(x1, x + sx)
        off = (row % 2) * size * .5
        y = y0
        k = 0
        while y < y1 - 1e-6:
            length = size * rng.uniform(.8, 1.3) if k else size * rng.uniform(.3, .8) + off * 0
            y2 = min(y1, y + length)
            if y1 - y2 < size * .25:
                y2 = y1
            a = [x + joint / 2, y + joint / 2, x2 - joint / 2, y2 - joint / 2]
            base = len(verts)
            dz = rng.uniform(-.004, .004)
            verts += [(a[0], a[1], z + dz), (a[2], a[1], z + dz), (a[2], a[3], z + dz), (a[0], a[3], z + dz)]
            faces.append([base, base + 1, base + 2, base + 3])
            tone = rng.uniform(.8, 1.0)
            cols += [tint(colour, tone * rng.uniform(.95, 1.0)) for _ in range(4)]
            y = y2
            k += 1
        x = x2
        row += 1
    p.add(np.array(verts), faces, np.array(cols), slot, False)
    p.add([(x0, y0, z - .006), (x1, y0, z - .006), (x1, y1, z - .006), (x0, y1, z - .006)], [[0, 1, 2, 3]], under, slot, False)


def leaf_cloud(p, centres, radius, count, rng, colours, size=(.07, .13), slot='CN_Leaf', droop=.3, up_bias=.4, tones=(.75, 1.0)):
    """Foliage as single leaves: small blades folded along their vein, scattered on clump shells around
    centres (a two-sided material, so one face each). colours: palette leaf colours drawn at random."""
    centres = np.atleast_2d(np.asarray(centres, np.float64))
    r = np.broadcast_to(np.asarray(radius, np.float64), (len(centres), 3)) if np.ndim(radius) else np.full((len(centres), 3), float(radius))
    pick = rng.integers(0, len(centres), count)
    d = rng.normal(0, 1, (count, 3))
    d[:, 2] = np.abs(d[:, 2]) * up_bias + d[:, 2] * (1 - up_bias)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    base = centres[pick] + d * r[pick] * (.55 + .45 * rng.uniform(0, 1, (count, 1)) ** .5)
    side = np.cross(d, UP)
    sl = np.linalg.norm(side, axis=1, keepdims=True)
    side = np.where(sl > 1e-3, side / np.maximum(sl, 1e-6), np.array([1., 0, 0]))
    up = np.cross(side, d)
    tw = rng.uniform(-math.pi, math.pi, (count, 1))
    along = np.cos(tw) * up + np.sin(tw) * side + d * .4 - UP * droop
    along /= np.linalg.norm(along, axis=1, keepdims=True)
    across = np.cross(d, along)
    across /= np.maximum(np.linalg.norm(across, axis=1, keepdims=True), 1e-6)
    L = rng.uniform(*size, (count, 1))
    W = L * rng.uniform(.3, .42, (count, 1))
    tip = base + along * L
    mid = base + along * L * .45 - d * W * .3
    verts = np.stack([base, mid - across * W, tip, mid + across * W], 1).reshape(-1, 3)
    n = np.arange(count) * 4
    faces = np.concatenate([np.stack([n, n + 1, n + 2], 1), np.stack([n, n + 2, n + 3], 1)]).tolist()
    cols = []
    for i in range(count):
        c = colours[rng.integers(0, len(colours))]
        shade = rng.uniform(*tones) * (.8 + .2 * np.clip(d[i, 2] * .5 + .5, 0, 1))
        cols += [tint(c, shade * .85), tint(c, shade), tint(c, shade), tint(c, shade)]
    p.add(verts, faces, np.array(cols), slot, False)


def awning(p, w, u0, u1, v_top, v_front, depth, rng, stripes=8, colours=(RED, WHITE_PURE), valance=.2, iron=CHARCOAL):
    """A striped canvas awning on iron arms: stripes sagging from the wall to a front bar, a scalloped
    valance, both faces built (its underside is what passers-by see)."""
    rows = 5
    for k in range(stripes):
        ua, ub = u0 + (u1 - u0) * k / stripes, u0 + (u1 - u0) * (k + 1) / stripes
        c = tint(colours[k % len(colours)], rng.uniform(.85, .98))
        grid = []
        for i in range(rows + 1):
            t = i / rows
            for u in (ua, (ua + ub) / 2, ub):
                sag = .05 * math.sin(math.pi * t) + (.012 if u == (ua + ub) / 2 else 0) * math.sin(math.pi * t)
                grid.append(w.at(u, v_top + (v_front - v_top) * t - sag, -depth * t - .02))
        grid = np.array(grid)
        faces = [[i * 3 + j, i * 3 + j + 1, (i + 1) * 3 + j + 1, (i + 1) * 3 + j] for i in range(rows) for j in range(2)]
        want = w.normal((ua + ub) / 2) * .4 + UP
        faces = [f if np.dot(newell(grid[f]), want) >= 0 else f[::-1] for f in faces]
        p.add(grid, faces, c, 'CN_Cloth', True)
        under = grid - UP * .004
        p.add(under, [f[::-1] for f in faces], tint(c, .8), 'CN_Cloth', True)
        # Valance: straight top along the front bar, scalloped bottom.
        top_a, top_b = grid[rows * 3], grid[rows * 3 + 2]
        pts = [top_a, top_b]
        for q in range(5):
            t = q / 4
            uu = ub + (ua - ub) * t
            drop = valance * (.75 + .25 * math.sin(math.pi * t))
            pts.append(w.at(uu, v_front - drop, -depth - .02))
        pts = np.array(pts)
        poly(p, pts, w.normal((ua + ub) / 2), c, 'CN_Cloth')
        poly(p, pts - w.normal((ua + ub) / 2) * .004, -w.normal((ua + ub) / 2), tint(c, .8), 'CN_Cloth')
    tube(p, [w.at(u0 - .03, v_front + .01, -depth - .02), w.at(u1 + .03, v_front + .01, -depth - .02)], .018, iron, 'CN_Metal', 6, True)
    for u in (u0 + .04, u1 - .04):
        tube(p, [w.at(u, v_top - .75, .02), w.at(u, v_front - .02, -depth + .02)], .016, iron, 'CN_Metal', 6, True)
        wbox(p, w, u - .05, u + .05, v_top - .82, v_top - .66, -.012, .01, iron, 'CN_Metal', 0)
    tube(p, [w.at(u0 - .05, v_top + .02, -.04), w.at(u1 + .05, v_top + .02, -.04)], .03, iron, 'CN_Metal', 6, True)


def observatory(p, cx, cy, z0, rng, r=1.3, drum=1.2, seed=0):
    """A rooftop observatory (entered by a stair from the room below): a plastered drum with two small
    windows, a moulded limestone cornice, a dome of light-blue glazed tile on gold ribs with its observing
    slit open toward +x, a gold telescope looking out of it and a gold finial."""
    white = tint(WHITE_PURE, rng.uniform(.92, 1.0))
    w = Wall((cx, cy, z0), r=r, a0=math.pi)
    ops = [(math.pi * r * f - .25, math.pi * r * f + .25, .45, .95) for f in (.5, 1.5)]
    wall_cells(p, w, 2 * math.pi * r, drum + .02, white, slot='CN_Plaster', openings=ops, reveal=.16, cell=.55, seed=seed, wrap=True)
    for op in ops:
        window(p, w, op, rng, 'lit' if rng.uniform() < .5 else 'glass', .16, GOLD_PALE, 'CN_Gold', surround=False, mullion=False, seed=seed)
    zc = z0 + drum
    revolve(p, [(r, zc - .02), (r + .05, zc + .02), (r + .08, zc + .1), (r + .15, zc + .17), (r + .15, zc + .24), (r - .02, zc + .24)],
            tint(LIMESTONE, .92), 'CN_White', 32, (cx, cy, 0), smooth=False, mult=lambda v: weather(v, seed, damp=0, stain=.05))
    zd = zc + .24
    R = r + .04
    slit = math.radians(26)
    rings = [(R * math.cos(t), zd + R * .92 * math.sin(t)) for t in np.linspace(0, math.radians(84), 9)]

    def glaze(v):
        k = np.floor(np.arctan2(v[:, 1] - cy, v[:, 0] - cx) / (2 * math.pi) * 64) + np.floor((v[:, 2] - zd) / .16) * 7
        return .82 + .16 * np.sin(k * 12.9898) ** 2
    revolve(p, rings, BLUE, 'CN_Blue', 32, (cx, cy, 0), arc=2 * math.pi - slit, start=slit / 2, mult=glaze)
    revolve(p, [(R * .95 * math.cos(t), zd + R * .87 * math.sin(t)) for t in np.linspace(0, math.radians(84), 6)], CHARCOAL, 'CN_Black', 12, (cx, cy, 0))
    cap = R * math.cos(math.radians(84))
    revolve(p, [(cap + .02, zd + R * .92 * math.sin(math.radians(84)) - .01), (cap * .5, zd + R * .92 + .02), (.03, zd + R * .92 + .05)],
            GOLD, 'CN_Gold', 12, (cx, cy, 0))
    for k in range(10):
        a = slit / 2 + (2 * math.pi - slit) * k / 9
        pts = [(cx + (R + .012) * math.cos(t) * math.cos(a), cy + (R + .012) * math.cos(t) * math.sin(a), zd + (R * .92 + .012) * math.sin(t))
               for t in np.linspace(0, math.radians(86), 8)]
        tube(p, pts, .03 if k in (0, 9) else .022, GOLD_PALE, 'CN_Gold', 5, True)
    top = zd + R * .92 + .05
    blob(p, (cx, cy, top + .07), .075, GOLD, 'CN_Gold', 1, .02, 5)
    tube(p, [(cx, cy, top + .12), (cx, cy, top + .3)], [.018, .004], GOLD, 'CN_Gold', 6, True)
    el = math.radians(32)
    a = np.array([cx, cy, zd + .2])
    b = a + np.array([math.cos(el), 0, math.sin(el)]) * (R + .35)
    tube(p, [a, a + (b - a) * .6, b], [.13, .12, .15], GOLD_DEEP, 'CN_Gold', 10, True)
    tube(p, [a - np.array([0, 0, .2]), a], .06, CHARCOAL, 'CN_Metal', 6, True)
    return top + .3


# ---------------------------------------------------------------- the other houses

def _house1(p, rng, seed):
    """The tower house: three storeys on a 5.2 m square, gold-framed windows under stone lintels, a small
    iron balcony on the top floor, a roof terrace and an observatory."""
    x0, x1, y0, y1 = -2.6, 2.6, -2.6, 2.6
    plinth, f1, f2, eave_wall = .45, 3.55, 6.55, 9.55
    style = {'frame': GOLD_PALE, 'frame_slot': 'CN_Gold', 'stone': LIMESTONE, 'door': BLACK, 'lintel': True, 'lit': .22, 'reveal': .26}
    walls = house_walls(x0, x1, y0, y1)
    L = y1 - y0
    front = [('door', (L / 2 - .55, L / 2 + .55, plinth, 3.05)), ('win', (.8, 1.4, 1.5, 2.65)), ('win', (L - 1.4, L - .8, 1.5, 2.65)),
             ('win', (1.15, 2.0, 4.3, 5.8)), ('win', (L - 2.0, L - 1.15, 4.3, 5.8)), ('french', (L / 2 - .5, L / 2 + .5, f2, f2 + 2.3))]
    back = plan_windows(L, 2, 1.5, 2.7, .75, margin=.6) + plan_windows(L, 2, 4.3, 5.8, .85, margin=.6) + plan_windows(L, 2, 7.3, 8.8, .85, margin=.6)
    side = plan_windows(L, 1, 1.45, 2.75, .8) + plan_windows(L, 2, 4.3, 5.8, .8, margin=.6) + plan_windows(L, 1, 7.3, 8.8, .8)
    plan = {'front': front, 'back': back, 'right': side, 'left': side}
    ze = eave_wall + CORNICE[-1][1]
    _shell(p, walls, plan, rng, style, seed, WHITE_COOL, eave_wall, ze, 0, plinth, (f1 - .2, f2 - .2), flat=True)
    quoins(p, x0, x1, y0, y1, plinth, eave_wall, rng, seed=seed, course=.48)
    w, _ = walls['front']
    balcony(p, w, L / 2 - .9, L / 2 + .9, f2, .5, rng, seed=seed, finial=GOLD)
    steps_up(p, w, L / 2 - .7, L / 2 + .7, plinth, 2, rng, seed=seed)
    parapet(p, x0, x1, y0, y1, ze, .82, rng, WHITE_COOL, seed=seed)
    observatory(p, -.55, 0, ze + .02, rng, seed=seed)


def _house2(p, rng, seed):
    """The long house: a ground-floor loggia of four round arches on Tuscan columns across its front, its
    rooms behind a recessed wall, a second storey over the arcade and a low barrel-tile roof."""
    x0, x1, y0, y1 = -3.5, 3.1, -5.6, 5.6
    plinth, zs, zc, eave_wall = .3, 2.72, 4.3, 6.82
    t, side_t, e, x_rec = .45, .45, .9, 1.0
    L = y1 - y0
    bay = (L - 2 * e) / 4
    style = {'frame': BLACK, 'stone': LIMESTONE, 'shutters': BLACK, 'door': RED, 'shutter_rate': .45}
    ze = eave_wall + CORNICE[-1][1]
    rise, lift = 1.2, .18
    white = WHITE_PURE
    front = Wall((x1, y0, 0), (1, 0, 0))
    # The arcade: end piers, the arched band over the columns (solid, both faces), the storey above, all rendered; the
    # arches' mouldings and keystones and the columns are limestone.
    wall_cells(p, Wall((x1, y0, 0), (1, 0, 0)), e, zs, white, slot='CN_Plaster', thick=t, ends=(False, True), top_edge=False, seed=seed)
    wall_cells(p, Wall((x1, y1 - e, 0), (1, 0, 0)), e, zs, white, slot='CN_Plaster', thick=t, ends=(True, False), top_edge=False, seed=seed + 1)
    arches = [(e + bay * k, e + bay * (k + 1), zs, zs + bay / 2, zs) for k in range(4)]
    wall_cells(p, front, L, zc, white, slot='CN_Plaster', openings=arches, thick=t, v0=zs, ends=(False, False), top_edge=False, seed=seed + 2)
    for (a0, a1, _, _, sp) in arches:
        arch_head(p, front, a0, a1, sp, t, white, slot='CN_Plaster', seed=seed, back=True)
        wsweep(p, front, arch_path(a0, a1, sp, sp, bottom=False)[1:-1], [(.15, 0), (.15, .025), (.13, .045), (0, .045), (0, 0)],
               tint(LIMESTONE, .93), 'CN_White', closed=False, mult=lambda v: weather(v, seed + 3, damp=0, stain=.05))
        kc = (a0 + a1) / 2
        wbox(p, front, kc - .1, kc + .1, sp + bay / 2 - .04, sp + bay / 2 + .22, -.07, .1, tint(LIMESTONE, .9), 'CN_White', .015)
    for k in range(1, 4):
        tuscan(p, x1 - t / 2, y0 + e + bay * k, plinth, zs - plinth, .19, rng, seed=seed + k)
    upper = [('win', (e + bay * (k + .5) - .45, e + bay * (k + .5) + .45, 5.0, 6.35)) for k in range(4)]
    wall_cells(p, front, L, ze + lift - .02, white, slot='CN_Plaster', openings=[op for _, op in upper], v0=zc, seed=seed + 4)
    fit(p, front, upper, rng, style, seed + 5, L)
    # Behind the arcade: the recessed wall with the doors, the loggia's end walls, ceiling, beams, floor.
    rec = Wall((x_rec, y0 + side_t, 0), (1, 0, 0))
    RL = L - 2 * side_t
    rec_ops = [('door', (RL * .3 - .55, RL * .3 + .55, plinth, 3.1)), ('win', (RL * .55 - .45, RL * .55 + .45, 1.2, 2.7)),
               ('win', (RL * .78 - .45, RL * .78 + .45, 1.2, 2.7)), ('win', (RL * .08 - .3, RL * .08 + .3, 1.2, 2.7))]
    wall_cells(p, rec, RL, zc, white, slot='CN_Plaster', openings=[op for _, op in rec_ops], seed=seed + 6)
    fit(p, rec, rec_ops, rng, dict(style, shutter_rate=0.0), seed + 7, RL)
    depth = x1 - t - x_rec
    wall_cells(p, Wall((x1 - t, y0 + side_t, 0), (0, 1, 0)), depth, zc, tint(white, .92), slot='CN_Plaster', seed=seed + 8)
    wall_cells(p, Wall((x_rec, y1 - side_t, 0), (0, -1, 0)), depth, zc, tint(white, .92), slot='CN_Plaster', seed=seed + 9)
    zceil = zs + bay / 2 + .25
    p.add([(x_rec, y0 + side_t, zceil), (x_rec, y1 - side_t, zceil), (x1 - t, y1 - side_t, zceil), (x1 - t, y0 + side_t, zceil)], [[0, 1, 2, 3]],
          paint(WHITE_PURE, [.72, .7, .74, .76]), 'CN_Plaster')
    for k in range(7):
        yb = y0 + side_t + .4 + (L - 2 * side_t - .8) * k / 6
        bevel_box(p, ((x_rec + x1 - t) / 2, yb, zceil - .11), ((x1 - t - x_rec) / 2, .08, .11), tint(CHARCOAL, rng.uniform(.6, 1)), 'CN_Black', .015)
    paving(p, x_rec, x1, y0 + side_t, y1 - side_t, plinth, .55, rng, IVORY, seed=seed)
    # The other walls, mouldings, quoins and roof.
    back = plan_windows(L, 4, 1.3, 2.75, .9, 2, (1.0, plinth, 2.75, 'backdoor'), .7) + plan_windows(L, 4, 5.0, 6.35, .9, margin=.7)
    side_ops = [('win', (x1 - x0 - 2.6, x1 - x0 - 1.7, 1.3, 2.75)), ('win', (2.2, 3.1, 5.0, 6.35))]
    walls = house_walls(x0, x1, y0, y1)
    # The loggia's end walls stand only side_t behind the side walls, along the loggia's span of each (in that wall's
    # u): a ground-floor window over that span gets a room no deeper (the left wall's west window).
    loggia = {'left': (x_rec - x0, x1 - t - x0), 'right': (t, x1 - x_rec)}
    for name in ('back', 'right', 'left'):
        w, length = walls[name]
        ops = back if name == 'back' else side_ops
        top = ze + lift - .02 if name == 'back' else eave_wall + .02
        wall_cells(p, w, length, top, white, slot='CN_Plaster', openings=[op for _, op in ops], seed=seed + 10 + len(name))
        span = loggia.get(name)
        clear = None if span is None else (lambda op, span=span: side_t if op[0] < span[1] and op[1] > span[0] and op[2] < zc else None)
        fit(p, w, ops, rng, style, seed + 11 + len(name), length, clear)
        if name != 'back':
            gable_end(p, w, length, ze, lift - .05, rise, white, seed, slot='CN_Plaster')
    stone = style['stone']
    ring_moulding(p, x0, x1, y0, y1, 0.0, [(0, 0), (.07, 0), (.07, plinth - .06), (.04, plinth), (0, plinth)], tint(stone, .86), seed=seed,
                  mult=lambda v: weather(v, seed + 1, damp=.32, rise=.3))
    ring_moulding(p, x0, x1, y0, y1, zc, STRING, tint(stone, .93), seed=seed + 2)
    ring_moulding(p, x0, x1, y0, y1, eave_wall, CORNICE, tint(stone, .95), seed=seed + 3)
    quoins(p, x0, x1, y0, y1, plinth, eave_wall, rng, seed=seed, course=.5)
    # A long roof laid with a larger tile, as a bigger house would be.
    gable_roof(p, x0, x1, y0, y1, ze, rise, rng, pitch=.36, course=.5)


def _house3(p, rng, seed):
    """The corner shop: a lit round-headed shop window under a striped awning beside a glazed door, red
    shutters above, and a roof terrace with a stair hut and a pergola grown over with red flowers."""
    x0, x1, y0, y1 = -3.7, 3.1, -3.5, 3.5
    plinth, f1, eave_wall = .4, 3.95, 7.0
    style = {'frame': BLACK, 'stone': LIMESTONE, 'shutters': RED, 'door': BLACK, 'shutter_rate': .75}
    walls = house_walls(x0, x1, y0, y1)
    L = y1 - y0
    shop = (1.0, 3.4, .95, 3.65, 2.45)
    front = [('door', (4.35, 5.45, plinth, 3.2))] + plan_windows(L, 3, 4.75, 6.25, .9, margin=.95)
    back = plan_windows(L, 2, 1.3, 2.8, .9, 1, (1.0, plinth, 2.8, 'backdoor'), 1.0) + plan_windows(L, 3, 4.75, 6.25, .9, margin=.95)
    side = plan_windows(x1 - x0, 2, 1.3, 2.8, .9, margin=.9) + plan_windows(x1 - x0, 2, 4.75, 6.25, .9, margin=.9)
    plan = {'front': front, 'back': back, 'right': side, 'left': side}
    ze = eave_wall + CORNICE[-1][1]
    w, _ = walls['front']
    # The shop window is cut with the front wall (the shell fills the other openings).
    for name, (wl, length) in walls.items():
        ops = plan[name]
        extra = [shop] if name == 'front' else []
        wall_cells(p, wl, length, eave_wall + .02, WHITE_PURE, slot='CN_Plaster', openings=[op for _, op in ops] + extra, seed=seed + len(name))
        fit(p, wl, ops, rng, style, seed + 7 * len(name), length)
    arch_head(p, w, shop[0], shop[1], shop[4], .24, WHITE_PURE, slot='CN_Plaster', seed=seed)
    window(p, w, shop, rng, 'lit', .24, BLACK, 'CN_Black', stone=style['stone'], glow=LIGHT_WARM, seed=seed, length=L)
    awning(p, w, shop[0] - .15, shop[1] + .15, 3.77, 3.1, .95, rng, stripes=8)
    stone = style['stone']
    ring_moulding(p, x0, x1, y0, y1, 0.0, [(0, 0), (.07, 0), (.07, plinth - .06), (.04, plinth), (0, plinth)], tint(stone, .86), seed=seed,
                  mult=lambda v: weather(v, seed + 1, damp=.32, rise=.3))
    ring_moulding(p, x0, x1, y0, y1, f1 - .16, STRING, tint(stone, .93), seed=seed + 2)
    ring_moulding(p, x0, x1, y0, y1, eave_wall, CORNICE, tint(stone, .95), seed=seed + 3)
    quoins(p, x0, x1, y0, y1, plinth, eave_wall, rng, seed=seed)
    steps_up(p, w, 4.15, 5.65, plinth, 2, rng, seed=seed)
    parapet(p, x0, x1, y0, y1, ze, .8, rng, seed=seed)
    deck = ze + .02
    # Stair hut at the back corner, its door facing the terrace.
    hx0, hx1, hy0, hy1 = x0 + .24, x0 + 2.0, y0 + .24, y0 + 1.9
    hut = house_walls(hx0, hx1, hy0, hy1)
    for name, (wl, length) in hut.items():
        wl.o = wl.o + np.array([0, 0, deck])
        ops = [('backdoor', ((hy1 - hy0) / 2 - .42, (hy1 - hy0) / 2 + .42, 0, 2.0))] if name == 'front' else []
        wall_cells(p, wl, length, 2.2, WHITE_PURE, slot='CN_Plaster', openings=[op for _, op in ops], seed=seed + 20 + len(name), cell=.8)
        fit(p, wl, ops, rng, style, seed + 21, length)
    pts, dirs = rect_ring((hx0 + hx1) / 2, (hy0 + hy1) / 2, (hx1 - hx0) / 2, (hy1 - hy0) / 2, 2.0)
    pts[:, 2] = deck + 2.2
    sweep3(p, pts, dirs, UP, [(0, 0), (.05, .02), (.07, .08), (.07, .14), (-(hy1 - hy0) / 2 + .01, .14)], tint(LIMESTONE, .9), 'CN_White')
    # Pergola over the front of the terrace: black iron posts and beams under red bougainvillea.
    px0, px1, py0, py1 = -.9, x1 - .45, y0 + .45, y1 - .45
    iron = CHARCOAL
    top = deck + 2.15
    for xx in (px0, px1):
        for yy in (py0, (py0 + py1) / 2, py1):
            tube(p, [(xx, yy, deck), (xx, yy, top)], .045, iron, 'CN_Metal', 6, True)
            bevel_box(p, (xx, yy, deck + .04), (.09, .09, .04), iron, 'CN_Metal', .01)
        bevel_box(p, (xx, (py0 + py1) / 2, top + .05), (.05, (py1 - py0) / 2 + .15, .06), iron, 'CN_Metal', .01)
    for k in range(10):
        yy = py0 + (py1 - py0) * k / 9
        bevel_box(p, ((px0 + px1) / 2, yy, top + .14), ((px1 - px0) / 2 + .2, .025, .03), iron, 'CN_Metal', .008)
    # Bougainvillea: a mat of leaf over the rafters, thickest along the beams, trailing over the front.
    centres = [(rng.uniform(px0, px1), rng.uniform(py0, py1), top + .12) for _ in range(18)]
    centres += [(xx + rng.uniform(-.2, .2), rng.uniform(py0, py1), top + .1) for xx in (px0, px1) for _ in range(5)]
    centres += [(px1 + .08, rng.uniform(py0, py1), top - rng.uniform(.25, .8)) for _ in range(6)]
    leaf_cloud(p, centres, (.55, .5, .12), 1000, rng, (RED_DEEP, RED_DEEP, RED, RED_BRIGHT, RED_BRIGHT), size=(.09, .16), up_bias=.7)
    for xx in (px0, px1):
        tube(p, [(xx + .06, py0 + .06, deck), (xx + .1, py0 + .2, deck + 1.2), (xx + .05, py0 + .1, top)], .035, CHARCOAL, 'CN_Black', 5, False)
    planter_box(p, px1 - .3, (py0 + py1) / 2, deck, rng)


def planter_box(p, x, y, z, rng):
    """A small stone trough of black soil, the root of the pergola's climber."""
    st = tint(IVORY, .9)
    bevel_box(p, (x, y, z + .2), (.22, .5, .2), st, 'CN_White', .02)
    p.add([(x - .19, y - .47, z + .37), (x + .19, y - .47, z + .37), (x + .19, y + .47, z + .37), (x - .19, y + .47, z + .37)], [[0, 1, 2, 3]],
          tint(CHARCOAL, .7), 'CN_Black', False)
    leaf_cloud(p, [(x, y + q, z + .5) for q in (-.3, 0, .3)], (.22, .28, .16), 80, rng, (RED_DEEP, RED_BRIGHT), size=(.05, .1))




# ---------------------------------------------------------------- ruins (the Old Quarter)

def rotation(axis, angle):
    """Rotation matrix (a proper rotation, so face winding survives) about a unit axis by angle radians."""
    a = np.asarray(axis, np.float64)
    a = a / np.linalg.norm(a)
    c, s_, t = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    x, y, z = a
    return np.array([[t * x * x + c, t * x * y - s_ * z, t * x * z + s_ * y],
                     [t * x * y + s_ * z, t * y * y + c, t * y * z - s_ * x],
                     [t * x * z - s_ * y, t * y * z + s_ * x, t * z * z + c]])


def merge(p, q, R=None, t=(0, 0, 0), pivot=(0, 0, 0)):
    """Appends part q into p, rotated by R about pivot and moved by t: fallen doors, slabs, railings and
    dome shards built upright and then tipped over."""
    v = np.asarray(q.v, np.float64)
    if R is not None:
        v = (v - np.asarray(pivot)) @ np.asarray(R).T + np.asarray(pivot)
    v = v + np.asarray(t, np.float64)
    base = len(p.v)
    p.v.extend(v.tolist())
    p.c.extend(q.c)
    for f, m, sm in zip(q.f, q.m, q.s):
        p.f.append([base + i for i in f])
        p.m.append(p.slots.index(q.slots[m]))
        p.s.append(sm)


def soot(w, ops, seed, inner=False):
    """Scorch for a burnt wall in wall terms: soot blooms, black plumes rising from every opening the fire
    vented through, a sooted foot where the rubble smouldered."""
    def f(v):
        v = np.asarray(v, np.float64).reshape(-1, 3)
        m = scorch(v, seed + (7 if inner else 0), strength=.85, base=.5 if inner else .7)
        u = (v - w.o) @ w.U
        for op in ops:
            u0, u1, a, b = op[:4]
            above = np.maximum(v[:, 2] - b + .25, 0)
            spread = (u1 - u0) / 2 + .2 + .35 * above
            plume = np.exp(-((u - (u0 + u1) / 2) / spread) ** 2) * (v[:, 2] > b - .25) * np.exp(-above / 3.0)
            m = m * (1 - .6 * plume)
        return np.clip(m, .04, 1)
    return f


def beam(p, a, b, w, h, rng, colour=CHARCOAL, burnt=.6):
    """A charred timber from a to b, w by h, its ends eaten back and narrowed by the fire."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    ax = b - a
    L = np.linalg.norm(ax)
    ax /= L
    side = np.cross(ax, UP)
    if np.linalg.norm(side) < 1e-6:
        side = np.array([1., 0, 0])
    side /= np.linalg.norm(side)
    up = np.cross(side, ax)
    pts = []
    for zb in (0, 1):
        for yb in (0, 1):
            for xb in (0, 1):
                end = a if xb == 0 else b
                shrink = 1 - burnt * rng.uniform(.3, 1.0) * .5
                pts.append(end + side * (w / 2 * (1 if yb else -1) * shrink) + up * (h / 2 * (1 if zb else -1) * shrink) + ax * rng.normal(0, .02))
    pts = np.array(pts)
    hexa(p, pts, paint(colour, rng.uniform(.5, 1.0, 8)), 'CN_Black')


def rubble(p, cx, cy, rx, ry, count, rng, height=.6, colours=(WHITE, IVORY, ASH), tiles=0, base_z=0.0):
    """A heap of fallen masonry: tumbled, broken blocks over a low mound, with shards of red tile; whites
    are greyed by smoke."""
    for _ in range(count):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0, 1) ** .7
        x, y = cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr
        z = base_z + height * (1 - rr ** 2) * rng.uniform(.5, 1.0)
        size = rng.uniform(.12, .38, 3) * np.array([1.4, 1, .8])
        R = rotation(rng.normal(0, 1, 3), rng.uniform(0, math.pi))
        corners = np.array([[sx, sy, sz] for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)], np.float64) * size / 2
        corners = corners * rng.uniform(.8, 1.15, (8, 1))
        pts = corners @ R.T + np.array([x, y, z])
        pts[:, 2] = np.maximum(pts[:, 2], base_z)
        c = colours[rng.integers(0, len(colours))]
        hexa(p, pts, paint(c, scorch(pts, int(rng.integers(0, 999)), strength=.5) * rng.uniform(.6, 1.0)), 'CN_White')
    for _ in range(tiles):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0, 1)
        x, y = cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr
        z = base_z + height * (1 - rr ** 2) * rng.uniform(.4, 1.0) + .05
        R = rotation(rng.normal(0, 1, 3), rng.uniform(0, .8))
        corners = np.array([[sx, sy, sz] for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)], np.float64) * np.array([.2, .12, .012])
        pts = corners @ R.T + np.array([x, y, z])
        pts[:, 2] = np.maximum(pts[:, 2], base_z)
        hexa(p, pts, tint(RED, rng.uniform(.45, .9)), 'CN_Red')
    mound(p, cx, cy, rx * .9, ry * .9, height * .75, rng, base_z)


def mound(p, cx, cy, rx, ry, h, rng, base_z=0.0, colour=ASH, rings=4, sides=14):
    """A low lumpy heap of crushed stone and ash (an elliptical cap that meets the ground at base_z)."""
    phase = rng.uniform(0, 100, 2)
    verts = [(cx, cy, base_z + h)]
    for i in range(1, rings + 1):
        t = i / rings
        for j in range(sides):
            a = 2 * math.pi * j / sides
            bump = 1 + .18 * math.sin(a * 3 + phase[0]) * math.sin(t * 5 + phase[1])
            r = math.sin(t * math.pi / 2) * bump
            z = base_z + h * math.cos(t * math.pi / 2) * (1 + .15 * math.sin(a * 5 + phase[1])) if i < rings else base_z
            verts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a), z))
    faces = [[0, 1 + j, 1 + (j + 1) % sides] for j in range(sides)]
    for i in range(rings - 1):
        for j in range(sides):
            a0, a1 = 1 + i * sides + j, 1 + i * sides + (j + 1) % sides
            faces.append([a0, a0 + sides, a1 + sides, a1])
    verts = np.array(verts)
    faces = [f if np.dot(newell(verts[f]), verts[f].mean(0) - (cx, cy, base_z - h)) >= 0 else f[::-1] for f in faces]
    p.add(verts, faces, paint(colour, scorch(verts, int(rng.integers(0, 999)), strength=.5, base=.8)), 'CN_White', True)


def weeds(p, spots, rng, count=10):
    """Gold grass and white flowers that took the ruin back."""
    for (x, y, z) in spots:
        for _ in range(count):
            a = rng.uniform(0, 2 * math.pi)
            l = rng.uniform(.25, .6)
            base = np.array([x + rng.normal(0, .15), y + rng.normal(0, .15), z])
            tipp = base + np.array([math.cos(a) * l * .35, math.sin(a) * l * .35, l])
            side = np.array([-math.sin(a), math.cos(a), 0]) * .012
            p.add([base - side, base + side, tipp], [[0, 1, 2]], tint(GOLD_GRASS if rng.uniform() < .8 else GOLD_STRAW, rng.uniform(.8, 1.0)), 'CN_Leaf', False)
        leaf_cloud(p, [(x, y, z + .35)], (.18, .18, .12), 14, rng, (WHITE_PURE,), size=(.03, .06))


def shell_piece(p, r, rz, t, e0, e1, a0, a1, ne, na, colour=BLUE, inner=CHARCOAL):
    """A broken piece of a glazed dome: a patch of the shell between elevations e0..e1 and azimuths
    a0..a1, with real thickness and its broken edges closed (glazed outside, sooted plaster inside)."""
    def pt(e, a, rr, rrz):
        return (rr * math.cos(e) * math.cos(a), rr * math.cos(e) * math.sin(a), rrz * math.sin(e))
    es, az = np.linspace(e0, e1, ne + 1), np.linspace(a0, a1, na + 1)
    outer = np.array([[pt(e, a, r, rz) for a in az] for e in es])
    inn = np.array([[pt(e, a, r - t, rz - t) for a in az] for e in es])
    verts, faces = [], []

    def quad(q, want):
        q = np.array(q)
        if np.dot(newell(q), want) < 0:
            q = q[::-1]
        faces.append(list(range(len(verts), len(verts) + 4)))
        verts.extend(q)
    for i in range(ne):
        for j in range(na):
            c = outer[i:i + 2, j:j + 2].reshape(-1, 3).mean(0)
            quad([outer[i, j], outer[i, j + 1], outer[i + 1, j + 1], outer[i + 1, j]], c)
    n_out = len(faces)
    for i in range(ne):
        for j in range(na):
            c = inn[i:i + 2, j:j + 2].reshape(-1, 3).mean(0)
            quad([inn[i, j], inn[i, j + 1], inn[i + 1, j + 1], inn[i + 1, j]], -c)
    for j in range(na):
        for i, sign in ((0, -1), (ne, 1)):
            q = [outer[i, j], outer[i, j + 1], inn[i, j + 1], inn[i, j]]
            quad(q, np.array([0, 0, sign]) + sign * .0 * np.mean(q, 0))
    for i in range(ne):
        for j, sign in ((0, -1), (na, 1)):
            a = az[j]
            q = [outer[i, j], outer[i + 1, j], inn[i + 1, j], inn[i, j]]
            quad(q, sign * np.array([-math.sin(a), math.cos(a), 0]))
    verts = np.array(verts)
    k = np.arange(len(verts))
    glaze = .7 + .25 * np.sin(verts[:, 0] * 31 + verts[:, 1] * 17) ** 2
    p.add(verts[:n_out * 4], [f for f in faces[:n_out]], paint(colour, glaze[:n_out * 4]), 'CN_Blue', True)
    rest = [[i - n_out * 4 for i in f] for f in faces[n_out:]]
    p.add(verts[n_out * 4:], rest, paint(inner, .7 + .3 * (k[n_out * 4:] % 3) / 2), 'CN_Black', False)


def ruin(k):
    """The Old Quarter's burnt houses (README sizes): 0 the shell of a two-storey house, 1 the stump of a
    tower house whose observatory fell in. Walls broken along their courses, scorched, open to the sky."""
    p = Part('SM_CN_Ruin%d' % k, ALL_SLOTS)
    rng = np.random.default_rng(3200 + k)
    (_ruin0, _ruin1)[k](p, rng, 3200 + k)
    return finish(p)


def _broken(points, rng, rough=.35):
    """A broken wall top: a piecewise-linear profile [(u, height)] with ragged noise."""
    us = np.array([q[0] for q in points])
    hs = np.array([q[1] for q in points])
    phase = rng.uniform(0, 100)

    def top(u):
        return float(np.interp(u, us, hs) + rough * (math.sin(u * 2.3 + phase) * .6 + math.sin(u * 5.9 + phase * 2) * .4))
    return top


def _ruin_walls(p, rng, seed, x0, x1, y0, y1, plan, profiles, thick=.42, colour=WHITE_PURE):
    """Solid broken walls of render (CN_Plaster) round a rectangle: the front and back run the full width
    and their ends are the corners; the sides fit between them. Openings stay as empty holes through the
    wall."""
    L, D = y1 - y0, x1 - x0
    walls = {'front': (Wall((x1, y0, 0), (1, 0, 0)), L, 0.0), 'back': (Wall((x0, y1, 0), (-1, 0, 0)), L, 0.0),
             'right': (Wall((x1 - thick, y1, 0), (0, 1, 0)), D - 2 * thick, thick), 'left': (Wall((x0 + thick, y0, 0), (0, -1, 0)), D - 2 * thick, thick)}
    for name, (w, length, shift) in walls.items():
        ops = [op for _, op in plan.get(name, [])]
        ops = [(a - shift, b - shift, c, d) for a, b, c, d in ops if a - shift > .1 and b - shift < length - .1]
        top = profiles[name]
        hmax = max(top(u) for u in np.linspace(0, length, 40)) + .5
        breaks = np.cumsum(rng.uniform(.22, .62, 40))
        us, vs = wall_cells(p, w, length, hmax, colour, slot='CN_Plaster', openings=ops, thick=thick, top=top, cell=.7, vcell=.3, seed=seed + len(name),
                            mult=soot(w, ops, seed + len(name)), inner_mult=soot(w, ops, seed + len(name), inner=True),
                            edge_mult=lambda v: scorch(v, seed, strength=.7, base=.75),
                            extra_u=breaks[breaks < length])
        ragged_top(p, w, us, vs, top, ops, thick, rng, colour, seed + len(name))
    return walls


def ragged_top(p, w, us, vs, top, ops, thick, rng, colour, seed):
    """Loose, tilted stones along a broken wall top, so its line reads as fallen masonry rather than a
    stepped edge."""
    vc = (vs[:-1] + vs[1:]) / 2
    for a, b in zip(us[:-1], us[1:]):
        uc = (a + b) / 2
        solid = vc < top(uc)
        if not solid.any():
            continue
        h = vs[1:][solid].max()
        if any(o[0] - .05 < uc < o[1] + .05 and o[2] - .05 < h < o[3] + .3 for o in ops):
            continue
        for _ in range(1 + int(rng.uniform() < .5)):
            wa, wb = a + rng.uniform(0, .3) * (b - a), b - rng.uniform(0, .3) * (b - a)
            hh = rng.uniform(.12, .3)
            lean = rng.normal(0, .06, 8)
            corners = []
            for zb in (0, 1):
                for yb in (0, 1):
                    for xb in (0, 1):
                        corners.append(w.at(wa if xb == 0 else wb, h - .03 + (hh if zb else 0) + lean[xb + 2 * yb + 4 * zb] * zb,
                                            (-.02 if yb == 0 else thick + .02) + rng.normal(0, .02)))
            corners = np.array(corners)
            hexa(p, corners, paint(colour, scorch(corners, seed, strength=.8, base=.75) * rng.uniform(.7, 1.0)), 'CN_White')


def _ruin0(p, rng, seed):
    x0, x1, y0, y1 = -3.0, 2.6, -4.15, 4.15
    plinth = .45
    L, D = y1 - y0, x1 - x0
    front = plan_windows(L, 3, 1.35, 2.95, 1.0, 1, (1.2, plinth, 3.35, 'door'), .65) + plan_windows(L, 3, 4.75, 6.25, .95, 1, (1.2, 3.95, 6.3, 'french'), .65)
    back = plan_windows(L, 3, 1.35, 2.85, .9, 0, (1.0, plinth, 2.75, 'backdoor'), .65) + plan_windows(L, 3, 4.75, 6.15, .9, margin=.65)
    side = plan_windows(D, 1, 1.4, 2.9, .9) + plan_windows(D, 1, 4.8, 6.2, .9)
    plan = {'front': front, 'back': back, 'right': side, 'left': side}
    profiles = {'front': _broken([(0, 7.3), (1.1, 7.15), (2.2, 5.2), (3.4, 3.3), (4.6, 2.6), (6.0, 4.4), (7.4, 5.6), (L, 5.4)], rng),
                'right': _broken([(0, 5.3), (1.6, 4.1), (3.2, 2.7), (D - .84, 2.1)], rng),
                'back': _broken([(0, 2.2), (2.5, 1.5), (4.5, 2.6), (6.5, 3.1), (L, 3.5)], rng),
                'left': _broken([(0, 3.4), (1.4, 4.5), (3.0, 6.0), (D - .84, 7.15)], rng)}
    _ruin_walls(p, rng, seed, x0, x1, y0, y1, plan, profiles)
    ring_moulding(p, x0, x1, y0, y1, 0.0, [(0, 0), (.07, 0), (.07, plinth - .06), (.04, plinth), (0, plinth)], tint(LIMESTONE, .7), seed=seed,
                  mult=lambda v: scorch(v, seed, strength=.4))
    quoins(p, x0, x1, y0, y1, plinth, 6.95, rng, colour=tint(LIMESTONE, .8), seed=seed, tops=(5.2, 2.0, 3.2, 7.4))
    # Inside: an ash floor, the collapsed upper floor and roof, charred joists and rafters.
    paving(p, x0 + .42, x1 - .42, y0 + .42, y1 - .42, .05, .7, rng, tint(ASH, .7), seed=seed, under=CHARCOAL)
    slab = Part('slab', ALL_SLOTS)
    hexa(slab, [(0, 0, -.14), (3.4, 0, -.14), (0, 2.8, -.14), (3.4, 2.8, -.14), (0, 0, 0), (3.4, 0, 0), (0, 2.8, 0), (3.4, 2.8, 0)], tint(RED_DEEP, .5), 'CN_Red')
    barrel_tiles(slab, (0, 0, 0), (1, 0, 0), (0, 1, 0), 3.35, 0, 2.8, rng, miss=.3, slip=.35, eave=0.0)
    merge(p, slab, rotation((0, 1, 0), math.radians(34)) @ rotation((0, 0, 1), math.radians(-8)), (x0 + .5, -1.6, 2.32))
    for (a, b) in (((x0 + .45, 2.6, 3.7), (x1 - .45, 2.5, 3.6)), ((x0 + .45, 1.2, 3.7), (.2, 1.0, 2.6)), ((.2, 1.0, 2.6), (1.6, .7, .3)),
                   ((x0 + .4, -2.8, 2.2), (.6, -3.3, .25)), ((x1 - .5, -3.6, 6.9), (x1 - .9, -1.6, 4.2)), ((-1.2, 3.6, .2), (1.2, 2.2, 1.5))):
        beam(p, a, b, .16, .22, rng)
    rubble(p, .6, -.6, 1.7, 2.6, 26, rng, .8, tiles=26, base_z=.05)
    rubble(p, x1 + .35, -1.6, .45, 1.6, 10, rng, .4, tiles=8)
    rubble(p, x0 - .3, 2.2, .35, 1.5, 7, rng, .3, tiles=6)
    # The fallen front door and a twisted length of the balcony railing in the street.
    leaf = Part('door', ALL_SLOTS)
    bevel_box(leaf, (0, 0, .03), (1.0, .5, .03), tint(RED, .35), 'CN_Lacquer', .01)
    for q in (-.55, 0, .55):
        bevel_box(leaf, (q, 0, .07), (.2, .34, .012), tint(RED, .28), 'CN_Lacquer', .008)
    merge(p, leaf, rotation((0, 1, 0), math.radians(9)) @ rotation((0, 0, 1), math.radians(70)), (x1 + .38, L / 2 + y0 - .2, .14))
    rail = Part('rail', ALL_SLOTS)
    railing(rail, [(0, 0, 0), (0, 1.8, 0)], .95, rng)
    merge(p, rail, rotation((0, 0, 1), math.radians(10)) @ rotation((0, 1, 0), math.radians(76)), (x1 + .16, -1.9, .05))
    weeds(p, [(x1 + .3, -2.8, 0), (x1 + .25, 1.9, 0), (-1.0, 2.6, .05), (.9, -2.9, .05), (x0 - .25, -2.6, 0), (-2.1, .4, .05)], rng)


def _ruin1(p, rng, seed):
    x0, x1, y0, y1 = -2.6, 2.6, -2.6, 2.6
    plinth = .45
    L = y1 - y0
    front = [('door', (L / 2 - .55, L / 2 + .55, plinth, 3.05)), ('win', (.8, 1.4, 1.5, 2.65)), ('win', (L - 1.4, L - .8, 1.5, 2.65)),
             ('win', (1.15, 2.0, 4.3, 5.8)), ('win', (L - 2.0, L - 1.15, 4.3, 5.8))]
    back = plan_windows(L, 2, 1.5, 2.7, .75, margin=.6) + plan_windows(L, 2, 4.3, 5.8, .85, margin=.6)
    side = plan_windows(L, 1, 1.45, 2.75, .8) + plan_windows(L, 2, 4.3, 5.8, .8, margin=.6)
    plan = {'front': front, 'back': back, 'right': side, 'left': side}
    profiles = {'front': _broken([(0, 6.4), (.9, 6.2), (2.0, 4.6), (3.4, 3.0), (L, 2.4)], rng, .3),
                'right': _broken([(0, 2.4), (2.0, 1.6), (L - .84, 1.9)], rng, .25),
                'back': _broken([(0, 1.9), (2.6, 3.1), (L, 4.5)], rng, .3),
                'left': _broken([(0, 4.5), (2.2, 5.5), (L - .84, 6.3)], rng, .3)}
    _ruin_walls(p, rng, seed, x0, x1, y0, y1, plan, profiles)
    ring_moulding(p, x0, x1, y0, y1, 0.0, [(0, 0), (.07, 0), (.07, plinth - .06), (.04, plinth), (0, plinth)], tint(LIMESTONE, .7), seed=seed,
                  mult=lambda v: scorch(v, seed, strength=.4))
    quoins(p, x0, x1, y0, y1, plinth, 9.55, rng, colour=tint(LIMESTONE, .8), seed=seed, course=.48, tops=(2.0, 1.5, 4.1, 6.5))
    paving(p, x0 + .42, x1 - .42, y0 + .42, y1 - .42, .05, .6, rng, tint(ASH, .7), seed=seed, under=CHARCOAL)
    # The observatory came down through the floors: shards of its glazed dome, a bent gold rib, the
    # telescope, charred floor joists.
    dome = Part('dome', ALL_SLOTS)
    shell_piece(dome, 1.34, 1.23, .045, math.radians(10), math.radians(70), 0, math.radians(95), 6, 9)
    merge(p, dome, rotation((1, .3, 0), math.radians(118)), (-.2, .3, 1.6))
    shard = Part('shard', ALL_SLOTS)
    shell_piece(shard, 1.34, 1.23, .045, math.radians(5), math.radians(40), 0, math.radians(40), 3, 4)
    merge(p, shard, rotation((0, 1, .2), math.radians(-100)), (x1 + .5, -1.2, 1.3))
    rib = [(-1.2 + .3 * math.cos(t), .8 + 1.1 * math.sin(t), .45 + .55 * math.sin(t * 1.7)) for t in np.linspace(0, 2.4, 9)]
    tube(p, rib, .024, tint(GOLD_PALE, .8), 'CN_Gold', 5, True)
    tube(p, [(.6, -1.4, .35), (1.2, .2, .9), (1.5, .9, 1.25)], [.13, .12, .15], tint(GOLD_DEEP, .75), 'CN_Gold', 10, True)
    for (a, b) in (((x0 + .45, -1.0, 3.4), (x1 - .45, -1.2, 3.3)), ((x0 + .45, .6, 3.4), (.4, 1.4, .4)), ((-1.6, -2.0, .3), (1.6, -.4, 1.2)),
                   ((x1 - .5, -2.1, 6.0), (x1 - .7, -.6, 3.6))):
        beam(p, a, b, .15, .2, rng)
    rubble(p, 0, 0, 1.5, 1.5, 22, rng, .9, tiles=10, base_z=.05)
    rubble(p, x1 + .35, 1.0, .4, 1.2, 8, rng, .35, tiles=4)
    rubble(p, .6, y1 + .3, 1.0, .3, 6, rng, .3, tiles=3)
    weeds(p, [(x1 + .3, -1.5, 0), (-1.4, 1.5, .05), (1.2, -1.6, .05), (x0 - .25, .4, 0)], rng)




# ---------------------------------------------------------------- civic buildings

def round_moulding(p, r, z, section, colour, slot='CN_White', sides=64, c=(0, 0, 0), seed=0, arc=2 * math.pi, start=0.0, tuck=.04):
    """A moulding run round a drum of radius r at height z. Each segment of the section is its own smooth
    band, so the profile keeps its crisp arrises while the circle shades round. Where the section meets
    the wall it is tucked in a little, under the chords of the wall's cells."""
    section = [(o - tuck if abs(o) < 1e-9 else o, h) for o, h in section]
    for (o0, h0), (o1, h1) in zip(section, section[1:]):
        if abs(o1 - o0) + abs(h1 - h0) < 1e-6:
            continue
        revolve(p, [(r + o0, z + h0), (r + o1, z + h1)], colour, slot, sides, c, True, arc, start,
                mult=lambda v: weather(v, seed, damp=.1, stain=.05))


def polar_paving(p, r0, r1, a0, a1, z, rng, colour=WHITE, ring=.7, slab=.8, joint=.012, c=(0, 0), slot='CN_White', under=SLATE):
    """Paving laid in rings between radii r0 and r1 over angles a0..a1, slabs with their own tones over a
    dark bed that shows in the joints."""
    verts, faces, cols = [], [], []
    n_r = max(1, int(round((r1 - r0) / ring)))
    for i in range(n_r):
        ra, rb = r0 + (r1 - r0) * i / n_r, r0 + (r1 - r0) * (i + 1) / n_r
        rm = (ra + rb) / 2
        n_a = max(1, int(round((a1 - a0) * rm / slab)))
        off = rng.uniform(0, 1)
        for j in range(n_a):
            aa = a0 + (a1 - a0) * (j + (off if j else 0) * 0) / n_a
            ab = a0 + (a1 - a0) * (j + 1) / n_a
            ja, jb = joint / 2 / max(ra, .1), joint / 2 / max(rb, .1)
            pts = [(ra + joint / 2, aa + ja), (ra + joint / 2, ab - ja), (rb - joint / 2, ab - jb), (rb - joint / 2, aa + jb)]
            base = len(verts)
            dz = rng.uniform(-.004, .004)
            verts += [(c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), z + dz) for rr, a in pts]
            faces.append([base, base + 1, base + 2, base + 3])
            tone = rng.uniform(.8, 1.0)
            cols += [tint(colour, tone)] * 4
    verts = np.array(verts)
    faces = [f if newell(verts[f])[2] >= 0 else f[::-1] for f in faces]
    p.add(verts, faces, np.array(cols), slot, False)
    revolve(p, [(r1, z - .006), (r0, z - .006)], under, slot, max(8, int((a1 - a0) / (2 * math.pi) * 48)), (c[0], c[1], 0), False, a1 - a0, a0)


def archive():
    """The Archive, where Kairos keeps the Conclave's memory: a round white tower (radius 10, 30 tall) on
    three steps. Its ground drum opens toward +x in an arcade of five round arches over a covered walk and
    a red double door; above, a gallery with an iron railing rings the upper tower, which is lit by twelve
    tall arched windows and a tier of smaller ones under a deep cornice, and carries a gold ribbed dome
    with a lantern."""
    p = Part('SM_CN_Archive', ALL_SLOTS)
    rng = np.random.default_rng(3300)
    seed = 3300
    # White marble throughout (CN_White, which the Unreal side gives a marble look on this mesh), dressings included:
    # neither the town's render nor its grey limestone.
    white, stone = WHITE, IVORY
    # Steps and platform.
    for k, (r, z) in enumerate(((10.0, .18), (9.7, .36), (9.4, .54))):
        st = tint(stone, .9 - .03 * k)
        revolve(p, [(r, z - .18), (r, z)], st, 'CN_White', 64, smooth=True, mult=lambda v: weather(v, seed + k, damp=.3, rise=.4))
        revolve(p, [(r, z), (r - .3 if k < 2 else 6.0, z)], st, 'CN_White', 64, smooth=False, mult=lambda v: weather(v, seed + k, damp=.2, rise=.4))
    base = .54
    R, T = 9.2, .6
    # Ground drum: the arcade sector toward +x (a solid wall, both faces) and the rest of the drum.
    bay, n_arch = 2.65, 5
    S = bay * n_arch
    zs = 3.55
    arc_w = 1.9
    arcade = Wall((0, 0, 0), r=R, a0=-S / 2 / R)
    arches = [(k * bay + (bay - arc_w) / 2, k * bay + (bay + arc_w) / 2, base, zs + arc_w / 2, zs) for k in range(n_arch)]
    top_drum = 7.7
    wall_cells(p, arcade, S, top_drum, white, openings=arches, thick=T, v0=base, ends=(False, False), top_edge=False, cell=1.0, seed=seed)
    for (a0, a1, _, _, sp) in arches:
        arch_head(p, arcade, a0, a1, sp, T, white, seed=seed, back=True)
        wsweep(p, arcade, arch_path(a0, a1, sp, sp, bottom=False)[1:-1], [(.18, 0), (.18, .03), (.15, .05), (0, .05), (0, 0)], tint(stone, .93), 'CN_White',
               closed=False, mult=lambda v: weather(v, seed + 1, damp=0, stain=.05))
        kc = (a0 + a1) / 2
        wbox(p, arcade, kc - .13, kc + .13, sp + arc_w / 2 - .05, sp + arc_w / 2 + .3, -.08, .12, tint(stone, .9), 'CN_White', .015)
    rest = Wall((0, 0, 0), r=R, a0=S / 2 / R)
    n_small = 9
    span = 2 * math.pi * R - S
    small = [(span * (k + .5) / n_small - .45, span * (k + .5) / n_small + .45, 3.0, 5.0, 4.55) for k in range(n_small)]
    wall_cells(p, rest, span, top_drum, white, openings=small, reveal=.3, v0=base, cell=1.1, seed=seed + 1)
    for op in small:
        arch_head(p, rest, op[0], op[1], op[4], .3, white, seed=seed)
        window(p, rest, op, rng, 'glass' if rng.uniform() < .7 else 'lit', .3, GOLD_PALE, 'CN_Gold', stone=stone, mullion=False, seed=seed,
               length=span)
    # The covered walk behind the arcade: its floor, a coffered ceiling on black beams, the inner wall and
    # the Archive's red double door, and the walls closing its ends.
    r_in = R - T
    r_wall = 6.6
    half = S / 2 / R
    polar_paving(p, r_wall, R - .02, -half, half, base, rng, stone, ring=.66, slab=.75)
    zceil = 5.15
    revolve(p, [(r_wall, zceil), (r_in, zceil)], tint(white, .8), 'CN_White', 24, smooth=False, arc=2 * half, start=-half)
    for k in range(n_arch + 1):
        a = -half + 2 * half * k / n_arch
        beam_c = ((r_wall + r_in) / 2 * math.cos(a), (r_wall + r_in) / 2 * math.sin(a), zceil - .13)
        bevel_box(p, beam_c, ((r_in - r_wall) / 2, .1, .13), tint(CHARCOAL, .8), 'CN_Black', .015, math.degrees(a))
    inner = Wall((0, 0, 0), r=r_wall, a0=-half)
    IL = 2 * half * r_wall
    door_op = (IL / 2 - .95, IL / 2 + .95, base, base + 3.4)
    inner_ops = [door_op, (IL * .17 - .4, IL * .17 + .4, 1.6, 3.4, 3.0), (IL * .83 - .4, IL * .83 + .4, 1.6, 3.4, 3.0)]
    wall_cells(p, inner, IL, zceil + .02, tint(white, .95), openings=inner_ops, v0=base, reveal=.32, cell=.9, seed=seed + 2)
    door(p, inner, door_op, rng, RED, .32, transom=.55, double=True, knocker=True, surround=stone, seed=seed, lit=True)
    for op in inner_ops[1:]:
        arch_head(p, inner, op[0], op[1], op[4], .28, white, seed=seed)
        window(p, inner, op, rng, 'lit', .28, GOLD_PALE, 'CN_Gold', stone=stone, mullion=False, seed=seed, glow=LIGHT_WARM, length=IL)
    for a, n in ((-half, (-math.sin(-half), math.cos(-half), 0)), (half, (math.sin(half), -math.cos(half), 0))):
        if a < 0:
            w = Wall((r_in * math.cos(a), r_in * math.sin(a), 0), n)
        else:
            w = Wall((r_wall * math.cos(a), r_wall * math.sin(a), 0), n)
        wall_cells(p, w, r_in - r_wall, zceil + .02, tint(white, .9), v0=base, cell=1.0, seed=seed + 3)
    # Drum cornice and the gallery.
    round_moulding(p, R, top_drum, [(0, 0), (.05, .03), (.08, .12), (.2, .2), (.24, .3), (.28, .42)], tint(stone, .95), seed=seed)
    zg = top_drum + .42
    revolve(p, [(R + .28, zg), (7.75, zg)], tint(stone, .85), 'CN_White', 64, smooth=False, mult=lambda v: weather(v, seed + 4, damp=0, stain=.08))
    posts = 32
    rr = R + .12
    for k in range(posts):
        a0, a1 = 2 * math.pi * k / posts, 2 * math.pi * (k + 1) / posts
        railing(p, [(rr * math.cos(a0), rr * math.sin(a0), zg), (rr * math.cos(a1), rr * math.sin(a1), zg)], 1.05, rng, spacing=.25)
    # Upper tower with its windows and the door onto the gallery.
    Ru = 7.9
    upper = Wall((0, 0, 0), r=Ru, a0=-math.pi)
    UL = 2 * math.pi * Ru
    tall, high = [], []
    for k in range(12):
        uc = UL * (k + .5) / 12
        tall.append((uc - .65, uc + .65, 9.7, 14.75 + .65, 14.75))
        high.append((uc - .45, uc + .45, 17.0, 18.65 + .45, 18.65))
    gdoor = (UL / 2 - .62, UL / 2 + .62, zg, zg + 2.75)
    tall = [op for op in tall if abs((op[0] + op[1]) / 2 - UL / 2) > 1.0]
    top_upper = 21.4
    wall_cells(p, upper, UL, top_upper, white, openings=tall + high + [gdoor], reveal=.34, v0=zg, cell=1.1, seed=seed + 5)
    for op in tall + high:
        arch_head(p, upper, op[0], op[1], op[4], .34, white, seed=seed)
        window(p, upper, op, rng, 'lit' if rng.uniform() < .35 else 'glass', .34, GOLD_PALE, 'CN_Gold', surround=op in tall, stone=stone,
               transom=None, seed=seed, glow=LIGHT_WARM)
    door(p, upper, gdoor, rng, BLACK, .3, transom=.5, double=True, surround=stone, seed=seed, glazed=True, lit=True)
    round_moulding(p, Ru, 16.3, STRING, tint(stone, .93), seed=seed)
    # The cornice's top runs in under the dome's foot, so no ring of the tower's inside shows between them.
    round_moulding(p, Ru, top_upper, [(0, 0), (.04, .02), (.06, .09), (.12, .12), (.15, .2), (.38, .3), (.42, .36), (.45, .46), (.45, .52), (-.12, .52)],
                   tint(stone, .96), seed=seed)
    # The gold ribbed dome and its lantern.
    zd = top_upper + .52
    Rd, H = Ru - .05, 5.9
    prof = [(Rd * math.cos(t), zd + H * math.sin(t)) for t in np.linspace(0, math.radians(80), 11)]

    def gilt(v):
        a = np.arctan2(v[:, 1], v[:, 0])
        sector = np.floor((a + math.pi) / (2 * math.pi) * 16)
        return .82 + .14 * np.sin(sector * 7.31) ** 2 - .1 * np.clip(1 - (v[:, 2] - zd) / 1.2, 0, 1)
    revolve(p, prof, GOLD, 'CN_Gold', 64, mult=gilt)
    rl = prof[-1][0]
    for k in range(16):
        a = 2 * math.pi * k / 16
        pts = [((r + .06) * math.cos(a), (r + .06) * math.sin(a), z + .04 * math.sin(t)) for (r, z), t in zip(prof, np.linspace(0, math.radians(80), 11))]
        tube(p, pts, .1, GOLD_PALE, 'CN_Gold', 5, True)
    zl = prof[-1][1]
    revolve(p, [(rl + .25, zl - .05), (rl + .25, zl + .12), (1.05, zl + .12)], tint(stone, .9), 'CN_White', 24, smooth=False)
    lan = Wall((0, 0, 0), r=1.05, a0=0.0)
    LL = 2 * math.pi * 1.05
    lan_ops = [(LL * (k + .5) / 6 - .22, LL * (k + .5) / 6 + .22, zl + .35, zl + .95 + .22, zl + .95) for k in range(6)]
    wall_cells(p, lan, LL, zl + 1.45, white, openings=lan_ops, reveal=.12, v0=zl + .12, cell=.6, seed=seed + 6)
    for op in lan_ops:
        arch_head(p, lan, op[0], op[1], op[4], .12, white, seed=seed, n=6)
        wpoly(p, lan, [(a, b, .1) for a, b in outline(op[0], op[1], op[2], op[3], op[4], 0, 6)], LIGHT_BLUE, 'CN_Glow')
    round_moulding(p, 1.05, zl + 1.45, [(0, 0), (.06, .03), (.1, .1), (.12, .16), (0, .16)], tint(stone, .92), sides=24, seed=seed)
    zc = zl + 1.61
    revolve(p, [(1.05 * math.cos(t), zc + .55 * math.sin(t)) for t in np.linspace(0, math.radians(85), 6)], GOLD, 'CN_Gold', 24)
    blob(p, (0, 0, zc + .66), .12, GOLD_PALE, 'CN_Gold', 1, .02, 7)
    tube(p, [(0, 0, zc + .7), (0, 0, 30.0)], [.03, .006], GOLD, 'CN_Gold', 6, True)
    return finish(p)




def band_ring(p, centre, axis, R, width, thick, colour, slot, segs=96, mult=None, ticks=0, tick_colour=None, stones=0, rng=None):
    """A flat ring band of radius R round axis (an armillary ring, a stone ring): a rectangular section
    width along the axis and thick radially. ticks: graduation marks on its outer face; stones: split
    into that many voussoirs with their own tones and a fine joint between them."""
    c = np.asarray(centre, np.float64)
    ax = np.asarray(axis, np.float64)
    ax /= np.linalg.norm(ax)
    a, b = tk.frame(ax)
    section = [(thick / 2, -width / 2), (thick / 2, width / 2), (-thick / 2, width / 2), (-thick / 2, -width / 2)]
    pieces = stones if stones else 1
    per = segs // pieces
    for s_ in range(pieces):
        t0 = 2 * math.pi * s_ / pieces + (.004 if stones else 0)
        t1 = 2 * math.pi * (s_ + 1) / pieces - (.004 if stones else 0)
        ts = np.linspace(t0, t1, per + 1) if stones else np.linspace(0, 2 * math.pi, segs, endpoint=False)
        verts = []
        for t in ts:
            radial = math.cos(t) * a + math.sin(t) * b
            for o, h in section:
                verts.append(c + radial * (R + o) + ax * h)
        verts = np.array(verts)
        n = len(ts)
        faces = []
        for i in range(n if not stones else n - 1):
            i2 = (i + 1) % n
            for k in range(4):
                k2 = (k + 1) % 4
                faces.append([i * 4 + k, i2 * 4 + k, i2 * 4 + k2, i * 4 + k2])
        if stones:
            faces += [[0, 1, 2, 3], [(n - 1) * 4 + 3, (n - 1) * 4 + 2, (n - 1) * 4 + 1, (n - 1) * 4]]
        fixed = []
        for f in faces:
            q = verts[f]
            mid = q.mean(0) - c
            radial_part = mid - ax * np.dot(mid, ax)
            want = q.mean(0) - (c + radial_part / max(np.linalg.norm(radial_part), 1e-9) * R)
            fixed.append(f if np.dot(newell(q), want) >= 0 else f[::-1])
        tone = rng.uniform(.82, 1.0) if (stones and rng is not None) else 1.0
        cols = paint(colour, (mult(verts) if mult else np.ones(len(verts))) * tone)
        p.add(verts, fixed, cols, slot, True)
    for k in range(ticks):
        t = 2 * math.pi * k / ticks
        radial = math.cos(t) * a + math.sin(t) * b
        tangent = -math.sin(t) * a + math.cos(t) * b
        q = c + radial * (R + thick / 2 + .006)
        long = (k % 3 == 0)
        L = width * (.8 if long else .45)
        pts = [q - tangent * .008 - ax * L / 2, q + tangent * .008 - ax * L / 2, q + tangent * .008 + ax * L / 2, q - tangent * .008 + ax * L / 2]
        poly(p, pts, radial, tick_colour or colour, slot)


def orrery():
    """The Orrery at the heart of the Commons: a white stone basin (radius 6) of light-blue water over a
    black floor, a black stone plinth, and on it three gold armillary rings (for the Center, Earth and the
    First Ones' world, each carrying its world) turning round a light-blue glowing sphere; a blank gold
    plaque on the rim. The great ring stands 9 m high."""
    p = Part('SM_CN_Orrery', ALL_SLOTS)
    rng = np.random.default_rng(3400)
    seed = 3400
    stone = tint(WHITE, .97)
    age = lambda v: weather(v, seed, damp=.28, rise=.35, stain=.06)
    # The basin, its crisp parts as separate bands and its rim rolled smooth.
    for seg in ([(6.0, 0), (6.0, .1), (5.93, .14)], [(5.93, .14), (5.9, .58)], [(5.9, .58), (5.97, .62), (5.99, .69), (5.94, .76), (5.8, .8), (5.6, .8), (5.48, .76), (5.45, .69)],
                [(5.45, .69), (5.45, .12)]):
        for a_, b_ in zip(seg, seg[1:]):
            revolve(p, [a_, b_], stone, 'CN_White', 72, smooth=True, mult=age)
    revolve(p, [(5.45, .12), (1.7, .12)], CHARCOAL, 'CN_Black', 72, smooth=False)
    revolve(p, [(5.45, .5), (1.74, .5)], tint(BLUE_PALE, .95), 'CN_Glass', 72, smooth=False)
    # The plaque, blank gold on a stone mount, set on the rim facing -x.
    bevel_box(p, (-5.7, 0, .84), (.1, .5, .05), tint(IVORY, .9), 'CN_White', .01)
    bevel_box(p, (-5.7, 0, .9), (.08, .42, .012), GOLD, 'CN_Gold', .004, shade=lambda v: np.full(len(v), .9))
    # Black stone plinth: a stepped octagon, a tapering shaft with gold bands, a capital.
    blk = tint(BLACK, 1.0)
    for r, z0, z1 in ((1.7, .12, .45), (1.35, .45, .75)):
        revolve(p, [(r, z0), (r, z1)], blk, 'CN_Black', 8, smooth=False, start=math.pi / 8)
        revolve(p, [(r, z1), (r * .8, z1)], blk, 'CN_Black', 8, smooth=False, start=math.pi / 8)
    revolve(p, [(1.0, .75), (.78, 3.0)], tint(SLATE, .9), 'CN_Black', 8, smooth=False, start=math.pi / 8)
    for z in (1.3, 2.6):
        revolve(p, [(.97 - (z - .75) * .098 + .03, z), (.97 - (z - .75) * .098 + .03, z + .1)], GOLD, 'CN_Gold', 8, smooth=False, start=math.pi / 8)
    revolve(p, [(.78, 3.0), (1.05, 3.2), (1.05, 3.35), (0, 3.35)], blk, 'CN_Black', 8, smooth=False, start=math.pi / 8)
    # The armillary: a meridian ring in a gold cradle, two tilted rings, the polar axis and the worlds.
    C = np.array([0, 0, 5.0])
    cradle = [(-.55, 0, 3.35), (-.3, 0, 3.9), (0, 0, 1.2 + 3.95 - 3.95 + 3.9 - 2.85), (.3, 0, 3.9), (.55, 0, 3.35)]
    tube(p, [cradle[0], cradle[1], cradle[3], cradle[4]], .06, GOLD_DEEP, 'CN_Gold', 8, True)
    rings = ((np.array([0., 1, 0]), 3.95, GOLD, WHITE_PURE, 'CN_Lacquer'),
             (rotation((1, 0, 0), math.radians(66)) @ np.array([0., 0, 1]), 3.4, GOLD_PALE, BLUE, 'CN_Lacquer'),
             (rotation((0, 1, 0), math.radians(23.4)) @ np.array([0., 0, 1]), 2.85, GOLD, GOLD_PALE, 'CN_Gold'))
    for k, (axis, R, metal, world, world_slot) in enumerate(rings):
        band_ring(p, C, axis, R, .2 - .03 * k, .055, metal, 'CN_Gold', 120, ticks=72, tick_colour=tint(metal, .7))
        a, b = tk.frame(axis)
        t = (.6, 2.3, 4.2)[k]
        q = C + (math.cos(t) * a + math.sin(t) * b) * R
        blob(p, q, .3 - .03 * k, world, world_slot, 2, .01, seed + k)
        for s_ in (-1, 1):
            tube(p, [C + axis * 0 + (math.cos(t + s_ * .12) * a + math.sin(t + s_ * .12) * b) * R, q], .025, metal, 'CN_Gold', 5, True)
    polar = rotation((0, 1, 0), math.radians(23.4)) @ np.array([0., 0, 1])
    tube(p, [C - polar * 3.95, C + polar * 3.95], .045, GOLD_DEEP, 'CN_Gold', 8, True)
    for s_ in (-1, 1):
        blob(p, C + polar * 3.95 * s_, .09, GOLD, 'CN_Gold', 1, .02, seed + 5)
        blob(p, C + np.array([0, 0, 3.95]) * s_, .11, GOLD, 'CN_Gold', 1, .02, seed + 6)
    # At .35 of full glow: at full strength the sphere blew out to white and lost its light blue.
    blob(p, C, .85, tint(LIGHT_BLUE, .35), 'CN_Glow', 3, 0.0, seed)
    band_ring(p, C, polar, .98, .06, .03, GOLD_PALE, 'CN_Gold', 48)
    return finish(p)


def shrine():
    """The shrine of the First One listeners (radius 4, 5 tall): a round dais of two steps with six low
    seat stones, and at its heart a ring of white voussoir stones standing on black stone, a light-blue
    crystal hanging in it with light in its heart and a band of light round the ring's inner face."""
    p = Part('SM_CN_Shrine', ALL_SLOTS)
    rng = np.random.default_rng(3500)
    seed = 3500
    stone = tint(WHITE, .97)
    for k, (r, z0, z1) in enumerate(((4.0, 0, .18), (3.65, .18, .36))):
        revolve(p, [(r, z0), (r, z1)], tint(stone, .92 - .03 * k), 'CN_White', 64, mult=lambda v: weather(v, seed + k, damp=.3, rise=.3))
        revolve(p, [(r, z1), (r - .35 if k == 0 else 0.4, z1)], tint(stone, .95), 'CN_White', 64, smooth=False, mult=lambda v: weather(v, seed + k, damp=.1))
    polar_paving(p, .4, 3.3, 0, 2 * math.pi, .365, rng, IVORY, ring=.72, slab=.9)
    for k in range(6):
        a = 2 * math.pi * (k + .5) / 6
        cx, cy = 2.9 * math.cos(a), 2.9 * math.sin(a)
        bevel_box(p, (cx, cy, .36 + .21), (.24, .5, .21), tint(IVORY, rng.uniform(.82, .95)), 'CN_White', .05, math.degrees(a),
                  shade=shader(IVORY, lambda v: weather(v, seed + k, damp=.2, rise=.3)))
    # The ring stands in the x = 0 plane facing +x, on a black stone foot.
    bevel_box(p, (0, 0, .36 + .3), (.4, .9, .3), BLACK, 'CN_Black', .04)
    C = np.array([0, 0, 2.62])
    band_ring(p, C, (1, 0, 0), 2.02, .5, .52, stone, 'CN_White', 96, stones=16, rng=rng, mult=lambda v: weather(v, seed, damp=.1, stain=.06))
    band_ring(p, C, (1, 0, 0), 1.755, .08, .012, LIGHT_BLUE, 'CN_Glow', 96)
    # The crystal: a long bipyramid with a cluster of smaller ones, a glowing heart.
    tk.prism(p, C, C + np.array([0, 0, 1.25]), .32, tint(BLUE_PALE, .95), 'CN_Glass', 6, .45)
    tk.prism(p, C, C - np.array([0, 0, 1.05]), .32, tint(BLUE_PALE, .95), 'CN_Glass', 6, .5)
    for k in range(5):
        a = 2 * math.pi * k / 5 + .3
        d = np.array([.2 * math.cos(a), .45 * math.sin(a), .55 * (1 if k % 2 else -1)])
        tk.prism(p, C + d * .3, C + d * (1.15 + .1 * k), .1, tint(BLUE_ICE, .9), 'CN_Glass', 5, .4)
    blob(p, C, .2, LIGHT_BLUE, 'CN_Glow', 2, 0.0, seed)
    return finish(p)


def ibeam(p, a, b, depth, width, rng, colour=CHARCOAL, flange=.018, web=.012, up=None):
    """A steel I-section from a to b: two flanges and a web (depth measured along up)."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    ax = b - a
    L = np.linalg.norm(ax)
    ax /= L
    upv = np.asarray(up if up is not None else (UP if abs(ax[2]) < .9 else (1, 0, 0)), np.float64)
    upv = upv - ax * np.dot(upv, ax)
    upv /= np.linalg.norm(upv)
    side = np.cross(ax, upv)
    steel = tint(colour, rng.uniform(.8, 1.0))

    def slab(c_off, half_up, half_side):
        pts = []
        for zb in (0, 1):
            for yb in (0, 1):
                for xb in (0, 1):
                    q = (a if xb == 0 else b) + upv * (c_off + (half_up if zb else -half_up)) + side * (half_side if yb else -half_side)
                    pts.append(q)
        hexa(p, pts, steel, 'CN_Metal')
    slab(depth / 2 - flange / 2, flange / 2, width / 2)
    slab(-depth / 2 + flange / 2, flange / 2, width / 2)
    slab(0, depth / 2 - flange, web / 2)


def rivets(p, pts, normal, rng, r=.012, colour=CHARCOAL):
    """Round rivet heads on a plate."""
    normal = np.asarray(normal, np.float64)
    for q in pts:
        tk.cylinder(p, np.asarray(q) - normal * .002, r, .01, colour, 'CN_Metal', 6, r * .6) if abs(normal[2]) > .9 else \
            tube(p, [np.asarray(q), np.asarray(q) + normal * .01], [r, r * .6], colour, 'CN_Metal', 6, True)


def panel_wall(p, w, length, height, rng, colour=WHITE_PURE, panel=1.0, seed=0, slot='CN_White', v0=0.0):
    """Insulated cladding: white panels with fine dark seams between them and a pressed rib up each one."""
    n = max(1, int(round(length / panel)))
    pw = length / n
    for k in range(n):
        a, b = k * pw + .008, (k + 1) * pw - .008
        tone = rng.uniform(.88, 1.0)
        for (ua, ub, d) in ((a, (a + b) / 2 - .03, 0), ((a + b) / 2 - .03, (a + b) / 2 + .03, -.018), ((a + b) / 2 + .03, b, 0)):
            pts = [(ua, v0, d), (ub, v0, d), (ub, height, d), (ua, height, d)]
            xyz = w.at(np.array(pts)[:, 0], np.array(pts)[:, 1], np.array(pts)[:, 2])
            wpoly(p, w, pts, paint(colour, weather(xyz, seed + k, damp=.3, rise=.6, stain=.05) * tone), slot)
        for ua in ((a + b) / 2 - .03, (a + b) / 2 + .03):
            wpoly(p, w, [(ua, v0, 0), (ua, height, 0), (ua, height, -.018), (ua, v0, -.018)], tint(colour, tone * .9), slot) if False else None
    wpoly(p, w, [(0, v0, .006), (length, v0, .006), (length, height, .006), (0, height, .006)], SLATE, 'CN_Black')


def mendery():
    """The Mendery, where the Commons' robots are mended (8 x 10 x 6, open toward +x): a black steel
    portal-frame shed with white cladding, a ribbed roof with a light-blue skylight along its ridge, a
    concrete floor with red and white safety edging, workbenches with vices and tools, a pegboard and
    shelves, pendant lights, and an overhead gantry whose hoist holds a robot torso in its sling."""
    p = Part('SM_CN_Mendery', ALL_SLOTS)
    rng = np.random.default_rng(3600)
    seed = 3600
    X0, X1, Y0, Y1 = -3.9, 3.9, -4.85, 4.85
    eave, ridge = 4.5, 5.75
    # Floor: a concrete slab in poured bays, safety edging at the open front.
    bevel_box(p, (0, 0, .07), (4.0, 5.0, .07), tint(ASH, 1.0), 'CN_White', .03)
    paving(p, X0, X1 - .35, Y0, Y1, .143, 2.4, rng, tint(WHITE, .7), joint=.01, seed=seed, under=SLATE)
    for k in range(20):
        ya, yb = Y0 + (Y1 - Y0) * k / 20, Y0 + (Y1 - Y0) * (k + 1) / 20
        p.add([(X1 - .33, ya, .145), (X1 - .05, ya, .145), (X1 - .05, yb, .145), (X1 - .33, yb, .145)], [[0, 1, 2, 3]],
              tint(RED if k % 2 else WHITE_PURE, .9), 'CN_Lacquer', False)
    # Frames: columns and rafters (I-sections), base plates with rivets, knee braces, purlins.
    frames = (-3.75, -1.25, 1.25, 3.75)
    for fx in frames:
        for sy in (-1, 1):
            y = sy * 4.75
            ibeam(p, (fx, y, .14), (fx, y, eave), .22, .16, rng, up=(0, 1, 0))
            bevel_box(p, (fx, y, .16), (.16, .14, .02), CHARCOAL, 'CN_Metal', .005)
            rivets(p, [(fx + dx, y + dy, .18) for dx in (-.1, .1) for dy in (-.08, .08)], UP, rng)
            ibeam(p, (fx, y, eave), (fx, 0, ridge), .24, .14, rng, up=(0, -sy * .2, 1))
            tube(p, [(fx, y * .99, eave - .7), (fx, y * .8, eave + .17)], .03, CHARCOAL, 'CN_Metal', 6, True)
    for k in range(5):
        t = k / 4
        for sy in (-1, 1):
            y, z = sy * 4.75 * (1 - t), eave + (ridge - eave) * t + .14
            ibeam(p, (X0 - .05, y, z), (X1 + .05, y, z), .12, .07, rng, up=(0, -sy * .2, 1))
    # Roof: ribbed white sheet on both slopes, a skylight of light-blue glass along the ridge.
    for sy in (-1, 1):
        n = 30
        verts, faces = [], []
        for i in range(n + 1):
            t = i / n
            y = sy * (4.95 - 4.95 * t * .92)
            z = eave + .22 + (ridge - eave) * (1 - abs(y) / 4.75) + (.035 if i % 2 else 0)
            verts += [(X0 - .15, y, z), (X1 + .15, y, z)]
        for i in range(n):
            faces.append([2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2])
        verts = np.array(verts)
        faces = [f if newell(verts[f])[2] >= 0 else f[::-1] for f in faces]
        p.add(verts, faces, paint(WHITE, weather(verts, seed, damp=0, stain=.1) * .92), 'CN_White', False)
        p.add(verts - (0, 0, .02), [f[::-1] for f in faces], tint(ASH, .9), 'CN_White', False)
        yy = sy * 4.95 * .08
        zz = ridge + .22 + .035
        p.add([(X0 - .15, 0, zz + .12), (X1 + .15, 0, zz + .12), (X1 + .15, yy, zz), (X0 - .15, yy, zz)], [[0, 1, 2, 3] if sy > 0 else [3, 2, 1, 0]],
              BLUE_PALE, 'CN_Glass', False)
    # Cladding on the back and the sides (the sides stop short of the open front).
    panel_wall(p, Wall((X0 - .1, Y1 - .05, 0), (-1, 0, 0)), Y1 - Y0 - .1, eave + .15, rng, seed=seed, v0=.14)
    panel_wall(p, Wall((X1 - 1.1, Y1 + .05, 0), (0, 1, 0)), X1 - 1.1 - X0 + .1, eave + .15, rng, seed=seed + 1, v0=.14)
    panel_wall(p, Wall((X0 - .1, Y0 - .05, 0), (0, -1, 0)), X1 - 1.1 - X0 + .1, eave + .15, rng, seed=seed + 2, v0=.14)
    for sy in (-1, 1):
        for y_off, z0, z1 in ((0, eave + .15, eave + .3),):
            pass
        gable = [(X0 - .1, sy * 4.9, eave + .15), (X0 - .1, 0, ridge + .2), (X0 - .1, sy * .02, eave + .15)]
    for x in (X0 - .1,):
        poly(p, [(x, -4.9, eave + .15), (x, 4.9, eave + .15), (x, 0, ridge + .2)], (-1, 0, 0), tint(WHITE_PURE, .85), 'CN_White')
    # Inside on the cladding: inner faces so the shed reads from within.
    for (o, n, L) in (((X0 - .08, Y0 + .05, 0), (1, 0, 0), Y1 - Y0 - .1), ((X0 - .1, Y1 - .03, 0), (0, -1, 0), X1 - 1.0 - X0),
                      ((X1 - 1.1, Y0 + .03, 0), (0, 1, 0), X1 - 1.0 - X0)):
        wl = Wall(o, n)
        wpoly(p, wl, [(0, .14, 0), (L, .14, 0), (L, eave + .15, 0), (0, eave + .15, 0)], paint(WHITE, [.7, .72, .8, .78]), 'CN_White')
    # Workbenches with vices, tools and a robot arm under repair.
    for sy in (-1, 1):
        y = sy * 3.9
        bevel_box(p, (-.6, y, .99), (1.6, .45, .045), tint(ASH, .8), 'CN_Metal', .01)
        for dx in (-1.5, 1.3):
            for dy in (-.38, .38):
                tube(p, [(-.6 + dx, y + dy, .14), (-.6 + dx, y + dy, .95)], .028, CHARCOAL, 'CN_Metal', 4, True)
        bevel_box(p, (-.6, y, .3), (1.55, .4, .015), tint(SLATE, .9), 'CN_Metal', .005)
        bevel_box(p, (.5, y - sy * .25, 1.12), (.12, .07, .09), CHARCOAL, 'CN_Metal', .01)
        tube(p, [(.5, y - sy * .25 - .1, 1.15), (.5, y - sy * .25 + .1, 1.15)], .012, GOLD_DEEP, 'CN_Gold', 6, True)
        for k in range(4):
            bevel_box(p, (-1.6 + .35 * k, y + rng.uniform(-.2, .2), 1.06), (rng.uniform(.04, .12), rng.uniform(.02, .06), .02),
                      CHARCOAL if k % 2 else GOLD_DEEP, 'CN_Metal' if k % 2 else 'CN_Gold', .004)
    arm = [(-1.1, -3.85, 1.08), (-.75, -3.75, 1.25), (-.35, -3.8, 1.2)]
    tube(p, arm, .06, WHITE_PURE, 'CN_Lacquer', 8, True)
    for q in arm:
        blob(p, q, .075, CHARCOAL, 'CN_Metal', 1, .02, 3)
    # Pegboard with tool outlines and shelves of crates on the back wall.
    bevel_box(p, (X0 + .05, -1.2, 1.9), (.03, 1.3, .7), CHARCOAL, 'CN_Black', .01)
    for k in range(12):
        bevel_box(p, (X0 + .09, -2.3 + .2 * k, 1.9 + rng.uniform(-.4, .4)), (.012, .025, rng.uniform(.1, .25)),
                  GOLD_DEEP if k % 3 == 0 else SLATE, 'CN_Gold' if k % 3 == 0 else 'CN_Metal', .004)
    for z in (.6, 1.3, 2.0):
        bevel_box(p, (X0 + .35, 2.4, z), (.3, 1.2, .025), tint(CHARCOAL, .9), 'CN_Metal', .006)
        for k in range(3):
            if rng.uniform() < .8:
                c = (WHITE_PURE, BLACK, RED)[int(rng.integers(0, 3))]
                bevel_box(p, (X0 + .35, 1.5 + .6 * k + rng.uniform(-.05, .05), z + .025 + .17), (.24, .26, .17), tint(c, rng.uniform(.8, 1.0)), 'CN_Lacquer', .012)
    for y in (1.2, 3.6):
        tube(p, [(X0 + .07, y, .14), (X0 + .07, y, 2.1)], .02, CHARCOAL, 'CN_Metal', 4, True)
    # The gantry: runway beams on brackets, a bridge, the hoist and its chain, a robot torso in a sling.
    for sy in (-1, 1):
        ibeam(p, (X0 + .15, sy * 4.45, 4.05), (X1 - .15, sy * 4.45, 4.05), .26, .14, rng)
        for fx in frames:
            bevel_box(p, (fx, sy * 4.6, 3.88), (.08, .17, .05), CHARCOAL, 'CN_Metal', .005)
    bx = .6
    ibeam(p, (bx, -4.45, 4.3), (bx, 4.45, 4.3), .3, .16, rng)
    bevel_box(p, (bx, -.3, 4.0), (.16, .2, .14), tint(RED, .8), 'CN_Lacquer', .02)
    chain = [(bx, -.3, 3.86), (bx, -.3, 2.95)]
    for k in range(10):
        z = 3.86 - k * .09
        tk.torus(p, (bx, -.3, z), .03, .007, CHARCOAL, 'CN_Metal', 8, 4, axis='x' if k % 2 else 'y')
    tube(p, [(bx, -.3, 2.95), (bx, -.3, 2.85), (bx + .08, -.3, 2.78), (bx + .02, -.3, 2.72)], .02, GOLD, 'CN_Gold', 6, True)
    blob(p, (bx, -.3, 2.25), (.38, .3, .48), WHITE_PURE, 'CN_Lacquer', 2, .05, seed, squash=(1, 1, 1))
    blob(p, (bx, -.3, 2.75), .16, CHARCOAL, 'CN_Metal', 1, .03, seed + 1)
    for s_ in (-1, 1):
        tube(p, [(bx + .02, -.3, 2.75), (bx + .3 * s_, -.3, 2.45), (bx + .32 * s_, -.3, 1.95)], .02, BLACK, 'CN_Cloth', 4, False)
        blob(p, (bx + .45 * s_, -.3, 2.35), (.1, .1, .12), CHARCOAL, 'CN_Metal', 1, .03, seed + 2)
    for k, (lx, ly) in enumerate(((-2.5, 0), (0, 0), (2.5, 0))):
        tube(p, [(lx, ly, ridge - .05), (lx, ly, 3.55)], .006, CHARCOAL, 'CN_Metal', 4, False)
        revolve(p, [(.04, 3.55), (.3, 3.42), (.32, 3.38)], CHARCOAL, 'CN_Metal', 12, (lx, ly, 0))
        revolve(p, [(.29, 3.4), (0.02, 3.4)], LIGHT_WARM, 'CN_Glow', 12, (lx, ly, 0), smooth=False)
    return finish(p)


# ---------------------------------------------------------------- shared pieces for street furniture and stonework

def bevel_block(c, h, bevel, segs=1, bottom=True):
    """bevel_box's shape (chamfered edges and corners) as vertices and outward faces, cut into segs lengths along
    local y so a bend can curve it: a warp moves only vertices, so a block of one length keeps flat faces, and a
    kerb stone bent round a circle would stand off it in a chord. bottom=False leaves out the faces under the
    block, for stones set into the ground."""
    c, h = np.asarray(c, np.float64), np.asarray(h, np.float64)
    hx, hy, hz = h
    ex, ey, ez = np.maximum(np.minimum(bevel, h * .45), 1e-4)
    # The section round local y (x, z), its chamfers included, and each end face: the section inset by the bevel.
    sec = [(-hx + ex, -hz), (hx - ex, -hz), (hx, -hz + ez), (hx, hz - ez), (hx - ex, hz), (-hx + ex, hz), (-hx, hz - ez), (-hx, -hz + ez)]
    end = [(-hx + ex, -hz + ez), (hx - ex, -hz + ez), (hx - ex, hz - ez), (-hx + ex, hz - ez)]
    corner = (0, 1, 1, 2, 2, 3, 3, 0)  # the end face corner each section point chamfers into
    ys = np.linspace(-hy + ey, hy - ey, segs + 1)
    verts = [(x, y, z) for y in ys for x, z in sec]
    faces = [[j * 8 + i, j * 8 + (i + 1) % 8, (j + 1) * 8 + (i + 1) % 8, (j + 1) * 8 + i] for j in range(segs) for i in range(8)]
    for ring, y in ((0, -hy), (segs, hy)):
        base = len(verts)
        verts += [(x, y, z) for x, z in end]
        for i in range(8):
            a, b = ring * 8 + i, ring * 8 + (i + 1) % 8
            fa, fb = base + corner[i], base + corner[(i + 1) % 8]
            faces.append([a, b, fb, fa] if fa != fb else [a, b, fa])
        faces.append([base, base + 1, base + 2, base + 3])
    verts = np.array(verts)
    if not bottom:
        faces = [f for f in faces if verts[f, 2].max() > -hz + ez + 1e-9]
    # The block is convex round its centre (the local origin), so a face's front is the side away from it.
    faces = [f if np.dot(newell(verts[f]), verts[f].mean(0)) > 0 else f[::-1] for f in faces]
    return verts + c, faces


def bent_box(p, c, h, colour, slot, warp, bevel=.03, mult=None, segs=1, bottom=True):
    """A bevelled block built at c (half extents h) in a local frame and then bent by warp(points) -> points:
    kerb and coping stones round a circle, voussoirs round an arch, slats on a raked frame. Curved stonework so
    keeps the chamfered joints that make masonry read; segs cuts the block along local y so it follows a bend
    (bevel_block). warp must keep orientation (a bend or a rotation, never a mirror), so the faces stay wound
    outward; mult(points) weathers the bent block in world space."""
    verts, faces = bevel_block(c, h, bevel, segs, bottom)
    v = warp(verts)
    p.add(v, faces, paint(colour, mult(v)) if mult is not None else colour, slot, False)


def polar(a_c, r_ref, c=(0.0, 0.0)):
    """A bent_box warp round a circle: local x is the radius, local y the distance along the circle (at r_ref)
    from angle a_c, z stays up. Stones built end to end in y meet on radial joints."""
    def warp(v):
        ang = a_c + v[:, 1] / r_ref
        return np.stack([c[0] + v[:, 0] * np.cos(ang), c[1] + v[:, 0] * np.sin(ang), v[:, 2]], 1)
    return warp


def turned(R, t):
    """A bent_box warp: the proper rotation R about the local origin, then a move to t."""
    R, t = np.asarray(R, np.float64), np.asarray(t, np.float64)
    return lambda v: v @ R.T + t


def along(a, b):
    """The rotation taking local x to the direction a -> b (local z stays as near up as it can), and the length."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    d = b - a
    L = float(np.linalg.norm(d))
    d = d / L
    s = np.cross(UP, d) if abs(d[2]) < .99 else np.array([0., 1., 0.])
    s /= np.linalg.norm(s)
    return np.stack([d, s, np.cross(d, s)], 1), L


def timber(p, a, b, w, h, colour, slot, bevel=.008, mult=None):
    """A squared beam, rafter or brace from a to b, w wide and h deep, with chamfered arrises."""
    R, L = along(a, b)
    bent_box(p, (0, 0, 0), (L / 2, w / 2, h / 2), colour, slot, turned(R, (np.asarray(a, np.float64) + b) / 2), bevel, mult)


def fluted(p, profile, flutes, colour, slot, depth=.07, c=(0, 0, 0)):
    """A fluted shaft: revolve(profile) with rounded flutes cut round it (four samples a flute)."""
    ang = np.linspace(0, 2 * math.pi, flutes * 4, endpoint=False)
    wob = 1 - depth * .5 * (1 + np.cos(ang * flutes))
    n = len(ang)
    verts = np.concatenate([np.stack([np.cos(ang) * r * wob, np.sin(ang) * r * wob, np.full(n, z)], 1) for r, z in profile]) + np.asarray(c, np.float64)
    faces = [[i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j] for i in range(len(profile) - 1) for j in range(n)]
    return p.add(verts, faces, colour, slot, True)


def blades(p, base, rng, count, length=(.25, .55), spread=.15, lean=(0.0, 0.0), colours=(GOLD_GRASS, GOLD_STRAW), width=.011, droop=.35):
    """A tuft of grass: curved blades (three triangles each, two-sided foliage) rising from base and arching
    over; lean (x, y) tips the whole tuft, as grass spilling over a kerb does."""
    base = np.asarray(base, np.float64)
    verts, faces, cols = [], [], []
    for _ in range(count):
        a = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(*length)
        b0 = base + np.array([rng.normal(0, spread * .3), rng.normal(0, spread * .3), 0])
        out = np.array([math.cos(a) * spread + lean[0], math.sin(a) * spread + lean[1], 0])
        mid = b0 + out * L * .5 + UP * L * .62
        tip = b0 + out * L * (1.1 + droop) + UP * L * (.95 - droop)
        side = np.array([-math.sin(a), math.cos(a), 0]) * width
        k = len(verts)
        verts += [b0 - side, b0 + side, mid + side * .7, mid - side * .7, tip]
        faces += [[k, k + 1, k + 2], [k, k + 2, k + 3], [k + 3, k + 2, k + 4]]
        c = colours[int(rng.integers(0, len(colours)))]
        tone = rng.uniform(.8, 1.0)
        cols += [tint(c, tone * .78)] * 2 + [tint(c, tone)] * 3
    p.add(np.array(verts), faces, np.array(cols), 'CN_Leaf', False)


# ---------------------------------------------------------------- street furniture

def bench():
    """A town bench (0.6 x 2 x 0.9) facing +x: three black cast-iron frames (two ends with scrolled armrests and a
    middle bearer), each a raked back leg and a front leg on small feet, carrying red-painted seat and back slats
    whose bolt heads show over every frame. The seat falls a little toward the back, as a sitter wants."""
    p = Part('SM_CN_Bench', ALL_SLOTS)
    rng = np.random.default_rng(3700)
    iron = tint(CHARCOAL, rng.uniform(.75, .95))

    def seat(x):
        return .455 - .05 * (.24 - x) / .46
    back = lambda s: np.array([-.175 - .11 * s, 0, seat(-.175) - .02 + (.895 - seat(-.175) + .02) * s])
    phi = math.atan2(.11, .895 - seat(-.175) + .02)
    nrm = np.array([math.cos(phi), 0, math.sin(phi)])
    for y in (-.86, 0.0, .86):
        end = abs(y) > .1
        r = .019 if end else .016
        tube(p, tk.bezier((-.215, y, .012), (-.19, y, .2), (-.17, y, .38), (-.175, y, seat(-.175) - .02), 6), r, iron, 'CN_Metal', 6, True)
        tube(p, [back(0) + (0, y, 0), back(.5) + (0, y, 0), back(1.0) + (0, y, 0)], r * .9, iron, 'CN_Metal', 6, True)
        tube(p, tk.bezier((.235, y, .012), (.215, y, .16), (.2, y, .3), (.205, y, seat(.205) - .02), 5), r, iron, 'CN_Metal', 6, True)
        tube(p, [(.255, y, seat(.255) - .027), (-.2, y, seat(-.2) - .027)], .015, iron, 'CN_Metal', 6, True)
        for fx in (-.215, .235):
            bevel_box(p, (fx, y, .009), (.042, .028, .009), iron, 'CN_Metal', .004)
        if end:
            tube(p, tk.bezier((-.2, y, .655), (-.02, y, .665), (.17, y, .67), (.255, y, .615), 7), .017, iron, 'CN_Metal', 6, True)
            curl = [(.262 + .028 * math.cos(t), y, .585 + .028 * math.sin(t)) for t in np.linspace(1.2, 1.2 - 1.8 * math.pi, 9)]
            tube(p, curl, .009, iron, 'CN_Metal', 5, True)
            tube(p, [(.205, y, seat(.205) - .02), (.21, y, .66)], .014, iron, 'CN_Metal', 6, True)
    bolts, back_bolts = [], []
    for k, x in enumerate(np.linspace(-.15, .21, 5)):
        c = tint(RED, rng.uniform(.72, .95))
        bevel_box(p, (x, 0, seat(x) + .002), (.033, .97, .014), c, 'CN_Red', .006, shade=shader(c, lambda v: 1 - .08 * (np.abs(v[:, 1]) > .9)))
        bolts += [(x, y, seat(x) + .016) for y in (-.86, 0.0, .86)]
    for s in (.3, .58, .86):
        q = back(s) + nrm * (.017 + .012)
        c = tint(RED, rng.uniform(.72, .95))
        bent_box(p, (0, 0, 0), (.011, .97, .043), c, 'CN_Red', turned(rotation((0, 1, 0), -phi), q), .006)
        back_bolts += [q + nrm * .011 + (0, y, 0) for y in (-.86, 0.0, .86)]  # the middle bearer's back leg too
    rivets(p, bolts, UP, rng, r=.008)
    rivets(p, back_bolts, nrm, rng, r=.008)
    return finish(p)


def planter():
    """A plaza planter (1 x 2 x 1): a white limestone trough on a plinth, panels of light-blue and white glazed tile
    in raised stone frames on its four faces, a moulded rim, black soil, and a clipped white shrub with red
    geraniums at its ends and gold grass spilling over the rim."""
    p = Part('SM_CN_Planter', ALL_SLOTS)
    rng = np.random.default_rng(3710)
    seed = 3710
    st = tint(IVORY, rng.uniform(.9, .97))
    age = lambda v: weather(v, seed, damp=.3, rise=.25, stain=.06)
    hx, hy, top = .44, .94, .62
    bevel_box(p, (0, 0, .055), (hx + .05, hy + .05, .055), tint(st, .9), 'CN_White', .02, shade=shader(st, age))
    bevel_box(p, (0, 0, (top + .11) / 2), (hx, hy, (top - .11) / 2), st, 'CN_White', .012, shade=shader(st, age))
    pts, dirs = rect_ring(0, 0, hx, hy, .5)
    pts[:, 2] = top
    sweep3(p, pts, dirs, UP, [(-.09, 0), (.03, 0), (.045, .015), (.045, .055), (.03, .07), (-.09, .07), (-.09, 0)], tint(st, .97), 'CN_White',
           mult=lambda v: weather(v, seed + 1, damp=0, stain=.06))
    soil = [(-hx + .088, -hy + .088, top + .035), (hx - .088, -hy + .088, top + .035), (hx - .088, hy - .088, top + .035), (-hx + .088, hy - .088, top + .035)]
    p.add(soil, [[0, 1, 2, 3]], paint(CHARCOAL, [.6, .9, .7, 1.0]), 'CN_Black', False)
    for name, (w, L) in house_walls(-hx, hx, -hy, hy).items():
        m = .13
        u0, u1, v0, v1 = m, L - m, .2, .5
        wsweep(p, w, rect_path(u0, u1, v0, v1), [(.04, 0), (.04, .012), (.028, .022), (0, .022), (0, 0)], tint(st, .95), 'CN_White')
        nu = max(2, int(round((u1 - u0) / .1)))
        tu, tv = (u1 - u0) / nu, (v1 - v0) / 3
        for i in range(nu):
            for j in range(3):
                edge = i in (0, nu - 1) or j in (0, 2)
                c = BLUE if edge else (BLUE_PALE if (i + j) % 2 else WHITE_PURE)
                a, b = u0 + i * tu + .003, v0 + j * tv + .003
                wpoly(p, w, [(a, b, -.005), (a + tu - .006, b, -.005), (a + tu - .006, b + tv - .006, -.005), (a, b + tv - .006, -.005)],
                      tint(c, rng.uniform(.86, 1.0)), 'CN_Blue')
        wpoly(p, w, [(u0, v0, -.0015), (u1, v0, -.0015), (u1, v1, -.0015), (u0, v1, -.0015)], tint(WHITE, .62), 'CN_White')
    # The clipped shrub: a shadowed core under a skin of small leaves that comes down to the soil, so it reads as one
    # mass (leaves alone, all above 0.8 m, read as confetti floating over the soil).
    blob(p, (0, 0, .79), (.2, .55, .16), tint(WHITE, .45), 'CN_Leaf', 2, .08, seed + 2)
    leaf_cloud(p, [(0, -.4, .8), (0, 0, .83), (0, .4, .8), (0, -.2, .78), (0, .2, .78)], (.27, .27, .19), 900, rng, (WHITE_PURE, WHITE_COOL, WHITE),
               size=(.045, .08), up_bias=.35)
    for sy in (-1, 1):
        leaf_cloud(p, [(rng.uniform(-.15, .15), sy * .74, .72)], (.15, .12, .08), 90, rng, (RED_DEEP, RED_DEEP, RED, RED_BRIGHT), size=(.04, .07), up_bias=.6)
    for sx in (-1, 1):
        for y in np.linspace(-.7, .7, 5):
            blades(p, (sx * .3, y + rng.uniform(-.08, .08), top + .03), rng, 7, (.2, .34), .1, (sx * .22, 0), droop=.55)
    return finish(p)


def lamp():
    """A street lamp 4.5 m tall: a white stone plinth, a black cast-iron base and fluted column with gold collars,
    a ladder bar, and a hexagonal lantern of gold frames and glass round a glowing mantle under a black cap, vent
    crown and gold finial. It is symmetric about its axis, because the level build hangs its light 35 cm under
    the top of the bounds at their centre (physis_conclave_tools.lamp_lights): 4.15 m, inside the glass and just
    over the mantle, which stops short of it so the shadow-casting mantle never closes round the light."""
    p = Part('SM_CN_Lamp', ALL_SLOTS)
    rng = np.random.default_rng(3730)
    seed = 3730
    st = tint(IVORY, .92)
    bevel_box(p, (0, 0, .2), (.26, .26, .2), st, 'CN_White', .025, shade=shader(st, lambda v: weather(v, seed, damp=.35, rise=.2)))
    ring_moulding(p, -.26, .26, -.26, .26, .34, [(0, 0), (.03, .01), (.04, .035), (.02, .06), (0, .06)], tint(st, .96), seed=seed, step=.6)
    bevel_box(p, (0, 0, .425), (.21, .21, .025), tint(st, .9), 'CN_White', .01)
    iron = tint(CHARCOAL, rng.uniform(.8, 1.0))
    revolve(p, [(.16, .45), (.16, .53), (.125, .58), (.105, .74), (.14, .78), (.14, .82), (.08, .9)], iron, 'CN_Metal', 16)
    fluted(p, [(.074, .89), (.068, 1.56), (.062, 2.4), (.056, 3.25)], 8, iron, 'CN_Metal')
    revolve(p, [(.074, 1.52), (.086, 1.56), (.086, 1.6), (.072, 1.64)], GOLD_PALE, 'CN_Gold', 16)
    revolve(p, [(.06, 3.22), (.084, 3.27), (.084, 3.33), (.058, 3.39)], GOLD_PALE, 'CN_Gold', 16)
    revolve(p, [(.056, 3.38), (.046, 3.58), (.07, 3.64), (.12, 3.7), (.165, 3.735), (.165, 3.75)], iron, 'CN_Metal', 16)
    # The ladder bar the lamplighter leans his ladder on, with scroll braces, both sides alike.
    tube(p, [(0, -.38, 3.12), (0, .38, 3.12)], .016, iron, 'CN_Metal', 6, True)
    for s in (-1, 1):
        blob(p, (0, s * .4, 3.12), .028, GOLD, 'CN_Gold', 1, .02, seed + s)
        tube(p, tk.bezier((0, s * .05, 2.86), (0, s * .1, 3.02), (0, s * .2, 3.1), (0, s * .3, 3.12), 6), .01, iron, 'CN_Metal', 5, False)
    # The lantern: gold frame, six panes of glass, the mantle glowing on its burner.
    revolve(p, [(.16, 3.75), (.185, 3.76), (.185, 3.79), (.165, 3.8)], GOLD, 'CN_Gold', 6, smooth=False, start=math.pi / 6)
    revolve(p, [(.165, 3.79), (.226, 4.22)], tint(BLUE_PALE, .95), 'CN_Glass', 6, smooth=False, start=math.pi / 6)
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        tube(p, [(.168 * math.cos(a), .168 * math.sin(a), 3.79), (.229 * math.cos(a), .229 * math.sin(a), 4.22)], .009, GOLD_PALE, 'CN_Gold', 4, False)
    revolve(p, [(.226, 4.21), (.24, 4.22), (.24, 4.255), (.22, 4.26)], GOLD, 'CN_Gold', 6, smooth=False, start=math.pi / 6)
    tube(p, [(0, 0, 3.8), (0, 0, 3.91)], [.024, .018], GOLD_DEEP, 'CN_Gold', 8, True)
    blob(p, (0, 0, 3.995), (.045, .045, .085), LIGHT_WARM, 'CN_Glow', 2, 0.0, seed)
    revolve(p, [(.272, 4.255), (.25, 4.29), (.12, 4.37), (.062, 4.385)], iron, 'CN_Metal', 6, smooth=False, start=math.pi / 6)
    # The lantern's floor and ceiling, so the glass never shows the sky or the street through it.
    revolve(p, [(.165, 3.752), (.02, 3.752)], tint(iron, .8), 'CN_Metal', 6, smooth=False, start=math.pi / 6)
    revolve(p, [(.02, 4.252), (.272, 4.252)], tint(iron, .6), 'CN_Metal', 6, smooth=False, start=math.pi / 6)
    revolve(p, [(.062, 4.385), (.07, 4.41), (.07, 4.43), (.04, 4.45)], iron, 'CN_Metal', 12)
    blob(p, (0, 0, 4.465), .024, GOLD, 'CN_Gold', 1, .02, seed + 5)
    tube(p, [(0, 0, 4.48), (0, 0, 4.5)], [.01, .002], GOLD, 'CN_Gold', 6, True)
    return finish(p)


def banner():
    """A banner pole 6 m tall: a white stone base, a black iron pole with gold collars and a gold spear finial, a
    cross-arm, and a long red banner hanging in front of the pole in soft folds that open toward its foot. Its
    sigil is gold on both faces, a sphere in three orbits (the Orrery's), over a white band and a swallowtail
    foot with gold tassels."""
    p = Part('SM_CN_Banner', ALL_SLOTS)
    rng = np.random.default_rng(3770)
    seed = 3770
    st = tint(IVORY, .9)
    bevel_box(p, (0, 0, .16), (.24, .24, .16), st, 'CN_White', .025, shade=shader(st, lambda v: weather(v, seed, damp=.35, rise=.2)))
    ring_moulding(p, -.24, .24, -.24, .24, .26, [(0, 0), (.025, .01), (.035, .035), (.015, .06), (0, .06)], tint(st, .96), seed=seed, step=.6)
    iron = tint(CHARCOAL, .85)
    revolve(p, [(.11, .32), (.11, .37), (.075, .43), (.058, .54)], iron, 'CN_Metal', 12)
    tube(p, [(0, 0, .52), (0, 0, 3.0), (0, 0, 5.84)], [.042, .039, .034], iron, 'CN_Metal', 8, True)
    for z in (2.3, 5.3):
        revolve(p, [(.04, z - .04), (.052, z - .01), (.052, z + .02), (.038, z + .045)], GOLD_PALE, 'CN_Gold', 12)
    blob(p, (0, 0, 5.87), .042, GOLD, 'CN_Gold', 1, .02, seed)
    tk.prism(p, (0, 0, 5.9), (0, 0, 6.0), .03, GOLD, 'CN_Gold', 4, .7)
    xa, za = .085, 5.45
    tube(p, [(0, 0, za), (xa, 0, za)], .017, iron, 'CN_Metal', 6, False)
    tube(p, [(xa, -.5, za), (xa, .5, za)], .014, iron, 'CN_Metal', 6, True)
    for s in (-1, 1):
        blob(p, (xa, s * .515, za), .026, GOLD, 'CN_Gold', 1, .02, seed + s)
    tube(p, [(xa, -.45, za), (xa, .45, za)], .03, tint(RED, .8), 'CN_Cloth', 8, True)  # the banner's sleeve over the arm

    W, zt, z_tail, z_notch = .44, za - .03, 2.55, 2.95
    phase = rng.uniform(0, 6.3)

    def bottom(y):
        return z_notch + (z_tail - z_notch) * min(abs(y) / W, 1.0)

    def depth(y, z):
        """How far the cloth stands in front of the arm's line, at a point of its face: folds that open toward
        the foot, a belly where the air takes it."""
        t = np.clip((zt - z) / (zt - bottom(y)), 0, 1)
        return xa + .03 * t + .018 * math.sin(math.pi * t) + (.01 + .022 * t) * math.sin(2 * math.pi * y / .22 + phase)

    ny, nt = 23, 16  # fine across the folds, so the sigil and band laid on the cloth never dip behind its chords
    ys = np.linspace(-W, W, ny)
    for out in (1, -1):
        verts, cols = [], []
        for i in range(nt + 1):
            t = i / nt
            for y in ys:
                z = zt - t * (zt - bottom(y))
                x = depth(y, z) + out * .002
                fold = math.sin(2 * math.pi * y / .22 + phase) * out
                verts.append((x, y, z))
                cols.append(.8 + .14 * fold - .1 * (1 - t) ** 6)
        verts = np.array(verts)
        faces = [[i * ny + j, i * ny + j + 1, (i + 1) * ny + j + 1, (i + 1) * ny + j] for i in range(nt) for j in range(ny - 1)]
        faces = [f if np.dot(newell(verts[f]), (out, 0, 0)) >= 0 else f[::-1] for f in faces]
        p.add(verts, faces, paint(RED, np.array(cols)), 'CN_Cloth', True)

        def on_cloth(pts2, lift):
            return np.array([(depth(y, z) + out * lift, y, z) for y, z in pts2])

        def strip(path2, half, colour, slot, lift, closed=True):
            path2 = np.asarray(path2, np.float64)
            n = len(path2)
            inner, outer = [], []
            for k in range(n):
                a, b = path2[(k - 1) % n if closed else max(k - 1, 0)], path2[(k + 1) % n if closed else min(k + 1, n - 1)]
                d = (b - a) / (np.linalg.norm(b - a) + 1e-9)
                nn = np.array([-d[1], d[0]])
                inner.append(path2[k] - nn * half)
                outer.append(path2[k] + nn * half)
            v = np.concatenate([on_cloth(inner, lift), on_cloth(outer, lift)])
            fs = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n if closed else n - 1)]
            fs = [f if np.dot(newell(v[f]), (out, 0, 0)) >= 0 else f[::-1] for f in fs]
            p.add(v, fs, colour, slot, True)
        zc = 4.3
        for k, rot in enumerate((0.0, math.pi / 3, -math.pi / 3)):
            s_ = np.linspace(0, 2 * math.pi, 33)[:-1]
            e = np.stack([.25 * np.cos(s_), .085 * np.sin(s_)], 1) @ np.array([[math.cos(rot), math.sin(rot)], [-math.sin(rot), math.cos(rot)]])
            strip(e + (0, zc), .011, GOLD_PALE, 'CN_Gold', .006 + .003 * k)
        disc = [(.06 * math.cos(a), zc + .06 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]]
        v = on_cloth(disc, .016)
        poly(p, v, (out, 0, 0), GOLD, 'CN_Gold', True)
        strip([(y, 3.3) for y in ys], .035, WHITE_PURE, 'CN_Cloth', .006, closed=False)
    for s in (-1, 1):
        y = s * W
        tip = np.array([depth(y, z_tail), y, z_tail])
        tube(p, [tip, tip - (0, 0, .1)], .006, GOLD_DEEP, 'CN_Cloth', 4, False)
        tube(p, [tip - (0, 0, .1), tip - (0, 0, .13), tip - (0, 0, .24)], [.012, .026, .016], GOLD_DEEP, 'CN_Cloth', 8, True)
    return finish(p)


# ---------------------------------------------------------------- terrace walls and stairs

def terrace_wall():
    """A terrace wall (0.6 x 12 x 2.5) facing +x, as the town lays them along its pad edges (1.5 m in the bank, 1 m
    standing over the upper pad) and as the courts raise them: dressed white limestone through-stones in running
    courses, each its own tone and set a little proud or shy, on a projecting footing course, under a coping of
    long slabs; weep holes along the front's second course with the stains they leave, rain streaks under the
    coping, rising damp, trails of red climber over the front and gold grass in the coping joints. Its ends are
    plain, because the runs meet end to end."""
    p = Part('SM_CN_TerraceWall', ALL_SLOTS)
    rng = np.random.default_rng(3740)
    seed = 3740
    half, hx = 6.0, .28
    courses = (0.0, .3, .64, .98, 1.32, 1.66, 2.0, 2.34)

    def age(v):
        streak = np.clip(noise2(v[:, 1] / .5, 3.7, seed) * 1.8, 0, 1) * np.clip((v[:, 2] - .8) / 1.5, 0, 1)
        return weather(v, seed, damp=.24, rise=.5, stain=.07) * (1 - .32 * streak)
    weep_spans = []
    for k in range(len(courses) - 1):
        z0, z1 = courses[k], courses[k + 1]
        y, first = -half, True
        while y < half - 1e-6:
            y2 = min(half, y + rng.uniform(.6, 1.15) * (.5 if first and k % 2 else 1.0))
            first = False
            if half - y2 < .3:
                y2 = half
            # The two lowest courses keep the line exactly, so the weep holes sit on their faces.
            shift = 0.0 if k < 2 else rng.uniform(-.005, .005)
            c = tint(WHITE if rng.uniform() < .6 else IVORY, rng.uniform(.8, .97))
            bevel_box(p, (shift, (y + y2) / 2, (z0 + z1) / 2), (hx + (.03 if k == 0 else 0), (y2 - y) / 2, (z1 - z0) / 2), c, 'CN_White',
                      .03 if k == 0 else .022, shade=shader(c, age))
            if k == 1:
                weep_spans.append((y, y2))
            y = y2
    y = -half
    joints = []
    while y < half - 1e-6:
        y2 = min(half, y + rng.uniform(.85, 1.25))
        if half - y2 < .35:
            y2 = half
        c = tint(IVORY, rng.uniform(.86, .97))
        bevel_box(p, (0, (y + y2) / 2, 2.42), (hx + .045, (y2 - y) / 2, .08), c, 'CN_White', .025,
                  shade=shader(c, lambda v: weather(v, seed + 1, damp=0, stain=.08)))
        joints.append(y2)
        y = y2
    for target in (-4.8, -2.4, 0.0, 2.4, 4.8):
        a, b = min(weep_spans, key=lambda s_: abs((s_[0] + s_[1]) / 2 - target))
        yc, x = (a + b) / 2, hx + .0015
        p.add([(x, yc - .04, .42), (x, yc + .04, .42), (x, yc + .04, .5), (x, yc - .04, .5)], [[0, 1, 2, 3]], tint(CHARCOAL, .5), 'CN_Black', False)
        p.add([(x - .0005, yc - .03, .325), (x - .0005, yc + .05, .325), (x - .0005, yc + .045, .42), (x - .0005, yc - .035, .42)], [[0, 1, 2, 3]],
              np.array([tint(WHITE, .82), tint(WHITE, .8), tint(WHITE, .5), tint(WHITE, .52)]), 'CN_White', False)
    for _ in range(3):
        yc = rng.uniform(-5.0, 5.0)
        n = int(rng.integers(4, 7))
        pts = [(.2, yc, 2.51), (hx + .045, yc + rng.normal(0, .05), 2.47)] + \
              [(hx + .03 + .015 * rng.uniform(), yc + rng.normal(0, .14) * i, 2.28 - .24 * i) for i in range(1, n)]
        tube(p, pts, .007, tint(CHARCOAL, .6), 'CN_Black', 4, False)
        # The climber's leaves lie flat on the stone, as a creeper's do: built loose, then pressed to the face.
        ivy = Part('ivy', ALL_SLOTS)
        leaf_cloud(ivy, [(x + .02, y_, z) for x, y_, z in pts[1:]], (.03, .26, .16), 70 * n, rng, (RED_DEEP, RED_DEEP, RED, RED_BRIGHT), size=(.045, .08),
                   droop=.4, up_bias=.1)
        v = np.asarray(ivy.v)
        v[:, 0] = np.clip(v[:, 0], hx + .008, hx + .06)
        ivy.v = v.tolist()
        merge(p, ivy)
    for yj in rng.choice(joints[:-1], 3, replace=False):
        blades(p, (rng.uniform(-.12, .12), yj, 2.5), rng, 9, (.14, .3), .08)
    return finish(p)


def flight():
    """A garden stair (4.5 x 3 x 2.5) climbing +x from its foot at x -2.25 to a pad 2.5 m up, as the town sets one on
    every riser a lane crosses: fifteen steps of 0.167 m rise and 0.3 m going on a solid core, each tread laid in
    two or three white stones with a nosing, worn paler down the middle, between plastered string walls under
    sloping copings that start on newel posts with gold finials; gold grass in a few of the corners."""
    p = Part('SM_CN_Stairs', ALL_SLOTS)
    rng = np.random.default_rng(3750)
    seed = 3750
    n, H, L = 15, 2.5, 4.5
    rise, going = H / n, L / n
    x0, hw, wt = -L / 2, 1.2, .3
    for i in range(n):
        top, xa = rise * (i + 1), x0 + going * i
        core = tint(IVORY, rng.uniform(.7, .8))
        bevel_box(p, (xa + going / 2, 0, (top - .06) / 2), (going / 2, hw, (top - .06) / 2), core, 'CN_White', .01,
                  shade=shader(core, lambda v: weather(v, seed + i, damp=.3, rise=.3)))
        edges = [-hw] + sorted(rng.uniform(-hw + .5, hw - .5, int(rng.integers(1, 3))).tolist()) + [hw]
        for a, b in zip(edges, edges[1:]):
            mid = (a + b) / 2
            c = tint(WHITE, min(1.0, rng.uniform(.84, .92) + .07 * math.exp(-(mid / .6) ** 2)))
            bevel_box(p, (xa + going / 2 - .015, mid, top - .03), (going / 2 + .015, (b - a) / 2, .03), c, 'CN_White', .014,
                      shade=shader(c, lambda v: weather(v, seed + 20 + i, damp=.12, rise=.3, stain=.04)))

    def ztop(x):
        return float(min(rise + .2 + (x - x0) * rise / going, H + .2))
    xs = list(np.linspace(x0 - .12, x0 + going * (n - 1), 9)) + [L / 2]
    for s in (-1, 1):
        ya, yb, yc = s * hw, s * (hw + wt), s * (hw + wt / 2)
        plaster = lambda pts: paint(WHITE, weather(np.asarray(pts), seed + 30 + s, damp=.3, rise=.4, stain=.07))
        for y_face, want in ((yb, s), (ya, -s)):
            for a, b in zip(xs, xs[1:]):
                for j in range(4):
                    pts = [(a, y_face, ztop(a) * j / 4), (b, y_face, ztop(b) * j / 4), (b, y_face, ztop(b) * (j + 1) / 4), (a, y_face, ztop(a) * (j + 1) / 4)]
                    poly(p, pts, (0, want, 0), plaster(pts), 'CN_White')
        for a, b in zip(xs, xs[1:]):
            pts = [(a, ya, ztop(a)), (b, ya, ztop(b)), (b, yb, ztop(b)), (a, yb, ztop(a))]
            poly(p, pts, UP, plaster(pts), 'CN_White')
        for x, want in ((xs[0], -1), (xs[-1], 1)):
            pts = [(x, ya, 0), (x, yb, 0), (x, yb, ztop(x)), (x, ya, ztop(x))]
            poly(p, pts, (want, 0, 0), plaster(pts), 'CN_White')
        # Copings: four sloping stones and a level one at the top, each a slab lapping the wall top.
        cuts = list(np.linspace(xs[0] - .03, xs[-2], 5)) + [xs[-1] + .02]
        for a, b in zip(cuts, cuts[1:]):
            a2, b2 = a + .003, b - .003
            pts = []
            for zb in (0, 1):
                for yb_ in (0, 1):
                    for xb in (0, 1):
                        x = a2 if xb == 0 else b2
                        pts.append((x, s * (hw - .035) if yb_ == 0 else s * (hw + wt + .035), ztop(x) - .005 + (.075 if zb else 0)))
            hexa(p, pts, tint(IVORY, rng.uniform(.86, .96)), 'CN_White')
        nx = x0 - .2
        c = tint(IVORY, .9)
        bevel_box(p, (nx, yc, .36), (.21, .21, .36), c, 'CN_White', .025, shade=shader(c, lambda v: weather(v, seed + 40, damp=.3, rise=.3)))
        bevel_box(p, (nx, yc, .755), (.24, .24, .035), tint(c, .97), 'CN_White', .015)
        revolve(p, [(.075, .79), (.05, .83), (.062, .855)], GOLD_DEEP, 'CN_Gold', 10, (nx, yc, 0))
        blob(p, (nx, yc, .93), .085, GOLD, 'CN_Gold', 1, .02, seed + s)
    for i in rng.choice(n, 5, replace=False):
        s = 1 if rng.uniform() < .5 else -1
        blades(p, (x0 + going * (i + .5), s * (hw - .04), rise * (i + 1)), rng, 6, (.1, .22), .06, (0, -s * .08))
    return finish(p)


# ---------------------------------------------------------------- the market stall

FRUIT = {'pear': [(.03, 0), (.55, .1), (.78, .36), (.56, .64), (.3, .84), (.1, 1.0)],
         'round': [(.12, 0), (.72, .12), (1.0, .46), (.78, .84), (.16, 1.0)]}


def fruit(p, c, size, colour, slot, rng, kind='pear', sides=6):
    """One fruit or bulb (a pear, a pomegranate, an onion) standing on c: a small lathe on a tilted axis with its own
    tone, darker where it rests, both ends closed."""
    prof = FRUIT[kind]
    hgt = (1.25 if kind == 'pear' else .95) * size
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + rng.uniform(0, 1)
    R = rotation((rng.normal(), rng.normal(), 0.0), rng.uniform(0, .5 if kind == 'pear' else .25))
    v = np.concatenate([np.stack([np.cos(ang) * r * size, np.sin(ang) * r * size, np.full(sides, z * hgt)], 1) for r, z in prof]) @ R.T
    v = v + np.asarray(c, np.float64)
    n = sides
    faces = [[i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j] for i in range(len(prof) - 1) for j in range(n)]
    faces += [list(range(n))[::-1], [(len(prof) - 1) * n + j for j in range(n)]]
    rest = (v[:, 2] - v[:, 2].min()) / max(float(np.ptp(v[:, 2])), 1e-6)
    p.add(v, faces, paint(colour, rng.uniform(.8, 1.0) * (.72 + .28 * rest)), slot, True)


def crate(p, c, h, colour, slot, rng, wall=.014):
    """An open crate standing on c (its floor's centre): a slatted floor and four sides of two boards each, with
    the gap between them."""
    x, y, z = c
    hx, hy, hz = h
    col = tint(colour, rng.uniform(.75, .95))
    bevel_box(p, (x, y, z + wall / 2), (hx - .002, hy - .002, wall / 2), tint(col, .8), slot, .004)
    for k in range(2):
        zc, hh = z + hz * (.5 + k) - .006 * (1 - 2 * k), hz / 2 - .009
        for s in (-1, 1):
            bevel_box(p, (x + s * (hx - wall / 2), y, zc), (wall / 2, hy, hh), tint(col, rng.uniform(.9, 1.0)), slot, .004)
            bevel_box(p, (x, y + s * (hy - wall / 2), zc), (hx - wall, wall / 2, hh), tint(col, rng.uniform(.9, 1.0)), slot, .004)


def stall():
    """Sefa's market stall (3 x 4 x 3.5) facing +x: a black-painted timber frame under a red and white striped canvas
    roof with scalloped valances, a red-painted counter with raised panels under a white cloth, crates of gold
    pears and gold-leaved terrace greens, a basket of white onions, a bowl of red pomegranates, a brass balance;
    on the back table white porcelain jars banded in blue, crates on the ground, a sack, a lantern hung from the
    ridge and bunches of herbs drying under the eave."""
    p = Part('SM_CN_Stall', ALL_SLOTS)
    rng = np.random.default_rng(3760)
    seed = 3760
    X, Y, eave, ridge = 1.28, 1.8, 2.36, 3.28
    black = tint(CHARCOAL, .9)
    for x in (-X, 0.0, X):
        for y in (-Y, Y):
            top = ridge if x == 0 else eave + .05
            bevel_box(p, (x, y, top / 2), (.045, .045, top / 2), tint(black, rng.uniform(.8, 1.0)), 'CN_Black', .008)
            bevel_box(p, (x, y, .03), (.075, .075, .03), tint(IVORY, .7), 'CN_White', .01)
    for x in (-X, X):
        timber(p, (x, -Y - .08, eave), (x, Y + .08, eave), .08, .1, black, 'CN_Black')
    for y in (-Y, Y):
        timber(p, (-X - .04, y, eave), (X + .04, y, eave), .08, .1, black, 'CN_Black')
    timber(p, (0, -Y - .1, ridge), (0, Y + .1, ridge), .08, .1, black, 'CN_Black')
    for y in (-Y, 0.0, Y):
        for s in (-1, 1):
            timber(p, (0, y, ridge - .01), (s * (X + .04), y, eave + .03), .06, .06, black, 'CN_Black')  # under the canvas's sag
    # The canvas: stripes running down both slopes, sagging between the rafters, both faces built. The ridge beam
    # and the eave plates carry it along their length, so the sag between rafters dies out toward both (sagging at
    # the ridge too, the cloth let the beam's top through between the rafters).
    zr, ze, edge, ny = ridge + .085, eave + .1, X + .19, 10
    width = 2 * (Y + .15) / ny
    for side in (1, -1):
        for k in range(ny):
            ya = -Y - .15 + width * k
            c = tint(RED if k % 2 == 0 else WHITE_PURE, rng.uniform(.86, .98))
            grid = []
            for i in range(8):
                x = edge * i / 7
                for y in (ya, ya + width / 2, ya + width):
                    span = math.sin(math.pi * min(x / X, 1.0))
                    z = zr - (zr - ze) * x / X - .025 * abs(math.sin(math.pi * y / Y)) * span - .02 * span
                    grid.append((side * x, y, z))
            grid = np.array(grid)
            faces = [[i * 3 + j, i * 3 + j + 1, (i + 1) * 3 + j + 1, (i + 1) * 3 + j] for i in range(7) for j in range(2)]
            faces = [f if np.dot(newell(grid[f]), UP) >= 0 else f[::-1] for f in faces]
            p.add(grid, faces, c, 'CN_Cloth', True)
            p.add(grid - UP * .004, [f[::-1] for f in faces], tint(c, .75), 'CN_Cloth', True)
            a_, b_ = grid[7 * 3], grid[7 * 3 + 2]
            pts = [a_, b_] + [np.array([side * edge, ya + width * (1 - q / 4), a_[2] - .2 * (.72 + .28 * math.sin(math.pi * q / 4))]) for q in range(5)]
            pts = np.array(pts)
            poly(p, pts, (side, 0, 0), c, 'CN_Cloth')
            poly(p, pts - np.array([side * .004, 0, 0]), (-side, 0, 0), tint(c, .78), 'CN_Cloth')
    # The counter.
    red = tint(RED, rng.uniform(.8, .92))
    bevel_box(p, (.99, 0, .44), (.25, 1.7, .44), red, 'CN_Red', .012, shade=shader(red, lambda v: weather(v, seed, damp=.15, rise=.25, stain=.04)))
    for k in range(4):
        bevel_box(p, (1.252, -1.275 + .85 * k, .47), (.012, .36, .27), tint(red, .9), 'CN_Red', .008)
    bevel_box(p, (1.252, 0, .05), (.012, 1.7, .05), black, 'CN_Black', .005)
    bevel_box(p, (.99, 0, .9), (.29, 1.76, .02), tint(WHITE_PURE, .82), 'CN_Red', .006)
    prof = [(.72, .923), (1.0, .923), (1.262, .923), (1.284, .905), (1.29, .82), (1.294, .7)]
    ys = np.linspace(-1.72, 1.72, 25)
    verts, cols = [], []
    for i, (x, z) in enumerate(prof):
        hang = max(0.0, (.923 - z) / .223)
        for y in ys:
            verts.append((x + .012 * hang * math.sin(2 * math.pi * y / .31), y, z))
            cols.append(.9 - .12 * hang * (1 + math.sin(2 * math.pi * y / .31)) / 2)
    verts = np.array(verts)
    m = len(ys)
    faces = [[i * m + j, (i + 1) * m + j, (i + 1) * m + j + 1, i * m + j + 1] for i in range(len(prof) - 1) for j in range(m - 1)]
    faces = [f if np.dot(newell(verts[f]), (1, 0, 1)) >= 0 else f[::-1] for f in faces]
    p.add(verts, faces, paint(WHITE_PURE, np.array(cols)), 'CN_Cloth', True)
    zt = .925
    # Goods: pears, greens, onions, pomegranates, the balance.
    pear = lambda q: fruit(p, q, .036, tint(GOLD_PALE, rng.uniform(.68, .86)), 'CN_Red', rng, 'pear')
    crate(p, (.98, -1.15, zt), (.2, .3, .085), WHITE_PURE, 'CN_Red', rng)
    p.add([(.79, -1.44, zt + .1), (1.17, -1.44, zt + .1), (1.17, -.86, zt + .1), (.79, -.86, zt + .1)], [[0, 1, 2, 3]], tint(GOLD_STRAW, .55), 'CN_Red', False)
    for i in range(3):
        for j in range(5):
            pear((.86 + .12 * i + rng.normal(0, .01), -1.39 + .11 * j + rng.normal(0, .01), zt + .095))
    crate(p, (.98, -.42, zt), (.2, .3, .07), WHITE_PURE, 'CN_Red', rng)
    leaf_cloud(p, [(.98 + rng.uniform(-.1, .1), -.42 + rng.uniform(-.2, .2), zt + .16) for _ in range(6)], (.1, .1, .07), 320, rng,
               (GOLD_GRASS, GOLD_STRAW, GOLD_GRASS), size=(.07, .13), up_bias=.7)
    basket = tint(GOLD_STRAW, .9)
    revolve(p, [(.14, zt), (.16, zt + .03), (.19, zt + .12), (.2, zt + .14)], basket, 'CN_Cloth', 12, (.96, .35, 0),
            mult=lambda v: .78 + .22 * np.sin(v[:, 2] * 160) ** 2)
    revolve(p, [(.2, zt + .14), (.18, zt + .13), (.15, zt + .03)], tint(basket, .7), 'CN_Cloth', 12, (.96, .35, 0))
    torus(p, (.96, .35, zt + .145), .2, .012, tint(basket, .85), 'CN_Cloth', 16, 5)
    for k in range(9):
        a, r = 2 * math.pi * k / 7, (.07 if k < 7 else .0)
        fruit(p, (.96 + r * math.cos(a) + .02 * (k - 7), .35 + r * math.sin(a), zt + .1 + (.03 if k >= 7 else 0)), .045,
              tint(WHITE_PURE, rng.uniform(.78, .92)), 'CN_Cloth', rng, 'round')
    revolve(p, [(.09, zt), (.16, zt + .05), (.2, zt + .09), (.19, zt + .095), (.15, zt + .055), (.08, zt + .01)], tint(BLACK, 1.0), 'CN_Lacquer', 14, (1.0, .95, 0))
    for k in range(7):
        a = 2 * math.pi * k / 6
        r = .09 if k < 6 else 0.0
        fruit(p, (1.0 + r * math.cos(a), .95 + r * math.sin(a), zt + .035 + (.05 if k == 6 else 0)), .05, tint(RED, rng.uniform(.75, .95)), 'CN_Red', rng, 'round')
    bx, by = 1.02, 1.45
    revolve(p, [(.08, zt), (.08, zt + .015), (.05, zt + .03), (.02, zt + .045)], GOLD, 'CN_Gold', 12, (bx, by, 0))
    tube(p, [(bx, by, zt + .04), (bx, by, zt + .33)], .01, GOLD, 'CN_Gold', 6, True)
    tube(p, [(bx, by - .17, zt + .32), (bx, by + .17, zt + .32)], .007, GOLD_PALE, 'CN_Gold', 6, True)
    for s in (-1, 1):
        cy = by + s * .17
        revolve(p, [(.02, zt + .1), (.07, zt + .115), (.085, zt + .13)], GOLD, 'CN_Gold', 12, (bx, cy, 0))
        revolve(p, [(.082, zt + .131), (.068, zt + .118), (.02, zt + .104)], GOLD_DEEP, 'CN_Gold', 12, (bx, cy, 0))
        for a in (0, 2.1, 4.2):
            tube(p, [(bx, cy, zt + .32), (bx + .08 * math.cos(a), cy + .08 * math.sin(a), zt + .13)], .0025, GOLD_PALE, 'CN_Gold', 3, False)
    # The back table, its porcelain, crates on the ground and a sack.
    bevel_box(p, (-.7, 0, .74), (.24, 1.45, .02), tint(WHITE_PURE, .75), 'CN_Red', .006)
    for x in (-.88, -.52):
        for y in (-1.36, 1.36):
            bevel_box(p, (x, y, .36), (.025, .025, .36), black, 'CN_Black', .005)
    for (y, hgt) in ((-1.05, .34), (-.62, .26), (.85, .3)):
        k = hgt / .34
        prof = [(.05 * k, 0), (.075 * k, .02), (.1 * k, .1), (.11 * k, .18), (.085 * k, .27), (.05 * k, .3), (.055 * k, .33), (.06 * k, .34)]
        prof = [(r, .76 + z * k) for r, z in prof]
        revolve(p, prof, tint(WHITE_PURE, rng.uniform(.85, .95)), 'CN_Lacquer', 12, (-.7, y, 0))
        revolve(p, [(r * 1.004, z) for r, z in prof[2:4]], tint(BLUE, rng.uniform(.85, 1.0)), 'CN_Blue', 12, (-.7, y, 0))
        revolve(p, [(.06 * k, prof[-1][1]), (.012, prof[-1][1] - .004)], CHARCOAL, 'CN_Black', 12, (-.7, y, 0), smooth=False)
    # The crates and the sack stand beside the table's back legs (x -0.88), not round them; the upper crate rests on
    # the lower one's top boards (z 0.237).
    crate(p, (-1.12, 1.35, 0), (.2, .3, .12), BLACK, 'CN_Black', rng)
    crate(p, (-1.12, 1.35, .237), (.2, .3, .085), BLACK, 'CN_Black', rng)
    for i in range(2):
        for j in range(4):
            pear((-1.2 + .15 * i, 1.13 + .14 * j, .252))
    blob(p, (-1.1, -1.5, .26), (.2, .17, .26), tint(WHITE, .85), 'CN_Cloth', 2, .12, seed, shade=lambda v: .7 + .3 * np.clip(v[:, 2] / .45, 0, 1))
    tube(p, [(-1.1, -1.5, .47), (-1.1, -1.5, .56)], [.05, .03], tint(WHITE, .7), 'CN_Cloth', 8, True)
    # The lantern on the ridge and the herbs under the front eave. The cap's profile runs up toward the hook, so its
    # faces point out of the lantern (listed downward they faced in).
    tube(p, [(0, 0, ridge - .05), (0, 0, 2.62)], .004, CHARCOAL, 'CN_Metal', 4, False)
    revolve(p, [(.11, 2.56), (.1, 2.58), (.03, 2.62)], black, 'CN_Metal', 6, smooth=False)
    revolve(p, [(.085, 2.37), (.1, 2.56)], tint(BLUE_PALE, .95), 'CN_Glass', 6, smooth=False)
    revolve(p, [(.09, 2.33), (.09, 2.37), (.02, 2.375)], black, 'CN_Metal', 6, smooth=False)
    revolve(p, [(.02, 2.555), (.11, 2.555)], tint(black, .6), 'CN_Metal', 6, smooth=False)
    blob(p, (0, 0, 2.47), (.035, .035, .06), LIGHT_WARM, 'CN_Glow', 1, 0.0, seed)
    for y in (-1.2, -.3, .7):
        tube(p, [(X, y, eave - .05), (X, y, eave - .2)], .004, GOLD_STRAW, 'CN_Cloth', 4, False)
        leaf_cloud(p, [(X, y, eave - .32)], (.06, .06, .13), 60, rng, (GOLD_STRAW, GOLD_GRASS), size=(.05, .09), droop=.9, up_bias=0.0)
    return finish(p)


# ---------------------------------------------------------------- the North Gate

def hung_lantern(p, c, rng, seed, r=.09, h=.3, glow=LIGHT_GOLD):
    """A small iron lantern (body centred on c): a hexagonal glass body round a glowing flame on a gold burner, an
    iron seat, a pointed iron cap with its hanging ring, floor and ceiling closed so the glass never shows the sky."""
    x, y, z = c
    iron = tint(CHARCOAL, rng.uniform(.8, 1.0))
    z0, z1 = z - h / 2, z + h / 2
    revolve(p, [(.02, z0 - .06), (r * .8, z0 - .02), (r * 1.08, z0)], iron, 'CN_Metal', 6, (x, y, 0), smooth=False, start=math.pi / 6)
    revolve(p, [(r * 1.08, z0 + .002), (.01, z0 + .002)], tint(iron, .8), 'CN_Metal', 6, (x, y, 0), smooth=False, start=math.pi / 6)
    revolve(p, [(r, z0), (r * 1.2, z1)], tint(BLUE_PALE, .95), 'CN_Glass', 6, (x, y, 0), smooth=False, start=math.pi / 6)
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        tube(p, [(x + r * 1.02 * math.cos(a), y + r * 1.02 * math.sin(a), z0), (x + r * 1.22 * math.cos(a), y + r * 1.22 * math.sin(a), z1)],
             .006, iron, 'CN_Metal', 4, False)
    revolve(p, [(.01, z1 - .002), (r * 1.3, z1 - .002)], tint(iron, .6), 'CN_Metal', 6, (x, y, 0), smooth=False, start=math.pi / 6)
    revolve(p, [(r * 1.3, z1 - .004), (r * 1.25, z1 + .02), (.03, z1 + .1), (.012, z1 + .12)], iron, 'CN_Metal', 6, (x, y, 0), smooth=False, start=math.pi / 6)
    tk.torus(p, (x, y, z1 + .15), .03, .006, iron, 'CN_Metal', 8, 4, axis='x')
    tube(p, [(x, y, z0 + .01), (x, y, z0 + .06)], .015, GOLD_DEEP, 'CN_Gold', 6, True)
    blob(p, (x, y, z - .01), (.025, .025, .055), glow, 'CN_Glow', 1, 0.0, seed)


def gate():
    """The North Gate (3 x 14 x 9), the arch the road north passes through (along x, 10 m clear): two piers of banded
    rusticated grey limestone on a plinth, a segmental arch of fifteen chamfered voussoirs whose keystone carries a
    gold medallion, rendered spandrels between stone pilasters, an entablature with gold paterae on a rendered frieze
    and a moulded cornice, a rendered attic with gold finials over the piers and a small gold armillary at its crown.
    Iron lanterns hang in the passage, iron pintles (one with a torn bar) show where the leaves hung before the swarm
    broke them, soot marks the north face, and guard stones protect the pier corners. Both faces are alike: the
    Commons sees the south one."""
    p = Part('SM_CN_Gate', ALL_SLOTS)
    rng = np.random.default_rng(3800)
    seed = 3800
    D, Y0, Y1 = 1.3, 5.0, 7.0                 # half depth, the opening's half width, the outer half width
    imp, half_span, rise_a = 4.4, 5.0, 2.2     # springing height, half span and rise of the segmental arch
    Ri = (half_span ** 2 + rise_a ** 2) / (2 * rise_a)
    th = math.asin(half_span / Ri)
    cz = imp - Ri * math.cos(th)
    Ro = Ri + .8
    z_arch = cz + Ro                           # the extrados crown, where the architrave starts

    def age(v):
        north = (v[:, 0] > D - .3) * np.clip(.4 + .9 * noise2(v[:, 1] / 1.2, v[:, 2] / 1.0, seed + 9), 0, 1) * np.exp(-v[:, 2] / 3.5)
        return weather(v, seed, damp=.3, rise=.7, stain=.06) * (1 - .45 * north)

    def plaster(v):
        v = np.asarray(v, np.float64)
        streak = np.clip(noise2(v[:, 1] / .6, 1.3, seed + 3) * 1.7, 0, 1) * np.clip((v[:, 2] - 5.0) / 2.4, 0, 1)
        return weather(v, seed + 5, damp=.1, rise=.6, stain=.08) * (1 - .22 * streak)
    beds = (LIMESTONE, tint(LIMESTONE, .94))  # the piers' blocks come from two beds of the quarry
    for s in (-1, 1):
        y_lo, y_hi = (Y0, Y1) if s > 0 else (-Y1, -Y0)
        c = tint(LIMESTONE, .84)
        bevel_box(p, (0, s * 6.02, .25), (D + .07, 1.05, .25), c, 'CN_White', .03, shade=shader(c, age))
        zs = np.linspace(.5, 4.25, 9)
        for k in range(8):
            if k % 2 == 0:
                blocks = [(-D, -D / 3, y_lo, y_hi), (-D / 3, D / 3, y_lo, y_hi), (D / 3, D, y_lo, y_hi)]
            else:
                ym = (y_lo + y_hi) / 2 + rng.uniform(-.2, .2)
                blocks = [(-D, D, y_lo, ym), (-D, D, ym, y_hi)]
            for xa, xb, ya, yb in blocks:
                c = tint(beds[0] if rng.uniform() < .5 else beds[1], rng.uniform(.8, .95))
                bevel_box(p, ((xa + xb) / 2, (ya + yb) / 2, (zs[k] + zs[k + 1]) / 2), ((xb - xa) / 2, (yb - ya) / 2, (zs[k + 1] - zs[k]) / 2),
                          c, 'CN_White', .045, shade=shader(c, age))
        bevel_box(p, (0, s * 6.0, 4.33), (D, 1.0, .08), tint(LIMESTONE, .86), 'CN_White', .01)
        ring_moulding(p, -D, D, y_lo, y_hi, 4.25, STRING, tint(LIMESTONE, .93), seed=seed + 2, step=.8)
        # Above the impost the pier is rendered, to the architrave, with a stone pilaster on each face.
        wy = s * Y1
        xs_side = np.linspace(-D, D, 4)
        zs_side = np.linspace(imp, z_arch + .02, 4)
        for a, b in zip(xs_side, xs_side[1:]):
            for z0, z1 in zip(zs_side, zs_side[1:]):
                pts = [(a, wy, z0), (b, wy, z0), (b, wy, z1), (a, wy, z1)]
                poly(p, pts, (0, s, 0), paint(WHITE_PURE, plaster(pts)), 'CN_Plaster')
        for xf in (-1, 1):
            c = tint(LIMESTONE, rng.uniform(.86, .94))
            bevel_box(p, (xf * (D + .035), s * 6.0, (4.41 + z_arch) / 2), (.035, .45, (z_arch - 4.41) / 2), c, 'CN_White', .012,
                      shade=shader(c, lambda v: weather(v, seed + 6, damp=0, stain=.06)))
            bevel_box(p, (xf * (D + .06), s * 6.0, z_arch - .08), (.06, .52, .08), tint(c, .97), 'CN_White', .015)
    # Spandrels: the rendered wall plane above the impost and the arch, on both faces, its bottom tucked behind the
    # voussoirs' extrados.
    joints = [-th + 2 * th * k / 15 for k in range(16)]
    cy_ = [Ro * math.sin(a) for a in joints]
    cz_ = [cz + Ro * math.cos(a) for a in joints]

    def chord(y):
        return float(np.interp(y, cy_, cz_)) - .03
    inner = [y for y in cy_ if abs(y) < Y0 - .05]
    cols = [-Y1, -6.5, -6.0, -5.5, -Y0] + inner + [Y0, 5.5, 6.0, 6.5, Y1]
    for xf in (-1, 1):
        x = xf * D
        for a, b in zip(cols, cols[1:]):
            if b <= -Y0 + 1e-9 or a >= Y0 - 1e-9:
                ba = bb = imp            # over the piers
            else:
                ba, bb = chord(a), chord(b)
            for j in range(3):
                za0, za1 = ba + (z_arch + .02 - ba) * j / 3, ba + (z_arch + .02 - ba) * (j + 1) / 3
                zb0, zb1 = bb + (z_arch + .02 - bb) * j / 3, bb + (z_arch + .02 - bb) * (j + 1) / 3
                pts = [(x, a, za0), (x, b, zb0), (x, b, zb1), (x, a, za1)]
                poly(p, pts, (xf, 0, 0), paint(WHITE_PURE, plaster(pts)), 'CN_Plaster')
    # The arch: fifteen voussoirs through the full depth, standing proud of the spandrels; the keystone taller.
    for k in range(15):
        a0, a1 = joints[k], joints[k + 1]
        key = k == 7
        r_out = Ro + (.28 if key else 0.0)
        rm = (Ri + r_out) / 2
        am = (a0 + a1) / 2

        def warp(v, am=am, rm=rm):
            a = am + v[:, 1] / rm
            return np.stack([v[:, 0], v[:, 2] * np.sin(a), cz + v[:, 2] * np.cos(a)], 1)
        c = tint(LIMESTONE, rng.uniform(.84, .96))
        bent_box(p, (0, 0, rm), (D + (.12 if key else .05), (a1 - a0) * rm / 2, (r_out - Ri) / 2), c, 'CN_White', warp, .03,
                 mult=lambda v, k=k: weather(v, seed + k, damp=.05, rise=.5, stain=.06))
    kz = cz + Ri + (Ro + .28 - Ri) * .45
    for xf in (-1, 1):
        x = xf * (D + .12)
        tube(p, [(x, 0, kz), (x + xf * .03, 0, kz)], .19, GOLD, 'CN_Gold', 16, True)
        tk.torus(p, (x + xf * .035, 0, kz), .17, .014, GOLD_PALE, 'CN_Gold', 24, 5, axis='x')
        blob(p, (x + xf * .04, 0, kz), .05, GOLD_PALE, 'CN_Gold', 1, .02, seed + xf)
    # Entablature (a limestone architrave, a rendered frieze), cornice, rendered attic and the gold on top.
    c = tint(LIMESTONE, .9)
    bevel_box(p, (0, 0, z_arch + .11), (D + .06, Y1 + .06, .11), c, 'CN_White', .02, shade=shader(c, lambda v: weather(v, seed + 7, damp=0, stain=.07)))
    zf = z_arch + .22
    bevel_box(p, (0, 0, zf + .18), (D + .02, Y1 + .02, .18), WHITE_PURE, 'CN_Plaster', .01,
              shade=shader(WHITE_PURE, lambda v: weather(v, seed + 8, damp=0, stain=.07)))
    for xf in (-1, 1):
        for y in (-6.0, -3.0, 3.0, 6.0):
            tube(p, [(xf * (D + .02), y, zf + .18), (xf * (D + .045), y, zf + .18)], .1, GOLD, 'CN_Gold', 12, True)
    zc = zf + .36
    ring_moulding(p, -D - .02, D + .02, -Y1 - .02, Y1 + .02, zc, CORNICE, tint(LIMESTONE, .95), seed=seed + 9, step=1.2)
    za = zc + CORNICE[-1][1]
    bevel_box(p, (0, 0, za + .14), (D + .02, Y1 + .02, .14), WHITE_PURE, 'CN_Plaster', .01,
              shade=shader(WHITE_PURE, lambda v: weather(v, seed + 10, damp=0, stain=.06)))
    ring_moulding(p, -D - .02, D + .02, -Y1 - .02, Y1 + .02, za + .28, COPING, tint(LIMESTONE, .92), seed=seed + 11, step=1.2)
    zt = za + .28
    for s in (-1, 1):
        c = tint(LIMESTONE, .9)
        bevel_box(p, (0, s * 6.0, zt + .14), (.32, .32, .14), c, 'CN_White', .02)
        bevel_box(p, (0, s * 6.0, zt + .31), (.36, .36, .03), tint(c, .96), 'CN_White', .012)
        revolve(p, [(.09, zt + .34), (.055, zt + .38), (.07, zt + .4)], GOLD_DEEP, 'CN_Gold', 12, (0, s * 6.0, 0))
        blob(p, (0, s * 6.0, zt + .49), .1, GOLD, 'CN_Gold', 1, .02, seed + 20 + s)
    bevel_box(p, (0, 0, zt + .07), (.26, .26, .07), tint(LIMESTONE, .9), 'CN_White', .015)
    tube(p, [(0, 0, zt + .14), (0, 0, zt + .26)], [.03, .02], GOLD_DEEP, 'CN_Gold', 8, True)
    ca = np.array([0, 0, zt + .48])
    for axis, R in (((1, 0, 0), .21), ((0, math.sin(math.radians(66)), math.cos(math.radians(66))), .18),
                    ((math.sin(math.radians(23.4)), 0, math.cos(math.radians(23.4))), .15)):
        band_ring(p, ca, axis, R, .03, .012, GOLD, 'CN_Gold', 32)
    blob(p, ca, .055, GOLD_PALE, 'CN_Gold', 1, .02, seed + 30)
    # In the passage: lanterns, the pintles of the lost leaves (one with a torn bar), guard stones at the corners.
    for s in (-1, 1):
        yw = s * Y0
        # The bracket's hook ends through the lantern's ring (its top bar is at 3.44-3.46), so the lantern hangs from it.
        tube(p, tk.bezier((0, yw, 3.55), (0, yw - s * .2, 3.58), (0, yw - s * .36, 3.6), (0, yw - s * .4, 3.44), 6), .014, CHARCOAL, 'CN_Metal', 5, True)
        bevel_box(p, (0, yw - s * .015, 3.55), (.06, .015, .09), CHARCOAL, 'CN_Metal', .004)
        hung_lantern(p, (0, yw - s * .4, 3.12), rng, seed + s)
        for z in (.9, 3.5):
            bevel_box(p, (1.05, yw - s * .03, z), (.045, .03, .05), CHARCOAL, 'CN_Metal', .004)
            tube(p, [(1.05, yw - s * .075, z + .04), (1.05, yw - s * .075, z + .16)], .017, CHARCOAL, 'CN_Metal', 6, True)
        for xf in (-1, 1):
            revolve(p, [(.2, 0), (.2, .1), (.17, .4), (.11, .6), (.045, .7)], tint(LIMESTONE, rng.uniform(.8, .9)), 'CN_White', 10,
                    (xf * (D + .02), s * (Y0 - .04), 0), mult=lambda v: weather(v, seed + 40, damp=.3, rise=.3))
            revolve(p, [(.045, .7), (.01, .705)], tint(LIMESTONE, .85), 'CN_White', 10, (xf * (D + .02), s * (Y0 - .04), 0), smooth=False)
    torn = tk.bezier((1.05, Y0 - .075, 3.62), (1.1, Y0 - .1, 3.0), (1.25, Y0 - .3, 2.6), (1.15, Y0 - .45, 2.2), 7)
    tube(p, torn, .018, tint(CHARCOAL, .7), 'CN_Metal', 5, True)
    tube(p, [torn[2], torn[2] + (-.05, -.35, -.08)], .012, tint(CHARCOAL, .7), 'CN_Metal', 5, True)
    return finish(p)


# ---------------------------------------------------------------- the Wellspring garden

def well_garden():
    """The Wellspring garden (a ring of radius 9 round the origin), laid out as a four-fold garden round the spring:
    at its heart a pool basin of radius 4 (a stepped kerb of white stones, light-blue water over black stone) where
    the current home to the Center stands (its pool, 35 cm above this mesh's base, sits in this water); three gold
    spouts feeding raised rills along the east, south and west paths; a paved ring; four beds of black soil edged
    in stone, planted with white shrubs, light-blue and red flowers, gold grass and the Starlace the Well's light
    makes glow; a low ring wall with a moulded coping, broken by the four paths between gold-finialed piers, and over
    the north entrance (the road to the Commons) an iron arbour grown over with white blossom. The base sits 10 cm
    in the ground (the scenario places it at floor - 10 cm): the ring's paving stands 2 cm proud, the paths' 3.4 cm."""
    p = Part('SM_CN_WellGarden', ALL_SLOTS)
    rng = np.random.default_rng(3900)
    seed = 3900
    pave_z = .12
    # The basin: a ring step (one band of stone, its slabs told apart by tone) and a kerb of sixteen stones.
    def slabs(v):
        sector = np.floor((np.arctan2(v[:, 1], v[:, 0]) + math.pi) / (2 * math.pi) * 20)
        return weather(v, seed + 1, damp=.3, rise=.2, stain=.05) * (.86 + .12 * np.sin(sector * 7.31) ** 2)
    revolve(p, [(4.45, 0.0), (4.45, .22)], IVORY, 'CN_White', 60, mult=slabs)
    # The step's tread runs on under the kerb, so no slot opens where the kerb's facets leave the circle.
    revolve(p, [(4.45, .22), (3.95, .22)], IVORY, 'CN_White', 60, smooth=False, mult=slabs)
    for r0, r1, z1, off, bev in ((3.45, 4.0, .44, .5, .035),):
        rm, n = (r0 + r1) / 2, 16
        for k in range(n):
            a_c = 2 * math.pi * (k + off) / n
            c = tint(IVORY if rng.uniform() < .5 else WHITE, rng.uniform(.82, .95))
            # Two lengths each, so the kerb curves (a stone of one length stands 7 cm off the circle at its middle);
            # their beds are in the ground, 10 cm under the floor, so they are left open.
            bent_box(p, (rm, 0, z1 / 2), ((r1 - r0) / 2, math.pi * rm / n, z1 / 2), c, 'CN_White', polar(a_c, rm), bev,
                     mult=lambda v, k=k: weather(v, seed + k, damp=.35, rise=.25, stain=.05), segs=2, bottom=False)
    ring = [(3.47 * math.cos(a), 3.47 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 49)[:-1]]
    floor = np.array([(x, y, .1) for x, y in ring])
    p.add(floor, [list(range(48))], paint(CHARCOAL, .7 + .3 * np.abs(np.sin(np.arange(48) * 1.7))), 'CN_Black', False)
    p.add(floor + (0, 0, .2), [list(range(48))], BLUE_ICE, 'CN_Water', False)
    polar_paving(p, 4.45, 6.2, 0, 2 * math.pi, pave_z, rng, WHITE, ring=.6, slab=.8)
    # Its dark bed runs on under the beds' edging, so the slit the slabs' chords leave against it reads as a joint.
    revolve(p, [(6.32, pave_z - .007), (6.17, pave_z - .007)], SLATE, 'CN_White', 48, smooth=False)
    # Paths (north the road's), and raised rills fed by gold spouts along the other three.
    for k in range(4):
        a = math.pi / 2 * k
        u, w = np.array([math.cos(a), math.sin(a), 0.]), np.array([-math.sin(a), math.cos(a), 0.])
        # The paths start on the ring's last course (its slabs reach 6.2, the circle meets the path's edges at 6.02),
        # 1.4 cm above it: both jitter their slabs by 4 mm and the path's dark bed lies 6 mm under its slabs, and any
        # nearer they would z-fight where they overlap.
        if k % 2 == 0:
            paving(p, 6.0 if u[0] > 0 else -9.3, 9.3 if u[0] > 0 else -6.0, -1.5, 1.5, pave_z + .014, .62, rng, WHITE, seed=seed + k)
        else:
            paving(p, -1.5, 1.5, 6.0 if u[1] > 0 else -9.3, 9.3 if u[1] > 0 else -6.0, pave_z + .014, .62, rng, WHITE, seed=seed + k)
        yaw = math.degrees(a)
        for s in (-1, 1):
            # The kerbs run from the ring's paving (it meets their line at 6.0) to the wall: begun at 6.2 they left a
            # hole to the ground at each corner of a bed.
            c = tint(IVORY, rng.uniform(.84, .92))
            bevel_box(p, 7.3 * u + 1.575 * s * w + (0, 0, .1), (1.3, .075, .1), c, 'CN_White', .02, yaw,
                      shade=shader(c, lambda v: weather(v, seed + 50, damp=.3, rise=.2)))
        if k == 0:
            continue
        stone = tint(IVORY, rng.uniform(.86, .94))
        for s in (-1, 1):
            bevel_box(p, 6.48 * u + .26 * s * w + (0, 0, .2), (1.92, .06, .08), stone, 'CN_White', .015, yaw,
                      shade=shader(stone, lambda v: weather(v, seed + 60, damp=.3, rise=.15)))
        for sx in (4.5, 8.46):
            bevel_box(p, sx * u + (0, 0, .2), (.06, .32, .08), stone, 'CN_White', .015, yaw)
        q = [4.56 * u - .2 * w, 8.4 * u - .2 * w, 8.4 * u + .2 * w, 4.56 * u + .2 * w]
        # Light-blue water over a black slate bed (the water is translucent, and over the white path it read white).
        poly(p, [v + (0, 0, .145) for v in q], UP, tint(CHARCOAL, .8), 'CN_Black')  # over the path's highest slab (0.138)
        poly(p, [v + (0, 0, .25) for v in q], UP, BLUE_ICE, 'CN_Water')
        spout = [3.85 * u + (0, 0, .45), 4.25 * u + (0, 0, .44), 4.4 * u + (0, 0, .4)]
        tube(p, spout, [.05, .04, .035], GOLD, 'CN_Gold', 8, True)
        tk.torus(p, 4.4 * u + (0, 0, .4), .036, .008, GOLD_PALE, 'CN_Gold', 8, 3, axis='x' if k % 2 == 0 else 'y')
        fall = [4.43 * u + (0, 0, .385), 4.5 * u + (0, 0, .33), 4.58 * u + (0, 0, .26)]
        for side in (1, -1):
            verts = np.array([pt + side * .001 * u + d * .025 * w for pt in fall for d in (-1, 1)])
            faces = [[0, 1, 3, 2], [2, 3, 5, 4]]
            faces = [f if np.dot(newell(verts[f]), u * side) >= 0 else f[::-1] for f in faces]
            p.add(verts, faces, tint(BLUE_ICE, .95), 'CN_Water', True)
    # The beds: black soil between the paths, edged in stone, planted.
    for k in range(4):
        a0, a1 = math.pi / 2 * k, math.pi / 2 * (k + 1)
        # From under the edging stones (6.2 to 6.35) to under the ring wall (8.6 to 9.0), so no slot shows at either.
        rows = np.linspace(6.27, 8.66, 4)
        verts = []
        for r in rows:
            lo, hi = a0 + math.asin(1.65 / r), a1 - math.asin(1.65 / r)
            verts += [(r * math.cos(t), r * math.sin(t), .15) for t in np.linspace(lo, hi, 13)]
        verts = np.array(verts)
        faces = [[i * 13 + j, i * 13 + j + 1, (i + 1) * 13 + j + 1, (i + 1) * 13 + j] for i in range(3) for j in range(12)]
        faces = [f if newell(verts[f])[2] >= 0 else f[::-1] for f in faces]
        p.add(verts, faces, paint(CHARCOAL, rng.uniform(.55, 1.0, len(verts))), 'CN_Black', False)
        lo, hi = a0 + math.asin(1.65 / 6.275), a1 - math.asin(1.65 / 6.275)
        for j in range(3):
            a_c = lo + (hi - lo) * (j + .5) / 3
            c = tint(IVORY, rng.uniform(.84, .93))
            bent_box(p, (6.275, 0, .1), (.075, (hi - lo) / 6 * 6.275 - .004, .1), c, 'CN_White', polar(a_c, 6.275), .02,
                     mult=lambda v: weather(v, seed + 70, damp=.3, rise=.2), segs=3, bottom=False)
        b = (a0 + a1) / 2
        at = lambda r, t, z: (r * math.cos(t), r * math.sin(t), z)  # noqa: E731
        # White shrubs: a shadowed core under a skin of large leaves, so the mass reads full from any side.
        shrubs = [(at(7.45, b - .25, .5), .5), (at(7.6, b + .27, .46), .46), (at(8.05, b, .4), .38)]
        for (centre, r) in shrubs:
            blob(p, centre, (r * .85, r * .85, r * .7), tint(WHITE, .42), 'CN_Leaf', 1, .2, seed + k)
        leaf_cloud(p, [c_ for c_, _ in shrubs], np.array([(r, r, r * .82) for _, r in shrubs]), 300, rng, (WHITE_PURE, WHITE_COOL, WHITE),
                   size=(.15, .24), up_bias=.45, tones=(.7, 1.0))
        leaf_cloud(p, [at(6.75, b + t, .22) for t in (-.48, -.16, .17, .47)], (.26, .26, .08), 90, rng, (BLUE_PALE, BLUE_PALE, BLUE),
                   size=(.05, .08), up_bias=.85)
        leaf_cloud(p, [at(7.15, b - .52, .26), at(7.25, b + .53, .26)], (.2, .2, .1), 40, rng, (RED_BRIGHT, RED, RED_DEEP), size=(.05, .08), up_bias=.7)
        # Low mats of gold-leaved ground cover between the shrubs, so the soil shows only in the gaps.
        leaf_cloud(p, [at(7.0, b - .05, .17), at(8.15, b - .38, .17), at(8.15, b + .4, .17)], (.42, .42, .04), 180, rng, (GOLD_GRASS, GOLD_STRAW, GOLD_GRASS),
                   size=(.1, .16), droop=.1, up_bias=.95)
        leaf_cloud(p, [at(6.55, b + t, .2) for t in (-.3, 0.0, .3)], (.18, .18, .05), 30, rng, (tint(LIGHT_BLUE, .45),), size=(.03, .05), slot='CN_Glow',
                   up_bias=.9)
        for _ in range(3):
            r, t = rng.uniform(6.6, 8.3), b + rng.uniform(-.55, .55)
            blades(p, at(r, t, .15), rng, 7, (.3, .6), .14)
    # The ring wall between the paths, with its coping, and gold-finialed piers either side of every path.
    gap = math.asin(1.75 / 8.8)
    for k in range(4):
        start = math.pi / 2 * k + gap
        arc = math.pi / 2 - 2 * gap
        wall = lambda v: weather(v, seed + 80, damp=.3, rise=.35, stain=.07)  # noqa: E731
        revolve(p, [(9.0, 0), (9.0, .5)], WHITE, 'CN_White', 10, arc=arc, start=start, mult=wall)
        revolve(p, [(8.6, .5), (8.6, 0)], tint(WHITE, .92), 'CN_White', 10, arc=arc, start=start, mult=wall)
        round_moulding(p, 9.0, .5, [(0, 0), (.06, 0), (.06, .06), (.03, .09), (-.43, .09), (-.46, .06), (-.46, 0), (-.4, 0)], tint(IVORY, .94),
                       sides=10, seed=seed + 81, arc=arc, start=start)
    for k in range(4):
        a = math.pi / 2 * k
        u, w = np.array([math.cos(a), math.sin(a), 0.]), np.array([-math.sin(a), math.cos(a), 0.])
        for s in (-1, 1):
            c0 = math.sqrt(8.8 ** 2 - 1.75 ** 2) * u + 1.75 * s * w
            c = tint(IVORY, rng.uniform(.86, .94))
            bevel_box(p, c0 + (0, 0, .55), (.25, .25, .55), c, 'CN_White', .025, math.degrees(a), shade=shader(c, lambda v: weather(v, seed + 90, damp=.3, rise=.3)))
            bevel_box(p, c0 + (0, 0, 1.14), (.29, .29, .04), tint(c, .96), 'CN_White', .015, math.degrees(a))
            revolve(p, [(.08, 1.18), (.05, 1.22), (.065, 1.24)], GOLD_DEEP, 'CN_Gold', 8, tuple(c0))
            blob(p, c0 + (0, 0, 1.33), .09, GOLD, 'CN_Gold', 1, .02, seed + k * 2 + s)
    # The arbour over the north entrance: two black iron hoops on posts, tied across, under white blossom.
    iron = tint(CHARCOAL, .85)
    for x in (8.95, 9.25):
        for s in (-1, 1):
            tube(p, [(x, s * 1.32, pave_z), (x, s * 1.32, 2.3)], .025, iron, 'CN_Metal', 6, True)
        hoop = [(x, -1.32 * math.cos(t), 2.3 + 1.32 * math.sin(t)) for t in np.linspace(0, math.pi, 13)]
        tube(p, hoop, .02, iron, 'CN_Metal', 6, False)
    for t in np.linspace(0, math.pi, 9):
        y, z = -1.32 * math.cos(t), 2.3 + 1.32 * math.sin(t)
        tube(p, [(8.95, y, z), (9.25, y, z)], .012, iron, 'CN_Metal', 4, False)
    for s in (-1, 1):
        for z in (.6, 1.2, 1.8):
            tube(p, [(8.95, s * 1.32, z), (9.25, s * 1.32, z)], .012, iron, 'CN_Metal', 4, False)
    bloom = [(9.1, -1.32 * math.cos(t), 2.3 + 1.32 * math.sin(t)) for t in np.linspace(0, math.pi, 10)]
    bloom += [(9.1, s * 1.32, z) for s in (-1, 1) for z in (.9, 1.6)]
    # The climber's mass along the hoops (a shadowed core, as the shrubs have) under its leaves and blossom.
    tube(p, bloom[:10], .11, tint(WHITE, .45), 'CN_Leaf', 6, True)
    leaf_cloud(p, bloom, (.17, .21, .17), 480, rng, (WHITE_PURE, WHITE_PURE, WHITE_COOL, BLUE_PALE), size=(.13, .21), droop=.5, up_bias=.3)
    return finish(p)


MESHES = [house, ruin, archive, orrery, shrine, mendery, stall, lamp, bench, planter, terrace_wall, flight, gate, well_garden, banner]
VARIANTS = {house: 4, ruin: 2}
# README sizes (x by y by z, metres; 0 leaves an axis free). Houses and ruins carry their ceiling as z, so a
# building well under it fails too; the lamp's top is held tight because the level hangs its light from it.
CONTRACT = {name: {'size': size} for name, size in (
    ('SM_CN_House0', (7, 9, CEILING['SM_CN_House0'])), ('SM_CN_House1', (6, 6, CEILING['SM_CN_House1'])),
    ('SM_CN_House2', (8, 12, CEILING['SM_CN_House2'])), ('SM_CN_House3', (8, 8, CEILING['SM_CN_House3'])),
    ('SM_CN_Ruin0', (7, 9, CEILING['SM_CN_Ruin0'])), ('SM_CN_Ruin1', (6, 6, CEILING['SM_CN_Ruin1'])),
    ('SM_CN_Archive', (20, 20, 30)), ('SM_CN_Orrery', (12, 12, 9)), ('SM_CN_Mendery', (8, 10, 6)), ('SM_CN_Shrine', (8, 8, 5)),
    ('SM_CN_Stall', (3, 4, 3.5)), ('SM_CN_Bench', (.6, 2, .9)), ('SM_CN_Planter', (1, 2, 1)),
    ('SM_CN_TerraceWall', (.6, 12, 2.5)), ('SM_CN_Stairs', (4.5, 3, 2.5)), ('SM_CN_Gate', (3, 14, 9)),
    ('SM_CN_WellGarden', (18, 18, 0)), ('SM_CN_Banner', (0, 0, 6)), ('SM_CN_Lamp', (0, 0, 4.5)))}
CONTRACT['SM_CN_Lamp']['tol'] = .01  # 5 cm, check.py's floor: lamp_lights hangs the light 35 cm under the top
CONTRACT['SM_CN_Lamp'] = {'size': (0, 0, 4.5), 'tol': .02}
