"""Structures of Hesper (level 7, Arche): the SM_SN_ meshes of the table "Meshes" in Tools/hesper/README.md, and the
Cantor (SM_SE_). Everything else Hesper stands on is Kathodos's (SM_AN_, SM_AV_, SM_AP_: Tools/arche_meshes).

Pure numpy through kit and Arche's masonry helpers (Tools/arche_meshes/structures.py, loaded by its path: course, gbox,
loft, gquad, column12, lamp, inlay, weather, done...). Metres, Unreal axes (x forward, y right, z up). Names, sizes and
pivots are the README's table; CONTRACT at the end repeats them for check.py.

Unison is drawn by its material (M_HS_Unison, which the scenario puts on every slot), so its meshes are only the
shape of the standing wave: thin wavering sheets, two-sided in the material, and the import gives them box collision.
"""
import importlib.util as _util

from kit import *  # noqa: F401,F403

_spec = _util.spec_from_file_location('physis_arche_structures', ROOT / 'Tools/arche_meshes/structures.py')
_ast = _util.module_from_spec(_spec)
_spec.loader.exec_module(_ast)
for _name in ('arr', 'unit', 'rot', 'cells', 'rgb', 'k_of', 'place', 'warp', 'batter', 'tint', 'recolour', 'gquad', 'face', 'fan', 'gbox', 'bar',
              'loft', 'ngon', 'turn', 'gem', 'lamp', 'course', 'weather', 'done', 'inlay', 'column12', 'FACTS'):
    globals()[_name] = getattr(_ast, _name)
X, Y, Z = np.eye(3)
_BUILDERS, _SIZES, _VARIANTS = [], {}, {}


def mesh(name, size, variants=0, **spec):
    def wrap(fn):
        _BUILDERS.append(fn)
        if variants:
            _VARIANTS[fn] = variants
            for k in range(variants):
                _SIZES['%s%d' % (name, k)] = dict(size=size, **spec)
        else:
            _SIZES[name] = dict(size=size, **spec)
        return fn
    return wrap


def sheet(p, y0, y1, z0, z1, x, amp, waves, slot, colour, nu=24, nv=12, phase=0.0):
    """A vertical sheet at depth x from (y0, z0) to (y1, z1), rippled along x by amp in `waves` standing waves along y
    and a slower sway up z: the shape of a standing tone."""
    ys, zs = np.linspace(y0, y1, nu + 1), np.linspace(z0, z1, nv + 1)
    gy, gz = np.meshgrid(ys, zs, indexing='ij')
    u = (gy - y0) / max(y1 - y0, 1e-6)
    w = (gz - z0) / max(z1 - z0, 1e-6)
    gx = x + amp * np.sin(TAU * waves * u + phase) * (.6 + .4 * np.cos(TAU * w * .8 + phase)) * np.sin(math.pi * np.clip(u * 1.02, 0, 1)) ** .3
    pts = np.stack([gx, gy, gz], -1).reshape(-1, 3)
    n = nv + 1
    faces = [[i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1] for i in range(nu) for j in range(nv)]
    return p.add(pts, faces, colour, slot, True)


# ---------------------------------------------------------------- Unison

@mesh('SM_SN_Unison', (6.0, 12.0, 12.0), tol=.08)
def unison():
    """A panel of the Choir Wall: five standing sheets of tone across its 6 m thickness, each 12 m wide and 12 m tall,
    rippling against each other, with a fringe of short sheets along the foot. Base pivot."""
    p = Part('SM_SN_Unison', (GLOW,))
    for k, x in enumerate(np.linspace(-2.6, 2.6, 5)):
        sheet(p, -6.0, 6.0, 0.0, 12.0 - .4 * (k % 2), x, .28, 2.0 + .5 * k, GLOW, GLOW_UNISON, 28, 14, phase=k * 1.3)
    for x in (-3.0, 3.0):        # the faces: two flat sheets, so the panel reads as a solid block from any side
        sheet(p, -6.0, 6.0, 0.0, 11.6, x, .0, 1.0, GLOW, k_of(GLOW_UNISON, .7), 12, 6)
    return done(p, 7301, pivot='base')


