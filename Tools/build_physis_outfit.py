"""Run in Blender: fit and skin Physis's outfit to the exported MetaHuman body.

blender --background --factory-startup --python Tools/build_physis_outfit.py -- PROJECT_ROOT
"""
import bpy
import bmesh
import numpy as np
import math
import json
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
DEST = ROOT / 'Art/Characters/Physis'
TEX = DEST / 'Textures'
TEX.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(DEST / 'physis-body-guide.fbx'))
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name.endswith('LOD1'))
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
for obj in list(bpy.context.scene.objects):
    if obj.type == 'MESH' and obj != body:
        bpy.data.objects.remove(obj, do_unlink=True)
body.name = 'MetaHuman_Body_Fitting_Guide'
body.hide_render = True
body.data.update()
bvh = BVHTree.FromPolygons([v.co for v in body.data.vertices], [p.vertices[:] for p in body.data.polygons])

# PBR sources are generated from periodic woven thread geometry and seeded
# branching curves. No lighting, shadows, or wrinkles are painted into albedo.
N = 2048
y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
warp = np.sin(x * 2 * np.pi * 256)
weft = np.sin(y * 2 * np.pi * 256)
height = .5 + .13 * warp + .13 * weft + .045 * warp * weft
grain = np.random.default_rng(27).normal(0, .007, (N, N)).astype(np.float32)
mask = np.zeros((N, N), dtype=np.float32)
rng = np.random.default_rng(1987)


def line(a, b, width):
    # Work in a local bounding rectangle; wrap samples to maintain tiling.
    a, b = np.asarray(a) * N, np.asarray(b) * N
    lo = np.floor(np.minimum(a, b) - width - 2).astype(int)
    hi = np.ceil(np.maximum(a, b) + width + 2).astype(int)
    yy, xx = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    ab = b - a
    t = np.clip(((xx-a[0])*ab[0]+(yy-a[1])*ab[1]) / max(np.dot(ab,ab), .001), 0, 1)
    d = np.sqrt((xx-a[0]-t*ab[0])**2+(yy-a[1]-t*ab[1])**2)
    values = np.clip(width + .7 - d, 0, 1)
    np.maximum.at(mask, (yy.ravel() % N, xx.ravel() % N), values.ravel())


for base_x in (.13, .48, .81):
    nodes = [(base_x, -.08)]
    for j in range(1, 14):
        prev = nodes[-1]
        nodes.append((prev[0] + rng.uniform(-.045, .045), -.08 + j*.09))
    for j,(a,b) in enumerate(zip(nodes[:-1], nodes[1:])):
        line(a,b,1.3)
        if j % 2 == 0:
            side = -1 if j % 4 else 1
            end = (a[0]+side*rng.uniform(.06,.12), a[1]+rng.uniform(.06,.13))
            mid = ((a[0]+end[0])*.5 + rng.uniform(-.012,.012), (a[1]+end[1])*.5)
            line(a,mid,.9);line(mid,end,.7)
            fork = (mid[0]+side*.035, mid[1]+.075)
            line(mid,fork,.6)


def save_image(name, rgb, data=False):
    if rgb.ndim == 2:
        rgb = np.repeat(rgb[...,None],3,axis=2)
    rgba = np.ones((N,N,4),dtype=np.float32)
    rgba[:,:,:3] = np.clip(rgb,0,1)
    image = bpy.data.images.new(name,width=N,height=N,alpha=False)
    image.colorspace_settings.name = 'Non-Color' if data else 'sRGB'
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(TEX/(name+'.png'))
    image.file_format = 'PNG'
    image.save()
    return image


colors = {'Ivory':(.68,.63,.52), 'Charcoal':(.035,.039,.044),
          'Sash':(.12,.105,.085), 'Boots':(.045,.04,.035), 'GoldTrim':(.48,.27,.085)}
