"""Builds level 3, the Conclave (`outfit_operation conclave:*`).

Run order (Tools/conclave/README.md "Run order"), in a fresh editor: materials, import, audio, map_art, blueprints,
level (map art before the HUD batch, whose PageMap names T_UI_MapConclave); then the Blueprint logic
(Tools/blueprint_logic/conclave_logic.py, center_overrides.py, then conclave_hud.py first in a fresh editor); then
scenario and portal. Meshes, height.bin and scatter.json come from Tools/build_physis_conclave.py, the map art from
Tools/build_physis_conclave_map.py, sound from Tools/build_physis_conclave_audio.py and build_physis_voice.py
--conclave, text from physis_conclave_lore.py, places from physis_conclave_plan.py (metres, Unreal axes), the ground's
and the water's materials from physis_conclave_ground.py (built with this module's helpers).

The author's rules for this level (2026-11-06) shape everything here: realistic shading (physically based
materials and real lights, no post-process material, no cel bands or ink lines), only gold, light blue, red,
green, black and white (green added 2026-11-08; greys are mixes of black and white), and no 3D text. Every colour constant goes through colour()
or tone(), which refuse whatever Tools/conclave_meshes/palette.py refuses.

Operations: materials, rays, import, import:PREFIX, audio, sound_classes, blueprints, level, map_art, save,
exec:PATH, scenario (which then writes the director's SunBase and SunStep, see SUN_BASE), portal; surface_skeletal
(M_CNSurface alone compiled for the people's skinned costumes, without the rest of materials); and the MetaHuman
people's steps, people_new, people_preview, people_guides, people_rig, people_textures, people_assemble, people_import,
people_post and people_verify (each :<Key>; people_verify alone checks everyone assembled) and npc_look, which
physis_conclave_people.py runs (its docstring has the order).
"""
import ast
import importlib.util
import json
import math
import pathlib
import re
import struct
import zlib

import unreal

import physis_center_tools as center
import physis_conclave_lore as lore
import physis_conclave_plan as plan
import physis_gameplay_tools as game
from physis_center_tools import custom, finish, node, param

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
ART = ROOT / 'Art/Meshes/Conclave'
CONCLAVE = '/Game/Conclave'
MESHES = CONCLAVE + '/Meshes'
MATS = CONCLAVE + '/Materials'
AUDIO = CONCLAVE + '/Audio'
LEVEL = '/Game/Levels/L_Conclave'
FOLDER = 'Conclave'
CM = 100.0
library = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
PROP = unreal.MaterialProperty
FLOAT1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
FLOAT3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
FLOAT4 = unreal.CustomMaterialOutputType.CMOT_FLOAT4


# ---------------------------------------------------------------- palette

def _load_palette():
    # Loaded from its file under a private module name: the editor's Python path has no Tools folder, and putting
    # Tools/conclave_meshes on sys.path would also expose its 'toolkit' and 'check' to every other script.
    spec = importlib.util.spec_from_file_location('physis_conclave_palette', ROOT / 'Tools/conclave_meshes/palette.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PAL = _load_palette()
WHITE1 = (1.0, 1.0, 1.0)  # a neutral multiplier (Tint), white by the palette's rule
# The white trees in green (author, 2026-11-08): their near-white leaf cards times LEAF_GREEN_TINT give a summer
# broadleaf albedo (about .07/.15/.03 linear), and light through them takes LEAF_GREEN_GLOW's yellow-green.
LEAF_GREEN_TINT = PAL.col(.075, .17, .035)
LEAF_GREEN_GLOW = PAL.col(.55, 1.0, .25)
# Pure red light, for lights and glows the meshes do not colour (the vaults' ray, the furnace grate): exposure lifted
# LIGHT_RED's 6 % green and 4 % blue into coral and salmon. It passes palette.allowed(); palette.py is not edited.
GLOW_RED = PAL.col(1.0, .005, .004)


def _load_slots():
    # The generators' material slots (toolkit.SLOTS) are the contract every imported mesh's slots follow. toolkit.py
    # imports numpy, which the editor's Python lacks, so its SLOTS literal is read from the source instead.
    tree = ast.parse((ROOT / 'Tools/conclave_meshes/toolkit.py').read_text())
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SLOTS' for t in stmt.targets):
            return tuple(ast.literal_eval(stmt.value))
    raise RuntimeError('Tools/conclave_meshes/toolkit.py has no SLOTS literal')


SLOTS = _load_slots()


def colour(rgb):
    """A palette colour as an (r, g, b) tuple of linear floats; refuses anything outside the five colours."""
    rgb = tuple(float(v) for v in rgb[:3])
    if not PAL.allowed(rgb):
        raise ValueError('colour (%.3f, %.3f, %.3f) is outside the Conclave palette' % rgb)
    return rgb


def tone(rgb, brightness):
    """A light, fog or glow luminance. Its hue is judged at full brightness, as palette.py's LIGHT_* colours are:
    how bright it reads depends on exposure, so a dim light-blue fog is still light blue, not navy."""
    peak = max(float(v) for v in rgb[:3])
    if peak <= 0:
        raise ValueError('a light colour needs some brightness')
    hue = colour(tuple(float(v) / peak for v in rgb[:3]))
    return tuple(v * brightness for v in hue)


def linear(rgb, alpha=1.0):
    return unreal.LinearColor(*colour(rgb), alpha)


# ---------------------------------------------------------------- HLSL building blocks
# Custom-node code cannot declare functions, so the noises are inlined from these templates ('@' is the
# variable prefix). Hashes are Dave Hoskins' sin-free hashes: sin() hashes lose precision far from the origin.

CORNERS = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1))


def value_noise(out, point):
    """Statements that set float `out` to smooth 3D value noise in [0, 1] of the float3 expression `point`."""
    code = 'float3 @_p = ' + point + '; float3 @_i = floor(@_p); float3 @_f = @_p - @_i; float3 @_u = @_f * @_f * (3.0 - 2.0 * @_f);\n'
    for k, (a, b, c) in enumerate(CORNERS):
        code += ('float3 @_q%d = frac((@_i + float3(%d.0, %d.0, %d.0)) * 0.1031); @_q%d += dot(@_q%d, @_q%d.zyx + 31.32); '
                 'float @_h%d = frac((@_q%d.x + @_q%d.y) * @_q%d.z);\n') % (k, a, b, c, k, k, k, k, k, k, k)
    code += ('float @ = lerp(lerp(lerp(@_h0, @_h1, @_u.x), lerp(@_h2, @_h3, @_u.x), @_u.y), '
             'lerp(lerp(@_h4, @_h5, @_u.x), lerp(@_h6, @_h7, @_u.x), @_u.y), @_u.z);\n')
    return code.replace('@', out)


def value_noise1(out, x):
    """Statements that set float `out` to smooth 1D value noise in [0, 1] of the float expression `x`."""
    code = 'float @_x = ' + x + '; float @_i = floor(@_x); float @_f = @_x - @_i; float @_u = @_f * @_f * (3.0 - 2.0 * @_f);\n'
    for k in (0, 1):
        code += ('float @_a%d = frac((@_i + %d.0) * 0.1031); @_a%d *= @_a%d + 33.33; @_a%d *= @_a%d + @_a%d; @_a%d = frac(@_a%d);\n'
                 % (k, k, k, k, k, k, k, k, k))
    code += 'float @ = lerp(@_a0, @_a1, @_u);\n'
    return code.replace('@', out)


def value_noise2(out, point):
    """Statements that set float `out` to smooth 2D value noise in [0, 1] of the float2 expression `point`, and float2
    `out`_g to its gradient with respect to that point: analytic, so a bump normal costs no extra samples."""
    code = ('float2 @_p = ' + point + '; float2 @_i = floor(@_p); float2 @_f = @_p - @_i;\n'
            'float2 @_u = @_f * @_f * (3.0 - 2.0 * @_f); float2 @_du = 6.0 * @_f * (1.0 - @_f); float3 @_q;\n')
    for k, (a, b) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
        code += ('@_q = frac(float3((@_i + float2(%d.0, %d.0)).xyx) * 0.1031); @_q += dot(@_q, @_q.yzx + 33.33); '
                 'float @_h%d = frac((@_q.x + @_q.y) * @_q.z);\n') % (a, b, k)
    code += ('float @_k = @_h0 - @_h1 - @_h2 + @_h3;\n'
             'float @ = @_h0 + (@_h1 - @_h0) * @_u.x + (@_h2 - @_h0) * @_u.y + @_k * @_u.x * @_u.y;\n'
             'float2 @_g = @_du * float2(@_h1 - @_h0 + @_k * @_u.y, @_h2 - @_h0 + @_k * @_u.x);\n')
    return code.replace('@', out)


def waves(count, seed, ratio=1.618, falloff=.65):
    """Plane waves for a micro-normal: golden-spiral directions (so no two line up), frequencies in an irrational
    ratio (so the sum never visibly repeats), amplitudes normalised to a total slope of 1."""
    rows = []
    for k in range(count):
        z = 1 - (k + .5) * 2 / count
        r = math.sqrt(max(0.0, 1 - z * z))
        a = k * 2.39996 + seed
        freq = ratio ** k
        rows.append(((r * math.cos(a), r * math.sin(a), z), freq, (seed * 7.31 + k * 2.17) % (2 * math.pi), freq ** -falloff))
    total = sum(row[3] for row in rows)
    return [(d, f, ph, amp / total) for d, f, ph, amp in rows]


def wave_gradient(out, point, table, footprint=None):
    """Statements that set float3 `out` to the gradient (a slope, unitless) of a sum of plane waves over the float3
    expression `point`; each wave's height is scaled to its wavelength, so its slope is just its amplitude. With
    `footprint` (a float variable: one pixel in the units of `point`), each wave fades out as its wavelength shrinks
    from 8 to 4 pixels, so the micro-normal settles to the smooth surface instead of shimmering at a distance."""
    code = 'float3 @_p = ' + point + '; float3 @ = float3(0.0, 0.0, 0.0); float @_w;\n'
    for (x, y, z), freq, phase, amp in table:
        fade = '' if footprint is None else ' * saturate(%.5f / %s - 1.0)' % (0.25 / freq, footprint)
        code += ('@_w = dot(@_p, float3(%.5f, %.5f, %.5f)) * %.5f + %.5f; @ += float3(%.5f, %.5f, %.5f) * (cos(@_w) * %.5f%s);\n'
                 % (x, y, z, 2 * math.pi * freq, phase, x, y, z, amp, fade))
    return code.replace('@', out)


SURFACE_WAVES = waves(6, 0.7)

# Bends the interpolated normal by a slope: the part of the gradient along the normal is removed first, so the
# result stays on the surface's side.
PERTURB = '''float3 n = normalize(VN);
float3 g = G - dot(G, n) * n;
return normalize(n - g * K);'''

# Texture detail (Tools/conclave_textures/textures.py; README "Materials and rendering"): each slot's set is two
# tileable maps, sampled triplanar in object space so detail stays put on things that move: _M (R albedo factor,
# G roughness factor, B cavity, A the set's feature: veins, grout, scratches, cracks) and _N (tangent normal, R along
# u, G along v). Projections follow Ben Golus's whiteout blend, with v up the object on both side planes (x-facing
# uv = p.yz, y-facing p.xz, z-facing p.xy), so vertical grain (bark) runs up every side. Rnd shifts the pattern per object so neighbours never match.
TRI_M = """float3 n = normalize(LN);
float3 w = pow(abs(n), Sharp);
w /= max(w.x + w.y + w.z, 0.0001);
float3 p = LP / max(Tile, 1.0) + frac(Rnd * 13.17) * 7.0;
float4 m = Texture2DSample(TexM, TexMSampler, p.yz) * w.x;
m += Texture2DSample(TexM, TexMSampler, p.xz) * w.y;
m += Texture2DSample(TexM, TexMSampler, p.xy) * w.z;
return m;"""
TRI_N = """float3 n = normalize(LN);
float3 w = pow(abs(n), Sharp);
w /= max(w.x + w.y + w.z, 0.0001);
float3 p = LP / max(Tile, 1.0) + frac(Rnd * 13.17) * 7.0;
float2 ax = (Texture2DSample(TexN, TexNSampler, p.yz).rg * 2.0 - 1.0) * K;
float2 ay = (Texture2DSample(TexN, TexNSampler, p.xz).rg * 2.0 - 1.0) * K;
float2 az = (Texture2DSample(TexN, TexNSampler, p.xy).rg * 2.0 - 1.0) * K;
float3 tx = float3(ax + n.yz, sqrt(saturate(1.0 - dot(ax, ax))) * n.x);
float3 ty = float3(ay + n.xz, sqrt(saturate(1.0 - dot(ay, ay))) * n.y);
float3 tz = float3(az + n.xy, sqrt(saturate(1.0 - dot(az, az))) * n.z);
return normalize(tx.zxy * w.x + ty.xzy * w.y + tz.xyz * w.z);"""
# Applied inside SURFACE after the procedural variation: the albedo factor and cavity scale the colour (a grey factor
# never moves a hue), the feature is coloured either absolutely (FB 0: grout, veins) or as the surface's own colour
# brightened or darkened (FB 1: scratches on gold stay gold), and roughens or polishes (FR).
DETAIL = """col *= 1.0 + AD * (DM.r * 2.0 - 1.0);
col *= lerp(1.0, DM.b, CA);
float fa = saturate(DM.a * FA);
col = lerp(col, lerp(FC.rgb, col * FC.rgb * 2.0, FB), fa);
rough += RD * (DM.g * 2.0 - 1.0) + FR * fa;
"""

# M_CNSurface: albedo and roughness variation, marble veins and brushed streaks, in object space, so detail stays
# put on things that move (enemies, pickups, people turning to talk). Rnd offsets the pattern per object: each
# scatter instance's PerInstanceRandom plus the per-actor Seed (custom primitive data SEED_DATA, set by mesh_actor),
# since PerInstanceRandom is 0 on single actors and the town's hundred-odd copies of each house would otherwise all
# wear one pattern. Lift raises a metal's dark vertex colour toward a real metal's reflectance (steel F0 is about
# 0.55) by scaling it, which keeps its hue; MaxAlbedo caps it the same way.
# Each noise octave fades to its mean as its cells shrink from 4 pixels to 1.3 (fp: one pixel in na's cells; nb's are
# 3.71 times smaller): unfaded, the end caps and the Spine 0.5 to 1.6 km away shimmered as static salt and pepper. One
# macro octave (MacroScale) then gives each copy of a house its own overall tone (Rnd) and varies big panels once the
# fine noise has faded. Splash darkens a wall's foot below SplashH local cm (rain splash and damp): only the plaster
# walls use it, and they stand on z 0.
SURFACE = ('float3 p = LP / max(Scale, 1.0) + Rnd * 37.13;\n'
           + value_noise('na', 'p') + value_noise('nb', 'p * 3.71 + float3(11.3, 7.1, 3.9)')
           + value_noise('nm', 'LP / max(MacroScale, 1.0) + Rnd * 5.3') +
           '''float fp = max(length(DDX(LP)), length(DDY(LP))) / max(Scale, 1.0);
float keepA = saturate(1.5 - 2.0 * fp);
float keepB = saturate(1.5 - 7.42 * fp);
float v = (na - 0.5) * keepA * 1.3 + (nb - 0.5) * keepB * 0.7;
float3 col = VC.rgb * Tint.rgb * (1.0 + Var * v);
col *= 1.0 + MacroVariation * (nm - 0.5) * 2.0;
float rough = R0 + RVar * ((nb - 0.5) * keepB * 1.4 + (na - 0.5) * keepA * 0.6);
if (Veins > 0.0)
{
    float3 vq = LP / max(VScale, 1.0) + Rnd * 11.7;
    float w1 = abs(sin(dot(vq, float3(0.82, 0.37, 0.43)) * 3.0 + na * 6.0 + nb * 2.0));
    float w2 = abs(sin(dot(vq, float3(-0.31, 0.91, 0.27)) * 5.0 + nb * 5.0 + na));
    float vm = pow(saturate(1.0 - w1), 14.0) + 0.5 * pow(saturate(1.0 - w2), 24.0);
    col = lerp(col, VCol.rgb * (0.85 + 0.3 * na), saturate(vm) * Veins);
}
if (Brushed > 0.0)
{
    float3 bn = normalize(N);
    float3 bt = abs(bn.z) < 0.95 ? normalize(cross(float3(0.0, 0.0, 1.0), bn)) : float3(1.0, 0.0, 0.0);
    float3 bb = cross(bn, bt);
    float across = dot(LP, bb) / max(BScale, 0.01);
''' + value_noise1('sa', 'across') + value_noise1('sb', 'across * 0.23 + dot(LP, bt) * 0.004') +
           '''    float streak = sa * 0.65 + sb * 0.35 - 0.5;
    rough += streak * 0.3 * Brushed;
    col *= 1.0 + streak * 0.06 * Brushed;
}
''' + DETAIL + '''col *= 1.0 - Splash * (1.0 - smoothstep(0.0, SplashH, LP.z)) * (0.6 + 0.4 * na);
if (Lift > 0.0)
{
    float lifted = max(max(col.r, col.g), col.b);
    col *= (lifted + Lift) / max(lifted, 0.02);
}
float peak = max(max(col.r, col.g), col.b);
col *= min(1.0, MaxA / max(peak, 0.0001));
return float4(col, saturate(rough));''')

# Emissive from the vertex colour. A red glow (red over four times its other channels and saturated: LIGHT_RED or
# GLOW_RED at any tone) keeps only its red channel, so exposure can no longer lift its 6 % green and 4 % blue into
# coral or salmon; RedScale sets its strength. Other saturated glows (gold, light blue) take ChromaScale of the
# strength, so they bloom in their hue instead of clipping to white. Greys (white lamps, the Spine) are unchanged.
GLOW_EMISSIVE = """float3 e = VC.rgb;
float m = max(e.r, max(e.g, e.b));
float s = (m - min(e.r, min(e.g, e.b))) / max(m, 0.0001);
float red = step(4.0 * max(e.g, e.b), e.r) * step(0.5, s);
e = lerp(e, float3(e.r, 0.0, 0.0), red);
float k = lerp(lerp(1.0, ChromaScale, saturate((s - 0.2) * 2.0)), RedScale, red);
return e * Strength * k;"""
# Metallic per pixel: where MetalFeature is set, the detail set's feature (the Steel set's scratches) is bare metal on a
# painted surface, so blackened iron shows bright steel where it is worn. MetalFeature 0 leaves the plain Metallic.
METAL = 'return saturate(M + MF * saturate(DM.a * FA));'

# DDX/DDY are Common.ush's wrappers (0 where derivatives do not exist), so the fade is safe in every shader type.
MICRO = ('float3 q = LP / max(Scale, 0.01) + Rnd * 53.71;\n'
         'float fpq = max(max(length(DDX(LP)), length(DDY(LP))), 0.0001) / max(Scale, 0.01);\n'
         + wave_gradient('g', 'q', SURFACE_WAVES, 'fpq') + 'return g;')

