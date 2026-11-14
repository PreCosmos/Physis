# ------------------------------------------------------------------ frigate

def frigate_cfg():
    def mark(P, N, D, colour, zone):
        band = (np.abs(P[..., 0] - 420) < 34) & (zone == PRIMARY)
        colour[band] = ZONE_COLOURS[ACCENT]
        stamp(P, N, colour, zone, TEXT['FNS-0417'], 58, (640, 70), 1)
        stamp(P, N, colour, zone, TEXT['FNS-0417'], 58, (640, 70), -1)
    return {'seed': 22, 'tile_cm': 900, 'height_scale': 1.1, 'length': 2600, 'ao': 180, 'hazard_pitch': 40, 'soot_x': -1250,
            'window_pitch': (11, 24), 'window_size': (6, 8), 'mark': mark}


def frigate(size):
    """Fast escort: blade hull, swept wing roots carrying outboard drives, missile deck, one hangar in the belly."""
    kit = Kit('SM_Ship_Frigate', HUMAN_SLOTS, 12)
    rng = kit.rng
    w = warship_section
    hull = Hull([(-1180, w(250, 230, 170, 40, 30, 20)), (-1130, w(310, 270, 200, 40, 34, 24)), (-1090, w(340, 290, 212, 40, 34, 26)),
                 (-470, w(380, 310, 226, 40, 36, 28)), (-440, w(350, 290, 212, 40, 34, 26)), (-400, w(330, 276, 204, 36, 32, 26)),
                 (210, w(270, 226, 170, 24, 26, 20)), (240, w(250, 212, 160, 24, 24, 18)), (280, w(236, 202, 152, 22, 22, 16)),
                 (800, w(130, 130, 96, 8, 12, 8)), (1190, w(44, 58, 42, 0, 6, 3)), (1290, w(14, 26, 18, 0, 3, 1))])
    kit.add(hull.loft(bevel=3), tone=.5)
    armour(kit, hull, 9, -1080, -480, rng, (140, 180, 220), 8, .3, .96, gap=9)
    armour(kit, hull, 9, -390, 200, rng, (130, 170), 8, .36, .96, [(-140, 90)], gap=9)
    armour(kit, hull, 9, 290, 760, rng, (110, 150), 7, .1, .96, [(350, 560)], gap=8)
    for k, ts, tier in ((8, 10, True), (3, 9, True), (2, 8, True), (1, 7, False)):
        armour(kit, hull, k, -1080, -480, rng, (160, 210, 260), ts, .04, .96, gap=9, tier=tier)
        armour(kit, hull, k, -390, 200, rng, (140, 180, 230), ts, .04, .96, gap=9, tier=tier)
        armour(kit, hull, k, 290, 760, rng, (120, 170), ts * .8, .04, .96, gap=8, tier=tier)
    armour(kit, hull, 7, -1080, -480, rng, (130, 170), 6, .1, .9, gap=9, win=True, tier=False)
    armour(kit, hull, 7, -390, 200, rng, (130, 170), 6, .1, .9, gap=9, win=True, tier=False)
    trench_dressing(kit, hull, -1080, -480, 60)
    trench_dressing(kit, hull, -390, 200, 60)
    # Wing roots: broad swept slabs. Their silhouette is what separates this ship from the cruiser.
    wing = [(-1120, 300), (-470, 300), (-720, 880), (-1040, 960), (-1180, 960), (-1250, 760)]
    plate = slab(wing, 44, HULL, PRIMARY, 3, 2)
    kit.sym(plate, mat((0, 0, -22)), tone=.45)
    kit.sym(slab([(-1080, 330), (-560, 330), (-740, 760), (-1060, 830)], 12, TRIM, SECONDARY, 1.6), mat((0, 0, 22)), tone=.25)
    kit.sym(slab([(-1040, 560), (-820, 500), (-780, 700), (-980, 790)], 8, HULL, ACCENT, 1.2), mat((0, 0, 33)), tone=.3)
    # Outboard drive pods.
    pod = loft([rect(112, -90, 90, 26, x * 1.0) * np.array((1, s, s)) for x, s in ((-1290, .7), (-1240, 1), (-860, 1), (-690, .75), (-520, .22))], HULL, PRIMARY, 3, 2, 20)
    kit.sym(pod, mat((0, 900, 0)), tone=.4)
    kit.sym(turret(46, 2, 200), mat((-900, 900, 86)), tone=.2)
    kit.sym(lathe([(-1300, 80), (-1300, 92), (-1240, 92), (-1240, 70)], 32, 'X', TRIM, METAL, cap=False), mat((0, 900, 0)), tone=.2)
    kit.sym(drive_bell(84, 150, 32, 12), mat((-1296, 900, 0)), tone=.3)
    kit.add(lathe([(-1208, 160), (-1208, 205), (-1160, 205), (-1160, 150)], 40, 'X', TRIM, METAL, cap=False), mat((0, 0, 30)), tone=.3)
    kit.add(drive_bell(150, 250, 40, 16), mat((-1190, 0, 30)), tone=.3)
    # Vertical launch deck: a real grid of cell hatches.
    for i, x in enumerate(np.arange(-340, 180, 46)):
        for y in (-108, -62, -16, 30, 76):
            half = hull.at(x)
            z = half[-1][1] * .98 - abs(y) * .06
            kit.add(box((36, 36, 7), (x, y + 16, z), TRIM, SECONDARY, 1.0, 2.5), tone=.3)
            kit.add(box((26, 26, 3), (x, y + 16, z + 4), TRIM, HAZARD if (i * 3 + int(y)) % 7 == 0 else METAL, .0, 1.5), tone=.3, uv=.6)
    # Main guns.
    half = hull.at(450)
    kit.add(lathe([(-40, 96), (half[-1][1] + 8, 96), (half[-1][1] + 14, 88)], 28, 'Z', TRIM, SECONDARY, 1.5), mat((450, 0, 0)))
    kit.add(turret(84, 2, 340), mat((450, 0, half[-1][1] + 10)), tone=.35)
    # Command tower: one tall stepped block, set right aft so the profile stays lean.
    for x0, x1, hw, z0, z1 in ((-1040, -520, 160, 270, 400), (-980, -600, 118, 390, 490), (-930, -650, 84, 480, 560)):
        sections = [rect(hw * .7, z0, z1 * .96, 7, x0), rect(hw, z0, z1, 8, x0 + 40), rect(hw, z0, z1, 8, x1 - 70), rect(hw * .7, z0, z1 * .9, 7, x1)]
        kit.add(loft(sections, HULL, PRIMARY, 1.8, 2, 20), win=1.0, tone=.4)
        kit.add(box(((x1 - x0) * .7, hw * 1.6, 7), ((x0 + x1) / 2 - 20, 0, z1 + 2), TRIM, SECONDARY, 1), tone=.2)
    glass = [np.array([(-720, y, 548) for y in (-66, 66)]), np.array([(-648, y, 512) for y in (-48, 48)])]
    kit.add(loft(glass, LIGHT, COOL, cap=False, closed=False), slot=LIGHT)
    kit.add(mast(240, 6.5), mat((-880, 0, 560)), tone=.1)
    kit.add(dish(52), mat((-790, 46, 564), (.3, .1, 0)), tone=.1)
    # Belly hangar: pocket in a keel module.
    rows = []
    for x, hw, depth in ((-860, 90, 0), (-800, 200, 0), (-690, 210, 0), (-680, 210, 130), (-120, 210, 130), (-110, 210, 0), (-40, 210, 0), (120, 90, 0)):
        rows.append(np.array([(x, -hw * .3, -160), (x, hw - depth, -190), (x, hw - depth, -244), (x, hw, -244) if depth == 0 else (x, hw - depth, -244), (x, hw, -270), (x, hw * .4, -300), (x, -hw * .4, -300), (x, -hw, -270), (x, -hw + depth, -244), (x, -hw + depth, -190), (x, hw * .3, -160)]))
    kit.add(loft(rows, HULL, PRIMARY, 2.2, 2, 20), tone=.4)
    kit.sym(box((470, 5, 44), (-400, 72, -216), LIGHT, BRIGHT), slot=LIGHT, uv=.5)
    for x in np.arange(-660, -120, 62):
        kit.sym(box((12, 118, 96), (x, 126, -216), TRIM, SECONDARY, .7), tone=.5)
    kit.sym(box((550, 12, 12), (-400, 208, -186), TRIM, HAZARD, .8), uv=1.4)
    for x in (-980, -700, -320, 40, 340, 620):
        half = hull.at(x)
        p = (half[8] + half[9]) / 2
        kit.sym(point_defence(26), mat((x, p[0], p[1] + 5), (0, -.5, 0)), tone=.3)
    for side, zone in ((1, GREEN), (-1, RED)):
        kit.add(box((22, 7, 7), (-1100, side * 962, 0), LIGHT, zone), slot=LIGHT)
    kit.sym(dish(40), mat((720, 118, 100), (.6, .1, 0)), tone=.1)
    return kit


