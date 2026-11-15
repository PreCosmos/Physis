"""Gameplay for level 3, the Conclave: Still Points, the people, the three Spine Pylons, the Spire's Trial of
Light, the Spindle Docks and the Shepherd, side requests, optional puzzles, Light Caches, sealed vaults, the AL
by region, Divinity Rays, tutorials and sound. Run through `outfit_operation conclave:scenario` (place) and
`conclave:portal` (portal: the Center's temple current, a targeted spawn that leaves the Center scenario alone).
Tools/conclave/sim_scenario.py runs both offline against a recording stub of `unreal` and checks the token graph.

Positions are plan metres (physis_conclave_plan: x north along the drum, y east) turned into centimetres here;
Place's methods take centimetres, like the Center's. Text comes from physis_conclave_lore; the few lines the
scenario authors itself (Still Point goals, puzzle clues) are looked up in MESSAGES first, so the lore can
take them over by key (see text()).

Progress tokens (BP_Physis Flags; Tools/conclave/README.md "Gameplay"):
  ,conclave, ,at_conclave,  arrived / saves load here     ,kairos,  Kairos met
  ,sluice1-3,  the Terraces' sluices (BP_Switch Seq 1-3)   ,pylon1,  the Terrace Pylon
  ,anchors,    the three buoy anchors shot                 ,pylon2,  the Reservoir Pylon
  ,bridge,     the crane's three cable locks cut           ,pylon3,  the Foundry Pylon
  ,spire,      all three pylons lit: the Spire unseals     ,lightstep,  Iriel teaches Light Step
  ,crown,      the Spire's crown (given with ,aug_hp5,)    ,docksgate,  the docks' lattice wall
  ,shepherd,   the AL Shepherd falls                       ,conclave_done,  Kairos afterwards
  side requests ,orsolya, ,seedpod, ,petra, ,page1-3, ,pages, ,tamsin, ,kite, ,halden, ,core, ,wisp,
  puzzles, caches, vaults and optional fights ,cn_*,  (furnace floors ,cn_floorN, are closed by Settle)
Encounter rooms 301-399, each once; loose packs are room 0. Tags for BP_ConclaveDirector: PylonBeam1-3 (hidden
in game until ,pylonN,). Markers for BP_Physis travel: TargetPoint tags ConclaveArrival (here) and ConclaveReturn
(in the Center, by portal()).
"""
import ast
import contextlib
import json
import math
import pathlib
import struct
import sys

import unreal

import physis_conclave_plan as plan
import physis_gameplay_tools as game
from physis_aaa_tools import wrap_text
from physis_conclave_lore import (ARRIVAL_LINE, CONCLAVE_ENEMIES, CONCLAVE_GATES, CONCLAVE_SCANS, CONCLAVE_TUTORIALS, GRASS_ENTRY, MESSAGES,
                                  PEOPLE, QUEST_KAIROS, WISP_GIFT, conclave_entries, conversation_pages, person_key)
from physis_lore import image_name, voice_name

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
MESH_TOOLS = ROOT / 'Tools/conclave_meshes'
if str(MESH_TOOLS) not in sys.path:
    # palette.py is plain Python (the colour rule); people.py (CAST) needs numpy, which only the offline harness has.
    sys.path.append(str(MESH_TOOLS))
import palette  # noqa: E402

CONCLAVE = '/Game/Conclave'
MESHES = CONCLAVE + '/Meshes'
MATS = CONCLAVE + '/Materials'
AUDIO = CONCLAVE + '/Audio'
VOICES = AUDIO + '/Voice'
LEVEL = '/Game/Levels/L_Conclave'
CENTER_LEVEL = '/Game/Levels/L_CenterOfTheUniverse'
SKELETAL = '/Game/Characters/Mannequins/Meshes/SKM_%s_Simple'
IDLE = '/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle'
M = 100.0
WALK = (plan.WALK_Y - 5.0) * M     # nothing stands past 295 m: the slope beyond runs into the parapet and the berm
AXIS = plan.AXIS_Z * M
VOICE_SPOT = (0.0, 0.0, -50000.0)  # voice actors are data: out of sight under the floor, as in the Center
KEEP = unreal.AttachmentRule.KEEP_WORLD

# Light colours: the palette's lights (linear RGB), so no light tints the level out of its five colours.
GOLD = palette.LIGHT_GOLD[:3]
BLUE = palette.LIGHT_BLUE[:3]
RED = palette.LIGHT_RED[:3]
WARM = palette.LIGHT_WARM[:3]

# The Center's temple (physis_center_scenario TEMPLE and TEMPLE_FLOOR + 600, cm): the current home opens 8 m north
# of the Heartbloom pedestal, and Physis comes back 4 m short of it, outside its 1.8 m travel radius.
TEMPLE = (76000.0, 0.0)
STILL_UNTIL = ',shepherd,'  # Conclave Still Points stop setting objectives once the Shepherd has fallen
SANCTUM = 3400.0 + 600.0
# The Heartbloom pedestal's Done text, identical to physis_center_scenario.py's (agreed with the Center session, 2026-11-06).
HEARTBLOOM_DONE = ("The Heartbloom opens in Physis's hands, and she understands how a wound is closed.~Mend learned: Z / |DL|.  "
                   "Heals 6 health for 25 Divinity.~A Divinity current has opened in the sanctum.~Step into it to follow it to "
                   "the Conclave, or explore the Center first.")
# On the sanctum's ring floor, 16 m north of the pedestal: the first place (8 m out) put the north crystal of the six
# (r 7-7.5 m, every 60 degrees) inside the current, and walking in from the pedestal she stopped 2.06 m from its
# centre, outside its 1.8 m reach (Center session's Play test, 2026-11-07). The return spot is 5 m short of it.
PORTAL = (TEMPLE[0] + 1600.0, TEMPLE[1], SANCTUM + 35.0)
RETURN = (TEMPLE[0] + 1100.0, TEMPLE[1], SANCTUM + 120.0)

LAST = None  # the last Place, for the offline harness (Tools/conclave/sim_scenario.py)
MISSING = set()


def cm(x, y):
    return x * M, y * M


def text(key, default):
    """A line the scenario says: MESSAGES[key] once the lore holds it, else the default written here."""
    return MESSAGES.get(key, default)


def wrap(message):
    """HUD lines: every '~'-separated part wrapped at 62 characters, so authored breaks stay where they are and
    wrapping twice changes nothing (wrap_text alone counts across a '~' and breaks short lines again)."""
    return '~'.join(wrap_text(part) for part in message.split('~')) if message else message


WRAPPED = ('Message', 'Done', 'Denied', 'Objective', 'ScanText', 'NextGoal', 'Note', 'Quest', 'Locked')


def props(actor, **values):
    for key, value in values.items():
        actor.set_editor_property(key, wrap(value) if key in WRAPPED and isinstance(value, str) else value)


def asset(path, optional=False):
    """The asset at path, or None when it is not imported yet (listed in MISSING unless optional)."""
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    if not optional:
        MISSING.add(path)
    return None


def mesh_asset(name):
    return asset(MESHES + '/' + name)


def cls(name):
    blueprint = asset(game.BLUEPRINTS + '/' + name)
    if blueprint is None:
        raise RuntimeError('%s is missing: run conclave:blueprints and Tools/blueprint_logic/conclave_logic.py first' % name)
    return blueprint.generated_class()


def sub():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


# ---------------------------------------------------------------- the height grid and the town

class Ground:
    """Art/Meshes/Conclave/height.bin from Tools/build_physis_conclave.py: metres, float32, index i * ny + j (i along x)."""

    def __init__(self, base=None):
        base = pathlib.Path(base) if base else ROOT / 'Art/Meshes/Conclave'
        meta = json.loads((base / 'height.json').read_text())
        self.half_x, self.half_y, self.cell = meta['half_x'], meta['half_y'], meta['cell']
        self.nx, self.ny = meta['nx'], meta['ny']
        self.water = meta.get('water', 0.0)
        self.h = struct.unpack('<%df' % (self.nx * self.ny), (base / 'height.bin').read_bytes())

    def at(self, x, y):
        """Ground height in cm at Unreal (x, y) in cm (the lake bed under water)."""
        fx, fy = (x / M + self.half_x) / self.cell, (y / M + self.half_y) / self.cell
        i, j = max(0, min(int(math.floor(fx)), self.nx - 2)), max(0, min(int(math.floor(fy)), self.ny - 2))
        u, v = max(0.0, min(1.0, fx - i)), max(0.0, min(1.0, fy - j))
        h, n = self.h, self.ny
        return (h[i * n + j] * (1 - u) * (1 - v) + h[(i + 1) * n + j] * u * (1 - v) + h[i * n + j + 1] * (1 - u) * v
                + h[(i + 1) * n + j + 1] * u * v) * M


# Footprints (x by y, metres) of what the generator's scatter.json stands up, which gameplay must not stand on
# (Tools/conclave/README.md sizes; trees by their trunks and lower boughs).
FOOTPRINT = {'SM_CN_House0': (7, 9), 'SM_CN_House1': (6, 6), 'SM_CN_House2': (8, 12), 'SM_CN_House3': (8, 8),
             'SM_CN_Ruin0': (7, 9), 'SM_CN_Ruin1': (6, 6), 'SM_CN_Stall': (3, 4), 'SM_CN_TerraceWall': (.6, 12),
             'SM_CN_Stairs': (4.5, 3), 'SM_CN_Bench': (.6, 2), 'SM_CN_Planter': (1, 2), 'SM_CN_Lamp': (.8, .8),
             'SM_CN_Banner': (.8, .8), 'SM_CV_TreeWhite': (2.5, 2.5), 'SM_CV_TreeRed': (2.5, 2.5),
             'SM_CV_TreeBlack': (2.5, 2.5), 'SM_CV_FruitTree': (2, 2), 'SM_CV_Hedge': (1, 2), 'SM_CV_Shrub': (1.2, 1.2),
             'SM_CV_RockWhite': (3, 3), 'SM_CV_RockBlack': (3, 3)}
CELL = 2000.0  # bucket size (cm) for footprint lookups


def town(path=None):
    """(footprints, scatter rows) from scatter.json: footprints are (x, y, half x, half y, yaw radians) in cm."""
    path = pathlib.Path(path) if path else ROOT / 'Art/Meshes/Conclave/scatter.json'
    if not path.exists():
        return [], {}
    data = json.loads(path.read_text())
    rows = []
    for mesh, items in data.items():
        size = FOOTPRINT.get(mesh) or next((v for k, v in FOOTPRINT.items() if mesh.startswith(k)), None)  # numbered variants
        if not size:
            continue
        for x, y, z, pitch, yaw, roll, s in items:
            rows.append((x, y, size[0] * 50 * s, size[1] * 50 * s, math.radians(yaw)))
    return rows, data


def gap(x, y, row):
    """Distance in cm from (x, y) to an oriented footprint."""
    cx, cy, hx, hy, yaw = row
    dx, dy = x - cx, y - cy
    c, s = math.cos(yaw), math.sin(yaw)
    u, v = dx * c + dy * s, -dx * s + dy * c
    return math.hypot(max(abs(u) - hx, 0.0), max(abs(v) - hy, 0.0))


# ---------------------------------------------------------------- placing

