"""Builds level 8, Morrow, the Valley Before Morning (`morrow:` operations). Tools/morrow/README.md is the contract.

Run order: materials, import, audio, map_art, blueprints, level (physis_morrow_level.py); then the Blueprint logic
(Tools/blueprint_logic/morrow_logic.py); then scenario and portal (physis_morrow_scenario.py). In the open editor the
operations run through Saved/Morrow/run/live.sh.

Morrow is on Earth: it stands on the Grove's scans, trees and Hedge machines and on Halcyon's houses, and on the Grove's
material masters; nothing new is downloaded. What makes it the cold dawn is frost: three new masters are the Grove's
surface, plain and ground shaders with hoarfrost laid over every face that looks up (M_MW_Surface, M_MW_Plain,
M_MW_Ground; MPC_Grove's Heal thaws it, which the director raises once the Lull stops), and every material on a mesh
placed in L_Morrow is swapped for its frosted twin (regrade(): made on first use from the original's parameters). Two
more masters are new: M_MW_Stilled (a person's own colours under hoarfrost, its amount the component's custom primitive
data 0: 1 Stilled .. 0 woken) and M_MW_Ember (Sit With's small warm light: unlit, translucent, ember rose).

  slot            look
  CN_White STONE  the slab-concrete scan graded to granite     CN_Black ROCK  the concrete scan, the Just's grey
  CN_Metal ALLOY  the steel scan, dull                         CN_Lacquer     paint (vertex colour) over the old-paint scan
  CN_Gold         brass     CN_Red  matte red                 CN_Blue  slate (the graphite scan)
  CN_Cloth        the canvas scan, painted                     CN_Plaster  frost and Rime: white, a little glossy
  CN_Bark         timber: the planks scan, painted             CN_Glow  light (vertex colour)
  CN_Glass        window glass, cold (ice on the ice meshes)   CN_Ground  the terrain     CN_Water  the reservoir's ice

Operations: materials, frost_masters, import, import:PREFIX, audio, blueprints, input, map_art, level, level:PART, save,
scenario, portal, exec:PATH.
"""
import json
import pathlib
import re

import unreal

import physis_conclave_tools as cn
import physis_gameplay_tools as game
import physis_grove_tools as gt

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
ART = ROOT / 'Art/Meshes/Morrow'
MORROW = '/Game/Morrow'
MESHES = MORROW + '/Meshes'
MATS = MORROW + '/Materials'
AUDIO = MORROW + '/Audio'
LEVEL = '/Game/Levels/L_Morrow'
FOLDER = 'Morrow'
CM = 100.0
library = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary

GRANITE_REF = (.30, .305, .31)
CONCRETE_REF = (.29, .29, .285)
STEEL_REF = (.19, .19, .195)
SLATE_REF = (.05, .055, .065)
GLOW_STRENGTH = 22.0
BREAKUP = (('MacroScale', 4000.0), ('MacroVariation', .32))
SCAN_TINT = (.80, .86, .96)        # the Grove's brown rocks, cooled to the valley's granite
FROST = (.80, .84, .90)            # hoarfrost's colour
FROST_AMOUNT = .85
EMBER = (1.0, .45, .34)            # Sit With
BORROWED = ('SM_GS_Boulder', 'SM_GS_Stone', 'SM_GS_CliffC', 'SM_GS_CliffA', 'SM_GS_CliffB')
ICE_MESHES = ('SM_OT_GorgeIce', 'SM_ON_IceDisc')


# ---------------------------------------------------------------- frost masters

FROST_CODE = '''float up = saturate((WN.z - 0.25) * 2.2);
float fz = Frost * (1.0 - 0.85 * saturate(Heal)) * up * saturate(0.78 + 1.0 * (%(n1)s - 0.5) + 0.6 * (%(n2)s - 0.5));
col = lerp(col, FrostColour.rgb * (0.88 + 0.24 * %(n2)s), fz);
'''


