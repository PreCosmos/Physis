"""Earth's people who stood in as the Conclave's MetaHumans, built as their own (the author, 2026-11-19: "Do we have
Metahumans or normal NPCs in General in Halcyon, hesper and Morrow? If not, implement them."):

    Commodore Hollis Marr   Halcyon   until now Rhea Sato's figure (a 26-year-old in a field hat)
    Edda Holt               Morrow    until now Old Wen's
    Corin Vell              Morrow    until now Marek Duran's
    Warden Maren Holt       Morrow    until now Doctor Ama Okafor's

Halcyon's Kairos and Petra are the Conclave's MetaHumans of the same people, and Hesper's people are First Ones, built
figures by the author's rule for Arche (GAME_ROADMAP.md "Level 5", the First Ones' native form): neither changes.

They are built by the Conclave's people pipeline (physis_conclave_people.py; the design is Tools/conclave/PEOPLE_DESIGN.md)
as the Grove's Director Voss was (physis_grove_people.py): physis_conclave_cast.MH is checked against the Conclave's
lore, so they are not written into it. install() adds them to the loaded tables for one Python session (the editor's,
or Blender's for their costumes), and every Conclave operation then takes their keys:

    editor:   earth:people_new:<Key>, earth:people_preview:<Key>, earth:people_guides:<Key>, then (signed in to Epic)
              earth:people_rig:<Key>, earth:people_textures:<Key>, earth:people_assemble:<Key>, then
              earth:people_import:<Key>, earth:people_post:<Key>, earth:bind:<Key> (the assembly leaves the hair
              unbound: see bind()), earth:people_verify:<Key>; last earth:wear, which shows each built look on the
              people placed in L_Halcyon and L_Morrow. Runner: Saved/Earth/run/op.sh OP [OP...] (results in
              Saved/Earth/run/<op>.json). Assemble each in a fresh editor: the 8 GB card ran out once when one
              session did several people's heavy steps.
    Blender:  Tools/build_earth_people.py -- <Key> [...] (their costumes on their guides, between people_guides and
              people_import); python3 Tools/build_earth_people.py --test builds them offline on stand-in guides

Their assets land beside the Conclave's and Voss's (the pipeline's folders are fixed): the character
/Game/Characters/Conclave/MHC_<Key>, the assembled look /Game/Conclave/People/<Key>/BP_<Key>. Their shared MetaHuman
assets go to Voss's /Game/MetaHumans/CommonGrove: a 5.9 assembly into the 5.8 /Game/MetaHumans/Common asks to
overwrite Physis's own assets, and unattended that question is answered Cancel.

Who they are. The levels' lore gives their parts, not their looks; these are Proposed, for the author's review:
  Marr   the Bastion's commander, about fifty-seven: sealed in with the Held Sea for weeks, upright, the jaw set. Deep
         brown skin, dark eyes, cropped hair going grey. The Just's graphite in its naval cut: a black officer's coat
         with brass buttons down the front and at the cuffs, a white shirt collar.
  Edda   Maren's mother, Tam's grandmother, seventy-four (her lines say so); widowed twenty years. Small,
         soft-faced, a smile held in the corners of the mouth. Fair skin reddened by the mountain wind, faded blue-grey eyes, white hair in a
         braided crown. A slate wool skirt, a cream blouse and a deep red knitted shawl: the one warm colour in a
         cold valley, as Sit With is its one warm light.
  Corin  the dam's engineer, the Just, about forty-four: tall, tired, practical. A short dark beard, hazel eyes. An
         ochre oilskin over charcoal, knee boots for the spillway.
  Maren  the Hold's Warden, in her forties: her mother's face, longer and leaner, drawn by grief. Her mother's
         blue-grey eyes; dark hair going grey, tied low under the cap. As her Stilled figure wears them
         (SM_OP_Stilled7, Tools/morrow_meshes/figures.py): the Just's olive field greatcoat, long, with brass buttons,
         and an officer's peaked cap; a grey jumper under the coat, knee boots.
Edda and Maren share two face presets (Grace and Celeste, in different measure) so the daughter reads as her
mother's.

costume entries may carry two keys the Conclave's do not, read only by Tools/build_earth_people.py: 'recolour'
{palette name the garment's builder uses: palette name it wears here}, and 'reslot' {material slot: slot} (the
oilskin's light-blue body is drawn in the CN_Blue slot; ochre cloth belongs in CN_Cloth). A recoloured garment's
'colours' are the colours it ends up in. That build makes three garments of its own: SM_EP_G_OfficerCoat, the
Conclave doctor's coat (SM_CP_G_CoatWhite) without her pens and stethoscope, its buttons brass; SM_EP_G_GreatcoatSkirt,
her coat's skirt to mid-calf; SM_EP_G_OfficerCap, a peaked cap. OLIVE (EXTRA_PALETTE) is the Just's field olive, the
drab of Maren's Stilled figure brought just inside the Conclave palette's green family, which the build's checks keep.
"""
import physis_conclave_cast as cast

