"""The elemental monsters: new bodies, built from nothing (not the air-swimmers' plans).

Author, 2026-11-17: "We need new VERY impressive designs. AAA quality. We also want more than 6 enemies. We need AT THE
VERY least monster designs based on lions, dragons, mantises, elephants, frogs, angels and demons", each with a
physical attack and an element (fire, ice, thunder, wind, dark, light; Tools/blueprint_logic/elements.py).

  SM_AE_PyreLion      2.9 m long    fire      a lion whose mane and tail tuft burn
  (the others are added below as they are built)

Pure numpy on creatures.py's tools (Body, pipe, membrane, spike, Rig, Pose). Every builder stands the animal on the
ground at z 0 facing +x, fits it to its length ('centre' pivot, like the air-swimmers) and leaves part.rig with two
animations: 'Swim' (the name the game plays in a loop: here the animal's prowl or hover) and 'Strike' (1.3 s, the blow
landing at about 0.68 s). In play each is a BP_TrainingDrone with Organic, Animal 5 (the body's rear and lunge), Reach
and Element.

    P=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages
    PYTHONPATH=$P python3 Tools/arche_meshes/check.py monsters --preview
"""
from creatures import *   # noqa: F401,F403  (the modelling and rigging tools, and kit's through it)


def c3(r, g, b):
    return np.array([r, g, b], np.float64)


BONE_W = c3(.62, .58, .50)
BLACK = c3(.012, .012, .014)


def limb(p, rg, prefix, parent, joints, radii, colour, host, sides=10, n=40, slot=SKIN, lead=.45):
    """A muscled limb through `joints` (shoulder, elbow, wrist, foot ...). radii: [(t, metres), ...] along it;
    colour(t) -> colours along it. One bone a segment, blended out of the body it grows from. Returns the path, the
    bone names and the first vertex."""
    joints = [np.asarray(j, np.float64) for j in joints]
    path = curve(joints, n)
    t = np.linspace(0, 1, n)
    start = pipe(p, path, prof(radii, t, False), colour(t), slot, sides, caps=(.3, .6))
    at = [int(np.argmin(norm(path - j, axis=1))) for j in joints]
    names = rg.chain(prefix, parent, path[at])
    rg.bind_proj(start, len(p.v), path[at], names, ('stick', host), lead=lead)
    return path, names, start


def claws(p, at, forward, count, length, spread, colour0, colour1, down=.35, radius=None):
    """Claws (or hooves' cleats) fanned across a foot."""
    forward = unit(forward)
    side = unit(np.cross(forward, V(0, 0, 1)))
    for k in range(count):
        q = (k - (count - 1) / 2) / max(count - 1, 1)
        d = unit(forward + side * q * spread * 1.4 + V(0, 0, -down))
        base = np.asarray(at, np.float64) + side * q * spread
        spike(p, base - d * length * .2, base + d * length, radius or length * .16, colour0, colour1, ROCK, 5, .7)


def horn(p, base, direction, length, radius, colour0, colour1, bend=(0, 0, 0), n=14, sides=7, twist=0.0):
    """A curved horn or tusk: it leaves base along direction and is drawn toward `bend` as it goes."""
    d, pts, q = unit(direction), [np.asarray(base, np.float64)], np.asarray(base, np.float64)
    for i in range(1, n):
        d = unit(d + np.asarray(bend, np.float64) * (1.6 / n))
        q = q + d * length / (n - 1)
        pts.append(q.copy())
    t = np.linspace(0, 1, n)
    r = radius * (1 - t) ** .75 + radius * .04
    r = r * (1 + .06 * np.sin(t * 60)) if twist else r
    start = pipe(p, np.array(pts), r, lit(mx(colour0, colour1, t ** 1.4), 1.0), ROCK, sides, caps=(.2, .9))
    p.rg.ride(start, base)
    return np.array(pts)


def fangs(p, rng, jaw, th, sign, ts, lengths, colour0, colour1, lean=-.25, radius=.012):
    """Teeth along a jaw Body's edge at spine fractions ts on both sides."""
    for side in (1, -1):
        for t, ln in zip(ts, lengths):
            P, N = jaw.at(t, th if side > 0 else PI - th)
            i = int(t * (jaw.n - 1))
            d = unit(jaw.U[i] * sign + jaw.S[i] * side * .10 + jaw.T[i] * lean)
            spike(p, P - d * ln * .25, P + d * ln, radius * (ln / .05) ** .5, colour0, colour1, ROCK, 5, .8)


def flames(p, rng, points, normals, sweep, lengths, hot, mid, cold, lift=.9, sides=4, slot=GLOW, wobble=.35):
    """Tongues of flame (a mane, a tuft, a crest) rooted at points: each leans along its normal, `sweep` and up,
    bright at the root and dark red at the tip."""
    for P, N, ln in zip(points, normals, lengths):
        d = unit(np.asarray(N, np.float64) * .55 + np.asarray(sweep, np.float64) + V(0, 0, lift) * rng.uniform(.4, 1.0) + rng.normal(0, wobble, 3) * .5)
        mid_pt = P + d * ln * .5 + rng.normal(0, .25, 3) * ln * .25
        tip = P + d * ln + V(0, 0, ln * .25)
        # two stacked tongues so the flame bends
        spike(p, P - d * ln * .08, mid_pt, ln * rng.uniform(.11, .16), light(hot, 1.0), light(mid, .95), slot, sides, .5)
        spike(p, P + d * ln * .28, tip, ln * rng.uniform(.07, .10), light(mid, .95), light(cold, .7), slot, sides, .7)


# ================================================================ SM_AE_PyreLion