def frost_surface(force=True):
    """M_MW_Surface: M_GRSurface with hoarfrost over every face that looks up (Frost, FrostColour; MPC_Grove Heal thaws
    it). The frost is matte, and takes the metal out of what it covers."""
    path = MATS + '/M_MW_Surface'
    if library.does_asset_exist(path) and not force:
        return 'kept'
    m = gt.master('M_MW_Surface', MATS, tangent_space_normal=False, used_with_instanced_static_meshes=True, used_with_skeletal_mesh=True)
    vc = gt.node(m, unreal.MaterialExpressionVertexColor, -1900, -500)
    lp = gt.node(m, unreal.MaterialExpressionLocalPosition, -1900, -380)
    rnd = cn.object_random(m, -2100, -260)
    wn = gt.node(m, unreal.MaterialExpressionVertexNormalWS, -1900, 600)
    ln = cn.transform(m, wn, cn.WORLD_TO_LOCAL, -1650, 700)
    values = {name: gt.scalar(m, name, value, -1650, -500 + i * 80) for i, (name, value) in enumerate(gt.SURFACE_DEFAULTS)}
    tex_d = gt.texture_object(m, 'ScanColour', gt.scan_texture('SConcrete', 'D'), 'D', -2400, -900)
    tex_n = gt.texture_object(m, 'ScanNormal', gt.scan_texture('SConcrete', 'N'), 'N', -2400, -750)
    tex_a = gt.texture_object(m, 'ScanMasks', gt.scan_texture('SConcrete', 'ARM'), 'M', -2400, -600)
    frame = [('LP', lp), ('LN', ln), ('Tile', values['Tile']), ('Sharp', values['TriSharpness']), ('Rnd', rnd)]
    tri = gt.cg.custom_outputs(gt.custom(m, gt.TRI_COLOUR, frame + [('TexD', tex_d), ('TexA', tex_a)], -1300, -900, gt.FLOAT4), [('ARM', gt.FLOAT3)])
    code = gt.SURFACE.replace('float peak = max(col.r', FROST_CODE % {'n1': 'nm', 'n2': 'nn'} + 'float peak = max(col.r', 1)
    code = code.replace('Metal = saturate(A.b * MetalScale);', 'Metal = saturate(A.b * MetalScale) * (1.0 - fz);')
    code = code.replace('return float4(col, saturate(A.g * RoughScale + RoughBias + 0.08 * (nn - 0.5)));',
                        'return float4(col, lerp(saturate(A.g * RoughScale + RoughBias + 0.08 * (nn - 0.5)), 0.62, fz));')
    assert 'fz);' in code and '0.62, fz' in code, 'M_GRSurface\'s code changed: update FROST_CODE\'s anchors'
    surf = gt.cg.custom_outputs(gt.custom(m, code, [
        ('VC', vc), ('D', tri), ('A', (tri, 'ARM')), ('LP', lp), ('Rnd', rnd), ('Mean', gt.vector(m, 'ScanMean', (.3, .3, .3), -1300, 300)),
        ('Ref', gt.vector(m, 'Reference', (.4, .4, .4), -1300, 400)), ('Tint', gt.vector(m, 'Tint', gt.WHITE, -1300, 500)),
        ('Balance', values['Balance']), ('Paint', values['Paint']), ('RustLo', values['RustLo']), ('RustHi', values['RustHi']),
        ('MacroScale', values['MacroScale']), ('Macro', values['MacroVariation']), ('Cavity', values['Cavity']),
        ('MetalScale', values['MetalScale']), ('RoughScale', values['RoughScale']), ('RoughBias', values['RoughBias']),
        ('WN', wn), ('Heal', gt.mpc_value(m, 'Heal', -1300, 800)), ('Frost', gt.scalar(m, 'Frost', FROST_AMOUNT, -1300, 880)),
        ('FrostColour', gt.vector(m, 'FrostColour', FROST, -1300, 960))],
        -900, -400, gt.FLOAT4), [('Metal', gt.FLOAT1), ('Occlusion', gt.FLOAT1)])
    lib.connect_material_property(cn.mask(m, surf, 'rgb', -500, -450), '', gt.PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, surf, 'a', -500, -330), '', gt.PROP.MP_ROUGHNESS)
    lib.connect_material_property(surf, 'Metal', gt.PROP.MP_METALLIC)
    lib.connect_material_property(surf, 'Occlusion', gt.PROP.MP_AMBIENT_OCCLUSION)
    lib.connect_material_property(values['Specular'], '', gt.PROP.MP_SPECULAR)
    normal = gt.custom(m, gt.TRI_NORMAL, frame + [('TexN', tex_n), ('K', values['NormalStrength'])], -1300, 700, gt.FLOAT3)
    lib.connect_material_property(cn.transform(m, normal, cn.LOCAL_TO_WORLD, -900, 700), '', gt.PROP.MP_NORMAL)
    gt.finish(m)
    return 'built'


def frost_plain(force=True):
    """M_MW_Plain: M_GRPlain (the vertex colour, a little varied) with the same hoarfrost."""
    path = MATS + '/M_MW_Plain'
    if library.does_asset_exist(path) and not force:
        return 'kept'
    m = gt.master('M_MW_Plain', MATS, used_with_instanced_static_meshes=True, used_with_skeletal_mesh=True)
    code = gt.PLAIN.replace('float peak = max(col.r', gt.cn.value_noise('nb', 'LP / 80.0 + Rnd * 11.7') + FROST_CODE % {'n1': 'na', 'n2': 'nb'} +
                            'float peak = max(col.r', 1)
    code = code.replace('return float4(col, saturate(R0 + RVar * (na - 0.5) * 2.0));', 'return float4(col, lerp(saturate(R0 + RVar * (na - 0.5) * 2.0), 0.6, fz));')
    assert '0.6, fz' in code, 'M_GRPlain\'s code changed: update its anchors'
    surf = gt.custom(m, code, [('VC', gt.node(m, unreal.MaterialExpressionVertexColor, -1200, -300)),
                               ('LP', gt.node(m, unreal.MaterialExpressionLocalPosition, -1200, -200)), ('Rnd', cn.object_random(m, -1400, -100)),
                               ('Tint', gt.vector(m, 'Tint', gt.WHITE, -1200, 50)), ('Var', gt.scalar(m, 'AlbedoVariation', .06, -1200, 150)),
                               ('Scale', gt.scalar(m, 'DetailScale', 40.0, -1200, 230)), ('R0', gt.scalar(m, 'Roughness', .5, -1200, 310)),
                               ('RVar', gt.scalar(m, 'RoughnessVariation', .06, -1200, 390)),
                               ('WN', gt.node(m, unreal.MaterialExpressionVertexNormalWS, -1200, 470)), ('Heal', gt.mpc_value(m, 'Heal', -1200, 550)),
                               ('Frost', gt.scalar(m, 'Frost', FROST_AMOUNT, -1200, 630)), ('FrostColour', gt.vector(m, 'FrostColour', FROST, -1200, 710))],
                     -700, -200, gt.FLOAT4)
    lib.connect_material_property(cn.mask(m, surf, 'rgb', -350, -250), '', gt.PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, surf, 'a', -350, -130), '', gt.PROP.MP_ROUGHNESS)
    lib.connect_material_property(gt.scalar(m, 'Metallic', 0.0, -350, 0), '', gt.PROP.MP_METALLIC)
    lib.connect_material_property(gt.scalar(m, 'Specular', .5, -350, 100), '', gt.PROP.MP_SPECULAR)
    gt.finish(m)
    return 'built'


