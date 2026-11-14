import re
p='build_physis_kit.py'
s=open(p,encoding='utf8').read()
def R(a,b,n=1):
    global s
    assert a in s, a[:60]
    s=s.replace(a,b) if n==0 else s.replace(a,b,n)
# stale stubs
s='\n'.join(l for l in s.split('\n') if 'if False' not in l)
R("""        x0, x1 = s * 256, s * 322
""","")
R("""    k.ring(o1, offset_poly(o1, -5), -52, -54, 'M_Trim', .6, 1) if False else None\n""","") if False else None
R("""        x0, x1 = (min(40, 214 * sign), max(40, 214 * sign)) if sign > 0 else (min(-40, -214), max(-40, -214))
""","")
R("""            k.bolts([(edge * f, -28, z + hgt / 2 + d) for f in (.34, .86) for d in (-12, 12)], r=1.5) if hgt > 80 else None
""","""            k.bolts([(edge * f, -28, z + hgt / 2 + d) for f in (.3, .9) for d in (-12, 12)], r=1.5)
""")
# tiles and sets
R("""TILE = {'M_Wall': 400, 'M_Trim': 200, 'M_Composite': 200, 'M_Deck': 200, 'M_Ceiling': 400, 'M_Hazard': 120,
        'M_Rubber': 100, 'M_Foam': 140, 'M_Light': 100, 'M_Glass': 400, 'M_Space': 800}""","""# These equal the physical tile of each set in Tools/build_physis_materials.py.
TILE = {'M_Wall': 200, 'M_Trim': 50, 'M_Composite': 60, 'M_Deck': 160, 'M_Ceiling': 200, 'M_Hazard': 100,
        'M_Rubber': 60, 'M_Foam': 140, 'M_Light': 100, 'M_Glass': 400, 'M_Space': 1600}""")
R("""SETS = {'M_Wall': 'T_Wall', 'M_Trim': 'T_Trim', 'M_Composite': 'T_Composite', 'M_Deck': 'T_Deck',
        'M_Ceiling': 'T_Ceiling', 'M_Hazard': 'T_Hazard', 'M_Foam': 'T_KitFoam'}""","""SETS = {'M_Wall': 'T_WallPanel', 'M_Trim': 'T_TitaniumTrim', 'M_Composite': 'T_DarkComposite', 'M_Deck': 'T_DeckPlate',
        'M_Ceiling': 'T_CeilingPanel', 'M_Hazard': 'T_HazardPaint', 'M_Foam': 'T_KitFoam'}""")
# ceiling stringers
R("""        with k.at(Rz(90) @ T(0, -200, 0)):
            ibeam(k, -y - 7, -y + 7, -40, -22, 0, 400, 'M_Wall', bevel=.4)""","""        with k.at(Rz(90)):
            ibeam(k, y - 7, y + 7, -40, -22, -400, 0, 'M_Wall', bevel=.4)""")
# hull winding
R("""            faces_f.append((a, b, c, d))
            faces_b.append((d, c, b, a))""","""            faces_f.append((d, c, b, a))
            faces_b.append((a, b, c, d))""")
R("""[(i, (i + 1) % nt, nt + (i + 1) % nt, nt + i) for i in range(nt)]""","""[(nt + i, nt + (i + 1) % nt, (i + 1) % nt, i) for i in range(nt)]""")
R("pale, deep = np.array((.76, .53, .17)), np.array((.33, .17, .05))","pale, deep = np.array((.58, .44, .24)), np.array((.16, .1, .05))")
R("n = noise.noise(q) * 7 + abs(noise.noise(q2)) * 4.4","n = noise.noise(q) * 9 + abs(noise.noise(q2)) * 6 - abs(noise.noise(q2 * 3.1)) * 2.4")
# lock
a=s.index("def _lock(k, sign):"); b=s.index("def blast_door(which):")
s=s[:a]+'''def _lock(k, sign):
    """Half of the central lock drum on each face; the drum splits on the seam at x=0."""
    def half(radius):
        return [(sign * radius * math.sin(math.pi * i / 28), 170 + radius * math.cos(math.pi * i / 28)) for i in range(29)]
    for face in (1, -1):
        with k.at(S(1, face, 1)):
            k.plate(half(90), -21, -29, 'M_Trim', 1.4, 2, taper=1.8)
            k.plate(half(64), -29, -33, 'M_Wall', 1.0, 2, taper=1.4)
            k.plate(half(24), -33, -37, 'M_Trim', .6, 2, taper=1.0)
            # Radial dogs: the part of the mechanism that visibly locks the door.
            for i in range(5):
                a = math.radians(-60 + i * 30)
                dx, dz = math.cos(a) * sign, math.sin(a)
                with k.at(T(dx * 76, -30, 170 + dz * 76) @ Ry(-math.degrees(math.atan2(dz, dx)))):
                    k.box(-9, 20, -5, 4, -6, 6, 'M_Wall', .9, 2)
                    k.bolt((14, -5, 0), (0, -1, 0), 1.6)


'''+s[b:]
# leaf cleanup
a=s.index("    seam = SEAM if sign > 0 else list(reversed(SEAM))"); b=s.index("    if poly_area(outline) < 0:\n        outline.reverse()\n    k.plate(outline, -15")
s=s[:a]+"    outline = list(SEAM) + [(edge, 340), (edge, 0)]\n"+s[b:]
R("""    with k.at(Rz(180)):
        with k.at(S(-1, 1, 1)):
            pass
    # Back""","    # Back")
