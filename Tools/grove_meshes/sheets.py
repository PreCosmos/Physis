"""The grove's photo-scanned leaf sheets and how its generated plants use them.

A sheet is one texture set (Tools/grove_scans/prepare.py: T_GRS_<Sheet>_D with the cutout in alpha, _N, _ARM) holding
several sprays: a leafy twig, a frond, a fir spray, a grass tuft. A plant's foliage is cards, each showing one spray.
CELLS lists every usable spray of every sheet as (u0, v0, u1, v1, stem): its rectangle in the sheet (u right, v down,
0 to 1) and the side its stem enters from ('bottom', 'top', 'left' or 'right'); the card's base sits at that side and
the spray grows away from it, whatever way it lies in the sheet. `size` is the spray's real length in metres along its
stem, so cards can be built at true scale.

One mesh uses one sheet for all its LEAF faces (its LEAF slot gets that sheet's material: looks.py). Cards carry
vertex-colour alpha 0, as the Conclave's atlas cards do, and solid twigs and stems alpha 1 (they are drawn in their
vertex colour, untextured).

    from sheets import sprays, spray_cells
    sprays(part, 'LBroadleaf', base, grow, facing, length, colours, rng=rng, crown=crown)
"""
import numpy as np

import al_flora as fl

# sheet -> {'aspect': width / length of the whole sheet's texels (1: square), 'cells': {name: (u0, v0, u1, v1, stem, size m)}}
CELLS = {
    # tree_small_02's leaf sheet: single ovate leaves and, used here, its one leafy twig (eight leaves on a 0.45 m stem).
    'LBroadleaf': {
        'twig': (.545, .030, .835, .670, 'bottom', .46),
        'leaf_a': (.040, .045, .200, .145, 'left', .09),
        'leaf_b': (.245, .410, .415, .525, 'left', .09),
        'leaf_c': (.265, .540, .425, .620, 'left', .09),
    },
    # jacaranda's fronds: twice-pinnate leaves, an ash or rowan's habit. Three whole fronds.
    'LFine': {
        'frond_a': (.160, .027, .988, .469, 'left', .55),
        'frond_b': (.000, .320, .430, .660, 'left', .34),
        'frond_c': (.250, .585, 1.000, .995, 'right', .50),
    },
    # fir_tree_01's twig sheet: flat fir sprays.
    'LFir': {
        'spray_a': (.316, .406, .637, .777, 'bottom', .55),
        'spray_b': (.645, .465, .949, .828, 'bottom', .55),
        'spray_c': (.656, .051, .934, .367, 'bottom', .48),
        'spray_d': (.195, .055, .414, .312, 'bottom', .40),
        'tip_a': (.500, .262, .625, .398, 'bottom', .22),
        'tip_b': (.543, .102, .586, .227, 'bottom', .18),
    },
    # grass_medium_01: whole tufts, a stand of long blades, and seed heads.
    'LGrass': {
        'tuft_a': (.219, .750, .469, .891, 'bottom', .30),
        'tuft_b': (.609, .758, .816, .855, 'bottom', .22),
        'tuft_c': (.254, .891, .473, 1.000, 'bottom', .26),
        'tuft_d': (.605, .875, .777, .996, 'bottom', .26),
        'tuft_e': (.059, .871, .180, 1.000, 'bottom', .28),
        'blades': (.766, .074, .957, .617, 'bottom', .75),
        'seed_a': (.730, .160, .773, .547, 'bottom', .70),
        'seed_b': (.715, .215, .746, .586, 'bottom', .70),
    },
    # celandine_01: round glossy leaf blades (their petiole joins at the named side) and open yellow flowers seen from
    # above. The sheet's stalks sit in smeared padding, so stalks are solid geometry.
    'LFlowers': {
        'leaf_a': (.025, .030, .215, .225, 'bottom', .07),
        'leaf_b': (.430, .040, .600, .235, 'bottom', .07),
        'leaf_c': (.750, .135, .960, .345, 'bottom', .08),
        'leaf_d': (.185, .460, .345, .615, 'top', .06),
        'leaf_e': (.555, .280, .715, .440, 'top', .06),
        'bloom_a': (.280, .720, .410, .845, 'bottom', .03),
        'bloom_b': (.065, .825, .190, .955, 'bottom', .03),
        'bloom_c': (.455, .810, .560, .930, 'bottom', .03),
    },
}


