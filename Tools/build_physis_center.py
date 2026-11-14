"""Generate the Center of the Universe (level 2): terrain, flora, fauna, ruins, temple, scatter.

Everything is procedural and stylised for realistic cel shading: shapes carry their colour in
vertex colour (RGB albedo, alpha = glow), so the Unreal materials stay few and the post-process
cel pass decides the light bands. Coordinates are written in Unreal metres (X north, Y east);
Blender's Y is flipped on the way out so the FBX lands the right way round.

Run:
  flatpak run org.blender.Blender -b --python Tools/build_physis_center.py -- [names] [--terrain] [--scatter]
    names      only build meshes whose name contains one of these words (default all)
    --terrain  build only the terrain tiles, water and height grid
    --scatter  rebuild only Art/Meshes/Center/scatter.json

Writes Art/Meshes/Center/*.fbx, Art/Meshes/Center/height.bin (+ .json), scatter.json, then
`outfit_operation center:import` and `center:build` in the editor.
"""
import json
import math
import struct
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Art/Meshes/Center'
F = np.float32

# ---------------------------------------------------------------- world plan (Unreal metres)

HALF = 1000.0          # the playable square is 2 km a side, mountains close it in
CELL = 2.5             # terrain resolution
TILES = 8
WATER = 0.0

REGIONS = {
    # name: (x, y, radius, floor height, blend)
    'Glade': (-700, 0, 120, 12, 90),
    'Marsh': (-360, -440, 360, -.35, 140),
    'Concourse': (0, 0, 210, 6, 120),
    'Choir': (-150, 560, 150, 1.2, 60),
    'Thornveil': (380, 400, 240, 16, 140),
    'Highlands': (400, -480, 280, 58, 160),
    'Temple': (760, 0, 160, 34, 70),
}
PATHS = (
    ((-700, 0), (-560, -60), (-420, -150), (-240, -110), (-110, -40), (0, 0)),
    ((0, 0), (-60, 200), (-120, 360), (-150, 480)),
    ((0, 0), (150, 140), (280, 300), (380, 400)),
    ((0, 0), (140, -150), (280, -320), (400, -480)),
    ((380, 400), (520, 300), (600, 150), (640, 40), (760, 0)),
    ((400, -480), (560, -330), (640, -160), (680, -40), (760, 0)),
    ((-360, -440), (-200, -300), (-110, -40)),
)


def noise2(x, y, seed):
    """Smooth value noise on a lattice, vectorised."""
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
        total = total + amp * noise2(x * f, y * f, seed + i * 17)
        amp *= gain
        f *= 2.03
    return total


def ridge(x, y, seed):
    return 1 - np.abs(fbm(x, y, seed, 5, 1 / 340.0))


def path_distance(x, y):
    best = np.full(x.shape, 1e9)
    for line in PATHS:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            dx, dy = bx - ax, by - ay
            t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
            best = np.minimum(best, np.hypot(x - ax - t * dx, y - ay - t * dy))
    # Wobble the trail edge so it reads as worn, not drawn.
    return best + 3 * noise2(x / 23, y / 23, 5)


def height(x, y):
    base = 9 + 10 * fbm(x, y, 1) + 6 * fbm(x, y, 2, 4, 1 / 90.0)
    h = base.copy()
    weight_total = np.zeros_like(x)
    for name, (cx, cy, r, floor, blend) in REGIONS.items():
        d = np.hypot(x - cx, y - cy)
        w = np.clip(1 - (d - r) / blend, 0, 1)
        w = w * w * (3 - 2 * w)
        local = floor + {'Marsh': 2.2 * fbm(x, y, 7, 4, 1 / 55.0) + .7 * fbm(x, y, 8, 3, 1 / 13.0),
                         'Highlands': 14 * ridge(x, y, 9) + 4 * fbm(x, y, 10, 4, 1 / 30.0),
                         'Thornveil': 5 * fbm(x, y, 11, 4, 1 / 70.0),
                         'Choir': .6 * fbm(x, y, 12, 3, 1 / 20.0) - 4.5 * np.clip(1 - d / 55, 0, 1),
                         'Glade': -4 * np.clip(d / r, 0, 1) ** 2}.get(name, .4 * fbm(x, y, 13, 3, 1 / 25.0))
        h = h * (1 - w) + local * w
        weight_total = np.maximum(weight_total, w)
    # Choir Hollow is a hidden canyon: tall walls around its floor, broken by one western gap.
    d = np.hypot(x + 150, y - 560)
    wall = np.clip(1 - np.abs(d - 205) / 55, 0, 1) ** .7 * (34 + 10 * ridge(x, y, 14))
    gap = np.clip(np.abs(np.arctan2(y - 560, x + 150) - math.radians(-84)) / .42, 0, 1)
    h = h + wall * gap
    # The temple stands on a plateau with cliffs on all sides but the southern ramp roads.
    d = np.hypot(x - 760, y)
    cliff = np.clip((d - 165) / 35, 0, 1)
    h = np.where(d < 200, 34 * (1 - cliff) + h * cliff, h)
    # Mountains close the world.
    edge = np.maximum(np.abs(x), np.abs(y))
    m = np.clip((edge - 820) / 160, 0, 1)
    h = h + m * m * (150 + 60 * ridge(x, y, 15))
    return h, path_distance(x, y)


def blur(h, radius):
    """Box blur of a grid, three passes (close to Gaussian)."""
    out = h.astype(np.float64)
    for _ in range(3):
        for axis in (0, 1):
            pad = np.pad(out, [(radius + 1, radius)] if False else [((radius + 1, radius) if a == axis else (0, 0)) for a in range(2)], mode='edge')
            c = np.cumsum(pad, axis=axis)
            hi = np.take(c, np.arange(2 * radius + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, np.arange(0, c.shape[axis] - 2 * radius - 1), axis=axis)
            out = (hi - lo) / (2 * radius + 1)
    return out


def grid():
    n = int(2 * HALF / CELL) + 1
    axis = np.linspace(-HALF, HALF, n, dtype=np.float64)
    gx, gy = np.meshgrid(axis, axis, indexing='ij')
    h, p = height(gx, gy)
    # Trails: flattened toward a blurred copy of the land so they cut gentle roads, never trenches.
    pw = np.clip(1 - (p - 4) / 6, 0, 1) * .9
    trail = np.maximum(blur(h, 6), WATER + .35)
    h = h * (1 - pw) + trail * pw
    return axis, gx, gy, h.astype(F), p


# ---------------------------------------------------------------- mesh building

class Part:
    """Accumulates triangles, vertex colours (alpha = glow) and material slots."""

    def __init__(self, name, slots):
        self.name, self.slots = name, list(slots)
        self.v, self.f, self.c, self.m, self.s = [], [], [], [], []

    def add(self, verts, faces, colour, slot=0, smooth=True, shade=None):
        base = len(self.v)
        verts = np.asarray(verts, np.float64)
        self.v.extend(verts.tolist())
        cols = np.tile(np.array(colour, np.float64), (len(verts), 1)) if np.ndim(colour) == 1 else np.asarray(colour, np.float64)
        if shade is not None:
            cols = cols.copy()
            cols[:, :3] *= shade(verts)[:, None]
        self.c.extend(cols.tolist())
        for face in faces:
            self.f.append([base + i for i in face])
            self.m.append(slot)
            self.s.append(smooth)
        return base

    def build(self):
        mesh = bpy.data.meshes.new(self.name)
        v = np.array(self.v)
        v[:, 1] *= -1  # Unreal Y east -> Blender -Y
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
        uv.data.foreach_set('uv', np.stack([coords[:, 0] + coords[:, 2] * .5, coords[:, 1] + coords[:, 2] * .5], 1).ravel() / 4)
        ob = bpy.data.objects.new(self.name, mesh)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def export(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=str(OUT / (ob.name + '.fbx')), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                             mesh_smooth_type='FACE', add_leaf_bones=False, object_types={'MESH'}, colors_type='LINEAR',
                             use_tspace=False, axis_forward='-Z', axis_up='Y')
    bpy.data.objects.remove(ob)
    print('exported', ob.name if False else '', flush=True)


def ico(level):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=level, radius=1)
    v = np.array([x.co[:] for x in bm.verts])
    f = [[x.index for x in face.verts] for face in bm.faces]
    bm.free()
    return v, f


ICO = {i: ico(i) for i in (1, 2, 3)}


def blob(part, c, r, colour, slot=0, level=2, rough=.18, seed=0, squash=(1, 1, 1), smooth=True, shade=None):
    v, f = ICO[level]
    rng = np.random.default_rng(abs(int(seed)))
    phase = rng.uniform(0, 100, 3)
    bump = 1 + rough * (np.sin(v[:, 0] * 3.1 + phase[0]) * np.sin(v[:, 1] * 2.7 + phase[1]) * np.sin(v[:, 2] * 3.3 + phase[2]) +
                        .5 * np.sin(v[:, 0] * 7 + v[:, 2] * 5 + phase[2]))
    pts = v * bump[:, None] * np.array(r if np.ndim(r) else (r, r, r)) * np.array(squash) + np.array(c)
    return part.add(pts, f, colour, slot, smooth, shade)


def frame(direction):
    # Left-handed (a x b = -d), so tube() and prism() wind their sides inward. Materials hide it; the Center's
    # per-polygon collision is double-sided for it (physis_center_tools.collision_shape).
    d = direction / (np.linalg.norm(direction) + 1e-9)
    up = np.array([0, 0, 1.]) if abs(d[2]) < .95 else np.array([1., 0, 0])
    a = np.cross(d, up)
    a /= np.linalg.norm(a)
    return a, np.cross(a, d)


def tube(part, points, radii, colour, slot=0, sides=8, cap=True, smooth=True, shade=None, twist=0.):
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


def prism(part, base, tip, r, colour, slot=1, sides=6, tip_len=.3, smooth=False):
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


def box(part, c, h, colour, slot=0, yaw=0., shade=None):
    c, h = np.array(c, np.float64), np.array(h, np.float64)
    s = np.array([[x, y, z] for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)], np.float64) * h
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    s = s @ np.array([[cy, sy, 0], [-sy, cy, 0], [0, 0, 1]])
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    return part.add(s + c, faces, colour, slot, False, shade)


def cylinder(part, c, r, h, colour, slot=0, sides=16, r2=None, smooth=True, yaw=0.):
    c = np.array(c, np.float64)
    r2 = r if r2 is None else r2
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + math.radians(yaw)
    lo = np.stack([np.cos(ang) * r, np.sin(ang) * r, np.zeros(sides)], 1) + c
    hi = np.stack([np.cos(ang) * r2, np.sin(ang) * r2, np.full(sides, h)], 1) + c
    faces = [[j, (j + 1) % sides, sides + (j + 1) % sides, sides + j] for j in range(sides)]
    faces += [list(range(sides))[::-1], [sides + j for j in range(sides)]]
    return part.add(np.concatenate([lo, hi]), faces, colour, slot, smooth)


