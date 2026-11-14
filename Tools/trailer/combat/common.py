import json, math
OUT = '/home/precosmos/PhysisProject/Tools/trailer/combat/%s.json'
K = '/Game/Characters/Physis/Animations/Katana/'
A = '/Game/Characters/Physis/Animations/'
BP = '/Game/Characters/Physis/Blueprints/'
KATANA = {'mesh': '/Game/Stylized_Katana/Katana/Meshes/SM_Katana_1_A', 'material': '/Game/Art/Materials/M_KatanaOrnate', 'loc': [-2.5, 2.1, -5.4], 'rot': [-96.96, -41.8, 163.32], 'scale': 0.4}
GUN = {'mesh': '/Game/Gameplay/SM_Physis_Gun', 'material': '/Game/Art/Materials/M_GunOrnate', 'loc': [-9, 3.5, 1], 'rot': [-16.7, -12.35, 169.6], 'scale': 1.25}
class Spot:
    def __init__(self, x, y, ground, facing):
        self.p, self.g, self.f = (x, y), ground, facing
        self.fwd = (math.cos(math.radians(facing)), math.sin(math.radians(facing)))
        self.right = (math.cos(math.radians(facing + 90)), math.sin(math.radians(facing + 90)))
    def at(self, d=0.0, r=0.0, z=0.0):
        return (self.p[0] + self.fwd[0] * d + self.right[0] * r, self.p[1] + self.fwd[1] * d + self.right[1] * r, self.g + z)
def look(cam, target):
    dx, dy, dz = target[0] - cam[0], target[1] - cam[1], target[2] - cam[2]
    return [math.degrees(math.atan2(dy, dx)), math.degrees(math.atan2(dz, math.hypot(dx, dy)))]
def cam(name, frames, focal, a0, t0, a1, t1):
    return {'name': name, 'frames': frames, 'focal': focal, 'from': list(a0) + look(a0, t0), 'to': list(a1) + look(a1, t1)}
def beam(start, end, thick):
    """A cube (100 cm) stretched from start to end: centre, rotation (roll, pitch, yaw) and scale."""
    dx, dy, dz = end[0] - start[0], end[1] - start[1], end[2] - start[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    mid = [(start[i] + end[i]) / 2 for i in range(3)]
    return mid, [0.0, math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx))], [length / 100.0, thick, thick]
def write(name, arg):
    json.dump(arg, open(OUT % name, 'w'), indent=1)
    print(name, 'written:', len(arg.get('fx', [])), 'fx,', len(arg.get('meshes', [])), 'meshes')