def spray_cells(sheet, *names):
    """The named cells of a sheet (all of them when none is named), as a list of (name, cell)."""
    cells = CELLS[sheet]
    return [(n, cells[n]) for n in (names or cells)]


def _uv(cell, s, t):
    """Sheet uv of the card point (s across 0..1, t along the stem 0..1 from its base)."""
    u0, v0, u1, v1, stem = cell[:5]
    if stem == 'bottom':
        return u0 + s * (u1 - u0), v1 - t * (v1 - v0)
    if stem == 'top':
        return u0 + s * (u1 - u0), v0 + t * (v1 - v0)
    if stem == 'left':
        return u0 + t * (u1 - u0), v0 + s * (v1 - v0)
    return u1 - t * (u1 - u0), v0 + s * (v1 - v0)


def _aspect(cell):
    """A cell's width over its length (across its stem over along it)."""
    u0, v0, u1, v1, stem = cell[:5]
    w, h = u1 - u0, v1 - v0
    return (w / h) if stem in ('bottom', 'top') else (h / w)


def sprays(part, sheet, base, grow, facing, length, colours, cells=None, rng=None, crown=None, normal=None, foot=.85,
           lean=0.0, bend=0.0):
    """Cards showing sprays of `sheet`: one per base point. Each card's base edge is centred on its base point; it runs
    `length` metres along `grow` and is as wide as its spray's own proportions make it, its face turned toward
    `facing`. cells: the cell names to draw from (at random per card, with rng; else the first). colours: one tint or
    one per card: a multiplier on the photo, where white leaves it as scanned (say (.9, .9, .9) for full sun and
    darker inside a crown, or a golden tint for autumn). Normals as fl.cards: `normal`, else `crown` (centre, radii),
    else each card's own facing. bend splits a card in two along its length and folds its outer half back by that
    fraction of its length, so a long spray droops instead of standing stiff.
    Returns the index of the first vertex added."""
    base = np.atleast_2d(np.asarray(base, np.float64))
    n = len(base)
    names = list(cells or CELLS[sheet])
    table = CELLS[sheet]
    pick = rng.integers(0, len(names), n) if rng is not None else np.zeros(n, np.int64)
    grow = np.broadcast_to(np.asarray(grow, np.float64), (n, 3))
    facing = np.broadcast_to(np.asarray(facing, np.float64), (n, 3))
    length = np.broadcast_to(np.asarray(length, np.float64), (n,))
    cols = np.asarray(colours, np.float64)
    if cols.ndim == 1:
        cols = np.tile(cols, (n, 1))
    first = len(part.v)
    for k, name in enumerate(names):
        mine = np.nonzero(pick == k)[0]
        if not len(mine):
            continue
        cell = table[name]
        width = length[mine] * _aspect(cell)
        start = fl.cards(part, base[mine], grow[mine], facing[mine], width, length[mine], (0, 0), cols[mine],
                         crown=crown, rng=None, foot=foot, lean=lean, shape='quad',
                         normal=None if normal is None else np.broadcast_to(np.asarray(normal, np.float64), (n, 3))[mine])
        # fl.cards laid each card as a quad in the order bottom-left, bottom-right, top-right, top-left of an atlas
        # cell; give those corners this spray's place in the sheet instead (mirrored for half the cards).
        flip = (rng.uniform(0, 1, len(mine)) < .5) if rng is not None else np.zeros(len(mine), bool)
        for i in range(len(mine)):
            s0, s1 = (1.0, 0.0) if flip[i] else (0.0, 1.0)
            corners = (_uv(cell, s0, 0.0), _uv(cell, s1, 0.0), _uv(cell, s1, 1.0), _uv(cell, s0, 1.0))
            for j, uv in enumerate(corners):
                part.uv[start + i * 4 + j] = (float(uv[0]), float(uv[1]))
        if bend:
            v = np.asarray(part.v[start:start + len(mine) * 4], np.float64).reshape(len(mine), 4, 3)
            f = fl.unit(facing[mine] - grow[mine] * np.sum(facing[mine] * fl.unit(grow[mine]), 1, keepdims=True))
            v[:, 2] -= f * (length[mine] * bend)[:, None]
            v[:, 3] -= f * (length[mine] * bend)[:, None]
            part.v[start:start + len(mine) * 4] = v.reshape(-1, 3).tolist()
    return first