# M_CNFoliage: leaves vary per plant (PerInstanceRandom, or a placed actor's Seed) and in patches; the wind sways
# with the square root of the height (a 0.6 m tuft moves about 2 cm, a tree crown 7 cm), so a canopy never parts from
# its rigid trunk.
LEAF = ('float3 p = LP / max(Scale, 1.0) + Rnd * 19.3;\n' + value_noise('na', 'p') +
        '''float v = (na - 0.5) * 2.0 + (frac(Rnd) - 0.5) * 1.2;
float3 col = VC.rgb * Tint.rgb * (1.0 + Var * v);
float peak = max(max(col.r, col.g), col.b);
col *= min(1.0, 0.9 / max(peak, 0.0001));
return float4(col, saturate(R0 + RVar * (na - 0.5) * 2.0));''')
# Light through the leaves (Two Sided Foliage's subsurface colour). Grey leaves (white blossom, black needles) pass K
# of their colour and keep their value; saturated ones pass their hue at TransmissionBright (TB), so a backlit red leaf
# glows red instead of maroon. Twigs on cards (the atlas's B) pass none.
LEAF_LIGHT = """float card = 1.0 - saturate(VA * 2.0);
float m = max(VC.r, max(VC.g, VC.b));
float s = (m - min(VC.r, min(VC.g, VC.b))) / max(m, 0.0001);
float3 t = lerp(VC.rgb * K, VC.rgb / max(m, 0.0001) * TB, saturate(2.0 * s));
return t * Sub.rgb * (1.0 - card * A.b);"""
# Subsurface opacity: Two Sided Foliage writes Opacity to the GBuffer, where shadow transmission reads it. With the
# implicit 1 any card between a leaf and the Spine cut that leaf's transmitted light off, so crowns went dark below.
LEAF_OPACITY = 'return lerp(Solid, Card, 1.0 - saturate(VA * 2.0));'
# Atlas cards (Tools/conclave_textures/atlas.py; al_flora.py marks their vertices with colour alpha 0): the atlas's
# albedo factor and relief on the vertex colour, twigs and stems in StemColour, and a masked outline. Solid leaf
# geometry (alpha 1: fruit, flowers, cores, stems) keeps exactly its old look.
LEAF_CARD = """float card = 1.0 - saturate(VA * 2.0);
float3 col = Leaf.rgb * (1.0 + card * Detail * (A.r * 2.0 - 1.0));
col = lerp(col, Stem.rgb, card * A.b);
float rough = Leaf.a + card * (RD * (A.g * 2.0 - 1.0) + A.b * 0.2);
float peak = max(max(col.r, col.g), col.b);
col *= min(1.0, 0.9 / max(peak, 0.0001));
return float4(col, saturate(rough));"""
LEAF_MASK = 'return lerp(1.0, A.a, 1.0 - saturate(VA * 2.0));'
LEAF_TANGENT = 'return normalize(lerp(float3(0.0, 0.0, 1.0), N, K));'
WIND = '''float h = max(LP.z, 0.0) / 100.0;
float t = T * Speed + dot(WP.xy, float2(0.0021, 0.0017));
float gust = 0.6 + 0.4 * sin(T * 0.37 + WP.x * 0.0004);
float sway = Amount * sqrt(h) * (sin(t) * 0.7 + sin(t * 2.3 + 1.7) * 0.3) * gust;
float flutter = Flutter * saturate(h * 3.0) * sin(T * 9.0 + dot(WP, float3(0.13, 0.07, 0.11)));
return float3(0.92 * sway + 0.4 * flutter, 0.39 * sway - 0.3 * flutter, flutter);'''
# Ground cover takes the ground's normal: a tuft's blades stand nearly upright, so under a high sun they shaded at 40 %
# of the lawn around them and meadows read as scattered dark specks. Below UpHeight (local cm) the normal bends toward
# world up, fully at the root; tree crowns, far above it, keep their own. A world-space normal is not flipped for back
# faces (MaterialTemplate.ush flips tangent-space ones only), so the facing side is taken from TwoSidedSign here.
LEAF_NORMAL = '''float card = 1.0 - saturate(VA * 2.0);
// A card's normal (its canopy normal with the atlas relief) is not flipped on its back face: both faces shade as the
// crown they belong to. Solid leaves flip as before.
float3 n = lerp(normalize(VN) * Parameters.TwoSidedSign, normalize(TN), card);
float k = Up * saturate(1.0 - LP.z / max(UpHeight, 1.0));
return normalize(lerp(n, float3(0.0, 0.0, 1.0), k));'''

GLASS_BASE = 'return VC.rgb * Tint.rgb;'
GLASS_OPACITY = 'return saturate(O + F * FO);'
# Glass lit from within (the Spire's crystal, light platforms and caches, Iriel's veil): its own colour, strongest at
# grazing angles where the light crosses more glass. Glow 0, the master's default, leaves every other glass unlit.
GLASS_GLOW = 'return VC.rgb * Glow * (0.15 + F);'

# M_CNGround and M_CNWater are built by Content/Python/physis_conclave_ground.py (ground_module() below) from this
# module's helpers.

# M_CNSky: black space, stars as soft discs in hashed cells, a faint white galactic band, and the ringed gas
# giant in its own sunlight. Each band and ring is one palette colour with a narrow edge: palette.py leaves a gap
# between white (saturation under 0.12) and gold (0.18 and over), so a soft blend of the two would paint pale
# creams it refuses. Rings hide behind the planet, shade it, and fall into its shadow.
SKY = ('''float3 d = normalize(-V);
float3 col = float3(0.0, 0.0, 0.0);
float3 sc = floor(d * 420.0);
float3 sq = frac(sc * 0.1031); sq += dot(sq, sq.zyx + 31.32);
float sh = frac((sq.x + sq.y) * sq.z);
float3 sj = frac(sq * 7.31 + 0.37);
float3 sp = normalize(sc + 0.15 + 0.7 * sj) * 420.0;
float sr = length(d * 420.0 - sp);
float sm = frac(sh * 91.7);
float star = saturate(1.0 - sr * 1.25) * step(0.9935, sh) * (0.08 + 0.92 * sm * sm * sm);
col += StarColour.rgb * StarBright * star;
float3 bandn = normalize(float3(0.31, -0.42, 0.85));
float band = pow(saturate(1.0 - abs(dot(d, bandn))), 9.0);
''' + value_noise('mw', 'd * 7.0 + float3(3.1, 1.7, 5.3)') + value_noise('mv', 'd * 19.0 + float3(8.2, 2.6, 4.4)') + '''col += MilkyColour.rgb * MilkyBright * band * saturate(mw * 0.9 + mv * 0.5 - 0.25);
float3 G = normalize(PlanetDir.xyz);
float3 A = normalize(PlanetAxis.xyz);
float3 S = normalize(SunDir.xyz);
float r = sin(Radius);
float b = dot(d, G);
float disc = r * r - (1.0 - b * b);
float tp = 1e9;
if (disc > 0.0 && b > 0.0)
{
    tp = b - sqrt(disc);
    float3 P = d * tp;
    float3 n = (P - G) / r;
    float3 e1 = normalize(cross(A, float3(0.31, 0.83, 0.47)));
    float3 e2 = cross(A, e1);
    float lat = dot(n, A);
    float lon = atan2(dot(n, e2), dot(n, e1));
    float y = lat + 0.045 * sin(lon * 3.0 + lat * 9.0) + 0.02 * sin(lon * 8.0 - lat * 21.0);
    float b1 = 0.5 + 0.5 * sin(y * 27.0);
    float b2 = 0.5 + 0.5 * sin(y * 63.0 + 1.3);
    float3 base = lerp(BandA.rgb, BandB.rgb, smoothstep(0.47, 0.53, b1));
    base = lerp(base, BandC.rgb, smoothstep(0.84, 0.88, b2) * smoothstep(0.30, 0.34, abs(lat)));
    float light = saturate(dot(n, S) * 1.1 + 0.05);
    float rs = dot(S, A);
    if (abs(rs) > 0.001)
    {
        float tr = -dot(P - G, A) / rs;
        float q = length(P + S * tr - G) / r;
        float shade = smoothstep(Inner, Inner + 0.04, q) * (1.0 - smoothstep(Outer - 0.06, Outer, q)) * (1.0 - 0.85 * (1.0 - smoothstep(0.0, 0.035, abs(q - Gap))));
        light *= tr > 0.0 ? 1.0 - 0.6 * shade : 1.0;
    }
    float limb = pow(saturate(1.0 - dot(n, -d)), 3.0);
    col = base * light * PlanetBright + RimColour.rgb * RimBright * limb * saturate(dot(n, S) + 0.25);
}
float dn = dot(d, A);
if (abs(dn) > 0.0001)
{
    float t = dot(G, A) / dn;
    if (t > 0.0 && t < tp)
    {
        float3 Q = d * t;
        float q = length(Q - G) / r;
        float ring = smoothstep(Inner, Inner + 0.04, q) * (1.0 - smoothstep(Outer - 0.06, Outer, q));
        float gap = 1.0 - 0.85 * (1.0 - smoothstep(0.0, 0.035, abs(q - Gap)));
        float grain = 0.6 + 0.4 * (0.5 + 0.5 * sin(q * 97.0) * sin(q * 41.0 + 0.7));
        float density = saturate(ring * gap * grain);
        float3 toG = G - Q;
        float along = dot(toG, S);
        float shadow = (along > 0.0 && length(toG - S * along) < r) ? 0.12 : 1.0;
        float3 rc = lerp(RingA.rgb, RingB.rgb, smoothstep(0.47, 0.53, 0.5 + 0.5 * sin(q * 23.0)));
        float3 ringCol = rc * RingBright * (0.35 + 0.65 * abs(dot(S, A))) * shadow;
        col = lerp(col, ringCol, density * 0.85);
    }
}
float3 o = Cam - float3(0.0, 0.0, AxisZ);
float qa = dot(d.yz, d.yz);
float qb = dot(o.yz, d.yz);
float qc = dot(o.yz, o.yz) - DrumR * DrumR;
float path = 1e7;
if (qa > 1e-6)
{
    path = (-qb + sqrt(max(qb * qb - qa * qc, 0.0))) / qa;
}
if (abs(d.x) > 1e-6)
{
    path = min(path, (sign(d.x) * HalfX - o.x) / d.x);
}
float len = max(path - HazeStart, 0.0);
float z0 = Cam.z + d.z * min(HazeStart, path);
float F1 = max(-127.0, HazeFalloff * d.z * len);
float l1 = abs(F1) > 1e-5 ? (1.0 - exp2(-F1)) / F1 : 0.6931 - 0.2402 * F1;
float F2 = max(-127.0, Haze2Falloff * d.z * len);
float l2 = abs(F2) > 1e-5 ? (1.0 - exp2(-F2)) / F2 : 0.6931 - 0.2402 * F2;
float od = (HazeDensity * exp2(-HazeFalloff * (z0 - HazeBase)) * l1 + Haze2Density * exp2(-Haze2Falloff * (z0 - Haze2Base)) * l2) * len;
float haze = min(1.0 - exp2(-od), HazeMax) * SkyHaze;
return lerp(col, HazeColour.rgb * HazeBright, haze);''')
# The sphere lies beyond the height fog's cut-off, so the sky haze above is the drum's own air between the camera and
# the window (the ray's exit through the drum's cylinder or an end cap), with the fog's colour, start and opacity cap:
# without it every window was a fog-free black hole in a hazy drum. Its depth is the engine's own height-fog line
# integral over both layers from the start distance on (HeightFogCommon.ush; HazeBase and Haze2Base are the layers'
# heights): the old exp2(-density * path) missed the line integral's ln 2 and the height term, so the windows took
# about 1.45 times the fog of the black ground beside them and space read brighter than the land. SkyHaze then thins
# it, because the drum's air scatters forward, toward the Spine, and the windows are mostly seen away from it. (If the
# director ever scales the fog's inscattering at run time, it does not scale HazeBright.)

# M_CNSpineHalo: the glow of the air around a lit third of the Spine, on an engine cylinder (radius 90 m) around it. The
# air's brightness falls off as a Gaussian of the distance from the axis (Sigma); HALO integrates it along the view ray
# in closed form, limited to the third's x range (HalfLen either side of the object's centre), with erf approximated
# by tanh(1.2 x) (its arguments clamped: tanh of a huge argument overflows to NaN on some compilers). Only arithmetic,
# no textures; additive and unlit, so a third with no halo actor shown adds nothing.
HALO = '''float3 d = normalize(-V);
float3 o = Cam - float3(OP.x, 0.0, AxisZ);
float a = max(d.y * d.y + d.z * d.z, 0.002);
float b = o.y * d.y + o.z * d.z;
float r2 = max(o.y * o.y + o.z * o.z - b * b / a, 0.0);
float ts = -b / a;
float k = sqrt(a) / Sigma;
float t0 = 0.0;
float t1 = 1e9;
if (abs(d.x) > 1e-5)
{
    float ta = (-HalfLen - o.x) / d.x;
    float tb = (HalfLen - o.x) / d.x;
    t0 = max(min(ta, tb), 0.0);
    t1 = max(max(ta, tb), 0.0);
}
else if (abs(o.x) > HalfLen)
{
    t1 = 0.0;
}
float S = 0.5 * (tanh(clamp(1.2 * k * (t1 - ts), -8.0, 8.0)) - tanh(clamp(1.2 * k * (t0 - ts), -8.0, 8.0)));
return Colour.rgb * Intensity * exp(-r2 / (Sigma * Sigma)) * S * min(rsqrt(a), 6.0);'''

# M_CNLightTrail on the engine cylinder (local z -50..50): a bright core where the surface faces the camera,
# soft edges and tips, a quick shimmer. Fade comes from custom primitive data 0, so BP_LightTrail fades it
# without a dynamic material instance.
TRAIL = '''float core = pow(saturate(1.0 - F), 1.5);
float tips = smoothstep(0.0, 0.3, 0.5 - abs(LP.z) / 100.0);
float shimmer = 0.85 + 0.15 * sin(T * 21.0 + LP.z * 0.25);
float3 c = lerp(Edge.rgb, Core.rgb, core * core);
return c * Intensity * core * tips * shimmer * saturate(Fade);'''

# M_CNFurnace (BP_Hazard's Shape): a world-space iron grate, so it tiles the same on any hazard mesh and size.
# BP_Hazard writes its pulse to custom primitive data 0 (Heat). The fire under the grate is red or gold, never a
# blend of the two: the colour switches inside a dark seam, and the glowing bar edges take the colour of their
# patch, so no orange appears anywhere. The fire is clearly lit or black: below about a third of full heat it goes
# out (no ember floor), since a dim red glow tone-maps to maroon. Vertex colour red is the plasma pool mesh's
# distance to its rim (white on other meshes).
FURNACE_BARS = '''float2 g = WP.xy / max(Cell, 1.0);
float2 dl = abs(frac(g + 0.5) - 0.5) * Cell;
float bar = 1.0 - smoothstep(Bar - 0.6, Bar + 0.6, min(dl.x, dl.y));
float2 dk = abs(frac(g * 0.25 + 0.5) - 0.5) * Cell * 4.0;
return max(bar, 1.0 - smoothstep(Bar * 2.0 - 0.6, Bar * 2.0 + 0.6, min(dk.x, dk.y)));'''
FURNACE_SURFACE = 'return float4(lerp(Pit.rgb, Iron.rgb, B), lerp(0.92, 0.55, B));'
FURNACE_GLOW = (value_noise('na', 'float3(WP.xy / 45.0, T * 0.35)') + value_noise('nb', 'float3(WP.xy / 170.0, T * 0.06) + float3(3.1, 7.7, 1.9)') +
                '''float heat = saturate(Heat);
float flicker = 0.78 + 0.22 * sin(T * 7.0 + na * 9.0);
float hot = heat * (0.55 + 0.45 * na) * flicker;
float k = smoothstep(0.58, 0.68, nb);
float seam = 1.0 - 4.0 * k * (1.0 - k);
float3 fire = (k < 0.5 ? Red.rgb : Gold.rgb) * seam;
fire *= smoothstep(0.25, 0.4, hot);
float gap = 1.0 - B;
float rim = B * (1.0 - B) * 4.0;
float edge = smoothstep(0.0, 0.25, VC.r);
return fire * (hot * gap + heat * 0.12 * rim) * Strength * edge;''')


# ---------------------------------------------------------------- material helpers

