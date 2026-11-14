"""Turns the downloaded photo-scanned models into the grove's game meshes (Blender 5, headless).

  flatpak-spawn --host flatpak run --filesystem=home org.blender.Blender -b --factory-startup --python-exit-code 1 \\
      --python /home/precosmos/PhysisProject/Tools/grove_scans/process.py -- [WORD ...] [--render] [--list]

Tools/grove_scans/models.py says which meshes come out of which model. For each row this script imports the model's
glTF (Art/Scans/Grove/polyhaven/<id>/), merges the row's nodes where the model's own layout puts them, turns the
scan's front to +x, scales it, welds and decimates it to its triangle budget (giving the result the original's
normals, so the scan's normal map still fits), sets the pivot, names each material slot GS_<material> and writes

    Art/Meshes/Grove/Scans/SM_GS_<mesh>.fbx     metres to centimetres on export, like the generated meshes
    Art/Meshes/Grove/Scans/scans.json           {'meshes': {mesh: facts}, 'materials': {slot: facts}}

A mesh's facts: source, nodes, tris (and the scan's own), min / max / size in metres on Unreal's axes, use, collide,
cull, shadow, slots. A material's facts: blend ('opaque', 'masked' or 'glass'), tex (px), the maps' files (D colour,
A cutout, N normal in OpenGL convention, ARM, E emissive) relative to Art/Scans/Grove, and the glTF factors.
Tools/grove_scans/prepare.py --models then writes the textures, and grove:scans imports both.

WORD limits the run to meshes or sources whose name contains it (scans.json keeps the others' facts).
--render also writes Saved/Grove/render/scans/<mesh>.png, lit like lookdev.py, to judge a mesh before import.
--list prints the rows and stops. The model files are data: nothing in them is executed, and this script lives apart
from them.
"""
import json
import math
import re
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/grove_scans'))
import models  # noqa: E402

SCANS = ROOT / 'Art/Scans/Grove'
OUT = ROOT / 'Art/Meshes/Grove/Scans'
RENDERS = ROOT / 'Saved/Grove/render/scans'
SLACK = 1.2          # a scan up to a fifth over its budget is left as it is
GLASS = 'GS_Glass'   # every clear glass shares one material


def clean(name):
    """A material's name without Blender's duplicate suffix, safe as an asset name."""
    return re.sub(r'[^A-Za-z0-9_]', '_', re.sub(r'\.\d{3}$', '', name))


def gltf_materials(asset):
    """{glTF material name: facts} from the model's own JSON (first of each name wins)."""
    folder = SCANS / 'polyhaven' / asset
    path = next(folder.glob('*.gltf'))
    data = json.loads(path.read_text())

    def uri(info):
        if not info:
            return None
        image = data['images'][data['textures'][info['index']]['source']]
        return image.get('uri')

    def beside(colour, word):
        """The map Poly Haven names like the colour map with 'diff' replaced (the cutout is a file of its own)."""
        if not colour:
            return None
        base = Path(colour).name
        for ext in ('.png', '.jpg'):
            for stem in (re.sub(r'_diff_', '_%s_' % word, base), re.sub(r'_diff_', '_%s_' % word.capitalize(), base)):
                candidate = folder / 'textures' / (Path(stem).stem + ext)
                if stem != base and candidate.exists():
                    return 'textures/' + candidate.name
        return None

    out = {}
    for m in data.get('materials', []):
        name = clean(m.get('name', 'material'))
        if name in out:
            continue
        pbr = m.get('pbrMetallicRoughness', {})
        colour = uri(pbr.get('baseColorTexture'))
        mode = m.get('alphaMode', 'OPAQUE')
        cutout = (beside(colour, 'alpha') or beside(colour, 'opacity')) if mode != 'OPAQUE' else None
        if mode == 'BLEND' and 'glass' in name.lower():
            blend = 'glass'
        elif mode != 'OPAQUE' and (cutout or (colour or '').lower().endswith('.png')):
            blend = 'masked'
        else:
            blend = 'opaque'
        maps = {'D': colour, 'A': cutout, 'N': uri(m.get('normalTexture')), 'ARM': uri(pbr.get('metallicRoughnessTexture')),
                'AO': uri(m.get('occlusionTexture')), 'E': uri(m.get('emissiveTexture'))}
        strength = (m.get('extensions', {}).get('KHR_materials_emissive_strength', {}) or {}).get('emissiveStrength', 1.0)
        out[name] = {'model': asset, 'blend': blend, 'two_sided': blend == 'masked',
                     'maps': {k: 'polyhaven/%s/%s' % (asset, v) for k, v in maps.items() if v},
                     'factors': {'colour': pbr.get('baseColorFactor', [1, 1, 1, 1]), 'metallic': pbr.get('metallicFactor', 1.0),
                                 'roughness': pbr.get('roughnessFactor', 1.0), 'emissive': m.get('emissiveFactor', [0, 0, 0]),
                                 'emissive_strength': strength, 'cutoff': m.get('alphaCutoff', .5)}}
    return path, out


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def triangles(mesh):
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


