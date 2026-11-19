"""Gameplay for the Center of the Universe: Still Points, puzzles, enemies by level, the temple,
and the awakening cinematic. Run through `outfit_operation center:scenario` and `center:cinema`.

Progress tokens (BP_Physis Flags):
  ,center,   arrived              ,lamp1, ,lamp2, ,marsh,   lantern puzzle (marsh steps rise)
  ,stone1, ,stone2, ,stone3,      Stillstones               ,concourse,  plaza cleared (optional)
  ,choir,    Hollow cleared       ,settle,  Settle learned  ,prisms,  prism puzzle (optional)
  ,temple,   temple door open     ,sanctum, Wardens down    ,mend,   Heartbloom taken (Mend)
  ,cacheN,   Echo Caches          ,woundN,  Divinity wounds closed by Settle
  ,bell0-2, ,bells,  Bell Ruins     ,causeway,  Sunken Causeway     ,mono1-3, ,monoliths,  Four Monoliths
  ,rootstair,  Root Stair         (cache8-15 their caches, cache16-19 the far Echo Caches)
Everything but the three Stillstones, the shrine and the Heartbloom is optional: the world is open.

The scenario sets instance-editable variables that Tools/blueprint_logic/center_overrides.py makes:
- BP_Checkpoint Until, made by part saves;
- BP_Switch Reach, made by part conclave;
- BP_Switch NeedB, DeniedB, NeedC and DeniedC, made by part switches (the Heartbloom pedestal's extra requirements);
- BP_Encounter Goal and Radius, made by part encounters;
- BP_TrainingDrone EnemyKind, ArenaAt, ArenaIn and ArenaOut, made by part drones (RoomMin and RoomMax are older).
It also needs BP_TrainingDrone's Ward component (center:drone_ward) and the enemies' materials (center:enemy_looks).
Run those parts (center_music.py runs every part) and ops before center:scenario. place() refuses before it changes
anything while one is missing.
"""
import math
import random

import unreal

import physis_gameplay_tools as game
from physis_aaa_tools import set_props, wrap_text
from physis_center_lore import CENTER_SCANS, CENTER_TUTORIALS, ENEMY_ENTRIES, FAUNA_SCANS, GRASS_SCAN, KIND_ENTRIES, PUZZLE_SCANS, center_entries
from physis_lore import voice_name, image_name

CENTER = '/Game/Center'
MESHES = CENTER + '/Meshes'
MATS = CENTER + '/Materials'
AUDIO = CENTER + '/Audio'
TEMPLE = (76000, 0)
TEMPLE_FLOOR = 3400
# The temple stands on its base: physis_center_tools 'Temple Base' at TEMPLE_FLOOR - 10, square tiers of half-width
# 38, 33 and 28 m with tops 2, 4 and 6 m up (Tools/build_physis_center.py temple_base). On the top tier
# (TEMPLE_FLOOR + 590) the sanctum (temple_sanctum, at TEMPLE_FLOOR + 600) adds two raised surfaces at
# SANCTUM_FLOOR: its ring floor (r 12-20 m) and the causeway from the gate. It also adds an inner causeway at
# TEMPLE_FLOOR + 600. height.bin holds only the terrain, 6 m lower, so things placed by terrain height ended up inside
# the base. Play test, 2026-11-07: the Sanctum Still Point, both Temple Capsules and the Heartbloom's scan tag could
# never be reached. Place.floor() stands them on these surfaces (the pedestal's drum is not modelled).
# TEMPLE_TIERS is (half-width cm, top z cm), innermost first.
TEMPLE_TIERS = ((2800, TEMPLE_FLOOR + 590), (3300, TEMPLE_FLOOR + 390), (3800, TEMPLE_FLOOR + 190))
SANCTUM_FLOOR = TEMPLE_FLOOR + 630
# The Heartbloom pedestal's Done text is agreed word for word with the Conclave session, whose conclave:portal op sets
# the same four lines on the placed pedestal. Keep the two identical. place() sets it as is, because wrap_text counts
# across '~' and would break the four lines into eight.
HEARTBLOOM_DONE = ("The Heartbloom opens in Physis's hands, and she understands how a wound is closed.~Mend learned: Z / |DL|.  "
                   "Heals 6 health for 25 Divinity.~A Divinity current has opened in the sanctum.~Step into it to follow it to "
                   "the Conclave, or explore the Center first.")
WAKE = (-68400, 0)
# Still Points away from the glade (place() puts the checkpoints at or next to these).
STILL_POINTS = ((-30000, -14000), (-9000, -4000), (-12860, 39000), (26000, 26000), (26000, -30000), (TEMPLE[0] - 9000, TEMPLE[1]))

# Enemy kinds (author, 2026-11-08: "more enemy variety"; EnemyKind on BP_TrainingDrone, whose rules are in
# center_overrides.py drones). Kind: label word, mesh, scale, health, materials by slot name (Place.dress), ward plate.
# Their scan entries are physis_center_lore KIND_ENTRIES. They stand on the roads and in the wild packs, never in a
# fight's room, where every enemy is gold (GOLD) and a kind's colours would not show.
# Ward plates go on the drone's Ward component (Place.ward): mesh, material, then location, rotation (roll, pitch,
# yaw) and scale relative to the drone, in the body's own units (the drone's scale applies on top). An engine cylinder
# is 100 cm across and 100 cm along its axis, so pitch 90 turns its axis to the drone's forward (+X) and it reads as a
# disc on the front. The Aegis Shard's plate stands just past its foremost shard (the Shardling reaches 77 cm forward of
# its origin, 97 cm down, 117 cm up) and covers most of its body. The Onyx Ward's face plate fills the Warden ring's
# inner hoop (radius 1.6 m) just in front of its core, hiding the violet core from the front only. Both stay within
# the body's height, so DroneHover still holds the body's own lowest point 20 cm off the ground.
AEGIS_PLATE = ('/Engine/BasicShapes/Cylinder', 'MI_Enemy_FrostWard', (88, 0, 10), (0, 90, 0), (1.5, 1.5, .08))
ONYX_PLATE = ('/Engine/BasicShapes/Cylinder', 'MI_Enemy_OnyxCrystal', (60, 0, 0), (0, 90, 0), (3.2, 3.2, .1))
KINDS = {
    1: ('Bastion', 'SM_CE_Shardling', 2.0, 20, {'M_Crystal': 'MI_Enemy_SlateCrystal', 'M_Glow': 'MI_Enemy_SlateGlow'}, None),
    2: ('Aegis', 'SM_CE_Shardling', 1.2, 10, {'M_Crystal': 'MI_Enemy_FrostCrystal'}, AEGIS_PLATE),
    3: ('Ember', 'SM_CE_Shardling', .7, 4, {'M_Crystal': 'MI_Enemy_EmberCrystal', 'M_Glow': 'MI_Enemy_EmberGlow'}, None),
    4: ('Onyx', 'SM_CE_Warden', .6, 14, {'M_Crystal': 'MI_Enemy_OnyxCrystal', 'M_Glow': 'MI_Enemy_OnyxGlow'}, ONYX_PLATE),
}
# Required enemies are gold (author, 2026-11-08): every enemy in a fight's room, that is every non-Static drone with a
# RoomId, since each Center room has its BP_Encounter. Static crystal locks and prisms never are.
GOLD = {'M_Crystal': 'MI_Enemy_GoldCrystal', 'M_Glow': 'MI_Enemy_GoldGlow'}
# Every material place() puts on enemies (physis_center_tools ENEMY_LOOKS makes them): ready() checks them first.
ENEMY_MATERIALS = sorted(set(GOLD.values()) | {mi for kind in KINDS.values() for mi in kind[4].values()} | {kind[5][1] for kind in KINDS.values() if kind[5]})
WARD = 'Ward'  # physis_center_tools WARD
# The sanctum's guardians (temple review, 2026-11-08): on the ring floor's diagonals 13 m out, Wardens on the far side
# (+-45 degrees from north), Guards on the gate's (+-135). From any spot at the pedestal all four are within the
# drones' 18 m, so none waits by the columns while the fight stalls. Level, label, bearing in degrees.
SANCTUM_GUARDIANS = ((4, 'Temple Warden 0', 45), (4, 'Temple Warden 1', -45), (3, 'Temple Guard 0', 135), (3, 'Temple Guard 1', -135))
# Stillstone One's isle, chosen by place() and read by divinity_rays() and the 'Stillstone' scan tag.
ISLE = []


def stone_ring(p, label, cx, cy, radius, toward, need, folder):
    """First One standing stones round an isle top (the platforms' tops are at z 60). The water jump reaches about 1.9 m
    over the water (2026-11-08), which let her land on the Stillstone Isle and the Causeway Islet and skip their
    puzzles; the author chose to keep the puzzles. A stone is a SM_CA_Monolith at (.3, .3, .14): 93 cm square, 3.3 m
    tall, tapering to 75 cm, set 123 cm apart, so no gap reaches her 68 cm capsule anywhere. The two stones facing
    `toward` (where the stepping stones or the causeway arrive) are a BP_Rise gate that sinks into the isle, like the
    Temple Door, once `need` is held."""
    n = max(8, int(round(2 * math.pi * radius / 123.0)))
    gate = math.atan2(toward[1] - cy, toward[0] - cx)
    off = lambda a: abs((a - gate + math.pi) % (2 * math.pi) - math.pi)
    angles = [k / n * 2 * math.pi for k in range(n)]
    gates = sorted(range(n), key=lambda k: off(angles[k]))[:2]
    for k, a in enumerate(angles):
        x, y, yaw = cx + math.cos(a) * radius, cy + math.sin(a) * radius, math.degrees(a)
        if k in gates:
            stone = p.rise('%s Gate %d' % (label, k), 'SM_CA_Monolith', (x, y, 60), need, -400, (0, 0, yaw), (.3, .3, .14), 120)
            stone.set_actor_location(unreal.Vector(x, y, 60), False, False)  # closed until need: it sinks 4 m from here
        else:
            p.mesh('%s Stone %d' % (label, k), 'SM_CA_Monolith', (x, y, 60), (0, 0, yaw), (.3, .3, .14), folder)


def compass(dx, dy):
    """The compass word for a direction in Unreal cm (x north, y east), for texts that point the way."""
    words = ('north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west')
    return words[int(round(math.degrees(math.atan2(dy, dx)) / 45.0)) % 8]


def cls(name):
    return unreal.load_asset(game.BLUEPRINTS + '/' + name).generated_class()


