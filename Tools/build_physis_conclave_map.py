"""Render the Conclave's map for the pause menu: Art/UI/T_UI_MapConclave.png.

A realistic view straight down on the drum's floor, in the level's six colours only (gold, light blue, red, green,
black, white; greys are black and white mixed). The ground is the terrain mesh's own albedo (drum.py's vertex colours:
golden lawns, white stone roads and plazas, black soil on the crop terraces, black slag in the Foundry, the docks'
grey deck, white sand and rock), the lake is light blue by depth, slopes are shaded under a high northern light,
and scatter.json's houses, ruins, terrace walls, trees, fields and flowers are drawn from above (roofs and canopies
rendered from the generators' own meshes). Then the walk limit (the parapets at |y| 300 m), the end caps, the
window strips beyond the floor's edge with space behind them, and glyphs (no text) for the Archive, the Orrery,
the three pylons, the Spire, the docks and the Wellspring's pool. Every pixel is a palette colour: shading moves
a gold, red or light blue only within its family (palette.py), and the finished image is checked pixel by pixel.

Same frame as the Center's map (physis_conclave_plan.MAP_HALF_CM, north up, east right), so the pause menu's
markers use one transform in both levels:
  U = (y + E) / (2 E)          V = (E - x) / (2 E)          (0..1, origin top-left: HUD DrawTexture UVs)
  pixel = (U * size, V * size), texel (c, r) covers [c, c+1) x [r, r+1); its centre is ((c + .5) / size, (r + .5) / size).

Run after Tools/build_physis_conclave.py (height.bin, scatter.json), with numpy (the Kokoro venv, Python 3.14):
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/build_physis_conclave_map.py [--size 1024]
then conclave:map_art in the editor (before the HUD batch, whose PageMap names T_UI_MapConclave).
"""
import argparse
import importlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Art/Meshes/Conclave'
sys.path.insert(0, str(ROOT / 'Tools'))
sys.path.insert(0, str(ROOT / 'Content/Python'))
sys.path.insert(0, str(ROOT / 'Tools/conclave_meshes'))

import physis_conclave_plan as plan  # noqa: E402
import drum  # noqa: E402  (the floor's colours, roads, masks and the vectorised palette rule)
from palette import (BLUE, BLUE_PALE, CHARCOAL, GOLD, GOLD_DEEP, GOLD_STRAW, GREEN_GRASS, GREEN_LEAF, RED_BRIGHT, RED_DEEP, WHITE, WHITE_PURE,  # noqa: E402
                     allowed)
from build_physis_center_map import write_png  # noqa: E402  (the same minimal PNG writer)

EXTENT_CM = plan.MAP_HALF_CM
SUN_ALT = math.radians(50.0)      # a high light from the north (top of the map): east and west slopes shade alike
SHADOW = 0.40                     # shadow length per metre of height (the Spine's sun, pitched -68 degrees)


def srgb(lin):
    return drum._srgb(np.asarray(lin, np.float64)[..., :3])


def disp(colour):
    """A palette colour (linear) as a display (sRGB) triple."""
    return srgb(np.array(colour[:3]))


# Display colours, all palette members.
SPACE = disp((.004, .004, .004))
FRAME = disp((.011, .011, .011))          # the window's steel, just above the black of space behind it
FRAME_MAJOR = disp((.022, .022, .022))
SILL = disp((.06, .06, .06))
ROAD = disp(WHITE)
INK = np.zeros(3)
WHITE_D = disp(WHITE_PURE)
GOLD_D = disp(GOLD)
GOLD_RICH = disp(GOLD_DEEP)
BLUE_D = disp(BLUE)
BLUE_LIGHT = disp(BLUE_PALE)
RED_D = disp(RED_BRIGHT)
WATER_SHALLOW = disp(BLUE_PALE)
WATER_DEEP = np.array((.42, .66, .88))      # sRGB: hue 209, saturation .52, value .88 (light blue)
CAP = disp((.42, .42, .42))


# ---------------------------------------------------------------- colour within the palette