def torus(part, c, big, small, colour, slot=0, sides=48, ring=10, axis='x', arc=2 * math.pi, smooth=True):
    pts = []
    for i in range(sides + (0 if arc >= 2 * math.pi else 1)):
        t = arc * i / sides - (arc - 2 * math.pi) / 2 * (arc < 2 * math.pi) * 0
        t = arc * i / sides + (math.pi / 2 - arc / 2 if arc < 2 * math.pi else 0)
        pts.append((math.cos(t) * big, math.sin(t) * big))
    pts = np.array(pts)
    if axis == 'x':
        path = np.stack([np.zeros(len(pts)), pts[:, 0], pts[:, 1]], 1)
    else:
        path = np.stack([pts[:, 0], pts[:, 1], np.zeros(len(pts))], 1)
    path = path + np.array(c, np.float64)
    if arc >= 2 * math.pi:
        path = np.concatenate([path, path[:1]])
    return tube(part, path, small, colour, slot, ring, cap=arc < 2 * math.pi, smooth=smooth)


def lathe(part, profile, colour, slot=0, sides=24, c=(0, 0, 0), smooth=True):
    """profile: list of (radius, z). Revolve around Z."""
    profile = np.asarray(profile, np.float64)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    verts = np.concatenate([np.stack([np.cos(ang) * r, np.sin(ang) * r, np.full(sides, z)], 1) for r, z in profile]) + np.array(c)
    faces = []
    for i in range(len(profile) - 1):
        for j in range(sides):
            k = (j + 1) % sides
            faces.append([i * sides + j, i * sides + k, (i + 1) * sides + k, (i + 1) * sides + j])
    return part.add(verts, faces, colour, slot, smooth)


def ribbon(part, points, width, colour, slot=0, normal=(0, 0, 1)):
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
        faces.append([2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1])  # two-sided without material flag
    return part.add(verts, faces, colour, slot, True)


def col(r, g, b, glow=0.):
    return np.array([r, g, b, glow])


def jitter(colour, rng, amount=.08):
    c = np.array(colour, np.float64)
    c[:3] *= 1 + rng.uniform(-amount, amount, 3)
    return c


# ---------------------------------------------------------------- palette (linear)

BARK = col(.055, .045, .06)
BARK_LIGHT = col(.11, .09, .1)
LEAF_TEAL = col(.02, .16, .17, .15)
LEAF_BLUE = col(.03, .09, .22, .2)
LEAF_VIOLET = col(.1, .04, .2, .2)
GLOW_CYAN = col(.25, .95, 1., 1.)
GLOW_GOLD = col(1., .72, .28, 1.)
GLOW_ROSE = col(1., .4, .75, 1.)
GLOW_LIME = col(.55, 1., .5, 1.)
STONE = col(.17, .17, .19)
STONE_DARK = col(.08, .085, .1)
CONCRETE = col(.26, .25, .24)
METAL = col(.2, .22, .25)
FIRST_WHITE = col(.62, .66, .72)
FIRST_GOLD = col(.6, .45, .2, .05)
CRYSTAL = col(.25, .75, 1., .75)
CRYSTAL_VIOLET = col(.55, .35, 1., .75)
MOSS = col(.04, .12, .08)

# Slots: Unreal assigns material instances by these names.
SOLID, GLASS, LEAF, GLOW = 'M_Cel', 'M_Crystal', 'M_Leaf', 'M_Glow'


# ---------------------------------------------------------------- flora

def leaves(part, c, r, count, colour, glow, rng, slot=1, size=(.35, .6), droop=.45, lit=.18, shell=.55):
    """A canopy of individual folded leaf blades on an ellipsoid shell around c.

    Each blade is a diamond folded along its vein. The base keeps the canopy colour; the tip shifts
    toward the glow colour and carries the glow in vertex alpha. A fraction `lit` of the leaves glow
    over their whole length, so the canopy sparkles rather than glowing as one flat sheet.
    """
    c = np.asarray(c, np.float64)
    r = np.broadcast_to(np.asarray(r, np.float64), (3,))
    d = rng.normal(0, 1, (count, 3))
    d[:, 2] = np.abs(d[:, 2]) * .45 + d[:, 2] * .55  # a little denser on top, but the underside is covered too
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    depth = shell + (1 - shell) * rng.uniform(0, 1, count) ** .5
    base = c + d * r * depth[:, None]
    # Blade direction: outward, drooping, with a random twist around the outward axis.
    side = np.cross(d, np.array([0, 0, 1.]))
    side_len = np.linalg.norm(side, axis=1, keepdims=True)
    side = np.where(side_len > 1e-3, side / np.maximum(side_len, 1e-6), np.array([1., 0, 0]))
    up = np.cross(side, d)
    twist = rng.uniform(-math.pi, math.pi, count)[:, None]
    along = np.cos(twist) * up + np.sin(twist) * side
    along = along * (1 - droop) + d * .35 + np.array([0, 0, -droop])
    along /= np.linalg.norm(along, axis=1, keepdims=True)
    across = np.cross(d, along)
    across /= np.maximum(np.linalg.norm(across, axis=1, keepdims=True), 1e-6)
    length = rng.uniform(*size, count)[:, None]
    width = length * rng.uniform(.28, .4, count)[:, None]
    fold = d * width * .35
    tip = base + along * length
    mid = base + along * length * .45
    left = mid - across * width - fold
    right = mid + across * width - fold
    verts = np.stack([base, left, tip, right], 1).reshape(-1, 3)
    n = np.arange(count) * 4
    faces = np.concatenate([np.stack([n, n + 1, n + 2], 1), np.stack([n, n + 2, n + 3], 1)]).tolist()
    colour = np.asarray(colour, np.float64)
    glow = np.asarray(glow, np.float64)
    shade = (.55 + .6 * np.clip((base[:, 2] - c[2]) / r[2] * .5 + .5, 0, 1))[:, None]
    tint = rng.uniform(.85, 1.15, (count, 1))
    body = np.concatenate([colour[None, :3] * shade * tint, np.full((count, 1), colour[3])], 1)
    shine = rng.uniform(0, 1, count) < lit
    tipc = body.copy()
    tipc[:, :3] = body[:, :3] * .4 + glow[None, :3] * .6
    tipc[:, 3] = np.where(shine, 1.0, .45)
    edge = body.copy()
    edge[:, :3] = body[:, :3] * .8 + glow[None, :3] * .2
    edge[:, 3] = np.where(shine, .8, colour[3])
    root = body.copy()
    root[:, 3] = np.where(shine, .6, 0)
    cols = np.stack([root, edge, tipc, edge], 1).reshape(-1, 4)
    base_index = len(part.v)
    part.v.extend(verts.tolist())
    part.c.extend(cols.tolist())
    for face in faces:
        part.f.append([base_index + i for i in face])
        part.m.append(slot)
        part.s.append(True)


def twigs(part, start, reach, count, rng, colour=None):
    """Thin twigs fanning out of a branch tip, so leaf clusters hang off wood rather than air."""
    colour = BARK if colour is None else colour
    ends = []
    for k in range(count):
        a = rng.uniform(0, 2 * math.pi)
        end = np.asarray(start) + np.array([math.cos(a) * reach * rng.uniform(.5, 1), math.sin(a) * reach * rng.uniform(.5, 1), rng.uniform(-.3, 1.2)])
        tube(part, bezier(start, start + (end - start) * .4 + (0, 0, .4), end - (0, 0, .2), end, 4), np.linspace(.1, .03, 4), colour, 0, 4, False)
        ends.append(end)
    return ends


def tree_glow(variant):
    rng = np.random.default_rng(10 + variant)
    p = Part('SM_CT_GlowTree%d' % variant, (SOLID, LEAF, GLOW))
    leaf = (LEAF_TEAL, LEAF_BLUE, LEAF_VIOLET)[variant % 3]
    light = (GLOW_CYAN, GLOW_CYAN, GLOW_ROSE)[variant % 3]
    height_m = 16 + variant * 4
    lean = rng.uniform(-3, 3, 2)
    trunk = bezier((0, 0, -1), (lean[0] * .3, lean[1] * .3, height_m * .35), (lean[0], lean[1], height_m * .65), (lean[0] * 1.2, lean[1] * 1.2, height_m), 14)
    trunk[:, :2] += np.sin(np.linspace(0, 3, 14))[:, None] * rng.uniform(-.8, .8, 2)
    tube(p, trunk, np.linspace(1.5 + variant * .2, .45, 14), BARK, 0, 10, shade=lambda v: .8 + .4 * (v[:, 2] / height_m))
    # Root flare.
    for k in range(6):
        a = k / 6 * 2 * math.pi + rng.uniform(-.3, .3)
        tube(p, bezier((0, 0, 1.5), (math.cos(a) * 1.5, math.sin(a) * 1.5, .8), (math.cos(a) * 3, math.sin(a) * 3, .1), (math.cos(a) * 4.2, math.sin(a) * 4.2, -.6), 6),
             np.linspace(.7, .15, 6), BARK, 0, 6)
    tips = []
    for k in range(5 + variant):
        t = rng.uniform(.45, .9)
        start = trunk[int(t * 13)]
        a = rng.uniform(0, 2 * math.pi)
        reach = rng.uniform(4, 7)
        end = start + np.array([math.cos(a) * reach, math.sin(a) * reach, rng.uniform(1.5, 4)])
        tube(p, bezier(start, start + (end - start) * .3 + (0, 0, 1), end - (0, 0, 1), end, 7), np.linspace(.45, .12, 7), BARK, 0, 6)
        tips.append(end)
    tips.append(trunk[-1])
    for i, t in enumerate(tips):
        for j, end in enumerate(twigs(p, t, 2.2, 3, rng)):
            c = end + rng.uniform(-.6, .6, 3) * (1, 1, .4) + (0, 0, .5)
            r = rng.uniform(2.0, 2.9)
            # A dim core keeps the crown dense; the blades make its surface.
            blob(p, c, (r * .42, r * .42, r * .3), jitter(leaf, rng) * (.6, .6, .6, 0), 1, 1, .2, rng.integers(1000))
            leaves(p, c, (r, r, r * .72), 360, jitter(leaf, rng), light, rng)
        # Hanging lantern fruit glows under the canopy.
        for j in range(3):
            hang = t + rng.uniform(-2.2, 2.2, 3) * (1, 1, 0) - (0, 0, rng.uniform(1.4, 3.0))
            tube(p, [hang + (0, 0, 1.6), hang + (0, 0, .2)], .03, BARK, 0, 4, False)
            blob(p, hang, (.32, .32, .42), light, 2, 1, .05, j)
    return p


