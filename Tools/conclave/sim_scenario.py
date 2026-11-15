"""Offline harness for the Conclave's scenario (Content/Python/physis_conclave_scenario.py). No Unreal: a recording
stub stands in for the `unreal` module, place() and portal() run against it, and what they built is checked.

  PYTHONPATH=~/PhysisProject/Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages \\
      python3 Tools/conclave/sim_scenario.py [--quiet] [--looks metahuman|mannequin]

--looks runs with physis_conclave_cast.LOOKS set to that value instead of the file's (the cast switch; both must pass).

The ground is Art/Meshes/Conclave/height.json and height.bin when the Blender build has written them, else a stub
from physis_conclave_plan: the drum circle, the plazas levelled, the lake bowl and its island, the Foundry's slag
moat (the shapes Tools/conclave/README.md "Terrain" asks of drum.py), so lake and moat rules mean something.

Checks: the token graph is solvable from the flags she arrives with (every Need, Show, requirement and gate token is
given by something reachable without it; every ability gate's ability is had before the gate; ,shepherd, and the
side requests' rewards are reachable; only later-level abilities stay out of reach); every PEOPLE key has a BP_NPC
and every page a voice; every BP_NPC stands at actor scale 1; a MetaHuman row whose look is assembled shows BP_<mh>
in Look at its MH look_scale with Body, garments and Shape empty, every other person stands in their CAST row's
Mannequin or figure with Look empty (the stub reports the looks of UNBUILT_LOOKS as not assembled, so both paths
run); people.py's cast checks pass; every Logbook title has a voice;
every mesh used exists among the generators' builders
(check.py's builds(); the README's contract names for a module not written yet); encounter rooms are unique in
301-399 and each holds its enemies; every placement is on the walkable floor (|y| <= 295 m), out of the lake unless
it belongs in it, and off the town's houses (scatter.json if present, else the README's keep-clear zones in the
town); about 150 combatants; light colours in the palette; no 3D text; every shared actor reskinned; Still Point
tokens apart from the Center's; a second place() replaces the first; portal() is a targeted spawn in the Center.
Exit status 1 if anything fails.
"""
import importlib
import importlib.abc
import importlib.util
import math
import pathlib
import re
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = ROOT / 'Content/Python'
MESH_TOOLS = ROOT / 'Tools/conclave_meshes'
ART = ROOT / 'Art/Meshes/Conclave'
QUIET = '--quiet' in sys.argv
LOOKS_OVERRIDE = sys.argv[sys.argv.index('--looks') + 1] if '--looks' in sys.argv else None
# People whose assembled look the stub reports as missing, so the stand-in path runs beside the Look path (the looks
# are built one person at a time: the Listener first, then Teodor, then the rest).
UNBUILT_LOOKS = ('Rhea',)
START = ',center,,settle,,mend,,awoke,,conclave,,at_conclave,'
LATER = (',trace,', ',resonance,', ',dissonance,', ',reweave,', ',sitwith,')  # abilities of later levels
CENTER_STILL = ((-684, 0), (-90, -40), (-128, 390), (260, 260), (260, -300), (670, 0), (744, 0))  # the Center's ,sp_x_y, (m)

FAIL, WARN, INFO = [], [], []


def fail(message):
    FAIL.append(message)


def warn(message):
    WARN.append(message)


# ---------------------------------------------------------------- the recording stub of `unreal`

class Vector:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def to_tuple(self):
        return (self.x, self.y, self.z)


class Rotator:
    def __init__(self, roll=0.0, pitch=0.0, yaw=0.0):
        self.roll, self.pitch, self.yaw = float(roll), float(pitch), float(yaw)


class LinearColor:
    def __init__(self, r=0.0, g=0.0, b=0.0, a=1.0):
        self.r, self.g, self.b, self.a = r, g, b, a


class Transform:
    def __init__(self, translation=None, rotation=None, scale=None):
        self.translation, self.rotation, self.scale3d = translation or Vector(), rotation or Rotator(), scale or Vector(1, 1, 1)


class Box:
    def __init__(self, lo, hi):
        self.min, self.max = Vector(*lo), Vector(*hi)


class Anything:
    """What the modules the scenario imports touch at import time (asset tools, material libraries)."""

    def __init__(self, name):
        self._name = name

    def __getattr__(self, name):
        return Anything(self._name + '.' + name)

    def __call__(self, *args, **kwargs):
        return Anything(self._name + '()')


def engine_class(name):
    return type(name, (), {'ue_name': name})


class BlueprintClass:
    def __init__(self, name):
        self.ue_name = name

    def get_name(self):
        return self.ue_name


class Asset:
    def __init__(self, path):
        self.path = path
        self.name = path.rsplit('/', 1)[-1]

    def generated_class(self):
        return BlueprintClass(self.name + '_C')

    def get_bounding_box(self):
        return Box((-50, -50, -50), (50, 50, 50))

    def get_path_name(self):
        return '%s.%s' % (self.path, self.name)


# Instance-editable variables of the shared Blueprints (read from the editor with list_variables, 2026-11-06) and the
# new ones the README defines, with the Python type each must be given.
S, F, I, B, O = str, float, int, bool, object
VARS = {
    'BP_Switch_C': {'Need': S, 'Give': S, 'Denied': S, 'Done': S, 'Seq': I, 'SeqBase': I, 'Finish': B, 'Cost': F, 'SeqFinal': S},
    'BP_Relic_C': {'Token': S, 'Need': S, 'Message': S, 'Divinity': F, 'Heal': B, 'Tease': B, 'Locked': S},
    'BP_Rise_C': {'Need': S, 'Lift': F, 'Speed': F},
    'BP_Requirement_C': {'NeedA': S, 'NeedB': S, 'NeedC': S, 'NeedD': S, 'Give': S, 'Message': S},
    'BP_SettleBarrier_C': {'Give': S},
    'BP_AbilitySocket_C': {'Ability': S, 'Give': S, 'Message': S, 'Radius': F, 'Hold': F, 'Solid': B},
    'BP_DivinityRay_C': {'DoneToken': S, 'Kind': I, 'Title': S},
    'BP_Hazard_C': {'Off': S, 'Period': F, 'Offset': F, 'Deep': B},
    'BP_Encounter_C': {'Room': I, 'Learn': I, 'Give': S, 'Message': S, 'NextGoal': S},
    'BP_Checkpoint_C': {'Radius': F, 'Objective': S, 'Until': S},
    # ShotOnly (2026-11-08, the Center's BP change): PhysisStrikeNow's blade skips such a Static target.
    'BP_TrainingDrone_C': {'Health': I, 'RoomId': I, 'Boss': B, 'Static': B, 'ShotOnly': B},
    'BP_Pickup_C': {'Kind': I, 'Token': S},
    'BP_CutGrass_C': {'Regrow': F, 'Chance': F},   # goldgrass (author, 2026-11-15): the Conclave's pickups grow in it
    'BP_LogVoice_C': {'Voice': O, 'Title': S, 'Image': O},
    'BP_TutorialTrigger_C': {'Message': S},
    'BP_ScanTarget_C': {'ScanText': S, 'ScanImportant': B, 'ScanCategory': S, 'ScanTitle': S},
    'BP_Platform_C': {'AmpX': F, 'AmpY': F, 'AmpZ': F, 'Period': F, 'Need': S},
    'BP_Awakening_C': {'TestArrival': B},
    'BP_NPC_C': {'Speaker': S, 'Key': S, 'Pages': S, 'Asks': S, 'Starts': S, 'Greet': I, 'Show': S, 'Hide': S, 'Give': S, 'Quest': S,
                 'RewardDivinity': F, 'RewardHeal': B, 'Note': S, 'Face': B, 'Bob': F},
    'BP_Current_C': {'Need': S, 'Dest': I, 'Radius': F},
    'BP_ConclaveDirector_C': {},
}
COMPONENT_KEYS = {'relative_scale3d', 'cast_shadow', 'never_distance_cull', 'ld_max_draw_distance', 'allow_cull_distance_volume', 'translucency_sort_priority',
                  'visible_in_ray_tracing', 'hidden_in_scene_capture', 'receives_decals', 'intensity', 'attenuation_radius', 'sound',
                  'volume_multiplier', 'override_attenuation', 'attenuation_overrides', 'allow_spatialization'}
