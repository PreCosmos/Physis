"""Gameplay for level 7, Hesper, the City of One Voice (GAME_ROADMAP.md "Level 7"). Still Points, the people, the
Tuning Court, the Choir Wall, the Unison veils, gates and shells (BP_Unison), the three bells, the Nave, the Choir Gate,
the Concord and the Cantor, side requests, caches, sealed vaults, the Choir and Arche's animals by region, Divinity
Rays, tutorials and voices. Run through `hesper:scenario` (place) and `hesper:portal` (the Center's sanctum current).

Positions are plan metres (physis_hesper_plan: x north, y east); Place's methods take centimetres. Everything placed
here is labelled 'Scene ...' in the outliner folder HesperScene (the level build owns the folder Hesper).

Progress tokens (BP_Physis Flags):
  ,hesper, ,at_hesper,  arrived / saves load here     ,aeon_h,  Aeon met     ,dissonance,  the Tuning Court
  ,hs_bell1, ,hs_bell2, ,hs_bell3,  the bells     ,hs_gate,  the Choir Gate opens     ,cantor,  the Cantor falls
  ,vaelun,  the Precentor, in person     ,hesper_done,  Aeon afterwards
  side requests ,liss, ,hs_stone1-3, ,hs_stones, ,tavor, ,tuningfork, ,anwe, ,reedflute,;  caches ,hs_cache1-5,;  seals ,hs_seal1-2,
  augmentations ,aug_hp10, ,aug_katana8, ,aug_pistol7, ,aug_defense8, ,aug_agility8,
Encounter rooms 701-799. Tags for BP_HesperDirector: HesperScar (hidden once the Cantor falls: the Concord's amber
light), HesperBloom (shown then), HesperHush (sounds faded then). Every BP_Unison hides itself once ,cantor, is held.
Markers: TargetPoint tags HesperArrival (here) and HesperReturn (in the Center).

This module stands on Arche's scenario (physis_arche_scenario: its Place with Arche's animals, pack(), the roadside
pieces), loaded a second time under another name, which stands on the Grove's (physis_grove_scenario); Hesper's folder,
meshes, voices, enemies and Still Point rule are put in their globals.
"""
import importlib.util
import math
import pathlib
import random
import types

import unreal

import physis_hesper_lore as lore
import physis_hesper_plan as plan
import physis_hesper_tools as T
from physis_lore import image_name, voice_name

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
_spec = importlib.util.spec_from_file_location('physis_hesper_arche', ROOT / 'Content/Python/physis_arche_scenario.py')
ar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ar)
base = ar.base

HESPER = '/Game/Hesper'
MESHES = HESPER + '/Meshes'
VOICES = HESPER + '/Audio/Voice'
LEVEL = '/Game/Levels/L_Hesper'
CENTER_LEVEL = '/Game/Levels/L_CenterOfTheUniverse'
FOLDER = 'HesperScene'
M = 100.0
UNISON = (1.0, .64, .2)
SERENE = (.55, .85, 1.0)
VIGIL = (.62, .38, 1.0)
DUSK = (1.0, .76, .52)
UNISON_MATERIAL = HESPER + '/Materials/M_HS_Unison'
# The Center: the temple's top tier, 16 m north-east of the Heartbloom (the Conclave's current is north, Earth's east,
# Arche's west, Halcyon's north-west; south is the sanctum's Still Point); she comes back 11 m out from it.
TEMPLE = (76000.0, 0.0)
SANCTUM = 3400.0 + 600.0
PORTAL = (TEMPLE[0] + 1131.0, TEMPLE[1] + 1131.0, SANCTUM + 35.0)
RETURN = (TEMPLE[0] + 778.0, TEMPLE[1] + 778.0, SANCTUM + 120.0)


def mesh_asset(name):
    """A mesh by its name alone: Hesper's own (SM_S[TNE]_), Arche's (SM_A*), the Conclave's (SM_C*), a scan (SM_GS_)
    or the Grove's."""
    if name.startswith('/'):
        return base.asset(name)
    if name.startswith(('SM_ST_', 'SM_SN_', 'SM_SE_')):
        return base.asset(MESHES + '/' + name)
    if name.startswith('SM_A'):
        return base.asset('/Game/Arche/Meshes/' + name)
    if name.startswith('SM_C'):
        return base.asset('/Game/Conclave/Meshes/' + name)
    if name.startswith('SM_GS_'):
        return base.asset('/Game/Grove/Scans/' + name)
    return base.asset('/Game/Grove/Meshes/' + name)


base.FOLDER, base.LEVEL, base.VOICES, base.STILL_UNTIL, base.mesh_asset = FOLDER, LEVEL, VOICES, ',cantor,', mesh_asset
ar.mesh_asset = mesh_asset
ar.lore = types.SimpleNamespace(ARCHE_ENEMIES=lore.HESPER_ENEMIES, MESSAGES=lore.MESSAGES)
cm, turned, component, props, wrap, asset, cls, sub = base.cm, base.turned, base.component, base.props, base.wrap, base.asset, base.cls, base.sub