def frost_ground(force=True):
    """M_MW_Ground: M_GRGround (the nine scanned layers) with hoarfrost over every face that looks up; the rock on the
    slopes keeps only a little of it."""
    path = MATS + '/M_MW_Ground'
    if library.does_asset_exist(path) and not force:
        return 'kept'
    import physis_morrow_plan as plan
    m = gt.master('M_MW_Ground', MATS, tangent_space_normal=False)
    table = gt.sets()
    vc = gt.node(m, unreal.MaterialExpressionVertexColor, -2000, -600)
    inputs = [('VC', vc), ('VA', (vc, 'A')),
              ('UV', gt.node(m, unreal.MaterialExpressionTextureCoordinate, -2000, -500, coordinate_index=0)),
              ('WP', gt.node(m, unreal.MaterialExpressionWorldPosition, -2000, -400)),
              ('VN', gt.node(m, unreal.MaterialExpressionVertexNormalWS, -2000, -300)),
              ('T', gt.node(m, unreal.MaterialExpressionTime, -2000, -200)), ('Heal', gt.mpc_value(m, 'Heal', -2000, -100))]
    for i, (key, set_name, _, look) in enumerate(gt.GROUND_LAYERS):
        colour = gt.texture_object(m, key + 'Colour', gt.scan_texture(set_name, 'D'), 'D', -3000, -1600 + i * 330)
        normal = gt.texture_object(m, key + 'Normal', gt.scan_texture(set_name, 'N'), 'N', -3000, -1450 + i * 330)
        gt.cg.shared_sampler(colour)
        gt.cg.shared_sampler(normal)
        inputs += [('Tex' + key, colour), ('Tex%sN' % key, normal),
                   ('Tile' + key, gt.scalar(m, key + 'Tile', table.get(set_name, {}).get('tile_m', 3.0) * CM, -2600, -1600 + i * 330)),
                   ('Look' + key, (gt.param(m, key + 'Look', tuple(look), -2600, -1500 + i * 330), 'RGBA')),
                   ('Mean' + key, gt.vector(m, key + 'Mean', tuple(table.get(set_name, {}).get('colour') or (.15, .12, .08)), -2600, -1400 + i * 330))]
    for i, (name, value) in enumerate((('Sharp', 2.0), ('RockLo', .75), ('RockHi', 1.15), ('MacroVar', .22), ('Water', plan.ICE_Z * CM),
                                       ('WetDark', .5), ('WetRough', .3), ('NormalK', 1.0), ('RockK', 1.0), ('GlowK', .6), ('RockMoss', .85), ('Breakup', .8))):
        inputs.append((name, gt.scalar(m, {'Sharp': 'BlendSharpness', 'MacroVar': 'MacroVariation', 'NormalK': 'NormalStrength',
                                           'RockK': 'RockNormalStrength', 'GlowK': 'BlightGlowStrength', 'RockLo': 'RockSlopeFrom',
                                           'RockHi': 'RockSlopeTo'}.get(name, name), value, -2000, 100 + i * 80)))
    inputs.append(('BlightGlow', gt.vector(m, 'BlightGlow', (1.0, .14, .68), -2000, 950)))
    inputs.append(('RockMossColour', gt.vector(m, 'RockMossColour', (.30, .32, .34), -2000, 1150)))
    inputs += [('Frost', gt.scalar(m, 'Frost', FROST_AMOUNT, -2000, 1250)), ('FrostColour', gt.vector(m, 'FrostColour', FROST, -2000, 1330)),
               ('SnowFrom', gt.scalar(m, 'SnowFrom', 13500.0, -2000, 1410)), ('SnowTo', gt.scalar(m, 'SnowTo', 18000.0, -2000, 1490))]
    code = gt.ground_code()
    anchor = 'float peak = max(col.r, max(col.g, col.b));\ncol *= min(1.0, 0.9 / max(peak, 0.0001));\nreturn float4(col, saturate(rough));'
    assert anchor in code, 'M_GRGround\'s code changed: update frost_ground\'s anchor'
    frost = ('float upg = saturate((Normal.z - 0.3) * 2.0);\n'
             'float fz = Frost * (1.0 - 0.85 * saturate(Heal)) * upg * (1.0 - 0.6 * wRock) * saturate(0.7 + 0.9 * (n1 - 0.5) + 0.5 * (n3 - 0.5));\n'
             '// Snow on the peaks above the valley: it stays when the frost thaws.\n'
             'float snow = smoothstep(SnowFrom, SnowTo, WP.z + 900.0 * (n2 - 0.5)) * saturate((Normal.z - 0.38) * 3.0);\n'
             'col = lerp(col, FrostColour.rgb * (0.86 + 0.28 * n2), max(fz, snow));\nrough = lerp(rough, 0.6, max(fz, snow));\n')
    code = code.replace(anchor, frost + anchor)
    ground = gt.cg.custom_outputs(gt.custom(m, code, inputs, -1200, -300, gt.FLOAT4), [('Normal', gt.FLOAT3), ('Glow', gt.FLOAT3)])
    lib.connect_material_property(cn.mask(m, ground, 'rgb', -700, -350), '', gt.PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, ground, 'a', -700, -230), '', gt.PROP.MP_ROUGHNESS)
    lib.connect_material_property(ground, 'Normal', gt.PROP.MP_NORMAL)
    lib.connect_material_property(ground, 'Glow', gt.PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(gt.scalar(m, 'Specular', .38, -700, 0), '', gt.PROP.MP_SPECULAR)
    gt.finish(m)
    return 'built'


STILLED_CODE = (gt.cn.value_noise('na', 'LP / 18.0 + Rnd * 7.3') + gt.cn.value_noise('nb', 'LP / 4.0 + Rnd * 3.1') + '''float3 own = VC.rgb * (1.0 + 0.08 * (na - 0.5));
float up = saturate(WN.z * 0.5 + 0.6);
float f = saturate(F * (0.75 + 0.35 * up + 0.25 * (nb - 0.5)));
float3 rime = FrostColour.rgb * (0.82 + 0.3 * nb);
float3 col = lerp(own, rime, f);
float peak = max(col.r, max(col.g, col.b));
col *= min(1.0, 0.9 / max(peak, 0.0001));
return float4(col, lerp(0.78, 0.32, f));''')


def stilled_master(force=True):
    """M_MW_Stilled: a person's own colours (the vertex colour) under hoarfrost. Custom primitive data 0 is the frost
    (1 Stilled .. 0 woken), which BP_Stilled lowers as they wake."""
    path = MATS + '/M_MW_Stilled'
    if library.does_asset_exist(path) and not force:
        return 'kept'
    m = gt.master('M_MW_Stilled', MATS, used_with_instanced_static_meshes=True)
    amount = gt.node(m, unreal.MaterialExpressionScalarParameter, -1200, 500, parameter_name='Frozen', default_value=1.0, use_custom_primitive_data=True,
                     primitive_data_index=0)
    surf = gt.custom(m, STILLED_CODE, [('VC', gt.node(m, unreal.MaterialExpressionVertexColor, -1200, -300)),
                                       ('LP', gt.node(m, unreal.MaterialExpressionLocalPosition, -1200, -200)), ('Rnd', cn.object_random(m, -1400, -100)),
                                       ('WN', gt.node(m, unreal.MaterialExpressionVertexNormalWS, -1200, 50)), ('F', amount),
                                       ('FrostColour', gt.vector(m, 'FrostColour', FROST, -1200, 300))], -700, -200, gt.FLOAT4)
    lib.connect_material_property(cn.mask(m, surf, 'rgb', -350, -250), '', gt.PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, surf, 'a', -350, -130), '', gt.PROP.MP_ROUGHNESS)
    lib.connect_material_property(gt.scalar(m, 'Specular', .5, -350, 100), '', gt.PROP.MP_SPECULAR)
    gt.finish(m)
    return 'built'