def willow():
    rng = np.random.default_rng(31)
    p = Part('SM_CT_Willow', (SOLID, LEAF, GLOW))
    trunk = bezier((0, 0, -1), (1, 0, 5), (-1, .5, 9), (0, 0, 12), 10)
    tube(p, trunk, np.linspace(1.3, .5, 10), BARK, 0, 9)
    blob(p, (0, 0, 13), (2.6, 2.6, 1.2), LEAF_BLUE * (.6, .6, .6, 0), 1, 2, .15, 3)
    leaves(p, (0, 0, 13), (5.5, 5.5, 3), 1400, LEAF_BLUE, GLOW_CYAN, rng, size=(.4, .7), droop=.7)
    for k in range(70):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(2.5, 5.6)
        top = np.array([math.cos(a) * r, math.sin(a) * r, 12.5 + rng.uniform(-.5, .8)])
        length = rng.uniform(5, 10)
        strand = bezier(top, top + (math.cos(a) * .8, math.sin(a) * .8, -length * .3), top + (math.cos(a) * 1.2, math.sin(a) * 1.2, -length * .7), top + (math.cos(a) * 1.4, math.sin(a) * 1.4, -length), 8)
        tone = np.tile(LEAF_TEAL, (16, 1))
        tone[-6:] = GLOW_CYAN * np.array([.7, .7, .7, 1])
        tone[-6:, 3] = np.linspace(.2, 1, 6).repeat(1)
        ribbon(p, strand, .05, tone, 1, normal=(math.cos(a), math.sin(a), 0))
        # Small leaves hang all along each strand, glowing brighter toward the end.
        for q in range(1, 8):
            leaves(p, strand[q], (.35, .35, .45), 6, LEAF_TEAL, GLOW_CYAN, rng, size=(.18, .3), droop=.9, lit=q / 9, shell=.2)
    return p


def mushroom(variant):
    rng = np.random.default_rng(40 + variant)
    p = Part('SM_CT_Mushroom%d' % variant, (SOLID, GLOW))
    for k in range(3 if variant else 1):
        off = np.array([0, 0, 0]) if k == 0 else np.append(rng.uniform(-3, 3, 2), 0)
        s = 1 if k == 0 else rng.uniform(.4, .6)
        h = (6 if variant == 0 else 3.5) * s
        stem = bezier(off, off + (rng.uniform(-.5, .5), rng.uniform(-.5, .5), h * .4), off + (rng.uniform(-.8, .8), 0, h * .8), off + (0, 0, h), 8)
        tube(p, stem, np.linspace(.6, .35, 8) * s * (2 if variant == 0 else 1.2), col(.55, .5, .6), 0, 10)
        cap_r = (5 if variant == 0 else 2.6) * s
        top = stem[-1]
        tint = (GLOW_ROSE, GLOW_CYAN)[variant % 2]
        lathe(p, [(0, .9), (cap_r * .5, .75), (cap_r * .9, .3), (cap_r, -.15), (cap_r * .85, -.3)], col(*(tint[:3] * .35), .25), 0, 28, top)
        lathe(p, [(cap_r * .84, -.32), (cap_r * .4, -.1), (.2, -.05)], tint, 1, 28, top)
        for j in range(8):
            a = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(.3, .8) * cap_r
            blob(p, top + (math.cos(a) * rr, math.sin(a) * rr, .95 - rr / cap_r * .7), .22 * s * (2 if variant == 0 else 1), col(1, .95, .9, .6), 1, 1, .1, j)
    return p


def reeds():
    rng = np.random.default_rng(50)
    p = Part('SM_CT_Reeds', (LEAF, GLOW))
    for k in range(34):
        base = np.append(rng.normal(0, .7, 2), -.3)
        h = rng.uniform(1.6, 3.4)
        bend = rng.uniform(-.6, .6, 2)
        blade = bezier(base, base + (0, 0, h * .4), base + (bend[0] * .5, bend[1] * .5, h * .8), base + (bend[0], bend[1], h), 6)
        ribbon(p, blade, np.linspace(.05, .005, 6), jitter(col(.05, .14, .1, .05), rng, .2), 0, normal=(rng.uniform(-1, 1), rng.uniform(-1, 1), 0))
        if k % 3 == 0:
            blob(p, blade[-1] + (0, 0, .1), (.06, .06, .22), GLOW_LIME if k % 2 else GLOW_CYAN, 1, 1, 0, k)
    return p


def lily():
    rng = np.random.default_rng(60)
    p = Part('SM_CT_Lily', (SOLID, GLOW))
    for k in range(5):
        c = np.append(rng.normal(0, 1.4, 2), .02)
        r = rng.uniform(.5, 1.0)
        ang = np.linspace(.3, 2 * math.pi - .1, 18)
        ring = np.stack([np.cos(ang) * r, np.sin(ang) * r, np.zeros(18)], 1) + c
        p.add(np.concatenate([[c], ring]), [[0, i + 1, i + 2] for i in range(17)], col(.03, .13, .08, .08), 0, True)
        if k % 2 == 0:
            for j in range(6):
                a = j / 6 * 2 * math.pi
                prism(p, c + (0, 0, .05), c + (math.cos(a) * .35, math.sin(a) * .35, .45), .08, GLOW_ROSE, 1, 4, .5, True)
            blob(p, c + (0, 0, .2), .12, GLOW_GOLD, 1, 1, 0, k)
    return p


def fern():
    rng = np.random.default_rng(70)
    p = Part('SM_CT_Fern', (LEAF,))
    for k in range(12):
        a = k / 12 * 2 * math.pi + rng.uniform(-.2, .2)
        reach = rng.uniform(1.2, 2.0)
        frond = bezier((0, 0, 0), (math.cos(a) * reach * .3, math.sin(a) * reach * .3, 1.0), (math.cos(a) * reach * .8, math.sin(a) * reach * .8, 1.1), (math.cos(a) * reach, math.sin(a) * reach, .4), 9)
        tone = np.tile(col(.03, .12, .1, .1), (18, 1))
        tone[-4:, 3] = .7
        tone[-4:, :3] = GLOW_CYAN[:3] * .5
        ribbon(p, frond, .18 * np.sin(np.linspace(.2, 3.0, 9)), tone, 0)
    return p


def grass():
    rng = np.random.default_rng(80)
    p = Part('SM_CT_Grass', (LEAF,))
    for k in range(60):
        base = np.append(rng.normal(0, .6, 2), -.05)
        h = rng.uniform(.4, 1.0)
        tip = base + np.append(rng.normal(0, .25, 2), h)
        tone = np.tile(jitter(col(.03, .1, .07, 0), rng, .3), (6, 1))
        tone[-2:, 3] = .25
        ribbon(p, bezier(base, base + (0, 0, h * .5), tip - (0, 0, h * .2), tip, 3), np.linspace(.035, .004, 3), tone, 0,
               normal=(rng.uniform(-1, 1), rng.uniform(-1, 1), .1))
    return p


def flowers():
    rng = np.random.default_rng(90)
    p = Part('SM_CT_Flowers', (LEAF, GLOW))
    for k in range(9):
        base = np.append(rng.normal(0, .5, 2), 0)
        h = rng.uniform(.5, 1.2)
        stem = bezier(base, base + (0, 0, h * .6), base + (.2, 0, h), base + (.35, 0, h * .85), 6)
        ribbon(p, stem, .02, col(.03, .1, .06), 0)
        tone = (GLOW_CYAN, GLOW_ROSE, GLOW_GOLD)[k % 3]
        lathe(p, [(0, 0), (.08, -.05), (.16, -.22), (.12, -.3)], tone, 1, 6, stem[-1])
    return p


def crystal_cluster(variant):
    rng = np.random.default_rng(100 + variant)
    p = Part('SM_CT_Crystal%d' % variant, (GLASS, SOLID))
    tone = (CRYSTAL, CRYSTAL_VIOLET, col(.4, 1., .85, .75))[variant]
    scale = (1.5, 3.2, 6.0)[variant]
    blob(p, (0, 0, -.2 * scale), (1.3 * scale, 1.3 * scale, .5 * scale), STONE_DARK, 1, 1, .3, variant, smooth=False)
    for k in range(9 + variant * 3):
        a = rng.uniform(0, 2 * math.pi)
        tilt = rng.uniform(0, .7) if k else 0
        length = rng.uniform(.8, 2.4) * scale * (1.6 if k == 0 else 1)
        d = np.array([math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)])
        base = np.append(rng.normal(0, .35 * scale, 2), 0)
        prism(p, base, base + d * length, rng.uniform(.12, .3) * scale, jitter(tone, rng, .15), 0)
    return p


def rock(variant):
    rng = np.random.default_rng(120 + variant)
    p = Part('SM_CT_Rock%d' % variant, (SOLID, GLOW))
    size = (1.6, 4.0, 9.0)[variant]
    blob(p, (0, 0, size * .25), (size, size * .8, size * .6), STONE, 0, 2, .3, variant, smooth=False,
         shade=lambda v: .6 + .5 * np.clip(v[:, 2] / size, 0, 1))
    # Glowing moss rim on top.
    blob(p, (0, 0, size * .72), (size * .7, size * .55, size * .12), col(.06, .22, .14, .45), 0, 2, .25, variant + 9)
    if variant:
        for k in range(6):
            a = rng.uniform(0, 2 * math.pi)
            prism(p, (math.cos(a) * size * .5, math.sin(a) * size * .4, size * .5), (math.cos(a) * size * .9, math.sin(a) * size * .7, size * 1.1), .12 * size, CRYSTAL, 1, 5)
    return p


def roots():
    rng = np.random.default_rng(130)
    p = Part('SM_CT_RootArch', (SOLID, GLOW))
    for k in range(5):
        off = rng.normal(0, .8, 3)
        arch = bezier((-9 + off[0], off[1], -1), (-6, off[1], 9 + off[2]), (6, off[1] * .5, 9 - off[2]), (9 - off[0], -off[1], -1), 14)
        tube(p, arch, np.linspace(1.0, .6, 14) * rng.uniform(.6, 1.1), BARK, 0, 8, twist=.2)
    for k in range(18):
        t = rng.uniform(.15, .85)
        pt = bezier((-9, 0, -1), (-6, 0, 9), (6, 0, 9), (9, 0, -1), 50)[int(t * 49)]
        blob(p, pt + rng.normal(0, .5, 3), .18, GLOW_CYAN, 1, 1, 0, k)
    return p