class Place:
    def __init__(self, ground, footprints=(), scatter=None):
        self.g = ground
        self.count = 0
        self.log = []      # (actor, needs, wet) for every spawn: the offline harness solves the token graph from it
        self.needs = ()    # tokens Physis must hold to reach what is being placed (the gates around it)
        self.wet = False   # placing what belongs in the lake: buoys, the island, piers
        self.solids = []   # (x, y, radius) cm: set pieces that packs, pickups and courts keep clear of
        self.stills = []   # Still Points (x, y) cm: no enemy within 30 m, where she returns after a fall
        self.scatter = scatter or {}
        self.town = {}
        for row in footprints:
            self.town.setdefault((int(row[0] // CELL), int(row[1] // CELL)), []).append(row)
        self.sites = []    # (title, x, y, kind, token): a Divinity Ray over each (0 puzzle, 1 vault, 2 Light Cache)
        self.marks = {}    # named places (cm) for the summary: Still Points, pylons, the current, the arrival
        self.scans = {}    # lore scan title -> (x, y, z) cm where its tag stands instead of the lore's point
        self.scan_zones = {}
        self.spots = {key: (x * M, y * M, yaw, None) for key, (x, y, yaw) in SPOTS.items()}
        self.zones = {}    # person key -> gate tokens around the spot
        self.moved = {}    # tutorial name -> place (cm), for tutorials that belong on a piece built here
        self.ring_panels = {}
        self.unset = []    # (label, property) a Blueprint lacked: reported in 'unset', never skipped silently

    @contextlib.contextmanager
    def behind(self, *tokens):
        saved = self.needs
        self.needs = tuple(sorted(set(saved) | {t for t in tokens if t}))
        try:
            yield
        finally:
            self.needs = saved

    @contextlib.contextmanager
    def water(self):
        saved, self.wet = self.wet, True
        try:
            yield
        finally:
            self.wet = saved

    def note(self, actor):
        self.log.append((actor, self.needs, self.wet))
        self.count += 1
        return actor

    # -- primitives (cm) ---------------------------------------------------------------
    def spawn(self, name, label, place, scale=None, folder='Scenario', **values):
        actor = sub().spawn_actor_from_class(cls(name), unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path('Conclave/' + folder)
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))
        if values:
            props(actor, **values)
        return self.note(actor)

    def mesh(self, label, mesh, place, rot=(0, 0, 0), scale=1.0, folder='Scenario', collide=True, solid=0.0, shadow=True):
        actor = sub().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place), unreal.Rotator(*rot))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path('Conclave/' + folder)
        part = actor.static_mesh_component
        part.set_static_mesh(mesh_asset(mesh))
        part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
        if not shadow:
            part.set_editor_property('cast_shadow', False)
        scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        actor.set_actor_scale3d(unreal.Vector(*scale))
        if solid:
            self.solids.append((place[0], place[1], solid))
        return self.note(actor)

    def landmark(self, label, mesh, place, yaw=0.0, scale=1.0, solid=0.0, folder='Landmarks', collide=True):
        """A set piece the scenario stands up, unless the generator's scatter.json already has it (the level build
        then places it), so the two never double one."""
        if mesh in self.scatter:
            if solid:
                self.solids.append((place[0], place[1], solid))
            return None
        return self.mesh(label, mesh, place, (0, 0, yaw), scale, folder, collide, solid)

    def light(self, label, place, colour, intensity, radius, folder='Lights'):
        actor = sub().spawn_actor_from_class(unreal.PointLight, unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path('Conclave/' + folder)
        comp = actor.get_component_by_class(unreal.PointLightComponent)
        comp.set_light_color(unreal.LinearColor(colour[0], colour[1], colour[2], 1))
        comp.set_editor_property('intensity', float(intensity))
        comp.set_editor_property('attenuation_radius', float(radius))
        comp.set_cast_shadows(False)
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        return self.note(actor)

    def marker(self, label, place, tag, folder):
        actor = sub().spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path('Conclave/' + folder)
        actor.set_editor_property('tags', [tag])
        return self.note(actor)

    def at(self, x, y, lift=0.0):
        return (x, y, max(self.g.at(x, y), 0.0) + lift)

    def low(self, x, y, points, spread):
        """The lowest ground under a set of offsets (u, v) in cm along the unit vectors spread = (fx, fy, sx, sy)."""
        fx, fy, sx, sy = spread
        return min(self.g.at(x + fx * u + sx * v, y + fy * u + sy * v) for u, v in points)

    def ok(self, x, y, clear, still, dry):
        if abs(y) > WALK:
            return False
        if dry and plan.in_lake(x / M, y / M, 3.0):
            return False
        if any(math.hypot(x - sx, y - sy) < r + clear for sx, sy, r in self.solids):
            return False
        if still and any(math.hypot(x - sx, y - sy) < still for sx, sy in self.stills):
            return False
        reach = int((clear + 1200) // CELL) + 1
        ix, iy = int(x // CELL), int(y // CELL)
        for i in range(ix - reach, ix + reach + 1):
            for j in range(iy - reach, iy + reach + 1):
                if any(gap(x, y, row) < clear for row in self.town.get((i, j), ())):
                    return False
        return True

    def free(self, x, y, clear=300.0, still=0.0, dry=True, reach=6000):
        """The nearest spot to (x, y) on the walkable floor (|y| <= 295 m), out of the lake when dry, `clear` cm from
        every set piece and scatter footprint and `still` cm from every Still Point: rings 1.5 m apart outward."""
        if self.ok(x, y, clear, still, dry):
            return x, y
        for r in range(150, reach + 1, 150):
            n = max(8, int(2 * math.pi * r / 150))
            for k in range(n):
                a = (k + .5 * ((r // 150) % 2)) / n * 2 * math.pi
                px, py = x + math.cos(a) * r, y + math.sin(a) * r
                if self.ok(px, py, clear, still, dry):
                    return px, py
        unreal.log_warning('Conclave scenario: no free spot near (%d, %d)' % (x, y))
        return x, y

    def reskin(self, actor, mesh, material=None):
        """A shared actor dressed in the palette: its first mesh part becomes `mesh`, the others go. BP_TrainingDrone's
        'Ward' (the Center's front plate, added by center:drone_ward on 2026-11-08; meshless unless the Center gives
        one) is never taken for the body, whatever the component order, and is left as it is."""
        parts = [part for part in actor.get_components_by_class(unreal.StaticMeshComponent)
                 if part.get_name().split('_GEN')[0] != 'Ward']
        for index, part in enumerate(parts):
            if index == 0:
                if mesh:
                    part.set_static_mesh(mesh_asset(mesh))
                if material:
                    part.set_material(0, material)
            else:
                part.set_visibility(False)
                part.set_collision_profile_name('NoCollision')
        return parts[0] if parts else None

    # -- gameplay pieces ---------------------------------------------------------------
    def check(self, label, x, y, objective, radius=700.0):
        place = self.at(x, y, 110)
        actor = self.spawn('BP_Checkpoint', 'Still Point ' + label, place, folder='Still Points', Radius=radius, Objective=objective)
        # Until (BP_Checkpoint, center_overrides.py still_points(), from 2026-11-07): a first visit skips its objective once
        # the flags hold it. After the Shepherd falls, a Still Point found late must not overwrite "Return to Kairos" or
        # the closing quest. Older BP_Checkpoints have no Until, so it is set only where the variable exists.
        try:
            actor.set_editor_property('Until', STILL_UNTIL)
        except Exception:
            pass
        self.mesh('Still Point Ring ' + label, 'SM_CN_StillPoint', self.at(x, y, -5), (0, 0, 0), 1.0, 'Still Points')
        self.light('Still Point Glow ' + label, self.at(x, y, 300), BLUE, 2400, 900, 'Still Points')
        self.stills.append((x, y))
        self.marks['Still Point ' + label] = place
        return actor

    def scan(self, category, title, body, place, important, folder='Scans'):
        x, y, z = place
        z = (max(self.g.at(x, y), 0.0) + 150) if z is None else z
        tag = self.spawn('BP_ScanTarget', 'Story ' + title, (x, y, z), folder=folder, ScanText=body, ScanCategory=category,
                         ScanTitle=title, ScanImportant=important)
        game.hide_scan(tag)
        return tag

    def tag(self, actor, entry, place, label, folder='Enemies'):
        """A scan tag riding on an enemy or target, set up before it is attached (a property change re-runs the
        tag's construction script, which can drop an attachment)."""
        category, title, body = entry
        tag = self.spawn('BP_ScanTarget', 'Tag ' + label, (place[0], place[1], place[2] + 70), folder=folder, ScanCategory=category,
                         ScanTitle=title, ScanText=body, ScanImportant=True)
        game.hide_scan(tag)
        tag.attach_to_actor(actor, 'None', KEEP, KEEP, KEEP, False)
        return tag

    def switch(self, label, place, yaw=0.0, mesh=None, solid=False, scale=None, folder='Switches', **values):
        """BP_Switch: Interact within 260 cm of its origin. Every Conclave switch wears a palette prop; `solid` gives
        that prop collision (only props narrow enough to stand within reach of their origin)."""
        actor = self.spawn('BP_Switch', label, place, None, folder, **values)
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = self.reskin(actor, mesh)
        if part:
            part.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))
        return actor

    def relic(self, label, place, token, message, need='', divinity=0.0, heal=False, mesh='SM_CN_LightCache', scale=1.0,
              tease=False, locked='', folder='Items'):
        """BP_Relic: walked into (170 cm from her centre, so 1.1-1.3 m above the floor) it gives `token` (one or more)."""
        actor = self.spawn('BP_Relic', label, place, None, folder, Token=token, Need=need, Message=message, Divinity=float(divinity), Heal=heal)
        if tease:
            props(actor, Tease=True, Locked=locked)
        self.reskin(actor, mesh)
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        return actor

    def barrier(self, label, x, y, yaw, give='', width=1.0, height=1.0, folder='Barricades'):
        """BP_SettleBarrier as an AL barricade (SM_CN_Barricade, 8 m along its local Y): rolled so its sheet follows
        the ground from end to end and sunk 40 cm, so no gap opens under it on the drum's slopes."""
        a = math.radians(yaw)
        ux, uy = -math.sin(a), math.cos(a)
        half = 400.0 * width
        za, zb, zc = self.g.at(x - ux * half, y - uy * half), self.g.at(x + ux * half, y + uy * half), self.g.at(x, y)
        roll = -math.degrees(math.atan2(zb - za, 2 * half))
        actor = self.spawn('BP_SettleBarrier', 'Barricade ' + label, (x, y, min(zc, (za + zb) / 2) - 40), None, folder, Give=give)
        actor.set_actor_rotation(unreal.Rotator(roll, 0, yaw), False)
        self.reskin(actor, 'SM_CN_Barricade')
        if width != 1.0 or height != 1.0:
            actor.set_actor_scale3d(unreal.Vector(1, width, height))
        return actor

    def lattice(self, label, place, yaw, hold=0.0, give='', radius=900.0, message='', ability=',lightstep,', mesh='SM_CN_Lattice',
                scale=None, folder='Lattices'):
        """BP_AbilitySocket as a solid gate: Light Step (or a later ability) used within `radius` opens it, for good
        when hold is 0, else for `hold` seconds. It reports itself in the token graph by `ability`."""
        actor = self.spawn('BP_AbilitySocket', label, place, scale, folder, Ability=ability, Give=give, Radius=radius, Hold=hold,
                           Solid=True, Message=message)
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = self.reskin(actor, mesh)
        if part:
            part.set_collision_profile_name('BlockAll')
        return actor

    def rise(self, label, mesh, start, need, lift, rot=(0, 0, 0), scale=1.0, speed=150.0, folder='Scenario'):
        """BP_Rise standing at `start` until `need` is held, then sliding `lift` cm (negative sinks it)."""
        actor = self.spawn('BP_Rise', label, start, None, folder, Need=need, Lift=float(lift), Speed=float(speed))
        actor.set_actor_rotation(unreal.Rotator(*rot), False)
        self.reskin(actor, mesh)
        scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        actor.set_actor_scale3d(unreal.Vector(*scale))
        return actor

    def enemy(self, level, label, x, y, room=0, z=None):
        """An AL of CONCLAVE_ENEMIES[level] with its Logbook tag. On the floor it is kept 30 m from Still Points and
        clear of set pieces; z (a platform top, cm) puts it over a piece built in the air instead."""
        mesh, health, scale, hover, entry = CONCLAVE_ENEMIES[level]
        if z is None:
            x, y = self.free(x, y, 400.0, 3000.0, not self.wet)
            base = max(self.g.at(x, y), 0.0)
        else:
            base = z
        place = (x, y, base + hover)
        actor = self.spawn('BP_TrainingDrone', 'Enemy L%d %s' % (level, label), place, (scale, scale, scale), 'Enemies',
                           RoomId=room, Boss=False, Health=health)
        actor.set_editor_property('Static', False)
        self.reskin(actor, mesh)
        self.tag(actor, entry, place, label)
        return actor

    def target(self, label, mesh, place, room, health, scale=1.0, entry=None, yaw=0.0, folder='Targets', shot_only=False):
        """A Static BP_TrainingDrone: a lock to break (blade or sidearm), counted by its room's encounter. shot_only: the
        sidearm alone breaks it (BP_TrainingDrone.ShotOnly, which PhysisStrikeNow skips; Center session, 2026-11-08)."""
        actor = self.spawn('BP_TrainingDrone', 'Target ' + label, place, (scale, scale, scale), folder, RoomId=room, Boss=False, Health=health)
        actor.set_editor_property('Static', True)
        if shot_only:
            try:
                actor.set_editor_property('ShotOnly', True)
            except Exception:
                self.unset.append((label, 'ShotOnly'))
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        self.reskin(actor, mesh)
        if entry:
            self.tag(actor, entry, place, label, folder)
        return actor

    # Where the tufts of one clump of goldgrass stand round its centre (cm).
    GRASS = ((0, 0), (95, 30), (-70, 80), (40, -100), (-105, -45))

    def pickup(self, kind, label, x, y, lift=120.0, z=None):
        """No loose pickups lie in the Conclave (author, 2026-11-15): a clump of goldgrass grows where each one lay
        (grass()). `kind` and `lift` are kept so the call sites read as before; what a tuft drops is random."""
        return self.grass(label, x, y, z)

    def grass(self, label, x, y, z=None):
        """A clump of BP_CutGrass tufts (SM_CV_Wheat in MI_CN_CutGrass). Her blade cuts a tuft within 2.6 m in front of
        her (BP_Physis.PhysisStrikeNow calls GrassCut); half the time, and always while she is short of Divinity or
        health, it drops a pickup of a random kind (40% health, 35% Divinity, 25% ammo) that lasts 3 minutes, and the
        tuft grows back after 2 minutes. On a piece built in the air (z, its top) the clump is three tufts drawn in.
        The first tuft of a clump carries the Logbook tag (GRASS_ENTRY), so the grass can be scanned."""
        if z is None:
            x, y = self.free(x, y, 150.0, 0.0, not self.wet)
        spots = self.GRASS if z is None else [(dx * .45, dy * .45) for dx, dy in self.GRASS[:3]]
        first = None
        for k, (dx, dy) in enumerate(spots):
            base = max(self.g.at(x + dx, y + dy), 0.0) if z is None else z
            actor = self.spawn('BP_CutGrass', '%s Grass %d' % (label, k), (x + dx, y + dy, base), None, 'Grass')
            actor.set_actor_rotation(unreal.Rotator(0, 0, (k * 73) % 360), False)
            # A tuft cuts down from, and grows back to, the size its Shape has here (BP_CutGrass.Full): the Blueprint's
            # own 1.3 is the Center's; the Conclave's wheat stands fuller.
            for part in actor.get_components_by_class(unreal.StaticMeshComponent):
                part.set_editor_property('relative_scale3d', unreal.Vector(*GRASS_SIZE))
            if first is None:
                first = actor
                self.tag(actor, GRASS_ENTRY, (x + dx, y + dy, base), label + ' Grass', 'Grass')   # one tag a clump: scannable
        return first

    def encounter(self, label, x, y, room, give, message, goal=''):
        return self.spawn('BP_Encounter', label, self.at(x, y, 400), None, 'Encounters', Room=room, Learn=0, Give=give,
                          Message=message, NextGoal=goal)

    def require(self, label, place, needs, give, message):
        values = {'Need%s' % 'ABCD'[i]: token for i, token in enumerate(needs)}
        return self.spawn('BP_Requirement', label, place, None, 'Requirements', Give=give, Message=message, **values)

    def floor(self, label, x, y, size, token, period, offset, material):
        """A pulsing furnace floor (BP_Hazard): it burns while it glows, Settle within 16 m darkens it for good
        (token). Its hurt zone is axis-aligned, size (x, y) cm."""
        actor = self.spawn('BP_Hazard', 'Furnace Floor ' + label, (x, y, self.g.at(x, y) + 3), (size[0] / 100, size[1] / 100, 1),
                           'Foundry', Deep=False, Off=token, Period=float(period), Offset=float(offset))
        if material:
            self.reskin(actor, None, material)
        return actor

    def site(self, title, x, y, kind, token):
        self.sites.append((title, x, y, kind, token))

    def spot(self, row):
        """Where a person stands: the scenario's spot for the key, or one shared by the same person at the same lore
        place (KairosSpire stands where Kairos stands), else the lore's point."""
        key, speaker, (lx, ly), yaw = row[0], row[1], row[5], row[6]
        if key in self.spots:
            return self.spots[key]
        for other in PEOPLE:
            if other[1] == speaker and other[5] == (lx, ly) and other[0] in self.spots:
                return self.spots[other[0]]
        return (lx * M, ly * M, yaw, None)


GRASS_SIZE = (2.4, 2.4, 1.5)   # a goldgrass tuft's Shape scale in the Conclave
PICKUPS = {0: 'SM_CN_PickupHealth', 1: 'SM_CN_PickupDivinity', 2: 'SM_CN_PickupAmmo'}

# Where the Commons folk stand (metres, yaw): inside the generator's keep-clear zones (plaza 45 m round the Orrery,
# the Archive 16 m, the Mendery 12 m, the Shrine 10 m, Patience 8 m, the north gate road, 6 m either side of a road),
# so no house of the town lands on a person. Everyone else stands at the lore's point or where a region puts them.
SPOTS = {'Orsolya': (-738.0, 10.0, 200.0), 'Kairos': (-425.2, 107.5, -112.6), 'Petra': (-415.4, 107.3, -100.0),
         'Tamsin': (-500.0, 28.0, 120.0), 'Halden': (-517.1, -103.6, 65.6), 'Patience': (-430.0, 52.0, 230.0),
         'Wen': (-492.0, -34.0, 70.0), 'Marek': (-385.0, -5.0, 260.0), 'Sefa': (-456.0, -36.0, 20.0),
         'Quill': (-462.0, 40.0, 180.0), 'Teodor': (-312.0, 9.0, 270.0), 'Ama': (-548.0, 5.0, 300.0),
         'Listener': (-565.0, 102.0, 250.0), 'Dov': (-62.0, 4.0, 120.0)}


# ---------------------------------------------------------------- walls of panels

def ring(p, label, cx, cy, radius, panel, put, steep=False):
    """Panels closing a circle of `radius` cm round (cx, cy), each tangent to it (put(label, x, y, yaw, width)).
    Where the circle runs past the walk limit the parapet closes it, and an end panel along the slope runs on to
    the parapet; with `steep`, chords that cross a sheer terrace face (no walkable way across) are left to it."""
    step = math.radians(.5)
    inside = [abs(cy + math.sin(k * step) * radius) <= WALK for k in range(720)]
    runs = []
    if all(inside):
        n = max(3, int(math.ceil(2 * math.pi * radius / panel)))
        angles = [(k + .5) / n * 2 * math.pi for k in range(n)]
        ends = []
    else:
        start = inside.index(False)
        run = []
        for i in range(721):
            k = start + i
            if i < 720 and inside[k % 720]:
                run.append(k * step)
            elif run:
                runs.append(run)
                run = []
        angles, ends = [], []
        for run in runs:
            a0, a1 = run[0], run[-1]
            n = max(1, int(math.ceil((a1 - a0) * radius / panel)))
            angles += [a0 + (a1 - a0) * j / n for j in range(n + 1)]
            ends += [a0, a1]
    placed = []
    for k, a in enumerate(angles):
        x, y = cx + math.cos(a) * radius, cy + math.sin(a) * radius
        if steep and sheer(p, x, y, a):
            continue
        placed.append(put('%s %d' % (label, k), x, y, math.degrees(a), 1.0))
    for k, a in enumerate(ends):
        x, y = cx + math.cos(a) * radius, cy + math.sin(a) * radius
        # Yaw 0 runs the panel's width along y, from the circle's end out toward the parapet at 300 m.
        placed.append(put('%s End %d' % (label, k), x, math.copysign(WALK, y), 0.0, 1.15))
    p.ring_panels[label] = [a for a in placed if a is not None]
    return p.ring_panels[label]


def sheer(p, x, y, a):
    """True when a panel at (x, y) tangent at bearing a would stand across a terrace face no one walks or jumps
    up: each of three cuts across it climbs more than 50 degrees somewhere within 2.5 m."""
    ux, uy = math.cos(a), math.sin(a)
    for t in (-300.0, 0.0, 300.0):
        sx, sy = x - uy * t, y + ux * t
        h = [p.g.at(sx + ux * d, sy + uy * d) for d in range(-250, 251, 50)]
        if max(abs(b - c) for b, c in zip(h, h[1:])) < 60.0:
            return False
    return True


def court(p, label, x, y, gate, give='', ability=',lightstep,', yaw=None, size=1200.0, folder='Courts', message=''):
    """A walled square court (SM_CN_TerraceWall raised to about 5 m) with a 6 m gate in its front wall: a lattice
    (Light Step, open for good) or a sealed vault door (an ability learned in a later level). On the drum's slopes
    the gate wall runs along the slope's contour, facing downhill, so the gate stands level. Returns the centre
    (x, y, floor) and the gate actor."""
    x, y = p.free(x, y, size * .85)
    if yaw is None:
        yaw = 0.0 if abs(y) < 8000 else (90.0 if y < 0 else -90.0)
    a = math.radians(yaw)
    fx, fy, sx, sy = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    half = size / 2
    walls = ((-half, 0.0, 180.0, 1.0), (0.0, half, 90.0, 1.0), (0.0, -half, -90.0, 1.0), (half, 450.0, 0.0, .25), (half, -450.0, 0.0, .25))
    for k, (u, v, turn, length) in enumerate(walls):
        wx, wy = x + fx * u + sx * v, y + fy * u + sy * v
        t = math.radians(yaw + turn)
        along = (-math.sin(t), math.cos(t))
        reach = 600.0 * length * size / 1200
        heights = [p.g.at(wx + along[0] * d, wy + along[1] * d) for d in (-reach, 0.0, reach)]
        base = min(heights) - 30
        p.mesh('%s Wall %d' % (label, k), 'SM_CN_TerraceWall', (wx, wy, base), (0, 0, yaw + turn),
               (1.0, length * size / 1200, (480 + max(heights) - base) / 250), folder)
    gx, gy = x + fx * half, y + fy * half
    gz = min(p.g.at(gx + sx * d, gy + sy * d) for d in (-300.0, 0.0, 300.0)) - 15
    if gate == 'lattice':
        door = p.lattice(label + ' Gate', (gx, gy, gz), yaw, 0.0, give, 900.0, message, folder=folder)
    else:
        door = p.lattice(label + ' Door', (gx, gy, gz), yaw, 0.0, give, 900.0, message, ability, 'SM_CN_VaultDoor', folder=folder)
    p.solids.append((x, y, half * 1.45))
    return (x, y, p.g.at(x, y)), door


# ---------------------------------------------------------------- the people

FIGURES = ('SM_CP_Robot', 'SM_CP_Courier', 'SM_CP_Mechanoid', 'SM_CP_Mecha', 'SM_CP_Lightform', 'SM_CP_Wisp')
BOB = {'SM_CP_Courier': 4.0, 'SM_CP_Lightform': 6.0, 'SM_CP_Wisp': 12.0}  # cm of idle float for figures that hover
ALIASES = {'mesh': 'shape', 'figure': 'shape', 'mannequin': 'body', 'skeleton': 'body', 'material': 'skin'}
# BP_NPC's garment components and the bones they hang from (its construction script and BeginPlay attach them there
# too: Tools/blueprint_logic/conclave_logic.py npc()).
GARMENTS = (('Lower', 'pelvis'), ('Upper', 'spine_05'), ('Head', 'head'))
# A garment rides its bone rigidly, so its world-bounds centre keeps one distance from that bone in every pose: up to
# 41 cm for the long skirts on the pelvis (people.py's meshes over the README's bind pose), so a 40 cm limit would list
# skirts that hang right. A garment dropped under the actor's root (the 2026-11-07 review's heaps) lies about a metre
# from its bone.
GARMENT_REACH = 50.0  # cm
# BP_NPC's ChildActorComponent that shows a MetaHuman person (physis_conclave_tools LOOK), and the costume component
# under that person's Body (physis_conclave_people COSTUME).
LOOK = 'Look'
COSTUME = 'Costume'


def cast_table():
    """CAST, the looks of the people: Content/Python/physis_conclave_cast.py, a pure literal the editor imports
    (its Python has no numpy, so it cannot import the mesh generator Tools/conclave_meshes/people.py, which checks
    the same table against its builders)."""
    try:
        import importlib
        import physis_conclave_cast
        importlib.reload(physis_conclave_cast)
        return dict(physis_conclave_cast.CAST), 'physis_conclave_cast.py'
    except Exception as error:  # a broken table leaves the people as bare Mannequins and figures, never no people
        unreal.log_warning('Conclave scenario: physis_conclave_cast.CAST could not be read (%s); the people stand undressed' % error)
    return {}, ''


def look(row, cast):
    """A person's look from CAST (keyed by the lore's mesh name, the key or the speaker; a dict, a tuple
    (body, skin, lower, upper, head) or a figure's mesh name). Without one, a figure stands as its own mesh and a
    human as a bare Mannequin (Quinn for an af_/bf_ voice, Manny otherwise). 'mh' is the person's MetaHuman (a dict
    row's 'mh', else ''); the rest of the row stays the stand-in until that MetaHuman is assembled. 'look_scale' is the
    scale Look shows that MetaHuman at (a dict row's, else 1). A row's 'scale', the stand-in's, is not read: a
    MetaHuman's height is its body's."""
    key, speaker, mesh, voice = row[:4]
    entry = next((cast[name] for name in (mesh, key, speaker) if name in cast), None)
    out = {'body': '', 'skin': '', 'lower': '', 'upper': '', 'head': '', 'shape': '', 'mh': '', 'look_scale': 1.0,
           'bob': BOB.get(mesh, 0.0)}
    if isinstance(entry, str):
        out['shape'] = entry
    elif isinstance(entry, (tuple, list)):
        out.update({field: value or '' for field, value in zip(('body', 'skin', 'lower', 'upper', 'head'), entry)})
    elif isinstance(entry, dict):
        for name, value in entry.items():
            field = ALIASES.get(str(name).lower(), str(name).lower())
            if field in out and value is not None:
                out[field] = value
    if not out['body'] and not out['shape']:
        if mesh in FIGURES:
            out['shape'] = mesh
        else:
            out['body'] = 'Quinn' if voice[:2] in ('af', 'bf') else 'Manny'
    body = str(out['body']).replace('SKM_', '').replace('_Simple', '')
    out['body'] = body[:1].upper() + body[1:].lower() if body else ''
    if out['body'] and not out['skin']:
        out['skin'] = 'Porcelain' if sum(map(ord, key)) % 2 else 'Obsidian'
    out['skin'] = str(out['skin']).replace('MI_CP_', '')
    for field in ('lower', 'upper', 'head'):
        if out[field] and not str(out[field]).startswith('SM_'):
            out[field] = 'SM_CP_G_' + out[field]
    if out['shape'] and not str(out['shape']).startswith('SM_'):
        out['shape'] = 'SM_CP_' + out['shape']
    out['bob'] = float(out['bob'] or 0.0)
    out['look_scale'] = float(out['look_scale'] or 1.0)
    return out


def component(actor, name):
    for part in actor.get_components_by_class(unreal.ActorComponent):
        if part.get_name() == name:
            return part
    return None


def assembled(dress):
    """The person's assembled MetaHuman Blueprint (physis_conclave_cast FILES['look']), or None: no MetaHuman in the
    row, or not assembled yet, and then the row's Mannequin stands in (people are built one at a time). A row carries
    'mh' only when cast_table() has read the cast module, so it is loaded here."""
    if not dress['mh']:
        return None
    import physis_conclave_cast
    return asset(physis_conclave_cast.FILES['look'].format(key=dress['mh']), optional=True)


def wear(npc, dress):
    """Dresses a BP_NPC. A MetaHuman whose Blueprint is assembled shows through Look, which takes that Blueprint's
    generated class (a ChildActorComponent spawns a class), with Body, the garments and Shape emptied. Everyone else
    clears Look first, so no figure or stand-in keeps a MetaHuman, and wears a Mannequin body in its skin with garments
    on its bones, or a figure's Shape. Garments are modelled in actor space over the bind pose, so each takes the
    actor's transform while the body still shows the bind pose, before MM_Idle is set to play, and is attached to its
    bone keeping that world transform. Once BP_NPC's construction script has attached it there at spawn, this attach
    changes nothing: the world transform, set while attached, is stored relative to the bone, which every later
    construction re-reads. Returns the garments put on, (component name, bone, component, mesh), for fitting().
    A MetaHuman's Look takes the row's look_scale before its class, so the person spawns at that size."""
    body, shape, view = component(npc, 'Body'), component(npc, 'Shape'), component(npc, LOOK)
    parts = {name: component(npc, name) for name, _ in GARMENTS}
    built = assembled(dress)
    if built is not None and view is not None:
        # Scale first: setting the class spawns the person at Look's world transform, scale included, and attaches it
        # keeping that scale (ChildActorComponent CreateChildActor), so BP_<mh> and all of it stand at the row's size
        # on Look's origin, the floor under BP_NPC. A child is an adult body shown smaller (MH look_scale).
        size = dress['look_scale']
        view.set_relative_scale3d(unreal.Vector(size, size, size))
        view.set_child_actor_class(built.generated_class())
        if body:
            body.set_skinned_asset_and_update(None, True)
        for part in list(parts.values()) + [shape]:
            if part:
                part.set_static_mesh(None)
        return []
    if view:
        view.set_child_actor_class(None)
    if dress['shape']:
        if shape:
            shape.set_static_mesh(mesh_asset(dress['shape']))
        if body:
            body.set_skinned_asset_and_update(None, True)
        for part in parts.values():
            if part:
                part.set_static_mesh(None)
        return []
    if shape:
        shape.set_static_mesh(None)
    if not body:
        return []
    body.set_skinned_asset_and_update(asset(SKELETAL % dress['body']), True)
    skin = asset(MATS + '/MI_CP_' + dress['skin'])
    for slot in range(2):
        body.set_material(slot, skin)
    here = npc.get_actor_transform()
    worn = []
    for name, bone in GARMENTS:
        part, mesh = parts[name], dress[name.lower()]
        if not part:
            continue
        model = mesh_asset(mesh) if mesh else None
        part.set_static_mesh(model)
        if mesh:
            part.set_world_transform(here, False, True)
            part.attach_to_component(body, bone, KEEP, KEEP, KEEP, False)
            worn.append((name, bone, part, model))
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    body.override_animation_data(asset(IDLE), True, True, 0.0, 1.0)
    return worn


def shown(key, view, mh, size):
    """The report's rows for a person shown through Look: BP_<mh> spawned at size, the row's look_scale (BP_NPC
    stands at actor scale 1, so its world scale is Look's), its Body on the people's shared skeleton playing their idle
    by itself, and its costume under Body following it (physis_conclave_people people_post). Look's spawned actor is
    read as a property, its C++ getter not being exposed to Python; the offline harness never spawns child actors, so
    there every such row reads 'not measured'."""
    import physis_conclave_cast
    try:
        child = view.get_editor_property('child_actor')
        if child is None:
            return ['%s %s: not measured (no BP_%s spawned)' % (key, LOOK, mh)]
        rows = []
        if child.get_class().get_name() != 'BP_%s_C' % mh:
            rows.append('%s %s: shows %s, not BP_%s' % (key, LOOK, child.get_class().get_name(), mh))
        scale = child.get_actor_scale3d()
        if max(abs(scale.x - size), abs(scale.y - size), abs(scale.z - size)) > 1e-3:
            rows.append('%s %s: BP_%s stands at scale %.3f, not its look_scale %.3f (re-run conclave:scenario)' %
                        (key, LOOK, mh, scale.z, size))
        body = component(child, 'Body')
        mesh = body.get_skinned_asset() if body else None
        if mesh is None or not body.is_visible():
            return rows + ['%s %s: its Body shows no mesh' % (key, LOOK)]
        if mesh.skeleton is None or mesh.skeleton.get_path_name().split('.')[0] != physis_conclave_cast.SKELETON:
            rows.append('%s %s: its Body is not on %s' % (key, LOOK, physis_conclave_cast.SKELETON))
        idle = body.get_editor_property('animation_data').get_editor_property('anim_to_play')
        if (body.get_animation_mode() != unreal.AnimationMode.ANIMATION_SINGLE_NODE or idle is None
                or idle.get_path_name().split('.')[0] != physis_conclave_cast.IDLE):
            rows.append('%s %s: its Body does not play %s (run conclave:people_post:%s)' % (key, LOOK, physis_conclave_cast.IDLE, mh))
        costume = component(child, COSTUME)
        if costume is None or costume.get_skinned_asset() is None:
            rows.append('%s %s: no costume (run conclave:people_import:%s, then people_post)' % (key, LOOK, mh))
        elif costume.get_attach_parent() != body or costume.get_editor_property('leader_pose_component') != body:
            rows.append('%s %s: the costume does not follow Body' % (key, LOOK))
        return rows
    except Exception as error:
        return ['%s %s: not measured (%s)' % (key, LOOK, error)]


def fitting(key, npc, dress, worn):
    """The scenario report's 'people' rows for one person (the whole list must come out empty). A MetaHuman shown
    through Look is measured by shown(); one assembled but standing in, since BP_NPC has no Look yet, is listed. For a
    Mannequin: a Body that shows no Mannequin (no mesh, or hidden), and each garment that is not attached to its bone on
    the Body, hangs from a bone the Body lacks, or has its world-bounds centre more than GARMENT_REACH from that bone.
    Whatever cannot be measured is listed with the reason, so an empty list means every garment was measured on its
    bone. The offline harness's stub has no attachment queries, so there every row reads 'not measured'
    (sim_scenario.py checks attachment itself)."""
    rows = []
    if assembled(dress) is not None:
        view = component(npc, LOOK)
        if view is not None:
            return shown(key, view, dress['mh'], dress['look_scale'])
        rows.append('%s: BP_NPC has no %s, so the Mannequin stands in for BP_%s (run conclave:npc_look)' % (key, LOOK, dress['mh']))
    if not dress['body']:
        return rows  # a figure: its Shape is its whole look
    body = component(npc, 'Body')
    try:
        if body.get_skinned_asset() is None or not body.is_visible():
            rows.append('%s: the Body shows no %s' % (key, dress['body']))
    except Exception as error:
        rows.append('%s Body: not measured (%s)' % (key, error))
    for name, bone, part, model in worn:
        try:
            parent, socket = part.get_attach_parent(), str(part.get_attach_socket_name())
            if parent != body or socket != bone:
                rows.append('%s %s: attached to %s %s, not Body %s' % (key, name, parent.get_name() if parent else 'nothing', socket, bone))
            elif not body.does_socket_exist(bone):
                rows.append('%s %s: the Body has no bone %s' % (key, name, bone))
            elif model is None:
                rows.append('%s %s: no mesh to measure' % (key, name))
            else:
                box = model.get_bounding_box()
                local = unreal.Vector((box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2, (box.min.z + box.max.z) / 2)
                gap = part.get_world_transform().transform_location(local).distance(body.get_socket_location(bone))
                if gap > GARMENT_REACH:
                    rows.append('%s %s: %.0f cm from %s' % (key, name, gap, bone))
        except Exception as error:
            rows.append('%s %s: not measured (%s)' % (key, name, error))
    return rows


def person(p, row, cast, place, yaw):
    key, speaker, mesh, voice, kind = row[:5]
    show, hide, greeting, topics, give, quest, reward = row[7:]
    pages = conversation_pages(row)
    starts, first = [], len(greeting)
    for _, answer in topics:
        starts.append(first)
        first += len(answer)
    dress = look(row, cast)
    npc = p.spawn('BP_NPC', 'Person ' + key, place, None, 'People', Speaker=speaker, Key=key,
                  Pages='|'.join(wrap(page) for page in pages), Asks='|'.join(label for label, _ in topics),
                  Starts='|'.join(str(s) for s in starts), Greet=len(greeting), Show=show, Hide=hide,
                  Give=give + (WISP_GIFT if key == 'Wisp' else ''), Quest=quest,
                  RewardDivinity=float(reward.get('divinity', 0.0)), RewardHeal=bool(reward.get('heal', False)),
                  Note=reward.get('note', ''), Face=kind != 'mecha', Bob=dress['bob'])
    npc.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    p.misfits += fitting(key, npc, dress, wear(npc, dress))
    # Page k plays BP_Physis.PhysisNarrate("Talk <Key> <k>"), k counted from 0 over the greeting and then each topic.
    # Someone with no voice (Patience, silent until the Shepherd falls) gets no voice actors: a BP_LogVoice with no
    # sound makes PhysisNarrate, which has no IsValid guard, log "Accessed None" on every page.
    for k in range(len(pages) if voice else 0):
        title = person_key(key, k)
        p.spawn('BP_LogVoice', 'Voice ' + title, VOICE_SPOT, None, 'Voices', Title=title, Voice=asset(VOICES + '/' + voice_name(title)))
    return npc


def people(p):
    cast, source = cast_table()
    p.cast_source = source
    p.misfits = []  # the report's 'people': fitting()'s rows for everyone
    for row in PEOPLE:
        x, y, yaw, z = p.spot(row)
        floor = max(p.g.at(x, y), 0.0) if z is None else z
        with p.behind(*p.zones.get(row[0], ())):
            person(p, row, cast, (x, y, floor), yaw)


# ---------------------------------------------------------------- the regions

def pylon(p, n, name, x, y, need, face, folder='Pylons'):
    """A Spine Pylon: the mast, the beam it sends up to the Spine (tag PylonBeamN, hidden in game until
    BP_ConclaveDirector shows it for ,pylonN,) and the board at its foot, facing `face` (radians), that relights it
    once `need` is held. The beam leans to meet the axis square on, ending inside the Spine."""
    base = p.g.at(x, y) - 30
    p.mesh(name, 'SM_CN_Pylon', (x, y, base), (0, 0, math.degrees(face)), 1.0, folder, solid=450)
    top = base + 1800
    across, up = -y, AXIS - top
    length = math.hypot(across, up) - 300
    beam = p.mesh(name + ' Beam', 'SM_CN_PylonBeam', (x, y, top), (math.degrees(math.atan2(across, up)), 0, 0), (1.0, 1.0, length / 69000),
                  folder, collide=False, shadow=False)
    beam.set_actor_hidden_in_game(True)
    beam.set_editor_property('tags', ['PylonBeam%d' % n])
    bx, by = x + math.cos(face) * 380, y + math.sin(face) * 380
    board = p.switch(name + ' Board', (bx, by, p.g.at(bx, by) - 5), math.degrees(face), 'SM_CN_Board', True, folder=folder, Need=need,
                     Give=',pylon%d,' % n, Denied=MESSAGES['pylon_dry'], Done=MESSAGES['pylon%d' % n])
    p.light(name + ' Crown', (x, y, top + 250), GOLD, 7000, 2600, folder)
    p.marks[name] = (x, y, base)
    return board


def pack(p, label, x, y, levels, room=0, spread=700.0, z=None):
    """Enemies round (x, y): one of each level in `levels`, spread on a circle."""
    out = []
    for k, level in enumerate(levels):
        a = k / len(levels) * 2 * math.pi + .6
        out.append(p.enemy(level, '%s %d' % (label, k), x + math.cos(a) * spread, y + math.sin(a) * spread, room, z))
    return out


def wellspring(p):
    wx, wy = cm(*plan.WELL)
    floor = p.g.at(wx, wy)
    p.landmark('Wellspring Garden', 'SM_CN_WellGarden', (wx, wy, floor - 10), 0.0, 1.0, 1200)
    # The current home to the Center sits in the garden's basin, shown always (no Need).
    p.spawn('BP_Current', 'Current Home', (wx, wy, floor + 25), None, 'Wellspring', Need='', Dest=2, Radius=180.0)
    p.marks['Current Home'] = (wx, wy, floor + 25)
    p.light('Wellspring Glow', (wx, wy, floor + 600), BLUE, 9000, 2800, 'Wellspring')
    sx, sy = cm(-733.0, -6.0)
    p.check('Wellspring', sx, sy, text('still_wellspring', 'Follow the road north to the Commons and find Kairos at the Archive.'), 800.0)
    # She arrives on the Still Point, 20 m from the current: outside its 1.8 m reach, so arriving never sends her back.
    p.marks['Arrival'] = p.at(sx, sy, 120)
    p.marker('Arrival', p.marks['Arrival'], 'ConclaveArrival', 'Wellspring')
    p.pickup(0, 'Wellspring Capsule', sx + 700, sy - 500)
    p.pickup(1, 'Wellspring Crystal', sx + 500, sy + 900)


# The Orrery's rings, in the plaque's order, and where each one's wheel stands on the basin rim (bearing, degrees).
ORRERY_RINGS = (("the First Ones' world", 95.0), ('Earth', 335.0), ('the Center', 215.0))


def commons(p):
    ox, oy = cm(*plan.ORRERY)
    p.landmark('Orrery', 'SM_CN_Orrery', (ox, oy, p.g.at(ox, oy) - 10), 0.0, 1.0, 700)
    toward = lambda x, y: math.degrees(math.atan2(oy - y, ox - x))  # noqa: E731
    ax, ay = cm(*plan.ARCHIVE)
    p.landmark('Archive', 'SM_CN_Archive', (ax, ay, p.g.at(ax, ay) - 20), toward(ax, ay), 1.0, 1100)  # its arcade faces the plaza
    mx, my = cm(*plan.MENDERY)
    p.landmark('Mendery', 'SM_CN_Mendery', (mx, my, p.g.at(mx, my) - 10), toward(mx, my), 1.0, 700)
    hx, hy = cm(*plan.SHRINE)
    p.landmark('Listeners Shrine', 'SM_CN_Shrine', (hx, hy, p.g.at(hx, hy) - 10), toward(hx, hy), 1.0, 450)
    p.landmark('North Gate', 'SM_CN_Gate', (-30500.0, 0.0, p.g.at(-30500.0, 0.0) - 10), 0.0, 1.0)
    # The market on the plaza's north-west edge, by Sefa.
    for k, bearing in enumerate((-55.0, -66.0, -77.0)):
        b = math.radians(bearing)
        x, y = ox + math.cos(b) * 4200, oy + math.sin(b) * 4200
        p.landmark('Market Stall %d' % k, 'SM_CN_Stall', (x, y, p.g.at(x, y) - 5), bearing + 180, 1.0, 300)
    for k, (x, y, z) in enumerate(((ox, oy, 1200), (ax + 1300 * math.cos(math.radians(toward(ax, ay))), ay + 1300 * math.sin(math.radians(toward(ax, ay))), 600),
                                   (ox + 3400 * math.cos(math.radians(-66)), oy + 3400 * math.sin(math.radians(-66)), 500))):
        p.light('Commons Lamp %d' % k, (x, y, p.g.at(x, y) + z), GOLD, 5000, 2400, 'Commons')
    cx, cy = cm(-488.0, -22.0)
    p.check('Commons', cx, cy, text('still_commons', 'The Commons. Kairos keeps the Archive on the east terrace; past the north gate the swarm holds the three Spine Pylons.'), 900.0)
    for k, side in enumerate((-550.0, 550.0)):
        p.pickup(0, 'Gate Capsule %d' % k, -32000.0, side)
    p.pickup(2, 'Gate Ammo', -32400.0, 0.0)

    # Puzzle: the Orrery's rings, turned in the plaque's order. Each wheel that will not turn reads the plaque's first
    # line; each that turns reads the next.
    clue = text('orrery_clue', "The plaque on the rim begins: 'First the world that made the instrument.'")
    lines = (text('orrery_turn1', "The First Ones' ring turns, slow and heavy. The plaque goes on: 'Then the world that came to listen.'"),
             text('orrery_turn2', "The Earth ring turns. The plaque ends: 'Last, the place between them all.'"),
             text('orrery_turn3', "The ring of the Center turns, and all three move together. Light gathers by the basin's west rim."))
    for k, (name, bearing) in enumerate(ORRERY_RINGS):
        b = math.radians(bearing)
        x, y = ox + math.cos(b) * 850, oy + math.sin(b) * 850
        p.switch('Orrery Wheel %d' % k, (x, y, p.g.at(x, y) - 5), bearing, 'SM_CN_Sluice', True, folder='Puzzles',
                 Need='' if k == 0 else ',cn_orrery%d,' % k, Give=',cn_orrery,' if k == 2 else ',cn_orrery%d,' % (k + 1),
                 Denied='' if k == 0 else 'The ring of %s will not turn yet. %s' % (name, clue), Done=lines[k])
    gx, gy = ox + math.cos(math.radians(270)) * 950, oy + math.sin(math.radians(270)) * 950
    p.relic('Orrery Gift', p.at(gx, gy, 120), ',cn_orrerygift,', text('orrery_gift', 'The Orrery keeps time again. Divinity +60.'), ',cn_orrery,', 60.0,
            False, 'SM_CN_LightCache', .6)
    p.site('The Orrery', ox, oy, 0, ',cn_orrerygift,')


# The Terraces' three sluices in the irrigation board's order: the lowest by the west stair, the middle one under
# the pipe bridge, the high one beside the pylon. From the road the middle one is met first.
SLUICES = (('Low', (-112.0, -200.0)), ('Middle', (-45.0, -232.0)), ('High', (-30.0, -262.0)))
BOARD = (-70.0, -232.0)
TERRACE_RING = 3400.0


def terraces(p):
    px, py = cm(*plan.TERRACE_PYLON)
    rx, ry = cm(-60.0, -215.0)  # where the west road ends on the Terraces
    facing = lambda x, y: math.degrees(math.atan2(ry - y, rx - x))  # noqa: E731
    p.check('Terraces', *cm(-134.0, -125.0), text('still_terraces', 'The Terraces. Scan the irrigation board, open the three sluices in its order and wake the Terrace Pylon.'))
    bx, by = cm(*BOARD)
    p.mesh('Irrigation Board', 'SM_CN_Board', (bx, by, p.g.at(bx, by) - 5), (0, 0, facing(bx, by)), 1.0, 'Terraces', solid=150)
    p.scans['The Irrigation Board'] = (bx, by, p.g.at(bx, by) + 160)
    spots = [cm(*xy) for _, xy in SLUICES]
    for k, (name, _) in enumerate(SLUICES):
        x, y = spots[k]
        with p.behind(',settle,' if k == 2 else ''):
            p.switch('Sluice ' + name, (x, y, p.g.at(x, y) - 5), facing(x, y), 'SM_CN_Sluice', True, folder='Terraces',
                     Seq=k + 1, SeqBase=0, Need='', Give=',sluice%d,' % (k + 1), Denied='', Done=MESSAGES['sluice%d' % (k + 1)])
        p.light('Sluice Glow %d' % k, p.at(x, y, 320), GOLD, 1800, 800, 'Terraces')
    # The board's landmarks: the west stair by the low sluice and the pipe bridge over the middle one.
    sx, sy = spots[0]
    p.mesh('West Stair', 'SM_CN_Stairs', (sx, sy - 650, p.g.at(sx, sy - 650) - 20), (0, 0, -90), 1.0, 'Terraces', solid=300)
    # The irrigation channel runs from sluice to sluice up to the pylon's turbine (water, no collision).
    line = spots + [(px, py)]
    heading = []
    piece = 0
    for (ax, ay), (bx2, by2) in zip(line, line[1:]):
        dist = math.hypot(bx2 - ax, by2 - ay)
        yaw = math.degrees(math.atan2(by2 - ay, bx2 - ax))
        heading.append(yaw)
        count = max(1, int(math.ceil(dist / 1000)))
        for k in range(count):
            t0, t1 = k / count, (k + 1) / count
            x0, y0, x1, y1 = ax + (bx2 - ax) * t0, ay + (by2 - ay) * t0, ax + (bx2 - ax) * t1, ay + (by2 - ay) * t1
            z0, z1 = p.g.at(x0, y0), p.g.at(x1, y1)
            pitch = math.degrees(math.atan2(z1 - z0, dist / count))
            p.mesh('Channel %d' % piece, 'SM_CN_Channel', ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2 - 20), (0, pitch, yaw),
                   (dist / count / 1000, 1.0, 1.0), 'Terraces', collide=False)
            piece += 1
    mx, my = spots[1]
    p.mesh('Pipe Bridge', 'SM_CN_PipeBridge', (mx, my, p.g.at(mx, my) - 30), (0, 0, heading[1] + 90), 1.0, 'Terraces')
    # Hydroponic beds on level ground (the generator's pads), and the one Rhea hides behind.
    beds(p, cm(-95.0, -190.0), 7000, [(px, py, TERRACE_RING + 600)] + [(x, y, 900) for x, y in spots] + [(bx, by, 700)])
    hx, hy = cm(-150.0, -146.0)
    p.mesh('Rhea Tray', 'SM_CN_HydroBed', (hx, hy, p.low(hx, hy, ((-500, -150), (500, -150), (-500, 150), (500, 150)), (1, 0, 0, 1)) - 10),
           (0, 0, 90), 1.0, 'Terraces', solid=500)

    # The upper Terraces round the pylon: the swarm's barricades close them on every walkable side.
    face = math.radians(facing(px, py))
    with p.behind(',settle,'):
        pylon(p, 1, 'Terrace Pylon', px, py, ',sluice3,', face)
        kx, ky = px + 1400, py - 1800
        p.relic('Tamsin Kite', p.at(kx, ky, 130), ',kite,', MESSAGES['kite'], mesh='SM_CN_Kite')
        for k, (bearing, r, level) in enumerate(((40, 900, 5), (200, 900, 5), (120, 1400, 3), (300, 1400, 3))):
            b = math.radians(bearing)
            p.enemy(level, 'Terrace Guard %d' % k, px + math.cos(b) * r, py + math.sin(b) * r, 301)
        p.encounter('Terrace Guards', px, py, 301, ',cn_terraceguard,', text('terrace_guards', 'The Reavers fall, and the upper Terraces are quiet.'))
        for k, (dx, dy) in enumerate(((-900, 1200), (1500, 300))):
            p.enemy(2, 'Upper Terrace %d' % k, px + dx, py + dy)
        p.pickup(0, 'Pylon Capsule', px - 700, py + 900)
    panels = ring(p, 'Terrace', px, py, TERRACE_RING, 760.0, lambda label, x, y, yaw, width: p.barrier(label, x, y, yaw, '', width), True)
    nearest = min(panels, key=lambda a: math.hypot(a.get_actor_location().x - rx, a.get_actor_location().y - ry), default=None)
    if nearest:
        where = nearest.get_actor_location()
        p.scans['AL Barricade'] = (where.x, where.y, where.z + 450)

    p.relic('Ledger Page Terraces', p.at(*cm(-95.0, -172.0), lift=110), ',page1,', MESSAGES['page'], mesh='SM_CN_LedgerPage')
    for label, (x, y), levels in (('Terrace Road', (-205, -55), (1, 1, 2)), ('Terrace Low', (-200, -150), (1, 1, 2)),
                                  ('Terrace Board', (-95, -245), (1, 2, 2)), ('Terrace West', (-160, -232), (2, 2, 3)),
                                  ('Terrace North', (25, -228), (1, 2, 3)), ('Terrace Beds', (-60, -178), (1, 1, 1)),
                                  ('Terrace South', (-235, -110), (1, 2)), ('Terrace Stair', (-125, -215), (2, 3))):
        pack(p, label, *cm(x, y), levels)
    p.pickup(0, 'Terraces Capsule', *cm(-128.0, -118.0))
    p.pickup(1, 'Terraces Crystal', *cm(-140.0, -132.0))
    p.pickup(2, 'Board Ammo', bx + 400, by + 300)


def beds(p, centre, reach, keep):
    """Up to eight 3 x 10 m hydroponic beds on level ground near centre (cm): their long side along the contour,
    off the roads and clear of `keep` ((x, y, r) cm)."""
    cx, cy = centre
    found = []
    for gx in range(int(cx - reach), int(cx + reach) + 1, 1000):
        for gy in range(int(cy - reach), int(cy + reach) + 1, 600):
            if plan.path_gap(gx / M, gy / M) < 9 or any(math.hypot(gx - x, gy - y) < r for x, y, r in keep) or not p.ok(gx, gy, 300, 0, True):
                continue
            h = [p.g.at(gx + u, gy + v) for u in (-520, 520) for v in (-170, 170)]
            if max(h) - min(h) < 25:
                found.append((max(h) - min(h), gx, gy))
    found.sort()
    taken = []
    for _, gx, gy in found:
        if len(taken) >= 8:
            break
        if all(abs(gx - x) > 1200 or abs(gy - y) > 500 for x, y in taken):
            taken.append((gx, gy))
            p.mesh('Hydro Bed %d' % len(taken), 'SM_CN_HydroBed', (gx, gy, p.g.at(gx, gy) - 5), (0, 0, 90), 1.0, 'Terraces', solid=500)
    return taken


# The buoys hold the island's lock, each about 20 m off a shore it can be shot from (the sidearm reaches 35 m).
BUOYS = ((60.0, 74.0, 90.0), (112.0, 40.0, 0.0), (10.0, -28.0, -90.0))  # x, y, the anchor's red eye faces (degrees)
LOCK_RING = 1100.0
ISLAND_RING = 550.0


def reservoir(p):
    ix, iy = cm(*plan.RESERVOIR_ISLAND)
    sx, sy = cm(52.0, 99.0)
    p.check('Reservoir', sx, sy, text('still_reservoir', 'The Reservoir. Shoot the three anchors on the buoys, then wake the Reservoir Pylon on the island.'))
    face = math.atan2(sy - iy, sx - ix)
    entry = next(row[:3] for row in CONCLAVE_SCANS if row[1] == 'AL Anchor')
    with p.water():
        for k, (x, y, eye) in enumerate(BUOYS):
            x, y = cm(x, y)
            p.mesh('Buoy %d' % k, 'SM_CN_Buoy', (x, y, -30), (0, 0, eye), 1.0, 'Reservoir', solid=200)
            # Hovering 0.8 m over the buoy's platform: out of a swimmer's blade (3 m) beside the buoy. Shot only: since
            # 2026-11-08 the water jump (1000 cm/s, again on every press while swimming) lands Physis on the deck, where
            # the blade would reach; the lore says the anchors must be shot.
            p.target('Anchor %d' % k, 'SM_CE_Anchor', (x, y, 230), 304, 4, 1.0, entry, eye, 'Reservoir', shot_only=True)
            p.light('Anchor Eye %d' % k, (x + math.cos(math.radians(eye)) * 150, y + math.sin(math.radians(eye)) * 150, 260), RED, 1500, 700, 'Reservoir')
        p.encounter('Anchors', ix, iy, 304, ',anchors,', MESSAGES['anchors'])
        # The lock: a ring of AL force round the island, standing on the lake bed at least 3.5 m out of the water, that
        # sinks into the bed when the anchors fall.
        def lock(label, x, y, yaw, width):
            base = p.g.at(x, y) - 20
            tall = max(1.0, (350 - base) / 400)
            return p.rise(label, 'SM_CN_Barricade', (x, y, base), ',anchors,', -(400 * tall + 150), (0, 0, yaw), (1, width, tall), 220.0, 'Reservoir')
        ring(p, 'Island Lock', ix, iy, LOCK_RING, 760.0, lock)
        p.light('Island Lock Glow', (ix, iy, 900), RED, 4000, 2200, 'Reservoir')
        with p.behind(',anchors,'):
            for k, bearing in enumerate((20, 110, 200, 290)):
                b = math.radians(bearing)
                p.enemy(5 if k % 2 == 0 else 3, 'Island Guard %d' % k, ix + math.cos(b) * 850, iy + math.sin(b) * 850, 302)
            p.encounter('Island Guards', ix, iy, 302, ',cn_islandguard,', text('island_guards', 'The island\'s guards fall into the lake.'))
            with p.behind(',settle,'):
                pylon(p, 2, 'Reservoir Pylon', ix, iy, ',anchors,', face, 'Reservoir')
                b = face + math.pi
                p.relic('Starlace Seed Pod', p.at(ix + math.cos(b) * 420, iy + math.sin(b) * 420, 120), ',seedpod,', MESSAGES['seedpod'], mesh='SM_CN_SeedPod')
            ring(p, 'Island', ix, iy, ISLAND_RING, 760.0, lambda label, x, y, yaw, width: p.barrier(label, x, y, yaw, '', width, folder='Reservoir'))
    drowned_gate(p)
    # Dov's mooring on the south-west shore.
    with p.water():
        p.mesh('Mooring Pier', 'SM_CN_Pier', (-5000.0, 200.0, 0.0), (0, 0, 0), 1.0, 'Reservoir')
        for k, (x, y, yaw) in enumerate(((-4600.0, 800.0, 15.0), (-4700.0, -400.0, -10.0))):
            p.mesh('Moored Boat %d' % k, 'SM_CN_Boat', (x, y, -50.0), (0, 0, yaw), 1.0, 'Reservoir', solid=300)
        p.relic('Ledger Page Reservoir', (-4450.0, 200.0, 210.0), ',page2,', MESSAGES['page'], mesh='SM_CN_LedgerPage')
    for label, (x, y), levels in (('Shore South', (12, -64), (1, 1, 2)), ('Shore East', (92, 94), (2, 2, 3)),
                                  ('Shore North', (128, 76), (1, 2, 3)), ('Shore West', (-95, 42), (1, 1, 2)),
                                  ('Shore Gate', (-14, -60), (2, 2)), ('Shore Far', (150, -20), (1, 2))):
        pack(p, label, *cm(x, y), levels)
    p.pickup(2, 'Shore Ammo 0', sx + 500, sy + 300)
    p.pickup(2, 'Shore Ammo 1', sx - 500, sy + 350)
    p.pickup(0, 'Shore Capsule', sx + 100, sy + 600)


def drowned_gate(p):
    """Puzzle: the drowned water gate in the south-west of the lake. Two valves on the shores, turned in any order,
    raise it and lift a walkway out of the water to the cache under its arch (shown only then)."""
    sx, sy = cm(-56.0, -12.6)
    gx, gy = cm(-22.0, -6.0)
    yaw = math.degrees(math.atan2(gy - sy, gx - sx))
    ux, uy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for k, (x, y) in enumerate((cm(-60.0, -20.0), cm(30.0, -60.0))):
        p.switch('Drowned Valve %d' % k, (x, y, p.g.at(x, y) - 5), math.degrees(math.atan2(gy - y, gx - x)), 'SM_CN_Sluice', True,
                 folder='Puzzles', Need='', Give=',cn_valve%d,' % (k + 1), Denied='',
                 Done=text('drowned_valve', 'The valve turns, stiff with silt. Somewhere under the water a chain draws tight.'))
    p.require('Drowned Valves', (gx, gy, 600), (',cn_valve1,', ',cn_valve2,'), ',cn_drowned,',
              text('drowned_open', 'Both valves turn. Out in the water the drowned gate rises, and a walkway lifts toward it.'))
    with p.water():
        bed = p.g.at(gx, gy)
        p.rise('Drowned Gate', 'SM_CN_Gate', (gx, gy, bed - 450), ',cn_drowned,', 450, (0, 0, yaw), 1.0, 120.0, 'Puzzles')
        for k, d in enumerate((600.0, 1800.0, 3060.0)):
            x, y = sx + ux * d, sy + uy * d
            p.rise('Drowned Walk %d' % k, 'SM_CN_Pier', (x, y, -290.0), ',cn_drowned,', 250, (0, 0, yaw), 1.0, 110.0, 'Puzzles')
        p.relic('Drowned Cache', (gx, gy, 170.0), ',cn_drowncache,', text('drowned_cache', 'The gate kept its cache dry. Divinity +70, and Physis is fully healed.'),
                ',cn_drowned,', 70.0, True, 'SM_CN_LightCache', .6)
        p.light('Drowned Gate Glow', (gx, gy, 500), GOLD, 2500, 1200, 'Puzzles')
    p.site('The Drowned Gate', gx, gy, 0, ',cn_drowncache,')


def foundry(p):
    fx, fy = cm(*plan.FOUNDRY_PYLON)
    qx, qy = cm(-30.0, 232.0)
    p.check('Foundry', qx, qy, text('still_foundry', 'The Foundry. Cut the crane\'s three cable locks to lower its bridge across the slag, then wake the Foundry Pylon.'))
    # The crane over the slag moat (18-28 m round the pylon) on its south-west side: its bridge hangs 8 m up until the
    # locks are cut, then comes down across the moat, pitched to meet both banks.
    a = math.radians(225.0)
    ca, sa = math.cos(a), math.sin(a)
    inner = p.g.at(fx + ca * 1550, fy + sa * 1550)
    outer = p.g.at(fx + ca * 3050, fy + sa * 3050)
    bx, by = fx + ca * 2300, fy + sa * 2300
    deck = (bx, by, (inner + outer) / 2 + 5)
    pitch = math.degrees(math.atan2(inner - outer, 1600))
    p.rise('Crane Bridge', 'SM_CN_CraneBridge', (deck[0], deck[1], deck[2] + 800), ',bridge,', -800, (0, pitch, math.degrees(a) + 180), 1.0, 120.0, 'Foundry')
    legs = [p.g.at(fx + ca * r, fy + sa * r) for r in (1200, 3400)]
    p.landmark('Crane', 'SM_CN_Crane', (bx, by, min(legs) - 20), math.degrees(a) - 90, 1.0, 0.0, 'Foundry')
    for r in (1200, 3400):
        p.solids.append((fx + ca * r, fy + sa * r, 300))
    entry = next(row[:3] for row in CONCLAVE_SCANS if row[1] == 'Cable Lock')
    for k, (r, turn) in enumerate(((3550, -7.0), (3550, 7.0), (3850, 0.0))):
        b = a + math.radians(turn)
        x, y = fx + math.cos(b) * r, fy + math.sin(b) * r
        p.target('Cable Lock %d' % k, 'SM_CN_CableLock', (x, y, p.g.at(x, y) + 120), 305, 6, 1.0, entry, math.degrees(b), 'Foundry')
    p.encounter('Cable Locks', bx, by, 305, ',bridge,', MESSAGES['bridge'])
    p.light('Crane Lamp', (bx, by, max(legs) + 1500), GOLD, 5000, 2500, 'Foundry')
    with p.behind(',bridge,'):
        pylon(p, 3, 'Foundry Pylon', fx, fy, ',bridge,', a, 'Foundry')
        for k, (bearing, r, level) in enumerate(((100, 1000, 5), (330, 1000, 5), (20, 1300, 3), (170, 1300, 3))):
            b = math.radians(bearing)
            p.enemy(level, 'Yard Guard %d' % k, fx + math.cos(b) * r, fy + math.sin(b) * r, 303)
        p.encounter('Yard Guards', fx, fy, 303, ',cn_yardguard,', text('yard_guards', 'The Reavers in the pylon yard go dark.'))

    # Forge-Mother Ilex, barricaded in front of her workshop.
    ix, iy = cm(-28.0, 196.0)
    ex, ey = cm(-40.0, 215.0)  # where the east road ends
    away = math.atan2(iy - ey, ix - ex)
    wx, wy = ix + math.cos(away) * 800, iy + math.sin(away) * 800
    p.landmark('Ilex Workshop', 'SM_CN_Workshop', (wx, wy, p.g.at(wx, wy) - 20), math.degrees(away) + 180, 1.0, 0.0, 'Foundry')
    for key in ('Ilex', 'IlexThanks'):
        p.spots[key] = (ix, iy, math.degrees(away) + 180, None)
        p.zones[key] = (',settle,',)
    ring(p, 'Ilex', wx, wy, 1300.0, 760.0, lambda label, x, y, yaw, width: p.barrier(label, x, y, yaw, '', width, folder='Foundry'))
    p.solids.append((wx, wy, 1450))

    furnace_row(p)
    prism_mill(p)
    p.landmark('Foundry Workshop', 'SM_CN_Workshop', (-16000.0, 23600.0, p.g.at(-16000.0, 23600.0) - 20), 0.0, 1.0, 950, 'Foundry')
    for label, (x, y), levels in (('Foundry Road', (-72, 203), (1, 1, 2)), ('Foundry Yard', (-55, 252), (1, 2, 3)),
                                  ('Foundry East', (-150, 255), (1, 1, 2)), ('Foundry Slag', (40, 232), (1, 2)),
                                  ('Foundry South', (-120, 150), (2, 2, 3)), ('Ilex Watch', (-5, 170), (1, 1))):
        pack(p, label, *cm(x, y), levels)
    p.pickup(0, 'Foundry Capsule', qx + 600, qy - 400)
    p.pickup(1, 'Foundry Crystal', qx - 500, qy + 500)
    p.pickup(0, 'Crane Capsule', fx + ca * 4300 + 300, fy + sa * 4300)


def furnace_row(p):
    """Halden's memory core at the dead end of a lane between two rows of furnaces, across three pulsing furnace
    floors (cross them dark, or Settle them dark for good). A floor's hurt zone is axis-aligned, so the lane runs
    along x, on the flattest ground found in the Foundry."""
    best = None
    for cx in range(-14000, -5999, 1000):
        for cy in range(15000, 21001, 1000):
            if plan.path_gap(cx / M, cy / M) < 14 or not p.ok(cx, cy, 2400, 0, True):
                continue
            h = [p.g.at(cx + u, cy + v) for u in range(-1600, 2001, 400) for v in (-450, 0, 450)]
            if best is None or max(h) - min(h) < best[0]:
                best = (max(h) - min(h), cx, cy)
    cx, cy = best[1:] if best else cm(-100.0, 175.0)
    material = asset(MATS + '/M_CNFurnace')
    for k, u in enumerate((-1200, -400, 400, 1200)):
        for side, yaw in ((-1, 90.0), (1, -90.0)):
            x, y = cx + u, cy + side * 750
            p.mesh('Furnace %d %d' % (k, side), 'SM_CN_Furnace', (x, y, p.g.at(x, y) - 30), (0, 0, yaw), 1.0, 'Foundry')
    for k, u in enumerate((-1200, -400, 400)):
        p.floor('%d' % k, cx + u, cy, (900, 1000), ',cn_floor%d,' % (k + 1), 3.0, k * 1.57, material)
    for k, v in enumerate((-500, 500)):
        x, y = cx + 1700, cy + v
        p.mesh('Furnace End %d' % k, 'SM_CN_PipeRack', (x, y, p.g.at(x, y) - 20), (0, 0, 0), 1.0, 'Foundry')
    p.relic('Halden Core', p.at(cx + 1300, cy, 120), ',core,', MESSAGES['core'], mesh='SM_CN_MemoryCore')
    for k, u in enumerate((-800, 800)):
        p.light('Furnace Glow %d' % k, p.at(cx + u, cy, 450), GOLD, 4000, 1600, 'Foundry')
    p.scans['Furnace Floor'] = p.at(cx - 1700, cy - 300, 160)
    for k in range(5):
        p.solids.append((cx - 1600 + k * 800, cy, 1100))
    p.marks['Furnace Row'] = (cx, cy, p.g.at(cx, cy))


def prism_mill(p):
    """Puzzle: three prisms over pipe racks, too high for the blade: shoot all three and the mill sets its light down."""
    cx, cy = p.free(*cm(-130.0, 240.0), 1600)
    for k, bearing in enumerate((90.0, 210.0, 330.0)):
        b = math.radians(bearing)
        x, y = cx + math.cos(b) * 900, cy + math.sin(b) * 900
        p.mesh('Prism Rack %d' % k, 'SM_CN_PipeRack', (x, y, p.g.at(x, y) - 20), (0, 0, bearing), 1.0, 'Puzzles')
        p.target('Prism %d' % k, 'SM_CN_LightCache', (x, y, p.g.at(x, y) + 900), 306, 1, .9, None, bearing, 'Puzzles')
        p.light('Prism Glow %d' % k, (x, y, p.g.at(x, y) + 1100), BLUE, 1500, 700, 'Puzzles')
    p.encounter('Prism Mill', cx, cy, 306, ',cn_prisms,', text('prism_mill', 'The three prisms shatter, and the mill sets its light down at its centre.'))
    p.relic('Prism Gift', p.at(cx, cy, 120), ',cn_prismgift,', text('prism_gift', 'The prism mill\'s gift: Divinity +70, and Physis is fully healed.'),
            ',cn_prisms,', 70.0, True, 'SM_CN_LightCache', .6)
    p.solids.append((cx, cy, 1300))
    p.site('The Prism Mill', cx, cy, 0, ',cn_prismgift,')


# The Trial of Light. The climb winds round the Spire on a circle 38 m from its axis (the crystal is at most 24 m
# across its base), platform to platform up 4 m ramps, from a gate 4 m above the plaza to the crown at about 60 m.
RHO = 3800.0
START = 215.0     # bearing of the first platform (degrees), on the south-west face, toward the arriving roads
INSET = 380.0     # a ramp starts and ends this far inside a platform's edge-centre (hexagon radius 5 m, inradius 4.33 m)
# kind, ramps, lattice hold on each ramp (None: none), next platform's scale, label
CLIMB = (('ramp', 1, (0.0,), 1.0, 'First Lattice'), ('ramp', 1, (None,), 1.0, ''), ('ramp', 1, (None,), 1.0, ''),
         ('ramp', 3, (3.5, 3.5, 3.5), 1.6, 'Timed Lattice'), ('ramp', 1, (None,), 1.0, ''), ('ramp', 1, (None,), 1.0, ''),
         ('gap', 0, (), 1.0, ''), ('ramp', 1, (None,), 1.0, ''), ('ramp', 1, (None,), 1.0, ''), ('ramp', 1, (None,), 1.0, ''),
         ('ramp', 1, (None,), 1.0, ''), ('ramp', 1, (None,), 1.0, ''), ('crown', 1, (None,), 0.0, ''))
CROWN_INSET = 850.0  # the last ramp runs 0.5 m onto the crown dais (radius 9 m)
GAP = 1800.0         # centre to centre across the gap: 8-9 m of air between the platforms, so a jump, then a step


def spire(p):
    cx, cy = cm(*plan.SPIRE)
    p.landmark('Lightform Spire', 'SM_CN_Spire', (cx, cy, p.g.at(cx, cy) - 100), 0.0, 1.0, 2700, 'Spire')
    p.light('Spire Foot', (cx, cy, p.g.at(cx, cy) + 3500), BLUE, 12000, 6000, 'Spire')
    p.check('Spire', *cm(312.0, -6.0), text('still_spire', 'The Lightform Spire. When the Spine burns, Iriel waits at the gate on its south-west face; climb to the crown.'))
    # The three relit pylons make the Spine whole, and that unseals the Spire (,spire,): the requirement ticks
    # wherever it stands, so it waits at the Spire's foot.
    p.require('Spine Whole', (cx, cy, p.g.at(cx, cy) + 600), (',pylon1,', ',pylon2,', ',pylon3,'), ',spire,', MESSAGES['spire'])
    climb(p, cx, cy)
    for k, bearing in enumerate((0.0, 60.0, 120.0, 300.0)):
        b = math.radians(bearing)
        p.enemy(4, 'Spire Hunter %d' % k, cx + math.cos(b) * 5000, cy + math.sin(b) * 5000)
    for k, (x, y) in enumerate(((290.0, 45.0), (300.0, -55.0))):
        p.enemy(2, 'Spire Road %d' % k, *cm(x, y))
    p.pickup(0, 'Spire Capsule', *cm(318.0, -14.0))
    p.pickup(2, 'Spire Ammo', *cm(316.0, 4.0))


def climb(p, cx, cy):
    b = math.radians(START)
    out = (math.cos(b), math.sin(b))
    p1 = (cx + out[0] * RHO, cy + out[1] * RHO)
    foot = (p1[0] + out[0] * (INSET + 1200), p1[1] + out[1] * (INSET + 1200))
    h0 = p.g.at(*foot)
    inward = START + 180.0
    # The ramp up from the plaza to the gate: its top is 4 m up, so the platform cannot be climbed from the side.
    p.mesh('Spire Ramp 0', 'SM_CN_LightRamp', (foot[0], foot[1], h0 + 2), (0, 0, inward), 1.0, 'Spire')
    p.solids += [(foot[0] - out[0] * 600, foot[1] - out[1] * 600, 900), (p1[0], p1[1], 700)]
    tangent = (-out[1], out[0])
    for key in ('Iriel', 'IrielBase'):
        p.spots[key] = (foot[0] + tangent[0] * 550 + out[0] * 150, foot[1] + tangent[1] * 550 + out[1] * 150, START, None)
    p.light('Spire Gate Light', (p1[0], p1[1], h0 + 1300), BLUE, 6000, 2500, 'Spire')
    top = h0 + 400
    nodes = [(p1[0], p1[1], top, 1.0)]
    # The gate on the first platform's outer edge: an arch, and a leaf of light in it that sinks once the Spine burns.
    # Its 2 m deep threshold must stand wholly on the platform: at 4.2 m out (the first place) it overhung the gate ramp,
    # whose top is 3.8 m out, by 1.4 m, leaving a 40-60 cm stone face across the ramp that she could not step onto
    # (Play test, 2026-11-07: she stopped 1.7 m short of the platform). At 2.8 m its outer face meets the ramp's top.
    gx, gy = p1[0] + out[0] * 280, p1[1] + out[1] * 280
    p.mesh('Spire Gate', 'SM_CN_SpireGate', (gx, gy, top - 5), (0, 0, START), 1.0, 'Spire')
    p.rise('Spire Seal', 'SM_CN_Lattice', (gx, gy, top - 5), ',spire,', -820, (0, 0, START), (1.0, 1.15, 1.4), 160.0, 'Spire')
    theta = START
    timed = 0
    with p.behind(',spire,'):
        p.mesh('Spire Platform 1', 'SM_CN_LightPlatform', (p1[0], p1[1], top), (0, 0, START), 1.0, 'Spire')
        p.moved['Light Step'] = (p1[0] - out[0] * 150, p1[1] - out[1] * 150, top + 160)
        zone = (',spire,',)
        for index, (kind, ramps, holds, scale, label) in enumerate(CLIMB):
            x, y, z, s = nodes[-1]
            inset_out = INSET * s
            inset_in = CROWN_INSET if kind == 'crown' else INSET * scale
            length = GAP if kind == 'gap' else inset_out + 1200 * ramps + inset_in
            theta += math.degrees(2 * math.asin(length / (2 * RHO)))
            nb = math.radians(theta)
            nx, ny = cx + math.cos(nb) * RHO, cy + math.sin(nb) * RHO
            ux, uy = (nx - x) / length, (ny - y) / length
            yaw = math.degrees(math.atan2(uy, ux))
            with p.behind(*zone):
                for k in range(ramps):
                    rx, ry = x + ux * (inset_out + 1200 * k), y + uy * (inset_out + 1200 * k)
                    p.mesh('Spire Ramp %d %d' % (index + 1, k), 'SM_CN_LightRamp', (rx, ry, z + 400 * k), (0, 0, yaw), 1.0, 'Spire')
                    if holds[k] is not None:
                        lx, ly, lz = rx + ux * 600, ry + uy * 600, z + 400 * k + 185
                        if holds[k] > 0:
                            timed += 1
                            p.lattice('Spire Timed Lattice %d' % timed, (lx, ly, lz), yaw, holds[k], '', 900.0, '', folder='Spire')
                        else:
                            p.lattice('Spire First Lattice', (lx, ly, lz), yaw, 0.0, '', 800.0, '', folder='Spire')
                            p.scans['Spire Lattice'] = (lx, ly, lz + 420)
                            p.scan_zones['Spire Lattice'] = (',spire,',)
                            zone = (',spire,', ',lightstep,')
            nz = z - 60 if kind == 'gap' else z + 400 * ramps
            if kind == 'crown':
                crown(p, cx, cy, nx, ny, nz, theta)
                break
            with p.behind(*zone):
                p.mesh('Spire Platform %d' % (index + 2), 'SM_CN_LightPlatform', (nx, ny, nz), (0, 0, yaw), (scale, scale, 1.0), 'Spire')
                if scale > 1.0:
                    fight(p, nx, ny, nz)
                if index + 2 in (3, 9):
                    p.pickup(0, 'Spire Climb Capsule %d' % (index + 2), nx, ny, 120, nz)
                if index + 2 in (10, 12):
                    p.enemy(4, 'Spire High Hunter %d' % (index + 2), nx, ny, 0, nz)
            nodes.append((nx, ny, nz, scale))
    p.marks['Spire Climb Start'] = (p1[0], p1[1], top)


def fight(p, x, y, z):
    """The Echo Hunters' landing, halfway up: five hunters, and a gift that shows once they fall."""
    for k in range(5):
        a = k / 5 * 2 * math.pi
        p.enemy(4, 'Spire Landing Hunter %d' % k, x + math.cos(a) * 450, y + math.sin(a) * 450, 307, z)
    p.encounter('Spire Hunters', x, y, 307, ',cn_hunters,', text('spire_hunters', 'The hunters scatter into light. The landing is yours.'))
    p.relic('Hunters Gift', (x, y, z + 120), ',cn_huntersgift,', text('hunters_gift', 'Light gathers where the hunters fell. Divinity +40, and Physis is fully healed.'),
            ',cn_hunters,', 40.0, True, 'SM_CN_LightCache', .5)
    p.pickup(2, 'Spire Landing Ammo', x + 300, y - 300, 120, z)


def crown(p, cx, cy, x, y, top, theta):
    """The crown dais at about 60 m: IrielCrown, the Health Augmentation that also gives ,crown, (the relic's token
    holds both), and a lift of light outside it that rides down to the plaza and back once the crown is reached."""
    with p.behind(',spire,', ',lightstep,'):
        p.mesh('Spire Crown', 'SM_CN_CrownDais', (x, y, top - 100), (0, 0, theta), 1.0, 'Spire')
        inward = math.atan2(cy - y, cx - x)
        p.spots['IrielCrown'] = (x + math.cos(inward) * 450, y + math.sin(inward) * 450, math.degrees(inward) + 180, top)
        p.zones['IrielCrown'] = (',spire,', ',lightstep,')
        p.relic('Crown Augmentation', (x, y, top + 120), ',aug_hp5,,crown,',
                MESSAGES['crown'] + '~' + text('aug_hp', 'Health Augmentation absorbed. Physis gains a Health Tank, and she is whole again.'),
                '', 0.0, True, 'SM_CN_AugHealth', 1.0)
        p.light('Spire Crown Light', (x, y, top + 700), BLUE, 9000, 3000, 'Spire')
        b = math.radians(theta)
        ex, ey = cx + math.cos(b) * (RHO + 1400), cy + math.sin(b) * (RHO + 1400)
        bottom = p.g.at(ex, ey) + 90
        lift = p.spawn('BP_Platform', 'Spire Lift', (ex, ey, (top + bottom) / 2), None, 'Spire', AmpX=0.0, AmpY=0.0,
                       AmpZ=(top - bottom) / 2, Period=24.0, Need=',crown,')
        p.reskin(lift, 'SM_CN_LightPlatform')
    p.marks['Spire Crown'] = (x, y, top)
    p.marks['Spire Lift'] = (ex, ey, bottom)


def old_quarter(p):
    p.check('Old Quarter', *cm(466.0, 172.0), text('still_quarter', 'The Old Quarter. Light Step opens its lattices: caches, old puzzles and a lost Lightform child wait among the ruins.'))
    # Wisp, behind the lattices of a closed court.
    (wx, wy, wz), _ = court(p, 'Wisp Court', *cm(552.0, 262.0), 'lattice')
    for key in ('Wisp',):
        p.spots[key] = (wx, wy, 180.0, None)
        p.zones[key] = (',lightstep,',)
    p.light('Wisp Glow', (wx, wy, wz + 400), BLUE, 3000, 1400, 'Courts')
    cache(p, 1, 'Lane Cache', cm(520.0, 240.0), ',cn_cache1,')
    cache(p, 2, 'Quarter Cache', cm(430.0, 135.0), ',cn_cache2,')
    bell_lanterns(p, cm(440.0, 230.0))
    light_run(p, cm(575.0, 160.0))
    p.relic('Ledger Page Quarter', p.at(*cm(505.0, 185.0), lift=110), ',page3,', MESSAGES['page'], mesh='SM_CN_LedgerPage')
    sx, sy = cm(520.0, 115.0)
    p.enemy(6, 'Quarter Siegeframe', sx, sy, 309)
    pack(p, 'Siege Escort', sx, sy, (2, 3, 4), 309, 1100)
    p.encounter('Quarter Siegeframe', sx, sy, 309, ',cn_siege1,', text('siege1', 'The Siegeframe crashes down among the ruins. Something it guarded glints in the rubble.'))
    p.relic('Siegeframe Hoard', p.at(sx + 500, sy, 120), ',cn_siegegift1,', text('siege_gift', 'The Siegeframe guarded Divinity +100, and Physis is fully healed.'),
            ',cn_siege1,', 100.0, True, 'SM_CN_LightCache', .6)
    for label, (x, y), levels in (('Quarter Gate', (432, 196), (2, 2, 3)), ('Quarter Lane', (500, 150), (2, 3, 4)),
                                  ('Quarter East', (545, 222), (2, 3, 3)), ('Quarter North', (470, 262), (2, 2, 4)),
                                  ('Quarter Far', (595, 205), (3, 3, 4)), ('Quarter Rim', (610, 255), (2, 4))):
        pack(p, label, *cm(x, y), levels)
    p.pickup(0, 'Quarter Capsule', *cm(460.0, 165.0))
    p.pickup(1, 'Quarter Crystal', *cm(472.0, 180.0))
    p.pickup(2, 'Quarter Ammo 0', *cm(520.0, 200.0))
    p.pickup(2, 'Quarter Ammo 1', *cm(450.0, 250.0))


def cache(p, n, title, at, token):
    """A Light Cache: condensed Divinity in a court behind a lattice (a light-blue ray over it)."""
    (x, y, z), door = court(p, title + ' Court', at[0], at[1], 'lattice')
    if n == 1:
        where = door.get_actor_location()
        p.scans['Light Cache'] = (where.x, where.y, where.z + 450)
    with p.behind(',lightstep,'):
        p.relic(title, (x, y, z + 120), token, text('light_cache', 'Light Cache absorbed. Divinity +60.'), '', 60.0, False, 'SM_CN_LightCache', 1.0)
    p.light(title + ' Glow', (x, y, z + 450), BLUE, 3000, 1300, 'Courts')
    p.site(title, x, y, 2, token)


def bell_lanterns(p, at):
    """Puzzle: four bell lanterns hidden round a ruined square; each rings as it is lit, and when all four sound the
    square lifts its cache."""
    cx, cy = p.free(at[0], at[1], 900)
    tokens = []
    for k, bearing in enumerate((20.0, 115.0, 205.0, 290.0)):
        b = math.radians(bearing)
        r = 1500 + 300 * (k % 2)
        x, y = p.free(cx + math.cos(b) * r, cy + math.sin(b) * r, 250)
        tokens.append(',cn_bell%d,' % (k + 1))
        p.switch('Bell Lantern %d' % k, (x, y, p.g.at(x, y) - 5), bearing + 180, 'SM_CN_Lamp', True, folder='Puzzles', Need='', Give=tokens[-1],
                 Denied='', Done=text('bell_lit', 'The lantern lights, and its bell rings low across the ruins.'))
        p.light('Bell Lantern Glow %d' % k, (x, y, p.g.at(x, y) + 480), GOLD, 1500, 700, 'Puzzles')
    p.require('Bell Chord', p.at(cx, cy, 400), tokens, ',cn_bells,', text('bells', 'All four bells sound one chord, and the square lifts its old cache into the light.'))
    p.rise('Bell Dais', 'SM_CN_LightPlatform', p.at(cx, cy, -120), ',cn_bells,', 150, (0, 0, 0), (.4, .4, 1.0), 90.0, 'Puzzles')
    p.relic('Bell Cache', p.at(cx, cy, 150), ',cn_bellgift,', text('bell_gift', 'The square kept its cache for whoever lit it whole. Divinity +80.'),
            ',cn_bells,', 80.0, False, 'SM_CN_LightCache', .6)
    p.solids.append((cx, cy, 500))
    p.site('The Bell Lanterns', cx, cy, 0, ',cn_bellgift,')


def light_run(p, at):
    """Puzzle: a walled lane of three timed lattices; each opens for a few breaths as she steps, and the cache waits
    at the closed end. The lane runs along x, the contour of the slope, so every lattice stands level."""
    x0, y0 = p.free(at[0] - 2000, at[1], 900)
    for k in range(4):
        for side in (-1, 1):
            x, y = x0 + 500 + k * 1000, y0 + side * 330
            p.mesh('Light Run Wall %d %d' % (k, side), 'SM_CN_TerraceWall', (x, y, p.low(x, y, ((-500, 0), (500, 0)), (1, 0, 0, 1)) - 30),
                   (0, 0, 90.0 * side), (1.0, 1000 / 1200, 2.0), 'Puzzles')
    ex = x0 + 4100
    p.mesh('Light Run End', 'SM_CN_TerraceWall', (ex, y0, p.g.at(ex, y0) - 30), (0, 0, 0), (1.0, .6, 2.0), 'Puzzles')
    zone = ()
    for k in range(3):
        x = x0 + 1000 * (k + 1)
        with p.behind(*zone):
            p.lattice('Light Run Lattice %d' % k, (x, y0, p.low(x, y0, ((0, -300), (0, 300)), (1, 0, 0, 1)) - 15), 0.0, 3.0, '', 650.0, '', folder='Puzzles')
        zone = (',lightstep,',)
    with p.behind(',lightstep,'):
        p.relic('Light Run Cache', p.at(x0 + 3700, y0, 120), ',cn_rungift,', text('run_gift', 'The end of the light run: Divinity +80, and Physis is fully healed.'),
                '', 80.0, True, 'SM_CN_LightCache', .6)
    for k in range(4):
        p.solids.append((x0 + 500 + k * 1000, y0, 700))
    p.light('Light Run Glow', p.at(x0 + 2000, y0, 600), GOLD, 3000, 2200, 'Puzzles')
    p.site('The Light Run', x0 + 2000, y0, 0, ',cn_rungift,')


# The listeners' four stones, tallest first (height scale); positions round the terrace do not follow the order.
STONES = ((2.4, 200.0), (1.9, 20.0), (1.4, 290.0), (0.9, 110.0))
VAULTS = (('Vault of Echoes', (330.0, -235.0), ',trace,', ',cn_vault1,'), ('Vault of the Chord', (470.0, -262.0), ',resonance,', ',cn_vault2,'),
          ('Vault of Discord', (545.0, -190.0), ',dissonance,', ',cn_vault3,'))


def orchard(p):
    # Puzzle: the Listeners' Stones (the scan on the terrace gives the order: tallest to shortest).
    lx, ly = cm(410.0, -232.0)
    for rank, (height, bearing) in enumerate(STONES):
        b = math.radians(bearing)
        x, y = p.free(lx + math.cos(b) * 900, ly + math.sin(b) * 900, 200)
        last = rank == len(STONES) - 1
        stone = p.switch('Listener Stone %d' % rank, (x, y, p.g.at(x, y) - 30), bearing, 'SM_CV_RockWhite', True, (.8, .8, height), 'Puzzles',
                         Need='' if rank == 0 else ',cn_stone%d,' % rank, Give=',cn_stones,' if last else ',cn_stone%d,' % (rank + 1),
                         Denied=text('stone_denied', 'The stone stays quiet. The listeners wake the tallest first, as the Serene wake.'),
                         Done=text('stones_done', 'The last stone wakes, and the four hum one note under the drum\'s turning.') if last else
                         text('stone_wake', 'The stone wakes with a low note.'))
        p.light('Listener Stone Glow %d' % rank, (x, y, p.g.at(x, y) + 250 * height + 150), BLUE, 1200, 600, 'Puzzles')
    p.relic('Listeners Gift', p.at(lx, ly, 120), ',cn_stonegift,', text('stone_gift', 'The listeners left Divinity +80 at the stones\' centre, and Physis is fully healed.'),
            ',cn_stones,', 80.0, True, 'SM_CN_LightCache', .6)
    p.solids.append((lx, ly, 1100))
    p.site("The Listeners' Stones", lx, ly, 0, ',cn_stonegift,')
    for title, (x, y), ability, token in VAULTS:
        vault(p, title, cm(x, y), ability, token)
    cache(p, 3, 'Orchard Cache', cm(360.0, -150.0), ',cn_cache3,')
    sx, sy = cm(520.0, -120.0)
    p.enemy(6, 'Orchard Siegeframe', sx, sy, 310)
    pack(p, 'Orchard Escort', sx, sy, (2, 3, 4), 310, 1100)
    p.encounter('Orchard Siegeframe', sx, sy, 310, ',cn_siege2,', text('siege2', 'The Siegeframe falls among the orchard rows.'))
    p.relic('Orchard Hoard', p.at(sx - 500, sy, 120), ',cn_siegegift2,', text('siege_gift', 'The Siegeframe guarded Divinity +100, and Physis is fully healed.'),
            ',cn_siege2,', 100.0, True, 'SM_CN_LightCache', .6)
    for label, (x, y), levels in (('Orchard Gate', (420, -128), (2, 2, 3)), ('Orchard West', (335, -190), (2, 3, 3)),
                                  ('Orchard Rows', (455, -205), (2, 3, 4)), ('Orchard Terrace', (385, -262), (2, 2, 4)),
                                  ('Orchard Far', (590, -240), (3, 4))):
        pack(p, label, *cm(x, y), levels)
    p.pickup(0, 'Orchard Capsule 0', *cm(420.0, -140.0))
    p.pickup(0, 'Orchard Capsule 1', *cm(500.0, -220.0))
    p.pickup(1, 'Orchard Crystal', *cm(400.0, -215.0))
    p.pickup(2, 'Orchard Ammo', *cm(440.0, -180.0))


def vault(p, title, at, ability, token):
    """A sealed vault of the Wise: a court whose door opens only to an ability from a later level (a red ray, a
    'Sealed Vault' scan). Its gift is shown, out of reach, until then."""
    opened = token[:-1] + '_open,'
    (x, y, z), door = court(p, title, at[0], at[1], 'vault', opened, ability, message=text('vault_open', 'The vault remembers what opens it, and opens.'))
    where = door.get_actor_location()
    category, name, body = CONCLAVE_GATES[0]
    p.scan(category, name, body, (where.x, where.y, where.z + 450), True)
    with p.behind(ability):
        p.relic(title + ' Gift', (x, y, z + 130), token, text('vault_gift', 'The vault\'s gift: Divinity +120, and Physis is fully healed.'), opened, 120.0, True,
                'SM_CN_LightCache', .8, True, text('vault_locked', 'The vault still holds it. What opens it is learned elsewhere.'))
    p.light(title + ' Sigil', (where.x, where.y, where.z + 500), RED, 2500, 1100, 'Courts')
    p.site(title, x, y, 1, token)


DOCK_LATTICE = 4800.0
DOCK_BARRICADE = 4200.0


def docks(p):
    dx, dy = cm(*plan.DOCKS_ARENA)
    p.check('Docks', *cm(626.0, 6.0), text('still_docks', 'The Spindle Docks. Light Step through the lattice wall, Settle the barricades and stop the AL Shepherd.'))
    for label, mesh, (x, y), yaw, solid in (('Wrecked Freighter', 'SM_CN_Freighter', (735.0, -105.0), 15.0, 3200),
                                            ('Ship Cradle', 'SM_CN_Cradle', (742.0, 92.0), -12.0, 1700),
                                            ('Spindle Lift', 'SM_CN_Lift', (778.0, 0.0), 0.0, 600)):
        x, y = cm(x, y)
        p.landmark(label, mesh, (x, y, p.g.at(x, y) - 30), yaw, 1.0, solid, 'Docks')
    for k, (r, bearing) in enumerate(((5800, 40), (6000, 140), (5600, 220), (6200, 320), (2600, 70), (2400, 160), (2700, 250), (2300, 340))):
        b = math.radians(bearing)
        x, y = dx + math.cos(b) * r, dy + math.sin(b) * r
        p.mesh('Dock Crate %d' % k, 'SM_CN_Crate', (x, y, p.g.at(x, y) - 10), (0, 0, bearing * 1.7), 1.0 + .25 * (k % 3), 'Docks', solid=250)
    # The nest: a wall of lattices the swarm grew from the Lightforms' light, and inside it a ring of barricades.
    ring(p, 'Dock Lattice', dx, dy, DOCK_LATTICE, 590.0,
         lambda label, x, y, yaw, width: p.lattice(label, (x, y, p.g.at(x, y) - 15), yaw, 0.0, ',docksgate,', 900.0, MESSAGES['docksgate'], folder='Docks'))
    with p.behind(',lightstep,'):
        ring(p, 'Dock', dx, dy, DOCK_BARRICADE, 760.0, lambda label, x, y, yaw, width: p.barrier(label, x, y, yaw, '', width, folder='Docks'))
    with p.behind(',lightstep,', ',settle,'):
        p.enemy(7, 'AL Shepherd', dx, dy, 308)
        for k, (level, bearing, r) in enumerate(((5, 90, 1500), (5, 270, 1500), (3, 0, 2000), (3, 180, 2000), (4, 45, 2500), (4, 225, 2500))):
            b = math.radians(bearing)
            p.enemy(level, 'Shepherd Guard %d' % k, dx + math.cos(b) * r, dy + math.sin(b) * r, 308)
        p.encounter('Shepherd', dx, dy, 308, ',shepherd,', MESSAGES['shepherd'], QUEST_KAIROS)
        for k, bearing in enumerate((120.0, 300.0)):
            b = math.radians(bearing)
            p.pickup(0, 'Nest Capsule %d' % k, dx + math.cos(b) * 3300, dy + math.sin(b) * 3300)
    for k, bearing in enumerate((0.0, 120.0, 240.0)):
        b = math.radians(bearing)
        p.light('Nest Light %d' % k, p.at(dx + math.cos(b) * 2000, dy + math.sin(b) * 2000, 700), RED, 6000, 3000, 'Docks')
    for label, (x, y), levels in (('Dock Approach West', (600, -62), (3, 4, 5)), ('Dock Approach East', (600, 62), (3, 3, 4)),
                                  ('Dock Freighter', (650, -112), (3, 4, 5)), ('Dock Cradle', (650, 112), (3, 4, 4)),
                                  ('Dock Road', (585, 0), (4, 5))):
        pack(p, label, *cm(x, y), levels, 0, 800)
    qx, qy = cm(626.0, 6.0)
    for k, (kind, ox, oy) in enumerate(((0, 600, 500), (0, 600, -500), (2, -500, 600), (2, -500, -600), (1, 0, 900))):
        p.pickup(kind, 'Docks Supply %d' % k, qx + ox, qy + oy)


def roads(p):
    """Patrols on the roads and the open land between the districts and the Spire (levels 2-3)."""
    for label, (x, y), levels in (('West Road South', (120, -178), (2, 3)), ('West Road North', (235, -105), (2, 3)),
                                  ('East Road South', (140, 178), (2, 3)), ('East Road North', (250, 105), (2, 3)),
                                  ('Lake Road', (210, 42), (2, 2)), ('Midfield West', (150, -60), (2, 3)),
                                  ('Midfield East', (165, 110), (2, 3))):
        pack(p, label, *cm(x, y), levels, 0, 900)


# ---------------------------------------------------------------- passes over the whole level

# Lore scans that do not stand free: the anchors' and cable locks' ride on their targets (Place.target), the relics'
# on BP_Relic (center_logic.py RELIC_SCANS maps each relic's token to its row).
ATTACHED = ('AL Anchor', 'Cable Lock', 'The Crown Augmentation', "Tamsin's Kite", 'A Ledger Page', 'The Starlace Seed Pod',
            "Halden-7's Memory Core")


def scans(p):
    for category, title, body, (x, y, z), important in CONCLAVE_SCANS:
        if title in ATTACHED:
            continue
        place = p.scans.get(title) or (x * M, y * M, None if z is None else z * M)
        with p.behind(*p.scan_zones.get(title, ())):
            p.scan(category, title, body, place, important)


def voices(p):
    """A BP_LogVoice for every Logbook title (Divinity's voice) and for the arrival line the director narrates."""
    for category, title, body in conclave_entries() + [('Story',) + tuple(ARRIVAL_LINE)]:
        p.spawn('BP_LogVoice', 'Voice ' + title, VOICE_SPOT, None, 'Voices', Title=title, Voice=asset(VOICES + '/' + voice_name(title)),
                Image=asset('/Game/UI/Log/' + image_name(title), True))


def tutorials(p):
    for index, (message, (x, y), scale) in enumerate(CONCLAVE_TUTORIALS):
        place = p.moved.get(message.split(':')[0]) or p.at(x * M, y * M, 160)
        p.spawn('BP_TutorialTrigger', 'Tutorial %02d' % (index + 1), place, scale, 'Tutorial', Message=message)


# Divinity Rays over every optional puzzle (gold), Light Cache (light blue) and sealed vault (red): kind, the
# Conclave's instance of the Center's M_DivinityRay, width (cm). They rise about 600 m and stop 20 m short of the
# Spine, which runs along the axis 706 m up.
RAY_KINDS = {0: ('MI_CNRay_Puzzle', 900.0), 1: ('MI_CNRay_Vault', 800.0), 2: ('MI_CNRay_Cache', 650.0)}
RAY_HEIGHT = 60000.0


def divinity_rays(p):
    box = asset('/Engine/BasicShapes/Cylinder').get_bounding_box()
    for name, x, y, kind, token in p.sites:
        look_name, width = RAY_KINDS[kind]
        material = asset(MATS + '/' + look_name)
        if material is None:
            raise RuntimeError('Run conclave:materials first: no %s' % look_name)
        foot = max(p.g.at(x, y), 0.0) - 300
        height = min(RAY_HEIGHT, AXIS - 2000 - foot)
        sz, sxy = height / (box.max.z - box.min.z), width / (box.max.x - box.min.x)
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
    return len(p.sites)


def sound_scape(p):
    """The drum's hum everywhere, and the Commons, the Foundry and the water where they are."""
    def ambient(label, sound, place, radius, volume):
        actor = sub().spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(*place))
        actor.set_actor_label('Scene Sound ' + label)
        actor.set_folder_path('Conclave/Sound')
        comp = actor.get_component_by_class(unreal.AudioComponent)
        comp.set_editor_property('sound', asset(AUDIO + '/' + sound))
        comp.set_editor_property('volume_multiplier', volume)
        if radius:
            comp.set_editor_property('override_attenuation', True)
            settings = comp.get_editor_property('attenuation_overrides')
            settings.set_editor_property('falloff_distance', radius)
            settings.set_editor_property('attenuation_shape_extents', unreal.Vector(radius * .3, 0, 0))
            comp.set_editor_property('attenuation_overrides', settings)
        else:
            comp.set_editor_property('allow_spatialization', False)
        return p.note(actor)
    ambient('Drum', 'S_Amb_Drum', (0, 0, 0), 0, .5)
    ambient('Commons', 'S_Amb_Commons', p.at(*cm(*plan.COMMONS_PLAZA), lift=400), 16000, .85)
    ambient('Foundry', 'S_Amb_Foundry', p.at(*cm(-40.0, 215.0), lift=400), 14000, .8)
    ambient('Water', 'S_Amb_Water', (plan.LAKE[0] * M, plan.LAKE[1] * M, 300), 13000, .7)


def residents(p):
    """What the level must hold once: BP_Awakening (TestArrival off) marks an open-world level for the shared
    graphs, BP_ConclaveDirector runs the Conclave's own, and a PlayerStart on the arrival. The level build may have
    placed them already (they are not Scene actors, so clear() leaves them)."""
    have = {actor.get_class().get_name() for actor in sub().get_all_level_actors()}
    wx, wy = cm(*plan.WELL)
    if 'BP_Awakening_C' not in have:
        p.spawn('BP_Awakening', 'Awakening', (wx, wy, p.g.at(wx, wy) + 300), None, 'Directors', TestArrival=False)
    if 'BP_ConclaveDirector_C' not in have:
        if unreal.EditorAssetLibrary.does_asset_exist(game.BLUEPRINTS + '/BP_ConclaveDirector'):
            p.spawn('BP_ConclaveDirector', 'Conclave Director', (wx, wy, p.g.at(wx, wy) + 400), None, 'Directors')
        else:
            unreal.log_warning('Conclave scenario: BP_ConclaveDirector does not exist yet; run Tools/blueprint_logic/conclave_logic.py, then this again')
    if 'PlayerStart' not in have:
        start = sub().spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(*p.marks['Arrival']), unreal.Rotator(0, 0, 0))
        start.set_actor_label('Scene Player Start')
        start.set_folder_path('Conclave/Directors')
        p.note(start)


def arrival_off():
    """Every BP_Awakening with TestArrival off before a save (an editor test switch that must never be saved on)."""
    count = 0
    for actor in sub().get_all_level_actors():
        if actor.get_class().get_name() == 'BP_Awakening_C':
            actor.set_editor_property('TestArrival', False)
            count += 1
    return count


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def open_level(path):
    """Opens a map unless it is the open one, refusing while any open map has unsaved changes."""
    world = editor_world()
    current = world.get_path_name().split('.')[0] if world else ''
    if current == path:
        return
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    # Never save another session's or the author's unsaved edits on the way (load_level does not prompt, so it would
    # silently drop them, and saving would keep them unasked): refuse instead.
    dirty = [pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them before opening %s' % (', '.join(dirty), path))
    if not levels.load_level(path):
        raise RuntimeError('Could not open ' + path)


def save_level(path):
    """Saves the open map in place (save_map onto a loaded map is a Save As that fails behind a modal dialog)."""
    world = editor_world()
    if world.get_path_name().split('.')[0] != path:
        raise RuntimeError('Refusing to save: %s is open, not %s' % (world.get_path_name(), path))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


def clear():
    for actor in sub().get_all_level_actors():
        if actor.get_actor_label().startswith('Scene ') or isinstance(actor, unreal.TextRenderActor):
            sub().destroy_actor(actor)


def place(ground=None):
    global LAST
    MISSING.clear()
    open_level(LEVEL)
    clear()
    footprints, scatter = town()
    p = Place(ground or Ground(), footprints, scatter)
    LAST = p
    wellspring(p)
    commons(p)
    terraces(p)
    reservoir(p)
    foundry(p)
    spire(p)
    old_quarter(p)
    orchard(p)
    docks(p)
    roads(p)
    cache(p, 4, 'Terrace Cache', cm(45.0, -250.0), ',cn_cache4,')
    # The Ledger of Names: three pages blew out of the Archive, one each to the Terraces, the Reservoir, the Old Quarter.
    p.require('Ledger Pages', p.at(*cm(*plan.ARCHIVE), lift=600), (',page1,', ',page2,', ',page3,'), ',pages,', MESSAGES['pages'])
    people(p)
    scans(p)
    voices(p)
    tutorials(p)
    rays = divinity_rays(p)
    sound_scape(p)
    residents(p)
    arrival_off()
    save_level(LEVEL)
    combatants = [actor for actor, _, _ in p.log if actor.get_class().get_name() == 'BP_TrainingDrone_C' and not actor.get_editor_property('Static')]
    return {'level': LEVEL, 'placed': p.count, 'combatants': len(combatants), 'rays': rays, 'cast': p.cast_source or 'none (bare Mannequins)',
            'people': p.misfits, 'unset': p.unset,
            'missing_assets': sorted(MISSING)[:40], 'missing_count': len(MISSING), 'houses_checked': sum(len(v) for v in p.town.values()),
            'marks': {name: [round(v) for v in place_] for name, place_ in p.marks.items()}}


# ---------------------------------------------------------------- the Center's temple current

def portal():
    """The current to the Conclave in the Center's sanctum, shown once Mend is learned: a targeted spawn into
    L_CenterOfTheUniverse that replaces only its own earlier actors (labels 'Conclave Current...'), so the Center's
    scenario is neither re-run nor cleared. The labels never start with 'Scene ' or 'Cine ', which the Center's
    clear() and cinema() delete (Center session, 2026-11-06), so a Center scenario re-run leaves them alone. It also
    sets the placed Heartbloom pedestal's Done text to HEARTBLOOM_DONE, the same text physis_center_scenario.py holds."""
    open_level(CENTER_LEVEL)
    dirty = [pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:  # the Center was already open with someone's unsaved edits: never save them along with the portal
        raise RuntimeError('unsaved changes in %s: save or discard them before conclave:portal' % ', '.join(dirty))
    actors = sub()
    removed = 0
    pedestal = False
    for actor in actors.get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith(('Conclave Current', 'Scene Conclave Current')):  # the second: an earlier version's labels
            actors.destroy_actor(actor)
            removed += 1
        elif label == 'Scene Heartbloom Pedestal':
            # Set as is: props() would re-wrap it, and its four lines are agreed word for word with the Center.
            actor.set_editor_property('Done', HEARTBLOOM_DONE)
            pedestal = True

    def spawn(name, suffix, place, scale=None, **values):
        actor = actors.spawn_actor_from_class(cls(name), unreal.Vector(*place))
        actor.set_actor_label('Conclave Current' + suffix)
        actor.set_folder_path('Center/Conclave')
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))
        if values:
            props(actor, **values)
        return actor

    spawn('BP_Current', '', PORTAL, Need=',mend,', Dest=1, Radius=180.0)
    # No tutorial strip or scan tag here: neither could be hidden before Mend (the tag is found by distance, facing and
    # line of sight alone), and the strip, crossed on the way to the current, replaced the Heartbloom's Done text,
    # which already says where the current is. The current sets the quest itself (BP_Current, ,cn_currenthint,); its
    # Logbook entry and voice are at the Conclave's Wellspring current.
    back = actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*RETURN))
    back.set_actor_label('Conclave Current Return')
    back.set_folder_path('Center/Conclave')
    back.set_editor_property('tags', ['ConclaveReturn'])
    awakenings = arrival_off()
    save_level(CENTER_LEVEL)
    return {'level': CENTER_LEVEL, 'current': [round(v) for v in PORTAL], 'return': [round(v) for v in RETURN], 'removed': removed,
            'awakenings_off': awakenings, 'heartbloom_text_set': pedestal}
