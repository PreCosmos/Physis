import re
p='build_physis_kit.py'
s=open(p,encoding='utf8').read()
def R(a,b,n=1):
    global s
    assert s.count(a)>=1, a[:70]
    s=s.replace(a,b) if n==0 else s.replace(a,b,n)

# --- docs and constants
R("Vertex colour: R = bevel/edge flag, G = per-part random, B = 1 (reserved).","Vertex colour: R = bevel/edge flag, G = per-part random, B = paint scheme for M_Wall and M_Ceiling\n(1 = station grey, .5 = bone, 0 = cargo olive; compare against .1 and .9 so sRGB handling cannot change the result).")
R("TILE = {'M_Wall': 200, 'M_Trim': 50,","TILE = {'M_Wall': 180, 'M_Trim': 120,")
R("'M_Ceiling': 200, 'M_Hazard': 100,","'M_Ceiling': 180, 'M_Hazard': 100,")
R("'M_Light': 100, 'M_Glass'","'M_Light': 60, 'M_Glass'")
R("SETS = {'M_Wall': 'T_WallPanel', 'M_Trim': 'T_TitaniumTrim',","SETS = {'M_Wall': 'T_KitPaint', 'M_Trim': 'T_KitMetal',")
R("'M_Ceiling': 'T_CeilingPanel',","'M_Ceiling': 'T_KitPaint',")
R("MASK_SIZE = {'SM_Kit_WallPanel': 2048, 'SM_Kit_BlastDoor': 2048, 'SM_Kit_HullBreach': 2048, 'SM_Kit_DoorFrame': 2048}",
  "MASK_SIZE = {'SM_Kit_WallPanel': 2048, 'SM_Kit_BlastDoor': 2048, 'SM_Kit_HullBreach': 2048, 'SM_Kit_DoorFrame': 2048,\n             'SM_Kit_CrateLarge': 2048, 'SM_Kit_CrateSmall': 2048, 'SM_Kit_Console': 2048, 'SM_Kit_WeaponRack': 2048}\nGREY, BONE, CARGO = 1.0, .5, 0.0  # vertex-colour B, see the module docstring\nPAINT = {GREY: (.21, .25, .30), BONE: (.62, .60, .53), CARGO: (.17, .20, .13)}")

# --- tone plumbing
R("        self.UV, self.EDGE, self.PID = [], [], []\n","        self.UV, self.EDGE, self.PID, self.TONE = [], [], [], []\n        self.paint = GREY\n")
R("""    def at(self, m):
        return Kit._At(self, m)
""","""    class _Paint:
        def __init__(self, kit, tone):
            self.kit, self.tone = kit, tone

        def __enter__(self):
            self.prev, self.kit.paint = self.kit.paint, self.tone

        def __exit__(self, *_):
            self.kit.paint = self.prev

    def at(self, m):
        return Kit._At(self, m)

    def painted(self, tone):
        return Kit._Paint(self, tone)
""")
R("                self.PID.append(pid)\n","                self.PID.append(pid)\n                self.TONE.append(self.paint)\n")
R("        c[:, 0], c[:, 1] = self.EDGE, self.PID\n","        c[:, 0], c[:, 1], c[:, 2] = self.EDGE, self.PID, self.TONE\n")

# --- wall colour blocking
R("""    with k.at(T(0, -22, 323) @ Rx(-6.4)):
        k.plate(crect(x0, 0, x1, 118, (2, 2, 2, 2)), 0, 11, 'M_Wall', 1.1, 2, taper=-.6, align=True)
""","""    with k.at(T(0, -22, 323) @ Rx(-6.4)):
        with k.painted(BONE):
            k.plate(crect(x0, 0, x1, 118, (2, 2, 2, 2)), 0, 11, 'M_Wall', 1.1, 2, taper=-.6, align=True)
""")
R("        k.plate(offset_poly(hatch, -.5), -19, -22.6, 'M_Wall', .7, 2, taper=.5)\n        k.plate(crect(x0 + 40, 160, x1 - 40, 232, 4), -22.6, -23.6, 'M_Wall', .3, 1)\n",
  "        with k.painted(BONE):\n            k.plate(offset_poly(hatch, -.5), -19, -22.6, 'M_Wall', .7, 2, taper=.5)\n            k.plate(crect(x0 + 40, 160, x1 - 40, 232, 4), -22.6, -23.6, 'M_Wall', .3, 1)\n")
