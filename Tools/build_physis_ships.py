"""Hero capital ships and Meridian Station's exterior for the Physis opening.

Run:  flatpak run org.blender.Blender -b --python Tools/build_physis_ships.py -- [assets] [--size N] [--clay] [--no-export]
      assets: cruiser frigate vigil shard station (default all)

Everything is procedural. Pipeline for each asset:
  1. Parts are authored with lofts, lathes and bevels (no booleans), mirrored where a warship is
     mirrored, and joined into one mesh with weighted normals.
  2. UV0 is a unique atlas at a uniform cm-per-texel; UVDetail (UV1) is a world-scale projection
     that the tiling detail sets use in Unreal.
  3. Cycles bakes position, normal, part data, occlusion and edge masks into UV0; numpy composes
     the PBR maps from those, and the normal map is derived from the composed height.
  4. FBX goes to Art/Meshes, textures to Art/Textures/Ships, review renders to Art/Review.
Noses point along +X, Z is up. The FBX call matches Tools/build_physis_cinematic.py.
"""
import colorsys
import math
import struct
import sys
import time
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / 'Art/Meshes'
TEXTURES = ROOT / 'Art/Textures/Ships'
REVIEW = ROOT / 'Art/Review'
HUMAN_SLOTS = ('M_Hull', 'M_Trim', 'M_Lights', 'M_Drive')
FIRST_SLOTS = ('M_Crystal', 'M_CrystalGlow')
HULL, TRIM, LIGHT, DRIVE = 0, 1, 2, 3
CRYSTAL, GLOW = 0, 1
# Paint zones on hull and trim.
PRIMARY, SECONDARY, METAL, ACCENT, DARK, SCORCH, HAZARD = 0, 1, 2, 3, 4, 5, 6
# Colour zones on the lights slot.
WARM, AMBER, COOL, RED, GREEN, BRIGHT, DIM, GLASS = 10, 11, 12, 13, 14, 15, 16, 17


# ------------------------------------------------------------------ parts

class Part:
    __slots__ = ('V', 'F', 'S', 'Z')

    def __init__(self, V, F, S, Z):
        self.V, self.F, self.S, self.Z = np.asarray(V, float).reshape(-1, 3), F, np.asarray(S, int), np.asarray(Z, int)


def from_bm(bm, slot, zone, keep=False):
    bm.verts.index_update()
    V = [v.co[:] for v in bm.verts]
    F = [tuple(v.index for v in f.verts) for f in bm.faces]
    S = [f.material_index for f in bm.faces] if keep else [slot] * len(F)
    part = Part(V, F, S, [zone] * len(F))
    bm.free()
    return part


def merge(*parts):
    V, F, S, Z, offset = [], [], [], [], 0
    for part in parts:
        V.append(part.V)
        F += [tuple(i + offset for i in face) for face in part.F]
        S.append(part.S)
        Z.append(part.Z)
        offset += len(part.V)
    return Part(np.vstack(V), F, np.concatenate(S), np.concatenate(Z))


def mat(location=(0, 0, 0), rotation=(0, 0, 0), scale=1.0):
    scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    return Matrix.LocRotScale(Vector(location), __import__('mathutils').Euler(rotation), Vector(scale))


def moved(part, matrix):
    m = np.array(matrix)
    V = part.V @ m[:3, :3].T + m[:3, 3]
    F = part.F if np.linalg.det(m[:3, :3]) > 0 else [face[::-1] for face in part.F]
    return Part(V, F, part.S, part.Z)


def bevel_edges(bm, width, segments=2, angle=28, edges=None):
    if width <= 0:
        return []
    if edges is None:
        limit = math.radians(angle)
        edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > limit]
    if not edges:
        return []
    verts = list({v for e in edges for v in e.verts})
    out = bmesh.ops.bevel(bm, geom=verts + edges, offset=width, offset_type='OFFSET', segments=segments, profile=.5, affect='EDGES', clamp_overlap=True)
    return out['faces']


def loft(sections, slot=HULL, zone=PRIMARY, bevel=0, segments=2, angle=28, cap=True, closed=True, flip=False, weld=False, recalc=False):
    sections = [np.asarray(s, float) for s in sections]
    bm = bmesh.new()
    rows = [[bm.verts.new(p) for p in s] for s in sections]
    n = len(rows[0])
    for a, b in zip(rows, rows[1:]):
        for j in range(n if closed else n - 1):
            k = (j + 1) % n
            quad = (a[j], a[k], b[k], b[j])
            try:
                bm.faces.new(quad[::-1] if flip else quad)
            except ValueError:
                pass
    if cap:
        bm.faces.new(rows[0][::-1])
        bm.faces.new(rows[-1])
    if weld:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=.02)
        bmesh.ops.dissolve_degenerate(bm, dist=.02, edges=bm.edges[:])
    if cap or recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bevel_edges(bm, bevel, segments, angle)
    return from_bm(bm, slot, zone)


def ring(radius, x=0.0, n=32, axis='X', phase=0.0):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False) + phase
    c, s = np.cos(t) * radius, np.sin(t) * radius
    h = np.full(n, float(x))
    return np.stack((h, c, s), 1) if axis == 'X' else np.stack((c, s, h), 1)


def lathe(profile, n=32, axis='X', slot=TRIM, zone=METAL, bevel=0, cap=True, flip=False, phase=0.0):
    # Revolve (height, radius) points. Sharp profile corners read as machined steps.
    return loft([ring(r, h, n, axis, phase) for h, r in profile], slot, zone, bevel, 1, 30, cap, True, flip, False)


def rect(hw, z0, z1, c=0.0, x=0.0, y=0.0):
    # Chamfered rectangle in the YZ plane.
    s = [(hw - c, z0), (hw, z0 + c), (hw, z1 - c), (hw - c, z1), (-hw + c, z1), (-hw, z1 - c), (-hw, z0 + c), (-hw + c, z0)]
    return np.array([(x, y + a, b) for a, b in s])


def beam(start, end, hw, hh=None, slot=TRIM, zone=SECONDARY, bevel=0.0, up=(0, 0, 1), c=None):
    # Chamfered square bar between two points.
    start, end = Vector(start), Vector(end)
    d = (end - start).normalized()
    u = Vector(up)
    side = d.cross(u)
    if side.length < 1e-3:
        side = d.cross(Vector((0, 1, 0)))
    side.normalize()
    u = side.cross(d).normalized()
    hh = hw if hh is None else hh
    c = min(hw, hh) * .3 if c is None else c
    pts = [(hw - c, -hh), (hw, -hh + c), (hw, hh - c), (hw - c, hh), (-hw + c, hh), (-hw, hh - c), (-hw, -hh + c), (-hw + c, -hh)]
    sec = [[tuple(p + side * a + u * b) for a, b in pts] for p in (start, end)]
    return loft(sec, slot, zone, bevel, 1)


def slab(outline, thickness, slot=HULL, zone=PRIMARY, bevel=0.0, segments=1):
    # Extrude a 2D outline in XY along +Z.
    bottom = [(x, y, 0) for x, y in outline]
    top = [(x, y, thickness) for x, y in outline]
    return loft([bottom, top], slot, zone, bevel, segments)


def box(size, center, slot=TRIM, zone=SECONDARY, bevel=0.0, c=0.0):
    x, y, z = size
    cx, cy, cz = center
    sec = lambda at: rect(y / 2, cz - z / 2, cz + z / 2, c or min(y, z) * .08, at, cy)
    return loft([sec(cx - x / 2), sec(cx + x / 2)], slot, zone, bevel, 1)


class Kit:
    """Collects parts into one mesh with per-face slot, paint zone, tone, windows and UV scale."""

    def __init__(self, name, slots, seed):
        self.name, self.slots = name, slots
        self.rng = np.random.default_rng(seed)
        self.V, self.F, self.S, self.Z, self.T, self.W, self.U, self.C, self.I = [], [], [], [], [], [], [], [], []
        self.count, self.parts = 0, 0

    def add(self, part, matrix=None, tone=None, win=0.0, uv=1.0, mode=0, slot=None):
        part = moved(part, matrix) if matrix is not None else part
        n = len(part.F)
        offset = self.count
        self.V.append(part.V)
        self.F += [tuple(i + offset for i in face) for face in part.F]
        self.S.append(part.S if slot is None else np.full(n, slot))
        self.Z.append(part.Z)
        self.T.append(np.full(n, self.rng.uniform(0, 1) if tone is None else tone, np.float32))
        self.W.append(np.full(n, win, np.float32))
        self.U.append(np.full(n, uv, np.float32))
        self.C.append(np.full(n, mode, np.int32))
        self.I.append(np.full(n, self.parts, np.int32))
        self.count += len(part.V)
        self.parts += 1

    def sym(self, part, matrix=None, **options):
        # Mirror across XZ. Both sides share one tone so panels match port to starboard.
        options.setdefault('tone', float(self.rng.uniform(0, 1)))
        self.add(part, matrix, **options)
        base = mat(scale=(1, -1, 1)) @ (matrix if matrix is not None else Matrix.Identity(4))
        self.add(part, base, **options)

    def build(self, sharp=50, longest=0.0):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(np.vstack(self.V).tolist(), [], self.F)
        mesh.update()
        for key in self.slots:
            mesh.materials.append(bpy.data.materials.get(key) or bpy.data.materials.new(key))
        mesh.polygons.foreach_set('material_index', np.concatenate(self.S).astype(np.int32))
        for name, data in (('a_tone', self.T), ('a_win', self.W)):
            mesh.attributes.new(name, 'FLOAT', 'FACE').data.foreach_set('value', np.concatenate(data))
        zones = np.concatenate(self.Z).astype(np.float32)
        if self.slots is FIRST_SLOTS:
            zones[np.concatenate(self.S) == GLOW] = 30
            zones[np.concatenate(self.Z) == 1] = 31  # filaments fade away from the core
        mesh.attributes.new('a_zone', 'FLOAT', 'FACE').data.foreach_set('value', zones)
        self.scale = np.concatenate(self.U)
        self.mode = np.concatenate(self.C)
        self.ids = np.concatenate(self.I)
        self.face_slot = np.concatenate(self.S)
        self.face_zone = np.concatenate(self.Z)
        if longest:
            # Very long faces would force the whole atlas down to their scale. Split them.
            mesh.attributes.new('a_orig', 'INT', 'FACE').data.foreach_set('value', np.arange(len(mesh.polygons), dtype=np.int32))
            bm = bmesh.new()
            bm.from_mesh(mesh)
            for _ in range(4):
                edges = [e for e in bm.edges if e.calc_length() > longest]
                if not edges:
                    break
                bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
            bm.to_mesh(mesh)
            bm.free()
            orig = np.empty(len(mesh.polygons), np.int32)
            mesh.attributes['a_orig'].data.foreach_get('value', orig)
            self.scale, self.mode, self.ids = self.scale[orig], self.mode[orig], self.ids[orig]
            self.face_slot, self.face_zone = self.face_slot[orig], self.face_zone[orig]
            mesh.attributes.remove(mesh.attributes['a_orig'])
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        mesh.shade_smooth()
        mesh.set_sharp_from_angle(angle=math.radians(sharp))
        modifier = obj.modifiers.new('WN', 'WEIGHTED_NORMAL')
        modifier.keep_sharp = True
        modifier.mode = 'FACE_AREA'
        modifier.weight = 100
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        return obj


# ------------------------------------------------------------------ UVs

def unwrap(obj, kit, size, chart_limit=2600.0):
    """UV0: unique shelf-packed atlas. UVDetail: world-scale projection in centimetres."""
    mesh = obj.data
    nv, nf, nl = len(mesh.vertices), len(mesh.polygons), len(mesh.loops)
    co = np.empty(nv * 3)
    mesh.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    start = np.empty(nf, int)
    total = np.empty(nf, int)
    mesh.polygons.foreach_get('loop_start', start)
    mesh.polygons.foreach_get('loop_total', total)
    normal = np.empty(nf * 3)
    mesh.polygon_normals.foreach_get('vector', normal)
    normal = normal.reshape(-1, 3)
    lv = np.empty(nl, int)
    le = np.empty(nl, int)
    mesh.loops.foreach_get('vertex_index', lv)
    mesh.loops.foreach_get('edge_index', le)
    poly = np.repeat(np.arange(nf), total)
    axis = np.abs(normal).argmax(1)
    sign = (normal[np.arange(nf), axis] > 0).astype(int)
    P = co[lv]
    uv = np.zeros((nl, 2))
    a = axis[poly]
    uv[a == 0] = P[a == 0][:, (1, 2)]
    uv[a == 1] = P[a == 1][:, (0, 2)]
    uv[a == 2] = P[a == 2][:, (0, 1)]
    # Cylindrical faces (the station shell) unroll so panels follow the hull.
    cyl = (kit.mode > 0)
    sector = np.zeros(nf, int)
    if cyl.any():
        c = cyl[poly]
        theta = np.arctan2(P[c, 2], P[c, 1])
        # Keep every corner of a polygon on the same side of the +/-pi seam.
        centre = np.zeros(nf)
        np.add.at(centre, poly, 0)
        cy = np.zeros(nf)
        cz = np.zeros(nf)
        np.add.at(cy, poly, P[:, 1])
        np.add.at(cz, poly, P[:, 2])
        mid = np.arctan2(cz, cy)
        theta = mid[poly[c]] + (theta - mid[poly[c]] + math.pi) % (2 * math.pi) - math.pi
        uv[c, 0] = P[c, 0]
        uv[c, 1] = theta * kit.mode[poly[c]]
        # Steep cones and flanges barely change in x, so x alone smears the texture into radial streaks.
        # Those faces unroll by slant length instead.
        steep = np.abs(normal[poly[c], 0]) > .3
        radius = np.hypot(P[c, 1], P[c, 2])
        along = uv[c, 0]
        # One constant scale: a per-slope one jumps between neighbouring faces and makes vast charts.
        along[steep] = radius[steep] / .6
        uv[c, 0] = along
        steep_face = np.zeros(nf, bool)
        steep_face[poly[c][steep]] = True
        sector[cyl] = np.floor((mid[cyl] + math.pi) / (2 * math.pi) * 20).astype(int) + steep_face[cyl] * 20
    if kit.slots is FIRST_SLOTS:
        # Seams go to a shared swatch, so a chart must never hold seam and crystal faces together.
        sector = kit.face_slot.astype(int).copy()
    detail = uv.copy()
    # Charts: connected faces of one part facing one way, capped in size.
    cu = np.zeros(nf)
    cv = np.zeros(nf)
    np.add.at(cu, poly, uv[:, 0])
    np.add.at(cv, poly, uv[:, 1])
    cu /= total
    cv /= total
    grid = (np.floor(cu / chart_limit).astype(np.int64) & 1023) * 1024 + (np.floor(cv / chart_limit).astype(np.int64) & 1023)
    key = kit.ids.astype(np.int64) * 8 * 41 * 1048576 + (axis * 2 + sign + sector * 8) * 1048576 + grid
    # Union faces across shared edges with matching keys.
    order = np.argsort(le, kind='stable')
    e_sorted = le[order]
    p_sorted = poly[order]
    same = np.flatnonzero((e_sorted[1:] == e_sorted[:-1]) & (key[p_sorted[1:]] == key[p_sorted[:-1]]))
    parent = list(range(nf))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in same.tolist():
        a_, b_ = find(int(p_sorted[i])), find(int(p_sorted[i + 1]))
        if a_ != b_:
            parent[a_] = b_
    roots = np.array([find(i) for i in range(nf)])
    _, chart = np.unique(roots, return_inverse=True)
    count = chart.max() + 1
    uv = uv * kit.scale[poly][:, None]
    corner = chart[poly]
    lo = np.full((count, 2), 1e18)
    hi = np.full((count, 2), -1e18)
    np.minimum.at(lo, corner, uv)
    np.maximum.at(hi, corner, uv)
    dims = hi - lo
    # Lay long charts flat, then fit by bisection on scale.
    swap = dims[:, 1] > dims[:, 0]
    w = np.where(swap, dims[:, 1], dims[:, 0])
    h = np.where(swap, dims[:, 0], dims[:, 1])
    # Flat-colour lights and parts smaller than a few texels share one chart per paint zone.
    # They carry no information worth a texel of their own, and padding would otherwise eat the atlas.
    first = np.zeros(count, int)
    first[chart] = np.arange(nf)
    group = kit.face_zone[first] * 8 + kit.face_slot[first]
    guess = math.sqrt(float((dims[:, 0] * dims[:, 1]).sum()) / (size * size * .5))
    tiny = dims.max(1) < guess * 4
    # Lights and crystal seams are often thinner than a texel, and such a strip bakes as broken dashes.
    tiny |= kit.face_slot[first] == (LIGHT if kit.slots is HUMAN_SLOTS else GLOW)
    home = np.arange(count)
    for value in np.unique(group[tiny]):
        members = np.flatnonzero(tiny & (group == value))
        best = members[np.argmax(dims[members].max(1))]
        home[members] = best
        tiny[best] = False
    # Every shared zone owns a swatch of real texels, however small the host chart is.
    hosts = np.unique(home[home != np.arange(count)])
    w[hosts] = np.maximum(w[hosts], guess * 8)
    h[hosts] = np.maximum(h[hosts], guess * 8)
    live = np.flatnonzero(~tiny)
    order = live[np.argsort(-h[live], kind='stable')]
    pad = 4 / size
    W, H = w[order], h[order]

    def pack(scale):
        x, y, row = pad, pad, 0.0
        px = np.empty(len(W))
        py = np.empty(len(W))
        for i, (cw, ch) in enumerate(zip((W * scale).tolist(), (H * scale).tolist())):
            if cw + pad * 2 > 1:
                return None
            if x + cw + pad > 1:
                x, y = pad, y + row + pad
                row = 0.0
            if row == 0.0:
                row = ch
            px[i], py[i] = x, y
            x += cw + pad
        return (px, py) if y + row + pad <= 1 else None

    low, high = 0.0, 1 / max(W.max(), 1)
    best = None
    for _ in range(16):
        mid = (low + high) / 2
        result = pack(mid)
        if result is None:
            high = mid
        else:
            low, best = mid, result
    px, py = best
    x = np.zeros(count)
    y = np.zeros(count)
    x[order], y[order] = px, py
    local = (uv - lo[corner]) * low
    flip = swap[corner]
    packed = np.empty_like(local)
    packed[~flip, 0] = local[~flip, 0]
    packed[~flip, 1] = local[~flip, 1]
    packed[flip, 0] = local[flip, 1]
    packed[flip, 1] = dims[corner[flip], 0] * low - local[flip, 0]
    packed[:, 0] += x[corner]
    packed[:, 1] += y[corner]
    # Sharers fit inside their host's bounds.
    shared = tiny[corner]
    if shared.any():
        host = home[corner[shared]]
        span = np.minimum(w[host], h[host]) * low
        # Per-axis, so slivers still cover texel centres and cannot fall between them.
        reach = np.maximum(dims[corner[shared]], 1e-3)
        fit = (uv[shared] - lo[corner[shared]]) / reach
        # Sharers fill the middle of the swatch, where they bake one flat zone colour. Overlaps are harmless
        # because every chart here shares the zone, and their UVs stay large enough for valid tangents.
        packed[shared, 0] = x[host] + (.25 + fit[:, 0] * .5) * span
        packed[shared, 1] = y[host] + (.25 + fit[:, 1] * .5) * span
    layer = mesh.uv_layers.new(name='UV0')
    layer.data.foreach_set('uv', packed.astype(np.float32).ravel())
    second = mesh.uv_layers.new(name='UVDetail')
    second.data.foreach_set('uv', (detail / 1000).astype(np.float32).ravel())
    mesh.uv_layers.active_index = 0
    cm_per_texel = 1 / (low * size)
    used = (W * H).sum() * low * low
    count = len(live)
    print(f'[uv] {kit.name}: {count} charts, {cm_per_texel:.2f} cm/texel at {size}, {used:.0%} of atlas in chart bounds')
    return cm_per_texel


