"""Generate Physis gameplay hero props: sidearm, training drone, pickups, scan targets.

Every prop is authored as a signed distance field in numpy, so bevels, grooves and
blends are exact. The field becomes a dense sculpt (surface nets), the sculpt is
decimated to the game mesh, and normal, occlusion and position are baked from one
to the other. Materials are then painted texel by texel from the true surface
position, curvature and part id, so wear follows real edges.

Run:
  flatpak run org.blender.Blender -b --python Tools/build_physis_props.py -- [props] [--q N] [--size N] [--norender] [--sheet]
    props      any of gun drone health divinity ammo conduit terminal (default all)
    --q N      voxel multiplier for fast drafts (default 1)
    --size N   texture size (default 2048)
    --sheet    no building; re-render Art/Review/props.png from what is on disk

Writes Art/Meshes/Props/SM_*.fbx, Art/Materials/Props/T_*.png, Art/Review/props.png.
Blender's own Python holds numpy; nothing here touches Unreal or the network.
"""
import math
import mmap
import os
import struct
import sys
import time
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MESHES = ROOT / 'Art/Meshes/Props'
TEXTURES = ROOT / 'Art/Materials/Props'
REVIEW = ROOT / 'Art/Review'
WORKERS = 11
F = np.float32


# ---------------------------------------------------------------- distance fields

def hyp(*a):
    return np.sqrt(sum(x * x for x in a))


def rd(a, b, r=0.):
    """Intersect two distances with a rounded edge of radius r."""
    x, y = a + r, b + r
    return np.minimum(np.maximum(x, y), 0) + hyp(np.maximum(x, 0), np.maximum(y, 0)) - r


def cd(a, b, c=0.):
    """Intersect two distances with a 45 degree chamfer of size c."""
    return np.maximum(np.maximum(a, b), (a + b + c) * .7071)


def box(p, c, h, r=0.):
    q = np.abs(p - np.array(c, F)) - (np.array(h, F) - r)
    return hyp(*(np.maximum(q[:, i], 0) for i in range(3))) + np.minimum(q.max(1), 0) - r


def sphere(p, c, r):
    return hyp(*(p - np.array(c, F)).T) - r


def ellipsoid(p, c, r):
    q = p - np.array(c, F)
    r = np.array(r, F)
    k0 = np.sqrt(((q / r) ** 2).sum(1))
    k1 = np.sqrt(((q / (r * r)) ** 2).sum(1))
    return k0 * (k0 - 1) / np.maximum(k1, 1e-6)


def cyl(p, c, axis, r, h, b=0.):
    q = p - np.array(c, F)
    u, v = [i for i in range(3) if i != axis]
    return rd(hyp(q[:, u], q[:, v]) - r, np.abs(q[:, axis]) - h, b)


def chamfer_cyl(p, c, axis, r, h, b):
    q = p - np.array(c, F)
    u, v = [i for i in range(3) if i != axis]
    return cd(hyp(q[:, u], q[:, v]) - r, np.abs(q[:, axis]) - h, b)


def torus(p, c, axis, big, small):
    q = p - np.array(c, F)
    u, v = [i for i in range(3) if i != axis]
    return hyp(hyp(q[:, u], q[:, v]) - big, q[:, axis]) - small


def capsule(p, a, b, r):
    a, b = np.array(a, F), np.array(b, F)
    e = b - a
    w = p - a
    t = np.clip((w * e).sum(1) / max(float((e * e).sum()), 1e-9), 0, 1)
    return hyp(*(w - e * t[:, None]).T) - r


def tube(p, points, r, r2=None):
    """Tapered polyline, r at the first point and r2 at the last."""
    out = None
    n = len(points) - 1
    r2 = r if r2 is None else r2
    for i in range(n):
        d = capsule(p, points[i], points[i + 1], r + (r2 - r) * (i + .5) / n)
        out = d if out is None else np.minimum(out, d)
    return out


def bezier(a, b, c, d=None, n=10):
    a, b, c = np.array(a, float), np.array(b, float), np.array(c, float)
    t = np.linspace(0, 1, n + 1)[:, None]
    if d is None:
        return (1 - t) ** 2 * a + 2 * t * (1 - t) * b + t * t * c
    d = np.array(d, float)
    return (1 - t) ** 3 * a + 3 * t * (1 - t) ** 2 * b + 3 * t * t * (1 - t) * c + t ** 3 * d


def rotate(p, axis, degrees, c=(0, 0, 0)):
    """Move sample points into a frame rotated by degrees about axis through c."""
    q = p - np.array(c, F)
    u, v = [(1, 2), (2, 0), (0, 1)][axis]
    s, k = math.sin(math.radians(degrees)), math.cos(math.radians(degrees))
    out = q.copy()
    out[:, u] = k * q[:, u] + s * q[:, v]
    out[:, v] = -s * q[:, u] + k * q[:, v]
    return out + np.array(c, F)


def smin(a, b, k):
    h = np.clip(.5 + .5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def repeat(x, pitch, lo, hi):
    """Limited repetition: distance to the nearest of the slots between lo and hi."""
    n = np.clip(np.round((x - lo) / pitch), 0, round((hi - lo) / pitch))
    return x - (lo + n * pitch)


def fillet(points, radius, steps=5):
    """Round polygon corners. A point may carry its own radius as a third value."""
    pts = [np.array(a[:2], float) for a in points]
    rad = [a[2] if len(a) > 2 else radius for a in points]
    out = []
    n = len(pts)
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        r = rad[i]
        u, v = a - b, c - b
        lu, lv = np.linalg.norm(u), np.linalg.norm(v)
        u, v = u / lu, v / lv
        angle = math.acos(np.clip(u @ v, -1, 1))
        if r <= 0 or angle > 3.1:
            out.append(b)
            continue
        t = min(r / math.tan(angle / 2), lu * .49, lv * .49)
        r = t * math.tan(angle / 2)
        centre = b + (u + v) / np.linalg.norm(u + v) * (r / math.sin(angle / 2))
        s, e = b + u * t - centre, b + v * t - centre
        turn = math.atan2(s[0] * e[1] - s[1] * e[0], s @ e)
        for k in range(steps + 1):
            w = turn * k / steps
            co, si = math.cos(w), math.sin(w)
            out.append(centre + np.array((co * s[0] - si * s[1], si * s[0] + co * s[1])))
    return np.array(out)


class Shape:
    """A closed 2D outline, stored as a distance table so lookups stay cheap."""

    def __init__(self, points, radius=0., step=.02, pad=1.5):
        v = fillet(points, radius) if radius or any(len(a) > 2 for a in points) else np.array([a[:2] for a in points], float)
        self.lo = v.min(0) - pad
        size = np.ceil((v.max(0) + pad - self.lo) / step).astype(int) + 1
        size = np.minimum(size, 1500)
        self.step = (v.max(0) + pad - self.lo) / (size - 1)
        y, x = np.meshgrid(*(self.lo[i] + np.arange(size[i]) * self.step[i] for i in (1, 0)), indexing='ij')
        d = np.full(x.shape, 1e12)
        inside = np.zeros(x.shape, bool)
        for a, c in zip(v, np.roll(v, 1, 0)):
            ex, ey = c - a
            wx, wy = x - a[0], y - a[1]
            t = np.clip((wx * ex + wy * ey) / max(ex * ex + ey * ey, 1e-12), 0, 1)
            d = np.minimum(d, (wx - ex * t) ** 2 + (wy - ey * t) ** 2)
            c1, c2, c3 = y >= a[1], y < c[1], ex * wy > ey * wx
            inside ^= (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        self.table = (np.sqrt(d) * np.where(inside, -1, 1)).astype(F)

    def __call__(self, x, y):
        u = np.clip((x - self.lo[0]) / self.step[0], 0, self.table.shape[1] - 1.001)
        v = np.clip((y - self.lo[1]) / self.step[1], 0, self.table.shape[0] - 1.001)
        i, j = u.astype(np.int32), v.astype(np.int32)
        fu, fv = u - i, v - j
        t = self.table
        near = (t[j, i] * (1 - fu) + t[j, i + 1] * fu) * (1 - fv) + (t[j + 1, i] * (1 - fu) + t[j + 1, i + 1] * fu) * fv
        # Past the edge of the table, stay a valid lower bound.
        over = hyp(x - (self.lo[0] + u * self.step[0]), y - (self.lo[1] + v * self.step[1]))
        return near + over


class Build:
    """Accumulates parts into one distance and a part id."""

    def __init__(self, p):
        self.p = p
        self.d = np.full(len(p), 1e6, F)
        self.id = np.zeros(len(p), np.int32)

    def add(self, d, part):
        m = d < self.d
        self.d = np.where(m, d, self.d)
        self.id[m] = part

    def blend(self, d, part, k):
        m = d < self.d
        self.d = smin(self.d, d, k)
        self.id[m] = part

    def cut(self, d, part=None):
        m = -d > self.d
        self.d = np.where(m, -d, self.d)
        if part is not None:
            self.id[m] = part

    def clip(self, d):
        self.d = np.maximum(self.d, d)


# ---------------------------------------------------------------- sculpt

def shared(shape, kind):
    """An array that forked workers write straight into."""
    count = int(np.prod(shape)) * np.dtype(kind).itemsize
    return np.frombuffer(mmap.mmap(-1, count), kind).reshape(shape)


def forked(tasks, work):
    """Run work(i) across worker processes. Workers never touch bpy."""
    children = []
    for k in range(WORKERS):
        pid = os.fork()
        if pid == 0:
            code = 0
            try:
                for i in range(k, tasks, WORKERS):
                    work(i)
            except BaseException:
                import traceback
                traceback.print_exc()
                code = 1
            os._exit(code)
        children.append(pid)
    for pid in children:
        if os.waitpid(pid, 0)[1]:
            raise RuntimeError('worker failed')


def sample(field, lo, hi, voxel):
    lo, hi = np.array(lo, float), np.array(hi, float)
    size = np.ceil((hi - lo) / voxel).astype(int) + 1
    size += (-size) % 12
    grid = shared(size, F)
    grid[...] = 1e3
    block = 12
    cx, cy, cz = [np.arange(0, n, block) for n in size]
    a = np.stack(np.meshgrid(cx, cy, cz, indexing='ij'), -1).reshape(-1, 3)
    centres = (lo + (a + block / 2) * voxel).astype(F)
    d = np.concatenate([field(centres[i:i + 200000]).d for i in range(0, len(centres), 200000)])
    reach = block * voxel * 1.8
    near = np.abs(d) < reach
    # Coarse sign fills the blocks that need no fine sampling.
    for (i, j, k), v in zip(a[~near], d[~near]):
        if v < 0:
            grid[i:i + block, j:j + block, k:k + block] = -1e3
    todo = a[near]
    print('  sculpt %s voxels, %d of %d blocks' % (tuple(size), len(todo), len(a)), flush=True)
    t = np.arange(block)
    offset = np.stack(np.meshgrid(t, t, t, indexing='ij'), -1).reshape(-1, 3)

    def run(batch):
        idx = (batch[:, None, :] + offset[None]).reshape(-1, 3)
        keep = (idx < size).all(1)
        idx = idx[keep]
        values = field((lo + idx * voxel).astype(F)).d
        grid[idx[:, 0], idx[:, 1], idx[:, 2]] = values

    batches = [todo[i:i + 96] for i in range(0, len(todo), 96)]
    forked(len(batches), lambda i: run(batches[i]))
    return grid, lo


def surface_nets(grid, lo, voxel):
    inside = grid < 0
    nx, ny, nz = grid.shape
    corners = inside[:-1, :-1, :-1].astype(np.uint8)
    for k, (i, j, m) in enumerate(((1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1))):
        corners = corners | (inside[i:nx - 1 + i, j:ny - 1 + j, m:nz - 1 + m].astype(np.uint8) << (k + 1))
    active = (corners != 0) & (corners != 255)
    cells = np.argwhere(active)
    index = np.full(active.shape, -1, np.int32)
    index[cells[:, 0], cells[:, 1], cells[:, 2]] = np.arange(len(cells))
    # Vertex: average of the crossings on the twelve cell edges.
    total = np.zeros((len(cells), 3), F)
    count = np.zeros(len(cells), F)
    for axis in range(3):
        for a in (0, 1):
            for b in (0, 1):
                u, v = [i for i in range(3) if i != axis]
                o0 = np.zeros(3, int)
                o0[u], o0[v] = a, b
                o1 = o0.copy()
                o1[axis] = 1
                c0 = cells + o0
                c1 = cells + o1
                f0 = grid[c0[:, 0], c0[:, 1], c0[:, 2]]
                f1 = grid[c1[:, 0], c1[:, 1], c1[:, 2]]
                cross = (f0 < 0) != (f1 < 0)
                t = np.clip(f0[cross] / (f0[cross] - f1[cross]), 0, 1)
                pos = o0[None].astype(F).repeat(cross.sum(), 0)
                pos[:, axis] = t
                total[cross] += pos
                count[cross] += 1
    verts = cells + total / count[:, None]
    verts = (verts * voxel + lo).astype(F)
    quads = []
    for axis in range(3):
        u, v = [i for i in range(3) if i != axis]
        s = [1, 1, 1]
        s[axis] = 0
        e0 = inside[tuple(slice(None, -1) if i != axis else slice(None) for i in range(3))]
        lo_side = np.take(inside, range(1, inside.shape[axis]), axis)
        hi_side = np.take(inside, range(0, inside.shape[axis] - 1), axis)
        del e0
        edge = np.argwhere(lo_side != hi_side)
        edge = edge[(edge[:, u] > 0) & (edge[:, v] > 0) & (edge[:, u] < grid.shape[u] - 1) & (edge[:, v] < grid.shape[v] - 1)]
        flip = hi_side[edge[:, 0], edge[:, 1], edge[:, 2]]
        du, dv = np.zeros(3, int), np.zeros(3, int)
        du[u], dv[v] = 1, 1
        c = [edge, edge - dv, edge - du - dv, edge - du]
        ids = [index[a[:, 0], a[:, 1], a[:, 2]] for a in c]
        q = np.stack(ids, 1)
        # Winding: the sign of axis order and of which side is solid.
        if axis == 1:
            q[~flip] = q[~flip][:, ::-1]
        else:
            q[flip] = q[flip][:, ::-1]
        quads.append(q[(q >= 0).all(1)])
    return verts, np.concatenate(quads)


def mesh_from(name, verts, quads, material):
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(verts))
    mesh.vertices.foreach_set('co', verts.ravel())
    mesh.loops.add(quads.size)
    mesh.loops.foreach_set('vertex_index', quads.ravel().astype(np.int32))
    mesh.polygons.add(len(quads))
    mesh.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4, dtype=np.int32))
    mesh.update(calc_edges=True)
    mesh.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
    mesh.materials.append(material)
    item = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(item)
    return item


def only(item):
    bpy.ops.object.select_all(action='DESELECT')
    item.select_set(True)
    bpy.context.view_layer.objects.active = item


def decimate(item, target):
    only(item)
    tris = len(item.data.polygons) * 2
    if tris > target:
        mod = item.modifiers.new('d', 'DECIMATE')
        mod.ratio = target / tris
        bpy.ops.object.modifier_apply(modifier=mod.name)