TEMPLATES = {'StaticMeshActor': (('StaticMeshComponent', 'StaticMeshComponent0'),), 'PointLight': (('PointLightComponent', 'LightComponent0'),),
             'AmbientSound': (('AudioComponent', 'AudioComponent0'),),
             'BP_NPC_C': (('SkeletalMeshComponent', 'Body'), ('StaticMeshComponent', 'Lower'), ('StaticMeshComponent', 'Upper'),
                          ('StaticMeshComponent', 'Head'), ('StaticMeshComponent', 'Shape'), ('ChildActorComponent', 'Look')),
             'BP_TrainingDrone_C': (('StaticMeshComponent', 'Shape'), ('StaticMeshComponent', 'Eye'))}
for name in ('BP_Switch_C', 'BP_Relic_C', 'BP_Rise_C', 'BP_SettleBarrier_C', 'BP_AbilitySocket_C', 'BP_DivinityRay_C', 'BP_Hazard_C',
             'BP_Pickup_C', 'BP_Platform_C', 'BP_Current_C', 'BP_CutGrass_C'):
    TEMPLATES[name] = (('StaticMeshComponent', 'Shape'),)


class Settings:
    def __init__(self):
        self.values = {}

    def set_editor_property(self, key, value):
        self.values[key] = value


class Component:
    def __init__(self, owner, kind, name):
        self.owner, self.kind, self.name = owner, kind, name
        self.mesh = None
        self.materials = {}
        self.collision = None
        self.visible = True
        self.values = {}
        self.parent = None
        self.socket = None
        self.world = None
        self.anim = None
        self.mode = None
        self.colour = None
        self.child = None         # a ChildActorComponent's class; set_child_actor_class records every call
        self.child_set = False
        self.scale3d = None       # set_relative_scale3d's last Vector (the scenario sets Look's for a MetaHuman)

    def matches(self, wanted):
        primitive = wanted == 'PrimitiveComponent' and self.kind != 'ChildActorComponent'
        return wanted in ('ActorComponent', 'SceneComponent') or primitive or wanted == self.kind

    def need(self, *kinds):
        if self.kind not in kinds:
            fail('%s.%s: a %s call on a %s' % (self.owner.label, self.name, '/'.join(kinds), self.kind))

    def get_name(self):
        return self.name

    def set_static_mesh(self, mesh):
        self.need('StaticMeshComponent')
        self.mesh = mesh

    def set_skinned_asset_and_update(self, mesh, reinit_pose=True):
        self.need('SkeletalMeshComponent')
        self.mesh = mesh

    def set_material(self, index, material):
        self.need('StaticMeshComponent', 'SkeletalMeshComponent')
        self.materials[index] = material

    def get_num_materials(self):
        return 1

    def set_collision_profile_name(self, profile):
        self.collision = profile

    def set_visibility(self, visible):
        self.visible = visible

    def set_animation_mode(self, mode):
        self.need('SkeletalMeshComponent')
        self.mode = mode

    def override_animation_data(self, anim, looping=True, playing=True, position=0.0, rate=1.0):
        self.need('SkeletalMeshComponent')
        if self.mesh is None:
            fail('%s: animation set before the body has a mesh' % self.owner.label)
        self.anim = (anim, looping, playing)

    def set_world_transform(self, transform, sweep=False, teleport=False):
        self.world = transform

    def attach_to_component(self, parent, socket, location_rule, rotation_rule, scale_rule, weld):
        if self.world is None:
            fail('%s.%s: attached before its world transform was set' % (self.owner.label, self.name))
        if parent.anim is not None:
            fail('%s.%s: attached after the body started animating (the garment would sit off the bind pose)' % (self.owner.label, self.name))
        self.parent, self.socket = parent, socket

    def set_light_color(self, colour):
        self.need('PointLightComponent')
        self.colour = colour

    def set_child_actor_class(self, cls, *template):
        """Look takes the person's assembled Blueprint class (None clears it). The editor spawns the child actor at once;
        this stub never does, so get_child_actor() is None and fitting() must call such a row not measured."""
        self.need('ChildActorComponent')
        self.child, self.child_set = cls, True

    def get_child_actor_class(self):
        self.need('ChildActorComponent')
        return self.child

    def get_child_actor(self):
        self.need('ChildActorComponent')
        return None

    def set_relative_scale3d(self, scale):
        self.scale3d = scale

    def set_cast_shadows(self, value):
        self.values['cast_shadows'] = value

    def set_mobility(self, value):
        self.values['mobility'] = value

    def set_editor_property(self, key, value):
        if key not in COMPONENT_KEYS:
            fail('%s.%s: unknown component property %s' % (self.owner.label, self.name, key))
        self.values[key] = value

    def get_editor_property(self, key):
        if key == 'attenuation_overrides':
            return self.values.setdefault(key, Settings())
        return self.values.get(key)


class Actor:
    def __init__(self, world, cname, location, rotation):
        self.world, self.cname = world, cname
        self.location = Vector(location.x, location.y, location.z)
        self.rotation = rotation or Rotator()
        self.scale = Vector(1, 1, 1)
        self.label, self.folder = '', ''
        self.props = {}
        self.hidden = False
        self.collision = True
        self.parent = None
        self.components = [Component(self, kind, name) for kind, name in TEMPLATES.get(cname, ())]
        if cname == 'StaticMeshActor':
            self.static_mesh_component = self.components[0]

    def get_class(self):
        return BlueprintClass(self.cname)

    def set_actor_label(self, label):
        self.label = label

    def get_actor_label(self):
        return self.label

    def set_folder_path(self, path):
        self.folder = str(path)

    def get_folder_path(self):
        return self.folder

    def set_actor_scale3d(self, scale):
        self.scale = scale

    def set_actor_rotation(self, rotation, teleport=False):
        self.rotation = rotation

    def set_actor_location(self, location, sweep=False, teleport=False):
        self.location = location

    def get_actor_location(self):
        return Vector(self.location.x, self.location.y, self.location.z)

    def get_actor_transform(self):
        return Transform(self.get_actor_location(), self.rotation, self.scale)

    def set_actor_hidden_in_game(self, hidden):
        self.hidden = hidden

    def set_actor_enable_collision(self, enabled):
        self.collision = enabled

    def attach_to_actor(self, parent, socket, location_rule, rotation_rule, scale_rule, weld):
        self.parent = parent

    def get_attach_parent_actor(self):
        return self.parent

    def get_components_by_class(self, cls):
        return [c for c in self.components if c.matches(cls.ue_name)]

    def get_component_by_class(self, cls):
        found = self.get_components_by_class(cls)
        return found[0] if found else None

    def set_editor_property(self, key, value):
        if key == 'tags':
            self.props[key] = list(value)
            return
        known = VARS.get(self.cname)
        if known is None or key not in known:
            fail('%s (%s): unknown property %s' % (self.label or '?', self.cname, key))
        else:
            want = known[key]
            ok = (value is None or isinstance(value, Asset)) if want is O else (
                isinstance(value, (int, float)) and not isinstance(value, bool) if want is F else
                isinstance(value, int) and not isinstance(value, bool) if want is I else isinstance(value, want))
            if not ok:
                fail('%s: %s.%s given %r (%s wanted)' % (self.label or '?', self.cname, key, value, want.__name__))
        self.props[key] = value

    def get_editor_property(self, key):
        return self.props.get(key)


