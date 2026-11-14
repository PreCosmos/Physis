# ---------------------------------------------------------------- prop registry

PROPS = {}


def prop(key, name, short, body, glow, bounds, voxel, tris, look, paint, scale=1., grime=1., cage=.05, ao=2., curve=.06, views=()):
    PROPS[key] = dict(name=name, short=short, body=body, glow=glow, bounds=bounds, voxel=voxel, tris=tris, look=look, paint=paint,
                      scale=scale, grime=grime, cage=cage, ao=ao, curve=curve, views=views)


def polar(u, v, count, phase=0.):
    """Fold the plane into one wedge of count around the origin; first result is radial."""
    r = hyp(u, v)
    a = np.arctan2(v, u) + phase
    w = 2 * math.pi / count
    a = (a + w / 2) % w - w / 2
    return r * np.cos(a), r * np.sin(a)


def lathe(shape, p, c=(0, 0, 0), axis=2):
    q = p - np.array(c, F)
    u, v = [i for i in range(3) if i != axis]
    return shape(hyp(q[:, u], q[:, v]), q[:, axis])


def once(store, build):
    if not store:
        store.update(build())
    return store


# ---------------------------------------------------------------- sidearm

GUN_X = 1.4
GUN_BODY, GUN_FRAME, GUN_GRIP, GUN_METAL, GUN_GOLD, GUN_INLAY, GUN_CORE = 1, 2, 3, 4, 5, 6, 7
GUN = {}


def gun_shapes():
    return once(GUN, lambda: dict(
        slide=Shape([(-5.0, 4.66), (-5.75, 6.55, .3), (-4.4, 7.72, .4), (5, 8.1), (12.4, 7.72, 3.5), (15.4, 6.5, .5), (15.55, 5.0, .25), (15, 4.66)], step=.015),
        frame=Shape([(-5.1, 4.56), (16.75, 4.56), (16.35, 3.95, .22), (12.0, 2.86, 1.8), (7.6, 2.72, .6), (2.2, 2.6, .35), (1.3, 2.1, .5), (-.9, -7.1, .4),
                     (-6.4, -6.7, .4), (-3.75, 2.6, 1.7), (-5.55, 3.5, .3)], step=.015),
        outer=Shape([(1.5, 2.9), (7.6, 2.9), (7.85, 2.0, .45), (6.7, -.55, .9), (2.0, -.9, 1.0), (.5, -.1), (.4, 1.6)], step=.015),
        hole=Shape([(2.5, 2.42, .3), (6.9, 2.42, .35), (5.95, .02, .6), (2.3, -.12, .7), (1.8, 1.0, .4)], step=.015),
        trigger=Shape([(3.65, 2.7), (4.35, 2.7), (4.2, 1.7, .4), (4.75, .72, .3), (4.42, .55, .15), (3.62, 1.45, .35)], step=.015),
        panel=Shape([(-3.4, 1.45), (.35, 1.45), (-1.35, -6.2), (-5.6, -5.95)], .55, step=.015),
        mag=Shape([(-1.0, -6.8), (-6.5, -6.35), (-6.78, -7.5, .25), (-.85, -8.0, .25)], step=.015),
        window=Shape([(3.0, 6.15), (4.3, 7.0), (11.3, 6.95), (12.9, 6.15), (11.7, 5.3), (4.9, 5.25)], .12, step=.015),
        bolt=Shape([(2.6, 6.28), (.95, 5.92), (1.2, 6.28), (-2.3, 4.98), (-.15, 5.72), (-.4, 5.36), (2.6, 6.02)], step=.012),
        facet=Shape([(-1.2, 4.28), (15.0, 4.28), (14.2, 3.75), (2.6, 3.25), (.7, 3.25)], .15, step=.015),
        lever=Shape([(-2.6, 4.5), (2.6, 4.5), (2.95, 4.15), (2.5, 3.75), (-.2, 3.95), (-2.5, 4.1)], .1, step=.015)))


def gun_core(p):
    q = p - np.array((GUN_X, 0, 0), F)
    b = Build(p)
    y, z = q[:, 1], q[:, 2] - 6.15
    x = q[:, 0]
    a = np.arctan2(z, y)
    radius = 1.0 + .16 * np.cos(3 * a + 2.1 * x)
    b.add(rd((hyp(y, z) - radius) * .72, np.abs(x - 8) - 6.2, .05), GUN_CORE)
    return b


def gun_body(p):
    g = gun_shapes()
    q = p - np.array((GUN_X, 0, 0), F)
    x, y, z = q[:, 0], q[:, 1], q[:, 2]
    ay = np.abs(y)
    m = np.stack((x, ay, z), 1)
    b = Build(p)

    # Slide: hexagonal section, flanks hollowed with a hard shoulder.
    d = rd(g['slide'](x, z), ay - 1.55, .13)
    d = rd(d, (ay - 1.55) * .74 + (z - 6.95) * .67, .12)
    hollow = ellipsoid(m, (6.4, 5.32, 6.1), (10.2, 3.98, 1.72))
    b.add(smax(d, -hollow, .05), GUN_BODY)
    # Graphite insert carries the core window; a gold pinstripe outlines it.
    w = g['window'](x, z)
    b.cut(np.maximum(w - .52, 1.2 - ay), GUN_METAL)
    b.cut(np.maximum(np.abs(w - .62) - .035, 1.3 - ay), GUN_GOLD)
    b.cut(rd(w - np.maximum(ay - 1.1, 0) * .8, .9 - ay, .02), GUN_METAL)
    # Rear grip serrations, slanted and V cut.
    s = np.abs(repeat(x + (z - 6) * .34, .46, -5.2, -2.4))
    b.cut(np.maximum.reduce((s - .07 - np.maximum(ay - 1.36, 0) * .7, 1.36 - ay, z - 7.2, 4.95 - z)), GUN_METAL)
    # Top vents reach the core.
    s = repeat(x, 2.55, 3.2, 10.85)
    b.cut(np.maximum(rd(np.abs(s) - .98, ay - .3 - np.maximum(z - 7.75, 0) * .7, .12), 6.85 - z), GUN_METAL)
    # Gold ribs bridge the flank windows.
    s = np.abs(repeat(x, 2.4, 5.7, 10.5))
    b.add(np.maximum.reduce((s - .17, ay - 1.28, w - .25, .8 - ay)), GUN_GOLD)
    # Ejection port on the right.
    b.cut(np.maximum(box(q, (.2, 1.3, 7.0), (1.75, .62, .72), .1), -y), GUN_GOLD)
    # Rear cap and striker.
    r = rotate(q, 1, 12, (-5.5, 0, 6.2))
    b.cut(chamfer_cyl(r, (-5.6, 0, 6.2), 0, 1.0, .3, .08), GUN_METAL)
    b.add(chamfer_cyl(r, (-5.45, 0, 6.2), 0, .62, .18, .06), GUN_GOLD)
    # Sights.
    rear = box(q, (-3.5, 0, 8.05), (.72, 1.0, .42), .12)
    rear = np.maximum(rear, -box(q, (-3.5, 0, 8.4), (2, .26, .34), .04))
    b.add(rear, GUN_FRAME)
    b.add(box(q, (11.2, 0, 8.1), (.62, .2, .44), .08), GUN_FRAME)
    for c in ((-4.2, .55, 8.15), (-4.2, -.55, 8.15), (10.6, 0, 8.22)):
        b.cut(cyl(q, c, 0, .11, .07), GUN_INLAY)
    # Lightning inlay running out of the window.
    b.cut(np.maximum(g['bolt'](x, z) - np.maximum(ay - 1.42, 0) * .4, 1.38 - ay), GUN_INLAY)

    # Compensator: graphite octagon raked at the crown, gold only in the crown.
    w_, h = ay, np.abs(z - 5.85)
    oct_ = np.maximum.reduce((w_ - 1.32, h - 1.3, (w_ + h) * .7071 - 1.56))
    comp = rd(oct_, np.maximum(14.6 - x, x + (z - 5.85) * .3 - 18.45), .1)
    b.add(comp, GUN_FRAME)
    s = repeat(x + ay * .46, 1.02, 15.9, 17.2)
    b.cut(np.maximum.reduce((np.abs(s) - .25, ay - .95, 6.55 - z, 15.2 - x)), GUN_GOLD)
    b.cut(np.maximum.reduce((np.abs(repeat(x, 1.1, 16.1, 17.2)) - .27, np.abs(z - 5.85) - .44, .6 - ay)), GUN_GOLD)
    b.cut(chamfer_cyl(q, (18.5, 0, 5.85), 0, .98, .22, .08), GUN_GOLD)
    b.cut(cyl(q, (18.5, 0, 5.85), 0, .62, 2.2), GUN_METAL)

    # Frame, with the grip swelling to fit a palm.
    blend = ramp(z, 1.4, 3.1)
    width = 1.66 - .14 * blend
    edge = .86 - .68 * blend
    f = rd(g['frame'](x, z), ay - width, edge)
    f = np.minimum(f, rd(g['outer'](x, z), ay - .66, .26))
    for c in ((2.08, -.72), (1.48, -3.2), (.88, -5.7)):
        f = smax(f, 1.56 - hyp(x - c[0], z - c[1]), .24)
    f = rd(f, -g['hole'](x, z), .1)
    b.add(box(q, (5, 0, 4.62), (10, 1.2, .2)), GUN_METAL)
    b.add(f, GUN_FRAME)
    b.cut(np.maximum(g['facet'](x, z) - np.maximum(ay - 1.4, 0) * 1.4, 1.38 - ay), None)
    # Angled heat slots glow from within.
    v = rotate(q, 1, 20, (10, 0, 3.8))
    s = repeat(v[:, 0], 1.25, 7.6, 12.6)
    slot = rd(np.abs(s) - .12, np.abs(v[:, 2] - 3.72) - .26, .1)
    b.cut(np.maximum(slot - np.maximum(ay - 1.26, 0), 1.2 - ay), GUN_INLAY)
    # Accessory rail under the nose.
    s = np.abs(repeat(x, .84, 8.4, 12.6))
    b.cut(np.maximum(s - .21, z - 2.98 - np.maximum(x - 8, 0) * .1), GUN_METAL)
    # Grip panels.
    b.cut(np.maximum(g['panel'](x, z) + .02 - np.maximum(ay - 1.3, 0) * .5, 1.3 - ay), GUN_METAL)
    panel = rd(g['panel'](x, z) + .08, ay - 1.66 + .3 * ((x + z * .24 + 1.8) / 2.6) ** 2, .2)
    b.add(panel, GUN_GRIP)
    b.cut(np.maximum(np.abs(hyp(x + 2.55, z + 2.3) - .68) - .1, 1.5 - ay), GUN_GOLD)
    b.add(chamfer_cyl(m, (-2.55, 1.56, -2.3), 1, .46, .13, .05), GUN_GOLD)
    for c in ((-3.0, .6), (-.75, .6), (-4.9, -5.3), (-1.9, -5.4)):
        d = chamfer_cyl(m, (c[0], 1.5, c[1]), 1, .25, .08, .03)
        d = np.maximum(d, -np.maximum(np.abs(rotate(m - np.array((c[0], 0, c[1]), F), 1, 30)[:, 0]) - .045, 1.53 - ay))
        b.add(d, GUN_METAL)
    # Magazine and base plate.
    b.add(rd(g['mag'](x, z), ay - 1.46, .2), GUN_FRAME)
    b.cut(np.maximum(np.abs(z + .085 * x + 7.62) - .05, np.abs(x + 3.8) - 2.4), GUN_INLAY)
    # Trigger, levers, pins, charge indicator.
    b.add(rd(g['trigger'](x, z), ay - .36, .14), GUN_GOLD)
    b.add(rd(g['lever'](x, z), np.abs(y + 1.62) - .14, .07), GUN_METAL)
    b.add(chamfer_cyl(m, (6.5, 1.55, 3.82), 1, .32, .1, .06), GUN_METAL)
    b.add(chamfer_cyl(m, (.85, 1.5, 1.72), 1, .42, .16, .05), GUN_METAL)
    s = np.abs(repeat(x, .34, -3.1, -1.74))
    b.cut(np.maximum.reduce((s - .1, np.abs(z - 3.75) - .15, 1.3 - ay)), GUN_INLAY)
    return b


