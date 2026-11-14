"""The Conclave's cast (level 3): how each person in physis_conclave_lore.PEOPLE looks (Tools/conclave/README.md,
People; the MetaHuman redesign is Tools/conclave/PEOPLE_DESIGN.md).

Plain Python with no imports, so the editor's Python (which has no numpy, so it cannot run the mesh generator's
builders, Tools/conclave_meshes/people.py) reads it on its own. people.py imports these tables and fails its build if
a name here is not one of its meshes, is worn by a body it was not modelled on, or disagrees with the lore about who
is a figure or who a MetaHuman is; Tools/conclave/people_audit.py checks MH against the engine's MetaHuman content and
the palette. The scenario reads CAST in the editor.

CAST_MANNEQUIN, one row per PEOPLE key (the looks before the MetaHumans):
  body   'Quinn' or 'Manny' (SKM_<body>_Simple playing MM_Idle), None for a figure
  scale  the stand-in's scale against a 1.80 m Mannequin (Tamsin is a child; the Listener stands tall). Nothing
         applies it: the scenario's look() does not read it and BP_NPC stands at actor scale 1. It is never a
         MetaHuman's size, which is its body's height (and, for a child, MH look_scale)
  skin   'Porcelain' or 'Obsidian' (MI_CP_<skin> on both Mannequin slots), None for a figure
  lower  garment on the pelvis, upper on spine_05, head on the head (SM_CP_G_*), or None
  shape  the static mesh of a figure that is not human (SM_CP_*, the lore's mesh), None for a person on a Mannequin
Every key of PEOPLE has a row, and the rows of one speaker are the same look (a person who appears again after
a quest keeps their clothes). Skins are chosen against the clothes so each figure reads at thirty metres:
obsidian sets off white, ivory and gold cloth and gives a black coat or gambeson black sleeves (Kairos, Teodor);
porcelain sets off red, black and light-blue cloth. Bare Mannequin arms read as sleeves, bare legs as hose.

CAST_METAHUMAN is the same table with 'mh' and 'look_scale' added to the rows of every MH entry that is not pending:
the key of the person's MetaHuman and the scale it is shown at (MH look_scale, 1 without one). The scenario shows that
person through BP_NPC's Look (FILES['look']) at that scale and empties Body, Lower, Upper, Head and Shape; while that
Blueprint is not assembled yet, the rest of the row is the stand-in look, so people can be built one at a time.
Figures and pending people keep their CAST_MANNEQUIN rows.

CAST is the table the scenario uses, chosen by LOOKS; setting LOOKS to 'mannequin' and re-running conclave:scenario is
the rollback (PEOPLE_DESIGN.md 3.6).

MH, one entry per dressed speaker, keyed by their first row's key (also the {key} of FILES). Values inside 'skin',
'freckles', 'accents', 'eyes'['set'], 'lashes' and 'makeup' are keyed by the Python names of the MetaHuman structs
they fill (MetaHumanCharacterSkin.h, Eyes.h, Makeup.h, MetaHumanCharacter.h), so the editor sets them as they are.
Enum values are member names ('TYPE1', 'IRIS003', 'SHORT_FINE', 'FULL_THIN_LINER'). A colour is a palette name
(Tools/conclave_meshes/palette.py PALETTE, linear RGB) or a linear RGB tuple; makeup and costume colours are always
palette names, since the palette rule still binds them.
  name      the lore's speaker; rows: the PEOPLE keys they appear as; age: years (None for the ageless First One)
  pending   None, or why the person waits for the author: such an entry is not built and its rows keep their Mannequin
  colouring natural skin, eye and hair colour in words (the author's review and the audit's summary)
  quality   EMetaHumanQualityLevel of the OPTIMIZED build ('HIGH'; 'MEDIUM' if the VRAM budget needs it)
  face      presets: ((preset under PRESETS, weight), ...), weights summing to 1: the face model coefficients are their
            weighted blend, quaternions renormalised. push: each PCA mode weight w becomes t + push * (w - t), t the
            archetype's (a new MetaHumanCharacter's); 1 is the blend itself. landmarks: ((index, (x, y, z)), ...), the
            change wanted on the mesh in cm, in get_face_landmarks' frame (79 points; x across the face, +x on the side
            of 23, 28 and 45; y forward; z up); request SCULPT_GAIN times as much. head_scale: set by the author in
            MetaHuman Creator (Python cannot write it).
  body      height_cm, masculine_feminine (0 masculine), fat, muscularity (0-1 of their constraint ranges, as the
            MetaHumanGenerator toolset's BodyShape), measurements: {constraint name: 0-1 of its range}
  look_scale  a child's entry only (absent: 1): the uniform scale of BP_NPC's Look, which shows the assembled person
            at that size in the level. MetaHuman has no child body, so a child is an adult body at the body model's
            least height (135 cm) shown smaller; the guides, the costume and the studio portraits stay at height_cm
  skin      MetaHumanCharacterSkinProperties: u (lightness), v (redness), face_texture_index (0-152, one per person),
            body_texture_index (0-8), roughness, and nail tints
  freckles  None (mask NONE) or MetaHumanCharacterFrecklesProperties
  accents   {region: MetaHumanCharacterAccentRegionProperties}; 0.5 is neutral
  eyes      primary, secondary: iris colour (u warmth: 0 blue, grey, green to 1 brown, amber; v brightness) on both eyes;
            pattern: the iris pattern; set: {'iris.<field>' | 'pupil.<field>' | 'cornea.<field>' | 'sclera.<field>':
            value} on both eyes after the colours
  lashes    MetaHumanCharacterEyelashesProperties (type adds the matching WI_Eyelashes groom)
  makeup    {'foundation' | 'eyes' | 'blush' | 'lips': that makeup struct's fields}; {} is none
  grooms    {slot: (wardrobe item under GROOMS, {instance parameter: value})}; Melanin, Redness and Whiteness carry
            natural hair colour. A slot missing here (Hair, Eyebrows, Beard, Mustache, Peachfuzz) is cleared.
  costume   the pieces of one skinned mesh on SKELETON (Tools/conclave_meshes/costumes.py builds it), each a dict:
              piece    its name, unique in the costume
              port     a people.py garment builder (SM_CP_G_*, one of the person's CAST_MANNEQUIN garments) refitted
                       to this body; keep: the part of it that stays when the rest is now a groom; note: a change
              make     or a new piece: a kind of NEW_PIECES, with cut: one of that kind's cuts
              colours  palette names, main first
              slot     the main colour's material slot (CN_Cloth when absent; gold trims are CN_Gold)
              bone     a rigid piece's one bone, weighted 100%; without it the piece takes the body's weights
  idle      (start seconds, play rate) of IDLE, so people standing together do not breathe in step
"""

LOOKS = 'metahuman'  # which table CAST is: 'metahuman' or 'mannequin' (the rollback)

