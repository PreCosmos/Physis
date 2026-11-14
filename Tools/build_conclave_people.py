"""Run in Blender (headless): a Conclave MetaHuman's costume, skinned to metahuman_base_skel, and the cloth mask that hides
the skin under it (Tools/conclave/PEOPLE_DESIGN.md 3.3: Phase 0 step 6 wrote it, Phase 1 step 5 runs it).

  flatpak-spawn --host flatpak run org.blender.Blender -b --factory-startup --python-exit-code 1 \\
      --python /home/precosmos/PhysisProject/Tools/build_conclave_people.py -- Listener [Teodor ...]

(--python-exit-code 1 makes a failure to import the costume modules exit non-zero too; main() covers the rest.)

For each MH key (physis_conclave_cast.MH; a pending entry is refused, as the editor's operations refuse it) it reads the
guides conclave:people_guides wrote with the editor closed, FILES['body_guide'] and FILES['face_guide'], and writes
FILES['costume_fbx'], FILES['cloth_mask_png'] (white where skin shows), costume-build.json (the guide's measurements, the
pieces, the weights) and <Key>-costume.blend (to look at) beside them. Then, in a fresh editor, conclave:people_import.

The costume itself is Tools/conclave_meshes/costumes.py (numpy; its own test runs offline: python3
Tools/conclave_meshes/costumes.py --physis). This script only turns the guides into its arrays, its Part into a skinned
Blender mesh, and checks the result as check.py checks every Conclave mesh. As Tools/build_physis_outfit.py did for
Physis: the costume lives in the body guide's frame and on its armature; it takes the weights of the nearest body or face
surface (POLYINTERP_NEAREST) on the core deform bones that stay at every LOD; rigid pieces follow one bone; skirts hang
from the pelvis and follow the thighs toward the hem; at most four influences, normalised; the FBX axes are the guide's.
"""
import json
import sys
import time
import traceback
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tools/conclave_meshes'))
sys.path.insert(0, str(ROOT / 'Content/Python'))

import costumes  # noqa: E402
from check import check_part  # noqa: E402  (the offline validator's rules, so the build refuses what check.py would)
from physis_conclave_cast import FILES, MH  # noqa: E402

BODY_LOD, FACE_LOD = 1, 0   # Physis's outfit was fitted to the body's LOD1; the face's LOD0 holds the neck and bib whole
MASK_SIZE = 2048            # the cloth mask's pixels (people_import caps it to TEXTURE_CAPS['body'] in the editor)
MASK_EDGE = 3               # px the hidden areas shrink by, so filtering never darkens skin that shows
CLEARANCE = .002            # m: a cloth vertex found inside the body moves out to this far off it (a safety net: the
                            # builders fit over the guide; a top's armhole edge can dip into the shoulder under its
                            # sleeve; the report counts how many it caught)
INFLUENCES = 4              # bones per vertex (Physis's outfit; the skinned mesh's LODs keep them)
HANG = (.75, .06)           # a skirt's thigh share at the hem (Physis's outfit) and the |y| (m) by which it is full
HEAD_HEIGHT = (1.0, 2.4)    # m: where a MetaHuman's head bone can be (the toolset's 135-220 cm bodies)


def arguments():
    keys = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if not keys:
        raise SystemExit('usage: blender -b --python build_conclave_people.py -- <MH key> [...] (keys: %s)' % ', '.join(MH))
    for key in keys:
        if key not in MH:
            raise SystemExit('%s is not a key of physis_conclave_cast.MH (%s)' % (key, ', '.join(MH)))
        if MH[key]['pending']:
            raise SystemExit('%s is pending: %s' % (key, MH[key]['pending']))
    return keys


def project_file(pattern, key):
    return ROOT / pattern.format(key=key)


def imported(path):
    """Imports an FBX into the scene; returns the objects it added."""
    if not path.exists():
        raise SystemExit('%s is missing: run conclave:people_guides first (then quit the editor)' % path.relative_to(ROOT))
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    return [o for o in bpy.context.scene.objects if o not in before]