def tidy(item, sampler, voxel):
    """Clear decimation slivers on flat plates, then seat the vertices on the surface."""
    only(item)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_degenerate(threshold=voxel * .02)
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.beautify_fill(angle_limit=math.radians(4))
    bpy.ops.object.mode_set(mode='OBJECT')

    def seat():
        verts = np.empty(len(item.data.vertices) * 3, F)
        item.data.vertices.foreach_get('co', verts)
        verts = verts.reshape(-1, 3)
        item.data.vertices.foreach_set('co', project(sampler, verts, voxel).ravel())
        item.data.update()
        return verts

    span = seat()
    # Long triangles can bridge a groove. Split them and let the pieces settle.
    longest = float(np.max(span.max(0) - span.min(0))) * .07
    for _ in range(3):
        mesh = bmesh.new()
        mesh.from_mesh(item.data)
        long_edges = [e for e in mesh.edges if e.calc_length() > longest]
        if not long_edges:
            mesh.free()
            break
        bmesh.ops.subdivide_edges(mesh, edges=long_edges, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(mesh, faces=mesh.faces[:])
        mesh.to_mesh(item.data)
        mesh.free()
        seat()


# ---------------------------------------------------------------- bake

def target_image(name, size, alpha=False):
    image = bpy.data.images.new(name, size, size, alpha=alpha, float_buffer=True)
    image.colorspace_settings.name = 'Non-Color'
    return image


def repair(results, covered, lo, extent, samplers, voxel):
    """Needle triangles rasterise with wild barycentrics. Rebuild those texels from their neighbours."""
    pos = results['pos'][..., :3] * extent + lo
    index = np.nonzero(covered)
    d = np.minimum.reduce([np.abs(s(pos[index].astype(F))) for _, s in samplers])
    off = np.zeros(covered.shape, bool)
    off[index] = d > voxel * 16
    shift = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
    span = np.median(hyp(*(pos - np.roll(pos, 1, 1))[index].T))
    close = np.zeros(covered.shape, np.int8)
    for a, b in shift:
        gap = pos - np.roll(pos, (a, b), (0, 1))
        close += ((hyp(gap[..., 0], gap[..., 1], gap[..., 2]) < span * 9) & np.roll(covered, (a, b), (0, 1))).astype(np.int8)
    # Needles draw whole lines of wrong positions, so ask a wider neighbourhood.
    stack = [np.where(np.roll(covered, (a, b), (0, 1))[..., None], np.roll(pos, (a, b), (0, 1)), pos)
             for a in (-2, 0, 2) for b in (-2, 0, 2)]
    middle = np.median(np.stack(stack), axis=0)
    del stack
    gap = pos - middle
    off |= covered & (hyp(gap[..., 0], gap[..., 1], gap[..., 2]) > span * 7)
    bad = covered & (off | (close < 2))
    print('  repaired texels', int(bad.sum()), 'of', int(covered.sum()), flush=True)
    good = covered & ~bad
    channels = [results['pos'][..., :3], results['nor'][..., :3], results['tan'][..., :3], results['shell'][..., :1]]
    for _ in range(24):
        todo = covered & ~good
        if not todo.any():
            break
        weight = np.zeros(covered.shape, F)
        totals = [np.zeros(c.shape, F) for c in channels]
        for a, b in shift:
            near = np.roll(good, (a, b), (0, 1)).astype(F)
            weight += near
            for total, c in zip(totals, channels):
                total += np.roll(c, (a, b), (0, 1)) * near[..., None]
        fill = todo & (weight > 0)
        for total, c in zip(totals, channels):
            c[fill] = total[fill] / weight[fill][:, None]
        good = good | fill
    results['shell'][..., 0] = np.round(results['shell'][..., 0])


def bake_own(low, tag, size, lo, extent):
    """Bake one data channel of the mesh to itself, no projection involved."""
    image = target_image('own_' + tag, size, True)
    for slot, mat in enumerate(low.data.materials):
        tree = mat.node_tree
        tree.nodes.clear()
        out = tree.nodes.new('ShaderNodeOutputMaterial')
        emit = tree.nodes.new('ShaderNodeEmission')
        tree.links.new(emit.outputs[0], out.inputs['Surface'])
        if tag == 'shell':
            emit.inputs['Color'].default_value = (slot, 1, 0, 1)
        else:
            geo = tree.nodes.new('ShaderNodeNewGeometry')
            if tag == 'pos':
                sub = tree.nodes.new('ShaderNodeVectorMath')
                sub.operation = 'SUBTRACT'
                sub.inputs[1].default_value = tuple(lo)
                div = tree.nodes.new('ShaderNodeVectorMath')
                div.operation = 'DIVIDE'
                div.inputs[1].default_value = tuple(extent)
                tree.links.new(geo.outputs['Position'], sub.inputs[0])
                tree.links.new(sub.outputs[0], div.inputs[0])
                tree.links.new(div.outputs[0], emit.inputs['Color'])
            else:
                source = geo.outputs['Normal']
                if tag == 'tan':
                    node = tree.nodes.new('ShaderNodeTangent')
                    node.direction_type = 'UV_MAP'
                    node.uv_map = low.data.uv_layers.active.name
                    source = node.outputs[0]
                mul = tree.nodes.new('ShaderNodeVectorMath')
                mul.operation = 'SCALE'
                mul.inputs['Scale'].default_value = .5
                add = tree.nodes.new('ShaderNodeVectorMath')
                add.operation = 'ADD'
                add.inputs[1].default_value = (.5, .5, .5)
                tree.links.new(source, mul.inputs[0])
                tree.links.new(mul.outputs[0], add.inputs[0])
                tree.links.new(add.outputs[0], emit.inputs['Color'])
        node = tree.nodes.new('ShaderNodeTexImage')
        node.name = 'Bake'
        node.image = image
        node.select = True
        tree.nodes.active = node
    scene = bpy.context.scene
    scene.cycles.samples = 1
    only(low)
    scene.render.bake.margin = 8
    scene.render.bake.margin_type = 'ADJACENT_FACES'
    bpy.ops.object.bake(type='EMIT', use_selected_to_active=False, margin=8, use_clear=True)
    out = np.empty(size * size * 4, F)
    image.pixels.foreach_get(out)
    return out.reshape(size, size, 4)[::-1].copy()


def write_png(path, data, bits=8):
    """Write an RGB array in 0..1 directly, bypassing colour management."""
    h, w = data.shape[:2]
    data = np.clip(data, 0, 1)
    if bits == 16:
        raw = (data * 65535 + .5).astype('>u2')
    else:
        raw = (data * 255 + .5).astype(np.uint8)
    # Sub filter shrinks these files a lot.
    row = raw.reshape(h, -1).tobytes()
    stride = raw.reshape(h, -1).shape[1] * raw.dtype.itemsize
    bytes_ = np.frombuffer(row, np.uint8).reshape(h, stride)
    bpp = 3 * raw.dtype.itemsize
    sub = bytes_.copy()
    sub[:, bpp:] = bytes_[:, bpp:] - bytes_[:, :-bpp]
    filtered = np.concatenate((np.ones((h, 1), np.uint8), sub), 1).tobytes()

    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body) & 0xffffffff)

    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, bits, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(filtered, 6)) + chunk(b'IEND', b''))


# ---------------------------------------------------------------- paint helpers

RNG = np.random.default_rng(1977)
LATTICE = RNG.random((64, 64, 64)).astype(F)


def noise(p):
    i = np.floor(p).astype(np.int32)
    f = p - i
    f = f * f * (3 - 2 * f)
    i &= 63
    j = (i + 1) & 63
    L = LATTICE
    fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
    a = L[i[:, 0], i[:, 1], i[:, 2]] * (1 - fx) + L[j[:, 0], i[:, 1], i[:, 2]] * fx
    b = L[i[:, 0], j[:, 1], i[:, 2]] * (1 - fx) + L[j[:, 0], j[:, 1], i[:, 2]] * fx
    c = L[i[:, 0], i[:, 1], j[:, 2]] * (1 - fx) + L[j[:, 0], i[:, 1], j[:, 2]] * fx
    d = L[i[:, 0], j[:, 1], j[:, 2]] * (1 - fx) + L[j[:, 0], j[:, 1], j[:, 2]] * fx
    return ((a * (1 - fy) + b * fy) * (1 - fz) + (c * (1 - fy) + d * fy) * fz)


def fbm(p, octaves=5, gain=.5):
    total, amp, norm = 0, 1, 0
    q = p.astype(F).copy()
    for n in range(octaves):
        total = total + noise(q) * amp
        norm += amp
        amp *= gain
        q = q * 2.03 + 17.3
    return total / norm


def ramp(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def srgb(c):
    return np.array(c, F)


def to_linear(c):
    return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)


class Trilinear:
    def __init__(self, grid, lo, voxel):
        self.g, self.lo, self.v = grid, np.array(lo, F), voxel
        self.top = np.array(grid.shape, np.int32) - 2

    def __call__(self, p):
        q = (p - self.lo) / self.v
        i = np.clip(np.floor(q).astype(np.int32), 0, self.top)
        f = np.clip(q - i, 0, 1)
        g = self.g
        x, y, z = i[:, 0], i[:, 1], i[:, 2]
        fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
        a = g[x, y, z] * (1 - fx) + g[x + 1, y, z] * fx
        b = g[x, y + 1, z] * (1 - fx) + g[x + 1, y + 1, z] * fx
        c = g[x, y, z + 1] * (1 - fx) + g[x + 1, y, z + 1] * fx
        d = g[x, y + 1, z + 1] * (1 - fx) + g[x + 1, y + 1, z + 1] * fx
        return (a * (1 - fy) + b * fy) * (1 - fz) + (c * (1 - fy) + d * fy) * fz


def gradient(sampler, p, step):
    g = np.zeros_like(p)
    for axis in range(3):
        q = p.copy()
        q[:, axis] += step
        high = sampler(q)
        q[:, axis] -= 2 * step
        g[:, axis] = high - sampler(q)
    return g / np.maximum(hyp(*g.T), 1e-6)[:, None]


def project(sampler, p, voxel):
    """Walk points onto the zero surface of the field."""
    p = p.copy()
    limit = voxel * 6
    for _ in range(5):
        d = np.clip(sampler(p), -limit, limit)
        p -= gradient(sampler, p, voxel)  * d[:, None] * .9
    return p


def field_occlusion(sampler, p, n, reach):
    """Hemisphere occlusion marched through the field along five directions."""
    t = np.cross(n, np.where(np.abs(n[:, 2:3]) < .9, (0, 0, 1), (1, 0, 0)).astype(F))
    t /= np.maximum(hyp(*t.T), 1e-5)[:, None]
    u = np.cross(n, t)
    rays = [n] + [(n + a * .85)  / 1.312 for a in (t, -t, u, -u)]
    total = np.zeros(len(p), F)
    for ray in rays:
        hit = np.zeros(len(p), F)
        for h in (.08, .2, .45, 1):
            step = reach * h
            hit = np.maximum(hit, np.clip(1 - sampler(p + ray * step) / (step * .8), 0, 1) * (1.15 - h * .75))
        total += hit
    return np.clip(1 - total / len(rays) * 1.05, 0, 1)


def curvature(sampler, p, step):
    """Mean curvature estimate: positive on convex edges, negative in creases."""
    total = sampler(p) * -6
    for axis in range(3):
        for sign in (-1, 1):
            q = p.copy()
            q[:, axis] += sign * step
            total = total + sampler(q)
    return total / step


# Block-letter glyphs on a 4x6 cell, as strokes.
GLYPHS = {
    'A': ['00 04 26 44 40', '02 42'], 'B': ['00 06 36 44 33 03', '33 42 41 30 00'], 'C': ['46 16 05 01 10 40'],
    'D': ['00 06 26 44 42 20 00'], 'E': ['46 06 00 40', '03 33'], 'F': ['46 06 00', '03 33'], 'G': ['46 16 05 01 10 40 43 23'],
    'H': ['00 06', '40 46', '03 43'], 'I': ['10 30', '16 36', '20 26'], 'J': ['46 41 30 10 01'], 'K': ['00 06', '46 03 40'],
    'L': ['06 00 40'], 'M': ['00 06 23 46 40'], 'N': ['00 06 40 46'], 'O': ['10 01 05 16 36 45 41 30 10'],
    'P': ['00 06 36 45 44 33 03'], 'Q': ['10 01 05 16 36 45 41 30 10', '22 40'], 'R': ['00 06 36 45 44 33 03', '23 40'],
    'S': ['46 16 05 04 13 33 42 41 30 00'], 'T': ['06 46', '20 26'], 'U': ['06 01 10 30 41 46'], 'V': ['06 20 46'],
    'W': ['06 10 23 30 46'], 'X': ['00 46', '06 40'], 'Y': ['06 23 46', '23 20'], 'Z': ['06 46 00 40'],
    '0': ['10 01 05 16 36 45 41 30 10', '11 35'], '1': ['14 26 20', '10 30'], '2': ['05 16 36 45 44 00 40'],
    '3': ['05 16 36 45 44 33 42 41 30 10 01', '13 33'], '4': ['30 36 02 42'], '5': ['46 06 03 33 42 41 30 00'],
    '6': ['45 36 16 05 01 10 30 41 42 33 03'], '7': ['06 46 20'], '8': ['13 04 05 16 36 45 44 33 13 02 01 10 30 41 42 33'],
    '9': ['01 10 30 41 45 36 16 05 04 13 43'], '-': ['13 33'], '.': ['20 21'], '/': ['00 46'], ' ': [],
}


def text_plane(p, normal_mask, text, origin, u, v, height, weight=.09):
    """Distance-like mask for block text on a plane; u is reading direction, v is up."""
    origin, u, v = np.array(origin, F), np.array(u, F), np.array(v, F)
    q = p - origin
    x = (q @ u) / height * 6
    y = (q @ v) / height * 6
    out = np.zeros(len(p), F)
    live = normal_mask & (y > -1) & (y < 7) & (x > -1) & (x < 6.4 * len(text))
    if not live.any():
        return out
    px, py = x[live], y[live]
    best = np.full(len(px), 1e6, F)
    for index, char in enumerate(text.upper()):
        ox = index * 5.4
        near = np.abs(px - ox - 2) < 4
        if not near.any():
            continue
        for stroke in GLYPHS.get(char, []):
            pts = [(int(s[0]) + ox, int(s[1])) for s in stroke.split()]
            for a, b in zip(pts, pts[1:]):
                ex, ey = b[0] - a[0], b[1] - a[1]
                wx, wy = px - a[0], py - a[1]
                t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
                best = np.minimum(best, hyp(wx - ex * t, wy - ey * t))
    out[live] = 1 - ramp(best * height / 6, height * weight * .8, height * weight * 1.15)
    return out


GOLD_DEEP, GOLD, GOLD_HOT = np.array((.95, .36, .03), F), np.array((1, .62, .13), F), np.array((1, .82, .48), F)


def worley(q):
    """Distance to the nearest two feature points, and a random tone per cell."""
    f1, f2, tone = np.empty(len(q), F), np.empty(len(q), F), np.empty(len(q), F)
    offsets = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)], np.int32)
    for start in range(0, len(q), 150000):
        c = q[start:start + 150000]
        base = np.floor(c).astype(np.int32)
        best, next_, pick = np.full(len(c), 9., F), np.full(len(c), 9., F), np.zeros(len(c), F)
        for o in offsets:
            cell = base + o
            i, j, k = cell[:, 0] & 63, cell[:, 1] & 63, cell[:, 2] & 63
            jitter = np.stack((LATTICE[i, j, k], LATTICE[j, k, i], LATTICE[k, i, j]), 1)
            d = hyp(*(cell + jitter - c).T)
            closer = d < best
            next_ = np.where(closer, best, np.minimum(next_, d))
            pick = np.where(closer, LATTICE[k, j, i], pick)
            best = np.minimum(best, d)
        f1[start:start + 150000], f2[start:start + 150000], tone[start:start + 150000] = best, next_, pick
    return f1, f2, tone


def crystal_light(a, m, q, core):
    """Light held inside a solid: facets of unequal depth, a hot heart, planar fractures."""
    f1, f2, tone = worley(q)
    crack = ramp(f2 - f1, .08, .01) * ramp(fbm(q * .55 + 7, 2), .46, .62)
    a.glow[m] = (GOLD_DEEP * (.14 + .46 * core)[:, None] * (.55 + .75 * tone)[:, None]
                 + GOLD * (core * core * (.2 + .34 * tone))[:, None]
                 + GOLD_HOT * (crack * (.18 + .42 * core) + core ** 5 * .22)[:, None])
    a.base[m] = np.array((.24, .1, .018), F) * (.6 + .6 * tone)[:, None]
    a.rough[m] = np.clip(.06 + crack * .3, 0, 1)
    a.height[m] -= crack * .005 * a.scale


