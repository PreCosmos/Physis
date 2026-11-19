"""Builds level 7, Hesper, the City of One Voice, on Arche (`hesper:` operations). Tools/hesper/README.md is the contract.

Run order: materials, import, audio, map_art, blueprints, level (physis_hesper_level.py); then the Blueprint logic
(Tools/blueprint_logic/hesper_logic.py); then scenario and portal (physis_hesper_scenario.py). In the open editor the
operations run through Saved/Hesper/run/live.sh.

Hesper is on Arche: it stands on Kathodos's meshes (SM_AN_, SM_AV_, SM_AP_, the animals) and on the Grove's material
masters (M_GRSurface, M_GRPlain, M_GRGlow) and scans; nothing new is downloaded. What makes it the dusk is the grading:
MI_HS_* are Arche's MI_AR_* graded warm (honey stone, red-brown rock, bronze for silver), and every Arche material on a
mesh placed in L_Hesper is swapped for its MI_HS_ twin (regrade()). Two masters are new: M_HS_Unison (the Concord's
tone: unlit, translucent amber, its strength the component's custom primitive data 0, which BP_Unison sets) and
M_HS_Dissonance (her note: a clear blue-white ring, the same way).

  slot            look
  CN_White STONE  the slab-concrete scan graded to honey stone       CN_Black ROCK  the rock scan graded to red-brown
  CN_Metal ALLOY  the plate-steel scan graded to bronze              CN_Lacquer     enamel (vertex colour paint)
  CN_Gold         electrum      CN_Red  the AL's red     CN_Blue  glaze     CN_Cloth  the canvas scan, painted
  CN_Plaster      lichen        CN_Bark  the animals' hide           CN_Glow  light (vertex colour)
  CN_Glass        crystal, warmed                     CN_Ground  the terrain             CN_Water  the Reed Terraces

Operations: materials, tone_materials, import, import:PREFIX, audio, blueprints, input, map_art, level, level:PART, save,
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
ART = ROOT / 'Art/Meshes/Hesper'
HESPER = '/Game/Hesper'
MESHES = HESPER + '/Meshes'
MATS = HESPER + '/Materials'
AUDIO = HESPER + '/Audio'
ARCHE_MATS = '/Game/Arche/Materials'
LEVEL = '/Game/Levels/L_Hesper'
FOLDER = 'Hesper'
CM = 100.0
library = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

STONE_REF = (.60, .52, .42)
ROCK_REF = (.18, .095, .075)
BRONZE_REF = (.42, .30, .16)
DUST_REF = (.45, .38, .30)
GLOW_STRENGTH = 26.0
BREAKUP = (('MacroScale', 4000.0), ('MacroVariation', .42))
SCAN_TINT = (1.25, .92, .78)      # the Grove's brown rocks, warmed to the plateau's red-brown
GROUND_TINT = (.62, .54, .44)
BORROWED = ('SM_GS_Boulder', 'SM_GS_Stone', 'SM_GS_CliffC', 'SM_GS_CliffA', 'SM_GS_CliffB')
UNISON = (1.0, .64, .20)
DISSONANCE = (.70, .88, 1.0)


def surface(name, set_name, ref, paint=False, balance=.92, metal=False, tint=(1.0, 1.0, 1.0), tile=None, rough_scale=1.0, extra=()):
    """An M_GRSurface instance on a Grove texture set, graded toward `ref`."""
    row = gt.sets().get(set_name, {})
    scalars = [('Tile', (tile or row.get('tile_m') or 2.0) * CM), ('Paint', 1.0 if paint else 0.0), ('Balance', balance),
               ('MetalScale', 1.0 if metal else 0.0), ('RustLo', 2.0), ('RustHi', 3.0), ('RoughScale', rough_scale)] + list(extra)
    vectors = [('ScanMean', tuple(row.get('colour') or (.3, .3, .3))), ('Reference', tuple(ref)), ('Tint', tint)]
    return gt.instance(name, unreal.load_asset(gt.MATS + '/M_GRSurface'), scalars, vectors,
                       [('ScanColour', gt.scan_texture(set_name, 'D')), ('ScanNormal', gt.scan_texture(set_name, 'N')),
                        ('ScanMasks', gt.scan_texture(set_name, 'ARM'))], folder=MATS)


def plain(name, rough, metal, tint=(1.0, 1.0, 1.0)):
    return gt.instance(name, unreal.load_asset(gt.MATS + '/M_GRPlain'), [('Roughness', rough), ('Metallic', metal)], [('Tint', tint)], folder=MATS)


SLOT_MATERIAL = {'CN_Bark': 'MI_HS_Hide', 'CN_White': 'MI_HS_Stone', 'CN_Black': 'MI_HS_Rock', 'CN_Metal': 'MI_HS_Bronze', 'CN_Lacquer': 'MI_HS_Enamel',
                 'CN_Gold': 'MI_HS_Electrum', 'CN_Red': 'MI_HS_Red', 'CN_Blue': 'MI_HS_Glaze', 'CN_Cloth': 'MI_HS_Cloth', 'CN_Plaster': 'MI_HS_Lichen',
                 'CN_Glow': 'MI_HS_Glow', 'CN_Glass': 'MI_HS_Crystal', 'CN_Ground': 'MI_HS_Ground', 'CN_Water': 'MI_HS_Pool'}
# Arche's materials and their dusk twins: regrade() swaps one for the other on whatever is placed in L_Hesper.
TWINS = {'MI_AR_Stone': 'MI_HS_Stone', 'MI_AR_Rock': 'MI_HS_Rock', 'MI_AR_Alloy': 'MI_HS_Bronze', 'MI_AR_Enamel': 'MI_HS_Enamel',
         'MI_AR_Electrum': 'MI_HS_Electrum', 'MI_AR_Tile': 'MI_HS_Glaze', 'MI_AR_Cloth': 'MI_HS_Cloth', 'MI_AR_Lichen': 'MI_HS_Lichen',
         'MI_AR_Crystal': 'MI_HS_Crystal', 'MI_AR_Ground': 'MI_HS_Ground', 'MI_AR_Scan_Boulder': 'MI_HS_Scan_Boulder',
         'MI_AR_Scan_Stone': 'MI_HS_Scan_Stone', 'MI_AR_Scan_CliffC': 'MI_HS_Scan_CliffC', 'MI_AR_FrostGrass': 'MI_HS_DuskGrass'}


def materials():
    made = [surface('MI_HS_Stone', 'SConcreteSlab', STONE_REF, balance=.9).get_name(),
            surface('MI_HS_Rock', 'SRock', ROCK_REF, balance=.95, extra=BREAKUP).get_name(),
            surface('MI_HS_Bronze', 'SSteelPlates', BRONZE_REF, balance=.9, metal=True, rough_scale=.8).get_name(),
            surface('MI_HS_Enamel', 'SPaint', (.7, .68, .64), paint=True, balance=.3).get_name(),
            surface('MI_HS_Cloth', 'SCanvas', (.6, .56, .5), paint=True, balance=.3).get_name(),
            surface('MI_HS_Ground', 'SRock', DUST_REF, balance=.9, tile=7.0, tint=GROUND_TINT, extra=BREAKUP).get_name(),
            plain('MI_HS_Electrum', .3, 1.0, (1.0, .9, .72)).get_name(), plain('MI_HS_Red', .6, 0.0).get_name(),
            plain('MI_HS_Glaze', .14, 0.0, (3.0, 1.3, .35)).get_name(), plain('MI_HS_Lichen', .95, 0.0, (1.0, .9, .7)).get_name(), plain('MI_HS_Hide', .42, 0.0).get_name()]
    gt.instance('MI_HS_Glow', unreal.load_asset(gt.MATS + '/M_GRGlow'), [('Strength', GLOW_STRENGTH)], folder=MATS)
    plain('MI_HS_GlowOff', .3, 0.0, (.04, .03, .02))
    gt.instance('MI_HS_Crystal', unreal.load_asset(cn.MATS + '/M_CNGlass'), [('Opacity', .42), ('FresnelOpacity', .95), ('Roughness', .07)],
                [('Tint', (1.0, .80, .62))], folder=MATS)
    water = unreal.load_asset(cn.MATS + '/M_CNWater')
    gt.instance('MI_HS_Pool', water, [('Ripple', .12), ('RippleSpeed', .4), ('Clarity', 300.0), ('MaxOpacity', .9), ('TintDepth', 200.0),
                                      ('FoamStrength', .1), ('FoamWidth', 1.2), ('Roughness', .02)],
                [('WaterColour', (.10, .07, .05)), ('BodyColour', (.02, .012, .008)), ('FoamColour', (.8, .7, .6))], folder=MATS)
    borrowed = {}
    for stem in BORROWED:
        mesh = unreal.load_asset(gt.SCANS + '/' + stem)
        if mesh is None:
            continue
        mi = gt.instance('MI_HS_Scan_' + stem[6:], mesh.get_material(0), [('Moss', 0.0), ('DetailAmount', .5)], [('Tint', SCAN_TINT), ('DetailMean', (.2, .14, .08))],
                         folder=MATS)
        borrowed[stem] = mi.get_name()
    grass = gt.instance('MI_HS_DuskGrass', unreal.load_asset(gt.MATS + '/M_GRLeaf'), [('Part', 1.0), ('WindAmount', 2.0), ('Flutter', .5), ('Gain', .9)],
                        [('WarmTint', (1.15, .85, .5))],
                        [('Sheet', gt.scan_texture('LGrass', 'D')), ('SheetNormal', gt.scan_texture('LGrass', 'N')),
                         ('SheetMasks', gt.scan_texture('LGrass', 'ARM'))], folder=MATS)
    return {'instances': made + ['MI_HS_Glow', 'MI_HS_Crystal', 'MI_HS_Pool', grass.get_name()], 'borrowed': borrowed, 'tone': tone_materials(),
            'relinked': relink()}


def tone_master(name, colour, base=.12, rim=.6, bands=.25, speed=.25, glow=5.0, force=True):
    """An unlit, translucent, two-sided master: `colour` brighter and more opaque at grazing angles, with slow bands of
    light running up through it; custom primitive data 0 is its strength (0 unseen .. 1 whole). M_HS_Unison is the
    Concord's tone (amber, dense), M_HS_Dissonance her note (blue-white, thin, mostly rim)."""
    from physis_center_tools import node
    lib = unreal.MaterialEditingLibrary
    path = MATS + '/' + name
    if library.does_asset_exist(path) and not force:
        return 'kept'
    m = gt.master(name, MATS, blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, shading_model=unreal.MaterialShadingModel.MSM_UNLIT, two_sided=True)
    strength = node(m, unreal.MaterialExpressionScalarParameter, -900, 300, parameter_name='Strength', default_value=1.0, use_custom_primitive_data=True,
                    primitive_data_index=0)
    fres = node(m, unreal.MaterialExpressionFresnel, -900, 0, exponent=2.2, base_reflect_fraction=.04)
    tone = node(m, unreal.MaterialExpressionConstant3Vector, -900, -200, constant=unreal.LinearColor(*colour, 1.0))
    world = node(m, unreal.MaterialExpressionWorldPosition, -1300, 500)
    mask_z = node(m, unreal.MaterialExpressionComponentMask, -1100, 500, r=False, g=False, b=True, a=False)
    lib.connect_material_expressions(world, '', mask_z, '')
    per = node(m, unreal.MaterialExpressionDivide, -950, 500, const_b=120.0)
    lib.connect_material_expressions(mask_z, '', per, 'A')
    time = node(m, unreal.MaterialExpressionTime, -1100, 650)
    slow = node(m, unreal.MaterialExpressionMultiply, -950, 650, const_b=speed)
    lib.connect_material_expressions(time, '', slow, 'A')
    rise = node(m, unreal.MaterialExpressionSubtract, -800, 550)
    lib.connect_material_expressions(per, '', rise, 'A')
    lib.connect_material_expressions(slow, '', rise, 'B')
    band = node(m, unreal.MaterialExpressionFrac, -650, 550)
    lib.connect_material_expressions(rise, '', band, '')
    sharp = node(m, unreal.MaterialExpressionPower, -500, 550, const_exponent=4.0)
    lib.connect_material_expressions(band, '', sharp, 'Base')
    f2 = node(m, unreal.MaterialExpressionMultiply, -650, 0, const_b=2.0)
    lib.connect_material_expressions(fres, '', f2, 'A')
    b2 = node(m, unreal.MaterialExpressionMultiply, -350, 550, const_b=1.4)
    lib.connect_material_expressions(sharp, '', b2, 'A')
    s1 = node(m, unreal.MaterialExpressionAdd, -450, 100, const_b=.45)
    lib.connect_material_expressions(f2, '', s1, 'A')
    s2 = node(m, unreal.MaterialExpressionAdd, -250, 200)
    lib.connect_material_expressions(s1, '', s2, 'A')
    lib.connect_material_expressions(b2, '', s2, 'B')
    lit = node(m, unreal.MaterialExpressionMultiply, -100, -100)
    lib.connect_material_expressions(tone, '', lit, 'A')
    lib.connect_material_expressions(s2, '', lit, 'B')
    shown = node(m, unreal.MaterialExpressionMultiply, 100, -100, const_b=glow)
    lib.connect_material_expressions(lit, '', shown, 'A')
    emissive = node(m, unreal.MaterialExpressionMultiply, 250, -100)
    lib.connect_material_expressions(shown, '', emissive, 'A')
    lib.connect_material_expressions(strength, '', emissive, 'B')
    lib.connect_material_property(emissive, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # opacity = (base + rim * fresnel + bands * band) * strength
    o1 = node(m, unreal.MaterialExpressionMultiply, -650, 250, const_b=rim)
    lib.connect_material_expressions(fres, '', o1, 'A')
    o2 = node(m, unreal.MaterialExpressionAdd, -450, 300, const_b=base)
    lib.connect_material_expressions(o1, '', o2, 'A')
    o3 = node(m, unreal.MaterialExpressionMultiply, -350, 700, const_b=bands)
    lib.connect_material_expressions(sharp, '', o3, 'A')
    o4 = node(m, unreal.MaterialExpressionAdd, -200, 400)
    lib.connect_material_expressions(o2, '', o4, 'A')
    lib.connect_material_expressions(o3, '', o4, 'B')
    o5 = node(m, unreal.MaterialExpressionMultiply, 0, 400)
    lib.connect_material_expressions(o4, '', o5, 'A')
    lib.connect_material_expressions(strength, '', o5, 'B')
    lib.connect_material_property(o5, '', unreal.MaterialProperty.MP_OPACITY)
    lib.recompile_material(m)
    game.save(m)
    return 'built'


def tone_materials():
    return {'M_HS_Unison': tone_master('M_HS_Unison', UNISON, base=.2, rim=.55, bands=.3, speed=.35, glow=5.0),
            'M_HS_Dissonance': tone_master('M_HS_Dissonance', DISSONANCE, base=.0, rim=.4, bands=.06, speed=-.2, glow=3.0)}


# ---------------------------------------------------------------- import

NO_COLLISION = ('SM_SE_', 'SM_SN_Fork', 'SM_SN_Flute', 'SM_ST_Pool', 'SM_ST_Haze')
BOX_MESHES = ('SM_SN_Unison', 'SM_SN_Shell', 'SM_SN_Pylon', 'SM_SN_Parapet')
HARD_LODS = ((1.0, 1.0), (.5, .3), (.25, .12), (.12, .04))
TERRAIN_LODS = ((1.0, 1.0), (.5, .45), (.25, .2))


def apply_slots(mesh):
    unknown = []
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = cn.slot_name(slot)
        want = SLOT_MATERIAL.get(name)
        if mesh.get_name() == 'SM_ST_Haze' and name == 'CN_Ground':
            want = 'MI_HS_Rock'
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
        chain = TERRAIN_LODS if stem.startswith('SM_ST_Terrain') else None if stem.startswith('SM_ST_') else HARD_LODS
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


_twins = {}


def twin(material):
    """The dusk twin of an Arche material (or None)."""
    if material is None:
        return None
    name = material.get_name()
    if name not in TWINS:
        return None
    if name not in _twins:
        path = MATS + '/' + TWINS[name]
        _twins[name] = unreal.load_asset(path) if library.does_asset_exist(path) else None
    return _twins[name]


def regrade(actor):
    """Swaps every Arche material on the actor's mesh components for its dusk twin (the meshes stay Kathodos's)."""
    swapped = 0
    for part in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = part.get_editor_property('static_mesh')
        if mesh is None:
            continue
        for slot in range(part.get_num_materials()):
            material = part.get_material(slot)
            parent = material
            new = twin(parent)
            if new is not None and new != material:
                part.set_material(slot, new)
                swapped += 1
    return swapped


def import_audio():
    sounds, voices, loops = 0, 0, []
    music_class = unreal.load_asset(cn.MUSIC_CLASS)
    for path in sorted((ROOT / 'Art/Audio/Hesper').glob('*.wav')):
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
    for path in sorted((ROOT / 'Art/Audio/Hesper/Voice').glob('*.wav')):
        game.import_file(str(path), AUDIO + '/Voice')
        voices += 1
    return {'sounds': sounds, 'voices': voices, 'looping': loops}


# ---------------------------------------------------------------- Blueprints and input

NEW_BLUEPRINTS = ('BP_Unison', 'BP_Dissonance', 'BP_HesperDirector', 'BP_HesperCurrent')


def dissonance_input():
    """IA_Dissonance on C, and on the pad's D-pad up held 0.45 s (a tap still switches weapons)."""
    imc = unreal.load_asset('/Game/Input/IMC_Default')
    path = game.ACTIONS + '/IA_Dissonance'
    action = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset('IA_Dissonance', game.ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
    game.save(action)
    mappings = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
    existing = {(m.action.get_name() if m.action else None, game.key_name(m.key)) for m in mappings}
    added = []
    for key, hold in (('C', False), ('Gamepad_DPad_Up', True)):
        if ('IA_Dissonance', key) in existing:
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
    return {'added': added, 'IA_Dissonance': [(game.key_name(m.key), [t.get_class().get_name() for t in m.get_editor_property('triggers')]) for m in after
                                              if m.action and m.action.get_name() == 'IA_Dissonance'],
            'C elsewhere': [m.action.get_name() for m in after if m.action and game.key_name(m.key) == 'C' and m.action.get_name() != 'IA_Dissonance']}


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
    """Hesper's own Blueprints with their components (Tools/blueprint_logic/hesper_logic.py writes their graphs)."""
    made = []
    for name in NEW_BLUEPRINTS:
        if library.does_asset_exist(game.BLUEPRINTS + '/' + name):
            continue
        bp = cn.new_blueprint(name)
        if name == 'BP_Unison':
            gt.shape(bp, unreal.load_asset(MESHES + '/SM_SN_Unison'), shadow=False)
            light(bp, UNISON, 1200.0, 500.0)
        elif name == 'BP_Dissonance':
            ring = gt.shape(bp, unreal.load_asset('/Engine/BasicShapes/Sphere'), shadow=False)
            ring.set_editor_property('relative_scale3d', unreal.Vector(18.0, 18.0, 18.0))   # 9 m round her (the sphere is 1 m across)
            ring.set_collision_profile_name('NoCollision')
            ring.set_material(0, unreal.load_asset(MATS + '/M_HS_Dissonance'))
            light(bp, DISSONANCE, 1400.0, 120.0)
        elif name == 'BP_HesperCurrent':
            gt.shape(bp, unreal.load_asset(cn.MESHES + '/SM_CN_Current'))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
        made.append(name)
    return {'made': made, 'input': dissonance_input()}


def map_art():
    game.import_file(str(ROOT / 'Art/UI/T_UI_MapHesper.png'), '/Game/UI')
    texture = unreal.load_asset('/Game/UI/T_UI_MapHesper')
    if texture is None:
        raise RuntimeError('Art/UI/T_UI_MapHesper.png did not import')
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
    if operation == 'tone_materials':
        return json.dumps(tone_materials(), default=str)
    if operation == 'import' or operation.startswith('import:'):
        return json.dumps(import_meshes(operation.partition(':')[2]), default=str)
    if operation == 'audio':
        return json.dumps(import_audio(), default=str)
    if operation == 'blueprints':
        return json.dumps(blueprints(), default=str)
    if operation == 'input':
        return json.dumps(dissonance_input(), default=str)
    if operation == 'map_art':
        return json.dumps(map_art(), default=str)
    if operation == 'level':
        return json.dumps(_module('physis_hesper_level').build_level(), default=str)
    if operation.startswith('level:'):
        return json.dumps(_module('physis_hesper_level').execute(operation.split(':', 1)[1]), default=str)
    if operation == 'save':
        _module('physis_hesper_level').save_level()
        return json.dumps({'saved': LEVEL})
    if operation == 'scenario':
        _module('physis_hesper_lore')
        return json.dumps(_module('physis_hesper_scenario').place(_module('physis_hesper_level').Ground()), default=str)
    if operation == 'portal':
        return json.dumps(_module('physis_hesper_scenario').portal(), default=str)
    raise ValueError('unknown hesper operation ' + operation)
