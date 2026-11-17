"""Gameplay for level 5, Arche: Kathodos, the city of the Descent (GAME_ROADMAP.md "Level 5"). Still Points, the
people, the First Arch, everything that can be rewoven (the Span, the two Stairs, the three Mirrors, restless
causeways, bulwarks, the Garden's loom), the Veil, the Lens Court and the Sunderer, side requests, the Ossuary's
vault, sealed vaults, geode caches, the Ward by region, Divinity Rays, tutorials and voices. Run through
`arche:scenario` (place) and `arche:portal` (the Center's temple current to Arche).

Positions are plan metres (physis_arche_plan: x north, y east); Place's methods take centimetres. Everything placed
here is labelled 'Scene ...' in the outliner folder ArcheScene (the level build owns the folder Arche).

Progress tokens (BP_Physis Flags):
  ,arche, ,at_arche,  arrived / saves load here     ,aeon,  Aeon met     ,reweave,  the First Arch
  ,ar_span,  the Sundered Span    ,ar_stair1, ,ar_stair2,  the Stairs    ,ar_gw, ,ar_ge, ,ar_gn,  each Mirror's guard
  ,ar_mirror_w, ,ar_mirror_e, ,ar_mirror_n,  the Mirrors    ,ar_veil,  all three: the Veil falls
  ,sunderer,  the Sunderer falls    ,maruth,  the Lens-keeper, in person    ,arche_done,  Aeon afterwards
  side requests ,ilun, ,chime, ,oreth, ,tab1, ,tab2, ,tab3, ,tablets, ,sael, ,seedstone,
  the Ossuary ,ar_name1-3, ,ar_vault,;  caches ,ar_cache1-5,
  augmentations ,aug_hp8, ,aug_katana6, ,aug_pistol5, ,aug_defense6, ,aug_agility6,
Encounter rooms 501-599. Tags for BP_ArcheDirector: ArcheScar (hidden once the Sunderer falls), ArcheBloom (shown
then), ArcheMirrorW / E / N (each Mirror's light on the Veil). Markers: TargetPoint tags ArcheArrival (here) and
ArcheReturn (in the Center).

This module stands on the Grove's scenario (physis_grove_scenario: the Place class and its passes), loaded a second
time under another name with Arche's folder, meshes, voices and Still Point rule put in its globals.
"""
import importlib.util
import math
import random
import pathlib

import unreal

import physis_arche_lore as lore
import physis_arche_plan as plan
import physis_gameplay_tools as game
from physis_lore import image_name, voice_name

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
_spec = importlib.util.spec_from_file_location('physis_arche_base', ROOT / 'Content/Python/physis_grove_scenario.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

ARCHE = '/Game/Arche'
MESHES = ARCHE + '/Meshes'
VOICES = ARCHE + '/Audio/Voice'
LEVEL = '/Game/Levels/L_Arche'
CENTER_LEVEL = '/Game/Levels/L_CenterOfTheUniverse'
FOLDER = 'ArcheScene'
M = 100.0
T0, T1, T2 = (t * M for t in plan.TIER)
SERENE = (.55, .85, 1.0)
VIGIL = (.62, .38, 1.0)
PEARL = (1.0, .88, .62)
RED = (1.0, .12, .08)
TEMPLE = (76000.0, 0.0)
SANCTUM = 3400.0 + 600.0
PORTAL = (TEMPLE[0], TEMPLE[1] - 1600.0, SANCTUM + 35.0)
RETURN = (TEMPLE[0], TEMPLE[1] - 1100.0, SANCTUM + 120.0)


def mesh_asset(name):
    """A mesh by its name alone: Arche's own (SM_A*), the Conclave's (SM_CN_, SM_CP_, SM_CE_: the AL), the Grove's
    (SM_GN_, SM_GV_) or a scan (SM_GS_)."""
    if name.startswith('/'):
        return base.asset(name)
    if name.startswith('SM_A'):
        return base.asset(MESHES + '/' + name)
    if name.startswith('SM_C'):
        return base.asset('/Game/Conclave/Meshes/' + name)
    if name.startswith('SM_GS_'):
        return base.asset('/Game/Grove/Scans/' + name)
    return base.asset('/Game/Grove/Meshes/' + name)


base.FOLDER, base.LEVEL, base.VOICES, base.STILL_UNTIL, base.mesh_asset = FOLDER, LEVEL, VOICES, ',sunderer,', mesh_asset
cm, turned, component, props, wrap, asset, cls, sub = base.cm, base.turned, base.component, base.props, base.wrap, base.asset, base.cls, base.sub


class Place(base.Place):
    def __init__(self, ground):
        super().__init__(ground)
        self.sights = []    # (label, where she stands cm, weave actor): each mark must be in plain sight from there
        self.unrigged = []  # animals placed without a skinned mesh (arche:import_rigs not run)
        self.uncut = []     # woven things without a block mesh (Tools/build_physis_arche_weave.py)

    def ok(self, x, y, clear, still):
        mx, my = x / M, y / M
        if plan.rim(mx, my) > .9 or plan.in_water(mx, my, 3.0) or plan.in_chasm(mx, my, 3.0) or plan.on_riser(mx, my, 3.0):
            return False
        if any(math.hypot(x - sx, y - sy) < r + clear for sx, sy, r in self.solids):
            return False
        return not (still and any(math.hypot(x - sx, y - sy) < still for sx, sy in self.stills))

    def enemy(self, level, label, x, y, room=0, z=None):
        mesh, health, scale, hover, entry, kind = lore.ARCHE_ENEMIES[level]
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
            # A living thing: it never fires. It closes, calls, draws back and strikes with its body (arche_shared.animals).
            number, reach = ANIMALS[level]
            for name, value in (('Organic', True), ('Animal', number), ('Reach', reach)):
                actor.set_editor_property(name, value)
        shape = self.reskin(actor, mesh)
        if level in ANIMALS:
            self.rig(actor, shape, mesh)
        self.tag(actor, entry, place, label)
        self.enemies += 1
        return actor

    def rig(self, actor, shape, mesh):
        """The animal's skinned mesh in the actor's Body, with its two animations; the static mesh stays in Shape,
        unseen, for bounds and collision. Without an imported rig (arche:import_rigs) the static mesh is shown."""
        folder = '/Game/Arche/Rigged/'
        stem = mesh[3:]   # SM_AE_Mote -> AE_Mote
        skinned, swim, strike = (unreal.load_asset(folder + name) if unreal.EditorAssetLibrary.does_asset_exist(folder + name) else None
                                 for name in ('SK_' + stem, 'A_%s_Swim' % stem, 'A_%s_Strike' % stem))
        body = next((part for part in actor.get_components_by_class(unreal.SkeletalMeshComponent) if part.get_name().split('_GEN')[0] == 'Body'), None)
        if not (skinned and swim and strike and body):
            self.unrigged.append(stem)
            return
        body.set_skeletal_mesh_asset(skinned)
        play = unreal.SingleAnimationPlayData()
        play.set_editor_property('anim_to_play', swim)
        play.set_editor_property('saved_looping', True)
        play.set_editor_property('saved_playing', True)
        body.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        body.set_editor_property('animation_data', play)
        actor.set_editor_property('Swim', swim)
        actor.set_editor_property('Strike', strike)
        shape.set_editor_property('visible', False)   # in the editor; in play DroneAnimal hides it when Swim starts

    def weave(self, label, mesh, place, yaw=0.0, give='', done='', hold=0.0, loom='', limit=1, need='', hide='', mark=(0.0, 0.0, 200.0), range_m=45.0,
              scale=1.0, drift=260.0, stand=None, folder='Weaves'):
        """BP_Weave: `mesh` standing at `place` (cm, its pivot) once rewoven. mark: where its ring of slivers turns,
        relative to the actor (cm). stand: where she is expected to reweave it from (cm), checked by sights()."""
        actor = self.spawn('BP_Weave', label, place, None, folder, Need=need, Hide=hide, Give=give, Done=done, Hold=float(hold), Loom=loom,
                           Limit=int(limit), Range=range_m * M, Drift=float(drift))
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        shape = component(actor, 'Shape')
        # The same thing cut into blocks, where it has been made (SM_AW_*): sundered, its blocks hang apart, and they
        # fly home when she reweaves it. The blocks hang at least a third of the thing's length away.
        blocks = 'SM_AW_' + mesh[6:]
        cut = unreal.EditorAssetLibrary.does_asset_exist('/Game/Arche/Meshes/' + blocks)
        asset = mesh_asset(blocks if cut else mesh)
        shape.set_static_mesh(asset)
        for slot in range(shape.get_num_materials()):
            shape.set_material(slot, None)
        size = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        shape.set_relative_scale3d(unreal.Vector(*size))
        if cut:
            box = asset.get_bounds().box_extent
            longest = 2 * max(box.x, box.y, box.z) * max(size)
            reach = max(float(drift), .34 * longest)
            actor.set_editor_property('Drift', reach / max(size))
            shape.set_editor_property('bounds_scale', min(12.0, 1.5 + 4.0 * reach / longest))
        else:
            self.uncut.append(mesh)
        for name in ('Mark', 'Glow'):
            part = component(actor, name)
            if part:
                part.set_editor_property('relative_location', unreal.Vector(*mark))
        if stand:
            self.sights.append((label, stand, actor))
        return actor

    def beam(self, label, start, end, colour, tag, width=.6):
        """A shaft of light from start to end (cm): the engine cylinder in the link's beam material, shown by a tag."""
        dx, dy, dz = end[0] - start[0], end[1] - start[1], end[2] - start[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        actor = sub().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, (start[2] + end[2]) / 2),
                                             unreal.Rotator(0, math.degrees(math.atan2(math.hypot(dx, dy), dz)) * -1, math.degrees(math.atan2(dy, dx))))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path(FOLDER + '/Mirrors')
        part = actor.static_mesh_component
        part.set_mobility(unreal.ComponentMobility.MOVABLE)
        part.set_static_mesh(asset('/Engine/BasicShapes/Cylinder'))
        part.set_material(0, asset('/Game/Grove/Materials/M_GRBeam'))
        part.set_collision_profile_name('NoCollision')
        part.set_editor_property('cast_shadow', False)
        part.set_default_custom_primitive_data_vector4(0, unreal.Vector4(colour[0], colour[1], colour[2], 1.0))
        part.set_default_custom_primitive_data_float(4, length)
        actor.set_actor_scale3d(unreal.Vector(width, width, length / 100.0))
        actor.set_editor_property('tags', [tag])
        actor.set_actor_hidden_in_game(True)
        return self.note(actor)


