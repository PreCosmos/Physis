"""The Conclave's dressed people as MetaHumans (Tools/conclave/PEOPLE_DESIGN.md): one editor step per operation, so a GPU
editor session can run them one at a time through the conclave dispatcher (`outfit_operation conclave:<op>:<Key>`,
physis_conclave_tools.execute, which reloads this module and the cast first). <Key> is a key of physis_conclave_cast.MH,
the speaker's first row (Listener, Kairos, Teodor...); a pending entry is refused. Every operation returns a
JSON-able report and raises when it cannot do its step. What the MH table holds is in physis_conclave_cast's docstring.

Per person, in this order (PEOPLE_DESIGN.md 3.3, Phase 1):
  people_new:<Key>[:replace]  the MetaHumanCharacter FILES['character'] from MH[<Key>]: blended face presets, landmark
                              sculpt, body, skin, eyes, lashes, makeup, grooms; writes FILES['face_record']. An existing
                              character is refused unless ':replace' is given, which deletes it with its face rig, its
                              texture sources and any HeadScale set in MetaHuman Creator
  people_preview:<Key>        studio portraits (front, three-quarter, profile, full body) of the character, and of its
                              assembled look once there is one, as PNGs beside the face record, shot in L_PeopleStudio.
                              The author approves the look; HeadScale (Python cannot write it) is set in MetaHuman
                              Creator and the character saved there
  people_guides:<Key>         the body and face meshes as FBX (FILES['body_guide'], FILES['face_guide']) for the costume
                              build. Then quit the editor: Blender and Unreal never run together
  [Blender, headless: Tools/build_conclave_people.py writes FILES['costume_fbx'] and FILES['cloth_mask_png']]
  people_rig:<Key>            Epic's cloud auto-rig (cast.RIG). THE AUTHOR SIGNS IN (SIGN_IN)
  people_textures:<Key>       Epic's cloud texture sources (cast.TEXTURE_SOURCES), in the same session as people_rig
  people_assemble:<Key>       the OPTIMIZED build into BUILD_PATH/<Key> (FILES['look']), shared assets in COMMON. A real
                              GPU only (it bakes): fresh editor, apps closed, Tools/watch_unreal_vram.sh running on the
                              host, and COMMON backed up before the first build (Physis shares it)
  conclave:surface_skeletal   once, physis_conclave_tools: M_CNSurface compiles for skeletal meshes (not conclave:materials)
  people_import:<Key>         the costume FILES['costume'] on cast.SKELETON in the Conclave's slot materials, and its
                              cloth mask FILES['cloth_mask']. Only ever a fresh import: a new costume replaces the old
                              one with the editor closed (delete its .uasset first), as Physis's outfit was
  people_post:<Key>           the assembled Blueprint's post-pass: Body plays cast.IDLE from the entry's start at its
                              rate, ticking, card hair, ray tracing, texture caps, the costume under Body, the body skin
                              masked under the costume. Assembly rewrites the Blueprint, so it runs after every build
  people_verify[:<Key>]       read-only checks of the post-pass, for every assembled person without a key
  npc_look                    once: BP_NPC's Look, the ChildActorComponent the scenario shows each person through
Then Tools/blueprint_logic/conclave_logic.py npc (BeginPlay's talk range and icon height count Look's child actor) and
conclave:scenario, whose people report must be empty. Rollback: LOOKS = 'mannequin' in physis_conclave_cast, then
conclave:scenario.

Hazards kept to (Tools/conclave/people_research.json): every subsystem call needs the character registered for editing;
RequestAutoRigging and CommitHeadModelSettings index the editing map without checking it, so an unregistered character
crashes the editor (registered()). A registration a step makes is released when the step ends, even on an error; one
that MetaHuman Creator holds is used and left alone (opened()). Plugin content (the presets, the Creator's lookdev
textures) may be changed in memory only: never save a /MetaHumanCharacter package; reports list any left changed.
Editor Python: no numpy.
"""
import contextlib
import json
import math
import re

import unreal

import physis_conclave_cast as cast
import physis_conclave_tools as T
import physis_gameplay_tools as game

REPLACE = 'replace'  # people_new:<Key>:replace rebuilds an existing character
SIGN_IN = ('The author signs in to Epic in the editor: the first cloud request of a session opens Epic\'s sign-in (EOS, '
           'in a browser) and only the author may complete it; a 403 means the MetaHuman EULA is not accepted on that account.')
# Reruns of an unchanged face reuse Epic's cached rig instead of another 150-300 s request (PEOPLE_DESIGN.md 3.2).
AUTORIG_CACHE = 'MetaHuman.Cloud.Autorig.UseDdc 1'

# The slots a character's grooms fill (MetaHumanCharacter Config/Editor.ini); the lashes come with the eyelash type.
GROOM_SLOTS = ('Hair', 'Eyebrows', 'Beard', 'Mustache', 'Peachfuzz')
NO_FRECKLES = {'mask': 'NONE'}
# The eight texture-source resolutions (MetaHumanCharacterSkin.h, FMetaHumanCharacterTextureSourceResolutions).
SOURCE_FIELDS = ('face_albedo', 'face_normal', 'face_cavity', 'face_animated_maps', 'body_albedo', 'body_normal', 'body_cavity',
                 'body_masks')
# MH body fields and the body constraints they drive: Height in cm, the rest a fraction of the constraint's range.
BODY_GLOBALS = (('height_cm', 'Height'), ('masculine_feminine', 'Masculine/Feminine'), ('fat', 'Fat'), ('muscularity', 'Muscularity'))
# A patch's values in the face model's coefficient vector, counted from its start (PatchBlendModel.cpp
# SerializeToVector): scale, rotation quaternion x y z w, translation x y z, then the count of its PCA weights and the
# weights themselves.
SCALE, ROTATION, TRANSLATION, MODES = 0, range(1, 5), range(5, 8), 8

# The person's own assets sit beside the costume: /Game/Characters/Conclave/<Key>.
FOLDER = cast.FILES['costume'].rsplit('/', 1)[0]
BODY_MATERIAL = FOLDER + '/MI_{key}_Body'
# Physis's masked copy of the MetaHuman body master (physis_animation_tools body_mask): its ClothMask, white where skin
# shows, hides the skin under clothes. Each person's skin hangs under it with their own mask (spike S8).
MASK_MASTER = '/Game/Characters/Physis/Materials/M_Physis_Body'
MASK_PARAMETER = 'ClothMask'
COSTUME = 'Costume'  # the costume's component under Body; physis_conclave_scenario.fitting() reads it by this name
# People stay out of ray tracing, meshes and hair, until spike S10 measures what they cost there (PEOPLE_DESIGN.md 3.2).
IN_RAY_TRACING = False
# The MetaHuman component's correctives and neck rig: costly for a standing NPC, little to see (PEOPLE_DESIGN.md 3.2).
MH_COMPONENT_OFF = ('enable_body_correctives', 'enable_neck_correctives', 'enable_neck_proc_control_rig')
# Physis's low-memory assembly (physis_outfit_tools trim_preview_textures): the Creator's preview textures, never
# saved, shrink so the bake has the VRAM (on 2026-10-30 a full VRAM stalled the laptop).
PREVIEW_TEXTURES = ('/MetaHumanCharacter/Lookdev', '/Engine/Transient')
PREVIEW_TEXTURE_CAP = 512