# keys
a=s.index("def _keys(k, x0"); b=s.index("def console():")
s=s[:a]+s[b:]
R("""            lit = k.rng.uniform() < .14
            x = x0 + (x1 - x0) * (c + .5) / cols
            y = y0 + (y1 - y0) * (r + .5) / rows
            s = 1.5
            k.box(x - s, x + s, y - s, y + s, z, z + .7, 'M_Light' if lit else 'M_Trim', 0 if lit else .2, 1)""","""            x = x0 + (x1 - x0) * (c + .5) / cols
            y = y0 + (y1 - y0) * (r + .5) / rows
            s = 1.5
            k.box(x - s, x + s, y - s, y + s, z, z + .7, 'M_Trim', .2, 1)
            if k.rng.uniform() < .16:
                # Lit caps sample a flat header colour from the screen atlas.
                u = .02 if k.rng.uniform() < .7 else .35
                k.quad([(x - s + .3, y - s + .3, z + .72), (x + s - .3, y - s + .3, z + .72), (x + s - .3, y + s - .3, z + .72), (x - s + .3, y + s - .3, z + .72)],
                       'M_Screen', (u, .992, u + .05, .996))""")
# floor trim
R("with k.at(T(x, -26.4, 13.6) @ Rx(-58)):","with k.at(T(x, -25.6, 14.2) @ Rx(-32)):")
R("""            k.box(-74, 74, -.5, 1.2, -5.6, 5.6, 'M_Composite', .2, 1)
            for i in range(-11, 12):
                k.box(i * 6.2 - 1.3, i * 6.2 + 1.3, -1.1, 1.1, -4, 4, 'M_Trim', .25, 1)""","""            k.box(-78, 78, -.8, 1, -7.2, 7.2, 'M_Composite', .3, 1)
            for z in (-7.2, 7.2):
                k.box(-79, 79, -1.8, 1, z - 1, z + 1, 'M_Trim', .3, 1)
            for i in range(-11, 12):
                k.box(i * 6.6 - 1.7, i * 6.6 + 1.7, -2, 1, -6.2, 6.2, 'M_Trim', .35, 1)""")
R("""with k.at(T(x, -15.5, 30.5) @ Rx(-35)):
            k.box(-82, 82, -.6, .6, -2.2, 2.2, 'M_Light', 0)""","""with k.at(T(x, -14.6, 30.6) @ Rx(-55)):
            k.box(-82, 82, -.5, .5, -2.4, 2.4, 'M_Composite', .15, 1)
            k.box(-80, 80, -.8, .2, -.7, .7, 'M_Light', 0)""")
