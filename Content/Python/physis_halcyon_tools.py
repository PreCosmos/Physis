"""Builds level 6, Halcyon, the Drowned Harbour (`halcyon:` operations). Tools/halcyon/README.md is the contract.

Run order: materials, import, audio, map_art, blueprints, level (physis_halcyon_level.py); then the Blueprint logic
(Tools/blueprint_logic/halcyon_logic.py); then scenario and portal (physis_halcyon_scenario.py). In the open editor
the operations run through Saved/Halcyon/run/live.sh.

Halcyon stands on the Grove's material masters (physis_grove_tools: M_GRSurface, M_GRPlain, M_GRGlow) and its scanned
texture sets; nothing new is downloaded. The grading is neutral: limestone and render pulled to a pale warm grey,
slate near black, steel dull and rusting, the sea grey-green. One master is new: M_HA_Trace, the past as Trace
Reading shows it (unlit, translucent pale silver, its strength the component's custom primitive data 0).

  slot            look
  CN_White STONE  the old-concrete scan graded to limestone, tinted by the vertex colour
  CN_Black ROCK   the concrete scan graded to the Just's grey
  CN_Metal ALLOY  the steel scan, dull, metallic       CN_Lacquer  paint: the vertex colour is the paint, the old-paint scan its wear
  CN_Gold         brass: plain metal                  CN_Red  matte red          CN_Blue  slate (the graphite scan)
  CN_Cloth        the canvas scan, painted            CN_Plaster  wrack and weed: plain, wet
  CN_Bark         timber: the planks scan, painted    CN_Glow  light (vertex colour)
  CN_Glass        window glass: the Conclave's glass, grey-green     CN_Ground  the terrain     CN_Water  the sea

Operations: materials, import, import:PREFIX, audio, blueprints, map_art, level, level:PART, save, scenario, portal,
exec:PATH.
"""
import json
import pathlib
import re

import unreal

import physis_conclave_tools as cn
import physis_gameplay_tools as game
import physis_grove_tools as gt

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
ART = ROOT / 'Art/Meshes/Halcyon'
HALCYON = '/Game/Halcyon'
MESHES = HALCYON + '/Meshes'
MATS = HALCYON + '/Materials'
AUDIO = HALCYON + '/Audio'
LEVEL = '/Game/Levels/L_Halcyon'
FOLDER = 'Halcyon'
CM = 100.0
library = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

LIME_REF = (.56, .55, .52)
CONCRETE_REF = (.30, .30, .29)
STEEL_REF = (.20, .20, .20)
SLATE_REF = (.06, .065, .075)
GROUND_REF = (.12, .12, .08)
GLOW_STRENGTH = 22.0
BREAKUP = (('MacroScale', 4000.0), ('MacroVariation', .35))
SCAN_TINT = (.78, .84, .92)     # the Grove's brown rocks, cooled to the coast's grey
BORROWED = ('SM_GS_Boulder', 'SM_GS_Stone', 'SM_GS_CliffC', 'SM_GS_CliffA', 'SM_GS_CliffB')
TRACE_SILVER = (.78, .84, .95)


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


SLOT_MATERIAL = {'CN_Bark': 'MI_HA_Timber', 'CN_White': 'MI_HA_Stone', 'CN_Black': 'MI_HA_Concrete', 'CN_Metal': 'MI_HA_Steel',
                 'CN_Lacquer': 'MI_HA_Paint', 'CN_Gold': 'MI_HA_Brass', 'CN_Red': 'MI_HA_Red', 'CN_Blue': 'MI_HA_Slate', 'CN_Cloth': 'MI_HA_Cloth',
                 'CN_Plaster': 'MI_HA_Wrack', 'CN_Glow': 'MI_HA_Glow', 'CN_Glass': 'MI_HA_Glass', 'CN_Ground': 'MI_HA_Ground', 'CN_Water': 'MI_HA_Sea'}


