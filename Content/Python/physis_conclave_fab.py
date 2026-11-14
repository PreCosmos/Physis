"""Fab packs in the Conclave (author, 2026-11-07: "Both": procedural assets plus free Fab packs, recoloured into the
level's five colours). The packs live untouched in their own folders (/Game/AncientTreasures, /Game/SICKA_MouldingSet,
/Game/OldWest, /Game/GV_FreeShrubsPack); the Conclave uses them through its own palette-locked materials, set on the
placed actors only, so the packs' assets stay as Fab delivered them.

M_CNFab (opaque, Default Lit) and M_CNFabLeaf (masked, two-sided foliage, wind) sample a pack's colour, normal and packed
roughness/metal/AO maps by UV and remap every colour texel into ONE palette family by its hue (a hard choice, never a
blend, so no in-between hue such as orange can appear): greys stay greys; bright warm hues become gold; dark warm hues
(wood, leather, soil) become the BrownTarget (black by default); reds become red; greens become the GreenTarget (light
blue patina on objects, a plant's own leaf colour on foliage); blues and cyans become light blue; purples and pinks the
PurpleTarget. A family colour keeps the texel's brightness, clamped so a gold never darkens into brown, a red into
maroon or a light blue into navy (palette.py's thresholds), and no albedo goes above 0.9.

Run in the editor through conclave:exec with a scratch script that imports this module, e.g.
    import physis_conclave_fab as fab; RESULT = fab.materials()
"""
import importlib
import json
import math
import pathlib

import unreal

import physis_conclave_tools as ct

lib = unreal.MaterialEditingLibrary
library = unreal.EditorAssetLibrary
PAL = ct.PAL
FAB_MATS = ct.MATS + '/Fab'

# Hue families. Angles are degrees in sRGB HSV; GreySat is the saturation below which a texel counts as grey.
REMAP = '''float3 c = saturate(C.rgb);
float3 s = pow(max(c, 0.0), 1.0 / 2.2);
float mx = max(s.r, max(s.g, s.b));
float mn = min(s.r, min(s.g, s.b));
float sat = (mx - mn) / max(mx, 0.0001);
float h = 0.0;
if (mx - mn > 0.0001)
{
    if (mx == s.r) { h = (s.g - s.b) / (mx - mn); }
    else if (mx == s.g) { h = 2.0 + (s.b - s.r) / (mx - mn); }
    else { h = 4.0 + (s.r - s.g) / (mx - mn); }
    h = frac(h / 6.0 + 1.0) * 360.0;
}
float lum = dot(c, float3(0.2126, 0.7152, 0.0722)) * Gain;
float3 target = float3(1.0, 1.0, 1.0);
float kmin = 0.0;
if (sat < GreySat)
{
    target = float3(1.0, 1.0, 1.0);
    kmin = 0.0;
}
else if (h < 14.0 || h >= 335.0)
{
    // Dark reds are rust, dried blood and stained wood: black, not maroon spots on gold.
    if (mx < RedV) { target = Brown.rgb; kmin = BrownMin; }
    else { target = Red.rgb; kmin = 0.16; }
}
else if (h < 68.0)
{
    if (mx < BrownV) { target = Brown.rgb; kmin = BrownMin; }
    else { target = Gold.rgb; kmin = 0.3; }
}
else if (h < 165.0)
{
    target = Green.rgb; kmin = GreenMin;
}
else if (h < 262.0)
{
    target = Blue.rgb; kmin = 0.42;
}
else
{
    target = Purple.rgb; kmin = 0.16;
}
float tl = max(dot(target, float3(0.2126, 0.7152, 0.0722)), 0.0001);
float k = clamp(lum / tl, kmin, 0.9 / max(max(target.r, target.g), target.b));
return target * k;'''
LEAF_WIND = ct.WIND

# Packed-map layouts: which channel holds roughness, metallic and ambient occlusion.
LAYOUTS = {'RMA': ((1, 0, 0), (0, 1, 0), (0, 0, 1)), 'ORM': ((0, 1, 0), (0, 0, 1), (1, 0, 0))}


def _vec(material, name, xyz, x, y):
    return ct.param(material, name, tuple(float(v) for v in xyz), x, y)