def override(ob, others=()):
    picked = [ob] + [o for o in others if o is not ob]
    for o in bpy.context.view_layer.objects:
        o.select_set(o in picked)
    bpy.context.view_layer.objects.active = ob
    return bpy.context.temp_override(object=ob, active_object=ob, selected_objects=picked, selected_editable_objects=picked)


def gather(nodes, pattern):
    """Copies of the matching nodes with their world transforms applied, joined into one object. Returns it and the
    first node's origin (a plant's root)."""
    chosen = [ob for ob in nodes if pattern is None or re.search(pattern, ob.name)]
    if not chosen:
        return None, None
    origin = chosen[0].matrix_world.translation.copy()
    copies = []
    for ob in chosen:
        dup = ob.copy()
        dup.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(dup)
        if dup.data.shape_keys:          # a scan saved with morph targets: modifiers cannot be applied over them
            dup.shape_key_clear()
        world = ob.matrix_world.copy()
        dup.parent = None
        dup.matrix_world = Matrix.Identity(4)
        dup.data.transform(world)
        if world.determinant() < 0:
            dup.data.flip_normals()
        copies.append(dup)
    target = copies[0]
    if len(copies) > 1:
        with override(target, copies):
            bpy.ops.object.join()
    return target, origin


def apply(ob, kind, **settings):
    mod = ob.modifiers.new(kind.title(), kind)
    for key, value in settings.items():
        setattr(mod, key, value)
    with override(ob):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def reduce(ob, budget, notes):
    """Welds and decimates ob to about `budget` triangles and gives it the original's normals."""
    before = triangles(ob.data)
    source = ob.copy()
    source.data = ob.data.copy()
    bpy.context.scene.collection.objects.link(source)
    try:
        apply(ob, 'WELD', merge_threshold=1e-5)
        apply(ob, 'DECIMATE', decimate_type='COLLAPSE', ratio=min(1.0, budget / max(triangles(ob.data), 1)), use_collapse_triangulate=True)
        ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
        try:
            apply(ob, 'DATA_TRANSFER', object=source, use_loop_data=True, data_types_loops={'CUSTOM_NORMAL'}, loop_mapping='POLYINTERP_NEAREST')
        except Exception as error:   # noqa: BLE001  (smooth shading is the fallback)
            notes.append('normals not transferred: %s' % str(error)[:80])
    finally:
        mesh = source.data
        bpy.data.objects.remove(source)
        bpy.data.meshes.remove(mesh)
    return before


