"""Morrow's buildings, the dam and the Hold, the Rime, the props, and the rooms of the Morning (level 8;
Tools/morrow/README.md is the contract).

The valley builds in grey granite, lime-washed on the houses, under slate; the mill and the bridge are old timber; the
Just's Hold is poured concrete and olive-painted steel with amber lamps. Frost is the materials' work (the Morrow
copies of the Grove's masters frost every face that looks up); the Rime is geometry: hoarfrost grown into standing
crystals, white, with the forced magenta deep in its roots. The Morning's rooms are the Holts' house as Maren
remembers it: the kitchen, the long hall, the field, the crest, each standing in the mist.
"""
from kit import *  # noqa: F401,F403


def _rng(seed):
    return np.random.default_rng(seed)


def weather(p, start, seed, amount=.2, height=1.6):
    grime(p, start, amount, 1.4, seed)
    ao(p, start, height, .62)


def wall_windows(p, rng, x, ys, z, w, h, sign=1.0, axis='x', glass=GLASS_COLD, frame=PAINT_WHITE, lit=False):
    """Windows on a wall face: the plane x = const facing +x (sign 1) or -x for axis 'x', or y = const for 'y'."""
    yaw = (0.0 if sign > 0 else 180.0) if axis == 'x' else (90.0 if sign > 0 else -90.0)
    for u in ys:
        c = (x + .03 * sign, u, z) if axis == 'x' else (u, x + .03 * sign, z)
        window_frame(p, c, w, h, .14, frame, ENAMEL, GLOW_LAMP if lit else glass, GLOW if lit else CRYSTAL, yaw, 1, .05)


def gable(p, at, thick, half, z0, rise, colour, slot, axis='x'):
    """A gable end: a triangular slab of wall (base 2 * half wide at height z0, apex rise above it), thick metres
    through, standing across `axis` at `at` (a gable on an end wall at x = at for axis 'x', at y = at for 'y')."""
    t = thick / 2
    if axis == 'x':
        pts = [(at - t, -half, z0), (at - t, half, z0), (at - t, 0, z0 + rise), (at + t, -half, z0), (at + t, half, z0), (at + t, 0, z0 + rise)]
    else:
        pts = [(half, at - t, z0), (-half, at - t, z0), (0, at - t, z0 + rise), (half, at + t, z0), (-half, at + t, z0), (0, at + t, z0 + rise)]
    faces = [[0, 2, 1], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]]
    v = np.array(pts, np.float64)
    centre_ = v.mean(0)
    fixed = []
    for f in faces:
        a, b, c = v[f[0]], v[f[1]], v[f[2]]
        n = np.cross(b - a, c - b)
        fixed.append(f if np.dot(n, v[f].mean(0) - centre_) > 0 else f[::-1])
    p.add(v, fixed, colour, slot, False)


# ---------------------------------------------------------------- the Rime

