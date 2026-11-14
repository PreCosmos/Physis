"""Meridian Station modular interior kit: procedural mid-poly meshes, masks and previews.

Run:
  flatpak run org.blender.Blender -b --python Tools/build_physis_kit.py -- [--only A,B] [--no-bake]
                                  [--no-render] [--no-cells] [--no-export] [--no-textures] [--samples 48] [--cell 900] [--room]

Writes Art/Meshes/Kit/SM_Kit_*.fbx, Art/Meshes/Kit/Textures/T_Kit*.png, Art/Review/kit.png, Art/Review/kit_room.png.
UV0 = world-scale tiling coordinates; UV1 = unique unwrap for the baked mask and lightmaps.
Vertex colour: R = bevel/edge flag, G = per-part random, B = paint scheme for M_Wall and M_Ceiling
(1 = station grey, .5 = bone, 0 = cargo olive; compare against .1 and .9 so sRGB handling cannot change the result).
Mask textures: R = occlusion, G = edge wear, B = grime.
Pivots and facing are listed on each builder. Wall pieces face Blender -Y from a back plane at y=0.
"""
import argparse
import math
import struct
import sys
import time
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, noise

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Art/Meshes/Kit'
TEX = OUT / 'Textures'
REVIEW = ROOT / 'Art/Review'
MATERIALS = ROOT / 'Art/Materials'
SKY = ROOT / 'Art/UI/T_Sky_Space.png'

# Slot order is stable; a mesh lists only the slots it uses, in this order.
SLOTS = ('M_Wall', 'M_Trim', 'M_Composite', 'M_Deck', 'M_Ceiling', 'M_Hazard', 'M_Rubber', 'M_Foam',
         'M_Light', 'M_Screen', 'M_Decal', 'M_Glass', 'M_Space')
# Centimetres per UV unit on UV0, for each tiling set.
# These equal the physical tile of each set in Tools/build_physis_materials.py.
TILE = {'M_Wall': 180, 'M_Trim': 120, 'M_Composite': 60, 'M_Deck': 160, 'M_Ceiling': 180, 'M_Hazard': 100,
        'M_Rubber': 60, 'M_Foam': 140, 'M_Light': 60, 'M_Glass': 400, 'M_Space': 1600}
SETS = {'M_Wall': 'T_KitPaint', 'M_Trim': 'T_KitMetal', 'M_Composite': 'T_DarkComposite', 'M_Deck': 'T_DeckPlate',
        'M_Ceiling': 'T_KitPaint', 'M_Hazard': 'T_HazardPaint', 'M_Foam': 'T_KitFoam'}
MASK_SIZE = {'SM_Kit_WallPanel': 2048, 'SM_Kit_BlastDoor': 2048, 'SM_Kit_HullBreach': 2048, 'SM_Kit_DoorFrame': 2048,
             'SM_Kit_CrateLarge': 2048, 'SM_Kit_CrateSmall': 2048, 'SM_Kit_Console': 2048, 'SM_Kit_WeaponRack': 2048}
GREY, BONE, CARGO = 1.0, .5, 0.0  # vertex-colour B, see the module docstring
PAINT = {GREY: (.21, .25, .30), BONE: (.62, .60, .53), CARGO: (.17, .20, .13)}


# ---------------------------------------------------------------------------------------------- PNG

def write_png(path, data, bits=8):
    """Write a float array (h, w, channels) in 0..1, top row first, with no colour management."""
    data = np.clip(data, 0, 1)
    h, w, c = data.shape
    if bits == 16:
        raw = (data * 65535 + .5).astype('>u2')
    else:
        raw = (data * 255 + .5).astype(np.uint8)
    rows = np.zeros((h, 1 + w * c * (bits // 8)), np.uint8)
    rows[:, 1:] = np.frombuffer(raw.tobytes(), np.uint8).reshape(h, -1)
    ctype = {1: 0, 3: 2, 4: 6}[c]

    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body))
    blob = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, bits, ctype, 0, 0, 0))
    blob += chunk(b'IDAT', zlib.compress(rows.tobytes(), 6)) + chunk(b'IEND', b'')
    Path(path).write_bytes(blob)


# --------------------------------------------------------------------------------- transform helpers

def T(x=0, y=0, z=0):
    return Matrix.Translation((x, y, z))


def Rx(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'X')


def Ry(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Y')


def Rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def S(x=1, y=1, z=1):
    return Matrix.Diagonal((x, y, z, 1))


def aim(pos, direction):
    """Matrix placing local +Z along direction at pos."""
    d = Vector(direction).normalized()
    return T(*pos) @ Vector((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()


def crect(a0, b0, a1, b1, c=0.0):
    """Chamfered rectangle, counter-clockwise; c is a size or (bl, br, tr, tl)."""
    bl, br, tr, tl = (c, c, c, c) if not isinstance(c, (tuple, list)) else c
    pts = []
    for corner, size, first, second in (((a0, b0), bl, (0, 1), (1, 0)), ((a1, b0), br, (-1, 0), (0, 1)),
                                        ((a1, b1), tr, (0, -1), (-1, 0)), ((a0, b1), tl, (1, 0), (0, -1))):
        if size > 0:
            pts.append((corner[0] + first[0] * size, corner[1] + first[1] * size))
            pts.append((corner[0] + second[0] * size, corner[1] + second[1] * size))
        else:
            pts.append(corner)
    return pts


def poly_area(pts):
    return .5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))


def offset_poly(pts, d):
    """Miter offset; positive grows a counter-clockwise polygon."""
    out = []
    n = len(pts)
    for i in range(n):
        p, a, b = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = Vector((a[0] - p[0], a[1] - p[1])).normalized()
        e2 = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        n1, n2 = Vector((e1.y, -e1.x)), Vector((e2.y, -e2.x))
        bis = n1 + n2
        if bis.length < 1e-5:
            bis = n1
        bis.normalize()
        k = 1 / max(.3, bis.dot(n1))
        out.append((a[0] + bis.x * d * k, a[1] + bis.y * d * k))
    return out


def fillet(points, radius, steps=4):
    """Replace interior corners of a polyline by arcs."""
    if radius <= 0 or len(points) < 3:
        return [Vector(p) for p in points]
    pts = [Vector(p) for p in points]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        u, v = (a - b), (c - b)
        lu, lv = u.length, v.length
        u.normalize()
        v.normalize()
        turn = u.angle(v)
        if turn > math.pi - .02:
            out.append(b)
            continue
        cut = min(radius / math.tan(turn / 2), lu * .48, lv * .48)
        s, e = b + u * cut, b + v * cut
        for j in range(steps + 1):
            t = j / steps
            out.append(s * (1 - t) ** 2 + b * 2 * t * (1 - t) + e * t ** 2)
    out.append(pts[-1])
    return out


# ------------------------------------------------------------------------------------- mesh building

class Kit:
    """Collects parts into one mesh. Each part is bevelled and UV-projected in its own local space."""

    def __init__(self, name, seed=1):
        self.name = name
        self.V, self.F, self.FM = [], [], []
        self.UV, self.EDGE, self.PID, self.TONE = [], [], [], []
        self.paint = GREY
        self.stack = [Matrix.Identity(4)]
        self.rng = np.random.default_rng(seed)
        self.parts = 0

    class _At:
        def __init__(self, kit, m):
            self.kit, self.m = kit, m

        def __enter__(self):
            self.kit.stack.append(self.kit.stack[-1] @ self.m)

        def __exit__(self, *_):
            self.kit.stack.pop()

    class _Paint:
        def __init__(self, kit, tone):
            self.kit, self.tone = kit, tone

        def __enter__(self):
            self.prev, self.kit.paint = self.kit.paint, self.tone

        def __exit__(self, *_):
            self.kit.paint = self.prev

    def at(self, m):
        return Kit._At(self, m)

    def painted(self, tone):
        return Kit._Paint(self, tone)

    # -- primitive assembly
    def commit(self, bm, mat, bevel=0.0, segs=2, angle=35.0, align=False, uv='box', edge=0.0, tile=None, fix=True):
        bm.normal_update()
        if fix:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.normal_update()
        flag = bm.faces.layers.int.new('bev')
        if bevel > 0:
            limit = math.radians(angle)
            edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0) > limit]
            result = bmesh.ops.bevel(bm, geom=edges, offset=bevel, offset_type='OFFSET', profile_type='SUPERELLIPSE',
                                     segments=segs, profile=.5, affect='EDGES', clamp_overlap=True, loop_slide=True,
                                     harden_normals=False, miter_outer='SHARP', miter_inner='SHARP',
                                     vmesh_method='ADJ', spread=.1)
            for f in result['faces']:
                f[flag] = 1
            bm.normal_update()
        uvl = bm.loops.layers.uv.verify()
        size = tile or TILE.get(mat, 100)
        if uv == 'box':
            cos = np.array([v.co for v in bm.verts])
            span = cos.max(0) - cos.min(0)
            ou, ov = (0, 0) if align else self.rng.uniform(0, 1, 2)
            for f in bm.faces:
                a = int(np.argmax([abs(c) for c in f.normal]))
                axes = [i for i in (0, 1, 2) if i != a]
                if span[axes[1]] > span[axes[0]]:
                    axes.reverse()
                for loop in f.loops:
                    loop[uvl].uv = (loop.vert.co[axes[0]] / size + ou, loop.vert.co[axes[1]] / size + ov)
        m = self.stack[-1]
        flip = m.to_3x3().determinant() < 0
        base = len(self.V)
        bm.verts.index_update()
        slot = SLOTS.index(mat)
        pid = float(self.rng.uniform())
        for v in bm.verts:
            self.V.append(tuple(m @ v.co))
        for f in bm.faces:
            loops = list(f.loops)
            if flip:
                loops.reverse()
            self.F.append([base + loop.vert.index for loop in loops])
            self.FM.append(slot)
            e = max(edge, float(f[flag]))
            for loop in loops:
                self.UV.append(tuple(loop[uvl].uv))
                self.EDGE.append(e)
                self.PID.append(pid)
                self.TONE.append(self.paint)
        bm.free()
        self.parts += 1

    def box(self, x0, x1, y0, y1, z0, z1, mat='M_Trim', bevel=.6, segs=2, align=False, edge=0.0):
        bm = bmesh.new()
        c = [(x, y, z) for x in (min(x0, x1), max(x0, x1)) for y in (min(y0, y1), max(y0, y1)) for z in (min(z0, z1), max(z0, z1))]
        vs = [bm.verts.new(p) for p in c]
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            bm.faces.new([vs[i] for i in q])
        self.commit(bm, mat, bevel, segs, align=align, edge=edge)

    @staticmethod
    def _pt(plane, a, b, c):
        return {'XZ': (a, c, b), 'XY': (a, b, c), 'YZ': (c, a, b)}[plane]

    def plate(self, outline, c0, c1, mat='M_Wall', bevel=.8, segs=2, plane='XZ', taper=0.0, align=False, edge=0.0):
        """Extrude a polygon from c0 to c1 along the plane normal; c1's face is inset by taper."""
        pts = list(outline)
        if poly_area(pts) < 0:
            pts.reverse()
        top = offset_poly(pts, -taper) if taper else pts
        bm = bmesh.new()
        a = [bm.verts.new(self._pt(plane, p[0], p[1], c0)) for p in pts]
        b = [bm.verts.new(self._pt(plane, p[0], p[1], c1)) for p in top]
        bm.faces.new(a)
        bm.faces.new(list(reversed(b)))
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
        self.commit(bm, mat, bevel, segs, align=align, edge=edge)

    def ring(self, outer, inner, c0, c1, mat='M_Trim', bevel=.8, segs=2, plane='XZ', taper=0.0, align=False):
        """A frame between two polygons of equal point count."""
        o, i = list(outer), list(inner)
        if poly_area(o) < 0:
            o.reverse()
            i.reverse()
        ot = offset_poly(o, -taper) if taper else o
        it = offset_poly(i, taper) if taper else i
        bm = bmesh.new()
        ob = [bm.verts.new(self._pt(plane, p[0], p[1], c0)) for p in o]
        ib = [bm.verts.new(self._pt(plane, p[0], p[1], c0)) for p in i]
        of = [bm.verts.new(self._pt(plane, p[0], p[1], c1)) for p in ot]
        jf = [bm.verts.new(self._pt(plane, p[0], p[1], c1)) for p in it]
        n = len(o)
        for s in range(n):
            t = (s + 1) % n
            bm.faces.new((ob[s], ob[t], of[t], of[s]))
            bm.faces.new((of[s], of[t], jf[t], jf[s]))
            bm.faces.new((jf[s], jf[t], ib[t], ib[s]))
            bm.faces.new((ib[s], ib[t], ob[t], ob[s]))
        self.commit(bm, mat, bevel, segs, align=align)

    def tube(self, points, r, mat='M_Trim', sides=12, rad=0.0, caps=True, steps=5, tile=None, rf=None):
        """Sweep a circle along a polyline with filleted corners. U runs along the length."""
        pts = fillet(points, rad, steps)
        clean = [pts[0]]
        for p in pts[1:]:
            if (p - clean[-1]).length > 1e-3:
                clean.append(p)
        pts = clean
        tang = []
        for i in range(len(pts)):
            d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
            tang.append(d.normalized())
        up = Vector((0, 0, 1)) if abs(tang[0].z) < .9 else Vector((1, 0, 0))
        n = (up - tang[0] * up.dot(tang[0])).normalized()
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.verify()
        rings = []
        length = [0.0]
        size = tile or TILE[mat]
        for i, p in enumerate(pts):
            if i:
                length.append(length[-1] + (p - pts[i - 1]).length)
                rot = tang[i - 1].rotation_difference(tang[i])
                n = (rot @ n)
                n = (n - tang[i] * n.dot(tang[i])).normalized()
            b = tang[i].cross(n)
            radius = rf(i / (len(pts) - 1)) * r if rf else r
            rings.append([bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * radius)
                          for a in [2 * math.pi * s / sides for s in range(sides)]])
        round_v = 2 * math.pi * r / size
        for i in range(len(pts) - 1):
            for s in range(sides):
                t = (s + 1) % sides
                f = bm.faces.new((rings[i][s], rings[i + 1][s], rings[i + 1][t], rings[i][t]))
                uvs = ((length[i], s), (length[i + 1], s), (length[i + 1], s + 1), (length[i], s + 1))
                for loop, (u, q) in zip(f.loops, uvs):
                    loop[uvl].uv = (u / size, q / sides * round_v)
        if caps:
            for rng in (rings[0], rings[-1]):
                f = bm.faces.new(rng)
                for loop in f.loops:
                    q = loop.vert.co - pts[0]
                    loop[uvl].uv = (q.x / size, q.y / size)
        self.commit(bm, mat, 0, uv='keep', edge=0)

    def lathe(self, profile, mat='M_Trim', sides=20, bevel=0.0, segs=1, edge=0.0):
        """Revolve (r, z) around local Z; ends are capped."""
        bm = bmesh.new()
        rings = []
        for r, z in profile:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * s / sides), r * math.sin(2 * math.pi * s / sides), z))
                          for s in range(sides)])
        for a, b in zip(rings, rings[1:]):
            for s in range(sides):
                t = (s + 1) % sides
                bm.faces.new((a[s], a[t], b[t], b[s]))
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
        self.commit(bm, mat, bevel, segs, angle=38, edge=edge)

    def bolt(self, pos, direction=(0, -1, 0), r=1.5, h=1.2, mat='M_Trim'):
        with self.at(aim(pos, direction)):
            self.lathe([(r * 1.35, 0), (r * 1.35, h * .25), (r, h * .3), (r, h * .85), (r * .8, h)], mat, sides=6, edge=.7)

    def bolts(self, points, direction=(0, -1, 0), r=1.5, h=1.2):
        for p in points:
            self.bolt(p, direction, r, h)

    def quad(self, pts, mat, rect=(0, 0, 1, 1)):
        """A single-sided quad, used for screens and decals. rect is u0, v0, u1, v1."""
        bm = bmesh.new()
        vs = [bm.verts.new(p) for p in pts]
        f = bm.faces.new(vs)
        uvl = bm.loops.layers.uv.verify()
        u0, v0, u1, v1 = rect
        for loop, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
            loop[uvl].uv = uv
        m = self.stack[-1]
        flip = m.to_3x3().determinant() < 0
        self.commit(bm, mat, 0, uv='keep', fix=False) if not flip else bm.free()

    def decal(self, cell, x, z, w, y=-.1, mirror=False, h=None):
        """A decal card facing -Y in the current frame; cell is (col, row) in the 4x4 atlas."""
        h = h if h is not None else w
        col, row = cell
        rect = (col / 4, 1 - (row + 1) / 4, (col + 1) / 4, 1 - row / 4)
        self.quad([(x - w / 2, y, z - h / 2), (x + w / 2, y, z - h / 2), (x + w / 2, y, z + h / 2), (x - w / 2, y, z + h / 2)], 'M_Decal', rect)

    def screen(self, cell, a, b, c, d):
        """Screen quad a-b-c-d (bottom left, bottom right, top right, top left); cell in the 3x3 atlas."""
        col, row = cell
        self.quad((a, b, c, d), 'M_Screen', (col / 3, 1 - (row + 1) / 3, (col + 1) / 3, 1 - row / 3))

    def mesh_part(self, verts, faces, mat, tile=None):
        bm = bmesh.new()
        vs = [bm.verts.new(v) for v in verts]
        bm.verts.index_update()
        for f in faces:
            try:
                bm.faces.new([vs[i] for i in f])
            except ValueError:
                pass
        self.commit(bm, mat, 0, tile=tile, fix=False)

    # -- finishing
    def finish(self):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata(self.V, [], self.F)
        me.update()
        used = [s for s in SLOTS if SLOTS.index(s) in set(self.FM)]
        remap = {SLOTS.index(s): i for i, s in enumerate(used)}
        for s in used:
            me.materials.append(bpy.data.materials.get(s) or bpy.data.materials.new(s))
        me.polygons.foreach_set('material_index', [remap[i] for i in self.FM])
        uv = me.uv_layers.new(name='UVMap')
        uv.data.foreach_set('uv', np.array(self.UV, np.float32).ravel())
        col = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        c = np.ones((len(self.EDGE), 4), np.float32)
        c[:, 0], c[:, 1], c[:, 2] = self.EDGE, self.PID, self.TONE
        col.data.foreach_set('color', c.ravel())
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
        limit = math.radians(42)
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            e.smooth = not (e.is_manifold and e.calc_face_angle(0) > limit) if e.is_manifold else False
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        mod = ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
        mod.mode = 'FACE_AREA'
        mod.weight = 100
        mod.keep_sharp = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        # Second channel: a unique unwrap for masks and lightmaps.
        mask = me.uv_layers.new(name='UVMask')
        me.uv_layers.active = mask
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=.004, area_weight=0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        me.uv_layers.active = me.uv_layers['UVMap']
        me.uv_layers['UVMap'].active_render = True
        return ob