def pyre_lion():
    """SM_AE_PyreLion (2.9 m long, 1.7 m to the top of the mane): a great lion, mid-stride, head low and forward and
    jaws parted on four long fangs. Deep chest, tucked waist, heavy shoulders; a charred hide over a tawny belly with
    seams of ember glowing along the spine and down the shoulders; eyes like coals. Its mane is fire: hundreds of
    tongues of flame from the crown, round the neck and down the chest, swept back as it moves; the tuft of its tail
    burns too, and embers light the backs of its legs."""
    rng = np.random.default_rng(7101)
    p = Part('SM_AE_PyreLion', (SKIN, ROCK, GLOW))
    rg = Rig(p)
    CHAR, EMBER_HIDE, TAWNY = c3(.050, .030, .022), c3(.16, .07, .03), c3(.50, .33, .17)
    HOT, MID, COLD = c3(1.0, .86, .35), c3(1.0, .42, .06), c3(.70, .08, .02)
    # ---- trunk: chest to rump
    b = Body([V(.62, 0, 1.06), V(.40, 0, 1.04), V(.05, .01, 1.00), V(-.38, .02, .98), V(-.74, .02, 1.00), V(-.98, .01, .94)], 70, 32,
             ry=[(0, .25), (.12, .33), (.3, .31), (.52, .24), (.74, .28), (.9, .24), (1, .12)],
             up_r=[(0, .23), (.12, .28), (.3, .24), (.52, .19), (.74, .23), (.9, .21), (1, .11)],
             dn_r=[(0, .30), (.12, .42), (.3, .40), (.52, .25), (.74, .28), (.9, .24), (1, .11)])
    ribs = .010 * np.sin(b.TT * 95) * smooth(.14, .2, b.TT) * (1 - smooth(.46, .52, b.TT)) * (np.abs(np.cos(b.TH)) > .35)
    shoulder = .035 * np.exp(-((b.TT - .14) / .08) ** 2) * np.exp(-((np.abs(b.TH - PI / 2) - 1.05) / .5) ** 2)
    haunch = .04 * np.exp(-((b.TT - .78) / .09) ** 2) * np.exp(-((np.abs(b.TH - PI / 2) - 1.15) / .55) ** 2)
    b.push(ribs + shoulder + haunch + .006 * mottle(b.G, .09, 5))
    c = rgb(hide(b.G, b.N, mx(CHAR, EMBER_HIDE, .35), TAWNY, 11, .22, .22, -.5, .25))
    b.add(p, lit(c, 1.0), caps=(.5, .6))
    rg.bone('Chest', 'Root', b.cp(.34), b.cp(.08))
    back_ts = (.34, .58, .82, 1.0)
    back = [rg.bone('Spine', 'Chest', b.cp(.34), b.cp(.58)), ]
    back.append(rg.bone('Hips', 'Spine', b.cp(.58), b.cp(1.0)))
    vt = b.vt()
    rg.bind((b.start, b.end), rg.spine_rows(vt, (.34, .58, 1.0), back, {'Chest': 1}))
    host = (b.start, b.end)
    # ---- neck and skull: carried low and forward
    nk = Body([V(.52, 0, 1.10), V(.72, 0, 1.18), V(.90, 0, 1.24), V(1.04, 0, 1.25)], 30, 28,
              ry=[(0, .26), (.5, .23), (1, .21)], up_r=[(0, .24), (.5, .22), (1, .20)], dn_r=[(0, .31), (.5, .26), (1, .21)])
    nk.push(.006 * mottle(nk.G, .08, 6))
    nk.add(p, lit(rgb(hide(nk.G, nk.N, mx(CHAR, EMBER_HIDE, .35), TAWNY, 12, .2, .2, -.5, .25)), 1.0), caps=(.4, .4))
    necks = rg.chain('Neck', 'Chest', [nk.cp(0), nk.cp(.5), nk.cp(1.0)])
    rg.bind((nk.start, nk.end), rg.spine_rows(nk.vt(), (0, .5, 1.0), necks, {'Chest': 1}))
    hinge = V(1.04, 0, 1.17)
    sk = Body([V(.96, 0, 1.27), V(1.12, 0, 1.31), V(1.27, 0, 1.28), V(1.40, 0, 1.21), V(1.46, 0, 1.18)], 34, 28,
              ry=[(0, .21), (.3, .225), (.55, .17), (.8, .145), (1, .11)], up_r=[(0, .19), (.3, .20), (.55, .135), (.8, .105), (1, .08)],
              dn_r=[(0, .12), (.3, .06), (.6, .035), (1, .025)], power=2.8)
    brow = .03 * np.exp(-((sk.TT - .36) / .07) ** 2) * np.exp(-((np.abs(sk.TH - PI / 2) - .75) / .3) ** 2)
    cheek = .025 * np.exp(-((sk.TT - .25) / .12) ** 2) * (np.abs(np.cos(sk.TH)) > .8)
    sk.push(brow + cheek)
    sc = rgb(hide(sk.G, sk.N, mx(CHAR, EMBER_HIDE, .45), TAWNY, 13, .15, .15, -.6, .1))
    sc = np.where((sk.TH < -.25)[..., None] & (sk.TH > -PI + .25)[..., None], c3(.20, .03, .03), sc)       # the roof of the mouth
    sk.add(p, lit(sc, 1.0), caps=(.4, .5))
    jw = Body([hinge + V(-.02, 0, -.04), hinge + V(.14, 0, -.09), hinge + V(.28, 0, -.12), hinge + V(.38, 0, -.12)], 26, 24,
              ry=[(0, .19), (.3, .17), (.7, .14), (1, .10)], up_r=[(0, .03), (.5, .02), (1, .015)], dn_r=[(0, .11), (.3, .10), (.7, .075), (1, .05)], power=2.8)
    jc = rgb(hide(jw.G, jw.N, TAWNY, mx(TAWNY, BONE_W, .4), 14, .15, .12, -.6, .1))
    jc = np.where(((jw.TH > .3) & (jw.TH < PI - .3))[..., None], c3(.30, .04, .04), jc)                    # tongue and gums
    jw.add(p, lit(jc, 1.0), caps=(.3, .5))
    rg.bone('Head', necks[-1], nk.cp(1.0), sk.c[-1])
    rg.bone('Jaw', 'Head', hinge + V(-.02, 0, -.05), jw.c[-1])
    rg.bind((sk.start, sk.end), {'Head': 1})
    rg.bind((jw.start, jw.end), {'Jaw': 1})
    rg.bind((orb(p, hinge + V(.1, 0, -.02), .07, light(MID, 1.0), GLOW, None, 1.0, 2), len(p.v)), {'Head': 1})     # the furnace in its throat
    fangs(p, rng, sk, -.32, -1, (.80, .70, .62, .54, .46), (.13, .05, .045, .04, .04), lit(BONE_W, .8), lit(BONE_W, 1.2))
    fangs(p, rng, jw, .32, 1, (.86, .74, .64, .54), (.10, .045, .04, .04), lit(BONE_W, .8), lit(BONE_W, 1.2))
    for side in (1, -1):
        P, N = sk.at(.40, .95 if side > 0 else PI - .95)
        eye(p, P, unit(N + V(.5, 0, .15)), .028, light(HOT, 1.0), lit(CHAR, .8))
        P, N = sk.at(.1, 1.1 if side > 0 else PI - 1.1)                                                   # round ears
        G = fan(np.array([P + sk.T[3] * q for q in np.linspace(-.05, .05, 7)]), np.array([P + N * .11 + V(0, side * .03, .04) + sk.T[3] * q * .5 for q in np.linspace(-.05, .05, 7)]), 5,
                arch=V(-.02, 0, 0))
        rg.bind((membrane_start(p, G, .014, lit(CHAR, 1.4), lit(TAWNY, .8), SKIN), len(p.v)), {'Head': 1})
    P, N = sk.at(.97, PI / 2)
    rg.bind((orb(p, P + V(.0, 0, -.02), .045, lit(BLACK, 1.0), SKIN, V(1, 0, .2), .7, 2), len(p.v)), {'Head': 1})   # the nose
    # ---- legs, mid-stride: left fore and right hind forward
    def leg_colour(t):
        return lit(mx(mx(CHAR, EMBER_HIDE, .4), mx(CHAR, TAWNY, .5), t), 1 + .06 * np.sin(t * 40))
    legs = []
    for name, parent, side, dx, hind in (('LegFR', 'Chest', 1, -.10, False), ('LegFL', 'Chest', -1, .16, False), ('LegHR', 'Hips', 1, .14, True), ('LegHL', 'Hips', -1, -.12, True)):
        y = side * .25
        if not hind:
            joints = [V(.44, y * .9, .92), V(.36 + dx * .3, y, .56), V(.44 + dx * .8, y, .27), V(.50 + dx, y, .07)]
            radii = [(0, .19), (.2, .19), (.33, .125), (.5, .115), (.66, .085), (.9, .08), (1, .10)]
        else:
            joints = [V(-.76, y * .95, .92), V(-.58 + dx * .3, y * 1.1, .56), V(-.90 + dx * .8, y, .31), V(-.80 + dx, y, .07)]
            radii = [(0, .23), (.2, .22), (.33, .135), (.5, .10), (.66, .075), (.9, .075), (1, .10)]
        path, names, st = limb(p, rg, name, parent, joints, radii, leg_colour, host)
        foot = path[-1] + V(.08, 0, -.01)
        rg.bind((orb(p, foot, .13, lit(mx(CHAR, TAWNY, .35), 1.0), SKIN, V(0, 0, 1), .55, 2), len(p.v)), {names[-1]: 1})
        mark = len(p.v)
        claws(p, foot + V(.08, 0, -.02), V(1, 0, 0), 4, .06, .06, lit(BLACK, 2.0), lit(BONE_W, .9))
        rg.bind((mark, len(p.v)), {names[-1]: 1})
        for k in range(5):                                                                              # embers up the back of the leg
            q = path[int((.2 + .12 * k) * (len(path) - 1))]
            mark = len(p.v)
            spot(p, q + V(-.06, 0, 0), V(-1, 0, .2), .018, light(MID, .9))
            rg.bind((mark, len(p.v)), rg.rows(q[None, :])[0])
        legs.append((names, side, hind))
    # ---- tail and its burning tuft
    tpath, tails, st = limb(p, rg, 'Tail', 'Hips', [V(-.96, 0, .98), V(-1.22, .03, .84), V(-1.44, .08, .56), V(-1.62, .12, .44), V(-1.78, .10, .56), V(-1.86, .06, .74)],
                            [(0, .075), (.3, .05), (1, .038)], lambda t: lit(mx(CHAR, EMBER_HIDE, t), 1.0), host, sides=8, n=44)
    mark = len(p.v)
    tip = tpath[-1]
    pts = tip + rng.normal(0, .03, (26, 3))
    flames(p, rng, pts, unit(pts - tpath[-4]), V(-.2, 0, .5), rng.uniform(.12, .3, 26), HOT, MID, COLD)
    rg.bind((mark, len(p.v)), {tails[-1]: 1})
    # ---- seams of ember: down the spine and over the shoulders
    for th, t0, t1, w in ((PI / 2, .04, .94, .035), (PI / 2 - .95, .08, .30, .026), (PI / 2 + .95, .08, .30, .026), (PI / 2 - .9, .68, .88, .022), (PI / 2 + .9, .68, .88, .022)):
        ts = np.linspace(t0, t1, 26)
        q = [b.at(t, th + .06 * math.sin(t * 40)) for t in ts]
        ridge(p, [a[0] for a in q], [a[1] for a in q], w * (.4 + .6 * np.sin(PI * np.linspace(0, 1, 26)) ** .6), light(HOT, 1.0), light(MID, .6), height=.3)
    # ---- the mane: fire from the crown, round the neck, down the chest and along the shoulders
    marks = []
    for surf, t_lo, t_hi, count, big, bone in ((nk, .0, 1.0, 230, .34, None), (sk, .0, .30, 70, .24, 'Head'), (b, .0, .16, 120, .30, 'Chest')):
        P_, N_, L_ = [], [], []
        for k in range(count):
            t = rng.uniform(t_lo, t_hi)
            th = rng.uniform(-PI, PI)
            if surf is sk and -2.6 < th < -.5:
                continue                                         # not in the mouth
            if surf is b and -2.3 < th < -.85 and t > .08:
                continue
            P, N = surf.at(t, th)
            P_.append(P)
            N_.append(N)
            L_.append(big * rng.uniform(.5, 1.0) * (1.15 if N[2] > .3 else .85))
        mark = len(p.v)
        flames(p, rng, P_, N_, V(-.75, 0, .15), L_, HOT, MID, COLD, lift=.55)
        if bone:
            rg.bind((mark, len(p.v)), {bone: 1})
        else:
            rg.stick(mark, None, (nk.start, nk.end))
    # a dark ruff under the fire, so the head reads against it
    ruff = len(p.v)
    for k in range(90):
        P, N = nk.at(rng.uniform(.15, 1.0), rng.uniform(-PI, PI))
        d = unit(N + V(-.9, 0, .1))
        spike(p, P - d * .02, P + d * rng.uniform(.10, .2), .03, lit(CHAR, 1.6), lit(EMBER_HIDE, 1.4), SKIN, 4, .6)
    rg.stick(ruff, None, (nk.start, nk.end))

    def swim(t):
        """2.4 s: a prowl in place. The legs walk in diagonal pairs, the shoulders and hips roll against each other,
        the head hangs low and swings a little with each step, the jaw works, the tail lashes slowly."""
        w = TAU * t / 2.4
        P = Pose()
        for names, side, hind in legs:
            ph = w + (0 if (side > 0) != hind else PI)
            P.turn(names[0], YA, -.30 * math.sin(ph)).turn(names[1], YA, .22 * max(math.sin(ph + .9), -.2)).turn(names[2], YA, -.18 * math.sin(ph + 1.6))
        P.turn('Chest', XA, .035 * math.sin(w)).turn('Hips', XA, -.045 * math.sin(w)).turn('Spine', ZA, .04 * math.sin(w))
        P.turn(necks, YA, np.array([.05, .04]) * math.sin(2 * w)).turn('Head', ZA, .07 * math.sin(w + .6)).turn('Head', YA, .04 * math.sin(2 * w + 1))
        P.turn('Jaw', YA, .06 + .05 * math.sin(2 * w + .5))
        P.turn(tails, ZA, wave(5, .16, w, .8, .25)).turn(tails, YA, wave(5, .05, 2 * w, .6))
        return P

    def strike(t, P):
        """Gathers: the hindquarters sink, the chest rises, the head draws back and the jaws open wide; then it
        springs: the forelegs reach and rake down, the head drives forward and the jaws close; settles."""
        rear = key(t, [(0, 0), (.48, 1), (.58, 1.05), (.69, -1), (.84, -.7), (1.3, 0)])
        up, down = max(rear, 0), min(rear, 0)
        jaw = key(t, [(0, 0), (.4, .55), (.62, .75), (.7, .7), (.78, -.05), (1.3, 0)])
        P.turn('Chest', YA, -.30 * up - .10 * down).turn('Spine', YA, .12 * up).turn('Hips', YA, .10 * up)
        P.turn(necks, YA, np.array([-.16, -.14]) * up + np.array([-.14, -.10]) * down).turn('Head', YA, -.22 * up - .25 * down)
        P.turn('Jaw', YA, jaw)
        for names, side, hind in legs:
            if hind:
                P.turn(names[0], YA, .30 * up - .25 * down).turn(names[1], YA, -.45 * up + .2 * down).turn(names[2], YA, .30 * up)
            else:
                P.turn(names[0], YA, -.75 * up + .65 * down).turn(names[1], YA, .5 * up + .25 * down).turn(names[2], YA, -.5 * up - .4 * down)
        P.turn(tails, YA, np.array([-.2, -.2, -.15, -.1, -.1]) * up).turn(tails, ZA, np.array([.1, .15, .2, .2, .2]) * rear)
        return P

    fit(p, 0, 2.9)
    return rg.finish(animations(2.4, swim, strike))