STUDIO = cast.FILES['character'].rsplit('/', 1)[0] + '/Preview/L_PeopleStudio'
CUBE = '/Engine/BasicShapes/Cube'
CYLINDER = '/Engine/BasicShapes/Cylinder'
# A subject stands at the origin facing +y, as MetaHuman previews do (Physis's portrait camera stands at +y,
# Tools/capture_physis_preview.py). Views: (name, bearing from +y toward +x in degrees, distance cm, aim height as a
# fraction of the person's height, field of view degrees). Eyes are at about 93.5% of standing height.
EYE_LEVEL = .935
VIEWS = (('front', 0.0, 105.0, EYE_LEVEL, 30.0), ('three_quarter', 35.0, 105.0, EYE_LEVEL, 30.0),
         ('profile', 90.0, 105.0, EYE_LEVEL, 30.0), ('body', 20.0, 430.0, .5, 34.0))
PORTRAIT_SIZE = 1024
# Physis's tuned review lights (physis_outfit_tools review_scene), white here so skin, eyes and hair are judged in
# neutral light: (label, place cm, intensity), all aimed at STUDIO_AIM, each STUDIO_LIGHT_SIZE cm.
STUDIO_LIGHTS = (('People Studio Key', (-180.0, 220.0, 260.0), 1600.0), ('People Studio Fill', (180.0, 190.0, 180.0), 800.0),
                 ('People Studio Rim', (0.0, -180.0, 210.0), 2000.0))
STUDIO_AIM = (0.0, 0.0, 120.0)
STUDIO_LIGHT_SIZE = (140.0, 180.0)
# Grey walls behind the front and the side views, so the portraits are not cut out of a black void and auto exposure
# meters a lit scene: (label, place cm, scale of the 1 m cube). The platform is Physis's studio disc.
STUDIO_WALLS = (('People Studio Back', (0.0, -320.0, 200.0), (8.0, .1, 4.0)), ('People Studio Side', (-320.0, 0.0, 200.0), (.1, 8.0, 4.0)))
STUDIO_PLATFORM = ('People Studio Platform', (0.0, 0.0, -3.0), (1.6, 1.6, .05))


# ---------------------------------------------------------------- shared

def person(key):
    """MH[key], refusing a key that is no buildable MetaHuman."""
    entry = cast.MH.get(key)
    if entry is None:
        owner = next((name for name, item in cast.MH.items() if key in item['rows']), None)
        if owner:
            raise ValueError('%s is a row of %s: name the MetaHuman, conclave:<op>:%s' % (key, owner, owner))
        raise ValueError('no MetaHuman %r in physis_conclave_cast.MH (%s)' % (key, ', '.join(sorted(cast.MH))))
    if entry['pending']:
        raise RuntimeError('%s is pending and not built: %s' % (key, entry['pending']))
    return entry


def exists(path):
    return unreal.EditorAssetLibrary.does_asset_exist(path)


def package(item):
    return item.get_path_name().split('.')[0]


def project_file(pattern, key):
    return T.ROOT / pattern.format(key=key)


def shown_path(path):
    return str(path.relative_to(T.ROOT))


def creator():
    return unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)


def actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def character(key):
    path = cast.FILES['character'].format(key=key)
    if not exists(path):
        raise RuntimeError('%s does not exist: run conclave:people_new:%s first' % (path, key))
    return unreal.load_asset(path)


@contextlib.contextmanager
def opened(made):
    """The MetaHuman subsystem with `made` registered for editing. A registration this step makes is released when the
    step ends, even on an error (the first one loads the 985 MB texture-synthesis model, the last release unloads it);
    one MetaHuman Creator or an earlier step already holds is used and left as it was."""
    sub = creator()
    if sub.is_object_added_for_editing(made):
        yield sub
        return
    if not sub.try_add_object_to_edit(made):
        raise RuntimeError('could not open %s for editing (LogMetaHumanCharacterEditor says why)' % made.get_path_name())
    try:
        yield sub
    finally:
        sub.remove_object_to_edit(made)


def registered(sub, made):
    """Guards the calls that crash the editor on a character not registered for editing."""
    if not sub.is_object_added_for_editing(made):
        raise RuntimeError('%s is not open for editing' % made.get_name())


def plugin_changes():
    """MetaHuman plugin packages changed in memory (registering a preset can migrate it, assembly caps lookdev
    textures). They are the engine's own content: never save them."""
    return sorted(item.get_name() for item in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                  if item.get_name().startswith('/MetaHumanCharacter/'))


def linear(value, natural):
    """A cast colour: a palette name (linear RGB) or, for natural colours only (skin, nails, eyes), an RGB tuple. Makeup
    and costume colours must be palette names: the palette rule still binds them."""
    if isinstance(value, str):
        if value not in T.PAL.PALETTE:
            raise ValueError('%r is not a palette colour (Tools/conclave_meshes/palette.py)' % value)
        rgb = T.PAL.PALETTE[value][:3]
    elif natural:
        rgb = tuple(float(c) for c in value)
    else:
        raise ValueError('%r: makeup colours are palette names' % (value,))
    return unreal.LinearColor(*rgb, 1.0)


def fill(struct, values, natural):
    """Sets fields of a MetaHuman settings struct by their Python names, as Epic's examples do. A field's kind comes from
    its current value: an enum takes the member the table names ('TYPE1', 'IRIS003'), a colour a cast colour."""
    for name, value in values.items():
        current = getattr(struct, name)
        if isinstance(current, unreal.EnumBase):
            value = getattr(type(current), value)
        elif isinstance(current, unreal.LinearColor):
            value = linear(value, natural)
        setattr(struct, name, value)


def blueprint_parts(blueprint):
    """{variable name: (component template, subobject handle, subobject data)} of a Blueprint's own components. The
    templates are named <name>_GEN_VARIABLE, so components are known by their variable names (Body, Face, Costume)."""
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    found = {}
    for handle in unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem).k2_gather_subobject_data_for_blueprint(blueprint):
        data = library.get_data(handle)
        template = library.get_associated_object(data)
        if isinstance(template, unreal.ActorComponent):
            found[str(library.get_variable_name(data))] = (template, handle, data)
    return found


def assembled(key):
    path = cast.FILES['look'].format(key=key)
    if not exists(path):
        raise RuntimeError('%s is not assembled: run conclave:people_assemble:%s first' % (path, key))
    return unreal.load_asset(path)


def skin_materials(mesh, key):
    """The body skin's material instances on an assembled body mesh: MI_Body* in this person's own build folder, never
    a shared one in COMMON."""
    own = cast.BUILD_PATH + '/' + key + '/'
    return [slot.material_interface for slot in mesh.get_editor_property('materials')
            if slot.material_interface and slot.material_interface.get_name().startswith('MI_Body')
            and slot.material_interface.get_path_name().startswith(own)]


