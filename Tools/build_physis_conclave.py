"""Generate the Conclave (level 3): every mesh of Tools/conclave_meshes as FBX, the floor's height grid and the
town and vegetation layout (Tools/conclave/README.md is the contract).

The generators are pure numpy modules (drum, architecture, districts, people, al_flora) that check.py validates
offline; this script only turns their Parts into Blender meshes and exports them, so a mesh is changed in its
module, never here. Coordinates are Unreal metres (x north, y east, z up); toolkit.Part.build() flips y for
Blender and the FBX export scales metres to centimetres.

Run (one heavy job at a time on this machine; check.py must pass for every module first):
  flatpak run org.blender.Blender -b --python Tools/build_physis_conclave.py -- [names] [--terrain] [--scatter]
    names      only build meshes whose name contains one of these words (any case); height and scatter stay as they are
    --terrain  build only the floor (SM_CD_Terrain_*, SM_CD_Water), height.bin + height.json and scatter.json
    --scatter  rebuild only scatter.json
Offline dry check (no Blender; numpy from the Kokoro venv), the same selection, nothing written:
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/build_physis_conclave.py --dry [names] [--terrain] [--scatter]
    builds every Part exactly as Blender would, runs check.py's checks on each, prints the counts, and (without names)
    the height and scatter report, keep-clear audit included.

Writes Art/Meshes/Conclave/<mesh>.fbx, height.bin, height.json and scatter.json; then the map art
(Tools/build_physis_conclave_map.py) and `conclave:import` in the editor. Exit status 1 if anything failed.
"""
import importlib
import sys
import time
import traceback
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MESH_DIR = ROOT / 'Tools/conclave_meshes'
OUT = ROOT / 'Art/Meshes/Conclave'
MODULES = ('drum', 'architecture', 'districts', 'people', 'al_flora')
TERRAIN_BUILDERS = ('terrain_tile', 'water')     # drum.py's floor: what --terrain rebuilds
OPTIONS = ('--dry', '--terrain', '--scatter')

sys.path.insert(0, str(ROOT / 'Content/Python'))
sys.path.insert(0, str(MESH_DIR))

try:
    import bpy
except ImportError:  # plain Python: only the dry check can run
    bpy = None

import toolkit  # noqa: E402
from check import check_part  # noqa: E402  (the offline validator's per-mesh checks, so the build enforces the same rules)


def arguments():
    """Words and options after Blender's '--' (Blender's own arguments come before it); in plain Python, all of them."""
    if bpy is not None:
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    else:
        argv = [a for a in sys.argv[1:] if a != '--']
    options = {a for a in argv if a.startswith('--')}
    unknown = sorted(options - set(OPTIONS))
    if unknown:
        raise SystemExit('unknown option %s (known: %s)' % (', '.join(unknown), ' '.join(OPTIONS)))
    return [a.lower() for a in argv if not a.startswith('--')], options


def load_modules(problems, names=MODULES):
    """Imports the generator modules; one that fails (or exposes no MESHES) is reported and the others still build."""
    modules = {}
    for name in names:
        try:
            module = importlib.import_module(name)
        except Exception as error:
            problems.append('%s: import failed: %s' % (name, ''.join(traceback.format_exception_only(type(error), error)).strip()))
            continue
        if not getattr(module, 'MESHES', None):
            problems.append('%s: exposes no MESHES' % name)
            continue
        modules[name] = module
    return modules


def parts(module, builders=None):
    """The module's Parts in MESHES order, each variant of a VARIANTS builder in turn, as check.py builds them.
    Yields (builder name, Part or None, error text, seconds)."""
    variants = getattr(module, 'VARIANTS', {})
    for builder in module.MESHES:
        if builders is not None and builder.__name__ not in builders:
            continue
        count = variants.get(builder, 0)
        for k in (range(count) if count else (None,)):
            start = time.time()
            try:
                part = builder(k) if count else builder()
            except Exception:
                label = builder.__name__ + ('(%d)' % k if count else '()')
                yield builder.__name__, None, '%s raised:\n%s' % (label, traceback.format_exc().rstrip()), time.time() - start
                continue
            yield builder.__name__, part, None, time.time() - start


def custom_normals(mesh, normals):
    """Sets per-vertex normals (Unreal axes, in the Part's vertex order) as the mesh's custom normals, which the FBX
    carries and the import keeps (FBXNIM_IMPORT_NORMALS). A terrain tile's are the whole grid's, so its edge is
    shaded as if its neighbour's faces were there."""
    n = np.asarray(normals, np.float64).copy()
    n[:, 1] *= -1                        # Unreal y east -> Blender -y, as Part.build() flips the vertices
    if hasattr(mesh, 'use_auto_smooth'):  # Blender before 4.1 applies custom normals only with auto smooth
        mesh.use_auto_smooth = True
    mesh.normals_split_custom_set_from_vertices(n.tolist())


def export(part, warnings):
    """Blender: the Part as a mesh object, written to OUT/<name>.fbx; the object and its mesh are freed either way."""
    try:
        ob = part.build()
    except Exception:   # build() makes the mesh (and last the object) as it goes: free what it left
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
        except Exception as error:   # the mesh is still right, only its tile seams shade a little apart
            warnings.append('%s: custom normals not set (%s: %s)' % (name, type(error).__name__, error))
    try:
        toolkit.export(ob, OUT)
    finally:
        left = bpy.data.objects.get(name)   # still in the scene only when the exporter raised
        if left is not None:
            bpy.data.objects.remove(left)
        # toolkit.export() removes the object only; the mesh data would stay as an orphan, and a full run holds a few
        # million triangles of them (this machine has been OOM-killed).
        bpy.data.meshes.remove(mesh)


