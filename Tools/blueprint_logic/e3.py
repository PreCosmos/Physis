p='build_physis_kit.py'
s=open(p,encoding='utf8').read()
def R(a,b):
    global s
    assert a in s, a[:70]
    s=s.replace(a,b)
# truss spans exactly the module so it tiles on Y
R("""    for i in range(-3, 3):
        y0 = i * pitch + 20
        y1 = y0 + pitch""","""    for i in range(5):
        y0 = i * pitch - 200
        y1 = y0 + pitch""")
R("""    for i in range(-3, 4):
        y = i * pitch + 20
        k.plate([(y - 16, -74), (y + 16, -74), (y + 9, -56), (y - 9, -56)], 199, 201, 'M_Trim', .4, 1, plane='YZ')
        y2 = y + pitch / 2
        if y2 < 200:
            k.plate([(y2 - 16, -22), (y2 + 16, -22), (y2 + 9, -40), (y2 - 9, -40)], 199, 201, 'M_Trim', .4, 1, plane='YZ')""","""    for i in range(6):
        y = i * pitch - 200
        if 0 < i < 5:
            k.plate([(y - 16, -74), (y + 16, -74), (y + 9, -56), (y - 9, -56)], 199, 201, 'M_Trim', .4, 1, plane='YZ')
        y2 = y + pitch / 2
        if y2 < 200:
            k.plate([(y2 - 16, -22), (y2 + 16, -22), (y2 + 9, -40), (y2 - 9, -40)], 199, 201, 'M_Trim', .4, 1, plane='YZ')""")
R("for y in (-140, -60, 20, 100)]","for y in (-120, -40, 40, 120)]")
# bake excludes decals and glass: they float over surfaces and would occlude them
R("""    me.materials.clear()
    me.materials.append(mat)
    me.polygons.foreach_set('material_index', [0] * len(me.polygons))
""","""    skip = [i for i, m in enumerate(ob.data.materials) if m.name.split('.')[0] in ('M_Decal', 'M_Glass')]
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in skip], context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(mat)
    me.polygons.foreach_set('material_index', [0] * len(me.polygons))
""")
# neutral grime, cooler bare metal
R("grime.inputs['B'].default_value = (.32, .27, .2, 1)","grime.inputs['B'].default_value = (.33, .33, .35, 1)")
R("worn.inputs['B'].default_value = (.62, .63, .64, 1)","worn.inputs['B'].default_value = (.56, .58, .6, 1)")
R("em.inputs[1].default_value = 7","em.inputs[1].default_value = 4.5")
R("em.inputs[0].default_value = (1, .94, .82, 1)","em.inputs[0].default_value = (1, .95, .86, 1)")
# thinner meridian line
R("k.box(x0 - 2, x1 + 2, -18.6, -17.6, 303, 313, 'M_Light', 0)","k.box(x0 - 2, x1 + 2, -18.6, -17.6, 306, 310, 'M_Light', 0)")
R("k.ring(crect(-62.5, -62.5, 62.5, 62.5, 14), crect(-58, -58, 58, 58, 13), 304, 312, 'M_Light', 0, plane='XY')","k.ring(crect(-62.5, -62.5, 62.5, 62.5, 14), crect(-58, -58, 58, 58, 13), 306, 310, 'M_Light', 0, plane='XY')")
# space card uses a framed crop of the existing sky
R("k.box(34, 366, -5, -4, 34, 266, 'M_Space', 0)","k.quad([(34, -4, 34), (366, -4, 34), (366, -4, 266), (34, -4, 266)], 'M_Space', (.12, .42, .38, .62))")
# room layout
a=s.index("    x0, x1, y0, y1, h = 74, 1526"); b=s.index("    def shell(name, a, b, mat):")
s=s[:a]+"""    x0, x1, y0, y1, h = 74, 1526, -600, 600, 450
    for i in range(3):
        put('HullBreach' if i == 1 else 'WallPanel', x0, y0 + i * 400, 0, 90)
        put('WallPanel', x1, y1 - i * 400, 0, -90)
        put('FloorTrim', x1 - 36, y1 - i * 400, 0, -90)
        if i != 1:
            put('FloorTrim', x0 + 36, y0 + i * 400, 0, 90)
    put('WallPanel', 74, y1)
    put('WallPanel', 1126, y1)
    put('DoorFrame', 800, y1 + 20)
    put('BlastDoor', 800, y1 + 20)
    for i in range(4):
        for j in range(3):
            put('CeilingTruss', x0 + i * 400, y0 + 200 + j * 400, h)
    put('PipeRun', 74, y1 - 36, 356)
    put('PowerConduit', x1 - 36, y1, 350, -90)
    put('Console', 1326, y1 - 96)
    put('Terminal', 1120, y1 - 80, 0, 10)
    put('Column', 640, 240)
    put('CrateLarge', 340, -340, 0, 12)
    put('CrateSmall', 340, -340, 142, 40)
    put('CrateSmall', 520, -480, 0, -18)
    put('FloorVent', 1000, 120, 0, 90)
    put('WeaponRack', x1 - 36, y0 + 200, 0, -90)
    put('Viewport', x0 + 37, y1 - 400, 110, 90)
"""+s[b:]
R("co.location = (1290, -540, 158)\n    target = Vector((430, 480, 175))","co.location = (1330, -560, 160)\n    target = Vector((330, 330, 185))")
open(p,'w',encoding='utf8').write(s)