def families(rgb):
    """Which palette family each display colour leans to (drum.snap's capture ranges): gold, red, blue masks."""
    h, s, v = drum._hsv(np.clip(rgb, 0, 1))
    chroma = s >= .115
    gold = chroma & (h >= 20) & (h <= 70) & (s >= .15) & (v >= .45)
    red = chroma & ((h >= 325) | (h <= 18)) & (s >= .45) & (v >= .25)
    blue = chroma & (h >= 170) & (h <= 240) & (v >= .5)
    return h, s, v, gold, red, blue


def darken(rgb, k):
    """rgb times k in value, held in its family: a gold, red or light blue keeps hue and saturation and stops at the
    family's value floor (a gold shaded darker than that would read brown), a grey darkens or lightens freely."""
    h, s, v, gold, red, blue = families(rgb)
    floor = np.where(gold, .53, np.where(red, .32, np.where(blue, .60, 0.0)))
    v2 = np.clip(np.maximum(v * k, np.minimum(v, floor)), 0, 1)
    return drum._rgb(h, s, v2)


def to_palette(rgb):
    """Every pixel into the palette (drum.snap: a blend stays in its family, anything between families or too dark
    to read as one becomes the grey of its value)."""
    return srgb(drum.snap(drum._linear(np.clip(rgb, 0, 1))))


def quantise_checked(rgb):
    """8-bit image whose every colour passes palette.allowed; a colour that 8-bit rounding pushed over a family's
    edge becomes the grey of its value. Returns the image and how many colours needed that."""
    img = (np.clip(rgb, 0, 1) * 255 + .5).astype(np.uint8)
    flat = img.reshape(-1, 3)
    colours, inverse = np.unique(flat, axis=0, return_inverse=True)
    lin = drum._linear(colours / 255.0)
    bad = np.array([not allowed(c) for c in lin])
    if bad.any():
        grey = (colours[bad].max(1)[:, None] * np.ones(3)).astype(np.uint8)
        colours = colours.copy()
        colours[bad] = grey
        flat = colours[inverse.ravel()]
        img = flat.reshape(img.shape)
    check = np.unique(img.reshape(-1, 3), axis=0)
    left = [tuple(c) for c in check if not allowed(drum._linear(c / 255.0))]
    if left:
        raise SystemExit('map colours outside the palette: %s' % left[:8])
    return img, int(bad.sum()), len(check)


# ---------------------------------------------------------------- drawing helpers (pixel units)

def cover(sd):
    """Anti-aliased coverage of a shape from its signed distance in pixels (negative inside)."""
    return np.clip(.5 - sd, 0, 1)


def paint(img, coverage, colour, alpha=1.0):
    a = (np.clip(coverage, 0, 1) * alpha)[..., None]
    img *= 1 - a
    img += np.asarray(colour, np.float64) * a


def sd_ellipse(u, w, a, b, turn):
    """Approximate signed distance to an ellipse (semi-axes a, b, turned by `turn` radians)."""
    c, s = math.cos(turn), math.sin(turn)
    x, y = u * c + w * s, -u * s + w * c
    f = np.sqrt((x / a) ** 2 + (y / b) ** 2)
    g = np.sqrt((x / a / a) ** 2 + (y / b / b) ** 2) + 1e-9
    return (f - 1) * f / g


def sd_triangle(u, w, r):
    """Signed distance to an equilateral triangle of inradius-ish size r pointing up (Inigo Quilez's formula)."""
    k = math.sqrt(3.0)
    px, py = np.abs(u) - r, -w + r / k
    fold = px + k * py > 0
    qx = np.where(fold, (px - k * py) / 2, px)
    qy = np.where(fold, (-k * px - py) / 2, py)
    qx = qx - np.clip(qx, -2 * r, 0)
    return -np.hypot(qx, qy) * np.sign(qy)