# ------------------------------------------------------------------ First Ones

def blade(length, width, thick, seed, sides=6, belly=.42, tip=.0, glow=(0, 3), seam=None, stations=None):
    """A crystal blade along +X from 0. Big planar facets; chosen long edges become luminous seams."""
    rng = np.random.default_rng(seed)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + rng.uniform(-.17, .17, sides) + .4
    rad = rng.uniform(.82, 1.12, sides)
    prof = np.stack((np.cos(ang) * rad * width / 2, np.sin(ang) * rad * thick / 2), 1)
    stations = stations or ((0, .012), (belly * .34, .62), (belly, 1), (belly + (1 - belly) * .46, .66), (1, .012))
    bm = bmesh.new()
    rows = []
    for i, (t, s) in enumerate(stations):
        # Facet edges drift between stations so faces are never parallel to the axis.
        drift = rng.uniform(-.1, .1, (sides, 2)) * (width, thick) * s * (0 < i < len(stations) - 1)
        lean = np.array((tip * width * t * t, tip * .3 * thick * t))
        pts = prof * s + drift + lean
        rows.append([bm.verts.new((t * length, y, z)) for y, z in pts])
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    for a, b in zip(rows, rows[1:]):
        for j in range(sides):
            k = (j + 1) % sides
            bm.faces.new((a[j], a[k], b[k], b[j]))
    bm.edges.ensure_lookup_table()
    long_edges = []
    for j in glow:
        for a, b in zip(rows, rows[1:]):
            e = bm.edges.get((a[j], b[j]))
            if e:
                long_edges.append(e)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) == 4], quad_method='SHORT_EDGE')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    seam = seam if seam is not None else width * .018
    new = bevel_edges(bm, seam, 1, 0, long_edges)
    for face in new:
        face.material_index = GLOW
    glows = set(new)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(9) and not any(f in glows for f in e.link_faces)]
    bevel_edges(bm, seam * .16, 1, 0, edges)
    return from_bm(bm, CRYSTAL, 0, keep=True)


def monolith_arc(radius, a0, a1, width, thick, seed):
    """One curved piece of a broken halo: a long gem bent around the ship's axis."""
    rng = np.random.default_rng(seed)
    n = 5
    prof = [(1, .25), (.42, 1), (-.5, .86), (-1, -.1), (-.3, -1), (.6, -.8)]
    prof = np.array(prof) * (thick / 2, width / 2)
    sections = []
    for i in range(n):
        t = i / (n - 1)
        a = a0 + (a1 - a0) * t
        s = .05 if i in (0, n - 1) else (.72 if i in (1, n - 2) else 1) * rng.uniform(.92, 1.06)
        pts = []
        for r, x in prof * s:
            rr = radius + r
            pts.append((x, math.cos(a) * rr, math.sin(a) * rr))
        sections.append(np.array(pts))
    bm = bmesh.new()
    rows = [[bm.verts.new(p) for p in s] for s in sections]
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    for a, b in zip(rows, rows[1:]):
        for j in range(6):
            k = (j + 1) % 6
            bm.faces.new((a[j], a[k], b[k], b[j]))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) == 4], quad_method='SHORT_EDGE')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    long_edges = [bm.edges.get((a[1], b[1])) for a, b in zip(rows, rows[1:])]
    new = bevel_edges(bm, width * .014, 1, 0, [e for e in long_edges if e])
    for face in new:
        face.material_index = GLOW
    glows = set(new)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(9) and not any(f in glows for f in e.link_faces)]
    bevel_edges(bm, width * .003, 1, 0, edges)
    return from_bm(bm, CRYSTAL, 0, keep=True)


def filament(a, b, hw):
    return beam(a, b, hw, slot=GLOW, zone=0, c=0)


