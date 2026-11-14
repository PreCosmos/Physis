"""The Conclave's foliage atlas (T_CN_LeafAtlas_M / _N), made with numpy alone: four 'cards' that al_flora.py maps
onto quads, two by two (u to the right, v down, cell (column, row)):
  (0, 0) a broadleaf twig: alternate ovate leaves on a twig rising from the bottom centre (red and white trees,
         shrubs, hedges, the orchard)
  (1, 0) a blossom spray: five-petalled flowers and a few young leaves on a forked twig (the white tree)
  (0, 1) a grass clump: tapering blades rising from the bottom, three seed stems (golden grass, wheat, reeds)
  (1, 1) a conifer spray: needles along a stem and its side shoots (the black conifer)
Channels like the detail sets' (linear data): _M R albedo factor (0.5 = the vertex colour), G roughness factor,
B stem mask (1 on twigs, stems and petioles: the material colours them its StemColour, so wood is never leaf-coloured),
A opacity (the material is masked at 0.5; the mips keep their alpha coverage). _N is the tangent normal of the cards'
relief (leaves fold along the midrib and cup, veins and needles stand out). Greyscale data again: every hue comes from
the vertex colour (palette) or StemColour.

Run: PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/conclave_textures/atlas.py
     [--size 2048] [--sheet]   (writes Art/Textures/Conclave/T_CN_LeafAtlas_M.png, _N.png; --sheet a preview)
"""
import argparse
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import textures as T  # noqa: E402  (png writer, blur, noise)

F32 = np.float32


class Canvas:
    """One atlas cell: painter's-order compositing of value channels, alpha as union."""

    def __init__(self, c):
        self.c = c
        self.alb = np.full((c, c), .5, F32)
        self.rough = np.full((c, c), .5, F32)
        self.stem = np.zeros((c, c), F32)
        self.alpha = np.zeros((c, c), F32)
        self.h = np.zeros((c, c), F32)

    def put(self, x0, y0, cover, alb, rough, stem, h):
        """Composites a patch whose top-left pixel is (x0, y0); values are arrays the patch's shape or scalars."""
        hh, ww = cover.shape
        xa, ya = max(x0, 0), max(y0, 0)
        xb, yb = min(x0 + ww, self.c), min(y0 + hh, self.c)
        if xa >= xb or ya >= yb:
            return
        sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
        dst = (slice(ya, yb), slice(xa, xb))
        k = cover[sl]

        def part(v):
            return v[sl] if isinstance(v, np.ndarray) else v
        for name, value in (('alb', alb), ('rough', rough), ('stem', stem), ('h', h)):
            plane = getattr(self, name)
            plane[dst] = plane[dst] * (1 - k) + part(value) * k
        self.alpha[dst] = 1 - (1 - self.alpha[dst]) * (1 - k)


def patch_grid(xmin, xmax, ymin, ymax):
    x0, y0 = int(math.floor(xmin)), int(math.floor(ymin))
    xs = np.arange(x0, int(math.ceil(xmax)) + 1, dtype=F32) + .5
    ys = np.arange(y0, int(math.ceil(ymax)) + 1, dtype=F32) + .5
    return x0, y0, xs[None, :], ys[:, None]


def stroke(cv, pts, widths, alb, rough=.55, stem=1.0, h0=1.0, hlift=0.0):
    """A tapered stem along the polyline pts (pixels) with per-point widths: a chain of capsules, round in section."""
    pts = np.asarray(pts, F32)
    widths = np.asarray(widths, F32)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        wa, wb = widths[i] / 2, widths[i + 1] / 2
        r = max(wa, wb) + 2
        x0, y0, X, Y = patch_grid(min(a[0], b[0]) - r, max(a[0], b[0]) + r, min(a[1], b[1]) - r, max(a[1], b[1]) + r)
        d = b - a
        ln2 = max(float(d @ d), 1e-6)
        t = np.clip(((X - a[0]) * d[0] + (Y - a[1]) * d[1]) / ln2, 0, 1)
        px, py = a[0] + t * d[0] - X, a[1] + t * d[1] - Y
        dist = np.sqrt(px * px + py * py)
        w = wa + (wb - wa) * t
        cover = np.clip(w - dist + .5, 0, 1)
        prof = np.sqrt(np.clip(1 - (dist / np.maximum(w, .5)) ** 2, 0, 1))
        cv.put(x0, y0, cover, alb, rough, stem, h0 * prof * np.maximum(w, 1) * .5 + hlift)


