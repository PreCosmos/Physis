"""Gameplay for level 4, Earth: the Wounded Grove (GAME_ROADMAP.md "Level 4", Tools/grove/DESIGN_NOTES.md): Still
Points, the people, the thornroot wall, the Graft, link anchors and flows, the Weir and the Relay, the Rift, the
Deeproot Array and the Warden, side requests, Old Town's vault, seed caches, the Hedge by region, Divinity Rays,
tutorials and voices. Run through `grove:scenario` (place) and `grove:portal` (the Center's temple current to Earth, a
targeted spawn that leaves the Center's own scenario alone).

Positions are plan metres (physis_grove_plan: x north, y east); Place's methods take centimetres. Everything placed
here is labelled 'Scene ...' in the outliner folder GroveScene (the level build owns the folder Grove), so a rerun
replaces only its own actors. Text comes from physis_grove_lore.

Progress tokens (BP_Physis Flags):
  ,grove, ,at_grove,   arrived / saves load here        ,tess,  Thessaly met        ,resonance,  the Graft
  ,gr_road,  the road patrol     ,gr_weir, ,gr_relay,  the guards over each source   ,water, ,power,  the lifelines
  ,gr_first_w, ,gr_first_e,  which lifeline came first (BP_GroveDirector)            ,arraygate,  both lifelines
  ,gr_forecourt,  the gate's guard    ,gr_court,  the Root Court's    ,stabilized,  the core coupling
  ,warden,  the Warden falls     ,voss,  the Director, in person      ,grove_done,  Thessaly afterwards
  side requests ,burr, ,pin, ,wick, ,can1, ,can2, ,can3, ,cans,;  vault ,gr_vault,;  caches ,gr_cache1-5, ,gr_falls,
  vents ,gr_vent1-4, (closed by Settle);  augmentations ,aug_hp7, ,aug_katana5, ,aug_pistol4, ,aug_defense5, ,aug_agility5,
Encounter rooms 401-499, each once; loose packs are room 0. Tags for BP_GroveDirector: GroveBlight (hidden once the
Warden falls), GroveBloom, GroveWater, GrovePower. Markers for travel: TargetPoint tags GroveArrival (here) and
GroveReturn (in the Center, by portal()).

Link anchors are placed lifted: the knot hangs 1.5 m over where she lands (Perch brings her down), so railings,
parapets and platform edges never hide its seed from below. routes() traces every hop of every chain in the editor
world and lists the ones a wall or a trunk blocks; the report's 'blocked' must come out empty.
"""
import math

import unreal

import physis_gameplay_tools as game
import physis_grove_lore as lore
import physis_grove_plan as plan
from physis_aaa_tools import wrap_text
from physis_lore import image_name, voice_name

GROVE = '/Game/Grove'
MESHES = GROVE + '/Meshes'
SCANS = GROVE + '/Scans'
CONCLAVE = '/Game/Conclave/Meshes'
VOICES = GROVE + '/Audio/Voice'
LEVEL = '/Game/Levels/L_Grove'
CENTER_LEVEL = '/Game/Levels/L_CenterOfTheUniverse'
FOLDER = 'GroveScene'
M = 100.0
VOICE_SPOT = (0.0, 0.0, -50000.0)
KEEP = unreal.AttachmentRule.KEEP_WORLD
STILL_UNTIL = ',warden,'

# Light colours (linear): resonance, the Just's amber, thornroot's magenta, a Still Point's pale blue.
LINK = (.25, 1.0, .7)
AMBER = (1.0, .6, .2)
MAGENTA = (1.0, .15, .6)
BLUE = (.6, .8, 1.0)

# The Center's temple (physis_center_scenario TEMPLE, sanctum floor): Earth's current stands 16 m east of the
# Heartbloom's pedestal (the Conclave's stands 16 m north), and she comes back 5 m short of it.
TEMPLE = (76000.0, 0.0)
SANCTUM = 3400.0 + 600.0
PORTAL = (TEMPLE[0], TEMPLE[1] + 1600.0, SANCTUM + 35.0)
RETURN = (TEMPLE[0], TEMPLE[1] + 1100.0, SANCTUM + 120.0)

MISSING = set()
WRAPPED = ('Message', 'Done', 'Denied', 'Objective', 'ScanText', 'NextGoal', 'Note', 'Quest', 'Locked')


def cm(x, y):
    return x * M, y * M


def wrap(message):
    return '~'.join(wrap_text(part) for part in message.split('~')) if message else message


def props(actor, **values):
    for key, value in values.items():
        actor.set_editor_property(key, wrap(value) if key in WRAPPED and isinstance(value, str) else value)


def asset(path, optional=False):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    if not optional:
        MISSING.add(path)
    return None


def mesh_asset(name):
    """A mesh by its name alone: the grove's own (SM_GN_, SM_GV_, SM_GE_, SM_GP_, SM_GT_), a scan (SM_GS_) or one of
    the Conclave's shared pieces (SM_CN_, SM_CP_)."""
    if name.startswith('/'):
        return asset(name)
    if name.startswith('SM_GS_'):
        return asset(SCANS + '/' + name)
    if name.startswith(('SM_CN_', 'SM_CP_')):
        return asset(CONCLAVE + '/' + name)
    return asset(MESHES + '/' + name)


def cls(name):
    blueprint = asset(game.BLUEPRINTS + '/' + name)
    if blueprint is None:
        raise RuntimeError('%s is missing: run grove:blueprints and Tools/blueprint_logic/grove_logic.py first' % name)
    return blueprint.generated_class()


def sub():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def component(actor, name):
    for part in actor.get_components_by_class(unreal.ActorComponent):
        if part.get_name() == name:
            return part
    return None


def turned(dx, dy, yaw):
    """A local offset (dx forward, dy right) turned by yaw degrees."""
    a = math.radians(yaw)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


# ---------------------------------------------------------------- placing