def octa(r, stretch=1.5):
    # Luminous core.
    bm = bmesh.new()
    verts = [bm.verts.new(v) for v in ((r * stretch, 0, 0), (-r * stretch, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r), (0, 0, -r))]
    for f in ((0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2), (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5)):
        bm.faces.new([verts[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return from_bm(bm, GLOW, 0)


def vigil(size):
    """A warship that does not touch itself: split lance, floating core, broken crown, ordered wake."""
    kit = Kit('SM_Ship_Vigil', FIRST_SLOTS, 13)
    L = 7000
    # Fore lance and aft lance point at each other across the core.
    kit.add(blade(4300, 1160, 720, 3, 7, .34, glow=(0, 3, 5)), mat((-800 + 0, 0, 40)), tone=.5, uv=1.2)
    kit.add(blade(2500, 980, 620, 5, 6, .66, glow=(1, 4)), mat((-3500, -40, -30)), tone=.72, uv=1.2)
    # Asymmetric flanking blades: one long, one short, the rest of the balance comes from the crown.
    kit.add(blade(3600, 560, 300, 7, 5, .3, tip=.1, glow=(2,)), mat((-1400, 1240, 180), (.28, -.02, .05)), tone=.3)
    kit.add(blade(2300, 400, 240, 9, 5, .36, glow=(0,)), mat((-2100, -1020, -340), (-.2, .05, -.07)), tone=.8)
    kit.add(blade(1500, 280, 170, 11, 5, .4, glow=(1,)), mat((-300, 1860, 520), (.5, -.06, .1)), tone=.2)
    kit.add(octa(330, 2.0), mat((-1000, 0, 10)), tone=.5, uv=.3)
    kit.add(octa(150, 2.0), mat((-1000, 0, 10)), tone=.5, uv=.3)
    # Crown: a tilted halo around the core, unfinished on purpose, stepping down in size.
    crown = mat((-1000, 0, 60), (.0, .24, .1))
    angles = [(-.35, .65, 620, 300), (.72, 1.5, 520, 250), (1.58, 2.2, 430, 210), (2.28, 2.75, 340, 170), (2.84, 3.15, 260, 130), (3.22, 3.4, 190, 96), (3.48, 3.58, 130, 66)]
    ends = []
    for i, (a0, a1, w, t) in enumerate(angles):
        kit.add(monolith_arc(2280, a0, a1, w, t, 20 + i), crown, tone=.2 + i * .1)
        m = (a0 + a1) / 2
        ends.append(np.array(crown) @ np.array((0, math.cos(m) * 2150, math.sin(m) * 2150, 1)))
    # Tethers of light from core to crown: all the structure this ship admits to.
    for p in ends[:4]:
        kit.add(filament((-1000, 0, 10), tuple(p[:3]), 5), tone=.5, uv=.3)
    # Lesser ring, a counterweight behind.
    ring_at = mat((-3000, 0, -60), (.1, -.14, 0))
    for i in range(5):
        a = -1.2 + i * .78 + .2
        kit.add(monolith_arc(1160, a, a + .56, 300 - 30 * i, 150 - 14 * i, 40 + i), ring_at, tone=.6)
    # Wake: ordered shards that shrink along a falling curve.
    for i in range(11):
        t = i / 10
        x = -3400 + 2900 * t
        z = -760 - 520 * math.sin(t * math.pi * .9) * (1 - t * .4)
        y = 260 * math.sin(t * 5)
        s = 1 - t * .72
        kit.add(blade(420 * s + 110, 92 * s + 28, 58 * s + 16, 60 + i, 5, .42, glow=(0,), seam=5), mat((x, y, z), (0, -.1, .03)), tone=.35)
    return kit


def shard(size):
    """Fast attack craft: a cleft lance with a fan of feathers on one side only."""
    kit = Kit('SM_Ship_Shard', FIRST_SLOTS, 14)
    kit.add(blade(2800, 620, 340, 31, 6, .36, glow=(0, 3)), mat((-1400, 90, 18), (0, 0, -.02)), tone=.5, uv=1.2)
    kit.add(blade(2000, 400, 250, 33, 5, .44, glow=(1, 3)), mat((-1400, -300, -60), (0, 0, .05)), tone=.75, uv=1.2)
    kit.add(octa(120, 2.4), mat((-340, -130, -14)), tone=.5, uv=.3)
    for i in range(6):
        t = i / 5
        a = .08 + t * .62
        length = 1320 - 760 * t
        x = -1420 + 300 * t
        y = 500 + 200 * t
        z = -30 + 180 * math.sin(t * 2.4)
        kit.add(blade(length, 190 - 72 * t, 92 - 34 * t, 40 + i, 5, .36, glow=(1,), seam=6), mat((x, y, z), (.18 * t, 0, a - .3)), tone=.3 + t * .3)
    for i in range(5):
        t = i / 4
        kit.add(blade(190 - 90 * t, 60 - 24 * t, 34 - 12 * t, 50 + i, 5, .4, glow=(0,), seam=3), mat((-1640 + 180 * t, -640 + 220 * t, -160 + 40 * t), (0, 0, .1)), tone=.4)
    kit.add(filament((-340, -130, -14), (-1100, 760, 40), 2.5), tone=.5, uv=.3)
    return kit


def voronoi_veil(obj, size, cell, depth, seed, spin=(.31, .7, -.64)):
    # Fracture sheets seen through the surface: position sinks along the normal and slides with
    # facet orientation, so the pattern breaks at each facet the way refraction does.
    def build(nodes, links):
        geometry = nodes.new('ShaderNodeNewGeometry')
        cross = nodes.new('ShaderNodeVectorMath')
        cross.operation = 'CROSS_PRODUCT'
        links.new(geometry.outputs['True Normal'], cross.inputs[0])
        cross.inputs[1].default_value = spin
        scale = nodes.new('ShaderNodeVectorMath')
        scale.operation = 'MULTIPLY_ADD'
        links.new(cross.outputs[0], scale.inputs[0])
        scale.inputs[1].default_value = (depth * 1.3,) * 3
        links.new(geometry.outputs['True Normal'], scale.inputs[2])
        sink = nodes.new('ShaderNodeVectorMath')
        sink.operation = 'MULTIPLY_ADD'
        links.new(geometry.outputs['True Normal'], sink.inputs[0])
        sink.inputs[1].default_value = (-depth,) * 3
        links.new(geometry.outputs['Position'], sink.inputs[2])
        add = nodes.new('ShaderNodeVectorMath')
        add.operation = 'ADD'
        links.new(sink.outputs[0], add.inputs[0])
        links.new(cross.outputs[0], add.inputs[1])
        offset = nodes.new('ShaderNodeVectorMath')
        offset.operation = 'ADD'
        links.new(add.outputs[0], offset.inputs[0])
        offset.inputs[1].default_value = (seed * 3.1, seed * 7.7, seed * 1.3)
        voronoi = nodes.new('ShaderNodeTexVoronoi')
        voronoi.feature = 'DISTANCE_TO_EDGE'
        voronoi.inputs['Scale'].default_value = 1 / cell
        links.new(offset.outputs[0], voronoi.inputs['Vector'])
        return voronoi.outputs['Distance']
    return bake(obj, size, build)[..., 0]


def crystal_detail(px=2048):
    """Tiling cleavage terraces and fine growth lines. Facets stay clean at distance."""
    rng = np.random.default_rng(5)
    y, x = np.mgrid[0:px, 0:px] / px
    height = np.zeros((px, px), np.float32)
    for kx, ky, w in ((3, 1, 1), (1, 4, .6), (5, 2, .4)):
        wave = (x * kx + y * ky + fft_noise(px, 3.2, kx + 90) * .35) % 1
        height += (np.floor(wave * 9) / 9 + np.clip(wave * 9 % 1 - .9, 0, 1)) * w
    height = blur_wrap(height.astype(np.float32), 1.0) * .4 + (fft_noise(px, 1.6, 7, 30) - .5) * .05
    png(TEXTURES / 'T_CrystalDetail_Normal.png', normal_from_height(height, .35), 16)


def first_textures(obj, name, size, cm_per_texel, cfg):
    L = cfg['length']
    maps = bake_maps(obj, size, L * .007, L * .08, cfg['spp'])
    P, N, D = maps['P'], maps['N'], maps['D']
    zone, tone, ao, edge = np.rint(maps['zone']), maps['tone'], np.clip(maps['ao'], 0, 1), maps['edge']
    glowing = zone == 30
    veil1 = np.exp(-voronoi_veil(obj, size, L * .085, L * .012, 1) / .035)
    veil2 = np.exp(-voronoi_veil(obj, size, L * .17, L * .03, 2, (-.6, .2, .77)) / .05)
    veil3 = np.exp(-voronoi_veil(obj, size, L * .045, L * .005, 3, (.8, -.5, .3)) / .03)
    cloud = fft_noise(1024, 2.6, cfg['seed'])
    fog = sample(cloud, D[..., 0] / L * 3, D[..., 1] / L * 3)
    core = np.zeros((size, size), np.float32)
    for c in cfg['cores']:
        core = np.maximum(core, np.exp(-np.linalg.norm(P - np.array(c, np.float32), axis=2) / (L * .13)))
    # Facets each hold a different depth of colour, as cut gems do.
    facet = (np.abs(np.sin(N[..., 0] * 7.1 + N[..., 1] * 13.3 + N[..., 2] * 5.7 + tone * 9)))[..., None]
    shallow = np.array((.05, .22, .29), np.float32)
    deep = np.array((.006, .03, .055), np.float32)
    ice = np.array((.42, .78, .86), np.float32)
    colour = deep + (shallow - deep) * (facet * .5 + fog[..., None] * .45)
    colour = colour + ice * (veil1 * .13 + veil3 * .07 + veil2 * .1)[..., None] * (.5 + fog[..., None])
    colour = colour * (.72 + ao[..., None] * .28)
    halo = smooth(.05, .6, edge)
    teal = np.array((.28, 1, .88), np.float32)
    white = np.array((.8, 1, .98), np.float32)
    glow = teal * ((veil1 * .05 + veil2 * .09 + veil3 * .02)[..., None] * (.2 + core[..., None] * 2.2))
    glow += teal * (core ** 2 * .1 * (.6 + fog * .8))[..., None] * (1 - ao[..., None] * .4)
    glow += teal * (halo * .05)[..., None]
    pulse = .62 + .38 * np.sin(P[..., 0] / L * 34 + fog * 5)
    seam_colour = teal * (1 - core[..., None]) + white * core[..., None]
    glow[glowing] = (seam_colour * (pulse * (.8 + core * .6))[..., None])[glowing]
    colour[glowing] = (.5, .95, .9)
    rough = .07 + facet[..., 0] * .1 + fog * .1 + veil3 * .1
    rough = np.where(glowing, .3, rough)
    terrace = np.floor(np.mod((P[..., 0] * .8 + P[..., 2] * .6) / (L * .012) + fog * 6, 40))
    height = (terrace * L * .00016) * smooth(.5, .7, fog)
    # Steps only where the frost cloud allows, so most of each facet stays polished.
    height = height * ~glowing
    height = np.clip(height, -1e6, 1e6).astype(np.float32)
    orm = np.dstack((ao * .8 + .2, np.clip(rough, .04, 1), np.zeros_like(rough)))
    png(TEXTURES / f'T_{name}_BaseColor.png', srgb(colour))
    png(TEXTURES / f'T_{name}_Normal.png', normal_from_height(height, cm_per_texel), 16)
    png(TEXTURES / f'T_{name}_ORM.png', orm)
    png(TEXTURES / f'T_{name}_Emissive.png', srgb(np.clip(glow, 0, 1)))


# ------------------------------------------------------------------ station

# Playable decks: clear of everything for x -700..19000. Greybox rooms reach x=18400, past the brief's 17000.
SHELL_R = 5200.0
SHELL_N = 48
DECK_END = 19000.0
MOUTH_X = (-1300.0, 1900.0)
STEP = 2 * math.pi / SHELL_N


def polar(r, a, x):
    return (x, math.cos(a) * r, math.sin(a) * r)


def shell_part():
    """Open hull skin: one quad-strip tube with a window cut for each hangar mouth, no caps, no inner surface."""
    xs = sorted(set(list(np.arange(-2400, 19801, 1100)) + list(MOUTH_X)))
    angles = [i * STEP - math.pi / 2 for i in range(SHELL_N)]
    V = [polar(SHELL_R, a, x) for x in xs for a in angles]
    F = []
    for i in range(len(xs) - 1):
        mid = (xs[i] + xs[i + 1]) / 2
        for j in range(SHELL_N):
            centre = (j + .5) % SHELL_N
            if MOUTH_X[0] < mid < MOUTH_X[1] and (min(centre, SHELL_N - centre) < 1 or abs(centre - SHELL_N / 2) < 1):
                continue
            k = (j + 1) % SHELL_N
            a, b, c, d = i * SHELL_N + j, i * SHELL_N + k, (i + 1) * SHELL_N + k, (i + 1) * SHELL_N + j
            F.append((a, b, c, d))
    return Part(V, F, [HULL] * len(F), [PRIMARY] * len(F))


def in_mouth(x0, x1, a0, a1):
    # Is this polar patch over either hangar mouth? Mouth half-span is one shell facet, plus trim.
    if x1 < MOUTH_X[0] - 420 or x0 > MOUTH_X[1] + 420:
        return False
    for centre in (-math.pi / 2, math.pi / 2):
        lo, hi = (a0 - centre + math.pi) % (2 * math.pi) - math.pi, (a1 - centre + math.pi) % (2 * math.pi) - math.pi
        if min(abs(lo), abs(hi)) < STEP * 2.4 or lo * hi < 0 and abs(lo) < 1:
            return True
    return False


def polar_plate(x0, x1, a0, a1, r, t, zone=PRIMARY, slot=HULL, cut=.1, bevel=3.0, curve=2):
    """A curved armour slab on the hull, chamfered at its corners."""
    xc = min((x1 - x0) * cut, 90)
    ac = (a1 - a0) * cut
    rows = []
    for x, e in ((x0, 1), (x0 + xc, 0), (x1 - xc, 0), (x1, 1)):
        arc = np.linspace(a0 + ac * e, a1 - ac * e, curve + 1)
        section = [polar(r - 6, arc[0], x)]
        section += [polar(r + t, a, x) for a in arc]
        section += [polar(r - 6, arc[-1], x)]
        rows.append(section)
    return loft(rows, slot, zone, bevel, 1, 25)


def bay(w=460.0, h=320.0, depth=170.0, lit=True):
    """Casemate bay on +Z, long axis X: raised armoured surround around a real recess."""
    t = 54
    parts = [box((w + t * 2, t, depth), (0, h / 2 + t / 2, depth / 2), HULL, PRIMARY, 4, 10),
             box((w + t * 2, t, depth), (0, -h / 2 - t / 2, depth / 2), HULL, PRIMARY, 4, 10),
             box((t, h, depth * .9), (w / 2 + t / 2, 0, depth * .45), HULL, SECONDARY, 4, 8),
             box((t, h, depth * .9), (-w / 2 - t / 2, 0, depth * .45), HULL, SECONDARY, 4, 8),
             box((w, h, 8), (0, 0, 8), TRIM, DARK)]
    for x in np.linspace(-w * .36, w * .36, 4):
        parts.append(box((12, h, 40), (x, 0, 28), TRIM, SECONDARY))
    if lit:
        parts.append(box((w * .9, 8, 8), (0, h / 2 - 8, depth * .42), LIGHT, WARM))
        parts.append(box((w * .9, 8, 8), (0, -h / 2 + 8, depth * .42), LIGHT, AMBER))
        parts.append(box((w * .8, h * .5, 2), (0, 0, 15), LIGHT, BRIGHT))
    parts.append(box((w + t * 2, 18, 8), (0, h / 2 + t + 8, 5), TRIM, HAZARD))
    return merge(*parts)


def casemate_gun():
    return merge(box((460, 340, 120), (0, 0, 60), HULL, PRIMARY, 5, 16), turret(150, 2, 640, 20))


def emitter():
    """Shield emitter: a tall stalk ending in a ribbed reflector and a cold focus ring."""
    parts = [lathe([(0, 110), (40, 110), (70, 60), (320, 44), (340, 90), (372, 90), (384, 64)], 16, 'Z', TRIM, SECONDARY)]
    parts.append(lathe([(380, 66), (404, 210), (440, 250), (442, 236), (410, 180), (392, 60)], 28, 'Z', TRIM, METAL, cap=False))
    parts.append(lathe([(392, 46), (470, 60), (548, 36), (592, 2)], 12, 'Z', TRIM, METAL))
    parts.append(lathe([(452, 214), (456, 236), (462, 236), (466, 214)], 28, 'Z', LIGHT, COOL, cap=False))
    return merge(*parts)


def lander():
    # Parked boat. Sets the scale of the hangar deck.
    sections = [rect(s[0], s[1], s[2], 12, s[3]) for s in ((40, 60, 96, -300), (96, 40, 150, -230), (110, 36, 180, -60), (84, 40, 150, 170), (22, 46, 80, 320))]
    parts = [loft(sections, HULL, PRIMARY, 3, 1, 20)]
    for side in (-1, 1):
        parts.append(box((240, 170, 16), (-120, side * 180, 96), HULL, SECONDARY, 2))
        parts.append(moved(drive_bell(46, 80, 16, 0), mat((-290, side * 62, 112))))
        for x in (-170, 110):
            parts.append(box((22, 22, 44), (x, side * 72, 22), TRIM, METAL))
    return merge(*parts)


def hangar(kit):
    """Built on +Y, then mirrored: the opening cinematic flies into the -Y one.
    The pocket stops at y=3350, outside the playable decks."""
    x0, x1 = MOUTH_X
    xm = (x0 + x1) / 2
    half = SHELL_R * math.sin(STEP)
    outer = SHELL_R * math.cos(STEP)
    back = 3350.0
    run = outer - back
    # Pocket shell.
    kit.sym(box((x1 - x0 + 200, run + 40, 120), (xm, back + run / 2, -half - 60), HULL, SECONDARY, 5), uv=2.6, tone=.3)
    kit.sym(box((x1 - x0 + 200, run + 40, 120), (xm, back + run / 2, half + 60), HULL, SECONDARY, 5), uv=2.6, tone=.3)
    kit.sym(box((120, run + 40, half * 2 + 240), (x0 - 60, back + run / 2, 0), HULL, SECONDARY, 5), uv=2.6, tone=.3)
    kit.sym(box((120, run + 40, half * 2 + 240), (x1 + 60, back + run / 2, 0), HULL, SECONDARY, 5), uv=2.6, tone=.3)
    kit.sym(box((x1 - x0, 40, half * 2), (xm, back - 20, 0), TRIM, DARK), uv=2.6)
    # The light the camera flies into: glowing bulkhead panels behind dark frames.
    for x in np.arange(x0 + 260, x1 - 200, 520):
        kit.sym(box((440, 6, half * 1.6), (x, back + 4, 40), LIGHT, BRIGHT), slot=LIGHT, uv=1)
    for x in np.arange(x0, x1 + 1, 260):
        kit.sym(box((40, 80, half * 2), (x, back + 40, 0), TRIM, SECONDARY, 3), uv=2.2, tone=.4)
    # Portal frames marching out to the mouth.
    for y in np.arange(back + 260, outer - 80, 300):
        kit.sym(box((64, 110, half * 2), (x0 + 34, y, 0), TRIM, SECONDARY, 4), uv=2.2, tone=.5)
        kit.sym(box((64, 110, half * 2), (x1 - 34, y, 0), TRIM, SECONDARY, 4), uv=2.2, tone=.5)
        kit.sym(box((x1 - x0, 90, 80), (xm, y, half - 44), TRIM, SECONDARY, 4), uv=2.2, tone=.5)
        kit.sym(box((x1 - x0 - 140, 24, 12), (xm, y + 60, half - 94), LIGHT, WARM), slot=LIGHT)
    # Deck: bright lane markers converge on the back wall.
    for offset in (-600, -200, 200, 600):
        for y in np.arange(back + 160, outer, 180):
            kit.sym(box((70, 34, 5), (xm + offset, y, -half + 3), LIGHT, AMBER if abs(offset) > 300 else WARM), slot=LIGHT)
    for y in np.arange(back + 100, outer, 600):
        kit.sym(box((x1 - x0 - 100, 22, 8), (xm, y, -half + 4), TRIM, HAZARD), uv=2)
    kit.sym(lander(), mat((x0 + 720, back + 1100, -half), (0, 0, -1.2)), uv=2, tone=.4)
    kit.sym(lander(), mat((x1 - 620, back + 780, -half), (0, 0, -1.9)), uv=2, tone=.6)
    # Armoured lip: stepped jaws framing the opening. Nothing passes y=5560, where the camera sits.
    lip = outer + 150
    for z, h in ((half + 120, 240), (-half - 120, 240)):
        kit.sym(box((x1 - x0 + 700, 300, h), (xm, outer + 10, z), HULL, PRIMARY, 8, 40), uv=2, tone=.42)
    for x in (x0 - 170, x1 + 170):
        kit.sym(box((340, 300, half * 2 + 240), (x, outer + 10, 0), HULL, PRIMARY, 8, 40), uv=2, tone=.42)
    kit.sym(box((x1 - x0 + 120, 40, 44), (xm, lip + 16, half + 34), TRIM, HAZARD, 3), uv=2.4)
    kit.sym(box((x1 - x0 + 120, 40, 44), (xm, lip + 16, -half - 34), TRIM, HAZARD, 3), uv=2.4)
    kit.sym(box((x1 - x0 + 60, 12, 16), (xm, lip + 36, half - 6), LIGHT, BRIGHT), slot=LIGHT)
    kit.sym(box((x1 - x0 + 60, 12, 16), (xm, lip + 36, -half + 6), LIGHT, BRIGHT), slot=LIGHT)
    for x in np.arange(x0, x1 + 1, 240):
        kit.sym(box((60, 26, 70), (x, lip + 12, half + 150), TRIM, SECONDARY, 2), uv=1.6)
    for z in (-half, -half * .33, half * .33, half):
        kit.sym(box((16, 12, 100), (x0 + 6, lip + 24, z), LIGHT, RED), slot=LIGHT)
        kit.sym(box((16, 12, 100), (x1 - 6, lip + 24, z), LIGHT, GREEN), slot=LIGHT)


def arm(kit, x, angle, length, cradles=3):
    """Docking arm: a truss with piers either side and a lit tower at the tip."""
    base = mat((x, 0, 0), (angle - math.pi / 2, 0, 0))
    r0, r1 = SHELL_R + 200, SHELL_R + 200 + length
    parts = []
    parts.append(loft([rect(s * 300, -s * 240, s * 240, 60 * s, 0) @ np.array(((0, 1, 0), (0, 0, 1), (1, 0, 0))) + np.array((0, 0, z)) for z, s in ((r0 - 400, 1.6), (r0 + 500, 1.1), (r1 * .96, .9), (r1, .6))], HULL, PRIMARY, 10, 2, 20))
    for i in range(cradles):
        z = r0 + (r1 - r0) * (i + .7) / (cradles + .3)
        for side in (-1, 1):
            parts.append(box((240, 1500, 170), (side * 0, side * 980, z), TRIM, SECONDARY, 6))
            parts.append(box((1100, 180, 120), (0, side * 1680, z), HULL, PRIMARY, 6))
            parts.append(box((1000, 14, 14), (0, side * 1778, z + 40), LIGHT, AMBER))
            parts.append(box((1000, 14, 14), (0, side * 1778, z - 40), LIGHT, AMBER))
        parts.append(box((900, 900, 90), (0, 0, z), TRIM, METAL, 6))
    parts.append(lathe([(r1, 170), (r1 + 500, 100), (r1 + 540, 150), (r1 + 640, 150), (r1 + 660, 40), (r1 + 1400, 8)], 12, 'Z', TRIM, SECONDARY))
    parts.append(lathe([(r1 + 1400, 22), (r1 + 1440, 22)], 8, 'Z', LIGHT, RED))
    kit.add(merge(*parts), base, tone=float(kit.rng.uniform(.2, .8)))


def habitat(kit, x, spoke_phase):
    """Habitat ring: a pressurised torus with stepped section, armour shingles, and spokes."""
    R = 12000.0
    w, h = 1040.0, 720.0
    section = [(-w, -h * .5), (-w, h * .2), (-w * .8, h * .62), (-w * .44, h * .82), (w * .44, h * .82), (w * .8, h * .62), (w, h * .2), (w, -h * .5), (w * .6, -h), (-w * .6, -h)]
    n = 96
    rows = []
    for i in range(n + 1):
        a = i / n * 2 * math.pi
        rows.append([(x + dx, math.cos(a) * (R + dr), math.sin(a) * (R + dr)) for dx, dr in section])
    kit.add(loft(rows, HULL, SECONDARY, 0, 1, 25, cap=False, recalc=True), tone=.3, mode=12800)
    # Window galleries and armour shingles on the outer face.
    for i in range(n):
        a0, a1 = i / n * 2 * math.pi, (i + 1) / n * 2 * math.pi
        gap = .0024
        if i % 8 == 0:
            kit.add(polar_plate(x - w * .8, x + w * .8, a0, a1 + 2 * math.pi / n * 1, R + h * .82 - 8, 90, SECONDARY, TRIM, .06, 5), tone=.2, mode=12800, uv=.8)
            kit.add(emitter(), mat(polar(R + h * .82 + 60, a0 + .03, x), (a0 + .03 - math.pi / 2, 0, 0)), tone=.2)
        elif i % 8 == 1:
            continue
        else:
            kit.add(polar_plate(x - w * .78, x - w * .22, a0 + gap, a1 - gap, R + h * .82, 34, cut=.06, curve=1), tone=float(kit.rng.uniform(.3, .7)), mode=12800, uv=.8)
            kit.add(polar_plate(x + w * .22, x + w * .78, a0 + gap, a1 - gap, R + h * .82, 34, cut=.06, curve=1), tone=float(kit.rng.uniform(.3, .7)), mode=12800, uv=.8)
            kit.add(polar_plate(x - w * .2, x + w * .2, a0 + gap, a1 - gap, R + h * .82, 16, cut=.04, curve=1), win=1.0, tone=.5, mode=12800, uv=1)
        # Galleries on both faces of the ring; these are what light up at distance.
    for side in (-1, 1):
        rows = []
        for r in (R - h * .4, R + h * .2):
            rows.append(ring(r, x + side * (w + 8), n))
        kit.add(loft(rows, HULL, PRIMARY, cap=False, flip=side > 0), win=1.0, tone=.5, mode=12800)
    for i in range(6):
        a = spoke_phase + i * math.pi / 3
        kit.add(merge(*[beam(polar(SHELL_R - 60, a, x + dx), polar(R - h * .9, a, x + dx), 260, 150, HULL, PRIMARY, 8, (1, 0, 0), 50) for dx in (-420, 420)]), tone=.4, uv=.7)
        for r in np.arange(6400, 11000, 1300):
            kit.add(box((840, 180, 180), polar(r, a, x), TRIM, SECONDARY, 5), tone=.3, uv=.7)
        kit.add(beam(polar(SHELL_R + 120, a, x - 420), polar(R - h, a, x + 420), 60, 60, TRIM, METAL), tone=.3)
        kit.add(beam(polar(SHELL_R + 120, a, x + 420), polar(R - h, a, x - 420), 60, 60, TRIM, METAL), tone=.3)


def spine(kit):
    """Dorsal and ventral citadels run the whole length, carrying the main batteries."""
    rows = [(-5900, 700, 3200, 4300), (-4700, 1100, 4700, 6100), (-2500, 1200, 5120, 6700), (-1700, 1250, 5120, 6950), (2800, 1250, 5120, 7000), (3400, 1120, 5120, 6840),
            (9200, 1120, 5120, 6840), (9800, 1000, 5120, 6680), (18300, 1000, 5120, 6680), (20000, 900, 5120, 6500), (24600, 640, 2500, 3900), (31500, 180, 300, 1250), (32000, 60, 160, 520)]
    def section(x, hw, z0, z1):
        return [(x, -hw * 1.2, z0), (x, hw * 1.2, z0), (x, hw, z0 + (z1 - z0) * .5), (x, hw * .72, z1), (x, -hw * .72, z1), (x, -hw, z0 + (z1 - z0) * .5)]
    part = loft([section(*r) for r in rows], HULL, PRIMARY, 12, 2, 20)
    kit.add(part, tone=.45)
    kit.add(part, mat((0, 0, 0), (math.pi, 0, 0)), tone=.45)
    rng = kit.rng
    for sign in (1, -1):
        rotate = mat((0, 0, 0), (0 if sign > 0 else math.pi, 0, 0))
        # Tiers of armour down the citadel's roof.
        x = -4400.0
        while x < 22000:
            run = float(rng.choice((900, 1200, 1500)))
            z = np.interp(x + run / 2, [r[0] for r in rows], [r[3] for r in rows])
            hw = np.interp(x + run / 2, [r[0] for r in rows], [r[1] for r in rows]) * .66
            kit.add(box((run - 70, hw * 1.9, 110), (x + run / 2, 0, z + 44), HULL, PRIMARY if rng.random() < .6 else SECONDARY, 8, 24), rotate)
            x += run
        for x, bigger in ((-1300, 1), (1700, 1), (4600, 0), (7400, 0), (11000, 0), (13800, 0), (16600, 0), (21300, 1)):
            z = np.interp(x, [r[0] for r in rows], [r[3] for r in rows]) + 96
            r = 460 if bigger else 340
            kit.add(lathe([(z - 80, r * 1.3), (z + 30, r * 1.3), (z + 40, r * 1.2)], 32, 'Z', TRIM, SECONDARY, 4), mat((x, 0, 0)) @ rotate if False else rotate @ mat((x, 0, 0)))
            kit.add(turret(r, 3, r * 3.7, 24), rotate @ mat((x, 0, z + 30), (0, 0, 0 if x > 8000 else math.pi)), tone=.4)
        for x in (3000, 9500, 18300):
            z = np.interp(x, [r[0] for r in rows], [r[3] for r in rows]) + 60
            kit.add(mast(2300, 62, 5), rotate @ mat((x, 0, z)), tone=.2)
            kit.add(dish(460, 32), rotate @ mat((x + 620, 0, z + 130), (0, .5, 0)), tone=.2)
    # Citadel flanks carry window galleries and casemates.
    for sign in (1, -1):
        for x in np.arange(3700, 18600, 900):
            for side in (-1, 1):
                kit.add(box((780, 12, 330), (x + 360, side * (1090), sign * 5920), HULL, PRIMARY, 2), win=1.0, tone=.5, uv=1)


def station(size):
    """Meridian Station exterior. Long axis X; decks run inside the open shell."""
    kit = Kit('SM_Station_Hull', HUMAN_SLOTS, 21)
    rng = kit.rng
    kit.add(shell_part(), tone=.5, mode=5200, uv=.8)
    # Belts: armour shingles in rings around the shell, leaving the spine sectors to the citadels.
    bays = []
    rows = np.arange(-1900, 19000, 1450)
    for i, x in enumerate(rows):
        for j in range(SHELL_N // 2):
            a0 = j * STEP * 2 - math.pi / 2 + .004
            a1 = a0 + STEP * 2 - .008
            c = (a0 + a1) / 2
            if abs(math.cos(c)) < .22 or in_mouth(x, x + 1380, a0, a1):
                continue
            pick = (i * 7 + j * 5) % 6
            if pick == 0 and x > 1800:
                kit.add(polar_plate(x, x + 1380, a0, a1, SHELL_R, 26, SECONDARY, TRIM, .04, 3), mode=5200, uv=.8)
                bays.append((x + 690, c))
            elif pick in (1, 3):
                kit.add(polar_plate(x, x + 1380, a0, a1, SHELL_R, 40, cut=.08), mode=5200, uv=.9)
                kit.add(polar_plate(x + 180, x + 1200, a0 + .03, a1 - .03, SHELL_R + 40, 34, SECONDARY if pick == 3 else PRIMARY, cut=.1, bevel=2.5), mode=5200, uv=.9)
            elif pick == 2:
                kit.add(polar_plate(x, x + 1380, a0, a1, SHELL_R, 30, cut=.06), win=1.0, mode=5200, uv=1)
            else:
                kit.add(polar_plate(x, x + 660, a0, a1, SHELL_R, 44, cut=.07), mode=5200, uv=.9)
                kit.add(polar_plate(x + 720, x + 1380, a0, a1, SHELL_R, 58, SECONDARY, cut=.07), mode=5200, uv=.9)
    for x, a in bays:
        kit.add(bay(), mat(polar(SHELL_R + 40, a, x), (a - math.pi / 2, 0, 0)), tone=.5, uv=1)
    for x in np.arange(2500, 19000, 2900):
        kit.add(lathe([(x - 90, 5180), (x - 90, 5330), (x - 50, 5400), (x + 50, 5400), (x + 90, 5330), (x + 90, 5180)], SHELL_N, 'X', TRIM, SECONDARY, cap=False, phase=-math.pi / 2), tone=.3, mode=5200)
    # Bulkhead flanges, hollow so nothing crosses the decks.
    for x0, x1, r in ((-2500, -1750, 7200), (19100, 19850, 7600)):
        kit.add(lathe([(x0, 5150), (x0, r - 140), (x0 + 150, r), (x1 - 150, r), (x1, r - 140), (x1, 5150)], SHELL_N, 'X', HULL, PRIMARY, cap=False, phase=-math.pi / 2), tone=.4, mode=7000)
        for i in range(24):
            a = i / 24 * 2 * math.pi + .02
            kit.add(polar_plate(x0 + 40, x1 - 40, a, a + .22, r, 70, SECONDARY if i % 3 == 0 else PRIMARY, cut=.1, bevel=5), tone=.4, mode=7000, win=0)
            if i % 3 == 1:
                kit.add(emitter(), mat(polar(r + 50, a + .11, (x0 + x1) / 2), (a + .11 - math.pi / 2, 0, 0)), tone=.3)
    hangar(kit)
    # Fore and aft funnels are open shells too: they begin outside the deck range and close further out.
    kit.add(lathe([(19850, 5200), (20200, 5150), (22200, 4000), (24600, 2500)], SHELL_N, 'X', HULL, PRIMARY, cap=False, phase=-math.pi / 2), tone=.4, mode=4200)
    kit.add(lathe([(-5200, 2800), (-4000, 4200), (-2500, 5200)], SHELL_N, 'X', HULL, PRIMARY, cap=False, phase=-math.pi / 2), tone=.4, mode=4200)
    # Forward lance: the fortress's one enormous gun.
    kit.add(lathe([(24600, 2500), (24900, 2300), (25000, 1500), (29500, 980), (29800, 1180), (30100, 1180), (30300, 760), (34300, 480), (34500, 640), (34900, 640), (35100, 340), (37000, 190), (37100, 300), (37450, 300), (37450, 120), (36900, 80)], SHELL_N, 'X', HULL, SECONDARY, cap=False), tone=.3, mode=1500)
    for i in range(6):
        a = i * math.pi / 3 + math.pi / 6
        kit.add(beam(polar(1420, a, 25100), polar(620, a, 34200), 150, 90, HULL, PRIMARY, 6, (1, 0, 0)), tone=.3)
        kit.add(moved(box((1800, 90, 60), (27500, 0, 0), TRIM, METAL), mat((0, 0, 0), (a, 0, 0)) @ mat((0, 0, 1320))), tone=.3)
        for x in (26000, 28000, 32000):
            kit.add(box((60, 420, 220), polar(np.interp(x, [25000, 29500, 30300, 34300], [1520, 1000, 780, 500]), a, x), TRIM, SECONDARY, 4), tone=.3)
    for x in np.arange(25400, 37000, 1200):
        r = np.interp(x, [25000, 29500, 30300, 34300, 35100, 37000], [1500, 980, 760, 480, 340, 190])
        kit.add(lathe([(x, r - 8), (x, r + 30), (x + 50, r + 30), (x + 50, r - 8)], 32, 'X', LIGHT, COOL, cap=False), slot=LIGHT)
    # Aft reactor block and drive cluster.
    kit.add(lathe([(-7000, 1900), (-6900, 2300), (-6650, 2300), (-6500, 3100), (-5400, 3100), (-5200, 2700)], SHELL_N, 'X', TRIM, SECONDARY, cap=False, phase=-math.pi / 2), tone=.3, mode=2800)
    kit.add(lathe([(-7010, 1920), (-7010, 1), ], 32, 'X', TRIM, DARK, cap=False, flip=True), tone=.3)
    for i in range(6):
        a = i * math.pi / 3
        kit.add(drive_bell(560, 800, 48, 18), mat(polar(1300, a, -6800)), tone=.3, uv=.8)
        kit.add(lathe([(-6980, 620), (-6810, 620)], 32, 'X', TRIM, METAL, cap=False), mat(polar(1300, a, 0)), tone=.3)
    spine(kit)
    habitat(kit, 6500, .22)
    habitat(kit, 13300, .22 + math.pi / 6)
    for x, a, n in ((17200, math.radians(40), 3), (17200, math.radians(140), 3), (17200, math.radians(220), 2), (17200, math.radians(320), 2),
                    (-3400, math.radians(30), 2), (-3400, math.radians(150), 2), (-3400, math.radians(210), 2), (-3400, math.radians(330), 2)):
        arm(kit, x, a, 7800 if n == 3 else 5400, n)
    for a in np.radians((20, 65, 115, 160, 200, 245, 295, 340)):
        kit.add(emitter(), mat(polar(3000, a, 23800), (a - math.pi / 2, .4, 0), 2.2), tone=.3)
    return kit


def station_cfg():
    def mark(P, N, D, colour, zone):
        for side in (-1, 1):
            stamp(P, N, colour, zone, TEXT['MERIDIAN'], 300, (300, 1440), side, (.34, .33, .3))
        band = (np.abs(P[..., 0] - 9800) < 170) & (zone == PRIMARY)
        colour[band] = ZONE_COLOURS[ACCENT]
    return {'seed': 32, 'tile_cm': 5600, 'height_scale': 3.2, 'length': 44000, 'ao': 1500, 'hazard_pitch': 180, 'soot_x': -3000,
            'window_pitch': (70, 150), 'window_size': (40, 56), 'mark': mark, 'side_only': False, 'row_skip': 2}


def check_station(obj):
    """Fail the build if anything sits inside the deck volume."""
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    span = (co[:, 0] > -700) & (co[:, 0] < DECK_END)
    bad = span & (np.abs(co[:, 1]) < 3000) & (np.abs(co[:, 2]) < 3000)
    near = span & (np.hypot(co[:, 1], co[:, 2]) < 4400) & ~(np.abs(co[:, 1]) > 3300) & ~(np.abs(co[:, 2]) < 1000)
    camera = (np.abs(co[:, 0] - 300) < 500) & (np.abs(co[:, 2]) < 350) & (np.abs(co[:, 1]) > 5560)
    print(f'[check] deck volume verts={int(bad.sum())} inner cylinder verts={int(near.sum())} camera-path verts={int(camera.sum())}')
    assert not bad.any() and not near.any() and not camera.any()


# ------------------------------------------------------------------ driver

BUILDERS = {'cruiser': cruiser, 'frigate': frigate, 'vigil': vigil, 'shard': shard, 'station': station}
HUMAN_CFG = {'cruiser': cruiser_textures_cfg, 'frigate': frigate_cfg, 'station': station_cfg}
FIRST_CFG = {'vigil': {'seed': 41, 'length': 7000, 'cores': [(-1000, 0, 10)]}, 'shard': {'seed': 42, 'length': 2800, 'cores': [(-340, -130, -14)]}}
FINAL_SIZE = {'cruiser': 4096, 'station': 4096, 'frigate': 2048, 'vigil': 2048, 'shard': 2048}


def views_for(asset, length):
    if asset == 'station':
        return [{'dir': (.2, -1, .28), 'dist': 118000, 'lens': 60}, {'dir': (-.8, -.55, .4), 'dist': 76000, 'lens': 45, 'at': (12000, 0, 0)},
                {'dir': (.9, .7, .35), 'dist': 76000, 'lens': 45, 'at': (12000, 0, 0)}, {'dir': (.06, -1, .1), 'dist': 21000, 'lens': 30, 'at': (900, 0, 0)},
                {'dir': (0, -1, 0), 'dist': 5950, 'lens': 18, 'at': (300, 300, 0)}, {'dir': (.6, -1, .35), 'dist': 15000, 'lens': 45, 'at': (10000, -4000, 2000)}]
    near = length * 1.05
    return [{'dir': (1, -.85, .42), 'dist': near * 1.9, 'lens': 80}, {'dir': (-1, -.6, .3), 'dist': near * 1.9, 'lens': 80},
            {'dir': (.12, -1, .08), 'dist': near * 2.0, 'lens': 80}, {'dir': (.02, -.1, 1), 'dist': near * 2.0, 'lens': 80},
            {'dir': (1, -1, .5), 'dist': near * .85, 'lens': 80, 'at': (length * .12, 0, length * .05)},
            {'dir': (-1, -.9, .25), 'dist': near * .55, 'lens': 80, 'at': (-length * .4, 0, 0)}]


def run(asset, size, clay, write_mesh):
    started = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    kit = BUILDERS[asset](size)
    obj = kit.build(14 if asset in FIRST_CFG else 50)
    report(obj)
    if asset == 'station':
        check_station(obj)
    cm_per_texel = unwrap(obj, kit, size, 6000.0 if asset == 'station' else 2600.0)
    name = kit.name.replace('SM_Ship_', '').replace('SM_Station_', 'Station').replace('SM_', '')
    if not clay:
        if asset in FIRST_CFG:
            first_textures(obj, name, size, cm_per_texel, dict(FIRST_CFG[asset], spp=48))
        else:
            human_textures(obj, name, size, cm_per_texel, dict(HUMAN_CFG[asset](), spp=48))
    if write_mesh:
        export(obj)
    preview_material(obj, name, clay=clay)
    frames = render_views(obj, views_for(asset, obj.dimensions.x), asset, samples=24 if clay else 48)
    contact(frames, 3, REVIEW / f'ships_{asset}.png')
    print(f'[done] {asset} in {time.time() - started:.0f}s')


def sheet():
    """Stack the per-asset review sheets into Art/Review/ships.png."""
    rows = []
    for asset in BUILDERS:
        path = REVIEW / f'ships_{asset}.png'
        if path.exists():
            image = bpy.data.images.load(str(path))
            w, h = image.size
            data = np.empty(w * h * 4, np.float32)
            image.pixels.foreach_get(data)
            rows.append(data.reshape(h, w, 4)[..., :3][::2, ::2].copy())
            bpy.data.images.remove(image)
    png(REVIEW / 'ships.png', np.vstack(rows[::-1]))


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    assets = [a for a in args if a in BUILDERS]
    if '--sheet' in args and not assets:
        sheet()
        return
    assets = assets or list(BUILDERS)
    size = int(args[args.index('--size') + 1]) if '--size' in args else 0
    clay = '--clay' in args
    write_mesh = '--no-export' not in args
    for text in ('FNS-2312', 'FNS-0417', 'MERIDIAN'):
        TEXT[text] = text_mask(text, 96)
    for folder in (MESHES, TEXTURES, REVIEW):
        folder.mkdir(parents=True, exist_ok=True)
    if not clay:
        detail_set()
        crystal_detail()
    for asset in assets:
        run(asset, size or FINAL_SIZE[asset], clay, write_mesh)
    sheet()
    print('PHYSIS_SHIPS_DONE')


if __name__ == '__main__':
    main()
