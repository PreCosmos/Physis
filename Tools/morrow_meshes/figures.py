"""Morrow's figures: the Stilled (people of the town caught in the Rime where they stood), the Rime-shapes (Maren's
grief in the Morning, frost given form) and the Unrisen (level 8; Tools/morrow/README.md is the contract).

The Stilled are modelled in their own clothes' colours in one slot: in play they wear M_MW_Stilled, which lays
hoarfrost over that colour by the component's custom primitive data 0 (1 frozen .. 0 woken), so the same mesh serves
before and after. The Rime-shapes and the Unrisen are frost through and through, with the forced magenta in their
cores; they hover, so they are centred ('centre' pivot), except the kneeling Unrisen, which rests on the ground.
"""
from kit import *  # noqa: F401,F403

SKIN = col(.420, .300, .240)
SKIN_PALE = col(.520, .400, .340)
HAIR_GREY = col(.400, .390, .380)
HAIR_DARK = col(.060, .045, .035)

# The Stilled: (name, height, coat length 0..1, hat, bulk, coat colour, under colour, hat colour, extra)
#   hat: 'cap' (peaked), 'flat', 'knit', 'hood', 'bun' (no hat: hair up), 'phones' (headset), 'officer'
#   extra: 'apron', 'skirt', 'scarf', 'letter', ''
STILLED = (
    ('SM_OP_Stilled0', 1.74, .45, 'flat', 1.1, col(.20, .17, .13), col(.30, .28, .25), col(.12, .11, .10), 'apron'),     # the miller
    ('SM_OP_Stilled1', 1.80, .66, 'cap', 1.0, col(.07, .09, .13), col(.15, .15, .16), col(.06, .07, .10), ''),            # the bridge keeper
    ('SM_OP_Stilled2', 1.66, .72, 'bun', .9, col(.20, .10, .09), col(.33, .30, .26), HAIR_GREY, 'skirt'),                 # Ada Fenn, the teacher
    ('SM_OP_Stilled3', 1.78, .38, 'flat', 1.0, col(.20, .12, .06), col(.10, .12, .16), col(.12, .09, .06), 'scarf'),       # Jory Pike
    ('SM_OP_Stilled4', 1.68, .42, 'phones', .95, col(.32, .25, .16), col(.10, .10, .14), HAIR_DARK, ''),                  # Ines Okon, the operator
    ('SM_OP_Stilled5', 1.76, .40, 'knit', 1.1, PAINT_OLIVE, col(.12, .12, .10), col(.30, .08, .05), ''),                  # Corin's crew: overalls
    ('SM_OP_Stilled6', 1.72, .62, 'hood', 1.05, col(.14, .16, .12), col(.10, .10, .10), col(.14, .16, .12), ''),           # Corin's crew: a work coat
    ('SM_OP_Stilled7', 1.72, .74, 'officer', 1.0, col(.13, .14, .09), col(.10, .10, .08), col(.10, .11, .07), 'letter'),  # Warden Maren Holt
)