KEYS = ('Marr', 'Edda', 'Corin', 'Maren')
# Linear RGBA, as palette.PALETTE: sRGB (.38, .41, .30), hue 76 degrees, so palette.family() reads it as green.
EXTRA_PALETTE = {'OLIVE': (.119, .140, .073, 1.0)}
COMMON = '/Game/MetaHumans/CommonGrove'
GROOMS = cast.GROOMS
# The levels' people shown through each look: level, then (lore module, MH key) per person. A row of that lore whose
# mesh is the key and whose kind is 'human' wears it.
LEVELS = {'/Game/Levels/L_Halcyon': ('physis_halcyon_lore', ('Marr',)),
          '/Game/Levels/L_Morrow': ('physis_morrow_lore', ('Edda', 'Corin', 'Maren'))}
# Actors each level must still hold before earth:wear saves it: a failed Blueprint write once took 'Halcyon Director'
# out of L_Halcyon, and the next save lost it (the Halcyon session, 2026-11-18).
REQUIRED = {'/Game/Levels/L_Halcyon': ('Halcyon Director', 'Awakening Director', 'Swim Director'),
            '/Game/Levels/L_Morrow': ('Morrow Director', 'Awakening Director', 'Swim Director')}
# Whose figure each stood in as until its own was built (what earth:wear replaces).
STAND_INS = {'Marr': 'Rhea', 'Edda': 'Wen', 'Corin': 'Marek', 'Maren': 'Ama'}

