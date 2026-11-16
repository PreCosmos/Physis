"""The level of Arche (`arche:level`): L_Arche's land, water, light and scatter, from Tools/build_physis_arche.py's
height.bin and scatter.json. Everything placed here goes in the outliner folder Arche (the scenario's is ArcheScene),
so a rebuild replaces only its own actors.

The look (author, 2026-11-16): realistic, cool. A small cold sun stands low in the south-east, blue-white; the sky is
thin and deep, the haze pale blue with a low mist lying in the Great Chasm; no post-process stylisation. Bloom is a
little stronger than Earth's so crystal and the Vigil's light keep luminous edges.
"""
import json
import math
import struct

import unreal

import physis_arche_plan as plan
import physis_arche_tools as T
import physis_conclave_tools as cn
import physis_gameplay_tools as game
import physis_grove_level as gl
import physis_grove_tools as gt

CM = T.CM
FOLDER = T.FOLDER
LEVEL = T.LEVEL
library = unreal.EditorAssetLibrary


def actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Ground:
    """Art/Meshes/Arche/height.bin (float32 metres, index i * ny + j, i along x) with height.json."""

    def __init__(self):
        meta = json.loads((T.ART / 'height.json').read_text())
        self.half_x, self.half_y, self.cell = float(meta['half_x']), float(meta['half_y']), float(meta['cell'])
        self.nx, self.ny = int(meta['nx']), int(meta['ny'])
        self.water = float(meta.get('water', plan.WATER))
        self.h = struct.unpack('<%df' % (self.nx * self.ny), (T.ART / 'height.bin').read_bytes()[:self.nx * self.ny * 4])

    def metres(self, x, y):
        fx, fy = (x + self.half_x) / self.cell, (y + self.half_y) / self.cell
        i, j = max(0, min(int(math.floor(fx)), self.nx - 2)), max(0, min(int(math.floor(fy)), self.ny - 2))
        u, v = min(max(fx - i, 0.0), 1.0), min(max(fy - j, 0.0), 1.0)
        h, n = self.h, self.ny
        return h[i * n + j] * (1 - u) * (1 - v) + h[(i + 1) * n + j] * u * (1 - v) + h[i * n + j + 1] * (1 - u) * v + h[(i + 1) * n + j + 1] * u * v

    def at(self, x, y):
        """Ground height in cm at Unreal (x, y) in cm."""
        return self.metres(x / CM, y / CM) * CM


# ---------------------------------------------------------------- the look

SUN_LUX = 20.0                 # the game's exposure convention (physis_grove_level: lights and glows are tuned to it)
SUN_PITCH, SUN_YAW = -26.0, 128.0
SUN_COLOUR = (.84, .92, 1.0)
FOG = {'fog_density': .0035, 'fog_height_falloff': .06, 'start_distance': 1500.0, 'fog_max_opacity': .7, 'fog_cutoff_distance': 0.0}
FOG_LOW = {'fog_density': .02, 'fog_height_falloff': .35, 'fog_height_offset': -3200.0}
FOG_COLOUR, FOG_BRIGHT = (.42, .56, .95), .35
FOG_SUN, FOG_SUN_BRIGHT = (.80, .90, 1.0), .9
POST_CHANGES = {'bloom_intensity': .8, 'auto_exposure_bias': .1, 'vignette_intensity': .3}
RAYLEIGH = (.10, .30, .95)     # a deeper, colder sky than Earth's


def spawn(cls, label, place=(0, 0, 0), rot=(0, 0, 0), folder=FOLDER + '/Light', tags=()):
    actor = actors().spawn_actor_from_class(cls, unreal.Vector(*place), unreal.Rotator(*rot))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    if tags:
        actor.set_editor_property('tags', list(tags))
    return actor