def build_meshes(modules, words, terrain_only, dry, problems, warnings):
    """Builds (and unless dry, exports) every selected Part. Returns per-module stats."""
    stats, seen = {}, {}
    for name, module in modules.items():
        if terrain_only and name != 'drum':
            continue
        contract = getattr(module, 'CONTRACT', {})
        s = stats.setdefault(name, {'meshes': 0, 'tris': 0, 'verts': 0, 'refused': 0, 'seconds': 0.0})
        built = set()
        for builder, part, error, seconds in parts(module, TERRAIN_BUILDERS if terrain_only else None):
            s['seconds'] += seconds
            if part is None:
                problems.append('%s.%s' % (name, error))
                continue
            if not isinstance(part, toolkit.Part):
                problems.append('%s.%s returned %r, not a toolkit.Part' % (name, builder, type(part).__name__))
                continue
            built.add(part.name)
            if words and not any(w in part.name.lower() for w in words):
                continue
            if part.name in seen:
                problems.append('%s: name used twice (%s and %s); the second is not exported' % (part.name, seen[part.name], name))
                continue
            seen[part.name] = name
            found = []
            check_part(part, contract, found, True)
            normals = getattr(part, 'normals', None)
            if normals is not None:   # custom normals ride with the Part (terrain tiles): one per vertex, unit length
                n = np.asarray(normals, np.float64)
                if n.shape != (len(part.v), 3) or not np.isfinite(n).all() or np.abs(np.linalg.norm(n, axis=1) - 1).max() > 1e-3:
                    found.append('%s: normals must be one unit vector per vertex, got shape %s' % (part.name, n.shape))
            tris = part.triangles()
            if found:
                # An FBX that breaks the contract (a colour off the palette, a slot no face uses, which imports as a
                # stray WorldGridMaterial slot, a wrong pivot or size) would reach the level unnoticed: refuse it.
                problems.extend(found)
                s['refused'] += 1
                print('refused %-30s %s' % (part.name, '; '.join(found)), flush=True)
                continue
            start = time.time()
            if not dry:
                try:
                    export(part, warnings)
                except Exception:   # one exporter failure is reported; the rest of a long run still lands
                    problems.append('%s: export failed:\n%s' % (part.name, traceback.format_exc().rstrip()))
                    s['refused'] += 1
                    continue
            s['seconds'] += time.time() - start
            s['meshes'] += 1
            s['tris'] += tris
            s['verts'] += len(part.v)
            print('mesh %-30s %7d verts %7d faces %7d tris  %s  %.1f s' % (part.name, len(part.v), len(part.f), tris,
                                                                         ','.join(part.slots), seconds + time.time() - start), flush=True)
        missing = [n for n in contract if n not in built]
        if missing and not words and not terrain_only:
            problems.append('%s: CONTRACT names with no builder: %s' % (name, missing))
    return stats


def floor(modules, scatter_only, dry, problems):
    """height.bin + height.json (unless scatter_only) and scatter.json from drum.py, then its report (heights, road
    grades, plazas, moat, island, slopes, scatter counts, keep-clear audit). Dry: computed and reported, not written."""
    drum = modules.get('drum')
    if drum is None:
        problems.append('drum: not loaded, so no height grid or scatter')
        return None
    start = time.time()
    if not scatter_only:
        if dry:
            drum.grid()
        else:
            meta = drum.write_height(OUT)
            print('height %s/height.bin %d x %d, cell %.1f m' % (OUT, meta['nx'], meta['ny'], meta['cell']), flush=True)
    rows = drum.layout() if dry else drum.write_scatter(OUT)
    if not dry:
        print('scatter %s/scatter.json' % OUT, flush=True)
    stats = drum.report(rows)
    if stats.get('keep_clear_violations'):
        problems.append('scatter: keep-clear violations %s' % stats['keep_clear_violations'])
    print('floor %.1f s' % (time.time() - start), flush=True)
    return stats


def main():
    words, options = arguments()
    dry = '--dry' in options or bpy is None
    if bpy is None and '--dry' not in options:
        print('no bpy (plain Python): running the dry check, nothing is written', flush=True)
    start = time.time()
    problems, warnings = [], []
    if not dry:
        OUT.mkdir(parents=True, exist_ok=True)
        for ob in list(bpy.data.objects):     # the start-up scene's cube, camera and light
            bpy.data.objects.remove(ob)
    # The floor is drum.py's alone, so --terrain and --scatter do not wait on the other modules.
    modules = load_modules(problems, ('drum',) if options & {'--terrain', '--scatter'} else MODULES)
    stats = {}
    if '--scatter' in options:
        floor(modules, True, dry, problems)
    else:
        stats = build_meshes(modules, words, '--terrain' in options, dry, problems, warnings)
        if not words:
            floor(modules, False, dry, problems)

    print('\n%s summary (%s)' % ('dry' if dry else 'export', 'meshes matching ' + ' '.join(words) if words else 'all'))
    for name, s in stats.items():
        print('  %-13s %4d meshes %9d tris %9d verts  %d refused  %.1f s' % (name, s['meshes'], s['tris'], s['verts'], s['refused'], s['seconds']))
    if stats:
        print('  %-13s %4d meshes %9d tris' % ('total', sum(s['meshes'] for s in stats.values()), sum(s['tris'] for s in stats.values())))
    print('  %s in %.1f s' % ('checked, nothing written,' if dry else 'written to ' + str(OUT), time.time() - start))
    for w in warnings:   # written, but not as well as it could be
        print('  warning: ' + w)
    if problems:
        print('\nFAILED (%d):' % len(problems))
        for p in problems:
            print('  - ' + p.replace('\n', '\n    '))
        sys.exit(1)
    print('\nall built' if not dry else '\ndry check passed')


if __name__ == '__main__':
    main()