EARTH = {
    'Marr': {
        'name': 'Commodore Hollis Marr', 'rows': ('Marr',), 'age': 57, 'pending': None,
        'colouring': {'skin': 'deep brown, cool', 'eyes': 'dark brown', 'hair': 'black going grey, cropped close'},
        'quality': 'HIGH',
        'face': {'presets': (('Zuri', .6), ('Grace', .4)), 'push': 1.0, 'head_scale': 1.0,
                 # A long, firm face: the jaw squared, the brows low and level, the mouth set, the chin forward.
                 'landmarks': ((1, (-.1, 0, 0)), (28, (.1, 0, 0)), (25, (0, 0, -.06)), (78, (0, 0, -.06)), (48, (0, 0, -.04)),
                               (32, (0, 0, -.04)), (62, (0, .08, 0)))},
        'body': {'height_cm': 172.0, 'masculine_feminine': .82, 'fat': .30, 'muscularity': .45, 'measurements': {}},
        # Variant 62 (native tone .69, wrinkles medium): 55 (wrinkles high) aged her past seventy in the first portraits.
        'skin': {'u': .72, 'v': .48, 'face_texture_index': 62, 'body_texture_index': 5, 'roughness': 1.08},
        'freckles': None,
        'accents': {},
        'eyes': {'primary': (.90, .18), 'secondary': (.94, .10), 'pattern': 'IRIS002', 'set': {}},
        'lashes': {'type': 'SHORT_FINE', 'melanin': 1.0, 'redness': .05},
        'makeup': {},
        'grooms': {
            'Hair': (GROOMS + '/Hair/WI_Hair_S_Coil', {'Melanin': .9, 'Redness': .05, 'Whiteness': .55}),
            'Eyebrows': (GROOMS + '/Eyebrows/WI_Eyebrows_M_Thin', {'Melanin': .95, 'Redness': .05, 'Whiteness': .3}),
            'Peachfuzz': (GROOMS + '/Peachfuzz/WI_Peachfuzz_M_Thin', {'Melanin': .8, 'Redness': .05}),
        },
        'costume': (
            {'piece': 'coat_skirt', 'port': 'SM_CP_G_CoatSkirtWhite', 'recolour': {'WHITE_COOL': 'BLACK', 'WHITE_PURE': 'GOLD_DEEP'},
             'colours': ('BLACK', 'GOLD_DEEP')},
            {'piece': 'coat', 'port': 'SM_EP_G_OfficerCoat', 'recolour': {'WHITE_COOL': 'BLACK', 'WHITE_PURE': 'GOLD_DEEP'},
             'colours': ('BLACK', 'GOLD_DEEP')},
            # Black cuffs with two brass buttons each (a 'GOLD' second colour: a gold band read as gloves at a distance).
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('BLACK', 'GOLD')},
            {'piece': 'shirt', 'make': 'collar_cuffs', 'cut': 'shirt', 'colours': ('WHITE',)},
            {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('BLACK',)},
            {'piece': 'boots', 'make': 'boots', 'cut': 'ankle', 'colours': ('BLACK',)},
        ),
        'idle': (4.1, .9),
    },
    'Edda': {
        'name': 'Edda Holt', 'rows': ('Edda',), 'age': 74, 'pending': None,
        'colouring': {'skin': 'fair, weathered, wind-reddened cheeks', 'eyes': 'faded blue-grey, a pale ring', 'hair': 'white'},
        'quality': 'HIGH',
        'face': {'presets': (('Grace', .55), ('Celeste', .45)), 'push': 1.0, 'head_scale': 1.0,
                 # A soft, broad face: fuller lower cheeks, a smile held in the mouth's corners, hooded lids, a round chin.
                 'landmarks': ((2, (-.12, 0, 0)), (29, (.12, 0, 0)), (48, (0, 0, .05)), (32, (0, 0, .05)), (20, (0, 0, -.05)),
                               (44, (0, 0, -.05)), (62, (0, .05, -.04)))},
        'body': {'height_cm': 157.0, 'masculine_feminine': .95, 'fat': .45, 'muscularity': .2, 'measurements': {}},
        'skin': {'u': .24, 'v': .44, 'face_texture_index': 20, 'body_texture_index': 7, 'roughness': 1.12},
        'freckles': None,
        'accents': {'cheeks': {'redness': .55}, 'nose': {'redness': .45}},
        # Colour fades with age; a soft grey limbal ring stands for the pale arcus of the old (as Old Wen's).
        'eyes': {'primary': (.16, .42), 'secondary': (.22, .34), 'pattern': 'IRIS006',
                 'set': {'iris.global_saturation': .9, 'iris.limbal_ring_color': (.6, .6, .6)}},
        'lashes': {'type': 'SHORT_SPARSE', 'melanin': .4, 'redness': .05, 'salt_and_pepper': .8},
        'makeup': {},
        'grooms': {
            'Hair': (GROOMS + '/Hair/WI_Hair_S_UpdoBraids', {'Melanin': .35, 'Redness': .05, 'Whiteness': 1.0}),
            'Eyebrows': (GROOMS + '/Eyebrows/WI_Eyebrows_M_Thin', {'Melanin': .45, 'Redness': .05, 'Whiteness': .85}),
            'Peachfuzz': (GROOMS + '/Peachfuzz/WI_Peachfuzz_M_Thin', {'Melanin': .3, 'Redness': .05, 'Whiteness': 1.0}),
        },
        'costume': (
            {'piece': 'skirt', 'port': 'SM_CP_G_RobeSkirt', 'recolour': {'IVORY': 'SLATE'}, 'colours': ('SLATE', 'CHARCOAL')},
            {'piece': 'blouse', 'port': 'SM_CP_G_BlouseShawl', 'recolour': {'BLUE': 'IVORY', 'WHITE': 'RED_DEEP'},
             'colours': ('IVORY', 'RED_DEEP')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('IVORY',)},
            {'piece': 'boots', 'make': 'boots', 'cut': 'ankle', 'colours': ('BLACK',)},
        ),
        'idle': (1.6, .82),
    },
    'Corin': {
        'name': 'Corin Vell', 'rows': ('Corin',), 'age': 44, 'pending': None,
        'colouring': {'skin': 'light-medium, wind-burned', 'eyes': 'hazel', 'hair': 'dark brown, a short beard'},
        'quality': 'HIGH',
        'face': {'presets': (('Kelvin', .55), ('Bruce', .45)), 'push': 1.0, 'head_scale': 1.0,
                 # A strong nose a little broad at the wings, the brow creased, a firm jaw.
                 'landmarks': ((45, (.08, 0, 0)), (67, (-.08, 0, 0)), (64, (0, .06, 0)), (24, (0, 0, -.05)), (77, (0, 0, -.05)),
                               (1, (-.08, 0, 0)), (28, (.08, 0, 0)))},
        'body': {'height_cm': 181.0, 'masculine_feminine': .05, 'fat': .32, 'muscularity': .55, 'measurements': {}},
        'skin': {'u': .44, 'v': .52, 'face_texture_index': 137, 'body_texture_index': 2, 'roughness': 1.06},
        'freckles': None,
        'accents': {'cheeks': {'redness': .5}},
        'eyes': {'primary': (.52, .42), 'secondary': (.64, .30), 'pattern': 'IRIS003', 'set': {}},
        'lashes': {'type': 'SHORT_SPARSE', 'melanin': .85, 'redness': .1},
        'makeup': {},
        'grooms': {
            'Hair': (GROOMS + '/Hair/WI_Hair_S_Casual', {'Melanin': .85, 'Redness': .15, 'Whiteness': .08}),
            'Beard': (GROOMS + '/Beards/WI_Beard_S_Full', {'Melanin': .85, 'Redness': .15, 'Whiteness': .1}),
            'Mustache': (GROOMS + '/Mustaches/WI_Mustache_S_Full', {'Melanin': .85, 'Redness': .15, 'Whiteness': .1}),
            'Eyebrows': (GROOMS + '/Eyebrows/WI_Eyebrows_M_Dense', {'Melanin': .85, 'Redness': .15}),
            'Peachfuzz': (GROOMS + '/Peachfuzz/WI_Peachfuzz_M_Thin', {'Melanin': .7, 'Redness': .15}),
        },
        'costume': (
            {'piece': 'coat_skirt', 'port': 'SM_CP_G_OilskinSkirt', 'recolour': {'BLUE': 'GOLD_DEEP'}, 'reslot': {'CN_Blue': 'CN_Cloth'},
             'colours': ('GOLD_DEEP', 'BLACK')},
            {'piece': 'coat', 'port': 'SM_CP_G_Oilskin', 'recolour': {'BLUE': 'GOLD_DEEP'}, 'reslot': {'CN_Blue': 'CN_Cloth'},
             'colours': ('GOLD_DEEP', 'BLACK', 'CHARCOAL')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('GOLD_DEEP', 'BLACK')},
            {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('CHARCOAL',)},
            {'piece': 'boots', 'make': 'boots', 'cut': 'knee', 'colours': ('BLACK',)},
        ),
        'idle': (3.7, 1.02),
    },
    'Maren': {
        'name': 'Warden Maren Holt', 'rows': ('Maren',), 'age': 46, 'pending': None,
        'colouring': {'skin': 'fair, drawn', 'eyes': 'blue-grey, her mother\'s', 'hair': 'dark brown going grey, tied low'},
        'quality': 'HIGH',
        'face': {'presets': (('Celeste', .55), ('Grace', .25), ('Vivian', .2)), 'push': 1.0, 'head_scale': 1.0,
                 # Her mother's face, longer and leaner: hollow lower cheeks, the brows' heads drawn down, the mouth
                 # held shut, the chin lower.
                 'landmarks': ((2, (.1, 0, 0)), (29, (-.1, 0, 0)), (24, (0, 0, -.05)), (77, (0, 0, -.05)), (48, (0, 0, -.05)),
                               (32, (0, 0, -.05)), (62, (0, 0, -.1)))},
        'body': {'height_cm': 171.0, 'masculine_feminine': .86, 'fat': .22, 'muscularity': .42, 'measurements': {}},
        'skin': {'u': .27, 'v': .36, 'face_texture_index': 76, 'body_texture_index': 1, 'roughness': 1.08},
        'freckles': None,
        'accents': {},
        'eyes': {'primary': (.18, .38), 'secondary': (.24, .30), 'pattern': 'IRIS006', 'set': {}},
        'lashes': {'type': 'SHORT_FINE', 'melanin': .7, 'redness': .1},
        'makeup': {},
        'grooms': {
            # Tied low at the nape, under the cap (the costume grows the cap by this groom's depth).
            'Hair': (GROOMS + '/Hair/WI_Hair_S_LowPonytail', {'Melanin': .75, 'Redness': .12, 'Whiteness': .25}),
            'Eyebrows': (GROOMS + '/Eyebrows/WI_Eyebrows_M_Swept', {'Melanin': .75, 'Redness': .12, 'Whiteness': .15}),
            'Peachfuzz': (GROOMS + '/Peachfuzz/WI_Peachfuzz_M_Thin', {'Melanin': .55, 'Redness': .1}),
        },
        'costume': (
            {'piece': 'coat_skirt', 'port': 'SM_EP_G_GreatcoatSkirt', 'recolour': {'WHITE_COOL': 'OLIVE', 'WHITE_PURE': 'GOLD_DEEP'},
             'colours': ('OLIVE', 'GOLD_DEEP')},
            {'piece': 'coat', 'port': 'SM_EP_G_OfficerCoat', 'recolour': {'WHITE_COOL': 'OLIVE', 'WHITE_PURE': 'GOLD_DEEP'},
             'colours': ('OLIVE', 'GOLD_DEEP')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('OLIVE', 'GOLD')},
            {'piece': 'top', 'make': 'undertop', 'cut': 'crew', 'colours': ('ASH',)},
            {'piece': 'cap', 'port': 'SM_EP_G_OfficerCap', 'recolour': {'WHITE_COOL': 'OLIVE', 'WHITE_PURE': 'GOLD'},
             'colours': ('OLIVE', 'BLACK', 'GOLD'), 'bone': 'head'},
            {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('CHARCOAL',)},
            {'piece': 'boots', 'make': 'boots', 'cut': 'knee', 'colours': ('BLACK',)},
        ),
        'idle': (5.2, .94),
    },
}

