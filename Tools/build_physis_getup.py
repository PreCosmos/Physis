"""Author Physis's awakening animation: lying on her back, a gasping first breath, then getting up.

Starts from her retargeted idle (exported from Unreal as Saved/center/Physis_Idle.fbx with the body
skeleton) and keys whole-body poses on top of it. The torso pivots up from the ground; each limb is aimed
at world-space directions (elbows planted, hands pushing back, a knee down, a foot planted), and the
pelvis height is solved so the lowest contact sits on the ground. The standing tail reuses the idle
motion itself, with a slow look around.

Run: flatpak run org.blender.Blender -b --python Tools/build_physis_getup.py
Author, 2026-11-06: she rolls over to face down, pushes up with her hands while coming onto her knees, puts her
right foot forward and rises on the right leg, the left following. Rolling keeps the head's direction, so she now
lies with her head to the north (-Y here, the way she faces when standing): the lying poses are the earlier
ones turned 180 degrees and shifted (LIE_PLACE), and SEQ_Awakening's lying shots turn with her (see
physis_center_scenario.LIE_TURN; the saved SEQ_Awakening was turned once by Tools/trailer/awakening_turn_camera.py).

Author, 2026-11-05: "make the getting up a little more natural". The rise now flows through its poses
(unclamped curves instead of easing to a stop at every key), her right side leads the left, the left hand
pushes off the left knee, the fingers relax (flat only while planted) and she settles before the idle.

Writes Art/Characters/Physis/A_Physis_GetUp.fbx (20 s at 30 fps), imported by
`outfit_operation center:getup`. Timing matches SEQ_Awakening: eyes open and breath at 4.6 s, rise
10-16.1 s, look around after.

Author, 2026-11-08: "make Physis bring her leg forward twice as fast when she's getting up". The step from kneeling
up to the half kneel (the right foot planted in front) takes 9 frames instead of 18 (0.3 s); the poses after it keep
their pace and come 9 frames earlier (times on whole frames: a half frame rounds to even and skews the gaps), so she
stands at 16.1 s instead of 16.4 s. The half kneel eases (ease=True) instead of flowing through, so the quicker step
plants the foot instead of carrying it on up.
"""
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Saved/center/Physis_Idle.fbx'
OUT = ROOT / 'Art/Characters/Physis/A_Physis_GetUp.fbx'
FPS = 30
SECONDS = 20