class World:
    def __init__(self, path):
        self.path = path
        self.actors = []
        self.saves = 0

    def get_path_name(self):
        return '%s.%s' % (self.path, self.path.rsplit('/', 1)[-1])


class Stub:
    def __init__(self):
        self.worlds = {}
        self.current = self.world('/Game/Levels/L_MainMenu')
        self.loaded = []
        self.spawned = []
        self.levels_loaded = []
        self.dirty = []  # names of maps with unsaved changes (get_dirty_map_packages)

    def world(self, path):
        return self.worlds.setdefault(path, World(path))


STUB = Stub()


class EditorActorSubsystem:
    def spawn_actor_from_class(self, cls, location, rotation=None):
        cname = getattr(cls, 'ue_name', None)
        if cname is None:
            fail('spawn_actor_from_class given %r' % (cls,))
            cname = '?'
        actor = Actor(STUB.current, cname, location, rotation)
        STUB.current.actors.append(actor)
        STUB.spawned.append(actor)
        return actor

    def get_all_level_actors(self):
        return list(STUB.current.actors)

    def destroy_actor(self, actor):
        if actor in STUB.current.actors:
            STUB.current.actors.remove(actor)
        return True


class LevelEditorSubsystem:
    def load_level(self, path):
        STUB.current = STUB.world(path)
        STUB.levels_loaded.append(path)
        return True

    def save_current_level(self):
        STUB.current.saves += 1
        return True


class UnrealEditorSubsystem:
    def get_editor_world(self):
        return STUB.current


class EditorLoadingAndSavingUtils:
    """The scenario refuses to open or save a map while any map has unsaved changes (STUB.dirty lists them)."""
    @staticmethod
    def get_dirty_map_packages():
        return [types.SimpleNamespace(get_name=lambda n=name: n) for name in STUB.dirty]


SUBSYSTEMS = {}


def get_editor_subsystem(cls):
    return SUBSYSTEMS.setdefault(cls, cls())


def look_built(path):
    """Whether the stub has the assembled look at path (package or object path): the Blueprint of every MH person who is
    not pending, but UNBUILT_LOOKS."""
    package = path.split('.')[0]
    return any(package == cast_module.FILES['look'].format(key=key) for key, entry in cast_module.MH.items()
               if not entry['pending'] and key not in UNBUILT_LOOKS)


class EditorAssetLibrary:
    @staticmethod
    def does_asset_exist(path):
        if path.startswith(cast_module.BUILD_PATH + '/'):
            return look_built(path)
        return path.startswith(('/Game/Conclave/', '/Game/Characters/', '/Engine/'))


def load_asset(path):
    STUB.loaded.append(path)
    return Asset(path)


class Paths:
    @staticmethod
    def project_dir():
        return str(ROOT) + '/'

    @staticmethod
    def convert_relative_path_to_full(path):
        return path


class StubModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        if self.__dict__.get('_strict'):
            fail('the scenario touched unreal.%s, which this stub does not model: check it exists in the editor' % name)
        return Anything('unreal.' + name)


def make_unreal():
    module = StubModule('unreal')
    for name in ('StaticMeshActor', 'PointLight', 'AmbientSound', 'PlayerStart', 'TargetPoint', 'TextRenderActor', 'StaticMeshComponent',
                 'SkeletalMeshComponent', 'PointLightComponent', 'AudioComponent', 'ActorComponent', 'SceneComponent', 'ChildActorComponent'):
        setattr(module, name, engine_class(name))
    module.Vector, module.Rotator, module.LinearColor, module.Transform = Vector, Rotator, LinearColor, Transform
    module.AttachmentRule = types.SimpleNamespace(KEEP_WORLD='KEEP_WORLD', KEEP_RELATIVE='KEEP_RELATIVE', SNAP_TO_TARGET='SNAP_TO_TARGET')
    module.AnimationMode = types.SimpleNamespace(ANIMATION_SINGLE_NODE='ANIMATION_SINGLE_NODE')
    module.ComponentMobility = types.SimpleNamespace(MOVABLE='MOVABLE', STATIC='STATIC')
    module.EditorActorSubsystem, module.LevelEditorSubsystem, module.UnrealEditorSubsystem = EditorActorSubsystem, LevelEditorSubsystem, UnrealEditorSubsystem
    module.get_editor_subsystem, module.load_asset, module.EditorAssetLibrary, module.Paths = get_editor_subsystem, load_asset, EditorAssetLibrary, Paths
    module.EditorLoadingAndSavingUtils = EditorLoadingAndSavingUtils
    module.log = module.log_warning = module.log_error = lambda message: INFO.append(str(message))
    module._strict = False
    return module


class LooksOverride(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serves physis_conclave_cast with LOOKS set from --looks. It has to answer the import system itself: people.py
    puts Content/Python first on sys.path and the scenario's cast_table() reloads the module by name, so a patched
    attribute or a copy earlier on the path would be replaced by the file's own switch."""

    PATH = PY / 'physis_conclave_cast.py'

    def __init__(self, looks):
        self.source, count = re.subn(r"^LOOKS = '\w+'", 'LOOKS = %r' % looks, self.PATH.read_text(), flags=re.M)
        if count != 1:
            raise SystemExit('--looks: %s has no single LOOKS line to set' % self.PATH.name)

    def find_spec(self, name, path=None, target=None):
        return importlib.util.spec_from_loader(name, self, origin=str(self.PATH)) if name == 'physis_conclave_cast' else None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(self.source, str(self.PATH), 'exec'), module.__dict__)


UNREAL = make_unreal()
sys.modules['unreal'] = UNREAL
sys.path.insert(0, str(PY))
sys.path.insert(1, str(MESH_TOOLS))
if LOOKS_OVERRIDE is not None:
    sys.meta_path.insert(0, LooksOverride(LOOKS_OVERRIDE))
try:
    import physis_conclave_cast as cast_module  # noqa: E402
except KeyError as error:
    raise SystemExit('--looks %s: physis_conclave_cast picks no table for %s' % (LOOKS_OVERRIDE, error))

import physis_conclave_plan as plan  # noqa: E402
import physis_conclave_lore as lore  # noqa: E402
import palette  # noqa: E402
import physis_conclave_scenario as scenario  # noqa: E402
from physis_lore import voice_name  # noqa: E402

