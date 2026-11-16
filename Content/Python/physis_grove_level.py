"""L_Grove, the map of level 4 (`outfit_operation grove:level`; Tools/grove/README.md "The level").

Builds, in this order: the terrain's twelve tiles and the mountains behind them, the lake, the headpond, the stream
and the falls with the lake's swimming volume, the sky (a real atmosphere, clouds, the late-afternoon sun, sky light,
height fog with volumetric light), the look (exposure, Lumen; no post-process material), the forest (scatter.json:
generated trees with their own far versions, scanned undergrowth, rocks and deadwood), the cliff faces along the
valley's edge, the Gully, the Rift and the mesa, the three great trees and the Heartwood, and the level's start and
directors. Everything it places goes under the outliner folder 'Grove', which a rebuild clears first (the scenario's
actors too, so grove:scenario runs after it).

    grove:level            the whole build
    grove:level:look       only the sky, light, fog and look again (tuning without replacing the forest)
    grove:level:scatter    only the forest and the cliffs again
    grove:level:rim        only the cover of the rim's slopes again
"""
import json
import math
import struct
import zlib

import unreal

import physis_conclave_tools as cn
import physis_gameplay_tools as game
import physis_grove_plan as plan
import physis_grove_tools as T

CM = T.CM
FOLDER = T.FOLDER
LEVEL = T.LEVEL
library = unreal.EditorAssetLibrary


def actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


# ---------------------------------------------------------------- height grid

class Ground:
    """The terrain height grid from Tools/build_physis_grove.py: Art/Meshes/Grove/height.json (half_x, half_y, cell,
    nx, ny, water, headpond, pool, falls_lip; metres) and height.bin (float32 metres, index i * ny + j, i along x)."""

    def __init__(self):
        meta = json.loads((T.ART / 'height.json').read_text())
        self.half_x, self.half_y, self.cell = float(meta['half_x']), float(meta['half_y']), float(meta['cell'])
        self.nx, self.ny = int(meta['nx']), int(meta['ny'])
        self.water = float(meta.get('water', plan.WATER))
        self.headpond = float(meta.get('headpond', plan.HEADPOND))
        self.pool = float(meta.get('pool', 20.0))
        self.falls_lip = tuple(meta.get('falls_lip', (0, 0, 0)))
        raw = (T.ART / 'height.bin').read_bytes()
        count = self.nx * self.ny
        if len(raw) < count * 4:
            raise ValueError('height.bin holds %d bytes; %d x %d floats need %d' % (len(raw), self.nx, self.ny, count * 4))
        self.h = struct.unpack('<%df' % count, raw[:count * 4])

    def metres(self, x, y):
        """Ground height in metres at plan (x, y) in metres; clamped to the grid's edge outside it."""
        fx = (x + self.half_x) / self.cell
        fy = (y + self.half_y) / self.cell
        i = max(0, min(int(math.floor(fx)), self.nx - 2))
        j = max(0, min(int(math.floor(fy)), self.ny - 2))
        u = min(max(fx - i, 0.0), 1.0)
        v = min(max(fy - j, 0.0), 1.0)
        h, n = self.h, self.ny
        return (h[i * n + j] * (1 - u) * (1 - v) + h[(i + 1) * n + j] * u * (1 - v) + h[i * n + j + 1] * (1 - u) * v +
                h[(i + 1) * n + j + 1] * u * v)

    def at(self, x, y):
        """Ground height in cm at Unreal (x, y) in cm."""
        return self.metres(x / CM, y / CM) * CM

    def ground(self, x, y, lift=0):
        """(x, y, z) in cm: the ground, or the lake's surface over the lake, plus lift (a negative lift may go under
        water)."""
        return (x, y, max(self.at(x, y), self.water * CM if lift >= 0 else -1e9) + lift)

    def spot(self, place, lift=0):
        """A plan point (metres) on the ground, in cm."""
        return self.ground(place[0] * CM, place[1] * CM, lift)


# ---------------------------------------------------------------- the look

# The sun: late afternoon from the south-west, behind her left shoulder as she walks north, so what lies ahead is lit
# and the crowns she looks back at are backlit. 20 lux, not a real sun's 100,000: the game's glows, lamps and effects
# are tuned for the exposure that goes with it (about EV 3 in the open), and the sky, the fog and the clouds take
# their brightness from this light, so the picture is the same as at full strength.
SUN_LUX = 20.0
SUN_PITCH, SUN_YAW = -34.0, 58.0
SUN_COLOUR = (1.0, .95, .86)
SKY_INTENSITY = 1.0
# Haze: thin in the open (the far cliffs soften at a kilometre), with a second low layer of mist over the lake and in
# the Gully. Volumetric out to 120 m, so the sun draws shafts through the canopy.
FOG = {'fog_density': .011, 'fog_height_falloff': .055, 'start_distance': 600.0, 'fog_max_opacity': .92, 'fog_cutoff_distance': 0.0}
FOG_LOW = {'fog_density': .016, 'fog_height_falloff': .9, 'fog_height_offset': -2600.0}
FOG_BASE = 3000.0           # cm: the fog actor stands at the valley floor's height
FOG_COLOUR, FOG_BRIGHT = (.62, .74, .92), .75
FOG_SUN, FOG_SUN_BRIGHT = (1.0, .82, .58), 2.4
VOLUMETRIC = (('enable_volumetric_fog', True), ('volumetric_fog_scattering_distribution', .72), ('volumetric_fog_extinction_scale', 1.3),
              ('volumetric_fog_distance', 12000.0), ('volumetric_fog_static_lighting_scattering_intensity', 1.0))