# ------------------------------------------------------------------ baking

def cycles_scene():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.max_bounces = 4
    if scene.world is None:
        scene.world = bpy.data.worlds.new('World')
    return scene


def bake(obj, size, build=None, kind='EMIT', samples=1):
    scene = cycles_scene()
    scene.cycles.samples = samples
    image = bpy.data.images.new('bake', size, size, alpha=True, float_buffer=True)
    image.colorspace_settings.name = 'Non-Color'
    material = bpy.data.materials.new('bake')
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    target = nodes.new('ShaderNodeTexImage')
    target.image = image
    out = nodes.new('ShaderNodeOutputMaterial')
    if build:
        emit = nodes.new('ShaderNodeEmission')
        links.new(emit.outputs[0], out.inputs[0])
        links.new(build(nodes, links), emit.inputs[0])
    else:
        diffuse = nodes.new('ShaderNodeBsdfDiffuse')
        links.new(diffuse.outputs[0], out.inputs[0])
    nodes.active = target
    target.select = True
    keep = list(obj.data.materials)
    for i in range(len(keep)):
        obj.data.materials[i] = material
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bake_settings = scene.render.bake
    bake_settings.margin = 8
    bake_settings.margin_type = 'EXTEND'
    bake_settings.use_clear = True
    bpy.ops.object.bake(type=kind, use_clear=True, margin=8, margin_type='EXTEND')
    data = np.empty(size * size * 4, np.float32)
    image.pixels.foreach_get(data)
    for i, slot in enumerate(keep):
        obj.data.materials[i] = slot
    bpy.data.images.remove(image)
    bpy.data.materials.remove(material)
    return data.reshape(size, size, 4)


def attr(nodes, name):
    node = nodes.new('ShaderNodeAttribute')
    node.attribute_type = 'GEOMETRY'
    node.attribute_name = name
    return node


def combine(nodes, links, a, b, c):
    node = nodes.new('ShaderNodeCombineXYZ')
    for i, s in enumerate((a, b, c)):
        if s is not None:
            links.new(s, node.inputs[i])
    return node.outputs[0]


def encode(nodes, links, vector, norm):
    scaled = nodes.new('ShaderNodeVectorMath')
    scaled.operation = 'MULTIPLY_ADD'
    links.new(vector, scaled.inputs[0])
    scaled.inputs[1].default_value = (.5 / norm,) * 3
    scaled.inputs[2].default_value = (.5,) * 3
    return scaled.outputs[0]


def bake_maps(obj, size, edge_radius, ao_distance, spp, norm=120000.0):
    started = time.time()
    maps = {}

    def position(nodes, links):
        return encode(nodes, links, nodes.new('ShaderNodeNewGeometry').outputs['Position'], norm)

    def normal(nodes, links):
        return encode(nodes, links, nodes.new('ShaderNodeNewGeometry').outputs['True Normal'], 1.0)

    def detail(nodes, links):
        node = nodes.new('ShaderNodeUVMap')
        node.uv_map = 'UVDetail'
        return encode(nodes, links, node.outputs[0], norm / 1000)

    def data(nodes, links):
        slot = nodes.new('ShaderNodeObjectInfo')  # placeholder keeps node order stable
        return combine(nodes, links, attr(nodes, 'a_tone').outputs['Fac'], attr(nodes, 'a_zone').outputs['Fac'], attr(nodes, 'a_win').outputs['Fac'])

    def edge(nodes, links):
        bevel = nodes.new('ShaderNodeBevel')
        bevel.samples = 6
        bevel.inputs['Radius'].default_value = edge_radius
        geometry = nodes.new('ShaderNodeNewGeometry')
        dot = nodes.new('ShaderNodeVectorMath')
        dot.operation = 'DOT_PRODUCT'
        links.new(bevel.outputs[0], dot.inputs[0])
        links.new(geometry.outputs['True Normal'], dot.inputs[1])
        return dot.outputs['Value']

    raw = bake(obj, size, position)
    maps['valid'] = raw[..., 3] > .5
    maps['P'] = (raw[..., :3] - .5) * 2 * norm
    maps['N'] = bake(obj, size, normal)[..., :3] * 2 - 1
    maps['D'] = (bake(obj, size, detail)[..., :2] - .5) * 2 * norm
    raw = bake(obj, size, data)
    maps['tone'], maps['zone'], maps['win'] = raw[..., 0], raw[..., 1], raw[..., 2]
    maps['edge'] = np.clip(1 - bake(obj, size, edge, samples=4)[..., 0], 0, 1)
    world = bpy.context.scene.world if bpy.context.scene.world else None
    cycles_scene().world.light_settings.distance = ao_distance
    maps['ao'] = bake(obj, size, None, 'AO', spp)[..., 0]
    print(f'[bake] {obj.name} {size}px in {time.time() - started:.0f}s')
    return maps


# ------------------------------------------------------------------ image helpers

def png(path, array, bits=8):
    """Write a bottom-up float array as RGB PNG. Used instead of Blender's writer to avoid colour transforms."""
    array = np.clip(array[::-1], 0, 1)
    array = array[..., None] if array.ndim == 2 else array
    h, w, c = array.shape
    if bits == 16:
        data = (array * 65535 + .5).astype('>u2')
    else:
        data = (array * 255 + .5).astype(np.uint8)
    raw = np.zeros((h, w * c * (bits // 8) + 1), np.uint8)
    body = data.tobytes()
    stride = w * c * (bits // 8)
    rows = np.frombuffer(body, np.uint8).reshape(h, stride)
    # Sub filter: compresses smooth 16-bit data far better than none.
    step = c * (bits // 8)
    filtered = rows.copy()
    filtered[:, step:] = rows[:, step:] - rows[:, :-step]
    raw[:, 0] = 1
    raw[:, 1:] = filtered

    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff)

    kind = {1: 0, 3: 2, 4: 6}[c]
    blob = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, bits, kind, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw.tobytes(), 6)) + chunk(b'IEND', b'')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)


def srgb(linear):
    linear = np.clip(linear, 0, 1)
    return np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)


def fft_noise(size, beta, seed, low=1.0, high=None):
    # Periodic fractal noise in [0, 1].
    rng = np.random.default_rng(seed)
    fx = np.fft.fftfreq(size)[:, None] * size
    fy = np.fft.rfftfreq(size)[None, :] * size
    r = np.sqrt(fx * fx + fy * fy)
    r[0, 0] = 1
    amp = r ** (-beta / 2)
    amp[r < low] = 0
    if high:
        amp[r > high] = 0
    spectrum = amp * np.exp(2j * math.pi * rng.random(amp.shape))
    out = np.fft.irfft2(spectrum, s=(size, size))
    lo, hi = np.percentile(out[::4, ::4], (.5, 99.5))
    return np.clip((out - lo) / (hi - lo), 0, 1).astype(np.float32)


def blur_wrap(a, sigma):
    h, w = a.shape
    fx = np.fft.fftfreq(h)[:, None]
    fy = np.fft.rfftfreq(w)[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (math.pi * sigma) ** 2 * (fx * fx + fy * fy)), s=a.shape).astype(np.float32)


def sample(tile, u, v):
    # Bilinear lookup with wrap; u and v in tile fractions.
    h, w = tile.shape[:2]
    x = (u % 1) * w
    y = (v % 1) * h
    x0 = x.astype(np.int32) % w
    y0 = y.astype(np.int32) % h
    fx = (x - np.floor(x)).astype(np.float32)
    fy = (y - np.floor(y)).astype(np.float32)
    x1, y1 = (x0 + 1) % w, (y0 + 1) % h
    if tile.ndim == 3:
        fx, fy = fx[..., None], fy[..., None]
    return (tile[y0, x0] * (1 - fx) + tile[y0, x1] * fx) * (1 - fy) + (tile[y1, x0] * (1 - fx) + tile[y1, x1] * fx) * fy


def smooth(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)


