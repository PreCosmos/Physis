import bpy, sys
root = sys.argv[sys.argv.index('--') + 1]
for name in ('physis-body-guide.fbx', 'physis-face-guide.fbx'):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=root + '/Art/Characters/Physis/' + name)
    print('PROBE ==', name)
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            xs = [v.co for v in o.data.vertices]
            print('PROBE', o.name, len(xs), 'scale', tuple(round(s, 3) for s in o.matrix_world.to_scale()),
                  'x', round(min(v.x for v in xs), 1), round(max(v.x for v in xs), 1),
                  'y', round(min(v.y for v in xs), 1), round(max(v.y for v in xs), 1),
                  'z', round(min(v.z for v in xs), 1), round(max(v.z for v in xs), 1),
                  'groups', len(o.vertex_groups))
        else:
            print('PROBE', o.type, o.name, 'scale', tuple(round(s, 3) for s in o.matrix_world.to_scale()))
