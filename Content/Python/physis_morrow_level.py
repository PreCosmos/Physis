"""The level of Morrow (`morrow:level`): L_Morrow's land, reservoir, light and scatter, from Tools/build_physis_morrow.py's
height.bin and scatter.json. Everything placed here goes in the outliner folder Morrow (the scenario's is MorrowScene),
so a rebuild replaces only its own actors.

The look (author, 2026-11-19): realistic, cold dawn. The sun 5 degrees up in the east-south-east, under the eastern
ridge, so the valley lies in blue shadow while the western peaks take the first pink light; a pale gold horizon going to
steel blue overhead; mist in the low ground; frost (the materials). When the Lull stops, BP_MorrowDirector raises the
sun (tag MorrowSun) over the ridge. No post-process stylisation.
"""
import json
import math
import struct

import unreal

import physis_morrow_plan as plan
import physis_morrow_tools as T
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
    """Art/Meshes/Morrow/height.bin (float32 metres, index i * ny + j, i along x) with height.json."""

    def __init__(self):
        meta = json.loads((T.ART / 'height.json').read_text())
        self.half_x, self.half_y, self.cell = float(meta['half_x']), float(meta['half_y']), float(meta['cell'])
        self.nx, self.ny = int(meta['nx']), int(meta['ny'])
        self.water = float(meta.get('water', plan.ICE_Z))
        self.h = struct.unpack('<%df' % (self.nx * self.ny), (T.ART / 'height.bin').read_bytes()[:self.nx * self.ny * 4])

    def metres(self, x, y):
        fx, fy = (x + self.half_x) / self.cell, (y + self.half_y) / self.cell
        i, j = max(0, min(int(math.floor(fx)), self.nx - 2)), max(0, min(int(math.floor(fy)), self.ny - 2))
        u, v = min(max(fx - i, 0.0), 1.0), min(max(fy - j, 0.0), 1.0)
        h, n = self.h, self.ny
        return h[i * n + j] * (1 - u) * (1 - v) + h[(i + 1) * n + j] * u * (1 - v) + h[i * n + j + 1] * (1 - u) * v + h[(i + 1) * n + j + 1] * u * v

    def at(self, x, y):
        """Ground height in cm at Unreal (x, y) in cm (over the reservoir: its ice)."""
        z = self.metres(x / CM, y / CM)
        if plan.in_lake(x / CM, y / CM):
            z = max(z, plan.ICE_Z)
        return z * CM


# ---------------------------------------------------------------- the look

SUN_LUX = 5.5                  # the sun's own light before it clears the ridge (the game's exposure convention is 15)
SUN_PITCH, SUN_YAW = -5.0, 290.0   # 5 degrees up, from the east-south-east (the light travels toward yaw 290)
SUN_COLOUR = (1.0, .81, .72)
RISEN_PITCH, RISEN_LUX, RISEN_COLOUR = -26.0, 15.0, (1.0, .9, .78)   # after the Lull (BP_MorrowDirector)
FOG = {'fog_density': .0028, 'fog_height_falloff': .06, 'start_distance': 1200.0, 'fog_max_opacity': .85, 'fog_cutoff_distance': 0.0}
FOG_LOW = {'fog_density': .045, 'fog_height_falloff': .55, 'fog_height_offset': 1600.0}   # the mist lying in the valley's floor
FOG_COLOUR, FOG_BRIGHT = (.50, .60, .82), .45
FOG_SUN, FOG_SUN_BRIGHT = (1.0, .80, .70), .35
POST_CHANGES = {'bloom_intensity': .45, 'auto_exposure_bias': .55, 'vignette_intensity': .3}
RAYLEIGH = (.14, .30, .72)


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
    cn.try_set(sa, 'rayleigh_scattering_scale', .036, failed)
    cn.try_set(sa, 'mie_scattering_scale', .0025, failed)
    cn.try_set(sa, 'mie_anisotropy', .82, failed)
    sun = spawn(unreal.DirectionalLight, 'Sun', (0, 0, 30000), (0, SUN_PITCH, SUN_YAW), tags=('MorrowSun',))
    comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property('intensity', SUN_LUX)
    comp.set_light_color(gt.linear(SUN_COLOUR))
    for key, value in (('atmosphere_sun_light', True), ('light_source_angle', 1.2), ('forward_shading_priority', 1),
                       ('dynamic_shadow_distance_movable_light', 40000.0), ('dynamic_shadow_cascades', 4), ('contact_shadow_length', .03),
                       ('indirect_lighting_intensity', 1.2), ('volumetric_scattering_intensity', .8)):
        cn.try_set(comp, key, value, failed)
    light = spawn(unreal.SkyLight, 'Sky Light', (0, 0, 20000))
    sc = light.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for key, value in (('real_time_capture', True), ('intensity', 1.6), ('lower_hemisphere_is_black', False)):
        cn.try_set(sc, key, value, failed)
    cn.try_set(sc, 'light_color', unreal.Color(r=200, g=224, b=255, a=255), failed)   # the blue hour: the shadowed valley lit by the sky alone
    fog = spawn(unreal.ExponentialHeightFog, 'Haze', (0, 0, 0))
    haze = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    for key, value in FOG.items():
        cn.try_set(haze, key, value, failed)
    cn.try_set(haze, 'fog_inscattering_luminance', gt.linear(tuple(c * FOG_BRIGHT for c in FOG_COLOUR)), failed)
    cn.try_set(haze, 'sky_atmosphere_ambient_contribution_color_scale', gt.linear((0.0, 0.0, 0.0)), failed)
    cn.try_set(haze, 'directional_inscattering_luminance', gt.linear(tuple(c * FOG_SUN_BRIGHT for c in FOG_SUN)), failed)
    cn.try_set(haze, 'directional_inscattering_exponent', 8.0, failed)
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
    volume = spawn(unreal.PostProcessVolume, 'Morrow Look')
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
        raise RuntimeError('stop Play before building Morrow')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None or world.get_path_name().split('.')[0] != LEVEL:
        dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError('unsaved changes in %s: save or discard them before morrow:level' % ', '.join(dirty))
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
    if name.startswith('SM_H'):
        return unreal.load_asset('/Game/Halcyon/Meshes/' + name)
    return unreal.load_asset(T.MESHES + '/' + name)