class Place:
    def __init__(self, ground):
        self.g = ground
        self.count = 0
        self.solids = []   # (x, y, radius) cm: set pieces that packs and pickups keep clear of
        self.stills = []   # Still Points (x, y) cm: no ground enemy within 30 m
        self.sites = []    # (title, x, y, kind, token): a Divinity Ray over each (0 puzzle, 2 cache)
        self.marks = {}
        self.hops = []     # (label, from point cm, node actor): every link hop, traced by routes()
        self.flows = []    # (label, node, node): each leg of a flow, whose thread must not be cut by what stands between
        self.unset = []
        self.enemies = 0

    def note(self, actor):
        self.count += 1
        return actor

    # -- primitives (cm) ---------------------------------------------------------------
    def spawn(self, name, label, place, scale=None, folder='Scenario', **values):
        actor = sub().spawn_actor_from_class(cls(name), unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path(FOLDER + '/' + folder)
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))
        if values:
            props(actor, **values)
        return self.note(actor)

    def mesh(self, label, mesh, place, yaw=0.0, scale=1.0, folder='Scenario', collide=True, solid=0.0, shadow=True, tags=(),
             roll=0.0, pitch=0.0):
        actor = sub().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place), unreal.Rotator(roll, pitch, yaw))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path(FOLDER + '/' + folder)
        part = actor.static_mesh_component
        part.set_static_mesh(mesh_asset(mesh))
        part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
        if not shadow:
            part.set_editor_property('cast_shadow', False)
        scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        actor.set_actor_scale3d(unreal.Vector(*scale))
        if tags:
            actor.set_editor_property('tags', list(tags))
        if solid:
            self.solids.append((place[0], place[1], solid))
        return self.note(actor)

    def light(self, label, place, colour, intensity, radius, folder='Lights', tags=()):
        actor = sub().spawn_actor_from_class(unreal.PointLight, unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path(FOLDER + '/' + folder)
        comp = actor.get_component_by_class(unreal.PointLightComponent)
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_light_color(unreal.LinearColor(colour[0], colour[1], colour[2], 1))
        comp.set_editor_property('intensity', float(intensity))
        comp.set_editor_property('attenuation_radius', float(radius))
        comp.set_cast_shadows(False)
        if tags:
            actor.set_editor_property('tags', list(tags))
        return self.note(actor)

    def marker(self, label, place, tag, folder):
        actor = sub().spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path(FOLDER + '/' + folder)
        actor.set_editor_property('tags', [tag])
        return self.note(actor)

    def floor(self, x, y):
        """Ground height (cm), or the lake's surface over the lake."""
        return max(self.g.at(x, y), 0.0)

    def at(self, x, y, lift=0.0):
        return (x, y, self.floor(x, y) + lift)

    def ok(self, x, y, clear, still):
        if plan.rim(x / M, y / M) > .9 or plan.in_lake(x / M, y / M, 3.0) or plan.in_gully(x / M, y / M, 3.0) or plan.in_rift(x / M, y / M, 3.0):
            return False
        if any(math.hypot(x - sx, y - sy) < r + clear for sx, sy, r in self.solids):
            return False
        return not (still and any(math.hypot(x - sx, y - sy) < still for sx, sy in self.stills))

    def free(self, x, y, clear=300.0, still=0.0, reach=5000):
        """The nearest spot to (x, y) that is dry, out of the gorges, `clear` cm from every set piece and `still` cm
        from every Still Point."""
        if self.ok(x, y, clear, still):
            return x, y
        for r in range(150, reach + 1, 150):
            n = max(8, int(2 * math.pi * r / 150))
            for k in range(n):
                a = (k + .5 * ((r // 150) % 2)) / n * 2 * math.pi
                px, py = x + math.cos(a) * r, y + math.sin(a) * r
                if self.ok(px, py, clear, still):
                    return px, py
        unreal.log_warning('Grove scenario: no free spot near (%d, %d)' % (x, y))
        return x, y

    def reskin(self, actor, mesh, material=None):
        """A shared actor wearing a grove mesh: its first mesh part becomes `mesh`, the others go (BP_TrainingDrone's
        'Ward' plate is never taken for the body and is left as it is)."""
        parts = [part for part in actor.get_components_by_class(unreal.StaticMeshComponent) if part.get_name().split('_GEN')[0] != 'Ward']
        for index, part in enumerate(parts):
            if index == 0:
                if mesh:
                    part.set_static_mesh(mesh_asset(mesh))
                    for slot in range(part.get_num_materials()):
                        part.set_material(slot, None)   # the mesh's own materials, not the Blueprint's override
                if material:
                    part.set_material(0, material)
            else:
                part.set_visibility(False)
                part.set_collision_profile_name('NoCollision')
        return parts[0] if parts else None

    # -- gameplay pieces ---------------------------------------------------------------
    def check(self, label, x, y, objective, radius=700.0, z=None):
        place = (x, y, (self.floor(x, y) if z is None else z) + 110)
        actor = self.spawn('BP_Checkpoint', 'Still Point ' + label, place, folder='Still Points', Radius=radius, Objective=objective)
        actor.set_editor_property('Until', STILL_UNTIL)
        self.mesh('Still Point Ring ' + label, 'SM_CN_StillPoint', (x, y, place[2] - 115), 0, 1.0, 'Still Points')
        self.light('Still Point Glow ' + label, (x, y, place[2] + 190), BLUE, 2400, 900, 'Still Points')
        self.stills.append((x, y))
        self.marks['Still Point ' + label] = place
        self.pickup(0, label + ' Capsule', x + 420, y - 260, z)
        self.pickup(1, label + ' Crystal', x - 300, y + 420, z)
        return actor

    def scan(self, category, title, body, place, important, folder='Scans'):
        x, y, z = place
        z = self.floor(x, y) + 150 if z is None else z
        tag = self.spawn('BP_ScanTarget', 'Story ' + title, (x, y, z), folder=folder, ScanText=body, ScanCategory=category, ScanTitle=title,
                         ScanImportant=important)
        game.hide_scan(tag)
        return tag

    def tag(self, actor, entry, place, label, folder='Enemies'):
        category, title, body = entry
        tag = self.spawn('BP_ScanTarget', 'Tag ' + label, (place[0], place[1], place[2] + 70), folder=folder, ScanCategory=category,
                         ScanTitle=title, ScanText=body, ScanImportant=True)
        game.hide_scan(tag)
        tag.attach_to_actor(actor, 'None', KEEP, KEEP, KEEP, False)
        return tag

    def switch(self, label, place, yaw=0.0, mesh=None, solid=False, scale=None, folder='Switches', **values):
        actor = self.spawn('BP_Switch', label, place, None, folder, **values)
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = self.reskin(actor, mesh)
        if part:
            part.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))
        return actor

    def relic(self, label, place, token, message, need='', divinity=0.0, heal=False, mesh='SM_CN_LightCache', scale=1.0, folder='Items'):
        """BP_Relic: walked into (170 cm from her centre) it gives `token` (one or more)."""
        actor = self.spawn('BP_Relic', label, place, None, folder, Token=token, Need=need, Message=message, Divinity=float(divinity), Heal=heal)
        self.reskin(actor, mesh)
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        return actor

    def thorn(self, label, x, y, yaw, give='', folder='Thornroot'):
        """BP_SettleBarrier as a thornroot wall (SM_GN_ThornWall: 8 m along its local y), sunk 40 cm."""
        actor = self.spawn('BP_SettleBarrier', 'Thorn Wall ' + label, (x, y, self.g.at(x, y) - 40), None, folder, Give=give)
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = self.reskin(actor, 'SM_GN_ThornWall')
        if part:
            part.set_collision_profile_name('BlockAll')
        return actor

    def rise(self, label, mesh, start, need, lift, yaw=0.0, scale=1.0, speed=150.0, folder='Scenario'):
        """BP_Rise standing at `start` until `need` is held, then sliding `lift` cm (negative sinks it)."""
        actor = self.spawn('BP_Rise', label, start, None, folder, Need=need, Lift=float(lift), Speed=float(speed))
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = self.reskin(actor, mesh)
        if part:
            part.set_collision_profile_name('BlockAll')
        scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
        actor.set_actor_scale3d(unreal.Vector(*scale))
        return actor

    def enemy(self, level, label, x, y, room=0, z=None):
        """A Hedge machine of GROVE_ENEMIES[level] with its Logbook tag. On the ground it is kept 30 m from Still
        Points and clear of set pieces; z (a deck's or a roof's top, cm) puts it over something built."""
        mesh, health, scale, hover, entry, kind = lore.GROVE_ENEMIES[level]
        if z is None:
            x, y = self.free(x, y, 400.0, 3000.0)
            base = self.floor(x, y)
        else:
            base = z
        place = (x, y, base + hover)
        actor = self.spawn('BP_TrainingDrone', 'Enemy L%d %s' % (level, label), place, (scale, scale, scale), 'Enemies', RoomId=room, Boss=False,
                           Health=health)
        actor.set_editor_property('Static', False)
        try:
            actor.set_editor_property('EnemyKind', kind)
        except Exception:
            self.unset.append((label, 'EnemyKind'))
        self.reskin(actor, mesh)
        self.tag(actor, entry, place, label)
        self.enemies += 1
        return actor

    def target(self, label, mesh, place, room, health, scale=1.0, entry=None, yaw=0.0, folder='Targets', shot_only=False):
        """A Static BP_TrainingDrone: a lock to break, counted by its room's encounter. shot_only: the sidearm alone."""
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

    def pickup(self, kind, label, x, y, z=None, lift=120.0):
        """BP_Pickup: 0 health, 1 Divinity, 2 ammo."""
        if z is None:
            x, y = self.free(x, y, 150.0)
            z = self.floor(x, y)
        return self.spawn('BP_Pickup', 'Pickup ' + label, (x, y, z + lift), None, 'Pickups', Kind=kind)

    def encounter(self, label, x, y, room, give, message, goal='', z=None):
        place = (x, y, (self.floor(x, y) if z is None else z) + 400)
        return self.spawn('BP_Encounter', label, place, None, 'Encounters', Room=room, Learn=0, Give=give, Message=message, NextGoal=goal)

    def require(self, label, place, needs, give, message):
        values = {'Need%s' % 'ABCD'[i]: token for i, token in enumerate(needs)}
        return self.spawn('BP_Requirement', label, place, None, 'Requirements', Give=give, Message=message, **values)

    def vent(self, label, x, y, size, token, period, offset):
        """A forced vent (BP_Hazard): it burns while it glows; Settle within 16 m closes it for good (token)."""
        return self.spawn('BP_Hazard', 'Forced Vent ' + label, (x, y, self.g.at(x, y) + 4), (size[0] / 100, size[1] / 100, 1), 'Array', Deep=False,
                          Off=token, Period=float(period), Offset=float(offset))

    def site(self, title, x, y, kind, token):
        self.sites.append((title, x, y, kind, token))

    # -- the link ----------------------------------------------------------------------
    NODE_MESH = {0: 'SM_GN_LinkNode', 1: 'SM_GN_LinkSource%s', 2: 'SM_GN_LinkReceiver%s', 3: 'SM_GN_LinkRelay%s'}

    def node(self, label, place, kind=0, flow='', need='', hide='', give='', done='', reach_m=None, range_m=None, lift=0.0, perch=(0.0, 0.0),
             folder='Links'):
        """BP_LinkNode at `place` (cm: where she lands, for an anchor). lift (cm) hangs the knot that far above it;
        perch (cm, x and y) moves the landing sideways from under the knot."""
        x, y, z = place
        actor = self.spawn('BP_LinkNode', label, (x, y, z + lift), None, folder, Kind=kind, Flow=flow, Need=need, Hide=hide, Give=give, Done=done)
        if reach_m:
            actor.set_editor_property('Reach', reach_m * M)
        if range_m:
            actor.set_editor_property('Range', range_m * M)
        if lift or perch != (0.0, 0.0):
            actor.set_editor_property('Perch', unreal.Vector(perch[0], perch[1], -lift))
        name = self.NODE_MESH[kind]
        part = component(actor, 'Shape')
        if part:
            part.set_static_mesh(mesh_asset(name % flow.capitalize() if '%s' in name else name))
        glow = component(actor, 'Glow')
        if glow and flow in ('water', 'power'):
            colour = (.3, .75, 1.0) if flow == 'water' else (1.0, .72, .25)
            glow.set_light_color(unreal.LinearColor(colour[0], colour[1], colour[2], 1))
        return actor

    def anchor(self, label, x, y, z=None, need='', hide='', range_m=60.0, lift=150.0, perch=(0.0, 0.0), folder='Links'):
        """A link anchor over (x, y): she lands there, on the ground or on a surface whose top is z."""
        z = self.floor(x, y) if z is None else z
        return self.node(label, (x, y, z), 0, need=need, hide=hide, range_m=range_m, lift=lift, perch=perch, folder=folder)

    def chain(self, name, start, stops):
        """Records a route for fit() and routes(). `start` is where she stands first (cm); each stop is a knot, or a
        pair (the knot she arrives by, the knot she leaves by) on something she walks across between them. Forward
        she links from the last stop's leaving side to the next stop's arriving knot; back, the reverse."""
        stops = [stop if isinstance(stop, (tuple, list)) else (stop, stop) for stop in stops]
        leave = start
        for index, (arrive, depart) in enumerate(stops):
            self.hops.append(('%s %d' % (name, index + 1), leave, arrive))
            if index:
                self.hops.append(('%s %d back' % (name, index), self.landing(arrive), stops[index - 1][1]))
            leave = self.landing(depart)

    def flow(self, name, nodes):
        """Records a flow's legs (source, relays, socket) for routes(): the carried thread breaks when something
        stands between her and the node it comes from for 1.5 s, so each leg needs a clear line."""
        for index in range(len(nodes) - 1):
            self.flows.append(('%s leg %d' % (name, index + 1), nodes[index], nodes[index + 1]))

    @staticmethod
    def landing(node):
        """Where her capsule's centre comes to rest under a knot (cm)."""
        at, perch = node.get_actor_location(), node.get_editor_property('Perch')
        return (at.x + perch.x, at.y + perch.y, at.z + perch.z + 96.0)

    @staticmethod
    def sight(start, node):
        """None when her head at `start` (capsule centre, cm) sees the knot's seed, as PhysisLinkFind traces it (against
        the meshes themselves, not their collision hulls: a cliff rock's hull bulges well past the rock); else
        (what blocks, how far along in cm, the whole distance)."""
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        head = unreal.Vector(start[0], start[1], start[2] + 60.0)
        seed = node.get_actor_location() + unreal.Vector(0, 0, 100.0)
        hit = unreal.SystemLibrary.line_trace_single(world, head, seed, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [node],
                                                     unreal.DrawDebugTrace.NONE, True)
        data = hit.to_tuple() if hit is not None else None   # (blocking, overlap, time, distance, location, ..., [9] actor)
        if data and data[0]:
            return (data[9].get_actor_label() if data[9] else '?', data[3], (seed - head).length())
        return None

    @staticmethod
    def on_terrain(x, y, z):
        """True when nothing but the land lies under (x, y) near height z: no cliff rock, trunk or wall to land inside."""
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z + 2500.0), unreal.Vector(x, y, z - 500.0),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        data = hit.to_tuple() if hit is not None else None
        return bool(data and data[0] and data[9] and data[9].get_actor_label().startswith('Terrain') and abs(data[4].z - z) < 60.0)

    def bank(self, x, y, ux, uy, back=(500.0, 800.0, 1100.0, 1400.0, 1800.0)):
        """A landing on open ground near (x, y): the first spot stepping back along (ux, uy) with only land under it."""
        for d in back:
            px, py = x + ux * d, y + uy * d
            if self.on_terrain(px, py, self.g.at(px, py)):
                return px, py
        return x + ux * back[-1], y + uy * back[-1]

    def fit(self, top=1400.0, step=100.0):
        """Raises each knot whose hop is blocked, 1 m at a time (her landing stays where it is: Perch takes the
        rise), until every hop that can be cleared that way is clear. Returns the knots raised and by how much."""
        raised = {}
        for _ in range(4):
            changed = False
            for label, start, node in self.hops:
                while self.sight(start, node) is not None:
                    perch = node.get_editor_property('Perch')
                    if -perch.z >= top:
                        break
                    node.set_actor_location(node.get_actor_location() + unreal.Vector(0, 0, step), False, False)
                    node.set_editor_property('Perch', unreal.Vector(perch.x, perch.y, perch.z - step))
                    raised[node.get_actor_label()] = round(-(perch.z - step))
                    changed = True
            if not changed:
                break
        return raised


# ---------------------------------------------------------------- the regions

def pack(p, label, x, y, levels, room=0, spread=700.0, z=None):
    out = []
    for k, level in enumerate(levels):
        a = k / len(levels) * 2 * math.pi + .6
        out.append(p.enemy(level, '%s %d' % (label, k), x + math.cos(a) * spread, y + math.sin(a) * spread, room, z))
    return out


def cache(p, n, title, x, y, token=None, divinity=40.0, message=None, z=None):
    """A seed cache: Divinity, a cyan ray until it is taken."""
    token = token or ',gr_cache%d,' % n
    z = p.floor(x, y) if z is None else z
    p.relic('Seed Cache %d' % n, (x, y, z + 110), token, message or lore.MESSAGES['cache'], divinity=divinity, mesh='SM_GN_SeedCache', scale=1.0)
    p.light('Seed Cache Glow %d' % n, (x, y, z + 160), LINK, 1500, 500, 'Items')
    p.site(title, x, y, 2, token)


def dress(p, label, rows, folder, origin=(0.0, 0.0)):
    """Loose set dressing: (mesh, x m, y m, yaw, scale, solid radius cm) rows relative to origin (m), on the ground."""
    for k, (mesh, x, y, yaw, scale, solid) in enumerate(rows):
        px, py = cm(origin[0] + x, origin[1] + y)
        p.mesh('%s %d' % (label, k), mesh, (px, py, p.g.at(px, py) - 3), yaw, scale, folder, solid=solid)


def hollow(p):
    hx, hy = cm(*plan.HOLLOW)
    floor = p.g.at(hx, hy)
    p.spawn('BP_GroveCurrent', 'Current Home', (hx, hy, floor + 25), None, 'Hollow', Need='', Dest=2, Radius=180.0)
    p.marks['Current Home'] = (hx, hy, floor + 25)
    p.solids.append((hx, hy, 500))
    p.light('Hollow Glow', (hx, hy, floor + 600), LINK, 9000, 2800, 'Hollow')
    sx, sy = cm(*plan.HOLLOW_STILL)
    p.check('Hollow', sx, sy, lore.QUEST_ARRIVE, 800.0)
    # She arrives on the Still Point, 20 m from the current: outside its 1.8 m reach, so arriving never sends her back.
    p.marks['Arrival'] = p.at(sx, sy, 120)
    p.marker('Arrival', p.marks['Arrival'], 'GroveArrival', 'Hollow')
    cache(p, 1, 'Hollow Cache', *cm(-470.0, 20.0))


def road(p):
    # The thornroot wall across the road, 45 m up it: Settle parts it. Thorn runs on into the trees either side
    # (it goes with the blight when the grove heals); walking round through the wood costs nothing but the lesson.
    wx, wy = cm(-455.0, 72.0)
    heading = math.degrees(math.atan2(72.0 - 36.0, -455.0 + 490.0))
    p.thorn('Road', wx, wy, heading, ',gr_thorn,')
    for side in (-1, 1):
        for k in (1, 2):
            ox, oy = turned(0.0, side * (400.0 + 500.0 + (k - 1) * 1000.0), heading)
            p.mesh('Road Thorn %d %d' % (side, k), 'SM_GN_ThornCage', (wx + ox, wy + oy, p.g.at(wx + ox, wy + oy) - 60), heading, (1, 1, .62),
                   'Thornroot', tags=('GroveBlight',))
    p.light('Road Thorn Glow', p.at(wx, wy, 250), MAGENTA, 2600, 1100, 'Thornroot', ('GroveBlight',))
    pack(p, 'Road Patrol', *cm(-436.0, 90.0), (1, 1, 2), 401, 600)
    p.encounter('Road Patrol', *cm(-436.0, 90.0), 401, ',gr_road,', 'The patrol is down. The road north is clear.')
    # The fallen overpass, the road running under its standing span, and Burr under the fallen one.
    ox, oy = cm(*plan.OVERPASS)
    yaw = math.degrees(math.atan2(96.0 - 72.0, -350.0 + 455.0))
    p.mesh('Overpass', 'SM_GN_Overpass', (ox, oy, p.g.at(ox, oy) - 30), yaw, 1.0, 'Road', solid=0)
    dress(p, 'Road Wreck', (('SM_GS_CoveredCar', -470.0, 60.0, 30.0, 1.0, 300), ('SM_GS_CoveredCar', -380.0, 106.0, -12.0, 1.0, 300),
                            ('SM_GS_BarrierA', -448.0, 82.0, 50.0, 1.0, 120), ('SM_GS_BarrierB', -449.5, 84.0, 44.0, 1.0, 120),
                            ('SM_GS_BarrierA', -330.0, 78.0, -40.0, 1.0, 120), ('SM_GS_CoveredCar', -322.0, 70.0, 140.0, 1.0, 300),
                            ('SM_GS_Tyre', -383.0, 103.0, 0.0, 1.0, 0), ('SM_GS_StreetLamp', -300.0, 58.0, 20.0, 1.2, 60)), 'Road')
    pack(p, 'Road North', *cm(-345.0, 88.0), (1, 2), 0, 600)
    pack(p, 'Old Town Spur', *cm(-392.0, 185.0), (2, 2, 1), 0, 700)


def old_town(p):
    cx, cy = cm(*plan.OLD_TOWN)
    for label, mesh, (x, y), yaw, solid in (('Ruin A', 'SM_GN_Ruin0', (-338.0, 248.0), 30.0, 900), ('Ruin B', 'SM_GN_Ruin1', (-306.0, 250.0), -60.0, 750),
                                            ('Ruin C', 'SM_GN_Ruin0', (-352.0, 290.0), 200.0, 900), ('Ruin D', 'SM_GN_Ruin1', (-322.0, 304.0), 120.0, 750)):
        x, y = cm(x, y)
        p.mesh(label, mesh, (x, y, p.g.at(x, y) - 25), yaw, 1.0, 'Old Town', solid=solid)
    dress(p, 'Old Town Wreck', (('SM_GS_CoveredCar', -328.0, 272.0, 80.0, 1.0, 300), ('SM_GS_BarrierB', -316.0, 262.0, 10.0, 1.0, 120),
                                ('SM_GS_Hydrant', -330.0, 262.0, 0.0, 1.0, 40), ('SM_GS_TrashCan', -312.0, 276.0, 30.0, 1.0, 50),
                                ('SM_GS_StreetLamp', -334.0, 270.0, 90.0, 1.2, 60)), 'Old Town')
    # The Harrow walks the streets: avoidable, and nothing here is on the critical path.
    p.enemy(6, 'Harrow', cx + 400, cy - 600, 461)
    p.encounter('Harrow', cx, cy, 461, ',gr_harrow,', 'The Harrow is still. Old Town is quiet for the first time in forty years.')
    # Wick's first canister, on Ruin A's ground floor (its doorway faces +x).
    rx, ry = cm(-338.0, 248.0)
    p.relic('Seed Canister 1', (rx, ry, p.g.at(rx, ry) + 115), ',can1,', lore.MESSAGES['can'], mesh='SM_GN_Canister', scale=1.0)
    # The vault: a bunker of the Just whose door motor wants power. A battery bank across the square still holds a
    # charge; two relays carry it round the ruins (the source's thread is too short to reach the motor).
    bx, by, byaw = -292.0, 300.0, -125.0
    vx, vy = cm(bx, by)
    floor = p.g.at(vx, vy) - 10
    p.mesh('Vault Bunker', 'SM_GN_Bunker', (vx, vy, floor), byaw, 1.0, 'Old Town', solid=700)
    dx, dy = turned(370.0, 0.0, byaw)
    p.rise('Vault Door', 'SM_GN_BunkerDoor', (vx + dx, vy + dy, floor), ',gr_vault,', -280.0, byaw, 1.0, 90.0, 'Old Town')
    ex, ey = turned(270.0, 0.0, byaw)
    p.relic('The Old Edge', (vx + ex, vy + ey, floor + 115), ',aug_katana5,', lore.MESSAGES['edge'], ',gr_vault,', mesh='SM_CN_LightCache', scale=.8)
    sx, sy = cm(-350.0, 268.0)
    p.mesh('Battery Bank', 'SM_GN_Capacitor', (sx - 160, sy, p.g.at(sx, sy) - 5), 0.0, 1.0, 'Old Town', solid=200)
    vault = [p.node('Vault Source', p.at(sx, sy), 1, 'power', reach_m=22.0, range_m=14.0, folder='Old Town')]
    r1, r2 = cm(-332.0, 286.0), cm(-312.0, 296.0)
    vault.append(p.node('Vault Relay 1', p.at(*r1), 3, 'power', reach_m=20.0, range_m=10.0, folder='Old Town'))
    vault.append(p.node('Vault Relay 2', p.at(*r2), 3, 'power', reach_m=20.0, range_m=10.0, folder='Old Town'))
    kx, ky = turned(560.0, 260.0, byaw)
    vault.append(p.node('Vault Motor', p.at(vx + kx, vy + ky), 2, 'power', give=',gr_vault,', done=lore.MESSAGES['vault'], range_m=10.0, folder='Old Town'))
    p.flow('Vault', vault)
    p.site('Old Town Vault', vx, vy, 0, ',aug_katana5,')


CAMP_PROPS = (('SM_GS_PlanterB', 6.0, -12.0, 0.0, 1.6, 90), ('SM_GS_PlanterB', 6.0, -15.0, 0.0, 1.6, 90), ('SM_GS_PlanterC', 9.5, -13.5, 90.0, 1.3, 90),
              ('SM_GS_PlanterA', 2.5, -13.0, 20.0, 1.6, 80), ('SM_GS_SeedTray', 3.4, -9.6, 15.0, 2.0, 0), ('SM_GS_Pot', 4.2, -9.2, 0.0, 1.6, 0),
              ('SM_GS_WateringCan', 5.0, -9.8, 70.0, 1.3, 0), ('SM_GS_Spade', 2.0, -10.6, 0.0, 1.0, 0),
              ('SM_GS_CrateB', -6.0, -8.0, 30.0, 1.4, 100), ('SM_GS_CrateC', -7.6, -6.4, 80.0, 1.4, 100), ('SM_GS_MilCrate', -5.0, -6.2, 10.0, 1.4, 80),
              ('SM_GS_MilCrateOpen', -9.2, -9.0, -20.0, 1.4, 100), ('SM_GS_ToolCart', -3.0, -11.5, 100.0, 1.0, 90),
              ('SM_GS_Generator', 12.0, 4.0, 200.0, 1.5, 90), ('SM_GS_JerrycanA', 13.2, 3.0, 40.0, 1.2, 0), ('SM_GS_JerrycanB', 13.5, 4.1, 0.0, 1.2, 0),
              ('SM_GS_StorageCart', -10.0, 4.0, 0.0, 1.0, 110), ('SM_GS_BarrelA', -11.4, 6.2, 0.0, 1.0, 50), ('SM_GS_BarrelB', -12.2, 5.0, 0.0, 1.0, 50),
              ('SM_GS_ToolChest', 0.5, 12.5, 180.0, 1.2, 60), ('SM_GS_HandTruck', 2.0, 13.0, 200.0, 1.0, 50),
              ('SM_GS_StreetLamp', 9.0, 8.0, 220.0, 1.15, 50), ('SM_GS_StreetLamp', -9.0, -12.0, 40.0, 1.15, 50),
              ('SM_GS_StreetLamp', -14.0, 9.0, -30.0, 1.15, 50), ('SM_GS_StreetLamp', 13.0, -9.0, 150.0, 1.15, 50),
              # The camp's own buildings (Tools/grove_meshes/structures.py), their doors (+x) turned to the camp's middle:
              # Thessaly's shelter on the west side, the glasshouse by the nursery planters on the south-east.
              ('SM_GN_Shelter', -20.0, -8.0, 22.0, 1.0, 450), ('SM_GN_Greenhouse', 20.0, -14.0, 145.0, 1.0, 620))


def camp(p):
    cx, cy = plan.CAMP
    p.check('Field Camp', *cm(-262.0, -14.0), 'The Field Camp. Speak to Thessaly, the camp\'s botanist.')
    dress(p, 'Camp', CAMP_PROPS, 'Camp', (cx, cy))
    for k, (mesh, x, y, yaw, scale, solid) in enumerate(CAMP_PROPS):
        if mesh == 'SM_GS_StreetLamp':
            lx, ly = cm(cx + x, cy + y)
            p.light('Camp Lamp %d' % k, p.at(lx, ly, 420), AMBER, 3200, 1500, 'Camp')
    for spot in (lore.PEOPLE[0][5], lore.PEOPLE[3][5], lore.CAMP_POST):
        p.solids.append((spot[0] * M, spot[1] * M, 250))


def graft(p):
    gx, gy = cm(*plan.GRAFT)
    floor = p.g.at(gx, gy)
    # Two trunks grown into one: two oaks leaning into each other over the knot she lays her hand on.
    p.mesh('Graft Trunk A', 'SM_GV_Oak', (gx + 60, gy - 150, floor - 40), 20.0, 1.25, 'Graft', solid=250, roll=9.0)
    p.mesh('Graft Trunk B', 'SM_GV_Oak', (gx + 60, gy + 150, floor - 40), 200.0, 1.25, 'Graft', solid=250, roll=9.0)
    p.switch('The Graft', (gx - 170, gy, floor), 0.0, 'SM_GN_LinkNode', False, (1.6, 1.6, 1.6), 'Graft', Need=',tess,', Give=',resonance,',
             Denied=lore.MESSAGES['graft_denied'], Done=lore.GRAFT_DONE)
    p.light('Graft Glow', (gx - 170, gy, floor + 180), LINK, 2600, 900, 'Graft')
    p.solids.append((gx, gy, 500))
    pack(p, 'Graft Trail', *cm(-205.0, 52.0), (1, 1), 0, 500)


def gully(p):
    # The barrier she will remember: 16 m across at the trail, crossed only by the link. One anchor on each bank.
    sx, sy = cm(*plan.GULLY_SOUTH)
    nx, ny = cm(*plan.GULLY_NORTH)
    for y in (plan.GULLY_CROSS_Y,):
        gx = plan.gully_x(y)
        ax, ay = p.bank((gx - plan.GULLY_RIM) * M, y * M, -1.0, 0.0)
        bx, by = p.bank((gx + plan.GULLY_RIM) * M, y * M, 1.0, 0.0)
        a = p.anchor('Gully South %d' % y, ax, ay, need=',resonance,', range_m=45.0, lift=300.0)
        b = p.anchor('Gully North %d' % y, bx, by, need=',resonance,', range_m=45.0, lift=300.0)
        p.chain('Gully %d' % y, (ax - 300, ay, p.floor(ax - 300, ay) + 96), [a, b])
        # From the Gully's floor either bank's knot is a way up.
        pit = (gx * M, y * M, p.g.at(gx * M, y * M) + 96)
        p.hops.append(('Gully %d floor south' % y, pit, a))
        p.hops.append(('Gully %d floor north' % y, pit, b))
    # Once the Warden falls a root bridge grows across at the trail: the walking shortcut home.
    mx = plan.gully_x(plan.GULLY_CROSS_Y) * M
    rim = p.g.at(sx, sy)
    p.rise('Gully Root Bridge', 'SM_GN_RootBridge', (mx, sy, rim - 1500), ',warden,', 1500.0, 0.0, (1.15, 1, 1), 120.0, 'Bridges')
    fx = plan.gully_x(-150.0) * M
    cache(p, 2, 'Gully Cache', fx, -150.0 * M)


def understory(p):
    ux, uy = cm(*plan.UNDERSTORY)
    p.check('Understory', ux, uy, lore.QUEST_LIFELINES)
    for label, (x, y), levels in (('Trail West', (-22.0, -78.0), (1, 2)), ('Trail East', (-2.0, 104.0), (1, 1, 2)), ('Trail North', (72.0, 6.0), (2, 3)),
                                  ('Service Road', (118.0, 128.0), (2, 2, 3)), ('North Wood', (150.0, -40.0), (1, 3))):
        pack(p, label, *cm(x, y), levels, 0, 700)
    cache(p, 3, 'Understory Cache', *cm(14.0, 124.0))


# The Drowned Campus: blocks standing in the lake, their bases 2.5 m under its surface. (mesh, x, y, roof top above
# the mesh's base in cm, half x, half y in cm, parapet height cm)
BLOCKS = (('Tank', 'SM_GN_Tank', 50.0, -184.0, 700.0, 330.0, 330.0, 0.0), ('Lab A', 'SM_GN_Lab0', 90.0, -216.0, 900.0, 800.0, 600.0, 90.0),
          ('Lab B', 'SM_GN_Lab1', 132.0, -244.0, 1100.0, 600.0, 600.0, 0.0), ('Lab C', 'SM_GN_Lab0', 164.0, -264.0, 900.0, 800.0, 600.0, 90.0))
SUNK = -250.0


def campus(p):
    qx, qy = cm(*plan.QUAY)
    p.check('Campus Quay', qx, qy, 'The Drowned Campus. Link from roof to roof, north across the lake, to the Weir.')
    dress(p, 'Quay', (('SM_GS_Lifebuoy', 3.0, -4.0, 0.0, 1.0, 0), ('SM_GS_CrateB', -4.0, -3.0, 20.0, 1.3, 90), ('SM_GS_BarrelC', -5.0, -1.0, 0.0, 1.0, 50),
                      ('SM_GS_StreetLamp', 5.0, 3.0, 120.0, 1.15, 50)), 'Campus', plan.QUAY)
    pack(p, 'Quay', *cm(4.0, -108.0), (1, 1, 2), 411, 600)
    p.encounter('Quay', *cm(4.0, -108.0), 411, ',gr_quay,', 'The quay is clear.')
    roofs, nodes = {}, []
    stand = (qx, qy, p.floor(qx, qy) + 96)
    for index, (label, mesh, x, y, roof, half_x, half_y, parapet) in enumerate(BLOCKS):
        bx, by = cm(x, y)
        p.mesh('Campus ' + label, mesh, (bx, by, SUNK), 0.0, 1.0, 'Campus', solid=max(half_x, half_y) + 100)
        top = SUNK + roof
        roofs[label] = (bx, by, top)
        # Two anchors a block: one at the edge she comes from, one at the edge she leaves by, each landing 2 m in.
        px, py = (qx, qy) if index == 0 else cm(*BLOCKS[index - 1][2:4])
        nxt = cm(*BLOCKS[index + 1][2:4]) if index + 1 < len(BLOCKS) else cm(plan.WEIR[0], plan.WEIR[1] - 14.0)
        pair = []
        for side, (tx, ty) in (('in', (px, py)), ('out', nxt)):
            d = math.hypot(tx - bx, ty - by)
            ux, uy = (tx - bx) / d, (ty - by) / d
            reach = min(half_x / abs(ux) if abs(ux) > 1e-6 else 1e9, half_y / abs(uy) if abs(uy) > 1e-6 else 1e9) - 60.0
            ex, ey = bx + ux * reach, by + uy * reach
            node = p.node('Campus %s %s' % (label, side), (ex - ux * 200.0, ey - uy * 200.0, top), 0, need=',resonance,', range_m=60.0,
                          lift=150.0 + parapet, perch=(-ux * 0.0, -uy * 0.0), folder='Campus')
            node.set_actor_location(unreal.Vector(ex, ey, top + 150.0 + parapet), False, False)
            node.set_editor_property('Perch', unreal.Vector(-ux * 200.0, -uy * 200.0, -(150.0 + parapet)))
            pair.append(node)
        nodes.append(tuple(pair))
    # The Weir: its deck 12 m over the lake. The anchor hangs over the west gate tower; she lands on the deck beside it.
    wx, wy = cm(*plan.WEIR)
    deck = plan.WEIR_CREST * M
    p.mesh('Weir', 'SM_GN_Weir', (wx, wy, 0.0), 0.0, 1.0, 'Weir', solid=0)
    # The gate towers stand on the deck's upstream half, so everything she uses keeps to the downstream half (lane).
    lane = wx - 100.0
    tower = p.node('Weir Tower', (lane, wy - 1050.0, deck), 0, need=',resonance,', range_m=60.0, lift=650.0, folder='Weir')
    tower.set_actor_location(unreal.Vector(wx + 120.0, wy - 1400.0, deck + 650.0), False, False)
    tower.set_editor_property('Perch', unreal.Vector(-220.0, 350.0, -650.0))
    p.chain('Campus', stand, nodes + [tower])
    # Its guard, then the river: the source at the deck's west end wakes when the guard is gone; the relay stands at
    # the middle, the socket by the sluice wheel at the east end. 22 m apart, the thread 30 m long.
    for k, (level, dy) in enumerate(((5, 0.0), (2, 900.0), (2, -700.0))):
        p.enemy(level, 'Weir Guard %d' % k, lane, wy + dy, 413, deck)
    p.encounter('Weir Guard', wx, wy, 413, ',gr_weir,', lore.MESSAGES['weir_guard'], z=deck)
    p.flow('Weir', [p.node('Weir Source', (lane, wy - 2200.0, deck), 1, 'water', need=',gr_weir,', reach_m=30.0, range_m=12.0, folder='Weir'),
                    p.node('Weir Relay', (lane, wy, deck), 3, 'water', reach_m=30.0, range_m=10.0, folder='Weir'),
                    p.node('Weir Sluice', (lane, wy + 2200.0, deck), 2, 'water', give=',water,', done=lore.MESSAGES['water'], range_m=10.0, folder='Weir')])
    p.mesh('Sluice Wheel', 'SM_GN_SluiceWheel', (wx + 130, wy + 2420.0, deck), 180.0, 1.0, 'Weir')
    p.light('Weir Glow', (wx, wy + 2200.0, deck + 300), (.3, .75, 1.0), 2400, 1200, 'Weir', ('GroveWater',))
    bx, by = cm(*plan.WEIR_BANK)
    p.check('Weir', bx, by, 'The Weir. Carry the headpond\'s flow along the deck to the sluice wheel.')
    # Lancets on the roofs, the second canister on Lab B, a cache on Lab C, and Burr's pin in his hauler's wreck.
    for k, name in enumerate(('Lab A', 'Lab B')):
        rx, ry, top = roofs[name]
        p.enemy(2, 'Roof %d' % k, rx + 250, ry + 200, 412, top)
    p.enemy(1, 'Roof 2', roofs['Lab A'][0] - 300, roofs['Lab A'][1] - 200, 412, roofs['Lab A'][2])
    p.encounter('Roofs', roofs['Lab B'][0], roofs['Lab B'][1], 412, ',gr_roofs,', 'The roofs are clear.', z=roofs['Lab B'][2])
    rx, ry, top = roofs['Lab B']
    p.relic('Seed Canister 2', (rx - 300, ry + 300, top + 115), ',can2,', lore.MESSAGES['can'], mesh='SM_GN_Canister', scale=1.0)
    rx, ry, top = roofs['Lab C']
    cache(p, 4, 'Campus Cache', rx - 250, ry - 250, z=top)
    hx, hy = cm(-30.0, -214.0)
    bed = p.g.at(hx, hy)
    p.mesh('Hauler Wreck', 'SM_GS_CoveredCar', (hx, hy, bed - 20), 35.0, 1.5, 'Campus', pitch=6.0)
    p.relic("Burr's Pin", (hx + 60, hy, max(bed + 230, -60.0)), ',pin,', lore.MESSAGES['pin'], mesh='SM_GN_Pin', scale=1.0)
    pack(p, 'Weir Path', *cm(238.0, -176.0), (2, 3), 0, 600)


def canopy(p):
    fx, fy = cm(*plan.CANOPY_FOOT)
    p.check('Canopy Foot', fx, fy, 'The High Canopy. Link up into the great trees, and on to the Relay on its mesa.')
    pack(p, 'Canopy Foot', *cm(22.0, 160.0), (1, 1, 3), 421, 600)
    p.encounter('Canopy Foot', *cm(22.0, 160.0), 421, ',gr_foot,', 'The foot of the great trees is clear.')
    nodes, decks = [], []
    prev = (fx, fy)
    for index, (x, y, height) in enumerate(plan.GIANTS):
        tx, ty = cm(x, y)
        top = p.g.at(tx, ty) + height * M
        p.mesh('Tree Platform %d' % (index + 1), 'SM_GN_TreePlatform', (tx, ty, top), 0.0, 1.0, 'Canopy')
        decks.append((tx, ty, top))
        nxt = cm(*plan.GIANTS[index + 1][:2]) if index + 1 < len(plan.GIANTS) else cm(*plan.RELAY)
        pair = []
        for side, (ax, ay) in (('in', prev), ('out', nxt)):
            d = math.hypot(ax - tx, ay - ty)
            ux, uy = (ax - tx) / d, (ay - ty) / d
            node = p.anchor('Platform %d %s' % (index + 1, side), tx + ux * 450.0, ty + uy * 450.0, top, need=',resonance,', range_m=70.0, lift=220.0,
                            folder='Canopy')
            pair.append(node)
        nodes.append(tuple(pair))
        p.light('Platform Lamp %d' % (index + 1), (tx + 380, ty - 380, top + 230), AMBER, 1800, 1100, 'Canopy')
        prev = (tx, ty)
    # The mesa: she lands on its edge nearest the third tree.
    rx, ry = cm(*plan.RELAY)
    mesa = plan.RELAY_TOP * M
    d = math.hypot(prev[0] - rx, prev[1] - ry)
    ux, uy = (prev[0] - rx) / d, (prev[1] - ry) / d
    edge = p.anchor('Relay Mesa', rx + ux * 1750.0, ry + uy * 1750.0, mesa, need=',resonance,', range_m=70.0, lift=220.0, folder='Relay')
    p.chain('Canopy', (fx, fy, p.floor(fx, fy) + 96), nodes + [edge])
    tx, ty, top = decks[1]
    p.relic('Seed Canister 3', (tx - 420, ty + 150, top + 115), ',can3,', lore.MESSAGES['cans'], mesh='SM_GN_Canister', scale=1.0)
    p.enemy(2, 'Platform Lancet', decks[2][0] + 430, decks[2][1] - 100, 0, decks[2][2])
    # The Relay: the mast on the mesa, the capacitor bank at its south edge, a relay at the plinth's foot and the
    # coupling off the edge of the mast's deck, 6 m up.
    p.mesh('Relay Tower', 'SM_GN_RelayTower', (rx, ry, mesa - 10), 0.0, 1.0, 'Relay', solid=650)
    p.check('Relay', rx + 300.0, ry - 1500.0, 'The Relay. Carry the capacitors\' charge to the coupling on the mast.', z=mesa)
    for k, (level, bearing, r) in enumerate(((5, 80.0, 1100.0), (1, 200.0, 1300.0), (1, 320.0, 1300.0), (3, 20.0, 1500.0))):
        b = math.radians(bearing)
        p.enemy(level, 'Relay Guard %d' % k, rx + math.cos(b) * r, ry + math.sin(b) * r, 422, mesa)
    p.encounter('Relay Guard', rx, ry, 422, ',gr_relay,', lore.MESSAGES['relay_guard'], z=mesa)
    p.mesh('Capacitor Bank', 'SM_GN_Capacitor', (rx - 1700.0, ry + 500.0, mesa - 5), 15.0, 1.0, 'Relay', solid=200)
    p.flow('Relay', [p.node('Relay Source', (rx - 1500.0, ry + 330.0, mesa), 1, 'power', need=',gr_relay,', reach_m=22.0, range_m=12.0, folder='Relay'),
                     p.node('Relay Plinth', (rx - 700.0, ry - 700.0, mesa), 3, 'power', reach_m=14.0, range_m=10.0, folder='Relay'),
                     p.node('Relay Coupling', (rx - 480.0, ry, mesa + 600.0), 2, 'power', give=',power,', done=lore.MESSAGES['power'], range_m=12.0, folder='Relay')])
    p.light('Relay Glow', (rx, ry, mesa + 900), (1.0, .72, .25), 5000, 2400, 'Relay', ('GrovePower',))
    cache(p, 5, 'Mesa Cache', rx + 1300.0, ry + 900.0, z=mesa)
    # Down: no fall hurts her. The service road runs from the mesa's foot to the gantry mast at the Rift.
    mx, my = cm(*plan.MAST)
    p.mesh('Gantry Mast', 'SM_GN_Mast', (mx, my, p.g.at(mx, my) - 20), plan.EAST_BEARING, 1.0, 'Rift', solid=300)


def rift_bridge(p, label, bearing, need):
    """A root bridge across the Rift on a bearing: 20 m of deck over the 16 m gorge, risen from under its floor."""
    x, y = cm(*plan.ring_point(bearing, (plan.RIFT_IN + plan.RIFT_OUT) / 2))
    rim = p.g.at(*cm(*plan.ring_point(bearing, plan.RIFT_IN - 3.0)))
    return p.rise(label, 'SM_GN_RootBridge', (x, y, rim - 1900), need, 1900.0, bearing, (1.1, 1, 1), 150.0, 'Bridges')


def rift(p):
    rift_bridge(p, 'West Root Bridge', plan.WEST_BEARING, ',water,')
    rift_bridge(p, 'South Root Bridge', plan.SOUTH_BEARING, ',warden,')
    # East: the old line. With the charge back, two knots wake, one on each rim by the gantry mast.
    b = math.radians(plan.EAST_BEARING)
    ox, oy = p.bank(*cm(*plan.ring_point(plan.EAST_BEARING, plan.RIFT_OUT)), math.cos(b), math.sin(b))
    ix, iy = p.bank(*cm(*plan.ring_point(plan.EAST_BEARING, plan.RIFT_IN)), -math.cos(b), -math.sin(b))
    outer = p.anchor('Rift East Outer', ox, oy, need=',power,', range_m=55.0, lift=300.0, folder='Rift')
    inner = p.anchor('Rift East Inner', ix, iy, need=',power,', range_m=55.0, lift=300.0, folder='Rift')
    p.chain('Rift East', (ox + math.cos(b) * 300, oy + math.sin(b) * 300, p.floor(ox, oy) + 96), [outer, inner])
    p.light('Rift East Glow', p.at(ox, oy, 300), (1.0, .72, .25), 2200, 1200, 'Rift', ('GrovePower',))
    pack(p, 'Rift West', *cm(*plan.ring_point(plan.WEST_BEARING, plan.RIFT_OUT + 22.0)), (2, 3, 1), 431, 600)
    p.encounter('Rift West', *cm(*plan.ring_point(plan.WEST_BEARING, plan.RIFT_OUT + 22.0)), 431, ',gr_riftw,', 'The western rim is clear.')
    pack(p, 'Rift East', *cm(*plan.ring_point(plan.EAST_BEARING + 14.0, plan.RIFT_OUT + 24.0)), (2, 3, 3), 432, 600)
    p.encounter('Rift East', *cm(*plan.ring_point(plan.EAST_BEARING + 14.0, plan.RIFT_OUT + 24.0)), 432, ',gr_rifte,', 'The eastern rim is clear.')
    # Thornroot round the knoll's rim: the wound, seen before the wall.
    for k in range(14):
        bearing = 180.0 + (k - 6.5) * 24.0
        x, y = cm(*plan.ring_point(bearing, plan.RIFT_IN - 9.0 - (k % 3) * 3.0))
        p.mesh('Rift Thorn %d' % k, 'SM_GV_Thorn', (x, y, p.g.at(x, y) - 20), k * 77.0, 1.0 + .2 * (k % 3), 'Thornroot', collide=False,
               tags=('GroveBlight',))
    # The Forecourt's Still Point stands back from the gate (22 m from its guard), just inside the Rift's rim.
    fx, fy = cm(*plan.ring_point(plan.SOUTH_BEARING, plan.RIFT_IN - 8.0))
    p.check('Forecourt', fx, fy, 'The gate of the Deeproot Array.')
    gate = plan.ring_point(plan.SOUTH_BEARING, plan.ARRAY_WALL + 9.0)
    for k, (level, dy) in enumerate(((4, -700.0), (4, 700.0), (1, -1300.0), (1, 1300.0))):
        gx, gy = gate[0] * M, gate[1] * M + dy
        p.enemy(level, 'Gate Guard %d' % k, gx, gy, 441, p.g.at(gx, gy))
    p.encounter('Forecourt', gate[0] * M, gate[1] * M, 441, ',gr_forecourt,', 'The gate\'s guard is down.')


WALL_SLOTS = 38
CAGE_BEARINGS = (62.0, -62.0)


def array(p):
    hx, hy = cm(*plan.HEARTWOOD)
    top = p.g.at(*cm(*plan.GATE))
    radius = plan.ARRAY_WALL * M
    # The ring wall: panels 12 m wide, their faces outward, and the gate in the slot facing south.
    for k in range(WALL_SLOTS):
        bearing = plan.SOUTH_BEARING + k * 360.0 / WALL_SLOTS
        b = math.radians(bearing)
        x, y = hx + math.cos(b) * radius, hy + math.sin(b) * radius
        if k == 0:
            p.mesh('Array Gate Frame', 'SM_GN_ArrayGateFrame', (x, y, top - 30), bearing, 1.0, 'Array')
            p.rise('Array Gate', 'SM_GN_ArrayGate', (x, y, top - 30), ',arraygate,', -900.0, bearing, 1.0, 110.0, 'Array')
        else:
            p.mesh('Array Wall %d' % k, 'SM_GN_ArrayWall', (x, y, p.g.at(x, y) - 60), bearing, (1, 1.03, 1.05), 'Array')
    for k, bearing in enumerate((30.0, 90.0, 150.0, 210.0, 270.0, 330.0)):
        b = math.radians(bearing)
        x, y = hx + math.cos(b) * (radius - 550.0), hy + math.sin(b) * (radius - 550.0)
        p.mesh('Array Tower %d' % k, 'SM_GN_ArrayTower', (x, y, top - 20), bearing + 180.0, 1.0, 'Array', solid=350)
        p.light('Array Tower Light %d' % k, (x, y, top + 1400), AMBER, 5200, 2600, 'Array')
    gx, gy = cm(*plan.GATE)
    p.require('Array Gate Lock', (gx, gy, top + 600), (',water,', ',power,'), ',arraygate,', lore.MESSAGES['arraygate'])
    # Inside: the Still Point, the core coupling's dais with the surge on it, and the Heartwood's heart at the foot of
    # the trunk, 29 m apart (the surge's thread is 20 m, the heart answers within 8). Two relays carry the surge there: along the west side if the water came first, the east
    # if the power did (the saved choice of BP_GroveDirector; same source, socket and exit either way).
    # The Still Point stands just inside the gate; the Root Court's guards keep to its far sides.
    rx, ry = cm(265.0, -20.0)
    p.check('Root Court', rx, ry, lore.QUEST_CORE)
    dx, dy = cm(282.0, -20.0)
    p.mesh('Core Dais', 'SM_GN_CoreDais', (dx, dy, top - 10), 0.0, 1.0, 'Array', solid=0)
    surge = p.node('Core Surge', (dx, dy, top + 110), 1, 'surge', need=',arraygate,', reach_m=20.0, range_m=10.0, folder='Array')
    heart = p.node('Heartwood Heart', (311.0 * M, -20.0 * M, top), 2, 'surge', give=',stabilized,', done=lore.MESSAGES['stabilized'], range_m=8.0,
                   folder='Array')
    for token, sign in ((',gr_first_w,', -1.0), (',gr_first_e,', 1.0)):
        side = 'West' if sign < 0 else 'East'
        p.flow('Core ' + side, [surge,
                                p.node('Core Relay %s 1' % side, (292.0 * M, (-20.0 + sign * 22.0) * M, top), 3, 'surge', need=token, reach_m=14.0,
                                       range_m=8.0, folder='Array'),
                                p.node('Core Relay %s 2' % side, (306.0 * M, (-20.0 + sign * 18.0) * M, top), 3, 'surge', need=token, reach_m=14.0,
                                       range_m=8.0, folder='Array'), heart])
        for k, (x, off) in enumerate(((287.0, 11.0), (299.0, 20.0))):
            n = (1 if sign < 0 else 3) + k
            p.vent(str(n), x * M, (-20.0 + sign * off) * M, (400.0, 400.0), ',gr_vent%d,' % n, 3.2, n * 1.1)
    for k, (level, x, y) in enumerate(((4, 302.0, -58.0), (2, 318.0, -64.0), (2, 302.0, 18.0), (3, 318.0, 26.0))):
        p.enemy(level, 'Court Guard %d' % k, x * M, y * M, 451, top)
    p.encounter('Root Court', 300.0 * M, -20.0 * M, 451, ',gr_court,', 'The Root Court is clear.', z=top)
    for k, (x, y, yaw) in enumerate(((300.0, -70.0, 20.0), (300.0, 32.0, -20.0), (352.0, -72.0, 100.0))):
        p.mesh('Conduit %d' % k, 'SM_GN_Conduit', (x * M, y * M, top - 15), yaw, 1.0, 'Array', solid=500)
    # The Warden's cage: thorn from the trunk to the wall on both sides, sunk by the stabilised core.
    for side, bearing in enumerate(CAGE_BEARINGS):
        b = math.radians(bearing)
        for k in range(6):
            r = (13.0 + 5.0 + k * 10.0) * M
            p.rise('Warden Cage %d %d' % (side, k), 'SM_GN_ThornCage', (hx + math.cos(b) * r, hy + math.sin(b) * r, top - 40), ',stabilized,', -760.0,
                   bearing - 90.0, (1, 1.04, 1), 180.0, 'Thornroot')
    # The Warden's ground, north of the trunk: the Warden, its Wasps and Burls, and three shield emitters high on
    # the wall that only the sidearm reaches. The room's fall is the Hedge's.
    ax, ay = cm(*plan.ARENA)
    p.enemy(7, 'Warden', ax, ay, 452, top)
    for k, (level, bearing, r) in enumerate(((1, 45.0, 1300.0), (1, 135.0, 1300.0), (1, 225.0, 1300.0), (1, 315.0, 1300.0), (3, 90.0, 1700.0), (3, 270.0, 1700.0))):
        b = math.radians(bearing)
        p.enemy(level, 'Warden Guard %d' % k, ax + math.cos(b) * r, ay + math.sin(b) * r, 452, top)
    emitter = next(row for row in lore.GROVE_SCANS if row[1] == 'Shield Emitter')
    for k, bearing in enumerate((-22.0, 0.0, 22.0)):
        b = math.radians(bearing)
        x, y = hx + math.cos(b) * (radius - 140.0), hy + math.sin(b) * (radius - 140.0)
        p.target('Shield Emitter %d' % k, 'SM_GE_Emitter', (x, y, top + 620), 452, 6, 1.6, emitter[:3], bearing + 180.0, 'Array', True)
        p.light('Emitter Light %d' % k, (x, y, top + 620), AMBER, 2600, 900, 'Array')
    p.encounter('Warden', ax, ay, 452, ',warden,', lore.MESSAGES['warden'], lore.QUEST_VOSS, z=top)
    for k, bearing in enumerate((100.0, 260.0)):
        b = math.radians(bearing)
        p.pickup(0, 'Arena Capsule %d' % k, ax + math.cos(b) * 1900.0, ay + math.sin(b) * 1900.0, top)
    # Afterwards: the Heartwood's gift at the trunk's north foot, and the Director at her bunker's door.
    p.relic("The Heartwood's Gift", (350.0 * M, -20.0 * M, top + 115), ',aug_hp7,', lore.MESSAGES['gift'], ',warden,', heal=True, mesh='SM_CN_LightCache',
            scale=.9)
    bx, by = cm(*lore.BUNKER)
    byaw = math.degrees(math.atan2(-20.0 * M - by, 282.0 * M - bx))
    ox, oy = turned(-560.0, 0.0, byaw)
    p.mesh('Control Bunker', 'SM_GN_Bunker', (bx + ox, by + oy, top - 10), byaw, 1.0, 'Array', solid=650)
    lx, ly = turned(-190.0, 0.0, byaw)
    p.rise('Bunker Door', 'SM_GN_BunkerDoor', (bx + lx, by + ly, top - 10), ',warden,', -290.0, byaw, 1.0, 60.0, 'Array')
    p.light('Bunker Lamp', (bx, by, top + 260), AMBER, 2200, 900, 'Array')


def falls(p):
    """Optional: two ledges up the cliff beside the waterfall, reached by the link, and the grove's highest cache."""
    px, py = cm(*plan.FALLS_POOL)
    stand = (px - 300, py + 500, p.floor(px - 300, py + 500) + 96)
    nodes = []
    for k, want in enumerate((3300.0, 4700.0)):
        spot = None
        for step in range(8, 60):
            x, y = px + step * 60.0, py + 700.0 - step * 14.0
            if p.g.at(x, y) >= want:
                spot = (x, y)
                break
        if spot is None:
            continue
        x, y = spot
        p.mesh('Falls Ledge %d' % k, 'SM_GN_Walkway', (x - 250.0, y, want + 60.0), 0.0, (1.0, 1.6, 1.0), 'Falls')
        nodes.append(p.anchor('Falls Ledge %d' % k, x - 330.0, y, want + 60.0, need=',resonance,', range_m=45.0, lift=180.0, folder='Falls'))
        if k == 1:
            p.relic('Falls Cache', (x - 120.0, y, want + 170.0), ',gr_falls,', lore.MESSAGES['falls'], divinity=80.0, mesh='SM_GN_SeedCache', scale=1.0)
            p.site('Falls Cache', x - 120.0, y, 2, ',gr_falls,')
    if nodes:
        p.chain('Falls', (stand[0], stand[1], stand[2]), nodes)


# ---------------------------------------------------------------- people

# Where a person's figure comes from: (mesh, scale, lift cm, bob cm) for the machines; Voss, the one human, is shown
# through BP_NPC's Look (a MetaHuman Blueprint) when hers exists.
FIGURES = {'SM_GP_Thessaly': ('SM_GP_Thessaly', 1.0, 0.0, 0.0), 'SM_GP_Burr': ('SM_GP_Burr', 1.0, 0.0, 0.0),
           'SM_GP_Wick': ('SM_GP_Wick', 1.0, 0.0, 0.0), 'SM_GP_Intercom': ('SM_GP_Intercom', 1.0, 0.0, 0.0)}
# Where a person stands when it is not the lore's point (x, y metres, yaw): the Root Court's post by its Still Point.
SPOTS = {'VossCore': (268.0, -10.0, 180.0)}
# Hers (built by the Conclave's people pipeline, so it lands in its folder: physis_grove_people.py), else a stand-in.
VOSS_LOOKS = ('/Game/Conclave/People/Voss/BP_Voss', '/Game/Grove/People/Voss/BP_Voss', '/Game/Conclave/People/Rhea/BP_Rhea')


def person(p, row):
    key, speaker, mesh, voice, kind, (x, y), yaw = row[:7]
    show, hide, greeting, topics, give, quest, reward = row[7:]
    pages = lore.conversation_pages(row)
    starts, first = [], len(greeting)
    for _, answer in topics:
        starts.append(first)
        first += len(answer)
    figure = FIGURES.get(mesh)
    if key in SPOTS:
        x, y, yaw = SPOTS[key]
    px, py = cm(x, y)
    if key.startswith('Burr'):
        # Under the fallen span's raised edge, in the overpass's own frame (README: the point (4, -3.5)).
        oyaw = math.degrees(math.atan2(96.0 - 72.0, -350.0 + 455.0))
        dx, dy = turned(400.0, -350.0, oyaw)
        px, py = plan.OVERPASS[0] * M + dx, plan.OVERPASS[1] * M + dy
        yaw = oyaw + 180.0
    place = (px, py, p.g.at(px, py))
    npc = p.spawn('BP_NPC', 'Person ' + key, place, None, 'People', Speaker=speaker, Key=key, Pages='|'.join(wrap(page) for page in pages),
                  Asks='|'.join(label for label, _ in topics), Starts='|'.join(str(s) for s in starts), Greet=len(greeting), Show=show, Hide=hide,
                  Give=give, Quest=quest, RewardDivinity=float(reward.get('divinity', 0.0)), RewardHeal=bool(reward.get('heal', False)),
                  Note=reward.get('note', ''), Face=kind in ('robot', 'human'), Bob=figure[3] if figure else 0.0)
    npc.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    body, shape, view = component(npc, 'Body'), component(npc, 'Shape'), component(npc, 'Look')
    for name in ('Lower', 'Upper', 'Head'):
        part = component(npc, name)
        if part:
            part.set_static_mesh(None)
    shown = ''
    if figure:
        if view:
            view.set_child_actor_class(None)
        if body:
            body.set_skinned_asset_and_update(None, True)
        if shape:
            shape.set_static_mesh(mesh_asset(figure[0]))
            shape.set_relative_scale3d(unreal.Vector(figure[1], figure[1], figure[1]))
        shown = figure[0]
    else:
        built = next((asset(path, True) for path in VOSS_LOOKS if asset(path, True) is not None), None)
        if built is not None and view is not None:
            view.set_relative_scale3d(unreal.Vector(1, 1, 1))
            view.set_child_actor_class(built.generated_class())
            if body:
                body.set_skinned_asset_and_update(None, True)
            if shape:
                shape.set_static_mesh(None)
            shown = built.get_name()
        else:
            shown = 'bare Mannequin'
    p.people.append((key, shown))
    for k in range(len(pages)):
        title = lore.person_key(key, k)
        p.spawn('BP_LogVoice', 'Voice ' + title, VOICE_SPOT, None, 'Voices', Title=title, Voice=asset(VOICES + '/' + voice_name(title)))
    return npc


def people(p):
    p.people = []
    for row in lore.PEOPLE:
        person(p, row)


# ---------------------------------------------------------------- passes over the whole level

# Lore scans that do not stand free: the relics' ride on BP_Relic (RelicTag, by token), the emitter's on its targets.
ATTACHED = ("Burr's Coupling Pin", 'A Seed Canister', "The Heartwood's Gift", 'The Old Edge', 'Shield Emitter', 'Seed Cache')


def scans(p):
    for category, title, body, (x, y, z), important in lore.GROVE_SCANS:
        if title in ATTACHED:
            continue
        p.scan(category, title, body, (x * M, y * M, z), important)


def voices(p):
    for category, title, body in lore.grove_entries() + [('Story',) + tuple(lore.ARRIVAL_LINE)]:
        p.spawn('BP_LogVoice', 'Voice ' + title, VOICE_SPOT, None, 'Voices', Title=title, Voice=asset(VOICES + '/' + voice_name(title)),
                Image=asset('/Game/UI/Log/' + image_name(title), True))


def tutorials(p):
    for index, (message, (x, y), scale) in enumerate(lore.GROVE_TUTORIALS):
        p.spawn('BP_TutorialTrigger', 'Tutorial %02d' % (index + 1), p.at(x * M, y * M, 160), scale, 'Tutorial', Message=message)


RAY_KINDS = {0: ('/Game/Conclave/Materials/MI_CNRay_Puzzle', 900.0), 1: ('/Game/Conclave/Materials/MI_CNRay_Vault', 800.0),
             2: ('/Game/Conclave/Materials/MI_CNRay_Cache', 650.0)}
RAY_HEIGHT = 60000.0


def divinity_rays(p):
    box = asset('/Engine/BasicShapes/Cylinder').get_bounding_box()
    for name, x, y, kind, token in p.sites:
        path, width = RAY_KINDS[kind]
        material = asset(path)
        foot = p.floor(x, y) - 300
        sz, sxy = RAY_HEIGHT / (box.max.z - box.min.z), width / (box.max.x - box.min.x)
        ray = p.spawn('BP_DivinityRay', 'Ray ' + name, (x, y, foot - box.min.z * sz), (sxy, sxy, sz), 'Rays', DoneToken=token, Kind=kind, Title=name)
        part = ray.get_components_by_class(unreal.StaticMeshComponent)[0]
        for index in range(max(1, part.get_num_materials())):
            part.set_material(index, material)
        part.set_collision_profile_name('NoCollision')
        for key, value in (('cast_shadow', False), ('never_distance_cull', True), ('ld_max_draw_distance', 0.0), ('allow_cull_distance_volume', False),
                           ('translucency_sort_priority', 10), ('visible_in_ray_tracing', False), ('hidden_in_scene_capture', True),
                           ('receives_decals', False)):
            try:
                part.set_editor_property(key, value)
            except Exception as error:
                unreal.log_warning('Ray %s: %s' % (key, error))
    return len(p.sites)


def crossings():
    """Where she crosses a gorge (cm): the Gully at the trail and the Rift's three crossings, both rims of each."""
    out = []
    gx = plan.gully_x(plan.GULLY_CROSS_Y)
    for x in (gx - plan.GULLY_RIM, gx + plan.GULLY_RIM):
        out.append(cm(x, plan.GULLY_CROSS_Y))
    for bearing in (plan.WEST_BEARING, plan.SOUTH_BEARING, plan.EAST_BEARING):
        for r in (plan.RIFT_IN, plan.RIFT_OUT):
            out.append(cm(*plan.ring_point(bearing, r)))
    return out


def open_crossings(reach=1300.0):
    """The level build lines both gorges with cliff rock that stands 2 m and more above their rims: a parapet she
    cannot see a knot over, or step onto a root bridge through. At each crossing the rock within 13 m of the rim point
    is taken out (instances of the level's cliff actors; the land's own wall stays), as an old bridgehead would be
    clear. A rerun finds them gone; a level rebuild puts them back for the next scenario run to take out again."""
    points, removed = crossings(), 0
    for actor in sub().get_all_level_actors():
        if not str(actor.get_folder_path()).startswith('Grove/Cliffs'):
            continue
        for part in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            for index in range(part.get_instance_count() - 1, -1, -1):
                at = part.get_instance_transform(index, True).translation
                if any(math.hypot(at.x - x, at.y - y) < reach for x, y in points):
                    part.remove_instance(index)
                    removed += 1
    return removed


def sound_scape(p):
    """The forest everywhere, the water at the lake and the weir, the Array's hum round the Heartwood (which stops
    with the blight: tag GroveBlight). Placed only for the beds grove:audio has imported."""
    placed = []

    def ambient(label, sound, place, radius, volume, tags=()):
        wave = asset(GROVE + '/Audio/' + sound, True)
        if wave is None:
            return
        actor = sub().spawn_actor_from_class(unreal.AmbientSound, unreal.Vector(*place))
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
    ambient('Forest', 'S_Amb_Forest', (0, 0, 4000), 0, .55)
    ambient('Lake', 'S_Amb_Water', (plan.LAKE[0] * M, plan.LAKE[1] * M, 300), 16000, .7)
    ambient('Weir', 'S_Amb_Water', (plan.WEIR[0] * M, plan.WEIR[1] * M, 1300), 9000, .8)
    ambient('Array', 'S_Amb_Array', (plan.HEARTWOOD[0] * M, plan.HEARTWOOD[1] * M, 4800), 14000, .8, ('GroveBlight',))
    return placed


def upright_trees():
    """The level build stood the great trees with their turn in the pitch slot (Rotator is roll, pitch, yaw), so they
    leaned 20 to 87 degrees: each is set upright with that angle as its yaw. Returns what it turned."""
    fixed = []
    for actor in sub().get_all_level_actors():
        if actor.get_actor_label().startswith('Great Tree'):
            r = actor.get_actor_rotation()
            if abs(r.pitch) > .5 or abs(r.roll) > .5:
                actor.set_actor_rotation(unreal.Rotator(0, 0, r.pitch if abs(r.roll) < 90 else 180.0 - r.pitch), False)
                fixed.append(actor.get_actor_label())
    return fixed


def routes(p):
    """Traces every recorded hop in the editor world, from her head where she stands to the knot's seed (as
    BP_Physis.PhysisLinkFind does), and checks the knot's reach. Returns (hops checked, the blocked ones)."""
    blocked = []
    for label, start, node in p.hops:
        seed = node.get_actor_location() + unreal.Vector(0, 0, 100.0)
        far = (seed - unreal.Vector(start[0], start[1], start[2] + 60.0)).length()
        reach = node.get_editor_property('Range') or 3200.0
        if far > reach:
            blocked.append('%s: %.0f m away, its reach is %.0f m' % (label, far / M, reach / M))
            continue
        seen = p.sight(start, node)
        if seen is not None:
            blocked.append('%s: blocked by %s at %.0f m of %.0f' % (label, seen[0], seen[1] / M, seen[2] / M))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for label, a, b in p.flows:
        start, end = a.get_actor_location() + unreal.Vector(0, 0, 100.0), b.get_actor_location() + unreal.Vector(0, 0, 100.0)
        far = (end - start).length()
        span = (a.get_editor_property('Reach') or 3000.0) + (b.get_editor_property('Range') or 3200.0)
        if far > span:
            blocked.append('%s: %.0f m apart, thread and reach give %.0f m' % (label, far / M, span / M))
        hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [a, b],
                                                     unreal.DrawDebugTrace.NONE, True)
        data = hit.to_tuple() if hit is not None else None
        if data and data[0]:
            blocked.append('%s: thread cut by %s at %.0f m of %.0f' % (label, data[9].get_actor_label() if data[9] else '?', data[3] / M, far / M))
    return len(p.hops) + len(p.flows), blocked


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def open_level(path):
    world = editor_world()
    current = world.get_path_name().split('.')[0] if world else ''
    if current == path:
        return
    dirty = [pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them before opening %s' % (', '.join(dirty), path))
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(path):
        raise RuntimeError('Could not open ' + path)


def save_level(path):
    world = editor_world()
    if world.get_path_name().split('.')[0] != path:
        raise RuntimeError('Refusing to save: %s is open, not %s' % (world.get_path_name(), path))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


def clear():
    removed = 0
    for actor in sub().get_all_level_actors():
        folder = str(actor.get_folder_path())
        if folder == FOLDER or folder.startswith(FOLDER + '/'):
            sub().destroy_actor(actor)
            removed += 1
    return removed


def arrival_off():
    for actor in sub().get_all_level_actors():
        if actor.get_class().get_name() == 'BP_Awakening_C':
            actor.set_editor_property('TestArrival', False)


def place(ground, save=True):
    MISSING.clear()
    open_level(LEVEL)
    removed = clear()
    trees = upright_trees()
    opened = open_crossings()
    p = Place(ground)
    hollow(p)
    road(p)
    camp(p)
    graft(p)
    gully(p)
    understory(p)
    campus(p)
    canopy(p)
    rift(p)
    array(p)
    old_town(p)
    p.require('Seed Canisters', p.at(*cm(*plan.CAMP), lift=600), (',can1,', ',can2,', ',can3,'), ',cans,', lore.MESSAGES['cans'])
    people(p)
    scans(p)
    voices(p)
    tutorials(p)
    rays = divinity_rays(p)
    sounds = sound_scape(p)
    arrival_off()
    raised = p.fit()
    hops, blocked = routes(p)
    if save:
        save_level(LEVEL)
    return {'level': LEVEL, 'removed': removed, 'placed': p.count, 'enemies': p.enemies, 'rays': rays, 'sounds': sounds, 'people': p.people, 'unset': p.unset,
            'trees_set_upright': trees, 'cliff_rocks_removed': opened, 'hops': hops, 'raised': raised, 'blocked': blocked, 'missing_assets': sorted(MISSING)[:60], 'missing_count': len(MISSING),
            'marks': {name: [round(v) for v in spot] for name, spot in p.marks.items()}}


# ---------------------------------------------------------------- the Center's temple current

def portal():
    """The current to Earth in the Center's sanctum, shown once the Shepherd has fallen: a targeted spawn into
    L_CenterOfTheUniverse that replaces only its own earlier actors (labels 'Grove Current...', which the Center's
    clear() and cinema() leave alone)."""
    open_level(CENTER_LEVEL)
    dirty = [pkg.get_name() for pkg in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them before grove:portal' % ', '.join(dirty))
    actors = sub()
    removed = 0
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label().startswith('Grove Current'):
            actors.destroy_actor(actor)
            removed += 1
    world = editor_world()
    floors = {}
    for name, spot in (('current', PORTAL), ('return', RETURN)):
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(spot[0], spot[1], spot[2] + 600.0), unreal.Vector(spot[0], spot[1], spot[2] - 1500.0),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        data = hit.to_tuple() if hit is not None else None
        floors[name] = round(data[4].z) if data and data[0] else None
    place_z = (floors['current'] if floors['current'] is not None else SANCTUM) + 35.0
    back_z = (floors['return'] if floors['return'] is not None else SANCTUM) + 120.0
    current = actors.spawn_actor_from_class(cls('BP_GroveCurrent'), unreal.Vector(PORTAL[0], PORTAL[1], place_z))
    current.set_actor_label('Grove Current')
    current.set_folder_path('Center/Grove')
    props(current, Need=',shepherd,', Dest=1, Radius=180.0)
    back = actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(RETURN[0], RETURN[1], back_z))
    back.set_actor_label('Grove Current Return')
    back.set_folder_path('Center/Grove')
    back.set_editor_property('tags', ['GroveReturn'])
    arrival_off()
    save_level(CENTER_LEVEL)
    return {'level': CENTER_LEVEL, 'current': [PORTAL[0], PORTAL[1], place_z], 'return': [RETURN[0], RETURN[1], back_z], 'floors': floors,
            'removed': removed}