def texture_kind(path):
    """The TEXTURE_CAPS entry an assembled texture falls under, from where assembly puts it and how it names it
    (MH_Physis: Face/Baked/T_Head_LOD3_*, T_BakedNormal_LOD4, T_EyeIrisL_BC, T_Teeth_N, Body/Baked/T_Body_BC_VT); the
    face's unnumbered maps serve its best LOD. None for the hair cards' own textures, which assembly already caps."""
    name = path.rsplit('/', 1)[-1].split('.')[0]
    if name.startswith('T_Teeth'):
        return 'teeth'
    if name.startswith('T_Eye'):
        return 'eyes'
    if '/Body/' in path:
        return 'body'
    if '/Face/' in path:
        lod = re.search(r'LOD(\d+)', name)
        return 'face_lod1' if lod is None or int(lod.group(1)) <= 1 else 'face_other_lods'
    return None


def capped_textures(key):
    """(path, texture, cap) for every texture of the person's build that TEXTURE_CAPS covers."""
    rows = []
    for path in unreal.EditorAssetLibrary.list_assets(cast.BUILD_PATH + '/' + key, recursive=True, include_folder=False):
        kind = texture_kind(path)
        texture = unreal.load_asset(path) if kind else None
        if isinstance(texture, unreal.Texture2D):
            rows.append((path, texture, cast.TEXTURE_CAPS[kind]))
    return rows


# ---------------------------------------------------------------- people_new

def discard(path):
    """Deletes the character at path for people_new's replace. Its editors close and its registration is released
    first: a character open in MetaHuman Creator or registered for editing cannot be deleted."""
    # people_preview's studio actor keeps the character alive, and a live object at the path makes the new create open
    # an 'Overwrite Existing Object' dialog no script can answer: leave the studio level first (2026-11-09).
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is not None and world.get_path_name().split('.')[0].startswith(path.rsplit('/', 1)[0] + '/Preview/'):
        unreal.EditorLoadingAndSavingUtils.load_map('/Engine/Maps/Entry')
    old = unreal.load_asset(path)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(old)
    sub = creator()
    if sub.is_object_added_for_editing(old):
        sub.remove_object_to_edit(old)
    del old
    if not unreal.EditorAssetLibrary.delete_asset(path):
        raise RuntimeError('could not delete %s (something still references it): delete it in the Content Browser, then '
                           'run people_new again' % path)
    # The deleted object stays in memory until garbage collection; creating the new character at the same path before
    # that opens an 'Overwrite Existing Object' dialog, which a script cannot answer, and the create fails (2026-11-09).
    unreal.SystemLibrary.collect_garbage()


def patches(values):
    """[(index of each patch's scale, its PCA weight count)] of a face coefficient vector; the counts must account for
    every value."""
    count, at, layout = int(round(values[0])), 1, []
    for _ in range(count):
        modes = int(round(values[at + MODES]))
        layout.append((at, modes))
        at += MODES + 1 + modes
    if at != len(values):
        raise ValueError('face coefficients: %d values, but their layout accounts for %d' % (len(values), at))
    return layout


def blend(template, sources, push):
    """The weighted blend of the presets' face coefficients [(values, weight)], laid out as template, the archetype's.
    Counts are copied, never blended: the model reads them back with an int cast, so 11.9999 would be 11 and shift every
    value after it. Each patch's quaternions are taken into the first one's hemisphere before they are averaged (q and
    -q are one rotation) and renormalised. Only the PCA weights are pushed: w becomes t + push * (w - t), t the
    archetype's weight."""
    layout = patches(template)
    for values, _ in sources:
        if patches(values) != layout:
            raise ValueError('a preset\'s face coefficients are laid out unlike a new character\'s')

    def mix(index):
        return sum(values[index] * weight for values, weight in sources)

    out = list(template)
    for at, modes in layout:
        out[at + SCALE] = mix(at + SCALE)
        first = [sources[0][0][at + i] for i in ROTATION]
        rotation = [0.0] * len(ROTATION)
        for values, weight in sources:
            quaternion = [values[at + i] for i in ROTATION]
            side = 1.0 if sum(a * b for a, b in zip(quaternion, first)) >= 0 else -1.0
            rotation = [total + side * weight * c for total, c in zip(rotation, quaternion)]
        length = math.sqrt(sum(c * c for c in rotation))
        if length == 0:
            raise ValueError('face patch at %d: the presets\' rotations cancel out' % at)
        for i, c in zip(ROTATION, rotation):
            out[at + i] = c / length
        for i in TRANSLATION:
            out[at + i] = mix(at + i)
        for index in range(at + MODES + 1, at + MODES + 1 + modes):
            out[index] = template[index] + push * (mix(index) - template[index])
    return out


def points(vectors):
    return [(p.x, p.y, p.z) for p in vectors]


def shape_face(sub, made, face):
    """The face: the presets' blend (each preset opened for editing to read it), then the landmark sculpt, requested
    SCULPT_GAIN times larger than the change wanted, since the face model applies only part of a move. Returns the face
    record: the coefficients, the landmarks before and after the sculpt, and how much of each wanted move the mesh took
    (spike S4)."""
    template = list(sub.get_face_model_coefficients(made))
    sources = []
    for name, weight in face['presets']:
        path = cast.PRESETS + '/' + name
        preset = unreal.load_asset(path)
        if preset is None:
            raise RuntimeError('preset %s is missing (the MetaHumanCharacter plugin\'s optional content)' % path)
        with opened(preset) as reader:
            sources.append((list(reader.get_face_model_coefficients(preset)), float(weight)))
    blended = blend(template, sources, float(face['push']))
    sub.set_face_model_coefficients(made, blended)
    sub.commit_face_state(made)
    before = points(sub.get_face_landmarks(made))
    moves = [(index, tuple(float(c) for c in delta)) for index, delta in face['landmarks']]
    stray = [index for index, _ in moves if not 0 <= index < len(before)]
    if stray:
        raise ValueError('landmarks %s are not among the face\'s %d' % (stray, len(before)))
    if moves:
        sub.translate_face_landmarks(made, [index for index, _ in moves],
                                     [unreal.Vector(*(c * cast.SCULPT_GAIN for c in delta)) for _, delta in moves])
        sub.commit_face_state(made)
    after = points(sub.get_face_landmarks(made))
    applied = {}
    for index, delta in moves:
        moved = [a - b for a, b in zip(after[index], before[index])]
        applied[index] = round(sum(m * d for m, d in zip(moved, delta)) / sum(d * d for d in delta), 3)
    return {'presets': [list(item) for item in face['presets']], 'push': face['push'], 'gain': cast.SCULPT_GAIN,
            'coefficients': list(sub.get_face_model_coefficients(made)), 'wanted_cm': {i: list(d) for i, d in moves},
            'before': before, 'after': after, 'applied': applied}


def shape_body(sub, made, body, problems):
    """The body constraints, as the MetaHumanGenerator toolset sets them (Height in cm inside its range, the rest lerped
    over theirs), then the neck refitted to the body; reset_neck_to_body only applies the face state, so it is
    committed again."""
    named = {str(item.name): item for item in sub.get_body_constraints(made, False)}
    wanted = [(name, body[field]) for field, name in BODY_GLOBALS] + sorted(body['measurements'].items())
    targets = {}
    for name, value in wanted:
        constraint = named.get(name)
        if constraint is None:
            raise RuntimeError('the body model has no constraint %r (it has %s)' % (name, ', '.join(sorted(named))))
        low, high = float(constraint.min_measurement), float(constraint.max_measurement)
        if name == 'Height':
            target = min(max(float(value), low), high)
            if target != float(value):
                problems.append('height %.1f cm is outside the body model\'s %.1f-%.1f cm: built at %.1f (spike S13)' %
                                (value, low, high, target))
        else:
            target = low + (high - low) * float(value)
        constraint.is_active = True
        constraint.target_measurement = target
        targets[name] = round(target, 2)
    sub.set_body_constraints(made, list(named.values()))
    sub.commit_body_state(made)
    unreal.MetaHumanGeneratorSubsystemWrapper.reset_neck_to_body(made)
    sub.commit_face_state(made)
    return targets


