# ---------------------------------------------------------------- training drone

DR_SHELL, DR_GREY, DR_FRAME, DR_RUBBER, DR_METAL, DR_LAMP, DR_HOT, DR_EYE = 1, 2, 3, 4, 5, 6, 7, 8
DRONE = {}
HUB = Shape([(0, 2.6), (2.0, 2.6, .5), (3.6, 1.2, .7), (3.1, -4.5, 1), (1, -7.0, .6), (0, -7.2)], step=.04, pad=3)
DRONE_TILT = -12


def drone_shapes():
    return once(DRONE, lambda: dict(
        plan=Shape([(34, -3), (34, 8.5), (18, 21, 2), (-6, 24, 3), (-30, 13, 1.5), (-36.5, 7, .8), (-36.5, -3)], step=.05, pad=3),
        side=Shape([(34.5, 7.5), (23, 14.5, 3), (3, 19.5, 6), (-24, 14, 3), (-36.5, 8, 1), (-36.5, -3, 1), (-12, -14.5, 3), (18, -13.5, 3), (34.5, -6, 1)], step=.05, pad=3),
        duct=Shape([(8.5, 5.0), (9.7, 6.2, .5), (11.3, 5.6, .8), (11.5, 1.5, .9), (11.2, -3.6, .6), (10.1, -5.4, .4), (8.3, -5.0), (8.0, 0)], step=.04, pad=3),
        fin=Shape([(-31, 7), (-13, 12), (-31, 24, .4), (-37, 25, .3)], .3, step=.05, pad=3),
        arm=Shape([(10, 12), (3, 26, 1), (-.5, 32), (-14, 32), (-20, 24, 1), (-24, 12)], .6, step=.05, pad=3)))


def drone_hull(p):
    g = drone_shapes()
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ay = np.abs(y)
    d = smax(g['plan'](x, ay), g['side'](x, z), .5)
    d = smax(d, ay * .62 + (z - 5) * .78 - 16.5, .5)
    return smax(d, ay * .6 - (z - 5) * .8 - 15.5, .5)