def ibeam(k, x0, x1, z0, z1, y0, y1, mat='M_Trim', web=.22, flange=.16, bevel=.4):
    """I-section with its length along Y, in an XZ profile."""
    w, h = x1 - x0, z1 - z0
    tw, tf = w * web / 2, h * flange
    mx = (x0 + x1) / 2
    pts = [(x0, z0), (x1, z0), (x1, z0 + tf), (mx + tw, z0 + tf), (mx + tw, z1 - tf), (x1, z1 - tf), (x1, z1), (x0, z1),
           (x0, z1 - tf), (mx - tw, z1 - tf), (mx - tw, z0 + tf), (x0, z0 + tf)]
    k.plate(pts, y0, y1, mat, bevel, 1)


def slats(k, x0, x1, z0, z1, y, n, mat='M_Trim', depth=5.0, tilt=38):
    """Louvred blades across a rectangle, in front of a dark cavity."""
    pitch = (z1 - z0) / n
    for i in range(n):
        z = z0 + pitch * (i + .5)
        with k.at(T(0, y, z) @ Rx(tilt)):
            k.box(x0, x1, -depth / 2, depth / 2, -.45, .45, mat, .15, 1)


def clamp(k, pos, r, axis='X', mat='M_Trim', width=5.0, foot=None):
    """Pipe saddle: a ring around a pipe plus a stand-off foot running to `foot` along +Y."""
    d = {'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[axis]
    with k.at(aim(pos, d)):
        k.lathe([(r + .9, -width / 2), (r + 1.5, -width / 2 + .5), (r + 1.5, width / 2 - .5), (r + .9, width / 2)], mat, 18, edge=.6)
    if foot is not None:
        p = Vector(pos)
        k.box(p.x - width / 2 if axis != 'Y' else p.x - 3, p.x + width / 2 if axis != 'Y' else p.x + 3, p.y + r, foot, p.z - 3.2, p.z + 3.2, mat, .4, 1)
        k.box(p.x - width, p.x + width, foot - 1.4, foot, p.z - 6, p.z + 6, mat, .4, 1)
        k.bolts([(p.x + s * width * .65, foot - 1.4, p.z) for s in (-1, 1)], r=1.0, h=.9)


# ----------------------------------------------------------------------------------------- the kit

def half_rib(k, x, sign):
    """Half of a structural rib at a module seam, so adjacent modules make one full rib."""
    out = [(0, 0), (30, 0), (30, -8), (20, -20), (20, -36), (0, -36)]
    k.plate([(x + sign * a, b) for a, b in out], 0, 450, 'M_Wall', 1.6, 2, plane='XY', align=True)
    # Dark inlay along the rib's face, with a raised centre strap that bolts through it.
    k.box(x + sign * 0, x + sign * 11, -36.6, -34, 62, 388, 'M_Composite', .3, 1)
    for a in (0, 1):
        z0, z1 = (0, 66) if a == 0 else (384, 450)
        gus = [(0, 0), (0, 66), (-36, 66), (-60, 26), (-60, 0)] if a == 0 else [(0, 0), (0, 66), (-60, 66), (-60, 40), (-36, 0)]
        for off, thick in ((4.0, 3.0), (20.0, 3.0)):
            x0 = x + sign * off
            with k.at(T(0, 0, z0)):
                k.plate(gus, x0, x0 + sign * thick, 'M_Trim', .6, 1, plane='YZ')
        bolts_at = (z0 + 20, z0 + 46)
        k.bolts([(x + sign * 7, -36.6, z) for z in bolts_at], r=1.6)
    for z in (140, 230, 320):
        k.box(x + sign * 0, x + sign * 16, -38, -34, z - 7, z + 7, 'M_Trim', .5, 1)
        k.bolts([(x + sign * 9, -38, z + s) for s in (-3.6, 3.6)], r=1.1, h=.9)


def bay(k, x0, x1, service):
    """One wall bay: kick plate, main panel, meridian strip, raked upper panel."""
    mid = (x0 + x1) / 2
    # Kick plate with a louvre or a junction box.
    k.plate(crect(x0, 8, x1, 76, (2, 2, 1, 1)), -9, -19, 'M_Wall', 1.0, 2, taper=1.0)
    if not service:
        k.ring(crect(x0 + 16, 20, x1 - 16, 66, 3), crect(x0 + 20, 24, x1 - 20, 62, 1.5), -19, -21, 'M_Trim', .4, 1)
        k.box(x0 + 20, x1 - 20, -14, -13, 24, 62, 'M_Composite', 0)
        slats(k, x0 + 20, x1 - 20, 24, 62, -17.5, 7, 'M_Trim')
        k.bolts([(x, -21, z) for x in (x0 + 18, x1 - 18) for z in (22, 64)], r=.9, h=.7)
    else:
        k.plate(crect(mid - 44, 18, mid + 44, 66, 4), -19, -29, 'M_Trim', .9, 2, taper=.8)
        k.plate(crect(mid - 36, 24, mid + 36, 60, 2), -29, -30.6, 'M_Composite', .4, 1)
        k.bolts([(mid + a, -29, z) for a in (-40, 40) for z in (23, 61)], r=1.0, h=.8)
        k.decal((0, 1), mid, 42, 24, y=-30.7)
        for a in (-26, -8, 10):
            with k.at(aim((mid + a, -13, 76), (0, 0, 1))):
                k.lathe([(3.4, -3), (3.4, 0), (2.6, .6), (2.6, 5)], 'M_Trim', 12)
    # Main panel.
    outer = crect(x0, 82, x1, 296, (2, 2, 26, 2) if service else (2, 2, 2, 26))
    k.plate(outer, -8, -21, 'M_Wall', 1.1, 2, taper=1.2, align=True)
    if service:
        # Access hatch: recess, door, hinges, latch.
        hatch = crect(x0 + 24, 124, x1 - 24, 262, (3, 3, 14, 3))
        k.ring(offset_poly(hatch, 4), offset_poly(hatch, .6), -20, -22.4, 'M_Trim', .5, 1)
        with k.painted(BONE):
            k.plate(offset_poly(hatch, -.5), -19, -22.6, 'M_Wall', .7, 2, taper=.5)
            k.plate(crect(x0 + 40, 160, x1 - 40, 232, 4), -22.6, -23.6, 'M_Wall', .3, 1)
        for z in (146, 240):
            with k.at(aim((x0 + 25, -23, z), (0, 0, 1))):
                k.lathe([(1.6, -7), (1.6, 7)], 'M_Trim', 10, .25)
            k.box(x0 + 20, x0 + 38, -23.2, -22, z - 5, z + 5, 'M_Trim', .3, 1)
        k.box(x1 - 34, x1 - 26, -25, -22.6, 182, 214, 'M_Trim', .6, 2)
        k.box(x1 - 32.5, x1 - 27.5, -25.6, -24.6, 186, 196, 'M_Hazard', .2, 1)
        k.decal((1, 1), mid, 250, 30, y=-22.7, h=15)
    else:
        # A raised structural doubler with a tapered edge and fixings in the logic of its corners.
        plate = crect(x0 + 14, 100, x1 - 14, 282, (3, 3, 3, 20))
        with k.painted(BONE):
            k.plate(plate, -21, -24, 'M_Wall', .8, 2, taper=1.6)
        k.plate(crect(x0 + 40, 120, x1 - 40, 190, 3), -24, -25, 'M_Composite', .25, 1)
        k.bolts([(x, -24, z) for x in (x0 + 21, x1 - 21) for z in (108, 196, 272)], r=1.0, h=.7)
        k.decal((2, 0), mid, 232, 54, y=-24.1, h=27)
    # Meridian strip: a continuous light line at 3.08 m, shielded by a brow.
    k.box(x0 - 2, x1 + 2, -18, -6, 298, 320, 'M_Composite', .4, 1)
    k.box(x0 - 2, x1 + 2, -24, -6, 316, 321, 'M_Trim', .8, 2)
    k.box(x0 - 2, x1 + 2, -22, -6, 297, 301, 'M_Trim', .6, 2)
    k.box(x0 - 2, x1 + 2, -18.6, -17.6, 306, 310, 'M_Light', 0)
    # Raked upper panel: it leans back so it takes the ceiling light differently from the main panel.
    with k.at(T(0, -22, 323) @ Rx(-6.4)):
        with k.painted(BONE):
            k.plate(crect(x0, 0, x1, 118, (2, 2, 2, 2)), 0, 11, 'M_Wall', 1.1, 2, taper=-.6, align=True)
        k.ring(crect(x0 + 14, 74, x1 - 14, 104, 2), crect(x0 + 18, 78, x1 - 18, 100, 1), 0, -1.2, 'M_Trim', .3, 1)
        slats(k, x0 + 18, x1 - 18, 78, 100, 2.4, 5, 'M_Trim', 3.4)
        k.plate(crect(x0 + 18, 18, x1 - 18, 60, 2), 0, -1.2, 'M_Wall', .4, 1, taper=.4)
    # Conduit behind the gap, seen between kick plate and main panel.


def wall_panel():
    """400 x 450 x 38. Pivot: floor, left end, back plane. Tiles every 400 along +X; faces -Y."""
    k = Kit('SM_Kit_WallPanel', 11)
    k.box(0, 400, -5, 0, 0, 450, 'M_Composite', 0, align=True)
    half_rib(k, 0, 1)
    half_rib(k, 400, -1)
    # Sill and head beams run through and tie every module together.
    k.box(0, 400, -32, 0, 0, 8, 'M_Trim', 1.0, 2)
    k.box(0, 400, -26, -18, 8, 11, 'M_Trim', .5, 1)
    k.box(0, 400, -30, 0, 442, 450, 'M_Trim', 1.0, 2)
    # Centre rib: a narrower web member, with a stiffener and a pair of fixings at each joint.
    k.plate([(190, 0), (210, 0), (210, -14), (205, -30), (195, -30), (190, -14)], 8, 442, 'M_Wall', 1.2, 2, plane='XY', align=True)
    k.box(197, 203, -30.8, -29, 100, 294, 'M_Composite', .2, 1)
    for z in (78, 320):
        k.box(186, 214, -33, -12, z - 6, z + 6, 'M_Trim', .8, 2)
        k.bolts([(200 + s, -33, z) for s in (-8, 8)], r=1.1, h=.9)
    bay(k, 32, 188, False)
    bay(k, 212, 368, True)
    # Service conduit and cable through the gap above the kick plates, passing behind the ribs.
    k.tube([(0, -12, 79), (400, -12, 79)], 2.6, 'M_Trim', 10)
    k.tube([(0, -9, 80.5), (130, -8, 80.5), (150, -6, 80), (300, -6, 80), (320, -8, 80.5), (400, -9, 80.5)], 1.3, 'M_Rubber', 8)
    for x in (70, 150, 250, 330):
        clamp(k, (x, -12, 79), 2.6, 'X', width=3)
    return k


def _tray(k, y0, y1, z, seed, cables):
    """Ladder tray with side rails, rungs and cables that wander but return to their start at x=400."""
    for y, s in ((y0, 1), (y1, -1)):
        k.plate([(y, z), (y + s * 2.2, z), (y + s * 2.2, z + 1), (y + s * .9, z + 1), (y + s * .9, z + 8), (y + s * 2.6, z + 8), (y + s * 2.6, z + 9), (y, z + 9)],
                0, 400, 'M_Trim', .2, 1, plane='YZ')
    for x in range(20, 400, 40):
        k.box(x - 1.6, x + 1.6, y0 + 1, y1 - 1, z, z + 1.3, 'M_Trim', .2, 1)
    for x in (100, 300):
        k.tube([(x, y0 - 3, z - 2), (x, y0 - 3, -2)], .8, 'M_Trim', 6)
        k.tube([(x, y1 + 3, z - 2), (x, y1 + 3, -2)], .8, 'M_Trim', 6)
        k.box(x - 2.5, x + 2.5, y0 - 5, y1 + 5, z - 3, z - .8, 'M_Trim', .4, 1)
    rng = np.random.default_rng(seed)
    width = y1 - y0 - 8
    for i in range(cables):
        y = y0 + 4 + width * (i + .5) / cables
        r = rng.uniform(.9, 2.0)
        phase, level = rng.uniform(0, 6.28), rng.uniform(0, 3)
        pts = [(x, y + 1.6 * math.sin(2 * math.pi * x / 400 * 2 + phase), z + 1.5 + r + level * (.6 + .4 * math.sin(2 * math.pi * x / 400 + phase)))
               for x in range(0, 401, 40)]
        k.tube(pts, r, 'M_Rubber', 7, rad=30, steps=3)


def _light_strip(k, x0, x1, y0, y1):
    """A recessed troffer, framed, with a louvred diffuser sitting inside the ceiling plane."""
    k.ring(crect(x0, y0, x1, y1, 4), crect(x0 + 7, y0 + 7, x1 - 7, y1 - 7, 2), -3, -9, 'M_Trim', 1.0, 2, plane='XY', taper=.8)
    k.ring(crect(x0 + 6, y0 + 6, x1 - 6, y1 - 6, 2), crect(x0 + 8, y0 + 8, x1 - 8, y1 - 8, 1), -3, -14, 'M_Composite', .2, 1, plane='XY')
    k.box(x0 + 8, x1 - 8, y0 + 8, y1 - 8, -6, -5, 'M_Light', 0)
    n = int((x1 - x0) // 28)
    for i in range(1, n):
        x = x0 + (x1 - x0) * i / n
        k.box(x - .8, x + .8, y0 + 7, y1 - 7, -5, -12, 'M_Trim', .2, 1)


def ceiling_truss():
    """400 x 400 x 96. Pivot: ceiling plane, x=0, centred on Y. Tiles on X and Y; hangs down -Z."""
    k = Kit('SM_Kit_CeilingTruss', 12)
    k.box(0, 400, -200, 200, -3, 0, 'M_Ceiling', 0, align=True)
    # Coffers give the ceiling a depth of its own between trays.
    for y0, y1 in ((-196, -142), (146, 196)):
        for x0, x1 in ((6, 170), (230, 394)):
            with k.painted(BONE):
                k.plate(crect(x0, y0, x1, y1, 5), -3, -7, 'M_Ceiling', .8, 2, plane='XY', taper=1.0)
    # Transverse truss, centred on x=200.
    for z0, z1, bx in ((-22, -2, 13), (-96, -74, 16)):
        ibeam(k, 200 - bx, 200 + bx, z0, z1, -200, 200, 'M_Trim', bevel=.5)
    pitch = 80
    for i in range(5):
        y0 = i * pitch - 200
        y1 = y0 + pitch
        for ya, za, yb, zb in ((y0, -74, (y0 + y1) / 2, -22), ((y0 + y1) / 2, -22, y1, -74)):
            for side in (-6, 6):
                d = Vector((0, yb - ya, zb - za))
                mid = Vector((200 + side, (ya + yb) / 2, (za + zb) / 2))
                with k.at(aim(mid, d)):
                    k.box(-3, 3, -2, 2, -d.length / 2, d.length / 2, 'M_Wall', .5, 1)
    for i in range(6):
        y = i * pitch - 200
        if 0 < i < 5:
            k.plate([(y - 16, -74), (y + 16, -74), (y + 9, -56), (y - 9, -56)], 199, 201, 'M_Trim', .4, 1, plane='YZ')
        y2 = y + pitch / 2
        if y2 < 200:
            k.plate([(y2 - 16, -22), (y2 + 16, -22), (y2 + 9, -40), (y2 - 9, -40)], 199, 201, 'M_Trim', .4, 1, plane='YZ')
    # Longitudinal stringers that sit on the bottom chord and carry the module across.
    for y in (-180, 180):
        with k.at(Rz(90)):
            ibeam(k, y - 7, y + 7, -40, -22, -400, 0, 'M_Wall', bevel=.4)
    for z in (-74, -22):
        k.bolts([(200 + s, y, z - 4 if z == -74 else z - 18) for s in (-8, 8) for y in (-120, -40, 40, 120)], (0, 0, -1), 1.0, .8)
    _tray(k, -136, -86, -58, 5, 7)
    _tray(k, 96, 132, -50, 6, 4)
    # Chilled-water main beside the tray, with one flange pair per module.
    k.tube([(0, 150, -34), (400, 150, -34)], 6, 'M_Trim', 14)
    for x in (70, 86, 320):
        with k.at(aim((x, 150, -34), (1, 0, 0))):
            k.lathe([(7, -1.8), (9.4, -1.5), (9.4, 1.5), (7, 1.8)], 'M_Trim', 20, .3, edge=.3)
    for x in (120, 280):
        clamp(k, (x, 150, -34), 6, 'X')
        k.tube([(x, 150, -24), (x, 150, -3)], 1.1, 'M_Trim', 6)
    _light_strip(k, 14, 180, -56, 56)
    _light_strip(k, 220, 386, -56, 56)
    return k


def floor_trim():
    """400 x 34 x 42. Pivot: floor, x=0, back plane. Tiles every 400 along +X; faces -Y."""
    k = Kit('SM_Kit_FloorTrim', 13)
    prof = [(0, 0), (-34, 0), (-34, 3), (-30, 6), (-20, 22), (-20, 27), (-10, 34), (-6, 42), (0, 42)]
    k.plate(prof, 0, 400, 'M_Trim', .8, 2, plane='YZ', align=True)
    # Segment joints, a toe light and drainage notches break up the extrusion.
    for x in (0, 200, 400):
        x0, x1 = max(x - 7, 0), min(x + 7, 400)
        k.plate([(-36, 0), (-36, 4), (-32, 7), (-22, 24), (-22, 29), (-12, 36), (-8, 44), (0, 44), (0, 0)], x0, x1, 'M_Wall', .8, 2, plane='YZ')
    for x in (100, 300):
        with k.at(T(x, -25.6, 14.2) @ Rx(-32)):
            k.box(-78, 78, -.8, 1, -7.2, 7.2, 'M_Composite', .3, 1)
            for z in (-7.2, 7.2):
                k.box(-79, 79, -1.8, 1, z - 1, z + 1, 'M_Trim', .3, 1)
            for i in range(-11, 12):
                k.box(i * 6.6 - 1.7, i * 6.6 + 1.7, -2, 1, -6.2, 6.2, 'M_Trim', .35, 1)
        with k.at(T(x, -14.6, 30.6) @ Rx(-55)):
            k.box(-82, 82, -.5, .5, -2.4, 2.4, 'M_Composite', .15, 1)
            k.box(-80, 80, -.8, .2, -.7, .7, 'M_Light', 0)
        k.bolts([(x + s, -5, 42) for s in (-60, 60)], (0, 0, 1), 1.2, 1)
    for x in (0, 200, 400):
        k.bolts([(max(min(x + s, 396), 4), -33.5, 3.4) for s in (-4, 4)], (0, 0, 1), 1.0, .8)
    return k


def floor_vent():
    """200 x 100 x 7. Pivot: floor, centre of the vent. Sits on top of the deck, ramped so it can be walked over."""
    k = Kit('SM_Kit_FloorVent', 14)
    outer, inner = crect(-100, -50, 100, 50, 7), crect(-88, -38, 88, 38, 3)
    k.ring(outer, inner, 0, 6, 'M_Deck', 1.0, 2, plane='XY', taper=3.2)
    k.box(-90, 90, -40, 40, 0, .8, 'M_Composite', 0)
    k.ring(crect(-89, -39, 89, 39, 3), crect(-87, -37, 87, 37, 2.5), .8, 6.4, 'M_Trim', .3, 1, plane='XY')
    # Two blade banks separated by a load-bearing spine and cross-ties.
    k.box(-3, 3, -38, 38, 0, 6, 'M_Trim', .6, 2)
    for x in (-45, 45):
        k.box(x - 1.6, x + 1.6, -38, 38, 0, 5.2, 'M_Trim', .4, 1)
    for side in (-1, 1):
        for i in range(21):
            x = side * (6.2 + i * 3.9)
            with k.at(T(x, 0, 3.4) @ Ry(side * 30)):
                k.box(-.3, .3, -37.6, 37.6, -2.5, 2.5, 'M_Trim', .08, 1)
    k.bolts([(sx * 93, sy * 43, 4.8) for sx in (-1, 1) for sy in (-1, 1)] + [(0, sy * 44, 4.8) for sy in (-1, 1)], (0, 0, 1), 1.3, .8)
    return k


def pipe_run():
    """400 x 56 x 80. Pivot: x=0, back plane, on the main pipe's height. Tiles along +X; faces -Y."""
    k = Kit('SM_Kit_PipeRun', 15)
    main, sec, thin = (-32, 12.5), (-24, 7.0), (-16, 4.0)
    z_main, z_sec, z_thin = 0, 34, -30
    k.tube([(0, main[0], z_main), (400, main[0], z_main)], main[1], 'M_Trim', 20)
    k.tube([(0, sec[0], z_sec), (400, sec[0], z_sec)], sec[1], 'M_Wall', 16)
    k.tube([(0, thin[0], z_thin), (90, thin[0], z_thin), (112, thin[0] - 8, z_thin), (152, thin[0] - 8, z_thin), (174, thin[0], z_thin), (400, thin[0], z_thin)],
           thin[1], 'M_Trim', 12, rad=8)
    # Thermal lagging on the main, cinched by stainless bands.
    with k.at(aim((215, main[0], z_main), (1, 0, 0))):
        k.lathe([(12.5, -92), (14.6, -90), (14.6, 90), (12.5, 92)], 'M_Composite', 22, .5)
    for x in range(135, 300, 32):
        with k.at(aim((x, main[0], z_main), (1, 0, 0))):
            k.lathe([(14.5, -1.4), (15.3, -1.2), (15.3, 1.2), (14.5, 1.4)], 'M_Trim', 22, 0, edge=.5)
    # Module-end flanges mate the run to the next one.
    for x, sign in ((0, 1), (400, -1)):
        with k.at(aim((x, main[0], z_main), (sign, 0, 0))):
            k.lathe([(19.5, 0), (19.5, 2.6), (15, 3.4), (13.4, 7), (12.5, 8)], 'M_Trim', 24, .35, edge=.3)
            for i in range(8):
                a = (i + .5) * math.pi / 4
                k.bolt((16.8 * math.cos(a), 16.8 * math.sin(a), 3.0), (0, 0, 1), 1.0, .9)
        with k.at(aim((x, sec[0], z_sec), (sign, 0, 0))):
            k.lathe([(11, 0), (11, 1.8), (8, 2.4), (7, 5)], 'M_Trim', 18, .3, edge=.3)
    # Gate valve with its yoke and handwheel, on a tee off the main.
    vx = 72
    with k.at(aim((vx, main[0], z_main), (1, 0, 0))):
        k.lathe([(13.2, -22), (17.5, -20), (20, -12), (20, 12), (17.5, 20), (13.2, 22)], 'M_Wall', 24, .5)
        for s in (-1, 1):
            k.lathe([(13.2, s * 21), (21, s * 21), (21, s * 24), (13.2, s * 24)], 'M_Trim', 24, .35, edge=.3)
            for i in range(8):
                a = (i + .5) * math.pi / 4
                k.bolt((18.4 * math.cos(a), 18.4 * math.sin(a), s * 24), (0, 0, s), 1.0, .9)
    with k.at(aim((vx, main[0] - 17, z_main), (0, -1, 0))):
        k.lathe([(10, -1), (10, 2), (7, 3), (6.2, 8), (9, 9), (9, 11), (4, 12)], 'M_Trim', 20, .35)
        for a in (0, 180):
            with k.at(Rz(a) @ T(7.4, 0, 10)):
                k.box(-1.2, 1.2, -2, 2, 0, 22, 'M_Trim', .3, 1)
        k.box(-9, 9, -2.4, 2.4, 31, 34, 'M_Trim', .4, 1)
        k.tube([(0, 0, 8), (0, 0, 46)], 1.5, 'M_Trim', 10)
        k.lathe([(3.8, 37.6), (3.8, 41.4), (2, 42)], 'M_Trim', 12, .2)
        # Handwheel: rim torus, four spokes.
        rim = [(math.cos(i * math.pi / 18) * 15, math.sin(i * math.pi / 18) * 15, 40) for i in range(37)]
        k.tube(rim, 1.5, 'M_Hazard', 10, caps=False)
        for i in range(4):
            a = i * math.pi / 2 + .4
            k.tube([(math.cos(a) * 3, math.sin(a) * 3, 40), (math.cos(a) * 14.4, math.sin(a) * 14.4, 40)], 1.0, 'M_Trim', 8)
    # Pressure gauge on the secondary line.
    with k.at(aim((244, sec[0] - 7, z_sec), (0, -1, 0))):
        k.lathe([(1.4, 0), (1.4, 9)], 'M_Trim', 8)
        with k.at(T(0, 0, 9)):
            k.lathe([(6, 0), (6.6, .6), (6.6, 3.4), (5.8, 4)], 'M_Trim', 20, .2)
    # Branch: a small return off the secondary, down into the wall.
    k.tube([(320, sec[0], z_sec), (320, sec[0] - 13, z_sec), (320, sec[0] - 13, 8), (320, 0, 8)], 3.0, 'M_Trim', 12, rad=7)
    with k.at(aim((320, sec[0], z_sec), (0, -1, 0))):
        k.lathe([(9, 7), (8, 8), (4.4, 9), (3.4, 12)], 'M_Trim', 16, .2)
    # Yoked wall brackets.
    for x in (36, 364):
        k.plate(crect(x - 9, -58, x + 9, 60, 3), 0, -3, 'M_Trim', .7, 2)
        k.box(x - 5, x + 5, -4, -3, -56, 58, 'M_Composite', 0)
        k.bolts([(x + a, -3, b) for a in (-6, 6) for b in (-52, 54)], r=1.3)
        for y, r, z in (((-32), 12.5, 0), (-24, 7, 34), (-16, 4, -30)):
            clamp(k, (x, y, z), r, 'X', width=7, foot=-3)
    return k


def _portal_side(k):
    """Everything on the -Y side of a doorway; called twice with a half turn."""
    w, h = 210, 340
    # Stepped reveal, three layers that close in on the opening like a lens.
    o3 = crect(-326, 0, 326, 482, (2, 2, 86, 86))
    i3 = crect(-250, 0, 250, 404, (.5, .5, 52, 52))
    k.ring(o3, i3, -20, -30, 'M_Wall', 1.8, 2, taper=2.2, align=True)
    o2 = crect(-252, 0, 252, 406, (.5, .5, 54, 54))
    i2 = crect(-226, 0, 226, 376, (.5, .5, 42, 42))
    k.ring(o2, i2, -20, -42, 'M_Trim', 1.4, 2, taper=2.5)
    o1 = crect(-228, 0, 228, 378, (.5, .5, 44, 44))
    i1 = crect(-w, 0, w, h, (.5, .5, 30, 30))
    k.ring(o1, i1, -20, -52, 'M_Composite', .9, 2, taper=1.0)
    # Vertical pilasters on the outer layer, with raked caps.
    for s in (-1, 1):
        k.plate(crect(min(s * 258, s * 318), 14, max(s * 258, s * 318), 318, 3), -28, -33, 'M_Wall', .9, 2, taper=1.2)
        k.box(s * 266, s * 310, -34, -32.5, 26, 112, 'M_Composite', .3, 1)
        slats(k, min(s * 268, s * 308), max(s * 268, s * 308), 30, 108, -33, 8)
        k.box(s * 270, s * 306, -34, -33, 150, 210, 'M_Trim', .3, 1)
        k.decal((3, 2), s * 288, 262, 44, y=-33.2, h=22)
        for z in (20, 118, 142, 312):
            k.bolts([(s * (264 + a), -33, z) for a in (0, 48)], r=1.2)
        # A doubler that follows the raked corner and ties lintel to pilaster.
        gusset = [(150, 410), (236, 410), (321, 328), (321, 322), (258, 322), (258, 356), (208, 398), (150, 398)]
        k.plate([(s * a, b) for a, b in gusset], -28, -34, 'M_Trim', .9, 2, taper=.9)
        k.bolts([(s * a, -34, b) for a, b in ((166, 404), (214, 404), (250, 372), (292, 334), (314, 326))], r=1.2)
        # Hydraulic ram parallel to the jamb: cylinder, rod, trunnions.
        rx = s * 240
        with k.at(T(rx, -44, 0)):
            k.box(-13, 13, -7, 8, 2, 16, 'M_Trim', 1.0, 2)
            k.box(-13, 13, -7, 8, 300, 318, 'M_Trim', 1.0, 2)
            with k.at(aim((0, -2, 16), (0, 0, 1))):
                k.lathe([(9, 0), (9, 6), (7.4, 8), (7.4, 164), (9, 166), (9, 172), (4.2, 174), (3.6, 180), (3.6, 288)], 'M_Wall', 18, .4)
                for z in (32, 90, 148):
                    k.lathe([(7.4, z - 2), (8.4, z - 1.4), (8.4, z + 1.4), (7.4, z + 2)], 'M_Trim', 18, 0, edge=.5)
            # Rod boot shield.
            k.tube([(10.6, -2, 30), (10.6, -2, 300)], 1.2, 'M_Rubber', 8)
        # Hazard chevrons on the inner jamb's front face.
        k.box(s * 212, s * 226, -53.6, -51.6, 0, 150, 'M_Hazard', .3, 1)
        k.bolts([(s * 219, -53.6, z) for z in (10, 140)], r=.9, h=.7)
    # Header: a lintel box with a status lamp, and the deck code in front of it.
    k.plate(crect(-140, 382, 140, 444, (3, 3, 14, 14)), -30, -44, 'M_Trim', 1.4, 2, taper=1.5)
    k.plate(crect(-120, 392, 120, 434, 6), -44, -45.4, 'M_Composite', .4, 1)
    k.box(-96, 96, -46.2, -45.0, 406, 420, 'M_Light', 0)
    for s in (-1, 1):
        k.box(s * 102, s * 114, -45.8, -45, 400, 426, 'M_Trim', .3, 1)
    k.bolts([(s * a, -44, b) for s in (-1, 1) for a in (130,) for b in (392, 430)], r=1.3)
    k.decal((0, 0), 0, 460, 110, y=-30.6, h=27.5)
    # Sill: a ramp plate that carries the deck through the wall.
    k.plate([(-34, 0), (-34, .8), (-14, 3), (0, 3), (0, 0)], -w, w, 'M_Deck', .4, 1, plane='YZ')
    for s in (-1, 1):
        k.box(s * 160, s * 170, -24, -12, 0, 3.4, 'M_Hazard', .2, 1)


def door_frame():
    """652 x 108 x 482; opening 420 x 340. Pivot: floor, centre of the doorway and wall thickness; straddles a 40 cm wall."""
    k = Kit('SM_Kit_DoorFrame', 16)
    _portal_side(k)
    with k.at(Rz(180)):
        _portal_side(k)
    # Reveal lining through the wall, with the blast door's guide track in the middle of it.
    for s in (-1, 1):
        k.box(s * 210, s * 232, -20, 20, 0, 340, 'M_Composite', .5, 1)
        k.box(s * 210, s * 216, -3, -9, 3, 330, 'M_Trim', .4, 1)
        k.box(s * 210, s * 216, 3, 9, 3, 330, 'M_Trim', .4, 1)
    k.box(-210, 210, -20, 20, 340, 356, 'M_Composite', .5, 1)
    k.box(-210, 210, -9, -3, 334, 340, 'M_Trim', .4, 1)
    k.box(-210, 210, 3, 9, 334, 340, 'M_Trim', .4, 1)
    return k


SEAM = [(-22, 0), (-22, 96), (26, 138), (26, 182), (-26, 226), (-26, 270), (22, 312), (22, 340)]


def _leaf(k, sign):
    """One leaf of the blast door. sign=-1 is the left leaf (x<0)."""
    edge = 214 * sign
    outline = list(SEAM) + [(edge, 340), (edge, 0)]
    if poly_area(outline) < 0:
        outline.reverse()
    k.plate(outline, -15, 15, 'M_Trim', 1.0, 2, align=True)
    armour = offset_poly(outline, -8)

    def face():
        # Armour skin with a broad chamfer so the seam looks machined from thick plate.
        k.plate(armour, -15, -21, 'M_Wall', 1.2, 2, taper=2.8, align=True)
        inner = 44 * sign
        # Horizontal strakes are the door's weight: they stop the leaf reading as a flat card.
        for z, hgt in ((32, 40), (262, 48)):
            pts = crect(min(inner, edge * .94), z, max(inner, edge * .94), z + hgt, (3, 3, 3, 3))
            with k.painted(BONE):
                k.plate(pts, -21, -28, 'M_Wall', 1.2, 2, taper=2.0)
            k.plate(crect(min(inner, edge * .94) + 8, z + 8, max(inner, edge * .94) - 8, z + hgt - 8, 2), -28, -29, 'M_Composite', .25, 1)
            k.bolts([(edge * f, -28, z + hgt / 2 + d) for f in (.3, .9) for d in (-12, 12)], r=1.5)
        # Vertical ribs and a recessed grip ladder make the middle of the leaf.
        for f, wid in ((.62, 11), (.88, 11)):
            k.plate(crect(edge * f - wid, 80, edge * f + wid, 256, 2), -21, -26, 'M_Wall', 1.0, 2, taper=1.0)
            k.box(edge * f - wid * .4, edge * f + wid * .4, -26.8, -25.8, 88, 248, 'M_Composite', .2, 1)
            k.bolts([(edge * f, -26, z) for z in (96, 168, 240)], r=1.4)
        # Hazard chevrons run along the seam, on the door's closing edge.
        # Foot plate, dented by traffic.
        k.plate(crect(min(edge * .3, edge * .96), 4, max(edge * .3, edge * .96), 24, 2), -21, -24, 'M_Hazard', .6, 1, taper=.5)
    face()
    # Back face is the mirrored front.
    with k.at(S(1, -1, 1)):
        face()
    # Edge rollers inside the guide track.
    for z in (40, 300):
        k.box(edge - sign * 2, edge + sign * 3, -9, 9, z - 14, z + 14, 'M_Trim', 1.0, 2)


def _lock(k, sign):
    """Half of the central lock on each face: a recessed gear race, a stepped rotor and five radial bolts."""
    cz = 170

    def arc(r, t0=0.0, t1=180.0, n=36):
        return [(sign * (.5 + r * math.sin(math.radians(t0 + (t1 - t0) * i / n))), cz + r * math.cos(math.radians(t0 + (t1 - t0) * i / n))) for i in range(n + 1)]

    def band(r0, r1, t0=0.0, t1=180.0, n=36):
        return arc(r1, t0, t1, n) + arc(r0, t0, t1, n)[::-1]

    def polar(r, deg):
        return sign * (.5 + r * math.sin(math.radians(deg))), cz + r * math.cos(math.radians(deg))
    for face in (1, -1):
        with k.at(S(1, face, 1)):
            # Race: a dark annular well between a heavy retaining ring and the rotor.
            k.plate(arc(100), -21, -23.5, 'M_Composite', .5, 1)
            k.plate(band(84, 100), -21, -33, 'M_Trim', 1.6, 2, taper=2.2)
            for i in range(24):
                deg = 3.75 + i * 7.5
                if i % 4 != 2:
                    x, z = polar(92, deg)
                    k.bolt((x, -33, z), r=1.2, h=1.0)
            # Gear teeth run round the race and give the drum a machined rhythm.
            for i in range(15):
                deg = 6 + i * 12
                x, z = polar(77, deg)
                with k.at(T(x, -23.5, z) @ Ry(sign * deg)):
                    k.box(-3.2, 3.2, -7, 0, -7, 7, 'M_Trim', .7, 2)
            # Rotor: stepped disc, bone painted, with bolt circle and an index arc in hazard.
            with k.painted(BONE):
                k.plate(arc(68), -23.5, -36, 'M_Wall', 1.6, 2, taper=2.6)
            k.plate(band(50, 54, 20, 80, 12), -36, -36.6, 'M_Hazard', .2, 1)
            k.plate(band(50, 54, 100, 160, 12), -36, -36.6, 'M_Hazard', .2, 1)
            for i in range(6):
                x, z = polar(44, 15 + i * 30)
                k.bolt((x, -36, z), r=1.8, h=1.5)
            k.plate(arc(36), -36, -41, 'M_Trim', 1.2, 2, taper=1.4)
            k.plate(arc(24), -41, -44, 'M_Composite', .5, 1, taper=.8)
            k.plate(arc(12), -44, -49, 'M_Trim', 1.0, 2, taper=1.6)
            # Radial bolts: a guide housing, a polished pin and an anchor block in the armour.
            for i in range(5):
                deg = 30 + i * 30
                x, z = polar(0, deg)
                with k.at(T(x, -26, z) @ Ry(sign * deg)):
                    k.plate(crect(-13, 62, 13, 90, 2), -8, 7, 'M_Wall', 1.1, 2, taper=1.2)
                    k.box(-9, 9, -9.2, -7, 66, 86, 'M_Composite', .3, 1)
                    k.bolts([(sx * 9.5, -8, zz) for sx in (-1, 1) for zz in (66, 86)], r=1.0, h=.8)
                    with k.at(T(0, -1, 88)):
                        k.lathe([(4.6, 0), (4.6, 22), (3.8, 24), (0.01, 24)], 'M_Trim', 14, 0, edge=.4)
                        k.lathe([(5.8, 0), (5.8, 3), (4.6, 4)], 'M_Trim', 14, 0)
                    k.plate(crect(-12, 104, 12, 118, 2), 4, -7, 'M_Trim', 1.0, 2, taper=.9)
                    k.bolts([(sx * 8, -7, 111) for sx in (-1, 1)], r=1.3, h=1.0)


def blast_door(which):
    """Leaf pair for a 420 x 340 opening, 58 thick. Pivot: floor, centre of the door. Leaves slide along X."""
    k = Kit({0: 'SM_Kit_BlastDoor', -1: 'SM_Kit_BlastDoor_L', 1: 'SM_Kit_BlastDoor_R'}[which], 17)
    for sign in ((-1, 1) if which == 0 else (which,)):
        _leaf(k, sign)
        _lock(k, sign)
    return k


def console():
    """170 x 96 x 118. Pivot: floor, centre of the front; the operator stands on the -Y side."""
    k = Kit('SM_Kit_Console', 18)
    k.paint = BONE
    # Side cheeks give the silhouette: toe kick, knee recess, raked desk, hooded head.
    cheek = [(-48, 0), (40, 0), (40, 92), (34, 118), (10, 118), (-6, 92), (-44, 80), (-48, 76), (-36, 40), (-36, 10), (-48, 6)]
    for x in (-85, 69, -8):
        wid = 16 if x != -8 else 16
        k.plate(cheek, x, x + wid, 'M_Wall', 1.4, 2, plane='YZ', taper=.8)
        k.plate(offset_poly(crect(-30, 12, 32, 74, 6), 0), x - .8, x + wid + .8, 'M_Composite', .4, 1, plane='YZ')
    k.box(-69, 69, -34, 34, 10, 74, 'M_Composite', .4, 1)
    k.box(-85, 85, -46, 40, 0, 6, 'M_Trim', .9, 2)
    k.box(-68, 68, -36, -34, 14, 70, 'M_Trim', .4, 1)
    slats(k, -60, 60, 16, 44, -36, 8, 'M_Trim')
    # Desk slope, rotated 17 degrees from flat, carrying the keyboard band.
    for x0, x1 in ((-69, -8), (8, 69)):
        with k.at(T(0, -44, 80) @ Rx(17.5)):
            k.box(x0, x1, 0, 40, -3, 0, 'M_Trim', .7, 2)
            k.box(x0 + 3, x1 - 3, 3, 37, 0, .6, 'M_Composite', .2, 1)
            _keys_flat(k, x0 + 6, x1 - 6, 6, 26, .6)
        # Raised upper bank with the two main displays.
        with k.at(T(0, -6, 92) @ Rx(68)):
            k.box(x0, x1, 0, 30, -4, 0, 'M_Trim', .8, 2)
            k.ring(crect(x0 + 3, 2, x1 - 3, 28, 1.2), crect(x0 + 5, 4, x1 - 5, 26, .6), 0, .9, 'M_Composite', .25, 1, plane='XY')
            k.screen((0 if x0 < 0 else 1, 0), (x0 + 5, 4, .3), (x1 - 5, 4, .3), (x1 - 5, 26, .3), (x0 + 5, 26, .3))
    # Hood over the screens, with a concealed task light.
    k.plate([(0, 118), (36, 118), (36, 126), (28, 128), (-4, 122), (-6, 118)], -86, 86, 'M_Wall', 1.1, 2, plane='YZ', taper=.5)
    k.box(-70, 70, -4.8, -3.6, 119.4, 120.2, 'M_Light', 0)
    k.box(-80, 80, 38, 42, 12, 112, 'M_Trim', .8, 2)
    # Cable loom leaving the rear and going to the floor.
    for i, (x, r) in enumerate(((-30, 2.4), (-24, 1.6), (-19, 1.9), (32, 2.2))):
        k.tube([(x, 42, 60 + i * 4), (x, 50, 50), (x + 2, 52, 14), (x + 8, 60, 2.4), (x + 14, 92, 2.4)], r, 'M_Rubber', 8, rad=10)
    return k


def _keys_flat(k, x0, x1, y0, y1, z):
    rows, cols = 5, max(4, int((x1 - x0) // 4.2))
    for r in range(rows):
        for c in range(cols):
            if (r == 4 and (c < 2 or c > cols - 3)) or (r == 2 and c % 7 == 3):
                continue
            x = x0 + (x1 - x0) * (c + .5) / cols
            y = y0 + (y1 - y0) * (r + .5) / rows
            s = 1.5
            k.box(x - s, x + s, y - s, y + s, z, z + .7, 'M_Trim', .2, 1)
            if k.rng.uniform() < .16:
                # Lit caps sample a flat header colour from the screen atlas.
                u = .02 if k.rng.uniform() < .7 else .35
                k.quad([(x - s + .3, y - s + .3, z + .72), (x + s - .3, y - s + .3, z + .72), (x + s - .3, y + s - .3, z + .72), (x - s + .3, y + s - .3, z + .72)],
                       'M_Screen', (u, .992, u + .05, .996))


def terminal():
    """70 x 56 x 176. Pivot: floor, centre of the base. A free-standing lectern; screen faces -Y."""
    k = Kit('SM_Kit_Terminal', 19)
    k.paint = BONE
    k.plate(crect(-36, -30, 36, 30, 8), 0, 4, 'M_Trim', 1.0, 2, plane='XY', taper=1.2)
    k.bolts([(sx * 29, sy * 23, 3.6) for sx in (-1, 1) for sy in (-1, 1)], (0, 0, 1), 1.4)
    # Stem: a splayed spine with lightening cut-outs and a cable that actually enters it.
    stem = [(-17, 4), (17, 4), (11, 40), (9, 118), (-9, 118), (-11, 40)]
    k.plate(stem, -8, 10, 'M_Wall', 1.2, 2, taper=.9)
    for z0, z1 in ((46, 74), (82, 110)):
        k.plate(crect(-5, z0, 5, z1, 2), -9, 11, 'M_Composite', .3, 1)
    k.box(-12, 12, -10, 12, 112, 120, 'M_Trim', .8, 2)
    # Head: a raked housing with a keypad shelf below the screen.
    with k.at(T(0, 0, 120) @ Rx(-16)):
        body = crect(-34, 0, 34, 48, (5, 5, 11, 11))
        k.plate(body, -8, 12, 'M_Trim', 1.2, 2, taper=.9)
        k.ring(body, offset_poly(body, -4), -8, -10.5, 'M_Wall', .7, 2)
        k.screen((2, 0), (-29, -8.8, 4), (29, -8.8, 4), (29, -8.8, 44), (-29, -8.8, 44))
    with k.at(T(0, -7, 115) @ Rx(38)):
        k.box(-30, 30, -19, 2, -3, 0, 'M_Wall', .8, 2)
        k.box(-27, 27, -17, 0, 0, .4, 'M_Composite', .1, 1)
        _keys_flat(k, -25, 25, -16, -1, .4)
    for s in (-1, 1):
        k.tube([(s * 9, 13, 142), (s * 11, 23, 120), (s * 9, 24, 40), (s * 12, 20, 6), (s * 13, 14, 4)], 1.5, 'M_Rubber', 8, rad=12)
    return k


def crate(name, w, d, h, seed):
    """w x d x h. Pivot: floor, centre. Stackable on its own feet."""
    k = Kit(name, seed)
    k.paint = CARGO
    post, rail = (14 if w > 120 else 9), (14 if w > 120 else 9)
    scale = w / 200
    k.box(-w / 2 + 9, w / 2 - 9, -d / 2 + 9, d / 2 - 9, 4, h - 4, 'M_Composite', 0)
    # Rails: stacked rings at the top and bottom, the crate's primary shape.
    outer = crect(-w / 2, -d / 2, w / 2, d / 2, 10 * scale)
    inner = crect(-w / 2 + rail, -d / 2 + rail, w / 2 - rail, d / 2 - rail, 4 * scale)
    k.ring(outer, inner, 0, rail, 'M_Trim', 1.1, 2, plane='XY', taper=.9)
    k.ring(outer, inner, h - rail, h, 'M_Trim', 1.1, 2, plane='XY', taper=.9)
    # Corner posts, L-section, with their own castings.
    for i in range(4):
        with k.at(Rz(90 * i)):
            hw, hd = (w, d) if i % 2 == 0 else (d, w)
            hw, hd = hw / 2, hd / 2
            l = [(hw, -hd + post * 1.5), (hw, -hd + 8 * scale), (hw - 8 * scale, -hd), (hw - post * 1.5, -hd), (hw - post * 1.5, -hd + 3), (hw - 3, -hd + post * 1.5)]
            k.plate(l, rail - .5, h - rail + .5, 'M_Trim', .8, 2, plane='XY')
    for i in range(4):
        with k.at(Rz(90 * i)):
            hw, hd = (w if i % 2 == 0 else d) / 2, (d if i % 2 == 0 else w) / 2
            panel_w = hw - post - 2
            # A side panel with pressed ribs. Sides differ so a stack does not read as a copy-paste.
            kind = (i + seed) % 2
            k.plate(crect(-panel_w, rail + 1, panel_w, h - rail - 1, 3 * scale), -hd + 3, -hd + 5.5, 'M_Wall', .7, 2, taper=-.3)
            ribs = 4 if w > 120 else 3
            if kind == 0:
                for j in range(ribs):
                    x = -panel_w + (2 * panel_w) * (j + .5) / ribs
                    wide = panel_w / ribs * .56
                    k.plate(crect(x - wide, rail + 8, x + wide, h - rail - 8, 2.4 * scale), -hd + 3, -hd + 1.6, 'M_Wall', .5, 2, taper=1.0)
            else:
                band = (h - 2 * rail) * .22
                mid = h / 2
                k.plate(crect(-panel_w + 8, mid - band, panel_w - 8, mid + band, 3 * scale), -hd + 3, -hd + 1.8, 'M_Hazard' if w > 120 else 'M_Wall', .5, 2, taper=.7)
            # Handles recessed through the panel on two sides.
            if i % 2 == 0:
                z = h * .62
                k.tube([(-22 * scale, -hd + 3, z), (-20 * scale, -hd - .8, z), (20 * scale, -hd - .8, z), (22 * scale, -hd + 3, z)], 1.2 + scale * .7, 'M_Trim', 8, rad=3)
                for s in (-1, 1):
                    k.box(s * 22 * scale - 3, s * 22 * scale + 3, -hd + 1, -hd + 3.4, z - 4, z + 4, 'M_Trim', .4, 1)
            # Latches over the top rail.
            for s in (-1, 1):
                x = s * panel_w * .55
                k.box(x - 7 * scale, x + 7 * scale, -hd - 1.4, -hd + .2, h - rail - 14 * scale, h - rail + 4, 'M_Trim', .6, 2)
                k.box(x - 5 * scale, x + 5 * scale, -hd - 2.2, -hd - 1, h - rail - 11 * scale, h - rail - 3, 'M_Hazard', .3, 1)
                with k.at(aim((x, -hd - 1.6, h - rail + 2), (1, 0, 0))):
                    k.lathe([(1.4, -8 * scale), (1.4, 8 * scale)], 'M_Trim', 8, .1)
            if kind == 1:
                k.decal((1, 0), 0, h * .5, min(w, h) * .5, y=-hd + 1.7, h=min(w, h) * .25)
    # Lid with a raised centre, stacking recess and lifting eyes.
    k.plate(crect(-w / 2 + rail, -d / 2 + rail, w / 2 - rail, d / 2 - rail, 4 * scale), h - 6, h - 1.2, 'M_Wall', .9, 2, plane='XY', taper=.6)
    k.plate(crect(-w / 3, -d / 3, w / 3, d / 3, 6 * scale), h - 1.2, h + .6, 'M_Wall', .8, 2, plane='XY', taper=1.4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (w / 2 - rail * .55), sy * (d / 2 - rail * .55)
            k.plate(crect(cx - 5, cy - 5, cx + 5, cy + 5, 1.5), h, h + 1.2, 'M_Trim', .4, 1, plane='XY')
    k.bolts([(sx * w * .24, sy * d * .24, h + .6) for sx in (-1, 1) for sy in (-1, 1)], (0, 0, 1), 1.4)
    return k


def rifle(k):
    """Meridian service carbine, 92 long, along local +X, muzzle up, in the XZ plane at y=0."""
    # Receiver in two skins, so it has a parting line and a visible thickness.
    body = [(0, -2), (14, -2), (22, -3), (46, -3), (49, 0), (60, 0), (60, 6.5), (44, 7.5), (26, 7.5), (20, 6), (0, 6)]
    k.plate(body, -2.6, 2.6, 'M_Trim', .35, 2, taper=.25)
    k.plate([(6, -.5), (24, -1.2), (44, -1.2), (44, 5.4), (6, 4.6)], -3.0, 3.0, 'M_Wall', .3, 1, taper=.3)
    k.box(30, 42, -3.3, 3.3, 3, 5.4, 'M_Composite', .2, 1)
    # Handguard with cooling slots; the barrel is seen through them.
    k.plate(crect(46, -.8, 74, 6.8, 1.2), -2.9, 2.9, 'M_Composite', .4, 2, taper=.3)
    for x in (51, 57, 63, 69):
        k.box(x - 1.6, x + 1.6, -3.1, 3.1, 2.2, 5.0, 'M_Trim', .15, 1)
    with k.at(aim((60, 0, 3.2), (1, 0, 0))):
        k.lathe([(1.3, 0), (1.3, 30), (1.9, 31), (1.9, 34), (2.4, 34.6), (2.4, 38), (1.9, 38.6), (1.9, 40.6), (2.4, 41.2), (2.4, 44), (.2, 44.4)], 'M_Trim', 12)
    # Top rail with real teeth, and a sealed optic on two mounts.
    k.box(6, 72, -1.5, 1.5, 7.2, 8.3, 'M_Trim', .15, 1)
    for x in np.arange(8, 72, 3.2):
        k.box(float(x) - .7, float(x) + .7, -1.7, 1.7, 8.2, 9.0, 'M_Trim', .1, 1)
    with k.at(aim((20, 0, 13.6), (1, 0, 0))):
        k.lathe([(.2, -.4), (2.9, 0), (2.9, 4), (2.2, 5), (2.2, 15), (2.9, 16), (2.9, 21), (.2, 21.4)], 'M_Composite', 14)
    for x in (24, 36):
        k.box(x - 1.8, x + 1.8, -1.9, 1.9, 8.8, 11.4, 'M_Trim', .2, 1)
    # Grip, magazine and trigger guard hang from the receiver at their own angles.
    k.plate([(17, -2), (27, -2), (22, -17), (13, -18)], -2.2, 2.2, 'M_Composite', .5, 2, taper=.35)
    k.plate([(31, -3), (41, -3), (45, -21), (35, -23)], -2.0, 2.0, 'M_Trim', .4, 2, taper=.3)
    k.box(32, 40, -2.3, 2.3, -7, -5, 'M_Composite', .2, 1)
    k.tube([(26, -3, -2.5), (27, 0, -7), (31, 0, -7.4), (32, 0, -3)], .5, 'M_Trim', 6, rad=1.2)
    # Skeleton stock: a real opening, with a rubber butt pad.
    k.ring([(0, -2), (0, 6), (-26, 5.5), (-28, -8), (-23, -8), (-10, -2)], [(-4, 0), (-4, 3.4), (-22, 2.8), (-23.5, -5), (-21, -5), (-9, 0)], -1.5, 1.5, 'M_Composite', .35, 1, taper=.15)
    k.box(-31, -27.6, -2.2, 2.2, -9, 7, 'M_Rubber', .6, 2)
    k.box(50, 53, -3.0, -2.8, 1.2, 1.9, 'M_Light', 0)


def weapon_rack():
    """250 x 42 x 232. Pivot: floor, centre, back plane. Wall mounted; faces -Y."""
    k = Kit('SM_Kit_WeaponRack', 20)
    back = crect(-125, 0, 125, 232, (3, 3, 24, 24))
    k.plate(back, 0, -8, 'M_Wall', 1.4, 2, taper=1.0, align=True)
    k.plate(crect(-112, 64, 112, 208, 10), -8, -9.4, 'M_Composite', .4, 1)
    # Header with task lamp and storage base with ammunition drawers.
    k.plate(crect(-126, 208, 126, 232, (1, 1, 18, 18)), -8, -38, 'M_Trim', 1.5, 2, taper=1.0)
    k.box(-104, 104, -32, -28, 206.6, 208.2, 'M_Light', 0)
    k.decal((0, 0), 0, 220, 80, y=-38.2, h=20)
    k.plate(crect(-126, 0, 126, 56, (2, 2, 6, 6)), -8, -40, 'M_Wall', 1.4, 2, taper=1.0)
    for i in range(4):
        x = -93 + i * 62
        k.plate(crect(x - 28, 7, x + 28, 49, 2), -40, -42, 'M_Trim', .6, 2, taper=.5)
        k.box(x - 12, x + 12, -43.6, -41.8, 37, 41, 'M_Trim', .5, 1)
        k.box(x + 17, x + 24, -42.4, -41.8, 38, 41, 'M_Light', 0)
        k.decal((2, 1), x - 8, 22, 26, y=-42.1, h=13)
    # Five cradles: bottom butt cup, top magnetic lock with status pip.
    for i in range(5):
        x = -96 + i * 48
        with k.at(T(x, -18, 57)):
            k.plate(crect(-11, -10, 11, 10, 3), 0, 3, 'M_Trim', .6, 2, plane='XY', taper=.5)
            k.ring(crect(-7, -7, 7, 7, 2), crect(-5, -5, 5, 5, 1.5), 3, 7, 'M_Composite', .3, 1, plane='XY')
        k.box(x - 7, x + 7, -14, -8, 158, 174, 'M_Trim', .7, 2)
        k.box(x - 9, x + 9, -26, -14, 163, 171, 'M_Wall', .7, 2)
        k.box(x + 4, x + 7, -26.4, -25.9, 165.6, 168.4, 'M_Light', 0)
        if i != 3:
            with k.at(T(x, -20, 93) @ Ry(-90) @ S(1, 1.25, 1.25)):
                rifle(k)
        k.tube([(x, -8.4, 158), (x, -7.4, 120), (x, -8.4, 62)], .7, 'M_Rubber', 6)
    return k


def _insulator(k, pos, direction):
    with k.at(aim(pos, direction)):
        prof = [(5, 0)]
        z = 0
        for _ in range(4):
            prof += [(5, z + .6), (8, z + 1.1), (8, z + 2.1), (5, z + 2.6)]
            z += 2.8
        prof += [(3.4, z), (3.4, z + 4)]
        k.lathe(prof, 'M_Composite', 16)


def power_conduit():
    """400 x 44 x 72. Pivot: x=0, back plane, centre height. Tiles along +X; faces -Y."""
    k = Kit('SM_Kit_PowerConduit', 21)
    # Chamfered bus duct; a channel on its face holds an exposed, glowing bus-bar.
    prof = [(0, -28), (-26, -28), (-34, -20), (-34, 20), (-26, 28), (0, 28)]
    k.plate(prof, 0, 400, 'M_Wall', 1.2, 2, plane='YZ', align=True)
    for x0, x1 in ((46, 170), (230, 354)):
        k.plate(crect(x0, -9, x1, 9, 2.4), -34, -34.6, 'M_Composite', .3, 1)
        k.box(x0 + 3, x1 - 3, -35.4, -34.4, -2.4, 2.4, 'M_Light', 0)
        for x in np.arange(x0 + 12, x1, 14):
            k.box(x - 1.2, x + 1.2, -36.4, -34, -9.6, 9.6, 'M_Trim', .3, 1)
    # Finned heat-sink along the top and bottom chamfers, split into two runs.
    for x0, x1 in ((48, 168), (232, 352)):
        for x in np.arange(x0, x1, 5):
            for sign in (1, -1):
                k.plate([(-30, sign * 24), (-22, sign * 32), (-20, sign * 30), (-28, sign * 22)], x - .5, x + .5, 'M_Trim', 0, plane='YZ')
    # Couplers at the module ends and the junction block in the middle.
    for x, wide in ((0, 20), (400, 20)):
        k.plate([(0, -36), (-28, -36), (-40, -24), (-40, 24), (-28, 36), (0, 36)], max(0, x - wide), min(400, x + wide), 'M_Trim', 1.6, 2, plane='YZ', taper=0)
        for z in (-26, 0, 26):
            k.bolt((min(max(x, 10), 390), -40, z) if z == 0 else (min(max(x, 10), 390), -33, z), r=1.5)
    k.plate([(0, -40), (-30, -40), (-44, -26), (-44, 26), (-30, 40), (0, 40)], 176, 224, 'M_Trim', 1.8, 2, plane='YZ')
    k.plate(crect(182, -26, 218, 26, 3), -44, -45.4, 'M_Wall', .5, 1, taper=.4)
    k.decal((3, 1), 200, 0, 26, y=-45.5)
    k.bolts([(x, -45.4, z) for x in (184, 216) for z in (-22, 22)], r=1.2)
    for s in (-1, 1):
        _insulator(k, (200 + s * 13, -22, s * 36 * 0 + 40), (0, 0, 1))
        _insulator(k, (200 + s * 13, -22, -40), (0, 0, -1))
        k.tube([(200 + s * 13, -22, 56), (200 + s * 13, -22, 62), (200 + s * 13, 0, 62)], 2.0, 'M_Rubber', 8, rad=4)
    return k


def _tear(theta):
    """Hole radius as a function of angle; low-frequency shape plus sharp torn teeth."""
    r = 136 + 22 * math.sin(theta * 2 + 1) + 16 * math.sin(theta * 3 + .3) + 9 * math.sin(theta * 7 + 2)
    tooth = abs(((theta * 13 / (2 * math.pi) + .35 * math.sin(theta * 5)) % 1) * 2 - 1)
    return r - tooth ** 2 * 26 * (.6 + .4 * math.sin(theta * 4 + 1))


def hull_breach(samples_res=2.4):
    """400 x ~110 x 450. Pivot and tiling identical to WallPanel. Blown in from the hull side, patched with foam."""
    k = Kit('SM_Kit_HullBreach', 22)
    cx, cz = 200, 232
    k.box(0, 400, -5, 0, 0, 450, 'M_Composite', 0, align=True)
    half_rib(k, 0, 1)
    half_rib(k, 400, -1)
    k.box(0, 400, -32, 0, 0, 8, 'M_Trim', 1.0, 2)
    k.box(0, 400, -30, 0, 442, 450, 'M_Trim', 1.0, 2)
    # The torn skin: a polar sheet whose rings peel into the room near the hole.
    # The outer face keeps its paint; the inner face and lip are raw, bright, freshly torn metal.
    nt, nr = 200, 20
    verts_front, verts_back = [], []
    for j in range(nr + 1):
        t = j / nr
        for i in range(nt):
            th = 2 * math.pi * i / nt
            ct, st = math.cos(th), math.sin(th)
            sc = min(166 / max(abs(ct), 1e-4), 218 / max(abs(st), 1e-4))
            inner = _tear(th)
            r = inner + (sc - inner) * (t ** .8)
            x, z = cx + ct * r, cz + st * r
            peel = (1 - t) ** 2.8
            lobes = .55 + .45 * math.sin(th * 5 + 2) * math.sin(th * 2 + 1)
            pull = 56 * peel * lobes
            # Curl the petal: the tip turns back towards the wall.
            curl = 16 * (1 - t) ** 7 * math.sin(th * 3)
            bend = noise.noise(Vector((x * .03, z * .03, 3))) * 7 * (1 - t) ** .7
            crease = abs(noise.noise(Vector((x * .07, z * .07, 7)))) * 6 * (1 - t) ** 1.1
            y = -19 - pull - bend + crease + curl * .3
            x += ct * pull * .22 + curl * st * .6
            z += st * pull * .22 - curl * ct * .6
            verts_front.append((x, y, z))
            verts_back.append((x + ct * 1.0, y + 2.6, z + st * 1.0))
    faces_f, faces_b = [], []
    for j in range(nr):
        for i in range(nt):
            n = (i + 1) % nt
            a, b, c, d = j * nt + i, j * nt + n, (j + 1) * nt + n, (j + 1) * nt + i
            faces_f.append((d, c, b, a))
            faces_b.append((a, b, c, d))
    k.mesh_part(verts_front, faces_f, 'M_Wall')
    k.mesh_part(verts_back, faces_b, 'M_Trim')
    rim = [verts_front[i] for i in range(nt)] + [verts_back[i] for i in range(nt)]
    k.mesh_part(rim, [(nt + i, nt + (i + 1) % nt, (i + 1) % nt, i) for i in range(nt)], 'M_Trim')
    k.EDGE[-nt * 4:] = [1.0] * (nt * 4)
    # Broken stiffeners run into the hole and stop, jagged.
    for x0, x1, z, stop in ((30, 170, 84, 1), (230, 370, 84, -1), (30, 150, 346, 1), (250, 370, 346, -1)):
        k.box(min(x0, x1), max(x0, x1), -18, -5, z - 4, z + 4, 'M_Trim', .6, 2)
    # The repair is the hero: a riveted doubler welded over the hole, with sealant squeezed out around it.
    patch = crect(-112, -106, 118, 110, (22, 12, 30, 16))

    def densify(poly, step):
        out = []
        for p, q in zip(poly, poly[1:] + poly[:1]):
            n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / step))
            out += [(p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n) for i in range(n)]
        return out
    rim_pts = densify(patch, 5.0)
    with k.at(T(cx, -41, cz) @ Ry(3.5)):
        k.plate(patch, 0, -6, 'M_Wall', 1.6, 2, taper=1.0)
        # Hand-laid weld bead: lumpy, and it wanders along the edge. Closed by repeating its first point.
        bead = [(p[0] + 1.2 * noise.noise(Vector((p[0] * .1, p[1] * .1, 1))), -.6, p[1] + 1.2 * noise.noise(Vector((p[0] * .1, p[1] * .1, 2)))) for p in rim_pts]
        k.tube([Vector(p) for p in bead + bead[:1]], 2.0, 'M_Trim', 6, caps=False,
               rf=lambda f: 1 + .28 * math.sin(f * 900) + .14 * math.sin(f * 2300))
        for i, p in enumerate(densify(offset_poly(patch, -9), 26.0)):
            k.bolt((p[0], -6, p[1]), r=1.7, h=1.3)
        # A second, smaller plate where the first was not enough.
        with k.at(Ry(-9) @ T(-22, -6, 16)):
            with k.painted(CARGO):
                doubler = crect(-62, -48, 82, 44, (8, 14, 8, 20))
                k.plate(doubler, 0, -4.4, 'M_Wall', 1.1, 2, taper=.7)
            for p in densify(offset_poly(doubler, -6), 21.0):
                k.bolt((p[0], -4.4, p[1]), r=1.4, h=1.0)
            k.decal((2, 2), 8, -8, 62, y=-4.5, h=31)
    # Sealant: a pressure-fed mass behind the patch that squeezes out in beads along tear and plate edge.
    ball = bpy.data.metaballs.new('foam')
    ball.resolution = samples_res
    ball.threshold = .7
    ob = bpy.data.objects.new('foam', ball)
    bpy.context.scene.collection.objects.link(ob)
    rng = np.random.default_rng(9)
    for _ in range(26):
        th, r = rng.uniform(0, 6.283), math.sqrt(rng.uniform()) * 112
        e = ball.elements.new()
        e.co = (cx + math.cos(th) * r, rng.uniform(-12, -4), cz + math.sin(th) * r)
        e.radius = rng.uniform(38, 56)
    for i in range(120):
        th = rng.uniform(0, 6.283)
        r = _tear(th) * rng.uniform(.84, .99)
        e = ball.elements.new()
        e.co = (cx + math.cos(th) * r, rng.uniform(-34, -20), cz + math.sin(th) * r)
        e.radius = rng.uniform(13, 27)
    for p in rim_pts[::2]:
        if rng.uniform() < .62:
            e = ball.elements.new()
            e.co = (cx + p[0] * 1.03, -36 + rng.uniform(-3, 3), cz + p[1] * 1.03)
            e.radius = rng.uniform(9, 17)
    for i in range(10):
        # Runs that slumped down the wall before they cured.
        th = rng.uniform(math.pi * 1.15, math.pi * 1.85)
        r = _tear(th) * .98
        x, z = cx + math.cos(th) * r, cz + math.sin(th) * r
        for s in range(int(rng.integers(3, 7))):
            e = ball.elements.new()
            e.co = (x + rng.uniform(-2, 2), rng.uniform(-30, -25), z - s * 9)
            e.radius = 11 - s * 1.1
    bpy.context.view_layer.update()
    dep = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dep))
    bpy.data.objects.remove(ob)
    temp = bpy.data.objects.new('foam_mesh', me)
    bpy.context.scene.collection.objects.link(temp)
    dec = temp.modifiers.new('d', 'DECIMATE')
    dec.ratio = min(1.0, 22000 / max(1, len(me.polygons)))
    dep = bpy.context.evaluated_depsgraph_get()
    done = bpy.data.meshes.new_from_object(temp.evaluated_get(dep))
    verts = []
    for v in done.vertices:
        p = v.co
        # Billow, not lumps: cured sealant is rounded blisters meeting in tight creases.
        q = Vector((p.x * .06, p.y * .06, p.z * .06))
        n = 0
        for o, amp in ((1, 5.0), (2.3, 2.4), (5.1, 1.0)):
            n += abs(noise.noise(q * o)) * amp
        verts.append(tuple(p + v.normal * (n - 1.5)))
    k.mesh_part(verts, [tuple(p.vertices) for p in done.polygons], 'M_Foam')
    bpy.data.objects.remove(temp)
    # Emergency strongbacks across the patch, anchored into the ribs.
    for z, tilt in ((318, -9), (150, 7)):
        with k.at(T(200, -52, z) @ Ry(tilt)):
            k.plate(crect(-182, -9, 182, 9, 2.5), -6, 0, 'M_Trim', .9, 2)
            k.plate(crect(-148, -5, 148, 5, 1), -7, -6, 'M_Hazard', .25, 1)
            for s in (-1, 1):
                k.box(s * 170 - 8, s * 170 + 8, -2, 40, -6, 6, 'M_Trim', .8, 2)
                k.bolt((s * 176, -6, 0), r=2.0)
                k.bolt((s * 164, -6, 0), r=2.0)
    # Severed cables that fell out of the wall before the patch went on.
    for x, r, drop, xe in ((120, 1.8, 120, 116), (136, 1.2, 80, 142), (262, 2.2, 148, 272), (250, 1.3, 90, 247)):
        k.tube([(x, -14, 380), (x + 2, -40, 372), (x + 4, -66, 340), ((x + xe) / 2, -70, 300), (xe, -66, 380 - drop - 80)], r, 'M_Rubber', 8, rad=18)
    return k


def viewport():
    """400 x 62 x 300. Pivot: floor of the frame (place at 110 cm), left end, back plane. Faces -Y.
    The room walls are solid, so the view is a recessed card behind the glass (slot M_Space)."""
    k = Kit('SM_Kit_Viewport', 23)
    # Space card at the back. Its UVs tile large so the parallax of the frame does the work.
    k.box(0, 400, -3, 0, 0, 300, 'M_Composite', 0)
    k.quad([(34, -4, 34), (366, -4, 34), (366, -4, 266), (34, -4, 266)], 'M_Space', (.12, .42, .38, .62))
    W0, W1, Z0, Z1 = 40, 360, 46, 254
    win = crect(W0, Z0, W1, Z1, 34)
    outer = crect(0, 0, 400, 300, (8, 8, 54, 54))
    # Heavy stepped frame: it must look as thick as hull plate.
    k.ring(outer, offset_poly(win, 26), -4, -30, 'M_Wall', 2.0, 2, taper=2.4, align=True)
    k.ring(offset_poly(win, 28), offset_poly(win, 10), -4, -46, 'M_Trim', 1.6, 2, taper=3.5)
    k.ring(offset_poly(win, 12), win, -4, -36, 'M_Composite', .8, 2, taper=2.0)
    # Laminated glazing bars and the pane itself.
    k.plate(crect(194, Z0 - 2, 206, Z1 + 2, 1), -8, -30, 'M_Trim', .9, 2, taper=1.0)
    k.plate(crect(W0 - 2, 146, W1 + 2, 154, 1), -8, -26, 'M_Trim', .7, 2, taper=.8)
    k.box(W0, W1, -20, -19, Z0, Z1, 'M_Glass', 0, align=True)
    # Corner gussets and clamp bolts around the glazing.
    for x, z in ((26, 28), (374, 28), (26, 272), (374, 272)):
        k.bolt((x, -30, z), r=1.8)
    for s in np.linspace(58, 342, 9):
        k.bolt((float(s), -44.2, 27), r=1.2, h=1.0)
        k.bolt((float(s), -44.2, 273), r=1.2, h=1.0)
    # Glazing clamps round the frame: each carries the pane's load into the hull plate.
    for x in np.linspace(76, 324, 6):
        for z, sign in ((10, 1), (258, -1)):
            k.plate(crect(float(x) - 12, z, float(x) + 12, z + 12, 2), -29, -32.5, 'M_Wall', .7, 2, taper=.6)
            k.bolts([(float(x) + a, -32.5, z + 6) for a in (-7.5, 7.5)], r=1.1, h=.9)
    for side in (-1, 1):
        cx = 200 + side * 186
        k.plate(crect(cx - 7, 96, cx + 7, 204, 2), -28, -31, 'M_Wall', .7, 2, taper=.6)
        k.bolts([(cx, -31, z) for z in (106, 150, 194)], r=1.2, h=1.0)
    # Shutter housing with a half-lowered armoured blind.
    k.plate(crect(-2, 268, 402, 322, (2, 2, 12, 12)), -2, -50, 'M_Trim', 1.8, 2, taper=1.2)
    k.box(14, 386, -50.6, -49.6, 286, 306, 'M_Composite', .3, 1)
    k.box(26, 374, -51.4, -50.2, 293, 298, 'M_Light', 0)
    for x in np.linspace(40, 360, 9):
        k.box(float(x) - 1.2, float(x) + 1.2, -52.2, -49.8, 288, 304, 'M_Trim', .3, 1)
    k.box(14, 386, -51, -49.6, 272, 282, 'M_Composite', .3, 1)
    for i in range(3):
        z = 254 - i * 11
        with k.at(T(0, -34, z) @ Rx(-8)):
            k.box(W0 + 4, W1 - 4, -2.4, 2.4, -4.9, 4.9, 'M_Wall', .7, 2)
    for x in (56, 344):
        k.box(x - 3, x + 3, -36, -33, 216, 268, 'M_Trim', .5, 1)
    # Sill rail, for leaning on.
    k.box(4, 396, -44, -4, 0, 14, 'M_Trim', 1.2, 2)
    for x in (46, 354):
        k.tube([(x, -46, 12), (x, -60, 26)], 2.0, 'M_Trim', 10)
    k.tube([(4, -60, 28), (396, -60, 28)], 2.4, 'M_Wall', 12)
    return k


def column():
    """122 x 122 x 450. Pivot: floor, centre. Stands free; fits the 140 cm cover pillars at 1.15 scale."""
    k = Kit('SM_Kit_Column', 24)
    H = 450
    # Core and four corner chords. Each face keeps a channel so the column is not a box.
    core = crect(-44, -44, 44, 44, 14)
    k.plate(core, 4, H - 8, 'M_Composite', .8, 1, plane='XY')
    chord = crect(36, 36, 61, 61, (2, 2, 6, 2))
    for i in range(4):
        with k.at(Rz(90 * i)):
            k.plate(chord, 40, H - 34, 'M_Wall', 1.4, 2, plane='XY', align=True)
            for z in (96, 232, 372):
                k.box(61, 63, 41, 58, z - 15, z + 15, 'M_Trim', .5, 2)
                k.box(41, 58, 61, 63, z - 15, z + 15, 'M_Trim', .5, 2)
                for a in (-9, 9):
                    k.bolts([(63, 49.5, z + a)], (1, 0, 0), 1.2, 1.0)
                    k.bolts([(49.5, 63, z + a)], (0, 1, 0), 1.2, 1.0)
    # Base: a stepped plinth with anchor bolts, the column's visual weight.
    k.plate(crect(-84, -84, 84, 84, 14), 0, 10, 'M_Trim', 1.6, 2, plane='XY', taper=1.8)
    k.plate(crect(-74, -74, 74, 74, 12), 10, 44, 'M_Wall', 1.4, 2, plane='XY', taper=5)
    k.ring(crect(-71, -71, 71, 71, 12), crect(-66, -66, 66, 66, 10), 22, 30, 'M_Hazard', .3, 1, plane='XY')
    k.bolts([(sx * 76, sy * 76 * f, 10) for sx in (-1, 1) for sy in (-1, 1) for f in (.1, .75)]
            + [(sx * 76 * .4, sy * 76, 10) for sx in (-1, 1) for sy in (-1, 1)], (0, 0, 1), 2.1, 1.6)
    # Waist collar with a meridian light band at the same height as the wall strip.
    k.plate(crect(-67, -67, 67, 67, 16), 290, 300, 'M_Trim', 1.2, 2, plane='XY', taper=-.0)
    k.plate(crect(-67, -67, 67, 67, 16), 316, 326, 'M_Trim', 1.2, 2, plane='XY')
    k.plate(crect(-60, -60, 60, 60, 14), 300, 316, 'M_Composite', .3, 1, plane='XY')
    k.ring(crect(-62.5, -62.5, 62.5, 62.5, 14), crect(-58, -58, 58, 58, 13), 306, 310, 'M_Light', 0, plane='XY')
    # Lower collar: a heavy strap at hip height.
    k.plate(crect(-65, -65, 65, 65, 14), 150, 170, 'M_Trim', 1.2, 2, plane='XY', taper=.5)
    # Capital: flared knee braces that hand the load out to the ceiling.
    k.plate(crect(-84, -84, 84, 84, 16), H - 18, H, 'M_Trim', 1.6, 2, plane='XY', taper=-.0)
    k.plate(crect(-62, -62, 62, 62, 10), H - 42, H - 18, 'M_Wall', 1.2, 2, plane='XY', taper=-8)
    for i in range(4):
        with k.at(Rz(90 * i)):
            gus = [(44, H - 96), (80, H - 18), (44, H - 18)]
            for y in (-14, 8):
                with k.at(T(0, y, 0)):
                    k.plate(gus, 0, 6, 'M_Trim', .9, 2)
            # Face channels: a riser on one face, a service plate on the others.
            if i == 0:
                k.tube([(0, -50, 44), (0, -50, H - 18)], 6, 'M_Trim', 14)
                for z in (60, 134, 200, 270, 350):
                    k.box(-9, 9, -48, -40, z - 3, z + 3, 'M_Trim', .6, 1)
                    with k.at(aim((0, -50, z), (0, 0, 1))):
                        k.lathe([(6, -3), (7.4, -2.4), (7.4, 2.4), (6, 3)], 'M_Trim', 16, .2, edge=.5)
            elif i == 1:
                k.plate(crect(-28, 186, 28, 278, 4), -44, -46.8, 'M_Wall', .6, 2, taper=.6)
                k.decal((2, 1), 0, 234, 36, y=-46.9, h=18)
                k.plate(crect(-28, 58, 28, 142, 4), -44, -46.8, 'M_Wall', .6, 2, taper=.6)
                k.ring(crect(-20, 66, 20, 134, 2), crect(-17, 69, 17, 131, 1), -46.8, -47.6, 'M_Trim', .2, 1)
            elif i == 2:
                for off, r in ((-12, 1.8), (-6, 1.3), (1, 2.2), (9, 1.5)):
                    k.tube([(off, -47, 44), (off, -47, H - 18)], r, 'M_Rubber', 8)
                for z in (84, 200, 340):
                    k.box(-22, 22, -50.5, -44, z - 3, z + 3, 'M_Trim', .6, 2)
            else:
                k.plate(crect(-28, 186, 28, 278, 4), -44, -46.8, 'M_Wall', .6, 2, taper=.6)
                k.box(-16, 16, -48.2, -46.6, 236, 262, 'M_Hazard', .3, 1)
    return k


BUILD = {
    'WallPanel': wall_panel, 'CeilingTruss': ceiling_truss, 'FloorTrim': floor_trim, 'FloorVent': floor_vent,
    'PipeRun': pipe_run, 'DoorFrame': door_frame,
    'BlastDoor': lambda: blast_door(0), 'BlastDoor_L': lambda: blast_door(-1), 'BlastDoor_R': lambda: blast_door(1),
    'Console': console, 'Terminal': terminal,
    'CrateLarge': lambda: crate('SM_Kit_CrateLarge', 200, 200, 140, 31), 'CrateSmall': lambda: crate('SM_Kit_CrateSmall', 100, 100, 80, 32),
    'WeaponRack': weapon_rack, 'PowerConduit': power_conduit, 'HullBreach': hull_breach, 'Viewport': viewport, 'Column': column,
}
PREVIEW_SKIP = ('BlastDoor_L', 'BlastDoor_R')


# -------------------------------------------------------------------------------- owned textures

def tile_noise(size, seed, turns=6, base=2):
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size))
    for octave in range(turns):
        f = base * 2 ** octave
        grid = rng.normal(0, 1, (f, f))
        cells = np.fft.ifft2(np.fft.fft2(grid), s=None)
        coords = np.arange(size) * f / size
        i = coords.astype(int) % f
        t = coords - np.floor(coords)
        t = t * t * (3 - 2 * t)
        j = (i + 1) % f
        a = grid[i][:, i] * (1 - t)[:, None] + grid[j][:, i] * t[:, None]
        b = grid[i][:, j] * (1 - t)[:, None] + grid[j][:, j] * t[:, None]
        out += (a * (1 - t)[None, :] + b * t[None, :]) / 2 ** octave
    return (out - out.min()) / (out.max() - out.min())