def look():
    failed = []
    sky = spawn(unreal.SkyAtmosphere, 'Atmosphere')
    sa = sky.get_component_by_class(unreal.SkyAtmosphereComponent)
    cn.try_set(sa, 'rayleigh_scattering', gt.linear(RAYLEIGH), failed)
    cn.try_set(sa, 'rayleigh_scattering_scale', .034, failed)
    cn.try_set(sa, 'mie_scattering_scale', .002, failed)
    sun = spawn(unreal.DirectionalLight, 'Sun', (0, 0, 30000), (0, SUN_PITCH, SUN_YAW), tags=('ArcheSun',))
    comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property('intensity', SUN_LUX)
    comp.set_light_color(gt.linear(SUN_COLOUR))
    for key, value in (('atmosphere_sun_light', True), ('light_source_angle', .45), ('forward_shading_priority', 1),
                       ('dynamic_shadow_distance_movable_light', 30000.0), ('dynamic_shadow_cascades', 4), ('contact_shadow_length', .03),
                       ('indirect_lighting_intensity', 1.2), ('volumetric_scattering_intensity', 1.4)):
        cn.try_set(comp, key, value, failed)
    light = spawn(unreal.SkyLight, 'Sky Light', (0, 0, 20000))
    sc = light.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for key, value in (('real_time_capture', True), ('intensity', 1.0), ('lower_hemisphere_is_black', False)):
        cn.try_set(sc, key, value, failed)
    fog = spawn(unreal.ExponentialHeightFog, 'Haze', (0, 0, plan.TIER[0] * CM))
    haze = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    for key, value in FOG.items():
        cn.try_set(haze, key, value, failed)
    cn.try_set(haze, 'fog_inscattering_luminance', gt.linear(tuple(c * FOG_BRIGHT for c in FOG_COLOUR)), failed)
    cn.try_set(haze, 'sky_atmosphere_ambient_contribution_color_scale', gt.linear((0.0, 0.0, 0.0)), failed)
    cn.try_set(haze, 'directional_inscattering_luminance', gt.linear(tuple(c * FOG_SUN_BRIGHT for c in FOG_SUN)), failed)
    cn.try_set(haze, 'directional_inscattering_exponent', 10.0, failed)
    cn.try_set(haze, 'directional_inscattering_start_distance', 3000.0, failed)
    for key, value in gl.VOLUMETRIC:
        cn.try_set(haze, key, value, failed)
    try:
        layer = unreal.ExponentialHeightFogData()
        for key, value in FOG_LOW.items():
            layer.set_editor_property(key, value)
        haze.set_editor_property('second_fog_data', layer)
    except Exception as error:
        failed.append('second_fog_data: %s' % error)
    volume = spawn(unreal.PostProcessVolume, 'Arche Look')
    volume.set_editor_property('unbound', True)
    settings = volume.settings
    for key, value in gl.POST:
        try:
            settings.set_editor_property(key, POST_CHANGES.get(key, value))
        except Exception as error:
            failed.append('%s: %s' % (key, error))
    blendables = unreal.WeightedBlendables()   # no post-process material
    blendables.set_editor_property('array', [])
    settings.set_editor_property('weighted_blendables', blendables)
    volume.set_editor_property('settings', settings)
    return {'sun': [SUN_PITCH, SUN_YAW], 'failed': failed}


# ---------------------------------------------------------------- level file

def open_level(prefixes=(FOLDER,)):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if les.is_in_play_in_editor():
        raise RuntimeError('stop Play before building Arche')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None or world.get_path_name().split('.')[0] != LEVEL:
        dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError('unsaved changes in %s: save or discard them before arche:level' % ', '.join(dirty))
        if library.does_asset_exist(LEVEL):
            les.load_level(LEVEL)
        elif not les.new_level(LEVEL):
            raise RuntimeError('could not create ' + LEVEL)
    sub = actors()
    removed = 0
    for actor in sub.get_all_level_actors():
        folder = str(actor.get_folder_path())
        if not isinstance(actor, unreal.WorldSettings) and any(folder == p or folder.startswith(p + '/') for p in prefixes):
            sub.destroy_actor(actor)
            removed += 1
    return removed


def save_level():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    path = world.get_path_name().split('.')[0]
    if path != LEVEL:
        raise RuntimeError('%s is open, not %s: nothing saved' % (path, LEVEL))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


def mesh(name):
    if name.startswith('SM_GS_'):
        return unreal.load_asset(gt.SCANS + '/' + name)
    if name.startswith('SM_GV_'):
        return unreal.load_asset(gt.MESHES + '/' + name)
    return unreal.load_asset(T.MESHES + '/' + name)


def terrain():
    missing = []
    for i in range(plan.TILES_X):
        for j in range(plan.TILES_Y):
            name = 'SM_AT_Terrain_%d_%d' % (i, j)
            if gl.mesh_actor('Terrain %d %d' % (i, j), mesh(name), (0, 0, 0), folder=FOLDER + '/Terrain') is None:
                missing.append(name)
    return {'tiles': plan.TILES_X * plan.TILES_Y, 'missing': missing}


def water(g):
    """The Cisterns' sheet, and swimming under it: a water PhysicsVolume from the waterline down past the bed."""
    sheet = mesh('SM_AT_Cistern')
    if gl.mesh_actor('Cistern', sheet, (0, 0, 0), folder=FOLDER + '/Water', collide=False, shadow=False) is None:
        return {'missing': ['SM_AT_Cistern']}
    box = sheet.get_bounding_box()
    x0, x1, y0, y1 = box.min.x, box.max.x, box.min.y, box.max.y
    top, bottom = g.water * CM, plan.CISTERN_BED * CM - 300.0
    sub = actors()
    volume = sub.spawn_actor_from_class(unreal.PhysicsVolume, unreal.Vector((x0 + x1) / 2, (y0 + y1) / 2, (top + bottom) / 2))
    volume.set_actor_label('Water Volume')
    volume.set_folder_path(FOLDER + '/Water')
    volume.set_actor_scale3d(unreal.Vector((x1 - x0) / 200.0, (y1 - y0) / 200.0, (top - bottom) / 200.0))
    volume.set_editor_property('water_volume', True)
    volume.set_editor_property('fluid_friction', .35)
    volume.set_editor_property('terminal_velocity', 600.0)
    director = sub.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/BP_SwimDirector').generated_class(), unreal.Vector(0, 0, 0))
    director.set_actor_label('Swim Director')
    director.set_folder_path(FOLDER + '/Water')
    return {'volume_cm': [x0, x1, y0, y1, bottom, top]}


