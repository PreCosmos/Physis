"""Arche's animals as skinned meshes with their animations (Tools/arche_meshes/creatures.py carries each rig).

Every creature Part has a `rig`: bones, four skin weights per vertex, and animations given as pose(t) functions
(rotation vectors per bone, in mesh axes). This script builds the mesh as the static export does, an armature from
the bones, the vertex groups from the weights, and one action per animation sampled at 30 fps, and writes

  Art/Meshes/Arche/Rigged/SK_AE_<Name>.fbx            the mesh on its skeleton (no animation)
  Art/Meshes/Arche/Rigged/A_AE_<Name>_<Anim>.fbx      the skeleton alone with one animation

Run (after check.py creatures passes):
  /usr/bin/blender -b --factory-startup --python-exit-code 1 --python Tools/build_physis_arche_rigs.py -- [names]
then `arche:import_rigs` in the editor. The static SM_AE_* meshes stay as they are: the enemy keeps one for its
collision and bounds, and wears the skinned mesh.

Units: an armature exported in metres reaches Unreal with a root bone scaled by 100, which every animation then
undoes (the mesh shrinks to a hundredth), so this scene is built in centimetres with a unit scale of 0.01.

Axes: the generators work in Unreal metres (y right); toolkit.Part.build() mirrors y for Blender. A bone's head and
tail are mirrored the same way, and a rotation vector (an axial vector) becomes (-x, y, -z) under that mirror.
A pose rotation is given about the bone's head in the frame its posed parent carries, in mesh axes; as a pose-bone
basis that is B^T R B with B the bone's rest orientation in armature space.
"""
import importlib
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MESH_DIR = ROOT / 'Tools/arche_meshes'
OUT = ROOT / 'Art/Meshes/Arche/Rigged'
FPS = 30

sys.path.insert(0, str(MESH_DIR))
import kit  # noqa: E402,F401
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

FBX = dict(use_selection=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1.0, mesh_smooth_type='FACE', add_leaf_bones=False, colors_type='LINEAR',
           use_tspace=False, axis_forward='-Z', axis_up='Y', primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False)


def check_rig(part):
    rig = getattr(part, 'rig', None)
    if rig is None:
        return ['%s has no rig' % part.name]
    found, names = [], [b[0] for b in rig['bones']]
    if names[0] != 'Root' or rig['bones'][0][1] is not None:
        found.append('the first bone must be Root, without a parent')
    for k, (name, parent, head, tail) in enumerate(rig['bones']):
        if k and parent not in names[:k]:
            found.append('bone %s: its parent %s is not listed before it' % (name, parent))
        if np.linalg.norm(np.subtract(tail, head)) < 1e-4:
            found.append('bone %s has no length' % name)
    if len(set(names)) != len(names):
        found.append('bone names repeat')
    index, weight = np.asarray(rig['index']), np.asarray(rig['weight'], np.float64)
    n = len(part.v)
    if index.shape != (n, 4) or weight.shape != (n, 4):
        found.append('index and weight must be (%d, 4), got %s and %s' % (n, index.shape, weight.shape))
    else:
        if index.min() < 0 or index.max() >= len(names):
            found.append('bone indices out of range')
        if np.abs(weight.sum(1) - 1).max() > 1e-3 or weight.min() < 0:
            found.append('weights must be >= 0 and sum to 1 per vertex')
    for name, anim in rig['anims'].items():
        unknown = set()
        for t in np.linspace(0, anim['seconds'], 7):
            unknown |= set(anim['pose'](float(t))) - set(names)
        if unknown:
            found.append('%s poses unknown bones %s' % (name, sorted(unknown)[:6]))
    return ['%s: %s' % (part.name, text) for text in found]


CM = 100.0   # the scene is in centimetres (unit scale 0.01) so the skeleton's root reaches Unreal at scale 1


def flip(p):
    return Vector((p[0] * CM, -p[1] * CM, p[2] * CM))


def rotation(vector):
    """A mesh-axes rotation vector as a Blender-space 3x3 rotation."""
    r = Vector((-vector[0], vector[1], -vector[2]))
    angle = r.length
    return Matrix.Identity(3) if angle < 1e-9 else Matrix.Rotation(angle, 3, r / angle)


