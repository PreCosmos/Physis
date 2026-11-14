"""Generate the Meridian Station interior PBR library from procedural height fields.

Run:
  flatpak-spawn --host flatpak run org.blender.Blender -b --python Tools/build_physis_materials.py
Options after a `--`:
  --only WallPanel,DeckPlate   build a subset          --size 1024   working size
  --no-build                   reuse existing PNGs     --no-sheet    skip the review renders
  --samples 96                 Cycles samples          --corridor-only  only the corridor render
  --audit                      measure the written PNGs (PBR ranges, normal sign, seams)
  --art-direction              hostile close-ups to Art/Review/materials_ad.png

Writes Art/Materials/T_<Name>_{BaseColor,Normal,ORM,Height[,Emissive]}.png, the non-tiling
T_StationDecals atlas (BaseColor alpha is coverage) and T_MacroVariation_Mask.
and the review images Art/Review/materials.png and Art/Review/materials_corridor.png.

Everything is computed in centimetres, on periodic fields: FFT noise and blurs, and
stamps that wrap the tile edge. Each surface is modelled as a height field first, and
wear, grime, roughness and occlusion all derive from that height. Normal maps are
DirectX/Unreal (green-down), written 16-bit by the encoder below so no colour
management touches them.
"""
import argparse
import math
import struct
import sys
import time
import zlib
from pathlib import Path

import numpy as np

try:
    import bpy
except ImportError:
    bpy = None

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Art/Materials'
REVIEW = ROOT / 'Art/Review'
TAU = 2 * math.pi
DENOISE = True


# ---------------------------------------------------------------- palette (linear)
def lin(r, g, b):
    def f(v):
        v /= 255
        return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
    return np.array((f(r), f(g), f(b)), dtype=np.float32)


NAVAL = lin(79, 91, 101)
NAVAL_PALE = lin(104, 114, 122)
NAVAL_DARK = lin(46, 54, 62)
DECK_GREY = lin(58, 67, 76)
PRIMER = lin(108, 110, 96)
OXIDE = lin(104, 62, 44)
STEEL = np.array((.50, .51, .52), dtype=np.float32)
STEEL_DARK = np.array((.30, .31, .32), dtype=np.float32)
TITANIUM = np.array((.40, .375, .345), dtype=np.float32)
BRASS = np.array((.78, .56, .28), dtype=np.float32)
AMBER = lin(184, 124, 46)
HAZARD_BLACK = lin(38, 39, 42)
STENCIL_WHITE = lin(208, 208, 196)
GRIME = lin(34, 31, 28)
SOOT = lin(30, 29, 29)
RUST = lin(92, 50, 28)


# ---------------------------------------------------------------- periodic field kit
class Canvas:
    def __init__(self, size, tile, seed):
        self.n = size
        self.tile = float(tile)
        self.px = size / float(tile)
        self.seed = seed
        self.count = 0
        coords = (np.arange(size, dtype=np.float32) + .5) / self.px
        self.X, self.Y = np.meshgrid(coords, coords)
        self.fx, self.fy = np.meshgrid(np.fft.rfftfreq(size, 1 / self.px), np.fft.fftfreq(size, 1 / self.px))

    def rng(self):
        self.count += 1
        return np.random.default_rng((self.seed, self.count))

    def zeros(self):
        return np.zeros((self.n, self.n), dtype=np.float32)

    def noise(self, lo, hi, beta=1.0, stretch=(1, 1), angle=0.0):
        """Unit-variance band-limited noise. lo and hi are wavelengths in cm; stretch
        lengthens features along the rotated x and y axes."""
        ca, sa = math.cos(angle), math.sin(angle)
        u = (self.fx * ca + self.fy * sa) * stretch[0]
        v = (-self.fx * sa + self.fy * ca) * stretch[1]
        f = np.sqrt(u * u + v * v)
        f[0, 0] = 1e-6
        amp = f ** (-beta) * (1 - np.exp(-(f * hi) ** 4)) * np.exp(-(f * lo) ** 4)
        amp[0, 0] = 0
        out = np.fft.irfft2(np.fft.rfft2(self.rng().standard_normal((self.n, self.n))) * amp, s=(self.n, self.n))
        return (out / max(out.std(), 1e-9)).astype(np.float32)

    def blur(self, a, sx, sy=None):
        sy = sx if sy is None else sy
        g = np.exp(-2 * math.pi ** 2 * ((self.fx * sx) ** 2 + (self.fy * sy) ** 2))
        return np.fft.irfft2(np.fft.rfft2(a) * g, s=(self.n, self.n)).astype(np.float32)

    def drip(self, a, length):
        """One-sided exponential smear toward +row, for run-off below seams and bolts."""
        h = 1 / (1 + 1j * TAU * self.fy * length)
        return np.clip(np.fft.irfft2(np.fft.rfft2(a) * h, s=(self.n, self.n)), 0, None).astype(np.float32)

    def warp(self, a, dx, dy):
        n = self.n
        rows, cols = np.mgrid[0:n, 0:n]
        sx = cols + dx * self.px
        sy = rows + dy * self.px
        x0 = np.floor(sx).astype(np.int32)
        y0 = np.floor(sy).astype(np.int32)
        tx = (sx - x0).astype(np.float32)
        ty = (sy - y0).astype(np.float32)
        x0 %= n
        y0 %= n
        x1 = (x0 + 1) % n
        y1 = (y0 + 1) % n
        return ((a[y0, x0] * (1 - tx) + a[y0, x1] * tx) * (1 - ty)
                + (a[y1, x0] * (1 - tx) + a[y1, x1] * tx) * ty)

    def wrap(self, d):
        return d - self.tile * np.round(d / self.tile)

    def rect(self, x0, y0, x1, y1, r=0.0):
        """Signed distance to a rounded rectangle that wraps the tile edge."""
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        qx = np.abs(self.wrap(self.X - cx)) - ((x1 - x0) / 2 - r)
        qy = np.abs(self.wrap(self.Y - cy)) - ((y1 - y0) / 2 - r)
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

    def strip(self, axis, centre, half):
        return np.abs(self.wrap((self.X if axis == 'x' else self.Y) - centre)) - half

    def patch(self, x, y, radius):
        """Wrapped index and local cm coordinates for a stamp."""
        half = int(radius * self.px) + 2
        ci, cj = int(x * self.px), int(y * self.px)
        offs = np.arange(-half, half + 1)
        lx, ly = np.meshgrid((offs + ci + .5) / self.px - x, (offs + cj + .5) / self.px - y)
        return np.ix_((cj + offs) % self.n, (ci + offs) % self.n), lx.astype(np.float32), ly.astype(np.float32)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    if a.ndim == 3 or (hasattr(b, 'ndim') and b.ndim == 3) or getattr(a, 'shape', None) == (3,):
        t = t[..., None]
    return a + (b - a) * t


def rgb(field, colour):
    return field[..., None] * colour


def convex(c, h, r, scale):
    return np.clip((h - c.blur(h, r)) / scale, 0, 1)


def concave(c, h, r, scale):
    return np.clip((c.blur(h, r) - h) / scale, 0, 1)


def occlusion(c, h, depth=1.0):
    total = 0
    for r, k, w in ((.12, .05, .3), (.4, .14, .35), (1.3, .35, .35), (4, .9, .3)):
        total = total + concave(c, h, r, k * depth) * w
    return 1 - np.clip(total, 0, .92)


def raised(h, sdf, top, bevel, floor=None):
    """Lift a plate out of the surface with a soft machined bevel."""
    base = h if floor is None else floor
    h[:] = np.maximum(h, base + (top - base) * sstep(0, -bevel, sdf))


