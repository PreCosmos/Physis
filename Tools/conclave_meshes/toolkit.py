"""Mesh toolkit for the Conclave's generators (Tools/conclave_meshes/*.py). Pure numpy: Blender is only
needed by Part.build() and export(), so every generator can be built and checked offline with check.py.

Conventions (see Tools/conclave/README.md):
  - Units are metres; axes are Unreal's: x forward (north), y right (east), z up. Part.build() flips y for
    Blender, and the FBX export scales metres to centimetres.
  - A face is a list of vertex indices, wound counter-clockwise seen from OUTSIDE (its front).
  - Colours are linear RGB(A) palette colours (palette.py). Material slots are names from SLOTS.
"""
import math

import numpy as np

from palette import allowed

F = np.float32

# Material slots: the Unreal side maps each to one realistic material instance (Tools/conclave/README.md). CN_Plaster
# (2026-11-07) is the lime render of the town's walls, apart from CN_White's dressed stone.
SLOTS = ('CN_White', 'CN_Black', 'CN_Lacquer', 'CN_Metal', 'CN_Gold', 'CN_Red', 'CN_Blue', 'CN_Cloth', 'CN_Leaf', 'CN_Bark',
         'CN_Plaster', 'CN_Glow', 'CN_Glass', 'CN_Ground', 'CN_Water')


# ---------------------------------------------------------------- noise (same lattice noise as the Center)