# The Mannequin row the costume build measures each stand-in guide from and takes the ported garments' patterns from
# (physis_grove_people.ROW): a woman's garments were modelled on Quinn, a man's on Manny.
ROWS = {
    'Marr': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Obsidian', 'lower': 'SM_CP_G_CoatSkirtWhite', 'upper': 'SM_CP_G_CoatWhite',
             'head': None, 'shape': None},
    'Edda': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_RobeSkirt', 'upper': 'SM_CP_G_BlouseShawl',
             'head': None, 'shape': None},
    'Corin': {'body': 'Manny', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_OilskinSkirt', 'upper': 'SM_CP_G_Oilskin',
              'head': None, 'shape': None},
    'Maren': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_CoatSkirtWhite', 'upper': 'SM_CP_G_CoatWhite',
              'head': 'SM_CP_G_FieldHat', 'shape': None},
}


def install():
    """Adds Earth's people to the loaded Conclave tables (not to the file). Safe to call again. Returns their keys."""
    for key in KEYS:
        cast.MH[key] = EARTH[key]
        cast.CAST_MANNEQUIN[key] = ROWS[key]
    return KEYS


def look(key):
    """The assembled Blueprint's path for a key (what earth:wear shows)."""
    return cast.FILES['look'].format(key=key)


def execute(operation):
    """earth:<people operation>:<Key>[:replace] runs the Conclave's operation of that name on one of Earth's people;
    earth:wear shows every built look in the levels."""
    if operation == 'wear':
        return wear()
    if operation.startswith('bind:'):
        install()
        return bind(operation.split(':', 1)[1])
    install()
    import importlib
    import physis_conclave_people as people
    importlib.reload(people)
    install()
    name, _, rest = operation.partition(':')
    key, _, option = rest.partition(':')
    if name not in people.KEYED:
        raise ValueError('unknown people operation %r (%s)' % (name, ', '.join(sorted(people.KEYED))))
    if name == 'people_verify' and not key:
        return {k: execute('people_verify:' + k) for k in KEYS if people.exists(look(k))}
    if key not in KEYS:
        raise ValueError('%r is not one of Earth\'s people (%s)' % (key, ', '.join(KEYS)))
    kept = cast.COMMON, cast.SKELETON
    cast.COMMON = COMMON
    cast.SKELETON = cast.SKELETON.replace(kept[0], COMMON)
    try:
        if option:
            return people.KEYED[name](key, option == people.REPLACE)
        return people.KEYED[name](key)
    finally:
        cast.COMMON, cast.SKELETON = kept