GUN_LOOK = {
    GUN_BODY: dict(base=(.8, .77, .7), rough=.3, metal=0, finish='ceramic', tone=.06, rough_var=.1,
                   chip=dict(base=(.42, .38, .3), rough=.42, metal=.85), edge_a=.5, edge_b=1.2, scuff=.08, chip_amount=.8),
    GUN_FRAME: dict(base=(.13, .135, .145), rough=.4, metal=.95, finish='cast', tone=.2,
                    chip=dict(base=(.5, .49, .47), rough=.3, metal=1), edge_a=.4, edge_b=1.1, scuff=.15, chip_amount=.8),
    GUN_GRIP: dict(base=(.06, .06, .065), rough=.62, metal=0, finish='stipple', tone=.15),
    GUN_METAL: dict(base=(.2, .2, .21), rough=.38, metal=.95, finish='brushed', tone=.15),
    GUN_GOLD: dict(base=(.88, .64, .3), rough=.26, metal=1, finish='brushed', tone=.1),
    GUN_INLAY: dict(base=(.95, .62, .2), rough=.3, metal=0, glow=(.95, .5, .1)),
    GUN_CORE: dict(base=(.95, .7, .3), rough=.12, metal=0, glow=(1, .6, .15)),
}


def gun_paint(a):
    x, y, z = a.p[:, 0] - GUN_X, a.p[:, 1], a.p[:, 2]
    m = a.ids == GUN_CORE
    if m.any():
        w = fbm(a.p[m] * np.array((.9, 2.4, 2.4), F), 4)
        vein = np.exp(-(((np.abs(w - .5) - .03) / .018) ** 2))
        a.glow[m] = np.array((1, .42, .06), F) * (.38 + .35 * a.large[m])[:, None] + np.array((1, .86, .5), F) * vein[:, None]
    side = np.abs(a.n[:, 1]) > .7
    shifted = a.p - np.array((GUN_X, 0, 0), F)
    for sign in (1, -1):
        s = side & (np.sign(y) == sign)
        # Text reads front to back on the right so it is never mirrored.
        start = 13.8 if sign > 0 else 3.6
        ink = text_plane(shifted, s & (a.ids == GUN_BODY), 'MERIDIAN ARMS', (start - 2.0 * (sign > 0) * 0, 0, 4.92), (-sign, 0, 0), (0, 0, 1), .24)
        a.layer(ink, (.3, .22, .12), .4)
        a.height -= ink * .012
    s = side & (a.ids == GUN_FRAME)
    for sign, start in ((-1, 5.2), (1, 12.8)):
        ink = text_plane(shifted, s & (np.sign(y) == sign), 'MK IV  7741-PH', (start, 0, 3.72), (-sign, 0, 0), (0, 0, 1), .17)
        a.layer(ink, (.72, .7, .62), .5, 0)


prop('gun', 'SM_Physis_Gun', 'Gun', gun_body, gun_core, ((-4.8, -2.4, -9), (20.5, 2.4, 9.2)), .02, 60000, GUN_LOOK, gun_paint,
     views=((-58, 16, 1), (118, 22, 1), (-90, 2, 1), (-26, 28, .42, (15.5, 0, 6)), (150, 12, .5, (0, 0, 0)), (-125, 30, .5, (0, 0, 6))))


# ---------------------------------------------------------------- training drone

DR_SHELL, DR_ORANGE, DR_FRAME, DR_RUBBER, DR_METAL, DR_LAMP, DR_HOT, DR_EYE = 1, 2, 3, 4, 5, 6, 7, 8
DRONE = {}


def drone_shapes():
    return once(DRONE, lambda: dict(
        duct=Shape([(10.2, 5.0), (11.4, 6.2, .5), (13.0, 5.6, .8), (13.2, 1.5, .9), (12.9, -3.6, .6), (11.8, -5.4, .4), (10.0, -5.0), (9.7, 0)], step=.04, pad=3),
        fin=Shape([(-30, 6), (-16, 6), (-24, 17, .5), (-32.5, 19, .6)], .3, step=.05, pad=3),
        arm=Shape([(-13, -6.5), (12, -4.5), (9, 6.5, 2), (-9, 7.5, 2)], 1.2, step=.05, pad=3)))


def drone_hull(p):
    return ellipsoid(p, (0, 0, 2), (34, 26, 20)), ellipsoid(p, (0, 0, 1), (31, 23.4, 18))


