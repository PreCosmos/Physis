"""Port Halcyon's buildings, the Bastion, the pieces of the past (traces) and the props (level 6;
Tools/halcyon/README.md is the contract).

The town is limestone and lime render under slate: terraced houses two and three storeys high, painted doors and
shutters, sash windows, chimneys, quoins and string courses, weathered darker toward the ground and stained with wrack
where the sea came in. The Just built in poured concrete painted olive, with amber lights. What only the past holds
(the Harbour Bridge, catwalks, stair flights, the library's shelves) is modelled as it stood; in play it wears the
trace material (physis_halcyon_tools: MI_HA_Trace) and shows only while Physis reads.
"""
from kit import *  # noqa: F401,F403


def _rng(seed):
    return np.random.default_rng(seed)


def weather(p, start, seed, amount=.22, height=1.6):
    grime(p, start, amount, 1.4, seed)
    ao(p, start, height, .62)


def tri(p, a, b, c, colour, slot):
    p.add(np.array([a, b, c], np.float64), [[0, 1, 2]], colour, slot, False)


def facade_windows(p, rng, x, y_positions, z_rows, w, h, frame, shutter=None, glass=GLASS_SEA, sign=1.0, axis='x', broken=False):
    """Sash windows on a wall face: in the plane x = const facing +x (sign 1) or -x (sign -1) for axis 'x', or the
    plane y = const facing +y / -y for axis 'y'. Each has a dark glass pane, a painted frame, and shutters if given."""
    yaw = (0.0 if sign > 0 else 180.0) if axis == 'x' else (90.0 if sign > 0 else -90.0)
    for z in z_rows:
        for u in y_positions:
            c = (x + .03 * sign, u, z) if axis == 'x' else (u, x + .03 * sign, z)
            g = None if (broken and rng.uniform() < .5) else glass
            window_frame(p, c, w, h, .14, frame, ENAMEL, g, CRYSTAL if g is not None else None, yaw, 1, .05)
            if g is None:   # a broken window shows the dark room behind
                a = np.array(c)
                d = np.array((-.12 * sign, 0, 0)) if axis == 'x' else np.array((0, -.12 * sign, 0))
                if axis == 'x':
                    q = [a + d + (0, -w / 2, -h / 2), a + d + (0, w / 2, -h / 2), a + d + (0, w / 2, h / 2), a + d + (0, -w / 2, h / 2)]
                else:
                    q = [a + d + (-w / 2, 0, -h / 2), a + d + (w / 2, 0, -h / 2), a + d + (w / 2, 0, h / 2), a + d + (-w / 2, 0, h / 2)]
                if sign < 0:
                    q = q[::-1]
                if axis == 'y':
                    q = q[::-1]
                p.add(np.array(q), [[0, 1, 2, 3]], SOOT, STONE, False)
            if shutter is not None:
                for s in (-1, 1):
                    off = s * (w / 2 + .28)
                    cc = (x + .06 * sign, u + off, z) if axis == 'x' else (u + off, x + .06 * sign, z)
                    half = (.03, .24, h / 2 + .04) if axis == 'x' else (.24, .03, h / 2 + .04)
                    if rng.uniform() < .85:
                        bevel_box(p, cc, half, vary(rng, shutter, .2), ENAMEL, .01)


# ---------------------------------------------------------------- the town's houses

# hx, hy: half depth (x, front to back) and half width (y, along the street); floors; storey height; kind
HOUSE_KINDS = {
    0: dict(hx=4.0, hy=3.5, floors=2, storey=3.1, kind='terrace', seed=11),
    1: dict(hx=3.2, hy=3.0, floors=3, storey=2.9, kind='narrow', seed=12),
    2: dict(hx=4.0, hy=3.5, floors=2, storey=3.1, kind='ruin', seed=13),
    3: dict(hx=4.5, hy=4.0, floors=2, storey=3.3, kind='shop', seed=14),
}
DOOR_COLOURS = (PAINT_GREEN, PAINT_BLUE, PAINT_RED, PAINT_OLIVE, SLATE_PALE)