def paint_skin(sub, made, entry):
    """Skin, freckles, accents and the texture sources the cloud will send (all TEXTURE_SOURCES), committed at once:
    a later skin commit would resynthesise the textures and drop downloaded ones."""
    settings = made.skin_settings
    fill(settings.skin, entry['skin'], natural=True)
    fill(settings.freckles, entry['freckles'] or NO_FRECKLES, natural=True)
    for region, values in entry['accents'].items():
        fill(getattr(settings.accents, region), values, natural=True)
    sources = settings.desired_texture_sources_resolutions
    for field in SOURCE_FIELDS:
        setattr(sources, field, getattr(type(getattr(sources, field)), cast.TEXTURE_SOURCES))
    sub.commit_skin_settings(made, settings)


def wrong_sources(made):
    """The texture-source resolutions that are not TEXTURE_SOURCES."""
    sources = made.skin_settings.desired_texture_sources_resolutions
    return {field: str(getattr(sources, field)) for field in SOURCE_FIELDS
            if getattr(sources, field) != getattr(type(getattr(sources, field)), cast.TEXTURE_SOURCES)}


def paint_eyes(sub, made, eyes):
    """Both eyes alike: the iris colours (u warmth, v brightness) and pattern, then the entry's 'part.field' values."""
    settings = made.eyes_settings
    iris = {'primary_color_u': eyes['primary'][0], 'primary_color_v': eyes['primary'][1], 'secondary_color_u': eyes['secondary'][0],
            'secondary_color_v': eyes['secondary'][1], 'pattern': eyes['pattern']}
    for eye in (settings.eye_left, settings.eye_right):
        fill(eye.iris, iris, natural=True)
        for path, value in eyes['set'].items():
            part, name = path.split('.')
            fill(getattr(eye, part), {name: value}, natural=True)
    sub.commit_eyes_settings(made, settings)


def set_lashes(sub, made, lashes):
    """The eyelashes (their type also selects the matching eyelash groom)."""
    registered(sub, made)
    settings = made.head_model_settings
    fill(settings.eyelashes, lashes, natural=True)
    sub.commit_head_model_settings(made, settings)


def set_makeup(sub, made, makeup):
    if not makeup:
        return
    settings = made.makeup_settings
    for part, values in makeup.items():
        fill(getattr(settings, part), values, natural=False)
    sub.commit_makeup_settings(made, settings)


def set_grooms(sub, made, grooms, problems):
    """Each groom slot takes its wardrobe item or is cleared, through the preview collection, which
    on_edit_preview_collection copies into the character (edits to its internal collection would be lost the next time
    the preview is rebuilt). A groom's colour parameters exist only once the preview is assembled."""
    collection = sub.get_preview_collection(made)
    if collection is None:
        raise RuntimeError('%s has no preview collection' % made.get_name())
    keys = {}
    for slot in GROOM_SLOTS:
        if slot not in grooms:
            collection.default_instance.set_single_slot_selection(slot, unreal.MetaHumanPaletteItemKey())
            continue
        path = grooms[slot][0]
        item = unreal.load_asset(path)
        if item is None:
            raise RuntimeError('groom %s is missing (the MetaHumanCharacter plugin\'s optional content)' % path)
        key = collection.try_add_item_from_wardrobe_item(slot, item)
        if key is None:
            raise RuntimeError('%s did not go into the %s slot' % (path, slot))
        collection.default_instance.set_single_slot_selection(slot, key)
        keys[slot] = key
    sub.on_edit_preview_collection(made)
    sub.assemble_for_preview(made)
    for slot, key in keys.items():
        found = {str(item.name): item for item in
                 collection.default_instance.get_instance_parameters(unreal.MetaHumanPaletteItemPath(item_key=key))}
        for name, value in grooms[slot][1].items():
            if name in found:
                found[name].set_float(float(value))
            else:
                problems.append('%s groom %s has no parameter %s' % (slot, grooms[slot][0].rsplit('/', 1)[-1], name))
    sub.on_edit_preview_collection(made)
    return {slot: grooms[slot][0].rsplit('/', 1)[-1] for slot in keys}


def people_new(key, replace=False):
    entry = person(key)
    path = cast.FILES['character'].format(key=key)
    replaced = exists(path)
    if replaced:
        if not replace:
            raise RuntimeError('%s exists: conclave:people_new:%s:%s rebuilds it from MH, deleting its face rig, its texture '
                               'sources and any HeadScale set in MetaHuman Creator' % (path, key, REPLACE))
        discard(path)
    folder, name = path.rsplit('/', 1)
    made = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.MetaHumanCharacter,
                                                                   unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew))
    if made is None:
        raise RuntimeError('could not create ' + path)
    # Epic's scripts all edit with the editable preview material; the build code warns exported textures can be black otherwise.
    made.set_editor_property('preview_material_type', unreal.MetaHumanCharacterSkinPreviewMaterial.EDITABLE)
    problems = []
    with opened(made) as sub:
        record = shape_face(sub, made, entry['face'])
        body = shape_body(sub, made, entry['body'], problems)
        paint_skin(sub, made, entry)
        paint_eyes(sub, made, entry['eyes'])
        set_lashes(sub, made, entry['lashes'])
        set_makeup(sub, made, entry['makeup'])
        grooms = set_grooms(sub, made, entry['grooms'], problems)
        game.save(made)
    record_file = project_file(cast.FILES['face_record'], key)
    record_file.parent.mkdir(parents=True, exist_ok=True)
    record_file.write_text(json.dumps(dict(record, key=key, character=path), indent=1))
    head_scale = entry['face']['head_scale']
    return {'character': path, 'replaced': replaced, 'presets': record['presets'], 'push': record['push'],
            'landmarks': len(record['applied']),
            'applied_mean': round(sum(record['applied'].values()) / len(record['applied']), 3) if record['applied'] else None,
            'body': body, 'grooms': grooms, 'face_record': shown_path(record_file), 'problems': problems,
            'never_save': plugin_changes(),
            'head_scale': ('set HeadScale %.2f in MetaHuman Creator (Python cannot) and save the character there' % head_scale
                           if head_scale != 1.0 else 1.0),
            'next': 'conclave:people_preview:%s' % key}


# ---------------------------------------------------------------- the studio: people_preview, people_guides

