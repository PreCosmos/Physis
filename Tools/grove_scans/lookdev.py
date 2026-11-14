"""Look-dev renders of the grove's generated meshes in their scanned textures (Blender 5, Cycles on the CPU), so a
mesh can be judged as it will look in the game before it is imported: the same slot-to-scan table as Unreal's side
(Tools/grove_meshes/looks.py), triplanar ("box") projection for surfaces, leaf sheets through the cards' uvs.

  flatpak-spawn --host flatpak run --filesystem=home org.blender.Blender -b --factory-startup --python-exit-code 1 \\
      --python /home/precosmos/PhysisProject/Tools/grove_scans/lookdev.py -- MODULE [NAME ...] [--size 900] [--samples 40] [--back] [--close]

MODULE is a generator module (flora, structures, machines, _sample); NAME filters meshes by a word in their name.
Writes Saved/Grove/render/<mesh>.png (with --back also <mesh>_back.png; --close frames the lowest 4 m, for a tall
tree's trunk and roots). One Blender at a time on this machine.
An approximation, not the game: bumps come from the scans' brightness here (Unreal uses their normal maps), and the
light is a plain late-afternoon sky.
"""
import importlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/grove_meshes'))
import kit  # noqa: E402,F401
import looks  # noqa: E402

TEXTURES = ROOT / 'Art/Scans/Grove/_ready/textures'
SETS = json.loads((ROOT / 'Art/Scans/Grove/_ready/sets.json').read_text()) if (ROOT / 'Art/Scans/Grove/_ready/sets.json').exists() else {}
OUT = ROOT / 'Saved/Grove/render'


def image(name, kind, colour=True):
    for ext in ('png', 'jpg'):
        path = TEXTURES / ('T_GRS_%s_%s.%s' % (name, kind, ext))
        if path.exists():
            img = bpy.data.images.load(str(path), check_existing=True)
            if not colour:
                img.colorspace_settings.name = 'Non-Color'
            return img
    return None


