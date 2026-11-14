"""K1: katana combo at the Concourse (Cut, Slice, Whirl) into a Shardling, which bursts on the third hit."""
import json, math
OUT = '/home/precosmos/PhysisProject/Tools/trailer/combat/k1.json'
K = '/Game/Characters/Physis/Animations/Katana/'
G = 614.0                     # ground at the spot
P = (-2600.0, -3600.0)
F = 54.0                      # her facing (toward the Concourse Ring); actor yaw = facing - 90
fwd = (math.cos(math.radians(F)), math.sin(math.radians(F)))
right = (math.cos(math.radians(F + 90)), math.sin(math.radians(F + 90)))
at = lambda d=0.0, r=0.0: (P[0] + fwd[0] * d + right[0] * r, P[1] + fwd[1] * d + right[1] * r)
def look(cam, target):
    dx, dy, dz = target[0] - cam[0], target[1] - cam[1], target[2] - cam[2]
    return math.degrees(math.atan2(dy, dx)), math.degrees(math.atan2(dz, math.hypot(dx, dy)))
# Her forward travel per hit (cm), as LaunchCharacter lunges do in the game.
steps = [(0, 0), (10, 0), (16, 25), (31, 25), (36, 55), (50, 55), (57, 90), (80, 90)]
physis_keys = [[f, at(d)[0], at(d)[1], G, F - 90] for f, d in steps]
anims = [[0, 13, K + 'Physis_AS_HK_Idle', 1.0, 0.0],
         [10, 33, K + 'Physis_AS_F_Cut', 2.3, 0.266],
         [30, 52, K + 'Physis_AS_F_Slice', 2.3, 0.247],
         [49, 80, K + 'Physis_AS_F_Whirl', 1.84, 0.28],
         [77, 80, K + 'Physis_AS_HK_Idle', 1.0, 0.4]]
# Shardling 1: closes in, knocked back by each hit, gone at the burst.
e1 = [(0, 330, 150), (12, 215, 145), (15, 215, 150), (19, 240, 155), (34, 240, 150), (38, 262, 160), (55, 275, 150), (58, 292, 165)]
e1_keys = [[f, at(d)[0], at(d)[1], G + z, 0, 0, F + 180] for f, d, z in e1]
e2_keys = [[0, at(760, -260)[0], at(760, -260)[1], G + 170, 0, 0, F + 160], [80, at(700, -200)[0], at(700, -200)[1], G + 160, 0, 0, F + 170]]
hits = [(15, 215), (34, 240), (55, 275)]
fx = []
for i, (f, d) in enumerate(hits):
    pd = dict(steps)[min(dict(steps), key=lambda k: abs(k - f))]
    x, y = at(pd)
    fx.append({'class': '/Game/Characters/Physis/Blueprints/BP_SlashFX', 'at': [x, y, G + 100], 'rot': [(-30, 25, -15)[i], 0, F], 'frame': f - 1, 'len': 4})
    ex, ey = at(d)
    fx.append({'class': '/Game/Characters/Physis/Blueprints/BP_Spark', 'at': [ex, ey, G + 145], 'rot': [0, 0, 0], 'frame': f, 'len': 8})
bx, by = at(285)
fx.append({'class': '/Game/Characters/Physis/Blueprints/BP_DroneBurst', 'at': [bx, by, G + 155], 'rot': [0, 0, 0], 'frame': 56, 'len': 40})
# Cameras: over her left shoulder pushing in, then low at her front right for the finish and the burst.
mid = (at(160)[0], at(160)[1], G + 125)
ca0 = (*at(-330, -150), G + 175); ca1 = (*at(-250, -170), G + 155)
cb0 = (*at(150, 360), G + 70); cb1 = (*at(210, 300), G + 80)
mid2 = (at(230)[0], at(230)[1], G + 120)
ca1 = (*at(-215, -175), G + 150)
cams = [{'name': 'K1 shoulder', 'frames': 80, 'focal': 22, 'from': [*ca0, *look(ca0, mid)], 'to': [*ca1, *look(ca1, mid)]}]
arg = {'sequence': '/Game/Trailer/SEQ_Trailer_Combat1', 'frames': 80,
       'physis': {'possess': 'CineOnly', 'keys': physis_keys, 'anims': anims,
                  'weapon': {'mesh': '/Game/Stylized_Katana/Katana/Meshes/SM_Katana_1_A', 'material': '/Game/Art/Materials/M_KatanaOrnate',
                             'loc': [-2.5, 2.1, -5.4], 'rot': [-96.96, -41.8, 163.32], 'scale': 0.4}},
       'meshes': [{'name': 'Shardling', 'mesh': '/Game/Center/Meshes/SM_CE_Shardling', 'scale': [1, 1, 1], 'keys': e1_keys, 'range': [0, 58]},
                  {'name': 'Shardling 2', 'mesh': '/Game/Center/Meshes/SM_CE_Shardling', 'scale': [1.2, 1.2, 1.2], 'keys': e2_keys}],
       'fx': fx, 'cameras': cams}
json.dump(arg, open(OUT, 'w'), indent=1)
print('k1 written', len(fx), 'fx')