def shag(p, rng, surf, t_range, th_range, count, length, colour0, colour1, drop=V(0, 0, -1), sides=4, slot=SKIN, radius=.035, frost=None, frost_share=.0):
    """Hanging hair (or icicles) on a Body: tapered locks rooted on the skin, drawn toward `drop`. Returns the points."""
    roots = []
    for k in range(count):
        t, th = rng.uniform(*t_range), rng.uniform(*th_range)
        P, N = surf.at(t, th)
        d = unit(N * .35 + np.asarray(drop, np.float64) + rng.normal(0, .12, 3))
        ln = length * rng.uniform(.55, 1.0)
        icy = frost is not None and rng.random() < frost_share
        c0, c1 = (frost, frost) if icy else (colour0, colour1)
        spike(p, P - d * ln * .1, P + d * ln, radius * rng.uniform(.7, 1.2), lit(c0, 1.0) if not icy else light(c0, .9), lit(c1, 1.0) if not icy else light(c1, 1.0),
              CRYSTAL if icy else slot, sides, .75)
        roots.append(P)
    return roots


# ================================================================ SM_AE_RimeMammoth

def rime_mammoth():
    """SM_AE_RimeMammoth (5 m from tusk tip to tail, 3.3 m at the shoulder hump): a mammoth of the cold. A high domed
    head and a sloping back under a long dark coat that hangs in locks to its knees, every lock tipped with ice;
    icicles along the belly; two great tusks of blue ice sweeping out, forward and up; a trunk held curled, its tip
    rimed; small ears; pillar legs; pale blue eyes; a crest of ice crystals along the hump, and frost seams glowing
    faintly through the coat."""
    rng = np.random.default_rng(7202)
    p = Part('SM_AE_RimeMammoth', (SKIN, ROCK, CRYSTAL, GLOW))
    rg = Rig(p)
    FUR, FUR_LIGHT, SKIN_G = c3(.060, .045, .038), c3(.20, .15, .11), c3(.16, .14, .13)
    ICE, ICE_PALE, FROST = c3(.45, .75, .95), c3(.80, .92, 1.0), c3(.60, .88, 1.0)
    b = Body([V(.95, 0, 2.45), V(.55, 0, 2.62), V(.0, 0, 2.50), V(-.6, 0, 2.30), V(-1.15, 0, 2.10), V(-1.5, 0, 1.75)], 70, 34,
             ry=[(0, .62), (.15, .82), (.4, .86), (.7, .78), (.9, .62), (1, .30)], up_r=[(0, .55), (.15, .66), (.4, .56), (.7, .50), (.9, .42), (1, .22)],
             dn_r=[(0, .80), (.15, 1.0), (.4, 1.02), (.7, .92), (.9, .70), (1, .30)])
    b.push(.03 * mottle(b.G, .25, 3) + .012 * np.sin(b.TH * 26 + b.TT * 9))
    b.add(p, lit(rgb(hide(b.G, b.N, FUR, FUR_LIGHT, 21, .3, .25, -.6, .3)), 1.0), caps=(.5, .6))
    rg.bone('Chest', 'Root', b.cp(.45), b.cp(.1))
    rg.bone('Hips', 'Chest', b.cp(.45), b.cp(1.0))
    rg.bind((b.start, b.end), rg.spine_rows(b.vt(), (.45, 1.0), ['Hips'], {'Chest': 1}))
    host = (b.start, b.end)
    hd = Body([V(.9, 0, 2.55), V(1.3, 0, 2.86), V(1.72, 0, 2.70), V(1.98, 0, 2.30), V(2.05, 0, 1.95)], 40, 30,
              ry=[(0, .50), (.3, .56), (.6, .50), (.85, .36), (1, .26)], up_r=[(0, .45), (.3, .52), (.6, .42), (.85, .30), (1, .24)],
              dn_r=[(0, .55), (.3, .56), (.6, .46), (.85, .30), (1, .24)])
    hd.push(.05 * np.exp(-((hd.TT - .3) / .12) ** 2) * (np.sin(hd.TH) > .6) + .02 * mottle(hd.G, .2, 4))
    hd.add(p, lit(rgb(hide(hd.G, hd.N, FUR, FUR_LIGHT, 22, .3, .25, -.6, .3)), 1.0), caps=(.4, .4))
    rg.bone('Head', 'Chest', hd.cp(0), hd.cp(1.0))
    rg.bind((hd.start, hd.end), rg.spine_rows(hd.vt(), (0, 1.0), ['Head'], {'Chest': 1}))
    # trunk: curled back toward the mouth, ringed
    def trunk_colour(t):
        return lit(mx(SKIN_G, mx(SKIN_G, ICE_PALE, .6), smooth(.7, 1, t)), 1 + .10 * np.sin(t * 150))
    tpath, trunk, st = limb(p, rg, 'Trunk', 'Head', [V(2.02, 0, 2.05), V(2.36, 0, 1.55), V(2.48, 0, .95), V(2.30, 0, .52), V(2.02, 0, .50), V(1.92, 0, .74)],
                            [(0, .27), (.3, .2), (.7, .13), (1, .085)], trunk_colour, (hd.start, hd.end), sides=12, n=60)
    # tusks of ice
    for side in (1, -1):
        mark = len(p.v)
        horn(p, V(1.86, side * .30, 2.02), V(.55, side * .45, -.72), 2.5, .135, ICE, ICE_PALE, bend=V(.5, -side * .28, 1.0), n=22, sides=9)
        p.c[mark:len(p.v)] = light(mx(ICE, ICE_PALE, np.linspace(0, 1, len(p.v) - mark)), .85).tolist()
        for i in range(mark, len(p.v)):
            pass
        rg.bind((mark, len(p.v)), {'Head': 1})
        # move the tusk's faces to the crystal slot
        slot_c = p.slots.index(CRYSTAL)
        first = next(k for k, f in enumerate(p.f) if min(f) >= mark)
        for k in range(first, len(p.f)):
            p.m[k] = slot_c
        P, N = hd.at(.62, .55 if side > 0 else PI - .55)
        eye(p, P, unit(N + V(.4, 0, 0)), .05, light(FROST, 1.0), lit(FUR, .9))
        P, N = hd.at(.22, .25 if side > 0 else PI - .25)                                           # small ears
        root = np.array([P + V(q, 0, 0) for q in np.linspace(-.16, .16, 8)])
        G = fan(root, root + V(-.18, side * .30, -.34) + np.array([[0, 0, .12 * math.sin(k)] for k in range(8)]), 6, arch=V(0, side * .08, 0))
        st = membrane_start(p, G, .03, lit(FUR, 1.2), lit(SKIN_G, 1.0), SKIN)
        ear = rg.bone('Ear%s' % ('R' if side > 0 else 'L'), 'Head', P, P + V(-.18, side * .30, -.34))
        rg.bind((st, len(p.v)), {ear: 1})
    legs = []
    for name, parent, side, x, dx in (('LegFR', 'Chest', 1, .55, .10), ('LegFL', 'Chest', -1, .55, -.14), ('LegHR', 'Hips', 1, -1.05, -.12), ('LegHL', 'Hips', -1, -1.05, .14)):
        y = side * .52
        joints = [V(x, y, 1.75), V(x + dx * .4, y, 1.05), V(x + dx * .8, y, .45), V(x + dx, y, .12)]
        path, names, st = limb(p, rg, name, parent, joints, [(0, .40), (.35, .33), (.7, .28), (.92, .30), (1, .33)],
                               lambda t: lit(mx(FUR, SKIN_G, smooth(.55, 1, t)), 1 + .05 * np.sin(t * 60)), host, sides=14)
        mark = len(p.v)
        claws(p, path[-1] + V(.26, 0, -.04), V(1, 0, 0), 4, .09, .13, lit(BONE_W, .7), lit(BONE_W, 1.1), down=.1, radius=.05)
        rg.bind((mark, len(p.v)), {names[-1]: 1})
        legs.append((names, side, x < 0))
    tails_path, tails, st = limb(p, rg, 'Tail', 'Hips', [V(-1.5, 0, 1.85), V(-1.72, 0, 1.5), V(-1.78, .04, 1.05)], [(0, .09), (1, .04)], lambda t: lit(mx(FUR, FUR_LIGHT, t), 1.0), host, sides=7, n=20)
    # the coat: long locks down the flanks, the head and the legs' tops; a fifth of them ice
    mark = len(p.v)
    shag(p, rng, b, (.02, .97), (-.2, .55), 330, .85, FUR, FUR_LIGHT, radius=.06, frost=ICE_PALE, frost_share=.14)
    shag(p, rng, b, (.02, .97), (PI - .55, PI + .2), 330, .85, FUR, FUR_LIGHT, radius=.06, frost=ICE_PALE, frost_share=.14)
    shag(p, rng, b, (.05, .95), (-2.2, -.95), 150, .55, FUR, FUR_LIGHT, radius=.05, frost=ICE, frost_share=.45)        # belly: icicles
    rg.stick(mark, None, host)
    mark = len(p.v)
    shag(p, rng, hd, (.05, .6), (-.5, .9), 70, .5, FUR, FUR_LIGHT, radius=.05, frost=ICE_PALE, frost_share=.2)
    shag(p, rng, hd, (.05, .6), (PI - .9, PI + .5), 70, .5, FUR, FUR_LIGHT, radius=.05, frost=ICE_PALE, frost_share=.2)
    rg.bind((mark, len(p.v)), {'Head': 1})
    # the crest of ice along the hump and the crown
    mark = len(p.v)
    for surf, t0, t1, n_, big in ((b, .03, .55, 30, .5), (hd, .12, .45, 12, .35)):
        for t in np.linspace(t0, t1, n_):
            P, N = surf.at(t + rng.uniform(-.01, .01), PI / 2 + rng.uniform(-.25, .25))
            d = unit(N + V(-.35, rng.uniform(-.3, .3), 0))
            ln = big * rng.uniform(.5, 1.0)
            spike(p, P - d * ln * .15, P + d * ln, ln * .14, light(ICE, .7), light(ICE_PALE, 1.0), CRYSTAL, 6, .5)
    for th, t0, t1 in ((PI / 2 - .6, .1, .8), (PI / 2 + .6, .1, .8)):                                        # frost seams
        ts = np.linspace(t0, t1, 22)
        q = [b.at(t, th + .1 * math.sin(t * 25)) for t in ts]
        ridge(p, [a[0] + a[1] * .02 for a in q], [a[1] for a in q], .05 * np.sin(PI * np.linspace(0, 1, 22)) ** .6 + .01, light(FROST, .9), light(ICE, .5), height=.3)
    rg.stick(mark, None, None)

    def swim(t):
        """4 s: a slow walk in place. Each leg lifts in turn, the great head nods with the stride, the trunk swings
        and curls, the ears fan, the tail flicks."""
        w = TAU * t / 4.0
        P = Pose()
        for i, (names, side, hind) in enumerate(legs):
            ph = w + (0, PI, PI / 2, 3 * PI / 2)[i]
            P.turn(names[0], YA, -.16 * math.sin(ph)).turn(names[1], YA, .14 * max(math.sin(ph + .8), 0)).turn(names[2], YA, -.08 * math.sin(ph + 1.4))
        P.turn('Chest', XA, .02 * math.sin(w)).turn('Hips', XA, -.025 * math.sin(w))
        P.turn('Head', YA, .05 * math.sin(2 * w)).turn('Head', ZA, .05 * math.sin(w + .5))
        P.turn(trunk, ZA, wave(5, .10, w, .7, .2)).turn(trunk, YA, wave(5, .07, 2 * w + 1, .6, .2))
        P.turn('EarR', ZA, .18 * math.sin(2 * w)).turn('EarL', ZA, -.18 * math.sin(2 * w + .4))
        P.turn(tails, ZA, wave(2, .25, 3 * w, .8))
        return P

    def strike(t, P):
        """Rears its head and throws the trunk up and back over it, tusks high; then drives the tusks down and
        forward with its whole front, the trunk whipping out; settles."""
        rear = key(t, [(0, 0), (.5, 1), (.6, 1.05), (.69, -1), (.85, -.7), (1.3, 0)])
        up, down = max(rear, 0), min(rear, 0)
        P.turn('Chest', YA, -.10 * up - .06 * down).turn('Head', YA, -.38 * up - .42 * down)
        P.turn(trunk, YA, np.array([-.5, -.45, -.4, -.3, -.2]) * up + np.array([.25, .3, .3, .25, .2]) * down)
        P.turn('EarR', ZA, .5 * up).turn('EarL', ZA, -.5 * up)
        for names, side, hind in legs:
            if not hind:
                P.turn(names[0], YA, -.22 * up + .2 * down).turn(names[1], YA, .25 * up)
        P.turn(tails, YA, np.array([-.3, -.3]) * up)
        return P

    fit(p, 0, 5.0)
    return rg.finish(animations(4.0, swim, strike))


