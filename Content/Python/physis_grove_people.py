"""Director Maren Voss, the Wounded Grove's one MetaHuman (Tools/grove/README.md, author rule 3).

She is built by the Conclave's people pipeline (physis_conclave_people.py; the design is Tools/conclave/PEOPLE_DESIGN.md),
which reads its people from physis_conclave_cast.MH. That table is checked against the Conclave's own lore, so Voss is
not written into it: install() adds her to the loaded tables for the length of one Python session (the editor's, or
Blender's for her costume), and every Conclave operation then takes the key 'Voss':

    editor:   grove:voss:people_new, grove:voss:people_preview, grove:voss:people_guides, then (signed in to Epic)
              grove:voss:people_rig, grove:voss:people_textures, grove:voss:people_assemble, then
              grove:voss:people_import, grove:voss:people_post, grove:voss:people_verify
    Blender:  Tools/build_grove_people.py (her costume on her guides, between people_guides and people_import)

Her assets land beside the Conclave's (the pipeline's folders are fixed): the character /Game/Characters/Conclave/MHC_Voss,
the assembled look /Game/Conclave/People/Voss/BP_Voss, which physis_grove_scenario.VOSS_LOOKS shows at the bunker.

Who she is (physis_grove_lore): the Array's director for nineteen years, about fifty-eight, not cruel, worn by the
watch she has kept. Light olive skin gone sallow indoors, grey eyes, iron-grey hair pulled back, deep lines. She wears
the Just's field dress as the Conclave's doctor wears her coat, in graphite instead of white, with the one amber
(gold) stripe of the Just's livery at collar and cuff.
"""
import physis_conclave_cast as cast

KEY = 'Voss'
VOSS = {
    'name': 'Director Maren Voss', 'rows': (KEY,), 'age': 58, 'pending': None,
    'colouring': {'skin': 'light olive, sallow', 'eyes': 'grey', 'hair': 'iron grey'},
    'quality': 'HIGH',
    'face': {'presets': (('Grace', .55), ('Jelena', .45)), 'push': 1.0, 'head_scale': 1.0,
             # A longer, drawn face: brows low and level, the mouth set.
             'landmarks': ((20, (0, 0, -.08)), (44, (0, 0, -.08)), (62, (0, .05, -.1)))},
    'body': {'height_cm': 169.0, 'masculine_feminine': .86, 'fat': .26, 'muscularity': .34, 'measurements': {}},
    'skin': {'u': .34, 'v': .40, 'face_texture_index': 120, 'body_texture_index': 4, 'roughness': 1.10},
    'freckles': None,
    'accents': {},
    'eyes': {'primary': (.12, .42), 'secondary': (.16, .34), 'pattern': 'IRIS004', 'set': {}},
    'lashes': {'type': 'SHORT_FINE', 'melanin': .55, 'redness': .1},
    'makeup': {},
    'grooms': {
        'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_LowPonytail', {'Melanin': .5, 'Redness': .08, 'Whiteness': .7}),
        'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Natural', {'Melanin': .55, 'Redness': .08, 'Whiteness': .45}),
        'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin', {'Melanin': .4, 'Redness': .08}),
    },
    'costume': (
        {'piece': 'coat_skirt', 'port': 'SM_CP_G_CoatSkirtWhite', 'colours': ('CHARCOAL', 'SLATE')},
        {'piece': 'coat', 'port': 'SM_CP_G_CoatWhite', 'colours': ('CHARCOAL', 'SLATE', 'BLACK', 'ASH', 'BLUE', 'GOLD')},
        {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('CHARCOAL',)},
        {'piece': 'top', 'make': 'undertop', 'cut': 'crew', 'colours': ('ASH',)},
        {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('BLACK',)},
        {'piece': 'boots', 'make': 'boots', 'cut': 'ankle', 'colours': ('BLACK',)},
    ),
    'idle': (3.3, .92),
}
# The Mannequin row the costume builder measures its stand-in from and takes her ported garments' patterns from.
ROW = {'body': 'Quinn', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_CoatSkirtWhite', 'upper': 'SM_CP_G_CoatWhite', 'head': None,
       'shape': None}
LOOK = cast.FILES['look'].format(key=KEY)
COMMON = '/Game/MetaHumans/CommonGrove'


def install():
    """Adds Voss to the loaded Conclave tables (not to the file). Safe to call again."""
    cast.MH[KEY] = VOSS
    cast.CAST_MANNEQUIN[KEY] = ROW
    return KEY


def execute(operation):
    """grove:voss:<people operation>: the Conclave's operation of that name, on Voss."""
    install()
    import importlib
    import physis_conclave_people as people
    importlib.reload(people)
    install()
    name, _, option = operation.partition(':')
    if name not in people.KEYED:
        raise ValueError('unknown people operation %r (%s)' % (name, ', '.join(sorted(people.KEYED))))
    # Her shared MetaHuman assets go to a folder of her own. The Conclave's /Game/MetaHumans/Common is also Physis's,
    # assembled with Unreal 5.8: a 5.9 assembly into it asks to overwrite those assets ("any manual changes to their
    # Common assets will be lost"), and unattended that question is answered Cancel, so nothing is built.
    kept = cast.COMMON, cast.SKELETON
    cast.COMMON = COMMON
    cast.SKELETON = cast.SKELETON.replace(kept[0], COMMON)
    try:
        if option:
            return people.KEYED[name](KEY, option == people.REPLACE)
        return people.KEYED[name](KEY)
    finally:
        cast.COMMON, cast.SKELETON = kept
