"""Author Physis's swimming loops on her body skeleton: treading water and a heads-up breaststroke.

Run: blender -b --python Tools/build_physis_swim.py [-- OUT_DIR]
Writes Art/Characters/Physis/A_Physis_SwimTread.fbx and A_Physis_SwimStroke.fbx (30 fps), imported by
`outfit_operation center:swim`, and Saved/swim_debug/<clip>.json (joint places on every frame, for a look at the
motion without Unreal). BP_SwimDirector plays them looping: the tread below 40-90 cm/s along the water, the stroke
above.

Author, 2026-11-15: "fix Physis's swim animations and make them as natural as possible". The clips of 2026-11-04
were five whole-body poses each with bone rotations interpolated between them (the method the get-up had), built on
build_physis_getup.build_pose, which no longer exists. Measured on them: the idle's stance (hips turned 22 degrees)
came through, so in the stroke her left hand rode 11 cm lower than her right and her feet 6 cm apart in height; in
the tread her feet moved 6 cm in all (no kick to speak of) and her hands slid 20 cm straight in and out at one
depth; in the stroke the legs snapped at up to 5.6 m/s and came together slowly after the kick, and nothing in
either clip moved her body.

Both loops are now solved on every frame with the get-up's tools (two-bone reach, hinge elbows and knees, palms):
  - her body is squared first (hips, chest and head all facing the way she swims), so left and right match;
  - each hand and foot is a place relative to its shoulder or hip, moving through its own keys, so the hands
    stay under the water and the elbows and knees bend only as they can;
  - the body answers the limbs: it lifts on each scull, and in the stroke the chest rises for the breath as the
    hands sweep in, the hips drop, and she surges forward after the kick;
  - every curve is periodic, so the last frame flows into the first.
Treading (2.4 s): an eggbeater kick, the two legs half a cycle apart, lower legs circling under bent knees held
forward and apart; the hands scull in flat figure-eights under the surface, palms leaning into each sweep; she
lifts a little on every sweep and sways slowly, and the second half of the loop is not a copy of the first.
Breaststroke (1.6 s): glide, outsweep to the catch, insweep under the chin with the breath, the hands shoot
forward as the heels come up, the feet turn out and whip round and together, glide.

Heights are above the clip's root (her capsule's bottom). With buoyancy 1.3 the capsule floats with its centre
47 cm under the surface (capsule half height 88), so the water is WATER = 1.37 m above the root.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_physis_getup as rig  # noqa: E402

FPS = 30
WATER = 1.37
OUT = rig.ROOT / 'Art/Characters/Physis'
DEBUG = rig.ROOT / 'Saved/swim_debug'
ARM, LEG = rig.ARM, rig.LEG
mirror = lambda v: Vector((-v[0], v[1], v[2]))


def cyc(keys, phase):
    """A periodic curve through keys [(fraction of the loop, values)]: shape-preserving (flat where a value turns
    or holds), tiled so the loop's end runs into its start."""
    ts = [f + k for k in (-1, 0, 1) for f, _ in keys]
    vs = np.array([np.ravel(v) for _ in range(3) for _, v in keys], float)
    return rig.pchip(ts, vs, phase % 1.0)