@mesh('SM_SN_Shell', (7.0, 7.0, 8.0), tol=.08)
def shell():
    """A shell of Unison round a thing it silences: sixteen ribbons climbing from a ring 3.5 m across the ground to a
    crown 8 m up, and three rings of tone round them. Base pivot."""
    p = Part('SM_SN_Shell', (GLOW,))
    for j in range(16):
        a0 = TAU * j / 16
        pts, widths = [], []
        for t in np.linspace(0, 1, 14):
            r = 3.5 * math.sin(math.pi * (.08 + .84 * (1 - t) ** .8)) + .25
            a = a0 + .5 * t
            pts.append((r * math.cos(a), r * math.sin(a), 8.0 * t))
        pts = arr(pts)
        ring = []
        for q in range(len(pts)):
            d = unit(pts[min(q + 1, len(pts) - 1)] - pts[max(q - 1, 0)])
            side = unit(np.cross(d, unit(arr((pts[q][0], pts[q][1], 0.0)) + 1e-9)))
            ring.append((pts[q] - side * .32, pts[q] + side * .32))
        verts = np.array([v for pair in ring for v in pair])
        faces = [[2 * q, 2 * q + 2, 2 * q + 3, 2 * q + 1] for q in range(len(ring) - 1)]
        p.add(verts, faces, GLOW_UNISON, GLOW, True)
    for z, r in ((1.2, 3.55), (3.6, 3.2), (6.0, 2.1)):
        a = np.linspace(0, TAU, 33)
        lo = np.stack([np.cos(a) * r, np.sin(a) * r, np.full(33, z - .18)], 1)
        hi = np.stack([np.cos(a) * r, np.sin(a) * r, np.full(33, z + .18)], 1)
        faces = [[q, q + 1, 34 + q, 33 + q] for q in range(32)]
        p.add(np.concatenate([lo, hi]), faces, k_of(GLOW_UNISON, .8), GLOW, True)
    centre(p, False)
    v = arr(p.v)
    v[:, 2] -= v[:, 2].min()
    p.v = v.tolist()
    return done(p, 7302, pivot='base')


# ---------------------------------------------------------------- the bells

@mesh('SM_SN_Bell', (5.2, 5.2, 7.4), tol=.04)
def bell():
    """One of Hesper's three great bells, in its stone frame: a stepped plinth 5.2 m square, four battered piers, a
    lintel of long blocks with a line of inlay, and the bell hung from an alloy yoke, its lip 1.6 m from the plinth.
    Bronze bell (ALLOY), glazed amber band at its shoulder."""
    rng = np.random.default_rng(7310)
    p = Part('SM_SN_Bell', (STONE, ALLOY, ELECTRUM, TILE))
    gbox(p, (-2.6, -2.6, 0), (2.6, 2.6, .35), STONE, STONE_HONEY, .6, .04, 'z')
    gbox(p, (-2.2, -2.2, .35), (2.2, 2.2, .6), STONE, vary(rng, STONE_HONEY, .04), .5, .04, 'z')
    for sx in (-1, 1):
        for sy in (-1, 1):
            s = gbox(p, (sx * 1.85 - .32, sy * 1.85 - .32, .6), (sx * 1.85 + .32, sy * 1.85 + .32, 6.6), STONE, vary(rng, STONE_HONEY, .05), .5, .035)
            batter(p, s, .012, 0, sx * 1.85, .6)
    for sx in (-1, 1):
        gbox(p, (sx * 1.85 - .4, -2.3, 6.6), (sx * 1.85 + .4, 2.3, 7.05), STONE, vary(rng, STONE_HONEY, .04), .5, .04)
    gbox(p, (-2.3, -.45, 7.0), (2.3, .45, 7.4), STONE, STONE_HONEY, .5, .04)
    for sgn in (-1, 1):
        inlay(p, (sgn * .45, -2.1, 7.2), (sgn * .45, 2.1, 7.2), .04, .006, Y * sgn)
    bar(p, (0, 0, 7.0), (0, 0, 6.2), .3, .3, ALLOY, BRONZE_DARK)
    bar(p, (-1.5, 0, 6.6), (1.5, 0, 6.6), .22, .26, ALLOY, BRONZE_DARK)
    profile = [(.05, 6.2), (.75, 6.15), (1.05, 5.95), (1.18, 5.5), (1.25, 4.6), (1.42, 3.6), (1.72, 2.6), (1.95, 2.0), (2.0, 1.8), (1.86, 1.62)]
    lathe(p, profile, BRONZE, ALLOY, 32, (0, 0, 0), True)
    lathe(p, [(1.80, 1.66), (1.6, 1.9), (1.15, 2.6), (.9, 3.6), (.85, 4.6), (.7, 5.6), (.05, 5.75)], BRONZE_DARK, ALLOY, 32, (0, 0, 0), True)
    lathe(p, [(1.27, 5.0), (1.3, 5.2), (1.29, 5.42), (1.25, 5.48)], GLAZE_AMBER, TILE, 32, (0, 0, 0), True)
    lathe(p, [(1.74, 2.55), (1.78, 2.62), (1.77, 2.7), (1.72, 2.72)], ELECTRUM_PALE, ELECTRUM, 32, (0, 0, 0), True)
    return done(p, 7310, reach=1.6, facts=dict(lip=1.62))