class Paint:
    """Layers painted over the atlas. All arrays are per covered texel."""

    def __init__(self, p, n, ao, curve, ids, palette, scale):
        self.p, self.n, self.ao, self.curve, self.ids, self.palette = p, n, ao, curve, ids, palette
        self.scale = scale
        count = len(p)
        self.base = np.zeros((count, 3), F)
        self.rough = np.zeros(count, F)
        self.metal = np.zeros(count, F)
        self.glow = np.zeros((count, 3), F)
        self.height = np.zeros(count, F)
        self.wear = np.zeros(count, F)
        q = p / scale
        self.large = fbm(q * .35 + 3, 5)
        self.medium = fbm(q * 1.7 + 11, 5)
        self.fine = fbm(q * 9 + 5, 4)
        self.finest = fbm(q * 40 + 9, 3)

    def layer(self, mask, colour, rough=None, metal=None):
        """Paint over everything where mask is 1."""
        m = mask[:, None]
        self.base = self.base * (1 - m) + np.array(colour, F) * m
        if rough is not None:
            self.rough = self.rough * (1 - mask) + rough * mask
        if metal is not None:
            self.metal = self.metal * (1 - mask) + metal * mask

    def materials(self):
        for part, look in self.palette.items():
            m = self.ids == part
            if not m.any():
                continue
            self.apply(m, look)

    def apply(self, m, look):
        base = np.array(look['base'], F)
        q = self.p[m] / self.scale
        tone = (self.large[m] - .5) * look.get('tone', .18) + (self.medium[m] - .5) * look.get('tone', .18) * .7
        rough = look['rough'] + (self.medium[m] - .5) * look.get('rough_var', .14) + (self.fine[m] - .5) * .06
        finish = look.get('finish', 'smooth')
        height = np.zeros(m.sum(), F)
        if finish == 'brushed':
            along = np.array(look.get('along', (1, 0, 0)), F)
            axis = q * 90
            axis -= (axis @ along)[:, None] * along * .985
            streak = fbm(axis, 2)
            rough = rough + (streak - .5) * .22
            tone = tone + (streak - .5) * .08
            height = (streak - .5) * .004
        elif finish == 'cast':
            height = (self.fine[m] - .5) * .008 + (self.finest[m] - .5) * .006
            rough = rough + (self.finest[m] - .5) * .12
        elif finish == 'stipple':
            cell = np.abs(noise(q * 34) - .5) * 2
            height = cell * .022 + (self.finest[m] - .5) * .006
            rough = rough + (cell - .5) * .16
        elif finish == 'ceramic':
            height = (self.fine[m] - .5) * .0022
        elif finish == 'organic':
            height = (self.fine[m] - .5) * .01 + (self.finest[m] - .5) * .004
        self.base[m] = np.clip(base[None] * (1 + tone)[:, None], 0, 1)
        self.rough[m] = np.clip(rough, .05, 1)
        self.metal[m] = look.get('metal', 0)
        self.height[m] = height * self.scale
        if 'glow' in look:
            self.glow[m] = np.array(look['glow'], F)
        # Chips first bite the exposed edges, then the base beneath shows through.
        chip = look.get('chip')
        if chip:
            edge = ramp(self.curve[m], look.get('edge_a', .3), look.get('edge_b', .9))
            scatter = ramp(self.medium[m] + (self.fine[m] - .5) * .55 + (self.finest[m] - .5) * .12, .54, .74)
            mark = np.clip(edge * scatter * 1.3, 0, 1) * look.get('chip_amount', 1) * .8
            mark = ramp(mark, .22, .7)
            # A few stand-alone scuffs away from edges.
            scuff = ramp(self.fine[m] * .6 + self.medium[m] * .4 + self.large[m] * .25, .88, .96) * .7
            mark = np.maximum(mark, scuff * look.get('scuff', .5))
            c = np.array(chip['base'], F)
            self.base[m] = self.base[m] * (1 - mark[:, None]) + c * mark[:, None] * (.85 + self.fine[m][:, None] * .3)
            self.rough[m] = self.rough[m] * (1 - mark) + chip['rough'] * mark
            self.metal[m] = self.metal[m] * (1 - mark) + chip['metal'] * mark
            self.height[m] -= mark * .006 * self.scale
            self.wear[m] = mark

    def grime(self, amount=1., colour=(.075, .062, .05)):
        crease = ramp(-self.curve, .06, .55)
        hollow = 1 - self.ao
        dirt = np.clip(crease * .75 + ramp(hollow, .08, .75) * .7, 0, 1) * ramp(self.medium + self.fine * .4, .42, .86)
        dirt = dirt * amount
        emissive = (self.glow.sum(1) > 0)
        dirt[emissive] = 0
        self.base = self.base * (1 - dirt[:, None] * .78) + np.array(colour, F) * dirt[:, None] * .78
        self.rough = np.clip(self.rough + dirt * .22, 0, 1)
        # Slight surface occlusion, kept subtle so lighting still owns the shadows.
        self.base *= (.72 + .28 * self.ao)[:, None]
        dust = ramp(self.n[:, 2], .35, .95) * ramp(self.large + self.medium * .35, .62, 1.05) * .14 * amount
        dust[emissive] = 0
        self.base = self.base * (1 - dust[:, None]) + np.array((.42, .4, .37), F) * dust[:, None]
        self.rough = np.clip(self.rough + dust * .2, 0, 1)

    def edge_light(self, amount=.1):
        """Very slight brightening on convex edges, as handled surfaces polish."""
        edge = ramp(self.curve, .05, .35) * (self.glow.sum(1) == 0)
        self.base = np.clip(self.base * (1 + edge[:, None] * amount), 0, 1)
        self.rough = np.clip(self.rough - edge * .08, .04, 1)

    def scratches(self, count=70, seed=3, strength=.5):
        """Long thin scratches as a stretched noise ridge."""
        rng = np.random.default_rng(seed)
        q = self.p / self.scale
        for _ in range(3):
            axis = rng.normal(size=3)
            axis /= np.linalg.norm(axis)
            k = q * 26
            k = k - (k @ axis.astype(F))[:, None] * axis.astype(F) * .97
            ridge = 1 - np.abs(noise(k + rng.uniform(0, 50, 3).astype(F)) - .5) * 2
            mark = ramp(ridge, .992, .999) * ramp(self.large, .42, .6) * strength
            self.base = self.base * (1 + mark[:, None] * .35)
            self.rough = np.clip(self.rough * (1 - mark) + .62 * mark, 0, 1)


# ---------------------------------------------------------------- prop registry

PROPS = {}


def prop(key, name, short, body, glow, bounds, voxel, tris, look, paint, scale=1., grime=1., ao=2., curve=.06, views=(), sharp=52, glow_uv=1., final=1., cap=9.):
    PROPS[key] = dict(name=name, short=short, body=body, glow=glow, bounds=bounds, voxel=voxel, tris=tris, look=look, paint=paint,
                      scale=scale, grime=grime, ao=ao, curve=curve, views=views, sharp=sharp, glow_uv=glow_uv, final=final, cap=cap)


def polar(u, v, count, phase=0.):
    """Fold the plane into one wedge of count around the origin; first result is radial."""
    r = hyp(u, v)
    a = np.arctan2(v, u) + phase
    w = 2 * math.pi / count
    a = (a + w / 2) % w - w / 2
    return r * np.cos(a), r * np.sin(a)


def lathe(shape, p, c=(0, 0, 0), axis=2):
    q = p - np.array(c, F)
    u, v = [i for i in range(3) if i != axis]
    return shape(hyp(q[:, u], q[:, v]), q[:, axis])


def once(store, build):
    if not store:
        store.update(build())
    return store


# ---------------------------------------------------------------- sidearm

GUN_X = 1.4
GUN_BODY, GUN_FRAME, GUN_GRIP, GUN_METAL, GUN_GOLD, GUN_INLAY, GUN_CORE = 1, 2, 3, 4, 5, 6, 7
GUN = {}


def gun_shapes():
    return once(GUN, lambda: dict(
        slide=Shape([(-5.0, 4.66), (-5.75, 6.55, .3), (-4.4, 7.72, .4), (5, 8.1), (12.4, 7.72, 3.5), (15.4, 6.5, .5), (15.55, 5.0, .25), (15, 4.66)], step=.015),
        frame=Shape([(-5.1, 4.56), (16.75, 4.56), (16.35, 3.95, .22), (12.0, 2.86, 1.8), (7.6, 2.72, .6), (2.2, 2.6, .35), (1.3, 2.1, .5), (-.9, -7.1, .4),
                     (-6.4, -6.7, .4), (-3.75, 2.6, 1.7), (-5.55, 3.5, .3)], step=.015),
        outer=Shape([(1.5, 2.9), (7.6, 2.9), (7.85, 2.0, .45), (6.7, -.55, .9), (2.0, -.9, 1.0), (.5, -.1), (.4, 1.6)], step=.015),
        hole=Shape([(2.5, 2.42, .3), (6.9, 2.42, .35), (5.95, .02, .6), (2.3, -.12, .7), (1.8, 1.0, .4)], step=.015),
        trigger=Shape([(3.65, 2.7), (4.35, 2.7), (4.2, 1.7, .4), (4.75, .72, .3), (4.42, .55, .15), (3.62, 1.45, .35)], step=.015),
        panel=Shape([(-3.4, 1.45), (.35, 1.45), (-1.35, -6.2), (-5.6, -5.95)], .55, step=.015),
        mag=Shape([(-1.0, -6.8), (-6.5, -6.35), (-6.78, -7.5, .25), (-.85, -8.0, .25)], step=.015),
        window=Shape([(3.0, 6.15), (4.3, 7.0), (11.3, 6.95), (12.9, 6.15), (11.7, 5.3), (4.9, 5.25)], .12, step=.015),
        bolt=Shape([(2.6, 6.28), (.95, 5.92), (1.2, 6.28), (-2.3, 4.98), (-.15, 5.72), (-.4, 5.36), (2.6, 6.02)], step=.012),
        facet=Shape([(-1.2, 4.28), (15.0, 4.28), (14.2, 3.75), (2.6, 3.25), (.7, 3.25)], .15, step=.015),
        lever=Shape([(-2.6, 4.5), (2.6, 4.5), (2.95, 4.15), (2.5, 3.75), (-.2, 3.95), (-2.5, 4.1)], .1, step=.015)))


def gun_core(p):
    q = p - np.array((GUN_X, 0, 0), F)
    b = Build(p)
    y, z = q[:, 1], q[:, 2] - 6.15
    x = q[:, 0]
    a = np.arctan2(z, y)
    radius = 1.08 + .05 * np.cos(3 * a + 2.1 * x)
    b.add(rd((hyp(y, z) - radius) * .72, np.abs(x - 7.6) - 5.3, .05), GUN_CORE)
    return b


def gun_body(p):
    g = gun_shapes()
    q = p - np.array((GUN_X, 0, 0), F)
    x, y, z = q[:, 0], q[:, 1], q[:, 2]
    ay = np.abs(y)
    m = np.stack((x, ay, z), 1)
    b = Build(p)

    # Slide: hexagonal section, flanks hollowed with a hard shoulder.
    d = rd(g['slide'](x, z), ay - 1.55, .13)
    d = rd(d, (ay - 1.55) * .74 + (z - 6.95) * .67, .12)
    hollow = ellipsoid(m, (6.4, 5.32, 6.1), (10.2, 3.98, 1.72))
    b.add(smax(d, -hollow, .05), GUN_BODY)
    # Graphite insert carries the core window; a gold pinstripe outlines it.
    w = g['window'](x, z)
    b.cut(np.maximum(w - .52, 1.2 - ay), GUN_METAL)
    b.cut(np.maximum(np.abs(w - .62) - .035, 1.3 - ay), GUN_GOLD)
    b.cut(rd(w - np.maximum(ay - 1.1, 0) * .8, .55 - ay, .02), GUN_METAL)
    # Rear grip serrations, slanted and V cut.
    s = np.abs(repeat(x + (z - 6) * .34, .46, -5.2, -2.4))
    b.cut(np.maximum.reduce((s - .07 - np.maximum(ay - 1.36, 0) * .7, 1.36 - ay, z - 7.2, 4.95 - z)), GUN_METAL)
    # Forward serrations, finer than the rear set, so the slide has a second scale of form.
    s = np.abs(repeat(x + (z - 6) * .34, .3, 12.3, 14.1))
    b.cut(np.maximum.reduce((s - .05 - np.maximum(ay - 1.4, 0) * .7, 1.4 - ay, z - 7.0, 5.1 - z)), GUN_METAL)
    # Top vents reach the core.
    s = repeat(x, 2.55, 3.2, 10.85)
    b.cut(np.maximum(rd(np.abs(s) - .98, ay - .3 - np.maximum(z - 7.75, 0) * .7, .12), 6.85 - z), GUN_METAL)
    # Gold ribs bridge the flank windows.
    s = np.abs(repeat(x, 2.4, 5.7, 10.5))
    b.add(np.maximum.reduce((s - .17, ay - 1.28, w - .25, .8 - ay)), GUN_GOLD)
    # Ejection port on the right.
    b.cut(np.maximum(box(q, (.2, 1.3, 7.0), (1.75, .62, .72), .1), -y), GUN_GOLD)
    # Rear cap and striker.
    r = rotate(q, 1, 12, (-5.5, 0, 6.2))
    b.cut(chamfer_cyl(r, (-5.6, 0, 6.2), 0, 1.0, .3, .08), GUN_METAL)
    b.add(chamfer_cyl(r, (-5.45, 0, 6.2), 0, .62, .18, .06), GUN_GOLD)
    # Sights.
    rear = box(q, (-3.5, 0, 8.05), (.72, 1.0, .42), .12)
    rear = np.maximum(rear, -box(q, (-3.5, 0, 8.4), (2, .26, .34), .04))
    b.add(rear, GUN_FRAME)
    b.add(box(q, (11.2, 0, 8.1), (.62, .2, .44), .08), GUN_FRAME)
    for c in ((-4.2, .55, 8.15), (-4.2, -.55, 8.15), (10.6, 0, 8.22)):
        b.cut(cyl(q, c, 0, .11, .07), GUN_INLAY)
    # Lightning inlay running out of the window.
    b.cut(np.maximum(g['bolt'](x, z) - np.maximum(ay - 1.42, 0) * .4, 1.38 - ay), GUN_INLAY)

    # Compensator: graphite octagon raked at the crown, gold only in the crown.
    w_, h = ay, np.abs(z - 5.85)
    oct_ = np.maximum.reduce((w_ - 1.32, h - 1.3, (w_ + h) * .7071 - 1.56))
    comp = rd(oct_, np.maximum(14.6 - x, x + (z - 5.85) * .3 - 18.45), .1)
    b.add(comp, GUN_FRAME)
    s = repeat(x + ay * .46, 1.02, 15.9, 17.2)
    b.cut(np.maximum.reduce((np.abs(s) - .25, ay - .95, 6.55 - z, 15.2 - x)), GUN_GOLD)
    b.cut(np.maximum.reduce((np.abs(repeat(x, 1.1, 16.1, 17.2)) - .27, np.abs(z - 5.85) - .44, .6 - ay)), GUN_GOLD)
    b.cut(chamfer_cyl(q, (18.5, 0, 5.85), 0, .98, .22, .08), GUN_GOLD)
    b.cut(cyl(q, (18.5, 0, 5.85), 0, .62, 2.2), GUN_METAL)

    # Frame, with the grip swelling to fit a palm.
    blend = ramp(z, 1.4, 3.1)
    width = 1.66 - .14 * blend
    edge = .86 - .68 * blend
    f = rd(g['frame'](x, z), ay - width, edge)
    f = np.minimum(f, rd(g['outer'](x, z), ay - .66, .26))
    for c in ((2.08, -.72), (1.48, -3.2), (.88, -5.7)):
        f = smax(f, 1.56 - hyp(x - c[0], z - c[1]), .24)
    f = rd(f, -g['hole'](x, z), .1)
    b.add(box(q, (5, 0, 4.62), (10, 1.2, .2)), GUN_METAL)
    b.add(f, GUN_FRAME)
    b.cut(np.maximum(g['facet'](x, z) - np.maximum(ay - 1.4, 0) * 1.4, 1.38 - ay), None)
    # Angled heat slots glow from within.
    s = repeat(x + (z - 3.85) * .55, 1.1, 8.0, 12.4)
    slot = rd(np.abs(s) - .15, np.abs(z - 3.88) - .22, .05)
    b.cut(np.maximum(slot, 1.16 - ay), GUN_METAL)
    b.cut(np.maximum(slot + .05, 1.2 - ay), GUN_METAL)
    b.add(np.maximum(slot + .03, ay - 1.17), GUN_INLAY)
    # Accessory rail under the nose.
    s = np.abs(repeat(x, .84, 8.4, 12.6))
    b.cut(np.maximum(s - .21, z - 2.98 - np.maximum(x - 8, 0) * .1), GUN_METAL)
    # Grip panels.
    b.cut(np.maximum(g['panel'](x, z) + .02 - np.maximum(ay - 1.3, 0) * .5, 1.3 - ay), GUN_METAL)
    panel = rd(g['panel'](x, z) + .08, ay - 1.66 + .3 * ((x + z * .24 + 1.8) / 2.6) ** 2, .2)
    b.add(panel, GUN_GRIP)
    b.cut(np.maximum(np.abs(hyp(x + 2.55, z + 2.3) - .68) - .1, 1.5 - ay), GUN_GOLD)
    b.add(chamfer_cyl(m, (-2.55, 1.56, -2.3), 1, .46, .13, .05), GUN_GOLD)
    for c in ((-3.0, .6), (-.75, .6), (-4.9, -5.3), (-1.9, -5.4)):
        d = chamfer_cyl(m, (c[0], 1.5, c[1]), 1, .25, .08, .03)
        d = np.maximum(d, -np.maximum(np.abs(rotate(m - np.array((c[0], 0, c[1]), F), 1, 30)[:, 0]) - .045, 1.53 - ay))
        b.add(d, GUN_METAL)
    # Magazine and base plate.
    b.add(rd(g['mag'](x, z), ay - 1.46, .2), GUN_FRAME)
    b.cut(np.maximum(np.abs(z + .085 * x + 7.62) - .05, np.abs(x + 3.8) - 2.4), GUN_INLAY)
    # Trigger, levers, pins, charge indicator.
    b.add(rd(g['trigger'](x, z), ay - .36, .14), GUN_GOLD)
    b.add(rd(g['lever'](x, z), np.abs(y + 1.62) - .14, .07), GUN_METAL)
    b.add(chamfer_cyl(m, (6.5, 1.55, 3.82), 1, .32, .1, .06), GUN_METAL)
    b.add(chamfer_cyl(m, (.85, 1.5, 1.72), 1, .42, .16, .05), GUN_METAL)
    s = np.abs(repeat(x, .34, -3.1, -1.74))
    b.cut(np.maximum.reduce((s - .1, np.abs(z - 3.75) - .15, 1.3 - ay)), GUN_INLAY)
    return b