EXPOSURE = (0.2, 6.5)       # EV100: the floor lets the eye open in the shade of the forest, the ceiling holds the open lake
POST = (('override_auto_exposure_method', True), ('auto_exposure_method', unreal.AutoExposureMethod.AEM_HISTOGRAM),
        ('override_auto_exposure_bias', True), ('auto_exposure_bias', 0.2),
        ('override_auto_exposure_min_brightness', True), ('auto_exposure_min_brightness', EXPOSURE[0]),
        ('override_auto_exposure_max_brightness', True), ('auto_exposure_max_brightness', EXPOSURE[1]),
        ('override_auto_exposure_speed_up', True), ('auto_exposure_speed_up', 2.0),
        ('override_auto_exposure_speed_down', True), ('auto_exposure_speed_down', 1.2),
        ('override_auto_exposure_apply_physical_camera_exposure', True), ('auto_exposure_apply_physical_camera_exposure', False),
        ('override_bloom_intensity', True), ('bloom_intensity', .5),
        ('override_ambient_occlusion_intensity', True), ('ambient_occlusion_intensity', .6),
        ('override_ambient_occlusion_radius', True), ('ambient_occlusion_radius', 120.0),
        ('override_reflection_method', True), ('reflection_method', unreal.ReflectionMethod.LUMEN),
        ('override_dynamic_global_illumination_method', True),
        ('dynamic_global_illumination_method', unreal.DynamicGlobalIlluminationMethod.LUMEN),
        ('override_lumen_scene_lighting_quality', True), ('lumen_scene_lighting_quality', 2.0),
        ('override_lumen_scene_detail', True), ('lumen_scene_detail', 2.0),
        ('override_lumen_scene_view_distance', True), ('lumen_scene_view_distance', 150000.0),
        ('override_lumen_final_gather_quality', True), ('lumen_final_gather_quality', 2.0),
        ('override_lumen_max_trace_distance', True), ('lumen_max_trace_distance', 150000.0),
        ('override_lumen_reflection_quality', True), ('lumen_reflection_quality', 2.0),
        ('override_lumen_ray_lighting_mode', True), ('lumen_ray_lighting_mode', unreal.LumenRayLightingModeOverride.HIT_LIGHTING_FOR_REFLECTIONS),
        ('override_lumen_front_layer_translucency_reflections', True), ('lumen_front_layer_translucency_reflections', True),
        ('override_lumen_skylight_leaking', True), ('lumen_skylight_leaking', .06),
        ('override_local_exposure_shadow_contrast_scale', True), ('local_exposure_shadow_contrast_scale', .72),
        ('override_local_exposure_highlight_contrast_scale', True), ('local_exposure_highlight_contrast_scale', .85),
        ('override_local_exposure_detail_strength', True), ('local_exposure_detail_strength', 1.1),
        ('override_vignette_intensity', True), ('vignette_intensity', .25))


def spawn(cls, label, place=(0, 0, 0), rot=(0, 0, 0), folder=FOLDER + '/Light', tags=()):
    actor = actors().spawn_actor_from_class(cls, unreal.Vector(*place), unreal.Rotator(*rot))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    if tags:
        actor.set_editor_property('tags', list(tags))
    return actor


def sky():
    """The atmosphere, the sun, the sky light that captures them every frame, and a deck of fair-weather cloud."""
    failed = []
    spawn(unreal.SkyAtmosphere, 'Atmosphere')
    sun = spawn(unreal.DirectionalLight, 'Sun', (0, 0, 30000), (0, SUN_PITCH, SUN_YAW), tags=('GroveSun',))
    comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property('intensity', SUN_LUX)
    comp.set_light_color(T.linear(SUN_COLOUR))
    for key, value in (('atmosphere_sun_light', True), ('light_source_angle', .8), ('forward_shading_priority', 1),
                       ('dynamic_shadow_distance_movable_light', 30000.0), ('dynamic_shadow_cascades', 4),
                       ('contact_shadow_length', .03), ('contact_shadow_non_casting_intensity', .5), ('indirect_lighting_intensity', 1.2),
                       ('volumetric_scattering_intensity', 1.6), ('cast_cloud_shadows', True), ('cloud_shadow_strength', .55),
                       ('cloud_scattered_luminance_scale', T.linear((1.0, 1.0, 1.0)))):
        cn.try_set(comp, key, value, failed)
    light = spawn(unreal.SkyLight, 'Sky Light', (0, 0, 20000))
    sc = light.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for key, value in (('real_time_capture', True), ('intensity', SKY_INTENSITY), ('lower_hemisphere_is_black', False),
                       ('volumetric_scattering_intensity', 1.0)):
        cn.try_set(sc, key, value, failed)
    try:
        cloud = spawn(unreal.VolumetricCloud, 'Clouds')
        cc = cloud.get_component_by_class(unreal.VolumetricCloudComponent)
        for key, value in (('layer_bottom_altitude', 4.5), ('layer_height', 4.0), ('view_sample_count_scale', .8),
                           ('shadow_view_sample_count_scale', .7)):
            cn.try_set(cc, key, value, failed)
    except Exception as error:
        failed.append('clouds: %s' % error)
    return {'sun_lux': SUN_LUX, 'sun': [SUN_PITCH, SUN_YAW], 'failed': failed}