def ember_master(force=True):
    """M_MW_Ember: Sit With's light, a small warm glow round her: unlit, translucent, two-sided ember rose, brighter at
    grazing angles, a slow breath through it. Custom primitive data 0 is its strength (0 unseen .. 1 whole)."""
    from physis_center_tools import node
    path = MATS + '/M_MW_Ember'
    if library.does_asset_exist(path) and not force:
        return 'kept'
    m = gt.master('M_MW_Ember', MATS, blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, shading_model=unreal.MaterialShadingModel.MSM_UNLIT, two_sided=True)
    strength = node(m, unreal.MaterialExpressionScalarParameter, -900, 300, parameter_name='Strength', default_value=1.0, use_custom_primitive_data=True,
                    primitive_data_index=0)
    glow = gt.custom(m, '''float f = pow(1.0 - saturate(abs(dot(normalize(V), normalize(N)))), 2.0);
float breath = 0.8 + 0.2 * sin(T * 1.3);
Opacity = saturate(0.14 * f * f * S * breath);
return C.rgb * (0.2 + 1.8 * f) * 1.4 * S * breath;''', [('V', node(m, unreal.MaterialExpressionCameraVectorWS, -900, -300)),
                                                      ('N', node(m, unreal.MaterialExpressionVertexNormalWS, -900, -200)),
                                                      ('T', node(m, unreal.MaterialExpressionTime, -900, -100)), ('S', strength),
                                                      ('C', node(m, unreal.MaterialExpressionConstant3Vector, -900, 0, constant=unreal.LinearColor(*EMBER, 1.0)))],
                     -500, 0, gt.FLOAT3)
    glow = gt.cg.custom_outputs(glow, [('Opacity', gt.FLOAT1)])
    lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(glow, 'Opacity', unreal.MaterialProperty.MP_OPACITY)
    gt.finish(m)
    return 'built'


