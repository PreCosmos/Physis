"""Tileable PBR detail textures for the Conclave (level 3), made with numpy alone (no imaging library).

Run with the Kokoro venv's numpy (see Tools/conclave/README.md):
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/conclave_textures/textures.py \
      [--size 2048] [--only Stone,Gold] [--sheet] [--force]

Writes Art/Textures/Conclave/T_CN_<Set>_N.png and T_CN_<Set>_M.png for every set in SETS, textures.json (each set's
tile size in centimetres, which the materials sample at) and, with --sheet, Saved/Conclave/texture_sheet.png: every
set lit in a palette colour, in SETS order, four to a row, for review. A set that scans.py made from a scanned
surface (its textures.json 'for' starts with 'scan:') is kept, so a later run never overwrites the scan; --force
makes the procedural set again.

Both maps are linear data (import with sRGB off):
  _N  RGB tangent-space normal of the set's height: R = x along image columns (u, left to right), G = y along image
      rows (v, top to bottom), B = z out of the surface, 128 = 0. The material samples it at uv = position / tile, so
      on a plane u runs along that plane's first axis and v along its second.
  _M  RGBA: R albedo factor (mean 0.5; base colour x (1 + AlbedoDetail x (2R - 1))), G roughness factor (mean 0.5;
      roughness = base + RoughDetail x (2G - 1)), B cavity (1 open, lower in pits, joints and crevices), A the set's
      feature (veins, grout, joints, scratches, cracks, gaps), which the material colours and roughens.
Every map is greyscale data: hue comes only from the palette colour the material multiplies (vertex colour x Tint),
so no texture can bring a colour outside gold, light blue, red, green, black and white into the level (author's
rule, 2026-11-06; green added 2026-11-08). Heights are in centimetres at the set's real tile size, so the normals have real slopes.
"""
import argparse
import json
import math
import pathlib
import struct
import sys
import time
import zlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Textures/Conclave'
SHEET = ROOT / 'Saved/Conclave/texture_sheet.png'
F32 = np.float32


# ---------------------------------------------------------------- tileable building blocks

_FREQ = {}


def freqs(n):
    """Frequency grids (cycles per tile) of an n x n rfft2."""
    if n not in _FREQ:
        _FREQ[n] = ((np.fft.rfftfreq(n) * n).astype(F32)[None, :], (np.fft.fftfreq(n) * n).astype(F32)[:, None])
    return _FREQ[n]


def noise(n, seed, lo=1.0, hi=None, beta=1.0, stretch=1.0, angle=0.0):
    """Tileable fractal noise, zero mean and unit deviation: white noise shaped to amplitude f^-beta between lo and hi
    cycles per tile (soft edges). stretch > 1 makes features streak along `angle` (radians from the u axis)."""
    fx, fy = freqs(n)
    spec = np.fft.rfft2(np.random.default_rng(seed).standard_normal((n, n), dtype=F32))
    if stretch != 1.0:
        c, s = math.cos(angle), math.sin(angle)
        f = np.sqrt(((fx * c + fy * s) * stretch) ** 2 + (fy * c - fx * s) ** 2)
    else:
        f = np.sqrt(fx * fx + fy * fy)
    hi = hi or n / 2.0
    amp = np.where(f > 0, np.maximum(f, 1e-3) ** -beta, 0.0)
    amp = amp / (1.0 + np.exp(np.clip((lo - f) * 4.0 / max(lo, 1.0), -60, 60)))
    amp = amp / (1.0 + np.exp(np.clip((f - hi) * 4.0 / max(hi, 1.0), -60, 60)))
    out = np.fft.irfft2(spec * amp, s=(n, n)).astype(F32)
    out -= out.mean()
    return out / (out.std() + 1e-9)


def blur(img, sigma):
    """Periodic Gaussian blur; sigma in pixels."""
    fx, fy = freqs(img.shape[0])
    g = np.exp(-2.0 * (math.pi * sigma / img.shape[0]) ** 2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(img) * g, s=img.shape).astype(F32)


def grid(n):
    y, x = np.mgrid[0:n, 0:n].astype(F32)
    return (x + .5) / n, (y + .5) / n


def sample(img, x, y):
    """img at pixel coordinates (float arrays), wrapping, bilinear."""
    n = img.shape[0]
    x0, y0 = np.floor(x), np.floor(y)
    fx, fy = (x - x0).astype(F32), (y - y0).astype(F32)
    x0, y0 = x0.astype(np.int64) % n, y0.astype(np.int64) % n
    x1, y1 = (x0 + 1) % n, (y0 + 1) % n
    return (img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) + (img[y1, x0] * (1 - fx) + img[y1, x1] * fx) * fy


def voronoi(n, cells, seed, jitter=.9, warp=None, offsets=False):
    """Tileable jittered-grid Voronoi, `cells` per side: F1 and F2 (in cell widths) and each pixel's cell id; with
    offsets, also the pixel's position relative to its cell's point (cell widths). warp = (dx, dy) in pixels bends
    the borders."""
    pts = .5 + (np.random.default_rng(seed).random((cells, cells, 2), dtype=F32) - .5) * jitter
    y, x = np.mgrid[0:n, 0:n].astype(F32)
    if warp is not None:
        x, y = x + warp[0], y + warp[1]
    px, py = (x + .5) * cells / n, (y + .5) * cells / n
    cx, cy = np.floor(px).astype(np.int32), np.floor(py).astype(np.int32)
    f1 = np.full((n, n), 9.0, F32)
    f2 = f1.copy()
    ids = np.zeros((n, n), np.int32)
    rx = np.zeros((n, n), F32) if offsets else None
    ry = np.zeros((n, n), F32) if offsets else None
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            gx, gy = cx + dx, cy + dy
            wx, wy = gx % cells, gy % cells
            ox, oy = px - (gx + pts[wy, wx, 0]), py - (gy + pts[wy, wx, 1])
            d = np.hypot(ox, oy)
            nearer = d < f1
            f2 = np.where(nearer, f1, np.minimum(f2, d))
            ids = np.where(nearer, wy * cells + wx, ids)
            f1 = np.where(nearer, d, f1)
            if offsets:
                rx = np.where(nearer, ox, rx)
                ry = np.where(nearer, oy, ry)
    return (f1, f2, ids, rx, ry) if offsets else (f1, f2, ids)


def per_cell(ids, seed, count):
    """A random value in 0..1 per Voronoi cell, looked up per pixel."""
    return np.random.default_rng(seed).random(count, dtype=F32)[ids]