def normal_from_height(height, cm_per_texel):
    # Tangent axes follow UV0, so the height gradient in the atlas is the tangent-space slope.
    dv, du = np.gradient(height, cm_per_texel)
    n = np.dstack((-du, -dv, np.ones_like(height, dtype=np.float32)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    # DirectX: green points down.
    return np.dstack((n[..., 0] * .5 + .5, -n[..., 1] * .5 + .5, n[..., 2] * .5 + .5))


def text_mask(string, height_px, aspect=None, pad=.08):
    """Rasterise Blender's built-in font to a mask for stencilled hull markings."""
    curve = bpy.data.curves.new('t', 'FONT')
    curve.body = string
    item = bpy.data.objects.new('t', curve)
    bpy.context.collection.objects.link(item)
    mesh = item.to_mesh().copy()
    item.to_mesh_clear()
    bpy.data.objects.remove(item)
    bpy.data.curves.remove(curve)
    mesh.calc_loop_triangles()
    co = np.array([v.co[:2] for v in mesh.vertices])
    lo, hi = co.min(0), co.max(0)
    extent = (hi - lo).max()
    width = int(height_px * (hi - lo)[0] / (hi - lo)[1])
    scale = (height_px - 1) / (hi - lo)[1]
    p = (co - lo) * scale
    out = np.zeros((height_px, width + 2), np.float32)
    for tri in mesh.loop_triangles:
        a, b, c = p[list(tri.vertices)]
        x0, y0 = np.floor(np.min((a, b, c), 0)).astype(int)
        x1, y1 = np.ceil(np.max((a, b, c), 0)).astype(int) + 1
        y, x = np.mgrid[y0:y1, x0:x1]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        l0 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d
        l1 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d
        inside = (l0 >= -.01) & (l1 >= -.01) & (l0 + l1 <= 1.01)
        out[y0:y1, x0:x1][inside[:out.shape[0] - y0, :out.shape[1] - x0]] = 1
    bpy.data.meshes.remove(mesh)
    return out


# ------------------------------------------------------------------ human texture set

def panel_tile(px, seed, cm_per_px, min_panel=44):
    """Seamless armour panelling: height in cm, panel random, and machinery masks."""
    rng = np.random.default_rng(seed)
    value = np.zeros((px, px), np.float32)
    lift = np.zeros((px, px), np.float32)
    seam = np.zeros((px, px), np.float32)
    bolts = np.zeros((px, px), np.float32)
    inset = np.zeros((px, px), np.float32)
    grille = np.zeros((px, px), np.float32)
    stack = [(0, 0, px, px, 0)]
    while stack:
        x, y, w, h, depth = stack.pop()
        if depth < 7 and (depth < 3 or rng.random() < .7) and max(w, h) > min_panel * 1.6:
            if w > h * rng.uniform(.8, 1.3):
                cut = int(w * rng.choice((.25, .333, .5, .667, .75)))
                stack += [(x, y, cut, h, depth + 1), (x + cut, y, w - cut, h, depth + 1)]
            else:
                cut = int(h * rng.choice((.333, .5, .667)))
                stack += [(x, y, w, cut, depth + 1), (x, y + cut, w, h - cut, depth + 1)]
            continue
        value[y:y + h, x:x + w] = rng.random()
        lift[y:y + h, x:x + w] = rng.choice((-1.2, 0, 0, .8, 1.6))
        seam[y:y + 1, x:x + w] = 1
        seam[y:y + h, x:x + 1] = 1
        kind = rng.random()
        margin = max(4, int(min(w, h) * .12))
        if kind < .22 and w > 30 and h > 30:
            # Fastener row around the panel.
            pitch = max(5, int(14 / max(cm_per_px, .2) / 2))
            bolts[y + 3:y + h - 2, x + 3:x + 5:1][::pitch] = 1
            bolts[y + 3:y + h - 2, x + w - 5:x + w - 3:1][::pitch] = 1
            bolts[y + 3:y + 5, x + 3:x + w - 2][:, ::pitch] = 1
            bolts[y + h - 5:y + h - 3, x + 3:x + w - 2][:, ::pitch] = 1
        elif kind < .34 and w > 40 and h > 40:
            # Access hatch: an inset rectangle.
            hx, hy = x + margin, y + margin
            hw, hh = max(8, int((w - 2 * margin) * rng.uniform(.4, .8))), max(8, int((h - 2 * margin) * rng.uniform(.4, .8)))
            inset[hy:hy + hh, hx:hx + hw] = 1
        elif kind < .42 and w > 50 and h > 26:
            # Louvred vent.
            band = (np.arange(h - 2 * margin) // 3) % 2 == 0
            grille[y + margin:y + h - margin, x + margin:x + w - margin] = band[:, None].astype(np.float32)
    wide = blur_wrap(seam, 1.0) * 2.2
    height = lift - np.clip(wide, 0, 1) * 2.6
    height += blur_wrap(inset, .8) * -1.6 - (blur_wrap(inset, .7) - blur_wrap(inset, 2.5)).clip(0, 1) * .8
    height += blur_wrap(grille, .6) * -1.8
    height += blur_wrap(bolts, .6) * 1.6
    # Panel faces are never quite flat: a soft pillow towards the seams.
    height -= blur_wrap(seam, 7) * 2.5
    return {'height': height, 'id': value, 'seam': np.clip(wide, 0, 1), 'inset': inset, 'grille': grille}


def detail_set(seed=71, px=2048):
    """Tiling micro-surface for close shots, used on UVDetail in Unreal at 1 tile per 4 m."""
    fine = fft_noise(px, 2.0, seed, 6)
    micro = fft_noise(px, 1.4, seed + 1, 40)
    scratches = np.zeros((px, px), np.float32)
    rng = np.random.default_rng(seed + 2)
    for _ in range(1400):
        x, y = rng.integers(0, px, 2)
        length = rng.integers(16, 240)
        slope = rng.uniform(-.25, .25)
        t = np.arange(length)
        scratches[(y + (t * slope).astype(int)) % px, (x + t) % px] = 1
    scratches = blur_wrap(scratches, .6) * 2
    grid = np.zeros((px, px), np.float32)
    grid[::px // 8, :] = 1
    grid[:, ::px // 8] = 1
    rivet = np.zeros((px, px), np.float32)
    rivet[px // 64::px // 32, px // 64::px // 32] = 1
    height = (fine - .5) * 1.2 + (micro - .5) * .35 - np.clip(scratches, 0, 1) * .5 - np.clip(blur_wrap(grid, 1.0) * 2, 0, 1) * 1.2 + np.clip(blur_wrap(rivet, 2.0) * 22, 0, 1) * 1.0
    normal = normal_from_height(height, .2)
    rough = .42 + (micro - .5) * .3 + np.clip(scratches, 0, 1) * -.15 + (fine - .5) * .25
    orm = np.dstack((np.clip(1 + (height - height.max()) * .03, 0, 1), np.clip(rough, 0, 1), np.zeros_like(rough)))
    png(TEXTURES / 'T_HullDetail_Normal.png', normal, 16)
    png(TEXTURES / 'T_HullDetail_ORM.png', orm)


ZONE_COLOURS = {PRIMARY: (.105, .11, .12), SECONDARY: (.03, .034, .04), METAL: (.20, .205, .215), ACCENT: (.012, .04, .1), DARK: (.012, .013, .015), SCORCH: (.05, .045, .042), HAZARD: (.33, .19, .03)}
LIGHT_COLOURS = {WARM: (1, .78, .48), AMBER: (1, .5, .12), COOL: (.62, .82, 1), RED: (1, .08, .05), GREEN: (.1, 1, .3), BRIGHT: (1, .93, .8), DIM: (.17, .135, .09), GLASS: (.05, .1, .15)}


def windows(D, kit_cfg, win, normal):
    """Lit windows on a deck grid: rows per deck, gaps at frames, compartments lit in groups."""
    col, row = kit_cfg['window_pitch']
    w, h = kit_cfg['window_size']
    u, v = D[..., 0] / col, D[..., 1] / row
    cu, cv = np.floor(u), np.floor(v)
    fu, fv = u - cu, v - cv
    frame = ((cu % 9) >= 7.5) | (cv % kit_cfg.get('row_skip', 3) != 0)
    cell = ((np.abs(fu - .5) < w / col / 2) & (np.abs(fv - .5) < h / row / 2) & ~frame)
    group = np.floor(cu / 9) * 73 + cv * 197
    lit_group = np.mod(np.sin(group * 12.9898) * 43758.5453, 1) > .42
    lit_one = np.mod(np.sin((cu * 311.7 + cv * 74.7)) * 24634.6345, 1) > .2
    warm = np.mod(np.sin(group * 7.13) * 9631.17, 1)
    mask = cell & (win > .5) & (np.abs(normal[..., 2]) < .6) if kit_cfg.get('side_only', True) else cell & (win > .5)
    lit = mask & lit_group & lit_one
    colour = np.where((warm > .22)[..., None], np.array((1, .76, .46), np.float32), np.array((.66, .84, 1), np.float32))
    glow = np.mod(np.sin((cu + cv * 13) * 3.7) * 513.3, 1) * .6 + .4
    return mask, lit[..., None] * colour * glow[..., None]


def slot_free(zone):
    return zone < WARM


def stencils(D, cfg, colour, mask):
    """Small service print on the plates: blocks of pale lines, so a plate has a scale up close."""
    cell = cfg['tile_cm'] / 6
    u, v = D[..., 0] / cell, D[..., 1] / cell
    cu, cv = np.floor(u), np.floor(v)
    fu, fv = u - cu, v - cv
    pick = np.mod(np.sin(cu * 127.1 + cv * 311.7) * 43758.5453, 1)
    long = np.mod(np.sin(cu * 269.5 + cv * 183.3) * 24634.6345, 1) * .14 + .06
    lines = (fv > .62) & (fv < .72) & (np.mod(fv * 60, 2) < 1.25)
    lines &= (fu > .12) & (fu < .12 + long) & (np.mod(fu * 120 + cv, 3) < 2.3)
    tick = (fu > .1) & (fu < .112) & (fv > .6) & (fv < .74)
    colour[mask & (pick > .72) & lines] = (.3, .29, .26)
    colour[mask & (pick > .72) & tick] = (.3, .17, .03)


def battle_damage(P, N, valid, cfg, noise):
    """Old shell hits: crater, torn paint and a wide scorch, all on the hit's own side of the hull."""
    h, w = valid.shape
    crater = np.zeros((h, w), np.float32)
    burn = np.zeros((h, w), np.float32)
    torn = np.zeros((h, w), np.float32)
    rng = np.random.default_rng(cfg['seed'] + 9)
    ys, xs = np.nonzero(valid[::8, ::8])
    if not len(ys):
        return crater, burn, torn
    low, high = cfg['impact']
    step = 4
    Ps, Ns, ns = P[::step, ::step], N[::step, ::step], noise[::step, ::step]
    for _ in range(cfg['impacts']):
        i = int(rng.integers(0, len(ys)))
        c, n = P[ys[i] * 8, xs[i] * 8].copy(), N[ys[i] * 8, xs[i] * 8].copy()
        r = float(low * (high / low) ** rng.random())
        reach = r * 4.5
        near = np.abs(Ps - c).max(2) < reach
        rows, cols = np.nonzero(near)
        if not len(rows):
            continue
        y0, y1 = rows.min() * step, min((rows.max() + 1) * step, h)
        x0, x1 = cols.min() * step, min((cols.max() + 1) * step, w)
        d = np.linalg.norm(P[y0:y1, x0:x1] - c, axis=2) / r * (.75 + noise[y0:y1, x0:x1] * .5)
        side = smooth(.15, .55, N[y0:y1, x0:x1] @ n) * valid[y0:y1, x0:x1]
        pit = 1 - smooth(.35, 1, d)
        rim = np.exp(-((d - 1.05) / .22) ** 2)
        crater[y0:y1, x0:x1] += ((rim * .1 - pit * .34) * r * .22 * side).astype(np.float32)
        burn[y0:y1, x0:x1] = np.maximum(burn[y0:y1, x0:x1], (np.exp(-(d / 2.1) ** 2) * side).astype(np.float32))
        torn[y0:y1, x0:x1] = np.maximum(torn[y0:y1, x0:x1], (smooth(1.45, 1.0, d) * smooth(.35, .55, d + noise[y0:y1, x0:x1] * .3) * side).astype(np.float32))
    return crater, burn, torn


def human_textures(obj, name, size, cm_per_texel, cfg):
    edge_radius = max(cm_per_texel * 1.6, 1.0)
    maps = bake_maps(obj, size, edge_radius, cfg['ao'], cfg['spp'])
    P, N, D = maps['P'], maps['N'], maps['D']
    zone = np.rint(maps['zone']).astype(np.int32)
    tone, ao, edge = maps['tone'], np.clip(maps['ao'], 0, 1), np.clip(maps['edge'] * 2.5, 0, 1)
    tile_cm = cfg['tile_cm']
    px = int(np.clip(tile_cm / (cm_per_texel * .6), 1024, 4096))
    tile = panel_tile(px, cfg['seed'], tile_cm / px)
    u, v = D[..., 0] / tile_cm, D[..., 1] / tile_cm
    height = sample(tile['height'], u, v) * cfg['height_scale'] * 1.5
    panel = sample(tile['id'], u, v)
    seam = sample(tile['seam'], u, v)
    grille = sample(tile['grille'], u, v)
    # Second, larger plate layout breaks the repetition of the tile.
    big = sample(tile['height'], u * .37 + .13, v * .37 + .41) * cfg['height_scale'] * 2.2
    height = np.where(sample(tile['id'], u * .11, v * .11) > .55, height, height * .55 + big * .45)
    size_noise = 1024
    cloud = fft_noise(size_noise, 2.4, cfg['seed'] + 1)
    speck = fft_noise(size_noise, 1.2, cfg['seed'] + 2, 30)
    streaks = fft_noise(size_noise, 1.8, cfg['seed'] + 3, 2)
    span = cfg['length']
    fade = sample(cloud, D[..., 0] / span * 2.1 + .3, D[..., 1] / span * 2.1 + .7)
    blotch = sample(cloud, D[..., 0] / span * 5, D[..., 1] / span * 5)
    chips = sample(speck, D[..., 0] / span * 26, D[..., 1] / span * 26)
    # Streaks run with the hull, thin across it: decades of drive wash and venting.
    wash = sample(streaks, D[..., 0] / span * .9, D[..., 1] / span * 9)
    colour = np.zeros((size, size, 3), np.float32)
    for key, value in ZONE_COLOURS.items():
        colour[zone == key] = value
    painted = (zone == PRIMARY) | (zone == SECONDARY) | (zone == ACCENT) | (zone == HAZARD)
    # Large plates differ slightly: replacements, repairs and repaint batches.
    variation = (np.round(panel * 5) / 5 - .5) * .55 + (tone - .5) * .6 + (fade - .5) * .3
    colour *= (1 + variation * painted)[..., None]
    # Disruptive fleet scheme: large angular blocks of warm and cold grey across the armour.
    scheme = sample(tile['id'], u * .19 + v * .07 + .31, v * .19 - u * .07 + .77)
    hull_paint = zone == PRIMARY
    colour[hull_paint & (scheme > .68)] *= np.array((1.5, 1.4, 1.22), np.float32)
    colour[hull_paint & (scheme < .3)] *= np.array((.6, .68, .84), np.float32)
    stencils(D, cfg, colour, hull_paint)
    hazard = (zone == HAZARD) & (np.mod((D[..., 0] + D[..., 1]) / cfg['hazard_pitch'], 1) < .5)
    colour[hazard] = (.02, .02, .022)
    # Hull numbers, stripes and ship-specific markings go here.
    if cfg.get('mark'):
        cfg['mark'](P, N, D, colour, zone)
    # Wear: paint chips to bare metal on exposed edges, with noise so it stays broken.
    wear = np.clip(edge * (chips * 1.6 + blotch * .7) - .56, 0, 1) * 3.4
    wear = np.clip(wear, 0, 1) * painted
    bare = np.array((.46, .46, .47), np.float32)
    colour = colour * (1 - wear[..., None]) + bare * wear[..., None]
    crater, burn, torn = battle_damage(P, N, maps['valid'] & (slot_free(zone)), cfg, chips)
    height += crater
    wear = np.maximum(wear, torn)
    colour = colour * (1 - torn[..., None]) + bare * .55 * torn[..., None]
    colour *= (1 - burn[..., None] * .93)
    grime = np.clip((1 - ao) * 1.3 * (.7 + blotch * .5) + seam * .62 + (1 - smooth(.25, .62, wash)) * .08, 0, 1)
    colour *= (1 - grime[..., None] * .8)
    soot = smooth(.35, .95, wash) * smooth(cfg['soot_x'] + span * .3, cfg['soot_x'], P[..., 0]) * .42
    colour *= (1 - soot[..., None])
    metal = np.isin(zone, (METAL, SCORCH)).astype(np.float32)
    metal = np.maximum(metal, wear)
    metal[maps['valid'] == 0] = 0
    # Speculars must break up, or painted steel reads as concrete.
    rough = np.where(painted, .4 + (panel - .5) * .2 + (blotch - .5) * .36, .3 + (blotch - .5) * .2) + (chips - .5) * .12 + grime * .24 - wear * .12 + soot * .1 + burn * .3
    rough = np.where(zone == SCORCH, .38, rough)
    colour[zone == SCORCH] *= 3.2
    metal[zone == SCORCH] = .55
    glow = np.zeros((size, size, 3), np.float32)
    mask, lit = windows(D, cfg, maps['win'], N)
    colour[mask] = (.012, .016, .022)
    rough[mask] = .1
    metal[mask] = 0
    height[mask] -= 1.6 * cfg['height_scale']
    glow += lit * 1.0
    slot_light = zone >= WARM
    for key, value in LIGHT_COLOURS.items():
        hit = zone == key
        colour[hit] = np.array(value) * .8
        glow[hit] = value
    if cfg.get('light'):
        cfg['light'](P, N, D, glow, colour, rough, metal, zone)
    # Drive plume surfaces: blue core with a hot rim. Zone 20 marks them.
    drive = zone == 20
    if drive.any():
        # Keep the throat's hue: at about 14 times emissive these values only just reach white.
        colour[drive] = (.16, .3, .6)
        glow[drive] = (.1, .24, .62)
    wall = zone == 21
    if wall.any():
        colour[wall] = (.05, .1, .22)
        glow[wall] = (.012, .04, .13)
    height *= 1 - slot_light
    ao_map = np.clip(ao * .9 + .1, 0, 1) * (1 - seam * .35) * (1 - grille * .3)
    orm = np.dstack((ao_map, np.clip(rough, .05, 1), np.clip(metal, 0, 1)))
    normal = normal_from_height(height, cm_per_texel)
    png(TEXTURES / f'T_{name}_BaseColor.png', srgb(colour))
    png(TEXTURES / f'T_{name}_Normal.png', normal, 16)
    png(TEXTURES / f'T_{name}_ORM.png', orm)
    png(TEXTURES / f'T_{name}_Emissive.png', srgb(glow))


# ------------------------------------------------------------------ preview

def preview_material(obj, name, emissive_power=14.0, clay=False):
    mesh = obj.data
    for i, slot in enumerate(mesh.materials):
        material = bpy.data.materials.new('Preview' + str(i))
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        bsdf = nodes['Principled BSDF']
        if clay:
            bsdf.inputs['Base Color'].default_value = (.42, .43, .45, 1)
            bsdf.inputs['Roughness'].default_value = .45
            if slot.name in ('M_Lights', 'M_Drive', 'M_CrystalGlow'):
                bsdf.inputs['Emission Color'].default_value = (1, .8, .5, 1)
                bsdf.inputs['Emission Strength'].default_value = 6
        else:
            def load(suffix, colour='Non-Color'):
                node = nodes.new('ShaderNodeTexImage')
                node.image = bpy.data.images.load(str(TEXTURES / f'T_{name}_{suffix}.png'), check_existing=True)
                node.image.colorspace_settings.name = colour
                return node
            links.new(load('BaseColor', 'sRGB').outputs[0], bsdf.inputs['Base Color'])
            orm = nodes.new('ShaderNodeSeparateColor')
            links.new(load('ORM').outputs[0], orm.inputs[0])
            links.new(orm.outputs[1], bsdf.inputs['Roughness'])
            links.new(orm.outputs[2], bsdf.inputs['Metallic'])
            normal = load('Normal')
            flip = nodes.new('ShaderNodeRGBCurve')
            flip.mapping.curves[1].points[0].location = (0, 1)
            flip.mapping.curves[1].points[1].location = (1, 0)
            flip.mapping.update()
            links.new(normal.outputs[0], flip.inputs[1])
            map_node = nodes.new('ShaderNodeNormalMap')
            map_node.uv_map = 'UV0'
            links.new(flip.outputs[0], map_node.inputs['Color'])
            links.new(map_node.outputs[0], bsdf.inputs['Normal'])
            links.new(load('Emissive', 'sRGB').outputs[0], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = emissive_power
        mesh.materials[i] = material


def render_views(obj, views, label, width=960, height=540, samples=48, floor=None):
    scene = cycles_scene()
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 3
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.006, .008, .014, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = 1
    corners = np.array([obj.matrix_world @ Vector(c) for c in obj.bound_box])
    centre = Vector(corners.mean(0))
    radius = float(np.linalg.norm(corners - corners.mean(0), axis=1).max())
    rig = []
    for direction, energy, colour, angle in (((-.5, -.75, .55), 4.2, (1, .94, .85), 1.5), ((.8, .45, .15), .6, (.55, .7, 1), 6), ((.75, -.2, -.65), 2.4, (.7, .85, 1), 1)):
        light = bpy.data.lights.new('sun', 'SUN')
        light.energy, light.color, light.angle = energy, colour, math.radians(angle)
        item = bpy.data.objects.new('sun', light)
        scene.collection.objects.link(item)
        item.rotation_euler = Vector(direction).to_track_quat('Z', 'Y').to_euler()
        rig.append(item)
    camera_data = bpy.data.cameras.new('cam')
    camera_data.clip_start, camera_data.clip_end = 10, radius * 400
    camera = bpy.data.objects.new('cam', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    frames = []
    for index, view in enumerate(views):
        direction = Vector(view['dir']).normalized()
        target = Vector(view.get('at', centre))
        camera_data.lens = view.get('lens', 70)
        distance = view.get('dist', radius * 2.2)
        camera.location = target + direction * distance
        camera.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
        path = REVIEW / f'_{label}_{index}.png'
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path))
        data = np.empty(width * height * 4, np.float32)
        image.pixels.foreach_get(data)
        frames.append(data.reshape(height, width, 4)[..., :3].copy())
        bpy.data.images.remove(image)
        path.unlink()
    for item in rig + [camera]:
        bpy.data.objects.remove(item)
    return frames


def contact(frames, columns, path):
    rows = [np.hstack(frames[i:i + columns] + [np.zeros_like(frames[0])] * (columns - len(frames[i:i + columns]))) for i in range(0, len(frames), columns)]
    png(path, np.vstack(rows[::-1]))


def export(obj):
    for other in bpy.context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(MESHES / (obj.name + '.fbx')), use_selection=True, axis_forward='-Z', axis_up='Y', bake_space_transform=False,
                             mesh_smooth_type='FACE', add_leaf_bones=False, use_triangles=True, use_tspace=False, object_types={'MESH'})


def report(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    corners = np.array([Vector(c) for c in obj.bound_box])
    lo, hi = corners.min(0), corners.max(0)
    print(f'[mesh] {obj.name}: tris={len(mesh.loop_triangles)} min={lo.round(0).tolist()} max={hi.round(0).tolist()} slots={[m.name for m in mesh.materials]}')


# ------------------------------------------------------------------ human kit

class Hull:
    """Lofted hull from half sections on +Y, each running keel to spine."""

    def __init__(self, stations):
        self.x = np.array([s[0] for s in stations], float)
        self.h = np.array([s[1] for s in stations], float)

    def at(self, x):
        i = int(np.clip(np.searchsorted(self.x, x) - 1, 0, len(self.x) - 2))
        t = (x - self.x[i]) / max(self.x[i + 1] - self.x[i], 1e-6)
        return self.h[i] * (1 - t) + self.h[i + 1] * t

    def full(self, half):
        return np.vstack((half, (half[-2:0:-1] * np.array((-1, 1)))))

    def sections(self):
        return [np.column_stack((np.full(len(p), x), p)) for x, p in ((x, self.full(h)) for x, h in zip(self.x, self.h))]

    def loft(self, slot=HULL, zone=PRIMARY, bevel=4.0, segments=2):
        return loft(self.sections(), slot, zone, bevel, segments, 22)

    def plate(self, k, x0, x1, s0=.04, s1=.96, t=12.0, cham=.3, inset=.5, slot=HULL, zone=PRIMARY, bevel=1.6):
        """Armour slab on facet k, conforming to the hull. Ends chamfer so plates read as cut, not boxes."""
        length = x1 - x0
        run = (x1 - x0)
        c = min(cham * (s1 - s0), .45 * (s1 - s0))
        xc = min(length * .09, 42)
        xs = [x0, x0 + xc, x1 - xc, x1]
        between = [x for x in self.x if x0 + xc + 1 < x < x1 - xc - 1]
        xs = sorted(xs + between)
        sections = []
        for x in xs:
            half = self.at(x)
            a, b = half[k], half[k + 1]
            d = b - a
            n = np.array((d[1], -d[0]))
            n = n / max(np.linalg.norm(n), 1e-6)
            e = 1 if x0 + xc <= x <= x1 - xc else 0
            lo = s0 + c * (1 - e)
            hi = s1 - c * (1 - e)
            top_in = inset * t / max(np.linalg.norm(d), 1)
            pts = [a + d * lo - n * 3, a + d * (lo + top_in) + n * t, a + d * (hi - top_in) + n * t, a + d * hi - n * 3]
            sections.append(np.column_stack((np.full(4, x), np.array(pts))))
        return loft(sections, slot, zone, bevel, 1, 25)


def light_wall(kit, x, y, z, width, height, strips):
    """Back-lit bulkhead: bars with dark gaps, hot in the middle band, so it never flattens to a white sheet."""
    pitch = height / strips
    for i in range(strips):
        at = z - height / 2 + pitch * (i + .5)
        hot = abs(i - (strips - 1) / 2) < strips * .17
        kit.sym(box((width, 6, pitch * .62), (x, y, at), LIGHT, BRIGHT if hot else DIM), slot=LIGHT, uv=.5)


def turret(r=150.0, barrels=3, length=600.0, n=28):
    """Naval main battery: barbette, sloped gunhouse, mantlet, sleeved barrels with muzzle brakes."""
    parts = [lathe([(0, r * 1.16), (r * .10, r * 1.16), (r * .14, r * 1.08), (r * .24, r * 1.04), (r * .28, r * .98)], n, 'Z', TRIM, SECONDARY, bevel=r * .012)]
    hw, top = r * .92, r * .78
    base = r * .24
    sec = [(-r * 1.25, .58, .58), (-r * .92, .9, .86), (-r * .55, 1, 1), (r * .35, 1, 1), (r * .98, .78, .72), (r * 1.16, .68, .6)]
    parts.append(loft([rect(hw * w, base, base + (top - base) * h + r * .06, r * .13, x) for x, w, h in sec], HULL, PRIMARY, r * .022, 2, 20))
    parts.append(box((r * .6, r * .52, r * .14), (-r * .35, 0, top + r * .1), TRIM, SECONDARY, r * .015))
    parts.append(box((r * .16, r * .2, r * .12), (-r * .1, r * .42, top + r * .1), TRIM, METAL, r * .01))
    parts.append(box((r * .5, r * .05, r * .18), (-r * .75, hw * .7, top * .62), TRIM, SECONDARY))
    parts.append(box((r * .5, r * .05, r * .18), (-r * .75, -hw * .7, top * .62), TRIM, SECONDARY))
    z = base + (top - base) * .42
    pitch = r * .46 if barrels > 1 else 0
    for i in range(barrels):
        y = (i - (barrels - 1) / 2) * pitch
        rb = r * .082
        profile = [(r * 1.0, rb * 2.1), (r * 1.22, rb * 2.1), (r * 1.26, rb * 1.7), (r * 1.7, rb * 1.42), (r * 1.76, rb * 1.1), (length * .82, rb * .92),
                   (length * .84, rb * 1.3), (length * .88, rb * 1.3), (length * .885, rb * .95), (length * .91, rb * .95), (length * .915, rb * 1.3),
                   (length * .95, rb * 1.3), (length * .955, rb * 1.05), (length, rb * 1.12), (length, rb * .66), (length * .96, rb * .6)]
        parts.append(moved(lathe(profile, 14, 'X', TRIM, METAL), mat((0, y, z))))
        parts.append(box((r * .3, rb * 3.2, rb * .9), (r * 1.08, y, z + rb * 2.1), TRIM, SECONDARY, rb * .1))
    return merge(*parts)


def point_defence(r=44.0):
    # Twin-barrel dome mount.
    ball = [(0, r), (r * .22, r), (r * .3, r * .9), (r * .62, r * .78), (r * .86, r * .46), (r * .92, r * .18)]
    parts = [lathe(ball, 14, 'Z', TRIM, SECONDARY)]
    for y in (-.2, .2):
        parts.append(moved(lathe([(r * .5, r * .13), (r * 1.7, r * .1), (r * 1.72, r * .15), (r * 2.05, r * .15), (r * 2.05, r * .05)], 8, 'X', TRIM, METAL), mat((0, y * r, r * .52))))
    return merge(*parts)


def drive_bell(r=300.0, length=520.0, n=48, ribs=20):
    """Drive bell facing -X, with regen channels, collars, gimbal rams and a plume plug."""
    # Outer skin then back in along the throat. Local x runs aft from 0 to -length.
    outer = [(0, r * .46), (-length * .1, r * .46), (-length * .15, r * .52), (-length * .42, r * .66), (-length * .72, r * .86), (-length * .98, r), (-length, r), (-length * 1.004, r * .985)]
    inner = [(-length * .98, r * .93), (-length * .72, r * .79), (-length * .42, r * .58), (-length * .18, r * .4), (-length * .08, r * .3)]
    bell = lathe(outer + inner, n, 'X', TRIM, SCORCH, cap=False, flip=True)
    parts = [bell]
    # The bell is open, so the throat gets its own plug and glow.
    parts.append(lathe([(-length * .09, r * .34), (-length * .2, r * .33), (-length * .5, r * .17), (-length * .62, 1.0)], n // 2, 'X', DRIVE, 20, cap=False, flip=True))
    parts.append(lathe([(-length * .08, r * .31), (-length * .3, r * .44)], n // 2, 'X', DRIVE, 21, cap=False))
    for at, w in ((-.22, 1.04), (-.46, 1.04), (-.7, 1.04)):
        x = length * at
        rr = np.interp(-x, [0, length * .15, length * .42, length * .72, length], [r * .46, r * .52, r * .66, r * .86, r])
        parts.append(lathe([(x + 12, rr * .98), (x + 12, rr * w + 6), (x - 12, rr * w + 6), (x - 12, rr * .98)], n, 'X', TRIM, METAL, cap=False))
    for i in range(ribs):
        t = i / ribs * 2 * math.pi
        c, s = math.cos(t), math.sin(t)
        pts = [(-length * .15, r * .53), (-length * .42, r * .67), (-length * .72, r * .87), (-length * .97, r * 1.0)]
        sec = []
        for x, rr in pts:
            sec.append(np.array([(x, (rr - 1) * c - 6 * s, (rr - 1) * s + 6 * c), (x, (rr + 8) * c - 4 * s, (rr + 8) * s + 4 * c), (x, (rr + 8) * c + 4 * s, (rr + 8) * s - 4 * c), (x, (rr - 1) * c + 6 * s, (rr - 1) * s - 6 * c)]))
        parts.append(loft(sec, TRIM, METAL))
    for i in range(4):
        t = i * math.pi / 2 + math.pi / 4
        c, s = math.cos(t), math.sin(t)
        parts.append(beam((60, r * .95 * c, r * .95 * s), (-length * .5, r * .78 * c, r * .78 * s), r * .05, slot=TRIM, zone=METAL))
        parts.append(beam((60, r * .95 * c, r * .95 * s), (-length * .22, r * .86 * c, r * .86 * s), r * .08, slot=TRIM, zone=SECONDARY))
    return merge(*parts)


def dish(r=120.0, n=24):
    # Parabolic antenna opening towards +Z, with tripod feed.
    profile = [(r * .32 * (i / 7) ** 2 * 1.4, r * i / 7 + .5) for i in range(8)]
    back = [(p[0] - r * .03, p[1] * .96) for p in profile[::-1]]
    parts = [lathe(profile + back, n, 'Z', TRIM, PRIMARY, cap=False, flip=False)]
    parts.append(lathe([(-r * .4, r * .12), (0, r * .12), (r * .04, r * .22), (r * .04, r * .05), (r * .7, r * .03), (r * .72, r * .07), (r * .82, r * .07), (r * .82, 1)], 10, 'Z', TRIM, METAL))
    for i in range(3):
        t = i / 3 * 2 * math.pi
        parts.append(beam((r * .8 * math.cos(t), r * .8 * math.sin(t), r * .24), (0, 0, r * .72), r * .012, slot=TRIM, zone=METAL))
    return merge(*parts)


def mast(height, r, spars=4):
    parts = [lathe([(0, r * 2), (height * .03, r * 2), (height * .04, r), (height * .6, r * .7), (height * .62, r * 1.4), (height * .64, r * .5), (height, r * .12)], 8, 'Z', TRIM, SECONDARY)]
    for i in range(spars):
        h = height * (.2 + .68 * i / max(spars - 1, 1))
        span = height * (.2 - .15 * i / max(spars - 1, 1))
        parts.append(box((r * .5, span * 2, r * .5), (0, 0, h), TRIM, METAL))
        parts.append(box((r * 1.4, r * .4, r * 1.4), (0, span, h), TRIM, SECONDARY))
        parts.append(box((r * 1.4, r * .4, r * 1.4), (0, -span, h), TRIM, SECONDARY))
    return merge(*parts)


def radiator(length, height, fins=7, t=10.0):
    # Heat rejection bank: louvred panels in a deep frame, hinged on a manifold.
    w = height
    parts = [box((length, w + 26, 16), (0, 0, 0), TRIM, SECONDARY, 1.6), box((length * .96, w, 12), (0, 0, 12), TRIM, DARK)]
    pitch = length * .96 / (fins * 4)
    for i in range(fins * 4):
        x = -length * .48 + pitch * (i + .5)
        parts.append(moved(box((pitch * .72, w * .96, 5), (0, 0, 0), TRIM, METAL), mat((x, 0, 20), (0, .55, 0))))
    for i in range(1, fins):
        parts.append(box((12, w + 26, 26), (-length * .48 + i * length * .96 / fins, 0, 18), TRIM, SECONDARY, 1.2))
    parts.append(box((length, 18, 26), (0, w / 2 + 10, 14), TRIM, METAL, 1.6))
    return merge(*parts)


def armour(kit, hull, k, x0, x1, rng, lengths, t=12, s0=.05, s1=.95, skip=(), gap=14, second=.45, zone=PRIMARY, win=False, tier=True, dark=.14):
    """Lay a run of plates down one facet. Plates vary in length and sit in two tiers in places."""
    x = x0
    while x < x1 - 60:
        run = float(rng.choice(lengths))
        end = min(x + run, x1)
        if x1 - end < 80:
            end = x1
        if not any(a < end and x < b for a, b in skip):
            kit.sym(hull.plate(k, x, end, s0, s1, t, .12, .6, zone=SECONDARY if (rng.random() < dark and not win) else zone), win=1.0 if win else 0.0)
            if tier and rng.random() < second and end - x > 170:
                pad = (end - x) * rng.uniform(.14, .26)
                span = s1 - s0
                a = s0 + span * rng.uniform(.14, .3)
                b = s1 - span * rng.uniform(.14, .3)
                kit.sym(hull.plate(k, x + pad, end - pad, a, b, t + rng.uniform(5, 9), .08, 1.0, slot=TRIM if rng.random() < .35 else HULL, zone=SECONDARY if rng.random() < .35 else zone, bevel=1.2))
        x = end + gap


# ------------------------------------------------------------------ deck machinery

def vent_bank(l=150.0, w=70.0, slats=7):
    # Recessed heat vent: raised coaming around angled louvres.
    parts = [box((l, w, 7), (0, 0, 3.5), TRIM, DARK)]
    for sx, sy, dx, dy in ((l, 6, 0, w / 2), (l, 6, 0, -w / 2), (6, w + 6, l / 2, 0), (6, w + 6, -l / 2, 0)):
        parts.append(box((sx, sy, 12), (dx, dy, 6), TRIM, SECONDARY, .7))
    pitch = l / slats
    for i in range(slats):
        parts.append(moved(box((pitch * .55, w - 8, 2.4), (0, 0, 0), TRIM, METAL), mat((-l / 2 + pitch * (i + .5), 0, 8.5), (0, .6, 0))))
    return merge(*parts)


def hatch(r=34.0):
    # Personnel lock: collar, dished door, locking dogs.
    parts = [lathe([(0, r), (6, r), (9, r * .9), (9, r * .78), (6, r * .72), (11, r * .3), (11, 1)], 18, 'Z', TRIM, SECONDARY, .5)]
    for i in range(6):
        t = i / 6 * 2 * math.pi
        parts.append(box((7, 4, 4), (math.cos(t) * r * .88, math.sin(t) * r * .88, 10.5), TRIM, METAL))
    parts.append(box((r * 1.1, 3, 3), (0, 0, 12.5), TRIM, HAZARD))
    return merge(*parts)


def rcs(s=26.0):
    # Attitude thruster quad.
    parts = [box((s * 2.4, s * 2.4, s * .7), (0, 0, s * .35), TRIM, SECONDARY, 1, s * .2)]
    for dx, dy, rz in ((1, 0, 0), (-1, 0, math.pi), (0, 1, math.pi / 2), (0, -1, -math.pi / 2)):
        nozzle = lathe([(s * .3, s * .2), (s * .55, s * .24), (s * .95, s * .36), (s * .95, s * .3), (s * .4, s * .12)], 10, 'X', TRIM, SCORCH, cap=False)
        parts.append(moved(nozzle, mat((dx * s * .6, dy * s * .6, s * .4), (0, 0, rz))))
    return merge(*parts)


def blister(r=44.0):
    # Sensor blister: faired dome on a machined base.
    return lathe([(0, r * 1.1), (r * .1, r * 1.1), (r * .14, r), (r * .3, r * .96), (r * .55, r * .78), (r * .75, r * .46), (r * .82, r * .1)], 18, 'Z', TRIM, SECONDARY, .5)


def locker(l=120.0, w=56.0, h=28.0):
    # Armoured ready-use locker with two hinged lids.
    parts = [box((l, w, h), (0, 0, h / 2), HULL, PRIMARY, 1.1, 3)]
    for x in (-l * .25, l * .25):
        parts.append(box((l * .42, w * .8, 3), (x, 0, h + 1), TRIM, SECONDARY, .5))
        parts.append(box((l * .1, w * .86, 5), (x, 0, h + 3), TRIM, METAL))
    return merge(*parts)


def run_pipe(kit, hull, k, s, x0, x1, lift, r, step=90.0):
    # Service main along one facet, held off the plates by clamps.
    points = []
    for x in np.arange(x0, x1 + 1, step):
        half = hull.at(x)
        a, b = half[k], half[k + 1]
        d = b - a
        n = np.array((d[1], -d[0])) / max(np.linalg.norm(d), 1e-6)
        p = a + d * s + n * lift
        points.append((x, p[0], p[1]))
    kit.sym(loft([ring(r, 0, 8) + np.array(p) for p in points], TRIM, METAL), tone=.45)
    for p in points[::2]:
        kit.sym(box((9, r * 3, lift + r), (p[0], p[1], p[2] - lift / 2), TRIM, SECONDARY), tone=.45)


def fittings(kit, hull, k, x0, x1, blocked, scale=1.0, lift=14.0, spacing=240.0):
    """Working machinery bolted to one armour facet. Items sit in clusters with empty deck between."""
    rng = kit.rng
    kinds = (vent_bank(150 * scale, 70 * scale), hatch(34 * scale), rcs(26 * scale), blister(44 * scale), locker(120 * scale, 56 * scale, 28 * scale))
    weights = (.34, .2, .1, .14, .22)
    x = x0
    while x < x1:
        x += float(rng.uniform(.7, 1.4)) * spacing * scale
        if rng.random() < .25 or x >= x1 or any(a - 70 < x < b + 70 for a, b in blocked):
            continue
        half = hull.at(x)
        a, b = half[k], half[k + 1]
        d = b - a
        n = np.array((d[1], -d[0])) / max(np.linalg.norm(d), 1e-6)
        s = float(rng.uniform(.25, .78))
        p = a + d * s + n * lift
        roll = math.atan2(-n[0], n[1])
        kit.sym(kinds[int(rng.choice(5, p=weights))], mat((x, p[0], p[1]), (roll, 0, 0)), tone=float(rng.uniform(.2, .7)))


# ------------------------------------------------------------------ cruiser

def warship_section(w, ht, hb, tz, tw, d):
    """Half section keel to spine with a recessed side trench. Facets: 0 keel, 1-3 lower flank,
    4 trench floor lower lip, 5 trench floor, 6 trench upper lip, 7 upper flank, 8 shoulder, 9 deck."""
    return np.array([(0, -hb * 1.05), (w * .34, -hb), (w * .78, -hb * .74), (w, -hb * .2), (w, tz - tw), (w - d, tz - tw * .6),
                     (w - d, tz + tw * .6), (w * .985, tz + tw), (w * .9, ht * .62), (w * .5, ht * .93), (0, ht)])


def cruiser_textures_cfg():
    def mark(P, N, D, colour, zone):
        # Federation ID on the flanks, a broad fore band, and a pale spine stripe.
        band = (np.abs(P[..., 0] - 1050) < 60) & (zone == PRIMARY)
        colour[band] = ZONE_COLOURS[ACCENT]
        thin = (np.abs(P[..., 0] - 960) < 11) & (zone == PRIMARY)
        colour[thin] = (.32, .2, .05)
        stamp(P, N, colour, zone, TEXT['FNS-2312'], 110, (1400, 190), 1)
        stamp(P, N, colour, zone, TEXT['FNS-2312'], 110, (1400, 190), -1)
    return {'seed': 12, 'tile_cm': 1800, 'height_scale': 1.5, 'length': 6000, 'ao': 340, 'hazard_pitch': 60, 'soot_x': -2900,
            'window_pitch': (15, 34), 'window_size': (8, 11), 'mark': mark, 'impacts': 34, 'impact': (22, 95)}


TEXT = {}


def stamp(P, N, colour, zone, mask, height_cm, centre, side, paint=(.17, .165, .15)):
    # Project a mask onto a Y-facing flank in world XZ.
    h, w = mask.shape
    x = (P[..., 0] - centre[0]) / (height_cm / h) * -side + w / 2
    y = (P[..., 2] - centre[1]) / (height_cm / h) + h / 2
    hit = (x >= 0) & (x < w - 1) & (y >= 0) & (y < h - 1) & (N[..., 1] * side > .55) & (zone <= SECONDARY)
    values = mask[y[hit].astype(int), x[hit].astype(int)] > .5
    target = colour[hit]
    target[values] = paint
    colour[hit] = target


def cruiser_hull():
    w = warship_section
    rows = [(-2780, w(560, 500, 390, 110, 60, 40)), (-2640, w(700, 590, 470, 110, 70, 50)),
            (-2560, w(760, 640, 510, 110, 70, 50)), (-2520, w(800, 660, 530, 110, 70, 56)),
            (-1540, w(960, 720, 580, 110, 80, 62)), (-1500, w(930, 700, 560, 110, 80, 62)),
            (-1440, w(900, 680, 540, 110, 80, 62)),
            (-260, w(830, 620, 500, 110, 76, 58)), (-220, w(800, 600, 480, 110, 76, 58)),
            (-160, w(770, 580, 460, 100, 70, 54)),
            (880, w(590, 460, 370, 70, 54, 42)), (920, w(560, 436, 350, 70, 50, 40)), (980, w(530, 420, 336, 60, 46, 36)),
            (1880, w(320, 300, 240, 30, 30, 22)), (1930, w(300, 282, 226, 30, 28, 20)),
            (2480, w(190, 196, 150, 10, 18, 12)), (2900, w(92, 118, 84, 0, 10, 6)), (2980, w(60, 84, 60, 0, 8, 4))]
    return Hull(rows)


def trench_dressing(kit, hull, x0, x1, side_step=120.0):
    # Conduits and frames in the side trench: the recess reads as working structure.
    for x in np.arange(x0, x1, side_step):
        half = hull.at(x)
        a, b = half[5], half[6]
        kit.sym(box((16, 18, abs(b[1] - a[1]) + 8), (x, a[0] + 8, (a[1] + b[1]) / 2), TRIM, METAL), tone=.3)
    for off, r in ((.25, 9), (.5, 13), (.76, 7)):
        points = []
        for x in np.arange(x0, x1 + 1, 100):
            half = hull.at(x)
            a, b = half[5], half[6]
            p = a + (b - a) * off
            points.append((x, p[0] + r + 2, p[1]))
        sections = [ring(r, 0, 8) + np.array(p) for p in points]
        kit.sym(loft(sections, TRIM, METAL), tone=.5)
    for x in np.arange(x0 + 60, x1, side_step * 3):
        half = hull.at(x)
        p = (half[5] + half[6]) / 2
        kit.sym(box((60, 6, 6), (x, p[0] + 2, p[1]), LIGHT, AMBER), slot=LIGHT)


def sponson_section(w, top, bot, depth=0.0, mouth=60.0):
    # Half section of the sponson around its own centreline: outer face at +w, with a pocket of `depth`.
    # A pocket jump between adjacent stations makes real end walls with no booleans.
    return [(-w * .7, bot * .9), (w * .66, bot), (w, bot * .55), (w, -mouth), (w - depth, -mouth * .9), (w - depth, mouth * .9), (w, mouth), (w, top * .55), (w * .62, top), (-w * .7, top * .92)]


def sponson(kit):
    """Flight pod: hangar pocket in the outboard face, armoured over, with a landing bay light well."""
    y0 = 1320.0
    xs = [(-2120, 160, 150, 170, 0), (-2040, 240, 200, 210, 0), (-1980, 268, 222, 230, 0), (-1400, 268, 222, 230, 0), (-1390, 268, 222, 230, 200), (260, 268, 222, 230, 200),
          (270, 268, 222, 230, 0), (360, 268, 222, 230, 0), (760, 200, 170, 190, 0), (1120, 60, 96, 110, 0)]
    sections = []
    for x, w, top, bot, depth in xs:
        sec = sponson_section(w, top, -bot, depth, 96)
        sections.append(np.array([(x, y0 + a, b) for a, b in sec]))
    kit.sym(loft(sections, HULL, PRIMARY, 4, 2, 20), tone=.42)
    # Pylons to the main hull, swept.
    for x, t in ((-1640, 220), (-500, 280)):
        kit.sym(loft([rect(t * .5, -90, 100, 22, 0, 0) @ np.array(((0, 1, 0), (1, 0, 0), (0, 0, 1))) + np.array((x, y, 0)) for y in (840, 1060, 1120)], TRIM, SECONDARY, 2.5), tone=.2)
    # Hangar interior: ribs, deck and a lit back wall.
    outer = y0 + 268
    back = outer - 200
    light_wall(kit, -565, back + 6, 0, 1630, 170, 7)
    for x in np.arange(-1360, 240, 110):
        kit.sym(box((26, 196, 196), (x, outer - 98, 0), TRIM, SECONDARY, 1.2), tone=.5)
        kit.sym(box((14, 7, 7), (x + 55, back + 9, 88), LIGHT, WARM), slot=LIGHT, uv=.4)
    for x in np.arange(-1320, 240, 330):
        kit.sym(box((16, 22, 210), (x, outer + 2, 0), TRIM, SECONDARY, 1.0), tone=.5)
    kit.sym(box((1660, 8, 8), (-565, outer + 4, 98), LIGHT, AMBER), slot=LIGHT)
    kit.sym(box((1660, 8, 8), (-565, outer + 4, -98), LIGHT, AMBER), slot=LIGHT)
    # Hazard lip around the mouth.
    kit.sym(box((1680, 16, 16), (-565, outer + 1, 112), TRIM, HAZARD, 1), uv=1.4)
    kit.sym(box((1680, 16, 16), (-565, outer + 1, -112), TRIM, HAZARD, 1), uv=1.4)
    # Layered armour on the pod.
    rng = kit.rng
    for z0, z1, y1 in ((122, 214, 268), (-224, -122, 268)):
        for x in np.arange(-1960, 340, 1):
            break
        x = -1960.0
        while x < 340:
            run = float(rng.choice((220, 300, 380)))
            end = min(x + run, 350)
            outline = [(x + 22, z0), (end - 22, z0), (end, z0 + 22), (end, z1 - 8), (end - 8, z1), (x + 8, z1), (x, z1 - 8), (x, z0 + 22)]
            kit.sym(slab(outline, 11, HULL, PRIMARY, 1.4), mat((0, outer - .5, 0), (math.pi / 2, 0, 0)) @ mat(scale=(1, 1, -1)))
            x = end + 12
    for x in np.arange(-1920, 300, 420):
        kit.sym(moved(point_defence(30), mat((x + 120, y0 + 210, 200))), tone=.3) if False else None
    # Dorsal pod deck: a turret and radiators.
    kit.sym(turret(92, 2, 380), mat((-300, y0 + 40, 216)), tone=.15)
    kit.sym(turret(92, 2, 380), mat((-1050, y0 + 40, 216)), tone=.15)
    kit.sym(radiator(560, 150, 4), mat((-1660, y0 - 10, 222)), tone=.6)
    # Aft pod drive.
    kit.sym(drive_bell(150, 280, 32, 12), mat((-2110, y0, 30)), tone=.5)
    kit.sym(lathe([(-2150, 150), (-2150, 176), (-2030, 176), (-2030, 150)], 32, 'X', TRIM, SECONDARY, cap=False), mat((0, y0, 30)), tone=.5)


def citadel(kit, x, scale=1.0):
    """Stepped command superstructure, three tiers, with a canted bridge and sensor crown."""
    tiers = [(-760, 700, 330, 420, 150), (-610, 520, 240, 570, 130), (-470, 340, 170, 700, 110)]
    for x0, length, hw, z, h in tiers:
        sec = [(x0, .78, .7), (x0 + 50, 1, .92), (x0 + length - 90, 1, 1), (x0 + length, .7, 1.0)]
        sections = [rect(hw * s, z - 6, z + h * t, 14, x + a) for a, s, t in sec]
        kit.add(loft(sections, HULL, PRIMARY, 2.6, 2, 20), win=1.0, tone=.4)
        kit.add(box((length * .78, hw * 1.7, 12), (x + x0 + length * .45, 0, z + h * .98), TRIM, SECONDARY, 1.5), tone=.2)
    # Bridge: a canted glass face.
    bx = x - 180
    z = 810
    sections = [rect(120, z, z + 92, 12, bx - 170), rect(140, z, z + 100, 14, bx - 110), rect(140, z, z + 104, 14, bx + 70), rect(96, z + 8, z + 60, 12, bx + 190)]
    kit.add(loft(sections, HULL, SECONDARY, 2.4, 2, 20), tone=.2)
    for side in (-1, 1):
        kit.add(box((8, 6, 26), (bx + 150, side * 118, z + 62), LIGHT, COOL), slot=LIGHT, uv=.5)
    glass = [np.array([(bx + 86, y, z + 90) for y in (-120, 120)]), np.array([(bx + 188, y, z + 62) for y in (-84, 84)])]
    kit.add(loft(glass, LIGHT, GLASS, cap=False, closed=False, flip=False), slot=LIGHT)
    for y in np.arange(-98, 99, 28):
        kit.add(beam((bx + 86, y, z + 91), (bx + 188, y * .7, z + 63), 2.0, slot=TRIM, zone=SECONDARY))
    kit.add(mast(420, 11), mat((bx - 150, 0, z + 100)), tone=.1)
    kit.add(dish(92), mat((bx - 60, 92, z + 118), (.3, .1, 0)), tone=.1)
    kit.add(dish(70), mat((bx + 20, -86, z + 116), (-.3, -.2, 0)), tone=.1)
    kit.add(box((140, 12, 90), (bx - 240, 138, z + 30), TRIM, SECONDARY, 1.0), tone=.1)
    kit.add(box((140, 12, 90), (bx - 240, -138, z + 30), TRIM, SECONDARY, 1.0), tone=.1)


def cruiser(size):
    kit = Kit('SM_Ship_Cruiser', HUMAN_SLOTS, 11)
    rng = kit.rng
    hull = cruiser_hull()
    kit.add(hull.loft(bevel=5), tone=.5)
    keep = [(-1500, -1420), (-240, -160), (900, 980), (1880, 1930)]
    turrets = [(-120, 0), (560, 0), (1280, 0)]
    # Deck armour with clear rings left around barbettes.
    blocked = [(x - 230, x + 230) for x, _ in turrets]
    armour(kit, hull, 9, -2500, -1560, rng, (260, 340, 420), 14, .02, .96, gap=16)
    armour(kit, hull, 9, -1420, 860, rng, (220, 300, 380), 14, .22, .96, blocked, gap=16)
    armour(kit, hull, 9, 980, 1860, rng, (180, 240), 11, .16, .96, blocked, gap=14)
    armour(kit, hull, 8, -2500, -1560, rng, (300, 380, 480), 16, .03, .97, gap=14)
    armour(kit, hull, 8, -1420, -280, rng, (260, 340), 15, .03, .97, gap=14)
    armour(kit, hull, 8, -140, 860, rng, (240, 320), 14, .03, .97, gap=14)
    armour(kit, hull, 8, 980, 1860, rng, (200, 280), 12, .03, .97, gap=14)
    armour(kit, hull, 7, -2500, -1560, rng, (240, 320), 10, .08, .92, gap=14, win=True, tier=False)
    armour(kit, hull, 7, -1420, -280, rng, (240, 320), 10, .08, .92, gap=14, win=True, tier=False)
    armour(kit, hull, 7, -140, 860, rng, (220, 300), 9, .08, .92, gap=14, win=True, tier=False)
    armour(kit, hull, 3, -2500, -1560, rng, (340, 440), 16, .05, .9, gap=14, second=.5)
    armour(kit, hull, 3, -1420, -280, rng, (300, 380), 14, .05, .9, gap=14)
    armour(kit, hull, 3, -140, 860, rng, (260, 340), 13, .05, .9, gap=14)
    armour(kit, hull, 2, -2500, -1560, rng, (340, 440), 15, .04, .96, gap=14)
    armour(kit, hull, 2, -1420, -280, rng, (300, 380), 14, .04, .96, gap=14)
    armour(kit, hull, 2, -140, 860, rng, (260, 340), 12, .04, .96, gap=14)
    armour(kit, hull, 2, 980, 1860, rng, (200, 280), 11, .04, .96, gap=14)
    armour(kit, hull, 1, -2500, 860, rng, (360, 480), 11, .1, .96, gap=16)
    armour(kit, hull, 0, -2300, 600, rng, (420, 520), 10, .1, .9, gap=16, tier=False, zone=SECONDARY)
    trench_dressing(kit, hull, -2470, -1570)
    trench_dressing(kit, hull, -1400, -300)
    trench_dressing(kit, hull, -130, 860)
    trench_dressing(kit, hull, 1000, 1840, 90)
    blocked_all = blocked + [(-2460, -1700), (-1540, -1420), (-260, -160), (880, 980)]
    for k, lift, spacing in ((9, 14, 230), (8, 15, 250), (3, 15, 280), (2, 14, 300), (1, 11, 340)):
        fittings(kit, hull, k, -2500, 860, blocked_all if k >= 8 else keep, 1.0, lift, spacing)
    fittings(kit, hull, 9, 980, 1860, blocked, .8, 11, 230)
    fittings(kit, hull, 2, 980, 1860, [], .8, 11, 280)
    run_pipe(kit, hull, 8, .3, -2480, -1580, 24, 11)
    run_pipe(kit, hull, 8, .36, -2480, -1580, 24, 7)
    run_pipe(kit, hull, 8, .3, -1400, 840, 24, 11)
    run_pipe(kit, hull, 8, .72, -1400, 840, 24, 8)
    run_pipe(kit, hull, 3, .6, -1400, 840, 24, 12)
    sponson(kit)
    citadel(kit, -1100)
    # Forward main battery, superfiring along the deck on raised barbettes.
    for (x, _), r, z_add in zip(turrets, (172, 160, 142), (0, 48, 0)):
        half = hull.at(x)
        z = half[-1][1]
        kit.add(lathe([(z - 60, 215), (z + z_add + 6, 215), (z + z_add + 16, 200)], 36, 'Z', TRIM, SECONDARY, 2.5))
        kit.add(turret(r, 3, r * 4.0), mat((x, 0, z + z_add + 12)), tone=.35)
    kit.add(turret(150, 3, 600), mat((-2200, 0, 640), (0, 0, math.pi)), tone=.35)
    kit.add(lathe([(590, 205), (650, 205), (660, 190)], 36, 'Z', TRIM, SECONDARY, 2.5), mat((-2200, 0, 0)))
    # Ventral battery.
    for x, r in ((-500, 150), (420, 136)):
        half = hull.at(x)
        z = half[0][1]
        kit.add(lathe([(-z - 60, r * 1.3), (-z + 6, r * 1.3), (-z + 16, r * 1.18)], 36, 'Z', TRIM, SECONDARY, 2.5), mat((x, 0, 0), (math.pi, 0, 0)))
        kit.add(turret(r, 2, r * 3.6), mat((x, 0, z - 12), (math.pi, 0, 0)), tone=.35)
    # Shoulder point defence, one per bay.
    for x in (-2300, -1900, -1140, -640, 40, 480, 760, 1160, 1640):
        half = hull.at(x)
        p = (half[8] + half[9]) / 2
        kit.sym(point_defence(46), mat((x, p[0], p[1] + 10), (0, -.5, 0)), tone=.3)
        p = (half[1] + half[2]) / 2
        if x < 900:
            kit.sym(point_defence(40), mat((x + 90, p[0], p[1] - 8), (math.pi, .4, 0)), tone=.3)
    # Spinal lance through the prow.
    kit.add(lathe([(2860, 62), (3020, 56), (3030, 66), (3090, 66), (3094, 46), (3112, 46), (3116, 62), (3150, 62), (3150, 32), (3090, 24)], 24, 'X', TRIM, METAL), tone=.3)
    for t in range(4):
        a = t * math.pi / 2 + math.pi / 4
        c, s = math.cos(a), math.sin(a)
        kit.add(beam((2500, c * 90, s * 90), (3060, c * 70, s * 70), 12, slot=TRIM, zone=SECONDARY), tone=.3)
    kit.add(lathe([(3120, 20), (3120, 1)], 16, 'X', LIGHT, COOL, cap=False), slot=LIGHT)
    # Stern: drive block with a stepped frame around four main bells.
    aft = [(y, z, r) for y in (-340, 340) for z in (-160, 300)]
    kit.add(loft([rect(760, -470, 590, 90, -2780), rect(760, -470, 590, 90, -2800), rect(700, -420, 540, 80, -2830)], TRIM, SECONDARY, 4) if False else loft([rect(560, -380, 500, 80, -2790), rect(530, -360, 470, 74, -2830)], TRIM, SECONDARY, 4), tone=.3)
    for y, z in ((-300, 240), (300, 240), (-300, -170), (300, -170)):
        kit.add(lathe([(-2845, 212), (-2845, 238), (-2815, 238), (-2815, 206)], 44, 'X', TRIM, METAL, cap=False), mat((0, y, z)), tone=.3)
        kit.add(drive_bell(205, 360, 44, 18), mat((-2835, y, z)), tone=.3)
    kit.add(lathe([(-2860, 90), (-2860, 150), (-2800, 150)], 32, 'X', TRIM, SECONDARY, cap=False), mat((0, 0, 40)), tone=.4)
    kit.add(drive_bell(118, 220, 32, 12), mat((-2840, 0, 40)), tone=.3)
    kit.sym(radiator(620, 210, 5), mat((-2080, 330, 626), (-.32, 0, 0)), tone=.6)
    # Ventral fin and sensors.
    kit.add(loft([np.array([(-1800, -9, -560), (-1800, 9, -560), (-1800, 9, -480), (-1800, -9, -480)]), np.array([(-1300, -9, -640), (-1300, 9, -640), (-1300, 9, -480), (-1300, -9, -480)]), np.array([(-1120, -7, -540), (-1120, 7, -540), (-1120, 7, -480), (-1120, -7, -480)])], TRIM, SECONDARY, 1.5))
    kit.sym(dish(84), mat((2010, 186, 196), (0, .5, 1.1)), tone=.1)
    # Port and starboard running lights, ventral beacons.
    for side, zone in ((1, GREEN), (-1, RED)):
        kit.add(box((40, 14, 14), (1100, side * 1600 * .36, 80), LIGHT, zone), slot=LIGHT)
        kit.add(box((26, 10, 10), (-2010, side * 1590, 10), LIGHT, zone), slot=LIGHT)
    return kit


# ------------------------------------------------------------------ frigate

def frigate_cfg():
    def mark(P, N, D, colour, zone):
        band = (np.abs(P[..., 0] - 420) < 34) & (zone == PRIMARY)
        colour[band] = ZONE_COLOURS[ACCENT]
        stamp(P, N, colour, zone, TEXT['FNS-0417'], 58, (640, 70), 1)
        stamp(P, N, colour, zone, TEXT['FNS-0417'], 58, (640, 70), -1)
    return {'seed': 22, 'tile_cm': 900, 'height_scale': 1.1, 'length': 2600, 'ao': 180, 'hazard_pitch': 40, 'soot_x': -1250,
            'window_pitch': (11, 24), 'window_size': (6, 8), 'mark': mark, 'impacts': 16, 'impact': (12, 55)}


def frigate(size):
    """Fast escort: blade hull, swept wing roots carrying outboard drives, missile deck, one hangar in the belly."""
    kit = Kit('SM_Ship_Frigate', HUMAN_SLOTS, 12)
    rng = kit.rng
    w = warship_section
    hull = Hull([(-1180, w(250, 230, 170, 40, 30, 20)), (-1130, w(310, 270, 200, 40, 34, 24)), (-1090, w(340, 290, 212, 40, 34, 26)),
                 (-470, w(380, 310, 226, 40, 36, 28)), (-440, w(350, 290, 212, 40, 34, 26)), (-400, w(330, 276, 204, 36, 32, 26)),
                 (210, w(270, 226, 170, 24, 26, 20)), (240, w(250, 212, 160, 24, 24, 18)), (280, w(236, 202, 152, 22, 22, 16)),
                 (800, w(130, 130, 96, 8, 12, 8)), (1190, w(44, 58, 42, 0, 6, 3)), (1290, w(14, 26, 18, 0, 3, 1))])
    kit.add(hull.loft(bevel=3), tone=.5)
    armour(kit, hull, 9, -1080, -480, rng, (140, 180, 220), 8, .3, .96, gap=9)
    armour(kit, hull, 9, -390, 200, rng, (130, 170), 8, .36, .96, [(-140, 90)], gap=9)
    armour(kit, hull, 9, 290, 760, rng, (110, 150), 7, .1, .96, [(350, 560)], gap=8)
    for k, ts, tier in ((8, 10, True), (3, 9, True), (2, 8, True), (1, 7, False)):
        armour(kit, hull, k, -1080, -480, rng, (160, 210, 260), ts, .04, .96, gap=9, tier=tier)
        armour(kit, hull, k, -390, 200, rng, (140, 180, 230), ts, .04, .96, gap=9, tier=tier)
        armour(kit, hull, k, 290, 760, rng, (120, 170), ts * .8, .04, .96, gap=8, tier=tier)
    armour(kit, hull, 7, -1080, -480, rng, (130, 170), 6, .1, .9, gap=9, win=True, tier=False)
    armour(kit, hull, 7, -390, 200, rng, (130, 170), 6, .1, .9, gap=9, win=True, tier=False)
    for k, lift, spacing in ((8, 11, 170), (3, 10, 190), (2, 9, 210)):
        fittings(kit, hull, k, -1060, 180, [(-470, -390)], .58, lift, spacing)
    fittings(kit, hull, 9, -1060, -500, [], .58, 9, 150)
    run_pipe(kit, hull, 8, .4, -1060, -490, 15, 6, 60)
    run_pipe(kit, hull, 8, .4, -380, 190, 15, 6, 60)
    trench_dressing(kit, hull, -1080, -480, 60)
    trench_dressing(kit, hull, -390, 200, 60)
    # Wing roots: broad swept slabs. Their silhouette is what separates this ship from the cruiser.
    wing = [(-1120, 300), (-470, 300), (-720, 880), (-1040, 960), (-1180, 960), (-1250, 760)]
    plate = slab(wing, 44, HULL, PRIMARY, 3, 2)
    kit.sym(plate, mat((0, 0, -22)), tone=.45)
    kit.sym(slab([(-1080, 330), (-560, 330), (-740, 760), (-1060, 830)], 12, TRIM, SECONDARY, 1.6), mat((0, 0, 22)), tone=.25)
    kit.sym(slab([(-1040, 560), (-820, 500), (-780, 700), (-980, 790)], 8, HULL, ACCENT, 1.2), mat((0, 0, 33)), tone=.3)
    # Outboard drive pods.
    pod = loft([rect(112, -90, 90, 26, x * 1.0) * np.array((1, s, s)) for x, s in ((-1290, .7), (-1240, 1), (-860, 1), (-690, .75), (-520, .22))], HULL, PRIMARY, 3, 2, 20)
    kit.sym(pod, mat((0, 900, 0)), tone=.4)
    kit.sym(turret(46, 2, 200), mat((-900, 900, 86)), tone=.2)
    kit.sym(lathe([(-1300, 80), (-1300, 92), (-1240, 92), (-1240, 70)], 32, 'X', TRIM, METAL, cap=False), mat((0, 900, 0)), tone=.2)
    kit.sym(drive_bell(84, 150, 32, 12), mat((-1296, 900, 0)), tone=.3)
    kit.add(lathe([(-1208, 160), (-1208, 205), (-1160, 205), (-1160, 150)], 40, 'X', TRIM, METAL, cap=False), mat((0, 0, 30)), tone=.3)
    kit.add(drive_bell(150, 250, 40, 16), mat((-1190, 0, 30)), tone=.3)
    # Vertical launch deck: a real grid of cell hatches.
    for i, x in enumerate(np.arange(-340, 180, 46)):
        for y in (-108, -62, -16, 30, 76):
            half = hull.at(x)
            z = half[-1][1] * .98 - abs(y) * .06
            kit.add(box((36, 36, 7), (x, y + 16, z), TRIM, SECONDARY, 1.0, 2.5), tone=.3)
            kit.add(box((26, 26, 3), (x, y + 16, z + 4), TRIM, HAZARD if (i * 3 + int(y)) % 7 == 0 else METAL, .0, .6), tone=.3, uv=.6)
    # Main guns.
    half = hull.at(450)
    kit.add(lathe([(-40, 96), (half[-1][1] + 8, 96), (half[-1][1] + 14, 88)], 28, 'Z', TRIM, SECONDARY, 1.5), mat((450, 0, 0)))
    kit.add(turret(84, 2, 340), mat((450, 0, half[-1][1] + 10)), tone=.35)
    # Command tower: one tall stepped block, set right aft so the profile stays lean.
    for x0, x1, hw, z0, z1 in ((-1040, -520, 160, 270, 400), (-980, -600, 118, 390, 490), (-930, -650, 84, 480, 560)):
        sections = [rect(hw * .7, z0, z1 * .96, 7, x0), rect(hw, z0, z1, 8, x0 + 40), rect(hw, z0, z1, 8, x1 - 70), rect(hw * .7, z0, z1 * .9, 7, x1)]
        kit.add(loft(sections, HULL, PRIMARY, 1.8, 2, 20), win=1.0, tone=.4)
        kit.add(box(((x1 - x0) * .7, hw * 1.6, 7), ((x0 + x1) / 2 - 20, 0, z1 + 2), TRIM, SECONDARY, 1), tone=.2)
    glass = [np.array([(-720, y, 548) for y in (-66, 66)]), np.array([(-648, y, 512) for y in (-48, 48)])]
    kit.add(loft(glass, LIGHT, GLASS, cap=False, closed=False), slot=LIGHT)
    kit.add(mast(240, 6.5), mat((-880, 0, 560)), tone=.1)
    kit.add(dish(52), mat((-790, 46, 564), (.3, .1, 0)), tone=.1)
    # Belly hangar: pocket in a keel module.
    rows = []
    for x, hw, depth in ((-860, 90, 0), (-800, 200, 0), (-690, 210, 0), (-680, 210, 130), (-120, 210, 130), (-110, 210, 0), (-40, 210, 0), (120, 90, 0)):
        rows.append(np.array([(x, -hw * .3, -160), (x, hw - depth, -190), (x, hw - depth, -244), (x, hw, -244) if depth == 0 else (x, hw - depth, -244), (x, hw, -270), (x, hw * .4, -300), (x, -hw * .4, -300), (x, -hw, -270), (x, -hw + depth, -244), (x, -hw + depth, -190), (x, hw * .3, -160)]))
    kit.add(loft(rows, HULL, PRIMARY, 2.2, 2, 20), tone=.4)
    light_wall(kit, -400, 72, -216, 470, 80, 5)
    for x in np.arange(-660, -120, 62):
        kit.sym(box((12, 118, 96), (x, 126, -216), TRIM, SECONDARY, .7), tone=.5)
    kit.sym(box((550, 12, 12), (-400, 208, -186), TRIM, HAZARD, .8), uv=1.4)
    for x in (-980, -700, -320, 40, 340, 620):
        half = hull.at(x)
        p = (half[8] + half[9]) / 2
        kit.sym(point_defence(26), mat((x, p[0], p[1] + 5), (0, -.5, 0)), tone=.3)
    for side, zone in ((1, GREEN), (-1, RED)):
        kit.add(box((22, 7, 7), (-1100, side * 962, 0), LIGHT, zone), slot=LIGHT)
    kit.sym(dish(40), mat((720, 118, 100), (.6, .1, 0)), tone=.1)
    return kit


# ------------------------------------------------------------------ First Ones

def gem_cuts(bm, rng, length, width, thick, count):
    # Slice the form with planes. Each cut leaves one large clean facet, the way a stone is cut.
    for _ in range(count):
        verts = bm.verts[:]
        if len(verts) < 8:
            return
        co = np.array([v.co[:] for v in verts])
        t = rng.uniform(.12, .9)
        x = co[:, 0].min() + (co[:, 0].max() - co[:, 0].min()) * t
        turn = rng.uniform(0, 2 * math.pi)
        normal = Vector((rng.uniform(-.5, .5), math.cos(turn), math.sin(turn) * width / max(thick, 1) * .7)).normalized()
        near = np.abs(co[:, 0] - x) < length * .3
        pool = co[near] if near.any() else co
        reach = (pool @ np.array(normal)).max()
        base = Vector((x, 0, 0)).dot(normal)
        offset = base + (reach - base) * rng.uniform(.74, .9)
        # Tips and the blade's ends define its length: a cut may never remove them.
        tips = co[[co[:, 0].argmin(), co[:, 0].argmax()]]
        if (tips @ np.array(normal)).max() >= offset:
            continue
        plane = normal * offset
        cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=.01, plane_co=plane, plane_no=normal, clear_outer=True)
        edges = [e for e in cut['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            for face in bmesh.ops.holes_fill(bm, edges=edges, sides=64)['faces']:
                face.material_index = CRYSTAL
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def blade(length, width, thick, seed, sides=6, belly=.42, tip=.0, glow=(0, 3), seam=None, stations=None, cuts=None):
    """A crystal blade along +X from 0. Big planar facets; chosen long edges become luminous seams."""
    rng = np.random.default_rng(seed)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + rng.uniform(-.17, .17, sides) + .4
    rad = rng.uniform(.82, 1.12, sides)
    prof = np.stack((np.cos(ang) * rad * width / 2, np.sin(ang) * rad * thick / 2), 1)
    stations = stations or ((0, .012), (belly * .34, .62), (belly, 1), (belly + (1 - belly) * .46, .66), (1, .012))
    bm = bmesh.new()
    rows = []
    for i, (t, s) in enumerate(stations):
        # Facet edges drift between stations so faces are never parallel to the axis.
        drift = rng.uniform(-.1, .1, (sides, 2)) * (width, thick) * s * (0 < i < len(stations) - 1)
        lean = np.array((tip * width * t * t, tip * .3 * thick * t))
        pts = prof * s + drift + lean
        rows.append([bm.verts.new((t * length, y, z)) for y, z in pts])
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    for a, b in zip(rows, rows[1:]):
        for j in range(sides):
            k = (j + 1) % sides
            bm.faces.new((a[j], a[k], b[k], b[j]))
    bm.edges.ensure_lookup_table()
    long_edges = []
    for j in glow:
        for a, b in zip(rows, rows[1:]):
            e = bm.edges.get((a[j], b[j]))
            if e:
                long_edges.append(e)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) == 4], quad_method='SHORT_EDGE')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    seam = max(seam if seam is not None else width * .018, length * .0035, 7.0)
    new = bevel_edges(bm, seam, 1, 0, long_edges)
    for face in new:
        face.material_index = GLOW
    gem_cuts(bm, rng, length, width, thick, cuts if cuts is not None else int(np.clip(length / 240, 3, 14)))
    glows = {f for f in bm.faces if f.material_index == GLOW}
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(9) and not any(f in glows for f in e.link_faces)]
    bevel_edges(bm, seam * .14, 1, 0, edges)
    return from_bm(bm, CRYSTAL, 0, keep=True)


def monolith_arc(radius, a0, a1, width, thick, seed):
    """One curved piece of a broken halo: a long gem bent around the ship's axis."""
    rng = np.random.default_rng(seed)
    n = 5
    prof = [(1, .25), (.42, 1), (-.5, .86), (-1, -.1), (-.3, -1), (.6, -.8)]
    prof = np.array(prof) * (thick / 2, width / 2)
    sections = []
    for i in range(n):
        t = i / (n - 1)
        a = a0 + (a1 - a0) * t
        s = .05 if i in (0, n - 1) else (.72 if i in (1, n - 2) else 1) * rng.uniform(.92, 1.06)
        pts = []
        for r, x in prof * s:
            rr = radius + r
            pts.append((x, math.cos(a) * rr, math.sin(a) * rr))
        sections.append(np.array(pts))
    bm = bmesh.new()
    rows = [[bm.verts.new(p) for p in s] for s in sections]
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    for a, b in zip(rows, rows[1:]):
        for j in range(6):
            k = (j + 1) % 6
            bm.faces.new((a[j], a[k], b[k], b[j]))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) == 4], quad_method='SHORT_EDGE')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    long_edges = [bm.edges.get((a[1], b[1])) for a, b in zip(rows, rows[1:])]
    new = bevel_edges(bm, width * .014, 1, 0, [e for e in long_edges if e])
    for face in new:
        face.material_index = GLOW
    glows = set(new)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(9) and not any(f in glows for f in e.link_faces)]
    bevel_edges(bm, width * .003, 1, 0, edges)
    return from_bm(bm, CRYSTAL, 0, keep=True)


def filament(a, b, hw):
    # Tapered: a thread of light, not a strut.
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    side = d.cross(Vector((0, 0, 1)))
    side = side if side.length > 1e-3 else d.cross(Vector((0, 1, 0)))
    side.normalize()
    up = side.cross(d).normalized()
    sec = [[tuple(p + side * x * w + up * y * w) for x, y in ((1, 0), (0, 1), (-1, 0), (0, -1))] for p, w in ((a, hw), (a.lerp(b, .35), hw * .55), (b, hw * .16))]
    return loft(sec, GLOW, 1)


def octa(r, stretch=1.5):
    # Luminous core.
    bm = bmesh.new()
    verts = [bm.verts.new(v) for v in ((r * stretch, 0, 0), (-r * stretch, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r), (0, 0, -r))]
    for f in ((0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2), (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5)):
        bm.faces.new([verts[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return from_bm(bm, GLOW, 0)


def vigil(size):
    """A warship that does not touch itself: split lance, floating core, broken crown, ordered wake."""
    kit = Kit('SM_Ship_Vigil', FIRST_SLOTS, 13)
    L = 7000
    # Fore lance and aft lance point at each other across the core.
    kit.add(blade(4300, 1160, 720, 3, 7, .34, glow=(0, 3, 5)), mat((-800 + 0, 0, 40)), tone=.5, uv=1.2)
    kit.add(blade(2500, 980, 620, 5, 6, .66, glow=(1, 4)), mat((-3500, -40, -30)), tone=.72, uv=1.2)
    # Asymmetric flanking blades: one long, one short, the rest of the balance comes from the crown.
    kit.add(blade(3600, 560, 300, 7, 5, .3, tip=.1, glow=(2,)), mat((-1400, 1240, 180), (.28, -.02, .05)), tone=.3)
    kit.add(blade(2300, 400, 240, 9, 5, .36, glow=(0,)), mat((-2100, -1020, -340), (-.2, .05, -.07)), tone=.8)
    kit.add(blade(1500, 280, 170, 11, 5, .4, glow=(1,)), mat((-300, 1860, 520), (.5, -.06, .1)), tone=.2)
    kit.add(octa(120, 2.4), mat((-1000, 0, 10), (.5, 0, 0)), tone=.5, uv=.6)
    # Heart: a cage of small blades holding the light, so the core has depth instead of being a lamp.
    for i in range(9):
        a, b = i * 2.399, (i - 4) * .3
        kit.add(blade(520 + 90 * (i % 3), 86, 54, 80 + i, 5, .42, glow=(0,), seam=4), mat((-1000, 0, 10), (a, b, 0)) @ mat((110, 0, 0)), tone=.3 + i * .05)
    # Crown: a tilted halo around the core, unfinished on purpose, stepping down in size.
    crown = mat((-1000, 0, 60), (.0, .24, .1))
    angles = [(-.35, .65, 620, 300), (.72, 1.5, 520, 250), (1.58, 2.2, 430, 210), (2.28, 2.75, 340, 170), (2.84, 3.15, 260, 130), (3.22, 3.4, 190, 96), (3.48, 3.58, 130, 66)]
    ends = []
    for i, (a0, a1, w, t) in enumerate(angles):
        kit.add(monolith_arc(2280, a0, a1, w, t, 20 + i), crown, tone=.2 + i * .1)
        m = (a0 + a1) / 2
        ends.append(np.array(crown) @ np.array((0, math.cos(m) * 2150, math.sin(m) * 2150, 1)))
    # Tethers of light from core to crown: all the structure this ship admits to.
    for p in ends[:4]:
        kit.add(filament((-1000, 0, 10), tuple(p[:3]), 2.4), tone=.5, uv=.3)
    # Lesser ring, a counterweight behind.
    ring_at = mat((-3000, 0, -60), (.1, -.14, 0))
    for i in range(5):
        a = -1.2 + i * .78 + .2
        kit.add(monolith_arc(1160, a, a + .56, 300 - 30 * i, 150 - 14 * i, 40 + i), ring_at, tone=.6)
    # Wake: ordered shards that shrink along a falling curve.
    for i in range(11):
        t = i / 10
        x = -3400 + 2900 * t
        z = -760 - 520 * math.sin(t * math.pi * .9) * (1 - t * .4)
        y = 260 * math.sin(t * 5)
        s = 1 - t * .72
        kit.add(blade(420 * s + 110, 92 * s + 28, 58 * s + 16, 60 + i, 5, .42, glow=(0,), seam=5), mat((x, y, z), (0, -.1, .03)), tone=.35)
    return kit


def shard(size):
    """Fast attack craft: a cleft lance with a fan of feathers on one side only."""
    kit = Kit('SM_Ship_Shard', FIRST_SLOTS, 14)
    kit.add(blade(2800, 620, 340, 31, 6, .36, glow=(0, 3)), mat((-1400, 90, 18), (0, 0, -.02)), tone=.5, uv=1.2)
    kit.add(blade(2000, 400, 250, 33, 5, .44, glow=(1, 3)), mat((-1400, -300, -60), (0, 0, .05)), tone=.75, uv=1.2)
    kit.add(octa(120, 2.4), mat((-340, -130, -14)), tone=.5, uv=.3)
    for i in range(6):
        t = i / 5
        a = .08 + t * .62
        length = 1320 - 760 * t
        x = -1420 + 300 * t
        y = 500 + 200 * t
        z = -30 + 180 * math.sin(t * 2.4)
        kit.add(blade(length, 190 - 72 * t, 92 - 34 * t, 40 + i, 5, .36, glow=(1,), seam=6), mat((x, y, z), (.18 * t, 0, a - .3)), tone=.3 + t * .3)
    for i in range(5):
        t = i / 4
        kit.add(blade(190 - 90 * t, 60 - 24 * t, 34 - 12 * t, 50 + i, 5, .4, glow=(0,), seam=3), mat((-1640 + 180 * t, -640 + 220 * t, -160 + 40 * t), (0, 0, .1)), tone=.4)
    kit.add(filament((-340, -130, -14), (-1100, 760, 40), 1.6), tone=.5, uv=.3)
    return kit


def voronoi_veil(obj, size, cell, depth, seed, spin=(.31, .7, -.64)):
    # Fracture sheets seen through the surface: position sinks along the normal and slides with
    # facet orientation, so the pattern breaks at each facet the way refraction does.
    def build(nodes, links):
        geometry = nodes.new('ShaderNodeNewGeometry')
        cross = nodes.new('ShaderNodeVectorMath')
        cross.operation = 'CROSS_PRODUCT'
        links.new(geometry.outputs['True Normal'], cross.inputs[0])
        cross.inputs[1].default_value = spin
        scale = nodes.new('ShaderNodeVectorMath')
        scale.operation = 'MULTIPLY_ADD'
        links.new(cross.outputs[0], scale.inputs[0])
        scale.inputs[1].default_value = (depth * 1.3,) * 3
        links.new(geometry.outputs['True Normal'], scale.inputs[2])
        sink = nodes.new('ShaderNodeVectorMath')
        sink.operation = 'MULTIPLY_ADD'
        links.new(geometry.outputs['True Normal'], sink.inputs[0])
        sink.inputs[1].default_value = (-depth,) * 3
        links.new(geometry.outputs['Position'], sink.inputs[2])
        add = nodes.new('ShaderNodeVectorMath')
        add.operation = 'ADD'
        links.new(sink.outputs[0], add.inputs[0])
        links.new(cross.outputs[0], add.inputs[1])
        offset = nodes.new('ShaderNodeVectorMath')
        offset.operation = 'ADD'
        links.new(add.outputs[0], offset.inputs[0])
        offset.inputs[1].default_value = (seed * 3.1, seed * 7.7, seed * 1.3)
        voronoi = nodes.new('ShaderNodeTexVoronoi')
        voronoi.feature = 'DISTANCE_TO_EDGE'
        voronoi.inputs['Scale'].default_value = 1 / cell
        links.new(offset.outputs[0], voronoi.inputs['Vector'])
        return voronoi.outputs['Distance']
    return bake(obj, size, build)[..., 0]


def crystal_detail(px=2048):
    """Tiling cleavage terraces and fine growth lines. Facets stay clean at distance."""
    rng = np.random.default_rng(5)
    y, x = np.mgrid[0:px, 0:px] / px
    height = np.zeros((px, px), np.float32)
    for kx, ky, w in ((3, 1, 1), (1, 4, .6), (5, 2, .4)):
        wave = (x * kx + y * ky + fft_noise(px, 3.2, kx + 90) * .35) % 1
        height += (np.floor(wave * 9) / 9 + np.clip(wave * 9 % 1 - .9, 0, 1)) * w
    height = blur_wrap(height.astype(np.float32), 1.0) * .4 + (fft_noise(px, 1.6, 7, 30) - .5) * .05
    png(TEXTURES / 'T_CrystalDetail_Normal.png', normal_from_height(height, .35), 16)


def first_textures(obj, name, size, cm_per_texel, cfg):
    L = cfg['length']
    maps = bake_maps(obj, size, L * .007, L * .08, cfg['spp'])
    P, N, D = maps['P'], maps['N'], maps['D']
    zone, tone, ao, edge = np.rint(maps['zone']), maps['tone'], np.clip(maps['ao'], 0, 1), maps['edge']
    threads = zone == 31
    glowing = (zone == 30) | threads
    # A few thin fracture sheets deep inside, not a web across the surface.
    cell = cfg.get('cell', 1.0)
    veil1 = np.exp(-voronoi_veil(obj, size, L * .2 * cell, L * .02, 1) / .005)
    veil2 = np.exp(-voronoi_veil(obj, size, L * .36 * cell, L * .05, 2, (-.6, .2, .77)) / .007)
    cloud = fft_noise(1024, 2.6, cfg['seed'])
    fog = sample(cloud, D[..., 0] / L * 2.2, D[..., 1] / L * 2.2)
    core = np.zeros((size, size), np.float32)
    for c in cfg['cores']:
        core = np.maximum(core, np.exp(-np.linalg.norm(P - np.array(c, np.float32), axis=2) / (L * .1)))
    # Each facet holds its own depth of colour, as cut gems do.
    facet = np.mod(np.abs(N[..., 0] * 17.1 + N[..., 1] * 31.3 + N[..., 2] * 23.7 + tone * 9), 1).astype(np.float32)
    # Soften the texel steps where one facet's value meets the next.
    facet = blur_wrap(facet, 1.4)[..., None]
    # Most facets are near black glass; only some catch the inner light. Value contrast is the crystal.
    shallow = np.array((.018, .13, .2), np.float32)
    deep = np.array((.0015, .007, .016), np.float32)
    depth = core[..., None] ** .6
    colour = deep + (shallow - deep) * np.clip(facet ** 3.2 * (.35 + depth * .8) + fog[..., None] * .03, 0, 1)
    # Broken up, so fractures read as sheets inside the stone and never close into cells.
    sheets = (veil1 * (.35 + fog * .5) + veil2 * .6 * (.85 - fog * .5)) * cfg.get('sheet', 1.0)
    sheets = sheets * smooth(.5, .72, sample(cloud, D[..., 0] / L * 7.3 + .2, D[..., 1] / L * 7.3 + .6))
    colour = colour + np.array((.2, .5, .56), np.float32) * (sheets * core * .1)[..., None]
    colour = colour * (.84 + ao[..., None] * .16)
    halo = smooth(.08, .7, edge)
    teal = np.array((.2, .95, .84), np.float32)
    white = np.array((.72, 1, .95), np.float32)
    glow = teal * (sheets * (.003 + core ** 1.5 * .1))[..., None]
    glow += teal * (core ** 2 * .1 * facet[..., 0] ** 2)[..., None]
    glow += teal * (halo * (.012 + core * .05))[..., None]
    pulse = .7 + .3 * np.sin(P[..., 0] / L * 19 + fog * 4)
    seam_colour = teal * (1 - core[..., None]) + white * core[..., None]
    glow[glowing] = (seam_colour * (pulse * (.5 - core ** 3 * .28))[..., None])[glowing]
    glow[threads] = (teal * (.05 + core ** 1.5 * .5)[..., None])[threads]
    colour[glowing] = (.06, .17, .17)
    rough = .2 + facet[..., 0] * .16 + sheets * .05
    rough = np.where(glowing, .3, rough)
    # Faint cleavage planes, long and straight. Facets stay polished.
    phase = (P[..., 0] * .8 + P[..., 2] * .6) / (L * .02)
    height = np.minimum(np.abs(np.mod(phase, 1) - .5), .04) * L * .0016 * ~glowing
    height = height.astype(np.float32)
    orm = np.dstack((ao * .8 + .2, np.clip(rough, .04, 1), np.zeros_like(rough)))
    png(TEXTURES / f'T_{name}_BaseColor.png', srgb(colour))
    png(TEXTURES / f'T_{name}_Normal.png', normal_from_height(height, cm_per_texel), 16)
    png(TEXTURES / f'T_{name}_ORM.png', orm)
    png(TEXTURES / f'T_{name}_Emissive.png', srgb(np.clip(glow, 0, 1)))


# ------------------------------------------------------------------ station

# Playable decks: clear of everything for x -700..19000. Greybox rooms reach x=18400, past the brief's 17000.
SHELL_R = 5200.0
SHELL_N = 48
DECK_END = 19000.0
MOUTH_X = (-1300.0, 1900.0)
STEP = 2 * math.pi / SHELL_N


def polar(r, a, x):
    return (x, math.cos(a) * r, math.sin(a) * r)


def shell_part():
    """Open hull skin: one quad-strip tube with a window cut for each hangar mouth, no caps, no inner surface."""
    xs = sorted(set(list(np.arange(-2400, 19801, 1100)) + list(MOUTH_X)))
    angles = [i * STEP for i in range(SHELL_N)]
    V = [polar(SHELL_R, a, x) for x in xs for a in angles]
    F = []
    for i in range(len(xs) - 1):
        mid = (xs[i] + xs[i + 1]) / 2
        for j in range(SHELL_N):
            centre = (j + .5) % SHELL_N
            if MOUTH_X[0] < mid < MOUTH_X[1] and (min(centre, SHELL_N - centre) < 1 or abs(centre - SHELL_N / 2) < 1):
                continue
            k = (j + 1) % SHELL_N
            a, b, c, d = i * SHELL_N + j, i * SHELL_N + k, (i + 1) * SHELL_N + k, (i + 1) * SHELL_N + j
            F.append((a, b, c, d))
    return Part(V, F, [HULL] * len(F), [PRIMARY] * len(F))


def in_mouth(x0, x1, a0, a1):
    # Is this polar patch over either hangar mouth? Mouth half-span is one shell facet, plus trim.
    if x1 < MOUTH_X[0] - 420 or x0 > MOUTH_X[1] + 420:
        return False
    for centre in (0.0, math.pi):
        lo, hi = (a0 - centre + math.pi) % (2 * math.pi) - math.pi, (a1 - centre + math.pi) % (2 * math.pi) - math.pi
        if min(abs(lo), abs(hi)) < STEP * 2.4 or lo * hi < 0 and abs(lo) < 1:
            return True
    return False


def polar_plate(x0, x1, a0, a1, r, t, zone=PRIMARY, slot=HULL, cut=.1, bevel=3.0, curve=2):
    """A curved armour slab on the hull, chamfered at its corners."""
    xc = min((x1 - x0) * cut, 90)
    ac = (a1 - a0) * cut
    rows = []
    for x, e in ((x0, 1), (x0 + xc, 0), (x1 - xc, 0), (x1, 1)):
        arc = np.linspace(a0 + ac * e, a1 - ac * e, curve + 1)
        section = [polar(r - 6, arc[0], x)]
        section += [polar(r + t, a, x) for a in arc]
        section += [polar(r - 6, arc[-1], x)]
        rows.append(section)
    return loft(rows, slot, zone, bevel, 1, 25)


def bay(w=300.0, h=210.0, depth=120.0, lit=True):
    """Casemate bay on +Z, long axis X: raised armoured surround around a real recess."""
    t = 40
    parts = [box((w + t * 2, t, depth), (0, h / 2 + t / 2, depth / 2), HULL, PRIMARY, 4, 10),
             box((w + t * 2, t, depth), (0, -h / 2 - t / 2, depth / 2), HULL, PRIMARY, 4, 10),
             box((t, h, depth * .9), (w / 2 + t / 2, 0, depth * .45), HULL, SECONDARY, 4, 8),
             box((t, h, depth * .9), (-w / 2 - t / 2, 0, depth * .45), HULL, SECONDARY, 4, 8),
             box((w, h, 8), (0, 0, 8), TRIM, DARK)]
    for x in np.linspace(-w * .36, w * .36, 4):
        parts.append(box((12, h, 40), (x, 0, 28), TRIM, SECONDARY))
    if lit:
        parts.append(box((w * .9, 8, 8), (0, h / 2 - 8, depth * .42), LIGHT, WARM))
        parts.append(box((w * .9, 8, 8), (0, -h / 2 + 8, depth * .42), LIGHT, AMBER))
        parts.append(box((w * .8, h * .5, 2), (0, 0, 15), LIGHT, BRIGHT))
    parts.append(box((w + t * 2, 18, 8), (0, h / 2 + t + 8, 5), TRIM, HAZARD))
    return merge(*parts)


def casemate_gun():
    return merge(box((460, 340, 120), (0, 0, 60), HULL, PRIMARY, 5, 16), turret(150, 2, 640, 20))


def emitter():
    """Shield emitter: a tall stalk ending in a ribbed reflector and a cold focus ring."""
    parts = [lathe([(0, 110), (40, 110), (70, 60), (320, 44), (340, 90), (372, 90), (384, 64)], 16, 'Z', TRIM, SECONDARY)]
    parts.append(lathe([(380, 66), (404, 210), (440, 250), (442, 236), (410, 180), (392, 60)], 28, 'Z', TRIM, METAL, cap=False))
    parts.append(lathe([(392, 46), (470, 60), (548, 36), (592, 2)], 12, 'Z', TRIM, METAL))
    parts.append(lathe([(452, 214), (456, 236), (462, 236), (466, 214)], 28, 'Z', LIGHT, COOL, cap=False))
    return merge(*parts)


def lander():
    # Parked boat. Sets the scale of the hangar deck.
    sections = [rect(s[0], s[1], s[2], 12, s[3]) for s in ((40, 60, 96, -300), (96, 40, 150, -230), (110, 36, 180, -60), (84, 40, 150, 170), (22, 46, 80, 320))]
    parts = [loft(sections, HULL, PRIMARY, 3, 1, 20)]
    for side in (-1, 1):
        parts.append(box((240, 170, 16), (-120, side * 180, 96), HULL, SECONDARY, 2))
        parts.append(moved(drive_bell(46, 80, 16, 0), mat((-290, side * 62, 112))))
        for x in (-170, 110):
            parts.append(box((22, 22, 44), (x, side * 72, 22), TRIM, METAL))
    return merge(*parts)


def hangar(kit):
    """Built on +Y, then mirrored: the opening cinematic flies into the -Y one.
    The pocket stops at y=3350, outside the playable decks."""
    x0, x1 = MOUTH_X
    xm = (x0 + x1) / 2
    half = SHELL_R * math.sin(STEP)
    outer = SHELL_R * math.cos(STEP)
    back = 3350.0
    run = outer - back
    # Pocket shell.
    kit.sym(box((x1 - x0 + 200, run + 40, 120), (xm, back + run / 2, -half - 60), HULL, SECONDARY, 5), uv=2.6, tone=.3)
    kit.sym(box((x1 - x0 + 200, run + 40, 120), (xm, back + run / 2, half + 60), HULL, SECONDARY, 5), uv=2.6, tone=.3)
    kit.sym(box((120, run + 40, half * 2 + 240), (x0 - 60, back + run / 2, 0), HULL, SECONDARY, 5), uv=2.6, tone=.3)
    kit.sym(box((120, run + 40, half * 2 + 240), (x1 + 60, back + run / 2, 0), HULL, SECONDARY, 5), uv=2.6, tone=.3)
    kit.sym(box((x1 - x0, 40, half * 2), (xm, back - 20, 0), TRIM, DARK), uv=2.6)
    # The light the camera flies into: glowing bulkhead panels behind dark frames.
    for x in np.arange(x0 + 260, x1 - 200, 520):
        light_wall(kit, x, back + 4, 40, 440, half * 1.6, 11)
    for x in np.arange(x0, x1 + 1, 260):
        kit.sym(box((40, 80, half * 2), (x, back + 40, 0), TRIM, SECONDARY, 3), uv=2.2, tone=.4)
    # Portal frames marching out to the mouth.
    for y in np.arange(back + 260, outer - 80, 300):
        kit.sym(box((64, 110, half * 2), (x0 + 34, y, 0), TRIM, SECONDARY, 4), uv=2.2, tone=.5)
        kit.sym(box((64, 110, half * 2), (x1 - 34, y, 0), TRIM, SECONDARY, 4), uv=2.2, tone=.5)
        kit.sym(box((x1 - x0, 90, 80), (xm, y, half - 44), TRIM, SECONDARY, 4), uv=2.2, tone=.5)
        kit.sym(box((x1 - x0 - 140, 24, 12), (xm, y + 60, half - 94), LIGHT, WARM), slot=LIGHT)
    # Deck: bright lane markers converge on the back wall.
    for offset in (-600, -200, 200, 600):
        for y in np.arange(back + 160, outer, 180):
            kit.sym(box((70, 34, 5), (xm + offset, y, -half + 3), LIGHT, AMBER if abs(offset) > 300 else WARM), slot=LIGHT)
    for y in np.arange(back + 100, outer, 600):
        kit.sym(box((x1 - x0 - 100, 22, 8), (xm, y, -half + 4), TRIM, HAZARD), uv=2)
    kit.sym(lander(), mat((x0 + 720, back + 1100, -half), (0, 0, -1.2)), uv=2, tone=.4)
    kit.sym(lander(), mat((x1 - 620, back + 780, -half), (0, 0, -1.9)), uv=2, tone=.6)
    # Armoured lip: stepped jaws framing the opening. Nothing passes y=5560, where the camera sits.
    lip = outer + 150
    for z, h in ((half + 120, 240), (-half - 120, 240)):
        kit.sym(box((x1 - x0 + 700, 300, h), (xm, outer + 10, z), HULL, PRIMARY, 8, 40), uv=2, tone=.42)
    for x in (x0 - 170, x1 + 170):
        kit.sym(box((340, 300, half * 2 + 240), (x, outer + 10, 0), HULL, PRIMARY, 8, 40), uv=2, tone=.42)
    kit.sym(box((x1 - x0 + 120, 40, 44), (xm, lip + 16, half + 34), TRIM, HAZARD, 3), uv=2.4)
    kit.sym(box((x1 - x0 + 120, 40, 44), (xm, lip + 16, -half - 34), TRIM, HAZARD, 3), uv=2.4)
    kit.sym(box((x1 - x0 + 60, 12, 16), (xm, lip + 36, half - 6), LIGHT, BRIGHT), slot=LIGHT)
    kit.sym(box((x1 - x0 + 60, 12, 16), (xm, lip + 36, -half + 6), LIGHT, BRIGHT), slot=LIGHT)
    for x in np.arange(x0, x1 + 1, 240):
        kit.sym(box((60, 26, 70), (x, lip + 12, half + 150), TRIM, SECONDARY, 2), uv=1.6)
    for z in (-half, -half * .33, half * .33, half):
        kit.sym(box((16, 12, 100), (x0 + 6, lip + 24, z), LIGHT, RED), slot=LIGHT)
        kit.sym(box((16, 12, 100), (x1 - 6, lip + 24, z), LIGHT, GREEN), slot=LIGHT)


def arm(kit, x, angle, length, cradles=3):
    """Docking arm: a truss with piers either side and a lit tower at the tip."""
    base = mat((x, 0, 0), (angle - math.pi / 2, 0, 0))
    r0, r1 = SHELL_R + 200, SHELL_R + 200 + length
    parts = []
    parts.append(loft([rect(s * 300, -s * 240, s * 240, 60 * s, 0) @ np.array(((0, 1, 0), (0, 0, 1), (1, 0, 0))) + np.array((0, 0, z)) for z, s in ((r0 - 400, 1.6), (r0 + 500, 1.1), (r1 * .96, .9), (r1, .6))], HULL, PRIMARY, 10, 2, 20))
    for i in range(cradles):
        z = r0 + (r1 - r0) * (i + .7) / (cradles + .3)
        for side in (-1, 1):
            parts.append(box((240, 1500, 170), (side * 0, side * 980, z), TRIM, SECONDARY, 6))
            parts.append(box((1100, 180, 120), (0, side * 1680, z), HULL, PRIMARY, 6))
            parts.append(box((1000, 14, 14), (0, side * 1778, z + 40), LIGHT, AMBER))
            parts.append(box((1000, 14, 14), (0, side * 1778, z - 40), LIGHT, AMBER))
            if (i + side) % 3:
                parts.append(moved(docked_ship(float(2100 + 500 * ((i * 7 + side) % 3))), mat((0, side * 2240, z))))
        parts.append(box((900, 900, 90), (0, 0, z), TRIM, METAL, 6))
    parts.append(lathe([(r1, 170), (r1 + 500, 100), (r1 + 540, 150), (r1 + 640, 150), (r1 + 660, 40), (r1 + 1400, 8)], 12, 'Z', TRIM, SECONDARY))
    parts.append(lathe([(r1 + 1400, 22), (r1 + 1440, 22)], 8, 'Z', LIGHT, RED))
    kit.add(merge(*parts), base, tone=float(kit.rng.uniform(.2, .8)))


def docked_ship(length=2600.0):
    # Far-read tender at a pier. Its job is to give the arm a human scale, so it stays cheap.
    w = warship_section
    L = length
    hull = Hull([(-L * .5, w(L * .1, L * .09, L * .07, 0, L * .012, L * .008)), (-L * .1, w(L * .12, L * .1, L * .08, 0, L * .012, L * .008)),
                 (L * .3, w(L * .07, L * .06, L * .05, 0, L * .008, L * .005)), (L * .5, w(L * .012, L * .018, L * .012, 0, L * .002, L * .001))])
    parts = [hull.loft(bevel=0)]
    parts.append(box((L * .22, L * .08, L * .06), (-L * .24, 0, L * .12), HULL, SECONDARY, 2))
    parts.append(lathe([(-L * .56, L * .05), (-L * .5, L * .065)], 12, 'X', TRIM, SCORCH))
    return merge(*parts)


def habitat(kit, x, spoke_phase):
    """Habitat ring: a pressurised torus with stepped section, armour shingles, and spokes."""
    R = 12000.0
    w, h = 1040.0, 720.0
    section = [(-w, -h * .5), (-w, h * .2), (-w * .8, h * .62), (-w * .44, h * .82), (w * .44, h * .82), (w * .8, h * .62), (w, h * .2), (w, -h * .5), (w * .6, -h), (-w * .6, -h)]
    n = 96
    rows = []
    for i in range(n + 1):
        a = i / n * 2 * math.pi
        rows.append([(x + dx, math.cos(a) * (R + dr), math.sin(a) * (R + dr)) for dx, dr in section])
    kit.add(loft(rows, HULL, PRIMARY, 0, 1, 25, cap=False, recalc=True), tone=.3, mode=12800)
    # Window galleries and armour shingles on the outer face.
    for i in range(n):
        a0, a1 = i / n * 2 * math.pi, (i + 1) / n * 2 * math.pi
        gap = .0024
        if i % 8 == 0:
            kit.add(polar_plate(x - w * .8, x + w * .8, a0, a1 + 2 * math.pi / n * 1, R + h * .82 - 8, 90, SECONDARY, TRIM, .06, 5), tone=.2, mode=12800, uv=.8)
            kit.add(emitter(), mat(polar(R + h * .82 + 60, a0 + .03, x), (a0 + .03 - math.pi / 2, 0, 0)), tone=.2)
        elif i % 8 == 1:
            continue
        else:
            kit.add(polar_plate(x - w * .78, x - w * .22, a0 + gap, a1 - gap, R + h * .82, 34, cut=.06, curve=1), tone=float(kit.rng.uniform(.3, .7)), mode=12800, uv=.8)
            kit.add(polar_plate(x + w * .22, x + w * .78, a0 + gap, a1 - gap, R + h * .82, 34, cut=.06, curve=1), tone=float(kit.rng.uniform(.3, .7)), mode=12800, uv=.8)
            kit.add(polar_plate(x - w * .2, x + w * .2, a0 + gap, a1 - gap, R + h * .82, 16, cut=.04, curve=1), win=1.0, tone=.5, mode=12800, uv=1)
        # Galleries on both faces of the ring; these are what light up at distance.
    for side in (-1, 1):
        rows = []
        for r in (R - h * .4, R + h * .2):
            rows.append(ring(r, x + side * (w + 8), n))
        kit.add(loft(rows, HULL, PRIMARY, cap=False, flip=side > 0), win=1.0, tone=.5, mode=12800)
    for i in range(6):
        a = spoke_phase + i * math.pi / 3
        kit.add(merge(*[beam(polar(SHELL_R - 60, a, x + dx), polar(R - h * .9, a, x + dx), 260, 150, HULL, PRIMARY, 8, (1, 0, 0), 50) for dx in (-420, 420)]), tone=.4, uv=.7)
        for r in np.arange(6400, 11000, 1300):
            kit.add(box((840, 180, 180), polar(r, a, x), TRIM, SECONDARY, 5), tone=.3, uv=.7)
        kit.add(beam(polar(SHELL_R + 120, a, x - 420), polar(R - h, a, x + 420), 60, 60, TRIM, METAL), tone=.3)
        kit.add(beam(polar(SHELL_R + 120, a, x + 420), polar(R - h, a, x - 420), 60, 60, TRIM, METAL), tone=.3)


def spine(kit):
    """Dorsal and ventral citadels run the whole length, carrying the main batteries."""
    rows = [(-5900, 700, 3200, 4300), (-4700, 1100, 4700, 6300), (-2500, 1200, 5120, 7300), (-1700, 1250, 5120, 7700), (2800, 1250, 5120, 7800), (3400, 1120, 5120, 7500),
            (9200, 1120, 5120, 7500), (9800, 1000, 5120, 7200), (18300, 1000, 5120, 7200), (20000, 900, 5120, 7000), (24600, 640, 2500, 4400), (31500, 180, 300, 1350), (32000, 60, 160, 560)]
    def section(x, hw, z0, z1):
        return [(x, -hw * 1.2, z0), (x, hw * 1.2, z0), (x, hw, z0 + (z1 - z0) * .5), (x, hw * .72, z1), (x, -hw * .72, z1), (x, -hw, z0 + (z1 - z0) * .5)]
    part = loft([section(*r) for r in rows], HULL, PRIMARY, 12, 2, 20)
    kit.add(part, tone=.45)
    kit.add(part, mat((0, 0, 0), (math.pi, 0, 0)), tone=.45)
    rng = kit.rng
    for sign in (1, -1):
        rotate = mat((0, 0, 0), (0 if sign > 0 else math.pi, 0, 0))
        # Tiers of armour down the citadel's roof.
        x = -4400.0
        while x < 22000:
            run = float(rng.choice((900, 1200, 1500)))
            z = np.interp(x + run / 2, [r[0] for r in rows], [r[3] for r in rows])
            hw = np.interp(x + run / 2, [r[0] for r in rows], [r[1] for r in rows]) * .66
            kit.add(box((run - 70, hw * 1.9, 110), (x + run / 2, 0, z + 44), HULL, PRIMARY if rng.random() < .6 else SECONDARY, 8, 24), rotate)
            x += run
        for x, bigger in ((-1300, 1), (1700, 1), (4600, 0), (7400, 0), (11000, 0), (13800, 0), (16600, 0), (21300, 1)):
            z = np.interp(x, [r[0] for r in rows], [r[3] for r in rows]) + 96
            r = 460 if bigger else 340
            kit.add(lathe([(z - 80, r * 1.3), (z + 30, r * 1.3), (z + 40, r * 1.2)], 32, 'Z', TRIM, SECONDARY, 4), mat((x, 0, 0)) @ rotate if False else rotate @ mat((x, 0, 0)))
            kit.add(turret(r, 3, r * 3.7, 24), rotate @ mat((x, 0, z + 30), (0, 0, 0 if x > 8000 else math.pi)), tone=.4)
        for x in (3000, 9500, 18300):
            z = np.interp(x, [r[0] for r in rows], [r[3] for r in rows]) + 60
            kit.add(mast(2300, 62, 5), rotate @ mat((x, 0, z)), tone=.2)
            kit.add(dish(460, 32), rotate @ mat((x + 620, 0, z + 130), (0, .5, 0)), tone=.2)
    # Citadel flanks carry window galleries and casemates.
    for sign in (1, -1):
        for x in np.arange(3700, 18600, 900):
            for side in (-1, 1):
                kit.add(box((780, 12, 460), (x + 360, side * 1110, sign * 5980), HULL, PRIMARY, 2), win=1.0, tone=.5, uv=1)


def station(size):
    """Meridian Station exterior. Long axis X; decks run inside the open shell."""
    kit = Kit('SM_Station_Hull', HUMAN_SLOTS, 21)
    rng = kit.rng
    kit.add(shell_part(), tone=.5, mode=5200, uv=.8)
    # Belts: armour shingles in rings around the shell, leaving the spine sectors to the citadels.
    bays = []
    rows = np.arange(-1900, 18800, 960)
    for i, x in enumerate(rows):
        for j in range(SHELL_N):
            a0 = j * STEP - math.pi / 2 + .003
            a1 = a0 + STEP - .006
            c = (a0 + a1) / 2
            if abs(math.cos(c)) < .22 or in_mouth(x, x + 900, a0, a1):
                continue
            pick = int(rng.integers(0, 7)) if (i + j // 2) % 3 else 2
            if pick == 0 and x > 2000:
                kit.add(polar_plate(x, x + 900, a0, a1, SHELL_R, 22, SECONDARY, TRIM, .04, 3, 1), mode=5200, uv=.8)
                bays.append((x + 450, c))
            elif pick in (1, 3):
                kit.add(polar_plate(x, x + 900, a0, a1, SHELL_R, 34, cut=.05, curve=1), mode=5200, uv=.9)
                kit.add(polar_plate(x + 150, x + 750, a0 + STEP * .14, a1 - STEP * .14, SHELL_R + 34, 28, SECONDARY if pick == 3 else PRIMARY, cut=.08, bevel=2.5, curve=1), mode=5200, uv=.9)
            elif pick == 2:
                kit.add(polar_plate(x, x + 900, a0, a1, SHELL_R, 26, cut=.04, curve=1), win=1.0, mode=5200, uv=1)
            else:
                kit.add(polar_plate(x, x + 420, a0, a1, SHELL_R, 40, cut=.05, curve=1), mode=5200, uv=.9)
                kit.add(polar_plate(x + 460, x + 900, a0, a1, SHELL_R, 52, SECONDARY if pick == 5 else PRIMARY, cut=.05, curve=1), mode=5200, uv=.9)
    for x, a in bays:
        kit.add(bay(), mat(polar(SHELL_R + 40, a, x), (a - math.pi / 2, 0, 0)), tone=.5, uv=1)
    for x in np.arange(2500, 19000, 2900):
        kit.add(lathe([(x - 90, 5180), (x - 90, 5330), (x - 50, 5400), (x + 50, 5400), (x + 90, 5330), (x + 90, 5180)], SHELL_N, 'X', TRIM, SECONDARY, cap=False, phase=-math.pi / 2), tone=.3, mode=5200)
    # Bulkhead flanges, hollow so nothing crosses the decks.
    for x0, x1, r in ((-2500, -1750, 7200), (19100, 19850, 7600)):
        kit.add(lathe([(x0, 5150), (x0, r - 140), (x0 + 150, r), (x1 - 150, r), (x1, r - 140), (x1, 5150)], SHELL_N, 'X', HULL, PRIMARY, cap=False, phase=-math.pi / 2), tone=.4, mode=7000)
        for i in range(24):
            a = i / 24 * 2 * math.pi + .02
            kit.add(polar_plate(x0 + 40, x1 - 40, a, a + .22, r, 70, SECONDARY if i % 3 == 0 else PRIMARY, cut=.1, bevel=5), tone=.4, mode=7000, win=0)
            if i % 3 == 1:
                kit.add(emitter(), mat(polar(r + 50, a + .11, (x0 + x1) / 2), (a + .11 - math.pi / 2, 0, 0)), tone=.3)
    hangar(kit)
    # Fore and aft funnels are open shells too: they begin outside the deck range and close further out.
    kit.add(lathe([(19850, 5200), (20200, 5150), (22200, 4000), (24600, 2500)], SHELL_N, 'X', HULL, PRIMARY, cap=False, phase=-math.pi / 2), tone=.4, mode=4200)
    kit.add(lathe([(-5200, 2800), (-4000, 4200), (-2500, 5200)], SHELL_N, 'X', HULL, PRIMARY, cap=False, phase=-math.pi / 2), tone=.4, mode=4200)
    # Funnel stiffeners: heavy collars and gussets, so the cones carry structure.
    for x in (20550, 22100, 23000, 23800):
        r = float(np.interp(x, [19850, 20200, 22200, 24600], [5200, 5150, 4000, 2500]))
        kit.add(lathe([(x - 70, r - 30), (x - 70, r + 70), (x - 30, r + 110), (x + 30, r + 96), (x + 70, r + 40), (x + 70, r - 70)], 36, 'X', TRIM, SECONDARY, cap=False, phase=-math.pi / 2), tone=.3, mode=4200)
    for x in (-4600, -3900):
        r = float(np.interp(x, [-5200, -4000, -2500], [2800, 4200, 5200]))
        kit.add(lathe([(x - 70, r - 70), (x - 70, r + 50), (x - 30, r + 100), (x + 30, r + 110), (x + 70, r + 70), (x + 70, r - 30)], 36, 'X', TRIM, SECONDARY, cap=False, phase=-math.pi / 2), tone=.3, mode=4200)
    # Forward lance: the fortress's one enormous gun.
    kit.add(lathe([(24600, 2500), (24900, 2300), (25000, 1500), (29500, 980), (29800, 1180), (30100, 1180), (30300, 760), (34300, 480), (34500, 640), (34900, 640), (35100, 340), (37000, 190), (37100, 300), (37450, 300), (37450, 120), (36900, 80)], SHELL_N, 'X', HULL, SECONDARY, cap=False), tone=.3, mode=1500)
    for i in range(6):
        a = i * math.pi / 3 + math.pi / 6
        kit.add(beam(polar(1420, a, 25100), polar(620, a, 34200), 150, 90, HULL, PRIMARY, 6, (1, 0, 0)), tone=.3)
        kit.add(moved(box((1800, 90, 60), (27500, 0, 0), TRIM, METAL), mat((0, 0, 0), (a, 0, 0)) @ mat((0, 0, 1320))), tone=.3)
        for x in (26000, 28000, 32000):
            kit.add(box((60, 420, 220), polar(np.interp(x, [25000, 29500, 30300, 34300], [1520, 1000, 780, 500]), a, x), TRIM, SECONDARY, 4), tone=.3)
    for x in np.arange(25400, 37000, 1200):
        r = np.interp(x, [25000, 29500, 30300, 34300, 35100, 37000], [1500, 980, 760, 480, 340, 190])
        kit.add(lathe([(x, r - 8), (x, r + 30), (x + 50, r + 30), (x + 50, r - 8)], 32, 'X', LIGHT, COOL, cap=False), slot=LIGHT)
    # Aft reactor block and drive cluster.
    kit.add(lathe([(-7000, 1900), (-6900, 2300), (-6650, 2300), (-6500, 3100), (-5400, 3100), (-5200, 2700)], SHELL_N, 'X', TRIM, SECONDARY, cap=False, phase=-math.pi / 2), tone=.3, mode=2800)
    kit.add(lathe([(-7010, 1920), (-7010, 1), ], 32, 'X', TRIM, DARK, cap=False, flip=True), tone=.3)
    for i in range(6):
        a = i * math.pi / 3
        kit.add(drive_bell(560, 800, 48, 18), mat(polar(1300, a, -6800)), tone=.3, uv=.8)
        kit.add(lathe([(-6980, 620), (-6810, 620)], 32, 'X', TRIM, METAL, cap=False), mat(polar(1300, a, 0)), tone=.3)
    spine(kit)
    habitat(kit, 6500, .22)
    habitat(kit, 13300, .22 + math.pi / 6)
    for x, a, n in ((17200, math.radians(40), 3), (17200, math.radians(140), 3), (17200, math.radians(220), 2), (17200, math.radians(320), 2),
                    (-3400, math.radians(30), 2), (-3400, math.radians(150), 2), (-3400, math.radians(210), 2), (-3400, math.radians(330), 2)):
        arm(kit, x, a, 7800 if n == 3 else 5400, n)
    for a in np.radians((20, 65, 115, 160, 200, 245, 295, 340)):
        kit.add(emitter(), mat(polar(3000, a, 23800), (a - math.pi / 2, .4, 0), 2.2), tone=.3)
    return kit


def station_cfg():
    def mark(P, N, D, colour, zone):
        for side in (-1, 1):
            stamp(P, N, colour, zone, TEXT['MERIDIAN'], 300, (300, 1440), side, (.17, .165, .15))
        band = (np.abs(P[..., 0] - 9800) < 170) & (zone == PRIMARY)
        colour[band] = ZONE_COLOURS[ACCENT]
    return {'seed': 32, 'tile_cm': 5600, 'height_scale': 3.2, 'length': 44000, 'ao': 1500, 'hazard_pitch': 180, 'soot_x': -3000,
            'window_pitch': (72, 170), 'window_size': (36, 58), 'mark': mark, 'side_only': False, 'row_skip': 3, 'impacts': 60, 'impact': (120, 520)}


def check_station(obj):
    """Fail the build if anything sits inside the deck volume."""
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    span = (co[:, 0] > -700) & (co[:, 0] < DECK_END)
    bad = span & (np.abs(co[:, 1]) < 3000) & (np.abs(co[:, 2]) < 3000)
    near = span & (np.hypot(co[:, 1], co[:, 2]) < 4400) & ~(np.abs(co[:, 1]) > 3300) & ~(np.abs(co[:, 2]) < 1000)
    camera = (np.abs(co[:, 0] - 300) < 500) & (np.abs(co[:, 2]) < 350) & (np.abs(co[:, 1]) > 5560)
    for z in (0, 200, -200, 500):
        for sy in (1, -1):
            hit, at, _, face = obj.ray_cast(Vector((300, sy * 5650, z)), Vector((0, -sy, 0)))
            print('[ray]', sy, z, hit, tuple(round(v) for v in at), face, obj.data.materials[obj.data.polygons[face].material_index].name if hit else '')
    print(f'[check] deck volume verts={int(bad.sum())} inner cylinder verts={int(near.sum())} camera-path verts={int(camera.sum())}')
    assert not bad.any() and not near.any() and not camera.any()


# ------------------------------------------------------------------ driver

BUILDERS = {'cruiser': cruiser, 'frigate': frigate, 'vigil': vigil, 'shard': shard, 'station': station}
HUMAN_CFG = {'cruiser': cruiser_textures_cfg, 'frigate': frigate_cfg, 'station': station_cfg}
FIRST_CFG = {'vigil': {'seed': 41, 'length': 7000, 'cores': [(-1000, 0, 10)]}, 'shard': {'seed': 42, 'length': 2800, 'cores': [(-340, -130, -14)], 'cell': 2.6, 'sheet': .55}}
FINAL_SIZE = {'cruiser': 4096, 'station': 4096, 'frigate': 2048, 'vigil': 2048, 'shard': 2048}


def views_for(asset, length):
    if asset == 'station':
        return [{'dir': (.2, -1, .28), 'dist': 118000, 'lens': 60}, {'dir': (-.8, -.55, .4), 'dist': 76000, 'lens': 45, 'at': (12000, 0, 0)},
                {'dir': (.9, .7, .35), 'dist': 76000, 'lens': 45, 'at': (12000, 0, 0)}, {'dir': (.06, -1, .1), 'dist': 21000, 'lens': 30, 'at': (900, 0, 0)},
                {'dir': (0, -1, 0), 'dist': 5950, 'lens': 18, 'at': (300, 300, 0)}, {'dir': (.6, -1, .35), 'dist': 15000, 'lens': 45, 'at': (10000, -4000, 2000)}]
    near = length * 1.05
    return [{'dir': (1, -.85, .42), 'dist': near * 1.9, 'lens': 80}, {'dir': (-1, -.6, .3), 'dist': near * 1.9, 'lens': 80},
            {'dir': (.12, -1, .08), 'dist': near * 2.0, 'lens': 80}, {'dir': (.02, -.1, 1), 'dist': near * 2.0, 'lens': 80},
            {'dir': (1, -1, .5), 'dist': near * .85, 'lens': 80, 'at': (length * .12, 0, length * .05)},
            {'dir': (-1, -.9, .25), 'dist': near * .55, 'lens': 80, 'at': (-length * .4, 0, 0)}]


REVIEW_VIEWS = {
    'cruiser': [{'dir': (.5, -1, .28), 'dist': 1500, 'lens': 50, 'at': (800, -400, 300)}, {'dir': (-.15, -1, .1), 'dist': 1800, 'lens': 50, 'at': (-1000, -700, 100)},
                {'dir': (.5, .3, 1), 'dist': 1600, 'lens': 50, 'at': (-1400, 0, 600)}, {'dir': (.3, -.5, -1), 'dist': 2600, 'lens': 50, 'at': (0, 0, -300)},
                {'dir': (1, -.1, .12), 'dist': 2600, 'lens': 60, 'at': (2400, 0, 0)}, {'dir': (-1, -.25, .15), 'dist': 2600, 'lens': 50, 'at': (-2800, 0, 60)}],
    'frigate': [{'dir': (.5, -1, .3), 'dist': 900, 'lens': 50, 'at': (200, -100, 150)}, {'dir': (-.5, -1, .45), 'dist': 1100, 'lens': 50, 'at': (-800, -300, 300)},
                {'dir': (.3, -.5, -1), 'dist': 1500, 'lens': 50, 'at': (-300, 0, -200)}, {'dir': (.1, .1, 1), 'dist': 1100, 'lens': 50, 'at': (-80, 0, 200)},
                {'dir': (1, -.2, .2), 'dist': 1300, 'lens': 60, 'at': (900, 0, 0)}, {'dir': (-1, -.04, .05), 'dist': 1000, 'lens': 50, 'at': (-1300, 450, 0)}],
    'vigil': [{'dir': (.4, -1, .3), 'dist': 2600, 'lens': 50, 'at': (-1000, 0, 40)}, {'dir': (1, -.4, .2), 'dist': 2600, 'lens': 50, 'at': (2800, 0, 40)},
              {'dir': (-.2, -1, .4), 'dist': 1800, 'lens': 50, 'at': (-1000, 2000, 900)}, {'dir': (.2, -1, 0), 'dist': 800, 'lens': 50, 'at': (1000, -100, 40)},
              {'dir': (0, -1, .2), 'dist': 1400, 'lens': 50, 'at': (-2000, 0, -1000)}, {'dir': (-1, .3, .2), 'dist': 4200, 'lens': 50, 'at': (-3000, 0, 0)}],
    'shard': [{'dir': (.4, -1, .4), 'dist': 1500, 'lens': 50, 'at': (0, 0, 0)}, {'dir': (1, -.3, .2), 'dist': 1200, 'lens': 50, 'at': (1200, 0, 0)},
              {'dir': (-.5, -.3, 1), 'dist': 1500, 'lens': 50, 'at': (-800, 500, 0)}, {'dir': (.2, -1, 0), 'dist': 500, 'lens': 50, 'at': (-200, -100, 0)},
              {'dir': (-1, -.2, .2), 'dist': 1600, 'lens': 50, 'at': (-1400, 0, 0)}, {'dir': (.3, .6, -1), 'dist': 1800, 'lens': 50, 'at': (0, 0, 0)}],
    'station': [{'dir': (.1, -1, .15), 'dist': 9000, 'lens': 35, 'at': (10000, -5200, 800)}, {'dir': (.8, -.5, .4), 'dist': 16000, 'lens': 40, 'at': (22000, 0, 2000)},
                {'dir': (-1, -.3, .3), 'dist': 24000, 'lens': 40, 'at': (-6000, 0, 0)}, {'dir': (.3, -1, .6), 'dist': 7000, 'lens': 35, 'at': (10000, 2000, 7000)},
                {'dir': (.15, -1, .1), 'dist': 30000, 'lens': 50, 'at': (9000, -12000, 0)}, {'dir': (.05, -1, 0), 'dist': 11000, 'lens': 35, 'at': (300, -5200, 0)}],
}


def run(asset, size, clay, write_mesh, review=False):
    started = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    kit = BUILDERS[asset](size)
    obj = kit.build(14 if asset in FIRST_CFG else 50, 5000.0 if asset == 'station' else 0.0)
    report(obj)
    if asset == 'station':
        check_station(obj)
    cm_per_texel = unwrap(obj, kit, size, 6000.0 if asset == 'station' else 2600.0)
    name = kit.name.replace('SM_Ship_', '').replace('SM_Station_', 'Station').replace('SM_', '')
    if review:
        # Art-direction close-ups on the textures already on disk: no bake, no export.
        preview_material(obj, name, 7.0 if asset in FIRST_CFG else 14.0, False)
        frames = render_views(obj, REVIEW_VIEWS[asset], asset, samples=32)
        contact(frames, 3, REVIEW / f'ships_ad_{asset}.png')
        print(f'[done] review {asset} in {time.time() - started:.0f}s')
        return
    if not clay:
        if asset in FIRST_CFG:
            first_textures(obj, name, size, cm_per_texel, dict(FIRST_CFG[asset], spp=48))
        else:
            human_textures(obj, name, size, cm_per_texel, dict(HUMAN_CFG[asset](), spp=48))
    if write_mesh:
        export(obj)
    preview_material(obj, name, 7.0 if asset in FIRST_CFG else 14.0, clay)
    frames = render_views(obj, views_for(asset, obj.dimensions.x), asset, samples=24 if clay else 48)
    contact(frames, 3, REVIEW / f'ships_{asset}.png')
    print(f'[done] {asset} in {time.time() - started:.0f}s')


def sheet():
    """Stack the per-asset review sheets into Art/Review/ships.png."""
    rows = []
    for asset in BUILDERS:
        path = REVIEW / f'ships_{asset}.png'
        if path.exists():
            image = bpy.data.images.load(str(path))
            w, h = image.size
            data = np.empty(w * h * 4, np.float32)
            image.pixels.foreach_get(data)
            rows.append(data.reshape(h, w, 4)[..., :3][::2, ::2].copy())
            bpy.data.images.remove(image)
    png(REVIEW / 'ships.png', np.vstack(rows[::-1]))


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    assets = [a for a in args if a in BUILDERS]
    if '--sheet' in args and not assets:
        sheet()
        return
    assets = assets or list(BUILDERS)
    size = int(args[args.index('--size') + 1]) if '--size' in args else 0
    clay = '--clay' in args
    write_mesh = '--no-export' not in args
    review = '--review' in args
    for text in ('FNS-2312', 'FNS-0417', 'MERIDIAN'):
        TEXT[text] = text_mask(text, 96)
    for folder in (MESHES, TEXTURES, REVIEW):
        folder.mkdir(parents=True, exist_ok=True)
    if not clay and not review:
        detail_set()
        crystal_detail()
    for asset in assets:
        run(asset, size or FINAL_SIZE[asset], clay, write_mesh, review)
    if review:
        print('PHYSIS_SHIPS_DONE')
        return
    sheet()
    print('PHYSIS_SHIPS_DONE')


if __name__ == '__main__':
    main()