class Swimmer:
    def __init__(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(rig.SOURCE))
        self.arm = arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        self.scene = bpy.context.scene
        self.scene.render.fps = FPS
        self.scene.frame_set(1)
        for b in arm.pose.bones:
            b.rotation_mode = 'QUATERNION'
        self.names = [b.name for b in arm.pose.bones]
        self.base = {n: arm.pose.bones[n].matrix_basis.copy() for n in self.names}
        arm.animation_data.action = None
        rig.set_base(arm, self.base)
        rig.PALM_SIGNS = rig.palm_signs(arm)
        w = lambda n: rig.head_of(arm, n)
        hips = w('thigh_l') - w('thigh_r')
        self.square = -math.degrees(math.atan2(hips.y, hips.x))
        # How far the idle turns her chest and head from her hips (about her own up): taken out again in body().
        self.untwist = {}
        flat = lambda v: math.degrees(math.atan2(v.y, v.x))
        rig.rotate_about(arm, arm.pose.bones['pelvis'], Quaternion((0, 0, 1), math.radians(self.square)), w('pelvis'))
        chest = flat(w('upperarm_l') - w('upperarm_r'))
        head = arm.pose.bones['head']
        rest = lambda n: arm.data.bones[n].matrix_local.to_3x3()
        # The head's turn from its rest facing, about world up, compared with the pelvis's.
        yaw = lambda n: math.degrees(((arm.matrix_world @ arm.pose.bones[n].matrix).to_3x3() @ rest(n).inverted()).to_euler('ZYX').z)
        self.chest_twist = chest
        self.head_twist = yaw('head') - yaw('spine_05')
        print('SQUARE hips %.1f, chest turned %.1f from them, head %.1f from the chest' % (self.square, chest, self.head_twist), flush=True)
        rig.set_base(arm, self.base)
        self.len = {s: (((w(LEG[s][1]) - w(LEG[s][0])).length, (w(LEG[s][2]) - w(LEG[s][1])).length),
                        ((w(ARM[s][2]) - w(ARM[s][1])).length, (w(ARM[s][3]) - w(ARM[s][2])).length)) for s in 'lr'}
        print('LIMBS thigh %.3f calf %.3f upper arm %.3f forearm %.3f' % (self.len['l'][0] + self.len['l'][1]), flush=True)

    def body(self, place, pitch, roll, yaw, arch, nod, turn):
        """Pelvis at place; pitch 90 upright, 0 face down (she faces -Y); roll and yaw in degrees; then the spine."""
        arm = self.arm
        rig.set_base(arm, self.base)
        up, front = rig.pitched(pitch)
        sway = Quaternion((0, 0, 1), math.radians(yaw)) @ Quaternion((0, -1, 0), math.radians(roll))
        up, front = sway @ Vector(up), sway @ Vector(front)
        q = rig.facing(up, front, self.square)
        pelvis = arm.pose.bones['pelvis']
        rig.rotate_about(arm, pelvis, q, rig.head_of(arm, 'pelvis'))
        axis = up.normalized()
        for name in rig.SPINE[1:]:
            b = arm.pose.bones[name]
            rig.rotate_about(arm, b, Quaternion(axis, math.radians(-self.chest_twist / 5)), rig.head_of(arm, name))
        for name in rig.NECK:
            b = arm.pose.bones[name]
            rig.rotate_about(arm, b, Quaternion(axis, math.radians(-self.head_twist / 3)), rig.head_of(arm, name))
        lateral = (up.cross(front)).normalized()
        rig.bend_spine(arm, lateral, arch, nod, turn)
        rig.set_world(arm, pelvis, Matrix.Translation(Vector(place) - rig.head_of(arm, 'pelvis')) @ (arm.matrix_world @ pelvis.matrix))

    def leg(self, s, ankle, pole, foot):
        """Ankle at a place relative to the hip, the knee toward pole, the foot along foot (all for the left side)."""
        names = LEG[s]
        fix = (lambda v: Vector(v)) if s == 'l' else mirror
        hip = rig.head_of(self.arm, names[0])
        d1, d2, _ = rig.two_bone(hip, hip + fix(ankle), *self.len[s][0], fix(pole), 'leg_' + s)
        rig.hinge_chain(self.arm, names[:3], names[3], d1, d2, rig.unit(fix(foot)))

    def hand(self, s, wrist, pole, fingers, palm, depth=None):
        """Wrist at a place relative to the shoulder (depth: metres under the water instead of its z), the elbow
        toward pole, fingers along fingers, the palm facing palm (all for the left side)."""
        names = ARM[s]
        fix = (lambda v: Vector(v)) if s == 'l' else mirror
        shoulder = rig.head_of(self.arm, names[1])
        target = shoulder + fix(wrist)
        if depth is not None:
            target.z = WATER - depth
        d1, d2, _ = rig.two_bone(shoulder, target, *self.len[s][1], fix(pole), 'arm_' + s)
        rig.hinge_chain(self.arm, names[1:], 'middle_metacarpal_' + s, d1, d2, rig.unit(fix(fingers)))
        rig.palm_facing(self.arm, s, rig.PALM_SIGNS[s], rig.unit(fix(palm)))

    def snapshot(self):
        return {n: self.arm.pose.bones[n].matrix_basis.copy() for n in self.names}