def leaf(cv, rng, base, angle, length, width, tone, fold=.6, serrate=.03, lift=0.0):
    """An ovate leaf from base (pixels) pointing along angle (radians, 0 = +u, -pi/2 = up the image): folded along
    its midrib, cupped, with a raised midrib, side veins and a darker rim."""
    ca, sa = math.cos(angle), math.sin(angle)
    tip = (base[0] + ca * length, base[1] + sa * length)
    r = width * .6 + 3
    x0, y0, X, Y = patch_grid(min(base[0], tip[0]) - r, max(base[0], tip[0]) + r, min(base[1], tip[1]) - r, max(base[1], tip[1]) + r)
    dx, dy = X - base[0], Y - base[1]
    s = (dx * ca + dy * sa) / length                       # 0 at the base, 1 at the tip
    q = -dx * sa + dy * ca                                 # across, pixels
    sc = np.clip(s, 0, 1)
    half = width / 2 * np.sin(math.pi * sc ** .8) ** .75 * (1 - .2 * sc) * (1 + serrate * np.sin(sc * 46 * math.pi))
    edge = half - np.abs(q)
    cover = np.clip(edge + .5, 0, 1) * np.clip(s * length + .5, 0, 1) * np.clip((1 - s) * length + .5, 0, 1)
    qn = np.clip(np.abs(q) / np.maximum(half, 1), 0, 1)
    vein_phase = sc * 9 - qn * 1.4
    veins = np.exp(-((vein_phase - np.round(vein_phase)) / .07) ** 2) * (qn > .08) * (qn < .85)
    midrib = np.exp(-(q / max(width * .035, 1.2)) ** 2)
    h = (1 - qn) * fold * width * .25 + (1 - qn * qn) * width * .12 + midrib * width * .05 - veins * width * .015 + lift
    rim = np.clip(1 - edge / max(width * .08, 1), 0, 1)
    alb = tone + .12 * midrib + .06 * veins - .12 * rim + .06 * (sc - .5)
    rough = .45 + .15 * veins + .1 * rim
    cv.put(x0, y0, cover, alb, rough, 0.0, h)
    return tip


def petal_flower(cv, rng, centre, radius, tone, lift=0.0):
    """A five-petalled blossom seen roughly face-on: cupped petals round a small darker centre."""
    rot = rng.uniform(0, 2 * math.pi)
    for k in range(5):
        a = rot + k * 2 * math.pi / 5 + rng.uniform(-.12, .12)
        base = (centre[0] + math.cos(a) * radius * .15, centre[1] + math.sin(a) * radius * .15)
        leaf(cv, rng, base, a, radius * .95, radius * .78, tone + rng.uniform(-.04, .04), fold=.15, serrate=.0, lift=lift)
    r = radius * .22
    x0, y0, X, Y = patch_grid(centre[0] - r - 2, centre[0] + r + 2, centre[1] - r - 2, centre[1] + r + 2)
    d = np.hypot(X - centre[0], Y - centre[1])
    cover = np.clip(r - d + .5, 0, 1)
    cv.put(x0, y0, cover, tone - .25, .6, 0.0, lift + radius * .25 + np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1)) * r * .4)


def bez(p0, p1, p2, n):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.asarray(p0, F32) + 2 * (1 - t) * t * np.asarray(p1, F32) + t * t * np.asarray(p2, F32)


def broadleaf(c, rng):
    cv = Canvas(c)
    twig = bez((c * .5, c * .99), (c * .47, c * .55), (c * .54, c * .1), 40)
    stroke(cv, twig, np.linspace(c * .022, c * .006, 40), .3)
    count = 11
    for k in range(count):
        t = .14 + .84 * k / (count - 1)
        i = int(t * 39)
        p = twig[i]
        side = 1 if k % 2 else -1
        tang = twig[min(i + 1, 39)] - twig[max(i - 1, 0)]
        up = math.atan2(tang[1], tang[0])
        a = up + side * rng.uniform(.6, 1.0)
        L = c * (.36 - .14 * t) * rng.uniform(.9, 1.1)
        pet = (p[0] + math.cos(a) * c * .035, p[1] + math.sin(a) * c * .035)
        stroke(cv, [p, pet], [c * .007, c * .005], .32)
        leaf(cv, rng, pet, a + side * rng.uniform(-.15, .2), L, L * .46, .5 + rng.uniform(-.08, .08), lift=c * .01)
    leaf(cv, rng, twig[-1], math.atan2(twig[-1][1] - twig[-4][1], twig[-1][0] - twig[-4][0]), c * .2, c * .09, .55, lift=c * .01)
    return cv