class Place(ar.Place):
    def __init__(self, ground):
        super().__init__(ground)
        self.unisons = []

    def ok(self, x, y, clear, still):
        mx, my = x / M, y / M
        if plan.rim(mx, my) > .9 or plan.off_edge(mx, my, 6.0) or plan.in_pool(mx, my, 2.0) or plan.on_wall(mx, my, 4.0):
            return False
        if any(math.hypot(x - sx, y - sy) < r + clear for sx, sy, r in self.solids):
            return False
        return not (still and any(math.hypot(x - sx, y - sy) < still for sx, sy in self.stills))

    def unison(self, label, place, yaw=0.0, scale=(1.0, 1.0, 1.0), mesh='SM_SN_Unison', hold=0.0, give='', done='', need='', hide=',cantor,',
               folder='Unison'):
        """BP_Unison: the Concord's tone standing at `place` (cm: the middle of its foot). The actor stands at the
        middle of the shape's box, the shape below it, so the Blueprint can measure her distance to the box."""
        figure = mesh_asset(mesh)
        box = figure.get_bounding_box() if figure else None
        size = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        half = [(box.max.x - box.min.x) / 2 * size[0], (box.max.y - box.min.y) / 2 * size[1], (box.max.z - box.min.z) / 2 * size[2]] if box else [300, 600, 600]
        actor = self.spawn('BP_Unison', label, (place[0], place[1], place[2] + half[2]), None, folder, Need=need, Hide=hide, Give=give, Done=done,
                           Hold=float(hold), HalfX=float(half[0]), HalfY=float(half[1]), HalfZ=float(half[2]))
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        shape = component(actor, 'Shape')
        shape.set_static_mesh(figure)
        shape.set_relative_scale3d(unreal.Vector(*size))
        shape.set_relative_location(unreal.Vector(0, 0, -half[2]), False, False)
        tone = asset(UNISON_MATERIAL, True)
        for slot in range(shape.get_num_materials()):
            shape.set_material(slot, tone)
        shape.set_editor_property('cast_shadow', False)
        shape.set_collision_profile_name('BlockAll')
        self.unisons.append(label)
        return actor

    def shell(self, label, x, y, z=None, give='', done='', hold=3.0, scale=1.0, need='', folder='Shells'):
        """A shell of Unison round what stands at (x, y): breaks for good once her note has covered it `hold` s."""
        z = self.floor(x, y) - 10.0 if z is None else z
        return self.unison(label, (x, y, z), 0.0, (scale, scale, scale), 'SM_SN_Shell', hold, give, done, need, folder=folder)


def pack(p, label, x, y, levels, room=0, spread=700.0, z=None):
    return ar.pack(p, label, x, y, levels, room, spread, z)


def cache(p, n, title, x, y, z=None):
    token = ',hs_cache%d,' % n
    z = p.floor(x, y) if z is None else z
    p.relic('Dusk Cache %d' % n, (x, y, z + 110), token, lore.MESSAGES['cache'], divinity=40.0, mesh='SM_AN_Cache', scale=1.3)
    p.light('Dusk Glow %d' % n, (x, y, z + 160), DUSK, 1500, 500, 'Items')
    p.site(title, x, y, 2, token)


def dress(p, label, rows, folder, origin=(0.0, 0.0)):
    for k, (mesh, x, y, yaw, scale, solid) in enumerate(rows):
        px, py = cm(origin[0] + x, origin[1] + y)
        p.mesh('%s %d' % (label, k), mesh, (px, py, p.g.at(px, py) - 3), yaw, scale, folder, solid=solid)


# ---------------------------------------------------------------- the regions

def stair(p):
    sx_, sy_ = cm(*plan.STAIR)
    floor = p.g.at(sx_, sy_)
    p.spawn('BP_HesperCurrent', 'Current Home', (sx_, sy_, floor + 25), None, 'Stair', Need='', Dest=2, Radius=180.0)
    p.solids.append((sx_, sy_, 500))
    p.light('Stair Glow', (sx_, sy_, floor + 600), SERENE, 9000, 2800, 'Stair')
    x, y = cm(*plan.STAIR_STILL)
    p.check('Sunward Stair', x, y, lore.QUEST_ARRIVE, 800.0)
    p.marks['Arrival'] = p.at(x, y, 120)
    p.marker('Arrival', p.marks['Arrival'], 'HesperArrival', 'Stair')
    dress(p, 'Stair', (('SM_AN_Lantern', -8.0, 12.0, 0.0, 1.0, 40), ('SM_AN_Lantern', 12.0, 14.0, 0.0, 1.0, 40), ('SM_AN_Bench', -14.0, -8.0, 30.0, 1.0, 130),
                       ('SM_AN_Urn', 10.0, -14.0, 0.0, 1.0, 60), ('SM_AN_Obelisk', 18.0, -18.0, 20.0, 1.0, 120), ('SM_AN_Column', -18.0, 16.0, 0.0, 1.0, 90)),
          'Stair', plan.STAIR)
    cache(p, 1, 'Sunward Stair Cache', *cm(-470.0, 4.0))


def terrace(p):
    pack(p, 'Long Terrace', *cm(-424.0, 66.0), (1, 1, 2), 701, 600)
    p.encounter('Long Terrace', *cm(-424.0, 66.0), 701, ',hs_road,', 'The Choir\'s patrol is down. The terrace north is clear.')
    pack(p, 'Terrace North', *cm(-352.0, 44.0), (1, 2), 0, 600)
    pack(p, 'Hall Lane', *cm(-372.0, 140.0), (2, 2, 1), 0, 700)


