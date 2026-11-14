"""Grow the Physis logo: procedural botanical emblems cast as gold relief in Cycles.

Run (host):
  flatpak run org.blender.Blender -b --python Tools/build_physis_logo.py -- concepts
  flatpak run org.blender.Blender -b --python Tools/build_physis_logo.py -- final
  flatpak run org.blender.Blender -b --python Tools/build_physis_logo.py -- final --deliver

Pipeline: each emblem is grown as vector strokes (space colonization, phyllotaxis, golden
spirals), stamped into a height field, built as a real mesh and path traced in polished
metal. Letters come from Blender text objects, then get a chiselled height from their
distance field. Only the final compositing (halo, glow, alpha) happens in numpy.

Writes Art/Review/logo_*.png; with --deliver also Art/UI/T_UI_Title.png (2048x1280) and
Art/UI/T_UI_LogoMark.png (1024x1024), both straight-alpha 8-bit sRGB PNG.
"""
import math
import shutil
import struct
import sys
import zlib
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'Art/UI'
REVIEW = ROOT / 'Art/Review'
WORK = REVIEW / '_logo_work'
FONTS = Path('/run/host/fonts/urw-base35')
PHI = (1 + math.sqrt(5)) / 2
CAP, WORD_Y, RULE_Y = 172, 1012, 1152  # wordmark layout in 2048-wide canvas pixels
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))

GOLD = np.array((1.00, 0.61, 0.19))
PALE_GOLD = np.array((1.00, 0.76, 0.38))
ROSE_GOLD = np.array((1.00, 0.49, 0.20))
LEAF = np.array((0.20, 0.58, 0.13))
LEAF_DEEP = np.array((0.09, 0.42, 0.13))
LEAF_LIGHT = np.array((0.62, 0.74, 0.20))


# ---------------------------------------------------------------- image helpers

def write_png(path, rgba, seed=1):
    """Straight-alpha float RGBA (0-1, display-encoded) to dithered 8-bit PNG."""
    rng = np.random.default_rng(seed)
    noise = rng.random(rgba.shape[:2] + (1,), dtype=np.float32) - rng.random(rgba.shape[:2] + (1,), dtype=np.float32)
    data = np.clip(rgba * 255 + .5 + noise * .5, 0, 255).astype(np.uint8)
    height, width, channels = data.shape
    delta = data.copy()
    delta[:, 1:] = data[:, 1:] - data[:, :-1]
    raw = np.zeros((height, 1 + width * channels), np.uint8)
    raw[:, 0] = 1
    raw[:, 1:] = delta.reshape(height, -1)
    colour_type = 6 if channels == 4 else 2

    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload))

    head = struct.pack('>IIBBBBB', width, height, 8, colour_type, 0, 0, 0)
    blob = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', head) + chunk(b'IDAT', zlib.compress(raw.tobytes(), 6)) + chunk(b'IEND', b'')
    Path(path).write_bytes(blob)


def gauss(a, sigma):
    if sigma <= 0:
        return a.copy()
    pad = int(sigma * 3) + 2
    p = np.pad(a, pad)
    fy = np.fft.fftfreq(p.shape[0])[:, None]
    fx = np.fft.rfftfreq(p.shape[1])[None, :]
    out = np.fft.irfft2(np.fft.rfft2(p) * np.exp(-2 * math.pi ** 2 * sigma ** 2 * (fx ** 2 + fy ** 2)), p.shape)
    return out[pad:-pad, pad:-pad].astype(np.float32)


def distance(mask, window):
    """Exact Euclidean distance to the True pixels, valid up to `window` pixels."""
    far = float(window * window * 4)
    f = np.where(mask, 0, far).astype(np.float32)
    for axis in (0, 1):
        best = f.copy()
        for k in range(1, window + 1):
            k2 = float(k * k)
            best = np.minimum(best, np.roll(f, k, axis) + k2)
            best = np.minimum(best, np.roll(f, -k, axis) + k2)
        f = best
    return np.sqrt(f)


def downsample(a, k):
    if k == 1:
        return a
    h, w = a.shape[0] // k, a.shape[1] // k
    return a[:h * k, :w * k].reshape((h, k, w, k) + a.shape[2:]).mean((1, 3))