WILD = {1: 8, 2: 9, 3: 10, 4: 11, 5: 12, 6: 13}   # the Ward's levels as Arche's own animals
# ARCHE_ENEMIES level: (BP_TrainingDrone.Animal, how far its blow reaches from its middle, cm)
ANIMALS = {8: (1, 230.0), 9: (2, 300.0), 10: (3, 300.0), 11: (4, 330.0), 12: (5, 350.0), 13: (6, 800.0)}


def pack(p, label, x, y, levels, room=0, spread=700.0, z=None):
    """Enemies round a point. A loose pack (room 0) is a shoal of Arche's animals, as long as their meshes are
    imported; the Ward (the Lens's AL) keeps the rooms it was told to guard."""
    if room == 0 and asset(MESHES + '/SM_AE_Mote', True) is not None:
        levels = tuple(WILD.get(level, level) for level in levels)
    return base.pack(p, label, x, y, levels, room, spread, z)


def cache(p, n, title, x, y, z=None):
    token = ',ar_cache%d,' % n
    z = p.floor(x, y) if z is None else z
    p.relic('Geode Cache %d' % n, (x, y, z + 110), token, lore.MESSAGES['cache'], divinity=40.0, mesh='SM_AN_Cache', scale=1.3)
    p.light('Geode Glow %d' % n, (x, y, z + 160), SERENE, 1500, 500, 'Items')
    p.site(title, x, y, 2, token)


def dress(p, label, rows, folder, origin=(0.0, 0.0)):
    for k, (mesh, x, y, yaw, scale, solid) in enumerate(rows):
        px, py = cm(origin[0] + x, origin[1] + y)
        p.mesh('%s %d' % (label, k), mesh, (px, py, p.g.at(px, py) - 3), yaw, scale, folder, solid=solid)


def stand_at(p, x, y, z=None):
    return (x, y, (p.floor(x, y) if z is None else z) + 96.0)


# ---------------------------------------------------------------- the city between the set pieces

SAFE = ((plan.LANDING, 55.0), (plan.HEARTHOLD, 75.0), (plan.FIRST_ARCH, 30.0))   # no enemy is added this near (m)
# What stands beside the roads: (mesh, forward m, sideways m, yaw relative to the road, scale, solid cm or 0, lit)
ROADSIDE = {
    'shrine': (('SM_AN_Obelisk', 0.0, 0.0, 20.0, 1.0, 120, False), ('SM_AN_Urn', 1.6, 1.2, 0.0, 1.0, 60, False), ('SM_AN_Urn', -1.5, 1.4, 40.0, .8, 50, False),
               ('SM_AN_Lantern', 0.4, -2.2, 0.0, 1.0, 40, True)),
    'colonnade': (('SM_AN_Column', -7.5, 0.0, 0.0, 1.0, 90, False), ('SM_AN_ColumnBroken', -2.5, 0.0, 70.0, 1.0, 90, False),
                  ('SM_AN_Column', 2.5, 0.0, 0.0, 1.0, 90, False), ('SM_AN_ColumnBroken', 7.5, 0.0, 200.0, 1.0, 90, False),
                  ('SM_AN_Urn', 0.0, 2.4, 0.0, 1.0, 60, False)),
    'house': (('SM_AN_House0', 0.0, 4.0, -90.0, 1.0, 650, False), ('SM_AN_Bench', 5.5, -3.0, 0.0, 1.0, 130, False),
              ('SM_AN_Urn', -5.0, -2.4, 0.0, 1.0, 60, False), ('SM_AN_Lantern', 3.0, -4.6, 0.0, 1.0, 40, True)),
    'workshop': (('SM_AN_House1', 0.0, 4.0, -90.0, 1.0, 550, False), ('SM_AN_Urn', 4.6, -1.6, 0.0, 1.0, 60, False), ('SM_AN_Urn', 5.6, -2.6, 30.0, .8, 50, False),
                 ('SM_AN_ColumnBroken', -5.5, -2.0, 120.0, 1.0, 90, False), ('SM_AN_Lantern', -2.6, -4.4, 0.0, 1.0, 40, True)),
    'rest': (('SM_AN_Basin', 0.0, 0.0, 0.0, 1.0, 380, False), ('SM_AN_Bench', 0.0, 5.0, 90.0, 1.0, 130, False), ('SM_AN_Bench', 5.0, 0.0, 0.0, 1.0, 130, False),
             ('SM_AN_Lantern', -4.0, -4.0, 0.0, 1.0, 40, True), ('SM_AN_Lantern', 4.0, 4.4, 0.0, 1.0, 40, True)),
    'court': (('SM_AV_Crystal2', 0.0, 0.0, 0.0, 1.2, 150, False), ('SM_AV_Crystal1', 3.2, 1.0, 60.0, 1.0, 100, False), ('SM_AV_Crystal1', -2.6, 2.4, 140.0, .9, 100, False),
              ('SM_AV_Crystal0', 1.0, -3.0, 220.0, 1.1, 80, False), ('SM_AV_Crystal0', -3.0, -1.6, 300.0, .9, 80, False), ('SM_AN_Bench', 0.6, 5.6, 90.0, 1.0, 130, False)),
}
# Shoals and patrols by tier: what a pack is made of (ARCHE_ENEMIES levels 1 to 5; pack() turns a shoal into animals).
SHOALS = {0: ((1, 1, 2), (1, 2), (1, 1, 1), (2, 3)), 1: ((2, 3, 4), (3, 4), (2, 2, 4), (1, 1, 2, 2)), 2: ((4, 5), (3, 4, 5), (4, 4), (2, 3, 4))}
PATROLS = {0: ((1, 1, 2), (2, 2), (1, 3)), 1: ((2, 3), (2, 4), (3, 3, 1)), 2: ((4, 5), (3, 5, 5), (4, 4, 2))}


