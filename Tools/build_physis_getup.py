"""Author Physis's awakening animation: lying on her back, a gasping first breath, then getting up.

Starts from her retargeted idle (exported from Unreal as Saved/center/Physis_Idle.fbx with the body
skeleton) and poses the whole body on top of it. The standing tail reuses the idle motion itself, with a
slow look around.

Run: blender -b --python Tools/build_physis_getup.py            (writes the clip Unreal imports)
     blender -b --python Tools/build_physis_getup.py -- <other.fbx>   (a trial build somewhere else)

Writes Art/Characters/Physis/A_Physis_GetUp.fbx (20 s at 30 fps), imported by
`outfit_operation center:getup`. Timing matches SEQ_Awakening: eyes open and breath at 4.6 s, rise
10-16.1 s, look around after.

Author, 2026-11-15: "fix the getting up animation ... make it look as natural as possible". Measured on the
clip of 2026-11-08: lying face down she hung 20 cm above the ground on her hands with her feet 30 cm up; her
knees hovered 15 cm high the whole time she knelt and slid 60 cm forward at 1.5 m/s; arms and feet passed up
to 14 cm under the ground; both feet shuffled 15 cm without lifting as the idle took over. The cause was the
method: a few whole-body poses, each limb aimed at a direction, bone rotations interpolated between them, so
nothing was ever held where it touched the ground. The rise (10-16.1 s) is now solved on every frame:
  - the body (pelvis place, facing, spine, head) and each limb have their own keys (rise_keys);
  - a planted hand, knee or foot is a place in the world, reached by two-bone IK and held exactly while two
    keys in a row name the same place; a moving one travels through its keys' places (a step has an arc);
  - free limbs are still aimed at directions, but no joint may pass under the ground;
  - while she lies and rolls the body rests on the ground (hips, chest, shoulders, head); while she kneels
    the hips stay a thigh's length from the planted knees.
The moves are the same ones in the same time (roll to face down, push up onto her knees, right foot forward
in 9 frames, rise on the right leg), with these changes: the knees stay where they were when she pushes up
(her hips go up and back over them instead of the knees sliding in under her), so she stands up 40 cm behind
the origin and walks the last of it: the left foot steps through, the right closes, and she arrives in the
idle's own stance (the idle stands with the left foot ahead and the body turned 22 degrees: the rise keeps
her hips square until those steps). The right arm no longer sweeps round over her head as she rolls: it folds
at her side and she rolls over it. Elbows bend about their own hinge like the knees. The lying part (0-10 s)
is untouched. The clip and script before this are Saved/center/A_Physis_GetUp_v3.fbx and
build_physis_getup_v3.py.

Author, 2026-11-08: "make Physis bring her leg forward twice as fast when she's getting up". The step from kneeling
up to the half kneel (the right foot planted in front) takes 9 frames instead of 18 (0.3 s), 13.75-14.04 s.

Author, 2026-11-06: she rolls over to face down, pushes up with her hands while coming onto her knees, puts her
right foot forward and rises on the right leg, the left following. Rolling keeps the head's direction, so she now
lies with her head to the north (-Y here, the way she faces when standing): the lying poses are the earlier
ones turned 180 degrees and shifted (LIE_PLACE), and SEQ_Awakening's lying shots turn with her (see
physis_center_scenario.LIE_TURN; the saved SEQ_Awakening was turned once by Tools/trailer/awakening_turn_camera.py).

Author, 2026-11-05: "make the getting up a little more natural". The rise flows through its poses, her sides
are not mirror images, the fingers relax (flat only while planted) and she settles before the idle.
"""
import math
import sys
from bisect import bisect_right
from pathlib import Path

import bpy
import numpy as np
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


# ---------------------------------------------------------------- lying (0-10 s), as it was
# Each pose: time (s), torso angle from the ground (0 lying, 90 upright), extra spine arch and head nod (degrees,
# positive = bent back: chest out, chin up), head turn, pelvis (y, clearance), and limb directions (upper, lower,
# end) for the left side, mirrored for the right. Authored head south, then turned and shifted by LIE_PLACE.
LIE_POSES = [
    dict(t=0.0, torso=0, arch=0, nod=0, turn=8, pelvis_y=.92, clear=.11,
         arm=((.35, -1, -.05), (.3, -1, .1), (.2, -1, 0)), leg=((.06, -1, -.03), (.03, -1, 0), (0, -.25, 1))),
    dict(t=4.3, torso=0, arch=0, nod=0, turn=8, pelvis_y=.92, clear=.11,
         arm=((.35, -1, -.05), (.3, -1, .1), (.2, -1, 0)), leg=((.06, -1, -.03), (.03, -1, 0), (0, -.25, 1))),
    # The gasp: chest heaves up, chin lifts, hands tense, one knee draws up a little.
    dict(t=4.5, torso=4, arch=-14, nod=18, turn=0, pelvis_y=.92, clear=.11, curl=3,
         arm=((.45, -1, .05), (.35, -1, .35), (.2, -1, .3)), leg=((.06, -1, .08), (.03, -1, -.05), (0, -.3, 1))),
    dict(t=6.0, torso=2, arch=-5, nod=8, turn=-5, pelvis_y=.92, clear=.11,
         arm=((.38, -1, 0), (.32, -1, .15), (.2, -1, .05)), leg=((.06, -1, .02), (.03, -1, 0), (0, -.25, 1))),
    dict(t=8.0, torso=1, arch=-2, nod=12, turn=-14, pelvis_y=.92, clear=.11,
         arm=((.36, -1, -.03), (.3, -1, .12), (.2, -1, 0)), leg=((.06, -1, -.02), (.03, -1, 0), (0, -.25, 1))),
    dict(t=10.0, torso=1, arch=-3, nod=10, turn=0, pelvis_y=.92, clear=.11,
         arm=((.36, -1, -.03), (.3, -1, .12), (.2, -1, 0)), leg=((.06, -1, -.02), (.03, -1, 0), (0, -.25, 1))),
]
LIE_PLACE = (180.0, -.36, 1.47)  # lying poses: turned about Z, then shifted (x, y), so she lies head north
RISE_FROM = 10.0         # the last lying pose is the rise's first key
STAND_AT = 16.1          # from here on she plays the idle, with the head turns below
PALM_SIGNS = {'l': 1, 'r': 1}
BLEND_IN = .7            # seconds from the last solved frame into the idle (they are the same pose now)
LOOKS = ((16.1, 0), (17.4, 32), (18.3, 32), (19.2, -30), (20.0, -10))