HOUSE_DRESS = (('SM_AN_Bench', 8.0, -8.0, 20.0, 1.0, 130), ('SM_AN_Bench', 9.0, 8.0, -20.0, 1.0, 130), ('SM_AN_Basin', 16.0, 0.0, 0.0, 1.0, 380),
               ('SM_AN_Lantern', 12.0, 14.0, 0.0, 1.0, 40), ('SM_AN_Lantern', 12.0, -14.0, 0.0, 1.0, 40), ('SM_AN_Urn', -2.0, 20.0, 0.0, 1.0, 60),
               ('SM_AN_Urn', -1.0, 21.5, 40.0, .8, 50), ('SM_AN_Obelisk', 20.0, 18.0, 0.0, 1.0, 120))


def house(p):
    hx, hy = plan.HOUSE
    p.check('House of Listeners', *cm(*plan.HOUSE_STILL), 'The House of Listeners. Speak to Aeon.')
    x, y = cm(hx - 16.0, hy)
    p.mesh('House of Listeners', 'SM_AN_Hall', (x, y, p.g.at(x, y) - 20), 0.0, 1.0, 'House', solid=1100)
    dress(p, 'House', HOUSE_DRESS, 'House', plan.HOUSE)
    for k, (dx, dy) in enumerate(((12.0, 14.0), (12.0, -14.0))):
        lx, ly = cm(hx + dx, hy + dy)
        p.light('House Lamp %d' % k, (lx, ly, p.g.at(lx, ly) + 380), SERENE, 2400, 1400, 'House')
    for row in lore.PEOPLE:
        if row[5][0] < -250.0:
            p.solids.append((row[5][0] * M, row[5][1] * M, 250))


def tuning(p):
    """The Tuning Court: a fallen bell in a shell of Unison. With Aeon met, the switch here teaches Dissonance; the
    shell is the first she breaks."""
    tx, ty = cm(*plan.TUNING)
    floor = p.g.at(tx, ty)
    yaw = math.degrees(math.atan2(30.0 - plan.TUNING[1], plan.wall_x(30.0) - plan.TUNING[0]))
    p.mesh('Fallen Bell', 'SM_SN_Bell', (tx, ty, floor - 60), yaw + 20.0, .85, 'Tuning', solid=400)
    p.shell('Fallen Bell Shell', tx, ty, floor - 20, ',hs_tuned,', lore.MESSAGES['tuning_bell'], 2.0, 1.05, need=',dissonance,', folder='Tuning')
    dx, dy = turned(700.0, 0.0, yaw)
    p.switch('The Tuning Court', (tx + dx, ty + dy, floor), yaw, 'SM_AN_Pedestal', False, None, 'Tuning', Need=',aeon_h,', Give=',dissonance,',
             Denied=lore.MESSAGES['tuning_denied'], Done=lore.TUNING_DONE)
    p.light('Tuning Glow', (tx, ty, floor + 600), UNISON, 3000, 1600, 'Tuning', ('HesperScar',))
    dress(p, 'Tuning', (('SM_AN_ColumnBroken', -10.0, 8.0, 40.0, 1.0, 90), ('SM_AN_Column', 10.0, -10.0, 0.0, 1.0, 90), ('SM_AN_Bench', -8.0, -9.0, 60.0, 1.0, 130),
                        ('SM_AN_Urn', 12.0, 9.0, 0.0, 1.0, 60)), 'Tuning', plan.TUNING)
    pack(p, 'Tuning Way', *cm(-246.0, 48.0), (1, 1), 0, 500)


def choir_wall(p):
    """The Choir Wall: panels of Unison from the western edge to the eastern cliffs (plan.wall_panels). The barrier she
    remembers: crossed only inside her note."""
    for k, (x, y, yaw) in enumerate(plan.wall_panels()):
        px, py = cm(x, y)
        ground = min(p.g.at(px, py - 600.0), p.g.at(px, py + 600.0), p.g.at(px, py))
        p.unison('Choir Wall %02d' % k, (px, py, ground - 100.0), yaw, (1.0, 1.02, 1.0), folder='Choir Wall')
        if k % 4 == 2:
            p.light('Choir Wall Light %d' % k, (px - 500.0, py, ground + 700.0), UNISON, 4000, 2200, 'Choir Wall', ('HesperScar',))
    x, y = cm(plan.wall_x(30.0), 30.0)
    p.scan('Story', 'The Concord', next(r[2] for r in lore.HESPER_SCANS if r[1] == 'The Concord'), (x - 1200.0, y + 1600.0, None), True, 'Choir Wall')