def place(ob, origin, row):
    """Front to +x, scale, pivot. Returns (min, max) on Unreal's axes, metres."""
    scale = row['scale']
    turn = Matrix.Rotation(math.pi / 2, 4, 'Z') @ Matrix.Scale(scale, 4)
    mesh = ob.data
    if row['pivot'] == 'origin':
        mesh.transform(Matrix.Translation(-origin))
    mesh.transform(turn)
    count = len(mesh.vertices)
    co = np.zeros(count * 3)
    mesh.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    lo, hi = co.min(0), co.max(0)
    if row['pivot'] == 'base':
        shift = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])
    elif row['pivot'] == 'top':
        shift = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -hi[2])
    else:
        shift = (0.0, 0.0, 0.0)
    mesh.transform(Matrix.Translation(shift))
    lo, hi = lo + shift, hi + shift
    mesh.update()
    return [float(lo[0]), float(-hi[1]), float(lo[2])], [float(hi[0]), float(-lo[1]), float(hi[2])]


def name_slots(ob, facts):
    """Material slots renamed GS_<material> (glass: GS_Glass), duplicates merged, unused ones removed."""
    mesh = ob.data
    index = np.zeros(len(mesh.polygons), np.int32)
    mesh.polygons.foreach_get('material_index', index)
    wanted, remap = [], {}
    for i, slot in enumerate(ob.material_slots):
        base = clean(slot.material.name) if slot.material else 'none'
        base = base[3:] if base.startswith('GS_') else base
        name = GLASS if facts.get(base, {}).get('blend') == 'glass' else 'GS_' + base
        if name not in wanted:
            wanted.append(name)
        remap[i] = wanted.index(name)
        material = bpy.data.materials.get(name)
        if material is None:
            material = slot.material if slot.material and not slot.material.name.startswith('GS_') else bpy.data.materials.new(name)
            material.name = name
        slot.material = material
    index = np.array([remap.get(int(i), 0) for i in index], np.int32)
    for i, name in enumerate(wanted):
        ob.material_slots[i].material = bpy.data.materials[name]
    mesh.polygons.foreach_set('material_index', index)
    mesh.update()
    with override(ob):
        bpy.ops.object.material_slot_remove_unused()
    return [slot.material.name for slot in ob.material_slots]


def cutouts(facts):
    """For the look-dev render only: a masked material takes its cutout map (the glTF's jpg colour has no alpha)."""
    for name, row in facts.items():
        material = bpy.data.materials.get('GS_' + name)
        if material is None or row['blend'] != 'masked' or 'A' not in row['maps'] or not material.use_nodes:
            continue
        nodes, links = material.node_tree.nodes, material.node_tree.links
        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(SCANS / row['maps']['A']), check_existing=True)
        tex.image.colorspace_settings.name = 'Non-Color'
        for link in list(bsdf.inputs['Alpha'].links):
            links.remove(link)
        links.new(tex.outputs['Color'], bsdf.inputs['Alpha'])


def export(ob, name):
    ob.name = name
    ob.data.name = name
    with override(ob):
        bpy.ops.export_scene.fbx(filepath=str(OUT / (name + '.fbx')), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                                 mesh_smooth_type='FACE', add_leaf_bones=False, object_types={'MESH'}, colors_type='LINEAR',
                                 use_tspace=False, axis_forward='-Z', axis_up='Y')