def house(k):
    """A house of the town, front (+x) to the street: render over limestone, a plinth and quoins, a string course at
    each floor, sash windows with shutters, a panelled door up one step, a slate roof with its ridge along the street
    and a chimney on one gable. Variant 0 a two-storey terrace house (8 x 7 m), 1 a narrow three-storey one, 2 a
    ruin (the roof gone, the walls broken off, soot and beams), 3 a shop house with a shopfront and an awning."""
    h = HOUSE_KINDS[k]
    hx, hy, floors, storey, kind = h['hx'], h['hy'], h['floors'], h['storey'], h['kind']
    rng = _rng(h['seed'])
    slots = ((STONE, ENAMEL, CRYSTAL, WOOD, LICHEN) if kind == 'ruin' else (STONE, TILE, ENAMEL, CRYSTAL, LICHEN)) + ((CLOTH,) if kind == 'shop' else ())
    p = Part('SM_HN_House%d' % k, slots)
    top = floors * storey + .5
    render = vary(rng, RENDER, .06)
    s = len(p.v)
    # The body: a plinth of limestone, the rendered walls above.
    bevel_box(p, (0, 0, .35), (hx + .05, hy + .05, .35), LIME_SHADE, STONE, .04)
    if kind == 'ruin':
        # Walls broken off at uneven heights: built from tall blocks of varying height along each face.
        for axis, length, fixed in (('x', hy, hx), ('x', hy, -hx), ('y', hx, hy), ('y', hx, -hy)):
            n = 7
            for j in range(n):
                u0, u1 = -length + 2 * length * j / n, -length + 2 * length * (j + 1) / n
                zt = top * rng.uniform(.35, .95) if 0 < j < n - 1 else top * rng.uniform(.75, 1.0)
                cu, hu = (u0 + u1) / 2, (u1 - u0) / 2
                c = (fixed - np.sign(fixed) * .25, cu, .7 + (zt - .7) / 2) if axis == 'x' else (cu, fixed - np.sign(fixed) * .25, .7 + (zt - .7) / 2)
                half = (.25, hu, (zt - .7) / 2) if axis == 'x' else (hu, .25, (zt - .7) / 2)
                bevel_box(p, c, half, mix(render, SOOT, rng.uniform(.0, .45)), STONE, .03)
        for j in range(4):   # fallen floor beams
            y = rng.uniform(-hy + .8, hy - .8)
            z = storey + rng.uniform(-.4, .3)
            tube(p, [(-hx + .3, y, z + rng.uniform(-.8, 0)), (hx - .6, y + rng.uniform(-.5, .5), z)], .12, vary(rng, TIMBER, .2), WOOD, 6, True, False)
        bevel_box(p, (0, 0, .72), (hx - .5, hy - .5, .02), SOOT, STONE, .01)
    else:
        bevel_box(p, (0, 0, .7 + (top - .7) / 2), (hx, hy, (top - .7) / 2), render, STONE, .05)
    # String courses and quoins.
    for f in range(1, floors + (0 if kind == 'ruin' else 1)):
        z = f * storey + .5
        if kind != 'ruin' or f == 1:
            bevel_box(p, (0, 0, z), (hx + .06, hy + .06, .09), LIME, STONE, .02)
    for sx in (-1, 1):
        for sy in (-1, 1):
            z = .7
            while z < (top if kind != 'ruin' else top * .6) - .3:
                big = (int(z / .35) % 2) == 0
                bevel_box(p, (sx * (hx - (.25 if big else .18)), sy * (hy + .02), z + .17), (.25 if big else .18, .05, .16), LIME, STONE, .02)
                bevel_box(p, (sx * (hx + .02), sy * (hy - (.18 if big else .25)), z + .17), (.05, .18 if big else .25, .16), LIME, STONE, .02)
                z += .35
    # Windows: two per floor on the front (one on the narrow house), fewer behind; the shop's ground floor is a shopfront.
    cols = (-hy * .45, hy * .45) if hy > 3.2 else (0.0,)
    rows = [storey * f + .5 + storey * .52 for f in range(floors)]
    door_y = -hy * .45 if len(cols) > 1 else hy * .5
    shutter = DOOR_COLOURS[int(rng.integers(0, len(DOOR_COLOURS)))]
    broken = kind == 'ruin'
    if kind == 'shop':
        facade_windows(p, rng, hx, cols, rows[1:], 1.0, 1.5, PAINT_WHITE, shutter, sign=1.0)
        bevel_box(p, (hx + .06, .6, 1.9), (.06, hy * .55, 1.1), shutter, ENAMEL, .02)        # the shopfront's frame
        p.add(np.array([(hx + .1, -hy * .45, .95), (hx + .1, hy * .45 + 1.2, .95), (hx + .1, hy * .45 + 1.2, 2.75), (hx + .1, -hy * .45, 2.75)]),
              [[0, 1, 2, 3]], GLASS_SEA, CRYSTAL, False)
        # The awning: canvas on a light frame, sloping out over the pavement.
        a, b = hx + .1, hx + 1.6
        p.add(np.array([(a, -hy + .3, 3.25), (b, -hy + .3, 2.75), (b, hy - .3, 2.75), (a, hy - .3, 3.25)]), [[0, 1, 2, 3], [3, 2, 1, 0]], vary(rng, CANVAS_W, .1),
              CLOTH, False)
        door_y = -hy + .9
    else:
        facade_windows(p, rng, hx, [c for c in cols if abs(c - door_y) > .8], rows[:1], 1.0, 1.5, PAINT_WHITE, shutter, sign=1.0,
                       broken=broken)
        facade_windows(p, rng, hx, cols, rows[1:], 1.0, 1.5, PAINT_WHITE, shutter, sign=1.0, broken=broken)
    facade_windows(p, rng, -hx, cols[:1] if kind == 'narrow' else cols, rows[1:] if kind != 'ruin' else rows[:1], .9, 1.3, PAINT_WHITE, None,
                   sign=-1.0, broken=broken)
    # The door: up one step, in a limestone surround.
    bevel_box(p, (hx + .25, door_y, .12), (.3, .75, .12), LIME_WORN, STONE, .02)
    bevel_box(p, (hx + .04, door_y, 1.75), (.06, .62, 1.05), LIME, STONE, .02)
    bevel_box(p, (hx + .08, door_y, 1.7), (.04, .48, .98), vary(rng, shutter, .15), ENAMEL, .015)
    for z in (1.15, 2.1):
        bevel_box(p, (hx + .12, door_y, z), (.02, .34, .3), tone(shutter, .8), ENAMEL, .01)
    if kind != 'ruin':
        # The roof: slate, its ridge along the street (y), with the gable ends filled in render.
        rise = hx * .8
        gable_roof(p, (0, 0, top), 2 * hy, 2 * hx, rise, vary(rng, SLATE, .15), TILE, .35, .16, 90.0, LIME_SHADE, STONE)
        for sy in (-1, 1):
            y = sy * hy
            pts = [(-hx, y, top), (hx, y, top), (0, y, top + rise)]
            tri(p, *(pts if sy > 0 else pts[::-1]), render, STONE)
        # A chimney on one gable, with pots.
        cy = (hy - .45) * (1 if rng.uniform() < .5 else -1)
        bevel_box(p, (-.4, cy, top + rise * .5 + .8), (.55, .4, rise * .5 + 1.0), mix(render, SOOT, .2), STONE, .03)
        for j in (-1, 1):
            cylinder(p, (-.4 + j * .22, cy, top + rise + 1.8), .13, .5, (.30, .14, .08), STONE, 10)
        # Moss along the roof's edges.
        for sx in (-1, 1):
            bevel_box(p, (sx * (hx + .25), 0, top + .02), (.18, hy + .3, .04), vary(rng, WEED_GREEN, .2), LICHEN, .01)
    else:
        bevel_box(p, (hx * .3, hy * .2, .78), (1.2, .9, .08), WRACK, LICHEN, .02)
    weather(p, s, h['seed'], .26)
    # The wrack line where the sea came in: a dark band 0.4 to 1.4 m up.
    v = np.asarray(p.v[s:], np.float64)
    band = np.exp(-((v[:, 2] - .9) / .45) ** 2) * .45
    c = np.asarray(p.c[s:], np.float64)
    c[:, :3] = c[:, :3] * (1 - band[:, None]) + np.array(WRACK[:3]) * band[:, None]
    p.c[s:] = c.tolist()
    finish(p)
    return p


# ---------------------------------------------------------------- waterfront

def quay():
    """A quay panel of the sea wall, 12 m along y, its face to the sea (+x): coursed limestone blocks 10 m high from
    the sea bed, a granite coping 2.4 m deep that is the quay's edge, iron rings, weed and wrack below the tide line
    (about 7 m up: placed on the bed at -7)."""
    rng = _rng(21)
    p = Part('SM_HN_Quay', (STONE, ALLOY, LICHEN))
    s = len(p.v)
    z = 0.0
    while z < 9.6:
        hgt = rng.uniform(.5, .7)
        y = -6.0
        off = rng.uniform(0, .6)
        while y < 6.0 - .01:
            w = min(rng.uniform(.9, 1.6), 6.0 - y) if y > -6.0 else min(off + .6, 1.2)
            bevel_box(p, (.0 + rng.uniform(-.03, .03), y + w / 2, z + hgt / 2), (1.15, w / 2 - .01, hgt / 2 - .01), vary(rng, LIME_SHADE, .18), STONE, .04)
            y += w
        z += hgt
    bevel_box(p, (0, 0, 9.85), (1.25, 6.0, .25), LIME_WORN, STONE, .04)
    for y in (-3.0, 3.0):
        torus(p, (1.22, y, 8.2), .22, .035, STEEL_W, ALLOY, 16, 6, 'x')
    weather(p, s, 21, .2, 3.0)
    v = np.asarray(p.v[s:], np.float64)
    c = np.asarray(p.c[s:], np.float64)
    wet = np.clip((7.6 - v[:, 2]) / 1.2, 0, 1)[:, None]
    c[:, :3] = c[:, :3] * (1 - wet * .65) + np.array(WRACK[:3]) * wet * .65
    p.c[s:] = c.tolist()
    for k in range(40):   # weed on the face below the tide line
        y, z = rng.uniform(-5.8, 5.8), rng.uniform(5.0, 7.4)
        blob(p, (1.18, y, z), rng.uniform(.12, .3), vary(rng, WRACK, .3), LICHEN, 1, .4, k, (.4, 1.0, .7))
    finish(p)
    return p