def _family_inputs(m, x, y):
    """The remap's palette targets as parameters (palette-checked through ct.cparam) and its thresholds."""
    return [('Red', ct.cparam(m, 'RedTarget', PAL.RED, x, y)), ('Gold', ct.cparam(m, 'GoldTarget', PAL.GOLD, x, y + 80)),
            ('Brown', ct.cparam(m, 'BrownTarget', PAL.CHARCOAL, x, y + 160)),
            ('Green', ct.cparam(m, 'GreenTarget', PAL.BLUE_PALE, x, y + 240)),
            ('Blue', ct.cparam(m, 'BlueTarget', PAL.BLUE, x, y + 320)),
            ('Purple', ct.cparam(m, 'PurpleTarget', PAL.RED, x, y + 400)),
            ('GreySat', ct.scalar(m, 'GreySaturation', .16, x, y + 480)), ('BrownV', ct.scalar(m, 'BrownValue', .42, x, y + 560)),
            ('RedV', ct.scalar(m, 'RedValue', .38, x, y + 880)),
            ('BrownMin', ct.scalar(m, 'BrownMin', 0.0, x, y + 640)), ('GreenMin', ct.scalar(m, 'GreenMin', .3, x, y + 720)),
            ('Gain', ct.scalar(m, 'BrightnessGain', 1.0, x, y + 800))]