def height_normal(height, strength):
    """DirectX normal map from tiling height; rows increase downward, so green is -dh/drow."""
    dx = np.roll(height, -1, 1) - np.roll(height, 1, 1)
    dy = np.roll(height, -1, 0) - np.roll(height, 1, 0)
    nx, ny, nz = -dx * strength, -dy * strength, np.ones_like(height)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack((nx / length, ny / length, nz / length)) * .5 + .5


def foam_textures():
    size = 2048
    rng = np.random.default_rng(3)
    # Toroidal cell field: bubbles of three sizes, the large ones broken open.
    height = np.zeros((size, size))
    yy, xx = np.mgrid[0:size, 0:size]
    for count, radius, depth in ((40, 30, .7), (700, 11, .45), (16000, 3.5, .3)):
        canvas = np.zeros((size, size))
        pos = rng.integers(0, size, (count, 2))
        rad = rng.uniform(.5, 1.25, count) * radius
        r = int(radius * 1.3) + 1
        by, bx = np.mgrid[-r:r + 1, -r:r + 1]
        for (py, px), q in zip(pos, rad):
            d = np.clip(1 - (bx * bx + by * by) / (q * q), 0, 1)
            ys = (py + by) % size
            xs = (px + bx) % size
            canvas[ys, xs] = np.maximum(canvas[ys, xs], d)
        height -= canvas * depth
    lump = tile_noise(size, 5, 5, 3)
    height = height * .55 + lump * 1.3
    height = (height - height.min()) / (height.max() - height.min())
    tone = tile_noise(size, 6, 5, 4)[..., None]
    pits = np.clip((.5 - height) * 3, 0, 1)[..., None]
    pale, deep = np.array((.5, .49, .44)), np.array((.1, .095, .08))
    base = pale * (.76 + tone * .34)
    base = base * (1 - pits) + deep * pits
    ao = np.clip(height * 1.5 + .25, 0, 1)
    orm = np.dstack((ao, .62 + (1 - height) * .3, np.zeros_like(height)))
    write_png(TEX / 'T_KitFoam_BaseColor.png', np.clip(base, 0, 1) ** (1 / 2.2), 8)
    write_png(TEX / 'T_KitFoam_Normal.png', height_normal(height, 14), 16)
    write_png(TEX / 'T_KitFoam_ORM.png', orm, 8)