def person(k):
    """One of the Stilled, standing still and looking a little down, 1.66 to 1.8 m tall, facing +x: legs, coat (or
    skirt and shawl), arms, hands, head and hair or hat, each in its own colour. One slot (CLOTH)."""
    name, height, coat, hat, bulk, coat_c, under_c, hat_c, extra = STILLED[k]
    rng = np.random.default_rng(870 + k)
    p = Part(name, (CLOTH,))
    sh = height * .82
    hip = height * .52
    hem = sh - (sh - .05) * coat - .05
    boots = col(.05, .045, .04)
    for sy in (-1, 1):
        tube(p, [(0, sy * .1, 0.05), (0, sy * .1, hem + .1)], [.07 * bulk, .085 * bulk], under_c, CLOTH, 8)
        bevel_box(p, (.06, sy * .1, .05), (.13, .055, .05), boots, CLOTH, .02)
    if extra == 'skirt':
        prof = [(.3 * bulk, .12), (.24 * bulk, hip), (.17 * bulk, hip + .12), (.19 * bulk, sh - .15), (.19 * bulk, sh - .02), (.08, sh + .04)]
    else:
        prof = [(.25 * bulk, hem), (.2 * bulk, hip), (.19 * bulk, hip + .15), (.21 * bulk, sh - .15), (.2 * bulk, sh - .02), (.08, sh + .04)]
    lathe(p, prof, coat_c, CLOTH, 16, (0, 0, 0))
    if extra == 'apron':
        p.add(np.array([(.2 * bulk, -.17, hip + .25), (.2 * bulk, .17, hip + .25), (.27 * bulk, .2, hem + .05), (.27 * bulk, -.2, hem + .05)]),
              [[0, 3, 2, 1], [1, 2, 3, 0]], col(.45, .43, .38), CLOTH, False)
    if extra == 'skirt':     # a shawl over the shoulders
        lathe(p, [(.24 * bulk, sh - .32), (.23 * bulk, sh - .1), (.12, sh + .02)], col(.30, .26, .22), CLOTH, 16, (0, 0, 0))
    if extra == 'scarf':
        torus(p, (0, 0, sh + .02), .1, .045, col(.45, .08, .05), CLOTH, 16, 6, 'z')
        tube(p, [(.08, .05, sh), (.15, .08, sh - .3), (.16, .07, sh - .5)], .035, col(.45, .08, .05), CLOTH, 6)
    for sy in (-1, 1):
        a = (0, sy * .22 * bulk, sh - .06)
        if extra == 'letter' and sy > 0:     # her right hand holds the letter up before her
            b = (.2, sy * .25 * bulk, sh - .32)
            h_ = (.34, sy * .12, sh - .2)
            tube(p, [a, b, h_], [.07 * bulk, .06 * bulk, .05], coat_c, CLOTH, 8)
            blob(p, h_, .05, SKIN, CLOTH, 1, .05, 3, (1.2, .8, 1.3))
            p.add(np.array([(.38, .02, sh - .32), (.38, .2, sh - .32), (.4, .2, sh - .06), (.4, .02, sh - .06)]), [[0, 1, 2, 3], [3, 2, 1, 0]],
                  col(.8, .78, .72), CLOTH, False)
            continue
        b = (.04, sy * .27 * bulk, hip + .12)
        h_ = (.12, sy * .2 * bulk, hip - .06)
        tube(p, [a, b, h_], [.07 * bulk, .06 * bulk, .05], coat_c, CLOTH, 8)
        blob(p, h_, .05, SKIN, CLOTH, 1, .05, sy + 3, (1.2, .8, 1.3))
    tube(p, [(0, 0, sh), (.01, 0, sh + .09)], .055, SKIN, CLOTH, 8)
    blob(p, (.03, 0, sh + .2), .11, SKIN_PALE if k in (2, 4, 7) else SKIN, CLOTH, 2, .02, k, (1.1, .92, 1.15))
    top = sh + .29
    if hat == 'cap':
        cylinder(p, (.02, 0, sh + .27), .12, .07, hat_c, CLOTH, 14, .13)
        p.add(np.array([(.08, -.09, sh + .275), (.08, .09, sh + .275), (.2, .08, sh + .25), (.2, -.08, sh + .25)]), [[0, 1, 2, 3], [3, 2, 1, 0]], hat_c,
              CLOTH, False)
    elif hat == 'officer':
        cylinder(p, (.02, 0, sh + .27), .115, .06, hat_c, CLOTH, 16, .14)
        cylinder(p, (.02, 0, sh + .33), .14, .03, hat_c, CLOTH, 16)
        p.add(np.array([(.1, -.09, sh + .28), (.1, .09, sh + .28), (.22, .08, sh + .26), (.22, -.08, sh + .26)]), [[0, 1, 2, 3], [3, 2, 1, 0]], boots,
              CLOTH, False)
    elif hat == 'flat':
        blob(p, (.05, 0, sh + .29), .13, hat_c, CLOTH, 1, .05, 7, (1.25, 1.0, .35))
    elif hat == 'knit':
        blob(p, (.02, 0, sh + .29), .12, hat_c, CLOTH, 1, .1, 9, (1.0, 1.0, .75))
    elif hat == 'bun':
        blob(p, (0, 0, sh + .25), .12, hat_c, CLOTH, 1, .06, 11, (1.05, 1.0, .8))
        blob(p, (-.09, 0, sh + .3), .06, hat_c, CLOTH, 1, .1, 12)
    elif hat == 'phones':
        blob(p, (0, 0, sh + .24), .118, hat_c, CLOTH, 1, .06, 13, (1.05, 1.02, .9))
        torus(p, (.01, 0, sh + .22), .125, .012, STEEL_W, CLOTH, 16, 4, 'x', math.pi, True, 0.0)
        for sy in (-1, 1):
            cylinder(p, (.02, sy * .12, sh + .17), .04, .025, STEEL_W, CLOTH, 10)
    else:
        lathe(p, [(.15, sh + .08), (.16, sh + .2), (.13, sh + .3), (.04, sh + .36)], hat_c, CLOTH, 14, (-.02, 0, 0), True, math.tau * .78, math.pi * .61)
    finish(p)
    return p


