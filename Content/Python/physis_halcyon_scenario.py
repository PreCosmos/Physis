"""Gameplay for level 6, Halcyon, the Drowned Harbour (GAME_ROADMAP.md "Level 6"). Still Points, the people, the
Clocktower, the traces (the Harbour Bridge, the Drowned Quarter's catwalks, the past's stairs to the harbourmaster's
roof, the foreman's cab and the keeper's lamp, the library's shelves), the three echoes, the Mole and the Held Sea, the
Sea Gate, the Bastion and the Keel, side requests, caches, sealed vaults, the Tide Guard by region, Divinity Rays,
tutorials and voices. Run through `halcyon:scenario` (place) and `halcyon:portal` (the Center's temple current).

Positions are plan metres (physis_halcyon_plan: x north, y east); Place's methods take centimetres. Everything placed
here is labelled 'Scene ...' in the outliner folder HalcyonScene (the level build owns the folder Halcyon).

Progress tokens (BP_Physis Flags):
  ,halcyon, ,at_halcyon,  arrived / saves load here     ,kairos_h,  Kairos met     ,trace,  the Clocktower
  ,ha_line1, ,ha_line2, ,ha_line3,  the echoes     ,ha_gate,  the Sea Gate opens     ,keel,  the Keel falls
  ,marr,  the Commodore, in person     ,aug_agility7, then ,halcyon_done,  Kairos afterwards
  side requests ,petra_h, ,shelf1-3, ,shelves, ,ledger, ,logbook,;  caches ,ha_cache1-5,;  seals ,ha_seal1-2,
  augmentations ,aug_hp9, ,aug_katana7, ,aug_pistol6, ,aug_defense7, ,aug_agility7,
Encounter rooms 601-699. Tags for BP_HalcyonDirector: HalcyonScar (hidden once the Keel falls: the Held Sea, the forced
light), HalcyonBloom (shown then: the footbridge over the Breach). Markers: TargetPoint tags HalcyonArrival (here) and
HalcyonReturn (in the Center).

This module stands on the Grove's scenario (physis_grove_scenario: the Place class and its passes), loaded a second
time under another name with Halcyon's folder, meshes, voices and Still Point rule put in its globals.
"""
import importlib.util
import math
import pathlib
import random

import unreal