R("        k.plate(plate, -21, -24, 'M_Wall', .8, 2, taper=1.6)\n","        with k.painted(BONE):\n            k.plate(plate, -21, -24, 'M_Wall', .8, 2, taper=1.6)\n")

# --- crates are cargo olive, consoles and terminals bone
R("    k = Kit(name, seed)\n    post, rail =","    k = Kit(name, seed)\n    k.paint = CARGO\n    post, rail =")
R("    k = Kit('SM_Kit_Console', 18)\n","    k = Kit('SM_Kit_Console', 18)\n    k.paint = BONE\n")
R("    k = Kit('SM_Kit_Terminal', 19)\n","    k = Kit('SM_Kit_Terminal', 19)\n    k.paint = BONE\n")

# --- ceiling coffers catch light
R("            k.plate(crect(x0, y0, x1, y1, 5), -3, -7, 'M_Ceiling', .8, 2, plane='XY', taper=1.0)\n","            with k.painted(BONE):\n                k.plate(crect(x0, y0, x1, y1, 5), -3, -7, 'M_Ceiling', .8, 2, plane='XY', taper=1.0)\n")

# --- door strakes
R("            k.plate(pts, -21, -28, 'M_Wall', 1.2, 2, taper=2.0)\n","            with k.painted(BONE):\n                k.plate(pts, -21, -28, 'M_Wall', 1.2, 2, taper=2.0)\n")

# --- lock drum
a=s.index("def _lock(k, sign):"); b=s.index("def blast_door(which):")
s=s[:a]+'''def _lock(k, sign):
    """Half of the central lock on each face: a recessed gear race, a stepped rotor and five radial bolts."""
    cz = 170

    def arc(r, t0=0.0, t1=180.0, n=36):
        return [(sign * (.5 + r * math.sin(math.radians(t0 + (t1 - t0) * i / n))), cz + r * math.cos(math.radians(t0 + (t1 - t0) * i / n))) for i in range(n + 1)]

    def band(r0, r1, t0=0.0, t1=180.0, n=36):
        return arc(r1, t0, t1, n) + arc(r0, t0, t1, n)[::-1]

    def polar(r, deg):
        return sign * (.5 + r * math.sin(math.radians(deg))), cz + r * math.cos(math.radians(deg))
    for face in (1, -1):
        with k.at(S(1, face, 1)):
            # Race: a dark annular well between a heavy retaining ring and the rotor.
            k.plate(arc(100), -21, -23.5, 'M_Composite', .5, 1)
            k.plate(band(84, 100), -21, -33, 'M_Trim', 1.6, 2, taper=2.2)
            for i in range(24):
                deg = 3.75 + i * 7.5
                if i % 4 != 2:
                    x, z = polar(92, deg)
                    k.bolt((x, -33, z), r=1.2, h=1.0)
            # Gear teeth run round the race and give the drum a machined rhythm.
            for i in range(15):
                deg = 6 + i * 12
                x, z = polar(77, deg)
                with k.at(T(x, -23.5, z) @ Ry(sign * deg)):
                    k.box(-3.2, 3.2, -7, 0, -7, 7, 'M_Trim', .7, 2)
            # Rotor: stepped disc, bone painted, with bolt circle and an index arc in hazard.
            with k.painted(BONE):
                k.plate(arc(68), -23.5, -36, 'M_Wall', 1.6, 2, taper=2.6)
            k.plate(band(50, 54, 20, 80, 12), -36, -36.6, 'M_Hazard', .2, 1)
            k.plate(band(50, 54, 100, 160, 12), -36, -36.6, 'M_Hazard', .2, 1)
            for i in range(6):
                x, z = polar(44, 15 + i * 30)
                k.bolt((x, -36, z), r=1.8, h=1.5)
            k.plate(arc(36), -36, -41, 'M_Trim', 1.2, 2, taper=1.4)
            k.plate(arc(24), -41, -44, 'M_Composite', .5, 1, taper=.8)
            k.plate(arc(12), -44, -49, 'M_Trim', 1.0, 2, taper=1.6)
            # Radial bolts: a guide housing, a polished pin and an anchor block in the armour.
            for i in range(5):
                deg = 30 + i * 30
                x, z = polar(0, deg)
                with k.at(T(x, -26, z) @ Ry(sign * deg)):
                    k.plate(crect(-13, 62, 13, 90, 2), -8, 7, 'M_Wall', 1.1, 2, plane='XY' if False else 'XZ', taper=1.2)
                    k.box(-9, 9, -9.2, -7, 66, 86, 'M_Composite', .3, 1)
                    k.bolts([(sx * 9.5, -8, zz) for sx in (-1, 1) for zz in (66, 86)], r=1.0, h=.8)
                    with k.at(T(0, -1, 88)):
                        k.lathe([(4.6, 0), (4.6, 22), (3.8, 24), (0.01, 24)], 'M_Trim', 14, 0, edge=.4)
                        k.lathe([(5.8, 0), (5.8, 3), (4.6, 4)], 'M_Trim', 14, 0)
                    k.plate(crect(-12, 104, 12, 118, 2), 4, -7, 'M_Trim', 1.0, 2, taper=.9)
                    k.bolts([(sx * 8, -7, 111) for sx in (-1, 1)], r=1.3, h=1.0)


'''+s[b:]
s=s.replace("'M_Wall', 1.1, 2, plane='XY' if False else 'XZ', taper=1.2)","'M_Wall', 1.1, 2, taper=1.2)")