def drone_body(p):
    g = drone_shapes()
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ay = np.abs(y)
    m = np.stack((x, ay, z), 1)
    b = Build(p)
    hull = drone_hull(p)

    # Chassis under the armour.
    b.add(hull + 2, DR_FRAME)
    seam = z + 2 - .06 * x                      # armour stops here
    above = -seam
    # Spine runs nose to tail, stepped below the shoulders.
    spine = rd(rd(ay - 5.6 - .06 * np.maximum(10 - x, 0), np.abs(x + 7) - 21, .4), -above, .3)
    b.add(rd(hull + .55, spine, .3), DR_GREY)
    # Shoulders are the raised bone-white mass.
    front = x - 15 + ay * .55
    rear = -12 - x + ay * .3
    shoulder = rd(rd(front, rear, .4), np.maximum(6.9 + .06 * np.maximum(10 - x, 0) - ay, -above), .4)
    b.add(rd(hull - .75, shoulder, .35), DR_SHELL)
    # Rear quarter plates.
    tail = rd(rd(-rear + 1.1, np.maximum(6.9 - ay, -above), .3), -35 - x, .3)
    b.add(rd(hull + .2, tail, .3), DR_GREY)
    # Cowl wraps the nose and overhangs the eye.
    cowl = rd(-front + 1.1, -above, .3)
    b.add(rd(hull + .35, cowl, .3), DR_SHELL)
    # Lower skirt.
    skirt = np.maximum.reduce((seam + 1.0, -z - 11, x - 13, -15 - x))
    b.add(rd(hull + .7, skirt, .3), DR_GREY)
    # Shoulder relief: a recessed access panel and four cooling louvres.
    b.cut(np.maximum(box(m, (0, 16, 0), (7, 4.4, 40), 1), -hull - 1.2))
    t = rotate(m, 1, -22, (-7, 18, 8))
    s = np.abs(repeat(t[:, 0], 2.1, -10, -4))
    b.cut(np.maximum.reduce((s - .55, np.abs(t[:, 2] - 12) - 5, 12 - ay, -hull - 2.2)), DR_METAL)
    # Fasteners at shoulder corners.
    for c in ((8.4, 10, 15), (-9.4, 10.6, 16.3), (5, 20.5, 8.7), (-10.5, 23.5, 5.2)):
        b.add(np.maximum(sphere(m, c, 1.05), 0 * x - 1e3), DR_METAL)

    # Chassis vent band between skirt and armour.
    s = np.abs(repeat(x, 2.6, -14, 12))
    b.cut(np.maximum.reduce((s - .7, np.abs(seam + .1) - .6, 8 - ay, -hull - 3.2)), DR_METAL)

    # Eye: a flat-topped socket under the brow, so it glares.
    socket = np.maximum(chamfer_cyl(p, (34, 0, 1), 0, 10.6, 8.5, 0), z - 8.2)
    b.cut(socket - np.maximum(x - 31.5, 0) * .5, DR_METAL)
    brow = rotate(p, 1, 8, (30, 0, 9))
    b.add(rd(hull - .7, np.maximum.reduce((8.4 - brow[:, 2], ay - 12.2, 19 - x)), .4), DR_SHELL)
    v = rotate(np.stack((x - 27, y, z - 1), 1), 0, 12)
    u_, v_ = polar(v[:, 1], v[:, 2], 10)
    b.add(np.maximum.reduce((np.abs(u_ - 8.6) - 2.3, np.abs(v_ + (u_ - 8.6) * .6) - 1.3, np.abs(x - 27) - .5)), DR_METAL)
    # Sensor slits flanking the socket.
    b.cut(np.maximum.reduce((np.abs(ay - 14) - .7, np.abs(z - 2) - 2.2, 26 - x, -hull - .6)), DR_LAMP)

    # Armoured arms out to the nacelles.
    arm = rd(g['arm'](x, ay), np.abs(z + 1 + (ay - 14) * .12) - 3.6, .9)
    b.add(arm, DR_FRAME)
    b.add(rd(rd(g['arm'](x, ay) + 1.2, np.abs(z - 2.8 + (ay - 14) * .12) - .7, .3), 22 - ay + 0 * x, .2), DR_GREY)

    # Thrust nacelles, canted outward.
    c = (-7, 33.5, -1)
    t = rotate(m, 0, DRONE_TILT, c)
    n = t - np.array(c, F)
    radial = hyp(n[:, 0], n[:, 1])
    u_, v_ = polar(n[:, 0], n[:, 1], 5, .4)
    stator = np.maximum.reduce((np.abs(v_) - .55, u_ - 9.4, 2.1 - u_, np.abs(n[:, 2] + 3.5) - 1.4))
    u_, v_ = polar(n[:, 0], n[:, 1], 9)
    rotor = np.maximum.reduce((np.abs(v_ + (u_ - 6) * .14 + n[:, 2] * .35) - .28, u_ - 8.1, 2.1 - u_, np.abs(n[:, 2] - .8) - 1.1))
    b.add(np.minimum(stator, lathe(HUB, t, c)), DR_METAL)
    b.add(rotor, DR_METAL)
    arm_cut = -(radial - 9.8)
    b.d = np.maximum(b.d, np.minimum(arm_cut, np.where(radial < 9.8, 1e3, 1e3)) * 0 + np.where((np.abs(n[:, 2]) < 7) & (radial < 8.1) & (b.id != DR_METAL), 2., -1e3))
    b.add(lathe(g['duct'], t, c), DR_SHELL)
    b.cut(np.maximum(np.abs(radial - 11.5) - .12, np.abs(n[:, 2] - 1.6) - .45) - .1, DR_LAMP)
    # A hood covers the inner half of the intake, like a brow.
    hood = rd(rd(radial - 12.1, np.abs(n[:, 2] - 6.8) - .85, .3), n[:, 1] + 2.4 + n[:, 0] * .22, .4)
    b.add(hood, DR_GREY)
    b.add(rd(rd(radial - 7.6, np.abs(n[:, 2] - 7.4) - .22, .1), n[:, 1] + 2.8 + n[:, 0] * .22, .1) + 0 * x, DR_METAL)
    # Hydraulic strut under each arm.
    b.add(capsule(m, (8, 11, -11), (-1, 24, -5.2), 1.05), DR_METAL)
    b.add(capsule(m, (8, 11, -11), (4.6, 16.2, -8.9), 1.85), DR_FRAME)

    # Twin cannons slung under the shoulders.
    b.blend(box(m, (12, 13, -9.4), (10.5, 3.8, 3.7), .9), DR_FRAME, 1)
    b.add(chamfer_cyl(m, (26, 13, -9.6), 0, 1.4, 15.4, .15), DR_METAL)
    b.add(chamfer_cyl(m, (25, 13, -9.6), 0, 2.2, 2.6, .3), DR_FRAME)
    b.add(chamfer_cyl(m, (39.4, 13, -9.6), 0, 2.05, 2, .25), DR_FRAME)
    b.cut(cyl(m, (41.4, 13, -9.6), 0, .95, 2.6), DR_RUBBER)
    s = repeat(x, 1.1, 38.1, 40.3)
    b.cut(np.maximum.reduce((np.abs(s) - .24, np.abs(ay - 13) - 3, np.abs(z + 9.6) - .55)), DR_RUBBER)

    # Rear drive pair.
    b.add(rd(hyp(m[:, 1] - 6.8, z - 3) - 4.6, np.abs(x + 35.5) - 4.4, .5), DR_FRAME)
    b.cut(cyl(m, (-40, 6.8, 3), 0, 3.5, 3.1), DR_METAL)
    u_, v_ = polar(m[:, 1] - 6.8, z - 3, 6)
    b.add(np.maximum.reduce((np.abs(v_) - .18, u_ - 3.5, np.abs(x + 38.4) - 1)), DR_METAL)

    # Tail blades, swept and canted apart.
    fin = rotate(m, 0, -24, (0, 7, 7))
    b.blend(rd(g['fin'](fin[:, 0], fin[:, 2]), np.abs(fin[:, 1] - 7) - .85, .45), DR_SHELL, .7)
    # Dorsal sensor block and mast.
    r = rotate(p, 1, 4)
    b.blend(box(r, (-10, 0, 19.6), (6.5, 2.3, 1.9), .7), DR_FRAME, .7)
    b.cut(box(r, (-10, 0, 21.4), (4.6, 1.1, .4), .2), DR_LAMP)
    b.add(capsule(p, (-15, 0, 20), (-23, 0, 33), .3), DR_METAL)
    return b