def root_bridge():
    rng = np.random.default_rng(131)
    p = Part('SM_CT_RootBridge', (SOLID, GLOW))
    # Flat walkable deck of braided roots, 20 m long, 4 m wide, top at z=0.
    for k in range(7):
        y = -1.7 + k * .55
        line = np.stack([np.linspace(-10, 10, 16), np.full(16, y) + np.sin(np.linspace(0, 6, 16) + k) * .12, -.35 + np.sin(np.linspace(0, 3.14, 16)) * .0], 1)
        tube(p, line, .32, BARK_LIGHT if k % 2 else BARK, 0, 7, twist=.4)
    for side in (-2.1, 2.1):
        rail = np.stack([np.linspace(-10, 10, 16), np.full(16, side), .6 + .25 * np.sin(np.linspace(0, 9, 16))], 1)
        tube(p, rail, .14, BARK, 0, 6)
        for x in np.linspace(-9, 9, 8):
            blob(p, (x, side, .7), .14, GLOW_CYAN, 1, 1, 0, int(x))
    return p


# ---------------------------------------------------------------- architecture

def human_arch():
    p = Part('SM_CA_HumanArch', (SOLID, GLOW))
    for side in (-1, 1):
        box(p, (0, side * 6, 5), (1.2, 1.2, 5), CONCRETE)
        box(p, (0, side * 6, .4), (1.6, 1.6, .4), STONE)
    arc = bezier((0, -6, 10), (0, -4, 13.5), (0, 4, 13.5), (0, 6, 10), 12)
    tube(p, arc, 1.1, CONCRETE, 0, 4, smooth=False)
    # Broken edge and a dead strip light that the Center has re-lit.
    box(p, (1.25, 0, 12.6), (.06, 3, .12), GLOW_GOLD, 1)
    box(p, (0, 4.5, 14.5), (1.0, 1.4, .6), CONCRETE, 0, 25)
    return p


def human_pillar():
    p = Part('SM_CA_HumanPillar', (SOLID, GLOW))
    box(p, (0, 0, .5), (1.4, 1.4, .5), STONE)
    box(p, (0, 0, 4.5), (.9, .9, 3.5), CONCRETE)
    box(p, (.2, .1, 8.6), (.8, .7, .6), CONCRETE, 0, 12)
    for z in (2.0, 5.0):
        box(p, (0, 0, z), (.95, .95, .08), METAL)
    box(p, (.92, 0, 3.4), (.04, .25, 1.6), GLOW_CYAN, 1)
    return p


def human_wall():
    rng = np.random.default_rng(140)
    p = Part('SM_CA_HumanWall', (SOLID, GLOW))
    for i in range(6):
        x = -10 + i * 4
        h = rng.uniform(3, 8) if i not in (2, 3) else 8
        box(p, (x, 0, h / 2), (2, .6, h / 2), CONCRETE if i % 2 else col(.22, .21, .2), 0, shade=lambda v: .7 + .04 * v[:, 2])
        if h > 6:
            box(p, (x, -.62, h - 2), (1.2, .03, .7), col(.05, .08, .1, .35), 1)
    box(p, (0, 0, 8.4), (12, .7, .4), METAL)
    return p


def human_stairs():
    p = Part('SM_CA_HumanStairs', (SOLID, GLOW))
    for i in range(14):
        box(p, (i * .8, 0, i * .4 + .2), (.4, 4, .2 + i * .2), CONCRETE if i % 2 else STONE, 0)
    for side in (-4.1, 4.1):
        for i in range(0, 14, 3):
            box(p, (i * .8, side, i * .4 + 1.6), (.08, .08, .8), METAL)
            box(p, (i * .8, side, i * .4 + 2.45), (.12, .12, .06), GLOW_GOLD, 1)
    return p


def human_dish():
    p = Part('SM_CA_Dish', (SOLID, GLOW))
    box(p, (0, 0, 3), (2.5, 2.5, 3), CONCRETE)
    tube(p, [(0, 0, 6), (0, 0, 9)], .6, METAL, 0, 10)
    prof = [(0, 0), (4, .6), (8, 2.2), (11, 4.5), (11.2, 4.7)]
    v = [(r, z) for r, z in prof]
    lathe(p, v, col(.4, .42, .45), 0, 36, (0, 0, 9))
    for k in range(3):
        a = k / 3 * 2 * math.pi
        tube(p, [(math.cos(a) * 9, math.sin(a) * 9, 12.5), (0, 0, 19)], .15, METAL, 0, 6)
    blob(p, (0, 0, 19), .6, GLOW_GOLD, 1, 1, 0, 1)
    return p


def lamp():
    p = Part('SM_CA_Lamp', (SOLID, GLOW))
    tube(p, [(0, 0, 0), (0, 0, 4.2), (.6, 0, 4.8), (1.2, 0, 4.8)], .1, METAL, 0, 8)
    box(p, (0, 0, .3), (.35, .35, .3), STONE)
    box(p, (1.25, 0, 4.6), (.35, .2, .1), METAL)
    box(p, (1.25, 0, 4.48), (.28, .14, .03), GLOW_GOLD, 1)
    return p


def first_ring():
    p = Part('SM_CA_FirstRing', (SOLID, GLASS, GLOW))
    torus(p, (0, 0, 13), 12, 1.0, FIRST_WHITE, 0, 64, 8)
    torus(p, (0, 0, 13), 12, .3, GLOW_CYAN, 2, 64, 6, smooth=True)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        c = np.array([0, math.cos(a) * 12, 13 + math.sin(a) * 12])
        prism(p, c, c + np.array([0, math.cos(a), math.sin(a)]) * 3.4, .6, CRYSTAL, 1, 6)
    for side in (-1, 1):
        prism(p, (0, side * 10, -1), (0, side * 9, 4), 1.6, FIRST_WHITE, 0, 6, .4)
    return p


def first_monolith():
    p = Part('SM_CA_Monolith', (SOLID, GLASS, GLOW))
    prism(p, (0, 0, -1), (0, 0, 22), 2.2, FIRST_WHITE, 0, 4, .2)
    prism(p, (0, 0, -1), (0, 0, 22.4), 2.32, col(.15, .6, 1, .9), 1, 4, .2)
    for z in range(3, 20, 4):
        box(p, (0, 0, z), (2.4, 2.4, .12), FIRST_GOLD, 0, 45)
    return p


def first_spire():
    rng = np.random.default_rng(150)
    p = Part('SM_CA_Spire', (SOLID, GLASS, GLOW))
    prism(p, (0, 0, -2), (0, 0, 48), 4, FIRST_WHITE, 0, 6, .45)
    for k in range(10):
        z = rng.uniform(6, 34)
        a = rng.uniform(0, 2 * math.pi)
        prism(p, (math.cos(a) * 2, math.sin(a) * 2, z), (math.cos(a) * 9, math.sin(a) * 9, z + rng.uniform(2, 9)), rng.uniform(.4, 1), CRYSTAL, 1, 6)
    for z in (8, 18, 30):
        torus(p, (0, 0, z), 5.5 - z * .07, .18, GLOW_CYAN, 2, 40, 6, axis='z')
    return p


def first_platform():
    p = Part('SM_CA_Platform', (SOLID, GLASS, GLOW))
    # Hexagonal floating stone, top at z=0, 6 m across: the puzzle platform.
    ang = np.linspace(0, 2 * math.pi, 7)[:-1]
    top = np.stack([np.cos(ang) * 3, np.sin(ang) * 3, np.zeros(6)], 1)
    rim = np.stack([np.cos(ang) * 3, np.sin(ang) * 3, np.full(6, -.6)], 1)
    keel = np.array([[0, 0, -3.5]])
    verts = np.concatenate([top, rim, keel])
    faces = [[0, 1, 2, 3, 4, 5]] + [[j, 6 + j, 6 + (j + 1) % 6, (j + 1) % 6] for j in range(6)] + [[6 + j, 12, 6 + (j + 1) % 6] for j in range(6)]
    p.add(verts, faces, FIRST_WHITE, 0, False, shade=lambda v: .55 + .15 * (v[:, 2] + 3.5))
    torus(p, (0, 0, .02), 2.4, .06, GLOW_CYAN, 2, 36, 4, axis='z')
    prism(p, (0, 0, -3.2), (0, 0, -5.5), .5, CRYSTAL, 1, 6, .8)
    return p


def light_arch():
    """The Center's own style: a First One crystal arch that human stone and living roots grew into."""
    rng = np.random.default_rng(160)
    p = Part('SM_CA_LightArch', (SOLID, GLASS, GLOW))
    arc = bezier((0, -8, -1), (0, -7, 14), (0, 7, 14), (0, 8, -1), 18)
    tube(p, arc, np.linspace(1.4, 1.0, 18), FIRST_WHITE, 0, 6, smooth=False)
    for k in range(4):
        off = rng.normal(0, .7, 3)
        tube(p, arc + off * (1, 0, .3) + rng.normal(0, .3, (18, 3)), .45, BARK, 0, 7, twist=.4)
    for i in range(1, 17, 2):
        c = arc[i]
        prism(p, c, c + (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(2, 3.5)), .35, CRYSTAL, 1, 6)
    for side in (-1, 1):
        box(p, (0, side * 8, .5), (2, 2, 1.5), CONCRETE, 0, 15 * side)
    tube(p, arc + (0, 0, -.9), .12, GLOW_CYAN, 2, 5)
    return p


def lantern():
    p = Part('SM_CA_Lantern', (SOLID, GLASS, GLOW))
    lathe(p, [(1.0, 0), (1.0, .3), (.4, .5), (.3, 2.0), (.6, 2.3), (.6, 2.5)], STONE, 0, 12)
    for k in range(4):
        a = k / 4 * 2 * math.pi
        tube(p, [(math.cos(a) * .55, math.sin(a) * .55, 2.5), (math.cos(a) * .3, math.sin(a) * .3, 3.6), (0, 0, 4.0)], .06, BARK, 0, 5)
    prism(p, (0, 0, 2.6), (0, 0, 3.7), .26, CRYSTAL, 1, 6, .4)
    return p


def shrine():
    p = Part('SM_CA_Shrine', (SOLID, GLASS, GLOW))
    lathe(p, [(6, 0), (6, .4), (5.4, .5), (5.4, .9), (4.6, 1.0), (0, 1.0)], STONE, 0, 32, (0, 0, -.5))
    torus(p, (0, 0, .52), 4.9, .07, GLOW_CYAN, 2, 48, 4, axis='z')
    for k in range(6):
        a = k / 6 * 2 * math.pi
        prism(p, (math.cos(a) * 5.6, math.sin(a) * 5.6, .4), (math.cos(a) * 5.9, math.sin(a) * 5.9, 5 + (k % 2) * 2), .5, FIRST_WHITE, 0, 4, .3)
    return p


def stillstone():
    p = Part('SM_CA_Stillstone', (SOLID, GLASS, GLOW))
    prism(p, (0, 0, -.5), (0, 0, .5), .3, CRYSTAL, 1, 8, .5)
    prism(p, (0, 0, .5), (0, 0, -.5), .3, CRYSTAL, 1, 8, .5)
    torus(p, (0, 0, 0), .42, .03, GLOW_GOLD, 2, 32, 4, axis='z')
    return p


