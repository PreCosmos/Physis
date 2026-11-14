"""Offline audit of the Conclave's MetaHuman cast (MH in Content/Python/physis_conclave_cast.py) against the installed
engine's MetaHuman content and headers, the lore and the Conclave palette, with a summary for review. Plain Python: no
numpy, no Unreal, nothing written.

  python3 Tools/conclave/people_audit.py [--engine DIR]    (DIR: the engine's Engine folder)

Checks, for every MH entry (Tools/conclave/PEOPLE_DESIGN.md is the design):
  the schema: the keys the editor operations and the costume build read, and nothing else;
  rows: every CAST_METAHUMAN row that shows a MetaHuman names an entry that is not pending, of its own speaker, and an
    entry's rows are the lore's rows of that speaker;
  face: every preset exists in the plugin's content, the weights sum to 1, landmark indices exist (79, the Physis
    baseline's count), mirrored pairs move as mirrors (a warning: a crooked feature may be meant), head_scale in range;
  body: height within the MetaHumanGenerator toolset's clamp, the 0-1 fractions, measurement names the engine's own;
  look_scale, the one optional key: a child's only, in LOOK_SCALE;
  skin, freckles, accents, eyes, lashes, makeup: every field is a field of the struct it fills, in the header's clamp
    range, enum values are members, colours are palette names or RGB; face_texture_index is in the texture model,
    unique across the cast, and near the skin's u (a warning: a variant is chosen for its stubble or marks too);
  grooms: each item exists in its slot's folder, its parameters are the groom pipeline's and in 0-1, everyone has
    peachfuzz;
  makeup and costume colours pass palette.allowed (natural skin, eyes and hair are the author's exception and are not
    checked against it);
  costume: ported builders are the person's own Mannequin garments and every lower and upper one is ported, new pieces
    are NEW_PIECES kinds and cuts, slots are toolkit's, rigid bones are on the MetaHuman skeleton, names unique;
  quality and idle within the build policy and the idle's length; the module's paths and build enums.
Exit status 1 if anything fails.
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Content/Python'))
sys.path.insert(0, str(ROOT / 'Tools/conclave_meshes'))

import palette  # noqa: E402
import physis_conclave_cast as cast  # noqa: E402
from physis_conclave_lore import PEOPLE  # noqa: E402

ENGINE = (Path(sys.argv[sys.argv.index('--engine') + 1]) if '--engine' in sys.argv
          else Path.home() / 'UnrealEngine/Linux_Unreal_Engine_5.9.0_preview-1/Engine')  # where Tools/package_physis.sh finds it
MHC = ENGINE / 'Plugins/MetaHuman/MetaHumanCharacter'
HEADERS = [MHC / 'Source/MetaHumanCharacter/Public' / name for name in
           ('MetaHumanCharacterSkin.h', 'MetaHumanCharacterEyes.h', 'MetaHumanCharacterMakeup.h', 'MetaHumanCharacter.h',
            'MetaHumanCharacterAssemblySettings.h')]
HEADERS.append(MHC / 'Source/MetaHumanCharacterEditor/Public/MetaHumanCharacterEditorSubsystem.h')
TEXTURE_MODEL = MHC / 'Content/Optional/TextureSynthesis/TS-1.3-F_UE_res-1024_nchr-153'
BODY_UI = MHC / 'Source/MetaHumanCharacterEditor/Private/UI/Views/SMetaHumanCharacterEditorBodyModelToolView.cpp'
WARDROBE_INI = MHC / 'Config/Editor.ini'
GROOM_PIPELINE = MHC / 'Content/BuildPipeline/DefaultWardobePipeline/DefaultGroomPipeline.uasset'
TOOLSET = ENGINE / 'Plugins/Experimental/Toolsets/MetaHumanGenerator/Content/Python/metahuman_toolset/metahuman.py'
LANDMARKS = ROOT / 'Art/Characters/Physis/face-identity-baseline.json'  # get_face_landmarks on Physis: count and sides
BODY_GUIDE = ROOT / 'Art/Characters/Physis/physis-body-guide.fbx'      # metahuman_base_skel's bones, exported
TOOLKIT = ROOT / 'Tools/conclave_meshes/toolkit.py'                     # SLOTS, the material slots of every mesh

IDLE_SECONDS = 7.567          # Physis_MM_Idle's SequenceLength (30 fps), read from the asset on 2026-11-09
IDLE_RATES = (.75, 1.25)      # slower or faster than this and the idle stops reading as breathing
QUALITIES = ('HIGH', 'MEDIUM')  # PEOPLE_DESIGN.md 3.2: CINEMATIC is silently HIGH here; LOW drops the hair cards
PUSH = (1.0, 1.3)             # the Listener's 1.15 is spike S3; past this the face leaves what the model was fitted on
LANDMARK_MOVE = 1.0           # cm wanted on the mesh: more is a different head, not a sculpt
MIRROR = .15                  # cm: landmarks this close to each other's mirror image are a left/right pair
NATIVE_TONE = .05             # a face variant's native tone this close to the skin's u keeps its colour gains
GROOM_PARAMETERS = ('Melanin', 'Redness', 'Whiteness', 'Lightness', 'Roughness')  # the natural ones; no dye
SCHEMA = {'name', 'rows', 'age', 'pending', 'colouring', 'quality', 'face', 'body', 'skin', 'freckles', 'accents', 'eyes',
          'lashes', 'makeup', 'grooms', 'costume', 'idle'}
OPTIONAL = {'look_scale'}     # a child's entry only; without it the person shows at 1
LOOK_SCALE = (.8, 1.0)        # a child is an adult body at the least height (135 cm) shown smaller: 108-135 cm
FACE_KEYS = {'presets', 'push', 'landmarks', 'head_scale'}
BODY_KEYS = {'height_cm', 'masculine_feminine', 'fat', 'muscularity', 'measurements'}
EYE_KEYS = {'primary', 'secondary', 'pattern', 'set'}
COLOURING_KEYS = {'skin', 'eyes', 'hair'}
PIECE_KEYS = {'piece', 'port', 'make', 'cut', 'colours', 'keep', 'note', 'slot', 'bone'}
# Which header struct each MH section fills (the eyes' iris, pupil, cornea and sclera come from the eye struct's fields).
SECTIONS = {'skin': 'FMetaHumanCharacterSkinProperties', 'freckles': 'FMetaHumanCharacterFrecklesProperties',
            'lashes': 'FMetaHumanCharacterEyelashesProperties'}

FAIL, WARN = [], []


def fail(message):
    FAIL.append(message)


def warn(message):
    WARN.append(message)


# ---------------------------------------------------------------- what the engine says

def snake(name):
    """Unreal's Python name for a C++ name: PrimaryColorU -> primary_color_u, UnderEye -> under_eye."""
    name = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name)
    return re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', '_', name).lower()