materials = {}
gold = np.array([.68,.4,.12],dtype=np.float32)
for name,color in colors.items():
    variation = (height-.5)*.045 + grain
    color_array = np.clip(np.array(color)[None,None,:] + variation[...,None], 0, 1)
    if name in ('Ivory','Charcoal'):
        strength = .82 if name == 'Ivory' else .48
        color_array = color_array*(1-mask[...,None]*strength)+gold*mask[...,None]*strength
    image = save_image('T_Physis_'+name+'_BaseColor',color_array)
    mat = bpy.data.materials.new(name);mat.use_nodes=True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    texture = mat.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
    mat.node_tree.links.new(texture.outputs['Color'],bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = .8 if name!='GoldTrim' else .4
    bsdf.inputs['Metallic'].default_value = .65 if name=='GoldTrim' else 0
    materials[name]=mat
dx = (np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.3
dy = (np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.3
normal = np.stack([-dx,-dy,np.ones_like(dx)],axis=2)
normal /= np.linalg.norm(normal,axis=2,keepdims=True)
save_image('T_Physis_Fabric_Normal',normal*.5+.5,True)
orm=np.stack([np.ones_like(x),np.clip(.82+(height-.5)*.1,0,1),np.zeros_like(x)],axis=2)
save_image('T_Physis_Fabric_ORM',orm,True)
save_image('T_Physis_Divinity_Mask',mask,True)

pieces=[]


def skin_mesh(obj):
    obj.parent=arm
    obj.matrix_world=body.matrix_world.copy()
    for group in body.vertex_groups:
        if group.name not in obj.vertex_groups:
            obj.vertex_groups.new(name=group.name)
    bpy.context.view_layer.objects.active=obj
    transfer=obj.modifiers.new('Fitted MetaHuman skin weights','DATA_TRANSFER')
    transfer.object=body;transfer.use_vert_data=True
    transfer.data_types_verts={'VGROUP_WEIGHTS'}
    transfer.vert_mapping='POLYINTERP_NEAREST'
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    modifier=obj.modifiers.new('MetaHuman Skeleton','ARMATURE');modifier.object=arm
    for face in obj.data.polygons:face.use_smooth=True
    pieces.append(obj)
    return obj


def surface(name, vertices, faces, uvs, material):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    mesh.materials.append(materials[material])
    layer=mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        for loop in face.loop_indices:
            layer.data[loop].uv=uvs[mesh.loops[loop].vertex_index]
    return skin_mesh(obj)


def fitted_shell(name, material, predicate, thickness):
    indices=[v.index for v in body.data.vertices if predicate(v)]
    keep=set(indices);remap={old:new for new,old in enumerate(indices)}
    verts=[tuple(body.data.vertices[i].co+body.data.vertices[i].normal*thickness) for i in indices]
    source_faces=[p for p in body.data.polygons if all(i in keep for i in p.vertices)]
    faces=[tuple(remap[i] for i in p.vertices) for p in source_faces]
    uv_by_vertex={}
    src_uv=body.data.uv_layers.active
    for p in source_faces:
        for li in p.loop_indices:
            uv_by_vertex[body.data.loops[li].vertex_index]=tuple(src_uv.data[li].uv)
    uvs=[uv_by_vertex.get(i,(0,0)) for i in indices]
    return surface(name,verts,faces,uvs,material)


def hand_vertex(v):
    return abs(v.co.x)>43 or sum(g.weight for g in v.groups if any(k in body.vertex_groups[g.group].name for k in ('hand_','thumb_','index_','middle_','ring_','pinky_')))> .5


fitted_shell('Charcoal_Sleeves_And_Trousers','Charcoal',
             lambda v: 12<v.co.z and not hand_vertex(v), .55)


def body_surface(x,z,front=True):
    values=[]
    for offset in (-3,0,3):
        origin=Vector((x+offset,-60 if front else 60,z))
        hit=bvh.ray_cast(origin,Vector((0,1 if front else -1,0)),120)[0]
        if hit is not None:values.append(hit.y)
    return (min(values)-1.4 if front else max(values)+1.4) if values else (-7 if front else 8)


# An independent panel topology produces clean sewn boundaries and a fabric
# silhouette across the chest instead of copying anatomical breast contours.
cols=49;rows=40;verts=[];faces=[];uvs=[]
for front in (True,False):
    for row in range(rows):
        t=row/(rows-1)
        for col in range(cols):
            u=col/(cols-1);signed=2*u-1
            top=137-15*(1-abs(signed))**1.1 if front else 137+1.5*(1-abs(signed))
            z=108+(top-108)*t
            width=float(np.interp(z,[108,115,120,125,130,135,140],[12.5,13,15.5,16.5,18,17,11]))
            xx=signed*width
            yy=body_surface(xx,z,front)
            verts.append((xx,yy,z));uvs.append((u,t))
base=rows*cols
for front in (0,1):
    off=front*base
    for row in range(rows-1):
        for col in range(cols-1):
            i=off+row*cols+col
            face=(i,i+1,i+cols+1,i+cols)
            faces.append(face if not front else tuple(reversed(face)))
for row in range(rows-1):
    for col in (0,cols-1):
        i=row*cols+col;faces.append((i,i+cols,i+cols+base,i+base))
surface('Ivory_Wrap_Bodice',verts,faces,uvs,'Ivory')

# Broad diagonal overlap/lapel carries the wrapped construction in the concept.
verts=[];faces=[];uvs=[]
for row in range(48):
    t=row/47
    z=135-27*t;center_x=-16+28*t;width=2.0+1.0*t
    for col in range(5):
        u=col/4;xx=center_x+(u-.5)*width*2
        verts.append((xx,body_surface(xx,z,True)-.6,z));uvs.append((u,1-t))
for row in range(47):
    for col in range(4):
        i=row*5+col;faces.append((i,i+1,i+6,i+5))
surface('Ivory_Diagonal_Wrap_Lapel',verts,faces,uvs,'Ivory')

# Four separate curved cloth panels provide the characteristic split silhouette.
for number,(start,end) in enumerate([(-78,-6),(6,78),(102,178),(182,258)]):
    verts=[];uvs=[];faces=[];cols=25;rows=42
    for r in range(rows):
        t=r/(rows-1)
        rx=np.interp(t,[0,.2,1],[13.5,18,24])
        ry=np.interp(t,[0,.2,1],[11,13.5,18])
        for col in range(cols):
            u=col/(cols-1);angle=math.radians(start+(end-start)*u)
            hem=13+9*u if number in (0,2) else 22-9*u
            z=109*(1-t)+hem*t
            fold=math.sin(u*math.pi*7)*(.2+1.1*t)
            verts.append(((rx+fold)*math.sin(angle),-3-(ry+fold)*math.cos(angle),z))
            uvs.append((u,1-t))
    for r in range(rows-1):
        for col in range(cols-1):
            i=r*cols+col;faces.append((i,i+1,i+cols+1,i+cols))
    surface('Ivory_Split_Tail_'+str(number+1),verts,faces,uvs,'Ivory')


def ring_band(name,z0,z1,rx,ry,material,offset_y=-3):
    verts=[];uvs=[];faces=[];steps=96;rows=5
    for r in range(rows):
        t=r/(rows-1)
        for col in range(steps+1):
            u=col/steps;a=u*math.pi*2
            ripple=.15*math.sin(u*math.pi*10+t*5)
            verts.append(((rx+ripple)*math.sin(a),offset_y-(ry+ripple)*math.cos(a),z0+(z1-z0)*t))
            uvs.append((u,t))
    for r in range(rows-1):
        for col in range(steps):
            i=r*(steps+1)+col;faces.append((i,i+1,i+steps+2,i+steps+1))
    return surface(name,verts,faces,uvs,material)


ring_band('Wrapped_Waist_Sash',107,113,14,11.5,'Sash')
ring_band('Sash_Upper_Stitch',112.5,112.8,14.2,11.7,'GoldTrim')
ring_band('Sash_Lower_Stitch',107.2,107.5,14.2,11.7,'GoldTrim')
ring_band('Charcoal_Standing_Collar',135.5,142,7.0,5.6,'Charcoal',offset_y=2.0)
for side in ('l','r'):
    wrist=arm.data.bones['hand_'+side].head_local
    elbow=arm.data.bones['lowerarm_'+side].head_local
    axis=(wrist-elbow).normalized()
    normal=axis.cross(Vector((0,1,0))).normalized();binormal=axis.cross(normal).normalized()
    verts=[];uvs=[];faces=[];steps=40
    for row in range(4):
        t=row/3;center=wrist-axis*(5.5-5*t)
        for col in range(steps+1):
            u=col/steps;a=u*math.pi*2
            p=center+normal*math.cos(a)*3.2+binormal*math.sin(a)*3.6
            verts.append(tuple(p));uvs.append((u,t))
    for row in range(3):
        for col in range(steps):
            i=row*(steps+1)+col;faces.append((i,i+1,i+steps+2,i+steps+1))
    surface('Tailored_Wrist_Cuff_'+side,verts,faces,uvs,'Charcoal')
for side in (-1,1):
    foot_points=[v.co for v in body.data.vertices if v.co.z<7 and v.co.x*side>0]
    cy=(min(v.y for v in foot_points)+max(v.y for v in foot_points))*.5
    ry=(max(v.y for v in foot_points)-min(v.y for v in foot_points))*.5+1.5
    rx=(max(v.x for v in foot_points)-min(v.x for v in foot_points))*.5+1.0
    cx=(min(v.x for v in foot_points)+max(v.x for v in foot_points))*.5
    profiles=[(0.6,rx,ry,cy),(2.6,rx,ry,cy),(4,rx,ry,cy),(7,5.2,10,-3),(10,4.7,5.5,0),(18,4.9,5.2,2),(24,5.2,5.5,2.5)]
    verts=[];faces=[];uvs=[];steps=48
    for row,(z,rx,ry,cy) in enumerate(profiles):
        for col in range(steps+1):
            u=col/steps;a=u*math.pi*2
            verts.append((cx+rx*math.sin(a),cy-ry*math.cos(a),z))
            uvs.append((u,row/(len(profiles)-1)))
    for row in range(len(profiles)-1):
        for col in range(steps):
            i=row*(steps+1)+col;faces.append((i,i+1,i+steps+2,i+steps+1))
    surface('Boot_'+('L' if side>0 else 'R'),verts,faces,uvs,'Boots')

# One deforming mesh, five named material sections, existing MetaHuman hierarchy.
bpy.ops.object.select_all(action='DESELECT')
for obj in pieces:obj.select_set(True)
bpy.context.view_layer.objects.active=pieces[0]
bpy.ops.object.join()
outfit=bpy.context.object;outfit.name='SK_Physis_Outfit'
# Helper/corrective bones can be stripped from the leader at lower body LODs.
# Bind clothing only to core deform bones that remain available across LODs.
core={'root','pelvis','spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head'}
for side in ('l','r'):
    core.update(part+'_'+side for part in ('clavicle','upperarm','lowerarm','hand','thigh','calf','foot','ball'))
targets={}
for group in outfit.vertex_groups:
    bone=arm.data.bones.get(group.name)
    while bone and bone.name not in core:bone=bone.parent
    targets[group.index]=bone.name if bone else 'pelvis'
weights=[]
for vertex in outfit.data.vertices:
    mapped={}
    for group in vertex.groups:
        name=targets[group.group];mapped[name]=mapped.get(name,0)+group.weight
    weights.append(mapped)
outfit.vertex_groups.clear()
for name in sorted(set(n for vertex in weights for n in vertex)):
    outfit.vertex_groups.new(name=name)
for index,vertex in enumerate(weights):
    for name,weight in vertex.items():outfit.vertex_groups[name].add([index],weight,'REPLACE')
bpy.ops.object.vertex_group_limit_total(limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True);outfit.select_set(True);bpy.context.view_layer.objects.active=outfit
bpy.ops.export_scene.fbx(filepath=str(DEST/'SK_Physis_Outfit.fbx'),use_selection=True,
                        object_types={'ARMATURE','MESH'},add_leaf_bones=False,
                        bake_anim=False,mesh_smooth_type='FACE',use_mesh_modifiers=True,
                        axis_forward='-Y',axis_up='Z',path_mode='STRIP')
body.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(DEST/'Physis_Outfit.blend'))
report={'vertices':len(outfit.data.vertices),'polygons':len(outfit.data.polygons),
        'material_slots':[m.name for m in outfit.data.materials],
        'texture_resolution':[N,N], 'maximum_skin_influences':4,
        'binding':'Transferred from slim Physis body, remapped to core deform bones for LOD compatibility',
        'unweighted_vertices':sum(1 for v in outfit.data.vertices if not v.groups),
        'notes':['Skinned garment; cloth simulation not authored yet.',
                 'Concept likeness and animation intersections require Unreal visual review.']}
(DEST/'outfit-build.json').write_text(json.dumps(report,indent=2))
print('PHYSIS_OUTFIT_BUILT',json.dumps(report))