def refuse_dirty_maps(why):
    """Loading a level drops unsaved edits without asking, so none may be pending (physis_conclave_scenario's rule)."""
    dirty = [item.get_name() for item in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them before %s' % (', '.join(dirty), why))


def open_studio():
    """Opens STUDIO, made the first time: Physis's review lights in white, two grey walls and a platform."""
    world = editor_world()
    if world and package(world) == STUDIO:
        return
    refuse_dirty_maps('the people studio opens')
    if exists(STUDIO):
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(STUDIO):
            raise RuntimeError('could not open ' + STUDIO)
        return
    unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    aim = unreal.Vector(*STUDIO_AIM)
    for label, place, intensity in STUDIO_LIGHTS:
        light = actors().spawn_actor_from_class(unreal.RectLight, unreal.Vector(*place),
                                                unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*place), aim))
        light.set_actor_label(label)
        part = light.get_component_by_class(unreal.RectLightComponent)
        part.set_intensity(intensity)
        part.set_light_color(unreal.LinearColor(*T.PAL.LIGHT_WHITE))
        part.set_editor_property('source_width', STUDIO_LIGHT_SIZE[0])
        part.set_editor_property('source_height', STUDIO_LIGHT_SIZE[1])
    for (label, place, scale), shape in [(wall, CUBE) for wall in STUDIO_WALLS] + [(STUDIO_PLATFORM, CYLINDER)]:
        solid = actors().spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*place))
        solid.set_actor_label(label)
        solid.static_mesh_component.set_static_mesh(unreal.load_asset(shape))
        solid.set_actor_scale3d(unreal.Vector(*scale))
    if not unreal.EditorLoadingAndSavingUtils.save_map(editor_world(), STUDIO):
        raise RuntimeError('could not save ' + STUDIO)


def save_studio():
    """Saves the studio in place once the transient subjects are gone, so a later step finds no unsaved map."""
    if package(editor_world()) == STUDIO:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


def portraits(key, prefix, height):
    """VIEWS of whatever stands at the origin, as <prefix>-<view>.png beside the face record, through a scene capture
    (physis_aaa_tools capture_logs): it renders at once, so every view is written before the next."""
    world = editor_world()
    target = unreal.RenderingLibrary.create_render_target2d(world, PORTRAIT_SIZE, PORTRAIT_SIZE,
                                                            unreal.TextureRenderTargetFormat.RTF_RGBA8)
    camera = actors().spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0))
    part = camera.capture_component2d
    part.set_editor_property('texture_target', target)
    part.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    part.set_editor_property('capture_every_frame', False)
    folder = project_file(cast.FILES['face_record'], key).parent
    folder.mkdir(parents=True, exist_ok=True)
    made = []
    try:
        for view, bearing, distance, aim, fov in VIEWS:
            angle, z = math.radians(bearing), aim * height
            eye = unreal.Vector(distance * math.sin(angle), distance * math.cos(angle), z)
            camera.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, unreal.Vector(0, 0, z)), False, False)
            part.set_editor_property('fov_angle', fov)
            part.capture_scene()
            name = '%s-%s.png' % (prefix, view)
            unreal.RenderingLibrary.export_render_target(world, target, str(folder), name)
            made.append(shown_path(folder / name))
    finally:
        actors().destroy_actor(camera)
    return made


def people_preview(key):
    entry = person(key)
    made = character(key)
    open_studio()
    height = entry['body']['height_cm']
    shots = {}
    with opened(made) as sub:
        # A fresh registration has no preview assembly (the instance's EditorAssemblyOutput is transient), and the
        # preview actor draws no grooms without one: no hair, brows, beard, lashes or fuzz in the portraits the author
        # approves. MetaHuman Creator assembles on opening (MetaHumanCharacterEditorToolkit.cpp), so this does too.
        sub.assemble_for_preview(made)
        # Transient: it references meshes the subsystem owns and must never be saved with a level.
        actor = sub.spawn_meta_human_actor(made, True)
        if actor is None:
            raise RuntimeError('MetaHuman Creator could not spawn a preview of ' + key)
        try:
            actor.set_actor_location(unreal.Vector(0, 0, 0), False, False)
            shots['preview'] = portraits(key, 'preview', height)
        finally:
            actors().destroy_actor(actor)
    look = cast.FILES['look'].format(key=key)
    if exists(look):
        built = actors().spawn_actor_from_class(unreal.load_asset(look).generated_class(), unreal.Vector(0, 0, 0))
        try:
            shots['built'] = portraits(key, 'built', height)
        finally:
            actors().destroy_actor(built)
    save_studio()
    head_scale = entry['face']['head_scale']
    return {'character': package(made), 'studio': STUDIO, 'portraits': shots, 'assembled': exists(look),
            'review': ('the author approves the look; to change HeadScale (MH says %.2f) open %s in MetaHuman Creator, set it '
                       'there and save' % (head_scale, package(made))),
            'next': 'conclave:people_guides:%s' % key}