# Where each MetaHuman's assets and files live ({key} is the MH key). people_assemble builds with absolute_build_path
# BUILD_PATH and name_override <key>, which is what makes the look FILES['look']. The editor writes the character, the
# face record and the guides; the Blender costume build reads the guides and writes the costume and its skin mask
# (white where skin shows); the editor imports both.
FILES = {
    'character': '/Game/Characters/Conclave/MHC_{key}',
    'look': '/Game/Conclave/People/{key}/BP_{key}',
    'costume': '/Game/Characters/Conclave/{key}/SK_{key}_Costume',
    'cloth_mask': '/Game/Characters/Conclave/{key}/T_{key}_ClothMask',
    'face_record': 'Art/Characters/Conclave/{key}/face.json',
    'body_guide': 'Art/Characters/Conclave/{key}/body-guide.fbx',
    'face_guide': 'Art/Characters/Conclave/{key}/face-guide.fbx',
    'costume_fbx': 'Art/Characters/Conclave/{key}/SK_{key}_Costume.fbx',
    'cloth_mask_png': 'Art/Characters/Conclave/{key}/T_{key}_ClothMask.png',
}
BUILD_PATH = '/Game/Conclave/People'
COMMON = '/Game/MetaHumans/Common'      # shared with Physis: back it up before the first build
PRESETS = '/MetaHumanCharacter/Optional/Presets'
GROOMS = '/MetaHumanCharacter/Optional/Grooms/Bindings'
SKELETON = '/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel'
IDLE = '/Game/Characters/Physis/Animations/Physis_MM_Idle'
# PEOPLE_DESIGN.md 3.2: CINEMATIC is silently HIGH on this pipeline; HIGH strips face LOD0, the only LOD with blend
# shapes, so the cheaper rig loses nothing; 2K sources are the default, set so no character drifts to 4K or 8K.
PIPELINE = 'OPTIMIZED'
RIG = 'JOINTS_ONLY'
TEXTURE_SOURCES = 'RES2K'
# The post-pass caps on assembled textures (pixels): the best face LOD keeps 2K; other face LODs, eyes and the body,
# mostly under clothes, 1K; teeth 512 (MH_Physis came out with an 8K body base colour).
TEXTURE_CAPS = {'face_lod1': 2048, 'face_other_lods': 1024, 'eyes': 1024, 'body': 1024, 'teeth': 512}
# The face model applies only 25-40% of a landmark move (physis_outfit_tools.py refine_nose), so landmarks hold the
# change wanted and the request is this many times larger; spike S4 measures it on a face that is not Physis's.
SCULPT_GAIN = 2.5

# Pieces the Mannequin skin used to stand in for, which costumes.py makes new for each body: kind -> cuts.
NEW_PIECES = {
    'sleeves': ('wrist', 'elbow_rolled', 'forearm_rolled', 'three_quarter', 'short', 'bell', 'wide'),
    'collar_cuffs': ('shirt',),
    'undertop': ('crew',),
    'trousers': ('ankle',),
    'socks': ('knee',),
    'boots': ('ankle', 'mid_calf', 'knee'),
    'shoes': ('lace', 'flat', 'strap'),
    'slippers': ('flat',),
    'sandals': ('flat',),
    'vambrace': ('forearm',),
}

CAST_MANNEQUIN = {
    # Orsolya Fenn, gardener: black skirt and white apron, light-blue blouse and white shawl, straw hat.
    'Orsolya': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Obsidian', 'lower': 'SM_CP_G_ApronSkirtWhite',
                'upper': 'SM_CP_G_BlouseShawl', 'head': 'SM_CP_G_StrawHat', 'shape': None},
    'OrsolyaThanks': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Obsidian', 'lower': 'SM_CP_G_ApronSkirtWhite',
                      'upper': 'SM_CP_G_BlouseShawl', 'head': 'SM_CP_G_StrawHat', 'shape': None},
    # Kairos, historian: a long black coat with gold buttons, white hair and beard.
    'Kairos': {'body': 'Manny', 'scale': 1.0, 'skin': 'Obsidian', 'lower': 'SM_CP_G_CoatSkirtBlack',
               'upper': 'SM_CP_G_CoatBlack', 'head': 'SM_CP_G_SageHair', 'shape': None},
    'KairosSpire': {'body': 'Manny', 'scale': 1.0, 'skin': 'Obsidian', 'lower': 'SM_CP_G_CoatSkirtBlack',
                    'upper': 'SM_CP_G_CoatBlack', 'head': 'SM_CP_G_SageHair', 'shape': None},
    'KairosDone': {'body': 'Manny', 'scale': 1.0, 'skin': 'Obsidian', 'lower': 'SM_CP_G_CoatSkirtBlack',
                   'upper': 'SM_CP_G_CoatBlack', 'head': 'SM_CP_G_SageHair', 'shape': None},
    # Petra Lune, archivist: red skirt and satchel, ivory blouse, black bun and spectacles.
    'Petra': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_SkirtSatchel',
              'upper': 'SM_CP_G_BlouseStrap', 'head': 'SM_CP_G_BunBlack', 'shape': None},
    'PetraThanks': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_SkirtSatchel',
                    'upper': 'SM_CP_G_BlouseStrap', 'head': 'SM_CP_G_BunBlack', 'shape': None},
    # Tamsin, a child: a light-blue tunic with a white belt and collar, short black hair.
    'Tamsin': {'body': 'Quinn', 'scale': 0.66, 'skin': 'Porcelain', 'lower': 'SM_CP_G_TunicSkirt',
               'upper': 'SM_CP_G_Tunic', 'head': 'SM_CP_G_ShortHair', 'shape': None},
    'TamsinThanks': {'body': 'Quinn', 'scale': 0.66, 'skin': 'Porcelain', 'lower': 'SM_CP_G_TunicSkirt',
                     'upper': 'SM_CP_G_Tunic', 'head': 'SM_CP_G_ShortHair', 'shape': None},
    # Halden-7, the Mendery's Robot.
    'Halden': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Robot'},
    'HaldenThanks': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Robot'},
    # Patience, the seated Mecha.
    'Patience': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Mecha'},
    'PatienceDone': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Mecha'},
    # Old Wen, an elder: an ivory robe with a black sash and stole, a white top bun.
    'Wen': {'body': 'Quinn', 'scale': 0.97, 'skin': 'Obsidian', 'lower': 'SM_CP_G_RobeSkirt',
            'upper': 'SM_CP_G_RobeShawl', 'head': 'SM_CP_G_BunWhite', 'shape': None},
    'WenDone': {'body': 'Quinn', 'scale': 0.97, 'skin': 'Obsidian', 'lower': 'SM_CP_G_RobeSkirt',
                'upper': 'SM_CP_G_RobeShawl', 'head': 'SM_CP_G_BunWhite', 'shape': None},
    # Marek Duran, a worker: a light-blue work shirt under a black canvas apron, a red cap.
    'Marek': {'body': 'Manny', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_WorkApronSkirt',
              'upper': 'SM_CP_G_WorkApron', 'head': 'SM_CP_G_CapRed', 'shape': None},
    # Sefa Moreno, a merchant: a tiered gold skirt, a white blouse, a red headscarf, gold coins and hoops.
    'Sefa': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Obsidian', 'lower': 'SM_CP_G_SkirtGold',
             'upper': 'SM_CP_G_Blouse', 'head': 'SM_CP_G_HeadscarfRed', 'shape': None},
    # Unit Quill, the courier Robot.
    'Quill': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Courier'},
    'QuillDone': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Courier'},
    # Teodor Vass, a guard: white armour over a black gambeson, a red sash, a crested white helmet.
    'Teodor': {'body': 'Manny', 'scale': 1.03, 'skin': 'Obsidian', 'lower': 'SM_CP_G_GuardBelt',
               'upper': 'SM_CP_G_ArmourVest', 'head': 'SM_CP_G_Helmet', 'shape': None},
    'TeodorDone': {'body': 'Manny', 'scale': 1.03, 'skin': 'Obsidian', 'lower': 'SM_CP_G_GuardBelt',
                   'upper': 'SM_CP_G_ArmourVest', 'head': 'SM_CP_G_Helmet', 'shape': None},
    # Doctor Ama Okafor: a white coat and a stethoscope, a black bob.
    'Ama': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Obsidian', 'lower': 'SM_CP_G_CoatSkirtWhite',
            'upper': 'SM_CP_G_CoatWhite', 'head': 'SM_CP_G_BobBlack', 'shape': None},
    # The Listener, a First One listener: a tall white robe with gold, a hood and a listening ring.
    'Listener': {'body': 'Manny', 'scale': 1.1, 'skin': 'Obsidian', 'lower': 'SM_CP_G_RobeSkirtTall',
                 'upper': 'SM_CP_G_RobeTall', 'head': 'SM_CP_G_HoodHalo', 'shape': None},
    # Dov Pell, a fisher: a light-blue oilskin, a black knitted cap and beard.
    'Dov': {'body': 'Manny', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_OilskinSkirt',
            'upper': 'SM_CP_G_Oilskin', 'head': 'SM_CP_G_KnitCapBeard', 'shape': None},
    # Rhea Sato, a farmer: a black skirt and blouse under a gold apron, a white field hat.
    'Rhea': {'body': 'Quinn', 'scale': 1.0, 'skin': 'Porcelain', 'lower': 'SM_CP_G_ApronSkirtGold',
             'upper': 'SM_CP_G_BlouseBib', 'head': 'SM_CP_G_FieldHat', 'shape': None},
    # Forge-Mother Ilex, the four-armed Mechanoid.
    'Ilex': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Mechanoid'},
    'IlexThanks': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Mechanoid'},
    # Iriel, a Lightform.
    'Iriel': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Lightform'},
    'IrielBase': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Lightform'},
    'IrielCrown': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Lightform'},
    # The Wisp, a lost Lightform child.
    'Wisp': {'body': None, 'scale': 1.0, 'skin': None, 'lower': None, 'upper': None, 'head': None, 'shape': 'SM_CP_Wisp'},
}