def along(points, step, start):
    """Points every `step` metres along a road: (x, y, heading in radians)."""
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
    """The city between the set pieces (author, 2026-11-17: "the level feels too empty"): ruins, shrines and crystal
    courts beside every road, a shoal of animals out in the open ground every 90 m or so, and the Ward's patrols
    on the roads themselves. Seeded, so a rerun places the same city. Nothing is put on a road, in water, on a
    riser, in the Chasm, on a set piece or (enemies) near the Landing, the Hearthold or the First Arch."""
    rng = random.Random(5)
    kinds = sorted(ROADSIDE)
    for row in lore.KEEPERS:   # the keepers are placed later (people()): keep their ground free
        p.solids.append((row[5][0] * M, row[5][1] * M, 450.0))
    made = {'roadside': 0, 'shoals': 0, 'patrols': 0}

    def tier(x):
        return 0 if x < plan.TIER2_X - 6 else 1 if x < plan.TIER3_X - 6 else 2

    def safe(x, y):
        return any(math.hypot(x - sx, y - sy) < r for (sx, sy), r in SAFE)

    def off_road(x, y, pad):
        for _, _, half, points in plan.PATHS:
            for (ax, ay), (bx, by) in zip(points, points[1:]):
                t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
                if math.hypot(x - ax - t * (bx - ax), y - ay - t * (by - ay)) < half + pad:
                    return False
        return True

    for name, kind, half, points in plan.PATHS:
        side = 1
        for k, (x, y, heading) in enumerate(along(points, 34.0, 14.0)):
            side = -side
            reach = half + rng.uniform(13.0, 24.0)
            cx, cy = x - math.sin(heading) * reach * side, y + math.cos(heading) * reach * side
            what = rng.choice(kinds)
            radius = 900.0 if what in ('house', 'workshop') else 600.0
            if not off_road(cx, cy, 7.0) or not p.ok(cx * M, cy * M, radius, 1500.0):
                continue
            face = heading + (math.pi if side > 0 else 0.0)   # the cluster's own "forward" runs along the road, its back to the open ground
            for n, (mesh, forward, sideways, yaw, scale, solid, lit) in enumerate(ROADSIDE[what]):
                px = (cx + math.cos(face) * forward - math.sin(face) * sideways) * M
                py = (cy + math.sin(face) * forward + math.cos(face) * sideways) * M
                label = 'Roadside %s %d %s %d' % (name, k, what, n)
                p.mesh(label, mesh, (px, py, p.g.at(px, py) - 4), math.degrees(face) + yaw, scale, 'Roadside', solid=solid)
                if lit:
                    p.light(label + ' Light', (px, py, p.g.at(px, py) + 300), SERENE, 2200, 1200, 'Roadside')
            p.solids.append((cx * M, cy * M, radius))
            made['roadside'] += 1
    # Shoals out in the open ground, to either side of every road and trail.
    for name, kind, half, points in plan.PATHS:
        side = -1
        for k, (x, y, heading) in enumerate(along(points, 88.0, 50.0)):
            side = -side
            reach = half + rng.uniform(34.0, 60.0)
            cx, cy = x - math.sin(heading) * reach * side, y + math.cos(heading) * reach * side
            if safe(cx, cy) or not p.ok(cx * M, cy * M, 500.0, 3000.0):
                continue
            pack(p, 'Shoal %s %d' % (name, k), cx * M, cy * M, rng.choice(SHOALS[tier(cx)]), 0, 650)
            made['shoals'] += 1
    # The Ward walks the roads (not the trails): machines, so pack() is not asked to turn them into animals.
    for name, kind, half, points in plan.PATHS:
        if kind != 'road':
            continue
        for k, (x, y, heading) in enumerate(along(points, 85.0, 40.0)):
            if safe(x, y) or plan.in_chasm(x, y, 8.0):
                continue
            base.pack(p, 'Patrol %s %d' % (name, k), x * M, y * M, rng.choice(PATROLS[tier(x)]), 0, 500)
            made['patrols'] += 1
    p.life = made


# ---------------------------------------------------------------- the regions

def landing(p):
    lx, ly = cm(*plan.LANDING)
    floor = p.g.at(lx, ly)
    p.spawn('BP_ArcheCurrent', 'Current Home', (lx, ly, floor + 25), None, 'Landing', Need='', Dest=2, Radius=180.0)
    p.solids.append((lx, ly, 500))
    p.light('Landing Glow', (lx, ly, floor + 600), SERENE, 9000, 2800, 'Landing')
    sx, sy = cm(*plan.LANDING_STILL)
    p.check('Landing', sx, sy, lore.QUEST_ARRIVE, 800.0)
    p.marks['Arrival'] = p.at(sx, sy, 120)
    p.marker('Arrival', p.marks['Arrival'], 'ArcheArrival', 'Landing')
    cache(p, 1, 'Landing Cache', *cm(-470.0, 4.0))


def processional(p):
    pack(p, 'Processional', *cm(-424.0, 66.0), (1, 1, 2), 501, 600)
    p.encounter('Processional', *cm(-424.0, 66.0), 501, ',ar_road,', 'The Ward\'s patrol is down. The road north is clear.')
    pack(p, 'Lower Road', *cm(-352.0, 44.0), (1, 2), 0, 600)
    pack(p, 'Ossuary Way', *cm(-372.0, 140.0), (2, 2, 1), 0, 700)
    for k, (x, y) in enumerate(((-452.0, 30.0), (-396.0, 26.0))):
        px, py = cm(x, y)
        p.mesh('Processional Stele %d' % k, 'SM_AN_Obelisk', (px, py, p.g.at(px, py) - 5), 40.0 * k, 1.0, 'Processional', solid=120)


HEARTH = (('SM_AN_House0', 22.0, -24.0, 150.0, 1.0, 650), ('SM_AN_House1', 26.0, 2.0, 180.0, 1.0, 550), ('SM_AN_House0', 20.0, 28.0, 215.0, 1.0, 650),
          ('SM_AN_House1', -26.0, -22.0, 40.0, 1.0, 550), ('SM_AN_House0', -30.0, 6.0, 0.0, 1.0, 650), ('SM_AN_House1', -22.0, 32.0, -40.0, 1.0, 550),
          ('SM_AN_Basin', 0.0, 8.0, 0.0, 1.0, 380), ('SM_AN_Bench', 5.0, 14.0, 60.0, 1.0, 130), ('SM_AN_Bench', -5.0, 2.0, 240.0, 1.0, 130),
          ('SM_AN_Urn', 10.0, -10.0, 0.0, 1.0, 60), ('SM_AN_Urn', 11.2, -8.8, 30.0, .8, 50), ('SM_AN_Urn', -12.0, 20.0, 0.0, 1.0, 60),
          ('SM_AN_Lantern', 8.0, 6.0, 0.0, 1.0, 40), ('SM_AN_Lantern', -8.0, 14.0, 0.0, 1.0, 40), ('SM_AN_Lantern', 2.0, -14.0, 0.0, 1.0, 40),
          ('SM_AN_Lantern', -16.0, -6.0, 0.0, 1.0, 40), ('SM_AN_Obelisk', 4.0, -22.0, 20.0, 1.0, 120), ('SM_AN_Obelisk', 14.0, 18.0, 70.0, 1.0, 120))