def trace_master(force=False):
    """M_HA_Trace: the past as Trace Reading shows it. Unlit, translucent, two-sided pale silver, brighter and more
    opaque at grazing angles (the edges read), with a slow drift of light up through it. The component's custom
    primitive data 0 is its strength (0 unseen .. 1 read), which BP_Trace sets."""
    from physis_center_tools import node
    lib = unreal.MaterialEditingLibrary
    path = MATS + '/M_HA_Trace'
    if library.does_asset_exist(path) and not force:
        return 'kept'
    m = gt.master('M_HA_Trace', MATS, blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, shading_model=unreal.MaterialShadingModel.MSM_UNLIT, two_sided=True)
    strength = node(m, unreal.MaterialExpressionScalarParameter, -900, 300, parameter_name='TraceT', default_value=1.0, use_custom_primitive_data=True,
                    primitive_data_index=0)
    fres = node(m, unreal.MaterialExpressionFresnel, -900, 0, exponent=2.5, base_reflect_fraction=.04)
    colour = node(m, unreal.MaterialExpressionConstant3Vector, -900, -200, constant=unreal.LinearColor(*TRACE_SILVER, 1.0))
    # A slow band of light rising through it: frac(world z / 300 cm - time * 0.15).
    world = node(m, unreal.MaterialExpressionWorldPosition, -1300, 500)
    mask_z = node(m, unreal.MaterialExpressionComponentMask, -1100, 500, r=False, g=False, b=True, a=False)
    lib.connect_material_expressions(world, '', mask_z, '')
    per = node(m, unreal.MaterialExpressionDivide, -950, 500, const_b=300.0)
    lib.connect_material_expressions(mask_z, '', per, 'A')
    time = node(m, unreal.MaterialExpressionTime, -1100, 650)
    slow = node(m, unreal.MaterialExpressionMultiply, -950, 650, const_b=.15)
    lib.connect_material_expressions(time, '', slow, 'A')
    rise = node(m, unreal.MaterialExpressionSubtract, -800, 550)
    lib.connect_material_expressions(per, '', rise, 'A')
    lib.connect_material_expressions(slow, '', rise, 'B')
    band = node(m, unreal.MaterialExpressionFrac, -650, 550)
    lib.connect_material_expressions(rise, '', band, '')
    sharp = node(m, unreal.MaterialExpressionPower, -500, 550, const_exponent=6.0)
    lib.connect_material_expressions(band, '', sharp, 'Base')
    # light = 0.5 + 2.2 * fresnel + 1.2 * band
    f2 = node(m, unreal.MaterialExpressionMultiply, -650, 0, const_b=2.2)
    lib.connect_material_expressions(fres, '', f2, 'A')
    b2 = node(m, unreal.MaterialExpressionMultiply, -350, 550, const_b=1.2)
    lib.connect_material_expressions(sharp, '', b2, 'A')
    s1 = node(m, unreal.MaterialExpressionAdd, -450, 100, const_b=.5)
    lib.connect_material_expressions(f2, '', s1, 'A')
    s2 = node(m, unreal.MaterialExpressionAdd, -250, 200)
    lib.connect_material_expressions(s1, '', s2, 'A')
    lib.connect_material_expressions(b2, '', s2, 'B')
    lit = node(m, unreal.MaterialExpressionMultiply, -100, -100)
    lib.connect_material_expressions(colour, '', lit, 'A')
    lib.connect_material_expressions(s2, '', lit, 'B')
    shown = node(m, unreal.MaterialExpressionMultiply, 100, -100, const_b=6.0)
    lib.connect_material_expressions(lit, '', shown, 'A')
    emissive = node(m, unreal.MaterialExpressionMultiply, 250, -100)
    lib.connect_material_expressions(shown, '', emissive, 'A')
    lib.connect_material_expressions(strength, '', emissive, 'B')
    lib.connect_material_property(emissive, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # opacity = (0.16 + 0.55 * fresnel + 0.2 * band) * T
    o1 = node(m, unreal.MaterialExpressionMultiply, -650, 250, const_b=.55)
    lib.connect_material_expressions(fres, '', o1, 'A')
    o2 = node(m, unreal.MaterialExpressionAdd, -450, 300, const_b=.16)
    lib.connect_material_expressions(o1, '', o2, 'A')
    o3 = node(m, unreal.MaterialExpressionMultiply, -350, 700, const_b=.2)
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


def materials():
    made = [surface('MI_HA_Stone', 'SConcreteSlab', LIME_REF, balance=.9, tint=(.8, .8, .78)).get_name(),
            surface('MI_HA_Concrete', 'SConcrete', CONCRETE_REF, balance=.92, extra=BREAKUP).get_name(),
            surface('MI_HA_Steel', 'SSteel', STEEL_REF, balance=.85, metal=True, rough_scale=1.1).get_name(),
            surface('MI_HA_Paint', 'SPaintOld', (.5, .5, .5), paint=True, balance=.35).get_name(),
            surface('MI_HA_Cloth', 'SCanvas', (.42, .4, .35), paint=True, balance=.3).get_name(),
            surface('MI_HA_Timber', 'SPlanks', (.2, .17, .13), paint=True, balance=.55).get_name(),
            surface('MI_HA_Slate', 'SGraphite', SLATE_REF, balance=.9, rough_scale=.8).get_name(),
            surface('MI_HA_Ground', 'SRockMoss', GROUND_REF, balance=.88, tile=5.0, extra=BREAKUP).get_name(),
            plain('MI_HA_Brass', .35, 1.0).get_name(), plain('MI_HA_Red', .6, 0.0).get_name(), plain('MI_HA_Wrack', .3, 0.0).get_name()]
    gt.instance('MI_HA_Glow', unreal.load_asset(gt.MATS + '/M_GRGlow'), [('Strength', GLOW_STRENGTH)], folder=MATS)
    plain('MI_HA_GlowOff', .3, 0.0, (.03, .03, .03))
    gt.instance('MI_HA_Glass', unreal.load_asset(cn.MATS + '/M_CNGlass'), [('Opacity', .55), ('FresnelOpacity', .9), ('Roughness', .05)],
                [('Tint', (.40, .48, .50))], folder=MATS)
    water = unreal.load_asset(cn.MATS + '/M_CNWater')
    gt.instance('MI_HA_Sea', water, [('Ripple', .35), ('RippleSpeed', .7), ('Clarity', 260.0), ('MaxOpacity', .92), ('TintDepth', 220.0),
                                     ('FoamStrength', .35), ('FoamWidth', 2.5), ('Roughness', .05)],
                [('WaterColour', (.05, .09, .08)), ('BodyColour', (.008, .016, .014)), ('FoamColour', (.75, .78, .76))], folder=MATS)
    # The Held Sea: water standing up in walls. The sea's translucent material reads pale on a vertical face, so the
    # walls are opaque and glossy: the vertex colour (dark water, foam at the crest) with a mirror finish.
    gt.instance('MI_HA_HeldSea', unreal.load_asset(gt.MATS + '/M_GRPlain'), [('Roughness', .04), ('Metallic', 0.0)], [('Tint', (.8, .9, .9))], folder=MATS)
    borrowed = {}
    for stem in BORROWED:
        mesh = unreal.load_asset(gt.SCANS + '/' + stem)
        if mesh is None:
            continue
        mi = gt.instance('MI_HA_Scan_' + stem[6:], mesh.get_material(0), [('Moss', .25), ('DetailAmount', .5)],
                         [('Tint', SCAN_TINT), ('DetailMean', (.2, .14, .08))], folder=MATS)
        borrowed[stem] = mi.get_name()
    return {'instances': made + ['MI_HA_Glow', 'MI_HA_Glass', 'MI_HA_Sea', 'MI_HA_HeldSea'], 'trace': trace_master(True), 'borrowed': borrowed,
            'relinked': relink()}


# ---------------------------------------------------------------- import

NO_COLLISION = ('SM_HE_', 'SM_HP_', 'SM_HN_Cache', 'SM_HN_Logbook', 'SM_HT_Sea')
BOX_MESHES = ('SM_HN_House', 'SM_HN_GateDoor', 'SM_HN_HeldSea', 'SM_HN_Shelf', 'SM_HN_Pump', 'SM_HN_Speaker', 'SM_HN_Lamp', 'SM_HN_Crate',
              'SM_HN_Bollard', 'SM_HN_Boat', 'SM_HN_Shed', 'SM_HN_Clocktower', 'SM_HN_SignalHouse')
HARD_LODS = ((1.0, 1.0), (.5, .3), (.25, .12), (.12, .04))
TERRAIN_LODS = ((1.0, 1.0), (.5, .45), (.25, .2))


def apply_slots(mesh):
    unknown = []
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = cn.slot_name(slot)
        want = SLOT_MATERIAL.get(name)
        if mesh.get_name() == 'SM_HN_HeldSea' and name == 'CN_Water':
            want = 'MI_HA_HeldSea'
        folder = MATS
        if name == 'CN_Ground':    # Earth's ground: the Grove's layered scans, weighted by the tile's vertices (land.layers())
            folder, want = gt.MATS, 'MI_GR_Ground'
        material = unreal.load_asset(folder + '/' + want) if want and library.does_asset_exist(folder + '/' + want) else None
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
        chain = TERRAIN_LODS if stem.startswith('SM_HT_Terrain') else None if stem.startswith('SM_HT_') else HARD_LODS
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
    for path in sorted((ROOT / 'Art/Audio/Halcyon').glob('*.wav')):
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
    for path in sorted((ROOT / 'Art/Audio/Halcyon/Voice').glob('*.wav')):
        game.import_file(str(path), AUDIO + '/Voice')
        voices += 1
    return {'sounds': sounds, 'voices': voices, 'looping': loops}


# ---------------------------------------------------------------- Blueprints and input

NEW_BLUEPRINTS = ('BP_Trace', 'BP_HalcyonDirector', 'BP_HalcyonCurrent')


def trace_input():
    """IA_TraceRead on T, and on the pad's D-pad down held 0.45 s (a tap is still Reload)."""
    imc = unreal.load_asset('/Game/Input/IMC_Default')
    path = game.ACTIONS + '/IA_TraceRead'
    action = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset('IA_TraceRead', game.ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
    game.save(action)
    mappings = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
    existing = {(m.action.get_name() if m.action else None, game.key_name(m.key)) for m in mappings}
    added = []
    for key, hold in (('T', False), ('Gamepad_DPad_Down', True)):
        if ('IA_TraceRead', key) in existing:
            continue
        bound = unreal.Key()
        bound.set_editor_property('key_name', key)
        mapping = imc.map_key(action, bound)
        if hold:
            trigger = unreal.new_object(unreal.InputTriggerHold, imc)
            trigger.set_editor_property('hold_time_threshold', .45)
            trigger.set_editor_property('is_one_shot', True)
            mapping.set_editor_property('triggers', [trigger])
            # map_key returns a copy in some builds: write the mapping back by index
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
    return {'added': added, 'IA_TraceRead': [(game.key_name(m.key), [t.get_class().get_name() for t in m.get_editor_property('triggers')]) for m in after
                                             if m.action and m.action.get_name() == 'IA_TraceRead']}


def blueprints():
    """Halcyon's own Blueprints with their components (Tools/blueprint_logic/halcyon_logic.py writes their graphs)."""
    made = []
    for name in NEW_BLUEPRINTS:
        if library.does_asset_exist(game.BLUEPRINTS + '/' + name):
            continue
        bp = cn.new_blueprint(name)
        if name == 'BP_Trace':
            gt.shape(bp, unreal.load_asset(MESHES + '/SM_HN_Catwalk'))
            glow = gt.add_component(bp, unreal.PointLightComponent, 'Glow')
            glow.set_editor_property('relative_location', unreal.Vector(0, 0, 150))
            glow.set_mobility(unreal.ComponentMobility.MOVABLE)
            glow.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
            glow.set_editor_property('intensity', 0.0)
            glow.set_editor_property('attenuation_radius', 900.0)
            glow.set_light_color(gt.linear(TRACE_SILVER))
            glow.set_cast_shadows(False)
        elif name == 'BP_HalcyonCurrent':
            gt.shape(bp, unreal.load_asset(cn.MESHES + '/SM_CN_Current'))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
        made.append(name)
    return {'made': made, 'input': trace_input()}


def map_art():
    game.import_file(str(ROOT / 'Art/UI/T_UI_MapHalcyon.png'), '/Game/UI')
    texture = unreal.load_asset('/Game/UI/T_UI_MapHalcyon')
    if texture is None:
        raise RuntimeError('Art/UI/T_UI_MapHalcyon.png did not import')
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
    if operation == 'trace_material':
        return json.dumps(trace_master(True), default=str)
    if operation == 'import' or operation.startswith('import:'):
        return json.dumps(import_meshes(operation.partition(':')[2]), default=str)
    if operation == 'audio':
        return json.dumps(import_audio(), default=str)
    if operation == 'blueprints':
        return json.dumps(blueprints(), default=str)
    if operation == 'input':
        return json.dumps(trace_input(), default=str)
    if operation == 'map_art':
        return json.dumps(map_art(), default=str)
    if operation == 'level':
        return json.dumps(_module('physis_halcyon_level').build_level(), default=str)
    if operation.startswith('level:'):
        return json.dumps(_module('physis_halcyon_level').execute(operation.split(':', 1)[1]), default=str)
    if operation == 'save':
        _module('physis_halcyon_level').save_level()
        return json.dumps({'saved': LEVEL})
    if operation == 'scenario':
        _module('physis_halcyon_lore')
        return json.dumps(_module('physis_halcyon_scenario').place(_module('physis_halcyon_level').Ground()), default=str)
    if operation == 'portal':
        return json.dumps(_module('physis_halcyon_scenario').portal(), default=str)
    raise ValueError('unknown halcyon operation ' + operation)