def drone_body(p):
    g = drone_shapes()
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ay = np.abs(y)
    m = np.stack((x, ay, z), 1)
    b = Build(p)
    outer, inner = drone_hull(p)

    # Chassis under the armour.
    b.add(inner, DR_FRAME)
    # Carapace: an upper shell, swept down at the nose and tail.
    line = -3.5 + .00085 * x * x + .05 * x
    shell = rd(outer, line - z, .35)
    b.add(shell, DR_SHELL)
    # Plate joints reach down to the chassis.
    keep = -inner - .1
    spine = np.abs(ay - (8.5 + .0035 * x * x)) - .3
    ribs = np.minimum(np.abs(x + 15 + ay * .22) - .3, np.abs(x - 7 + ay * .3) - .3)
    plate = np.minimum(spine, np.where(ay > 8, ribs, 1e3))
    b.cut(np.maximum(plate - np.maximum(outer + .25, 0) * 1.2, keep))
    # Orange training spine.
    b.id[(ay < 8.2 + .0035 * x * x) & (b.id == DR_SHELL)] = DR_ORANGE
    # Shallow hatch insets on the flanks of the shell.
    for c, h in (((-6, 19, 4), (6.5, 6, 4)), ((-22, 15, 5), (4, 6, 3.2))):
        b.cut(np.maximum(box(m, c, h, .8), -outer - .45))
    # Vent louvres behind the eye.
    s = repeat(x + z * .5, 2.4, -3, 7)
    b.cut(np.maximum.reduce((np.abs(s) - .55, np.abs(z - 2) - 6.5, ay - 30, 14 - ay, -outer - 1.2)), DR_METAL)
    # Dorsal sensor spine: a raised low keel.
    b.blend(rd(box(p, (-8, 0, 21), (14, 2.4, 2), 1.6), -outer - .2 - 3, .1) if False else box(rotate(p, 1, -5), (-8, 0, 21.6), (13, 2.2, 1.7), 1.4), DR_FRAME, 1.2)
    for n in range(3):
        b.cut(box(p, (-16 + n * 7, 0, 23.2), (2.4, 1.2, .5), .3), DR_METAL)

    # Eye socket: a heavy cowled ring.
    b.cut(sphere(p, (31, 0, 2), 12.8), DR_METAL)
    v = np.stack((x - 25, y, z - 2), 1)
    ring = np.maximum(np.abs(hyp(y, z - 2) - 11.8 + (x - 27) * .28) - 1.5, np.abs(x - 28) - 3.2)
    b.add(rd(ring, np.abs(x - 28) - 3.2, .4), DR_FRAME)
    brow = rotate(p, 1, 16, (26, 0, 13))
    b.blend(rd(box(brow, (24, 0, 13.6), (9, 10.5, 1.5), 1.2), -(z - 11.8), .4), DR_SHELL, .8)
    # Iris blades.
    u_, v_ = polar(rotate(v, 0, 12)[:, 1], rotate(v, 0, 12)[:, 2], 10)
    blade = np.maximum.reduce((np.abs(u_ - 8.8) - 2.6, np.abs(v_ + (u_ - 8.8) * .55) - 1.25, np.abs(x - 25.5) - .55))
    b.add(blade, DR_METAL)
    b.add(torus(p, (24, 0, 2), 0, 9, .9) if False else np.maximum(np.abs(hyp(y, z - 2) - 11.2) - .9, np.abs(x - 24) - 2), DR_RUBBER)

    # Thrust nacelles.
    c = (-3, 32, -2)
    duct = lathe(g['duct'], m, c)
    # Stators and hub inside the duct.
    n = m - np.array(c, F)
    u_, v_ = polar(n[:, 0], n[:, 1], 5, .4)
    stator = np.maximum.reduce((np.abs(v_) - .6, u_ - 11, 2.5 - u_, np.abs(n[:, 2] + 3.5) - 1.4))
    hub = lathe(HUB, m, c)
    u_, v_ = polar(n[:, 0], n[:, 1], 9, n[:, 2] * 0)
    twist = np.abs(v_ + (u_ - 7) * .14 + n[:, 2] * .35)
    rotor = np.maximum.reduce((twist - .3, u_ - 9.6, 2.5 - u_, np.abs(n[:, 2] - .8) - 1.1))
    b.add(np.minimum(stator, hub), DR_METAL)
    b.add(rotor, DR_METAL)
    b.add(duct, DR_SHELL)
    # Lamp strip inside the lip, hazard band on the rim comes from paint.
    b.cut(np.maximum(np.abs(hyp(n[:, 0], n[:, 1]) - 13.25) - .1, np.abs(n[:, 2] - 1.6) - .5) - .12, DR_LAMP)
    # Pylons from hull to nacelle with an armoured cheek.
    arm = rd(g['arm'](x + 3, z - 1), np.abs(ay - 21.5) - 6.5, .9)
    arm = np.maximum(arm, -sphere(m, (-3, 32, 16), 1) if False else -(hyp(n[:, 0], n[:, 1]) - 13.0))
    b.add(arm, DR_FRAME)
    cheek = rd(ellipsoid(m, (-3, 22, 3), (15, 9, 11.5)), 1.5 - (m[:, 2] - 1 + .08 * (x + 3)) - 3, .5)
    cheek = np.maximum(cheek, -(hyp(n[:, 0], n[:, 1]) - 13.4))
    b.blend(cheek, DR_SHELL, .4)
    b.cut(np.maximum(np.abs(x + 3 + (m[:, 2] - 5) * .3) - .25, -ellipsoid(m, (-3, 22, 3), (15, 9, 11.5)) - .6))
    b.cut(np.maximum.reduce((np.abs(repeat(m[:, 2], 2.0, -2.5, 1.5)) - .4, np.abs(x + 3) - 7, 20 - ay, ay - 27.5)), DR_METAL)
    # Hydraulic strut under each pylon.
    b.add(capsule(m, (6, 12, -9), (2, 24, -5.8), 1.6), DR_METAL)
    b.add(capsule(m, (6, 12, -9), (3.6, 19, -7), 2.3), DR_FRAME)

    # Chin turret with twin barrels.
    b.add(sphere(p, (15, 0, -13), 7.5), DR_RUBBER)
    t = rotate(p, 1, -8, (15, 0, -13))
    b.add(box(t, (18.5, 0, -13.2), (6.5, 7, 3), 1.2), DR_FRAME)
    tm = np.stack((t[:, 0], np.abs(t[:, 1]), t[:, 2]), 1)
    b.add(chamfer_cyl(tm, (28, 4.6, -13.2), 0, 1.5, 11, .15), DR_METAL)
    b.add(chamfer_cyl(tm, (25, 4.6, -13.2), 0, 2.15, 2.2, .3), DR_FRAME)
    b.add(chamfer_cyl(tm, (37.8, 4.6, -13.2), 0, 2.0, 1.6, .25), DR_FRAME)
    b.cut(cyl(tm, (39.5, 4.6, -13.2), 0, 1.0, 2.5), DR_RUBBER)
    s = repeat(t[:, 0], 1.4, 29, 34)
    b.cut(np.maximum.reduce((np.abs(s) - .3, tm[:, 1] - 8, np.abs(tm[:, 1] - 4.6) - 3, t[:, 2] + 12.2, -t[:, 2] - 14.4)) if False else 1e3 + 0 * x)

    # Rear drive pair and tail fins.
    rear = np.maximum(hyp(m[:, 1] - 8.5, z - 1) - 5.2, np.abs(x + 30.5) - 5)
    b.add(rd(rear, np.abs(x + 30.5) - 5, .5), DR_FRAME)
    b.cut(cyl(m, (-36, 8.5, 1), 0, 3.9, 2.8), DR_METAL)
    u_, v_ = polar(m[:, 1] - 8.5, z - 1, 6)
    b.add(np.maximum.reduce((np.abs(v_) - .2, u_ - 3.9, np.abs(x + 34.5) - 1)), DR_METAL)
    fin = rotate(m, 0, -19, (0, 3, 6))
    b.blend(rd(g['fin'](fin[:, 0], fin[:, 2]), np.abs(fin[:, 1] - 3) - .75, .4), DR_SHELL, .9)
    # Antenna mast.
    b.add(capsule(p, (-20, 0, 21), (-26, 0, 35), .32), DR_METAL)
    b.add(cyl(p, (-20.4, 0, 22), 2, 1.4, 1.6, .3), DR_FRAME)
    # Armour fasteners at plate corners.
    for c_ in ((-11, 10.3, 16.6), (4, 10, 17.4), (-11, 21, 8), (2, 22.3, 8.4)):
        b.add(chamfer_cyl(rotate(m - np.array(c_, F), 0, 45 if c_[1] > 20 else 22), (0, 0, 0), 2, .9, .6, .2), DR_METAL)
    return b


HUB = Shape([(0, 2.6), (2.4, 2.6, .5), (4.2, 1.2, .7), (3.6, -4.5, 1), (1, -7.2, .6), (0, -7.4)], step=.04, pad=3)


def drone_glow(p):
    b = Build(p)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    # Eye lens, faceted slightly by a fine ring.
    b.add(sphere(p, (18.5, 0, 2), 9.2), DR_EYE)
    # Hot thrust plates deep in each duct.
    m = np.stack((x, np.abs(y), z), 1)
    b.add(chamfer_cyl(m, (-3, 32, -4.6), 2, 10.6, .22, .05), DR_HOT)
    # Rear drive glow.
    b.add(cyl(m, (-33.2, 8.5, 1), 0, 4.1, .3), DR_HOT)
    return b


