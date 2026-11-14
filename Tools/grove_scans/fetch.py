"""Downloads the grove's CC0 photo-scanned assets (author's permission, 2026-11-10: Poly Haven and ambientCG, about
6-8 GB) into Art/Scans/Grove, and records every file in Art/Scans/Grove/manifest.json.

    python3 -I Tools/grove_scans/fetch.py PICKS.json [--dry] [--only ID[,ID...]] [--cap-gb 9]

PICKS.json is a list of rows:
    {"source": "polyhaven" | "ambientcg", "id": "fir_tree_01", "kind": "model" | "texture", "res": "2k",
     "purpose": "...", "use": "scatter" | "hero" | "dressing" | "surface" | "atlas" | "cliff", "priority": 1}

Poly Haven models come as glTF (a .gltf, its .bin and its textures; no .blend files, which can carry scripts), at the
row's texture resolution. A row of kind "texture" may name a MODEL's id: it then fetches only that model's maps (its
leaf or bark sheet, with Alpha where there is one), not its geometry. Poly Haven textures come as the maps Unreal uses: Diffuse, nor_dx (DirectX normals), arm
(ambient occlusion, roughness, metal packed in R, G, B) and Displacement, as jpg (png where no jpg exists).
ambientCG materials come as their <res>-JPG zip, unpacked here with every member's path checked.

Each asset gets its own folder, Art/Scans/Grove/<source>/<id>/, holding nothing else: downloaded files are data, so
no script lives beside them, and whatever reads them later is run from another folder. A file already there with the
listed size (and md5, where the source gives one) is kept, so the run can be repeated. Nothing outside the two
sources' own hosts is ever fetched.
"""
import hashlib
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Scans/Grove'
AGENT = 'physis-level-build/1.0 (game level build; CC0 asset fetch)'
HOSTS = ('api.polyhaven.com', 'dl.polyhaven.org', 'cdn.polyhaven.com', 'ambientcg.com', 'acg-download.struffelproductions.com',
         'acg-media.struffelproductions.com')
POLYHAVEN_MAPS = ('Diffuse', 'nor_dx', 'arm', 'Displacement', 'Rough', 'AO')   # the last two only when there is no arm
EXTRA_MAPS = ('Alpha', 'Translucent', 'Mask')   # a plant's cutout and translucency, when its sheet has them
LICENCE = 'CC0 1.0 (public domain dedication)'


def allowed(url):
    host = urllib.parse.urlparse(url).hostname or ''
    return url.startswith('https://') and (host in HOSTS or host.endswith('.polyhaven.org') or host.endswith('.polyhaven.com'))


def get(url, binary=False, tries=4):
    if not allowed(url):
        raise RuntimeError('refused: %s is not one of the permitted hosts' % url)
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                data = response.read()
            return data if binary else json.loads(data)
        except Exception as error:  # noqa: BLE001  (a dropped connection: wait, try again)
            if attempt == tries - 1:
                raise
            print('  retry %d: %s (%s)' % (attempt + 1, url.rsplit('/', 1)[-1], error), flush=True)
            time.sleep(3 * (attempt + 1))


def md5(path):
    digest = hashlib.md5()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def safe_relative(name):
    """A member or include path as a safe relative path (no absolute paths, no '..', no drive letters)."""
    parts = [p for p in pathlib.PurePosixPath(name.replace('\\', '/')).parts if p not in ('', '.', '/')]
    if not parts or any(p == '..' or ':' in p for p in parts):
        raise RuntimeError('unsafe path in download: %r' % name)
    return pathlib.Path(*parts)


def save(url, target, size=None, digest=None, dry=False):
    """Downloads url to target unless it is already there and matches. Returns (bytes, fetched)."""
    if target.exists() and (size is None or target.stat().st_size == size) and (digest is None or md5(target) == digest):
        return target.stat().st_size, False
    if dry:
        return size or 0, False
    target.parent.mkdir(parents=True, exist_ok=True)
    data = get(url, binary=True)
    if digest and hashlib.md5(data).hexdigest() != digest:
        raise RuntimeError('md5 mismatch for %s' % url)
    partial = target.with_suffix(target.suffix + '.part')
    partial.write_bytes(data)
    partial.replace(target)
    return len(data), True


