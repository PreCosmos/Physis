"""Builds level 2, the Center of the Universe (`outfit_operation center:*`).

Order: materials, import, audio, level, scenario, cinema. Meshes and the height grid come from
Tools/build_physis_center.py, sound from Tools/build_physis_center_audio.py, text from
physis_center_lore.py. Gameplay Blueprint logic lives in Tools/blueprint_logic/center_logic.py.

The ops that build into the map and save it refuse unless the Center is the open map and no BP_Awakening has
TestArrival ticked (center_open). They are scenario, cinema, fauna, swim, director and save. center:level opens the
Center itself and refuses while any map has unsaved changes, so an unsaved tick stops it too. Like every rebuild
before it, it removes the whole 'Center' folder tree, including the Awakening Director (cinema or director places it
again). It keeps the Conclave's current (KEEP_FOLDERS), so conclave:portal need not run again after it.
center:materials refuses while the Center is open: deleting the materials its water, sky and post-process use clears
those references in the open map.

The enemy kinds (2026-11-08) need two more ops before center:scenario, both safe with the Center open and refused
while Play runs: enemy_looks (the enemies' own materials, ENEMY_LOOKS) and drone_ward (BP_TrainingDrone's Ward
component, then the Blueprint compiled and saved).
"""
import json
import math
import pathlib
import struct

import unreal

import physis_gameplay_tools as game
from physis_center_lore import CENTER_SCANS, CENTER_TUTORIALS, ENEMY_ENTRIES, center_entries

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
CENTER = '/Game/Center'
MESHES = CENTER + '/Meshes'
MATS = CENTER + '/Materials'
AUDIO = CENTER + '/Audio'
LEVEL = '/Game/Levels/L_CenterOfTheUniverse'
library = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
PROP = unreal.MaterialProperty


# ---------------------------------------------------------------- materials

def fresh_material(name, folder=MATS):
    path = folder + '/' + name
    if library.does_asset_exist(path):
        library.delete_asset(path)
    return tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())


def node(material, cls, x, y, **props):
    expression = lib.create_material_expression(material, cls, x, y)
    for key, value in props.items():
        expression.set_editor_property(key, value)
    return expression


def param(material, name, value, x, y):
    if isinstance(value, (tuple, list)):
        return node(material, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name, default_value=unreal.LinearColor(*value, 1) if len(value) == 3 else unreal.LinearColor(*value))
    return node(material, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value)


def custom(material, code, inputs, x, y, output=unreal.CustomMaterialOutputType.CMOT_FLOAT3):
    expression = node(material, unreal.MaterialExpressionCustom, x, y, code=code, output_type=output)
    entries = []
    for name, _ in inputs:
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        entries.append(entry)
    expression.set_editor_property('inputs', entries)
    for name, source in inputs:
        if isinstance(source, tuple):
            lib.connect_material_expressions(source[0], source[1], expression, name)
        else:
            lib.connect_material_expressions(source, '', expression, name)
    return expression


def finish(material):
    lib.recompile_material(material)
    game.save(material)
    return material


WIND = '''float3 p = LP;
float h = saturate(p.z / Height);
float t = T * Speed + WP.x * 0.0021 + WP.y * 0.0017;
float sway = (sin(t) * 0.7 + sin(t * 2.3 + 1.7) * 0.3) * h * h * Amount;
return float3(sway, sway * 0.6, 0);'''

# Creature motion lives in the vertex shader: each instance orbits its placed spot, turns to face
# the way it travels, bobs, and flaps or strides. Hundreds cost no game-thread time at all.
CREATURE_LOCAL = '''float ang = T * Speed + Rnd * 6.2831;
float dir = Speed >= 0 ? 1.0 : -1.0;
float head = ang + 1.5708 * dir;
float c = cos(head), s = sin(head);
float3 p = LP;
float wing = abs(p.y) > Body ? sin(T * Flap * 6.2831 + Rnd * 40.0) * (abs(p.y) - Body) * 0.9 : 0.0;
float stride = p.z < Legs ? sin(T * Stride + (p.x > 0 ? 0 : 3.14) + (p.y > 0 ? 1.57 : 0)) * (Legs - p.z) * 0.35 : 0.0;
p.z += wing;
p.x += stride;
float3 r = float3(p.x * c - p.y * s, p.x * s + p.y * c, p.z);
return r - LP;'''
CREATURE_ORBIT = '''float ang = T * Speed + Rnd * 6.2831;
float rad = Radius * (0.55 + 0.45 * frac(Rnd * 7.31));
return float3(cos(ang) * rad, sin(ang) * rad, sin(T * 1.3 + Rnd * 23.0) * Bob);'''

CEL = '''float2 uv = GetDefaultSceneTextureUV(Parameters, 14);
float3 sc = SceneTextureLookup(uv, 14, false).rgb;
float depth = SceneTextureLookup(uv, 1, false).r;
if (depth > 2000000.0) return sc;
float3 diff = max(SceneTextureLookup(uv, 2, false).rgb, 0.035);
float3 nrm = SceneTextureLookup(uv, 8, false).rgb;
float3 light = sc / diff;
float L = max(dot(light, float3(0.3, 0.59, 0.11)), 1e-4);
float lg = log2(L) / Stops;
float lq = (floor(lg) + smoothstep(0.5 - Soft, 0.5 + Soft, frac(lg))) * Stops;
float glow = saturate((L - GlowStart) / GlowStart);
float k = lerp(exp2(lq - log2(L)), 1.0, glow);
float3 col = sc * lerp(1.0, k, Strength);
float2 px = View.BufferSizeAndInvSize.zw * Thick * saturate(1.5 - depth / 20000.0 + 0.5);
float dl = SceneTextureLookup(uv + float2(-px.x, 0), 1, false).r;
float dr = SceneTextureLookup(uv + float2(px.x, 0), 1, false).r;
float du = SceneTextureLookup(uv + float2(0, -px.y), 1, false).r;
float dd = SceneTextureLookup(uv + float2(0, px.y), 1, false).r;
float dedge = abs(dl + dr + du + dd - 4.0 * depth) / depth;
float3 nl = SceneTextureLookup(uv + float2(-px.x, 0), 8, false).rgb;
float3 nu = SceneTextureLookup(uv + float2(0, -px.y), 8, false).rgb;
float nedge = (1.0 - dot(nrm, nl)) + (1.0 - dot(nrm, nu));
float ink = saturate((dedge - DepthEdge) * 18.0) + saturate((nedge - NormalEdge) * 3.0);
ink *= saturate(1.0 - depth / InkFar) * (1.0 - glow);
return lerp(col, col * Ink, saturate(ink) * InkStrength);'''