def render(ob, scene_setup, frame):
    scene = bpy.context.scene
    if scene.world is None or scene.world.name != 'Sky':
        scene_setup(560, 24)
    for other in bpy.context.scene.collection.objects:
        other.hide_render = other is not ob
    cam, lo = frame(scene, ob)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, float(lo[2]) - .002))
    plane = bpy.context.active_object
    ground = bpy.data.materials.new('Ground')
    ground.use_nodes = True
    next(n for n in ground.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (.06, .055, .045, 1)
    plane.data.materials.append(ground)
    scene.render.filepath = str(RENDERS / (ob.name + '.png'))
    bpy.ops.render.render(write_still=True)
    for item in (plane, cam):
        bpy.data.objects.remove(item)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    words = [a.lower() for a in argv if not a.startswith('--')]
    rows = [r for r in models.rows() if not words or any(w in r['mesh'].lower() or w in r['source'].lower() for w in words)]
    if '--list' in argv:
        for r in rows:
            print('%-22s %-32s %-7s tris %-6d tex %-5d %s' % (r['mesh'], r['source'], r['use'], r['tris'], r['tex'], r['nodes'] or '*'))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    facts_path = OUT / 'scans.json'
    facts = json.loads(facts_path.read_text()) if facts_path.exists() else {'meshes': {}, 'materials': {}}
    lookdev = None
    if '--render' in argv:
        RENDERS.mkdir(parents=True, exist_ok=True)
        import lookdev   # noqa: E402  (its scene and camera set-up)
    failed = []
    by_source = {}
    for r in rows:
        by_source.setdefault(r['source'], []).append(r)
    for source, group in by_source.items():
        try:
            path, materials = gltf_materials(source)
        except Exception as error:   # noqa: BLE001
            failed.append('%s: %s' % (source, error))
            continue
        reset()
        bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=False)
        bpy.context.view_layer.update()
        nodes = [ob for ob in bpy.data.objects if ob.type == 'MESH']
        for row in group:
            notes = []
            try:
                ob, origin = gather(nodes, row['nodes'])
                if ob is None:
                    failed.append('%s: no node of %s matches %r (it has %s)' % (row['mesh'], source, row['nodes'], sorted(o.name for o in nodes)[:12]))
                    continue
                own = triangles(ob.data)
                if row['tris'] and own > row['tris'] * SLACK:
                    reduce(ob, row['tris'], notes)
                lo, hi = place(ob, origin, row)
                slots = name_slots(ob, materials)
                export(ob, row['mesh'])
                tris = triangles(ob.data)
                facts['meshes'][row['mesh']] = {
                    'source': 'polyhaven/' + source, 'nodes': row['nodes'] or '*', 'tris': tris, 'tris_scan': own, 'min': [round(v, 4) for v in lo],
                    'max': [round(v, 4) for v in hi], 'size': [round(b - a, 4) for a, b in zip(lo, hi)], 'use': row['use'],
                    'collide': row['collide'], 'cull': row['cull'], 'shadow': row['shadow'], 'scale': row['scale'], 'slots': slots, 'notes': notes}
                for slot in slots:
                    if slot == GLASS:
                        facts['materials'][GLASS] = {'blend': 'glass', 'maps': {}, 'tex': 0}
                        continue
                    entry = dict(materials.get(slot[3:], {'blend': 'opaque', 'maps': {}, 'two_sided': False, 'factors': {}}))
                    entry['tex'] = row['tex']   # settled over every mesh that wears it, below
                    facts['materials'][slot] = entry
                if lookdev is not None:
                    cutouts(materials)
                    render(ob, lookdev.scene_setup, lookdev.frame)
                print('%-22s %7d -> %6d tris  %5.2f x %5.2f x %5.2f m  %s %s' % (row['mesh'], own, tris, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2],
                                                                                 ','.join(slots), '; '.join(notes)), flush=True)
                mesh = ob.data
                bpy.data.objects.remove(ob)
                bpy.data.meshes.remove(mesh)
            except Exception as error:   # noqa: BLE001  (one mesh failing must not stop the rest)
                failed.append('%s: %s: %s' % (row['mesh'], type(error).__name__, str(error)[:200]))
        facts_path.write_text(json.dumps(facts, indent=1, sort_keys=True))
    # A texture size is the largest any of its meshes asks for: recompute over every mesh in the table, so a partial
    # run cannot shrink one.
    want = {}
    for r in models.rows():
        for slot in facts['meshes'].get(r['mesh'], {}).get('slots', []):
            want[slot] = max(want.get(slot, 0), r['tex'])
    for slot, size in want.items():
        if slot in facts['materials'] and slot != GLASS:
            facts['materials'][slot]['tex'] = size
    used = {slot for m in facts['meshes'].values() for slot in m['slots']}
    facts['materials'] = {k: v for k, v in facts['materials'].items() if k in used}
    facts_path.write_text(json.dumps(facts, indent=1, sort_keys=True))
    print('\n%d meshes, %d materials in %s' % (len(facts['meshes']), len(facts['materials']), facts_path))
    for line in failed:
        print('  FAILED', line)
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
