import json
import math
import pathlib
import shutil

import unreal

import physis_gameplay_tools as game
from physis_lore import WING, WING_HEIGHT, wing_room, ABILITIES, BOSS_ENTRY, DRONE_ENTRY, RELEASE_ENTRY, LOG_ENTRIES, STORY_SCANS, all_entries, image_name, voice_name

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
TEX = '/Game/Art/Textures'
MAT = '/Game/Art/Materials'
KIT = '/Game/Art/Kit'
CINEMA = game.CINEMA
library = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
COMPRESS = unreal.TextureCompressionSettings
PROP = unreal.MaterialProperty


def texture(path, kind='color', fresh_copy=False):
    """Import one texture once, with the settings its map type needs."""
    path = ROOT / path
    asset = TEX + '/' + path.stem
    if fresh_copy or not library.does_asset_exist(asset):
        game.import_file(str(path), TEX)
    item = unreal.load_asset(asset)
    if item is None:
        raise RuntimeError('No texture ' + str(path))
    if kind == 'normal':
        item.set_editor_property('compression_settings', COMPRESS.TC_NORMALMAP)
        item.set_editor_property('srgb', False)
    elif kind == 'mask':
        item.set_editor_property('compression_settings', COMPRESS.TC_MASKS)
        item.set_editor_property('srgb', False)
    return item


def fresh(name, folder):
    path = folder + '/' + name
    if library.does_asset_exist(path):
        library.delete_asset(path)
    if not library.does_directory_exist(folder):
        library.make_directory(folder)
    return tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())


def sampler(material, name, default, kind, x, y):
    node = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('texture', default)
    if kind == 'normal':
        node.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    elif kind == 'mask':
        node.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    return node


def scalar(material, name, value, x, y):
    node = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', value)
    return node


def vector(material, name, value, x, y):
    node = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', unreal.LinearColor(*value, 1))
    return node


def maths(material, cls, a, b, x, y, a_out='', b_out=''):
    node = lib.create_material_expression(material, cls, x, y)
    lib.connect_material_expressions(a, a_out, node, 'A')
    if b is not None:
        lib.connect_material_expressions(b, b_out, node, 'B')
    return node


def wire_pbr(material, uv, base, normal, orm, tint):
    for node in (base, normal, orm):
        lib.connect_material_expressions(uv, '', node, 'UVs')
    tinted = maths(material, unreal.MaterialExpressionMultiply, base, tint, -300, -100, 'RGB')
    lib.connect_material_property(tinted, '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(normal, 'RGB', PROP.MP_NORMAL)
    lib.connect_material_property(orm, 'R', PROP.MP_AMBIENT_OCCLUSION)
    lib.connect_material_property(orm, 'G', PROP.MP_ROUGHNESS)
    lib.connect_material_property(orm, 'B', PROP.MP_METALLIC)
    return tinted


def master_station(default):
    """Tiled by world position, so the scaled graybox cubes keep true physical texel size."""
    material = fresh('M_StationSurface', MAT)
    # Custom nodes cannot take large-world positions, so the position is wrapped to a plain
    # float first. The wrap repeats every 64 tiles, where a texture seam would be invisible.
    position = lib.create_material_expression(material, unreal.MaterialExpressionWorldPosition, -1700, 0)
    tile = scalar(material, 'TileCM', 200, -1700, 300)
    span = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -1500, 300)
    span.set_editor_property('const_b', 64)
    lib.connect_material_expressions(tile, '', span, 'A')
    scaled = maths(material, unreal.MaterialExpressionDivide, position, span, -1300, 0)
    wrapped = lib.create_material_expression(material, unreal.MaterialExpressionFrac, -1150, 0)
    lib.connect_material_expressions(scaled, '', wrapped, '')
    facing = lib.create_material_expression(material, unreal.MaterialExpressionVertexNormalWS, -1300, 150)
    uv = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -1000, 100)
    uv.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    uv.set_editor_property('code', 'float3 a = abs(Facing); float2 uv = Where.xz; if (a.z > .5) uv = Where.xy; else if (a.x > .5) uv = Where.yz; return uv * 64.;')
    inputs = []
    for name in ('Where', 'Facing'):
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    uv.set_editor_property('inputs', inputs)
    lib.connect_material_expressions(wrapped, '', uv, 'Where')
    lib.connect_material_expressions(facing, '', uv, 'Facing')
    base = sampler(material, 'Base', default[0], 'color', -800, -200)
    normal = sampler(material, 'Normal', default[1], 'normal', -800, 100)
    orm = sampler(material, 'ORM', default[2], 'mask', -800, 400)
    tint = vector(material, 'Tint', (1, 1, 1), -600, -300)
    wire_pbr(material, uv, base, normal, orm, tint)
    lib.recompile_material(material)
    game.save(material)
    return material