# mesh: (collides, cull distance cm (0 never), casts shadow)
RULES = {'SM_GV_Grass': (False, 7000, False), 'SM_AV_Crystal0': (False, 30000, True), 'SM_AV_Crystal1': (True, 45000, True),
         'SM_AV_Crystal2': (True, 60000, True), 'SM_AV_CrystalGreat': (True, 0, True), 'SM_AN_Lantern': (True, 40000, True),
         'SM_GS_Stone': (False, 25000, True)}
RULE_DEFAULT = (True, 0, True)
OVERRIDES = {'SM_GV_Grass': 'MI_AR_FrostGrass', 'SM_GS_Boulder': 'MI_AR_Scan_Boulder', 'SM_GS_Stone': 'MI_AR_Scan_Stone',
             'SM_GS_CliffC': 'MI_AR_Scan_CliffC'}


def scatter():
    data = gt.read_json(T.ART / 'scatter.json')
    counts, failed, missing = {}, [], []
    for name, rows in sorted(data.items()):
        if name == 'SM_GV_Grass':
            continue   # Earth's grass stays green under any tint, and Arche grows crystal, not grass
        air = name.startswith('Air:')
        stem = name.split(':', 1)[1] if air else name
        asset = mesh(stem)
        if asset is None:
            missing.append(stem)
            continue
        collide, cull, shadow = (False, 0, True) if air else RULES.get(stem, RULE_DEFAULT)
        placed = [tuple(row) for row in rows]
        actor = gl.instanced(('Air ' if air else 'Scatter ') + stem[6:], asset, placed, collide, cull, shadow, FOLDER + ('/Air' if air else '/Scatter'),
                             failed, rt=not stem.startswith('SM_GV_'), tags=('ArcheScar',) if air else ())
        override = OVERRIDES.get(stem)
        material = unreal.load_asset(T.MATS + '/' + override) if override else None
        if material is not None:
            for part in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent):
                for slot in range(max(1, part.get_num_materials())):
                    part.set_material(slot, material)
        counts[name] = len(placed)
    return {'instances': counts, 'total': sum(counts.values()), 'missing': missing, 'failed': sorted(set(failed))}


def start(g):
    """Where editor play starts (the Landing), and the level's directors: BP_Awakening marks an open-world level for
    the shared graphs (TestArrival off); BP_ArcheDirector marks Arche and runs what is its own."""
    x, y = plan.LANDING_STILL[0] * CM, plan.LANDING_STILL[1] * CM
    sub = actors()
    if not any(isinstance(actor, unreal.PlayerStart) for actor in sub.get_all_level_actors()):
        player = sub.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(x, y, g.at(x, y) + 120), unreal.Rotator(0, 0, 20))
        player.set_actor_label('Physis Arrives')
        player.set_folder_path(FOLDER)
    made = []
    lx, ly = plan.LANDING[0] * CM, plan.LANDING[1] * CM
    for name, label in (('BP_Awakening', 'Awakening Director'), ('BP_ArcheDirector', 'Arche Director')):
        blueprint = unreal.load_asset(game.BLUEPRINTS + '/' + name)
        if blueprint is None:
            continue
        actor = sub.spawn_actor_from_class(blueprint.generated_class(), unreal.Vector(lx, ly, g.at(lx, ly)))
        actor.set_actor_label(label)
        actor.set_folder_path(FOLDER + '/Director')
        if name == 'BP_Awakening':
            actor.set_editor_property('TestArrival', False)
        made.append(label)
    return {'directors': made}


def build_level():
    report = {'removed': open_level()}
    g = Ground()
    report['terrain'] = terrain()
    report['water'] = water(g)
    report['look'] = look()
    report['scatter'] = scatter()
    report['start'] = start(g)
    save_level()
    return report


def execute(part):
    if part == 'look':
        report = {'removed': open_level((FOLDER + '/Light',)), 'look': look()}
    elif part == 'scatter':
        report = {'removed': open_level((FOLDER + '/Scatter', FOLDER + '/Air')), 'scatter': scatter()}
    elif part == 'start':
        report = {'removed': open_level((FOLDER + '/Director',)), 'start': start(Ground())}
    else:
        raise ValueError('unknown arche level part ' + part)
    save_level()
    return report
