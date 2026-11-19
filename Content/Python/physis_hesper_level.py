"""The level of Hesper (`hesper:level`): L_Hesper's land, pools, light and scatter, from Tools/build_physis_hesper.py's
height.bin and scatter.json. Everything placed here goes in the outliner folder Hesper (the scenario's is HesperScene),
so a rebuild replaces only its own actors.

The look (author, 2026-11-18): realistic, a warm dusk. The sun sits 7 degrees above the western horizon for ever: long
raking gold light across the plateau from the west, long violet shadows reaching east, an amber-rose sky going deep
blue overhead, a warm haze filling the drop beyond the western edge and lying low in the city; no post-process
stylisation. Kathodos's meshes are regraded (physis_hesper_tools.regrade) so its pale stone reads as honey.
"""
import json
import math
import struct

import unreal

import physis_hesper_plan as plan
import physis_hesper_tools as T
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
    """Art/Meshes/Hesper/height.bin (float32 metres, index i * ny + j, i along x) with height.json."""

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

SUN_LUX = 14.0                 # the game's exposure convention (physis_grove_level: lights and glows are tuned to it)
SUN_PITCH, SUN_YAW = -7.0, 75.0     # the light travels east-north-east: the sun stands low in the west-south-west
SUN_COLOUR = (1.0, .64, .38)
FOG = {'fog_density': .0018, 'fog_height_falloff': .06, 'start_distance': 2500.0, 'fog_max_opacity': .7, 'fog_cutoff_distance': 0.0}
FOG_LOW = {'fog_density': .045, 'fog_height_falloff': .18, 'fog_height_offset': -6000.0}   # the haze filling the drop
FOG_COLOUR, FOG_BRIGHT = (.85, .55, .45), .3
FOG_SUN, FOG_SUN_BRIGHT = (1.0, .58, .28), 1.6
POST_CHANGES = {'bloom_intensity': .9, 'auto_exposure_bias': .25, 'vignette_intensity': .35}
RAYLEIGH = (.175, .41, 1.0)     # the engine's own: a low sun makes the horizon amber and the zenith deep blue


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
    cn.try_set(sa, 'rayleigh_scattering_scale', .0331, failed)
    cn.try_set(sa, 'mie_scattering_scale', .006, failed)
    cn.try_set(sa, 'mie_anisotropy', .82, failed)
    sun = spawn(unreal.DirectionalLight, 'Sun', (0, 0, 30000), (0, SUN_PITCH, SUN_YAW), tags=('HesperSun',))
    comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property('intensity', SUN_LUX)
    comp.set_light_color(gt.linear(SUN_COLOUR))
    for key, value in (('atmosphere_sun_light', True), ('light_source_angle', 1.6), ('forward_shading_priority', 1),
                       ('dynamic_shadow_distance_movable_light', 30000.0), ('dynamic_shadow_cascades', 4), ('contact_shadow_length', .03),
                       ('indirect_lighting_intensity', 1.3), ('volumetric_scattering_intensity', 2.0)):
        cn.try_set(comp, key, value, failed)
    light = spawn(unreal.SkyLight, 'Sky Light', (0, 0, 20000))
    sc = light.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for key, value in (('real_time_capture', True), ('intensity', 1.15), ('lower_hemisphere_is_black', False)):
        cn.try_set(sc, key, value, failed)
    fog = spawn(unreal.ExponentialHeightFog, 'Haze', (0, 0, 0))
    haze = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    for key, value in FOG.items():
        cn.try_set(haze, key, value, failed)
    cn.try_set(haze, 'fog_inscattering_luminance', gt.linear(tuple(c * FOG_BRIGHT for c in FOG_COLOUR)), failed)
    cn.try_set(haze, 'sky_atmosphere_ambient_contribution_color_scale', gt.linear((0.0, 0.0, 0.0)), failed)
    cn.try_set(haze, 'directional_inscattering_luminance', gt.linear(tuple(c * FOG_SUN_BRIGHT for c in FOG_SUN)), failed)
    cn.try_set(haze, 'directional_inscattering_exponent', 6.0, failed)
    cn.try_set(haze, 'directional_inscattering_start_distance', 2000.0, failed)
    for key, value in gl.VOLUMETRIC:
        cn.try_set(haze, key, value, failed)
    try:
        layer = unreal.ExponentialHeightFogData()
        for key, value in FOG_LOW.items():
            layer.set_editor_property(key, value)
        haze.set_editor_property('second_fog_data', layer)
    except Exception as error:
        failed.append('second_fog_data: %s' % error)
    volume = spawn(unreal.PostProcessVolume, 'Hesper Look')
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
        raise RuntimeError('stop Play before building Hesper')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None or world.get_path_name().split('.')[0] != LEVEL:
        dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError('unsaved changes in %s: save or discard them before hesper:level' % ', '.join(dirty))
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
    if name.startswith('SM_A'):
        return unreal.load_asset('/Game/Arche/Meshes/' + name)
    return unreal.load_asset(T.MESHES + '/' + name)


def terrain():
    missing = []
    for i in range(plan.TILES_X):
        for j in range(plan.TILES_Y):
            name = 'SM_ST_Terrain_%d_%d' % (i, j)
            if gl.mesh_actor('Terrain %d %d' % (i, j), mesh(name), (0, 0, 0), folder=FOLDER + '/Terrain') is None:
                missing.append(name)
    floor = gl.mesh_actor('Haze Floor', mesh('SM_ST_Haze'), (0, 0, -17000.0), folder=FOLDER + '/Terrain', collide=False, shadow=False)
    if floor is None:
        missing.append('SM_ST_Haze')
    return {'tiles': plan.TILES_X * plan.TILES_Y, 'missing': missing}