# Ground contact sizes (m): how far each joint's centre stays above the ground.
R_ELBOW, R_WRIST, R_KNUCKLE = .04, .03, .02
R_KNEE, R_ANKLE, R_BALL = .055, .05, .02
HAND_REACH = .10         # wrist to knuckles, for keeping the hand above the ground


def head_of(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].head


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


def hinge_chain(arm, names, tip, upper_dir, lower_dir, end_dir, weight=1.0, hard=False):
    """Pose a limb like a real one: the ball joint (hip, shoulder) takes any rotation and twist, the hinge (knee,
    elbow) only bends about its own axis. Aiming each bone separately lets the lower bone roll about itself, so a
    knee or elbow could bend sideways; here the twist is solved at the ball joint so the hinge bends in the
    wanted plane. A nearly straight limb has no bending plane: its twist fades out (hard: is left alone below a
    threshold, as the lying poses were built)."""
    upper, lower, end = (arm.pose.bones[n] for n in names)
    want_u, want_l = Vector(upper_dir).normalized(), Vector(lower_dir).normalized()
    root = lambda: arm.matrix_world @ upper.head
    mid = lambda: arm.matrix_world @ lower.head
    far = lambda: arm.matrix_world @ end.head
    rotate_about(arm, upper, (mid() - root()).normalized().rotation_difference(want_u), root())
    have_l = (far() - mid()).normalized()
    perp_have = have_l - want_u * have_l.dot(want_u)
    perp_want = want_l - want_u * want_l.dot(want_u)
    bent = min(perp_have.length, perp_want.length)
    if hard:
        fade = 1.0 if bent > .2 else 0.0
    else:
        fade = min(max((bent - .06) / .2, 0.0), 1.0)
        fade = fade * fade * (3 - 2 * fade)
    if fade * weight > 0:
        angle = perp_have.normalized().angle(perp_want.normalized())
        sign = 1 if perp_have.cross(perp_want).dot(want_u) >= 0 else -1
        rotate_about(arm, upper, Quaternion(want_u, sign * angle * fade * weight), root())
    have_l = (far() - mid()).normalized()
    axis = have_l.cross(want_l)
    if axis.length > 1e-5:
        rotate_about(arm, lower, Quaternion(axis.normalized(), have_l.angle(want_l)), mid())
    aim(arm, names[2], tip, end_dir)


def curl_fingers(arm, curls):
    """Each finger joint curls toward the palm (the palm's facing is calibrated on the idle's first frame)."""
    for s in 'lr':
        fingers, normal = palm_normal(arm, s)
        axis = fingers.cross(normal * PALM_SIGNS[s]).normalized()
        for finger in ('index', 'middle', 'ring', 'pinky'):
            for joint in ('01', '02', '03'):
                name = '%s_%s_%s' % (finger, joint, s)
                if name in arm.pose.bones:
                    b = arm.pose.bones[name]
                    rotate_about(arm, b, Quaternion(axis, math.radians(curls[s] * (1.0 if joint == '01' else .8))), arm.matrix_world @ b.head)


def bend_spine(arm, lateral, arch, nod, turn):
    """Spine arch and head nod, spread over the bones, about the body's own left-right axis; then the head turn."""
    for name in SPINE[1:]:
        b = arm.pose.bones[name]
        rotate_about(arm, b, Quaternion(lateral, math.radians(-arch / 5)), arm.matrix_world @ b.head)
    for name in NECK:
        b = arm.pose.bones[name]
        rotate_about(arm, b, Quaternion(lateral, math.radians(-nod / 3)), arm.matrix_world @ b.head)
    up = (head_of(arm, 'head') - head_of(arm, 'neck_01')).normalized()
    for name in NECK[1:]:
        b = arm.pose.bones[name]
        rotate_about(arm, b, Quaternion(up, math.radians(turn / 2)), arm.matrix_world @ b.head)


def set_base(arm, base):
    for name, basis in base.items():
        arm.pose.bones[name].matrix_basis = basis.copy()
    bpy.context.view_layer.update()