def master_kit(default, mask, macro):
    """Kit surfaces: tiled PBR on UV0, edge wear on UV1, paint scheme in vertex colour B.
    Weathering comes from a world-scale macro map; the mask's baked grime is too blocky to use."""
    material = fresh('M_KitSurface', MAT)
    uv0 = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -1500, 0)
    uv1 = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -1500, 700)
    uv1.set_editor_property('coordinate_index', 1)
    base = sampler(material, 'Base', default[0], 'color', -1300, -200)
    normal = sampler(material, 'Normal', default[1], 'normal', -1300, 100)
    orm = sampler(material, 'ORM', default[2], 'mask', -1300, 400)
    wear = sampler(material, 'Mask', mask, 'mask', -1300, 700)
    for node in (base, normal, orm):
        lib.connect_material_expressions(uv0, '', node, 'UVs')
    lib.connect_material_expressions(uv1, '', wear, 'UVs')
    position = lib.create_material_expression(material, unreal.MaterialExpressionWorldPosition, -1700, 1000)
    spread = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -1500, 1000)
    spread.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    spread.set_editor_property('code', 'return P.xy / 1400 + P.z / 900;')
    entry = unreal.CustomInput()
    entry.set_editor_property('input_name', 'P')
    spread.set_editor_property('inputs', [entry])
    lib.connect_material_expressions(position, '', spread, 'P')
    weather = sampler(material, 'Macro', macro, 'mask', -1300, 1000)
    lib.connect_material_expressions(spread, '', weather, 'UVs')
    painted = scalar(material, 'Painted', 0, -1500, -400)
    tint = vector(material, 'Tint', (1, 1, 1), -1500, -300)
    colour = lib.create_material_expression(material, unreal.MaterialExpressionVertexColor, -1500, -600)
    scheme = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -1100, -400)
    scheme.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    scheme.set_editor_property('code', 'if (Painted < .5) return Tint; if (B > .9) return float3(.21, .25, .30); if (B < .1) return float3(.17, .20, .13); return float3(.30, .33, .37);')
    inputs = []
    for name in ('Painted', 'Tint', 'B'):
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    scheme.set_editor_property('inputs', inputs)
    lib.connect_material_expressions(painted, '', scheme, 'Painted')
    lib.connect_material_expressions(tint, '', scheme, 'Tint')
    lib.connect_material_expressions(colour, 'B', scheme, 'B')
    surface = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -800, -100)
    surface.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    surface.set_editor_property('code', 'float3 c = Col * Paint * lerp(.62, 1.1, smoothstep(.25, .75, V)); return lerp(c, float3(.42, .44, .47), M.g * .8);')
    inputs = []
    for name in ('Col', 'Paint', 'M', 'V'):
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    surface.set_editor_property('inputs', inputs)
    lib.connect_material_expressions(base, 'RGB', surface, 'Col')
    lib.connect_material_expressions(scheme, '', surface, 'Paint')
    lib.connect_material_expressions(wear, 'RGB', surface, 'M')
    lib.connect_material_expressions(weather, 'R', surface, 'V')
    lib.connect_material_property(surface, '', PROP.MP_BASE_COLOR)
    rough = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -800, 300)
    rough.set_editor_property('code', 'return lerp(saturate(O.g + (.5 - V) * .3), .3, M.g);')
    metal = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -800, 450)
    metal.set_editor_property('code', 'return lerp(O.b, 1., M.g);')
    for node in (rough, metal):
        node.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        inputs = []
        for name in ('O', 'M', 'V'):
            entry = unreal.CustomInput()
            entry.set_editor_property('input_name', name)
            inputs.append(entry)
        node.set_editor_property('inputs', inputs)
        lib.connect_material_expressions(orm, 'RGB', node, 'O')
        lib.connect_material_expressions(wear, 'RGB', node, 'M')
        lib.connect_material_expressions(weather, 'R', node, 'V')
    lib.connect_material_property(rough, '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(metal, '', PROP.MP_METALLIC)
    lib.connect_material_property(normal, 'RGB', PROP.MP_NORMAL)
    lib.connect_material_property(orm, 'R', PROP.MP_AMBIENT_OCCLUSION)
    lib.recompile_material(material)
    game.save(material)
    return material


def master_atlas(default):
    """One PBR atlas on UV0 with emissive: ships, station hull and hero props."""
    material = fresh('M_AtlasPBR', MAT)
    uv = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -1100, 0)
    base = sampler(material, 'Base', default[0], 'color', -800, -200)
    normal = sampler(material, 'Normal', default[1], 'normal', -800, 100)
    orm = sampler(material, 'ORM', default[2], 'mask', -800, 400)
    light = sampler(material, 'Light', default[3], 'color', -800, 700)
    lib.connect_material_expressions(uv, '', light, 'UVs')
    tint = vector(material, 'Tint', (1, 1, 1), -600, -300)
    tinted = wire_pbr(material, uv, base, normal, orm, tint)
    power = scalar(material, 'LightPower', 14, -600, 800)
    lit = maths(material, unreal.MaterialExpressionMultiply, light, power, -300, 700, 'RGB')
    # Space shots have no sun actor, because one would leak through the station interior.
    ambient = scalar(material, 'Ambient', 0, -600, 950)
    lift = maths(material, unreal.MaterialExpressionMultiply, tinted, ambient, -300, 900)
    total = maths(material, unreal.MaterialExpressionAdd, lit, lift, -120, 800)
    lib.connect_material_property(total, '', PROP.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    game.save(material)
    return material


def master_glow(default):
    material = fresh('M_KitGlow', MAT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    sample = sampler(material, 'Light', default, 'color', -700, 0)
    tint = vector(material, 'Tint', (.92, .96, 1), -700, 300)
    power = scalar(material, 'LightPower', 2.4, -700, 450)
    mixed = maths(material, unreal.MaterialExpressionMultiply, sample, tint, -450, 100, 'RGB')
    lit = maths(material, unreal.MaterialExpressionMultiply, mixed, power, -250, 200)
    lib.connect_material_property(lit, '', PROP.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    game.save(material)
    return material


def master_decal(default):
    material = fresh('M_KitDecal', MAT)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    sample = sampler(material, 'Base', default, 'color', -700, 0)
    lib.connect_material_property(sample, 'RGB', PROP.MP_BASE_COLOR)
    lib.connect_material_property(sample, 'A', PROP.MP_OPACITY_MASK)
    rough = lib.create_material_expression(material, unreal.MaterialExpressionConstant, -400, 300)
    rough.set_editor_property('r', .6)
    lib.connect_material_property(rough, '', PROP.MP_ROUGHNESS)
    lib.recompile_material(material)
    game.save(material)
    return material


def instance(name, parent, folder=MAT, textures=(), scalars=(), vectors=()):
    path = folder + '/' + name
    item = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(item, parent)
    for key, value in textures:
        lib.set_material_instance_texture_parameter_value(item, key, value)
    for key, value in scalars:
        lib.set_material_instance_scalar_parameter_value(item, key, value)
    for key, value in vectors:
        lib.set_material_instance_vector_parameter_value(item, key, unreal.LinearColor(*value, 1))
    lib.update_material_instance(item)
    game.save(item)
    return item


def pbr_set(stem, folder='Art/Materials', fresh_copy=False):
    return (texture('%s/%s_BaseColor.png' % (folder, stem), 'color', fresh_copy), texture('%s/%s_Normal.png' % (folder, stem), 'normal', fresh_copy),
            texture('%s/%s_ORM.png' % (folder, stem), 'mask', fresh_copy))


def fbx(path, folder, scale=.01):
    options = unreal.FbxImportUI()
    options.set_editor_property('import_mesh', True)
    options.set_editor_property('import_as_skeletal', False)
    options.set_editor_property('import_materials', False)
    options.set_editor_property('import_textures', False)
    options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    data = options.static_mesh_import_data
    data.set_editor_property('combine_meshes', True)
    data.set_editor_property('import_uniform_scale', scale)
    data.set_editor_property('generate_lightmap_u_vs', False)
    data.set_editor_property('auto_generate_collision', False)
    data.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)
    data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    game.import_file(str(ROOT / path), folder, options)
    return unreal.load_asset(folder + '/' + pathlib.Path(path).stem)


def assign(mesh, looks):
    for index, look in enumerate(looks):
        mesh.set_material(index, look)
    game.save(mesh)


def slots(mesh):
    return [str(slot.get_editor_property('material_slot_name')) for slot in mesh.get_editor_property('static_materials')]


def import_surfaces():
    if not library.does_directory_exist(TEX):
        library.make_directory(TEX)
    wall = pbr_set('T_WallPanel')
    master_station(wall)
    parent = unreal.load_asset(MAT + '/M_StationSurface')
    for name, stem, tile, tint in (('MI_Wall', 'T_WallPanel', 200, (1, 1, 1)), ('MI_Deck', 'T_DeckPlate', 160, (1, 1, 1)), ('MI_Ceiling', 'T_CeilingPanel', 200, (.8, .8, .85)),
                                   ('MI_Runner', 'T_FloorRunner', 100, (1, 1, 1)), ('MI_Titanium', 'T_TitaniumTrim', 50, (1, 1, 1)), ('MI_Hazard', 'T_HazardPaint', 100, (1, 1, 1)),
                                   ('MI_Composite', 'T_DarkComposite', 60, (1, 1, 1))):
        base, normal, orm = pbr_set(stem)
        instance(name, parent, textures=(('Base', base), ('Normal', normal), ('ORM', orm)), scalars=(('TileCM', tile),), vectors=(('Tint', tint),))
    return {'surfaces': 7}


def import_kit():
    if not library.does_directory_exist(KIT):
        library.make_directory(KIT)
    root = 'Art/Meshes/Kit/Textures'
    paint = pbr_set('T_KitPaint', root)
    metal = pbr_set('T_KitMetal', root)
    composite = pbr_set('T_DarkComposite')
    deck = pbr_set('T_DeckPlate')
    hazard = pbr_set('T_HazardPaint')
    foam = pbr_set('T_KitFoam', root)
    surface = master_kit(paint, texture(root + '/T_KitMask_WallPanel.png', 'mask'), texture('Art/Materials/T_MacroVariation_Mask.png', 'mask'))
    glow = master_glow(texture(root + '/T_KitLight_Emissive.png'))
    decal = master_decal(texture(root + '/T_KitDecal_BaseColor.png'))
    screen = instance('MI_KitScreen', glow, textures=(('Light', texture(root + '/T_KitScreen_Emissive.png')),), scalars=(('LightPower', 2.2),), vectors=(('Tint', (1, 1, 1)),))
    light = instance('MI_KitLight', glow)
    glass = instance('MI_KitGlass', unreal.load_asset(MAT + '/M_AtlasPBR')) if False else unreal.load_asset(CINEMA + '/MI_Crystal')
    space = unreal.load_asset(CINEMA + '/M_Space')
    sets = {'M_Wall': (paint, 1), 'M_Ceiling': (paint, 1), 'M_Trim': (metal, 0), 'M_Composite': (composite, 0), 'M_Rubber': (composite, 0),
            'M_Deck': (deck, 0), 'M_Hazard': (hazard, 0), 'M_Foam': (foam, 0)}
    fixed = {'M_Light': light, 'M_Screen': screen, 'M_Decal': decal, 'M_Glass': glass, 'M_Space': space}
    report = {}
    for path in sorted((ROOT / 'Art/Meshes/Kit').glob('SM_Kit_*.fbx')):
        mesh = fbx('Art/Meshes/Kit/' + path.name, KIT)
        short = path.stem[len('SM_Kit_'):]
        wear_path = root + '/T_KitMask_%s.png' % short
        wear = texture(wear_path, 'mask') if (ROOT / wear_path).exists() else texture(root + '/T_KitMask_BlastDoor.png', 'mask')
        looks = []
        for slot in slots(mesh):
            if slot in fixed:
                looks.append(fixed[slot])
                continue
            base, normal, orm = sets.get(slot, sets['M_Wall'])[0]
            painted = sets.get(slot, sets['M_Wall'])[1]
            tints = {'M_Rubber': (.25, .25, .25)}
            looks.append(instance('MI_%s_%s' % (short, slot[2:]), surface, KIT, (('Base', base), ('Normal', normal), ('ORM', orm), ('Mask', wear)),
                                  (('Painted', painted),), (('Tint', tints.get(slot, (1, 1, 1))),)))
        assign(mesh, looks)
        bounds = mesh.get_bounding_box()
        report[short] = [[round(v) for v in bounds.min.to_tuple()], [round(v) for v in bounds.max.to_tuple()], slots(mesh)]
    return report


def import_cinema():
    atlas = None
    shots = {'SM_Ship_Cruiser': 'T_Cruiser', 'SM_Ship_Frigate': 'T_Frigate', 'SM_Ship_Vigil': 'T_Vigil', 'SM_Ship_Shard': 'T_Shard', 'SM_Station_Hull': 'T_StationHull'}
    report = {}
    for stem, name in shots.items():
        folder = 'Art/Textures/Ships'
        base, normal, orm = pbr_set(name, folder)
        light = texture('%s/%s_Emissive.png' % (folder, name))
        if atlas is None:
            atlas = master_atlas((base, normal, orm, light))
        mesh = fbx('Art/Meshes/%s.fbx' % stem, CINEMA)
        looks = []
        for slot in slots(mesh):
            power = {'M_Drive': 16, 'M_Crystal': 7, 'M_CrystalGlow': 7}.get(slot, 14)
            looks.append(instance('MI_%s_%s' % (stem[3:], slot[2:]), atlas, CINEMA, (('Base', base), ('Normal', normal), ('ORM', orm), ('Light', light)), (('LightPower', power), ('Ambient', .3))))
        assign(mesh, looks)
        report[stem] = slots(mesh)
    # The new 8K sky and logo keep their old asset names, so nothing that uses them changes.
    work = ROOT / 'Saved/ArtImport'
    work.mkdir(exist_ok=True)
    shutil.copy(ROOT / 'Art/Sky/T_Sky_Space_8K.png', work / 'T_Sky_Space.png')
    game.import_file(str(work / 'T_Sky_Space.png'), CINEMA)
    stars = unreal.load_asset(CINEMA + '/T_Sky_Space')
    stars.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    stars.set_editor_property('never_stream', True)
    stars.set_editor_property('adjust_brightness', .3)
    game.save(stars)
    game.import_file(str(ROOT / 'Art/UI/T_UI_Title.png'), '/Game/UI')
    title = unreal.load_asset('/Game/UI/T_UI_Title')
    title.set_editor_property('compression_settings', COMPRESS.TC_EDITOR_ICON)
    title.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    title.set_editor_property('never_stream', True)
    game.save(title)
    return report


def import_props():
    atlas = unreal.load_asset(MAT + '/M_AtlasPBR')
    glow = {'T_Gun': 6, 'T_Drone': 8}
    report = {}
    for stem, name in (('SM_Physis_Gun', 'T_Gun'), ('SM_Pickup_Health', 'T_PickupHealth'), ('SM_Pickup_Divinity', 'T_PickupDivinity'), ('SM_Pickup_Ammo', 'T_PickupAmmo'),
                       ('SM_Drone', 'T_Drone'), ('SM_Scan_Conduit', 'T_ScanConduit'), ('SM_Scan_Terminal', 'T_ScanTerminal')):
        folder = 'Art/Materials/Props'
        base, normal, orm = pbr_set(name, folder, True)
        light = texture('%s/%s_Emissive.png' % (folder, name), 'color', True)
        item = instance('MI_' + name[2:], atlas, '/Game/Gameplay', (('Base', base), ('Normal', normal), ('ORM', orm), ('Light', light)), (('LightPower', glow.get(name, 8)),))
        mesh = fbx('Art/Meshes/Props/%s.fbx' % stem, '/Game/Gameplay')
        assign(mesh, [item] * len(slots(mesh)))
        bounds = mesh.get_bounding_box()
        report[stem] = [[round(v, 1) for v in bounds.min.to_tuple()], [round(v, 1) for v in bounds.max.to_tuple()]]
    return report


def dress():
    """Lines the graybox with kit pieces. The cubes stay as collision; kit pieces never collide."""
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        if actor.get_actor_label().startswith('Kit ') or actor.get_actor_label().startswith('Mood '):
            subsystem.destroy_actor(actor)
    count = [0]

    def kit(name, place, yaw=0, scale=(1, 1, 1), shadow=True):
        actor = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place), unreal.Rotator(0, 0, yaw))
        actor.set_actor_label('Kit ' + name)
        part = actor.static_mesh_component
        part.set_static_mesh(unreal.load_asset(KIT + '/SM_Kit_' + name))
        part.set_collision_profile_name('NoCollision')
        part.set_editor_property('cast_shadow', shadow)
        actor.set_actor_scale3d(unreal.Vector(*scale))
        actor.set_folder_path('Dressing')
        count[0] += 1
        return actor

    def run(start, end, fixed, axis, flip, height, gaps=()):
        """Panels along one wall, facing into the room. flip turns them to the other side."""
        tiers = max(1, round(height / 450))
        tier = height / tiers
        steps = max(1, round((end - start) / 400))
        size = (end - start) / steps
        for index in range(steps):
            middle = start + size * (index + .5)
            if any(abs(middle - gap) < 420 for gap in gaps):
                continue
            first = start + size * index
            if flip:
                first += size
            yaw = {(0, False): 0, (0, True): 180, (1, False): 90, (1, True): 270}[(axis, flip)]
            for level in range(tiers):
                place = (first, fixed, level * tier) if axis == 0 else (fixed, first, level * tier)
                if index % 7 == 3 and level == 0 and not gaps and axis == 0 and fixed < 0:
                    kit('HullBreach', place, yaw, (size / 400, 1, tier / 450))
                else:
                    kit('WallPanel', place, yaw, (size / 400, 1, tier / 450), False)
            kit('FloorTrim', (first, fixed, 0) if axis == 0 else (fixed, first, 0), yaw, (size / 400, 1, 1), False)
            if index % 3 == 1:
                kit('PipeRun' if index % 2 else 'PowerConduit', (first, fixed, min(height - 150, 300)) if axis == 0 else (fixed, first, min(height - 150, 300)), yaw, (size / 400, 1, 1), False)

    for index, (name, x1, x2, y1, y2, height) in enumerate(game.ROOMS):
        gaps = [3300] if name == 'Damage Control' else [5600] if name == 'Crew Ring' else [7200] if name == 'Armory' else []
        south = [3300, 12000] if name in ('Damage Control', 'Reactor Gallery') else [1800] if name == 'Breach Deck' else []
        run(x1, x2, y2, 0, True, height, gaps)
        run(x1, x2, y1, 0, False, height, south)
        run(y1, y2, x2, 1, False, height, [0])
        run(y1, y2, x1, 1, True, height, [0])
        if index + 1 < len(game.ROOMS):
            kit('DoorFrame', (x2, 0, 0), 90)
        # Ceiling grid, thinned to a spine in wide rooms to keep the triangle count honest.
        rows = max(1, (y2 - y1) // 400)
        for x in range(x1 + 200, x2, 400):
            for row in range(rows):
                y = y1 + (y2 - y1) * (row + .5) / rows
                if rows > 2 and row not in (rows // 2 - 1, rows // 2) and (x // 400) % 2:
                    continue
                kit('CeilingTruss', (x, y, height), 0, (1, (y2 - y1) / rows / 400, 1), False)
        # Rubber walkway along the spine of each room.
        strip = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector((x1 + x2) / 2, 0, .5))
        strip.set_actor_label('Kit Runner')
        strip.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        strip.static_mesh_component.set_material(0, unreal.load_asset(MAT + '/MI_Runner'))
        strip.static_mesh_component.set_collision_profile_name('NoCollision')
        strip.set_actor_scale3d(unreal.Vector((x2 - x1) / 100, 2.2, .01))
        strip.set_folder_path('Dressing')
    doors = wing_doors()
    for index, (name, kind, guide) in enumerate(WING):
        x1, x2, y1, y2, entry, exit_ = wing_room(index)
        gaps = {side: [at for i, s, at in doors if i == index and s == side] for side in ('north', 'south', 'east', 'west')}
        run(x1, x2, y2, 0, True, WING_HEIGHT, gaps['north'])
        run(x1, x2, y1, 0, False, WING_HEIGHT, gaps['south'])
        run(y1, y2, x2, 1, False, WING_HEIGHT, gaps['east'])
        run(y1, y2, x1, 1, True, WING_HEIGHT, gaps['west'])
        for point in (entry, exit_):
            kit('DoorFrame', (point[0], point[1], 0), 0 if point[1] in (y1, y2) and point[0] not in (x1, x2) else 90)
        for x in range(int(x1) + 200, int(x2), 400):
            for row in (0, 1):
                kit('CeilingTruss', (x, y1 + (y2 - y1) * (row + .5) / 2, WING_HEIGHT), 0, (1, (y2 - y1) / 2 / 400, 1), False)
    for x in (6700, 7300, 7900):
        kit('WeaponRack', (x, 760, 0), 180)
    for x in (4700, 5400, 6000):
        kit('Console', (x, -780, 0), 0)
    for x in (14000, 15000, 16000):
        kit('Terminal', (x, 1150, 0), 180)
    kit('Console', (17800, 0, 0), 90)
    # Surfaces and the set pieces that stand in for graybox blocks.
    swaps = {'Crate Low': ('CrateSmall', 200, 80), 'Crate Mid': ('CrateLarge', 200, 140), 'Crate High': ('CrateLarge', 200, 200),
             'Cover Pillar': ('Column', 140, 200), 'Arena Pillar': ('Column', 240, 300)}
    looks = {'Floor': 'MI_Deck', 'Ceiling': 'MI_Ceiling', 'Wall': 'MI_Wall', 'Collapsed Beam': 'MI_Hazard', 'Reactor Core': 'MI_Titanium', 'Sealed Divinity Door': 'MI_Hazard'}
    for actor in subsystem.get_all_level_actors():
        if not isinstance(actor, unreal.StaticMeshActor):
            continue
        label = actor.get_actor_label()
        if label.startswith(('Kit ', 'Cine ', 'Mood ')):
            continue
        for key, (piece, width, tall) in swaps.items():
            if label.startswith(key):
                spot = actor.get_actor_location()
                kit(piece, (spot.x, spot.y, 0), 0, (width / 206, width / 206, tall / 142) if 'Crate' in piece else (width / 168, width / 168, tall / 450))
                actor.static_mesh_component.set_material(0, unreal.load_asset(MAT + '/MI_Composite'))
                actor.set_actor_hidden_in_game(True)
                actor.static_mesh_component.set_editor_property('visible', False)
        for key, look in looks.items():
            if key in label:
                actor.static_mesh_component.set_material(0, unreal.load_asset(MAT + '/' + look))
    return {'pieces': count[0]}


def mood():
    """Dim, tinted key lights with a soft fill, so textures read and faces stay lit."""
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        if actor.get_actor_label().startswith('Mood '):
            subsystem.destroy_actor(actor)
    palette = {'Breach Deck': (1, .68, .5), 'Damage Control': (1, .74, .55), 'Crew Ring': (.8, .88, 1), 'Armory': (.84, .9, 1),
               'Boarding Spine': (.6, .8, 1), 'Reactor Gallery': (.5, .95, .92), 'Fleet Bridge Approach': (.65, .76, 1), 'Observation Deck': (.75, .84, 1), 'Service Loop': (1, .72, .5)}
    tints = {'enemies': (1, .55, .4), 'platform': (1, .7, .45), 'pulse': (1, .62, .35), 'gantry': (1, .7, .45), 'lifts': (.95, .72, .5), 'shoot': (1, .6, .35),
             'relay': (.45, .8, 1), 'triage': (.75, .95, 1), 'sequence': (.7, .6, 1), 'locks': (.6, .8, 1), 'node': (.45, 1, .65), 'final': (1, .85, .55)}
    for name, kind, guide in WING:
        palette['Wing ' + name] = tints[kind]
    lights = 0
    for actor in subsystem.get_all_level_actors():
        label = actor.get_actor_label()
        if isinstance(actor, unreal.PointLight) and label.endswith(' Light'):
            part = actor.get_component_by_class(unreal.PointLightComponent)
            part.set_light_color(unreal.LinearColor(*palette.get(label[:-len(' Light')], (.8, .9, 1)), 1))
            part.set_editor_property('intensity', 4000)
            part.set_editor_property('attenuation_radius', 2200)
            part.set_cast_shadows(True)
            lights += 1
        elif isinstance(actor, unreal.PostProcessVolume):
            settings = actor.get_editor_property('settings')
            for key, value in (('bloom_intensity', .5), ('vignette_intensity', .4), ('film_grain_intensity', .04), ('scene_fringe_intensity', .15),
                               ('auto_exposure_min_brightness', 1), ('auto_exposure_max_brightness', 1),
                               ('dynamic_global_illumination_method', unreal.DynamicGlobalIlluminationMethod.SCREEN_SPACE),
                               ('reflection_method', unreal.ReflectionMethod.SCREEN_SPACE)):
                settings.set_editor_property('override_' + key, True)
                settings.set_editor_property(key, value)
            actor.set_editor_property('settings', settings)
    for name, x1, x2, y1, y2, height in game.ROOMS:
        tint = palette.get(name, (.8, .9, 1))
        for x in range(x1 + 400, x2, 800):
            for y in (y1 * .5, y2 * .5):
                fill = subsystem.spawn_actor_from_class(unreal.PointLight, unreal.Vector(x, y, min(height - 120, 260)))
                fill.set_actor_label('Mood Fill')
                fill.set_folder_path('Dressing')
                part = fill.get_component_by_class(unreal.PointLightComponent)
                part.set_editor_property('intensity', 1000)
                part.set_editor_property('attenuation_radius', 1100)
                part.set_cast_shadows(False)
                part.set_light_color(unreal.LinearColor(*[.5 + c * .5 for c in tint], 1))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.EditorLoadingAndSavingUtils.save_map(world, game.LEVEL)
    return {'lights': lights}


def is_ward(part):
    """BP_TrainingDrone's second StaticMeshComponent, 'Ward' (Center session, center:drone_ward, 2026-11-08): empty
    and without collision except on the Center's Aegis Shard and Onyx Ward enemies, which give it a front plate. The
    drone body tools below must never put a drone mesh on it, or every drone would get a second body. Template
    components are named Ward_GEN_VARIABLE, placed ones Ward."""
    return part.get_name().split('_GEN')[0] == 'Ward'


def drone():
    bp = unreal.load_asset(game.BLUEPRINTS + '/BP_TrainingDrone')
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    done = []
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        part = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
        if isinstance(part, unreal.StaticMeshComponent) and not is_ward(part):
            done.append([part.get_name(), [round(v, 2) for v in part.get_editor_property('relative_scale3d').to_tuple()]])
            part.set_static_mesh(unreal.load_asset('/Game/Gameplay/SM_Drone'))
            part.set_material(0, unreal.load_asset('/Game/Gameplay/MI_Drone'))
            part.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    game.save(bp)
    return done


def sharpen():
    """Pins tiled sets at full mip, since the streamer can't see the world-position UVs,
    and gives each placed drone the new mesh, which its saved component otherwise overrides."""
    pinned = 0
    for stem in ('T_WallPanel', 'T_DeckPlate', 'T_CeilingPanel', 'T_FloorRunner', 'T_TitaniumTrim', 'T_HazardPaint', 'T_DarkComposite', 'T_KitPaint', 'T_KitMetal'):
        for kind in ('BaseColor', 'Normal', 'ORM'):
            item = unreal.load_asset('%s/%s_%s' % (TEX, stem, kind))
            if item:
                item.set_editor_property('never_stream', True)
                game.save(item)
                pinned += 1
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    drones = 0
    for actor in subsystem.get_all_level_actors():
        if actor.get_actor_label().startswith('Drone '):
            for part in actor.get_components_by_class(unreal.StaticMeshComponent):
                if is_ward(part):
                    continue
                part.set_static_mesh(unreal.load_asset('/Game/Gameplay/SM_Drone'))
                part.set_material(0, unreal.load_asset('/Game/Gameplay/MI_Drone'))
                part.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
                drones += 1
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.EditorLoadingAndSavingUtils.save_map(world, game.LEVEL)
    return {'pinned': pinned, 'drones': drones}


def scan_props():
    """Puts a real prop under the visible scan targets; the glowing markers stay as they are."""
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        if actor.get_actor_label().startswith('Prop '):
            subsystem.destroy_actor(actor)
    looks = {'Scan Conduit': ('SM_Scan_Conduit', (2900, -790, 62), 0), 'Scan Crew Terminal': ('SM_Scan_Terminal', (5300, 850, 61), 180)}
    for label, (mesh, place, yaw) in looks.items():
        prop = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place), unreal.Rotator(0, 0, yaw))
        prop.set_actor_label('Prop ' + label)
        prop.static_mesh_component.set_static_mesh(unreal.load_asset('/Game/Gameplay/' + mesh))
        prop.static_mesh_component.set_collision_profile_name('NoCollision')
        prop.set_folder_path('Dressing')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.EditorLoadingAndSavingUtils.save_map(world, game.LEVEL)
    return list(looks)


def menu_assets():
    """An empty map whose game mode shows only the menu HUD."""
    tools_bp = game.BLUEPRINTS
    made = {}
    for name, parent in (('BP_MenuHUD', unreal.HUD), ('BP_MenuGameMode', unreal.GameModeBase)):
        path = tools_bp + '/' + name
        if not library.does_asset_exist(path):
            factory = unreal.BlueprintFactory()
            factory.set_editor_property('parent_class', parent)
            made[name] = tools.create_asset(name, tools_bp, unreal.Blueprint, factory)
            unreal.BlueprintEditorLibrary.compile_blueprint(made[name])
            game.save(made[name])
    mode = unreal.load_asset(tools_bp + '/BP_MenuGameMode')
    defaults = unreal.get_default_object(mode.generated_class())
    defaults.set_editor_property('hud_class', unreal.load_asset(tools_bp + '/BP_MenuHUD').generated_class())
    defaults.set_editor_property('default_pawn_class', None)
    game.save(mode)
    level = '/Game/Levels/L_MainMenu'
    if not library.does_asset_exist(level):
        unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        world.get_world_settings().set_editor_property('default_game_mode', mode.generated_class())
        unreal.EditorLoadingAndSavingUtils.save_map(world, level)
    return {'level': level}


def flipbook_material():
    material = fresh('M_Flipbook', MAT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('two_sided', True)
    fire = texture('Art/FX/T_FX_Fireball_BaseColor.png')
    glow = texture('Art/FX/T_FX_Fireball_Emissive.png')
    coords = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -1200, 0)
    age = scalar(material, 'Age', 0, -1200, 150)
    age.set_editor_property('use_custom_primitive_data', True)
    age.set_editor_property('primitive_data_index', 0)
    grid = scalar(material, 'Grid', 8, -1200, 300)
    cell = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -950, 100)
    cell.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    cell.set_editor_property('code', 'float f = floor(saturate(Age) * (Grid * Grid - 1.)); return (UV + float2(fmod(f, Grid), floor(f / Grid))) / Grid;')
    inputs = []
    for name in ('UV', 'Age', 'Grid'):
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    cell.set_editor_property('inputs', inputs)
    lib.connect_material_expressions(coords, '', cell, 'UV')
    lib.connect_material_expressions(age, '', cell, 'Age')
    lib.connect_material_expressions(grid, '', cell, 'Grid')
    base = sampler(material, 'Base', fire, 'color', -700, -100)
    light = sampler(material, 'Light', glow, 'color', -700, 200)
    lib.connect_material_expressions(cell, '', base, 'UVs')
    lib.connect_material_expressions(cell, '', light, 'UVs')
    power = scalar(material, 'LightPower', 6, -500, 350)
    ambient = scalar(material, 'Ambient', .2, -500, 0)
    fade = scalar(material, 'Fade', 1, -500, 500)
    fade.set_editor_property('use_custom_primitive_data', True)
    fade.set_editor_property('primitive_data_index', 1)
    lit = maths(material, unreal.MaterialExpressionMultiply, light, power, -300, 250, 'RGB')
    soft = maths(material, unreal.MaterialExpressionMultiply, base, ambient, -300, 50, 'RGB')
    total = maths(material, unreal.MaterialExpressionAdd, lit, soft, -120, 150)
    lib.connect_material_property(total, '', PROP.MP_EMISSIVE_COLOR)
    alpha = maths(material, unreal.MaterialExpressionMultiply, base, fade, -300, 500, 'A')
    lib.connect_material_property(alpha, '', PROP.MP_OPACITY)
    lib.recompile_material(material)
    game.save(material)
    smoke = texture('Art/FX/T_FX_SmokePuff_BaseColor.png')
    sparks = texture('Art/FX/T_FX_Sparks.png')
    instance('MI_FX_Fire', material)
    instance('MI_FX_Smoke', material, textures=(('Base', smoke), ('Light', smoke)), scalars=(('Grid', 6), ('LightPower', 0), ('Ambient', .32)))
    instance('MI_FX_Spark', material, textures=(('Base', sparks), ('Light', sparks)), scalars=(('Grid', 4), ('LightPower', 18), ('Ambient', 0)))


