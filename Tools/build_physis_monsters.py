"""The elemental monsters' generated models (Art/Monsters/Models/<Name>.glb, from Tools/image_to_3d.py) made into game
animals: reduced, set on a skeleton, skinned, animated, and written as

  Art/Meshes/Monsters/SM_MN_<Name>.fbx                 a light static copy (the enemy's collision and bounds)
  Art/Meshes/Monsters/Rigged/SK_MN_<Name>.fbx          the mesh on its skeleton
  Art/Meshes/Monsters/Rigged/A_MN_<Name>_Swim.fbx      its walk, a loop (the enemy blueprint calls every gait Swim)
  Art/Meshes/Monsters/Rigged/A_MN_<Name>_Strike.fbx    its attack, 1.3 s
  Art/Meshes/Monsters/T_MN_<Name>_D.png (and _ORM)     the model's own textures

Run:
  LD_LIBRARY_PATH=Saved/AudioTools/libplacebo387 blender -b --python-exit-code 1 --python Tools/build_physis_monsters.py -- [Name ...] [--preview DIR]
then physis_monster_models.import_all() in the editor (Content/Python).

A generated model is one welded surface with no parts, so the skeleton is laid in by hand: each MONSTERS entry gives the
joints, measured on the model (Blender units as generated, about 1 long), in the axes the game uses: x forward, y left,
z up, the origin at the middle of the model's box. `turn` is the rotation that brings the generated model into those
axes. Skin weights: Blender's automatic weights fail on a generated surface (loose strands, holes), so they are solved
on a closed voxel copy and carried over to the real mesh by nearest surface.

Poses are rotation vectors (axis times angle, radians) per bone, in those same axes, about the bone's head, in the
frame its posed parent carries. About +y a positive turn pitches the nose down and swings a hanging leg backwards.

Units and FBX settings are those of Tools/build_physis_arche_rigs.py (a scene in centimetres at unit scale 0.01).
"""
import heapq
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'Art/Monsters/Models'
OUT = ROOT / 'Art/Meshes/Monsters'
FPS = 30
FBX = dict(use_selection=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1.0, mesh_smooth_type='FACE', add_leaf_bones=False, colors_type='LINEAR',
           use_tspace=False, axis_forward='-Z', axis_up='Y', primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False)
TAU = 2 * math.pi


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def keyed(t, keys):
    """keys: [(time, {bone: (x, y, z)})], in order. The pose at t, eased between the two keys round it."""
    if t <= keys[0][0]:
        return dict(keys[0][1])
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            k = smooth((t - t0) / (t1 - t0))
            return {name: tuple(np.asarray(a.get(name, (0, 0, 0))) * (1 - k) + np.asarray(b.get(name, (0, 0, 0))) * k) for name in set(a) | set(b)}
    return dict(keys[-1][1])


def leg(pose, upper, lower, foot, phase, swing, fold):
    """One walking leg: the upper bone swings, and on the way forward the lower folds and the foot hangs."""
    lift = max(0.0, math.cos(phase))
    pose[upper] = (0, -swing * math.sin(phase), 0)
    pose[lower] = (0, fold * lift, 0)
    pose[foot] = (0, -0.45 * fold * lift, 0)


# ---------------------------------------------------------------- Pyre Lion

def lion_walk(t, seconds=1.2):
    p = TAU * t / seconds
    pose = {'Pelvis': (0.04 * math.sin(p), 0, 0.04 * math.sin(p)), 'Spine': (0, 0.02 * math.sin(2 * p), -0.05 * math.sin(p)), 'Chest': (-0.04 * math.sin(p), 0, -0.03 * math.sin(p)),
            'Neck': (0, 0.05 * math.sin(2 * p + .6), 0.03 * math.sin(p)), 'Head': (0, -0.04 * math.sin(2 * p + .6), 0.04 * math.sin(p))}
    for k, name in enumerate(('Tail1', 'Tail2', 'Tail3')):
        pose[name] = (0, 0.08 * math.sin(p - k), 0.22 * math.sin(p - .7 * k))
    leg(pose, 'FrontL_Upper', 'FrontL_Lower', 'FrontL_Foot', p, 0.30, 0.5)
    leg(pose, 'HindR_Upper', 'HindR_Lower', 'HindR_Foot', p + 0.5, 0.30, 0.5)
    leg(pose, 'FrontR_Upper', 'FrontR_Lower', 'FrontR_Foot', p + math.pi, 0.30, 0.5)
    leg(pose, 'HindL_Upper', 'HindL_Lower', 'HindL_Foot', p + math.pi + 0.5, 0.30, 0.5)
    return pose


def lion_strike(t):
    """It gathers on its haunches, rears with the right paw up, then comes down with the paw and the jaws."""
    start = lion_walk(0.0)
    rear = {'Pelvis': (0, 0.10, 0), 'Spine': (0, -0.16, 0), 'Chest': (0, -0.24, 0.06), 'Neck': (0, -0.22, 0), 'Head': (0, -0.20, 0),
            'FrontR_Upper': (0, -0.6, 0), 'FrontR_Lower': (0, 0.6, 0), 'FrontR_Foot': (0, -0.25, 0), 'FrontL_Upper': (0, 0.22, 0), 'FrontL_Lower': (0, 0.1, 0),
            'HindL_Upper': (0, -0.2, 0), 'HindR_Upper': (0, -0.2, 0), 'HindL_Lower': (0, 0.28, 0), 'HindR_Lower': (0, 0.28, 0),
            'Tail1': (0, -0.5, 0), 'Tail2': (0, -0.3, 0.2), 'Tail3': (0, -0.2, 0.3)}
    hit = {'Pelvis': (0, -0.05, 0), 'Spine': (0, 0.12, 0), 'Chest': (0, 0.22, -0.08), 'Neck': (0, 0.20, 0), 'Head': (0, 0.16, 0),
           'FrontR_Upper': (0, -0.55, 0.15), 'FrontR_Lower': (0, 0.15, 0), 'FrontR_Foot': (0, 0.5, 0), 'FrontL_Upper': (0, 0.3, 0),
           'HindL_Upper': (0, 0.2, 0), 'HindR_Upper': (0, 0.2, 0), 'Tail1': (0, 0.3, 0), 'Tail2': (0, 0.2, -0.3), 'Tail3': (0, 0.1, -0.4)}
    return keyed(t, [(0.0, start), (0.42, rear), (0.50, rear), (0.66, hit), (0.82, hit), (1.3, start)])