def build_lying_pose(arm, base, pose):
    set_base(arm, base)
    pelvis = arm.pose.bones['pelvis']
    pivot = arm.matrix_world @ pelvis.head
    # Torso: pivot the whole body about X at the pelvis; at 90 she is upright.
    rotate_about(arm, pelvis, Quaternion((1, 0, 0), math.radians(pose['torso'] - 90)), pivot)
    bend_spine(arm, Vector((1, 0, 0)), pose['arch'], pose['nod'], pose['turn'])
    for s, names in ARM.items():
        upper, lower, end = pose['arm']
        aim(arm, names[1], names[2], side(upper, s))
        aim(arm, names[2], names[3], side(lower, s))
        aim(arm, names[3], 'middle_metacarpal_' + s, side(end, s))
    for s, names in LEG.items():
        upper, lower, end = pose['leg']
        hinge_chain(arm, names[:3], names[3], side(upper, s), side(lower, s), side(end, s), hard=True)
    curl = pose.get('curl', 16)
    curl_fingers(arm, {'l': curl, 'r': curl})
    # Place the pelvis: in y as given, and in z so the lowest contact point rests on the ground.
    contacts = ['pelvis', 'spine_03', 'spine_05', 'head', 'hand_l', 'hand_r', 'lowerarm_l', 'lowerarm_r', 'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r']
    low = min(head_of(arm, n).z - (pose['clear'] if n in ('pelvis', 'spine_03', 'spine_05', 'head') else .045) for n in contacts)
    here = arm.matrix_world @ pelvis.head
    set_world(arm, pelvis, Matrix.Translation(Vector((0, pose['pelvis_y'] - here.y, -low))) @ (arm.matrix_world @ pelvis.matrix))
    spin, dx, dy = LIE_PLACE
    place = Matrix.Translation((dx, dy, 0)) @ Quaternion((0, 0, 1), math.radians(spin)).to_matrix().to_4x4()
    set_world(arm, pelvis, place @ (arm.matrix_world @ pelvis.matrix))


# ---------------------------------------------------------------- the rise (10-16.1 s), solved on every frame

def pchip(ts, vs, t):
    """Shape-preserving cubic through the keys: it flows through a run of keys that keeps going the same way and
    is flat where a value turns round or holds, so nothing overshoots (a planted place stays exactly planted).
    Starts and ends at rest."""
    if t <= ts[0]:
        return vs[0].copy()
    if t >= ts[-1]:
        return vs[-1].copy()
    n = len(ts)
    h = np.diff(np.asarray(ts, float))
    delta = (vs[1:] - vs[:-1]) / h[:, None]
    m = np.zeros_like(vs)
    for k in range(1, n - 1):
        both = delta[k - 1] * delta[k] > 0
        w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
        with np.errstate(divide='ignore', invalid='ignore'):
            m[k] = np.where(both, (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k]), 0.0)
    i = min(bisect_right(ts, t) - 1, n - 2)
    x = (t - ts[i]) / h[i]
    return ((2 * x ** 3 - 3 * x ** 2 + 1) * vs[i] + (x ** 3 - 2 * x ** 2 + x) * h[i] * m[i]
            + (-2 * x ** 3 + 3 * x ** 2) * vs[i + 1] + (x ** 3 - x ** 2) * h[i] * m[i + 1])


def unit(v):
    v = Vector(v)
    return v.normalized() if v.length > 1e-9 else Vector((0, 0, 1))


def keep_above(root, dirs, lengths, radii):
    """Walk down a chain of directions from root; wherever a joint would sink under the ground, lift that bone's
    direction just enough to rest the joint on it."""
    p, out = Vector(root), []
    for d, length, r in zip(dirs, lengths, radii):
        d = unit(d)
        need = min((r - p.z) / length, .999)
        if d.z < need:
            flat = Vector((d.x, d.y, 0))
            flat = flat.normalized() if flat.length > 1e-6 else Vector((0, 1, 0))
            d = Vector((flat.x * math.sqrt(1 - need * need), flat.y * math.sqrt(1 - need * need), need))
        out.append(d)
        p = p + d * length
    return out


MISSES = []


def two_bone(root, target, l1, l2, pole, tag):
    """Where the middle joint goes so the end reaches target; pole is the way the knee or elbow points."""
    v = Vector(target) - root
    d = v.length
    reach = (l1 + l2) * .999
    if d > reach:
        MISSES.append((tag, round((d - reach) * 100, 1)))
        d = reach
    d = max(d, abs(l1 - l2) + 1e-3)
    u = v.normalized()
    a = (d * d + l1 * l1 - l2 * l2) / (2 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = Vector(pole)
    p = p - u * p.dot(u)
    p = p.normalized() if p.length > 1e-5 else u.orthogonal().normalized()
    joint = root + u * a + p * h
    end = root + u * d
    return (joint - root).normalized(), (end - joint).normalized(), end


def facing(up, front, yaw=0.0):
    """The whole-body turn from the idle's stance: up (pelvis toward neck), front (where the chest faces), then
    yaw degrees about her own up (the idle stands turned; SQUARE undoes it)."""
    up_w = Vector(up).normalized()
    front_w = Vector(front)
    front_w = (front_w - up_w * front_w.dot(up_w)).normalized()
    left_w = up_w.cross(front_w)
    frame = lambda l, f, u: Matrix((l, f, u)).transposed()
    turn = frame(left_w, front_w, up_w) @ frame(Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))).transposed()
    return turn.to_quaternion() @ Quaternion((0, 0, 1), math.radians(yaw))


def rolled(angle, lift=0.0):
    """Lying along Y, head north: 0 on her back, 90 on her right side, 180 face down; lift raises the chest end."""
    a = math.radians(angle)
    return (0, -1, lift), (math.sin(a), 0, math.cos(a))


def pitched(angle):
    """Facing north: 0 face down, 90 upright, less than 90 leaning forward."""
    a = math.radians(angle)
    return (0, -math.cos(a), math.sin(a)), (0, -math.sin(a), -math.cos(a))