def rime_cluster(p, rng, centre, half, count, height, lean=18.0, root=True):
    """Hoarfrost grown into standing crystals over a footprint (half extents x, y): tall six-sided needles leaning
    out from the middle, smaller ones at their feet, the forced magenta glowing at their roots."""
    cx, cy, cz = centre
    hx, hy = half
    for k in range(count):
        u, v = rng.uniform(-1, 1), rng.uniform(-1, 1)
        x, y = cx + u * hx, cy + v * hy
        edge = max(abs(u), abs(v))
        h = height * rng.uniform(.45, 1.0) * (1.0 - .55 * edge ** 2)
        a = math.radians(rng.uniform(0, 360))
        tilt = math.radians(rng.uniform(0, lean) + 12.0 * edge)
        out = np.array((math.cos(a) * math.sin(tilt) + u * .25, math.sin(a) * math.sin(tilt) + v * .25, math.cos(tilt)))
        out /= np.linalg.norm(out)
        r = rng.uniform(.12, .32) * (h / height) ** .5 + .05
        base = np.array((x, y, cz - .2))
        prism(p, base, base + out * h, r, vary(rng, FROST, .08), LICHEN, 6, rng.uniform(.18, .35))
        if root and rng.uniform() < .45:
            blob(p, (x, y, cz + .1), r * 1.6, GLOW_RIME, GLOW, 1, .2, int(rng.integers(0, 999)), (1, 1, .5))
    for k in range(count // 2):      # the rime's skirt: small needles low down
        u, v = rng.uniform(-1.15, 1.15), rng.uniform(-1.15, 1.15)
        base = np.array((cx + u * hx, cy + v * hy, cz - .1))
        h = height * rng.uniform(.08, .25)
        a = math.radians(rng.uniform(0, 360))
        out = np.array((math.cos(a) * .5, math.sin(a) * .5, 1.0))
        prism(p, base, base + out / np.linalg.norm(out) * h, rng.uniform(.05, .14), vary(rng, FROST_BLUE, .1), LICHEN, 5, .4)


def rime_wall():
    """SM_ON_RimeWall: a standing wall of Rime 12 m long (y), 3 m deep, about 6 m high; a Rime wall across a yard, a
    lane or a doorway. Box collision; tag MorrowScar (gone when the Lull stops)."""
    p = Part('SM_ON_RimeWall', (LICHEN, GLOW))
    rime_cluster(p, _rng(801), (0, 0, 0), (1.2, 5.8), 120, 6.2, 10.0)
    finish(p)
    return p


def rime_mound():
    """SM_ON_RimeMound: the Rime heaped over the Ferry Bridge, 34 m along the bridge (x), 9 m wide, 7 m high: a long
    ridge of crystals and frozen spray. Box collision; it goes for good when the keeper wakes."""
    p = Part('SM_ON_RimeMound', (LICHEN, GLOW))
    rng = _rng(802)
    for x in np.linspace(-15.5, 15.5, 9):
        blob(p, (x, rng.uniform(-.6, .6), 1.6), (2.6, 3.4, 2.4), vary(rng, FROST, .06), LICHEN, 2, .25, int(rng.integers(0, 999)))
    rime_cluster(p, rng, (0, 0, 1.4), (16.0, 3.6), 260, 6.0, 22.0)
    finish(p)
    return p


def rime_door():
    """SM_ON_RimeDoor: Rime filling a doorway, 0.8 m deep, 1.8 m wide, 2.6 m high (in the Morning's rooms). Box
    collision."""
    p = Part('SM_ON_RimeDoor', (LICHEN, GLOW))
    rng = _rng(803)
    for k in range(70):
        y, z = rng.uniform(-.85, .85), rng.uniform(.1, 2.4)
        base = np.array((rng.uniform(-.3, .3), y, z))
        a = rng.uniform(0, math.tau)
        out = np.array((rng.choice((-1, 1)) * rng.uniform(.4, 1), math.cos(a) * .6, math.sin(a) * .6))
        out /= np.linalg.norm(out)
        prism(p, base - out * .3, base + out * rng.uniform(.4, .9), rng.uniform(.06, .16), vary(rng, FROST, .08), LICHEN, 6, .3)
    for k in range(8):
        blob(p, (0, rng.uniform(-.7, .7), rng.uniform(.3, 2.2)), .18, GLOW_RIME, GLOW, 1, .2, k, (.6, 1, 1))
    bevel_box(p, (0, 0, 1.3), (.25, .9, 1.3), vary(rng, FROST_BLUE, .05), LICHEN, .1)
    finish(p)
    return p


# ---------------------------------------------------------------- the valley's buildings

def chapel():
    """SM_ON_Chapel: the Pass Chapel (and, larger, the chapel on the square): a small granite chapel, lime-washed,
    9 m long (x), 6 m wide, a slate gable roof along x, a bell-cote on its front gable (+x) with its bell, an arched
    door under it, two narrow arched windows each side. Front (+x)."""
    p = Part('SM_ON_Chapel', (STONE, TILE, ENAMEL, CRYSTAL, ELECTRUM, WOOD))
    rng = _rng(811)
    s = len(p.v)
    hx, hy, eave = 4.5, 3.0, 4.6
    bevel_box(p, (0, 0, .3), (hx + .1, hy + .1, .3), GRANITE_SHADE, STONE, .04)
    bevel_box(p, (0, 0, .6 + (eave - .6) / 2), (hx, hy, (eave - .6) / 2), WHITEWASH, STONE, .05)
    # The gables: stepped granite triangles (hexa wedges) at both ends.
    for sx in (-1, 1):
        gable(p, sx * hx, .5, hy, eave, 2.4, WHITEWASH, STONE)
    gable_roof(p, (0, 0, eave), 2 * hx, 2 * hy, 2.4, SLATE, TILE, .45, .16, 0.0, SLATE_PALE, TILE)
    # Quoins.
    for sx in (-1, 1):
        for sy in (-1, 1):
            z = .6
            while z < eave - .2:
                big = int(z / .4) % 2 == 0
                bevel_box(p, (sx * (hx - (.28 if big else .18)), sy * (hy + .02), z + .19), (.28 if big else .18, .05, .18), GRANITE, STONE, .02)
                bevel_box(p, (sx * (hx + .02), sy * (hy - (.18 if big else .28)), z + .19), (.05, .18 if big else .28, .18), GRANITE, STONE, .02)
                z += .4
    # The door: an arched granite surround, a plank door.
    arch(p, (hx + .06, 0, 0), 1.5, 3.0, .28, .3, GRANITE, STONE, 0.0, 10)
    for sy in (-1, 1):
        bevel_box(p, (hx + .06, sy * .89, 1.12), (.15, .14, 1.12), GRANITE, STONE, .02)
    bevel_box(p, (hx + .02, 0, 1.12), (.05, .74, 1.12), TIMBER, WOOD, .015)
    p.add(np.array([(hx + .021, -.74, 2.24), (hx + .021, .74, 2.24), (hx + .021, 0, 2.95)]), [[0, 1, 2]], TIMBER, WOOD, False)
    for z in (.5, 1.7):
        bevel_box(p, (hx + .08, 0, z), (.02, .7, .05), STEEL_W, ENAMEL, .01)
    # Lancet windows along both sides.
    for sy in (-1, 1):
        for x in (-2.2, 1.4):
            yaw = 90.0 if sy > 0 else -90.0
            window_frame(p, (x, sy * (hy + .03), 2.4), .55, 1.5, .14, GRANITE, STONE, GLASS_COLD, CRYSTAL, yaw, 0, .07)
            arch(p, (x, sy * (hy + .05), 1.6), .7, 1.75, .12, .16, GRANITE, STONE, yaw, 6)
    # The bell-cote: a granite frame on the front gable's peak, its bell hanging in it.
    top = eave + 2.4
    for sy in (-1, 1):
        bevel_box(p, (hx, sy * .55, top + .7), (.3, .15, .8), GRANITE, STONE, .03)
    bevel_box(p, (hx, 0, top + 1.6), (.35, .75, .12), GRANITE, STONE, .03)
    p.add(np.array([(hx - .36, -.8, top + 1.72), (hx + .36, -.8, top + 1.72), (hx + .36, .8, top + 1.72), (hx - .36, .8, top + 1.72),
                    (hx, -.8, top + 2.2), (hx, .8, top + 2.2)]), [[0, 1, 4], [3, 5, 2], [1, 2, 5, 4], [3, 0, 4, 5]], SLATE, TILE, False)
    lathe(p, [(.05, -.62), (.3, -.55), (.25, -.3), (.18, 0.0), (.06, .06)], BRASS_DULL, ELECTRUM, 16, (hx, 0, top + 1.4))
    weather(p, s, 811, .18, 2.0)
    finish(p)
    return p


def mill():
    """SM_ON_Mill: the Mill House, two storeys of granite 10 m long (x) and 8 m wide under slate, a lean-to on its
    west end, the wheel's axle box on its -y side (the wheel is its own mesh), a door and windows on its front (+x)."""
    p = Part('SM_ON_Mill', (STONE, TILE, ENAMEL, CRYSTAL, WOOD, GLOW))
    rng = _rng(812)
    s = len(p.v)
    hx, hy, eave = 5.0, 4.0, 6.0
    bevel_box(p, (0, 0, eave / 2), (hx, hy, eave / 2), GRANITE, STONE, .05)
    for sx in (-1, 1):
        gable(p, sx * hx, .4, hy, eave, 3.0, GRANITE, STONE)
    gable_roof(p, (0, 0, eave), 2 * hx, 2 * hy, 3.0, SLATE, TILE, .45, .18, 0.0, SLATE_PALE, TILE)
    # A chimney on the east gable.
    bevel_box(p, (hx - .6, 1.6, eave + 3.2), (.45, .55, 1.6), GRANITE_SHADE, STONE, .03)
    # Front (+x): a door and windows, one lit (Edda keeps the fire).
    bevel_box(p, (hx + .03, -1.4, 1.1), (.06, .6, 1.1), PAINT_GREEN, ENAMEL, .015)
    bevel_box(p, (hx + .06, -1.4, 2.28), (.1, .78, .1), GRANITE_SHADE, STONE, .02)
    wall_windows(p, rng, hx, (1.6,), 1.7, 1.0, 1.3, 1.0, 'x', lit=True)
    wall_windows(p, rng, hx, (-1.8, 1.8), 4.3, .9, 1.2, 1.0, 'x')
    wall_windows(p, rng, -hx, (0.0,), 4.3, .9, 1.2, -1.0, 'x')
    wall_windows(p, rng, hy, (-2.5, 2.5), 4.3, .9, 1.2, 1.0, 'y')
    # The lean-to on the west end.
    bevel_box(p, (-hx - 1.6, 0, 1.3), (1.6, 3.0, 1.3), GRANITE_SHADE, STONE, .04)
    p.add(np.array([(-hx, -3.3, 3.2), (-hx, 3.3, 3.2), (-hx - 3.5, 3.3, 2.4), (-hx - 3.5, -3.3, 2.4)]), [[0, 3, 2, 1], [1, 2, 3, 0]], SLATE, TILE, False)
    # The wheel's axle box and the leat on the -y side.
    bevel_box(p, (-1.0, -hy - .4, 2.6), (.5, .4, .5), TIMBER, WOOD, .03)
    bevel_box(p, (-1.0, -hy - 1.8, 5.4), (3.6, .45, .25), TIMBER, WOOD, .03)
    for x in (-3.8, 1.8):
        bevel_box(p, (x, -hy - 1.8, 2.7), (.15, .15, 2.7), TIMBER, WOOD, .02)
    weather(p, s, 812, .22, 2.2)
    finish(p)
    return p


def wheel():
    """SM_ON_Wheel: the mill wheel, 5.2 m across and 1.3 m wide (its axle along y), timber rims, spokes and paddles,
    frozen. 'centre' pivot on its axle, so the level can turn it once the miller wakes."""
    p = Part('SM_ON_Wheel', (WOOD, ALLOY))
    rng = _rng(813)
    for y in (-.55, .55):
        torus(p, (0, y, 0), 2.5, .1, vary(rng, TIMBER, .1), WOOD, 40, 6, 'y')
        torus(p, (0, y, 0), 1.7, .08, vary(rng, TIMBER, .1), WOOD, 32, 6, 'y')
        for k in range(8):
            a = k * math.tau / 8
            tube(p, [(0, y, 0), (math.cos(a) * 2.45, y, math.sin(a) * 2.45)], .07, TIMBER, WOOD, 6)
    for k in range(24):
        a = k * math.tau / 24
        c = np.array((math.cos(a) * 2.35, 0, math.sin(a) * 2.35))
        bevel_box(p, tuple(c), (.07 if abs(math.sin(a)) > .7 else .3, .62, .3 if abs(math.sin(a)) > .7 else .07), vary(rng, TIMBER_GREY, .1), WOOD, .02)
    tube(p, [(0, -.85, 0), (0, .85, 0)], .16, STEEL_W, ALLOY, 12)
    centre(p)
    return p


def bench():
    """SM_ON_Bench: Edda's bench by the millpond, 1.9 m long (y), timber slats on cast-iron ends, a small brass plate
    on its backrest (his name is cut in it; no letters are modelled). Front (+x)."""
    p = Part('SM_ON_Bench', (WOOD, ALLOY, ELECTRUM))
    rng = _rng(814)
    for sy in (-.85, .85):
        tube(p, [(.25, sy, 0), (.2, sy, .45), (-.2, sy, .48), (-.28, sy, .95)], .035, STEEL_W, ALLOY, 6)
        tube(p, [(-.25, sy, 0), (-.18, sy, .45)], .035, STEEL_W, ALLOY, 6)
    for k in range(4):
        bevel_box(p, (.18 - k * .12, 0, .47), (.045, .98, .02), vary(rng, TIMBER, .15), WOOD, .008)
    for k in range(3):
        z = .62 + k * .12
        bevel_box(p, (-.2 - .06 * k, 0, z), (.02, .98, .045), vary(rng, TIMBER, .15), WOOD, .008)
    bevel_box(p, (-.15, 0, .74), (.012, .12, .03), BRASS_DULL, ELECTRUM, .004)
    finish(p)
    return p


def bridge():
    """SM_ON_Bridge: the Ferry Bridge, 32 m long (x) and 5 m wide: a timber deck on two king-post trusses, railings,
    iron straps. Pivot at the deck's top centre (the scenario sets it between the Gorge's rims)."""
    p = Part('SM_ON_Bridge', (WOOD, ALLOY, STONE))
    rng = _rng(815)
    L, W = 16.0, 2.5
    bevel_box(p, (0, 0, -.2), (L, W, .2), TIMBER, WOOD, .03)
    for k in range(int(2 * L / .4)):
        x = -L + .2 + k * .4
        bevel_box(p, (x, 0, -.02), (.18, W + .05, .03), vary(rng, TIMBER_GREY, .12), WOOD, .006)
    for sy in (-1, 1):
        y = sy * (W - .1)
        bevel_box(p, (0, y, -.7), (L, .14, .35), TIMBER, WOOD, .02)
        for x in np.linspace(-L + .2, L - .2, 17):
            bevel_box(p, (x, y, .55), (.07, .07, .55), TIMBER, WOOD, .01)
        bevel_box(p, (0, y, 1.12), (L, .08, .05), TIMBER, WOOD, .01)
        bevel_box(p, (0, y, .6), (L, .04, .03), TIMBER, WOOD, .01)
        # The truss: a king post at the middle, braces to the ends, under the deck.
        tube(p, [(-L, y, -.9), (0, y, -3.0), (L, y, -.9)], .12, TIMBER, WOOD, 6)
        tube(p, [(0, y, -.4), (0, y, -3.0)], .1, TIMBER, WOOD, 6)
        for x in (-8.0, 8.0):
            tube(p, [(x, y, -.5), (x, y, -1.95)], .07, STEEL_W, ALLOY, 6)
    # Granite seats at both ends.
    for sx in (-1, 1):
        bevel_box(p, (sx * (L - .6), 0, -1.4), (.6, W + .3, 1.2), GRANITE, STONE, .04)
    grime(p, 0, .18, 1.6, 815)
    return p


def school():
    """SM_ON_School: the Schoolhouse, 18 m long (y) and 9 m deep (x), one tall storey of lime-washed granite under
    slate, tall windows along its front (+x) and back, its door in the middle of the front under a small porch, a
    timber bell cupola on the ridge."""
    p = Part('SM_ON_School', (STONE, TILE, ENAMEL, CRYSTAL, WOOD, ELECTRUM))
    rng = _rng(816)
    s = len(p.v)
    hx, hy, eave = 4.5, 9.0, 5.2
    bevel_box(p, (0, 0, .3), (hx + .1, hy + .1, .3), GRANITE_SHADE, STONE, .04)
    bevel_box(p, (0, 0, .6 + (eave - .6) / 2), (hx, hy, (eave - .6) / 2), WHITEWASH, STONE, .05)
    for sy in (-1, 1):
        gable(p, sy * hy, .4, hx, eave, 2.6, WHITEWASH, STONE, 'y')
    gable_roof(p, (0, 0, eave), 2 * hy, 2 * hx, 2.6, SLATE, TILE, .45, .16, 90.0, SLATE_PALE, TILE)
    ys = [y for y in np.linspace(-hy + 1.6, hy - 1.6, 6) if abs(y) > 1.6]
    wall_windows(p, rng, hx, ys, 2.6, 1.1, 2.4, 1.0, 'x')
    wall_windows(p, rng, -hx, list(np.linspace(-hy + 1.6, hy - 1.6, 6)), 2.6, 1.1, 2.4, -1.0, 'x')
    bevel_box(p, (hx + .03, 0, 1.25), (.06, .8, 1.25), PAINT_BLUE, ENAMEL, .015)
    # The porch: two posts and a little slate roof.
    for sy in (-1, 1):
        bevel_box(p, (hx + 1.5, sy * 1.2, 1.4), (.1, .1, 1.4), TIMBER, WOOD, .02)
    p.add(np.array([(hx, -1.5, 3.3), (hx, 1.5, 3.3), (hx + 1.8, 1.5, 2.85), (hx + 1.8, -1.5, 2.85)]), [[0, 3, 2, 1], [1, 2, 3, 0]], SLATE, TILE, False)
    bevel_box(p, (hx + .7, 0, .1), (.8, 1.4, .1), GRANITE_WORN, STONE, .02)
    # The cupola and its bell.
    top = eave + 2.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(p, (sx * .55, sy * .55, top + .6), (.07, .07, .7), PAINT_WHITE, ENAMEL, .01)
    bevel_box(p, (0, 0, top + .05), (.7, .7, .12), PAINT_WHITE, ENAMEL, .01)
    lathe(p, [(.75, top + 1.3), (.6, top + 1.5), (.05, top + 2.1)], SLATE, TILE, 4, (0, 0, 0), False, math.tau, math.pi / 4)
    lathe(p, [(.04, -.42), (.22, -.38), (.18, -.2), (.12, 0.0), (.04, .04)], BRASS_DULL, ELECTRUM, 14, (0, 0, top + 1.05))
    weather(p, s, 816, .16, 1.8)
    finish(p)
    return p


def hangar():
    """SM_ON_Hangar: the gliding club's hangar on the field, 14 m deep (x) and 18 m wide, open at the front (+x): a
    timber frame under a shallow corrugated roof, boarded sides and back. Complex collision (she can walk in)."""
    p = Part('SM_ON_Hangar', (WOOD, ALLOY, ENAMEL))
    rng = _rng(817)
    hx, hy, h = 7.0, 9.0, 5.4
    for x in np.linspace(-hx, hx, 6):
        for sy in (-1, 1):
            bevel_box(p, (x, sy * hy, h / 2), (.14, .14, h / 2), TIMBER, WOOD, .02)
        tube(p, [(x, -hy, h), (x, 0, h + 1.0), (x, hy, h)], .1, TIMBER, WOOD, 6)
    for sy in (-1, 1):
        for k in range(14):
            bevel_box(p, (rng.uniform(-.02, .02), sy * hy, .25 + k * .38), (hx, .03, .17), vary(rng, TIMBER_GREY, .14), WOOD, .006)
    for k in range(14):
        bevel_box(p, (-hx, 0, .25 + k * .38), (.03, hy, .17), vary(rng, TIMBER_GREY, .14), WOOD, .006)
    for sy in (-1, 1):
        n = 12
        for k in range(n):
            y0, y1 = sy * hy * k / n, sy * hy * (k + 1) / n
            z0, z1 = h + 1.0 - k / n * 1.0, h + 1.0 - (k + 1) / n * 1.0
            pts = np.array([(-hx - .3, y0, z0 + .12), (hx + .4, y0, z0 + .12), (hx + .4, y1, z1 + .12), (-hx - .3, y1, z1 + .12)])
            p.add(pts if sy > 0 else pts[::-1], [[0, 1, 2, 3], [3, 2, 1, 0]], vary(rng, STEEL_W, .1), ALLOY, False)
    bevel_box(p, (0, 0, .05), (hx, hy, .05), CONCRETE_DARK, ENAMEL, .01)
    grime(p, 0, .2, 1.4, 817)
    finish(p)
    return p


def glider():
    """SM_ON_Glider: the two-seat glider Tam and Jory built, 15 m wingspan (y), 7.6 m long (x, its nose +x): a slim
    painted fuselage with a canopy, high wings with yellow tips, a T-tail, resting on its skid with one wingtip down."""
    p = Part('SM_ON_Glider', (ENAMEL, CRYSTAL, ALLOY))
    rng = _rng(818)
    pts = [(3.8, 0, .9), (3.2, 0, .98), (2.0, 0, 1.05), (.5, 0, 1.08), (-1.0, 0, 1.02), (-2.6, 0, 1.0), (-3.8, 0, 1.1)]
    tube(p, pts, [.12, .34, .42, .4, .3, .18, .1], PAINT_WHITE, ENAMEL, 14)
    blob(p, (1.7, 0, 1.38), (.95, .32, .26), GLASS_COLD, CRYSTAL, 2, .02, 3)
    # Wings: tapered slabs with a little dihedral, the left (-y) one resting lower.
    for sy in (-1, 1):
        root, tip = np.array((.6, sy * .35, 1.45)), np.array((.3, sy * 7.5, 1.45 + .35 + (-.45 if sy < 0 else 0)))
        for k in range(8):
            a, b = root + (tip - root) * k / 8, root + (tip - root) * (k + 1) / 8
            chord = 1.25 - .65 * (k + .5) / 8
            colour = PAINT_YELLOW if k == 7 else PAINT_WHITE
            hexa(p, [a + (chord * .4, 0, -.05), a + (-chord * .6, 0, -.05), b + (chord * .4, 0, -.04), b + (-chord * .6, 0, -.04),
                     a + (chord * .4, 0, .06), a + (-chord * .6, 0, .05), b + (chord * .4, 0, .05), b + (-chord * .6, 0, .04)], colour, ENAMEL)
    # The T-tail.
    hexa(p, [(-3.3, -.05, 1.1), (-3.9, -.05, 1.15), (-3.3, .05, 1.1), (-3.9, .05, 1.15),
             (-3.7, -.04, 2.3), (-4.0, -.04, 2.3), (-3.7, .04, 2.3), (-4.0, .04, 2.3)], PAINT_WHITE, ENAMEL)
    bevel_box(p, (-3.85, 0, 2.32), (.3, 1.3, .03), PAINT_WHITE, ENAMEL, .01)
    bevel_box(p, (.8, 0, .55), (.5, .05, .1), STEEL_W, ALLOY, .02)
    finish(p)
    return p


def telegraph():
    """SM_ON_Telegraph: the Telegraph House on its rock, a granite hut 5 m by 4 m under slate, an open porch on its
    front (+x) with the operator's table and key, a mast of 9 m beside it with its insulators."""
    p = Part('SM_ON_Telegraph', (STONE, TILE, ENAMEL, CRYSTAL, WOOD, ALLOY, ELECTRUM))
    rng = _rng(819)
    s = len(p.v)
    hx, hy, eave = 2.5, 2.0, 3.0
    bevel_box(p, (0, 0, eave / 2), (hx, hy, eave / 2), WHITEWASH, STONE, .04)
    for sx in (-1, 1):
        gable(p, sx * hx, .3, hy, eave, 1.4, WHITEWASH, STONE)
    gable_roof(p, (0, 0, eave), 2 * hx, 2 * hy, 1.4, SLATE, TILE, .35, .14, 0.0, SLATE_PALE, TILE)
    bevel_box(p, (hx + .03, -.9, 1.0), (.05, .45, 1.0), PAINT_GREEN, ENAMEL, .012)
    wall_windows(p, rng, hx, (.8,), 1.5, .8, .9, 1.0, 'x')
    # The porch: a lean-to roof on two posts, the table and the key under it.
    for sy in (-1, 1):
        bevel_box(p, (hx + 2.2, sy * 1.7, 1.2), (.08, .08, 1.2), TIMBER, WOOD, .01)
    p.add(np.array([(hx, -2.0, 2.7), (hx, 2.0, 2.7), (hx + 2.5, 2.0, 2.35), (hx + 2.5, -2.0, 2.35)]), [[0, 3, 2, 1], [1, 2, 3, 0]], SLATE, TILE, False)
    bevel_box(p, (hx + 1.0, .9, .75), (.45, .8, .03), TIMBER, WOOD, .01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(p, (hx + 1.0 + sx * .38, .9 + sy * .72, .37), (.03, .03, .37), TIMBER, WOOD, .005)
    bevel_box(p, (hx + 1.0, .7, .8), (.08, .05, .02), BRASS_DULL, ELECTRUM, .004)
    tube(p, [(hx + 1.0, .66, .83), (hx + 1.06, .66, .86)], .006, BRASS_DULL, ELECTRUM, 6)
    bevel_box(p, (hx + .8, 1.35, .86), (.14, .18, .1), STEEL_W, ALLOY, .01)
    # The mast.
    tube(p, [(-hx - .8, hy + .6, 0), (-hx - .8, hy + .6, 9.0)], [.12, .08], TIMBER, WOOD, 8)
    for z in (7.6, 8.4):
        bevel_box(p, (-hx - .8, hy + .6, z), (.06, .7, .05), TIMBER, WOOD, .01)
        for sy in (-1, 1):
            cylinder(p, (-hx - .8, hy + .6 + sy * .6, z + .04), .04, .12, GLASS_COLD, CRYSTAL, 8)
    weather(p, s, 819, .2, 1.6)
    finish(p)
    return p


def dam(k):
    """SM_ON_Dam<k>: a section of the dam's crest, 24 m along the dam (y) and 16 m across (x, the reservoir on +x):
    the roadway's slab, a concrete parapet with its coping on the upstream side, a kerb wall and lamp posts on the
    downstream side, and the upstream face going down 16 m into the reservoir. Variant 1 leaves the kerb open in the
    middle for the Dam Stair. Pivot: the roadway's top at the middle of the section (z 0)."""
    p = Part('SM_ON_Dam%d' % k, (ROCK, STONE, ALLOY, GLOW))
    rng = _rng(820 + k)
    bevel_box(p, (0, 0, -.3), (8.0, 12.0, .3), CONCRETE_JUST, ROCK, .03)
    for y in np.linspace(-12.0, 12.0, 7)[:-1]:     # expansion joints
        bevel_box(p, (0, y + 2.0, .005), (8.0, .03, .01), CONCRETE_DARK, ROCK, .002)
    # Upstream: the parapet, and the face down into the water.
    bevel_box(p, (7.5, 0, .65), (.4, 12.0, .65), CONCRETE_JUST, ROCK, .04)
    bevel_box(p, (7.5, 0, 1.36), (.5, 12.0, .08), GRANITE, STONE, .02)
    bevel_box(p, (8.2, 0, -8.0), (.3, 12.0, 8.0), CONCRETE_DARK, ROCK, .05)
    # Downstream: a kerb wall (gapped for the stair on variant 1) and lamps.
    for y0, y1 in (((-12.0, -6.5), (6.5, 12.0)) if k == 1 else ((-12.0, 12.0),)):
        bevel_box(p, (-7.7, (y0 + y1) / 2, .3), (.3, (y1 - y0) / 2, .3), CONCRETE_JUST, ROCK, .03)
        bevel_box(p, (-7.7, (y0 + y1) / 2, .64), (.36, (y1 - y0) / 2, .05), GRANITE, STONE, .01)
    for y in (-6.0, 6.0):
        tube(p, [(-7.4, y, .6), (-7.4, y, 4.2), (-6.9, y, 4.5)], .07, STEEL_W, ALLOY, 8)
        bevel_box(p, (-6.75, y, 4.4), (.22, .14, .1), STEEL_W, ALLOY, .02)
        blob(p, (-6.75, y, 4.27), (.14, .1, .05), GLOW_JUST, GLOW, 1, .02, 2)
    grime(p, 0, .25, 2.0, 820 + k)
    return p


def hold():
    """SM_ON_Hold: the Hold, the Just's depot let into the dam: an intake tower of poured concrete 14 m square and
    24 m high on the crest, olive-painted steel doors 4 m wide on its front (+x) under a canopy, amber lamps, a frosted
    grille, vents in its flanks breathing the Lull's magenta, and a railing round its roof. Box collision."""
    p = Part('SM_ON_Hold', (ROCK, ALLOY, ENAMEL, GLOW, STONE))
    rng = _rng(830)
    s = len(p.v)
    h = 24.0
    bevel_box(p, (0, 0, h / 2), (7.0, 7.0, h / 2), CONCRETE_JUST, ROCK, .08)
    for z in (6.0, 12.0, 18.0):
        bevel_box(p, (0, 0, z), (7.08, 7.08, .12), CONCRETE_DARK, ROCK, .02)
    bevel_box(p, (0, 0, h + .15), (7.3, 7.3, .15), GRANITE, STONE, .03)
    # The doors and their frame, the canopy, the lamps.
    bevel_box(p, (7.04, 0, 2.5), (.08, 2.4, 2.5), STEEL_W, ALLOY, .03)
    for sy in (-1, 1):
        bevel_box(p, (7.1, sy * 1.0, 2.3), (.06, .95, 2.25), PAINT_OLIVE, ENAMEL, .02)
        for z in (1.0, 2.3, 3.6):
            bevel_box(p, (7.17, sy * 1.0, z), (.02, .9, .06), STEEL_W, ALLOY, .01)
    bevel_box(p, (8.2, 0, 5.3), (1.2, 3.0, .15), CONCRETE_JUST, ROCK, .03)
    for sy in (-1, 1):
        bevel_box(p, (7.3, sy * 2.9, 4.2), (.2, .15, .22), STEEL_W, ALLOY, .02)
        blob(p, (7.48, sy * 2.9, 4.2), (.05, .12, .14), GLOW_JUST, GLOW, 1, .02, sy + 4)
    # Vents in the flanks, the Lull breathing magenta behind their slats.
    for sy in (-1, 1):
        for z in (9.0, 15.0):
            for x in (-3.0, 3.0):
                bevel_box(p, (x, sy * 7.02, z), (1.2, .06, .9), GLOW_RIME, GLOW, .01)
                for k in range(5):
                    bevel_box(p, (x, sy * 7.1, z - .7 + k * .35), (1.25, .05, .05), STEEL_W, ALLOY, .01)
    # The roof's railing and a mast.
    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if sx:
            bevel_box(p, (sx * 7.1, 0, h + 1.3), (.03, 7.1, .03), STEEL_W, ALLOY, .01)
        else:
            bevel_box(p, (0, sy * 7.1, h + 1.3), (7.1, .03, .03), STEEL_W, ALLOY, .01)
    tube(p, [(-4.0, -4.0, h), (-4.0, -4.0, h + 7.0)], [.12, .05], STEEL_W, ALLOY, 8)
    blob(p, (-4.0, -4.0, h + 7.1), .12, GLOW_JUST, GLOW, 1, .02, 9)
    weather(p, s, 830, .25, 4.0)
    finish(p)
    return p


def stair_flight():
    """SM_ON_Stair: one flight of the Dam Stair, granite steps 10 m wide climbing 15 steps of 0.30 by 0.69 m along +x
    (10.35 m run, 4.49 m rise: the embankment's slope), on a footing that sinks into the slope, with handrail posts.
    Pivot: the bottom front edge's middle (z 0), so flights chain end to end."""
    p = Part('SM_ON_Stair', (STONE, ALLOY))
    rng = _rng(831)
    run, rise, n = .69, .2993, 15
    for i in range(n):
        top = rise * (i + 1)
        bevel_box(p, (run * (i + .5), 0, top - .6), (run / 2, 5.0, .6), vary(rng, GRANITE, .06), STONE, .02)
    for sy in (-1, 1):
        for i in range(0, n, 5):
            x = run * (i + .5)
            tube(p, [(x, sy * 4.8, rise * (i + 1)), (x, sy * 4.8, rise * (i + 1) + 1.0)], .03, STEEL_W, ALLOY, 6)
        tube(p, [(0, sy * 4.8, 1.0 + rise), (run * n, sy * 4.8, 1.0 + rise * (n + 1))], .025, STEEL_W, ALLOY, 6)
    return p


def ice_house():
    """SM_ON_IceHouse: the Hold's old ice house, a granite vault half let into the slope, 9 m long (x), 7 m wide, a
    turfed barrel roof, its door on the front (+x) between two buttresses."""
    p = Part('SM_ON_IceHouse', (STONE, ENAMEL, LICHEN))
    rng = _rng(832)
    s = len(p.v)
    bevel_box(p, (0, 0, 1.2), (4.5, 3.5, 1.2), GRANITE, STONE, .05)
    for k in range(12):
        a0, a1 = math.pi * k / 12, math.pi * (k + 1) / 12
        pts = []
        for r_bit in (0, 1):
            for a_bit in (0, 1):
                for x_bit in (0, 1):
                    a = a0 if a_bit == 0 else a1
                    r = 3.5 if r_bit == 0 else 3.9
                    pts.append((-4.5 if x_bit == 0 else 4.5, -math.cos(a) * r, 2.4 + math.sin(a) * r * .55))
        hexa(p, pts, GRANITE_SHADE if r_bit else GRANITE, STONE)
    blob(p, (0, 0, 3.4), (4.6, 4.0, 1.4), vary(rng, FROST, .05), LICHEN, 2, .1, 7)
    for sy in (-1, 1):
        bevel_box(p, (4.6, sy * 1.5, 1.4), (.35, .3, 1.4), GRANITE_SHADE, STONE, .03)
    bevel_box(p, (4.53, 0, 1.0), (.05, .7, 1.0), PAINT_OLIVE, ENAMEL, .015)
    weather(p, s, 832, .22, 1.6)
    finish(p)
    return p


def ice_disc():
    """SM_ON_IceDisc: a unit disc of ice, 1 m in radius and 0.12 m thick (scaled over the millpond). Its top is z 0,
    so it is placed at the ice's height."""
    p = Part('SM_ON_IceDisc', (CRYSTAL,))
    cylinder(p, (0, 0, -.12), 1.0, .12, ICE, CRYSTAL, 48)
    return p


def satchel():
    """SM_ON_Satchel: Pilgrim's courier satchel, canvas with a brass-buckled flap, 0.4 m wide. 'centre' pivot."""
    p = Part('SM_ON_Satchel', (CLOTH, ELECTRUM))
    bevel_box(p, (0, 0, 0), (.08, .2, .15), CANVAS_W, CLOTH, .04)
    bevel_box(p, (.07, 0, .07), (.03, .2, .09), mix(CANVAS_W, WOOL_DARK, .3), CLOTH, .02)
    bevel_box(p, (.105, 0, .0), (.012, .03, .025), BRASS_DULL, ELECTRUM, .005)
    tube(p, [(0, -.19, .14), (0, -.1, .35), (0, .1, .35), (0, .19, .14)], .015, CANVAS_W, CLOTH, 6)
    centre(p)
    return p


def lantern():
    """SM_ON_Lantern: a hanging storm lantern for the Mill House and the Morning's rooms, 0.4 m tall: a brass frame
    round a glass chimney and its flame. Pivot at its hook (top)."""
    p = Part('SM_ON_Lantern', (ELECTRUM, CRYSTAL, GLOW))
    lathe(p, [(.11, -.36), (.12, -.33), (.06, -.3)], BRASS_DULL, ELECTRUM, 12)
    cylinder(p, (0, 0, -.3), .07, .18, GLASS_COLD, CRYSTAL, 12, .05)
    blob(p, (0, 0, -.22), (.02, .02, .045), GLOW_LAMP, GLOW, 1, .05, 3)
    lathe(p, [(.07, -.12), (.09, -.1), (.03, -.04), (.01, 0.0)], BRASS_DULL, ELECTRUM, 12)
    torus(p, (0, 0, .03), .03, .006, BRASS_DULL, ELECTRUM, 12, 4, 'x')
    return p


# ---------------------------------------------------------------- the Morning: rooms of what she lost

def kitchen():
    """SM_ON_Kitchen: the Holts' kitchen as Maren remembers it, 14 m by 12 m (larger than it was), 3.3 m to the
    ceiling: boarded floor, lime-washed walls with a window on the east (+y) wall, a dresser, the range, the table
    with three chairs (the fourth is Tam's, its own mesh), the letter on the table, a lamp; a doorway 1.8 m wide in
    the +x wall to the hall. Complex collision. Pivot: the floor's middle (z 0)."""
    p = Part('SM_ON_Kitchen', (WOOD, STONE, ENAMEL, ALLOY, CLOTH, GLOW))
    rng = _rng(840)
    hx, hy, h = 7.0, 6.0, 3.3
    for k in range(int(2 * hy / .24)):
        bevel_box(p, (0, -hy + .12 + k * .24, -.04), (hx, .115, .04), vary(rng, TIMBER, .12), WOOD, .004)
    bevel_box(p, (0, 0, -.3), (hx + .3, hy + .3, .22), GRANITE_SHADE, STONE, .02)
    bevel_box(p, (0, 0, h + .15), (hx + .3, hy + .3, .15), WHITEWASH, STONE, .02)
    for x in np.linspace(-hx + 1.0, hx - 1.0, 6):
        bevel_box(p, (x, 0, h - .1), (.12, hy, .1), TIMBER, WOOD, .02)
    wall = lambda c, half: bevel_box(p, c, half, WHITEWASH, STONE, .02)
    wall((-hx - .15, 0, h / 2), (.15, hy + .3, h / 2))
    wall((0, -hy - .15, h / 2), (hx, .15, h / 2))
    # The east wall with its window, 2.4 m wide, 1.5 m high, sill at 1.0.
    for y0, y1 in ((-hx, -1.2), (1.2, hx)):
        wall(((y0 + y1) / 2, hy + .15, h / 2), ((y1 - y0) / 2, .15, h / 2))
    wall((0, hy + .15, .5), (1.2, .15, .5))
    wall((0, hy + .15, h - .4), (1.2, .15, .4))
    window_frame(p, (0, hy + .02, 1.75), 2.4, 1.5, .2, PAINT_WHITE, ENAMEL, None, None, 90.0, 2, .05)
    # The +x wall with the doorway (1.8 m wide, 2.4 m high) to the hall.
    for y0, y1 in ((-hy - .3, -.9), (.9, hy + .3)):
        wall((hx + .15, (y0 + y1) / 2, h / 2), (.15, (y1 - y0) / 2, h / 2))
    wall((hx + .15, 0, 2.4 + (h - 2.4) / 2), (.15, .9, (h - 2.4) / 2))
    # The range against the west wall, the dresser against the south wall.
    bevel_box(p, (-hx + .55, -2.0, .45), (.5, 1.0, .45), STEEL_W, ALLOY, .03)
    bevel_box(p, (-hx + .55, -2.0, .93), (.55, 1.05, .03), mix(STEEL_W, SOOT, .5), ALLOY, .01)
    tube(p, [(-hx + .4, -2.4, .96), (-hx + .4, -2.4, h)], .1, STEEL_W, ALLOY, 10)
    bevel_box(p, (2.0, -hy + .3, .45), (1.3, .3, .45), PAINT_GREEN, ENAMEL, .02)
    bevel_box(p, (2.0, -hy + .2, 1.5), (1.3, .18, .6), PAINT_GREEN, ENAMEL, .02)
    for k in range(5):
        cylinder(p, (1.0 + k * .5, -hy + .28, 1.55), .17, .02, PAINT_WHITE, ENAMEL, 14)
    # The table, three chairs, the letter.
    bevel_box(p, (0, 0, .76), (1.1, .6, .04), TIMBER, WOOD, .01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(p, (sx * 1.0, sy * .5, .37), (.04, .04, .37), TIMBER, WOOD, .005)
    for cx, cy, yaw in ((-1.5, 0, 0.0), (0, -1.0, 90.0), (0, 1.0, -90.0)):
        merge(p, chair_part(rng), (cx, cy, 0), yaw)
    quad(p, (.2, .05, .802), (.45, .05, .802), (.45, .38, .802), (.2, .38, .802), PAINT_WHITE, CLOTH)
    quad(p, (.1, -.2, .801), (.32, -.12, .801), (.24, .12, .801), (.02, .04, .801), mix(PAINT_WHITE, WOOL, .3), CLOTH)
    # A lamp over the table.
    tube(p, [(0, 0, h), (0, 0, 2.4)], .01, STEEL_W, ALLOY, 4)
    lathe(p, [(.35, 2.28), (.3, 2.34), (.08, 2.42)], PAINT_WHITE, ENAMEL, 16)
    blob(p, (0, 0, 2.32), .07, GLOW_LAMP, GLOW, 1, .02, 4)
    return p


def chair_part(rng):
    """A ladder-back kitchen chair facing +x (its seat at 0.45 m), as a loose Part to merge."""
    q = Part('chair', (WOOD,))
    wood = vary(rng, TIMBER, .1)
    bevel_box(q, (0, 0, .45), (.22, .22, .025), wood, WOOD, .006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = .45 if sx > 0 else 1.0
            bevel_box(q, (sx * .19, sy * .19, h / 2), (.02, .02, h / 2), wood, WOOD, .004)
    for z in (.62, .78, .94):
        bevel_box(q, (-.19, 0, z), (.012, .19, .03), wood, WOOD, .004)
    return q


def chair():
    """SM_ON_Chair: Tam's chair at the kitchen table, the way he left it (pushed back, turned a little). The Morning's
    first memory. Front (+x)."""
    rng = _rng(841)
    p = Part('SM_ON_Chair', (WOOD,))
    merge(p, chair_part(rng))
    finish(p)
    return p


def hall_section(k):
    """SM_ON_Hall<k>: one 8 m length of the Long Hall (along x), 4.8 m wide and 3.4 m high: a runner on boarded
    floor, papered walls with a closed door on each side, a ceiling with a pendant lamp; open at both ends. Variant 1
    has, in its middle, his door: the frame with his heights marked on it, a child's coat on a hook. Complex
    collision. Pivot: the floor's middle (z 0)."""
    p = Part('SM_ON_Hall%d' % k, (WOOD, STONE, ENAMEL, CLOTH, ALLOY, GLOW))
    rng = _rng(842 + k)
    hx, hy, h = 4.0, 2.4, 3.4
    for j in range(int(2 * hy / .2)):
        bevel_box(p, (0, -hy + .1 + j * .2, -.04), (hx, .095, .04), vary(rng, TIMBER, .1), WOOD, .004)
    bevel_box(p, (0, 0, .003), (hx, .8, .003), mix(PAINT_RED, WOOL, .5), CLOTH, .001)
    bevel_box(p, (0, 0, -.3), (hx, hy + .3, .22), GRANITE_SHADE, STONE, .02)
    bevel_box(p, (0, 0, h + .15), (hx, hy + .3, .15), WHITEWASH, STONE, .02)
    paper = mix(PAINT_GREEN, WHITEWASH, .55)
    for sy in (-1, 1):
        bevel_box(p, (0, sy * (hy + .15), h / 2), (hx, .15, h / 2), paper, STONE, .02)
        bevel_box(p, (0, sy * (hy - .01), .12), (hx, .02, .12), TIMBER, WOOD, .005)
        dx = rng.uniform(-1.5, 1.5)
        bevel_box(p, (dx, sy * (hy - .02), 1.1), (.5, .04, 1.1), vary(rng, TIMBER, .1), ENAMEL, .01)
        bevel_box(p, (dx, sy * (hy - .01), 2.28), (.62, .05, .08), PAINT_WHITE, ENAMEL, .01)
        for s in (-1, 1):
            bevel_box(p, (dx + s * .56, sy * (hy - .01), 1.1), (.06, .05, 1.1), PAINT_WHITE, ENAMEL, .01)
        blob(p, (dx + .35, sy * (hy - .07), 1.05), .035, BRASS_DULL, ALLOY, 1, .02, 2)
    if k == 1:
        # His door, facing down the hall from the +y wall, its frame marked at his heights.
        for z in np.linspace(.85, 1.75, 7):
            bevel_box(p, (.62, hy - .08, z), (.05, .006, .004), SOOT, ENAMEL, .001)
        tube(p, [(-.9, hy - .05, 1.5), (-.9, hy - .2, 1.48)], .015, BRASS_DULL, ALLOY, 6)
        blob(p, (-.9, hy - .25, 1.1), (.18, .1, .42), mix(PAINT_BLUE, WOOL, .3), CLOTH, 1, .15, 5)
    tube(p, [(0, 0, h), (0, 0, 2.6)], .01, STEEL_W, ALLOY, 4)
    blob(p, (0, 0, 2.55), .09, GLOW_LAMP, GLOW, 1, .02, 4 + k)
    return p


def island():
    """SM_ON_Island: a piece of ground standing in the mist, 10 m in radius (scaled up where a room needs more): a
    flat top on a jagged underside of rock hanging 8 m down. The top is ground (the Grove ground shader's layer
    weights in its colour: mostly grass, some earth, so Morrow's frost lies on it as on the valley's). Complex
    collision. Pivot: its top's middle (z 0)."""
    p = Part('SM_ON_Island', (GROUND, ROCK))
    rng = _rng(850)
    n, rings = 48, 6
    verts, faces = [(0.0, 0.0, 0.0)], []
    for i in range(1, rings + 1):
        r = 10.0 * i / rings
        for j in range(n):
            a = j * math.tau / n
            wob = 1.0 + .04 * math.sin(a * 5 + 1.3) * (i / rings)
            verts.append((math.cos(a) * r * wob, math.sin(a) * r * wob, rng.uniform(-.04, .04) * (i < rings)))
    for j in range(n):
        faces.append([0, 1 + j, 1 + (j + 1) % n])
    for i in range(rings - 1):
        for j in range(n):
            a, b = 1 + i * n + j, 1 + i * n + (j + 1) % n
            faces.append([a, a + n, b + n, b])
    p.add(np.array(verts), faces, col(.75, .3, .08, 1.0), GROUND, True)
    # The underside: a ragged cone of rock.
    rim_ = [(math.cos(j * math.tau / n) * 10.0, math.sin(j * math.tau / n) * 10.0) for j in range(n)]
    layers_ = [(1.0, -.02), (1.0, -1.0), (.8, -2.5), (.55, -4.5), (.3, -6.5), (.05, -8.2)]
    verts, faces = [], []
    for li, (k_, z) in enumerate(layers_):
        for j, (x, y) in enumerate(rim_):
            jag = 1.0 if li < 2 else rng.uniform(.75, 1.2)
            verts.append((x * k_ * jag, y * k_ * jag, z + (rng.uniform(-.6, .6) if li > 1 else 0)))
    for li in range(len(layers_) - 1):
        for j in range(n):
            a, b = li * n + j, li * n + (j + 1) % n
            faces.append([a, a + n, b + n, b])
    p.add(np.array(verts), faces, ROCK_GREY, ROCK, False)
    return p


def walk():
    """SM_ON_Walk: a plank walkway 10 m long (x) and 2.4 m wide over the mist between the Morning's rooms, rope rails
    on posts. Pivot at the deck's top centre."""
    p = Part('SM_ON_Walk', (WOOD, CLOTH))
    rng = _rng(851)
    for k in range(25):
        bevel_box(p, (-5.0 + .2 + k * .4, 0, -.04), (.18, 1.2, .04), vary(rng, TIMBER_GREY, .12), WOOD, .006)
    for sy in (-1, 1):
        bevel_box(p, (0, sy * 1.0, -.16), (5.0, .1, .08), TIMBER, WOOD, .01)
        for x in np.linspace(-4.8, 4.8, 5):
            bevel_box(p, (x, sy * 1.12, .5), (.05, .05, .55), TIMBER, WOOD, .008)
        tube(p, [(x_, sy * 1.12, 1.0 - .06 * math.sin(math.pi * ((x_ + 4.8) % 2.4) / 2.4)) for x_ in np.linspace(-4.8, 4.8, 13)], .02, CANVAS_W,
             CLOTH, 6)
    return p


MESHES = [rime_wall, rime_mound, rime_door, chapel, mill, wheel, bench, bridge, school, hangar, glider, telegraph, dam, hold, stair_flight,
          ice_house, ice_disc, satchel, lantern, kitchen, chair, hall_section, island, walk]
VARIANTS = {dam: 2, hall_section: 2}
CONTRACT = {
    'SM_ON_RimeWall': {'size': (0, 12.0, 0), 'tol': .25},
    'SM_ON_Chapel': {'size': (9.5, 0, 0), 'tol': .2},
    'SM_ON_Wheel': {'pivot': 'centre'},
    'SM_ON_Bridge': {'size': (32.0, 5.6, 0), 'tol': .05, 'pivot': 'any'},
    'SM_ON_Dam0': {'size': (16.0, 24.0, 0), 'tol': .1, 'pivot': 'any'},
    'SM_ON_Dam1': {'size': (16.0, 24.0, 0), 'tol': .1, 'pivot': 'any'},
    'SM_ON_Hold': {'size': (0, 14.0, 0), 'tol': .15},
    'SM_ON_Stair': {'size': (10.35, 10.0, 0), 'tol': .05, 'pivot': 'any'},
    'SM_ON_IceDisc': {'size': (2.0, 2.0, .12), 'tol': .05, 'pivot': 'any'},
    'SM_ON_Satchel': {'pivot': 'centre'},
    'SM_ON_Lantern': {'pivot': 'any'},
    'SM_ON_Kitchen': {'pivot': 'any'},
    'SM_ON_Hall0': {'size': (8.0, 0, 0), 'tol': .05, 'pivot': 'any'},
    'SM_ON_Hall1': {'size': (8.0, 0, 0), 'tol': .05, 'pivot': 'any'},
    'SM_ON_Island': {'size': (20.0, 20.0, 0), 'tol': .1, 'pivot': 'any'},
    'SM_ON_Walk': {'size': (10.0, 0, 0), 'tol': .05, 'pivot': 'any'},
}