def frost_masters():
    return {'M_MW_Surface': frost_surface(), 'M_MW_Plain': frost_plain(), 'M_MW_Ground': frost_ground(), 'M_MW_Stilled': stilled_master(),
            'M_MW_Ember': ember_master()}


# ---------------------------------------------------------------- instances

def surface(name, set_name, ref, paint=False, balance=.92, metal=False, tint=(1.0, 1.0, 1.0), tile=None, rough_scale=1.0, extra=(), frost=FROST_AMOUNT):
    """An M_MW_Surface instance on a Grove texture set, graded toward `ref`."""
    row = gt.sets().get(set_name, {})
    scalars = [('Tile', (tile or row.get('tile_m') or 2.0) * CM), ('Paint', 1.0 if paint else 0.0), ('Balance', balance),
               ('MetalScale', 1.0 if metal else 0.0), ('RustLo', 2.0), ('RustHi', 3.0), ('RoughScale', rough_scale), ('Frost', frost)] + list(extra)
    vectors = [('ScanMean', tuple(row.get('colour') or (.3, .3, .3))), ('Reference', tuple(ref)), ('Tint', tint)]
    return gt.instance(name, unreal.load_asset(MATS + '/M_MW_Surface'), scalars, vectors,
                       [('ScanColour', gt.scan_texture(set_name, 'D')), ('ScanNormal', gt.scan_texture(set_name, 'N')),
                        ('ScanMasks', gt.scan_texture(set_name, 'ARM'))], folder=MATS)


def plain(name, rough, metal, tint=(1.0, 1.0, 1.0), frost=FROST_AMOUNT):
    return gt.instance(name, unreal.load_asset(MATS + '/M_MW_Plain'), [('Roughness', rough), ('Metallic', metal), ('Frost', frost)], [('Tint', tint)],
                       folder=MATS)


SLOT_MATERIAL = {'CN_Bark': 'MI_MW_Timber', 'CN_White': 'MI_MW_Stone', 'CN_Black': 'MI_MW_Concrete', 'CN_Metal': 'MI_MW_Steel',
                 'CN_Lacquer': 'MI_MW_Paint', 'CN_Gold': 'MI_MW_Brass', 'CN_Red': 'MI_MW_Red', 'CN_Blue': 'MI_MW_Slate', 'CN_Cloth': 'MI_MW_Cloth',
                 'CN_Plaster': 'MI_MW_Frost', 'CN_Glow': 'MI_MW_Glow', 'CN_Glass': 'MI_MW_Glass', 'CN_Ground': 'MI_MW_Ground', 'CN_Water': 'MI_MW_Ice'}
# Halcyon's houses and props, borrowed: their materials' frosted twins.
TWINS = {'MI_HA_Stone': 'MI_MW_Wash', 'MI_HA_Concrete': 'MI_MW_Concrete', 'MI_HA_Steel': 'MI_MW_Steel', 'MI_HA_Paint': 'MI_MW_Paint',
         'MI_HA_Cloth': 'MI_MW_Cloth', 'MI_HA_Timber': 'MI_MW_Timber', 'MI_HA_Slate': 'MI_MW_Slate', 'MI_HA_Brass': 'MI_MW_Brass',
         'MI_HA_Red': 'MI_MW_Red', 'MI_HA_Wrack': 'MI_MW_Frost', 'MI_HA_Glow': 'MI_MW_Glow', 'MI_HA_Glass': 'MI_MW_Glass',
         'MI_HA_Scan_Boulder': 'MI_MW_Scan_Boulder', 'MI_HA_Scan_Stone': 'MI_MW_Scan_Stone', 'MI_HA_Scan_CliffC': 'MI_MW_Scan_CliffC'}