@mesh('SM_SN_Fork', (.09, .41, 1.1), tol=.12, pivot='centre')
def fork():
    """Tavor's tuning fork, a hand tool a metre long: a stem with an electrum collar and two long tines."""
    p = Part('SM_SN_Fork', (ALLOY, ELECTRUM))
    tube(p, [(0, 0, -.55), (0, 0, -.05)], [.03, .03], BRONZE, ALLOY, 8)
    tube(p, [(0, 0, -.1), (0, 0, -.02)], [.045, .045], ELECTRUM_PALE, ELECTRUM, 8)
    for s in (-1, 1):
        pts = [(0, s * .03, -.04), (0, s * .14, .06), (0, s * .18, .2), (0, s * .18, .55)]
        tube(p, pts, [.025, .025, .025, .022], BRONZE, ALLOY, 8)
    return done(p, 7311, pivot='centre')


@mesh('SM_SN_Flute', (.9, .07, .06), tol=.2, pivot='centre')
def flute():
    """Anwe's reed flute: a reed tube with five stops and electrum bands."""
    p = Part('SM_SN_Flute', (CLOTH, ELECTRUM))
    tube(p, [(-.45, 0, 0), (.45, 0, 0)], [.03, .028], REED, CLOTH, 10)
    for x in (-.4, -.1, .25, .42):
        tube(p, [(x - .02, 0, 0), (x + .02, 0, 0)], [.034, .034], ELECTRUM_PALE, ELECTRUM, 10)
    return done(p, 7312, pivot='centre')


# ---------------------------------------------------------------- the western edge

@mesh('SM_SN_Parapet', (.7, 12.0, 1.15), tol=.04)
def parapet():
    """The edge's parapet: a 12 m run of low wall in long dressed blocks with a coped top 1.15 m high, battered on its
    outer face (+x is the side toward the drop is -x? no: it stands along y; either face may face the drop)."""
    rng = np.random.default_rng(7320)
    p = Part('SM_SN_Parapet', (STONE, ELECTRUM))
    y = -6.0
    while y < 5.99:
        w = min(rng.uniform(1.6, 2.6), 6.0 - y)
        gbox(p, (-.3, y + .01, 0), (.3, y + w - .01, .92), STONE, vary(rng, STONE_HONEY, .06), .4, .03, 'z')
        y += w
    gbox(p, (-.35, -6.0, .92), (.35, 6.0, 1.15), STONE, STONE_HONEY, .5, .05)
    inlay(p, (.35, -5.8, 1.03), (.35, 5.8, 1.03), .03, .005, X)
    return done(p, 7320, reach=.6)


# ---------------------------------------------------------------- the Concord

@mesh('SM_SN_Pylon', (2.4, 2.4, 7.2), tol=.05)
def pylon():
    """A tuning pylon of the Concord: a stepped stone foot, a bronze stem and two tall tines 1.2 m apart with the
    amber of the tone standing between them. The Cantor's shield answers to four of them."""
    rng = np.random.default_rng(7330)
    p = Part('SM_SN_Pylon', (STONE, ALLOY, ELECTRUM, GLOW))
    gbox(p, (-1.2, -1.2, 0), (1.2, 1.2, .4), STONE, STONE_HONEY, .5, .04, 'z')
    gbox(p, (-.85, -.85, .4), (.85, .85, 1.2), STONE, vary(rng, STONE_HONEY, .04), .4, .04)
    lathe(p, [(.32, 1.2), (.3, 1.4), (.22, 1.5), (.2, 2.6), (.3, 2.75), (.34, 2.9), (.05, 2.95)], BRONZE, ALLOY, 16)
    for s in (-1, 1):
        pts = [(0, s * .15, 2.85), (0, s * .55, 3.2), (0, s * .62, 3.8), (0, s * .6, 7.0)]
        tube(p, pts, [.16, .15, .14, .12], BRONZE, ALLOY, 12)
        tube(p, [(0, s * .6, 4.6), (0, s * .6, 4.8)], [.17, .17], ELECTRUM_PALE, ELECTRUM, 12)
    sheet(p, -.46, .46, 3.4, 6.8, 0.0, .06, 3.0, GLOW, GLOW_UNISON, 8, 10)
    sheet(p, .46, -.46, 3.4, 6.8, 0.0, .06, 3.0, GLOW, GLOW_UNISON, 8, 10)
    return done(p, 7330, reach=1.0)