# ---------------------------------------------------------------- the Rime-shapes and the Unrisen

def frost_body(p, rng, profile, lean, sides=14, colour=FROST):
    """A hooded robe of frost from a lathe profile [(radius, z), ...], bent forward by `lean` (metres at the top)."""
    s = len(p.v)
    lathe(p, profile, colour, LICHEN, sides, (0, 0, 0))
    v = np.asarray(p.v[s:], np.float64)
    top = max(z for _, z in profile)
    v[:, 0] += lean * (v[:, 2] / top) ** 2
    v[:, :2] *= 1 + .08 * np.sin(v[:, 2] * 5.0 + rng.uniform(0, 6))[:, None]
    p.v[s:] = v.tolist()


def spikes(p, rng, centre, radius, count, length, colour=FROST):
    c = np.asarray(centre, np.float64)
    for k in range(count):
        d = rng.normal(size=3)
        d[2] = abs(d[2]) * .6 + .2
        d /= np.linalg.norm(d)
        base = c + d * radius
        prism(p, base, base + d * length * rng.uniform(.5, 1.0), length * .08, vary(rng, colour, .08), LICHEN, 5, .4)


def shade():
    """SM_OE_Shade: a Rime-shape, about 1.9 m: a hunched, hooded figure of frost with long arms and no face, needles
    along its back, magenta in the hollow of its hood. 'centre' pivot (it hovers)."""
    rng = np.random.default_rng(880)
    p = Part('SM_OE_Shade', (LICHEN, GLOW))
    frost_body(p, rng, [(.05, 0.0), (.32, .1), (.36, .6), (.3, 1.1), (.28, 1.45), (.22, 1.7), (.06, 1.92)], .35)
    blob(p, (.42, 0, 1.6), (.12, .14, .16), GLOW_RIME, GLOW, 1, .1, 3)
    for sy in (-1, 1):
        tube(p, [(.2, sy * .3, 1.4), (.45, sy * .45, 1.0), (.6, sy * .4, .5), (.7, sy * .3, .2)], [.09, .07, .05, .02], FROST_BLUE, LICHEN, 7)
    spikes(p, rng, (-.1, 0, 1.3), .3, 26, .6)
    centre(p)
    return p


def mourner():
    """SM_OE_Mourner: a larger Rime-shape, about 3.4 m: a tall veiled figure of frost, its arms folded over something
    it will not show, a crown of needles. 'centre' pivot (it hovers)."""
    rng = np.random.default_rng(881)
    p = Part('SM_OE_Mourner', (LICHEN, GLOW))
    frost_body(p, rng, [(.1, 0.0), (.7, .2), (.62, 1.2), (.5, 2.2), (.46, 2.8), (.32, 3.15), (.08, 3.4)], .25, 18)
    for sy in (-1, 1):
        tube(p, [(.1, sy * .5, 2.7), (.55, sy * .45, 2.2), (.6, -sy * .1, 1.95)], [.13, .11, .09], FROST_BLUE, LICHEN, 8)
    blob(p, (.55, 0, 2.05), (.22, .26, .2), GLOW_RIME, GLOW, 1, .15, 5)
    spikes(p, rng, (.1, 0, 3.15), .3, 18, .9)
    spikes(p, rng, (-.2, 0, 1.6), .5, 30, .8)
    centre(p)
    return p


