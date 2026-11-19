"""Blender: gridded straight-on views of a generated model, for placing its skeleton by eye (Tools/build_physis_monsters.py).
  blender -b --python Tools/model_measure.py -- MODEL.glb OUT_PREFIX
Writes OUT_PREFIX_x.png (seen from +x: right of the picture is +y), _y.png (seen from -y: right is +x) and _z.png
(from above: right is +x, up is +y). Each is 1200 px for 1.2 units, the model's origin in the middle, so a pixel is
0.001 units; the caller draws a grid every 100 px (0.1 unit). Also prints the box and, for a few heights, where the
model's cross-section is (to find legs)."""
import math, sys
import bpy, numpy as np
glb, out = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
v = np.array([ob.matrix_world @ p.co for p in ob.data.vertices])
print('BOX', v.min(0).round(3).tolist(), v.max(0).round(3).tolist())
low = v[:, 2].min()
for z in [low + 0.02, low + 0.08, low + 0.16, low + 0.26]:
    sel = v[np.abs(v[:, 2] - z) < 0.012][:, :2]
    cells = set(map(tuple, np.floor(sel / 0.025).astype(int)))
    groups = []
    while cells:
        stack, group = [cells.pop()], []
        while stack:
            c = stack.pop(); group.append(c)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (c[0] + dx, c[1] + dy)
                    if n in cells:
                        cells.remove(n); stack.append(n)
        g = (np.array(group) + .5) * 0.025
        if len(group) >= 3:
            groups.append('(%.2f, %.2f)±(%.2f, %.2f)' % (g[:, 0].mean(), g[:, 1].mean(), np.ptp(g[:, 0]) / 2, np.ptp(g[:, 1]) / 2))
    print('SLICE z %.2f: %s' % (z, '  '.join(sorted(groups))))
s = bpy.context.scene
s.render.engine = 'BLENDER_WORKBENCH'; s.display.shading.light = 'FLAT'; s.display.shading.color_type = 'TEXTURE'
s.render.resolution_x = s.render.resolution_y = 1200
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); s.collection.objects.link(cam); s.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.2
for name, loc, rot in (('x', (5, 0, 0), (math.radians(90), 0, math.radians(90))), ('y', (0, -5, 0), (math.radians(90), 0, 0)), ('z', (0, 0, 5), (0, 0, 0))):
    cam.location = loc; cam.rotation_euler = rot
    s.render.filepath = '%s_%s.png' % (out, name); bpy.ops.render.render(write_still=True)