def noise2(x, y, seed):
    """Smooth value noise on a lattice, vectorised. Range about -1..1."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)

    def h(a, b):
        n = (a * 374761393 + b * 668265263 + seed * 2147483647) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
    return (h(xi, yi) * (1 - u) * (1 - v) + h(xi + 1, yi) * u * (1 - v) + h(xi, yi + 1) * (1 - u) * v + h(xi + 1, yi + 1) * u * v) * 2 - 1


def fbm(x, y, seed, octaves=6, scale=1 / 260.0, gain=.5):
    total, amp, f = 0, 1, scale
    for i in range(octaves):
        total = total + amp * noise2(np.asarray(x) * f, np.asarray(y) * f, seed + i * 17)
        amp *= gain
        f *= 2.03
    return total


def blur(h, radius):
    """Box blur of a 2-D grid, three passes (close to Gaussian)."""
    out = h.astype(np.float64)
    for _ in range(3):
        for axis in (0, 1):
            pad = np.pad(out, [((radius + 1, radius) if a == axis else (0, 0)) for a in range(2)], mode='edge')
            c = np.cumsum(pad, axis=axis)
            hi = np.take(c, np.arange(2 * radius + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, np.arange(0, c.shape[axis] - 2 * radius - 1), axis=axis)
            out = (hi - lo) / (2 * radius + 1)
    return out


# ---------------------------------------------------------------- the mesh accumulator

class Part:
    """Accumulates triangles/quads, per-vertex colours and material slots for one mesh."""

    def __init__(self, name, slots):
        bad = [s for s in slots if s not in SLOTS]
        if bad:
            raise ValueError('%s: unknown material slots %s' % (name, bad))
        self.name, self.slots = name, list(slots)
        self.v, self.f, self.c, self.m, self.s = [], [], [], [], []
        self.uv = []   # per vertex: (u, v) in image convention (v down) for atlas cards, or None (projected UVs)

    def add(self, verts, faces, colour, slot=0, smooth=True, shade=None, uv=None):
        """Adds vertices and faces. colour: one RGB(A) or one per vertex. slot: index into self.slots or a
        slot name. shade(verts) -> per-vertex multiplier on RGB (ambient occlusion, grime); keep it within
        the palette (multiplying a grey keeps it grey; a gold or red stays in family only if it stays bright
        enough, which check.py verifies). uv: one (u, v) per vertex, image convention (v down), for meshes that
        sample an atlas (foliage cards); vertices without one get the projected UVs."""
        if isinstance(slot, str):
            slot = self.slots.index(slot)
        base = len(self.v)
        verts = np.asarray(verts, np.float64)
        cols = np.asarray(colour, np.float64)
        if cols.ndim == 1:
            cols = np.tile(cols, (len(verts), 1))
        if cols.shape[1] == 3:
            cols = np.concatenate([cols, np.ones((len(cols), 1))], 1)
        if shade is not None:
            cols = cols.copy()
            cols[:, :3] *= np.asarray(shade(verts), np.float64)[:, None]
        self.v.extend(verts.tolist())
        self.c.extend(cols.tolist())
        if uv is None:
            self.uv.extend([None] * len(verts))
        else:
            uv = np.asarray(uv, np.float64).reshape(len(verts), 2)
            self.uv.extend([(float(a), float(b)) for a, b in uv])
        for face in faces:
            self.f.append([base + i for i in face])
            self.m.append(int(slot))
            self.s.append(bool(smooth))
        return base

    # -- statistics used by check.py
    def triangles(self):
        return sum(len(f) - 2 for f in self.f)

    def bounds(self):
        v = np.asarray(self.v)
        return v.min(0), v.max(0)

    def build(self):
        """Blender only: makes the mesh object (called by Tools/build_physis_conclave.py)."""
        import bpy
        mesh = bpy.data.meshes.new(self.name)
        v = np.array(self.v)
        v[:, 1] *= -1  # Unreal y east -> Blender -y; the flip mirrors, so faces are reversed to keep fronts outside
        mesh.from_pydata(v.tolist(), [], [list(reversed(f)) for f in self.f])
        mesh.update()
        for slot in self.slots:
            mat = bpy.data.materials.get(slot) or bpy.data.materials.new(slot)
            mesh.materials.append(mat)
        mesh.polygons.foreach_set('material_index', self.m)
        mesh.polygons.foreach_set('use_smooth', self.s)
        attr = mesh.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        attr.data.foreach_set('color', np.clip(np.array(self.c), 0, 1).ravel())
        uv = mesh.uv_layers.new(name='UV')
        loops = np.zeros(len(mesh.loops), np.int64)
        mesh.loops.foreach_get('vertex_index', loops)
        coords = np.array(self.v)[loops]
        uvs = np.stack([coords[:, 0] + coords[:, 2] * .5, coords[:, 1] + coords[:, 2] * .5], 1) / 4
        given = [i for i, t in enumerate(self.uv) if t is not None] if len(self.uv) == len(self.v) else []
        if given:
            table = np.full((len(self.v), 2), np.nan)
            table[given] = [self.uv[i] for i in given]
            per_loop = table[loops]
            have = ~np.isnan(per_loop[:, 0])
            # Blender's v runs up and the FBX import flips it back, so image-convention v becomes 1 - v here.
            uvs[have] = np.stack([per_loop[have, 0], 1.0 - per_loop[have, 1]], 1)
        uv.data.foreach_set('uv', uvs.ravel())
        ob = bpy.data.objects.new(self.name, mesh)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def export(ob, out):
    """Blender only: writes ob to out/<name>.fbx and removes it from the scene."""
    import bpy
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=str(out / (ob.name + '.fbx')), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             mesh_smooth_type='FACE', add_leaf_bones=False, object_types={'MESH'}, colors_type='LINEAR',
                             use_tspace=False, axis_forward='-Z', axis_up='Y')
    bpy.data.objects.remove(ob)


# ---------------------------------------------------------------- primitives

def _ico(level):
    """Unit icosphere (vertices, triangles) by subdivision, faces wound outward."""
    t = (1 + 5 ** .5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = [np.array(p, np.float64) / np.linalg.norm(p) for p in v]
    for _ in range(level):
        cache, nf = {}, []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                p = (v[a] + v[b]) / 2
                v.append(p / np.linalg.norm(p))
                cache[key] = len(v) - 1
            return cache[key]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    v = np.array(v)
    # Make every face wind outward (counter-clockwise seen from outside).
    out = []
    for a, b, c in f:
        n = np.cross(v[b] - v[a], v[c] - v[a])
        out.append((a, b, c) if np.dot(n, v[a]) > 0 else (a, c, b))
    return v, out


ICO = {i: _ico(i) for i in (1, 2, 3)}


def blob(part, c, r, colour, slot=0, level=2, rough=.18, seed=0, squash=(1, 1, 1), smooth=True, shade=None):
    """A lumpy sphere: foliage clumps, rocks, heads, bulbs."""
    v, f = ICO[level]
    rng = np.random.default_rng(abs(int(seed)))
    phase = rng.uniform(0, 100, 3)
    bump = 1 + rough * (np.sin(v[:, 0] * 3.1 + phase[0]) * np.sin(v[:, 1] * 2.7 + phase[1]) * np.sin(v[:, 2] * 3.3 + phase[2]) +
                        .5 * np.sin(v[:, 0] * 7 + v[:, 2] * 5 + phase[2]))
    pts = v * bump[:, None] * np.array(r if np.ndim(r) else (r, r, r)) * np.array(squash) + np.array(c)
    return part.add(pts, f, colour, slot, smooth, shade)


def frame(direction):
    """Right-handed basis (a, b) perpendicular to direction, so tube() and prism() wind outward."""
    d = np.asarray(direction, np.float64)
    d = d / (np.linalg.norm(d) + 1e-12)
    up = np.array([0, 0, 1.]) if abs(d[2]) < .95 else np.array([1., 0, 0])
    a = np.cross(up, d)
    a /= np.linalg.norm(a)
    b = np.cross(d, a)
    return a, b


def tube(part, points, radii, colour, slot=0, sides=8, cap=True, smooth=True, shade=None, twist=0.):
    """A tube along a polyline with per-point radii: pipes, trunks, limbs, cables."""
    points = np.asarray(points, np.float64)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (len(points),))
    rings = []
    for i, p in enumerate(points):
        d = points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]
        a, b = frame(d)
        ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + twist * i
        rings.append(p + radii[i] * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b))
    verts = np.concatenate(rings)
    faces = []
    for i in range(len(points) - 1):
        for j in range(sides):
            k = (j + 1) % sides
            faces.append([i * sides + j, i * sides + k, (i + 1) * sides + k, (i + 1) * sides + j])
    if cap:
        faces.append(list(range(sides))[::-1])
        faces.append([(len(points) - 1) * sides + j for j in range(sides)])
    return part.add(verts, faces, colour, slot, smooth, shade)


def bezier(a, b, c, d, n=10):
    t = np.linspace(0, 1, n)[:, None]
    a, b, c, d = (np.array(x, np.float64) for x in (a, b, c, d))
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d


def prism(part, base, tip, r, colour, slot=0, sides=6, tip_len=.3, smooth=False):
    """A pointed crystal or spike from base to tip."""
    base, tip = np.array(base, np.float64), np.array(tip, np.float64)
    axis = tip - base
    a, b = frame(axis)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    ring = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
    shoulder = base + axis * (1 - tip_len)
    verts = np.concatenate([base + r * ring * .85, shoulder + r * ring, [tip]])
    faces = [[j, (j + 1) % sides, sides + (j + 1) % sides, sides + j] for j in range(sides)]
    faces += [[sides + j, sides + (j + 1) % sides, 2 * sides] for j in range(sides)]
    faces.append(list(range(sides))[::-1])
    return part.add(verts, faces, colour, slot, smooth)


def _yaw(points, yaw):
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    rot = np.array([[cy, sy, 0], [-sy, cy, 0], [0, 0, 1]])
    return np.asarray(points, np.float64) @ rot


def yawed(points, yaw):
    """Rotates local points by yaw degrees about z (Unreal yaw: +x toward +y)."""
    return _yaw(points, yaw)


def box(part, c, h, colour, slot=0, yaw=0., shade=None):
    """An axis-aligned box (half extents h), turned by yaw degrees about z. Flat shaded."""
    c, h = np.array(c, np.float64), np.array(h, np.float64)
    s = np.array([[x, y, z] for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)], np.float64) * h
    s = _yaw(s, yaw)
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    return part.add(s + c, faces, colour, slot, False, shade)


def bevel_box(part, c, h, colour, slot=0, bevel=.04, yaw=0., shade=None):
    """A box with chamfered edges and corners: edges catch the light, which makes stone, wood-free
    joinery and metal read as real objects rather than CG blocks. bevel is in metres."""
    c, h = np.array(c, np.float64), np.array(h, np.float64)
    e = np.minimum(bevel, h * .45)
    # 24 vertices: each corner split three ways (one per adjacent face).
    verts, faces = [], []
    index = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                corner = np.array([sx, sy, sz]) * h
                for axis in range(3):
                    p = corner.copy()
                    for other in range(3):
                        if other != axis:
                            p[other] -= np.array([sx, sy, sz])[other] * e[other]
                    index[(sx, sy, sz, axis)] = len(verts)
                    verts.append(p)
    # Main faces (one per axis direction).
    for axis in range(3):
        for s in (-1, 1):
            o = [a for a in range(3) if a != axis]
            quad = []
            for u, w in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                key = [0, 0, 0]
                key[axis], key[o[0]], key[o[1]] = s, u, w
                quad.append(index[(key[0], key[1], key[2], axis)])
            n = np.zeros(3)
            n[axis] = s
            p = [verts[i] for i in quad]
            if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n) < 0:
                quad = quad[::-1]
            faces.append(quad)
    # Edge chamfers (12) and corner triangles (8).
    for axis in range(3):
        o = [a for a in range(3) if a != axis]
        for su in (-1, 1):
            for sw in (-1, 1):
                quad = []
                for s in (-1, 1):
                    for which in (o[0], o[1]):
                        key = [0, 0, 0]
                        key[axis], key[o[0]], key[o[1]] = s, su, sw
                        quad.append(index[(key[0], key[1], key[2], which)])
                quad = [quad[0], quad[1], quad[3], quad[2]]
                n = np.zeros(3)
                n[o[0]], n[o[1]] = su, sw
                p = [verts[i] for i in quad]
                if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n) < 0:
                    quad = quad[::-1]
                faces.append(quad)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                tri = [index[(sx, sy, sz, a)] for a in range(3)]
                n = np.array([sx, sy, sz], np.float64)
                p = [verts[i] for i in tri]
                if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n) < 0:
                    tri = tri[::-1]
                faces.append(tri)
    verts = _yaw(np.array(verts), yaw) + c
    return part.add(verts, faces, colour, slot, False, shade)


def cylinder(part, c, r, h, colour, slot=0, sides=16, r2=None, smooth=True, yaw=0.):
    """An upright cylinder or cone frustum standing on c (base centre), height h."""
    c = np.array(c, np.float64)
    r2 = r if r2 is None else r2
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + math.radians(yaw)
    lo = np.stack([np.cos(ang) * r, np.sin(ang) * r, np.zeros(sides)], 1) + c
    hi = np.stack([np.cos(ang) * r2, np.sin(ang) * r2, np.full(sides, h)], 1) + c
    faces = [[j, (j + 1) % sides, sides + (j + 1) % sides, sides + j] for j in range(sides)]
    faces += [list(range(sides))[::-1], [sides + j for j in range(sides)]]
    return part.add(np.concatenate([lo, hi]), faces, colour, slot, smooth)


def lathe(part, profile, colour, slot=0, sides=24, c=(0, 0, 0), smooth=True, arc=2 * math.pi, start=0.0):
    """Revolve a profile [(radius, z), ...] (listed bottom to top for an outward surface) around z."""
    profile = np.asarray(profile, np.float64)
    full = arc >= 2 * math.pi - 1e-6
    n = sides if full else sides + 1
    ang = start + np.linspace(0, arc, n, endpoint=not full)
    verts = np.concatenate([np.stack([np.cos(ang) * r, np.sin(ang) * r, np.full(n, z)], 1) for r, z in profile]) + np.array(c)
    faces = []
    for i in range(len(profile) - 1):
        for j in range(sides):
            k = (j + 1) % n
            faces.append([i * n + j, i * n + k, (i + 1) * n + k, (i + 1) * n + j])
    return part.add(verts, faces, colour, slot, smooth)


def torus(part, c, big, small, colour, slot=0, sides=48, ring=10, axis='z', arc=2 * math.pi, smooth=True, start=0.0):
    """A ring of radius big, tube radius small, around axis 'z' (lying flat) or 'x' (standing, facing x)."""
    full = arc >= 2 * math.pi - 1e-6
    n = sides + (0 if full else 1)
    t = start + np.linspace(0, arc, n, endpoint=not full)
    pts = np.stack([np.cos(t) * big, np.sin(t) * big], 1)
    if axis == 'x':
        path = np.stack([np.zeros(n), pts[:, 0], pts[:, 1]], 1)
    elif axis == 'y':
        path = np.stack([pts[:, 0], np.zeros(n), pts[:, 1]], 1)
    else:
        path = np.stack([pts[:, 0], pts[:, 1], np.zeros(n)], 1)
    path = path + np.array(c, np.float64)
    if full:
        path = np.concatenate([path, path[:1]])
    return tube(part, path, small, colour, slot, ring, cap=not full, smooth=smooth)


def ribbon(part, points, width, colour, slot=0, normal=(0, 0, 1)):
    """A two-sided strip along a polyline (leaf blades, cloth strips, banners)."""
    points = np.asarray(points, np.float64)
    width = np.broadcast_to(np.asarray(width, np.float64), (len(points),))
    verts, faces = [], []
    for i, p in enumerate(points):
        d = points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]
        side = np.cross(d, normal)
        side /= np.linalg.norm(side) + 1e-9
        verts += [p - side * width[i], p + side * width[i]]
    for i in range(len(points) - 1):
        faces.append([2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2])
        faces.append([2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1])
    return part.add(verts, faces, colour, slot, True)


def quad(part, a, b, c, d, colour, slot=0, smooth=False, two_sided=False):
    """One quad a-b-c-d (counter-clockwise seen from its front)."""
    faces = [[0, 1, 2, 3]] + ([[0, 3, 2, 1]] if two_sided else [])
    return part.add([a, b, c, d], faces, colour, slot, smooth)


# ---------------------------------------------------------------- architecture helpers

def hexa(part, corners, colour, slot=0, smooth=False):
    """A six-sided solid from 8 corners in box order (index = x bit + 2 * y bit + 4 * z bit), each face
    turned to face away from the solid's centre. Any sheared or tapered block: roof slabs, voussoirs,
    wedges, steps on a slope."""
    pts = np.asarray(corners, np.float64)
    centre = pts.mean(0)
    faces = []
    for face in ([0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]):
        a, b, c = pts[face[0]], pts[face[1]], pts[face[2]]
        n = np.cross(b - a, c - a)
        if np.dot(n, pts[face].mean(0) - centre) < 0:
            face = face[::-1]
        faces.append(face)
    return part.add(pts, faces, colour, slot, smooth)


def gable_roof(part, c, length, width, rise, colour, slot=0, overhang=.4, thick=.18, yaw=0., ridge_colour=None, ridge_slot=None):
    """A pitched roof over a footprint length (local x) by width (local y), eaves at c's height, ridge
    rise metres above them along local x. Both slabs have thickness and overhang so the edge reads."""
    L = length / 2 + overhang
    half = width / 2
    slope = rise / max(half, 1e-6)
    W = half + overhang
    drop = overhang * slope
    origin = np.array(c, np.float64)
    for side in (-1, 1):
        # Box order corners: x bit (-L / +L), y bit (ridge / eave), z bit (underside / top).
        pts = []
        for z_top in (0, 1):
            for y_bit in (0, 1):
                for x_bit in (0, 1):
                    x = -L if x_bit == 0 else L
                    y = 0.0 if y_bit == 0 else side * W
                    z = rise if y_bit == 0 else -drop
                    pts.append((x, y, z + (thick if z_top else 0.0)))
        hexa(part, yawed(pts, yaw) + origin, colour, slot)
    if ridge_colour is not None:
        tube(part, yawed([(-L, 0, rise + thick), (L, 0, rise + thick)], yaw) + origin, .09, ridge_colour,
             ridge_slot if ridge_slot is not None else slot, 8)


def arch(part, c, span, rise, thick, depth, colour, slot=0, yaw=0., segments=12):
    """A round arch in the local y-z plane (the opening faces local x): feet at c + (0, +-span/2, rise -
    span/2), crown at height rise above c. Built from voussoirs, so it can be any thickness."""
    r_in, r_out = span / 2, span / 2 + thick
    centre_z = rise - r_in
    origin = np.array(c, np.float64)
    for i in range(segments):
        a0, a1 = math.pi * i / segments, math.pi * (i + 1) / segments
        pts = []
        for r_bit in (0, 1):
            for a_bit in (0, 1):
                for x_bit in (0, 1):
                    a = a0 if a_bit == 0 else a1
                    r = r_in if r_bit == 0 else r_out
                    pts.append(((-depth / 2) if x_bit == 0 else depth / 2, -math.cos(a) * r, centre_z + math.sin(a) * r))
        hexa(part, yawed(pts, yaw) + origin, colour, slot)


def stairs(part, c, steps, rise, run, width, colour, slot=0, yaw=0., bevel=.02):
    """A flight of solid steps climbing along local +x from c (bottom front edge centre)."""
    for i in range(steps):
        h = rise * (i + 1)
        centre = np.array([run * (i + .5), 0, h / 2])
        bevel_box(part, _yaw([centre], yaw)[0] + np.array(c, np.float64), (run / 2, width / 2, h / 2), colour, slot, bevel, yaw)


def column(part, c, r, h, colour, slot=0, flutes=0, base_colour=None, base_slot=None, capital=True, sides=20):
    """A classical column: plinth, (optionally fluted) shaft with entasis, capital."""
    bc = base_colour if base_colour is not None else colour
    bs = base_slot if base_slot is not None else slot
    c = np.array(c, np.float64)
    bevel_box(part, c + (0, 0, .12), (r * 1.45, r * 1.45, .12), bc, bs, .025)
    lathe(part, [(r * 1.25, .24), (r * 1.2, .34), (r * 1.02, .40)], bc, bs, sides, c, True)
    prof = []
    for k in range(9):
        t = k / 8
        prof.append((r * (1 - .12 * t + .04 * math.sin(math.pi * t)), .40 + (h - .9) * t))
    if flutes:
        ang = np.linspace(0, 2 * math.pi, flutes * 4, endpoint=False)
        rings = []
        for rr, z in prof:
            wob = 1 - .045 * (np.cos(ang * flutes) > .3)
            rings.append(np.stack([np.cos(ang) * rr * wob, np.sin(ang) * rr * wob, np.full(len(ang), z)], 1))
        n = len(ang)
        verts = np.concatenate(rings) + c
        faces = [[i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j] for i in range(len(prof) - 1) for j in range(n)]
        part.add(verts, faces, colour, slot, True)
    else:
        lathe(part, prof, colour, slot, sides, c, True)
    if capital:
        top = h - .5
        lathe(part, [(r * .9, top), (r * 1.15, top + .18), (r * 1.3, top + .3)], bc, bs, sides, c, True)
        bevel_box(part, c + (0, 0, top + .4), (r * 1.5, r * 1.5, .1), bc, bs, .02)


def window_frame(part, c, w, h, depth, frame_colour, frame_slot, glass_colour=None, glass_slot=None, yaw=0., mullions=1, bar=.06):
    """A window set into a wall facing local +x at c (centre): frame, mullions and a glass or glow pane."""
    c = np.array(c, np.float64)
    def put(centre, half):
        bevel_box(part, _yaw([centre], yaw)[0] + c, half, frame_colour, frame_slot, .012, yaw)
    put((0, 0, h / 2), (depth / 2, w / 2 + bar, bar))
    put((0, 0, -h / 2), (depth / 2 + .03, w / 2 + bar * 1.6, bar * 1.2))  # sill
    for s in (-1, 1):
        put((0, s * w / 2, 0), (depth / 2, bar, h / 2))
    for k in range(1, mullions + 1):
        put((0, -w / 2 + w * k / (mullions + 1), 0), (depth / 2 * .8, bar * .6, h / 2))
    if glass_colour is not None:
        a, b, cc, d = [(-depth * .2, -w / 2, -h / 2), (-depth * .2, w / 2, -h / 2), (-depth * .2, w / 2, h / 2), (-depth * .2, -w / 2, h / 2)]
        pts = _yaw(np.array([a, b, cc, d]), yaw) + c
        part.add(pts, [[0, 1, 2, 3]], glass_colour, glass_slot, False)


def oriented(points, origin, forward, up=(0, 0, 1)):
    """Places local points (x forward, y right, z up) at origin with the given forward and up vectors.
    Used for things standing on the drum's curved walls, whose up points at the axis."""
    f = np.asarray(forward, np.float64)
    u = np.asarray(up, np.float64)
    u = u / np.linalg.norm(u)
    f = f - u * np.dot(f, u)
    f = f / np.linalg.norm(f)
    r = np.cross(u, f)  # Unreal's right (+y) for forward +x and up +z: a proper rotation, so winding is kept
    pts = np.asarray(points, np.float64)
    return np.asarray(origin, np.float64) + pts[:, :1] * f + pts[:, 1:2] * r + pts[:, 2:3] * u


def check_colours(part):
    """Returns the vertex colours of part that are outside the palette (unique, rounded)."""
    bad = set()
    for c in part.c:
        if not allowed(c[:3]):
            bad.add(tuple(round(v, 3) for v in c[:3]))
    return sorted(bad)
