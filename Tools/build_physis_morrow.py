"""Generate Morrow, the Valley Before Morning (level 8): every mesh of Tools/morrow_meshes as FBX, the valley's height grid
and the scatter layout (Tools/morrow/README.md is the contract).

The generators are pure numpy modules (land, structures, figures) that Tools/morrow_meshes/check.py validates
offline; this script only turns their Parts into Blender meshes and exports them, so a mesh is changed in its module,
never here. Coordinates are Unreal metres (x north, y east, z up); toolkit.Part.build() flips y for Blender and the
FBX export scales metres to centimetres.

Run (one heavy job at a time on this machine; check.py must pass for every module first):
  /usr/bin/blender -b --factory-startup --python-exit-code 1 --python Tools/build_physis_morrow.py -- [names] [--terrain] [--scatter]
    names      only build meshes whose name contains one of these words (any case); height and scatter stay as they are
    --terrain  build only the land (SM_OT_*), height.bin + height.json and scatter.json
    --scatter  rebuild only scatter.json
Offline dry check (no Blender), the same selection, nothing written:
  python3 Tools/build_physis_morrow.py --dry [names]

Writes Art/Meshes/Morrow/<mesh>.fbx, height.bin, height.json and scatter.json; then the map art
(Tools/build_physis_morrow_map.py) and `morrow:import` in the editor. Exit status 1 if anything failed.
"""
import importlib
import importlib.util
import sys
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MESH_DIR = ROOT / 'Tools/morrow_meshes'
OUT = ROOT / 'Art/Meshes/Morrow'
MODULES = ('land', 'structures', 'figures')
OPTIONS = ('--dry', '--terrain', '--scatter')

sys.path.insert(0, str(MESH_DIR))
import kit  # noqa: E402,F401  (puts the Conclave toolkit behind the Grove's own modules on the path)
import toolkit  # noqa: E402

try:
    import bpy
except ImportError:  # plain Python: only the dry check can run
    bpy = None


def morrow_check():
    """Tools/morrow_meshes/check.py by its path (the Conclave has a check.py too)."""
    spec = importlib.util.spec_from_file_location('morrow_check', MESH_DIR / 'check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arguments():
    if bpy is not None:
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    else:
        argv = [a for a in sys.argv[1:] if a != '--']
    options = {a for a in argv if a.startswith('--')}
    unknown = sorted(options - set(OPTIONS))
    if unknown:
        raise SystemExit('unknown option %s (known: %s)' % (', '.join(unknown), ' '.join(OPTIONS)))
    return [a.lower() for a in argv if not a.startswith('--')], options


def parts(module):
    variants = getattr(module, 'VARIANTS', {})
    for builder in module.MESHES:
        count = variants.get(builder, 0)
        for k in (range(count) if count else (None,)):
            start = time.time()
            try:
                part = builder(k) if count else builder()
            except Exception:
                yield builder.__name__, None, '%s raised:\n%s' % (builder.__name__, traceback.format_exc().rstrip()), time.time() - start
                continue
            yield builder.__name__, part, None, time.time() - start


def custom_normals(mesh, normals):
    """Per-vertex normals (Unreal axes, the Part's vertex order) as the mesh's custom normals: terrain tiles carry the
    whole grid's, plants with atlas cards their canopy's."""
    n = np.asarray(normals, np.float64).copy()
    n[:, 1] *= -1
    if hasattr(mesh, 'use_auto_smooth'):
        mesh.use_auto_smooth = True
    mesh.normals_split_custom_set_from_vertices(n.tolist())


def export(part, warnings):
    try:
        ob = part.build()
    except Exception:
        for collection in (bpy.data.objects, bpy.data.meshes):
            left = collection.get(part.name)
            if left is not None:
                collection.remove(left)
        raise
    name, mesh = ob.name, ob.data
    normals = getattr(part, 'normals', None)
    if normals is not None:
        try:
            custom_normals(mesh, normals)
        except Exception as error:
            warnings.append('%s: custom normals not set (%s: %s)' % (name, type(error).__name__, error))
    try:
        toolkit.export(ob, OUT)
    finally:
        left = bpy.data.objects.get(name)
        if left is not None:
            bpy.data.objects.remove(left)
        bpy.data.meshes.remove(mesh)


def main():
    words, options = arguments()
    dry = '--dry' in options or bpy is None
    start = time.time()
    problems, warnings, stats, seen = [], [], {}, {}
    check = morrow_check()
    if not dry:
        OUT.mkdir(parents=True, exist_ok=True)
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob)
    names = ('land',) if options & {'--terrain', '--scatter'} else MODULES
    modules = {}
    for name in names:
        try:
            modules[name] = importlib.import_module(name)
        except Exception as error:
            problems.append('%s: import failed: %s' % (name, ''.join(traceback.format_exception_only(type(error), error)).strip()))
    if '--scatter' not in options:
        for name, module in modules.items():
            contract = getattr(module, 'CONTRACT', {})
            s = stats.setdefault(name, {'meshes': 0, 'tris': 0, 'refused': 0})
            for builder, part, error, seconds in parts(module):
                if part is None:
                    problems.append('%s.%s' % (name, error))
                    continue
                if words and not any(w in part.name.lower() for w in words):
                    continue
                if part.name in seen:
                    problems.append('%s: name used twice (%s and %s)' % (part.name, seen[part.name], name))
                    continue
                seen[part.name] = name
                found = []
                check.check_part(part, contract, found, True)
                normals = getattr(part, 'normals', None)
                if normals is not None and np.asarray(normals).shape != (len(part.v), 3):
                    found.append('%s: normals must be one per vertex' % part.name)
                if found:
                    problems.extend(found)
                    s['refused'] += 1
                    print('refused %-28s %s' % (part.name, '; '.join(found)), flush=True)
                    continue
                if not dry:
                    try:
                        export(part, warnings)
                    except Exception:
                        problems.append('%s: export failed:\n%s' % (part.name, traceback.format_exc().rstrip()))
                        s['refused'] += 1
                        continue
                s['meshes'] += 1
                s['tris'] += part.triangles()
                print('mesh %-28s %7d verts %7d tris  %s  %.1f s' % (part.name, len(part.v), part.triangles(), ','.join(part.slots), seconds), flush=True)
    land = modules.get('land')
    if land is not None and not words:
        if '--scatter' not in options and not dry:
            meta = land.write_height(OUT)
            print('height %d x %d, cell %.1f m' % (meta['nx'], meta['ny'], meta['cell']), flush=True)
        rows = land.layout() if dry else land.write_scatter(OUT)
        land.report(rows)
    print('\n%s summary' % ('dry' if dry else 'export'))
    for name, s in stats.items():
        print('  %-11s %4d meshes %9d tris  %d refused' % (name, s['meshes'], s['tris'], s['refused']))
    print('  %s in %.1f s' % ('checked, nothing written,' if dry else 'written to ' + str(OUT), time.time() - start))
    for w in warnings:
        print('  warning: ' + w)
    if problems:
        print('\nFAILED (%d):' % len(problems))
        for p in problems:
            print('  - ' + p.replace('\n', '\n    '))
        sys.exit(1)
    print('\nall built' if not dry else '\ndry check passed')


if __name__ == '__main__':
    main()