def export_fbx(mesh, path):
    """A skeletal mesh as binary FBX, as Physis's body guide was exported (physis_character_tools export_body_guide)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    task = unreal.AssetExportTask()
    task.object = mesh
    task.filename = str(path)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = unreal.SkeletalMeshExporterFBX()
    task.options = unreal.FbxExportOption()
    task.options.ascii = False
    if not unreal.Exporter.run_asset_export_task(task):
        raise RuntimeError('FBX export of %s failed' % mesh.get_name())


def people_guides(key):
    person(key)
    made = character(key)
    open_studio()
    files = {}
    with opened(made) as sub:
        actor = sub.spawn_meta_human_actor(made, True)
        if actor is None:
            raise RuntimeError('MetaHuman Creator could not spawn a preview of ' + key)
        try:
            meshes = {part.get_name(): part.get_editor_property('skeletal_mesh_asset')
                      for part in actor.get_components_by_class(unreal.SkeletalMeshComponent)}
            exported = {}
            for name, prefix in (('body_guide', 'body'), ('face_guide', 'face')):
                found = [mesh for label, mesh in sorted(meshes.items()) if label.lower().startswith(prefix) and mesh]
                if not found:
                    raise RuntimeError('the preview has no %s mesh (its components: %s)' % (prefix, ', '.join(sorted(meshes))))
                path = project_file(cast.FILES[name], key)
                export_fbx(found[0], path)
                files[name], exported[name] = shown_path(path), found[0]
            skeleton = exported['body_guide'].skeleton
            files['skeleton'] = package(skeleton) if skeleton else None
        finally:
            actors().destroy_actor(actor)
    save_studio()
    return dict(files, next='quit the editor, then run the Blender costume build for %s (Tools/build_conclave_people.py)' % key)


# ---------------------------------------------------------------- the cloud: people_rig, people_textures

def people_rig(key):
    person(key)
    made = character(key)
    rig = getattr(unreal.MetaHumanRigType, cast.RIG, None)
    if rig is None:
        raise RuntimeError('MetaHumanRigType has no %s (it has %s)' % (cast.RIG, [n for n in dir(unreal.MetaHumanRigType) if n.isupper()]))
    unreal.SystemLibrary.execute_console_command(None, AUTORIG_CACHE)
    with opened(made) as sub:
        registered(sub, made)
        params = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        params.rig_type = rig
        # Blocking keeps HTTP, sign-in and tickers running until the answer is in: Epic's pattern for scripts.
        params.blocking = True
        params.report_progress = False
        sub.request_auto_rigging(made, params)
        game.save(made)
    return {'character': package(made), 'rig_type': cast.RIG, 'sign_in': SIGN_IN,
            'rigged': 'Python cannot read the rig state: people_textures reports whether the character can be assembled',
            'next': 'conclave:people_textures:%s in this same editor session' % key}


def people_textures(key):
    person(key)
    made = character(key)
    with opened(made) as sub:
        wrong = wrong_sources(made)
        if wrong:
            raise RuntimeError('%s asks for texture sources other than %s (%s): people_new sets them; rebuild with '
                               'people_new:%s:%s or set Texture Sources in MetaHuman Creator' % (key, cast.TEXTURE_SOURCES, wrong, key, REPLACE))
        params = unreal.MetaHumanCharacterTextureRequestParams()
        params.blocking = True
        params.report_progress = False
        sub.request_texture_sources(made, params)
        if not made.get_editor_property('has_high_resolution_textures'):
            raise RuntimeError('no texture sources arrived for %s. Requests fail until someone is signed in, and a session '
                               'signs in with its first auto-rig: run people_rig:%s first in this session. %s' % (key, key, SIGN_IN))
        ready = sub.can_build_meta_human(made, True)
        game.save(made)
    problems = [] if ready else ['the textures are in but %s cannot be assembled: the face rig is missing (run people_rig:%s; '
                                 'LogMetaHumanCharacterEditor says why)' % (key, key)]
    return {'character': package(made), 'texture_sources': cast.TEXTURE_SOURCES, 'ready_to_assemble': ready, 'problems': problems,
            'sign_in': SIGN_IN, 'next': 'conclave:people_assemble:%s in a fresh GPU editor' % key if ready else 'conclave:people_rig:%s' % key}


# ---------------------------------------------------------------- people_assemble

def trim_preview_textures():
    """Caps only textures that are never saved (transient ones, the plugin's lookdev in memory)."""
    count = 0
    for texture in unreal.ObjectIterator(unreal.Texture2D):
        if texture.get_path_name().startswith(PREVIEW_TEXTURES):
            texture.set_editor_property('max_texture_size', PREVIEW_TEXTURE_CAP)
            count += 1
    unreal.SystemLibrary.collect_garbage()
    return count


def people_assemble(key):
    entry = person(key)
    made = character(key)
    pipeline = getattr(unreal.MetaHumanDefaultPipelineType, cast.PIPELINE)
    quality = getattr(unreal.MetaHumanQualityLevel, entry['quality'])
    with opened(made) as sub:
        # build_meta_human only logs a refusal, so readiness is checked first.
        if not made.get_editor_property('has_high_resolution_textures'):
            raise RuntimeError('%s has no texture sources: run conclave:people_textures:%s first' % (key, key))
        if not sub.can_build_meta_human(made, True):
            raise RuntimeError('%s cannot be assembled yet, usually for want of its face rig (people_rig:%s); '
                               'LogMetaHumanCharacterEditor says why' % (key, key))
        # Baking runs on the GPU: a realtime viewport competes for the VRAM.
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_viewport_realtime(False)
        trimmed = trim_preview_textures()
        params = unreal.MetaHumanCharacterEditorBuildParameters()
        params.pipeline_type = pipeline
        params.pipeline_quality = quality
        params.absolute_build_path = cast.BUILD_PATH
        params.name_override = key
        params.common_folder_path = cast.COMMON
        params.enable_wardrobe_item_validation = False
        sub.build_meta_human(made, params)
        # Saving renders thumbnails: the baking memory is freed first, or Vulkan runs out.
        unreal.SystemLibrary.collect_garbage()
        for folder in (cast.BUILD_PATH + '/' + key, cast.COMMON):
            unreal.EditorAssetLibrary.save_directory(folder, only_if_is_dirty=True, recursive=True)
        game.save(made)
    look = cast.FILES['look'].format(key=key)
    if not exists(look):
        raise RuntimeError('assembly wrote no %s: LogMetaHumanCharacterEditor says why' % look)
    return {'look': look, 'pipeline': cast.PIPELINE, 'quality': entry['quality'], 'common': cast.COMMON,
            'preview_textures_capped': trimmed, 'never_save': plugin_changes(),
            'next': 'conclave:surface_skeletal (once), then conclave:people_import:%s and people_post:%s; check COMMON and '
                    'Physis against the backup (spike S11)' % (key, key)}


# ---------------------------------------------------------------- people_import

def people_import(key):
    person(key)
    fbx = project_file(cast.FILES['costume_fbx'], key)
    png = project_file(cast.FILES['cloth_mask_png'], key)
    missing = [shown_path(path) for path in (fbx, png) if not path.exists()]
    if missing:
        raise RuntimeError('%s missing: run the Blender costume build for %s (Tools/build_conclave_people.py) first' %
                           (', '.join(missing), key))
    surface = unreal.load_asset(T.MATS + '/M_CNSurface')
    if surface is None or not surface.get_editor_property('used_with_skeletal_mesh'):
        raise RuntimeError('M_CNSurface does not compile for skeletal meshes: run conclave:surface_skeletal first')
    skeleton = unreal.load_asset(cast.SKELETON)
    if skeleton is None:
        raise RuntimeError('%s is missing: an assembly into COMMON copies it there' % cast.SKELETON)
    path = cast.FILES['costume'].format(key=key)
    if exists(path):
        # Importing over Physis's skinned outfit left every section on one material (Tools/build_physis_outfit.py), and
        # the slot names read back fine, so nothing here could tell: a costume is only ever imported fresh.
        raise RuntimeError('%s exists, and importing over it leaves every section on one material: quit the editor, delete '
                           'Content/%s.uasset, start the editor again, then run conclave:people_import:%s and people_post:%s'
                           % (path, path[len('/Game/'):], key, key))
    folder, name = path.rsplit('/', 1)
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = True
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    options.create_physics_asset = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.skeleton = skeleton
    data = options.skeletal_mesh_import_data
    # The costume's colours are its vertex colours (M_CNSurface reads them), and Blender writes its normals.
    data.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)
    data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    data.set_editor_property('import_morph_targets', False)
    task = unreal.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.save = True
    task.options = options
    task.factory = unreal.FbxFactory()
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if mesh is None:
        raise RuntimeError('%s did not import as %s' % (shown_path(fbx), path))
    if package(mesh.skeleton) != cast.SKELETON:
        raise RuntimeError('%s is on %s, not %s' % (path, package(mesh.skeleton), cast.SKELETON))
    slots, unknown, unmade, unskinned = list(mesh.get_editor_property('materials')), [], [], []
    for index, slot in enumerate(slots):
        slot_name = T.slot_name(slot)
        look = T.SLOT_LOOK.get(slot_name)
        material = unreal.load_asset(T.MATS + '/' + look) if look else None
        if look is None:
            unknown.append(slot_name)
        elif material is None:
            unmade.append(look)
        else:
            base = material.get_base_material()
            if not base.get_editor_property('used_with_skeletal_mesh'):
                unskinned.append('%s (%s)' % (slot_name, base.get_name()))
            slots[index] = unreal.SkeletalMaterial(material_interface=material, material_slot_name=slot.material_slot_name,
                                                   uv_channel_data=slot.uv_channel_data)
    if unknown or unmade:
        raise RuntimeError('%s: slots %s are not toolkit.SLOTS, looks %s are not built (conclave:materials)' % (path, unknown, unmade))
    mesh.set_editor_property('materials', slots)
    game.save(mesh)
    mask_path = cast.FILES['cloth_mask'].format(key=key)
    game.import_file(str(png), mask_path.rsplit('/', 1)[0])
    mask = unreal.load_asset(mask_path)
    if mask is None:
        raise RuntimeError('%s did not import as %s' % (shown_path(png), mask_path))
    # A mask, not a colour (Physis's _Mask textures), sampled over the body's UVs, which body textures cap.
    mask.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    mask.set_editor_property('srgb', False)
    mask.set_editor_property('max_texture_size', cast.TEXTURE_CAPS['body'])
    game.save(mask)
    return {'costume': path, 'slots': [T.slot_name(slot) for slot in slots], 'cloth_mask': mask_path,
            'problems': ['slot %s: its master does not compile for skeletal meshes, so it renders as the default material' % item
                         for item in unskinned],
            'next': 'conclave:people_post:%s' % key}


