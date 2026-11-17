"""Arche's Reweave targets cut into stone blocks (SM_AW_*), so a thing can hang sundered and fly back together.

Each mesh a BP_Weave can show (WOVEN below) is built by its own generator, then cut here: its faces are divided
until none is longer than a block, every face is given to the nearest of a jittered grid of block centres, and no
vertex is shared between blocks. Each vertex then carries its block in three extra UV sets, which the weave
materials (arche:weave_materials, M_AR_*Weave) read to move a whole block at once:

  UV1 = (pivot x, pivot y)   the block's middle, cm, mesh space
  UV2 = (pivot z, seed)      seed 0..1, one per block: its direction, spin and timing
  UV3 = (order, 0)           0..1 along the mesh's longest side: the order in which the blocks come home

The shape, the colours and the shading are the uncut mesh's (its smooth normals are kept as custom normals), so
rewoven it looks exactly as SM_AN_<Name> does. Blocks are open shells; the weave materials are two-sided.

Run:
  /usr/bin/blender -b --factory-startup --python-exit-code 1 --python Tools/build_physis_arche_weave.py -- [names]
  python3 Tools/build_physis_arche_weave.py --dry      (numpy only: counts, nothing written)
then `arche:import:SM_AW_` in the editor. Writes Art/Meshes/Arche/SM_AW_<Name>.fbx.
"""
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MESH_DIR = ROOT / 'Tools/arche_meshes'
OUT = ROOT / 'Art/Meshes/Arche'
sys.path.insert(0, str(MESH_DIR))
import kit  # noqa: E402,F401
import toolkit  # noqa: E402

try:
    import bpy
except ImportError:
    bpy = None

WOVEN = ('SM_AN_Span', 'SM_AN_Stair', 'SM_AN_Causeway', 'SM_AN_Bulwark', 'SM_AN_Mirror', 'SM_AN_Obelisk')
BLOCKS = 110          # about this many blocks in a mesh
BLOCK_MIN, BLOCK_MAX = .35, 2.2   # a block's size in metres


def corners(part):
    """The Part as loose triangles: positions, colours and normals per corner, and each triangle's slot."""
    v, c = np.asarray(part.v, np.float64), np.asarray(part.c, np.float64)
    tris, slots, smooth = [], [], []
    for face, slot, soft in zip(part.f, part.m, part.s):
        for k in range(1, len(face) - 1):
            tris.append((face[0], face[k], face[k + 1]))
            slots.append(slot)
            smooth.append(soft)
    tris, slots, smooth = np.asarray(tris), np.asarray(slots), np.asarray(smooth)
    p = v[tris]
    flat = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])   # area-weighted face normals
    soft = np.zeros_like(v)
    for k in range(3):
        np.add.at(soft, tris[smooth, k], flat[smooth])
    length = np.linalg.norm(flat, axis=1, keepdims=True)
    unit = flat / np.maximum(length, 1e-12)
    n = np.repeat(unit[:, None, :], 3, 1)
    vertex = soft[tris]
    vertex /= np.maximum(np.linalg.norm(vertex, axis=2, keepdims=True), 1e-12)
    n[smooth] = vertex[smooth]
    return p, c[tris], n, slots


def divide(p, c, n, slots, limit):
    """Halves every triangle's longest edge until none is longer than `limit`."""
    for _ in range(14):
        edges = np.linalg.norm(p - np.roll(p, -1, 1), axis=2)   # edge k runs from corner k to k + 1
        longest = edges.argmax(1)
        split = edges.max(1) > limit
        if not split.any():
            break
        i = np.nonzero(split)[0]
        a, b, o = longest[i], (longest[i] + 1) % 3, (longest[i] + 2) % 3
        row = np.arange(len(i))

        def halves(x):
            xa, xb, xo = x[i][row, a], x[i][row, b], x[i][row, o]
            mid = (xa + xb) / 2
            return np.stack([xa, mid, xo], 1), np.stack([mid, xb, xo], 1)
        p1, p2 = halves(p)
        c1, c2 = halves(c)
        n1, n2 = halves(n)
        keep = ~split
        p, c, n = (np.concatenate([x[keep], x1, x2]) for x, x1, x2 in ((p, p1, p2), (c, c1, c2), (n, n1, n2)))
        slots = np.concatenate([slots[keep], slots[i], slots[i]])
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-12)
    return p, c, n, slots