def balanced(text, start):
    """The index just past the parenthesis that closes the one at text[start]."""
    depth = 0
    for i in range(start, len(text)):
        depth += {'(': 1, ')': -1}.get(text[i], 0)
        if depth == 0:
            return i + 1
    raise ValueError('unbalanced parentheses')


def parse_headers(paths):
    """Structs {name: {python field: (C++ type, clamp (lo, hi) or None, writable from Python)}} and enums {name: Python
    member names} of the headers, as UHT exposes them: bool fields lose their b, ScriptName renames, hidden enum members
    are left out."""
    structs, enums = {}, {}
    for path in paths:
        text = path.read_text()
        for match in re.finditer(r'enum class (\w+)\s*:\s*\w+\s*\{(.*?)\};', text, re.S):
            members = []
            for line in match.group(2).splitlines():
                line = line.split('//')[0].strip()
                member = re.match(r'(\w+)\s*(?:=\s*[^,]*?)?\s*(?:UMETA\((.*)\))?\s*,?$', line)
                if member and 'Hidden' not in (member.group(2) or ''):
                    members.append(snake(member.group(1)).upper())
            enums[match.group(1)] = members
        for match in re.finditer(r'struct\s+(?:\w+_API\s+)?(F\w+)\s*\{(.*?)\n\};', text, re.S):
            body, fields, at = match.group(2), {}, 0
            while True:
                at = body.find('UPROPERTY(', at)
                if at < 0:
                    break
                end = balanced(body, at + len('UPROPERTY'))
                meta = body[at:end]
                declaration = re.match(r'\s*([\w:<>, *]+?)\s+(\w+)\s*(=[^;]*)?;', body[end:])
                at = end
                if not declaration:
                    continue
                kind, name = declaration.group(1).strip(), declaration.group(2)
                script = re.search(r'ScriptName\s*=\s*"(\w+)"', meta)
                if script:
                    name = script.group(1)
                elif kind == 'bool' and re.match(r'b[A-Z]', name):
                    name = name[1:]
                lo, hi = (re.search(r'%s\s*=\s*"([-\d.]+)"' % key, meta) for key in ('ClampMin', 'ClampMax'))
                fields[snake(name)] = (kind, (float(lo.group(1)), float(hi.group(1))) if lo and hi else None,
                                       'BlueprintReadWrite' in meta)
            structs[match.group(1)] = fields
    return structs, enums