def hearthold(p):
    hx, hy = plan.HEARTHOLD
    p.check('Hearthold', *cm(*plan.HEARTHOLD_STILL), 'The Hearthold. Speak to Aeon, the eldest of the Serene.')
    dress(p, 'Hearthold', HEARTH, 'Hearthold', (hx, hy))
    for k, (mesh, x, y, yaw, scale, solid) in enumerate(HEARTH):
        if mesh == 'SM_AN_Lantern':
            lx, ly = cm(hx + x, hy + y)
            p.light('Hearthold Lantern %d' % k, p.at(lx, ly, 300), SERENE, 2600, 1300, 'Hearthold')
    for row in lore.PEOPLE:
        if row[5][0] < -200.0:
            p.solids.append((row[5][0] * M, row[5][1] * M, 250))
    # The seedstone's bed: where Sael plants it once it is brought (the first new thing in Kathodos).
    sx, sy = cm(hx - 4.0, hy + 26.0)
    seedling = p.mesh('Sael\'s Crystal', 'SM_AV_Crystal0', (sx, sy, p.g.at(sx, sy) - 10), 0.0, .7, 'Hearthold', collide=False, tags=('ArcheBloom',))
    seedling.set_actor_hidden_in_game(True)


def first_arch(p):
    ax, ay = cm(*plan.FIRST_ARCH)
    floor = p.g.at(ax, ay)
    yaw = math.degrees(math.atan2(plan.CHASM_CROSS_Y - 24.0, plan.SPAN_SOUTH[0] + 240.0))
    p.mesh('First Arch', 'SM_AN_Arch', (ax, ay, floor - 10), yaw, 1.0, 'Arch')
    sx, sy = turned(-350.0, 520.0, yaw)
    p.switch('The First Arch', (ax + sx, ay + sy, floor), yaw, 'SM_AN_Pedestal', False, None, 'Arch', Need=',aeon,', Give=',reweave,',
             Denied=lore.MESSAGES['arch_denied'], Done=lore.ARCH_DONE)
    p.light('Arch Glow', (ax, ay, floor + 700), PEARL, 3600, 1600, 'Arch')
    p.solids.append((ax, ay, 700))
    pack(p, 'Arch Way', *cm(-246.0, 44.0), (1, 1), 0, 500)


def over(knot, toward):
    """Hangs a rim knot out over the Chasm's wall (`toward` cm along x) so it shows from the floor; she still lands
    on the rim where it was placed."""
    at, perch = knot.get_actor_location(), knot.get_editor_property('Perch')
    knot.set_actor_location(unreal.Vector(at.x + toward, at.y, at.z), False, False)
    knot.set_editor_property('Perch', unreal.Vector(perch.x - toward, perch.y, perch.z))


def chasm(p):
    # The Sundered Span: 32 m of bridge over the 26 m Chasm, its deck at the Lower Tier's level. Rewoven for good:
    # the map's shortcut, and the proof of the ability.
    mx = plan.chasm_x(plan.CHASM_CROSS_Y) * M
    my = plan.CHASM_CROSS_Y * M
    sx, nx = plan.SPAN_SOUTH[0] * M, plan.SPAN_NORTH[0] * M
    p.weave('The Span', 'SM_AN_Span', (mx, my, T0), 0.0, give=',ar_span,', done=lore.MESSAGES['span'], need=',reweave,', mark=(0.0, 0.0, 260.0),
            range_m=60.0, drift=700.0, stand=stand_at(p, sx - 900.0, my), folder='Chasm')
    p.light('Span Scar', (mx, my, T0 + 500), VIGIL, 2600, 2200, 'Chasm', ('ArcheScar',))
    # The link's knots (from Earth) on the rims: a way out of the Chasm for whoever falls in. The northern one wakes
    # only once the Span stands, so the link alone never crosses.
    south = p.anchor('Chasm South', sx - 700.0, my + 900.0, need=',resonance,', range_m=70.0, lift=400.0, folder='Chasm')
    over(south, 800.0)
    north = p.anchor('Chasm North', nx + 700.0, my - 900.0, need=',ar_span,', range_m=70.0, lift=400.0, folder='Chasm')
    over(north, -800.0)
    pit = (mx, my, p.g.at(mx, my) + 96.0)
    p.hops.append(('Chasm floor south', pit, south))
    p.hops.append(('Chasm floor north', pit, north))
    climb(p)
    for y in (-180.0, 220.0):
        cx = plan.chasm_x(y) * M
        knot = p.anchor('Chasm South %d' % y, cx - (plan.CHASM_RIM + 7.0) * M, y * M, need=',resonance,', range_m=70.0, lift=400.0, folder='Chasm')
        over(knot, 800.0)
        p.hops.append(('Chasm floor %d' % y, (cx, y * M, p.g.at(cx, y * M) + 96.0), knot))


CLIMB_TOP_Y, CLIMB_SLOPE = 55.0, 20.0   # the Climb's head (m, 25 m east of the Span) and its pitch in degrees


def wall_x(p, y, z):
    """Where the Chasm's south wall stands at height z on the line y (cm): the northernmost ground at least that high."""
    centre = plan.chasm_x(y / M) * M
    x = centre - 2600.0
    for step in range(105):
        if p.g.at(x + 25.0, y) < z:
            break
        x += 25.0
    return x


def climb(p):
    """The Climb: the way back up for whoever falls into the Chasm. Causeway slabs hung against the south wall, as
    the First Ones hung their stepping slabs, rising from the floor to the south rim beside the Span. It is always
    there (no ability, nothing to reweave) and it leads only to the south side, so it does not cross the Chasm."""
    slope = math.radians(CLIMB_SLOPE)
    run, rise = 840.0 * math.cos(slope), 840.0 * math.sin(slope)   # slabs are 9 m long: 0.6 m of overlap
    top_y = CLIMB_TOP_Y * M
    rim = p.g.at(wall_x(p, top_y, T0 - 300.0) - 300.0, top_y)
    foot_y = top_y
    count = 0
    while True:   # how many slabs it takes from the floor at its foot
        count += 1
        foot_y = top_y + count * run
        floor = p.g.at(plan.chasm_x(foot_y / M) * M, foot_y)
        if rim - count * rise <= floor + 40.0 or count > 30:
            break
    slabs = []
    for k in range(count):
        y = top_y + (count - k - .5) * run
        z = rim - (count - k - .5) * rise
        x = wall_x(p, y, z) + 170.0 - 70.0   # 3.4 m wide, 0.7 m of it inside the wall
        ahead = wall_x(p, y - run, z) - wall_x(p, y + run, z)
        yaw = -90.0 + max(-6.0, min(6.0, math.degrees(math.atan2(ahead, 2 * run))))   # uphill is towards -y, following the wall
        p.mesh('Climb %02d' % k, 'SM_AN_Causeway', (x, y, z), yaw, folder='Chasm', pitch=CLIMB_SLOPE)
        slabs.append((round(x), round(y), round(z), round(yaw, 1)))
    # The landing: a level slab let into the rim, and lanterns at the foot and the head so it is found from the floor.
    # two level slabs side by side carry on from the last one and reach back into the rim
    last_x, last_y = slabs[-1][0], slabs[-1][1]
    head_x, head_y = last_x - 150.0, last_y - 450.0 * math.cos(slope) - 420.0
    for k, dx in enumerate((0.0, -320.0, -640.0)):
        p.mesh('Climb Landing %d' % k, 'SM_AN_Causeway', (last_x + dx, head_y, rim + 4.0), -90.0, folder='Chasm')
    foot = (plan.chasm_x(foot_y / M) * M, foot_y + 250.0)
    for label, (x, y) in (('Foot A', (foot[0] - 250.0, foot[1])), ('Foot B', (foot[0] + 250.0, foot[1])), ('Head', (last_x - 900.0, head_y - 520.0))):
        p.mesh('Climb Lantern ' + label, 'SM_AN_Lantern', (x, y, p.g.at(x, y) - 5.0), folder='Chasm')
        p.light('Climb Light ' + label, (x, y, p.g.at(x, y) + 330.0), SERENE, 1800, 1800, 'Chasm')
    p.climb = {'slabs': slabs, 'rim': round(rim), 'foot': [round(v) for v in foot], 'count': count}