def lion_paint(p):
    """Vertex colours for the lion, from places measured on the generated model (its own axes: x sideways, the head
    at -y, z up). RGB multiplies the skin's picture, alpha is a glow mask.
    The author, 2026-11-17: "the Lion doesn't have eyes and its mane is the same color as his body, it needs to be
    darker." The mane is everything forward of the shoulders and above the forelegs, but for the face; the model's
    eyes are shut and its face has too few vertices to paint one on, so the eyes are added as small shapes (EYES)."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ramp = lambda v, a, b: np.clip((v - a) / (b - a), 0.0, 1.0)
    mane = ramp(-y, 0.0, 0.06) * ramp(z, -0.19, -0.13)
    face = ramp(-y, 0.33, 0.37) * ramp(x, -0.03, 0.0) * ramp(-x, -0.155, -0.125) * ramp(z, -0.01, 0.03) * ramp(-z, -0.275, -0.245)
    mane = mane * (1.0 - face)
    colour = np.ones((len(p), 4))
    colour[:, :3] = 1.0 - mane[:, None] * (1.0 - np.array([0.30, 0.24, 0.21]))
    colour[:, 3] = 0.0
    return colour


# The second lion (2026-11-18): regenerated from a picture with a black mane and open eyes, after the author's "the
# Lion doesn't have eyes and its mane is the same color as his body". It needs neither lion_paint nor add_eyes, which
# stay for the first model (Art/Monsters/Models/PyreLion_before.glb). Its head is turned to its right, its hind legs
# stand one ahead of the other, and its body lies 0.04 to the left of the model's middle.
LION = {
    'model': 'PyreLion', 'turn': 90.0, 'length_cm': 300.0, 'middle': 0.04,
    'bones': [
        ('Root', None, (0, 0, 0), (0.06, 0, 0)),
        ('Pelvis', 'Root', (-0.30, 0.04, 0.13), (-0.12, 0.04, 0.17)), ('Spine', 'Pelvis', (-0.12, 0.04, 0.17), (0.08, 0.04, 0.17)), ('Chest', 'Spine', (0.08, 0.04, 0.17), (0.20, 0.04, 0.16)),
        ('Neck', 'Chest', (0.20, 0.04, 0.16), (0.30, 0.02, 0.22)), ('Head', 'Neck', (0.30, 0.02, 0.22), (0.44, -0.18, 0.20)),
        ('Tail1', 'Pelvis', (-0.37, 0.03, 0.08), (-0.39, 0.02, -0.08)), ('Tail2', 'Tail1', (-0.39, 0.02, -0.08), (-0.39, 0.0, -0.24)), ('Tail3', 'Tail2', (-0.39, 0.0, -0.24), (-0.46, -0.07, -0.17)),
        ('FrontL_Upper', 'Chest', (0.24, 0.11, 0.0), (0.25, 0.11, -0.13)), ('FrontL_Lower', 'FrontL_Upper', (0.25, 0.11, -0.13), (0.26, 0.11, -0.30)), ('FrontL_Foot', 'FrontL_Lower', (0.26, 0.11, -0.30), (0.32, 0.11, -0.40)),
        ('FrontR_Upper', 'Chest', (0.24, -0.03, 0.0), (0.25, -0.03, -0.13)), ('FrontR_Lower', 'FrontR_Upper', (0.25, -0.03, -0.13), (0.26, -0.03, -0.30)), ('FrontR_Foot', 'FrontR_Lower', (0.26, -0.03, -0.30), (0.32, -0.03, -0.40)),
        ('HindL_Upper', 'Pelvis', (-0.26, 0.12, 0.06), (-0.17, 0.12, -0.12)), ('HindL_Lower', 'HindL_Upper', (-0.17, 0.12, -0.12), (-0.25, 0.10, -0.28)), ('HindL_Foot', 'HindL_Lower', (-0.25, 0.10, -0.28), (-0.16, 0.13, -0.40)),
        ('HindR_Upper', 'Pelvis', (-0.26, -0.03, 0.06), (-0.19, -0.03, -0.16)), ('HindR_Lower', 'HindR_Upper', (-0.19, -0.03, -0.16), (-0.35, -0.03, -0.26)), ('HindR_Foot', 'HindR_Lower', (-0.35, -0.03, -0.26), (-0.30, -0.06, -0.40)),
    ],
    'anims': {'Swim': (1.2, lion_walk), 'Strike': (1.3, lion_strike)},
}


# ---------------------------------------------------------------- the drake

def drake_walk(t, seconds=1.4):
    p = TAU * t / seconds
    pose = {'Pelvis': (0.05 * math.sin(p), 0.02 * math.sin(2 * p), 0.06 * math.sin(p)), 'Spine': (0, 0, -0.04 * math.sin(p)), 'Chest': (-0.04 * math.sin(p), 0.03 * math.sin(2 * p), -0.04 * math.sin(p)),
            'Neck1': (0, 0.06 * math.sin(2 * p + .5), 0.05 * math.sin(p + .4)), 'Neck2': (0, -0.05 * math.sin(2 * p + .5), 0.04 * math.sin(p + .8)), 'Head': (0, 0.05 * math.sin(2 * p + 1.0), 0.05 * math.sin(p + 1.2)),
            'Wing1': (0.14 * math.sin(2 * p), 0, 0.05 * math.sin(p)), 'Wing2': (0.10 * math.sin(2 * p - .6), 0, 0), 'WingWeb': (0.12 * math.sin(2 * p - .9), 0, 0),
            'ArmR_Upper': (0, 0.12 * math.sin(p), 0), 'ArmR_Lower': (0, 0.10 * math.sin(p + .5), 0), 'ArmL_Upper': (0, -0.12 * math.sin(p), 0), 'ArmL_Lower': (0, -0.10 * math.sin(p + .5), 0)}
    for k, name in enumerate(('Tail1', 'Tail2', 'Tail3', 'Tail4')):
        pose[name] = (0, 0.05 * math.sin(2 * p - k), 0.16 * math.sin(p - .7 * k))
    leg(pose, 'LegR_Upper', 'LegR_Lower', 'LegR_Foot', p, 0.40, 0.7)
    leg(pose, 'LegL_Upper', 'LegL_Lower', 'LegL_Foot', p + math.pi, 0.40, 0.7)
    return pose


def drake_strike(t):
    """It draws its neck back and its wing up, then snaps the head forward and down."""
    start = drake_walk(0.0)
    draw = {'Pelvis': (0, 0.03, 0), 'Spine': (0, -0.07, 0), 'Chest': (0, -0.10, 0), 'Neck1': (0, -0.22, 0), 'Neck2': (0, -0.10, 0), 'Head': (0, 0.18, 0),
            'Wing1': (-0.30, -0.1, 0), 'Wing2': (-0.2, 0, 0), 'WingWeb': (-0.2, 0, 0), 'ArmR_Upper': (0, -0.3, 0), 'ArmL_Upper': (0, -0.3, 0),
            'Tail1': (0, 0.2, 0), 'Tail2': (0, 0.15, 0.2), 'Tail3': (0, 0.1, 0.3), 'LegR_Upper': (0, 0.12, 0), 'LegL_Upper': (0, 0.12, 0)}
    snap = {'Pelvis': (0, -0.02, 0), 'Spine': (0, 0.08, 0), 'Chest': (0, 0.12, 0), 'Neck1': (0, 0.30, 0), 'Neck2': (0, 0.18, 0), 'Head': (0, -0.10, 0),
            'Wing1': (0.2, 0.1, 0), 'Wing2': (0.2, 0, 0), 'WingWeb': (0.25, 0, 0), 'ArmR_Upper': (0, 0.3, 0), 'ArmL_Upper': (0, 0.3, 0),
            'Tail1': (0, -0.25, 0), 'Tail2': (0, -0.2, -0.2), 'Tail3': (0, -0.15, -0.3), 'LegR_Upper': (0, -0.15, 0), 'LegL_Upper': (0, -0.15, 0)}
    return keyed(t, [(0.0, start), (0.44, draw), (0.52, draw), (0.66, snap), (0.84, snap), (1.3, start)])


DRAKE = {
    'model': 'StormDrake', 'turn': 11.6, 'length_cm': 430.0, 'faces': 90000, 'middle': 0.02,
    'bones': [
        ('Root', None, (0, 0, 0), (0.06, 0, 0)),
        ('Pelvis', 'Root', (-0.06, 0.02, -0.07), (0.07, 0.02, -0.02)), ('Spine', 'Pelvis', (0.07, 0.02, -0.02), (0.16, 0.03, 0.08)), ('Chest', 'Spine', (0.16, 0.03, 0.08), (0.17, 0.03, 0.20)),
        ('Neck1', 'Chest', (0.17, 0.03, 0.20), (0.16, 0.03, 0.33)), ('Neck2', 'Neck1', (0.16, 0.03, 0.33), (0.27, 0.03, 0.34)), ('Head', 'Neck2', (0.27, 0.03, 0.34), (0.48, 0.02, 0.28)),
        ('Tail1', 'Pelvis', (-0.06, 0.03, -0.07), (-0.20, 0.10, -0.14)), ('Tail2', 'Tail1', (-0.20, 0.10, -0.14), (-0.32, 0.12, -0.28)),
        ('Tail3', 'Tail2', (-0.32, 0.12, -0.28), (-0.43, 0.07, -0.38)), ('Tail4', 'Tail3', (-0.43, 0.07, -0.38), (-0.50, 0.05, -0.35)),
        ('Wing1', 'Chest', (0.03, 0.08, 0.26), (-0.05, 0.18, 0.33)), ('Wing2', 'Wing1', (-0.05, 0.18, 0.33), (-0.30, 0.24, 0.37)), ('WingWeb', 'Wing1', (-0.05, 0.18, 0.33), (-0.10, 0.30, 0.0)),
        ('LegR_Upper', 'Pelvis', (0.0, -0.08, -0.08), (0.04, -0.08, -0.21)), ('LegR_Lower', 'LegR_Upper', (0.04, -0.08, -0.21), (0.01, -0.10, -0.36)), ('LegR_Foot', 'LegR_Lower', (0.01, -0.10, -0.36), (0.14, -0.15, -0.45)),
        ('LegL_Upper', 'Pelvis', (-0.03, 0.10, -0.08), (0.05, 0.11, -0.22)), ('LegL_Lower', 'LegL_Upper', (0.05, 0.11, -0.22), (-0.13, 0.14, -0.37)), ('LegL_Foot', 'LegL_Lower', (-0.13, 0.14, -0.37), (-0.04, 0.20, -0.45)),
        ('ArmR_Upper', 'Chest', (0.15, -0.06, 0.06), (0.12, -0.18, 0.04)), ('ArmR_Lower', 'ArmR_Upper', (0.12, -0.18, 0.04), (0.04, -0.30, 0.02)),
        ('ArmL_Upper', 'Chest', (0.15, 0.02, -0.04), (0.19, -0.02, -0.16)), ('ArmL_Lower', 'ArmL_Upper', (0.19, -0.02, -0.16), (0.21, -0.01, -0.30)),
    ],
    'anims': {'Swim': (1.4, drake_walk), 'Strike': (1.3, drake_strike)},
}

# ---------------------------------------------------------------- the mammoth

def mammoth_walk(t, seconds=2.0):
    p = TAU * t / seconds
    pose = {'Pelvis': (0.03 * math.sin(p), 0, 0.03 * math.sin(p)), 'Spine': (0, 0.015 * math.sin(2 * p), -0.03 * math.sin(p)), 'Chest': (-0.03 * math.sin(p), 0, -0.02 * math.sin(p)),
            'Neck': (0, 0.04 * math.sin(2 * p + .5), 0), 'Head': (0, -0.05 * math.sin(2 * p + .5), 0.05 * math.sin(p)),
            'Trunk1': (0, 0.10 * math.sin(p), 0.10 * math.sin(p + .3)), 'Trunk2': (0, 0.14 * math.sin(p - .6), 0.12 * math.sin(p - .4)), 'Trunk3': (0, 0.18 * math.sin(p - 1.2), 0.12 * math.sin(p - 1.0)),
            'Tail1': (0, 0, 0.2 * math.sin(2 * p)), 'Tail2': (0, 0, 0.3 * math.sin(2 * p - .8))}
    leg(pose, 'FrontL_Upper', 'FrontL_Lower', 'FrontL_Foot', p, 0.28, 0.45)
    leg(pose, 'HindR_Upper', 'HindR_Lower', 'HindR_Foot', p + 0.6, 0.24, 0.4)
    leg(pose, 'FrontR_Upper', 'FrontR_Lower', 'FrontR_Foot', p + math.pi, 0.28, 0.45)
    leg(pose, 'HindL_Upper', 'HindL_Lower', 'HindL_Foot', p + math.pi + 0.6, 0.24, 0.4)
    return pose


def mammoth_strike(t):
    """It throws its head and trunk up, then brings the tusks down and forward."""
    start = mammoth_walk(0.0)
    up = {'Spine': (0, -0.03, 0), 'Chest': (0, -0.06, 0), 'Neck': (0, -0.12, 0), 'Head': (0, -0.16, 0), 'Trunk1': (0, -0.35, 0), 'Trunk2': (0, -0.4, 0), 'Trunk3': (0, -0.4, 0),
          'FrontL_Upper': (0, -0.25, 0), 'FrontL_Lower': (0, 0.4, 0), 'Tail1': (0, -0.4, 0)}
    down = {'Spine': (0, 0.04, 0), 'Chest': (0, 0.08, 0), 'Neck': (0, 0.14, 0), 'Head': (0, 0.18, 0), 'Trunk1': (0, 0.2, 0), 'Trunk2': (0, 0.2, 0), 'Trunk3': (0, 0.2, 0),
            'FrontL_Upper': (0, 0.1, 0), 'Tail1': (0, 0.2, 0)}
    return keyed(t, [(0.0, start), (0.46, up), (0.54, up), (0.70, down), (0.86, down), (1.3, start)])


MAMMOTH = {
    'model': 'RimeMammoth', 'turn': 0.0, 'length_cm': 430.0,
    'bones': [
        ('Root', None, (0, 0, 0), (0.06, 0, 0)),
        ('Pelvis', 'Root', (-0.36, 0, 0.15), (-0.15, 0, 0.22)), ('Spine', 'Pelvis', (-0.15, 0, 0.22), (0.05, 0, 0.25)), ('Chest', 'Spine', (0.05, 0, 0.25), (0.16, 0, 0.24)),
        ('Neck', 'Chest', (0.16, 0, 0.24), (0.24, 0, 0.21)), ('Head', 'Neck', (0.24, 0, 0.21), (0.36, 0, 0.14)),
        ('Trunk1', 'Head', (0.36, 0, 0.13), (0.38, 0, 0.0)), ('Trunk2', 'Trunk1', (0.38, 0, 0.0), (0.43, 0, -0.10)), ('Trunk3', 'Trunk2', (0.43, 0, -0.10), (0.45, 0, -0.16)),
        # the tusks curl round the trunk: without bones of their own their skin went with the trunk and they folded into the head
        ('TuskL1', 'Head', (0.31, 0.07, 0.09), (0.42, 0.11, -0.01)), ('TuskL2', 'TuskL1', (0.42, 0.11, -0.01), (0.43, 0.12, 0.25)),
        ('TuskR1', 'Head', (0.31, -0.07, 0.09), (0.42, -0.11, -0.01)), ('TuskR2', 'TuskR1', (0.42, -0.11, -0.01), (0.43, -0.12, 0.25)),
        ('Tail1', 'Pelvis', (-0.45, 0.05, 0.06), (-0.47, 0.07, -0.05)), ('Tail2', 'Tail1', (-0.47, 0.07, -0.05), (-0.48, 0.08, -0.16)),
    ] + [row for side, y in (('L', 0.075), ('R', -0.075)) for row in (
        ('Front%s_Upper' % side, 'Chest', (0.12, y, 0.02), (0.11, y, -0.16)), ('Front%s_Lower' % side, 'Front%s_Upper' % side, (0.11, y, -0.16), (0.13, y, -0.31)),
        ('Front%s_Foot' % side, 'Front%s_Lower' % side, (0.13, y, -0.31), (0.17, y, -0.365)),
        ('Hind%s_Upper' % side, 'Pelvis', (-0.34, y, 0.0), (-0.33, y, -0.17)), ('Hind%s_Lower' % side, 'Hind%s_Upper' % side, (-0.33, y, -0.17), (-0.35, y, -0.31)),
        ('Hind%s_Foot' % side, 'Hind%s_Lower' % side, (-0.35, y, -0.31), (-0.31, y, -0.365)))],
    'anims': {'Swim': (2.0, mammoth_walk), 'Strike': (1.3, mammoth_strike)},
}


# ---------------------------------------------------------------- the toad

def toad_walk(t, seconds=1.4):
    """A heavy crawl: it reaches with one forelimb and the other, and its body rocks."""
    p = TAU * t / seconds
    pose = {'Pelvis': (0.04 * math.sin(p), 0.04 * math.sin(2 * p), 0.05 * math.sin(p)), 'Spine': (0, -0.03 * math.sin(2 * p), -0.04 * math.sin(p)), 'Chest': (0, -0.04 * math.sin(2 * p), -0.04 * math.sin(p)),
            'Head': (0, 0.05 * math.sin(2 * p + .6), 0.05 * math.sin(p))}
    for side, phase in (('L', p), ('R', p + math.pi)):
        lift = max(0.0, math.cos(phase))
        pose['Front%s_Upper' % side] = (0, -0.30 * math.sin(phase), 0.12 * math.sin(phase) * (1 if side == 'L' else -1))
        pose['Front%s_Lower' % side] = (0, -0.35 * lift, 0)
        pose['Front%s_Foot' % side] = (0, 0.3 * lift, 0)
        back = phase + math.pi
        pose['Hind%s_Upper' % side] = (0, 0.14 * math.sin(back), 0)
        pose['Hind%s_Lower' % side] = (0, -0.18 * math.sin(back), 0)
        pose['Hind%s_Foot' % side] = (0, 0.14 * math.sin(back), 0)
    return pose


def toad_strike(t):
    """It sinks on its haunches, then throws its head and forelimbs forward and up."""
    start = toad_walk(0.0)
    sink = {'Pelvis': (0, 0.10, 0), 'Spine': (0, 0.08, 0), 'Chest': (0, 0.06, 0), 'Head': (0, 0.12, 0),
            'FrontL_Upper': (0, 0.25, 0), 'FrontR_Upper': (0, 0.25, 0), 'HindL_Upper': (0, -0.12, 0), 'HindR_Upper': (0, -0.12, 0)}
    lunge = {'Pelvis': (0, -0.10, 0), 'Spine': (0, -0.08, 0), 'Chest': (0, -0.06, 0), 'Head': (0, -0.12, 0),
             'FrontL_Upper': (0, -0.7, 0.2), 'FrontR_Upper': (0, -0.7, -0.2), 'FrontL_Lower': (0, -0.4, 0), 'FrontR_Lower': (0, -0.4, 0),
             'HindL_Upper': (0, 0.3, 0), 'HindR_Upper': (0, 0.3, 0), 'HindL_Lower': (0, -0.35, 0), 'HindR_Lower': (0, -0.35, 0), 'HindL_Foot': (0, 0.3, 0), 'HindR_Foot': (0, 0.3, 0)}
    return keyed(t, [(0.0, start), (0.44, sink), (0.52, sink), (0.66, lunge), (0.84, lunge), (1.3, start)])


TOAD = {
    'model': 'GloomToad', 'turn': 90.0, 'length_cm': 260.0,
    'bones': [
        ('Root', None, (0, 0, 0), (0.06, 0, 0)),
        ('Pelvis', 'Root', (-0.40, 0, -0.08), (-0.15, 0, 0.05)), ('Spine', 'Pelvis', (-0.15, 0, 0.05), (0.10, 0, 0.12)), ('Chest', 'Spine', (0.10, 0, 0.12), (0.25, 0, 0.17)),
        ('Head', 'Chest', (0.25, 0, 0.17), (0.48, 0, 0.25)),
    ] + [row for side, k in (('L', 1), ('R', -1)) for row in (
        ('Front%s_Upper' % side, 'Chest', (0.13, 0.30 * k, 0.0), (0.17, 0.34 * k, -0.22)), ('Front%s_Lower' % side, 'Front%s_Upper' % side, (0.17, 0.34 * k, -0.22), (0.36, 0.31 * k, -0.35)),
        ('Front%s_Foot' % side, 'Front%s_Lower' % side, (0.36, 0.31 * k, -0.35), (0.44, 0.31 * k, -0.37)),
        ('Hind%s_Upper' % side, 'Pelvis', (-0.42, 0.20 * k, -0.10), (-0.10, 0.33 * k, -0.20)), ('Hind%s_Lower' % side, 'Hind%s_Upper' % side, (-0.10, 0.33 * k, -0.20), (-0.44, 0.36 * k, -0.28)),
        ('Hind%s_Foot' % side, 'Hind%s_Lower' % side, (-0.44, 0.36 * k, -0.28), (-0.08, 0.30 * k, -0.35)))],
    'anims': {'Swim': (1.4, toad_walk), 'Strike': (1.3, toad_strike)},
}


# ---------------------------------------------------------------- the mantis

MANTIS_LIMBS = ('L1', 'R2', 'L3', 'R1', 'L2', 'R3')   # the first three step together, then the other three


def mantis_walk(t, seconds=0.9):
    p = TAU * t / seconds
    pose = {'Thorax': (0.03 * math.sin(p), 0.03 * math.sin(2 * p), 0.04 * math.sin(p)), 'Head': (0, 0.06 * math.sin(2 * p + .5), 0.10 * math.sin(p + .4)),
            'Abdomen1': (0, 0.03 * math.sin(2 * p), -0.05 * math.sin(p)), 'Abdomen2': (0, 0.04 * math.sin(2 * p - .6), -0.07 * math.sin(p - .5)),
            'ArmL': (0, 0.10 * math.sin(2 * p), 0), 'ArmR': (0, 0.10 * math.sin(2 * p + 1.0), 0)}
    for k, name in enumerate(MANTIS_LIMBS):
        phase = p + (0 if k < 3 else math.pi)
        turn = 1 if 'L' in name else -1
        lift = max(0.0, math.cos(phase))
        pose['Limb%s_Upper' % name] = (0.10 * lift * turn, 0, 0.22 * math.sin(phase) * turn)   # swings about the upright, lifts sideways
        pose['Limb%s_Lower' % name] = (-0.14 * lift * turn, 0, 0)
    return pose


def mantis_strike(t):
    """It rears on its hind legs with the forelimbs high, then whips them down."""
    start = mantis_walk(0.0)
    rear = {'Thorax': (0, -0.35, 0), 'Head': (0, 0.15, 0), 'Abdomen1': (0, 0.10, 0), 'ArmL': (0, -0.9, 0.2), 'ArmR': (0, -0.9, -0.2),
            'LimbL1_Upper': (0, -0.5, 0), 'LimbR1_Upper': (0, -0.5, 0), 'LimbL1_Lower': (0, -0.3, 0), 'LimbR1_Lower': (0, -0.3, 0)}
    cut = {'Thorax': (0, 0.28, 0), 'Head': (0, -0.10, 0), 'Abdomen1': (0, -0.08, 0), 'ArmL': (0, 0.8, -0.1), 'ArmR': (0, 0.8, 0.1),
           'LimbL1_Upper': (0, 0.35, 0), 'LimbR1_Upper': (0, 0.35, 0)}
    return keyed(t, [(0.0, start), (0.42, rear), (0.52, rear), (0.63, cut), (0.82, cut), (1.3, start)])


def _limb(name, hip, knee, foot):
    return [('Limb%s_Upper' % name, 'Thorax', hip, knee), ('Limb%s_Lower' % name, 'Limb%s_Upper' % name, knee, foot)]


# Its legs are not a mirrored set (one forelimb crosses under the body), so each is measured by itself; they are named
# Limb, not Leg, because the rule that keeps a leg's skin on its own side of the body would cut the crossing one.
MANTIS = {
    'model': 'GaleMantis', 'turn': 90.0, 'length_cm': 330.0,
    'bones': [
        ('Root', None, (0, 0, 0), (0.06, 0, 0)),
        ('Thorax', 'Root', (0.0, 0, 0.05), (0.24, 0, 0.27)), ('Head', 'Thorax', (0.24, 0, 0.27), (0.33, 0, 0.22)),
        ('Abdomen1', 'Root', (0.0, 0, 0.05), (-0.25, 0, 0.0)), ('Abdomen2', 'Abdomen1', (-0.25, 0, 0.0), (-0.50, 0, -0.04)),
        ('ArmL', 'Thorax', (0.06, 0.06, 0.10), (0.20, 0.08, 0.08)), ('ArmR', 'Thorax', (0.06, -0.06, 0.10), (0.20, -0.08, 0.08)),
    ] + _limb('L1', (0.10, -0.05, 0.0), (0.33, -0.15, -0.07), (0.45, -0.13, -0.44)) + _limb('R1', (0.10, 0.03, 0.0), (0.28, -0.20, -0.08), (0.37, -0.17, -0.42))
      + _limb('L2', (0.02, -0.05, -0.02), (0.05, -0.22, -0.10), (0.13, -0.35, -0.44)) + _limb('R2', (0.0, 0.05, -0.02), (-0.05, 0.26, -0.10), (-0.05, 0.38, -0.44))
      + _limb('L3', (-0.05, -0.05, -0.02), (-0.15, -0.25, -0.10), (-0.29, -0.38, -0.44)) + _limb('R3', (-0.05, 0.05, -0.02), (-0.22, 0.15, -0.10), (-0.30, 0.19, -0.40)),
    'anims': {'Swim': (0.9, mantis_walk), 'Strike': (1.3, mantis_strike)},
}


# ---------------------------------------------------------------- the seraph

def seraph_glide(t, seconds=2.4):
    """It does not walk: it hangs upright, its wings beating slowly and its robe swaying."""
    p = TAU * t / seconds
    beat = math.sin(p)
    pose = {'Robe': (0.015 * math.sin(p), 0.02 * math.sin(p + .8), 0), 'Hips': (0, 0.02 * math.sin(p), 0.02 * math.sin(p)), 'Chest': (0, -0.03 * math.sin(p), 0),
            'Head': (0, 0.04 * math.sin(p + .5), 0.04 * math.sin(p * 0.5)), 'ArmL': (0.05 * beat, 0.05 * math.sin(p + 1), 0), 'ArmR': (-0.05 * beat, 0.05 * math.sin(p + 1), 0)}
    for side, k in (('L', 1), ('R', -1)):
        pose['Wing%s1' % side] = (0.14 * beat * k, 0, 0.03 * math.cos(p) * k)
        pose['Wing%s2' % side] = (0.08 * math.sin(p - .7) * k, 0, 0)
    return pose


def seraph_strike(t):
    """Its wings draw back and up, then sweep forward round what stands before it."""
    start = seraph_glide(0.0)
    back = {'Chest': (0, -0.08, 0), 'Head': (0, -0.12, 0), 'Robe': (0, 0.04, 0), 'ArmL': (0.3, -0.2, 0), 'ArmR': (-0.3, -0.2, 0),
            'WingL1': (0.28, 0, -0.12), 'WingR1': (-0.28, 0, 0.12), 'WingL2': (0.12, 0, -0.06), 'WingR2': (-0.12, 0, 0.06)}
    sweep = {'Chest': (0, 0.10, 0), 'Head': (0, 0.10, 0), 'Robe': (0, -0.04, 0), 'ArmL': (0.1, 0.4, 0), 'ArmR': (-0.1, 0.4, 0),
             'WingL1': (-0.18, 0, 0.22), 'WingR1': (0.18, 0, -0.22), 'WingL2': (-0.08, 0, 0.12), 'WingR2': (0.08, 0, -0.12)}
    return keyed(t, [(0.0, start), (0.44, back), (0.54, back), (0.68, sweep), (0.86, sweep), (1.3, start)])


SERAPH = {
    'model': 'Seraph', 'turn': 90.0, 'length_cm': 340.0,
    'bones': [
        ('Root', None, (0, 0, 0), (0.06, 0, 0)),
        ('Hips', 'Root', (0, 0, -0.15), (0, 0, 0.05)), ('Chest', 'Hips', (0, 0, 0.05), (0, 0, 0.22)), ('Head', 'Chest', (0, 0, 0.24), (0, 0, 0.38)),
        ('Robe', 'Hips', (0, 0, -0.15), (0, 0, -0.46)),
    ] + [row for side, k in (('L', 1), ('R', -1)) for row in (
        ('Wing%s1' % side, 'Chest', (-0.02, 0.06 * k, 0.20), (-0.02, 0.28 * k, 0.28)), ('Wing%s2' % side, 'Wing%s1' % side, (-0.02, 0.28 * k, 0.28), (-0.02, 0.50 * k, 0.33)),
        ('Arm%s' % side, 'Chest', (0.0, 0.07 * k, 0.20), (0.02, 0.12 * k, 0.0)))],
    'anims': {'Swim': (2.4, seraph_glide), 'Strike': (1.3, seraph_strike)},
}


# ---------------------------------------------------------------- the fiend

def fiend_walk(t, seconds=1.3):
    p = TAU * t / seconds
    pose = {'Pelvis': (0.04 * math.sin(p), 0.02 * math.sin(2 * p), 0.07 * math.sin(p)), 'Spine': (0, 0.03, -0.06 * math.sin(p)), 'Chest': (-0.03 * math.sin(p), 0.02 * math.sin(2 * p), -0.06 * math.sin(p)),
            'Head': (0, 0.04 * math.sin(2 * p + .5), 0.06 * math.sin(p)),
            'ArmL_Upper': (0, 0.30 * math.sin(p), 0), 'ArmL_Lower': (0, -0.15 - 0.15 * math.sin(p), 0), 'ArmR_Upper': (0, -0.30 * math.sin(p), 0), 'ArmR_Lower': (0, -0.15 + 0.15 * math.sin(p), 0)}
    for side, k in (('L', 1), ('R', -1)):
        pose['Wing%s1' % side] = (0.08 * math.sin(2 * p) * k, 0, 0.06 * math.sin(p) * k)
        pose['Wing%s2' % side] = (0.10 * math.sin(2 * p - .7) * k, 0, 0)
    leg(pose, 'LegR_Upper', 'LegR_Lower', 'LegR_Foot', p, 0.30, 0.5)
    leg(pose, 'LegL_Upper', 'LegL_Lower', 'LegL_Foot', p + math.pi, 0.30, 0.5)
    return pose


def fiend_strike(t):
    """It spreads its wings and draws its right claw back over its shoulder, then rakes it down across."""
    start = fiend_walk(0.0)
    draw = {'Pelvis': (0, 0.04, 0.15), 'Spine': (0, -0.08, 0.15), 'Chest': (0, -0.12, 0.2), 'Head': (0, -0.1, -0.2),
            'ArmR_Upper': (0.3, -1.6, 0), 'ArmR_Lower': (0, -0.7, 0), 'ArmL_Upper': (0, 0.3, 0),
            'WingL1': (0.4, 0, -0.2), 'WingR1': (-0.4, 0, 0.2), 'WingL2': (0.3, 0, 0), 'WingR2': (-0.3, 0, 0), 'LegL_Upper': (0, -0.2, 0), 'LegR_Upper': (0, 0.2, 0)}
    rake = {'Pelvis': (0, -0.04, -0.2), 'Spine': (0, 0.14, -0.2), 'Chest': (0, 0.2, -0.3), 'Head': (0, 0.1, 0.2),
            'ArmR_Upper': (-0.3, -0.5, 0.5), 'ArmR_Lower': (0, -0.2, 0), 'ArmL_Upper': (0, 0.5, 0),
            'WingL1': (-0.1, 0, 0.3), 'WingR1': (0.1, 0, -0.3), 'LegL_Upper': (0, 0.15, 0), 'LegR_Upper': (0, -0.3, 0), 'LegR_Lower': (0, 0.3, 0)}
    return keyed(t, [(0.0, start), (0.44, draw), (0.52, draw), (0.64, rake), (0.84, rake), (1.3, start)])


FIEND = {
    'model': 'NightFiend', 'turn': 90.0, 'length_cm': 300.0,
    'bones': [
        ('Root', None, (0, 0, 0), (0.06, 0, 0)),
        ('Pelvis', 'Root', (0.0, 0, -0.08), (0.02, 0, 0.05)), ('Spine', 'Pelvis', (0.02, 0, 0.05), (0.05, 0, 0.18)), ('Chest', 'Spine', (0.05, 0, 0.18), (0.08, 0, 0.27)),
        ('Head', 'Chest', (0.10, 0, 0.27), (0.16, 0, 0.40)),
        # what hangs behind and between its legs: a still bone of its own, or each leg drags half of it into a slab
        ('Cloth', 'Pelvis', (-0.08, 0, -0.12), (-0.16, 0, -0.30)),
    ] + [row for side, k in (('L', 1), ('R', -1)) for row in (
        ('Leg%s_Upper' % side, 'Pelvis', (0.02, 0.08 * k, -0.06), (0.07, 0.10 * k, -0.24)), ('Leg%s_Lower' % side, 'Leg%s_Upper' % side, (0.07, 0.10 * k, -0.24), (0.01, 0.08 * k, -0.40)),
        ('Leg%s_Foot' % side, 'Leg%s_Lower' % side, (0.01, 0.08 * k, -0.40), (0.14, 0.07 * k, -0.49)),
        ('Arm%s_Upper' % side, 'Chest', (0.05, 0.16 * k, 0.20), (0.04, 0.20 * k, 0.0)), ('Arm%s_Lower' % side, 'Arm%s_Upper' % side, (0.04, 0.20 * k, 0.0), (0.06, 0.19 * k, -0.14)),
        ('Wing%s1' % side, 'Chest', (-0.04, 0.10 * k, 0.25), (-0.06, 0.22 * k, 0.42)), ('Wing%s2' % side, 'Wing%s1' % side, (-0.06, 0.22 * k, 0.42), (-0.04, 0.40 * k, -0.28)))],
    'anims': {'Swim': (1.3, fiend_walk), 'Strike': (1.3, fiend_strike)},
}

MONSTERS = {'PyreLion': LION, 'StormDrake': DRAKE, 'RimeMammoth': MAMMOTH, 'GloomToad': TOAD, 'GaleMantis': MANTIS, 'Seraph': SERAPH, 'NightFiend': FIEND}


# ---------------------------------------------------------------- building

def select(*objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def rotation(vector):
    v = Vector(vector)
    return Matrix.Identity(3) if v.length < 1e-9 else Matrix.Rotation(v.length, 3, v.normalized())


def textures(ob, name):
    """The model's own images, saved beside the meshes: base colour, and the packed roughness and metal if it has them."""
    saved = {}
    tree = ob.data.materials[0].node_tree
    shader = next(n for n in tree.nodes if n.type == 'BSDF_PRINCIPLED')

    def image_of(socket):
        seen, links = set(), list(socket.links)
        while links:
            node = links.pop().from_node
            if node in seen:
                continue
            seen.add(node)
            if node.type == 'TEX_IMAGE' and node.image:
                return node.image
            for inp in node.inputs:
                links.extend(inp.links)
        return None
    for key, socket in (('D', 'Base Color'), ('ORM', 'Roughness')):
        image = image_of(shader.inputs[socket])
        if image is None:
            continue
        path = OUT / ('T_MN_%s_%s.png' % (name, key))
        scene = bpy.context.scene
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        image.save_render(str(path), scene=scene) if key == 'ORM' else image.save(filepath=str(path)) if image.file_format == 'PNG' else image.save_render(str(path), scene=scene)
        saved[key] = (path.name, tuple(image.size))
    return saved