WORLD_TO_LOCAL = (unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD, unreal.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
LOCAL_TO_WORLD = (unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL, unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
TANGENT_TO_WORLD = (unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT, unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)


# UE 5.8's DeleteAllMaterialExpressions walks a view of the expression array while each delete compacts that array,
# so one pass deletes only about half the nodes (MaterialEditingLibrary.cpp). Each pass halves what is left: ten
# empty any graph under a thousand nodes, and a pass over an empty graph does nothing. Counting the nodes instead
# would mean reading an existing material's graph, and an introspection call on one crashed the editor.
CLEAR_PASSES = 10
SKIPPED = []  # material settings the editor refused, reported by conclave:materials


def master(name, **settings):
    """The material MATS/name with an empty graph, made if missing. It is rebuilt in place, not deleted: meshes,
    placed actors and Blueprints that use it keep their reference (a deleted material leaves those slots empty)."""
    path = MATS + '/' + name
    if library.does_asset_exist(path):
        material = unreal.load_asset(path)
        for _ in range(CLEAR_PASSES):
            lib.delete_all_material_expressions(material)
    else:
        material = tools.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    values = {'material_domain': unreal.MaterialDomain.MD_SURFACE, 'blend_mode': unreal.BlendMode.BLEND_OPAQUE,
              'shading_model': unreal.MaterialShadingModel.MSM_DEFAULT_LIT, 'two_sided': False, 'tangent_space_normal': True}
    values.update(settings)
    for key, value in values.items():
        try:
            material.set_editor_property(key, value)
        except Exception as error:
            # Reported rather than raised: one refused flag should not leave every later material unbuilt.
            SKIPPED.append('%s.%s: %s' % (name, key, error))
    return material


def scalar(material, name, value, x, y):
    return param(material, name, float(value), x, y)


def cparam(material, name, rgb, x, y):
    return param(material, name, colour(rgb), x, y)


def mask(material, source, channels, x, y):
    expression = node(material, unreal.MaterialExpressionComponentMask, x, y,
                      r='r' in channels, g='g' in channels, b='b' in channels, a='a' in channels)
    lib.connect_material_expressions(source, '', expression, '')
    return expression


def transform(material, source, kind, x, y):
    expression = node(material, unreal.MaterialExpressionTransform, x, y, transform_source_type=kind[0], transform_type=kind[1])
    lib.connect_material_expressions(source, '', expression, '')
    return expression


def multiply(material, a, b, x, y):
    expression = node(material, unreal.MaterialExpressionMultiply, x, y)
    lib.connect_material_expressions(a, '', expression, 'A')
    lib.connect_material_expressions(b, '', expression, 'B')
    return expression


# Custom primitive data index of the per-actor pattern seed (M_CNSurface, M_CNFoliage). 0 to 2 belong to the shared
# Blueprints' own materials (BP_Hazard writes 0-2, BP_LightTrail and the Settle wave 0), so their writes never move it.
SEED_DATA = 3


def object_random(material, x, y):
    """PerInstanceRandom plus the actor's Seed: a different value for every scatter instance and every placed actor
    (0 on anything placed without a seed, as PerInstanceRandom alone is)."""
    total = node(material, unreal.MaterialExpressionAdd, x + 200, y)
    lib.connect_material_expressions(node(material, unreal.MaterialExpressionPerInstanceRandom, x, y), '', total, 'A')
    seed = node(material, unreal.MaterialExpressionScalarParameter, x, y + 80, parameter_name='Seed', default_value=0.0,
                use_custom_primitive_data=True, primitive_data_index=SEED_DATA)
    lib.connect_material_expressions(seed, '', total, 'B')
    return total


def seed_of(label):
    """An actor's Seed in [0, 1), fixed by its label, so a rebuild keeps every actor's look."""
    return zlib.crc32(label.encode('utf-8')) / 4294967296.0


def instance(name, parent, scalars=(), vectors=(), textures=(), switches=()):
    """Creates or re-parents MATS/name and sets exactly these overrides (stale ones are cleared first)."""
    path = MATS + '/' + name
    mi = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(mi, parent)
    lib.clear_all_material_instance_parameters(mi)
    for key, value in scalars:
        lib.set_material_instance_scalar_parameter_value(mi, key, float(value))
    for key, value in vectors:
        lib.set_material_instance_vector_parameter_value(mi, key, linear(value))
    for key, texture in textures:
        lib.set_material_instance_texture_parameter_value(mi, key, texture)
    for key, value in switches:
        lib.set_material_instance_static_switch_parameter_value(mi, key, value)
    lib.update_material_instance(mi)
    game.save(mi)
    return mi


# ---------------------------------------------------------------- looks (README "Materials and rendering")

SURFACE_DEFAULTS = {'Roughness': .5, 'RoughnessVariation': .12, 'Metallic': 0.0, 'Specular': .5, 'AlbedoVariation': .06,
                    'DetailScale': 90.0, 'NormalScale': 8.0, 'NormalStrength': .06, 'Veins': 0.0, 'VeinScale': 120.0,
                    'Brushed': 0.0, 'BrushScale': .35, 'EmissiveStrength': 0.0, 'Lift': 0.0, 'MaxAlbedo': .9,
                    # texture detail: off unless an instance names a set (DETAIL_SETS)
                    'DetailTile': 100.0, 'TriSharpness': 4.0, 'AlbedoDetail': 0.0, 'RoughDetail': 0.0, 'CavityAmount': 0.0,
                    'FeatureAmount': 0.0, 'FeatureFromBase': 1.0, 'FeatureRough': 0.0, 'DetailNormalStrength': 0.0,
                    # glow hue (GLOW_EMISSIVE), bare metal in the feature (METAL) and a wall foot's splash, all off at
                    # these values; the macro tone (SURFACE) varies every surface by up to 6 % over MacroScale cm
                    'ChromaScale': 1.0, 'RedScale': 1.0, 'MetalFeature': 0.0, 'Splash': 0.0, 'SplashH': 70.0,
                    'MacroScale': 3000.0, 'MacroVariation': .06}

# Slot instances of M_CNSurface: (scalars, vectors). Scales are centimetres in object space. Glow strengths are
# set for the level's exposure (EV100 about 2.5 to 4): 24 reads as a lit lamp or window, the Spine blooms.
# AlbedoVariation scales noise whose spread is about +-0.27, so 0.3 is about +-8 % (stone and plaster vary that much;
# 0.05 was +-1.4 %, which reads as flat CG paint). Normal waves start at NormalScale cm and fade under 8 pixels (MICRO).
SURFACES = {
    # Texture detail replaces the old procedural veins and brushing (Veins 0, Brushed 0) where a set carries them.
    # CN_White is tooled limestone (the Limestone set; 2026-11-07 review): dressings, stone walls and rock, its black
    # crust fainter than marble's veins. The Archive, the Shrine and the Orrery keep marble (MI_CN_Marble, MESH_LOOKS).
    'MI_CN_White': ({'Roughness': .5, 'RoughnessVariation': .12, 'AlbedoVariation': .2, 'DetailScale': 120, 'NormalScale': 35,
                     'NormalStrength': .03, 'Veins': 0.0, 'VeinScale': 140, 'DetailTile': 100, 'AlbedoDetail': .22,
                     'RoughDetail': .22, 'CavityAmount': .6, 'FeatureAmount': .45, 'FeatureFromBase': 0.0, 'FeatureRough': .04,
                     'DetailNormalStrength': 1.0}, {'Tint': WHITE1, 'VeinColour': PAL.grey(.42), 'FeatureColour': PAL.grey(.35)}),
    'MI_CN_Marble': ({'Roughness': .5, 'RoughnessVariation': .12, 'AlbedoVariation': .2, 'DetailScale': 120, 'NormalScale': 35,
                      'NormalStrength': .03, 'Veins': 0.0, 'VeinScale': 140, 'DetailTile': 120, 'AlbedoDetail': .22,
                      'RoughDetail': .22, 'CavityAmount': .6, 'FeatureAmount': .6, 'FeatureFromBase': 0.0, 'FeatureRough': .04,
                      'DetailNormalStrength': 1.0}, {'Tint': WHITE1, 'VeinColour': PAL.grey(.42), 'FeatureColour': PAL.grey(.30)}),
    # Lime render on the house and ruin walls (slot CN_Plaster, the Render set): matt, patchy limewash, damp at the foot.
    'MI_CN_Plaster': ({'Roughness': .82, 'RoughnessVariation': .1, 'AlbedoVariation': .15, 'DetailScale': 120, 'NormalScale': 35,
                       'NormalStrength': .02, 'DetailTile': 200, 'AlbedoDetail': .25, 'RoughDetail': .15, 'CavityAmount': .7,
                       'FeatureAmount': .8, 'FeatureFromBase': 0.0, 'FeatureRough': .1, 'DetailNormalStrength': .8,
                       'Splash': .18, 'SplashH': 70}, {'Tint': WHITE1, 'FeatureColour': PAL.grey(.42)}),
    'MI_CN_Black': ({'Roughness': .66, 'RoughnessVariation': .12, 'AlbedoVariation': .3, 'DetailScale': 70, 'NormalScale': 25,
                     'NormalStrength': .04, 'DetailTile': 140, 'AlbedoDetail': .45, 'RoughDetail': .25, 'CavityAmount': .6,
                     'FeatureAmount': .6, 'FeatureFromBase': 0.0, 'FeatureRough': -.35, 'DetailNormalStrength': 1.0},
                    {'Tint': WHITE1, 'FeatureColour': PAL.grey(.28)}),
    'MI_CN_Lacquer': ({'Roughness': .14, 'RoughnessVariation': .04, 'AlbedoVariation': .04, 'DetailScale': 200, 'NormalScale': 60,
                       'NormalStrength': .006, 'DetailTile': 80, 'AlbedoDetail': .04, 'RoughDetail': .2, 'CavityAmount': 0.0,
                       'FeatureAmount': .35, 'FeatureFromBase': 1.0, 'FeatureRough': .2, 'DetailNormalStrength': 1.0},
                      {'Tint': WHITE1, 'FeatureColour': PAL.grey(.6)}),
    # Satin enamel on the AL's and the robots' plates (MESH_LOOKS): rougher than lacquer, so white plates stop mirroring
    # the gold ground as tan.
    'MI_CN_Enamel': ({'Roughness': .3, 'RoughnessVariation': .1, 'Specular': .4, 'AlbedoVariation': .05, 'DetailScale': 150,
                      'NormalScale': 40, 'NormalStrength': .006, 'DetailTile': 80, 'AlbedoDetail': .06, 'RoughDetail': .25,
                      'CavityAmount': .2, 'FeatureAmount': .35, 'FeatureFromBase': 1.0, 'FeatureRough': .2,
                      'DetailNormalStrength': .8}, {'Tint': WHITE1, 'FeatureColour': PAL.grey(.6)}),
    'MI_CN_Metal': ({'Metallic': .9, 'Roughness': .35, 'RoughnessVariation': .08, 'AlbedoVariation': .1, 'DetailScale': 60,
                     'NormalScale': 14, 'NormalStrength': .01, 'Brushed': 0.0, 'BrushScale': .3, 'Lift': .35, 'MaxAlbedo': 1.0,
                     'DetailTile': 80, 'AlbedoDetail': .18, 'RoughDetail': .35, 'CavityAmount': .3, 'FeatureAmount': .5,
                     'FeatureFromBase': 1.0, 'FeatureRough': -.12, 'DetailNormalStrength': 1.0},
                    {'Tint': WHITE1, 'FeatureColour': PAL.grey(.66)}),
    # Painted, blackened iron on the Foundry's plant, the pylons, cranes and wrecks (MESH_LOOKS): a dark dielectric coat
    # with bright bare steel in the Steel set's scratches (MetalFeature), so it stops mirroring the gold land as rust brown.
    'MI_CN_Iron': ({'Metallic': .12, 'MetalFeature': .85, 'Lift': 0.0, 'Roughness': .55, 'RoughnessVariation': .1,
                    'AlbedoVariation': .12, 'DetailScale': 80, 'NormalScale': 20, 'NormalStrength': .015, 'MaxAlbedo': .9,
                    'DetailTile': 120, 'AlbedoDetail': .12, 'RoughDetail': .2, 'CavityAmount': .5, 'FeatureAmount': .6,
                    'FeatureFromBase': 0.0, 'FeatureRough': -.25, 'DetailNormalStrength': .7},
                   {'Tint': WHITE1, 'FeatureColour': PAL.grey(.45)}),
    # Polished gold, not glitter (2026-11-07 review): smoother, with fainter scratches and relief.
    'MI_CN_Gold': ({'Metallic': 1.0, 'Roughness': .18, 'RoughnessVariation': .06, 'AlbedoVariation': .04, 'DetailScale': 80,
                    'NormalScale': 16, 'NormalStrength': .008, 'Brushed': 0.0, 'BrushScale': .4, 'MaxAlbedo': 1.0,
                    'DetailTile': 60, 'AlbedoDetail': .06, 'RoughDetail': .12, 'CavityAmount': 0.0, 'FeatureAmount': .25,
                    'FeatureFromBase': 1.0, 'FeatureRough': .1, 'DetailNormalStrength': .35},
                   {'Tint': WHITE1, 'FeatureColour': PAL.grey(.58)}),
    'MI_CN_Red': ({'Roughness': .55, 'RoughnessVariation': .1, 'AlbedoVariation': .15, 'DetailScale': 90, 'NormalScale': 30,
                   'NormalStrength': .02, 'DetailTile': 120, 'AlbedoDetail': .22, 'RoughDetail': .22, 'CavityAmount': .5,
                   'FeatureAmount': .6, 'FeatureFromBase': 1.0, 'FeatureRough': .1, 'DetailNormalStrength': 1.0},
                  {'Tint': WHITE1, 'FeatureColour': PAL.grey(.32)}),
    'MI_CN_Blue': ({'Roughness': .18, 'RoughnessVariation': .05, 'AlbedoVariation': .1, 'DetailScale': 150, 'NormalScale': 40,
                    'NormalStrength': .01, 'DetailTile': 60, 'AlbedoDetail': .2, 'RoughDetail': .25, 'CavityAmount': .6,
                    'FeatureAmount': 1.0, 'FeatureFromBase': 0.0, 'FeatureRough': .5, 'DetailNormalStrength': 1.0},
                   {'Tint': WHITE1, 'FeatureColour': PAL.grey(.62)}),
    'MI_CN_Cloth': ({'Roughness': .92, 'RoughnessVariation': .04, 'AlbedoVariation': .15, 'Specular': .3, 'DetailScale': 50,
                     'NormalScale': 1.5, 'NormalStrength': .02, 'DetailTile': 20, 'AlbedoDetail': .3, 'RoughDetail': .1,
                     'CavityAmount': .6, 'FeatureAmount': .3, 'FeatureFromBase': 1.0, 'FeatureRough': .05,
                     'DetailNormalStrength': 1.0}, {'Tint': WHITE1, 'FeatureColour': PAL.grey(.6)}),
    # Tree bark (2026-11-07): trunks, limbs and stems had the stone and basalt sets; vertex colour still says white or black.
    'MI_CN_Bark': ({'Roughness': .78, 'RoughnessVariation': .08, 'AlbedoVariation': .15, 'DetailScale': 80, 'NormalScale': 20,
                    'NormalStrength': .02, 'DetailTile': 100, 'AlbedoDetail': .35, 'RoughDetail': .15, 'CavityAmount': .7,
                    'FeatureAmount': .7, 'FeatureFromBase': 1.0, 'FeatureRough': .05, 'DetailNormalStrength': 1.2},
                   {'Tint': WHITE1, 'FeatureColour': PAL.grey(.2)}),
    # Saturated glows at ChromaScale/RedScale of the strength keep their hue (red AL eyes, gold lamps, light-blue lights).
    'MI_CN_Glow': ({'Roughness': .4, 'RoughnessVariation': 0, 'AlbedoVariation': 0, 'NormalStrength': 0, 'EmissiveStrength': 24,
                    # RedScale .3 measured in the editor on 2026-11-08: the enemy barricades' red pixels rose from 5.9 to
                    # 14.3 % of the frame and the orange-red ones fell from 7.8 to 1.5 % (at .8 they bloomed orange).
                    'ChromaScale': .55, 'RedScale': .3},
                   {'Tint': PAL.grey(.2)}),
    # The AL's eyes, cores and emitters (MESH_LOOKS): their red at .3 of the strength, so the eye reads pure red, not a
    # coral or white blowout, and stays the brightest red on the unit.
    'MI_CN_ALGlow': ({'Roughness': .4, 'RoughnessVariation': 0, 'AlbedoVariation': 0, 'NormalStrength': 0, 'EmissiveStrength': 24,
                      'ChromaScale': .5, 'RedScale': .3},
                     {'Tint': PAL.grey(.2)}),
    # The lit Spine is the drum's sun: the level puts this on SpineLit's glow slots so it blooms like one.
    'MI_CN_SpineGlow': ({'Roughness': .4, 'RoughnessVariation': 0, 'AlbedoVariation': 0, 'NormalStrength': 0, 'EmissiveStrength': 120},
                        {'Tint': PAL.grey(.2)}),
    # The end caps' ring lights and bay are navigation lights a kilometre and more away, not lamps: on MI_CN_Glow they
    # were the brightest thing at the end of every view (drum() puts this on the caps' glow slots).
    'MI_CN_CapGlow': ({'Roughness': .4, 'RoughnessVariation': 0, 'AlbedoVariation': 0, 'NormalStrength': 0, 'EmissiveStrength': 6},
                      {'Tint': PAL.grey(.2)}),
}
# Which texture set (Tools/conclave_textures) each M_CNSurface instance samples; the rest keep the defaults (no detail).
DETAIL_SETS = {'MI_CN_White': 'Limestone', 'MI_CN_Marble': 'Stone', 'MI_CN_Plaster': 'Render', 'MI_CN_Black': 'Basalt',
               'MI_CN_Lacquer': 'Lacquer', 'MI_CN_Enamel': 'Lacquer', 'MI_CN_Metal': 'Steel', 'MI_CN_Iron': 'Steel',
               'MI_CN_Gold': 'Gold', 'MI_CN_Red': 'Plaster', 'MI_CN_Blue': 'Tile', 'MI_CN_Cloth': 'Cloth', 'MI_CN_Bark': 'Bark'}

# Slots whose surface needs its own shading model or blend mode get an instance of that master, so every slot in
# toolkit.SLOTS maps to an MI_CN_<slot> that can be tuned without recompiling a shader: (master, scalars, vectors).
# Empty overrides take the master's defaults. The glass, water and leaf variants are per-mesh looks (MESH_LOOKS).
SLOT_MASTERS = {'MI_CN_Leaf': ('M_CNFoliage', {}, {}),
                # Visible light-blue glass (its hue is the BLUE_PALE vertex colour).
                'MI_CN_Glass': ('M_CNGlass', {'Opacity': .2, 'FresnelOpacity': .75, 'Roughness': .03, 'Specular': .5}, {'Tint': WHITE1}),
                # The drum's windows, dark (2026-11-07): lit translucency on a pale tint made them a bright grey sheet at
                # the grazing angles they are seen at; real glass shows what is behind it plus a reflection, so space
                # reads black.
                'MI_CN_SpaceGlass': ('M_CNGlass', {'Opacity': .06, 'FresnelOpacity': .45, 'Roughness': .03}, {'Tint': PAL.grey(.03)}),
                # Window panes: a grey film that mirrors the drum at grazing angles and shows the rooms behind.
                'MI_CN_Pane': ('M_CNGlass', {'Opacity': .3, 'FresnelOpacity': .85, 'Roughness': .02}, {'Tint': PAL.grey(.35)}),
                # Glass lit from within (GLASS_GLOW): the Spire's crystal, light platforms and caches, lattices, the
                # Shrine; and Iriel's and the Wisp's veil of light.
                'MI_CN_LightGlass': ('M_CNGlass', {'Opacity': .14, 'FresnelOpacity': .6, 'Roughness': .05, 'Glow': 3.0}, {'Tint': WHITE1}),
                'MI_CP_LightVeil': ('M_CNGlass', {'Opacity': .25, 'FresnelOpacity': .7, 'Glow': 1.5}, {'Tint': WHITE1}),
                # Crowns of trees, shrubs, hedges and vines: their own canopy normals (no ground normal) and thinner cards.
                'MI_CN_LeafCrown': ('M_CNFoliage', {'GroundNormal': 0.0, 'CardSubsurfaceOpacity': .25}, {}),
                'MI_CN_LeafGreen': ('M_CNFoliage', {'GroundNormal': 0.0, 'CardSubsurfaceOpacity': .25},
                                    {'Tint': LEAF_GREEN_TINT, 'SubsurfaceTint': LEAF_GREEN_GLOW}),
                'MI_CN_Ground': ('M_CNGround', {}, {}),
                # M_CNWater's parameters are physis_conclave_ground.py's contract; its defaults are the lake's look.
                'MI_CN_Water': ('M_CNWater', {}, {}),
                # Basins, channels and the Orrery: clear grey water with no light-blue tint over their black beds (it
                # rendered navy or brown) and no foam at their rims.
                'MI_CN_WaterBasin': ('M_CNWater', {'TintDepth': 0.0, 'Clarity': 60.0, 'MaxOpacity': .55, 'FoamStrength': 0.0,
                                                   'Ripple': .15}, {'WaterColour': PAL.grey(.5)})}
SLOT_LOOK = {slot: 'MI_' + slot for slot in SLOTS}
# Per-mesh looks (2026-11-07 review): (mesh-name prefix, slot, instance), checked before SLOT_LOOK, first match wins. One
# CN_Glass look cannot be at once the drum's windows onto black space, a house's panes, the Spire's glowing crystal and
# Iriel's veil; basin water on black beds rendered navy; tree crowns want their own foliage settings. The AL's red eyes
# get their own glow, AL and robot plates satin enamel instead of mirror lacquer, the Foundry's plant, pylons, cranes
# and wrecks painted iron instead of polished steel, and only the Archive, the Shrine and the Orrery marble.
MESH_LOOKS = tuple([('SM_CV_TreeWhite', 'CN_Leaf', 'MI_CN_LeafGreen'), ('SM_CD_Windows', 'CN_Glass', 'MI_CN_SpaceGlass')]
                   + [(p, 'CN_Glass', 'MI_CN_Pane') for p in ('SM_CN_House', 'SM_CN_Archive', 'SM_CN_Mendery', 'SM_CN_Workshop',
                                                               'SM_CN_Crane', 'SM_CN_Stall', 'SM_CN_Lamp')]
                   + [(p, 'CN_Glass', 'MI_CN_LightGlass') for p in ('SM_CN_Spire', 'SM_CN_LightPlatform', 'SM_CN_LightRamp',
                                                                     'SM_CN_LightCache', 'SM_CN_Lattice', 'SM_CN_Shrine')]
                   + [('SM_CN_Orrery', 'CN_Glass', 'MI_CN_WaterBasin')]
                   + [(p, 'CN_Water', 'MI_CN_WaterBasin') for p in ('SM_CN_Orrery', 'SM_CN_WellGarden', 'SM_CN_Channel', 'SM_CN_Sluice')]
                   + [(p, 'CN_Glass', 'MI_CP_LightVeil') for p in ('SM_CP_Lightform', 'SM_CP_Wisp')]
                   + [(p, 'CN_Leaf', 'MI_CN_LeafCrown') for p in ('SM_CV_Tree', 'SM_CV_FruitTree', 'SM_CV_Shrub', 'SM_CV_Hedge',
                                                                   'SM_CV_Vines')]
                   + [('SM_CE_', 'CN_Glow', 'MI_CN_ALGlow'), ('SM_CE_', 'CN_Lacquer', 'MI_CN_Enamel')]
                   + [(p, 'CN_Lacquer', 'MI_CN_Enamel') for p in ('SM_CP_Robot', 'SM_CP_Courier', 'SM_CP_Mechanoid', 'SM_CP_Mecha')]
                   + [(p, 'CN_Metal', 'MI_CN_Iron') for p in ('SM_CN_Furnace', 'SM_CN_Workshop', 'SM_CN_Crane', 'SM_CN_PipeRack',
                                                              'SM_CN_PipeBridge', 'SM_CN_Pylon', 'SM_CN_Sluice', 'SM_CN_Board',
                                                              'SM_CN_Lift', 'SM_CN_Cradle', 'SM_CN_Freighter')]
                   + [(p, 'CN_White', 'MI_CN_Marble') for p in ('SM_CN_Archive', 'SM_CN_Shrine', 'SM_CN_Orrery')]
                   # The figures' white ceramic plates (Halden-7, Quill, Ilex, Patience) are CN_White: they keep the
                   # look they had (marble's values) rather than turn tooled limestone, until a people round decides.
                   + [('SM_CP_', 'CN_White', 'MI_CN_Marble')])
_UNDEFINED = sorted(look for look in list(SLOT_LOOK.values()) + [row[2] for row in MESH_LOOKS]
                    if look not in SURFACES and look not in SLOT_MASTERS)
if _UNDEFINED:
    raise ValueError('toolkit.SLOTS or MESH_LOOKS name material instances not defined here: ' + ', '.join(_UNDEFINED))

SKY_LOOK = {'PlanetDir': (.30, .80, .52), 'SunDir': (.75, -.35, .55), 'PlanetAxis': (-.20, -.05, .98)}  # directions, not colours
SKY_COLOURS = {'StarColour': PAL.LIGHT_WHITE, 'MilkyColour': PAL.WHITE_COOL, 'BandA': PAL.GOLD_PALE, 'BandB': PAL.WHITE,
               'BandC': PAL.BLUE_PALE, 'RimColour': PAL.LIGHT_BLUE, 'RingA': PAL.IVORY, 'RingB': PAL.WHITE_COOL}
SKY_SCALARS = {'StarBright': 40.0, 'MilkyBright': .25, 'Radius': .22, 'Inner': 1.35, 'Outer': 2.3, 'Gap': 1.95,
               'PlanetBright': 6.0, 'RimBright': 1.5, 'RingBright': 5.0}

# The Spine in thirds (m): the SpineDim/SpineLit meshes and their halos. The halo (HALO) is the glowing air around a lit
# third: a Gaussian HALO_SIGMA cm wide at HALO_INTENSITY. If the gold strips overhead lose their hue within 5 degrees of
# the Spine, narrow it to 1800.
SPINE_THIRD = 2 * plan.HALF_X / 3
HALO_SIGMA = 2500.0
HALO_INTENSITY = 30.0

# Divinity Rays (the Center's M_DivinityRay): gold over puzzles, light blue over Light Caches, red over vaults
# (violet is not in the palette). Intensities are for this level's daylight exposure, about 20 times the Center's
# night (its instances use 0.5 to 0.65). The vaults' ray is pure red and dimmer: LIGHT_RED at 12 bloomed coral.
RAY_LOOKS = {'MI_CNRay_Puzzle': (PAL.LIGHT_GOLD, 12.0), 'MI_CNRay_Cache': (PAL.LIGHT_BLUE, 10.0), 'MI_CNRay_Vault': (GLOW_RED, 5.0)}

# The people's skins on any Mannequin slot (Quinn or Manny, body or torso): the slots use different texture sets,
# so the contract's single instance per skin gets neutral textures (white base, flat normal, linear white MRA)
# and its look from the parameters. Logo off: M_Mannequin's logo glows cyan, which is not in the palette.
SKINS = {'MI_CP_Porcelain': (PAL.WHITE_COOL, .22), 'MI_CP_Obsidian': (PAL.BLACK, .16)}
MANNEQUIN = '/Game/Characters/Mannequins/Materials/M_Mannequin'


# ---------------------------------------------------------------- materials

TEXTURES = CONCLAVE + '/Textures'
TEXTURE_ART = ROOT / 'Art/Textures/Conclave'


def detail_sets():
    """Tools/conclave_textures' manifest: {set: {'tile_cm', 'size', 'for'}}."""
    path = TEXTURE_ART / 'textures.json'
    return json.loads(path.read_text()) if path.exists() else {}


def detail_texture(name, kind):
    """T_CN_<name>_<kind> (kind 'M' masks or 'N' normal), imported by conclave:textures."""
    texture = unreal.load_asset('%s/T_CN_%s_%s' % (TEXTURES, name, kind))
    if texture is None:
        raise RuntimeError('T_CN_%s_%s is missing: run Tools/conclave_textures/textures.py, then conclave:textures' % (name, kind))
    return texture


def import_textures():
    """Imports every set's maps as linear data: _N as a BC5 normal map, _M as BC7 RGBA masks."""
    report = {}
    for name in sorted(detail_sets()):
        for kind in ('M', 'N'):
            source = TEXTURE_ART / ('T_CN_%s_%s.png' % (name, kind))
            game.import_file(str(source), TEXTURES)
            texture = unreal.load_asset('%s/T_CN_%s_%s' % (TEXTURES, name, kind))
            texture.set_editor_property('srgb', False)
            if kind == 'N':
                texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
                texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
            else:
                texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_BC7)
                texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
            game.save(texture)
        report[name] = 'ok'
    # The foliage atlas: masks with alpha (BC7), mips that keep each card's alpha coverage so leaves do not thin out
    # with distance, and its normal map.
    for kind in ('M', 'N'):
        source = TEXTURE_ART / ('T_CN_LeafAtlas_%s.png' % kind)
        if not source.exists():
            report['LeafAtlas'] = 'missing: run Tools/conclave_textures/atlas.py'
            break
        game.import_file(str(source), TEXTURES)
        texture = unreal.load_asset('%s/T_CN_LeafAtlas_%s' % (TEXTURES, kind))
        texture.set_editor_property('srgb', False)
        if kind == 'N':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP)
        else:
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_BC7)
            texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
            for key, value in (('do_scale_mips_for_alpha_coverage', True),
                               ('alpha_coverage_thresholds', unreal.Vector4(0.0, 0.0, 0.0, .5))):
                try:
                    texture.set_editor_property(key, value)
                except Exception as error:
                    report.setdefault('atlas_skipped', []).append('%s: %s' % (key, error))
        game.save(texture)
        report['LeafAtlas'] = 'ok'
    return report