def fog():
    failed = []
    actor = spawn(unreal.ExponentialHeightFog, 'Haze', (0, 0, FOG_BASE))
    haze = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
    for key, value in FOG.items():
        cn.try_set(haze, key, value, failed)
    cn.try_set(haze, 'fog_inscattering_luminance', T.linear(tuple(c * FOG_BRIGHT for c in FOG_COLOUR)), failed)
    cn.try_set(haze, 'sky_atmosphere_ambient_contribution_color_scale', T.linear((0.0, 0.0, 0.0)), failed)
    cn.try_set(haze, 'directional_inscattering_luminance', T.linear(tuple(c * FOG_SUN_BRIGHT for c in FOG_SUN)), failed)
    cn.try_set(haze, 'directional_inscattering_exponent', 9.0, failed)
    cn.try_set(haze, 'directional_inscattering_start_distance', 3000.0, failed)
    for key, value in VOLUMETRIC:
        cn.try_set(haze, key, value, failed)
    cn.try_set(haze, 'volumetric_fog_albedo', unreal.Color(235, 240, 250, 255), failed)
    try:
        layer = unreal.ExponentialHeightFogData()
        for key, value in FOG_LOW.items():
            layer.set_editor_property(key, value)
        haze.set_editor_property('second_fog_data', layer)
    except Exception as error:
        failed.append('second_fog_data: %s' % error)
    return {'failed': failed}


def post():
    volume = spawn(unreal.PostProcessVolume, 'Grove Look')
    volume.set_editor_property('unbound', True)
    settings = volume.settings
    failed = []
    for key, value in POST:
        try:
            settings.set_editor_property(key, value)
        except Exception as error:
            failed.append('%s: %s' % (key, error))
    blendables = unreal.WeightedBlendables()   # no post-process material: the author's rule for Earth
    blendables.set_editor_property('array', [])
    settings.set_editor_property('weighted_blendables', blendables)
    volume.set_editor_property('settings', settings)
    return {'failed': failed}


def look():
    return {'sky': sky(), 'fog': fog(), 'post': post()}


# ---------------------------------------------------------------- level file

def open_level(prefixes=(FOLDER,)):
    """Opens L_Grove (made if missing) and removes what an earlier build placed in the given outliner folders.
    Refuses while Play runs or another map has unsaved changes (switching maps would stop on a dialog)."""
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    playing = getattr(les, 'is_in_play_in_editor', None)
    if playing and playing():
        raise RuntimeError('stop Play before building the Grove')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None or world.get_path_name().split('.')[0] != LEVEL:
        listing = getattr(unreal.EditorLoadingAndSavingUtils, 'get_dirty_map_packages', None)
        dirty = [p.get_name() for p in listing()] if listing else []
        if dirty:
            raise RuntimeError('unsaved changes in %s: save or discard them before grove:level' % ', '.join(dirty))
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
    if path == LEVEL:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    elif path.startswith('/Temp/'):
        unreal.EditorLoadingAndSavingUtils.save_map(world, LEVEL)
    else:
        raise RuntimeError('%s is open, not %s: nothing saved' % (path, LEVEL))


def mesh_actor(label, asset, place, rot=(0, 0, 0), scale=1.0, folder=FOLDER, collide=True, shadow=True, tags=()):
    """A StaticMeshActor of a loaded mesh (None when the mesh was never imported)."""
    if asset is None:
        return None
    actor = actors().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place), unreal.Rotator(*rot))
    actor.set_actor_label(label)
    part = actor.static_mesh_component
    part.set_static_mesh(asset)
    part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
    part.set_editor_property('cast_shadow', shadow)
    part.set_default_custom_primitive_data_float(cn.SEED_DATA, cn.seed_of(label))
    size = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    actor.set_actor_scale3d(unreal.Vector(*size))
    actor.set_folder_path(folder)
    if tags:
        actor.set_editor_property('tags', list(tags))
    return actor


def generated(name):
    return unreal.load_asset(T.MESHES + '/' + name)


def scanned(name):
    return unreal.load_asset(T.SCANS + '/' + name)


def any_mesh(name):
    return scanned(name) if name.startswith('SM_GS_') else generated(name)


# ---------------------------------------------------------------- land and water

