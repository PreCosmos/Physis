"""The trailer's shots, level by level (read by trailer_ue.py in Unreal and by cut.py outside it). Pure Python.

Positions are Unreal centimetres. A shot: name, frames (30 fps), keys of (time 0..1, camera position, look-at point
[, roll]), focal length in mm (the cine camera's sensor is 24.89 mm wide), optional focus distance (cm) and aperture
for depth of field, 'ev' exposure compensation in stops, 'ease' for a move that starts and ends at rest. Two keys make a straight move at constant speed.
In the Awakening, 'anim' is the second of the get-up clip (and of the eye clip) at which the shot starts.
"""
import math


def aim(pos, pitch, yaw, reach=10000.0):
    """A look-at point `reach` cm ahead of pos along a pitch and yaw in degrees."""
    p, y = math.radians(pitch), math.radians(yaw)
    return (pos[0] + math.cos(p) * math.cos(y) * reach, pos[1] + math.cos(p) * math.sin(y) * reach, pos[2] + math.sin(p) * reach)


def move(a, pa, ya, b, pb, yb):
    return [(0, a, aim(a, pa, ya)), (1, b, aim(b, pb, yb))]


# The wake point in the Center and its floor: the stand-in Physis lies with her head at W(3, 36, 22), feet toward -x,
# and stands up facing +x about 40 cm behind W(0, 0, 0).
WAKE = (-68400.0, 0.0, 1183.6)


def W(x, y, z):
    return (WAKE[0] + x, WAKE[1] + y, WAKE[2] + z)


LEFT_EYE = W(8.45, 36.6, 38.3)   # while she lies still, before the first breath lifts her head 13 cm