# ---------------------------------------------------------------- treading water

TREAD_SECONDS = 2.4


def tread(sw, t):
    beat = 2 * math.pi * t / 1.2          # one kick of each leg and one scull out and in
    slow = 2 * math.pi * t / TREAD_SECONDS
    # She lifts as the hands press (twice a scull, a little more on the out-sweep) and settles between.
    lift = .010 * math.sin(2 * beat - .9) + .006 * math.sin(beat - .4) + .005 * math.sin(slow)
    sw.body((.012 * math.sin(slow), .006 * math.sin(beat + .5), .955 + lift),
            pitch=83 + 1.5 * math.sin(beat + 1.2), roll=1.6 * math.sin(slow) + .8 * math.sin(beat), yaw=2.0 * math.sin(slow + .8),
            arch=2 + 1.5 * math.sin(2 * beat - .9), nod=9 + 1.5 * math.sin(slow + 2.0), turn=4 * math.sin(slow + 2.4))
    for s, lag in (('l', 0.0), ('r', math.pi)):
        a = beat + lag
        # Eggbeater: the thigh held forward and out, rocking a little; the lower leg circles under the knee, out and
        # forward, then in and back (the right leg mirrored and half a cycle later).
        l1, l2 = sw.len[s][0]
        thigh = rig.unit((.30 + .06 * math.cos(a), -.70 + .06 * math.sin(a + .5), -.58 - .05 * math.sin(a)))
        shin = rig.unit((.10 + .38 * math.cos(a), .40 - .40 * math.sin(a), -.80))
        ankle = thigh * l1 + shin * l2
        # The sole leads the sweep: toes out as the foot goes out, forward as it comes round.
        foot = (.50 + .30 * math.cos(a + .6), -.50 - .25 * math.sin(a + .6), -.62)
        sw.leg(s, ankle, thigh, foot)
    for s, lag in (('l', 0.0), ('r', .18)):
        a = beat + .7 - lag
        out, going = math.sin(a), math.cos(a)   # where the hand is in its sweep, and which way it is moving
        # A flat figure-eight under the surface: out and in, dipping a little at each turn.
        wrist = (.11 + .15 * out, -.33 - .025 * math.cos(2 * a), 0)
        fingers = (.20 + .30 * going, -.92, -.10)
        palm = (.60 * going, .12, -.80)           # the palm leans into the sweep, thumb down going out, up coming in
        sw.hand(s, wrist, (.80, .45, -.40), fingers, palm, depth=.15 + .02 * math.sin(2 * a + .4))
    rig.curl_fingers(sw.arm, {'l': 12, 'r': 12})


# ---------------------------------------------------------------- breaststroke