def shatter(part, seed=7):
    """(positions, colours, normals, slots per triangle, block per triangle, pivots, seeds, order): the Part as
    loose triangles grouped into blocks."""
    rng = np.random.default_rng(seed + sum(map(ord, part.name)))
    p, c, n, slots = corners(part)
    lo, hi = p.reshape(-1, 3).min(0), p.reshape(-1, 3).max(0)
    size = np.maximum(hi - lo, .05)
    block = float(np.clip((size.prod() / BLOCKS) ** (1 / 3), BLOCK_MIN, BLOCK_MAX))
    p, c, n, slots = divide(p, c, n, slots, block * .7)
    counts = np.maximum(np.round(size / block).astype(int), 1)
    axes = [lo[k] + (np.arange(counts[k]) + .5) * size[k] / counts[k] for k in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3)
    grid += rng.uniform(-.38, .38, grid.shape) * (size / counts)
    centre = p.mean(1)
    owner = np.empty(len(centre), np.int64)
    for start in range(0, len(centre), 4096):
        d = ((centre[start:start + 4096, None, :] - grid[None]) ** 2).sum(2)
        owner[start:start + 4096] = d.argmin(1)
    used, owner = np.unique(owner, return_inverse=True)
    pivots = np.zeros((len(used), 3))
    np.add.at(pivots, owner, centre)
    pivots /= np.bincount(owner)[:, None]
    seeds = rng.uniform(.02, .98, len(used))
    axis = int(size.argmax())
    order = (pivots[:, axis] - lo[axis]) / size[axis]
    return p, c, n, slots, owner, pivots, seeds, order


def build(part):
    """Blender: the cut mesh as an object named SM_AW_<Name>."""
    p, c, n, slots, owner, pivots, seeds, order = shatter(part)
    count = len(p)
    name = 'SM_AW_' + part.name[6:]
    # One vertex per corner, then welded where position, normal, colour and block all agree.
    rows = np.concatenate([p.reshape(-1, 3), n.reshape(-1, 3), c.reshape(-1, 4), np.repeat(owner, 3)[:, None].astype(np.float64)], 1)
    _, first, inverse = np.unique(np.round(rows, 5), axis=0, return_index=True, return_inverse=True)
    inverse = inverse.reshape(-1)
    v, vn, vc, vb = rows[first, :3], rows[first, 3:6], rows[first, 6:10], rows[first, 10].astype(np.int64)
    faces = inverse.reshape(count, 3)
    mesh = bpy.data.meshes.new(name)
    flipped = v.copy()
    flipped[:, 1] *= -1   # Unreal y -> Blender -y, as toolkit.Part.build does; the mirror reverses the winding
    mesh.from_pydata(flipped.tolist(), [], faces[:, ::-1].tolist())
    mesh.update()
    for slot in part.slots:
        mesh.materials.append(bpy.data.materials.get(slot) or bpy.data.materials.new(slot))
    mesh.polygons.foreach_set('material_index', slots.astype(np.int32))
    mesh.polygons.foreach_set('use_smooth', np.ones(count, bool))
    colour = mesh.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    colour.data.foreach_set('color', np.clip(vc, 0, 1).ravel())
    loops = np.zeros(len(mesh.loops), np.int64)
    mesh.loops.foreach_get('vertex_index', loops)
    at, block = v[loops], vb[loops]
    cm = 100.0

    def layer(label, u, w):
        uv = mesh.uv_layers.new(name=label)
        uv.data.foreach_set('uv', np.stack([u, 1.0 - w], 1).ravel())   # the FBX import flips v back
    layer('UV', (at[:, 0] + at[:, 2] * .5) / 4, 1.0 - (at[:, 1] + at[:, 2] * .5) / 4)   # the uncut mesh's projected UVs
    layer('Pivot', pivots[block, 0] * cm, pivots[block, 1] * cm)
    layer('Height', pivots[block, 2] * cm, seeds[block])
    layer('Order', order[block], np.zeros(len(block)))
    normals = vn.copy()
    normals[:, 1] *= -1
    if hasattr(mesh, 'use_auto_smooth'):
        mesh.use_auto_smooth = True
    mesh.normals_split_custom_set_from_vertices(normals.tolist())
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob, len(pivots), count


def parts(words):
    import importlib
    for module_name in ('structures', 'figures'):
        module = importlib.import_module(module_name)
        variants = getattr(module, 'VARIANTS', {})
        for builder in module.MESHES:
            if variants.get(builder, 0):
                continue
            part = builder()
            if part.name in WOVEN and (not words or any(w in part.name.lower() for w in words)):
                yield part


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ([] if bpy is not None else sys.argv[1:])
    dry = '--dry' in argv or bpy is None
    words = [a.lower() for a in argv if not a.startswith('--')]
    seen = []
    for part in parts(words):
        start = time.time()
        if dry:
            p, c, n, slots, owner, pivots, seeds, order = shatter(part)
            blocks, tris = len(pivots), len(p)
        else:
            for collection in (bpy.data.objects, bpy.data.meshes):
                for item in list(collection):
                    collection.remove(item)
            ob, blocks, tris = build(part)
            toolkit.export(ob, OUT)
        seen.append(part.name)
        print('weave %-16s %4d blocks %7d tris (uncut %d)  %.1f s' % ('SM_AW_' + part.name[6:], blocks, tris, part.triangles(), time.time() - start), flush=True)
    missing = [name for name in WOVEN if name not in seen and not words]
    if missing:
        print('FAILED: no generator made', missing)
        sys.exit(1)
    print('dry check passed' if dry else 'written to %s' % OUT)


if __name__ == '__main__':
    main()