def terrain(g):
    missing, shifted = [], []
    size_x, size_y = 2 * g.half_x / plan.TILES_X, 2 * g.half_y / plan.TILES_Y
    for i in range(plan.TILES_X):
        for j in range(plan.TILES_Y):
            name = 'SM_GT_Terrain_%d_%d' % (i, j)
            asset = generated(name)
            if mesh_actor('Terrain %d %d' % (i, j), asset, (0, 0, 0), folder=FOLDER + '/Terrain') is None:
                missing.append(name)
                continue
            box = asset.get_bounding_box()
            want = ((-g.half_x + (i + .5) * size_x) * CM, (-g.half_y + (j + .5) * size_y) * CM)
            got = ((box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2)
            if abs(got[0] - want[0]) > size_x * CM / 4 or abs(got[1] - want[1]) > size_y * CM / 4:
                shifted.append(name)
    if mesh_actor('Mountains', generated('SM_GT_Backdrop'), (0, 0, 0), folder=FOLDER + '/Terrain', collide=False, shadow=False) is None:
        missing.append('SM_GT_Backdrop')
    return {'tiles': plan.TILES_X * plan.TILES_Y, 'missing': missing, 'not_at_their_cell': shifted}


def water(g):
    """The water's sheets, and swimming under the lake only: a water PhysicsVolume over the lake sheet's footprint
    from the waterline down past the deepest bed (ground above the waterline is outside it, so shores stay dry). The
    headpond, the stream and the pool are shallow and waded."""
    placed, missing = [], []
    for name in ('SM_GT_Lake', 'SM_GT_Headpond', 'SM_GT_River', 'SM_GT_Falls'):
        if mesh_actor(name[6:], generated(name), (0, 0, 0), folder=FOLDER + '/Water', collide=False, shadow=False) is None:
            missing.append(name)
        else:
            placed.append(name)
    lake = generated('SM_GT_Lake')
    if lake is None:
        return {'placed': placed, 'missing': missing, 'volume_cm': None}
    box = lake.get_bounding_box()
    x0, x1, y0, y1 = box.min.x, box.max.x, box.min.y, box.max.y
    top = g.water * CM
    bed = min(g.at(x, y) for x in cn.frange(x0, x1, 400.0) for y in cn.frange(y0, y1, 400.0))
    bottom = min(bed, top - 200.0) - 300.0
    sub = actors()
    volume = sub.spawn_actor_from_class(unreal.PhysicsVolume, unreal.Vector((x0 + x1) / 2, (y0 + y1) / 2, (top + bottom) / 2))
    volume.set_actor_label('Water Volume')
    volume.set_folder_path(FOLDER + '/Water')
    volume.set_actor_scale3d(unreal.Vector((x1 - x0) / 200.0, (y1 - y0) / 200.0, (top - bottom) / 200.0))  # the brush is 200 cm
    volume.set_editor_property('water_volume', True)
    volume.set_editor_property('fluid_friction', .35)
    volume.set_editor_property('terminal_velocity', 600.0)
    director = sub.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/BP_SwimDirector').generated_class(), unreal.Vector(0, 0, 0))
    director.set_actor_label('Swim Director')
    director.set_folder_path(FOLDER + '/Water')
    return {'placed': placed, 'missing': missing, 'volume_cm': [x0, x1, y0, y1, bottom, top]}


# ---------------------------------------------------------------- the forest

def chance(label):
    """A fixed number in [0, 1) for a label, so a rebuild keeps every plant where and what it was."""
    return zlib.crc32(label.encode('utf-8')) / 4294967296.0


# A scatter class (a row list of scatter.json) and the meshes it becomes: (mesh, share, scale, sink as a fraction of
# the mesh's height, extra yaw). Scanned undergrowth, rocks and deadwood stand in for the classes the generators
# only sketched; a mesh that was never imported gives its share to the others.
CLASSES = {
    'SM_GV_Fern': (('SM_GS_FernB', .2, 1.5, 0, 0), ('SM_GS_FernC', .2, 1.5, 0, 0), ('SM_GS_FernA', .1, 1.7, 0, 0), ('SM_GS_FernD', .1, 1.7, 0, 0),
                   ('SM_GS_NettleA', .05, 1.0, 0, 0), ('SM_GS_NettleB', .05, 1.0, 0, 0), ('SM_GS_NettleC', .04, 1.1, 0, 0),
                   ('SM_GS_HerbA', .04, 2.0, 0, 0), ('SM_GS_HerbB', .04, 2.0, 0, 0), ('SM_GS_HerbC', .03, 2.0, 0, 0),
                   ('SM_GS_WeedA', .03, 1.4, 0, 0), ('SM_GS_WeedB', .03, 1.4, 0, 0), ('SM_GS_PeriwinkleA', .03, 1.6, 0, 0),
                   ('SM_GS_PeriwinkleB', .03, 1.6, 0, 0), ('SM_GS_SorrelC', .03, 1.6, 0, 0)),
    'SM_GV_Bush': (('SM_GV_Bush', .5, 1.0, 0, 0), ('SM_GS_ShrubA', .14, 1.0, 0, 0), ('SM_GS_ShrubB', .12, 1.0, 0, 0),
                   ('SM_GS_ShrubC', .12, 1.0, 0, 0), ('SM_GS_ShrubD', .12, 1.0, 0, 0)),
    'SM_GV_Rock0': (('SM_GS_MossRockA', .16, 1.0, .2, 0), ('SM_GS_MossRockB', .16, 1.0, .2, 0), ('SM_GS_MossRockD', .16, 1.0, .2, 0),
                    ('SM_GS_MossRockE', .14, 1.0, .2, 0), ('SM_GS_MossRockF', .14, 1.0, .2, 0), ('SM_GS_Boulder', .14, 1.5, .18, 0),
                    ('SM_GS_MossRockC', .1, 1.1, .2, 0)),
    'SM_GV_Rock1': (('SM_GS_MossRockG', .14, 1.3, .15, 0), ('SM_GS_MossRockJ', .14, 1.3, .15, 0), ('SM_GS_MossRockK', .14, 1.3, .15, 0),
                    ('SM_GS_MossRockM', .14, 1.3, .15, 0), ('SM_GS_MossRockL', .12, 1.3, .15, 0), ('SM_GS_MossRockH', .1, 1.5, .15, 0),
                    ('SM_GS_MossRockI', .1, 1.5, .15, 0), ('SM_GS_Stone', .12, 1.4, .2, 0)),
    'SM_GV_Log': (('SM_GS_LogB', .3, 1.3, .1, 90), ('SM_GS_LogA', .22, 1.6, .12, 90), ('SM_GS_StumpA', .14, 1.0, .04, 0),
                  ('SM_GS_StumpB', .14, 1.0, .04, 0), ('SM_GS_RootsA', .1, 1.0, .08, 0), ('SM_GS_BranchA', .05, 1.2, 0, 0),
                  ('SM_GS_BranchB', .05, 1.2, 0, 0)),
    'SM_GV_Flowers': (('SM_GV_Flowers', .5, 1.0, 0, 0), ('SM_GS_DandelionA', .1, 1.3, 0, 0), ('SM_GS_DandelionB', .08, 1.3, 0, 0),
                      ('SM_GS_DandelionC', .08, 1.3, 0, 0), ('SM_GS_SorrelA', .08, 1.5, 0, 0), ('SM_GS_SorrelB', .08, 1.5, 0, 0),
                      ('SM_GS_SorrelD', .08, 1.5, 0, 0)),
}
# Generated classes: (collide, cull distance in cm (0 never), casts a shadow).
RULES = {'SM_GV_Grass': (False, 6500, False), 'SM_GV_Flowers': (False, 6500, False), 'SM_GV_Reeds': (False, 12000, False),
         'SM_GV_Lily': (False, 12000, False), 'SM_GV_Mushrooms': (False, 4500, False), 'SM_GV_Bush': (False, 16000, True),
         'SM_GV_Sapling': (False, 22000, True), 'SM_GV_Thorn': (True, 0, True), 'SM_GV_Snag': (True, 0, True),
         'SM_GV_Oak': (True, 0, True), 'SM_GV_Beech': (True, 0, True), 'SM_GV_Pine': (True, 0, True), 'SM_GV_Birch': (True, 0, True)}
RULE_DEFAULT = (True, 40000, True)
# Out of the ray-tracing scene: Lumen's traces treat every card as opaque, so a meadow's grass roofs its own ground.
RT_SKIP_USES = ('cover', 'debris')
RT_SKIP = ('SM_GV_Grass', 'SM_GV_Flowers', 'SM_GV_Mushrooms', 'SM_GV_Lily')
BLOOM_TAG, BLIGHT_TAG = 'GroveBloom', 'GroveBlight'   # shown, and hidden, once the grove is healed (BP_GroveDirector)
BLIGHT_CLASSES = ('SM_GV_Thorn',)


def scan_facts():
    return T.read_json(T.SCAN_ART / 'scans.json').get('meshes', {})


def rule_for(mesh, facts):
    if mesh in facts:
        row = facts[mesh]
        return (row['collide'] != 'none', int(row['cull'] * CM), bool(row['shadow']))
    return RULES.get(mesh, RULE_DEFAULT)


def instanced(label, asset, rows, collide, cull, shadow, folder, failed, rt=True, tags=(), hidden=False):
    """One actor holding every instance of one mesh in a native hierarchical instanced component (saved with the
    level, never reset by a construction script)."""
    actor = actors().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = subobjects.k2_gather_subobject_data_for_instance(actor)[0]
    handle, _ = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.HierarchicalInstancedStaticMeshComponent,
                                                                          blueprint_context=None))
    part = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
    part.set_static_mesh(asset)
    part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
    part.set_editor_property('cast_shadow', shadow)
    part.set_editor_property('instance_end_cull_distance', int(cull))
    part.set_editor_property('instance_start_cull_distance', int(cull * .8))
    if shadow:
        cn.try_set(part, 'shadow_cache_invalidation_behavior', unreal.ShadowCacheInvalidationBehavior.RIGID, failed)
    cn.try_set(part, 'world_position_offset_disable_distance', 7000, failed)
    if not rt:
        cn.rt_skip(part, failed)
    transforms = [unreal.Transform(unreal.Vector(x, y, z), unreal.Rotator(roll, pitch, yaw), unreal.Vector(sx, sy, sz))
                  for x, y, z, pitch, yaw, roll, sx, sy, sz in rows]
    part.add_instances(transforms, False, True)
    if tags:
        actor.set_editor_property('tags', list(tags))
    if hidden:
        actor.set_actor_hidden_in_game(True)
    return actor