def leaf_atlas(kind):
    """T_CN_LeafAtlas_<kind> (Tools/conclave_textures/atlas.py), imported by conclave:textures."""
    texture = unreal.load_asset('%s/T_CN_LeafAtlas_%s' % (TEXTURES, kind))
    if texture is None:
        raise RuntimeError('T_CN_LeafAtlas_%s is missing: run Tools/conclave_textures/atlas.py, then conclave:textures' % kind)
    return texture


def detail_parameters(material, x, y, prefix='Detail', set_name='Stone'):
    """The masks and normal texture-object parameters a detail Custom node samples."""
    masks = node(material, unreal.MaterialExpressionTextureObjectParameter, x, y, parameter_name=prefix + 'Masks',
                 texture=detail_texture(set_name, 'M'), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    normal = node(material, unreal.MaterialExpressionTextureObjectParameter, x, y + 150, parameter_name=prefix + 'Normal',
                  texture=detail_texture(set_name, 'N'), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    return masks, normal


# The MetaHuman people's costumes are skinned meshes in the Conclave's own slot looks (PEOPLE_DESIGN.md 3.3), so the
# surface master also compiles for skeletal meshes; surface_skeletal() sets just this on the existing master.
SURFACE_SKINNED = {'used_with_skeletal_mesh': True}


def material_surface():
    # Normal curvature to roughness: roughness rises where the normal bends within a pixel (bevels, gold rims), so
    # polished edges stop sparkling at a distance. A refusal is reported in SKIPPED.
    m = master('M_CNSurface', tangent_space_normal=False, used_with_instanced_static_meshes=True, normal_curvature_to_roughness=True,
               **SURFACE_SKINNED)
    vc = node(m, unreal.MaterialExpressionVertexColor, -1700, -500)
    lp = node(m, unreal.MaterialExpressionLocalPosition, -1700, -380)
    rnd = object_random(m, -1900, -300)
    vn = node(m, unreal.MaterialExpressionVertexNormalWS, -1700, 800)
    values = {}
    for i, (name, value) in enumerate(SURFACE_DEFAULTS.items()):
        values[name] = scalar(m, name, value, -1400, -500 + i * 80)
    ln = transform(m, vn, WORLD_TO_LOCAL, -1400, 900)
    tex_m, tex_n = detail_parameters(m, -2300, -900)
    tri_m = custom(m, TRI_M, [('LP', lp), ('LN', ln), ('TexM', tex_m), ('Tile', values['DetailTile']),
                              ('Sharp', values['TriSharpness']), ('Rnd', rnd)], -1150, -900, FLOAT4)
    surf = custom(m, SURFACE, [('VC', vc), ('Tint', cparam(m, 'Tint', WHITE1, -1400, 800)), ('LP', lp), ('Rnd', rnd),
                               ('N', ln), ('Var', values['AlbedoVariation']),
                               ('R0', values['Roughness']), ('RVar', values['RoughnessVariation']), ('Scale', values['DetailScale']),
                               ('Veins', values['Veins']), ('VScale', values['VeinScale']),
                               ('VCol', cparam(m, 'VeinColour', PAL.grey(.42), -1400, 1000)), ('Brushed', values['Brushed']),
                               ('BScale', values['BrushScale']), ('Lift', values['Lift']), ('MaxA', values['MaxAlbedo']),
                               ('DM', tri_m), ('AD', values['AlbedoDetail']), ('RD', values['RoughDetail']),
                               ('CA', values['CavityAmount']), ('FA', values['FeatureAmount']),
                               ('FC', cparam(m, 'FeatureColour', PAL.grey(.5), -1400, 1100)), ('FB', values['FeatureFromBase']),
                               ('FR', values['FeatureRough']), ('Splash', values['Splash']), ('SplashH', values['SplashH']),
                               ('MacroScale', values['MacroScale']), ('MacroVariation', values['MacroVariation'])],
                  -900, -300, FLOAT4)
    lib.connect_material_property(mask(m, surf, 'rgb', -500, -400), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(mask(m, surf, 'a', -500, -250), '', PROP.MP_ROUGHNESS)
    metal = custom(m, METAL, [('M', values['Metallic']), ('MF', values['MetalFeature']), ('DM', tri_m), ('FA', values['FeatureAmount'])],
                   -500, -100, FLOAT1)
    lib.connect_material_property(metal, '', PROP.MP_METALLIC)
    lib.connect_material_property(values['Specular'], '', PROP.MP_SPECULAR)
    grad = custom(m, MICRO, [('LP', lp), ('Rnd', rnd), ('Scale', values['NormalScale'])], -1100, 600, FLOAT3)
    tri_n = custom(m, TRI_N, [('LP', lp), ('LN', ln), ('TexN', tex_n), ('Tile', values['DetailTile']),
                              ('Sharp', values['TriSharpness']), ('Rnd', rnd), ('K', values['DetailNormalStrength'])],
                   -1150, 750, FLOAT3)
    textured = transform(m, tri_n, LOCAL_TO_WORLD, -850, 750)
    normal = custom(m, PERTURB, [('VN', textured), ('G', transform(m, grad, LOCAL_TO_WORLD, -850, 600)), ('K', values['NormalStrength'])],
                    -500, 600, FLOAT3)
    lib.connect_material_property(normal, '', PROP.MP_NORMAL)
    glow = custom(m, GLOW_EMISSIVE, [('VC', vc), ('Strength', values['EmissiveStrength']), ('ChromaScale', values['ChromaScale']),
                                    ('RedScale', values['RedScale'])], -500, 200, FLOAT3)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


# The costume masters: M_CNSurface for cloth, metal and gold, M_CNGlass for Petra's spectacle lenses (2026-11-09).
SKINNED_MASTERS = ('M_CNSurface', 'M_CNGlass')


def surface_skeletal():
    """SKINNED_MASTERS with SURFACE_SKINNED set and recompiled, nothing else: conclave:materials rebuilds every master
    (the ground and water too), which the people's costume import does not need."""
    report = {}
    for name in SKINNED_MASTERS:
        path = MATS + '/' + name
        if not library.does_asset_exist(path):
            raise RuntimeError('%s is missing: run conclave:materials first' % path)
        material = unreal.load_asset(path)
        before = {key: material.get_editor_property(key) for key in SURFACE_SKINNED}
        for key, value in SURFACE_SKINNED.items():
            material.set_editor_property(key, value)
        finish(material)
        report[name] = {'before': before, 'after': {key: material.get_editor_property(key) for key in SURFACE_SKINNED}}
    return report


def surface_instances():
    """Every slot's instance: M_CNSurface's (SURFACES) and the other masters' (SLOT_MASTERS). Masters first, since
    instance() re-parents onto whatever asset is loaded."""
    parent = unreal.load_asset(MATS + '/M_CNSurface')
    for name, (scalars, vectors) in SURFACES.items():
        merged = dict(SURFACE_DEFAULTS)
        merged.update(scalars)
        sets = DETAIL_SETS.get(name)
        textures = (('DetailMasks', detail_texture(sets, 'M')), ('DetailNormal', detail_texture(sets, 'N'))) if sets else ()
        instance(name, parent, merged.items(), vectors.items(), textures)
    for name, (base, scalars, vectors) in SLOT_MASTERS.items():
        instance(name, unreal.load_asset(MATS + '/' + base), scalars.items(), vectors.items())
    return sorted(SURFACES) + sorted(SLOT_MASTERS)


def material_foliage():
    m = master('M_CNFoliage', two_sided=True, shading_model=unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,
               used_with_instanced_static_meshes=True, tangent_space_normal=False, blend_mode=unreal.BlendMode.BLEND_MASKED,
               opacity_mask_clip_value=.5, dithered_lod_transition=True)
    vc = node(m, unreal.MaterialExpressionVertexColor, -1300, -300)
    lp = node(m, unreal.MaterialExpressionLocalPosition, -1300, -150)
    rnd = object_random(m, -1500, -50)
    uv = node(m, unreal.MaterialExpressionTextureCoordinate, -1700, -650, coordinate_index=0)
    atlas = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1450, -700, parameter_name='Atlas',
                 texture=leaf_atlas('M'), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    lib.connect_material_expressions(uv, '', atlas, 'UVs')
    atlas_n = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1450, 820, parameter_name='AtlasNormal',
                   texture=leaf_atlas('N'), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    lib.connect_material_expressions(uv, '', atlas_n, 'UVs')
    # Leaf cuticle is waxy (F0 about 0.04, so Specular 0.5, roughness about 0.55): the sun glints on canopies.
    leaf = custom(m, LEAF, [('VC', vc), ('Tint', cparam(m, 'Tint', WHITE1, -1000, -400)), ('LP', lp), ('Rnd', rnd),
                            ('Var', scalar(m, 'AlbedoVariation', .18, -1000, -300)), ('Scale', scalar(m, 'DetailScale', 140.0, -1000, -220)),
                            ('R0', scalar(m, 'Roughness', .55, -1000, -140)), ('RVar', scalar(m, 'RoughnessVariation', .12, -1000, -60))],
                  -700, -250, FLOAT4)
    va = (vc, 'A')
    rgba = (atlas, 'RGBA')
    carded = custom(m, LEAF_CARD, [('VA', va), ('Leaf', leaf), ('A', rgba), ('Detail', scalar(m, 'CardDetail', .55, -1000, -520)),
                                   ('RD', scalar(m, 'CardRoughDetail', .2, -1000, -600)),
                                   ('Stem', cparam(m, 'StemColour', PAL.CHARCOAL, -1000, -680))], -450, -300, FLOAT4)
    lib.connect_material_property(mask(m, carded, 'rgb', -200, -300), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(mask(m, carded, 'a', -200, -180), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(scalar(m, 'Specular', .5, -400, -60), '', PROP.MP_SPECULAR)
    lib.connect_material_property(custom(m, LEAF_MASK, [('VA', va), ('A', rgba)], -450, 0, FLOAT1), '', PROP.MP_OPACITY_MASK)
    light = custom(m, LEAF_LIGHT, [('VC', vc), ('VA', va), ('A', rgba), ('Sub', cparam(m, 'SubsurfaceTint', WHITE1, -1000, 100)),
                                   ('K', scalar(m, 'SubsurfaceStrength', .8, -1000, 200)),
                                   ('TB', scalar(m, 'TransmissionBright', .55, -1000, 280))], -700, 120, FLOAT3)
    lib.connect_material_property(custom(m, LEAF_OPACITY, [('VA', va), ('Card', scalar(m, 'CardSubsurfaceOpacity', .2, -1000, 360)),
                                                           ('Solid', scalar(m, 'SolidSubsurfaceOpacity', .6, -1000, 440))],
                                         -700, 250, FLOAT1), '', PROP.MP_OPACITY)
    lib.connect_material_property(light, '', PROP.MP_SUBSURFACE_COLOR)
    tangent = custom(m, LEAF_TANGENT, [('N', atlas_n), ('K', scalar(m, 'CardNormal', .8, -1200, 950))], -1100, 850, FLOAT3)
    tn = transform(m, tangent, TANGENT_TO_WORLD, -900, 850)
    normal = custom(m, LEAF_NORMAL, [('VN', node(m, unreal.MaterialExpressionVertexNormalWS, -1300, 650)), ('LP', lp), ('VA', va),
                                     ('TN', tn), ('Up', scalar(m, 'GroundNormal', 1.0, -1000, 650)),
                                     ('UpHeight', scalar(m, 'GroundNormalHeight', 150.0, -1000, 730))], -700, 650, FLOAT3)
    lib.connect_material_property(normal, '', PROP.MP_NORMAL)
    wind = custom(m, WIND, [('LP', lp), ('WP', node(m, unreal.MaterialExpressionWorldPosition, -1300, 400)),
                            ('T', node(m, unreal.MaterialExpressionTime, -1300, 500)), ('Speed', scalar(m, 'WindSpeed', 1.1, -1000, 400)),
                            ('Amount', scalar(m, 'WindAmount', 2.4, -1000, 480)), ('Flutter', scalar(m, 'Flutter', .7, -1000, 560))],
                  -700, 450, FLOAT3)
    lib.connect_material_property(wind, '', PROP.MP_WORLD_POSITION_OFFSET)
    return finish(m)


def material_glass():
    m = master('M_CNGlass', blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, two_sided=True,
               translucency_lighting_mode=unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,
               screen_space_reflections=True, compute_fog_per_pixel=True, **SURFACE_SKINNED)  # Petra's lenses
    vc = node(m, unreal.MaterialExpressionVertexColor, -1000, -200)
    base = custom(m, GLASS_BASE, [('VC', vc), ('Tint', cparam(m, 'Tint', WHITE1, -1000, -80))], -600, -200, FLOAT3)
    lib.connect_material_property(base, '', PROP.MP_BASE_COLOR)
    opacity = custom(m, GLASS_OPACITY, [('O', scalar(m, 'Opacity', .12, -1000, 100)),
                                        ('F', node(m, unreal.MaterialExpressionFresnel, -1000, 200, exponent=5.0)),
                                        ('FO', scalar(m, 'FresnelOpacity', .55, -1000, 300))], -600, 150, FLOAT1)
    lib.connect_material_property(opacity, '', PROP.MP_OPACITY)
    lib.connect_material_property(scalar(m, 'Roughness', .04, -600, 350), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(scalar(m, 'Specular', .5, -600, 450), '', PROP.MP_SPECULAR)
    glow = custom(m, GLASS_GLOW, [('VC', vc), ('Glow', scalar(m, 'Glow', 0.0, -1000, 450)),
                                  ('F', node(m, unreal.MaterialExpressionFresnel, -1000, 550, exponent=3.0))], -600, 550, FLOAT3)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def material_sky():
    m = master('M_CNSky', shading_model=unreal.MaterialShadingModel.MSM_UNLIT, two_sided=True)
    inputs = [('V', node(m, unreal.MaterialExpressionCameraVectorWS, -1300, -400))]
    y = -300
    for name, value in SKY_LOOK.items():
        inputs.append((name, param(m, name, tuple(float(v) for v in value), -1300, y)))
        y += 100
    for name, value in SKY_COLOURS.items():
        inputs.append((name, cparam(m, name, value, -1300, y)))
        y += 100
    for name, value in SKY_SCALARS.items():
        inputs.append((name, scalar(m, name, value, -1300, y)))
        y += 80
    # The drum's air in front of the windows (see SKY), matched to the height fog that lighting() places: both of its
    # layers, with the component's densities and falloffs per 1000 cm as the engine passes them to its shaders.
    inputs += [('Cam', node(m, unreal.MaterialExpressionCameraPositionWS, -1300, y)),
               ('HazeColour', cparam(m, 'HazeColour', FOG_TINT, -1300, y + 100))]
    y += 200
    for name, value in (('HazeDensity', FOG['fog_density'] / 1000.0), ('HazeFalloff', FOG['fog_height_falloff'] / 1000.0),
                        ('Haze2Density', FOG_FLOOR['fog_density'] / 1000.0), ('Haze2Falloff', FOG_FLOOR['fog_height_falloff'] / 1000.0),
                        ('HazeBase', FOG_BASE), ('Haze2Base', FOG_BASE + FOG_FLOOR['fog_height_offset']),
                        ('HazeBright', FOG_BRIGHT),
                        ('HazeStart', FOG['start_distance']), ('HazeMax', FOG['fog_max_opacity']), ('SkyHaze', SKY_HAZE),
                        ('AxisZ', plan.AXIS_Z * CM), ('DrumR', plan.R * CM), ('HalfX', plan.HALF_X * CM)):
        inputs.append((name, scalar(m, name, value, -1300, y)))
        y += 80
    lib.connect_material_property(custom(m, SKY, inputs, -700, 0, FLOAT3), '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def material_light_trail():
    m = master('M_CNLightTrail', shading_model=unreal.MaterialShadingModel.MSM_UNLIT, blend_mode=unreal.BlendMode.BLEND_ADDITIVE,
               two_sided=True, compute_fog_per_pixel=True, translucency_pass=unreal.MaterialTranslucencyPass.MTP_AFTER_DOF)
    fade = node(m, unreal.MaterialExpressionScalarParameter, -1000, 300, parameter_name='Fade', default_value=1.0,
                use_custom_primitive_data=True, primitive_data_index=0)
    glow = custom(m, TRAIL, [('F', node(m, unreal.MaterialExpressionFresnel, -1000, -200, exponent=1.5)),
                             ('LP', node(m, unreal.MaterialExpressionLocalPosition, -1000, -100)),
                             ('T', node(m, unreal.MaterialExpressionTime, -1000, 0)), ('Fade', fade),
                             ('Intensity', scalar(m, 'Intensity', 18.0, -1000, 400)),
                             ('Edge', cparam(m, 'EdgeColour', PAL.LIGHT_BLUE, -1000, 500)),
                             ('Core', cparam(m, 'CoreColour', PAL.LIGHT_WHITE, -1000, 600))], -500, 100, FLOAT3)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def material_spine_halo():
    """M_CNSpineHalo (HALO) for the 'Spine Halo N' cylinders. Unlit and additive after depth of field, like the light
    trail; no vertex fog, which over a 533 m cylinder's few vertices would be wrong everywhere between them."""
    m = master('M_CNSpineHalo', shading_model=unreal.MaterialShadingModel.MSM_UNLIT, blend_mode=unreal.BlendMode.BLEND_ADDITIVE,
               two_sided=False, translucency_pass=unreal.MaterialTranslucencyPass.MTP_AFTER_DOF, use_translucency_vertex_fog=False)
    halo = custom(m, HALO, [('V', node(m, unreal.MaterialExpressionCameraVectorWS, -1000, -300)),
                            ('Cam', node(m, unreal.MaterialExpressionCameraPositionWS, -1000, -200)),
                            ('OP', node(m, unreal.MaterialExpressionObjectPositionWS, -1000, -100)),
                            ('AxisZ', scalar(m, 'AxisZ', plan.AXIS_Z * CM, -1000, 0)),
                            ('Sigma', scalar(m, 'Sigma', HALO_SIGMA, -1000, 80)),
                            ('HalfLen', scalar(m, 'HalfLen', SPINE_THIRD / 2 * CM, -1000, 160)),
                            ('Intensity', scalar(m, 'Intensity', HALO_INTENSITY, -1000, 240)),
                            ('Colour', cparam(m, 'Colour', PAL.LIGHT_WHITE, -1000, 320))], -500, 0, FLOAT3)
    lib.connect_material_property(halo, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def material_furnace():
    m = master('M_CNFurnace')
    wp = node(m, unreal.MaterialExpressionWorldPosition, -1400, -300)
    bars = custom(m, FURNACE_BARS, [('WP', wp), ('Cell', scalar(m, 'Cell', 30.0, -1100, -400)), ('Bar', scalar(m, 'Bar', 3.0, -1100, -320))],
                  -800, -350, FLOAT1)
    surface = custom(m, FURNACE_SURFACE, [('B', bars), ('Iron', cparam(m, 'Iron', PAL.SLATE, -800, -200)),
                                          ('Pit', cparam(m, 'Pit', PAL.BLACK, -800, -100))], -500, -250, FLOAT4)
    lib.connect_material_property(mask(m, surface, 'rgb', -250, -300), '', PROP.MP_BASE_COLOR)
    lib.connect_material_property(mask(m, surface, 'a', -250, -180), '', PROP.MP_ROUGHNESS)
    lib.connect_material_property(multiply(m, bars, scalar(m, 'Metal', .35, -800, 0), -500, -50), '', PROP.MP_METALLIC)
    heat = node(m, unreal.MaterialExpressionScalarParameter, -1100, 300, parameter_name='Heat', default_value=1.0,
                use_custom_primitive_data=True, primitive_data_index=0)
    glow = custom(m, FURNACE_GLOW, [('WP', wp), ('T', node(m, unreal.MaterialExpressionTime, -1100, 200)), ('Heat', heat),
                                    ('VC', node(m, unreal.MaterialExpressionVertexColor, -1100, 400)), ('B', bars),
                                    ('Red', cparam(m, 'HotRed', GLOW_RED, -1100, 500)),
                                    ('Gold', cparam(m, 'HotGold', PAL.LIGHT_GOLD, -1100, 600)),
                                    ('Strength', scalar(m, 'GlowStrength', 30.0, -1100, 700))], -500, 300, FLOAT3)
    lib.connect_material_property(glow, '', PROP.MP_EMISSIVE_COLOR)
    return finish(m)


def ray_instances():
    """MI_CNRay_* of the Center's M_DivinityRay. Rerun after center:rays: a rebuilt M_DivinityRay leaves its
    instances without a parent. Bottom and Top are the engine cylinder's local extent, which BP_DivinityRay uses."""
    parent = unreal.load_asset('/Game/Center/Materials/M_DivinityRay')
    if parent is None:
        raise RuntimeError('M_DivinityRay is missing: run center:rays first')
    box = unreal.load_asset('/Engine/BasicShapes/Cylinder').get_bounding_box()
    for name, (rgb, power) in RAY_LOOKS.items():
        instance(name, parent, (('Intensity', power), ('Bottom', box.min.z), ('Top', box.max.z), ('Rise', .004), ('Taper', .7)),
                 (('Colour', rgb),))
    return {'rays': sorted(RAY_LOOKS), 'cylinder_z': [box.min.z, box.max.z]}


def white_png(size=4):
    """A size x size opaque white RGBA PNG (no imaging library in the editor's Python)."""
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    rows = b''.join(b'\x00' + b'\xff' * (size * 4) for _ in range(size))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def linear_white():
    """T_CN_LinearWhite: M_Mannequin samples its MRA as Linear Color, which refuses the engine's sRGB white."""
    path = MATS + '/T_CN_LinearWhite'
    if not library.does_asset_exist(path):
        source = ROOT / 'Saved/Conclave/T_CN_LinearWhite.png'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(white_png())
        game.import_file(str(source), MATS)
    texture = unreal.load_asset(path)
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)
    game.save(texture)
    return texture


def skins():
    parent = unreal.load_asset(MANNEQUIN)
    if parent is None:
        raise RuntimeError(MANNEQUIN + ' is missing')
    textures = (('Base Texture', unreal.load_asset('/Engine/EngineResources/WhiteSquareTexture')),
                ('BNormal', unreal.load_asset('/Engine/EngineMaterials/FlatNormal')), ('MRA', linear_white()))
    for name, (tint, rough) in SKINS.items():
        instance(name, parent, (('MetalPaintMetallic', 0.0), ('MetalPaintRoughness', rough), ('EmissivePower', 0.0)),
                 (('Paint Tint', tint), ('LogoTint', PAL.GOLD)), textures, (('Logo?', False),))
    return sorted(SKINS)


def ground_module():
    """Content/Python/physis_conclave_ground.py, which builds M_CNGround and M_CNWater with this module's helpers. It is
    reloaded here because the conclave: dispatcher (physis_outfit_tools) reloads only the plan, the lore and this module."""
    import importlib
    import physis_conclave_ground
    importlib.reload(physis_conclave_ground)
    return physis_conclave_ground


def materials():
    del SKIPPED[:]
    ground = ground_module()
    sky = material_sky()
    made = [material_surface(), material_foliage(), material_glass(), ground.material_ground(), ground.material_water(), sky,
            material_light_trail(), material_furnace(), material_spine_halo()]
    report = {m.get_name(): lib.get_statistics(m).num_pixel_shader_instructions for m in made}
    # The level's sky wears an instance (sky(), apply_look.py), so SkyHaze and HazeBright tune without a recompile.
    instance('MI_CNSky', sky)
    report['instances'] = surface_instances() + ['MI_CNSky']
    report['skins'] = skins()
    try:
        report.update(ray_instances())
    except RuntimeError as error:
        # The rays only need the Center's M_DivinityRay; the rest of the look must not wait for it.
        report['rays'] = str(error)
    report['relinked'] = relink()
    report['skipped'] = list(SKIPPED)
    return report


# ---------------------------------------------------------------- import

# SLOT_LOOK (slot name -> MI_CN_<slot>) is built from toolkit.SLOTS with the looks above.

# Sections that never collide: Physis walks through leaves and into water (the lake's swimming is a volume).
PASS_THROUGH = ('CN_Leaf', 'CN_Water')
# One box, so no gap between bars, emitters or sheets lets Physis through until the lock opens.
BOX_MESHES = ('SM_CN_Lattice', 'SM_CN_Barricade', 'SM_CN_VaultDoor')
# No collision: people, figures and enemies (BP_NPC is talked to by distance and blocks nothing; the enemies'
# Blueprints keep their own hit rules), items and pickups (walked into), light that is only light, small plants and leaf
# litter, the water surface, and the Spine and upper lands 700 m up.
NO_COLLISION = ('SM_CP_', 'SM_CE_', 'SM_CN_Kite', 'SM_CN_MemoryCore', 'SM_CN_LedgerPage', 'SM_CN_SeedPod', 'SM_CN_LightCache',
                'SM_CN_Aug', 'SM_CN_Pickup', 'SM_CN_PylonBeam', 'SM_CV_GrassGold', 'SM_CV_Wheat', 'SM_CV_Flowers', 'SM_CV_Reeds',
                'SM_CV_Lily', 'SM_CV_Vines', 'SM_CV_Litter', 'SM_CD_Water', 'SM_CD_Spine', 'SM_CD_UpperLand')
# LOD chains of (triangle fraction, screen size), by mesh prefix (lod_chain()). Nanite is off, so a mesh without one
# draws every triangle at every distance.
LODS = ((1.0, 1.0), (.5, .35), (.25, .15), (.1, .05))  # the Center's chain: rocks and the AL
# Card plants get no reduction LODs at all: quadric reduction deletes whole cards while their solid parts survive, so
# hedges turned into red sofas and shrubs into blotches 6 to 40 m away (2026-11-07 review).
NO_LOD = ('SM_CV_GrassGold', 'SM_CV_Lily', 'SM_CV_Litter', 'SM_CV_Shrub', 'SM_CV_Hedge', 'SM_CV_Vines')
# Trees step down gently, so a crown still reads as a crown at about 115 m.
TREES = ('SM_CV_Tree', 'SM_CV_FruitTree')
TREE_LODS = ((1.0, 1.0), (.7, .1), (.45, .03))
# Wheat, flowers and reeds are thin blades and stems: on LODS a tuft reached its 10 % LOD 12 m away and became a few
# dark slivers, so meadows read as sparse specks. Two gentle steps instead (wheat: 15 m and 36 m).
PLANT_LODS = ((1.0, 1.0), (.55, .07), (.3, .03))
SMALL_PLANTS = ('SM_CV_Wheat', 'SM_CV_Flowers', 'SM_CV_Reeds')
# The town's buildings and street furniture, placed by the hundred.
BUILDINGS = ('SM_CN_House', 'SM_CN_Ruin', 'SM_CN_TerraceWall', 'SM_CN_Stairs', 'SM_CN_Lamp', 'SM_CN_Bench', 'SM_CN_Gate',
             'SM_CN_Archive', 'SM_CN_Stall', 'SM_CN_Planter')
BUILDING_LODS = ((1.0, 1.0), (.5, .2), (.25, .08), (.12, .03))
# Terrain tiles are 200 x 350 m: they switch only when far, so a seam shifted by reduction stays under a pixel.
TERRAIN_LODS = ((1.0, 1.0), (.5, .45), (.25, .2))


def slot_name(slot):
    # Blender's duplicate suffix (.001) may arrive as _001 after the importer's renaming.
    return re.sub(r'[._]\d{3}$', '', str(slot.get_editor_property('material_slot_name')))


def apply_slots(mesh):
    """Sets every slot's material from its name; returns the slot names no look exists for."""
    unknown = []
    changed = False
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = slot_name(slot)
        look = next((row[2] for row in MESH_LOOKS if mesh.get_name().startswith(row[0]) and row[1] == name), SLOT_LOOK.get(name))
        if look is None:
            unknown.append(name)
            look = 'MI_CN_White'
        material = unreal.load_asset(MATS + '/' + look)
        if material is not None and slot.get_editor_property('material_interface') != material:
            mesh.set_material(index, material)
            changed = True
    return unknown, changed


def collision_kind(stem):
    if stem in BOX_MESHES:
        return 'box'
    if stem.startswith(NO_COLLISION):
        return 'none'
    return 'complex'


def collision(mesh, kind):
    """Per-polygon collision is double-sided (the Center learned that one-sided collision lets Physis into a solid
    and then holds her inside). Sections map to slots through the mesh's own section info, not by index."""
    editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    editor.remove_collisions(mesh)
    body = mesh.get_editor_property('body_setup')
    if kind == 'box':
        # The subsystem's own enum, as physis_aaa_tools uses it. ScriptingCollisionShapeType only reaches it through
        # a deprecated redirect (EditorScriptingUtilities' config), which a later engine may drop.
        editor.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
    if body:
        body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if kind == 'complex'
                                 else unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        body.set_editor_property('double_sided_geometry', kind == 'complex')
    slots = [slot_name(s) for s in mesh.get_editor_property('static_materials')]
    for section in range(mesh.get_num_sections(0)):
        index = editor.get_lod_material_slot(mesh, 0, section)
        slot = slots[index] if 0 <= index < len(slots) else ''
        editor.enable_section_collision(mesh, kind == 'complex' and slot not in PASS_THROUGH, 0, section)


def lods(mesh, chain):
    """LODs of (triangle fraction, screen size). The subsystem's SetLods takes FStaticMeshReductionOptions (5.8's
    StaticMeshEditorSubsystemHelpers.h; EditorScriptingMeshReductionOptions is only a deprecated redirect to it).
    Its automatic screen sizes are on by default and would ignore the chain's, so they are turned off."""
    options = unreal.StaticMeshReductionOptions()
    options.set_editor_property('auto_compute_lod_screen_size', False)
    settings = []
    for fraction, size in chain:
        step = unreal.StaticMeshReductionSettings()
        step.set_editor_property('percent_triangles', float(fraction))
        step.set_editor_property('screen_size', float(size))
        settings.append(step)
    options.set_editor_property('reduction_settings', settings)
    return unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_lods(mesh, options)


def lod_chain(stem):
    """A mesh's LOD chain: () for none (LOD 0 only), None to leave its LODs as they are. NO_LOD is tested first, so no
    later prefix can give a card plant a reduction chain."""
    if stem.startswith(NO_LOD):
        return ()
    if stem.startswith(TREES):
        return TREE_LODS
    if stem.startswith(SMALL_PLANTS):
        return PLANT_LODS
    if stem.startswith(('SM_CV_', 'SM_CE_')):
        return LODS
    if stem.startswith(BUILDINGS):
        return BUILDING_LODS
    if stem.startswith('SM_CD_Terrain'):
        return TERRAIN_LODS
    return None


def apply_lods(mesh, chain):
    """Gives the mesh its lod_chain(); returns why that failed, or None. The subsystem's SetLods returns the LOD count
    (-1 when it refuses) and RemoveLods whether it worked. Complex collision stays LOD 0's whatever the chain."""
    editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    try:
        done = editor.remove_lods(mesh) if chain == () else lods(mesh, chain) >= 0
    except Exception as error:
        return str(error)
    return None if done else 'refused'


def import_options():
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
    data.set_editor_property('build_nanite', False)
    data.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)
    data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    return options


def import_meshes(prefix=''):
    made, unknown, failed, lod_failed = [], {}, [], {}
    for path in sorted(ART.glob(prefix + '*.fbx')):
        stem = path.stem
        game.import_file(str(path), MESHES, import_options())
        mesh = unreal.load_asset(MESHES + '/' + stem)
        if mesh is None:
            failed.append(stem)
            continue
        missing, _ = apply_slots(mesh)
        if missing:
            unknown[stem] = missing
        collision(mesh, collision_kind(stem))
        chain = lod_chain(stem)
        if chain is not None:
            why = apply_lods(mesh, chain)
            if why:
                lod_failed[stem] = why
        game.save(mesh)
        made.append(stem)
    return {'meshes': len(made), 'failed': failed, 'unknown_slots': unknown, 'lod_failed': lod_failed}


def relink():
    """Points every imported Conclave mesh's slots at the current looks (for an import that ran before materials)."""
    count = 0
    for path in library.list_assets(MESHES, False) if library.does_directory_exist(MESHES) else []:
        mesh = unreal.load_asset(path)
        if isinstance(mesh, unreal.StaticMesh):
            _, changed = apply_slots(mesh)
            if changed:
                game.save(mesh)
                count += 1
    return count


# ---------------------------------------------------------------- audio

LOOPING = ('S_Music_', 'S_Amb_')
AMBIENCE = 'S_Amb_'
# Each Conclave sound follows its volume setting exactly once. S_Music_Conclave plays in BP_Physis's MusicComp at
# 0.1 x MusicVol (center_overrides.py PhysisMusicPick) and every voice through PhysisNarrate at VoiceVol / 8, so they
# follow the settings already. The Center's SC_CenterMusic and SC_CenterVoice, which BP_Awakening's SyncMix scales by
# MusicVol / 6 and VoiceVol / 10, are for sounds outside those players (the Center's sound_classes()); on top of them
# they square the setting (Music 3 would play at a quarter of the default instead of half, Music 10 at 2.8 times it).
# The ambience plays from the scenario's AmbientSound actors, which nothing else scales, so it alone takes
# SC_CenterMusic and rides the Music Volume setting. (Tools/conclave/README.md "Audio" said music and voices too.)
MUSIC_CLASS = '/Game/Center/Audio/SC_CenterMusic'
VOICE_CLASS = '/Game/Center/Audio/SC_CenterVoice'


def sound_class_for(path, stem):
    if stem.startswith(AMBIENCE) and '/Voice/' not in path:
        return MUSIC_CLASS
    return None  # music and voices are scaled by their players; effects play at their own volume, as the Center's


def sound_classes():
    classes = {path: unreal.load_asset(path) for path in (MUSIC_CLASS, VOICE_CLASS)}
    if None in classes.values():
        raise RuntimeError('the Center sound classes are missing: run center:sound_classes first')
    assigned, cleared = [], 0
    for path in library.list_assets(AUDIO, True) if library.does_directory_exist(AUDIO) else []:
        wave = unreal.load_asset(path)
        if not isinstance(wave, unreal.SoundWave):
            continue
        want = sound_class_for(path, wave.get_name())
        have = wave.get_editor_property('sound_class_object')
        if want:
            if have != classes[want]:
                wave.set_editor_property('sound_class_object', classes[want])
                game.save(wave)
            assigned.append(wave.get_name())
        elif have in classes.values():
            # Music, voices and effects never take the Center's classes (no class plays in the default one).
            wave.set_editor_property('sound_class_object', None)
            game.save(wave)
            cleared += 1
    return {'SC_CenterMusic': sorted(assigned), 'cleared': cleared}


def import_audio():
    sounds, voices, loops = 0, 0, []
    for path in sorted((ROOT / 'Art/Audio/Conclave').glob('*.wav')):
        game.import_file(str(path), AUDIO)
        wave = unreal.load_asset(AUDIO + '/' + path.stem)
        if wave is None:
            continue
        looping = path.stem.startswith(LOOPING)
        wave.set_editor_property('looping', looping)
        game.save(wave)
        if looping:
            loops.append(path.stem)
        sounds += 1
    for path in sorted((ROOT / 'Art/Audio/Conclave/Voice').glob('*.wav')):
        game.import_file(str(path), AUDIO + '/Voice')
        voices += 1
    report = {'sounds': sounds, 'voices': voices, 'looping': loops}
    report['classes'] = sound_classes()
    return report


# ---------------------------------------------------------------- height grid

class Ground:
    """The terrain height grid from Tools/build_physis_conclave.py: Art/Meshes/Conclave/height.json (half_x, half_y,
    cell, nx, ny, water, regions, paths; metres) and height.bin (float32 metres, index i * ny + j, i along x)."""

    def __init__(self):
        meta = json.loads((ART / 'height.json').read_text())
        self.half_x, self.half_y, self.cell = float(meta['half_x']), float(meta['half_y']), float(meta['cell'])
        self.nx, self.ny = int(meta['nx']), int(meta['ny'])
        self.water = float(meta.get('water', plan.WATER))
        self.regions = meta.get('regions') or dict(plan.REGIONS)
        self.paths = meta.get('paths') or [list(line) for line in plan.PATHS]
        raw = (ART / 'height.bin').read_bytes()
        count = self.nx * self.ny
        if len(raw) < count * 4:
            raise ValueError('height.bin holds %d bytes; %d x %d floats need %d' % (len(raw), self.nx, self.ny, count * 4))
        self.h = struct.unpack('<%df' % count, raw[:count * 4])

    def at(self, x, y):
        """Ground height in cm at Unreal (x, y) in cm; clamped to the grid's edge outside it."""
        fx = (x / CM + self.half_x) / self.cell
        fy = (y / CM + self.half_y) / self.cell
        i = max(0, min(int(math.floor(fx)), self.nx - 2))
        j = max(0, min(int(math.floor(fy)), self.ny - 2))
        u = min(max(fx - i, 0.0), 1.0)
        v = min(max(fy - j, 0.0), 1.0)
        h, n = self.h, self.ny
        value = (h[i * n + j] * (1 - u) * (1 - v) + h[(i + 1) * n + j] * u * (1 - v) +
                 h[i * n + j + 1] * (1 - u) * v + h[(i + 1) * n + j + 1] * u * v)
        return value * CM

    def ground(self, x, y, lift=0):
        """(x, y, z): the ground, or the water surface over the lake, plus lift (a negative lift may go under water)."""
        return (x, y, max(self.at(x, y), self.water * CM if lift >= 0 else -1e9) + lift)


# ---------------------------------------------------------------- level look

# The Spine's sun. It is placed dim, as play starts (the swarm has drunk the pylons; the level holds the SpineDim
# thirds), so a load shows no bright first frames before the director's first tick. BP_ConclaveDirector sets every
# SpineSun light to SunBase + SunStep per relit pylon, which tune_director() writes on the placed director. Without
# them it falls back to a quarter of the placed intensity plus a quarter per pylon (conclave_logic.py director()),
# which assumes a light placed at full and would leave this one at a quarter of its light; conclave:level runs before
# conclave_logic.py adds the variables, so tune_director() runs again after conclave:scenario. Pitched -58 so shadows
# read (0.62 of a thing's height, against 0.40 at -68) and walls along the north-south streets take side light; the yaw
# brings it from the south-east, from behind Physis's right shoulder as she walks north (the end caps take the Spine's
# light from FILLS instead). The first editor shots at 2.25 lux rendered the lit lawn sRGB (71, 60, 37) and the
# lake (78, 96, 107): brown and navy by palette.py, because the exposure floor held the frame about 2 stops dark. The
# Spine now gives 7.2 lux dark and 18 lit (glows, rays and lamps keep their values: they are set for EV100 about 2.5).
SUN_PITCH, SUN_YAW = -58.0, -60.0
SUN_FULL = 18.0               # lux, all three pylons lit
SUN_BASE = SUN_FULL * .4      # three dark pylons: dim, not night (the lawn must render gold: sRGB value 0.5 and over)
SUN_STEP = (SUN_FULL - SUN_BASE) / 3
DIRECTOR_SUN = (('SunBase', SUN_BASE), ('SunStep', SUN_STEP))
SUN_COLOUR = (1.0, .97, .92)  # the warmest white under which every palette albedo keeps its family (LIGHT_WARM turns WHITE and IVORY cream)
# The Spine lights the far side as a line light would (2026-11-07 review): one fill for each land strip overhead, a
# directional light on lighting channel 1 only, which only the upper lands and the end caps take (DRUM; Lumen's surface
# cache honours lighting channels, so neither adds light or bounce on the floor), tagged SpineSun so the director
# brightens it with the sun. Each travels from the axis toward its strip's centre, at LAND_PERIOD and twice it round the
# drum from the floor's bottom line (the floor strip, a window, a land strip; drum.py UPPER_LANDS), raked FILL_RAKE
# degrees along x so the far side's relief and houses shade: a strip takes 0.81-0.94 of the light across its width (the
# one upward fill fell from 0.87 to 0), the east fill lights the north cap and the west fill the south cap at 0.34, and
# neither reaches the other strip, which faces away from it.
LAND_PERIOD = math.degrees(2 * plan.STRIP + plan.WINDOW)   # 120
FILL_RAKE = 20.0
FILLS = (('Spine Fill E', LAND_PERIOD, FILL_RAKE), ('Spine Fill W', 2 * LAND_PERIOD, -FILL_RAKE))  # label, theta, rake (deg)
SKY_TINT = (.72, .84, 1.0)    # light-blue white
SKY_INTENSITY = .7            # the capture sees the denser haze below; this aims at a sun about 4 to 5 times the fill
FOG_TINT = (.82, .90, 1.0)    # white-blue haze: a bluer one turns black stone navy where it blends into the haze
FOG_BRIGHT = .9               # cd/m2 (luminance 0.8): 0.11 per lux of the dark Spine, 0.045 lit (1.2 until the 2026-11-07 review)
# M_CNSky's share of the fog in front of the windows (SKY): the drum's air scatters forward, toward the Spine, and the
# windows are mostly seen looking away from it.
SKY_HAZE = .6
SKY_RADIUS = 2500000.0        # cm: 25 km, far outside the drum, so the fog cut-off below skips it (M_CNSky hazes it)
# The drum's air does not thin with world z (spin gravity: the pressure at the axis is 96 % of the floor's), so the haze
# is nearly uniform: the far cap (1.5 km) and the land overhead (1.4 km) take about 65 %, the Commons from the
# Wellspring (300 m) about 20 %. The old falloff (0.05, halving every 200 m) left everything above 200 m almost clear.
# Thinner since Lumen (2026-11-07): at .010 the haze greyed the windows' black space and flattened every view. No
# directional inscattering (lighting() sets its luminance to 0): its lobe sat on the sun light's fixed direction, a glow
# in the south-east sky unrelated to the Spine, whose glow is now its halo (HALO).
FOG = {'fog_density': .0055, 'fog_height_falloff': .002, 'start_distance': 3000.0, 'fog_max_opacity': .85,
       # Beyond the drum's longest view (about 2.2 km), so only the sky sphere goes unfogged.
       'fog_cutoff_distance': 300000.0}
FOG_FLOOR = {'fog_density': .004, 'fog_height_falloff': .5, 'fog_height_offset': 0.0}   # second layer: mist in the low ground
FOG_BASE = plan.WATER * CM    # cm: the fog actor stands at the waterline; its layers' heights are measured from it
LAMP = (PAL.LIGHT_GOLD, 60.0, 1500.0)       # colour, candelas, attenuation radius (cm)
NEST = (PAL.LIGHT_RED, 90.0, 2600.0)
LIGHTFORM = (PAL.LIGHT_BLUE, 90.0, 2400.0)
# Exposure in EV100 (r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange is on). The floor clamps how far
# it brightens a dim Conclave, so the dark Spine reads as dimmer and relighting it reads as day returning; the bias is
# applied after the clamp (+0.3: the histogram meters a gold-and-white floor a little dark).
EXPOSURE = (1.8, 8.0)
POST = (('override_auto_exposure_method', True), ('auto_exposure_method', unreal.AutoExposureMethod.AEM_HISTOGRAM),
        ('override_auto_exposure_bias', True), ('auto_exposure_bias', 0.3),
        ('override_auto_exposure_min_brightness', True), ('auto_exposure_min_brightness', EXPOSURE[0]),
        ('override_auto_exposure_max_brightness', True), ('auto_exposure_max_brightness', EXPOSURE[1]),
        ('override_auto_exposure_speed_up', True), ('auto_exposure_speed_up', 2.0),
        ('override_auto_exposure_speed_down', True), ('auto_exposure_speed_down', 1.0),
        ('override_auto_exposure_apply_physical_camera_exposure', True), ('auto_exposure_apply_physical_camera_exposure', False),
        ('override_bloom_intensity', True), ('bloom_intensity', .6),
        ('override_ambient_occlusion_intensity', True), ('ambient_occlusion_intensity', .65),
        ('override_ambient_occlusion_radius', True), ('ambient_occlusion_radius', 150.0),
        ('override_ambient_occlusion_quality', True), ('ambient_occlusion_quality', 70.0),
        # Lumen GI and reflections (author, 2026-11-07: AAA look, retry Lumen). Hardware ray traced: the project has
        # r.Lumen.HardwareRayTracing on and mesh distance fields off, so a run with -noraytracing falls back to no GI
        # here. Trace and view distances cover the drum (1.4 km across, 1.6 km long); hit lighting for reflections
        # makes gold and water reflect lit surfaces rather than the surface cache.
        ('override_reflection_method', True), ('reflection_method', unreal.ReflectionMethod.LUMEN),
        ('override_dynamic_global_illumination_method', True),
        ('dynamic_global_illumination_method', unreal.DynamicGlobalIlluminationMethod.LUMEN),
        ('override_lumen_scene_lighting_quality', True), ('lumen_scene_lighting_quality', 2.0),
        ('override_lumen_scene_detail', True), ('lumen_scene_detail', 2.0),
        ('override_lumen_scene_view_distance', True), ('lumen_scene_view_distance', 200000.0),
        ('override_lumen_final_gather_quality', True), ('lumen_final_gather_quality', 2.0),
        ('override_lumen_max_trace_distance', True), ('lumen_max_trace_distance', 200000.0),
        ('override_lumen_reflection_quality', True), ('lumen_reflection_quality', 2.0),
        ('override_lumen_ray_lighting_mode', True), ('lumen_ray_lighting_mode', unreal.LumenRayLightingModeOverride.HIT_LIGHTING_FOR_REFLECTIONS),
        ('override_lumen_front_layer_translucency_reflections', True), ('lumen_front_layer_translucency_reflections', True),
        # A light-blue-white floor under every shadow (review 2026-11-07: shade crushed to black and brown at 0).
        ('override_lumen_skylight_leaking', True), ('lumen_skylight_leaking', .15),
        ('override_lumen_skylight_leaking_tint', True), ('lumen_skylight_leaking_tint', linear((.9, .95, 1.0))),
        ('override_local_exposure_shadow_contrast_scale', True), ('local_exposure_shadow_contrast_scale', .65),
        ('override_local_exposure_detail_strength', True), ('local_exposure_detail_strength', 1.1),
        ('override_vignette_intensity', True), ('vignette_intensity', .25),
        # Deep shadow toward grey: shaded gold would read brown, shaded red maroon, shaded light blue navy. It only
        # moves colours toward the palette's greys. Up to 0.08 after exposure (UE's default 0.09): at 0.15 it also took
        # 13 % of the saturation from sunlit lawn at 0.1, and at the old exposure 40 % from all of it.
        ('override_color_saturation_shadows', True), ('color_saturation_shadows', unreal.Vector4(.4, .4, .4, 1.0)),
        ('override_color_correction_shadows_max', True), ('color_correction_shadows_max', .08))
# Sphere reflection captures: (name, plan place, influence radius m).
CAPTURES = (('Commons', plan.COMMONS_PLAZA, 120.0), ('Reservoir', plan.RESERVOIR_ISLAND, 110.0), ('Foundry', plan.FOUNDRY_PYLON, 90.0),
            ('Spire', plan.SPIRE, 80.0), ('Docks', plan.DOCKS_ARENA, 80.0))
# Red AL light where the swarm nests, light blue where Lightforms are: (name, plan place, ring radius m, lights).
AL_NESTS = (('Docks', plan.DOCKS_ARENA, 30.0, 6), ('Old Quarter', tuple(plan.REGIONS['Old Quarter'][:2]), 24.0, 3))
LIGHTFORM_RINGS = (('Spire', plan.SPIRE, 26.0, 4),)
LIGHTFORM_PEOPLE = ('Iriel', 'Wisp')
START_NORTH = 6.5  # m north of the Wellspring pool: in its garden, well clear of the current's 1.8 m radius

# The drum shell: (mesh, collides, casts shadow, lit only by the fills on channel 1). Nothing of the shell casts
# shadows: with the sun 22 degrees off vertical, a 1.4 km end cap would shade a third of the floor. The upper lands face
# down toward the axis, away from the sun, and the end caps took it at a grazing 0.27 (the south one none): both take
# FILLS instead.
DRUM = (('SM_CD_Water', False, False, False), ('SM_CD_Windows', True, False, False), ('SM_CD_UpperLandE', False, False, True),
        ('SM_CD_UpperLandW', False, False, True), ('SM_CD_CapSouth', True, False, True), ('SM_CD_CapNorth', True, False, True),
        ('SM_CD_ParapetW', True, True, False), ('SM_CD_ParapetE', True, True, False))
SCATTER_RULES = {
    # mesh: (collide, cull distance cm (0 never), cast shadow)
    'SM_CV_GrassGold': (False, 8000, False), 'SM_CV_Wheat': (False, 12000, False), 'SM_CV_FlowersWhite': (False, 10000, False),
    'SM_CV_FlowersRed': (False, 10000, False), 'SM_CV_FlowersBlue': (False, 10000, False), 'SM_CV_Reeds': (False, 14000, False),
    'SM_CV_Lily': (False, 12000, False), 'SM_CV_Vines': (False, 20000, False), 'SM_CV_Shrub': (True, 30000, True),
    'SM_CV_Hedge': (True, 40000, True), 'SM_CV_RockWhite': (True, 60000, True), 'SM_CV_RockBlack': (True, 60000, True),
    'SM_CV_TreeWhite': (True, 0, True), 'SM_CV_TreeRed': (True, 0, True), 'SM_CV_TreeBlack': (True, 0, True),
    'SM_CV_FruitTree': (True, 0, True),
    # Leaf litter under the trees lies flat on the ground: nothing to walk into and no shadow to cast.
    'SM_CV_LitterWhite': (False, 6000, False), 'SM_CV_LitterRed': (False, 6000, False), 'SM_CV_LitterBlack': (False, 6000, False),
}
SCATTER_DEFAULT = (True, 90000, True)
WELL_GLOW = (PAL.LIGHT_BLUE, 60.0, 1600.0)  # the spring of Divinity glows light blue in its pool


def check_palette():
    """Runs every colour table of this module through palette.allowed() when the module loads, so a refused colour
    stops an operation before it builds anything rather than halfway through a level. (Each material's own
    defaults are checked by colour() as the material is built.)"""
    for rgb in ([WHITE1, SKY_TINT, SUN_COLOUR, FOG_TINT] + [rgb for _, vectors in SURFACES.values() for rgb in vectors.values()] +
                [rgb for _, _, vectors in SLOT_MASTERS.values() for rgb in vectors.values()] + list(SKY_COLOURS.values()) +
                [rgb for rgb, _ in RAY_LOOKS.values()] + [rgb for rgb, _ in SKINS.values()] +
                [look[0] for look in (LAMP, NEST, LIGHTFORM, WELL_GLOW)] + [PAL.LIGHT_WHITE, PAL.GOLD, GLOW_RED]):
        colour(rgb)
    for rgb in (FOG_TINT, SUN_COLOUR):
        tone(rgb, 1.0)


check_palette()


# ---------------------------------------------------------------- level

def actors():
    return center.actors()


def mesh_actor(label, mesh, place, rot=(0, 0, 0), scale=1.0, folder=FOLDER, collide=True, shadow=True):
    """A StaticMeshActor of MESHES/mesh, or None when the mesh was never imported."""
    asset = unreal.load_asset(MESHES + '/' + mesh)
    if asset is None:
        return None
    actor = actors().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place), unreal.Rotator(*rot))
    actor.set_actor_label(label)
    part = actor.static_mesh_component
    part.set_static_mesh(asset)
    part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
    part.set_editor_property('cast_shadow', shadow)
    part.set_default_custom_primitive_data_float(SEED_DATA, seed_of(label))  # its own surface pattern (object_random)
    size = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    actor.set_actor_scale3d(unreal.Vector(*size))
    actor.set_folder_path(folder)
    return actor


# Ground cover out of the ray-tracing scene (2026-11-07 review): Lumen's surface-cache traces treat every hit as opaque,
# so millions of grass and flower card quads roofed the ground's bounce light; dropping some 210k TLAS instances also
# saves VRAM and build time. Trees, shrubs, hedges and reeds stay in, for the lake's reflections. VSM still shadows all.
RT_SKIP = ('SM_CV_GrassGold', 'SM_CV_Wheat', 'SM_CV_Flowers', 'SM_CV_Lily', 'SM_CV_Litter')


def rt_skip(part, failed):
    try_set(part, 'visible_in_ray_tracing', False, failed)
    try_set(part, 'affect_distance_field_lighting', False, failed)


def scatter_actor(label, mesh, rows, collide, cull, shadow, folder=FOLDER + '/Scatter', failed=None):
    """One actor per mesh holding every instance in a native (non-Blueprint) instanced component, so the
    per-instance data is saved with the level and never reset by a construction script (as the Center's). Settings
    this engine refuses go to `failed`."""
    failed = [] if failed is None else failed
    actor = actors().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.static_mesh_component.set_collision_profile_name('NoCollision')
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root = subobjects.k2_gather_subobject_data_for_instance(actor)[0]
    handle, _ = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root, new_class=unreal.HierarchicalInstancedStaticMeshComponent,
                                                                          blueprint_context=None))
    part = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
    part.set_static_mesh(unreal.load_asset(MESHES + '/' + mesh))
    part.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
    part.set_editor_property('cast_shadow', shadow)
    part.set_editor_property('instance_end_cull_distance', int(cull))
    part.set_editor_property('instance_start_cull_distance', int(cull * .8))
    if shadow:
        # Wind moves leaves a few centimetres (M_CNFoliage): their shadows need not follow, so the sway does not
        # invalidate the virtual shadow map's cached pages every frame (VSM is on and nothing here is Nanite).
        try_set(part, 'shadow_cache_invalidation_behavior', unreal.ShadowCacheInvalidationBehavior.RIGID, failed)
    # Beyond 60 m the sway is under a pixel: no world position offset there (vertex work and shadow invalidation saved).
    try_set(part, 'world_position_offset_disable_distance', 6000, failed)
    if mesh.startswith(RT_SKIP):
        rt_skip(part, failed)
    transforms = [unreal.Transform(unreal.Vector(x, y, z), unreal.Rotator(roll, pitch, yaw), unreal.Vector(s, s, s))
                  for x, y, z, pitch, yaw, roll, s in (row[:7] for row in rows)]
    part.add_instances(transforms, False, True)
    return actor


def channels(*on):
    """FLightingChannels with exactly these channels on (channel 0 is on by default, so all three are given)."""
    return unreal.LightingChannels(channel0=0 in on, channel1=1 in on, channel2=2 in on)


def light(cls, label, place, rot=(0, 0, 0), folder=FOLDER + '/Light', tags=()):
    actor = actors().spawn_actor_from_class(cls, unreal.Vector(*place), unreal.Rotator(*rot))
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    if tags:
        actor.set_editor_property('tags', list(tags))
    return actor


def point(label, place, look, folder=FOLDER + '/Light', tags=()):
    rgb, candelas, radius = look
    actor = light(unreal.PointLight, label, place, folder=folder, tags=tags)
    comp = actor.get_component_by_class(unreal.PointLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)  # before the value: units do not convert it
    comp.set_editor_property('intensity', float(candelas))
    comp.set_light_color(linear(rgb))
    comp.set_editor_property('attenuation_radius', float(radius))
    comp.set_editor_property('source_radius', 10.0)
    comp.set_editor_property('max_draw_distance', 12000.0)
    comp.set_editor_property('max_distance_fade_range', 3000.0)
    comp.set_cast_shadows(False)
    return actor


def open_level():
    """Opens L_Conclave (made if missing) and removes what an earlier build placed (every actor in a Conclave
    folder, the scenario's too, as the Center's build does). Refuses while Play runs or another map has unsaved
    changes, since switching maps would then stop on a modal dialog."""
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    playing = getattr(les, 'is_in_play_in_editor', None)
    if playing and playing():
        raise RuntimeError('stop Play before building the Conclave')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None or world.get_path_name().split('.')[0] != LEVEL:
        listing = getattr(unreal.EditorLoadingAndSavingUtils, 'get_dirty_map_packages', None)
        dirty = [p.get_name() for p in listing()] if listing else []
        if dirty:
            raise RuntimeError('unsaved changes in %s: save or discard them before conclave:level' % ', '.join(dirty))
        if library.does_asset_exist(LEVEL):
            les.load_level(LEVEL)
        elif not les.new_level(LEVEL):
            raise RuntimeError('could not create ' + LEVEL)
    sub = actors()
    removed = 0
    for actor in sub.get_all_level_actors():
        if not isinstance(actor, unreal.WorldSettings) and str(actor.get_folder_path()).startswith(FOLDER):
            sub.destroy_actor(actor)
            removed += 1
    return removed


def save_level():
    """Saves L_Conclave in place. A Save As over the open map (the Center's fallback) would write whatever level is
    open into L_Conclave, so only a new, never-saved level (a /Temp path) is saved under the name."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    path = world.get_path_name().split('.')[0]
    if path == LEVEL:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    elif path.startswith('/Temp/'):
        unreal.EditorLoadingAndSavingUtils.save_map(world, LEVEL)
    else:
        raise RuntimeError('%s is open, not %s: nothing saved' % (path, LEVEL))


def terrain(g):
    missing, shifted = [], []
    size_x, size_y = 2 * g.half_x / plan.TILES_X, 2 * g.half_y / plan.TILES_Y
    for i in range(plan.TILES_X):
        for j in range(plan.TILES_Y):
            name = 'SM_CD_Terrain_%d_%d' % (i, j)
            if mesh_actor('Terrain %d %d' % (i, j), name, (0, 0, 0), folder=FOLDER + '/Terrain') is None:
                missing.append(name)
                continue
            # Tiles are modelled in world space, like the Center's: placed at the origin, a tile's bounds sit on its
            # cell of the grid. Report any that do not, rather than guess at another convention.
            box = unreal.load_asset(MESHES + '/' + name).get_bounding_box()
            want = ((-g.half_x + (i + .5) * size_x) * CM, (-g.half_y + (j + .5) * size_y) * CM)
            got = ((box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2)
            if abs(got[0] - want[0]) > size_x * CM / 4 or abs(got[1] - want[1]) > size_y * CM / 4:
                shifted.append(name)
    return {'tiles': plan.TILES_X * plan.TILES_Y - len(missing), 'missing': missing, 'not_at_their_cell': shifted}


def drum():
    placed, missing = [], []
    fill_only = channels(1)
    cap_glow = unreal.load_asset(MATS + '/MI_CN_CapGlow')
    for mesh, collide, shadow, upper in DRUM:
        actor = mesh_actor(mesh[6:], mesh, (0, 0, 0), folder=FOLDER + '/Drum', collide=collide, shadow=shadow)
        if actor is None:
            missing.append(mesh)
            continue
        if upper:
            # The upper lands and the end caps take the Spine's light from the fills alone (channel 1, FILLS).
            actor.static_mesh_component.set_editor_property('lighting_channels', fill_only)
        if mesh.startswith('SM_CD_Cap') and cap_glow:
            for index, slot in enumerate(unreal.load_asset(MESHES + '/' + mesh).get_editor_property('static_materials')):
                if slot_name(slot) == 'CN_Glow':
                    actor.static_mesh_component.set_material(index, cap_glow)
        placed.append(mesh)
    return {'placed': placed, 'missing': missing}


def spine():
    glow = unreal.load_asset(MATS + '/MI_CN_SpineGlow')
    lit_mesh = unreal.load_asset(MESHES + '/SM_CD_SpineLit')
    glow_slots = [index for index, slot in enumerate(lit_mesh.get_editor_property('static_materials'))
                  if slot_name(slot) == 'CN_Glow'] if lit_mesh and glow else []
    placed = []
    for k in range(3):  # south, middle, north
        place = ((k - 1) * SPINE_THIRD * CM, 0.0, plan.AXIS_Z * CM)
        dim = mesh_actor('Spine Dim %d' % (k + 1), 'SM_CD_SpineDim', place, folder=FOLDER + '/Spine', collide=False, shadow=False)
        lit = mesh_actor('Spine Lit %d' % (k + 1), 'SM_CD_SpineLit', place, folder=FOLDER + '/Spine', collide=False, shadow=False)
        if dim:
            dim.set_editor_property('tags', ['SpineDim%d' % (k + 1)])
            placed.append('SpineDim%d' % (k + 1))
        if lit:
            lit.set_editor_property('tags', ['SpineLit%d' % (k + 1)])
            lit.set_actor_hidden_in_game(True)  # BP_ConclaveDirector shows it when its pylon wakes
            for index in glow_slots:
                lit.static_mesh_component.set_material(index, glow)
            placed.append('SpineLit%d' % (k + 1))
    return {'placed': placed, 'halos': spine_halos()}


# The halo's cylinder: the engine's (100 cm across, local z -50..50), turned by pitch 90 so its axis lies along x and
# scaled to a radius of 90 m (3.6 Sigma, where the glow is gone) and one third of the Spine long.
HALO_MESH = '/Engine/BasicShapes/Cylinder'
HALO_SCALE = (180.0, 180.0, SPINE_THIRD * CM / 100.0)


def spine_halos():
    """'Spine Halo 1..3' (M_CNSpineHalo) around the three thirds, tagged SpineLitN and hidden in game like the lit
    thirds, so BP_ConclaveDirector's SpineThirds shows each halo with its own third (a dark third has none). They are
    light only: no collision, no shadow, nothing in ray tracing, reflection captures or distance-field lighting."""
    halo = unreal.load_asset(MATS + '/M_CNSpineHalo')
    cylinder = unreal.load_asset(HALO_MESH)
    placed, failed = [], []
    for k in range(3):  # south, middle, north, as spine()
        actor = actors().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector((k - 1) * SPINE_THIRD * CM, 0.0, plan.AXIS_Z * CM),
                                                unreal.Rotator(0.0, 90.0, 0.0))
        actor.set_actor_label('Spine Halo %d' % (k + 1))
        actor.set_folder_path(FOLDER + '/Spine')
        part = actor.static_mesh_component
        part.set_static_mesh(cylinder)
        part.set_material(0, halo)
        part.set_collision_profile_name('NoCollision')
        part.set_editor_property('cast_shadow', False)
        for key in ('visible_in_ray_tracing', 'visible_in_reflection_captures', 'affect_distance_field_lighting'):
            try_set(part, key, False, failed)
        actor.set_actor_scale3d(unreal.Vector(*HALO_SCALE))
        actor.set_editor_property('tags', ['SpineLit%d' % (k + 1)])
        actor.set_actor_hidden_in_game(True)
        placed.append(actor.get_actor_label())
    return {'placed': placed, 'failed': sorted(set(failed))}


def sky():
    sphere = unreal.load_asset('/Engine/EngineSky/SM_SkySphere')
    actor = actors().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, plan.AXIS_Z * CM))
    actor.set_actor_label('Sky')
    actor.set_folder_path(FOLDER + '/Light')
    part = actor.static_mesh_component
    part.set_static_mesh(sphere)
    part.set_material(0, unreal.load_asset(MATS + '/MI_CNSky'))
    part.set_collision_profile_name('NoCollision')
    part.set_editor_property('cast_shadow', False)
    scale = SKY_RADIUS / sphere.get_bounding_box().max.x
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    return {'radius_km': SKY_RADIUS / 100000.0}


def try_set(target, key, value, failed):
    """set_editor_property, with a refusal reported rather than raised (a property this engine version lacks)."""
    try:
        target.set_editor_property(key, value)
    except Exception as error:
        failed.append('%s: %s' % (key, error))


def fill_rotation(theta, rake):
    """(roll, pitch, yaw) of a directional light travelling from the axis toward the drum's surface at theta degrees
    round from the floor's bottom line (toward +y first), tilted rake degrees toward +x (negative: toward -x). A light's
    forward axis is its travel direction: (cos pitch cos yaw, cos pitch sin yaw, sin pitch)."""
    t, r = math.radians(theta), math.radians(rake)
    d = (math.sin(r), math.cos(r) * math.sin(t), -math.cos(r) * math.cos(t))
    return (0.0, math.degrees(math.asin(d[2])), math.degrees(math.atan2(d[1], d[0])))


def lighting():
    failed = []
    sun = light(unreal.DirectionalLight, 'Spine Sun', (0, 0, plan.AXIS_Z * CM), (0, SUN_PITCH, SUN_YAW), tags=('SpineSun',))
    comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property('intensity', SUN_BASE)
    comp.set_light_color(linear(SUN_COLOUR))
    comp.set_editor_property('light_source_angle', 1.2)  # the Spine is a 14 m wide line, not a point: softer shadows
    comp.set_editor_property('atmosphere_sun_light', False)
    comp.set_editor_property('forward_shading_priority', 1)  # translucent glass and water take their light from it
    comp.set_editor_property('dynamic_shadow_distance_movable_light', 20000.0)
    comp.set_editor_property('dynamic_shadow_cascades', 3)
    # Screen-space contact shadows seat what casts no shadow map (grass, flowers, reeds) and small props on the ground.
    try_set(comp, 'contact_shadow_length', .03, failed)
    try_set(comp, 'contact_shadow_non_casting_intensity', .5, failed)
    # More bounce from sunlit lawn and walls into the shade (Lumen honours a light's indirect intensity).
    try_set(comp, 'indirect_lighting_intensity', 1.4, failed)
    # The same Spine lights the far side: FILLS, on lighting channel 1 only, so they never light the floor.
    fills = {}
    for label, theta, rake in FILLS:
        rot = fill_rotation(theta, rake)
        fill = light(unreal.DirectionalLight, label, (0, 0, plan.AXIS_Z * CM), rot, tags=('SpineSun',))
        fc = fill.get_component_by_class(unreal.DirectionalLightComponent)
        fc.set_mobility(unreal.ComponentMobility.MOVABLE)
        fc.set_editor_property('intensity', SUN_BASE)
        fc.set_light_color(linear(SUN_COLOUR))
        fc.set_cast_shadows(False)
        fc.set_editor_property('atmosphere_sun_light', False)
        fc.set_editor_property('lighting_channels', channels(1))
        fills[label] = [round(rot[1], 1), round(rot[2], 1)]   # pitch, yaw
    # The sky light captures the drum itself from its middle: inside a habitat the fill comes from the lit land all
    # around (the floor below, the lands overhead), not from a sky.
    skylight = light(unreal.SkyLight, 'Drum Light', (0, 0, 35000))
    sc = skylight.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    sc.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    sc.set_editor_property('real_time_capture', False)
    sc.set_editor_property('sky_distance_threshold', 5000.0)
    sc.set_editor_property('lower_hemisphere_is_black', False)
    sc.set_editor_property('intensity', SKY_INTENSITY)
    sc.set_light_color(linear(SKY_TINT))
    fog = light(unreal.ExponentialHeightFog, 'Drum Haze', (0, 0, FOG_BASE))
    haze = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    for key, value in FOG.items():
        haze.set_editor_property(key, value)
    haze.set_editor_property('fog_inscattering_luminance', unreal.LinearColor(*tone(FOG_TINT, FOG_BRIGHT), 1))
    # Off (black; the engine's default is not): see FOG.
    haze.set_editor_property('directional_inscattering_luminance', linear((0.0, 0.0, 0.0)))
    haze.set_editor_property('enable_volumetric_fog', False)
    try:
        layer = unreal.ExponentialHeightFogData()
        for key, value in FOG_FLOOR.items():
            layer.set_editor_property(key, value)
        haze.set_editor_property('second_fog_data', layer)
    except Exception as error:
        failed.append('second_fog_data: %s' % error)
    return {'sun_lux': [SUN_BASE, SUN_FULL], 'sun_step': SUN_STEP, 'fills': fills, 'failed': failed}


def post():
    volume = light(unreal.PostProcessVolume, 'Conclave Look', (0, 0, 0))
    volume.set_editor_property('unbound', True)
    settings = volume.settings
    failed = []
    for key, value in POST:
        try:
            settings.set_editor_property(key, value)
        except Exception as error:
            failed.append('%s: %s' % (key, error))
    # No blendables at all: the Conclave has no post-process material (no PP_CenterCel).
    blendables = unreal.WeightedBlendables()
    blendables.set_editor_property('array', [])
    settings.set_editor_property('weighted_blendables', blendables)
    volume.set_editor_property('settings', settings)
    return {'failed': failed}


def reflections(g):
    made = []
    for name, (x, y), radius in CAPTURES:
        place = g.ground(x * CM, y * CM, 800)
        actor = light(unreal.SphereReflectionCapture, 'Reflection ' + name, place, folder=FOLDER + '/Light/Reflections')
        actor.get_component_by_class(unreal.SphereReflectionCaptureComponent).set_editor_property('influence_radius', radius * CM)
        made.append(name)
    return made


def frange(lo, hi, step):
    v = lo
    while v <= hi:
        yield v
        v += step


def water(g):
    """Swimming water only under the lake: a water PhysicsVolume over the water mesh's footprint, from the
    waterline down past the deepest bed. Ground above the waterline is outside it, so the shore stays dry."""
    mesh = unreal.load_asset(MESHES + '/SM_CD_Water')
    if mesh:
        box = mesh.get_bounding_box()
        x0, x1, y0, y1 = box.min.x, box.max.x, box.min.y, box.max.y
    else:
        cx, cy, ax, ay = plan.LAKE
        x0, x1, y0, y1 = (cx - ax - 15) * CM, (cx + ax + 15) * CM, (cy - ay - 15) * CM, (cy + ay + 15) * CM
    top = g.water * CM
    bed = min(g.at(x, y) for x in frange(x0, x1, 400.0) for y in frange(y0, y1, 400.0))
    bottom = min(bed, top - 200.0) - 300.0
    sub = actors()
    volume = sub.spawn_actor_from_class(unreal.PhysicsVolume, unreal.Vector((x0 + x1) / 2, (y0 + y1) / 2, (top + bottom) / 2))
    volume.set_actor_label('Water Volume')
    volume.set_folder_path(FOLDER + '/Terrain')
    volume.set_actor_scale3d(unreal.Vector((x1 - x0) / 200.0, (y1 - y0) / 200.0, (top - bottom) / 200.0))  # the brush is 200 cm
    volume.set_editor_property('water_volume', True)
    volume.set_editor_property('fluid_friction', .35)
    volume.set_editor_property('terminal_velocity', 600.0)
    director = sub.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/BP_SwimDirector').generated_class(), unreal.Vector(0, 0, 0))
    director.set_actor_label('Swim Director')
    director.set_folder_path(FOLDER + '/Terrain')
    return {'volume_cm': [x0, x1, y0, y1, bottom, top]}


def lamp_lights(rows):
    """A gold light at every second lamp, at the top of the lamp mesh's bounds (its lantern), turned with the lamp."""
    lamp = unreal.load_asset(MESHES + '/SM_CN_Lamp')
    if lamp is None or not rows:
        return 0
    box = lamp.get_bounding_box()
    cx, cy, top = (box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2, box.max.z - 35.0
    made = 0
    for index, row in enumerate(rows):
        if index % 2:
            continue
        x, y, z, pitch, yaw, roll, s = row[:7]
        a = math.radians(yaw)
        place = (x + s * (cx * math.cos(a) - cy * math.sin(a)), y + s * (cx * math.sin(a) + cy * math.cos(a)), z + s * top)
        point('Lamp Light %d' % index, place, LAMP, folder=FOLDER + '/Light/Lamps')
        made += 1
    return made


def scatter():
    """scatter.json from the generator: SM_CV_ rows become one instanced actor per mesh, the rest single actors."""
    path = ART / 'scatter.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    counts, missing, failed = {}, [], []
    for mesh, rows in sorted(data.items()):
        if not rows:
            continue
        if unreal.load_asset(MESHES + '/' + mesh) is None:
            missing.append(mesh)
            continue
        if mesh.startswith('SM_CV_'):
            collide, cull, shadow = SCATTER_RULES.get(mesh, SCATTER_DEFAULT)
            scatter_actor('Scatter ' + mesh[6:], mesh, rows, collide, cull, shadow, failed=failed)
        else:
            for index, row in enumerate(rows):
                x, y, z, pitch, yaw, roll, s = row[:7]
                mesh_actor('%s %d' % (mesh[6:], index), mesh, (x, y, z), (roll, pitch, yaw), s, folder=FOLDER + '/Town/' + mesh[6:])
        counts[mesh] = len(rows)
    return {'meshes': counts, 'missing': missing, 'lamp_lights': lamp_lights(data.get('SM_CN_Lamp', [])), 'failed': sorted(set(failed))}


def person_place(key):
    for row in lore.PEOPLE:
        if row[0] == key:
            return row[5]
    return None


def place_lights(g):
    made = {'nests': 0, 'lightforms': 0}

    def ring(kind, name, centre, radius, count, look, tags):
        for k in range(count):
            a = 2 * math.pi * k / count + .4
            x, y = (centre[0] + math.cos(a) * radius) * CM, (centre[1] + math.sin(a) * radius) * CM
            point('%s Light %s %d' % (kind, name, k), g.ground(x, y, 400), look, folder=FOLDER + '/Light/' + kind, tags=tags)
            made['nests' if kind == 'Nest' else 'lightforms'] += 1
    for name, centre, radius, count in AL_NESTS:
        ring('Nest', name, centre, radius, count, NEST, ('ALLight',))
    for name, centre, radius, count in LIGHTFORM_RINGS:
        ring('Lightform', name, centre, radius, count, LIGHTFORM, ('LightformLight',))
    for key in LIGHTFORM_PEOPLE:
        place = person_place(key)
        if place:
            point('Lightform Light ' + key, g.ground(place[0] * CM, place[1] * CM, 300), LIGHTFORM, folder=FOLDER + '/Light/Lightform',
                  tags=('LightformLight',))
            made['lightforms'] += 1
    point('Wellspring Glow', g.ground(plan.WELL[0] * CM, plan.WELL[1] * CM, 250), WELL_GLOW, folder=FOLDER + '/Light')
    return made


def start(g):
    x, y = (plan.WELL[0] + START_NORTH) * CM, plan.WELL[1] * CM
    sub = actors()
    player = sub.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(*g.ground(x, y, 120)), unreal.Rotator(0, 0, 0))
    player.set_actor_label('Physis Arrives')
    player.set_folder_path(FOLDER)
    # BP_Awakening marks an open-world level for the shared graphs (Still Points, drops, hover, restore); its
    # TestArrival must stay off here, or editor play would run the Center's awakening.
    awakening = sub.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/BP_Awakening').generated_class(), unreal.Vector(*g.ground(x, y)))
    awakening.set_actor_label('Awakening Director')
    awakening.set_folder_path(FOLDER + '/Director')
    awakening.set_editor_property('TestArrival', False)
    director = sub.spawn_actor_from_class(unreal.load_asset(game.BLUEPRINTS + '/BP_ConclaveDirector').generated_class(), unreal.Vector(*g.ground(x, y)))
    director.set_actor_label('Conclave Director')
    director.set_folder_path(FOLDER + '/Director')
    return {'start': [x, y], 'director_tuned': director_sun(director)[0]}


def director_sun(director):
    """Writes SunBase and SunStep (DIRECTOR_SUN) on a placed BP_ConclaveDirector: (what it holds now, whether this
    changed it). They exist once conclave_logic.py has run, which the run order puts after conclave:level."""
    tuned, changed = {}, False
    for key, value in DIRECTOR_SUN:
        try:
            if director.get_editor_property(key) != value:
                director.set_editor_property(key, value)
                changed = True
            tuned[key] = value
        except Exception:
            pass  # the variable is not there yet: tune_director() sets it after conclave:scenario
    return tuned, changed


def tune_director():
    """SunBase and SunStep on every placed BP_ConclaveDirector of the open level, saved when changed; run after the
    scenario, when conclave_logic.py has added the variables (see SUN_BASE)."""
    directors = [actor for actor in actors().get_all_level_actors() if actor.get_class().get_name() == 'BP_ConclaveDirector_C']
    results = [director_sun(director) for director in directors]
    if directors and all(len(tuned) == len(DIRECTOR_SUN) for tuned, _ in results):
        if any(changed for _, changed in results):
            save_level()
        return {'directors': len(directors), 'tuned': dict(DIRECTOR_SUN)}
    # Without them the director's fallback leaves the drum at a quarter of its light: say so, do not hide it.
    return {'directors': len(directors), 'tuned': False,
            'warning': 'BP_ConclaveDirector has no SunBase/SunStep: run Tools/blueprint_logic/conclave_logic.py, then conclave:scenario'}


# Materials the level puts on its own actors (sky(), spine_halos()); conclave:materials makes them.
LEVEL_MATERIALS = ('MI_CNSky', 'M_CNSpineHalo')


def check_level_materials():
    """Refuses before anything is removed or placed when a LEVEL_MATERIALS asset is missing (a sky sphere without its
    material would show the engine's default grid around the drum)."""
    missing = [name for name in LEVEL_MATERIALS if not library.does_asset_exist(MATS + '/' + name)]
    if missing:
        raise RuntimeError('%s missing: run conclave:materials first' % ', '.join(missing))


def build_level():
    """Terrain, the drum shell, the Spine and its halos, sky, light, fog, the look, reflections, the lake's water, the
    town and vegetation scatter, lamps and the level's directors."""
    for name in ('BP_SwimDirector', 'BP_Awakening', 'BP_ConclaveDirector'):
        if not library.does_asset_exist(game.BLUEPRINTS + '/' + name):
            raise RuntimeError(name + ' is missing: run conclave:blueprints first')
    check_level_materials()
    report = {'removed': open_level()}
    g = Ground()
    report['terrain'] = terrain(g)
    report['drum'] = drum()
    report['spine'] = spine()
    report['sky'] = sky()
    report['light'] = lighting()
    report['post'] = post()
    report['reflections'] = reflections(g)
    report['water'] = water(g)
    report['scatter'] = scatter()
    report['lights'] = place_lights(g)
    report['start'] = start(g)
    save_level()
    return report


# ---------------------------------------------------------------- Blueprints and input

IDLE = '/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle'
TRAIL_MESH = '/Engine/BasicShapes/Cylinder'


def new_blueprint(name):
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', unreal.Actor)
    return tools.create_asset(name, game.BLUEPRINTS, unreal.Blueprint, factory)


def blueprint_root(bp):
    """The new Blueprint's DefaultSceneRoot, found as physis_center_tools.blueprints() does. Taken once, before any
    component is added: afterwards the gather also returns the added scene components."""
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        item = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
        if isinstance(item, unreal.SceneComponent):
            return item
    raise RuntimeError('%s has no scene root' % bp.get_name())


def shape(bp, mesh, collision_profile='NoCollision', shadow=True, name='Shape', root=None):
    from editor_toolset.toolsets.actor import ActorTools
    # Under the root, as the Center attaches its Shapes (ActorTools.add_component takes the parent component).
    part = ActorTools.add_component(root or blueprint_root(bp), unreal.StaticMeshComponent.static_class(), name)
    if mesh:
        part.set_static_mesh(mesh)
    part.set_mobility(unreal.ComponentMobility.MOVABLE)
    part.set_collision_profile_name(collision_profile)
    part.set_editor_property('cast_shadow', shadow)
    return part


# BP_NPC's ChildActorComponent for a MetaHuman person (PEOPLE_DESIGN.md 3.1): the scenario gives it the person's
# assembled Blueprint class, so hiding BP_NPC hides the person and a rebuild updates every placed row. A MetaHuman faces
# +y in its own space (Physis's preview and studio cameras stand at +y), BP_NPC faces +x: the same turn as Body (spike S7).
LOOK = 'Look'
LOOK_YAW = -90.0


def fit_look(part):
    part.set_editor_property('relative_location', unreal.Vector(0, 0, 0))
    part.set_editor_property('relative_rotation', unreal.Rotator(0, 0, LOOK_YAW))
    part.set_mobility(unreal.ComponentMobility.MOVABLE)  # BP_NPC turns to face Physis while talking
    return part


def add_look(owner):
    """Look under BP_NPC's root; owner is the root of a new BP_NPC or an existing BP_NPC (ActorTools.add_component
    puts a component under the root either way)."""
    from editor_toolset.toolsets.actor import ActorTools
    return fit_look(ActorTools.add_component(owner, unreal.ChildActorComponent.static_class(), LOOK))


def npc_blueprint():
    """BP_NPC's components (README "People"): the Mannequin Body turned -90 so it faces +x like the garments, playing
    MM_Idle by itself once the scenario gives it a mesh; Lower, Upper and Head under the root (actor space), so the
    scenario's keep-world attachment to pelvis, spine_05 and head keeps each garment where it was modelled; Shape for
    figures that are not human; Look for a MetaHuman person, who then leaves Body and the garments empty. Talking is by
    distance, so nothing collides."""
    from editor_toolset.toolsets.actor import ActorTools
    bp = new_blueprint('BP_NPC')
    root = blueprint_root(bp)
    body = ActorTools.add_component(root, unreal.SkeletalMeshComponent.static_class(), 'Body')
    body.set_editor_property('relative_location', unreal.Vector(0, 0, 0))
    body.set_editor_property('relative_rotation', unreal.Rotator(0, 0, -90))
    body.set_mobility(unreal.ComponentMobility.MOVABLE)
    body.set_collision_profile_name('NoCollision')
    body.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    play = unreal.SingleAnimationPlayData()
    play.set_editor_property('anim_to_play', unreal.load_asset(IDLE))
    play.set_editor_property('saved_looping', True)
    play.set_editor_property('saved_playing', True)
    body.set_editor_property('animation_data', play)
    # About thirty people stand in the Commons: their idles only tick while someone can see them.
    body.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED)
    for name in ('Lower', 'Upper', 'Head', 'Shape'):
        shape(bp, None, name=name, root=root)  # all under the root: actor space, as the garments are modelled
    add_look(root)
    return bp


def blueprints():
    current = unreal.load_asset(MESHES + '/SM_CN_Current')
    trail = unreal.load_asset(MATS + '/M_CNLightTrail')
    input_report = light_step_input()
    made = []
    for name in ('BP_NPC', 'BP_Current', 'BP_ConclaveDirector', 'BP_LightTrail'):
        if library.does_asset_exist(game.BLUEPRINTS + '/' + name):
            continue  # conclave_logic.py has its variables and graphs: never remake it
        if name == 'BP_NPC':
            bp = npc_blueprint()
        elif name == 'BP_Current':
            if current is None:
                raise RuntimeError('SM_CN_Current is missing: run conclave:import first')
            bp = new_blueprint(name)
            shape(bp, current)
        elif name == 'BP_LightTrail':
            if trail is None:
                raise RuntimeError('M_CNLightTrail is missing: run conclave:materials first')
            bp = new_blueprint(name)
            part = shape(bp, unreal.load_asset(TRAIL_MESH), shadow=False)
            part.set_material(0, trail)
            part.set_default_custom_primitive_data_float(0, 1.0)  # Fade, until the trail's logic sets it
        else:
            bp = new_blueprint(name)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
        made.append(name)
    return {'made': made, 'input': input_report}


def light_step_input():
    """IA_LightStep on X and the gamepad's left shoulder, both free in play (GDD "Light Step"), added beside the
    existing mappings like the Center's Settle and Mend."""
    imc = unreal.load_asset('/Game/Input/IMC_Default')
    mappings = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
    existing = {(m.action.get_name() if m.action else None, game.key_name(m.key)) for m in mappings}
    path = game.ACTIONS + '/IA_LightStep'
    action = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset('IA_LightStep', game.ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
    game.save(action)
    taken = sorted('%s=%s' % (a, k) for a, k in existing if k in ('X', 'Gamepad_LeftShoulder') and a != 'IA_LightStep')
    for key in ('X', 'Gamepad_LeftShoulder'):
        if ('IA_LightStep', key) not in existing:
            bound = unreal.Key()
            bound.set_editor_property('key_name', key)
            imc.map_key(action, bound)
    game.save(imc)
    mapped = [game.key_name(m.key) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
              if m.action and m.action.get_name() == 'IA_LightStep']
    return {'IA_LightStep': mapped, 'shared_with': taken}


# ---------------------------------------------------------------- pause-menu map

def map_art():
    """Imports the pause menu's Conclave page (Tools/build_physis_conclave_map.py -> Art/UI/T_UI_MapConclave.png)
    as a UI texture, alone, with the Center's settings."""
    game.import_file(str(ROOT / 'Art/UI/T_UI_MapConclave.png'), '/Game/UI')
    texture = unreal.load_asset('/Game/UI/T_UI_MapConclave')
    if texture is None:
        raise RuntimeError('Art/UI/T_UI_MapConclave.png did not import')
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    for axis in ('address_x', 'address_y'):
        texture.set_editor_property(axis, unreal.TextureAddress.TA_CLAMP)
    game.save(texture)
    return {'map': [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]}


# ---------------------------------------------------------------- dispatcher

def scenario_module():
    import importlib
    import physis_conclave_scenario
    # The lore first: the scenario reads its tables at import time.
    importlib.reload(lore)
    importlib.reload(physis_conclave_scenario)
    return physis_conclave_scenario


def people_module():
    """Content/Python/physis_conclave_people.py, the MetaHuman people's steps, with the cast table it builds from. Both
    are reloaded here because the conclave: dispatcher (physis_outfit_tools) reloads only the plan, the lore and this
    module."""
    import importlib
    import physis_conclave_cast
    import physis_conclave_people
    importlib.reload(physis_conclave_cast)
    importlib.reload(physis_conclave_people)
    return physis_conclave_people


def execute(operation):
    if operation.startswith('exec:'):
        # exec:PATH runs a scratch script with this module's globals; it sets RESULT.
        scope = dict(globals())
        exec(open(operation.split(':', 1)[1]).read(), scope)
        return json.dumps(scope.get('RESULT'), default=str)
    if operation == 'materials':
        return json.dumps(materials(), default=str)
    if operation == 'textures':
        return json.dumps(import_textures(), default=str)
    if operation == 'rays':
        return json.dumps(ray_instances(), default=str)
    if operation == 'import':
        return json.dumps(import_meshes(), default=str)
    if operation.startswith('import:'):
        # import:PREFIX reimports only the meshes whose file name starts with PREFIX.
        return json.dumps(import_meshes(operation.split(':', 1)[1]), default=str)
    if operation == 'audio':
        return json.dumps(import_audio(), default=str)
    if operation == 'sound_classes':
        return json.dumps(sound_classes(), default=str)
    if operation == 'blueprints':
        return json.dumps(blueprints(), default=str)
    if operation == 'level':
        return json.dumps(build_level(), default=str)
    if operation == 'map_art':
        return json.dumps(map_art(), default=str)
    if operation == 'save':
        save_level()
        return json.dumps({'saved': LEVEL})
    if operation == 'scenario':
        report = scenario_module().place(Ground())
        report['sun'] = tune_director()  # the director's SunBase/SunStep exist now (see SUN_BASE)
        return json.dumps(report, default=str)
    if operation == 'portal':
        return json.dumps(scenario_module().portal(), default=str)
    if operation == 'surface_skeletal':
        return json.dumps(surface_skeletal(), default=str)
    if operation.startswith(('people_', 'npc_look')):
        return json.dumps(people_module().execute(operation), default=str)
    raise ValueError('unknown conclave operation ' + operation)