def bind(key):
    """earth:bind:<Key>: gives each groom component of the assembled Blueprint the binding its assembly made for it. On
    2026-11-19 the 5.9 assembly wrote every <Groom>_Binding (to this person's face mesh) but left the components'
    binding empty, so the hair hung where an upright head would be while the face followed the idle (Voss's, built
    2026-11-16, has them). Run after people_post; safe to run again."""
    import unreal
    import physis_conclave_people as people
    blueprint = unreal.load_asset(look(key))
    if blueprint is None:
        raise RuntimeError(look(key) + ' is not assembled')
    folder = look(key).rsplit('/', 1)[0] + '/Grooms'
    bindings = {}
    for path in unreal.EditorAssetLibrary.list_assets(folder, recursive=False):
        asset = unreal.load_asset(path)
        if isinstance(asset, unreal.GroomBindingAsset):
            groom = asset.get_editor_property('groom')
            if groom is not None:
                bindings[groom.get_path_name()] = asset
    def unbound():
        """{component: the binding it should have} for every groom component that lacks it."""
        out = {}
        for name, (template, _, _) in people.blueprint_parts(blueprint).items():
            if not isinstance(template, unreal.GroomComponent) or template.get_editor_property('groom_asset') is None:
                continue
            want = bindings.get(template.get_editor_property('groom_asset').get_path_name())
            if want is not None and template.get_editor_property('binding_asset') != want:
                out[name] = (template, want)
        return out

    # The first write after the Blueprint is loaded did not always survive its compile and save (Edda and Corin,
    # 2026-11-19; a second run kept them), so it is checked from the Blueprint again and repeated.
    report = {'bound': {}, 'tries': 0}
    for _ in range(3):
        missing = unbound()
        if not missing:
            break
        report['tries'] += 1
        for name, (template, want) in missing.items():
            template.set_editor_property('binding_asset', want)
            report['bound'][name] = want.get_name()
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        people.game.save(blueprint)
    report['still_unbound'] = sorted(unbound())
    report['no_binding_made'] = sorted(name for name, (template, _, _) in people.blueprint_parts(blueprint).items()
                                       if isinstance(template, unreal.GroomComponent) and template.get_editor_property('groom_asset')
                                       and template.get_editor_property('groom_asset').get_path_name() not in bindings)
    return report