UNREAL._strict = True


# ---------------------------------------------------------------- the ground

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def stub_height(x, y):
    """Metres: the drum circle, plazas levelled (blended over 20 m), the lake bowl (bed -4 m, a shore rising to the
    drum over a quarter of the ellipse), the island mound (radius 16 m to +3 m) and the slag moat (18-28 m, 6 m)."""
    z = plan.drum_z(y)
    for (cx, cy), r in ((plan.WELL, 30.0), (plan.ORRERY, 45.0), (plan.SPIRE, 60.0), (plan.DOCKS_ARENA, 50.0)):
        w = smooth((math.hypot(x - cx, y - cy) - r) / 20.0)
        z = plan.drum_z(cy) * (1 - w) + z * w
    cx, cy, ax, ay = plan.LAKE
    e = math.sqrt(((x - cx) / ax) ** 2 + ((y - cy) / ay) ** 2)
    if e < 1:
        z = -4.0 * (1 - e * e)
    elif e < 1.25:
        z *= smooth((e - 1) / .25)
    ix, iy = plan.RESERVOIR_ISLAND
    r = math.hypot(x - ix, y - iy)
    if r < 16:
        z = max(z, -4.0 + 7.0 * (1 - r / 16))
    fx, fy = plan.FOUNDRY_PYLON
    if 18.0 <= math.hypot(x - fx, y - fy) <= 28.0:
        z -= 6.0
    return z


class StubGround:
    def at(self, x, y):
        return stub_height(x / 100.0, y / 100.0) * 100.0


def ground():
    if (ART / 'height.json').exists() and (ART / 'height.bin').exists():
        return scenario.Ground(ART), 'Art/Meshes/Conclave/height.bin'
    return StubGround(), 'stub from physis_conclave_plan (no height.bin yet)'


# ---------------------------------------------------------------- mesh names

CONTRACT_MODULES = ('drum', 'architecture', 'districts', 'people', 'al_flora')


def builder_names():
    """Mesh names the generators build (check.py's builds()), and the README contract's names for any module that
    is not there yet or does not import."""
    names, report = set(), []
    try:
        import check
    except Exception as error:
        return None, ['check.py does not import (%s)' % error]
    for module_name in CONTRACT_MODULES:
        if not (MESH_TOOLS / (module_name + '.py')).exists():
            report.append('%s.py not written yet' % module_name)
            continue
        if module_name == 'drum':
            continue  # the scenario places no drum mesh; the terrain build is heavy
        try:
            module = importlib.import_module(module_name)
            built = [part.name for part in check.builds(module)]
            names.update(built)
            report.append('%s.py: %d meshes' % (module_name, len(built)))
        except Exception as error:
            report.append('%s.py failed to build: %r' % (module_name, error))
    return names, report


def contract_names():
    text = (ROOT / 'Tools/conclave/README.md').read_text()
    return {name for name in re.findall(r'`(SM_C[DNPEV]_[A-Za-z0-9_]+)`', text)}


# ---------------------------------------------------------------- the token graph

def tokens(value):
    """',a,,b,' -> {',a,', ',b,'}."""
    return {',%s,' % t for t in (value or '').split(',') if t}


def rules_from(place):
    """(name, needs, gives, actor) for everything that gives a token, with the gate tokens around it."""
    zone = {id(actor): set(needs) for actor, needs, _ in place.log}
    drones = {}
    for actor, needs, _ in place.log:
        if actor.cname == 'BP_TrainingDrone_C':
            drones.setdefault(actor.props.get('RoomId', 0), []).append(actor)
    rules = []
    for actor, needs, _ in place.log:
        pr, cname, need = actor.props, actor.cname, set(needs)
        if cname == 'BP_Switch_C':
            need |= tokens(pr.get('Need'))
            gives = tokens(pr.get('Give'))
            seq = pr.get('Seq', 0) or 0
            if seq > 1:
                need.add('seq:%d' % (seq - 1))
            if seq > 0:
                gives.add('seq:%d' % seq)
        elif cname == 'BP_Relic_C':
            need |= tokens(pr.get('Need'))
            gives = tokens(pr.get('Token'))
        elif cname == 'BP_Requirement_C':
            need = set().union(*(tokens(pr.get(k)) for k in ('NeedA', 'NeedB', 'NeedC', 'NeedD')))
            gives = tokens(pr.get('Give'))
        elif cname == 'BP_AbilitySocket_C':
            need |= tokens(pr.get('Ability'))
            gives = tokens(pr.get('Give'))
        elif cname == 'BP_SettleBarrier_C':
            need.add(',settle,')
            gives = tokens(pr.get('Give'))
        elif cname == 'BP_Hazard_C':
            need.add(',settle,')
            gives = tokens(pr.get('Off'))
        elif cname == 'BP_Encounter_C':
            room = pr.get('Room')
            need = set().union(*(zone[id(d)] for d in drones.get(room, []))) if drones.get(room) else set()
            gives = tokens(pr.get('Give'))
        elif cname == 'BP_NPC_C':
            need |= tokens(pr.get('Show'))
            gives = tokens(pr.get('Give'))
        else:
            continue
        if gives:
            rules.append((actor.label, need, gives, actor))
    return rules


def closure(rules, start, banned=(), skip=None):
    have = set(start)
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if rule is skip:
                continue
            _, need, gives, _ = rule
            if need <= have and not gives <= have:
                new = {g for g in gives if g not in banned} - have
                if new:
                    have |= new
                    changed = True
    return have