def content_file(path):
    """The .uasset of a plugin content path (/MetaHumanCharacter/... is the plugin's Content folder)."""
    prefix = '/MetaHumanCharacter/'
    return MHC / 'Content' / (path[len(prefix):] + '.uasset') if path.startswith(prefix) else None


def wardrobe_slots():
    """{slot name: content folder it lists} from the plugin's wardrobe settings."""
    text = WARDROBE_INI.read_text()
    return {slot: folder for folder, slot in re.findall(r'ContentDirectoryToMonitor=\(Path="([^"]+)"\),SlotName="(\w+)"', text)}


def body_constraints():
    """Every body constraint name the Creator's body tool shows."""
    text = BODY_UI.read_text()
    names = []
    for block in re.findall(r'const TArray<FName> \w+ConstraintsNames =\s*\{(.*?)\};', text, re.S):
        names += re.findall(r'TEXT\("([^"]+)"\)', block)
    return names


def toolset_height():
    """The MetaHumanGenerator toolset's clamp on height_cm (PEOPLE_DESIGN.md: the real minimum is spike S13)."""
    match = re.search(r"height_cm = unreal\.uproperty\(.*?'ClampMin': ([\d.]+), 'ClampMax': ([\d.]+)", TOOLSET.read_text(), re.S)
    return float(match.group(1)), float(match.group(2))


def texture_model():
    """(variant count, [native tone u per variant], {attribute: (values, names)}) of the face texture model."""
    params = json.loads((TEXTURE_MODEL / 'ts_params.json').read_text())
    attributes = json.loads((TEXTURE_MODEL / 'texture_attributes.json').read_text())['attributes']
    tones = [params['characters'][key]['v_ui_chr_0'] for key in sorted(params['characters'])]
    return params['model']['n_characters'], tones, {k: (v['values'], v['names']) for k, v in attributes.items()}


def landmarks():
    return [(p['x'], p['y'], p['z']) for p in json.loads(LANDMARKS.read_text())['points']]


def slots():
    """toolkit.SLOTS read from the source (toolkit imports numpy), or None if it cannot be read."""
    try:
        for node in ast.parse(TOOLKIT.read_text()).body:
            if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'SLOTS' for t in node.targets):
                return set(ast.literal_eval(node.value))
    except (OSError, SyntaxError, ValueError) as error:
        warn('material slots not checked: %s (%s)' % (TOOLKIT.name, error))
    return None


def bones():
    """Bone names of the MetaHuman body skeleton in Physis's exported body guide (FBX stores each as name\\0\\1Model)."""
    if not BODY_GUIDE.exists():
        warn('rigid bones not checked: %s is missing' % BODY_GUIDE.relative_to(ROOT))
        return None
    return {name.decode() for name in re.findall(rb'([A-Za-z0-9_]+)\x00\x01Model', BODY_GUIDE.read_bytes())}


# ---------------------------------------------------------------- the checks

def number(value, lo, hi):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and lo <= value <= hi


def colour_ok(value):
    """A palette name or a linear RGB tuple in 0-1."""
    if isinstance(value, str):
        return value in palette.PALETTE
    return isinstance(value, tuple) and len(value) == 3 and all(number(c, 0, 1) for c in value)


def fields(where, values, struct, structs, enums):
    """Each value names a field of struct that Python can write, and fits it: its clamp, its enum, a colour, a bool."""
    known = structs[struct]
    for name, value in values.items():
        if name not in known or not known[name][2]:
            fail('%s: %s is not a field of %s that Python can write' % (where, name, struct))
            continue
        kind, clamp, _ = known[name]
        if kind in enums:
            ok = value in enums[kind]
        elif kind == 'FLinearColor':
            ok = colour_ok(value)
        elif kind == 'bool':
            ok = isinstance(value, bool)
        elif kind in ('float', 'int32'):
            ok = number(value, *(clamp or (float('-inf'), float('inf')))) and (kind == 'float' or isinstance(value, int))
        else:
            ok = False
        if not ok:
            fail('%s: %s = %r does not fit %s %s%s' % (where, name, value, kind, name, ' in %s' % (clamp,) if clamp else ''))