STROKE_SECONDS = 1.6
# Fractions of the loop. Body: (pitch from face-down, pelvis forward (-y), pelvis height, arch, nod).
STROKE_BODY = (
    (.00, (25, .000, 1.225, 8, 22)),       # glide: long, the chest up enough to keep her chin over the water
    (.24, (25, .010, 1.225, 8, 22)),
    (.44, (29, .020, 1.215, 11, 20)),      # outsweep: the chest starts up
    (.62, (35, .030, 1.190, 15, 15)),      # insweep: the breath, hips down
    (.78, (30, .005, 1.210, 11, 19)),      # hands shoot, the kick starts
    (.93, (25, -.035, 1.225, 8, 22)),      # the kick's drive carries her forward
)
# Wrist from the shoulder (x out, y forward when negative, z up), elbow pole, fingers, palm.
STROKE_ARM = (
    (.00, ((-.09, -.515, -.08), (.5, .2, -.8), (.02, -1, .00), (.15, 0, -1))),      # stretched ahead, hands together
    (.24, ((-.09, -.515, -.08), (.5, .2, -.8), (.02, -1, .00), (.25, 0, -1))),
    (.42, ((.19, -.42, -.12), (.8, .1, .4), (.40, -.88, -.20), (.60, .30, -.70))),   # outsweep to the catch, palms out
    (.53, ((.21, -.20, -.27), (.9, -.1, .4), (.00, -.80, -.60), (.00, .70, -.70))),  # the pull: elbows high, palms back
    (.66, ((-.08, -.17, -.25), (.6, .5, -.6), (-.25, -.95, -.10), (-.60, .35, -.55))),  # insweep: hands meet under the chin
    (.76, ((-.10, -.34, -.12), (.5, .4, -.7), (-.05, -1, .05), (-.25, .10, -.90))),     # shooting forward
    (.88, ((-.09, -.515, -.08), (.5, .2, -.8), (.02, -1, .00), (.15, 0, -1))),
)
# Ankle from the hip, knee pole, foot (toes).
STROKE_LEG = (
    (.00, ((-.04, .822, -.13), (.1, -.2, -1), (.00, 1, -.10))),       # legs long and together, toes pointed
    (.44, ((-.04, .822, -.13), (.1, -.2, -1), (.00, 1, -.10))),
    (.62, ((.07, .30, -.03), (.35, -.45, -.85), (.45, .45, .75))),   # heels drawn up to the seat, knees a little apart
    (.70, ((.27, .31, -.08), (.15, -.45, -.9), (.85, .20, .45))),    # the catch: feet out past the knees, toes turned out
    (.78, ((.36, .58, -.17), (.15, -.3, -.95), (.70, .65, .05))),    # whipping round and back
    (.90, ((-.04, .822, -.13), (.1, -.2, -1), (.00, 1, -.10))),       # together
)


def stroke(sw, t):
    phase = t / STROKE_SECONDS
    pitch, forward, height, arch, nod = cyc(STROKE_BODY, phase)
    sw.body((0, -forward, height), pitch=pitch, roll=0, yaw=0, arch=arch, nod=nod, turn=0)
    ankle, pole, foot = cyc(STROKE_LEG, phase).reshape(3, 3)
    wrist, elbow, fingers, palm = cyc(STROKE_ARM, phase).reshape(4, 3)
    for s in 'lr':
        sw.leg(s, ankle, pole, foot)
    for s in 'lr':
        sw.hand(s, wrist, elbow, fingers, palm)
    rig.curl_fingers(sw.arm, {'l': 7, 'r': 7})


# ---------------------------------------------------------------- build

TRACK = ('pelvis', 'head', 'upperarm_l', 'upperarm_r', 'lowerarm_l', 'lowerarm_r', 'hand_l', 'hand_r', 'thigh_l', 'thigh_r',
         'calf_l', 'calf_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r', 'neck_01', 'spine_03', 'spine_05', 'middle_metacarpal_l', 'middle_metacarpal_r')