# --- rifle
a=s.index("def rifle(k):"); b=s.index("def weapon_rack():")
s=s[:a]+'''def rifle(k):
    """Meridian service carbine, 92 long, along local +X, muzzle up, in the XZ plane at y=0."""
    # Receiver in two skins, so it has a parting line and a visible thickness.
    body = [(0, -2), (14, -2), (22, -3), (46, -3), (49, 0), (60, 0), (60, 6.5), (44, 7.5), (26, 7.5), (20, 6), (0, 6)]
    k.plate(body, -2.6, 2.6, 'M_Trim', .35, 2, taper=.25)
    k.plate([(6, -.5), (24, -1.2), (44, -1.2), (44, 5.4), (6, 4.6)], -3.0, 3.0, 'M_Wall', .3, 1, taper=.3)
    k.box(30, 42, -3.3, 3.3, 3, 5.4, 'M_Composite', .2, 1)
    # Handguard with cooling slots; the barrel is seen through them.
    k.plate(crect(46, -.8, 74, 6.8, 1.2), -2.9, 2.9, 'M_Composite', .4, 2, taper=.3)
    for x in (51, 57, 63, 69):
        k.box(x - 1.6, x + 1.6, -3.1, 3.1, 2.2, 5.0, 'M_Trim', .15, 1)
    with k.at(aim((60, 0, 3.2), (1, 0, 0))):
        k.lathe([(1.3, 0), (1.3, 30), (1.9, 31), (1.9, 34), (2.4, 34.6), (2.4, 38), (1.9, 38.6), (1.9, 40.6), (2.4, 41.2), (2.4, 44), (.2, 44.4)], 'M_Trim', 12)
    # Top rail with real teeth, and a sealed optic on two mounts.
    k.box(6, 72, -1.5, 1.5, 7.2, 8.3, 'M_Trim', .15, 1)
    for x in np.arange(8, 72, 3.2):
        k.box(float(x) - .7, float(x) + .7, -1.7, 1.7, 8.2, 9.0, 'M_Trim', .1, 1)
    with k.at(aim((20, 0, 13.6), (1, 0, 0))):
        k.lathe([(.2, -.4), (2.9, 0), (2.9, 4), (2.2, 5), (2.2, 15), (2.9, 16), (2.9, 21), (.2, 21.4)], 'M_Composite', 14)
    for x in (24, 36):
        k.box(x - 1.8, x + 1.8, -1.9, 1.9, 8.8, 11.4, 'M_Trim', .2, 1)
    # Grip, magazine and trigger guard hang from the receiver at their own angles.
    k.plate([(17, -2), (27, -2), (22, -17), (13, -18)], -2.2, 2.2, 'M_Composite', .5, 2, taper=.35)
    k.plate([(31, -3), (41, -3), (45, -21), (35, -23)], -2.0, 2.0, 'M_Trim', .4, 2, taper=.3)
    k.box(32, 40, -2.3, 2.3, -7, -5, 'M_Composite', .2, 1)
    k.tube([(26, -3, -2.5), (27, 0, -7), (31, 0, -7.4), (32, 0, -3)], .5, 'M_Trim', 6, rad=1.2)
    # Skeleton stock: a real opening, with a rubber butt pad.
    k.ring([(0, -2), (0, 6), (-26, 5.5), (-28, -8), (-23, -8), (-10, -2)], [(-4, 0), (-4, 3.4), (-22, 2.8), (-23.5, -5), (-21, -5), (-9, 0)], -1.5, 1.5, 'M_Composite', .35, 1, taper=.15)
    k.box(-31, -27.6, -2.2, 2.2, -9, 7, 'M_Rubber', .6, 2)
    k.box(46, 58, -3.0, -2.8, 1.2, 2.0, 'M_Light', 0)


'''+s[b:]
s=s.replace("""        k.lathe([(1.4, 0), (1.4, 9)], 'M_Trim', 8)
        with k.at(T(0, 0, 9)):""","""        k.lathe([(1.4, 0), (1.4, 9)], 'M_Trim', 8)
        with k.at(T(0, 0, 9)):""")