def concourse(p):
    ux, uy = cm(*plan.CONCOURSE)
    p.check('Concourse', ux, uy, lore.QUEST_MIRRORS)
    # Two bulwarks on the road to the First Stair, and the Ward's Lancers to try them on.
    for k, (x, y, yaw) in enumerate(((-24.0, 22.0, 0.0), (-10.0, -12.0, 0.0))):
        bx, by = cm(x, y)
        p.weave('Concourse Bulwark %d' % k, 'SM_AN_Bulwark', (bx, by, p.g.at(bx, by) - 5), yaw, hold=14.0, need=',reweave,', mark=(0.0, 0.0, 170.0),
                range_m=30.0, drift=160.0, stand=stand_at(p, bx - 600.0, by), folder='Bulwarks')
    for k, (level, x, y) in enumerate(((2, 22.0, 26.0), (2, 26.0, -18.0), (1, 12.0, 4.0))):
        p.enemy(level, 'Concourse %d' % k, x * M, y * M, 502)
    p.encounter('Concourse', 20.0 * M, 4.0 * M, 502, ',ar_concourse,', 'The road to the First Stair is clear.')
    for label, (x, y), levels in (('Cistern Way', (-36.0, -84.0), (1, 2)), ('Lower East', (-40.0, 150.0), (1, 1, 3)), ('Lower West', (-60.0, -220.0), (2, 3))):
        pack(p, label, *cm(x, y), levels, 0, 700)
    cache(p, 2, 'Lower Tier Cache', *cm(-30.0, 190.0))
    pack(p, 'Lower Cache Keeper', *cm(-30.0, 190.0), (5,), 0, 500)


def stair(p, n, foot_x, level, give, done, room, guard):
    """A grand stair against a riser: 18 m long, its top landing flush with the tier above. Rewoven for good."""
    x = (foot_x + plan.RISER - 9.0 + .4) * M
    p.weave('Stair %d' % n, 'SM_AN_Stair', (x, 0.0, level), 0.0, give=give, done=done, need=',reweave,', mark=(-400.0, 0.0, 900.0), range_m=60.0,
            drift=600.0, stand=stand_at(p, x - 2400.0, 0.0), folder='Stairs')
    p.light('Stair Scar %d' % n, (x, 0.0, level + 900), VIGIL, 2400, 2000, 'Stairs', ('ArcheScar',))
    for k, (lv, dx, dy) in enumerate(guard):
        gx, gy = x + dx, dy
        p.enemy(lv, 'Stair %d Guard %d' % (n, k), gx, gy, room, p.g.at(gx, gy))
    p.encounter('Stair %d' % n, x - 1800.0, 0.0, room, ',ar_gs%d,' % n, 'The stair\'s guard is down.')


def stairs(p):
    stair(p, 1, plan.STAIR1[0], T0, ',ar_stair1,', lore.MESSAGES['stair1'], 503, ((5, -2000.0, 0.0), (1, -2300.0, 700.0), (1, -2300.0, -700.0)))
    stair(p, 2, plan.STAIR2[0], T1, ',ar_stair2,', lore.MESSAGES['stair2'], 504, ((5, -2000.0, 300.0), (3, -2400.0, -600.0), (2, -2600.0, 800.0)))


def mirror(p, side, x, y, z, need):
    """A great Mirror: rewoven for good, it turns toward the Veil; a shaft of light from it to the Veil shows then."""
    gx, gy = cm(*plan.GATE)
    yaw = math.degrees(math.atan2(gy - y, gx - x))
    token = ',ar_mirror_%s,' % side[0]
    back = turned(-500.0, 0.0, yaw)
    p.weave('Mirror ' + side, 'SM_AN_Mirror', (x, y, z), yaw, give=token, done=lore.MESSAGES['mirror_' + side[0]], need=need, mark=(0.0, 0.0, 460.0),
            range_m=40.0, drift=420.0, stand=(x + back[0], y + back[1], z + 96.0), folder='Mirrors')
    tag = 'ArcheMirror' + side[0].upper()
    p.beam('Mirror Light ' + side, (x, y, z + 460.0), (gx, gy, T2 + 500.0), PEARL, tag)
    glow = p.light('Mirror Glow ' + side, (x, y, z + 460.0), PEARL, 6000, 2400, 'Mirrors', (tag,))
    glow.set_actor_hidden_in_game(True)


def cisterns(p):
    sx, sy = cm(*plan.CISTERN_SHORE)
    p.check('Cistern Shore', sx, sy, 'The Cisterns. Reweave the causeway to the Mirror\'s island; it will not hold long.')
    ix, iy, ir = (v * M for v in plan.CISTERN_ISLE)
    top = (plan.TIER[0] + 1.0) * M
    # A standing pier from the bank (two spans on broken columns), then two restless spans to the island.
    x = plan.CISTERN_ISLE[0] * M
    edge = iy + ir                                   # the island's near edge (toward the shore, +y)
    spots = [edge + 450.0 + k * 900.0 for k in range(4)]     # span centres from the island outward
    for k, y in enumerate(spots[2:]):
        z = top - 30.0 - 30.0 * k
        p.mesh('Cistern Pier %d' % k, 'SM_AN_Causeway', (x, y, z), 90.0, 1.0, 'Cisterns')
        p.mesh('Cistern Pier Foot %d' % k, 'SM_AN_ColumnBroken', (x, y, z - 100.0 - 450.0), 0.0, (1.0, 1.0, 1.0), 'Cisterns')
    pier_end = (x, spots[2] - 250.0, top - 30.0 + 96.0)
    a = p.weave('Cistern Span 1', 'SM_AN_Causeway', (x, spots[1], top - 15.0), 90.0, hold=9.0, need=',reweave,', mark=(0.0, 0.0, 180.0), range_m=15.0,
                drift=200.0, stand=pier_end, folder='Cisterns')
    p.weave('Cistern Span 0', 'SM_AN_Causeway', (x, spots[0], top), 90.0, hold=9.0, need=',reweave,', mark=(0.0, 0.0, 180.0), range_m=15.0, drift=200.0,
            stand=(x, spots[1], top - 15.0 + 96.0), folder='Cisterns')
    # After the Sunderer the whole causeway stands for good.
    for k, y in enumerate(spots[:2]):
        whole = p.mesh('Cistern Causeway %d' % k, 'SM_AN_Causeway', (x, y, top - 15.0 * k), 90.0, 1.0, 'Cisterns', tags=('ArcheBloom',))
        whole.set_actor_hidden_in_game(True)
    for k, (level, dx, dy) in enumerate(((5, 300.0, -300.0), (2, -500.0, -500.0))):
        p.enemy(level, 'Cistern Guard %d' % k, ix + dx, iy + dy, 511, top)
    p.encounter('Cistern Guard', ix, iy, 511, ',ar_gw,', lore.MESSAGES['mirror_guard'], z=top)
    mirror(p, 'west', ix, iy - 300.0, top, ',ar_gw,')
    p.relic('Seedstone', (ix - 600.0, iy + 300.0, top + 115), ',seedstone,', lore.MESSAGES['seedstone'], mesh='SM_AN_Seedstone', scale=1.4)
    cache(p, 3, 'Cistern Cache', ix + 650.0, iy + 200.0, z=top)
    pack(p, 'Cistern Bank', *cm(-20.0, -128.0), (1, 1, 2), 0, 600)