def market(p):
    mx_, my_ = cm(*plan.MARKET)
    p.check('Bell Market', mx_, my_, lore.QUEST_BELLS)
    dress(p, 'Market', (('SM_AN_Basin', 0.0, 14.0, 0.0, 1.0, 380), ('SM_AN_Bench', 8.0, -10.0, 10.0, 1.0, 130), ('SM_AN_Bench', -8.0, -11.0, -10.0, 1.0, 130),
                        ('SM_AN_Lantern', 12.0, -12.0, 0.0, 1.0, 40), ('SM_AN_Lantern', -12.0, 12.0, 0.0, 1.0, 40), ('SM_AN_Urn', 14.0, 6.0, 0.0, 1.0, 60),
                        ('SM_AN_Urn', 15.0, 7.4, 30.0, .8, 50), ('SM_AN_Obelisk', -16.0, -2.0, 0.0, 1.0, 120)), 'Market', plan.MARKET)
    for k, (level, x, y) in enumerate(((2, -40.0, 30.0), (2, -36.0, -14.0), (1, -48.0, 8.0))):
        p.enemy(level, 'Market %d' % k, x * M, y * M, 702)
    p.encounter('Bell Market', -42.0 * M, 8.0 * M, 702, ',hs_market,', 'The Bell Market is clear.')
    for label, (x, y), levels in (('Reed Walk', (-40.0, -84.0), (1, 2)), ('Gallery Walk', (-30.0, 110.0), (1, 1, 3)), ('Nave Road', (40.0, 30.0), (2, 3))):
        pack(p, label, *cm(x, y), levels, 0, 700)
    cache(p, 2, 'Bell Market Cache', *cm(-60.0, 60.0))


def bell(p, row, folder, guard_room, guard_levels, guard_at, veils=()):
    key, (bx, by), token, line = row
    x, y = cm(bx, by)
    floor = p.g.at(x, y)
    p.mesh('%s Bell' % key, 'SM_SN_Bell', (x, y, floor - 30), 0.0, 1.0, folder, solid=380)
    p.shell('%s Bell Shell' % key, x, y, floor - 20, token, line, 3.0, 1.12, folder=folder)
    p.light('%s Bell Light' % key, (x, y, floor + 900), UNISON, 3200, 1500, folder, ('HesperScar',))
    p.light('%s Bell Dusk' % key, (x - 500, y, floor + 400), DUSK, 1600, 1500, folder)
    gx, gy = cm(*guard_at)
    for k, level in enumerate(guard_levels):
        a = k * 2.1
        p.enemy(level, '%s Guard %d' % (key, k), gx + math.cos(a) * 700.0, gy + math.sin(a) * 700.0, guard_room)
    p.encounter('%s Guard' % key, gx, gy, guard_room, ',hs_g%d,' % guard_room, lore.MESSAGES['bell_guard'])
    for k, (vx, vy, yaw, width) in enumerate(veils):
        px, py = cm(vx, vy)
        p.unison('%s Veil %d' % (key, k), (px, py, p.g.at(px, py) - 100.0), yaw, (.8, width / 12.0, .8), folder=folder)