def artifact():
    """The Heartbloom: the artifact that teaches Physis to Mend."""
    p = Part('SM_CA_Artifact', (SOLID, GLASS, GLOW))
    for k in range(8):
        a = k / 8 * 2 * math.pi
        petal = bezier((0, 0, 0), (math.cos(a) * .5, math.sin(a) * .5, .3), (math.cos(a) * .8, math.sin(a) * .8, .9), (math.cos(a) * .3, math.sin(a) * .3, 1.4), 8)
        tube(p, petal, np.linspace(.1, .02, 8), CRYSTAL if k % 2 else col(.6, 1., .7, .8), 1, 5)
    blob(p, (0, 0, .6), .32, GLOW_GOLD, 2, 2, .05, 4)
    for r in (.9, 1.25):
        torus(p, (0, 0, .6), r, .025, GLOW_CYAN, 2, 40, 4)
    return p


def barrier():
    """A Divinity-thorn barrier: weaponized crystal only Settle dissolves. 12 m wide, 7 m tall."""
    rng = np.random.default_rng(170)
    p = Part('SM_CA_Barrier', (GLASS, SOLID))
    for k in range(46):
        x = rng.uniform(-6, 6)
        base = np.array([rng.uniform(-.8, .8), x, -.5])
        tip = base + (rng.uniform(-1.6, 1.6), rng.uniform(-1, 1), rng.uniform(3, 7.5))
        prism(p, base, tip, rng.uniform(.18, .5), col(1., .25, .45, .85) if k % 4 else col(.9, .55, 1., .9), 0, 5, .55)
    for x in np.linspace(-6, 6, 7):
        blob(p, (0, x, 0), (1, 1.2, .6), STONE_DARK, 1, 1, .3, int(x * 3), smooth=False)
    return p



# ---------------------------------------------------------------- ability gates and augmentations (vaults)
# Gates are 12 m wide along their local Y and 7 m tall, like the Settle barrier, so the scenario places
# every kind the same way in a wall gap. Each future ability has its own colour: Light Step gold,
# Dissonance violet, Sit With (memory) deep blue, Resonance cyan, Reweave green, Trace Reading amber.

GATE_POST = col(.1, .1, .12)
GLOW_VIOLET = col(.7, .35, 1., 1.)
GLOW_DEEP = col(.35, .55, 1., 1.)
GLOW_AMBER = col(1., .62, .2, 1.)
GLOW_GREEN = col(.35, 1., .45, 1.)


def gate_frame(p, colour):
    for side in (-1, 1):
        box(p, (0, side * 6.25, 3.6), (.45, .45, 4.1), GATE_POST)
        box(p, (0, side * 6.25, 7.75), (.6, .6, .15), colour, 2)
    box(p, (0, 0, 7.4), (.35, 6.7, .25), GATE_POST)


def gate_light():
    """Light Step lattice: hardened light, bars 40 cm apart, which only someone moving as light can cross.
    The bars are glowing crystal (the glass slot), not the glow slot: glow sections never collide."""
    p = Part('SM_CA_GateLight', (SOLID, GLASS, GLOW))
    gate_frame(p, GLOW_GOLD)
    bar = col(1., .75, .3, .9)
    for y in np.arange(-5.8, 5.81, .4):
        tube(p, [(0, y, -.5), (0, y, 7.2)], .045, bar, 1, 5)
    for z in np.arange(.4, 7.2, .8):
        tube(p, [(0, -6., z), (0, 6., z)], .035, bar, 1, 5)
    return p


def gate_dissonance():
    """Dissonance field: a standing wave of violet light filling the opening, double-sided."""
    p = Part('SM_CA_GateDissonance', (SOLID, GLASS, GLOW))
    gate_frame(p, GLOW_VIOLET)
    ys, zs = np.linspace(-6, 6, 33), np.linspace(-.5, 7.2, 17)
    verts = [(.18 * math.sin(y * 1.7 + z * 1.1) * math.cos(z * .9), y, z) for z in zs for y in ys]
    n = len(ys)
    faces = []
    for i in range(len(zs) - 1):
        for j in range(n - 1):
            a, b, c2, d = i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j
            faces += [[a, b, c2, d], [a, d, c2, b]]
    p.add(verts, faces, col(.55, .3, 1., .85), 1, True)
    for z in (1.5, 3.8, 6.1):
        tube(p, [(0, y, z + .25 * math.sin(y)) for y in np.linspace(-6, 6, 13)], .05, GLOW_VIOLET, 2, 5, cap=False)
    return p


def gate_memory():
    """Sit With door: a sealed door of grief, two stone leaves with a circle of deep blue light."""
    p = Part('SM_CA_GateMemory', (SOLID, GLASS, GLOW))
    gate_frame(p, GLOW_DEEP)
    for side in (-1, 1):
        box(p, (0, side * 2.95, 3.35), (.3, 2.95, 3.85), col(.12, .14, .2))
        box(p, (.32, side * 2.95, 3.35), (.04, 2.5, 3.4), col(.08, .09, .14))
    torus(p, (.4, 0, 3.6), 1.9, .07, GLOW_DEEP, 2, 48, 5, axis='x')
    torus(p, (.4, 0, 3.6), 1.2, .05, GLOW_DEEP, 2, 40, 5, axis='x')
    blob(p, (.45, 0, 3.6), .35, GLOW_DEEP, 2, 1, .05, 7)
    return p


def node_resonance():
    """Resonance node: a cyan crystal floating over its stone base, ringed twice."""
    p = Part('SM_CA_NodeResonance', (SOLID, GLASS, GLOW))
    cylinder(p, (0, 0, -.2), .9, .6, STONE_DARK, 0, 8, .7, False)
    prism(p, (0, 0, 1.6), (0, 0, 3.2), .45, CRYSTAL, 1, 6, .45)
    prism(p, (0, 0, 1.6), (0, 0, .8), .45, CRYSTAL, 1, 6, .45)
    for z, r in ((1.6, 1.0), (1.6, 1.35)):
        torus(p, (0, 0, z), r, .04, GLOW_CYAN, 2, 40, 4, axis='z')
    return p


def anchor_reweave():
    """Reweave anchor: a broken green-banded stele, its fragments hanging where they used to be."""
    rng = np.random.default_rng(311)
    p = Part('SM_CA_AnchorReweave', (SOLID, GLASS, GLOW))
    box(p, (0, 0, 1.2), (.45, .7, 1.4), FIRST_WHITE)
    for z in (.7, 1.6, 2.4):
        torus(p, (0, 0, z), .95, .05, GLOW_GREEN, 2, 32, 4, axis='z', arc=4.4)
    for k in range(7):
        box(p, (rng.uniform(-.5, .5), rng.uniform(-.8, .8), 2.9 + k * .32), (.2, .3, .12), FIRST_WHITE, 0, rng.uniform(0, 90))
    blob(p, (0, 0, 2.9), .25, GLOW_GREEN, 2, 1, .05, 9)
    return p


def echo_trace():
    """Trace echo: an amber crystal where the past is thin; shards of the moment orbit it."""
    p = Part('SM_CA_EchoTrace', (SOLID, GLASS, GLOW))
    prism(p, (0, 0, 0), (0, 0, 2.6), .5, col(1., .6, .2, .75), 1, 5, .5)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        prism(p, (math.cos(a) * 1.1, math.sin(a) * 1.1, 1. + .25 * k), (math.cos(a) * 1.3, math.sin(a) * 1.3, 1.5 + .25 * k), .12, col(1., .7, .3, .8), 1, 4, .5)
    torus(p, (0, 0, 1.2), 1.2, .03, GLOW_AMBER, 2, 40, 4, axis='z')
    return p


def aug_shell(p, colour):
    """Every augmentation floats inside the same two gold rings, so they read as one family."""
    torus(p, (0, 0, 0), .62, .025, GLOW_GOLD, 2, 40, 4, axis='z')
    torus(p, (0, 0, 0), .62, .025, colour, 2, 40, 4, axis='x')


def aug_health():
    p = Part('SM_CA_AugHealth', (SOLID, GLASS, GLOW))
    for side in (-1, 1):
        blob(p, (0, side * .17, .12), .2, col(1., .3, .45, .9), 1, 2, .04, 3 + side)
    prism(p, (0, 0, .1), (0, 0, -.42), .3, col(1., .3, .45, .9), 1, 8, .9)
    aug_shell(p, GLOW_ROSE)
    return p


def aug_katana():
    p = Part('SM_CA_AugKatana', (SOLID, GLASS, GLOW))
    prism(p, (0, 0, -.15), (0, 0, .55), .07, col(.85, .95, 1., .9), 1, 4, .35)
    prism(p, (0, 0, -.15), (0, 0, -.45), .06, col(.85, .95, 1., .9), 1, 4, .4)
    torus(p, (0, 0, -.15), .16, .03, GLOW_GOLD, 2, 24, 4, axis='z')
    blob(p, (0, 0, -.15), .08, col(1., .25, .3, 1.), 2, 1, .05, 5)
    aug_shell(p, col(1., .3, .3, 1.))
    return p


def aug_pistol():
    p = Part('SM_CA_AugPistol', (SOLID, GLASS, GLOW))
    blob(p, (0, 0, 0), .2, col(1., .55, .15, .95), 2, 2, .08, 11)
    for k in range(3):
        a = k / 3 * 2 * math.pi
        tube(p, [(math.cos(a) * .3, math.sin(a) * .3, -.3), (math.cos(a) * .3, math.sin(a) * .3, .3)], .045, col(1., .7, .3, .9), 1, 6)
    aug_shell(p, GLOW_GOLD)
    return p


def aug_defense():
    p = Part('SM_CA_AugDefense', (SOLID, GLASS, GLOW))
    ang = np.linspace(0, 2 * math.pi, 6, endpoint=False)
    hexagon = [(0, math.cos(a) * .36, math.sin(a) * .36 + .02) for a in ang]
    verts = [(x - .06, y, z) for x, y, z in hexagon] + [(x + .06, y, z) for x, y, z in hexagon] + [(-.12, 0, .02), (.12, 0, .02)]
    faces = [[j, (j + 1) % 6, 6 + (j + 1) % 6, 6 + j] for j in range(6)] + [[12, (j + 1) % 6, j] for j in range(6)] + [[13, 6 + j, 6 + (j + 1) % 6] for j in range(6)]
    p.add(verts, faces, col(.35, .6, 1., .85), 1, False)
    torus(p, (0, 0, .02), .4, .03, GLOW_DEEP, 2, 6, 4, axis='x')
    aug_shell(p, GLOW_DEEP)
    return p


