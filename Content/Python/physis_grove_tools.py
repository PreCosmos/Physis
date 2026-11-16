"""Builds level 4, Earth: the Wounded Grove (`outfit_operation grove:*`). Tools/grove/README.md is the contract.

Run order, in a fresh editor (README "Run order"): textures, materials, import, scans, audio, map_art, blueprints,
level (physis_grove_level.py); then the Blueprint logic (Tools/blueprint_logic/grove_logic.py, center_overrides.py,
then grove_hud.py first in a fresh editor); then scenario and portal (physis_grove_scenario.py).

What comes from where: the generated meshes, height.bin and scatter.json from Tools/build_physis_grove.py; the
photo-scanned meshes and scans.json from Tools/grove_scans/process.py; every texture from Tools/grove_scans/prepare.py
(the sets in Art/Scans/Grove/_ready/textures with sets.json, the models' own maps in _ready/models with models.json);
which scan a generated mesh's slot wears from Tools/grove_meshes/looks.py (the table Blender's look-dev renders use
too); text from physis_grove_lore.py; places from physis_grove_plan.py (metres, Unreal axes).

The author's rules for this level (2026-11-10): AAA quality, as realistic as possible. So everything here is
physically based: scanned albedo, normal and roughness maps, real lights through a real atmosphere, Lumen, no
post-process material, natural colours (the Conclave's six-colour palette does not apply on Earth). No 3D text.

Materials (all in /Game/Grove/Materials):
  MPC_Grove      Motion (0.12 before Resonance Link, 1 after), Heal (0 until the Warden falls), Her (Physis's place)
  M_GRSurface    a generated mesh's surface in a scanned set, projected triplanar in object space: 'tint' (the scan,
                 shaded by the vertex colour over its reference colour) or 'paint' (the vertex colour is the paint,
                 the scan its wear and rust)
  M_GRPlain      no scan: vertex colour, roughness and metal (brass, glazed ceramic, the backdrop)
  M_GRGlow       light: the vertex colour times Strength, lifted by a link node's aim (custom primitive data GLOW_DATA)
  M_GRLeaf       a generated plant's leaf cards on a scanned leaf sheet, its solid twigs plain; wind, her passage, the
                 Heartwood's sickness
  M_GRScan       a scanned model's own maps (props, deadwood); M_GRRock the same for rocks and cliffs with a tiling
                 rock detail in world space, so a boulder scaled into a cliff stays sharp; M_GRScanPlant cut-out foliage
  M_GRGround     the terrain: nine scanned layers blended by the vertex weights and their height maps, rock on slopes
  M_GRFalls, M_GRBeam   the waterfall's sheets; the link's beam
  Water is the Conclave's M_CNWater in the grove's colours; glass its M_CNGlass.

Operations: textures, materials, import, import:PREFIX, scans, scans:WORD, audio, blueprints, map_art, level, save,
scenario, portal, exec:PATH.
"""
import importlib.util
import json
import math
import pathlib
import re

import unreal

import physis_center_tools as center
import physis_conclave_ground as cg
import physis_conclave_tools as cn
import physis_gameplay_tools as game
import physis_grove_plan as plan
from physis_center_tools import custom, finish, node, param

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
ART = ROOT / 'Art/Meshes/Grove'
SCAN_ART = ART / 'Scans'
READY = ROOT / 'Art/Scans/Grove/_ready'
GROVE = '/Game/Grove'
MESHES = GROVE + '/Meshes'
SCANS = GROVE + '/Scans'
MATS = GROVE + '/Materials'
TEXTURES = GROVE + '/Textures'
SCAN_TEXTURES = SCANS + '/Textures'
SCAN_MATS = SCANS + '/Materials'
AUDIO = GROVE + '/Audio'
LEVEL = '/Game/Levels/L_Grove'
FOLDER = 'Grove'
CM = 100.0
library = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
PROP = unreal.MaterialProperty
FLOAT1, FLOAT2, FLOAT3, FLOAT4 = (unreal.CustomMaterialOutputType.CMOT_FLOAT1, unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                                  unreal.CustomMaterialOutputType.CMOT_FLOAT3, unreal.CustomMaterialOutputType.CMOT_FLOAT4)
SKIPPED = []     # settings the editor refused, reported by the operation that met them
GLOW_DATA = 4    # custom primitive data index of a glow's lift (BP_LinkNode's aim); 0-3 belong to the shared Blueprints
WHITE = (1.0, 1.0, 1.0)


def _load(name, path):
    """A pure-Python table module under Tools, loaded by its path (the editor's Python path has no Tools folder)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOOKS = _load('physis_grove_looks', 'Tools/grove_meshes/looks.py')


def linear(rgb, alpha=1.0):
    return unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), float(alpha))


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else {}


def sets():
    """The scanned texture sets: {name: {kind, size, tile_m, colour, maps}} (Tools/grove_scans/prepare.py)."""
    return read_json(READY / 'sets.json')


# ---------------------------------------------------------------- material helpers (the Conclave's, without its palette)

def master(name, folder=None, **settings):
    """The material folder/name with an empty graph, made if missing and rebuilt in place (see the Conclave's
    master(): meshes and actors keep their reference)."""
    folder = folder or MATS
    path = folder + '/' + name
    if library.does_asset_exist(path):
        material = unreal.load_asset(path)
        for _ in range(cn.CLEAR_PASSES):
            lib.delete_all_material_expressions(material)
    else:
        material = tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    values = {'material_domain': unreal.MaterialDomain.MD_SURFACE, 'blend_mode': unreal.BlendMode.BLEND_OPAQUE,
              'shading_model': unreal.MaterialShadingModel.MSM_DEFAULT_LIT, 'two_sided': False, 'tangent_space_normal': True}
    values.update(settings)
    for key, value in values.items():
        try:
            material.set_editor_property(key, value)
        except Exception as error:
            SKIPPED.append('%s.%s: %s' % (name, key, error))
    return material


def scalar(material, name, value, x, y):
    return param(material, name, float(value), x, y)


def vector(material, name, rgb, x, y):
    return param(material, name, tuple(float(v) for v in rgb), x, y)


def instance(name, parent, scalars=(), vectors=(), textures=(), switches=(), folder=None):
    """Creates or re-parents folder/name and sets exactly these overrides (stale ones are cleared first)."""
    folder = folder or MATS
    path = folder + '/' + name
    mi = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(mi, parent)
    lib.clear_all_material_instance_parameters(mi)
    for key, value in scalars:
        lib.set_material_instance_scalar_parameter_value(mi, key, float(value))
    for key, value in vectors:
        lib.set_material_instance_vector_parameter_value(mi, key, linear(value[:3], value[3] if len(value) > 3 else 1.0))
    for key, texture in textures:
        lib.set_material_instance_texture_parameter_value(mi, key, texture)
    for key, value in switches:
        lib.set_material_instance_static_switch_parameter_value(mi, key, bool(value))
    lib.update_material_instance(mi)
    game.save(mi)
    return mi


def texture_object(material, name, texture, kind, x, y):
    """A texture-object parameter a Custom node samples: kind 'D' colour, 'N' normal, 'M' linear masks."""
    sampler = {'D': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, 'N': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
               'M': unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]
    return node(material, unreal.MaterialExpressionTextureObjectParameter, x, y, parameter_name=name, texture=texture, sampler_type=sampler)


def texture_sample(material, name, texture, kind, x, y, uv=None):
    """A sampled texture parameter on the mesh's own uv (or `uv`)."""
    sampler = {'D': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, 'N': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
               'M': unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind]
    expression = node(material, unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=name, texture=texture, sampler_type=sampler)
    if uv is not None:
        lib.connect_material_expressions(uv, '', expression, 'UVs')
    return expression