def strokes(n, count, seed, length, width, depth=(1.0, 1.0), angle=None, spread=math.pi, field=None, taper=.6,
            combine='max', bend=None):
    """Tileable anti-aliased line strokes, as height. length and width are (min, max) pixel ranges; directions are
    around `angle` within +-spread/2 (any when angle is None), or follow `field` (an angle per pixel) if given. Each
    stroke peaks at a random depth in `depth` along its middle and thins toward its ends (taper). combine 'max' layers
    them (blades over blades), 'add' sums them (scratches). bend, a (min, max) curvature in 1/pixels, curves each
    stroke either way along a parabola (a plasterer's float sweeps arcs); without it strokes are straight and the
    generator draws exactly what it always drew."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), F32)
    for _ in range(count):
        cx, cy = rng.random(2) * n
        if field is not None:
            a = float(field[int(cy) % n, int(cx) % n]) + rng.normal(0, .15)
        elif angle is None:
            a = rng.random() * math.pi * 2
        else:
            a = angle + (rng.random() - .5) * spread
        ln = rng.uniform(*length)
        w = rng.uniform(*width)
        h = rng.uniform(*depth)
        k = rng.uniform(*bend) * rng.choice((-1.0, 1.0)) if bend is not None else 0.0
        sag = abs(k) * (ln / 2) ** 2 / 2                  # how far the curve leaves its chord, pixels
        dx, dy = math.cos(a), math.sin(a)
        ex, ey = abs(dx) * ln / 2 + w + 2 + sag, abs(dy) * ln / 2 + w + 2 + sag
        xs = np.arange(int(cx - ex), int(cx + ex) + 1)
        ys = np.arange(int(cy - ey), int(cy + ey) + 1)
        if len(xs) >= n or len(ys) >= n:
            continue
        px = xs[None, :] + .5 - cx
        py = ys[:, None] + .5 - cy
        t = px * dx + py * dy                       # along the stroke, from its middle
        across = -px * dy + py * dx
        if k:
            across = across - k * t * t / 2
        d = np.abs(across)                          # across it
        along = np.clip(1 - np.abs(t) / (ln / 2), 0, 1)
        half = w / 2 * along ** taper
        cover = np.clip(half - d + .5, 0, 1) * (along > 0)
        patch = (cover * h * np.sqrt(np.clip(1 - (d / np.maximum(half, .5)) ** 2, 0, 1))).astype(F32)
        index = np.ix_(ys % n, xs % n)
        out[index] = np.maximum(out[index], patch) if combine == 'max' else out[index] + patch
    return out


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def bumps(n, count, seed, radius, height):
    """Round pebbles or rivet heads: `count` spherical caps with radius in pixels (min, max), tileable, max-combined."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), F32)
    for _ in range(count):
        cx, cy = rng.random(2) * n
        r = rng.uniform(*radius)
        h = rng.uniform(*height)
        xs = np.arange(int(cx - r - 1), int(cx + r + 2))
        ys = np.arange(int(cy - r - 1), int(cy + r + 2))
        d2 = ((xs[None, :] + .5 - cx) ** 2 + (ys[:, None] + .5 - cy) ** 2) / (r * r)
        patch = (np.sqrt(np.clip(1 - d2, 0, 1)) * h).astype(F32)
        index = np.ix_(ys % n, xs % n)
        out[index] = np.maximum(out[index], patch)
    return out


# ---------------------------------------------------------------- the sets
# Each returns h (height, cm), alb and rough (variation, any scale: normalised to factors), cav (extra cavity 0..1,
# 1 = open) and feat (0..1). Pixel size is tile / n cm; helpers take pixels, so sizes are written as cm * PX.

class Set:
    def __init__(self, name, tile, make, colour, metal=False, feature=(0.0, 0.0, 0.0), note='', height_cavity=True):
        self.name, self.tile, self.make, self.colour, self.metal, self.feature, self.note = (
            name, tile, make, colour, metal, feature, note)
        self.height_cavity = height_cavity


def stone(n, px, s):
    """Honed white stone and marble: soft clouds, grey veins (feature) along the contours of a smooth, gently warped
    field (so they flow and branch like real veins and thicken where it is flat), fine grain, pores, waviness."""
    y, x = np.mgrid[0:n, 0:n].astype(F32)
    wx, wy = noise(n, s + 1, 1, 8, 2.0) * (.05 * n), noise(n, s + 2, 1, 8, 2.0) * (.05 * n)
    main = sample(noise(n, s + 3, 1, 5, 2.2), x + wx, y + wy) + .012 * noise(n, s + 14, 60, 700, .6)   # ragged edges
    side = sample(noise(n, s + 4, 2, 10, 2.0), x + wx * .6, y + wy * .6) + .008 * noise(n, s + 15, 60, 700, .6)
    hair = sample(noise(n, s + 11, 4, 24, 1.8), x + wx * .3, y + wy * .3)
    width = .035 + .035 * smoothstep(-1, 1, noise(n, s + 10, 1, 6, 1.6))
    veins = np.maximum(1 - smoothstep(0, width, np.abs(main)),
                       .7 * (1 - smoothstep(0, .025, np.abs(side))) * smoothstep(-.4, .8, noise(n, s + 12, 1, 6, 1.6)))
    veins = np.maximum(veins, .4 * (1 - smoothstep(0, .012, np.abs(hair))) * smoothstep(0, 1.2, noise(n, s + 13, 1, 6, 1.6)))
    halo = 1 - smoothstep(0, width * 5, np.abs(main))                   # stain bleeding a little beside the main veins
    feat = np.clip(veins + .18 * halo, 0, 1)
    grain = noise(n, s + 5, 120, n / 2, .2)
    cloud = noise(n, s + 6, 1, 40, 1.3)
    pores = smoothstep(2.9, 3.5, -noise(n, s + 7, 250, n / 2, 0))
    h = .03 * noise(n, s + 8, 2, 40, 1.6) + .004 * grain - .025 * pores - .002 * veins
    alb = .7 * cloud + .35 * grain - 1.5 * pores
    rough = .45 * noise(n, s + 9, 12, 400, .8) + .3 * grain + 2.0 * pores + .4 * veins
    return h, alb, rough, 1 - .6 * pores, feat


def basalt(n, px, s):
    """Black stone, slate and soot: salt-and-pepper grain, cleavage layers, vesicles; feature = mica glints."""
    grain = noise(n, s + 1, 180, n / 2, .1)
    mid = noise(n, s + 2, 6, 96, 1.0)
    cleave = noise(n, s + 3, 2, 64, 1.3, stretch=6, angle=.35)
    vesicles = smoothstep(2.7, 3.3, noise(n, s + 4, 120, 600, .3))
    glint = smoothstep(3.0, 3.6, noise(n, s + 5, 300, n / 2, 0))
    h = .09 * cleave + .03 * mid + .006 * grain - .05 * vesicles
    alb = .5 * grain + .45 * mid + .25 * cleave - 1.2 * vesicles
    rough = .5 * mid + .3 * grain + .8 * vesicles
    return h, alb, rough, 1 - .7 * vesicles, glint


def gold(n, px, s):
    """Polished gold metal: shallow hammered dimples in patches, fine brushing, sparse fine scratches (feature) and
    tarnish. Deeper dimples and three times the scratches read as glitter at grazing angles (2026-11-07 review)."""
    warp = noise(n, s + 1, 2, 24, 1.3) * 6, noise(n, s + 2, 2, 24, 1.3) * 6
    f1, f2, ids = voronoi(n, int(round(n * px / 2.0)), s + 3, .95, warp)     # dimples about 2 cm across
    hammer = smoothstep(-.6, .5, noise(n, s + 4, 1, 6, 1.4))
    dimple = (f1 ** 2) * (.8 + .4 * per_cell(ids, s + 5, int(round(n * px / 2.0)) ** 2))
    brushed = noise(n, s + 6, 3, n / 2, .45, stretch=40)
    scratches = strokes(n, int(n * .15), s + 7, (.4 / px, 6.0 / px), (.6, 1.8), (.3, 1.0), combine='add')
    scratches = np.clip(scratches, 0, 1)
    tarnish = noise(n, s + 8, 1, 12, 1.6)
    h = .015 * dimple * hammer + .0006 * brushed - .0015 * scratches
    alb = .12 * tarnish + .04 * brushed
    rough = .6 * brushed * (1 - hammer) + .4 * noise(n, s + 9, 2, 40, 1.2) + .5 * smoothstep(1.4, 2.6, noise(n, s + 10, 6, 60, 1))
    return h, alb, rough, np.ones((n, n), F32), scratches