def palette_colour(where, name):
    if not isinstance(name, str) or name not in palette.PALETTE:
        fail('%s: %r is not a palette colour name' % (where, name))
    elif not palette.allowed(palette.PALETTE[name]):
        fail('%s: %s is outside the palette' % (where, name))


def check_rows():
    speakers = {}
    for row in PEOPLE:
        speakers.setdefault(row[1], []).append(row[0])
    for row, look in cast.CAST_METAHUMAN.items():
        key = look.get('mh')
        if key is None:
            continue
        if key not in cast.MH:
            fail('CAST_METAHUMAN %s shows %r, which has no MH entry' % (row, key))
        elif cast.MH[key]['pending']:
            fail('CAST_METAHUMAN %s shows %s, which is pending' % (row, key))
        elif row not in cast.MH[key]['rows']:
            fail('CAST_METAHUMAN %s shows %s, whose rows are %s' % (row, key, cast.MH[key]['rows']))
    for key, entry in cast.MH.items():
        if tuple(speakers.get(entry['name'], ())) != entry['rows']:
            fail('MH %s: rows %s, but the lore gives %r %s' % (key, entry['rows'], entry['name'], speakers.get(entry['name'])))
        for row in entry['rows']:
            shows = cast.CAST_METAHUMAN.get(row, {}).get('mh')
            if entry['pending'] and shows is not None:
                fail('MH %s is pending, but row %s shows a MetaHuman' % (key, row))