def add_eyes(ob, world, spec):
    """A coal-bright eye with a slit pupil on the surface at each of spec['eyes'], found by looking at the head from
    straight ahead (the head is at -y). They join the mesh and wear its material: vertex colour white with alpha 1
    glows (physis_monster_models M_MN_Monster, Eye), black with alpha 0 is the pupil."""
    import bmesh
    bpy.context.view_layer.update()
    back = world.inverted()
    wide, high = spec['eye_size']
    made = []
    for ex, ez in spec['eyes']:
        hit, where, _, _ = ob.ray_cast(back @ Vector((ex, -2.0, ez)), back.to_3x3() @ Vector((0, 1, 0)))
        if not hit:
            continue
        spot = world @ where
        for label, radii, forward, colour in (('iris', (wide, wide * 0.3, high), 0.0, (1, 1, 1, 1)), ('pupil', (wide * 0.22, wide * 0.3, high * 0.9), wide * 0.12, (0, 0, 0, 0))):
            mesh = bpy.data.meshes.new('Eye')
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
            bm.to_mesh(mesh)
            bm.free()
            mesh.transform(back @ Matrix.Translation(spot + Vector((0, -forward, 0))) @ Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0)))
            for polygon in mesh.polygons:
                polygon.use_smooth = True
            mesh.uv_layers.new(name=ob.data.uv_layers[0].name)
            tint = mesh.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
            tint.data.foreach_set('color', np.tile(np.array(colour, np.float32), len(mesh.vertices)))
            mesh.materials.append(ob.data.materials[0])
            part = bpy.data.objects.new('Eye', mesh)
            part.matrix_world = world
            bpy.context.scene.collection.objects.link(part)
            made.append(part)
    if made:
        select(ob, *made)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.join()
    return len(made)


