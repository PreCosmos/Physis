GROUND = -(1 - 2 / PHI ** 2)  # the golden cut of the ring's diameter: y = -.236

# Limbs and roots leave the braid as cubic curves: (leaves at y, control 1, control 2, tip).
LIMBS = (
    (-.05, (.05, .12), (.34, .02), (.72, .20)),
    (.05, (.05, .28), (.28, .30), (.60, .55)),
    (.15, (.03, .42), (.15, .52), (.35, .78)),
)
ROOTS = (
    (-.34, (.05, -.44), (.36, -.30), (.74, -.44)),
    (-.38, (.04, -.52), (.26, -.50), (.52, -.72)),
    (-.42, (.03, -.60), (.10, -.66), (.23, -.88)),
)


def bezier(p0, p1, p2, p3, count=70):
    t = np.linspace(0, 1, count)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def braid_strands(rng):
    """Every limb runs down through the trunk, crosses over, and leaves as a root opposite.

    The trunk is therefore not a stamped rod but six grown fibres, as on an old olive.
    Returns (limb polyline, root polyline, trunk section) per strand.
    """
    strands = []
    for sign in (1, -1):
        for rank in range(3):
            y_top, c1, c2, tip = LIMBS[rank]
            y_low, r1, r2, end = ROOTS[rank]
            jitter = lambda p: np.asarray(p) * (sign, 1) + rng.normal(0, .007, 2)
            ys = np.linspace(y_low, y_top, 90)
            f = (ys - y_low) / (y_top - y_low)
            d = rank * .42
            theta = (math.pi / 2 - d) * (2 * f - 1) * sign
            mid = (y_low + y_top) / 2
            amp = .048 + .062 * ((ys - mid) / (y_top - y_low) * 2) ** 2
            trunk = np.stack((amp * np.sin(theta), ys), -1)
            limb = bezier(trunk[-1], jitter(c1) * (1, 1), jitter(c2), jitter(tip))
            # The strand crosses, so its root leaves on the opposite side.
            root = bezier(trunk[0], jitter(r1) * (-1, 1), jitter(r2) * (-1, 1), jitter(end) * (-1, 1))
            strands.append((limb, root, trunk, theta))
    return strands


def hairline(t, thick, thin=.0065, power=1.15):
    return thin + (thick - thin) * (1 - t) ** power


def ring_strand(rel, frame, sign, rng, ring=1.0):
    """One side of the bowl of the phi: a laurel rising from the root, curling in at the crown."""
    stop = math.radians(69)
    angle = np.linspace(-math.pi / 2, stop, 200)
    arc = np.stack((sign * np.cos(angle), np.sin(angle)), -1) * ring
    # Spiral continuing the same tangent, tightening by the golden ratio each quarter turn.
    pts, _ = golden_spiral(1.45, 150)
    pts = pts[::-1]
    pts = pts * (1, -1) / np.hypot(*pts[0]) * .155
    tan = pts[1] - pts[0]
    head = arc[-1] - arc[-2]
    turn = math.atan2(head[1], head[0]) - math.atan2(tan[1], tan[0])
    if sign < 0:
        pts = pts * (1, -1)
        tan = pts[1] - pts[0]
        turn = math.atan2(head[1], head[0]) - math.atan2(tan[1], tan[0])
    c, s = math.cos(turn), math.sin(turn)
    pts = (pts @ np.array(((c, s), (-s, c)))) + (arc[-1] - (pts @ np.array(((c, s), (-s, c))))[0])
    line = np.concatenate((arc, pts[1:]))
    f = np.linspace(0, 1, len(line))
    rel.tube(frame.p(line), (.040 + (.0075 - .040) * f ** 1.25) * frame.s, GOLD)
    knob = frame.p(line[-1])
    rel.segment(knob, knob, .017 * frame.s, .017 * frame.s, GOLD)
    # Laurel: big outward leaves that set the silhouette, smaller ones inside.
    t = .035
    side = 1
    n = len(arc)
    while t < .95:
        i = int(t * (n - 2))
        tangent = arc[i + 1] - arc[i]
        heading = math.atan2(tangent[1], tangent[0])
        out = side > 0
        size = (.235 - .10 * t) * (1 if out else .58) * (1 + rng.uniform(-.07, .07))
        direction = heading - sign * side * (.42 + rng.uniform(-.05, .05))
        rel.leaf(frame.p(arc[i]), frame.angle(direction), size * frame.s, size * .32 * frame.s,
                 bend=sign * side * rng.uniform(.04, .15), tip=mix_leaf(rng), root=GOLD,
                 lift=f[i] * 0 + .9 * frame.s / 300, veins=5, rough=.36)
        t += .043 + .012 * (1 - t) if out else .018
        side = -side