def steel(n, px, s):
    """Dark steel and iron: strong brushing, pitting, scratches (feature), grime in patches."""
    brushed = noise(n, s + 1, 3, n / 2, .4, stretch=60)
    pits = smoothstep(2.4, 3.2, noise(n, s + 2, 150, 900, .2)) * smoothstep(-.3, .8, noise(n, s + 3, 1, 8, 1.4))
    scratches = np.clip(strokes(n, int(n * .6), s + 4, (.3 / px, 8.0 / px), (.6, 2.0), (.3, 1.0), combine='add'), 0, 1)
    grime = noise(n, s + 5, 1, 16, 1.5)
    h = .0008 * brushed - .01 * pits - .002 * scratches + .004 * noise(n, s + 6, 2, 30, 1.8)
    alb = .35 * grime + .1 * brushed - .8 * pits
    rough = .7 * brushed + .6 * grime + 1.2 * pits
    return h, alb, rough, 1 - .5 * pits, scratches


def lacquer(n, px, s):
    """Gloss paint and lacquer: orange peel, swirl and hairline scratches (feature), settled dust."""
    peel = noise(n, s + 1, n * px / .5, n * px / .12, .9)          # bumps 1.2 to 5 mm
    swirls = np.clip(strokes(n, int(n * .25), s + 2, (1.0 / px, 6.0 / px), (.5, 1.2), (.2, .7), combine='add'), 0, 1)
    dust = smoothstep(-.2, 1.5, noise(n, s + 3, 1, 16, 1.4))
    h = .0012 * peel - .0006 * swirls
    alb = .15 * noise(n, s + 4, 1, 16, 1.4) - .1 * dust
    rough = .3 * peel + 1.0 * dust + .3 * noise(n, s + 5, 8, 120, 1)
    return h, alb, rough, np.ones((n, n), F32), swirls


def plaster(n, px, s):
    """Red paint over plaster and red stone: trowel undulation, sand grain, hairline cracks (feature), wear."""
    trowel = noise(n, s + 1, 1, 14, 1.8)
    sand = noise(n, s + 2, 200, n / 2, .2)
    warp = noise(n, s + 3, 2, 30, 1.3) * 10, noise(n, s + 4, 2, 30, 1.3) * 10
    f1, f2, ids = voronoi(n, 7, s + 5, .9, warp)
    crack = (1 - smoothstep(0, .012, f2 - f1)) * (per_cell(ids, s + 6, 49) > .45) * smoothstep(-.2, .6, noise(n, s + 7, 1, 8, 1.4))
    mottle = noise(n, s + 8, 1, 30, 1.2)
    h = .06 * trowel + .005 * sand - .02 * crack
    alb = .55 * mottle + .25 * sand - .3 * crack
    rough = .4 * mottle + .35 * sand + .3 * trowel
    return h, alb, rough, 1 - .5 * crack, crack


def tile(n, px, s):
    """Light-blue glazed tiles, 10 cm: grout (feature), rounded edges, per-tile tilt and shade, glaze waviness."""
    tiles = int(round(n * px / 10.0))
    u, v = grid(n)
    a, b = u * tiles, v * tiles
    ia, ib = np.floor(a).astype(np.int32), np.floor(b).astype(np.int32)
    fa, fb = a - ia, b - ib
    edge = np.minimum(np.minimum(fa, 1 - fa), np.minimum(fb, 1 - fb)) * 10.0      # cm to the nearest tile edge
    grout = 1 - smoothstep(.10, .16, edge)
    bevel = np.sqrt(np.clip(edge / .28, 0, 1))
    rng = np.random.default_rng(s + 1)
    k = (ia % tiles) * tiles + (ib % tiles)
    tilt_x, tilt_y, shade, lift = (rng.normal(0, 1, tiles * tiles).astype(F32)[k] for _ in range(4))
    glaze = noise(n, s + 2, tiles * 1.5, tiles * 12, 1.2)
    craze = 1 - smoothstep(0, .02, np.subtract(*voronoi(n, tiles * 5, s + 3, .9)[1::-1]))
    h = (.03 * bevel + .004 * glaze + .006 * lift + .0012 * (tilt_x * (fa - .5) + tilt_y * (fb - .5)) * 10) * (1 - grout) - .05 * grout
    alb = .6 * shade + .2 * glaze
    rough = .4 * glaze + .8 * craze + 2.0 * grout
    return h, alb, rough, 1 - .7 * grout, grout


def cloth(n, px, s):
    """Plain-weave fabric, threads about 0.8 mm: over-under undulation, slubs, fibre fuzz (feature)."""
    threads = int(round(n * px / .08))
    u, v = grid(n)
    a, b = u * threads, v * threads
    ia, ib = np.floor(a), np.floor(b)
    fa, fb = a - ia - .5, b - ib - .5
    slub_a = np.random.default_rng(s + 1).normal(0, 1, threads).astype(F32)[ia.astype(np.int32) % threads]
    slub_b = np.random.default_rng(s + 2).normal(0, 1, threads).astype(F32)[ib.astype(np.int32) % threads]
    warp_w = .42 + .05 * slub_a
    weft_w = .42 + .05 * slub_b
    warp_p = np.sqrt(np.clip(1 - (fa / warp_w) ** 2, 0, 1))
    weft_p = np.sqrt(np.clip(1 - (fb / weft_w) ** 2, 0, 1))
    warp_z = .5 + .5 * np.cos(math.pi * (b + ia))
    weft_z = .5 + .5 * np.cos(math.pi * (a + ib + 1))
    fibre = noise(n, s + 3, threads * 2, n / 2, .3)
    fuzz = smoothstep(1.2, 2.6, noise(n, s + 4, threads, n / 2, .2))
    surface = np.maximum(warp_p * (.55 + .45 * warp_z), weft_p * (.55 + .45 * weft_z))
    h = .03 * surface + .002 * fibre
    alb = .3 * (slub_a + slub_b) + .5 * surface + .3 * noise(n, s + 5, 1, 12, 1.3)
    rough = .5 * fibre + .5 * fuzz
    return h, alb, rough, .55 + .45 * surface, fuzz