# ---------------------------------------------------------------- people_post, people_verify

def put_costume(parts, body, costume):
    """The costume as a SkeletalMeshComponent under Body (Physis's restore_outfit_component); the Blueprint's
    construction script makes Body's children follow it by leader pose. A rebuild deletes every extra skeletal mesh
    component (MetaHumanDefaultEditorPipelineLegacy.cpp), so this adds it again; an existing one takes the mesh again."""
    existing = parts.get(COSTUME)
    if existing is None:
        from editor_toolset.toolsets.actor import ActorTools
        part, state = ActorTools.add_component(body, unreal.SkeletalMeshComponent.static_class(), COSTUME), 'added'
    else:
        part, state = existing[0], 'updated'
    part.set_skeletal_mesh_asset(costume)
    part.set_leader_pose_component(body)
    return state


def parameter_names(material):
    library = unreal.MaterialEditingLibrary
    return {str(name) for listing in (library.get_scalar_parameter_names, library.get_vector_parameter_names,
                                      library.get_texture_parameter_names) for name in listing(material)}


def mask_skin(key, body):
    """Hangs the body skin under MASK_MASTER through MI_<Key>_Body, a copy of the skin's own parent that carries this
    person's ClothMask, so no skin is drawn under the costume (physis_animation_tools body_mask does it for Physis)."""
    mask_path = cast.FILES['cloth_mask'].format(key=key)
    if not exists(mask_path):
        return 'no cloth mask yet: run conclave:people_import:%s' % key
    master = unreal.load_asset(MASK_MASTER)
    if master is None:
        raise RuntimeError('%s is missing (Physis\'s anim:body_mask makes it)' % MASK_MASTER)
    mesh = body.get_editor_property('skeletal_mesh_asset')
    skins = skin_materials(mesh, key)
    if not skins:
        raise RuntimeError('%s has no body skin material (MI_Body*) of its own' % mesh.get_name())
    library = unreal.MaterialEditingLibrary
    target = BODY_MATERIAL.format(key=key)
    mask = unreal.load_asset(mask_path)
    for skin in skins:
        parent = skin.get_editor_property('parent')
        if package(parent) == target:
            continue
        lacking = parameter_names(parent) - parameter_names(master)
        if lacking:
            raise RuntimeError('%s is not on the master %s was copied from (it has %s too): the masked master needs a copy '
                               'of its own (spike S8)' % (package(parent), MASK_MASTER, sorted(lacking)))
        own = unreal.load_asset(target) if exists(target) else unreal.EditorAssetLibrary.duplicate_asset(package(parent), target)
        if own is None:
            raise RuntimeError('could not make ' + target)
        library.set_material_instance_parent(own, master)
        library.update_material_instance(own)
        game.save(own)
        library.set_material_instance_parent(skin, own)
        library.update_material_instance(skin)
        game.save(skin)
    own = unreal.load_asset(target)
    library.set_material_instance_texture_parameter_value(own, MASK_PARAMETER, mask)
    library.update_material_instance(own)
    game.save(own)
    # The setter can report failure when it worked (physis_outfit_tools material_params), so the value is read back.
    used = library.get_material_instance_texture_parameter_value(own, MASK_PARAMETER)
    if used is None or package(used) != mask_path:
        raise RuntimeError('%s did not take %s as its %s' % (target, mask_path, MASK_PARAMETER))
    return {'skins': [skin.get_name() for skin in skins], 'parent': target, 'mask': mask_path}


def people_post(key):
    entry = person(key)
    blueprint = assembled(key)
    idle = unreal.load_asset(cast.IDLE)
    if idle is None:
        raise RuntimeError(cast.IDLE + ' is missing')
    costume_path = cast.FILES['costume'].format(key=key)
    parts = blueprint_parts(blueprint)
    if 'Body' not in parts:
        raise RuntimeError('%s has no Body component' % package(blueprint))
    report = {'blueprint': package(blueprint)}
    if exists(costume_path):
        report['costume'] = put_costume(parts, parts['Body'][0], unreal.load_asset(costume_path))
        parts = blueprint_parts(blueprint)  # adding a component compiled the Blueprint: read its components again
    else:
        report['costume'] = 'not imported yet: run conclave:people_import:%s, then people_post again' % key
    body = parts['Body'][0]
    start, rate = entry['idle']
    play = unreal.SingleAnimationPlayData()
    for name, value in (('anim_to_play', idle), ('saved_looping', True), ('saved_playing', True), ('saved_position', float(start)),
                        ('saved_play_rate', float(rate))):
        play.set_editor_property(name, value)
    body.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    body.set_editor_property('animation_data', play)
    face = parts['Face'][0] if 'Face' in parts else None
    grooms = [template for template, _, _ in parts.values() if isinstance(template, unreal.GroomComponent)]
    meshes = [part for part in (body, face, parts.get(COSTUME, (None,))[0]) if part is not None]
    for part in (body, face):
        if part is not None:
            # Hidden people (another row of the same speaker, or before their token) cost no animation.
            part.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED)
    for part in meshes + grooms:
        # A talk pauses the game: the person keeps breathing and the head stays on the body (BP_NPC switches only itself).
        part.set_tickable_when_paused(True)
        part.set_editor_property('visible_in_ray_tracing', IN_RAY_TRACING)
    for groom in grooms:
        # Per component, never the global hair cvars, which Physis shares.
        groom.set_editor_property('use_cards', True)
        settings = groom.get_editor_property('simulation_settings')
        settings.set_editor_property('override_settings', True)
        solver = settings.get_editor_property('solver_settings')
        solver.set_editor_property('enable_simulation', False)
        settings.set_editor_property('solver_settings', solver)
        groom.set_editor_property('simulation_settings', settings)
    component = next((template for template, _, _ in parts.values() if 'MetaHumanComponent' in template.get_class().get_name()), None)
    if component is not None:
        for flag in MH_COMPONENT_OFF:
            component.set_editor_property(flag, False)
    report['mask'] = mask_skin(key, body)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    game.save(blueprint)
    capped = []
    for path, texture, cap in capped_textures(key):
        current = texture.get_editor_property('max_texture_size')
        if current == 0 or current > cap:
            texture.set_editor_property('max_texture_size', cap)
            game.save(texture)
            capped.append('%s %d' % (path.rsplit('/', 1)[-1].split('.')[0], cap))
    report.update({'idle': [start, rate], 'grooms': len(grooms), 'metahuman_component': component is not None,
                   'textures_capped': capped, 'next': 'conclave:people_verify:%s' % key})
    return report


def tickable(part):
    return part.get_editor_property('primary_component_tick').get_editor_property('tick_even_when_paused')