def sd_segment(u, w, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = np.clip(((u - ax) * dx + (w - ay) * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(u - ax - t * dx, w - ay - t * dy)


class Canvas:
    """The image plus its world coordinates: X (north, metres) per row, Y (east) per column."""

    def __init__(self, size, extent_cm):
        self.size = size
        self.E = extent_cm / 100.0
        self.px = 2 * self.E / size
        t = (np.arange(size) + .5) / size
        self.xs = self.E - t * 2 * self.E          # row centres, north (top) to south
        self.ys = -self.E + t * 2 * self.E         # column centres, west (left) to east
        self.X = np.repeat(self.xs[:, None], size, 1)
        self.Y = np.repeat(self.ys[None, :], size, 0)
        self.img = np.zeros((size, size, 3))
        self.s = size / 1024.0                     # glyph and line widths are designed at 1024

    def pixel(self, x, y):
        """World metres -> (column, row) in pixels (continuous)."""
        return (y + self.E) / self.px - .5, (self.E - x) / self.px - .5

    def window(self, x, y, radius_px):
        """Rows and columns within radius_px of a world point, and the pixel offsets (u right, w down) there."""
        cu, cw = self.pixel(x, y)
        c0, c1 = max(int(cu - radius_px), 0), min(int(cu + radius_px) + 2, self.size)
        r0, r1 = max(int(cw - radius_px), 0), min(int(cw + radius_px) + 2, self.size)
        if c0 >= c1 or r0 >= r1:
            return None
        u = np.arange(c0, c1)[None, :] - cu
        w = np.arange(r0, r1)[:, None] - cw
        return (slice(r0, r1), slice(c0, c1)), np.broadcast_to(u, (r1 - r0, c1 - c0)), np.broadcast_to(w, (r1 - r0, c1 - c0))


# ---------------------------------------------------------------- the floor

def load(data):
    meta = json.loads((data / 'height.json').read_text())
    h = np.fromfile(data / 'height.bin', '<f4').reshape(meta['nx'], meta['ny']).astype(np.float64)
    return meta, h


def floor(cv, meta, H, G):
    """Terrain albedo, the lake, slope shading. Returns the floor and water masks."""
    X, Y = cv.X, cv.Y
    inside = (np.abs(X) <= meta['half_x']) & (np.abs(Y) <= meta['half_y'])
    lin = np.stack([drum.sample(G['colour'][..., c], X, Y) for c in range(3)], -1)
    colour = srgb(lin)

    # Shading by the real slope under a light from the north: flat ground 1.0, the drum's own rise and the risers
    # a little darker, north faces lit and south faces shadowed. The lake's surface is shaded apart (flat).
    hx, hy = np.gradient(drum.blur(H, 1), meta['cell'])
    SX, SY = drum.sample(hx, X, Y), drum.sample(hy, X, Y)
    lx, lz = math.cos(SUN_ALT), math.sin(SUN_ALT)
    lit = (-SX * lx + lz) / np.sqrt(1 + SX * SX + SY * SY)
    k = np.clip(1 + .62 * (lit / lz - 1), .62, 1.16)
    colour = darken(colour, k)

    # The lake: SM_CD_Water's rectangle at the water level, light blue by depth, a pale line at the waterline.
    v = np.asarray(drum.water().v)
    rect = (X >= v[:, 0].min()) & (X <= v[:, 0].max()) & (Y >= v[:, 1].min()) & (Y <= v[:, 1].max())
    depth = meta['water'] - drum.sample(H, X, Y)
    grad = np.hypot(SX, SY) * cv.px + 1e-3            # metres of height per pixel
    wet = np.clip(.5 + depth / grad, 0, 1) * rect
    water = WATER_SHALLOW * (1 - drum.sstep(0, 3.5, depth)[..., None]) + WATER_DEEP * drum.sstep(0, 3.5, depth)[..., None]
    colour = colour * (1 - wet[..., None]) + water * wet[..., None]
    shore = np.clip(1.1 - np.abs(depth) / grad, 0, 1) * rect
    paint(colour, shore, BLUE_LIGHT, .55)
    cv.img[inside] = colour[inside]
    return inside, wet


def roads(cv, G):
    """The roads' stone crisp over the terrain's 2 m colour, at their real widths (the plaza and the docks' deck
    already carry them)."""
    lines = drum.road_lines()
    d, which, _ = drum.nearest_on([pts for pts, _, _ in lines], cv.X, cv.Y)
    hw = np.array([w for _, w, _ in lines])[which]
    plazas = np.maximum(drum.sample(G['surface']['plaza'], cv.X, cv.Y), drum.sample(G['surface']['deck'], cv.X, cv.Y))
    paint(cv.img, cover((d - hw) / cv.px), ROAD, .85 * (1 - np.clip(plazas * 1.5, 0, 1)))


# ---------------------------------------------------------------- scatter seen from above

def top_view(part, res):
    """A Part seen from straight above: per res-metre cell the colour of the highest upward face over it (sRGB),
    its height, and the cell grid's origin. Fans every face into triangles; faces turned down are hidden."""
    v = np.asarray(part.v, np.float64)
    col = srgb(np.asarray(part.c, np.float64))
    lo, hi = v.min(0), v.max(0)
    x0, y0 = lo[0] - res, lo[1] - res
    nx, ny = int(math.ceil((hi[0] - x0) / res)) + 2, int(math.ceil((hi[1] - y0) / res)) + 2
    zbuf = np.full((nx, ny), -np.inf)
    rgb = np.zeros((nx, ny, 3))
    for f in part.f:
        for k in range(1, len(f) - 1):
            a, b, c = v[f[0]], v[f[k]], v[f[k + 1]]
            n = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if n <= 1e-12:
                continue                              # seen from below or edge on
            i0 = max(int((min(a[0], b[0], c[0]) - x0) / res), 0)
            i1 = min(int((max(a[0], b[0], c[0]) - x0) / res) + 1, nx)
            j0 = max(int((min(a[1], b[1], c[1]) - y0) / res), 0)
            j1 = min(int((max(a[1], b[1], c[1]) - y0) / res) + 1, ny)
            if i0 >= i1 or j0 >= j1:
                continue
            px = x0 + (np.arange(i0, i1)[:, None] + .5) * res
            py = y0 + (np.arange(j0, j1)[None, :] + .5) * res
            wa = ((b[0] - px) * (c[1] - py) - (b[1] - py) * (c[0] - px)) / n
            wb = ((c[0] - px) * (a[1] - py) - (c[1] - py) * (a[0] - px)) / n
            wc = 1 - wa - wb
            inside = (wa >= 0) & (wb >= 0) & (wc >= 0)
            if not inside.any():
                continue
            z = wa * a[2] + wb * b[2] + wc * c[2]
            sub = zbuf[i0:i1, j0:j1]
            top = inside & (z > sub)
            sub[top] = z[top]
            rgb[i0:i1, j0:j1][top] = (col[f[0]] + col[f[k]] + col[f[k + 1]]) / 3
    return {'rgb': rgb, 'z': zbuf, 'x0': x0, 'y0': y0, 'res': res, 'reach': float(np.hypot(*np.maximum(np.abs(lo[:2]), np.abs(hi[:2]))))}


# Meshes drawn from above (module, resolution in metres); the rest of the scatter is splatted as small points.
SPRITES = {'architecture': ('SM_CN_House0', 'SM_CN_House1', 'SM_CN_House2', 'SM_CN_House3', 'SM_CN_Ruin0', 'SM_CN_Ruin1',
                            'SM_CN_TerraceWall', 'SM_CN_Stairs'),
           'al_flora': ('SM_CV_TreeWhite', 'SM_CV_TreeRed', 'SM_CV_TreeBlack', 'SM_CV_FruitTree', 'SM_CV_Hedge')}
SPRITE_RES = .25
# Stand-ins when a generator module is missing or broken: a footprint (x, y) and a top colour.
FALLBACK = {'SM_CN_House0': ((7, 9), RED_DEEP), 'SM_CN_House1': ((6, 6), RED_DEEP), 'SM_CN_House2': ((8, 12), RED_DEEP),
            'SM_CN_House3': ((8, 8), WHITE), 'SM_CN_Ruin0': ((7, 9), (.12, .12, .12)), 'SM_CN_Ruin1': ((6, 6), (.12, .12, .12)),
            'SM_CN_TerraceWall': ((.6, 12), WHITE), 'SM_CN_Stairs': ((4.5, 3), WHITE), 'SM_CV_Hedge': ((1, 2), RED_DEEP),
            'SM_CV_TreeWhite': ((6, 6), GREEN_LEAF), 'SM_CV_TreeRed': ((7, 7), RED_DEEP), 'SM_CV_TreeBlack': ((5, 5), (.02, .02, .02)),
            'SM_CV_FruitTree': ((4, 4), WHITE_PURE)}
# Points: colour (linear) and the patch each instance covers seen from above (diameter, metres).
POINTS = {'SM_CV_Wheat': (GOLD_STRAW, 1.5), 'SM_CV_Reeds': (GREEN_GRASS, 1.3), 'SM_CV_Lily': (WHITE_PURE, 1.5),
          'SM_CV_FlowersWhite': (WHITE_PURE, .9), 'SM_CV_FlowersRed': (RED_BRIGHT, .9), 'SM_CV_FlowersBlue': (BLUE, .9),
          'SM_CV_Shrub': (WHITE_PURE, 1.3), 'SM_CV_RockWhite': (WHITE, 1.4), 'SM_CV_RockBlack': (CHARCOAL, 1.4)}


def sprites(problems):
    """Top views of the scatter's buildings, walls and trees, from their generators (pure numpy, like the build)."""
    out = {}
    for module_name, names in SPRITES.items():
        try:
            module = importlib.import_module(module_name)
        except Exception as error:  # the map still draws, with stand-ins
            problems.append('%s: %s: %s' % (module_name, type(error).__name__, error))
            continue
        variants = getattr(module, 'VARIANTS', {})
        for builder in getattr(module, 'MESHES', ()):
            for k in (range(variants[builder]) if variants.get(builder) else (None,)):
                try:   # one broken builder costs its own sprites only
                    part = builder(k) if k is not None else builder()
                except Exception as error:
                    problems.append('%s.%s: %s: %s' % (module_name, builder.__name__, type(error).__name__, error))
                    continue
                if part.name in names:
                    out[part.name] = top_view(part, SPRITE_RES)
    for name, ((lx, ly), colour) in FALLBACK.items():
        if name not in out:
            nx, ny = int(lx / SPRITE_RES) + 1, int(ly / SPRITE_RES) + 1
            tall = 9.0 if name.startswith(('SM_CN_House', 'SM_CV_Tree')) else 2.5
            out[name] = {'rgb': np.tile(disp(colour), (nx, ny, 1)), 'z': np.full((nx, ny), tall), 'x0': -lx / 2, 'y0': -ly / 2,
                         'res': SPRITE_RES, 'reach': math.hypot(lx, ly) / 2, 'stand_in': True}
    return out


def stamp(cv, sprite, rows, layer):
    """Draws a sprite at every scatter row: its shadow (layer 'shadow') or itself ('top'), 3 x 3 samples a pixel."""
    rgb, zb, x0, y0, res = sprite['rgb'], sprite['z'], sprite['x0'], sprite['y0'], sprite['res']
    nx, ny = zb.shape
    tall = float(np.max(zb[np.isfinite(zb)])) if np.isfinite(zb).any() else 0.0
    sub = (np.arange(3) - 1) / 3.0
    for x, y, _z, _pitch, yaw, _roll, scale in rows:
        x, y, scale = x / 100.0, y / 100.0, max(scale, 1e-3)
        reach = sprite['reach'] * scale + (SHADOW * tall * scale if layer == 'shadow' else 0)
        win = cv.window(x, y, reach / cv.px + 2)
        if win is None:
            continue
        sl, u, w = win
        cov = np.zeros(u.shape)
        acc = np.zeros(u.shape + (3,))
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        for du in sub:
            for dw in sub:
                wx = x - (w + dw) * cv.px                 # world north of the sample
                wy = y + (u + du) * cv.px
                if layer == 'shadow':
                    wx = wx + SHADOW * tall * scale       # the object north of a point shades it (light from the north)
                dx, dy = wx - x, wy - y
                lu, lv = (c * dx + s * dy) / scale, (-s * dx + c * dy) / scale
                i, j = np.floor((lu - x0) / res).astype(np.int64), np.floor((lv - y0) / res).astype(np.int64)
                ok = (i >= 0) & (i < nx) & (j >= 0) & (j < ny)
                ii, jj = np.clip(i, 0, nx - 1), np.clip(j, 0, ny - 1)
                hit = ok & np.isfinite(zb[ii, jj])
                cov += hit
                acc += rgb[ii, jj] * hit[..., None]
        cov /= 9.0
        if layer == 'shadow':
            region = cv.img[sl]
            region[:] = region * (1 - cov[..., None]) + darken(region, .8) * cov[..., None]
        else:
            colour = acc / np.maximum(cov * 9.0, 1e-9)[..., None]
            region = cv.img[sl]
            region[:] = region * (1 - cov[..., None]) + colour * cov[..., None]


def points(cv, rows, colour, diameter):
    """Small plants and rocks as soft points: each covers its own area of a pixel, so a field or a drift of flowers
    tints the ground the way it does from far above."""
    if not rows:
        return
    a = np.asarray(rows, np.float64)
    cu, cw = cv.pixel(a[:, 0] / 100.0, a[:, 1] / 100.0)
    area = min(math.pi * (diameter * .5) ** 2 / cv.px ** 2, 1.0) * np.clip(a[:, 6], .5, 2) ** 2
    acc = np.zeros((cv.size, cv.size))
    c0, r0 = np.floor(cu).astype(np.int64), np.floor(cw).astype(np.int64)
    fu, fw = cu - c0, cw - r0
    for dc, dr, wgt in ((0, 0, (1 - fu) * (1 - fw)), (1, 0, fu * (1 - fw)), (0, 1, (1 - fu) * fw), (1, 1, fu * fw)):
        cc, rr = c0 + dc, r0 + dr
        ok = (cc >= 0) & (cc < cv.size) & (rr >= 0) & (rr < cv.size)
        np.add.at(acc, (rr[ok], cc[ok]), (area * wgt)[ok])
    paint(cv.img, np.clip(acc, 0, 1), disp(colour))


def scatter(cv, data, problems):
    path = data / 'scatter.json'
    if not path.exists():
        problems.append('no scatter.json: the map has no houses or trees')
        return {}
    rows = json.loads(path.read_text())
    for name, (colour, diameter) in POINTS.items():
        points(cv, rows.get(name, []), colour, diameter)
    tops = sprites(problems)
    order = ('SM_CN_TerraceWall', 'SM_CN_Stairs', 'SM_CV_Hedge', 'SM_CN_Ruin0', 'SM_CN_Ruin1', 'SM_CN_House0', 'SM_CN_House1',
             'SM_CN_House2', 'SM_CN_House3', 'SM_CV_FruitTree', 'SM_CV_TreeWhite', 'SM_CV_TreeRed', 'SM_CV_TreeBlack')
    for layer in ('shadow', 'top'):
        for name in order:
            if rows.get(name) and name in tops:
                stamp(cv, tops[name], rows[name], layer)
    stand_ins = sorted(n for n in order if rows.get(n) and tops[n].get('stand_in'))
    if stand_ins:
        problems.append('no generator mesh yet, drawn as footprints: %s' % ', '.join(stand_ins))
    return {name: len(rows.get(name, [])) for name in order}


# ---------------------------------------------------------------- the drum around the floor

def drum_frame(cv, meta):
    """Beyond the floor's edge: the window strips (space behind dark steel ribs and frames, stars), the walk limit's
    parapets, and the end caps."""
    X, Y = cv.X, cv.Y
    s = cv.s
    ay = np.abs(Y)
    half_x, edge = meta['half_x'], meta['half_y']
    reach = plan.R * math.sin(math.radians(drum.WINDOW_STRIPS[0]) + plan.WINDOW)    # the window's far sill, seen from above
    pane = (ay > edge) & (ay <= reach + cv.px) & (np.abs(X) <= half_x)
    cv.img[pane] = SPACE
    rng = np.random.default_rng(1406)
    star = pane & (rng.uniform(0, 1, X.shape) < .006)
    bright = rng.uniform(0, 1, X.shape) ** 3
    cv.img[star] = (SPACE + (WHITE_D - SPACE) * (.25 + .75 * bright[..., None]))[star]
    few = star & (rng.uniform(0, 1, X.shape) < .08)
    cv.img[few] = BLUE_LIGHT
    # Ribs along the drum every 7.5 degrees of arc (lines of constant y from above), frames every 40 m along it.
    n_arc = int(round(math.degrees(plan.WINDOW) / drum.RIB_ARC))
    for k in range(n_arc + 1):
        y = plan.R * math.sin(math.radians(drum.WINDOW_STRIPS[0] + drum.RIB_ARC * k))
        sill = k in (0, n_arc)
        width = (1.6 if sill else .55) * s
        line = cover(np.abs(ay - y) / cv.px - width) * (np.abs(X) <= half_x)
        paint(cv.img, line * (ay >= edge - cv.px), SILL if sill else FRAME)
    xs = np.arange(-half_x, half_x + 1e-6, drum.RIB_X)
    for b, x in enumerate(xs):
        major = b % 5 == 0 or b == len(xs) - 1
        line = cover(np.abs(X - x) / cv.px - (.9 if major else .4) * s) * pane
        paint(cv.img, line, FRAME_MAJOR if major else FRAME)
    # The walk limit: the parapets' white balustrade along |y| 300 m, cased in black so it reads on rock and grass.
    run = np.abs(X) <= drum.END_BERM - 3.0
    d = np.abs(ay - plan.WALK_Y) / cv.px
    paint(cv.img, cover(d - 1.9 * s) * run, INK, .8)
    paint(cv.img, cover(d - .85 * s) * run, WHITE_D)
    # The end caps: steel walls across the drum at x +-800 m, with the gold of their rings where they meet the floor.
    for side in (-1, 1):
        dx = np.abs(X - side * half_x) / cv.px
        span = ay <= reach
        paint(cv.img, cover(dx - 3.2 * s) * span, INK)
        paint(cv.img, cover(dx - 2.0 * s) * span, CAP)
        for r in (0.0,) + drum.CAP_RINGS:
            for sy in ((1,) if r == 0 else (-1, 1)):
                tick = np.maximum(dx - 2.0 * s, np.abs(Y - sy * r) / cv.px - .9 * s)
                paint(cv.img, cover(tick) * span, GOLD_D)


# ---------------------------------------------------------------- glyphs (no text)

def glyph(cv, x, y, radius_px, draw):
    win = cv.window(x, y, radius_px + 2)
    if win is not None:
        sl, u, w = win
        region = cv.img[sl]
        draw(region, u, w)


def glyphs(cv):
    s = cv.s

    def orrery(img, u, w):              # three gold armillary rings round a light-blue sphere
        for turn in (0.0, math.pi / 3, 2 * math.pi / 3):
            e = np.abs(sd_ellipse(u, w, 12.5 * s, 4.6 * s, turn))
            paint(img, cover(e - 1.7 * s), INK)
        for turn in (0.0, math.pi / 3, 2 * math.pi / 3):
            e = np.abs(sd_ellipse(u, w, 12.5 * s, 4.6 * s, turn))
            paint(img, cover(e - .75 * s), GOLD_D)
        r = np.hypot(u, w)
        paint(img, cover(r - 3.6 * s), INK)
        paint(img, cover(r - 2.6 * s), BLUE_D)

    def archive(img, u, w):             # the round tower from above: white wall, gold ribbed dome, lantern
        r = np.hypot(u, w)
        paint(img, cover(r - 9.6 * s), INK)
        paint(img, cover(r - 8.5 * s), WHITE_D)
        paint(img, cover(r - 6.2 * s), GOLD_RICH)
        for k in range(8):
            a = 2 * math.pi * k / 8
            rib = sd_segment(u, w, (1.6 * s * math.cos(a), 1.6 * s * math.sin(a)), (6.0 * s * math.cos(a), 6.0 * s * math.sin(a)))
            paint(img, cover(rib - .45 * s), GOLD_D)
        paint(img, cover(r - 1.9 * s), INK)
        paint(img, cover(r - 1.2 * s), WHITE_D)

    def pylon(img, u, w):               # a crystal-crowned pylon: diamond in white with a light-blue heart
        d = (np.abs(u) + np.abs(w)) / math.sqrt(2)
        paint(img, cover(d - 9.0 * s / math.sqrt(2) - .8 * s), INK)
        paint(img, cover(d - 9.0 * s / math.sqrt(2)), WHITE_D)
        paint(img, cover(d - 5.2 * s / math.sqrt(2)), BLUE_D)
        paint(img, cover(np.hypot(u, w) - 1.1 * s), WHITE_D)

    def spire(img, u, w):               # the Spire of hardened light: a six-pointed star round a white core
        star = np.minimum(sd_triangle(u, w, 8.4 * s), sd_triangle(u, -w, 8.4 * s))
        paint(img, cover(star - 1.3 * s), INK)
        paint(img, cover(star), BLUE_D)
        inner = np.minimum(sd_triangle(u, w, 4.0 * s), sd_triangle(u, -w, 4.0 * s))
        paint(img, cover(inner), BLUE_LIGHT)
        paint(img, cover(np.hypot(u, w) - 2.0 * s), WHITE_D)

    def docks(img, u, w):               # the docking ring with its clamps, the AL nest red at its heart
        r = np.hypot(u, w)
        ring = np.abs(r - 10.5 * s)
        spokes = np.full(u.shape, 1e9)
        for k in range(6):
            a = 2 * math.pi * (k + .5) / 6
            spokes = np.minimum(spokes, sd_segment(u, w, (11 * s * math.cos(a), 11 * s * math.sin(a)), (15.5 * s * math.cos(a), 15.5 * s * math.sin(a))))
        paint(img, cover(np.minimum(ring - 2.1 * s, spokes - 2.0 * s)), INK)
        paint(img, cover(np.minimum(ring - 1.0 * s, spokes - .9 * s)), WHITE_D)
        paint(img, cover(r - 4.6 * s), INK)
        paint(img, cover(r - 3.6 * s), RED_D)

    def well(img, u, w):                # the Wellspring's garden ring and its pool of Divinity
        r = np.hypot(u, w)
        paint(img, cover(np.abs(r - 5.4 * s) - 1.6 * s), INK, .8)
        paint(img, cover(np.abs(r - 5.4 * s) - .7 * s), WHITE_D)
        paint(img, cover(r - 3.0 * s), BLUE_D)

    for (x, y), draw, radius in ((plan.WELL, well, 8), (plan.ORRERY, orrery, 15), (plan.ARCHIVE, archive, 11),
                                 (plan.TERRACE_PYLON, pylon, 11), (plan.RESERVOIR_PYLON, pylon, 11), (plan.FOUNDRY_PYLON, pylon, 11),
                                 (plan.SPIRE, spire, 15), (plan.DOCKS_ARENA, docks, 18)):
        glyph(cv, x, y, radius * s, draw)


# ---------------------------------------------------------------- the whole map

def render(size, extent_cm=EXTENT_CM, data=DATA):
    problems = []
    meta, H = load(data)
    G = drum.grid()
    stale = float(np.abs(G['H'].astype(np.float64) - H).max()) if G['H'].shape == H.shape else float('inf')
    if stale > .01:
        problems.append('height.bin differs from drum.py by up to %.2f m: rebuild it (Tools/build_physis_conclave.py) first' % stale)
    cv = Canvas(size, extent_cm)
    floor(cv, meta, H, G)
    roads(cv, G)
    counts = scatter(cv, data, problems)
    drum_frame(cv, meta)
    glyphs(cv)
    img, fixed, colours = quantise_checked(to_palette(cv.img))
    return img, {'problems': problems, 'scatter_drawn': counts, 'palette_regreyed': fixed, 'colours': colours}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, default=1024)
    parser.add_argument('--extent', type=float, default=EXTENT_CM, help='half-width shown, cm')
    parser.add_argument('--data', default=str(DATA), help='folder with height.bin, height.json and scatter.json')
    parser.add_argument('--out', default=str(ROOT / 'Art/UI/T_UI_MapConclave.png'))
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    img, info = render(args.size, args.extent, Path(args.data))
    write_png(args.out, img)
    print('map', args.out, img.shape, 'extent_cm', args.extent, 'm/px', round(2 * args.extent / 100 / args.size, 3))
    print('  %d colours, all in the palette (%d re-greyed after 8-bit rounding)' % (info['colours'], info['palette_regreyed']))
    print('  drawn from scatter.json:', info['scatter_drawn'])
    for p in info['problems']:
        print('  warning:', p)


if __name__ == '__main__':
    main()