def solve(place):
    rules = rules_from(place)
    start = tokens(START)
    reach = closure(rules, start)
    givers = {}
    for rule in rules:
        for token in rule[2]:
            givers.setdefault(token, []).append(rule)
    required = {}
    for actor, needs, _ in place.log:
        pr = actor.props
        wanted = set(needs)
        for key in ('Need', 'Show', 'NeedA', 'NeedB', 'NeedC', 'NeedD', 'Ability'):
            if actor.cname in ('BP_ScanTarget_C', 'BP_LogVoice_C'):
                continue
            wanted |= tokens(pr.get(key) if isinstance(pr.get(key), str) else '')
        for token in wanted:
            required.setdefault(token, set()).add(actor.label)
    later = set(LATER)
    expected = set()
    for token, users in sorted(required.items()):
        if token in start:
            continue
        if token in later:
            expected.add(token)
            continue
        if token not in givers:
            fail('token %s is needed (%s) but nothing gives it' % (token, ', '.join(sorted(users)[:3])))
            continue
        without = closure(rules, start, banned={token})
        if not any(need <= without for _, need, _, _ in givers[token]):
            if any(need & later for _, need, _, _ in givers[token]):
                expected.add(token)
            else:
                fail('token %s cannot be had without already holding it (needed by %s)' % (token, ', '.join(sorted(users)[:3])))
    # Everything kept out of reach must sit behind a later-level ability.
    out = {t for t in required if t not in reach and t not in start}
    for token in sorted(out - expected - later):
        fail('token %s is out of reach (needed by %s)' % (token, ', '.join(sorted(required[token])[:3])))
    # Ability gates: the ability is had without passing the gate.
    sockets = [rule for rule in rules if rule[3].cname == 'BP_AbilitySocket_C']
    plain = [a for a, _, _ in place.log if a.cname == 'BP_AbilitySocket_C' and not tokens(a.props.get('Give'))]
    gates = 0
    for actor in [r[3] for r in sockets] + plain:
        ability = actor.props.get('Ability')
        if ability in later:
            continue
        gates += 1
        skip = next((r for r in sockets if r[3] is actor), None)
        if ability not in closure(rules, start, skip=skip):
            fail('%s needs %s, which cannot be had before it' % (actor.label, ability))
    # People: a person's gift must come before the token that hides them.
    for actor, needs, _ in place.log:
        if actor.cname == 'BP_NPC_C' and tokens(actor.props.get('Give')):
            hide = tokens(actor.props.get('Hide'))
            need = set(needs) | tokens(actor.props.get('Show'))
            if hide and not need <= closure(rules, start, banned=hide - tokens(actor.props.get('Give'))):
                fail('%s: what shows them needs %s, which hides them first' % (actor.label, ', '.join(sorted(hide))))
    goals = (',kairos,', ',pylon1,', ',pylon2,', ',pylon3,', ',spire,', ',lightstep,', ',crown,', ',docksgate,', ',shepherd,', ',conclave_done,',
             ',seedpod,', ',pages,', ',kite,', ',core,', ',wisp,', ',aug_hp5,', ',aug_hp6,', ',aug_katana4,', ',aug_pistol3,', ',aug_defense4,',
             ',aug_agility4,')
    for token in goals:
        if token not in reach:
            fail('%s is not reachable from the arrival flags' % token)
    # Gate tokens declared round a placement must have a physical gate behind them.
    gate_tokens = set()
    for actor, needs, _ in place.log:
        pr = actor.props
        if actor.cname in ('BP_Rise_C', 'BP_Platform_C'):
            gate_tokens |= tokens(pr.get('Need'))
        if actor.cname == 'BP_AbilitySocket_C':
            gate_tokens |= tokens(pr.get('Ability'))
        if actor.cname == 'BP_SettleBarrier_C':
            gate_tokens.add(',settle,')
    for token in sorted({t for _, needs, _ in place.log for t in needs} - gate_tokens):
        fail('placements sit behind %s, but no gate (BP_Rise, socket or barricade) answers to it' % token)
    return reach, rules, expected, gates


# ---------------------------------------------------------------- the checks

def labelled(world, prefix='Scene '):
    return [a for a in world.actors if a.label.startswith(prefix)]


KEEP_CLEAR = ((plan.WELL, 30.0), (plan.ORRERY, 45.0), (plan.ARCHIVE, 16.0), (plan.MENDERY, 12.0), (plan.SHRINE, 10.0), (plan.PATIENCE, 8.0))


def keep_clear(x, y):
    """In one of the README's keep-clear zones (metres), where the generator stands no house."""
    if any(math.hypot(x - cx, y - cy) <= r for (cx, cy), r in KEEP_CLEAR):
        return True
    if -330 <= x <= -280 and abs(y) < 12:
        return True
    return plan.path_gap(x, y) <= 6.0


DATA = ('BP_LogVoice_C', 'BP_Encounter_C', 'BP_Requirement_C', 'BP_Awakening_C', 'BP_ConclaveDirector_C')


def check_placements(world, place, houses):
    wet = {id(actor): w for actor, _, w in place.log}
    town = plan.REGIONS['Commons']
    unverified = 0
    for actor in labelled(world):
        if actor.cname in DATA or actor.label == 'Scene Sound Drum':
            continue
        x, y = actor.location.x / 100, actor.location.y / 100
        if abs(y) > 295.0 + 1e-6:
            fail('%s stands at y %.1f m, past the 295 m walk limit' % (actor.label, y))
        # A Divinity Ray over a drowned puzzle and the lake's own water sound belong over the water.
        intended = actor.cname == 'BP_DivinityRay_C' or actor.label == 'Scene Sound Water'
        if plan.in_lake(x, y) and not wet.get(id(actor)) and not intended:
            fail('%s stands in the lake at (%.0f, %.0f) m' % (actor.label, x, y))
        if houses:
            for row in houses:
                if scenario.gap(actor.location.x, actor.location.y, row) < 50 and actor.cname not in ('PointLight', 'BP_DivinityRay_C'):
                    fail('%s stands on a scatter footprint at (%.0f, %.0f) m' % (actor.label, row[0] / 100, row[1] / 100))
                    break
        elif math.hypot(x - town[0], y - town[1]) <= town[2]:
            if not keep_clear(x, y):
                fail('%s is in the town outside every keep-clear zone at (%.0f, %.0f) m (a house may stand there)' % (actor.label, x, y))
        elif plan.REGIONS['Old Quarter'] and math.hypot(x - plan.REGIONS['Old Quarter'][0], y - plan.REGIONS['Old Quarter'][1]) <= plan.REGIONS['Old Quarter'][2]:
            unverified += 1
    if not houses and unverified:
        warn('%d placements in the Old Quarter wait for scatter.json to be checked against its ruins (place() avoids them when it exists)' % unverified)


def shown_as(value):
    """What a Look was given, in words: a class by name, a Blueprint asset (not its class) by path."""
    if hasattr(value, 'ue_name'):
        return value.ue_name
    return 'the asset %s (not its generated class)' % value.path if isinstance(value, Asset) else repr(value)


def check_dress(key, npc, dress):
    """A person standing in their CAST row: the Mannequin body in its skin and garments on their bones, or the
    figure's Shape, and Look empty. Without a row (CAST unreadable, failed elsewhere) only the form is checked."""
    parts = {c.name: c for c in npc.components}
    body, shape = parts['Body'], parts['Shape']
    if body.mesh is None and shape.mesh is None:
        fail('%s: neither a body nor a figure' % key)
    if body.mesh is not None:
        if body.anim is None or not body.anim[0] or body.anim[0].path != scenario.IDLE or not body.anim[1]:
            fail('%s: the body does not loop MM_Idle' % key)
        if sorted(body.materials) != [0, 1]:
            fail('%s: the skin is not on both Mannequin slots' % key)
        for c in npc.components:
            if c.name in ('Lower', 'Upper', 'Head') and c.mesh is not None and (c.parent is not body or c.socket != {'Lower': 'pelvis', 'Upper': 'spine_05', 'Head': 'head'}[c.name]):
                fail('%s: %s is not on its bone' % (key, c.name))
        if dress:
            worn = (body.mesh.name, body.materials[0].name if 0 in body.materials else None,
                    *(parts[name].mesh.name if parts[name].mesh else None for name in ('Lower', 'Upper', 'Head')))
            want = ('SKM_%s_Simple' % dress['body'], 'MI_CP_%s' % dress['skin'], dress['lower'], dress['upper'], dress['head'])
            if worn != want:
                fail('%s: wears %s, its CAST row %s' % (key, worn, want))
    elif dress and shape.mesh is not None and shape.mesh.name != dress['shape']:
        fail('%s: stands as %s, its CAST row %s' % (key, shape.mesh.name, dress['shape']))
    if parts['Look'].child is not None:
        fail('%s: Look shows %s beside its %s' % (key, shown_as(parts['Look'].child), 'body' if body.mesh is not None else 'figure'))