# --- breach
a=s.index("    # The torn skin: a polar sheet"); b=s.index("def viewport():")
s=s[:a]+'''    # The torn skin: a polar sheet whose rings peel into the room near the hole.
    # The outer face keeps its paint; the inner face and lip are raw, bright, freshly torn metal.
    nt, nr = 260, 26
    verts_front, verts_back = [], []
    for j in range(nr + 1):
        t = j / nr
        for i in range(nt):
            th = 2 * math.pi * i / nt
            ct, st = math.cos(th), math.sin(th)
            sc = min(166 / max(abs(ct), 1e-4), 218 / max(abs(st), 1e-4))
            inner = _tear(th)
            r = inner + (sc - inner) * (t ** .8)
            x, z = cx + ct * r, cz + st * r
            peel = (1 - t) ** 2.8
            lobes = .55 + .45 * math.sin(th * 5 + 2) * math.sin(th * 2 + 1)
            pull = 56 * peel * lobes
            # Curl the petal: the tip turns back towards the wall.
            curl = 16 * (1 - t) ** 7 * math.sin(th * 3)
            bend = noise.noise(Vector((x * .03, z * .03, 3))) * 7 * (1 - t) ** .7
            crease = abs(noise.noise(Vector((x * .07, z * .07, 7)))) * 6 * (1 - t) ** 1.1
            y = -19 - pull - bend + crease + curl * .3
            x += ct * pull * .22 + curl * st * .6
            z += st * pull * .22 - curl * ct * .6
            verts_front.append((x, y, z))
            verts_back.append((x + ct * 1.0, y + 2.6, z + st * 1.0))
    faces_f, faces_b = [], []
    for j in range(nr):
        for i in range(nt):
            n = (i + 1) % nt
            a, b, c, d = j * nt + i, j * nt + n, (j + 1) * nt + n, (j + 1) * nt + i
            faces_f.append((d, c, b, a))
            faces_b.append((a, b, c, d))
    k.mesh_part(verts_front, faces_f, 'M_Wall')
    k.mesh_part(verts_back, faces_b, 'M_Trim')
    rim = [verts_front[i] for i in range(nt)] + [verts_back[i] for i in range(nt)]
    k.mesh_part(rim, [(nt + i, nt + (i + 1) % nt, (i + 1) % nt, i) for i in range(nt)], 'M_Trim')
    k.EDGE[-nt * 4:] = [1.0] * (nt * 4)
    # Broken stiffeners run into the hole and stop, jagged.
    for x0, x1, z, stop in ((30, 170, 84, 1), (230, 370, 84, -1), (30, 150, 346, 1), (250, 370, 346, -1)):
        k.box(min(x0, x1), max(x0, x1), -18, -5, z - 4, z + 4, 'M_Trim', .6, 2)
    # The repair is the hero: a riveted doubler welded over the hole, with sealant squeezed out around it.
    patch = crect(-112, -106, 118, 110, (22, 12, 30, 16))

    def densify(poly, step):
        out = []
        for p, q in zip(poly, poly[1:] + poly[:1]):
            n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / step))
            out += [(p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n) for i in range(n)]
        return out
    rim_pts = densify(patch, 5.0)
    with k.at(T(cx, -41, cz) @ Ry(3.5)):
        k.plate(patch, 0, -6, 'M_Wall', 1.6, 2, taper=1.0)
        # Hand-laid weld bead: lumpy, and it wanders along the edge. Closed by repeating its first point.
        bead = [(p[0] + 1.2 * noise.noise(Vector((p[0] * .1, p[1] * .1, 1))), .4, p[1] + 1.2 * noise.noise(Vector((p[0] * .1, p[1] * .1, 2)))) for p in rim_pts]
        k.tube([Vector(p) for p in bead + bead[:1]], 2.0, 'M_Trim', 6, caps=False,
               rf=lambda f: 1 + .28 * math.sin(f * 900) + .14 * math.sin(f * 2300))
        for i, p in enumerate(densify(offset_poly(patch, -9), 26.0)):
            k.bolt((p[0], -6, p[1]), r=1.7, h=1.3)
        # A second, smaller plate where the first was not enough.
        with k.at(Ry(-9) @ T(-22, -6, 16)):
            with k.painted(CARGO):
                doubler = crect(-62, -48, 82, 44, (8, 14, 8, 20))
                k.plate(doubler, 0, -4.4, 'M_Wall', 1.1, 2, taper=.7)
            for p in densify(offset_poly(doubler, -6), 21.0):
                k.bolt((p[0], -4.4, p[1]), r=1.4, h=1.0)
            k.decal((2, 2), 8, -8, 62, y=-4.5, h=31)
    # Sealant: a pressure-fed mass behind the patch that squeezes out in beads along tear and plate edge.
    ball = bpy.data.metaballs.new('foam')
    ball.resolution = samples_res
    ball.threshold = .7
    ob = bpy.data.objects.new('foam', ball)
    bpy.context.scene.collection.objects.link(ob)
    rng = np.random.default_rng(9)
    for _ in range(26):
        th, r = rng.uniform(0, 6.283), math.sqrt(rng.uniform()) * 112
        e = ball.elements.new()
        e.co = (cx + math.cos(th) * r, rng.uniform(-12, -4), cz + math.sin(th) * r)
        e.radius = rng.uniform(38, 56)
    for i in range(120):
        th = rng.uniform(0, 6.283)
        r = _tear(th) * rng.uniform(.84, .99)
        e = ball.elements.new()
        e.co = (cx + math.cos(th) * r, rng.uniform(-34, -20), cz + math.sin(th) * r)
        e.radius = rng.uniform(13, 27)
    for p in rim_pts[::2]:
        if rng.uniform() < .62:
            e = ball.elements.new()
            e.co = (cx + p[0] * 1.03, -36 + rng.uniform(-3, 3), cz + p[1] * 1.03)
            e.radius = rng.uniform(9, 17)
    for i in range(10):
        # Runs that slumped down the wall before they cured.
        th = rng.uniform(math.pi * 1.15, math.pi * 1.85)
        r = _tear(th) * .98
        x, z = cx + math.cos(th) * r, cz + math.sin(th) * r
        for s in range(int(rng.integers(3, 7))):
            e = ball.elements.new()
            e.co = (x + rng.uniform(-2, 2), rng.uniform(-30, -25), z - s * 9)
            e.radius = 11 - s * 1.1
    bpy.context.view_layer.update()
    dep = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dep))
    bpy.data.objects.remove(ob)
    temp = bpy.data.objects.new('foam_mesh', me)
    bpy.context.scene.collection.objects.link(temp)
    dec = temp.modifiers.new('d', 'DECIMATE')
    dec.ratio = min(1.0, 34000 / max(1, len(me.polygons)))
    dep = bpy.context.evaluated_depsgraph_get()
    done = bpy.data.meshes.new_from_object(temp.evaluated_get(dep))
    verts = []
    for v in done.vertices:
        p = v.co
        # Billow, not lumps: cured sealant is rounded blisters meeting in tight creases.
        q = Vector((p.x * .06, p.y * .06, p.z * .06))
        n = 0
        for o, amp in ((1, 5.0), (2.3, 2.4), (5.1, 1.0)):
            n += abs(noise.noise(q * o)) * amp
        verts.append(tuple(p + v.normal * (n - 1.5)))
    k.mesh_part(verts, [tuple(p.vertices) for p in done.polygons], 'M_Foam')
    bpy.data.objects.remove(temp)
    # Emergency strongbacks across the patch, anchored into the ribs.
    for z, tilt in ((318, -9), (150, 7)):
        with k.at(T(200, -52, z) @ Ry(tilt)):
            k.plate(crect(-182, -9, 182, 9, 2.5), -6, 0, 'M_Trim', .9, 2)
            k.plate(crect(-148, -5, 148, 5, 1), -7, -6, 'M_Hazard', .25, 1)
            for s in (-1, 1):
                k.box(s * 170 - 8, s * 170 + 8, -2, 40, -6, 6, 'M_Trim', .8, 2)
                k.bolt((s * 176, -6, 0), r=2.0)
                k.bolt((s * 164, -6, 0), r=2.0)
    # Severed cables that fell out of the wall before the patch went on.
    for x, r, drop, xe in ((120, 1.8, 120, 116), (136, 1.2, 80, 142), (262, 2.2, 148, 272), (250, 1.3, 90, 247)):
        k.tube([(x, -14, 380), (x + 2, -40, 372), (x + 4, -66, 340), ((x + xe) / 2, -70, 300), (xe, -66, 380 - drop - 80)], r, 'M_Rubber', 8, rad=18)
    return k


'''+s[b:]
R("def hull_breach(samples_res=3.4):","def hull_breach(samples_res=2.4):")