def build(name, preview=None):
    spec = MONSTERS[name]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.01
    bpy.ops.import_scene.gltf(filepath=str(MODELS / (spec['model'] + '.glb')))
    ob = next(o for o in scene.objects if o.type == 'MESH')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'Rigged').mkdir(exist_ok=True)
    report = {'textures': textures(ob, name)}

    world = ob.matrix_world.copy()
    ob.parent = None
    for other in [o for o in scene.objects if o is not ob]:
        bpy.data.objects.remove(other)
    points = np.array([world @ v.co for v in ob.data.vertices])
    lo, hi = points.min(0), points.max(0)
    size = spec['length_cm'] / float((hi - lo).max())
    # into the game's axes, the middle of the box at the origin, in centimetres
    place = Matrix.Scale(size, 4) @ Matrix.Rotation(math.radians(spec['turn']), 4, 'Z') @ Matrix.Translation(-Vector((lo + hi) / 2)) @ world
    paint = spec['paint'](points) if 'paint' in spec else np.concatenate([np.ones((len(points), 3)), np.zeros((len(points), 1))], axis=1)
    tint = ob.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')   # every monster carries one: with none the engine gives white with full alpha
    tint.data.foreach_set('color', paint.astype(np.float32).ravel())
    ob.data.color_attributes.active_color = tint
    ob.data.color_attributes.render_color_index = 0
    report['painted'] = [int((paint[:, :3].min(1) < 0.9).sum()), int((paint[:, 3] > 0.5).sum())]
    if spec.get('eyes'):
        add_eyes(ob, world, spec)
    ob.data.transform(place)
    ob.matrix_world = Matrix.Identity(4)
    if place.determinant() < 0:
        ob.data.flip_normals()
    ob.name = 'SK_MN_' + name
    report['faces_generated'] = len(ob.data.polygons)

    # A generated mesh is cut along every texture seam, and its smooth look is all in its stored normals (the faces
    # themselves are blocky). So the mesh that is exported stays exactly as generated; a welded copy, which is one
    # connected surface, is used only to work out the skin weights, and each real vertex takes those of the welded
    # vertex at its place. (Welding or reducing the real mesh lost the normals: flat blocks, 2026-11-17.)
    weld = ob.copy()
    weld.data = ob.data.copy()
    scene.collection.objects.link(weld)
    select(weld)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=spec['length_cm'] * 1e-5)
    bpy.ops.object.mode_set(mode='OBJECT')
    report['vertices_welded'] = len(weld.data.vertices)
    select(ob)
    ob.data.materials[0].name = 'Monster'
    points = np.array([v.co for v in ob.data.vertices])
    report.update(faces=len(ob.data.polygons), vertices=len(points), half_size_cm=[round(float(v)) for v in (points.max(0) - points.min(0)) / 2],
                  floor_cm=round(float(-points[:, 2].min()), 1))

    armature = bpy.data.armatures.new('Armature')
    arm = bpy.data.objects.new('Armature', armature)
    scene.collection.objects.link(arm)
    select(arm)
    bpy.ops.object.mode_set(mode='EDIT')
    made = {}
    for bone_name, parent, head, tail in spec['bones']:
        bone = armature.edit_bones.new(bone_name)
        bone.head, bone.tail = Vector(head) * size, Vector(tail) * size
        if parent is not None:
            bone.parent = made[parent]
            bone.use_connect = False
        made[bone_name] = bone
    bpy.ops.object.mode_set(mode='OBJECT')
    armature.bones['Root'].use_deform = False

    # Skin weights by distance: each vertex takes its four nearest bones, weighted by the inverse fourth power of its
    # distance to the bone's line, then the weights are relaxed along the mesh's edges so no crease shows at a joint.
    deform = [row for row in spec['bones'] if row[0] != 'Root']
    real = points
    points = np.array([v.co for v in weld.data.vertices])
    heads = np.array([row[2] for row in deform]) * size
    tails = np.array([row[3] for row in deform]) * size
    axis = tails - heads
    along = np.clip(((points[:, None, :] - heads[None]) * axis[None]).sum(2) / (axis * axis).sum(1)[None], 0.0, 1.0)
    distance = np.linalg.norm(points[:, None, :] - (heads[None] + along[:, :, None] * axis[None]), axis=2)
    # Distance is measured along the surface where it can be: a bone owns the largest connected patch of the vertices
    # nearest to it, and its distance to any other vertex is the way there over the mesh's edges. So a hand resting
    # by a knee, or one thigh against the other, takes nothing from the wrong bone. A loose piece no patch reaches
    # (a strand of mane) keeps the straight distance.
    edges = np.array([e.vertices[:] for e in weld.data.edges])
    lengths = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    around = [[] for _ in range(len(points))]
    for (i, j), d in zip(edges.tolist(), lengths.tolist()):
        around[i].append((j, d))
        around[j].append((i, d))
    nearest = distance.argmin(1)
    over = np.full_like(distance, np.inf)
    for k in range(len(deform)):
        mine = set(np.nonzero(nearest == k)[0].tolist()) or set(np.argsort(distance[:, k])[:20].tolist())
        best, left = [], set(mine)
        while left:
            stack, patch = [left.pop()], []
            while stack:
                v = stack.pop()
                patch.append(v)
                for n, _ in around[v]:
                    if n in left:
                        left.remove(n)
                        stack.append(n)
            if len(patch) > len(best):
                best = patch
        heap = [(float(distance[v, k]), v) for v in best]
        heapq.heapify(heap)
        cost = over[:, k]
        for d, v in heap:
            cost[v] = d
        while heap:
            d, v = heapq.heappop(heap)
            if d > cost[v]:
                continue
            for n, step in around[v]:
                if d + step < cost[n]:
                    cost[n] = d + step
                    heapq.heappush(heap, (d + step, n))
    loose = np.isinf(over).all(1)
    over[loose] = distance[loose]
    report['loose_vertices'] = int(loose.sum())
    weights = 1.0 / (over / spec['length_cm'] + 0.004) ** 4
    # a leg takes no skin from the other side of the body (the thighs touch, and distance alone cannot tell them apart)
    middle = spec.get('middle', 0.0) * size
    for k, row in enumerate(deform):
        if row[0].startswith(('Front', 'Hind', 'Leg')):
            left = (row[2][1] + row[3][1]) / 2 > spec.get('middle', 0.0)
            weights[(points[:, 1] < middle) if left else (points[:, 1] > middle), k] = 0.0
    weights /= weights.sum(1, keepdims=True)
    count = np.bincount(edges.ravel(), minlength=len(points)).astype(np.float64)[:, None]
    for _ in range(6):
        spread = np.zeros_like(weights)
        np.add.at(spread, edges[:, 0], weights[edges[:, 1]])
        np.add.at(spread, edges[:, 1], weights[edges[:, 0]])
        weights = np.where(count > 0, 0.5 * weights + 0.5 * spread / np.maximum(count, 1), weights)
    keep = np.argsort(-weights, axis=1)[:, :4]
    kept = np.take_along_axis(weights, keep, axis=1)
    kept[kept < 0.02] = 0.0
    kept /= kept.sum(1, keepdims=True)
    tree = KDTree(len(points))
    for k, point in enumerate(points):
        tree.insert(point, k)
    tree.balance()
    same = np.array([tree.find(point)[1] for point in real])
    keep, kept = keep[same], kept[same]
    bpy.data.objects.remove(weld)
    groups = [ob.vertex_groups.new(name=row[0]) for row in deform]
    for column in range(4):
        for bone_index in np.unique(keep[:, column]):
            rows = np.nonzero((keep[:, column] == bone_index) & (kept[:, column] > 0))[0]
            for value in np.unique(np.round(kept[rows, column], 2)):
                chosen = rows[np.round(kept[rows, column], 2) == value]
                if value > 0:
                    groups[bone_index].add([int(v) for v in chosen], float(value), 'ADD')
    select(ob)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    report['unweighted'] = sum(1 for v in ob.data.vertices if not v.groups)
    modifier = ob.modifiers.new('Armature', 'ARMATURE')
    modifier.object = arm
    ob.parent = arm

    select(arm, ob)
    bpy.ops.export_scene.fbx(filepath=str(OUT / 'Rigged' / ('SK_MN_%s.fbx' % name)), object_types={'ARMATURE', 'MESH'}, bake_anim=False, **FBX)

    rest = {bone.name: bone.matrix_local.to_3x3() for bone in armature.bones}
    scene.render.fps = FPS
    for bone in arm.pose.bones:
        bone.rotation_mode = 'QUATERNION'

    def set_pose(pose, frame=None):
        for bone in arm.pose.bones:
            if bone.name == 'Root':
                continue
            b = rest[bone.name]
            turn = pose.get(bone.name)
            q = (Matrix.Identity(3) if turn is None else b.transposed() @ rotation(turn) @ b).to_quaternion()
            if frame and bone.rotation_quaternion.dot(q) < 0:
                q.negate()
            bone.rotation_quaternion = q
            if frame is not None:
                bone.keyframe_insert('rotation_quaternion', frame=frame)

    if preview:
        shots(scene, arm, spec, name, set_pose, Path(preview))
    report['anims'] = {}
    for anim_name, (seconds, pose) in spec['anims'].items():
        frames = int(round(seconds * FPS))
        arm.animation_data_clear()
        arm.animation_data_create()
        arm.animation_data.action = bpy.data.actions.new(anim_name)
        for frame in range(frames + 1):
            set_pose(pose(frame / FPS), frame)
        scene.frame_start, scene.frame_end = 0, frames
        select(arm)
        bpy.ops.export_scene.fbx(filepath=str(OUT / 'Rigged' / ('A_MN_%s_%s.fbx' % (name, anim_name))), object_types={'ARMATURE'}, bake_anim=True,
                                 bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
                                 bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, bake_anim_step=1.0, **FBX)
        report['anims'][anim_name] = frames
    arm.animation_data_clear()
    set_pose({})

    # the light static copy: no skeleton, a tenth of the faces
    ob.modifiers.remove(ob.modifiers['Armature'])
    ob.parent = None
    ob.vertex_groups.clear()
    select(ob)
    light = ob.modifiers.new('Light', 'REMESH')   # a coarse closed hull: it is never drawn
    light.mode = 'VOXEL'
    light.voxel_size = spec['length_cm'] * 0.025
    bpy.ops.object.modifier_apply(modifier='Light')
    if not ob.data.materials:
        ob.data.materials.append(bpy.data.materials.new('Monster'))
    ob.name = 'SM_MN_' + name
    bpy.ops.export_scene.fbx(filepath=str(OUT / ('SM_MN_%s.fbx' % name)), object_types={'MESH'}, bake_anim=False, **FBX)
    report['static_faces'] = len(ob.data.polygons)
    return report