def flagstone(n, px, s):
    """Paved white stone: irregular flags about 60 cm with joints (feature), chipped edges, tilt and pitting."""
    cells = int(round(n * px / 60.0))
    warp = noise(n, s + 1, 2, 40, 1.4) * (3.0 / px), noise(n, s + 2, 2, 40, 1.4) * (3.0 / px)
    f1, f2, ids, rx, ry = voronoi(n, cells, s + 3, .85, warp, offsets=True)
    count = cells * cells
    gap = (f2 - f1) * (60.0 / 2)                                          # cm from the joint, roughly
    chips = noise(n, s + 4, 20, 300, .8)
    joint_w = .7 + .35 * chips                                           # cm
    joint = 1 - smoothstep(joint_w * .6, joint_w * 1.1, gap)
    edge_round = np.sqrt(np.clip(gap / 2.5, 0, 1))
    rng = np.random.default_rng(s + 5)
    sx, sy, lift, shade = (rng.normal(0, 1, count).astype(F32)[ids] for _ in range(4))
    tilt = (sx * rx + sy * ry) * 60.0 * .004       # each flag sits a little askew: slope about 0.4 %
    surface = .12 * noise(n, s + 6, 4, 120, 1.3) + .02 * noise(n, s + 7, 120, n / 2, .3)
    pits = smoothstep(3.1, 3.7, noise(n, s + 8, 60, 500, .3))
    h = (surface + .25 * lift + .3 * edge_round + tilt) * (1 - joint) - .4 * joint - .08 * pits
    alb = .7 * shade + .4 * noise(n, s + 9, 2, 60, 1.2) + .2 * noise(n, s + 10, 80, n / 2, .3) - .6 * pits
    rough = .5 * shade + .5 * noise(n, s + 11, 4, 120, 1.0) + 1.0 * joint + .8 * pits
    return h, alb, rough, 1 - .8 * joint - .4 * pits, joint


def grassmat(n, px, s):
    """Golden turf as a walker sees it, mostly at grazing angles: tussocks 5-15 cm across with dark soil gaps between
    (feature), each a dense stand of upright blade tips (bumps 3-8 mm proud) over short blades lying every way
    (1-3 cm) and a pale layer of long dead thatch underneath; pebbles show in the gaps. No flow field: combed blades
    read as fur. The layers are composited by height, so whatever stands highest gives the pixel its tone."""
    # Tussocks are the highs of a band-pass field (features 5-15 cm), gaps its deepest lows: irregular holes and short
    # channels, never the polygon network Voronoi cells drew (it read as cracked mud). The lawn thins in patches.
    tile = n * px
    field = (noise(n, s + 1, tile / 15.0, tile / 5.0, 1.0) + .35 * noise(n, s + 2, tile / 5.0, tile / 1.2, .6)
             + .8 * noise(n, s + 3, 1, 8, 1.3))
    gaps = 1 - smoothstep(-2.3, -1.7, field)
    stand = smoothstep(-1.9, -.9, field)
    crown = .6 * smoothstep(-1.2, 1.6, field)                                # cm: dense tussocks stand higher
    tips = bumps(n, int(n * n / 14), s + 4, (.1 / px, .25 / px), (.3, .8))   # upright tips 2-5 mm thick, 3-8 mm proud
    blades = strokes(n, int(n * n / 80), s + 5, (1.0 / px, 3.0 / px), (.12 / px, .28 / px), (.25, .6))
    thatch = strokes(n, int(n * n / 700), s + 6, (4.0 / px, 10.0 / px), (.08 / px, .16 / px), (.08, .2))
    pebbles = bumps(n, int(n * n / 24000), s + 7, (.25 / px, 1.0 / px), (.15, .45))
    tone = .25 * noise(n, s + 8, 30, n / 2, .5) + .35 * noise(n, s + 9, tile / 15.0, tile / 5.0, 1.0)
    # (height in cm or -1 where the layer is absent, albedo, roughness), bottom to top. A clump is a closed mass of
    # leaves, shaded inside (the mat), so soil shows only in the gaps; live grass is waxier than the dead thatch and
    # the soil; loose blades lie across the gaps too, but tips stand only in the clumps.
    layers = ((np.where(stand > .2, .1 + crown * .5 + .05 * noise(n, s + 10, 60, n / 2, .5), -1.0), -.35, .2),
              (np.where(thatch > .01, thatch + .05, -1.0), .9, .5),
              (np.where(blades > .01, blades + crown * .6, -1.0), .1, -.3),
              (np.where((tips > .01) & (stand > .5), tips + crown, -1.0), .35, -.3),
              (np.where(pebbles > .01, pebbles, -1.0), .6, -.4))
    h = .04 * noise(n, s + 11, 20, n / 2, .6)                                # the soil between
    alb = np.full((n, n), -1.0, F32)
    rough = np.full((n, n), .6, F32)
    covered = np.zeros((n, n), F32)
    for height, albedo, roughness in layers:
        cover = smoothstep(-.02, .02, height - h) * (height > 0)
        alb = alb + (albedo + tone - alb) * cover
        rough = rough + (roughness - rough) * cover
        covered = np.maximum(covered, cover)
        h = np.maximum(h, height)
    feat = (1 - covered) * (.6 + .4 * gaps)                                 # bare soil, darkest in the gaps
    return h, alb, rough, 1 - .7 * feat, feat


def soil(n, px, s):
    """Black soil, slag and silt: clods, crumbs, small stones and cracks (feature)."""
    cells = int(round(n * px / 7.0))
    bend = noise(n, s + 12, 4, 60, 1.3) * (1.2 / px), noise(n, s + 13, 4, 60, 1.3) * (1.2 / px)
    f1, f2, ids = voronoi(n, cells, s + 1, .95, bend)
    c1, c2, cid = voronoi(n, cells * 3, s + 14, .95, bend)
    big = smoothstep(0, .35, f2 - f1) * (.4 + .9 * per_cell(ids, s + 2, cells * cells))
    small = smoothstep(0, .3, c2 - c1) * (.3 + .6 * per_cell(cid, s + 15, cells * cells * 9))
    keep = per_cell(ids, s + 16, cells * cells) > .35                       # some ground is crumb only
    clod = np.where(keep, np.maximum(big, small * .7), small * .6) * (.75 + .25 * noise(n, s + 17, 30, 300, .8))
    crumbs = noise(n, s + 3, n * px / 1.2, n / 2, .4)
    stones = bumps(n, int(n * n / 9000), s + 4, (.3 / px, 1.4 / px), (.3, .8))
    warp = noise(n, s + 5, 2, 30, 1.3) * 12, noise(n, s + 6, 2, 30, 1.3) * 12
    g1, g2, gid = voronoi(n, 6, s + 7, .9, warp)
    crack = (1 - smoothstep(0, .02, g2 - g1)) * (per_cell(gid, s + 8, 36) > .4)
    h = .9 * clod + .08 * crumbs + stones - .8 * crack + .3 * noise(n, s + 9, 1, 12, 1.6)
    alb = .4 * per_cell(ids, s + 10, cells * cells) + .3 * crumbs + 1.0 * (stones > .05) - .6 * crack
    rough = .3 * crumbs - .5 * (stones > .05) + .4 * noise(n, s + 11, 2, 40, 1.2)
    return h, alb, rough, 1 - .7 * crack, crack