def material_cel():
    """Opaque surfaces: vertex colour albedo, vertex alpha drives the glow."""
    m = fresh_material('M_Cel')
    vc = node(m, unreal.MaterialExpressionVertexColor, -900, 0)
    tint = param(m, 'Tint', (1, 1, 1), -900, -200)
    base = node(m, unreal.MaterialExpressionMultiply, -600, -100)
    lib.connect_material_expressions(vc, '', base, 'A')
    lib.connect_material_expressions(tint, '', base, 'B')
    power = param(m, 'GlowPower', 9.0, -900, 250)
    clock = node(m, unreal.MaterialExpressionTime, -1100, 400)
    pulse = custom(m, 'return 0.8 + 0.2 * sin(T * 1.3 + WP.x * 0.004 + WP.y * 0.003);', [('T', clock), ('WP', node(m, unreal.MaterialExpressionWorldPosition, -1100, 520))], -900, 420, unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    glow = custom(m, 'return RGB * A * A * P * Pulse;', [('RGB', base), ('A', (vc, 'A')), ('P', power), ('Pulse', pulse)], -400, 200)
    lib.connect_material_property(base, '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(param(m, 'Roughness', .8, -400, 0), '', PROP.MP_ROUGHNESS)
    return finish(m)


def material_leaf():
    m = fresh_material('M_Leaf')
    m.set_editor_property('two_sided', True)
    vc = node(m, unreal.MaterialExpressionVertexColor, -900, 0)
    lib.connect_material_property(vc, '', PROP.MP_BASE_COLOR)
    power = param(m, 'GlowPower', 6.0, -900, 250)
    glow = custom(m, 'return RGB * A * A * P;', [('RGB', vc), ('A', (vc, 'A')), ('P', power)], -400, 200)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(param(m, 'Roughness', .7, -400, 0), '', PROP.MP_ROUGHNESS)
    wind = custom(m, WIND, [('LP', node(m, unreal.MaterialExpressionLocalPosition, -1200, 500)), ('WP', node(m, unreal.MaterialExpressionWorldPosition, -1200, 600)),
                            ('T', node(m, unreal.MaterialExpressionTime, -1200, 700)), ('Height', param(m, 'Height', 1600.0, -1200, 800)),
                            ('Speed', param(m, 'Speed', 1.1, -1200, 900)), ('Amount', param(m, 'Amount', 40.0, -1200, 1000))], -700, 600)
    world = node(m, unreal.MaterialExpressionTransform, -400, 600, transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                 transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    lib.connect_material_expressions(wind, '', world, '')
    lib.connect_material_property(world, '', PROP.MP_WORLD_POSITION_OFFSET)
    return finish(m)


def material_glow():
    m = fresh_material('M_Glow')
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    vc = node(m, unreal.MaterialExpressionVertexColor, -900, 0)
    power = param(m, 'GlowPower', 12.0, -900, 250)
    clock = node(m, unreal.MaterialExpressionTime, -1100, 400)
    glow = custom(m, 'return RGB * P * (0.75 + 0.25 * sin(T * 2.1 + WP.x * 0.01));',
                  [('RGB', vc), ('P', power), ('T', clock), ('WP', node(m, unreal.MaterialExpressionWorldPosition, -1100, 520))], -400, 200)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def material_crystal():
    m = fresh_material('M_Crystal')
    vc = node(m, unreal.MaterialExpressionVertexColor, -900, 0)
    fres = node(m, unreal.MaterialExpressionFresnel, -900, 300, exponent=2.5)
    power = param(m, 'GlowPower', 5.0, -900, 450)
    base = custom(m, 'return RGB * 0.35;', [('RGB', vc)], -500, 0)
    glow = custom(m, 'return RGB * (A * P * 0.5 + F * P * 1.2 + 0.15);', [('RGB', vc), ('A', (vc, 'A')), ('F', fres), ('P', power)], -500, 250)
    lib.connect_material_property(base, '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(param(m, 'Roughness', .08, -500, 500), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(param(m, 'Specular', 1.0, -500, 600), '', PROP.MP_SPECULAR)
    return finish(m)


# Camera fade: a creature's pixels closer to the camera than Near are clipped and dither back in by Far. A jellyfish
# drifting past the start of the Glade put its glowing tentacles against the lens as huge white streaks and hid
# Physis (2026-11-05). The game camera sits 3.3 m behind her, so creatures at her side stay whole. D: pixel - camera.
CREATURE_FADE = """float fade = saturate((length(D) - Near) / max(Far - Near, 1.0));
float2 px = Parameters.SvPosition.xy + View.StateFrameIndexMod8 * float2(7.0, 3.0);
float noise = frac(52.9829189 * frac(dot(px, float2(0.06711056, 0.00583715))));
return fade > noise ? 1.0 : 0.0;"""


def material_creature():
    """Crystal creature with vertex-shader motion. Parameters per instance set: Radius, Speed, Bob, Flap, Stride.
    Masked, so it can fade out close to the camera (CREATURE_FADE)."""
    m = fresh_material('M_Creature')
    m.set_editor_property('two_sided', True)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property('opacity_mask_clip_value', 0.5)
    toward = node(m, unreal.MaterialExpressionSubtract, -1250, -350)
    lib.connect_material_expressions(node(m, unreal.MaterialExpressionWorldPosition, -1500, -400), '', toward, 'A')
    lib.connect_material_expressions(node(m, unreal.MaterialExpressionCameraPositionWS, -1500, -300), '', toward, 'B')
    fade = custom(m, CREATURE_FADE, [('D', toward), ('Near', param(m, 'CamNear', 80.0, -1000, -450)), ('Far', param(m, 'CamFar', 300.0, -1000, -350))],
                  -500, -400, unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    lib.connect_material_property(fade, '', PROP.MP_OPACITY_MASK)
    vc = node(m, unreal.MaterialExpressionVertexColor, -900, 0)
    fres = node(m, unreal.MaterialExpressionFresnel, -900, 300, exponent=2.0)
    power = param(m, 'GlowPower', 6.0, -900, 450)
    base = custom(m, 'return RGB * 0.3;', [('RGB', vc)], -500, 0)
    glow = custom(m, 'return RGB * (A * P * 0.6 + F * P + 0.2);', [('RGB', vc), ('A', (vc, 'A')), ('F', fres), ('P', power)], -500, 250)
    lib.connect_material_property(base, '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(param(m, 'Roughness', .15, -500, 500), '', PROP.MP_ROUGHNESS)
    lp = node(m, unreal.MaterialExpressionLocalPosition, -1500, 700)
    clock = node(m, unreal.MaterialExpressionTime, -1500, 800)
    rnd = node(m, unreal.MaterialExpressionPerInstanceRandom, -1500, 900)
    speed = param(m, 'Speed', .3, -1500, 1000)
    local = custom(m, CREATURE_LOCAL, [('LP', lp), ('T', clock), ('Rnd', rnd), ('Speed', speed), ('Flap', param(m, 'Flap', 0.0, -1500, 1100)),
                                       ('Body', param(m, 'Body', 10.0, -1500, 1200)), ('Legs', param(m, 'Legs', 0.0, -1500, 1300)),
                                       ('Stride', param(m, 'Stride', 6.0, -1500, 1400))], -1000, 700)
    world = node(m, unreal.MaterialExpressionTransform, -700, 700, transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                 transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    lib.connect_material_expressions(local, '', world, '')
    orbit = custom(m, CREATURE_ORBIT, [('T', clock), ('Rnd', rnd), ('Speed', speed), ('Radius', param(m, 'Radius', 600.0, -1500, 1500)),
                                       ('Bob', param(m, 'Bob', 40.0, -1500, 1600))], -1000, 1000)
    total = node(m, unreal.MaterialExpressionAdd, -400, 800)
    lib.connect_material_expressions(world, '', total, 'A')
    lib.connect_material_expressions(orbit, '', total, 'B')
    lib.connect_material_property(total, '', PROP.MP_WORLD_POSITION_OFFSET)
    return finish(m)


def material_terrain():
    m = fresh_material('M_CenterTerrain')
    vc = node(m, unreal.MaterialExpressionVertexColor, -1000, 0)
    wp = node(m, unreal.MaterialExpressionWorldPosition, -1200, 300)
    # Cheap hashed detail breaks the vertex colour into moss and soil clumps at two scales.
    detail = custom(m, '''float2 p = WP.xy * 0.004;
float n = sin(p.x * 1.7 + sin(p.y * 2.3)) * sin(p.y * 1.9 + sin(p.x * 1.1));
float2 q = WP.xy * 0.0007;
float m = sin(q.x * 2.3 + sin(q.y * 1.7)) * sin(q.y * 2.1 + sin(q.x * 1.3));
return RGB * Bright * (0.8 + 0.14 * n + 0.12 * m);''', [('RGB', vc), ('WP', wp), ('Bright', param(m, 'Brightness', 2.2, -1200, 150))], -700, 0)
    clock = node(m, unreal.MaterialExpressionTime, -1200, 500)
    glow = custom(m, '''float w = 0.75 + 0.25 * sin(T * 0.9 + WP.x * 0.002 + WP.y * 0.0017);
return float3(0.25, 0.95, 0.8) * A * A * P * w;''', [('A', (vc, 'A')), ('T', clock), ('WP', wp), ('P', param(m, 'GlowPower', 3.0, -1200, 650))], -700, 300)
    lib.connect_material_property(detail, '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(param(m, 'Roughness', .92, -700, 600), '', PROP.MP_ROUGHNESS)
    return finish(m)


def material_water():
    m = fresh_material('M_CenterWater')
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    fade = node(m, unreal.MaterialExpressionDepthFade, -800, 300)
    lib.connect_material_expressions(param(m, 'FadeDistance', 160.0, -1100, 400), '', fade, 'FadeDistance')
    wp = node(m, unreal.MaterialExpressionWorldPosition, -1200, 0)
    clock = node(m, unreal.MaterialExpressionTime, -1200, 150)
    fres = node(m, unreal.MaterialExpressionFresnel, -1200, 250, exponent=4.0)
    colour = custom(m, '''float2 p = WP.xy * 0.0025;
float c = sin(p.x * 3.1 + T * 0.35 + sin(p.y * 2.7 + T * 0.2)) * sin(p.y * 3.3 - T * 0.3 + sin(p.x * 2.1));
float caustic = pow(saturate(c * 0.5 + 0.5), 6.0);
return float3(0.004, 0.02, 0.03) + float3(0.15, 0.7, 0.9) * caustic * 0.12 + float3(0.12, 0.3, 0.6) * F * 0.5;''',
                    [('WP', wp), ('T', clock), ('F', fres)], -800, 0)
    opacity = custom(m, 'return saturate(0.55 + F * 0.4) * D;', [('F', fres), ('D', fade)], -500, 300, unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    lib.connect_material_property(colour, '', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(opacity, '', PROP.MP_OPACITY)
    return finish(m)


def material_sky():
    """Unlit sky dome: the galactic heart of the universe hangs over the Center, with Divinity currents."""
    m = fresh_material('M_CenterSky')
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided', True)
    view = node(m, unreal.MaterialExpressionCameraVectorWS, -1100, 0)
    clock = node(m, unreal.MaterialExpressionTime, -1100, 200)
    sky = custom(m, '''float3 d = normalize(-V);
float up = saturate(d.z);
float3 col = lerp(float3(0.012, 0.016, 0.04), float3(0.002, 0.003, 0.012), pow(up, 0.6));
// Galactic core to the north, low and vast.
float3 core = normalize(float3(1.0, 0.15, 0.22));
float g = saturate(dot(d, core));
col += float3(1.0, 0.75, 0.55) * pow(g, 40.0) * 3.0 + float3(0.55, 0.35, 0.8) * pow(g, 8.0) * 0.6 + float3(0.15, 0.25, 0.6) * pow(g, 2.5) * 0.25;
// The galactic band.
float3 bandn = normalize(float3(-0.2, 0.25, 0.95));
float b = 1.0 - abs(dot(d, bandn));
float neb = sin(d.x * 9.0 + sin(d.y * 13.0)) * sin(d.y * 11.0 + sin(d.z * 7.0)) * 0.5 + 0.5;
col += float3(0.25, 0.3, 0.6) * pow(b, 14.0) * (0.4 + 0.6 * neb) * 0.6;
// Divinity currents: slow luminous ribbons across the sky.
float r = sin(d.x * 4.0 + d.y * 3.0 + T * 0.03) + sin(d.y * 5.0 - d.z * 4.0 - T * 0.02);
col += float3(0.1, 0.8, 0.9) * pow(saturate(1.0 - abs(r) * 3.0), 6.0) * up * 0.35;
// Stars.
float3 q = floor(d * 380.0);
float h = frac(sin(dot(q, float3(12.9898, 78.233, 37.719))) * 43758.5453);
float tw = 0.7 + 0.3 * sin(T * 3.0 + h * 50.0);
col += pow(h, 400.0) * 20.0 * tw * float3(0.9, 0.95, 1.0) * saturate(d.z + 0.2);
return col;''', [('V', view), ('T', clock)], -700, 0)
    lib.connect_material_property(sky, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def material_cel_post():
    m = fresh_material('PP_CenterCel')
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property('blendable_location', unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF)
    # These lookups make sure the scene textures used by the custom code are bound.
    keep = [node(m, unreal.MaterialExpressionSceneTexture, -1400, i * 120, scene_texture_id=t) for i, t in enumerate(
        (unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0, unreal.SceneTextureId.PPI_SCENE_DEPTH, unreal.SceneTextureId.PPI_DIFFUSE_COLOR, unreal.SceneTextureId.PPI_WORLD_NORMAL))]
    inputs = [('K%d' % i, (k, 'Color')) for i, k in enumerate(keep)]
    names = (('Stops', 1.1), ('Soft', .12), ('Strength', .85), ('GlowStart', 4.0), ('Thick', 1.0), ('DepthEdge', .012), ('NormalEdge', .45),
             ('InkFar', 60000.0), ('InkStrength', .8))
    for i, (name, value) in enumerate(names):
        inputs.append((name, param(m, name, value, -1100, i * 110)))
    inputs.append(('Ink', param(m, 'Ink', (.12, .1, .2), -1100, 1100)))
    out = custom(m, CEL, inputs, -500, 0)
    lib.connect_material_property(out, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


# Divinity Rays (physis_center_scenario.divinity_rays): a shaft of light from the heavens over every puzzle, Echo
# Cache and ability vault, so each can be found from across the Center (author, 2026-11-04: "I can't find any
# puzzles"). LP: local position (mesh units); R: pixel offset from the shaft's axis and C: camera offset (world cm);
# V: CameraVectorWS; D: DepthFade, softening the foot where it meets the ground.
RAY = """float h = saturate((LP.z - Bottom) / max(Top - Bottom, 1.0));
float vertical = smoothstep(0.0, Rise, h) * pow(saturate(1.0 - h), Taper);
float2 radial = R.xy / max(length(R.xy), 1.0);
float2 view = V.xy / max(length(V.xy), 1e-4);
float profile = pow(abs(dot(radial, view)), Soft);
float pulse = 1.0 + Pulse * sin(T * 0.9);
float bands = 1.0 - Bands * (0.5 + 0.5 * sin(R.z * 0.0015 + T * 1.8));
float near = smoothstep(NearIn, NearOut, length(C.xy));
return Colour * Intensity * vertical * profile * pulse * bands * near * D;"""


def material_ray():
    """Unlit, additive, two-sided shaft: fades in at its foot and out toward the heavens, soft at its silhouette
    (from the pixel's offset to the axis, so the mesh's normals do not matter), breathes slowly with bands of light
    falling down it, and fades out while the camera is near its axis. Fog only dims additive surfaces. It stays in
    the After-DOF translucency pass, so PP_CenterCel (Scene Color Before DOF) never bands or inks it."""
    m = fresh_material('M_DivinityRay')
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('two_sided', True)
    for key, value in (('compute_fog_per_pixel', True), ('translucency_pass', unreal.MaterialTranslucencyPass.MTP_AFTER_DOF)):
        try:
            m.set_editor_property(key, value)
        except Exception as error:
            unreal.log_warning('M_DivinityRay %s: %s' % (key, error))
    wp = node(m, unreal.MaterialExpressionWorldPosition, -1500, 0)
    op = node(m, unreal.MaterialExpressionObjectPositionWS, -1500, 150)
    cam = node(m, unreal.MaterialExpressionCameraPositionWS, -1500, 300)
    radial = node(m, unreal.MaterialExpressionSubtract, -1250, 50)
    lib.connect_material_expressions(wp, '', radial, 'A')
    lib.connect_material_expressions(op, '', radial, 'B')
    toward = node(m, unreal.MaterialExpressionSubtract, -1250, 250)
    lib.connect_material_expressions(cam, '', toward, 'A')
    lib.connect_material_expressions(op, '', toward, 'B')
    foot = node(m, unreal.MaterialExpressionDepthFade, -1250, 450)
    lib.connect_material_expressions(param(m, 'SoftFoot', 400.0, -1500, 450), '', foot, 'FadeDistance')
    inputs = [('LP', node(m, unreal.MaterialExpressionLocalPosition, -1500, -150)), ('R', radial), ('C', toward),
              ('V', node(m, unreal.MaterialExpressionCameraVectorWS, -1500, 600)), ('T', node(m, unreal.MaterialExpressionTime, -1500, 700)),
              ('D', foot), ('Colour', param(m, 'Colour', (1.0, .8, .45), -1000, -300))]
    for i, (name, value) in enumerate((('Intensity', .6), ('Bottom', -50.0), ('Top', 50.0), ('Rise', .04), ('Taper', 1.6), ('Soft', 2.0),
                                       ('Pulse', .15), ('Bands', .25), ('NearIn', 2500.0), ('NearOut', 10000.0))):
        inputs.append((name, param(m, name, value, -1000, -150 + i * 110)))
    lib.connect_material_property(custom(m, RAY, inputs, -500, 0), '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


RAY_LOOKS = {  # instance: linear colour, Intensity
    # Saturated, so the three still read apart once added to the Center's bright lavender haze (pale ones went white).
    'MI_DivinityRay_Puzzle': ((1.0, .55, .1), .65),  # open-world puzzles (three sealed by Settle thorns): Divinity gold
    'MI_DivinityRay_Vault': ((.6, .2, 1.0), .55),    # ability vaults, sealed until later levels: First One violet
    'MI_DivinityRay_Cache': ((.1, .75, 1.0), .5),    # Echo Caches, opened by Settle: Settle cyan
}


def ray_looks():
    """Creates or re-parents the ray instances (a rebuilt M_DivinityRay leaves them parentless). Bottom and Top
    are the engine cylinder's local extent, which BP_DivinityRay uses."""
    parent = unreal.load_asset(MATS + '/M_DivinityRay')
    box = unreal.load_asset('/Engine/BasicShapes/Cylinder').get_bounding_box()
    for name, (colour, power) in RAY_LOOKS.items():
        path = MATS + '/' + name
        mi = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(mi, parent)
        lib.clear_all_material_instance_parameters(mi)  # no stale overrides of parameters the parent no longer has
        lib.set_material_instance_vector_parameter_value(mi, 'Colour', unreal.LinearColor(*colour, 1))
        # Rays are kilometres tall: a 10-20 m fade at the foot, and light that stays strong high up.
        for key, value in (('Intensity', power), ('Bottom', box.min.z), ('Top', box.max.z), ('Rise', .004), ('Taper', .7)):
            lib.set_material_instance_scalar_parameter_value(mi, key, float(value))
        game.save(mi)
    return {'looks': sorted(RAY_LOOKS), 'cylinder_z': [box.min.z, box.max.z]}


# Enemy looks (center:enemy_looks; author, 2026-11-08: more enemy variety, and the enemies a fight needs shown in
# gold). The Center's masters take all their colour from vertex colour, and center:materials deletes and remakes them
# (so it refuses while the Center is open). The enemies get two masters of their own instead: M_Crystal's and M_Glow's
# shading, with the vertex colour leaned toward Tint by TintMix. 0 keeps the vertex colour. 1 is the Tint, shaded by
# the vertex colour's luminance, so a crystal keeps its light and dark parts; on the enemies' crystals (luminance
# about 0.5) that is close to the Tint itself. physis_center_scenario's Place.dress puts the instances on enemy slots by
# slot name. This op makes or updates only these twelve assets, and it never deletes one: a master is emptied and
# rebuilt in place, so the instances, and the placed enemies that use them, keep their references. So it is safe with
# the Center open.
ENEMY_TINT = '''float3 c = RGB.rgb;
float l = dot(c, float3(0.3, 0.59, 0.11));
return lerp(c, Tint.rgb * (0.4 + 1.2 * l), Mix);'''
ENEMY_LOOKS = {  # instance: master, Tint, TintMix, GlowPower
    # Tuned in Play on 2026-11-08: the first values read as white under the Center's bloom. Gold is a saturated yellow
    # (required enemies), Ember a red-orange well apart from it, Slate dark, Frost a clear cyan.
    'MI_Enemy_GoldCrystal': ('M_EnemyCrystal', (1.0, .74, .12), 1.0, 1.6),   # every enemy a fight counts
    'MI_Enemy_GoldGlow': ('M_EnemyGlow', (1.0, .78, .2), 1.0, 8.0),          # (M_Glow's 12 would outshine the red cores)
    'MI_Enemy_SlateCrystal': ('M_EnemyCrystal', (.16, .18, .22), 1.0, .4),   # Bastion: dull, heavy slate
    'MI_Enemy_SlateGlow': ('M_EnemyGlow', (.85, .06, .05), 1.0, 6.0),        # its deep red core
    'MI_Enemy_FrostCrystal': ('M_EnemyCrystal', (.18, .55, .95), 1.0, 1.2),  # Aegis Shard
    # Its ward plate: an engine cylinder, which has no vertex colour (white, full glow), hence the low power.
    'MI_Enemy_FrostWard': ('M_EnemyCrystal', (.3, .75, 1.0), 1.0, .8),
    'MI_Enemy_EmberCrystal': ('M_EnemyCrystal', (1.0, .22, .04), 1.0, 2.0),  # Ember Skitter
    'MI_Enemy_EmberGlow': ('M_EnemyGlow', (1.0, .3, .05), 1.0, 10.0),
    'MI_Enemy_OnyxCrystal': ('M_EnemyCrystal', (.06, .05, .08), 1.0, .4),    # Onyx Ward, and its face plate: black glass
    'MI_Enemy_OnyxGlow': ('M_EnemyGlow', (.6, .25, 1.0), 1.0, 10.0),         # its violet core, seen only from behind
}
# UE 5.8's DeleteAllMaterialExpressions deletes only about half the nodes per pass (physis_conclave_tools.master), so
# a rebuild empties a master in ten passes. Counting its nodes instead would mean reading an existing material's
# graph, and an introspection call on one crashed the editor.
ENEMY_CLEAR_PASSES = 10


def enemy_master(name, unlit):
    """MATS/name with an empty graph: made if missing, else emptied in place (never deleted)."""
    path = MATS + '/' + name
    if library.does_asset_exist(path):
        m = unreal.load_asset(path)
        for _ in range(ENEMY_CLEAR_PASSES):
            lib.delete_all_material_expressions(m)
    else:
        m = tools.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT if unlit else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    return m


def enemy_tint(m, vc):
    """The vertex colour leaned toward Tint by TintMix (ENEMY_TINT)."""
    return custom(m, ENEMY_TINT, [('RGB', vc), ('Tint', param(m, 'Tint', (1, 1, 1), -1300, -250)), ('Mix', param(m, 'TintMix', 0.0, -1300, -120))], -1000, 0)


def material_enemy_crystal():
    """material_crystal's shading on the tinted vertex colour."""
    m = enemy_master('M_EnemyCrystal', False)
    vc = node(m, unreal.MaterialExpressionVertexColor, -1300, 100)
    rgb = enemy_tint(m, vc)
    fres = node(m, unreal.MaterialExpressionFresnel, -900, 300, exponent=2.5)
    power = param(m, 'GlowPower', 5.0, -900, 450)
    base = custom(m, 'return RGB * 0.35;', [('RGB', rgb)], -500, 0)
    glow = custom(m, 'return RGB * (A * P * 0.5 + F * P * 1.2 + 0.15);', [('RGB', rgb), ('A', (vc, 'A')), ('F', fres), ('P', power)], -500, 250)
    lib.connect_material_property(base, '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(param(m, 'Roughness', .08, -500, 500), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(param(m, 'Specular', 1.0, -500, 600), '', PROP.MP_SPECULAR)
    return finish(m)


def material_enemy_glow():
    """material_glow's shading (unlit, pulsing) on the tinted vertex colour."""
    m = enemy_master('M_EnemyGlow', True)
    vc = node(m, unreal.MaterialExpressionVertexColor, -1300, 100)
    rgb = enemy_tint(m, vc)
    power = param(m, 'GlowPower', 12.0, -900, 250)
    clock = node(m, unreal.MaterialExpressionTime, -1100, 400)
    glow = custom(m, 'return RGB * P * (0.75 + 0.25 * sin(T * 2.1 + WP.x * 0.01));',
                  [('RGB', rgb), ('P', power), ('T', clock), ('WP', node(m, unreal.MaterialExpressionWorldPosition, -1100, 520))], -400, 200)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def enemy_looks():
    refuse_in_play('center:enemy_looks')
    masters = {'M_EnemyCrystal': material_enemy_crystal(), 'M_EnemyGlow': material_enemy_glow()}
    for name, (parent, tint, mix, power) in ENEMY_LOOKS.items():
        path = MATS + '/' + name
        mi = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(mi, masters[parent])
        lib.clear_all_material_instance_parameters(mi)  # no stale overrides
        lib.set_material_instance_vector_parameter_value(mi, 'Tint', unreal.LinearColor(*tint, 1))
        lib.set_material_instance_scalar_parameter_value(mi, 'TintMix', float(mix))
        lib.set_material_instance_scalar_parameter_value(mi, 'GlowPower', float(power))
        game.save(mi)
    return {'masters': sorted(masters), 'looks': sorted(ENEMY_LOOKS)}


def map_input():
    """The level map's input (Tools/blueprint_logic/center_overrides.py part map): M and the gamepad's View (Select)
    button, which was the Logbook's (author, 2026-11-04); the Logbook keeps L and stays a tab of the same menu. The
    menu pauses the game, so IA_Map fires while paused, like IA_Logbook and IA_Pause. physis_gameplay_tools'
    input_actions() holds the same bindings, so a rerun keeps them."""
    imc = unreal.load_asset('/Game/Input/IMC_Default')

    def key(name):
        bound = unreal.Key()
        bound.set_editor_property('key_name', name)
        return bound
    logbook = unreal.load_asset(game.ACTIONS + '/IA_Logbook')
    imc.unmap_all_keys_from_action(logbook)
    imc.map_key(logbook, key('L'))
    path = game.ACTIONS + '/IA_Map'
    action = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset('IA_Map', game.ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
    action.set_editor_property('trigger_when_paused', True)
    game.save(action)
    imc.unmap_all_keys_from_action(action)
    for name in ('M', 'Gamepad_Special_Left'):
        imc.map_key(action, key(name))
    game.save(imc)
    return [(m.action.get_name(), game.key_name(m.key)) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
            if m.action.get_name() in ('IA_Logbook', 'IA_Map')]


def map_art():
    """Imports the pause menu's map (Tools/build_physis_center_map.py -> Art/UI/T_UI_MapCenter.png) as a UI texture,
    alone: play:ui_import re-imports every UI texture and the station's meshes."""
    game.import_file(str(ROOT / 'Art/UI/T_UI_MapCenter.png'), '/Game/UI')
    texture = unreal.load_asset('/Game/UI/T_UI_MapCenter')
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    for axis in ('address_x', 'address_y'):
        texture.set_editor_property(axis, unreal.TextureAddress.TA_CLAMP)
    game.save(texture)
    return {'map': [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]}


def materials():
    made = [f() for f in (material_cel, material_leaf, material_glow, material_crystal, material_creature, material_terrain, material_water,
                          material_sky, material_cel_post)]
    if library.does_asset_exist(MESHES + '/SM_Center_Terrain_0_0'):
        terrain_look()
    report = {}
    for m in made:
        stats = lib.get_statistics(m)
        report[m.get_name()] = stats.num_pixel_shader_instructions
    return report


# ---------------------------------------------------------------- import

SLOT_LOOK = {'M_Cel': 'M_Cel', 'M_Crystal': 'M_Crystal', 'M_Leaf': 'M_Leaf', 'M_Glow': 'M_Glow', 'M_CenterTerrain': 'MI_CenterTerrain', 'M_CenterWater': 'M_CenterWater'}
TERRAIN_LOOK = {'GlowPower': .8, 'Brightness': 1.9}


def terrain_look():
    path = MATS + '/MI_CenterTerrain'
    mi = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset('MI_CenterTerrain', MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(mi, unreal.load_asset(MATS + '/M_CenterTerrain'))
    for name, value in TERRAIN_LOOK.items():
        lib.set_material_instance_scalar_parameter_value(mi, name, value)
    game.save(mi)
    for tx in range(8):
        for ty in range(8):
            mesh = unreal.load_asset(MESHES + '/SM_Center_Terrain_%d_%d' % (tx, ty))
            if mesh and mesh.get_material(0) != mi:
                mesh.set_material(0, mi)
                game.save(mesh)
    return mi
CREATURE_MOTION = {
    # mesh: Radius (cm), Speed (rad/s), Bob, Flap (Hz), Body (cm), Legs (cm), Stride
    'SM_CC_Moth': (500, .9, 60, 7.0, 6, 0, 0),  # GlowPower set high in creature_looks so moths outshine the ink lines
    'SM_CC_Jelly': (900, .12, 120, 0, 999, 0, 0),
    'SM_CC_Stag': (2600, .05, 0, 0, 999, 125, 9.0),
    'SM_CC_Fox': (1500, .14, 0, 0, 999, 38, 14.0),
    'SM_CC_SkyWhale': (60000, .012, 900, .12, 500, 0, 0),
}


def import_meshes(prefix=''):
    folder = ROOT / 'Art/Meshes/Center'
    made = []
    for path in sorted(folder.glob(prefix + '*.fbx')):
        stem = path.stem
        options = unreal.FbxImportUI()
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_as_skeletal', False)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
        data = options.static_mesh_import_data
        data.set_editor_property('combine_meshes', True)
        data.set_editor_property('generate_lightmap_u_vs', False)
        data.set_editor_property('auto_generate_collision', False)
        data.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)
        data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        game.import_file(str(path), MESHES, options)
        mesh = unreal.load_asset(MESHES + '/' + stem)
        if mesh is None:
            continue
        creature = stem in CREATURE_MOTION
        for index, slot in enumerate(mesh.get_editor_property('static_materials')):
            name = str(slot.get_editor_property('material_slot_name'))
            look = 'MI_' + stem if creature else SLOT_LOOK.get(name.split('.')[0], 'M_Cel')
            mesh.set_material(index, unreal.load_asset(MATS + '/' + look) or unreal.load_asset(MATS + '/M_Cel'))
        tree_like = stem.startswith(('SM_CT_GlowTree', 'SM_CT_Willow', 'SM_CT_Crystal', 'SM_CT_StillTree', 'SM_CT_Mushroom'))
        walkable = tree_like or stem.startswith(('SM_Center_Terrain', 'SM_CA_', 'SM_CT_RootBridge', 'SM_CT_Rock', 'SM_CT_RootArch'))
        collision_shape(mesh, walkable)
        if stem.startswith(('SM_CT_', 'SM_Center_Terrain')) and not stem.startswith('SM_CT_StillTree'):
            options = unreal.EditorScriptingMeshReductionOptions()
            options.set_editor_property('reduction_settings', [unreal.EditorScriptingMeshReductionSettings(1.0, 1.0), unreal.EditorScriptingMeshReductionSettings(.5, .35),
                                                               unreal.EditorScriptingMeshReductionSettings(.25, .15), unreal.EditorScriptingMeshReductionSettings(.1, .05)])
            unreal.EditorStaticMeshLibrary.set_lods(mesh, options)
        game.save(mesh)
        made.append(stem)
    return {'meshes': len(made)}


# The vaults' ability gates (physis_center_vaults.py): one box each, so no bar or membrane gap lets Physis through.
SOLID_GATES = ('SM_CA_GateLight', 'SM_CA_GateDissonance', 'SM_CA_GateMemory')


def collision_shape(mesh, complex_):
    """Per-polygon collision for trees, rocks, ruins and terrain, with no fitted primitives.
    Leaf and glow sections never collide, so only trunks and branches block Physis.
    Per-polygon collision is double-sided: build_physis_center.frame() builds a left-handed basis, so every
    tube and prism (trunks, roots, arches, crystals, spires) winds its sides inward, and one-sided collision
    let Physis walk into those from outside and then held her inside."""
    unreal.EditorStaticMeshLibrary.remove_collisions(mesh)
    body = mesh.get_editor_property('body_setup')
    if mesh.get_name() in SOLID_GATES:
        # A vault gate is one solid slab: its box blocks queries and physics alike, whatever its sections are.
        unreal.EditorStaticMeshLibrary.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.BOX)
        if body:
            body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
            body.set_editor_property('double_sided_geometry', False)
        return
    if body:
        body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if complex_ else unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
        body.set_editor_property('double_sided_geometry', bool(complex_))
    slots = [str(s.get_editor_property('material_slot_name')) for s in mesh.get_editor_property('static_materials')]
    editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for section in range(mesh.get_num_sections(0)):
        # Sections follow slot order here (an unused slot is always the last one).
        slot = slots[min(section, len(slots) - 1)]
        editor.enable_section_collision(mesh, slot not in ('M_Leaf', 'M_Glow'), 0, section)


def double_sided():
    """Makes the per-polygon collision of every Center structure, tree, rock and crystal double-sided
    (collision_shape now does this on import)."""
    done = []
    for path in unreal.EditorAssetLibrary.list_assets(MESHES, False):
        mesh = unreal.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh) or not mesh.get_name().startswith(('SM_CA_', 'SM_CT_')):
            continue
        body = mesh.get_editor_property('body_setup')
        if body and body.get_editor_property('collision_trace_flag') == unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
            collision_shape(mesh, True)
            game.save(mesh)
            done.append(mesh.get_name())
    return {'double_sided': done}


def tree_collision():
    done = []
    for path in unreal.EditorAssetLibrary.list_assets(MESHES, False):
        mesh = unreal.load_asset(path)
        stem = mesh.get_name()
        if isinstance(mesh, unreal.StaticMesh) and stem.startswith(('SM_CT_GlowTree', 'SM_CT_Willow', 'SM_CT_Crystal', 'SM_CT_StillTree', 'SM_CT_Mushroom', 'SM_CT_Rock', 'SM_CT_RootArch')):
            collision_shape(mesh, True)
            game.save(mesh)
            body = mesh.get_editor_property('body_setup')
            done.append((stem, str(body.get_editor_property('collision_trace_flag')).split('.')[-1] if body else None))
    return done


CREATURE_FADE_RANGE = {'SM_CC_Jelly': (200.0, 700.0)}  # cm; others (80, 300)


def creature_looks():
    parent = unreal.load_asset(MATS + '/M_Creature')
    for stem, (radius, speed, bob, flap, body, legs, stride) in CREATURE_MOTION.items():
        path = MATS + '/MI_' + stem
        mi = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset('MI_' + stem, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(mi, parent)
        glow = {'SM_CC_Moth': 60.0, 'SM_CC_Jelly': 14.0, 'SM_CC_Fox': 9.0, 'SM_CC_Stag': 9.0}.get(stem, 6.0)
        # Camera fade range (M_Creature CREATURE_FADE): the 5.6 m jellyfish's glowing tentacles still crossed half the
        # view at 3-6 m, so it fades out over a longer range than the animals at her side.
        near, far = CREATURE_FADE_RANGE.get(stem, (80.0, 300.0))
        for name, value in (('Radius', radius), ('Speed', speed), ('Bob', bob), ('Flap', flap), ('Body', body), ('Legs', legs), ('Stride', stride), ('GlowPower', glow),
                            ('CamNear', near), ('CamFar', far)):
            lib.set_material_instance_scalar_parameter_value(mi, name, float(value))
        game.save(mi)
    return {'creatures': len(CREATURE_MOTION)}


def import_audio():
    made = []
    for path in sorted((ROOT / 'Art/Audio/Center').glob('*.wav')):
        game.import_file(str(path), AUDIO)
        sound = unreal.load_asset(AUDIO + '/' + path.stem)
        loops = path.stem.startswith(('S_Music_Center', 'S_Music_Temple', 'S_Center_Ambience', 'S_Temple_Ambience', 'S_Creature_Loop', 'S_Whale_Loop'))
        sound.set_editor_property('looping', loops)
        game.save(sound)
        made.append(path.stem)
    for path in sorted((ROOT / 'Art/Audio/Voice/Center').glob('*.wav')):
        game.import_file(str(path), AUDIO + '/Voice')
        made.append(path.stem)
    sound_classes()
    return {'sounds': len(made)}


def sound_classes():
    """The awakening's music and voice-over (SEQ_Awakening's audio track) and the temple's music (an ambient
    sound) play outside BP_Physis's MusicComp and VoiceComp, so the Music and Voice Volume settings reach
    them through two sound classes that BP_Awakening's SyncMix scales in SM_CenterSettings: music by
    MusicVol / 6, voice by VoiceVol / 10, both 1.0 at the default settings, so the mix is unchanged there."""
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    made = {}
    for name, kind, factory in (('SC_CenterMusic', unreal.SoundClass, unreal.SoundClassFactory),
                                ('SC_CenterVoice', unreal.SoundClass, unreal.SoundClassFactory),
                                ('SM_CenterSettings', unreal.SoundMix, unreal.SoundMixFactory)):
        path = AUDIO + '/' + name
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            made[name] = unreal.load_asset(path)
        else:
            made[name] = tools.create_asset(name, AUDIO, kind, factory())
        game.save(made[name])
    for sound, group in (('S_Music_Awakening', 'SC_CenterMusic'), ('S_Music_Temple', 'SC_CenterMusic'),
                         ('Voice/S_VO_Awakening', 'SC_CenterVoice')):
        wave = unreal.load_asset(AUDIO + '/' + sound)
        wave.set_editor_property('sound_class_object', made[group])
        game.save(wave)
    return {'sound_classes': sorted(made)}


# ---------------------------------------------------------------- height grid

class Ground:
    def __init__(self):
        meta = json.loads((ROOT / 'Art/Meshes/Center/height.json').read_text())
        self.half, self.cell, self.n, self.water = meta['half'], meta['cell'], meta['n'], meta['water']
        self.regions = meta['regions']
        raw = (ROOT / 'Art/Meshes/Center/height.bin').read_bytes()
        self.h = struct.unpack('<%df' % (self.n * self.n), raw)

    def at(self, x, y):
        """Ground height in cm at Unreal (x, y) in cm."""
        fx, fy = (x / 100 + self.half) / self.cell, (y / 100 + self.half) / self.cell
        i, j = max(0, min(int(fx), self.n - 2)), max(0, min(int(fy), self.n - 2))
        u, v = fx - i, fy - j
        h = self.h
        n = self.n
        value = h[i * n + j] * (1 - u) * (1 - v) + h[(i + 1) * n + j] * u * (1 - v) + h[i * n + j + 1] * (1 - u) * v + h[(i + 1) * n + j + 1] * u * v
        return value * 100

    def ground(self, x, y, lift=0):
        return (x, y, max(self.at(x, y), self.water * 100 if lift >= 0 else -1e9) + lift)


# ---------------------------------------------------------------- level

def actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def mesh_actor(label, mesh, place, rot=(0, 0, 0), scale=1.0, folder='Center', collide=True, shadow=True):
    sub = actors()
    actor = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place), unreal.Rotator(*rot))
    actor.set_actor_label(label)
    part = actor.static_mesh_component
    part.set_static_mesh(unreal.load_asset(MESHES + '/' + mesh))
    part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
    part.set_editor_property('cast_shadow', shadow)
    scale = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    actor.set_folder_path(folder)
    return actor


def scatter_actor(label, mesh, rows, collide, cull, shadow, bounds=1.0, folder='Center/Scatter'):
    """One actor per mesh holding every instance in a native (non-Blueprint) instanced component,
    so the per-instance data is saved with the level and never reset by a construction script."""
    sub = actors()
    actor = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = subobjects.k2_gather_subobject_data_for_instance(actor)[0]
    handle, _ = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.HierarchicalInstancedStaticMeshComponent, blueprint_context=None))
    part = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
    part.set_static_mesh(unreal.load_asset(MESHES + '/' + mesh))
    part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
    part.set_editor_property('cast_shadow', shadow)
    part.set_editor_property('instance_end_cull_distance', cull)
    part.set_editor_property('instance_start_cull_distance', int(cull * .8))
    part.set_editor_property('bounds_scale', bounds)
    transforms = [unreal.Transform(unreal.Vector(x, y, z), unreal.Rotator(roll, pitch, yaw), unreal.Vector(s, s, s)) for x, y, z, pitch, yaw, roll, s in rows]
    part.add_instances(transforms, False, True)
    return actor


def scatter_blueprint():
    path = game.BLUEPRINTS + '/BP_CenterScatter'
    if library.does_asset_exist(path):
        return
    from editor_toolset.toolsets.actor import ActorTools
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', unreal.Actor)
    bp = tools.create_asset('BP_CenterScatter', game.BLUEPRINTS, unreal.Blueprint, factory)
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = None
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        item = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
        if isinstance(item, unreal.SceneComponent):
            root = item
    ActorTools.add_component(root, unreal.HierarchicalInstancedStaticMeshComponent.static_class(), 'Instances')
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    game.save(bp)


SCATTER_RULES = {
    # mesh: (collide, cull distance cm, cast shadow)
    'SM_CT_Grass': (False, 9000, False), 'SM_CT_Flowers': (False, 11000, False), 'SM_CT_Fern': (False, 14000, False),
    'SM_CT_Reeds': (False, 16000, False), 'SM_CT_Lily': (False, 16000, False), 'SM_CT_Crystal0': (False, 30000, False),
    'SM_CT_Rock0': (True, 30000, True), 'SM_CT_Mushroom1': (False, 40000, True),
}


def light(cls, label, place, rot=(0, 0, 0), folder='Center/Light'):
    actor = actors().spawn_actor_from_class(cls, unreal.Vector(*place), unreal.Rotator(*rot))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    return actor


def point(label, place, colour, intensity, radius, shadows=False):
    actor = light(unreal.PointLight, label, place)
    comp = actor.get_component_by_class(unreal.PointLightComponent)
    comp.set_light_color(unreal.LinearColor(*colour, 1))
    comp.set_editor_property('intensity', intensity)
    comp.set_editor_property('attenuation_radius', radius)
    comp.set_cast_shadows(shadows)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    return actor


# Folders build_level() keeps: the Divinity current to the Conclave and its return point (the Conclave session's
# re-runnable conclave:portal op, 2026-11-07). Nothing in the Center's own build places them again.
KEEP_FOLDERS = ('Center/Conclave',)


def new_level():
    """Opens the Center (or makes it) and removes what build_level() places: every actor in a 'Center' folder except
    KEEP_FOLDERS. load_level never asks about unsaved changes, it drops them, so this refuses while any map has some."""
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    unsaved = [package.get_name() for package in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if unsaved:
        raise RuntimeError('center:level refused: %s has unsaved changes, which opening the Center would drop. '
                           'Save or revert them first.' % ', '.join(unsaved))
    if library.does_asset_exist(LEVEL):
        les.load_level(LEVEL)
        sub = actors()
        for actor in sub.get_all_level_actors():
            folder = str(actor.get_folder_path())
            if not isinstance(actor, (unreal.WorldSettings, unreal.Brush)) and folder.startswith('Center') and not folder.startswith(KEEP_FOLDERS):
                sub.destroy_actor(actor)
    else:
        les.new_level(LEVEL)
    return les


def build_level():
    """Terrain, water, sky, light, cel post-process, scatter, landmarks and ruins."""
    new_level()
    g = Ground()
    sub = actors()
    for tx in range(8):
        for ty in range(8):
            actor = mesh_actor('Terrain %d %d' % (tx, ty), 'SM_Center_Terrain_%d_%d' % (tx, ty), (0, 0, 0), folder='Center/Terrain')
            actor.static_mesh_component.set_editor_property('cast_shadow', True)
    water = mesh_actor('Water', 'SM_Center_Water', (0, 0, 0), collide=False, shadow=False, folder='Center/Terrain')
    water.static_mesh_component.set_material(0, unreal.load_asset(MATS + '/M_CenterWater'))
    # A floor 45 cm under the surface so Physis wades through the marsh instead of sinking to the bed.
    floor = mesh_actor('Water Floor', 'SM_Center_Water', (0, 0, -45), shadow=False, folder='Center/Terrain')
    floor.set_actor_hidden_in_game(True)
    floor.static_mesh_component.set_visibility(False)
    sky = sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
    sky.set_actor_label('Sky')
    sky.set_folder_path('Center/Light')
    sky.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/EngineSky/SM_SkySphere'))
    sky.static_mesh_component.set_material(0, unreal.load_asset(MATS + '/M_CenterSky'))
    sky.static_mesh_component.set_collision_profile_name('NoCollision')
    sky.static_mesh_component.set_editor_property('cast_shadow', False)
    sky.set_actor_scale3d(unreal.Vector(3000, 3000, 3000))
    # Moonlight from the galactic core: cool, low, long shadows.
    moon = light(unreal.DirectionalLight, 'Core Light', (0, 0, 20000), (0, -24, 165))
    comp = moon.get_component_by_class(unreal.DirectionalLightComponent)
    comp.set_editor_property('intensity', 2.2)
    comp.set_light_color(unreal.LinearColor(.62, .72, 1.0, 1))
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property('dynamic_shadow_distance_movable_light', 18000.0)
    comp.set_editor_property('dynamic_shadow_cascades', 3)
    rim = light(unreal.DirectionalLight, 'Rim Light', (0, 0, 20000), (0, -10, -20))
    rc = rim.get_component_by_class(unreal.DirectionalLightComponent)
    rc.set_editor_property('intensity', .5)
    rc.set_light_color(unreal.LinearColor(.85, .45, 1.0, 1))
    rc.set_cast_shadows(False)
    rc.set_mobility(unreal.ComponentMobility.MOVABLE)
    skylight = light(unreal.SkyLight, 'Sky Fill', (0, 0, 5000))
    sc = skylight.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    sc.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sc.set_editor_property('cubemap', unreal.load_asset('/Engine/EngineResources/DefaultTextureCube') or None)
    sc.set_editor_property('intensity', 1.4)
    sc.set_light_color(unreal.LinearColor(.25, .38, .7, 1))
    sc.set_editor_property('lower_hemisphere_color', unreal.LinearColor(.02, .05, .06, 1))
    fog = light(unreal.ExponentialHeightFog, 'Marsh Mist', (0, 0, -200))
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property('fog_density', .006)
    fc.set_editor_property('fog_height_falloff', .12)
    fc.set_editor_property('fog_inscattering_luminance', unreal.LinearColor(.03, .07, .12, 1))
    fc.set_editor_property('directional_inscattering_luminance', unreal.LinearColor(.25, .18, .35, 1))
    fc.set_editor_property('start_distance', 1500.0)
    pp = light(unreal.PostProcessVolume, 'Center Look', (0, 0, 0))
    pp.set_editor_property('unbound', True)
    settings = pp.settings
    for key, value in (('override_auto_exposure_method', True), ('auto_exposure_method', unreal.AutoExposureMethod.AEM_HISTOGRAM),
                       ('override_auto_exposure_bias', True), ('auto_exposure_bias', 0.0),
                       ('override_auto_exposure_min_brightness', True), ('auto_exposure_min_brightness', -4.0),
                       ('override_auto_exposure_max_brightness', True), ('auto_exposure_max_brightness', -1.0),
                       ('override_auto_exposure_apply_physical_camera_exposure', True), ('auto_exposure_apply_physical_camera_exposure', False),
                       ('override_bloom_intensity', True), ('bloom_intensity', 1.15), ('override_bloom_threshold', True), ('bloom_threshold', .6),
                       ('override_vignette_intensity', True), ('vignette_intensity', .45),
                       ('override_color_saturation', True), ('color_saturation', unreal.Vector4(1.12, 1.12, 1.15, 1)),
                       ('override_color_contrast', True), ('color_contrast', unreal.Vector4(1.08, 1.08, 1.08, 1)),
                       ('override_scene_color_tint', True), ('scene_color_tint', unreal.LinearColor(.92, .97, 1.08, 1)),
                       ('override_film_toe', True), ('film_toe', .5)):
        try:
            settings.set_editor_property(key, value)
        except Exception:
            pass
    blend = unreal.WeightedBlendable()
    blend.set_editor_property('weight', 1.0)
    blend.set_editor_property('object', unreal.load_asset(MATS + '/PP_CenterCel'))
    blendables = unreal.WeightedBlendables()
    blendables.set_editor_property('array', [blend])
    settings.set_editor_property('weighted_blendables', blendables)
    pp.set_editor_property('settings', settings)
    # Scatter from the generator.
    data = json.loads((ROOT / 'Art/Meshes/Center/scatter.json').read_text())
    count = 0
    for mesh, rows in data.items():
        collide, cull, shadow = SCATTER_RULES.get(mesh, (True, 90000, True))
        if mesh.startswith('SM_CA_'):
            for index, row in enumerate(rows):
                x, y, z, pitch, yaw, roll, s = row
                mesh_actor('%s %d' % (mesh[6:], index), mesh, (x, y, z), (roll, pitch, yaw), s, folder='Center/Ruins')
        else:
            scatter_actor('Scatter ' + mesh[6:], mesh, rows, collide, cull, shadow)
        count += len(rows)
    landmarks(g)
    fauna(g)
    lamps(g, data.get('SM_CA_Lamp', []))
    fauna_actors(g)
    player = sub.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(*g.ground(-68400, 0, 120)), unreal.Rotator(0, 0, 0))
    player.set_actor_label('Physis Wakes')
    player.set_folder_path('Center')
    save_level()
    return {'instances': count}


def lamps(g, rows):
    for index, (x, y, z, pitch, yaw, roll, s) in enumerate(rows):
        if index % 2 == 0:
            yaw_r = math.radians(yaw)
            point('Lamp Light %d' % index, (x + math.cos(yaw_r) * 120, y + math.sin(yaw_r) * 120, z + 440), (1, .72, .4), 2200, 1600)


def landmarks(g):
    """Hand-placed set dressing for each region: what the player remembers and navigates by."""
    # The Glade: the Still Tree and the clearing where Physis wakes.
    x, y = -70500, -1500
    mesh_actor('Still Tree', 'SM_CT_StillTree', g.ground(x, y, -150), (0, 0, 20), 1.0, folder='Center/Glade')
    for i in range(10):
        a = i / 10 * 2 * math.pi
        mesh_actor('Glade Crystal %d' % i, 'SM_CT_Crystal%d' % (i % 2), g.ground(-68400 + math.cos(a) * 1500, math.sin(a) * 1500, -30), (0, 0, i * 37), .8 + (i % 3) * .2, folder='Center/Glade')
    point('Still Tree Glow', (x, y, g.at(x, y) + 1800), (.35, .85, 1), 60000, 6000, True)
    point('Wake Glow', (-68400, 0, g.at(-68400, 0) + 300), (.6, .85, 1), 6000, 1200)
    mesh_actor('Glade Arch', 'SM_CA_LightArch', g.ground(-56000, -4000, -80), (0, 0, 70), 1.0, folder='Center/Glade')
    # Concourse: a human plaza the Center swallowed, under a First One ring.
    cx, cy = 0, 0
    mesh_actor('Concourse Ring', 'SM_CA_FirstRing', g.ground(cx, cy, -100), (0, 0, 35), 1.4, folder='Center/Concourse')
    mesh_actor('Concourse Dish', 'SM_CA_Dish', g.ground(cx + 9000, cy - 9000, -50), (0, 0, -30), 1.2, folder='Center/Concourse')
    for i, (dx, dy, yaw) in enumerate(((-6000, 3000, 0), (6000, 4000, 90), (-4000, -7000, 45), (7000, -2000, 120))):
        mesh_actor('Concourse Arch %d' % i, 'SM_CA_HumanArch', g.ground(cx + dx, cy + dy, -20), (0, 0, yaw), 1.0, folder='Center/Concourse')
    mesh_actor('Concourse Stairs', 'SM_CA_HumanStairs', g.ground(cx - 8000, cy - 2000, -30), (0, 0, 180), 1.0, folder='Center/Concourse')
    # Choir Hollow: the hidden canyon of the Settle shrine.
    mesh_actor('Choir Arch', 'SM_CA_LightArch', g.ground(-15000 + 3000, 56000 - 18000, -100), (0, 0, 10), 1.3, folder='Center/Choir')
    # Marsh: willow halls and the sky whale's path overhead.
    mesh_actor('Marsh Arch', 'SM_CA_LightArch', g.ground(-36000, -44000, -100), (0, 0, -30), 1.2, folder='Center/Marsh')
    # Thornveil and Highlands landmarks.
    mesh_actor('Thornveil Spire', 'SM_CA_Spire', g.ground(40000, 46000, -200), (0, 0, 0), 1.4, folder='Center/Thornveil')
    mesh_actor('Highland Spire', 'SM_CA_Spire', g.ground(42000, -50000, -200), (0, 0, 40), 2.0, folder='Center/Highlands')
    mesh_actor('Highland Ring', 'SM_CA_FirstRing', g.ground(52000, -40000, -100), (0, 0, 90), 1.8, folder='Center/Highlands')
    temple(g)


TEMPLE = (76000, 0)


def temple(g):
    """The Temple of the First Light: the first temple. Its interior puzzles come later."""
    x, y = TEMPLE
    floor = 3400
    mesh_actor('Temple Base', 'SM_CA_TempleBase', (x, y, floor - 10), (0, 0, 0), 1.0, folder='Center/Temple')
    mesh_actor('Temple Colonnade', 'SM_CA_TempleColonnade', (x, y, floor + 600), (0, 0, 0), 1.0, folder='Center/Temple')
    mesh_actor('Temple Dome', 'SM_CA_TempleDome', (x, y, floor + 600), (0, 0, 0), 1.0, folder='Center/Temple')
    mesh_actor('Temple Gate', 'SM_CA_TempleGate', (x - 2400, y, floor + 600), (0, 0, 0), 1.0, folder='Center/Temple')
    mesh_actor('Temple Sanctum', 'SM_CA_TempleSanctum', (x, y, floor + 600), (0, 0, 0), 1.0, folder='Center/Temple')
    point('Temple Oculus', (x, y, floor + 4000), (.9, .8, .55), 90000, 5200, True)
    point('Temple Pool', (x, y, floor + 700), (.3, .9, 1), 12000, 2400)
    point('Temple Gate Light', (x - 2600, y, floor + 1400), (1, .8, .45), 15000, 2600)
    for i in range(6):
        a = i / 6 * 2 * math.pi
        point('Temple Column Light %d' % i, (x + math.cos(a) * 2400, y + math.sin(a) * 2400, floor + 2600), (.4, .85, 1), 5000, 1800)


# Scannable animals: one actor each, moved by BP_Creature on the CPU so its scan tag follows it.
# The shader keeps only the flapping and striding (MI_Actor_*: no orbit, no heading turn).
FAUNA = {
    # mesh: count, hover (lo, hi cm), scale, radius cm, speed rad/s, bob cm, ground, regions
    'SM_CC_Moth': (110, (220, 600), (.8, 1.2), 500, .9, 60, False, ('Glade', 'Marsh', 'Concourse', 'Choir', 'Thornveil')),
    'SM_CC_Jelly': (40, (400, 1400), (.8, 1.6), 900, .12, 120, False, ('Marsh', 'Choir', 'Glade')),
    'SM_CC_Stag': (34, (0, 0), (.9, 1.15), 2600, .05, 0, True, ('Glade', 'Concourse', 'Thornveil', 'Highlands', 'Marsh')),
    'SM_CC_Fox': (40, (0, 0), (.9, 1.1), 1500, .14, 0, True, ('Glade', 'Concourse', 'Thornveil', 'Marsh', 'Choir')),
}


def actor_looks():
    parent = unreal.load_asset(MATS + '/M_Creature')
    for stem in FAUNA:
        source = unreal.load_asset(MATS + '/MI_' + stem)
        path = MATS + '/MI_Actor_' + stem
        mi = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset('MI_Actor_' + stem, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(mi, parent)
        for name in ('Flap', 'Body', 'Legs', 'Stride', 'GlowPower', 'CamNear', 'CamFar'):
            lib.set_material_instance_scalar_parameter_value(mi, name, lib.get_material_instance_scalar_parameter_value(source, name))
        for name in ('Radius', 'Speed', 'Bob'):
            lib.set_material_instance_scalar_parameter_value(mi, name, 0.0)
        game.save(mi)


def fauna_actors(g):
    import random
    from physis_center_lore import FAUNA_SCANS
    from physis_aaa_tools import set_props
    actor_looks()
    sub = actors()
    for actor in sub.get_all_level_actors():
        if actor.get_actor_label().startswith(('Fauna ', 'Creature ')) and 'SkyWhale' not in actor.get_actor_label():
            sub.destroy_actor(actor)
    entries = {mesh: (category, title, text) for category, title, text, mesh in FAUNA_SCANS}
    creature = unreal.load_asset(game.BLUEPRINTS + '/BP_Creature').generated_class()
    tag_class = unreal.load_asset(game.BLUEPRINTS + '/BP_ScanTarget').generated_class()
    rng = random.Random(3)
    made = 0
    for mesh, (count, hover, scale, radius, speed, bob, ground, regions) in FAUNA.items():
        placed = 0
        while placed < count:
            cx, cy, r, _, _ = g.regions[rng.choice(regions)]
            a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0, r * .9)
            x, y = (cx + math.cos(a) * d) * 100, (cy + math.sin(a) * d) * 100
            floor = g.at(x, y)
            if ground and floor < 30:
                continue
            z = max(floor, 0) + rng.uniform(*hover)
            s = rng.uniform(*scale)
            actor = sub.spawn_actor_from_class(creature, unreal.Vector(x, y, z))
            actor.set_actor_label('Creature %s %d' % (mesh[6:], placed))
            actor.set_folder_path('Center/Fauna')
            actor.set_actor_scale3d(unreal.Vector(s, s, s))
            part = actor.get_component_by_class(unreal.StaticMeshComponent)
            part.set_static_mesh(unreal.load_asset(MESHES + '/' + mesh))
            part.set_material(0, unreal.load_asset(MATS + '/MI_Actor_' + mesh))
            part.set_collision_profile_name('NoCollision')
            part.set_editor_property('cast_shadow', mesh == 'SM_CC_Stag')
            actor.set_editor_property('Radius', radius * rng.uniform(.55, 1.0))
            actor.set_editor_property('Speed', speed * rng.choice((-1, 1)) * rng.uniform(.8, 1.2))
            actor.set_editor_property('Bob', float(bob))
            actor.set_editor_property('Phase', rng.uniform(0, 6.283))
            actor.set_editor_property('YawOffset', -90.0)
            actor.set_editor_property('Ground', ground)
            # Its scan tag rides along, at the middle of the body.
            category, title, text = entries[mesh]
            bounds = part.static_mesh.get_bounding_box()
            middle = (bounds.max.z + bounds.min.z) / 2 * s
            tag = sub.spawn_actor_from_class(tag_class, unreal.Vector(x, y, z + middle))
            tag.set_actor_label('Creature Tag %s %d' % (mesh[6:], placed))
            tag.set_folder_path('Center/Fauna')
            set_props(tag, ScanCategory=category, ScanTitle=title, ScanText=text)
            tag.set_editor_property('ScanImportant', False)
            game.hide_scan(tag)
            tag.attach_to_actor(actor, 'None', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
            placed += 1
            made += 1
    save_level()
    return {'creatures': made}


def fauna(g):
    """Ethereal wildlife, animated in their material: moths, jellies, stags, foxes and the sky whales."""
    import random
    rng = random.Random(3)
    groups = {} if True else {
        'SM_CC_Moth': (240, 220, 600, (0.8, 1.2)),
        'SM_CC_Jelly': (60, 400, 1400, (0.8, 1.6)),
        'SM_CC_Stag': (34, 0, 0, (0.9, 1.15)),
        'SM_CC_Fox': (40, 0, 0, (0.9, 1.1)),
    }
    wants = {'SM_CC_Moth': ('Glade', 'Marsh', 'Concourse', 'Choir', 'Thornveil'), 'SM_CC_Jelly': ('Marsh', 'Choir', 'Glade'),
             'SM_CC_Stag': ('Glade', 'Concourse', 'Thornveil', 'Highlands', 'Marsh'), 'SM_CC_Fox': ('Glade', 'Concourse', 'Thornveil', 'Marsh', 'Choir')}
    for mesh, (count, lo, hi, scale) in groups.items():
        rows = []
        while len(rows) < count:
            name = rng.choice(wants[mesh])
            cx, cy, r, _, _ = g.regions[name]
            a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0, r * .9)
            x, y = (cx + math.cos(a) * d) * 100, (cy + math.sin(a) * d) * 100
            ground = g.at(x, y)
            if mesh in ('SM_CC_Stag', 'SM_CC_Fox') and ground < 20:
                continue
            z = max(ground, 0) + rng.uniform(lo, hi)
            rows.append([x, y, z, 0, 0, 0, rng.uniform(*scale)])
        scatter_actor('Fauna ' + mesh[6:], mesh, rows, False, 60000, mesh in ('SM_CC_Stag',), 30.0, 'Center/Fauna')
    # Three sky whales circle the world far overhead.
    rows = [[-30000, -30000, 52000, 0, 0, 0, 3.0], [20000, 30000, 64000, 0, 0, 0, 2.4], [40000, -45000, 80000, 0, 0, 0, 3.4]]
    scatter_actor('Fauna SkyWhale', 'SM_CC_SkyWhale', rows, False, 0, False, 400.0, 'Center/Fauna')


def center_open(action):
    """The Center's map ops build into the open map and save it, so they run only with the Center open. They also never
    save it with BP_Awakening TestArrival ticked. That is the author's rule: a saved tick replays the awakening on every
    Center start in an editor build. Raises before anything changes."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    path = world.get_path_name().split('.')[0] if world else ''
    if path != LEVEL:
        raise RuntimeError('%s refused: the open map is %s, not %s. Open the Center first.' % (action, path or 'none', LEVEL))
    ticked = [actor.get_actor_label() for actor in actors().get_all_level_actors()
              if actor.get_class().get_name() == 'BP_Awakening_C' and actor.get_editor_property('TestArrival')]
    if ticked:
        raise RuntimeError('%s refused: TestArrival is ticked on %s, and the Center is never saved that way. It may be the '
                           'author testing the awakening: ask before unticking it.' % (action, ', '.join(ticked)))


def save_level():
    """Saves the open Center in place. It is never a Save As: save_map(world, LEVEL) with another map open would write
    that map over the Center, or stop at a modal dialog that blocks the editor."""
    center_open('Saving the Center')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


# ---------------------------------------------------------------- Blueprints and input for the Center

NEW_ACTORS = (('BP_Relic', MESHES + '/SM_CA_Stillstone', 'NoCollision'), ('BP_Rise', MESHES + '/SM_CA_Platform', 'BlockAll'),
              ('BP_Requirement', None, None), ('BP_SettleBarrier', MESHES + '/SM_CA_Barrier', 'BlockAll'),
              ('BP_SettleWave', '/Engine/BasicShapes/Sphere', 'NoCollision'), ('BP_Awakening', None, None),
              ('BP_Creature', MESHES + '/SM_CC_Moth', 'NoCollision'), ('BP_SwimDirector', None, None),
              # A lock that opens when Physis uses one ability near it (Settle now; Light Step, Resonance Link,
              # Trace Reading, Dissonance, Reweave and Sit With in later levels): center_logic.py actors.
              ('BP_AbilitySocket', MESHES + '/SM_CA_GateLight', 'BlockAll'),
              # A Divinity Ray over a puzzle (physis_center_scenario.divinity_rays), hidden once its reward is taken.
              ('BP_DivinityRay', '/Engine/BasicShapes/Cylinder', 'NoCollision'))


def settle_wave_material():
    m = fresh_material('M_SettleWave')
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('two_sided', True)
    fade = node(m, unreal.MaterialExpressionScalarParameter, -900, 200, parameter_name='Fade', default_value=1.0, use_custom_primitive_data=True, primitive_data_index=0)
    fres = node(m, unreal.MaterialExpressionFresnel, -900, 0, exponent=3.0)
    glow = custom(m, 'return float3(0.35, 1.2, 1.6) * pow(F, 1.5) * saturate(Fade) * 6.0;', [('F', fres), ('Fade', fade)], -500, 0)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def blueprints():
    from editor_toolset.toolsets.actor import ActorTools
    # settle_wave_material() deletes and recreates M_SettleWave, and BP_SettleWave gets its material only when the
    # Blueprint is first made: rebuilding it here on every run left the existing Settle wave without a material.
    if not library.does_asset_exist(MATS + '/M_SettleWave'):
        settle_wave_material()
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    made = []
    for name, mesh, collision in NEW_ACTORS:
        path = game.BLUEPRINTS + '/' + name
        if library.does_asset_exist(path):
            continue
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = tools.create_asset(name, game.BLUEPRINTS, unreal.Blueprint, factory)
        if mesh:
            root = None
            for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
                item = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
                if isinstance(item, unreal.SceneComponent):
                    root = item
            part = ActorTools.add_component(root, unreal.StaticMeshComponent.static_class(), 'Shape')
            part.set_static_mesh(unreal.load_asset(mesh))
            part.set_mobility(unreal.ComponentMobility.MOVABLE)
            part.set_collision_profile_name(collision)
            if name == 'BP_SettleWave':
                part.set_material(0, unreal.load_asset(MATS + '/M_SettleWave'))
                part.set_editor_property('cast_shadow', False)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
        made.append(name)
    # Settle and Mend inputs, added beside the existing mappings.
    imc = unreal.load_asset('/Game/Input/IMC_Default')
    existing = {(m.action.get_name(), game.key_name(m.key)) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')}
    for name, keys in (('IA_Settle', ('V', 'Gamepad_DPad_Right')), ('IA_Mend', ('Z', 'Gamepad_DPad_Left'))):
        path = game.ACTIONS + '/' + name
        action = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset(name, game.ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
        game.save(action)
        for key in keys:
            if (name, key) not in existing:
                bound = unreal.Key()
                bound.set_editor_property('key_name', key)
                imc.map_key(action, bound)
    game.save(imc)
    return {'made': made}


def refuse_in_play(action):
    """Raises before any change while Play runs: a Blueprint compiled or a material rebuilt under a running game
    reinstances what the game is using."""
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    playing = getattr(les, 'is_in_play_in_editor', None)
    if (playing and playing()) or unreal.EditorLevelLibrary.get_pie_worlds(False):
        raise RuntimeError('%s refused: Play is running. Stop it first.' % action)


# BP_TrainingDrone's 'Ward': a second StaticMeshComponent on the scene root, beside Shape. It is empty on every enemy
# but two kinds (center_overrides.py drones): the scenario (Place.ward) gives the Aegis Shard its ward plate and the
# Onyx Ward its dark face plate, on the drone's front (+X), so the player sees which side is protected. It never
# collides or casts a shadow. Place.reskin leaves it alone, since it is not the enemy's body.
WARD = 'Ward'


def ward_part(bp):
    """BP_TrainingDrone's 'Ward' component template, or None while center:drone_ward has not run."""
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        part = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
        if isinstance(part, unreal.StaticMeshComponent) and part.get_name().split('_GEN')[0] == WARD:
            return part
    return None


def drone_ward():
    """Adds the 'Ward' component to BP_TrainingDrone if it is missing (on the root, as the toolset attaches a new
    component to a Blueprint's root), sets it up whether new or not (no mesh, no collision, no shadow), then compiles
    and saves the Blueprint. Running it again changes nothing."""
    refuse_in_play('center:drone_ward')
    from editor_toolset.toolsets.actor import ActorTools
    bp = unreal.load_asset(game.BLUEPRINTS + '/BP_TrainingDrone')
    part = ward_part(bp)
    made = part is None
    if made:
        part = ActorTools.add_component(bp, unreal.StaticMeshComponent.static_class(), WARD)
    part.set_static_mesh(None)
    part.set_mobility(unreal.ComponentMobility.MOVABLE)
    part.set_collision_profile_name('NoCollision')
    part.set_editor_property('cast_shadow', False)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    game.save(bp)
    return {'ward': part.get_name(), 'made': made}


def import_getup(names=('A_Physis_GetUp',)):
    """Clips authored in Blender (get-up, swimming) imported onto Physis's body skeleton."""
    idle = unreal.load_asset('/Game/Characters/Physis/Animations/Physis_MM_Idle')
    options = unreal.FbxImportUI()
    options.set_editor_property('import_mesh', False)
    options.set_editor_property('import_animations', True)
    options.set_editor_property('import_as_skeletal', True)
    options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
    options.set_editor_property('skeleton', idle.get_editor_property('skeleton'))
    data = options.anim_sequence_import_data
    data.set_editor_property('animation_length', unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('import_bone_tracks', True)
    data.set_editor_property('remove_redundant_keys', False)
    report = {}
    for name in names:
        game.import_file(str(ROOT / 'Art/Characters/Physis' / (name + '.fbx')), '/Game/Characters/Physis/Animations', options)
        clip = unreal.load_asset('/Game/Characters/Physis/Animations/' + name)
        report[name] = clip.get_play_length() if clip else None
    return report


def water():
    """Deep water: one water volume under the whole waterline (z 0). Shallows stay walkable: Physis
    only swims once the water reaches the middle of her body. The old hidden wading floor goes."""
    sub = actors()
    for actor in sub.get_all_level_actors():
        if actor.get_actor_label() in ('Water Floor', 'Water Volume', 'Swim Director'):
            sub.destroy_actor(actor)
    volume = sub.spawn_actor_from_class(unreal.PhysicsVolume, unreal.Vector(0, 0, -1500))
    volume.set_actor_label('Water Volume')
    volume.set_folder_path('Center/Terrain')
    volume.set_actor_scale3d(unreal.Vector(1000, 1000, 15))  # the default brush is 200 cm: 2 km square, 30 m deep
    volume.set_editor_property('water_volume', True)
    volume.set_editor_property('fluid_friction', .35)
    volume.set_editor_property('terminal_velocity', 600.0)
    director = sub.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/BP_SwimDirector').generated_class(), unreal.Vector(0, 0, 0))
    director.set_actor_label('Swim Director')
    director.set_folder_path('Center/Terrain')
    save_level()
    box = volume.get_actor_bounds(False)
    return {'volume_top': box[0].z + box[1].z, 'volume_extent': box[1].to_tuple()}


def place_director():
    sub = actors()
    for actor in sub.get_all_level_actors():
        if actor.get_actor_label() == 'Awakening Director':
            sub.destroy_actor(actor)
    director = sub.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/BP_Awakening').generated_class(), unreal.Vector(-68400, 0, 0))
    director.set_actor_label('Awakening Director')
    director.set_folder_path('Center/Cinema')
    save_level()
    return {'director': True}


# ---------------------------------------------------------------- dispatcher

def execute(operation):
    if operation.startswith('exec:'):
        # exec:PATH runs a scratch script with this module's globals; it sets RESULT.
        scope = dict(globals())
        exec(open(operation.split(':', 1)[1]).read(), scope)
        return json.dumps(scope.get('RESULT'), default=str)
    if operation.startswith('prune:'):
        # prune:<Blueprint path>:<graph> removes the dead nodes write_graph_dsl left in that graph (physis_graph_prune).
        # The Blueprint write helpers call it after every write. It reports same=False if the live DSL changed.
        import importlib
        import physis_graph_prune
        importlib.reload(physis_graph_prune)
        return json.dumps(physis_graph_prune.prune_ref(operation.split(':', 1)[1]))
    if operation == 'materials':
        # It deletes and remakes M_CenterWater, M_CenterSky and PP_CenterCel. With the Center open, that clears the
        # water's, the sky's and 'Center Look's references and dirties the map, and a later save would keep them
        # cleared (review, 2026-11-07).
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if world and world.get_path_name().split('.')[0] == LEVEL:
            raise RuntimeError('center:materials refused: it remakes materials the open Center uses. Open another map '
                               'first (center:level opens the Center again).')
        return json.dumps(materials())
    if operation == 'import':
        report = creature_looks()
        report.update(import_meshes())
        return json.dumps(report)
    if operation.startswith('import:'):
        # import:PREFIX reimports only the meshes whose file name starts with PREFIX.
        return json.dumps(import_meshes(operation.split(':', 1)[1]))
    if operation == 'double_sided':
        return json.dumps(double_sided())
    if operation == 'tree_collision':
        return json.dumps(tree_collision())
    if operation == 'creature_looks':
        return json.dumps(creature_looks())
    if operation == 'creature_fade':
        # Only M_Creature (camera fade), then both instance sets re-parented: MI_SM_CC_* (scatter) and MI_Actor_* (creatures).
        m = material_creature()
        report = creature_looks()
        actor_looks()
        stats = lib.get_statistics(m)
        orphans = [a.get_asset_name() for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(MATS, False)
                   if str(a.asset_class_path.asset_name) == 'MaterialInstanceConstant' and unreal.load_asset(str(a.package_name)).get_editor_property('parent') is None]
        report.update({'pixel_instructions': stats.num_pixel_shader_instructions, 'vertex_instructions': stats.num_vertex_shader_instructions,
                       'blend': str(m.get_editor_property('blend_mode')), 'parentless_instances': orphans})
        return json.dumps(report)
    if operation == 'audio':
        return json.dumps(import_audio())
    if operation == 'sound_classes':
        return json.dumps(sound_classes())
    if operation in ('fauna', 'swim', 'director', 'scenario', 'cinema'):
        # These build into the open map and save it: refuse before any change unless it is the Center, as it is
        # safe to save (center_open). center:level opens the Center itself (new_level).
        center_open('center:' + operation)
    if operation == 'level':
        return json.dumps(build_level())
    if operation == 'blueprints':
        return json.dumps(blueprints())
    if operation == 'fauna':
        return json.dumps(fauna_actors(Ground()))
    if operation == 'getup':
        return json.dumps(import_getup())
    if operation == 'swim':
        report = import_getup(('A_Physis_SwimTread', 'A_Physis_SwimStroke'))
        report.update(water())
        return json.dumps(report)
    if operation == 'director':
        return json.dumps(place_director())
    if operation == 'save':
        save_level()
        return json.dumps({'saved': LEVEL})
    if operation == 'map_art':
        return json.dumps(map_art())
    if operation == 'map_input':
        return json.dumps(map_input())
    if operation == 'rays':
        material_ray()
        return json.dumps(ray_looks())
    if operation == 'enemy_looks':
        # Only its own new assets (M_EnemyCrystal, M_EnemyGlow, MI_Enemy_*), rebuilt in place: safe with the Center
        # open, unlike 'materials'. Before center:scenario, which puts them on the enemies.
        return json.dumps(enemy_looks())
    if operation == 'drone_ward':
        # BP_TrainingDrone's Ward component, before center:scenario (the Aegis Shards' and Onyx Wards' plates).
        return json.dumps(drone_ward())
    if operation == 'scenario':
        import physis_center_lore
        import physis_center_scenario
        import importlib
        # The lore first: the scenario imports its tables (and the vaults read them) at import time.
        importlib.reload(physis_center_lore)
        importlib.reload(physis_center_scenario)
        return json.dumps(physis_center_scenario.place(Ground()))
    if operation == 'cinema':
        import physis_center_scenario
        import importlib
        importlib.reload(physis_center_scenario)
        return json.dumps(physis_center_scenario.cinema(Ground()))
    raise ValueError('unknown center operation ' + operation)
