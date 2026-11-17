"""Builds level 5, Arche, the First Ones' Planet (`arche:` operations). Tools/arche/README.md is the contract.

Run order: materials, import, audio, map_art, blueprints, level (physis_arche_level.py); then the Blueprint logic
(Tools/blueprint_logic/arche_logic.py); then scenario and portal (physis_arche_scenario.py). In the open editor the
operations run through Saved/Arche/run/live.sh.

Arche stands on the Grove's material masters (physis_grove_tools: M_GRSurface, M_GRPlain, M_GRGlow, M_GRRock,
M_GRScan, M_GRLeaf) and its scanned texture sets; nothing new is downloaded. What makes it another world is the
grading: every scanned surface is pulled to a cool reference colour (Balance near 1), the rock is blue-black, the
metal silver, and light comes from crystal. Instances are made in /Game/Arche/Materials as MI_AR_*.

  slot            look
  CN_White STONE  the slab-concrete scan graded to pale cool stone, tinted by the vertex colour
  CN_Black ROCK   the rock scan graded to blue-black
  CN_Metal ALLOY  the plate-steel scan graded to silver, metallic
  CN_Lacquer      enamel: the vertex colour is the paint, the paint scan its wear
  CN_Gold         electrum: plain metal            CN_Red  matte red            CN_Blue  glazed tile
  CN_Cloth        the canvas scan, painted         CN_Plaster  lichen: plain, very rough
  CN_Bark         the animals' hide: plain, a soft sheen
  CN_Glow         light (vertex colour)            CN_Glass  crystal: the Conclave's glass, denser, ice-tinted
  CN_Ground       the terrain: the rock scan over the vertex colour       CN_Water  the Cisterns

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
ART = ROOT / 'Art/Meshes/Arche'
ARCHE = '/Game/Arche'
MESHES = ARCHE + '/Meshes'
MATS = ARCHE + '/Materials'
AUDIO = ARCHE + '/Audio'
LEVEL = '/Game/Levels/L_Arche'
FOLDER = 'Arche'
CM = 100.0
library = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

STONE_REF = (.56, .58, .61)
ROCK_REF = (.11, .12, .145)
ALLOY_REF = (.56, .58, .60)
DUST_REF = (.47, .47, .46)
GLOW_STRENGTH = 26.0
# Large faces (the rim's cliffs, the Chasm's walls) showed the rock scan's repeat: a strong slow variation, 40 m
# across, breaks it up, and the scan itself is laid finer.
BREAKUP = (('MacroScale', 4000.0), ('MacroVariation', .42))
# The scanned rocks and grass borrowed from the Grove, regraded: (tint, moss)
SCAN_TINT = (.62, .80, 1.25)     # the Grove's brown rock, lifted and cooled to the risers' blue-grey
GROUND_TINT = (.50, .53, .60)     # the ground reads as pale stone dust, not snow: its albedo sits near .25
BORROWED = ('SM_GS_Boulder', 'SM_GS_Stone', 'SM_GS_CliffC', 'SM_GS_CliffA', 'SM_GS_CliffB')


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


SLOT_MATERIAL = {'CN_Bark': 'MI_AR_Hide', 'CN_White': 'MI_AR_Stone', 'CN_Black': 'MI_AR_Rock', 'CN_Metal': 'MI_AR_Alloy', 'CN_Lacquer': 'MI_AR_Enamel', 'CN_Gold': 'MI_AR_Electrum',
                 'CN_Red': 'MI_AR_Red', 'CN_Blue': 'MI_AR_Tile', 'CN_Cloth': 'MI_AR_Cloth', 'CN_Plaster': 'MI_AR_Lichen', 'CN_Glow': 'MI_AR_Glow',
                 'CN_Glass': 'MI_AR_Crystal', 'CN_Ground': 'MI_AR_Ground', 'CN_Water': 'MI_AR_Cistern'}


def materials():
    made = [surface('MI_AR_Stone', 'SConcreteSlab', STONE_REF, balance=.9).get_name(),
            surface('MI_AR_Rock', 'SRock', ROCK_REF, balance=.95, extra=BREAKUP).get_name(),
            surface('MI_AR_Alloy', 'SSteelPlates', ALLOY_REF, balance=.9, metal=True, rough_scale=.7).get_name(),
            surface('MI_AR_Enamel', 'SPaint', (.7, .7, .69), paint=True, balance=.3).get_name(),
            surface('MI_AR_Cloth', 'SCanvas', (.62, .62, .64), paint=True, balance=.3).get_name(),
            surface('MI_AR_Ground', 'SRock', DUST_REF, balance=.9, tile=7.0, tint=GROUND_TINT, extra=BREAKUP).get_name(),
            plain('MI_AR_Electrum', .3, 1.0).get_name(), plain('MI_AR_Red', .6, 0.0).get_name(), plain('MI_AR_Tile', .14, 0.0).get_name(),
            plain('MI_AR_Lichen', .95, 0.0).get_name(), plain('MI_AR_Hide', .42, 0.0).get_name()]   # Hide: the animals' skin
    gt.instance('MI_AR_Glow', unreal.load_asset(gt.MATS + '/M_GRGlow'), [('Strength', GLOW_STRENGTH)], folder=MATS)
    plain('MI_AR_GlowOff', .3, 0.0, (.03, .03, .04))   # a light that has gone out: the Lens after the Sunderer
    gt.instance('MI_AR_Crystal', unreal.load_asset(cn.MATS + '/M_CNGlass'), [('Opacity', .42), ('FresnelOpacity', .95), ('Roughness', .07)],
                [('Tint', (.55, .78, 1.0))], folder=MATS)
    water = unreal.load_asset(cn.MATS + '/M_CNWater')
    gt.instance('MI_AR_Cistern', water, [('Ripple', .1), ('RippleSpeed', .4), ('Clarity', 420.0), ('MaxOpacity', .88), ('TintDepth', 300.0),
                                         ('FoamStrength', .15), ('FoamWidth', 1.5), ('Roughness', .02)],
                [('WaterColour', (.03, .10, .13)), ('BodyColour', (.004, .012, .022)), ('FoamColour', (.7, .78, .82))], folder=MATS)
    # The Grove's scanned rocks, regraded: an instance of each one's own material, cooled and without moss.
    borrowed = {}
    for stem in BORROWED:
        mesh = unreal.load_asset(gt.SCANS + '/' + stem)
        if mesh is None:
            continue
        parent = mesh.get_material(0)
        mi = gt.instance('MI_AR_Scan_' + stem[6:], parent, [('Moss', 0.0), ('DetailAmount', .5)], [('Tint', SCAN_TINT), ('DetailMean', (.2, .14, .08))], folder=MATS)
        borrowed[stem] = mi.get_name()
    grass = gt.instance('MI_AR_FrostGrass', unreal.load_asset(gt.MATS + '/M_GRLeaf'), [('Part', 1.0), ('WindAmount', 2.4), ('Flutter', .5), ('Gain', .9)],
                        [('WarmTint', (.55, .8, 1.0))],
                        [('Sheet', gt.scan_texture('LGrass', 'D')), ('SheetNormal', gt.scan_texture('LGrass', 'N')),
                         ('SheetMasks', gt.scan_texture('LGrass', 'ARM'))], folder=MATS)
    return {'instances': made + ['MI_AR_Glow', 'MI_AR_Crystal', 'MI_AR_Cistern', grass.get_name()], 'borrowed': borrowed, 'relinked': relink()}


# ---------------------------------------------------------------- import

NO_COLLISION = ('SM_AE_', 'SM_AP_', 'SM_AN_Shard', 'SM_AN_Knot', 'SM_AN_Cache', 'SM_AN_Chime', 'SM_AN_Tablet', 'SM_AN_Seedstone', 'SM_AT_Cistern')
BOX_MESHES = ('SM_AN_Veil', 'SM_AN_VaultDoor', 'SM_AN_Bulwark')
HARD_LODS = ((1.0, 1.0), (.5, .3), (.25, .12), (.12, .04))
TERRAIN_LODS = ((1.0, 1.0), (.5, .45), (.25, .2))


def apply_slots(mesh):
    unknown = []
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        name = cn.slot_name(slot)
        want = SLOT_MATERIAL.get(name)
        material = unreal.load_asset(MATS + '/' + want) if want else None
        if material is None:
            unknown.append('%s -> %s' % (name, want))
            continue
        if slot.get_editor_property('material_interface') != material:
            mesh.set_material(index, material)
    return unknown


RIGGED = ARCHE + '/Rigged'


def skinned_usage(material):
    """The base material of `material` compiled for skinned meshes too (a packaged game draws the default grey
    material on a skinned mesh whose material was not)."""
    base = material.get_base_material() if hasattr(material, 'get_base_material') else material
    if base is None or base.get_editor_property('used_with_skeletal_mesh'):
        return None
    base.set_editor_property('used_with_skeletal_mesh', True)
    unreal.MaterialEditingLibrary.recompile_material(base)
    game.save(base)
    return base.get_name()


def import_rigs(source=None, destination=None):
    """Art/Meshes/Arche/Rigged (Tools/build_physis_arche_rigs.py): SK_AE_<Name>.fbx as a skinned mesh in the slots'
    looks, then each A_AE_<Name>_<Anim>.fbx as an animation on that mesh's skeleton."""
    source = pathlib.Path(source) if source else ART / 'Rigged'
    destination = destination or RIGGED
    report = {'meshes': {}, 'anims': {}, 'failed': [], 'usage': []}
    for path in sorted(source.glob('SK_*.fbx')):
        # A rig whose bones changed cannot be imported over its old skeleton, so the old assets go first (run the
        # scenario afterwards: placed animals lose their mesh until it sets it again).
        for old in [str(a).split('.')[0] for a in library.list_assets(destination, recursive=False)]:
            name = old.split('/')[-1]
            if name in (path.stem, path.stem + '_Skeleton', path.stem + '_PhysicsAsset') or name.startswith('A_%s_' % path.stem[3:]):
                library.delete_asset(old)
        options = unreal.FbxImportUI()
        for key, value in (('import_mesh', True), ('import_as_skeletal', True), ('import_materials', False), ('import_textures', False),
                           ('import_animations', False), ('create_physics_asset', False), ('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)):
            options.set_editor_property(key, value)
        data = options.skeletal_mesh_import_data
        data.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)
        data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        data.set_editor_property('import_morph_targets', False)
        game.import_file(str(path), destination, options)
        mesh = unreal.load_asset(destination + '/' + path.stem)
        if not isinstance(mesh, unreal.SkeletalMesh):
            report['failed'].append(path.stem)
            continue
        slots, unknown = list(mesh.get_editor_property('materials')), []
        for slot in slots:
            name = str(slot.get_editor_property('material_slot_name'))
            material = unreal.load_asset(MATS + '/' + SLOT_MATERIAL.get(name, '?'))
            if material is None:
                unknown.append(name)
                continue
            slot.set_editor_property('material_interface', material)
            changed = skinned_usage(material)
            if changed:
                report['usage'].append(changed)
        mesh.set_editor_property('materials', slots)
        game.save(mesh)
        skeleton = mesh.get_editor_property('skeleton')
        box = mesh.get_bounds().box_extent
        report['meshes'][path.stem] = {'bones': len(mesh.get_editor_property('skeleton').get_reference_pose().get_bone_names()) if hasattr(skeleton, 'get_reference_pose') else None,
                                      'slots': [str(s.get_editor_property('material_slot_name')) for s in slots], 'unknown': unknown,
                                      'half_size': [round(box.x), round(box.y), round(box.z)], 'skeleton': skeleton.get_name()}
        for clip in sorted(source.glob('A_%s_*.fbx' % path.stem[3:])):
            options = unreal.FbxImportUI()
            for key, value in (('import_mesh', False), ('import_as_skeletal', False), ('import_materials', False), ('import_textures', False),
                               ('import_animations', True), ('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION), ('skeleton', skeleton)):
                options.set_editor_property(key, value)
            anim_data = options.anim_sequence_import_data
            anim_data.set_editor_property('remove_redundant_keys', False)
            anim_data.set_editor_property('import_bone_tracks', True)
            game.import_file(str(clip), destination, options)
            sequence = unreal.load_asset(destination + '/' + clip.stem)
            if not isinstance(sequence, unreal.AnimSequence):
                report['failed'].append(clip.stem)
                continue
            report['anims'][clip.stem] = round(sequence.get_play_length(), 2)
    report['assets'] = sorted(str(a).split('.')[-1] for a in library.list_assets(destination, recursive=False))
    return report


def animal_body():
    """BP_TrainingDrone's Body: an empty skinned-mesh part under Shape. An animal's skinned mesh goes in it (the
    scenario sets it per actor) and rides Shape's motion; the machines leave it empty."""
    path = '/Game/Characters/Physis/Blueprints/BP_TrainingDrone'
    bp = unreal.load_asset(path)
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    data_of = unreal.SubobjectDataBlueprintFunctionLibrary
    parts = {}
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        item = data_of.get_associated_object(data_of.get_data(handle))
        if isinstance(item, unreal.SceneComponent):
            parts[item.get_name().split('_GEN')[0]] = handle
    if 'Body' in parts:
        return {'body': 'already there', 'parts': sorted(parts)}
    handle, why = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=parts['Shape'], new_class=unreal.SkeletalMeshComponent,
                                                                            blueprint_context=bp))
    body = data_of.get_object_for_blueprint(data_of.get_data(handle), bp)
    if body is None:
        raise RuntimeError('Body was not added (%s)' % why)
    subobjects.rename_subobject(handle, unreal.Text('Body'))
    body.set_mobility(unreal.ComponentMobility.MOVABLE)
    body.set_collision_profile_name('NoCollision')
    body.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    body.set_editor_property('bounds_scale', 2.0)   # limbs swing outside the rest pose's box
    body.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    game.save(bp)
    return {'body': 'added', 'parts': sorted(parts)}


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
        chain = TERRAIN_LODS if stem.startswith('SM_AT_Terrain') else None if stem.startswith('SM_AT_') else HARD_LODS
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
    for path in sorted((ROOT / 'Art/Audio/Arche').glob('*.wav')):
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
    for path in sorted((ROOT / 'Art/Audio/Arche/Voice').glob('*.wav')):
        game.import_file(str(path), AUDIO + '/Voice')
        voices += 1
    return {'sounds': sounds, 'voices': voices, 'looping': loops}


# ---------------------------------------------------------------- Blueprints and input

NEW_BLUEPRINTS = ('BP_Weave', 'BP_ArcheDirector', 'BP_ArcheCurrent')


def weave_input():
    """IA_Reweave on B and the right stick's click, added beside the existing mappings; reports any other action
    already on those keys."""
    imc = unreal.load_asset('/Game/Input/IMC_Default')
    mappings = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
    existing = {(m.action.get_name() if m.action else None, game.key_name(m.key)) for m in mappings}
    path = game.ACTIONS + '/IA_Reweave'
    action = unreal.load_asset(path) if library.does_asset_exist(path) else \
        tools.create_asset('IA_Reweave', game.ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
    game.save(action)
    keys = ('B', 'Gamepad_RightThumbstick')
    wrong = unreal.Key()
    wrong.set_editor_property('key_name', 'V')     # V is Settle's: an earlier version of this bound Reweave to it too
    if ('IA_Reweave', 'V') in existing:
        imc.unmap_key(action, wrong)
    taken = sorted('%s=%s' % (a, k) for a, k in existing if k in keys and a != 'IA_Reweave')
    for key in keys:
        if ('IA_Reweave', key) not in existing:
            bound = unreal.Key()
            bound.set_editor_property('key_name', key)
            imc.map_key(action, bound)
    game.save(imc)
    return {'IA_Reweave': [game.key_name(m.key) for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
                           if m.action and m.action.get_name() == 'IA_Reweave'], 'shared_with': taken,
            'all': sorted('%s=%s' % (a, k) for a, k in existing)}


def blueprints():
    """Arche's own Blueprints with their components (Tools/blueprint_logic/arche_logic.py writes their graphs)."""
    made = []
    for name in NEW_BLUEPRINTS:
        if library.does_asset_exist(game.BLUEPRINTS + '/' + name):
            continue
        bp = cn.new_blueprint(name)
        if name == 'BP_Weave':
            gt.shape(bp, unreal.load_asset(MESHES + '/SM_AN_Span'))
            mark = gt.shape(bp, unreal.load_asset(MESHES + '/SM_AN_Knot'), shadow=False, name='Mark')
            mark.set_editor_property('relative_location', unreal.Vector(0, 0, 150))
            for k in range(6):   # the slivers that circle the mark and fall into it (arche_logic.py PIECES)
                gt.shape(bp, unreal.load_asset(MESHES + '/SM_AN_Shard%d' % (k % 4)), shadow=False, name='P%d' % k)
            glow = gt.add_component(bp, unreal.PointLightComponent, 'Glow')
            glow.set_editor_property('relative_location', unreal.Vector(0, 0, 150))
            glow.set_mobility(unreal.ComponentMobility.MOVABLE)
            glow.set_editor_property('intensity_units', unreal.LightUnits.CANDELAS)
            glow.set_editor_property('intensity', 5.0)
            glow.set_editor_property('attenuation_radius', 800.0)
            glow.set_light_color(gt.linear((1.0, .88, .62)))
            glow.set_cast_shadows(False)
        elif name == 'BP_ArcheCurrent':
            gt.shape(bp, unreal.load_asset(cn.MESHES + '/SM_CN_Current'))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        game.save(bp)
        made.append(name)
    return {'made': made, 'input': weave_input()}


def map_art():
    game.import_file(str(ROOT / 'Art/UI/T_UI_MapArche.png'), '/Game/UI')
    texture = unreal.load_asset('/Game/UI/T_UI_MapArche')
    if texture is None:
        raise RuntimeError('Art/UI/T_UI_MapArche.png did not import')
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
    if operation == 'import' or operation.startswith('import:'):
        return json.dumps(import_meshes(operation.partition(':')[2]), default=str)
    if operation == 'audio':
        return json.dumps(import_audio(), default=str)
    if operation == 'animal_body':
        return json.dumps(animal_body(), default=str)
    if operation == 'import_rigs' or operation.startswith('import_rigs:'):
        test = operation.partition(':')[2]   # a trial folder under the project, imported in place of Art/Meshes/Arche/Rigged
        return json.dumps(import_rigs(*((ROOT / test,) if test else ())), default=str)
    if operation == 'blueprints':
        return json.dumps(blueprints(), default=str)
    if operation == 'map_art':
        return json.dumps(map_art(), default=str)
    if operation == 'level':
        return json.dumps(_module('physis_arche_level').build_level(), default=str)
    if operation.startswith('level:'):
        return json.dumps(_module('physis_arche_level').execute(operation.split(':', 1)[1]), default=str)
    if operation == 'save':
        _module('physis_arche_level').save_level()
        return json.dumps({'saved': LEVEL})
    if operation == 'scenario':
        _module('physis_arche_lore')
        return json.dumps(_module('physis_arche_scenario').place(_module('physis_arche_level').Ground()), default=str)
    if operation == 'portal':
        return json.dumps(_module('physis_arche_scenario').portal(), default=str)
    raise ValueError('unknown arche operation ' + operation)