GUN_LOOK = {
    GUN_BODY: dict(base=(.74, .71, .64), rough=.36, metal=0, finish='ceramic', tone=.07, rough_var=.12,
                   chip=dict(base=(.66, .62, .55), rough=.42, metal=.7), edge_a=.6, edge_b=1.5, scuff=.05, chip_amount=.6),
    GUN_FRAME: dict(base=(.13, .135, .145), rough=.4, metal=.95, finish='cast', tone=.2,
                    chip=dict(base=(.5, .49, .47), rough=.3, metal=1), edge_a=.4, edge_b=1.1, scuff=.15, chip_amount=.8),
    GUN_GRIP: dict(base=(.06, .06, .065), rough=.62, metal=0, finish='stipple', tone=.15),
    GUN_METAL: dict(base=(.2, .2, .21), rough=.38, metal=.95, finish='brushed', tone=.15),
    GUN_GOLD: dict(base=(.88, .64, .3), rough=.24, metal=1, finish='smooth', tone=.08),
    GUN_INLAY: dict(base=(.45, .28, .08), rough=.3, metal=0, glow=(1, .66, .16)),
    GUN_CORE: dict(base=(.3, .15, .04), rough=.12, metal=0, glow=(1, .6, .15)),
}


def gun_paint(a):
    x, y, z = a.p[:, 0] - GUN_X, a.p[:, 1], a.p[:, 2]
    m = a.ids == GUN_CORE
    if m.any():
        core = .35 + .65 * np.exp(-((x[m] - 7.6) / 3.2) ** 2)
        crystal_light(a, m, a.p[m] * np.array((.55, 1.5, 1.5), F), core)
    side = np.abs(a.n[:, 1]) > .7
    shifted = a.p - np.array((GUN_X, 0, 0), F)
    for sign in (1, -1):
        s = side & (np.sign(y) == sign)
        # Text reads front to back on the right so it is never mirrored.
        start = 1.3 if sign > 0 else -1.7
        ink = text_plane(shifted, s & (a.ids == GUN_BODY), 'MERIDIAN ARMS', (start, 0, 4.86), (-sign, 0, 0), (0, 0, 1), .2)
        a.layer(ink, (.3, .22, .12), .4)
        a.height -= ink * .012
    s = side & (a.ids == GUN_FRAME)
    for sign, start in ((-1, 5.2), (1, 12.8)):
        ink = text_plane(shifted, s & (np.sign(y) == sign), 'MK IV  7741-PH', (start, 0, 3.72), (-sign, 0, 0), (0, 0, 1), .17)
        a.layer(ink, (.72, .7, .62), .5, 0)


prop('gun', 'SM_Physis_Gun', 'Gun', gun_body, gun_core, ((-4.8, -2.4, -9), (20.5, 2.4, 9.2)), .02, 60000, GUN_LOOK, gun_paint, final=.96,
     views=((-58, 16, 1), (118, 22, 1), (-90, 2, 1), (-26, 28, .42, (15.5, 0, 6)), (150, 12, .5, (0, 0, 0)), (-125, 30, .5, (0, 0, 6))))


# ---------------------------------------------------------------- training drone

DR_SHELL, DR_GREY, DR_FRAME, DR_RUBBER, DR_METAL, DR_LAMP, DR_HOT, DR_EYE = 1, 2, 3, 4, 5, 6, 7, 8
DRONE = {}
HUB = Shape([(0, 2.6), (2.0, 2.6, .5), (3.6, 1.2, .7), (3.1, -4.5, 1), (1, -7.0, .6), (0, -7.2)], step=.04, pad=3)
DRONE_TILT = -12


def drone_shapes():
    return once(DRONE, lambda: dict(
        plan=Shape([(34, -3), (34, 8.5), (18, 21, 2), (-6, 24, 3), (-30, 13, 1.5), (-36.5, 7, .8), (-36.5, -3)], step=.05, pad=3),
        side=Shape([(34.5, 7.5), (23, 14.5, 3), (3, 19.5, 6), (-24, 14, 3), (-36.5, 8, 1), (-36.5, -3, 1), (-12, -14.5, 3), (18, -13.5, 3), (34.5, -6, 1)], step=.05, pad=3),
        duct=Shape([(8.5, 5.0), (9.7, 6.2, .5), (11.3, 5.6, .8), (11.5, 1.5, .9), (11.2, -3.6, .6), (10.1, -5.4, .4), (8.3, -5.0), (8.0, 0)], step=.04, pad=3),
        fin=Shape([(-31, 7), (-13, 12), (-31, 24, .4), (-37, 25, .3)], .3, step=.05, pad=3),
        arm=Shape([(10, 12), (3, 26, 1), (-.5, 32), (-14, 32), (-20, 24, 1), (-24, 12)], .6, step=.05, pad=3)))


def drone_hull(p):
    g = drone_shapes()
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ay = np.abs(y)
    d = smax(g['plan'](x, ay), g['side'](x, z), .5)
    d = smax(d, ay * .62 + (z - 5) * .78 - 16.5, .5)
    return smax(d, ay * .6 - (z - 5) * .8 - 15.5, .5)


def drone_body(p):
    g = drone_shapes()
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ay = np.abs(y)
    m = np.stack((x, ay, z), 1)
    b = Build(p)
    hull = drone_hull(p)

    # Chassis under the armour.
    b.add(hull + 2, DR_FRAME)
    seam = z + 2 - .06 * x                      # armour stops here
    above = -seam
    # Spine runs nose to tail, stepped below the shoulders.
    spine = rd(rd(ay - 5.6 - .06 * np.maximum(10 - x, 0), np.abs(x + 7) - 21, .4), above, .3)
    b.add(rd(hull + .55, spine, .3), DR_GREY)
    # Shoulders are the raised bone-white mass.
    front = x - 15 + ay * .55
    rear = -12 - x + ay * .3
    shoulder = rd(rd(front, rear, .4), np.maximum(6.9 + .06 * np.maximum(10 - x, 0) - ay, above), .4)
    b.add(rd(hull - .75, shoulder, .35), DR_SHELL)
    # Rear quarter plates.
    tail = rd(rd(-rear + 1.1, np.maximum(6.9 - ay, above), .3), -35 - x, .3)
    b.add(rd(hull + .2, tail, .3), DR_GREY)
    # Cowl wraps the nose and overhangs the eye.
    cowl = rd(-front + 1.1, above, .3)
    b.add(rd(hull + .35, cowl, .3), DR_SHELL)
    # Lower skirt.
    skirt = np.maximum.reduce((seam + 1.0, -z - 11, x - 13, -15 - x))
    b.add(rd(hull + .7, skirt, .3), DR_GREY)
    # Shoulder relief: a recessed access panel and four cooling louvres.
    b.cut(np.maximum(box(m, (0, 16, 0), (7, 4.4, 40), 1), -hull - 1.2))
    t = rotate(m, 1, -22, (-7, 18, 8))
    s = np.abs(repeat(t[:, 0], 2.1, -10, -4))
    b.cut(np.maximum.reduce((s - .55, np.abs(t[:, 2] - 12) - 5, 12 - ay, -hull - 2.2)), DR_METAL)
    # A groove echoing the shoulder edge gives the big plate a second scale.
    b.cut(np.maximum(np.abs(shoulder + 1.7) - .13, -hull - .95), DR_FRAME)
    # Panel lines break the shoulder into service plates.
    for c_, k_ in (((1.5, 0, 0), .34), ((-6, 0, 0), -.26)):
        b.cut(np.maximum(np.abs(x - c_[0] + (ay - 14) * k_) - .16, -hull - .95), DR_FRAME)
    # Fasteners at shoulder corners.
    for c in ((8.4, 10, 15), (-9.4, 10.6, 16.3), (5, 20.5, 8.7), (-10.5, 23.5, 5.2)):
        b.add(sphere(m, c, 1.05), DR_METAL)

    # Chassis vent band between skirt and armour.
    s = np.abs(repeat(x, 2.6, -14, 12))
    b.cut(np.maximum.reduce((s - .7, np.abs(seam + .1) - .6, 8 - ay, -hull - 3.2)), DR_METAL)

    # Eye: a flat-topped socket under the brow, so it glares.
    socket = np.maximum(chamfer_cyl(p, (34, 0, 1), 0, 10.6, 8.5, 0), z - 8.2)
    b.cut(socket - np.maximum(x - 31.5, 0) * .5, DR_METAL)
    brow = rotate(p, 1, 8, (30, 0, 9))
    b.add(rd(hull - .7, np.maximum.reduce((8.4 - brow[:, 2], ay - 12.2, 19 - x)), .4), DR_SHELL)
    v = rotate(np.stack((x - 27, y, z - 1), 1), 0, 12)
    u_, v_ = polar(v[:, 1], v[:, 2], 20)
    b.add(np.maximum.reduce((np.abs(u_ - 10.4) - 1.4, np.abs(v_ + (u_ - 10) * .5) - .3, np.abs(x - 27) - .9, z - 8.6)), DR_FRAME)
    # Machined lens bezel: the eye is an optic, not a ball.
    ring = hyp(y, z - 1)
    b.add(rd(np.abs(ring - 8.75) - .95, np.abs(x - 25.2) - 1.3, .28), DR_METAL)
    b.cut(np.maximum(np.abs(ring - 8.75) - .16, np.abs(x - 26.5) - .3), DR_RUBBER)
    # Sensor slits flanking the socket.
    b.cut(np.maximum.reduce((np.abs(ay - 14) - .7, np.abs(z - 2) - 2.2, 26 - x, -hull - .6)), DR_LAMP)

    # Armoured arms out to the nacelles.
    arm = rd(g['arm'](x, ay), np.abs(z + 1 + (ay - 14) * .12) - 3.6, .9)
    b.add(arm, DR_FRAME)
    b.add(rd(rd(g['arm'](x, ay) + 1.2, np.abs(z - 2.8 + (ay - 14) * .12) - .7, .3), 22 - ay, .2), DR_GREY)

    # Thrust nacelles, canted outward.
    c = (-7, 33.5, -1)
    t = rotate(m, 0, DRONE_TILT, c)
    n = t - np.array(c, F)
    radial = hyp(n[:, 0], n[:, 1])
    u_, v_ = polar(n[:, 0], n[:, 1], 5, .4)
    stator = np.maximum.reduce((np.abs(v_) - .55, u_ - 9.4, 2.1 - u_, np.abs(n[:, 2] + 3.5) - 1.4))
    u_, v_ = polar(n[:, 0], n[:, 1], 9)
    rotor = np.maximum.reduce((np.abs(v_ + (u_ - 6) * .14 + n[:, 2] * .35) - .28, u_ - 8.1, 2.1 - u_, np.abs(n[:, 2] - .8) - 1.1))
    b.add(np.minimum(stator, lathe(HUB, t, c)), DR_METAL)
    b.add(rotor, DR_METAL)
    b.d = np.maximum(b.d, np.where((np.abs(n[:, 2]) < 7) & (radial < 8.1) & (b.id != DR_METAL), 2., -1e3))
    b.add(lathe(g['duct'], t, c), DR_SHELL)
    b.cut(np.maximum(np.abs(radial - 11.5) - .12, np.abs(n[:, 2] - 1.6) - .45) - .1, DR_LAMP)
    # A hood covers the inner half of the intake, like a brow.
    hood = rd(rd(radial - 12.1, np.abs(n[:, 2] - 6.8) - .85, .3), n[:, 1] + 2.4 + n[:, 0] * .22, .4)
    b.add(hood, DR_GREY)
    b.add(rd(rd(radial - 7.6, np.abs(n[:, 2] - 7.4) - .22, .1), n[:, 1] + 2.8 + n[:, 0] * .22, .1), DR_METAL)
    # Hydraulic strut under each arm.
    b.add(capsule(m, (8, 11, -11), (-1, 24, -5.2), 1.05), DR_METAL)
    b.add(capsule(m, (8, 11, -11), (4.6, 16.2, -8.9), 1.85), DR_FRAME)

    # Twin cannons slung under the shoulders.
    b.blend(box(m, (12, 13, -9.4), (10.5, 3.8, 3.7), .9), DR_FRAME, 1)
    b.add(chamfer_cyl(m, (26, 13, -9.6), 0, 1.4, 15.4, .15), DR_METAL)
    b.add(chamfer_cyl(m, (25, 13, -9.6), 0, 2.2, 2.6, .3), DR_FRAME)
    b.add(chamfer_cyl(m, (39.4, 13, -9.6), 0, 2.05, 2, .25), DR_FRAME)
    b.cut(cyl(m, (41.4, 13, -9.6), 0, .95, 2.6), DR_RUBBER)
    s = repeat(x, 1.1, 38.1, 40.3)
    b.cut(np.maximum.reduce((np.abs(s) - .24, np.abs(ay - 13) - 3, np.abs(z + 9.6) - .55)), DR_RUBBER)

    # Rear drive pair.
    b.add(rd(hyp(m[:, 1] - 6.8, z - 3) - 4.6, np.abs(x + 35.5) - 4.4, .5), DR_FRAME)
    b.cut(cyl(m, (-40, 6.8, 3), 0, 3.5, 3.1), DR_METAL)
    u_, v_ = polar(m[:, 1] - 6.8, z - 3, 6)
    b.add(np.maximum.reduce((np.abs(v_) - .18, u_ - 3.5, np.abs(x + 38.4) - 1)), DR_METAL)

    # Tail blades, swept and canted apart.
    fin = rotate(m, 0, -24, (0, 7, 7))
    b.blend(rd(g['fin'](fin[:, 0], fin[:, 2]), np.abs(fin[:, 1] - 7) - .85, .45), DR_SHELL, .7)
    # Dorsal sensor block and mast.
    r = rotate(p, 1, 4)
    b.blend(box(r, (-10, 0, 19.6), (6.5, 2.3, 1.9), .7), DR_FRAME, .7)
    b.cut(box(r, (-10, 0, 21.4), (4.6, 1.1, .4), .2), DR_LAMP)
    b.add(capsule(p, (-15, 0, 20), (-23, 0, 33), .3), DR_METAL)
    return b


