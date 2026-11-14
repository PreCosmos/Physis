"""Kit smoke test: one grove tree with scanned leaf sprays, and one crate (not part of the level)."""
from kit import *
from sheets import sprays, CELLS


def sample_tree():
    rng = np.random.default_rng(7)
    p = Part('SM_GV_Oak', (BARK, LEAF))
    cfg = dict(segs=[9, 7, 5, 4], up=[.1, .32, .22, .15], wiggle=.12, taper=[.55, .45, .4, .35], children=[5, 4, 3],
               t0=[.45, .3, .35], spread=[(.55, .85), (.45, .8), (.4, .8)], ratio=[(.62, .78), (.55, .7), (.5, .62)],
               child_r=[.6, .62, .65])
    t = fl.grow(rng, np.zeros(3), (.06, -.04, 1), 6.5, .42, cfg)
    fl.wood(p, rng, t, BARK_BROWN, BARK, [14, 8, 6, 4], ground=2.0)
    fl.roots(p, rng, .42, 6, BARK_BROWN, BARK, 1.3, ground=2.0)
    tips = np.array([e for e, _, d in t['tips'] if d >= 2])
    crown = fl.crown_of(tips, 1.0)
    base, grow_, face = [], [], []
    for pts, _, depth in t['wood']:
        if depth < 2:
            continue
        for q in np.r_[rng.uniform(.15, 1.0, 26 if depth == 3 else 10), 1.0]:
            at, along = fl._along(pts, q)
            out = fl.unit(at - crown[0])
            a, b = frame(along)
            spin = rng.uniform(0, TAU)
            side = a * math.cos(spin) + b * math.sin(spin)
            base.append(at)
            grow_.append(fl.unit(along * .45 + side * .55 + out * .35 + UP * .1))
            face.append(fl.unit(UP * .6 + out * .4 + rng.normal(0, .25, 3)))
    base, grow_, face = np.array(base), np.array(grow_), np.array(face)
    depth = np.linalg.norm((base - crown[0]) / crown[1], axis=1)
    tint = np.clip(.55 + .45 * depth, .5, 1.0)[:, None] * np.array([[.92, .95, .88]]) * rng.uniform(.85, 1.05, (len(base), 1))
    sprays(p, 'LBroadleaf', base, grow_, face, rng.uniform(.75, 1.15, len(base)), tint, cells=('twig',), rng=rng, crown=crown)
    fl._scale_to(p, 14.0)
    return finish(p, centre_xy=False)


def sample_crate():
    p = Part('SM_GN_Crate', (PAINT, STEEL))
    bevel_box(p, (0, 0, .5), (.6, .45, .5), JUST_OLIVE, PAINT, .03)
    for s in (-1, 1):
        bevel_box(p, (0, s * .46, .5), (.62, .02, .06), STEEL_GREY, STEEL, .01)
    ao(p, 0, 1.0, .6)
    grime(p, 0, .3, .5)
    return finish(p)


MESHES = [sample_tree, sample_crate]
CONTRACT = {'SM_GV_Oak': {'size': (0, 0, 14.0), 'pivot': 'any'}, 'SM_GN_Crate': {'size': (1.2, .95, 1.0)}}