def materials():
    masters = frost_masters()
    made = [surface('MI_MW_Stone', 'SConcreteSlab', GRANITE_REF, balance=.9, tint=(.92, .95, 1.0)).get_name(),
            surface('MI_MW_Wash', 'SConcreteSlab', (.6, .61, .615), balance=.85).get_name(),
            surface('MI_MW_Concrete', 'SConcrete', CONCRETE_REF, balance=.92, extra=BREAKUP).get_name(),
            surface('MI_MW_Steel', 'SSteel', STEEL_REF, balance=.85, metal=True, rough_scale=1.1, frost=.6).get_name(),
            surface('MI_MW_Paint', 'SPaintOld', (.5, .5, .5), paint=True, balance=.35).get_name(),
            surface('MI_MW_Cloth', 'SCanvas', (.42, .4, .35), paint=True, balance=.3, frost=.5).get_name(),
            surface('MI_MW_Timber', 'SPlanks', (.2, .17, .13), paint=True, balance=.55).get_name(),
            surface('MI_MW_Slate', 'SGraphite', SLATE_REF, balance=.9, rough_scale=.8, frost=1.0).get_name(),
            plain('MI_MW_Brass', .35, 1.0, frost=.3).get_name(), plain('MI_MW_Red', .6, 0.0).get_name(),
            plain('MI_MW_Frost', .38, 0.0, (1.0, 1.02, 1.08), frost=0.0).get_name()]
    gt.instance('MI_MW_Glow', unreal.load_asset(gt.MATS + '/M_GRGlow'), [('Strength', GLOW_STRENGTH)], folder=MATS)
    gt.instance('MI_MW_Glass', unreal.load_asset(cn.MATS + '/M_CNGlass'), [('Opacity', .55), ('FresnelOpacity', .9), ('Roughness', .05)],
                [('Tint', (.42, .50, .58))], folder=MATS)
    # The reservoir and the river: ice (glossy, pale, a little blue), and once the Lull stops, water.
    gt.instance('MI_MW_Ice', unreal.load_asset(MATS + '/M_MW_Plain'), [('Roughness', .16), ('Metallic', 0.0), ('RoughnessVariation', .12), ('Frost', .55)],
                [('Tint', (1.5, 1.6, 1.7))], folder=MATS)
    water = unreal.load_asset(cn.MATS + '/M_CNWater')
    gt.instance('MI_MW_Lake', water, [('Ripple', .2), ('RippleSpeed', .4), ('Clarity', 300.0), ('MaxOpacity', .92), ('TintDepth', 250.0),
                                      ('FoamStrength', .05), ('FoamWidth', 1.0), ('Roughness', .03)],
                [('WaterColour', (.05, .08, .10)), ('BodyColour', (.008, .014, .02)), ('FoamColour', (.8, .82, .84))], folder=MATS)
    # The ground: Morrow's frosted copy of the Grove's, the layers' looks cooled and paled (the grass is winter grass).
    gt.instance('MI_MW_Ground', unreal.load_asset(MATS + '/M_MW_Ground'), [], [('GrassLook', (.62, .64, .55, .45)), ('ForestLook', (.8, .8, .78, .7)),
                                                                              ('LitterLook', (.72, .7, .66, .6)), ('MossLook', (.42, .48, .44, .6)),
                                                                              ('RockLook', (.36, .39, .43, .35))], folder=MATS)
    borrowed = {}
    for stem in BORROWED:
        mesh = unreal.load_asset(gt.SCANS + '/' + stem)
        if mesh is None:
            continue
        mi = gt.instance('MI_MW_Scan_' + stem[6:], mesh.get_material(0), [('Moss', 0.0), ('DetailAmount', .5)],
                         [('Tint', SCAN_TINT), ('DetailMean', (.2, .14, .08))], folder=MATS)
        borrowed[stem] = mi.get_name()
    return {'masters': masters, 'instances': made + ['MI_MW_Glow', 'MI_MW_Glass', 'MI_MW_Ice', 'MI_MW_Lake', 'MI_MW_Ground'], 'borrowed': borrowed,
            'relinked': relink()}


# ---------------------------------------------------------------- frosted twins of borrowed materials

_twins = {}
PARENTS = {'M_GRSurface': 'M_MW_Surface', 'M_GRPlain': 'M_MW_Plain'}


def _base(material):
    m = material
    for _ in range(8):
        if isinstance(m, unreal.MaterialInstance):
            parent = m.get_editor_property('parent')
            if parent is None:
                break
            m = parent
        else:
            break
    return m


def frosted(material):
    """The frosted twin of a material on a borrowed mesh (or None to keep it): Halcyon's are mapped by TWINS; any other
    instance of the Grove's surface or plain master gets an MI_MW_F_ copy on Morrow's frost master with the same
    parameters; leaves get a pale, cold copy of themselves."""
    if material is None:
        return None
    name = material.get_name()
    if name.startswith(('MI_MW_', 'M_MW_')):
        return None
    if name in _twins:
        return _twins[name]
    out = None
    if name in TWINS:
        path = MATS + '/' + TWINS[name]
        out = unreal.load_asset(path) if library.does_asset_exist(path) else None
    elif isinstance(material, unreal.MaterialInstance):
        base = _base(material).get_name()
        if base in PARENTS or base == 'M_GRLeaf':
            parent = unreal.load_asset(MATS + '/' + PARENTS[base]) if base in PARENTS else material
            scalars = [(n, lib.get_material_instance_scalar_parameter_value(material, n)) for n in lib.get_scalar_parameter_names(material)]
            vectors = []
            for n in lib.get_vector_parameter_names(material):
                c = lib.get_material_instance_vector_parameter_value(material, n)
                vectors.append((n, (c.r, c.g, c.b, c.a)))
            textures = [(n, lib.get_material_instance_texture_parameter_value(material, n)) for n in lib.get_texture_parameter_names(material)]
            textures = [(n, t) for n, t in textures if t is not None]
            if base == 'M_GRLeaf':
                # Frost on leaves and grass: paler, colder, less saturated, and stiller in the windless dawn.
                scalars = [(n, v) for n, v in scalars if n not in ('Gain', 'WindAmount')] + [('Gain', .95), ('WindAmount', .6)]
                vectors = [(n, v) for n, v in vectors if n != 'WarmTint'] + [('WarmTint', (1.25, 1.35, 1.55, 1.0))]
            out = gt.instance('MI_MW_F_' + name[3:] if name.startswith('MI_') else 'MI_MW_F_' + name, parent, scalars, vectors, textures, folder=MATS)
    _twins[name] = out
    return out