def mix_leaf(rng):
    """Each leaf its own alloy: from deep emerald gold to sunlit green."""
    v = rng.random()
    a, b = (LEAF_DEEP, LEAF) if v < .5 else (LEAF, LEAF_LIGHT)
    return a + (b - a) * (v * 2 % 1)


def emblem_phi(rel, frame, seed=11, crown_points=340, root_points=170):
    """Concept A: a tree of life whose braided trunk, leader and laurel ring form a phi."""
    rng = np.random.default_rng(seed)
    px = rel.w / max(frame.s, 1)
    strands = braid_strands(rng)

    # Skeleton the twigs grow from.
    nodes, parents = [], []

    def add_chain(points):
        for j, q in enumerate(points):
            parents.append(len(nodes) - 1 if j else -1)
            nodes.append(np.asarray(q))

    for limb, *_ in strands:
        add_chain(limb[8::2])
    leader_y = np.linspace(.15, .92, 40)
    leader = np.stack((.006 * np.sin(leader_y * 5), leader_y), -1)
    add_chain(leader)
    crown_skel = len(nodes)

    def crown(p):
        r = math.hypot(*p)
        ceiling = .82 - .10 * min(abs(p[0]) / .3, 1) * (p[1] > 0 and abs(p[0]) < .3)
        return r < ceiling and p[1] > .04 + .24 * abs(p[0]) ** 3 and abs(p[0]) > .04

    right = poisson(rng, lambda p: p[0] > 0 and crown(p), crown_points // 2, .064)
    left = right * (-1, 1) + rng.normal(0, .016, right.shape)
    tw, tp = colonize((nodes, parents), np.concatenate((right, left)), step=.022, influence=.34, kill=.05,
                      tropism=(0, .10), seed=seed)
    tw, tp = prune(tw, tp, 6)
    tw, children = smooth_nodes(tw, tp, 12, frozen=crown_skel)
    radii = np.minimum(branch_radii(tp, .0052), .019)

    root_nodes, root_parents = [], []
    for _, root, *_r in strands:
        for j, q in enumerate(root[8::2]):
            root_parents.append(len(root_nodes) - 1 if j else -1)
            root_nodes.append(q)
    root_skel = len(root_nodes)

    def roots(p):
        r = math.hypot(*p)
        return r < .84 and p[1] < -.42 - .12 * abs(p[0]) ** 2

    rright = poisson(rng, lambda p: p[0] > .04 and roots(p), root_points // 2, .07)
    rleft = rright * (-1, 1) + rng.normal(0, .016, rright.shape)
    rn, rp = colonize((root_nodes, root_parents), np.concatenate((rright, rleft)), step=.02, influence=.3, kill=.05,
                      tropism=(0, -.14), seed=seed + 1)
    rn, rp = prune(rn, rp, 7)
    rn, rchildren = smooth_nodes(rn, rp, 12, frozen=root_skel)
    rrad = np.minimum(branch_radii(rp, .0042), .014)

    # Fine growth first, so limbs and braid sit on top of it.
    for i, p in enumerate(tp):
        if p >= 0 and i >= crown_skel:
            pa, pb = frame.p(tw[p]), frame.p(tw[i])
            rel.segment(pa, pb, max(radii[p] * frame.s, .6), max(radii[i] * frame.s, .6), GOLD)
    for i, p in enumerate(rp):
        if p >= 0 and i >= root_skel:
            pa, pb = frame.p(rn[p]), frame.p(rn[i])
            rel.segment(pa, pb, max(rrad[p] * frame.s, .6), max(rrad[i] * frame.s, .6), ROSE_GOLD)

    # Leaves under the limbs: alternate on the twigs, sprays at each tip, kept off the ring.
    def place(base, heading, size):
        tip = np.asarray(base) + size * np.array((math.cos(heading), math.sin(heading)))
        if math.hypot(*tip) > .885 or abs(tip[0]) < .022:
            return
        rel.leaf(frame.p(base), frame.angle(heading), size * frame.s, size * .34 * frame.s,
                 bend=rng.uniform(-.2, .2), tip=mix_leaf(rng), root=GOLD, lift=.5 * frame.s / 300 + rng.uniform(0, 1.6) * frame.s / 300,
                 veins=4, rough=.36)

    for i in range(crown_skel, len(tw)):
        if len(children[i]) == 1 and i % 4 == 0:
            d = tw[i] - tw[tp[i]]
            place(tw[i], math.atan2(d[1], d[0]) + (1 if i % 8 else -1) * rng.uniform(.5, .9), rng.uniform(.075, .115))
    for i in range(len(tw)):
        if children[i] or i < crown_skel:
            continue
        p = i
        for _ in range(4):
            p = tp[p] if tp[p] >= 0 else p
        d = tw[i] - tw[p]
        heading = math.atan2(d[1], d[0])
        place(tw[i], heading + rng.uniform(-.2, .2), rng.uniform(.13, .185))
        place(tw[p], heading + rng.choice((-1, 1)) * rng.uniform(.6, .9), rng.uniform(.09, .125))

    # The upright of the phi: a leader that thins to a spire above and a taproot below.
    ys = np.linspace(-1.08, 1.06, 300)
    up = np.clip(ys, 0, None) / 1.06
    down = np.clip(-ys, 0, None) / 1.08
    thick = .0345 * (1 - up) ** .8 + .0115 * up
    thick = np.where(ys < 0, .0345 * (1 - down) ** .9 + .0125 * down, thick)
    wave = .006 * np.sin(ys * 5)
    line = frame.p(np.stack((wave, ys), -1))
    blend = np.clip((ys - GROUND) / .3 + .5, 0, 1)
    colours = ROSE_GOLD[None] * (1 - blend[:, None]) + GOLD[None] * blend[:, None]
    for i in range(len(ys) - 1):
        rel.segment(line[i], line[i + 1], thick[i] * frame.s, thick[i + 1] * frame.s, colours[i])

    # Limbs and roots, tapering out of the braid.
    for limb, root, trunk, theta in strands:
        f = np.linspace(0, 1, len(limb))
        for curve, thick_at, tint in ((root, .0225, ROSE_GOLD), (limb, .025, GOLD)):
            f = np.linspace(0, 1, len(curve))
            rr = hairline(f, thick_at, .0052) * frame.s
            q = frame.p(curve)
            for i in range(len(curve) - 1):
                rel.segment(q[i], q[i + 1], rr[i], rr[i + 1], tint, lift=max(1 - i / 12, 0) * .018 * frame.s)
        f = (trunk[:, 1] - trunk[0, 1]) / (trunk[-1, 1] - trunk[0, 1])
        q = frame.p(trunk)
        over_under = (.5 + .5 * np.cos(theta * 3))
        for i in range(len(trunk) - 1):
            tint = ROSE_GOLD * (1 - f[i]) + GOLD * f[i]
            rel.segment(q[i], q[i + 1], .0225 * frame.s, .0225 * frame.s, tint,
                        lift=(.008 + .020 * over_under[i]) * frame.s)

    # Spire, taproot trident, then the ring over everything.
    rel.leaf(frame.p((0, 1.02)), frame.angle(math.pi / 2), .31 * frame.s, .085 * frame.s, tip=LEAF, root=GOLD,
             lift=.01 * frame.s, veins=5, relief=.42, rough=.32)
    for sign in (-1, 1):
        rel.leaf(frame.p((0, 1.015)), frame.angle(math.pi / 2 - sign * .55), .15 * frame.s, .052 * frame.s,
                 bend=sign * .16, tip=LEAF, root=GOLD, veins=0, rough=.34)
        t = np.linspace(0, 1, 50)
        for reach, spread, start in ((.25, .15, -1.03),):
            curve = np.stack((sign * spread * t ** 1.6, start - reach * t ** .9), -1)
            rel.tube(frame.p(curve), (.0205 * (1 - t) ** 1.1 + .0045) * frame.s, ROSE_GOLD)
    t = np.linspace(0, 1, 40)
    rel.tube(frame.p(np.stack((.006 * np.sin(t * 3), -1.04 - .27 * t), -1)), (.0215 * (1 - t) ** .9 + .0045) * frame.s, ROSE_GOLD)

    for sign in (-1, 1):
        ring_strand(rel, frame, sign, rng)
    # A clasp where the ring crosses the stem, so the join feels made.
    for sign in (-1, 1):
        rel.leaf(frame.p((0, -1.0)), frame.angle(-math.pi / 2 + sign * 1.25), .13 * frame.s, .058 * frame.s,
                 bend=sign * -.12, tip=PALE_GOLD, root=GOLD, veins=0, lift=.022 * frame.s)