def pick_format(entry, order=('jpg', 'png')):
    for ext in order:
        if ext in entry:
            return ext, entry[ext]
    return None, None


def polyhaven_model(row, folder, dry):
    files = get('https://api.polyhaven.com/files/' + row['id'])
    formats = files.get('gltf')
    if not formats:
        raise RuntimeError('no glTF for ' + row['id'])
    res = row.get('res', '2k') if row.get('res', '2k') in formats else sorted(formats, key=lambda r: int(r.rstrip('k')))[min(1, len(formats) - 1)]
    main = formats[res]['gltf']
    listed = [(main['url'].rsplit('/', 1)[-1], main)] + list(main.get('include', {}).items())
    out, total = [], 0
    for name, info in listed:
        size, _ = save(info['url'], folder / safe_relative(name), info.get('size'), info.get('md5'), dry)
        out.append({'file': str(safe_relative(name)), 'bytes': info.get('size', size), 'md5': info.get('md5'), 'url': info['url']})
        total += info.get('size', size)
    # A plant's cutout is not in its glTF (the colour map there is a jpg, which has no alpha): its Alpha / opacity map
    # is a file of its own, one per material ('Alpha', 'opacity', 'wire_alpha', ...). Saved beside the glTF's textures
    # under Poly Haven's own file name.
    for name, levels in files.items():
        if not isinstance(levels, dict) or name.lower().rsplit('_', 1)[-1] not in ('alpha', 'opacity'):
            continue
        level = res if res in levels else sorted(levels, key=lambda r: int(r.rstrip('k')))[min(1, len(levels) - 1)]
        ext, info = pick_format(levels[level], ('png', 'jpg'))
        if info is None:
            continue
        target = folder / 'textures' / safe_relative(info['url'].rsplit('/', 1)[-1])
        size, _ = save(info['url'], target, info.get('size'), info.get('md5'), dry)
        out.append({'file': str(target.relative_to(folder)), 'map': name, 'bytes': info.get('size', size), 'md5': info.get('md5'),
                    'url': info['url']})
        total += info.get('size', size)
    return {'res': res, 'format': 'gltf', 'files': out, 'bytes': total}


def polyhaven_texture(row, folder, dry):
    files = get('https://api.polyhaven.com/files/' + row['id'])
    res = row.get('res', '2k')
    maps = [m for m in POLYHAVEN_MAPS[:4] if m in files] + ([] if 'arm' in files else [m for m in POLYHAVEN_MAPS[4:] if m in files])
    maps += [m for m in EXTRA_MAPS if m in files]
    if row.get('maps'):          # a row may name exactly the maps it wants (a model's leaf sheet without its geometry)
        maps = [m for m in row['maps'] if m in files]
    out, total = [], 0
    for name in maps:
        levels = files[name]
        level = res if res in levels else sorted(levels, key=lambda r: int(r.rstrip('k')))[min(1, len(levels) - 1)]
        ext, info = pick_format(levels[level])
        if info is None:
            continue
        target = folder / ('%s_%s_%s.%s' % (row['id'], name, level, ext))
        size, _ = save(info['url'], target, info.get('size'), info.get('md5'), dry)
        out.append({'file': target.name, 'map': name, 'bytes': info.get('size', size), 'md5': info.get('md5'), 'url': info['url']})
        total += info.get('size', size)
    if not out or not (row.get('maps') or any(f['map'] == 'Diffuse' for f in out)):
        raise RuntimeError('no Diffuse map for ' + row['id'])
    return {'res': res, 'format': 'maps', 'files': out, 'bytes': total}