def mole_slab():
    """A length of the Mole, the breakwater out to the Bastion: 12 m along x, 9 m wide, 4.4 m high, its top a road of
    setts between low parapets (deck at 4.0), big rubble blocks along its sides. Placed with its base at -1.4 so the
    deck stands at plan.MOLE_TOP."""
    rng = _rng(22)
    p = Part('SM_HN_MoleSlab', (STONE, ROCK, LICHEN))
    s = len(p.v)
    bevel_box(p, (0, 0, 1.9), (6.0, 4.5, 1.9), LIME_SHADE, STONE, .05)
    bevel_box(p, (0, 0, 3.9), (6.0, 4.0, .1), LIME_WORN, STONE, .02)
    for sy in (-1, 1):
        bevel_box(p, (0, sy * 4.25, 4.25), (6.0, .25, .45), LIME, STONE, .04)
        for k in range(9):
            x = -5.5 + k * 1.4 + rng.uniform(-.3, .3)
            blob(p, (x, sy * rng.uniform(4.6, 5.4), rng.uniform(.2, 1.0)), rng.uniform(.6, 1.0), vary(rng, ROCK_GREY, .2), ROCK, 1, .25, k + 5,
                 (1.2, 1.0, .8))
    weather(p, s, 22, .18, 2.0)
    for k in range(18):
        sy = 1 if k % 2 else -1
        blob(p, (rng.uniform(-5.6, 5.6), sy * 4.52, rng.uniform(.6, 1.6)), rng.uniform(.15, .35), vary(rng, WRACK, .3), LICHEN, 1, .4, k, (1, .4, .6))
    finish(p)
    return p


def boat(k=0):
    """A wrecked fishing boat, 9 m long: a clinker timber hull, a small wheelhouse aft, flaking paint, weed."""
    rng = _rng(31)
    p = Part('SM_HN_Boat', (WOOD, ENAMEL, CRYSTAL, LICHEN))
    s = len(p.v)
    paint = PAINT_BLUE
    stations = np.linspace(-4.5, 4.5, 13)
    rings = []
    for x in stations:
        t = x / 4.5
        half = 1.6 * (1 - abs(t) ** 2.2 * (.9 if t > 0 else .4))
        depth = 1.6 * (1 - .3 * abs(t))
        ang = np.linspace(-math.pi / 2, math.pi / 2, 9)
        rings.append([(x, math.sin(a) * half, 2.0 - depth * math.cos(a) ** .8) for a in ang])
    n = len(rings[0])
    verts = np.array([pt for ring in rings for pt in ring])
    faces = [[i * n + j + 1, i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1] for i in range(len(rings) - 1) for j in range(n - 1)]
    colours = np.array([paint if v[2] > 1.35 else TIMBER_GREY for v in verts])
    p.add(verts, faces, colours, WOOD, True)
    p.add(verts, [f[::-1] for f in faces], tone(TIMBER, .6), WOOD, True)    # the inside
    bevel_box(p, (-2.5, 0, 2.6), (1.0, .9, .9), PAINT_WHITE, ENAMEL, .03)
    window_frame(p, (-1.48, 0, 2.9), .9, .5, .08, PAINT_WHITE, ENAMEL, GLASS_SEA, CRYSTAL)
    bevel_box(p, (-2.5, 0, 3.55), (1.1, 1.0, .06), PAINT_BLUE, ENAMEL, .02)
    weather(p, s, 31, .3, 1.5)
    for j in range(16):
        blob(p, (rng.uniform(-4, 4), rng.uniform(-1.3, 1.3), rng.uniform(.4, .9)), rng.uniform(.12, .3), vary(rng, WRACK, .3), LICHEN, 1, .4, j, (1, 1, .5))
    finish(p)
    return p


# ---------------------------------------------------------------- landmarks

def clocktower():
    """The Clocktower on Clock Lane: a limestone tower 6 m square and 21 m to its parapet, a slate spire to 27 m, a
    door on +x, a white dial on each face at 16 m with brass hands stopped at fourteen minutes past seven (the moment
    of the strike), louvred belfry openings above."""
    rng = _rng(41)
    p = Part('SM_HN_Clocktower', (STONE, TILE, ENAMEL, ELECTRUM, WOOD, LICHEN))
    s = len(p.v)
    bevel_box(p, (0, 0, .6), (3.3, 3.3, .6), LIME_SHADE, STONE, .05)
    bevel_box(p, (0, 0, 10.8), (3.0, 3.0, 9.6), vary(rng, LIME, .05), STONE, .05)
    for z in (7.0, 13.0, 19.5):
        bevel_box(p, (0, 0, z), (3.12, 3.12, .14), LIME_WORN, STONE, .03)
    bevel_box(p, (0, 0, 20.9), (3.25, 3.25, .5), LIME, STONE, .04)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(p, (sx * 2.85, sy * 2.85, 21.7), (.32, .32, .55), LIME, STONE, .03)
    spire = [(3.0, 21.4), (2.4, 22.6), (.25, 27.0), (.0, 27.2)]
    lathe(p, spire, SLATE, TILE, 4, (0, 0, 0), False, start=math.pi / 4)
    # The door and a window above it.
    bevel_box(p, (3.02, 0, 1.9), (.08, .9, 1.3), LIME, STONE, .02)
    bevel_box(p, (3.06, 0, 1.8), (.05, .7, 1.2), PAINT_GREEN, ENAMEL, .015)
    window_frame(p, (3.05, 0, 10.0), .8, 1.8, .14, PAINT_WHITE, ENAMEL)
    for yaw in (0.0, 90.0, 180.0, 270.0):
        a = math.radians(yaw)
        f = np.array((math.cos(a), math.sin(a), 0.0))
        r = np.array((-math.sin(a), math.cos(a), 0.0))
        c = f * 3.06 + np.array((0, 0, 16.0))
        # The dial: a white disc with twelve marks; the hands at 7:14.
        ang = np.linspace(0, math.tau, 32, endpoint=False)
        ring = [c + r * math.cos(t) * 1.5 + np.array((0, 0, 1)) * math.sin(t) * 1.5 for t in ang]
        p.add(np.array([c] + ring), [[0, 1 + (j + 1) % 32, 1 + j] for j in range(32)], PAINT_WHITE, ENAMEL, False)
        for m in range(12):
            t = m * math.tau / 12
            d = r * math.sin(t) + np.array((0, 0, 1)) * math.cos(t)
            box(p, c + f * .03 + d * 1.3, np.abs(f) * .02 + np.abs(r) * .05 + np.array((0, 0, .05)), SOOT, STONE)
        for length, angle, width in ((.8, 7 * 30 + 14 * .5, .07), (1.25, 14 * 6, .05)):
            t = math.radians(angle)
            d = r * math.sin(t) + np.array((0, 0, 1)) * math.cos(t)
            q = [c + f * .06 - d * .15 + np.cross(f, d) * width, c + f * .06 - d * .15 - np.cross(f, d) * width,
                 c + f * .06 + d * length - np.cross(f, d) * width * .3, c + f * .06 + d * length + np.cross(f, d) * width * .3]
            p.add(np.array(q), [[0, 1, 2, 3], [3, 2, 1, 0]], BRASS_DULL, ELECTRUM, False)
        torus(p, tuple(c), 1.55, .07, LIME, STONE, 32, 6, 'x' if abs(f[0]) > .5 else 'y')
        # The belfry: an arched opening with timber louvres.
        for z in np.arange(18.0, 19.4, .3):
            bevel_box(p, f * 2.95 + np.array((0, 0, z)), np.abs(f) * .12 + np.abs(r) * .8 + np.array((0, 0, .04)), TIMBER, WOOD, .01)
    weather(p, s, 41, .22, 3.0)
    for k in range(30):
        a = rng.uniform(0, math.tau)
        blob(p, (math.cos(a) * 3.1, math.sin(a) * 3.1, rng.uniform(0, 1.5)), rng.uniform(.15, .3), vary(rng, WEED_GREEN, .3), LICHEN, 1, .4, k, (1, 1, .6))
    finish(p)
    return p