def terrain():
    missing = []
    for i in range(plan.TILES_X):
        for j in range(plan.TILES_Y):
            name = 'SM_OT_Terrain_%d_%d' % (i, j)
            if gl.mesh_actor('Terrain %d %d' % (i, j), mesh(name), (0, 0, 0), folder=FOLDER + '/Terrain') is None:
                missing.append(name)
    return {'tiles': plan.TILES_X * plan.TILES_Y, 'missing': missing}


def water(g):
    """The reservoir: its ice (walkable; tag MorrowScar, so it goes when the Lull stops) and, under the same sheet, its
    water (tag MorrowBloom, shown then), with swimming in a water PhysicsVolume over the lake from its surface down past
    its bed; and the river's ice in the Gorge (it only shows: the Gorge's floor carries her)."""
    sheet = mesh('SM_OT_Lake')
    if sheet is None:
        return {'missing': ['SM_OT_Lake']}
    ice = gl.mesh_actor('Reservoir Ice', sheet, (0, 0, 0), folder=FOLDER + '/Water', collide=True, shadow=False)
    ice.set_editor_property('tags', ['MorrowScar'])
    lake = gl.mesh_actor('Reservoir', sheet, (0, 0, -6.0), folder=FOLDER + '/Water', collide=False, shadow=False)
    lake.static_mesh_component.set_material(0, unreal.load_asset(T.MATS + '/MI_MW_Lake'))
    lake.set_editor_property('tags', ['MorrowBloom'])
    lake.set_actor_hidden_in_game(True)
    river = mesh('SM_OT_GorgeIce')
    if river is not None:
        gl.mesh_actor('Gorge Ice', river, (0, 0, 0), folder=FOLDER + '/Water', collide=False, shadow=False)
    sub = actors()
    x0, x1, y0, y1 = (plan.CREST_X1 + 2.0) * CM, (plan.HALF_X + 300.0) * CM, -plan.HALF_Y * CM, plan.HALF_Y * CM
    top, bottom = (plan.ICE_Z - .1) * CM, (plan.LAKE_BED - 6.0) * CM
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
RULES = {'SM_GV_Grass': (False, 7000, False), 'SM_GV_Bush': (False, 30000, True), 'SM_GV_Sapling': (False, 30000, True),
         'SM_HN_Lamp': (True, 40000, True), 'SM_GS_Stone': (False, 25000, True)}
RULE_DEFAULT = (True, 0, True)
OVERRIDES = {'SM_GS_Boulder': 'MI_MW_Scan_Boulder', 'SM_GS_Stone': 'MI_MW_Scan_Stone', 'SM_GS_CliffC': 'MI_MW_Scan_CliffC'}


def scatter():
    data = gt.read_json(T.ART / 'scatter.json')
    counts, failed, missing, frosted = {}, [], [], 0
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
        if material is not None:
            for part in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent):
                for slot in range(max(1, part.get_num_materials())):
                    part.set_material(slot, material)
        else:
            frosted += T.regrade(actor)
        counts[name] = len(placed)
    return {'instances': counts, 'total': sum(counts.values()), 'missing': missing, 'frosted_slots': frosted, 'failed': sorted(set(failed))}


def start(g):
    """Where editor play starts (the Pass Chapel), and the level's directors: BP_Awakening marks an open-world level
    for the shared graphs (TestArrival off); BP_MorrowDirector marks Morrow and runs what is its own."""
    x, y = plan.CHAPEL_STILL[0] * CM, plan.CHAPEL_STILL[1] * CM
    sub = actors()
    if not any(isinstance(actor, unreal.PlayerStart) for actor in sub.get_all_level_actors()):
        player = sub.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(x, y, g.at(x, y) + 120), unreal.Rotator(0, 0, 0))
        player.set_actor_label('Physis Arrives')
        player.set_folder_path(FOLDER)
    made = []
    lx, ly = plan.CHAPEL[0] * CM, plan.CHAPEL[1] * CM
    for name, label in (('BP_Awakening', 'Awakening Director'), ('BP_MorrowDirector', 'Morrow Director')):
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
        report = {'removed': open_level((FOLDER + '/Scatter',)), 'scatter': scatter()}
    elif part == 'water':
        report = {'removed': open_level((FOLDER + '/Water',)), 'water': water(Ground())}
    elif part == 'start':
        report = {'removed': open_level((FOLDER + '/Director',)), 'start': start(Ground())}
    else:
        raise ValueError('unknown morrow level part ' + part)
    save_level()
    return report