def check_people(world):
    npcs = {a.props.get('Key'): a for a in world.actors if a.cname == 'BP_NPC_C'}
    voices = {a.props.get('Title'): a for a in world.actors if a.cname == 'BP_LogVoice_C'}
    table, _ = scenario.cast_table()
    # The scenario shows MetaHumans once its look() carries 'mh' or it sets any Look; until then a MetaHuman row stands
    # in its Mannequin look, which is right but shows no MetaHuman.
    knows = 'mh' in scenario.look(lore.PEOPLE[0], table) or any(
        c.child_set for npc in npcs.values() for c in npc.components if c.name == 'Look')
    shown, stand_ins = [], []
    for row in lore.PEOPLE:
        key = row[0]
        npc = npcs.get(key)
        if npc is None:
            fail('PEOPLE %s has no BP_NPC' % key)
            continue
        # A person's size is the body's (a child's MH look_scale on Look), never an actor scale: shown() relies on it.
        if npc.scale.to_tuple() != (1.0, 1.0, 1.0):
            fail('%s: BP_NPC stands at actor scale %s' % (key, npc.scale.to_tuple()))
        pages = lore.conversation_pages(row)
        if len(npc.props['Pages'].split('|')) != len(pages):
            fail('%s: %d pages in Pages, %d in the lore' % (key, len(npc.props['Pages'].split('|')), len(pages)))
        for page in pages:
            if '|' in page:
                fail('%s: a page holds "|", the page separator' % key)
        for line in npc.props['Pages'].replace('|', '~').split('~'):
            if len(line) > 70:
                warn('%s: a talk line runs %d characters' % (key, len(line)))
        # Someone with no Kokoro voice (Patience until the Shepherd falls) has no voice actors: a soundless one makes
        # PhysisNarrate log "Accessed None" on every page.
        voiced = bool(row[3])
        for k in range(len(pages)):
            title = lore.person_key(key, k)
            voice = voices.get(title)
            want = scenario.VOICES + '/' + voice_name(title)
            if not voiced:
                if voice is not None:
                    fail('%s page %d: a voice actor for someone with no voice' % (key, k))
                continue
            if voice is None:
                fail('%s page %d: no BP_LogVoice titled %r' % (key, k, title))
            elif not isinstance(voice.props.get('Voice'), Asset) or voice.props['Voice'].path != want:
                fail('%s page %d: voice %r, wanted %s' % (key, k, voice.props.get('Voice'), want))
        dress = table.get(key, {})
        mh = dress.get('mh')
        if not (mh and knows and look_built(cast_module.FILES['look'].format(key=mh))):
            if mh:
                stand_ins.append(key)
            check_dress(key, npc, dress)
            continue
        # A MetaHuman: Look holds its assembled Blueprint's class, and nothing of the stand-in stays dressed.
        look = next(c for c in npc.components if c.name == 'Look')
        if getattr(look.child, 'ue_name', None) != 'BP_%s_C' % mh:
            fail('%s: Look shows %s, wanted the class BP_%s_C of %s' % (key, shown_as(look.child), mh, cast_module.FILES['look'].format(key=mh)))
        size = cast_module.MH[mh].get('look_scale', 1.0)
        got = look.scale3d.to_tuple() if look.scale3d is not None else None
        if got is None or max(abs(g - size) for g in got) > 1e-6:
            fail('%s: Look at scale %s, wanted its MH look_scale %s' % (key, got, size))
        dressed = [c.name for c in npc.components if c.name in ('Body', 'Lower', 'Upper', 'Head', 'Shape') and c.mesh is not None]
        if dressed:
            fail('%s: %s still dressed beside the Look' % (key, ', '.join(dressed)))
        shown.append(key)
    if stand_ins and not knows:
        warn('the scenario never sets BP_NPC\'s Look (physis_conclave_scenario look() and wear()): %d MetaHuman rows stand in '
             'their Mannequin looks' % len(stand_ins))
    for title in [row[1] for row in lore.conclave_entries()] + [lore.ARRIVAL_LINE[0]]:
        if title not in voices:
            fail('Logbook %r has no BP_LogVoice' % title)
    # People one is meant to tell apart stand at least 6 m apart (Interact picks the first within 3 m).
    spots = {}
    for row in lore.PEOPLE:
        npc = npcs.get(row[0])
        if npc:
            spots.setdefault(row[1], set()).add((round(npc.location.x), round(npc.location.y)))
    flat = [(speaker, xy) for speaker, xys in spots.items() for xy in xys]
    for i, (sa, (ax, ay)) in enumerate(flat):
        for sb, (bx, by) in flat[i + 1:]:
            if sa != sb and math.hypot(ax - bx, ay - by) < 600:
                fail('%s and %s stand %.1f m apart' % (sa, sb, math.hypot(ax - bx, ay - by) / 100))
    return npcs, voices, shown, stand_ins


def check_meshes(names_built, report):
    used = sorted({path.rsplit('/', 1)[-1] for path in STUB.loaded if path.startswith(scenario.MESHES + '/')})
    contract = contract_names()
    written = {m for m in CONTRACT_MODULES if (MESH_TOOLS / (m + '.py')).exists()}
    missing_builder, contract_only = [], []
    for name in used:
        if names_built and name in names_built:
            continue
        if name in contract:
            contract_only.append(name)
            continue
        if name.startswith('SM_CP_G_'):
            missing_builder.append(name) if 'people' in written else contract_only.append(name)
            continue
        missing_builder.append(name)
    for name in missing_builder:
        fail('mesh %s is neither built by a generator nor in the README contract' % name)
    module_of = {'SM_CN_': ('architecture', 'districts'), 'SM_CE_': ('al_flora',), 'SM_CV_': ('al_flora',), 'SM_CP_': ('people',)}
    for name in contract_only:
        owners = next((m for prefix, m in module_of.items() if name.startswith(prefix)), ())
        if any(m in written for m in owners) and names_built is not None:
            fail('mesh %s is in the contract, but its generator (%s) does not build it' % (name, '/'.join(owners)))
    materials = sorted({path.rsplit('/', 1)[-1] for path in STUB.loaded if path.startswith(scenario.MATS + '/')})
    readme = (ROOT / 'Tools/conclave/README.md').read_text()
    assumed = [m for m in materials if m not in readme]
    return used, contract_only, materials, assumed