def check_entry(key, entry, engine):
    structs, enums, constraints, height, (variants, tones, _), points, slot_folders, groom_names, toolkit_slots, skeleton = engine
    where = 'MH %s' % key
    if not SCHEMA <= set(entry) <= SCHEMA | OPTIONAL:
        fail('%s: keys %s missing, %s unknown' % (where, sorted(SCHEMA - set(entry)), sorted(set(entry) - SCHEMA - OPTIONAL)))
        return
    for part, wanted in (('face', FACE_KEYS), ('body', BODY_KEYS), ('eyes', EYE_KEYS), ('colouring', COLOURING_KEYS)):
        if set(entry[part]) != wanted:
            fail('%s %s: keys %s, wanted %s' % (where, part, sorted(entry[part]), sorted(wanted)))
            return
    if entry['quality'] not in QUALITIES:
        fail('%s: quality %r, not one of %s' % (where, entry['quality'], QUALITIES))
    start, rate = entry['idle']
    if not number(start, 0, IDLE_SECONDS - 1e-3) or not number(rate, *IDLE_RATES):
        fail('%s: idle %r (start in 0-%.2f s, rate %s)' % (where, entry['idle'], IDLE_SECONDS, IDLE_RATES))

    face = entry['face']
    weights = [w for _, w in face['presets']]
    for name, _ in face['presets']:
        if not content_file(cast.PRESETS + '/' + name).exists():
            fail('%s: preset %s is not in the plugin content' % (where, name))
    if not weights or any(not number(w, 1e-6, 1) for w in weights) or abs(sum(weights) - 1) > 1e-6:
        fail('%s: preset weights %s do not sum to 1' % (where, weights))
    if not number(face['push'], *PUSH):
        fail('%s: push %r outside %s' % (where, face['push'], PUSH))
    lo, hi = structs['FMetaHumanCharacterFaceEvaluationSettings']['head_scale'][1]
    if not number(face['head_scale'], lo, hi):
        fail('%s: head_scale %r outside %s-%s' % (where, face['head_scale'], lo, hi))
    moved = {}
    for index, delta in face['landmarks']:
        if not isinstance(index, int) or not 0 <= index < len(points) or index in moved:
            fail('%s: landmark %r is not one of 0-%d once' % (where, index, len(points) - 1))
        elif len(delta) != 3 or any(not number(c, -LANDMARK_MOVE, LANDMARK_MOVE) for c in delta):
            fail('%s: landmark %d moves %r (at most %.1f cm on each axis)' % (where, index, delta, LANDMARK_MOVE))
        else:
            moved[index] = delta
    for i, d in moved.items():
        x, y, z = points[i]
        twin = next((j for j, p in enumerate(points) if j != i and abs(p[0] + x) < MIRROR and abs(p[1] - y) < MIRROR
                     and abs(p[2] - z) < MIRROR), None)
        if twin is not None and i < twin and twin in moved and any(abs(a - b) > 1e-9 for a, b in zip((-d[0], d[1], d[2]), moved[twin])):
            warn('%s: landmarks %d and %d are a pair but move %s and %s (crooked on purpose?)' % (where, i, twin, d, moved[twin]))

    body = entry['body']
    if not number(body['height_cm'], *height):
        fail('%s: height %r cm outside the toolset clamp %s' % (where, body['height_cm'], height))
    for name in ('masculine_feminine', 'fat', 'muscularity'):
        if not number(body[name], 0, 1):
            fail('%s: body %s %r outside 0-1' % (where, name, body[name]))
    for name, value in body['measurements'].items():
        if name not in constraints or name in ('Masculine/Feminine', 'Muscularity', 'Fat', 'Height'):
            fail('%s: measurement %r is not a body constraint of its own' % (where, name))
        elif not number(value, 0, 1):
            fail('%s: measurement %s %r outside 0-1' % (where, name, value))
    if 'look_scale' in entry and (not number(entry['look_scale'], *LOOK_SCALE) or entry['age'] is None or entry['age'] >= 18):
        fail('%s: look_scale %r (a child\'s only, in %s-%s)' % (where, entry['look_scale'], LOOK_SCALE[0], LOOK_SCALE[1]))

    skin = dict(entry['skin'])
    index = skin.pop('face_texture_index', None)
    if not isinstance(index, int) or not 0 <= index < variants:
        fail('%s: face_texture_index %r is not one of the model\'s 0-%d' % (where, index, variants - 1))
    elif abs(tones[index] - skin.get('u', -1)) > NATIVE_TONE:
        warn('%s: face variant %d is native to u %.2f, the skin is u %.2f' % (where, index, tones[index], skin.get('u', -1)))
    for name in ('u', 'v', 'face_texture_index', 'body_texture_index', 'roughness'):
        if name not in entry['skin']:
            fail('%s: skin has no %s' % (where, name))
    fields(where + ' skin', skin, SECTIONS['skin'], structs, enums)
    if entry['freckles'] is not None:
        fields(where + ' freckles', entry['freckles'], SECTIONS['freckles'], structs, enums)
    regions = structs['FMetaHumanCharacterAccentRegions']
    for region, values in entry['accents'].items():
        if region not in regions:
            fail('%s: accents %s is not a region' % (where, region))
        else:
            fields('%s accents %s' % (where, region), values, regions[region][0], structs, enums)

    eyes, eye = entry['eyes'], structs['FMetaHumanCharacterEyeProperties']
    for part in ('primary', 'secondary'):
        if len(eyes[part]) != 2 or any(not number(c, 0, 1) for c in eyes[part]):
            fail('%s: eyes %s %r is not (u, v) in 0-1' % (where, part, eyes[part]))
    fields(where + ' eyes', {'pattern': eyes['pattern']}, eye['iris'][0], structs, enums)
    for path, value in eyes['set'].items():
        part, _, name = path.partition('.')
        if part not in eye:
            fail('%s: eyes set %s is not on an eye' % (where, path))
        else:
            fields('%s eyes %s' % (where, part), {name: value}, eye[part][0], structs, enums)
    fields(where + ' lashes', entry['lashes'], SECTIONS['lashes'], structs, enums)
    makeup = structs['FMetaHumanCharacterMakeupSettings']
    for part, values in entry['makeup'].items():
        if part not in makeup:
            fail('%s: makeup %s is not a makeup section' % (where, part))
            continue
        fields('%s makeup %s' % (where, part), values, makeup[part][0], structs, enums)
        for name, value in values.items():
            if structs[makeup[part][0]].get(name, ('',))[0] == 'FLinearColor':
                palette_colour('%s makeup %s %s' % (where, part, name), value)

    for slot, (item, parameters) in entry['grooms'].items():
        folder = slot_folders.get(slot)
        if folder is None or slot == 'Eyelashes':
            fail('%s: groom slot %s is not a hair slot (lashes come from lashes)' % (where, slot))
        elif item.rsplit('/', 1)[0] != folder or not item.startswith(cast.GROOMS + '/'):
            fail('%s: %s groom %s is not in %s' % (where, slot, item, folder))
        elif not content_file(item).exists():
            fail('%s: %s groom %s is not in the plugin content' % (where, slot, item))
        for name, value in parameters.items():
            if name not in GROOM_PARAMETERS or name not in groom_names:
                fail('%s: %s groom parameter %s is not a natural hair parameter of the groom pipeline' % (where, slot, name))
            elif not number(value, 0, 1):
                fail('%s: %s groom %s %r outside 0-1' % (where, slot, name, value))
    if 'Peachfuzz' not in entry['grooms']:
        fail('%s: no peachfuzz (everyone gets it, in their hair colour)' % where)

    check_costume(where, key, entry['costume'], toolkit_slots, skeleton)