def material(mesh_name, slot):
    set_name, mode, ref, rough, metal = looks.look(mesh_name, slot)
    mat = bpy.data.materials.new('%s:%s' % (mesh_name, slot))
    mat.use_nodes = True
    tree = mat.node_tree
    nodes, links = tree.nodes, tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    vc = nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Col'

    def mix(kind, a, b, factor=1.0):
        node = nodes.new('ShaderNodeMix')
        node.data_type = 'RGBA'
        node.blend_type = kind
        node.inputs[0].default_value = factor if not hasattr(factor, 'node') else 1.0
        if hasattr(factor, 'node'):
            links.new(factor, node.inputs[0])
        for socket, value in ((node.inputs[6], a), (node.inputs[7], b)):
            if hasattr(value, 'node'):
                links.new(value, socket)
            else:
                socket.default_value = tuple(value) + (1.0,) if len(value) == 3 else value
        return node.outputs[2]

    def boxed(img):
        coord = nodes.new('ShaderNodeTexCoord')
        mapping = nodes.new('ShaderNodeMapping')
        tile = (SETS.get(set_name) or {}).get('tile_m') or 2.0
        mapping.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1 / tile)
        links.new(coord.outputs['Object'], mapping.inputs['Vector'])
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = img
        tex.projection = 'BOX'
        tex.projection_blend = .25
        links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
        return tex

    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    base = image(set_name, 'D') if set_name else None
    if mode == 'glow':
        bsdf.inputs['Base Color'].default_value = (0, 0, 0, 1)
        links.new(vc.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 6.0
    elif mode == 'glass':
        bsdf.inputs['Transmission Weight'].default_value = .9
        links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
    elif mode == 'leaf' and base is not None:
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = base
        tinted = mix('MULTIPLY', tex.outputs['Color'], vc.outputs['Color'])
        gain = mix('MULTIPLY', tinted, (1.6, 1.6, 1.6))
        colour = mix('MIX', gain, vc.outputs['Color'], vc.outputs['Alpha'])     # vertex alpha 1: a solid twig, plain
        links.new(colour, bsdf.inputs['Base Color'])
        alpha = nodes.new('ShaderNodeMix')
        alpha.data_type = 'FLOAT'
        links.new(vc.outputs['Alpha'], alpha.inputs[0])
        links.new(tex.outputs['Alpha'], alpha.inputs[2])
        alpha.inputs[3].default_value = 1.0
        links.new(alpha.outputs[0], bsdf.inputs['Alpha'])
        bsdf.inputs['Subsurface Weight'].default_value = 0.0
    elif mode in ('tint', 'paint') and base is not None:
        tex = boxed(base)
        if mode == 'tint':
            scale = [1.0 / max(c, .02) for c in (ref or (.5, .5, .5))]
            ratio = mix('MULTIPLY', vc.outputs['Color'], scale)
            colour = mix('MULTIPLY', tex.outputs['Color'], ratio)
        else:
            sep = nodes.new('ShaderNodeSeparateColor')
            sep.mode = 'HSV'
            links.new(tex.outputs['Color'], sep.inputs[0])
            value = nodes.new('ShaderNodeCombineColor')
            for k in range(3):
                links.new(sep.outputs[2], value.inputs[k])
            painted = mix('MULTIPLY', vc.outputs['Color'], value.outputs[0])
            painted = mix('MULTIPLY', painted, (1.35, 1.35, 1.35))
            ramp = nodes.new('ShaderNodeMapRange')
            ramp.inputs['From Min'].default_value, ramp.inputs['From Max'].default_value = .28, .5
            links.new(sep.outputs[1], ramp.inputs['Value'])
            colour = mix('MIX', painted, tex.outputs['Color'], ramp.outputs['Result'])   # saturated texels are rust: keep them
        links.new(colour, bsdf.inputs['Base Color'])
        arm = image(set_name, 'ARM', False)
        if arm is not None:
            packed = boxed(arm)
            parts = nodes.new('ShaderNodeSeparateColor')
            links.new(packed.outputs['Color'], parts.inputs[0])
            links.new(parts.outputs[1], bsdf.inputs['Roughness'])
            if metal > 0:
                links.new(parts.outputs[2], bsdf.inputs['Metallic'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .5
        bump.inputs['Distance'].default_value = .02
        links.new(tex.outputs['Color'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    else:
        links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def scene_setup(size, samples):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = size, int(size * .8)
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX' if 'AgX' in [v.name for v in type(scene.view_settings).bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    world = bpy.data.worlds.new('Sky')
    scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    background = next(n for n in nodes if n.type == 'BACKGROUND')
    sky = nodes.new('ShaderNodeTexSky')
    for key, value in (('sun_elevation', math.radians(32)), ('sun_rotation', math.radians(-40)), ('sun_intensity', 1.0)):
        try:
            setattr(sky, key, value)
        except Exception:
            pass
    links.new(sky.outputs['Color'], background.inputs['Color'])
    background.inputs['Strength'].default_value = .06
    return scene


def frame(scene, ob, back=False, close=False):
    """A camera looking at the object's three-quarter front (Blender x forward, like the mesh's +x)."""
    box = np.array([ob.matrix_world @ __import__('mathutils').Vector(c) for c in ob.bound_box])
    lo, hi = box.min(0), box.max(0)
    if close:
        hi[2] = min(hi[2], lo[2] + 4.0)
        centre_xy = np.zeros(2)
        lo[:2], hi[:2] = np.maximum(lo[:2], centre_xy - 5), np.minimum(hi[:2], centre_xy + 5)
    centre = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) / 2
    cam_data = bpy.data.cameras.new('Cam')
    cam_data.lens = 60
    cam = bpy.data.objects.new('Cam', cam_data)
    scene.collection.objects.link(cam)
    az, el = math.radians(215 if back else 35), math.radians(14)
    distance = radius / math.tan(cam_data.angle / 2) * 1.12
    # the Part was built with y flipped (Unreal's +y is Blender's -y), so the camera stands on the -y side for azimuth > 0
    offset = np.array([math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), math.sin(el)]) * distance
    cam.location = tuple(centre + offset)
    direction = __import__('mathutils').Vector(tuple(-offset))
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    cam_data.clip_end = distance * 4 + 100
    scene.camera = cam
    return cam, lo


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    value = lambda flag, default: int(argv[argv.index(flag) + 1]) if flag in argv else default   # noqa: E731
    size, samples = value('--size', 900), value('--samples', 40)
    words = [a.lower() for a in argv if not a.startswith('--') and not a.isdigit()]
    module_name, words = words[0], words[1:]
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    scene = scene_setup(size, samples)
    module = importlib.import_module(module_name)
    variants = getattr(module, 'VARIANTS', {})
    OUT.mkdir(parents=True, exist_ok=True)
    ground_mat = bpy.data.materials.new('Ground')
    ground_mat.use_nodes = True
    next(n for n in ground_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (.035, .033, .027, 1)
    # A word picks builders by their function name when it names one (so the rest are not even built), else meshes by
    # their own name.
    squash = lambda text: text.replace('_', '').lower()   # noqa: E731
    by_function = [b for b in module.MESHES if any(squash(w) in squash(b.__name__) for w in words)]
    for builder in (by_function or module.MESHES):
        count = variants.get(builder, 0)
        for k in (range(count) if count else (None,)):
            part = builder(k) if count else builder()
            named = any(squash(w) in squash(part.name) for w in words)
            if words and not named and (not by_function or count):
                continue
            ob = part.build()
            if getattr(part, 'normals', None) is not None:
                n = np.asarray(part.normals, np.float64).copy()
                n[:, 1] *= -1
                ob.data.normals_split_custom_set_from_vertices(n.tolist())
            for index, slot in enumerate(part.slots):
                ob.data.materials[index] = material(part.name, slot)
            cam, lo = frame(scene, ob, close='--close' in argv)
            bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, float(lo[2]) - .002))
            plane = bpy.context.active_object
            plane.data.materials.append(ground_mat)
            scene.render.filepath = str(OUT / (part.name + ('_close' if '--close' in argv else '') + '.png'))
            bpy.ops.render.render(write_still=True)
            print('rendered', scene.render.filepath, flush=True)
            if '--back' in argv:
                bpy.data.objects.remove(cam)
                cam, _ = frame(scene, ob, back=True, close='--close' in argv)
                scene.render.filepath = str(OUT / (part.name + '_back.png'))
                bpy.ops.render.render(write_still=True)
                print('rendered', scene.render.filepath, flush=True)
            for item in (ob, plane, cam):
                bpy.data.objects.remove(item)


if __name__ == '__main__':
    main()