@mesh('SM_SN_Concord', (26.0, 26.0, 30.7), tol=.06)
def concord():
    """The Concord: a round stone drum 26 m across and 5 m high in long courses, stepped twice; on it a ring of twelve
    bronze pipes rising from 14 to 31 m, longest at the back (+x... the horn's mouth faces -x, toward the gate); in the
    middle the horn, a bronze bell-mouth 9 m across leaning toward the court, amber light deep in its throat; one band
    of electrum round the drum."""
    rng = np.random.default_rng(7340)
    p = Part('SM_SN_Concord', (STONE, ALLOY, ELECTRUM, GLOW, TILE))
    for z0, z1, r in ((0.0, 2.2, 13.0), (2.2, 3.8, 11.8), (3.8, 5.0, 10.8)):
        a = np.linspace(0, TAU, 49)[:-1]
        rings = [np.stack([np.cos(a) * r, np.sin(a) * r, np.full(48, z)], 1) for z in (z0, z1)]
        loft(p, rings, STONE, [rgb(vary(rng, STONE_HONEY, .04)), rgb(vary(rng, STONE_HONEY, .04))], caps='t')
        for k in range(1, int((z1 - z0) / .55)):
            zz = z0 + k * .55
            lo = np.stack([np.cos(a) * (r + .015), np.sin(a) * (r + .015), np.full(48, zz - .02)], 1)
            hi = np.stack([np.cos(a) * (r + .015), np.sin(a) * (r + .015), np.full(48, zz + .02)], 1)
            loft(p, [lo, hi], STONE, rgb(STONE_DUSK))
    a = np.linspace(0, TAU, 49)[:-1]
    loft(p, [np.stack([np.cos(a) * 13.03, np.sin(a) * 13.03, np.full(48, 1.6)], 1), np.stack([np.cos(a) * 13.03, np.sin(a) * 13.03, np.full(48, 1.7)], 1)],
         ELECTRUM, rgb(ELECTRUM_PALE))
    for j in range(12):
        ang = math.pi + TAU * (j + .5) / 12      # j 0 starts beside the gate side
        back = .5 - .5 * math.cos(ang)            # 0 toward -x (the gate), 1 at the back (+x)
        h = 14.0 + 17.0 * back
        r = 8.6
        c = (math.cos(ang) * r, math.sin(ang) * r)
        lathe(p, [(.95, 5.0), (.9, 5.6), (.7, 5.8), (.72, h - .8), (.95, h - .4), (.95, h), (.6, h), (.6, h - .3), (.05, h - .3)], BRONZE, ALLOY, 16,
              (c[0], c[1], 0), True)
        lathe(p, [(.74, h * .55), (.78, h * .55 + .25), (.74, h * .55 + .5)], ELECTRUM_PALE, ELECTRUM, 16, (c[0], c[1], 0))
        lathe(p, [(.5, h - .32), (.02, h - .32)], GLOW_UNISON, GLOW, 12, (c[0], c[1], 0), False)
    # The horn: a bell-mouth turned about an axis leaning 30 degrees toward -x, its throat on the drum.
    s = len(p.v)
    lathe(p, [(1.2, 0.0), (1.3, 3.0), (1.8, 6.0), (2.8, 8.5), (4.5, 10.2), (4.7, 10.5)], BRONZE, ALLOY, 32, (0, 0, 0), True)
    lathe(p, [(4.4, 10.4), (2.6, 8.6), (1.6, 6.2), (1.05, 3.0), (.95, 1.0)], BRONZE_DARK, ALLOY, 32, (0, 0, 0), True)
    lathe(p, [(.95, 1.2), (.02, 1.4)], GLOW_UNISON, GLOW, 24, (0, 0, 0), False)
    lathe(p, [(4.71, 10.2), (4.74, 10.35), (4.71, 10.5)], ELECTRUM_PALE, ELECTRUM, 32, (0, 0, 0))
    place(p, s, rot('y', -30), (1.5, 0.0, 4.9))
    a = np.linspace(0, TAU, 25)[:-1]
    for k in range(24):           # glazed amber tiles set in the drum's top step
        ca, sa = math.cos(a[k]), math.sin(a[k])
        gquad(p, (ca * 10.2 - sa * .5, sa * 10.2 + ca * .5, 5.005), (ca * 10.2 + sa * .5, sa * 10.2 - ca * .5, 5.005),
              (ca * 10.7 + sa * .5, sa * 10.7 - ca * .5, 5.005), (ca * 10.7 - sa * .5, sa * 10.7 + ca * .5, 5.005), TILE, GLAZE_AMBER)
    return done(p, 7340, reach=2.5, facts=dict(top=5.0))