LEVELS = {
    'Awakening': {'map': '/Game/Levels/L_CenterOfTheUniverse', 'shots': [
        {'name': 'a1_eye', 'ev': -0.8, 'frames': 96, 'anim': 1.2, 'focal': 85,
         'keys': [(0, W(3.2, 36.6, 57.5), LEFT_EYE), (1, W(3.6, 36.6, 55.5), LEFT_EYE)]},
        {'name': 'a1_gasp', 'ev': -1.3, 'frames': 60, 'anim': 4.4, 'focal': 35, 'focus': 125, 'aperture': 2.0,
         'keys': [(0, W(-62, 150, 44), W(-14, 36, 40)), (1, W(-54, 150, 50), W(-14, 36, 42))]},
        {'name': 'a2_profile', 'ev': -1.3, 'frames': 84, 'anim': 6.6, 'focal': 50, 'focus': 80, 'aperture': 2.0,
         'keys': [(0, W(-34, 114, 36), W(0, 36, 38)), (1, W(-16, 114, 42), W(0, 36, 38))]},
        {'name': 'a3_above', 'ev': -1.0, 'frames': 96, 'anim': 6.4, 'focal': 21, 'ease': True,
         'keys': [(0, W(-92, 36, 400), W(-82, 36, 10), 0), (1, W(-92, 36, 900), W(-82, 36, 10), 30)]},
        {'name': 'a4_roll', 'ev': -0.5, 'frames': 111, 'anim': 10.0, 'focal': 35, 'focus': 520, 'aperture': 2.8,
         'keys': [(0, W(60, -500, 32), W(-50, 30, 45)), (1, W(20, -470, 36), W(-50, 30, 70))]},
        {'name': 'a5_rise', 'frames': 84, 'anim': 13.7, 'focal': 28, 'focus': 480, 'aperture': 2.8,
         'keys': [(0, W(-430, 230, 35), W(-20, 0, 100)), (1, W(-400, 250, 50), W(-20, 0, 125))]},
        {'name': 'a6_reveal', 'frames': 120, 'anim': 16.0, 'focal': 21, 'ease': True,
         'keys': [(0, W(-200, -60, 165), W(1400, 100, 200)), (1, W(-2600, 1900, 2800), W(9000, -1500, 600))]},
    ]},
    'Center': {'map': '/Game/Levels/L_CenterOfTheUniverse', 'shots': [
        {'name': 'c1_rays', 'frames': 105, 'focal': 21, 'keys': move((-27000, -9500, 5710), -7, 16, (-23200, -8050, 5820), -6, 19)},
        {'name': 'c2_ring', 'frames': 90, 'focal': 21, 'keys': move((-4600, -6100, 1017), 5, 53, (-3500, -4650, 992), 6, 53)},
        {'name': 'c3_marsh', 'frames': 90, 'focal': 21, 'keys': move((-29600, -38400, 258), 0, -132, (-29950, -38050, 255), 1, -134)},
        {'name': 'c4_choir', 'frames': 75, 'focal': 21, 'keys': move((-12400, 45600, 532), 3, 104, (-12600, 46350, 528), 2, 104)},
        {'name': 'c5_temple', 'frames': 105, 'focal': 21, 'keys': move((58000, 0, 4465), 1, 0, (62500, 0, 4350), 4, 0)},
    ]},    'Station': {'map': '/Game/Levels/L_BattleStation', 'shots': [
        {'name': 's2_battle', 'frames': 120, 'focal': 12, 'keys': move((8500, -224000, 29000), -5, 88, (7800, -212000, 27300), -6, 89)},
        {'name': 's3_approach', 'frames': 90, 'focal': 12, 'keys': move((7000, -100000, 13500), -5, 87, (5000, -70000, 9000), -4, 87)},
        {'name': 's4_hall', 'frames': 75, 'focal': 21, 'keys': move((4250, -380, 195), -1, 10, (4720, -280, 186), 0, 8)},
        {'name': 's5_spine', 'frames': 75, 'focal': 21, 'keys': move((8250, -300, 330), -8, 2, (8780, -275, 311), -7, 4)},
        {'name': 's6_boss', 'frames': 75, 'focal': 21, 'keys': move((13600, -620, 240), 1, 22, (14000, -460, 231), 2, 17)},
    ]},
    'Conclave': {'map': '/Game/Levels/L_Conclave', 'shots': [
        {'name': 'n1_well', 'frames': 90, 'focal': 24, 'keys': [(0, (-75200, 0, 850), (-47000, 0, 4000)), (1, (-73600, 0, 900), (-47000, 0, 4000))]},
        {'name': 'n2_overhead', 'frames': 105, 'focal': 18, 'ease': True,
         'keys': [(0, (-30000, 0, 3000), (20000, 0, 9000)), (1, (-29000, 0, 3200), (20000, 0, 70000))]},
        {'name': 'n3_patience', 'frames': 75, 'focal': 35, 'keys': [(0, (-45200, 3400, 930), (-43000, 5200, 1250)), (1, (-44700, 3800, 960), (-43000, 5200, 1250))]},
        {'name': 'n4_lake', 'frames': 75, 'focal': 24, 'keys': [(0, (-5000, -3000, 1400), (6000, 4500, 2200)), (1, (-4200, -4200, 1400), (6000, 4500, 2200))]},
        {'name': 'n5_terraces', 'frames': 75, 'focal': 24, 'keys': [(0, (-12000, -16000, 3000), (-2000, -26800, 4500)), (1, (-11000, -17000, 3100), (-2000, -26800, 4500))]},
        {'name': 'n6_docks', 'frames': 75, 'focal': 24, 'keys': [(0, (63000, -3000, 1400), (70000, 0, 1600)), (1, (64000, -2600, 1350), (70000, 0, 1600))]},
    ]},
    'Grove': {'map': '/Game/Levels/L_Grove', 'shots': [
        {'name': 'g1_valley', 'frames': 105, 'focal': 21, 'keys': [(0, (-64000, -4000, 26000), (20000, 0, 3600)), (1, (-56000, 0, 24000), (20000, 0, 3600))]},
        {'name': 'g2_floor', 'frames': 75, 'focal': 28, 'focus': 650, 'aperture': 2.8,
         'keys': [(0, (-29000, -3000, 3700), (-25000, 0, 3500)), (1, (-28850, -3250, 3715), (-25000, 0, 3500))]},
        {'name': 'g3_thorn', 'frames': 75, 'focal': 35, 'keys': [(0, (-43400, 9000, 4100), (-40500, 10800, 4100)), (1, (-43000, 9250, 4090), (-40500, 10800, 4100))]},
        {'name': 'g4_falls', 'frames': 75, 'focal': 21, 'keys': [(0, (33000, -25000, 2200), (43000, -30000, 6000)), (1, (33150, -25100, 2400), (43000, -30000, 6000))]},
        {'name': 'g5_heart', 'frames': 105, 'focal': 21, 'keys': [(0, (20500, -2000, 4700), (33000, -2000, 7500)), (1, (21500, -2000, 5300), (33000, -2000, 8200))]},
    ]},
    'Arche': {'map': '/Game/Levels/L_Arche', 'shots': [
        {'name': 'r1_basin', 'frames': 105, 'focal': 24, 'keys': [(0, (-28000, -16000, 7000), (40000, 0, 4500)), (1, (-24000, -14500, 6600), (40000, 0, 4500))]},
        {'name': 'r2_arch', 'frames': 80, 'focal': 24, 'keys': [(0, (-24800, 1500, 1050), (-21500, 3000, 1500)), (1, (-24300, 1900, 1100), (-21500, 3000, 1500))]},
        {'name': 'r3_span', 'frames': 80, 'focal': 24, 'keys': [(0, (-18200, 600, 1300), (-15000, 3000, 1400)), (1, (-17900, 1500, 1350), (-15000, 3000, 1400))]},
        {'name': 'r4_cistern', 'frames': 75, 'focal': 21, 'keys': [(0, (1300, -13800, 1120), (2000, -20500, 1000)), (1, (1100, -14300, 1080), (2000, -20500, 1000))]},
        {'name': 'r5_garden', 'frames': 75, 'focal': 28, 'keys': [(0, (13800, 19000, 2250), (18800, 28200, 3200)), (1, (14100, 19500, 2200), (18800, 28200, 3200))]},
        {'name': 'r6_lens', 'frames': 96, 'focal': 24, 'keys': [(0, (37000, -2400, 3450), (45200, 0, 5000)), (1, (39000, -1600, 3550), (45200, 0, 5000))]},
    ]},
}