def scratches(size, rng, count, lengths, curve=.0008):
    """Seamless thin random scratches, accumulated on a torus."""
    canvas = np.zeros((size, size), np.float32)
    for _ in range(count):
        n = int(rng.uniform(*lengths))
        a = rng.uniform(0, 6.283) + np.cumsum(rng.normal(0, curve * 40, n)) * .05
        x = rng.uniform(0, size) + np.cumsum(np.cos(a))
        y = rng.uniform(0, size) + np.cumsum(np.sin(a))
        taper = np.sin(np.linspace(0, math.pi, n)) ** .6 * rng.uniform(.2, 1)
        np.maximum.at(canvas, (y.astype(int) % size, x.astype(int) % size), taper)
    return canvas


def soft(a, passes=2):
    for _ in range(passes):
        a = (a * 2 + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 6
    return a


def paint_textures():
    """Clean, tiling, paint-only surfaces. All panel logic is modelled, so these carry no lines or type."""
    size = 2048
    rng = np.random.default_rng(21)
    peel = tile_noise(size, 31, 3, 180)
    big = tile_noise(size, 32, 5, 3)
    mid = tile_noise(size, 33, 6, 14)
    fine = scratches(size, rng, 900, (30, 260))
    deep = scratches(size, rng, 60, (120, 520))
    # Height in arbitrary units: orange peel, slow undulation of plate, then scratches through the coat.
    height = peel * .10 + big * .22 - soft(fine, 1) * .05 - soft(deep, 1) * .12
    # Small nicks, clustered by a slow mask so whole tiles stay clean.
    chip = np.clip((tile_noise(size, 34, 4, 90) - .73) * 30, 0, 1) * np.clip((tile_noise(size, 35, 3, 4) - .52) * 9, 0, 1)
    height = height - soft(chip, 1) * .12
    albedo = .70 * (.86 + big * .2 + (mid - .5) * .12)
    albedo = albedo + fine * .06 + deep * .08
    colour = np.dstack((albedo, albedo, albedo * .985))
    primer = np.array((.30, .29, .28))
    colour = colour * (1 - chip[..., None]) + primer * chip[..., None]
    rough = .50 + (mid - .5) * .16 + (big - .5) * .1 + chip * .2 - deep * .12
    ao = 1 - soft(deep + chip, 2) * .35
    write_png(TEX / 'T_KitPaint_BaseColor.png', np.clip(colour, 0, 1) ** (1 / 2.2), 8)
    write_png(TEX / 'T_KitPaint_Normal.png', height_normal(height, 5.0), 16)
    write_png(TEX / 'T_KitPaint_ORM.png', np.dstack((ao, np.clip(rough, 0, 1), np.zeros_like(ao))), 8)
    # Bead-blasted gunmetal with a faint rolling direction along U: cool, and never wood.
    blast = tile_noise(size, 41, 2, 300)
    grain = tile_noise(size, 42, 4, 40)
    # Stretch the grain along rows by averaging it across columns.
    for shift in (3, 7, 17, 41, 97):
        grain = (grain + np.roll(grain, shift, 1)) / 2
    wearlines = scratches(size, rng, 1500, (40, 340))
    dings = np.clip((tile_noise(size, 43, 6, 7) - .73) * 18, 0, 1)
    height = blast * .07 + (grain - .5) * .05 - soft(wearlines, 1) * .025 - soft(dings, 2) * .18
    mottle = tile_noise(size, 44, 6, 5)
    v = .40 + (mottle - .5) * .14 + (grain - .5) * .08 + wearlines * .07
    colour = np.dstack((v * .94, v * .98, v * 1.05))
    rough = .40 + (mottle - .5) * .22 + (blast - .5) * .10 - wearlines * .12 + dings * .1
    ao = np.ones_like(rough)
    write_png(TEX / 'T_KitMetal_BaseColor.png', np.clip(colour, 0, 1) ** (1 / 2.2), 8)
    write_png(TEX / 'T_KitMetal_Normal.png', height_normal(height, 4.0), 16)
    write_png(TEX / 'T_KitMetal_ORM.png', np.dstack((ao, np.clip(rough, 0, 1), np.ones_like(ao))), 8)
    # LED diffuser: soft emitter bands, so lamps carry structure instead of clipping to flat white.
    n = 512
    yy, xx = np.mgrid[0:n, 0:n]
    bands = .5 + .5 * np.cos(yy / n * 2 * math.pi * 6)
    dots = .5 + .5 * np.cos(xx / n * 2 * math.pi * 24)
    e = .62 + bands * .30 + bands * dots * .10 + (tile_noise(n, 45, 4, 4) - .5) * .08
    write_png(TEX / 'T_KitLight_Emissive.png', np.dstack((e, e, e)) ** (1 / 2.2), 8)


def _text_scene():
    scene = bpy.data.scenes.new('kit_atlas')
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 2048
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    scene.display_settings.display_device = 'sRGB'
    world = bpy.data.worlds.new('none')
    scene.world = world
    cam = bpy.data.cameras.new('atlas')
    cam.type = 'ORTHO'
    cam.ortho_scale = 4
    ob = bpy.data.objects.new('atlas', cam)
    ob.location = (2, 2, 5)
    scene.collection.objects.link(ob)
    scene.camera = ob
    mat = bpy.data.materials.new('atlas_white')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    em = nodes.new('ShaderNodeEmission')
    out = nodes.new('ShaderNodeOutputMaterial')
    em.inputs[0].default_value = (1, 1, 1, 1)
    mat.node_tree.links.new(em.outputs[0], out.inputs[0])
    return scene, mat


def decal_textures():
    """4x4 stencil atlas, rendered from real type and then worn; white is tinted per cell."""
    scene, mat = _text_scene()

    def text(body, col, row, size=.26, y=.5, x=.5, bold=.012):
        cu = bpy.data.curves.new('t', 'FONT')
        cu.body = body
        cu.size = size
        cu.align_x, cu.align_y = 'CENTER', 'CENTER'
        cu.offset = bold
        cu.space_character = 1.12
        cu.materials.append(mat)
        ob = bpy.data.objects.new('t', cu)
        ob.location = (col + x, 3 - row + y, 0)
        scene.collection.objects.link(ob)

    def poly(pts, col, row):
        me = bpy.data.meshes.new('p')
        me.from_pydata([(p[0], p[1], 0) for p in pts], [], [list(range(len(pts)))])
        me.materials.append(mat)
        ob = bpy.data.objects.new('p', me)
        ob.location = (col, 3 - row, 0)
        scene.collection.objects.link(ob)

    text('MERIDIAN', 0, 0, .19, .58)
    text('STATION  04', 0, 0, .1, .36)
    text('MFS', 1, 0, .34, .6)
    text('CARGO 7A', 1, 0, .12, .33)
    text('DECK 3', 2, 0, .22, .62)
    text('FRAME 118', 2, 0, .11, .38)
    poly([(.08, .3), (.5, .3), (.5, .16), (.92, .5), (.5, .84), (.5, .7), (.08, .7)], 3, 0)
    # Warning triangle and lightning glyph.
    poly([(.5, .94), (.97, .1), (.03, .1)], 0, 1)
    poly([(.54, .72), (.4, .46), (.5, .46), (.42, .22), (.62, .52), (.52, .52), (.62, .72)], 0, 2)
    text('ACCESS', 1, 1, .22, .62)
    text('PANEL', 1, 1, .22, .34)
    text('C-14', 2, 1, .3, .6)
    text('LOAD 400 KG', 2, 1, .09, .3)
    text('HV', 3, 1, .36, .62)
    text('12 KV', 3, 1, .13, .28)
    text('NO STEP', 1, 2, .16)
    text('SEALED', 2, 2, .19)
    text('PRESSURE', 3, 2, .13, .62)
    text('BULKHEAD', 3, 2, .13, .38)
    for i, code in enumerate(('01', '02', '03', '04')):
        text(code, i, 3, .36)
    scene.render.filepath = str(TEX / '_decal_raw.png')
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    bpy.ops.render.render(write_still=True, scene=scene.name)
    img = bpy.data.images.load(scene.render.filepath)
    px = np.array(img.pixels[:], np.float32).reshape(2048, 2048, 4)[::-1]
    alpha = px[..., 3]
    # Wear: chips and overspray make it paint, not a font.
    wear = tile_noise(2048, 8, 7, 12)
    alpha = alpha * np.clip((wear - .24) * 7, 0, 1) * .94
    colour = np.ones((2048, 2048, 3)) * np.array((.86, .86, .82))
    colour[1024 + 0:1536, :, :] *= 1
    colour[512:1024, 0:512] = (.92, .62, .08)
    colour[1024:1536, 0:512] = (.08, .08, .08)
    colour[1024:1536, 512:1024] = (.74, .1, .06)
    colour[1024:1536, 1024:1536] = (.74, .1, .06)
    colour[512:1024, 1536:2048] = (.92, .62, .08)
    write_png(TEX / 'T_KitDecal_BaseColor.png', np.dstack((colour ** (1 / 2.2), alpha)), 8)
    bpy.data.images.remove(img)
    (TEX / '_decal_raw.png').unlink()
    bpy.data.scenes.remove(scene)


def screen_type():
    """Render the type layer of the screen atlas with a real font. Returns premultiplied RGB and alpha."""
    scene, white = _text_scene()
    bpy.data.objects['atlas'].location = (1.5, 1.5, 5)
    bpy.data.cameras['atlas'].ortho_scale = 3
    rng = np.random.default_rng(14)
    mats = {}

    def ink(colour):
        if colour not in mats:
            m = white.copy()
            m.node_tree.nodes['Emission'].inputs[0].default_value = (*colour, 1)
            mats[colour] = m
        return mats[colour]
    ICE, GOLD, RED, WHITE = (.32, .72, 1), (1, .62, .14), (1, .16, .08), (1, 1, 1)

    def text(cell, x, y, body, size=.03, colour=ICE):
        col, row = cell
        cu = bpy.data.curves.new('t', 'FONT')
        cu.body = body
        cu.size = size
        cu.materials.append(ink(colour))
        ob = bpy.data.objects.new('t', cu)
        ob.location = (col + x, 3 - row - y, 0)
        scene.collection.objects.link(ob)

    def head(cell, title, code):
        text(cell, .03, .048, title, .03, (0, 0, 0))
        text(cell, .78, .048, code, .03, (0, 0, 0))

    def code(n):
        return ''.join(rng.choice(list('0123456789ABCDEF'), n))
    verbs = ('SEAL', 'VENT', 'PURGE', 'CYCLE', 'ROUTE', 'HOLD', 'ARM', 'SYNC', 'TRIM')
    parts = ('BLKHD', 'FRAME', 'BUS-A', 'COIL', 'ATMO', 'DECK', 'LOCK', 'PDC', 'SPINE')

    def log(cell, x, y, rows, gap=.031, size=.0235, colour=ICE):
        for r in range(rows):
            line = f'{int(rng.integers(0, 24)):02d}:{int(rng.integers(0, 60)):02d}  {rng.choice(verbs):5s} {rng.choice(parts):5s}-{int(rng.integers(1, 99)):02d}  {code(4)}  {rng.choice(("OK", "OK", "OK", "ACK", "WAIT"))}'
            text(cell, x, y + r * gap, line, size, colour)

    head((0, 0), 'FLEET TACTICAL  //  MERIDIAN', 'SWP 06')
    for i, label in enumerate(('CONTACTS   12', 'HOSTILE     6', 'CLOSING   41 KM', 'FIRST ONES', 'BRG 212.6', 'ELV 014.2', 'TTI 08:41')):
        text((0, 0), .8, .11 + i * .036, label, .022, RED if i in (1, 3) else ICE)
    log((0, 0), .8, .52, 12, .03, .0145)
    head((1, 0), 'STATION  HULL  STATUS', 'D-07')
    for i in range(8):
        text((1, 0), .07 + i * .105, .68, f'D{i + 1:02d}', .022, RED if i == 7 else GOLD if i in (2, 3) else ICE)
    log((1, 0), .07, .75, 7, .03)
    text((2, 0), .07, .09, 'COMMS LOG  //  CHANNEL 4  //  ENCRYPTED', .026, GOLD)
    log((2, 0), .07, .15, 18, .0285)
    text((2, 0), .13, .73, 'PRESSURE LOSS  DECK 07', .043, WHITE)
    text((2, 0), .13, .785, 'EVACUATE FRAME 118 TO 126', .03, WHITE)
    log((2, 0), .07, .86, 4, .0285, .0235, GOLD)
    head((0, 1), 'REACTOR  BUS  WAVEFORM', '12 KV')
    for i, (label, y, c) in enumerate((('PHASE A  398.2', .1, GOLD), ('PHASE B  401.7', .36, ICE), ('PHASE C  OUT OF BAND', .62, RED))):
        text((0, 1), .05, y, label, .024, c)
    log((0, 1), .06, .86, 4, .03)
    head((1, 1), 'SYSTEM  INTEGRITY', 'ROLL UP')
    for i in range(14):
        text((1, 1), .062 + i * .0644, .845, f'{i + 1:02d}', .017, ICE)
    log((1, 1), .06, .89, 3, .03)
    text((2, 1), .12, .49, 'LOCKDOWN', .13, WHITE)
    text((2, 1), .13, .57, 'BLAST DOORS SEALED  //  AUTH REQUIRED', .03, WHITE)
    head((0, 2), 'BOARDING  MAP', 'DECK 07')
    for i in range(16):
        text((0, 2), rng.uniform(.08, .8), rng.uniform(.12, .9), f'{rng.choice(parts)} {int(rng.integers(1, 99)):02d}', .02, ICE)
    text((1, 2), .06, .06, 'MAINTENANCE QUEUE', .03, GOLD)
    log((1, 2), .06, .11, 30, .029)
    text((2, 2), .39, .5, 'STANDBY', .05, GOLD)
    text((2, 2), .32, .9, 'MERIDIAN STATION 04', .03, GOLD)
    scene.render.resolution_x = scene.render.resolution_y = 2049
    scene.cycles.samples = 24
    scene.render.filepath = str(TEX / '_screen_raw.png')
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = str(TEX / '_screen_raw.exr')
    bpy.ops.render.render(write_still=True, scene=scene.name)
    img = bpy.data.images.load(scene.render.filepath)
    px = np.array(img.pixels[:], np.float32).reshape(2049, 2049, 4)[::-1]
    bpy.data.images.remove(img)
    (TEX / '_screen_raw.exr').unlink()
    bpy.data.scenes.remove(scene)
    return px[..., :3], px[..., 3:]


def screen_textures():
    """3x3 atlas of operating displays: drawn graphics under real rendered type, with a soft phosphor bloom."""
    cell = 683
    size = cell * 3
    out = np.zeros((size, size, 3))
    rng = np.random.default_rng(14)
    ice, gold, red = np.array((.32, .72, 1)), np.array((1, .62, .14)), np.array((1, .16, .08))

    def field():
        yy, xx = np.mgrid[0:cell, 0:cell]
        c = np.zeros((cell, cell, 3)) + np.array((.008, .02, .032))
        minor = ((xx % 24) < 1) | ((yy % 24) < 1)
        major = ((xx % 120) < 1.5) | ((yy % 120) < 1.5)
        c += minor[..., None] * ice * .025 + major[..., None] * ice * .06
        return c, xx, yy

    def box(c, x0, y0, x1, y1, colour, t=2):
        c[y0:y0 + t, x0:x1] = colour
        c[y1 - t:y1, x0:x1] = colour
        c[y0:y1, x0:x0 + t] = colour
        c[y0:y1, x1 - t:x1] = colour

    # 0,0 fleet tactical: range rings, contacts, a bearing sweep.
    c, xx, yy = field()
    cx, cy = cell * .4, cell * .52
    r = np.hypot(xx - cx, yy - cy)
    ang = np.arctan2(yy - cy, xx - cx)
    for ring in (80, 160, 240):
        c += (np.abs(r - ring) < 1.2)[..., None] * ice * .4
    sweep = np.mod(ang + .6, 6.283)
    c += ((r < 240) * np.exp(-sweep * 2.2))[..., None] * ice * .3
    for _ in range(12):
        a, q = rng.uniform(0, 6.28), rng.uniform(40, 235)
        px, py = int(cx + math.cos(a) * q), int(cy + math.sin(a) * q)
        col = red if rng.uniform() < .5 else ice
        box(c, px - 7, py - 7, px + 7, py + 7, col)
        c[py - 2:py + 2, px - 2:px + 2] = col
    c[:46, :] = gold * .8
    box(c, int(cell * .78), 56, cell - 16, cell - 16, ice * .4, 1)
    out[0:cell, 0:cell] = c
    # 0,1 station schematic: decks in profile with their status.
    c, xx, yy = field()
    y0, y1 = int(cell * .2), int(cell * .62)
    for i in range(8):
        x = 46 + i * 72
        tall = int(16 * (3 - abs(i - 3.5)))
        status = gold if i in (2, 3) else red if i == 7 else ice
        c[y0 - tall:y1 + tall // 2, x:x + 62] = status * .13
        box(c, x, y0 - tall, x + 62, y1 + tall // 2, status)
    c[:46, :] = ice * .7
    out[0:cell, cell:cell * 2] = c
    # 0,2 terminal: a tall comms log with a warning block.
    c, xx, yy = field()
    c[int(cell * .67):int(cell * .81), 50:cell - 50] = red * .55
    box(c, 50, int(cell * .67), cell - 50, int(cell * .81), red)
    out[0:cell, cell * 2:] = c
    # 1,0 power waveforms.
    c, xx, yy = field()
    x = np.arange(cell)
    for col, base, amp, freq in ((gold, 150, 56, 13), (ice, 325, 80, 7), (red, 500, 34, 27)):
        wave = base + amp * np.sin(x / cell * freq * 6.283) * (1 + .4 * np.sin(x / cell * 3.1))
        for i in x:
            y = int(wave[i])
            c[y - 2:y + 2, i] = col
            c[min(y, base):max(y, base), i] += col * .05
    c[:46, :] = gold * .8
    out[cell:cell * 2, 0:cell] = c
    # 1,1 bars of system health.
    c, xx, yy = field()
    for i in range(14):
        v = rng.uniform(.25, 1)
        x = 40 + i * 44
        tall = int(v * 460)
        col = red if v < .35 else gold if v < .6 else ice
        c[560 - tall:560, x:x + 30] = col * .55
        c[560 - tall:560 - tall + 3, x:x + 30] = col
    c[:46, :] = ice * .7
    out[cell:cell * 2, cell:cell * 2] = c
    # Remaining cells: a lockdown alarm, a boarding map and a standby page.
    c, xx, yy = field()
    band = np.mod(xx + yy, 120) < 60
    c[:70] = np.where(band[:70][..., None], gold, 0.015)
    c[-70:] = np.where(band[-70:][..., None], gold, 0.015)
    c[250:430, 50:cell - 50] = red * .55
    box(c, 50, 250, cell - 50, 430, red)
    out[cell:cell * 2, cell * 2:] = c
    c, xx, yy = field()
    for _ in range(26):
        a, b = rng.integers(40, cell - 150, 2)
        w, h = rng.integers(40, 150, 2)
        box(c, a, b, a + w, b + h, ice * .55)
        c[b:b + h, a:a + w] += ice * .03
    c[:46, :] = ice * .7
    out[cell * 2:, 0:cell] = c
    c, xx, yy = field()
    out[cell * 2:, cell:cell * 2] = c
    c, xx, yy = field()
    c += (np.abs(np.hypot(xx - cell / 2, yy - cell / 2) - 200) < 3)[..., None] * gold
    out[cell * 2:, cell * 2:] = c
    rgb, alpha = screen_type()
    out = out * (1 - alpha) + rgb
    # Phosphor bloom and a dim scanline; a little edge fall-off per cell sells the glass.
    bloom = out.copy()
    for _ in range(3):
        bloom = soft(bloom[::1], 3)
    out = out + bloom * .28
    edge = np.mgrid[0:size].astype(np.float32) % cell / cell
    fall = (.72 + .28 * np.clip(np.sin(edge * math.pi) * 3, 0, 1))
    out = out * fall[:, None, None] * fall[None, :, None]
    scan = (.9 + .1 * np.sin(np.arange(size) * 2.09))[:, None, None]
    write_png(TEX / 'T_KitScreen_Emissive.png', (np.clip(out * scan, 0, 1) ** (1 / 2.2))[:2048, :2048], 8)


# ----------------------------------------------------------------------------------- mask baking

def _node(tree, kind, **values):
    n = tree.nodes.new(kind)
    for key, value in values.items():
        setattr(n, key, value)
    return n


def bake_mask(ob, samples=48):
    """R = occlusion, G = edge wear, B = grime. Written to T_KitMask_<name> and used on UV1."""
    scene = bpy.context.scene
    size = MASK_SIZE.get(ob.name, 1024)
    name = 'T_KitMask_' + ob.name[len('SM_Kit_'):]
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    mat = bpy.data.materials.new('bake_' + ob.name)
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    L = t.links.new
    out = _node(t, 'ShaderNodeOutputMaterial')
    em = _node(t, 'ShaderNodeEmission')
    L(em.outputs[0], out.inputs[0])
    tight = _node(t, 'ShaderNodeAmbientOcclusion', samples=12, only_local=True)
    tight.inputs['Distance'].default_value = 16
    wide = _node(t, 'ShaderNodeAmbientOcclusion', samples=12, only_local=True)
    wide.inputs['Distance'].default_value = 90
    attr = _node(t, 'ShaderNodeVertexColor', layer_name='Col')
    sep = _node(t, 'ShaderNodeSeparateColor')
    L(attr.outputs[0], sep.inputs[0])
    coord = _node(t, 'ShaderNodeTexCoord')
    geo = _node(t, 'ShaderNodeNewGeometry')
    fine = _node(t, 'ShaderNodeTexNoise')
    fine.inputs['Scale'].default_value = .2
    fine.inputs['Detail'].default_value = 7
    fine.inputs['Roughness'].default_value = .62
    L(coord.outputs['Object'], fine.inputs['Vector'])
    broad = _node(t, 'ShaderNodeTexNoise')
    broad.inputs['Scale'].default_value = .018
    broad.inputs['Detail'].default_value = 5
    L(coord.outputs['Object'], broad.inputs['Vector'])
    # Streaks fall under gravity: squash object space on Z so noise runs vertically.
    mapping = _node(t, 'ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (1, 1, .06)
    L(coord.outputs['Object'], mapping.inputs['Vector'])
    streak = _node(t, 'ShaderNodeTexNoise')
    streak.inputs['Scale'].default_value = .12
    streak.inputs['Detail'].default_value = 4
    L(mapping.outputs[0], streak.inputs['Vector'])

    def math_node(op, a, b=None, clamp=True):
        n = _node(t, 'ShaderNodeMath', operation=op, use_clamp=clamp)
        for socket, value in zip(n.inputs, (a, b)):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                socket.default_value = value
            else:
                L(value, socket)
        return n.outputs[0]

    def ramp(value, a, b):
        n = _node(t, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        L(value, n.inputs['Value'])
        n.inputs['From Min'].default_value = a
        n.inputs['From Max'].default_value = b
        return n.outputs[0]
    # Occlusion: tight contact shadow plus soft large-scale fall-off.
    occ = math_node('MULTIPLY', ramp(tight.outputs['AO'], 0.0, .85), math_node('ADD', math_node('MULTIPLY', wide.outputs['AO'], .55), .45))
    # Edge wear: flagged bevels, chipped into islands; a light scuff in broad patches.
    chips = ramp(fine.outputs[0], .42, .60)
    patches = ramp(broad.outputs[0], .46, .6)
    wear = math_node('MULTIPLY', sep.outputs[0], math_node('MULTIPLY', chips, math_node('ADD', math_node('MULTIPLY', patches, .45), .3)))
    # Grime collects in cavities, on upward faces, and in streaks under fixings.
    cavity = math_node('MULTIPLY', math_node('SUBTRACT', 1, wide.outputs['AO']), 2.0)
    sepn = _node(t, 'ShaderNodeSeparateXYZ')
    L(geo.outputs['Normal'], sepn.inputs[0])
    up = math_node('MULTIPLY', ramp(sepn.outputs[2], .6, .98), ramp(broad.outputs[0], .38, .62))
    run = math_node('MULTIPLY', ramp(streak.outputs[0], .5, .68), math_node('MULTIPLY', ramp(broad.outputs[0], .35, .6), .55))
    grime = math_node('MAXIMUM', math_node('MAXIMUM', math_node('MULTIPLY', cavity, ramp(broad.outputs[0], .3, .62)), up), run)
    if ob.name == 'SM_Kit_HullBreach':
        # Blast soot, thrown outward from the hole and broken up by the noise.
        dist = _node(t, 'ShaderNodeVectorMath', operation='DISTANCE')
        L(coord.outputs['Object'], dist.inputs[0])
        dist.inputs[1].default_value = (200, -30, 232)
        soot = math_node('MULTIPLY', ramp(dist.outputs['Value'], 215, 165), math_node('MULTIPLY', broad.outputs[0], 1.0))
        grime = math_node('MAXIMUM', grime, soot)
    comb = _node(t, 'ShaderNodeCombineColor')
    L(occ, comb.inputs[0])
    L(wear, comb.inputs[1])
    L(grime, comb.inputs[2])
    L(comb.outputs[0], em.inputs[0])
    tex = _node(t, 'ShaderNodeTexImage', image=img)
    t.nodes.active = tex
    # Bake on a copy so the original keeps its material slots; every face takes one material.
    me = ob.data.copy()
    skip = [i for i, m in enumerate(ob.data.materials) if m.name.split('.')[0] in ('M_Decal', 'M_Glass')]
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in skip], context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(mat)
    me.polygons.foreach_set('material_index', [0] * len(me.polygons))
    me.uv_layers.active = me.uv_layers['UVMask']
    me.uv_layers['UVMask'].active_render = True
    temp = bpy.data.objects.new('bake', me)
    scene.collection.objects.link(temp)
    bpy.ops.object.select_all(action='DESELECT')
    temp.select_set(True)
    bpy.context.view_layer.objects.active = temp
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    bpy.ops.object.bake(type='EMIT', margin=10, margin_type='EXTEND', use_clear=True, target='IMAGE_TEXTURES')
    px = np.array(img.pixels[:], np.float32).reshape(size, size, 4)[::-1, :, :3]
    write_png(TEX / (name + '.png'), px, 8)
    bpy.data.objects.remove(temp)
    bpy.data.meshes.remove(me)
    bpy.data.materials.remove(mat)
    return img


# -------------------------------------------------------------------------------- preview shading

BASES = {'M_Wall': ((.2, .25, .3), .46, 0), 'M_Trim': ((.17, .18, .2), .36, .9), 'M_Composite': ((.05, .055, .062), .52, 0),
         'M_Deck': ((.11, .115, .12), .46, .8), 'M_Ceiling': ((.26, .27, .28), .6, 0), 'M_Hazard': ((.72, .5, .04), .5, 0),
         'M_Rubber': ((.012, .012, .014), .62, 0), 'M_Foam': ((.5, .3, .08), .75, 0)}


def load(path, non_color=True):
    if not Path(path).exists():
        return None
    img = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    return img


def preview_material(slot, mask, owner):
    mat = bpy.data.materials.new(slot + '_' + owner)
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    L = t.links.new
    out = _node(t, 'ShaderNodeOutputMaterial')
    uv = _node(t, 'ShaderNodeUVMap', uv_map='UVMap')
    if slot in ('M_Light', 'M_Screen', 'M_Space'):
        em = _node(t, 'ShaderNodeEmission')
        L(em.outputs[0], out.inputs[0])
        if slot == 'M_Light':
            tex = _node(t, 'ShaderNodeTexImage', image=load(TEX / 'T_KitLight_Emissive.png', False))
            L(uv.outputs[0], tex.inputs[0])
            tint = _node(t, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
            tint.inputs['Factor'].default_value = 1
            L(tex.outputs[0], tint.inputs['A'])
            tint.inputs['B'].default_value = (.92, .96, 1, 1)
            L(tint.outputs['Result'], em.inputs[0])
            em.inputs[1].default_value = 2.4
        else:
            tex = _node(t, 'ShaderNodeTexImage', image=load(TEX / 'T_KitScreen_Emissive.png', False) if slot == 'M_Screen' else load(SKY, False))
            L(uv.outputs[0], tex.inputs[0])
            L(tex.outputs[0], em.inputs[0])
            em.inputs[1].default_value = 2.2 if slot == 'M_Screen' else 1.1
        return mat
    if slot == 'M_Decal':
        bs = _node(t, 'ShaderNodeBsdfPrincipled')
        tex = _node(t, 'ShaderNodeTexImage', image=load(TEX / 'T_KitDecal_BaseColor.png', False))
        L(uv.outputs[0], tex.inputs[0])
        L(tex.outputs[0], bs.inputs['Base Color'])
        bs.inputs['Roughness'].default_value = .55
        clear = _node(t, 'ShaderNodeBsdfTransparent')
        mix = _node(t, 'ShaderNodeMixShader')
        L(tex.outputs[1], mix.inputs[0])
        L(clear.outputs[0], mix.inputs[1])
        L(bs.outputs[0], mix.inputs[2])
        L(mix.outputs[0], out.inputs[0])
        return mat
    if slot == 'M_Glass':
        bs = _node(t, 'ShaderNodeBsdfPrincipled')
        bs.inputs['Base Color'].default_value = (.7, .8, .85, 1)
        bs.inputs['Roughness'].default_value = .05
        bs.inputs['Alpha'].default_value = .035
        L(bs.outputs[0], out.inputs[0])
        return mat
    bs = _node(t, 'ShaderNodeBsdfPrincipled')
    L(bs.outputs[0], out.inputs[0])
    base, rough, metal = BASES[slot]
    base_socket, rough_socket, metal_socket = None, None, None
    stem = SETS.get(slot)
    folder = TEX if stem and stem.startswith('T_Kit') else MATERIALS
    colour = load(folder / (stem + '_BaseColor.png'), False) if stem else None
    # UV0 is in tiling coordinates already, so the parallel sets map 1:1.
    if colour:
        c = _node(t, 'ShaderNodeTexImage', image=colour)
        L(uv.outputs[0], c.inputs[0])
        base_socket = c.outputs[0]
        if slot in ('M_Wall', 'M_Ceiling'):
            # Paint scheme from vertex colour B: the same three-way pick the master material needs.
            vc = _node(t, 'ShaderNodeVertexColor', layer_name='Col')
            vs = _node(t, 'ShaderNodeSeparateColor')
            L(vc.outputs[0], vs.inputs[0])
            is_grey = _node(t, 'ShaderNodeMath', operation='GREATER_THAN')
            L(vs.outputs[2], is_grey.inputs[0])
            is_grey.inputs[1].default_value = .9
            is_cargo = _node(t, 'ShaderNodeMath', operation='LESS_THAN')
            L(vs.outputs[2], is_cargo.inputs[0])
            is_cargo.inputs[1].default_value = .1
            pick = _node(t, 'ShaderNodeMix', data_type='RGBA')
            L(is_cargo.outputs[0], pick.inputs['Factor'])
            pick.inputs['A'].default_value = (*PAINT[BONE], 1)
            pick.inputs['B'].default_value = (*PAINT[CARGO], 1)
            pick2 = _node(t, 'ShaderNodeMix', data_type='RGBA')
            L(is_grey.outputs[0], pick2.inputs['Factor'])
            L(pick.outputs['Result'], pick2.inputs['A'])
            pick2.inputs['B'].default_value = (*PAINT[GREY], 1)
            tinted = _node(t, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
            tinted.inputs['Factor'].default_value = 1
            L(c.outputs[0], tinted.inputs['A'])
            L(pick2.outputs['Result'], tinted.inputs['B'])
            base_socket = tinted.outputs['Result']
        orm = load(folder / (stem + '_ORM.png'))
        if orm:
            o = _node(t, 'ShaderNodeTexImage', image=orm)
            L(uv.outputs[0], o.inputs[0])
            sp = _node(t, 'ShaderNodeSeparateColor')
            L(o.outputs[0], sp.inputs[0])
            rough_socket, metal_socket = sp.outputs[1], sp.outputs[2]
        nor = load(folder / (stem + '_Normal.png'))
        if nor:
            n = _node(t, 'ShaderNodeTexImage', image=nor)
            L(uv.outputs[0], n.inputs[0])
            sp = _node(t, 'ShaderNodeSeparateColor')
            L(n.outputs[0], sp.inputs[0])
            flip = _node(t, 'ShaderNodeMath', operation='SUBTRACT')
            flip.inputs[0].default_value = 1
            L(sp.outputs[1], flip.inputs[1])
            comb = _node(t, 'ShaderNodeCombineColor')
            L(sp.outputs[0], comb.inputs[0])
            L(flip.outputs[0], comb.inputs[1])
            L(sp.outputs[2], comb.inputs[2])
            nm = _node(t, 'ShaderNodeNormalMap', uv_map='UVMap')
            L(comb.outputs[0], nm.inputs['Color'])
            L(nm.outputs[0], bs.inputs['Normal'])
    elif slot == 'M_Hazard':
        # Stand-in stripes until T_Hazard exists.
        sep = _node(t, 'ShaderNodeSeparateXYZ')
        L(uv.outputs[0], sep.inputs[0])
        add = _node(t, 'ShaderNodeMath', operation='ADD')
        L(sep.outputs[0], add.inputs[0])
        L(sep.outputs[1], add.inputs[1])
        mul = _node(t, 'ShaderNodeMath', operation='MULTIPLY')
        L(add.outputs[0], mul.inputs[0])
        mul.inputs[1].default_value = 7
        fr = _node(t, 'ShaderNodeMath', operation='FRACT')
        L(mul.outputs[0], fr.inputs[0])
        gt = _node(t, 'ShaderNodeMath', operation='GREATER_THAN')
        L(fr.outputs[0], gt.inputs[0])
        gt.inputs[1].default_value = .5
        mix = _node(t, 'ShaderNodeMix', data_type='RGBA')
        L(gt.outputs[0], mix.inputs['Factor'])
        mix.inputs['A'].default_value = (.03, .03, .03, 1)
        mix.inputs['B'].default_value = (*base, 1)
        base_socket = mix.outputs['Result']
    if base_socket is None:
        # Stand-in tiling until the T_ sets exist: mottled paint with a fine dimple.
        vs = _node(t, 'ShaderNodeVertexColor', layer_name='Col')
        sp = _node(t, 'ShaderNodeSeparateColor')
        L(vs.outputs[0], sp.inputs[0])
        mr = _node(t, 'ShaderNodeMapRange')
        L(sp.outputs[1], mr.inputs['Value'])
        mr.inputs['To Min'].default_value = .84
        mr.inputs['To Max'].default_value = 1.08
        vm = _node(t, 'ShaderNodeVectorMath', operation='SCALE')
        vm.inputs[0].default_value = base
        L(mr.outputs[0], vm.inputs['Scale'])
        base_socket = vm.outputs[0]
        ntex = _node(t, 'ShaderNodeTexNoise')
        ntex.inputs['Scale'].default_value = 60
        ntex.inputs['Detail'].default_value = 8
        L(uv.outputs[0], ntex.inputs['Vector'])
        bump = _node(t, 'ShaderNodeBump')
        bump.inputs['Strength'].default_value = .08
        bump.inputs['Distance'].default_value = .4
        L(ntex.outputs[0], bump.inputs['Height'])
        L(bump.outputs[0], bs.inputs['Normal'])
    if rough_socket is None:
        v = _node(t, 'ShaderNodeValue')
        v.outputs[0].default_value = rough
        rough_socket = v.outputs[0]
    if metal_socket is None:
        v = _node(t, 'ShaderNodeValue')
        v.outputs[0].default_value = metal
        metal_socket = v.outputs[0]
    # This chain is the master material in the report: AO, then grime, then worn edge.
    if mask is not None:
        mu = _node(t, 'ShaderNodeUVMap', uv_map='UVMask')
        mt = _node(t, 'ShaderNodeTexImage', image=mask)
        mt.extension = 'EXTEND'
        L(mu.outputs[0], mt.inputs[0])
        ms = _node(t, 'ShaderNodeSeparateColor')
        L(mt.outputs[0], ms.inputs[0])
        grime = _node(t, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
        L(ms.outputs[2], grime.inputs['Factor'])
        L(base_socket, grime.inputs['A'])
        grime.inputs['B'].default_value = (.33, .33, .35, 1)
        worn = _node(t, 'ShaderNodeMix', data_type='RGBA')
        L(ms.outputs[1], worn.inputs['Factor'])
        L(grime.outputs['Result'], worn.inputs['A'])
        worn.inputs['B'].default_value = (.42, .44, .47, 1)
        occ = _node(t, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
        occ.inputs['Factor'].default_value = 1
        L(worn.outputs['Result'], occ.inputs['A'])
        L(ms.outputs[0], occ.inputs['B'])
        L(occ.outputs['Result'], bs.inputs['Base Color'])
        rg = _node(t, 'ShaderNodeMix', data_type='FLOAT')
        L(ms.outputs[2], rg.inputs['Factor'])
        L(rough_socket, rg.inputs['A'])
        rg.inputs['B'].default_value = .86
        rw = _node(t, 'ShaderNodeMix', data_type='FLOAT')
        L(ms.outputs[1], rw.inputs['Factor'])
        L(rg.outputs[0], rw.inputs['A'])
        rw.inputs['B'].default_value = .3
        L(rw.outputs[0], bs.inputs['Roughness'])
        mw = _node(t, 'ShaderNodeMix', data_type='FLOAT')
        L(ms.outputs[1], mw.inputs['Factor'])
        L(metal_socket, mw.inputs['A'])
        mw.inputs['B'].default_value = 1
        L(mw.outputs[0], bs.inputs['Metallic'])
    else:
        L(base_socket, bs.inputs['Base Color'])
        L(rough_socket, bs.inputs['Roughness'])
        L(metal_socket, bs.inputs['Metallic'])
    return mat


# ------------------------------------------------------------------------------------- render stage

def area(name, loc, target, power, size, colour):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy, light.size, light.color = power, size, colour
    ob = bpy.data.objects.new(name, light)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(ob)
    return ob


def setup_render(cell, samples):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5
    scene.render.resolution_x, scene.render.resolution_y = cell, cell * 3 // 4
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.022, .026, .034, 1)
    scene.world = world


def render_cell(ob, cell_path):
    scene = bpy.context.scene
    corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector([min(c[i] for c in corners) for i in range(3)])
    hi = Vector([max(c[i] for c in corners) for i in range(3)])
    centre, size = (lo + hi) / 2, (hi - lo)
    radius = size.length / 2
    # Three-quarter view from the room side, slightly above eye level.
    view = Vector((.62, -1, .34)).normalized()
    if ob.name == 'SM_Kit_CeilingTruss':
        view = Vector((.5, -1, -.56)).normalized()
    cam = bpy.data.cameras.new('c')
    cam.lens = 70
    cam.clip_end = 100000
    cam.clip_start = 1
    co = bpy.data.objects.new('c', cam)
    co.location = centre + view * radius * 5.0
    co.rotation_euler = (-view).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(co)
    scene.camera = co
    gz = lo.z
    me = bpy.data.meshes.new('g')
    span = radius * 12
    me.from_pydata([(centre.x - span, centre.y - span, gz), (centre.x + span, centre.y - span, gz), (centre.x + span, centre.y + span, gz), (centre.x - span, centre.y + span, gz)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new('g', me)
    gm = bpy.data.materials.new('gm')
    gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.03, .033, .04, 1)
    gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .4
    me.materials.append(gm)
    scene.collection.objects.link(g)
    if ob.name == 'SM_Kit_CeilingTruss':
        g.location.z = hi.z - lo.z
    r = radius
    power = r * r * 180
    up = -1 if ob.name == 'SM_Kit_CeilingTruss' else 1
    lights = [area('key', centre + Vector((1.5, -2.2, 1.9 * up)) * r, centre, power * .8, r * 1.2, (1, .95, .88)),
              area('fill', centre + Vector((-2.4, -1.5, .4 * up)) * r, centre, power * .24, r * 2.0, (.72, .84, 1)),
              area('rim', centre + Vector((-.8, 2.4, 1.8)) * r, centre, power * 1.3, r * 1.0, (.8, .9, 1))]
    scene.render.filepath = str(cell_path)
    bpy.ops.render.render(write_still=True)
    for x in lights + [co, g]:
        bpy.data.objects.remove(x)


def contact(paths, target, columns=4):
    imgs = []
    for p in paths:
        im = bpy.data.images.load(str(p))
        w, h = im.size
        a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
        imgs.append(a)
        bpy.data.images.remove(im)
    h, w, _ = imgs[0].shape
    rows = math.ceil(len(imgs) / columns)
    sheet = np.zeros((rows * h, columns * w, 3))
    for i, a in enumerate(imgs):
        sheet[(i // columns) * h:(i // columns + 1) * h, (i % columns) * w:(i % columns + 1) * w] = a
    write_png(target, sheet, 8)


# Review cameras inside the assembled room: location, target, lens. Coordinates are room_render's.
SHOTS = {
    'breach': ((430, 40, 170), (74, 200, 235), 35),
    'breachwide': ((760, 150, 200), (74, 200, 225), 40),
    'wall': ((1150, 180, 150), (1526, 330, 190), 35),
    'door': ((800, 120, 150), (800, 600, 190), 35),
    'console': ((1180, 330, 170), (1326, 560, 95), 40),
    'crates': ((640, -240, 140), (340, -380, 70), 40),
    'rack': ((1200, -300, 140), (1490, -200, 120), 35),
    'ceiling': ((800, 0, 120), (900, 200, 440), 24),
    'column': ((460, 60, 140), (640, 240, 200), 35),
    'viewport': ((400, 300, 160), (74, 480, 240), 35),
    'game': ((800, -420, 230), (800, 300, 90), 28),
}


def room_render(objects, samples, shots=None):
    """Assemble the kit into a Breach-Deck-sized room: the real test of whether modules work together."""
    scene = bpy.context.scene
    src = dict(objects)
    placed = []

    def put(name, x, y, z=0, yaw=0):
        ob = bpy.data.objects.new(name + '_r', src[name].data)
        ob.location = (x, y, z)
        ob.rotation_euler = (0, 0, math.radians(yaw))
        scene.collection.objects.link(ob)
        placed.append(ob)
    x0, x1, y0, y1, h = 74, 1526, -600, 600, 450
    for i in range(3):
        put('HullBreach' if i == 1 else 'WallPanel', x0, y0 + i * 400, 0, 90)
        put('WallPanel', x1, y1 - i * 400, 0, -90)
        put('FloorTrim', x1 - 36, y1 - i * 400, 0, -90)
        if i != 1:
            put('FloorTrim', x0 + 36, y0 + i * 400, 0, 90)
    put('WallPanel', 74, y1)
    put('WallPanel', 1126, y1)
    put('DoorFrame', 800, y1 + 20)
    put('BlastDoor', 800, y1 + 20)
    for i in range(4):
        for j in range(3):
            put('CeilingTruss', x0 + i * 400, y0 + 200 + j * 400, h)
    put('PipeRun', 74, y1 - 36, 356)
    put('PowerConduit', x1 - 36, y1, 350, -90)
    put('Console', 1326, y1 - 96)
    put('Terminal', 1120, y1 - 80, 0, 10)
    put('Column', 640, 240)
    put('CrateLarge', 340, -340, 0, 12)
    put('CrateSmall', 340, -340, 142, 40)
    put('CrateSmall', 520, -480, 0, -18)
    put('FloorVent', 1000, 120, 0, 90)
    put('WeaponRack', x1 - 36, y0 + 200, 0, -90)
    put('Viewport', x0 + 37, y1 - 400, 110, 90)
    def shell(name, a, b, mat):
        bpy.ops.mesh.primitive_cube_add(location=[(p + q) / 2 for p, q in zip(a, b)])
        ob = bpy.context.object
        ob.scale = [(q - p) / 2 for p, q in zip(a, b)]
        ob.data.materials.append(mat)
        return ob
    dark = bpy.data.materials.new('dark')
    dark.use_nodes = True
    dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.02, .022, .026, 1)
    deck = preview_material('M_Deck', None, 'room')
    for a, b in (((x0 - 60, y0 - 60, h), (x1 + 60, y1 + 60, h + 40)), ((x0 - 60, y0, 0), (x0, y1, h)), ((x1, y0, 0), (x1 + 60, y1, h)),
                 ((x0, y1, 0), (590, y1 + 40, h)), ((1010, y1, 0), (x1, y1 + 40, h)), ((590, y1, 340), (1010, y1 + 40, h)), ((x0, y0 - 40, 0), (x1, y0, h))):
        shell('wall', a, b, dark)
    me = bpy.data.meshes.new('floor')
    me.from_pydata([(x0 - 60, y0, 0), (x1 + 60, y0, 0), (x1 + 60, y1 + 200, 0), (x0 - 60, y1 + 200, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    tile = TILE['M_Deck']
    uv.data.foreach_set('uv', np.array([(0, 0), (1600 / tile, 0), (1600 / tile, 1400 / tile), (0, 1400 / tile)], np.float32).ravel())
    me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    me.materials.append(deck)
    floor = bpy.data.objects.new('floor', me)
    scene.collection.objects.link(floor)
    world = scene.world
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.002, .002, .003, 1)
    cam = bpy.data.cameras.new('room')
    cam.lens = 24
    cam.clip_end = 100000
    co = bpy.data.objects.new('room', cam)
    co.location = (1330, -560, 160)
    target = Vector((330, 330, 185))
    co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(co)
    scene.camera = co
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.cycles.samples = samples
    scene.cycles.max_bounces = 7
    if shots:
        scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    for name, loc, power, colour in (('a', (500, 0, 400), 1.6e6, (.94, .96, 1)), ('b', (1100, 0, 400), 1.6e6, (.94, .96, 1))):
        area(name, loc, (loc[0], loc[1], 0), power, 500, colour)
    area('c', (800, 560, 330), (800, 0, 0), 2.0e5, 200, (1, .55, .2))
    area('d', (800, 0, 40), (800, 0, 450), 4.0e5, 900, (.85, .92, 1))
    if shots:
        for tag in shots:
            loc, aim_at, lens = SHOTS[tag]
            co.location = loc
            cam.lens = lens
            co.rotation_euler = (Vector(aim_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(REVIEW / 'Kit' / ('shot_' + tag + '.png'))
            bpy.ops.render.render(write_still=True)
        return
    scene.render.filepath = str(REVIEW / 'kit_room.png')
    bpy.ops.render.render(write_still=True)


def export(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=str(OUT / (ob.name + '.fbx')), use_selection=True, axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, mesh_smooth_type='FACE', add_leaf_bones=False, object_types={'MESH'},
                             use_mesh_modifiers=True, colors_type='LINEAR', use_tspace=False, apply_scale_options='FBX_SCALE_NONE')


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', default='')
    parser.add_argument('--no-bake', action='store_true')
    parser.add_argument('--no-render', action='store_true')
    parser.add_argument('--no-export', action='store_true')
    parser.add_argument('--no-textures', action='store_true')
    parser.add_argument('--samples', type=int, default=48)
    parser.add_argument('--bake-samples', type=int, default=48)
    parser.add_argument('--cell', type=int, default=900)
    parser.add_argument('--suffix', default='')
    parser.add_argument('--room', action='store_true')
    parser.add_argument('--no-cells', action='store_true')
    parser.add_argument('--shots', default='', help='comma list of SHOTS tags, or all; rendered to Art/Review/Kit/shot_*.png')
    parser.add_argument('--room-samples', type=int, default=96)
    args = parser.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'CPU'
    for path in (OUT, TEX, REVIEW, REVIEW / 'Kit'):
        path.mkdir(parents=True, exist_ok=True)
    if not args.no_textures:
        paint_textures()
        foam_textures()
        screen_textures()
        decal_textures()
    names = args.only.split(',') if args.only else list(BUILD)
    objects = []
    for name in names:
        start = time.time()
        kit = BUILD[name]()
        ob = kit.finish()
        ob.hide_render = True
        mask = None
        if not args.no_bake:
            bake_mask(ob, args.bake_samples)
        mask = load(TEX / ('T_KitMask_' + ob.name[len('SM_Kit_'):] + '.png'))
        if not args.no_export:
            export(ob)
        tris = len(ob.data.polygons)
        d = ob.dimensions
        slots = [m.name for m in ob.data.materials]
        print(f'KIT {ob.name} tris={tris} size=({d.x:.0f},{d.y:.0f},{d.z:.0f}) slots={slots} t={time.time() - start:.0f}s', flush=True)
        # Assign in place: clearing the slot list would reset every face's material index.
        for i, slot in enumerate(slots):
            ob.data.materials[i] = preview_material(slot, mask, ob.name)
        objects.append((name, ob))
    if not args.no_render:
        setup_render(args.cell, args.samples)
    if not args.no_render and not args.no_cells:
        paths = []
        for name, ob in objects:
            if name in PREVIEW_SKIP:
                continue
            ob.hide_render = False
            path = REVIEW / 'Kit' / (name + '.png')
            render_cell(ob, path)
            ob.hide_render = True
            paths.append(path)
        every = [REVIEW / 'Kit' / (n + '.png') for n in BUILD if n not in PREVIEW_SKIP]
        contact([p for p in every if p.exists()], REVIEW / ('kit' + args.suffix + '.png'), 4)
    if args.room:
        for _, ob in objects:
            ob.hide_render = True
        room_render(objects, args.room_samples, (list(SHOTS) if args.shots == 'all' else args.shots.split(',')) if args.shots else None)
    print('PHYSIS_KIT_DONE', flush=True)


main()