def split(name, rows, facts, missing):
    """A class's rows shared out among its meshes: {mesh: [(x, y, z, pitch, yaw, roll, sx, sy, sz), ...]}."""
    variants = [v for v in CLASSES.get(name, ((name, 1.0, 1.0, 0, 0),)) if any_mesh(v[0]) is not None]
    for v in CLASSES.get(name, ((name, 1.0, 1.0, 0, 0),)):
        if any_mesh(v[0]) is None:
            missing.add(v[0])
    if not variants:
        return {}
    total = sum(v[1] for v in variants)
    out = {}
    for index, row in enumerate(rows):
        x, y, z, pitch, yaw, roll, s = row[:7]
        pick, acc = chance('%s:%d' % (name, index)) * total, 0.0
        chosen = variants[-1]
        for v in variants:
            acc += v[1]
            if pick < acc:
                chosen = v
                break
        mesh, _, scale, sink, turn = chosen
        s *= scale
        height = facts[mesh]['size'][2] * CM if mesh in facts else 0.0
        out.setdefault(mesh, []).append((x, y, z - sink * height * s, pitch, yaw + turn, roll, s, s, s))
    return out


def scatter():
    """scatter.json: every vegetation class as instanced actors, one per mesh."""
    data = T.read_json(T.ART / 'scatter.json')
    facts = scan_facts()
    counts, failed, missing = {}, [], set()
    for name, rows in sorted(data.items()):
        if not rows or name.startswith('Cliff:'):
            continue
        bloom = name.startswith('Bloom:')
        base = name.split(':', 1)[1] if bloom else name
        for mesh, placed in sorted(split(base, rows, facts, missing).items()):
            collide, cull, shadow = rule_for(mesh, facts)
            uses = facts.get(mesh, {}).get('use')
            rt = not (mesh.startswith(RT_SKIP) or uses in RT_SKIP_USES)
            tags = (BLOOM_TAG,) if bloom else (BLIGHT_TAG,) if base in BLIGHT_CLASSES else ()
            label = '%s %s' % ('Bloom' if bloom else 'Scatter', mesh[6:])
            instanced(label, any_mesh(mesh), placed, collide and not bloom, cull, shadow and not bloom,
                      FOLDER + ('/Bloom' if bloom else '/Scatter'), failed, rt, tags, hidden=bloom)
            counts[label] = len(placed)
    return {'instances': counts, 'total': sum(counts.values()), 'missing': sorted(missing), 'failed': sorted(set(failed))}


# Cliff pieces: scanned rock faces, open at the back, whose face looks +x. A wall gets a tall face piece every row,
# pushed back so its open back is inside the hill, squeezed in depth, and here and there a sloping outcrop at its foot.
# (mesh, its height m, its depth m)
FACES = (('SM_GS_CliffC', 10.52, 5.25),)
OUTCROPS = (('SM_GS_CliffA', 3.57, 3.83), ('SM_GS_CliffB', 2.48, 2.13))
CLIFF_DEPTH = .55        # of the piece's own depth
OUTCROP_SHARE = {'rim': .55, 'gully': .3, 'rift': .35, 'mesa': .5}