def signal_house():
    """The Signal House on Chapel Hill, where the Wise camp: a long two-storey limestone house (16 x 10 m) with a slate
    roof, a door on +x, and beside it a signal mast with yards and a lantern."""
    rng = _rng(42)
    p = Part('SM_HN_SignalHouse', (STONE, TILE, ENAMEL, CRYSTAL, ALLOY, CLOTH, GLOW))
    s = len(p.v)
    hx, hy, top = 5.0, 8.0, 7.0
    bevel_box(p, (0, 0, .35), (hx + .05, hy + .05, .35), LIME_SHADE, STONE, .04)
    bevel_box(p, (0, 0, 3.85), (hx, hy, 3.15), LIME, STONE, .05)
    bevel_box(p, (0, 0, 3.75), (hx + .06, hy + .06, .09), LIME_WORN, STONE, .02)
    facade_windows(p, rng, hx, (-5.5, -2.8, 2.8, 5.5), (2.0, 5.2), 1.0, 1.5, PAINT_WHITE, PAINT_BLUE, sign=1.0)
    facade_windows(p, rng, -hx, (-4.0, 0.0, 4.0), (2.0, 5.2), 1.0, 1.5, PAINT_WHITE, None, sign=-1.0)
    bevel_box(p, (hx + .25, 0, .12), (.3, .9, .12), LIME_WORN, STONE, .02)
    bevel_box(p, (hx + .06, 0, 1.6), (.06, .7, 1.0), PAINT_BLUE, ENAMEL, .015)
    gable_roof(p, (0, 0, top), 2 * hy, 2 * hx, 3.4, SLATE, TILE, .4, .16, 90.0, LIME_SHADE, STONE)
    for sy in (-1, 1):
        pts = [(-hx, sy * hy, top), (hx, sy * hy, top), (0, sy * hy, top + 3.4)]
        tri(p, *(pts if sy > 0 else pts[::-1]), LIME, STONE)
    # The mast: a steel pole 18 m high on the house's north end, two yards, a lantern at the top.
    mx, my = 0.0, hy + 3.0
    cylinder(p, (mx, my, 0), .18, 18.0, STEEL_W, ALLOY, 10, .1)
    for z, w in ((11.0, 3.0), (14.5, 2.0)):
        tube(p, [(mx, my - w, z), (mx, my + w, z)], .06, STEEL_W, ALLOY, 6)
        for sgn in (-1, 1):
            tube(p, [(mx, my + sgn * w, z), (mx + .02, my + sgn * w * .6, z - 1.2)], .02, CANVAS_W, CLOTH, 4)
    cylinder(p, (mx, my, 18.0), .3, .6, GLOW_LAMP, GLOW, 10)
    cylinder(p, (mx, my, 18.6), .38, .12, STEEL_W, ALLOY, 10)
    p.add(np.array([(mx + .2, my, 9.0), (mx + .2, my + 1.8, 9.2), (mx + .2, my + 1.8, 10.4), (mx + .2, my, 10.6)]), [[0, 1, 2, 3], [3, 2, 1, 0]],
          (.45, .05, .03), CLOTH, False)    # a signal flag
    weather(p, s, 42, .2, 2.0)
    finish(p)
    return p


def lighthouse():
    """The lighthouse on Lighthouse Point: a whitewashed tapering tower 22 m to its gallery (radius 4.2 at the foot,
    3.0 at the top), a walkable gallery 4.6 m round with a railing at 22 m, a lantern room of glass and a domed cap.
    The door is on +x; the tower's own stair is long gone (the past's flights climb its outside)."""
    rng = _rng(51)
    p = Part('SM_HN_Lighthouse', (STONE, ALLOY, CRYSTAL, ENAMEL, GLOW, LICHEN))
    s = len(p.v)
    lathe(p, [(4.6, 0.0), (4.6, .8), (4.2, .8), (3.0, 21.6), (3.0, 21.7)], PAINT_WHITE, STONE, 32)
    for z in (6.0, 12.0, 18.0):
        lathe(p, [(4.2 - (z / 21.6) * 1.2 + .06, z - .12), (4.2 - (z / 21.6) * 1.2 + .1, z), (4.2 - (z / 21.6) * 1.2 + .06, z + .12)], RENDER_GREY, STONE, 32)
    lathe(p, [(3.0, 21.7), (4.7, 21.8), (4.7, 22.0), (0.0, 22.0)], LIME_WORN, STONE, 32, smooth=False)    # the gallery floor (top at 22)
    # The railing, open on the -y side where the keeper's outside stair arrived (a gap of 3 m).
    for k in range(32):
        a = k * math.tau / 32
        if math.sin(a) < -.93:
            continue
        cylinder(p, (math.cos(a) * 4.55, math.sin(a) * 4.55, 22.0), .03, 1.05, STEEL_W, ALLOY, 6)
    gap = math.asin(.93)
    torus(p, (0, 0, 23.05), 4.55, .04, STEEL_W, ALLOY, 48, 6, 'z', math.tau - 2 * (math.pi / 2 - gap) - .2, -math.pi / 2 + (math.pi / 2 - gap) + .1)
    lathe(p, [(2.2, 22.0), (2.2, 22.6)], STEEL_W, ALLOY, 16)
    lathe(p, [(2.15, 22.6), (2.15, 25.4)], GLASS_SEA, CRYSTAL, 16, smooth=False)
    for k in range(8):
        a = k * math.tau / 8
        cylinder(p, (math.cos(a) * 2.17, math.sin(a) * 2.17, 22.6), .05, 2.8, STEEL_W, ALLOY, 6)
    cylinder(p, (0, 0, 23.2), .7, 1.6, GLOW_LAMP, GLOW, 12)
    lathe(p, [(2.4, 25.4), (2.2, 26.2), (1.2, 27.0), (.25, 27.4), (.0, 27.6)], (.22, .26, .25), ENAMEL, 24)
    cylinder(p, (0, 0, 27.5), .06, 1.2, STEEL_W, ALLOY, 6)
    bevel_box(p, (4.22, 0, 1.6), (.12, .7, 1.1), PAINT_RED, ENAMEL, .02)
    for z in (8.0, 14.0):
        r = 4.2 - (z / 21.6) * 1.2
        window_frame(p, (r + .02, 0, z), .6, 1.0, .12, PAINT_WHITE, ENAMEL, GLASS_SEA, CRYSTAL)
    weather(p, s, 51, .2, 4.0)
    for k in range(40):
        a = rng.uniform(0, math.tau)
        blob(p, (math.cos(a) * 4.62, math.sin(a) * 4.62, rng.uniform(0, .9)), rng.uniform(.15, .3), vary(rng, WEED_GREEN, .3), LICHEN, 1, .4, k, (1, 1, .6))
    finish(p)
    return p