def wear():
    """Shows each of Earth's built looks on its people in L_Halcyon and L_Morrow (BP_NPC's Look), and saves each level
    it changed. A person whose look is not assembled yet keeps the stand-in. Refuses a level with unsaved changes, as
    the scenarios do; the editor is left in the level it was in."""
    import importlib
    import unreal
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    dirty = [item.get_name() for item in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError('unsaved changes in %s: save or discard them first' % ', '.join(dirty))
    world = unreal.EditorLevelLibrary.get_editor_world()
    start = world.get_path_name().split('.')[0] if world else None
    report = {}
    for level, (lore_name, keys) in LEVELS.items():
        lore = importlib.import_module(lore_name)
        built = {key: unreal.load_asset(look(key)) for key in keys if unreal.EditorAssetLibrary.does_asset_exist(look(key))}
        if not built:
            report[level] = 'nothing assembled yet'
            continue
        rows = {row[0]: row[2] for row in lore.PEOPLE if row[4] == 'human' and row[2] in built}
        if not levels.load_level(level):
            raise RuntimeError('could not open ' + level)
        everyone = actors.get_all_level_actors()
        labels = {actor.get_actor_label() for actor in everyone}
        lacking = [label for label in REQUIRED[level] if label not in labels]
        if lacking:
            raise RuntimeError('%s lacks %s: not saved; put it back (its level:start op) first' % (level, ', '.join(lacking)))
        changed = []
        for actor in everyone:
            if not actor.get_class().get_name().startswith('BP_NPC'):
                continue
            try:
                row = str(actor.get_editor_property('Key'))
            except Exception:
                continue
            if row not in rows:
                continue
            view = next((c for c in actor.get_components_by_class(unreal.ChildActorComponent) if c.get_name() == 'Look'), None)
            if view is None:
                raise RuntimeError('%s has no Look component' % actor.get_actor_label())
            view.set_relative_scale3d(unreal.Vector(1, 1, 1))
            view.set_child_actor_class(built[rows[row]].generated_class())
            changed.append('%s: %s' % (row, built[rows[row]].get_name()))
        missing = sorted(set(rows) - {item.split(':')[0] for item in changed})
        if len(actors.get_all_level_actors()) != len(everyone):
            raise RuntimeError('%s: the actor count changed while its looks were set: not saved' % level)
        if changed:
            unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False)
        report[level] = {'shown': changed, 'rows_not_placed': missing}
    if start and start != (unreal.EditorLevelLibrary.get_editor_world().get_path_name().split('.')[0]):
        levels.load_level(start)
    return report