def check_costume(where, key, costume, toolkit_slots, skeleton):
    look = cast.CAST_MANNEQUIN[cast.MH[key]['rows'][0]]
    own = {look[field] for field in ('lower', 'upper', 'head') if look[field]}
    ported, names = set(), set()
    for piece in costume:
        label = '%s costume %s' % (where, piece.get('piece'))
        if set(piece) - PIECE_KEYS or 'piece' not in piece or piece['piece'] in names:
            fail('%s: keys %s (piece names unique; known keys %s)' % (label, sorted(piece), sorted(PIECE_KEYS)))
            continue
        names.add(piece['piece'])
        if ('port' in piece) == ('make' in piece):
            fail('%s: a piece is either ported or made' % label)
        elif 'port' in piece:
            ported.add(piece['port'])
            if piece['port'] not in own:
                fail('%s: ports %s, not one of %s\'s Mannequin garments %s' % (label, piece['port'], key, sorted(own)))
            if 'cut' in piece or 'slot' in piece:
                fail('%s: a ported piece keeps its builder\'s cut and slots' % label)
        elif piece['make'] not in cast.NEW_PIECES or piece.get('cut') not in cast.NEW_PIECES[piece['make']]:
            fail('%s: %s %s is not a NEW_PIECES kind and cut' % (label, piece['make'], piece.get('cut')))
        elif 'keep' in piece:
            fail('%s: keep is for a ported piece' % label)
        if not piece.get('colours'):
            fail('%s: no colours' % label)
        for name in piece.get('colours', ()):
            palette_colour(label, name)
        if 'slot' in piece and toolkit_slots is not None and piece['slot'] not in toolkit_slots:
            fail('%s: slot %s is not one of toolkit.SLOTS' % (label, piece['slot']))
        if 'bone' in piece and skeleton is not None and piece['bone'] not in skeleton:
            fail('%s: bone %s is not on metahuman_base_skel' % (label, piece['bone']))
    for field in ('lower', 'upper'):
        if look[field] and look[field] not in ported:
            fail('%s costume: the %s garment %s is not ported' % (where, field, look[field]))
    if look['head'] and look['head'] not in ported:
        warn('%s costume: %s is not ported (its hair is now grooms)' % (where, look['head']))


def check_module(enums):
    for name, pattern in cast.FILES.items():
        if '{key}' not in pattern:
            fail('FILES %s %r has no {key}' % (name, pattern))
    if cast.FILES['look'] != cast.BUILD_PATH + '/{key}/BP_{key}':
        fail('FILES look %r is not where a build to BUILD_PATH named <key> writes its Blueprint' % cast.FILES['look'])
    if not cast.SKELETON.startswith(cast.COMMON + '/'):
        fail('SKELETON %s is not in COMMON %s' % (cast.SKELETON, cast.COMMON))
    for name, path in (('PRESETS', cast.PRESETS), ('GROOMS', cast.GROOMS)):
        if not content_file(path + '/x').parent.is_dir():
            fail('%s %s is not a plugin content folder' % (name, path))
    idle = ROOT / 'Content' / (cast.IDLE[len('/Game/'):] + '.uasset')
    if not idle.exists():
        fail('IDLE %s is not in the project' % cast.IDLE)
    for name, value, enum in (('PIPELINE', cast.PIPELINE, 'EMetaHumanDefaultPipelineType'), ('RIG', cast.RIG, 'EMetaHumanRigType'),
                              ('TEXTURE_SOURCES', cast.TEXTURE_SOURCES, 'ERequestTextureResolution')):
        if value not in enums.get(enum, ()):
            fail('%s %r is not a member of %s %s' % (name, value, enum, enums.get(enum)))
    if cast.LOOKS not in ('metahuman', 'mannequin') or cast.CAST is not {'metahuman': cast.CAST_METAHUMAN, 'mannequin': cast.CAST_MANNEQUIN}[cast.LOOKS]:
        fail('LOOKS %r does not pick CAST' % cast.LOOKS)
    if any(not number(v, 1, 8192) for v in cast.TEXTURE_CAPS.values()) or not number(cast.SCULPT_GAIN, 1, 4):
        fail('TEXTURE_CAPS %s / SCULPT_GAIN %r' % (cast.TEXTURE_CAPS, cast.SCULPT_GAIN))