def crane():
    """A dockside crane in the Cannery Yards: a riveted steel portal on four legs (8 x 8 m), a machinery house and cab
    at 14 m, a lattice jib reaching 16 m over the water (+x), rust running from every joint. The cab's platform (the
    foreman's post) is at 13.4 m on its +y side; its ladder is gone."""
    rng = _rng(61)
    p = Part('SM_HN_Crane', (ALLOY, ENAMEL, CRYSTAL, WOOD))
    s = len(p.v)
    paint = col(.30, .20, .08)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(p, [(sx * 4, sy * 4, 0), (sx * 2.2, sy * 2.2, 12.5)], .28, paint, ENAMEL, 8)
        tube(p, [(sx * 3.4, -3.4, 4.0), (sx * 3.4, 3.4, 4.0)], .15, paint, ENAMEL, 6)
        tube(p, [(-3.4, sx * 3.4, 4.0), (3.4, sx * 3.4, 4.0)], .15, paint, ENAMEL, 6)
        tube(p, [(sx * 3.9, -3.9, .5), (sx * 2.4, 2.4, 11.5)], .1, paint, ENAMEL, 6)
    bevel_box(p, (0, 0, 13.0), (2.8, 2.8, .5), STEEL_W, ALLOY, .04)
    bevel_box(p, (-.6, 0, 15.2), (2.4, 2.0, 1.7), paint, ENAMEL, .05)
    bevel_box(p, (-.6, 0, 17.0), (2.6, 2.2, .12), STEEL_W, ALLOY, .03)
    # The cab, forward and to +y, glazed on three sides, with its platform.
    bevel_box(p, (2.0, 2.4, 14.6), (1.1, .9, 1.1), paint, ENAMEL, .04)
    for c, w, yaw in (((3.12, 2.4, 14.8), 1.4, 0.0), ((2.0, 3.32, 14.8), 1.8, 90.0)):
        window_frame(p, c, w, .9, .1, STEEL_W, ALLOY, GLASS_SEA, CRYSTAL, yaw)
    bevel_box(p, (1.2, 4.2, 13.4), (2.6, 1.0, .06), STEEL_W, ALLOY, .02)     # the platform (top 13.46)
    for x in (-1.3, 3.7):
        cylinder(p, (x, 5.15, 13.46), .03, 1.0, STEEL_W, ALLOY, 6)
    tube(p, [(-1.3, 5.15, 14.46), (3.7, 5.15, 14.46)], .03, STEEL_W, ALLOY, 6)
    # The jib: a lattice of four chords out to +x and up.
    root, tip = np.array((1.0, 0, 16.0)), np.array((18.0, 0, 21.0))
    for dy, dz in ((-.6, -.5), (.6, -.5), (-.4, .5), (.4, .5)):
        tube(p, [root + (0, dy, dz), tip + (0, dy * .5, dz * .5)], .1, paint, ENAMEL, 6)
    for k in range(12):
        t0, t1 = k / 12, (k + 1) / 12
        a, b = root + (tip - root) * t0, root + (tip - root) * t1
        tube(p, [a + (0, -.6 * (1 - t0 * .5), -.5 * (1 - t0 * .5)), b + (0, .6 * (1 - t1 * .5), .5 * (1 - t1 * .5))], .04, paint, ENAMEL, 4)
    tube(p, [(-2.0, 0, 17.2), (-.5, 0, 22.0), tip], .05, STEEL_W, ALLOY, 4)
    tube(p, [tuple(tip), (18.0, 0, 12.0)], .03, STEEL_W, ALLOY, 4)
    bevel_box(p, (18.0, 0, 11.7), (.3, .4, .3), STEEL_W, ALLOY, .03)
    bevel_box(p, (-3.0, 0, 15.0), (.6, 1.6, 1.4), (.15, .15, .14), ALLOY, .03)   # counterweight
    bevel_box(p, (-.6, 0, 13.55), (1.6, 1.6, .05), TIMBER_GREY, WOOD, .01)
    grime(p, s, .35, 1.0, 61)
    finish(p, centre_xy=False)    # the origin stays at the portal's centre: the jib reaches out over the water
    return p


def shed():
    """A cannery shed, 20 m along y, 12 m deep: a limestone base course, corrugated steel walls and a pitched
    corrugated roof, great sliding doors on the +x side, a row of high windows, rust and salt."""
    rng = _rng(62)
    p = Part('SM_HN_Shed', (STONE, ALLOY, ENAMEL, CRYSTAL))
    s = len(p.v)
    hx, hy = 6.0, 10.0
    bevel_box(p, (0, 0, .6), (hx + .1, hy + .1, .6), LIME_SHADE, STONE, .04)
    ys = np.arange(-hy, hy + .01, .25)
    for sx in (-1, 1):   # corrugated long walls (+x and -x)
        x = sx * hx
        verts, faces = [], []
        for j, y in enumerate(ys):
            d = .05 * math.sin(j * math.pi / 2)
            verts += [(x + sx * d, y, 1.2), (x + sx * d, y, 7.0)]
        for j in range(len(ys) - 1):
            f = [2 * j, 2 * j + 2, 2 * j + 3, 2 * j + 1]
            faces.append(f if sx > 0 else f[::-1])
        p.add(np.array(verts), faces, vary(rng, STEEL_W, .1), ALLOY, False)
    for sy in (-1, 1):
        bevel_box(p, (0, sy * hy, 4.1), (hx, .06, 2.9), STEEL_W, ALLOY, .01)
        pts = [(-hx, sy * hy, 7.0), (hx, sy * hy, 7.0), (0, sy * hy, 9.4)]
        tri(p, *(pts if sy > 0 else pts[::-1]), STEEL_W, ALLOY)
    gable_roof(p, (0, 0, 7.0), 2 * hy, 2 * hx, 2.4, (.20, .17, .14), ALLOY, .5, .1, 90.0)
    for sy in (-1, 1):
        bevel_box(p, (hx + .12, sy * 4.0, 3.0), (.08, 2.8, 1.9), PAINT_OLIVE, ENAMEL, .02)
    for y in np.arange(-8.0, 8.1, 4.0):
        window_frame(p, (hx + .06, y, 6.0), 2.0, .7, .1, STEEL_W, ALLOY, GLASS_SEA, CRYSTAL)
    grime(p, s, .35, 1.6, 62)
    ao(p, s, 2.0, .6)
    finish(p)
    return p


def office():
    """The harbourmaster's office, standing in the Drowned Quarter's water: a square limestone block (8 x 8 m, 7.2 m
    to a flat roof with a parapet), a clock on its front, its outside stair long gone. The roof is walkable (top
    7.2 m): the harbourmaster's echo stands there."""
    rng = _rng(63)
    p = Part('SM_HN_Office', (STONE, ENAMEL, CRYSTAL, LICHEN))
    s = len(p.v)
    bevel_box(p, (0, 0, 3.55), (4.0, 4.0, 3.55), LIME, STONE, .05)
    bevel_box(p, (0, 0, 7.15), (4.15, 4.15, .05), LIME_WORN, STONE, .02)
    for sx, sy, hx_, hy_ in ((1, 0, .2, 4.15), (-1, 0, .2, 4.15), (0, 1, 4.15, .2), (0, -1, 4.15, .2)):
        bevel_box(p, (sx * 3.95, sy * 3.95, 7.6), (hx_, hy_, .45), LIME, STONE, .03)
    for axis_sign, axis in ((1.0, 'x'), (-1.0, 'x'), (1.0, 'y'), (-1.0, 'y')):
        facade_windows(p, rng, 4.0 * axis_sign, (-1.8, 1.8), (2.0, 5.0), .9, 1.4, PAINT_WHITE, PAINT_GREEN, sign=axis_sign, axis=axis)
    bevel_box(p, (4.05, 0, 6.2), (.05, .6, .6), PAINT_WHITE, ENAMEL, .02)
    weather(p, s, 63, .25, 3.0)
    v = np.asarray(p.v[s:], np.float64)
    c = np.asarray(p.c[s:], np.float64)
    wet = np.clip((2.6 - v[:, 2]) / 1.0, 0, 1)[:, None]
    c[:, :3] = c[:, :3] * (1 - wet * .7) + np.array(WRACK[:3]) * wet * .7
    p.c[s:] = c.tolist()
    for k in range(30):
        a = rng.uniform(-4, 4)
        side = rng.integers(0, 4)
        x, y = [(4.05, a), (-4.05, a), (a, 4.05), (a, -4.05)][side]
        blob(p, (x, y, rng.uniform(1.4, 2.4)), rng.uniform(.12, .28), vary(rng, WRACK, .3), LICHEN, 1, .4, k, (1, 1, .5))
    finish(p)
    return p