MH = {
    # Orsolya Fenn, the gardener at the Wellspring: sturdy, strong forearms, fair hair going grey under a straw hat.
    'Orsolya': {
        'name': 'Orsolya Fenn', 'rows': ('Orsolya', 'OrsolyaThanks'), 'age': 55, 'pending': None,
        'colouring': {'skin': 'light, sun-weathered', 'eyes': 'grey', 'hair': 'fair, going grey'},
        'quality': 'HIGH',
        'face': {'presets': (('Vivian', .6), ('Lani', .4)), 'push': 1.0, 'head_scale': 1.0,
                 # Lifted cheekbones, fuller lower cheeks, wider nostrils, a rounder chin.
                 'landmarks': ((2, (-.2, 0, 0)), (23, (0, .1, .15)), (29, (.2, 0, 0)), (45, (.15, 0, 0)), (62, (0, .1, 0)),
                               (66, (0, .1, .15)), (67, (-.15, 0, 0)))},
        'body': {'height_cm': 164.0, 'masculine_feminine': .92, 'fat': .50, 'muscularity': .45, 'measurements': {}},
        # No freckles, so she does not echo Physis (u .22, type-2 freckles).
        'skin': {'u': .20, 'v': .78, 'face_texture_index': 14, 'body_texture_index': 7, 'roughness': 1.06},
        'freckles': None,
        'accents': {'cheeks': {'redness': .6}, 'nose': {'redness': .6}},
        'eyes': {'primary': (.22, .52), 'secondary': (.18, .44), 'pattern': 'IRIS002', 'set': {}},
        'lashes': {'type': 'SHORT_FINE', 'melanin': .5, 'redness': .12},
        'makeup': {},
        'grooms': {
            # The low ponytail stands in for the plait at her nape and sits tight under the hat.
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_LowPonytail',
                     {'Melanin': .28, 'Redness': .12, 'Whiteness': .3}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Natural',
                         {'Melanin': .38, 'Redness': .12, 'Whiteness': .2}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .25, 'Redness': .1, 'Whiteness': .3}),
        },
        'costume': (
            {'piece': 'skirt', 'port': 'SM_CP_G_ApronSkirtWhite', 'colours': ('CHARCOAL', 'WHITE', 'GOLD')},
            {'piece': 'blouse', 'port': 'SM_CP_G_BlouseShawl', 'colours': ('BLUE', 'WHITE')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'elbow_rolled', 'colours': ('BLUE',)},
            {'piece': 'hat', 'port': 'SM_CP_G_StrawHat', 'keep': 'the hat and its ribbon; the plait is her Hair groom',
             'colours': ('GOLD_STRAW', 'CHARCOAL'), 'bone': 'head'},
            {'piece': 'boots', 'make': 'boots', 'cut': 'ankle', 'colours': ('BLACK',)},
        ),
        'idle': (0.0, .97),
    },
    # Kairos, keeper of the Archive: lean, a dry half-smile, white hair combed back to the collar, a full white beard.
    'Kairos': {
        'name': 'Kairos', 'rows': ('Kairos', 'KairosSpire', 'KairosDone'), 'age': 68, 'pending': None,
        'colouring': {'skin': 'cool olive', 'eyes': 'dark brown', 'hair': 'white'},
        'quality': 'HIGH',
        'face': {'presets': (('Walter', .6), ('Lorenzo', .4)), 'push': 1.0, 'head_scale': 1.0,
                 # A higher forehead, a longer straight nose, deeper-set eyes, hollow temples, mouth corners up.
                 'landmarks': ((6, (0, .1, 0)), (7, (0, 0, .2)), (18, (0, -.1, 0)), (19, (0, -.1, 0)), (22, (0, -.1, 0)),
                               (32, (0, 0, .08)), (33, (0, -.1, 0)), (41, (-.1, 0, 0)), (48, (0, 0, .08)), (58, (.1, 0, 0)),
                               (64, (0, 0, -.1)))},
        'body': {'height_cm': 181.0, 'masculine_feminine': .08, 'fat': .28, 'muscularity': .30, 'measurements': {}},
        'skin': {'u': .52, 'v': .32, 'face_texture_index': 109, 'body_texture_index': 8, 'roughness': 1.10},
        'freckles': None,
        'accents': {},
        'eyes': {'primary': (.88, .16), 'secondary': (.92, .10), 'pattern': 'IRIS005', 'set': {}},
        'lashes': {'type': 'SHORT_SPARSE', 'melanin': .6, 'redness': .05, 'salt_and_pepper': .6},
        'makeup': {},
        'grooms': {
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_M_BobSlick',
                     {'Melanin': .5, 'Redness': .05, 'Whiteness': .95}),
            'Beard': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Beards/WI_Beard_L_Full',
                      {'Melanin': .5, 'Redness': .05, 'Whiteness': .95}),
            'Mustache': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Mustaches/WI_Mustache_L_Full',
                         {'Melanin': .5, 'Redness': .05, 'Whiteness': .95}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Unruly',
                         {'Melanin': .6, 'Redness': .05, 'Whiteness': .8}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .4, 'Redness': .05, 'Whiteness': .9}),
        },
        # SM_CP_G_SageHair is all hair and beard: the grooms replace it.
        'costume': (
            {'piece': 'coat_skirt', 'port': 'SM_CP_G_CoatSkirtBlack', 'colours': ('CHARCOAL', 'GOLD')},
            {'piece': 'coat', 'port': 'SM_CP_G_CoatBlack', 'colours': ('CHARCOAL', 'GOLD', 'WHITE_PURE')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('CHARCOAL', 'GOLD'),
             'note': 'gold cuff buttons'},
            {'piece': 'collar_cuffs', 'make': 'collar_cuffs', 'cut': 'shirt', 'colours': ('WHITE_PURE',)},
            {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('CHARCOAL',)},
            {'piece': 'shoes', 'make': 'shoes', 'cut': 'lace', 'colours': ('BLACK',)},
        ),
        'idle': (3.8, .90),
    },
    # Petra Lune, archivist: slim, dark-brown hair in a low bun, gold wire spectacles.
    'Petra': {
        'name': 'Petra Lune', 'rows': ('Petra', 'PetraThanks'), 'age': 34, 'pending': None,
        'colouring': {'skin': 'light golden tan', 'eyes': 'hazel', 'hair': 'dark brown'},
        'quality': 'HIGH',
        'face': {'presets': (('Jelena', .5), ('Sunita', .5)), 'push': 1.0, 'head_scale': 1.0,
                 # A narrower jaw, a smaller mouth, level brows, eyes slightly wider apart.
                 'landmarks': ((1, (.2, 0, 0)), (19, (.08, 0, 0)), (25, (0, 0, -.1)), (28, (-.2, 0, 0)), (32, (-.1, 0, 0)),
                               (33, (-.08, 0, 0)), (48, (.1, 0, 0)), (78, (0, 0, -.1)))},
        'body': {'height_cm': 170.0, 'masculine_feminine': .95, 'fat': .30, 'muscularity': .25, 'measurements': {}},
        'skin': {'u': .48, 'v': .58, 'face_texture_index': 78, 'body_texture_index': 3, 'roughness': 1.06},
        'freckles': None,
        'accents': {},
        # Hazel: an amber-brown and a green mixed in one iris.
        'eyes': {'primary': (.74, .38), 'secondary': (.42, .48), 'pattern': 'IRIS007', 'set': {}},
        'lashes': {'type': 'LONG_SLIGHT_CURL', 'melanin': .92, 'redness': .10},
        'makeup': {},
        'grooms': {
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_Updo',
                     {'Melanin': .86, 'Redness': .14}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Fine',
                         {'Melanin': .88, 'Redness': .14}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .7, 'Redness': .14}),
        },
        'costume': (
            {'piece': 'skirt', 'port': 'SM_CP_G_SkirtSatchel', 'colours': ('RED', 'CHARCOAL', 'GOLD')},
            {'piece': 'blouse', 'port': 'SM_CP_G_BlouseStrap', 'colours': ('IVORY', 'CHARCOAL', 'GOLD')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('IVORY',), 'note': 'buttoned cuffs'},
            {'piece': 'spectacles', 'port': 'SM_CP_G_BunBlack', 'keep': 'the wire spectacles; the hair and bun are her Hair groom',
             'colours': ('GOLD', 'BLUE_PALE'), 'bone': 'head'},
            {'piece': 'boots', 'make': 'boots', 'cut': 'ankle', 'colours': ('BLACK',)},
        ),
        'idle': (1.9, 1.02),
    },
    # Tamsin, a child of about ten. MetaHuman has no child body, so she is an adult body at the body model's least
    # height (Height is 135-220 cm in its body_model.dna) shown at look_scale .9, about 122 cm in the level (author,
    # 2026-11-09: scale an adult down). Her head is the face model's adult-size head (head_scale 1: Python cannot set
    # HeadScale); on a 135 cm body that is about a sixth of her height.
    'Tamsin': {
        'name': 'Tamsin', 'rows': ('Tamsin', 'TamsinThanks'), 'age': 10, 'pending': None,
        'colouring': {'skin': 'light, freckled', 'eyes': 'green', 'hair': 'chestnut'},
        'quality': 'HIGH',
        'face': {'presets': (('Mikel', .6), ('Vivian', .4)), 'push': 1.0, 'head_scale': 1.0,
                 # A shorter nose and lower face, rounder cheeks, bigger eyes, a fuller forehead.
                 'landmarks': ((4, (0, 0, .15)), (5, (0, 0, .15)), (6, (0, -.15, 0)), (7, (0, .15, 0)), (20, (0, 0, .12)),
                               (23, (.2, .15, 0)), (37, (0, 0, -.08)), (44, (0, 0, .12)), (50, (0, 0, .15)), (53, (0, 0, -.08)),
                               (62, (0, -.2, .25)), (64, (0, -.25, .15)), (66, (-.2, .15, 0)))},
        # A child's torso: no bust (underbust 72 cm under the least chest, 75) and a straight waist (62 cm over the
        # least hip, 76); narrow shoulders (28 cm across) and small hands (14.5 cm round). Her neck is the longest the
        # body model gives a 135 cm body (8 cm of its 4-18): at its default the shoulders rose to within 2 cm of her
        # adult-size chin, and costumes.measure() found no neck between them (2026-11-09).
        'body': {'height_cm': 135.0, 'masculine_feminine': .55, 'fat': .32, 'muscularity': .18,
                 'measurements': {'Chest': 0.0, 'Underbust': .1, 'Bust Span': 0.0, 'Waist': .07, 'Hip': 0.0,
                                  'Neck Length': .29, 'Across Shoulder': .2, 'Hand Circumference': .12}},
        'look_scale': .9,
        'skin': {'u': .42, 'v': .60, 'face_texture_index': 103, 'body_texture_index': 1, 'roughness': 1.06},
        'freckles': {'mask': 'TYPE1', 'density': .35},
        'accents': {},
        'eyes': {'primary': (.36, .55), 'secondary': (.30, .46), 'pattern': 'IRIS003', 'set': {}},
        'lashes': {'type': 'SHORT_FINE', 'melanin': .7, 'redness': .3},
        'makeup': {},
        'grooms': {
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_Messy',
                     {'Melanin': .62, 'Redness': .4}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Fine',
                         {'Melanin': .65, 'Redness': .38}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .4, 'Redness': .35}),
        },
        'costume': (
            {'piece': 'tunic_skirt', 'port': 'SM_CP_G_TunicSkirt', 'colours': ('BLUE', 'WHITE_PURE', 'GOLD')},
            {'piece': 'tunic', 'port': 'SM_CP_G_Tunic', 'colours': ('BLUE', 'WHITE_PURE', 'GOLD')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'short', 'colours': ('BLUE',)},
            {'piece': 'clip', 'port': 'SM_CP_G_ShortHair', 'keep': 'the red clip on the right; the hair is her Hair groom',
             'colours': ('RED',), 'bone': 'head'},
            {'piece': 'socks', 'make': 'socks', 'cut': 'knee', 'colours': ('WHITE_PURE',)},
            # Closed lace-ups: the strap cut leaves the toes bare under its low vamp, and they showed through the socks.
            {'piece': 'shoes', 'make': 'shoes', 'cut': 'lace', 'colours': ('BLACK',)},
        ),
        'idle': (5.6, 1.08),
    },
    # Old Wen, an elder: small and frail, white hair in a top bun with two crossed gold pins.
    'Wen': {
        'name': 'Old Wen', 'rows': ('Wen', 'WenDone'), 'age': 82, 'pending': None,
        'colouring': {'skin': 'light, cool', 'eyes': 'brown, faded, age ring', 'hair': 'white'},
        'quality': 'HIGH',
        'face': {'presets': (('Sook-ja', .7), ('Grace', .3)), 'push': 1.0, 'head_scale': 1.0,
                 # Slightly hooded eyes, thin lips, mouth corners up.
                 'landmarks': ((4, (0, 0, .05)), (5, (0, 0, -.05)), (20, (0, 0, -.05)), (32, (0, 0, .05)), (44, (0, 0, -.05)),
                               (48, (0, 0, .05)))},
        'body': {'height_cm': 152.0, 'masculine_feminine': .95, 'fat': .40, 'muscularity': .12, 'measurements': {}},
        'skin': {'u': .28, 'v': .30, 'face_texture_index': 90, 'body_texture_index': 8, 'roughness': 1.12},
        'freckles': None,
        'accents': {},
        # Colour fades with age, and a softer limbal ring stands for the pale arcus of the old.
        'eyes': {'primary': (.80, .30), 'secondary': (.86, .22), 'pattern': 'IRIS008',
                 'set': {'iris.global_saturation': 1.2, 'iris.limbal_ring_color': (.6, .6, .6)}},
        'lashes': {'type': 'SHORT_SPARSE', 'melanin': .45, 'redness': .05, 'salt_and_pepper': .8},
        'makeup': {},
        'grooms': {
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_Updo',
                     {'Melanin': .4, 'Redness': .05, 'Whiteness': 1.0}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_S_FlatThin',
                         {'Melanin': .5, 'Redness': .05, 'Whiteness': .9}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .3, 'Redness': .05, 'Whiteness': 1.0}),
        },
        'costume': (
            {'piece': 'robe_skirt', 'port': 'SM_CP_G_RobeSkirt', 'colours': ('IVORY', 'CHARCOAL')},
            {'piece': 'robe', 'port': 'SM_CP_G_RobeShawl', 'colours': ('IVORY', 'CHARCOAL', 'GOLD_DEEP', 'GOLD_PALE')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wide', 'colours': ('IVORY',)},
            {'piece': 'pins', 'port': 'SM_CP_G_BunWhite', 'keep': 'the two crossed gold pins; the hair is her Hair groom',
             'colours': ('GOLD',), 'bone': 'head'},
            {'piece': 'slippers', 'make': 'slippers', 'cut': 'flat', 'colours': ('BLACK',)},
        ),
        'idle': (2.7, .85),
    },
    # Marek Duran, foundry worker: heavy-shouldered, an old broken nose, a buzz cut and stubble under a red cap.
    'Marek': {
        'name': 'Marek Duran', 'rows': ('Marek',), 'age': 45, 'pending': None,
        'colouring': {'skin': 'golden tan', 'eyes': 'brown', 'hair': 'black, a little grey'},
        'quality': 'HIGH',
        'face': {'presets': (('Orlando', .5), ('Victor', .5)), 'push': 1.0, 'head_scale': 1.0,
                 # A heavier jaw and brow; the broken nose leans to one side (Python's landmark moves may be asymmetric).
                 'landmarks': ((1, (-.25, 0, 0)), (6, (.15, 0, 0)), (28, (.25, 0, 0)), (59, (0, .1, 0)), (64, (.1, 0, 0)))},
        'body': {'height_cm': 178.0, 'masculine_feminine': .05, 'fat': .45, 'muscularity': .72, 'measurements': {}},
        # Variant 6 is native to a lighter skin (u .49) than his, but it is the nearest heavy-stubble variant.
        'skin': {'u': .62, 'v': .66, 'face_texture_index': 6, 'body_texture_index': 6, 'roughness': 1.06},
        'freckles': None,
        'accents': {},
        'eyes': {'primary': (.84, .26), 'secondary': (.90, .16), 'pattern': 'IRIS004', 'set': {}},
        'lashes': {'type': 'SHORT_SPARSE', 'melanin': .95, 'redness': .08},
        'makeup': {},
        'grooms': {
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_BuzzCut',
                     {'Melanin': .95, 'Redness': .08, 'Whiteness': .1}),
            'Beard': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Beards/WI_Beard_S_Stubble',
                      {'Melanin': .95, 'Redness': .08, 'Whiteness': .15}),
            'Mustache': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Mustaches/WI_Mustache_S_Stubble',
                         {'Melanin': .95, 'Redness': .08, 'Whiteness': .15}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_FlatThick',
                         {'Melanin': .95, 'Redness': .08}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .8, 'Redness': .08}),
        },
        'costume': (
            {'piece': 'apron_skirt', 'port': 'SM_CP_G_WorkApronSkirt', 'colours': ('CHARCOAL', 'RED', 'GOLD')},
            {'piece': 'shirt_apron', 'port': 'SM_CP_G_WorkApron',
             'colours': ('BLUE', 'CHARCOAL', 'GOLD', 'GOLD_PALE', 'RED', 'WHITE', 'WHITE_PURE')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'elbow_rolled', 'colours': ('BLUE',)},
            {'piece': 'cap', 'port': 'SM_CP_G_CapRed', 'keep': 'the flat cap; the hair is his Hair groom', 'colours': ('RED',),
             'bone': 'head'},
            {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('CHARCOAL',)},
            {'piece': 'boots', 'make': 'boots', 'cut': 'ankle', 'colours': ('BLACK',)},
        ),
        'idle': (6.4, .98),
    },
    # Sefa Moreno, fruit seller: full-figured, high round cheeks, black hair pulled back under a red headscarf.
    'Sefa': {
        'name': 'Sefa Moreno', 'rows': ('Sefa',), 'age': 41, 'pending': None,
        'colouring': {'skin': 'warm brown', 'eyes': 'dark brown', 'hair': 'black'},
        'quality': 'HIGH',
        'face': {'presets': (('Zuri', .6), ('Sunita', .4)), 'push': 1.0, 'head_scale': 1.0,
                 # High round cheeks, a wider mouth, fuller lips.
                 'landmarks': ((4, (0, .05, 0)), (5, (0, .05, 0)), (23, (0, .15, .1)), (32, (.12, 0, 0)), (48, (-.12, 0, 0)),
                               (66, (0, .15, .1)))},
        'body': {'height_cm': 161.0, 'masculine_feminine': .92, 'fat': .62, 'muscularity': .35, 'measurements': {}},
        'skin': {'u': .70, 'v': .74, 'face_texture_index': 141, 'body_texture_index': 3, 'roughness': 1.06},
        'freckles': None,
        'accents': {},
        'eyes': {'primary': (.90, .12), 'secondary': (.94, .06), 'pattern': 'IRIS006', 'set': {}},
        'lashes': {'type': 'LONG_CURL', 'melanin': 1.0, 'redness': .10},
        'makeup': {},
        'grooms': {
            # The hairline shows under the scarf's front edge.
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_PulledBack',
                     {'Melanin': .97, 'Redness': .12}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Thick',
                         {'Melanin': .97, 'Redness': .12}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .85, 'Redness': .12}),
        },
        'costume': (
            {'piece': 'skirt', 'port': 'SM_CP_G_SkirtGold', 'colours': ('GOLD_DEEP', 'RED', 'GOLD', 'CHARCOAL')},
            {'piece': 'blouse', 'port': 'SM_CP_G_Blouse', 'colours': ('WHITE_PURE', 'RED', 'GOLD', 'GOLD_DEEP', 'BLUE')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'three_quarter', 'colours': ('WHITE_PURE',)},
            {'piece': 'headscarf', 'port': 'SM_CP_G_HeadscarfRed',
             'keep': 'the headscarf and the hoop earrings; the line of hair under it is her Hair groom',
             'colours': ('RED', 'GOLD'), 'bone': 'head'},
            {'piece': 'sandals', 'make': 'sandals', 'cut': 'flat', 'colours': ('RED',)},
        ),
        'idle': (.9, 1.0),
    },
    # Teodor Vass, guard at the north gate: a powerful build, a square jaw, a coil buzz cut under a crested helmet.
    'Teodor': {
        'name': 'Teodor Vass', 'rows': ('Teodor', 'TeodorDone'), 'age': 33, 'pending': None,
        'colouring': {'skin': 'very dark, cool', 'eyes': 'dark brown', 'hair': 'black'},
        'quality': 'HIGH',
        'face': {'presets': (('Omari', .6), ('Victor', .4)), 'push': 1.0, 'head_scale': 1.0,
                 # A square jaw, a firm chin, level brows.
                 'landmarks': ((1, (-.2, 0, 0)), (25, (0, 0, -.08)), (28, (.2, 0, 0)), (62, (0, .1, 0)), (78, (0, 0, -.08)))},
        'body': {'height_cm': 187.0, 'masculine_feminine': .03, 'fat': .28, 'muscularity': .78, 'measurements': {}},
        'skin': {'u': .93, 'v': .16, 'face_texture_index': 146, 'body_texture_index': 5, 'roughness': 1.06},
        'freckles': None,
        'accents': {},
        'eyes': {'primary': (.92, .10), 'secondary': (.95, .05), 'pattern': 'IRIS009', 'set': {}},
        'lashes': {'type': 'SHORT_FINE', 'melanin': 1.0, 'redness': .04},
        'makeup': {},
        'grooms': {
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_CoilBuzzCut',
                     {'Melanin': 1.0, 'Redness': .04}),
            'Beard': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Beards/WI_Beard_S_Stubble',
                      {'Melanin': 1.0, 'Redness': .04}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Dense',
                         {'Melanin': 1.0, 'Redness': .04}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .9, 'Redness': .04}),
        },
        'costume': (
            {'piece': 'belt', 'port': 'SM_CP_G_GuardBelt', 'colours': ('BLACK', 'CHARCOAL', 'GOLD', 'GOLD_PALE', 'WHITE_PURE', 'ASH')},
            {'piece': 'armour', 'port': 'SM_CP_G_ArmourVest',
             'colours': ('CHARCOAL', 'WHITE_PURE', 'GOLD', 'GOLD_PALE', 'RED', 'ASH', 'BLUE')},
            {'piece': 'helmet', 'port': 'SM_CP_G_Helmet', 'colours': ('WHITE_PURE', 'GOLD', 'RED', 'BLACK'), 'bone': 'head'},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('CHARCOAL',), 'note': 'quilted like the gambeson'},
            {'piece': 'vambrace_l', 'make': 'vambrace', 'cut': 'forearm', 'colours': ('WHITE_PURE', 'GOLD'), 'slot': 'CN_Lacquer',
             'bone': 'lowerarm_l'},
            {'piece': 'vambrace_r', 'make': 'vambrace', 'cut': 'forearm', 'colours': ('WHITE_PURE', 'GOLD'), 'slot': 'CN_Lacquer',
             'bone': 'lowerarm_r'},
            {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('CHARCOAL',)},
            {'piece': 'boots', 'make': 'boots', 'cut': 'knee', 'colours': ('BLACK',)},
        ),
        'idle': (4.6, .95),
    },
    # Doctor Ama Okafor: trim, tired eyes, a black bob with a few grey hairs and a thin gold band across the crown.
    'Ama': {
        'name': 'Doctor Ama Okafor', 'rows': ('Ama',), 'age': 47, 'pending': None,
        'colouring': {'skin': 'dark, neutral', 'eyes': 'dark brown', 'hair': 'black, a few grey'},
        'quality': 'HIGH',
        'face': {'presets': (('Asha', .5), ('Celeste', .5)), 'push': 1.0, 'head_scale': 1.0,
                 # Defined cheekbones, tired and slightly hooded eyes.
                 'landmarks': ((20, (0, 0, -.05)), (23, (.1, 0, .1)), (44, (0, 0, -.05)), (66, (-.1, 0, .1)))},
        'body': {'height_cm': 171.0, 'masculine_feminine': .90, 'fat': .35, 'muscularity': .38, 'measurements': {}},
        'skin': {'u': .86, 'v': .46, 'face_texture_index': 73, 'body_texture_index': 5, 'roughness': 1.06},
        'freckles': None,
        'accents': {},
        'eyes': {'primary': (.90, .14), 'secondary': (.93, .08), 'pattern': 'IRIS001', 'set': {}},
        'lashes': {'type': 'LONG_SLIGHT_CURL', 'melanin': 1.0, 'redness': .06},
        'makeup': {},
        'grooms': {
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_M_BobBangs',
                     {'Melanin': 1.0, 'Redness': .06, 'Whiteness': .1}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_SlightArch',
                         {'Melanin': 1.0, 'Redness': .06, 'Whiteness': .05}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .9, 'Redness': .06}),
        },
        'costume': (
            {'piece': 'coat_skirt', 'port': 'SM_CP_G_CoatSkirtWhite', 'colours': ('WHITE_COOL', 'WHITE_PURE')},
            {'piece': 'coat', 'port': 'SM_CP_G_CoatWhite', 'colours': ('WHITE_COOL', 'WHITE_PURE', 'BLACK', 'ASH', 'BLUE', 'GOLD')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('WHITE_COOL',)},
            {'piece': 'top', 'make': 'undertop', 'cut': 'crew', 'colours': ('BLUE',)},
            {'piece': 'band', 'port': 'SM_CP_G_BobBlack', 'keep': 'the thin gold band across the crown; the bob is her Hair groom',
             'colours': ('GOLD',), 'bone': 'head'},
            {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('CHARCOAL',)},
            {'piece': 'shoes', 'make': 'shoes', 'cut': 'flat', 'colours': ('BLACK',)},
        ),
        'idle': (2.3, .97),
    },
    # The Listener, a First One (PEOPLE_DESIGN.md 2): tall, narrow, long-necked, hairless and browless, large ice-blue
    # irises in gold rings; "rings that listen" in the ring behind the hood, the limbal rings, the liner and the nails.
    'Listener': {
        'name': 'The Listener', 'rows': ('Listener',), 'age': None, 'pending': None,
        # More alien (author, 2026-11-09, after the first portraits read as a bald human): pushed further, longer and
        # narrower, paler under a cool light-blue foundation, colourless lips, small pupils, gold cat-eye and cheek marks.
        'colouring': {'skin': 'ashen pale, least red', 'eyes': 'ice blue, full gold rings, blue-white sclera',
                      'hair': 'none: white fuzz, lashes'},
        'quality': 'HIGH',
        # Pushed past the blend instead of extreme landmark moves, which the Python path does not bound.
        'face': {'presets': (('Jelena', .55), ('Asha', .45)), 'push': 1.3, 'head_scale': 1.0,
                 # Larger, wider-set eyes; a bridge with no dip; narrow nostrils; high flat cheekbones hollowed below; a
                 # small serene mouth; a long tapering chin; small flat ears; a longer skull under the hood.
                 'landmarks': ((1, (0.32, 0, 0)), (2, (0.24, 0, 0)), (3, (0.16, 0, 0)), (6, (0, 0.16, 0)), (13, (0, -1, 0)),
                               (18, (0.312, 0, 0.104)), (19, (0.208, 0, 0)), (20, (0, 0, 0.312)), (22, (-0.312, 0, 0.104)), (23, (0.24, 0, 0.24)),
                               (28, (-0.32, 0, 0)), (29, (-0.24, 0, 0)), (30, (-0.16, 0, 0)), (32, (-0.24, 0, 0.08)), (33, (-0.208, 0, 0)),
                               (37, (0, 0, -0.208)), (38, (-0.32, 0, 0)), (44, (0, 0, 0.312)), (45, (-0.24, 0, 0)), (48, (0.24, 0, 0.08)),
                               (53, (0, 0, -0.208)), (54, (0.32, 0, 0)), (59, (0, 0.32, 0)), (60, (0, 0, 1)), (62, (0, 0, -0.448)),
                               (64, (0, 0, -0.24)), (66, (-0.24, 0, 0.24)), (67, (0.24, 0, 0)))},
        'body': {'height_cm': 208.0, 'masculine_feminine': .40, 'fat': .05, 'muscularity': .20,
                 'measurements': {'Neck Length': 1.0, 'Across Shoulder': .15, 'Upper Arm Length': .95, 'Lower Arm Length': .95,
                                  'Hand Circumference': .10, 'Waist': .15, 'Inseam': .90}},
        # The least red tone at mid lightness, inside the synthesis model's natural map (fallback: u .95, v .05);
        # an unlined, unmarked variant; gold nails, the toes' too, though the robe hides the feet.
        # v 0 baked to a tan: the live preview tints to any u/v, but the texture synthesis clamps to its natural tone map
        # (first build, 2026-11-09). Physis's u .22 / v .52 bakes true; this is as pale and clearly less red.
        'skin': {'u': .25, 'v': .30, 'face_texture_index': 130, 'body_texture_index': 1, 'roughness': .95,
                 'fingernail_tint_color': 'GOLD', 'fingernail_tint_intensity': .7, 'fingernail_metallic': .5,
                 'toenail_tint_color': 'GOLD', 'toenail_tint_intensity': .7, 'toenail_metallic': .5},
        'freckles': None,
        'accents': {'lips': {'saturation': 0.0, 'redness': 0.0, 'lightness': .65}, 'cheeks': {'redness': 0.0, 'saturation': 0.0},
                    'nose': {'redness': 0.0}, 'ears': {'redness': 0.0}},
        'eyes': {'primary': (.03, .97), 'secondary': (.08, .85), 'pattern': 'IRIS001',
                 'set': {'iris.limbal_ring_color': 'GOLD', 'iris.limbal_ring_size': .85, 'cornea.size': .185, 'pupil.dilation': .85,
                         'sclera.use_custom_tint': True, 'sclera.tint': (.82, .90, 1.0), 'sclera.vascularity_intensity': 0.0}},
        # White lashes and fuzz catch the rim light (spike S9 checks they read).
        'lashes': {'type': 'LONG_SLIGHT_CURL', 'melanin': 0.0, 'lightness': 1.0},
        # Assembly bakes makeup; whether the metallic finish survives the bake is spike S9.
        # No foundation: it covers the face only, so the ears, neck and hands kept another colour and it read as paint
        # (first alien portraits, 2026-11-09). The pale, least-red skin carries the coolness everywhere instead.
        'makeup': {'eyes': {'type': 'CAT_EYE', 'primary_color': 'GOLD', 'secondary_color': 'GOLD', 'roughness': .2,
                            'opacity': 1.0, 'metalness': 1.0},
                   'blush': {'type': 'ANGLED', 'color': 'GOLD', 'intensity': 1.0, 'roughness': .25},
                   'lips': {'type': 'NATURAL', 'color': 'WHITE_COOL', 'roughness': .45, 'opacity': .45, 'metalness': 0.0}},
        'grooms': {
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': 0.0, 'Whiteness': 1.0}),
        },
        'costume': (
            {'piece': 'robe_skirt', 'port': 'SM_CP_G_RobeSkirtTall', 'colours': ('WHITE_PURE', 'GOLD', 'GOLD_DEEP')},
            {'piece': 'robe', 'port': 'SM_CP_G_RobeTall', 'colours': ('WHITE_PURE', 'BLUE', 'GOLD', 'GOLD_DEEP')},
            # Ending at the wrist so the gold-nailed hands show; floor length, so no shoes.
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'bell', 'colours': ('WHITE_PURE', 'BLUE_PALE'),
             'note': 'lined in BLUE_PALE'},
            {'piece': 'hood', 'port': 'SM_CP_G_HoodHalo', 'keep': 'the hood and its gold edge',
             'note': 'lined in BLUE_PALE instead of shaded dark, so his face reads under the Spine',
             'colours': ('WHITE_PURE', 'BLUE_PALE', 'GOLD')},
            {'piece': 'ring', 'port': 'SM_CP_G_HoodHalo', 'keep': 'the listening ring, its lights and its bracket',
             'colours': ('GOLD', 'GOLD_PALE', 'LIGHT_BLUE'), 'bone': 'head'},
        ),
        'idle': (5.1, .80),
    },
    # Dov Pell, fisher at the Reservoir: thickset, a squint, auburn hair and full beard going grey under a knit cap.
    'Dov': {
        'name': 'Dov Pell', 'rows': ('Dov',), 'age': 61, 'pending': None,
        'colouring': {'skin': 'fair, wind-burned', 'eyes': 'blue', 'hair': 'auburn, going grey'},
        'quality': 'HIGH',
        'face': {'presets': (('Bruce', .6), ('Walter', .4)), 'push': 1.0, 'head_scale': 1.0,
                 # A squint, a broad nose, a heavy brow.
                 'landmarks': ((37, (0, 0, .05)), (45, (.15, 0, 0)), (53, (0, 0, .05)), (59, (0, .1, 0)), (67, (-.15, 0, 0)))},
        'body': {'height_cm': 176.0, 'masculine_feminine': .08, 'fat': .55, 'muscularity': .55, 'measurements': {}},
        'skin': {'u': .16, 'v': .86, 'face_texture_index': 4, 'body_texture_index': 7, 'roughness': 1.06},
        'freckles': None,
        'accents': {'cheeks': {'redness': .7}, 'nose': {'redness': .65}},
        'eyes': {'primary': (.10, .80), 'secondary': (.16, .60), 'pattern': 'IRIS003', 'set': {}},
        'lashes': {'type': 'SHORT_SPARSE', 'melanin': .6, 'redness': .5, 'salt_and_pepper': .5},
        'makeup': {},
        'grooms': {
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_Clean',
                     {'Melanin': .62, 'Redness': .58, 'Whiteness': .35}),
            'Beard': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Beards/WI_Beard_S_Full',
                      {'Melanin': .55, 'Redness': .62, 'Whiteness': .45}),
            'Mustache': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Mustaches/WI_Mustache_S_Full',
                         {'Melanin': .55, 'Redness': .62, 'Whiteness': .45}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Messy',
                         {'Melanin': .6, 'Redness': .55, 'Whiteness': .3}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .45, 'Redness': .5, 'Whiteness': .4}),
        },
        'costume': (
            {'piece': 'oilskin_skirt', 'port': 'SM_CP_G_OilskinSkirt', 'colours': ('BLUE', 'BLACK')},
            {'piece': 'oilskin', 'port': 'SM_CP_G_Oilskin', 'colours': ('BLUE', 'BLACK', 'CHARCOAL')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'wrist', 'colours': ('BLUE', 'BLACK'), 'slot': 'CN_Blue',
             'note': 'black cuffs'},
            {'piece': 'cap', 'port': 'SM_CP_G_KnitCapBeard', 'keep': 'the knitted cap; the hair and beard are his grooms',
             'colours': ('CHARCOAL',), 'bone': 'head'},
            {'piece': 'trousers', 'make': 'trousers', 'cut': 'ankle', 'colours': ('CHARCOAL',)},
            {'piece': 'boots', 'make': 'boots', 'cut': 'knee', 'colours': ('BLACK',), 'slot': 'CN_Lacquer', 'note': 'rubber'},
        ),
        'idle': (1.4, .93),
    },
    # Rhea Sato, terrace farmer: compact and strong, a determined chin, brown hair pulled back under a field hat.
    'Rhea': {
        'name': 'Rhea Sato', 'rows': ('Rhea',), 'age': 26, 'pending': None,
        'colouring': {'skin': 'light-medium, freckled', 'eyes': 'green', 'hair': 'brown'},
        'quality': 'HIGH',
        'face': {'presets': (('Etta', .5), ('Tuya', .5)), 'push': 1.0, 'head_scale': 1.0,
                 # Rounder cheeks, a determined chin.
                 'landmarks': ((2, (-.1, 0, 0)), (29, (.1, 0, 0)), (62, (0, .1, 0)))},
        'body': {'height_cm': 158.0, 'masculine_feminine': .88, 'fat': .30, 'muscularity': .55, 'measurements': {}},
        'skin': {'u': .36, 'v': .50, 'face_texture_index': 119, 'body_texture_index': 2, 'roughness': 1.06},
        'freckles': {'mask': 'TYPE1', 'density': .2},
        'accents': {},
        'eyes': {'primary': (.38, .48), 'secondary': (.30, .42), 'pattern': 'IRIS007', 'set': {}},
        'lashes': {'type': 'SHORT_THIN', 'melanin': .8, 'redness': .2},
        'makeup': {},
        'grooms': {
            # Sized to sit under the hat's neck curtain.
            'Hair': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_PulledBack',
                     {'Melanin': .7, 'Redness': .2}),
            'Eyebrows': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Natural',
                         {'Melanin': .75, 'Redness': .2}),
            'Peachfuzz': ('/MetaHumanCharacter/Optional/Grooms/Bindings/Peachfuzz/WI_Peachfuzz_M_Thin',
                          {'Melanin': .55, 'Redness': .2}),
        },
        'costume': (
            {'piece': 'skirt', 'port': 'SM_CP_G_ApronSkirtGold', 'colours': ('CHARCOAL', 'GOLD_DEEP', 'GOLD')},
            {'piece': 'blouse', 'port': 'SM_CP_G_BlouseBib', 'colours': ('CHARCOAL', 'GOLD_DEEP', 'GOLD')},
            {'piece': 'sleeves', 'make': 'sleeves', 'cut': 'forearm_rolled', 'colours': ('CHARCOAL',)},
            {'piece': 'hat', 'port': 'SM_CP_G_FieldHat', 'keep': 'the hat, its neck curtain and chin cord; the hair is her Hair groom',
             'colours': ('WHITE', 'GOLD_DEEP', 'GOLD', 'BLACK'), 'bone': 'head'},
            {'piece': 'boots', 'make': 'boots', 'cut': 'mid_calf', 'colours': ('BLACK',)},
        ),
        'idle': (6.9, 1.05),
    },
}

# Every dressed human whose entry is not pending shows their MetaHuman at its look_scale; their row stays the stand-in
# look, whose 'scale' is never read for a MetaHuman.
_SHOWN = {row: key for key, entry in MH.items() if not entry['pending'] for row in entry['rows']}
CAST_METAHUMAN = {row: dict(look, mh=_SHOWN[row], look_scale=MH[_SHOWN[row]].get('look_scale', 1.0)) if row in _SHOWN
                  else look for row, look in CAST_MANNEQUIN.items()}

CAST = {'metahuman': CAST_METAHUMAN, 'mannequin': CAST_MANNEQUIN}[LOOKS]
