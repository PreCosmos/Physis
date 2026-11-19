"""Gameplay for level 8, Morrow, the Valley Before Morning (GAME_ROADMAP.md "Level 8"). Still Points, the people, Edda's
bench, the Stilled, the Ferry Bridge and its Rime, the Schoolhouse's yard, the Glider Field, the Telegraph House, the
Dam Stair, the crest and the Hold, the Ice House, the Morning (Maren's mind: the kitchen, the hall, the field, the crest
as she remembers it, the Unrisen), caches, sealed vaults, the Frost Guard by region, Divinity Rays, tutorials and
voices. Run through `morrow:scenario` (place) and `morrow:portal` (the Center's sanctum current).

Positions are plan metres (physis_morrow_plan: x north, y east); Place's methods take centimetres. Everything placed
here is labelled 'Scene ...' in the outliner folder MorrowScene (the level build owns the folder Morrow).

Progress tokens (BP_Physis Flags):
  ,morrow, ,at_morrow,  arrived / saves load here     ,edda,  Edda met     ,sitwith,  the bench
  ,mw_miller,  the miller     ,mw_bridge,  the keeper: the Ferry Bridge     ,mw_mem1-3, ,mw_mems,  the three memories
  ,mw_inner,  Maren sat with (BP_MorrowDirector takes her in: ,mw_in,)     ,mw_room1-3,  the Morning's memories
  ,mw_still,  the Unrisen stops     ,unrisen,  sat with (the director brings her out: ,mw_out,, and the sun rises)
  ,maren,  Maren in person     ,aug_agility9, then Edda's reward
  side requests ,corin, ,mw_crew1-3, ,mw_crew, ,pilgrim, ,satchel,;  caches ,mw_cache1-5,;  seals ,mw_seal1-2,
  augmentations ,aug_hp11, ,aug_katana9, ,aug_pistol8, ,aug_defense9, ,aug_agility9,
Encounter rooms 801-899. Tags for BP_MorrowDirector: MorrowScar (hidden once the Unrisen is sat with: the Rime, the
ice), MorrowBloom (shown then), MorrowBridge (the Rime on the Ferry Bridge, hidden with ,mw_bridge,), MorrowRoom1-2
(the Morning's Rime doors), MorrowWay (the walk to the Morning's crest, shown with ,mw_room3,), MorrowSun, MorrowHush.
Markers: TargetPoint tags MorrowArrival (here), MorrowReturn (in the Center), MorrowInner (the Morning's kitchen) and
MorrowCrest (where she comes back out).

This module stands on the Grove's scenario (physis_grove_scenario: the Place class and its passes), loaded a second
time under another name with Morrow's folder, meshes, voices and Still Point rule put in its globals.
"""
import importlib.util
import math
import pathlib
import random

import unreal

