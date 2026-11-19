"""Halcyon's figures: the Keel (the Tide Guard's command frame, the boss) and the echoes, people the town remembers
(level 6; Tools/halcyon/README.md is the contract).

The echoes are worn in the trace material in play (pale silver light), so they are modelled as plain figures in
one slot: a coat, hands, a face turned a little down, each by their trade's silhouette.
"""
from kit import *  # noqa: F401,F403


def keel():
    """The Keel: the Just's command frame grown into the Undertow. About 9 m long, 7 m tall and 5 m wide, it hovers:
    a deep blade of olive-painted plate like an upturned ship's keel, ribbed in steel, a great amber eye at its bow
    (+x), four arms of pipe ending in clamps, and four magenta conduits trailing from its stern to the pumps.
    'centre' pivot."""
    rng = np.random.default_rng(101)
    p = Part('SM_HE_Keel', (ENAMEL, ALLOY, GLOW, RED))
    s = len(p.v)
    # The blade: stations along x, each a pointed section deep below and broad above.
    xs = np.linspace(-4.5, 4.5, 15)
    rings = []
    for x in xs:
        t = x / 4.5
        width = 2.4 * (1 - abs(t) ** 2.4 * (.92 if t > 0 else .55))
        depth = 3.6 * (1 - abs(t) ** 2.0 * .7)
        ang = np.linspace(0, math.tau, 18, endpoint=False)
        ring = []
        for a in ang:
            cy, sz = math.sin(a), math.cos(a)
            z = sz * (depth if sz < 0 else 1.4) * (1 - .25 * abs(cy) if sz < 0 else 1)
            y = cy * width * (.35 + .65 * (1 + sz) / 2) if sz < 0 else cy * width
            ring.append((x, y, z))
        rings.append(ring)
    n = 18
    verts = np.array([pt for ring in rings for pt in ring])
    faces = [[i * n + (j + 1) % n, i * n + j, (i + 1) * n + j, (i + 1) * n + (j + 1) % n] for i in range(len(rings) - 1) for j in range(n)]
    faces.append(list(range(n))[::-1])
    faces.append([(len(rings) - 1) * n + j for j in range(n)])
    p.add(verts, faces, PAINT_OLIVE, ENAMEL, True)
    for x in np.linspace(-3.6, 3.6, 7):     # ribs
        t = x / 4.5
        torus(p, (x, 0, -.6), 2.45 * (1 - abs(t) ** 2.4 * .7), .08, STEEL_W, ALLOY, 32, 6, 'x')
    bevel_box(p, (0, 0, 1.5), (3.6, 1.6, .2), STEEL_W, ALLOY, .05)
    bevel_box(p, (-.5, 0, 2.0), (1.6, 1.0, .4), PAINT_OLIVE, ENAMEL, .05)
    # The eye at the bow, and a ring of red AL-style signal lamps along the deck.
    blob(p, (4.25, 0, .2), .7, GLOW_JUST, GLOW, 2, .02, 1, (.6, 1, 1))
    torus(p, (4.1, 0, .2), .8, .12, STEEL_W, ALLOY, 24, 6, 'x')
    for k in range(6):
        cylinder(p, (-3.0 + k * 1.2, 1.55 * (1 if k % 2 else -1), 1.7), .1, .12, PAINT_RED, RED, 8)
    # Arms: pipes from the shoulders bending down to clamps.
    for sx in (-1, 1):
        for sy in (-1, 1):
            a = np.array((sx * 2.2, sy * 2.0, .6))
            b = a + (sx * .8, sy * 1.6, -1.2)
            c = b + (sx * .6, sy * .3, -2.4)
            tube(p, [a, b, c], .22, STEEL_W, ALLOY, 8)
            bevel_box(p, tuple(c + (0, 0, -.3)), (.4, .25, .45), PAINT_OLIVE, ENAMEL, .04)
    # Conduits trailing from the stern, glowing magenta.
    for k in range(4):
        y, z = (-.8, .8)[k % 2], (-.4, .5)[k // 2]
        pts = [(-4.3, y, z), (-5.6, y * 1.6, z - .4), (-6.6, y * 2.2, z - 1.4)]
        tube(p, pts, .14, GLOW_FORCED, GLOW, 8)
    grime(p, s, .3, 1.2, 101)
    centre(p)
    return p


# Echoes: (name, height, coat length 0..1 of the height, hat: 'cap' | 'hood' | 'flat', bulk)
ECHOES = (('SM_HP_Echo0', 1.78, .62, 'cap', 1.0),     # the harbourmaster: a long coat and a peaked cap
          ('SM_HP_Echo1', 1.74, .4, 'flat', 1.1),     # the foreman: a short jacket, a flat cap, broad
          ('SM_HP_Echo2', 1.70, .7, 'hood', .95))     # the keeper: an oilskin to the shins, its hood up


def echo(k):
    """A person the town remembers, standing at rest and looking a little down: body, coat, arms, head and hat, 1.7
    to 1.8 m tall, facing +x. One slot: in play they wear the trace material."""
    name, height, coat, hat, bulk = ECHOES[k]
    p = Part(name, (CLOTH,))
    c = col(.6, .6, .6)
    sh = height * .82    # shoulder height
    hip = height * .52
    # Legs below the coat.
    hem = sh - (sh - .05) * coat - .05
    for sy in (-1, 1):
        tube(p, [(0, sy * .1, 0.05), (0, sy * .1, hem + .1)], [.07 * bulk, .085 * bulk], c, CLOTH, 8)
        bevel_box(p, (.06, sy * .1, .05), (.13, .055, .05), c, CLOTH, .02)
    # The coat: a lathe from the hem to the shoulders, flaring at the hem.
    prof = [(.26 * bulk, hem), (.2 * bulk, hip), (.19 * bulk, hip + .15), (.21 * bulk, sh - .15), (.2 * bulk, sh - .02), (.08, sh + .04)]
    lathe(p, prof, c, CLOTH, 16, (0, 0, 0))
    v = np.asarray(p.v, np.float64)
    # Arms hanging, hands before the coat.
    for sy in (-1, 1):
        a = (0, sy * .22 * bulk, sh - .06)
        b = (.04, sy * .27 * bulk, hip + .12)
        h_ = (.12, sy * .2 * bulk, hip - .06)
        tube(p, [a, b, h_], [.07 * bulk, .06 * bulk, .05], c, CLOTH, 8)
        blob(p, h_, .055, c, CLOTH, 1, .05, sy + 3, (1.2, .8, 1.3))
    # The head, turned a little down, and the neck.
    tube(p, [(0, 0, sh), (.01, 0, sh + .09)], .055, c, CLOTH, 8)
    blob(p, (.03, 0, sh + .2), .11, c, CLOTH, 2, .02, k, (1.1, .92, 1.15))
    if hat == 'cap':
        cylinder(p, (.02, 0, sh + .27), .12, .07, c, CLOTH, 14, .13)
        p.add(np.array([(.08, -.09, sh + .275), (.08, .09, sh + .275), (.2, .08, sh + .25), (.2, -.08, sh + .25)]), [[0, 1, 2, 3], [3, 2, 1, 0]], c, CLOTH, False)
    elif hat == 'flat':
        blob(p, (.05, 0, sh + .29), .13, c, CLOTH, 1, .05, 7, (1.25, 1.0, .35))
    else:
        lathe(p, [(.15, sh + .08), (.16, sh + .2), (.13, sh + .3), (.04, sh + .36)], c, CLOTH, 14, (-.02, 0, 0), True, math.tau * .78, math.pi * .61)
    finish(p)
    return p


MESHES = [keel, echo]
VARIANTS = {echo: len(ECHOES)}
CONTRACT = {'SM_HE_Keel': {'pivot': 'centre'}}
