"""K3: the sidearm at the Concourse west. Three shots with gold tracers into a Shardling Matriarch, a burst after the third."""
import sys; sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
s = Spot(-9000, -3500, 602, 180.0)
target = s.at(800, 0, 600 - 602 + 165)
muzzle = s.at(72, 22, 146)
shots = (13, 31, 49)
meshes = [{'name': 'Matriarch', 'mesh': '/Game/Center/Meshes/SM_CE_Shardling', 'scale': [1.45, 1.45, 1.45],
           'keys': [[0, *target, 0, 0, s.f + 180], [20, target[0] + 25, target[1], target[2] + 8, 0, 0, s.f + 175], [52, target[0] + 60, target[1] + 20, target[2] + 15, 0, 0, s.f + 170]], 'range': [0, 52]}]
fx = []
for i, f in enumerate(shots):
    hit = (target[0] + 25 + 12 * i, target[1] + (-30, 25, 0)[i], target[2] + (15, -10, 5)[i])
    mid, rot, scale = beam(muzzle, hit, .025)
    meshes.append({'name': 'Tracer %d' % i, 'mesh': '/Engine/BasicShapes/Cube', 'material': '/Game/Gameplay/MI_Item_Tracer', 'scale': scale, 'shadow': False,
                   'keys': [[f, *mid, *rot]], 'range': [f, f + 3]})
    fx.append({'class': BP + 'BP_Spark', 'at': list(hit), 'frame': f + 1, 'len': 8})
fx.append({'class': BP + 'BP_DroneBurst', 'at': list(s.at(795, 0, 600 - 602 + 175)), 'frame': 51, 'len': 40})
anims = [[0, 90, A + 'Physis_MF_Pistol_Idle_ADS', 1.0, 0.0]]  # Physis_MM_Pistol_Fire is additive: alone it leaves the bind pose
keys = [[0, *s.at(0)[:2], s.g, s.f], [90, *s.at(-15)[:2], s.g, s.f]]  # the female pistol clips face the actor's own forward (the katana clips face +90)
c0, c1 = s.at(-235, 95, 168), s.at(-195, 80, 160)
d0, d1 = s.at(120, -330, 115), s.at(160, -300, 105)
c1 = s.at(-175, 75, 156)
cams = [cam('K3 shoulder', 90, 22, c0, target, c1, target)]
write('k3', {'sequence': '/Game/Trailer/SEQ_Trailer_Combat3', 'frames': 90,
             'physis': {'possess': 'CineOnly', 'keys': keys, 'anims': anims, 'weapon': GUN}, 'meshes': meshes, 'fx': fx, 'cameras': cams})