import physis_morrow_lore as lore
import physis_morrow_plan as plan
import physis_morrow_tools as T
import physis_gameplay_tools as game
from physis_lore import image_name, voice_name

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
_spec = importlib.util.spec_from_file_location('physis_morrow_base', ROOT / 'Content/Python/physis_grove_scenario.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

MORROW = '/Game/Morrow'
MESHES = MORROW + '/Meshes'
VOICES = MORROW + '/Audio/Voice'
LEVEL = '/Game/Levels/L_Morrow'
CENTER_LEVEL = '/Game/Levels/L_CenterOfTheUniverse'
FOLDER = 'MorrowScene'
M = 100.0
COLD = (.62, .74, 1.0)
AMBER = (1.0, .55, .12)
RIME = (1.0, .14, .68)
EMBER = (1.0, .45, .34)
LAMP = (1.0, .78, .5)
DAWN = (1.0, .82, .6)
# The Center: the temple's top tier, 16 m south-east of the Heartbloom (the Conclave's current is north, the Grove's
# east, Arche's west, Halcyon's north-west, Hesper's north-east; south is the sanctum's Still Point); she comes back
# 11 m out from it.
TEMPLE = (76000.0, 0.0)
SANCTUM = 3400.0 + 600.0
PORTAL = (TEMPLE[0] - 1131.0, TEMPLE[1] + 1131.0, SANCTUM + 35.0)
RETURN = (TEMPLE[0] - 778.0, TEMPLE[1] + 778.0, SANCTUM + 120.0)
# Morrow's people as MetaHumans, the first of each that exists: their own (physis_earth_people.py, 2026-11-19), else
# the Conclave's who stood in for them before (Wen, Marek, Ama).
LOOKS = {'Edda': ('/Game/Conclave/People/Edda/BP_Edda', '/Game/Conclave/People/Wen/BP_Wen'),
         'Corin': ('/Game/Conclave/People/Corin/BP_Corin', '/Game/Conclave/People/Marek/BP_Marek'),
         'Maren': ('/Game/Conclave/People/Maren/BP_Maren', '/Game/Conclave/People/Ama/BP_Ama')}
# Levels whose enemies are living (Maren's grief): (Animal, Reach cm) as arche_shared.animals reads them.
ANIMALS = {7: (1, 230.0), 8: (5, 350.0), 9: (6, 800.0)}
INNER_X = 1000.0   # plan metres: east of this is the Morning


def mesh_asset(name):
    """A mesh by its name alone: Morrow's own (SM_O*), Halcyon's (SM_H*), the Conclave's (SM_C*), a scan (SM_GS_) or the
    Grove's."""
    if name.startswith('/'):
        return base.asset(name)
    if name.startswith('SM_O'):
        return base.asset(MESHES + '/' + name)
    if name.startswith('SM_H'):
        return base.asset('/Game/Halcyon/Meshes/' + name)
    if name.startswith('SM_C'):
        return base.asset('/Game/Conclave/Meshes/' + name)
    if name.startswith('SM_GS_'):
        return base.asset('/Game/Grove/Scans/' + name)
    return base.asset('/Game/Grove/Meshes/' + name)


base.FOLDER, base.LEVEL, base.VOICES, base.STILL_UNTIL, base.mesh_asset = FOLDER, LEVEL, VOICES, ',unrisen,', mesh_asset
cm, turned, component, props, wrap, asset, cls, sub = base.cm, base.turned, base.component, base.props, base.wrap, base.asset, base.cls, base.sub
INNER_FLOOR = plan.INNER_Z * M


class Place(base.Place):
    def __init__(self, ground):
        super().__init__(ground)
        self.stilled = []

    def floor(self, x, y):
        if x / M > INNER_X:
            return INNER_FLOOR
        return self.g.at(x, y)

    def ok(self, x, y, clear, still):
        mx, my = x / M, y / M
        if mx > INNER_X:
            return not (still and any(math.hypot(x - sx, y - sy) < still for sx, sy in self.stills))
        if plan.rim(mx, my) > .9 or plan.in_gorge(mx, my, 3.0) or plan.in_pond(mx, my, 2.0) or plan.in_lake(mx, my, 3.0):
            return False
        if any(math.hypot(x - sx, y - sy) < r + clear for sx, sy, r in self.solids):
            return False
        return not (still and any(math.hypot(x - sx, y - sy) < still for sx, sy in self.stills))

    def enemy(self, level, label, x, y, room=0, z=None):
        mesh, health, scale, hover, entry, kind = lore.MORROW_ENEMIES[level]
        if z is None:
            x, y = self.free(x, y, 400.0, 3000.0)
            ground = self.floor(x, y)
        else:
            ground = z
        place = (x, y, ground + hover)
        actor = self.spawn('BP_TrainingDrone', 'Enemy L%d %s' % (level, label), place, (scale, scale, scale), 'Enemies', RoomId=room, Boss=False,
                           Health=health)
        actor.set_editor_property('Static', False)
        actor.set_editor_property('EnemyKind', kind)
        if level in ANIMALS:
            # Grief: it never fires. It closes, draws back and strikes with its body (arche_shared.animals), and it is
            # not destroyed but scattered.
            number, reach = ANIMALS[level]
            for name, value in (('Organic', True), ('Animal', number), ('Reach', reach)):
                try:
                    actor.set_editor_property(name, value)
                except Exception:
                    self.unset.append((label, name))
        self.reskin(actor, mesh)
        self.tag(actor, entry, place, label)
        self.enemies += 1
        return actor

    def still(self, row, folder='Stilled', show='', hide='', pages=(), step=0.0, key=None, hold=4.0, radius=320.0):
        """BP_Stilled: one of the Stilled (a lore.STILLED row), a memory, or the kneeling Unrisen. Sitting with it within
        `radius` cm for `hold` s wakes it (morrow_logic.stilled): it thaws, says its text, gives its token. With `pages`
        it is the spoken stage: a page every `step` s of sitting, and it wakes after the last."""
        rkey, name, mesh, (x, y), yaw, voice, kind, narration, speech, after, give, need, denied = row
        px, py = cm(x, y)
        z = self.floor(px, py)
        done = lore.stilled_text(row) if not pages else ''
        actor = self.spawn('BP_Stilled', 'Stilled ' + rkey, (px, py, z), None, folder, Show=show, Hide=hide, Need=need, Give=give, Done=wrap(done),
                           Denied=wrap(denied), Key=(key if key is not None else (rkey if speech else '')), Pages='|'.join(wrap(p) for p in pages),
                           Step=float(step), Hold=float(hold), Radius=float(radius))
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        shape = component(actor, 'Shape')
        if shape is not None:
            figure = mesh_asset(mesh) if mesh else None
            shape.set_static_mesh(figure)
            if figure is not None:
                for slot in range(shape.get_num_materials()):
                    shape.set_material(slot, None)
                shape.set_collision_profile_name('BlockAll' if mesh.startswith('SM_OP_') else 'NoCollision')
        self.stilled.append(rkey)
        return actor


def pack(p, label, x, y, levels, room=0, spread=700.0, z=None):
    return base.pack(p, label, x, y, levels, room, spread, z)


def cache(p, n, title, x, y, z=None, need=''):
    token = ',mw_cache%d,' % n
    z = p.floor(x, y) if z is None else z
    p.relic('Frost Cache %d' % n, (x, y, z + 110), token, lore.MESSAGES['cache'], need=need, divinity=40.0, mesh='SM_HN_Cache', scale=1.3)
    p.light('Cache Glow %d' % n, (x, y, z + 160), COLD, 1300, 500, 'Items')
    p.site(title, x, y, 2, token)


def dress(p, label, rows, folder, origin=(0.0, 0.0), yaw0=0.0):
    """Props round a point: rows of (mesh, x, y, yaw, scale, solid cm) in metres, turned by yaw0."""
    for k, (mesh, x, y, yaw, scale, solid) in enumerate(rows):
        dx, dy = turned(x * M, y * M, yaw0)
        px, py = origin[0] * M + dx, origin[1] * M + dy
        p.mesh('%s %d' % (label, k), mesh, (px, py, p.g.at(px, py) - 3), yaw0 + yaw, scale, folder, solid=solid)


def stilled_row(key):
    return next(row for row in lore.STILLED if row[0] == key)


# ---------------------------------------------------------------- the valley

def chapel(p):
    gx, gy = cm(*plan.CHAPEL)
    floor = p.g.at(gx, gy)
    p.spawn('BP_MorrowCurrent', 'Current Home', (gx, gy, floor + 25), None, 'Chapel', Need='', Dest=2, Radius=180.0)
    p.solids.append((gx, gy, 500))
    p.light('Chapel Glow', (gx, gy, floor + 600), COLD, 9000, 2800, 'Chapel')
    sx, sy = cm(*plan.CHAPEL_STILL)
    p.check('Pass Chapel', sx, sy, lore.QUEST_ARRIVE, 800.0)
    p.marks['Arrival'] = p.at(sx, sy, 120)
    p.marker('Arrival', p.marks['Arrival'], 'MorrowArrival', 'Chapel')
    cx, cy = cm(plan.CHAPEL[0] + 14.0, plan.CHAPEL[1] + 12.0)
    p.mesh('Pass Chapel', 'SM_ON_Chapel', (cx, cy, p.g.at(cx, cy) - 30), 200.0, 1.0, 'Chapel', solid=700)
    p.light('Chapel Lamp', (cx - 300, cy - 200, p.g.at(cx, cy) + 300), LAMP, 1200, 900, 'Chapel')
    dress(p, 'Chapel', (('SM_HN_Lamp', -8.0, 12.0, 0.0, 1.0, 40), ('SM_HN_Lamp', 12.0, -12.0, 0.0, 1.0, 40), ('SM_GV_Pine', -16.0, -14.0, 0.0, 1.1, 150),
                        ('SM_GV_Pine', 20.0, 22.0, 0.0, .9, 150), ('SM_HN_Crate', 9.0, 10.0, 25.0, .8, 100)), 'Chapel', plan.CHAPEL)
    cache(p, 1, 'Pass Chapel Cache', *cm(-470.0, -14.0))


def orchard(p):
    pack(p, 'Orchard Road', *cm(-424.0, 46.0), (1, 1, 2), 801, 600)
    p.encounter('Orchard Road', *cm(-424.0, 46.0), 801, ',mw_road,', 'The Frost Guard\'s patrol is down. The road down to the mill is clear.')
    pack(p, 'Orchards', *cm(-350.0, 34.0), (1, 2), 0, 600)
    pack(p, 'Ice House Lane', *cm(-370.0, 130.0), (2, 2, 1), 0, 700)


CAMP = (('SM_HN_Crate', 4.0, 10.0, 15.0, 1.0, 100), ('SM_HN_Crate', 5.4, 11.0, 40.0, .8, 90), ('SM_GN_Canister', 6.0, -9.0, 0.0, 1.0, 80),
        ('SM_HN_Lamp', 12.0, 6.0, 0.0, 1.0, 40), ('SM_HN_Lamp', 12.0, -6.0, 0.0, 1.0, 40), ('SM_GV_Birch', -14.0, 18.0, 0.0, .8, 150))


def mill(p):
    mx, my = plan.MILL
    p.check('Mill House', *cm(*plan.MILL_STILL), 'The Mill House. Speak to Edda.')
    hx, hy = cm(mx + 2.0, my - 8.0)
    p.mesh('Mill House', 'SM_ON_Mill', (hx, hy, p.g.at(hx, hy) - 20), 0.0, 1.0, 'Mill', solid=900)
    wx, wy = cm(*plan.WHEEL)
    p.mesh('Mill Wheel', 'SM_ON_Wheel', (wx, wy, p.g.at(hx, hy) - 20 + 260), 0.0, 1.0, 'Mill', tags=('MorrowWheel',))
    p.light('Mill Window', (hx + 560, hy + 160, p.g.at(hx, hy) + 170), LAMP, 2600, 1200, 'Mill')
    p.light('Mill Fire', (hx + 900, hy + 400, p.g.at(hx, hy) + 250), LAMP, 1800, 1400, 'Mill')
    dress(p, 'Mill Yard', CAMP, 'Mill', plan.MILL)
    # The millpond's ice and Edda's bench on its bank.
    px, py, pr = plan.POND
    ix, iy = cm(px, py)
    p.mesh('Millpond Ice', 'SM_ON_IceDisc', (ix, iy, (plan.floor_z(px) - .45) * M), 0.0, (pr + 3.0, pr + 3.0, 1.0), 'Mill')
    bx, by = cm(*plan.BENCH)
    yaw = math.degrees(math.atan2(iy - by, ix - bx))
    p.switch('Edda\'s Bench', (bx, by, p.g.at(bx, by) - 2), yaw, 'SM_ON_Bench', True, None, 'Mill', Need=',edda,', Give=',sitwith,',
             Denied=lore.MESSAGES['bench_denied'], Done=lore.BENCH_DONE)
    p.light('Bench Glow', (bx, by, p.g.at(bx, by) + 400), EMBER, 1600, 900, 'Mill')
    p.still(stilled_row('Miller'))
    for row in lore.PEOPLE:
        if row[5][0] < -250.0:
            p.solids.append((row[5][0] * M, row[5][1] * M, 250))


def gorge(p):
    """The Ferry Bridge: 32 m over the 26 m Gorge, its deck tilted to meet both rims, buried in Rime until the keeper
    wakes (MorrowBridge). The barrier she remembers: opened only by sitting with him."""
    my = plan.GORGE_CROSS_Y * M
    mx = plan.gorge_x(plan.GORGE_CROSS_Y) * M
    south, north = plan.BRIDGE_SOUTH[0] * M - 300.0, plan.BRIDGE_NORTH[0] * M + 300.0
    zs, zn = p.g.at(south, my), p.g.at(north, my)
    pitch = math.degrees(math.atan2(zn - zs, north - south))
    p.mesh('Ferry Bridge', 'SM_ON_Bridge', (mx, my, (zs + zn) / 2 + 2.0), 0.0, 1.0, 'Gorge', pitch=pitch)
    mound = p.mesh('Ferry Bridge Rime', 'SM_ON_RimeMound', (mx, my, (zs + zn) / 2 - 60.0), 0.0, (1.0, 1.15, 1.0), 'Gorge', tags=('MorrowBridge', 'MorrowScar'),
                   pitch=pitch)
    p.light('Bridge Rime', (mx, my, zs + 400), RIME, 2600, 1800, 'Gorge', ('MorrowBridge',))
    p.still(stilled_row('Keeper'))
    kx, ky = cm(*plan.KEEPER)
    p.mesh('Bridge Bell Post', 'SM_HN_Lamp', (kx + 250, ky - 200, p.g.at(kx, ky) - 3), 0.0, 1.0, 'Gorge')
    for k, x in enumerate((south - 300.0, north + 300.0)):
        p.light('Bridge Abutment %d' % k, (x, my, p.g.at(x, my) + 300), COLD, 1200, 800, 'Gorge')
    return mound


def square(p):
    ux, uy = cm(*plan.SQUARE)
    p.check('Chapel Square', ux, uy, lore.QUEST_THREE)
    cx, cy = cm(plan.SQUARE[0] + 16.0, plan.SQUARE[1] + 14.0)
    p.mesh('Square Chapel', 'SM_ON_Chapel', (cx, cy, p.g.at(cx, cy) - 30), 225.0, 1.35, 'Square', solid=900)
    dress(p, 'Square', (('SM_HN_Crate', 8.0, -6.0, 10.0, 1.0, 100), ('SM_HN_Bollard', -9.0, 8.0, 0.0, 1.0, 40), ('SM_HN_Bollard', -9.0, -8.0, 0.0, 1.0, 40),
                        ('SM_HN_Lamp', 12.0, -10.0, 0.0, 1.0, 40), ('SM_GN_Canister', -7.0, 12.0, 0.0, 1.0, 80)), 'Square', plan.SQUARE)
    for k, (level, x, y) in enumerate(((2, -40.0, 30.0), (2, -36.0, -14.0), (1, -48.0, 8.0))):
        p.enemy(level, 'Square %d' % k, x * M, y * M, 802)
    p.encounter('Chapel Square', -42.0 * M, 8.0 * M, 802, ',mw_square,', 'Chapel Square is clear.')
    for label, (x, y), levels in (('School Lane', (-40.0, -84.0), (1, 2)), ('Field Lane', (-30.0, 110.0), (1, 1, 3)), ('Dam Road', (40.0, 30.0), (2, 3))):
        pack(p, label, *cm(x, y), levels, 0, 700)
    cache(p, 2, 'Square Cache', *cm(-60.0, 40.0))


def school(p):
    """The Schoolhouse, its front (+x) to the north, Ada Lowe at its door; Rime walls ring its yard and break it into a
    maze (MorrowScar)."""
    sx, sy = cm(*plan.SCHOOL)
    floor = p.g.at(sx, sy)
    p.check('Schoolhouse', *cm(*plan.SCHOOL_STILL), 'The Schoolhouse is west, past the Rime.')
    p.mesh('Schoolhouse', 'SM_ON_School', (sx, sy, floor - 30), 0.0, 1.0, 'School', solid=1100)
    # The yard's ring of Rime: 12 walls round a 28 m circle in front of the school, open to the north-east where the
    # lane comes in; and three walls inside it, so the way to the door winds.
    cx, cy = sx + 1800.0, sy
    for k in range(14):
        bearing = k * 360.0 / 14
        if 30.0 < bearing < 60.0 or 160.0 < bearing < 200.0:
            continue     # the gap where the lane comes in, and the school's own front
        b = math.radians(bearing)
        x, y = cx + math.cos(b) * 2400.0, cy + math.sin(b) * 2400.0
        p.mesh('School Rime %02d' % k, 'SM_ON_RimeWall', (x, y, p.g.at(x, y) - 30), bearing, (1.0, .58, 1.0), 'School', tags=('MorrowScar',))
    for k, (dx, dy, yaw) in enumerate(((900.0, -700.0, 90.0), (300.0, 700.0, 90.0), (-500.0, -300.0, 0.0))):
        x, y = cx + dx, cy + dy
        p.mesh('School Maze %d' % k, 'SM_ON_RimeWall', (x, y, p.g.at(x, y) - 30), yaw, (1.0, .9, 1.0), 'School', tags=('MorrowScar',))
    p.light('School Rime', (cx, cy, floor + 500), RIME, 4000, 3200, 'School', ('MorrowScar',))
    p.still(stilled_row('Ada'))
    for k, (level, dx, dy) in enumerate(((5, 900.0, 900.0), (2, -400.0, 1200.0), (2, 1300.0, -900.0))):
        p.enemy(level, 'School Guard %d' % k, cx + dx, cy + dy, 803)
    p.encounter('School Guards', cx, cy, 803, ',mw_school,', 'The Frost Guard at the school is down.')


def field(p):
    fx, fy = plan.FIELD
    p.check('Glider Field', *cm(*plan.FIELD_STILL), 'The Glider Field is up the lane, on its bench.')
    hx, hy = cm(fx + 30.0, fy + 26.0)
    p.mesh('Hangar', 'SM_ON_Hangar', (hx, hy, p.g.at(hx, hy) - 15), 225.0, 1.0, 'Field', solid=1200)
    gx, gy = cm(fx + 12.0, fy + 2.0)
    p.mesh('Glider', 'SM_ON_Glider', (gx, gy, p.g.at(gx, gy) - 5), 30.0, 1.0, 'Field', solid=400)
    p.still(stilled_row('Jory'))
    for k, (level, dx, dy) in enumerate(((3, -20.0, -20.0), (4, 20.0, -30.0), (5, -10.0, 30.0))):
        p.enemy(level, 'Field Guard %d' % k, (fx + dx) * M, (fy + dy) * M, 804)
    p.encounter('Field Guards', *cm(fx, fy), 804, ',mw_field,', 'The Frost Guard on the field is down.')
    cache(p, 3, 'Hangar Cache', *cm(fx + 34.0, fy + 8.0))


def telegraph(p):
    tx, ty = cm(*plan.TELEGRAPH)
    p.check('Telegraph House', *cm(*plan.ROCK_STILL), 'The Telegraph House is up the path, on its rock.')
    p.mesh('Telegraph House', 'SM_ON_Telegraph', (tx, ty, p.g.at(tx, ty) - 20), 0.0, 1.0, 'Telegraph', solid=500)
    p.still(stilled_row('Ines'))
    sx, sy = tx + 150.0, ty - 300.0
    p.relic('Pilgrim\'s Satchel', (sx, sy, p.g.at(sx, sy) + 60), ',satchel,', lore.MESSAGES['satchel'], need=',pilgrim,', mesh='SM_ON_Satchel', scale=1.4)
    for k, (level, dx, dy) in enumerate(((5, -1600.0, -1000.0), (2, -800.0, 900.0))):
        p.enemy(level, 'Telegraph Guard %d' % k, tx + dx, ty + dy, 805)
    p.encounter('Telegraph Guards', tx - 1200.0, ty, 805, ',mw_rock,', 'The Frost Guard on the rock is down.')


def dam(p):
    """The crest: sections of the dam from wall to wall (the stair's gap at the middle), the Hold, Maren; the Dam
    Stair's flights up the embankment; the guards on the stair."""
    reach = plan.RIM[1] * (1 - (plan.CREST[0] / plan.RIM[0]) ** 2) ** .5 + 20.0
    cx = plan.CREST[0] * M
    top = (plan.CREST_Z + .15) * M
    k = 0
    for y in [i * 24.0 for i in range(-int(reach // 24), int(reach // 24) + 1)]:
        p.mesh('Dam %02d' % k, 'SM_ON_Dam1' if y == 0.0 else 'SM_ON_Dam0', (cx, y * M, top), 0.0, 1.0, 'Dam')
        k += 1
    for f in range(11):
        x, z = plan.FOOT_X + 10.35 * f, plan.FOOT_Z + 4.4895 * f
        p.mesh('Dam Stair %02d' % f, 'SM_ON_Stair', (x * M, 0.0, z * M - 5.0), 0.0, 1.0, 'Dam')
    p.check('Dam Stair', *cm(*plan.STAIR_STILL), 'The Dam Stair. Maren is on the crest.')
    p.check('Crest', *cm(*plan.CREST_STILL), lore.QUEST_CREST, z=top)
    hx, hy = cm(*plan.HOLD)
    p.mesh('Hold', 'SM_ON_Hold', (hx, hy, top - 10), 90.0, 1.0, 'Dam', solid=900)
    door = (hx, hy + 820.0, top)
    p.switch('Hold Doors', door, 90.0, 'SM_HN_Bollard', False, (.01, .01, .01), 'Dam', Need=',unrisen,', Give=',mw_holdopen,',
             Denied=lore.MESSAGES['hold_shut'], Done='The Hold\'s doors stand open. The Lull is still, and the cold has gone out of it.')
    p.relic('The Lull\'s Heart', (hx + 300.0, hy + 1100.0, top + 115), ',aug_hp11,', lore.MESSAGES['heart'], ',unrisen,', heal=True, mesh='SM_CN_LightCache',
            scale=1.4)
    p.light('Hold Vents', (hx, hy, top + 1200), RIME, 6000, 3000, 'Dam', ('MorrowScar',))
    p.light('Hold Lamps', (hx, hy + 900, top + 450), AMBER, 2400, 1200, 'Dam')
    p.still(stilled_row('MarenStilled'), hide=',unrisen,', radius=360.0)
    mx, my = cm(*plan.MAREN)
    p.require('Memories', (mx, my, top + 300), (',mw_mem1,', ',mw_mem2,', ',mw_mem3,'), ',mw_mems,', lore.MESSAGES['memories'])
    p.marker('Crest Return', (cx - 200.0, 2400.0, top + 120), 'MorrowCrest', 'Dam')
    p.light('Crest Rime', (mx, my, top + 600), RIME, 3000, 2600, 'Dam', ('MorrowScar',))
    for k, (level, x, y) in enumerate(((5, 330.0, 14.0), (5, 380.0, -14.0), (4, 300.0, -20.0), (2, 350.0, 30.0), (2, 400.0, -30.0), (1, 420.0, 60.0))):
        z = (plan.dam_z(x) or plan.floor_z(x)) * M
        p.enemy(level, 'Stair Guard %d' % k, x * M, y * M, 806, z)
    p.encounter('Dam Stair', 360.0 * M, 0.0, 806, ',mw_stair,', 'The Dam Stair is clear. Maren is on the crest.', z=(plan.dam_z(360.0)) * M)
    cache(p, 4, 'Dam Foot Cache', *cm(plan.FOOT_X - 20.0, 40.0))


def icehouse(p):
    ix, iy = cm(*plan.ICEHOUSE)
    floor = p.g.at(ix, iy)
    p.mesh('Ice House', 'SM_ON_IceHouse', (ix, iy, floor - 60), 0.0, 1.0, 'Ice House', solid=700)
    for key in ('Crew1', 'Crew2', 'Crew3'):
        p.still(stilled_row(key))
    p.require('Ice House Crew', (ix, iy, floor + 600), (',mw_crew1,', ',mw_crew2,', ',mw_crew3,'), ',mw_crew,', lore.MESSAGES['crew'])
    p.relic('The Icecutter\'s Blade', (ix + 560.0, iy - 150.0, floor + 115), ',aug_katana9,', lore.MESSAGES['blade'], ',mw_crew,', mesh='SM_CN_LightCache',
            scale=.8)
    p.site('Ice House', ix, iy, 0, ',aug_katana9,')
    p.enemy(6, 'Ice House Harrow', ix + 1800.0, iy - 2200.0, 861)
    p.encounter('Ice House Harrow', ix + 1800.0, iy - 2200.0, 861, ',mw_harrow,', 'The Harrow is still.')


def sealed(p):
    """Vaults for abilities learned elsewhere: Trace Reading (Halcyon) and Dissonance (Hesper) both open already."""
    for n, ((x, y), ability) in enumerate(((plan.SEALED_TRACE, ',trace,'), (plan.SEALED_DISSONANCE, ',dissonance,')), 1):
        px, py = cm(x, y)
        yaw = math.degrees(math.atan2(-py, -px))
        door = p.spawn('BP_AbilitySocket', 'Sealed Vault %d' % n, (px, py, p.g.at(px, py) - 10), None, 'Sealed', Ability=ability, Give=',mw_seal%d,' % n,
                       Radius=900.0, Hold=0.0, Solid=True, Message='The vault\'s seal opens.')
        door.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = p.reskin(door, 'SM_HN_GateDoor')
        if part:
            part.set_relative_scale3d(unreal.Vector(1.0, .3, .32))
            part.set_collision_profile_name('BlockAll')
        back = turned(-480.0, 0.0, yaw)
        p.mesh('Sealed Cell %d' % n, 'SM_ON_IceHouse', (px + back[0], py + back[1], p.g.at(px, py) - 60), yaw, (.6, .6, .6), 'Sealed', solid=500)
        entry = lore.MORROW_GATES[0]
        p.scan(entry[0], entry[1], entry[2], (px + turned(300.0, 0.0, yaw)[0], py + turned(300.0, 0.0, yaw)[1], None), True, 'Sealed')
        p.site('Sealed Vault %d' % n, px, py, 1, ',mw_seal%d,' % n)
        front = turned(250.0, 0.0, yaw)
        p.relic('Sealed Vault %d Cache' % n, (px + front[0], py + front[1], p.g.at(px, py) + 110), ',mw_sealgift%d,' % n,
                'The vault held a depot\'s winter store. Divinity +80.', ',mw_seal%d,' % n, divinity=80.0, mesh='SM_HN_Cache', scale=1.5)


# ---------------------------------------------------------------- the Morning

def morning(p):
    """Maren's mind: the kitchen on its island, the Long Hall in the air, the field, and the crest as she remembers it,
    in a row along x 1.5 km north of the dam. Its Rime doors (MorrowRoom1-2) open as she sits with the memories; the
    walk to the crest (MorrowWay) shows when the third is sat with."""
    z0 = INNER_FLOOR
    kx, ky = cm(*plan.KITCHEN)
    p.mesh('Kitchen Island', 'SM_ON_Island', (kx, ky, z0 - 40), 0.0, (1.25, 1.25, 1.0), 'Morning')
    p.mesh('Kitchen', 'SM_ON_Kitchen', (kx, ky, z0 + 5), 0.0, 1.0, 'Morning')
    p.light('Kitchen Lamp', (kx, ky, z0 + 230), LAMP, 900, 1100, 'Morning')
    p.light('Kitchen Window', (kx, ky + 500, z0 + 180), DAWN, 700, 900, 'Morning')
    sx, sy = cm(*plan.INNER_STILL)
    # The Morning's Still Point: a checkpoint without the valley's ring of stones (it stands in her kitchen).
    still = p.spawn('BP_Checkpoint', 'Still Point The Morning', (sx, sy, z0 + 110), folder='Still Points', Radius=500.0, Objective=lore.QUEST_MORNING)
    still.set_editor_property('Until', ',unrisen,')
    p.stills.append((sx, sy))
    p.marks['Still Point The Morning'] = (sx, sy, z0 + 110)
    p.marker('Morning Arrival', (sx, sy, z0 + 120), 'MorrowInner', 'Morning')
    chair, door, glider = lore.MEMORIES
    for key, mesh, (x, y, lift), yaw, scale, narration, give in lore.MEMORIES:
        row = (key, key, mesh, (x, y), yaw, '', '', narration, '', '', give, '', '')
        p.still(row, 'Morning', hold=3.5, radius=260.0 if key != 'Glider' else 600.0)
    p.mesh('Kitchen Rime Door', 'SM_ON_RimeDoor', (kx + 715.0, ky, z0 + 5), 0.0, 1.0, 'Morning', tags=('MorrowRoom1',))
    # The Long Hall: seven lengths of 8 m in the air from the kitchen's door; the fourth has his door.
    hall0 = (plan.HALL[0] - plan.HALL_HALF[0]) * M
    for k in range(7):
        x = hall0 + (k * 8.0 + 4.0) * M
        p.mesh('Hall %d' % k, 'SM_ON_Hall1' if k == 3 else 'SM_ON_Hall0', (x, 0.0, z0 + 5), 0.0, 1.0, 'Morning')
        p.light('Hall Lamp %d' % k, (x, 0.0, z0 + 250), LAMP, 500, 700, 'Morning')
    end = (plan.HALL[0] + plan.HALL_HALF[0]) * M
    p.mesh('Hall Rime Door', 'SM_ON_RimeDoor', (end - 40.0, 0.0, z0 + 5), 0.0, (1.0, 2.6, 1.25), 'Morning', tags=('MorrowRoom2',))
    for k, (dx, dy) in enumerate(((-1200.0, 80.0), (300.0, -90.0), (1600.0, 60.0))):
        p.enemy(7, 'Hall Shape %d' % k, plan.HALL[0] * M + dx, dy, 871, z0)
    # The field: a wide island of frost in the mist, the walk to it from the hall's end.
    fx, fy, fr = plan.FIELD_IN
    p.mesh('Hall Walk', 'SM_ON_Walk', (end + 400.0, 0.0, z0), 0.0, 1.0, 'Morning')
    p.mesh('Field Island', 'SM_ON_Island', (fx * M, fy * M, z0), 0.0, (fr / 10.0, fr / 10.0, 1.6), 'Morning')
    p.light('Field Glow', (fx * M, fy * M, z0 + 1500), DAWN, 3000, 6000, 'Morning')
    for k, (level, dx, dy) in enumerate(((7, -10.0, 14.0), (7, 8.0, -18.0), (8, 20.0, 10.0), (7, 26.0, -6.0))):
        p.enemy(level, 'Field Shape %d' % k, (fx + dx) * M, (fy + dy) * M, 872, z0)
    # The way to the crest, and the crest as she remembers it: three lengths of the dam on an island, the Unrisen.
    cx, cy, cr = plan.CREST_IN
    edge0, edge1 = fx + fr - 2.0, cx - cr + 2.0
    n = max(1, int(math.ceil((edge1 - edge0) / 9.5)))
    for k in range(n):
        x = edge0 + (k + .5) * (edge1 - edge0) / n
        walk = p.mesh('Way %d' % k, 'SM_ON_Walk', (x * M, 0.0, z0), 0.0, ((edge1 - edge0) / n / 10.0 + .05, 1.0, 1.0), 'Morning', tags=('MorrowWay',))
        walk.set_actor_hidden_in_game(True)
    p.mesh('Crest Island', 'SM_ON_Island', (cx * M, cy * M, z0), 0.0, (cr / 10.0, cr / 10.0, 1.3), 'Morning')
    for k, y in enumerate((-24.0, 0.0, 24.0)):
        p.mesh('Remembered Dam %d' % k, 'SM_ON_Dam0', ((cx + 8.0) * M, y * M, z0 + 15), 0.0, 1.0, 'Morning')
    p.enemy(9, 'The Unrisen', (cx - 2.0) * M, cy * M, 873, z0)
    p.encounter('The Unrisen', (cx - 2.0) * M, cy * M, 873, ',mw_still,', lore.MESSAGES['still'], lore.QUEST_SIT, z=z0)
    kneel = ('Unrisen', 'The Unrisen', 'SM_OP_Unrisen', (cx - 2.0, cy), 180, '', '', '', '', '', ',unrisen,', '', '')
    p.still(kneel, 'Morning', show=',mw_still,', hide=',unrisen,', pages=[line for _, line in lore.STAGE], step=lore.STAGE_STEP, key='MarenStage',
            radius=900.0)
    p.light('Unrisen Light', ((cx - 2.0) * M, cy * M, z0 + 450), (1.0, .82, .55), 5000, 3000, 'Morning')


# ---------------------------------------------------------------- the valley between the set pieces

SAFE = ((plan.CHAPEL, 55.0), (plan.MILL, 75.0), (plan.BENCH, 30.0))
PATROLS = ((1, 1, 2), (2, 2), (1, 3), (2, 3), (3, 4), (2, 4))


def along(points, step, start):
    out, carry = [], start
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        length = math.hypot(bx - ax, by - ay)
        heading = math.atan2(by - ay, bx - ax)
        while carry < length:
            out.append((ax + (bx - ax) * carry / length, ay + (by - ay) * carry / length, heading))
            carry += step
        carry -= length
    return out


def life(p):
    """The Frost Guard on the valley's roads: a patrol every 85 m or so, harder toward the dam. Seeded."""
    rng = random.Random(8)
    made = 0
    for row in lore.PEOPLE:
        p.solids.append((row[5][0] * M, row[5][1] * M, 450.0))
    for name, kind, half, points in plan.PATHS:
        for k, (x, y, heading) in enumerate(along(points, 85.0, 40.0)):
            if any(math.hypot(x - sx, y - sy) < r for (sx, sy), r in SAFE) or plan.in_gorge(x, y, 8.0):
                continue
            hard = min(len(PATROLS) - 1, max(0, int((x + 520.0) / 140.0)))
            pack(p, 'Patrol %s %d' % (name, k), x * M, y * M, rng.choice(PATROLS[max(0, hard - 1):hard + 1]), 0, 500)
            made += 1
    p.life = {'patrols': made}


# ---------------------------------------------------------------- people

def person(p, row):
    key, speaker, mesh, voice, kind, (x, y), yaw = row[:7]
    show, hide, greeting, topics, give, quest, reward = row[7:]
    pages = lore.conversation_pages(row)
    starts, first = [], len(greeting)
    for _, answer in topics:
        starts.append(first)
        first += len(answer)
    px, py = cm(x, y)
    z = p.g.at(px, py)
    if key == 'Maren':
        z = (plan.CREST_Z + .15) * M
    npc = p.spawn('BP_NPC', 'Person ' + key, (px, py, z), None, 'People', Speaker=speaker, Key=key,
                  Pages='|'.join(wrap(page) for page in pages), Asks='|'.join(label for label, _ in topics), Starts='|'.join(str(s) for s in starts),
                  Greet=len(greeting), Show=show, Hide=hide, Give=give, Quest=quest, RewardDivinity=float(reward.get('divinity', 0.0)),
                  RewardHeal=bool(reward.get('heal', False)), Note=reward.get('note', ''), Face=kind in ('human', 'robot'), Bob=0.0)
    npc.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    body, shape, view = component(npc, 'Body'), component(npc, 'Shape'), component(npc, 'Look')
    for name in ('Lower', 'Upper', 'Head'):
        part = component(npc, name)
        if part:
            part.set_static_mesh(None)
    shown = 'MISSING'
    if kind == 'human':
        built = next((made for made in (asset(path, True) for path in LOOKS.get(mesh, ())) if made is not None), None)
        if built is not None and view is not None:
            view.set_relative_scale3d(unreal.Vector(1, 1, 1))
            view.set_child_actor_class(built.generated_class())
            if body:
                body.set_skinned_asset_and_update(None, True)
            if shape:
                shape.set_static_mesh(None)
            shown = built.get_name()
    else:
        if view:
            view.set_child_actor_class(None)
        if body:
            body.set_skinned_asset_and_update(None, True)
        figure = mesh_asset(mesh)
        if shape and figure:
            shape.set_static_mesh(figure)
            shown = figure.get_name()
    p.people.append((key, shown))
    for k in range(len(pages)):
        title = lore.person_key(key, k)
        voice_asset = asset(VOICES + '/' + voice_name(title), True)
        if voice_asset is not None:
            p.spawn('BP_LogVoice', 'Voice ' + title, base.VOICE_SPOT, None, 'Voices', Title=title, Voice=voice_asset)
        else:
            p.unvoiced.append(title)
    return npc


def people(p):
    p.people, p.unvoiced = [], []
    for row in lore.PEOPLE:
        person(p, row)


# ---------------------------------------------------------------- passes

ATTACHED = ('Pilgrim\'s Satchel', 'The Lull\'s Heart', 'The Icecutter\'s Blade', 'Frost Cache')


def scans(p):
    for category, title, body, (x, y, z), important in lore.MORROW_SCANS:
        if title in ATTACHED:
            continue
        p.scan(category, title, body, (x * M, y * M, z if z is not None or x <= INNER_X else INNER_FLOOR + 150), important)


def voices(p):
    for category, title, body in lore.morrow_entries() + [('Story',) + tuple(lore.ARRIVAL_LINE), ('Story',) + tuple(lore.MORNING_LINE)]:
        voice = asset(VOICES + '/' + voice_name(title), True)
        if voice is None:
            p.unvoiced.append(title)
            continue
        p.spawn('BP_LogVoice', 'Voice ' + title, base.VOICE_SPOT, None, 'Voices', Title=title, Voice=voice, Image=asset('/Game/UI/Log/' + image_name(title), True))
    for title, text, speaker, kind in lore.voiced_lines():
        voice = asset(VOICES + '/' + voice_name(title), True)
        if voice is None:
            p.unvoiced.append(title)
            continue
        p.spawn('BP_LogVoice', 'Voice ' + title, base.VOICE_SPOT, None, 'Voices', Title=title, Voice=voice)


def tutorials(p):
    for index, (message, (x, y), scale) in enumerate(lore.MORROW_TUTORIALS):
        px, py = x * M, y * M
        p.spawn('BP_TutorialTrigger', 'Tutorial %02d' % (index + 1), (px, py, p.floor(px, py) + 160), scale, 'Tutorial', Message=message)


def sound_scape(p):
    """The valley's dawn everywhere, the Lull's hum by the Hold (which stops with it: tags MorrowScar, MorrowHush), the
    stillness of the Morning (Tools/build_physis_morrow_audio.py amb, then morrow:audio)."""
    placed = []

    def ambient(label, sounds, place_, radius, volume, tags=()):
        wave = next((asset(path, True) for path in sounds if asset(path, True) is not None), None)
        if wave is None:
            return
        actor = sub().spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(*place_))
        actor.set_actor_label('Scene Sound ' + label)
        actor.set_folder_path(FOLDER + '/Sound')
        comp = actor.get_component_by_class(unreal.AudioComponent)
        comp.set_editor_property('sound', wave)
        comp.set_editor_property('volume_multiplier', volume)
        if radius:
            comp.set_editor_property('override_attenuation', True)
            settings = comp.get_editor_property('attenuation_overrides')
            settings.set_editor_property('falloff_distance', radius)
            settings.set_editor_property('attenuation_shape_extents', unreal.Vector(radius * .3, 0, 0))
            comp.set_editor_property('attenuation_overrides', settings)
        else:
            comp.set_editor_property('allow_spatialization', False)
        if tags:
            actor.set_editor_property('tags', list(tags))
        p.note(actor)
        placed.append('%s (%s)' % (label, wave.get_name()))
    ambient('Valley', (MORROW + '/Audio/S_Amb_Morrow', '/Game/Grove/Audio/S_Amb_Grove', '/Game/Grove/Audio/S_Amb_Lake'), (0, 0, 3000), 0, .45)
    ambient('Lull', (MORROW + '/Audio/S_Amb_Lull', '/Game/Halcyon/Audio/S_Amb_HeldSea'), (plan.HOLD[0] * M, plan.HOLD[1] * M, plan.CREST_Z * M + 500), 14000,
            .7, ('MorrowScar', 'MorrowHush'))
    ambient('Morning', (MORROW + '/Audio/S_Amb_Morning',), (plan.HALL[0] * M, 0, INNER_FLOOR + 300), 22000, .7)
    return placed


def frost(p):
    """Everything this scenario placed wears its frosted twins (physis_morrow_tools.regrade)."""
    swapped = 0
    for actor in sub().get_all_level_actors():
        folder = str(actor.get_folder_path())
        if folder == FOLDER or folder.startswith(FOLDER + '/'):
            swapped += T.regrade(actor)
    return swapped


def arrival_off():
    for actor in sub().get_all_level_actors():
        if actor.get_class().get_name() == 'BP_Awakening_C':
            actor.set_editor_property('TestArrival', False)


def place(ground, save=True):
    base.MISSING.clear()
    base.open_level(LEVEL)
    removed = base.clear()
    p = Place(ground)
    chapel(p)
    orchard(p)
    mill(p)
    gorge(p)
    square(p)
    school(p)
    field(p)
    telegraph(p)
    dam(p)
    icehouse(p)
    sealed(p)
    morning(p)
    life(p)
    people(p)
    scans(p)
    voices(p)
    tutorials(p)
    rays = base.divinity_rays(p)
    sounds = sound_scape(p)
    frosted = frost(p)
    arrival_off()
    if save:
        base.save_level(LEVEL)
    return {'level': LEVEL, 'removed': removed, 'placed': p.count, 'enemies': p.enemies, 'rays': rays, 'sounds': sounds, 'people': p.people,
            'stilled': p.stilled, 'unset': p.unset, 'unvoiced': len(p.unvoiced), 'frosted_slots': frosted, 'missing_assets': sorted(base.MISSING)[:60],
            'missing_count': len(base.MISSING), 'life': getattr(p, 'life', None), 'marks': {name: [round(v) for v in spot] for name, spot in p.marks.items()}}


# ---------------------------------------------------------------- the Center's sanctum current

def portal():
    """The current to Morrow in the Center's sanctum, shown once the Cantor has fallen: a targeted spawn into
    L_CenterOfTheUniverse that replaces only its own earlier actors (labels 'Morrow Current...')."""
    base.open_level(CENTER_LEVEL)
    dirty = [pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them before morrow:portal' % ', '.join(dirty))
    actors = sub()
    removed = 0
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith('Morrow Current'):
            actors.destroy_actor(actor)
            removed += 1
    current = actors.spawn_actor_from_class(cls('BP_MorrowCurrent'), unreal.Vector(*PORTAL))
    current.set_actor_label('Morrow Current')
    current.set_folder_path('Center/Morrow')
    props(current, Need=',cantor,', Dest=1, Radius=180.0)
    back = actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*RETURN))
    back.set_actor_label('Morrow Current Return')
    back.set_folder_path('Center/Morrow')
    back.set_editor_property('tags', ['MorrowReturn'])
    arrival_off()
    base.save_level(CENTER_LEVEL)
    return {'level': CENTER_LEVEL, 'current': list(PORTAL), 'return': list(RETURN), 'removed': removed}