# column core
R("k.plate(core, 0, H, 'M_Composite', .8, 1, plane='XY')","k.plate(core, 4, H - 8, 'M_Composite', .8, 1, plane='XY')")
# door pilasters
R("""        k.box(s * 262, s * 316, -33, -30, 30, 150, 'M_Composite', .3, 1)
        for z in (40, 140):
            k.bolts([(s * (262 + a), -33, z) for a in (6, 48)], r=1.2)
""","""        k.plate(crect(min(s * 258, s * 318), 14, max(s * 258, s * 318), 318, 3), -28, -33, 'M_Wall', .9, 2, taper=1.2)
        k.box(s * 266, s * 310, -34, -32.5, 26, 112, 'M_Composite', .3, 1)
        slats(k, min(s * 268, s * 308), max(s * 268, s * 308), 30, 108, -33, 8)
        k.box(s * 270, s * 306, -34, -33, 150, 210, 'M_Trim', .3, 1)
        k.decal((3, 2), s * 288, 262, 44, y=-33.2, h=22)
        for z in (20, 118, 142, 312):
            k.bolts([(s * (264 + a), -33, z) for a in (0, 48)], r=1.2)
        # A doubler that follows the raked corner and ties lintel to pilaster.
        gusset = [(150, 410), (236, 410), (321, 328), (321, 322), (258, 322), (258, 356), (208, 398), (150, 398)]
        k.plate([(s * a, b) for a, b in gusset], -28, -34, 'M_Trim', .9, 2, taper=.9)
        k.bolts([(s * a, -34, b) for a, b in ((166, 404), (214, 404), (250, 372), (292, 334), (314, 326))], r=1.2)
""")
# rifles
R("""with k.at(T(x, -20, 62) @ Ry(-90)):""","""with k.at(T(x, -20, 62) @ Ry(-90) @ S(1.12, 1.25, 1.25)):""")
R("""    k.plate(body, -2.4, 2.4, 'M_Trim', .35, 1)
""","""    k.plate(body, -2.4, 2.4, 'M_Trim', .35, 1)
    k.plate([(26, 0), (58, 0), (58, 6), (28, 7)], -2.8, 2.8, 'M_Wall', .4, 1, taper=.4)
""")
# screen palette: amber is the station's UI colour, cyan the accent
R("cyan, amber, red = np.array((.2, .8, 1)), np.array((1, .66, .18)), np.array((1, .22, .14))","amber, cyan, red = np.array((.45, .78, 1)), np.array((1, .66, .18)), np.array((1, .22, .14))")
# grime softer, no speckle
R("math_node('MULTIPLY', cavity, ramp(fine.outputs[0], .3, .6))","math_node('MULTIPLY', cavity, ramp(broad.outputs[0], .3, .62))")
# preview
R("em.inputs[1].default_value = 14","em.inputs[1].default_value = 7")
R("em.inputs[1].default_value = 5 if slot == 'M_Screen' else 2.5","em.inputs[1].default_value = 2.2 if slot == 'M_Screen' else 1.1")
R("""        bs = _node(t, 'ShaderNodeBsdfPrincipled')
        tex = _node(t, 'ShaderNodeTexImage', image=load(TEX / 'T_KitDecal_BaseColor.png', False))
        L(uv.outputs[0], tex.inputs[0])
        L(tex.outputs[0], bs.inputs['Base Color'])
        L(tex.outputs[1], bs.inputs['Alpha'])
        bs.inputs['Roughness'].default_value = .55
        L(bs.outputs[0], out.inputs[0])
        return mat""","""        bs = _node(t, 'ShaderNodeBsdfPrincipled')
        tex = _node(t, 'ShaderNodeTexImage', image=load(TEX / 'T_KitDecal_BaseColor.png', False))
        L(uv.outputs[0], tex.inputs[0])
        L(tex.outputs[0], bs.inputs['Base Color'])
        bs.inputs['Roughness'].default_value = .55
        clear = _node(t, 'ShaderNodeBsdfTransparent')
        mix = _node(t, 'ShaderNodeMixShader')
        L(tex.outputs[1], mix.inputs[0])
        L(clear.outputs[0], mix.inputs[1])
        L(bs.outputs[0], mix.inputs[2])
        L(mix.outputs[0], out.inputs[0])
        return mat""")
R("""    tile = bpy.data.images.get('none')
""","")
R("BASES = {'M_Wall': ((.46, .48, .5), .46, 0),","BASES = {'M_Wall': ((.2, .25, .3), .46, 0),")
# ceiling lit from below in preview
R("""    lights = [area('key', centre + Vector((1.5, -2.2, 1.9)) * r, centre, power * 1.0, r * 1.2, (1, .95, .88)),
              area('fill', centre + Vector((-2.4, -1.5, .4)) * r, centre, power * .24, r * 2.0, (.72, .84, 1)),
              area('rim', centre + Vector((-.8, 2.4, 1.8)) * r, centre, power * 1.3, r * 1.0, (.8, .9, 1))]""","""    up = -1 if ob.name == 'SM_Kit_CeilingTruss' else 1
    lights = [area('key', centre + Vector((1.5, -2.2, 1.9 * up)) * r, centre, power * .8, r * 1.2, (1, .95, .88)),
              area('fill', centre + Vector((-2.4, -1.5, .4 * up)) * r, centre, power * .24, r * 2.0, (.72, .84, 1)),
              area('rim', centre + Vector((-.8, 2.4, 1.8)) * r, centre, power * 1.3, r * 1.0, (.8, .9, 1))]""")