def rise_keys(lie, idle, square):
    """The rise's keys. lie: the last lying pose, measured. idle: the idle at STAND_AT, measured. Places are metres
    in the final frame (she ends at the origin facing -Y; her left is +X once she is face down or on her feet).

    body: t, p (pelvis place), up/front, yaw (1 = hips square, 0 = the idle's turn), arch and nod (positive = bent
          back: chest out, chin up), turn, ground (1 = the body rests on the ground: its height is solved).
    legs: ('dir', thigh, calf, foot) aimed; ('knee', place, calf, foot) the knee on a place; ('foot', ankle place,
          knee's way, foot direction, ball place or None) the ankle on a place, the foot aimed (at the ball's place
          when given: heel up, toes down).
    arms: ('dir', upper, lower, hand); ('pin', wrist place, elbow's way, hand direction); ('knee', offset from her
          own knee, elbow's way, hand direction). Optional palm (the way it faces) and curl (finger degrees).
    """
    def body(t, p, frame, yaw=1.0, arch=0, nod=0, turn=0, ground=0):
        return dict(t=t, p=p, q=facing(frame[0], frame[1], yaw * square), yaw=yaw * square, arch=arch, nod=nod, turn=turn, ground=ground)

    bodies = [
        dict(t=10.0, p=lie['p'], q=lie['q'], yaw=0.0, arch=-3, nod=10, turn=0, ground=0),
        # The roll, over her right side. The head leads: it turns the way she is going.
        body(10.45, (-.365, .55, .11), rolled(30), arch=0, nod=16, turn=26, ground=1),
        body(10.85, (-.300, .55, .14), rolled(56), arch=-2, nod=10, turn=20, ground=1),
        body(11.20, (-.200, .55, .19), rolled(92, .08), arch=-4, nod=4, turn=8, ground=1),
        body(11.55, (-.100, .55, .15), rolled(132, .06), arch=2, nod=22, turn=-4, ground=1),
        body(11.90, (0, .55, .11), rolled(180, .12), arch=8, nod=34, turn=0, ground=1),
        # Pushing up: the chest first, then the hips, up and back over her knees.
        body(12.25, (0, .555, .125), pitched(12), arch=16, nod=30),
        body(12.70, (0, .66, .36), pitched(13), arch=6, nod=16),
        body(13.10, (0, .78, .46), pitched(15), arch=-2, nod=4),
        # The hands push off; the torso swings up to kneel.
        body(13.45, (0, .90, .50), pitched(46), arch=-5, nod=14),
        body(13.75, (0, .955, .52), pitched(80), arch=0, nod=6, turn=-4),
        # Half kneel: the right foot planted in front; then forward over it and up.
        body(14.04, (-.02, .91, .51), pitched(83), arch=0, nod=2, turn=-6),
        body(14.45, (-.05, .70, .62), pitched(60), arch=-4, nod=18, turn=-3),
        body(14.84, (-.065, .53, .85), pitched(76), arch=0, nod=8),
        # On her feet: the left steps through, the right closes into the idle's stance.
        body(15.07, (-.05, .40, .895), pitched(85), nod=3),
        body(15.30, (0, .24, .85), pitched(87), nod=0, turn=4),
        body(15.56, (.04, .09, .90), pitched(88), yaw=.6, turn=3),
        body(15.85, (.022, .02, .912), pitched(91), yaw=.1, arch=2, nod=3),
        dict(t=STAND_AT, p=idle['p'], q=Quaternion(), yaw=0.0, arch=0, nod=0, turn=0, ground=0),
    ]
    knee_l, knee_r = (.10, .985, R_KNEE), (-.10, .985, R_KNEE)
    shin, instep = (0, 1, 0), (0, .98, -.2)
    toes_l = (.10, 1.53, .025)                       # the ball of the left foot while she kneels
    step_r = (-.10, .54, .078)                       # where the right foot plants for the half kneel
    flat_r = (-.10, -.88, -.466)                     # a flat foot: ankle toward ball
    ball_r = tuple(a + .15 * b for a, b in zip(step_r, unit(flat_r)))
    legs = {'l': [
        dict(t=10.0, leg=('dir',) + lie['leg_l']),
        # The left knee comes up, swings over and drops in front of her as she turns onto her side.
        dict(t=10.45, leg=('dir', (-.05, .66, .75), (0, .3, -.954), (0, .9, -.43))),
        dict(t=10.85, leg=('dir', (.45, .60, .66), (.25, .45, -.86), (.3, .9, -.3))),
        dict(t=11.20, leg=('dir', (.65, .58, -.5), (-.3, .95, 0), (-.1, 1, -.1))),
        dict(t=11.55, leg=('dir', (.35, .92, -.2), (-.05, 1, .05), (0, 1, -.1))),
        dict(t=11.90, leg=('knee', knee_l, shin, instep)),
        dict(t=14.04, leg=('knee', knee_l, shin, instep)),
        # The knee lifts as her weight goes onto the right foot; the toes are last to leave.
        dict(t=14.45, leg=('foot', (.105, 1.40, .15), (0, -1, -.3), None, toes_l)),
        dict(t=14.68, leg=('foot', (.11, 1.20, .30), (0, -1, 0), (0, .45, -.9), None)),
        dict(t=15.00, leg=('foot', (.14, .58, .17), (0, -1, 0), (0, -.6, -.8), None)),
        dict(t=15.30, leg=('foot', idle['ankle_l'], idle['pole_l'], idle['foot_l'], None)),
        dict(t=STAND_AT, leg=('foot', idle['ankle_l'], idle['pole_l'], idle['foot_l'], None)),
    ], 'r': [
        dict(t=10.0, leg=('dir',) + lie['leg_r']),
        dict(t=10.45, leg=('dir', (.06, 1, -.03), (.03, 1, 0), (.1, .3, 1))),
        dict(t=10.85, leg=('dir', (.08, 1, -.05), (.05, 1, 0), (.4, .4, .8))),
        dict(t=11.20, leg=('dir', (.10, 1, -.08), (.05, 1, 0), (.6, .8, 0))),
        dict(t=11.55, leg=('dir', (0, 1, -.06), (0, 1, 0), (.3, .9, -.3))),
        dict(t=11.90, leg=('knee', knee_r, shin, instep)),
        dict(t=13.75, leg=('knee', knee_r, shin, instep)),
        # The step: the knee lifts, the foot swings under it and plants (9 frames, 2026-11-08).
        dict(t=13.89, leg=('foot', (-.10, .96, .16), (0, -1, .5), (0, .5, -.87), None)),
        dict(t=13.97, leg=('foot', (-.10, .72, .19), (0, -1, .3), (0, -.2, -.98), None)),
        dict(t=14.04, leg=('foot', step_r, (0, -1, 0), flat_r, None)),
        dict(t=15.30, leg=('foot', step_r, (0, -1, 0), flat_r, None)),
        # Heel up, toes off, a short step to close.
        dict(t=15.45, leg=('foot', (-.10, .50, .17), (-.1, -1, 0), None, ball_r)),
        dict(t=15.65, leg=('foot', (-.10, .36, .15), (-.3, -1, 0), (-.4, -.7, -.6), None)),
        dict(t=15.85, leg=('foot', idle['ankle_r'], idle['pole_r'], idle['foot_r'], None)),
        dict(t=STAND_AT, leg=('foot', idle['ankle_r'], idle['pole_r'], idle['foot_r'], None)),
    ]}
    hand_l, hand_r = (.17, .27, .035), (-.21, .30, .035)   # where her hands push the ground
    down = (0, 0, -1)
    arms = {'l': [
        dict(t=10.0, arm=('dir',) + lie['arm_l'], curl=16),
        # The left arm reaches across her and plants in front of her chest as she comes onto her side.
        dict(t=10.45, arm=('dir', (.45, .45, .6), (.8, -.1, .45), (.85, -.2, .3)), curl=10),
        dict(t=10.85, arm=('dir', (.75, -.05, .6), (.9, -.25, -.2), (.8, -.4, -.45)), curl=8),
        dict(t=11.20, arm=('pin', hand_l, (.2, .5, 1), (-.15, -1, -.1)), palm=down, curl=4),
        dict(t=11.90, arm=('pin', hand_l, (.5, .8, 1), (-.15, -1, -.1)), palm=down, curl=4),
        dict(t=12.25, arm=('pin', hand_l, (.5, 1, .6), (-.15, -1, -.1)), palm=down, curl=4),
        dict(t=13.08, arm=('pin', hand_l, (.4, 1, .2), (-.15, -1, -.1)), palm=down, curl=5),
        # Off the ground, hanging forward as the torso comes up, then onto her thigh.
        dict(t=13.38, arm=('dir', (.15, -.6, -.78), (.05, -.75, -.66), (0, -.8, -.6)), curl=12),
        dict(t=13.75, arm=('dir', (.12, .10, -1), (0, -.45, -.9), (-.1, -.6, -.8)), curl=14),
        dict(t=14.04, arm=('dir', (.14, .12, -1), (.02, -.4, -.92), (-.05, -.55, -.83)), curl=14),
        # Out a little for balance as she leans, then swinging against the legs.
        dict(t=14.45, arm=('dir', (.22, .25, -.94), (.12, -.25, -.96), (.06, -.35, -.93)), curl=16),
        dict(t=14.84, arm=('dir', (.16, .08, -1), (.08, -.3, -.95), (.04, -.35, -.93)), curl=17),
        dict(t=15.07, arm=('dir', (.14, .2, -.97), (.08, -.05, -1), (.04, -.1, -1)), curl=18),
        dict(t=15.30, arm=('dir', (.14, .12, -1), (.08, -.15, -1), (.04, -.2, -1)), curl=18),
        dict(t=15.56, arm=('dir', (.13, -.08, -1), (.07, -.3, -.95), (.04, -.35, -.93)), curl=18),
        dict(t=STAND_AT, arm=('dir',) + idle['arm_l'], curl=16),
    ], 'r': [
        dict(t=10.0, arm=('dir',) + lie['arm_r'], curl=16),
        # The right arm folds at her side: she rolls over it and it comes out beside her chest, ready to push.
        dict(t=10.45, arm=('dir', (.3, .95, .05), (.6, -.3, .55), (.5, -.6, .4)), curl=12),
        dict(t=10.85, arm=('dir', (.5, .85, -.05), (.3, -.9, .25), (.1, -1, .1)), curl=10),
        dict(t=11.20, arm=('pin', (-.02, .24, .04), (.3, 1, .15), (-.3, -1, 0)), palm=down, curl=8),
        dict(t=11.90, arm=('pin', hand_r, (-.5, .8, 1), (.15, -1, -.1)), palm=down, curl=4),
        dict(t=12.25, arm=('pin', hand_r, (-.5, 1, .6), (.15, -1, -.1)), palm=down, curl=4),
        dict(t=13.14, arm=('pin', hand_r, (-.4, 1, .2), (.15, -1, -.1)), palm=down, curl=5),
        dict(t=13.42, arm=('dir', (-.15, -.6, -.78), (-.05, -.75, -.66), (0, -.8, -.6)), curl=12),
        dict(t=13.75, arm=('dir', (-.12, .10, -1), (0, -.45, -.9), (.1, -.6, -.8)), curl=14),
        # The right hand presses the right knee while she rises on that leg.
        dict(t=14.04, arm=('knee', (0, .04, .075), (-1, .6, .2), (.1, -.8, -.6)), palm=(0, .2, -1), curl=10),
        dict(t=14.50, arm=('knee', (0, .04, .075), (-1, .6, .2), (.1, -.8, -.6)), palm=(0, .2, -1), curl=10),
        dict(t=14.84, arm=('dir', (-.16, -.1, -1), (-.08, -.4, -.9), (-.04, -.45, -.9)), curl=16),
        dict(t=15.07, arm=('dir', (-.14, -.15, -1), (-.07, -.45, -.9), (-.04, -.5, -.87)), curl=18),
        dict(t=15.30, arm=('dir', (-.14, -.05, -1), (-.08, -.3, -.95), (-.04, -.35, -.93)), curl=18),
        dict(t=15.56, arm=('dir', (-.14, .12, -.99), (-.08, -.08, -1), (-.04, -.1, -1)), curl=18),
        dict(t=STAND_AT, arm=('dir',) + idle['arm_r'], curl=16),
    ]}
    return bodies, legs, arms