# --- foam look: neutral cured sealant
R("for count, radius, depth in ((180, 34, 1.0), (1500, 12, .5), (9000, 4, .22)):","for count, radius, depth in ((40, 30, .7), (700, 11, .45), (16000, 3.5, .3)):")
R("    pale, deep = np.array((.58, .44, .24)), np.array((.16, .1, .05))\n    base = pale * (.82 + tone * .3)\n","    pale, deep = np.array((.5, .49, .44)), np.array((.1, .095, .08))\n    base = pale * (.76 + tone * .34)\n")

# --- new paint, metal and light textures
R("def _text_scene():",'''def scratches(size, rng, count, lengths, curve=.0008):
    """Seamless thin random scratches, accumulated on a torus."""
    canvas = np.zeros((size, size), np.float32)
    for _ in range(count):
        n = int(rng.uniform(*lengths))
        a = rng.uniform(0, 6.283) + np.cumsum(rng.normal(0, curve * 40, n)) * .05
        x = rng.uniform(0, size) + np.cumsum(np.cos(a))
        y = rng.uniform(0, size) + np.cumsum(np.sin(a))
        taper = np.sin(np.linspace(0, math.pi, n)) ** .6 * rng.uniform(.2, 1)
        np.maximum.at(canvas, (y.astype(int) % size, x.astype(int) % size), taper)
    return canvas


def soft(a, passes=2):
    for _ in range(passes):
        a = (a * 2 + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 6
    return a


def paint_textures():
    """Clean, tiling, paint-only surfaces. All panel logic is modelled, so these carry no lines or type."""
    size = 2048
    rng = np.random.default_rng(21)
    peel = tile_noise(size, 31, 3, 180)
    big = tile_noise(size, 32, 5, 3)
    mid = tile_noise(size, 33, 6, 14)
    fine = scratches(size, rng, 900, (30, 260))
    deep = scratches(size, rng, 60, (120, 520))
    # Height in arbitrary units: orange peel, slow undulation of plate, then scratches through the coat.
    height = peel * .10 + big * .22 - soft(fine, 1) * .10 - soft(deep, 1) * .30
    chip = np.clip((tile_noise(size, 34, 7, 9) - .71) * 22, 0, 1)
    height = height - soft(chip, 1) * .22
    albedo = .70 * (.86 + big * .2 + (mid - .5) * .12)
    albedo = albedo * (1 - fine * .0) + fine * .16 + deep * .22
    colour = np.dstack((albedo, albedo, albedo * .985))
    primer = np.array((.20, .19, .18))
    colour = colour * (1 - chip[..., None]) + primer * chip[..., None]
    rough = .50 + (mid - .5) * .16 + (big - .5) * .1 + chip * .2 - deep * .12
    ao = 1 - soft(deep + chip, 2) * .35
    write_png(TEX / 'T_KitPaint_BaseColor.png', np.clip(colour, 0, 1) ** (1 / 2.2), 8)
    write_png(TEX / 'T_KitPaint_Normal.png', height_normal(height, 5.0), 16)
    write_png(TEX / 'T_KitPaint_ORM.png', np.dstack((ao, np.clip(rough, 0, 1), np.zeros_like(ao))), 8)
    # Bead-blasted gunmetal with a faint rolling direction along U: cool, and never wood.
    blast = tile_noise(size, 41, 2, 300)
    grain = tile_noise(size, 42, 4, 40)
    # Stretch the grain along rows by averaging it across columns.
    for shift in (3, 7, 17, 41, 97):
        grain = (grain + np.roll(grain, shift, 1)) / 2
    wearlines = scratches(size, rng, 1500, (40, 340))
    dings = np.clip((tile_noise(size, 43, 6, 7) - .73) * 18, 0, 1)
    height = blast * .07 + (grain - .5) * .05 - soft(wearlines, 1) * .06 - soft(dings, 2) * .3
    mottle = tile_noise(size, 44, 6, 5)
    v = .40 + (mottle - .5) * .14 + (grain - .5) * .08 + wearlines * .14
    colour = np.dstack((v * .94, v * .98, v * 1.05))
    rough = .40 + (mottle - .5) * .22 + (blast - .5) * .10 - wearlines * .12 + dings * .1
    ao = np.ones_like(rough)
    write_png(TEX / 'T_KitMetal_BaseColor.png', np.clip(colour, 0, 1) ** (1 / 2.2), 8)
    write_png(TEX / 'T_KitMetal_Normal.png', height_normal(height, 4.0), 16)
    write_png(TEX / 'T_KitMetal_ORM.png', np.dstack((ao, np.clip(rough, 0, 1), np.ones_like(ao))), 8)
    # LED diffuser: soft emitter bands, so lamps carry structure instead of clipping to flat white.
    n = 512
    yy, xx = np.mgrid[0:n, 0:n]
    bands = .5 + .5 * np.cos(yy / n * 2 * math.pi * 6)
    dots = .5 + .5 * np.cos(xx / n * 2 * math.pi * 24)
    e = .62 + bands * .30 + bands * dots * .10 + (tile_noise(n, 45, 4, 4) - .5) * .08
    write_png(TEX / 'T_KitLight_Emissive.png', np.dstack((e, e, e)) ** (1 / 2.2), 8)


def _text_scene():''')
open(p,'w',encoding='utf8').write(s)