def sand(n, px, s):
    """White shore sand: low wind ripples about 8 cm apart, strong grain, a few shell and pebble bits (feature). It is
    quieter than the first pass (2026-11-07 review): half the ripple contrast, denser ripples, half the bits."""
    u, v = grid(n)
    waves = int(round(n * px / 8.0))
    phase = 2 * math.pi * waves * v + 2.2 * noise(n, s + 1, 1, 10, 1.6) + .4 * noise(n, s + 2, 4, 40, 1.2)
    ripple = np.sin(phase) + .35 * np.sin(2 * phase + 1.1)                 # steep lee, gentle stoss
    amount = smoothstep(-1.0, .6, noise(n, s + 3, 1, 6, 1.5))
    grain = noise(n, s + 4, 300, n / 2, .1)
    bits = bumps(n, int(n * n / 60000), s + 5, (.15 / px, .7 / px), (.1, .3))
    h = .125 * ripple * amount + .006 * grain + bits + .3 * noise(n, s + 6, 1, 8, 1.7)
    alb = .5 * grain + .15 * ripple * amount + 1.2 * (bits > .02) + .3 * noise(n, s + 7, 1, 20, 1.3)
    rough = .6 * grain - .4 * (bits > .02) + .1 * ripple
    return h, alb, rough, np.ones((n, n), F32), (bits > .02).astype(F32)


def rock(n, px, s):
    """Rough rock for steep ground: ridged layers, strata, cracks (feature), lichen-free grit."""
    ridged = sum((1 - np.abs(noise(n, s + 1 + k, 2 ** k, 2 ** (k + 3), .8))) * .55 ** k for k in range(5))
    strata = noise(n, s + 7, 1, 40, 1.4, stretch=10, angle=.1)
    warp = noise(n, s + 8, 2, 30, 1.4) * 20, noise(n, s + 9, 2, 30, 1.4) * 20
    g1, g2, gid = voronoi(n, 5, s + 10, .9, warp)
    crack = 1 - smoothstep(0, .025, g2 - g1)
    h = 2.5 * ridged + 1.2 * strata - 2.0 * crack + .05 * noise(n, s + 11, 100, n / 2, .3)
    alb = .5 * ridged + .4 * strata - .8 * crack + .3 * noise(n, s + 12, 60, n / 2, .3)
    rough = .4 * ridged + .4 * noise(n, s + 13, 8, 200, .8)
    return h, alb, rough, 1 - .6 * crack, crack


def deck(n, px, s):
    """Grey metal deck: plates 100 x 50 cm with seams (feature), bolt heads, scuffs and dents."""
    u, v = grid(n)
    cols, rows = int(round(n * px / 100.0)), int(round(n * px / 50.0))
    a, b = u * cols, v * rows
    ia, ib = np.floor(a).astype(np.int32), np.floor(b).astype(np.int32)
    a = a + .5 * (ib % 2)                                                   # running bond
    ia = np.floor(a).astype(np.int32)
    fa, fb = a - ia, b - ib
    ex, ey = np.minimum(fa, 1 - fa) * 100.0, np.minimum(fb, 1 - fb) * 50.0  # cm to the seams
    seam = 1 - smoothstep(.15, .35, np.minimum(ex, ey))
    bolts = np.zeros((n, n), F32)
    for cx_cm in np.arange(5.0, 100.0, 10.0):
        for edge_cm in (3.0, 47.0):
            d = np.hypot(fa * 100.0 - cx_cm, fb * 50.0 - edge_cm)
            bolts = np.maximum(bolts, np.sqrt(np.clip(1 - (d / .9) ** 2, 0, 1)))
    k = (ia % cols) * rows + (ib % rows)                                   # the plate cut by the tile's edge is one plate
    plate = np.random.default_rng(s + 1).normal(0, 1, cols * rows).astype(F32)[k]
    scuffs = np.clip(strokes(n, int(n * .5), s + 2, (2 / px, 30 / px), (.8, 3.0), (.2, .8), angle=.1, spread=.6, combine='add'), 0, 1)
    dents = noise(n, s + 3, 2, 30, 1.6)
    h = .08 * dents + .3 * bolts - .25 * seam - .004 * scuffs
    alb = .4 * plate + .4 * noise(n, s + 4, 1, 16, 1.4) + .3 * scuffs
    rough = .5 * plate + .5 * noise(n, s + 5, 2, 60, 1.2) - .6 * scuffs
    return h, alb, rough, 1 - .6 * seam, np.maximum(seam, scuffs * .6)


def bark(n, px, s):
    """Tree bark (CN_Bark), fibres running along v (up a trunk: the material's side planes map v to height): vertical
    furrows between plates that crack across, fine fibres, and lenticel dashes (feature) as on birch."""
    y, x = np.mgrid[0:n, 0:n].astype(F32)
    bend = noise(n, s + 1, 1, 12, 1.5) * (2.0 / px)
    ridges = np.clip(1 - np.abs(sample(noise(n, s + 2, 2, 40, 1.2, stretch=7, angle=math.pi / 2), x + bend, y)), 0, 1)
    plates_w = noise(n, s + 3, 2, 30, 1.3) * (1.5 / px), noise(n, s + 4, 2, 30, 1.3) * (4.0 / px)
    cells = int(round(n * px / 6.0))
    f1, f2, ids = voronoi(n, cells, s + 5, .9, plates_w)
    crack = 1 - smoothstep(0, .06, f2 - f1)
    fibres = noise(n, s + 6, 20, n / 2, .5, stretch=12, angle=math.pi / 2)
    lent = smoothstep(2.3, 3.0, noise(n, s + 7, 30, 260, .6, stretch=6, angle=0.0))     # short dashes across the trunk
    h = .9 * ridges ** 1.5 + .15 * fibres - .5 * crack + .2 * per_cell(ids, s + 8, cells * cells)
    alb = .5 * ridges + .2 * fibres - .4 * crack + .3 * noise(n, s + 9, 1, 12, 1.3)
    rough = .3 * fibres + .4 * crack - .2 * ridges
    return h, alb, rough, 1 - .6 * crack, lent


def ripple(n, px, s):
    """Capillary ripples on water (M_CNWater samples only this set's normal): about 1.5 mm rms in waves 1-30 cm long,
    on a steep spectrum so the surface stays smooth. The masks are neutral (R .5, G .5, B 1, A 0)."""
    flat = np.zeros((n, n), F32)
    return .15 * noise(n, s + 1, 10, 300, 2.5), flat, flat, np.ones((n, n), F32), flat


# Laid stone (Setts, Paving): courses stacked along one image axis, pieces along the other, every course wrapping
# with the tile. A piece is indexed course * PIECES + its place in the course.
PIECES = 64


def _pieces(rng, total, lo, hi):
    """Lengths drawn lo..hi and scaled to fill total exactly, so the courses wrap with the tile."""
    lengths = rng.uniform(lo, hi, max(1, int(round(total / ((lo + hi) / 2)))))
    return lengths * (total / lengths.sum())


def _splittable(r, lo, hi):
    """Whether a length r divides into pieces each lo..hi long."""
    return math.ceil(r / hi - 1e-9) * lo <= r + 1e-9