def pools():
    """The Reed Terraces' water: one sheet stretched over each pool at its surface (the terrain hides the edges)."""
    sheet = mesh('SM_ST_Pool')
    made = []
    for k, (x, y, hx, hy, rise, yaw) in enumerate(plan.POOLS):
        z = (plan.rise_z(x) + rise) * CM
        actor = gl.mesh_actor('Pool %d' % k, sheet, (x * CM, y * CM, z), (0, 0, yaw), (hx + 4.0, hy + 4.0, 1.0), folder=FOLDER + '/Water', collide=False,
                              shadow=False)
        if actor is not None:
            made.append(round(z))
    return {'pools': made}


def edge():
    """The western edge: blocking volumes 12 m long, 30 m tall, standing 1 m outside the parapet line from rim to rim,
    so nobody steps into the drop; and a floor far below that ends a fall (and a fall ends at the last Still Point:
    BP_Physis's kill height is set in the World Settings)."""
    sub = actors()
    count = 0
    x = -plan.HALF_X + 20.0
    while x < plan.HALF_X - 20.0:
        y = plan.edge_y(x) + 1.0
        if plan.rim(x, y) < 1.15:
            heading = math.degrees(math.atan2(plan.edge_y(x + 3.0) - plan.edge_y(x - 3.0), 6.0))
            wall = sub.spawn_actor_from_class(unreal.BlockingVolume, unreal.Vector(x * CM, y * CM, 4000.0), unreal.Rotator(0, 0, -heading))
            wall.set_actor_label('Edge %02d' % count)
            wall.set_folder_path(FOLDER + '/Edge')
            wall.set_actor_scale3d(unreal.Vector(6.4, .5, 40.0))      # the brush is 200 cm: 12.8 m along the edge, 1 m thick, 80 m tall
            count += 1
        x += 12.0
    try:
        settings = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
        settings.set_editor_property('kill_z', -15000.0)
    except Exception:
        pass
    return {'volumes': count}


# mesh: (collides, cull distance cm (0 never), casts shadow)
RULES = {'SM_GV_Grass': (False, 7000, False), 'SM_GS_Stone': (False, 25000, True), 'SM_AV_Crystal0': (False, 30000, True),
         'SM_AV_Crystal1': (True, 40000, True), 'SM_AN_Lantern': (True, 40000, True)}
RULE_DEFAULT = (True, 0, True)
OVERRIDES = {'SM_GS_Boulder': 'MI_HS_Scan_Boulder', 'SM_GS_Stone': 'MI_HS_Scan_Stone', 'SM_GS_CliffC': 'MI_HS_Scan_CliffC', 'SM_GV_Grass': 'MI_HS_DuskGrass'}


def scatter():
    data = gt.read_json(T.ART / 'scatter.json')
    counts, failed, missing, swapped = {}, [], [], 0
    for name, rows in sorted(data.items()):
        asset = mesh(name)
        if asset is None:
            missing.append(name)
            continue
        collide, cull, shadow = RULES.get(name, RULE_DEFAULT)
        placed = [tuple(row) for row in rows]
        actor = gl.instanced('Scatter ' + name[6:], asset, placed, collide, cull, shadow, FOLDER + '/Scatter', failed, rt=not name.startswith('SM_GV_'))
        override = OVERRIDES.get(name)
        material = unreal.load_asset(T.MATS + '/' + override) if override else None
        for part in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent):
            for slot in range(max(1, part.get_num_materials())):
                if material is not None:
                    part.set_material(slot, material)
                else:
                    new = T.twin(part.get_material(slot))
                    if new is not None:
                        part.set_material(slot, new)
                        swapped += 1
        counts[name] = len(placed)
    return {'instances': counts, 'total': sum(counts.values()), 'missing': missing, 'regraded_slots': swapped, 'failed': sorted(set(failed))}


def start(g):
    """Where editor play starts (the Sunward Stair), and the level's directors: BP_Awakening marks an open-world level
    for the shared graphs (TestArrival off); BP_HesperDirector marks Hesper and runs what is its own."""
    x, y = plan.STAIR_STILL[0] * CM, plan.STAIR_STILL[1] * CM
    sub = actors()
    if not any(isinstance(actor, unreal.PlayerStart) for actor in sub.get_all_level_actors()):
        player = sub.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(x, y, g.at(x, y) + 120), unreal.Rotator(0, 0, 10))
        player.set_actor_label('Physis Arrives')
        player.set_folder_path(FOLDER)
    made = []
    lx, ly = plan.STAIR[0] * CM, plan.STAIR[1] * CM
    for name, label in (('BP_Awakening', 'Awakening Director'), ('BP_HesperDirector', 'Hesper Director')):
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
    report['pools'] = pools()
    report['edge'] = edge()
    report['look'] = look()
    report['scatter'] = scatter()
    report['start'] = start(g)
    save_level()
    return report


def execute(part):
    if part == 'look':
        report = {'removed': open_level((FOLDER + '/Light',)), 'look': look()}
    elif part == 'scatter':
        report = {'removed': open_level((FOLDER + '/Scatter',)), 'scatter': scatter()}
    elif part == 'edge':
        report = {'removed': open_level((FOLDER + '/Edge',)), 'edge': edge()}
    elif part == 'start':
        report = {'removed': open_level((FOLDER + '/Director',)), 'start': start(Ground())}
    else:
        raise ValueError('unknown hesper level part ' + part)
    save_level()
    return report