def arc_material():
    material = fresh('M_SlashArc', MAT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('two_sided', True)
    coords = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    age = scalar(material, 'Age', 0, -900, 150)
    age.set_editor_property('use_custom_primitive_data', True)
    age.set_editor_property('primitive_data_index', 0)
    shape = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -600, 50)
    shape.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    shape.set_editor_property('code', 'float along = pow(UV.x, 2.2); float across = pow(UV.y, 5.) * (1. - smoothstep(.93, 1., UV.y)); float a = along * across * (1. - Age); return float3(1., .8, .48) * a * 9.;')
    inputs = []
    for name in ('UV', 'Age'):
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    shape.set_editor_property('inputs', inputs)
    lib.connect_material_expressions(coords, '', shape, 'UV')
    lib.connect_material_expressions(age, '', shape, 'Age')
    lib.connect_material_property(shape, '', PROP.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    game.save(material)
    return material


FX_ACTORS = (('BP_Burst', 'MI_FX_Fire'), ('BP_DroneBurst', 'MI_FX_Fire'), ('BP_Smoke', 'MI_FX_Smoke'), ('BP_DroneSmoke', 'MI_FX_Smoke'), ('BP_Spark', 'MI_FX_Spark'), ('BP_SlashFX', 'M_SlashArc'))


def fx_assets():
    flipbook_material()
    arc = arc_material()
    mesh = fbx('Art/Meshes/Props/SM_SlashArc.fbx', '/Game/Gameplay')
    mesh.set_material(0, arc)
    game.save(mesh)
    if not library.does_directory_exist('/Game/Audio'):
        library.make_directory('/Game/Audio')
    sounds = sorted((ROOT / 'Art/Audio/Game').glob('S_*.wav'))
    for path in sounds:
        game.import_file(str(path), '/Game/Audio')
    music = unreal.load_asset('/Game/Audio/S_Music_Combat')
    music.set_editor_property('looping', True)
    game.save(music)
    source = game.BLUEPRINTS + '/BP_Burst'
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    plane = unreal.load_asset('/Engine/BasicShapes/Plane')
    for name, look in FX_ACTORS:
        path = game.BLUEPRINTS + '/' + name
        if not library.does_asset_exist(path):
            library.duplicate_asset(source, path)
        bp = unreal.load_asset(path)
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            part = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(part, unreal.StaticMeshComponent):
                part.set_static_mesh(mesh if name == 'BP_SlashFX' else plane)
                part.set_material(0, arc if name == 'BP_SlashFX' else unreal.load_asset(MAT + '/' + look))
                part.set_editor_property('cast_shadow', False)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
    return {'sounds': len(sounds), 'fx': len(FX_ACTORS)}


# Name, source clip, spin degrees, forward lean degrees, leap height in cm.
FORGED = (('Cut', 'Slash1', 0, 16, 0), ('Slice', 'Slash2', -45, 18, 0), ('Whirl', 'Slash5', 360, 12, 0),
          ('Flash', 'Slash6', 40, 20, 0), ('Crescent', 'Slash3', 0, 18, 45), ('Gale', 'Slash4', -360, 12, 0),
          ('Rush', 'Slash9', 0, 24, 0), ('Reaper', 'Slash7', 360, 14, 25), ('Meteor', 'Slash8', 0, 32, 95),
          ('Thrust', 'Stab', 0, 28, 0), ('Heel', 'Kick1', -30, 14, 0), ('Rend', 'Combo1', 0, 18, 0),
          ('Spin', 'Kick2', 360, 10, 20), ('Drive', 'Combo2', 0, 20, 0), ('Cyclone', 'Combo3', 720, 12, 15),
          ('Pierce', 'Stab', 0, 36, 35), ('Storm', 'Combo5', -360, 14, 0), ('Bloom', 'Combo4', 0, 22, 75))


def ease(value):
    value = min(max(value, 0), 1)
    return value * value * (3 - 2 * value)


def quat_axis(x, y, z, degrees):
    half = math.radians(degrees) / 2
    return unreal.Quat(x * math.sin(half), y * math.sin(half), z * math.sin(half), math.cos(half))


def forge_clips():
    folder = '/Game/Characters/Physis/Animations/Katana'
    anim = unreal.AnimationLibrary
    rows = {}
    for name, source, spin, lean, leap in FORGED:
        path = folder + '/Physis_AS_F_' + name
        if library.does_asset_exist(path):
            library.delete_asset(path)
        clip = library.duplicate_asset(folder + '/Physis_AS_HK_' + source, path)
        count = anim.get_num_frames(clip) + 1
        poses = [anim.get_bone_pose_for_frame(clip, 'root', index, False) for index in range(count)]
        places = [pose.translation for pose in poses]
        turns = [pose.rotation for pose in poses]
        sizes = [pose.scale3d for pose in poses]
        out_places, out_turns = [], []
        for index in range(count):
            t = index / max(count - 1, 1)
            swing = ease((t - .12) / .46)
            pose = math.sin(math.pi * min(t / .8, 1)) ** 1.4
            add = quat_axis(0, 0, 1, spin * swing) * quat_axis(1, 0, 0, -lean * pose)
            base = turns[index]
            out_turns.append(base * add)
            point = places[index]
            out_places.append(unreal.Vector(point.x, point.y, point.z + leap * pose))
        clip.get_editor_property('controller').set_bone_track_keys('root', out_places, out_turns, sizes)
        game.save(clip)
        montage_path = folder + '/Montages/AM_Physis_F_' + name
        if library.does_asset_exist(montage_path):
            library.delete_asset(montage_path)
        factory = unreal.AnimMontageFactory()
        factory.set_editor_property('source_animation', clip)
        game.save(tools.create_asset('AM_Physis_F_' + name, folder + '/Montages', unreal.AnimMontage, factory))
        rows[name] = round(clip.get_play_length(), 3)
    return rows


def battle_assets():
    for name in ('S_Music_Combat', 'S_Laser1', 'S_Laser2', 'S_LaserHit'):
        game.import_file(str(ROOT / 'Art/Audio/Game' / (name + '.wav')), '/Game/Audio')
    music = unreal.load_asset('/Game/Audio/S_Music_Combat')
    music.set_editor_property('looping', True)
    game.save(music)
    look = instance('MI_EnemyBolt', unreal.load_asset('/Game/Gameplay/M_Physis_Item'), '/Game/Gameplay', vectors=(('Colour', (1, .08, .05)), ('Glow', (38, 3, 1.4))), scalars=(('Roughness', .4),))
    path = game.BLUEPRINTS + '/BP_EnemyBolt'
    if not library.does_asset_exist(path):
        library.duplicate_asset(game.BLUEPRINTS + '/BP_BoltTeal', path)
    bp = unreal.load_asset(path)
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        part = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
        if isinstance(part, unreal.StaticMeshComponent):
            part.set_material(0, look)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.get_default_object(bp.generated_class()).set_editor_property('initial_life_span', 3)
    game.save(bp)
    return {'bolt': True}


SCENARIO_PARTS = (('BP_Gate', '/Engine/BasicShapes/Cube', 'MI_Hazard', 'BlockAll'), ('BP_Switch', KIT + '/SM_Kit_Terminal', None, 'NoCollision'),
                  ('BP_Platform', '/Engine/BasicShapes/Cube', 'MI_Titanium', 'BlockAll'), ('BP_Hazard', '/Engine/BasicShapes/Cube', 'MI_Plasma', 'OverlapAllDynamic'),
                  ('BP_Checkpoint', None, None, None), ('BP_Encounter', None, None, None), ('BP_Watcher', None, None, None))


def scenario_assets():
    from editor_toolset.toolsets.actor import ActorTools
    instance('MI_Plasma', unreal.load_asset('/Game/Gameplay/M_Physis_Item'), MAT, vectors=(('Colour', (.05, .5, .6)), ('Glow', (.5, 5, 6.5))), scalars=(('Roughness', .25),))
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for name, mesh, look, collision in SCENARIO_PARTS:
        path = game.BLUEPRINTS + '/' + name
        if library.does_asset_exist(path):
            continue
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = tools.create_asset(name, game.BLUEPRINTS, unreal.Blueprint, factory)
        if mesh:
            root = None
            for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
                data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
                item = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
                if isinstance(item, unreal.SceneComponent):
                    root = item
            part = ActorTools.add_component(root, unreal.StaticMeshComponent.static_class(), 'Shape')
            part.set_static_mesh(unreal.load_asset(mesh))
            part.set_mobility(unreal.ComponentMobility.MOVABLE)
            part.set_collision_profile_name(collision)
            if look:
                part.set_material(0, unreal.load_asset(MAT + '/' + look))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
    return {'parts': len(SCENARIO_PARTS)}


SCENARIO_TUTORIALS = (('Move: W A S D / |LS|     Look: Mouse / |RS|', (320, 0, 160), (1, 2.6, 1)),
                      ('Jump: Space / |A|     Climb the crates', (800, 300, 160), (.5, 1.2, 1)),
                      ('Crystals hold Divinity.  Capsules heal.  Cells are ammo.', (1250, 0, 160), (.4, 2.6, 1)),
                      ('Interact with terminals: E / |X|', (2050, 500, 160), (.5, 1, 1)),
                      ('Divinity Sense: Q / |Y|     Then hold Right Mouse / |LT| on a marker. Scans fill your Logbook: L / |Menu| then the Logbook tab', (2650, 0, 160), (.4, 2.5, 1)),
                      ('Dodge: Left Alt / |B|     Block or parry: Right Mouse / |B| as an attack lands', (4500, 0, 160), (.4, 2.6, 1)),
                      ('Light attack: Left Mouse / |RB|     Heavy attack: Middle Mouse or F / |RT|', (4750, 0, 160), (.4, 2.6, 1)),
                      ('Hold Left Shift / |LT| to lock on     Chain attacks into combos', (5400, 0, 160), (.4, 2.6, 1)),
                      ('Draw your sidearm: Tab / |DU|     Reload: R / |DD|     Hold fire to charge a shot', (560, 0, 160), (.3, 2.6, 1)),
                      ('Pause Menu: Esc / Menu', (700, -300, 160), (.5, 1.2, 1)))


def box_part(subsystem, label, centre, size, look):
    actor = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*centre))
    actor.set_actor_label('Puzzle ' + label)
    actor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    actor.static_mesh_component.set_material(0, unreal.load_asset(MAT + '/' + look))
    actor.set_actor_scale3d(unreal.Vector(size[0] / 100, size[1] / 100, size[2] / 100))
    actor.set_folder_path('Scenario')
    return actor


def wrap_text(text, width=62):
    """Breaks a message into HUD lines with ~; |TOKEN| pad icons count as one short word."""
    lines, line, count = [], [], 0
    for word in text.split(' '):
        size = 3 if word.startswith('|') and word.endswith('|') else len(word)
        if count and count + 1 + size > width:
            lines.append(' '.join(line))
            line, count = [], 0
        line.append(word)
        count += size + (1 if count else 0)
    lines.append(' '.join(line))
    return '~'.join(lines)


def station_room_box(room):
    """Floor box (x1, x2, y1, y2) of a station fight room by a drone's RoomId: 1 Crew Ring, 2 Reactor Gallery,
    3 Fleet Bridge Approach (the boss), 101+ the Inner Ring rooms. Drones fight only while Physis is inside it
    (author, 2026-11-07; dronefix.py DroneThink). None for any other id: such a drone fights by distance."""
    names = {1: 'Crew Ring', 2: 'Reactor Gallery', 3: 'Fleet Bridge Approach'}
    if room in names:
        return next(r[1:5] for r in game.ROOMS if r[0] == names[room])
    if 101 <= room < 101 + len(WING):
        return wing_room(room - 101)[:4]
    return None


def room_box_props(room):
    box = station_room_box(room)
    if not box:
        return {}
    x1, x2, y1, y2 = box
    return {'RoomMin': unreal.Vector(x1, y1, -100000.0), 'RoomMax': unreal.Vector(x2, y2, 100000.0)}


def set_props(actor, **values):
    for key, value in values.items():
        if key in ('Message', 'Done', 'Denied', 'Objective', 'ScanText', 'NextGoal') and value:
            value = wrap_text(value)
        actor.set_editor_property(key, value)