def _joints(rng, total, lo, hi, avoid=(), gap=0.0, tries=500):
    """Joint positions (cm) round a course that wraps at total: every piece lo..hi long and no joint within gap of one
    in avoid (the neighbouring courses'), so joints stagger the way a mason lays them."""
    avoid = np.asarray(avoid, np.float64)

    def clear(x):
        return not len(avoid) or np.abs((x - avoid + total / 2) % total - total / 2).min() >= gap
    for _ in range(tries):
        start = rng.uniform(0, total)
        if not clear(start):
            continue
        joints = [start]
        while start + total - joints[-1] > hi:
            rest = start + total - joints[-1]
            for _draw in range(40):
                piece = rng.uniform(lo, hi)
                if _splittable(rest - piece, lo, hi) and clear(joints[-1] + piece):
                    joints.append(joints[-1] + piece)
                    break
            else:
                break                                    # this course is boxed in: start it again elsewhere
        else:
            return np.sort(np.mod(joints, total))        # the last piece closes on start, which is clear
    raise RuntimeError('no staggered course of %.0f cm in pieces of %.0f-%.0f cm' % (total, lo, hi))


def _staggered(rng, total, courses, lo, hi, gap):
    """Each course's joints, staggered from the course before and, for the last, from the first (they meet across
    the tile's edge)."""
    joints = []
    for k in range(courses):
        avoid = list(joints[-1]) if joints else []
        if k == courses - 1 and k:
            avoid += list(joints[0])
        joints.append(_joints(rng, total, lo, hi, avoid, gap))
    return joints


def _coursework(n, px, bounds, joints):
    """A laid surface, per pixel, with courses stacked along the first array axis (bounds: their edges, cm) and pieces
    along the second (joints: per course, cm): the piece's index, the distances to the nearest course edge and to the
    nearest joint (cm), the offsets from the piece's centre and its size, each on both axes. Arrays are [first axis,
    second axis], so a surface whose courses stack along u (image columns) takes their transposes."""
    at = (np.arange(n) + .5) * px
    total = n * px
    course = np.clip(np.searchsorted(bounds, at, 'right') - 1, 0, len(bounds) - 2)
    start, end = bounds[course], bounds[course + 1]
    ids = np.zeros((n, n), np.int32)
    d_b, off_b, size_b = (np.zeros((n, n), F32) for _ in range(3))
    for k, j in enumerate(joints):
        ext = np.concatenate([j[-1:] - total, j, j[:1] + total])
        i = np.searchsorted(ext, at, 'right') - 1
        lo, hi = ext[i], ext[i + 1]
        rows = course == k
        ids[rows] = k * PIECES + (i - 1) % len(j)
        d_b[rows] = np.minimum(at - lo, hi - at)
        off_b[rows] = at - (lo + hi) / 2
        size_b[rows] = hi - lo

    def across(values):
        return np.broadcast_to(values.astype(F32)[:, None], (n, n)).copy()
    return (ids, across(np.minimum(at - start, end - at)), d_b, across(at - (start + end) / 2), off_b,
            across(end - start), size_b)


def granite(n, s):
    """Granite's grain as albedo: fine speckle with dark mica and pale feldspar flecks."""
    return (.6 * noise(n, s, 300, n / 2, .1) - .8 * smoothstep(2.2, 3.0, noise(n, s + 1, 200, n / 2, .2))
            + .5 * smoothstep(2.4, 3.2, noise(n, s + 2, 120, n / 2, .3)))


def setts(n, px, s):
    """Granite setts for the roads, drawn in M_CNGround's road space (u along the road, v across it): straight courses
    10-14 cm wide follow one another along u, each a row of setts 12-20 cm long across the road with its joints
    staggered from its neighbours'. Joints 0.8-1.2 cm wide and 6 mm deep with grit in them, domed tops 3-4 mm high,
    chipped edges, every sett its own tone (+-18 %) and roughness (+-.1); feature = joints."""
    rng = np.random.default_rng(s + 1)
    tile = n * px
    bounds = np.concatenate([[0.0], np.cumsum(_pieces(rng, tile, 10.0, 14.0))])
    bounds[-1] = tile
    joints = _staggered(rng, tile, len(bounds) - 1, 12.0, 20.0, 3.0)
    ids, d_u, d_v, off_u, off_v, size_u, size_v = (a.T for a in _coursework(n, px, bounds, joints))
    tone, rough_k, lift, dome_k, tilt_u, tilt_v = (rng.uniform(-1, 1, len(joints) * PIECES).astype(F32)[ids]
                                                   for _ in range(6))
    edge = np.minimum(d_u, d_v)                                             # cm to the nearest joint's centre line
    half = .5 + .1 * np.clip(noise(n, s + 2, 30, 400, .8), -1, 1)           # joints 0.8-1.2 cm wide
    joint = 1 - smoothstep(half - px * .5, half + px * .5, edge)
    chips = smoothstep(1.1, 1.9, noise(n, s + 3, 40, 400, .9)) * (1 - smoothstep(0, 1.6, edge - half))
    arris = np.sqrt(np.clip((edge - half) / (.9 - .4 * chips), 0, 1))       # a chip breaks the rounded edge
    dome = np.clip(1 - np.abs(2 * off_u / size_u) ** 3, 0, 1) * np.clip(1 - np.abs(2 * off_v / size_v) ** 3, 0, 1)
    top = (.35 + .05 * dome_k) * dome + .08 * lift + .006 * (tilt_u * off_u + tilt_v * off_v) \
        + .01 * noise(n, s + 4, 60, n / 2, .5)
    grit = bumps(n, int(n * n / 300), s + 5, (.05 / px, .15 / px), (.05, .15)) + .03 * noise(n, s + 6, 100, n / 2, .3)
    floor = grit - .6
    h = floor + (top - floor) * arris - .3 * chips * arris
    alb = tone + .5 * granite(n, s + 7) + .4 * chips * (1 - joint) + .2 * dome - 1.4 * joint
    rough = rough_k + .3 * noise(n, s + 10, 60, n / 2, .4) - .4 * dome + 1.2 * joint + .5 * chips
    return h, alb, rough, 1 - .8 * joint - .35 * chips, joint


