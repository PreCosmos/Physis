"""K2: Divine Parry in the Glade. A Prism Wraith's bolt crawls in (slow motion); she blocks into a burst of sparks, then the Cyclone counter."""
import sys; sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
s = Spot(-64500, 2500, 1099, 90.0)
wraith = s.at(900, 0, 1084 - 1099 + 420)
muzzle = s.at(800, 0, 1084 - 1099 + 405)
chest = s.at(55, 0, 132)
bolt0, rot, scale = beam(muzzle, chest, .07)
start = [muzzle[i] + (chest[i] - muzzle[i]) * .0 for i in range(3)]
end = [muzzle[i] + (chest[i] - muzzle[i]) * .97 for i in range(3)]
meshes = [{'name': 'Prism Wraith', 'mesh': '/Game/Center/Meshes/SM_CE_Wraith', 'keys': [[0, *wraith, 0, 0, s.f + 180], [105, wraith[0] - 30, wraith[1] + 40, wraith[2] + 25, 0, 0, s.f + 176]]},
          {'name': 'Bolt', 'mesh': '/Engine/BasicShapes/Cube', 'material': '/Game/Gameplay/MI_EnemyBolt', 'scale': [1.5, .07, .07], 'shadow': False,
           'keys': [[20, *start, *rot], [48, *end, *rot]], 'range': [20, 49]}]
anims = [[0, 37, K + 'Physis_AS_HK_Idle', 1.0, 0.0], [34, 58, K + 'Physis_AS_HK_Block', 0.8, 0.0],
         [55, 101, K + 'Physis_AS_F_Cyclone', 1.6, 0.0], [98, 105, K + 'Physis_AS_HK_Idle', 1.0, 0.6]]
keys = [[0, *s.at(0)[:2], s.g, s.f - 90], [47, *s.at(0)[:2], s.g, s.f - 90], [52, *s.at(-22)[:2], s.g, s.f - 90], [105, *s.at(-22)[:2], s.g, s.f - 90]]
sparks = [s.at(-22 + 60, 0, 120), s.at(-22, 45, 150), s.at(-22, -45, 95)]
fx = [{'class': BP + 'BP_Spark', 'at': list(muzzle), 'frame': 8, 'len': 8}, {'class': BP + 'BP_Spark', 'at': list(muzzle), 'frame': 20, 'len': 8}]
fx += [{'class': BP + 'BP_Spark', 'at': list(p), 'frame': 48 + i, 'len': 8} for i, p in enumerate(sparks)]
fx += [{'class': BP + 'BP_SlashFX', 'at': list(s.at(-22, 0, 100)), 'rot': [r, 0, s.f + yaw], 'frame': f, 'len': 4} for f, r, yaw in ((49, 25, 0), (66, -20, 180), (80, 30, 0))]
c0, c1 = s.at(-260, 140, 120), s.at(-215, 125, 110)
d0, d1 = s.at(170, -210, 105), s.at(150, -170, 100)
cams = [cam('K2 shoulder', 46, 20, c0, s.at(500, 0, 220), c1, s.at(420, 0, 200)),
        cam('K2 parry', 59, 24, d0, s.at(-10, 0, 120), d1, s.at(-15, 0, 115))]
write('k2', {'sequence': '/Game/Trailer/SEQ_Trailer_Combat2', 'frames': 105,
             'physis': {'possess': 'CineOnly', 'keys': keys, 'anims': anims, 'weapon': KATANA}, 'meshes': meshes, 'fx': fx, 'cameras': cams})