# ---------------------------------------------------------------- the Bastion and the Held Sea

def bastion_wall():
    """A panel of the Bastion's ring wall, 12 m along y, facing +x (outward): Just poured concrete, battered, 14 m
    high, with board marks, an amber-lit slit and olive-painted steel at its head."""
    rng = _rng(71)
    p = Part('SM_HN_BastionWall', (ROCK, ENAMEL, GLOW, LICHEN))
    s = len(p.v)
    z = 0.0
    while z < 13.0:
        hgt = 1.2
        lean = z / 14.0 * .9
        bevel_box(p, (-lean, 0, z + hgt / 2), (1.5 - lean * .3, 6.0, hgt / 2 - .005), vary(rng, CONCRETE_JUST, .06), ROCK, .02)
        z += hgt
    bevel_box(p, (-.9, 0, 13.6), (.9, 6.05, .6), PAINT_OLIVE, ENAMEL, .03)
    for y in (-3.0, 3.0):
        bevel_box(p, (.55, y, 9.0), (.08, .12, .9), GLOW_JUST, GLOW, .01)
    weather(p, s, 71, .25, 3.0)
    v = np.asarray(p.v[s:], np.float64)
    c = np.asarray(p.c[s:], np.float64)
    wet = np.clip((2.0 - v[:, 2]) / 1.5, 0, 1)[:, None]
    c[:, :3] = c[:, :3] * (1 - wet * .6) + np.array(WRACK[:3]) * wet * .6
    p.c[s:] = c.tolist()
    for k in range(20):
        blob(p, (1.5, rng.uniform(-5.8, 5.8), rng.uniform(.2, 1.4)), rng.uniform(.12, .3), vary(rng, WRACK, .3), LICHEN, 1, .4, k, (.5, 1, .6))
    finish(p)
    return p


def bastion():
    """The Bastion's command block, 26 m along y, 16 m deep, 18 m high: stepped concrete masses, slit windows lit
    amber, an antenna mast and the Just's olive steel. It stands at the court's north side, facing -x (the court);
    a mesh with a front faces +x, so it is placed turned 180 degrees."""
    rng = _rng(72)
    p = Part('SM_HN_Bastion', (ROCK, ENAMEL, ALLOY, GLOW, CRYSTAL))
    s = len(p.v)
    bevel_box(p, (0, 0, 6.0), (8.0, 13.0, 6.0), CONCRETE_JUST, ROCK, .06)
    bevel_box(p, (-1.5, 0, 14.0), (6.0, 9.0, 2.0), CONCRETE_JUST, ROCK, .06)
    bevel_box(p, (-3.0, 0, 17.0), (3.5, 4.0, 1.0), CONCRETE_WET, ROCK, .05)
    for z in (4.0, 8.5):
        for y in np.arange(-11.0, 11.1, 2.75):
            bevel_box(p, (8.02, y, z), (.06, .5, .14), GLOW_JUST, GLOW, .01)
    for y in (-6.0, 6.0):
        bevel_box(p, (4.6, y, 14.2), (.06, 1.6, .4), GLASS_SEA, CRYSTAL, .01)
    bevel_box(p, (8.1, 0, 2.6), (.15, 2.6, 2.6), PAINT_OLIVE, ENAMEL, .03)    # the court door
    bevel_box(p, (8.3, 0, 5.6), (.35, 3.2, .3), CONCRETE_WET, ROCK, .03)
    cylinder(p, (-3.0, 0, 18.0), .25, 14.0, STEEL_W, ALLOY, 8, .08)
    for z in (24.0, 28.0):
        tube(p, [(-3.0, -2.0, z), (-3.0, 2.0, z)], .05, STEEL_W, ALLOY, 6)
    cylinder(p, (-3.0, 0, 31.9), .25, .3, GLOW_JUST, GLOW, 8)
    for y in (-11.0, 11.0):
        bevel_box(p, (6.0, y, 12.4), (1.5, 1.5, .4), PAINT_OLIVE, ENAMEL, .03)
    weather(p, s, 72, .28, 4.0)
    finish(p)
    return p


def sea_gate():
    """The Sea Gate in the Held Sea, at the Mole's end: a concrete portal 18 m along y, its opening 10 m wide and 10
    m high (passage along x), amber lamps on its piers, a speaker horn. The door (SM_HN_GateDoor) fills it."""
    p = Part('SM_HN_SeaGate', (ROCK, ENAMEL, GLOW, ALLOY))
    s = len(p.v)
    for sy in (-1, 1):
        bevel_box(p, (0, sy * 6.5, 7.0), (2.0, 1.5, 7.0), CONCRETE_JUST, ROCK, .06)
        bevel_box(p, (2.05, sy * 6.5, 11.0), (.06, .3, .3), GLOW_JUST, GLOW, .02)
    bevel_box(p, (0, 0, 12.0), (2.0, 5.0, 2.0), CONCRETE_JUST, ROCK, .06)
    bevel_box(p, (0, 0, 14.15), (2.2, 8.2, .15), PAINT_OLIVE, ENAMEL, .03)
    lathe(p, [(.05, 0), (.45, .9)], STEEL_W, ALLOY, 12, (2.2, 5.6, 11.5))
    weather(p, s, 73, .25, 3.0)
    finish(p)
    return p


def gate_door():
    """The Sea Gate's door: one slab of olive-painted steel 10 x 10 m, 1 m thick, riveted, with an amber seam."""
    p = Part('SM_HN_GateDoor', (ENAMEL, GLOW))
    bevel_box(p, (0, 0, 5.0), (.5, 5.0, 5.0), PAINT_OLIVE, ENAMEL, .05)
    for z in np.arange(1.0, 9.6, 1.7):
        bevel_box(p, (.52, 0, z), (.03, 4.8, .06), tone(PAINT_OLIVE, .7), ENAMEL, .01)
    bevel_box(p, (.55, 0, 5.0), (.02, .06, 4.8), GLOW_JUST, GLOW, .01)
    grime(p, 0, .3, 1.2, 74)
    finish(p)
    return p


def held_sea():
    """A section of the Held Sea: water standing in a wall where the Undertow forces it back, 16 m along y, 3 m thick
    at its foot thinning to 1.2 m, 22 m high with a broken, foaming crest; magenta light runs in it near its foot.
    Placed in a ring round the Bastion, its face (+x) toward the rock. The water slot wears the sea's material."""
    rng = _rng(81)
    p = Part('SM_HN_HeldSea', (WATER, GLOW))
    ys = np.linspace(-8.2, 8.2, 25)
    zs = np.linspace(-1.0, 22.0, 30)
    verts, faces, cols = [], [], []
    for side in (1, -1):
        base = len(verts)
        for z in zs:
            t = (z + 1) / 23.0
            for y in ys:
                bump = .35 * math.sin(y * .9 + z * .5) + .2 * math.sin(y * 2.3 - z * 1.1)
                x = side * (1.5 - .9 * t) + bump * (1 if side > 0 else .3)
                zz = z if z < 21.0 else 21.0 + (1.0 + .9 * math.sin(y * 1.3)) * (z - 21.0)
                verts.append((x, y, zz))
                foam = max(0.0, (z - 19.5) / 2.5)
                cols.append(mix(col(.10, .14, .13), col(.55, .58, .56), foam))
        n = len(ys)
        for i in range(len(zs) - 1):
            for j in range(n - 1):
                f = [base + i * n + j, base + i * n + j + 1, base + (i + 1) * n + j + 1, base + (i + 1) * n + j]
                faces.append(f if side > 0 else f[::-1])
    n, m = len(ys), len(zs)
    top = (m - 1) * n
    for j in range(n - 1):      # the crest joins the two faces
        a, b = top + j, top + j + 1
        faces.append([a, n * m + a, n * m + b, b][::-1])
    p.add(np.array(verts), faces, np.array(cols), WATER, True)
    for k in range(10):
        y = rng.uniform(-7.5, 7.5)
        z0 = rng.uniform(0, 3.0)
        tube(p, [(1.6, y, z0), (1.5, y + rng.uniform(-1, 1), z0 + rng.uniform(2, 6)), (1.3, y + rng.uniform(-2, 2), z0 + rng.uniform(6, 10))],
             .05, GLOW_FORCED, GLOW, 5)
    finish(p)
    return p