def middle(p):
    p.check('Middle Tier', *cm(*plan.MIDDLE_STILL), 'The Middle Tier. East to the Crystal Garden; north to the Second Stair.')
    for label, (x, y), levels in (('Middle Road', (200.0, 14.0), (2, 3)), ('Makers Row West', (160.0, -90.0), (1, 2, 2)), ('Garden Way', (142.0, 110.0), (1, 4)),
                                  ('Middle East', (220.0, 150.0), (2, 4))):
        pack(p, label, *cm(x, y), levels, 0, 700)
    tx, ty = cm(176.0, -52.0)
    p.relic('Record Tablet 2', (tx, ty, p.g.at(tx, ty) + 115), ',tab2,', lore.MESSAGES['tablet'], mesh='SM_AN_Tablet', scale=1.5)
    dress(p, 'Makers Row', (('SM_AN_House1', 170.0, -40.0, 90.0, 1.0, 550), ('SM_AN_ColumnBroken', 184.0, -56.0, 0.0, 1.0, 150),
                            ('SM_AN_Bench', 164.0, -56.0, 20.0, 1.0, 130), ('SM_AN_Obelisk', 150.0, -30.0, 0.0, 1.0, 120)), 'Middle')


def garden(p):
    p.check('Crystal Garden', *cm(*plan.GARDEN_STILL), 'The Crystal Garden. The Mirror stands on the pinnacle; the Garden\'s loom holds two shapes.')
    px, py, pr, ph = plan.PINNACLE
    top = T1 + ph * M
    # The Garden's loom holds two shapes of three. The stair climbs to the pinnacle's height 7 m short of it, a
    # causeway spans the gap; the third shape is a bulwark by the guards, and weaving it drops the oldest of the others.
    foot = (px - pr - 7.0 - 18.0 + 9.0) * M
    stair_x = foot
    p.weave('Garden Stair', 'SM_AN_Stair', (stair_x, py * M, T1), 0.0, loom='garden', limit=2, need=',reweave,', mark=(-400.0, 0.0, 900.0), range_m=55.0,
            drift=600.0, stand=stand_at(p, stair_x - 2200.0, py * M), folder='Garden')
    landing_x = stair_x + 900.0
    p.weave('Garden Causeway', 'SM_AN_Causeway', (landing_x + 380.0, py * M, top), 0.0, loom='garden', limit=2, need=',reweave,', mark=(0.0, 0.0, 180.0),
            range_m=40.0, drift=220.0, stand=(landing_x - 100.0, py * M, top + 96.0), folder='Garden')
    bx, by = stair_x - 2600.0, py * M + 1500.0
    p.weave('Garden Bulwark', 'SM_AN_Bulwark', (bx, by, p.g.at(bx, by) - 5), 200.0, loom='garden', limit=2, need=',reweave,', mark=(0.0, 0.0, 170.0),
            range_m=30.0, drift=160.0, stand=stand_at(p, bx - 600.0, by), folder='Garden')
    for k, (level, dx, dy) in enumerate(((5, -3000.0, -400.0), (4, -3300.0, 500.0), (1, -2900.0, 900.0))):
        ex, ey = stair_x + dx, py * M + dy
        p.enemy(level, 'Garden Guard %d' % k, ex, ey, 521, p.g.at(ex, ey))
    p.encounter('Garden Guard', stair_x - 3000.0, py * M, 521, ',ar_ge,', lore.MESSAGES['mirror_guard'])
    mirror(p, 'east', px * M + 200.0, py * M, top, ',ar_ge,')
    p.relic('Ilun\'s Chime', (px * M - 100.0, py * M + 500.0, top + 115), ',chime,', lore.MESSAGES['chime'], mesh='SM_AN_Chime', scale=1.6)
    cache(p, 4, 'Garden Cache', *cm(214.0, 214.0))
    pack(p, 'Garden Cache Keeper', *cm(214.0, 214.0), (5, 1, 1), 0, 500)


def galleries(p):
    p.check('Galleries', *cm(*plan.GALLERY_STILL), 'The Galleries. The stair reaches most of the way; the link will take you the rest.')
    mx, my, mr, mh = plan.MESA
    top = T2 + mh * M
    # A stair rewoven against the mesa's south-west face climbs 12 of its 18 m; a knot of the grove's kind on the
    # mesa's edge draws her the rest (the other world's ability opens this one's door).
    a = math.atan2(plan.GALLERY_STILL[1] - my, plan.GALLERY_STILL[0] - mx)
    ux, uy = math.cos(a), math.sin(a)
    yaw = math.degrees(a) + 180.0
    sx, sy = (mx + ux * (mr + 6.0 + 9.0 + 1.0)) * M, (my + uy * (mr + 6.0 + 9.0 + 1.0)) * M
    p.weave('Gallery Stair', 'SM_AN_Stair', (sx, sy, T2), yaw, give=',ar_gallery,', need=',reweave,', mark=(-400.0, 0.0, 900.0), range_m=55.0, drift=600.0,
            stand=stand_at(p, sx + ux * 2200.0, sy + uy * 2200.0), folder='Galleries')
    landing_ = (sx - ux * 800.0, sy - uy * 800.0, T2 + 1200.0 + 96.0)
    knot = p.anchor('Gallery Knot', (mx + ux * (mr - 3.0)) * M, (my + uy * (mr - 3.0)) * M, top, need=',resonance,', range_m=40.0, lift=260.0,
                    folder='Galleries')
    p.hops.append(('Gallery stair to mesa', landing_, knot))
    for k, (level, bearing, r) in enumerate(((4, 40.0, 700.0), (1, 160.0, 800.0), (1, 280.0, 800.0))):
        b = math.radians(bearing)
        p.enemy(level, 'Gallery Guard %d' % k, mx * M + math.cos(b) * r, my * M + math.sin(b) * r, 531, top)
    p.encounter('Gallery Guard', mx * M, my * M, 531, ',ar_gn,', lore.MESSAGES['mirror_guard'], z=top)
    mirror(p, 'north', mx * M - ux * 300.0, my * M - uy * 300.0, top, ',ar_gn,')
    p.relic('Record Tablet 3', (mx * M + 500.0, my * M - 500.0, top + 115), ',tab3,', lore.MESSAGES['tablets'], mesh='SM_AN_Tablet', scale=1.5)
    pack(p, 'Gallery Way', *cm(300.0, 120.0), (2, 4), 0, 700)
    cache(p, 5, 'Upper Tier Cache', *cm(300.0, -150.0))
    pack(p, 'Upper Cache Keeper', *cm(300.0, -150.0), (5, 4), 0, 600)


WALL_SLOTS = 40


