"""Exports the plasma pool: an organic, irregular outline with shore distance in vertex color.

Run: flatpak run org.blender.Blender -b --python Tools/build_physis_pool.py
"""
import math
import pathlib

import bpy

ROOT = pathlib.Path(bpy.path.abspath(__file__)).resolve().parent.parent
RINGS, SEGMENTS = 14, 180


def outline(angle):
    """A squared-off blob filling the 100 cm tile, with a wandering natural shoreline."""
    x, y = math.cos(angle), math.sin(angle)
    box = 1 / max((abs(x) ** 6 + abs(y) ** 6) ** (1 / 6), 1e-4)
    wobble = (.05 * math.sin(angle * 5 + 1) + .04 * math.sin(angle * 11 + 4) + .025 * math.sin(angle * 23 + 2) + .012 * math.sin(angle * 47))
    return 50 * box * (.9 + wobble)


vertices = [(0, 0, 0)]
shore = [1.0]
for ring in range(1, RINGS + 1):
    t = ring / RINGS
    reach = 1 - (1 - t) ** 2.4
    for segment in range(SEGMENTS):
        angle = 2 * math.pi * segment / SEGMENTS
        radius = outline(angle) * reach
        vertices.append((math.cos(angle) * radius, math.sin(angle) * radius, 0))
        shore.append(1 - t)
faces = [(0, 1 + segment, 1 + (segment + 1) % SEGMENTS) for segment in range(SEGMENTS)]
for ring in range(RINGS - 1):
    start = 1 + ring * SEGMENTS
    for segment in range(SEGMENTS):
        following = (segment + 1) % SEGMENTS
        faces.append((start + segment, start + SEGMENTS + segment, start + SEGMENTS + following, start + following))
mesh = bpy.data.meshes.new('SM_PlasmaPool')
mesh.from_pydata(vertices, [], faces)
paint = mesh.color_attributes.new(name='Col', type='BYTE_COLOR', domain='POINT')
for index, value in enumerate(shore):
    paint.data[index].color = (value, value, value, 1)
mesh.materials.append(bpy.data.materials.new('M_Plasma'))
item = bpy.data.objects.new('SM_PlasmaPool', mesh)
bpy.context.collection.objects.link(item)
item.select_set(True)
bpy.context.view_layer.objects.active = item
bpy.ops.export_scene.fbx(filepath=str(ROOT / 'Art/Meshes/Props/SM_PlasmaPool.fbx'), use_selection=True, axis_forward='-Y', axis_up='Z', mesh_smooth_type='FACE', add_leaf_bones=False, colors_type='LINEAR')
print('POOL DONE', flush=True)