def check(key):
    """The post-pass on the assembled Blueprint, as rows of what is wrong (PEOPLE_DESIGN.md 3.5)."""
    entry = person(key)
    blueprint = assembled(key)
    parts = blueprint_parts(blueprint)
    rows = []
    if 'Body' not in parts:
        return ['no Body component']
    body, body_handle, _ = parts['Body']
    mesh = body.get_editor_property('skeletal_mesh_asset')
    if mesh is None or mesh.skeleton is None or package(mesh.skeleton) != cast.SKELETON:
        rows.append('Body is not on %s' % cast.SKELETON)
    play = body.get_editor_property('animation_data')
    anim = play.get_editor_property('anim_to_play')
    start, rate = entry['idle']
    if body.get_editor_property('animation_mode') != unreal.AnimationMode.ANIMATION_SINGLE_NODE or anim is None or package(anim) != cast.IDLE:
        rows.append('Body does not play %s by itself' % cast.IDLE)
    elif (abs(play.get_editor_property('saved_position') - start) > 1e-3 or abs(play.get_editor_property('saved_play_rate') - rate) > 1e-3
          or not play.get_editor_property('saved_looping')):
        rows.append('Body\'s idle is not a loop from %.2f s at %.2f' % (start, rate))
    face = parts['Face'][0] if 'Face' in parts else None
    if face is None:
        rows.append('no Face component')
    for name, part in (('Body', body), ('Face', face)):
        if part is not None and part.get_editor_property('visibility_based_anim_tick_option') != \
                unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED:
            rows.append('%s ticks its pose when not rendered' % name)
    grooms = [(name, template) for name, (template, _, _) in parts.items() if isinstance(template, unreal.GroomComponent)]
    costume = parts.get(COSTUME)
    meshes = [(name, part) for name, part in (('Body', body), ('Face', face), (COSTUME, costume[0] if costume else None)) if part]
    for name, part in meshes + grooms:
        try:
            if not tickable(part):
                rows.append('%s stops while the game is paused' % name)
        except Exception as error:
            rows.append('%s tick-when-paused not readable (%s)' % (name, error))
        if part.get_editor_property('visible_in_ray_tracing') != IN_RAY_TRACING:
            rows.append('%s is %sin ray tracing' % (name, '' if not IN_RAY_TRACING else 'not '))
    for name, groom in grooms:
        settings = groom.get_editor_property('simulation_settings')
        if not groom.get_editor_property('use_cards'):
            rows.append('%s draws strands, not cards' % name)
        if not settings.get_editor_property('override_settings') or settings.get_editor_property('solver_settings').get_editor_property('enable_simulation'):
            rows.append('%s may simulate' % name)
    component = next((template for template, _, _ in parts.values() if 'MetaHumanComponent' in template.get_class().get_name()), None)
    if component is None:
        rows.append('no MetaHuman component')
    else:
        rows += ['MetaHuman component %s is on' % flag for flag in MH_COMPONENT_OFF if component.get_editor_property(flag)]
    costume_path = cast.FILES['costume'].format(key=key)
    if costume is None:
        rows.append('no %s component (people_import, then people_post)' % COSTUME)
    else:
        worn = costume[0].get_editor_property('skeletal_mesh_asset')
        if worn is None or package(worn) != costume_path:
            rows.append('%s wears %s, not %s' % (COSTUME, package(worn) if worn else 'nothing', costume_path))
        if not unreal.SubobjectDataBlueprintFunctionLibrary.is_attached_to(costume[2], body_handle):
            rows.append('%s is not under Body' % COSTUME)
    target = BODY_MATERIAL.format(key=key)
    skins = skin_materials(mesh, key) if mesh else []
    if not skins:
        rows.append('no body skin material of its own')
    for skin in skins:
        parent = skin.get_editor_property('parent')
        if package(parent) != target or package(parent.get_editor_property('parent')) != MASK_MASTER:
            rows.append('%s is not under %s and %s' % (skin.get_name(), target, MASK_MASTER))
    if exists(target):
        mask = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(unreal.load_asset(target), MASK_PARAMETER)
        if mask is None or package(mask) != cast.FILES['cloth_mask'].format(key=key):
            rows.append('%s has no %s of %s' % (target, MASK_PARAMETER, key))
    for path, texture, cap in capped_textures(key):
        size = texture.get_editor_property('max_texture_size')
        if size == 0 or size > cap:
            rows.append('%s may be larger than %d' % (path.rsplit('/', 1)[-1].split('.')[0], cap))
    return rows


def people_verify(key=None):
    """One person's post-pass checks, or every assembled person's without a key; empty problems pass."""
    keys = [key] if key else [name for name, entry in cast.MH.items() if not entry['pending'] and exists(cast.FILES['look'].format(key=name))]
    found = {name: check(name) for name in keys}
    return {'checked': keys, 'problems': {name: rows for name, rows in found.items() if rows},
            'passed': not any(found.values())}


# ---------------------------------------------------------------- npc_look

def npc_look():
    """BP_NPC gains Look (conclave:blueprints never remakes BP_NPC: conclave_logic.py's graphs live in it), or an existing
    Look takes physis_conclave_tools' settings again."""
    path = game.BLUEPRINTS + '/BP_NPC'
    if not exists(path):
        raise RuntimeError('%s is missing: run conclave:blueprints first' % path)
    blueprint = unreal.load_asset(path)
    existing = blueprint_parts(blueprint).get(T.LOOK)
    if existing is None:
        T.add_look(blueprint)
        state = 'added'
    elif not isinstance(existing[0], unreal.ChildActorComponent):
        raise RuntimeError('BP_NPC already has a %s named %s' % (existing[0].get_class().get_name(), T.LOOK))
    else:
        T.fit_look(existing[0])
        state = 'kept'
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    game.save(blueprint)
    return {'blueprint': path, T.LOOK: state, 'yaw': T.LOOK_YAW,
            'next': 'python3 Tools/blueprint_logic/conclave_logic.py npc (read the graphs back), then conclave:scenario'}


# ---------------------------------------------------------------- dispatcher

KEYED = {'people_new': people_new, 'people_preview': people_preview, 'people_guides': people_guides, 'people_rig': people_rig,
         'people_textures': people_textures, 'people_assemble': people_assemble, 'people_import': people_import,
         'people_post': people_post, 'people_verify': people_verify}


def execute(operation):
    """conclave:<op>[:<Key>[:replace]] (physis_conclave_tools.execute hands over everything after 'conclave:')."""
    name, _, rest = operation.partition(':')
    key, _, option = rest.partition(':')
    if name == 'npc_look':
        if rest:
            raise ValueError('conclave:npc_look takes no key')
        return npc_look()
    if name not in KEYED:
        raise ValueError('unknown conclave people operation %s (%s, npc_look)' % (name, ', '.join(KEYED)))
    if option and (name, option) != ('people_new', REPLACE):
        raise ValueError('conclave:%s takes no option %r' % (name, option))
    if not key:
        if name == 'people_verify':
            return people_verify()
        raise ValueError('conclave:%s:<Key> needs a MetaHuman: %s' % (name, ', '.join(k for k, e in cast.MH.items() if not e['pending'])))
    return people_new(key, option == REPLACE) if name == 'people_new' else KEYED[name](key)
