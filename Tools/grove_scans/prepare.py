"""Turns the downloaded scans' texture maps (Art/Scans/Grove/<source>/<id>/...) into the sets the grove's materials
use, one naming and one layout whatever the source:

    Art/Scans/Grove/_ready/textures/T_GRS_<Name>_D.png    colour (sRGB); alpha = height for ground layers ('ground'),
                                                         opacity for leaf sheets ('leaf'), absent otherwise (then .jpg)
                                   T_GRS_<Name>_N.jpg    normal map, DirectX convention (as Unreal reads it)
                                   T_GRS_<Name>_ARM.jpg  ambient occlusion, roughness, metal in R, G, B ('surface', 'leaf')
    Art/Scans/Grove/_ready/sets.json                     {Name: {kind, size, tile_m, from, maps}}

    python3 -I Tools/grove_scans/prepare.py [Name ...] [--force]
    python3 -I Tools/grove_scans/prepare.py --models [WORD ...] [--force]     the scanned models' own maps (model_textures)

SETS is the table: Name -> (kind, source, id, map prefix, size px, tile metres). Poly Haven maps are named
<id>_<prefix><map>_<res>; a model's sheets have their own prefixes (leaves_, twig_, bark_, trunk_a_). ambientCG maps are
<Id>_<res>-JPG_<Map>. Images are decoded and encoded with ffmpeg and packed with numpy (no imaging library here).
Run it with the Kokoro venv's numpy on PYTHONPATH (-I drops the environment, so the path is added below).
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages'))
import numpy as np  # noqa: E402

SCANS = ROOT / 'Art/Scans/Grove'
OUT = SCANS / '_ready/textures'
PH, ACG = 'polyhaven', 'ambientcg'

# Name: (kind, source, id, map prefix, size, tile metres)
SETS = {
    # Terrain layers: colour with height in alpha, and a normal map (roughness is a constant per layer).
    'GForest': ('ground', PH, 'forest_ground_04', '', 2048, 3.0),
    'GLitter': ('ground', PH, 'leaves_forest_ground', '', 2048, 3.0),
    'GGrass': ('ground', ACG, 'Grass004', '', 2048, 2.5),
    'GDirt': ('ground', PH, 'rocky_trail', '', 2048, 3.0),
    'GMud': ('ground', PH, 'mud_forest', '', 1024, 3.0),
    'GGravel': ('ground', PH, 'river_small_rocks', '', 2048, 2.5),
    'GSand': ('ground', PH, 'damp_sand', '', 1024, 2.5),
    'GMoss': ('ground', ACG, 'Ground037', '', 2048, 2.5),
    'GBlight': ('ground', PH, 'burned_ground_01', '', 2048, 3.0),
    'GRock': ('ground', PH, 'cliff_side', '', 2048, 6.0),
    'GAsphalt': ('ground', PH, 'road_damaged', '', 2048, 4.0),
    # Surfaces of the level's own meshes, laid on triplanar by slot.
    'SConcrete': ('surface', PH, 'preconcrete_wall_001', '', 2048, 3.0),
    'SConcreteSlab': ('surface', PH, 'concrete_slab_wall', '', 2048, 3.0),
    'SConcreteOld': ('surface', PH, 'concrete_wall_003', '', 2048, 3.0),
    'SConcreteMoss': ('surface', ACG, 'Concrete026', '', 2048, 2.5),
    'SConcreteCracked': ('surface', PH, 'cracked_concrete_wall', '', 1024, 3.0),
    'SConcreteFloor': ('surface', PH, 'concrete_floor_damaged_01', '', 1024, 3.0),
    'SAsphalt': ('surface', PH, 'worn_asphalt', '', 1024, 3.0),
    'SRock': ('surface', PH, 'rock_face_03', '', 2048, 4.0),
    'SRockDark': ('surface', PH, 'dark_rock', '', 1024, 3.0),
    'SRockMoss': ('surface', ACG, 'Rock059', '', 1024, 2.5),
    'SSteel': ('surface', PH, 'rusty_metal_sheet', '', 1024, 1.5),
    'SSteelPlates': ('surface', ACG, 'MetalPlates002', '', 1024, 2.0),
    'SGraphite': ('surface', ACG, 'Metal030', '', 1024, 1.0),
    'SPaint': ('surface', ACG, 'PaintedMetal012', '', 2048, 1.6),
    'SPaintRust': ('surface', ACG, 'PaintedMetal010', '', 2048, 2.0),
    'SPaintOld': ('surface', ACG, 'PaintedMetal011', '', 1024, 2.0),
    'SRust': ('surface', PH, 'rusty_metal_03', '', 2048, 1.5),
    'SRustLight': ('surface', PH, 'rusty_metal_02', '', 1024, 1.5),
    'SCorrugated': ('surface', PH, 'worn_corrugated_iron', '', 1024, 2.0),
    'SDeckPlate': ('surface', ACG, 'DiamondPlate002', '', 1024, 1.0),
    'SSolar': ('surface', ACG, 'SolarPanel003', '', 1024, 1.6),
    'SCanvas': ('surface', ACG, 'Fabric061', '', 1024, .6),
    'SRope': ('surface', ACG, 'Rope001', '', 512, .25),
    'SPlanks': ('surface', PH, 'dark_wooden_planks', '', 1024, 2.0),
    'SWood': ('surface', PH, 'rough_wood', '', 1024, 1.2),
    'SMoss': ('surface', ACG, 'Moss002', '', 1024, 1.2),
    # Bark.
    'BOak': ('surface', PH, 'jolcham_oak_bark_01', '', 2048, 1.4),
    'BOakGrey': ('surface', ACG, 'Bark001', '', 2048, 1.6),
    'BBeech': ('surface', ACG, 'Bark005', '', 1024, 1.6),
    'BBirch': ('surface', ACG, 'Bark009', '', 1024, 1.2),
    'BPine': ('surface', PH, 'pine_bark', '', 1024, 1.2),
    'BGiant': ('surface', PH, 'metasequoia_bark', '', 2048, 2.4),
    'BHeart': ('surface', PH, 'bark_willow', '', 2048, 3.0),
    'BOld': ('surface', ACG, 'Bark006', '', 1024, 1.4),
    'BRoot': ('surface', PH, 'roots', '', 1024, 1.5),
    'BFir': ('surface', PH, 'fir_tree_01', 'trunk_a_', 1024, 1.2),
    # Leaf, needle and grass sheets: colour with the cutout in alpha.
    'LBroadleaf': ('leaf', PH, 'tree_small_02', 'leaves_', 2048, 0),
    'LFine': ('leaf', PH, 'jacaranda_tree', 'leaves_', 2048, 0),
    'LFir': ('leaf', PH, 'fir_tree_01', 'twig_', 2048, 0),
    'LPine': ('leaf', PH, 'pine_tree_01', 'twig_', 2048, 0),
    'LGrass': ('leaf', PH, 'grass_medium_01', '', 2048, 0),
    'LGrass2': ('leaf', PH, 'grass_medium_02', '', 1024, 0),
    'LFlowers': ('leaf', PH, 'celandine_01', '', 1024, 0),
}
# What each source calls a map: (colour, normal DX, packed arm, roughness, occlusion, metal, height, opacity).
POLYHAVEN = {'colour': ('diff', 'Diffuse'), 'normal': ('nor_dx',), 'arm': ('arm',), 'rough': ('rough', 'Rough'), 'ao': ('ao', 'AO'),
             'metal': (), 'height': ('disp', 'Displacement'), 'opacity': ('alpha', 'Alpha')}
AMBIENTCG = {'colour': ('Color',), 'normal': ('NormalDX',), 'arm': (), 'rough': ('Roughness',), 'ao': ('AmbientOcclusion',),
             'metal': ('Metalness',), 'height': ('Displacement',), 'opacity': ('Opacity',)}


def find(source, asset, prefix, role):
    folder = SCANS / source / asset
    names = (POLYHAVEN if source == PH else AMBIENTCG)[role]
    for name in names:
        pattern = '%s_%s%s_*' % (asset, prefix, name) if source == PH else '%s_*_%s.*' % (asset, name)
        hits = sorted(p for p in folder.glob(pattern) if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
        if hits:
            return hits[0]
    return None


def decode(path, size, channels):
    """An image as a (size, size, channels) uint8 array (1 grey, 3 RGB)."""
    fmt = 'gray' if channels == 1 else 'rgb24'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', 'scale=%d:%d:flags=lanczos' % (size, size), '-f', 'rawvideo',
                          '-pix_fmt', fmt, '-'], check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(size, size, channels)


def encode(array, path):
    """Writes an (h, w, 3 or 4) uint8 array as .png (lossless) or .jpg (quality 2), by the path's suffix."""
    h, w, c = array.shape
    fmt = 'rgba' if c == 4 else 'rgb24'
    quality = ['-q:v', '2'] if path.suffix == '.jpg' else ['-compression_level', '6']
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', fmt, '-s', '%dx%d' % (w, h), '-i', '-'] + quality + [str(path)],
                   input=array.tobytes(), check=True)


