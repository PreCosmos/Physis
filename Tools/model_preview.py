"""Blender: a four-view sheet of a GLB. blender -b --python Tools/model_preview.py -- MODEL.glb OUT.png"""
import math, sys
import bpy
from mathutils import Vector
glb, out = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
mid, size = (lo + hi) / 2, max(hi - lo)
print('STATS faces', sum(len(o.data.polygons) for o in meshes), 'verts', sum(len(o.data.vertices) for o in meshes), 'size', tuple(round(v, 3) for v in hi - lo), 'materials', [m.name for o in meshes for m in o.data.materials])
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'; scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'TEXTURE'  # no GPU memory: the card is busy generating
scene.render.resolution_x = scene.render.resolution_y = 768
world = bpy.data.worlds.new('w'); scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.35, .37, .4, 1); world.node_tree.nodes['Background'].inputs[1].default_value = 1.2
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 4; sun.rotation_euler = (math.radians(50), 0, math.radians(30)); scene.collection.objects.link(sun)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
for k, (yaw, pitch) in enumerate([(35, 12), (125, 12), (215, 12), (270, 60)]):
    a, b = math.radians(yaw), math.radians(pitch)
    cam.location = mid + Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b))) * size * 2.1
    cam.rotation_euler = (mid - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = '%s_%d.png' % (out[:-4], k)
    bpy.ops.render.render(write_still=True)