# ================================================================ SM_AE_GloomToad

def gloom_toad():
    """SM_AE_GloomToad (2.4 m long, 1.5 m tall): a huge squat toad the colour of a starless night. A broad flat body
    all warts, the largest of them swollen sacs of violet light; a mouth as wide as its head, agape on a pale throat,
    with its long tongue lolling out and curled; bulging eyes set high, slit-pupilled; a pale mottled belly and a
    throat sac; short splayed forelegs with long fingers; great folded hind legs with webbed feet."""
    rng = np.random.default_rng(7303)
    p = Part('SM_AE_GloomToad', (SKIN, ROCK, CRYSTAL, GLOW))
    rg = Rig(p)
    NIGHT, DEEP, BELLY = c3(.014, .010, .030), c3(.07, .035, .13), c3(.34, .30, .36)
    VIOLET, MAGENTA, THROAT = c3(.55, .12, .95), c3(.95, .20, .75), c3(.42, .12, .30)
    b = Body([V(.55, 0, .80), V(.25, 0, .90), V(-.20, 0, .86), V(-.65, 0, .66), V(-.95, 0, .42)], 60, 36,
             ry=[(0, .62), (.25, .82), (.5, .86), (.8, .62), (1, .22)], up_r=[(0, .36), (.25, .46), (.5, .44), (.8, .30), (1, .14)],
             dn_r=[(0, .52), (.25, .62), (.5, .60), (.8, .40), (1, .16)])
    b.push(.035 * np.maximum(mottle(b.G, .11, 4), 0) * (np.sin(b.TH) > -.2) + .012 * mottle(b.G, .05, 9))
    b.add(p, lit(rgb(hide(b.G, b.N, mx(NIGHT, DEEP, .3), BELLY, 31, .2, .3, -.55, .15)), 1.0), caps=(.5, .6))
    rg.bone('Chest', 'Root', b.cp(.5), b.cp(.1))
    rg.bone('Hips', 'Chest', b.cp(.5), b.cp(1.0))
    rg.bind((b.start, b.end), rg.spine_rows(b.vt(), (.5, 1.0), ['Hips'], {'Chest': 1}))
    host = (b.start, b.end)
    hinge = V(.50, 0, .78)
    sk = Body([V(.42, 0, .92), V(.75, 0, 1.00), V(1.05, 0, .96), V(1.28, 0, .86), V(1.36, 0, .80)], 36, 34,
              ry=[(0, .62), (.3, .66), (.6, .58), (.85, .42), (1, .26)], up_r=[(0, .34), (.3, .32), (.6, .22), (.85, .14), (1, .08)],
              dn_r=[(0, .10), (.4, .06), (1, .03)], power=2.6)
    sk.push(.03 * np.maximum(mottle(sk.G, .1, 5), 0) * (np.sin(sk.TH) > 0))
    sc = rgb(hide(sk.G, sk.N, mx(NIGHT, DEEP, .3), BELLY, 32, .2, .3, -.55, .15))
    sc = np.where(((sk.TH < -.2) & (sk.TH > -PI + .2))[..., None], THROAT * .8, sc)
    sk.add(p, lit(sc, 1.0), caps=(.4, .5))
    jw = Body([hinge + V(-.04, 0, -.10), hinge + V(.28, 0, -.30), hinge + V(.58, 0, -.40), hinge + V(.80, 0, -.40)], 30, 34,
              ry=[(0, .60), (.3, .64), (.7, .54), (1, .30)], up_r=[(0, .05), (.5, .03), (1, .02)], dn_r=[(0, .24), (.3, .30), (.7, .22), (1, .08)], power=2.6)
    jc = rgb(hide(jw.G, jw.N, BELLY, mx(BELLY, c3(.6, .55, .6), .5), 33, .15, .25, -.6, .1))
    jc = np.where(((jw.TH > .2) & (jw.TH < PI - .2))[..., None], THROAT, jc)
    jw.add(p, lit(jc, 1.0), caps=(.3, .5))
    rg.bone('Head', 'Chest', sk.cp(0), sk.c[-1])
    rg.bone('Jaw', 'Head', hinge + V(-.04, 0, -.10), jw.c[-1])
    rg.bind((sk.start, sk.end), rg.spine_rows(sk.vt(), (0, 1.0), ['Head'], {'Chest': 1}))
    rg.bind((jw.start, jw.end), {'Jaw': 1})
    rg.bind((orb(p, hinge + V(.12, 0, -.10), .2, light(MAGENTA, .55), GLOW, V(0, 0, 1), .6, 2), len(p.v)), {'Jaw': 1})        # the lit gullet
    # the tongue: out of the mouth, down and curled at its tip
    tpath, tongue, st = limb(p, rg, 'Tongue', 'Jaw', [hinge + V(.15, 0, -.22), hinge + V(.6, 0, -.30), hinge + V(1.0, .05, -.42), hinge + V(1.32, .12, -.60), hinge + V(1.46, .2, -.5), hinge + V(1.40, .26, -.38)],
                             [(0, .12), (.6, .08), (.9, .07), (1, .09)], lambda t: lit(mx(THROAT * 1.6, MAGENTA * .6, t), 1.0), (jw.start, jw.end), sides=10, n=50)
    for side in (1, -1):                                                                                 # eyes, high and bulging
        P, N = sk.at(.34, 1.0 if side > 0 else PI - 1.0)
        mark = len(p.v)
        orb(p, P + N * .02, .17, lit(mx(NIGHT, DEEP, .5), 1.2), SKIN, None, 1.0, 2)
        eye(p, P + N * .12, unit(N + V(.5, side * .3, .1)), .10, light(MAGENTA, 1.0), lit(NIGHT, 1.0))
        rg.bind((mark, len(p.v)), {'Head': 1})
    # warts: dark lumps everywhere on the back, the big ones sacs of light
    mark = len(p.v)
    for k in range(150):
        P, N = b.at(rng.uniform(.03, .95), rng.uniform(-.1, PI + .1))
        r = rng.uniform(.025, .06)
        orb(p, P - N * r * .3, r, lit(mx(NIGHT, DEEP, rng.uniform(.2, .8)), 1.3), SKIN, N, .7, 1)
    for k in range(26):
        P, N = b.at(rng.uniform(.08, .9), rng.uniform(.15, PI - .15))
        r = rng.uniform(.05, .11)
        orb(p, P - N * r * .25, r * 1.25, lit(DEEP, 1.4), SKIN, N, .6, 1)
        orb(p, P + N * r * .15, r, light(mx(VIOLET, MAGENTA, rng.uniform(0, .6)), rng.uniform(.6, 1.0)), GLOW, N, .75, 2)
    rg.stick(mark, None, host)
    mark = len(p.v)
    for k in range(40):
        P, N = sk.at(rng.uniform(.05, .8), rng.uniform(.25, PI - .25))
        r = rng.uniform(.02, .05)
        orb(p, P - N * r * .3, r, lit(mx(NIGHT, DEEP, rng.uniform(.2, .8)), 1.3), SKIN, N, .7, 1)
    rg.bind((mark, len(p.v)), {'Head': 1})
    def leg_colour(t):
        return lit(mx(mx(NIGHT, DEEP, .5), mx(DEEP, BELLY, .5), t), 1 + .08 * np.sin(t * 45))
    legs = []
    for side in (1, -1):
        # forelegs: short, elbows out, fingers spread
        path, names, st = limb(p, rg, 'Arm%s' % ('R' if side > 0 else 'L'), 'Chest', [V(.30, side * .62, .62), V(.42, side * .92, .40), V(.62, side * .84, .12), V(.78, side * .86, .05)],
                               [(0, .17), (.3, .14), (.66, .10), (1, .09)], leg_colour, host)
        mark = len(p.v)
        for q in (-.7, -.25, .25, .7):
            d = unit(V(1, side * (.25 + q * .6), -.05))
            pipe(p, np.array([path[-1], path[-1] + d * .18, path[-1] + d * .34 + V(0, 0, -.03)]), np.array([.045, .035, .04]), lit(mx(DEEP, BELLY, .4), 1.0), SKIN, 6)
        rg.bind((mark, len(p.v)), {names[-1]: 1})
        legs.append((names, side, False))
        # hind legs: folded, the long foot flat
        path, names, st = limb(p, rg, 'Leg%s' % ('R' if side > 0 else 'L'), 'Hips', [V(-.62, side * .50, .58), V(-.20, side * .98, .62), V(-.80, side * 1.06, .22), V(-.30, side * 1.12, .06)],
                               [(0, .26), (.25, .24), (.45, .16), (.7, .12), (1, .08)], leg_colour, host, n=50)
        mark = len(p.v)
        toes = [path[-1] + unit(V(1, side * q, 0)) * .42 for q in (-.5, -.15, .2, .55)]
        for tip in toes:
            pipe(p, np.array([path[-1], (path[-1] + tip) / 2 + V(0, 0, .02), tip]), np.array([.05, .035, .04]), lit(mx(DEEP, BELLY, .4), 1.0), SKIN, 6)
        web = fan(np.array([path[-1]] * 4), np.array(toes), 5)
        membrane(p, web, .012, lit(mx(DEEP, VIOLET, .25), 1.0), lit(BELLY, .8), SKIN)
        rg.bind((mark, len(p.v)), {names[-1]: 1})
        legs.append((names, side, True))
    P, N = b.at(.1, -PI / 2)
    rg.bind((orb(p, P + V(.15, 0, .05), .34, lit(mx(BELLY, c3(.7, .6, .7), .4), 1.0), SKIN, V(.3, 0, -1), .8, 2), len(p.v)), {'Chest': 1})      # the throat sac

    def swim(t):
        """3 s: it squats and breathes: the body rises and settles on its legs, the head tilts, the jaw hangs and
        works, the tongue sways and curls."""
        w = TAU * t / 3.0
        P = Pose()
        for names, side, hind in legs:
            if hind:
                P.turn(names[0], XA, side * .05 * math.sin(w)).turn(names[1], XA, -side * .08 * math.sin(w))
            else:
                P.turn(names[0], XA, side * .06 * math.sin(w + .5)).turn(names[1], YA, .06 * math.sin(w + .5))
        P.turn('Chest', YA, -.03 * math.sin(w)).turn('Head', YA, .04 * math.sin(w + 1)).turn('Head', ZA, .05 * math.sin(.5 * w * 2 + .3))
        P.turn('Jaw', YA, .05 + .05 * math.sin(2 * w))
        P.turn(tongue, ZA, wave(5, .12, 2 * w, .8, .25)).turn(tongue, YA, wave(5, .08, w + 1, .7, .2))
        return P

    def strike(t, P):
        """Gulps: the head lifts and the mouth gapes, the tongue drawn back; then the whole body lunges on its hind
        legs and the tongue lashes straight out; it snaps back."""
        rear = key(t, [(0, 0), (.5, 1), (.6, 1.05), (.69, -1), (.82, -.6), (1.3, 0)])
        up, down = max(rear, 0), min(rear, 0)
        P.turn('Chest', YA, -.18 * up - .1 * down).turn('Head', YA, -.3 * up - .1 * down)
        P.turn('Jaw', YA, .35 * up - .5 * down)
        P.turn(tongue, YA, np.array([-.5, -.5, -.45, -.4, -.3]) * up + np.array([-.1, .25, .45, .7, .6]) * down)
        P.turn(tongue, ZA, np.array([0, -.05, -.15, -.35, -.5]) * down * -1)
        for names, side, hind in legs:
            if hind:
                P.turn(names[0], XA, -side * .35 * down).turn(names[1], XA, side * .5 * down)
            else:
                P.turn(names[0], YA, -.3 * up)
        return P

    fit(p, 0, 2.4)
    return rg.finish(animations(3.0, swim, strike))


MESHES = [pyre_lion, rime_mammoth, gloom_toad]
CONTRACT = {'SM_AE_PyreLion': {'size': (2.9, 0, 0), 'tol': .1, 'pivot': 'centre'}, 'SM_AE_RimeMammoth': {'size': (5.0, 0, 0), 'tol': .1, 'pivot': 'centre'},
            'SM_AE_GloomToad': {'size': (2.4, 0, 0), 'tol': .1, 'pivot': 'centre'}}

if __name__ == '__main__':
    import check
    for _part in check.builds(sys.modules[__name__]):
        _v = np.asarray(_part.v)
        print('%s  %d tris  %s .. %s' % (_part.name, _part.triangles(), np.round(_v.min(0), 3).tolist(), np.round(_v.max(0), 3).tolist()))