def court(p):
    cx, cy = cm(*plan.COURT)
    radius = plan.COURT_WALL * M
    p.check('Upper Tier', *cm(*plan.UPPER_STILL), 'The Upper Tier. The Veil stands in the Lens Court\'s wall.')
    for k in range(WALL_SLOTS):
        bearing = 180.0 + k * 360.0 / WALL_SLOTS
        b = math.radians(bearing)
        x, y = cx + math.cos(b) * radius, cy + math.sin(b) * radius
        if k == 0:
            p.mesh('Veil Frame', 'SM_AN_GateFrame', (x, y, T2 - 30), bearing, 1.0, 'Court')
            p.rise('The Veil', 'SM_AN_Veil', (x, y, T2 - 10), ',ar_veil,', -1150.0, bearing, 1.0, 260.0, 'Court')
            p.light('Veil Light', (x, y, T2 + 500), VIGIL, 5200, 2200, 'Court', ('ArcheScar',))
        elif k not in (1, WALL_SLOTS - 1) or True:
            p.mesh('Court Wall %d' % k, 'SM_AN_Wall', (x, y, p.g.at(x, y) - 60), bearing, (1, 1.02, 1.06), 'Court')
    gx, gy = cm(*plan.GATE)
    p.require('Veil Lock', (gx, gy, T2 + 600), (',ar_mirror_w,', ',ar_mirror_e,', ',ar_mirror_n,'), ',ar_veil,', lore.MESSAGES['veil'])
    p.check('Lens Court', *cm(*plan.COURT_STILL), lore.QUEST_SUNDERER)
    lx, ly = cm(*plan.LENS)
    # The Lens stands twice: lit until the Sunderer falls (tag ArcheScar), then dark (tag ArcheBloom: the same mesh
    # with its lights' slot in a material that has gone out).
    p.mesh('Sundering Lens', 'SM_AN_Lens', (lx, ly, T2 - 20), 0.0, 1.0, 'Court', solid=1900, tags=('ArcheScar',))
    dark = p.mesh('Sundering Lens Dark', 'SM_AN_Lens', (lx, ly, T2 - 20), 0.0, 1.0, 'Court', tags=('ArcheBloom',))
    dark.set_actor_hidden_in_game(True)
    out = asset(ARCHE + '/Materials/MI_AR_GlowOff')
    lens = mesh_asset('SM_AN_Lens')
    if lens is not None and out is not None:
        for index, slot in enumerate(lens.get_editor_property('static_materials')):
            if str(slot.get_editor_property('imported_material_slot_name')) == 'CN_Glow' or str(slot.get_editor_property('material_slot_name')) == 'CN_Glow':
                dark.static_mesh_component.set_material(index, out)
    p.light('Lens Light', (lx - 600, ly, T2 + 2200), VIGIL, 26000, 9000, 'Court', ('ArcheScar',))
    # The Sunderer and its Ward, and four bulwarks to reweave between her and its fire.
    p.enemy(7, 'Sunderer', cx + 600.0, cy, 552, T2)
    for k, (level, bearing, r) in enumerate(((5, 60.0, 1900.0), (5, 300.0, 1900.0), (1, 120.0, 1500.0), (1, 240.0, 1500.0), (1, 180.0, 1100.0), (3, 0.0, 2300.0))):
        b = math.radians(bearing)
        p.enemy(level, 'Sunderer Ward %d' % k, cx + math.cos(b) * r, cy + math.sin(b) * r, 552, T2)
    for k, bearing in enumerate((135.0, 225.0, 45.0, 315.0)):
        b = math.radians(bearing)
        bx, by = cx + math.cos(b) * 1500.0, cy + math.sin(b) * 1500.0
        p.weave('Court Bulwark %d' % k, 'SM_AN_Bulwark', (bx, by, T2 - 5), bearing + 180.0, hold=14.0, need=',reweave,', mark=(0.0, 0.0, 170.0), range_m=30.0,
                drift=160.0, stand=(bx - math.cos(b) * 500.0, by - math.sin(b) * 500.0, T2 + 96.0), folder='Bulwarks')
    p.encounter('Sunderer', cx, cy, 552, ',sunderer,', lore.MESSAGES['sunderer'], lore.QUEST_MARUTH, z=T2)
    for k, bearing in enumerate((90.0, 270.0)):
        b = math.radians(bearing)
        p.pickup(0, 'Court Capsule %d' % k, cx + math.cos(b) * 2600.0, cy + math.sin(b) * 2600.0, T2)
    p.relic('The Lens\'s Heart', (cx + 2400.0, cy, T2 + 115), ',aug_hp8,', lore.MESSAGES['heart'], ',sunderer,', heal=True, mesh='SM_AN_Seedstone', scale=2.0)


def ossuary(p):
    ox, oy = cm(*plan.OSSUARY)
    floor = p.g.at(ox, oy)
    p.mesh('Ossuary Hall', 'SM_AN_Hall', (ox, oy, floor - 10), -110.0, 1.0, 'Ossuary', solid=1500)
    # The vault: a cell whose door opens when the three name-steles before it stand again.
    vx, vy, vyaw = ox - 1400.0, oy + 2000.0, -70.0
    vfloor = p.g.at(vx, vy) - 10
    p.mesh('Ossuary Vault', 'SM_AN_House1', (vx, vy, vfloor), vyaw, 1.0, 'Ossuary', solid=550)
    dx, dy = turned(330.0, 0.0, vyaw)
    p.rise('Ossuary Door', 'SM_AN_VaultDoor', (vx + dx, vy + dy, vfloor), ',ar_vault,', -620.0, vyaw, (1.0, .42, .62), 110.0, 'Ossuary')
    p.relic('The Namer\'s Edge', (vx, vy, vfloor + 115), ',aug_katana6,', lore.MESSAGES['edge'], ',ar_vault,', mesh='SM_CN_LightCache', scale=.8)
    for k in range(3):
        sx, sy = turned(900.0 + 0.0, (k - 1) * 500.0, vyaw)
        x, y = vx + sx, vy + sy
        p.weave('Name Stele %d' % (k + 1), 'SM_AN_Obelisk', (x, y, p.g.at(x, y) - 5), vyaw, give=',ar_name%d,' % (k + 1), need=',reweave,',
                mark=(0.0, 0.0, 260.0), range_m=30.0, drift=180.0, stand=stand_at(p, x + turned(600.0, 0.0, vyaw)[0], y + turned(600.0, 0.0, vyaw)[1]),
                folder='Ossuary')
    p.require('Ossuary Vault', (vx, vy, vfloor + 600), (',ar_name1,', ',ar_name2,', ',ar_name3,'), ',ar_vault,', lore.MESSAGES['vault'])
    p.site('Ossuary Vault', vx, vy, 0, ',aug_katana6,')
    # The Ossuary's old circler: the Leviathan (a Siegeframe of the Ward stands in until its mesh is imported).
    wild = asset(MESHES + '/SM_AE_Leviathan', True) is not None
    p.enemy(13 if wild else 6, 'Leviathan' if wild else 'Siegeframe', ox + 1800.0, oy - 2200.0, 561)
    p.encounter('Ossuary Circler', ox, oy, 561, ',ar_siege,', 'The Leviathan scatters into the air, and the Ossuary is quiet.' if wild
                else 'The Siegeframe is still.')
    tx, ty = turned(0.0, 0.0, 0.0)
    p.relic('Record Tablet 1', (ox + 300.0, oy - 200.0, floor + 60.0 + 115), ',tab1,', lore.MESSAGES['tablet'], mesh='SM_AN_Tablet', scale=1.5)