def aug_agility():
    p = Part('SM_CA_AugAgility', (SOLID, GLASS, GLOW))
    for side in (-1, 1):
        feather = bezier((0, 0, -.35), (0, side * .35, -.1), (0, side * .45, .25), (0, side * .15, .5), 9)
        tube(p, feather, np.linspace(.09, .015, 9), col(.5, 1., .55, .9), 1, 5)
    blob(p, (0, 0, -.3), .07, GLOW_LIME, 2, 1, .05, 13)
    aug_shell(p, GLOW_LIME)
    return p

def still_tree():
    """The landmark of the Glade, where Physis wakes: a vast crystal-veined tree."""
    rng = np.random.default_rng(180)
    p = Part('SM_CT_StillTree', (SOLID, LEAF, GLOW, GLASS))
    trunk = bezier((0, 0, -2), (3, 1, 14), (-3, -1, 26), (0, 0, 38), 18)
    tube(p, trunk, np.linspace(5.5, 2.0, 18), BARK, 0, 14, twist=.15)
    for k in range(7):
        sp = trunk + (rng.normal(0, .3, 3) * (1, 1, 0))
        tube(p, sp * (1, 1, 1) + np.array([math.cos(k), math.sin(k), 0]) * np.linspace(5, 2, 18)[:, None] * .85, .35, GLOW_CYAN * (1, 1, 1, 1), 2, 5, twist=.3)
    for k in range(9):
        a = k / 9 * 2 * math.pi
        tube(p, bezier((0, 0, 3), (math.cos(a) * 6, math.sin(a) * 6, 2), (math.cos(a) * 10, math.sin(a) * 10, 0), (math.cos(a) * 15, math.sin(a) * 15, -2), 8), np.linspace(2.2, .5, 8), BARK, 0, 8)
    tips = []
    for k in range(9):
        a = k / 9 * 2 * math.pi + rng.uniform(-.2, .2)
        start = trunk[rng.integers(10, 17)]
        end = start + (math.cos(a) * rng.uniform(12, 18), math.sin(a) * rng.uniform(12, 18), rng.uniform(3, 9))
        tube(p, bezier(start, start + (end - start) * .4 + (0, 0, 4), end - (0, 0, 2), end, 9), np.linspace(1.6, .4, 9), BARK, 0, 8)
        tips.append(end)
    tips.append(trunk[-1] + (0, 0, 3))
    for t in tips:
        for j, end in enumerate(twigs(p, t, 4.5, 4, rng)):
            c = end + rng.uniform(-1, 1, 3) * (1, 1, .4) + (0, 0, 1)
            r = rng.uniform(4.2, 6.2)
            blob(p, c, (r * .42, r * .42, r * .28), jitter(LEAF_BLUE, rng) * (.6, .6, .6, 0), 1, 1, .2, rng.integers(999))
            leaves(p, c, (r, r, r * .65), 900, jitter(LEAF_BLUE, rng), GLOW_CYAN, rng, size=(.6, 1.0), lit=.25)
        for j in range(5):
            hang = t + rng.uniform(-5, 5, 3) * (1, 1, 0) - (0, 0, rng.uniform(3, 6))
            tube(p, [hang + (0, 0, 3), hang], .05, BARK, 0, 4, False)
            prism(p, hang, hang - (0, 0, 1.2), .3, CRYSTAL, 3, 6, .5)
    return p


# ---------------------------------------------------------------- temple of the First Light

def temple_base():
    """Stepped plateau crown: 70 m square, entered by a broad southern stair. Floor top at z=6."""
    p = Part('SM_CA_TempleBase', (SOLID, GLOW, GLASS))
    for i, (half, z) in enumerate(((38, 0), (33, 2), (28, 4))):
        box(p, (0, 0, z + 1), (half, half, 1), STONE if i % 2 else col(.24, .23, .25), 0, 45 * 0)
        for side in (-1, 1):
            for axis in (0, 1):
                c = [0, 0, z + 2.05]
                c[axis] = side * (half - .3)
                h = [half, half, .05]
                h[axis] = .2
                box(p, c, h, GLOW_GOLD, 1)
    # Grand stair on the south (-X) face.
    for i in range(12):
        box(p, (-38 - 6 + i * .5, 0, i * .5 + .25), (.5 + (12 - i) * .5, 9, .25 + i * .25), CONCRETE if i % 2 else STONE)
    return p


def temple_colonnade():
    p = Part('SM_CA_TempleColonnade', (SOLID, GLOW, GLASS))
    count = 20
    for k in range(count):
        a = k / count * 2 * math.pi
        if abs(math.cos(a) + 1) < .05:
            continue  # the south door
        c = np.array([math.cos(a) * 24, math.sin(a) * 24, 0])
        cylinder(p, c, 1.3, 1.2, STONE, 0, 12)
        cylinder(p, c + (0, 0, 1.2), 1.0, 16, CONCRETE, 0, 12, .85)
        prism(p, c + (0, 0, 17.2), c + (0, 0, 20), 1.1, CRYSTAL, 2, 6, .6)
        cylinder(p, c + (0, 0, 16.9), .9, .3, GLOW_GOLD, 1, 12)
    torus(p, (0, 0, 20.5), 24, .9, FIRST_WHITE, 0, 80, 8, axis='z')
    torus(p, (0, 0, 20.5), 24, .28, GLOW_CYAN, 1, 80, 6, axis='z')
    return p


def temple_dome():
    p = Part('SM_CA_TempleDome', (SOLID, GLOW, GLASS))
    ribs = 16
    for k in range(ribs):
        a = k / ribs * 2 * math.pi
        arc = [(math.cos(a) * 24 * math.cos(t), math.sin(a) * 24 * math.cos(t), 21 + 18 * math.sin(t)) for t in np.linspace(0, math.pi / 2 * .92, 14)]
        tube(p, arc, np.linspace(.8, .4, 14), FIRST_WHITE, 0, 6, smooth=False)
        tube(p, np.array(arc) * (1, 1, 1) - (0, 0, .05), .16, GLOW_CYAN, 1, 4)
    torus(p, (0, 0, 21 + 18 * math.sin(math.pi / 2 * .92)), 24 * math.cos(math.pi / 2 * .92), .7, FIRST_GOLD, 0, 32, 6, axis='z')
    # Crystal oculus: light pours in here.
    prism(p, (0, 0, 46), (0, 0, 36), 3, CRYSTAL, 2, 8, .6)
    return p


def temple_gate():
    """The temple's ring door. It stands in the south gap of the colonnade; the barrier closes it."""
    p = Part('SM_CA_TempleGate', (SOLID, GLOW, GLASS))
    torus(p, (0, 0, 8), 8, .9, FIRST_WHITE, 0, 56, 8)
    torus(p, (0, 0, 8), 8, .25, GLOW_GOLD, 1, 56, 6)
    for side in (-1, 1):
        box(p, (0, side * 9.5, 5), (1.5, 1.5, 5), CONCRETE)
        box(p, (0, side * 9.5, 10.5), (1.7, 1.7, .5), FIRST_GOLD)
        prism(p, (0, side * 9.5, 11), (0, side * 9.5, 15), 1.2, CRYSTAL, 2, 6, .5)
    return p


def temple_sanctum():
    """Inner sanctum floor: the pool, the walk and the pedestal where the Heartbloom rests."""
    p = Part('SM_CA_TempleSanctum', (SOLID, GLOW, GLASS))
    lathe(p, [(20, 0), (20, .3), (12, .3), (12, -.8), (11.5, -.9), (0, -.9)], col(.12, .12, .15), 0, 48)
    torus(p, (0, 0, .32), 12, .08, GLOW_CYAN, 1, 64, 4, axis='z')
    box(p, (-13, 0, .15), (8, 2.2, .15), STONE)  # causeway from the gate
    box(p, (-5, 0, -.3), (5, 2.2, .3), STONE)
    lathe(p, [(3, -.9), (3, .5), (2.4, .7), (1.2, 1.0), (1.2, 2.2), (1.8, 2.5), (1.8, 2.7), (0, 2.7)], FIRST_WHITE, 0, 24)
    torus(p, (0, 0, 2.7), 1.6, .07, GLOW_GOLD, 1, 40, 4, axis='z')
    for k in range(6):
        a = k / 6 * 2 * math.pi
        prism(p, (math.cos(a) * 7, math.sin(a) * 7, -1), (math.cos(a) * 7.5, math.sin(a) * 7.5, 2.5 + k % 2), .7, CRYSTAL, 2, 6, .4)
    return p


# ---------------------------------------------------------------- creatures (ethereal, crystal)

def moth():
    p = Part('SM_CC_Moth', (GLASS, GLOW))
    tube(p, [(-.25, 0, 0), (0, 0, 0), (.3, 0, .02)], [.04, .07, .05], col(.3, .9, 1, .9), 1, 6)
    for side in (-1, 1):
        for k, (sx, sy) in enumerate(((.15, .55), (-.12, .4))):
            wing = np.array([(0, side * .04, 0), (sx + .15, side * sy * .6, .03), (sx, side * sy, .02), (sx - .2, side * sy * .7, 0)])
            p.add(wing, [[0, 1, 2, 3], [3, 2, 1, 0]], col(.4, .85, 1., .55) if k == 0 else col(.7, .5, 1., .55), 0, True)
    return p


def jelly():
    rng = np.random.default_rng(200)
    p = Part('SM_CC_Jelly', (GLASS, GLOW))
    lathe(p, [(0, 1.2), (.7, 1.05), (1.1, .6), (1.2, .1), (1.0, 0), (.6, .15), (0, .2)], col(.35, .75, 1., .55), 0, 20)
    blob(p, (0, 0, .7), .35, GLOW_ROSE, 1, 2, .1, 2)
    for k in range(12):
        a = k / 12 * 2 * math.pi
        top = np.array([math.cos(a) * .9, math.sin(a) * .9, .05])
        line = top + np.stack([np.sin(np.linspace(0, 4, 10) + k) * .15, np.cos(np.linspace(0, 4, 10) + k) * .15, -np.linspace(0, rng.uniform(2.5, 4), 10)], 1)
        tone = np.tile(col(.4, .8, 1, .7), (20, 1))
        ribbon(p, line, np.linspace(.05, .01, 10), tone, 0, normal=(math.cos(a), math.sin(a), 0))
    return p


