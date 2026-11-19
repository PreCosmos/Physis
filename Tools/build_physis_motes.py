"""SM_FX_Motes (260) and SM_FX_Puffs (64): clouds of tiny squares in a ball of radius 100 cm, which the materials of
physis_monster_models.import_fx turn into sparks and crystals (Motes) and into flames and mist (Puffs) round an elemental monster. Each square sits at its mote's place and
is only half a centimetre across (a square of no size would be dropped on import); the material grows it towards the
camera's right and up. UV0: the corner (0..1). UV1: two random numbers of the mote (its pace and its starting phase).

  LD_LIBRARY_PATH=Saved/AudioTools/libplacebo387 blender -b --python Tools/build_physis_motes.py
writes Art/Meshes/Monsters/SM_FX_Motes.fbx and SM_FX_Puffs.fbx; then physis_monster_models.import_fx() in the editor.
"""
import random
from pathlib import Path

import bpy

OUT = Path(__file__).resolve().parents[1] / 'Art/Meshes/Monsters'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.scale_length = 0.01


def cloud(name, count, inner, outer, seed):
    rng = random.Random(seed)
    verts, faces, corners, seeds = [], [], [], []
    for k in range(count):
        while True:
            p = [rng.uniform(-1, 1) for _ in range(3)]
            r = sum(v * v for v in p) ** .5
            if inner < r < outer:
                break
        pair = (rng.random(), rng.random())
        base = len(verts)
        for cx, cy in ((0, 0), (1, 0), (1, 1), (0, 1)):
            verts.append((p[0] * 100 + (cx - .5) * .5, p[1] * 100 + (cy - .5) * .5, p[2] * 100))
            corners.append((cx, cy))
            seeds.append(pair)
        faces.append((base, base + 1, base + 2, base + 3))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    first, second = mesh.uv_layers.new(name='Corner'), mesh.uv_layers.new(name='Seed')
    for loop in mesh.loops:
        first.data[loop.index].uv = corners[loop.vertex_index]
        second.data[loop.index].uv = seeds[loop.vertex_index]
    mesh.materials.append(bpy.data.materials.new('Motes'))
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=str(OUT / (name + '.fbx')), use_selection=True, apply_scale_options='FBX_SCALE_NONE', global_scale=1.0, object_types={'MESH'}, bake_anim=False,
                             axis_forward='-Z', axis_up='Y')
    print('WROTE', name, len(faces))


cloud('SM_FX_Motes', 260, 0.3, 1.0, 7)     # sparks, crystals
cloud('SM_FX_Puffs', 64, 0.2, 0.85, 11)    # flames, mist: large, so few