def scratches(c, count, length, wander=.15, angle=None, spread=TAU, width=.7, taper=True):
    """Thin gouges as bilinear splats of a random walk, wrapping the tile. Returns 0..1."""
    rng = c.rng()
    n = c.n
    out = np.zeros((n, n), dtype=np.float32)
    for lo, hi, share in length if isinstance(length, list) else [(length[0], length[1], 1)]:
        total = int(count * share)
        steps = np.maximum((rng.uniform(lo, hi, total) * c.px * 2).astype(int), 4)
        # Damage comes in events: a few near-parallel strokes, not evenly sprinkled hairs.
        events = max(1, total // 4)
        event = rng.integers(0, events, total)
        base = rng.uniform(0, TAU, events) if angle is None else angle + rng.normal(0, spread, events)
        heading = base[event] + rng.normal(0, .05, total)
        ox = rng.uniform(0, n, events)[event] + rng.normal(0, 3 * c.px, total)
        oy = rng.uniform(0, n, events)[event] + rng.normal(0, 3 * c.px, total)
        force = rng.uniform(.25, 1, total) ** 2.5
        idx = np.repeat(np.arange(total), steps)
        pos = np.arange(steps.sum()) - np.repeat(np.cumsum(steps) - steps, steps)
        t = pos / steps[idx]
        bend = wander * .25 * (rng.uniform(-1, 1, total)[idx] * t + rng.uniform(-1, 1, total)[idx] * np.sin(t * TAU))
        ang = heading[idx] + bend
        px_x = ox[idx] + pos * .5 * np.cos(ang)
        px_y = oy[idx] + pos * .5 * np.sin(ang)
        env = np.sin(np.pi * t) ** .4 if taper else 1
        val = force[idx] * env * (.75 + .25 * np.sin(pos * rng.uniform(.004, .03)))
        fx, fy = np.floor(px_x).astype(int), np.floor(px_y).astype(int)
        ax, ay = px_x - fx, px_y - fy
        for dx, dy, w in ((0, 0, (1 - ax) * (1 - ay)), (1, 0, ax * (1 - ay)), (0, 1, (1 - ax) * ay), (1, 1, ax * ay)):
            np.maximum.at(out, ((fy + dy) % n, (fx + dx) % n), (val * w).astype(np.float32))
    out = np.clip(out * 2.2, 0, 1)
    return np.clip(c.blur(out, width / c.px) * 2.5, 0, 1)


# ---------------------------------------------------------------- fasteners
def hexdist(lx, ly, r, rot):
    ca, sa = math.cos(rot), math.sin(rot)
    x = np.abs(lx * ca + ly * sa)
    y = np.abs(-lx * sa + ly * ca)
    return np.maximum(x * .866 + y * .5, y) - r


def bolt(c, h, marks, x, y, r, rng):
    ix, lx, ly = c.patch(x, y, r * 2)
    d = np.hypot(lx, ly)
    washer = sstep(r * 1.5, r * 1.4, d) * .1
    head = sstep(0, -.14, hexdist(lx, ly, r, rng.uniform(0, 1.05))) * sstep(r * 1.2, r * .95, d)
    h[ix] += washer + head * (r * .34)
    marks[ix] = np.maximum(marks[ix], sstep(r * 1.5, r * 1.3, d))


def screw(c, h, marks, x, y, r, rng):
    """Countersunk cross-head panel screw, sitting flush."""
    ix, lx, ly = c.patch(x, y, r * 1.6)
    d = np.hypot(lx, ly)
    dish = sstep(r * 1.25, r * 1.0, d) * .05
    a = rng.uniform(0, 3.14)
    ca, sa = math.cos(a), math.sin(a)
    u = np.abs(lx * ca + ly * sa)
    v = np.abs(-lx * sa + ly * ca)
    slot = np.maximum(sstep(r * .2, r * .1, u) * sstep(r * .8, r * .6, v), sstep(r * .2, r * .1, v) * sstep(r * .8, r * .6, u))
    h[ix] += -dish - slot * .12
    marks[ix] = np.maximum(marks[ix], sstep(r * 1.2, r * 1.0, d))


def quarter_turn(c, h, marks, x, y, r, rng):
    """Dzus-style captive fastener: dished seat, raised head, single wing slot."""
    ix, lx, ly = c.patch(x, y, r * 1.8)
    d = np.hypot(lx, ly)
    seat = sstep(r * 1.6, r * 1.1, d) * .2
    head = sstep(r * 1.02, r * .86, d) * .24
    a = rng.normal(0, .2)
    ca, sa = math.cos(a), math.sin(a)
    u = np.abs(lx * ca + ly * sa)
    v = np.abs(-lx * sa + ly * ca)
    slot = sstep(r * .2, r * .11, v) * sstep(r * .92, r * .8, u) * .16
    h[ix] += -seat + head - slot
    marks[ix] = np.maximum(marks[ix], sstep(r * 1.1, r * .95, d))


def rivet(c, h, marks, x, y, r, rng):
    ix, lx, ly = c.patch(x, y, r * 1.2)
    d2 = (lx * lx + ly * ly) / (r * r)
    h[ix] += np.sqrt(np.clip(1 - d2, 0, 1)) * r * .4
    marks[ix] = np.maximum(marks[ix], (d2 < 1).astype(np.float32))


# ---------------------------------------------------------------- stencil lettering
# Each stroke is a polyline of hex digit pairs on an 8x12 grid (y up). Strokes stop short
# of each other so the letters keep the bridges a real cut stencil needs.
GLYPHS = {
    'A': '11 19 3b;71 79 5b;35 55', 'B': '11 1b;3b 6b 7a 77 66 36;66 75 72 61 31',
    'C': '7a 6b 2b 1a 12 21 61 72', 'D': '11 1b;3b 5b 79 73 51 31',
    'E': '11 1b;3b 7b;36 66;31 71', 'F': '11 1b;3b 7b;36 66',
    'G': '7a 6b 2b 1a 12 21 61 72 76 46', 'H': '11 1b;71 7b;36 56', 'I': '41 4b',
    'J': '6b 62 51 21 12', 'K': '11 1b;46 7b;46 71', 'L': '1b 11 71', 'M': '11 1b 46 7b 71',
    'N': '11 1b 71 7b', 'O': '3b 2b 1a 12 21 31;5b 6b 7a 72 61 51',
    'P': '11 1b;3b 6b 7a 76 65 35', 'Q': '3b 2b 1a 12 21 31;5b 6b 7a 72 61 51;43 71',
    'R': '11 1b;3b 6b 7a 77 66 36;56 71', 'S': '7a 6b 2b 1a 17 26 66 75 72 61 21 12',
    'T': '1b 7b;49 41', 'U': '1b 12 21 61 72 7b', 'V': '1b 16 41 76 7b', 'W': '1b 11 46 71 7b',
    'X': '1b 71;7b 11', 'Y': '1b 46 7b;44 41', 'Z': '1b 7b 11 71',
    '0': '3b 2b 1a 12 21 31;5b 6b 7a 72 61 51', '1': '29 4b 41', '2': '1a 2b 6b 7a 77 12 11 71',
    '3': '1a 2b 6b 7a 77 66 46;66 75 72 61 21 12', '4': '5b 15 75;59 51', '5': '7b 1b 17 67 76 72 61 21 12',
    '6': '6b 2b 1a 12 21 61 72 75 66 26', '7': '1b 7b 7a 31', '8': '2b 6b 7a 77 66 26 17 1a 2b;26 15 12 21 61 72 75 66',
    '9': '66 26 17 1a 2b 6b 7a 72 61 21', '-': '25 65', '/': '11 7b', '.': '41 42',
}


def stroke(c, mask, p, q, half, cap0=0.0, cap1=0.0):
    (x0, y0), (x1, y1) = p, q
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 1e-6:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    pad = half + max(cap0, cap1)
    radius = length / 2 + pad + 1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    ix, lx, ly = c.patch(mx, my, radius)
    along = (lx + mx - x0) * ux + (ly + my - y0) * uy
    perp = np.abs(-(lx + mx - x0) * uy + (ly + my - y0) * ux)
    cov = (np.clip(.5 + (half - perp) * c.px, 0, 1) * np.clip(.5 + (along + cap0) * c.px, 0, 1)
           * np.clip(.5 + (length + cap1 - along) * c.px, 0, 1))
    mask[ix] = np.maximum(mask[ix], cov.astype(np.float32))


def text(c, mask, string, x, y, height, angle=0.0, weight=1.0):
    u = height / 12
    ca, sa = math.cos(angle), math.sin(angle)
    half = u * weight
    cursor = 0.0
    for ch in string:
        cursor -= u * 2 if ch in 'I1.' else 0
        for strokes in filter(None, GLYPHS.get(ch, '').split(';')):
            pts = [(int(pair[0], 16), int(pair[1], 16)) for pair in strokes.split()]
            pts = [(x + (cursor + gx * u) * ca - (12 - gy) * u * sa, y + (cursor + gx * u) * sa + (12 - gy) * u * ca) for gx, gy in pts]
            for i in range(len(pts) - 1):
                stroke(c, mask, pts[i], pts[i + 1], half, half if i else 0, half if i < len(pts) - 2 else 0)
        cursor += u * (6 if ch in 'I1.' else 9.6)


def sprayed(c, mask, wear=.4):
    """Cut-stencil paint: soft overspray halo, worn inside by fine noise."""
    halo = c.blur(mask, .25) * .35
    body = c.blur(mask, .5 / c.px)
    breakup = sstep(wear + .5, wear - .4, c.noise(.2, 4, 1.2) + c.noise(3, 30, .8) * .7)
    return np.clip(body * breakup + halo * (c.noise(.15, 1) > .6), 0, 1)


# ---------------------------------------------------------------- paint and wear stack
class Surface:
    """Height, linear albedo, roughness, metallic and occlusion for one tile."""

    def __init__(self, c, h, alb, rough, metal, ao, emissive=None):
        self.c, self.h, self.alb, self.rough, self.metal, self.ao, self.emissive = c, h, alb, rough, metal, ao, emissive


def weather(c, h, paint, *, thick=.022, chip=1.0, scratch=1.0, grime=1.0, gloss=.4, rust=.3,
            bias=None, extra_scratch=None, void=None, drip=14.0, metal_col=STEEL, primer=PRIMER,
            grime_col=GRIME, relief=1.0):
    """Turn a structural height and a paint colour map into a finished worn surface."""
    # Sheet metal is never flat: slow oil-canning, roller orange peel, weld-spatter pits.
    h = h + c.noise(9, 70, 1.5) * .034 * relief + c.noise(.5, 2.2, .5) * .0024
    pits = sstep(2.9, 3.4, c.noise(.1, .5, .3))
    h = h - pits * .012

    edge = np.maximum(convex(c, h, .16, .05), convex(c, h, .5, .15) * .9)
    edge = c.blur(edge, .4 / c.px)
    regional = c.noise(10, 80, 1.2)
    blotch = c.noise(.25, 7, 1.35)
    fine = c.noise(.1, 1.2, .7)

    # Paint fails along exposed edges in patches, and in sparse field dings.
    # Damage clusters: whole runs of edge stay intact, then a hard-used stretch lets go.
    cluster = sstep(-.35, 1.05, c.noise(3, 28, 1.1) + regional * .55)
    score = edge * (.62 + 1.05 * cluster) * chip + blotch * .24 * (.3 + cluster) + fine * .1 - 1.0
    dingf = c.noise(.12, 2.4, .75)
    dings = sstep(2.75, 3.0, dingf + fine * .2) * .6 * chip
    score = np.maximum(score, dings - .28)
    if bias is not None:
        score = score + bias
    # Sweeping scrapes from carts and cargo cross the panels at shallow angles.
    gouge = scratches(c, int(60 * scratch), [(8, 40, .75), (40, 110, .25)], wander=.2, angle=.12, spread=.5, width=.8)
    light = scratches(c, int(420 * scratch), [(2, 12, .7), (12, 40, .3)], wander=.5, width=.55)
    if extra_scratch is not None:
        gouge = np.maximum(gouge, extra_scratch)
    # A scrape skips: it bites through to primer in places and only burnishes the rest.
    skip = sstep(-.3, 1.2, c.noise(.7, 12, .9) + cluster * .5)
    score = np.maximum(score, gouge * skip * .42 - .2)

    primer_mask = sstep(0, .03, score)
    steel_mask = sstep(.14, .19, score + fine * .05)
    # Chalked, thinned paint feathers out around every failure.
    chalk = sstep(-.16, 0, score) * (1 - primer_mask)

    h = h - primer_mask * thick - steel_mask * thick * .7 - light * .004 - gouge * .012

    # Colour: rolled paint varies slowly, sun-less station air yellows it a touch.
    tone = 1 + c.noise(5, 60, 1.0) * .05 + c.noise(.6, 4, .8) * .018
    alb = paint * tone[..., None]
    warm = np.clip(c.noise(12, 90, 1.2) * .5 + .3, 0, 1)
    alb = alb * (1 + (warm * .05)[..., None] * np.array((1, .25, -.6), dtype=np.float32))
    alb = mix(alb, alb * 1.16 + rgb(np.ones_like(h), lin(120, 124, 124)) * .03, chalk * .6)
    alb = mix(alb, primer * (1 + fine * .06)[..., None], primer_mask)
    steel = metal_col * (1 + c.noise(.3, 5, .9) * .1)[..., None]
    alb = mix(alb, steel, steel_mask)
    alb = mix(alb, alb * 1.3 + .02, np.maximum(light * .35, gouge * .4) * (1 - steel_mask))

    rough = gloss + c.noise(1, 14, .9) * .035 + c.noise(.8, 40, .8, stretch=(1, 12)) * .055 + chalk * .2
    rough = mix(rough, .62 + fine * .04, primer_mask)
    rough = mix(rough, .3 + c.noise(.2, 3, .8) * .05, steel_mask)
    rough = rough + light * .12 * (1 - steel_mask)
    metal = steel_mask.copy()

    # Rust only where steel has sat bare: the crew keeps on top of it, not always in time.
    if rust > 0:
        rusty = sstep(.2, 1.1, c.blur(steel_mask, .5) * 2.4 + c.noise(.6, 8, 1.0) * .4) * rust
        alb = mix(alb, RUST * (1 + c.noise(.2, 2, .6) * .25)[..., None], rusty * steel_mask)
        run = c.drip(rusty * steel_mask, 6) * sstep(-.4, 1, c.noise(.3, 8, .8, stretch=(1, 14)))
        alb = mix(alb, RUST * .9, np.clip(run * 1.1, 0, .4) * (1 - steel_mask))
        metal = metal * (1 - rusty * .8)
        rough = mix(rough, .8, rusty * steel_mask)

    ao = occlusion(c, h)
    if void is not None:
        ao = ao * (1 - void * .9)

    # Grime: held in crevices, run down from seams, and filmed over everything low.
    crevice = np.clip(concave(c, h, .35, .1) + concave(c, h, 1.2, .35) * .9, 0, 1)
    runs = c.drip(crevice, drip) * sstep(-.5, 1.3, c.noise(.35, 14, .9, stretch=(1, 24)) + regional * .3)
    # Hand-washed from the top down: vertical wipes and tide marks, never cloud shapes.
    film = sstep(-.3, 1.7, c.noise(2.5, 30, 1.0, stretch=(1, 9)) + regional * .35)
    g = np.clip(crevice * (.65 + .3 * fine) + runs * .42 + film * .16, 0, 1) * grime
    g = np.clip(g, 0, .92)
    speck = sstep(1.6, 2.4, c.noise(.12, .8, .6)) * .25 * grime
    tint = mix(np.ones_like(alb) * grime_col, np.ones_like(alb) * SOOT, sstep(-.5, 1, c.noise(1, 12, 1)))
    alb = mix(alb, tint, np.clip(g * .82 + speck, 0, .95))
    # The wash film is a colour story only: as roughness it became hard blotches in the highlight.
    held = np.clip(crevice * (.65 + .3 * fine) + runs * .22, 0, 1) * grime
    rough = mix(rough, .82, np.clip(held, 0, .92) * .85) + film * .03
    metal = metal * (1 - g * .9)

    alb = alb * (.74 + .26 * ao)[..., None]   # ORM carries the rest; Lumen would double it
    if void is not None:
        alb = mix(alb, np.ones_like(alb) * .006, void)
        rough = mix(rough, .7, void)
    floor_alb = .013 if void is None else mix(np.full_like(h, .013), np.full_like(h, .004), void)[..., None]
    return Surface(c, h, np.clip(alb, floor_alb, 1), np.clip(rough, .04, 1), np.clip(metal, 0, 1), ao)


def add_paint(alb_map, mask, colour):
    return mix(alb_map, np.ones_like(alb_map) * colour, np.clip(mask, 0, 1))


# ---------------------------------------------------------------- 1. wall panels
def wall_panel(c):
    rng = c.rng()
    t = c.tile
    floor = -.9
    h = c.zeros() + floor
    marks = c.zeros()
    paint = np.ones((c.n, c.n, 3), dtype=np.float32) * NAVAL
    void = c.zeros()
    bias = c.zeros()

    # Frame: a vertical stringer every 2 m, a mid rail, and a cap rail at the tile edge.
    stringer = c.strip('x', 0, 7.5)
    raised(h, stringer, 1.0, .4, floor)
    rail_mid = c.strip('y', 131, 5.5)
    raised(h, rail_mid, .6, .35, floor)
    rail_top = c.strip('y', 0, 3.0)
    raised(h, rail_top, .6, .3, floor)

    # Upper bulkhead plates.
    a = c.rect(9, 4, 98.5, 124.5, .8)
    b = c.rect(101.5, 4, 191, 124.5, .8)
    raised(h, a, 0, .22, floor)
    raised(h, b, 0, .22, floor)
    # Plate A carries a pressed lightening recess, plate B three stiffener beads.
    press = c.rect(19, 14, 88.5, 114.5, 6)
    h += sstep(1.3, -1.3, press) * -.32
    for x in (118.0, 146.25, 174.5):
        bead = c.rect(x - 2.6, 13, x + 2.6, 115.5, 2.6)
        h += sstep(1.2, -1.6, bead) * .42

    # Lower service bay: hatch at left, ventilation at right, in the dark wainscot colour.
    hatch = c.rect(9, 138.5, 60, 196.5, .8)
    vent_plate = c.rect(62.5, 138.5, 191, 196.5, .8)
    raised(h, hatch, .05, .22, floor)
    raised(h, vent_plate, 0, .22, floor)
    # Hatch: inset recessed pull with a captive bar.
    cup = c.rect(25, 161, 45, 174, 2.4)
    h += sstep(.5, -.5, cup) * -.75
    bar = c.rect(27, 166.2, 43, 168.8, 1.2)
    h += sstep(.25, -.45, bar) * .55
    # Vent: angled louvres in a framed opening. Open slots go to true black.
    frame = c.rect(74, 146, 179, 189, 1.2)
    opening = c.rect(76, 148, 177, 187, .4)
    h += sstep(.6, -.3, frame) * .18
    slats = 7
    pitch = 39 / slats
    u = ((c.Y - 148) / pitch) % 1
    profile = (u ** 1.3 * 1.5 - 1.6) * (u < .84) + (-2.0) * (u >= .84)
    open_mask = sstep(.25, -.25, opening)
    h = mix(h, h * 0 - .05 + profile, open_mask)
    void = np.maximum(void, open_mask * sstep(.8, .86, u) * (1 - sstep(.97, 1, u)))
    # Louvre mullions.
    for x in (109.667, 143.333):
        m = c.rect(x - .9, 147, x + .9, 188, .3)
        h = mix(h, h * 0 + .15, sstep(.2, -.1, m))

    # Conduit clipped along the mid rail: the one strong horizontal highlight.
    dy = c.wrap(c.Y - 131)
    pipe = np.sqrt(np.clip(1.9 ** 2 - dy * dy, 0, None)) * 1.0
    h = np.maximum(h, .6 + pipe * (np.abs(dy) < 1.9) - .25)
    for i in range(5):
        x = 20 + i * 40.0
        clamp = c.rect(x - 1.5, 127, x + 1.5, 135, .4)
        h = np.maximum(h, mix(h, 2.75 - np.abs(dy) ** 2 * .17, sstep(.2, -.2, clamp)))
        bolt(c, h, marks, x, 134.0, .65, rng)
        bolt(c, h, marks, x, 128.0, .65, rng)

    # Paint zones.
    lower = sstep(.3, -.3, np.minimum(hatch, vent_plate))
    paint = add_paint(paint, lower, NAVAL_DARK)
    frame_zone = sstep(.3, -.3, np.minimum(stringer, np.minimum(rail_mid, rail_top)))
    paint = add_paint(paint, frame_zone, NAVAL * .72)
    # Plates were painted in different years: value and hue both step between them.
    for sdf, shift, warm in ((a, 1.09, .02), (b, .9, -.02), (hatch, 1.12, .03), (vent_plate, .92, -.01)):
        step_mask = sstep(.2, -.2, sdf)[..., None]
        paint = paint * (1 + (shift - 1) * step_mask) * (1 + warm * step_mask * np.array((1, 0, -1), dtype=np.float32))
    pipe_zone = sstep(2.1, 1.9, np.abs(dy))
    paint = add_paint(paint, pipe_zone, NAVAL_PALE * .8)

    # Fasteners follow load paths: heavy bolts up the stringer, screws around each plate.
    for i in range(8):
        y = 12.5 + 25 * i
        bolt(c, h, marks, -4.6, y, 1.0, rng)
        bolt(c, h, marks, 4.6, y, 1.0, rng)
    for x0, y0, x1, y1 in ((9, 4, 98.5, 124.5), (101.5, 4, 191, 124.5), (62.5, 138.5, 191, 196.5)):
        nx, ny = max(2, int((x1 - x0) / 22)), max(2, int((y1 - y0) / 22))
        for i in range(nx + 1):
            x = x0 + 2.6 + (x1 - x0 - 5.2) * i / nx
            screw(c, h, marks, x, y0 + 2.6, .85, rng)
            screw(c, h, marks, x, y1 - 2.6, .85, rng)
        for j in range(1, ny):
            y = y0 + 2.6 + (y1 - y0 - 5.2) * j / ny
            screw(c, h, marks, x0 + 2.6, y, .85, rng)
            screw(c, h, marks, x1 - 2.6, y, .85, rng)
    for x, y in ((14, 143.5), (55, 143.5), (14, 191.5), (55, 191.5)):
        quarter_turn(c, h, marks, x, y, 1.5, rng)
    for i in range(16):
        rivet(c, h, marks, 6.25 + 12.5 * i, 0, .55, rng)

    # Touch-up: rectangles of slightly different paint rolled over past damage.
    for x0, y0, w, hh in ((104, 84, 38, 30), (34, 44, 26, 18), (120, 150, 46, 28)):
        edge = c.noise(.5, 6, 1) * .7
        patch = sstep(.8, -.8, c.rect(x0, y0, x0 + w, y0 + hh, 1.5) + edge)
        paint = paint * (1 + (patch * rng.uniform(-.09, .1))[..., None] * np.array((1.1, 1, .92), dtype=np.float32))
        bias = bias - patch * .32
        h = h + patch * .006

    # Amber line marking the service bay, and the stencils. Paint sits over the plate.
    amber = c.rect(62.5, 139.5, 191, 141.0, .1)
    amber_mask = sstep(.08, -.08, amber) * sstep(1.2, .2, c.noise(.8, 16, 1))
    paint = add_paint(paint, amber_mask, AMBER * .92)
    amber2 = sstep(.08, -.08, c.rect(9, 139.5, 60, 141.0, .1)) * sstep(1.2, .2, c.noise(.8, 16, 1))
    paint = add_paint(paint, amber2, AMBER * .92)

    white = c.zeros()
    text(c, white, 'ACCESS', 24.5, 149, 2.6, weight=.95)
    text(c, white, 'AIR RETURN', 82, 143.0, 1.9, weight=.95)
    white = sprayed(c, white, .05)
    paint = add_paint(paint, white * .9, STENCIL_WHITE)
    # Chevron pointing at the hatch pull.
    chev = c.zeros()
    for i in (0, 1):
        x = 13.5 + i * 5.2
        stroke(c, chev, (x, 164.5), (x + 3, 167.5), .8, .5, .5)
        stroke(c, chev, (x + 3, 167.5), (x, 170.5), .8, .5, .5)
    paint = add_paint(paint, sprayed(c, chev, -.3) * .95, AMBER)

    bias = bias + marks * .2
    s = weather(c, h, paint, chip=1.1, scratch=1.2, gloss=.36, bias=bias, void=void, rust=.3, grime=1.15)

    return s


# ---------------------------------------------------------------- 2. deck plate
def deck_plate(c):
    rng = c.rng()
    t = c.tile
    floor = -.6
    h = c.zeros() + floor
    marks = c.zeros()

    # Two staggered runs of plate with a flat bolting margin around the tread.
    plates = [(1, 1, 79, 79), (81, 1, 159, 79), (41, 81, 119, 159), (121, 81, 199, 159)]
    interior = np.full_like(h, 1e3)
    tones = np.ones_like(h)
    for (x0, y0, x1, y1) in plates:
        d = c.rect(x0, y0, x1, y1, .5)
        raised(h, d, 0, .2, floor)
        interior = np.minimum(interior, d)
        tones = tones * (1 + rng.uniform(-.07, .07) * sstep(.3, -.3, d))

    # Raised teardrop lugs on a chequer of crossed axes.
    n = 32
    p = c.tile / n
    i = np.floor(c.X / p).astype(np.int32)
    j = np.floor(c.Y / p).astype(np.int32)
    u = (c.X / p - i - .5) * p
    v = (c.Y / p - j - .5) * p
    sign = np.where((i + j) % 2 == 0, 1.0, -1.0).astype(np.float32)
    a = (u + v * sign) * .7071
    b = (v - u * sign) * .7071
    L = p * .5
    w = p * .155 * np.clip(1 - (a / L) ** 2, 0, 1) ** .55 * (1 + .25 * a / L)
    d = np.abs(b) - w
    lug = sstep(.06, -.22, d) * (np.abs(a) < L)
    field = sstep(-4.2, -5.4, interior)
    worn_down = 1 - .35 * sstep(-.4, 1.4, c.noise(14, 60, 1.2))
    lugh = lug * field * .3 * worn_down
    h = h + lugh

    # Countersunk bolts in the margin, on a pitch that matches the frames below.
    for (x0, y0, x1, y1) in plates:
        for s in range(5):
            f = (s + .5) / 5
            for x, y in ((x0 + 2.5, y0 + (y1 - y0) * f), (x1 - 2.5, y0 + (y1 - y0) * f),
                         (x0 + (x1 - x0) * f, y0 + 2.5), (x0 + (x1 - x0) * f, y1 - 2.5)):
                screw(c, h, marks, x % c.tile, y % c.tile, 1.05, rng)

    # Lifting recess in one plate: two machined finger slots.
    for y in (119.0, 124.5):
        lift = c.rect(68, y - 1, 92, y + 1, 1)
        h = h + sstep(.1, -.2, lift) * -.5

    # Traffic: lanes of polish along Y, boots turn at the seams, wheels leave long rubs.
    lane = sstep(.05, 1.5, c.noise(9, 120, .9, stretch=(1, 30)) + c.noise(14, 60, 1.1) * .5)
    bias = lug * field * (lane * .8 - .12) - .03 - (1 - lane) * .1
    rubs = scratches(c, 60, [(12, 60, .7), (60, 140, .3)], wander=.1, angle=math.pi / 2, spread=.12, width=.9)
    paint = np.ones((c.n, c.n, 3), dtype=np.float32) * DECK_GREY * tones[..., None]

    s = weather(c, h, paint, chip=1.2, scratch=.8, gloss=.5, bias=bias + lane * .04 + marks * .25,
                extra_scratch=rubs, rust=.22, thick=.03, drip=.01, grime=1.15, relief=.6,
                metal_col=STEEL_DARK * 1.45, primer=lin(72, 74, 70))
    # Polished lug crowns, oil and tyre-black marks.
    crown = np.clip(lug * field * (.25 + lane * .9), 0, 1) * s.metal
    s.rough = mix(s.rough, .22 + c.noise(.2, 2, .6) * .03, crown * .9)
    oil = sstep(1.7, 2.6, c.noise(1.5, 25, 1.4) + c.noise(.3, 3, .8) * .18)
    s.alb = mix(s.alb, s.alb * .3, oil * .8)
    s.rough = mix(s.rough, .16, oil * .8)
    tyre = c.blur(rubs, .1) * 1.2 * lane
    s.alb = mix(s.alb, np.ones_like(s.alb) * .012, np.clip(tyre, 0, .55))
    return s


# ---------------------------------------------------------------- 3. ceiling service panels
def ceiling_panel(c):
    rng = c.rng()
    floor = -1.3
    h = c.zeros() + floor
    marks = c.zeros()
    void = c.zeros()
    paint = np.ones((c.n, c.n, 3), dtype=np.float32) * NAVAL_PALE

    # T-bar suspension grid with bays set out for what runs above them.
    tbar_x = np.minimum(c.strip('x', 0, 3.2), c.strip('x', 100, 3.2))
    tbar_y = np.minimum(c.strip('y', 0, 3.2), c.strip('y', 134, 3.2))
    grid = np.minimum(tbar_x, tbar_y)
    raised(h, grid, .55, .3, floor)
    # Service spine: three pipes in an open tray along the row between y=0 and 22.
    tray = c.strip('y', 14, 10)
    tray = np.maximum(tray, -grid)
    raised(h, c.strip('y', 3.2 + 1.6, 1.6), .55, .2, floor)
    raised(h, c.strip('y', 24 + 1.6 - .4, 1.6), .55, .2, floor)

    bays = {
        'perf': (5, 29, 96.5, 130),
        'solid': (103.5, 29, 196.5, 130),
        'vent': (5, 138, 96.5, 196.5),
        'perf2': (103.5, 138, 196.5, 196.5),
    }
    sdfs = {}
    for name, (x0, y0, x1, y1) in bays.items():
        sdfs[name] = c.rect(x0, y0, x1, y1, .6)
        raised(h, sdfs[name], .05, .2, floor)

    # Perforated acoustic infill on a hex lattice that divides the tile exactly.
    nx, ny = 112, 130
    px_, py_ = c.tile / nx, c.tile / ny
    def lattice(ox, oy):
        return np.hypot(((c.X - ox) / px_ - np.round((c.X - ox) / px_)) * px_,
                        ((c.Y - oy) / (py_ * 2) - np.round((c.Y - oy) / (py_ * 2))) * py_ * 2)
    dist = np.minimum(lattice(0, 0), lattice(px_ / 2, py_))
    perf_zone = sstep(.1, -.1, np.minimum(c.rect(11, 35, 90.5, 124, 1), c.rect(109.5, 144, 190.5, 190.5, 1)))
    hole = sstep(.36, .28, dist) * perf_zone
    h = h - hole * .7
    void = np.maximum(void, sstep(.33, .26, dist) * perf_zone * .96)
    # Perimeter of each perforated field gets a formed step so it reads as a pressed tray.
    for sdf in (c.rect(9.5, 33.5, 92, 125.5, 1.5), c.rect(108, 142.5, 192, 192, 1.5)):
        h = h + sstep(.8, -.8, sdf) * -.14

    # Solid access door: hinge knuckles on one edge, latches on the other, recessed tag.
    door_inset = c.rect(114, 40, 186, 119, 3)
    h = h + sstep(1.1, -1.1, door_inset) * .22
    for y in (45, 113):
        knuckle = c.rect(103.5 - 1, y - 7, 110, y + 7, .5)
        h = h + sstep(.25, -.35, knuckle) * .3
        for k in range(2):
            rivet(c, h, marks, 107.5, y - 4 + 8 * k, .7, rng)
    for y in (63, 96):
        cup = c.rect(186, y - 4, 194, y + 4, 1.6)
        h = h + sstep(.3, -.3, cup) * -.5
        quarter_turn(c, h, marks, 190, y, 1.8, rng)

    # Diffuser: blades in a frame, air sucks dust into them so they streak dark.
    frame = c.rect(14, 146, 88, 189, 1.5)
    h = h + sstep(.5, -.3, frame) * .2
    opening = c.rect(16.5, 148.5, 85.5, 186.5, .6)
    pitch = 38 / 12
    w = ((c.Y - 148.5) / pitch) % 1
    blade = -1.2 + np.sin(np.clip(w / .72, 0, 1) * math.pi) * 1.15
    oz = sstep(.15, -.15, opening)
    h = mix(h, blade, oz)
    void = np.maximum(void, oz * sstep(.74, .8, w))

    # Paint zones and per-bay tone.
    grid_zone = sstep(.3, -.3, grid)
    paint = add_paint(paint, grid_zone, NAVAL * .85)
    for sdf, shift in ((sdfs['perf'], 1.05), (sdfs['solid'], .94), (sdfs['vent'], .98), (sdfs['perf2'], .9)):
        paint = paint * (1 + (shift - 1) * sstep(.2, -.2, sdf))[..., None]

    # Pipes, clamps, and one amber-banded line so damage crews can find the coolant.
    for y, r, col in ((9.5, 2.6, NAVAL * .8), (15.5, 2.6, NAVAL_DARK), (20.8, 1.6, NAVAL * .95)):
        dy = c.wrap(c.Y - y)
        cyl = np.sqrt(np.clip(r * r - dy * dy, 0, None)) + r * .8 + floor - .1
        inside = (np.abs(dy) < r).astype(np.float32)
        h = np.maximum(h, cyl * inside + (floor - 5) * (1 - inside))
        paint = add_paint(paint, sstep(r + .1, r - .1, np.abs(dy)), col)
    for i in range(4):
        x = 25 + 50 * i
        strap = c.rect(x - 1.6, 5.5, x + 1.6, 23.5, .3)
        raised(h, strap, 3.2, .9)
        paint = add_paint(paint, sstep(.2, -.2, strap), NAVAL_DARK * .85)
    for x in (50.0, 150.0):
        band = sstep(.1, -.1, c.rect(x - 4, 6.8, x + 4, 12.5, .1))
        paint = add_paint(paint, band * .9, AMBER * .9)

    for sdf_rect_, step in (((5, 29, 96.5, 130), 22), ((103.5, 29, 196.5, 130), 22), ((5, 138, 96.5, 196.5), 19), ((103.5, 138, 196.5, 196.5), 19)):
        x0, y0, x1, y1 = sdf_rect_
        nu, nv = int((x1 - x0) / step), int((y1 - y0) / step)
        for i in range(nu + 1):
            x = x0 + 2.2 + (x1 - x0 - 4.4) * i / nu
            for y in (y0 + 2.2, y1 - 2.2):
                screw(c, h, marks, x, y, .75, rng)
        for j in range(1, nv):
            y = y0 + 2.2 + (y1 - y0 - 4.4) * j / nv
            for x in (x0 + 2.2, x1 - 2.2):
                screw(c, h, marks, x, y, .75, rng)

    # Pipes are round, so curvature wear would peel every crown: they are protected here.
    bias = marks * .2 - sstep(.4, -.4, c.strip('y', 14, 9.5)) * .9
    # Stencils the crew reads looking up.
    ink = c.zeros()
    text(c, ink, 'COOLANT', 54.5, 7.5, 2.0, weight=.8)
    text(c, ink, 'COOLANT', 154.5, 7.5, 2.0, weight=.8)
    paint = add_paint(paint, sprayed(c, ink, .4) * .85, HAZARD_BLACK)
    s = weather(c, h, paint, chip=.9, scratch=.6, gloss=.44, grime=1.15, rust=.2, void=void, bias=bias, drip=7)
    # Dark halo on the wash around the diffuser, where exhaust dust settles.
    soot = np.clip(c.blur(sstep(.2, -.2, frame), 2.2) * 1.3 * (1 - oz), 0, 1)
    soot = soot * (.6 + .4 * sstep(-1, 1, c.noise(.8, 10, 1)))
    s.alb = mix(s.alb, s.alb * .45, soot * .75)
    s.rough = mix(s.rough, .75, soot * .6)
    return s


# ---------------------------------------------------------------- 4. rubberised floor runner
def floor_runner(c):
    rng = c.rng()
    t = c.tile
    h = c.zeros()
    # Moulded raised discs on a staggered pitch. Worn footfall flattens the crowns.
    nx, ny = 40, 40
    dx, dy = t / nx, t / ny
    def nearest(ox, oy):
        u = ((c.X - ox) / dx - np.round((c.X - ox) / dx)) * dx
        v = ((c.Y - oy) / (dy * 2) - np.round((c.Y - oy) / (dy * 2))) * dy * 2
        return np.hypot(u, v)
    d = np.minimum(nearest(0, 0), nearest(dx / 2, dy))
    edge_band = c.strip('x', 0, 6.5)
    field = sstep(0, -.25, -edge_band)
    stud = sstep(.98, .72, d)
    traffic = np.clip(.5 + c.noise(25, 100, 1.4, stretch=(1, 4)) * .22 + c.noise(1.5, 12, .9) * .1, 0, 1)
    crown = .17 * (1 - traffic * .15)
    h += np.minimum(stud * .19, crown) * field

    # Moulded border: a lifted lip with the amber line sunk into it.
    h += sstep(.3, -.3, edge_band) * .1
    stripe = sstep(.08, -.08, c.strip('x', 0, 2.2))
    h -= stripe * .035
    # Butt joint: bonded sections every metre, slightly raised and glue-dirty.
    joint = c.strip('y', 0, .12)
    h = h - sstep(.08, -.08, joint) * .22

    # Rubber is soft: slow undulation, moulded-in bloom, fine abrasion.
    h = h + c.noise(6, 40, 1.3) * .03 + c.noise(.1, .5, .3) * .0022
    gouge = scratches(c, 70, [(1, 7, .85), (7, 22, .15)], wander=.7, width=1.0, angle=math.pi / 2, spread=.9)
    h = h - gouge * .05
    nicks = sstep(2.5, 2.9, c.noise(.15, .9, .6))
    h = h - nicks * .03

    ao = occlusion(c, h, .4)
    top = np.clip((h - c.blur(h, .7)) / .05, 0, 1)
    valley = concave(c, h, .6, .05)

    rubber = lin(47, 50, 55)
    alb = np.ones((c.n, c.n, 3), dtype=np.float32) * rubber
    alb = alb * (1 + c.noise(4, 40, 1) * .07 + c.noise(.3, 2, .6) * .05)[..., None]
    amber = AMBER * .9 * (1 + c.noise(.2, 3, .6) * .05)[..., None]
    wearline = sstep(-.6, 1.6, c.noise(.25, 7, .9, stretch=(1, 16)) + traffic * .7 - .3)
    alb = mix(alb, amber, stripe * (1 - wearline * .5))

    # Abrasion lightens and polishes crowns where boots land.
    scuff_shine = np.clip(top * (.35 + traffic * .4), 0, 1)
    alb = mix(alb, alb * 1.5 + .012, scuff_shine * .55)
    rough = .72 + c.noise(.3, 6, .7) * .03 - scuff_shine * .24
    # Boot rubber: smeared dark arcs. Dust: pale grey in the valleys.
    heel = sstep(1.3, 2.1, c.noise(1, 12, .9, stretch=(1, 3), angle=.3) + traffic * .3)
    alb = mix(alb, alb * .4, heel * .7)
    rough = mix(rough, .42, heel * .6)
    dust = np.clip(valley * 1.1 + sstep(.2, 2, c.noise(5, 50, 1)) * .25, 0, 1) * (1 - top * .8)
    dust = dust * (.45 + .55 * sstep(-1, 1, c.noise(.1, 1.2, .7)))
    dust_col = lin(112, 108, 100)
    alb = mix(alb, dust_col, dust * .34)
    rough = mix(rough, .9, dust * .7)
    alb = mix(alb, alb * 1.8 + .03, gouge * .5)
    rough = rough + gouge * .1

    # Glue line and tracked-in grime at the bond.
    glue = c.blur(sstep(.2, -.2, joint), .35)
    alb = mix(alb, np.ones_like(alb) * .012, np.clip(glue * 1.6, 0, .85))
    alb = alb * (.5 + .5 * ao)[..., None]
    return Surface(c, h, np.clip(alb, .006, 1), np.clip(rough, .05, 1), c.zeros(), ao)


# ---------------------------------------------------------------- 5. brushed titanium trim
def titanium_trim(c):
    rng = c.rng()
    t = c.tile
    # Two scales of belt grain along X, plus sparse deep grain lines from a loaded belt.
    grain = c.noise(.012, .5, .4, stretch=(300, 1)) * .8 + c.noise(.04, 1.1, .6, stretch=(120, 1)) * .45
    deep = sstep(1.9, 3.0, c.noise(.03, .5, .3, stretch=(90, 1)))
    h = grain * .0009 - deep * .0012
    # Slow rolling waves of the sheet, enough to bend highlights along long trims.
    h = h + c.noise(6, 40, 1.4) * .012

    # Machined drainage grooves and countersunk Torx-pattern screws.
    groove = c.zeros()
    for y in (6.0, 44.0):
        d = np.abs(c.wrap(c.Y - y))
        groove = np.maximum(groove, sstep(.26, .1, d))
        h -= sstep(.3, .08, d) * .1
    marks = c.zeros()
    for i in range(2):
        x = 12.5 + 25 * i
        for y in (25.0,):
            ix, lx, ly = c.patch(x, y, 1.6)
            d = np.hypot(lx, ly)
            sink = sstep(1.25, .98, d) * .09
            ang = np.arctan2(ly, lx)
            lobe = .42 + .09 * np.cos(ang * 6)
            socket = sstep(lobe + .03, lobe - .03, d) * .12
            h[ix] += -sink - socket
            marks[ix] = np.maximum(marks[ix], sstep(1.15, 1.0, d))

    # Finish scratches. Mostly off-axis, because they are from use, not the belt.
    fine = scratches(c, 340, [(.6, 5, .85), (5, 18, .15)], wander=.3, width=.6)
    h = h - fine * .0016
    ao = occlusion(c, h, .15)

    colour = TITANIUM * (1 + grain * .035 + c.noise(1, 14, .9, stretch=(12, 1)) * .012)[..., None]
    # Heat tint from the welding-in of the trims: straw through violet, very restrained.
    band = np.clip(np.exp(-((c.wrap(c.Y - 25) / 7.5) ** 2)) * (.7 + .3 * c.noise(4, 30, 1.1)), 0, 1)
    wobble = band + c.noise(.3, 8, 1.1) * .03
    tint = np.stack([.5 + .5 * np.cos(TAU * (wobble * 1.15 + o)) for o in (.0, .36, .62)], axis=-1)
    tint = 1 + (tint - .5) * .6
    colour = mix(colour, colour * tint.astype(np.float32), sstep(.3, .9, band) * .2)

    rough = .42 + grain * .05 + c.noise(.1, 12, .8, stretch=(30, 1)) * .02
    # Handled zones: skin oil lifts the shine and leaves a slight grime.
    hands = sstep(.5, 2.0, c.noise(.5, 9, .9, stretch=(14, 1)))
    rough = rough + hands * .04
    colour = colour * (1 - hands * .025)[..., None]
    rough = rough + fine * .08 + deep * .04
    colour = mix(colour, colour * 1.1, fine * .5)
    # Crevice dirt in grooves and screw seats.
    dirt = np.clip(groove + c.blur(marks, .15) * .55, 0, 1)
    dirt = np.clip(dirt * (.6 + .4 * sstep(-1, 1, c.noise(.3, 4, .9))), 0, 1)
    run = c.drip(dirt, 1.4) * .4 * sstep(-.5, 1, c.noise(.1, 2.4, .7, stretch=(1, 20)))
    g = np.clip(dirt * .85 + run, 0, 1)
    colour = mix(colour, np.ones_like(colour) * GRIME, g)
    rough = mix(rough, .78, g * .85)
    metal = 1 - g * .9
    colour = colour * (.6 + .4 * ao)[..., None]
    return Surface(c, h, np.clip(colour, .01, 1), np.clip(rough, .05, 1), metal, ao)


# ---------------------------------------------------------------- 6. hazard paint
def hazard_paint(c):
    rng = c.rng()
    t = c.tile
    floor = -.4
    h = c.zeros() + floor
    marks = c.zeros()
    raised(h, c.rect(.8, .8, 99.2, 49.2, .5), 0, .2, floor)
    raised(h, c.rect(.8, 50.8, 99.2, 99.2, .5), 0, .2, floor)

    for (y0, y1) in ((.8, 49.2), (50.8, 99.2)):
        for i in range(4):
            x = 12.5 + 25 * i
            bolt(c, h, marks, x, y0 + 3.2, 1.0, rng)
            bolt(c, h, marks, x, y1 - 3.2, 1.0, rng)

    # Masked diagonal bands: the tape line wanders by a millimetre or two, never more.
    period = 100 / 3
    w = c.noise(1.5, 25, 1.2) * .14 + c.noise(.2, 1.6, .7) * .022
    phase = ((c.X + c.Y + w) / period) % 1
    tri = np.abs(phase - .5)
    stripes = sstep(.255, .245, tri)
    # Black coat dragged thin by the roller shows the amber it was painted over.
    paint = np.ones((c.n, c.n, 3), dtype=np.float32) * AMBER * .8
    paint = paint * (1 + c.noise(.6, 18, 1) * .05)[..., None]
    thin = sstep(1.5, 2.8, c.noise(.3, 12, 1, stretch=(14, 1), angle=-math.pi / 4) + c.noise(.1, 1, .5, stretch=(16, 1)) * .3)
    paint = add_paint(paint, stripes * (1 - thin * .28), HAZARD_BLACK)

    # Blast-door edge duty: long shallow scrapes across the stripes, grouped not uniform.
    rake = scratches(c, 320, [(5, 26, .7), (26, 90, .3)], wander=.1, angle=-.12, spread=.09, width=1.0)
    group = sstep(-.4, 1.0, c.noise(8, 36, 1.0, stretch=(6, 1), angle=-.12))
    rake = rake * group
    bias = marks * .25 + group * .1 + np.clip(c.noise(.5, 12, .9), 0, 3) * .09 - .03
    s = weather(c, h, paint, chip=1.5, scratch=1.5, gloss=.46, bias=bias, extra_scratch=rake, rust=.1,
                thick=.03, grime=1.35, drip=9, relief=.7, primer=lin(62, 66, 68))
    return s


# ---------------------------------------------------------------- 7. dark composite
def dark_composite(c):
    rng = c.rng()
    n_tow = 128
    p = c.tile / n_tow
    i = np.floor(c.X / p).astype(np.int32)
    j = np.floor(c.Y / p).astype(np.int32)
    u = c.X / p - i - .5
    v = c.Y / p - j - .5
    warp_over = ((i + j) % 4) < 2  # 2x2 twill
    across = np.where(warp_over, u, v)
    along = np.where(warp_over, v, u)
    # Length of the float this cell belongs to: ends of a float dive under the crossing tow.
    phase = np.where(warp_over, (i + j) % 4, (i + j - 2) % 4).astype(np.float32)
    s = (phase + along + .5) / 2
    arch = np.clip(1 - (2 * s - 1) ** 4, 0, 1)
    crown = np.clip(1 - (across * 2) ** 4, 0, 1) ** .6
    fibres = c.noise(.012, .16, .3, stretch=(30, 1))
    fibresY = c.noise(.012, .16, .3, stretch=(1, 30))
    fibre = np.where(warp_over, fibresY, fibres)
    weave = arch * crown * .02 + fibre * .0012 * crown

    # Buried in cured resin: the clear coat smooths the bumps but only partly.
    resin = c.blur(weave, .05)
    drift = c.noise(5, 34, 1.4) * .014 + c.noise(.8, 4, 1) * .0018
    h = resin * .72 + weave * .28 + drift

    # Moulded inlay line and the abrasion a rifle-butt or a bulkhead leaves.
    groove = c.zeros()
    for y in (.0, 30.0):
        d = np.abs(c.wrap(c.Y - y))
        groove = np.maximum(groove, sstep(.26, .08, d))
    h = h - groove * .16
    worn = sstep(1.0, 2.5, c.noise(.3, 9, 1.0) + c.noise(.1, .9, .6) * .25)
    flats = scratches(c, 160, [(.5, 6, .85), (6, 22, .15)], wander=.3, width=.75)
    h = h - flats * .003 - worn * .006

    ao = occlusion(c, h, .2)
    base = lin(44, 48, 54)
    # A tow lit along its fibres catches differently to its neighbour: that is the twill read.
    direction = np.where(warp_over, 1.3, .74).astype(np.float32)
    shade = (.72 + .4 * arch * crown) * direction * (1 + fibre * .05)
    alb = base * shade[..., None] * (1 + c.noise(4, 30, 1.2) * .06)[..., None]
    # Scuffing whitens the resin; a little blue from the resin batch.
    alb = mix(alb, alb * 1.7 + np.array((.012, .014, .017), dtype=np.float32), worn * .5)
    alb = mix(alb, alb * 3.0 + .03, flats * .45)
    rough = .24 + (1 - crown) * .03 + c.noise(.6, 10, .9) * .018 + worn * .34 + flats * .25
    rough = rough + (1 - ao) * .15
    dirt = np.clip(groove * .9 + c.drip(groove, 1.2) * .25 * sstep(-.5, 1, c.noise(.1, 2, .7, stretch=(1, 16))), 0, 1)
    alb = mix(alb, np.ones_like(alb) * GRIME * .7, dirt)
    rough = mix(rough, .8, dirt * .8)
    alb = alb * (.6 + .4 * ao)[..., None]
    return Surface(c, h, np.clip(alb, .012, 1), np.clip(rough, .05, 1), c.zeros(), ao)


# ---------------------------------------------------------------- 8. glass-like screen
def screen_glass(c):
    t = c.tile
    # Chemically-toughened cover glass. Almost perfectly flat, with a slow optical roll.
    h = c.noise(14, 50, 1.6) * .0025 + c.noise(1.5, 8, 1.2) * .00012
    hair = scratches(c, 480, [(.4, 4, .8), (4, 16, .2)], wander=.25, width=.5)
    wipe = scratches(c, 120, [(4, 24, 1)], wander=.08, angle=.5, spread=.45, width=.5)
    pits = sstep(2.8, 3.3, c.noise(.08, .3, .3))
    h = h - hair * .0014 - wipe * .0007 - pits * .002

    # Fingerprint-grade oil film: swiped arcs and pressed ovals over a soft haze.
    swipe = sstep(.1, 1.8, c.noise(1.4, 16, 1.1, stretch=(2.2, 1), angle=.6))
    haze = sstep(-1, 2, c.noise(5, 40, 1.1))
    finger = c.zeros()
    rng = c.rng()
    ridges = c.zeros()
    for _ in range(26):
        x, y = rng.uniform(0, t), rng.uniform(0, t)
        r = rng.uniform(.6, 1.0)
        rot = rng.uniform(0, 3.14)
        ix, lx, ly = c.patch(x, y, r * 1.8)
        ca, sa = math.cos(rot), math.sin(rot)
        a = (lx * ca + ly * sa) / (r * 1.45)
        b = (-lx * sa + ly * ca) / r
        oval = sstep(1.05, .75, np.hypot(a, b))
        swirl = np.sin(np.hypot(a + .3, b * 1.3 - .2) * 44 + np.arctan2(b, a) * 1.5)
        finger[ix] = np.maximum(finger[ix], oval * rng.uniform(.25, .7))
        ridges[ix] = np.maximum(ridges[ix], oval * (swirl * .5 + .5) * rng.uniform(.3, .8))
    film = np.clip(swipe * .5 + haze * .14 + ridges * .75 + finger * .15, 0, 1)
    rough = .05 + film * .3 + hair * .2 + wipe * .05 + pits * .4
    alb = np.ones((c.n, c.n, 3), dtype=np.float32) * lin(9, 11, 14)
    alb = mix(alb, np.ones_like(alb) * lin(60, 60, 58), np.clip(film * .05 + hair * .22 + pits * .4, 0, 1))
    ao = c.zeros() + 1

    # Emissive layer: a dim amber tactical grid, sized to read at 60 cm of tile.
    em = c.zeros()
    grid = np.minimum(c.strip('x', 0, .03), c.strip('y', 0, .03))
    for k in range(1, 6):
        grid = np.minimum(grid, np.minimum(c.strip('x', k * 10, .018), c.strip('y', k * 10, .018)))
    em = np.maximum(em, sstep(.02, -.02, grid) * .13)
    ticks = c.zeros()
    for k in range(60):
        l = .9 if k % 10 == 0 else (.55 if k % 5 == 0 else .32)
        stroke(c, ticks, (k + .5 + 0, .0), (k + .5, l), .022)
        stroke(c, ticks, (.0, k + .5), (l, k + .5), .022)
    em = np.maximum(em, ticks * .32)
    block = c.zeros()
    text(c, block, 'SECTOR 7', 3, 3, 1.3, weight=.55)
    text(c, block, 'HULL 83', 3, 5.2, .9, weight=.55)
    text(c, block, 'TRACK 14', 33, 43, 1.0, weight=.55)
    text(c, block, 'BEARING 208', 33, 45, .7, weight=.6)
    text(c, block, 'SHIELD 41', 33, 13, .9, weight=.55)
    bars = c.zeros()
    rng2 = c.rng()
    for row in range(7):
        fill = rng2.uniform(.25, 1)
        bars = np.maximum(bars, sstep(.012, -.012, c.rect(33, 15 + row * 1.05, 33 + 16 * fill, 15.42 + row * 1.05)))
    bars = bars * sstep(-.2, .2, np.sin(c.X * TAU / .62) + .75)
    em = np.maximum(em, block * .62)
    em = np.maximum(em, bars * .24)
    # Contact rings around a blip, the only circular forms.
    d = np.hypot(c.wrap(c.X - 16), c.wrap(c.Y - 34))
    for r in (3, 6, 9):
        em = np.maximum(em, sstep(.03, .012, np.abs(d - r)) * .2)
    em = np.maximum(em, sstep(.42, .3, d) * 1.0)
    d2 = np.hypot(c.wrap(c.X - 21.4), c.wrap(c.Y - 30.6))
    em = np.maximum(em, sstep(.26, .18, d2))
    # Scan raster and panel falloff.
    raster = .84 + .16 * np.sin(c.Y * TAU * 8)
    glow = c.blur(em, .14) * .55 + c.blur(em, .6) * .28
    em_total = np.clip(em + glow, 0, 1.2) * raster * (.9 + .1 * sstep(-1, 1, c.noise(8, 40, 1)))
    amber = np.array((1.0, .52, .13), dtype=np.float32)
    emissive = rgb(em_total, amber) + rgb(em * .55, np.array((1, .9, .75), dtype=np.float32))
    return Surface(c, h, np.clip(alb, .002, 1), np.clip(rough, .03, 1), c.zeros(), ao, np.clip(emissive, 0, 1))


# name, recipe, tile (cm), seed, normal strength
MATERIALS = [
    ('WallPanel', wall_panel, 200, 11, 1.5),
    ('DeckPlate', deck_plate, 160, 22, 1.5),
    ('CeilingPanel', ceiling_panel, 200, 33, 1.4),
    ('FloorRunner', floor_runner, 100, 44, 1.6),
    ('TitaniumTrim', titanium_trim, 50, 55, 1.6),
    ('HazardPaint', hazard_paint, 100, 66, 1.5),
    ('DarkComposite', dark_composite, 60, 77, 1.4),
    ('ScreenGlass', screen_glass, 60, 88, 1.0),
]


# ---------------------------------------------------------------- decal atlas
DECAL_CELLS = {
    'deck07': (0, 0), 'deck03': (1, 0), 'svc3b': (2, 0), 'fr22': (3, 0),
    'meridian': (0, 1), 'brass_plate': (1, 1), 'repair_doubler': (2, 1), 'plug_weld': (3, 1),
    'scorch_round': (0, 2), 'scorch_blast': (1, 2), 'impact': (2, 2), 'shrapnel': (3, 2),
    'beam_gouge': (0, 3), 'rust_run': (1, 3), 'soot_run': (2, 3), 'oil_stain': (3, 3),
}


def decal_atlas(c):
    """Sixteen 50 cm cells at the wall's texel density: everything that must not tile."""
    rng = c.rng()
    alb = np.ones((c.n, c.n, 3), dtype=np.float32) * .1
    alpha, h, metal = c.zeros(), c.zeros(), c.zeros()
    rough = c.zeros() + .6

    def local(name):
        i, j = DECAL_CELLS[name]
        cx, cy = (i + .5) * 50, (j + .5) * 50
        lx, ly = c.X - cx, c.Y - cy
        return cx, cy, lx, ly, sstep(24.5, 22.5, np.maximum(np.abs(lx), np.abs(ly)))

    def put(name, colour, mask, r=.6, m=0.0, height=None):
        """Write one cell. Colour fills the whole cell so bilinear never fringes on alpha 0."""
        *_, fade = local(name)
        cell = np.abs(local(name)[2]) < 25
        cell = cell & (np.abs(local(name)[3]) < 25)
        col = colour if getattr(colour, 'ndim', 1) == 3 else np.ones_like(alb) * colour
        alb[cell] = col[cell]
        alpha[cell] = (mask * fade)[cell]
        rough[cell] = (r * np.ones_like(h))[cell]
        metal[cell] = (m * np.ones_like(h))[cell]
        if height is not None:
            h[cell] = (height * fade)[cell]

    def stencil(name, lines, colour, wear):
        cx, cy, *_ = local(name)
        ink = c.zeros()
        y = cy - 10
        for string, size in lines:
            text(c, ink, string, cx - 22, y, size, weight=1.0)
            y += size * 1.5
        put(name, colour, np.clip(sprayed(c, ink, wear) * 1.1, 0, 1), .55)

    stencil('deck07', (('DECK 07', 7.5), ('FRAME 14-C', 3.0)), STENCIL_WHITE, .05)
    stencil('deck03', (('DECK 03', 7.5), ('FRAME 09-A', 3.0)), STENCIL_WHITE, .25)
    stencil('svc3b', (('SVC 3-B', 6.0), ('DO NOT STOW', 3.0)), HAZARD_BLACK, .3)
    stencil('fr22', (('FR 22', 6.0), ('P-07', 3.5)), STENCIL_WHITE, .8)
    stencil('meridian', (('MERIDIAN', 5.5), ('STATION GUARD', 3.0)), AMBER, .15)

    # Brass identity plate, polished out of habit, dark in its engraving.
    cx, cy, lx, ly, _ = local('brass_plate')
    sdf = c.rect(cx - 16, cy - 9, cx + 16, cy + 9, .5)
    marks = c.zeros()
    hp = sstep(.14, -.12, sdf) * .16
    for x, y in ((-14, -7), (14, -7), (-14, 7), (14, 7)):
        rivet(c, hp, marks, cx + x, cy + y, .55, rng)
    ink = c.zeros()
    text(c, ink, 'FR 14-C', cx - 12, cy - 6, 3.2, weight=.7)
    text(c, ink, 'BLKHD 07', cx - 12, cy + .5, 2.9, weight=.6)
    ink = c.blur(ink, .35 / c.px)
    brush = c.noise(.1, 8, .5, stretch=(40, 1))
    tarnish = sstep(-.3, 1.4, c.noise(1, 10, 1.1) - sdf * .12)
    colour = (BRASS * (1 + brush * .05)[..., None]) * (1 - tarnish * .4 - ink * .85)[..., None]
    put('brass_plate', colour, sstep(.12, -.12, sdf), .3 + tarnish * .22 + ink * .4 + brush * .03, 1 - ink * .9, hp - ink * .02)

    # Welded doubler over a hit: primed and never finished. Best replaced by a mesh up close.
    cx, cy, lx, ly, _ = local('repair_doubler')
    sdf = c.rect(cx - 19, cy - 19, cx + 19, cy + 19, 1.2)
    bead = sstep(1.0, .3, np.abs(sdf - .4))
    ripple = np.sin((c.X + c.Y) * 7 + c.noise(.8, 6, 1) * 1.5) * .05 + c.noise(.12, .6, .4) * .03
    hp = sstep(.1, -.15, sdf) * .32 + bead * (.2 + ripple)
    marks = c.zeros()
    for x, y in ((-15, -15), (15, -15), (-15, 15), (15, 15)):
        bolt(c, hp, marks, cx + x, cy + y, .9, rng)
    ink = c.zeros()
    text(c, ink, 'REPAIR 3/19', cx - 11, cy + 8, 2.4)
    primer = mix(np.ones_like(alb) * lin(88, 92, 86), np.ones_like(alb) * STENCIL_WHITE, sprayed(c, ink, .1) * .9)
    burn = np.clip(sstep(5, .5, np.abs(sdf)) * .75, 0, 1) * sstep(-1, .8, c.noise(.8, 8, 1))
    primer = mix(primer, np.ones_like(alb) * SOOT, burn)
    primer = mix(primer, np.ones_like(alb) * STEEL * .62, bead)
    put('repair_doubler', primer, sstep(7, 1, sdf + c.noise(.8, 7, 1) * .9) * .97 * (1 - .75 * sstep(.2, 1.2, sdf)),
        .62 - bead * .2, bead * .8, hp)

    # Shell hole plugged with a welded disc.
    cx, cy, lx, ly, _ = local('plug_weld')
    d = np.hypot(lx, ly) + c.noise(.5, 5, 1) * .12
    bead = sstep(1.1, .35, np.abs(d - 11.5))
    hp = sstep(11.5, 11.2, d) * .25 + bead * (.24 + c.noise(.12, .7, .4) * .03)
    hp = hp + np.sin(np.arctan2(ly, lx) * 46 + d) * bead * .04
    colour = mix(np.ones_like(alb) * lin(78, 82, 80), np.ones_like(alb) * STEEL * .6, bead)
    halo = sstep(19, 12, d) * sstep(-1, .8, c.noise(.6, 7, 1))
    colour = mix(colour, np.ones_like(alb) * SOOT, halo * sstep(11, 13, d))
    put('plug_weld', colour, sstep(21, 12.5, d + c.noise(.8, 7, 1) * 1.6), .6 - bead * .2, bead * .8, hp)

    # Scorch: char core, blistered paint, brown heat-fade edge.
    def scorch(name, shape):
        cx, cy, lx, ly, _ = local(name)
        d = shape(lx, ly)
        ang = np.arctan2(ly, lx)
        rays = np.sin(ang * 9 + c.noise(4, 22, 1.2) * 2.2) * .9 + np.sin(ang * 23 + 1.1) * .5
        d = d + (c.noise(3, 20, 1.2) * 2.0 + rays + c.noise(.3, 2.5, .9) * .3) * sstep(.1, .7, d / 20)
        core = sstep(13, 4, d)
        blister = sstep(.4, 1.6, c.noise(.25, 1.4, .5)) * sstep(18, 8, d)
        col = mix(np.ones_like(alb) * lin(84, 70, 56), np.ones_like(alb) * lin(44, 42, 41), sstep(20, 7, d))
        col = mix(col, np.ones_like(alb) * lin(58, 55, 52), blister * .5)
        put(name, col, sstep(24, 1, d) ** 1.7 * .9, .7 + core * .2 - blister * .15, 0.0, blister * .05 - core * .02)

    scorch('scorch_round', lambda x, y: np.hypot(x, y))
    scorch('scorch_blast', lambda x, y: np.hypot(x * 1.9, (y - 11) * .74))

    # Impact: torn petals of bare steel, heat rainbow, soot.
    def crater(lx, ly, r, cell_h, cell_col, cell_mask, cell_rough, cell_metal):
        d = np.hypot(lx, ly)
        ang = np.arctan2(ly, lx)
        torn = d + (np.sin(ang * 5 + r * 9) * .26 + np.sin(ang * 11 + r * 4) * .14) * r + c.noise(.2, 1.6, .8) * .09 * r
        hole = sstep(r * .98, r * .82, torn)
        lip = sstep(r * 1.1, r * 1.0, torn) * sstep(r * 2.5, r * 1.15, torn)
        bare = sstep(r * 1.9, r * 1.35, torn) * (1 - hole) * sstep(-1.1, .1, c.noise(.3, 3, .9))
        heat = sstep(r * 5.0, r * 2.3, torn) * (1 - bare) * (1 - hole)
        wave = np.stack([.5 + .5 * np.cos(TAU * (d / (r * 3) + o)) for o in (0, .36, .62)], axis=-1).astype(np.float32)
        steel = STEEL * (.42 + .3 * wave) * (1 + c.noise(.2, 3, .9) * .1)[..., None]
        soot = sstep(r * 8, r * 1.5, torn + c.noise(.8, 7, 1) * r * .7) ** 1.5
        col = mix(np.ones_like(alb) * SOOT, steel, bare)
        col = mix(col, np.ones_like(alb) * .006, hole)
        cell_h += (lip * r * .22 - hole * r * .6) - bare * .03
        cell_col[:] = mix(cell_col, col, np.maximum(soot, np.maximum(bare, hole)))
        cell_mask[:] = np.maximum(cell_mask, np.maximum(soot * .85, np.maximum(bare, hole)))
        cell_rough[:] = mix(cell_rough, np.full_like(h, .5), bare)
        cell_metal[:] = np.maximum(cell_metal, bare * (1 - heat * .2))

    cx, cy, lx, ly, _ = local('impact')
    hp, colour, mask, rp, mp = c.zeros(), np.ones_like(alb) * SOOT, c.zeros(), c.zeros() + .82, c.zeros()
    crater(lx, ly, 3.2, hp, colour, mask, rp, mp)
    put('impact', colour, mask, rp, mp, hp)

    cx, cy, lx, ly, _ = local('shrapnel')
    hp, colour, mask, rp, mp = c.zeros(), np.ones_like(alb) * SOOT, c.zeros(), c.zeros() + .82, c.zeros()
    for _ in range(11):
        ox, oy = rng.uniform(-16, 16, 2)
        crater(lx - ox, ly - oy, rng.uniform(.28, .95), hp, colour, mask, rp, mp)
    put('shrapnel', colour, mask, rp, mp, hp)

    # Beam gouge: three parallel molten furrows, the First Ones' signature on a bulkhead.
    cx, cy, lx, ly, _ = local('beam_gouge')
    furrow = c.zeros()
    for off, half in ((-7.5, .55), (0, .95), (6.5, .7)):
        stroke(c, furrow, (cx - 21, cy + off - 3), (cx + 21, cy + off + 3), half, 1, 1)
    furrow = c.warp(furrow, c.noise(2, 12, 1.2) * .35, c.noise(2, 12, 1.2) * .5)
    furrow = c.blur(furrow, .18) * sstep(-1.6, .3, c.noise(.6, 7, 1) + .4)
    furrow = np.clip(furrow * 1.6, 0, 1)
    halo = np.clip(c.blur(furrow, 2.6) * 2.2, 0, 1) ** 1.3
    molten = STEEL * (.34 + .22 * sstep(-1, 1, c.noise(.3, 3, .8)))[..., None]
    colour = mix(np.ones_like(alb) * lin(44, 42, 41), molten, furrow)
    put('beam_gouge', colour, np.maximum(halo * .82, furrow), .78 - furrow * .3, furrow, -furrow * .35)

    # Runs: tall streaks hanging from the top of the cell, to sit under seams and bolts.
    def run(name, colour, strength, r):
        cx, cy, lx, ly, _ = local(name)
        source = sstep(1.5, 0, np.abs(ly + 20)) * (np.abs(lx) < 19)
        streak = c.drip(source.astype(np.float32), 16) * 1.5
        comb = sstep(-.2, 1.2, c.noise(.3, 7, .8, stretch=(1, 34)))
        put(name, colour, np.clip(streak * comb * strength, 0, .92), r)

    run('rust_run', RUST, 3.2, .78)
    run('soot_run', SOOT, 3.2, .85)

    cx, cy, lx, ly, _ = local('oil_stain')
    d = np.hypot(lx * 1.15, ly) + c.noise(2, 16, 1.2) * 3.2 + c.noise(.4, 3, .8) * .5
    wet = sstep(16, 12, d)
    put('oil_stain', np.ones_like(alb) * lin(34, 31, 28), sstep(23, 5, d) ** 1.4 * .62 + wet * .1, .42 - wet * .12)

    ao = occlusion(c, h)
    return Surface(c, h, np.clip(alb, .004, 1), np.clip(rough, .05, 1), np.clip(metal, 0, 1), ao), alpha


def export_extras():
    s, alpha = decal_atlas(Canvas(2048, 200, 91))
    base = OUT / 'T_StationDecals'
    write_png(f'{base}_BaseColor.png', np.dstack((to_srgb(s.alb), alpha)), 8, True)
    write_png(f'{base}_Normal.png', normal_map(s.c, s.h, 1.5) * .5 + .5, 16)
    write_png(f'{base}_ORM.png', np.dstack((s.ao, s.rough, s.metal)), 8)
    print('StationDecals: written')
    # World-space tile breaker: R grime patches, G vertical wash, B fine mottle.
    c = Canvas(1024, 970, 95)
    def unit(a):
        return np.clip(.5 + a * .2, 0, 1)
    write_png(OUT / 'T_MacroVariation_Mask.png', np.dstack((
        unit(c.noise(30, 400, 1.2)), unit(c.noise(8, 160, 1, stretch=(1, 7))), unit(c.noise(4, 50, .9)))), 8)
    print('MacroVariation: written')


# ---------------------------------------------------------------- PNG encoding
def write_png(path, data, bits=8, srgb=False):
    """Plain PNG writer: exact code values, no colour management in the path."""
    data = np.clip(data, 0, 1)
    if data.ndim == 2:
        data = data[..., None]
    height, width, channels = data.shape
    if bits == 16:
        raw = (data * 65535 + .5).astype('>u2').tobytes()
        row = width * channels * 2
    else:
        rng = np.random.default_rng(1)
        dither = rng.random(data.shape, dtype=np.float32) - rng.random(data.shape, dtype=np.float32)
        raw = np.clip(data * 255 + .5 + dither * .5, 0, 255).astype(np.uint8).tobytes()
        row = width * channels
    grid = np.frombuffer(raw, np.uint8).reshape(height, row)
    up = grid.copy()
    up[1:] -= grid[:-1]
    framed = np.zeros((height, row + 1), np.uint8)
    framed[:, 0] = 2
    framed[:, 1:] = up

    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body) & 0xffffffff)
    head = struct.pack('>IIBBBBB', width, height, bits, {1: 0, 3: 2, 4: 6}[channels], 0, 0, 0)
    blob = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', head)
    if srgb:
        blob += chunk(b'sRGB', b'\x00')
    blob += chunk(b'IDAT', zlib.compress(framed.tobytes(), 6)) + chunk(b'IEND', b'')
    Path(path).write_bytes(blob)