def regrade(actor):
    """Swaps every material on the actor's mesh components (instanced ones too) for its frosted twin."""
    swapped = 0
    for part in actor.get_components_by_class(unreal.StaticMeshComponent):
        if part.get_editor_property('static_mesh') is None:
            continue
        for slot in range(part.get_num_materials()):
            material = part.get_material(slot)
            new = frosted(material)
            if new is not None and new != material:
                part.set_material(slot, new)
                swapped += 1
    return swapped


# ---------------------------------------------------------------- import

NO_COLLISION = ('SM_OE_', 'SM_ON_Satchel', 'SM_ON_Lantern', 'SM_OT_GorgeIce')
BOX_MESHES = ('SM_ON_RimeWall', 'SM_ON_RimeMound', 'SM_ON_RimeDoor', 'SM_ON_Chapel', 'SM_ON_Mill', 'SM_ON_Hold', 'SM_ON_School', 'SM_ON_Telegraph',
              'SM_ON_IceHouse', 'SM_ON_Bench', 'SM_ON_Chair', 'SM_OP_')
HARD_LODS = ((1.0, 1.0), (.5, .3), (.25, .12), (.12, .04))
TERRAIN_LODS = ((1.0, 1.0), (.5, .45), (.25, .2))


def apply_slots(mesh):
    unknown = []
    stem = mesh.get_name()
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = cn.slot_name(slot)
        want = SLOT_MATERIAL.get(name)
        if stem.startswith(ICE_MESHES) and name == 'CN_Glass':
            want = 'MI_MW_Ice'
        if stem.startswith('SM_OP_') and name == 'CN_Cloth':
            want = 'M_MW_Stilled'
        material = unreal.load_asset(MATS + '/' + want) if want and library.does_asset_exist(MATS + '/' + want) else None
        if material is None:
            unknown.append('%s -> %s' % (name, want))
            continue
        if slot.get_editor_property('material_interface') != material:
            mesh.set_material(index, material)
    return unknown


def import_meshes(prefix=''):
    made, unknown, failed, notes = [], {}, [], []
    for path in sorted(ART.glob(prefix + '*.fbx')):
        stem = path.stem
        if re.search(r'_LOD\d$', stem):
            continue
        game.import_file(str(path), MESHES, cn.import_options())
        mesh = unreal.load_asset(MESHES + '/' + stem)
        if mesh is None:
            failed.append(stem)
            continue
        missing = apply_slots(mesh)
        if missing:
            unknown[stem] = missing
        cn.collision(mesh, 'box' if stem.startswith(BOX_MESHES) else 'none' if stem.startswith(NO_COLLISION) else 'complex')
        chain = TERRAIN_LODS if stem.startswith('SM_OT_Terrain') else None if stem.startswith('SM_OT_') else HARD_LODS
        if chain is not None:
            why = cn.apply_lods(mesh, chain)
            if why:
                notes.append('%s: %s' % (stem, why))
        game.save(mesh)
        made.append(stem)
    return {'meshes': len(made), 'failed': failed, 'unknown_slots': unknown, 'lods': notes}


def relink():
    count = 0
    for path in library.list_assets(MESHES, False) if library.does_directory_exist(MESHES) else []:
        mesh = unreal.load_asset(path)
        if isinstance(mesh, unreal.StaticMesh):
            apply_slots(mesh)
            game.save(mesh)
            count += 1
    return count


def import_audio():
    sounds, voices, loops = 0, 0, []
    music_class = unreal.load_asset(cn.MUSIC_CLASS)
    for path in sorted((ROOT / 'Art/Audio/Morrow').glob('*.wav')):
        game.import_file(str(path), AUDIO)
        wave = unreal.load_asset(AUDIO + '/' + path.stem)
        if wave is None:
            continue
        looping = path.stem.startswith(('S_Music_', 'S_Amb_'))
        wave.set_editor_property('looping', looping)
        if path.stem.startswith('S_Amb_') and music_class is not None:
            wave.set_editor_property('sound_class_object', music_class)
        game.save(wave)
        if looping:
            loops.append(path.stem)
        sounds += 1
    for path in sorted((ROOT / 'Art/Audio/Morrow/Voice').glob('*.wav')):
        game.import_file(str(path), AUDIO + '/Voice')
        voices += 1
    return {'sounds': sounds, 'voices': voices, 'looping': loops}


# ---------------------------------------------------------------- Blueprints and input

NEW_BLUEPRINTS = ('BP_Stilled', 'BP_SitWith', 'BP_MorrowDirector', 'BP_MorrowCurrent')