def paving(n, px, s):
    """Plaza ashlar: running courses 40, 50 or 60 cm wide (chosen per course) stacked along v, slabs 50-120 cm long
    along u with 4 mm joints staggered course to course; every slab its own tone (+-15 %) and a tilt of up to 0.3 %,
    chipped arrises, worn corners, and 5 % of the slabs cracked across by a Voronoi network (feature = joints and
    cracks). Straight courses, not crazy paving: a plaza is laid stone."""
    rng = np.random.default_rng(s + 1)
    tile = n * px
    while True:                                          # whole courses that add up to the tile exactly
        widths = []
        while sum(widths) < tile - 1e-6:
            widths.append(float(rng.choice((40.0, 50.0, 60.0))))
        if abs(sum(widths) - tile) < 1e-6:
            break
    bounds = np.concatenate([[0.0], np.cumsum(widths)])
    bounds[-1] = tile
    joints = _staggered(rng, tile, len(widths), 50.0, 120.0, 15.0)
    ids, d_v, d_u, off_v, off_u, size_v, size_u = _coursework(n, px, bounds, joints)
    count = len(joints) * PIECES
    tone, rough_k, lift, tilt_u, tilt_v = (rng.uniform(-1, 1, count).astype(F32)[ids] for _ in range(5))
    slabs = [k * PIECES + i for k, j in enumerate(joints) for i in range(len(j))]
    broken = np.zeros(count, F32)
    broken[rng.choice(slabs, max(1, int(round(len(slabs) * .05))), replace=False)] = 1
    edge = np.minimum(d_u, d_v)
    joint = 1 - smoothstep(.2 - px * .5, .2 + px * .5, edge)
    chips = smoothstep(1.3, 2.1, noise(n, s + 2, 60, 600, .9)) * (1 - smoothstep(0, 1.5, edge - .2))
    arris = np.sqrt(np.clip((edge - .2) / (.5 - .25 * chips), 0, 1))
    corner = (1 - smoothstep(0, 6, d_u)) * (1 - smoothstep(0, 6, d_v))     # feet and frost wear the corners down
    warp = noise(n, s + 3, 2, 40, 1.3) * (2.0 / px), noise(n, s + 4, 2, 40, 1.3) * (2.0 / px)
    f1, f2, _cell = voronoi(n, int(round(tile / 35.0)), s + 5, .9, warp)
    crack = (1 - smoothstep(0, .012, f2 - f1)) * broken[ids] * smoothstep(1.0, 2.0, edge)
    top = .08 * lift + .3 * (tilt_u * off_u + tilt_v * off_v) / 100.0 + .05 * noise(n, s + 6, 2, 40, 1.4) \
        + .012 * noise(n, s + 7, 80, n / 2, .4) - .25 * corner ** 1.5 - .1 * crack
    floor = -.25 + .03 * noise(n, s + 8, 150, n / 2, .3)
    h = floor + (top - floor) * arris - .25 * chips * arris
    stains = noise(n, s + 9, 1, 16, 1.4)
    alb = tone + .45 * granite(n, s + 10) + .15 * stains + .3 * chips - .3 * corner - 1.3 * joint - .8 * crack
    rough = .6 * rough_k + .3 * noise(n, s + 13, 40, n / 2, .5) + 1.0 * joint + .6 * crack + .4 * chips + .3 * corner
    return h, alb, rough, 1 - .8 * joint - .6 * crack - .3 * chips, np.maximum(joint, crack)


def render(n, px, s):
    """Lime render on the town's walls (CN_Plaster): trowel undulation of about 1.5 mm, sand grain, curved float marks,
    sparse hairline crazing, limewash in patches (+-12 %), drip streaks running down the wall (the triplanar side
    planes have v up) and a few spalls (feature): 3 mm recesses with a sharp lip where the render has come away and
    shows its coarse backing coat. No veins: render is not marble."""
    trowel = noise(n, s + 1, 1, 10, 1.8)
    grain = noise(n, s + 2, 250, n / 2, .2)
    # A float's passes, each a broad arc 20-80 cm in radius, overlapping about once over: they read in the sheen.
    floats = strokes(n, int(n * n / 26000), s + 3, (25.0 / px, 60.0 / px), (6.0 / px, 12.0 / px), (.2, .6), taper=.15,
                     combine='add', bend=(px / 80.0, px / 20.0))
    floats = floats / (floats.max() + 1e-6)
    f1, f2, _cell = voronoi(n, int(round(n * px / 4.0)), s + 4, .9)        # crazing cells about 4 cm
    craze = (1 - smoothstep(0, .02, f2 - f1)) * smoothstep(1.0, 1.8, noise(n, s + 5, 2, 16, 1.4))
    limewash = noise(n, s + 6, 1, 12, 1.4)
    drips = (smoothstep(.4, 2.2, noise(n, s + 7, 2, 24, 1.1, stretch=14, angle=math.pi / 2))
             * smoothstep(-.5, 1.0, noise(n, s + 11, 1, 6, 1.5)))           # soft, and broken along their run
    low = noise(n, s + 8, 2, 12, 1.4) + .08 * noise(n, s + 9, 20, 200, .8)  # ragged at the edge
    low = (low - low.min()) / (low.max() - low.min())
    spall = smoothstep(.8, .85, low)                                        # one to three per 2 m tile, up to 25 cm
    backing = noise(n, s + 10, 40, n / 2, .5)
    h = .15 * trowel + .006 * grain + .05 * floats - .015 * craze - .3 * spall + .03 * backing * spall
    alb = limewash + .25 * grain + .3 * floats - .5 * drips - .4 * craze - .6 * spall + .3 * backing * spall
    rough = .5 * grain - 1.6 * floats + .3 * limewash + .3 * craze + .8 * spall       # floated render is burnished
    return h, alb, rough, 1 - .5 * craze - .3 * spall, spall


def limestone(n, px, s):
    """Tooled limestone for the dressings (CN_White: quoins, sills, surrounds, mouldings, voussoirs): drove and claw
    chisel grooves, each patch one tool's work, pitting, fine grain and faint bedding bands along u; feature = small
    patches of black crust, the gypsum crust limestone grows where rain does not wash it."""
    drove = noise(n, s + 1, 150, 400, .6, stretch=30, angle=1.25)          # grooves 2.5-7 mm apart
    claw = noise(n, s + 2, 250, 600, .5, stretch=30, angle=2.15)           # the claw's finer teeth, at another angle
    claw_share = smoothstep(-.4, .4, noise(n, s + 3, 1, 6, 1.4))
    tooling = drove * (1 - claw_share) + claw * claw_share
    pits = bumps(n, int(n * n / 3500), s + 4, (.04 / px, .15 / px), (.02, .06))
    grain = noise(n, s + 5, 300, n / 2, .1)
    bedding = noise(n, s + 6, 1, 14, 1.6, stretch=12, angle=0.0)
    crust = smoothstep(1.4, 1.9, noise(n, s + 7, 3, 30, 1.3) + .3 * noise(n, s + 8, 30, 300, .8))
    h = .014 * tooling - pits + .004 * grain + .04 * noise(n, s + 9, 1, 12, 1.8) + .02 * crust * (1 + grain * .5)
    alb = .25 * tooling + .35 * grain + .5 * bedding - .8 * (pits > .005) - .4 * crust
    rough = .4 * tooling + .4 * grain + .6 * crust
    return h, alb, rough, 1 - .6 * (pits > .005), crust