DRONE_LOOK = {
    DR_SHELL: dict(base=(.74, .73, .69), rough=.42, metal=0, finish='ceramic', tone=.12, rough_var=.16,
                   chip=dict(base=(.27, .27, .28), rough=.42, metal=.9), edge_a=.3, edge_b=.95, chip_amount=.9, scuff=.3),
    DR_ORANGE: dict(base=(.82, .31, .07), rough=.42, metal=0, finish='ceramic', tone=.13,
                    chip=dict(base=(.27, .27, .28), rough=.42, metal=.9), edge_a=.3, edge_b=.95, chip_amount=.9, scuff=.35),
    DR_FRAME: dict(base=(.14, .15, .165), rough=.44, metal=.85, finish='cast', tone=.2,
                   chip=dict(base=(.5, .5, .48), rough=.34, metal=1), edge_a=.4, edge_b=1.1, chip_amount=.7, scuff=.2),
    DR_RUBBER: dict(base=(.05, .05, .055), rough=.72, metal=0, finish='cast'),
    DR_METAL: dict(base=(.42, .42, .43), rough=.34, metal=1, finish='brushed', along=(0, 0, 1), tone=.14),
    DR_LAMP: dict(base=(1, .4, .1), rough=.3, metal=0, glow=(1, .36, .06)),
    DR_HOT: dict(base=(1, .55, .2), rough=.4, metal=0, glow=(1, .5, .14)),
    DR_EYE: dict(base=(.9, .12, .04), rough=.08, metal=0, glow=(1, .14, .03)),
}


def drone_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    ay = np.abs(y)
    # Eye: pupil, rings and a hot centre.
    m = a.ids == DR_EYE
    r = hyp(y[m], z[m] - 2)
    a.glow[m] = (np.array((1, .05, .01), F) * (.5 + .5 * ramp(r, 7, 2))[:, None]
                 + np.array((1, .55, .25), F) * ramp(r, 3.2, 1.2)[:, None]
                 + np.array((1, .16, .03), F) * (np.abs(((r / 1.3) % 1) - .5) < .07)[:, None] * .35)
    # Thrust plates are hottest at the hub.
    m = a.ids == DR_HOT
    mm = np.stack((x[m], ay[m], z[m]), 1) - np.array((-3, 32, 0), F)
    k = ramp(hyp(mm[:, 0], mm[:, 1]), 11, 3)
    a.glow[m] = np.array((1, .32, .05), F) * (.45 + k[:, None] * .55)
    # Hazard band on the duct rims.
    n = np.stack((x, ay, z), 1) - np.array((-3, 32, -2), F)
    angle = np.arctan2(n[:, 1], n[:, 0])
    rim = (a.ids == DR_SHELL) & (hyp(n[:, 0], n[:, 1]) > 10) & (hyp(n[:, 0], n[:, 1]) < 13.5) & (n[:, 2] > 3)
    stripe = ((angle * 12 / (2 * math.pi) + n[:, 2] * .06) % 1) < .5
    band = (rim & (hyp(n[:, 0], n[:, 1]) < 13.1) & (hyp(n[:, 0], n[:, 1]) > 10.8)).astype(F)
    a.layer(band * stripe, (.08, .08, .085))
    a.layer(band * ~stripe, (.85, .55, .06))
    wear = a.wear > .5
    a.base[wear] = (.27, .27, .28)
    # Stencils on the armour.
    top = (a.n[:, 2] > .55) & np.isin(a.ids, (DR_SHELL, DR_ORANGE))
    for sign in (1, -1):
        ink = text_plane(a.p, top & (np.sign(y) == sign), 'TRN-07', (-4 if sign < 0 else 8, -sign * 14.5, 0), (-1, 0, 0) if sign > 0 else (1, 0, 0), (0, sign, 0), 3.2, .13)
        a.layer(ink * (a.wear < .5), (.09, .09, .1))
        ink = text_plane(a.p, top & (np.sign(y) == sign), 'MERIDIAN', (-18 if sign < 0 else -13, -sign * 12, 0), (-1, 0, 0) if sign > 0 else (1, 0, 0), (0, sign, 0), 1.1, .1)
        a.layer(ink * (a.wear < .5), (.09, .09, .1))
    # Hit marks from training rounds.
    impacts = np.random.default_rng(5).uniform((-30, -24, -5), (24, 24, 20), (16, 3))
    for c in impacts:
        d = hyp(x - c[0], y - c[1], z - c[2])
        s = ramp(d, 2.6, .5) * (a.ids != DR_EYE) * (a.glow.sum(1) == 0)
        scorch = s * ramp(a.medium + (a.fine - .5) * .8, .35, .6)
        a.base = a.base * (1 - scorch[:, None] * .7) + np.array((.04, .036, .03), F) * scorch[:, None] * .7
        a.rough = np.clip(a.rough + scorch * .2, 0, 1)
        a.metal = a.metal * (1 - scorch)


prop('drone', 'SM_Drone', 'Drone', drone_body, drone_glow, ((-38, -47, -22), (42, 47, 38)), .1, 90000, DRONE_LOOK, drone_paint,
     scale=4., cage=.2, ao=12., curve=.22,
     views=((-35, 22, 1), (35, 8, 1), (145, 30, 1), (-90, 55, 1), (2, 2, .55, (28, 0, -2)), (-125, -30, .9)))


# ---------------------------------------------------------------- pickups

HP_CAP, HP_RED, HP_METAL, HP_RUBBER, HP_GOLD, HP_LAMP, HP_FLUID = 1, 2, 3, 4, 5, 6, 7
HEALTH = {}


def health_body(p):
    s = once(HEALTH, lambda: dict(
        cap=Shape([(0, 17.2), (5.2, 17.2, .8), (8.4, 16, 1.4), (10.8, 13.4, 1.2), (11.2, 11.2, .4), (10.4, 10.6, .25), (10.4, 9.6, .25), (9.2, 9.1), (0, 9.1)], step=.015)))
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    az = np.abs(z)
    m = np.stack((x, y, az), 1)
    b = Build(p)
    cap = lathe(s['cap'], m)
    b.add(cap, HP_CAP)
    # A red collar band, seated in a groove.
    b.cut(np.maximum(np.abs(az - 12.8) - .95, 10.3 - hyp(x, y)), HP_RED)
    b.cut(np.maximum(np.abs(np.abs(az - 12.8) - 1.08) - .08, 10.2 - hyp(x, y)), HP_METAL)
    # End face: recessed cross, lit, with a grip knurl.
    cross = np.minimum(box(p * np.array((1, 1, 0), F), (0, 0, 0), (2.4, .8, 1)), box(p * np.array((1, 1, 0), F), (0, 0, 0), (.8, 2.4, 1)))
    b.cut(np.maximum(cross, 16.75 - az), HP_LAMP)
    b.cut(np.maximum(np.abs(hyp(x, y) - 4.4) - .12, 17 - az), HP_METAL)
    # Clamp shoulders that carry the struts.
    u, v = polar(x, y, 3, .52)
    b.add(rd(np.maximum(np.abs(v) - 1.9, np.abs(u - 9.1) - 1.5), az - 10.4, .35), HP_METAL)
    # Struts and their stepped sleeves.
    strut = hyp(u - 9.0, v)
    b.add(rd(strut - .78, az - 10, .1), HP_METAL)
    b.add(rd(strut - 1.08, np.abs(az - 3.6) - 2.8, .15), HP_RUBBER)
    # Waist ring holds the tank.
    b.add(rd(np.abs(hyp(x, y) - 8.5) - .55, az - .7, .2), HP_GOLD)
    b.cut(np.maximum.reduce((np.abs(repeat(polar(x, y, 12)[1], 1, 0, 0)) - .35, az - .32, 8.7 - hyp(x, y))), HP_METAL)
    # Inner seats of the tank.
    b.add(rd(hyp(x, y) - 8.0, np.abs(az - 9.4) - .5, .2), HP_METAL)
    return b