def check_level(world, place):
    by_class = {}
    for actor in labelled(world):
        by_class.setdefault(actor.cname, []).append(actor)
    rooms = {}
    for actor in by_class.get('BP_Encounter_C', []):
        room = actor.props['Room']
        if room in rooms:
            fail('room %d has two encounters (%s, %s)' % (room, rooms[room].label, actor.label))
        rooms[room] = actor
        if not 301 <= room <= 399:
            fail('%s uses room %d, outside 301-399' % (actor.label, room))
    drones = by_class.get('BP_TrainingDrone_C', [])
    held = {}
    for drone in drones:
        room = drone.props.get('RoomId', 0)
        held[room] = held.get(room, 0) + 1
        if room and room not in rooms:
            fail('%s is in room %d, which no encounter counts' % (drone.label, room))
        if drone.components[0].mesh is None or not drone.components[0].mesh.path.startswith(scenario.MESHES):
            fail('%s is not reskinned' % drone.label)
    for room, actor in rooms.items():
        if not held.get(room):
            fail('%s counts room %d, which holds no enemy (it would be won at once)' % (actor.label, room))
    combatants = [d for d in drones if not d.props.get('Static')]
    if not 135 <= len(combatants) <= 170:
        fail('%d combatants, about 150 wanted' % len(combatants))
    near = []
    for d in combatants:
        for sx, sy in place.stills:
            # BP_Checkpoint measures in 3-D (GetDistanceTo): an enemy on the Spire's climb above a Still Point is far.
            dz = d.location.z - (place.g.at(sx, sy) + 110)
            far = math.sqrt((d.location.x - sx) ** 2 + (d.location.y - sy) ** 2 + dz * dz)
            if far < 2990 and d.props.get('RoomId', 0) == 0:
                near.append('%s (%.0f m)' % (d.label, far / 100))
    if near:
        fail('%d loose enemies within 30 m of a Still Point: %s' % (len(near), ', '.join(near)))
    for cname in ('BP_Switch_C', 'BP_Relic_C', 'BP_Rise_C', 'BP_SettleBarrier_C', 'BP_AbilitySocket_C', 'BP_Pickup_C', 'BP_Platform_C'):
        for actor in by_class.get(cname, []):
            mesh = actor.components[0].mesh
            if mesh is None or not mesh.path.startswith(scenario.MESHES + '/'):
                fail('%s keeps its shared look (not reskinned into the palette)' % actor.label)
    for actor in by_class.get('BP_Hazard_C', []):
        material = actor.components[0].materials.get(0)
        if material is None or not material.path.startswith(scenario.MATS):
            fail('%s keeps the Center\'s wound look' % actor.label)
    kinds = {}
    for ray in by_class.get('BP_DivinityRay_C', []):
        kinds[ray.props['Kind']] = kinds.get(ray.props['Kind'], 0) + 1
        material = ray.components[0].materials.get(0)
        look = scenario.RAY_KINDS[ray.props['Kind']][0]
        if material is None or material.name != look:
            fail('%s wears %s, not %s' % (ray.label, material and material.name, look))
        top = ray.location.z + 50 * ray.scale.z
        if top > scenario.AXIS - 1500:
            fail('%s reaches %.0f m, into the Spine' % (ray.label, top / 100))
    if kinds != {0: 6, 1: 3, 2: 4}:
        fail('rays by kind %s, wanted 6 puzzles (0), 3 vaults (1), 4 Light Caches (2)' % kinds)
    for actor in by_class.get('PointLight', []):
        colour = actor.components[0].colour
        if colour is None or not palette.allowed((colour.r, colour.g, colour.b)):
            fail('%s lights in a colour outside the palette: %s' % (actor.label, colour and (colour.r, colour.g, colour.b)))
    if any(a.cname == 'TextRenderActor' for a in STUB.spawned):
        fail('3D text was placed')
    stills = by_class.get('BP_Checkpoint_C', [])
    if len(stills) != 8:
        fail('%d Still Points, 8 wanted' % len(stills))
    for actor in stills:
        key = (int(actor.location.x / 100), int(actor.location.y / 100))
        if key in CENTER_STILL:
            fail('%s has the same ,sp_%d_%d, token as a Center Still Point' % (actor.label, key[0], key[1]))
        if not actor.props.get('Objective'):
            fail('%s has no objective' % actor.label)
    beams = [a for a in labelled(world) if a.props.get('tags') and a.props['tags'][0].startswith('PylonBeam')]
    if sorted(a.props['tags'][0] for a in beams) != ['PylonBeam1', 'PylonBeam2', 'PylonBeam3'] or not all(a.hidden for a in beams):
        fail('pylon beams: %s (wanted PylonBeam1-3, hidden in game)' % [(a.label, a.props['tags'], a.hidden) for a in beams])
    for actor in [a for a in world.actors if a.cname == 'BP_Awakening_C']:
        if actor.props.get('TestArrival') is not False:
            fail('%s is saved with TestArrival on' % actor.label)
    if world.saves < 1:
        fail('%s was never saved' % world.path)
    return by_class, rooms, combatants


def check_spire(place):
    marks = place.marks
    start, crown, lift = marks.get('Spire Climb Start'), marks.get('Spire Crown'), marks.get('Spire Lift')
    if not (start and crown and lift):
        fail('the Spire climb is incomplete: %s' % sorted(k for k in marks if k.startswith('Spire')))
        return None
    rise = (crown[2] - start[2]) / 100 + 4
    if not 55 <= rise <= 65:
        fail('the Spire crown is %.1f m above the plaza, about 60 m wanted' % rise)
    spire = plan.SPIRE
    for actor, _, _ in place.log:
        if actor.label.startswith(('Scene Spire Platform', 'Scene Spire Ramp')) and actor.location.z > start[2] - 500:
            r = math.hypot(actor.location.x / 100 - spire[0], actor.location.y / 100 - spire[1])
            if r < 27.5:
                fail('%s is %.1f m from the Spire axis (the crystal is 24 m across its base)' % (actor.label, r))
    return rise


def check_portal():
    center = STUB.world(scenario.CENTER_LEVEL)
    awakening = Actor(center, 'BP_Awakening_C', Vector(-68400, 0, 0), None)
    awakening.label, awakening.props['TestArrival'] = 'Awakening Director', True
    glade = Actor(center, 'BP_Checkpoint_C', Vector(-68400, 0, 110), None)
    glade.label = 'Scene Still Point Glade'
    stale = Actor(center, 'BP_Current_C', Vector(0, 0, 0), None)
    stale.label = 'Scene Conclave Current'  # an earlier version's label: replaced
    pedestal = Actor(center, 'BP_Switch_C', Vector(76000, 0, 4270), None)
    pedestal.label = 'Scene Heartbloom Pedestal'
    center.actors += [awakening, glade, stale, pedestal]
    STUB.dirty = ['L_CenterOfTheUniverse']
    try:
        scenario.portal()
        fail('portal() saved over unsaved changes in the open Center')
    except RuntimeError:
        pass
    STUB.dirty = []
    result = scenario.portal()
    if STUB.current is not center:
        fail('portal() did not open the Center')
    if stale in center.actors:
        fail('portal() left its earlier current')
    if glade not in center.actors:
        fail('portal() removed a Center scenario actor')
    currents = [a for a in center.actors if a.cname == 'BP_Current_C']
    if len(currents) != 1 or currents[0].props.get('Dest') != 1 or currents[0].props.get('Need') != ',mend,':
        fail('portal(): currents %s' % [(a.label, a.props) for a in currents])
    else:
        c = currents[0].location
        if abs(c.z - (3400 + 600)) > 60 or not 1400 <= math.hypot(c.x - 76000, c.y) <= 1900:
            fail('portal(): the current stands at %s, not on the sanctum ring floor 14-19 m from the pedestal' % (c.to_tuple(),))
        back = [a for a in center.actors if a.props.get('tags') == ['ConclaveReturn']]
        if len(back) != 1 or math.hypot(back[0].location.x - c.x, back[0].location.y - c.y) < 250:
            fail('portal(): the return marker is missing or inside the current\'s reach')
    # No tutorial strip or scan tag in the Center: neither could be hidden before Mend, and the strip replaced the
    # Heartbloom's Done text (Center session's Play test, 2026-11-07).
    if any(a.label.startswith('Conclave Current') and a.cname in ('BP_TutorialTrigger_C', 'BP_ScanTarget_C') for a in center.actors):
        fail('portal(): a tutorial strip or scan tag in the Center, shown before Mend')
    if any(a.label.startswith(('Scene ', 'Cine ')) for a in center.actors if a.cname in ('BP_Current_C', 'BP_TutorialTrigger_C', 'BP_LogVoice_C') and a is not stale):
        fail("portal(): a portal actor is labelled 'Scene ...' or 'Cine ...', which the Center's scenario deletes")
    if pedestal.props.get('Done') != scenario.HEARTBLOOM_DONE:
        fail('portal(): the Heartbloom pedestal\'s Done text was not set')
    c = currents[0].location if currents else None
    if c is not None and math.hypot(c.x - 76000, c.y) < 1400:
        fail('portal(): the current stands %.1f m from the pedestal, among the sanctum crystals (r 7-7.5 m)' % (math.hypot(c.x - 76000, c.y) / 100))
    if awakening.props.get('TestArrival') is not False:
        fail('portal(): BP_Awakening saved with TestArrival on')
    if center.saves < 1:
        fail('portal(): the Center was not saved')
    return result