def resize(a, w, h):
    """Area-ish resample for previews."""
    k = max(1, min(a.shape[1] // w, a.shape[0] // h))
    b = downsample(a, k) if k > 1 else a
    ys = np.linspace(0, b.shape[0] - 1, h)
    xs = np.linspace(0, b.shape[1] - 1, w)
    y0 = ys.astype(int)
    x0 = xs.astype(int)
    y1 = np.minimum(y0 + 1, b.shape[0] - 1)
    x1 = np.minimum(x0 + 1, b.shape[1] - 1)
    ty = (ys - y0)[:, None, None]
    tx = (xs - x0)[None, :, None]
    top = b[y0][:, x0] * (1 - tx) + b[y0][:, x1] * tx
    low = b[y1][:, x0] * (1 - tx) + b[y1][:, x1] * tx
    return top * (1 - ty) + low * ty


def over(rgba, background):
    a = rgba[..., 3:]
    return rgba[..., :3] * a + background * (1 - a)


# ---------------------------------------------------------------- relief canvas

def rmin_wall(ra, rb):
    """Width of the chamfer that raises a lifted stroke: a slope, never a cliff."""
    return min(ra, rb) * .45


class Relief:
    """A height field with base colour, roughness and anti-aliased coverage."""

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.height = np.zeros((height, width), np.float32)
        self.cover = np.zeros((height, width), np.float32)
        self.colour = np.tile(GOLD.astype(np.float32), (height, width, 1))
        self.rough = np.full((height, width), .24, np.float32)

    def _write(self, y0, x0, h, cov, colour, rough):
        hgt = self.height[y0:y0 + h.shape[0], x0:x0 + h.shape[1]]
        cvr = self.cover[y0:y0 + h.shape[0], x0:x0 + h.shape[1]]
        win = (h >= hgt) & (cov > 0)
        self.colour[y0:y0 + h.shape[0], x0:x0 + h.shape[1]][win] = colour[win] if colour.ndim == 3 else colour
        self.rough[y0:y0 + h.shape[0], x0:x0 + h.shape[1]][win] = rough
        np.maximum(hgt, h, out=hgt)
        np.maximum(cvr, cov, out=cvr)

    def segment(self, a, b, ra, rb, colour=GOLD, rough=.24, lift=0.0, flat=.8, chisel=.7):
        pad = max(ra, rb) + 2
        x0 = max(int(min(a[0], b[0]) - pad), 0)
        y0 = max(int(min(a[1], b[1]) - pad), 0)
        x1 = min(int(max(a[0], b[0]) + pad) + 2, self.w)
        y1 = min(int(max(a[1], b[1]) + pad) + 2, self.h)
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        ex, ey = b[0] - a[0], b[1] - a[1]
        wx, wy = xx - a[0], yy - a[1]
        t = np.clip((wx * ex + wy * ey) / max(ex * ex + ey * ey, 1e-6), 0, 1)
        d = np.hypot(wx - ex * t, wy - ey * t)
        r = ra + (rb - ra) * t
        # Mostly a V-cut facet with a little round: a ridge catches light, a pillow does not.
        round_h = np.sqrt(np.maximum(r * r - d * d, 0)) * flat
        vee = np.maximum(r - d, 0) * .62
        h = round_h * (1 - chisel) + vee * chisel + lift * np.clip((r - d) / max(rmin_wall(ra, rb), .5), 0, 1)
        cov = np.clip(r - d + .5, 0, 1)
        self._write(y0, x0, h.astype(np.float32), cov.astype(np.float32), np.asarray(colour, np.float32), rough)

    def tube(self, points, radii, colour=GOLD, rough=.24, lift=0.0, chisel=.7):
        points = np.asarray(points, float)
        radii = np.maximum(np.broadcast_to(np.asarray(radii, float), (len(points),)), .55)
        for i in range(len(points) - 1):
            self.segment(points[i], points[i + 1], radii[i], radii[i + 1], colour, rough, lift, chisel=chisel)

    def leaf(self, base, angle, length, width, bend=0.0, tip=GOLD, root=GOLD, lift=0.0,
             veins=6, relief=.34, rough=.28):
        """A lanceolate leaf with a midrib groove and engraved lateral veins."""
        pad = max(length, width) + 3
        cx, cy = base[0] + math.cos(angle) * length * .5, base[1] + math.sin(angle) * length * .5
        x0, y0 = max(int(cx - pad), 0), max(int(cy - pad), 0)
        x1, y1 = min(int(cx + pad) + 1, self.w), min(int(cy + pad) + 1, self.h)
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        ux, uy = math.cos(angle), math.sin(angle)
        along = (xx - base[0]) * ux + (yy - base[1]) * uy
        across = -(xx - base[0]) * uy + (yy - base[1]) * ux
        u = along / length
        across = across - bend * length * u * u
        safe = np.clip(u, 1e-4, 1 - 1e-4)
        half = width * .5 * np.sin(math.pi * safe ** .72) ** 1.12 * (u > 0) * (u < 1)
        t = np.abs(across) / np.maximum(half, 1e-3)
        inside = t < 1
        # Folded along the midrib like a real leaf: two planes meeting at a crisp crease.
        fold = np.maximum(1 - t, 0)
        h = (fold * .78 + np.sqrt(np.maximum(1 - t * t, 0)) * .22) * half * relief * 2
        if width > 12 and veins:
            phase = (u * veins - t * .95) * 2 * math.pi
            line = np.maximum(np.cos(phase), 0) ** 16
            h -= line * min(width * .035, 1.5) * inside * np.clip(1.1 - t, 0, 1) * np.clip(u * 7, 0, 1)
        h = np.maximum(h, .2) * inside + lift * inside
        cov = np.clip(half - np.abs(across) + .5, 0, 1) * (half > 0)
        mix = np.clip(u, 0, 1)[..., None] ** 1.3
        colour = (np.asarray(root, np.float32) * (1 - mix) + np.asarray(tip, np.float32) * mix).astype(np.float32)
        self._write(y0, x0, h.astype(np.float32), cov.astype(np.float32), colour, rough)

    def text_layer(self, mask, bevel, colour_top, colour_low, rough=.2, lift=0.0, y_range=None, slope=.6):
        """Chisel a mask (0-1) into the height field using its distance field."""
        # Inscriptional V-cut: the slope runs right up to the medial axis, leaving a sharp
        # ridge down every stroke, as on a letter cut in stone and gilded.
        inside = mask > .5
        window = int(math.ceil(bevel * 1.25))
        d = distance(~inside, window) - .5
        d = gauss(np.minimum(np.maximum(d, 0) * inside, bevel).astype(np.float32), .9 * self.w / 2048)
        h = gauss((d * slope + lift * inside).astype(np.float32), .45 * self.w / 2048) * (mask > .02)
        if y_range:
            t = np.clip((np.arange(self.h) - y_range[0]) / (y_range[1] - y_range[0]), 0, 1)[:, None, None]
        else:
            t = np.linspace(0, 1, self.h)[:, None, None]
        grade = (np.asarray(colour_top) * (1 - t) + np.asarray(colour_low) * t).astype(np.float32)
        win = (h >= self.height) & (mask > 0)
        self.colour[win] = np.broadcast_to(grade, self.colour.shape)[win]
        self.rough[win] = rough
        self.height = np.maximum(self.height, h)
        self.cover = np.maximum(self.cover, mask.astype(np.float32))


class Frame:
    """Maps emblem units (y up) to canvas pixels."""

    def __init__(self, cx, cy, scale):
        self.cx, self.cy, self.s = cx, cy, scale

    def p(self, points):
        points = np.asarray(points, float)
        return np.stack((self.cx + points[..., 0] * self.s, self.cy - points[..., 1] * self.s), -1)

    def angle(self, a):
        return -a


# ---------------------------------------------------------------- growth

def colonize(trunk, attractors, step=.024, influence=.22, kill=.05, iterations=600, tropism=(0, 0), seed=1,
             persist=0.0, buds=1):
    """Runions-style space colonization. Returns node positions and parent indices."""
    rng = np.random.default_rng(seed)
    if isinstance(trunk, tuple):
        nodes = [np.asarray(p, float) for p in trunk[0]]
        parents = list(trunk[1])
    else:
        nodes = [np.asarray(p, float) for p in trunk]
        parents = [-1] + list(range(len(trunk) - 1))
    points = np.asarray(attractors, float)
    trop = np.asarray(tropism, float)
    seeded = len(nodes)
    # Only every `buds`-th skeleton node may sprout, or a limb grows a comb of side shoots.
    # Inherited heading (`persist`) makes shoots leave at an acute angle and arc away.
    barren = np.array([i < seeded and i % buds != 0 for i in range(seeded)], bool)
    for _ in range(iterations):
        if len(points) == 0:
            break
        arr = np.asarray(nodes)
        delta = points[:, None, :] - arr[None, :, :]
        dist = np.hypot(delta[..., 0], delta[..., 1])
        dist[:, :seeded][:, barren] = 1e6
        nearest = dist.argmin(1)
        near = dist[np.arange(len(points)), nearest]
        active = near < influence
        if not active.any():
            break
        pulls = {}
        for i in np.nonzero(active)[0]:
            direction = delta[i, nearest[i]] / max(near[i], 1e-6)
            pulls.setdefault(int(nearest[i]), []).append(direction)
        for index, dirs in pulls.items():
            d = np.mean(dirs, 0) + trop + rng.normal(0, .04, 2)
            if persist and parents[index] >= 0:
                heading = nodes[index] - nodes[parents[index]]
                d = d + persist * heading / max(np.hypot(*heading), 1e-6)
            norm = np.hypot(*d)
            if norm < 1e-3:
                continue
            nodes.append(nodes[index] + d / norm * step)
            parents.append(index)
        arr = np.asarray(nodes)
        dist = np.hypot(points[:, None, 0] - arr[None, :, 0], points[:, None, 1] - arr[None, :, 1]).min(1)
        points = points[dist > kill]
    return np.asarray(nodes), np.asarray(parents)


def branch_radii(parents, tip, exponent=2.3):
    """Pipe model: a parent's cross-section carries all of its children."""
    n = len(parents)
    flow = np.full(n, tip ** exponent)
    for i in range(n - 1, 0, -1):
        if parents[i] >= 0:
            flow[parents[i]] += flow[i]
    return flow ** (1 / exponent)


def smooth_nodes(nodes, parents, passes=6, weight=.5, frozen=0):
    nodes = nodes.copy()
    n = len(nodes)
    children = [[] for _ in range(n)]
    for i, p in enumerate(parents):
        if p >= 0:
            children[p].append(i)
    fixed = [i for i in range(n) if parents[i] < 0 or len(children[i]) != 1 or i < frozen]
    for _ in range(passes):
        out = nodes.copy()
        for i in range(n):
            if parents[i] >= 0 and len(children[i]) == 1:
                avg = (nodes[parents[i]] + nodes[children[i][0]]) * .5
                out[i] = nodes[i] * (1 - weight) + avg * weight
        out[fixed] = nodes[fixed]
        nodes = out
    return nodes, children


def stamp_tree(rel, frame, nodes, parents, radii, colour, rough=.24):
    px = frame.p(nodes)
    rr = radii * frame.s
    for i, p in enumerate(parents):
        if p >= 0:
            rel.segment(px[p], px[i], max(rr[p], .55), max(rr[i], .55), colour, rough)


def poisson(rng, inside, count, spacing, box=(-1, 1, -1, 1)):
    points = []
    tries = 0
    while len(points) < count and tries < count * 400:
        tries += 1
        p = np.array((rng.uniform(box[0], box[1]), rng.uniform(box[2], box[3])))
        if not inside(p):
            continue
        if points and np.hypot(*(np.asarray(points) - p).T).min() < spacing:
            continue
        points.append(p)
    return np.asarray(points)


def prune(nodes, parents, shortest=5, protect=0):
    """Drop short side spurs: they read as thorns, not twigs."""
    n = len(nodes)
    children = [[] for _ in range(n)]
    for i, p in enumerate(parents):
        if p >= 0:
            children[p].append(i)
    dead = np.zeros(n, bool)
    for i in range(n):
        if children[i]:
            continue
        run = [i]
        j = i
        while parents[j] >= 0 and len(children[parents[j]]) == 1:
            j = parents[j]
            run.append(j)
        if len(run) < shortest and parents[j] >= 0 and i >= protect:
            dead[run] = True
    keep = np.nonzero(~dead)[0]
    remap = -np.ones(n, int)
    remap[keep] = np.arange(len(keep))
    return nodes[keep], np.where(parents[keep] >= 0, remap[parents[keep]], -1)


STRAND = .0235
GROUND = -(1 - 2 / PHI ** 2)  # the golden cut of the ring's diameter: y = -.236

# Limbs and roots leave the braid as cubic curves: (leaves at y, control 1, control 2, tip).
LIMBS = (
    (-.05, (.06, .17), (.44, .27), (.80, .02)),
    (.05, (.05, .28), (.30, .28), (.66, .52)),
    (.15, (.03, .42), (.15, .50), (.38, .76)),
)
ROOTS = (
    (-.34, (.05, -.44), (.36, -.30), (.74, -.44)),
    (-.38, (.04, -.52), (.26, -.50), (.52, -.72)),
    (-.42, (.03, -.60), (.10, -.66), (.23, -.88)),
)


def bezier(p0, p1, p2, p3, count=277):  # every 4th point is the growth skeleton
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
            ys = np.linspace(y_low, y_top, 357)
            f = (ys - y_low) / (y_top - y_low)
            d = rank * .42
            # Each strand crosses at its own height, or the trunk pinches to an hourglass.
            f_s = f ** (.62, 1.0, 1.55)[rank]
            theta = (math.pi / 2 - d) * (2 * f_s - 1) * sign
            mid = (y_low + y_top) / 2
            amp = .056 + .040 * ((ys - mid) / (y_top - y_low) * 2) ** 2
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
        size = (.245 - .075 * t) * (1 if out else .52) * (1 + rng.uniform(-.07, .07))
        direction = heading - sign * side * (.42 + rng.uniform(-.05, .05))
        rel.leaf(frame.p(arc[i]), frame.angle(direction), size * frame.s, size * .37 * frame.s,
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
    strands = braid_strands(rng)

    # Skeleton the twigs grow from.
    nodes, parents = [], []

    def add_chain(points):
        for j, q in enumerate(points):
            parents.append(len(nodes) - 1 if j else -1)
            nodes.append(np.asarray(q))

    for limb, *_ in strands:
        add_chain(limb[32::8])
    leader_y = np.linspace(.15, .92, 40)
    leader = np.stack((.006 * np.sin(leader_y * 5), leader_y), -1)
    add_chain(leader)
    crown_skel = len(nodes)

    def crown(p):
        r = math.hypot(*p)
        ceiling = .85 - .10 * min(abs(p[0]) / .3, 1) * (p[1] > 0 and abs(p[0]) < .3)
        return r < ceiling and p[1] > -.10 + .34 * abs(p[0]) ** 2 * (abs(p[0]) > .3) + .12 * (abs(p[0]) < .3) and abs(p[0]) > .04

    right = poisson(rng, lambda p: p[0] > 0 and crown(p), crown_points // 2, .050)
    left = right * (-1, 1) + rng.normal(0, .016, right.shape)
    tw, tp = colonize((nodes, parents), np.concatenate((right, left)), step=.02, influence=.24, kill=.03,
                      tropism=(0, .06), seed=seed, persist=.85, buds=5)
    tw, tp = prune(tw, tp, 3, crown_skel)
    print('LOGO crown nodes', crown_skel, len(tw))
    tw, children = smooth_nodes(tw, tp, 12, frozen=crown_skel)
    radii = np.minimum(branch_radii(tp, .0052), .019)

    root_nodes, root_parents = [], []
    for _, root, *_r in strands:
        for j, q in enumerate(root[32::8]):
            root_parents.append(len(root_nodes) - 1 if j else -1)
            root_nodes.append(q)
    root_skel = len(root_nodes)

    def roots(p):
        r = math.hypot(*p)
        return r < .84 and p[1] < -.42 - .12 * abs(p[0]) ** 2

    rright = poisson(rng, lambda p: p[0] > .04 and roots(p), root_points // 2, .082)
    rleft = rright * (-1, 1) + rng.normal(0, .016, rright.shape)
    rn, rp = colonize((root_nodes, root_parents), np.concatenate((rright, rleft)), step=.02, influence=.26, kill=.042,
                      tropism=(0, -.08), seed=seed + 1, persist=1.1, buds=7)
    rn, rp = prune(rn, rp, 6, root_skel)
    print('LOGO root nodes', root_skel, len(rn))
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
        if len(children[i]) == 1 and i % 5 == 0:
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

    # Pendant sprigs under the lowest limbs, so the crown's underside weeps instead of
    # ending on a clean chord.
    for limb in (strands[0][0], strands[3][0]):
        side = np.sign(limb[-1][0])
        for f in np.linspace(.34, .93, 9):
            base = limb[int(f * (len(limb) - 1))]
            hang = rng.uniform(.10, .22) * (1.12 - abs(f - .62))
            t = np.linspace(0, 1, 16)
            sway = side * rng.uniform(.02, .07)
            sprig = base + np.stack((sway * t ** 2 + side * .02 * t, -hang * t ** .9), -1)
            rel.tube(frame.p(sprig), (.0062 - .0032 * t) * frame.s, GOLD)
            heading = -math.pi / 2 + side * rng.uniform(.05, .25)
            place(sprig[-1], heading, rng.uniform(.10, .15))
            for k, w in ((5, 1), (10, -1)):
                place(sprig[k], heading + w * rng.uniform(.6, .95), rng.uniform(.08, .115))

    # Limb tips finish in a leaf, never a bare hook.
    for limb, *_ in strands:
        d = limb[-1] - limb[-21]
        heading = math.atan2(d[1], d[0])
        place(limb[-1], heading, .17)
        for side in (-1, 1):
            place(limb[-53], heading + side * .7, .13)

    # The upright of the phi: a leader that thins to a spire above and a taproot below.
    ys = np.linspace(-1.08, 1.06, 300)
    up = np.clip(ys, 0, None) / 1.06
    down = np.clip(-ys, 0, None) / 1.08
    thick = .0345 * (1 - up) ** .8 + .0115 * up
    thick = np.where(ys < 0, .0345 * (1 - down) ** .9 + .0125 * down, thick)
    thick = thick + .030 * np.exp(-((ys + .19) / .24) ** 2)
    wave = .006 * np.sin(ys * 5)
    line = frame.p(np.stack((wave, ys), -1))
    blend = np.clip((ys - GROUND) / .3 + .5, 0, 1)
    colours = ROSE_GOLD[None] * (1 - blend[:, None]) + GOLD[None] * blend[:, None]
    for i in range(len(ys) - 1):
        rel.segment(line[i], line[i + 1], thick[i] * frame.s, thick[i + 1] * frame.s, colours[i])

    # Limbs and roots, tapering out of the braid.
    for limb, root, trunk, theta in strands:
        over_under = .5 + .5 * np.cos(theta * 3)
        lifts = (.008 + .020 * over_under) * frame.s
        for curve, start_lift, tint in ((root, lifts[0], ROSE_GOLD), (limb, lifts[-1], GOLD)):
            f = np.linspace(0, 1, len(curve))
            rr = hairline(f, STRAND, .0052) * frame.s
            q = frame.p(curve)
            for i in range(len(curve) - 1):
                rel.segment(q[i], q[i + 1], rr[i], rr[i + 1], tint, lift=start_lift * max(1 - i / 64, 0) ** 1.5)
        f = (trunk[:, 1] - trunk[0, 1]) / (trunk[-1, 1] - trunk[0, 1])
        q = frame.p(trunk)
        for i in range(len(trunk) - 1):
            tint = ROSE_GOLD * (1 - f[i]) + GOLD * f[i]
            rel.segment(q[i], q[i + 1], STRAND * frame.s, STRAND * frame.s, tint, lift=lifts[i])

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



def emblem_phyllotaxis(rel, frame, seed=5, count=377):
    """Concept B: a seedhead of 377 florets on the golden angle."""
    rng = np.random.default_rng(seed)
    for n in range(count, 0, -1):
        f = n / count
        r = math.sqrt(f) * .74
        a = n * GOLDEN_ANGLE
        p = np.array((math.cos(a), math.sin(a))) * r
        length = .05 + .36 * f ** 3.4
        width = (.036 + .098 * f ** 1.7) * (1 + rng.uniform(-.04, .04))
        lift = (1 - f) * .13 * frame.s
        green = np.clip((f - .55) / .45, 0, 1) ** 1.2
        tip = GOLD * (1 - green) + LEAF * green
        root = PALE_GOLD if f < .5 else GOLD
        start = p - np.array((math.cos(a), math.sin(a))) * length * .22
        rel.leaf(frame.p(start), frame.angle(a), length * frame.s, width * frame.s, tip=tip, root=root,
                 lift=lift, relief=.42, veins=4 if f > .55 else 0, bend=.05 * math.sin(a * 3))


def golden_spiral(turns=2.4, steps=420):
    b = math.log(PHI) / (math.pi / 2)
    end = turns * 2 * math.pi
    theta = np.linspace(0, end, steps)
    radius = np.exp(b * (theta - end))
    return np.stack((radius * np.cos(theta), radius * np.sin(theta)), -1), radius


def emblem_fern(rel, frame, seed=3):
    """Concept C: a fiddlehead on the golden spiral, unfurling into a letter P."""
    rng = np.random.default_rng(seed)
    pts, radius = golden_spiral(2.55)
    pts = np.stack((pts[:, 0], -pts[:, 1]), -1)
    # Rotate so the spiral leaves its outermost point heading straight down.
    tan = pts[-1] - pts[-2]
    turn = -math.pi / 2 - math.atan2(tan[1], tan[0])
    c, s = math.cos(turn), math.sin(turn)
    pts = pts @ np.array(((c, s), (-s, c)))
    last = pts[-1]
    stem_len = 2.1
    t = np.linspace(0, 1, 90)[1:]
    stem = np.stack((last[0] - .1 * t ** 2 * 0 + .10 * np.sin(t * 2.2) * t, last[1] - stem_len * t), -1)
    spine = np.concatenate((pts, stem))
    spine -= (spine.min(0) + spine.max(0)) * .5
    n = len(pts)
    weight = np.concatenate((.012 + .05 * radius, np.linspace(.062, .095, len(stem)) ))
    rel.tube(frame.p(spine), weight * frame.s, GOLD)
    # Pinnae along the outside of the coil, sized by the local radius of the spiral.
    length = np.cumsum(np.hypot(*(np.diff(spine, axis=0)).T))
    arc = 0.0
    i = 40
    while i < n + 34:
        tangent = spine[min(i + 1, len(spine) - 1)] - spine[i]
        heading = math.atan2(tangent[1], tangent[0])
        rad = radius[min(i, n - 1)]
        ramp = 1 if i < n else max(0, 1 - (i - n) / 34)
        for side, scale in ((-1, 1.0), (1, .42)):
            size = (.14 + .62 * rad) * scale * (.3 + .7 * ramp)
            direction = heading + side * 1.05
            d = np.array((math.cos(direction), math.sin(direction)))
            rachis = [spine[i] + d * size * k / 8 + np.array((-d[1], d[0])) * side * .10 * size * (k / 8) ** 2 for k in range(9)]
            rel.tube(frame.p(rachis), np.linspace(.014, .003, 9) * frame.s * (.5 + rad), GOLD)
            count = 7
            for k in range(1, count + 1):
                f = k / (count + .5)
                base = rachis[int(f * 8)]
                local = size * .30 * (1 - f * .72)
                for w in (-1, 1):
                    rel.leaf(frame.p(base), frame.angle(direction + w * .85), local * frame.s, local * .4 * frame.s,
                             tip=LEAF, root=GOLD, veins=0, bend=w * .06, lift=.5)
        i += max(6, int(5 + 13 * rad))
    # Roots at the foot of the stem, so the P stands on something living.
    foot = spine[-1]
    for k in range(5):
        a = -math.pi / 2 + (k - 2) * .42 + rng.uniform(-.06, .06)
        run = .22 + .14 * rng.random()
        path = [foot + np.array((math.cos(a + j * .05 * (k - 2)), math.sin(a + j * .05 * (k - 2)))) * run * j / 12 for j in range(13)]
        rel.tube(frame.p(path), np.linspace(.03, .004, 13) * frame.s, ROSE_GOLD)


def debug_growth():
    rel = Relief(600, 600)
    emblem_phi(rel, Frame(300, 300, 200))


EMBLEMS = {'phi': emblem_phi, 'phyllotaxis': emblem_phyllotaxis, 'fern': emblem_fern}


# ---------------------------------------------------------------- blender plumbing

def clear_scene():
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images, bpy.data.lights):
        for item in list(block):
            block.remove(item)
    scene.world = scene.world or bpy.data.worlds.new('World')
    return scene


def cycles(scene, width, height, samples):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 6
    scene.cycles.glossy_bounces = 4
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.cycles.filter_width = 1.1
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'OPEN_EXR'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '32'
    scene.view_settings.view_transform = 'Raw'
    scene.view_settings.look = 'None'


def camera(scene, width, height):
    data = bpy.data.cameras.new('Cam')
    data.type = 'ORTHO'
    data.ortho_scale = max(width, height)
    obj = bpy.data.objects.new('Cam', data)
    scene.collection.objects.link(obj)
    obj.location = (width / 2, height / 2, 2000)
    data.clip_end = 5000
    scene.camera = obj


def render_exr(scene, name):
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / (name + '.exr')
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = 'Non-Color'
    width, height = image.size
    pixels = np.zeros(width * height * 4, np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    return pixels.reshape(height, width, 4)[::-1]


def float_image(name, array):
    height, width = array.shape[:2]
    if array.ndim == 2:
        array = np.dstack((array, array, array))
    rgba = np.dstack((array, np.ones((height, width), np.float32)))[::-1]
    image = bpy.data.images.new(name, width, height, alpha=False, float_buffer=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(rgba.astype(np.float32).ravel())
    image.pack()
    return image


def text_mask(letters, width, height, cap_height, centre_y, tracking, font_file, kern=None, words_width=None):
    """Render each glyph from a Blender text object to a coverage mask, hand spaced."""
    scene = clear_scene()
    cycles(scene, width, height, 24)
    scene.render.film_transparent = True
    world = scene.world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0
    camera(scene, width, height)
    material = bpy.data.materials.new('Flat')
    material.use_nodes = True
    font = bpy.data.fonts.load(str(font_file))
    glyphs = []
    for ch in letters:
        curve = bpy.data.curves.new(ch, 'FONT')
        curve.body = ch
        curve.font = font
        curve.size = 100
        curve.resolution_u = 24
        obj = bpy.data.objects.new(ch, curve)
        scene.collection.objects.link(obj)
        curve.materials.append(material)
        glyphs.append(obj)
    bpy.context.view_layer.update()
    # Measure a flat-topped glyph for cap height.
    h_box = [v[1] for v in glyphs[1].bound_box]
    size = cap_height / (max(h_box) - min(h_box)) * 100
    for g in glyphs:
        g.data.size = size
    bpy.context.view_layer.update()
    extents = []
    for g in glyphs:
        xs = [v[0] for v in g.bound_box]
        extents.append((min(xs), max(xs)))
    kern = kern or [1] * (len(glyphs) - 1)
    total = sum(b - a for a, b in extents) + sum(tracking * k for k in kern)
    if words_width:
        scale_track = (words_width - sum(b - a for a, b in extents)) / sum(kern)
        tracking = scale_track
        total = words_width
    x = (width - total) / 2
    ortho_base = (height - width) / 2 if width > height else 0
    y_center = height - centre_y
    for i, g in enumerate(glyphs):
        a, b = extents[i]
        g.location = (x - a, y_center - cap_height / 2 + ortho_base * 0, 0)
        x += b - a + (tracking * kern[i] if i < len(kern) else 0)
    # Camera centred on canvas: geometry coordinates map 1:1 to pixels.
    rgba = render_exr(scene, 'text')
    return rgba[..., 3]


def env_image(size=(1024, 512)):
    """Studio built as a light map: broad key, cooler fill, thin rim, dark horizon."""
    w, h = size
    v, u = np.meshgrid((np.arange(h) + .5) / h, (np.arange(w) + .5) / w, indexing='ij')
    lat = (.5 - v) * math.pi  # row 0 is the top of the image
    lon = (.5 - u) * 2 * math.pi
    d = np.stack((np.cos(lon) * np.cos(lat), np.sin(lon) * np.cos(lat), np.sin(lat)), -1)

    def lobe(direction, width, power=6):
        direction = np.asarray(direction, float)
        direction = direction / np.linalg.norm(direction)
        c = np.clip((d * direction).sum(-1), -1, 1)
        return np.clip((c - math.cos(width)) / (1 - math.cos(width)), 0, 1) ** (1 / power)

    z = d[..., 2]
    # Mid-value overhead so flat tops read warm rather than blown out or black.
    colour = (np.clip(z, 0, 1) ** 1.2)[..., None] * np.array((.30, .23, .15))
    # Horizon goes dark: this is what gives polished metal its contrast.
    colour += (np.exp(-((z + .1) / .35) ** 2))[..., None] * np.array((.02, .02, .03))
    key = lobe((-.55, .62, .55), .62)[..., None]
    fill = lobe((.8, -.25, .45), .75)[..., None]
    rim = lobe((.15, -.95, .12), .32)[..., None]
    strip = np.exp(-((d[..., 0] + d[..., 1] * .4) / .05) ** 2)[..., None] * (z > .25)[..., None]
    colour += key * np.array((5.2, 4.5, 3.5))
    colour += fill * np.array((.95, 1.1, 1.25))
    colour += rim * np.array((4.2, 3.2, 2.0))
    colour += strip * np.array((1.6, 1.4, 1.1))
    return colour.astype(np.float32)


def relief_mesh(scene, rel, blur=.9):
    height = gauss(rel.height, blur)
    h, w = height.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    verts = np.stack((xx.ravel() + .5, (h - 1 - yy).ravel() + .5, height.ravel()), -1)
    index = (np.arange(h - 1)[:, None] * w + np.arange(w - 1)[None, :]).ravel()
    quads = np.stack((index + w, index + w + 1, index + 1, index), -1)
    mesh = bpy.data.meshes.new('Relief')
    mesh.vertices.add(len(verts))
    mesh.loops.add(quads.size)
    mesh.polygons.add(len(quads))
    mesh.vertices.foreach_set('co', verts.astype(np.float32).ravel())
    mesh.loops.foreach_set('vertex_index', quads.astype(np.int32).ravel())
    mesh.polygons.foreach_set('loop_start', (np.arange(len(quads)) * 4).astype(np.int32))
    mesh.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
    uv = mesh.uv_layers.new(name='UV')
    uvs = np.stack((verts[:, 0] / w, verts[:, 1] / h), -1)[quads.ravel()]
    uv.data.foreach_set('uv', uvs.astype(np.float32).ravel())
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new('Relief', mesh)
    scene.collection.objects.link(obj)

    material = bpy.data.materials.new('Gold')
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes['Principled BSDF']
    shader.inputs['Metallic'].default_value = 1
    base = nodes.new('ShaderNodeTexImage')
    base.image = float_image('Base', rel.colour)
    rough = nodes.new('ShaderNodeTexImage')
    rough.image = float_image('Rough', rel.rough)
    links.new(base.outputs['Color'], shader.inputs['Base Color'])
    links.new(rough.outputs['Color'], shader.inputs['Roughness'])
    mesh.materials.append(material)


def render_relief(rel, samples, name):
    scene = bpy.context.scene
    scene.render.film_transparent = False
    world = scene.world
    world.use_nodes = True
    tree = world.node_tree
    for node in list(tree.nodes):
        if node.bl_idname == 'ShaderNodeTexEnvironment':
            tree.nodes.remove(node)
    env = tree.nodes.new('ShaderNodeTexEnvironment')
    env.image = float_image('Studio', env_image())
    tree.links.new(env.outputs['Color'], tree.nodes['Background'].inputs['Color'])
    tree.nodes['Background'].inputs['Strength'].default_value = 1
    relief_mesh(scene, rel)
    return render_exr(scene, name)[..., :3]


def tone(rgb, exposure=1.0):
    """Filmic-ish shoulder, then sRGB. Highlights roll towards warm white, not clip."""
    x = np.maximum(rgb, 0) * exposure
    x = x * (1 + x / (3.6 ** 2)) / (1 + x)
    x = np.clip(x * 1.45, 0, 1)
    grey = x.mean(-1, keepdims=True)
    x = np.clip(grey + (x - grey) * 1.12, 0, 1)
    return np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055).astype(np.float32)


def finish(rgb, cover, ss, halo=1.0, glow=1.0):
    """Downsample, then build the halo stack as premultiplied layers and unpremultiply."""
    rgb = downsample(rgb, ss)
    cover = downsample(cover, ss)
    k = rgb.shape[1] / 2048
    near = np.clip(gauss(cover, 4.5 * k) * 2.0, 0, 1)
    wide = gauss(cover, 26 * k)
    aura = gauss(cover, 74 * k)
    shadow = np.clip(near * .6 + wide * .42, 0, .68) * halo
    light = np.clip(aura * .34, 0, .11) * glow
    glow_colour = np.array((1.0, .72, .34), np.float32)
    shadow_colour = np.array((.018, .013, .008), np.float32)
    # Under-to-over: wide light, dark halo, then the metal itself.
    premult = glow_colour * light[..., None]
    alpha = light.copy()
    premult = shadow_colour * shadow[..., None] + premult * (1 - shadow[..., None])
    alpha = shadow + alpha * (1 - shadow)
    premult = rgb * cover[..., None] + premult * (1 - cover[..., None])
    alpha = cover + alpha * (1 - cover)
    colour = premult / np.maximum(alpha[..., None], 1e-4)
    # Keep colour under fully transparent pixels gold, so filtering never fringes dark.
    colour = np.where(alpha[..., None] > 1e-3, colour, glow_colour)
    # Feather the outermost glow so no faint hard line shows at the texture border.
    h, w = alpha.shape
    edge = 36 * k
    fy = np.clip(np.minimum(np.arange(h), np.arange(h)[::-1]) / edge, 0, 1)[:, None]
    fx = np.clip(np.minimum(np.arange(w), np.arange(w)[::-1]) / edge, 0, 1)[None, :]
    alpha = alpha * np.maximum(cover, fy * fx)
    return np.dstack((np.clip(colour, 0, 1), np.clip(alpha, 0, 1))).astype(np.float32)


# ---------------------------------------------------------------- backgrounds

def space_background(width, height, offset=(0.15, .35)):
    image = bpy.data.images.load(str(UI / 'T_Sky_Space.png'))
    w, h = image.size
    pixels = np.zeros(w * h * 4, np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    sky = pixels.reshape(h, w, 4)[::-1, :, :3]
    cw = min(int(w * .28), w)
    ch = int(cw * height / width)
    x0, y0 = int(w * offset[0]), int(h * offset[1])
    crop = sky[y0:y0 + ch, x0:x0 + cw]
    return resize(crop, width, height).astype(np.float32)


def busy_background(width, height):
    """Deliberately hostile: bright nebula, hot stars and a cold rim of light."""
    rng = np.random.default_rng(4)
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    x /= width
    y /= height
    total = np.zeros((height, width), np.float32)
    for octave in range(5):
        scale = 2 ** octave
        for _ in range(7):
            a, b = rng.uniform(-3, 3, 2) * scale
            total += np.sin(2 * math.pi * (a * x + b * y) + rng.uniform(0, 6.3)).astype(np.float32) / scale
    total = (total - total.min()) / (total.max() - total.min())
    colour = np.stack((.10 + total ** 2 * .85, .10 + total ** 2 * .52, .22 + total ** 1.5 * .92), -1)
    stars = rng.random((height, width)) > .9985
    stars = np.clip(gauss(stars.astype(np.float32), 1.0) * 9, 0, 1)
    return np.clip(colour + stars[..., None], 0, 1).astype(np.float32)


def paste(sheet, tile, x, y):
    h, w = tile.shape[:2]
    sheet[y:y + h, x:x + w] = tile


# ---------------------------------------------------------------- layouts

def leaf_rule(rel, k, mask):
    """A swelled gilder's rule either side of a sprouting pair of leaves."""
    cx, cy = 1024 * k, RULE_Y * k
    for sign in (-1, 1):
        t = np.linspace(0, 1, 120)
        x = cx + sign * (44 * k + 400 * k * t)
        y = np.full_like(t, cy)
        rel.tube(np.stack((x, y), -1), (.7 + 3.1 * np.sin(np.clip(t * 1.25 + .02, 0, 1) * math.pi) ** .8 * (1 - t) ** .6) * k, GOLD, chisel=1)
        rel.leaf((cx, cy + 5 * k), (0 if sign > 0 else math.pi) - sign * .36, 40 * k, 13 * k, bend=sign * .10,
                 tip=LEAF, root=GOLD, veins=0, relief=.42)
    rel.leaf((cx, cy + 9 * k), -math.pi / 2, 30 * k, 11 * k, tip=LEAF, root=GOLD, veins=0, lift=2 * k, relief=.42)


def build_title(emblem, width, height, ss, samples, name, font, wide=1.0, wordmark=True, emblem_box=None,
                refine=None):
    """Compose emblem above wordmark on a canvas of width x height (output px)."""
    W, H = width * ss, height * ss
    k = W / 2048
    box = emblem_box or {'phi': (1024, 442, 304), 'phyllotaxis': (1024, 430, 410),
                         'fern': (1024, 432, 196)}[emblem]
    mask = None
    if wordmark:
        mask = text_mask('PHYSIS', W, H, CAP * k, WORD_Y * k, 74 * k, font, kern=[1.0, .92, .94, 1.0, 1.0],
                         words_width=1120 * k)
    scene = clear_scene()
    cycles(scene, W, H, samples)
    camera(scene, W, H)
    rel = Relief(W, H)
    EMBLEMS[emblem](rel, Frame(box[0] * k, box[1] * k, box[2] * k))
    if refine:
        refine(rel, k, mask)
    if mask is not None:
        rel.text_layer(mask, 15 * k, np.array((1.0, .70, .30)), GOLD, y_range=((WORD_Y - CAP / 2) * k, (WORD_Y + CAP / 2) * k))
    rgb = render_relief(rel, samples, name)
    return tone(rgb), rel.cover


def build_mark(emblem, size, ss, samples, name):
    S = size * ss
    scene = clear_scene()
    cycles(scene, S, S, samples)
    camera(scene, S, S)
    rel = Relief(S, S)
    scale = {'phi': .345, 'phyllotaxis': .455, 'fern': .225}[emblem] * S
    EMBLEMS[emblem](rel, Frame(S / 2, S / 2, scale))
    return tone(render_relief(rel, samples, name)), rel.cover


# ---------------------------------------------------------------- jobs

def concepts():
    w, h = 1024, 640
    backgrounds = space_background(w, h)
    columns = []
    for emblem, font in (('phi', 'P052-Roman.otf'), ('phyllotaxis', 'C059-Roman.otf'), ('fern', 'P052-Bold.otf')):
        rgb, cover = build_title(emblem, w, h, 2, 48, 'concept_' + emblem, FONTS / font)
        rgba = finish(rgb, cover, 2)
        columns.append((emblem, rgba))
    sheet = np.full((h * 2 + 200, w * 3, 3), .05, np.float32)
    for i, (emblem, rgba) in enumerate(columns):
        paste(sheet, over(rgba, np.full(rgba.shape[:2] + (3,), .025, np.float32)), i * w, 0)
        paste(sheet, over(rgba, backgrounds), i * w, h)
        small = resize(rgba, 256, 160)
        paste(sheet, over(small, np.full(small.shape[:2] + (3,), .04, np.float32)), i * w + 20, h * 2 + 20)
        tiny = resize(rgba, 128, 80)
        paste(sheet, over(tiny, resize(backgrounds, 128, 80)), i * w + 300, h * 2 + 20)
    write_png(REVIEW / 'logo_concepts.png', sheet)


def final(deliver=False, ss=2, samples=128, tag='final'):
    font = FONTS / 'P052-Roman.otf'
    rgb, cover = build_title('phi', 2048, 1280, ss, samples, 'title', font, refine=leaf_rule)
    title = finish(rgb, cover, ss)
    rgb, cover = build_mark('phi', 1024, ss, samples, 'mark')
    mark = finish(rgb, cover, ss, glow=.9)
    write_png(REVIEW / f'logo_{tag}_title.png', over(title, np.full(title.shape[:2] + (3,), .02, np.float32)))
    review_sheet(title, mark, REVIEW / f'logo_{tag}.png')
    write_png(REVIEW / f'logo_{tag}_T.png', title)
    write_png(REVIEW / f'logo_{tag}_M.png', mark)
    if deliver:
        write_png(UI / 'T_UI_Title.png', title)
        write_png(UI / 'T_UI_LogoMark.png', mark)


def review_sheet(title, mark, path):
    w, h = 960, 600
    t = resize(title, w, h)
    sky = space_background(w, h)
    busy = busy_background(w, h)
    sheet = np.full((h * 2 + 300, w * 2, 3), .06, np.float32)
    paste(sheet, over(t, np.full((h, w, 3), .02, np.float32)), 0, 0)
    paste(sheet, over(t, sky), w, 0)
    paste(sheet, over(t, busy), 0, h)
    paste(sheet, over(t, np.full((h, w, 3), np.array((.62, .68, .74)), np.float32)), w, h)
    x = 20
    for size in (256, 180, 96):
        m = resize(mark, size, size)
        paste(sheet, over(m, resize(busy, size, size)), x, h * 2 + 20)
        x += size + 20
    t2 = resize(title, 384, 240)
    paste(sheet, over(t2, resize(sky, 384, 240)), x, h * 2 + 20)
    x += 404
    t3 = resize(title, 192, 120)
    paste(sheet, over(t3, resize(busy, 192, 120)), x, h * 2 + 20)
    write_png(path, sheet)


def load_rgba(path):
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = 'Non-Color'
    w, h = image.size
    pixels = np.zeros(w * h * 4, np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    return pixels.reshape(h, w, 4)[::-1]


def crops(title_path, mark_path, out):
    """Art-director close-ups: 1:1 and 2x crops of the delivered texture, plus icon sizes."""
    title = load_rgba(title_path)
    mark = load_rgba(mark_path)
    bg = np.full(title.shape[:2] + (3,), .02, np.float32)
    flat = over(title, bg)
    H, W = flat.shape[:2]
    sx, sy = W / 2048, H / 1280
    windows = [(760, 30, 528, 330), (880, 330, 288, 180), (760, 560, 528, 330), (360, 900, 660, 280)]
    sheet = np.full((1100, 2112, 3), .06, np.float32)

    def zoom(win, scale):
        x, y, w, h = win
        c = flat[int(y * sy):int((y + h) * sy), int(x * sx):int((x + w) * sx)]
        return np.repeat(np.repeat(c, scale, 0), scale, 1)

    paste(sheet, zoom(windows[0], 2)[:660, :1056], 0, 0)
    paste(sheet, zoom(windows[1], 2)[:360, :576], 1060, 0)
    paste(sheet, zoom(windows[3], 1)[:280, :660], 1060, 380)
    paste(sheet, zoom(windows[2], 1)[:330, :528], 0, 670)
    sky = space_background(2048, 1280)
    x = 540
    for size in (128, 96, 64, 48, 32):
        m = resize(mark, size, size)
        paste(sheet, over(m, resize(sky, size, size)), x, 680)
        x += size + 16
    x = 540
    for tw, th in ((320, 200), (192, 120)):
        t = resize(title, tw, th)
        paste(sheet, over(t, resize(sky, tw, th)), x, 830)
        x += tw + 16
    write_png(out, sheet)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    REVIEW.mkdir(parents=True, exist_ok=True)
    job = args[0] if args else 'concepts'
    opts = dict(a[2:].split('=', 1) for a in args if a.startswith('--') and '=' in a)
    if job == 'concepts':
        concepts()
    elif job == 'final':
        samples = int(opts.get('samples', 128 if '--hq' in args or '--deliver' in args else 48))
        final('--deliver' in args, int(opts.get('ss', 2)), samples, opts.get('tag', 'final'))
    elif job == 'debug':
        debug_growth()
    elif job == 'crops':
        tag = opts.get('tag', '')
        if tag:
            crops(REVIEW / f'logo_{tag}_T.png', REVIEW / f'logo_{tag}_M.png', REVIEW / f'logo_{tag}_crops.png')
        else:
            crops(UI / 'T_UI_Title.png', UI / 'T_UI_LogoMark.png', REVIEW / 'logo_review_crops.png')
    shutil.rmtree(WORK, ignore_errors=True)


main()