def bleed(rgb, alpha, passes=8):
    """Colour bled outward under a cutout's edge, so mip-mapping never pulls the sheet's dark background into a
    leaf's rim: every transparent texel takes the mean of its opaque neighbours, `passes` times."""
    rgb = rgb.astype(np.float32)
    known = alpha[..., 0] > 100
    for _ in range(passes):
        acc = np.zeros_like(rgb)
        count = np.zeros(known.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            shifted = np.roll(known, (dy, dx), (0, 1))
            acc += np.roll(rgb, (dy, dx), (0, 1)) * shifted[..., None]
            count += shifted
        grow = ~known & (count > 0)
        rgb[grow] = acc[grow] / count[grow][:, None]
        known = known | grow
    return np.clip(rgb, 0, 255).astype(np.uint8)


def mean_colour(path):
    """The map's mean colour, linear (the materials scale a painted surface's wear by its scan's mean brightness)."""
    small = decode(path, 64, 3).astype(np.float64) / 255.0
    linear = np.where(small <= .04045, small / 12.92, ((small + .055) / 1.055) ** 2.4)
    return [round(float(v), 4) for v in linear.reshape(-1, 3).mean(0)]


def build(name, force=False):
    kind, source, asset, prefix, size, tile = SETS[name]
    colour = find(source, asset, prefix, 'colour')
    if colour is None:
        return None, 'no colour map (not downloaded?)'
    maps = {}
    target = OUT / ('T_GRS_%s_D.%s' % (name, 'jpg' if kind == 'surface' else 'png'))
    if force or not target.exists():
        rgb = decode(colour, size, 3)
        if kind == 'surface':
            encode(rgb, target)
        else:
            extra = find(source, asset, prefix, 'height' if kind == 'ground' else 'opacity')
            alpha = decode(extra, size, 1) if extra else np.full((size, size, 1), 128 if kind == 'ground' else 255, np.uint8)
            if kind == 'leaf':
                rgb = bleed(rgb, alpha)
            encode(np.concatenate([rgb, alpha], 2), target)
    maps['D'] = target.name
    normal = find(source, asset, prefix, 'normal')
    if normal is not None:
        target = OUT / ('T_GRS_%s_N.jpg' % name)
        if force or not target.exists():
            encode(decode(normal, size, 3), target)
        maps['N'] = target.name
    if kind != 'ground':
        target = OUT / ('T_GRS_%s_ARM.jpg' % name)
        if force or not target.exists():
            packed = find(source, asset, prefix, 'arm')
            if packed is not None:
                arm = decode(packed, size, 3)
            else:
                def grey(role, default):
                    path = find(source, asset, prefix, role)
                    return decode(path, size, 1) if path else np.full((size, size, 1), default, np.uint8)
                arm = np.concatenate([grey('ao', 255), grey('rough', 160), grey('metal', 0)], 2)
            encode(arm, target)
        maps['ARM'] = target.name
    return {'kind': kind, 'size': size, 'tile_m': tile, 'from': '%s/%s' % (source, asset), 'maps': maps,
            'colour': mean_colour(OUT / maps['D'])}, None


MODEL_FACTS = ROOT / 'Art/Meshes/Grove/Scans/scans.json'
MODEL_OUT = SCANS / '_ready/models'


def model_textures(names, force=False):
    """The scanned models' own maps (Tools/grove_scans/process.py's scans.json lists each material's files) as

        Art/Scans/Grove/_ready/models/T_GS_<material>_D.jpg   colour (png with the cutout in alpha when masked)
                                      T_GS_<material>_N.jpg   normal, DirectX convention (the glTF's is OpenGL: green flipped)
                                      T_GS_<material>_ARM.jpg occlusion, roughness, metal (the glTF factors applied)
                                      T_GS_<material>_E.jpg   emissive, where the model has one
        Art/Scans/Grove/_ready/models.json                    {slot: {blend, two_sided, size, maps, emissive}}
    """
    facts = json.loads(MODEL_FACTS.read_text())
    manifest_path = MODEL_OUT.parent / 'models.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    missing = []
    for slot, row in sorted(facts['materials'].items()):
        if names and not any(n.lower() in slot.lower() for n in names):
            continue
        if row['blend'] == 'glass' or not row.get('maps', {}).get('D'):
            manifest[slot] = {'blend': row['blend'], 'two_sided': True, 'size': 0, 'maps': {}}
            continue
        name, size, maps, files = slot[3:], int(row['tex']), {}, {k: SCANS / v for k, v in row['maps'].items()}
        gone = [str(p) for p in files.values() if not p.exists()]
        if gone:
            missing.append('%s: %s' % (slot, ', '.join(gone)))
            continue
        factors = row.get('factors', {})
        masked = row['blend'] == 'masked'
        target = MODEL_OUT / ('T_GS_%s_D.%s' % (name, 'png' if masked else 'jpg'))
        if force or not target.exists():
            rgb = decode(files['D'], size, 3)
            tint = np.array((factors.get('colour') or [1, 1, 1, 1])[:3], np.float32)
            if np.abs(tint - 1).max() > .01:
                rgb = np.clip(rgb.astype(np.float32) * tint, 0, 255).astype(np.uint8)
            if masked:
                if 'A' in files:
                    alpha = decode(files['A'], size, 1)
                else:   # the colour map's own alpha channel
                    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(files['D']), '-vf', 'scale=%d:%d:flags=lanczos,alphaextract' % (size, size),
                                          '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], check=True, capture_output=True).stdout
                    alpha = np.frombuffer(raw, np.uint8).reshape(size, size, 1)
                encode(np.concatenate([bleed(rgb, alpha), alpha], 2), target)
            else:
                encode(rgb, target)
        maps['D'] = target.name
        if 'N' in files:
            target = MODEL_OUT / ('T_GS_%s_N.jpg' % name)
            if force or not target.exists():
                normal = decode(files['N'], size, 3).copy()
                normal[..., 1] = 255 - normal[..., 1]
                encode(normal, target)
            maps['N'] = target.name
        target = MODEL_OUT / ('T_GS_%s_ARM.jpg' % name)
        if force or not target.exists():
            arm = np.zeros((size, size, 3), np.float32)
            arm[..., 0] = 255.0
            arm[..., 1] = 255.0 * float(factors.get('roughness', 1.0))
            arm[..., 2] = 255.0 * float(factors.get('metallic', 1.0)) if 'ARM' in files else 0.0
            if 'ARM' in files:
                packed = decode(files['ARM'], size, 3).astype(np.float32)
                arm[..., 1] = packed[..., 1] * float(factors.get('roughness', 1.0))
                arm[..., 2] = packed[..., 2] * float(factors.get('metallic', 1.0))
                if '_arm_' in files['ARM'].name.lower():
                    arm[..., 0] = packed[..., 0]
            if 'AO' in files and files['AO'] != files.get('ARM'):
                arm[..., 0] = decode(files['AO'], size, 1)[..., 0]
            encode(np.clip(arm, 0, 255).astype(np.uint8), target)
        maps['ARM'] = target.name
        emissive = 0.0
        if 'E' in files:
            target = MODEL_OUT / ('T_GS_%s_E.jpg' % name)
            if force or not target.exists():
                encode(decode(files['E'], size, 3), target)
            maps['E'] = target.name
            emissive = max(factors.get('emissive') or [0]) * float(factors.get('emissive_strength', 1.0))
        manifest[slot] = {'blend': row['blend'], 'two_sided': bool(row.get('two_sided')), 'size': size, 'maps': maps, 'emissive': emissive,
                          'from': 'polyhaven/' + row.get('model', '')}
        print('%-46s %-7s %4d px  %s' % (slot, row['blend'], size, ' '.join(sorted(maps))), flush=True)
    manifest = {k: v for k, v in manifest.items() if k in facts['materials']}
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    for line in missing:
        print('  missing', line)
    return 1 if missing else 0


def main():
    if '--models' in sys.argv:
        return model_textures([a for a in sys.argv[1:] if not a.startswith('--')], '--force' in sys.argv)
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(SETS)
    force = '--force' in sys.argv
    manifest = OUT.parent / 'sets.json'
    sets = json.loads(manifest.read_text()) if manifest.exists() else {}
    missing = []
    for name in names:
        row, why = build(name, force)
        if row is None:
            missing.append('%s: %s' % (name, why))
            continue
        sets[name] = row
        print('%-18s %-7s %4d px  %s' % (name, row['kind'], row['size'], ' '.join(sorted(row['maps']))), flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(sets, indent=1, sort_keys=True))
    for line in missing:
        print('  missing', line)
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