def heading(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def terraces(p):
    """The Reed Terraces: the Reed Walk out to the pools, two veils across it, and the Low Bell at the last pool."""
    p.check('Reed Terraces', *cm(*plan.TERRACE_STILL), 'The Reed Terraces. The Low Bell hangs at the last pool, in a shell of tone.')
    walk = next(pts for name, _, _, pts in plan.PATHS if name == 'Reed Walk')
    a, b = walk[-2], walk[-1]
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    # A veil across the walk (yaw: the panel's local y across the way) and one between the pools.
    across = heading(a, b)
    veils = ((mid[0], mid[1], across, 14.0), (50.0, -270.0, -20.0, 18.0))
    bell(p, lore.BELLS[0], 'Terraces', 711, (5, 2, 1), (40.0, -230.0), veils)
    fx, fy = cm(plan.POOLS[3][0] - 8.0, plan.POOLS[3][1] + 22.0)
    p.relic('Anwe\'s Flute', (fx, fy, p.g.at(fx, fy) + 100), ',reedflute,', lore.MESSAGES['flute'], ',anwe,', mesh='SM_SN_Flute', scale=2.0)
    cache(p, 3, 'Reed Terraces Cache', *cm(-50.0, -230.0))
    dress(p, 'Terraces', (('SM_AN_Bench', 30.0, -184.0, 90.0, 1.0, 130), ('SM_AN_Lantern', 20.0, -186.0, 0.0, 1.0, 40), ('SM_AN_Urn', 52.0, -222.0, 0.0, 1.0, 60)),
          'Terraces')


GALLERY_RING = 26.0


def galleries(p):
    """The Amber Galleries: colonnades in a ring round the middle court, the Middle Bell in it, and Unison closing
    every way in through the colonnade (a maze she walks through inside her note)."""
    p.check('Amber Galleries', *cm(*plan.GALLERY_STILL), 'The Amber Galleries. The Middle Bell hangs in the middle court.')
    cx, cy = plan.MID_BELL
    for k in range(16):      # the outer colonnade, 8 m outside the ring
        a = math.radians(k * 22.5)
        x, y = cm(cx + math.cos(a) * (GALLERY_RING + 8.0), cy + math.sin(a) * (GALLERY_RING + 8.0))
        p.mesh('Gallery Column %d' % k, 'SM_AN_Column', (x, y, p.g.at(x, y) - 20), math.degrees(a), 1.0, 'Galleries', solid=90)
    ways = []
    for k in range(8):
        a = math.radians(k * 45.0 + 11.25)
        x, y = cm(cx + math.cos(a) * GALLERY_RING, cy + math.sin(a) * GALLERY_RING)
        if k % 2 == 0:
            p.mesh('Gallery Arch %d' % k, 'SM_AN_Arch', (x, y, p.g.at(x, y) - 20), math.degrees(a), 1.0, 'Galleries', solid=0)
        ways.append((x / M, y / M, math.degrees(a), 11.0))
    # The ring between the arches: walls, so the only ways in are through the Unison.
    for k in range(8):
        a = math.radians(k * 45.0 + 33.75)
        x, y = cm(cx + math.cos(a) * GALLERY_RING, cy + math.sin(a) * GALLERY_RING)
        p.mesh('Gallery Wall %d' % k, 'SM_AN_Wall', (x, y, p.g.at(x, y) - 40), math.degrees(a), (1.0, 1.12, .9), 'Galleries')
    bell(p, lore.BELLS[1], 'Galleries', 721, (5, 4, 1), (plan.GALLERIES[0] - 30.0, plan.GALLERIES[1] - 30.0), ways)
    cache(p, 4, 'Amber Galleries Cache', *cm(plan.GALLERIES[0] - 40.0, plan.GALLERIES[1] + 70.0))
    pack(p, 'Galleries South', *cm(-10.0, 230.0), (3, 4), 0, 700)


def spire(p):
    """The Watch Spire on its rock: the ramp up the south-west side barred by three Unison gates, the High Bell on the
    terrace, the tower behind it, Tavor's fork at the tower's foot."""
    p.check('Watch Spire', *cm(*plan.SPIRE_STILL), 'The Watch Spire. The High Bell hangs on the terrace; the ramp up is barred by the tone.')
    sx, sy = cm(*plan.SPIRE)
    p.mesh('Watch Spire', 'SM_SN_Spire', (sx, sy, p.g.at(sx, sy) - 40), 45.0, 1.0, 'Spire', solid=650)
    (fx, fy), (tx, ty) = plan.RAMP
    up = heading((fx, fy), (tx, ty))
    gates = []
    for k, t in enumerate((.2, .5, .85)):
        gates.append((fx + (tx - fx) * t, fy + (ty - fy) * t, up, 10.0))
    bell(p, lore.BELLS[2], 'Spire', 731, (5, 3, 2), (plan.SPIRE_ROCK[0] - 44.0, plan.SPIRE_ROCK[1] - 44.0), gates)
    kx, ky = cm(plan.SPIRE[0] - 9.0, plan.SPIRE[1] - 3.0)
    p.relic('Tavor\'s Fork', (kx, ky, p.g.at(kx, ky) + 100), ',tuningfork,', lore.MESSAGES['fork'], ',tavor,', mesh='SM_SN_Fork', scale=1.6)
    cache(p, 5, 'Watch Spire Cache', *cm(plan.SPIRE_ROCK[0] + 20.0, plan.SPIRE_ROCK[1] - 20.0))


NAVE_VEILS = (262.0, 292.0, 322.0, 352.0)


def nave(p):
    """The Nave: walls on both sides from the market's end to the court, and Unison across it four times."""
    p.check('Nave', *cm(*plan.NAVE_STILL), 'The Nave. The Choir Gate is at its end.')
    x = plan.NAVE_SOUTH
    k = 0
    while x < plan.CHOIR_GATE[0] - 8.0:
        for side in (-1, 1):
            wx, wy = cm(x + 6.0, side * 11.5)
            p.mesh('Nave Wall %d %s' % (k, 'E' if side > 0 else 'W'), 'SM_AN_Wall', (wx, wy, p.g.at(wx, wy) - 60), 90.0 * side, (1.0, 1.0, 1.0), 'Nave')
        x += 12.0
        k += 1
    for k, vx in enumerate(NAVE_VEILS):
        px, py = cm(vx, 0.0)
        p.unison('Nave Veil %d' % k, (px, py, p.g.at(px, py) - 100.0), 0.0, (1.0, 23.0 / 12.0, 1.0), folder='Nave')
        p.light('Nave Light %d' % k, (px - 400.0, py, p.g.at(px, py) + 700.0), UNISON, 3600, 2000, 'Nave', ('HesperScar',))
    for k, (level, x, y) in enumerate(((5, 278.0, 3.0), (2, 306.0, -4.0), (5, 338.0, 2.0), (1, 300.0, 5.0))):
        p.enemy(level, 'Nave Guard %d' % k, x * M, y * M, 741)
    p.encounter('Nave Guard', 300.0 * M, 0.0, 741, ',hs_nave,', 'The Nave is clear. The Choir Gate is ahead.')


WALL_SLOTS = 17


def concord(p):
    cx, cy = cm(*plan.CONCORD)
    radius = plan.COURT_WALL * M
    floor = p.g.at(cx, cy)
    for k in range(WALL_SLOTS):
        bearing = 180.0 + k * 360.0 / WALL_SLOTS
        b = math.radians(bearing)
        x, y = cx + math.cos(b) * radius, cy + math.sin(b) * radius
        if k == 0:
            p.mesh('Choir Gate Frame', 'SM_AN_GateFrame', (x, y, p.g.at(x, y) - 30), bearing, 1.0, 'Concord')
            p.rise('The Choir Gate', 'SM_AN_Veil', (x, y, p.g.at(x, y) - 10), ',hs_gate,', -1150.0, bearing, 1.0, 260.0, 'Concord')
            p.light('Choir Gate Light', (x - 300, y, p.g.at(x, y) + 900), UNISON, 5200, 2200, 'Concord', ('HesperScar',))
        else:
            p.mesh('Court Wall %d' % k, 'SM_AN_Wall', (x, y, p.g.at(x, y) - 60), bearing, (1, 1.02, 1.06), 'Concord')
    gx, gy = cm(*plan.CHOIR_GATE)
    p.require('Choir Gate Lock', (gx, gy, p.g.at(gx, gy) + 600), (',hs_bell1,', ',hs_bell2,', ',hs_bell3,'), ',hs_gate,', lore.MESSAGES['gate'])
    p.check('Concord', *cm(*plan.COURT_STILL), lore.QUEST_CANTOR)
    hx, hy = cm(*plan.HORN)
    p.mesh('The Concord', 'SM_SN_Concord', (hx, hy, p.g.at(hx, hy) - 30), 0.0, 1.0, 'Concord', solid=1400)
    p.light('Concord Light', (hx - 900, hy, floor + 2200), UNISON, 26000, 9000, 'Concord', ('HesperScar',))
    p.light('Concord Dusk', (hx - 900, hy, floor + 2200), DUSK, 6000, 9000, 'Concord', ('HesperBloom',)).set_actor_hidden_in_game(True)
    # The Cantor and its Choir, and the four tuning pylons its shield answers to, each in a shell of tone.
    p.enemy(7, 'Cantor', cx + 600.0, cy, 752, floor)
    for k, (level, bearing, r) in enumerate(((5, 60.0, 1900.0), (5, 300.0, 1900.0), (1, 120.0, 1500.0), (1, 240.0, 1500.0), (1, 180.0, 1100.0), (3, 0.0, 2300.0))):
        b = math.radians(bearing)
        p.enemy(level, 'Cantor Choir %d' % k, cx + math.cos(b) * r, cy + math.sin(b) * r, 752, floor)
    entry = next(row for row in lore.HESPER_SCANS if row[1] == 'Tuning Pylon')
    for k, bearing in enumerate((45.0, 135.0, 225.0, 315.0)):
        b = math.radians(bearing)
        x, y = cx + math.cos(b) * 2300.0, cy + math.sin(b) * 2300.0
        z = p.g.at(x, y)
        p.target('Tuning Pylon %d' % k, 'SM_SN_Pylon', (x, y, z), 752, 6, 1.0, entry[:3], bearing + 180.0, 'Concord', True)
        p.shell('Pylon Shell %d' % k, x, y, z - 20, ',hs_pylon%d,' % k, lore.MESSAGES['pylon'], 2.0, .9, folder='Concord')
    p.encounter('Cantor', cx, cy, 752, ',cantor,', lore.MESSAGES['cantor'], lore.QUEST_VAELUN, z=floor)
    for k, bearing in enumerate((90.0, 270.0)):
        b = math.radians(bearing)
        p.pickup(0, 'Court Capsule %d' % k, cx + math.cos(b) * 2600.0, cy + math.sin(b) * 2600.0, floor)
    p.relic('The Concord\'s Heart', (cx + 1200.0, cy - 600.0, floor + 115), ',aug_hp10,', lore.MESSAGES['heart'], ',cantor,', heal=True,
            mesh='SM_AN_Seedstone', scale=2.0)


def hall(p):
    """The Hall of Withheld Votes: three speaking stones in shells of tone before its door; with all three spoken the
    Hall's blade can be taken. A Siegeframe walks before it."""
    lx, ly = cm(*plan.HALL)
    floor = p.g.at(lx, ly)
    p.mesh('Hall of Withheld Votes', 'SM_AN_Hall', (lx - 600.0, ly, floor - 20), 0.0, 1.0, 'Hall', solid=1100)
    for k in range(3):
        sx, sy = lx + 900.0, ly + (k - 1) * 600.0
        z = p.g.at(sx, sy)
        p.mesh('Speaking Stone %d' % (k + 1), 'SM_AN_Obelisk', (sx, sy, z - 10), 180.0, 1.0, 'Hall', solid=100)
        p.shell('Speaking Stone Shell %d' % (k + 1), sx, sy, z - 20, ',hs_stone%d,' % (k + 1), lore.MESSAGES['stone'], 3.0, .8, folder='Hall')
    p.require('Hall Stones', (lx, ly, floor + 600), (',hs_stone1,', ',hs_stone2,', ',hs_stone3,'), ',hs_stones,', lore.MESSAGES['stones'])
    p.relic('The Dissenter\'s Blade', (lx + 300.0, ly, floor + 115), ',aug_katana8,', lore.MESSAGES['blade'], ',hs_stones,', mesh='SM_AN_Tablet', scale=1.2)
    p.site('Hall of Withheld Votes', lx, ly, 0, ',aug_katana8,')
    p.enemy(6, 'Hall Siegeframe', lx + 1800.0, ly - 2200.0, 761)
    p.encounter('Hall Siegeframe', lx + 1800.0, ly - 2200.0, 761, ',hs_siege,', 'The Siegeframe is still.')


def sealed(p):
    """Vaults for abilities learned elsewhere: Trace Reading (Halcyon) and Reweave (Kathodos) both open now."""
    for n, ((x, y), ability) in enumerate(((plan.SEALED_TRACE, ',trace,'), (plan.SEALED_WEAVE, ',reweave,')), 1):
        px, py = cm(x, y)
        yaw = math.degrees(math.atan2(-py, -px))
        door = p.spawn('BP_AbilitySocket', 'Sealed Vault %d' % n, (px, py, p.g.at(px, py) - 10), None, 'Sealed', Ability=ability, Give=',hs_seal%d,' % n,
                       Radius=900.0, Hold=0.0, Solid=True, Message='The vault\'s seal opens.')
        door.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = p.reskin(door, 'SM_AN_VaultDoor')
        if part:
            part.set_collision_profile_name('BlockAll')
        back = turned(-420.0, 0.0, yaw)
        p.mesh('Sealed Cell %d' % n, 'SM_AN_House1', (px + back[0], py + back[1], p.g.at(px, py) - 20), yaw, (.7, .9, .8), 'Sealed', solid=500)
        entry = lore.HESPER_GATES[0]
        p.scan(entry[0], entry[1], entry[2], (px + turned(300.0, 0.0, yaw)[0], py + turned(300.0, 0.0, yaw)[1], None), True, 'Sealed')
        p.site('Sealed Vault %d' % n, px, py, 1, ',hs_seal%d,' % n)
        front = turned(250.0, 0.0, yaw)
        p.relic('Sealed Vault %d Cache' % n, (px + front[0], py + front[1], p.g.at(px, py) + 110), ',hs_sealgift%d,' % n,
                'The vault held a traveller\'s store. Divinity +80.', ',hs_seal%d,' % n, divinity=80.0, mesh='SM_AN_Cache', scale=1.5)


# ---------------------------------------------------------------- the city between the set pieces

SAFE = ((plan.STAIR, 55.0), (plan.HOUSE, 75.0), (plan.TUNING, 30.0), (plan.CONCORD, plan.COURT_WALL + 10.0))
PATROLS = ((1, 1, 2), (2, 2), (1, 3), (2, 3), (3, 4), (2, 4))


def life(p):
    """The Choir's patrols on the roads and a shoal of Arche's animals out in the open ground, harder toward the
    Concord, and Kathodos's roadside pieces (shrines, houses, courts) between. Seeded."""
    rng = random.Random(7)
    made, dressed = 0, 0
    for row in lore.PEOPLE:
        p.solids.append((row[5][0] * M, row[5][1] * M, 450.0))
    for name, kind, half, points in plan.PATHS:
        for k, (x, y, head) in enumerate(ar.along(points, 85.0, 40.0)):
            if any(math.hypot(x - sx, y - sy) < r for (sx, sy), r in SAFE) or plan.on_wall(x, y, 12.0) or plan.NAVE_SOUTH < x < plan.CHOIR_GATE[0] and abs(y) < 20:
                continue
            hard = min(len(PATROLS) - 1, max(0, int((x + 520.0) / 150.0)))
            pack(p, 'Patrol %s %d' % (name, k), x * M, y * M, rng.choice(PATROLS[max(0, hard - 1):hard + 1]), 0, 500)
            made += 1
            # A roadside piece every other stop, set back from the way.
            if k % 2 == 1:
                piece = rng.choice(sorted(ar.ROADSIDE))
                side = rng.choice((-1, 1))
                ox, oy = x - math.sin(head) * side * (half + 9.0), y + math.cos(head) * side * (half + 9.0)
                if plan.off_edge(ox, oy, 12.0) or plan.on_wall(ox, oy, 10.0) or plan.in_pool(ox, oy, 6.0) or plan.on_rock(ox, oy, 6.0) or plan.rim(ox, oy) > .88:
                    continue
                if any(math.hypot(ox * M - sx, oy * M - sy) < r + 900 for sx, sy, r in p.solids):
                    continue
                rows = [(mesh, fx * math.cos(head) - sy * math.sin(head), fx * math.sin(head) + sy * math.cos(head), yaw + math.degrees(head), scale, solid)
                        for mesh, fx, sy, yaw, scale, solid, _lit in ar.ROADSIDE[piece]]
                dress(p, 'Roadside %s %d' % (name, k), rows, 'Roadside', (ox, oy))
                p.solids.append((ox * M, oy * M, 600.0))
                dressed += 1
    p.life = {'patrols': made, 'roadside': dressed}


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
    npc = p.spawn('BP_NPC', 'Person ' + key, (px, py, p.g.at(px, py)), None, 'People', Speaker=speaker, Key=key,
                  Pages='|'.join(wrap(page) for page in pages), Asks='|'.join(label for label, _ in topics), Starts='|'.join(str(s) for s in starts),
                  Greet=len(greeting), Show=show, Hide=hide, Give=give, Quest=quest, RewardDivinity=float(reward.get('divinity', 0.0)),
                  RewardHeal=bool(reward.get('heal', False)), Note=reward.get('note', ''), Face=kind == 'firstone', Bob=0.0)
    npc.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    body, shape, view = component(npc, 'Body'), component(npc, 'Shape'), component(npc, 'Look')
    for name in ('Lower', 'Upper', 'Head'):
        part = component(npc, name)
        if part:
            part.set_static_mesh(None)
    if view:
        view.set_child_actor_class(None)
    if body:
        body.set_skinned_asset_and_update(None, True)
    figure = mesh_asset(mesh) or mesh_asset('SM_AP_Serene1')
    if shape:
        shape.set_static_mesh(figure)
    p.people.append((key, figure.get_name() if figure else 'MISSING'))
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

ATTACHED = ('Tavor\'s Fork', 'Anwe\'s Flute', 'The Concord\'s Heart', 'The Dissenter\'s Blade', 'Dusk Cache', 'Tuning Pylon', 'The Concord')


def scans(p):
    for category, title, body, (x, y, z), important in lore.HESPER_SCANS:
        if title in ATTACHED:
            continue
        p.scan(category, title, body, (x * M, y * M, z), important)


def voices(p):
    for category, title, body in lore.hesper_entries() + [('Story',) + tuple(lore.ARRIVAL_LINE)]:
        voice = asset(VOICES + '/' + voice_name(title), True)
        if voice is None:
            p.unvoiced.append(title)
            continue
        p.spawn('BP_LogVoice', 'Voice ' + title, base.VOICE_SPOT, None, 'Voices', Title=title, Voice=voice, Image=asset('/Game/UI/Log/' + image_name(title), True))


def tutorials(p):
    for index, (message, (x, y), scale) in enumerate(lore.HESPER_TUTORIALS):
        p.spawn('BP_TutorialTrigger', 'Tutorial %02d' % (index + 1), p.at(x * M, y * M, 160), scale, 'Tutorial', Message=message)


def sound_scape(p):
    """The plateau's wind everywhere, the Concord's drone by the court (faded once the Cantor falls: tag HesperHush),
    water among the Reed Terraces (Tools/build_physis_hesper_audio.py, then hesper:audio; Arche's beds until then)."""
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
    ambient('Wind', (HESPER + '/Audio/S_Amb_Hesper', '/Game/Arche/Audio/S_Amb_Arche'), (0, 0, 3000), 0, .5)
    ambient('Concord', (HESPER + '/Audio/S_Amb_Concord', '/Game/Arche/Audio/S_Amb_Lens'), (plan.HORN[0] * M, plan.HORN[1] * M, 4800), 18000, .9,
            ('HesperScar', 'HesperHush'))
    ambient('Reed Terraces', (HESPER + '/Audio/S_Amb_Reeds', '/Game/Arche/Audio/S_Amb_Cistern'), (plan.TERRACES[0] * M, plan.TERRACES[1] * M, 3200), 9000, .7)
    return placed


def regrade_all():
    """Kathodos's meshes in L_Hesper wear their dusk twins (physis_hesper_tools.regrade)."""
    swapped = 0
    for actor in sub().get_all_level_actors():
        if str(actor.get_folder_path()).startswith(FOLDER):
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
    stair(p)
    terrace(p)
    house(p)
    tuning(p)
    choir_wall(p)
    market(p)
    terraces(p)
    galleries(p)
    spire(p)
    nave(p)
    concord(p)
    hall(p)
    sealed(p)
    life(p)
    people(p)
    scans(p)
    voices(p)
    tutorials(p)
    rays = base.divinity_rays(p)
    sounds = sound_scape(p)
    regraded = regrade_all()
    arrival_off()
    if save:
        base.save_level(LEVEL)
    return {'level': LEVEL, 'removed': removed, 'placed': p.count, 'enemies': p.enemies, 'rays': rays, 'sounds': sounds, 'people': p.people,
            'unset': p.unset, 'unvoiced': len(p.unvoiced), 'unisons': len(p.unisons), 'regraded': regraded, 'unrigged': sorted(set(p.unrigged)),
            'missing_assets': sorted(base.MISSING)[:60], 'missing_count': len(base.MISSING), 'life': getattr(p, 'life', None),
            'marks': {name: [round(v) for v in spot] for name, spot in p.marks.items()}}


# ---------------------------------------------------------------- the Center's sanctum current

def portal():
    """The current to Hesper in the Center's sanctum, shown once the Keel has fallen: a targeted spawn into
    L_CenterOfTheUniverse that replaces only its own earlier actors (labels 'Hesper Current...')."""
    base.open_level(CENTER_LEVEL)
    dirty = [pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them before hesper:portal' % ', '.join(dirty))
    actors = sub()
    removed = 0
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith('Hesper Current'):
            actors.destroy_actor(actor)
            removed += 1
    current = actors.spawn_actor_from_class(cls('BP_HesperCurrent'), unreal.Vector(*PORTAL))
    current.set_actor_label('Hesper Current')
    current.set_folder_path('Center/Hesper')
    props(current, Need=',keel,', Dest=1, Radius=180.0)
    back = actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*RETURN))
    back.set_actor_label('Hesper Current Return')
    back.set_folder_path('Center/Hesper')
    back.set_editor_property('tags', ['HesperReturn'])
    arrival_off()
    base.save_level(CENTER_LEVEL)
    return {'level': CENTER_LEVEL, 'current': list(PORTAL), 'return': list(RETURN), 'removed': removed}