def ambientcg(row, folder, dry):
    query = urllib.parse.urlencode({'id': row['id'], 'include': 'downloadData', 'limit': 1})
    found = get('https://ambientcg.com/api/v2/full_json?' + query).get('foundAssets') or []
    if not found:
        raise RuntimeError('ambientCG has no asset ' + row['id'])
    want = '%s-JPG' % row.get('res', '2k').upper()
    downloads = []
    for folder_data in (found[0].get('downloadFolders') or {}).values():
        for category in (folder_data.get('downloadFiletypeCategories') or {}).values():
            downloads += category.get('downloads') or []
    chosen = next((d for d in downloads if d.get('attribute') == want), None) or next((d for d in downloads if 'JPG' in d.get('attribute', '')), None)
    if chosen is None:
        raise RuntimeError('ambientCG %s has no JPG download' % row['id'])
    url = chosen.get('downloadLink') or chosen.get('fullDownloadPath')
    archive = folder / (row['id'] + '_' + chosen['attribute'] + '.zip')
    size, fetched = save(url, archive, chosen.get('size'), None, dry)
    out = []
    if not dry:
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if member.is_dir():
                    continue
                target = folder / safe_relative(member.filename)
                if target.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.exr', '.tif', '.tiff'):
                    continue   # only image maps are unpacked (no .blend, .usdc, .mtlx or scripts)
                if not target.exists() or target.stat().st_size != member.file_size:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(bundle.read(member))
                out.append({'file': str(target.relative_to(folder)), 'bytes': member.file_size})
        archive.unlink()
    return {'res': chosen['attribute'], 'format': 'maps', 'files': out, 'bytes': chosen.get('size', size), 'url': url}


FETCH = {('polyhaven', 'model'): polyhaven_model, ('polyhaven', 'texture'): polyhaven_texture,
         ('ambientcg', 'texture'): ambientcg}
PAGE = {'polyhaven': 'https://polyhaven.com/a/%s', 'ambientcg': 'https://ambientcg.com/view?id=%s'}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv
    only = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
    cap = float(sys.argv[sys.argv.index('--cap-gb') + 1]) if '--cap-gb' in sys.argv else 9.0
    rows = json.loads(pathlib.Path(args[0]).read_text())
    manifest_path = OUT / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'licence': LICENCE, 'assets': {}}
    total, failed = sum(a.get('bytes', 0) for a in manifest['assets'].values()), []
    for row in sorted(rows, key=lambda r: (r.get('priority', 2), r['source'], r['id'])):
        key = '%s/%s' % (row['source'], row['id'])
        if only and row['id'] not in only:
            continue
        fetcher = FETCH.get((row['source'], row['kind']))
        if fetcher is None:
            failed.append((key, 'no fetcher for %s %s' % (row['source'], row['kind'])))
            continue
        if total / 1e9 > cap and key not in manifest['assets']:
            failed.append((key, 'skipped: the %.1f GB cap is reached' % cap))
            continue
        folder = OUT / row['source'] / safe_relative(row['id'])
        try:
            result = fetcher(row, folder, dry)
        except Exception as error:  # noqa: BLE001  (one asset failing must not stop the rest)
            failed.append((key, str(error)[:200]))
            print('FAILED %-40s %s' % (key, str(error)[:120]), flush=True)
            continue
        previous = manifest['assets'].get(key, {}).get('bytes', 0)
        total += result['bytes'] - previous
        entry = dict(row)
        entry.update(result)
        entry.update({'page': PAGE[row['source']] % row['id'], 'licence': LICENCE, 'fetched': time.strftime('%Y-%m-%d')})
        manifest['assets'][key] = entry
        print('%-8s %-44s %-5s %7.1f MB  (%5.2f GB so far)' % ('listed' if dry else 'ok', key, result['res'], result['bytes'] / 1e6, total / 1e9), flush=True)
        if not dry:
            OUT.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, indent=1))
    print('\n%d assets, %.2f GB%s' % (len(manifest['assets']), total / 1e9, ' (dry run: nothing written)' if dry else ''))
    for key, why in failed:
        print('  not fetched:', key, '-', why)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