def sit_input():
    """IA_SitWith on H, and on the pad's D-pad left held 0.45 s (a tap is still Mend)."""
    imc = unreal.load_asset('/Game/Input/IMC_Default')
    path = game.ACTIONS + '/IA_SitWith'
    action = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset('IA_SitWith', game.ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
    game.save(action)
    mappings = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
    existing = {(m.action.get_name() if m.action else None, game.key_name(m.key)) for m in mappings}
    added = []
    for key, hold in (('H', False), ('Gamepad_DPad_Left', True)):
        if ('IA_SitWith', key) in existing:
            continue
        bound = unreal.Key()
        bound.set_editor_property('key_name', key)
        mapping = imc.map_key(action, bound)
        if hold:
            trigger = unreal.new_object(unreal.InputTriggerHold, imc)
            trigger.set_editor_property('hold_time_threshold', .45)
            trigger.set_editor_property('is_one_shot', True)
            mapping.set_editor_property('triggers', [trigger])
            mappings = list(imc.get_editor_property('default_key_mappings').get_editor_property('mappings'))
            for m_ in mappings:
                if m_.action == action and game.key_name(m_.key) == key:
                    m_.set_editor_property('triggers', [trigger])
            data = imc.get_editor_property('default_key_mappings')
            data.set_editor_property('mappings', mappings)
            imc.set_editor_property('default_key_mappings', data)
        added.append(key)
    game.save(imc)
    after = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
    return {'added': added, 'IA_SitWith': [(game.key_name(m.key), [t.get_class().get_name() for t in m.get_editor_property('triggers')]) for m in after
                                           if m.action and m.action.get_name() == 'IA_SitWith'],
            'H elsewhere': [m.action.get_name() for m in after if m.action and game.key_name(m.key) == 'H' and m.action.get_name() != 'IA_SitWith']}


def light(bp, colour, radius, z=150.0):
    glow = gt.add_component(bp, unreal.PointLightComponent, 'Glow')
    glow.set_editor_property('relative_location', unreal.Vector(0, 0, z))
    glow.set_mobility(unreal.ComponentMobility.MOVABLE)
    glow.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
    glow.set_editor_property('intensity', 0.0)
    glow.set_editor_property('attenuation_radius', radius)
    glow.set_light_color(gt.linear(colour))
    glow.set_cast_shadows(False)
    return glow


def blueprints():
    """Morrow's own Blueprints with their components (Tools/blueprint_logic/morrow_logic.py writes their graphs)."""
    made = []
    for name in NEW_BLUEPRINTS:
        if library.does_asset_exist(game.BLUEPRINTS + '/' + name):
            continue
        bp = cn.new_blueprint(name)
        if name == 'BP_Stilled':
            gt.shape(bp, unreal.load_asset(MESHES + '/SM_OP_Stilled0'))
            light(bp, EMBER, 700.0, 120.0)
        elif name == 'BP_SitWith':
            glow = gt.shape(bp, unreal.load_asset('/Engine/BasicShapes/Sphere'), shadow=False)
            glow.set_editor_property('relative_scale3d', unreal.Vector(5.0, 5.0, 3.0))   # a low dome 5 m across round her
            glow.set_editor_property('relative_location', unreal.Vector(0, 0, -60.0))
            glow.set_collision_profile_name('NoCollision')
            glow.set_material(0, unreal.load_asset(MATS + '/M_MW_Ember'))
            light(bp, EMBER, 900.0, 60.0)
        elif name == 'BP_MorrowCurrent':
            gt.shape(bp, unreal.load_asset(cn.MESHES + '/SM_CN_Current'))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
        made.append(name)
    return {'made': made, 'input': sit_input()}


def map_art():
    game.import_file(str(ROOT / 'Art/UI/T_UI_MapMorrow.png'), '/Game/UI')
    texture = unreal.load_asset('/Game/UI/T_UI_MapMorrow')
    if texture is None:
        raise RuntimeError('Art/UI/T_UI_MapMorrow.png did not import')
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    for axis in ('address_x', 'address_y'):
        texture.set_editor_property(axis, unreal.TextureAddress.TA_CLAMP)
    game.save(texture)
    return {'map': [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]}


# ---------------------------------------------------------------- dispatcher

def _module(name):
    import importlib
    module = importlib.import_module(name)
    importlib.reload(module)
    return module


def execute(operation):
    if operation.startswith('exec:'):
        scope = dict(globals())
        exec(open(operation.split(':', 1)[1]).read(), scope)
        return json.dumps(scope.get('RESULT'), default=str)
    if operation == 'materials':
        return json.dumps(materials(), default=str)
    if operation == 'frost_masters':
        return json.dumps(frost_masters(), default=str)
    if operation == 'import' or operation.startswith('import:'):
        return json.dumps(import_meshes(operation.partition(':')[2]), default=str)
    if operation == 'audio':
        return json.dumps(import_audio(), default=str)
    if operation == 'blueprints':
        return json.dumps(blueprints(), default=str)
    if operation == 'input':
        return json.dumps(sit_input(), default=str)
    if operation == 'map_art':
        return json.dumps(map_art(), default=str)
    if operation == 'level':
        return json.dumps(_module('physis_morrow_level').build_level(), default=str)
    if operation.startswith('level:'):
        return json.dumps(_module('physis_morrow_level').execute(operation.split(':', 1)[1]), default=str)
    if operation == 'save':
        _module('physis_morrow_level').save_level()
        return json.dumps({'saved': LEVEL})
    if operation == 'scenario':
        _module('physis_morrow_lore')
        return json.dumps(_module('physis_morrow_scenario').place(_module('physis_morrow_level').Ground()), default=str)
    if operation == 'portal':
        return json.dumps(_module('physis_morrow_scenario').portal(), default=str)
    raise ValueError('unknown morrow operation ' + operation)
