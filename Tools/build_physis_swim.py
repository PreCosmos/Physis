"""Author Physis's swimming loops on her body skeleton: treading water and a breaststroke.

Uses the posing tools of Tools/build_physis_getup.py (torso pivot, hinge legs, aimed arms) on top of
her idle. Both clips loop seamlessly (last key equals the first). Heights are the pelvis above the clip's
root (her capsule's bottom). With buoyancy 1.3 Unreal floats the capsule about 77% submerged, so the root
rides about 1.37 m below the water: treading keeps the head and neck out, and the stroke holds the pelvis
just under the surface with the upper body tilted up, face clear of the water.

Run: flatpak run org.blender.Blender -b --python Tools/build_physis_swim.py
Writes Art/Characters/Physis/A_Physis_SwimTread.fbx and A_Physis_SwimStroke.fbx.
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_physis_getup as rig  # noqa: E402

FPS = 30
OUT = rig.ROOT / 'Art/Characters/Physis'

# Treading water: upright, slightly forward. Directions are (x out from her side, y forward when negative,
# z up). The hands scull in small in-and-out sweeps in front of the chest just under the surface, elbows bent
# and low, palms facing outward; they never pass behind her. The legs run a compact eggbeater under her: knees about hip-width
# apart, thighs a little forward, lower legs circling, the two legs half a cycle apart. A sweep takes 0.6 s,
# a whole loop 2.4 s (at 0.4 s per sweep it looked hurried).
PALM_OUT = (.85, -.1, -.5)  # palms face outward and a little down
SCULL_IN = ((.5, -.35, -.79), (-.3, -.92, .25), (-.4, -.9, .1))
SCULL_OUT = ((.55, -.3, -.78), (.45, -.85, .2), (.55, -.82, .05))
KICK_FRONT = ((.12, -.45, -.88), (.15, .4, -.9), (0, -.55, -.83))
KICK_DOWN = ((.08, -.3, -.95), (.05, .12, -.99), (0, -.8, -.6))
mirror = lambda leg: tuple((-x, y, z) for x, y, z in leg)
TREAD = (
    dict(t=0.0, torso=96, arch=0, nod=10, turn=0, height=.95, palm=PALM_OUT, arm=SCULL_IN, leg=KICK_FRONT, leg_r=mirror(KICK_DOWN)),
    dict(t=.6, torso=95, arch=2, nod=12, turn=0, height=.97, palm=PALM_OUT, arm=SCULL_OUT, leg=KICK_DOWN, leg_r=mirror(KICK_FRONT)),
    dict(t=1.2, torso=96, arch=0, nod=10, turn=0, height=.95, palm=PALM_OUT, arm=SCULL_IN, leg=KICK_FRONT, leg_r=mirror(KICK_DOWN)),
    dict(t=1.8, torso=95, arch=2, nod=12, turn=0, height=.97, palm=PALM_OUT, arm=SCULL_OUT, leg=KICK_DOWN, leg_r=mirror(KICK_FRONT)),
    dict(t=2.4, torso=96, arch=0, nod=10, turn=0, height=.95, palm=PALM_OUT, arm=SCULL_IN, leg=KICK_FRONT, leg_r=mirror(KICK_DOWN)),
)

# Breaststroke, one cycle: glide, pull, breathe and recover, kick, glide. The pelvis sits just under the
# surface; the upper body is tilted 25-35 degrees up from face-down (torso 180; flat, her head hangs 8 cm
# below her hips) and the head lifted, so her shoulders ride at the surface and her face stays out of the
# water, highest on the breath. (At 1.5 m with a flat torso she swam on top of the water.)
STROKE = (
    dict(t=0.0, torso=155, arch=-6, nod=24, turn=0, height=1.24,
         arm=((.08, -1, .02), (.05, -1, .02), (.02, -1, 0)), leg=((.06, 1, -.05), (.03, 1, 0), (0, 1, .2))),
    dict(t=.35, torso=150, arch=-10, nod=28, turn=0, height=1.25,
         arm=((.75, -.45, -.5), (.55, -.2, -.8), (.3, -.4, -.8)), leg=((.06, 1, -.05), (.03, 1, 0), (0, 1, .2))),
    dict(t=.65, torso=145, arch=-16, nod=32, turn=0, height=1.26,
         arm=((.55, .35, -.75), (-.35, -.85, -.2), (-.2, -.9, .1)), leg=((.28, .55, -.78), (.1, -.25, .95), (0, -.2, 1))),
    dict(t=.9, torso=158, arch=-8, nod=22, turn=0, height=1.24,
         arm=((.12, -1, .05), (.08, -1, .05), (.04, -1, 0)), leg=((.45, 1, -.15), (.35, 1, .05), (.2, 1, -.1))),
    dict(t=1.4, torso=155, arch=-6, nod=24, turn=0, height=1.24,
         arm=((.08, -1, .02), (.05, -1, .02), (.02, -1, 0)), leg=((.06, 1, -.05), (.03, 1, 0), (0, 1, .2))),
)


def build(name, poses):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(rig.SOURCE))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_set(1)
    base = {b.name: b.matrix_basis.copy() for b in arm.pose.bones}
    arm.animation_data.action = bpy.data.actions.new(name)
    for b in arm.pose.bones:
        b.rotation_mode = 'QUATERNION'
    previous = {}
    for pose in poses:
        frame = 1 + round(pose['t'] * FPS)
        spec = dict(pose, pelvis_y=0.0, clear=0.0)
        rig.build_pose(arm, base, spec)
        # Hold the pelvis at swimming height instead of resting on the ground.
        pelvis = arm.pose.bones['pelvis']
        here = arm.matrix_world @ pelvis.head
        shift = rig.Vector((-here.x, -here.y, pose['height'] - here.z))
        rig.set_world(arm, pelvis, rig.Matrix.Translation(shift) @ (arm.matrix_world @ pelvis.matrix))
        for b in arm.pose.bones:
            q = b.rotation_quaternion.copy()
            if b.name in previous and q.dot(previous[b.name]) < 0:
                q.negate()
                b.rotation_quaternion = q
            previous[b.name] = q.copy()
            b.keyframe_insert('location', frame=frame)
            b.keyframe_insert('rotation_quaternion', frame=frame)
    scene.frame_start, scene.frame_end = 1, 1 + round(poses[-1]['t'] * FPS)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = OUT / (name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_step=1, bake_anim_simplify_factor=0.0,
                             apply_unit_scale=True, primary_bone_axis='Y', secondary_bone_axis='X')
    print('SWIM', path, flush=True)


build('A_Physis_SwimTread', TREAD)
build('A_Physis_SwimStroke', STROKE)