def pump():
    """One of the Undertow's pumps round the Keel's chamber: a riveted olive column 2 m across and 6 m high with a
    window onto its magenta core and amber hazard lamps. The Keel's shield answers to them."""
    p = Part('SM_HN_Pump', (ENAMEL, ALLOY, GLOW, CRYSTAL))
    s = len(p.v)
    cylinder(p, (0, 0, 0), 1.0, .6, STEEL_W, ALLOY, 16)
    cylinder(p, (0, 0, .6), .85, 4.8, PAINT_OLIVE, ENAMEL, 16)
    cylinder(p, (0, 0, 5.4), 1.0, .6, STEEL_W, ALLOY, 16)
    cylinder(p, (0, 0, 1.6), .6, 2.6, GLOW_FORCED, GLOW, 12)
    for k in range(4):
        a = k * math.pi / 2
        bevel_box(p, (math.cos(a) * .86, math.sin(a) * .86, 2.9), (.06, .32, 1.2), GLASS_SEA, CRYSTAL, .01, math.degrees(a))
    cylinder(p, (0, 0, 6.0), .2, .25, GLOW_JUST, GLOW, 8)
    grime(p, s, .3, 1.0, 75)
    finish(p)
    return p


# ---------------------------------------------------------------- the past (traces)

def bridge():
    """The Harbour Bridge as it stood before the strike: an iron girder bridge along x, 32 m long, a continuous deck
    6 m wide (top at z 0 from end to end) between lattice parapets 1.1 m high, two arched girders beneath. Pivot at
    the deck's top centre."""
    p = Part('SM_HN_Bridge', (ALLOY, STONE, WOOD))
    bevel_box(p, (0, 0, -.15), (16.0, 3.0, .15), TIMBER_GREY, WOOD, .02)
    bevel_box(p, (0, 0, -.45), (16.0, 3.3, .15), STEEL_W, ALLOY, .02)
    for sy in (-1, 1):
        y = sy * 3.2
        tube(p, [(-16, y, 1.1), (16, y, 1.1)], .05, STEEL_W, ALLOY, 6)
        for x in np.arange(-16.0, 16.01, 1.6):
            cylinder(p, (x, y, 0), .035, 1.1, STEEL_W, ALLOY, 6)
            tube(p, [(x, y, .1), (x + .8, y, 1.0)], .02, STEEL_W, ALLOY, 4)
        pts = [(x, y, -.6 - 2.2 * (1 - (x / 16.0) ** 2)) for x in np.linspace(-16, 16, 17)]
        tube(p, pts, .25, STEEL_W, ALLOY, 8)
        for x in np.linspace(-14, 14, 8):
            tube(p, [(x, y, -.6), (x, y, -.6 - 2.2 * (1 - (x / 16.0) ** 2))], .07, STEEL_W, ALLOY, 6)
    for sx in (-1, 1):
        bevel_box(p, (sx * 15.4, 0, -1.6), (.6, 3.4, 1.1), LIME_SHADE, STONE, .04)
    return p


def catwalk():
    """A timber catwalk of the old waterfront, 9 m along x, 2.4 m wide, on two crossbeams, a rope handrail on posts
    along one side. Pivot at its deck's top centre."""
    p = Part('SM_HN_Catwalk', (WOOD, CLOTH, ALLOY))
    for y in np.arange(-1.1, 1.11, .275):
        bevel_box(p, (0, y, -.05), (4.5, .12, .05), TIMBER_GREY, WOOD, .01)
    for x in (-3.8, 3.8):
        bevel_box(p, (x, 0, -.2), (.12, 1.25, .1), TIMBER, WOOD, .01)
    for x in np.arange(-4.4, 4.41, 2.2):
        cylinder(p, (x, 1.15, 0), .05, 1.0, TIMBER, WOOD, 6)
    tube(p, [(-4.4, 1.15, .95), (4.4, 1.15, .95)], .025, CANVAS_W, CLOTH, 5)
    for x in (-4.3, 4.3):
        bevel_box(p, (x, -1.15, -.1), (.08, .06, .06), STEEL_W, ALLOY, .01)
    return p


def flight():
    """A flight of an old outside stair: timber treads on steel stringers climbing +x, 8 m of run and 6 m of rise
    (20 treads of 0.4 x 0.3 m), 2.4 m wide, and a top landing 1.4 m deep flush with x +4.7. Foot at x -4.7, z 0;
    'base' pivot, footprint centred."""
    p = Part('SM_HN_Flight', (WOOD, ALLOY))
    for k in range(20):
        x = -4.7 + .4 * k + .2
        z = .3 * (k + 1)
        bevel_box(p, (x, 0, z - .04), (.21, 1.2, .04), TIMBER_GREY, WOOD, .01)
    bevel_box(p, (4.0, 0, 5.96), (.7, 1.2, .04), TIMBER_GREY, WOOD, .01)
    # Stringers under the treads, and a handrail along the climb only: the landing's sides stay open, so a
    # switchback steps sideways from one flight's landing onto the next flight's foot.
    for sy in (-1, 1):
        tube(p, [(-4.7, sy * 1.25, .05), (3.3, sy * 1.25, 5.95), (4.7, sy * 1.25, 5.95)], .05, STEEL_W, ALLOY, 6)
        tube(p, [(-4.3, sy * 1.25, 1.3), (3.0, sy * 1.25, 6.78)], .03, STEEL_W, ALLOY, 5)
        for x in (-4.3, -.5, 3.0):
            z = max(0.0, min(6.0, (x + 4.7) * .75))
            cylinder(p, (x, sy * 1.25, 0.0), .04, z + 1.0, STEEL_W, ALLOY, 6)
    return p


def shelf():
    """A library bookcase as it stood: dark timber, 3 m along y, 2.6 m high, five shelves of books facing +x."""
    rng = _rng(91)
    p = Part('SM_HN_Shelf', (WOOD, CLOTH))
    bevel_box(p, (-.15, 0, 1.3), (.05, 1.5, 1.3), TIMBER, WOOD, .01)
    for sy in (-1, 1):
        bevel_box(p, (0, sy * 1.47, 1.3), (.2, .03, 1.3), TIMBER, WOOD, .01)
    for k in range(6):
        z = .1 + k * .5
        bevel_box(p, (0, 0, z), (.2, 1.47, .025), TIMBER, WOOD, .005)
        if k < 5:
            y = -1.4
            while y < 1.35:
                w = rng.uniform(.03, .07)
                hgt = rng.uniform(.28, .42)
                bevel_box(p, (.02, y + w, z + .03 + hgt / 2), (.15, w, hgt / 2), vary(rng, rng.choice([PAINT_RED, PAINT_BLUE, PAINT_GREEN, CANVAS_W, TIMBER]), .25),
                          CLOTH, .004)
                y += 2 * w + .005
    finish(p)
    return p