def scenario_place():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith(('Puzzle ', 'Scene ', 'Drone ', 'Scan Drone ', 'Boss ')) or label == 'Door Armory' or isinstance(actor, unreal.TextRenderActor):
            subsystem.destroy_actor(actor)
    cls = lambda name: unreal.load_asset(game.BLUEPRINTS + '/' + name).generated_class()

    def spawn(name, label, place, scale=None, **values):
        actor = subsystem.spawn_actor_from_class(cls(name), unreal.Vector(*place))
        actor.set_actor_label('Scene ' + label)
        actor.set_folder_path('Scenario')
        if scale:
            actor.set_actor_scale3d(unreal.Vector(*scale))
        if values:
            set_props(actor, **values)
        return actor

    def platform(label, centre, size=(240, 240, 30), amp=(0, 0, 0), period=5, need=''):
        spawn('BP_Platform', label, centre, (size[0] / 100, size[1] / 100, size[2] / 100), AmpX=amp[0], AmpY=amp[1], AmpZ=amp[2], Period=period, Need=need)

    def step(label, top, x, y, size=240):
        box_part(subsystem, label, (x, y, top / 2), (size, size, top), 'MI_Titanium')

    def switch(label, place, yaw, **values):
        actor = spawn('BP_Switch', label, place, **values)
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        return actor

    def node(label, place, cost, give, done, need='', denied=''):
        actor = spawn('BP_Switch', 'Node ' + label, place, Cost=cost, Give=give, Done=done, Need=need, Denied=denied)
        part = actor.get_component_by_class(unreal.StaticMeshComponent)
        part.set_static_mesh(unreal.load_asset('/Game/Gameplay/SM_Pickup_Divinity'))
        part.set_relative_location(unreal.Vector(0, 0, 90), False, False)
        part.set_relative_scale3d(unreal.Vector(3.4, 3.4, 3.4))
        lamp = subsystem.spawn_actor_from_class(unreal.PointLight, unreal.Vector(place[0], place[1], 170))
        lamp.set_actor_label('Puzzle Node Light')
        lamp.set_folder_path('Scenario')
        light = lamp.get_component_by_class(unreal.PointLightComponent)
        light.set_light_color(unreal.LinearColor(.25, .85, 1, 1))
        light.set_editor_property('intensity', 2600)
        light.set_editor_property('attenuation_radius', 620)
        light.set_cast_shadows(False)

    def fuse(index, place):
        pickup = spawn('BP_Pickup', 'Fuse %d' % index, place, (1.8, 1.8, 1.8), Token=',got%d,' % index)
        pickup.set_editor_property('Kind', 3)

    def check(label, place, objective, radius=380):
        spawn('BP_Checkpoint', label, place, Radius=radius, Objective=objective)

    gates = {'Power': ((2400, 0), ',power,'), 'Coolant': ((4200, 0), ',coolant,'), 'Crew': ((6400, 0), ',wing,'), 'Armory': ((8200, 0), ',code,'),
             'Reactor': ((13400, 0), ',lift,'), 'Bridge': ((16400, 0), ',boss,')}
    for label, (where, need) in gates.items():
        spawn('BP_Gate', 'Gate ' + label, (where[0], where[1], 0), Need=need).set_actor_rotation(unreal.Rotator(0, 0, 90), False)
    spawn('BP_Gate', 'Gate Service', (3300, -800, 0), Need=',lift,')

    # Breach Deck: climb the wreckage for a fuse, then cross the live floor to the breaker.
    check('Breach', (300, 0, 110), 'Restore emergency power to the east door.', 300)
    fuse(1, (1600, 300, 250))
    spawn('BP_Hazard', 'Live Floor', (2030, 620, 3), (6.4, 4.8, 1), Deep=True)
    step('Island Step', 90, 1860, 520, 170)
    step('Breaker Island', 130, 2130, 720, 300)
    switch('Breaker', (2130, 770, 130), 200, Need=',fuse,', Give=',power,', Denied='The breaker is dead. Something is missing from it.', Done='Emergency power restored. The east door is open.')

    # Damage Control: pulsing floor strips guard the coolant valve; a scan shows it is safe.
    check('Damage Control', (2620, 0, 110), 'Physis needs to scan the live conduit to restore the coolant. Use Divinity Sense.')
    node('Calm One', (2620, 620, 0), 20, ',calm1,', 'Divinity settles the plasma. It goes dark and still.')
    # Narrow enough to jump, slow, and they cool in turn with a visible warm-up.
    for index, x in enumerate((3000, 3330, 3660)):
        spawn('BP_Hazard', 'Pulse %d' % index, (x, 0, 3), (1.5, 15.6, 1), Period=7, Offset=index * 3.1416, Off=',calm1,')
    conduit = next(a for a in subsystem.get_all_level_actors() if a.get_actor_label() == 'Scan Conduit')
    spawn('BP_Watcher', 'Conduit Watch', (2900, -760, 200), Target=conduit, Give=',conduit,', Message='Conduit traced. The coolant valve will now respond.')
    switch('Coolant Valve', (4060, 620, 0), 200, Need=',conduit,', Give=',coolant,', Denied='The valve is locked out. Physis needs to scan the live conduit first.', Done='Coolant rerouted. The Crew Ring door is open.')

    # Crew Ring: first fight.
    check('Crew Ring', (4380, 0, 110), 'Clear the Crew Ring.')
    room1 = [(5100, 420), (5700, -420)]
    room2 = [(11650, 760), (12850, -760), (12850, 760)]
    scan = cls('BP_ScanTarget')

    def drone(label, place, room, boss=False, health=6, scale=1, entry=None):
        actor = spawn('BP_TrainingDrone', label, place, (scale, scale, scale), RoomId=room, Boss=boss, Health=health, **room_box_props(room))
        tag = subsystem.spawn_actor_from_class(scan, unreal.Vector(place[0], place[1], place[2] + 70))
        tag.set_actor_label('Scene Tag ' + label)
        entry = entry or (BOSS_ENTRY if boss else DRONE_ENTRY)
        tag.set_editor_property('ScanCategory', entry[0])
        tag.set_editor_property('ScanTitle', entry[1])
        tag.set_editor_property('ScanText', wrap_text(entry[2]))
        tag.set_editor_property('ScanImportant', True)
        tag.set_folder_path('Scenario')
        game.hide_scan(tag)
        tag.attach_to_actor(actor, 'None', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
        return tag

    for index, place in enumerate(room1):
        drone('Drone A%d' % index, (place[0], place[1], 130), 1)
    spawn('BP_Encounter', 'Room One', (5300, 0, 300), Room=1, Learn=2, Give=',room1,', Message='Room clear. New techniques: Rising Cut and Crescent Step. The north door to the Inner Ring is open.', NextGoal='Find a way into the Armory. The crew may have left word.')
    fuse(2, (4850, 770, 215))
    step('Terminal Shelf', 120, 4850, 780, 170)
    terminal = next(a for a in subsystem.get_all_level_actors() if a.get_actor_label() == 'Scan Crew Terminal')

    # Armory: the order comes from the Crew Terminal scan, one room back.
    check('Armory', (6620, 0, 110), 'Lift the Armory lockdown.')
    switch('Panel Blue', (6900, -700, 0), 20, Seq=6, SeqBase=3, Give=',code,', Done='Blue accepted. Lockdown lifted: the Boarding Spine is open.')
    switch('Panel Red', (7500, -700, 0), 0, Seq=4, SeqBase=3, Done='Red accepted.')
    switch('Panel Gold', (8000, -700, 0), -20, Seq=5, SeqBase=3, Done='Gold accepted.')
    parent = unreal.load_asset('/Game/Gameplay/M_Physis_Item')
    for name, tone, x in (('Blue', (.1, .4, 1), 6900), ('Red', (1, .06, .04), 7500), ('Gold', (1, .62, .12), 8000)):
        instance('MI_Panel' + name, parent, MAT, vectors=(('Colour', tone), ('Glow', tuple(c * 18 for c in tone))), scalars=(('Roughness', .3),))
        box_part(subsystem, 'Panel Bar ' + name, (x, -700, 205), (150, 16, 12), 'MI_Panel' + name)
        glow = subsystem.spawn_actor_from_class(unreal.PointLight, unreal.Vector(x, -640, 190))
        glow.set_actor_label('Puzzle Light ' + name)
        glow.set_folder_path('Scenario')
        lamp = glow.get_component_by_class(unreal.PointLightComponent)
        lamp.set_light_color(unreal.LinearColor(*tone, 1))
        lamp.set_editor_property('intensity', 1600)
        lamp.set_editor_property('attenuation_radius', 420)
        lamp.set_cast_shadows(False)

    # Boarding Spine: the corridor floods with plasma; cross on moving platforms.
    check('Spine', (8330, 0, 110), 'Cross the flooded Boarding Spine. Scan the room for hints.', 300)
    node('Calm Two', (8300, 330, 0), 30, ',calm2,', 'Divinity settles the flood. The plasma goes dark and still.')
    spawn('BP_Hazard', 'Spine Plasma', (9620, 0, 3), (24.8, 7.6, 1), Deep=True, Off=',calm2,')
    platform('Spine 1', (8700, 0, 75), (340, 340, 30))
    platform('Spine 2', (9280, 0, 95), (320, 320, 30), (0, 220, 0), 5.5)
    platform('Spine 3', (9800, -200, 120), (320, 320, 30))
    fuse(3, (9800, -200, 200))
    platform('Spine 4', (10400, 0, 100), (340, 340, 30), (180, 0, 0), 4.6)

    # Reactor Gallery: second fight, then climb the core to vent it.
    check('Reactor', (11180, 0, 110), 'Take back the Reactor Gallery.')
    for index, place in enumerate(room2):
        drone('Drone B%d' % index, (place[0], place[1], 150), 2)
    spawn('BP_Encounter', 'Room Two', (12000, 0, 500), Room=2, Learn=3, Give=',room2,', Message='Gallery clear. New techniques: Falling Moon, Thousand Petals, Severing Wind. The reactor is yours to reach.', NextGoal='Reach the Fleet Bridge. Scan the core for hints.')
    node('Reactor Lift', (11400, -1000, 0), 20, ',lift,', 'Divinity surges through the core. The platforms rise and the Fleet Bridge door opens.~Far behind you, the Service Loop and a sealed door answer.', ',room2,', 'The drones still hold the gallery.')
    climb = ((11650, -400, 110), (11700, 200, 230), (12250, 560, 350))
    for index, spot in enumerate(climb):
        platform('Climb %d' % index, spot, (260, 260, 30), need=',lift,', period=4 + index * .4, amp=(0, 0, 18 if index % 2 else -18))
    platform('Climb Lift', (12780, 180, 430), (300, 300, 30), (0, 0, 120), 6.5, ',lift,')
    box_part(subsystem, 'Vent Ledge', (12780, -360, 500), (360, 360, 30), 'MI_Titanium')
    switch('Reactor Vent', (12800, -400, 515), 90, Need=',fuses,', Give=',reactor,', Denied='The vent will not answer. Its fuse sockets are not all filled.', Done='Reactor vented. The core runs cool again.')

    # Fleet Bridge Approach: the Mecha Breacher.
    check('Bridge', (13620, 0, 110), 'Get past whatever guards the Fleet Bridge. Scan it before you fight.')
    seam = drone('Boss Mecha Breacher', (14900, 0, 230), 3, True, 30, 2.6)
    spawn('BP_Encounter', 'Boss Room', (14900, 0, 600), Room=3, Learn=1, Give=',boss,', Message='Mecha Breacher destroyed. Final technique learned: Final Bloom. The way to the Observation Deck is open.', NextGoal='Go to the Observation Deck and face the fleets.')
    for x, y, kind in ((14000, 900, 0), (15800, -900, 2), (15800, 900, 0), (14000, -900, 2)):
        pickup = spawn('BP_Pickup', 'Arena Supply', (x, y, 130))
        pickup.set_editor_property('Kind', kind)

    # Observation Deck: the canon closing scene.
    check('Observation', (16620, 0, 110), 'Go to the Observation Deck and face the fleets.')
    switch('Observation', (18150, 0, 0), 90, Give=',end,', Finish=True, Done='The fleets fall quiet.')
    for category, title, text in all_entries():
        spawn('BP_LogVoice', 'Voice ' + title, (0, 0, -500), Title=title, Voice=unreal.load_asset('/Game/Audio/Voice/' + voice_name(title)),
              Image=unreal.load_asset('/Game/UI/Log/' + image_name(title)))
    for category, title, text, place in STORY_SCANS:
        tag = spawn('BP_ScanTarget', 'Story ' + title, place, ScanText=text, ScanCategory=category, ScanTitle=title, ScanImportant=True)
        game.hide_scan(tag)
    for actor in subsystem.get_all_level_actors():
        if actor.get_actor_label() in LOG_ENTRIES:
            category, title, text, important = LOG_ENTRIES[actor.get_actor_label()]
            set_props(actor, ScanCategory=category, ScanTitle=title, ScanText=text, ScanImportant=important)
    for actor in subsystem.get_all_level_actors():
        if actor.get_class().get_name() == 'BP_ScanTarget_C':
            text = actor.get_editor_property('ScanText')
            actor.set_editor_property('ScanText', wrap_text(text.replace('~', ' ')))
    wing_content(spawn, platform, step, switch, node, check, drone, cls)
    # Divinity vault behind Damage Control's sealed north door. The reactor node's Divinity (,lift,)
    # unseals it; inside waits the Life Augmentation, a permanent second bar of health.
    for actor in subsystem.get_all_level_actors():
        if actor.get_actor_label() == 'Door Sealed':
            subsystem.destroy_actor(actor)
    spawn('BP_Gate', 'Gate Vault', (3300, 800, 0), Need=',lift,')
    for label, centre, size in (('Vault Floor', (3300, 1120, -10), (640, 640, 20)), ('Vault Ceiling', (3300, 1120, 350), (640, 640, 20)),
                                ('Vault West Wall', (2990, 1120, 170), (20, 640, 360)), ('Vault East Wall', (3610, 1120, 170), (20, 640, 360)),
                                ('Vault North Wall', (3300, 1440, 170), (640, 20, 360))):
        box_part(subsystem, label, centre, size, 'MI_Titanium')
    box_part(subsystem, 'Vault Pedestal', (3300, 1230, 45), (140, 140, 90), 'MI_Titanium')
    box_part(subsystem, 'Vault Pedestal Trim', (3300, 1230, 92), (160, 160, 6), 'MI_PanelGold')
    light = subsystem.spawn_actor_from_class(unreal.PointLight, unreal.Vector(3300, 1230, 260))
    light.set_actor_label('Scene Vault Light')
    light.set_folder_path('Scenario')
    light.point_light_component.set_editor_property('intensity', 9000.0)
    light.point_light_component.set_editor_property('light_color', unreal.Color(130, 200, 255, 255))
    light.point_light_component.set_editor_property('attenuation_radius', 900.0)
    augment = spawn('BP_Pickup', 'Life Augmentation', (3300, 1230, 170), (2.2, 2.2, 2.2))
    augment.set_editor_property('Kind', 4)
    game.TUTORIALS = tuple((wrap_text(text), place, scale) for text, place, scale in SCENARIO_TUTORIALS)
    game.place_tutorials()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.EditorLoadingAndSavingUtils.save_map(world, game.LEVEL)
    return {'placed': True}



def charge_orb_assets():
    """The sidearm's charge orb: an additive Divinity-energy sphere with a point light, grown by BP_ChargeOrb."""
    from editor_toolset.toolsets.actor import ActorTools
    material = fresh('M_ChargeOrb', MAT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('two_sided', True)
    normal = lib.create_material_expression(material, unreal.MaterialExpressionVertexNormalWS, -900, 0)
    view = lib.create_material_expression(material, unreal.MaterialExpressionCameraVectorWS, -900, 120)
    coords = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -900, 240)
    clock = lib.create_material_expression(material, unreal.MaterialExpressionTime, -900, 360)
    charge = scalar(material, 'Charge', 0, -900, 480)
    charge.set_editor_property('use_custom_primitive_data', True)
    charge.set_editor_property('primitive_data_index', 0)
    # Bright core, swirling gold-to-teal rim, and a fast flicker once fully charged.
    code = ('float rim = 1. - saturate(abs(dot(normalize(N), normalize(V)))); float core = pow(1. - rim, 3.); '
            'float swirl = .5 + .5 * sin(UV.x * 38. + Time * 9. + sin(UV.y * 24. - Time * 6.) * 2.2); '
            'float bolts = pow(saturate(sin(UV.x * 90. - Time * 21.) * sin(UV.y * 60. + Time * 13.)), 12.) * Charge; '
            'float3 gold = float3(1., .48, .06); float3 teal = float3(.08, .8, .7); '
            'float3 c = gold * (core * .8 + rim * rim * 2.6 * swirl + .25) + teal * bolts * 2.2; '
            'float full = step(.999, Charge); c *= (.12 + Charge * .45) * (1. + full * (.35 + .3 * sin(Time * 31.))); return c;')
    colour = custom_node(material, code, ('N', 'V', 'UV', 'Time', 'Charge'), unreal.CustomMaterialOutputType.CMOT_FLOAT3, -450, 200)
    for node, name in ((normal, 'N'), (view, 'V'), (coords, 'UV'), (clock, 'Time'), (charge, 'Charge')):
        lib.connect_material_expressions(node, '', colour, name)
    lib.connect_material_property(colour, '', PROP.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    game.save(material)
    library = unreal.EditorAssetLibrary
    path = game.BLUEPRINTS + '/BP_ChargeOrb'
    if library.does_asset_exist(path):
        # Rebuilding the material replaces the asset, so point the orb at the new one.
        bp = unreal.load_asset(path)
        for handle in unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem).k2_gather_subobject_data_for_blueprint(bp):
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
            if isinstance(obj, unreal.StaticMeshComponent):
                obj.set_material(0, material)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_ChargeOrb', game.BLUEPRINTS, unreal.Blueprint, factory)
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        root = None
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
            if isinstance(obj, unreal.SceneComponent):
                root = obj
        shape = ActorTools.add_component(root, unreal.StaticMeshComponent.static_class(), 'Shape')
        shape.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
        shape.set_collision_profile_name('NoCollision')
        shape.set_editor_property('cast_shadow', False)
        shape.set_material(0, material)
        glow = ActorTools.add_component(root, unreal.PointLightComponent.static_class(), 'Glow')
        glow.set_editor_property('intensity', 0.0)
        glow.set_editor_property('light_color', unreal.Color(110, 200, 255, 255))
        glow.set_editor_property('attenuation_radius', 320.0)
        glow.set_editor_property('cast_shadows', False)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
    return {'material': material.get_name(), 'blueprint': path}


# Baroque scrollwork mask (0..1) from local position and normal: mirrored log spirals,
# curling stems, small rings and border bands, projected along the dominant local axis.
ORNAMENT = ('float3 n = abs(normalize(N)); float2 uv = n.x > max(n.y, n.z) ? P.yz : (n.y > n.z ? P.xz : P.xy); uv *= S; '
            'float2 id = floor(uv); float2 f = frac(uv) - .5; f.x = abs(f.x); '
            'float2 c = f - float2(.2, .03); float r = length(c) + 1e-4; float a = atan2(c.y, c.x); '
            'float turn = frac(log(r) * 1.7 - a / 6.2832 + id.y * .5); '
            'float spiral = smoothstep(.72, .93, 1. - abs(turn - .5) * 2.) * step(r, .3) * step(.03, r); '
            'float ring = smoothstep(.035, .0, abs(length(f - float2(.0, .33)) - .09)); '
            'float stem = smoothstep(.03, .0, abs(f.y + .22 * sin(f.x * 9. + 1.2))) * step(f.x, .42); '
            'float band = smoothstep(.035, .0, abs(abs(f.y) - .47)); '
            'return saturate(spiral + ring * .8 + stem * .7 + band); ')


def local_inputs(material, x, y):
    """Local position and local-space normal, the inputs the scrollwork is drawn from."""
    position = lib.create_material_expression(material, unreal.MaterialExpressionLocalPosition, x, y)
    normal = lib.create_material_expression(material, unreal.MaterialExpressionVertexNormalWS, x, y + 120)
    local = lib.create_material_expression(material, unreal.MaterialExpressionTransform, x + 150, y + 120)
    local.set_editor_property('transform_source_type', unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
    local.set_editor_property('transform_type', unreal.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
    lib.connect_material_expressions(normal, '', local, '')
    return position, local


def weapon_assets():
    """Ornate weapons: black-and-gold sidearm, white-and-gold katana with a light-blue energy blade."""
    made = {}
    # Sidearm: gloss black metal with gold scrollwork that catches a little light.
    gun = fresh('M_GunOrnate', MAT)
    position, normal = local_inputs(gun, -1100, 0)
    mask = custom_node(gun, 'float S = .34; ' + ORNAMENT, ('P', 'N'), unreal.CustomMaterialOutputType.CMOT_FLOAT1, -700, 0)
    lib.connect_material_expressions(position, '', mask, 'P')
    lib.connect_material_expressions(normal, '', mask, 'N')
    for prop, code in ((PROP.MP_BASE_COLOR, 'return lerp(float3(.012, .012, .014), float3(1., .7, .28), M);'),
                       (PROP.MP_METALLIC, 'return lerp(.75, 1., M);'), (PROP.MP_ROUGHNESS, 'return lerp(.3, .2, M);'),
                       (PROP.MP_EMISSIVE_COLOR, 'return float3(1., .62, .2) * M * .35;')):
        kind = unreal.CustomMaterialOutputType.CMOT_FLOAT3 if prop in (PROP.MP_BASE_COLOR, PROP.MP_EMISSIVE_COLOR) else unreal.CustomMaterialOutputType.CMOT_FLOAT1
        node = custom_node(gun, code, ('M',), kind, -350, 0)
        lib.connect_material_expressions(mask, '', node, 'M')
        lib.connect_material_property(node, '', prop)
    lib.recompile_material(gun)
    game.save(gun)
    made['gun'] = gun.get_name()
    # Katana: blade below Y -33, guard -33..-17, grip above. Energy blade glows light blue.
    sword = fresh('M_KatanaOrnate', MAT)
    position, normal = local_inputs(sword, -1100, 0)
    view = lib.create_material_expression(sword, unreal.MaterialExpressionCameraVectorWS, -1100, 300)
    world_normal = lib.create_material_expression(sword, unreal.MaterialExpressionVertexNormalWS, -1100, 420)
    clock = lib.create_material_expression(sword, unreal.MaterialExpressionTime, -1100, 540)
    mask = custom_node(sword, 'float S = P.y > -17. ? .3 : .22; ' + ORNAMENT, ('P', 'N'), unreal.CustomMaterialOutputType.CMOT_FLOAT1, -700, 0)
    lib.connect_material_expressions(position, '', mask, 'P')
    lib.connect_material_expressions(normal, '', mask, 'N')
    zone = 'float blade = step(P.y, -33.); float guard = step(-33., P.y) * step(P.y, -17.); float grip = step(-17., P.y); '
    channels = (
        (PROP.MP_BASE_COLOR, zone + 'float3 white = float3(.86, .85, .82); float3 gold = float3(1., .72, .3); '
                             'float3 guardc = lerp(gold, gold * .25, M); float3 gripc = lerp(white, gold, M); '
                             'return blade * float3(.18, .45, 1.) + guard * guardc + grip * gripc;', ('P', 'M')),
        (PROP.MP_METALLIC, zone + 'return blade * 0. + guard * 1. + grip * lerp(.1, 1., M);', ('P', 'M')),
        (PROP.MP_ROUGHNESS, zone + 'return blade * .2 + guard * lerp(.22, .45, M) + grip * lerp(.45, .22, M);', ('P', 'M')),
        (PROP.MP_EMISSIVE_COLOR, zone + 'float facing = saturate(abs(dot(normalize(W), normalize(V)))); '
                                 'float flicker = .92 + .08 * sin(Time * 47.) * sin(Time * 13.); '
                                 'float3 glow = float3(.1, .48, 1.) * (2.6 + 2.4 * (1. - facing)) + float3(.6, .88, 1.) * pow(facing, 8.) * 1.6; '
                                 'return blade * glow * flicker + (guard + grip) * float3(1., .66, .25) * M * .12;', ('P', 'M', 'W', 'V', 'Time')))
    for prop, code, names in channels:
        kind = unreal.CustomMaterialOutputType.CMOT_FLOAT3 if prop in (PROP.MP_BASE_COLOR, PROP.MP_EMISSIVE_COLOR) else unreal.CustomMaterialOutputType.CMOT_FLOAT1
        node = custom_node(sword, code, names, kind, -350, 0)
        sources = {'P': position, 'M': mask, 'W': world_normal, 'V': view, 'Time': clock}
        for name in names:
            lib.connect_material_expressions(sources[name], '', node, name)
        lib.connect_material_property(node, '', prop)
    lib.recompile_material(sword)
    game.save(sword)
    made['katana'] = sword.get_name()
    # Put them on Physis: the sidearm is 25% bigger.
    gun_part = game.template('Gun')
    gun_part.set_material(0, gun)
    gun_part.set_editor_property('relative_scale3d', unreal.Vector(1.25, 1.25, 1.25))
    game.template('Katana').set_material(0, sword)
    bp = unreal.load_asset(game.CHARACTER)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    game.save(bp)
    return made

def custom_node(material, code, names, output, x, y):
    node = lib.create_material_expression(material, unreal.MaterialExpressionCustom, x, y)
    node.set_editor_property('output_type', output)
    node.set_editor_property('code', code)
    inputs = []
    for name in names:
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    node.set_editor_property('inputs', inputs)
    return node


def liquid_plasma():
    """Rolling molten liquid on the organic pool mesh; vertex color carries the distance to shore."""
    material = fresh('M_PlasmaLiquid', MAT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    position = lib.create_material_expression(material, unreal.MaterialExpressionWorldPosition, -1300, 0)
    scaled = lib.create_material_expression(material, unreal.MaterialExpressionDivide, -1150, 0)
    scaled.set_editor_property('const_b', 6400)
    lib.connect_material_expressions(position, '', scaled, 'A')
    # No frac here: wrapping the position cut hard seams into the plasma every 64 m.
    wrapped = scaled
    clock = lib.create_material_expression(material, unreal.MaterialExpressionTime, -1000, 150)
    paint = lib.create_material_expression(material, unreal.MaterialExpressionVertexColor, -1000, 300)
    heat = scalar(material, 'Heat', 1, -1000, 600)
    heat.set_editor_property('use_custom_primitive_data', True)
    heat.set_editor_property('primitive_data_index', 0)
    # Value noise with a precision-stable hash (no sin), quintic blending and a rotation per octave,
    # so no grid squares or seams show as the plasma moves.
    # Hash of a cell corner into 0..1 (Dave Hoskins' hash12), written as statements.
    hash_at = lambda name, corner: ('float3 h%s = frac(float3((c + %s).xyx) * .1031); h%s += dot(h%s, h%s.yzx + 33.33); '
                                    'float %s = frac((h%s.x + h%s.y) * h%s.z); ') % (name, corner, name, name, name, name, name, name, name)
    fbm = ('{ float2 q = %s; n = 0.; float amp = .5; for (int i = 0; i < 5; i++) { float2 c = floor(q); float2 f = frac(q); '
           'f = f * f * f * (f * (f * 6. - 15.) + 10.); '
           + hash_at('a', 'float2(0, 0)') + hash_at('b', 'float2(1, 0)') + hash_at('d', 'float2(0, 1)') + hash_at('e', 'float2(1, 1)') +
           'n += amp * lerp(lerp(a, b, f.x), lerp(d, e, f.x), f.y); '
           'q = mul(float2x2(.8, -.6, .6, .8), q) * 2.03 + float2(t * (1. + i * .6), -t * .5); amp *= .5; } } ')
    code = ('float2 p = W.xy * 16.; float t = Time * .1; float n = 0.; ' + fbm % 'p' +
            'float first = n; float2 warp = p + float2(sin(first * 6.28 + t * 2.), cos(first * 5. - t * 1.6)) * .9; ' + fbm % 'warp' +
            'float flow = saturate((n - .3) * 2.6); float swirl = .5 + .5 * sin(n * 26. + first * 12. + Time * .9); '
            'float3 c = lerp(float3(.5, .03, .005), float3(5., .9, .08), flow); c = lerp(c, float3(13., 6.5, 1.4), pow(flow, 3.) * swirl); '
            'float3 cool = float3(.11, .012, .004) + float3(.45, .04, .01) * pow(swirl, 6.) * flow; c = lerp(cool, c, saturate(Heat)); '
            'float bank = saturate(Shore * 5. + (first - .5) * .7); '
            'float3 crust = float3(.014, .005, .004) + float3(.8, .12, .02) * pow(bank, 3.) * saturate(Heat); '
            'return lerp(crust, c, smoothstep(.45, 1., bank));')
    colour = custom_node(material, code, ('W', 'Time', 'Heat', 'Shore'), unreal.CustomMaterialOutputType.CMOT_FLOAT3, -500, 150)
    lib.connect_material_expressions(wrapped, '', colour, 'W')
    lib.connect_material_expressions(clock, '', colour, 'Time')
    lib.connect_material_expressions(heat, '', colour, 'Heat')
    lib.connect_material_expressions(paint, 'R', colour, 'Shore')
    lib.connect_material_property(colour, '', PROP.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    game.save(material)
    return material


def plasma_assets():
    for name in ('S_PlasmaLoop', 'S_PlasmaBurn', 'S_PickupHealth', 'S_PickupDivinity', 'S_PickupAmmo', 'S_PickupFuse'):
        game.import_file(str(ROOT / 'Art/Audio/Game' / (name + '.wav')), '/Game/Audio')
    loop = unreal.load_asset('/Game/Audio/S_PlasmaLoop')
    loop.set_editor_property('looping', True)
    game.save(loop)
    path = '/Game/Audio/SA_Plasma'
    if not library.does_asset_exist(path):
        fade = tools.create_asset('SA_Plasma', '/Game/Audio', unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
        settings = fade.get_editor_property('attenuation')
        settings.set_editor_property('falloff_distance', 1500)
        fade.set_editor_property('attenuation', settings)
        game.save(fade)
    material = liquid_plasma()
    pool = fbx('Art/Meshes/Props/SM_PlasmaPool.fbx', '/Game/Gameplay')
    pool.set_material(0, material)
    game.save(pool)
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    hazard = unreal.load_asset(game.BLUEPRINTS + '/BP_Hazard')
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(hazard):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        part = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
        if isinstance(part, unreal.StaticMeshComponent):
            part.set_material(0, material)
            part.set_static_mesh(pool)
            part.set_collision_profile_name('NoCollision')
            part.set_editor_property('cast_shadow', False)
    unreal.BlueprintEditorLibrary.compile_blueprint(hazard)
    game.save(hazard)
    # Gates become two blast-door leaves; each leaf needs its own box to block the player.
    meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    left = unreal.load_asset(KIT + '/SM_Kit_BlastDoor_L')
    right = unreal.load_asset(KIT + '/SM_Kit_BlastDoor_R')
    for mesh in (left, right):
        if meshes.get_simple_collision_count(mesh) == 0:
            meshes.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        game.save(mesh)
    from editor_toolset.toolsets.actor import ActorTools
    gate = unreal.load_asset(game.BLUEPRINTS + '/BP_Gate')
    root = shape_part = leaf = None
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(gate):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        part = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
        if isinstance(part, unreal.StaticMeshComponent):
            if 'LeafR' in part.get_name():
                leaf = part
            else:
                shape_part = part
        elif isinstance(part, unreal.SceneComponent):
            root = part
    leaf = leaf or ActorTools.add_component(root, unreal.StaticMeshComponent.static_class(), 'LeafR')
    for part, mesh in ((shape_part, left), (leaf, right)):
        part.set_static_mesh(mesh)
        part.set_mobility(unreal.ComponentMobility.MOVABLE)
        part.set_collision_profile_name('BlockAll')
    unreal.BlueprintEditorLibrary.compile_blueprint(gate)
    game.save(gate)
    return {'doors': meshes.get_simple_collision_count(left)}


def jump_feel():
    bp = unreal.load_asset(game.CHARACTER)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    # Rise lasts exactly as long as the button is held, up to the hold limit; heavier gravity
    # ends a released jump at once, and strong air control steers it all the way.
    cdo.set_editor_property('jump_max_hold_time', .34)
    move = cdo.get_editor_property('character_movement')
    for key, value in (('jump_z_velocity', 400), ('gravity_scale', 1.7), ('air_control', 1.0), ('air_control_boost_multiplier', 2), ('falling_lateral_friction', 1.5)):
        move.set_editor_property(key, value)
    game.save(bp)
    return {'hold': cdo.get_editor_property('jump_max_hold_time')}


def font_assets():
    game.import_file(str(ROOT / 'Art/Fonts/P052-Roman.otf'), '/Game/UI')
    face = unreal.load_asset('/Game/UI/P052-Roman') or unreal.load_asset('/Game/UI/P052-Roman_Font')
    found = [str(a.asset_name) + ':' + str(a.asset_class_path.asset_name) for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game/UI', False) if 'P052' in str(a.asset_name) or 'Physis' in str(a.asset_name)]
    return {'face': face.get_name() if face else None, 'class': face.get_class().get_name() if face else None, 'found': found, 'font_api': [x for x in dir(unreal) if 'Font' in x][:30]}


def surround_assets():
    """Positional audio: world sounds (drones, bolts, plasma, explosions) get a spatialized attenuation,
    so the audio mixer pans them across stereo, 5.1 or 7.1 speakers from where they happen.
    PlaySound2D ignores attenuation, so HUD and Physis's own sounds stay centred; music and voice are left alone."""
    path = '/Game/Audio/SA_World'
    fade = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset('SA_World', '/Game/Audio', unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    settings = fade.get_editor_property('attenuation')
    settings.set_editor_property('attenuate', True)
    settings.set_editor_property('spatialize', True)
    settings.set_editor_property('attenuation_shape_extents', unreal.Vector(400, 0, 0))
    settings.set_editor_property('falloff_distance', 4200)
    fade.set_editor_property('attenuation', settings)
    game.save(fade)
    done = []
    for asset in library.list_assets('/Game/Audio', recursive=False):
        name = asset.split('.')[-1]
        if not name.startswith('S_') or name.startswith(('S_Music', 'S_VO_')):
            continue
        sound = unreal.load_asset(asset)
        if not isinstance(sound, unreal.SoundWave) or (sound.get_editor_property('attenuation_settings') and name == 'S_PlasmaLoop'):
            continue
        sound.set_editor_property('attenuation_settings', fade)
        game.save(sound)
        done.append(name)
    return {'attenuation': path, 'sounds': done}


def pause_assets():
    if not library.does_directory_exist('/Game/Audio/Voice'):
        library.make_directory('/Game/Audio/Voice')
    voices = sorted((ROOT / 'Art/Audio/Voice').glob('S_VO_*.wav'))
    for path in voices:
        game.import_file(str(path), '/Game/Audio/Voice')
    for name, parent in (('BP_LogVoice', unreal.Actor), ('BP_PhysisSave', unreal.SaveGame)):
        path = game.BLUEPRINTS + '/' + name
        if not library.does_asset_exist(path):
            factory = unreal.BlueprintFactory()
            factory.set_editor_property('parent_class', parent)
            bp = tools.create_asset(name, game.BLUEPRINTS, unreal.Blueprint, factory)
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            game.save(bp)
    return {'voices': len(voices)}


def menu_art():
    game.import_file(str(ROOT / 'Art/UI/T_UI_LogoMark.png'), '/Game/UI')
    mark = unreal.load_asset('/Game/UI/T_UI_LogoMark')
    mark.set_editor_property('compression_settings', COMPRESS.TC_EDITOR_ICON)
    mark.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    mark.set_editor_property('never_stream', True)
    game.save(mark)
    return {'mark': True}


def look_from(eye, target):
    return unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))


def capture_logs():
    """Photographs every Logbook subject in the level and imports the shots as textures."""
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    target = unreal.RenderingLibrary.create_render_target2d(world, 768, 432, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    camera = subsystem.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0))
    part = camera.capture_component2d
    part.set_editor_property('texture_target', target)
    part.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    part.set_editor_property('fov_angle', 70)
    labels = {a.get_actor_label(): a for a in subsystem.get_all_level_actors()}
    rooms = {name: (x1, x2, h) for name, x1, x2, y1, y2, h in game.ROOMS}
    poses = {}
    for label, (category, title, text, important) in LOG_ENTRIES.items():
        spot = labels[label].get_actor_location().to_tuple()
        poses[title] = spot
    for category, title, text, place in STORY_SCANS:
        poses[title] = place
    drone = labels.get('Scene Drone A0')
    boss = labels.get('Scene Boss Mecha Breacher')
    poses[DRONE_ENTRY[1]] = drone.get_actor_location().to_tuple() if drone else (5100, 420, 130)
    poses[BOSS_ENTRY[1]] = boss.get_actor_location().to_tuple() if boss else (14900, 0, 230)
    release = next((a for l, a in labels.items() if l.startswith('Scene Wing Release')), None)
    poses[RELEASE_ENTRY[1]] = release.get_actor_location().to_tuple() if release else (7200, 7800, 260)
    out = ROOT / 'Art/UI/Log'
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for category, title, text in all_entries():
        spot = poses[title]
        if title in rooms:
            x1, x2, height = rooms[title]
            eye = (x1 + 160, -260, min(height * .62, 300))
            aim = (x2, 120, height * .3)
        else:
            sideways = -1 if spot[1] > 0 else 1
            reach = 520 if title == BOSS_ENTRY[1] else 300
            eye = (spot[0] - reach * .55, spot[1] + sideways * reach, spot[2] + 70)
            aim = spot
            if title == RELEASE_ENTRY[1]:
                # The release hangs by the exit wall, so look at it from inside the room.
                eye, aim = (spot[0] - 250, spot[1] + 650, spot[2] + 20), spot
        camera.set_actor_location_and_rotation(unreal.Vector(*eye), look_from(eye, aim), False, False)
        part.capture_scene()
        name = image_name(title)
        unreal.RenderingLibrary.export_render_target(world, target, str(out), name + '.png')
        made.append(name)
    subsystem.destroy_actor(camera)
    for folder, source in (('/Game/UI/Log', out), ('/Game/UI/Abilities', ROOT / 'Art/UI/Abilities')):
        if not library.does_directory_exist(folder):
            library.make_directory(folder)
        for path in sorted(source.glob('T_*.png')):
            game.import_file(str(path), folder)
            image = unreal.load_asset(folder + '/' + path.stem)
            image.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
            image.set_editor_property('never_stream', True)
            game.save(image)
    return {'shots': len(made)}


def wing_doors():
    """Door gaps per room wall: (room index, side, coordinate along the wall)."""
    doors = []
    for index in range(len(WING)):
        x1, x2, y1, y2, entry, exit_ = wing_room(index)
        for point in (entry, exit_):
            side = 'south' if point[1] == y1 and point[0] != x1 and point[0] != x2 else 'north' if point[1] == y2 else 'west' if point[0] == x1 else 'east'
            doors.append((index, side, point[0] if side in ('north', 'south') else point[1]))
    return doors


WING_GOALS = ('Inner Ring: cross the Cargo Lift Hall.', 'Inner Ring: get through the Mess Hall.', 'Inner Ring: restore the Comms Relay door. Scan the room for hints.',
              'Inner Ring: cross the Coolant Vats.', 'Inner Ring: get through the Barracks.', 'Inner Ring: unlock the Signal Junction. Scan the room for hints.',
              'Inner Ring: cross the Starboard Gantry.', 'Inner Ring: get through the Drone Hangar.', 'Inner Ring: release the Pressure Locks. Scan the room for hints.',
              'Inner Ring: open the Fuel Line Maze door. Scan the room for hints.', 'Inner Ring: get through the Armory Annex.', 'Inner Ring: cross Hydroponics. Scan the room for hints.',
              'Inner Ring: cross the Ventilation Shaft.', 'Inner Ring: get through the Officer Quarters.', 'Inner Ring: open the Medical Bay door. Scan the room for hints.',
              'Inner Ring: release the ring from the Command Spur. Scan the room for hints.')


def wing_content(spawn, platform, step, switch, node, check, drone, cls):
    """Fills the Inner Ring: one checkpoint, scan and challenge per room."""
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    labels = {a.get_actor_label(): a for a in subsystem.get_all_level_actors()}
    spawn('BP_Gate', 'Gate Inner Entry', (5600, 900, 0), Need=',room1,')
    for index, (name, kind, guide) in enumerate(WING):
        x1, x2, y1, y2, entry, exit_ = wing_room(index)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = exit_[0] - entry[0], exit_[1] - entry[1]
        length = (dx * dx + dy * dy) ** .5
        dx, dy = dx / length, dy / length
        px, py = -dy, dx
        # Points along the walk from entry to exit, kept 2.5 m clear of every wall.
        along = lambda t, side=0.0, z=0.0: (min(max(entry[0] + dx * length * t + px * side, x1 + 250), x2 - 250),
                                            min(max(entry[1] + dy * length * t + py * side, y1 + 250), y2 - 250), z)
        token = ',w%d,' % index
        check('Wing %d' % index, along(.1, 0, 110), WING_GOALS[index], 300)
        on_x = abs(dy) > .5
        pool = lambda off='': spawn('BP_Hazard', 'Wing Pool %d' % index, along(.5, 0, 3), ((15.0, 10.0, 1) if on_x else (10.0, 15.0, 1)), Deep=True, Off=off)
        exit_gate = None
        if kind == 'platform':
            pool()
            for k, (t, side) in enumerate(((.36, 160), (.64, -160))):
                spot = along(t, side, 80)
                platform('Wing Lift %d %d' % (index, k), spot, (330, 330, 30), (px * 220, py * 220, 0) if k == 1 else (0, 0, 0), 4.8)
        elif kind == 'pulse':
            for k, t in enumerate((.25, .42, .58, .75)):
                spot = along(t, 0, 3)
                spawn('BP_Hazard', 'Wing Pulse %d %d' % (index, k), spot, ((15.6, 1.4, 1) if on_x else (1.4, 15.6, 1)), Period=7, Offset=k * 1.5708)
        elif kind == 'gantry':
            pool()
            for k, (t, high, side) in enumerate(((.3, 90, 0), (.5, 165, 120), (.7, 90, 0))):
                spot = along(t, side)
                step('Wing Gantry %d %d' % (index, k), high, spot[0], spot[1], 260)
        elif kind == 'lifts':
            pool()
            for k, t in enumerate((.38, .62)):
                platform('Wing Shaft %d %d' % (index, k), along(t, 0, 110), (320, 320, 30), (0, 0, 110), 5.5 + k)
        elif kind == 'enemies':
            # Tall solid parts no drone may start on: x, y and half width. On 2026-11-07 the wall clamp in along()
            # put Drone W7 1 on Wing Pillar 7 0 (both clamped to the same corner of the diagonal hangar walk). In
            # Play the drone's floor push lifted it out of the 4.5 m pillar and through the 4.7 m ceiling, where it
            # followed her out of reach, so the hangar fight never ended and its door never opened (author's
            # playtest). Low parts (tables, the dais) stay out: drones hover above them.
            blocks = []
            if name == 'Mess Hall':
                for k, (t, side) in enumerate(((.35, -250), (.45, 250), (.62, -120), (.7, 300))):
                    spot = along(t, side)
                    box_part(subsystem, 'Wing Table %d %d' % (index, k), (spot[0], spot[1], 45), (260, 120, 90), 'MI_Composite')
            elif name == 'Barracks':
                spawn('BP_Hazard', 'Wing Band %d' % index, along(.5, 0, 3), ((15.6, 1.6, 1) if on_x else (1.6, 15.6, 1)), Period=6)
            elif name == 'Drone Hangar':
                for k, side in enumerate((-300, 300)):
                    spot = along(.5, side)
                    box_part(subsystem, 'Wing Pillar %d %d' % (index, k), (spot[0], spot[1], 225), (150, 150, 450), 'MI_Hazard')
                    blocks.append((spot[0], spot[1], 75))
            elif name == 'Armory Annex':
                for k in range(3):
                    ammo = spawn('BP_Pickup', 'Wing Ammo %d' % k, along(.12, -300 + 300 * k, 130))
                    ammo.set_editor_property('Kind', 2)
            elif name == 'Officer Quarters':
                spot = along(.5)
                box_part(subsystem, 'Wing Dais %d' % index, (spot[0], spot[1], 30), (620, 620, 60), 'MI_Titanium')
                for k in range(2):
                    heal = spawn('BP_Pickup', 'Wing Capsule %d' % k, along(.12, -200 + 400 * k, 130))
                    heal.set_editor_property('Kind', 0)
            count = 3 if name in ('Drone Hangar', 'Officer Quarters') else 2
            for k in range(count):
                t, side, high = .35 + .2 * k, (-1) ** k * 380, 260 if name == 'Armory Annex' else 140
                # The usual spot, else the other side, else the walk line itself: the first one at least 80 cm
                # clear of every block's faces.
                for t2, side2 in ((t, side), (t, -side), (t, 0), (t + .1, side), (t - .1, -side)):
                    spot = along(t2, side2, high)
                    if all(max(abs(spot[0] - bx), abs(spot[1] - by)) > half + 80 for bx, by, half in blocks):
                        break
                drone('Drone W%d %d' % (index, k), spot, 101 + index)
            spawn('BP_Encounter', 'Wing Fight %d' % index, (cx, cy, 300), Room=101 + index, Learn=0, Give=token, Message='Room clear. The door is unsealed.', NextGoal='Go through the unsealed door.')
            exit_gate = token
        elif kind in ('relay', 'triage'):
            title = 'Comms Relay Node' if kind == 'relay' else 'Triage Console'
            tag = labels.get('Scene Story ' + title) or next((a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == 'Scene Story ' + title), None)
            mark = ',relay,' if kind == 'relay' else ',triage,'
            spawn('BP_Watcher', 'Wing Watch %d' % index, (cx, cy, 200), Target=tag, Give=mark, Message='Fault traced. The switch beside the exit will now respond.')
            if kind == 'triage':
                for k, (t, high) in enumerate(((.55, 70), (.68, 140), (.8, 210))):
                    spot = along(t, 420)
                    step('Wing Gurney %d %d' % (index, k), high, spot[0], spot[1], 200)
                switch('Wing Switch %d' % index, along(.8, 420, 210), 0, Need=mark, Give=token, Denied='The switch is dead. Something in this room controls it.', Done='Override accepted. The door is open.')
            else:
                switch('Wing Switch %d' % index, along(.85, 420, 0), 0, Need=mark, Give=token, Denied='The switch is dead. Something in this room controls it.', Done='Override accepted. The door is open.')
            exit_gate = token
        elif kind == 'sequence':
            for k, (t, colour, seq) in enumerate(((.28, 'Red', 3), (.5, 'Gold', 1), (.72, 'Blue', 2))):
                spot = along(t, 600, 0)
                panel = switch('Wing Panel %d %s' % (index, colour), spot, 0, Seq=seq, SeqBase=0, Give=token if seq == 3 else '', Done=('%s accepted.' % colour) if seq < 3 else 'Red accepted. The junction is open.')
                box_part(subsystem, 'Wing Bar %d %s' % (index, colour), (spot[0], spot[1], 205), (150, 16, 12) if not on_x else (16, 150, 12), 'MI_Panel' + colour)
            exit_gate = token
        elif kind == 'shoot':
            spawn('BP_Hazard', 'Wing Pool %d' % index, along(.66, 0, 3), ((15.0, 6.6, 1) if on_x else (6.6, 15.0, 1)), Deep=True, Off=token)
            release = drone('Wing Release %d' % index, along(.95, 300, 260), 101 + index, health=1, scale=.7, entry=RELEASE_ENTRY)
            target = release.get_attach_parent_actor()
            target.set_editor_property('Static', True)
            spawn('BP_Encounter', 'Wing Shot %d' % index, (cx, cy, 300), Room=101 + index, Learn=0, Give=token, Message='Release struck. The plasma drains and the door opens.', NextGoal='Go through the open door.')
            exit_gate = token
        elif kind == 'locks':
            # The far lock stands back in the Drone Hangar, in its open north-west quarter, clear of the pillars.
            hx1, hx2, hy1, hy2 = wing_room(index - 1)[:4]
            switch('Wing Lock Far', (hx1 + 350, hy2 - 350, 0), 0, Give=',lockA,', Done='A lock releases with a hiss.')
            switch('Wing Lock Near', along(.85, 500, 0), 0, Need=',lockA,', Give=token, Denied='The lock will not move. Something else is holding it.', Done='Both locks released. The door is open.')
            exit_gate = token
        elif kind == 'node':
            pool(',calm11,')
            node('Wing Bloom', along(.12, 600, 0), 20, ',calm11,', 'Divinity settles the flood. The plasma goes dark and still.')
            for k in range(2):
                crystal = spawn('BP_Pickup', 'Wing Crystal %d' % k, along(.1, -500 + 250 * k, 130))
                crystal.set_editor_property('Kind', 1)
        elif kind == 'final':
            switch('Wing Command', along(.6, 450, 0), 0, Give=',wing,', Done='Inner Ring released. The way south to the Armory is open.')
            exit_gate = ',wing,'
        if exit_gate:
            spawn('BP_Gate', 'Gate Wing %d' % index, (exit_[0], exit_[1], 0), Need=exit_gate).set_actor_rotation(unreal.Rotator(0, 0, 0 if exit_[1] in (y1, y2) and exit_[0] not in (x1, x2) else 90), False)


def vista_assets():
    """Copies of the fleet ship and battle director that live on after the opening is cleaned up."""
    made = {}
    for name, source in (('BP_VistaShip', 'BP_FleetShip'), ('BP_VistaDirector', 'BP_BattleDirector')):
        path = game.BLUEPRINTS + '/' + name
        item = unreal.load_asset(path)
        if item is None:
            item = library.duplicate_asset(game.BLUEPRINTS + '/' + source, path)
        made[name] = item.get_path_name() if item else None
        if item:
            game.save(item)
    return made


def vista_place():
    """A window in the Breach Deck's south wall and a battle that never stops beyond it."""
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith('Vista ') or label == 'Breach Deck South Wall':
            subsystem.destroy_actor(actor)
    station = game.Station()
    for x1, x2, z1, z2 in ((0, 1250, 0, 500), (2350, 2400, 0, 500), (1250, 2350, 0, 110), (1250, 2350, 430, 500)):
        station.box('Breach Deck South Wall', 'Breach Deck', ((x1 + x2) / 2, -900, (z1 + z2) / 2), (x2 - x1, 40, z2 - z1))
    for label, centre, size in (('Sill', (1800, -880, 105), (1140, 80, 22)), ('Header', (1800, -880, 435), (1140, 80, 22)),
                                ('Post West', (1245, -880, 270), (26, 80, 352)), ('Post East', (2355, -880, 270), (26, 80, 352)), ('Mullion', (1800, -880, 270), (18, 30, 320))):
        part = box_part(subsystem, label, centre, size, 'MI_Titanium')
        part.set_actor_label('Vista ' + label)
    ship = unreal.load_asset(game.BLUEPRINTS + '/BP_VistaShip').generated_class()
    rng = __import__('random').Random(23)
    models = (('SM_Ship_Cruiser', 'SM_Ship_Frigate', 'SM_Ship_Frigate', 2600, 0), ('SM_Ship_Vigil', 'SM_Ship_Shard', 'SM_Ship_Shard', -2600, 180))
    for side, (big, small, other, speed, yaw) in enumerate(models):
        for index in range(18):
            place = unreal.Vector(rng.uniform(-60000, 60000), -14000 - rng.uniform(0, 70000) - side * 8000, rng.uniform(-14000, 16000))
            actor = subsystem.spawn_actor_from_class(ship, place, unreal.Rotator(0, rng.uniform(-3, 3), yaw + rng.uniform(-6, 6)))
            actor.set_actor_label('Vista Ship %d %02d' % (side, index))
            actor.set_editor_property('SpeedX', speed * rng.uniform(.6, 1.1))
            part = actor.get_component_by_class(unreal.StaticMeshComponent)
            part.set_static_mesh(unreal.load_asset(game.CINEMA + '/' + (big if index % 6 == 0 else small if index % 2 else other)))
            actor.set_actor_scale3d(unreal.Vector(*[3.5 if index % 6 == 0 else 2.2] * 3))
            actor.set_folder_path('Vista')
    director = subsystem.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/BP_VistaDirector').generated_class(), unreal.Vector(1800, -20000, 0))
    director.set_actor_label('Vista Director')
    director.set_folder_path('Vista')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.EditorLoadingAndSavingUtils.save_map(world, game.LEVEL)
    return {'ships': 36}


def wing_build():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith('Wing ') or label in ('Crew Ring North Wall', 'Armory North Wall'):
            subsystem.destroy_actor(actor)
    station = game.Station()
    station.wall('Crew Ring North Wall', 'Crew Ring', 900, 0, 4200, 6400, 450, [5600])
    station.wall('Armory North Wall', 'Armory', 800, 0, 6400, 8200, 450, [7200])
    doors = wing_doors()
    for index, (name, kind, guide) in enumerate(WING):
        x1, x2, y1, y2, entry, exit_ = wing_room(index)
        label = 'Wing ' + name
        station.shell(label, x1, x2, y1, y2, WING_HEIGHT)
        gaps = {side: [at for i, s, at in doors if i == index and s == side] for side in ('north', 'south', 'east', 'west')}
        station.wall(label + ' North Wall', label, y2, 0, x1, x2, WING_HEIGHT, gaps['north'])
        station.wall(label + ' South Wall', label, y1, 0, x1, x2, WING_HEIGHT, gaps['south'])
        station.wall(label + ' East Wall', label, x2, 1, y1, y2, WING_HEIGHT, gaps['east'])
        station.wall(label + ' West Wall', label, x1, 1, y1, y2, WING_HEIGHT, gaps['west'])
        station.light(label + ' Light', label, ((x1 + x2) / 2, (y1 + y2) / 2, WING_HEIGHT - 60), 1800)
        for fx, fy in ((x1 + 400, y1 + 400), (x2 - 400, y2 - 400)):
            fill = station.actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(fx, fy, 260))
            fill.set_actor_label(label + ' Fill')
            fill.set_folder_path('Station/' + label)
            lamp = fill.get_component_by_class(unreal.PointLightComponent)
            lamp.set_editor_property('intensity', 1000)
            lamp.set_editor_property('attenuation_radius', 1100)
            lamp.set_cast_shadows(False)
            lamp.set_light_color(unreal.LinearColor(.85, .9, 1, 1))
    for name, x, y1, y2, wide in (('Wing Entry Hall', 5600, 900, 1500, 400), ('Wing Exit Hall', 7200, 800, 1500, 400)):
        station.shell(name, x - wide / 2, x + wide / 2, y1, y2, 400)
        station.wall(name + ' East Wall', name, x + wide / 2, 1, y1, y2, 400)
        station.wall(name + ' West Wall', name, x - wide / 2, 1, y1, y2, 400)
        station.light(name + ' Light', name, (x, (y1 + y2) / 2, 340), 900)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.EditorLoadingAndSavingUtils.save_map(world, game.LEVEL)
    return {'rooms': len(WING), 'pieces': station.count}


def execute(operation):
    if operation == 'vista_assets':
        return json.dumps(vista_assets())
    if operation == 'vista_place':
        return json.dumps(vista_place())
    if operation == 'wing_build':
        return json.dumps(wing_build())
    if operation == 'capture_logs':
        return json.dumps(capture_logs())
    if operation == 'menu_art':
        return json.dumps(menu_art())
    if operation == 'surround_assets':
        return json.dumps(surround_assets())
    if operation == 'pause_assets':
        return json.dumps(pause_assets())
    if operation == 'font_make':
        font = unreal.load_asset('/Game/UI/F_Physis')
        font.set_editor_property('font_cache_type', unreal.FontCacheType.RUNTIME)
        font.set_editor_property('legacy_font_size', 14)
        game.save(font)
        return json.dumps({'size': font.get_editor_property('legacy_font_size')})
    if operation.startswith('font_size:'):
        # Canvas draws the runtime font at this size and scales the glyphs, so a large size keeps text sharp.
        font = unreal.load_asset('/Game/UI/F_Physis')
        font.set_editor_property('legacy_font_size', int(operation.split(':')[1]))
        game.save(font)
        return json.dumps({'size': font.get_editor_property('legacy_font_size')})
    if operation == 'font_probe':
        font = unreal.load_asset('/Game/UI/F_Physis')
        if font is None:
            font = tools.create_asset('F_Physis', '/Game/UI', unreal.Font, unreal.FontFactory())
        rows = {'font': [x for x in dir(font) if 'font' in x or 'composite' in x or 'legacy' in x], 'composite': [x for x in dir(unreal.CompositeFont) if not x.startswith('_')][:20]}
        for name in ('Typeface', 'TypefaceEntry', 'FontData'):
            kind = getattr(unreal, name, None)
            rows[name] = [x for x in dir(kind) if not x.startswith('_')][:24] if kind else None
        return json.dumps(rows)
    if operation == 'font_assets':
        return json.dumps(font_assets())
    if operation == 'jump_feel':
        return json.dumps(jump_feel())
    if operation == 'plasma_errors':
        material = unreal.load_asset(MAT + '/M_Plasma')
        unreal.SystemLibrary.execute_console_command(unreal.EditorLevelLibrary.get_editor_world(), 'recompileshaders material M_Plasma')
        return json.dumps({'blend': str(material.get_editor_property('blend_mode')), 'usage': [k for k in ('used_with_static_lighting',) ]})
    if operation == 'plasma_only':
        material = liquid_plasma()
        stats = lib.get_statistics(material)
        fbx('Art/Meshes/Props/SM_PlasmaPool.fbx', '/Game/Gameplay')
        hazard = unreal.load_asset(game.BLUEPRINTS + '/BP_Hazard')
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(hazard):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            part = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(part, unreal.StaticMeshComponent):
                part.set_material(0, material)
        unreal.BlueprintEditorLibrary.compile_blueprint(hazard)
        game.save(hazard)
        pool = unreal.load_asset('/Game/Gameplay/SM_PlasmaPool')
        for index in range(len(pool.get_editor_property('static_materials'))):
            pool.set_material(index, material)
        game.save(pool)
        return json.dumps({'pixel': stats.num_pixel_shader_instructions, 'vertex': stats.num_vertex_shader_instructions})
    if operation == 'plasma_assets':
        return json.dumps(plasma_assets())
    if operation == 'watch_info':
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        rows = []
        for actor in subsystem.get_all_level_actors():
            if 'BP_Watcher' in actor.get_class().get_name():
                target = actor.get_editor_property('Target')
                rows.append([actor.get_actor_label(), target.get_actor_label() if target else None, target.get_class().get_name() if target else None])
        return json.dumps(rows)
    if operation == 'tag_info':
        # Scene tags of the open level and what each is attached to (drone tags must ride their drone).
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        rows = []
        for actor in subsystem.get_all_level_actors():
            if actor.get_actor_label().startswith('Scene Tag '):
                parent = actor.get_attach_parent_actor()
                rows.append([actor.get_actor_label(), parent.get_actor_label() if parent else None])
        return json.dumps({'level': unreal.EditorLevelLibrary.get_editor_world().get_name(), 'tags': rows})
    if operation == 'pie_drone_info':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        rows = []
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if 'BP_TrainingDrone' in actor.get_class().get_name():
                row = [actor.get_actor_label()] + [round(v) for v in actor.get_actor_location().to_tuple()]
                for name in ('Health', 'RoomId', 'StuckFor', 'Static', 'Boss', 'SpotActive', 'StunUntil'):
                    try:
                        value = actor.get_editor_property(name)
                        row.append(round(value, 2) if isinstance(value, float) else value)
                    except Exception:
                        row.append('?')
                rows.append(row)
        return json.dumps(rows)
    if operation == 'pie_drones':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        rows = []
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if 'BP_TrainingDrone' in actor.get_class().get_name():
                at = actor.get_actor_location()
                rows.append([round(at.x), round(at.y), round(at.z)])
        return json.dumps(rows)
    if operation.startswith('pie_jump_for:'):
        hold = float(operation.split(':')[1])
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        base = pawn.get_actor_location().z
        state = {'t': 0, 'top': 0, 'released': False}
        pawn.jump()

        def tick(dt):
            state['t'] += dt
            state['top'] = max(state['top'], pawn.get_actor_location().z - base)
            if state['t'] >= hold and not state['released']:
                state['released'] = True
                pawn.stop_jumping()
            if state['t'] > 1.4:
                unreal.unregister_slate_post_tick_callback(state['handle'])
                pathlib.Path(unreal.Paths.project_saved_dir(), 'Connection', 'jump.txt').write_text(str(round(state['top'])))
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
        return json.dumps({'jumping': hold})
    if operation == 'pie_pickups':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        rows = [[a.get_editor_property('Kind'), round(a.get_actor_location().x), round(a.get_actor_location().y)] for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_asset(game.BLUEPRINTS + '/BP_Pickup').generated_class())]
        return json.dumps({'count': len(rows), 'last': rows[-3:]})
    if operation == 'hazard_info':
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if 'BP_Hazard' in actor.get_class().get_name():
                part = actor.get_component_by_class(unreal.StaticMeshComponent)
                mesh = part.get_editor_property('static_mesh')
                bounds = mesh.get_bounding_box()
                rows.append([actor.get_actor_label(), mesh.get_name(), part.get_material(0).get_name(), [round(v) for v in actor.get_actor_scale3d().to_tuple()], [round(v) for v in bounds.max.to_tuple()], str(part.get_editor_property('visible'))])
        return json.dumps(rows)
    if operation.startswith('pie_look:'):
        pitch, yaw = [float(v) for v in operation.split(':')[1].split(',')]
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        controller = unreal.GameplayStatics.get_player_controller(world, 0)
        controller.set_control_rotation(unreal.Rotator(0, pitch, yaw))
        rows = []
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_asset(game.BLUEPRINTS + '/BP_Hazard').generated_class()):
            part = actor.get_component_by_class(unreal.StaticMeshComponent)
            at = part.get_world_location()
            box = part.get_editor_property('static_mesh').get_bounding_box()
            rows.append([part.get_material(0).get_name(), [round(v) for v in at.to_tuple()], [round(v) for v in part.get_world_scale().to_tuple()], str(part.is_visible()), round(actor.get_editor_property('Glow'), 2), [round(v, 1) for v in box.min.to_tuple()], [round(v, 1) for v in box.max.to_tuple()]])
        return json.dumps(rows)
    if operation == 'pool_fix':
        pool = unreal.load_asset('/Game/Gameplay/SM_PlasmaPool')
        look = unreal.load_asset(MAT + '/M_PlasmaLiquid')
        for index in range(len(pool.get_editor_property('static_materials'))):
            pool.set_material(index, look)
        game.save(pool)
        return json.dumps({'fixed': True})
    if operation == 'pool_slots':
        mesh = unreal.load_asset('/Game/Gameplay/SM_PlasmaPool')
        return json.dumps([[str(m.get_editor_property('material_slot_name')), m.get_editor_property('material_interface').get_name() if m.get_editor_property('material_interface') else None] for m in mesh.get_editor_property('static_materials')])
    if operation == 'plasma_tests':
        out = []
        for name, code in (('M_TestA', 'return float3(6., 1., .1);'), ('M_TestB', 'return float3(6., 1., .1) * (.6 + .4 * sin(Time));'),
                           ('M_TestC', 'float2 p = W.xy * 16.; return float3(frac(p), .1) * 5. * (.6 + .4 * sin(Time));')):
            material = fresh(name, MAT)
            material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
            position = lib.create_material_expression(material, unreal.MaterialExpressionWorldPosition, -1300, 0)
            scaled = lib.create_material_expression(material, unreal.MaterialExpressionDivide, -1150, 0)
            scaled.set_editor_property('const_b', 6400)
            lib.connect_material_expressions(position, '', scaled, 'A')
            wrapped = lib.create_material_expression(material, unreal.MaterialExpressionFrac, -1000, 0)
            lib.connect_material_expressions(scaled, '', wrapped, '')
            clock = lib.create_material_expression(material, unreal.MaterialExpressionTime, -1000, 150)
            node = custom_node(material, code, ('W', 'Time'), unreal.CustomMaterialOutputType.CMOT_FLOAT3, -500, 0)
            lib.connect_material_expressions(wrapped, '', node, 'W')
            lib.connect_material_expressions(clock, '', node, 'Time')
            lib.connect_material_property(node, '', PROP.MP_EMISSIVE_COLOR)
            lib.recompile_material(material)
            game.save(material)
            out.append(lib.get_statistics(material).num_pixel_shader_instructions)
        return json.dumps(out)
    if operation.startswith('pie_mat:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        look = unreal.load_asset(operation.split(':')[1])
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_asset(game.BLUEPRINTS + '/BP_Hazard').generated_class()):
            actor.get_component_by_class(unreal.StaticMeshComponent).set_material(0, look)
        return json.dumps({'look': look.get_name()})
    if operation.startswith('pie_scanat:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        title = operation.split(':')[1]
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_asset(game.BLUEPRINTS + '/BP_ScanTarget').generated_class()):
            if title in actor.get_editor_property('ScanTitle'):
                actor.set_editor_property('ScanDone', False)
                pawn.call_method('PhysisAddLog', (actor.get_editor_property('ScanCategory'), actor.get_editor_property('ScanTitle'), actor.get_editor_property('ScanText')))
                actor.set_editor_property('ScanDone', True)
                return json.dumps({'logged': title})
        return json.dumps({'logged': None})
    if operation == 'pie_log':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        return json.dumps({'open': pawn.get_editor_property('LogOpen'), 'data': pawn.get_editor_property('LogData')[:200], 'boss': pawn.get_editor_property('BossShown')})
    if operation.startswith('pie_page:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pawn.set_editor_property('MenuPage', int(operation.split(':')[1]))
        return json.dumps({'page': pawn.get_editor_property('MenuPage')})
    if operation == 'pie_voice':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        comp = pawn.get_editor_property('VoiceComp')
        return json.dumps({'voice': comp.sound.get_name() if comp and comp.sound else None, 'playing': comp.is_playing() if comp else None, 'title': pawn.get_editor_property('MenuTitle')})
    if operation == 'pie_quest':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        return json.dumps({'done': pawn.get_editor_property('QuestDone')[:80]})
    if operation.startswith('pie_aim:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        controller = unreal.GameplayStatics.get_player_controller(world, 0)
        title = operation.split(':')[1]
        target = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_asset(game.BLUEPRINTS + '/BP_ScanTarget').generated_class()) if title in a.get_editor_property('ScanTitle'))
        camera = next(c for c in pawn.get_components_by_class(unreal.CameraComponent))
        controller.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(camera.get_world_location(), target.get_actor_location()))
        return json.dumps({'target': target.get_actor_location().to_tuple()})
    if operation.startswith('pie_scandbg:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        title = operation.split(':')[1]
        rows = {'on': pawn.get_editor_property('ScanVisorOn'), 'held': pawn.get_editor_property('ScanHeld'), 'best': round(pawn.get_editor_property('VisorBest'), 4)}
        for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_asset(game.BLUEPRINTS + '/BP_ScanTarget').generated_class()):
            if title in a.get_editor_property('ScanTitle'):
                rows['t'] = [round(a.get_editor_property('ScanAimDot'), 4), a.get_editor_property('ScanInView'), a.get_editor_property('ScanAimed'), round(a.get_editor_property('ScanProgress'), 2), a.get_editor_property('ScanDone')]
        return json.dumps(rows)
    if operation.startswith('pie_speed:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        sideways = operation.split(':')[1] == 'side'
        state = {'t': 0, 'top': 0}

        def tick(dt):
            state['t'] += dt
            pawn.add_movement_input(pawn.get_actor_right_vector() if sideways else pawn.get_actor_forward_vector(), 1.0, False)
            v = pawn.get_velocity()
            state['top'] = max(state['top'], (v.x ** 2 + v.y ** 2) ** .5)
            if state['t'] > 1.2:
                unreal.unregister_slate_post_tick_callback(state['handle'])
                pathlib.Path(unreal.Paths.project_saved_dir(), 'Connection', 'speed.txt').write_text(str(round(state['top'])))
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
        return json.dumps({'moving': True})
    if operation == 'pie_lockon':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pawn.set_editor_property('LockHeld', True)
        pawn.call_method('PhysisLockFind')
        target = pawn.get_editor_property('LockTarget')
        return json.dumps({'target': target.get_name() if target else None})
    if operation == 'drone_info':
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if 'BP_TrainingDrone' in actor.get_class().get_name():
                for part in actor.get_components_by_class(unreal.StaticMeshComponent):
                    mesh = part.get_editor_property('static_mesh')
                    rows.append([actor.get_actor_label(), part.get_name(), mesh.get_name() if mesh else None, str(part.is_visible()), str(actor.is_hidden_ed()), [round(v, 1) for v in part.get_world_scale().to_tuple()], [round(v) for v in actor.get_actor_location().to_tuple()]])
        return json.dumps(rows)
    if operation == 'theme_import':
        game.import_file(str(ROOT / 'Art/Audio/Game/S_Music_MainTheme.wav'), '/Game/Audio')
        theme = unreal.load_asset('/Game/Audio/S_Music_MainTheme')
        theme.set_editor_property('looping', True)
        game.save(theme)
        return json.dumps({'theme': theme.get_name()})
    if operation == 'switch_info':
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if 'Wing Panel' in actor.get_actor_label():
                rows.append([actor.get_actor_label(), actor.get_editor_property('Seq'), actor.get_editor_property('SeqBase'), actor.get_editor_property('Give'), [round(v) for v in actor.get_actor_location().to_tuple()]])
        return json.dumps(rows)
    if operation.startswith('pie_time:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pawn.set_editor_property('LevelTime', float(operation.split(':')[1]))
        return json.dumps({'time': pawn.get_editor_property('LevelTime')})
    if operation == 'pie_ach':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        return json.dumps({'station': pawn.get_editor_property('AchStation'), 'swift': pawn.get_editor_property('AchSwift'), 'time': round(pawn.get_editor_property('LevelTime'), 1), 'done': pawn.get_editor_property('LevelDone')})
    if operation.startswith('area_all:'):
        x1, x2, y1, y2 = [float(v) for v in operation.split(':')[1].split(',')]
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            for part in actor.get_components_by_class(unreal.StaticMeshComponent):
                o, e, r = unreal.SystemLibrary.get_component_bounds(part)
                if o.x + e.x > x1 and o.x - e.x < x2 and o.y + e.y > y1 and o.y - e.y < y2 and e.x * e.y > 0 and (e.y > 500 or e.x > 500) and o.z < 600:
                    mesh = part.get_editor_property('static_mesh')
                    rows.append([actor.get_actor_label(), mesh.get_name() if mesh else None, [round(v) for v in o.to_tuple()], [round(v) for v in e.to_tuple()]])
        return json.dumps(rows)
    if operation.startswith('pie_window:'):
        width, height = [int(v) for v in operation.split(':')[1].split(',')]
        settings = unreal.find_object(None, '/Script/UnrealEd.Default__LevelEditorPlaySettings')
        for key, value in (('new_window_width', width), ('new_window_height', height), ('center_new_window', True)):
            try:
                settings.set_editor_property(key, value)
            except Exception as error:
                return json.dumps({'error': str(error), 'key': key})
        return json.dumps({'window': [width, height]})
    if operation.startswith('pie_drive:'):
        # pie_drive:X,Y,SECONDS[,JUMP_AT] walks Physis along (X, Y) for SECONDS of game time, jumping once at JUMP_AT.
        args = [float(v) for v in operation.split(':', 1)[1].split(',')]
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        start = unreal.GameplayStatics.get_time_seconds(world)
        state = {'jumped': len(args) < 4}
        def tick(dt):
            try:
                now = unreal.GameplayStatics.get_time_seconds(world) - start
                if now > args[2]:
                    unreal.unregister_slate_post_tick_callback(state['handle'])
                    return
                pawn.add_movement_input(unreal.Vector(args[0], args[1], 0), 1, True)
                if not state['jumped'] and now >= args[3]:
                    pawn.jump()
                    state['jumped'] = True
            except Exception:
                unreal.unregister_slate_post_tick_callback(state['handle'])
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
        return json.dumps({'driving': args})
    if operation.startswith('pie_find:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        key = operation.split(':', 1)[1]
        return json.dumps([[a.get_actor_label(), [round(v) for v in a.get_actor_location().to_tuple()]]
                           for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if key in a.get_actor_label()][:8])
    if operation.startswith('pie_hold_dilation:'):
        # Holds global time dilation every frame (so hit-stop cannot reset it); 0 releases it back to 1.
        value = float(operation.split(':')[1])
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        handle = getattr(unreal, '_physis_dilation_handle', None)
        if handle is not None:
            unreal.unregister_slate_post_tick_callback(handle)
            unreal._physis_dilation_handle = None
        if value <= 0:
            unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
            return json.dumps({'dilation': 1.0})
        def tick(dt):
            try:
                unreal.GameplayStatics.set_global_time_dilation(world, value)
            except Exception:
                unreal.unregister_slate_post_tick_callback(unreal._physis_dilation_handle)
                unreal._physis_dilation_handle = None
        unreal._physis_dilation_handle = unreal.register_slate_post_tick_callback(tick)
        return json.dumps({'dilation': value})
    if operation == 'quit_editor':
        unreal.SystemLibrary.quit_editor()
        return json.dumps({'quitting': True})
    if operation.startswith('pie_menu:'):
        # pie_menu:PAGE opens the pause menu on a page (0 Logbook, 1 Abilities, 2 Quests, 3 Settings).
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pawn.call_method('PhysisMenu', (int(operation.split(':')[1]),))
        return json.dumps({'menu': int(operation.split(':')[1])})
    if operation.startswith('pie_set:'):
        name, value = operation.split(':', 1)[1].split('=', 1)
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        old = pawn.get_editor_property(name)
        try:
            pawn.set_editor_property(name, type(old)(value))
        except Exception:
            setattr(pawn, name, type(old)(value))
        return json.dumps({name: str(pawn.get_editor_property(name))})
    if operation == 'dirty_packages':
        # Read-only: which maps and assets hold unsaved changes.
        lib = unreal.EditorLoadingAndSavingUtils
        names = lambda packages: [p.get_name() for p in packages]
        return json.dumps({'maps': names(lib.get_dirty_map_packages()), 'content': names(lib.get_dirty_content_packages()),
                           'level': unreal.EditorLevelLibrary.get_editor_world().get_name()})
    if operation == 'rename_divinity_sense':
        # Scan Visor -> Divinity Sense (author, 2026-11-07) in the open level's placed texts. Wrapped fields are unwrapped,
        # renamed and wrapped again as set_props does, which equals placing the new source text. Saves the level.
        pairs = (('Open the Scan Visor', 'Use Divinity Sense'), ('with the Scan Visor', 'with Divinity Sense'),
                 ('the Scan Visor', 'Divinity Sense'), ('Scan Visor', 'Divinity Sense'))
        wrapped = ('Message', 'Done', 'Denied', 'Objective', 'ScanText', 'NextGoal')
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            for key in wrapped + ('ScanTitle', 'Title'):
                try:
                    value = actor.get_editor_property(key)
                except Exception:
                    continue
                if not isinstance(value, str) or 'visor' not in value.lower():
                    continue
                text = value.replace('~', ' ') if key in wrapped else value
                for old, new in pairs:
                    text = text.replace(old, new)
                if key in wrapped:
                    text = wrap_text(text)
                if text != value:
                    actor.set_editor_property(key, text)
                    rows.append([actor.get_actor_label(), key, text])
        saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level() if rows else False
        return json.dumps({'level': unreal.EditorLevelLibrary.get_editor_world().get_name(), 'changed': rows, 'saved': saved})
    if operation.startswith('retext_scans:'):
        # retext_scans:Title|Title gives every placed scan tag with one of these ScanTitles the current physis_lore text
        # (wrapped as the scenario does), so a lore edit reaches the open level without re-placing the scenario, then
        # saves the level if anything changed. Added 2026-11-09 for 'AL Drone' and 'Divinity Crystal' (no automatic
        # parry by default; drones drop Divinity only often). Their voices: voice_one.
        titles = operation.split(':', 1)[1].split('|')
        texts = {row[1]: row[2] for row in all_entries()}
        missing = [t for t in titles if t not in texts]
        if missing:
            raise ValueError('Not in physis_lore: %s' % missing)
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            try:
                title = actor.get_editor_property('ScanTitle')
            except Exception:
                continue
            if title in titles:
                text = wrap_text(texts[title])
                if actor.get_editor_property('ScanText') != text:
                    actor.set_editor_property('ScanText', text)
                    rows.append(actor.get_actor_label())
        saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level() if rows else False
        return json.dumps({'level': unreal.EditorLevelLibrary.get_editor_world().get_name(), 'changed': rows, 'saved': saved})
    if operation.startswith('voice_one:'):
        # voice_one:S_VO_Name re-imports one Art/Audio/Voice wav over its SoundWave (pause_assets imports every voice).
        name = operation.split(':', 1)[1]
        path = ROOT / 'Art/Audio/Voice' / (name + '.wav')
        if not path.exists():
            raise ValueError('No such voice: ' + str(path))
        game.import_file(str(path), '/Game/Audio/Voice')
        sound = unreal.load_asset('/Game/Audio/Voice/' + name)
        return json.dumps({'voice': name, 'seconds': round(sound.get_editor_property('duration'), 2)})
    if operation == 'drone_rooms':
        # Gives every placed station drone its room box from its RoomId (station_room_box), then saves the station,
        # so drones already in L_BattleStation get it without re-placing the scenario.
        world = unreal.EditorLevelLibrary.get_editor_world()
        if world.get_name() != 'L_BattleStation':
            raise ValueError('Open L_BattleStation first (open level: %s)' % world.get_name())
        rows = {}
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if 'BP_TrainingDrone' in actor.get_class().get_name():
                room = actor.get_editor_property('RoomId')
                props = room_box_props(room)
                for key, value in props.items():
                    actor.set_editor_property(key, value)
                rows[actor.get_actor_label()] = [room, list(station_room_box(room) or [])]
        saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        return json.dumps({'drones': rows, 'saved': saved})
    if operation == 'pie_room_drones':
        # Read-only: each drone in Play with its room, whether Physis counts as inside it, health and position.
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        rows = {}
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if 'BP_TrainingDrone' in actor.get_class().get_name():
                at = actor.get_actor_location()
                rows[actor.get_actor_label()] = [actor.get_editor_property('RoomId'), bool(actor.get_editor_property('InRoom')),
                                                 actor.get_editor_property('Health'), round(at.x), round(at.y), round(at.z)]
        return json.dumps({'world': world.get_name(), 'drones': rows})
    if operation.startswith('pie_trace:'):
        # pie_trace:x,y,z;x,y,z... runs the station stuck rule's sunk trace (70 cm down onto each point) in Play.
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        rows = []
        for point in operation.split(':', 1)[1].split(';'):
            x, y, z = [float(v) for v in point.split(',')]
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z + 70), unreal.Vector(x, y, z), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
            if hit:
                info = hit.to_tuple()
                actor = info[9] if len(info) > 9 else None
                rows.append([point, actor.get_actor_label() if actor else None, round(info[4].z) if info[4] else None, bool(info[1])])
            else:
                rows.append([point, None])
        return json.dumps({'traces': rows})
    if operation.startswith('pie_drone_watch:'):
        # Read-only, for one RoomId in Play: each drone's position, health, Blocked, the stuck rule's sunk trace
        # (70 cm down onto it), the floor below it and the nearest other drone.
        room = int(operation.split(':', 1)[1])
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        everyone = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if 'BP_TrainingDrone' in a.get_class().get_name()]
        rows = {}
        for actor in everyone:
            if actor.get_editor_property('RoomId') != room:
                continue
            at = actor.get_actor_location()
            def probe(start, end):
                hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [actor], unreal.DrawDebugTrace.NONE, True)
                if not hit:
                    return None
                info = hit.to_tuple()
                other = info[9] if len(info) > 9 else None
                return [other.get_actor_label() if other else None, round(info[4].z) if info[4] else None]
            nearest = min([round((a.get_actor_location() - at).length()) for a in everyone if a != actor] or [0])
            rows[actor.get_actor_label().replace('Scene Drone ', '')] = {
                'at': [round(at.x), round(at.y), round(at.z)], 'hp': actor.get_editor_property('Health'),
                'blocked': bool(actor.get_editor_property('Blocked')),
                'sunk': probe(at + unreal.Vector(0, 0, 70), at), 'below': probe(at, at - unreal.Vector(0, 0, 60)), 'near': nearest}
        return json.dumps({'t': round(unreal.GameplayStatics.get_time_seconds(world), 2), 'drones': rows})
    if operation == 'pie_world':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        return json.dumps({'pie': [w.get_name() for w in worlds]})
    if operation.startswith('pie_call:'):
        # pie_call:PhysisFinish calls a pawn function that takes no arguments.
        name = operation.split(':', 1)[1]
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        unreal.GameplayStatics.get_player_pawn(world, 0).call_method(name)
        return json.dumps({'called': name})
    if operation.startswith('pie_setting:'):
        # pie_setting:ROW,DELTA presses left (-1) or right (+1) on a pause-menu Settings row (2 = Graphics Quality).
        row, delta = operation.split(':', 1)[1].split(',')
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pawn.call_method('PhysisSetting', (int(row), float(delta)))
        return json.dumps({n: str(pawn.get_editor_property(n)) for n in ('Quality', 'QualityWanted', 'QualityCap', 'MenuNote')})
    if operation.startswith('pie_method:'):
        # pie_method:PhysisGive,,room2, calls a pawn function with one argument.
        name, arg = operation.split(':', 1)[1].split(',', 1)
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pawn.call_method(name, (arg,))
        return json.dumps({'called': name})
    if operation.startswith('pie_get:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        return json.dumps({n: str(pawn.get_editor_property(n)) for n in operation.split(':', 1)[1].split(',')})
    if operation.startswith('pie_gate:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if actor.get_actor_label() == operation.split(':', 1)[1]:
                return json.dumps({'opened': actor.get_editor_property('Opened'), 'need': actor.get_editor_property('Need'), 'rise': actor.get_editor_property('Rise'),
                                   'z': round(actor.get_actor_location().z), 'scale_z': round(actor.get_actor_scale3d().z, 2)})
        return json.dumps({'missing': True})
    if operation.startswith('pie_cmd:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        unreal.SystemLibrary.execute_console_command(world, operation.split(':', 1)[1])
        return json.dumps({'ran': operation.split(':', 1)[1]})
    if operation.startswith('fixed_fps:'):
        # A fixed Play step cannot be set at run time in the editor. Python cannot reach UEngine's bUseFixedFrameRate
        # (set_editor_property 'use_fixed_frame_rate': "Failed to find property"), and the editor refuses console
        # SET ("Set commands not allowed in the editor", Center session 2026-11-09). Until 2026-11-08 this op raised
        # on the first, so no Play test before then ran fixed: in the background the editor drops to about 3 fps.
        # For a fixed step, launch the editor with -UseFixedTimeStep -FPS=30: every frame then advances game time
        # 1/30 s, however slowly it really runs (background throttling then slows the test, not the step). This op
        # only says so, so old test scripts keep running.
        return json.dumps({'fixed': None, 'how': 'launch the editor with -UseFixedTimeStep -FPS=30; it cannot change at run time'})
    if operation.startswith('mesh_slots:'):
        mesh = unreal.load_asset(operation.split(':', 1)[1])
        slots = [[m.get_editor_property('material_slot_name').__str__(), m.get_editor_property('material_interface').get_name() if m.get_editor_property('material_interface') else None]
                 for m in mesh.get_editor_property('static_materials')]
        box = mesh.get_bounding_box()
        return json.dumps({'slots': slots, 'min': [round(v, 1) for v in box.min.to_tuple()], 'max': [round(v, 1) for v in box.max.to_tuple()],
                           'sections': mesh.get_num_sections(0)})
    if operation.startswith('mesh_profile:'):
        # Width of a mesh in X and Z, sliced along its long Y axis.
        path, step = operation.split(':', 1)[1].rsplit(',', 1)
        mesh = unreal.load_asset(path)
        desc = mesh.get_static_mesh_description(0)
        bins = {}
        for i in range(desc.get_vertex_count()):
            v = desc.get_vertex_position(unreal.VertexID(i))
            k = int(v.y // float(step))
            lo, hi = bins.get(k, ([1e9, 1e9], [-1e9, -1e9]))
            bins[k] = ([min(lo[0], v.x), min(lo[1], v.z)], [max(hi[0], v.x), max(hi[1], v.z)])
        return json.dumps([[k * float(step), round(hi[0] - lo[0], 1), round(hi[1] - lo[1], 1), round(lo[0], 1), round(hi[0], 1)] for k, (lo, hi) in sorted(bins.items())])
    if operation == 'weapon_assets':
        return json.dumps(weapon_assets())
    if operation == 'charge_orb_assets':
        return json.dumps(charge_orb_assets())
    if operation.startswith('sfx_import:'):
        # sfx_import:S_A,S_B imports Art/Audio/Game wavs into /Game/Audio.
        made = []
        for name in operation.split(':', 1)[1].split(','):
            game.import_file(str(ROOT / 'Art/Audio/Game' / (name + '.wav')), '/Game/Audio')
            asset = unreal.load_asset('/Game/Audio/' + name)
            game.save(asset)
            made.append(asset.get_name())
        return json.dumps({'imported': made})
    if operation.startswith('room_actors:'):
        x1, x2, y1, y2 = [float(v) for v in operation.split(':')[1].split(',')]
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            at = actor.get_actor_location()
            if x1 <= at.x <= x2 and y1 <= at.y <= y2:
                o, e = actor.get_actor_bounds(False)
                rows.append([actor.get_actor_label(), [round(at.x), round(at.y), round(at.z)], [round(e.x), round(e.y), round(e.z)]])
        return json.dumps(rows)
    if operation.startswith('area_info:'):
        x1, x2, y1, y2 = [float(v) for v in operation.split(':')[1].split(',')]
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            at = actor.get_actor_location()
            if x1 <= at.x <= x2 and y1 <= at.y <= y2 and isinstance(actor, unreal.StaticMeshActor):
                part = actor.static_mesh_component
                mesh = part.get_editor_property('static_mesh')
                if mesh and not actor.get_actor_label().startswith('Kit '):
                    rows.append([actor.get_actor_label(), mesh.get_name(), part.get_material(0).get_name() if part.get_material(0) else None, [round(v) for v in at.to_tuple()], [round(v, 1) for v in actor.get_actor_scale3d().to_tuple()]])
        return json.dumps(rows)
    if operation.startswith('pie_hits:'):
        pitch = float(operation.split(':')[1])
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        camera = next(c for c in pawn.get_components_by_class(unreal.CameraComponent))
        eye = camera.get_world_location()
        rows = []
        for yaw_off in (-30, -15, 0, 15, 30):
            rot = camera.get_world_rotation()
            rot = unreal.Rotator(0, rot.pitch, rot.yaw + yaw_off)
            end = eye + rot.get_forward_vector() * 3000
            hit = unreal.SystemLibrary.line_trace_single(world, eye, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn], unreal.DrawDebugTrace.NONE, True)
            if hit:
                info = hit.to_tuple()
                actor = info[9] if len(info) > 9 else None
                part = info[10] if len(info) > 10 else None
                rows.append([yaw_off, actor.get_actor_label() if actor else None, part.get_material(0).get_name() if part and part.get_material(0) else None, [round(v) for v in info[4].to_tuple()]])
        return json.dumps(rows)
    if operation == 'scan_lines':
        rows = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if actor.get_class().get_name() == 'BP_ScanTarget_C':
                text = actor.get_editor_property('ScanText')
                rows.append(max(len(line) for line in text.split('~')))
        return json.dumps({'targets': len(rows), 'longest_line': max(rows), 'over_70': sum(1 for r in rows if r > 70)})
    if operation == 'overlaps':
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        props = [a for a in actors if a.get_actor_label().startswith(('Kit Column', 'Kit Console', 'Kit Terminal', 'Kit Crate', 'Kit WeaponRack', 'Puzzle ', 'Scene Wing Pillar', 'Scene Wing Table'))]
        targets = [a for a in actors if a.get_class().get_name() in ('BP_Switch_C', 'BP_ScanTarget_C') or a.get_actor_label().startswith(('Scan ', 'Kit Terminal', 'Kit Console', 'Prop '))]
        rows = []
        for t in targets:
            p = t.get_actor_location()
            for a in props:
                if a is t:
                    continue
                q = a.get_actor_location()
                if abs(p.x - q.x) < 170 and abs(p.y - q.y) < 170:
                    rows.append([t.get_actor_label(), a.get_actor_label(), [round(v) for v in p.to_tuple()], [round(v) for v in q.to_tuple()]])
        return json.dumps(rows)
    if operation == 'tag_hull':
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if actor.get_actor_label() == 'Cine Hull':
                actor.tags = ['CineOnly']
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.EditorLoadingAndSavingUtils.save_map(world, game.LEVEL)
        return json.dumps({'tagged': True})
    if operation == 'pie_state':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        at = pawn.get_actor_location()
        return json.dumps({'flags': pawn.get_editor_property('Flags'), 'fuses': pawn.get_editor_property('Fuses'), 'skill': pawn.get_editor_property('SkillLevel'), 'hp': pawn.get_editor_property('PhysisHealth'), 'seq': pawn.get_editor_property('SeqStep'),
                           'goal': pawn.get_editor_property('Objective'), 'at': [round(at.x), round(at.y), round(at.z)]})
    if operation.startswith('pie_scan:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        hits = 0
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.load_asset(game.BLUEPRINTS + '/BP_ScanTarget').generated_class()):
            if operation.split(':')[1] in actor.get_editor_property('ScanText'):
                actor.set_editor_property('ScanDone', True)
                hits += 1
        return json.dumps({'scanned': hits})
    if operation == 'pie_where_boss':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if 'BP_TrainingDrone' in actor.get_class().get_name() and actor.get_editor_property('Boss'):
                return json.dumps([round(v) for v in actor.get_actor_location().to_tuple()])
        return json.dumps(None)
    if operation.startswith('pie_boss:'):
        # pie_boss:front or pie_boss:back puts Physis in front of / behind the boss and lands one hit.
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if 'BP_TrainingDrone' in actor.get_class().get_name() and actor.get_editor_property('Boss'):
                at, ahead = actor.get_actor_location(), actor.get_actor_forward_vector()
                side = 1 if operation.endswith('front') else -1
                pawn.set_actor_location(unreal.Vector(at.x + ahead.x * 400 * side, at.y + ahead.y * 400 * side, 110), False, True)
                actor.call_method('TakeHit', (1,))
                return json.dumps({'health': actor.get_editor_property('Health'), 'eye': actor.get_editor_property('EyeHits'),
                                   'stun_until': round(actor.get_editor_property('StunUntil'), 1), 'now': round(unreal.GameplayStatics.get_time_seconds(world), 1)})
        return json.dumps({'boss': None})
    if operation.startswith('pie_kill:'):
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        hits = 0
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if 'BP_TrainingDrone' in actor.get_class().get_name() and actor.get_editor_property('RoomId') == int(operation.split(':')[1]):
                actor.call_method('TakeHit', (99,))
                hits += 1
        return json.dumps({'killed': hits})
    if operation == 'pie_boss_gun':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if 'BP_TrainingDrone' in actor.get_class().get_name() and actor.get_editor_property('Boss'):
                pawn.set_editor_property('GunHit', True)
                actor.call_method('TakeHit', (1,))
                gun = actor.get_editor_property('Health')
                pawn.set_editor_property('GunHit', False)
                actor.call_method('TakeHit', (3,))
                return json.dumps({'after_gun': gun, 'after_sword': actor.get_editor_property('Health')})
        return json.dumps({'boss': None})
    if operation == 'scenario_place':
        return json.dumps(scenario_place())
    if operation == 'scenario_assets':
        return json.dumps(scenario_assets())
    if operation == 'battle_assets':
        return json.dumps(battle_assets())
    if operation.startswith('keep_drones:'):
        keep = int(operation.split(':')[1])
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        gone = []
        for actor in subsystem.get_all_level_actors():
            label = actor.get_actor_label()
            if label.startswith(('Drone ', 'Scan Drone ')) and int(label.split()[-1]) > keep:
                gone.append(label)
                subsystem.destroy_actor(actor)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.EditorLoadingAndSavingUtils.save_map(world, game.LEVEL)
        return json.dumps(sorted(gone))
    if operation == 'forge':
        return json.dumps(forge_clips())
    if operation == 'anim_probe':
        path = '/Game/Characters/Physis/Animations/Katana'
        names = [str(a.asset_name) for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(path, False)]
        clip = unreal.load_asset(path + '/Physis_AS_HK_Slash5')
        ctrl = clip.get_editor_property('controller') if hasattr(clip, 'get_editor_property') else None
        model = clip.get_editor_property('data_model_interface') if False else None
        lib_a = unreal.AnimationLibrary
        tracks = lib_a.get_animation_track_names(clip)
        ctrl = clip.get_editor_property('controller') if 'controller' in dir(clip) else None
        return json.dumps({'names': names[:4], 'length': clip.get_play_length(), 'frames': lib_a.get_num_frames(clip), 'tracks': [str(t) for t in tracks][:5], 'count': len(tracks), 'lib': [x for x in dir(lib_a) if not x.startswith('_') and ('frame' in x or 'bone' in x or 'raw' in x or 'track' in x)][:40],
                           'seq': [x for x in dir(clip) if 'control' in x or 'data_model' in x or 'model' in x], 'has': [x for x in dir(unreal) if 'AnimationData' in x or 'AnimDataController' in x or 'AnimDataModel' in x], 'root': clip.get_editor_property('enable_root_motion'), 'skel': clip.get_editor_property('skeleton').get_name()})
    if operation == 'run_fast':
        bp = unreal.load_asset(game.CHARACTER)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        cdo = unreal.get_default_object(bp.generated_class())
        cdo.get_editor_property('character_movement').set_editor_property('max_walk_speed', 750)
        game.save(bp)
        # The run clips top out well below 1000, so they play faster to keep the feet planted.
        space = unreal.load_asset('/Game/Characters/Physis/Animations/AnimBP/Physis_BS_Idle_Walk_Run')
        samples = space.get_editor_property('sample_data')
        rows = []
        for sample in samples:
            clip = sample.get_editor_property('animation')
            name = clip.get_name() if clip else ''
            if 'Jog_Fwd' in name and 'Bwd' not in name:
                sample.set_editor_property('rate_scale', 1.35)
            elif 'Run' in name or 'Jog' in name:
                sample.set_editor_property('rate_scale', 1.0)
                rows.append([name, round(sample.get_editor_property('sample_value').y)])
        space.set_editor_property('sample_data', samples)
        game.save(space)
        return json.dumps({'run': cdo.get_editor_property('character_movement').get_editor_property('max_walk_speed'), 'rows': rows, 'y': sorted({round(s.get_editor_property('sample_value').y) for s in samples})})
    if operation == 'run_info':
        space = unreal.load_asset('/Game/Characters/Physis/Animations/AnimBP/Physis_BS_Idle_Walk_Run')
        rows = [[str(x.get_editor_property('animation').get_name()) if x.get_editor_property('animation') else None, str(x.get_editor_property('sample_value')), x.get_editor_property('rate_scale')] for x in space.get_editor_property('sample_data')]
        axes = [str(a) for a in space.get_editor_property('blend_parameters')] if False else []
        return json.dumps({'rows': rows})
    if operation == 'fx_assets':
        return json.dumps(fx_assets())
    if operation == 'pie_open':
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        unreal.GameplayStatics.open_level(world, 'L_BattleStation')
        return json.dumps({'opened': True})
    if operation == 'menu_mode':
        mode = unreal.load_asset(game.BLUEPRINTS + '/BP_MenuGameMode')
        unreal.BlueprintEditorLibrary.compile_blueprint(mode)
        cdo = unreal.get_default_object(mode.generated_class())
        cdo.set_editor_property('hud_class', unreal.load_asset(game.BLUEPRINTS + '/BP_MenuHUD').generated_class())
        cdo.set_editor_property('default_pawn_class', None)
        game.save(mode)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        world.get_world_settings().set_editor_property('default_game_mode', mode.generated_class())
        unreal.EditorLoadingAndSavingUtils.save_map(world, '/Game/Levels/L_MainMenu')
        return json.dumps({'hud': cdo.get_editor_property('hud_class').get_name(), 'world': world.get_name()})
    if operation == 'menu_assets':
        return json.dumps(menu_assets())
    if operation.startswith('pie_go:'):
        x, y, z = [float(v) for v in operation.split(':')[1].split(',')]
        world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        pawn.set_actor_location(unreal.Vector(x, y, z), False, False)
        return json.dumps({'at': [x, y, z]})
    if operation == 'doors':
        bp = unreal.load_asset(game.BLUEPRINTS + '/BP_StationDoor')
        look = unreal.load_asset(MAT + '/MI_Hazard')
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            part = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(part, unreal.StaticMeshComponent):
                part.set_material(0, look)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for actor in subsystem.get_all_level_actors():
            if actor.get_actor_label().startswith('Door '):
                for part in actor.get_components_by_class(unreal.StaticMeshComponent):
                    part.set_material(0, look)
        unreal.EditorLoadingAndSavingUtils.save_map(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(), game.LEVEL)
        return json.dumps({'doors': True})
    if operation == 'audit':
        rows = {}
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for actor in subsystem.get_all_level_actors():
            for part in actor.get_components_by_class(unreal.StaticMeshComponent):
                mesh = part.get_editor_property('static_mesh')
                for index in range(part.get_num_materials()):
                    look = part.get_material(index)
                    key = '%s | %s | %s' % (actor.get_class().get_name()[:22], mesh.get_name() if mesh else None, look.get_name() if look else None)
                    rows[key] = rows.get(key, 0) + 1
        keep = {k: v for k, v in rows.items() if not k.split(' | ')[2].startswith('MI_') or 'Item' in k or 'Hull' == k.split(' | ')[2][3:]}
        return json.dumps({'total': len(rows), 'suspect': keep, 'other': sorted({k.split(' | ')[1] + '/' + k.split(' | ')[2] for k in rows if 'Kit' not in k.split(' | ')[1]})[:60]})
    if operation == 'save_all':
        return json.dumps(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
    if operation.startswith('save_asset:'):
        # Saves one asset and nothing else (save_all also saves every open map), e.g.
        # save_asset:/Game/Characters/Physis/Blueprints/BP_Physis. Maps are refused.
        path = operation.split(':', 1)[1].strip()
        if not path.startswith('/Game/') or not unreal.EditorAssetLibrary.does_asset_exist(path):
            raise ValueError('No such asset: ' + path)
        data = unreal.EditorAssetLibrary.find_asset_data(path)
        kind = str(data.asset_class_path.asset_name) if hasattr(data, 'asset_class_path') else str(data.asset_class)
        if kind == 'World':
            raise ValueError('save_asset does not save maps: ' + path)
        return json.dumps({'asset': path, 'class': kind, 'saved': unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)})
    if operation.startswith('ui_textures:'):
        # ui_textures:T_Pad_DL,T_Pad_DR imports just those Art/UI images with play:ui_import's texture settings
        # (play:ui_import reimports every UI image and every gameplay mesh).
        root = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
        done = []
        for name in operation.split(':', 1)[1].split(','):
            png = root / 'Art/UI' / (name.strip() + '.png')
            if not name.strip().startswith('T_') or not png.exists():
                raise ValueError('No such UI image: ' + str(png))
            game.import_file(str(png), '/Game/UI')
            texture = unreal.load_asset('/Game/UI/' + png.stem)
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
            texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
            texture.set_editor_property('never_stream', True)
            texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
            texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
            game.save(texture)
            done.append(png.stem)
        return json.dumps({'imported': done})
    if operation == 'probe':
        rows = {}
        for name in ('/Game/Art/Kit/MI_WallPanel_Wall', MAT + '/MI_Deck', MAT + '/MI_Hazard', '/Game/Gameplay/MI_Drone'):
            item = unreal.load_asset(name)
            rows[name] = [[str(v.parameter_info.name), v.parameter_value.get_name() if v.parameter_value else None, v.parameter_value.blueprint_get_size_x() if v.parameter_value else 0, str(v.parameter_value.get_editor_property('compression_settings')) if v.parameter_value else '', v.parameter_value.get_editor_property('srgb') if v.parameter_value else ''] for v in item.get_editor_property('texture_parameter_values')] if item else None
        mesh = unreal.load_asset(KIT + '/SM_Kit_WallPanel')
        rows['wall'] = [m.get_editor_property('material_interface').get_name() if m.get_editor_property('material_interface') else None for m in mesh.get_editor_property('static_materials')]
        return json.dumps(rows)
    if operation == 'sharpen':
        return json.dumps(sharpen())
    if operation == 'scan_props':
        return json.dumps(scan_props())
    if operation == 'drone':
        return json.dumps(drone())
    if operation == 'surfaces':
        return json.dumps(import_surfaces())
    if operation == 'kit':
        return json.dumps(import_kit())
    if operation == 'cinema':
        return json.dumps(import_cinema())
    if operation == 'props':
        return json.dumps(import_props())
    if operation == 'dress':
        return json.dumps(dress())
    if operation == 'mood':
        return json.dumps(mood())
    raise ValueError(operation)