def unrisen():
    """SM_OE_Unrisen: the Unrisen as it fights, about 8 m tall: a towering robed figure of Rime, head bowed, arms
    flung wide, the morning held to its chest as a small trapped light, needles growing from its shoulders and back,
    its hem trailing away into mist. 'centre' pivot (it hovers)."""
    rng = np.random.default_rng(882)
    p = Part('SM_OE_Unrisen', (LICHEN, GLOW, CRYSTAL))
    frost_body(p, rng, [(.2, 0.0), (1.6, .4), (1.5, 2.0), (1.3, 3.8), (1.25, 5.2), (1.0, 6.2), (.55, 6.7), (.6, 7.3), (.35, 7.9), (.05, 8.1)],
               .6, 24)
    for sy in (-1, 1):
        tube(p, [(.2, sy * 1.0, 6.2), (.7, sy * 2.4, 6.0), (1.1, sy * 3.6, 5.2), (1.2, sy * 4.2, 4.4)], [.35, .28, .2, .1], FROST_BLUE, LICHEN, 10)
        spikes(p, rng, (.6, sy * 3.0, 5.6), .25, 10, 1.0)
    blob(p, (1.35, 0, 4.8), .55, (1.0, .82, .55, 1.0), GLOW, 2, .05, 7)
    blob(p, (1.3, 0, 4.8), .8, ICE, CRYSTAL, 2, .12, 8)
    spikes(p, rng, (-.3, 0, 6.3), 1.0, 40, 2.2)
    spikes(p, rng, (0, 0, 3.0), 1.4, 40, 1.2, FROST_BLUE)
    for k in range(6):
        blob(p, (rng.uniform(-.8, .8), rng.uniform(-.8, .8), rng.uniform(1.0, 5.0)), .2, GLOW_RIME, GLOW, 1, .2, 20 + k)
    centre(p)
    return p


def unrisen_kneeling():
    """SM_OP_Unrisen: the Unrisen when it has stopped: the same figure kneeling, 6 m tall, bowed over the light it
    holds in both arms against itself. It rests on the ground (its knees at z 0). One slot each for frost and light;
    in play it wears M_MW_Stilled on its frost (the spoken stage thaws it)."""
    rng = np.random.default_rng(883)
    p = Part('SM_OP_Unrisen', (CLOTH, GLOW))
    s = len(p.v)
    lathe(p, [(.3, 0.0), (2.0, .2), (2.1, 1.2), (1.7, 2.4), (1.4, 3.6), (1.2, 4.6), (.7, 5.2), (.6, 5.6), (.3, 6.0), (.05, 6.1)], FROST, CLOTH, 24,
          (0, 0, 0))
    v = np.asarray(p.v[s:], np.float64)
    v[:, 0] += 1.4 * (np.clip(v[:, 2] - 2.0, 0, None) / 4.1) ** 1.5
    p.v[s:] = v.tolist()
    for sy in (-1, 1):
        tube(p, [(.6, sy * 1.1, 4.6), (1.6, sy * 1.2, 3.8), (2.2, sy * .5, 3.2), (2.3, -sy * .2, 3.0)], [.34, .3, .26, .2], FROST_BLUE, CLOTH, 10)
    blob(p, (2.0, 0, 3.4), .5, (1.0, .82, .55, 1.0), GLOW, 2, .05, 7)
    for k in range(40):
        d = rng.normal(size=3)
        d[2] = abs(d[2])
        d /= np.linalg.norm(d)
        base = np.array((.5, 0, 4.0)) + d * 1.2
        prism(p, base, base + d * rng.uniform(.8, 1.8), .1, vary(rng, FROST, .08), CLOTH, 5, .4)
    finish(p)
    return p


MESHES = [person, shade, mourner, unrisen, unrisen_kneeling]
VARIANTS = {person: len(STILLED)}
CONTRACT = {'SM_OE_Shade': {'pivot': 'centre'}, 'SM_OE_Mourner': {'pivot': 'centre'}, 'SM_OE_Unrisen': {'pivot': 'centre'}}