import physis_halcyon_lore as lore
import physis_halcyon_plan as plan
import physis_gameplay_tools as game
from physis_lore import image_name, voice_name

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
_spec = importlib.util.spec_from_file_location('physis_halcyon_base', ROOT / 'Content/Python/physis_grove_scenario.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

HALCYON = '/Game/Halcyon'
MESHES = HALCYON + '/Meshes'
VOICES = HALCYON + '/Audio/Voice'
LEVEL = '/Game/Levels/L_Halcyon'
CENTER_LEVEL = '/Game/Levels/L_CenterOfTheUniverse'
FOLDER = 'HalcyonScene'
M = 100.0
SILVER = (.78, .84, .95)
AMBER = (1.0, .55, .12)
FORCED = (1.0, .12, .7)
LAMP = (1.0, .8, .5)
TRACE_MATERIAL = HALCYON + '/Materials/M_HA_Trace'
# The Center: the temple's top tier, 16 m north-west of the Heartbloom (the Conclave's current is north, Earth's east,
# Arche's west; south is the sanctum's Still Point); she comes back 5 m short of it.
TEMPLE = (76000.0, 0.0)
SANCTUM = 3400.0 + 600.0
PORTAL = (TEMPLE[0] + 1131.0, TEMPLE[1] - 1131.0, SANCTUM + 35.0)
RETURN = (TEMPLE[0] + 778.0, TEMPLE[1] - 778.0, SANCTUM + 120.0)
# The people built as MetaHumans, the first of each that exists: Kairos and Petra are the Conclave's own; Commodore
# Marr's is hers (physis_earth_people.py, 2026-11-19), with Rhea's figure standing in until it is assembled.
LOOKS = {'Kairos': ('/Game/Conclave/People/Kairos/BP_Kairos',), 'Petra': ('/Game/Conclave/People/Petra/BP_Petra',),
         'Marr': ('/Game/Conclave/People/Marr/BP_Marr', '/Game/Conclave/People/Rhea/BP_Rhea')}


def mesh_asset(name):
    """A mesh by its name alone: Halcyon's own (SM_H*), the Conclave's (SM_C*), a scan (SM_GS_) or the Grove's."""
    if name.startswith('/'):
        return base.asset(name)
    if name.startswith('SM_H'):
        return base.asset(MESHES + '/' + name)
    if name.startswith('SM_C'):
        return base.asset('/Game/Conclave/Meshes/' + name)
    if name.startswith('SM_GS_'):
        return base.asset('/Game/Grove/Scans/' + name)
    return base.asset('/Game/Grove/Meshes/' + name)


base.FOLDER, base.LEVEL, base.VOICES, base.STILL_UNTIL, base.mesh_asset = FOLDER, LEVEL, VOICES, ',keel,', mesh_asset
cm, turned, component, props, wrap, asset, cls, sub = base.cm, base.turned, base.component, base.props, base.wrap, base.asset, base.cls, base.sub


class Place(base.Place):
    def __init__(self, ground):
        super().__init__(ground)
        self.traces = []

    def floor(self, x, y):
        return max(self.g.at(x, y), 0.0)

    def ok(self, x, y, clear, still):
        mx, my = x / M, y / M
        if plan.rim(mx, my) > .9 or plan.in_sea(mx, my, 3.0) or plan.in_breach(mx, my, 3.0):
            return False
        if any(math.hypot(x - sx, y - sy) < r + clear for sx, sy, r in self.solids):
            return False
        return not (still and any(math.hypot(x - sx, y - sy) < still for sx, sy in self.stills))

    def enemy(self, level, label, x, y, room=0, z=None):
        mesh, health, scale, hover, entry, kind = lore.HALCYON_ENEMIES[level]
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
        self.reskin(actor, mesh)
        self.tag(actor, entry, place, label)
        self.enemies += 1
        return actor

    def trace(self, label, mesh, place, yaw=0.0, pitch=0.0, scale=1.0, give='', done='', need=',trace,', hide='', range_m=40.0, folder='Traces'):
        """BP_Trace: `mesh` standing at `place` (cm, its pivot) as it stood in the past. It shows, and bears her weight,
        only while she reads within range_m of it (Tools/blueprint_logic/halcyon_logic.py)."""
        actor = self.spawn('BP_Trace', label, place, None, folder, Need=need, Hide=hide, Give=give, Done=done, Range=range_m * M)
        actor.set_actor_rotation(unreal.Rotator(0, pitch, yaw), False)
        shape = component(actor, 'Shape')
        figure = mesh_asset(mesh)
        shape.set_static_mesh(figure)
        trace_look = asset(TRACE_MATERIAL, True)
        for slot in range(shape.get_num_materials()):
            shape.set_material(slot, trace_look)
        size = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        shape.set_relative_scale3d(unreal.Vector(*size))
        shape.set_editor_property('cast_shadow', False)
        self.traces.append(label)
        return actor


def pack(p, label, x, y, levels, room=0, spread=700.0, z=None):
    return base.pack(p, label, x, y, levels, room, spread, z)


def cache(p, n, title, x, y, z=None, need=''):
    token = ',ha_cache%d,' % n
    z = p.floor(x, y) if z is None else z
    p.relic('Tide Cache %d' % n, (x, y, z + 110), token, lore.MESSAGES['cache'], need=need, divinity=40.0, mesh='SM_HN_Cache', scale=1.3)
    p.light('Cache Glow %d' % n, (x, y, z + 160), SILVER, 1300, 500, 'Items')
    p.site(title, x, y, 2, token)


def dress(p, label, rows, folder, origin=(0.0, 0.0), yaw0=0.0):
    """Props round a point: rows of (mesh, x, y, yaw, scale, solid cm) in metres, turned by yaw0."""
    for k, (mesh, x, y, yaw, scale, solid) in enumerate(rows):
        dx, dy = turned(x * M, y * M, yaw0)
        px, py = origin[0] * M + dx, origin[1] * M + dy
        p.mesh('%s %d' % (label, k), mesh, (px, py, p.g.at(px, py) - 3), yaw0 + yaw, scale, folder, solid=solid)


# ---------------------------------------------------------------- the regions

def garden(p):
    gx, gy = cm(*plan.GARDEN)
    floor = p.g.at(gx, gy)
    p.spawn('BP_HalcyonCurrent', 'Current Home', (gx, gy, floor + 25), None, 'Garden', Need='', Dest=2, Radius=180.0)
    p.solids.append((gx, gy, 500))
    p.light('Garden Glow', (gx, gy, floor + 600), SILVER, 9000, 2800, 'Garden')
    sx, sy = cm(*plan.GARDEN_STILL)
    p.check('Cliff Garden', sx, sy, lore.QUEST_ARRIVE, 800.0)
    p.marks['Arrival'] = p.at(sx, sy, 120)
    p.marker('Arrival', p.marks['Arrival'], 'HalcyonArrival', 'Garden')
    dress(p, 'Garden', (('SM_HN_Crate', 10.0, -14.0, 20.0, .8, 100), ('SM_HN_Lamp', -8.0, 12.0, 0.0, 1.0, 40),
                        ('SM_HN_Lamp', 12.0, 14.0, 0.0, 1.0, 40), ('SM_GV_Bush', -14.0, -8.0, 0.0, 1.2, 0), ('SM_GV_Birch', 18.0, -20.0, 0.0, .8, 150)),
          'Garden', plan.GARDEN)
    cache(p, 1, 'Cliff Garden Cache', *cm(-470.0, 4.0))


def high_street(p):
    pack(p, 'High Street', *cm(-424.0, 66.0), (1, 1, 2), 601, 600)
    p.encounter('High Street', *cm(-424.0, 66.0), 601, ',ha_road,', 'The Tide Guard\'s patrol is down. The street north is clear.')
    pack(p, 'Upper Town', *cm(-352.0, 44.0), (1, 2), 0, 600)
    pack(p, 'Library Lane', *cm(-372.0, 140.0), (2, 2, 1), 0, 700)


CAMP = (('SM_GN_Shelter', -16.0, -16.0, 30.0, 1.0, 450), ('SM_GN_Shelter', -20.0, 10.0, -10.0, 1.0, 450), ('SM_HN_Crate', 6.0, -12.0, 15.0, 1.0, 100),
        ('SM_HN_Crate', 7.4, -11.0, 40.0, .8, 90), ('SM_GN_Canister', 9.0, 10.0, 0.0, 1.0, 80), ('SM_HN_Lamp', 12.0, 4.0, 0.0, 1.0, 40),
        ('SM_HN_Lamp', 12.0, -6.0, 0.0, 1.0, 40), ('SM_HN_Bollard', 13.0, 0.0, 0.0, 1.0, 40), ('SM_HN_Crate', -4.0, 22.0, 70.0, 1.0, 100))


def signal(p):
    sx, sy = plan.SIGNAL
    p.check('Signal House', *cm(*plan.SIGNAL_STILL), 'The Signal House. Speak to Kairos.')
    hx, hy = cm(sx - 12.0, sy)
    p.mesh('Signal House', 'SM_HN_SignalHouse', (hx, hy, p.g.at(hx, hy) - 20), 0.0, 1.0, 'Signal', solid=1100)
    dress(p, 'Camp', CAMP, 'Signal', plan.SIGNAL)
    for k, (x, y) in enumerate(((12.0, 4.0), (12.0, -6.0))):
        lx, ly = cm(sx + x, sy + y)
        p.light('Camp Lamp %d' % k, (lx + 55, ly, p.g.at(lx, ly) + 380), LAMP, 2400, 1400, 'Signal')
    for row in lore.PEOPLE:
        if row[5][0] < -250.0:
            p.solids.append((row[5][0] * M, row[5][1] * M, 250))


def clocktower(p):
    cx, cy = cm(*plan.CLOCK)
    floor = p.g.at(cx, cy)
    yaw = math.degrees(math.atan2(plan.BREACH_CROSS_Y - plan.CLOCK[1], plan.BRIDGE_SOUTH[0] - plan.CLOCK[0]))
    p.mesh('Clocktower', 'SM_HN_Clocktower', (cx, cy, floor - 20), yaw, 1.0, 'Clock', solid=600)
    dx, dy = turned(520.0, 0.0, yaw)
    p.switch('The Clocktower', (cx + dx, cy + dy, floor), yaw, 'SM_HN_Bollard', False, None, 'Clock', Need=',kairos_h,', Give=',trace,',
             Denied=lore.MESSAGES['clock_denied'], Done=lore.CLOCK_DONE)
    p.light('Clock Glow', (cx + dx, cy + dy, floor + 500), SILVER, 2600, 1400, 'Clock')
    # The morning before the wave: three echoes in the street at the tower's foot, there for whoever reads.
    for k, (ex, ey, yaw_) in enumerate(((7.0, -5.0, 150.0), (9.0, 6.0, 210.0), (-6.0, 8.0, 300.0))):
        tx, ty = cx + ex * M, cy + ey * M
        p.trace('Clock Street Echo %d' % k, 'SM_HP_Echo%d' % (k % 3), (tx, ty, p.g.at(tx, ty)), yaw_, folder='Clock')
    pack(p, 'Clock Lane', *cm(-246.0, 48.0), (1, 1), 0, 500)


def breach(p):
    """The Harbour Bridge, in the past: 32 m over the 26 m Breach, its deck tilted to meet both rims. The barrier she
    remembers: crossed only while she reads. The footbridge the town lays after the Keel (HalcyonBloom) is a second
    way, at y -40."""
    my = plan.BREACH_CROSS_Y * M
    mx = plan.breach_x(plan.BREACH_CROSS_Y) * M
    south, north = plan.BRIDGE_SOUTH[0] * M - 300.0, plan.BRIDGE_NORTH[0] * M + 300.0
    zs, zn = p.g.at(south, my), p.g.at(north, my)
    pitch = math.degrees(math.atan2(zn - zs, north - south))
    p.trace('Harbour Bridge', 'SM_HN_Bridge', (mx, my, (zs + zn) / 2 + 2.0), 0.0, pitch, done=lore.MESSAGES['bridge'], give=',ha_bridge,', range_m=45.0,
            folder='Breach')
    for k, x in enumerate((south - 300.0, north + 300.0)):
        p.light('Bridge Abutment %d' % k, (x, my, p.g.at(x, my) + 300), SILVER, 1500, 900, 'Breach')
    # The footbridge after the Keel: three planked spans at the rims' height, tagged HalcyonBloom.
    fy = -40.0 * M
    fx = plan.breach_x(-40.0) * M
    fs, fn = p.g.at(fx - plan.BREACH_RIM * M - 200.0, fy), p.g.at(fx + plan.BREACH_RIM * M + 200.0, fy)
    for k in range(3):
        t = (k - 1) * 900.0
        z = (fs + fn) / 2 + (fn - fs) * t / 2800.0
        span = p.mesh('Footbridge %d' % k, 'SM_HN_Catwalk', (fx + t, fy, z + 10.0), 0.0, (1.02, 1.3, 1.0), 'Breach', tags=('HalcyonBloom',))
        span.set_actor_hidden_in_game(True)
    p.light('Breach Scar', (mx, my, zs + 300), FORCED, 1600, 1600, 'Breach', ('HalcyonScar',))


def steps(p):
    ux, uy = cm(*plan.STEPS)
    p.check('Market Steps', ux, uy, lore.QUEST_ECHOES)
    dress(p, 'Market', (('SM_HN_Crate', 8.0, 6.0, 10.0, 1.0, 100), ('SM_HN_Crate', 9.0, 7.6, 60.0, .9, 90), ('SM_HN_Bollard', -9.0, 8.0, 0.0, 1.0, 40),
                        ('SM_HN_Bollard', -9.0, -8.0, 0.0, 1.0, 40), ('SM_HN_Lamp', 12.0, -10.0, 0.0, 1.0, 40), ('SM_GN_Canister', -7.0, 12.0, 0.0, 1.0, 80)),
          'Market', plan.STEPS)
    for k, (level, x, y) in enumerate(((2, -40.0, 30.0), (2, -36.0, -14.0), (1, -48.0, 8.0))):
        p.enemy(level, 'Steps %d' % k, x * M, y * M, 602)
    p.encounter('Market Steps', -42.0 * M, 8.0 * M, 602, ',ha_steps,', 'The Market Steps are clear.')
    for label, (x, y), levels in (('Quarter Lane', (-40.0, -84.0), (1, 2)), ('Cannery Row', (-30.0, 110.0), (1, 1, 3)), ('Mole Road', (40.0, 30.0), (2, 3))):
        pack(p, label, *cm(x, y), levels, 0, 700)
    cache(p, 2, 'Market Cache', *cm(-60.0, 60.0))


def quarter(p):
    """The Drowned Quarter: past catwalks from the shore out over the flooded streets to the harbourmaster's office,
    and the office's old outside stair up to its roof, where she stands."""
    qx, qy = cm(*plan.QUARTER_STILL)
    p.check('Drowned Quarter', qx, qy, 'The Drowned Quarter. The harbourmaster\'s office stands in the water; read the way out to it.')
    ox, oy = cm(*plan.HARBOURMASTER)
    base_z = p.g.at(ox, oy) - 20.0
    office_yaw = math.degrees(math.atan2(qy - oy, qx - ox))      # its front toward the shore
    p.mesh('Harbourmaster\'s Office', 'SM_HN_Office', (ox, oy, base_z), office_yaw, 1.0, 'Quarter', solid=700)
    roof = base_z + 720.0
    # Catwalks: from the shore (the first dry ground on the line from the Still Point) to a point 13.5 m off the
    # office's flank; from there one past flight climbs straight at the flank to its parapet's top (0.85 m above the roof).
    a = math.atan2(oy - qy, ox - qx)
    ux, uy = math.cos(a), math.sin(a)
    d = 0.0
    while p.g.at(qx + ux * d, qy + uy * d) > 40.0 and d < 30000:
        d += 100.0
    shore = (qx + ux * (d - 300.0), qy + uy * (d - 300.0))
    perp = (-uy, ux)
    if math.hypot(ox + perp[0] * 1355.0 - shore[0], oy + perp[1] * 1355.0 - shore[1]) > math.hypot(ox - perp[0] * 1355.0 - shore[0], oy - perp[1] * 1355.0 - shore[1]):
        perp = (uy, -ux)          # the flank nearer the shore
    end = (ox + perp[0] * 1355.0, oy + perp[1] * 1355.0)
    length = math.hypot(end[0] - shore[0], end[1] - shore[1])
    heading = math.degrees(math.atan2(end[1] - shore[1], end[0] - shore[0]))
    count = max(1, int(math.ceil(length / 880.0)))
    for k in range(count):
        t = (k + .5) / count
        x, y = shore[0] + (end[0] - shore[0]) * t, shore[1] + (end[1] - shore[1]) * t
        p.trace('Quarter Catwalk %d' % (k + 1), 'SM_HN_Catwalk', (x, y, 90.0), heading, folder='Quarter')
    parapet = base_z + 805.0
    climb = math.degrees(math.atan2(-perp[1], -perp[0]))
    p.trace('Office Stair', 'SM_HN_Flight', (ox + perp[0] * 885.0, oy + perp[1] * 885.0, 90.0), climb, scale=(1.0, 1.0, (parapet - 90.0) / 600.0),
            folder='Quarter')
    top = (ox + perp[0] * 415.0, oy + perp[1] * 415.0, parapet)
    echo(p, lore.ECHOES[0], (ox, oy, roof))
    p.light('Harbourmaster Lamp', (ox, oy, roof + 250), SILVER, 2200, 1200, 'Quarter')
    for k, (level, dx, dy) in enumerate(((5, -2400.0, 400.0), (2, -2600.0, -700.0), (1, -2200.0, 900.0))):
        p.enemy(level, 'Quarter Guard %d' % k, qx + ux * 1800 + dy * -uy * .3, qy + uy * 1800 + dy * ux * .3, 611)
    p.encounter('Quarter Guard', qx + ux * 1800, qy + uy * 1800, 611, ',ha_g1,', lore.MESSAGES['echo_guard'])
    cache(p, 3, 'Quarter Cache', *cm(-50.0, -230.0))
    p.marks['Office stair top'] = top


def yards(p):
    """The Cannery Yards: sheds, the crane on the quay, and the past's two flights up to its cab platform."""
    p.check('Cannery Yards', *cm(*plan.YARDS_STILL), 'The Cannery Yards. The foreman is remembered in his crane; read the stair up to him.')
    yx, yy = plan.YARDS
    for k, (x, y, yaw) in enumerate(((-30.0, -40.0, 90.0), (-30.0, 0.0, 90.0), (10.0, -45.0, 0.0), (-10.0, 46.0, 90.0))):
        sx, sy = cm(yx + x, yy + y)
        p.mesh('Cannery Shed %d' % k, 'SM_HN_Shed', (sx, sy, p.g.at(sx, sy) - 20), yaw, 1.0, 'Yards', solid=1100)
    fx, fy = cm(*plan.FOREMAN)
    cyaw = math.degrees(math.atan2(0.0, 1.0)) + 0.0     # the jib over the water, north
    ground = p.g.at(fx, fy)
    p.mesh('Crane', 'SM_HN_Crane', (fx, fy, ground - 10), cyaw, 1.0, 'Yards', solid=700)
    platform = ground - 10 + 1346.0
    # Flight B climbs +x to the platform's west edge (crane x -1.4 m, y 4.2 m); flight A below it, climbing -x, 2.6 m
    # further out (y 6.8), from the ground to B's foot.
    b_top = (fx - 140.0, fy + 420.0)
    half = (platform - ground) / 2
    p.trace('Crane Flight 2', 'SM_HN_Flight', (b_top[0] - 470.0, b_top[1], ground + half), 0.0, scale=(1.0, 1.0, half / 600.0), folder='Yards')
    # A shares B's span along x, 2.6 m further out; it climbs -x from the ground (its foot under B's top) to a landing
    # beside B's foot.
    p.trace('Crane Flight 1', 'SM_HN_Flight', (b_top[0] - 470.0, fy + 680.0, ground), 180.0, scale=(1.0, 1.0, half / 600.0), folder='Yards')
    echo(p, lore.ECHOES[1], (fx + 150.0, fy + 430.0, platform + 6.0))
    p.light('Crane Cab Light', (fx + 150, fy + 430, platform + 300), SILVER, 2000, 1200, 'Yards')
    for k, (level, dx, dy) in enumerate(((5, -1800.0, -600.0), (4, -2200.0, 800.0), (1, -1400.0, 1300.0))):
        p.enemy(level, 'Yard Guard %d' % k, fx + dx, fy + dy, 621)
    p.encounter('Yard Guard', fx - 1800.0, fy, 621, ',ha_g2,', lore.MESSAGES['echo_guard'])
    cache(p, 4, 'Yards Cache', *cm(yx - 40.0, yy + 70.0))
    pack(p, 'Yards South', *cm(-10.0, 230.0), (3, 4), 0, 700)


def point(p):
    """Lighthouse Point: the lighthouse, and the keeper's outside stair (four past flights up its west side) to the
    gallery, 22 m up, where she stands at the lamp."""
    p.check('Lighthouse Point', *cm(*plan.POINT_STILL), 'Lighthouse Point. The keeper is remembered at the lamp; read the stair up the tower.')
    lx, ly = cm(*plan.LIGHTHOUSE)
    ground = p.g.at(lx, ly)
    p.mesh('Lighthouse', 'SM_HN_Lighthouse', (lx, ly, ground - 10), 0.0, 1.0, 'Point', solid=600)
    gallery = ground - 10 + 2200.0
    # Four flights switching back on the tower's -y side, climbing along y: the odd ones away from the tower (-y),
    # 2.6 m to the west; the even ones toward it, the last ending at the railing's gap (gallery edge, y -4.7 m).
    foot = ground - 10.0
    each = (gallery - foot) / 4
    for k in range(4):
        z = foot + each * k
        if k % 2 == 0:
            place, heading = (lx - 260.0, ly - 1080.0, z), -90.0
        else:
            place, heading = (lx, ly - 940.0, z), 90.0
        p.trace('Lighthouse Flight %d' % (k + 1), 'SM_HN_Flight', place, heading, scale=(1.0, 1.0, each / 600.0), folder='Point')
    echo(p, lore.ECHOES[2], (lx, ly - 250.0, gallery))
    p.relic('Ledger\'s Logbook', (lx + 250.0, ly - 250.0, gallery + 110), ',logbook,', lore.MESSAGES['logbook'], mesh='SM_HN_Logbook', scale=2.0)
    p.light('Lamp Room', (lx, ly, gallery + 250), SILVER, 3000, 1600, 'Point')
    px, py = cm(plan.POINT[0] - 30.0, plan.POINT[1] - 30.0)
    for k, (level, dx, dy) in enumerate(((5, 0.0, 0.0), (3, 600.0, -400.0), (2, -500.0, 500.0))):
        p.enemy(level, 'Point Guard %d' % k, px + dx, py + dy, 631)
    p.encounter('Point Guard', px, py, 631, ',ha_g3,', lore.MESSAGES['echo_guard'])
    cache(p, 5, 'Point Cache', *cm(plan.POINT[0] + 20.0, plan.POINT[1] - 20.0))


def echo(p, row, place):
    key, mesh, _, _, yaw, line, token = row
    p.trace('Echo ' + key, mesh, place, yaw, give=token, done=line, range_m=30.0, folder='Echoes')


def mole(p):
    """The Mole out to the Sea Gate, the Held Sea's ring round the Bastion's rock, and the gate in it."""
    x = plan.MOLE_SOUTH[0] + 6.0
    k = 0
    while x < plan.SEA_GATE[0] - 2.0:
        p.mesh('Mole %02d' % k, 'SM_HN_MoleSlab', (x * M, 0.0, (plan.MOLE_TOP - 4.0) * M), 0.0, 1.0, 'Mole')
        x += 12.0
        k += 1
    p.check('The Mole', *cm(*plan.MOLE_STILL), 'The Mole. The Sea Gate is at its end.', z=plan.MOLE_TOP * M)
    for k, (level, mx, my) in enumerate(((5, 250.0, 0.0), (2, 270.0, 2.0), (1, 290.0, -2.0), (2, 210.0, 1.0))):
        p.enemy(level, 'Mole Guard %d' % k, mx * M, my * M, 641, plan.MOLE_TOP * M)
    p.encounter('Mole Guard', 250.0 * M, 0.0, 641, ',ha_mole,', 'The Mole is clear. The Sea Gate is ahead.', z=plan.MOLE_TOP * M)
    # The Held Sea: water standing in walls 78 m round the Bastion, its face to the rock, a gap for the gate.
    bx, by = cm(*plan.BASTION)
    count = 30
    for k in range(count):
        bearing = 180.0 + k * 360.0 / count
        b = math.radians(bearing)
        x, y = bx + math.cos(b) * plan.HELD_RADIUS * M, by + math.sin(b) * plan.HELD_RADIUS * M
        if k == 0:
            continue    # the Sea Gate stands here
        p.mesh('Held Sea %02d' % k, 'SM_HN_HeldSea', (x, y, -100.0), bearing + 180.0, (1.0, 1.04, 1.0), 'Held Sea', tags=('HalcyonScar',))
        if k % 3 == 0:
            p.light('Held Sea Light %d' % k, (x - math.cos(b) * 300, y - math.sin(b) * 300, 300.0), FORCED, 5000, 2600, 'Held Sea', ('HalcyonScar',))
    gx, gy = cm(*plan.SEA_GATE)
    deck = plan.MOLE_TOP * M
    p.mesh('Sea Gate', 'SM_HN_SeaGate', (gx, gy, deck - 20), 0.0, 1.0, 'Mole')
    p.rise('Sea Gate Door', 'SM_HN_GateDoor', (gx, gy, deck - 10), ',ha_gate,', -1100.0, 0.0, 1.0, 220.0, 'Mole')
    p.require('Sea Gate Lock', (gx - 400.0, gy, deck + 600), (',ha_line1,', ',ha_line2,', ',ha_line3,'), ',ha_gate,', lore.MESSAGES['gate'])
    for sgn in (-1, 1):
        p.light('Sea Gate Lamp %d' % sgn, (gx - 300, gy + sgn * 650, deck + 1100), AMBER, 3000, 1500, 'Mole')
    # Where the gate stands on the rock's side the mole carries on as a causeway to the court.
    x = plan.SEA_GATE[0] + 8.0
    k = 0
    while x < plan.BASTION[0] - plan.ROCK_RADIUS + 4.0:
        p.mesh('Gate Causeway %d' % k, 'SM_HN_MoleSlab', (x * M, 0.0, (plan.MOLE_TOP - 4.0) * M), 0.0, 1.0, 'Mole')
        x += 12.0
        k += 1


WALL_SLOTS = 17


def bastion(p):
    cx, cy = cm(*plan.COURT)
    top = plan.ROCK_TOP * M
    radius = plan.COURT_RADIUS * M
    p.check('Bastion', (plan.BASTION[0] - plan.ROCK_RADIUS + 10.0) * M, 0.0, lore.QUEST_KEEL, z=top)
    for k in range(WALL_SLOTS):
        bearing = 180.0 + k * 360.0 / WALL_SLOTS
        if k == 0:
            continue    # the court's gate, toward the Sea Gate
        b = math.radians(bearing)
        x, y = cx + math.cos(b) * radius, cy + math.sin(b) * radius
        p.mesh('Bastion Wall %02d' % k, 'SM_HN_BastionWall', (x, y, top - 30), bearing, (1.0, 1.0, 1.0), 'Bastion')
    p.mesh('Bastion', 'SM_HN_Bastion', (cx + radius + 900.0, cy, top - 30), 180.0, 1.0, 'Bastion', solid=1500)
    # The Keel, its guard, and the four pumps its shield answers to (the sidearm stops them).
    p.enemy(7, 'Keel', cx + 600.0, cy, 652, top)
    for k, (level, bearing, r) in enumerate(((5, 60.0, 1900.0), (5, 300.0, 1900.0), (1, 120.0, 1500.0), (1, 240.0, 1500.0), (1, 180.0, 1100.0),
                                             (3, 0.0, 2300.0))):
        b = math.radians(bearing)
        p.enemy(level, 'Keel Guard %d' % k, cx + math.cos(b) * r, cy + math.sin(b) * r, 652, top)
    entry = next(row for row in lore.HALCYON_SCANS if row[1] == 'Undertow Pump')
    for k, bearing in enumerate((45.0, 135.0, 225.0, 315.0)):
        b = math.radians(bearing)
        x, y = cx + math.cos(b) * 2300.0, cy + math.sin(b) * 2300.0
        p.target('Undertow Pump %d' % k, 'SM_HN_Pump', (x, y, top), 652, 6, 1.0, entry[:3], bearing + 180.0, 'Bastion', True)
        p.light('Pump Light %d' % k, (x, y, top + 400), FORCED, 2600, 900, 'Bastion', ('HalcyonScar',))
    p.encounter('Keel', cx, cy, 652, ',keel,', lore.MESSAGES['keel'], lore.QUEST_MARR, z=top)
    for k, bearing in enumerate((90.0, 270.0)):
        b = math.radians(bearing)
        p.pickup(0, 'Court Capsule %d' % k, cx + math.cos(b) * 2600.0, cy + math.sin(b) * 2600.0, top)
    p.relic('The Undertow\'s Heart', (cx + 1200.0, cy - 600.0, top + 115), ',aug_hp9,', lore.MESSAGES['heart'], ',keel,', heal=True,
            mesh='SM_CN_LightCache', scale=1.4)
    p.light('Court Forced Light', (cx, cy, top + 1800), FORCED, 16000, 6000, 'Bastion', ('HalcyonScar',))
    p.light('Court Day', (cx, cy, top + 2400), (1.0, .95, .9), 6000, 7000, 'Bastion')


def library(p):
    lx, ly = cm(*plan.LIBRARY)
    floor = p.g.at(lx, ly)
    for k, (x, y, yaw) in enumerate(((-14.0, -10.0, 0.0), (-14.0, 10.0, 0.0), (-4.0, -20.0, 90.0), (-4.0, 20.0, 270.0))):
        hx, hy = cm(plan.LIBRARY[0] + x, plan.LIBRARY[1] + y)
        p.mesh('Library Ruin %d' % k, 'SM_HN_House2', (hx, hy, p.g.at(hx, hy) - 40), yaw, (1.2, 1.4, 1.1), 'Library', solid=700)
    for k in range(3):
        sx, sy = lx + 300.0, ly + (k - 1) * 450.0
        p.trace('Library Shelf %d' % (k + 1), 'SM_HN_Shelf', (sx, sy, p.g.at(sx, sy) - 5), 180.0, give=',shelf%d,' % (k + 1), done=lore.MESSAGES['shelf'],
                range_m=25.0, folder='Library')
    p.require('Library Shelves', (lx, ly, floor + 600), (',shelf1,', ',shelf2,', ',shelf3,'), ',shelves,', lore.MESSAGES['shelves'])
    p.relic('The Reader\'s Knife', (lx - 300.0, ly, floor + 115), ',aug_katana7,', lore.MESSAGES['knife'], ',shelves,', mesh='SM_CN_LightCache', scale=.8)
    p.site('Drowned Library', lx, ly, 0, ',aug_katana7,')
    p.enemy(6, 'Library Harrow', lx + 1800.0, ly - 2200.0, 661)
    p.encounter('Library Harrow', lx + 1800.0, ly - 2200.0, 661, ',ha_harrow,', 'The Harrow is still.')


def sealed(p):
    """Vaults for abilities learned elsewhere: Reweave (from Arche) opens one now; Dissonance is later."""
    for n, ((x, y), ability) in enumerate(((plan.SEALED_WEAVE, ',reweave,'), (plan.SEALED_DISSONANCE, ',dissonance,')), 1):
        px, py = cm(x, y)
        yaw = math.degrees(math.atan2(-py, -px))
        door = p.spawn('BP_AbilitySocket', 'Sealed Vault %d' % n, (px, py, p.g.at(px, py) - 10), None, 'Sealed', Ability=ability, Give=',ha_seal%d,' % n,
                       Radius=900.0, Hold=0.0, Solid=True, Message='The vault\'s seal opens.')
        door.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = p.reskin(door, 'SM_HN_GateDoor')
        if part:
            part.set_relative_scale3d(unreal.Vector(1.0, .3, .32))
            part.set_collision_profile_name('BlockAll')
        back = turned(-480.0, 0.0, yaw)
        p.mesh('Sealed Cell %d' % n, 'SM_HN_Office', (px + back[0], py + back[1], p.g.at(px, py) - 20), yaw, (.55, .55, .55), 'Sealed', solid=500)
        entry = lore.HALCYON_GATES[0]
        p.scan(entry[0], entry[1], entry[2], (px + turned(300.0, 0.0, yaw)[0], py + turned(300.0, 0.0, yaw)[1], None), True, 'Sealed')
        p.site('Sealed Vault %d' % n, px, py, 1, ',ha_seal%d,' % n)
        front = turned(250.0, 0.0, yaw)
        p.relic('Sealed Vault %d Cache' % n, (px + front[0], py + front[1], p.g.at(px, py) + 110), ',ha_sealgift%d,' % n, 'The vault held a pilots\' store. Divinity +80.',
                ',ha_seal%d,' % n, divinity=80.0, mesh='SM_HN_Cache', scale=1.5)


# ---------------------------------------------------------------- the town between the set pieces

SAFE = ((plan.GARDEN, 55.0), (plan.SIGNAL, 75.0), (plan.CLOCK, 30.0))
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
    """The Tide Guard on the town's streets: a patrol every 85 m or so, harder toward the water. Seeded."""
    rng = random.Random(6)
    made = 0
    for row in lore.PEOPLE:
        p.solids.append((row[5][0] * M, row[5][1] * M, 450.0))
    for name, kind, half, points in plan.PATHS:
        for k, (x, y, heading) in enumerate(along(points, 85.0, 40.0)):
            if any(math.hypot(x - sx, y - sy) < r for (sx, sy), r in SAFE) or plan.in_breach(x, y, 8.0):
                continue
            hard = min(len(PATROLS) - 1, max(0, int((x + 520.0) / 130.0)))
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
    if key == 'Marr':
        z = plan.ROCK_TOP * M
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

ATTACHED = ('Ledger\'s Logbook', 'The Undertow\'s Heart', 'The Reader\'s Knife', 'Tide Cache', 'Undertow Pump')


def scans(p):
    for category, title, body, (x, y, z), important in lore.HALCYON_SCANS:
        if title in ATTACHED:
            continue
        p.scan(category, title, body, (x * M, y * M, z), important)


def voices(p):
    for category, title, body in lore.halcyon_entries() + [('Story',) + tuple(lore.ARRIVAL_LINE)]:
        voice = asset(VOICES + '/' + voice_name(title), True)
        if voice is None:
            p.unvoiced.append(title)
            continue
        p.spawn('BP_LogVoice', 'Voice ' + title, base.VOICE_SPOT, None, 'Voices', Title=title, Voice=voice, Image=asset('/Game/UI/Log/' + image_name(title), True))


def tutorials(p):
    for index, (message, (x, y), scale) in enumerate(lore.HALCYON_TUTORIALS):
        p.spawn('BP_TutorialTrigger', 'Tutorial %02d' % (index + 1), p.at(x * M, y * M, 160), scale, 'Tutorial', Message=message)


def sound_scape(p):
    """The harbour everywhere, the Held Sea's roar by the Bastion (which stops with it: tag HalcyonScar), the water
    among the Drowned Quarter's houses (Tools/build_physis_halcyon_audio.py amb, then halcyon:audio)."""
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
    ambient('Sea', (HALCYON + '/Audio/S_Amb_Halcyon', '/Game/Grove/Audio/S_Amb_Lake', '/Game/Arche/Audio/S_Amb_Cistern'), (0, 0, 3000), 0, .5)
    ambient('Held Sea', (HALCYON + '/Audio/S_Amb_HeldSea', '/Game/Grove/Audio/S_Amb_Falls'), (plan.BASTION[0] * M, plan.BASTION[1] * M, 800), 16000, .9,
            ('HalcyonScar', 'HalcyonHush'))
    ambient('Drowned Quarter', (HALCYON + '/Audio/S_Amb_Quarter',), (plan.QUARTER[0] * M, plan.QUARTER[1] * M, 200), 9000, .8)
    return placed


def arrival_off():
    for actor in sub().get_all_level_actors():
        if actor.get_class().get_name() == 'BP_Awakening_C':
            actor.set_editor_property('TestArrival', False)


def place(ground, save=True):
    base.MISSING.clear()
    base.open_level(LEVEL)
    removed = base.clear()
    p = Place(ground)
    garden(p)
    high_street(p)
    signal(p)
    clocktower(p)
    breach(p)
    steps(p)
    quarter(p)
    yards(p)
    point(p)
    mole(p)
    bastion(p)
    library(p)
    sealed(p)
    life(p)
    people(p)
    scans(p)
    voices(p)
    tutorials(p)
    rays = base.divinity_rays(p)
    sounds = sound_scape(p)
    arrival_off()
    raised = p.fit()
    if save:
        base.save_level(LEVEL)
    return {'level': LEVEL, 'removed': removed, 'placed': p.count, 'enemies': p.enemies, 'rays': rays, 'sounds': sounds, 'people': p.people,
            'unset': p.unset, 'unvoiced': len(p.unvoiced), 'traces': len(p.traces), 'raised': raised, 'missing_assets': sorted(base.MISSING)[:60],
            'missing_count': len(base.MISSING), 'life': getattr(p, 'life', None), 'marks': {name: [round(v) for v in spot] for name, spot in p.marks.items()}}


# ---------------------------------------------------------------- the Center's temple current

def portal():
    """The current to Halcyon in the Center's sanctum, shown once the Sunderer has fallen: a targeted spawn into
    L_CenterOfTheUniverse that replaces only its own earlier actors (labels 'Halcyon Current...')."""
    base.open_level(CENTER_LEVEL)
    dirty = [pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them before halcyon:portal' % ', '.join(dirty))
    actors = sub()
    removed = 0
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith('Halcyon Current'):
            actors.destroy_actor(actor)
            removed += 1
    current = actors.spawn_actor_from_class(cls('BP_HalcyonCurrent'), unreal.Vector(*PORTAL))
    current.set_actor_label('Halcyon Current')
    current.set_folder_path('Center/Halcyon')
    props(current, Need=',sunderer,', Dest=1, Radius=180.0)
    back = actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*RETURN))
    back.set_actor_label('Halcyon Current Return')
    back.set_folder_path('Center/Halcyon')
    back.set_editor_property('tags', ['HalcyonReturn'])
    arrival_off()
    base.save_level(CENTER_LEVEL)
    return {'level': CENTER_LEVEL, 'current': list(PORTAL), 'return': list(RETURN), 'removed': removed}