def sub():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Place:
    def __init__(self, ground):
        self.g = ground
        self.count = 0

    # -- primitives ---------------------------------------------------------------
    def spawn(self, name, label, place, scale=None, folder='Scenario', **values):
        actor = sub().spawn_actor_from_class(cls(name), unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path('Center/' + folder)
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))
        if values:
            set_props(actor, **values)
        self.count += 1
        return actor

    def mesh(self, label, mesh, place, rot=(0, 0, 0), scale=1.0, folder='Scenario', collide=True):
        actor = sub().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place), unreal.Rotator(*rot))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path('Center/' + folder)
        part = actor.static_mesh_component
        part.set_static_mesh(unreal.load_asset(MESHES + '/' + mesh))
        part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
        scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        actor.set_actor_scale3d(unreal.Vector(*scale))
        return actor

    def light(self, label, place, colour, intensity, radius):
        actor = sub().spawn_actor_from_class(unreal.PointLight, unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path('Center/Scenario')
        comp = actor.get_component_by_class(unreal.PointLightComponent)
        comp.set_light_color(unreal.LinearColor(*colour, 1))
        comp.set_editor_property('intensity', intensity)
        comp.set_editor_property('attenuation_radius', radius)
        comp.set_cast_shadows(False)
        return actor

    def floor(self, x, y):
        """The surface at (x, y): the terrain (water level at least), or the temple's floor where it stands on its base."""
        ground = max(self.g.at(x, y), 0.0)
        dx, dy = x - TEMPLE[0], y - TEMPLE[1]
        reach = max(abs(dx), abs(dy))
        if reach <= TEMPLE_TIERS[0][0]:
            # temple_sanctum: the ring floor, the causeway from the gate (x -21 to -5 m, |y| up to 2.2 m), then the
            # lower inner causeway (x -10 to 0 m).
            if 1200 <= math.hypot(dx, dy) <= 2000 or (-2100 <= dx <= -500 and abs(dy) <= 220):
                return max(ground, SANCTUM_FLOOR)
            if -1000 <= dx <= 0 and abs(dy) <= 220:
                return max(ground, TEMPLE_FLOOR + 600)
        for half, top in TEMPLE_TIERS:
            if reach <= half:
                return max(ground, top)
        return ground

    def at(self, x, y, lift=0.0):
        return (x, y, self.floor(x, y) + lift)

    def dry(self, x, y, need=40.0, reach=4000):
        """The nearest point at least `need` cm above the water, searching outward in rings."""
        if self.g.at(x, y) > need:
            return x, y
        for r in range(150, reach, 150):
            for k in range(16):
                a = k / 16 * 2 * math.pi
                px, py = x + math.cos(a) * r, y + math.sin(a) * r
                if self.g.at(px, py) > need:
                    return px, py
        return x, y

    def site(self, x, y, span=1200, reach=3000, need=80.0):
        """A dry, fairly level spot near (x, y), at least 25 m from any road: the candidate with the least
        height change across `span`, with a small preference for staying close to (x, y)."""
        best, score = None, 1e18
        for r in range(0, reach + 1, 500):
            ring_n = max(1, (r // 500) * 6)
            for k in range(ring_n):
                a = k / ring_n * 2 * math.pi
                px, py = x + math.cos(a) * r, y + math.sin(a) * r
                h = self.g.at(px, py)
                if h < need or road_gap(px, py) < 2500:
                    continue
                rim = [self.g.at(px + math.cos(b) * span, py + math.sin(b) * span) for b in (0, 1.57, 3.14, 4.71)]
                cost = max(abs(v - h) for v in rim) + r * .02
                if cost < score:
                    best, score = (px, py), cost
        return best or self.dry(x, y, need)

    def reskin(self, actor, mesh, material=None):
        # A drone's Ward component (center:drone_ward) is its kind's plate (Place.ward), not a stray part to hide, and
        # never the body that takes the mesh.
        parts = [part for part in actor.get_components_by_class(unreal.StaticMeshComponent) if part.get_name() != WARD]
        for index, part in enumerate(parts):
            if index == 0:
                part.set_static_mesh(unreal.load_asset(MESHES + '/' + mesh))
                if material:
                    part.set_material(0, material)
            else:
                part.set_visibility(False)
                part.set_collision_profile_name('NoCollision')
        return parts[0] if parts else None

    def depth(self, mesh, scale):
        """How far below its origin a Center mesh reaches at `scale` (cm), from the mesh's own bounds."""
        return -unreal.load_asset(MESHES + '/' + mesh).get_bounding_box().min.z * scale

    def top(self, mesh, scale=1.0):
        """How far above its origin a Center mesh reaches at `scale` (cm): scan tags go over it, not inside it."""
        return unreal.load_asset(MESHES + '/' + mesh).get_bounding_box().max.z * scale

    def dress(self, actor, mesh, looks=None):
        """reskin, then the slots that `looks` names ({slot name: instance in /Game/Center/Materials}) by the mesh's slot
        names, since FBX slot order differs between meshes. Every other slot keeps what it has. So does every slot
        without looks: slot 0 keeps the Blueprint template's MI_Drone (physis_aaa_tools drone), as every kind 0 enemy
        outside a fight has since before the kinds existed."""
        part = self.reskin(actor, mesh)
        if part and looks:
            asset = unreal.load_asset(MESHES + '/' + mesh)
            for index, slot in enumerate(asset.get_editor_property('static_materials')):
                look = looks.get(str(slot.get_editor_property('material_slot_name')).split('.')[0])
                if look:
                    part.set_material(index, unreal.load_asset(MATS + '/' + look))
        return part

    def ward(self, actor, mesh, material, at, rot, size):
        """A kind's plate on the drone's Ward component (AEGIS_PLATE, ONYX_PLATE). DroneStuckCheck hides the Aegis
        Shard's while its ward is broken; the Onyx Ward's always shows."""
        part = next((c for c in actor.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == WARD), None)
        if part is None:
            raise RuntimeError('%s has no Ward component: run center:drone_ward' % actor.get_actor_label())
        part.set_static_mesh(unreal.load_asset(mesh))
        part.set_material(0, unreal.load_asset(MATS + '/' + material))
        part.set_editor_property('relative_location', unreal.Vector(*at))
        part.set_editor_property('relative_rotation', unreal.Rotator(*rot))
        part.set_editor_property('relative_scale3d', unreal.Vector(*size))
        part.set_collision_profile_name('NoCollision')
        part.set_visibility(True)
        return part

    # -- gameplay pieces -------------------------------------------------------------
    def check(self, label, x, y, objective, radius=700, until=',mend,'):
        """A Still Point. Once Flags hold until, its first visit no longer sets its objective (center_overrides
        still_points). Every Center objective is spent once she has Mend, and the quest is then the current's, or
        the Conclave's after a trip home."""
        return self.spawn('BP_Checkpoint', 'Still Point ' + label, self.at(x, y, 110), Radius=radius, Objective=objective, Until=until)

    def scan(self, category, title, text, place, important):
        x, y, z = place
        z = (self.floor(x, y) + 150) if z is None else z
        tag = self.spawn('BP_ScanTarget', 'Story ' + title, (x, y, z), folder='Scans', ScanText=text, ScanCategory=category, ScanTitle=title, ScanImportant=important)
        game.hide_scan(tag)
        return tag

    def switch(self, label, place, yaw=0, mesh=None, solid=False, **values):
        """BP_Switch: Interact within 260 cm of its origin. Its shape has no collision; `solid` gives a
        reskinned stone or crystal collision (only for shapes narrow enough to stand within reach)."""
        actor = self.spawn('BP_Switch', label, place, **values)
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        if mesh:
            part = self.reskin(actor, mesh)
            if solid and part:
                part.set_collision_profile_name('BlockAll')
        return actor

    def relic(self, label, place, token, message, need='', divinity=0.0, heal=False, mesh='SM_CA_Stillstone', scale=1.6):
        actor = self.spawn('BP_Relic', label, place, Token=token, Need=need, Message=message, Divinity=divinity, Heal=heal)
        self.reskin(actor, mesh)
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        return actor

    def barrier(self, label, x, y, yaw, give=''):
        actor = self.spawn('BP_SettleBarrier', label, self.at(x, y, -40), Give=give)
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        return actor

    def cage(self, label, x, y, token, message, divinity=60.0, ring=3, radius=520, bearing=0.0):
        """An Echo Cache inside a ring of thorns: only Settle opens it. Over water the cache hangs 40 cm above the
        surface, not 120: a swimmer's centre is about 48 cm under it and BP_Relic gives the cache within 170 cm, so at
        120 she had to be within 29 cm of it sideways (lantern review, 2026-11-08). A 'Thorn Barrier' scan tag stands
        outside the ring, 10 m out at `bearing` (radians from north; the thorns' outer faces are 7.1 m out), so the
        thorns can be scanned before Settle."""
        for k in range(ring):
            a = k / ring * 2 * math.pi
            self.barrier('%s Thorn %d' % (label, k), x + math.cos(a) * radius, y + math.sin(a) * radius, math.degrees(a))
        self.relic(label, self.at(x, y, 40 if self.g.at(x, y) < 0 else 120), token, message, divinity=divinity, mesh='SM_CT_Crystal0', scale=.35)
        thorn = next(row for row in CENTER_SCANS if row[1] == 'Thorn Barrier')
        self.scan(thorn[0], thorn[1], thorn[2], self.at(x + math.cos(bearing) * (radius + 480), y + math.sin(bearing) * (radius + 480), 250), thorn[4])

    def rise(self, label, mesh, place, need, lift, rot=(0, 0, 0), scale=1.0, speed=180.0):
        actor = self.spawn('BP_Rise', label, (place[0], place[1], place[2] - lift), Need=need, Lift=lift, Speed=speed)
        actor.set_actor_rotation(unreal.Rotator(*rot), False)
        self.reskin(actor, mesh)
        scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        actor.set_actor_scale3d(unreal.Vector(*scale))
        return actor

    def enemy(self, level, label, x, y, room=0, static=False, scale=None, settle=False, **values):
        """A level 1-5 enemy (ENEMY_ENTRIES), EnemyKind 0. In a fight's room it is gold, unless it is Static. scale
        overrides the level's size. settle puts its lowest point 20 cm over the floor at once instead of the level's
        hover height: the temple's arena guardians are never let below where they were placed (DroneHover), so that
        must be their floor. values are more BP_TrainingDrone settings (RoomMin, ArenaOut...)."""
        mesh, health, size, hover, entry = ENEMY_ENTRIES[level]
        size = size if scale is None else scale
        place = (x, y, self.floor(x, y) + (self.depth(mesh, size) + 20.0 if settle else hover))
        actor = self.spawn('BP_TrainingDrone', 'Enemy L%d %s' % (level, label), place, (size, size, size), folder='Enemies', RoomId=room, Boss=False, Health=health, **values)
        actor.set_editor_property('Static', static)
        self.dress(actor, mesh, GOLD if room and not static else None)
        self.tag_enemy(actor, label, place, entry)
        return actor

    def foe(self, kind, level, label, x, y, room=0):
        """An enemy of kind 1-4 (KINDS), or of `level` for kind 0 (enemy()). A kind's health and look are its own; level
        only names it ('Enemy L<level> <word> <label>', so clear() and the tools still find it). Its scan tag carries
        its kind's entry. Kinds never stand in a fight's room, where gold would hide what they are."""
        if not kind:
            return self.enemy(level, label, x, y, room)
        if room:
            raise ValueError('enemy kind %d placed in room %d: kinds stay out of the fights (they would not be gold)' % (kind, room))
        word, mesh, scale, health, looks, plate = KINDS[kind]
        place = (x, y, self.floor(x, y) + self.depth(mesh, scale) + 20.0)
        actor = self.spawn('BP_TrainingDrone', 'Enemy L%d %s %s' % (level, word, label), place, (scale, scale, scale), folder='Enemies',
                           RoomId=0, Boss=False, Health=health, EnemyKind=kind)
        actor.set_editor_property('Static', False)
        self.dress(actor, mesh, looks)
        if plate:
            self.ward(actor, *plate)
        self.tag_enemy(actor, label, place, KIND_ENTRIES[kind])
        return actor

    def tag_enemy(self, actor, label, place, entry):
        """The enemy's scan tag, 70 cm over its origin and riding on it (TakeHit destroys it with the enemy)."""
        tag = sub().spawn_actor_from_class(cls('BP_ScanTarget'), unreal.Vector(place[0], place[1], place[2] + 70))
        tag.set_actor_label('Scene Tag ' + label)
        tag.set_folder_path('Center/Enemies')
        set_props(tag, ScanCategory=entry[0], ScanTitle=entry[1], ScanText=entry[2])
        tag.set_editor_property('ScanImportant', True)
        game.hide_scan(tag)
        tag.attach_to_actor(actor, 'None', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
        return tag

    def pickup(self, kind, label, x, y, lift=120):
        """A loose BP_Pickup. The Center places none since 2026-11-15 (see grass)."""
        actor = self.spawn('BP_Pickup', label, self.at(x, y, lift), folder='Pickups')
        actor.set_editor_property('Kind', kind)
        return actor

    def grass(self, label, x, y, tufts=6, spread=230.0):
        """A patch of BP_CutGrass: tall gold-tipped grass her blade cuts. A cut tuft may drop a pickup and grows back,
        so the Center has no loose pickups lying about (author, 2026-11-15: "remove any random pickups found in the
        Center and put in a special kind of grass that can be cut and drops random pickups"). BP_CutGrass is shared
        with the Conclave, whose session made it on 2026-11-15: BP_Physis PhysisStrikeNow calls GrassCut on tufts within
        2.6 m ahead of her; a cut tuft flattens and after Regrow seconds returns to the Shape scale it began with;
        Chance and Regrow are left at their defaults here (half the tufts drop, always when she is low; 120 s).
        The Center's tufts wear SM_CT_CutGrass (build_physis_center.cut_grass) with Shape at 1, whatever the
        Blueprint's own default is, so the actor's scale alone sizes them. Tufts stand on dry ground only; the same
        label always gives the same patch. One GRASS_SCAN tag hangs 1.5 m over the patch, named 'Grass Tag <label>'."""
        rng = random.Random('grass ' + label)
        made = []
        for k in range(tufts):
            a, r = rng.uniform(0, 2 * math.pi), spread * math.sqrt(rng.uniform(.03, 1))
            tx, ty = x + math.cos(a) * r, y + math.sin(a) * r
            if self.floor(tx, ty) < 15:
                continue
            size = rng.uniform(.85, 1.25)
            actor = self.spawn('BP_CutGrass', '%s Grass %d' % (label, k), self.at(tx, ty), (size, size, size * rng.uniform(.9, 1.15)), 'Grass')
            actor.set_actor_rotation(unreal.Rotator(0, 0, rng.uniform(0, 360)), False)
            # The Blueprint's own Shape is the Conclave's wheat in its gold material: here it wears the Center's tuft
            # in that mesh's materials, at a scale of its own.
            shape = actor.get_component_by_class(unreal.StaticMeshComponent)
            tuft = unreal.load_asset(MESHES + '/SM_CT_CutGrass')
            shape.set_static_mesh(tuft)
            for index in range(len(tuft.get_editor_property('static_materials'))):
                shape.set_material(index, tuft.get_material(index))
            shape.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
            shape.set_collision_profile_name('NoCollision')
            shape.set_editor_property('cast_shadow', False)
            made.append(actor)
        if made:
            category, title, text = GRASS_SCAN
            tag = self.spawn('BP_ScanTarget', 'Grass Tag ' + label, self.at(x, y, 150), folder='Scans', ScanText=text, ScanCategory=category,
                             ScanTitle=title, ScanImportant=False)
            game.hide_scan(tag)
        return made

    def encounter(self, label, x, y, room, give, message, goal='', fight='', radius=0.0):
        """A fight: done when no drone has its room. fight, the Goal, names its golden enemies: while some remain and
        she is within radius of this actor (3D), the objective reads '<fight>: N left' (center_overrides encounters).
        One Goal per place: overlapping fights would take turns on the objective line."""
        return self.spawn('BP_Encounter', label, self.at(x, y, 400), Room=room, Learn=0, Give=give, Message=message, NextGoal=goal,
                          Goal=fight, Radius=float(radius))

    def hint(self, label, x, y, text, scale):
        """A tutorial strip (BP_TutorialTrigger, a 600 x 600 x 400 box at scale 1): its text shows whenever she
        enters the box."""
        actor = sub().spawn_actor_from_class(cls('BP_TutorialTrigger'), unreal.Vector(*self.at(x, y, 160)))
        actor.set_actor_label('Scene Tutorial ' + label)
        actor.set_actor_scale3d(unreal.Vector(*scale))
        actor.set_editor_property('Message', wrap_text(text))
        actor.set_folder_path('Center/Tutorial')
        return actor

    def require(self, label, place, needs, give, message):
        values = {'Need%s' % 'ABCD'[i]: token for i, token in enumerate(needs)}
        return self.spawn('BP_Requirement', label, place, Give=give, Message=message, **values)

    def wound(self, label, x, y, size, token, **values):
        return self.spawn('BP_Hazard', 'Wound ' + label, self.at(x, y, 3), (size / 100, size / 100, 1), Deep=False, Off=token, **values)


def road_lines():
    import json as _json
    return _json.loads((game.pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / 'Art/Meshes/Center/height.json').read_text())['paths']


def road_gap(x, y):
    """Distance in cm from (x, y) to the nearest road."""
    best = 1e18
    for line in road_lines_cache():
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            ax, ay, bx, by = ax * 100, ay * 100, bx * 100, by * 100
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(dx * dx + dy * dy, 1.0)))
            best = min(best, math.hypot(x - (ax + dx * t), y - (ay + dy * t)))
    return best


_ROADS = []


def road_lines_cache():
    if not _ROADS:
        _ROADS.extend(road_lines())
    return _ROADS


def clear():
    for actor in sub().get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith('Scene ') or isinstance(actor, unreal.TextRenderActor):
            sub().destroy_actor(actor)


def ready():
    """Refuses unless everything place() sets exists (see the docstring), so it fails before clear(): a failure after
    it would leave the open Center emptied and unsaved."""
    for name, variable, part in (('BP_Checkpoint', 'Until', 'saves'), ('BP_Switch', 'Reach', 'conclave'),
                                 ('BP_Switch', 'NeedB', 'switches'), ('BP_Switch', 'DeniedB', 'switches'), ('BP_Switch', 'NeedC', 'switches'),
                                 ('BP_Switch', 'DeniedC', 'switches'), ('BP_Encounter', 'Goal', 'encounters'),
                                 ('BP_Encounter', 'Radius', 'encounters'), ('BP_TrainingDrone', 'EnemyKind', 'drones'),
                                 ('BP_TrainingDrone', 'ArenaAt', 'drones'), ('BP_TrainingDrone', 'ArenaIn', 'drones'),
                                 ('BP_TrainingDrone', 'ArenaOut', 'drones'), ('BP_TrainingDrone', 'RoomMin', 'drones'),
                                 ('BP_TrainingDrone', 'RoomMax', 'drones')):
        try:
            unreal.get_default_object(cls(name)).get_editor_property(variable)
        except Exception:
            raise RuntimeError('center:scenario refused before any change: %s has no %s. Run center_overrides.py %s '
                               '(or center_music.py) and save the Blueprints first.' % (name, variable, part))
    from physis_center_tools import ward_part
    if ward_part(unreal.load_asset(game.BLUEPRINTS + '/BP_TrainingDrone')) is None:
        raise RuntimeError('center:scenario refused before any change: BP_TrainingDrone has no Ward component. Run center:drone_ward first.')
    missing = [look for look in ENEMY_MATERIALS if not unreal.EditorAssetLibrary.does_asset_exist(MATS + '/' + look)]
    if missing:
        raise RuntimeError('center:scenario refused before any change: no %s. Run center:enemy_looks first.' % ', '.join(missing))


def place(ground):
    ready()
    clear()
    p = Place(ground)

    # ---- The Still Glade: where Physis wakes. The glade is the Still Point of the whole map.
    wx, wy = WAKE
    p.check('Glade', wx, wy, 'Explore the Center of the Universe', 900)
    for k, (dx, dy) in enumerate(((900, 700), (1100, -600), (-500, 900))):
        p.grass('Glade Crystal %d' % k, wx + dx, wy + dy)
    p.grass('Glade Capsule', wx + 1300, wy + 100)
    p.cage('Echo Cache Glade', -60000, 9000, ',cache1,', 'Echo Cache absorbed. Divinity +60.')
    p.light('Glade Cache Glow', p.at(-60000, 9000, 300), (.4, .9, 1), 3000, 900)

    # ---- Road patrols: crystal hunters along every road, weakest near the glade, stronger toward the temple.
    # A pair every 85 m of road (the author asked for three times the enemies; with the wilderness packs and
    # the larger fights below the Center holds about three times its first 78).
    paths = road_lines_cache()
    patrol = 0
    pair = 0
    for line in paths:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            length = math.hypot(bx - ax, by - ay)
            for k in range(max(1, int(length / 85))):
                t = (k + .5) / max(1, int(length / 85))
                x, y = (ax + (bx - ax) * t) * 100, (ay + (by - ay) * t) * 100
                if math.hypot(x - wx, y - wy) < 5000:
                    continue
                nx, ny = -(by - ay) / length, (bx - ax) / length
                level = 1 if x < -20000 else (2 if x < 30000 else 3)
                pair += 1
                for side in (-1, 1):
                    ex, ey = x + nx * side * 1400, y + ny * side * 1400
                    # None within 30 m of a Still Point, where Physis returns after a fall, and none within 70 m of the
                    # temple: patrols there stood on its stair, one inside it, chased her up into the sanctum and
                    # looked just like the guardians the fight counts (temple review, 2026-11-08).
                    if any(math.hypot(ex - sx, ey - sy) < 3000 for sx, sy in STILL_POINTS) or math.hypot(ex - TEMPLE[0], ey - TEMPLE[1]) < 7000:
                        continue
                    p.foe(road_kind(pair, x) if side == 1 else 0, level, 'Road Patrol %d' % patrol, ex, ey)
                    patrol += 1
    # The first fight, in sight of the glade on the north-east road.
    for k, (dx, dy) in enumerate(((6500, 1200), (7200, -900), (8200, 400), (6900, 2400), (8600, -1800), (9300, 1300))):
        p.enemy(1, 'Glade Edge %d' % k, wx + dx, wy + dy, 201)
    # The open-country fights (Glade Edge, the Concourse) show no count: the hub's circle would take over the main
    # quest line whenever she passes (Play test, 2026-11-08). Their hunters stay gold, members of a fight.
    p.encounter('Glade Edge Fight', wx + 7300, wy, 201, ',gladefight,', 'The crystal hunters scatter. Scan the creatures of the Center to learn their ways.', '')

    # ---- Lantern Marsh: light the lanterns in the stele's order; stepping stones rise to Stillstone 1.
    mx, my = p.dry(-30000, -14000)
    p.check('Marsh', mx, my, 'Find the Stillstone in Lantern Marsh. The stele at its edge knows the lantern order.')
    sx, sy = p.dry(-28500, -36500, 60)
    p.mesh('Lantern Stele', 'SM_CA_Monolith', p.at(sx, sy, -60), (0, 0, 30), (.18, .18, .12))
    # The isle: in the south-west of the marsh, the spot whose highest ground within 15 m is lowest, so that water too
    # deep to wade rings it (lantern review, 2026-11-08). The single deepest cell, used before, touched a dry bank on
    # its south side, so the stone could be walked to without lighting a lantern.
    best, low = None, 1e9
    for gx in range(-60000, -40000, 1000):
        for gy in range(-70000, -48000, 1000):
            rim = max(ground.at(gx + math.cos(k / 16 * 2 * math.pi) * r, gy + math.sin(k / 16 * 2 * math.pi) * r) for r in range(0, 1501, 300) for k in range(16))
            if rim < low:
                low, best = rim, (gx, gy)
    if low > -100:
        unreal.log_warning('Stillstone Isle: no site ringed by deep water (highest ground within 15 m: %d cm)' % low)
    ix, iy = best
    ISLE[:] = [ix, iy]
    shore = p.dry(ix + 3000, iy + 3000, 50, 9000)
    # The three lanterns stand along the Marsh road, the raised causeway that runs from near the Lantern Stele south-west
    # to the Marsh Arch (physis_center_tools landmarks: SM_CA_LightArch at -36000, -44000, where the road ends), where
    # the stele's words put them (author, 2026-11-09: the Red lantern was nowhere near the other two, and the stele's
    # willows, reed isle and arch were nowhere near any lantern). Walking from the stele toward the arch she meets them
    # in their order: Red, 41 m from the arch, at the causeway's edge (7 m from its centre line) beneath three willows
    # placed for it in the shallows 10-12 m off the road; Blue 3 m from the drowned lamp post (the lit SM_CA_Lamp,
    # scatter index 68, standing in the water 7 m off the road), on the other side, in 19 cm of water; Gold under the
    # arch itself, where the road ends. Their glows are the colours they are named for (Rose and Cyan read as red and
    # blue). Nothing stands on the trail band (the scatter keeps trees 8 m off it; review, 2026-11-09), and the lanterns
    # are solid now, so she can no longer walk through a lantern's stone foot. Sites: height map and scatter.json
    # (scratchpad lanterns/road.py), clear of the Echo Cache's thorns (11 m from the arch) and the arch's legs.
    for k, (wx2, wy2, size, yaw) in enumerate(((-32609, -42406, 1.15, 20), (-32068, -42287, 1.25, 140), (-31856, -41775, 1.05, 260))):
        p.mesh('Red Lantern Willow %d' % k, 'SM_CT_Willow', p.at(wx2, wy2, 0), (0, 0, yaw), size, 'Marsh')
    lanterns = (('Red', (-32453, -41827), ',lamp1,', '', (1, .22, .15)), ('Blue', (-35011, -42333), ',lamp2,', ',lamp1,', (.25, .45, 1)),
                ('Gold', (-36000, -44000), ',marsh,', ',lamp2,', (1, .75, .3)))
    for name, (lx, ly), give, need, colour in lanterns:
        if p.g.at(lx, ly) < -60:
            unreal.log_warning('Lantern %s: its site (%d, %d) is %d cm under water' % (name, lx, ly, -p.g.at(lx, ly)))
        # Denied no longer says the lantern 'stays dark': its glow light shines from the start. The Gold lantern's Done
        # names where the stones rise, now that the isle is chosen by its water.
        # On the bed, not the water's surface (p.at stops at the water line): the Blue lantern stands in 19 cm of water.
        p.switch('Lantern ' + name, (lx, ly, min(p.at(lx, ly, 0)[2], p.g.at(lx, ly))), 0, 'SM_CA_Lantern', True, Give=give, Need=need,
                 Denied='The %s lantern will not answer yet. Another must burn before it. The stele remembers the order.' % name,
                 Done=('The %s lantern burns. Somewhere in the marsh, water stirs.' % name) if give != ',marsh,' else
                 'The Gold lantern burns. Every lantern answers, and stepping stones rise from the deep water to the %s.' % compass(ix - lx, iy - ly))
        p.light('Lantern Glow ' + name, p.at(lx, ly, 330), colour, 2600, 1100)
        # A lit lantern shows it: once its token is held, a crystal flame rises out of its top (the lantern is 4 m tall).
        p.rise('Lantern Flame ' + name, 'SM_CT_Crystal0', p.at(lx, ly, 430), give, 120, (0, 0, 0), .15, 80)
    p.mesh('Stillstone Isle', 'SM_CA_Platform', (ix, iy, 60), (0, 0, 0), (3, 3, 1.4), 'Marsh')
    dx, dy = ix - shore[0], iy - shore[1]
    dist = math.hypot(dx, dy)
    steps = max(2, int(dist / 850))
    for k in range(1, steps):
        t = k / steps
        p.rise('Marsh Step %d' % k, 'SM_CA_Platform', (shore[0] + dx * t, shore[1] + dy * t, 40 + 15 * (k % 2)), ',marsh,', 500, (0, 0, k * 23), (.9, .9, .9), 160 + k * 15)
    stone_ring(p, 'Isle Ring', ix, iy, 730, shore, ',marsh,', 'Marsh')
    p.relic('Stillstone One', (ix, iy, 230), ',stone1,', 'Stillstone recovered: one of three. The temple far to the north will know.')
    p.light('Isle Glow', (ix, iy, 500), (.4, .9, 1), 6000, 2000)
    # From the water nothing said why the stone could not be reached (lantern review, 2026-11-08). The strip shows as
    # she nears the isle, on the water or on the stones.
    # Worded to stay true once the stones have risen: the strip shows on every visit (review, 2026-11-08).
    p.hint('Stillstone Isle', ix, iy, 'Stillstone Isle: a ring of First One stones closes it. Its gate faces the shore to the %s, '
           'where stepping stones rise when the three lanterns burn in the order the Lantern Stele keeps.' % compass(shore[0] - ix, shore[1] - iy), (6, 6, 1.5))
    # Marsh kinds: Ember Skitters among the shards and one Bastion, an elite she can walk round.
    for k in range(9):
        a = k / 9 * 2 * math.pi
        sx2, sy2 = p.dry(-36000 + math.cos(a) * (3500 + 900 * (k % 3)), -44000 + math.sin(a) * (3500 + 900 * (k % 3)), 60)
        p.foe(3 if k % 3 == 2 else 0, 1, 'Marsh Shard %d' % k, sx2, sy2)
    for k, (mx2, my2) in enumerate(((-42000, -40000), (-31000, -49000), (-39000, -51000))):
        mx2, my2 = p.dry(mx2, my2, 60)
        p.foe(1 if k == 1 else 0, 2, 'Marsh Matriarch %d' % k, mx2, my2)
    # Its thorns' tag on the south side: to the north it stood a metre from a leg of the Marsh Arch, 11 m away.
    p.cage('Echo Cache Marsh', -36500, -43000, ',cache2,', 'Echo Cache absorbed. Divinity +60.', bearing=math.pi)
    p.grass('Marsh Capsule', mx + 500, my + 300)

    # ---- The Concourse: an optional fight and an optional prism puzzle.
    p.check('Concourse', -9000, -4000, 'The Concourse. Clear the crystal hunters, or follow the roads: east to Choir Hollow, north-east to Thornveil, south-east to the Glass Highlands.')
    for k in range(12):
        a = k / 12 * 2 * math.pi + .2
        r = 3800 + 1100 * (k % 3)
        p.enemy(1, 'Concourse Shard %d' % k, math.cos(a) * r, math.sin(a) * r, 202)
    for k in range(6):
        a = k / 6 * 2 * math.pi + .7
        p.enemy(2, 'Concourse Matriarch %d' % k, math.cos(a) * 6800, math.sin(a) * 6800, 202)
    # The Goal goes on this fight only: the prism puzzle (203, Static prisms) overlaps the plaza, and two Goals there
    # would take turns on the objective line. 80 m covers the matriarchs' ring (68 m) and some room to fight in.
    p.encounter('Concourse Fight', 0, 0, 202, ',concourse,', 'The plaza is quiet. The crystal hunters scatter, and a cache of Divinity glows by the old dish.', 'Explore the Center. Choir Hollow lies east, along the canyon road.')
    p.relic('Concourse Cache', p.at(8000, -7000, 140), ',cache3,', 'The surveyors left Divinity here for whoever came next. Divinity +80.', ',concourse,', 80.0, mesh='SM_CT_Crystal0', scale=.4)
    # The prisms carry the vault prisms' 'Light Prism' entry. They were made by enemy(), which gave them the
    # Shardling's, so scanning a Shardling would also have greyed them (scans review, 2026-11-08).
    light = next(row for row in CENTER_SCANS if row[1] == 'Light Prism')
    for k, (dx, dy) in enumerate(((1800, 6800), (-7600, 1600), (5200, -6200))):
        pillar = p.mesh('Prism Pillar %d' % k, 'SM_CA_HumanPillar', p.at(dx, dy, -20), (0, 0, k * 40), (1, 1, 1.4))
        z = max(ground.at(dx, dy), 0) + 1500
        target = p.spawn('BP_TrainingDrone', 'Enemy L1 Prism %d' % k, (dx, dy, z), (1, 1, 1), 'Enemies', RoomId=203, Boss=False, Health=1)
        target.set_editor_property('Static', True)
        p.reskin(target, 'SM_CT_Crystal0')
        tag = p.scan(light[0], light[1], light[2], (dx, dy, z + 60), True)
        tag.attach_to_actor(target, 'None', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    p.encounter('Prism Puzzle', 0, 6000, 203, ',prisms,', 'Three prisms wake, and the ring above the plaza sings. A light pours down beside the stairs.', '')
    p.relic('Prism Gift', p.at(-8000, -2000, 140), ',cache4,', 'A gift from the ring: Physis is fully healed and gains Divinity +50.', ',prisms,', 50.0, True, 'SM_CT_Crystal1', .25)

    # ---- Choir Hollow: clear the guardians, then learn Settle at the shrine.
    p.check('Choir', -12860, 39000, 'Reach the shrine at the heart of Choir Hollow.', 900)
    # Settle depends on this fight, so it is doubled with lighter escorts rather than tripled.
    for k in range(10):
        a = k / 10 * 2 * math.pi
        level = 3 if k % 5 < 2 else 2
        p.enemy(level, 'Choir Guard %d' % k, -15000 + math.cos(a) * (3500 + 900 * (k % 2)), 56000 + math.sin(a) * (3500 + 900 * (k % 2)), 204)
    p.encounter('Choir Fight', -15000, 56000, 204, ',choir,', 'The Hollow falls silent. Every stone holds its note. The shrine is waiting.', 'Step into the Settle Shrine and use Interact.',
                'Defeat the golden guardians of the Hollow', 5500.0)
    p.mesh('Settle Shrine Ring', 'SM_CA_Shrine', (-15000, 56000, 0), (0, 0, 0), 1.0, 'Choir')
    p.switch('Settle Shrine', (-15000, 56000, 50), 0, 'SM_CT_Crystal1', Need=',choir,', Give=',settle,',
             Denied='The shrine does not answer while its guardians still stir. Quiet the Hollow first.',
             Done='Physis remembers Meridian, and this time she means it.~Settle learned: V / |DR|.  It calms creatures, dissolves thorn barriers and closes Divinity wounds.~Her perception sharpens: the Center comes fully into focus.')
    p.light('Shrine Light', (-15000, 56000, 900), (.5, .9, 1), 20000, 3500)
    p.cage('Echo Cache Choir', -19000, 61000, ',cache5,', 'Echo Cache absorbed. Divinity +60.')
    p.grass('Choir Capsule', -12000, 42000)
    p.grass('Choir Ammo', -12500, 42500)

    # ---- Thornveil: Settle opens the thorns and closes the wounds; Stillstone 2 lies at the heart.
    p.check('Thornveil', 26000, 26000, 'Thornveil. Use Settle to pass the thorns and find the Stillstone at their heart.')
    hx, hy = 40000, 44000
    for k in range(10):
        a = k / 10 * 2 * math.pi
        p.barrier('Heart Thorn %d' % k, hx + math.cos(a) * 1900, hy + math.sin(a) * 1900, math.degrees(a))
    p.mesh('Heart Dais', 'SM_CA_Platform', p.at(hx, hy, 40), (0, 0, 0), (1.6, 1.6, 1), 'Thornveil')
    p.relic('Stillstone Two', p.at(hx, hy, 220), ',stone2,', 'Stillstone recovered. The thorns remember they were never walls.')
    p.light('Heart Glow', p.at(hx, hy, 600), (1, .45, .7), 9000, 2600)
    for k, (wx2, wy2) in enumerate(((31500, 33000), (34500, 37500), (36000, 31000))):
        p.wound('Thornveil %d' % k, wx2, wy2, 900, ',wound%d,' % k)
    for k in range(12):
        a = k / 12 * 2 * math.pi + .4
        r = 4300 + 1000 * (k % 3)
        p.enemy(3 if k % 2 == 0 else 2, 'Thorn Guard %d' % k, hx + math.cos(a) * r, hy + math.sin(a) * r, 205)
    # No count line here: Stillstone Two lies at the fight's centre, and the count would replace the main quest's
    # guidance while she takes it (review, 2026-11-08). Its guardians stay gold.
    p.encounter('Thornveil Fight', hx, hy, 205, ',thornfight,', 'The Thornveil guardians fall still.', '')
    p.cage('Echo Cache Thornveil', 30000, 46000, ',cache6,', 'Echo Cache absorbed. Divinity +60.')
    p.grass('Thornveil Capsule', 28000, 29000)

    # ---- Glass Highlands: a spiral of floating stones to Stillstone 3; Sentinels are optional end-game.
    p.check('Highlands', 26000, -30000, 'Climb the floating stair at the Glass Highlands spire for the last Stillstone. It comes only to one who '
            'carries the other two. Avoid the Sentinels, or test yourself against them.')
    cx, cy = 42000, -50000
    base = max(ground.at(cx + 2600, cy), 0)
    for k in range(14):
        a = k * .55
        r = 2600 - k * 40
        z = base + 120 + k * 105
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        if k in (5, 10):
            plat = p.spawn('BP_Platform', 'Spire Drift %d' % k, (x, y, z), None, 'Highlands', AmpX=0.0, AmpY=0.0, AmpZ=90.0, Period=5.0, Need='')
            p.reskin(plat, 'SM_CA_Platform')
        else:
            p.mesh('Spire Stone %d' % k, 'SM_CA_Platform', (x, y, z), (0, 0, math.degrees(a)), (.75, .75, .6), 'Highlands')
    top = (cx + math.cos(14 * .55) * 2000, cy + math.sin(14 * .55) * 2000, base + 120 + 14 * 105)
    p.mesh('Spire Crown', 'SM_CA_Platform', top, (0, 0, 0), (1.5, 1.5, 1), 'Highlands')
    # The last Stillstone is the last one taken (author, 2026-11-09: "I got the last Stillstone relic before any other
    # same relics. That should also be impossible."). Stillstone Pair gives ,stones12, once One and Two are both held,
    # with a line that replaces the second stone's own; until then Stillstone Three shows on its crown (Tease) and says
    # why it stays (Locked, once per approach).
    p.require('Stillstone Pair', (cx, cy, base + 200), (',stone1,', ',stone2,'), ',stones12,',
              'Stillstone recovered: two of three. The last waits atop the floating stair at the Glass Highlands spire, and now it will come to you.')
    last = p.relic('Stillstone Three', (top[0], top[1], top[2] + 180), ',stone3,', 'Stillstone recovered: the last of three. The Temple of the First Light, far to the north, is waiting.',
                   ',stones12,')
    last.set_editor_property('Tease', True)
    last.set_editor_property('Locked', wrap_text('This Stillstone will not leave its crown until you carry the other two, from '
                                                 'Lantern Marsh and the heart of Thornveil.'))
    p.light('Crown Glow', (top[0], top[1], top[2] + 500), (.6, .8, 1), 9000, 2500)
    for k, (dx, dy) in enumerate(((-9000, 5000), (7000, 9000))):
        p.enemy(5, 'Highland Sentinel %d' % k, cx + dx, cy + dy, 206)
        for e in range(2):
            a = e * math.pi + k
            p.enemy(3, 'Sentinel Escort %d %d' % (k, e), cx + dx + math.cos(a) * 2600, cy + dy + math.sin(a) * 2600, 206)
    # The roomless Wardens are no part of the fight; one of them is a Bastion.
    for k, (dx, dy) in enumerate(((-6000, -6000), (9000, -9000), (-12000, -2000))):
        p.foe(1 if k == 1 else 0, 4, 'Highland Warden %d' % k, cx + dx, cy + dy)
    # The two Sentinel groups stand 165 m apart on either side of the spire, so one circle round both covers the spire's
    # stair too, and the Goal says the fight is optional: the region's text says she need not fight them.
    # No count line either: its circle would cover the whole floating stair to Stillstone Three (review, 2026-11-08).
    p.encounter('Sentinel Fight', cx, cy, 206, ',sentinels,', 'Both Hollow Sentinels fall silent. Very few would have managed that. A great cache of Divinity spills free on the high ground.', '')
    p.relic('Sentinel Hoard', p.at(cx - 3000, cy + 9000, 140), ',cache7,', 'The Sentinels guarded this for an age. Divinity +150, and Physis is fully healed.', ',sentinels,', 150.0, True, 'SM_CT_Crystal1', .3)
    p.grass('Highland Capsule', 26500, -30500)
    p.grass('Highland Ammo', 27000, -30500)

    # ---- The Temple of the First Light.
    tx, ty = TEMPLE
    p.check('Temple Stair', tx - 9000, ty, 'Return the three Stillstones to the Temple of the First Light. Settle the thorns that guard its stair.', 900)
    # The two thorn walls now stand across the stair (yaw 0), overlapping in the middle: at yaw 90 they ran along it and
    # left its middle 9 m open (bounds 14.3 x 3.9 m; temple review 2026-11-08, again 2026-11-09), so she could climb to
    # the sanctum without Settle. Each spans 14.3 m, so at 4.5 m either side of the centre line they cover 23 m, the
    # 18 m stair and a little more.
    for k, side in enumerate((-450, 450)):
        p.barrier('Temple Thorn %d' % k, tx - 4700, ty + side, 0, ',templethorn,' if k == 0 else '')
    # Three sockets: two pedestals flanking the door and a floating crown above it. Each stone rises into view when found.
    for k, (spot, token, pedestal) in enumerate((((tx - 2650, ty - 2200, TEMPLE_FLOOR + 600), ',stone1,', True),
                                                 ((tx - 2650, ty, TEMPLE_FLOOR + 600 + 1650), ',stone2,', False),
                                                 ((tx - 2650, ty + 2200, TEMPLE_FLOOR + 600), ',stone3,', True))):
        if pedestal:
            p.mesh('Socket %d' % k, 'SM_CA_Lantern', spot, (0, 0, 0), 1.0, 'Temple')
        p.rise('Socket Stone %d' % k, 'SM_CA_Stillstone', (spot[0], spot[1], spot[2] + (430 if pedestal else 0)), token, 150, (0, 0, 0), 1.4, 60)
    door = p.rise('Temple Door', 'SM_CA_Platform', (tx - 2400, ty, TEMPLE_FLOOR + 600 + 800), ',temple,', -1700, (90, 0, 0), (2.7, 2.7, .5), 200)
    door.set_actor_location(unreal.Vector(tx - 2400, ty, TEMPLE_FLOOR + 600 + 800), False, False)
    p.require('Temple Keys', (tx - 3000, ty, TEMPLE_FLOOR + 800), (',stone1,', ',stone2,', ',stone3,'), ',temple,',
              'Three Stillstones settle into their sockets. The Temple of the First Light opens.')
    # This Still Point stands 16 m from the sanctum's centre, inside the fight's count ('Defeat the golden guardians: N
    # left', 26 m). Its objective, set there, would file the count line in the Completed list (PhysisQuest files the
    # objective it replaces), so it never sets one: Until is ,center,, which every Center visit holds. It still heals
    # and is still her checkpoint. ,temple, (the door's token) would not be enough: by the temple's geometry the
    # colonnade leaves 4.9 m between its columns, so the door may not be the only way in from the top tier (not tried
    # in Play, 2026-11-08). The fight's win sets the next objective.
    p.check('Sanctum', tx - 1600, ty, 'Reach the Heartbloom at the centre of the sanctum.', 500, until=',center,')
    # Mend depends on this fight (temple review, 2026-11-08). The guardians stand on the ring floor at 0.6 scale, their
    # lowest point 20 cm over it, boxed to the colonnade's square (they fight only while she is inside it) and kept
    # between 10 and 19 m from the centre (center_overrides DroneArena): clear of the crystal ring and of the columns,
    # where the full-size ones stuck, and sent back where they stood if one sticks anyway.
    arena = dict(ArenaAt=unreal.Vector(tx, ty, 0.0), ArenaIn=1000.0, ArenaOut=1900.0,
                 RoomMin=unreal.Vector(tx - 2400, ty - 2400, -100000.0), RoomMax=unreal.Vector(tx + 2400, ty + 2400, 100000.0))
    for level, label, bearing in SANCTUM_GUARDIANS:
        a = math.radians(bearing)
        p.enemy(level, label, tx + math.cos(a) * 1300, ty + math.sin(a) * 1300, 207, scale=.6, settle=True, **arena)
    # 26 m from the centre: the colonnade (24 m) and 2 m more.
    p.encounter('Sanctum Fight', tx, ty, 207, ',sanctum,', 'The golden guardians bow and go dark. The Heartbloom opens.', 'Take the Heartbloom from its pedestal.',
                'Defeat the golden guardians', 2600.0)
    p.mesh('Heartbloom', 'SM_CA_Artifact', (tx, ty, TEMPLE_FLOOR + 600 + 275), (0, 0, 0), 1.3, 'Temple', False)
    # The switch's origin is the top of the pedestal's central column. The drum around it is 3 m wide with a 60 cm
    # rim, more than she can step, so from the floor she stops 3.35 m out and 3.8 m from the origin. Reach 450 lets
    # her take the Heartbloom from the floor on any side. center_overrides switch_reach reads it, in part conclave's
    # PhysisInteract and in conclave_hud.py's DrawInteract. The station's versions of those two, back after a station
    # rebuild until they run again, keep 260 for every switch.
    # Mend comes after the Stillstones and Settle (author, 2026-11-09: "I was able to get Mend before Settle. That should
    # be impossible."). The colonnade's 4.9 m gaps let her into the sanctum without the door, so the guardians' fight
    # alone proved nothing: the pedestal also needs ,temple, (the three Stillstones home, BP_Switch NeedB) and ,settle,
    # (NeedC; center_overrides part switches), whatever way she got in.
    pedestal = p.switch('Heartbloom Pedestal', (tx, ty, TEMPLE_FLOOR + 600 + 270), 0, None, Need=',sanctum,', Give=',mend,', Reach=450.0,
                        Denied='The golden guardians will not let you near the Heartbloom while they stand.', NeedB=',temple,',
                        DeniedB=wrap_text('The Heartbloom stays sealed until the three Stillstones are home. Find them, set them in the '
                                          'sockets at the temple door, then return.'),
                        NeedC=',settle,',
                        DeniedC=wrap_text('The Heartbloom has opened, but it will not come to someone who cannot yet Settle. '
                                          'Learn Settle at the shrine in Choir Hollow, then return.'))
    # The Done text names the Conclave portal: BP_Current "Conclave Current", placed by the Conclave session's
    # re-runnable conclave:portal op, which sets this same text on the placed actor. Keep the two identical. It is
    # set as is, after set_props, so the agreed four lines stay four.
    pedestal.set_editor_property('Done', HEARTBLOOM_DONE)
    for k in range(2):
        p.grass('Temple Capsule %d' % k, tx - 1800, ty - 600 + 1200 * k)

    puzzles(p)
    # The fifteen ability vaults (physis_center_vaults.py), clear of the hubs, Still Points, fights and puzzles.
    import importlib
    import physis_center_vaults
    importlib.reload(physis_center_vaults)
    taken = [(x, y, 7000) for _, x, y in PUZZLE_SITES] + [(x, y, r) for (x, y), r in HUB_RADII] + [(x, y, 6000) for x, y in STILL_POINTS]
    for title, x, y in physis_center_vaults.build(p, road_lines_cache(), taken):
        PUZZLE_SITES.append((title, x, y))
    divinity_rays(p)
    wilderness(p)
    grass_fields(p)

    # ---- Scans, fauna, voices, tutorials.
    for category, title, text, place_, important in CENTER_SCANS:
        if title == 'The Lantern Stele':
            # Over the stele, which is dried off its requested point above. Its tip is 2.09 m over the floor (the mesh
            # is 22.4 m tall, at 0.12 and sunk 0.6 m); at 1.5 m the tag was inside it, where the visor's line of sight
            # never reaches (lantern review, 2026-11-08). Half a metre over the tip.
            x, y = p.dry(place_[0], place_[1], 60)
            place_ = (x, y, p.floor(x, y) + 260)
        elif title == 'Stillstone':
            # Over Stillstone One (its centre 230, top 310), not at the lore point 113 m away, beyond the visor's 25 m.
            # 1.2 m above the stone's centre, so the stone's own tag takes it in (BP_Relic, within 1.5 m) and it goes
            # when the stone is taken.
            place_ = (ISLE[0], ISLE[1], 350)
        p.scan(category, title, text, place_, important)
    # Animals carry their own scan tags (physis_center_tools.fauna_actors).
    for category, title, text in center_entries():
        voice = unreal.load_asset(AUDIO + '/Voice/' + voice_name(title))
        image = unreal.load_asset('/Game/UI/Log/' + image_name(title))
        p.spawn('BP_LogVoice', 'Voice ' + title, (0, 0, -50000), folder='Voices', Title=title, Voice=voice, Image=image)
    for actor in sub().get_all_level_actors():
        if actor.get_class().get_name() == 'BP_ScanTarget_C':
            # Changing a property re-runs the tag's construction script, which can drop its attachment.
            parent = actor.get_attach_parent_actor()
            text = actor.get_editor_property('ScanText')
            actor.set_editor_property('ScanText', wrap_text(text.replace('~', ' ')))
            if parent and actor.get_attach_parent_actor() is None:
                actor.attach_to_actor(parent, 'None', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    # Tutorial triggers, placed here rather than through game.place_tutorials(), which saves to the station map. The
    # Stillstone isle's and the Sunken Causeway islet's (their places are chosen above) are already placed.
    for index, (text, (x, y), scale) in enumerate(CENTER_TUTORIALS):
        p.hint('%02d' % (index + 1), x, y, text, scale)
    sound_scape(p)
    from physis_center_tools import save_level
    save_level()
    return {'placed': p.count, 'puzzles': PUZZLE_SITES}


# ---------------------------------------------------------------- puzzles and packs between the regions

PUZZLE_SITES = []


def heading(p, x, y, length, headings=16):
    """The heading (radians) from (x, y) along which the ground rises least over `length` cm, avoiding water:
    climbs built along it stay clear of the ground and cannot be skipped by walking up a hill."""
    best = None
    for k in range(headings):
        a = k / headings * 2 * math.pi
        h = [p.g.at(x + math.cos(a) * length * t / 12, y + math.sin(a) * length * t / 12) for t in range(13)]
        cost = max(h) - h[0] + 400 * sum(1 for v in h if v < 40)
        if best is None or cost < best[0]:
            best = (cost, a)
    return best[1]


def puzzles(p):
    """Optional environmental puzzles in the stretches between the regions, each with its own cache.
    Mesh sizes (cm, scale 1): HumanWall 2400 x 140 x 880 (pivot at its foot), HumanArch 320 x 1520 x 1510,
    HumanPillar 280 x 920 (foot), Monolith 679 x 2340, Platform 600 x 520, 558 deep below its top-surface pivot,
    RootBridge 2012 x 458 with its deck at the pivot and side rails 1 m high, Rock2 2099 x 1366 x 1318,
    Crystal1 659 x 746 x 911, SettleBarrier 390 thick and 1428 wide along its local Y.
    Physis jumps about 150 cm, so every climb rises at most 110 cm a step."""
    PUZZLE_SITES.clear()

    def keep(name, x, y):
        PUZZLE_SITES.append((name, round(x), round(y)))

    def sign(name, x, y, z):
        """The puzzle's scan tag (physis_center_lore PUZZLE_SCANS, saying what to do there) at z, over the piece it
        stands by and clear of every mesh, since the visor needs a line of sight to a free tag (lantern review,
        2026-11-08: none of the eight puzzles had one)."""
        row = next(r for r in PUZZLE_SCANS if r[1] == name)
        return p.scan(row[0], row[1], row[2], (x, y, z), True)

    # 1. Bell Ruins (north-west, between the Glade and Choir Hollow): three glass bells stand in a ruined court.
    #    Ring all three (any order) and the court raises its old cache.
    bx, by = p.site(-45000, 28000, 2000, 4000)
    keep('Bell Ruins', bx, by)
    sign('Bell Ruins', bx, by, p.floor(bx, by) + 350)  # over the court's sunken dais, the bells 18 m round it
    p.mesh('Bell Ruin Arch', 'SM_CA_HumanArch', p.at(bx - 2300, by + 300, -40), (0, 0, 15), .8, 'Puzzles')
    for k, (dx, dy, yaw) in enumerate(((-1500, 1400, 40), (1700, -1100, -35), (900, 1900, 150), (-1200, -1700, 100))):
        p.mesh('Bell Ruin Wall %d' % k, 'SM_CA_HumanWall', p.at(bx + dx, by + dy, -80), (0, 0, yaw), (.45, .6, .5 + .1 * (k % 2)), 'Puzzles')
    for k in range(3):
        a = k / 3 * 2 * math.pi + .5
        x, y = bx + math.cos(a) * 1800, by + math.sin(a) * 1800
        bell = p.switch('Ruin Bell %d' % k, p.at(x, y, 0), math.degrees(a), 'SM_CT_Crystal1', True, Give=',bell%d,' % k, Need='', Denied='',
                        Done='The glass bell rings, low and long, and its note hangs in the court.')
        bell.set_actor_scale3d(unreal.Vector(.3, .3, .3))
        p.light('Ruin Bell Glow %d' % k, p.at(x, y, 300), (.55, .85, 1), 1800, 800)
    p.require('Bell Chord', p.at(bx, by, 300), (',bell0,', ',bell1,', ',bell2,'), ',bells,',
              'All three bells sound one chord. The floor of the court opens, and an old cache rises into the light.')
    p.rise('Bell Cache Dais', 'SM_CA_Platform', p.at(bx, by, 60), ',bells,', 260, (0, 0, 0), (.6, .6, .5), 90)
    p.relic('Bell Cache', p.at(bx, by, 190), ',cache8,', 'The court kept its cache for whoever rang it true. Divinity +80, and Physis is fully healed.',
            ',bells,', 80.0, True, 'SM_CT_Crystal0', .4)
    p.light('Bell Court Glow', p.at(bx, by, 600), (.55, .85, 1), 2500, 2400)

    # 2. Sunken Causeway (the deep water east of the marsh): a stone on the shore raises a causeway to an islet
    #    whose cache glows across the water. The islet's sides stand too high to climb out of the water.
    deep, low = None, -150.0
    for gx in range(-34000, -12000, 1000):
        for gy in range(-64000, -34000, 1000):
            h = p.g.at(gx, gy)
            if h < low:
                low, deep = h, (gx, gy)
    if deep:
        ix, iy = deep
        keep('Sunken Causeway', ix, iy)
        sx, sy = p.dry(ix + 2500, iy + 2500, 60, 9000)
        dx, dy = ix - sx, iy - sy
        steps = max(2, int(math.hypot(dx, dy) / 580))
        p.mesh('Causeway Islet', 'SM_CA_Platform', (ix, iy, 60), (0, 0, 15), (1.4, 1.4, 1.2), 'Puzzles')
        for k in range(1, steps):
            t = k / steps
            p.rise('Causeway Stone %d' % k, 'SM_CA_Platform', (sx + dx * t, sy + dy * t, 45 + 10 * (k % 2)), ',causeway,', 450,
                   (0, 0, k * 31), (.7, .7, .7), 140 + k * 12)
        stone = p.switch('Causeway Stone', p.at(sx, sy, -30), 0, 'SM_CA_Monolith', True, Give=',causeway,', Need='', Denied='',
                         Done='The stone sinks into the mud, and old stones lift out of the water toward the islet.')
        stone.set_actor_scale3d(unreal.Vector(.12, .12, .1))
        p.light('Causeway Stone Glow', p.at(sx, sy, 330), (.4, .9, 1), 1500, 700)
        stone_ring(p, 'Islet Ring', ix, iy, 320, (sx, sy), ',causeway,', 'Puzzles')
        p.relic('Islet Cache', (ix, iy, 190), ',cache9,', 'The islet\'s cache: Divinity +70, and Physis is fully healed.', '', 70.0, True, 'SM_CT_Crystal0', .4)
        p.light('Islet Glow', (ix, iy, 450), (.4, .9, 1), 4000, 1600)
        # Over the islet, where the gold ray leads, 60 cm over its cache (which reaches 3.6 m). The shore stone that
        # solves it is 40 m off, beyond the visor's 25 m, so a strip says where it is to anyone who swims out.
        sign('Sunken Causeway', ix, iy, 420)
        p.hint('Causeway Islet', ix, iy, 'A ring of First One stones closes the islet. Its causeway to the shore to the %s, and '
               'the gate in the ring, open when the standing stone there is woken with Interact.' % compass(sx - ix, sy - iy), (4, 4, 1.5))

    # 3. The Four Monoliths (east of the Concourse): four First One stones wake only from the shortest to the
    #    tallest, and they do not stand in that order.
    mx, my = p.site(32000, 4000, 1500)
    keep('Four Monoliths', mx, my)
    for rank, (size, spot) in enumerate(((.12, 2), (.17, 0), (.22, 3), (.27, 1))):
        a = spot / 4 * 2 * math.pi + .3
        x, y = mx + math.cos(a) * 2400, my + math.sin(a) * 2400
        last = rank == 3
        stone = p.switch('Monolith %d' % rank, p.at(x, y, -40), math.degrees(a), 'SM_CA_Monolith', True,
                         Give=',monoliths,' if last else ',mono%d,' % (rank + 1), Need='' if rank == 0 else ',mono%d,' % rank,
                         Denied='The stone stays cold. A smaller stone must wake before it.',
                         Done='The tallest stone wakes last. Light runs between all four, and something answers at their centre.' if last else 'The stone wakes with a low note.')
        stone.set_actor_scale3d(unreal.Vector(size, size, size))
        p.light('Monolith Glow %d' % rank, p.at(x, y, 120 + 2340 * size), (.6, .8, 1), 1500, 900)
    p.relic('Monolith Gift', p.at(mx, my, 160), ',cache10,', 'The four stones\' gift: Divinity +100.', ',monoliths,', 100.0, False, 'SM_CT_Crystal1', .25)
    sign('Four Monoliths', mx, my, p.floor(mx, my) + 450)  # over the centre and its gift (which reaches 3.7 m), the stones 24 m round it

    # 4. Drifting Steps (beside the canyon road to Choir Hollow): slabs that rise and fall, each a little higher,
    #    lead to a ledge on a pillar with a cache on top. Time each jump to a slab's low point.
    sx, sy = p.site(7000, 31000, 900)
    keep('Drifting Steps', sx, sy)
    sign('Drifting Steps', sx, sy, p.floor(sx, sy) + 250)  # at the start, 3.4 m short of the first slab
    a = heading(p, sx, sy, 3000)
    ux, uy = math.cos(a), math.sin(a)
    base = p.at(sx, sy)[2]
    for k in range(4):
        x, y = sx + ux * 520 * (k + 1), sy + uy * 520 * (k + 1)
        plat = p.spawn('BP_Platform', 'Drift Step %d' % k, (x, y, base + 110 * (k + 1)), None, 'Puzzles',
                       AmpX=0.0, AmpY=0.0, AmpZ=60.0, Period=5.0 + .6 * k, Need='')
        p.reskin(plat, 'SM_CA_Platform')
        plat.set_actor_rotation(unreal.Rotator(0, 0, math.degrees(a)), False)
        plat.set_actor_scale3d(unreal.Vector(.6, .6, .3))
    lx, ly = sx + ux * 520 * 5.2, sy + uy * 520 * 5.2
    top = base + 560
    p.mesh('Drift Ledge', 'SM_CA_Platform', (lx, ly, top), (0, 0, math.degrees(a)), (1.0, 1.0, .35), 'Puzzles')
    ground = max(p.g.at(lx, ly), 0.0)
    p.mesh('Drift Pillar', 'SM_CA_HumanPillar', (lx, ly, ground - 40), (0, 0, 0), (1.4, 1.4, max(.2, (top - 550 * .35 - ground + 60) / 920)), 'Puzzles')
    p.relic('Ledge Cache', (lx, ly, top + 130), ',cache11,', 'High above the canyon road: Divinity +70.', '', 70.0, False, 'SM_CT_Crystal0', .4)
    p.light('Ledge Glow', (lx, ly, top + 450), (.5, 1, .8), 3000, 1400)

    # 5. Thorn Garden (east, near the Temple road): a walled garden whose only gate is sealed by thorns.
    gx, gy = p.site(64000, 34000, 1500)
    keep('Thorn Garden', gx, gy)
    for k, (dx, dy, yaw, length) in enumerate(((0, 1050, 0, .9), (1050, 0, 90, .9), (-1050, 0, 90, .9), (-700, -1050, 0, .25), (700, -1050, 0, .25))):
        p.mesh('Garden Wall %d' % k, 'SM_CA_HumanWall', p.at(gx + dx, gy + dy, -60), (0, 0, yaw), (length, 1.3, .7), 'Puzzles')
    # Yaw 90 turns the barrier's width (its local Y) along the south wall, across the 8 m gate.
    p.barrier('Garden Gate Thorn', gx, gy - 1050, 90)
    sign('Thorn Garden', gx, gy - 1550, p.floor(gx, gy - 1550) + 250)  # outside the gate, 3 m off the thorns' face
    p.relic('Garden Cache', p.at(gx, gy, 150), ',cache12,', 'The sealed garden kept its Divinity for an age. Divinity +100, and Physis is fully healed.',
            '', 100.0, True, 'SM_CT_Crystal1', .25)
    p.light('Garden Glow', p.at(gx, gy, 500), (1, .5, .8), 4000, 1500)

    # 6. Wounded Gully (south of the Concourse, toward the Marsh road): a dead-end gully of rock with a cache at
    #    its end and three Divinity wounds across its floor. They pulse in turn: run each one while it is dark,
    #    or close them for good with Settle. A wound's hurt zone is an axis-aligned square and its pool is flat,
    #    so the gully runs along a world axis on the flattest ground nearby (about half a metre of relief).
    best = None
    for cx in range(-15000, 15001, 1500):
        for cy in range(-45000, -15000, 1500):
            if any(math.hypot(cx - sx, cy - sy) < 9000 for _, sx, sy in PUZZLE_SITES) or math.hypot(cx, cy) < 15000:
                continue
            for yaw in (0, 90):
                ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
                h = [p.g.at(cx + ca * u - sa * v, cy + sa * u + ca * v) for u in range(-3000, 3001, 500) for v in (-800, 0, 800)]
                if min(h) < 80:
                    continue
                if best is None or max(h) - min(h) < best[0]:
                    if road_gap(cx, cy) >= 2500:
                        best = (max(h) - min(h), cx, cy, yaw)
    _, wx2, wy2, yaw = best
    keep('Wounded Gully', wx2, wy2)
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    spot = lambda u, v: (wx2 + ca * u - sa * v, wy2 + sa * u + ca * v)
    # Between the first rocks, short of the first wound's pool (it starts at u -2225), and within the visor's 25 m of the
    # ray over the gully's middle.
    x, y = spot(-2300, 0)
    sign('Wounded Gully', x, y, p.floor(x, y) + 250)
    # Rock2 at (.55, .5, .6) is 1156 long and 684 deep; 800 apart they overlap, 792 out they leave a 9 m floor.
    for k, u in enumerate(range(-2400, 2401, 800)):
        for side in (-1, 1):
            x, y = spot(u, side * 792)
            p.mesh('Gully Rock %d %d' % (k, side), 'SM_CT_Rock2', p.at(x, y, -120), (0, 0, yaw + side * 3 + (k % 3 - 1) * 3), (.55, .5, .6), 'Puzzles')
    x, y = spot(2700, 0)
    p.mesh('Gully Rock End', 'SM_CT_Rock2', p.at(x, y, -120), (0, 0, yaw + 90), (.55, .5, .6), 'Puzzles')
    for k, u in enumerate((-1700, -500, 700)):
        x, y = spot(u, 0)
        p.wound('Gully %d' % k, x, y, 1050, ',wound%d,' % (k + 3), Period=3.0, Offset=k * 2.1)
    x, y = spot(1900, 0)
    p.relic('Gully Cache', p.at(x, y, 130), ',cache13,', 'Past the wounds, the gully\'s cache: Divinity +90.', '', 90.0, False, 'SM_CT_Crystal0', .4)
    p.light('Gully Glow', p.at(x, y, 450), (1, .45, .45), 3000, 1200)

    # 7. Root Stair (north, between Choir Hollow and Thornveil): a crystal raises four living roots into a stair,
    #    each 110 cm above the last, up to a lookout with a cache. Built along the heading where the hill falls away.
    rx, ry = p.site(14000, 60000, 1500)
    keep('Root Stair', rx, ry)
    a = heading(p, rx, ry, 6600)
    ux, uy = math.cos(a), math.sin(a)
    base = p.at(rx, ry)[2]
    crystal = p.switch('Root Crystal', p.at(rx - ux * 450, ry - uy * 450, 0), math.degrees(a), 'SM_CT_Crystal1', True, Give=',rootstair,', Need='', Denied='',
                       Done='The crystal hums, and the roots of the hill lift into a stair.')
    crystal.set_actor_scale3d(unreal.Vector(.3, .3, .3))
    p.light('Root Crystal Glow', p.at(rx - ux * 450, ry - uy * 450, 300), (.6, 1, .6), 1500, 800)
    sign('Root Stair', rx - ux * 450, ry - uy * 450, p.floor(rx - ux * 450, ry - uy * 450) + 400)  # over the crystal, 2.5 m tall
    # RootBridge at x .7 is 1411 long; 1450 apart leaves a 40 cm gap between steps.
    for k in range(4):
        c = 700 + 1450 * k
        p.rise('Root Step %d' % k, 'SM_CT_RootBridge', (rx + ux * c, ry + uy * c, base + 100 + 110 * k), ',rootstair,', 900 + 110 * k,
               (0, 0, math.degrees(a) + (k % 2) * 4 - 2), (.7, 1.3, 1.0), 220)
    c = 700 + 1450 * 3 + 705 + 60 + 330
    look = (rx + ux * c, ry + uy * c, base + 540)
    p.mesh('Root Lookout', 'SM_CA_Platform', look, (0, 0, math.degrees(a)), (1.1, 1.1, .5), 'Puzzles')
    ground = max(p.g.at(look[0], look[1]), 0.0)
    p.mesh('Root Lookout Pillar', 'SM_CA_HumanPillar', (look[0], look[1], ground - 40), (0, 0, 0), (1.6, 1.6, max(.2, (look[2] - 275 - ground + 60) / 920)), 'Puzzles')
    p.relic('Lookout Cache', (look[0], look[1], look[2] + 130), ',cache14,', 'From the lookout the whole north lies open. Divinity +80.', '', 80.0, False, 'SM_CT_Crystal0', .4)
    p.light('Lookout Glow', (look[0], look[1], look[2] + 450), (.6, 1, .6), 3000, 1400)

    # 8. Sky Stones (the Marsh's southern edge): a spiral of floating stones up to a crown, 100 cm a step.
    kx, ky = p.site(-12000, -66000, 1500)
    keep('Sky Stones', kx, ky)
    sign('Sky Stones', kx, ky, p.floor(kx, ky) + 250)  # in the spiral's middle, its stones 13 m round it
    base = p.at(kx, ky)[2]
    for k in range(10):
        a = k * .42
        p.mesh('Sky Stone %d' % k, 'SM_CA_Platform', (kx + math.cos(a) * 1300, ky + math.sin(a) * 1300, base + 100 * (k + 1)),
               (0, 0, math.degrees(a)), (.55, .55, .45), 'Puzzles')
    crown = (kx + math.cos(10 * .42) * 900, ky + math.sin(10 * .42) * 900, base + 100 * 11)
    p.mesh('Sky Crown', 'SM_CA_Platform', crown, (0, 0, 0), (1.1, 1.1, .8), 'Puzzles')
    p.relic('Crown Cache', (crown[0], crown[1], crown[2] + 130), ',cache15,', 'The sky stones\' crown: Divinity +100, and Physis is fully healed.',
            '', 100.0, True, 'SM_CT_Crystal1', .25)
    p.light('Crown Glow Sky', (crown[0], crown[1], crown[2] + 450), (.7, .8, 1), 4000, 1600)

    # Echo Caches in the far corners of the basin: only Settle opens them.
    for k, (ex, ey) in enumerate(((-82000, 45000), (66000, -66000), (-80000, -72000), (70000, 66000))):
        ex, ey = p.dry(ex, ey, 80, 9000)
        keep('Echo Cache %d' % (k + 8), ex, ey)
        p.cage('Echo Cache Far %d' % k, ex, ey, ',cache%d,' % (16 + k), 'Echo Cache absorbed. Divinity +60.')
        p.light('Far Cache Glow %d' % k, p.at(ex, ey, 300), (.4, .9, 1), 3000, 900)
    return PUZZLE_SITES


# ---------------------------------------------------------------- Divinity Rays
# A shaft of light from the heavens over every optional puzzle, Echo Cache and ability vault (author, 2026-11-04:
# "I can't find any puzzles"). Each is a BP_DivinityRay: an engine cylinder with an M_DivinityRay instance
# (center:rays), no collision or shadow, never distance-culled, drawn over the water plane, hidden from scene
# captures, and out once its reward (the token) is taken. The pause menu's map marks every ray.
# Kilometres tall, so from anywhere in the basin a ray leaves the top of the screen: light from the heavens, not a
# pillar ending in mid-air. Kind, instance, height and width (cm).
RAY_KINDS = ((0, 'MI_DivinityRay_Puzzle', 300000.0, 1000.0), (1, 'MI_DivinityRay_Vault', 250000.0, 900.0), (2, 'MI_DivinityRay_Cache', 200000.0, 700.0))
RAY_DONE = {'Bell Ruins': ',cache8,', 'Sunken Causeway': ',cache9,', 'Four Monoliths': ',cache10,', 'Drifting Steps': ',cache11,',
            'Thorn Garden': ',cache12,', 'Wounded Gully': ',cache13,', 'Root Stair': ',cache14,', 'Sky Stones': ',cache15,',
            'Echo Cache 8': ',cache16,', 'Echo Cache 9': ',cache17,', 'Echo Cache 10': ',cache18,', 'Echo Cache 11': ',cache19,',
            'Vault of the Patient Heart': ',aug_hp1,', 'Vault of the High Ledger': ',aug_hp2,', 'Vault of the Unwoven Span': ',aug_hp3,',
            'Vault of the Long Silence': ',aug_hp4,', 'Court of Edges': ',aug_katana1,', 'The Resonant Blades': ',aug_katana2,',
            'The Rewoven Arena': ',aug_katana3,', 'The Prism Gallery': ',aug_pistol1,', 'The Far Lights': ',aug_pistol2,',
            'The Furnace Walk': ',aug_defense1,', 'The Sentinel Hold': ',aug_defense2,', 'The Burning Stair': ',aug_defense3,',
            'The Lattice Run': ',aug_agility1,', 'The Pulse Garden': ',aug_agility2,', 'The Drift Spire': ',aug_agility3,'}
# The puzzles and Echo Caches of the first build, placed in place() above: (name, x, y, kind, token). The main path's
# own puzzles too (the lantern stele, the Thornveil heart, the floating stair, the temple door), out once solved.
# The marsh has two since 2026-11-08 (lantern review): the stele's, out once the lanterns are lit (,marsh,), and one
# over Stillstone One's isle (placed where place() chose it, ISLE), out once the stone is taken. The stele's alone,
# lit until the stone 300 m away was taken, marked the clue as if it were the reward.
RAY_EXTRA = (('Lantern Marsh', -28500, -36500, 0, ',marsh,'), ('Stillstone Isle', 0, 0, 0, ',stone1,'), ('Heart of Thornveil', 40000, 44000, 0, ',stone2,'),
             ('Glass Highlands Spire', 42000, -50000, 0, ',stone3,'), ('Temple of the First Light', 76000, 0, 0, ',temple,'),
             ('Prism Puzzle', 0, 6000, 0, ',cache4,'), ('Echo Cache Glade', -60000, 9000, 2, ',cache1,'),
             ('Echo Cache Marsh', -36500, -43000, 2, ',cache2,'), ('Echo Cache Choir', -19000, 61000, 2, ',cache5,'),
             ('Echo Cache Thornveil', 30000, 46000, 2, ',cache6,'))


def divinity_rays(p):
    import physis_center_vaults
    vaults = {title for title, _, _ in physis_center_vaults.VAULTS}
    sites = [(name, x, y, 1 if name in vaults else (2 if name.startswith('Echo Cache') else 0), RAY_DONE.get(name, ''))
             for name, x, y in PUZZLE_SITES] + list(RAY_EXTRA)
    box = unreal.load_asset('/Engine/BasicShapes/Cylinder').get_bounding_box()
    looks = {kind: (unreal.load_asset(CENTER + '/Materials/' + look), height, width) for kind, look, height, width in RAY_KINDS}
    for name, x, y, kind, token in sites:
        if name == 'Lantern Marsh':  # over the stele itself: place() dries it 31 m off this point (in the water)
            x, y = p.dry(x, y, 60)
        elif name == 'Stillstone Isle':
            x, y = ISLE
        material, height, width = looks[kind]
        if material is None:
            raise RuntimeError('Run center:rays first: no Divinity Ray material instances')
        sz, sxy = height / (box.max.z - box.min.z), width / (box.max.x - box.min.x)
        foot = p.at(x, y, -300.0)[2]  # sunk 3 m; over water, 3 m below the surface
        ray = p.spawn('BP_DivinityRay', 'Ray ' + name, (x, y, foot - box.min.z * sz), (sxy, sxy, sz), 'Rays', DoneToken=token, Kind=kind, Title=name)
        part = ray.get_components_by_class(unreal.StaticMeshComponent)[0]
        for index in range(max(1, part.get_num_materials())):
            part.set_material(index, material)
        part.set_collision_profile_name('NoCollision')
        for key, value in (('cast_shadow', False), ('never_distance_cull', True), ('ld_max_draw_distance', 0.0),
                           ('allow_cull_distance_volume', False), ('translucency_sort_priority', 10), ('visible_in_ray_tracing', False),
                           ('hidden_in_scene_capture', True), ('receives_decals', False)):
            try:
                part.set_editor_property(key, value)
            except Exception as error:
                unreal.log_warning('Ray %s: %s' % (key, error))
    return len(sites)


# Hubs and the radius kept clear around each (Choir Hollow's canyon and the temple plateau are wide).
HUB_RADII = ((WAKE, 9000), ((-61100, 0), 9000), ((0, 0), 9000), ((-15000, 56000), 16000), ((40000, 44000), 9000),
             ((42000, -50000), 9000), (TEMPLE, 18000), ((-30000, -14000), 9000), ((-36000, -44000), 9000))


# Where the kinds stand (author, 2026-11-08: more variety; enemy placement review). By region, east of the glade first:
# the west (L1) meets Ember Skitters (quick and fragile: block the dash), the middle (L2) adds Aegis Shards (strike
# past the ward), the east (L3) Onyx Wards (circle round them) and Bastions (heavy blows), with a few Bastions in the
# west and the middle as elites she can walk round. Each one replaces a kind 0 enemy, so the count stays the same.

def road_kind(pair, x):
    """The kind of a road pair's second enemy: every third pair's is a kind, by region. The first enemy of a pair
    stays kind 0."""
    if pair % 3:
        return 0
    if x < -20000:
        return 3
    if x < 30000:
        return 2 if pair % 6 == 0 else 3
    return 1 if pair % 12 == 0 else (4 if pair % 6 == 3 else 2)


# The three enemies of a wild pack, by pack number % 4 (n % 4 == 3 is also the pack one level higher).
PACK_KINDS = ((0, 0, 0), (0, 0, 3), (0, 2, 3), (1, 0, 0))


def pack_kinds(n, x):
    """The three kinds of wild pack n at x."""
    if x < -30000 and n % 4 == 2:
        return (0, 0, 3)  # no wards yet in the far west
    if x >= 30000 and n % 4 == 3:
        return (1, 4, 0)  # the east's elites
    if x >= 30000 and n % 4 == 1:
        return (0, 4, 0)
    return PACK_KINDS[n % 4]


def wilderness(p, packs=28):
    """Roaming packs of three in the open country between the regions: off the roads, clear of the hubs and
    puzzles, on gentle ground inside the mountain wall (which starts 820 m out). Levels 1 to 3 rise toward
    the east; every fourth pack is one level higher (up to 4). Some of each pack are kinds (pack_kinds)."""
    hubs = [(WAKE, 9000), ((-61100, 0), 9000), ((0, 0), 9000), ((-15000, 56000), 16000), ((40000, 44000), 9000),
            ((42000, -50000), 9000), (TEMPLE, 18000), ((-30000, -14000), 9000)]
    cands = []
    for gx in range(-78000, 78001, 6000):
        for gy in range(-78000, 78001, 6000):
            h = p.g.at(gx, gy)
            if h < 80 or any(math.hypot(gx - hx, gy - hy) < r for (hx, hy), r in hubs):
                continue
            if any(math.hypot(gx - sx, gy - sy) < 7000 for _, sx, sy in PUZZLE_SITES):
                continue
            rim = [p.g.at(gx + math.cos(b / 4 * math.pi) * 1500, gy + math.sin(b / 4 * math.pi) * 1500) for b in range(8)]
            if max(rim + [h]) - min(rim + [h]) > 600 or min(rim) < 40 or road_gap(gx, gy) < 3000:
                continue
            cands.append((gx, gy))
    picks = []
    while len(picks) < packs and cands:
        far = max(cands, key=lambda c: min(math.hypot(c[0] - q[0], c[1] - q[1]) for q in picks + [WAKE]))
        picks.append(far)
        cands.remove(far)
    for n, (px, py) in enumerate(picks):
        level = 1 if px < -30000 else (2 if px < 30000 else 3)
        if n % 4 == 3:
            level = min(4, level + 1)
        kinds = pack_kinds(n, px)
        for k in range(3):
            a = k / 3 * 2 * math.pi + n
            ex, ey = p.dry(px + math.cos(a) * 1300, py + math.sin(a) * 1300, 60)
            p.foe(kinds[k], level, 'Wild Pack %d %d' % (n, k), ex, ey)
    return picks


GRASS_FIELDS = 34   # patches of cuttable grass beside the roads, besides those where the loose pickups stood
# Where the Center's loose pickups stood until 2026-11-15: place() grows a patch at each (the same places, written
# there beside their regions), and center:grass does from this list.
PICKUP_SITES = (('Glade Crystal 0', -67500, 700), ('Glade Crystal 1', -67300, -600), ('Glade Crystal 2', -68900, 900),
                ('Glade Capsule', -67100, 100), ('Marsh Capsule', -29500, -13700), ('Choir Capsule', -12000, 42000),
                ('Choir Ammo', -12500, 42500), ('Thornveil Capsule', 28000, 29000), ('Highland Capsule', 26500, -30500),
                ('Highland Ammo', 27000, -30500), ('Temple Capsule 0', 74200, -600), ('Temple Capsule 1', 74200, 600))


def grass_fields(p, count=GRASS_FIELDS):
    """Patches of BP_CutGrass along the roads: 6 to 30 m off a road, on dry and fairly level ground, clear of the
    temple and the ground where she wakes, 12 m from anything else the scenario placed (enemies aside: they move),
    spread as far from each other as they will go. It reads the placed actors, so place() calls it last and
    center:grass gives the same patches in a level place() built."""
    placed = []
    for actor in sub().get_all_level_actors():
        if actor.get_actor_label().startswith('Scene ') and str(actor.get_folder_path()) not in ('Center/Enemies', 'Center/Grass'):
            at = actor.get_actor_location()
            placed.append((at.x, at.y))
    cands = []
    for gx in range(-76000, 76001, 2000):
        for gy in range(-76000, 76001, 2000):
            if not 600 <= road_gap(gx, gy) <= 3000 or p.g.at(gx, gy) < 80:
                continue
            if math.hypot(gx - TEMPLE[0], gy - TEMPLE[1]) < 18000 or math.hypot(gx - WAKE[0], gy - WAKE[1]) < 2500:
                continue
            rim = [p.g.at(gx + math.cos(b / 4 * math.pi) * 400, gy + math.sin(b / 4 * math.pi) * 400) for b in range(8)]
            if max(rim) - min(rim) > 220 or min(rim) < 40:
                continue
            if any(abs(gx - ax) < 1200 and abs(gy - ay) < 1200 and math.hypot(gx - ax, gy - ay) < 1200 for ax, ay in placed):
                continue
            cands.append((gx, gy))
    picks = []
    while len(picks) < count and cands:
        far = max(cands, key=lambda c: min(math.hypot(c[0] - q[0], c[1] - q[1]) for q in picks + [WAKE]))
        picks.append(far)
        cands.remove(far)
    for n, (gx, gy) in enumerate(picks):
        p.grass('Roadside %d' % n, gx, gy, 7, 260.0)
    return picks


def grass(ground):
    """center:grass. In the open Center, every loose BP_Pickup goes, a patch of BP_CutGrass grows at each of
    PICKUP_SITES (as place() builds them), and the roadside patches are placed. Run again, it places the same patches."""
    p = Place(ground)
    stood, removed = list(PICKUP_SITES), 0
    for actor in sub().get_all_level_actors():
        name = actor.get_class().get_name()
        if name == 'BP_CutGrass_C' or actor.get_actor_label().startswith('Scene Grass Tag '):
            sub().destroy_actor(actor)
        elif name == 'BP_Pickup_C':
            for kid in actor.get_attached_actors():
                sub().destroy_actor(kid)
            sub().destroy_actor(actor)
            removed += 1
    tufts = sum(len(p.grass(label, x, y)) for label, x, y in stood)
    fields = grass_fields(p)
    # The Logbook's entry for the grass, as place() spawns one for every entry.
    title = GRASS_SCAN[1]
    if not any(actor.get_actor_label() == 'Scene Voice ' + title for actor in sub().get_all_level_actors()):
        p.spawn('BP_LogVoice', 'Voice ' + title, (0, 0, -50000), folder='Voices', Title=title,
                Voice=unreal.load_asset(AUDIO + '/Voice/' + voice_name(title)), Image=unreal.load_asset('/Game/UI/Log/' + image_name(title)))
    from physis_center_tools import save_level
    save_level()
    grown = sum(actor.get_class().get_name() == 'BP_CutGrass_C' for actor in sub().get_all_level_actors())
    return {'pickups_removed': removed, 'pickup_sites': [s[0] for s in stood], 'roadside_patches': len(fields), 'tufts': grown,
            'tufts_at_pickup_sites': tufts}


def sound_scape(p):
    """Region ambience and music: a global night bed, temple drones and creature calls."""
    def ambient(label, sound, place, radius, volume):
        actor = sub().spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(*place))
        actor.set_actor_label('Scene Sound ' + label)
        actor.set_folder_path('Center/Sound')
        comp = actor.get_component_by_class(unreal.AudioComponent)
        comp.set_editor_property('sound', unreal.load_asset(AUDIO + '/' + sound))
        comp.set_editor_property('volume_multiplier', volume)
        if radius:
            comp.set_editor_property('override_attenuation', True)
            settings = comp.get_editor_property('attenuation_overrides')
            settings.set_editor_property('falloff_distance', radius)
            settings.set_editor_property('attenuation_shape_extents', unreal.Vector(radius * .3, 0, 0))
            comp.set_editor_property('attenuation_overrides', settings)
        else:
            comp.set_editor_property('allow_spatialization', False)
        return actor
    ambient('Night', 'S_Center_Ambience', (0, 0, 0), 0, .55)
    ambient('Temple', 'S_Temple_Ambience', (TEMPLE[0], TEMPLE[1], TEMPLE_FLOOR + 800), 9000, .9)
    ambient('Temple Music', 'S_Music_Temple', (TEMPLE[0], TEMPLE[1], TEMPLE_FLOOR + 800), 6000, .6)
    for k, (x, y) in enumerate(((-64000, 6000), (-34000, -40000), (-15000, 56000), (38000, 40000), (-4000, 0))):
        ambient('Creatures %d' % k, 'S_Creature_Loop%d' % (k % 3), p.at(x, y, 300), 6000, .7)
    ambient('Whale Song', 'S_Whale_Loop', (-30000, -30000, 40000), 60000, .8)


# ---------------------------------------------------------------- awakening cinematic

FACE_SKELETON = '/Game/MetaHumans/Common/Face/Face_Archetype_Skeleton'
CINE = CENTER + '/Cinema'


def eye_clip(rebuild=False):
    """A face clip that holds the eyes shut, flutters, then snaps them open on the breath.

    MetaHuman faces are driven by CTRL_expressions curves (RigLogic in the face post-process
    Animation Blueprint), so a curve-only clip on the face skeleton is enough.
    """
    path = CINE + '/A_Physis_EyesOpen'
    library = unreal.EditorAssetLibrary
    # BP_Awakening holds a reference to this clip: recreating it empties that reference, so keep it
    # unless asked (then rerun center_logic.py actors).
    if library.does_asset_exist(path) and not rebuild:
        return unreal.load_asset(path)
    if library.does_asset_exist(path):
        library.delete_asset(path)
    factory = unreal.AnimSequenceFactory()
    factory.set_editor_property('target_skeleton', unreal.load_asset(FACE_SKELETON))
    clip = unreal.AssetToolsHelpers.get_asset_tools().create_asset('A_Physis_EyesOpen', CINE, unreal.AnimSequence, factory)
    controller = clip.controller
    controller.open_bracket('Eyes', True)
    controller.set_frame_rate(unreal.FrameRate(30, 1), True)
    controller.set_number_of_frames(unreal.FrameNumber(30 * 14), True)
    # A curve-only clip is rejected by the single-node player, so give it a still root track.
    skeleton = unreal.load_asset(FACE_SKELETON)
    root = str(skeleton.get_editor_property('bone_tree')[0].get_editor_property('name')) if hasattr(skeleton, 'bone_tree') else 'root'
    controller.add_bone_curve(root, True) if hasattr(controller, 'add_bone_curve') else controller.add_bone_track(root, True)
    count = 30 * 14 + 1
    controller.set_bone_track_keys(root, [unreal.Vector(0, 0, 0)] * count, [unreal.Quat(0, 0, 0, 1)] * count, [unreal.Vector(1, 1, 1)] * count, True)
    controller.close_bracket(True)
    # Shut, a flutter at 3 s, open by 4.6 s with a startled widening on the breath, then calm.
    # Shut; a flutter at 2.4 s; the lids part slowly from 3.0 s so the pupil is seen opening, wide by 4.1 s.
    keys = {'CTRL_expressions_eyeBlinkL': ((0, 1), (2.4, 1), (2.55, .7), (2.75, 1), (3.0, 1), (3.5, .55), (4.1, 0), (9.0, 0), (9.1, 1), (9.25, 0), (14, 0)),
            'CTRL_expressions_eyeBlinkR': ((0, 1), (2.42, 1), (2.57, .72), (2.77, 1), (3.0, 1), (3.5, .55), (4.12, 0), (9.0, 0), (9.1, 1), (9.25, 0), (14, 0)),
            'CTRL_expressions_eyeWidenL': ((0, 0), (4.6, 0), (4.8, .7), (6.5, .1), (14, 0)),
            'CTRL_expressions_eyeWidenR': ((0, 0), (4.6, 0), (4.8, .7), (6.5, .1), (14, 0)),
            'CTRL_expressions_jawOpen': ((0, 0), (4.5, 0), (4.7, .3), (5.8, .04), (14, 0)),
            'CTRL_expressions_mouthLipsPartUL': ((0, 0), (4.5, .1), (4.7, .6), (6.0, .2), (14, .1)),
            'CTRL_expressions_mouthLipsPartDL': ((0, 0), (4.5, .1), (4.7, .6), (6.0, .2), (14, .1)),
            'CTRL_expressions_browRaiseInL': ((0, 0), (4.6, 0), (4.8, .6), (7.0, .1), (14, 0)),
            'CTRL_expressions_browRaiseInR': ((0, 0), (4.6, 0), (4.8, .6), (7.0, .1), (14, 0))}
    lib = unreal.AnimationLibrary
    for name, points in keys.items():
        lib.add_curve(clip, name, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
        lib.add_float_curve_keys(clip, name, [float(t) for t, _ in points], [float(v) for _, v in points])
    game.save(clip)
    return clip


# The cine Physis lies with her feet toward the Still Tree's clearing and rises facing north-east,
# where the roads lead. Camera keys: time, camera position and look-at target as offsets from WAKE
# at ground height, focal length.
FACING = -90.0  # the stand-in's turn: she stands facing +X (north) like the player; since 2026-11-06 she also lies head north
LIE_HEAD = (3, 36, 22)  # where her head lies, WAKE-relative (head south before 2026-11-06: (-150, 0, 22))
# Her left eye while she lies, measured in play (WAKE-relative, after the turn): the first shot
# looks straight down into it from the chin side, so the lids lift to reveal the pupil.
EYE = (-153.2, 0.4, 45.6)
SHOTS = (
    (0.0, (-147.5, -.5, 61), EYE, 95),
    (4.45, (-147.0, -.5, 63), EYE, 92),
    (4.5, (-95, 150, 125), (-150, 0, 40), 35),
    (5.4, (-100, 160, 135), (-150, 0, 40), 34),
    (5.6, (-420, 260, 230), (-100, 0, 20), 32),
    (9.8, (-470, 160, 300), (-80, 0, 30), 30),
    (10.0, (40, -500, 85), (-40, 0, 55), 24),
    (15.9, (110, -450, 150), (0, 0, 115), 24),
    (16.1, (-330, -70, 200), (900, 160, 140), 30),
    (19.5, (-420, 160, 210), (1600, 300, 260), 26),
    (26.0, (-1800, 1400, 1700), (4000, -600, 300), 18),
    (32.0, (-3600, 3000, 3600), (8000, -1000, 900), 16),
    (32.2, (-330, 90, 185), (1200, 0, 160), 24),
    (36.0, (-300, 0, 190), (1200, 0, 160), 24),
)


# Since 2026-11-06 she lies head north and rolls over to get up (Tools/build_physis_getup.py, LIE_PLACE): the lying shots
# (before 10 s) turn 180 degrees about the point her lying pose turned about, WAKE-relative, so they frame her as before.
LIE_TURN = (-73.5, 18.0)


def lie_turn(p):
    return (2 * LIE_TURN[0] - p[0], 2 * LIE_TURN[1] - p[1], p[2])


def cinema(ground):
    sub_ = sub()
    for actor in sub_.get_all_level_actors():
        if actor.get_actor_label().startswith('Cine '):
            sub_.destroy_actor(actor)
    wx, wy = WAKE
    # The stand-in plays A_Physis_GetUp (Tools/build_physis_getup.py) on her body and the eye clip on
    # her face; BP_Awakening starts both when the sequence starts.
    floor = max(ground.at(wx, wy), 0)
    eye_clip(rebuild=True)
    # Physis herself: the MetaHuman Blueprint, posed and animated at run time by BP_Awakening,
    # which removes her (tag CineOnly) when the player takes over at the same spot.
    source = unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
    physis = sub_.spawn_actor_from_class(source.generated_class(), unreal.Vector(wx, wy, floor + 2), unreal.Rotator(0, 0, FACING))
    physis.set_actor_label('Cine Physis')
    physis.set_folder_path('Center/Cinema')
    physis.tags = ['CineOnly']
    camera = sub_.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(wx, wy, floor + 200))
    camera.set_actor_label('Cine Camera')
    camera.set_folder_path('Center/Cinema')
    lens_part = camera.get_cine_camera_component()
    lens_part.set_editor_property('constrain_aspect_ratio', False)
    # Everything in focus: the eye close-up is only a hand's width from the lens.
    focus = lens_part.get_editor_property('focus_settings')
    focus.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
    lens_part.set_editor_property('focus_settings', focus)
    path = CINE + '/SEQ_Awakening'
    library = unreal.EditorAssetLibrary
    if library.does_asset_exist(path):
        library.delete_asset(path)
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset('SEQ_Awakening', CINE, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_playback_start_seconds(0)
    sequence.set_playback_end_seconds(36)
    def frame(seconds):
        # Scripted channel keys are in display-rate frames (add_key's default time unit).
        return unreal.FrameNumber(int(round(seconds * 30)))
    cam = sequence.add_possessable(camera)
    transform = cam.add_track(unreal.MovieScene3DTransformTrack).add_section()
    transform.set_range_seconds(0, 36)
    channels = transform.get_all_channels()
    lens = sequence.add_possessable(camera.get_cine_camera_component())
    lens.set_parent(cam)
    focal = lens.add_track(unreal.MovieSceneFloatTrack)
    focal.set_property_name_and_path('CurrentFocalLength', 'CurrentFocalLength')
    fsec = focal.add_section()
    fsec.set_range_seconds(0, 36)
    fch = fsec.get_all_channels()[0]
    for when, eye, look, length in SHOTS:
        if when < 10.0:
            eye, look = lie_turn(eye), lie_turn(look)
        ex, ey, ez = wx + eye[0], wy + eye[1], floor + eye[2]
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(ex, ey, ez), unreal.Vector(wx + look[0], wy + look[1], floor + look[2]))
        for channel, value in zip(channels[:6], (ex, ey, ez, 0.0, rot.pitch, rot.yaw)):
            channel.add_key(frame(when), value)
        fch.add_key(frame(when), float(length))
    glow = sub_.spawn_actor_from_class(unreal.PointLight, unreal.Vector(wx - 80, wy, floor + 120))
    glow.set_actor_label('Cine Rise Light')
    glow.set_folder_path('Center/Cinema')
    gl = glow.get_component_by_class(unreal.PointLightComponent)
    gl.set_light_color(unreal.LinearColor(.55, .9, 1, 1))
    gl.set_editor_property('attenuation_radius', 1400.0)
    gl.set_editor_property('intensity', 0.0)
    gl.set_cast_shadows(False)
    gl.set_mobility(unreal.ComponentMobility.MOVABLE)
    light = sequence.add_possessable(gl)
    light.set_parent(sequence.add_possessable(glow))
    power = light.add_track(unreal.MovieSceneFloatTrack)
    power.set_property_name_and_path('Intensity', 'Intensity')
    psec = power.add_section()
    psec.set_range_seconds(0, 36)
    pc = psec.get_all_channels()[0]
    for when, value in ((0, 0), (4.5, 0), (4.7, 2500), (6.5, 800), (10.0, 1200), (11.5, 3500), (14.5, 6000), (16.5, 1200), (19, 0), (36, 0)):
        pc.add_key(frame(when), float(value))
    cuts = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cuts.set_range_seconds(0, 36)
    cuts.set_camera_binding_id(sequence.get_binding_id(cam))
    audio = sequence.add_track(unreal.MovieSceneAudioTrack)
    for sound, start, end in (('S_Awaken_Heart', .3, 3.3), ('S_Awaken_Heart', 2.6, 5.6), ('S_Awaken_Gasp', 4.3, 12.2), ('S_Music_Awakening', 0, 36),
                              ('Voice/S_VO_Awakening', 21.0, 33.0)):
        section = audio.add_section()
        section.set_range_seconds(start, end)
        section.set_sound(unreal.load_asset(AUDIO + '/' + sound))
    fade = sequence.add_track(unreal.MovieSceneFadeTrack).add_section()
    fade.set_range_seconds(0, 36)
    fc = fade.get_all_channels()[0]
    # Black, the eyelids lift and fall twice, open on the breath; a blink at 9 s; a fade at the end.
    for when, value in ((0, 1), (.4, 1), (1.6, 0), (35.2, 0), (36, .6)):
        fc.add_key(frame(when), float(value))
    game.save(sequence)
    player = sub_.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(wx, wy, floor))
    player.set_actor_label('Cine Player')
    player.set_folder_path('Center/Cinema')
    player.set_sequence(sequence)
    from physis_center_tools import save_level
    save_level()
    comps = [c.get_name() for c in physis.get_components_by_class(unreal.SkeletalMeshComponent)]
    return {'sequence': path, 'physis_parts': comps}