def cliffs():
    data = T.read_json(T.ART / 'scatter.json')
    rows_by_mesh, failed, missing = {}, [], []
    for name, rows in sorted(data.items()):
        if not name.startswith('Cliff:'):
            continue
        where = name.split(':', 1)[1]
        for index, row in enumerate(rows):
            x, y, z, _, yaw, _, wall = row[:7]
            wall_cm = wall * CM
            a = math.radians(yaw)
            nx, ny = math.cos(a), math.sin(a)
            label = '%s:%d' % (name, index)
            mesh, height, depth = FACES[int(chance(label + 'f') * len(FACES)) % len(FACES)]
            s = wall / height * (1.08 + .3 * chance(label + 's'))
            back = depth * s * CLIFF_DEPTH * .42 * CM
            turn = (chance(label + 'y') - .5) * 22.0
            rows_by_mesh.setdefault(mesh, []).append((x - nx * back, y - ny * back, z - .1 * wall_cm, 0.0, yaw + turn, 0.0,
                                                      s * CLIFF_DEPTH, s * (1.0 if chance(label + 'm') < .5 else -1.0), s))
            if chance(label + 'o') < OUTCROP_SHARE.get(where, .3):
                mesh, height, depth = OUTCROPS[int(chance(label + 'k') * len(OUTCROPS)) % len(OUTCROPS)]
                so = wall / height * (.3 + .25 * chance(label + 't'))
                out = depth * so * .25 * CM
                side = (chance(label + 'd') - .5) * 2.0 * 400.0
                rows_by_mesh.setdefault(mesh, []).append((x + nx * out - ny * side, y + ny * out + nx * side, z - .12 * height * so * CM, 0.0,
                                                          yaw + (chance(label + 'q') - .5) * 50.0, 0.0, so, so, so))
    counts = {}
    for mesh, rows in sorted(rows_by_mesh.items()):
        asset = scanned(mesh)
        if asset is None:
            missing.append(mesh)
            continue
        instanced('Cliff ' + mesh[6:], asset, rows, True, 0, True, FOLDER + '/Cliffs', failed)
        counts[mesh] = len(rows)
    return {'pieces': counts, 'missing': missing, 'failed': sorted(set(failed))}


# ---------------------------------------------------------------- the rim's slopes
# The valley's rim climbs 240 m in bare terrain. This covers it: rock faces laid back on the slope, moss boulders
# bedded into it, firs and birches where a tree can stand, shrubs between. Only beyond the walkable oval (RIM_KEEP of
# plan.RIM), so nothing here changes where she can go. Every choice is a fixed function of the spot, so a rebuild
# puts each piece back where it was.
RIM_KEEP = .97            # of plan.RIM: nearer the valley than this, nothing is placed
RIM_STEP = 10.0           # m between candidate spots
RIM_FLAT, RIM_TREE, RIM_STEEP = 24.0, 46.0, 58.0   # degrees: below FLAT it is left alone, trees up to TREE, over STEEP rock only
RIM_GRASS_STEP, RIM_GRASS_MAX, RIM_GRASS_CULL = 4.0, 76.0, 32000    # m between tufts, the steepest ground that holds one (degrees), cm
RIM_HERBS = ('SM_GS_FernA', 'SM_GS_FernB', 'SM_GS_FernC', 'SM_GS_FernD', 'SM_GS_NettleA', 'SM_GS_WeedA', 'SM_GS_HerbA')
RIM_ROCKS = ('SM_GS_MossRockA', 'SM_GS_MossRockB', 'SM_GS_MossRockC', 'SM_GS_MossRockD', 'SM_GS_MossRockE', 'SM_GS_MossRockF',
             'SM_GS_MossRockK', 'SM_GS_Boulder')
RIM_SHRUBS = ('SM_GS_ShrubA', 'SM_GS_ShrubB', 'SM_GS_ShrubC', 'SM_GS_ShrubD', 'SM_GV_Bush')
RIM_FACES = (('SM_GS_CliffC', 10.52, 5.25, (1.0, 2.3)), ('SM_GS_CliffA', 3.57, 3.83, (2.2, 4.6)), ('SM_GS_CliffB', 2.48, 2.13, (2.6, 5.2)))


def patches(x, y, size, salt):
    """Smooth noise in 0..1 with features about `size` m across: a fixed function of the place."""
    fx, fy = x / size, y / size
    i, j = math.floor(fx), math.floor(fy)
    u, v = fx - i, fy - j
    u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
    c = [chance('%s:%d:%d' % (salt, i + a, j + b)) for a in (0, 1) for b in (0, 1)]
    return (c[0] * (1 - v) + c[1] * v) * (1 - u) + (c[2] * (1 - v) + c[3] * v) * u