def drone_glow(p):
    b = Build(p)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    b.add(sphere(p, (18.2, 0, 1), 9.8), DR_EYE)
    m = np.stack((x, np.abs(y), z), 1)
    t = rotate(m, 0, DRONE_TILT, (-7, 33.5, -1))
    b.add(chamfer_cyl(t, (-7, 33.5, -3.6), 2, 9.3, .22, .05), DR_HOT)
    b.add(cyl(m, (-37.6, 6.8, 3), 0, 3.7, .3), DR_HOT)
    return b


DRONE_LOOK = {
    DR_SHELL: dict(base=(.68, .66, .6), rough=.4, metal=0, finish='ceramic', tone=.13, rough_var=.16,
                   chip=dict(base=(.24, .24, .25), rough=.42, metal=.9), edge_a=.45, edge_b=1.2, chip_amount=.95, scuff=.16),
    DR_GREY: dict(base=(.2, .22, .25), rough=.48, metal=.15, finish='cast', tone=.2,
                  chip=dict(base=(.48, .48, .47), rough=.34, metal=1), edge_a=.45, edge_b=1.2, chip_amount=.9, scuff=.15),
    DR_FRAME: dict(base=(.11, .115, .125), rough=.44, metal=.85, finish='cast', tone=.2,
                   chip=dict(base=(.5, .5, .48), rough=.34, metal=1), edge_a=.5, edge_b=1.3, chip_amount=.7, scuff=.05),
    DR_RUBBER: dict(base=(.05, .05, .055), rough=.72, metal=0, finish='cast'),
    DR_METAL: dict(base=(.42, .42, .43), rough=.34, metal=1, finish='brushed', along=(1, 0, 0), tone=.14),
    DR_LAMP: dict(base=(1, .3, .08), rough=.3, metal=0, glow=(1, .24, .04)),
    DR_HOT: dict(base=(1, .45, .15), rough=.4, metal=0, glow=(1, .4, .1)),
    DR_EYE: dict(base=(.8, .08, .03), rough=.08, metal=0, glow=(1, .1, .02)),
}