def stag():
    """Glass Stag: a grazing crystal deer, about 2.4 m to the antler tips. Legs are their own pieces."""
    p = Part('SM_CC_Stag', (GLASS, SOLID, GLOW))
    body = bezier((-.8, 0, 1.3), (-.2, 0, 1.45), (.4, 0, 1.45), (.85, 0, 1.4), 8)
    tube(p, body, [.32, .4, .42, .42, .4, .38, .34, .3], col(.4, .8, 1., .45), 0, 12)
    neck = bezier((.8, 0, 1.45), (1.0, 0, 1.75), (1.1, 0, 1.95), (1.25, 0, 2.05), 6)
    tube(p, neck, np.linspace(.22, .14, 6), col(.4, .8, 1., .45), 0, 10)
    blob(p, (1.42, 0, 2.0), (.25, .13, .14), col(.45, .85, 1., .5), 0, 2, .05, 3)
    for side in (-1, 1):
        blob(p, (1.52, side * .08, 2.05), .03, GLOW_GOLD, 2, 1, 0, 5)
        for k, (dx, dz, dy) in enumerate(((.0, .6, .25), (.25, .45, .45), (-.2, .4, .55), (.1, .25, .7))):
            base = np.array([1.3, side * .08, 2.12])
            prism(p, base + (dx * .3, side * dy * .2, dz * .2), base + (dx, side * dy, dz + .3), .04, CRYSTAL, 0, 5, .5)
    for k, (x, side) in enumerate(((.65, -1), (.65, 1), (-.6, -1), (-.6, 1))):
        tube(p, [(x, side * .18, 1.25), (x + .05, side * .2, .7), (x - .03, side * .2, .06)], [.09, .06, .045], col(.5, .85, 1., .4), 0, 6)
    # Divinity core visible through the glass body.
    blob(p, (.2, 0, 1.4), .2, GLOW_CYAN, 2, 2, .1, 7)
    return p


def fox():
    p = Part('SM_CC_Fox', (GLASS, GLOW))
    tube(p, bezier((-.35, 0, .4), (-.1, 0, .45), (.15, 0, .45), (.35, 0, .45), 6), [.12, .15, .15, .15, .14, .12], col(.6, .5, 1., .5), 0, 10)
    blob(p, (.48, 0, .55), (.13, .09, .09), col(.65, .55, 1., .55), 0, 2, .05, 1)
    for side in (-1, 1):
        prism(p, (.47, side * .05, .62), (.45, side * .07, .78), .035, CRYSTAL_VIOLET, 0, 4, .6)
    tube(p, bezier((-.35, 0, .45), (-.6, 0, .55), (-.8, 0, .7), (-.9, 0, .9), 8), np.linspace(.08, .2, 8), col(.8, .5, 1., .85), 1, 8)
    for x in (.22, -.22):
        for side in (-1, 1):
            tube(p, [(x, side * .07, .38), (x, side * .07, .02)], .03, col(.6, .5, 1., .5), 0, 5)
    return p


def sky_whale():
    """A vast ethereal creature drifting high over the marsh: a living landmark."""
    p = Part('SM_CC_SkyWhale', (GLASS, GLOW))
    spine = bezier((-30, 0, 0), (-10, 0, 3), (10, 0, 3), (28, 0, -1), 20)
    radii = 6 * np.sin(np.linspace(.25, 3.0, 20)) ** .8 + .4
    tube(p, spine, radii, col(.25, .55, 1., .35), 0, 18)
    for side in (-1, 1):
        fin = np.array([(4, side * 4, -1), (-6, side * 22, -2), (-12, side * 20, -2.5), (-6, side * 4, -1)])
        p.add(fin, [[0, 1, 2, 3], [3, 2, 1, 0]], col(.4, .7, 1., .5), 0, True)
    tail = np.array([(-28, 0, 0), (-38, -9, 1), (-35, 0, 0), (-38, 9, 1)])
    p.add(tail, [[0, 1, 2], [0, 2, 3], [2, 1, 0], [3, 2, 0]], col(.4, .7, 1., .5), 0, True)
    for k in range(30):
        t = k / 29
        c = spine[int(t * 19)] + (0, 0, radii[int(t * 19)] * .9)
        blob(p, c, .5, GLOW_CYAN if k % 3 else GLOW_GOLD, 1, 1, 0, k)
    return p


# ---------------------------------------------------------------- enemies (crystal; levels by size and colour)

def shardling():
    """Level 1-2. A swarm-hunter: a cluster of red shards around a hungry core."""
    rng = np.random.default_rng(300)
    p = Part('SM_CE_Shardling', (GLASS, GLOW, SOLID))
    blob(p, (0, 0, 0), .35, col(1, .25, .3, 1), 1, 2, .15, 1)
    for k in range(12):
        d = rng.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        prism(p, d * .25, d * rng.uniform(.8, 1.3), .1, col(.9, .2, .35, .55), 0, 5, .5)
    return p


def wraith():
    """Level 3. A Prism Wraith: a hooded shape of shattered glass and trailing light."""
    rng = np.random.default_rng(310)
    p = Part('SM_CE_Wraith', (GLASS, GLOW, SOLID))
    lathe(p, [(0, 1.6), (.5, 1.4), (.8, .8), (.9, 0), (1.2, -1.2), (.8, -1.5), (.0, -1.4)], col(.5, .2, .9, .5), 0, 9, smooth=False)
    for side in (-1, 1):
        blob(p, (.62, side * .2, 1.0), .08, GLOW_ROSE, 1, 1, 0, side)
    for k in range(10):
        a = k / 10 * 2 * math.pi
        top = np.array([math.cos(a) * .9, math.sin(a) * .9, -1.2])
        line = top + np.stack([np.zeros(8), np.zeros(8), -np.linspace(0, rng.uniform(1.5, 3), 8)], 1) + rng.normal(0, .1, (8, 3))
        ribbon(p, line, np.linspace(.12, .01, 8), col(.7, .3, 1., .8), 0, normal=(math.cos(a), math.sin(a), 0))
    for side in (-1, 1):
        prism(p, (.2, side * .8, .4), (1.4, side * 1.6, -.4), .12, col(1, .3, .6, .7), 0, 4, .6)
    return p


def sentinel():
    """Level 5, end-game: the Hollow Sentinel, a First One war-construct the Center never woke from."""
    rng = np.random.default_rng(320)
    p = Part('SM_CE_Sentinel', (GLASS, GLOW, SOLID))
    prism(p, (0, 0, -2), (0, 0, 3.5), 1.4, FIRST_WHITE, 2, 6, .4)
    torus(p, (0, 0, .8), 2.4, .22, col(1, .5, .1, 1), 1, 40, 6, axis='z')
    torus(p, (0, 0, .8), 3.2, .12, FIRST_GOLD, 2, 40, 5)
    blob(p, (1.2, 0, 1.6), .45, col(1, .35, .05, 1), 1, 2, .05, 1)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        prism(p, (math.cos(a) * 1.6, math.sin(a) * 1.6, .8), (math.cos(a) * 4.2, math.sin(a) * 4.2, .8 + rng.uniform(-1.5, 1.5)), .3, col(.9, .5, .2, .5), 0, 6, .5)
    for side in (-1, 1):
        prism(p, (0, side * 1.4, 2.8), (0, side * 2.6, 5.5), .5, FIRST_WHITE, 2, 4, .6)
    return p


def warden():
    """Level 4: Temple Warden, a ring of blades that guards the sanctum approach."""
    p = Part('SM_CE_Warden', (GLASS, GLOW, SOLID))
    for r, tone in ((1.6, col(.3, .9, 1, .6)), (2.4, col(.9, .7, .3, .4))):
        torus(p, (0, 0, 0), r, .1, tone, 0, 36, 5)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        c = np.array([0, math.cos(a) * 2.4, math.sin(a) * 2.4])
        prism(p, c, c * 1.55, .18, col(.4, .9, 1., .6), 0, 4, .6)
    blob(p, (0, 0, 0), .55, col(.3, 1., .9, 1), 1, 2, .05, 3)
    return p


# ---------------------------------------------------------------- terrain

TERRAIN_SLOTS = ('M_CenterTerrain',)


def terrain():
    axis, gx, gy, h, path = grid()
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {'half': HALF, 'cell': CELL, 'n': len(axis), 'water': WATER, 'regions': REGIONS, 'paths': PATHS}
    (OUT / 'height.json').write_text(json.dumps(meta))
    (OUT / 'height.bin').write_bytes(h.astype('<f4').tobytes())
    # Slope for colour.
    dzx, dzy = np.gradient(h, CELL)
    slope = np.hypot(dzx, dzy)
    moss = .5 + .5 * fbm(gx, gy, 41, 4, 1 / 35.0)
    glowmoss = np.clip(fbm(gx, gy, 42, 4, 1 / 18.0) * 3 - .9, 0, 1)
    colour = np.zeros(h.shape + (4,))
    grass_c = np.array([.05, .13, .08])
    grass_b = np.array([.025, .05, .1])
    # Larger patches of violet heath and pale lichen break up the meadows.
    heath = np.clip(fbm(gx, gy, 43, 4, 1 / 70.0) * 2.5 - .6, 0, 1)[..., None]
    lichen = np.clip(fbm(gx, gy, 44, 4, 1 / 25.0) * 3 - 1.6, 0, 1)[..., None]
    mud = np.array([.05, .05, .055])
    rockc = np.array([.12, .12, .14])
    trail = np.array([.13, .12, .14])
    sand = np.array([.2, .18, .17])
    c = grass_c * moss[..., None] + grass_b * (1 - moss[..., None])
    c = c * (1 - heath) + np.array([.09, .05, .13]) * heath
    c = c * (1 - lichen * .6) + np.array([.2, .24, .22]) * lichen * .6
    # Highlands are glassy and cold; Thornveil is rose-tinted.
    for name, tint in (('Highlands', np.array([.07, .08, .12])), ('Thornveil', np.array([.07, .04, .07]))):
        cx, cy, r, _, b = REGIONS[name]
        w = np.clip(1 - (np.hypot(gx - cx, gy - cy) - r) / b, 0, 1)[..., None]
        c = c * (1 - w) + tint * w
    wet = np.clip(1 - (h - WATER) / 1.2, 0, 1)[..., None]
    c = c * (1 - wet) + mud * wet
    shore = np.clip(1 - np.abs(h - WATER - .3) / .5, 0, 1)[..., None] * .5
    c = c * (1 - shore) + sand * shore
    steep = np.clip((slope - .55) / .35, 0, 1)[..., None]
    c = c * (1 - steep) + rockc * steep
    tw = np.clip(1 - (path - 2.5) / 3, 0, 1)[..., None]
    c = c * (1 - tw) + trail * tw
    colour[..., :3] = c
    colour[..., 3] = glowmoss * (1 - steep[..., 0]) * (1 - tw[..., 0]) * .6 + tw[..., 0] * .08
    n = len(axis)
    per = (n - 1) // TILES
    for tx in range(TILES):
        for ty in range(TILES):
            p = Part('SM_Center_Terrain_%d_%d' % (tx, ty), TERRAIN_SLOTS)
            xs, ys = slice(tx * per, (tx + 1) * per + 1), slice(ty * per, (ty + 1) * per + 1)
            px, py, ph, pc = gx[xs, ys], gy[xs, ys], h[xs, ys], colour[xs, ys]
            m = per + 1
            verts = np.stack([px.ravel(), py.ravel(), ph.ravel()], 1)
            idx = np.arange(m * m).reshape(m, m)
            a, b, cc, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
            faces = np.stack([a, b, cc, d], 1).tolist()  # counter-clockwise seen from above: faces up
            p.add(verts, faces, pc.reshape(-1, 4), 0, True)
            # Skirt so tile seams never show sky.
            export(p.build())
    # Water: a single coarse plane at water level covering every basin.
    p = Part('SM_Center_Water', ('M_CenterWater',))
    m = 41
    ax = np.linspace(-HALF, HALF, m)
    wx, wy = np.meshgrid(ax, ax, indexing='ij')
    verts = np.stack([wx.ravel(), wy.ravel(), np.full(m * m, WATER)], 1)
    idx = np.arange(m * m).reshape(m, m)
    faces = np.stack([idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()], 1).tolist()
    p.add(verts, faces, col(1, 1, 1), 0, True)
    export(p.build())
    return axis, gx, gy, h, path, slope