def lod_mesh(objects, lod, what):
    meshes = [o for o in objects if o.type == 'MESH']
    found = [o for o in meshes if o.name.endswith('_LOD%d' % lod)]
    if not found:
        raise SystemExit('the %s guide has no _LOD%d mesh (it has %s)' % (what, lod, ', '.join(o.name for o in meshes)))
    return found[0]


def core_of(armature):
    """For each bone of an armature, the core deform bone (costumes.CORE) whose weight it counts for."""
    out = {}
    for bone in armature.data.bones:
        b = bone
        while b is not None and b.name not in costumes.CORE:
            b = b.parent
        out[bone.name] = b.name if b is not None else 'root'
    return out


def surface(obj, armature):
    """A guide mesh as costumes.measure() takes it: points (m, costumes' frame), triangles wound for that frame, each
    vertex's core bone, its UV, and its per-core-bone weights (for the weight source). Both guides' meshes are in the
    MetaHuman's mesh space (cm), so their own coordinates are kept as 'local'."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    co = np.zeros(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get('co', co)
    local = co.reshape(-1, 3)
    tris = np.zeros(len(mesh.loop_triangles) * 3, np.int64)
    mesh.loop_triangles.foreach_get('vertices', tris)
    core = core_of(armature)
    names = {g.index: core.get(g.name, 'head' if g.name.startswith('FACIAL') else 'root') for g in obj.vertex_groups}
    weights = np.zeros((len(mesh.vertices), len(costumes.CORE)))
    for v in mesh.vertices:
        for g in v.groups:
            weights[v.index, costumes.CORE.index(names[g.group])] += g.weight
    uv = None
    if mesh.uv_layers:
        loops = np.zeros(len(mesh.loops), np.int64)
        mesh.loops.foreach_get('vertex_index', loops)
        coords = np.zeros(len(mesh.loops) * 2)
        mesh.uv_layers[0].data.foreach_get('uv', coords)
        uv = np.zeros((len(mesh.vertices), 2))
        uv[loops[::-1]] = coords.reshape(-1, 2)[::-1]   # a vertex's first loop wins (the guides keep one UV a vertex)
    return {'points': costumes.from_fbx(local), 'tris': tris.reshape(-1, 3)[:, ::-1], 'labels': np.array(costumes.CORE)[weights.argmax(1)],
            'uv': uv, 'weights': weights, 'local': local}


def heads(armature, to_local, names=None):
    """Bone heads (costumes' frame) of an armature, in the body guide's local frame first."""
    m = to_local @ armature.matrix_world
    return {b.name: costumes.from_fbx(np.array(m @ b.head_local)) for b in armature.data.bones if names is None or b.name in names}


def check_frame(bones):
    """The guides' frame must be the one costumes.from_fbx assumes: centimetres, the left at -y, the toes ahead of the
    ankle (an importer that baked the unit scale or turned the axes would fit every piece to the wrong body)."""
    if not HEAD_HEIGHT[0] < bones['head'][2] < HEAD_HEIGHT[1]:
        raise SystemExit('the body guide\'s head bone is at %.3f m: its mesh is not in centimetres as exported' % bones['head'][2])
    if not (bones['thigh_l'][1] < 0 < bones['thigh_r'][1] and bones['ball_l'][0] > bones['foot_l'][0]):
        raise SystemExit('the body guide is not in the expected frame (z up, facing -y, its left at +x): thigh_l %s, ball_l %s'
                         % (np.round(bones['thigh_l'], 3).tolist(), np.round(bones['ball_l'], 3).tolist()))


def to_fbx(points):
    """costumes' frame (m) back to the guide's local frame (cm): the inverse of costumes.from_fbx."""
    p = np.asarray(points, np.float64)
    return np.stack([-p[..., 1], -p[..., 0], p[..., 2]], -1) * 100.


def costume_object(part, body):
    """The costume Part as a Blender mesh in the body guide's frame: its faces wound back for the mirrored frame, a
    material per slot named as the slot (people_import matches them), linear vertex colours, toolkit's projected UVs."""
    mesh = bpy.data.meshes.new(part.name)
    mesh.from_pydata(to_fbx(part.v).tolist(), [], [list(reversed(f)) for f in part.f])
    mesh.update()
    for slot in part.slots:
        mesh.materials.append(bpy.data.materials.get(slot) or bpy.data.materials.new(slot))
    mesh.polygons.foreach_set('material_index', part.m)
    mesh.polygons.foreach_set('use_smooth', part.s)
    colours = mesh.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    colours.data.foreach_set('color', np.clip(np.array(part.c), 0, 1).ravel())
    uv = mesh.uv_layers.new(name='UV')
    loops = np.zeros(len(mesh.loops), np.int64)
    mesh.loops.foreach_get('vertex_index', loops)
    v = np.array(part.v)[loops]
    uv.data.foreach_set('uv', (np.stack([v[:, 0] + v[:, 2] * .5, v[:, 1] + v[:, 2] * .5], 1) / 4).ravel())  # toolkit.Part.build's
    obj = bpy.data.objects.new(part.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = body.matrix_world.copy()
    return obj


def weight_source(name, parts, body):
    """The body and the face guides as one mesh whose vertex groups are the core bones: what the costume's weights are
    taken from (the face's for a hood or a collar over the neck)."""
    points = np.concatenate([p['local'] for p in parts])
    tris, base = [], 0
    for p in parts:
        tris.append(p['tris'][:, ::-1] + base)
        base += len(p['local'])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points.tolist(), [], np.concatenate(tris).tolist())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = body.matrix_world.copy()
    weights = np.concatenate([p['weights'] for p in parts])
    for j, bone in enumerate(costumes.CORE):
        group = obj.vertex_groups.new(name=bone)
        for i in np.nonzero(weights[:, j] > 1e-4)[0]:
            group.add([int(i)], float(weights[i, j]), 'REPLACE')
    return obj


def push_out(obj, held, tree):
    """Moves every cloth vertex found inside the body or the face out to CLEARANCE off it, but the held ones; returns
    how many it moved."""
    moved = 0
    cm = CLEARANCE * 100
    for v in obj.data.vertices:
        if held[v.index]:
            continue
        hit, normal, _, _ = tree.find_nearest(v.co)
        if hit is not None and (v.co - hit).dot(normal) < -.1:   # more than a millimetre in
            v.co = hit + normal * cm
            moved += 1
    return moved


def weigh(obj, source, cos, guide):
    """The costume's skin weights: the nearest guide surface's for 'body' pieces, then skirts hung from the pelvis and the
    thighs, rigid pieces on their one bone, at most INFLUENCES each, normalised."""
    for bone in costumes.CORE:
        obj.vertex_groups.new(name=bone)
    bpy.context.view_layer.objects.active = obj
    transfer = obj.modifiers.new('MetaHuman skin weights', 'DATA_TRANSFER')
    transfer.object = source
    transfer.use_vert_data = True
    transfer.data_types_verts = {'VGROUP_WEIGHTS'}
    transfer.vert_mapping = 'POLYINTERP_NEAREST'
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    points = np.asarray(cos.part.v, np.float64)
    lv = guide.levels
    groups = {g.name: g for g in obj.vertex_groups}
    for name, first, count, weighting, _ in cos.pieces:
        ids = list(range(first, first + count))
        if weighting == 'body':
            continue
        for i in ids:   # what the transfer gave this piece goes: it hangs or it is rigid
            for g in list(obj.data.vertices[i].groups):
                obj.vertex_groups[g.group].remove([i])
        if weighting == 'skirt':
            p = points[first:first + count]
            drop = np.clip((lv['waist'] - p[:, 2]) / (lv['waist'] - lv['knee']), 0, 1)
            leg = HANG[0] * drop * np.clip(np.abs(p[:, 1]) / (HANG[1] * guide.scale), 0, 1)
            for i, share, y in zip(ids, leg, p[:, 1]):
                groups['pelvis'].add([i], float(1 - share), 'REPLACE')
                if share > 0:
                    groups['thigh_l' if y < 0 else 'thigh_r'].add([i], float(share), 'REPLACE')
        else:
            groups[weighting].add(ids, 1.0, 'REPLACE')
    bpy.ops.object.vertex_group_limit_total(limit=INFLUENCES)
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
    unweighted = sum(1 for v in obj.data.vertices if not any(g.weight > 0 for g in v.groups))
    most = max((sum(1 for g in v.groups if g.weight > 0) for v in obj.data.vertices), default=0)
    # Drop the bones nothing uses, so the FBX carries only the weights there are.
    used = {obj.vertex_groups[g.group].name for v in obj.data.vertices for g in v.groups if g.weight > 0}
    for g in list(obj.vertex_groups):
        if g.name not in used:
            obj.vertex_groups.remove(g)
    return unweighted, most, sorted(used)


def mask(path, body, covered):
    """The cloth mask over the body's UVs: black where every corner of a body face is covered (the skin is not drawn),
    white elsewhere; the black shrunk by MASK_EDGE so filtering never eats into skin that shows. Saved through Blender
    as Tools/build_physis_outfit.py saved Physis's (T_Physis_Body_Mask), so its rows and V match the body's UVs."""
    n = MASK_SIZE
    cover = np.ones((n, n), np.float32)
    uv = body.data.uv_layers[0].data
    for poly in body.data.polygons:
        if not all(covered[i] for i in poly.vertices):
            continue
        corners = [tuple(uv[li].uv * n) for li in poly.loop_indices]
        for k in range(1, len(corners) - 1):
            (ax, ay), (bx, by), (cx, cy) = corners[0], corners[k], corners[k + 1]
            area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
            if abs(area) < 1e-9:
                continue
            x0, x1 = int(min(ax, bx, cx)), int(max(ax, bx, cx)) + 1
            y0, y1 = int(min(ay, by, cy)), int(max(ay, by, cy)) + 1
            xx, yy = np.mgrid[x0:x1 + 1, y0:y1 + 1]
            w0 = ((bx - xx) * (cy - yy) - (cx - xx) * (by - yy)) / area
            w1 = ((cx - xx) * (ay - yy) - (ax - xx) * (cy - yy)) / area
            inside = (w0 >= 0) & (w1 >= 0) & (w0 + w1 <= 1)
            cover[yy[inside] % n, xx[inside] % n] = 0   # the body's UVs sit in the second tile (u 1..2): wrap
    for _ in range(MASK_EDGE):
        cover = np.maximum.reduce([cover, np.roll(cover, 1, 0), np.roll(cover, -1, 0), np.roll(cover, 1, 1), np.roll(cover, -1, 1)])
    rgba = np.ones((n, n, 4), np.float32)
    rgba[..., :3] = cover[..., None]
    image = bpy.data.images.new(path.stem, width=n, height=n, alpha=False)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(path)
    image.file_format = 'PNG'
    image.save()
    return float(1 - cover.mean())


def build(key):
    start = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body_fbx, face_fbx = project_file(FILES['body_guide'], key), project_file(FILES['face_guide'], key)
    out_fbx, out_png = project_file(FILES['costume_fbx'], key), project_file(FILES['cloth_mask_png'], key)
    out_fbx.parent.mkdir(parents=True, exist_ok=True)
    added = imported(body_fbx)
    body = lod_mesh(added, BODY_LOD, 'body')
    arm = next((o for o in added if o.type == 'ARMATURE'), None)
    if arm is None:
        raise SystemExit('the body guide has no armature: export it as a skeletal mesh (people_guides)')
    for o in added:
        if o.type == 'MESH' and o is not body:
            bpy.data.objects.remove(o, do_unlink=True)
    to_local = body.matrix_world.inverted()
    face_added = imported(face_fbx)
    face = lod_mesh(face_added, FACE_LOD, 'face')
    face_arm = next((o for o in face_added if o.type == 'ARMATURE'), None)
    if face_arm is None:
        raise SystemExit('the face guide has no armature: export it as a skeletal mesh (people_guides)')
    face_local = face.matrix_world.inverted()
    # The face guide is in the body guide's frame (both are the MetaHuman's mesh space), as build_physis_outfit.py set it.
    body_data = surface(body, arm)
    face_data = surface(face, face_arm)
    bones = heads(arm, to_local, costumes.CORE)
    landmarks = {k: v for k, v in heads(face_arm, face_local).items() if k.startswith('FACIAL_')}
    check_frame(bones)
    guide = costumes.measure(body_data, face_data, bones, landmarks, source=str(body_fbx.relative_to(ROOT)))
    cos = costumes.costume(key, guide)
    problems = costumes.costume_problems(cos, guide)
    check_part(cos.part, costumes.CONTRACT, problems, True)
    if problems:
        raise SystemExit('%s: the costume is refused:\n  - %s' % (key, '\n  - '.join(problems)))
    for o in face_added:
        if o is not face:
            bpy.data.objects.remove(o, do_unlink=True)
    face.parent = None
    face.matrix_world = body.matrix_world.copy()
    obj = costume_object(cos.part, body)
    skin = np.concatenate([body_data['tris'][:, ::-1], face_data['tris'][:, ::-1] + len(body_data['local'])])  # the guides' own winding
    tree = BVHTree.FromPolygons([Vector(p) for p in np.concatenate([body_data['local'], face_data['local']])], [tuple(t) for t in skin])
    # Rigid pieces sit on their bone as built, and footwear's soles are meant to hold the feet's undersides.
    held = np.zeros(len(cos.part.v), bool)
    for _, first, count, weighting, kind in cos.pieces:
        if weighting not in ('body', 'skirt') or kind == 'footwear':
            held[first:first + count] = True
    pushed = push_out(obj, held, tree)
    source = weight_source(key + '_weights', (body_data, face_data), body)
    unweighted, most, used = weigh(obj, source, cos, guide)
    if unweighted:
        raise SystemExit('%s: %d costume vertices took no weight' % (key, unweighted))
    bpy.data.objects.remove(source, do_unlink=True)
    obj.parent = arm
    obj.matrix_world = body.matrix_world.copy()
    obj.modifiers.new('MetaHuman Skeleton', 'ARMATURE').object = arm
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(out_fbx), use_selection=True, object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
                             bake_anim=False, mesh_smooth_type='FACE', use_mesh_modifiers=True, axis_forward='-Y', axis_up='Z',
                             path_mode='STRIP', colors_type='LINEAR', use_tspace=False)
    hidden_share = mask(out_png, body, cos.covered)
    body.hide_set(True)
    face.hide_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_fbx.parent / ('%s-costume.blend' % key)))
    report = {'key': key, 'fbx': str(out_fbx.relative_to(ROOT)), 'mask': str(out_png.relative_to(ROOT)),
              'vertices': len(obj.data.vertices), 'triangles': cos.part.triangles(), 'material_slots': cos.part.slots,
              'pieces': [{'piece': n, 'first': f, 'vertices': c, 'weighting': w, 'kind': k} for n, f, c, w, k in cos.pieces],
              'bones': used, 'maximum_influences': most, 'pushed_out_of_the_body': pushed,
              'body_vertices_hidden': int(cos.covered.sum()), 'mask_hidden_share': round(hidden_share, 4),
              'guide': guide.record(), 'seconds': round(time.time() - start, 1)}
    (out_fbx.parent / 'costume-build.json').write_text(json.dumps(report, indent=1))
    print('CONCLAVE_COSTUME_BUILT', json.dumps({k: report[k] for k in ('key', 'vertices', 'triangles', 'maximum_influences',
                                                                         'pushed_out_of_the_body', 'mask_hidden_share', 'seconds')}),
          flush=True)


def main():
    for key in arguments():
        try:
            build(key)
        except Exception:
            # Blender exits 0 after an uncaught exception in a --python script (only SystemExit sets the status), so a
            # guide costumes.measure() refuses, a missing bone or a failed operator would otherwise read as a build that
            # finished, beside the outputs of an earlier run.
            traceback.print_exc()
            raise SystemExit('%s: the costume build failed (traceback above)' % key)


if __name__ == '__main__':
    main()