def to_srgb(a):
    a = np.clip(a, 0, 1)
    return np.where(a <= .0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - .055)


def normal_map(c, h, strength):
    """DirectX convention: green is positive toward the bottom of the image, so a bump's
    upper flank is dark in green and its lower flank is bright."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * .5 * c.px * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * .5 * c.px * strength
    # A light cross filter keeps single-pixel gradients from aliasing into sparkle.
    dx = (dx * 2 + np.roll(dx, 1, 0) + np.roll(dx, -1, 0)) / 4
    dy = (dy * 2 + np.roll(dy, 1, 1) + np.roll(dy, -1, 1)) / 4
    length = np.sqrt(dx * dx + dy * dy + 1)
    return np.dstack((-dx / length, -dy / length, 1 / length))


def export(name, s, strength):
    OUT.mkdir(parents=True, exist_ok=True)
    c = s.c
    base = OUT / f'T_{name}'
    write_png(f'{base}_BaseColor.png', to_srgb(s.alb), 8, True)
    write_png(f'{base}_Normal.png', normal_map(c, s.h, strength) * .5 + .5, 16)
    write_png(f'{base}_ORM.png', np.dstack((s.ao, s.rough, s.metal)), 8)
    lo, hi = float(s.h.min()), float(s.h.max())
    write_png(f'{base}_Height.png', (s.h - lo) / max(hi - lo, 1e-6), 16)
    if s.emissive is not None:
        write_png(f'{base}_Emissive.png', to_srgb(s.emissive), 8, True)
    print(f'{name}: height range {hi - lo:.3f} cm, albedo mean {s.alb.mean((0, 1)).round(3)}, '
          f'rough {s.rough.mean():.2f}, metal {s.metal.mean():.2f}')
    # Seam check: the step across the wrap must look like any other adjacent row or column.
    img = s.alb.mean(-1)
    wrap_x = np.abs(img[:, 0] - img[:, -1]).mean() / np.abs(np.diff(img, axis=1)).mean()
    wrap_y = np.abs(img[0] - img[-1]).mean() / np.abs(np.diff(img, axis=0)).mean()
    print(f'{name}: seam ratio x {wrap_x:.2f} y {wrap_y:.2f}')


# ---------------------------------------------------------------- review rendering
def load_pixels(path):
    img = bpy.data.images.load(str(path))
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    data = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(data)
    bpy.data.images.remove(img)
    return data.reshape(h, w, 4)[::-1]


def make_material(name, cutout=False, macro=False):
    """Unreal-equivalent shader, flipping green since Cycles' normal node expects OpenGL."""
    mat = bpy.data.materials.new(name + ('_Macro' if macro else ''))
    mat.use_nodes = True
    t = mat.node_tree
    bsdf = next(n for n in t.nodes if n.type == 'BSDF_PRINCIPLED')
    def tex(suffix, colour):
        node = t.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(str(OUT / f'T_{name}_{suffix}.png'), check_existing=True)
        node.image.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
        node.inputs['Vector'].default_value = (0, 0, 0)
        t.links.new(t.nodes.new('ShaderNodeUVMap').outputs['UV'], node.inputs['Vector'])
        return node
    colour_node = tex('BaseColor', True)
    colour_out = colour_node.outputs['Color']
    if cutout:
        t.links.new(colour_node.outputs['Alpha'], bsdf.inputs['Alpha'])
    if macro:
        # What the Unreal master material should do: BaseColor * lerp(.70, 1.18, mask.r), from world position.
        geo = t.nodes.new('ShaderNodeNewGeometry')
        sep_pos = t.nodes.new('ShaderNodeSeparateXYZ')
        t.links.new(geo.outputs['Position'], sep_pos.inputs[0])
        add = t.nodes.new('ShaderNodeMath')
        add.operation = 'ADD'
        t.links.new(sep_pos.outputs['X'], add.inputs[0])
        t.links.new(sep_pos.outputs['Y'], add.inputs[1])
        vec = t.nodes.new('ShaderNodeCombineXYZ')
        t.links.new(add.outputs[0], vec.inputs['X'])
        t.links.new(sep_pos.outputs['Z'], vec.inputs['Y'])
        scale = t.nodes.new('ShaderNodeVectorMath')
        scale.operation = 'SCALE'
        scale.inputs['Scale'].default_value = 1 / 970
        t.links.new(vec.outputs[0], scale.inputs[0])
        mask = t.nodes.new('ShaderNodeTexImage')
        mask.image = bpy.data.images.load(str(OUT / 'T_MacroVariation_Mask.png'), check_existing=True)
        mask.image.colorspace_settings.name = 'Non-Color'
        t.links.new(scale.outputs[0], mask.inputs['Vector'])
        rampm = t.nodes.new('ShaderNodeMapRange')
        rampm.inputs['To Min'].default_value = .7
        rampm.inputs['To Max'].default_value = 1.18
        t.links.new(mask.outputs['Color'], rampm.inputs['Value'])
        mult = t.nodes.new('ShaderNodeVectorMath')
        mult.operation = 'SCALE'
        t.links.new(colour_out, mult.inputs[0])
        t.links.new(rampm.outputs[0], mult.inputs['Scale'])
        colour_out = mult.outputs[0]
    t.links.new(colour_out, bsdf.inputs['Base Color'])
    orm = t.nodes.new('ShaderNodeSeparateColor')
    t.links.new(tex('ORM', False).outputs['Color'], orm.inputs['Color'])
    t.links.new(orm.outputs['Green'], bsdf.inputs['Roughness'])
    t.links.new(orm.outputs['Blue'], bsdf.inputs['Metallic'])
    sep = t.nodes.new('ShaderNodeSeparateColor')
    t.links.new(tex('Normal', False).outputs['Color'], sep.inputs['Color'])
    flip = t.nodes.new('ShaderNodeMath')
    flip.operation = 'SUBTRACT'
    flip.inputs[0].default_value = 1
    t.links.new(sep.outputs['Green'], flip.inputs[1])
    comb = t.nodes.new('ShaderNodeCombineColor')
    t.links.new(sep.outputs['Red'], comb.inputs['Red'])
    t.links.new(flip.outputs[0], comb.inputs['Green'])
    t.links.new(sep.outputs['Blue'], comb.inputs['Blue'])
    nrm = t.nodes.new('ShaderNodeNormalMap')
    t.links.new(comb.outputs['Color'], nrm.inputs['Color'])
    t.links.new(nrm.outputs['Normal'], bsdf.inputs['Normal'])
    em_path = OUT / f'T_{name}_Emissive.png'
    if em_path.exists():
        t.links.new(tex('Emissive', True).outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 1.5
    return mat


def reset_scene(samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = DENOISE
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .02
    scene.cycles.max_bounces = 6
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = 0
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    world = bpy.data.worlds.new('Studio')
    scene.world = world
    world.use_nodes = True
    t = world.node_tree
    bg = t.nodes['Background']
    coord = t.nodes.new('ShaderNodeTexCoord')
    grad = t.nodes.new('ShaderNodeSeparateXYZ')
    ramp = t.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .35
    ramp.color_ramp.elements[0].color = (.012, .014, .018, 1)
    ramp.color_ramp.elements[1].position = .85
    ramp.color_ramp.elements[1].color = (.22, .25, .29, 1)
    remap = t.nodes.new('ShaderNodeMath')
    remap.operation = 'MULTIPLY_ADD'
    remap.inputs[1].default_value = .5
    remap.inputs[2].default_value = .5
    t.links.new(coord.outputs['Generated'], grad.inputs[0])
    t.links.new(grad.outputs['Z'], remap.inputs[0])
    t.links.new(remap.outputs[0], ramp.inputs['Fac'])
    t.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    return scene


def area(name, location, target, size, energy, colour):
    light = bpy.data.lights.new(name, 'AREA')
    light.size = size
    light.energy = energy
    light.color = colour
    ob = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = location
    aim(ob, target)
    return ob


def aim(ob, target):
    from mathutils import Vector
    d = Vector(target) - Vector(ob.location)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(location, target, lens=70):
    cam = bpy.data.cameras.new('Cam')
    cam.lens = lens
    cam.clip_start = 1
    cam.clip_end = 100000
    ob = bpy.data.objects.new('Cam', cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = location
    aim(ob, target)
    bpy.context.scene.camera = ob
    return ob


def quad_mesh(name, verts, uvs, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [tuple(range(len(verts)))])
    layer = mesh.uv_layers.new(name='UV')
    for i, uv in enumerate(uvs):
        layer.data[i].uv = uv
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def sphere(name, radius, mat, repeat):
    mesh = bpy.data.meshes.new(name)
    rings, segs = 96, 192
    verts, faces, uvs = [], [], []
    for j in range(rings + 1):
        lat = math.pi * j / rings
        for i in range(segs + 1):
            lon = TAU * i / segs
            verts.append((radius * math.sin(lat) * math.cos(lon), radius * math.sin(lat) * math.sin(lon), radius * math.cos(lat)))
            uvs.append((i / segs * repeat, (1 - j / rings) * repeat / 2))
    for j in range(rings):
        for i in range(segs):
            a = j * (segs + 1) + i
            faces.append((a, a + segs + 1, a + segs + 2, a + 1))
    mesh.from_pydata(verts, [], faces)
    layer = mesh.uv_layers.new(name='UV')
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[mesh.loops[li].vertex_index]
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def render(path, w, h):
    scene = bpy.context.scene
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def label(sheet, string, x, y, height):
    """Print a caption into an sRGB uint-range float sheet with the stencil glyphs."""
    px_h, px_w = sheet.shape[:2]
    mask_c = np.zeros((int(height * 2), int(len(string) * height * .9) + 8), np.float32)

    u = height / 12
    cursor = 2.0
    half = u * .95
    hh, ww = mask_c.shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    for ch in string:
        cursor -= u * 2 if ch in 'I1.' else 0
        for st in filter(None, GLYPHS.get(ch, '').split(';')):
            pts = [(cursor + int(p[0], 16) * u, 2 + (12 - int(p[1], 16)) * u) for p in st.split()]
            for i in range(len(pts) - 1):
                (x0, y0), (x1, y1) = pts[i], pts[i + 1]
                ln = math.hypot(x1 - x0, y1 - y0) or 1
                ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
                al = (xx - x0) * ux + (yy - y0) * uy
                pe = np.abs(-(xx - x0) * uy + (yy - y0) * ux)
                cov = np.clip(.5 + half - pe, 0, 1) * np.clip(.5 + al + half, 0, 1) * np.clip(.5 + ln + half - al, 0, 1)
                mask_c = np.maximum(mask_c, cov)
        cursor += u * (6 if ch in 'I1.' else 9.6)
    hh = min(hh, px_h - y)
    ww = min(ww, px_w - x)
    sheet[y:y + hh, x:x + ww, :3] = mix(sheet[y:y + hh, x:x + ww, :3], np.array((.86, .62, .28), np.float32) * 1.0, mask_c[:hh, :ww])


def contact_sheet(samples, names):
    REVIEW.mkdir(parents=True, exist_ok=True)
    temp = REVIEW / '_cells'
    temp.mkdir(exist_ok=True)
    cell_h, sphere_w, plane_w = 460, 460, 700
    cols = 2
    selected = [m for m in MATERIALS if m[0] in names]
    rows = math.ceil(len(selected) / cols)
    sheet = np.full((rows * (cell_h + 12) + 12, cols * (sphere_w + plane_w + 16) + 12, 4), .03, np.float32)
    sheet[..., 3] = 1
    for idx, (name, _, tile, _, _) in enumerate(selected):
        for kind in ('sphere', 'plane'):
            scene = reset_scene(samples)
            mat = make_material(name)
            if kind == 'sphere':
                # Sphere diameter equals one tile, so features appear at true relative scale.
                sphere('S', tile / 2, mat, 2)
                r = tile / 2
                camera((0, -r * 5.2, r * .4), (0, 0, 0), 70)
                area('Key', (-r * 2.6, -r * 2.6, r * 2.2), (0, 0, 0), r * 1.6, r * r * 90, (1, .93, .84))
                area('Fill', (r * 3, -r * 1.6, r * .2), (0, 0, 0), r * 2.6, r * r * 22, (.72, .82, 1))
                area('Rim', (r * 1.2, r * 3, r * 2), (0, 0, 0), r * 1.4, r * r * 95, (1, .82, .6))
                out = temp / f'{name}_sphere.png'
                render(out, sphere_w, cell_h)
            else:
                # 3x3 tiles seen obliquely. Any seam shows up as a straight grid line.
                t = tile
                quad_mesh('P', [(-1.5 * t, -1.5 * t, 0), (1.5 * t, -1.5 * t, 0), (1.5 * t, 1.5 * t, 0), (-1.5 * t, 1.5 * t, 0)],
                          [(0, 0), (3, 0), (3, 3), (0, 3)], mat)
                camera((.15 * t, -2.1 * t, 1.25 * t), (.0, -.15 * t, 0), 50)
                area('Key', (-t * 1.4, -t * .5, t * 1.5), (0, 0, 0), t * 1.2, t * t * 48, (1, .93, .84))
                area('Fill', (t * 1.8, -t, t), (0, 0, 0), t * 1.8, t * t * 12, (.72, .82, 1))
                area('Rim', (2.2 * t, t * 2.0, t * .45), (0, 0, 0), t * .9, t * t * 26, (1, .82, .6))
                out = temp / f'{name}_plane.png'
                render(out, plane_w, cell_h)
        col = idx % cols
        row = idx // cols
        y = 12 + row * (cell_h + 12)
        x = 12 + col * (sphere_w + plane_w + 16)
        sheet[y:y + cell_h, x:x + sphere_w] = load_pixels(temp / f'{name}_sphere.png')
        sheet[y:y + cell_h, x + sphere_w + 4:x + sphere_w + 4 + plane_w] = load_pixels(temp / f'{name}_plane.png')
        label(sheet, f'{name.upper()}  {int(tile)} CM', x + 10, y + 8, 18)
    out = REVIEW / ('materials.png' if len(selected) == len(MATERIALS) else 'materials_partial.png')
    write_png(out, sheet[..., :3], 8, True)
    print('wrote', out)


def corridor(samples):
    """A live test: the set assembled at true scale, because spheres flatter everything."""
    scene = reset_scene(samples)
    REVIEW.mkdir(parents=True, exist_ok=True)
    mats = {name: make_material(name, macro=name in ('WallPanel', 'DeckPlate', 'CeilingPanel')) for name, *_ in MATERIALS}
    tiles = {name: tile for name, _, tile, _, _ in MATERIALS}
    W, H, L = 420.0, 300.0, 1400.0
    t = tiles['DeckPlate']
    quad_mesh('Deck', [(-W / 2, 0, 0), (W / 2, 0, 0), (W / 2, L, 0), (-W / 2, L, 0)],
              [(0, 0), (W / t, 0), (W / t, L / t), (0, L / t)], mats['DeckPlate'])
    t = tiles['CeilingPanel']
    quad_mesh('Ceil', [(-W / 2, 0, H), (-W / 2, L, H), (W / 2, L, H), (W / 2, 0, H)],
              [(0, 0), (0, L / t), (W / t, L / t), (W / t, 0)], mats['CeilingPanel'])
    t = tiles['WallPanel']
    wh = 200.0
    for side, x in ((-1, -W / 2), (1, W / 2)):
        y0, y1 = (0, L) if side < 0 else (L, 0)
        # Bottom of the wall tile (v=0 here means the tile's last row, the service bay).
        quad_mesh('Wall', [(x, y0, 8), (x, y1, 8), (x, y1, 8 + wh), (x, y0, 8 + wh)],
                  [(0, 0), (L / t, 0), (L / t, 1), (0, 1)], mats['WallPanel'])
        tc = tiles['DarkComposite']
        quad_mesh('Skirt', [(x, y0, 0), (x, y1, 0), (x, y1, 8), (x, y0, 8)],
                  [(0, 0), (L / tc, 0), (L / tc, 8 / tc), (0, 8 / tc)], mats['DarkComposite'])
        # Trim ledge at the top of the wall tile.
        tt = tiles['TitaniumTrim']
        quad_mesh('Trim', [(x, y0, 8 + wh), (x, y1, 8 + wh), (x, y1, 8 + wh + 14), (x, y0, 8 + wh + 14)],
                  [(0, 0), (L / tt, 0), (L / tt, 14 / tt), (0, 14 / tt)], mats['TitaniumTrim'])
        quad_mesh('Upper', [(x, y0, 222), (x, y1, 222), (x, y1, H), (x, y0, H)],
                  [(0, .6), (L / t, .6), (L / t, 1), (0, 1)], mats['WallPanel'])
    t = tiles['FloorRunner']
    rw = 100.0
    quad_mesh('Runner', [(-rw / 2, 0, .4), (rw / 2, 0, .4), (rw / 2, L, .4), (-rw / 2, L, .4)],
              [(0, 0), (1, 0), (1, L / t), (0, L / t)], mats['FloorRunner'])
    # End door: hazard frame around a composite slab.
    t = tiles['HazardPaint']
    quad_mesh('Frame', [(-W / 2, L, 0), (W / 2, L, 0), (W / 2, L, H), (-W / 2, L, H)],
              [(0, 0), (W / t, 0), (W / t, H / t), (0, H / t)], mats['HazardPaint'])
    tc = tiles['DarkComposite']
    quad_mesh('Door', [(-140, L - 4, 0), (140, L - 4, 0), (140, L - 4, 240), (-140, L - 4, 240)],
              [(0, 0), (280 / tc, 0), (280 / tc, 240 / tc), (0, 240 / tc)], mats['DarkComposite'])
    # Wall screen.
    ts = tiles['ScreenGlass']
    quad_mesh('Screen', [(W / 2 - 1.5, 560, 118), (W / 2 - 1.5, 640, 118), (W / 2 - 1.5, 640, 168), (W / 2 - 1.5, 560, 168)],
              [(0, 0), (80 / ts, 0), (80 / ts, 50 / ts), (0, 50 / ts)], mats['ScreenGlass'])

    decal = make_material('StationDecals', cutout=True)
    def dress(cell, side, along, z, size):
        i, j = DECAL_CELLS[cell]
        x = side * (W / 2 - .4)
        a, b = (along - size / 2, along + size / 2) if side < 0 else (along + size / 2, along - size / 2)
        quad_mesh('Decal', [(x, a, z), (x, b, z), (x, b, z + size), (x, a, z + size)],
                  [(i / 4, 1 - (j + 1) / 4), ((i + 1) / 4, 1 - (j + 1) / 4), ((i + 1) / 4, 1 - j / 4), (i / 4, 1 - j / 4)], decal)
    for cell, side, along, z, size in (
            ('deck07', 1, 300, 112, 92), ('deck07', -1, 760, 112, 92), ('brass_plate', -1, 330, 118, 38),
            ('repair_doubler', -1, 1000, 112, 66), ('scorch_blast', -1, 520, 74, 150), ('impact', -1, 520, 118, 48),
            ('beam_gouge', 1, 760, 92, 120), ('shrapnel', 1, 960, 104, 90),
            ('rust_run', 1, 520, 124, 84), ('soot_run', -1, 880, 124, 84), ('plug_weld', 1, 1120, 128, 46),
            ('meridian', -1, 1080, 165, 58)):
        dress(cell, side, along, z, size)
    for (cell, x, y, size) in (('oil_stain', 125, 400, 130), ('scorch_round', -125, 620, 200), ('shrapnel', 105, 700, 80)):
        i, j = DECAL_CELLS[cell]
        quad_mesh('FloorDecal', [(x - size / 2, y - size / 2, .5), (x + size / 2, y - size / 2, .5), (x + size / 2, y + size / 2, .5), (x - size / 2, y + size / 2, .5)],
                  [(i / 4, 1 - (j + 1) / 4), ((i + 1) / 4, 1 - (j + 1) / 4), ((i + 1) / 4, 1 - j / 4), (i / 4, 1 - j / 4)], decal)

    for y in range(150, int(L), 300):
        area('Bay', (0, y, H - 6), (0, y, 0), 70, 900000, (1, .9, .78))
    area('Far', (0, L - 60, H - 20), (0, L, 120), 90, 700000, (1, .62, .28))
    area('Back', (0, 30, 180), (0, 200, 100), 120, 160000, (.62, .75, 1))
    camera((-70, 40, 148), (34, 900, 92), 26)
    render(REVIEW / 'materials_corridor.png', 1600, 900)


def macro(samples, names):
    """Player-distance check: about a metre of surface filling each cell."""
    temp = REVIEW / '_cells'
    temp.mkdir(parents=True, exist_ok=True)
    selected = [m for m in MATERIALS if m[0] in names]
    w, h = 640, 420
    cols = 3
    rows = math.ceil(len(selected) / cols)
    sheet = np.full((rows * (h + 8) + 8, cols * (w + 8) + 8, 3), .03, np.float32)
    for idx, (name, _, tile, _, _) in enumerate(selected):
        reset_scene(samples)
        mat = make_material(name)
        t = tile
        quad_mesh('P', [(-t, -t, 0), (t, -t, 0), (t, t, 0), (-t, t, 0)], [(0, 0), (2, 0), (2, 2), (0, 2)], mat)
        span = min(t, 90)
        camera((span * .1, -span * .62, span * .62), (0, span * .02, 0), 40)
        area('Key', (-span, -span * .4, span * 1.1), (0, 0, 0), span * .8, span * span * 30, (1, .93, .84))
        area('Fill', (span * 1.3, -span * .6, span * .7), (0, 0, 0), span * 1.2, span * span * 7, (.72, .82, 1))
        out = temp / f'{name}_macro.png'
        render(out, w, h)
        y, x = 8 + idx // cols * (h + 8), 8 + idx % cols * (w + 8)
        sheet[y:y + h, x:x + w] = load_pixels(out)[..., :3]
        label(sheet, name.upper(), x + 8, y + 6, 15)
    write_png(REVIEW / 'materials_macro.png', sheet, 8, True)


# ---------------------------------------------------------------- art-director checks
def audit(names):
    """Measure the written PNGs, not the arrays that were meant to go into them."""
    for name, _, tile, _, _ in MATERIALS:
        if name not in names:
            continue
        base = OUT / f'T_{name}'
        alb = load_pixels(f'{base}_BaseColor.png')[..., :3]      # still sRGB-encoded values
        orm = load_pixels(f'{base}_ORM.png')
        nrm = load_pixels(f'{base}_Normal.png')[..., :3] * 2 - 1
        hgt = load_pixels(f'{base}_Height.png')[..., 0]
        lum = alb.mean(-1) * 255
        die = orm[..., 2] < .5
        dark = float((lum[die] < 30).mean()) * 100 if die.any() else 0
        hot = float((lum[die] > 240).mean()) * 100 if die.any() else 0
        metal_lum = float(lum[~die].mean()) if (~die).any() else 0
        gx = np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)
        gy = np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)
        cx = float(np.corrcoef(nrm[..., 0].ravel(), gx.ravel())[0, 1])
        cy = float(np.corrcoef(nrm[..., 1].ravel(), gy.ravel())[0, 1])
        steps_x = np.abs(np.diff(alb.mean(-1), axis=1)).mean()
        steps_y = np.abs(np.diff(alb.mean(-1), axis=0)).mean()
        seam_x = np.abs(alb[:, 0].mean(-1) - alb[:, -1].mean(-1)).mean() / steps_x
        seam_y = np.abs(alb[0].mean(-1) - alb[-1].mean(-1)).mean() / steps_y
        print(f'AUDIT {name}: nonmetal <sRGB30 {dark:.1f}% >240 {hot:.2f}% | metal area {100 * (1 - die.mean()):.1f}% '
              f'mean {metal_lum:.0f} | sRGB mean {lum.mean():.0f} sd {lum.std():.0f} | rough {orm[..., 1].mean():.2f} '
              f'sd {orm[..., 1].std():.2f} | AO {orm[..., 0].mean():.2f} | n~grad {cx:.2f} {cy:.2f} | seam {seam_x:.2f} {seam_y:.2f}')


def decal_sheet(samples):
    reset_scene(samples)
    quad_mesh('P', [(-100, -100, 0), (100, -100, 0), (100, 100, 0), (-100, 100, 0)], [(0, 0), (1, 0), (1, 1), (0, 1)], make_material('WallPanel'))
    quad_mesh('D', [(-100, -100, .3), (100, -100, .3), (100, 100, .3), (-100, 100, .3)], [(0, 0), (1, 0), (1, 1), (0, 1)],
              make_material('StationDecals', cutout=True))
    camera((0, -6, 300), (0, 0, 0), 50)
    area('Key', (-160, -120, 240), (0, 0, 0), 180, 300000, (1, .93, .84))
    area('Fill', (200, 60, 200), (0, 0, 0), 240, 90000, (.72, .82, 1))
    render(REVIEW / 'materials_decals.png', 1200, 1200)


def art_direction(samples):
    """Hostile angles: eye height, raking light, one hard source, and a long run for repetition."""
    temp = REVIEW / '_cells'
    temp.mkdir(parents=True, exist_ok=True)
    w, h = 800, 500
    def plane(name, across, along):
        t = next(m[2] for m in MATERIALS if m[0] == name)
        mat = make_material(name)
        return quad_mesh('P', [(-across, 0, 0), (across, 0, 0), (across, along, 0), (-across, along, 0)],
                         [(0, 0), (2 * across / t, 0), (2 * across / t, along / t), (0, along / t)], mat), t
    shots = [
        ('wall_rake', 'WallPanel', 300, 600, (-30, 40, 130), (20, 170, 0), 50, (-170, 120, 30)),
        ('deck_standing', 'DeckPlate', 300, 600, (0, -10, 165), (0, 170, 0), 40, (80, 150, 140)),
        ('ceiling_look', 'CeilingPanel', 300, 600, (40, 0, 150), (0, 190, 0), 40, (-120, 120, 90)),
        ('hazard_doorway', 'HazardPaint', 200, 400, (0, 0, 150), (0, 125, 0), 45, (70, 100, 120)),
        ('titanium_strip', 'TitaniumTrim', 80, 200, (10, -5, 42), (0, 60, 0), 45, (0, 60, 70)),
        ('composite_rake', 'DarkComposite', 100, 200, (-12, -10, 55), (5, 50, 0), 45, (-90, 60, 26)),
        ('runner_boots', 'FloorRunner', 100, 500, (0, -10, 150), (0, 130, 0), 45, (40, 120, 150)),
        ('wall_long_run', 'WallPanel', 900, 1200, (0, -300, 700), (0, 500, 0), 35, (0, 300, 500)),
    ]
    cols = 2
    rows = math.ceil(len(shots) / cols)
    sheet = np.full((rows * (h + 8) + 8, cols * (w + 8) + 8, 3), .03, np.float32)
    for idx, (tag, name, across, along, cam, tgt, lens, key) in enumerate(shots):
        reset_scene(samples)
        plane(name, across, along)
        camera(cam, tgt, lens)
        area('Key', key, tgt, 70, max(cam[2], 60) ** 2 * 16, (1, .93, .84))
        area('Sky', (0, tgt[1], cam[2] * 2), tgt, 300, cam[2] ** 2 * 2.5, (.7, .8, 1))
        out = temp / f'ad_{tag}.png'
        render(out, w, h)
        y, x = 8 + idx // cols * (h + 8), 8 + idx % cols * (w + 8)
        sheet[y:y + h, x:x + w] = load_pixels(out)[..., :3]
        label(sheet, tag.upper().replace('_', ' '), x + 8, y + 6, 15)
    write_png(REVIEW / 'materials_ad.png', sheet, 8, True)


# ---------------------------------------------------------------- entry
def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--samples', type=int, default=96)
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--no-sheet', action='store_true')
    ap.add_argument('--corridor-only', action='store_true')
    ap.add_argument('--audit', action='store_true')
    ap.add_argument('--no-denoise', action='store_true')
    ap.add_argument('--art-direction', action='store_true')
    args = ap.parse_args(argv)
    global DENOISE
    DENOISE = not args.no_denoise
    names = set(args.only.split(',')) if args.only else {m[0] for m in MATERIALS}
    if not args.no_build and not args.corridor_only:
        for name, recipe, tile, seed, strength in MATERIALS:
            if name in names:
                start = time.time()
                export(name, recipe(Canvas(args.size, tile, seed)), strength)
                print(f'{name}: built in {time.time() - start:.1f}s')
    if not args.no_build and not args.corridor_only and (not args.only or 'StationDecals' in names):
        export_extras()
    if args.audit:
        audit(names)
    if args.art_direction:
        art_direction(args.samples)
    if bpy is not None and not args.no_sheet:
        if args.corridor_only:
            corridor(args.samples)
        else:
            contact_sheet(args.samples, names)
            macro(args.samples, names)
            if len(names) >= len(MATERIALS):
                decal_sheet(args.samples)
                corridor(args.samples)


main()