def shots(scene, arm, spec, name, set_pose, folder):
    """Side and three-quarter pictures of the rest pose, four moments of the walk and three of the attack."""
    folder.mkdir(parents=True, exist_ok=True)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'TEXTURE'
    scene.render.resolution_x, scene.render.resolution_y = 640, 560
    world = bpy.data.worlds.new('w')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.5, .52, .55, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = 1.6
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    cam.data.clip_end = 100000
    scene.collection.objects.link(cam)
    scene.camera = cam
    reach = spec['length_cm']
    walk, strike = spec['anims']['Swim'], spec['anims']['Strike']
    moments = [('rest', {})] + [('walk%d' % k, walk[1](walk[0] * k / 4)) for k in range(4)] + [('strike%d' % k, strike[1](t)) for k, t in enumerate((0.46, 0.66, 0.9))]
    for label, pose in moments:
        set_pose(pose)
        for view, yaw in (('side', -90), ('quarter', -40)):
            a = math.radians(yaw)
            cam.location = Vector((math.cos(a), math.sin(a), 0.12)) * reach * 1.9
            cam.rotation_euler = (-cam.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(folder / ('%s_%s_%s.png' % (name, label, view)))
            bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(sun)
    bpy.data.objects.remove(cam)


def main():
    import json
    words = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    preview = words.pop(words.index('--preview') + 1) if '--preview' in words else None
    words = [w for w in words if w != '--preview']
    out = {}
    for name in MONSTERS:
        if words and name not in words:
            continue
        out[name] = build(name, preview)
        print('BUILT %s %s' % (name, json.dumps(out[name])), flush=True)
    (OUT / 'report.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