def blossom(c, rng):
    cv = Canvas(c)
    main = bez((c * .5, c * .99), (c * .5, c * .6), (c * .46, c * .14), 40)
    stroke(cv, main, np.linspace(c * .02, c * .006, 40), .3)
    forks = []
    for t, side in ((.35, 1), (.5, -1), (.68, 1), (.8, -1)):
        p = main[int(t * 39)]
        end = (p[0] + side * c * rng.uniform(.25, .33), p[1] - c * rng.uniform(.12, .2))
        f = bez(p, (p[0] + side * c * .1, p[1] - c * .02), end, 20)
        stroke(cv, f, np.linspace(c * .011, c * .004, 20), .3)
        forks.append(f)
    for f in forks + [main[16:]]:
        for k in range(3):
            q = f[int(rng.uniform(.2, .9) * (len(f) - 1))]
            a = rng.uniform(0, 2 * math.pi)
            leaf(cv, rng, q, a, c * .12, c * .055, .42, lift=c * .005)
    spots = np.concatenate([f[::3] for f in forks] + [main[8::3]])
    for p in spots:
        for _ in range(2):
            centre = (p[0] + rng.normal(0, c * .03), p[1] + rng.normal(0, c * .03))
            petal_flower(cv, rng, centre, c * rng.uniform(.045, .06), .62 + rng.uniform(-.05, .05), lift=c * .02)
    return cv


def grass(c, rng):
    cv = Canvas(c)
    for k in range(52):
        x = c * (.5 + rng.normal(0, .09))
        h = c * rng.uniform(.5, .97)
        lean = rng.normal(0, .22) + (x / c - .5) * 1.2
        top = (x + lean * h * .6, c - h)
        mid = (x + lean * h * .15, c - h * .6)
        pts = bez((x, c * 1.0), mid, top, 36)
        w = c * rng.uniform(.012, .02) * (1 - np.linspace(0, 1, 36) ** 1.4) + 1
        tone = .42 + rng.uniform(-.08, .08)
        stroke(cv, pts, w, tone, .55, 0.0, 1.0, hlift=k * .02)
        # sun-bleached tips: a paler pass over the top third
        stroke(cv, pts[24:], w[24:] * .9, tone + .14, .6, 0.0, 1.0, hlift=k * .02 + .01)
    for k in range(3):
        x = c * (.5 + rng.normal(0, .05))
        top = (x + rng.normal(0, c * .08), c * rng.uniform(.03, .1))
        pts = bez((x, c), (x, c * .5), top, 30)
        stroke(cv, pts, np.linspace(c * .007, c * .004, 30), .5, .6, 0.0)
        for j in range(9):
            p = pts[-1 - j]
            for side in (-1, 1):
                a = -math.pi / 2 + side * rng.uniform(.5, 1.0) + rng.normal(0, .1)
                leaf(cv, rng, p, a, c * .04, c * .014, .6, fold=.3, serrate=0, lift=c * .02)
    return cv


