SEED_HUSK, SEED_DARK, SEED_VEIN, SEED_CRYSTAL = 1, 2, 3, 4
SEED = {}


def seed_shape():
    return once(SEED, lambda: dict(
        husk=Shape([(-1, 22.6), (.8, 22.4, .4), (2, 19.5, 1.5), (6.5, 13.5, 3), (11.8, 4, 4), (12.6, -3, 4), (9.4, -12.6, 3), (3.6, -18, 1.5), (-1, -19.6)], step=.03, pad=4)))


def seed_warp(p):
    s = p.copy()
    s[:, 0] += .8 * np.sin(p[:, 2] * .17 + 1)
    s[:, 1] += .6 * np.sin(p[:, 2] * .13 + 2.5)
    return s


def seed_body(p):
    g = seed_shape()
    s = seed_warp(p)
    x, y, z = s[:, 0], s[:, 1], s[:, 2]
    r = np.maximum(hyp(x, y), .5)
    a = np.arctan2(y, x)
    turn = a + z * .075 + .2 * np.sin(z * .2)
    b = Build(p)
    outer = lathe(g['husk'], s)
    # Five leaves spiral up the seed, parting mid body and closing at both tips.
    span = math.pi / 5
    phi = np.abs(((turn + span) % (2 * span)) - span)   # 0 at leaf centre, span at the slit
    arc = phi * r
    open_ = ramp(z, -16, -3) * ramp(z, 18, 6)
    half = span * r - (.1 + 2.7 * open_)
    gap = arc - half
    belly = (phi / span) ** 2 * 1.5                      # each leaf swells like a bud scale
    surface = outer + belly
    husk = smax(smax(surface, -surface - 2.6, .3), gap, .45)
    # A raised midrib on each leaf, with side veins branching from it.
    husk = smin(husk, smax(surface - .34 + np.minimum(arc, 1) * .34, np.abs(phi) * r - .55, .3), .35) * 1
    b.add(husk * .8, SEED_HUSK)
    # Light seams run just inside the leaf margins.
    wob = .13 * np.sin(z * 2.1 + a * 5) + .08 * np.sin(z * 5.3 + a * 3)
    b.cut(np.maximum(np.abs(gap + .55 + wob) - .15, surface + .12) * .8, SEED_VEIN)
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