# Blender frame of the character: she faces -Y when standing, her left is +X, up is +Z.
SPINE = ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05')
NECK = ('neck_01', 'neck_02', 'head')
ARM = {'l': ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'), 'r': ('clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r')}
LEG = {'l': ('thigh_l', 'calf_l', 'foot_l', 'ball_l'), 'r': ('thigh_r', 'calf_r', 'foot_r', 'ball_r')}


def side(vec, s):
    """Mirror an x component for the right side."""
    return Vector((vec[0] if s == 'l' else -vec[0], vec[1], vec[2])).normalized()


# Each pose: time (s), torso angle from the ground (0 lying, 90 upright, >90 leaning forward), extra spine
# arch (degrees, negative = chest up), head nod (positive = chin up toward the sky/forward), head turn,
# pelvis (y, clearance), and limb directions (upper, lower, end) in world space for the left side.
POSES = [
    dict(t=0.0, torso=0, arch=0, nod=0, turn=8, pelvis_y=.92, clear=.11,
         arm=((.35, -1, -.05), (.3, -1, .1), (.2, -1, 0)), leg=((.06, -1, -.03), (.03, -1, 0), (0, -.25, 1))),
    dict(t=4.3, torso=0, arch=0, nod=0, turn=8, pelvis_y=.92, clear=.11,
         arm=((.35, -1, -.05), (.3, -1, .1), (.2, -1, 0)), leg=((.06, -1, -.03), (.03, -1, 0), (0, -.25, 1))),
    # The gasp: chest heaves up, chin lifts, hands tense, one knee draws up a little.
    dict(t=4.5, torso=4, arch=-14, nod=18, turn=0, pelvis_y=.92, clear=.11,
         arm=((.45, -1, .05), (.35, -1, .35), (.2, -1, .3)), leg=((.06, -1, .08), (.03, -1, -.05), (0, -.3, 1))),
    dict(t=6.0, torso=2, arch=-5, nod=8, turn=-5, pelvis_y=.92, clear=.11,
         arm=((.38, -1, 0), (.32, -1, .15), (.2, -1, .05)), leg=((.06, -1, .02), (.03, -1, 0), (0, -.25, 1))),
    dict(t=8.0, torso=1, arch=-2, nod=12, turn=-14, pelvis_y=.92, clear=.11,
         arm=((.36, -1, -.03), (.3, -1, .12), (.2, -1, 0)), leg=((.06, -1, -.02), (.03, -1, 0), (0, -.25, 1))),
    dict(t=10.0, torso=1, arch=-3, nod=10, turn=0, pelvis_y=.92, clear=.11,
         arm=((.36, -1, -.03), (.3, -1, .12), (.2, -1, 0)), leg=((.06, -1, -.02), (.03, -1, 0), (0, -.25, 1))),
    # --- The rise, authored in the final frame (she ends at the origin facing -Y; left is +X when face down or up on
    # her feet, -X while lying face up). Body orientation is given by up (pelvis toward neck) and front (where the chest
    # faces); every limb direction is world space, per side.
    # Ready to roll: chin tucks, the head turns to her right, the left knee bends, the left arm reaches across.
    # The left arm sweeps low across her chest (elbow soft, hand opening toward the ground past her right side); palms down.
    dict(t=10.5, up=(0, -1, 0), front=(0, 0, 1), arch=0, nod=14, turn=24, pelvis_x=-.36, pelvis_y=.55, clear=.11, curl=10, palm=(0, 0, -1),
         arm=((.75, 0, .55), (.85, .15, -.3), (.75, .25, -.6)), arm_r=((.35, 1, -.05), (.3, 1, 0), (.25, 1, -.05)),
         leg=((-.08, .55, .83), (0, .55, -.83), (0, 1, -.2)), leg_r=((.06, 1, -.03), (.03, 1, 0), (0, .25, 1))),
    # On her right side: the left knee drops over in front, the left hand plants before her chest.
    # The top hand lands flat before her chest, fingers toward her head; the lower arm lies along the ground past her head.
    dict(t=11.2, up=(0, -1, 0), front=(1, 0, 0), arch=4, nod=6, turn=10, pelvis_x=-.18, pelvis_y=.55, clear=.1, curl=6, palm=(0, 0, -1),
         arm=((.65, -.1, -.75), (.15, -.15, -.98), (.5, -.8, -.1)), arm_r=((.35, -.9, -.1), (.2, -1, 0), (.15, -1, 0)),
         leg=((.75, .55, -.35), (.1, .95, -.3), (.1, 1, -.1)), leg_r=((.15, 1, -.05), (.1, 1, 0), (.4, .8, 0))),
    # Face down, hands beside her shoulders, elbows up: ready to push.
    dict(t=11.9, up=(0, -1, 0), front=(0, 0, -1), arch=-4, nod=-6, turn=0, pelvis_x=0, pelvis_y=.55, clear=.1, curl=5, palm=(0, 0, -1),
         arm=((.55, .65, .3), (.05, -.2, -.98), (.1, -1, -.05)), arm_r=((-.55, .65, .3), (-.05, -.2, -.98), (-.1, -1, -.05)),
         leg=((.1, 1, 0), (.03, 1, 0), (0, .45, -.89)), leg_r=((-.1, 1, 0), (-.03, 1, 0), (0, .45, -.89))),
    # Pushing up with her hands as the knees draw in under her hips.
    dict(t=12.6, up=(0, -.92, .4), front=(0, -.4, -.92), arch=0, nod=-10, turn=0, pelvis_x=0, pelvis_y=.48, clear=.05, curl=5, palm=(0, 0, -1),
         arm=((.25, .1, -.96), (.08, -.05, -1), (.08, -1, -.1)), arm_r=((-.25, .1, -.96), (-.08, -.05, -1), (-.08, -1, -.1)),
         leg=((.1, -.3, -.95), (0, 1, -.1), (0, .6, -.8)), leg_r=((-.1, -.25, -.96), (0, 1, -.1), (0, .6, -.8))),
    # On hands and knees.
    dict(t=13.2, up=(0, -1, .08), front=(0, -.08, -1), arch=6, nod=-12, turn=0, pelvis_x=0, pelvis_y=.42, clear=.02, curl=5, palm=(0, 0, -1),
         arm=((.12, 0, -1), (.05, 0, -1), (.05, -1, -.1)), arm_r=((-.12, 0, -1), (-.05, 0, -1), (-.05, -1, -.1)),
         leg=((.1, 0, -1), (0, 1, -.05), (0, .75, -.65)), leg_r=((-.1, 0, -1), (0, 1, -.05), (0, .75, -.65))),
    # Kneeling up: the hands push off and leave the ground, the hips rise over the knees.
    dict(t=13.75, up=(0, -.45, .89), front=(0, -.89, -.45), arch=0, nod=-8, turn=0, pelvis_x=0, pelvis_y=.46, clear=.02, curl=12,
         arm=((.2, -.55, -.81), (.1, -.6, -.8), (.05, -.8, -.6)), arm_r=((-.2, -.5, -.84), (-.1, -.55, -.83), (-.05, -.8, -.6)),
         leg=((.1, .15, -.98), (0, 1, -.05), (0, .75, -.65)), leg_r=((-.1, .15, -.98), (0, 1, -.05), (0, .75, -.65))),
    # Half kneel: the right foot planted in front, the left knee down, the right hand on the right knee.
    dict(t=14.04, ease=True, up=(0, -.05, 1), front=(0, -1, 0), arch=0, nod=-2, turn=0, pelvis_x=0, pelvis_y=.40, clear=.02, curl=14,
         arm=((.18, .05, -1), (.1, -.2, -.97), (.05, -.3, -.95)), arm_r=((-.25, -.45, -.86), (-.05, -.7, -.72), (0, -.8, -.6)),
         leg=((.08, .06, -1), (0, 1, -.06), (0, .6, -.8)), leg_r=((-.12, -1, -.05), (0, -.05, -1), (0, -1, -.12))),
    # Rising on the right leg, leaning over it, the right hand pressing the knee, the left leg trailing.
    dict(t=14.84, up=(0, -.22, .97), front=(0, -.97, -.22), arch=0, nod=0, turn=0, pelvis_x=0, pelvis_y=.12, clear=.02, curl=15,
         arm=((.15, -.4, -.9), (.08, -.6, -.8), (.05, -.6, -.8)), arm_r=((-.22, -.35, -.91), (-.05, -.35, -.94), (0, -.5, -.87)),
         leg=((.08, .55, -.83), (0, .85, -.53), (0, .4, -.9)), leg_r=((-.1, -.55, -.83), (0, .2, -.98), (0, -1, -.1))),
    # Up: the left foot arrives beside the right.
    dict(t=15.56, up=(0, -.04, 1), front=(0, -1, 0), arch=0, nod=2, turn=0, pelvis_x=0, pelvis_y=0, clear=.02, curl=18,
         arm=((.14, .02, -1), (.08, -.15, -1), (.04, -.2, -1)), arm_r=((-.14, .02, -1), (-.08, -.15, -1), (-.04, -.2, -1)),
         leg=((.06, -.06, -1), (.02, .04, -1), (0, -1, -.12)), leg_r=((-.06, .02, -1), (-.02, 0, -1), (0, -1, -.12))),
    # Balance: a small sway back past upright before the idle takes over.
    dict(t=15.84, up=(0, .03, 1), front=(0, -1, 0), arch=-2, nod=5, turn=0, pelvis_x=0, pelvis_y=0, clear=.02, curl=20,
         arm=((.13, .03, -1), (.09, -.08, -1), (.04, -.12, -1)), arm_r=((-.13, .03, -1), (-.09, -.08, -1), (-.04, -.12, -1)),
         leg=((.04, -.04, -1), (0, .02, -1), (0, -1, -.05)), leg_r=((-.04, -.04, -1), (0, .02, -1), (0, -1, -.05))),
]
RISE = (10.0, 16.1)      # keys strictly inside flow through (unclamped curves); the ends ease
LEAD = .2                # the right arm runs this fraction ahead toward the next pose (legs half as much)
LIE_PLACE = (180.0, -.36, 1.47)  # lying poses: turned about Z, then shifted (x, y), so she lies head north and rises at the origin
# Finger curl (degrees per joint): relaxed by default, tense at the gasp, flat while the hands are planted.
CURL = {4.5: 3}
STAND_AT = 16.1          # from here on she plays the idle, with the head turns below
PALM_SIGNS = {'l': 1, 'r': 1}
BLEND_IN = .7           # seconds from the last keyed pose into the idle
LOOKS = ((16.1, 0), (17.4, 32), (18.3, 32), (19.2, -30), (20.0, -10))


def chain_heads(arm, names):
    return [arm.matrix_world @ arm.pose.bones[n].head for n in names]


def set_world(arm, bone, matrix):
    bone.matrix = arm.matrix_world.inverted() @ matrix
    bpy.context.view_layer.update()


def rotate_about(arm, bone, quat, pivot):
    world = arm.matrix_world @ bone.matrix
    turn = Matrix.Translation(pivot) @ quat.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    set_world(arm, bone, turn @ world)


def aim(arm, bone_name, child_name, direction):
    bone = arm.pose.bones[bone_name]
    head = arm.matrix_world @ bone.head
    child = arm.matrix_world @ arm.pose.bones[child_name].head
    current = (child - head).normalized()
    want = Vector(direction).normalized()
    rotate_about(arm, bone, current.rotation_difference(want), head)


def aim_end(arm, bone_name, tip, direction):
    """For the last bone of a chain, aim toward its own child (ball, or middle finger base)."""
    aim(arm, bone_name, tip, direction)


def palm_normal(arm, s):
    """The palm's facing before calibration: finger direction crossed with index-to-pinky."""
    world = lambda name: arm.matrix_world @ arm.pose.bones[name].head
    fingers = (world('middle_metacarpal_' + s) - world('hand_' + s)).normalized()
    across = (world('pinky_metacarpal_' + s) - world('index_metacarpal_' + s)).normalized()
    return fingers, fingers.cross(across)


def palm_signs(arm):
    """In the idle her palms face her thighs, so that fixes which way each palm normal points."""
    inward = {'l': Vector((-1, 0, 0)), 'r': Vector((1, 0, 0))}
    return {s: (1 if palm_normal(arm, s)[1].dot(inward[s]) > 0 else -1) for s in 'lr'}


def palm_facing(arm, s, sign, direction):
    """Roll the hand about its own pointing axis so the palm faces direction (world)."""
    fingers, normal = palm_normal(arm, s)
    normal = normal * sign
    want = Vector(direction)
    want = want - fingers * want.dot(fingers)
    normal = normal - fingers * normal.dot(fingers)
    if want.length < 1e-4 or normal.length < 1e-4:
        return
    want.normalize()
    normal.normalize()
    angle = math.atan2(normal.cross(want).dot(fingers), normal.dot(want))
    hand = arm.pose.bones['hand_' + s]
    rotate_about(arm, hand, Quaternion(fingers, angle), arm.matrix_world @ hand.head)


def hinge_leg(arm, names, thigh_dir, calf_dir, foot_dir):
    """Pose a leg like a real one: the hip takes any rotation and twist, the knee only bends about
    its own hinge. Aiming each bone separately let the calf roll about its axis, so a knee could
    bend sideways; here the twist is solved at the hip so the knee bends in the desired plane."""
    thigh, calf, foot = (arm.pose.bones[n] for n in names[:3])
    want_t, want_c = Vector(thigh_dir).normalized(), Vector(calf_dir).normalized()
    hip = lambda: arm.matrix_world @ thigh.head
    knee = lambda: arm.matrix_world @ calf.head
    ankle = lambda: arm.matrix_world @ foot.head
    # 1. Thigh along the desired direction.
    rotate_about(arm, thigh, (knee() - hip()).normalized().rotation_difference(want_t), hip())
    # 2. Twist the thigh about itself until the shin lies in the plane of the desired shin.
    have_c = (ankle() - knee()).normalized()
    perp_have = have_c - want_t * have_c.dot(want_t)
    perp_want = want_c - want_t * want_c.dot(want_t)
    # A nearly straight leg has no defined knee plane: leave its twist alone or it can flip.
    if perp_have.length > .2 and perp_want.length > .2:
        twist = perp_have.normalized().rotation_difference(perp_want.normalized())
        # Keep the twist about the thigh axis only.
        angle = perp_have.normalized().angle(perp_want.normalized())
        sign = 1 if perp_have.cross(perp_want).dot(want_t) >= 0 else -1
        rotate_about(arm, thigh, Quaternion(want_t, sign * angle), hip())
    # 3. Bend the knee about its hinge, which is now perpendicular to that plane.
    have_c = (ankle() - knee()).normalized()
    axis = have_c.cross(want_c)
    if axis.length > 1e-5:
        rotate_about(arm, calf, Quaternion(axis.normalized(), have_c.angle(want_c)), knee())
    # 4. The foot.
    aim(arm, names[2], names[3], foot_dir)


def build_pose(arm, base, pose):
    # Start from the idle frame's pose.
    for name, basis in base.items():
        arm.pose.bones[name].matrix_basis = basis.copy()
    bpy.context.view_layer.update()
    signs = palm_signs(arm) if 'palm' in pose else None
    pelvis = arm.pose.bones['pelvis']
    pivot = arm.matrix_world @ pelvis.head
    if 'up' in pose:
        # Whole-body orientation from two directions: up (pelvis toward neck) and front (where the chest faces). The
        # idle stands with up +Z, front -Y and her left +X; left = up x front.
        up_w = Vector(pose['up']).normalized()
        front_w = Vector(pose['front'])
        front_w = (front_w - up_w * front_w.dot(up_w)).normalized()
        left_w = up_w.cross(front_w)
        frame = lambda l, f, u: Matrix((l, f, u)).transposed()
        turn_body = frame(left_w, front_w, up_w) @ frame(Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))).transposed()
        rotate_about(arm, pelvis, turn_body.to_quaternion(), pivot)
        lateral = left_w
    else:
        # Torso: pivot the whole body about X at the pelvis; at 90 she is upright.
        rotate_about(arm, pelvis, Quaternion((1, 0, 0), math.radians(pose['torso'] - 90)), pivot)
        lateral = Vector((1, 0, 0))
    # Spine arch and head nod, spread over the bones, about the body's own left-right axis.
    for name in SPINE[1:]:
        b = arm.pose.bones[name]
        rotate_about(arm, b, Quaternion(lateral, math.radians(-pose['arch'] / 5)), arm.matrix_world @ b.head)
    for name in NECK:
        b = arm.pose.bones[name]
        rotate_about(arm, b, Quaternion(lateral, math.radians(-pose['nod'] / 3)), arm.matrix_world @ b.head)
    up = (arm.matrix_world @ arm.pose.bones['head'].head - arm.matrix_world @ arm.pose.bones['neck_01'].head).normalized()
    for name in NECK[1:]:
        b = arm.pose.bones[name]
        rotate_about(arm, b, Quaternion(up, math.radians(pose['turn'] / 2)), arm.matrix_world @ b.head)
    # Spine twist (about the body's own up) and lean (about its forward), spread over the spine.
    if pose.get('twist') or pose.get('lean'):
        body_up = (arm.matrix_world @ arm.pose.bones['neck_01'].head - arm.matrix_world @ pelvis.head).normalized()
        body_fwd = body_up.cross(lateral).normalized()
        for name in SPINE[1:]:
            b = arm.pose.bones[name]
            rotate_about(arm, b, Quaternion(body_up, math.radians(pose.get('twist', 0) / 5)) @ Quaternion(body_fwd, math.radians(pose.get('lean', 0) / 5)),
                         arm.matrix_world @ b.head)
    # Limbs (the right arm may have its own world directions: arm_r).
    for s, names in ARM.items():
        if s == 'r' and 'arm_r' in pose:
            upper, lower, end = pose['arm_r']
            place = lambda v: Vector(v).normalized()
        else:
            upper, lower, end = pose['arm']
            place = lambda v, s=s: side(v, s)
        aim(arm, names[1], names[2], place(upper))
        aim(arm, names[2], names[3], place(lower))
        aim_end(arm, names[3], 'middle_metacarpal_' + s, place(end))
        # Optional palm facing (world direction for the left hand, mirrored for the right).
        if signs:
            palm_facing(arm, s, signs[s], side(pose['palm'], s))
    for s, names in LEG.items():
        upper, lower, end = pose.get('leg_r' if s == 'r' and 'leg_r' in pose else 'leg', pose['leg'])
        if s == 'r' and 'leg_r' in pose:
            mirror = lambda v: Vector(v).normalized()
        else:
            mirror = lambda v, s=s: side(v, s)
        hinge_leg(arm, names, mirror(upper), mirror(lower), mirror(end))
    # Fingers: each joint curls toward the palm (the palm's facing is calibrated on the idle's first frame).
    curl = pose.get('curl', 16)
    for s in 'lr':
        fingers, normal = palm_normal(arm, s)
        axis = fingers.cross(normal * PALM_SIGNS[s]).normalized()
        for finger in ('index', 'middle', 'ring', 'pinky'):
            for joint in ('01', '02', '03'):
                name = '%s_%s_%s' % (finger, joint, s)
                if name in arm.pose.bones:
                    b = arm.pose.bones[name]
                    rotate_about(arm, b, Quaternion(axis, math.radians(curl * (1.0 if joint == '01' else .8))), arm.matrix_world @ b.head)
    # Place the pelvis: in y as given, and in z so the lowest contact point rests on the ground.
    contacts = ['pelvis', 'spine_03', 'spine_05', 'head', 'hand_l', 'hand_r', 'lowerarm_l', 'lowerarm_r', 'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r']
    low = min((arm.matrix_world @ arm.pose.bones[n].head).z - (pose['clear'] if n in ('pelvis', 'spine_03', 'spine_05', 'head') else .045) for n in contacts)
    here = arm.matrix_world @ pelvis.head
    shift = Vector((pose['pelvis_x'] - here.x if 'pelvis_x' in pose else 0, pose['pelvis_y'] - here.y, -low))
    set_world(arm, pelvis, Matrix.Translation(shift) @ (arm.matrix_world @ pelvis.matrix))
    # The lying poses were authored head south; turned and shifted (LIE_PLACE) she lies head north and rises in place.
    if 'up' not in pose:
        spin, dx, dy = LIE_PLACE
        place = Matrix.Translation((dx, dy, 0)) @ Quaternion((0, 0, 1), math.radians(spin)).to_matrix().to_4x4()
        set_world(arm, pelvis, place @ (arm.matrix_world @ pelvis.matrix))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SOURCE))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    idle = arm.animation_data.action
    scene = bpy.context.scene
    scene.render.fps = FPS
    bones = [b.name for b in arm.pose.bones]
    # Sample the idle at the frames we need, as local bases.
    idle_len = int(idle.frame_range[1])

    def idle_basis(frame):
        scene.frame_set(1 + (frame - 1) % (idle_len - 1))
        return {n: arm.pose.bones[n].matrix_basis.copy() for n in bones}
    global PALM_SIGNS
    idle_basis(1)
    bpy.context.view_layer.update()
    PALM_SIGNS = palm_signs(arm)
    # The right side leads: its arm (and, half as much, its leg) runs part of the way toward the next pose.
    blend = lambda a, b, k: tuple(tuple(x * (1 - k) + y * k for x, y in zip(u, v)) for u, v in zip(a, b))
    right = lambda dirs: tuple((-d[0], d[1], d[2]) for d in dirs)
    for here, there in zip(POSES, POSES[1:]):
        if RISE[0] < here['t'] < RISE[1]:
            here.setdefault('arm_r', blend(right(here['arm']), there.get('arm_r', right(there['arm'])), LEAD))
            here.setdefault('leg_r', blend(right(here['leg']), there.get('leg_r', right(there['leg'])), LEAD / 2))
        if here['t'] in CURL:
            here.setdefault('curl', CURL[here['t']])
    keyed = []
    for pose in POSES:
        frame = 1 + round(pose['t'] * FPS)
        keyed.append((frame, pose, idle_basis(frame)))
    stand = [(1 + round(t * FPS), turn, None) for t, turn in LOOKS]
    # Sample the idle for the standing tail now, while the idle is still the active action.
    tail = {frame: idle_basis(frame) for frame in range(1 + round(STAND_AT * FPS), 1 + SECONDS * FPS + 1, 4)}
    # A fresh action holds the result.
    action = bpy.data.actions.new('A_Physis_GetUp')
    arm.animation_data.action = action
    for b in arm.pose.bones:
        b.rotation_mode = 'QUATERNION'
    previous = {}

    def key_all(frame):
        for b in arm.pose.bones:
            q = b.rotation_quaternion.copy()
            last = previous.get(b.name)
            if last is not None and q.dot(last) < 0:
                q.negate()
                b.rotation_quaternion = q
            previous[b.name] = q.copy()
            b.keyframe_insert('location', frame=frame)
            b.keyframe_insert('rotation_quaternion', frame=frame)

    for frame, pose, base in keyed:
        build_pose(arm, base, pose)
        # Report each knee: its bend toward the toes (>0 is right) and its sideways lean.
        report = []
        for s_, names in LEG.items():
            w = lambda n: arm.matrix_world @ arm.pose.bones[n].head
            hip, knee, ankle, ball = w(names[0]), w(names[1]), w(names[2]), w(names[3])
            mid = (hip + ankle) / 2
            toes = (ball - ankle)
            toes.z = 0
            off = knee - mid
            report.append('%s fwd %.2f side %.2f' % (s_, off.dot(toes.normalized()) if toes.length > 1e-4 else 0, off.x if s_ == 'l' else -off.x))
        print('KNEE t=%.1f' % pose['t'], ' | '.join(report), flush=True)
        key_all(frame)
    # The last keyed pose, blended into the idle below (a hard switch snapped her feet and arms ~40 deg in a frame).
    settle = {n: arm.pose.bones[n].matrix_basis.copy() for n in bones}
    # The rise flows: keys strictly inside it get unclamped curves, so the body moves through them instead of
    # easing to a stop at each pose (clamped handles flatten every key).
    # A pose marked ease keeps clamped handles: the faster step to the half kneel flowed through its key and kicked
    # the planted right foot up about 50 cm (review, 2026-11-08).
    inside = {1 + round(p['t'] * FPS) for p in POSES if RISE[0] < p['t'] < RISE[1] and not p.get('ease')}
    curves = list(action.fcurves) if hasattr(action, 'fcurves') else [fc for layer in action.layers for strip in layer.strips
                                                                          for bag in strip.channelbags for fc in bag.fcurves]  # Blender 5: layered actions
    for fc in curves:
        for kp in fc.keyframe_points:
            if round(kp.co[0]) in inside:
                kp.handle_left_type = kp.handle_right_type = 'AUTO'
        fc.update()
    # Standing: the idle itself, every 4th frame, with the head turn layered on.
    turns = {f: t for f, t, _ in stand}
    first = min(tail)
    for frame, base in tail.items():
        # Evaluate the new action at this frame first: the curve edits above tag it, and the next scene update would
        # otherwise re-evaluate it at a stale frame (mid-lie) on top of the pose set below.
        scene.frame_set(frame)
        w = min(1.0, (frame - first) / (BLEND_IN * FPS))
        w = w * w * (3 - 2 * w)
        for n, basis in base.items():
            if w < 1.0:
                a = settle[n]
                arm.pose.bones[n].matrix_basis = Matrix.LocRotScale(a.to_translation().lerp(basis.to_translation(), w),
                                                                    a.to_quaternion().slerp(basis.to_quaternion(), w), Vector((1, 1, 1)))
            else:
                arm.pose.bones[n].matrix_basis = basis
        bpy.context.view_layer.update()
        # Interpolated head turn.
        times = sorted(turns)
        turn = 0.0
        for a, b in zip(times, times[1:]):
            if a <= frame <= b:
                k = (frame - a) / (b - a)
                k = k * k * (3 - 2 * k)
                turn = turns[a] * (1 - k) + turns[b] * k
        up = Vector((0, 0, 1))
        for name in NECK[1:]:
            pb = arm.pose.bones[name]
            rotate_about(arm, pb, Quaternion(up, math.radians(turn / 2)), arm.matrix_world @ pb.head)
        key_all(frame)
    # Motion check: no bone may turn faster than a person can, frame to frame (a flip shows as a spike).
    worst = []
    for b in arm.pose.bones:
        if not b.name.startswith(('pelvis', 'spine', 'neck', 'head', 'thigh', 'calf', 'foot', 'clavicle', 'upperarm', 'lowerarm', 'hand_')):
            continue
        last = None
        for frame in range(1, 1 + SECONDS * FPS + 1):
            scene.frame_set(frame)
            m = (arm.matrix_world @ b.matrix).to_quaternion()
            if last is not None:
                a = math.degrees(m.rotation_difference(last).angle) % 360
                step = min(a, 360 - a)
                worst.append((step, b.name, frame))
            last = m
    worst.sort(reverse=True)
    seen, top = set(), []
    for a, n, f in worst:
        key = (n.split('_')[0] + n[-2:], f // 15)
        if key not in seen:
            seen.add(key)
            top.append((round(a, 1), n, round(f / FPS, 2)))
        if len(top) == 10:
            break
    print('SPIN worst steps (deg/frame, bone, seconds):', top, flush=True)
    scene.frame_start, scene.frame_end = 1, 1 + SECONDS * FPS
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=str(OUT), use_selection=True, object_types={'ARMATURE'}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_step=1, bake_anim_simplify_factor=0.0,
                             apply_unit_scale=True, primary_bone_axis='Y', secondary_bone_axis='X')
    print('GETUP', OUT, len(keyed), 'poses')


if __name__ == '__main__':
    main()