def clear():
    for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.actions):
        for item in list(collection):
            collection.remove(item)


def select(*objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def export(part):
    rig = part.rig
    stem = part.name[3:]   # SM_AE_Mote -> AE_Mote
    clear()
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0 / CM
    ob = part.build()
    ob.data.transform(Matrix.Scale(CM, 4))
    armature = bpy.data.armatures.new('Armature')
    arm = bpy.data.objects.new('Armature', armature)   # Unreal drops a node of this name, so Root is the root bone
    bpy.context.scene.collection.objects.link(arm)
    select(arm)
    bpy.ops.object.mode_set(mode='EDIT')
    made = {}
    for name, parent, head, tail in rig['bones']:
        bone = armature.edit_bones.new(name)
        bone.head, bone.tail = flip(head), flip(tail)
        if parent is not None:
            bone.parent = made[parent]
            bone.use_connect = False
        made[name] = bone
    bpy.ops.object.mode_set(mode='OBJECT')
    names = [b[0] for b in rig['bones']]
    index, weight = np.asarray(rig['index']), np.asarray(rig['weight'], np.float64)
    groups = [ob.vertex_groups.new(name=name) for name in names]
    for column in range(4):
        for vertex in np.nonzero(weight[:, column] > 1e-5)[0]:
            groups[index[vertex, column]].add([int(vertex)], float(weight[vertex, column]), 'ADD')
    modifier = ob.modifiers.new('Armature', 'ARMATURE')
    modifier.object = arm
    ob.parent = arm
    OUT.mkdir(parents=True, exist_ok=True)
    select(arm, ob)
    bpy.ops.export_scene.fbx(filepath=str(OUT / ('SK_%s.fbx' % stem)), object_types={'ARMATURE', 'MESH'}, bake_anim=False, **FBX)

    rest = {bone.name: bone.matrix_local.to_3x3() for bone in armature.bones}
    scene = bpy.context.scene
    scene.render.fps = FPS
    written = []
    for anim_name, anim in rig['anims'].items():
        frames = int(round(anim['seconds'] * FPS))
        arm.animation_data_clear()
        arm.animation_data_create()
        action = bpy.data.actions.new(anim_name)
        arm.animation_data.action = action
        for bone in arm.pose.bones:
            bone.rotation_mode = 'QUATERNION'
        for frame in range(frames + 1):
            pose = anim['pose'](frame / FPS)
            for bone in arm.pose.bones:
                if bone.name == 'Root':
                    continue
                b = rest[bone.name]
                turn = pose.get(bone.name)
                basis = Matrix.Identity(3) if turn is None else b.transposed() @ rotation(turn) @ b
                q = basis.to_quaternion()
                previous = bone.rotation_quaternion
                if frame and previous.dot(q) < 0:   # the short way round, so keys never flip between frames
                    q.negate()
                bone.rotation_quaternion = q
                bone.keyframe_insert('rotation_quaternion', frame=frame)
        scene.frame_start, scene.frame_end = 0, frames
        select(arm)
        bpy.ops.export_scene.fbx(filepath=str(OUT / ('A_%s_%s.fbx' % (stem, anim_name))), object_types={'ARMATURE'}, bake_anim=True,
                                 bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
                                 bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, bake_anim_step=1.0, **FBX)
        written.append('%s %d frames' % (anim_name, frames))
    return len(names), written


def main():
    words = [a.lower() for a in (sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])]
    creatures = importlib.import_module('creatures')
    problems = []
    for builder in creatures.MESHES:
        start = time.time()
        part = builder()
        if words and not any(w in part.name.lower() for w in words):
            continue
        found = check_rig(part)
        if found:
            problems.extend(found)
            print('refused %s: %s' % (part.name, '; '.join(found)), flush=True)
            continue
        bones, written = export(part)
        print('rig %-18s %3d bones  %s  %.1f s' % (part.name, bones, ', '.join(written), time.time() - start), flush=True)
    if problems:
        print('\nFAILED (%d):\n  - %s' % (len(problems), '\n  - '.join(problems)))
        sys.exit(1)
    print('\nall rigs written to', OUT)


if __name__ == '__main__':
    main()