def rim_cover(g):
    facts = scan_facts()
    rows, failed, missing = {}, [], set()

    def put(mesh, row):
        if any_mesh(mesh) is None:
            missing.add(mesh)
        else:
            rows.setdefault(mesh, []).append(row)

    nx, ny = int(2 * g.half_x / RIM_STEP), int(2 * g.half_y / RIM_STEP)
    for i in range(nx):
        for j in range(ny):
            label = 'rim:%d:%d' % (i, j)
            x = -g.half_x + (i + chance(label + 'x')) * RIM_STEP
            y = -g.half_y + (j + chance(label + 'y')) * RIM_STEP
            if math.hypot(x / plan.RIM[0], y / plan.RIM[1]) < RIM_KEEP or abs(x) > g.half_x - 4 or abs(y) > g.half_y - 4:
                continue
            gx = (g.metres(x + 3, y) - g.metres(x - 3, y)) / 6.0
            gy = (g.metres(x, y + 3) - g.metres(x, y - 3)) / 6.0
            steep = math.degrees(math.atan(math.hypot(gx, gy)))
            if steep < RIM_FLAT:
                continue
            z = g.metres(x, y)
            down = math.degrees(math.atan2(-gy, -gx))               # the way the slope faces
            pick = chance(label + 'k')
            # Crags come in bands and clusters with scrubby slope between them, not evenly: an even spread read as scales.
            crag = min(1.0, max(0.0, (patches(x, y, 70.0, 'crag') * .65 + patches(x, y, 23.0, 'crag2') * .35 - .3) / .4))
            rock_share = (.22 if steep < RIM_TREE else .5 if steep < RIM_STEEP else .78) * (.12 + .95 * crag)
            if pick < rock_share:                                    # a rock face, laid back on the slope
                mesh, height, depth, (lo, hi) = RIM_FACES[int(chance(label + 'f') * 2.2) % len(RIM_FACES)]
                sc = (lo + (hi - lo) * chance(label + 's') ** 1.6) * (.75 + .6 * crag)
                back = math.radians(down)
                bury = depth * sc * CLIFF_DEPTH * .25
                lean = (90.0 - steep) * .75
                put(mesh, ((x - math.cos(back) * bury) * CM, (y - math.sin(back) * bury) * CM, (z - .1 * height * sc) * CM, -lean,
                           down + (chance(label + 'y2') - .5) * 70.0, (chance(label + 'r') - .5) * 36.0,
                           sc * CLIFF_DEPTH * 1.3, sc * (.8 + .5 * chance(label + 'm')), sc))   # never mirrored: a mirrored instance drew black here
            elif pick < rock_share + .2:                             # a moss boulder bedded in
                mesh = RIM_ROCKS[int(chance(label + 'f') * len(RIM_ROCKS)) % len(RIM_ROCKS)]
                sc = 1.8 + 3.6 * chance(label + 's') ** 1.5
                tall = facts.get(mesh, {}).get('size', (0, 0, 1.2))[2]
                put(mesh, (x * CM, y * CM, (z - .3 * tall * sc) * CM, (chance(label + 'p') - .5) * 30.0, chance(label + 'y2') * 360.0,
                           (chance(label + 'r') - .5) * 30.0, sc, sc, sc))
            elif steep < RIM_TREE and pick < rock_share + .62:       # a tree: firs mostly, a birch here and there
                roll = chance(label + 'f')
                mesh = 'SM_GV_Pine' if roll < .72 else 'SM_GV_Birch' if roll < .88 else 'SM_GV_Sapling'
                sc = .55 + .6 * chance(label + 's')
                put(mesh, (x * CM, y * CM, (z - .5) * CM, 0.0, chance(label + 'y2') * 360.0, 0.0, sc, sc, sc))
            elif steep < RIM_STEEP + 8.0:                            # shrubs hold what is left
                mesh = RIM_SHRUBS[int(chance(label + 'f') * len(RIM_SHRUBS)) % len(RIM_SHRUBS)]
                sc = 1.2 + 1.3 * chance(label + 's')
                put(mesh, (x * CM, y * CM, (z - .15) * CM, 0.0, chance(label + 'y2') * 360.0, 0.0, sc, sc, sc))
    # Grass on what the crags leave: big tufts lying on the slope (each turned to the ground's own tilt), thick on the
    # gentler ground and thinning out as it steepens, none on the crags themselves.
    grass, herbs = [], {}
    if any_mesh('SM_GV_Grass') is None:
        missing.add('SM_GV_Grass')
    else:
        step = RIM_GRASS_STEP
        for i in range(int(2 * g.half_x / step)):
            for j in range(int(2 * g.half_y / step)):
                label = 'rimgrass:%d:%d' % (i, j)
                x = -g.half_x + (i + 2.4 * chance(label + 'x') - .7) * step      # thrown wider than its cell: no rows
                y = -g.half_y + (j + 2.4 * chance(label + 'y') - .7) * step
                if math.hypot(x / plan.RIM[0], y / plan.RIM[1]) < RIM_KEEP or abs(x) > g.half_x - 4 or abs(y) > g.half_y - 4:
                    continue
                gx = (g.metres(x + 2, y) - g.metres(x - 2, y)) / 4.0
                gy = (g.metres(x, y + 2) - g.metres(x, y - 2)) / 4.0
                steep = math.degrees(math.atan(math.hypot(gx, gy)))
                if steep > RIM_GRASS_MAX:
                    continue
                crag = min(1.0, max(0.0, (patches(x, y, 70.0, 'crag') * .65 + patches(x, y, 23.0, 'crag2') * .35 - .3) / .4))
                keep = (1.0 - .8 * crag) * (1.0 - .55 * max(0.0, steep - 30.0) / (RIM_GRASS_MAX - 30.0)) * (.45 + .8 * patches(x, y, 31.0, 'sward'))
                if chance(label + 'k') > keep:
                    continue
                a = chance(label + 'a') * 2 * math.pi
                rot = unreal.MathLibrary.make_rot_from_zx(unreal.Vector(-gx, -gy, 1.0), unreal.Vector(math.cos(a), math.sin(a), 0.0))
                kind = chance(label + 'm')
                if kind < .5:
                    sc = 2.2 + 2.0 * chance(label + 's')
                    grass.append((x * CM, y * CM, (g.metres(x, y) - .12) * CM, rot.pitch, rot.yaw, rot.roll, sc, sc, sc * (.8 + .5 * chance(label + 'h'))))
                else:                                               # ferns and herbs: dark clumps among the tufts
                    mesh = RIM_HERBS[int((kind - .5) * 2 * len(RIM_HERBS)) % len(RIM_HERBS)]
                    sc = 2.4 + 2.4 * chance(label + 's')
                    herbs.setdefault(mesh, []).append((x * CM, y * CM, (g.metres(x, y) - .08) * CM, rot.pitch, rot.yaw, rot.roll, sc, sc, sc))
    counts = {}
    if grass:
        actor = instanced('Rim Grass', any_mesh('SM_GV_Grass'), grass, False, RIM_GRASS_CULL, False, FOLDER + '/Rim', failed, rt=False)
        look = T.rim_grass_material()
        for part in actor.get_components_by_class(unreal.HierarchicalInstancedStaticMeshComponent):
            part.set_material(0, look)
        counts['SM_GV_Grass'] = len(grass)
    for mesh, placed in sorted(herbs.items()):
        if any_mesh(mesh) is None:
            missing.add(mesh)
            continue
        instanced('Rim ' + mesh[6:], any_mesh(mesh), placed, False, RIM_GRASS_CULL, False, FOLDER + '/Rim', failed, rt=False)
        counts[mesh] = len(placed)
    for mesh, placed in sorted(rows.items()):
        woody = mesh.startswith(('SM_GV_Pine', 'SM_GV_Birch', 'SM_GV_Sapling'))
        plant = woody or mesh.startswith(('SM_GS_Shrub', 'SM_GV_Bush'))
        # No collision: none of it can be reached. Rock and trees are seen from across the valley, so never culled.
        # Out of the ray-traced scene: the lake's reflection drew every rim rock as a black blot.
        # The terrain casts no shadow past the sun's shadow distance, so the lake lies sunlit under the south-west rim; a
        # rock up there would still throw its own shadow down onto the water, a blot with no hill behind it. The rim's
        # sunward half (whose inner slopes face away from the sun anyway) casts none.
        sx, sy = math.cos(math.radians(SUN_YAW)), math.sin(math.radians(SUN_YAW))
        lit = [r for r in placed if r[0] * sx + r[1] * sy >= 0]
        shade = [r for r in placed if r[0] * sx + r[1] * sy < 0]
        for label, group, shadow in (('Rim ', lit, True), ('Rim sunward ', shade, False)):
            if group:
                instanced(label + mesh[6:], any_mesh(mesh), group, False, 60000 if plant and not woody else 0, shadow, FOLDER + '/Rim', failed,
                          rt=False)
        counts[mesh] = len(placed)
    return {'pieces': counts, 'total': sum(counts.values()), 'missing': sorted(missing), 'failed': sorted(set(failed))}