def drone_paint(a):
    x, y, z = a.p[:, 0], a.p[:, 1], a.p[:, 2]
    ay = np.abs(y)
    m = a.ids == DR_EYE
    r = hyp(y[m], z[m] - 1)
    a.glow[m] = (np.array((.9, .04, .01), F) * (.35 + .55 * ramp(r, 7.5, 2))[:, None]
                 + np.array((1, .5, .22), F) * ramp(r, 2.6, .8)[:, None]
                 + np.array((1, .14, .03), F) * (np.abs(((r / 1.15) % 1) - .5) < .06)[:, None] * .3)
    a.base[m] = np.array((.2, .02, .01), F)
    m = a.ids == DR_HOT
    a.glow[m] = np.array((1, .3, .05), F) * (.5 + .4 * a.large[m])[:, None]
    painted = (a.wear < .5)[:, None] * 1.
    # Orange training flash: two chevrons on each shoulder, a band on each hood.
    q = (x + ay * .55 - 15) * -1
    flash = (np.abs(q - 2.2) < .9) | (np.abs(q - 4.6) < .4)
    mask = (flash & (a.ids == DR_SHELL) & (x > -14) & (x < 15)).astype(F) * a.wear.__lt__(.5)
    a.layer(mask, (.8, .29, .05), .42, 0)
    n = rotate(np.stack((x, ay, z), 1), 0, DRONE_TILT, (-7, 33.5, -1)) - np.array((-7, 33.5, -1), F)
    radial = hyp(n[:, 0], n[:, 1])
    rim = (a.ids == DR_SHELL) & (radial > 8.8) & (n[:, 2] > 2.5) & (radial < 11)
    stripe = ((np.arctan2(n[:, 1], n[:, 0]) * 14 / (2 * math.pi) + radial * .1) % 1) < .5
    a.layer((rim & stripe).astype(F) * (a.wear < .5), (.09, .09, .095), .45, 0)
    a.layer((rim & ~stripe).astype(F) * (a.wear < .5), (.8, .52, .05), .45, 0)
    top = (a.n[:, 2] > .4) & np.isin(a.ids, (DR_SHELL, DR_GREY))
    for sign, ox, oy in ((-1, -9.5, -13.4), (1, 8.5, 13.4)):
        u, v = (-sign, 0, 0), (0, -sign, 0)
        ink = text_plane(a.p, top & (np.sign(y) == sign), 'TRN-07', (ox, oy, 0), u, v, 2.7, .13)
        a.layer(ink * (a.wear < .5), (.09, .09, .1))
        ink = text_plane(a.p, top & (np.sign(y) == sign), 'MERIDIAN DEFENSE', (ox, oy + sign * -.0 + (2 if sign < 0 else -2) * -1, 0), u, v, .8, .1)
        a.layer(ink * (a.wear < .5), (.09, .09, .1))
    impacts = np.random.default_rng(5).uniform((-30, -24, -5), (24, 24, 20), (14, 3))
    for c in impacts:
        d = hyp(x - c[0], y - c[1], z - c[2])
        s = ramp(d, 2.4, .4) * (a.glow.sum(1) == 0)
        scorch = s * ramp(a.medium + (a.fine - .5) * .8, .35, .6)
        a.base = a.base * (1 - scorch[:, None] * .75) + np.array((.04, .036, .03), F) * scorch[:, None] * .75
        a.rough = np.clip(a.rough + scorch * .2, 0, 1)
        a.metal = a.metal * (1 - scorch)


prop('drone', 'SM_Drone', 'Drone', drone_body, drone_glow, ((-42, -47, -18), (44, 47, 36)), .07, 110000, DRONE_LOOK, drone_paint,
     scale=4., cage=.3, ao=12., curve=.2, views=((-35, 18, 1), (32, 6, 1), (150, 28, 1), (-90, 62, 1), (0, 2, .5, (30, 0, -2)), (-125, -28, 1)))


# ---------------------------------------------------------------- pickups