class Rise:
    def __init__(self, arm, bases, lie, idle, square):
        self.arm, self.bases = arm, bases
        bodies, legs, arms = rise_keys(lie, idle, square)
        self.bt = [k['t'] for k in bodies]
        self.bp = np.array([k['p'] for k in bodies], float)
        quats = []
        for k in bodies:
            q = k['q'].copy()
            if quats and q.dot(quats[-1]) < 0:
                q.negate()
            quats.append(q)
        self.bq = np.array([tuple(q) for q in quats], float)
        self.bs = np.array([(k['yaw'], k['arch'], k['nod'], k['turn'], k['ground']) for k in bodies], float)
        self.legs = {s: [self.limb_key(k['t'], k['leg']) for k in legs[s]] for s in 'lr'}
        self.arms = {s: [self.limb_key(k['t'], k['arm'], k) for k in arms[s]] for s in 'lr'}
        self.curls = {s: ([k['t'] for k in arms[s]], np.array([[k.get('curl', 16)] for k in arms[s]], float)) for s in 'lr'}
        w = lambda n: head_of(arm, n)
        set_base(arm, bases[1])
        self.len = {s: (((w(LEG[s][1]) - w(LEG[s][0])).length, (w(LEG[s][2]) - w(LEG[s][1])).length, (w(LEG[s][3]) - w(LEG[s][2])).length),
                        ((w(ARM[s][2]) - w(ARM[s][1])).length, (w(ARM[s][3]) - w(ARM[s][2])).length)) for s in 'lr'}
        # Resolve every limb key into directions (and palm facings), with the body where it is at that time.
        for s in 'lr':
            for key in self.legs[s]:
                self.body(key['t'])
                self.pose_leg(s, key['mode'], key['prm'])
                key['dirs'] = self.measure(LEG[s][:3], LEG[s][3])
        for s in 'lr':
            for key in self.arms[s]:
                self.body(key['t'])
                for z in 'lr':
                    self.pose_leg(z, *self.limb_at(self.legs[z], key['t'])[:2])
                self.pose_arm(s, key['mode'], key['prm'], 1.0 if key['t'] > RISE_FROM else 0.0)
                if key['palm'] is not None:
                    palm_facing(arm, s, PALM_SIGNS[s], key['palm'])
                key['dirs'] = self.measure(ARM[s][1:], 'middle_metacarpal_' + s)
                key['palm'] = np.array(palm_normal(arm, s)[1] * PALM_SIGNS[s])
        self.palms = {s: ([k['t'] for k in self.arms[s]], np.array([k['palm'] for k in self.arms[s]], float)) for s in 'lr'}

    @staticmethod
    def limb_key(t, spec, key=None):
        mode, parts = spec[0], spec[1:]
        if mode == 'foot':
            ankle, pole, foot, ball = parts
            toward = 1.0 if ball is not None else 0.0
            foot = foot if foot is not None else (0, 0, -1)
            ball = ball if ball is not None else ankle
            prm = np.array(list(ankle) + list(unit(pole)) + list(unit(foot)) + list(ball) + [toward], float)
        else:
            # A place (or an offset) first for 'knee' and 'pin'; everything else is a direction.
            vectors = [unit(parts[0]) if mode == 'dir' else Vector(parts[0])] + [unit(p) for p in parts[1:]]
            prm = np.array([c for v in vectors for c in v], float)
        return dict(t=t, mode=mode, prm=prm, palm=(key or {}).get('palm'))

    def limb_at(self, keys, t):
        """The limb's mode and numbers at t: between two keys of the same kind their places are interpolated (and
        held when equal); otherwise the directions each key resolved to."""
        ts = [k['t'] for k in keys]
        if t <= ts[0]:
            return keys[0]['mode'], keys[0]['prm'], False
        if t >= ts[-1]:
            return keys[-1]['mode'], keys[-1]['prm'], False
        i = min(bisect_right(ts, t) - 1, len(keys) - 2)
        a, b = keys[i], keys[i + 1]
        if a['mode'] == b['mode'] and a['mode'] != 'dir':
            lo, hi = i, i + 1
            while lo > 0 and keys[lo - 1]['mode'] == a['mode']:
                lo -= 1
            while hi < len(keys) - 1 and keys[hi + 1]['mode'] == a['mode']:
                hi += 1
            prm = pchip(ts[lo:hi + 1], np.array([k['prm'] for k in keys[lo:hi + 1]]), t)
            return a['mode'], prm, bool(np.allclose(a['prm'][:3], b['prm'][:3]))
        return 'dir', pchip(ts, np.array([k['dirs'] for k in keys]), t), False

    def planted_knee(self, s, t):
        """The place her knee is planted on at t, if it is."""
        keys = self.legs[s]
        ts = [k['t'] for k in keys]
        if not ts[0] <= t <= ts[-1]:
            return None
        i = min(bisect_right(ts, t) - 1, len(keys) - 2)
        a, b = keys[i], keys[i + 1]
        if a['mode'] == b['mode'] == 'knee' and np.allclose(a['prm'][:3], b['prm'][:3]):
            return a['prm'][:3]
        return None

    def measure(self, names, tip):
        pts = [head_of(self.arm, n) for n in names] + [head_of(self.arm, tip)]
        return np.array([c for a, b in zip(pts, pts[1:]) for c in (b - a).normalized()], float)

    def body(self, t):
        arm = self.arm
        set_base(arm, self.bases[1 + round(t * FPS)])
        p = pchip(self.bt, self.bp, t)
        q = Quaternion(pchip(self.bt, self.bq, t)).normalized()
        yaw, arch, nod, turn, ground = pchip(self.bt, self.bs, t)
        pelvis = arm.pose.bones['pelvis']
        rotate_about(arm, pelvis, q, arm.matrix_world @ pelvis.head)
        lateral = q @ (Quaternion((0, 0, 1), -math.radians(yaw)) @ Vector((1, 0, 0)))
        bend_spine(arm, lateral, arch, nod, turn)
        move = lambda v: set_world(arm, pelvis, Matrix.Translation(v) @ (arm.matrix_world @ pelvis.matrix))
        move(Vector(p) - head_of(arm, 'pelvis'))
        if ground > 1e-3:
            # Resting on the ground: hips, chest and shoulders are the body's contacts (she holds her head up).
            low = min(head_of(arm, n).z - r for n, r in (('pelvis', .10), ('thigh_l', .09), ('thigh_r', .09), ('spine_03', .10),
                                                        ('spine_05', .10), ('upperarm_l', .065), ('upperarm_r', .065)))
            move(Vector((0, 0, -low * ground)))
        # Kneeling: the hips stay a thigh's length from each planted knee.
        held = [(s, Vector(knee)) for s in 'lr' for knee in [self.planted_knee(s, t)] if knee is not None]
        for _ in range(4 if held else 0):
            fix = Vector()
            for s, knee in held:
                hip = head_of(arm, LEG[s][0])
                fix += knee + (hip - knee).normalized() * self.len[s][0][0] - hip
            move(fix / len(held))

    def pose_leg(self, s, mode, prm):
        arm, names = self.arm, LEG[s]
        l1, l2, l3 = self.len[s][0]
        hip = head_of(arm, names[0])
        if mode == 'dir':
            d1, d2, d3 = keep_above(hip, (prm[0:3], prm[3:6], prm[6:9]), (l1, l2, l3), (R_KNEE, R_ANKLE, R_BALL))
        elif mode == 'knee':
            d1 = (Vector(prm[0:3]) - hip).normalized()
            d2, d3 = keep_above(hip + d1 * l1, (prm[3:6], prm[6:9]), (l2, l3), (R_ANKLE, R_BALL))
        else:
            d1, d2, ankle = two_bone(hip, prm[0:3], l1, l2, prm[3:6], 'leg_' + s)
            foot = unit(prm[6:9])
            toward = Vector(prm[9:12]) - ankle
            if prm[12] > 1e-3 and toward.length > 1e-4:
                foot = unit(foot * (1 - prm[12]) + toward.normalized() * prm[12])
            d3 = keep_above(ankle, (foot,), (l3,), (.008,))[0]
        hinge_chain(arm, names[:3], names[3], d1, d2, d3)

    def pose_arm(self, s, mode, prm, hinge):
        arm, names = self.arm, ARM[s]
        l1, l2 = self.len[s][1]
        shoulder = head_of(arm, names[1])
        if mode == 'dir':
            d1, d2, d3 = keep_above(shoulder, (prm[0:3], prm[3:6], prm[6:9]), (l1, l2, HAND_REACH), (R_ELBOW, R_WRIST, R_KNUCKLE))
        else:
            target = Vector(prm[0:3]) + (head_of(arm, LEG[s][1]) if mode == 'knee' else Vector())
            d1, d2, wrist = two_bone(shoulder, target, l1, l2, prm[3:6], 'arm_' + s)
            d3 = keep_above(wrist, (prm[6:9],), (HAND_REACH,), (R_KNUCKLE,))[0]
        hinge_chain(arm, names[1:], 'middle_metacarpal_' + s, d1, d2, d3, weight=hinge)

    def frame(self, t):
        """Pose the whole rig at time t."""
        self.body(t)
        for s in 'lr':
            self.pose_leg(s, *self.limb_at(self.legs[s], t)[:2])
        # Elbows bend about their hinge from the first move on (the lying poses were built without it).
        hinge = min(max((t - RISE_FROM) / .45, 0.0), 1.0)
        hinge = hinge * hinge * (3 - 2 * hinge)
        for s in 'lr':
            self.pose_arm(s, *self.limb_at(self.arms[s], t)[:2], hinge)
            palm_facing(self.arm, s, PALM_SIGNS[s], unit(pchip(*self.palms[s], t)))
        curl_fingers(self.arm, {s: float(pchip(*self.curls[s], t)[0]) for s in 'lr'})