def drone_glow(p):
    b = Build(p)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    b.add(sphere(p, (18.2, 0, 1), 9.8), DR_EYE)
    m = np.stack((x, np.abs(y), z), 1)
    t = rotate(m, 0, DRONE_TILT, (-7, 33.5, -1))
    b.add(chamfer_cyl(t, (-7, 33.5, -3.6), 2, 9.3, .22, .05), DR_HOT)
    b.add(cyl(m, (-37.6, 6.8, 3), 0, 3.7, .3), DR_HOT)
    return b


DRONE_LOOK = {
    DR_SHELL: dict(base=(.62, .6, .55), rough=.42, metal=0, finish='ceramic', tone=.14, rough_var=.18,
                   chip=dict(base=(.58, .57, .55), rough=.42, metal=.8), edge_a=.6, edge_b=1.6, chip_amount=.65, scuff=.08),
    DR_GREY: dict(base=(.2, .22, .25), rough=.48, metal=.15, finish='cast', tone=.2,
                  chip=dict(base=(.48, .48, .47), rough=.34, metal=1), edge_a=.45, edge_b=1.2, chip_amount=.9, scuff=.15),
    DR_FRAME: dict(base=(.19, .195, .21), rough=.46, metal=.55, finish='cast', tone=.2,
                   chip=dict(base=(.5, .5, .48), rough=.34, metal=1), edge_a=.5, edge_b=1.3, chip_amount=.7, scuff=.05),
    DR_RUBBER: dict(base=(.05, .05, .055), rough=.72, metal=0, finish='cast'),
    DR_METAL: dict(base=(.42, .42, .43), rough=.34, metal=1, finish='brushed', along=(1, 0, 0), tone=.14),
    DR_LAMP: dict(base=(1, .3, .08), rough=.3, metal=0, glow=(1, .24, .04)),
    DR_HOT: dict(base=(1, .45, .15), rough=.4, metal=0, glow=(1, .4, .1)),
    DR_EYE: dict(base=(.8, .08, .03), rough=.08, metal=0, glow=(1, .1, .02)),
}


def drone_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    ay = np.abs(y)
    m = a.ids == DR_EYE
    r = hyp(y[m], z[m] - 1)
    # Dark coated glass over a bladed iris: light gathers to a pinpoint.
    spin = np.arctan2(z[m] - 1, y[m])
    blades = ramp(np.cos(spin * 12 + r * .8), -.5, .85)
    a.glow[m] = (np.array((.8, .02, .006), F) * (np.exp(-(r / 4.6) ** 2) * (.3 + .7 * blades))[:, None]
                 + np.array((1, .16, .03), F) * np.exp(-(r / 2.1) ** 2)[:, None]
                 + np.array((1, .72, .42), F) * np.exp(-(r / .8) ** 2)[:, None]
                 + np.array((.9, .05, .01), F) * (np.exp(-((r - 6.5) / .14) ** 2) * .7)[:, None])
    a.base[m] = np.array((.018, .008, .008), F)
    a.rough[m] = .05
    m = a.ids == DR_HOT
    a.glow[m] = GOLD_DEEP * (.5 + .4 * a.large[m])[:, None]
    painted = (a.wear < .5)[:, None] * 1.
    # Orange training flash: two chevrons on each shoulder, a band on each hood.
    q = (x + ay * .55 - 15) * -1
    flash = (np.abs(q - 2.2) < .9) | (np.abs(q - 4.6) < .4)
    mask = (flash & (a.ids == DR_SHELL) & (x > -14) & (x < 15)).astype(F) * a.wear.__lt__(.5)
    a.layer(mask, (.8, .29, .05), .42, 0)
    n = rotate(np.stack((x, ay, z), 1), 0, DRONE_TILT, (-7, 33.5, -1)) - np.array((-7, 33.5, -1), F)
    radial = hyp(n[:, 0], n[:, 1])
    rim = (a.ids == DR_SHELL) & (radial > 8.8) & (n[:, 2] > 2.5) & (radial < 11)
    stripe = ((np.arctan2(n[:, 1], n[:, 0]) * 14 / (2 * math.pi) + radial * .1) % 1) < .5
    a.layer((rim & stripe).astype(F) * (a.wear < .5), (.09, .09, .095), .45, 0)
    a.layer((rim & ~stripe).astype(F) * (a.wear < .5), (.8, .52, .05), .45, 0)
    top = (a.n[:, 2] > .4) & np.isin(a.ids, (DR_SHELL, DR_GREY))
    for sign, ox, oy in ((-1, -9.5, -13.4), (1, 8.5, 13.4)):
        u, v = (-sign, 0, 0), (0, -sign, 0)
        ink = text_plane(a.p, top & (np.sign(y) == sign), 'TRN-07', (ox, oy, 0), u, v, 1.9, .13)
        a.layer(ink * (a.wear < .5), (.09, .09, .1))
        ink = text_plane(a.p, top & (np.sign(y) == sign), 'MERIDIAN DEFENSE', (ox, oy + sign * -.0 + (2 if sign < 0 else -2) * -1, 0), u, v, .8, .1)
        a.layer(ink * (a.wear < .5), (.09, .09, .1))
    impacts = np.random.default_rng(5).uniform((-30, -24, -5), (24, 24, 20), (14, 3))
    for c in impacts:
        d = hyp(x - c[0], y - c[1], z - c[2])
        s = ramp(d, 2.4, .4) * (a.glow.sum(1) == 0)
        scorch = s * ramp(a.medium + (a.fine - .5) * .8, .35, .6)
        a.base = a.base * (1 - scorch[:, None] * .75) + np.array((.04, .036, .03), F) * scorch[:, None] * .75
        a.rough = np.clip(a.rough + scorch * .2, 0, 1)
        a.metal = a.metal * (1 - scorch)


prop('drone', 'SM_Drone', 'Drone', drone_body, drone_glow, ((-42, -47, -18), (44, 47, 36)), .09, 110000, DRONE_LOOK, drone_paint,
     scale=4., ao=12., curve=.2, views=((-35, 18, 1), (32, 6, 1), (150, 28, 1), (-90, 62, 1), (0, 2, .5, (30, 0, -2)), (-125, -28, 1)))


# ---------------------------------------------------------------- pickups

HP_CAP, HP_RED, HP_METAL, HP_RUBBER, HP_GOLD, HP_LAMP, HP_FLUID = 1, 2, 3, 4, 5, 6, 7
HEALTH = {}


def health_body(p):
    s = once(HEALTH, lambda: dict(
        cap=Shape([(0, 17.2), (5.2, 17.2, .8), (8.4, 16, 1.4), (10.8, 13.4, 1.2), (11.2, 11.2, .4), (10.4, 10.6, .25), (10.4, 9.6, .25), (9.2, 9.1), (0, 9.1)], step=.015)))
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    az = np.abs(z)
    m = np.stack((x, y, az), 1)
    b = Build(p)
    cap = lathe(s['cap'], m)
    b.add(cap, HP_CAP)
    # A red collar band, seated in a groove.
    b.cut(np.maximum(np.abs(az - 12.8) - .95, 10.3 - hyp(x, y)), HP_RED)
    b.cut(np.maximum(np.abs(np.abs(az - 12.8) - 1.08) - .08, 10.2 - hyp(x, y)), HP_METAL)
    # End face: recessed cross, lit, with a grip knurl.
    cross = np.minimum(box(p * np.array((1, 1, 0), F), (0, 0, 0), (2.4, .8, 1)), box(p * np.array((1, 1, 0), F), (0, 0, 0), (.8, 2.4, 1)))
    b.cut(np.maximum(cross, 16.75 - az), HP_LAMP)
    b.cut(np.maximum(np.abs(hyp(x, y) - 4.4) - .12, 17 - az), HP_METAL)
    # Clamp shoulders that carry the struts.
    u, v = polar(x, y, 3, .52)
    b.add(rd(hyp(u - 9.0, v) - 1.75, np.abs(az - 9.9) - .9, .25), HP_METAL)
    # Struts and their stepped sleeves.
    strut = hyp(u - 9.0, v)
    b.add(rd(strut - .78, az - 10, .1), HP_METAL)
    b.add(rd(strut - 1.08, np.abs(az - 3.6) - 2.8, .15), HP_RUBBER)
    # Waist ring holds the tank.
    b.add(rd(np.abs(hyp(x, y) - 8.5) - .55, az - .7, .2), HP_GOLD)
    b.cut(np.maximum.reduce((np.abs(repeat(polar(x, y, 12)[1], 1, 0, 0)) - .35, az - .32, 8.7 - hyp(x, y))), HP_METAL)
    # Inner seats of the tank.
    b.add(rd(hyp(x, y) - 8.0, np.abs(az - 9.4) - .5, .2), HP_METAL)
    return b