def build(sw, name, pose, seconds, out):
    arm, scene = sw.arm, sw.scene
    frames = round(seconds * FPS)
    arm.animation_data.action = None
    rig.MISSES.clear()
    poses, places = [], []
    for k in range(frames + 1):
        pose(sw, (k % frames) / FPS)          # the last frame is the first again
        poses.append(sw.snapshot())
        skull = rig.head_of(arm, 'head') + (rig.head_of(arm, 'head') - rig.head_of(arm, 'neck_01')).normalized() * .09
        places.append(dict({n: tuple(round(c, 4) for c in rig.head_of(arm, n)) for n in TRACK}, skull=tuple(round(c, 4) for c in skull)))
    if rig.MISSES:
        print('REACH', name, sorted(set(rig.MISSES))[:12], flush=True)
    # Report: heights against the water, left against right, the fastest hand and foot.
    col = lambda n, i: np.array([p[n][i] for p in places])
    speed = lambda n: np.linalg.norm(np.diff(np.array([p[n] for p in places]), axis=0), axis=1).max() * FPS
    print('%s %d frames: head joint %.0f..%.0f cm over the water, hands %.0f..%.0f cm under, feet %.0f..%.0f cm under, pelvis moves %.1f cm up and down' % (
        name, frames, (col('head', 2).min() - WATER) * 100, (col('head', 2).max() - WATER) * 100,
        (WATER - col('hand_l', 2).max()) * 100, (WATER - col('hand_l', 2).min()) * 100,
        (WATER - col('foot_l', 2).max()) * 100, (WATER - col('foot_l', 2).min()) * 100, (col('pelvis', 2).max() - col('pelvis', 2).min()) * 100), flush=True)
    print('   fastest: hand %.1f m/s, foot %.1f m/s; shoulders level within %.1f cm, hips within %.1f cm' % (
        max(speed('hand_l'), speed('hand_r')), max(speed('foot_l'), speed('foot_r')),
        np.abs(col('upperarm_l', 2) - col('upperarm_r', 2)).max() * 100, np.abs(col('thigh_l', 2) - col('thigh_r', 2)).max() * 100), flush=True)
    DEBUG.mkdir(parents=True, exist_ok=True)
    (DEBUG / (name + '.json')).write_text(json.dumps({'fps': FPS, 'water': WATER, 'frames': places}))
    action = bpy.data.actions.new(name)
    arm.animation_data.action = action
    previous = {}
    for k, basis in enumerate(poses):
        for n, m in basis.items():
            arm.pose.bones[n].matrix_basis = m
        for b in arm.pose.bones:
            q = b.rotation_quaternion.copy()
            was = previous.get(b.name)
            if was is not None and q.dot(was) < 0:
                q.negate()
                b.rotation_quaternion = q
            previous[b.name] = q.copy()
            b.keyframe_insert('location', frame=1 + k)
            b.keyframe_insert('rotation_quaternion', frame=1 + k)
    # No bone may turn faster than a person can, frame to frame (a flip shows as a spike).
    worst = []
    for b in arm.pose.bones:
        if not b.name.startswith(('pelvis', 'spine', 'neck', 'head', 'thigh', 'calf', 'foot', 'clavicle', 'upperarm', 'lowerarm', 'hand_')):
            continue
        was = None
        for k in range(frames + 1):
            scene.frame_set(1 + k)
            m = (arm.matrix_world @ b.matrix).to_quaternion()
            if was is not None:
                a = math.degrees(m.rotation_difference(was).angle) % 360
                worst.append((round(min(a, 360 - a), 1), b.name, k))
            was = m
    worst.sort(reverse=True)
    print('   fastest turns (deg/frame, bone, frame):', worst[:5], flush=True)
    scene.frame_start, scene.frame_end = 1, 1 + frames
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(out / (name + '.fbx')), use_selection=True, object_types={'ARMATURE'}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_step=1, bake_anim_simplify_factor=0.0,
                             apply_unit_scale=True, primary_bone_axis='Y', secondary_bone_axis='X')
    print('SWIM', out / (name + '.fbx'), flush=True)


def main():
    out = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv and len(sys.argv) > sys.argv.index('--') + 1 else OUT
    for name, pose, seconds in (('A_Physis_SwimTread', tread, TREAD_SECONDS), ('A_Physis_SwimStroke', stroke, STROKE_SECONDS)):
        build(Swimmer(), name, pose, seconds, out)


if __name__ == '__main__':
    main()
