"""Shortlists Poly Haven's catalogue for the grove and draws contact sheets of the candidates' thumbnails, so the
picks can be made by eye. Metadata and thumbnails only: the assets themselves are fetched by fetch.py from a picks file.

    python3 -I Tools/grove_scans/catalogue.py [GROUP ...]

Writes Saved/Grove/scans/<group>.json (rows in sheet order: index, id, name, categories, polycount or map list, the
megabytes of the 2k and 4k downloads) and Saved/Grove/scans/<group>_<n>.png (thumbnails, 8 across, in that order).
"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/Grove/scans'
AGENT = 'physis-level-build/1.0 (game level build; CC0 asset fetch)'
API = 'https://api.polyhaven.com'
COLUMNS, ROWS, CELL = 8, 6, 200

# group -> (asset type, categories any of which admits an asset, words any of which in id/tags admits it, words that reject it)
GROUPS = {
    'nature_models': ('models', {'trees', 'plants', 'rocks', 'ground cover', 'flowers', 'grass', 'nature'}, (),
                      ('potted', 'moon', 'coast', 'succulent', 'iceplant', 'quiver', 'namaqualand', 'anthurium', 'calathea', 'pachira',
                       'garden_hose', 'heliophila', 'gazania', 'empodium', 'ursinia', 'stinkkruid', 'didelta', 'leipoldtia', 'othonna',
                       'searsia', 'rooibos', 'cheiridopsis', 'island_tree', 'sand_rocks')),
    'prop_models': ('models', {'industrial', 'containers', 'tools', 'structures', 'lighting', 'electronics', 'buildings'}, (),
                    ('lighthouse', 'chandelier', 'lamp_table', 'desk', 'kitchen', 'vintage', 'ornate', 'antique', 'gramophone', 'camera',
                     'telephone', 'television', 'radio', 'boombox', 'classic', 'chinese', 'japanese', 'baroque', 'ship', 'boat', 'cannon',
                     'treasure', 'food', 'wine', 'sword', 'katana', 'gun', 'lantern_chandelier')),
    'nature_textures': ('textures', {'bark', 'terrain', 'rock', 'sand', 'gravel', 'raw wood', 'natural', 'aerial'}, (),
                        ('snow', 'moon', 'coral', 'sandstone', 'brick', 'tiles', 'cobblestone', 'plaster', 'floor_tiles', 'pavement',
                         'palm', 'red_', 'volcanic', 'desert', 'beach', 'coast', 'parquet', 'laminate', 'plank_flooring', 'wood_floor')),
    'made_textures': ('textures', {'concrete', 'metal', 'asphalt', 'road', 'plaster-concrete', 'roofing', 'brick', 'fabric', 'tiles', 'plaster'}, (),
                      ('snow', 'moon', 'marble', 'carpet', 'wallpaper', 'denim', 'leather', 'wool', 'fleece', 'quilt', 'velvet', 'knit',
                       'herringbone', 'medieval', 'castle', 'church', 'mosaic', 'terrazzo', 'cobblestone', 'pavers', 'pavement', 'klinker',
                       'thatch', 'reed_roof', 'clay_roof', 'ceramic_roof', 'roof_tiles', 'stretchy', 'cotton', 'curtain', 'book')),
}


def get(url, binary=False):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': AGENT}), timeout=60) as response:
                data = response.read()
            return data if binary else json.loads(data)
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def megabytes(files, kind, res):
    try:
        if kind == 'models':
            main = files['gltf'][res]['gltf']
            return round((main['size'] + sum(v['size'] for v in main.get('include', {}).values())) / 1e6, 1)
        total = 0
        for name in ('Diffuse', 'nor_dx', 'arm', 'Displacement'):
            if name in files and res in files[name]:
                entry = files[name][res].get('jpg') or files[name][res].get('png')
                total += entry['size'] if entry else 0
        return round(total / 1e6, 1)
    except (KeyError, TypeError):
        return None


def sheets(group, rows, thumbs):
    """Contact sheets of a group's thumbnails, 8 across, in the rows' order. Some thumbnails are WebP under a .png name,
    so each is decoded on its own into a 200 px tile first; one that cannot be read keeps its place as a red tile."""
    tiles = OUT / 'tiles'
    tiles.mkdir(exist_ok=True)
    for row in rows:
        source, tile = thumbs / (row['id'] + '.png'), tiles / ('%s_%03d.png' % (group, row['index']))
        if tile.exists():
            continue
        kind = 'webp_pipe' if source.read_bytes()[:4] == b'RIFF' else 'png_pipe'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', kind, '-i', str(source), '-vf',
                        'scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x202020' % (CELL, CELL, CELL, CELL),
                        '-frames:v', '1', str(tile)], check=False)
        if not tile.exists():
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=red:s=%dx%d' % (CELL, CELL), '-frames:v', '1', str(tile)])
    per = COLUMNS * ROWS
    for sheet in range((len(rows) + per - 1) // per):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-start_number', str(sheet * per), '-i', str(tiles / (group + '_%03d.png')),
                        '-vf', 'tile=%dx%d:padding=4:color=0x000000' % (COLUMNS, ROWS), '-frames:v', '1', str(OUT / ('%s_%d.png' % (group, sheet)))], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    thumbs = OUT / 'thumbs'
    thumbs.mkdir(exist_ok=True)
    wanted = [a for a in sys.argv[1:] if not a.startswith('--')]
    for group, (kind, categories, words, reject) in GROUPS.items():
        if wanted and group not in wanted:
            continue
        assets = get('%s/assets?t=%s' % (API, kind))
        rows = []
        for key in sorted(assets):
            info = assets[key]
            text = (key + ' ' + ' '.join(info.get('tags', []))).lower()
            if not (set(info.get('categories', [])) & categories or any(w in text for w in words)):
                continue
            if any(w in key.lower() for w in reject):
                continue
            rows.append({'id': key, 'name': info.get('name'), 'categories': [c for c in info.get('categories', []) if not c.startswith('collection')]})
        for index, row in enumerate(rows):
            row['index'] = index
            files = get('%s/files/%s' % (API, row['id']))
            row['mb_2k'], row['mb_4k'] = megabytes(files, kind, '2k'), megabytes(files, kind, '4k')
            if kind == 'models':
                detail = get('%s/info/%s' % (API, row['id']))
                row['polycount'] = detail.get('polycount')
                row['size_m'] = [round(v / 1000.0, 2) for v in detail.get('dimensions', [])]
            else:
                row['maps'] = [m for m in ('Diffuse', 'nor_dx', 'arm', 'Displacement') if m in files]
            target = thumbs / (row['id'] + '.png')
            if not target.exists():
                target.write_bytes(get('https://cdn.polyhaven.com/asset_img/thumbs/%s.png?width=%d&height=%d' % (row['id'], CELL, CELL), binary=True))
            time.sleep(.05)
        (OUT / (group + '.json')).write_text(json.dumps(rows, indent=0))
        sheets(group, rows, thumbs)
        print('%-16s %3d candidates' % (group, len(rows)), flush=True)


if __name__ == '__main__':
    sys.exit(main())