@mesh('SM_SN_Spire', (11.0, 11.0, 48.0), tol=.06)
def spire():
    """The Watch Spire: a square tower 9 m on a side, battered, in long courses, with tall pointed slits on every face;
    a bell-chamber of four open arches at 36 m; a pointed stone cap and a crystal finial to 48 m."""
    rng = np.random.default_rng(7350)
    p = Part('SM_SN_Spire', (STONE, ALLOY, ELECTRUM, CRYSTAL, GLOW))
    gbox(p, (-5.5, -5.5, 0), (5.5, 5.5, 1.2), STONE, STONE_HONEY, 1.0, .05, 'z')
    s = gbox(p, (-4.5, -4.5, 1.2), (4.5, 4.5, 34.0), STONE, vary(rng, STONE_HONEY, .03), 1.2, .05)
    batter(p, s, .004, 0, 0, 1.2)
    batter(p, s, .004, 1, 0, 1.2)
    for z0 in np.arange(1.2, 34.0, .9):
        for sgn in (-1, 1):
            for axis in (0, 1):
                hw = 4.52 * (1 - .004 * (z0 - 1.2))
                if axis == 0:
                    gquad(p, (sgn * hw, -hw * sgn, z0 - .02), (sgn * hw, hw * sgn, z0 - .02), (sgn * hw, hw * sgn, z0 + .02), (sgn * hw, -hw * sgn, z0 + .02),
                          STONE, k_of(STONE_DUSK, 1.0))
                else:
                    gquad(p, (hw * sgn, sgn * hw, z0 - .02), (-hw * sgn, sgn * hw, z0 - .02), (-hw * sgn, sgn * hw, z0 + .02), (hw * sgn, sgn * hw, z0 + .02),
                          STONE, k_of(STONE_DUSK, 1.0))
    for z in (8.0, 16.0, 24.0):           # tall slits: dark recessed panels with a crystal pane
        for sgn in (-1, 1):
            for axis in (0, 1):
                hw = 4.53 * (1 - .004 * (z - 1.2))
                if axis == 0:
                    gquad(p, (sgn * hw, -.35 * sgn, z), (sgn * hw, .35 * sgn, z), (sgn * hw, .35 * sgn, z + 3.2), (sgn * hw, -.35 * sgn, z + 3.2), CRYSTAL, CRYSTAL_ICE)
                else:
                    gquad(p, (.35 * sgn, sgn * hw, z), (-.35 * sgn, sgn * hw, z), (-.35 * sgn, sgn * hw, z + 3.2), (.35 * sgn, sgn * hw, z + 3.2), CRYSTAL, CRYSTAL_ICE)
    # The bell-chamber: four corner piers and lintels, open between them.
    for sx in (-1, 1):
        for sy in (-1, 1):
            gbox(p, (sx * 4.1 - .55, sy * 4.1 - .55, 34.0), (sx * 4.1 + .55, sy * 4.1 + .55, 39.5), STONE, vary(rng, STONE_HONEY, .04), .6, .04)
    gbox(p, (-4.3, -4.3, 33.6), (4.3, 4.3, 34.0), STONE, STONE_HONEY, 1.0, .04)
    gbox(p, (-4.7, -4.7, 39.5), (4.7, 4.7, 40.4), STONE, STONE_HONEY, 1.0, .05)
    for sgn in (-1, 1):
        inlay(p, (sgn * 4.7, -4.5, 39.95), (sgn * 4.7, 4.5, 39.95), .05, .006, X * sgn)
        inlay(p, (-4.5, sgn * 4.7, 39.95), (4.5, sgn * 4.7, 39.95), .05, .006, Y * sgn)
    lathe(p, [(1.6, 35.0), (1.7, 36.6), (1.35, 37.6), (.2, 38.0)], BRONZE, ALLOY, 24)
    fan(p, (0, 0, 46.6), arr([(4.4, -4.4, 40.4), (4.4, 4.4, 40.4), (-4.4, 4.4, 40.4), (-4.4, -4.4, 40.4)]), STONE, STONE_HONEY, Z, STONE_ROSE)
    gem(p, (0, 0, 47.2), .35, .8, CRYSTAL, CRYSTAL_CLEAR, sides=6)
    lamp(p, (0, 0, 36.2), .3, .6, GLOW_SERENE, band=.3)
    return done(p, 7350, reach=3.0)