def sealed(p):
    """Vaults for abilities learned elsewhere: seen now, remembered, opened later."""
    for n, ((x, y), ability) in enumerate(((plan.SEALED_TRACE, ',trace,'), (plan.SEALED_DISSONANCE, ',dissonance,')), 1):
        px, py = cm(x, y)
        yaw = math.degrees(math.atan2(-py, -px))
        door = p.spawn('BP_AbilitySocket', 'Sealed Vault %d' % n, (px, py, p.g.at(px, py) - 10), None, 'Sealed', Ability=ability, Give=',ar_seal%d,' % n,
                       Radius=900.0, Hold=0.0, Solid=True, Message='The vault\'s seal opens.')
        door.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = p.reskin(door, 'SM_AN_VaultDoor')
        if part:
            part.set_collision_profile_name('BlockAll')
        back = turned(-380.0, 0.0, yaw)
        p.mesh('Sealed Cell %d' % n, 'SM_AN_House0', (px + back[0], py + back[1], p.g.at(px, py) - 10), yaw, 1.0, 'Sealed', solid=650)
        entry = lore.ARCHE_GATES[0]
        p.scan(entry[0], entry[1], entry[2], (px + turned(300.0, 0.0, yaw)[0], py + turned(300.0, 0.0, yaw)[1], None), True, 'Sealed')
        p.site('Sealed Vault %d' % n, px, py, 1, ',ar_seal%d,' % n)


# ---------------------------------------------------------------- people

# (mesh, scale): the First Ones stand as their own figures; Maruth's speaking stone is an obelisk.
SPOTS = {}


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
    figure = mesh_asset(mesh) if base.unreal.EditorAssetLibrary.does_asset_exist(MESHES + '/' + mesh) else mesh_asset('SM_AP_Serene1')
    if shape:
        shape.set_static_mesh(figure)
    p.people.append((key, figure.get_name() if figure else 'MISSING'))
    for k in range(len(pages)):
        title = lore.person_key(key, k)
        voice = asset(VOICES + '/' + voice_name(title), True)
        if voice is not None:   # a voice actor without a sound makes PhysisNarrate log an error on every page
            p.spawn('BP_LogVoice', 'Voice ' + title, base.VOICE_SPOT, None, 'Voices', Title=title, Voice=voice)
        else:
            p.unvoiced.append(title)
    return npc


def people(p):
    p.people, p.unvoiced = [], []
    for row in lore.PEOPLE:
        person(p, row)


# ---------------------------------------------------------------- passes

ATTACHED = ("Ilun's Chime", 'A Record Tablet', 'A Seedstone', "The Lens's Heart", "The Namer's Edge", 'Geode Cache')


def scans(p):
    for category, title, body, (x, y, z), important in lore.ARCHE_SCANS:
        if title in ATTACHED:
            continue
        p.scan(category, title, body, (x * M, y * M, z), important)
    # Enemy rows have no free marker; their tags ride on the machines.


def voices(p):
    for category, title, body in lore.arche_entries() + [('Story',) + tuple(lore.ARRIVAL_LINE)]:
        voice = asset(VOICES + '/' + voice_name(title), True)
        if voice is None:
            p.unvoiced.append(title)
            continue
        p.spawn('BP_LogVoice', 'Voice ' + title, base.VOICE_SPOT, None, 'Voices', Title=title, Voice=voice, Image=asset('/Game/UI/Log/' + image_name(title), True))


def tutorials(p):
    for index, (message, (x, y), scale) in enumerate(lore.ARCHE_TUTORIALS):
        p.spawn('BP_TutorialTrigger', 'Tutorial %02d' % (index + 1), p.at(x * M, y * M, 160), scale, 'Tutorial', Message=message)


def sights(p):
    """Every weave's mark must be in plain sight (traced against the meshes, as PhysisWeaveFind does) and in range
    from where she is expected to stand. Returns (checked, the hidden ones)."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    hidden = []
    for label, start, actor in p.sights:
        mark = component(actor, 'Mark')
        seed = mark.get_world_location() if hasattr(mark, 'get_world_location') else actor.get_actor_location()
        head = unreal.Vector(start[0], start[1], start[2] + 60.0)
        far = (seed - head).length()
        if far > (actor.get_editor_property('Range') or 4500.0):
            hidden.append('%s: its mark is %.0f m away, its range %.0f m' % (label, far / M, actor.get_editor_property('Range') / M))
            continue
        hit = unreal.SystemLibrary.line_trace_single(world, head, seed, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [actor], unreal.DrawDebugTrace.NONE, True)
        data = hit.to_tuple() if hit is not None else None
        if data and data[0]:
            hidden.append('%s: mark hidden by %s at %.0f m of %.0f' % (label, data[9].get_actor_label() if data[9] else '?', data[3] / M, far / M))
    return len(p.sights), hidden


def sound_scape(p):
    """The wind everywhere, the Cisterns' water, the Lens's hum (which stops with it: tag ArcheScar). Placed only
    for the beds arche:audio has imported."""
    placed = []

    def ambient(label, sound, place_, radius, volume, tags=()):
        wave = asset(ARCHE + '/Audio/' + sound, True)
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
        placed.append(label)
    ambient('Wind', 'S_Amb_Arche', (0, 0, 4000), 0, .55)
    ambient('Cisterns', 'S_Amb_Cistern', (plan.CISTERNS[0] * M, plan.CISTERNS[1] * M, 300), 15000, .75)
    ambient('Lens', 'S_Amb_Lens', (plan.LENS[0] * M, plan.LENS[1] * M, T2 + 2400), 16000, .8, ('ArcheScar',))
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
    landing(p)
    processional(p)
    hearthold(p)
    first_arch(p)
    chasm(p)
    concourse(p)
    stairs(p)
    cisterns(p)
    middle(p)
    garden(p)
    galleries(p)
    court(p)
    ossuary(p)
    sealed(p)
    life(p)
    p.require('Record Tablets', p.at(*cm(*plan.HEARTHOLD), lift=600), (',tab1,', ',tab2,', ',tab3,'), ',tablets,', lore.MESSAGES['tablets'])
    people(p)
    scans(p)
    voices(p)
    tutorials(p)
    rays = base.divinity_rays(p)
    sounds = sound_scape(p)
    arrival_off()
    raised = p.fit()
    hops, blocked = base.routes(p)
    seen, hidden = sights(p)
    if save:
        base.save_level(LEVEL)
    return {'level': LEVEL, 'removed': removed, 'placed': p.count, 'enemies': p.enemies, 'rays': rays, 'sounds': sounds, 'people': p.people, 'unset': p.unset,
            'unvoiced': len(p.unvoiced), 'hops': hops, 'raised': raised, 'blocked': blocked, 'weaves': seen, 'hidden': hidden, 'missing_assets': sorted(base.MISSING)[:60],
            'missing_count': len(base.MISSING), 'climb': getattr(p, 'climb', None), 'unrigged': sorted(set(p.unrigged)), 'uncut': sorted(set(p.uncut)), 'life': getattr(p, 'life', None), 'marks': {name: [round(v) for v in spot] for name, spot in p.marks.items()}}


# ---------------------------------------------------------------- the Center's temple current

def portal():
    """The current to Arche in the Center's sanctum, shown once the Warden has fallen: a targeted spawn into
    L_CenterOfTheUniverse that replaces only its own earlier actors (labels 'Arche Current...')."""
    base.open_level(CENTER_LEVEL)
    dirty = [pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them before arche:portal' % ', '.join(dirty))
    actors = sub()
    removed = 0
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith('Arche Current'):
            actors.destroy_actor(actor)
            removed += 1
    current = actors.spawn_actor_from_class(cls('BP_ArcheCurrent'), unreal.Vector(*PORTAL))
    current.set_actor_label('Arche Current')
    current.set_folder_path('Center/Arche')
    props(current, Need=',warden,', Dest=1, Radius=180.0)
    back = actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*RETURN))
    back.set_actor_label('Arche Current Return')
    back.set_folder_path('Center/Arche')
    back.set_editor_property('tags', ['ArcheReturn'])
    arrival_off()
    base.save_level(CENTER_LEVEL)
    return {'level': CENTER_LEVEL, 'current': list(PORTAL), 'return': list(RETURN), 'removed': removed}