# ---------------------------------------------------------------- the summary

def summary(engine):
    _, _, _, _, (variants, tones, attributes), points, _, _, _, _ = engine
    shown = sum('mh' in look for look in cast.CAST.values())
    figures = sum(look['shape'] is not None for look in cast.CAST.values())
    print('Conclave MetaHuman cast audit: %d entries (%d pending); LOOKS %s: %d MetaHuman rows, %d Mannequin, %d figures' %
          (len(cast.MH), sum(bool(e['pending']) for e in cast.MH.values()), cast.LOOKS, shown, len(cast.CAST) - shown - figures, figures))
    print('  engine: %s (%d face variants, %d landmarks)' % (ENGINE, variants, len(points)))
    print('  %-9s %4s %6s  %-10s %-20s %-22s %-24s %-6s %-12s %s' %
          ('who', 'age', 'height', 'skin u/v', 'face variant, u', 'eyes', 'hair', 'build', 'idle', 'costume'))
    for key, entry in cast.MH.items():
        index = entry['skin']['face_texture_index']
        variant = ('%d %s, %.2f' % (index, ' '.join('%s%d' % (name.split()[-1][0], values[index]) for name, (values, _) in attributes.items()),
                                    tones[index]) if 0 <= index < variants else '%r?' % index)
        made = sum('make' in piece for piece in entry['costume'])
        print('  %-9s %4s %6s  %-10s %-20s %-22s %-24s %-6s %-12s %d pieces, %d new%s' % (
            key, entry['age'] if entry['age'] is not None else '-', '%.0f cm' % entry['body']['height_cm'],
            '%.2f %.2f' % (entry['skin']['u'], entry['skin']['v']), variant,
            entry['colouring']['eyes'], entry['colouring']['hair'], entry['quality'],
            '%.1f s x%.2f' % entry['idle'], len(entry['costume']), made, '; PENDING' if entry['pending'] else ''))
    print('  skin u: %s' % ', '.join('%s %.2f' % (k, e['skin']['u']) for k, e in sorted(cast.MH.items(), key=lambda kv: kv[1]['skin']['u'])))
    for part in ('eyes', 'hair'):
        counts = {}
        for entry in cast.MH.values():
            colour = entry['colouring'][part].split(',')[0].split(':')[0]
            counts[colour] = counts.get(colour, 0) + 1
        print('  %s: %s' % (part, ', '.join('%s %d' % kv for kv in sorted(counts.items(), key=lambda kv: -kv[1]))))
    for key, entry in cast.MH.items():
        if entry['pending']:
            print('  pending %s: %s' % (key, entry['pending']))
        if 'look_scale' in entry:
            print('  %s: built at %.0f cm, shown at look_scale %.2f, %.1f cm in the level' %
                  (key, entry['body']['height_cm'], entry['look_scale'], entry['body']['height_cm'] * entry['look_scale']))


def main():
    structs, enums = parse_headers(HEADERS)
    engine = (structs, enums, body_constraints(), toolset_height(), texture_model(), landmarks(), wardrobe_slots(),
              {name for name in GROOM_PARAMETERS if name.encode() + b'\x00' in GROOM_PIPELINE.read_bytes()}, slots(), bones())
    check_module(enums)
    check_rows()
    for key, entry in cast.MH.items():
        check_entry(key, entry, engine)
    seen = {}
    for key, entry in cast.MH.items():
        seen.setdefault(entry['skin']['face_texture_index'], []).append(key)
    for index, keys in seen.items():
        if len(keys) > 1:
            fail('face variant %d is shared by %s (each person has their own)' % (index, ', '.join(keys)))
    summary(engine)
    for message in WARN:
        print('  warning: ' + message)
    if FAIL:
        print('\nFAILED (%d):' % len(FAIL))
        for message in FAIL:
            print('  - ' + message)
        sys.exit(1)
    print('\nall checks passed')


if __name__ == '__main__':
    main()