# ---------------------------------------------------------------- props

def lamp():
    """A cast-iron street lamp, 4.4 m: a fluted post on a square base, a scrolled arm, a glazed lantern."""
    p = Part('SM_HN_Lamp', (ALLOY, CRYSTAL, GLOW))
    bevel_box(p, (0, 0, .25), (.2, .2, .25), STEEL_W, ALLOY, .03)
    cylinder(p, (0, 0, .5), .1, 3.4, STEEL_W, ALLOY, 10, .06)
    tube(p, [(0, 0, 3.6), (.3, 0, 3.9), (.55, 0, 3.85)], .03, STEEL_W, ALLOY, 6)
    lathe(p, [(.12, 3.5), (.22, 3.7), (.22, 4.15)], GLASS_SEA, CRYSTAL, 6, (.55, 0, 0), False)
    lathe(p, [(.26, 4.15), (.05, 4.45)], STEEL_W, ALLOY, 6, (.55, 0, 0), False)
    cylinder(p, (.55, 0, 3.75), .06, .25, col(.25, .2, .14), GLOW, 6)
    finish(p)
    return p


def bollard():
    p = Part('SM_HN_Bollard', (ALLOY,))
    lathe(p, [(.24, 0.0), (.2, .55), (.28, .7), (.18, .8), (.03, .82)], STEEL_W, ALLOY, 16)
    grime(p, 0, .35, .4, 92)
    finish(p)
    return p


def crate():
    rng = _rng(93)
    p = Part('SM_HN_Crate', (WOOD,))
    bevel_box(p, (0, 0, .55), (.6, .6, .55), TIMBER_GREY, WOOD, .03)
    for z in (.15, .95):
        for sy in (-1, 1):
            bevel_box(p, (0, sy * .62, z), (.62, .03, .08), TIMBER, WOOD, .01)
            bevel_box(p, (sy * .62, 0, z), (.03, .62, .08), TIMBER, WOOD, .01)
    grime(p, 0, .3, .5, 93)
    finish(p)
    return p


def speaker():
    """A Just speaker post: an olive steel post 3.6 m high with a horn and an amber lamp (Commodore Marr's voice)."""
    p = Part('SM_HN_Speaker', (ENAMEL, ALLOY, GLOW))
    bevel_box(p, (0, 0, .2), (.3, .3, .2), CONCRETE_JUST, ENAMEL, .03)
    cylinder(p, (0, 0, .4), .08, 3.0, PAINT_OLIVE, ENAMEL, 8)
    bevel_box(p, (.1, 0, 2.6), (.16, .2, .3), PAINT_OLIVE, ENAMEL, .02)
    tube(p, [(.2, 0, 3.0), (.55, 0, 3.0), (.95, 0, 3.0)], [.08, .16, .36], STEEL_W, ALLOY, 12)
    cylinder(p, (0, 0, 3.4), .1, .2, GLOW_JUST, GLOW, 8)
    finish(p)
    return p


def cache():
    """A tide cache: a brass-bound sea chest the town's pilots kept against bad nights. 'centre' pivot."""
    p = Part('SM_HN_Cache', (WOOD, ELECTRUM, GLOW))
    bevel_box(p, (0, 0, 0), (.45, .3, .25), TIMBER, WOOD, .03)
    for x in (-.3, .3):
        bevel_box(p, (x, 0, 0), (.03, .32, .27), BRASS_DULL, ELECTRUM, .01)
    lathe(p, [(.3, .25), (.3, .3), (.02, .31)], TIMBER, WOOD, 12, (0, 0, 0))
    bevel_box(p, (.46, 0, .05), (.02, .06, .06), GLOW_PAST, GLOW, .01)
    centre(p)
    return p


def logbook():
    """Ledger's field logbook: a canvas-bound book with a brass clasp. 'centre' pivot."""
    p = Part('SM_HN_Logbook', (CLOTH, ELECTRUM))
    bevel_box(p, (0, 0, 0), (.16, .12, .03), (.12, .16, .2), CLOTH, .01)
    bevel_box(p, (.0, .0, .032), (.15, .11, .004), CANVAS_W, CLOTH, .002)
    bevel_box(p, (.165, 0, 0), (.01, .03, .03), BRASS_DULL, ELECTRUM, .004)
    centre(p)
    return p


def pontoon():
    """A pontoon of the bridge the Wise and the town lay over the Breach once the sea lies down: 9 m along x, 4 m
    wide, timber decking on steel floats. Pivot at its deck's top centre."""
    p = Part('SM_HN_Pontoon', (WOOD, ALLOY, CLOTH))
    for y in np.arange(-1.8, 1.81, .3):
        bevel_box(p, (0, y, -.05), (4.5, .14, .05), TIMBER_GREY, WOOD, .01)
    for sy in (-1, 1):
        tube(p, [(-4.3, sy * 1.3, -.6), (4.3, sy * 1.3, -.6)], .5, STEEL_W, ALLOY, 12)
        tube(p, [(-4.5, sy * 1.95, .9), (4.5, sy * 1.95, .9)], .025, CANVAS_W, CLOTH, 5)
        for x in np.arange(-4.4, 4.41, 2.2):
            cylinder(p, (x, sy * 1.95, 0), .04, .9, STEEL_W, ALLOY, 6)
    return p


# ---------------------------------------------------------------- contract

MESHES = [house, quay, mole_slab, boat, clocktower, signal_house, lighthouse, crane, shed, office, bastion_wall, bastion, sea_gate, gate_door,
          held_sea, pump, bridge, catwalk, flight, shelf, lamp, bollard, crate, speaker, cache, logbook, pontoon]
VARIANTS = {house: 4}
_T = .08
CONTRACT = {
    'SM_HN_House0': {'size': (8.1, 7.1, 0), 'tol': .2}, 'SM_HN_House1': {'size': (6.5, 6.1, 0), 'tol': .2},
    'SM_HN_House3': {'size': (0, 8.1, 0), 'tol': .2},
    'SM_HN_Quay': {'size': (2.5, 12.0, 10.1), 'tol': .1}, 'SM_HN_MoleSlab': {'size': (12.0, 0, 4.7), 'tol': .25},
    'SM_HN_Clocktower': {'size': (6.6, 6.6, 27.2), 'tol': .1}, 'SM_HN_Lighthouse': {'size': (9.4, 9.4, 28.8), 'tol': .1},
    'SM_HN_BastionWall': {'size': (3.73, 12.1, 14.2), 'tol': .1}, 'SM_HN_SeaGate': {'size': (4.85, 16.4, 14.3), 'tol': .1},
    'SM_HN_GateDoor': {'size': (1.1, 10.0, 10.0), 'tol': .1},
    'SM_HN_Bridge': {'size': (32.0, 7.0, 0), 'tol': .1, 'pivot': 'any', 'top': 1.15},
    'SM_HN_Catwalk': {'size': (9.0, 2.4, 0), 'tol': .1, 'pivot': 'any'},
    'SM_HN_Pontoon': {'size': (9.0, 4.0, 0), 'tol': .1, 'pivot': 'any'},
    'SM_HN_Crane': {'pivot': 'any'},
    'SM_HN_Flight': {'size': (9.4, 2.6, 6.8), 'tol': .1},
    'SM_HN_Cache': {'pivot': 'centre'}, 'SM_HN_Logbook': {'pivot': 'centre'},
}