# room render
R("""def export(ob):""","""def room_render(objects, samples):
    \"\"\"Assemble the kit into a Breach-Deck-sized room: the real test of whether modules work together.\"\"\"
    scene = bpy.context.scene
    src = dict(objects)
    placed = []

    def put(name, x, y, z=0, yaw=0):
        ob = bpy.data.objects.new(name + '_r', src[name].data)
        ob.location = (x, y, z)
        ob.rotation_euler = (0, 0, math.radians(yaw))
        scene.collection.objects.link(ob)
        placed.append(ob)
    x0, x1, y0, y1, h = 74, 1526, -600, 600, 450
    for z in (0,):
        for i in range(3):
            put('WallPanel' if i != 1 else 'HullBreach', x0, y1 - i * 400, z, 90)
            put('WallPanel', x1, y0 + i * 400, z, -90)
    put('WallPanel', 74, y1)
    put('WallPanel', 1126, y1)
    put('DoorFrame', 800, y1 + 20)
    put('BlastDoor', 800, y1 + 20)
    for i in range(4):
        for j in range(3):
            put('CeilingTruss', x0 + i * 400 - 400 * (i > 3), y0 + 200 + j * 400, h)
    for i in range(3):
        put('FloorTrim', x0 + 36, y1 - i * 400, 0, 90) if i != 1 else None
        put('FloorTrim', x1 - 36, y0 + i * 400, 0, -90)
    put('PipeRun', 74, y1 - 36, 356)
    put('PowerConduit', x1 - 36, y0 + 400, 350, -90)
    put('Console', 1326, y1 - 96)
    put('Terminal', 1120, y1 - 80, 0, 10)
    put('Column', 520, 90)
    put('CrateLarge', 300, -60, 0, 12)
    put('CrateSmall', 300, -60, 142, 40)
    put('CrateSmall', 460, -220, 0, -18)
    put('CrateSmall', 250, 180, 0, 8)
    put('FloorVent', 1000, 120, 0, 90)
    put('WeaponRack', x1 - 36, y0 + 1000, 0, -90)
    put('Viewport', x0 + 36, y0 + 400 - 0, 120, 90) if False else None
    def shell(name, a, b, mat):
        bpy.ops.mesh.primitive_cube_add(location=[(p + q) / 2 for p, q in zip(a, b)])
        ob = bpy.context.object
        ob.scale = [(q - p) / 2 for p, q in zip(a, b)]
        ob.data.materials.append(mat)
        return ob
    dark = bpy.data.materials.new('dark')
    dark.use_nodes = True
    dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.02, .022, .026, 1)
    deck = preview_material('M_Deck', None, 'room')
    for a, b in (((x0 - 60, y0 - 60, h), (x1 + 60, y1 + 60, h + 40)), ((x0 - 60, y0, 0), (x0, y1, h)), ((x1, y0, 0), (x1 + 60, y1, h)),
                 ((x0, y1, 0), (590, y1 + 40, h)), ((1010, y1, 0), (x1, y1 + 40, h)), ((590, y1, 340), (1010, y1 + 40, h)), ((x0, y0 - 40, 0), (x1, y0, h))):
        shell('wall', a, b, dark)
    me = bpy.data.meshes.new('floor')
    me.from_pydata([(x0 - 60, y0, 0), (x1 + 60, y0, 0), (x1 + 60, y1 + 200, 0), (x0 - 60, y1 + 200, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    tile = TILE['M_Deck']
    uv.data.foreach_set('uv', np.array([(0, 0), (1600 / tile, 0), (1600 / tile, 1400 / tile), (0, 1400 / tile)], np.float32).ravel())
    me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    me.materials.append(deck)
    floor = bpy.data.objects.new('floor', me)
    scene.collection.objects.link(floor)
    world = scene.world
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.002, .002, .003, 1)
    cam = bpy.data.cameras.new('room')
    cam.lens = 24
    cam.clip_end = 100000
    co = bpy.data.objects.new('room', cam)
    co.location = (1290, -540, 158)
    target = Vector((430, 480, 175))
    co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(co)
    scene.camera = co
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.cycles.samples = samples
    scene.cycles.max_bounces = 7
    for name, loc, power, colour in (('a', (500, 0, 400), 1.6e6, (1, .93, .84)), ('b', (1100, 0, 400), 1.6e6, (1, .93, .84))):
        area(name, loc, (loc[0], loc[1], 0), power, 500, colour)
    area('c', (800, 560, 330), (800, 0, 0), 2.0e5, 200, (1, .55, .2))
    scene.render.filepath = str(REVIEW / 'kit_room.png')
    bpy.ops.render.render(write_still=True)


def export(ob):""")
s='\n'.join(l for l in s.split('\n') if 'if False' not in l or "R(" in l)
R("""    parser.add_argument('--suffix', default='')""","""    parser.add_argument('--suffix', default='')
    parser.add_argument('--room', action='store_true')
    parser.add_argument('--no-cells', action='store_true')
    parser.add_argument('--room-samples', type=int, default=96)""")
R("""    if not args.no_render:
        setup_render(args.cell, args.samples)
        paths = []""","""    if not args.no_render:
        setup_render(args.cell, args.samples)
    if not args.no_render and not args.no_cells:
        paths = []""")
R("""    print('PHYSIS_KIT_DONE', flush=True)""","""    if args.room:
        for _, ob in objects:
            ob.hide_render = True
        room_render(objects, args.room_samples)
    print('PHYSIS_KIT_DONE', flush=True)""")
open(p,'w',encoding='utf8').write(s)
