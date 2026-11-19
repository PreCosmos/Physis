"""The generated elemental monsters in the editor (models: Tools/image_to_3d.py; rigs: Tools/build_physis_monsters.py).

  import physis_monster_models as mm
  mm.import_all()             # textures, material, static and skinned meshes, animations (GUI editor only)

Assets go beside the other animals (/Game/Arche/Meshes/SM_MN_<Name>, /Game/Arche/Rigged/SK_MN_<Name> and
A_MN_<Name>_Swim / _Strike), because physis_fauna.Placer finds an animal's skinned mesh and clips there by name.
Textures and materials: /Game/Monsters.

Each monster has one material slot, 'Monster', and one instance MI_MN_<Name> of M_MN_Monster: the model's own colour
and roughness/metal pictures, and a rim of its element's colour (Glow, GlowPower) that breathes slowly.
"""
import pathlib

import unreal

import physis_arche_tools as arche
import physis_conclave_tools as cn
import physis_gameplay_tools as game

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
ART = ROOT / 'Art/Meshes/Monsters'
FOLDER = '/Game/Monsters'
MESHES, RIGGED = '/Game/Arche/Meshes', '/Game/Arche/Rigged'
# name: (rim colour, rim strength, lift of its colour picture)
LOOKS = {'PyreLion': ((1.0, 0.32, 0.04), 0.8, 1.15), 'StormDrake': ((0.55, 0.75, 1.0), 1.0, 1.3), 'RimeMammoth': ((0.6, 0.85, 1.0), 0.8, 1.2),
         'GloomToad': ((0.55, 0.1, 0.9), 0.3, 0.4),   # the generated toad is violet-blue; the brief's is coal-black
         'GaleMantis': ((0.5, 0.9, 1.0), 0.6, 1.1), 'Seraph': ((1.0, 0.9, 0.6), 1.2, 1.1), 'NightFiend': ((0.6, 0.1, 1.0), 0.6, 1.2)}
mel = unreal.MaterialEditingLibrary
library = unreal.EditorAssetLibrary


def texture(name, colour):
    game.import_file(str(ART / (name + '.png')), FOLDER)
    tex = unreal.load_asset(FOLDER + '/' + name)
    if tex:
        tex.set_editor_property('srgb', colour)
        if not colour:
            tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property('never_stream', True)   # few and always close: no blurred first sight
        game.save(tex)
    return tex