# ---------------------------------------------------------------- the Cantor

@mesh('SM_SE_Cantor', (8.9, 11.0, 7.0), tol=.08, pivot='centre')
def cantor():
    """The Cantor, the Concord's own voice and its keeper: a ring of nine bronze pipes 10 m across, open to the front
    (+x); in it a long masked core of pale enamel with one vertical seam of amber light (the First Ones' face, made
    by the Vigil for a machine); plates of red enamel (the AL's) floating round the core; amber in every pipe's mouth.
    Centre pivot: it hovers."""
    rng = np.random.default_rng(7360)
    p = Part('SM_SE_Cantor', (ALLOY, ENAMEL, RED, GLOW, ELECTRUM))
    for j in range(9):
        ang = math.radians(50 + j * 260 / 8)          # open in front (+x)
        r = 4.8
        c = (math.cos(ang) * r, math.sin(ang) * r)
        h = 4.0 + 2.6 * math.sin(math.pi * j / 8)
        lathe(p, [(.42, -h / 2), (.48, -h / 2 + .2), (.36, -h / 2 + .4), (.36, h / 2 - .5), (.5, h / 2 - .2), (.5, h / 2), (.3, h / 2), (.02, h / 2 - .2)],
              BRONZE, ALLOY, 14, (c[0], c[1], 0))
        lathe(p, [(.29, h / 2 - .05), (.02, h / 2 - .15)], GLOW_UNISON, GLOW, 10, (c[0], c[1], 0), False)
        lathe(p, [(.38, 0), (.41, .15), (.38, .3)], ELECTRUM_PALE, ELECTRUM, 14, (c[0], c[1], 0))
    a = np.linspace(0, TAU, 41)[:-1]
    for z in (-1.6, 1.6):
        tube(p, [(math.cos(t) * 4.8, math.sin(t) * 4.8, z) for t in np.radians(np.linspace(50, 310, 30))], [.12] * 30, BRONZE_DARK, ALLOY, 8, cap=True)
    # The masked core: a long smooth head, its face toward +x with one seam of light.
    s = len(p.v)
    lathe(p, [(.02, -2.6), (.7, -2.4), (1.05, -1.6), (1.2, -.2), (1.12, 1.0), (.85, 2.0), (.4, 2.6), (.02, 2.75)], ENAMEL_WHITE, ENAMEL, 24, (0, 0, 0), True)
    warp(p, s, lambda v: v * arr([.8, 1.0, 1.0]))
    gquad(p, (.98, -.06, -1.4), (.98, .06, -1.4), (.92, .06, 1.6), (.92, -.06, 1.6), GLOW, GLOW_UNISON, 1, 8)
    for k in range(7):
        ang = TAU * k / 7 + rng.uniform(-.2, .2)
        c = arr((math.cos(ang) * 2.4, math.sin(ang) * 2.4, rng.uniform(-1.8, 1.8)))
        q = len(p.v)
        gbox(p, (-.06, -.6, -.45), (.06, .6, .45), RED, AL_RED, .3, .02)
        place(p, q, rot('z', math.degrees(ang)) @ rot('y', rng.uniform(-25, 25)), c)
    return done(p, 7360, pivot='centre')


MESHES = list(_BUILDERS)
VARIANTS = dict(_VARIANTS)
CONTRACT = dict(_SIZES)