def conifer(c, rng):
    cv = Canvas(c)
    main = bez((c * .5, c * .99), (c * .52, c * .55), (c * .5, c * .04), 50)
    shoots = [main]
    for t, side in ((.25, -1), (.35, 1), (.48, -1), (.58, 1), (.7, -1), (.8, 1)):
        p = main[int(t * 49)]
        L = c * (.42 - .25 * t)
        end = (p[0] + side * L * .9, p[1] - L * .55)
        shoots.append(bez(p, (p[0] + side * L * .5, p[1] - L * .05), end, 24))
    for s in shoots:
        n = len(s)
        width = np.linspace(c * (.018 if s is main else .01), c * .004, n)
        stroke(cv, s, width, .3)
        for i in range(1, n - 1):
            p = s[i]
            tang = s[i + 1] - s[i - 1]
            a0 = math.atan2(tang[1], tang[0])
            f = i / n
            for side in (-1, 1):
                for _ in range(4):
                    a = a0 + side * rng.uniform(.6, 1.2)
                    L = c * rng.uniform(.04, .065) * (1.1 - .4 * f)
                    tip = (p[0] + math.cos(a) * L, p[1] + math.sin(a) * L)
                    stroke(cv, [p, tip], [c * .006, c * .002], .45 + rng.uniform(-.1, .1), .5, 0.0, 1.0, hlift=c * .004)
    return cv


CELLS = ((0, 0, broadleaf), (1, 0, blossom), (0, 1, grass), (1, 1, conifer))


def dilate(value, alpha, passes=6):
    """Fills transparent texels with the alpha-weighted blur of their neighbours, wider each pass, so mips never pull
    in the background (dark or bright halos round the leaves)."""
    out = value.copy()
    have = alpha > .5
    for k in range(passes):
        sigma = 2.0 * 2 ** k
        num = T.blur(np.where(have, out, 0).astype(F32), sigma)
        den = T.blur(have.astype(F32), sigma)
        fill = num / np.maximum(den, 1e-4)
        out = np.where(have, out, np.where(den > 1e-3, fill, out))
        have = have | (den > 1e-3)
    return out


def build(n=2048, seed=11):
    c = n // 2
    full = {k: np.zeros((n, n), F32) for k in ('alb', 'rough', 'stem', 'alpha', 'h')}
    full['alb'][:] = .5
    full['rough'][:] = .5
    for i, (col, row, make) in enumerate(CELLS):
        cv = make(c, np.random.default_rng(seed + i))
        ys, xs = slice(row * c, (row + 1) * c), slice(col * c, (col + 1) * c)
        for k in full:
            full[k][ys, xs] = getattr(cv, k)
    alpha = full['alpha']
    alb = dilate(np.clip(full['alb'], 0, 1), alpha)
    rough = dilate(np.clip(full['rough'], 0, 1), alpha)
    stem = dilate(np.clip(full['stem'], 0, 1), alpha)
    h = full['h'] * (alpha > .02)
    nx, ny, nz = T.normals(T.blur(h, .7), 1.0 / .9)        # heights are in pixels: slope as drawn, softened a little
    flat = alpha < .02
    nx, ny, nz = np.where(flat, 0, nx), np.where(flat, 0, ny), np.where(flat, 1, nz)
    return {'m': (alb, rough, stem, alpha), 'n': (nx * .5 + .5, ny * .5 + .5, nz * .5 + .5)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--sheet', action='store_true')
    args = ap.parse_args()
    maps = build(args.size)
    T.OUT.mkdir(parents=True, exist_ok=True)
    T.png(T.OUT / 'T_CN_LeafAtlas_M.png', maps['m'])
    T.png(T.OUT / 'T_CN_LeafAtlas_N.png', maps['n'])
    if args.sheet:
        alb, rough, stem, alpha = maps['m']
        k = args.size // 1024
        def down(a):
            return a.reshape(1024, k, 1024, k).mean(axis=(1, 3))
        a, al, st = down(alpha), down(alb), down(stem)
        nx, ny, nz = (down(v) * 2 - 1 for v in maps['n'])
        light = np.array([-.4, -.5, .77]); light /= np.linalg.norm(light)
        ndl = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
        leafc = np.array([.6, .02, .02], F32)                 # previewed in red; stems black
        col = (leafc[None, None, :] * (1 + .8 * (2 * al - 1))[..., None] * (1 - st[..., None]) + .015 * st[..., None]) * (.25 + 1.5 * ndl)[..., None]
        bg = np.array([.75, .8, .85], F32)
        col = col * a[..., None] + bg * (1 - a[..., None])
        sheet = T.srgb(col)
        out = T.ROOT / 'Saved/Conclave/atlas_sheet.png'
        T.png(out, [sheet[..., i] for i in range(3)])
        print('sheet', out)
    print('atlas written', T.OUT / 'T_CN_LeafAtlas_M.png')


if __name__ == '__main__':
    main()