def collection():
    """MPC_Grove (README "Resonance Link"): Motion, Heal and Her, which BP_GroveDirector drives."""
    path = MATS + '/MPC_Grove'
    if library.does_asset_exist(path):
        mpc = unreal.load_asset(path)
    else:
        mpc = tools.create_asset('MPC_Grove', MATS, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    rows = []
    for name, value in (('Motion', .12), ('Heal', 0.0)):
        row = unreal.CollectionScalarParameter()
        row.set_editor_property('parameter_name', name)
        row.set_editor_property('default_value', value)
        rows.append(row)
    have = {str(r.get_editor_property('parameter_name')) for r in mpc.get_editor_property('scalar_parameters')}
    if have != {'Motion', 'Heal'}:
        mpc.set_editor_property('scalar_parameters', rows)
    her = unreal.CollectionVectorParameter()
    her.set_editor_property('parameter_name', 'Her')
    her.set_editor_property('default_value', unreal.LinearColor(0.0, 0.0, -1000000.0, 0.0))
    if {str(r.get_editor_property('parameter_name')) for r in mpc.get_editor_property('vector_parameters')} != {'Her'}:
        mpc.set_editor_property('vector_parameters', [her])
    game.save(mpc)
    return mpc


def mpc_value(material, name, x, y):
    """Motion, Heal or Her read from MPC_Grove (the collection is set before the name, which resolves its id)."""
    return node(material, unreal.MaterialExpressionCollectionParameter, x, y, collection=unreal.load_asset(MATS + '/MPC_Grove'),
                parameter_name=name)


def scan_texture(set_name, kind):
    """T_GRS_<set>_<kind> ('D', 'N' or 'ARM'), imported by grove:textures."""
    texture = unreal.load_asset('%s/T_GRS_%s_%s' % (TEXTURES, set_name, kind))
    if texture is None:
        raise RuntimeError('T_GRS_%s_%s is missing: run Tools/grove_scans/prepare.py, then grove:textures' % (set_name, kind))
    return texture


# ---------------------------------------------------------------- textures

def settle_texture(texture, kind, report=None):
    """Import settings by what the map is: 'D' colour, 'DM' colour with a cutout in alpha (mips keep the cutout's
    coverage, so leaves do not thin out with distance), 'DH' colour with a height map in alpha, 'N' a normal map,
    'ARM' linear masks, 'E' emissive colour."""
    colour = kind in ('D', 'DM', 'DH', 'E')
    texture.set_editor_property('srgb', colour)
    if kind == 'N':
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
    elif kind == 'ARM':
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
    else:
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
        texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
    if kind == 'DM':
        for key, value in (('do_scale_mips_for_alpha_coverage', True), ('alpha_coverage_thresholds', unreal.Vector4(0.0, 0.0, 0.0, .5))):
            try:
                texture.set_editor_property(key, value)
            except Exception as error:
                if report is not None:
                    report.append('%s.%s: %s' % (texture.get_name(), key, error))
    game.save(texture)
    return texture


def import_textures(word=''):
    """Every scanned set's maps into /Game/Grove/Textures."""
    report = {'sets': 0, 'missing': [], 'skipped': []}
    for name, row in sorted(sets().items()):
        if word and word.lower() not in name.lower():
            continue
        for key, file in row['maps'].items():
            source = READY / 'textures' / file
            if not source.exists():
                report['missing'].append(file)
                continue
            game.import_file(str(source), TEXTURES)
            texture = unreal.load_asset('%s/%s' % (TEXTURES, source.stem))
            if texture is None:
                report['missing'].append(file)
                continue
            kind = key if key != 'D' else {'ground': 'DH', 'leaf': 'DM'}.get(row['kind'], 'D')
            settle_texture(texture, kind, report['skipped'])
        report['sets'] += 1
    return report


# ---------------------------------------------------------------- HLSL (Custom nodes cannot declare functions)

# One scan projected on the three object planes. The side planes run v down the object (uv = y or x, -z), so a
# wall's rain streaks and a trunk's furrows run the way they were photographed; Rnd shifts the pattern per object.
TRI_FRAME = '''float3 n = normalize(LN);
float3 w = pow(abs(n), Sharp);
w /= max(w.x + w.y + w.z, 0.0001);
float3 p = LP / max(Tile, 1.0) + frac(Rnd * float3(13.17, 7.31, 3.77)) * 5.0;
float2 ux = float2(p.y, -p.z), uy = float2(p.x, -p.z), uz = p.xy;
'''
TRI_COLOUR = TRI_FRAME + '''ARM = (Texture2DSample(TexA, TexASampler, ux) * w.x + Texture2DSample(TexA, TexASampler, uy) * w.y
    + Texture2DSample(TexA, TexASampler, uz) * w.z).rgb;
return Texture2DSample(TexD, TexDSampler, ux) * w.x + Texture2DSample(TexD, TexDSampler, uy) * w.y + Texture2DSample(TexD, TexDSampler, uz) * w.z;'''
# The maps are DirectX-convention tangent normals: x along u, y along v (down the image). Each plane's map bends the
# object normal in that plane's own axes (whiteout blend), whichever way the face looks.
TRI_NORMAL = TRI_FRAME + '''float2 ax = (Texture2DSample(TexN, TexNSampler, ux).rg * 2.0 - 1.0) * K;
float2 ay = (Texture2DSample(TexN, TexNSampler, uy).rg * 2.0 - 1.0) * K;
float2 az = (Texture2DSample(TexN, TexNSampler, uz).rg * 2.0 - 1.0) * K;
float3 bx = float3(n.x * sqrt(saturate(1.0 - dot(ax, ax))), n.y + ax.x, n.z - ax.y);
float3 by = float3(n.x + ay.x, n.y * sqrt(saturate(1.0 - dot(ay, ay))), n.z - ay.y);
float3 bz = float3(n.x + az.x, n.y + az.y, n.z * sqrt(saturate(1.0 - dot(az, az))));
return normalize(bx * w.x + by * w.y + bz * w.z);'''

# M_GRSurface's colour. Tint: the scan, pulled toward the slot's reference colour by Balance (scans of one material
# differ in hue; the level keeps one concrete) and shaded by the vertex colour over that reference, so the weathering
# a generator painted darkens it. Paint: the vertex colour is the paint and the scan gives its wear (brightness over
# the scan's mean); saturated orange texels are rust and stay as scanned. Two slow octaves of noise then move the
# tone, so a wall 50 m long is not one texture repeated.
SURFACE = (cn.value_noise('nm', 'LP / max(MacroScale, 1.0) + Rnd * 5.3') +
           cn.value_noise('nn', 'LP / max(MacroScale * 0.27, 1.0) + Rnd * 9.1 + float3(4.1, 2.7, 6.3)') +
           '''float3 scan = D.rgb;
float3 mean = max(Mean.rgb, 0.004);
float3 ref = max(Ref.rgb, 0.02);
float3 tinted = scan * lerp(float3(1.0, 1.0, 1.0), ref / mean, Balance) * clamp(VC.rgb / ref, 0.0, 2.5);
float luma = dot(scan, float3(0.3, 0.59, 0.11));
float mx = max(scan.r, max(scan.g, scan.b)), mn = min(scan.r, min(scan.g, scan.b));
float sat = (mx - mn) / max(mx, 0.0001);
float rust = smoothstep(RustLo, RustHi, sat) * step(scan.b, scan.g) * step(scan.g, scan.r);
float wear = clamp(luma / max(dot(mean, float3(0.3, 0.59, 0.11)), 0.004), 0.0, 1.3);
float3 painted = lerp(VC.rgb * wear, scan, rust);
float3 col = lerp(tinted, painted, Paint) * Tint.rgb;
col *= 1.0 + Macro * ((nm - 0.5) * 1.4 + (nn - 0.5) * 0.6);
col *= lerp(1.0, A.r, Cavity);
float peak = max(col.r, max(col.g, col.b));
col *= min(1.0, 0.92 / max(peak, 0.0001));
Metal = saturate(A.b * MetalScale);
Occlusion = lerp(1.0, A.r, 0.85);
return float4(col, saturate(A.g * RoughScale + RoughBias + 0.08 * (nn - 0.5)));''')

PLAIN = (cn.value_noise('na', 'LP / max(Scale, 1.0) + Rnd * 37.13') + '''float3 col = VC.rgb * Tint.rgb * (1.0 + Var * (na - 0.5) * 2.0);
float peak = max(col.r, max(col.g, col.b));
col *= min(1.0, 0.92 / max(peak, 0.0001));
return float4(col, saturate(R0 + RVar * (na - 0.5) * 2.0));''')

# M_GRLeaf. Cards (vertex alpha 0) show their spray of the scanned sheet, tinted by the vertex colour; solid twigs and
# stems (alpha 1) are their vertex colour. Each plant has its own tone, and the valley's drifts in slow patches. A
# sick crown (Sick, the Heartwood's, until the grove heals) yellows and thins.
LEAF = (cn.value_noise('na', 'WP / 900.0') + cn.value_noise('nb', 'LP / 55.0 + Rnd * 3.1') +
        '''float card = 1.0 - saturate(VA * 2.0);
float sick = Sick * (1.0 - saturate(Heal));
float3 leaf = S.rgb * VC.rgb * Gain;
leaf *= 1.0 + Var * ((frac(Rnd * 7.13) - 0.5) * 1.3 + (na - 0.5) * 0.9);
leaf = lerp(leaf, leaf * Warm.rgb, saturate(frac(Rnd * 3.71) * 1.4 - 0.2));
float grey = dot(leaf, float3(0.3, 0.59, 0.11));
leaf = lerp(leaf, grey * SickColour.rgb * 2.4, sick * 0.85);
float3 col = lerp(VC.rgb, leaf, card);
float peak = max(col.r, max(col.g, col.b));
col *= min(1.0, 0.9 / max(peak, 0.0001));
Mask = lerp(1.0, S.a - sick * Thin * smoothstep(0.3, 0.7, nb), card);
Light = leaf * Sub.rgb * SubK * card;
return float4(col, lerp(SolidRough, saturate(A.g * RoughScale), card));''')
LEAF_NORMAL = 'return normalize(lerp(float3(0.0, 0.0, 1.0), N.rgb, K * (1.0 - saturate(VA * 2.0))));'
LEAF_OPACITY = 'return lerp(Solid, Card, 1.0 - saturate(VA * 2.0));'
# Wind: a sway that grows with the square root of the height and a flutter on the cards, both scaled by Motion (the
# grove barely stirs before she learns the link). Her passage: low growth within Reach of her is pushed away from her
# and pressed down (Part: 1 for ground cover, 0 for crowns).
WIND = '''float h = max(LP.z, 0.0) / 100.0;
float t = T * Speed + dot(WP.xy, float2(0.0021, 0.0017));
float gust = 0.6 + 0.4 * sin(T * 0.37 + WP.x * 0.0004);
float sway = Amount * sqrt(h) * (sin(t) * 0.7 + sin(t * 2.3 + 1.7) * 0.3) * gust;
float flutter = Flutter * saturate(h * 3.0) * Card * sin(T * 9.0 + dot(WP, float3(0.13, 0.07, 0.11)));
float3 off = float3(0.92 * sway + 0.4 * flutter, 0.39 * sway - 0.3 * flutter, flutter) * lerp(Still, 1.0, saturate(Motion));
float2 d = WP.xy - Her.xy;
float dist = length(d);
float press = Part * saturate(1.0 - dist / max(Reach, 1.0)) * saturate(1.0 - abs(WP.z - Her.z) / 250.0) * saturate(h * 2.5);
off.xy += d / max(dist, 1.0) * press * Push;
off.z -= press * Push * 0.45;
return off;'''

SCAN = '''float3 col = D.rgb * Tint.rgb * (1.0 + Var * (frac(Rnd * 5.37) - 0.5) * 2.0);
float peak = max(col.r, max(col.g, col.b));
col *= min(1.0, 0.92 / max(peak, 0.0001));
return float4(col, saturate(A.g * RoughScale));'''
# M_GRRock: the scan's colour and relief, and over it a tiling rock set in world space, which carries the close-up
# detail a 2k scan stretched over a 30 m cliff cannot (its brightness over its mean scales the colour, its normal adds
# to the scan's). Moss gathers on what faces up.
ROCK_FRAME = '''float3 n = normalize(VN);
float3 w = pow(abs(n), 4.0);
w /= max(w.x + w.y + w.z, 0.0001);
float3 p = WP / max(Tile, 1.0);
float2 ux = float2(p.y, -p.z), uy = float2(p.x, -p.z), uz = p.xy;
'''
ROCK = ROCK_FRAME + cn.value_noise('nm', 'WP / 260.0') + '''float3 det = (Texture2DSample(TexD, TexDSampler, ux) * w.x + Texture2DSample(TexD, TexDSampler, uy) * w.y
    + Texture2DSample(TexD, TexDSampler, uz) * w.z).rgb;
float rel = dot(det, float3(0.3, 0.59, 0.11)) / max(dot(Mean.rgb, float3(0.3, 0.59, 0.11)), 0.004);
float3 col = D.rgb * Tint.rgb * lerp(1.0, clamp(rel, 0.4, 1.8), Detail) * (1.0 + Var * (frac(Rnd * 5.37) - 0.5) * 2.0);
float up = saturate((normalize(PN).z - MossFrom) / max(1.0 - MossFrom, 0.01));
float moss = Moss * smoothstep(0.25, 0.75, up * (0.55 + 0.9 * nm));
col = lerp(col, MossColour.rgb * (0.7 + 0.6 * det.g / max(Mean.g, 0.004)), moss);
float peak = max(col.r, max(col.g, col.b));
col *= min(1.0, 0.92 / max(peak, 0.0001));
return float4(col, saturate(lerp(A.g * RoughScale, 0.92, moss)));'''
ROCK_NORMAL = ROCK_FRAME + '''float2 ax = (Texture2DSample(TexN, TexNSampler, ux).rg * 2.0 - 1.0) * K;
float2 ay = (Texture2DSample(TexN, TexNSampler, uy).rg * 2.0 - 1.0) * K;
float2 az = (Texture2DSample(TexN, TexNSampler, uz).rg * 2.0 - 1.0) * K;
float3 m = normalize(PN);
float3 bx = float3(m.x * sqrt(saturate(1.0 - dot(ax, ax))), m.y + ax.x, m.z - ax.y);
float3 by = float3(m.x + ay.x, m.y * sqrt(saturate(1.0 - dot(ay, ay))), m.z - ay.y);
float3 bz = float3(m.x + az.x, m.y + az.y, m.z * sqrt(saturate(1.0 - dot(az, az))));
return normalize(bx * w.x + by * w.y + bz * w.z);'''

PLANT = (cn.value_noise('na', 'WP / 900.0') + '''float3 leaf = D.rgb * Tint.rgb * Gain;
leaf *= 1.0 + Var * ((frac(Rnd * 7.13) - 0.5) * 1.3 + (na - 0.5) * 0.9);
float peak = max(leaf.r, max(leaf.g, leaf.b));
leaf *= min(1.0, 0.9 / max(peak, 0.0001));
Light = leaf * Sub.rgb * SubK;
return float4(leaf, saturate(A.g * RoughScale));''')

FALLS = (cn.value_noise2('n1', 'float2(UV.x * 9.0, UV.y * 2.2 - T * Speed)') +
         cn.value_noise2('n2', 'float2(UV.x * 23.0 + 3.7, UV.y * 5.5 - T * Speed * 1.7)') +
         cn.value_noise2('n3', 'float2(UV.x * 3.0 + 9.1, UV.y * 0.8 - T * Speed * 0.6)') +
         '''float streak = saturate(n1 * 0.55 + n2 * 0.35 + n3 * 0.45 - 0.22);
float ends = smoothstep(0.0, 0.25, UV.y) * (1.0 - 0.35 * smoothstep(2.2, 3.0, UV.y));
Opacity = saturate(streak * 1.6 + 0.12) * ends * Density;
return lerp(Deep.rgb, Foam.rgb, saturate(streak * 1.5));''')

BEAM = (cn.value_noise2('n1', 'float2(UV.x * 5.0, UV.y * Length / 90.0 - T * 2.6)') +
        cn.value_noise2('n2', 'float2(UV.x * 11.0 + 5.3, UV.y * Length / 35.0 - T * 5.1)') +
        '''float core = pow(saturate(1.0 - F), 2.2);
float flow = 0.55 + 0.9 * n1 * n2;
float ends = smoothstep(0.0, 0.04, UV.y) * smoothstep(1.0, 0.96, UV.y);
return C.rgb * (core * flow * ends * Strength * max(C.a, 0.0));''')


# ---------------------------------------------------------------- materials

SURFACE_DEFAULTS = (('Tile', 300.0), ('TriSharpness', 5.0), ('NormalStrength', 1.0), ('Paint', 0.0), ('Balance', .5), ('RustLo', .28),
                    ('RustHi', .5), ('MacroScale', 900.0), ('MacroVariation', .14), ('Cavity', .35), ('MetalScale', 0.0), ('RoughScale', 1.0),
                    ('RoughBias', 0.0), ('Specular', .5))


def material_surface():
    m = master('M_GRSurface', tangent_space_normal=False, used_with_instanced_static_meshes=True, used_with_skeletal_mesh=True)
    vc = node(m, unreal.MaterialExpressionVertexColor, -1900, -500)
    lp = node(m, unreal.MaterialExpressionLocalPosition, -1900, -380)
    rnd = cn.object_random(m, -2100, -260)
    ln = cn.transform(m, node(m, unreal.MaterialExpressionVertexNormalWS, -1900, 700), cn.WORLD_TO_LOCAL, -1650, 700)
    values = {name: scalar(m, name, value, -1650, -500 + i * 80) for i, (name, value) in enumerate(SURFACE_DEFAULTS)}
    tex_d = texture_object(m, 'ScanColour', scan_texture('SConcrete', 'D'), 'D', -2400, -900)
    tex_n = texture_object(m, 'ScanNormal', scan_texture('SConcrete', 'N'), 'N', -2400, -750)
    tex_a = texture_object(m, 'ScanMasks', scan_texture('SConcrete', 'ARM'), 'M', -2400, -600)
    frame = [('LP', lp), ('LN', ln), ('Tile', values['Tile']), ('Sharp', values['TriSharpness']), ('Rnd', rnd)]
    tri = cg.custom_outputs(custom(m, TRI_COLOUR, frame + [('TexD', tex_d), ('TexA', tex_a)], -1300, -900, FLOAT4), [('ARM', FLOAT3)])
    surf = cg.custom_outputs(custom(m, SURFACE, [
        ('VC', vc), ('D', tri), ('A', (tri, 'ARM')), ('LP', lp), ('Rnd', rnd), ('Mean', vector(m, 'ScanMean', (.3, .3, .3), -1300, 300)),
        ('Ref', vector(m, 'Reference', (.4, .4, .4), -1300, 400)), ('Tint', vector(m, 'Tint', WHITE, -1300, 500)),
        ('Balance', values['Balance']), ('Paint', values['Paint']), ('RustLo', values['RustLo']), ('RustHi', values['RustHi']),
        ('MacroScale', values['MacroScale']), ('Macro', values['MacroVariation']), ('Cavity', values['Cavity']),
        ('MetalScale', values['MetalScale']), ('RoughScale', values['RoughScale']), ('RoughBias', values['RoughBias'])],
        -900, -400, FLOAT4), [('Metal', FLOAT1), ('Occlusion', FLOAT1)])
    lib.connect_material_property(cn.mask(m, surf, 'rgb', -500, -450), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, surf, 'a', -500, -330), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(surf, 'Metal', PROP.MP_METALLIC)
    lib.connect_material_property(surf, 'Occlusion', PROP.MP_AMBIENT_OCCLUSION)
    lib.connect_material_property(values['Specular'], '', PROP.MP_SPECULAR)
    normal = custom(m, TRI_NORMAL, frame + [('TexN', tex_n), ('K', values['NormalStrength'])], -1300, 700, FLOAT3)
    lib.connect_material_property(cn.transform(m, normal, cn.LOCAL_TO_WORLD, -900, 700), '', PROP.MP_NORMAL)
    return finish(m)


def material_plain():
    m = master('M_GRPlain', used_with_instanced_static_meshes=True, used_with_skeletal_mesh=True)
    surf = custom(m, PLAIN, [('VC', node(m, unreal.MaterialExpressionVertexColor, -1200, -300)),
                             ('LP', node(m, unreal.MaterialExpressionLocalPosition, -1200, -200)), ('Rnd', cn.object_random(m, -1400, -100)),
                             ('Tint', vector(m, 'Tint', WHITE, -1200, 50)), ('Var', scalar(m, 'AlbedoVariation', .06, -1200, 150)),
                             ('Scale', scalar(m, 'DetailScale', 40.0, -1200, 230)), ('R0', scalar(m, 'Roughness', .5, -1200, 310)),
                             ('RVar', scalar(m, 'RoughnessVariation', .06, -1200, 390))], -700, -200, FLOAT4)
    lib.connect_material_property(cn.mask(m, surf, 'rgb', -350, -250), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, surf, 'a', -350, -130), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(scalar(m, 'Metallic', 0.0, -350, 0), '', PROP.MP_METALLIC)
    lib.connect_material_property(scalar(m, 'Specular', .5, -350, 100), '', PROP.MP_SPECULAR)
    return finish(m)


def material_glow():
    """Light from the vertex colour. A link node lifts its own seed while it is aimed at: custom primitive data
    GLOW_DATA holds the lift (0 on everything that never sets it)."""
    m = master('M_GRGlow', used_with_instanced_static_meshes=True, used_with_skeletal_mesh=True)
    vc = node(m, unreal.MaterialExpressionVertexColor, -900, -100)
    lift = node(m, unreal.MaterialExpressionScalarParameter, -900, 150, parameter_name='Lift', default_value=0.0,
                use_custom_primitive_data=True, primitive_data_index=GLOW_DATA)
    glow = custom(m, 'return VC.rgb * Strength * (1.0 + Lift);', [('VC', vc), ('Strength', scalar(m, 'Strength', 24.0, -900, 50)), ('Lift', lift)],
                  -500, 0, FLOAT3)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(node(m, unreal.MaterialExpressionConstant3Vector, -500, -200, constant=unreal.LinearColor(0.0, 0.0, 0.0, 1.0)),
                                  '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(scalar(m, 'Roughness', .35, -500, 200), '', PROP.MP_ROUGHNESS)
    return finish(m)


LEAF_DEFAULTS = (('Gain', 1.25), ('AlbedoVariation', .16), ('Sick', 0.0), ('Thin', .45), ('SubsurfaceStrength', 1.1), ('SolidRoughness', .7),
                 ('RoughScale', 1.0), ('Specular', .5), ('CardNormal', .7), ('CardSubsurfaceOpacity', .25), ('SolidSubsurfaceOpacity', .6),
                 ('WindSpeed', 1.1), ('WindAmount', 2.4), ('Flutter', .7), ('Still', .2), ('Part', 0.0), ('Reach', 130.0), ('Push', 28.0))


def foliage_settings():
    return dict(two_sided=True, shading_model=unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE, used_with_instanced_static_meshes=True,
                blend_mode=unreal.BlendMode.BLEND_MASKED, opacity_mask_clip_value=.4, dithered_lod_transition=True)


def wind(m, values, card, x, y):
    return custom(m, WIND, [('LP', node(m, unreal.MaterialExpressionLocalPosition, x - 600, y)),
                            ('WP', node(m, unreal.MaterialExpressionWorldPosition, x - 600, y + 100)),
                            ('T', node(m, unreal.MaterialExpressionTime, x - 600, y + 200)), ('Speed', values['WindSpeed']),
                            ('Amount', values['WindAmount']), ('Flutter', values['Flutter']), ('Still', values['Still']), ('Card', card),
                            ('Motion', mpc_value(m, 'Motion', x - 600, y + 300)), ('Her', mpc_value(m, 'Her', x - 600, y + 400)),
                            ('Part', values['Part']), ('Reach', values['Reach']), ('Push', values['Push'])], x, y, FLOAT3)


def material_leaf():
    m = master('M_GRLeaf', **foliage_settings())
    vc = node(m, unreal.MaterialExpressionVertexColor, -1700, -300)
    va = (vc, 'A')
    rnd = cn.object_random(m, -1900, -150)
    sheet = texture_sample(m, 'Sheet', scan_texture('LBroadleaf', 'D'), 'D', -1700, -700)
    sheet_n = texture_sample(m, 'SheetNormal', scan_texture('LBroadleaf', 'N'), 'N', -1700, 800)
    sheet_a = texture_sample(m, 'SheetMasks', scan_texture('LBroadleaf', 'ARM'), 'M', -1700, -500)
    values = {name: scalar(m, name, value, -1400, -300 + i * 80) for i, (name, value) in enumerate(LEAF_DEFAULTS)}
    leaf = cg.custom_outputs(custom(m, LEAF, [
        ('VC', vc), ('VA', va), ('S', (sheet, 'RGBA')), ('A', sheet_a), ('Rnd', rnd),
        ('LP', node(m, unreal.MaterialExpressionLocalPosition, -1700, -50)), ('WP', node(m, unreal.MaterialExpressionWorldPosition, -1700, 50)),
        ('Heal', mpc_value(m, 'Heal', -1700, 150)), ('Gain', values['Gain']), ('Var', values['AlbedoVariation']), ('Sick', values['Sick']),
        ('Thin', values['Thin']), ('Warm', vector(m, 'WarmTint', (1.12, 1.0, .72), -1100, 300)),
        ('SickColour', vector(m, 'SickColour', (.36, .30, .09), -1100, 400)), ('Sub', vector(m, 'SubsurfaceTint', (.85, 1.0, .45), -1100, 500)),
        ('SubK', values['SubsurfaceStrength']), ('SolidRough', values['SolidRoughness']), ('RoughScale', values['RoughScale'])],
        -700, -300, FLOAT4), [('Mask', FLOAT1), ('Light', FLOAT3)])
    lib.connect_material_property(cn.mask(m, leaf, 'rgb', -350, -350), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, leaf, 'a', -350, -230), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(leaf, 'Mask', PROP.MP_OPACITY_MASK)
    lib.connect_material_property(leaf, 'Light', PROP.MP_SUBSURFACE_COLOR)
    lib.connect_material_property(values['Specular'], '', PROP.MP_SPECULAR)
    lib.connect_material_property(custom(m, LEAF_OPACITY, [('VA', va), ('Card', values['CardSubsurfaceOpacity']),
                                                           ('Solid', values['SolidSubsurfaceOpacity'])], -700, 150, FLOAT1), '', PROP.MP_OPACITY)
    lib.connect_material_property(custom(m, LEAF_NORMAL, [('N', sheet_n), ('VA', va), ('K', values['CardNormal'])], -700, 800, FLOAT3),
                                  '', PROP.MP_NORMAL)
    card = custom(m, 'return 1.0 - saturate(VA * 2.0);', [('VA', va)], -1400, 1300, FLOAT1)
    lib.connect_material_property(wind(m, values, card, -700, 1300), '', PROP.MP_WORLD_POSITION_OFFSET)
    return finish(m)


def scan_inputs(m, x, y):
    """A scanned model's own maps on its own uv (the defaults are a rock's; every instance names its own)."""
    return (texture_sample(m, 'Colour', scan_texture('SRock', 'D'), 'D', x, y), texture_sample(m, 'Normal', scan_texture('SRock', 'N'), 'N', x, y + 250),
            texture_sample(m, 'Masks', scan_texture('SRock', 'ARM'), 'M', x, y + 500))


def material_scan():
    m = master('M_GRScan', used_with_instanced_static_meshes=True)
    colour, normal, masks = scan_inputs(m, -1500, -500)
    surf = custom(m, SCAN, [('D', colour), ('A', masks), ('Rnd', cn.object_random(m, -1500, 400)), ('Tint', vector(m, 'Tint', WHITE, -1200, 400)),
                            ('Var', scalar(m, 'InstanceVariation', .05, -1200, 500)), ('RoughScale', scalar(m, 'RoughScale', 1.0, -1200, 580))],
                  -800, -300, FLOAT4)
    lib.connect_material_property(cn.mask(m, surf, 'rgb', -450, -350), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, surf, 'a', -450, -230), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(cn.mask(m, masks, 'b', -450, -110), '', PROP.MP_METALLIC)
    lib.connect_material_property(cn.mask(m, masks, 'r', -450, 10), '', PROP.MP_AMBIENT_OCCLUSION)
    lib.connect_material_property(normal, '', PROP.MP_NORMAL)
    # A lamp's or a sign's own light: only instances that turn Emissive on sample the map.
    glow = texture_sample(m, 'Emissive', scan_texture('SRock', 'D'), 'D', -1500, 900)
    lit = cn.multiply(m, glow, scalar(m, 'EmissiveStrength', 8.0, -1500, 1150), -1100, 950)
    switch = node(m, unreal.MaterialExpressionStaticSwitchParameter, -700, 950, parameter_name='Emissive', default_value=False)
    lib.connect_material_expressions(lit, '', switch, 'True')
    lib.connect_material_expressions(node(m, unreal.MaterialExpressionConstant3Vector, -1100, 1150, constant=unreal.LinearColor(0.0, 0.0, 0.0, 1.0)),
                                     '', switch, 'False')
    lib.connect_material_property(switch, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def material_rock():
    m = master('M_GRRock', tangent_space_normal=False, used_with_instanced_static_meshes=True)
    colour, normal, masks = scan_inputs(m, -1900, -600)
    wp = node(m, unreal.MaterialExpressionWorldPosition, -1900, 300)
    vn = node(m, unreal.MaterialExpressionVertexNormalWS, -1900, 400)
    pixel = cn.transform(m, normal, cn.TANGENT_TO_WORLD, -1550, -350)   # the scan's own relief, in world space
    tile = scalar(m, 'DetailTile', 220.0, -1500, 500)
    tex_d = texture_object(m, 'DetailColour', scan_texture('SRock', 'D'), 'D', -1900, 600)
    tex_n = texture_object(m, 'DetailNormal', scan_texture('SRock', 'N'), 'N', -1900, 750)
    surf = custom(m, ROCK, [('WP', wp), ('VN', vn), ('PN', pixel), ('Tile', tile), ('TexD', tex_d), ('D', colour), ('A', masks),
                            ('Rnd', cn.object_random(m, -1900, 900)), ('Mean', vector(m, 'DetailMean', (.2, .14, .08), -1500, 600)),
                            ('Tint', vector(m, 'Tint', WHITE, -1500, 700)), ('Detail', scalar(m, 'DetailAmount', .55, -1500, 800)),
                            ('Var', scalar(m, 'InstanceVariation', .07, -1500, 880)), ('Moss', scalar(m, 'Moss', 0.0, -1500, 960)),
                            ('MossFrom', scalar(m, 'MossFrom', .45, -1500, 1040)), ('MossColour', vector(m, 'MossColour', (.05, .085, .02), -1500, 1120)),
                            ('RoughScale', scalar(m, 'RoughScale', 1.0, -1500, 1220))], -1000, -300, FLOAT4)
    lib.connect_material_property(cn.mask(m, surf, 'rgb', -600, -350), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, surf, 'a', -600, -230), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(cn.mask(m, masks, 'r', -600, -110), '', PROP.MP_AMBIENT_OCCLUSION)
    bent = custom(m, ROCK_NORMAL, [('WP', wp), ('VN', vn), ('PN', pixel), ('Tile', tile), ('TexN', tex_n),
                                   ('K', scalar(m, 'DetailNormalStrength', .6, -1500, 1300))], -1000, 400, FLOAT3)
    lib.connect_material_property(bent, '', PROP.MP_NORMAL)
    return finish(m)


PLANT_DEFAULTS = (('Gain', 1.2), ('AlbedoVariation', .14), ('SubsurfaceStrength', 1.0), ('RoughScale', 1.0), ('Specular', .5),
                  ('SubsurfaceOpacity', .3), ('WindSpeed', 1.2), ('WindAmount', 2.0), ('Flutter', .5), ('Still', .2), ('Part', 1.0),
                  ('Reach', 130.0), ('Push', 28.0))


def material_scan_plant():
    m = master('M_GRScanPlant', **foliage_settings())
    colour, normal, masks = scan_inputs(m, -1700, -600)
    values = {name: scalar(m, name, value, -1400, -300 + i * 80) for i, (name, value) in enumerate(PLANT_DEFAULTS)}
    leaf = cg.custom_outputs(custom(m, PLANT, [
        ('D', colour), ('A', masks), ('Rnd', cn.object_random(m, -1700, 300)), ('WP', node(m, unreal.MaterialExpressionWorldPosition, -1700, 450)),
        ('Tint', vector(m, 'Tint', WHITE, -1100, 300)), ('Gain', values['Gain']), ('Var', values['AlbedoVariation']),
        ('Sub', vector(m, 'SubsurfaceTint', (.85, 1.0, .45), -1100, 400)), ('SubK', values['SubsurfaceStrength']),
        ('RoughScale', values['RoughScale'])], -700, -300, FLOAT4), [('Light', FLOAT3)])
    lib.connect_material_property(cn.mask(m, leaf, 'rgb', -350, -350), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, leaf, 'a', -350, -230), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(colour, 'A', PROP.MP_OPACITY_MASK)
    lib.connect_material_property(leaf, 'Light', PROP.MP_SUBSURFACE_COLOR)
    lib.connect_material_property(values['SubsurfaceOpacity'], '', PROP.MP_OPACITY)
    lib.connect_material_property(values['Specular'], '', PROP.MP_SPECULAR)
    lib.connect_material_property(normal, '', PROP.MP_NORMAL)
    one = node(m, unreal.MaterialExpressionConstant, -1400, 1300, r=1.0)
    lib.connect_material_property(wind(m, values, one, -700, 1300), '', PROP.MP_WORLD_POSITION_OFFSET)
    return finish(m)


# The terrain's layers: (key, set, roughness, (tint r, g, b, saturation)). The scans are graded toward one valley:
# the moss scan is a bright yellow-green and the dirt a pale ochre beside a forest floor four times darker; asphalt
# and cliff rock lose most of their red.
GROUND_LAYERS = (('Forest', 'GForest', .88, (1.0, 1.0, 1.0, 1.0)), ('Litter', 'GLitter', .86, (.8, .82, .8, .9)),
                 ('Moss', 'GMoss', .9, (.36, .47, .4, 1.0)), ('Grass', 'GGrass', .84, (.5, .56, .42, .85)),
                 ('Gravel', 'GGravel', .62, (.95, .97, 1.0, .8)), ('Dirt', 'GDirt', .86, (.62, .6, .58, .9)),
                 ('Asphalt', 'GAsphalt', .7, (1.25, 1.3, 1.35, .3)), ('Blight', 'GBlight', .8, (.5, .42, .47, .6)),
                 ('Rock', 'GRock', .78, (.32, .37, .37, .5)))
TOP_LAYERS = tuple(row[0] for row in GROUND_LAYERS if row[0] != 'Rock')
GROUND_WEIGHT = {'Forest': '(1.0 - wLitter)', 'Litter': 'wLitter', 'Moss': 'wMoss', 'Grass': 'wGrass', 'Gravel': 'wGravel', 'Dirt': 'wDirt',
                 'Asphalt': 'wAsphalt', 'Blight': 'wBlight'}


def ground_code():
    """M_GRGround's one Custom node: colour and roughness (return), Normal (world space) and Glow.
    The tiles' vertices carry the layers' weights (Tools/grove_meshes/land.py): colour R grass, G dirt, B gravel,
    A 1 - blight; uv0 u asphalt, v moss; what is left is forest floor, which a slow noise turns to leaf litter in
    patches; rock takes over with the slope. A layer is only sampled where its weight is above nothing (explicit
    gradients, so the taps may sit in branches), through the view's shared wrap sampler (18 textures). Layers meet
    by their height maps: a layer's high texels come through first, so edges are a few centimetres of real detail.
    """
    rough = {key: value for key, _, value, _ in GROUND_LAYERS}
    code = ('float2 p = WP.xy;\nfloat2 dpx = DDX(p), dpy = DDY(p);\nfloat3 n = normalize(VN);\n' +
            cn.value_noise2('n1', 'p / 4000.0 + float2(1.7, 8.3)') + cn.value_noise2('n2', 'p / 16000.0 + float2(6.1, 2.9)') +
            cn.value_noise2('n3', 'p / 900.0 + float2(3.3, 5.1)') + cn.value_noise2('wa', 'p / 750.0 + float2(9.7, 1.3)') +
            cn.value_noise2('wb', 'p / 750.0 + float2(2.1, 7.9)') + cn.value_noise2('wm', 'p / 310.0 + float2(4.4, 6.2)') +
            cn.value_noise2('wr', 'p / 1100.0 + WP.z / 800.0 + float2(5.5, 0.7)') + '''float heal = saturate(Heal);
// Against tiling: every layer's uv is pushed about by a slow noise (its grid lines wander instead of running straight)
// and its colour is shaded by the same scan five times larger, so no two tiles of a wide floor are alike.
float2 warp = float2(wa, wb) - 0.5;
// And each layer is two layings of its scan, the second turned a quarter and a little larger, changing over in
// patches a few metres across: the eye finds no row or column to follow.
float mixm = smoothstep(0.38, 0.62, wm + 0.3 * (n3 - 0.5));
float wGrass = VC.r, wDirt = VC.g, wGravel = VC.b, wBlight = (1.0 - VA) * (1.0 - heal);
float wAsphalt = UV.x, wMoss = UV.y;
float wLitter = smoothstep(0.40, 0.62, n3 + 0.25 * (n1 - 0.5));
float slope = sqrt(saturate(1.0 - n.z * n.z)) / max(n.z, 0.05);
float wRock = smoothstep(RockLo, RockHi, slope);
float keep = 1.0 - wRock;
''')
    for key in TOP_LAYERS:
        code += ('float4 c{k} = float4(0.1, 0.1, 0.1, 0.5); float2 g{k} = float2(0.0, 0.0);\n'
                 'BRANCH if ({w} * keep > 0.004)\n{{\n    float2 uv = p / Tile{k} + warp * 0.9;\n    c{k} = {d};\n    g{k} = {n}.rg * 2.0 - 1.0;\n'
                 '    float2 uw = float2(-uv.y, uv.x) * 0.83 + float2(0.31, 0.67);\n'
                 '    float2 wdx = float2(-dpx.y, dpx.x) * (0.83 / Tile{k}), wdy = float2(-dpy.y, dpy.x) * (0.83 / Tile{k});\n'
                 '    float2 h{k} = {n2}.rg * 2.0 - 1.0;\n'
                 '    c{k} = lerp(c{k}, {d2}, mixm);\n    g{k} = lerp(g{k}, float2(h{k}.y, -h{k}.x), mixm);\n'
                 '    float big{k} = dot({b}.rgb, float3(0.3, 0.59, 0.11)) / max(dot(Mean{k}.rgb, float3(0.3, 0.59, 0.11)), 0.004);\n'
                 '    c{k}.rgb *= lerp(1.0, clamp(big{k}, 0.55, 1.6), Breakup);\n'
                 '    c{k}.rgb = lerp(dot(c{k}.rgb, float3(0.3, 0.59, 0.11)).xxx, c{k}.rgb, Look{k}.a) * Look{k}.rgb;\n}}\n'
                 ).format(k=key, w=GROUND_WEIGHT[key], d=cg.tap_grad('Tex' + key, 'uv', 'dpx / Tile' + key, 'dpy / Tile' + key),
                          b=cg.tap_grad('Tex' + key, 'uv * 0.19 + 0.37', 'dpx / Tile%s * 0.19' % key, 'dpy / Tile%s * 0.19' % key),
                          n=cg.tap_grad('Tex%sN' % key, 'uv', 'dpx / Tile' + key, 'dpy / Tile' + key),
                          d2=cg.tap_grad('Tex' + key, 'uw', 'wdx', 'wdy'), n2=cg.tap_grad('Tex%sN' % key, 'uw', 'wdx', 'wdy'))
    code += ('float3 col = lerp(cForest.rgb, cLitter.rgb, wLitter);\nfloat rough = lerp(%.2f, %.2f, wLitter);\n'
             'float2 g = lerp(gForest, gLitter, wLitter);\nfloat t;\n' % (rough['Forest'], rough['Litter']))
    for key in ('Moss', 'Grass', 'Gravel', 'Dirt', 'Asphalt'):
        code += ('t = saturate(w{k} * (1.0 + Sharp) - (1.0 - c{k}.a) * Sharp); col = lerp(col, c{k}.rgb, t); rough = lerp(rough, {r:.2f}, t); '
                 'g = lerp(g, g{k}, t);\n').format(k=key, r=rough[key])
    code += ('float tb = 0.85 * saturate(wBlight * (1.0 + Sharp) - (1.0 - cBlight.a) * Sharp);\n'
             'col = lerp(col, cBlight.rgb, tb); rough = lerp(rough, %.2f, tb); g = lerp(g, gBlight, tb);\n' % rough['Blight'])
    code += '''float macro = 1.0 + MacroVar * ((n1 - 0.5) * 1.2 + (n2 - 0.5) * 0.8);
col *= macro;
float wet = (1.0 - smoothstep(Water + 4.0, Water + 55.0, WP.z)) * step(WP.z, Water + 400.0);
col *= lerp(1.0, WetDark, wet);
rough = lerp(rough, WetRough, wet);
float3 top = normalize(float3(n.xy + g * NormalK, n.z));
float3 rn = n;
float3 rock = float3(0.1, 0.1, 0.1);
BRANCH if (wRock > 0.004)
{
    float3 pr = WP / TileRock;
    // The scan's strata lie level and repeat every tile: here they dip (a different way on each face) and are bent by
    // slow noise, so a slope shows folded beds instead of ruled lines.
    pr.z += (n1 - 0.5) * 1.3 + (n2 - 0.5) * 2.5;   // long folds only: short ones turn the beds into marbling
    float3 qx = DDX(WP) / TileRock, qy = DDY(WP) / TileRock;
    float3 tw = pow(abs(n), 6.0);
    tw /= max(tw.x + tw.y + tw.z, 0.0001);
    float2 ux = float2(pr.y, -pr.z - 0.24 * pr.y), uy = float2(pr.x, -pr.z + 0.18 * pr.x), uz = pr.xy;
    float2 uxa = float2(qx.y, -qx.z - 0.24 * qx.y), uxb = float2(qy.y, -qy.z - 0.24 * qy.y);
    float2 uya = float2(qx.x, -qx.z + 0.18 * qx.x), uyb = float2(qy.x, -qy.z + 0.18 * qy.x);
''' + ('    float3 rc = (%s * tw.x + %s * tw.y + %s * tw.z).rgb;\n' % (
        cg.tap_grad('TexRock', 'ux', 'uxa', 'uxb'), cg.tap_grad('TexRock', 'uy', 'uya', 'uyb'), cg.tap_grad('TexRock', 'uz', 'qx.xy', 'qy.xy'))) + \
        ('    float2 ax = (%s.rg * 2.0 - 1.0) * RockK;\n    float2 ay = (%s.rg * 2.0 - 1.0) * RockK;\n    float2 az = (%s.rg * 2.0 - 1.0) * RockK;\n' % (
            cg.tap_grad('TexRockN', 'ux', 'uxa', 'uxb'), cg.tap_grad('TexRockN', 'uy', 'uya', 'uyb'), cg.tap_grad('TexRockN', 'uz', 'qx.xy', 'qy.xy'))) + \
        ('    float3 rb = (%s * tw.x + %s * tw.y + %s * tw.z).rgb;\n' % (
            cg.tap_grad('TexRock', 'ux * 0.23', 'uxa * 0.23', 'uxb * 0.23'), cg.tap_grad('TexRock', 'uy * 0.23', 'uya * 0.23', 'uyb * 0.23'),
            cg.tap_grad('TexRock', 'uz * 0.23', 'qx.xy * 0.23', 'qy.xy * 0.23'))) + \
        ('    float2 vx = float2(pr.y, -pr.z + 0.3 * pr.y) * 0.61 + 0.4, vy = float2(pr.x, -pr.z - 0.26 * pr.x) * 0.61 + 0.7;\n'
         '    float2 vxa = float2(qx.y, -qx.z + 0.3 * qx.y) * 0.61, vxb = float2(qy.y, -qy.z + 0.3 * qy.y) * 0.61;\n'
         '    float2 vya = float2(qx.x, -qx.z - 0.26 * qx.x) * 0.61, vyb = float2(qy.x, -qy.z - 0.26 * qy.x) * 0.61;\n'
         '    float3 r2 = (%s * tw.x + %s * tw.y + %s * tw.z).rgb;\n' % (
             cg.tap_grad('TexRock', 'vx', 'vxa', 'vxb'), cg.tap_grad('TexRock', 'vy', 'vya', 'vyb'),
             cg.tap_grad('TexRock', 'uz * 0.61 + 0.4', 'qx.xy * 0.61', 'qy.xy * 0.61'))) + \
        '''    // A second laying of the scan, larger and dipping the other way, takes over in patches; and where a pixel covers
    // more than a hand's width of rock the beds fade to the scan's mean, so far slopes carry tone, not lines.
    rc = lerp(rc, r2, smoothstep(0.4, 0.6, wr));
    float farRock = saturate((length(DDX(WP)) + length(DDY(WP)) - 12.0) / 60.0);
    // The same scan four times larger shades the fine one, so a 200 m slope is not one 6 m tile in rows; moss and
    // lichen take the ledges and the damp patches.
    float rl = dot(float3(0.3, 0.59, 0.11), MeanRock.rgb);
    rc = lerp(MeanRock.rgb, rc, 0.62 * (1.0 - 0.65 * farRock));   // the beds' contrast, eased, and more so far away
    rc *= clamp(dot(rb, float3(0.3, 0.59, 0.11)) / max(rl, 0.004), 0.5, 1.6);
    rock = lerp(dot(rc, float3(0.3, 0.59, 0.11)).xxx, rc, LookRock.a) * LookRock.rgb * macro;
    float mossy = RockMoss * smoothstep(0.34, 0.64, 0.45 * n1 + 0.35 * n3 + 0.45 * n.z);   // turf and moss on all but the steepest rock
    rock = lerp(rock, RockMossColour.rgb * clamp(dot(rc, float3(0.3, 0.59, 0.11)) / max(rl, 0.004), 0.5, 1.6), mossy);
    float3 bx = float3(n.x * sqrt(saturate(1.0 - dot(ax, ax))), n.y + ax.x, n.z - ax.y);
    float3 by = float3(n.x + ay.x, n.y * sqrt(saturate(1.0 - dot(ay, ay))), n.z - ay.y);
    float3 bz = float3(n.x + az.x, n.y + az.y, n.z * sqrt(saturate(1.0 - dot(az, az))));
    rn = normalize(bx * tw.x + by * tw.y + bz * tw.z);
}
col = lerp(col, rock, wRock);
''' + ('rough = lerp(rough, %.2f, wRock);\n' % rough['Rock']) + cn.value_noise2('nv', 'p / 170.0 + float2(n1, n2) * 3.0') + '''float vein = pow(saturate(1.0 - abs(nv - 0.5) * 12.0), 3.0) * tb * keep;
Glow = BlightGlow.rgb * (vein * GlowK * (0.65 + 0.35 * sin(T * 1.7 + n3 * 12.0)));
Normal = normalize(lerp(top, rn, wRock));
float peak = max(col.r, max(col.g, col.b));
col *= min(1.0, 0.9 / max(peak, 0.0001));
return float4(col, saturate(rough));'''
    return code


def material_ground():
    m = master('M_GRGround', tangent_space_normal=False)
    table = sets()
    vc = node(m, unreal.MaterialExpressionVertexColor, -2000, -600)
    inputs = [('VC', vc), ('VA', (vc, 'A')),
              ('UV', node(m, unreal.MaterialExpressionTextureCoordinate, -2000, -500, coordinate_index=0)),
              ('WP', node(m, unreal.MaterialExpressionWorldPosition, -2000, -400)),
              ('VN', node(m, unreal.MaterialExpressionVertexNormalWS, -2000, -300)),
              ('T', node(m, unreal.MaterialExpressionTime, -2000, -200)), ('Heal', mpc_value(m, 'Heal', -2000, -100))]
    for i, (key, set_name, _, look) in enumerate(GROUND_LAYERS):
        colour = texture_object(m, key + 'Colour', scan_texture(set_name, 'D'), 'D', -3000, -1600 + i * 330)
        normal = texture_object(m, key + 'Normal', scan_texture(set_name, 'N'), 'N', -3000, -1450 + i * 330)
        cg.shared_sampler(colour)
        cg.shared_sampler(normal)
        inputs += [('Tex' + key, colour), ('Tex%sN' % key, normal),
                   ('Tile' + key, scalar(m, key + 'Tile', table.get(set_name, {}).get('tile_m', 3.0) * CM, -2600, -1600 + i * 330)),
                   ('Look' + key, (param(m, key + 'Look', tuple(look), -2600, -1500 + i * 330), 'RGBA')),
                   ('Mean' + key, vector(m, key + 'Mean', tuple(table.get(set_name, {}).get('colour') or (.15, .12, .08)), -2600, -1400 + i * 330))]
    for i, (name, value) in enumerate((('Sharp', 2.0), ('RockLo', .75), ('RockHi', 1.15), ('MacroVar', .22), ('Water', plan.WATER * CM),
                                       ('WetDark', .5), ('WetRough', .3), ('NormalK', 1.0), ('RockK', 1.0), ('GlowK', .6), ('RockMoss', .85), ('Breakup', .8))):
        inputs.append((name, scalar(m, {'Sharp': 'BlendSharpness', 'MacroVar': 'MacroVariation', 'NormalK': 'NormalStrength',
                                        'RockK': 'RockNormalStrength', 'GlowK': 'BlightGlowStrength', 'RockLo': 'RockSlopeFrom',
                                        'RockHi': 'RockSlopeTo'}.get(name, name), value, -2000, 100 + i * 80)))
    inputs.append(('BlightGlow', vector(m, 'BlightGlow', (1.0, .1, .38), -2000, 950)))
    inputs.append(('RockMossColour', vector(m, 'RockMossColour', (.036, .058, .016), -2000, 1150)))
    ground = cg.custom_outputs(custom(m, ground_code(), inputs, -1200, -300, FLOAT4), [('Normal', FLOAT3), ('Glow', FLOAT3)])
    lib.connect_material_property(cn.mask(m, ground, 'rgb', -700, -350), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(cn.mask(m, ground, 'a', -700, -230), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(ground, 'Normal', PROP.MP_NORMAL)
    lib.connect_material_property(ground, 'Glow', PROP.MP_EMISSIVE_COLOR)
    lib.connect_material_property(scalar(m, 'Specular', .38, -700, 0), '', PROP.MP_SPECULAR)
    return finish(m)


def material_falls():
    """The waterfall's sheets: streaks of white water sliding down the mesh's uv (v runs down the fall)."""
    m = master('M_GRFalls', blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, two_sided=True,
               translucency_lighting_mode=unreal.TranslucencyLightingMode.TLM_SURFACE, compute_fog_per_pixel=True)
    sheet = cg.custom_outputs(custom(m, FALLS, [
        ('UV', node(m, unreal.MaterialExpressionTextureCoordinate, -1100, -200, coordinate_index=0)),
        ('T', node(m, unreal.MaterialExpressionTime, -1100, -100)), ('Speed', scalar(m, 'Speed', 1.1, -1100, 0)),
        ('Density', scalar(m, 'Density', .9, -1100, 80)), ('Deep', vector(m, 'WaterColour', (.25, .34, .36), -1100, 180)),
        ('Foam', vector(m, 'FoamColour', (.82, .86, .88), -1100, 280))], -600, -100, FLOAT3), [('Opacity', FLOAT1)])
    lib.connect_material_property(sheet, '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(sheet, 'Opacity', PROP.MP_OPACITY)
    lib.connect_material_property(scalar(m, 'Roughness', .35, -600, 200), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(scalar(m, 'Specular', .4, -600, 280), '', PROP.MP_SPECULAR)
    return finish(m)


def material_beam():
    """The link's beam: an unlit additive cylinder (v along its length). Its colour and strength are custom primitive
    data 0-3 (RGB and alpha: BP_LinkBeam fades it), its length data 4 (so the flow's speed does not stretch)."""
    m = master('M_GRBeam', blend_mode=unreal.BlendMode.BLEND_ADDITIVE, shading_model=unreal.MaterialShadingModel.MSM_UNLIT, two_sided=True)
    colour = node(m, unreal.MaterialExpressionVectorParameter, -1100, -100, parameter_name='Colour',
                  default_value=unreal.LinearColor(.25, 1.0, .7, 1.0), use_custom_primitive_data=True, primitive_data_index=0)
    length = node(m, unreal.MaterialExpressionScalarParameter, -1100, 150, parameter_name='Length', default_value=1000.0,
                  use_custom_primitive_data=True, primitive_data_index=4)
    glow = custom(m, BEAM, [('UV', node(m, unreal.MaterialExpressionTextureCoordinate, -1100, -300, coordinate_index=0)),
                            ('T', node(m, unreal.MaterialExpressionTime, -1100, -200)), ('C', (colour, 'RGBA')), ('Length', length),
                            ('F', node(m, unreal.MaterialExpressionFresnel, -1100, 300, exponent=1.0, base_reflect_fraction=0.0)),
                            ('Strength', scalar(m, 'Strength', 30.0, -1100, 420))], -600, 0, FLOAT3)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


# ---------------------------------------------------------------- looks: a generated mesh's slots

# How far a tinted scan's own mean colour is pulled to the slot's reference colour (0: as scanned). Concrete, steel and
# paint are graded to the palette; bark, rock, rust and moss keep the colours they were photographed with.
BALANCE = {'SConcrete': .75, 'SConcreteSlab': .5, 'SConcreteOld': .8, 'SConcreteMoss': .35, 'SConcreteCracked': .7, 'SConcreteFloor': .3,
           'SSteel': .6, 'SSteelPlates': .5, 'SGraphite': .8, 'SDeckPlate': .5, 'SSolar': .3, 'SAsphalt': .6, 'SPlanks': .2}
BALANCE_DEFAULT = .15
METAL_SETS = ('SSteel', 'SSteelPlates', 'SGraphite', 'SPaint', 'SPaintRust', 'SPaintOld', 'SRust', 'SRustLight', 'SCorrugated', 'SDeckPlate')
RUST_BAND = {'SPaintOld': (.5, .75), 'SCanvas': (2.0, 3.0), 'BRoot': (2.0, 3.0)}   # (2, 3): nothing in the scan counts as rust
# Each leaf sheet's material: (ground cover that parts round her, wind amount, flutter).
LEAF_KINDS = {'LGrass': (1.0, 3.2, .5), 'LGrass2': (1.0, 3.2, .5), 'LFlowers': (1.0, 2.6, .5), 'LFine': (1.0, 2.2, .6)}
GLOW_STRENGTH = 24.0   # reads as a lit lamp at the level's exposure, as the Conclave's glows do


def look_name(look):
    """The material instance a look (looks.py) is made as."""
    set_name, mode, ref, rough, metal = look
    if mode == 'glow':
        return 'MI_GR_Glow'
    if mode == 'glass':
        return 'MI_GR_Glass'
    if mode == 'leaf':
        return 'MI_GR_Leaf_' + set_name
    if mode == 'plain' or not set_name:
        return 'MI_GR_Plain_R%02dM%02d' % (round(rough * 100), round(metal * 100))
    code = ''
    if mode == 'tint' and ref:
        code = '_%02X%02X%02X' % tuple(int(round(min(max(c, 0.0), 1.0) ** (1 / 2.2) * 255)) for c in ref)
    return 'MI_GR_%s_%s%s' % (set_name, 'T' if mode == 'tint' else 'P', code)


def all_looks():
    rows = list(LOOKS.SLOT_LOOK.values()) + [row[2] for row in LOOKS.MESH_LOOKS]
    seen, out = set(), []
    for look in rows:
        name = look_name(look)
        if name not in seen:
            seen.add(name)
            out.append(look)
    return out


def make_look(look):
    set_name, mode, ref, rough, metal = look
    name = look_name(look)
    table = sets()
    if mode == 'glow':
        return instance(name, unreal.load_asset(MATS + '/M_GRGlow'), [('Strength', GLOW_STRENGTH)])
    if mode == 'glass':
        return instance(name, unreal.load_asset(cn.MATS + '/M_CNGlass'), [('Opacity', .14), ('FresnelOpacity', .6), ('Roughness', .05)],
                        [('Tint', WHITE)])
    if mode == 'leaf':
        part, amount, flutter = LEAF_KINDS.get(set_name, (0.0, 2.4, .7))
        return instance(name, unreal.load_asset(MATS + '/M_GRLeaf'), [('Part', part), ('WindAmount', amount), ('Flutter', flutter)],
                        textures=[('Sheet', scan_texture(set_name, 'D')), ('SheetNormal', scan_texture(set_name, 'N')),
                                  ('SheetMasks', scan_texture(set_name, 'ARM'))])
    if mode == 'plain' or not set_name:
        return instance(name, unreal.load_asset(MATS + '/M_GRPlain'), [('Roughness', rough), ('Metallic', metal)])
    row = table.get(set_name, {})
    lo, hi = RUST_BAND.get(set_name, (.28, .5))
    scalars = [('Tile', (row.get('tile_m') or 2.0) * CM), ('Paint', 1.0 if mode == 'paint' else 0.0),
               ('Balance', BALANCE.get(set_name, BALANCE_DEFAULT)), ('MetalScale', 1.0 if set_name in METAL_SETS else 0.0),
               ('RustLo', lo), ('RustHi', hi)]
    vectors = [('ScanMean', tuple(row.get('colour') or (.3, .3, .3))), ('Reference', tuple(ref or row.get('colour') or (.4, .4, .4)))]
    return instance(name, unreal.load_asset(MATS + '/M_GRSurface'), scalars, vectors,
                    [('ScanColour', scan_texture(set_name, 'D')), ('ScanNormal', scan_texture(set_name, 'N')),
                     ('ScanMasks', scan_texture(set_name, 'ARM'))])


WATER_LOOKS = {
    # the lake: clear dark forest water, green-brown in the shallows; the headpond the same, stiller
    'MI_GR_Lake': ([('Ripple', .22), ('RippleSpeed', .7), ('Clarity', 260.0), ('MaxOpacity', .9), ('TintDepth', 220.0), ('FoamStrength', .35),
                    ('FoamWidth', 2.0), ('Roughness', .03)], [('WaterColour', (.06, .085, .045)), ('BodyColour', (.008, .014, .011)),
                                                             ('FoamColour', (.6, .62, .58))]),
    'MI_GR_Pond': ([('Ripple', .12), ('RippleSpeed', .5), ('Clarity', 200.0), ('MaxOpacity', .92), ('TintDepth', 160.0), ('FoamStrength', .2),
                    ('FoamWidth', 2.0), ('Roughness', .03)], [('WaterColour', (.05, .075, .045)), ('BodyColour', (.008, .013, .01)),
                                                             ('FoamColour', (.6, .62, .58))]),
    # the stream: livelier, shallower, foam on every stone
    'MI_GR_River': ([('Ripple', .5), ('RippleSpeed', 2.2), ('RippleDetail', .7), ('Clarity', 120.0), ('MaxOpacity', .8), ('TintDepth', 70.0),
                     ('FoamStrength', 1.0), ('FoamWidth', 6.0), ('Roughness', .05)], [('WaterColour', (.08, .1, .06)), ('BodyColour', (.012, .02, .016)),
                                                                                      ('FoamColour', (.7, .73, .7))]),
}


def instances():
    made = []
    for look in all_looks():
        make_look(look)
        made.append(look_name(look))
    instance('MI_GR_Ground', unreal.load_asset(MATS + '/M_GRGround'))
    instance('MI_GR_Falls', unreal.load_asset(MATS + '/M_GRFalls'))
    instance('MI_GR_Backdrop', unreal.load_asset(MATS + '/M_GRPlain'), [('Roughness', .92), ('AlbedoVariation', 0.0)])
    water = unreal.load_asset(cn.MATS + '/M_CNWater')
    if water is None:
        SKIPPED.append('M_CNWater is missing (conclave:materials makes it): the water instances were not made')
    else:
        for name, (scalars, vectors) in WATER_LOOKS.items():
            instance(name, water, scalars, vectors)
            made.append(name)
    # The Heartwood's crown is sick until the grove heals (README "Resonance Link": Heal).
    instance('MI_GR_Leaf_Heart', unreal.load_asset(MATS + '/M_GRLeaf'), [('Sick', 1.0)],
             textures=[('Sheet', scan_texture('LBroadleaf', 'D')), ('SheetNormal', scan_texture('LBroadleaf', 'N')),
                       ('SheetMasks', scan_texture('LBroadleaf', 'ARM'))])
    return made + ['MI_GR_Ground', 'MI_GR_Falls', 'MI_GR_Backdrop', 'MI_GR_Leaf_Heart']


def rim_grass_material():
    """The grass of the rim's slopes: the meadow's sheet at about half its brightness. Seen from the valley floor,
    hundreds of metres off and in full sun, the meadow's own material read as pale dots on the hillside."""
    return instance('MI_GR_Leaf_LGrassRim', unreal.load_asset(MATS + '/M_GRLeaf'), [('Part', 0.0), ('WindAmount', 3.2), ('Flutter', .5), ('Gain', .6)],
                    [('WarmTint', (.95, 1.0, .8))],
                    [('Sheet', scan_texture('LGrass', 'D')), ('SheetNormal', scan_texture('LGrass', 'N')), ('SheetMasks', scan_texture('LGrass', 'ARM'))])


def materials():
    del SKIPPED[:]
    collection()
    made = [material_surface(), material_plain(), material_glow(), material_leaf(), material_scan(), material_rock(), material_scan_plant(),
            material_ground(), material_falls(), material_beam()]
    report = {m.get_name(): lib.get_statistics(m).num_pixel_shader_instructions for m in made}
    report['instances'] = instances()
    report['relinked'] = relink()
    report['skipped'] = list(SKIPPED) + list(cn.SKIPPED)
    return report


# ---------------------------------------------------------------- import: the generated meshes

# No collision (README): the Hedge and the people (their Blueprints keep their own hit rules), what is picked up,
# light that is only light, small plants, the water, the far mountains.
NO_COLLISION = ('SM_GE_', 'SM_GP_', 'SM_GN_Link', 'SM_GN_SeedCache', 'SM_GN_Pin', 'SM_GN_Canister', 'SM_GN_ThornKnot', 'SM_GV_Grass',
                'SM_GV_Flowers', 'SM_GV_Fern', 'SM_GV_Reeds', 'SM_GV_Lily', 'SM_GV_Ivy', 'SM_GV_Mushrooms', 'SM_GV_Bush', 'SM_GV_Sapling',
                'SM_GT_Lake', 'SM_GT_Headpond', 'SM_GT_River', 'SM_GT_Falls', 'SM_GT_Backdrop')
BOX_MESHES = ('SM_GN_ThornWall', 'SM_GN_ThornCage', 'SM_GN_VaultDoor', 'SM_GN_ArrayGate', 'SM_GN_BunkerDoor')
# LOD chains of (triangle fraction, screen size). A plant with its own far versions (<mesh>_LOD1.. beside it) takes
# those instead, at OWN_SCREEN: reduction deletes whole leaf cards, so card plants are never reduced.
OWN_SCREEN = (1.0, .42, .16, .05)
NO_LOD = ('SM_GV_',)
HARD_LODS = ((1.0, 1.0), (.5, .3), (.25, .12), (.12, .04))       # structures, the Hedge, the people, link props
TERRAIN_LODS = ((1.0, 1.0), (.5, .45), (.25, .2))
WOOD_ONLY = ('SM_GV_Snag', 'SM_GV_Thorn')                         # no leaf cards: reduction is safe


def material_for(stem, slot):
    """The material of one slot of one generated mesh."""
    if slot == 'CN_Ground':
        return 'MI_GR_Ground'
    if slot == 'CN_Water':
        return {'SM_GT_Falls': 'MI_GR_Falls', 'SM_GT_River': 'MI_GR_River', 'SM_GT_Headpond': 'MI_GR_Pond'}.get(stem, 'MI_GR_Lake')
    if stem.startswith('SM_GT_Backdrop'):
        return 'MI_GR_Backdrop'
    if stem.startswith('SM_GV_Heartwood') and slot == 'CN_Leaf':
        return 'MI_GR_Leaf_Heart'
    return look_name(LOOKS.look(stem, slot))


def apply_slots(mesh):
    unknown, changed = [], False
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = cn.slot_name(slot)
        want = material_for(mesh.get_name(), name)
        material = unreal.load_asset(MATS + '/' + want)
        if material is None:
            unknown.append('%s -> %s' % (name, want))
            continue
        if slot.get_editor_property('material_interface') != material:
            mesh.set_material(index, material)
            changed = True
    return unknown, changed


def collision_kind(stem):
    if stem.startswith(BOX_MESHES):
        return 'box'
    if stem.startswith(NO_COLLISION):
        return 'none'
    return 'complex'


def lod_chain(stem):
    if stem.startswith('SM_GT_Terrain'):
        return TERRAIN_LODS
    if stem.startswith('SM_GT_'):
        return None
    if stem.startswith(WOOD_ONLY):
        return cn.LODS
    if stem.startswith(NO_LOD):
        return ()
    return HARD_LODS


def own_lods(mesh, files, report):
    """The mesh's own far versions as its LODs 1.., then the screen sizes they switch at."""
    editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    try:
        editor.remove_lods(mesh)
    except Exception:
        pass
    for index, path in enumerate(files, 1):
        got = editor.import_lod(mesh, index, str(path))
        if got != index:
            report.append('%s: LOD %d did not import (%s)' % (mesh.get_name(), index, got))
            return
    sizes = list(OWN_SCREEN[:len(files) + 1])
    setter = getattr(editor, 'set_lod_screen_sizes', None)
    try:
        if setter is None or not setter(mesh, sizes):
            report.append('%s: screen sizes left automatic' % mesh.get_name())
    except Exception as error:
        report.append('%s: screen sizes: %s' % (mesh.get_name(), error))


def import_meshes(prefix=''):
    made, unknown, failed, lod_notes = [], {}, [], []
    for path in sorted(ART.glob(prefix + '*.fbx')):
        stem = path.stem
        if re.search(r'_LOD\d$', stem):
            continue   # imported below as its mesh's LOD
        game.import_file(str(path), MESHES, cn.import_options())
        mesh = unreal.load_asset(MESHES + '/' + stem)
        if mesh is None:
            failed.append(stem)
            continue
        missing, _ = apply_slots(mesh)
        if missing:
            unknown[stem] = missing
        cn.collision(mesh, collision_kind(stem))
        far = [p for p in (ART / ('%s_LOD%d.fbx' % (stem, k)) for k in (1, 2, 3)) if p.exists()]
        if far:
            own_lods(mesh, far, lod_notes)
            apply_slots(mesh)   # the LODs' sections arrive with their own slots
        else:
            chain = lod_chain(stem)
            if chain is not None:
                why = cn.apply_lods(mesh, chain)
                if why:
                    lod_notes.append('%s: %s' % (stem, why))
        game.save(mesh)
        made.append(stem)
    return {'meshes': len(made), 'failed': failed, 'unknown_slots': unknown, 'lods': lod_notes}


def relink():
    count = 0
    for path in library.list_assets(MESHES, False) if library.does_directory_exist(MESHES) else []:
        mesh = unreal.load_asset(path)
        if isinstance(mesh, unreal.StaticMesh):
            _, changed = apply_slots(mesh)
            if changed:
                game.save(mesh)
                count += 1
    return count


# ---------------------------------------------------------------- import: the scanned models

ROCK_USES = ('rock', 'cliff')
SCAN_LODS = {'rock': cn.LODS, 'cliff': ((1.0, 1.0), (.5, .5), (.25, .22), (.1, .08)), 'wood': cn.LODS, 'debris': ((1.0, 1.0), (.4, .1)),
             'prop': HARD_LODS, 'item': ((1.0, 1.0), (.45, .12), (.2, .04)), 'big': HARD_LODS, 'plant': (), 'cover': ()}
# Scanned moss rocks and stumps already carry their moss; the bare boulder and the cliff faces grow some on top.
ROCK_MOSS = {'GS_boulder_01': .6, 'GS_rock_face_01': .8, 'GS_rock_face_02': .65, 'GS_mountainside': .85, 'GS_rock_07': .35}
# The cliff scans are a sunlit tan beside the terrain's own rock: graded down and cooler to sit in it, and each
# instance a different tone, so a slope of them is not one rock repeated.
ROCK_TINT = {'GS_rock_face_01': (.6, .63, .6), 'GS_rock_face_02': (.6, .63, .6), 'GS_mountainside': (.56, .6, .58), 'GS_boulder_01': (.7, .72, .68)}
ROCK_VARIATION = {'GS_rock_face_01': .22, 'GS_rock_face_02': .22, 'GS_mountainside': .22, 'GS_boulder_01': .18}


def scan_material(slot, row, uses, report):
    """MI_<slot> for one scanned material: its own maps on M_GRScan, M_GRRock or M_GRScanPlant; glass is the grove's."""
    if row.get('blend') == 'glass' or not row.get('maps'):
        return unreal.load_asset(MATS + '/MI_GR_Glass')
    textures = {}
    for key, file in row['maps'].items():
        source = READY / 'models' / file
        if not source.exists():
            report['missing'].append(file)
            continue
        game.import_file(str(source), SCAN_TEXTURES)
        texture = unreal.load_asset('%s/%s' % (SCAN_TEXTURES, source.stem))
        if texture is None:
            report['missing'].append(file)
            continue
        textures[key] = settle_texture(texture, {'D': 'DM' if row['blend'] == 'masked' else 'D'}.get(key, key), report['skipped'])
    if not {'D', 'N', 'ARM'} <= set(textures):
        return None
    maps = [('Colour', textures['D']), ('Normal', textures['N']), ('Masks', textures['ARM'])]
    if row['blend'] == 'masked':
        tall = any(u == 'plant' for u in uses)
        return instance('MI_' + slot, unreal.load_asset(MATS + '/M_GRScanPlant'), [('WindAmount', 2.2 if tall else 1.6)], textures=maps,
                        folder=SCAN_MATS)
    if any(u in ROCK_USES for u in uses):
        detail = sets().get('SRock', {})
        return instance('MI_' + slot, unreal.load_asset(MATS + '/M_GRRock'),
                        [('Moss', ROCK_MOSS.get(slot, 0.0)), ('MossFrom', .25), ('InstanceVariation', ROCK_VARIATION.get(slot, .07))],
                        [('DetailMean', tuple(detail.get('colour') or (.2, .14, .08))), ('Tint', ROCK_TINT.get(slot, WHITE))],
                        maps + [('DetailColour', scan_texture('SRock', 'D')), ('DetailNormal', scan_texture('SRock', 'N'))], folder=SCAN_MATS)
    if 'E' in textures:
        return instance('MI_' + slot, unreal.load_asset(MATS + '/M_GRScan'), [('EmissiveStrength', 10.0)], textures=maps + [('Emissive', textures['E'])],
                        switches=[('Emissive', True)], folder=SCAN_MATS)
    return instance('MI_' + slot, unreal.load_asset(MATS + '/M_GRScan'), textures=maps, folder=SCAN_MATS)


def scan_collision(mesh, kind):
    editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    if kind == 'mesh':
        cn.collision(mesh, 'complex')
        return
    cn.collision(mesh, 'box' if kind == 'box' else 'none')
    if kind == 'hull':
        editor.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.NDOP26)


def import_scans(word=''):
    """The scanned models (Tools/grove_scans/process.py): their materials first, then the meshes."""
    facts = read_json(SCAN_ART / 'scans.json')
    maps = read_json(READY / 'models.json')
    report = {'meshes': 0, 'materials': 0, 'missing': [], 'skipped': [], 'failed': [], 'lods': []}
    uses = {}
    for name, row in facts.get('meshes', {}).items():
        for slot in row['slots']:
            uses.setdefault(slot, set()).add(row['use'])
    materials_made = {}
    # Resuming after a crash (the 5.9 preview's card builder can fall over mid-run): scans:+ skips the meshes listed as
    # finished in Saved/Grove/run/scans_done.txt, which every finished mesh is added to.
    ledger = ROOT / 'Saved/Grove/run/scans_done.txt'
    resume = word == '+'
    word = '' if resume else word
    done = set(ledger.read_text().split()) if resume and ledger.exists() else set()
    for name, row in sorted(facts.get('meshes', {}).items()):
        if word and word.lower() not in name.lower():
            continue
        if name in done:
            continue
        for slot in row['slots']:
            if slot not in materials_made:
                materials_made[slot] = scan_material(slot, maps.get(slot, {}), uses.get(slot, ()), report)
                report['materials'] += 1
        game.import_file(str(SCAN_ART / (name + '.fbx')), SCANS, cn.import_options())
        mesh = unreal.load_asset(SCANS + '/' + name)
        if mesh is None:
            report['failed'].append(name)
            continue
        for index, slot in enumerate(mesh.get_editor_property('static_materials')):
            material = materials_made.get(cn.slot_name(slot))
            if material is None:
                report['failed'].append('%s: no material for slot %s' % (name, cn.slot_name(slot)))
            elif slot.get_editor_property('material_interface') != material:
                mesh.set_material(index, material)
        scan_collision(mesh, row['collide'])
        chain = SCAN_LODS.get(row['use'], ())
        why = cn.apply_lods(mesh, chain)
        if why:
            report['lods'].append('%s: %s' % (name, why))
        game.save(mesh)
        report['meshes'] += 1
        if ledger.parent.exists():
            with open(ledger, 'a') as out:
                out.write(name + '\n')
    return report


# ---------------------------------------------------------------- audio

LOOPING = ('S_Music_', 'S_Amb_')


def import_audio():
    """Art/Audio/Grove: music, effects and ambience into /Game/Grove/Audio, the voices into its Voice folder. The
    ambience alone takes the Center's music class (it plays from AmbientSound actors nothing else scales); music and
    voices are scaled by their players, as the Conclave's."""
    sounds, voices, loops = 0, 0, []
    music_class = unreal.load_asset(cn.MUSIC_CLASS)
    for path in sorted((ROOT / 'Art/Audio/Grove').glob('*.wav')):
        game.import_file(str(path), AUDIO)
        wave = unreal.load_asset(AUDIO + '/' + path.stem)
        if wave is None:
            continue
        looping = path.stem.startswith(LOOPING)
        wave.set_editor_property('looping', looping)
        if path.stem.startswith('S_Amb_') and music_class is not None:
            wave.set_editor_property('sound_class_object', music_class)
        game.save(wave)
        if looping:
            loops.append(path.stem)
        sounds += 1
    for path in sorted((ROOT / 'Art/Audio/Grove/Voice').glob('*.wav')):
        game.import_file(str(path), AUDIO + '/Voice')
        voices += 1
    return {'sounds': sounds, 'voices': voices, 'looping': loops}


# ---------------------------------------------------------------- Blueprints and input

BEAM_MESH = '/Engine/BasicShapes/Cylinder'
NEW_BLUEPRINTS = ('BP_LinkNode', 'BP_LinkBeam', 'BP_LinkPull', 'BP_LinkTether', 'BP_GroveDirector', 'BP_GroveCurrent')


def link_input():
    """IA_Link on G and the left stick's click (README "Resonance Link"), added beside the existing mappings."""
    imc = unreal.load_asset('/Game/Input/IMC_Default')
    mappings = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
    existing = {(m.action.get_name() if m.action else None, game.key_name(m.key)) for m in mappings}
    path = game.ACTIONS + '/IA_Link'
    action = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset('IA_Link', game.ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
    game.save(action)
    keys = ('G', 'Gamepad_LeftThumbstick')
    taken = sorted('%s=%s' % (a, k) for a, k in existing if k in keys and a != 'IA_Link')
    for key in keys:
        if ('IA_Link', key) not in existing:
            bound = unreal.Key()
            bound.set_editor_property('key_name', key)
            imc.map_key(action, bound)
    game.save(imc)
    mapped = [game.key_name(m.key) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
              if m.action and m.action.get_name() == 'IA_Link']
    return {'IA_Link': mapped, 'shared_with': taken}


def add_component(bp, cls, name):
    """A component under the Blueprint's scene root, returned as its template. Unreal 5.9 dropped
    editor_toolset.toolsets.actor (ActorTools.add_component), so this goes through the subobject subsystem."""
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    data_of = unreal.SubobjectDataBlueprintFunctionLibrary
    root = None
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        if isinstance(data_of.get_associated_object(data_of.get_data(handle)), unreal.SceneComponent):
            root = handle
            break
    if root is None:
        raise RuntimeError('%s has no scene root' % bp.get_name())
    handle, why = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=cls, blueprint_context=bp))
    part = data_of.get_object_for_blueprint(data_of.get_data(handle), bp)
    if part is None:
        raise RuntimeError('%s: %s was not added (%s)' % (bp.get_name(), name, why))
    subobjects.rename_subobject(handle, unreal.Text(name))
    return part


def shape(bp, mesh, shadow=True, name='Shape'):
    """The Conclave's shape() (a movable StaticMeshComponent without collision) on add_component above."""
    part = add_component(bp, unreal.StaticMeshComponent, name)
    if mesh:
        part.set_static_mesh(mesh)
    part.set_mobility(unreal.ComponentMobility.MOVABLE)
    part.set_collision_profile_name('NoCollision')
    part.set_editor_property('cast_shadow', shadow)
    return part


def blueprints():
    """The grove's own Blueprints with their components (Tools/blueprint_logic/grove_logic.py writes their graphs
    and variables, so one that exists is never remade)."""
    beam = unreal.load_asset(MATS + '/M_GRBeam')
    if beam is None:
        raise RuntimeError('M_GRBeam is missing: run grove:materials first')
    current = unreal.load_asset(cn.MESHES + '/SM_CN_Current')
    made = []
    for name in NEW_BLUEPRINTS:
        if library.does_asset_exist(game.BLUEPRINTS + '/' + name):
            continue
        bp = cn.new_blueprint(name)
        if name == 'BP_LinkNode':
            shape(bp, unreal.load_asset(MESHES + '/SM_GN_LinkNode'))
            glow = add_component(bp, unreal.PointLightComponent, 'Glow')
            glow.set_editor_property('relative_location', unreal.Vector(0, 0, 100))
            glow.set_mobility(unreal.ComponentMobility.MOVABLE)
            glow.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
            glow.set_editor_property('intensity', 6.0)
            glow.set_editor_property('attenuation_radius', 700.0)
            glow.set_editor_property('source_radius', 12.0)
            glow.set_light_color(linear((.25, 1.0, .7)))
            glow.set_cast_shadows(False)
        elif name in ('BP_LinkBeam', 'BP_LinkTether'):
            part = shape(bp, unreal.load_asset(BEAM_MESH), shadow=False)
            part.set_material(0, beam)
            part.set_default_custom_primitive_data_vector4(0, unreal.Vector4(.25, 1.0, .7, 1.0))
            part.set_default_custom_primitive_data_float(4, 1000.0)
        elif name == 'BP_GroveCurrent':
            if current is None:
                raise RuntimeError('SM_CN_Current is missing: run conclave:import first')
            shape(bp, current)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
        made.append(name)
    return {'made': made, 'input': link_input()}


# ---------------------------------------------------------------- pause-menu map

def map_art():
    """The pause menu's Grove page (Tools/build_physis_grove_map.py -> Art/UI/T_UI_MapGrove.png), with the Center's
    settings."""
    game.import_file(str(ROOT / 'Art/UI/T_UI_MapGrove.png'), '/Game/UI')
    texture = unreal.load_asset('/Game/UI/T_UI_MapGrove')
    if texture is None:
        raise RuntimeError('Art/UI/T_UI_MapGrove.png did not import')
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    for axis in ('address_x', 'address_y'):
        texture.set_editor_property(axis, unreal.TextureAddress.TA_CLAMP)
    game.save(texture)
    return {'map': [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]}


# ---------------------------------------------------------------- dispatcher

def level_module():
    import importlib
    import physis_grove_level
    importlib.reload(physis_grove_level)
    return physis_grove_level


def scenario_module():
    import importlib
    import physis_grove_lore
    import physis_grove_scenario
    importlib.reload(physis_grove_lore)
    importlib.reload(physis_grove_scenario)
    return physis_grove_scenario


def execute(operation):
    if operation.startswith('exec:'):
        scope = dict(globals())
        exec(open(operation.split(':', 1)[1]).read(), scope)
        return json.dumps(scope.get('RESULT'), default=str)
    if operation == 'textures' or operation.startswith('textures:'):
        return json.dumps(import_textures(operation.partition(':')[2]), default=str)
    if operation == 'materials':
        return json.dumps(materials(), default=str)
    if operation == 'instances':
        return json.dumps({'instances': instances(), 'relinked': relink()}, default=str)
    if operation == 'import' or operation.startswith('import:'):
        return json.dumps(import_meshes(operation.partition(':')[2]), default=str)
    if operation == 'scans' or operation.startswith('scans:'):
        return json.dumps(import_scans(operation.partition(':')[2]), default=str)
    if operation == 'audio':
        return json.dumps(import_audio(), default=str)
    if operation == 'blueprints':
        return json.dumps(blueprints(), default=str)
    if operation == 'map_art':
        return json.dumps(map_art(), default=str)
    if operation == 'level':
        return json.dumps(level_module().build_level(), default=str)
    if operation.startswith('level:'):
        return json.dumps(level_module().execute(operation.split(':', 1)[1]), default=str)
    if operation == 'save':
        level_module().save_level()
        return json.dumps({'saved': LEVEL})
    if operation == 'scenario':
        return json.dumps(scenario_module().place(level_module().Ground()), default=str)
    if operation.startswith('voss:'):
        import physis_grove_people
        return json.dumps(physis_grove_people.execute(operation.split(':', 1)[1]), default=str)
    if operation == 'portal':
        return json.dumps(scenario_module().portal(), default=str)
    raise ValueError('unknown grove operation ' + operation)