# (name, tile cm, maker, preview colour (linear), metal?, preview feature colour (linear), what it is for). A set's seed
# is its index here, so new sets go at the end: inserting one would change every set after it.
SETS = [
    Set('Stone', 120, stone, (.82, .80, .76), feature=(.42, .42, .42), note='CN_White: stone, plaster, marble, porcelain'),
    Set('Basalt', 140, basalt, (.05, .05, .05), feature=(.20, .20, .20), note='CN_Black: black stone, slate, soot'),
    Set('Gold', 60, gold, (1.0, .766, .336), metal=True, feature=(.95, .80, .50), note='CN_Gold', height_cavity=False),
    Set('Steel', 80, steel, (.32, .32, .32), metal=True, feature=(.55, .55, .55), note='CN_Metal', height_cavity=False),
    Set('Lacquer', 80, lacquer, (.60, .02, .02), feature=(.70, .05, .05), note='CN_Lacquer', height_cavity=False),
    Set('Plaster', 120, plaster, (.60, .02, .02), feature=(.30, .005, .008), note='CN_Red'),
    Set('Tile', 60, tile, (.35, .60, .85), feature=(.78, .80, .82), note='CN_Blue: glazed tile'),
    Set('Cloth', 20, cloth, (.90, .90, .90), feature=(.90, .90, .90), note='CN_Cloth'),
    Set('Flagstone', 400, flagstone, (.82, .80, .76), feature=(.12, .12, .12), note='ground: roads and plazas'),
    Set('GrassMat', 200, grassmat, (.45, .30, .08), feature=(.015, .015, .016), note='ground: golden lawns'),
    Set('Soil', 200, soil, (.05, .05, .05), feature=(.015, .015, .016), note='ground: soil, slag, silt'),
    Set('Sand', 300, sand, (.85, .80, .70), feature=(.90, .90, .90), note='ground: shore sand'),
    Set('Rock', 400, rock, (.32, .32, .32), feature=(.05, .05, .05), note='ground: steep rock'),
    Set('Deck', 200, deck, (.12, .12, .12), metal=True, feature=(.32, .32, .32), note='ground: dock deck plates'),
    Set('Bark', 100, bark, (.78, .76, .72), feature=(.03, .03, .03), note='CN_Bark: tree bark'),
    Set('Ripple', 300, ripple, (.50, .72, .88), feature=(.90, .90, .90), note='water: capillary ripples',
        height_cavity=False),
    Set('Setts', 200, setts, (.82, .80, .76), feature=(.12, .12, .12), note='ground: road setts in road space'),
    Set('Paving', 600, paving, (.82, .80, .76), feature=(.12, .12, .12), note='ground: plaza ashlar'),
    Set('Render', 200, render, (.90, .90, .90), feature=(.42, .42, .42), note='CN_Plaster: lime render'),
    Set('Limestone', 100, limestone, (.65, .65, .65), feature=(.35, .35, .35), note='CN_White: tooled limestone'),
]


# ---------------------------------------------------------------- maps, files, preview

def factor(a, spread=.17):
    a = a - a.mean()
    return np.clip(.5 + a / (a.std() + 1e-9) * spread, 0, 1)


def normals(h, px):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px)
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px)
    inv = 1 / np.sqrt(gx * gx + gy * gy + 1)
    return -gx * inv, -gy * inv, inv


def cavity(h, px, radius_cm, depth_cm):
    d = blur(h, radius_cm / px) - h
    return np.clip(1 - np.maximum(d, 0) / depth_cm, 0, 1)


def png(path, channels):
    img = np.stack([np.clip(np.rint(c * 255), 0, 255).astype(np.uint8) for c in channels], -1)
    hgt, wid, k = img.shape
    rows = img.reshape(hgt, wid * k).astype(np.int16)
    sub = rows.copy()
    sub[:, k:] -= rows[:, :-k]                                   # PNG 'Sub' filter: much smaller files for smooth maps
    raw = np.empty((hgt, wid * k + 1), np.uint8)
    raw[:, 0] = 1
    raw[:, 1:] = (sub & 0xFF).astype(np.uint8)

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', wid, hgt, 8, {3: 2, 4: 6}[k], 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(raw.tobytes(), 6)) + chunk(b'IEND', b''))


def build(spec, n, seed):
    px = spec.tile / n
    h, alb, rough, cav, feat = spec.make(n, px, seed)
    h = h.astype(F32)
    nx, ny, nz = normals(h, px)
    if spec.height_cavity:
        cav = cav * cavity(h, px, spec.tile / 60.0, max(float(h.std()) * 1.5, 1e-4))
    cav = np.clip(cav, 0, 1)
    maps = {'n': (nx * .5 + .5, ny * .5 + .5, nz * .5 + .5),
            'm': (factor(alb), factor(rough), cav, np.clip(feat, 0, 1).astype(F32))}
    return maps


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055)


def preview(spec, maps, size=512):
    """The set lit from the upper left in its palette colour: albedo x factor x cavity, the feature in its colour,
    Lambert plus a GGX-ish highlight, a soft tone curve. Downsampled to `size` (the whole tile)."""
    n = maps['m'][0].shape[0]
    k = n // size

    def down(a):
        return a.reshape(size, k, size, k).mean(axis=(1, 3))
    r, g, b, a = (down(c) for c in maps['m'])
    nx, ny, nz = (down(c) * 2 - 1 for c in maps['n'])
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    base = np.array(spec.colour, F32)[None, None, :] * (1 + .5 * (2 * r - 1))[..., None] * (.55 + .45 * b)[..., None]
    base = base * (1 - .7 * a[..., None]) + np.array(spec.feature, F32)[None, None, :] * .7 * a[..., None]
    light = np.array([-.45, -.55, .70], F32)
    light /= np.linalg.norm(light)
    ndl = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
    half = light + np.array([0, 0, 1], F32)
    half /= np.linalg.norm(half)
    ndh = np.clip(nx * half[0] + ny * half[1] + nz * half[2], 0, 1)
    rough = np.clip((.18 if spec.metal else .45) + .35 * (2 * g - 1), .05, 1)
    a2 = rough ** 4
    d = a2 / (math.pi * ((ndh * ndh) * (a2 - 1) + 1) ** 2)
    f0 = base if spec.metal else np.full_like(base, .04)
    diffuse = np.zeros_like(base) if spec.metal else base
    colour = (diffuse * ndl[..., None] * 2.6 + f0 * (d * ndl * .5)[..., None] * 2.6 + base * .12)
    return srgb(colour / (1 + colour * .35))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, default=2048)
    parser.add_argument('--only', default='')
    parser.add_argument('--sheet', action='store_true')
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--force', action='store_true', help="also remake sets that scans.py made from scans")
    args = parser.parse_args()
    wanted = [w for w in args.only.split(',') if w]
    unknown = sorted(set(wanted) - {spec.name for spec in SETS})
    if unknown:
        sys.exit('unknown sets: ' + ', '.join(unknown))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / 'textures.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    tiles = []
    for index, spec in enumerate(SETS):
        if wanted and spec.name not in wanted:
            continue
        made_for = manifest.get(spec.name, {}).get('for', '')
        if made_for.startswith('scan:') and not args.force:
            print('%-10s kept: %s (--force makes the procedural set again)' % (spec.name, made_for), flush=True)
            continue
        started = time.time()
        maps = build(spec, args.size, args.seed * 1000 + index * 37)
        png(OUT / ('T_CN_%s_N.png' % spec.name), maps['n'])
        png(OUT / ('T_CN_%s_M.png' % spec.name), maps['m'])
        manifest[spec.name] = {'tile_cm': spec.tile, 'size': args.size, 'for': spec.note}
        if args.sheet:
            tiles.append(preview(spec, maps))
        print('%-10s %5.1f s  tile %d cm' % (spec.name, time.time() - started, spec.tile), flush=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    if tiles:
        per_row = 4
        rows = [np.concatenate(tiles[i:i + per_row] + [np.zeros_like(tiles[0])] * (per_row - len(tiles[i:i + per_row])), 1)
                for i in range(0, len(tiles), per_row)]
        sheet = np.concatenate(rows, 0)
        SHEET.parent.mkdir(parents=True, exist_ok=True)
        png(SHEET, [sheet[..., c] for c in range(3)])
        print('sheet', SHEET)


if __name__ == '__main__':
    main()