def master(any_colour, any_orm):
    path = FOLDER + '/M_MN_Monster'
    if library.does_asset_exist(path):   # rebuilt in place, so its instances keep their parent
        material = unreal.load_asset(path)
        mel.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_MN_Monster', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('used_with_skeletal_mesh', True)
    material.set_editor_property('two_sided', True)

    def node(kind, x, y):
        return mel.create_material_expression(material, kind, x, y)
    colour = node(unreal.MaterialExpressionTextureSampleParameter2D, -700, -200)
    colour.set_editor_property('parameter_name', 'Colour')
    colour.set_editor_property('texture', any_colour)
    orm = node(unreal.MaterialExpressionTextureSampleParameter2D, -700, 100)
    orm.set_editor_property('parameter_name', 'ORM')
    orm.set_editor_property('texture', any_orm)
    orm.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    glow = node(unreal.MaterialExpressionVectorParameter, -700, 400)
    glow.set_editor_property('parameter_name', 'Glow')
    glow.set_editor_property('default_value', unreal.LinearColor(1, 0.4, 0.1, 1))
    power = node(unreal.MaterialExpressionScalarParameter, -700, 600)
    power.set_editor_property('parameter_name', 'GlowPower')
    power.set_editor_property('default_value', 3.0)
    rim = node(unreal.MaterialExpressionFresnel, -700, 750)
    rim.set_editor_property('exponent', 3.0)
    rim.set_editor_property('base_reflect_fraction', 0.0)
    time = node(unreal.MaterialExpressionTime, -900, 900)
    wave = node(unreal.MaterialExpressionSine, -750, 900)
    wave.set_editor_property('period', 3.0)
    mel.connect_material_expressions(time, '', wave, '')
    breathe = node(unreal.MaterialExpressionLinearInterpolate, -550, 900)   # 0.65 .. 1 as the sine goes -1 .. 1
    half = node(unreal.MaterialExpressionConstantBiasScale, -650, 1000)
    half.set_editor_property('bias', 1.0)
    half.set_editor_property('scale', 0.5)
    mel.connect_material_expressions(wave, '', half, '')
    breathe.set_editor_property('const_a', 0.65)
    breathe.set_editor_property('const_b', 1.0)
    mel.connect_material_expressions(half, '', breathe, 'Alpha')
    a = node(unreal.MaterialExpressionMultiply, -400, 500)
    mel.connect_material_expressions(glow, '', a, 'A')
    mel.connect_material_expressions(power, '', a, 'B')
    b = node(unreal.MaterialExpressionMultiply, -250, 600)
    mel.connect_material_expressions(a, '', b, 'A')
    mel.connect_material_expressions(rim, '', b, 'B')
    c = node(unreal.MaterialExpressionMultiply, -100, 700)
    mel.connect_material_expressions(b, '', c, 'A')
    mel.connect_material_expressions(breathe, '', c, 'B')
    bright = node(unreal.MaterialExpressionScalarParameter, -500, -350)   # the generated pictures are dark: lifted per monster
    bright.set_editor_property('parameter_name', 'Bright')
    bright.set_editor_property('default_value', 1.0)
    lifted = node(unreal.MaterialExpressionMultiply, -300, -250)
    mel.connect_material_expressions(colour, 'RGB', lifted, 'A')
    mel.connect_material_expressions(bright, '', lifted, 'B')
    # the mesh's vertex colours (Tools/build_physis_monsters.py paint): RGB darkens parts of the picture (the lion's
    # mane), alpha marks what glows by itself (its eyes)
    paint = node(unreal.MaterialExpressionVertexColor, -500, -100)
    painted = node(unreal.MaterialExpressionMultiply, -150, -200)
    mel.connect_material_expressions(lifted, '', painted, 'A')
    mel.connect_material_expressions(paint, 'RGB', painted, 'B')
    mel.connect_material_property(painted, '', unreal.MaterialProperty.MP_BASE_COLOR)
    eye = node(unreal.MaterialExpressionVectorParameter, -500, 100)
    eye.set_editor_property('parameter_name', 'Eye')
    eye.set_editor_property('default_value', unreal.LinearColor(8.0, 2.6, 0.3, 1))
    lit = node(unreal.MaterialExpressionMultiply, -300, 150)
    mel.connect_material_expressions(eye, '', lit, 'A')
    mel.connect_material_expressions(paint, 'A', lit, 'B')
    both = node(unreal.MaterialExpressionAdd, 50, 650)
    mel.connect_material_expressions(c, '', both, 'A')
    mel.connect_material_expressions(lit, '', both, 'B')
    mel.connect_material_property(both, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(orm, 'G', unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(orm, 'B', unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(material)
    game.save(material)
    return material


def unseen():
    path = FOLDER + '/M_MN_Unseen'
    if library.does_asset_exist(path):
        return unreal.load_asset(path)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_MN_Unseen', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    nothing = mel.create_material_expression(material, unreal.MaterialExpressionConstant, -300, 0)
    nothing.set_editor_property('r', 0.0)
    mel.connect_material_property(nothing, '', unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(material)
    game.save(material)
    return material


def look(name):
    colour, orm = texture('T_MN_%s_D' % name, True), texture('T_MN_%s_ORM' % name, False)
    base = master(colour, orm)
    path = '%s/MI_MN_%s' % (FOLDER, name)
    instance = unreal.load_asset(path) if library.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'MI_MN_' + name, FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(instance, base)
    mel.set_material_instance_texture_parameter_value(instance, 'Colour', colour)
    mel.set_material_instance_texture_parameter_value(instance, 'ORM', orm)
    rgb, strength, lift = LOOKS[name]
    mel.set_material_instance_scalar_parameter_value(instance, 'Bright', lift)
    mel.set_material_instance_vector_parameter_value(instance, 'Glow', unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    mel.set_material_instance_scalar_parameter_value(instance, 'GlowPower', strength)
    mel.update_material_instance(instance)
    game.save(instance)
    return instance


def import_all(names=None):
    if not library.does_directory_exist(FOLDER):
        library.make_directory(FOLDER)
    report = {}
    looks = {name: look(name) for name in (names or LOOKS)}
    for name, material in looks.items():
        stem = 'SM_MN_' + name
        game.import_file(str(ART / (stem + '.fbx')), MESHES, cn.import_options())
        mesh = unreal.load_asset(MESHES + '/' + stem)
        if mesh:
            # The static copy is a coarse hull, kept for the enemy's bounds and collision. It must never be seen: the
            # placer hides it, but an editor capture drew it over the real skin as flat blocks (2026-11-17).
            for slot in range(len(mesh.get_editor_property('static_materials'))):
                mesh.set_material(slot, unseen())
            cn.collision(mesh, 'box')
            game.save(mesh)
        report[name] = {'static': bool(mesh)}
    rigs = arche.import_rigs(ART / 'Rigged', RIGGED)
    for name, material in looks.items():
        skinned = unreal.load_asset('%s/SK_MN_%s' % (RIGGED, name))
        if skinned:
            slots = list(skinned.get_editor_property('materials'))
            for slot in slots:
                slot.set_editor_property('material_interface', material)
            skinned.set_editor_property('materials', slots)
            # A generated model's texture is thousands of patches a few texels wide: full-precision coordinates.
            sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
            settings = sub.get_lod_build_settings(skinned, 0)
            settings.set_editor_property('use_full_precision_u_vs', True)
            settings.set_editor_property('recompute_normals', False)
            sub.set_lod_build_settings(skinned, 0, settings)
            game.save(skinned)
        report[name].update(skinned=rigs['meshes'].get('SK_MN_' + name), anims={k: v for k, v in rigs['anims'].items() if name in k})
    report['failed'] = rigs['failed']
    return report


# ---------------------------------------------------------------- the element's fire, mist and motes

# Author, 2026-11-17, of the first clouds of soft dots: "The particles seem like orange and blue blobs. We need some real
# fire and some icy mist." So each element wears two clouds (Tools/build_physis_motes.py makes the meshes):
#   fire   (author, 2026-11-17: "make the fires around the lion, not go up": the flames are short, do not rise, and sit
#          in a cloud a little larger than the body; the bolts are a third as thick as first drawn)
#          flames: sheets that stand upright, turn to the camera, and are cut to a licking flame by moving noise
#          (M_FX_Flame, on SM_FX_Puffs), and small sparks rising through them (M_FX_Motes, on SM_FX_Motes)
#   thunder  bolts: M_FX_Bolt, a jagged line drawn across a square that turns to the camera at a new angle each flash
#   ice    mist: large soft translucent puffs that sink and thin out (M_FX_Mist; it fades where it meets a surface,
#          and lies low, round the legs: two more numbers, the cloud's middle and height against the body's half
#          height), and small glinting crystals falling
# A square's corner is UV0, its two random numbers UV1. Rise is cm over a life (negative falls), Size cm, Speed lives
# a second. NOISE is value noise in three octaves, shared by the flame and the mist.
NOISE = """struct Field {
  float h(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
  float n(float2 p) { float2 i = floor(p); float2 f = frac(p); f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(h(i), h(i + float2(1, 0)), f.x), lerp(h(i + float2(0, 1)), h(i + float2(1, 1)), f.x), f.y); }
  float fbm(float2 p) { return 0.6 * n(p) + 0.3 * n(p * 2.1 + 7.0) + 0.1 * n(p * 4.3 + 13.0); }
} field;
"""
MOTE_PLACE = """float ph = frac(T * Speed * (0.6 + 0.8 * Seed.x) + Seed.y);
float3 right = normalize(cross(float3(0, 0, 1), Cam));
float3 up = cross(Cam, right);
float s = Size * (0.5 + Seed.x) * lerp(sin(3.14159 * ph), 1.0 - 0.85 * ph, Shrink);
float3 sway = float3(sin(T * 1.7 + Seed.y * 40.0), cos(T * 1.3 + Seed.x * 40.0), 0) * Sway * ph;
return float3(0, 0, 1) * Rise * ph + sway + (right * (UV.x - 0.5) + up * (UV.y - 0.5)) * s;"""
MOTE_LIGHT = """float ph = frac(T * Speed * (0.6 + 0.8 * Seed.x) + Seed.y);
float d = saturate(1.0 - 2.0 * length(UV - 0.5));
float a = d * d * d * sin(3.14159 * ph) * lerp(1.0, 0.5 + 0.5 * sin(T * 9.0 + Seed.x * 50.0), Twinkle);
return lerp(A, B, ph) * a * Bright;"""
FLAME_PLACE = """float ph = frac(T * Speed * (0.6 + 0.8 * Seed.x) + Seed.y);
float3 right = normalize(cross(float3(0, 0, 1), Cam));
float s = Size * (0.6 + 0.8 * Seed.x) * (0.7 + 0.3 * sin(3.14159 * ph));
float lean = sin(T * 2.3 + Seed.y * 30.0) * 0.12 * UV.y;
return float3(0, 0, 1) * (Rise * ph + (UV.y - 0.35) * s * 1.15) + right * ((UV.x - 0.5) + lean) * s;"""
FLAME_LIGHT = NOISE + """float ph = frac(T * Speed * (0.6 + 0.8 * Seed.x) + Seed.y);
float y = UV.y;
float t = T * (1.5 + Seed.x);
float wob = field.fbm(float2(UV.x * 2.0 + Seed.y * 20.0, y * 2.5 - t * 1.5)) - 0.5;
float x = (UV.x - 0.5) + wob * 0.4 * y;
float w = 0.40 * sqrt(saturate(1.0 - y)) * smoothstep(0.0, 0.18, y) + 0.02;
float body = saturate(1.0 - abs(x) / w);
float lick = field.fbm(float2(UV.x * 3.5 + Seed.x * 30.0, y * 3.0 - t * 2.6));
float v = body * saturate(1.3 - y * (0.5 + 1.1 * lick));
v = pow(v, 1.4) * (0.5 + 1.0 * lick) * sin(3.14159 * ph);
float3 c = lerp(B, A, saturate(v * 1.7));
c = lerp(c, float3(1.0, 0.93, 0.65), saturate(v * 2.4 - 1.1));
return c * v * Bright;"""
MIST_FADE = NOISE + """float ph = frac(T * Speed * (0.6 + 0.8 * Seed.x) + Seed.y);
float d = saturate(1.0 - 2.0 * length(UV - 0.5));
float wisp = field.fbm(UV * 3.0 + Seed * 20.0 + float2(T * 0.11, -T * 0.07));
return d * d * (3.0 - 2.0 * d) * saturate(wisp * 1.7 - 0.25) * sin(3.14159 * ph) * Bright;"""
BOLT_PLACE = """float k = floor(T * Speed * 10.0 + Seed.y * 100.0);
float a = (Seed.y + frac(k * 0.37)) * 6.2832;
float3 right = normalize(cross(float3(0, 0, 1), Cam));
float3 up = cross(Cam, right);
float3 r2 = right * cos(a) + up * sin(a);
float3 u2 = up * cos(a) - right * sin(a);
return (r2 * (UV.x - 0.5) + u2 * (UV.y - 0.5)) * Size * (0.6 + 0.8 * Seed.x);"""
BOLT_LIGHT = NOISE + """float k = floor(T * Speed * 10.0 + Seed.y * 100.0);
float on = step(1.0 - Twinkle, field.h(float2(k, Seed.x * 50.0)));
float y = UV.y;
float path = (field.n(float2(y * 5.0, k * 1.7 + Seed.x * 10.0)) - 0.5) * 0.55 + (field.n(float2(y * 15.0, k * 3.1 + 5.0)) - 0.5) * 0.2
           + (field.n(float2(y * 40.0, k * 5.3 + 9.0)) - 0.5) * 0.06;
float d = abs(UV.x - 0.5 - path * sin(3.14159 * y));
float core = saturate(1.0 - d / 0.003);
float glow = saturate(1.0 - d / 0.037);
float v = (core + glow * glow * glow * 0.45) * pow(sin(3.14159 * y), 0.4) * on;
return lerp(B, A, core) * v * Bright;"""
# material: (blend, the code that places a square, the code of its light, the code of its opacity or None)
FX_MATERIALS = {'M_FX_Motes': ('add', MOTE_PLACE, MOTE_LIGHT, None), 'M_FX_Flame': ('add', FLAME_PLACE, FLAME_LIGHT, None),
                'M_FX_Mist': ('mist', MOTE_PLACE, 'return A;', MIST_FADE), 'M_FX_Bolt': ('add', BOLT_PLACE, BOLT_LIGHT, None)}
# element: the clouds it wears, each (mesh, material, instance, numbers, colour A, colour B, size of the cloud against the body)
MOTES = {
    1: (('SM_FX_Puffs', 'M_FX_Flame', 'MI_FX_Flame', dict(Rise=0.0, Size=62.0, Speed=0.9, Bright=1.9), (1.0, 0.42, 0.04), (0.9, 0.06, 0.0), 1.05),
        ('SM_FX_Motes', 'M_FX_Motes', 'MI_FX_Motes_Fire', dict(Rise=45.0, Size=5.0, Speed=0.7, Sway=45.0, Shrink=1.0, Twinkle=0.5, Bright=10.0), (1.0, 0.55, 0.1), (1.0, 0.1, 0.0), 1.0)),
    2: (('SM_FX_Puffs', 'M_FX_Mist', 'MI_FX_Mist_Ice', dict(Rise=-60.0, Size=170.0, Speed=0.16, Sway=45.0, Shrink=0.0, Bright=0.34), (0.82, 0.93, 1.0), (0.82, 0.93, 1.0), 1.15, -0.45, 0.6),
        ('SM_FX_Motes', 'M_FX_Motes', 'MI_FX_Motes_Ice', dict(Rise=-140.0, Size=4.5, Speed=0.3, Sway=25.0, Shrink=0.0, Twinkle=1.0, Bright=7.0), (0.9, 0.98, 1.0), (0.5, 0.8, 1.0), 1.0)),
    # thunder (author, 2026-11-17, of the drake: "instead of misty ice put some thunders engulfing him"): forked bolts
    # that flash across the body, each a new shape ten times a second and lit about one time in six (Twinkle), and
    # quick blue-white sparks
    3: (('SM_FX_Puffs', 'M_FX_Bolt', 'MI_FX_Bolt', dict(Size=330.0, Speed=1.0, Twinkle=0.16, Bright=22.0), (0.95, 0.97, 1.0), (0.3, 0.5, 1.0), 0.75),
        ('SM_FX_Motes', 'M_FX_Motes', 'MI_FX_Motes_Thunder', dict(Rise=40.0, Size=4.0, Speed=1.6, Sway=60.0, Shrink=0.0, Twinkle=1.0, Bright=14.0), (0.9, 0.95, 1.0), (0.35, 0.55, 1.0), 1.0)),
    # wind: thin pale air that swirls wide and fast round the body, with dust caught in it
    4: (('SM_FX_Puffs', 'M_FX_Mist', 'MI_FX_Mist_Wind', dict(Rise=40.0, Size=150.0, Speed=0.5, Sway=170.0, Shrink=0.0, Bright=0.13), (0.9, 0.96, 1.0), (0.9, 0.96, 1.0), 1.1, 0.0, 1.0),
        ('SM_FX_Motes', 'M_FX_Motes', 'MI_FX_Motes_Wind', dict(Rise=30.0, Size=3.0, Speed=1.2, Sway=150.0, Shrink=0.0, Twinkle=0.4, Bright=5.0), (0.9, 1.0, 1.0), (0.6, 0.9, 1.0), 1.1)),
    # light: large soft warm glows that hang and breathe, and gold sparks rising slowly
    6: (('SM_FX_Puffs', 'M_FX_Motes', 'MI_FX_Glow_Light', dict(Rise=30.0, Size=75.0, Speed=0.25, Sway=15.0, Shrink=0.0, Twinkle=0.2, Bright=0.8), (1.0, 0.93, 0.7), (1.0, 0.8, 0.4), 1.0),
        ('SM_FX_Motes', 'M_FX_Motes', 'MI_FX_Motes_Light', dict(Rise=90.0, Size=5.0, Speed=0.4, Sway=20.0, Shrink=0.0, Twinkle=1.0, Bright=12.0), (1.0, 0.95, 0.75), (1.0, 0.75, 0.3), 1.0)),
    # dark (author, 2026-11-17: "a dark aura"): slow black-violet smoke that rises and thins, with violet embers in it
    5: (('SM_FX_Puffs', 'M_FX_Mist', 'MI_FX_Mist_Dark', dict(Rise=110.0, Size=190.0, Speed=0.22, Sway=40.0, Shrink=0.0, Bright=1.15), (0.02, 0.0, 0.055), (0.02, 0.0, 0.055), 1.0, -0.1, 1.0),
        ('SM_FX_Motes', 'M_FX_Motes', 'MI_FX_Motes_Dark', dict(Rise=120.0, Size=5.0, Speed=0.35, Sway=30.0, Shrink=0.0, Twinkle=0.8, Bright=9.0), (0.75, 0.2, 1.0), (0.3, 0.0, 0.8), 1.0)),
}
ALL_NUMBERS = ('Rise', 'Size', 'Speed', 'Sway', 'Shrink', 'Twinkle', 'Bright')


def fx_material(name):
    blend, place_code, light_code, fade_code = FX_MATERIALS[name]
    path = FOLDER + '/' + name
    if library.does_asset_exist(path):
        material = unreal.load_asset(path)
        mel.delete_all_material_expressions(material)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE if blend == 'add' else unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('two_sided', True)

    def node(kind, x, y, **props):
        made = mel.create_material_expression(material, kind, x, y)
        for key, value in props.items():
            made.set_editor_property(key, value)
        return made
    corner = node(unreal.MaterialExpressionTextureCoordinate, -1200, 0, coordinate_index=0)
    seed = node(unreal.MaterialExpressionTextureCoordinate, -1200, 100, coordinate_index=1)
    time = node(unreal.MaterialExpressionTime, -1200, 200)
    # towards the camera, worked out from positions: the camera vector node does not exist in a vertex shader
    eye = node(unreal.MaterialExpressionCameraPositionWS, -1500, 250)
    here = node(unreal.MaterialExpressionWorldPosition, -1500, 350)
    apart = node(unreal.MaterialExpressionSubtract, -1350, 300)
    mel.connect_material_expressions(eye, '', apart, 'A')
    mel.connect_material_expressions(here, '', apart, 'B')
    cam = node(unreal.MaterialExpressionNormalize, -1200, 300)
    mel.connect_material_expressions(apart, '', cam, '')
    scalars = {key: node(unreal.MaterialExpressionScalarParameter, -1200, 400 + 90 * k, parameter_name=key, default_value=1.0) for k, key in enumerate(ALL_NUMBERS)}
    colours = {key: node(unreal.MaterialExpressionVectorParameter, -1200, 1100 + 200 * k, parameter_name=key, default_value=unreal.LinearColor(1, 1, 1, 1))
               for k, key in enumerate(('A', 'B'))}
    sources = dict(scalars, UV=corner, Seed=seed, T=time, Cam=cam, **colours)

    def custom(code, y, kind):
        import re
        names = [key for key in sources if re.search(r'\b%s\b' % key, code.replace(NOISE, ''))]
        made = node(unreal.MaterialExpressionCustom, -500, y, output_type=kind, code=code)
        inputs = []
        for key in names:
            entry = unreal.CustomInput()
            entry.set_editor_property('input_name', key)
            inputs.append(entry)
        made.set_editor_property('inputs', inputs)
        for key in names:
            mel.connect_material_expressions(sources[key], '', made, key)
        return made
    three, one = unreal.CustomMaterialOutputType.CMOT_FLOAT3, unreal.CustomMaterialOutputType.CMOT_FLOAT1
    mel.connect_material_property(custom(place_code, 0, three), '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.connect_material_property(custom(light_code, 500, three), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if fade_code:
        soft = node(unreal.MaterialExpressionDepthFade, -250, 1000, fade_distance_default=70.0)   # no hard line at the ground
        mel.connect_material_expressions(custom(fade_code, 1000, one), '', soft, 'Opacity')
        mel.connect_material_property(soft, '', unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(material)
    game.save(material)
    return material


def import_fx():
    """The two clouds' meshes, the three materials and every element's instances."""
    report = {'meshes': {}, 'instances': []}
    for stem in ('SM_FX_Motes', 'SM_FX_Puffs'):
        game.import_file(str(ART / (stem + '.fbx')), FOLDER, cn.import_options())
        mesh = unreal.load_asset(FOLDER + '/' + stem)
        report['meshes'][stem] = mesh.get_num_triangles(0) if mesh else None
    masters = {name: fx_material(name) for name in FX_MATERIALS}
    for clouds in MOTES.values():
        for _, parent, name, values, a, b in (row[:6] for row in clouds):
            target = FOLDER + '/' + name
            instance = unreal.load_asset(target) if library.does_asset_exist(target) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            mel.set_material_instance_parent(instance, masters[parent])
            for key, value in values.items():
                mel.set_material_instance_scalar_parameter_value(instance, key, value)
            mel.set_material_instance_vector_parameter_value(instance, 'A', unreal.LinearColor(a[0], a[1], a[2], 1))
            mel.set_material_instance_vector_parameter_value(instance, 'B', unreal.LinearColor(b[0], b[1], b[2], 1))
            mel.update_material_instance(instance)
            game.save(instance)
            report['instances'].append(name)
    for stem, first in (('SM_FX_Motes', 'MI_FX_Motes_Fire'), ('SM_FX_Puffs', 'MI_FX_Flame')):
        mesh = unreal.load_asset(FOLDER + '/' + stem)
        if mesh:
            mesh.set_material(0, unreal.load_asset(FOLDER + '/' + first))
            game.save(mesh)
    return report


def cloud(sub, owner, label, mesh, instance, middle, half_size, folder):
    keep = unreal.AttachmentRule.KEEP_WORLD
    spot = owner.get_actor_transform().transform_location(unreal.Vector(*middle))
    actor = sub.spawn_actor_from_class(unreal.StaticMeshActor, spot, owner.get_actor_rotation())
    actor.set_actor_label(owner.get_actor_label() + ' ' + label)
    actor.set_folder_path(folder)
    part = actor.static_mesh_component
    part.set_mobility(unreal.ComponentMobility.MOVABLE)
    part.set_static_mesh(unreal.load_asset(FOLDER + '/' + mesh))
    part.set_material(0, unreal.load_asset(FOLDER + '/' + instance))
    part.set_collision_profile_name('NoCollision')
    part.set_editor_property('cast_shadow', False)
    part.set_editor_property('bounds_scale', 4.0)
    actor.set_actor_scale3d(unreal.Vector(half_size[0] / 100.0, half_size[1] / 100.0, half_size[2] / 100.0))
    actor.attach_to_actor(owner, 'None', keep, keep, keep, False)
    return actor


def aura(sub, owner, element, half_size, folder, crown=None):
    """The element's clouds round `owner`: mesh actors fixed to it, the size of its body (half_size, cm). `crown`, a
    (middle, half size) in the body's own axes, adds a second cloud of the element's first kind there: the lion's
    burning mane. The enemy destroys what is attached to it when it dies."""
    made = []
    for k, row in enumerate(MOTES[element]):
        mesh, instance, against = row[0], row[2], row[6]
        lift, tall = row[7:9] if len(row) > 8 else (0.0, 1.0)
        size = (half_size[0] * against, half_size[1] * 1.3 * against, half_size[2] * against * tall)
        made.append(cloud(sub, owner, 'Motes %d' % k, mesh, instance, (0, 0, half_size[2] * lift), size, folder))
    if crown:
        mesh, _, instance = MOTES[element][0][:3]
        made.append(cloud(sub, owner, 'Motes Crown', mesh, instance, crown[0], crown[1], folder))
    return made