def health_glow(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    a = np.arctan2(y, x)
    b = Build(p)
    r = hyp(x, y)
    # Fluid column with a slow helix through it.
    b.add(rd(r - 7.7 - .14 * np.sin(2 * a + z * .9), np.abs(z) - 9.6, .3) * .85, HP_FLUID)
    return b


HEALTH_LOOK = {
    HP_CAP: dict(base=(.84, .84, .82), rough=.28, metal=0, finish='ceramic', tone=.05,
                 chip=dict(base=(.5, .5, .5), rough=.34, metal=1), chip_amount=.6, scuff=.1, edge_a=.5, edge_b=1.3),
    HP_RED: dict(base=(.72, .09, .05), rough=.32, metal=0, finish='ceramic', tone=.08),
    HP_METAL: dict(base=(.62, .62, .63), rough=.28, metal=1, finish='brushed', along=(0, 0, 1), tone=.08),
    HP_RUBBER: dict(base=(.06, .06, .065), rough=.66, metal=0, finish='stipple'),
    HP_GOLD: dict(base=(.86, .62, .3), rough=.28, metal=1, finish='brushed', along=(0, 0, 1)),
    HP_LAMP: dict(base=(1, .2, .1), rough=.3, metal=0, glow=(1, .18, .07)),
    HP_FLUID: dict(base=(.95, .22, .12), rough=.06, metal=0, glow=(1, .2, .08)),
}


def health_paint(a):
    m = a.ids == HP_FLUID
    x, y, z = a.p[m, 0], a.p[m, 1], a.p[m, 2]
    angle = np.arctan2(y, x)
    wave = np.sin(angle * 2 + z * .9)
    helix = ramp(wave, .55, .98)
    q = a.p[m] * .55
    cells = fbm(q + np.array((0, 0, 3), F), 3)
    bubbles = ramp(noise(a.p[m] * 1.6), .78, .84)
    level = .32 + .4 * ramp(np.abs(z), 9, 2)
    a.glow[m] = (np.array((1, .1, .04), F) * (level * (.75 + cells * .5))[:, None]
                 + np.array((1, .55, .42), F) * (helix * .6 + bubbles * .7)[:, None])
    a.base[m] = np.array((.5, .05, .03), F)
    b = np.abs(a.n[:, 2]) < .55
    ink = text_plane(a.p, b & (a.ids == HP_CAP) & (a.p[:, 0] > 0), 'MEDIGEL 40CC', (10, 6.2, 15.3), (0, -1, 0), (0, 0, 1), .75, .1) if False else 0 * a.rough
    a.layer(ink, (.1, .1, .1))


prop('health', 'SM_Pickup_Health', 'PickupHealth', health_body, health_glow, ((-13, -13, -18.5), (13, 13, 18.5)), .03, 28000, HEALTH_LOOK, health_paint,
     scale=1.6, grime=.6, cage=.08, ao=3., curve=.1, views=((-40, 16, 1), (-10, 60, .85)))


SEED_HUSK, SEED_DARK, SEED_VEIN, SEED_CRYSTAL = 1, 2, 3, 4
SEED = {}


def seed_shape():
    return once(SEED, lambda: dict(
        husk=Shape([(0, 22.6), (1.2, 20.5, 1), (6, 14.5, 3), (11.8, 4, 4), (12.6, -3, 4), (9, -12.6, 3), (3.4, -18, 1.5), (0, -19.6)], step=.03, pad=3)))


def seed_warp(p):
    s = p.copy()
    s[:, 0] += .8 * np.sin(p[:, 2] * .17 + 1)
    s[:, 1] += .6 * np.sin(p[:, 2] * .13 + 2.5)
    return s


def seed_body(p):
    g = seed_shape()
    s = seed_warp(p)
    x, y, z = s[:, 0], s[:, 1], s[:, 2]
    r = hyp(x, y)
    a = np.arctan2(y, x)
    turn = a + z * .1 + .25 * np.sin(z * .22)
    b = Build(p)
    outer = lathe(g['husk'], s)
    # Five leaves spiral up the seed. Slits close at both tips and gape mid body.
    open_ = ramp(z, -15, -1) * ramp(z, 17, 6)
    leaf = np.cos(5 * turn)
    # Distance from the slit centre across the surface, in cm.
    slit = (np.arccos(np.clip(leaf, -1, 1)) * -1 + math.pi) / 5 * np.maximum(r, 1)
    gap = slit - (.14 + 3.1 * open_)
    # Leaf belly: fuller in the centre of each leaf, like a bud.
    belly = (slit / 6.5) ** 2 * 1.4
    husk = smax(np.abs(outer + belly + 1.1) - 1.05, -gap, .4)
    husk = smax(husk, -hyp(gap - 5, gap * 0) * 0 - 1e3, .1)
    # Living ribs raised along each leaf.
    k = np.abs(np.abs(np.sin(5 * turn * .5)) - .5)
    rib = np.cos(3 * (turn * 5) + z * .7)
    husk = husk - .16 * ramp(rib, .4, 1) * ramp(gap, .3, 2)
    b.add(husk * .8, SEED_HUSK)
    # Inner lining of the leaves goes dark.
    # Veins run just beside the slit edges.
    vein = np.abs(gap - .5 - .16 * np.sin(z * 2.3 + a * 5)) - .14
    b.cut(np.maximum(vein, outer + belly + .1) * .8, SEED_VEIN)
    # Root tendrils curl under the seed, the stem curls above.
    for n in range(5):
        t = n * 2 * math.pi / 5 + .4
        o = np.array((math.cos(t), math.sin(t), 0))
        w = np.array((-o[1], o[0], 0))
        pts = bezier(o * 2 + (0, 0, -15.5), o * 11 + w * 3 + (0, 0, -19.5), o * 13.5 + w * -2 + (0, 0, -16.5), o * 11.5 + w * -4.5 + (0, 0, -13.5 - n * .5), 9)
        b.blend(tube(p, pts, 1.15, .22), SEED_HUSK, .9)
    for n in range(3):
        t = n * 2 * math.pi / 3 + 1.1
        o = np.array((math.cos(t), math.sin(t), 0))
        w = np.array((-o[1], o[0], 0))
        pts = bezier((0, 0, 19), o * 1 + (0, 0, 21.5), o * 3.6 + w * 1.6 + (0, 0, 21.5), o * 4.2 + w * 3.4 + (0, 0, 17.8 + n * .4), 8)
        b.blend(tube(p, pts, .7, .14), SEED_HUSK, .5)
    return b


def seed_crystal(p):
    b = Build(p)
    s = seed_warp(p)
    d = None
    for rx, ry, c, h, w in ((0, 0, (0, 0, 0), 17, 8.7), (22, 40, (2.6, -1.5, 3), 12.5, 5), (-19, 150, (-1.5, 2.8, -3), 12.5, 4.6), (12, 260, (-2.8, -2.2, 5), 9, 3.8)):
        q = rotate(rotate(s, 2, ry), 0, rx)
        q = q - np.array(c, F)
        u, v = polar(q[:, 0], q[:, 1], 6, rx * .1 + .3)
        # A doubly terminated faceted prism.
        e = np.maximum.reduce((u - w, (u * 1.3 + np.abs(q[:, 2]) - h + w * 1.3 * .42) * .6))
        d = e if d is None else np.minimum(d, e)
    b.add(d, SEED_CRYSTAL)
    return b


SEED_LOOK = {
    SEED_HUSK: dict(base=(.86, .6, .22), rough=.3, metal=1, finish='organic', tone=.28, rough_var=.3),
    SEED_DARK: dict(base=(.14, .09, .05), rough=.5, metal=.8, finish='organic'),
    SEED_VEIN: dict(base=(1, .7, .25), rough=.3, metal=0, glow=(1, .62, .16)),
    SEED_CRYSTAL: dict(base=(1, .78, .36), rough=.08, metal=0, glow=(1, .58, .14)),
}


def seed_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    # Antique hollows, polished high points.
    m = a.ids == SEED_HUSK
    hollow = ramp(-a.curve[m], .02, .35) + (1 - a.ao[m]) * .9
    pat = np.clip(hollow, 0, 1) * (.55 + a.medium[m] * .8)
    pat = np.clip(pat, 0, 1)[:, None]
    a.base[m] = a.base[m] * (1 - pat) + np.array((.12, .075, .04), F) * pat
    a.rough[m] = np.clip(a.rough[m] + pat[:, 0] * .4, 0, 1)
    shine = ramp(a.curve[m], .1, .6)
    a.base[m] = np.clip(a.base[m] * (1 + shine[:, None] * .3), 0, 1)
    # Crystal: light gathers in fractures and at its heart.
    m = a.ids == SEED_CRYSTAL
    w = fbm(a.p[m] * .22, 4)
    vein = np.exp(-(((w - .5) / .012) ** 2))
    heart = ramp(hyp(x[m], y[m], z[m] * .6), 12, 2)
    edge = ramp(a.curve[m], .12, .5)
    a.glow[m] = (np.array((1, .4, .05), F) * (.35 + heart * .5)[:, None]
                 + np.array((1, .85, .5), F) * (vein * .9 + edge * .8)[:, None])
    a.base[m] = np.array((.82, .55, .18), F)


prop('divinity', 'SM_Pickup_Divinity', 'PickupDivinity', seed_body, seed_crystal, ((-17, -17, -22.5), (17, 17, 23)), .035, 42000, SEED_LOOK, seed_paint,
     scale=2., grime=.2, cage=.1, ao=5., curve=.14, views=((-40, 12, 1), (130, 22, 1), (-20, 4, .5, (0, 0, 2))))


AM_SHELL, AM_FRAME, AM_METAL, AM_GOLD, AM_RUBBER, AM_LAMP, AM_CELL = 1, 2, 3, 4, 5, 6, 7
AMMO = {}


def ammo_body(p):
    s = once(AMMO, lambda: dict(
        cap=Shape([(0, 20), (4, 20, .4), (5.8, 18.7, .3), (9.8, 18, .9), (11, 16, .7), (11, 13, .4), (0, 13)], step=.015),
        window=Shape([(-2.5, -9), (2.5, -9), (3.1, -8), (3.1, 8), (2.5, 9), (-2.5, 9), (-3.1, 8), (-3.1, -8)], .3, step=.015)))
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    az = np.abs(z)
    m = np.stack((x, y, az), 1)
    b = Build(p)
    u, v = polar(x, y, 8, math.pi / 8)
    prism = rd(u - 9.2, az - 15, .5)
    b.add(prism, AM_SHELL)
    # Four long windows; alternate faces carry ribs.
    u4, v4 = polar(x, y, 4)
    win = s['window'](v4, z) - np.maximum(u4 - 8.2, 0) * .8
    b.cut(np.maximum(win, 7.2 - u4), AM_FRAME)
    u4b, v4b = polar(x, y, 4, math.pi / 4)
    b.cut(np.maximum.reduce((np.abs(repeat(z, 1.6, -7.2, 7.2)) - .34, np.abs(v4b) - 2.3, 8.75 - u4b)), AM_METAL)
    # End collars.
    collar = rd(u - 9.7, np.abs(az - 14) - 2.2, .35)
    b.add(collar, AM_FRAME)
    # Cap: lathe, so it reads as a machined part.
    b.add(lathe(s['cap'], np.stack((x, y, z), 1)), AM_METAL)
    b.add(rd(hyp(x, y) - 10.7, np.abs(z + 17) - 3, .5), AM_FRAME)
    # Contacts on the top face; lit ring between them.
    u6, v6 = polar(x, y, 6, .26)
    b.add(rd(hyp(u6 - 7.7, v6) - .95, z - 19.5, .15), AM_GOLD)
    b.cut(np.maximum(np.abs(hyp(x, y) - 2.6) - .32, 19.8 - z), AM_LAMP)
    # Foot: drive pins seat the cell in its bay.
    b.cut(np.maximum.reduce((hyp(u6 - 6.4, v6) - 1.1, z + 19.3)), AM_RUBBER)
    # Carry bail.
    side = bezier((0, -9.6, 14.5), (0, -10.5, 21.5), (0, -5, 21.8), n=8)
    q = np.stack((x, np.abs(y) * -1, z), 1)
    b.add(np.minimum(tube(q, side, .55), capsule(p, (0, -5, 21.8), (0, 5, 21.8), .55)), AM_RUBBER)
    b.add(chamfer_cyl(np.stack((x, np.abs(y), z), 1), (0, 9.7, 14.6), 1, 1.5, .7, .2), AM_FRAME)
    # Latches over the collars.
    u_, v_ = polar(x, y, 4, math.pi / 4)
    b.add(np.maximum(box(np.stack((u_, v_, az), 1), (9.8, 0, 12.2), (.5, 1.5, 3.4), .25), -1e3 + 0 * x), AM_METAL)
    return b


def ammo_glow(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    b = Build(p)
    r = hyp(x, y)
    b.add(rd(r - 7.5 + .3 * np.cos(z * 2.2), np.abs(z) - 12.5, .3) * .9, AM_CELL)
    return b


AMMO_LOOK = {
    AM_SHELL: dict(base=(.2, .205, .22), rough=.38, metal=.1, finish='cast', tone=.12,
                   chip=dict(base=(.55, .54, .52), rough=.3, metal=1), edge_a=.25, edge_b=.85, scuff=.25),
    AM_FRAME: dict(base=(.1, .105, .115), rough=.42, metal=.9, finish='cast',
                   chip=dict(base=(.5, .5, .48), rough=.3, metal=1), edge_a=.35, edge_b=1, scuff=.1),
    AM_METAL: dict(base=(.52, .52, .53), rough=.3, metal=1, finish='brushed', along=(0, 0, 1)),
    AM_GOLD: dict(base=(.88, .64, .3), rough=.24, metal=1, finish='brushed'),
    AM_RUBBER: dict(base=(.05, .05, .055), rough=.66, metal=0, finish='stipple'),
    AM_LAMP: dict(base=(1, .45, .1), rough=.3, metal=0, glow=(1, .42, .06)),
    AM_CELL: dict(base=(1, .5, .12), rough=.1, metal=0, glow=(1, .42, .05)),
}


def ammo_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    m = a.ids == AM_CELL
    w = fbm(a.p[m] * np.array((.45, .45, .18), F), 4)
    arc = np.exp(-(((w - .5) / .016) ** 2))
    ring = ramp(np.abs(((z[m] / 2.86) % 1) - .5), .35, .46)
    a.glow[m] = (np.array((1, .3, .03), F) * (.5 + .25 * a.large[m] - ring[:, None][:, 0] * .3)[:, None] + np.array((1, .82, .45), F) * arc[:, None])
    u, v = polar(x, y, 8, math.pi / 8)
    # Hazard band on the lower collar, charge label on two flats.
    band = ((np.abs(z + 13.9) < 1.1) & (a.ids == AM_FRAME)).astype(F)
    stripe = ((np.arctan2(y, x) * 8 + z * .5) % (math.pi * 2 / 3)) < math.pi / 3
    a.layer(band * stripe * (a.wear < .4), (.8, .52, .05), .42, 0)
    a.layer(band * ~stripe * (a.wear < .4), (.05, .05, .055), .42, 0)
    flats = (a.ids == AM_SHELL)
    angle = -math.pi / 4
    for t, title in ((-3 * math.pi / 4 + 0, 'CELL 8.2'), (math.pi / 4, 'CELL 8.2')):
        c, s = math.cos(t), math.sin(t)
        facing = (a.n[:, 0] * c + a.n[:, 1] * s) > .9
        rx, ry = (-s, c)
        ink = text_plane(a.p, facing & flats, title, (c * 9 - rx * 1.5 * 1 * -1, s * 9 - ry * 1.5 * -1, 3.5), (rx * -1, ry * -1, 0), (0, 0, 1), .62, .12)
        a.layer(ink * (a.wear < .4), (.82, .8, .72), .5, 0)
        ink = text_plane(a.p, facing & flats, 'MJ DC', (c * 9 - rx * 1.5 * -1, s * 9 - ry * 1.5 * -1, 2.2), (rx * -1, ry * -1, 0), (0, 0, 1), .62, .12)
        a.layer(ink * (a.wear < .4), (.8, .52, .05), .5, 0)


prop('ammo', 'SM_Pickup_Ammo', 'PickupAmmo', ammo_body, ammo_glow, ((-13, -13, -21), (13, 13, 23)), .03, 30000, AMMO_LOOK, ammo_paint,
     scale=1.6, cage=.08, ao=3., curve=.1, views=((-38, 16, 1), (20, 42, .85)))


# ---------------------------------------------------------------- scan targets, wall mounted, front toward -Y

SC_PLATE, SC_PAINT, SC_METAL, SC_RUBBER, SC_GOLD, SC_LAMP, SC_FLOW, SC_SCREEN, SC_KEY = 1, 2, 3, 4, 5, 6, 7, 8, 9
SC_LOOK = {
    SC_PLATE: dict(base=(.17, .18, .195), rough=.44, metal=.8, finish='cast', tone=.18,
                   chip=dict(base=(.52, .52, .5), rough=.32, metal=1), edge_a=.25, edge_b=.85, scuff=.25),
    SC_PAINT: dict(base=(.6, .58, .52), rough=.42, metal=0, finish='ceramic', tone=.14,
                   chip=dict(base=(.25, .25, .26), rough=.4, metal=.9), edge_a=.2, edge_b=.8, scuff=.35),
    SC_METAL: dict(base=(.5, .5, .51), rough=.34, metal=1, finish='brushed', along=(0, 0, 1), tone=.14),
    SC_RUBBER: dict(base=(.055, .055, .06), rough=.68, metal=0, finish='cast'),
    SC_GOLD: dict(base=(.86, .62, .28), rough=.28, metal=1, finish='brushed', along=(0, 0, 1)),
    SC_LAMP: dict(base=(1, .55, .15), rough=.3, metal=0, glow=(1, .5, .1)),
    SC_FLOW: dict(base=(1, .6, .2), rough=.1, metal=0, glow=(1, .52, .1)),
    SC_SCREEN: dict(base=(.02, .05, .07), rough=.08, metal=0, glow=(.02, .06, .08)),
    SC_KEY: dict(base=(.1, .1, .11), rough=.5, metal=0, finish='cast'),
}


def conduit_body(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax, az = np.abs(x), np.abs(z)
    m = np.stack((ax, y, z), 1)
    mz = np.stack((ax, y, az), 1)
    b = Build(p)
    # Wall strongback.
    b.add(box(p, (0, 6, 0), (27, 1.5, 60), .5), SC_PLATE)
    s = repeat(z, 13, -52, 52)
    b.cut(np.maximum.reduce((np.abs(ax - 23.6) - 1.6, np.abs(s) - 3.2, 3.9 - y)), SC_RUBBER)
    # Power mains enter top and bottom, then fan into the junction.
    for c, r in ((0, 3.9), (9.5, 2.9), (17, 2.2)):
        k = 21 if c == 0 else (24 + c * .25)
        pts = bezier((c, 2.2, 60), (c, 2.2, k + 8), (c * .9, 1.8 + c * .05, k + 4), (c * .8, -.6, k - 2), 7)
        b.add(tube(mz, pts, r), SC_PAINT if c == 0 else SC_METAL)
    # Pipe collars.
    b.add(np.minimum(chamfer_cyl(mz, (0, 2.2, 49), 2, 5.0, 1.2, .35), chamfer_cyl(mz, (0, 2.2, 36), 2, 5.0, 1.2, .35)), SC_PLATE)
    b.add(np.minimum(chamfer_cyl(mz, (9.5, 2.2, 49), 2, 3.8, .9, .3), chamfer_cyl(mz, (17, 2.2, 49), 2, 3.1, .8, .25)), SC_PLATE)
    # Retaining clamps across the bundle.
    clamp = rd(box(mz, (0, 3.6, 42.4), (23.5, 3.6, 2), .5), -hyp(ax * 0 + 1e3 * 0 + 0, 0 * ax) - 1e3, 0) if False else box(mz, (0, 2.6, 42.5), (22.5, 3.0, 1.9), .5)
    b.add(clamp, SC_PAINT)
    for c in (6, 13.5, 21):
        b.add(chamfer_cyl(mz, (c, -.4, 42.5), 1, .95, .55, .15), SC_METAL)
    # Junction housing.
    d = box(p, (0, 0, 0), (25.5, 7.2, 25.5), 1.2)
    d = cd(d, (ax + np.abs(z) - 45.5) * .7071, 0)
    b.add(d, SC_PAINT)
    # Heat-sink flanks.
    t = np.abs(repeat(z, 2.6, -16, 16))
    b.cut(np.maximum.reduce((t - .55, 18.8 - ax, 26 - 0 * ax - 1e3, -y - 6.6)) if False else np.maximum.reduce((t - .55, 18.8 - ax, -y - 6.4, y - 9)), SC_METAL)
    # Window into the bus, framed.
    win = box(p * np.array((1, 1, 1), F), (0, -7, 0), (13.6, 2.6, 21), 1.2)
    b.cut(win, SC_PLATE)
    frame = np.maximum(np.abs(box(p, (0, -6.4, 0), (15.6, 1.3, 23), 1.2)) - 0, 0 * x - 1e3)
    b.add(np.maximum(box(p, (0, -6.8, 0), (15.8, .9, 23.2), .4), -box(p, (0, -7, 0), (13.5, 2, 20.9), .9)), SC_PLATE)
    # Glass guard bars across the window.
    t = np.abs(repeat(z, 10.5, -15.75, 15.75))
    b.add(rd(t - .5, np.abs(y + 6.3) - .45, .2) + np.maximum(ax - 14, 0), SC_METAL)
    # Insulators stacked each side of the bus.
    b.add(np.maximum.reduce((hyp(np.abs(ax - 9.8), y + 1.8) - 1.5 - .34 * np.cos(z * 2.2), az - 21)), SC_RUBBER)
    # Corner fasteners.
    for c in ((21.5, 21.5), (21.5, 8), (21.5, -8), (21.5, -21.5)):
        b.add(chamfer_cyl(m, (c[0], -7.2, c[1]), 1, 1.0, .5, .15), SC_METAL)
    # Lamp column and a warning lamp over the housing.
    s = np.abs(repeat(z, 2.4, -10, 10))
    b.cut(np.maximum.reduce((s - .7, np.abs(ax - 17.4) - .5, y + 6.9)), SC_LAMP)
    return b


def conduit_glow(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    b = Build(p)
    # A living bus bar: three twisting rods.
    a = z * .34
    dx, dy = x - 3.4 * np.cos(a), (y + 2.2) - 2.4 * np.sin(a)
    r1 = hyp(dx, dy) - 1.5
    dx, dy = x - 3.4 * np.cos(a + 2.09), (y + 2.2) - 2.4 * np.sin(a + 2.09)
    r2 = hyp(dx, dy) - 1.5
    dx, dy = x - 3.4 * np.cos(a + 4.19), (y + 2.2) - 2.4 * np.sin(a + 4.19)
    r3 = hyp(dx, dy) - 1.5
    d = np.minimum(np.minimum(r1, r2), r3)
    b.add(rd(d * .8, np.abs(z) - 22, .2), SC_FLOW)
    return b


def conduit_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    m = a.ids == SC_FLOW
    w = fbm(a.p[m] * np.array((.5, .5, .17), F), 4)
    arc = np.exp(-(((w - .5) / .015) ** 2))
    a.glow[m] = np.array((1, .4, .05), F) * (.42 + .3 * a.large[m])[:, None] + np.array((1, .84, .5), F) * arc[:, None]
    # Hazard stripes above and below the housing.
    front = a.n[:, 1] < -.6
    band = ((np.abs(np.abs(z) - 42.5) < 1.5) & (np.abs(x) < 22) & (a.ids == SC_PAINT) & front).astype(F)
    stripe = ((x + z) % 6) < 3
    a.layer(band * stripe * (a.wear < .4), (.8, .52, .05))
    a.layer(band * ~stripe * (a.wear < .4), (.06, .06, .065))
    panel = front & (a.ids == SC_PAINT)
    ink = text_plane(a.p, panel, 'BUS 4-C', (-23.2, -7, 25), (1, 0, 0), (0, 0, 1), 1.7, .13) * 0
    a.layer(ink, (.08, .08, .09))
    for sign in (-1, 1):
        ink = text_plane(a.p, panel, 'HIGH CHARGE', (-6.8 if sign > 0 else -6.8, -7.2, 21.9 if sign > 0 else -23), (1, 0, 0), (0, 0, 1), .62, .11)
        a.layer(ink, (.09, .09, .1))


prop('conduit', 'SM_Scan_Conduit', 'ScanConduit', conduit_body, conduit_glow, ((-31, -9, -61), (31, 9, 61)), .09, 60000, SC_LOOK, conduit_paint,
     scale=3.5, grime=1.1, cage=.2, ao=10., curve=.2, views=((-70, 10, 1), (-120, 25, 1), (-90, 0, .42, (0, -7, 0))))


def terminal_body(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    m = np.stack((ax, y, z), 1)
    b = Build(p)
    # Back frame and side rails.
    b.add(box(p, (0, 6, 0), (28, 1.5, 59), .6), SC_PLATE)
    b.add(rd(box(m, (25.5, 2, 0), (3, 5.5, 55), 1), 0 * x - 1e3, 0), SC_PAINT)
    s = np.abs(repeat(z, 7, -45, 45))
    b.cut(np.maximum.reduce((s - 1.7, np.abs(ax - 25.5) - 1, y + 3.8)), SC_METAL)
    # Main body: slopes out toward the keys so the screen tips up to the viewer.
    v = rotate(p, 0, 7, (0, 0, 20))
    head = box(v, (0, 1.6, 20), (22.4, 5.4, 32), 1.4)
    b.add(head, SC_PAINT)
    # Hood.
    hood = rotate(p, 0, -24, (0, -3, 49))
    b.blend(box(hood, (0, -1.4, 52), (23.4, 6.2, 2.1), 1.2), SC_PLATE, 1.5)
    b.add(np.maximum(box(hood, (0, -5.8, 50.2), (23.2, 1.8, .55), .3), -1e3 + 0 * x), SC_METAL)
    # Screen bay.
    bay = box(v, (0, -3.8, 20), (20, 1.8, 27), 1)
    b.cut(bay, SC_RUBBER)
    # Heavy bezel with corner gussets.
    b.add(np.maximum(box(v, (0, -4.1, 20), (20.8, .9, 27.8), .5), -box(v, (0, -4.2, 20), (19, 2.4, 26), .6)), SC_PLATE)
    for sx in (-1, 1):
        for sz in (-1, 1):
            c = (sx * 19.3, -4.6, 20 + sz * 26.3)
            b.add(box(v, c, (1.7, .55, 1.7), .3), SC_METAL)
    # Soft keys along the screen edge.
    s = np.abs(repeat(z, 7.5, 2, 40))
    b.add(np.maximum(rd(np.abs(ax - 20.2 - 2.0 + 2) - .9, s - 2.4, .3) + 0 * x, np.abs(v[:, 1] + 4.6) - .6) + 1e3 * 0, SC_KEY) if False else None
    # Control deck, angled, with key rows.
    d = rotate(p, 0, -38, (0, -2, -18))
    deck = box(d, (0, -2, -24), (22.4, 6, 11.4), 1.2)
    b.blend(deck, SC_PLATE, 1.5)
    well = box(d, (-5.5, -8.6, -24), (15, 1.1, 9), .6)
    b.cut(well, SC_RUBBER)
    u = repeat(d[:, 0], 3.3, -18.6, 7.8)
    w = repeat(d[:, 2], 3.2, -29.8, -18.2)
    key = rd(rd(np.abs(u) - 1.4, np.abs(w) - 1.35, .3), d[:, 1] + 7.5 + .12 * 0, .3)
    key = np.maximum(key, -(d[:, 1] + 8.1))
    b.add(key, SC_KEY)
    # Dial and big confirm key on the right of the deck.
    b.add(chamfer_cyl(d, (15.8, -8.1, -19.6), 1, 3.1, 1.4, .3), SC_METAL)
    t = np.abs(polar(d[:, 0] - 15.8, d[:, 2] + 19.6, 28)[1])
    b.cut(np.maximum.reduce((t - .13, 2.8 - hyp(d[:, 0] - 15.8, d[:, 2] + 19.6), d[:, 1] + 8.6 - .5)), SC_RUBBER)
    b.add(chamfer_cyl(d, (15.8, -8.3, -29), 1, 2.1, .9, .3), SC_KEY)
    b.cut(np.maximum(np.abs(hyp(d[:, 0] - 15.8, d[:, 2] + 29) - 1.6) - .15, d[:, 1] + 8.9 + .6 * 0 + .1 - .4), SC_LAMP)
    # Lower cowl and cable run.
    b.add(rd(box(p, (0, 1.5, -50), (20, 5.2, 8), 1.4), 0 * x - 1e3, 0), SC_PLATE)
    for c in (-14, -7, 0, 7, 14):
        pts = bezier((c, 2, -60), (c, 2, -52), (c * .6, .1, -46), (c * .6, .1, -38), 6)
        b.add(tube(p, pts, 1.7 if c else 2.3), SC_RUBBER)
    b.cut(box(p, (0, -3, -50), (16.5, 1.6, 5.4), .6), SC_RUBBER)
    for sx in (-1, 1):
        b.add(np.maximum(box(np.stack((x - sx * 8, y, z), 1), (0, -3.6, -50), (6.6, .8, 3.8), .6), 0 * x - 1e3), SC_PAINT)
    # Status lamps over the hood line.
    s = np.abs(repeat(x, 3.2, -13, 13))
    b.cut(np.maximum.reduce((s - 1, np.abs(v[:, 2] - 48.3) + 0 - .34, v[:, 1] + 3.6)), SC_LAMP)
    return b


def terminal_glow(p):
    v = rotate(p, 0, 7, (0, 0, 20))
    b = Build(p)
    b.add(box(v, (0, -2.6, 20), (19.8, .9, 26.8), .4), SC_SCREEN)
    return b


def screen_ui(u, w):
    """Station interface, drawn in screen space: u across 0..40, w up 0..54."""
    cool = np.array((.55, .8, 1), F)
    gold = np.array((1, .62, .16), F)
    col = np.zeros(u.shape + (3,), F)
    col += np.array((.008, .03, .05), F)
    col += np.array((.01, .06, .09), F) * ((np.abs(u - 20) + np.abs(w - 27)) * -.02 + 1)[..., None]
    # Grid.
    grid = (np.abs(((u + .25) % 5) - .25) < .05) | (np.abs(((w + .25) % 5) - .25) < .05)
    col += cool * grid[..., None] * .05
    # Ring and bolt emblem, top centre.
    r = hyp(u - 20, w - 37)
    ring = np.abs(r - 8) < .22
    ring2 = (np.abs(r - 9.5) < .08) & (((np.arctan2(w - 37, u - 20) * 9) % 1) < .7)
    col += gold * (ring | ring2)[..., None] * 1.1
    # Sweep of a scope inside the ring.
    t = np.arctan2(w - 37, u - 20)
    sweep = ((t + 2) % (2 * math.pi)) / (2 * math.pi)
    col += cool * ((r < 7.8) * sweep ** 6)[..., None] * .55
    # Waveform.
    wave = 13.5 + 2.6 * np.sin(u * 1.1) * np.sin(u * .23 + 1) + .7 * np.sin(u * 4.1)
    line = np.exp(-((w - wave) / .16) ** 2) * ((u > 4) & (u < 36))
    col += cool * line[..., None] * 1.0
    col += cool * ((w < wave) & (w > 9) & (u > 4) & (u < 36))[..., None] * .06
    # Bar columns.
    for i in range(9):
        cx = 7 + i * 3.25
        top = 4.8 + 2.4 * abs(math.sin(i * 1.7 + .4))
        on = (np.abs(u - cx) < 1) & (w > 3) & (w < top)
        col += (gold if i == 5 else cool)[None] * on[..., None] * .7
    return col


def terminal_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    v = rotate(a.p, 0, 7, (0, 0, 20))
    m = a.ids == SC_SCREEN
    u, w = 20 - v[m, 0] * -1, v[m, 2] + 7
    a.glow[m] = screen_ui(u, w)
    a.base[m] = np.array((.015, .03, .04), F)
    # Readable text lines on the screen; drawn on the glass plane.
    front = np.ones(m.sum(), bool)
    q = np.stack((u, 0 * u, w), 1)
    for text, ox, oz, h, colour in (('MERIDIAN STATION', 4.5, 47.5, 1.5, (.65, .88, 1)), ('POWER GRID  NOMINAL', 4.5, 25, .95, (.65, .88, 1)), ('DIVINITY  NO SIGNAL', 4.5, 22.6, .95, (1, .6, .16))):
        ink = text_plane(q, front, text, (ox, 0, oz), (1, 0, 0), (0, 0, 1), h, .1)
        a.glow[m] = a.glow[m] + ink[:, None] * np.array(colour, F)
    # Key legends: a small tick on each key.
    d = rotate(a.p, 0, -38, (0, -2, -18))
    m = a.ids == SC_KEY
    uu = repeat(d[:, 0], 3.3, -18.6, 7.8)
    ww = repeat(d[:, 2], 3.2, -29.8, -18.2)
    tick = (np.abs(uu) < .55) & (np.abs(ww - .4) < .12) & m
    a.glow[tick] = (.8, .55, .2)
    a.base[tick] = (.8, .75, .6)
    front = a.n[:, 1] < -.55
    # Hazard on the lower cowl edge.
    band = ((np.abs(z + 58) < 1.2) & (a.ids == SC_PLATE)).astype(F)
    a.layer(band * (((x + z) % 5) < 2.5) * (a.wear < .4), (.8, .52, .05), .42, 0)
    panel = front & (a.ids == SC_PLATE)
    ink = text_plane(a.p, panel, 'TERMINAL 12', (-13, -6, 54.2), (1, 0, 0), (0, 0, 1), 1.2, .12) * 0
    a.layer(ink, (.8, .78, .7))
    ink = text_plane(a.p, front & (a.ids == SC_PAINT), 'M-12', (-23.8, 0, 56) if False else (22.6, 0, -40), (0, 0, 1), (-1, 0, 0), 1.3, .12) * 0
    a.layer(ink, (.1, .1, .1))


prop('terminal', 'SM_Scan_Terminal', 'ScanTerminal', terminal_body, terminal_glow, ((-30, -14, -61), (30, 9, 61)), .08, 50000, SC_LOOK, terminal_paint,
     scale=3.5, grime=1.1, cage=.2, ao=10., curve=.18, views=((-70, 8, 1), (-125, 20, 1), (-90, 2, .4, (0, -6, 28))))