def _textures(m, uv, x, y, alpha=False):
    base = ct.node(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name='BaseTex',
                   sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    packed = ct.node(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y + 300, parameter_name='PackedTex',
                     sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    normal = ct.node(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y + 600, parameter_name='NormalTex',
                     sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    for t in (base, packed, normal):
        lib.connect_material_expressions(uv, '', t, 'UVs')
    return base, packed, normal


def _defaults(m, base, packed, normal):
    """Engine textures as defaults, so an instance that misses one still compiles and renders flat."""
    for node, path in ((base, '/Engine/EngineResources/WhiteSquareTexture'), (normal, '/Engine/EngineMaterials/FlatNormal'),
                       (packed, None)):
        texture = unreal.load_asset(path) if path else ct.linear_white()
        if texture:
            node.set_editor_property('texture', texture)


def master_fab():
    m = ct.master('M_CNFab', tangent_space_normal=True, used_with_instanced_static_meshes=True)
    uv = ct.node(m, unreal.MaterialExpressionTextureCoordinate, -2200, 0, coordinate_index=0)
    base, packed, normal = _textures(m, uv, -1900, -300)
    _defaults(m, base, packed, normal)
    remap = ct.custom(m, REMAP, [('C', base)] + _family_inputs(m, -1500, -900), -900, -500, ct.FLOAT3)
    lib.connect_material_property(remap, '', ct.PROP.MP_BASE_COLOR)
    rmask = _vec(m, 'RoughMask', (1, 0, 0), -1500, 100)
    mmask = _vec(m, 'MetalMask', (0, 1, 0), -1500, 180)
    amask = _vec(m, 'AOMask', (0, 0, 1), -1500, 260)
    rough = ct.custom(m, 'return saturate(dot(P.rgb, M.rgb) * S + B);',
                      [('P', (packed, 'RGBA')), ('M', rmask), ('S', ct.scalar(m, 'RoughScale', 1.0, -1500, 340)),
                       ('B', ct.scalar(m, 'RoughBias', 0.0, -1500, 420))], -900, 100, ct.FLOAT1)
    metal = ct.custom(m, 'return saturate(lerp(dot(P.rgb, M.rgb), V, O));',
                      [('P', (packed, 'RGBA')), ('M', mmask), ('V', ct.scalar(m, 'MetalValue', 0.0, -1500, 500)),
                       ('O', ct.scalar(m, 'MetalOverride', 0.0, -1500, 580))], -900, 250, ct.FLOAT1)
    ao = ct.custom(m, 'return lerp(1.0, dot(P.rgb, M.rgb), K);',
                   [('P', (packed, 'RGBA')), ('M', amask), ('K', ct.scalar(m, 'AOAmount', 1.0, -1500, 660))], -900, 400, ct.FLOAT1)
    lib.connect_material_property(rough, '', ct.PROP.MP_ROUGHNESS)
    lib.connect_material_property(metal, '', ct.PROP.MP_METALLIC)
    lib.connect_material_property(ao, '', ct.PROP.MP_AMBIENT_OCCLUSION)
    lib.connect_material_property(normal, '', ct.PROP.MP_NORMAL)
    return ct.finish(m)


def master_fab_leaf():
    m = ct.master('M_CNFabLeaf', two_sided=True, shading_model=unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,
                  blend_mode=unreal.BlendMode.BLEND_MASKED, opacity_mask_clip_value=.4, tangent_space_normal=True,
                  used_with_instanced_static_meshes=True, dithered_lod_transition=True)
    uv = ct.node(m, unreal.MaterialExpressionTextureCoordinate, -2200, 0, coordinate_index=0)
    base, packed, normal = _textures(m, uv, -1900, -300)
    _defaults(m, base, packed, normal)
    remap = ct.custom(m, REMAP, [('C', base)] + _family_inputs(m, -1500, -900), -900, -500, ct.FLOAT3)
    lib.connect_material_property(remap, '', ct.PROP.MP_BASE_COLOR)
    rough = ct.custom(m, 'return saturate(dot(P.rgb, M.rgb) * S + B);',
                      [('P', (packed, 'RGBA')), ('M', _vec(m, 'RoughMask', (1, 0, 0), -1500, 100)),
                       ('S', ct.scalar(m, 'RoughScale', 1.0, -1500, 340)), ('B', ct.scalar(m, 'RoughBias', 0.0, -1500, 420))],
                      -900, 100, ct.FLOAT1)
    lib.connect_material_property(rough, '', ct.PROP.MP_ROUGHNESS)
    opacity = ct.custom(m, 'return lerp(1.0, A, U);', [('A', (base, 'A')), ('U', ct.scalar(m, 'UseAlpha', 1.0, -1500, 760))],
                        -900, 250, ct.FLOAT1)
    lib.connect_material_property(opacity, '', ct.PROP.MP_OPACITY_MASK)
    sub = ct.custom(m, 'return C * K;', [('C', remap), ('K', ct.scalar(m, 'SubsurfaceStrength', .6, -1500, 840))], -600, 350, ct.FLOAT3)
    lib.connect_material_property(sub, '', ct.PROP.MP_SUBSURFACE_COLOR)
    lib.connect_material_property(normal, '', ct.PROP.MP_NORMAL)
    lp = ct.node(m, unreal.MaterialExpressionLocalPosition, -1300, 900)
    wind = ct.custom(m, LEAF_WIND, [('LP', lp), ('WP', ct.node(m, unreal.MaterialExpressionWorldPosition, -1300, 1000)),
                                    ('T', ct.node(m, unreal.MaterialExpressionTime, -1300, 1100)),
                                    ('Speed', ct.scalar(m, 'WindSpeed', 1.0, -1000, 900)),
                                    ('Amount', ct.scalar(m, 'WindAmount', 1.6, -1000, 980)),
                                    ('Flutter', ct.scalar(m, 'Flutter', .5, -1000, 1060))], -700, 900, ct.FLOAT3)
    lib.connect_material_property(wind, '', ct.PROP.MP_WORLD_POSITION_OFFSET)
    return ct.finish(m)


def _source(path):
    """A pack material instance's textures and its layout: (base, normal, packed, layout, alpha) or None."""
    mi = unreal.load_asset(path)
    if not isinstance(mi, unreal.MaterialInstanceConstant):
        return None
    tex = {str(p.parameter_info.name).strip(): p.parameter_value for p in mi.get_editor_property('texture_parameter_values')}
    base = tex.get('Albedo') or tex.get('BaseColor') or tex.get('Base Color') or tex.get('Diffuse')
    normal = tex.get('Normal')
    packed, layout = (tex.get('RMA'), 'RMA') if tex.get('RMA') else ((tex.get('ORM'), 'ORM') if tex.get('ORM') else (None, 'RMA'))
    return base, normal, packed, layout


def fab_instance(source_path, name, leaf=False, targets=None, scalars=None):
    """MI_CNFab_<name> from a pack instance at source_path: its textures in the palette-locked master. targets maps
    family parameter names (RedTarget, GoldTarget, BrownTarget, GreenTarget, BlueTarget, PurpleTarget) to palette colours;
    scalars sets any other scalar."""
    src = _source(source_path)
    if src is None:
        raise RuntimeError('not a material instance: ' + source_path)
    base, normal, packed, layout = src
    parent = unreal.load_asset(ct.MATS + ('/M_CNFabLeaf' if leaf else '/M_CNFab'))
    r, mm, a = LAYOUTS[layout]
    vectors = [('RoughMask', r + (0,)), ('MetalMask', mm + (0,)), ('AOMask', a + (0,))]
    textures = [(k, t) for k, t in (('BaseTex', base), ('NormalTex', normal), ('PackedTex', packed)) if t is not None]
    mi_path = FAB_MATS + '/MI_CNFab_' + name
    if not library.does_directory_exist(FAB_MATS):
        library.make_directory(FAB_MATS)
    mi = unreal.load_asset(mi_path) if library.does_asset_exist(mi_path) else ct.tools.create_asset(
        'MI_CNFab_' + name, FAB_MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(mi, parent)
    lib.clear_all_material_instance_parameters(mi)
    for key, value in vectors:
        lib.set_material_instance_vector_parameter_value(mi, key, unreal.LinearColor(*value))
    for key, rgb in (targets or {}).items():
        lib.set_material_instance_vector_parameter_value(mi, key, ct.linear(rgb))   # linear() checks the palette
    merged = {}
    if packed is None:
        # No packed map: the master's default is linear white, which would read as fully metallic and fully rough.
        merged.update({'MetalOverride': 1.0, 'MetalValue': 0.0, 'RoughScale': .6, 'AOAmount': 0.0})
    merged.update(scalars or {})
    for key, value in merged.items():
        lib.set_material_instance_scalar_parameter_value(mi, key, float(value))
    for key, texture in textures:
        lib.set_material_instance_texture_parameter_value(mi, key, texture)
    lib.update_material_instance(mi)
    ct.game.save(mi)
    return mi


def materials():
    return {'M_CNFab': lib.get_statistics(master_fab()).num_pixel_shader_instructions,
            'M_CNFabLeaf': lib.get_statistics(master_fab_leaf()).num_pixel_shader_instructions}


# ---------------------------------------------------------------- placement (conclave:exec, physis_conclave_fab.place())

FOLDER = 'Conclave/Fab'
TREASURE = '/Game/AncientTreasures/Meshes/'
LABEL = 'Fab '
_MESHES = {}


def mesh_path(name):
    """A pack mesh's package path by asset name (the packs keep meshes in nested folders)."""
    if not _MESHES:
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        for pack in ('/Game/AncientTreasures', '/Game/SICKA_MouldingSet', '/Game/OldWest', '/Game/GV_FreeShrubsPack'):
            for a in reg.get_assets_by_path(pack, recursive=True):
                if str(a.asset_class_path.asset_name) == 'StaticMesh':
                    _MESHES[str(a.asset_name)] = str(a.package_name)
    return _MESHES[name]


def stone_instances():
    """Marble and gold for the moulding pack (its meshes carry no vertex colour, so the tint is the colour)."""
    parent = unreal.load_asset(ct.MATS + '/M_CNSurface')
    stone = dict(ct.SURFACE_DEFAULTS)
    stone.update(ct.SURFACES['MI_CN_White'][0])
    gold = dict(ct.SURFACE_DEFAULTS)
    gold.update(ct.SURFACES['MI_CN_Gold'][0])
    out = {}
    for name, scalars, tint, feature, sets in (('MI_CN_FabStone', stone, PAL.WHITE, PAL.grey(.30), 'Stone'),
                                                ('MI_CN_FabGold', gold, PAL.GOLD, PAL.grey(.58), 'Gold')):
        textures = (('DetailMasks', ct.detail_texture(sets, 'M')), ('DetailNormal', ct.detail_texture(sets, 'N')))
        out[name] = ct.instance(name, parent, scalars.items(), (('Tint', tint), ('FeatureColour', feature)), textures)
    return out


class Placer:
    """Spawns pack meshes on the ground with palette materials, refusing spots on roads, in the lake, on steep ground or
    against anything solid already there."""

    def __init__(self):
        self.sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        self.made, self.refused, self.cache = [], [], {}
        self.stone = stone_instances()
        import physis_conclave_plan as plan
        self.plan = plan

    def clear(self):
        n = 0
        for a in self.sub.get_all_level_actors():
            if str(a.get_folder_path()).startswith(FOLDER):
                self.sub.destroy_actor(a)
                n += 1
        return n

    def ground(self, x, y):
        """(z, normal z) of the terrain at x, y (cm), ignoring everything that is not terrain."""
        # From below the Spine (the axis is 706 m up): a trace from higher meets the far side of the drum first.
        hits = unreal.SystemLibrary.line_trace_multi(self.world, unreal.Vector(x, y, 50000), unreal.Vector(x, y, -20000),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        hits = hits[1] if isinstance(hits, tuple) else hits
        for hit in hits or []:
            t = hit.to_tuple()
            comp = t[10] if len(t) > 10 else None
            mesh = comp.static_mesh.get_name() if isinstance(comp, unreal.StaticMeshComponent) and comp.static_mesh else ''
            if mesh.startswith('SM_CD_Terrain'):
                return t[5].z, t[7].z
        return None, None

    def blocked(self, x, y, z, radius):
        types = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2]
        found = unreal.SystemLibrary.sphere_overlap_actors(self.world, unreal.Vector(x, y, z + radius + 20), radius, types, None, [])
        found = found[1] if isinstance(found, tuple) else found
        for a in found or []:
            label = a.get_actor_label()
            if label.startswith(('Terrain', 'SM_CD_Terrain')) or 'Terrain' in label or str(a.get_folder_path()).startswith('Conclave/Scatter'):
                continue
            return label
        return None

    def ok(self, x, y, radius, road=7.0, slope=.9, check=True):
        """The terrain height at a free spot, or None (and the reason is recorded)."""
        px, py = x / 100.0, y / 100.0
        if self.plan.path_gap(px, py) < road + radius / 100.0:
            return self._refuse(x, y, 'road')
        if self.plan.in_lake(px, py, 3.0):
            return self._refuse(x, y, 'lake')
        z, nz = self.ground(x, y)
        if z is None:
            return self._refuse(x, y, 'no terrain')
        if nz < slope:
            return self._refuse(x, y, 'slope')
        if check:
            hit = self.blocked(x, y, z, radius)
            if hit:
                return self._refuse(x, y, 'blocked by ' + hit)
        return z

    def _refuse(self, x, y, why):
        self.refused.append([round(x), round(y), why])
        return None

    def fab_mi(self, src, variant, leaf=False, targets=None, scalars=None):
        key = (src.get_path_name(), variant)
        if key not in self.cache:
            self.cache[key] = fab_instance(src.get_path_name().split('.')[0], src.get_name().replace('MI_', '') + variant, leaf, targets, scalars)
        return self.cache[key]

    def spawn(self, label, mesh_name, loc, yaw=0.0, scale=1.0, collide=True, materials='fab', leaf_colour=None, shadow=True,
              sink=0.0):
        mesh = unreal.load_asset(mesh_path(mesh_name))
        actor = self.sub.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(loc[0], loc[1], loc[2] - sink),
                                                unreal.Rotator(0.0, 0.0, yaw))
        actor.set_actor_label(LABEL + label)
        actor.set_folder_path(FOLDER)
        comp = actor.static_mesh_component
        comp.set_static_mesh(mesh)
        comp.set_mobility(unreal.ComponentMobility.STATIC)
        comp.set_collision_profile_name('BlockAll' if collide else 'NoCollision')
        comp.set_editor_property('cast_shadow', shadow)
        size = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
        actor.set_actor_scale3d(unreal.Vector(*size))
        for k, slot in enumerate(mesh.get_editor_property('static_materials')):
            src = slot.get_editor_property('material_interface')
            if materials in self.stone:
                comp.set_material(k, self.stone[materials])
                continue
            if src is None or 'Impostor' in src.get_name():
                continue
            sname = src.get_name()
            leafy = leaf_colour is not None and any(w in sname for w in ('Leaf', 'Frond'))
            if leafy:
                name, rgb = leaf_colour
                # Old West's desert fronds are dark olive: lift them so a gold or white plant does not render near black.
                lift = {'BrightnessGain': 1.9, 'GreenMin': .5} if '/OldWest/' in src.get_path_name() else None
                mi = self.fab_mi(src, '_' + name, True, {'GreenTarget': rgb, 'GoldTarget': rgb}, lift)
            else:
                mi = self.fab_mi(src, '')
            comp.set_material(k, mi)
        self.made.append([label, mesh_name, round(loc[0]), round(loc[1])])
        return actor


def _actor(sub, label):
    for a in sub.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def _local(origin, yaw_deg, u, v):
    a = math.radians(yaw_deg)
    return origin[0] + math.cos(a) * u - math.sin(a) * v, origin[1] + math.sin(a) * u + math.cos(a) * v


# A vault's hoard, in the court's frame (u toward the door, v across; cm from the court centre): along the back and
# side walls, clear of the gift in the middle and of the doorway.
HOARD = (('SM_Coin_Pile_01h', -420, -300, 0, 1.0, True), ('SM_Coin_Pile_01g', -430, 260, 30, 1.0, True),
         ('SM_OrnateChest_01b', -470, 0, 0, 1.0, True), ('SM_Statue_01a', -470, -470, 45, 1.3, True),
         ('SM_Statue_01a', -470, 470, -45, 1.3, True), ('SM_Urn_04a', 150, -480, 0, 1.0, True), ('SM_Urn_04a', 150, 480, 0, 1.0, True),
         ('SM_Coin_Pile_01d', -150, -470, 90, 1.0, False), ('SM_Coin_Pile_01e', -150, 470, -90, 1.0, False),
         ('SM_Chest_02d', 0, -480, 90, 1.0, True), ('SM_GoldBar_01a', -330, 120, 15, 3.0, False))
OFFERINGS = ('SM_Bowl_01a', 'SM_Chalice_01a', 'SM_Urn_01a', 'SM_Chalice_02a', 'SM_Urn_01a', 'SM_Bowl_01a')
SHRUB_TYPES = ('GV_Vol7_Shrub_A_full_type1', 'GV_Vol7_Shrub_B_full_type1', 'GV_Vol7_Shrub_D_full_type1')
COLUMN = 'SM_FullColumn_UV_1'


def place(clear_only=False):
    import physis_conclave_scenario as scenario
    p = Placer()
    report = {'cleared': p.clear()}
    if clear_only:
        return report
    PALE = PAL
    # 1. The sealed vaults' hoards.
    for title, _, _, _ in scenario.VAULTS:
        door = _actor(p.sub, 'Scene %s Door' % title)
        if door is None:
            report.setdefault('missing', []).append(title)
            continue
        d = door.get_actor_location()
        yaw = door.get_actor_rotation().yaw
        centre = _local((d.x, d.y), yaw, -600.0, 0.0)
        for k, (mesh, u, v, turn, scale, collide) in enumerate(HOARD):
            x, y = _local(centre, yaw, u, v)
            z, _ = p.ground(x, y)
            if z is not None:
                p.spawn('%s Hoard %d' % (title, k), mesh, (x, y, z), yaw + turn, scale, collide)
    # 2. Offerings round the Listeners Shrine; 3. urns and statues at the Archive's arcade.
    shrine = _actor(p.sub, 'Scene Listeners Shrine')
    if shrine:
        s = shrine.get_actor_location()
        for k, mesh in enumerate(OFFERINGS):
            a = math.radians(30 + k * 60)
            x, y = s.x + math.cos(a) * 560, s.y + math.sin(a) * 560
            z = p.ok(x, y, 60, road=3.0)
            if z is not None:
                p.spawn('Shrine Offering %d' % k, mesh, (x, y, z), math.degrees(a) + 180, 1.6, False)
    archive = _actor(p.sub, 'Scene Archive')
    if archive:
        c = archive.get_actor_location()
        yaw = archive.get_actor_rotation().yaw
        for k, (mesh, u, v, scale) in enumerate((('SM_Urn_04a', 1250, -450, 1.4), ('SM_Urn_04a', 1250, 450, 1.4),
                                                  ('SM_Statue_01a', 1250, -760, 1.8), ('SM_Statue_01a', 1250, 760, 1.8))):
            x, y = _local((c.x, c.y), yaw, u, v)
            z = p.ok(x, y, 80, road=2.0, check=False)
            if z is not None:
                p.spawn('Archive %s %d' % (mesh, k), mesh, (x, y, z), yaw, scale, True)
    # 4. Marble columns with gold urn finials at the Commons plaza's two road entrances and on its diagonals, and
    #    flanking the North Gate.
    ox, oy = p.plan.COMMONS_PLAZA[0] * 100, p.plan.COMMONS_PLAZA[1] * 100
    spots = [(ox + 4000, oy - 900), (ox + 4000, oy + 900), (ox - 4000, oy - 900), (ox - 4000, oy + 900)]
    spots += [(ox + math.cos(math.radians(a)) * 4000, oy + math.sin(math.radians(a)) * 4000) for a in (45, 135, 225, 315)]
    gate = _actor(p.sub, 'Scene North Gate')
    if gate:
        gl = gate.get_actor_location()
        spots += [(gl.x - 350, gl.y - 950), (gl.x - 350, gl.y + 950), (gl.x + 350, gl.y - 950), (gl.x + 350, gl.y + 950)]
    for k, (x, y) in enumerate(spots):
        z = p.ok(x, y, 90, road=5.0)
        if z is None:
            continue
        # Monumental: 6 m columns (the pack's are 3 m, house-sized) read against plazas a hundred metres across.
        p.spawn('Column %d' % k, COLUMN, (x, y, z), 0.0, 2.0, True, 'MI_CN_FabStone')
        p.spawn('Column Urn %d' % k, 'SM_Urn_01a', (x, y, z + 300 * 2.0 + 2), 0.0, 2.6, False)
    # 5. Feature shrubs (red, white, gold) round the Wellspring garden, the Commons plaza and the Archive.
    colours = (('Red', PAL.RED), ('White', PAL.WHITE_PURE), ('Gold', PAL.GOLD_STRAW))
    rings = [((p.plan.WELL[0] * 100, p.plan.WELL[1] * 100), 1500, 10), ((ox, oy), 4700, 14)]
    if archive:
        rings.append(((c.x, c.y), 1800, 7))
    n = 0
    for (cx, cy), radius, count in rings:
        for k in range(count):
            a = math.radians(k * 360.0 / count + 11)
            x, y = cx + math.cos(a) * radius, cy + math.sin(a) * radius
            z = p.ok(x, y, 220, road=4.0)
            if z is None:
                continue
            p.spawn('Shrub %d' % n, SHRUB_TYPES[n % 3], (x, y, z), (n * 67) % 360, .8 + .1 * (n % 3), False, 'fab', colours[n % 3],
                    sink=10)
            n += 1
    # 6. Yucca, Joshua trees and juniper among the Old Quarter's ruins.
    qx, qy, qr, _ = p.plan.REGIONS['Old Quarter']
    plants = (('SM_Yucca_02a', ('Red', PAL.RED)), ('SM_Yucca_03a', ('White', PAL.WHITE_PURE)), ('SM_Joshua_Tree_02a', ('White', PAL.WHITE_PURE)),
              ('SM_Juniper_Bush_01a', ('Gold', PAL.GOLD_STRAW)), ('SM_Yucca_05a', ('Red', PAL.RED)), ('SM_Joshua_Tree_04a', ('Gold', PAL.GOLD_STRAW)))
    import random
    rng = random.Random(23)
    placed = 0
    for tries in range(400):
        if placed >= 46:
            break
        a, r = rng.uniform(0, 2 * math.pi), qr * 100 * math.sqrt(rng.uniform(0.02, 0.9))
        x, y = qx * 100 + math.cos(a) * r, qy * 100 + math.sin(a) * r
        mesh, colour = plants[placed % len(plants)]
        z = p.ok(x, y, 180, road=5.0, slope=.85)
        if z is None:
            continue
        p.spawn('Quarter Plant %d' % placed, mesh, (x, y, z), rng.uniform(0, 360), rng.uniform(.85, 1.2), False, 'fab', colour, sink=8)
        placed += 1
    report['made'] = len(p.made)
    report['refused'] = len(p.refused)
    report['refused_sample'] = p.refused[:12]
    report['materials'] = len(p.cache)
    return report