def health_glow(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    a = np.arctan2(y, x)
    b = Build(p)
    r = hyp(x, y)
    # Fluid column with a slow helix through it.
    b.add(rd(r - 7.7 - .14 * np.sin(2 * a + z * .9), np.abs(z) - 9.6, .3) * .85, HP_FLUID)
    return b


HEALTH_LOOK = {
    HP_CAP: dict(base=(.74, .75, .73), rough=.38, metal=0, finish='ceramic', tone=.09, rough_var=.18,
                 chip=dict(base=(.5, .5, .5), rough=.34, metal=1), chip_amount=.6, scuff=.1, edge_a=.8, edge_b=1.8),
    HP_RED: dict(base=(.72, .09, .05), rough=.32, metal=0, finish='ceramic', tone=.08),
    HP_METAL: dict(base=(.62, .62, .63), rough=.28, metal=1, finish='brushed', along=(0, 0, 1), tone=.08),
    HP_RUBBER: dict(base=(.06, .06, .065), rough=.66, metal=0, finish='stipple'),
    HP_GOLD: dict(base=(.86, .62, .3), rough=.28, metal=1, finish='brushed', along=(0, 0, 1)),
    HP_LAMP: dict(base=(.8, .05, .03), rough=.3, metal=0, glow=(1, .05, .025)),
    HP_FLUID: dict(base=(.4, .05, .03), rough=.06, metal=0, glow=(1, .2, .08)),
}


def health_paint(a):
    m = a.ids == HP_FLUID
    x, y, z = a.p[m, 0], a.p[m, 1], a.p[m, 2]
    angle = np.arctan2(y, x)
    wave = np.sin(angle * 2 + z * .9)
    helix = ramp(wave, .55, .98)
    q = a.p[m] * .55
    cells = fbm(q + np.array((0, 0, 3), F), 3)
    # Round rising bubbles and a bright ribbon of serum, never a flat red wall.
    rng = np.random.default_rng(21)
    bubbles = np.zeros(len(z), F)
    for ta, tz, tr in zip(rng.uniform(-math.pi, math.pi, 90), rng.uniform(-9, 9, 90), rng.uniform(.09, .42, 90) ** 1.3):
        d = hyp((np.abs(((angle - ta + math.pi) % (2 * math.pi)) - math.pi)) * 7.7, z - tz)
        bubbles = np.maximum(bubbles, ramp(np.abs(d - tr), tr * .4 + .03, 0))
    ribbon = np.exp(-((wave - .92) / .07) ** 2)
    level = .12 + .5 * ramp(np.abs(z), 9.8, 2)
    a.glow[m] = (np.array((.75, .018, .012), F) * (level * (.45 + cells * 1.1))[:, None]
                 + np.array((1, .13, .06), F) * (ribbon * (.2 + .5 * cells))[:, None]
                 + np.array((1, .52, .4), F) * (bubbles * .5)[:, None])
    a.base[m] = np.array((.16, .012, .01), F)
    # Dosage ticks engraved round the lit cross.
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    r = hyp(x, y)
    ticks = (r > 5.1) & (r < 5.9) & (np.abs(z) > 15) & (np.abs(np.arctan2(y, x) * 36 / (2 * math.pi) % 1 - .5) > .42) & (a.ids == HP_CAP)
    a.layer(ticks.astype(F), (.14, .14, .15), .5)


prop('health', 'SM_Pickup_Health', 'PickupHealth', health_body, health_glow, ((-13, -13, -18.5), (13, 13, 18.5)), .03, 28000, HEALTH_LOOK, health_paint,
     scale=1.6, grime=.6, ao=3., curve=.1, views=((-40, 14, 1), (-10, 60, .85)))


SEED_HUSK, SEED_DARK, SEED_VEIN, SEED_CRYSTAL = 1, 2, 3, 4
SEED = {}


def seed_shape():
    return once(SEED, lambda: dict(
        husk=Shape([(-1, 22.6), (.8, 22.4, .4), (2, 19.5, 1.5), (6.5, 13.5, 3), (11.8, 4, 4), (12.6, -3, 4), (9.4, -12.6, 3), (3.6, -18, 1.5), (-1, -19.6)], step=.03, pad=4)))


def seed_warp(p):
    s = p.copy()
    s[:, 0] += .8 * np.sin(p[:, 2] * .17 + 1)
    s[:, 1] += .6 * np.sin(p[:, 2] * .13 + 2.5)
    return s


def seed_coords(p):
    """Leaf coordinates shared by the shape and the paint."""
    g = seed_shape()
    s = seed_warp(p)
    x, y, z = s[:, 0], s[:, 1], s[:, 2]
    r = np.maximum(hyp(x, y), .5)
    a = np.arctan2(y, x)
    turn = a + z * .075 + .2 * np.sin(z * .2)
    span = math.pi / 5
    phi = np.abs(((turn + span) % (2 * span)) - span)    # 0 at leaf centre, span at the slit
    arc = phi * r
    open_ = ramp(z, -16, -3) * ramp(z, 18, 6)
    fade = ramp(r, 1, 6)                                 # no leaf form where the angle is meaningless
    half = span * r * (1 + 1.2 * (1 - open_)) - 2.7 * open_
    gap = arc - half                                     # negative inside the leaf; closed at both tips
    surface = lathe(g['husk'], s) + (phi / span) ** 2 * 1.5 * fade
    return dict(s=s, r=r, z=z, span=span, arc=arc, open=open_, fade=fade, gap=gap, surface=surface)


def seed_body(p):
    c = seed_coords(p)
    surface, gap, arc, fade, open_, r = c['surface'], c['gap'], c['arc'], c['fade'], c['open'], c['r']
    b = Build(p)
    # Five leaves spiral up the seed, parting mid body and fused at both tips.
    husk = rd(smax(surface, -surface - 3, .4), gap, .6)
    # A raised midrib on each leaf.
    rib = smax(surface - .34 * fade + np.minimum(arc, 1) * .34 * fade, arc - .55 - (1 - fade) * 9, .3)
    husk = smin(husk, rib, .35)
    b.add(husk * .8, SEED_HUSK)
    # Where the leaves are fused they keep a fine seam, so the spiral carries to the tips.
    b.cut(np.maximum.reduce((np.abs(arc - c['span'] * r) - .09, surface + .16, .15 - (1 - open_), 1.6 - r)) * .8, SEED_DARK)
    # Root tendrils curl under the seed, the stem curls above.
    for n in range(5):
        t = n * 2 * math.pi / 5 + .4
        o = np.array((math.cos(t), math.sin(t), 0))
        w = np.array((-o[1], o[0], 0))
        pts = bezier(o * 2 + (0, 0, -15.5), o * 11 + w * 3 + (0, 0, -19.5), o * 13.5 + w * -2 + (0, 0, -16.5), o * 11.5 + w * -4.5 + (0, 0, -13.5 - n * .5), 9)
        b.blend(tube(p, pts, 1.15, .5), SEED_HUSK, .9)
    for n in range(3):
        t = n * 2 * math.pi / 3 + 1.1
        o = np.array((math.cos(t), math.sin(t), 0))
        w = np.array((-o[1], o[0], 0))
        pts = bezier((0, 0, 19), o * 1 + (0, 0, 21.5), o * 3.6 + w * 1.6 + (0, 0, 21.5), o * 4.2 + w * 3.4 + (0, 0, 17.8 + n * .4), 8)
        b.blend(tube(p, pts, .7, .34), SEED_HUSK, .5)
    return b


def seed_crystal(p):
    b = Build(p)
    s = seed_warp(p)
    d = None
    for rx, ry, c, h, w in ((0, 0, (0, 0, 0), 17, 8.7), (22, 40, (2.6, -1.5, 3), 12.5, 5), (-19, 150, (-1.5, 2.8, -3), 12.5, 4.6), (12, 260, (-2.8, -2.2, 5), 9, 3.8)):
        q = rotate(rotate(s, 2, ry), 0, rx)
        q = q - np.array(c, F)
        u, v = polar(q[:, 0], q[:, 1], 6, rx * .1 + .3)
        # A doubly terminated faceted prism.
        e = np.maximum.reduce((u - w, (u * 1.3 + np.abs(q[:, 2]) - h + w * 1.3 * .42) * .6))
        d = e if d is None else np.minimum(d, e)
    b.add(d, SEED_CRYSTAL)
    return b


SEED_LOOK = {
    SEED_HUSK: dict(base=(.84, .6, .25), rough=.36, metal=1, finish='organic', tone=.25, rough_var=.3),
    SEED_DARK: dict(base=(.14, .09, .05), rough=.5, metal=.8, finish='organic'),
    SEED_VEIN: dict(base=(.5, .28, .08), rough=.3, metal=0, glow=(1, .66, .16)),
    SEED_CRYSTAL: dict(base=(.24, .1, .02), rough=.08, metal=0, glow=(1, .66, .16)),
}


def seed_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    # Antique hollows, polished high points.
    m = m0 = a.ids == SEED_HUSK
    hollow = ramp(-a.curve[m], .02, .35) + (1 - a.ao[m]) * .9
    pat = np.clip(hollow, 0, 1) * (.55 + a.medium[m] * .8)
    pat = np.clip(pat, 0, 1)[:, None]
    a.base[m] = a.base[m] * (1 - pat) + np.array((.12, .075, .04), F) * pat
    a.rough[m] = np.clip(a.rough[m] + pat[:, 0] * .4, 0, 1)
    shine = ramp(a.curve[m], .1, .6)
    a.base[m] = np.clip(a.base[m] * (1 + shine[:, None] * .3), 0, 1)
    # Leaf venation: chevrons off the midrib, and a line of light inside each margin.
    c = seed_coords(a.p)
    ridge = np.exp(-(np.sin((c['z'] - c['arc'] * .9) * .95) / .17) ** 2) * ramp(c['gap'], -.5, -1.9) * ramp(c['arc'], .5, 1.3) * c['fade']
    outside = np.clip(ramp(c['surface'], -.9, -.3), 0, 1)
    a.height[m0] += (ridge * outside)[m0] * .05
    a.base[m0] *= (1 + (ridge * outside)[m0][:, None] * .22)
    margin = np.exp(-((c['gap'] + .95) / .13) ** 2) * outside * c['open']
    a.glow[m0] = a.glow[m0] + (GOLD * (margin * .85)[:, None])[m0]
    a.base[m0] = a.base[m0] * (1 - (margin[m0] * .7)[:, None])
    # Crystal: unequal facets, fractures, a heart of light.
    m = a.ids == SEED_CRYSTAL
    heart = ramp(hyp(x[m], y[m], z[m] * .6), 13, 3)
    crystal_light(a, m, a.p[m] * np.array((.2, .2, .11), F), heart)


prop('divinity', 'SM_Pickup_Divinity', 'PickupDivinity', seed_body, seed_crystal, ((-17, -17, -22.5), (17, 17, 23)), .05, 42000, SEED_LOOK, seed_paint,
     scale=2., grime=.2, ao=5., curve=.14, sharp=60, views=((-40, 12, 1), (130, 22, 1), (-20, 4, .5, (0, 0, 2))))


AM_SHELL, AM_FRAME, AM_METAL, AM_GOLD, AM_RUBBER, AM_LAMP, AM_CELL = 1, 2, 3, 4, 5, 6, 7
AMMO = {}


def ammo_body(p):
    s = once(AMMO, lambda: dict(
        cap=Shape([(0, 20), (4, 20, .4), (5.8, 18.7, .3), (9.8, 18, .9), (11, 16, .7), (11, 13, .4), (0, 13)], step=.015),
        window=Shape([(-2.5, -9), (2.5, -9), (3.1, -8), (3.1, 8), (2.5, 9), (-2.5, 9), (-3.1, 8), (-3.1, -8)], .3, step=.015)))
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    az = np.abs(z)
    m = np.stack((x, y, az), 1)
    b = Build(p)
    u, v = polar(x, y, 8, math.pi / 8)
    prism = rd(u - 9.2, az - 15, .5)
    b.add(prism, AM_SHELL)
    # Four long windows; alternate faces carry ribs.
    u4, v4 = polar(x, y, 4)
    win = s['window'](v4, z) - np.maximum(u4 - 8.2, 0) * .8
    b.cut(np.maximum(win, 7.2 - u4), AM_FRAME)
    u4b, v4b = polar(x, y, 4, math.pi / 4)
    b.cut(np.maximum.reduce((np.abs(repeat(z, 1.6, -7.2, 7.2)) - .34, np.abs(v4b) - 2.3, 8.75 - u4b)), AM_METAL)
    # End collars.
    collar = rd(u - 9.7, np.abs(az - 14) - 2.2, .35)
    b.add(collar, AM_FRAME)
    # Cap: lathe, so it reads as a machined part.
    b.add(lathe(s['cap'], np.stack((x, y, z), 1)), AM_METAL)
    b.add(rd(hyp(x, y) - 10.7, np.abs(z + 17) - 3, .5), AM_FRAME)
    # Contacts on the top face; lit ring between them.
    u6, v6 = polar(x, y, 6, .26)
    b.add(rd(hyp(u6 - 7.7, v6) - .95, z - 19.5, .15), AM_GOLD)
    b.cut(np.maximum(np.abs(hyp(x, y) - 2.6) - .32, 19.8 - z), AM_LAMP)
    # Foot: drive pins seat the cell in its bay.
    b.cut(np.maximum.reduce((hyp(u6 - 6.4, v6) - 1.1, z + 19.3)), AM_RUBBER)
    # Carry bail.
    side = bezier((0, -9.6, 14.5), (0, -10.5, 21.5), (0, -5, 21.8), n=8)
    q = np.stack((x, np.abs(y) * -1, z), 1)
    b.add(np.minimum(tube(q, side, .55), capsule(p, (0, -5, 21.8), (0, 5, 21.8), .55)), AM_RUBBER)
    b.add(chamfer_cyl(np.stack((x, np.abs(y), z), 1), (0, 9.7, 14.6), 1, 1.5, .7, .2), AM_FRAME)
    # Latches over the collars.
    u_, v_ = polar(x, y, 4, math.pi / 4)
    b.add(np.maximum(box(np.stack((u_, v_, az), 1), (9.8, 0, 12.2), (.5, 1.5, 3.4), .25), -1e3), AM_METAL)
    return b


def ammo_glow(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    b = Build(p)
    r = hyp(x, y)
    b.add(rd(r - 7.6 + .1 * np.cos(z * 2.2), np.abs(z) - 12.5, .3) * .9, AM_CELL)
    return b


AMMO_LOOK = {
    AM_SHELL: dict(base=(.2, .205, .22), rough=.38, metal=.1, finish='cast', tone=.12,
                   chip=dict(base=(.55, .54, .52), rough=.3, metal=1), edge_a=.25, edge_b=.85, scuff=.25),
    AM_FRAME: dict(base=(.1, .105, .115), rough=.42, metal=.9, finish='cast',
                   chip=dict(base=(.5, .5, .48), rough=.3, metal=1), edge_a=.35, edge_b=1, scuff=.1),
    AM_METAL: dict(base=(.52, .52, .53), rough=.3, metal=1, finish='brushed', along=(0, 0, 1)),
    AM_GOLD: dict(base=(.88, .64, .3), rough=.24, metal=1, finish='brushed'),
    AM_RUBBER: dict(base=(.05, .05, .055), rough=.66, metal=0, finish='stipple'),
    AM_LAMP: dict(base=(1, .5, .1), rough=.3, metal=0, glow=(1, .66, .16)),
    AM_CELL: dict(base=(.24, .1, .02), rough=.1, metal=0, glow=(1, .66, .16)),
}


def ammo_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    m = a.ids == AM_CELL
    ring = ramp(np.abs(((z[m] / 2.86) % 1) - .5), .35, .46)
    crystal_light(a, m, a.p[m] * np.array((.4, .4, .16), F), ramp(np.abs(z[m]), 13, 2) * (1 - ring * .75))
    u, v = polar(x, y, 8, math.pi / 8)
    # Hazard band on the lower collar, charge label on two flats.
    band = ((np.abs(z + 13.9) < 1.1) & (a.ids == AM_FRAME)).astype(F)
    stripe = ((np.arctan2(y, x) * 8 + z * .5) % (math.pi * 2 / 3)) < math.pi / 3
    a.layer(band * stripe * (a.wear < .4), (.8, .52, .05), .42, 0)
    a.layer(band * ~stripe * (a.wear < .4), (.05, .05, .055), .42, 0)
    flats = (a.ids == AM_SHELL)
    angle = -math.pi / 4
    for t, title in ((-3 * math.pi / 4 + 0, 'CELL 8.2'), (math.pi / 4, 'CELL 8.2')):
        c, s = math.cos(t), math.sin(t)
        facing = (a.n[:, 0] * c + a.n[:, 1] * s) > .9
        rx, ry = (-s, c)
        ink = text_plane(a.p, facing & flats, title, (c * 9 - rx * 1.5 * 1 * -1, s * 9 - ry * 1.5 * -1, 3.5), (rx * -1, ry * -1, 0), (0, 0, 1), .62, .12)
        a.layer(ink * (a.wear < .4), (.82, .8, .72), .5, 0)
        ink = text_plane(a.p, facing & flats, 'MJ DC', (c * 9 - rx * 1.5 * -1, s * 9 - ry * 1.5 * -1, 2.2), (rx * -1, ry * -1, 0), (0, 0, 1), .62, .12)
        a.layer(ink * (a.wear < .4), (.8, .52, .05), .5, 0)


prop('ammo', 'SM_Pickup_Ammo', 'PickupAmmo', ammo_body, ammo_glow, ((-13, -13, -21), (13, 13, 23)), .03, 30000, AMMO_LOOK, ammo_paint,
     scale=1.6, ao=3., curve=.1, views=((-38, 16, 1), (20, 42, .85)))


# ---------------------------------------------------------------- scan targets, wall mounted, front toward -Y

SC_PLATE, SC_PAINT, SC_METAL, SC_RUBBER, SC_GOLD, SC_LAMP, SC_FLOW, SC_SCREEN, SC_KEY = 1, 2, 3, 4, 5, 6, 7, 8, 9
SC_LOOK = {
    SC_PLATE: dict(base=(.27, .29, .32), rough=.46, metal=.45, finish='cast', tone=.18,
                   chip=dict(base=(.52, .52, .5), rough=.32, metal=1), edge_a=.25, edge_b=.85, scuff=.25),
    SC_PAINT: dict(base=(.5, .5, .47), rough=.44, metal=0, finish='ceramic', tone=.14,
                   chip=dict(base=(.25, .25, .26), rough=.4, metal=.9), edge_a=.2, edge_b=.8, scuff=.35),
    SC_METAL: dict(base=(.5, .5, .51), rough=.34, metal=1, finish='brushed', along=(0, 0, 1), tone=.14),
    SC_RUBBER: dict(base=(.055, .055, .06), rough=.68, metal=0, finish='cast'),
    SC_GOLD: dict(base=(.86, .62, .28), rough=.28, metal=1, finish='brushed', along=(0, 0, 1)),
    SC_LAMP: dict(base=(.5, .3, .08), rough=.3, metal=0, glow=(1, .66, .16)),
    SC_FLOW: dict(base=(.24, .1, .02), rough=.1, metal=0, glow=(1, .66, .16)),
    SC_SCREEN: dict(base=(.02, .05, .07), rough=.08, metal=0, glow=(.02, .06, .08)),
    SC_KEY: dict(base=(.17, .17, .18), rough=.5, metal=0, finish='cast'),
}


def conduit_body(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax, az = np.abs(x), np.abs(z)
    m = np.stack((ax, y, z), 1)
    mz = np.stack((ax, y, az), 1)
    b = Build(p)
    # Wall strongback.
    b.add(box(p, (0, 6, 0), (27, 1.5, 60), .5), SC_PLATE)
    s = repeat(z, 13, -52, 52)
    b.cut(np.maximum.reduce((np.abs(ax - 23.6) - 1.6, np.abs(s) - 3.2, 3.9 - y)), SC_RUBBER)
    # Power mains enter top and bottom, then fan into the junction.
    for c, r in ((0, 3.9), (9.5, 2.9), (17, 2.2)):
        k = 21 if c == 0 else (24 + c * .25)
        pts = bezier((c, 2.2, 60), (c, 2.2, k + 8), (c * .9, 1.8 + c * .05, k + 4), (c * .8, -.6, k - 2), 7)
        b.add(tube(mz, pts, r), SC_PAINT if c == 0 else SC_METAL)
    # Pipe collars.
    b.add(np.minimum(chamfer_cyl(mz, (0, 2.2, 49), 2, 5.0, 1.2, .35), chamfer_cyl(mz, (0, 2.2, 36), 2, 5.0, 1.2, .35)), SC_PLATE)
    b.add(np.minimum(chamfer_cyl(mz, (9.5, 2.2, 49), 2, 3.8, .9, .3), chamfer_cyl(mz, (17, 2.2, 49), 2, 3.1, .8, .25)), SC_PLATE)
    # Retaining clamps across the bundle.
    clamp = box(mz, (0, 2.6, 42.5), (22.5, 3.0, 1.9), .5)
    b.add(clamp, SC_PAINT)
    for c in (6, 13.5, 21):
        b.add(chamfer_cyl(mz, (c, -.4, 42.5), 1, .95, .55, .15), SC_METAL)
    # Junction housing.
    d = box(p, (0, 0, 0), (25.5, 7.2, 25.5), 1.2)
    d = cd(d, (ax + np.abs(z) - 45.5) * .7071, 0)
    b.add(d, SC_PAINT)
    # Heat-sink flanks.
    t = np.abs(repeat(z, 2.6, -16, 16))
    b.cut(np.maximum.reduce((t - .55, 18.8 - ax, -y - 6.4, y - 9)), SC_METAL)
    # Window into the bus, framed.
    win = box(p, (0, -3.6, 0), (13.6, 6, 21), 1.2)
    b.cut(win, SC_PLATE)
    b.add(np.maximum(box(p, (0, -6.8, 0), (15.8, .9, 23.2), .4), -box(p, (0, -7, 0), (13.5, 2, 20.9), .9)), SC_PLATE)
    # Shallow service panels break up the housing face.
    for c, h in (((20.5, -7.2, 14.5), (2.8, 1, 4.2)), ((20.5, -7.2, -14.5), (2.8, 1, 4.2))):
        b.cut(box(m, c, h, .5))
    b.cut(box(m, (0, -7.6, 23.9), (15.2, .8, .3)), SC_METAL)
    # Glass guard bars across the window.
    t = np.abs(repeat(z, 10.5, -15.75, 15.75))
    b.add(rd(t - .5, np.abs(y + 6.3) - .45, .2) + np.maximum(ax - 14, 0), SC_METAL)
    # Insulators stacked each side of the bus.
    b.add(np.maximum.reduce((hyp(np.abs(ax - 11.2), y + 2.2) - 1.3 - .34 * np.cos(z * 2.2), az - 21)), SC_RUBBER)
    s = np.abs(repeat(x, 3.2, -9.6, 9.6))
    b.add(np.maximum.reduce((s - 1.0, np.abs(y - 1.9) - 1, az - 21)), SC_METAL)
    # Corner fasteners.
    for c in ((21.5, 21.5), (21.5, 8), (21.5, -8), (21.5, -21.5)):
        b.add(chamfer_cyl(m, (c[0], -7.2, c[1]), 1, 1.0, .5, .15), SC_METAL)
    # Lamp column and a warning lamp over the housing.
    s = np.abs(repeat(z, 2.4, -7.2, 7.2))
    b.cut(np.maximum.reduce((s - .7, np.abs(ax - 17.4) - .5, y + 6.9)), SC_LAMP)
    return b


def conduit_glow(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    b = Build(p)
    # A living bus bar: three twisting rods.
    a = z * .2
    d = None
    for phase in (0, 2.09, 4.19):
        r = hyp(x - 3 * np.cos(a + phase), (y + 1) - 1.9 * np.sin(a + phase)) - 1.75
        d = r if d is None else np.minimum(d, r)
    b.add(rd(d * .8, np.abs(z) - 22, .2), SC_FLOW)
    return b


def conduit_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    m = a.ids == SC_FLOW
    crystal_light(a, m, a.p[m] * np.array((.3, .3, .1), F), .35 + .65 * np.exp(-(z[m] / 13) ** 2))
    # Hazard stripes above and below the housing.
    front = a.n[:, 1] < -.6
    band = ((np.abs(np.abs(z) - 42.5) < 1.5) & (np.abs(x) < 22) & (a.ids == SC_PAINT) & front).astype(F)
    stripe = ((x + z) % 6) < 3
    a.layer(band * stripe * (a.wear < .4), (.8, .52, .05))
    a.layer(band * ~stripe * (a.wear < .4), (.06, .06, .065))
    panel = front & (a.ids == SC_PAINT)
    for sign in (-1, 1):
        ink = text_plane(a.p, panel, 'HIGH CHARGE', (-6.8 if sign > 0 else -6.8, -7.2, 21.9 if sign > 0 else -23), (1, 0, 0), (0, 0, 1), .62, .11)
        a.layer(ink, (.09, .09, .1))


prop('conduit', 'SM_Scan_Conduit', 'ScanConduit', conduit_body, conduit_glow, ((-31, -9, -61), (31, 9, 61)), .09, 60000, SC_LOOK, conduit_paint,
     scale=3.5, grime=1.1, ao=10., curve=.2, glow_uv=1.3, cap=.3, views=((-70, 10, 1), (-120, 25, 1), (-90, 0, .42, (0, -7, 0))))


def terminal_body(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    m = np.stack((ax, y, z), 1)
    b = Build(p)
    # Back frame and side rails.
    b.add(box(p, (0, 6, 0), (28, 1.5, 59), .6), SC_PLATE)
    b.add(box(m, (25.5, 2, 0), (3, 5.5, 55), 1), SC_PAINT)
    s = np.abs(repeat(z, 7, -45, 45))
    b.cut(np.maximum.reduce((s - 1.7, np.abs(ax - 25.5) - 1, y + 3.8)), SC_METAL)
    # Main body: slopes out toward the keys so the screen tips up to the viewer.
    v = rotate(p, 0, 7, (0, 0, 20))
    head = box(v, (0, 1.6, 20), (22.4, 5.4, 32), 1.4)
    b.add(head, SC_PAINT)
    # Hood.
    hood = rotate(p, 0, -24, (0, -3, 49))
    b.blend(box(hood, (0, -1.4, 52), (23.4, 6.2, 2.1), 1.2), SC_PLATE, 1.5)
    b.add(np.maximum(box(hood, (0, -5.8, 50.2), (23.2, 1.8, .55), .3), -1e3), SC_METAL)
    # Screen bay.
    bay = box(v, (0, -3.8, 20), (20, 1.8, 27), 1)
    b.cut(bay, SC_RUBBER)
    # Heavy bezel with corner gussets.
    b.add(np.maximum(box(v, (0, -4.1, 20), (20.8, .9, 27.8), .5), -box(v, (0, -4.2, 20), (19, 2.4, 26), .6)), SC_PLATE)
    for sx in (-1, 1):
        for sz in (-1, 1):
            c = (sx * 19.3, -4.6, 20 + sz * 26.3)
            b.add(box(v, c, (1.7, .55, 1.7), .3), SC_METAL)
    # Soft keys along the screen edge.
    s = np.abs(repeat(z, 7.5, 2, 40))
    # Control deck, angled, with key rows.
    d = rotate(p, 0, -38, (0, -2, -18))
    deck = box(d, (0, -2, -24), (22.4, 6, 11.4), 1.2)
    b.blend(deck, SC_PLATE, 1.5)
    well = box(d, (-5.5, -8.6, -24), (15, 1.1, 9), .6)
    b.cut(well, SC_RUBBER)
    u = repeat(d[:, 0], 3.3, -18.6, 7.8)
    w = repeat(d[:, 2], 3.2, -29.8, -18.2)
    key = rd(rd(np.abs(u) - 1.4, np.abs(w) - 1.35, .3), d[:, 1] + 7.5, .3)
    key = np.maximum(key, -(d[:, 1] + 8.1))
    b.add(key, SC_KEY)
    # Dial and big confirm key on the right of the deck.
    b.add(chamfer_cyl(d, (15.8, -8.1, -19.6), 1, 3.1, 1.4, .3), SC_METAL)
    t = np.abs(polar(d[:, 0] - 15.8, d[:, 2] + 19.6, 28)[1])
    dial = hyp(d[:, 0] - 15.8, d[:, 2] + 19.6)
    b.cut(np.maximum.reduce((t - .13, 2.8 - dial, dial - 3.3, d[:, 1] + 8.1)), SC_RUBBER)
    b.add(chamfer_cyl(d, (15.8, -8.3, -29), 1, 2.1, .9, .3), SC_KEY)
    b.cut(np.maximum(np.abs(hyp(d[:, 0] - 15.8, d[:, 2] + 29) - 1.6) - .15, d[:, 1] + 8.9 + .1 - .4), SC_LAMP)
    # Lower cowl and cable run.
    b.add(box(p, (0, 1.5, -50), (20, 5.2, 8), 1.4), SC_PLATE)
    for c in (-14, -7, 0, 7, 14):
        pts = bezier((c, 2, -60), (c, 2, -52), (c * .6, .1, -46), (c * .6, .1, -38), 6)
        b.add(tube(p, pts, 1.7 if c else 2.3), SC_RUBBER)
    b.cut(box(p, (0, -3, -50), (16.5, 1.6, 5.4), .6), SC_RUBBER)
    for sx in (-1, 1):
        b.add(box(np.stack((x - sx * 8, y, z), 1), (0, -3.6, -50), (6.6, .8, 3.8), .6), SC_PAINT)
    # Status lamps over the hood line.
    s = np.abs(repeat(x, 3.2, -13, 13))
    b.cut(np.maximum.reduce((s - 1, np.abs(v[:, 2] - 48.3) + 0 - .34, v[:, 1] + 3.6)), SC_LAMP)
    return b


def terminal_glow(p):
    v = rotate(p, 0, 7, (0, 0, 20))
    b = Build(p)
    b.add(box(v, (0, -2.6, 20), (19.8, .9, 26.8), .4), SC_SCREEN)
    return b


def screen_ui(u, w):
    """Station interface, drawn in screen space: u across 0..40, w up 0..54."""
    cool = np.array((.55, .8, 1), F)
    gold = np.array((1, .62, .16), F)
    col = np.zeros(u.shape + (3,), F)
    col += np.array((.008, .03, .05), F)
    col += np.array((.01, .06, .09), F) * ((np.abs(u - 20) + np.abs(w - 27)) * -.02 + 1)[..., None]
    # Grid.
    grid = (np.abs(((u + .25) % 5) - .25) < .05) | (np.abs(((w + .25) % 5) - .25) < .05)
    col += cool * grid[..., None] * .05
    # Ring and bolt emblem, top centre.
    r = hyp(u - 20, w - 37)
    ring = np.abs(r - 8) < .22
    ring2 = (np.abs(r - 9.5) < .08) & (((np.arctan2(w - 37, u - 20) * 9) % 1) < .7)
    col += gold * (ring | ring2)[..., None] * 1.1
    # Sweep of a scope inside the ring.
    t = np.arctan2(w - 37, u - 20)
    sweep = ((t + 2) % (2 * math.pi)) / (2 * math.pi)
    col += cool * ((r < 7.8) * sweep ** 6)[..., None] * .55
    # Waveform.
    wave = 13.5 + 2.6 * np.sin(u * 1.1) * np.sin(u * .23 + 1) + .7 * np.sin(u * 4.1)
    line = np.exp(-((w - wave) / .16) ** 2) * ((u > 4) & (u < 36))
    col += cool * line[..., None] * 1.0
    col += cool * ((w < wave) & (w > 9) & (u > 4) & (u < 36))[..., None] * .06
    # Bar columns.
    for i in range(9):
        cx = 7 + i * 3.25
        top = 4.8 + 2.4 * abs(math.sin(i * 1.7 + .4))
        on = (np.abs(u - cx) < 1) & (w > 3) & (w < top)
        col += (gold if i == 5 else cool)[None] * on[..., None] * .7
    return col


def terminal_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    v = rotate(a.p, 0, 7, (0, 0, 20))
    m = a.ids == SC_SCREEN
    u, w = 20 - v[m, 0] * -1, v[m, 2] + 7
    a.glow[m] = screen_ui(u, w)
    a.base[m] = np.array((.015, .03, .04), F)
    # Readable text lines on the screen; drawn on the glass plane.
    front = np.ones(m.sum(), bool)
    q = np.stack((u, 0 * u, w), 1)
    for text, ox, oz, h, colour in (('MERIDIAN STATION', 4.5, 47.5, 1.5, (.65, .88, 1)), ('POWER GRID  NOMINAL', 4.5, 25, .95, (.65, .88, 1)), ('DIVINITY  NO SIGNAL', 4.5, 22.6, .95, (1, .6, .16))):
        ink = text_plane(q, front, text, (ox, 0, oz), (1, 0, 0), (0, 0, 1), h, .1)
        a.glow[m] = a.glow[m] + ink[:, None] * np.array(colour, F)
    # Key legends: a small tick on each key.
    d = rotate(a.p, 0, -38, (0, -2, -18))
    m = a.ids == SC_KEY
    uu = repeat(d[:, 0], 3.3, -18.6, 7.8)
    ww = repeat(d[:, 2], 3.2, -29.8, -18.2)
    tick = (np.abs(uu) < .55) & (np.abs(ww - .4) < .12) & m
    a.glow[tick] = (.8, .55, .2)
    a.base[tick] = (.8, .75, .6)
    front = a.n[:, 1] < -.55
    # Hazard on the lower cowl edge.
    band = ((np.abs(z + 58) < 1.2) & (a.ids == SC_PLATE)).astype(F)
    a.layer(band * (((x + z) % 5) < 2.5) * (a.wear < .4), (.8, .52, .05), .42, 0)


prop('terminal', 'SM_Scan_Terminal', 'ScanTerminal', terminal_body, terminal_glow, ((-30, -14, -61), (30, 9, 61)), .08, 50000, SC_LOOK, terminal_paint,
     scale=3.5, grime=1.1, ao=10., curve=.18, glow_uv=2.2, views=((-70, 8, 1), (-125, 20, 1), (-90, 2, .4, (0, -6, 28))))


# ---------------------------------------------------------------- pipeline

def typical_ratio(flat, corners, area):
    """UV area per unit of surface over the whole mesh, median across a sample of faces."""
    pick = np.linspace(0, len(corners) - 1, min(4000, len(corners))).astype(int)
    values = []
    for f in pick:
        a, b, c = flat[corners[f][:3]]
        values.append(abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) * .5 / max(float(area[f]), 1e-9))
    return float(np.median(values))


def unwrap(item, glow_scale, cap, limit=58):
    """Grow charts by normal, fold slivers into their neighbours, then unwrap with seams.

    Smart Project shatters decimated bevels into dust. These charts stay large,
    so the packer spends the atlas on surface instead of on margins.
    """
    only(item)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(item.data)
    bm.faces.ensure_lookup_table()
    faces = bm.faces
    normal = np.array([f.normal for f in faces], F)
    area = np.array([f.calc_area() for f in faces], F)
    centre = np.array([f.calc_center_median() for f in faces], F)
    reach = float(np.ptp(centre, 0).max()) * cap
    links = [[] for _ in faces]
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces[0].index, e.link_faces[1].index
            links[a].append(b)
            links[b].append(a)
    chart = np.full(len(faces), -1, np.int32)
    means = []
    near, wide = math.cos(math.radians(limit)), math.cos(math.radians(limit - 2))
    for seed in np.argsort(-area):
        if chart[seed] >= 0:
            continue
        index = len(means)
        chart[seed] = index
        mean = normal[seed] * area[seed]
        stack = [seed]
        while stack:
            f = stack.pop()
            for g in links[f]:
                if chart[g] >= 0 or (faces[f].material_index != faces[g].material_index):
                    continue
                unit = mean / max(np.linalg.norm(mean), 1e-9)
                if normal[g] @ unit > near and normal[g] @ normal[f] > wide and np.abs(centre[g] - centre[seed]).max() < reach:
                    chart[g] = index
                    mean = mean + normal[g] * area[g]
                    stack.append(g)
        means.append(mean / max(np.linalg.norm(mean), 1e-9))
    means = np.array(means)
    # Merge slivers: each small chart joins the most agreeable neighbour.
    total = area.sum()
    for _ in range(4):
        sizes = np.bincount(chart, area, len(means))
        small = np.argsort(sizes)
        small = small[sizes[small] < total * .0014]
        faces_of = {}
        for f, c in enumerate(chart):
            faces_of.setdefault(int(c), []).append(f)
        for c in small:
            c = int(c)
            members = faces_of.get(c)
            if not members:
                continue
            best, score = -1, .02
            for f in members:
                for g in links[f]:
                    other = int(chart[g])
                    if other != c and faces[f].material_index == faces[g].material_index and means[c] @ means[other] > score:
                        best, score = other, means[c] @ means[other]
            if best >= 0:
                chart[members] = best
                faces_of.setdefault(best, []).extend(members)
                faces_of[c] = []
    for e in bm.edges:
        e.seam = bool(len(e.link_faces) < 2 or chart[e.link_faces[0].index] != chart[e.link_faces[1].index])
    print('  charts', len(np.unique(chart)), flush=True)
    bmesh.update_edit_mesh(item.data)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=.002)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = item.data
    uv = mesh.uv_layers.active.data
    flat = np.empty(len(uv) * 2, F)
    uv.foreach_get('uv', flat)
    flat = flat.reshape(-1, 2)
    corners = [list(poly.loop_indices) for poly in mesh.polygons]
    verts = np.array([v.co for v in mesh.vertices], F)
    order = [[l.vertex_index for l in (mesh.loops[i] for i in c)] for c in corners]
    # A chart the solver spiked out would eat the whole atlas; flatten it by projection.
    members = {}
    for f, c in enumerate(chart):
        members.setdefault(int(c), []).append(f)
    fixed = 0
    typical = typical_ratio(flat, corners, area)
    for c, group in members.items():
        loops = np.array([l for f in group for l in corners[f]])
        where = flat[loops]
        extent = where.max(0) - where.min(0)
        real = np.concatenate([verts[order[f]] for f in group])
        n = np.array(means[c], F)
        t = np.cross(n, (0, 0, 1) if abs(n[2]) < .9 else (1, 0, 0))
        t /= np.linalg.norm(t)
        b = np.cross(n, t)
        plan = np.stack((real @ t, real @ b), 1)
        span = plan.max(0) - plan.min(0)
        ratio = float(extent[0] * extent[1]) / max(float(sum(area[f] for f in group)), 1e-9)
        if ratio > typical * 30 and float(span[0] * span[1]) < extent[0] * extent[1] / typical:
            flat[loops] = plan * math.sqrt(typical)
            fixed += 1
    print('  spiked charts flattened', fixed, flush=True)
    for f, poly in enumerate(mesh.polygons):
        if glow_scale != 1 and poly.material_index == 1:
            flat[corners[f]] *= glow_scale
    uv.foreach_set('uv', flat.ravel())
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=.0024, margin_method='FRACTION', shape_method='CONVEX')
    bpy.ops.object.mode_set(mode='OBJECT')


def build(key, quality, size):
    a = PROPS[key]
    start = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.use_denoising = False
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 24
    voxel = a['voxel'] * quality
    lo, hi = a['bounds']
    slots = [bpy.data.materials.new('M_%s_Body' % a['short']), bpy.data.materials.new('M_%s_Glow' % a['short'])]
    for mat in slots:
        mat.use_nodes = True
    samplers = []
    high, low = [], []
    for index, (field, tag) in enumerate(((a['body'], 'body'), (a['glow'], 'glow'))):
        if field is None:
            continue
        print(key, tag, flush=True)
        grid, origin = sample(field, lo, hi, voxel)
        verts, quads = surface_nets(grid, origin, voxel)
        print('  sculpt %d quads  %.0fs' % (len(quads), time.time() - start), flush=True)
        samplers.append((field, Trilinear(grid, origin, voxel)))
        l = mesh_from('lo_' + tag, verts, quads, slots[index])
        share = a['tris'] if index == 0 else a['tris'] * .08 + 1500
        decimate(l, share * (.92 if index == 0 else 1))
        tidy(l, Trilinear(grid, origin, voxel), voxel)
        low.append(l)
    bpy.ops.object.select_all(action='DESELECT')
    for item in low:
        item.select_set(True)
    bpy.context.view_layer.objects.active = low[0]
    bpy.ops.object.join()
    low_item = bpy.context.object
    low_item.name = a['name']
    low_item.data.name = a['name']
    print('  low %d tris  %.0fs' % (sum(len(f.vertices) - 2 for f in low_item.data.polygons), time.time() - start), flush=True)

    # Normals: hard above 52 degrees, weighted by face area below.
    only(low_item)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(a['sharp']), keep_sharp_edges=True)
    mod = low_item.modifiers.new('wn', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    mod.weight = 60
    bpy.ops.object.modifier_apply(modifier=mod.name)
    unwrap(low_item, a['glow_uv'], a['cap'])
    print('  unwrapped  %.0fs' % (time.time() - start), flush=True)

    # Rasterise the game mesh into the atlas, then land every texel on the true
    # surface by following the field. No rays, so nothing can miss or hit a neighbour.
    lo_a, hi_a = np.array(lo, F), np.array(hi, F)
    extent = hi_a - lo_a
    results = {tag: bake_own(low_item, tag, size, lo_a, extent) for tag in ('pos', 'nor', 'tan', 'shell')}
    print('  rasterised  %.0fs' % (time.time() - start), flush=True)
    covered = results['shell'][..., 1] > .5
    repair(results, covered, lo_a, extent, samplers, voxel)
    index = np.nonzero(covered)
    P = (results['pos'][index][:, :3] * extent + lo_a).astype(F)
    smooth = results['nor'][index][:, :3] * 2 - 1
    tangent = results['tan'][index][:, :3] * 2 - 1
    shell = (results['shell'][index][:, 0] > .5).astype(np.int32)
    if len(samplers) == 1:
        shell[:] = 0

    N = np.zeros_like(P)
    ids = np.zeros(len(P), np.int32)
    curve = np.zeros(len(P), F)
    step = a['curve']
    for k, (field, sampler) in enumerate(samplers):
        m = shell == k
        near = project(sampler, P[m], voxel)
        P[m] = near
        N[m] = gradient(sampler, near, voxel * .75)
        curve[m] = curvature(sampler, near, step) * .7 + curvature(sampler, near, step * 2.6) * .6

        part = shared(len(near), np.int32)

        def identify(i):
            part[i * 60000:(i + 1) * 60000] = field(near[i * 60000:(i + 1) * 60000]).id
        forked(len(near) // 60000 + 1, identify)
        ids[m] = part
    print('  surface  %.0fs' % (time.time() - start), flush=True)
    AO = field_occlusion(lambda q: np.minimum.reduce([s_(q) for _, s_ in samplers]), P, N, a['ao'])
    print('  occlusion  %.0fs' % (time.time() - start), flush=True)

    paint = Paint(P, N, AO, curve, ids, a['look'], a['scale'])
    paint.materials()
    if a['paint']:
        a['paint'](paint)
    paint.grime(a['grime'])
    paint.edge_light()
    paint.scratches()
    print('  painted  %.0fs' % (time.time() - start), flush=True)

    def image_of(values, default):
        out = np.full((size, size) + np.shape(default), default, F)
        out[index] = values
        return out

    # Detail height joins the baked normal in UV space.
    H = image_of(paint.height, 0.)
    px = np.zeros((size, size, 3), F)
    px[index] = P
    gx = np.roll(px, -1, 1) - np.roll(px, 1, 1)
    gy = np.roll(px, -1, 0) - np.roll(px, 1, 0)
    span = np.median(hyp(*gx[index].T)) / 2
    joined_x = hyp(gx[..., 0], gx[..., 1], gx[..., 2]) < span * 8
    joined_y = hyp(gy[..., 0], gy[..., 1], gy[..., 2]) < span * 8
    dx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * joined_x / (2 * span)
    dy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * joined_y / (2 * span)
    # Tangent space of the exact field normal, on the mesh's own Mikk frame.
    smooth /= np.maximum(hyp(*smooth.T), 1e-5)[:, None]
    tangent = tangent - smooth * (tangent * smooth).sum(1)[:, None]
    tangent /= np.maximum(hyp(*tangent.T), 1e-5)[:, None]
    bitangent = np.cross(smooth, tangent)
    ts = np.zeros((size, size, 3), F)
    ts[..., 2] = 1
    ts[index] = np.stack(((N * tangent).sum(1), (N * bitangent).sum(1), (N * smooth).sum(1)), 1)
    ts[..., 0] -= dx * covered
    ts[..., 1] += dy * covered
    ts /= np.maximum(hyp(ts[..., 0], ts[..., 1], ts[..., 2]), 1e-5)[..., None]
    ts = ts * .5 + .5
    ts[..., 1] = 1 - ts[..., 1]  # DirectX, green down
    ts[~covered] = (.5, .5, 1)

    TEXTURES.mkdir(parents=True, exist_ok=True)
    MESHES.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    stem = 'T_%s_' % a['short']
    write_png(TEXTURES / (stem + 'BaseColor.png'), image_of(paint.base, (.2, .2, .2)))
    write_png(TEXTURES / (stem + 'Normal.png'), ts, 16)
    orm = np.stack((image_of(AO, 1.), image_of(paint.rough, .5), image_of(paint.metal, 0.)), -1)
    write_png(TEXTURES / (stem + 'ORM.png'), orm)
    write_png(TEXTURES / (stem + 'Emissive.png'), image_of(paint.glow, (0, 0, 0)))
    print('  textures  %.0fs' % (time.time() - start), flush=True)

    bpy.ops.object.select_all(action='DESELECT')
    only(low_item)
    if a['final'] != 1:
        # Length is set here so the sculpt keeps its authored proportions and origin.
        low_item.scale = (a['final'],) * 3
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.export_scene.fbx(filepath=str(MESHES / (a['name'] + '.fbx')), use_selection=True, axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, mesh_smooth_type='FACE', use_tspace=True, add_leaf_bones=False)
    bounds = np.array([low_item.matrix_world @ v.co for v in low_item.data.vertices])
    print('RESULT', key, a['name'], 'tris', sum(len(f.vertices) - 2 for f in low_item.data.polygons),
          'min', bounds.min(0).round(2).tolist(), 'max', bounds.max(0).round(2).tolist(),
          'slots', [m.name for m in low_item.data.materials], '%.0fs' % (time.time() - start), flush=True)


# ---------------------------------------------------------------- review sheet

def preview_material(mat, short):
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    pr = tree.nodes.new('ShaderNodeBsdfPrincipled')
    tree.links.new(pr.outputs[0], out.inputs['Surface'])

    def tex(suffix, srgb_=False):
        node = tree.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(str(TEXTURES / ('T_%s_%s.png' % (short, suffix))), check_existing=True)
        node.image.colorspace_settings.name = 'sRGB' if srgb_ else 'Non-Color'
        return node

    tree.links.new(tex('BaseColor', True).outputs[0], pr.inputs['Base Color'])
    sep = tree.nodes.new('ShaderNodeSeparateColor')
    tree.links.new(tex('ORM').outputs[0], sep.inputs[0])
    tree.links.new(sep.outputs[1], pr.inputs['Roughness'])
    tree.links.new(sep.outputs[2], pr.inputs['Metallic'])
    # Unreal green-down back to Blender green-up for this preview only.
    nor = tex('Normal')
    split = tree.nodes.new('ShaderNodeSeparateColor')
    tree.links.new(nor.outputs[0], split.inputs[0])
    inv = tree.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1
    tree.links.new(split.outputs[1], inv.inputs[1])
    join = tree.nodes.new('ShaderNodeCombineColor')
    tree.links.new(split.outputs[0], join.inputs[0])
    tree.links.new(inv.outputs[0], join.inputs[1])
    tree.links.new(split.outputs[2], join.inputs[2])
    mapping = tree.nodes.new('ShaderNodeNormalMap')
    tree.links.new(join.outputs[0], mapping.inputs['Color'])
    tree.links.new(mapping.outputs[0], pr.inputs['Normal'])
    tree.links.new(tex('Emissive', True).outputs[0], pr.inputs['Emission Color'])
    pr.inputs['Emission Strength'].default_value = 1.7


def studio(size):
    world = bpy.data.worlds.new('w')
    bpy.context.scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    bg = tree.nodes['Background']
    coord = tree.nodes.new('ShaderNodeTexCoord')
    sep = tree.nodes.new('ShaderNodeSeparateXYZ')
    r = tree.nodes.new('ShaderNodeValToRGB')
    r.color_ramp.elements[0].position = .3
    r.color_ramp.elements[0].color = (.05, .055, .065, 1)
    r.color_ramp.elements[1].position = .85
    r.color_ramp.elements[1].color = (.52, .56, .62, 1)
    m = tree.nodes.new('ShaderNodeMapRange')
    m.inputs['From Min'].default_value = -1
    tree.links.new(coord.outputs['Generated'], sep.inputs[0])
    tree.links.new(sep.outputs[2], m.inputs['Value'])
    tree.links.new(m.outputs[0], r.inputs['Fac'])
    tree.links.new(r.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1

    def light(name, power, colour, loc, area):
        data = bpy.data.lights.new(name, 'AREA')
        data.size = area * size
        data.energy = power * size * size
        data.color = colour
        item = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(item)
        item.location = np.array(loc) * size
        direction = -np.array(item.location)
        from mathutils import Vector
        item.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
        return item

    return (light('key', 70, (1, .96, .9), (-.9, -1.3, 1.5), 1.1), light('fill', 12, (.72, .82, 1), (1.7, -.8, .3), 2.2),
            light('rim', 110, (.86, .92, 1), (.7, 1.5, .9), .7), light('kick', 26, (1, .82, .62), (-.6, 1.1, -.9), .8))


# Art-director angles: harsh close-ups the contact sheet never shows.
CLOSEUPS = {
    'gun': ((-78, 8, .26, (7, 0, 6.2)), (102, 8, .26, (7, 0, 6.2)), (-140, 20, .26, (-4, 0, 6.5)), (-100, 4, .28, (-3, 0, -2)), (-20, 55, .3, (12, 0, 7)), (180, 5, .3, (-4, 0, 3))),
    'drone': ((-30, 20, .32, (20, 0, 4)), (-110, 35, .36, (0, -10, 10)), (160, 30, .36, (-20, 0, 8)), (-70, -40, .4, (0, 0, -8)), (10, 5, .24, (32, 0, 2)), (60, 50, .36, (0, 25, 0))),
    'health': ((-70, 8, .4, (0, 0, 0)), (20, 40, .4, (0, 0, 12)), (-30, -30, .45, (0, 0, -10))),
    'divinity': ((-60, 10, .36, (0, 0, 2)), (60, 40, .36, (0, 0, 14)), (200, -25, .4, (0, 0, -14)), (100, 0, .24, (0, 0, 0))),
    'ammo': ((-50, 10, .4, (0, 0, 2)), (30, 50, .4, (0, 0, 14)), (-20, -20, .4, (0, 0, -14))),
    'conduit': ((-100, 15, .3, (15, -7, 0)), (-80, 10, .3, (-18, -5, 0)), (-90, 20, .3, (0, 0, 44)), (-60, 25, .3, (22, -2, -30))),
    'terminal': ((-90, 5, .36, (0, -8, 25)), (-80, 20, .36, (0, -8, -35)), (-40, 15, .36, (20, 0, 0))),
}


def render_sheet(keys, per_row=5, tile=(576, 432), spp=64, closeups=False):
    tiles = []
    folder = REVIEW / '_tiles'
    folder.mkdir(parents=True, exist_ok=True)
    for key in keys:
        a = PROPS[key]
        path = MESHES / (a['name'] + '.fbx')
        if not path.exists():
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = spp
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        scene.render.film_transparent = True
        scene.render.resolution_x, scene.render.resolution_y = tile
        scene.render.threads_mode = 'FIXED'
        scene.render.threads = 24
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Medium High Contrast'
        scene.render.image_settings.file_format = 'PNG'
        bpy.ops.import_scene.fbx(filepath=str(path), axis_forward='-Z', axis_up='Y')
        item = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
        for mat in item.data.materials:
            mat.use_nodes = True
            preview_material(mat, a['short'])
        points = np.array([item.matrix_world @ v.co for v in item.data.vertices])
        lo, hi = points.min(0), points.max(0)
        centre = (lo + hi) / 2
        size = float(np.linalg.norm(hi - lo))
        print('review', key, [round(float(v), 2) for v in hi - lo], flush=True)
        studio(size)
        camera = bpy.data.cameras.new('c')
        camera.lens = 85
        camera.clip_start = size * .02
        camera.clip_end = size * 30
        eye = bpy.data.objects.new('c', camera)
        bpy.context.collection.objects.link(eye)
        scene.camera = eye
        from mathutils import Vector
        for n, view in enumerate(CLOSEUPS[key] if closeups else a['views']):
            az, el, zoom = view[:3]
            focus = np.array(view[3], float) if len(view) > 3 else centre
            az_, el_ = math.radians(az), math.radians(el)
            direction = np.array((math.cos(az_) * math.cos(el_), math.sin(az_) * math.cos(el_), math.sin(el_)))
            span = hi - lo
            flat = float(np.linalg.norm(span[:2])) / (2 * .2118)
            tall = float(span[2]) / (2 * .1588)
            eye.location = focus + direction * max(flat, tall) * 1.14 * zoom
            eye.rotation_euler = Vector(-direction).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(folder / ('%s_%d.png' % (key, n)))
            bpy.ops.render.render(write_still=True)
            tiles.append(scene.render.filepath)
    if not tiles:
        return
    rows = math.ceil(len(tiles) / per_row)
    sheet = np.zeros((rows * tile[1], per_row * tile[0], 3), F)
    sheet[...] = (.05, .055, .065)
    for n, file in enumerate(tiles):
        image = bpy.data.images.load(file)
        data = np.empty(tile[0] * tile[1] * 4, F)
        image.pixels.foreach_get(data)
        data = data.reshape(tile[1], tile[0], 4)[::-1]
        y, x = n // per_row * tile[1], n % per_row * tile[0]
        # Soft floor glow behind the render keeps silhouettes readable.
        yy, xx = np.mgrid[0:tile[1], 0:tile[0]]
        vignette = np.exp(-(((xx - tile[0] / 2) / (tile[0] * .55)) ** 2 + ((yy - tile[1] / 2) / (tile[1] * .55)) ** 2))[..., None]
        back = np.array((.07, .078, .092), F) + np.array((.11, .12, .14), F) * vignette
        sheet[y:y + tile[1], x:x + tile[0]] = data[..., :3] * data[..., 3:] + back * (1 - data[..., 3:])
        bpy.data.images.remove(image)
    stem = 'props_ad' if closeups else 'props'
    write_png(REVIEW / ('%s_%s.png' % (stem, keys[0])) if len(keys) == 1 else REVIEW / (stem + '.png'), sheet)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    quality, size = 1., 2048
    sheet = render = True
    close = False
    keys = []
    i = 0
    while i < len(args):
        if args[i] == '--q':
            quality = float(args[i + 1])
            i += 1
        elif args[i] == '--size':
            size = int(args[i + 1])
            i += 1
        elif args[i] == '--sheet':
            sheet = False
        elif args[i] == '--closeups':
            sheet, close = False, True
        elif args[i] == '--norender':
            render = False
        else:
            keys.append(args[i])
        i += 1
    keys = keys or list(PROPS)
    if sheet:
        for key in keys:
            build(key, quality, size)
    if render:
        render_sheet(keys, closeups=close, per_row=4 if close else 5, tile=(720, 540) if close else (576, 432))


main()