def measure_limbs(arm):
    w = lambda n: head_of(arm, n)
    dirs = lambda names, tip: tuple(tuple((b - a).normalized()) for a, b in zip([w(n) for n in names], [w(n) for n in names[1:]] + [w(tip)]))
    out = {'p': tuple(w('pelvis'))}
    for s in 'lr':
        out['leg_' + s] = dirs(LEG[s][:3], LEG[s][3])
        out['arm_' + s] = dirs(ARM[s][1:], 'middle_metacarpal_' + s)
        hip, knee, ankle = w(LEG[s][0]), w(LEG[s][1]), w(LEG[s][2])
        along = (ankle - hip).normalized()
        bend = (knee - hip) - along * (knee - hip).dot(along)
        out['ankle_' + s] = tuple(ankle)
        out['pole_' + s] = tuple(bend.normalized()) if bend.length > 1e-4 else (0, -1, 0)
        out['foot_' + s] = out['leg_' + s][2]
    return out


def main():
    out = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 1 else OUT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SOURCE))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    idle = arm.animation_data.action
    scene = bpy.context.scene
    scene.render.fps = FPS
    bones = [b.name for b in arm.pose.bones]
    for b in arm.pose.bones:
        b.rotation_mode = 'QUATERNION'
    idle_len = int(idle.frame_range[1])
    last = 1 + SECONDS * FPS
    # The idle on every frame, as local bases; then pose with no action on the rig, so nothing re-evaluates under us.
    bases = {}
    for frame in range(1, last + 1):
        scene.frame_set(1 + (frame - 1) % (idle_len - 1))
        bases[frame] = {n: arm.pose.bones[n].matrix_basis.copy() for n in bones}
    arm.animation_data.action = None
    global PALM_SIGNS
    set_base(arm, bases[1])
    PALM_SIGNS = palm_signs(arm)
    hips = head_of(arm, 'thigh_l') - head_of(arm, 'thigh_r')
    square = -math.degrees(math.atan2(hips.y, hips.x))    # the idle stands turned: this squares her hips to -Y
    snapshot = lambda: {n: arm.pose.bones[n].matrix_basis.copy() for n in bones}
    poses = {}
    # Lying: a few poses, the curves between them as before.
    for pose in LIE_POSES:
        frame = 1 + round(pose['t'] * FPS)
        build_lying_pose(arm, bases[frame], pose)
        poses[frame] = snapshot()
    # The last lying pose, measured, is where the rise starts; the idle at STAND_AT is where it ends.
    rise_first, rise_last = 1 + round(RISE_FROM * FPS), 1 + round(STAND_AT * FPS)
    turn = lambda: (arm.matrix_world @ arm.pose.bones['pelvis'].matrix).to_3x3().normalized().to_quaternion()
    lie = measure_limbs(arm)
    lying = turn()
    set_base(arm, bases[rise_first])
    lie['q'] = lying @ turn().inverted()
    set_base(arm, bases[rise_last])
    stand = measure_limbs(arm)
    rise = Rise(arm, bases, lie, stand, square)
    track = ('pelvis', 'head', 'hand_l', 'hand_r', 'lowerarm_l', 'lowerarm_r', 'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r')
    MISSES.clear()
    for frame in range(rise_first, rise_last + 1):
        before = len(MISSES)
        rise.frame((frame - 1) / FPS)
        poses[frame] = snapshot()
        if len(MISSES) > before:
            print('REACH t=%.2f' % ((frame - 1) / FPS), MISSES[before:], flush=True)
        if (frame - rise_first) % 3 == 0:
            skull = head_of(arm, 'head') + (head_of(arm, 'head') - head_of(arm, 'neck_01')).normalized() * .08
            print('RISE t=%5.2f skull %3.0f ' % ((frame - 1) / FPS, (skull.z - .095) * 100) + ' '.join('%s %3.0f' % (n.replace('lowerarm', 'elbow').replace('calf', 'knee'), head_of(arm, n).z * 100) for n in track), flush=True)
    # Standing: the idle itself, every 4th frame, with the head turn layered on.
    settle = poses[rise_last]
    turns = dict((1 + round(t * FPS), deg) for t, deg in LOOKS)
    times = sorted(turns)
    for frame in range(rise_last + 4, last + 1, 4):
        w = min(1.0, (frame - rise_last) / (BLEND_IN * FPS))
        w = w * w * (3 - 2 * w)
        for n, basis in bases[frame].items():
            if w < 1.0:
                a = settle[n]
                arm.pose.bones[n].matrix_basis = Matrix.LocRotScale(a.to_translation().lerp(basis.to_translation(), w),
                                                                    a.to_quaternion().slerp(basis.to_quaternion(), w), Vector((1, 1, 1)))
            else:
                arm.pose.bones[n].matrix_basis = basis.copy()
        bpy.context.view_layer.update()
        deg = 0.0
        for a, b in zip(times, times[1:]):
            if a <= frame <= b:
                k = (frame - a) / (b - a)
                k = k * k * (3 - 2 * k)
                deg = turns[a] * (1 - k) + turns[b] * k
        for name in NECK[1:]:
            pb = arm.pose.bones[name]
            rotate_about(arm, pb, Quaternion((0, 0, 1), math.radians(deg / 2)), arm.matrix_world @ pb.head)
        poses[frame] = snapshot()
    # Key it all on a fresh action.
    action = bpy.data.actions.new('A_Physis_GetUp')
    arm.animation_data.action = action
    previous = {}
    for frame in sorted(poses):
        scene.frame_set(frame)
        for n, basis in poses[frame].items():
            arm.pose.bones[n].matrix_basis = basis
        for b in arm.pose.bones:
            q = b.rotation_quaternion.copy()
            was = previous.get(b.name)
            if was is not None and q.dot(was) < 0:
                q.negate()
                b.rotation_quaternion = q
            previous[b.name] = q.copy()
            b.keyframe_insert('location', frame=frame)
            b.keyframe_insert('rotation_quaternion', frame=frame)
    # Motion check: no bone may turn faster than a person can, frame to frame (a flip shows as a spike).
    worst = []
    for b in arm.pose.bones:
        if not b.name.startswith(('pelvis', 'spine', 'neck', 'head', 'thigh', 'calf', 'foot', 'clavicle', 'upperarm', 'lowerarm', 'hand_')):
            continue
        was = None
        for frame in range(1, last + 1):
            scene.frame_set(frame)
            m = (arm.matrix_world @ b.matrix).to_quaternion()
            if was is not None:
                a = math.degrees(m.rotation_difference(was).angle) % 360
                worst.append((min(a, 360 - a), b.name, frame))
            was = m
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
    scene.frame_start, scene.frame_end = 1, last
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=str(out), use_selection=True, object_types={'ARMATURE'}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_step=1, bake_anim_simplify_factor=0.0,
                             apply_unit_scale=True, primary_bone_axis='Y', secondary_bone_axis='X')
    print('GETUP', out, len(poses), 'frames posed')


if __name__ == '__main__':
    main()