# ---------------------------------------------------------------- scatter (instances for Unreal)

def scatter():
    axis, gx, gy, h, path = grid()
    dzx, dzy = np.gradient(h, CELL)
    slope = np.hypot(dzx, dzy)
    rng = np.random.default_rng(7)

    def sample(x, y):
        fx, fy = (x + HALF) / CELL, (y + HALF) / CELL
        i, j = np.clip(fx.astype(int), 0, len(axis) - 2), np.clip(fy.astype(int), 0, len(axis) - 2)
        u, v = fx - i, fy - j
        hh = h[i, j] * (1 - u) * (1 - v) + h[i + 1, j] * u * (1 - v) + h[i, j + 1] * (1 - u) * v + h[i + 1, j + 1] * u * v
        return hh, slope[i, j], path[i, j]

    def region_weight(name, x, y):
        cx, cy, r, _, b = REGIONS[name]
        return np.clip(1 - (np.hypot(x - cx, y - cy) - r) / b, 0, 1)

    keep_clear = [(REGIONS['Concourse'][0], REGIONS['Concourse'][1], 70), (-700, 0, 26), (760, 0, 175), (-150, 560, 40)]

    def place(mesh, count, rule, scale=(.8, 1.3), sink=.2, pitch=0., below_water=False, min_path=8):
        x = rng.uniform(-HALF * .93, HALF * .93, count * 4)
        y = rng.uniform(-HALF * .93, HALF * .93, count * 4)
        hh, sl, pd = sample(x, y)
        w = rule(x, y, hh, sl)
        ok = (rng.uniform(0, 1, len(x)) < w) & (pd > min_path)
        if not below_water:
            ok &= hh > WATER + .15
        for cx, cy, r in keep_clear:
            ok &= np.hypot(x - cx, y - cy) > r
        idx = np.nonzero(ok)[0][:count]
        rows = []
        for i in idx:
            s = rng.uniform(*scale)
            rows.append([round(float(x[i]) * 100, 1), round(float(y[i]) * 100, 1), round(float(hh[i] - sink * s) * 100, 1),
                         round(float(rng.uniform(-pitch, pitch)), 1), round(float(rng.uniform(0, 360)), 1), round(float(rng.uniform(-pitch, pitch)), 1), round(float(s), 3)])
        return mesh, rows

    lowland = lambda x, y, hh, sl: (sl < .5) * (hh < 70)
    rules = [
        place('SM_CT_GlowTree0', 380, lambda x, y, hh, sl: lowland(x, y, hh, sl) * (.35 + .65 * region_weight('Glade', x, y) + .5 * region_weight('Marsh', x, y)), (.8, 1.4), .5),
        place('SM_CT_GlowTree1', 300, lambda x, y, hh, sl: lowland(x, y, hh, sl) * (.3 + .6 * region_weight('Concourse', x, y) + .6 * region_weight('Choir', x, y)), (.8, 1.3), .5),
        place('SM_CT_GlowTree2', 260, lambda x, y, hh, sl: lowland(x, y, hh, sl) * (.15 + .9 * region_weight('Thornveil', x, y)), (.8, 1.3), .5),
        place('SM_CT_Willow', 160, lambda x, y, hh, sl: (sl < .4) * (hh < WATER + 2.5) * (.2 + region_weight('Marsh', x, y)), (.8, 1.3), .4),
        place('SM_CT_Mushroom0', 70, lambda x, y, hh, sl: lowland(x, y, hh, sl) * (region_weight('Marsh', x, y) + region_weight('Choir', x, y) + .1), (.7, 1.4), .2),
        place('SM_CT_Mushroom1', 260, lambda x, y, hh, sl: lowland(x, y, hh, sl) * (.3 + region_weight('Marsh', x, y)), (.6, 1.5), .1),
        place('SM_CT_Reeds', 6000, lambda x, y, hh, sl: (np.abs(hh - WATER) < .9) * 1.0, (.7, 1.4), .3, below_water=True, min_path=4),
        place('SM_CT_Lily', 900, lambda x, y, hh, sl: (hh < WATER - .25) * (hh > WATER - 1.6) * 1.0, (.7, 1.4), 0, below_water=True, min_path=3),
        place('SM_CT_Fern', 9000, lambda x, y, hh, sl: lowland(x, y, hh, sl) * .8, (.7, 1.5), .1, 6, min_path=4),
        place('SM_CT_Grass', 48000, lambda x, y, hh, sl: (sl < .6) * (hh < 90) * 1.0, (.8, 1.6), .05, 8, min_path=3),
        place('SM_CT_Flowers', 12000, lambda x, y, hh, sl: lowland(x, y, hh, sl) * (.5 + region_weight('Glade', x, y) * 2 + region_weight('Choir', x, y)), (.7, 1.4), 0, 8, min_path=3),
        place('SM_CT_Crystal0', 900, lambda x, y, hh, sl: (.15 + region_weight('Highlands', x, y) + .5 * region_weight('Thornveil', x, y)) * (sl < .9), (.6, 1.6), .2, 25),
        place('SM_CT_Crystal1', 260, lambda x, y, hh, sl: (.05 + region_weight('Highlands', x, y) + .3 * region_weight('Choir', x, y)) * (sl < .9), (.6, 1.4), .4, 20),
        place('SM_CT_Crystal2', 70, lambda x, y, hh, sl: (region_weight('Highlands', x, y) + .02) * (sl < .7), (.7, 1.3), .8, 12, min_path=20),
        place('SM_CT_Rock0', 1400, lambda x, y, hh, sl: .4 + sl, (.6, 1.8), .4, 30),
        place('SM_CT_Rock1', 420, lambda x, y, hh, sl: .2 + sl * 1.5, (.6, 1.5), .9, 30),
        place('SM_CT_Rock2', 170, lambda x, y, hh, sl: (sl > .4) * 1.0 + (np.maximum(np.abs(x), np.abs(y)) > 780) * .5, (.7, 1.6), 2.5, 25, min_path=16),
        place('SM_CT_RootArch', 40, lambda x, y, hh, sl: lowland(x, y, hh, sl) * (region_weight('Marsh', x, y) + region_weight('Glade', x, y) + .2), (.7, 1.2), .5, min_path=6),
        place('SM_CA_Monolith', 26, lambda x, y, hh, sl: (sl < .5) * (.1 + region_weight('Highlands', x, y) + region_weight('Thornveil', x, y)), (.6, 1.1), .5, 4, min_path=12),
        place('SM_CA_Spire', 7, lambda x, y, hh, sl: (sl < .4) * (region_weight('Highlands', x, y) + .02), (.8, 1.2), 1.0, 0, min_path=30),
        place('SM_CA_HumanPillar', 60, lambda x, y, hh, sl: (sl < .4) * (region_weight('Concourse', x, y) * 2 + .05), (.8, 1.2), .2, 3, min_path=5),
        place('SM_CA_HumanWall', 22, lambda x, y, hh, sl: (sl < .35) * (region_weight('Concourse', x, y) * 2 + .02), (.8, 1.1), .3, 2, min_path=10),
        place('SM_CA_Lamp', 70, lambda x, y, hh, sl: (sl < .3) * 1.0, (.9, 1.1), 0, 0, min_path=4.5),
    ]
    # Lamps line the trails: replace the random lamp pass with trailside posts.
    posts = []
    for line in PATHS:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            length = math.hypot(bx - ax, by - ay)
            for k in range(int(length / 45)):
                t = (k + .5) / int(length / 45 + 1)
                x, y = ax + (bx - ax) * t, ay + (by - ay) * t
                nx, ny = -(by - ay) / length, (bx - ax) / length
                x, y = x + nx * 7, y + ny * 7
                hh, sl, _ = sample(np.array([x]), np.array([y]))
                yaw = math.degrees(math.atan2(-ny, -nx))
                posts.append([round(x * 100, 1), round(y * 100, 1), round(float(hh[0]) * 100, 1), 0, round(yaw, 1), 0, 1.0])
    rules = [r for r in rules if r[0] != 'SM_CA_Lamp'] + [('SM_CA_Lamp', posts)]
    data = {name: rows for name, rows in rules}
    (OUT / 'scatter.json').write_text(json.dumps(data))
    print('scatter', {k: len(v) for k, v in data.items()}, flush=True)


MESHES = (tree_glow, willow, mushroom, reeds, lily, fern, grass, flowers, crystal_cluster, rock, roots, root_bridge, still_tree,
          human_arch, human_pillar, human_wall, human_stairs, human_dish, lamp, first_ring, first_monolith, first_spire, first_platform,
          light_arch, lantern, shrine, stillstone, artifact, barrier, temple_base, temple_colonnade, temple_dome, temple_gate, temple_sanctum,
          moth, jelly, stag, fox, sky_whale, shardling, wraith, sentinel, warden,
          gate_light, gate_dissonance, gate_memory, node_resonance, anchor_reweave, echo_trace,
          aug_health, aug_katana, aug_pistol, aug_defense, aug_agility)
VARIANTS = {tree_glow: 3, mushroom: 2, crystal_cluster: 3, rock: 3}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    words = [a for a in argv if not a.startswith('--')]
    OUT.mkdir(parents=True, exist_ok=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    if '--scatter' in argv:
        scatter()
        return
    if '--terrain' in argv:
        terrain()
        scatter()
        return
    for build in MESHES:
        for variant in range(VARIANTS.get(build, 1)):
            part = build(variant) if build in VARIANTS else build()
            if words and not any(w.lower() in part.name.lower() for w in words):
                continue
            export(part.build())
            print('mesh', part.name, len(part.v), 'verts', len(part.f), 'faces', flush=True)
    if not words:
        terrain()
        scatter()


main()