def great_trees(g):
    """The three great trees and the Heartwood: single actors, landmarks seen from the whole valley."""
    placed, missing = [], []
    giant = generated('SM_GV_GiantTree')
    for index, (x, y, _) in enumerate(plan.GIANTS):
        if mesh_actor('Great Tree %d' % (index + 1), giant, g.spot((x, y), -40), (0, 0, 47.0 + 113.0 * index), folder=FOLDER + '/Trees') is None:
            missing.append('SM_GV_GiantTree')
            break
        placed.append('Great Tree %d' % (index + 1))
    heart = generated('SM_GV_Heartwood')
    if mesh_actor('Heartwood', heart, g.spot(plan.HEARTWOOD, -60), (0, 0, 0), folder=FOLDER + '/Trees') is None:
        missing.append('SM_GV_Heartwood')
    else:
        placed.append('Heartwood')
    return {'placed': placed, 'missing': missing}


# ---------------------------------------------------------------- start and directors

def start(g):
    """Where editor play starts (the Hollow), and the level's directors: BP_Awakening marks an open-world level for
    the shared graphs (TestArrival off, or editor play would run the Center's awakening); BP_GroveDirector marks the
    Grove and drives its look."""
    place = g.spot(plan.HOLLOW_STILL, 120)
    sub = actors()
    player = sub.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(*place), unreal.Rotator(0, 0, 20))
    player.set_actor_label('Physis Arrives')
    player.set_folder_path(FOLDER)
    made = []
    for name, label in (('BP_Awakening', 'Awakening Director'), ('BP_GroveDirector', 'Grove Director')):
        actor = sub.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/' + name).generated_class(), unreal.Vector(*g.spot(plan.HOLLOW)))
        actor.set_actor_label(label)
        actor.set_folder_path(FOLDER + '/Director')
        if name == 'BP_Awakening':
            actor.set_editor_property('TestArrival', False)
        made.append(label)
    return {'start': [place[0], place[1]], 'directors': made}


def check_ready():
    for name in ('BP_SwimDirector', 'BP_Awakening', 'BP_GroveDirector'):
        if not library.does_asset_exist(game.BLUEPRINTS + '/' + name):
            raise RuntimeError(name + ' is missing: run grove:blueprints first')
    for name in ('MI_GR_Ground', 'MI_GR_Lake'):
        if not library.does_asset_exist(T.MATS + '/' + name):
            raise RuntimeError(name + ' is missing: run grove:materials first')


def build_level():
    check_ready()
    report = {'removed': open_level()}
    g = Ground()
    report['terrain'] = terrain(g)
    report['water'] = water(g)
    report['look'] = look()
    report['scatter'] = scatter()
    report['cliffs'] = cliffs()
    report['rim'] = rim_cover(g)
    report['trees'] = great_trees(g)
    report['start'] = start(g)
    save_level()
    return report


def execute(part):
    if part == 'look':
        report = {'removed': open_level((FOLDER + '/Light',)), 'look': look()}
    elif part == 'scatter':
        report = {'removed': open_level((FOLDER + '/Scatter', FOLDER + '/Bloom', FOLDER + '/Cliffs')), 'scatter': scatter(), 'cliffs': cliffs()}
    elif part == 'rim':
        report = {'removed': open_level((FOLDER + '/Rim',)), 'rim': rim_cover(Ground())}
    else:
        raise ValueError('unknown grove level part ' + part)
    save_level()
    return report