def check_cast():
    """The cast table the editor reads (Content/Python/physis_conclave_cast.py, pure Python) against the lore and
    the people generator's meshes: every person has a look, every mesh it names is built, and people.py's own cast
    checks pass (both tables and the MetaHuman rows; they assert at its import, so an AssertionError is theirs)."""
    table, source = scenario.cast_table()
    if not table:
        fail('physis_conclave_cast.CAST could not be read')
        return 'missing'
    missing = [row[0] for row in lore.PEOPLE if row[0] not in table]
    if missing:
        fail('CAST has no look for %s' % ', '.join(missing))
    try:
        import people
    except AssertionError as error:
        fail(str(error))
        return source
    except Exception as error:
        warn('people.py could not be imported offline to check CAST (%s)' % error)
        return source
    try:
        import check
        built = {part.name for part in check.builds(people)}
        named = {v for look in table.values() for k, v in look.items() if k in ('lower', 'upper', 'head', 'shape') and v}
        unknown = sorted(named - built)
        if unknown:
            fail('CAST names meshes people.py does not build: %s' % unknown)
    except Exception as error:
        warn('people.py could not be built offline to check CAST (%s)' % error)
    return source


def prune(rounds=6):
    """Removes the scatter rows (scatter.json) whose footprints a set piece stands on, then lays the scenario out
    again until none is met. Run after drum.write_scatter: the generator's random placement cannot know where the
    scenario's rings, lanes and courts reach, and keep-clear circles for each one only move the problem (scatter
    regenerates differently). Removing a row only frees ground, so the layout settles in a round or two."""
    path = scenario.ROOT / 'Art/Meshes/Conclave/scatter.json'
    import json as _json
    removed_total = 0
    for round_ in range(rounds):
        the_ground, _ = ground()
        scenario.place(the_ground)
        world = STUB.current
        data = _json.loads(path.read_text())
        doomed = set()
        for mesh, items in data.items():
            size = scenario.FOOTPRINT.get(mesh) or next((v for k, v in scenario.FOOTPRINT.items() if mesh.startswith(k)), None)
            if not size:
                continue
            for index, (x, y, z, pitch, yaw, roll, s) in enumerate(items):
                row = (x, y, size[0] * 50 * s, size[1] * 50 * s, math.radians(yaw))
                for actor in labelled(world):
                    if actor.cname in DATA or actor.cname in ('PointLight', 'BP_DivinityRay_C') or actor.label == 'Scene Sound Drum':
                        continue
                    if scenario.gap(actor.location.x, actor.location.y, row) < 50:
                        doomed.add((mesh, index))
                        break
        if not doomed:
            print('prune: settled after %d round(s), %d scatter rows removed' % (round_, removed_total))
            return removed_total
        for mesh in data:
            data[mesh] = [item for index, item in enumerate(data[mesh]) if (mesh, index) not in doomed]
        path.write_text(_json.dumps(data))
        removed_total += len(doomed)
        print('prune: round %d removed %d rows' % (round_ + 1, len(doomed)))
    print('prune: still meeting scatter after %d rounds (%d removed)' % (rounds, removed_total))
    return removed_total


def main():
    if '--prune' in sys.argv:
        prune()
        FAIL.clear()
        WARN.clear()
    the_ground, source = ground()
    # The level as the level build leaves it: something there already, which clear() must not remove.
    conclave = STUB.world(scenario.LEVEL)
    terrain = Actor(conclave, 'StaticMeshActor', Vector(0, 0, 0), None)
    terrain.label = 'Terrain 0 0'
    conclave.actors.append(terrain)
    first = scenario.place(the_ground)
    world = STUB.current
    if world is not conclave:
        fail('place() did not open %s' % scenario.LEVEL)
    count_first = len(labelled(world))
    second = scenario.place(the_ground)
    if len(labelled(world)) != count_first or second['placed'] != first['placed']:
        fail('a second place() left %d Scene actors (first %d): clear() does not replace the scenario' % (len(labelled(world)), count_first))
    if terrain not in world.actors:
        fail('clear() removed the level build\'s actors')
    place = scenario.LAST
    footprints, _ = scenario.town()
    check_placements(world, place, footprints)
    npcs, voices, shown, stand_ins = check_people(world)
    names, report = builder_names()
    used, contract_only, materials, assumed = check_meshes(names, report)
    by_class, rooms, combatants = check_level(world, place)
    rise = check_spire(place)
    reach, rules, expected, gates = solve(place)
    cast = check_cast()
    portal = check_portal()

    print('Conclave scenario, offline (%s)' % source)
    print('  placed %d actors (%d Scene actors in the level); %d combatants; %d encounters, rooms %s' %
          (first['placed'], count_first, len(combatants), len(rooms), ', '.join(str(r) for r in sorted(rooms))))
    counts = ', '.join('%s %d' % (c.replace('_C', ''), len(v)) for c, v in sorted(by_class.items(), key=lambda kv: -len(kv[1])))
    print('  by class: ' + counts)
    print('  people: %d NPCs, %d voice actors; CAST: %s (%s), looks %s: %d MetaHumans in Look, %d MetaHuman rows standing in (%s)' %
          (len(npcs), len(voices), first['cast'], cast, cast_module.LOOKS, len(shown), len(stand_ins), ', '.join(stand_ins) or 'none'))
    print('  token graph: %d givers, %d tokens reachable from %s; %d Light Step gates checked; out of reach by design: %s' %
          (len(rules), len(reach), START, gates, ', '.join(sorted(expected)) or 'none'))
    print('  meshes used: %d (%d checked against the README contract only, their generator not built yet)' % (len(used), len(contract_only)))
    print('  generators: ' + '; '.join(report))
    print('  materials: %s%s' % (', '.join(materials), ('; not in the README: ' + ', '.join(assumed)) if assumed else ''))
    print('  Spire crown %.1f m above the plaza; rays %d; houses checked %d' % (rise or 0, first['rays'], first['houses_checked']))
    print('  portal: %s' % portal)
    if not QUIET:
        for name, spot in sorted(first['marks'].items()):
            print('    %-28s %s' % (name, spot))
    for message in WARN:
        print('  warning: ' + message)
    if FAIL:
        print('\nFAILED (%d):' % len(FAIL))
        for message in FAIL:
            print('  - ' + message)
        sys.exit(1)
    print('\nall checks passed')


if __name__ == '__main__':
    main()
