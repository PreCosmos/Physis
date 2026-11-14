"""Districts of the Conclave (level 3): the Terraces, the Reservoir, the Foundry, the Spine Pylons, the
Lightform Spire, the Spindle Docks, the gates, the current, and every quest item, augmentation and pickup.

Pure numpy (toolkit, palette): Tools/build_physis_conclave.py builds these in Blender and check.py checks
them offline. Metres, Unreal axes (x forward, y right, z up); a mesh with a front faces +x. Names, sizes
and pivots are the contract in Tools/conclave/README.md; CONTRACT at the end repeats them for check.py.

Realism comes from three things: the parts real things are made of (plates with seams, ribs, rivets,
flanges, bevelled edges, frames, sills), vertex colour that darkens toward the ground and gathers grime
(weather()), and the slot, which picks the physically based surface. Every colour is a palette colour or a
shade of one that still passes palette.allowed(): tone() and weather() stop a shaded gold, red or blue at
the darkest step that stays in its family, so nothing brown, orange or navy can appear.
"""
import math

import numpy as np

from palette import (ASH, BLACK, BLUE, BLUE_ICE, BLUE_PALE, CHARCOAL, GOLD, GOLD_DEEP, GOLD_GRASS, GOLD_PALE,
                     GOLD_STRAW, IVORY, LIGHT_BLUE, LIGHT_GOLD, LIGHT_RED, LIGHT_WARM, LIGHT_WHITE, RED, RED_BRIGHT,
                     RED_DEEP, SLATE, WHITE, WHITE_COOL, WHITE_PURE, allowed)
from toolkit import (Part, arch, bevel_box, bezier, blob, box, cylinder, frame, gable_roof, hexa, lathe, noise2, prism,
                     ribbon, window_frame)

# Slot names (Tools/conclave/README.md, Material slots).
STONE, DARK, PAINT, METAL, GILT, REDS, TILE, CLOTH, LEAF, GLOW, GLASS, WATER = (
    'CN_White', 'CN_Black', 'CN_Lacquer', 'CN_Metal', 'CN_Gold', 'CN_Red', 'CN_Blue', 'CN_Cloth', 'CN_Leaf', 'CN_Glow',
    'CN_Glass', 'CN_Water')


# ---------------------------------------------------------------- colour that stays in the palette

def tone(colour, k):
    """colour with its RGB scaled by k. Brightening stops at albedo 0.9 (nothing real is whiter), and a
    darkened gold, red or blue stops at the darkest step that still passes allowed()."""
    rgb = np.asarray(colour[:3], np.float64)
    k = float(k)
    if k > 1.0:
        k = min(k, max(1.0, .9 / max(rgb.max(), 1e-6)))
    if allowed(rgb * k):
        return (*(rgb * k), 1.0)
    lo, hi = 0.0, 1.0  # parameter from k (refused) toward 1 (the original, allowed)
    for _ in range(12):
        mid = (lo + hi) / 2
        if allowed(rgb * (k + (1 - k) * mid)):
            hi = mid
        else:
            lo = mid
    out = rgb * (k + (1 - k) * hi)
    return (*out, 1.0) if allowed(out) else (*rgb, 1.0)


def vary(colour, rng, spread=.08):
    """One element's colour, a little lighter or darker than its neighbours so repeats do not look stamped."""
    return tone(colour, rng.uniform(1 - spread, 1 + spread))


def mix(a, b, t):
    """A blend of two palette colours (white-blue light, warm-cool stone), kept in the palette."""
    rgb = np.asarray(a[:3], np.float64) * (1 - t) + np.asarray(b[:3], np.float64) * t
    return (*rgb, 1.0) if allowed(rgb) else (tuple(a[:3]) + (1.0,) if t < .5 else tuple(b[:3]) + (1.0,))


# How strongly weather() marks each surface: gold and glossy paint shed grime, glass and light take none.
WEAR = {'CN_Gold': .3, 'CN_Lacquer': .65, 'CN_Leaf': .55, 'CN_Cloth': .6, 'CN_Glass': 0., 'CN_Glow': 0., 'CN_Water': 0.}


def weather(part, seed=0, ground=None, reach=1.6, depth=.42, grime=.2, streak=.12, cell=1.4):
    """Darkens vertex colour toward the ground (ambient occlusion and splash) and with blotches and
    rain streaks of grime from world-space noise, per slot by WEAR. Returns the part, so builders end with it."""
    if not part.v:
        return part
    v = np.asarray(part.v, np.float64)
    c = np.asarray(part.c, np.float64)
    slot_of = np.zeros(len(v), np.int64)
    for f, m in zip(part.f, part.m):
        slot_of[f] = m
    strength = np.array([WEAR.get(s, 1.0) for s in part.slots])[slot_of]
    z0 = v[:, 2].min() if ground is None else ground
    t = np.clip((v[:, 2] - z0) / reach, 0, 1)
    ao = 1 - depth * (1 - t) ** 2
    blot = np.maximum(0, noise2((v[:, 0] + .37 * v[:, 2]) / cell, (v[:, 1] - .53 * v[:, 2]) / cell, seed + 11))
    rain = np.maximum(0, noise2((v[:, 0] + v[:, 1]) * 2.3, v[:, 2] * .3, seed + 29))
    m = ao * (1 - grime * blot) * (1 - streak * rain)
    m = 1 - strength * (1 - m)
    for i in np.nonzero(strength > 0)[0]:
        part.c[i] = list(tone(c[i], m[i]))
    return part


# ---------------------------------------------------------------- placing parts

def rot_z(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1.]])


def rot_y(deg):
    """Pitch: +deg tips local +x up toward +z."""
    a = math.radians(deg)
    return np.array([[math.cos(a), 0, -math.sin(a)], [0, 1., 0], [math.sin(a), 0, math.cos(a)]])


def rot_x(deg):
    """Roll: +deg turns local +y toward +z."""
    a = math.radians(deg)
    return np.array([[1., 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])


def merge(part, sub, R=None, t=(0, 0, 0)):
    """Appends a sub-assembly modelled in its own frame, turned by R (a rotation, so fronts stay outside)
    and moved by t."""
    v = np.asarray(sub.v, np.float64)
    if R is not None:
        v = v @ np.asarray(R, np.float64).T
    v = v + np.asarray(t, np.float64)
    base = len(part.v)
    part.v.extend(v.tolist())
    part.c.extend(sub.c)
    for f, m, s in zip(sub.f, sub.m, sub.s):
        part.f.append([base + i for i in f])
        part.m.append(part.slots.index(sub.slots[m]))
        part.s.append(s)
    return part


def scratch(part):
    return Part(part.name, part.slots)


def tube(part, points, radii, colour, slot=0, sides=8, cap=True, smooth=True, shade=None, twist=0.):
    """toolkit.tube with the same arguments and winding, but each cross-section is carried along the path from the
    one before (parallel transport). toolkit.frame() orients every ring from the world's up, so a ring jumps 90
    degrees where a path's tangent passes near vertical and 180 where its sideways direction reverses: an upright
    wheel, hoop, claw or sigil ring was pinched at those points. A closed path (last point on the first) uses
    wrapped tangents, so its seam matches."""
    pts = np.asarray(points, np.float64)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (len(pts),))
    count = len(pts)
    closed = count > 3 and np.allclose(pts[0], pts[-1])
    dirs = []
    for i in range(count):
        if closed and i in (0, count - 1):
            d = pts[1] - pts[-2]
        else:
            d = pts[min(i + 1, count - 1)] - pts[max(i - 1, 0)]
        dirs.append(d / (np.linalg.norm(d) + 1e-12))
    a, _ = frame(dirs[0])
    rings = []
    for i, p in enumerate(pts):
        d = dirs[i]
        if i:
            k = np.cross(dirs[i - 1], d)  # the smallest rotation taking the last tangent onto this one
            s, c = np.linalg.norm(k), float(np.dot(dirs[i - 1], d))
            if s > 1e-9:
                k /= s
                a = a * c + np.cross(k, a) * s + k * np.dot(k, a) * (1 - c)
        a = a - d * np.dot(a, d)
        a /= np.linalg.norm(a) + 1e-12
        b = np.cross(d, a)
        ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + twist * i
        rings.append(p + radii[i] * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b))
    faces = []
    for i in range(count - 1):
        for j in range(sides):
            k = (j + 1) % sides
            faces.append([i * sides + j, i * sides + k, (i + 1) * sides + k, (i + 1) * sides + j])
    if cap:
        faces.append(list(range(sides))[::-1])
        faces.append([(count - 1) * sides + j for j in range(sides)])
    return part.add(np.concatenate(rings), faces, colour, slot, smooth, shade)


def torus(part, c, big, small, colour, slot=0, sides=48, ring=10, axis='z', arc=2 * math.pi, smooth=True, start=0.0):
    """toolkit.torus (same arguments), built with the tube above so an upright ring ('x' facing x, 'y' facing y)
    keeps its round section all the way round."""
    full = arc >= 2 * math.pi - 1e-6
    n = sides + (0 if full else 1)
    t = start + np.linspace(0, arc, n, endpoint=not full)
    u, v = np.cos(t) * big, np.sin(t) * big
    zero = np.zeros(n)
    path = np.stack({'x': (zero, u, v), 'y': (u, zero, v)}.get(axis, (u, v, zero)), 1) + np.asarray(c, np.float64)
    if full:
        path = np.concatenate([path, path[:1]])
    return tube(part, path, small, colour, slot, ring, cap=not full, smooth=smooth)


def strut(part, a, b, w, h, colour, slot, up=(0, 0, 1)):
    """A rectangular member from a to b, w wide and h deep: braces, girts, rails, rafters."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    f = b - a
    f /= np.linalg.norm(f)
    u = np.asarray(up, np.float64)
    if abs(np.dot(u, f)) > .95:
        u = np.array([1., 0, 0]) if abs(f[0]) < .9 else np.array([0, 1., 0])
    s = np.cross(u, f)
    s /= np.linalg.norm(s)
    u = np.cross(f, s)
    pts = [(a if xb == 0 else b) + s * (w / 2 if yb else -w / 2) + u * (h / 2 if zb else -h / 2)
           for zb in (0, 1) for yb in (0, 1) for xb in (0, 1)]
    return hexa(part, pts, colour, slot)


def ibeam(part, a, b, depth, width, colour, slot, up=(0, 0, 1)):
    """A rolled steel I-section from a to b: two flanges and a web, depth measured along up."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    f = (b - a) / np.linalg.norm(b - a)
    u = np.asarray(up, np.float64)
    u = u - f * np.dot(u, f)
    u /= np.linalg.norm(u)
    tf, tw = max(.012, depth * .09), max(.01, width * .12)
    for s in (-1, 1):
        off = u * s * (depth / 2 - tf / 2)
        strut(part, a + off, b + off, width, tf, colour, slot, u)
    strut(part, a, b, tw, depth - 2 * tf, colour, slot, u)


def angle_iron(part, a, b, size, colour, slot, out=(1, 1, 0)):
    """An L-section (the legs of lattice masts), its two flanges opening along out's two directions."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    f = (b - a) / np.linalg.norm(b - a)
    o = np.asarray(out, np.float64)
    e1 = np.array([o[0], 0, 0]) - f * f[0] * o[0]
    e2 = np.array([0, o[1], 0]) - f * f[1] * o[1]
    t = size * .14
    for e in (e1, e2):
        e /= np.linalg.norm(e)
        off = e * size / 2
        strut(part, a + off, b + off, size, t, colour, slot, np.cross(f, e))


def rivets(part, points, normal, r, colour, slot):
    """Domed rivet or bolt heads seated on a surface: six-sided frustums with no hidden underside."""
    pts = np.atleast_2d(np.asarray(points, np.float64))
    nrm = np.broadcast_to(np.asarray(normal, np.float64), pts.shape)
    verts, faces = [], []
    ang = np.linspace(0, 2 * math.pi, 6, endpoint=False)
    for p, n in zip(pts, nrm):
        n = n / np.linalg.norm(n)
        a, b = frame(n)
        ring = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
        k = len(verts)
        verts.extend(p - n * r * .2 + r * ring)
        verts.extend(p + n * r * .5 + r * .6 * ring)
        faces += [[k + j, k + (j + 1) % 6, k + 6 + (j + 1) % 6, k + 6 + j] for j in range(6)]
        faces.append([k + 6 + j for j in range(6)])
    return part.add(verts, faces, colour, slot, False)


def row(a, b, n):
    """n points evenly from a to b (rivet lines, posts, rungs)."""
    return [np.asarray(a, np.float64) + (np.asarray(b, np.float64) - np.asarray(a, np.float64)) * (i / max(n - 1, 1))
            for i in range(n)]


def polygon(part, pts, colour, slot, toward=None, smooth=False):
    """One flat polygon, wound so its front faces the direction toward (a vector)."""
    pts = np.asarray(pts, np.float64)
    order = list(range(len(pts)))
    if toward is not None:
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        if np.dot(n, toward) < 0:
            order = order[::-1]
    return part.add(pts, [order], colour, slot, smooth)


def ngon(c, r, sides, z=0.0, start=0.0):
    """Corners of a regular polygon around c at height z (start in degrees from +x)."""
    a = np.radians(start) + np.linspace(0, 2 * math.pi, sides, endpoint=False)
    return np.stack([c[0] + np.cos(a) * r, c[1] + np.sin(a) * r, np.full(sides, z)], 1)


def annulus(part, c, r_in, r_out, colour, slot, sides=32, z=0.0, start=0.0, up=True):
    """A flat ring (inlays, rims), facing +z (or -z)."""
    inner, outer = ngon(c, r_in, sides, z, start), ngon(c, r_out, sides, z, start)
    faces = [[j, (j + 1) % sides, sides + (j + 1) % sides, sides + j][::-1] for j in range(sides)]
    if not up:
        faces = [f[::-1] for f in faces]
    return part.add(np.concatenate([inner, outer]), faces, colour, slot, False)


def disc(part, c, r, colour, slot, sides=24, z=0.0, start=0.0, up=True):
    pts = ngon(c, r, sides, z, start)
    return part.add(pts, [list(range(sides)) if up else list(range(sides))[::-1]], colour, slot, False)


def loft(part, rings, colour, slot, inside, closed=True, smooth=True):
    """Skins consecutive rings of points (hulls, shells, blades). inside(point) gives a point within the
    solid near that point, and every face is turned to face away from it."""
    rings = [np.asarray(r, np.float64) for r in rings]
    n = len(rings[0])
    verts = np.concatenate(rings)
    faces = []
    span = n if closed else n - 1
    for i in range(len(rings) - 1):
        for j in range(span):
            k = (j + 1) % n
            f = [i * n + j, i * n + k, (i + 1) * n + k, (i + 1) * n + j]
            p = verts[f]
            normal = np.cross(p[1] - p[0], p[3] - p[0]) + np.cross(p[2] - p[1], p[0] - p[1])
            centre = p.mean(0)
            if np.dot(normal, centre - np.asarray(inside(centre), np.float64)) < 0:
                f = f[::-1]
            faces.append(f)
    cols = colour(verts) if callable(colour) else colour
    return part.add(verts, faces, cols, slot, smooth)


def stripes(part, a, b, w, h, count, colours, slots, up=(0, 0, 1)):
    """A bar painted in alternating bands (hazard red and white on legs, rails, booms), as strut(): w across the bar
    in the face, h along up, so a band laid on a face takes up = the face's normal and h = its thickness."""
    pts = row(a, b, count + 1)
    for i in range(count):
        strut(part, pts[i], pts[i + 1], w, h, colours[i % len(colours)], slots[i % len(slots)], up)


def lamp(part, c, colour=LIGHT_WARM, r=.12, cage=SLATE):
    """A bulkhead lamp: a glowing lens in a steel cage."""
    blob(part, c, r, colour, GLOW, 1, 0.0, 3)
    torus(part, c, r * 1.05, r * .12, cage, METAL, 12, 4, 'z')
    torus(part, c, r * 1.05, r * .12, cage, METAL, 12, 4, 'x')


# ---------------------------------------------------------------- the Terraces

def blade(part, base, yaw, height, lean, width, colour, slot=LEAF, bend=.55):
    """One leaf or stalk: a tapered, two-sided ribbon arching away from its base toward yaw."""
    d = np.array([math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0.])
    b = np.asarray(base, np.float64)
    pts = [b, b + d * lean * bend * .5 + (0, 0, height * .55), b + d * lean + (0, 0, height)]
    return ribbon(part, pts, np.array([width * .6, width, width * .15]), colour, slot, normal=d)


def crop(part, rng, x, y, z, kind):
    """One plant of a hydroponic row. wheat: golden stalks and ears; chard: a rosette of red leaves with
    bright ribs; bloom: gold-green bean leaves (gold, the palette's grass colour) with white flowers."""
    if kind == 'wheat':
        for s in range(rng.integers(4, 7)):
            yaw, h = rng.uniform(0, 360), rng.uniform(.3, .4)
            lean = rng.uniform(.02, .07)
            blade(part, (x, y, z), yaw, h, lean, .006, vary(GOLD_STRAW, rng, .1))
            d = np.array([math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0.])
            top = np.array([x, y, z]) + d * lean + (0, 0, h)
            ribbon(part, [top - d * .004, top + d * .012 + (0, 0, .07)], np.array([.012, .006]), vary(GOLD_STRAW, rng, .12), LEAF, d)
        for _ in range(2):
            blade(part, (x, y, z), rng.uniform(0, 360), rng.uniform(.14, .22), rng.uniform(.08, .14), .01, vary(GOLD_GRASS, rng, .08))
    elif kind == 'chard':
        for s in range(rng.integers(6, 9)):
            yaw = s * 47 + rng.uniform(-12, 12)
            h, lean = rng.uniform(.18, .3), rng.uniform(.08, .16)
            blade(part, (x, y, z), yaw, h, lean, rng.uniform(.035, .05), vary(RED_DEEP, rng, .1))
            blade(part, (x, y, z + .004), yaw, h * .8, lean * .8, .006, vary(RED_BRIGHT, rng, .08))
    else:
        for s in range(rng.integers(5, 7)):
            yaw = s * 61 + rng.uniform(-15, 15)
            blade(part, (x, y, z), yaw, rng.uniform(.2, .32), rng.uniform(.1, .16), .028, vary(GOLD_GRASS, rng, .1))
        for _ in range(rng.integers(2, 4)):
            c = np.array([x, y, z]) + (rng.uniform(-.06, .06), rng.uniform(-.06, .06), rng.uniform(.24, .34))
            # Each flower cluster on its own stalk from the plant's heart, so no flower hangs in the air.
            off = c[:2] - (x, y)
            blade(part, (x, y, z + .1), math.degrees(math.atan2(off[1], off[0])), c[2] - z - .1, float(np.hypot(*off)), .0025,
                  GOLD_GRASS, bend=.4)
            for q in range(3):
                d = q * 120 + rng.uniform(0, 40)
                blade(part, c, d, .02, .025, .012, WHITE_PURE, bend=.3)


def hydro_bed(k=0):
    """A raised hydroponic bed on the Terraces: a white painted steel trough on legs with stiffening ribs
    and a rolled lip, black growing medium, three rows of one crop and a drip line with a gold valve.
    3 x 10 x 1; variants 1 and 2 grow red chard and white-flowering beans instead of wheat."""
    rng = np.random.default_rng(301 + k)
    p = Part('SM_CN_HydroBed' + ('' if k == 0 else str(k)), (PAINT, METAL, DARK, GILT, LEAF))
    hx, hy = 1.5, 5.0
    for x in (-1.3, 1.3):
        for y in np.linspace(-4.6, 4.6, 5):
            bevel_box(p, (x, y, .11), (.04, .04, .11), SLATE, METAL, .008)
            bevel_box(p, (x, y, .006), (.07, .07, .006), CHARCOAL, METAL, .003)
    bevel_box(p, (0, 0, .245), (hx - .02, hy - .02, .025), vary(WHITE_PURE, rng, .05), PAINT, .01)
    for s in (-1, 1):
        bevel_box(p, (s * (hx - .04), 0, .465), (.04, hy, .205), vary(WHITE_PURE, rng, .04), PAINT, .012)
        bevel_box(p, (0, s * (hy - .04), .465), (hx - .08, .04, .205), vary(WHITE_PURE, rng, .04), PAINT, .012)
    # The rolled lip runs round all four walls with rounded corners: a lip on the long sides alone left its end caps
    # in the plane of the end walls' faces, where they flickered.
    lx, ly, bend = hx - .03, hy - .03, .06
    lip = []
    for cx, cy, a0 in ((lx, ly, 0.0), (-lx, ly, 90.0), (-lx, -ly, 180.0), (lx, -ly, 270.0)):
        for a in np.radians(a0 + np.array([0.0, 30.0, 60.0, 90.0])):
            lip.append((cx - bend * math.copysign(1, cx) + bend * math.cos(a), cy - bend * math.copysign(1, cy) + bend * math.sin(a), .675))
    tube(p, lip + [lip[0]], .03, WHITE_PURE, PAINT, 6, cap=False)
    for s in (-1, 1):
        for y in np.linspace(-hy + .6, hy - .6, 8):
            bevel_box(p, (s * (hx + .005), y, .46), (.02, .03, .19), vary(WHITE_PURE, rng, .05), PAINT, .006)
            rivets(p, [(s * (hx + .025), y, z) for z in (.32, .6)], (s, 0, 0), .009, ASH, METAL)
    # The medium is mounded around each plant, so its surface is a height field, not a flat slab.
    nx, ny = 9, 40
    xs, ys = np.linspace(-hx + .08, hx - .08, nx), np.linspace(-hy + .08, hy - .08, ny)
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    gz = .6 + .018 * noise2(gx * 3.1, gy * 3.1, 17 + k) - .012 * np.cos(gx * 2 * math.pi / .95) ** 2
    verts = np.stack([gx, gy, gz], -1).reshape(-1, 3)
    faces = [[i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1] for i in range(nx - 1) for j in range(ny - 1)]
    soil = [tone(CHARCOAL, .7 + .5 * (noise2(a * 5, b * 5, 3) * .5 + .5)) for a, b, _ in verts]
    p.add(verts, faces, soil, DARK, True)
    kind = ('wheat', 'chard', 'bloom')[k % 3]
    # Wheat is sown closer, four rows with a plant every 32 cm: at three rows and 38 cm the bed read as black medium
    # with a few straws. The leafy crops fill their rows already.
    rows, spacing = ((-1.05, -.35, .35, 1.05), .32) if kind == 'wheat' else ((-.95, 0, .95), .38)
    for x in rows:
        for y in np.arange(-hy + .35, hy - .3, spacing):
            crop(p, rng, x + rng.uniform(-.05, .05), y + rng.uniform(-.06, .06), .6, kind)
        tube(p, [(x + .12, -hy + .1, .615), (x + .12, hy - .1, .615)], .009, BLACK, DARK, 5)
    tube(p, [(-1.2, hy - .12, .64), (1.2, hy - .12, .64)], .022, SLATE, METAL, 8)
    cylinder(p, (1.0, hy - .12, .61), .04, .06, GOLD, GILT, 10)
    c = np.array([1.0, hy - .12, .7])
    tube(p, [c - (0, 0, .032), c + (0, 0, .004)], .008, GOLD_PALE, GILT, 6)  # the stem the handwheel turns on
    for a in (0.0, math.pi / 2):
        d = np.array([math.cos(a), math.sin(a), 0.0]) * .05
        tube(p, [c - d, c + d], .005, GOLD, GILT, 4)
    torus(p, c, .05, .008, GOLD, GILT, 12, 4, 'z')
    return weather(p, 301 + k, reach=.5, depth=.35)


def sluice():
    """A sluice gate of the irrigation channel: two stone piers with steel guide channels, a riveted gate
    leaf, a steel header with a bevel gearbox, and the gold handwheel at the front (+x). 1 x 3 x 3."""
    rng = np.random.default_rng(311)
    p = Part('SM_CN_Sluice', (STONE, METAL, GILT, DARK))
    for s in (-1, 1):
        for z0, z1 in ((0, .55), (.56, 1.12), (1.13, 1.68), (1.69, 2.2)):
            bevel_box(p, (0, s * 1.26, (z0 + z1) / 2), (.45, .23, (z1 - z0) / 2), vary(WHITE, rng, .06), STONE, .03)
        # Mortar 2 cm behind the 1 cm joints: they were open slits through the pier (one at eye height).
        bevel_box(p, (0, s * 1.26, 1.1), (.43, .21, 1.09), tone(ASH, 1.4), STONE, .01)
        bevel_box(p, (0, s * 1.26, 2.27), (.47, .25, .07), vary(IVORY, rng, .05), STONE, .025)
        for x in (-.08, .08):
            bevel_box(p, (x, s * 1.0, 1.18), (.012, .045, 1.06), CHARCOAL, METAL, .004)
        bevel_box(p, (0, s * 1.035, 1.18), (.09, .012, 1.06), CHARCOAL, METAL, .004)
    bevel_box(p, (0, 0, .06), (.45, 1.03, .06), vary(WHITE, rng, .05), STONE, .02)
    bevel_box(p, (0, 0, .85), (.04, .98, .72), SLATE, METAL, .012)
    for z in (.35, .85, 1.35):
        bevel_box(p, (.06, 0, z), (.025, .94, .03), CHARCOAL, METAL, .006)
        rivets(p, [(.088, y, z) for y in np.linspace(-.85, .85, 9)], (1, 0, 0), .012, ASH, METAL)
    tube(p, [(0, 0, 1.57), (0, 0, 2.62)], .035, ASH, METAL, 8)
    ibeam(p, (0, -1.45, 2.42), (0, 1.45, 2.42), .2, .16, CHARCOAL, METAL)
    bevel_box(p, (.05, 0, 2.66), (.17, .19, .12), SLATE, METAL, .02)
    rivets(p, [(.225, y, z) for y in (-.14, .14) for z in (2.58, 2.74)], (1, 0, 0), .014, ASH, METAL)
    tube(p, [(0, 0, 2.78), (0, 0, 2.98)], .05, CHARCOAL, METAL, 10)
    cylinder(p, (0, 0, 2.97), .06, .03, SLATE, METAL, 10)
    tube(p, [(.22, 0, 2.66), (.42, 0, 2.66)], .03, ASH, METAL, 8)
    c = np.array([.43, 0, 2.66])
    torus(p, c, .3, .028, GOLD, GILT, 40, 8, 'x')
    for j in range(5):
        a = j / 5 * 2 * math.pi
        tube(p, [c + (0, math.cos(a) * .05, math.sin(a) * .05), c + (0, math.cos(a) * .29, math.sin(a) * .29)], .014, GOLD, GILT, 6)
    tube(p, [c - (.03, 0, 0), c + (.05, 0, 0)], .055, GOLD_PALE, GILT, 10)
    tube(p, [c + (0, .3, 0), c + (.12, .3, 0)], .018, GOLD_PALE, GILT, 8)
    for y in (-.6, .6):
        bevel_box(p, (.02, y, 2.31), (.12, .08, .02), CHARCOAL, DARK, .005)
    return weather(p, 311, reach=1.2)


def channel():
    """The irrigation channel: dressed white stone in 2 m sections with dark mortar joints, coping on the
    walls, a wet darker band below the water line, and running water. 10 x 1.2 x 0.6, along x."""
    rng = np.random.default_rng(321)
    p = Part('SM_CN_Channel', (STONE, DARK, WATER))
    for i in range(5):
        x = -4 + 2 * i
        bevel_box(p, (x, 0, .06), (.995, .6, .06), vary(WHITE, rng, .05), STONE, .02)
        for s in (-1, 1):
            bevel_box(p, (x, s * .52, .27), (.995, .08, .15), vary(ASH, rng, .08), STONE, .015)
            bevel_box(p, (x, s * .52, .475), (.995, .08, .055), vary(WHITE, rng, .06), STONE, .012)
            bevel_box(p, (x, s * .525, .565), (.995, .075, .035), vary(IVORY, rng, .05), STONE, .012)
        if i:
            jx = x - 1.0
            box(p, (jx, 0, .055), (.006, .59, .055), CHARCOAL, DARK)
            for s in (-1, 1):
                box(p, (jx, s * .52, .34), (.006, .078, .26), CHARCOAL, DARK)
    xs = np.linspace(-5, 5, 11)
    verts = [(x, y, .4) for x in xs for y in (-.44, .44)]
    faces = [[2 * j, 2 * j + 2, 2 * j + 3, 2 * j + 1] for j in range(10)]
    p.add(verts, faces, [tone(BLUE_ICE, .92 + .08 * math.sin(v[0] * 1.7)) for v in verts], WATER, False)
    return weather(p, 321, reach=.4, depth=.3)


def board():
    """The irrigation board (scan target): a slate under a little red roof on white posts. Rhea's chalk
    diagram shows the order (no writing): the channel climbing the terrace past three sluices marked
    with one, two and three dots, and an arrow to the pylon. Faces +x. 0.4 x 2 x 2.2."""
    rng = np.random.default_rng(331)
    p = Part('SM_CN_Board', (PAINT, DARK, STONE, REDS, METAL, CLOTH))
    for s in (-1, 1):
        # Up into the roof slabs (they stopped 4-6 cm under them, so the roof hovered).
        bevel_box(p, (0, s * .9, 1.0825), (.06, .06, 1.0825), vary(WHITE_PURE, rng, .04), PAINT, .012)
        bevel_box(p, (0, s * .9, .06), (.09, .09, .06), ASH, STONE, .015)
    bevel_box(p, (0, 0, 1.35), (.02, .84, .57), SLATE, DARK, .006)
    for z in (.76, 1.94):
        bevel_box(p, (.0, 0, z), (.035, .88, .03), WHITE_PURE, PAINT, .008)
    for s in (-1, 1):
        # A hair thinner than the rails, so where they cross at the corners no two faces share a plane.
        bevel_box(p, (0, s * .855, 1.35), (.032, .03, .6), WHITE_PURE, PAINT, .008)
    bevel_box(p, (.07, 0, .74), (.05, .7, .012), CHARCOAL, METAL, .004)
    # Chalk is a film on the slate: matte (CN_Cloth, the paper surface; CN_White laid marble veins over it) and at most
    # 6 mm proud of the slate's face (the lines stood 1.4 cm out, raised bars rather than chalk).
    chalk = lambda: vary(WHITE, rng, .06)  # noqa: E731

    def stroke(a, b, w, level):
        """One 4 mm chalk line at depth level 0-3, 0.8 mm apart: consecutive lines of the channel take 0 and 1, those of
        each sluice's box 2 and 3, so no two lines that meet or cross share a face plane (they flickered there)."""
        x = .0215 + .0008 * level
        strut(p, (x, a[0], a[1]), (x, b[0], b[1]), w, .004, chalk(), CLOTH, (1, 0, 0))
    steps = [(-.7, .95), (-.3, .95), (-.3, 1.2), (.15, 1.2), (.15, 1.45), (.62, 1.45)]
    for k, (a, b) in enumerate(zip(steps, steps[1:])):
        stroke(a, b, .012, k % 2)
    for n, (y, z) in enumerate(((-.5, .95), (-.06, 1.2), (.4, 1.45)), 1):
        for k, (a, b) in enumerate((((y - .06, z - .1), (y + .06, z - .1)), ((y + .06, z - .1), (y + .06, z + .02)),
                                    ((y + .06, z + .02), (y - .06, z + .02)), ((y - .06, z + .02), (y - .06, z - .1)))):
            stroke(a, b, .01, 2 + k % 2)
        for d in range(n):  # the dots touch no line: 0.7 mm proud of the slate
            polygon(p, [(.0207, y - .05 + d * .05 + dy * .015, z + .12 + dz * .015) for dy, dz in ((-1, -1), (1, -1), (1, 1), (-1, 1))],
                    chalk(), CLOTH, toward=(1, 0, 0))
    stroke((.64, 1.45), (.64, 1.7), .012, 0)
    # The arrowhead lies over its line's end (front at 0.0235), so 1.4 mm in front of it.
    polygon(p, [(.0249, .58, 1.68), (.0249, .7, 1.68), (.0249, .64, 1.79)], chalk(), CLOTH, toward=(1, 0, 0))
    polygon(p, [(.0207, .74, 1.1), (.0207, .82, 1.1), (.0207, .78, 1.62)], chalk(), CLOTH, toward=(1, 0, 0))
    gable_roof(p, (0, 0, 2.11), 1.9, .32, .05, RED, REDS, .04, .03, 90.0)
    for s in (-1, 1):  # knee braces up into the roof's underside (2.12 m there)
        strut(p, (0, s * .9, 1.98), (s * .12, s * .9, 2.12), .03, .03, WHITE_PURE, PAINT, (0, 1, 0))
    return weather(p, 331, reach=.6)


def pipe_run(part, y, z, r, colour, slot, half=5.7, drop=.3, bend=.6):
    """A pipe that rises out of the ground, crosses at height z and goes back down (pipe bridges)."""
    left = bezier((-half, y, z - bend), (-half, y, z - bend * .45), (-half + bend * .45, y, z), (-half + bend, y, z), 6)
    right = bezier((half - bend, y, z), (half - bend * .45, y, z), (half, y, z - bend * .45), (half, y, z - bend), 6)
    pts = [(-half, y, drop)] + list(left) + [(x, y, z) for x in np.linspace(-half + bend, half - bend, 9)[1:-1]] + list(right) + [(half, y, drop)]
    return tube(part, pts, r, colour, slot, 12)


def pipe_bridge():
    """A pipe bridge of the Terraces: two steel portal frames on concrete footings carry three pipes
    (insulated white with gold cladding bands, red water, black steam) over the path between side
    trusses; the pipes rise from and return to the ground. 12 span on x, 4 tall."""
    rng = np.random.default_rng(341)
    p = Part('SM_CN_PipeBridge', (METAL, PAINT, REDS, GILT, STONE))
    for x in (-4.5, 4.5):
        for y in (-.95, .95):
            bevel_box(p, (x, y, .14), (.32, .32, .14), vary(ASH, rng, .08), STONE, .03)
            bevel_box(p, (x, y, .29), (.2, .2, .012), CHARCOAL, METAL, .004)
            rivets(p, [(x + dx, y + dy, .3) for dx in (-.15, .15) for dy in (-.15, .15)], (0, 0, 1), .02, ASH, METAL)
            ibeam(p, (x, y, .3), (x, y, 3.3), .26, .2, CHARCOAL, METAL, (1, 0, 0))
            for n in range(6):
                bevel_box(p, (x, y, .42 + n * .17), (.15, .15, .085), RED if n % 2 == 0 else WHITE_PURE, REDS if n % 2 == 0 else PAINT, .01)
            strut(p, (x, y, 2.55), (x, y - .6 * np.sign(y), 3.2), .1, .1, SLATE, METAL, (1, 0, 0))
        ibeam(p, (x, -1.15, 3.36), (x, 1.15, 3.36), .26, .2, CHARCOAL, METAL)
    for y in (-1.02, 1.02):
        strut(p, (-4.5, y, 3.53), (4.5, y, 3.53), .08, .08, SLATE, METAL, (0, 1, 0))
        strut(p, (-4.5, y, 3.94), (4.5, y, 3.94), .08, .08, SLATE, METAL, (0, 1, 0))
        xs = np.linspace(-4.5, 4.5, 7)
        for i, x in enumerate(xs):
            strut(p, (x, y, 3.53), (x, y, 3.94), .06, .06, SLATE, METAL, (0, 1, 0))
            if i < 6:
                a, b = ((x, y, 3.53), (xs[i + 1], y, 3.94)) if i % 2 == 0 else ((x, y, 3.94), (xs[i + 1], y, 3.53))
                strut(p, a, b, .05, .05, SLATE, METAL, (0, 1, 0))
    for x in np.linspace(-3, 3, 3):
        strut(p, (x, -1.02, 3.49), (x, 1.02, 3.49), .08, .06, SLATE, METAL, (1, 0, 0))
    for y, r, colour, slot, zbase in ((-.45, .2, WHITE_PURE, PAINT, 3.49), (.15, .14, RED, REDS, 3.49), (.62, .11, CHARCOAL, METAL, 3.49)):
        z = zbase + r
        pipe_run(p, y, z, r, colour, slot)
        for x in (-5.7, 5.7):
            bevel_box(p, (x, y, .15), (r + .12, r + .12, .15), vary(ASH, rng, .06), STONE, .02)
        for x in (-2.4, 0.0, 2.4):
            # 8 cm wide, so the middle clamp's flanks stand clear of the 6 cm cross strut it sits on (they shared its planes).
            tube(p, [(x - .04, y, z), (x + .04, y, z)], r + .04, SLATE, METAL, 12)
            rivets(p, [(x + .045, y + math.cos(a) * (r + .025), z + math.sin(a) * (r + .025)) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)],
                   (1, 0, 0), .012, ASH, METAL)
        if colour is WHITE_PURE:
            for x in np.arange(-4.0, 4.01, 1.0):
                tube(p, [(x - .02, y, z), (x + .02, y, z)], r + .008, GOLD_PALE, GILT, 12)
    return weather(p, 341, reach=1.0)


# ---------------------------------------------------------------- the Reservoir

def buoy():
    """A mooring buoy of the Reservoir, where an AL anchor sits: a black antifouled float with a red and a
    white band, a rubber fender, a boarding ladder and a riveted steel deck whose top is 1.2 m above the
    base. Radius 1.5."""
    rng = np.random.default_rng(351)
    p = Part('SM_CN_Buoy', (DARK, REDS, PAINT, METAL, GILT))
    lathe(p, [(.35, 0), (.9, .12), (1.3, .32), (1.44, .45)], CHARCOAL, DARK, 28)
    lathe(p, [(1.44, .45), (1.5, .62), (1.5, .82)], RED, REDS, 28)
    lathe(p, [(1.5, .82), (1.47, 1.02), (1.38, 1.12), (1.34, 1.17)], WHITE_PURE, PAINT, 28)
    disc(p, (0, 0), .35, CHARCOAL, DARK, 28, 0.0, up=False)
    torus(p, (0, 0, .82), 1.5, .055, BLACK, DARK, 40, 8, 'z')
    for j in range(8):  # steel lashings wrapped round the fender (flat rings at its centre height, they lay buried in it)
        a = j / 8 * 2 * math.pi + .2
        radial = np.array([math.cos(a), math.sin(a), 0.0])
        c = radial * 1.5 + (0, 0, .82)
        loop = [c + .066 * (math.cos(t) * radial + math.sin(t) * np.array([0, 0, 1.0])) for t in np.linspace(0, 2 * math.pi, 9)]
        tube(p, loop, .011, SLATE, METAL, 4, cap=False)
    lathe(p, [(1.34, 1.17), (1.36, 1.205), (1.3, 1.205), (1.3, 1.195)], GOLD, GILT, 28)  # a lip 5 mm proud of the deck
    disc(p, (0, 0), 1.33, CHARCOAL, METAL, 28, 1.19)  # the deck under the plates: their seams show dark steel
    for j in range(6):
        a0, a1 = j / 6 * 2 * math.pi + .01, (j + 1) / 6 * 2 * math.pi - .01
        pts = [(0, 0, 1.2)] + [(math.cos(a) * 1.3, math.sin(a) * 1.3, 1.2) for a in np.linspace(a0, a1, 6)]
        p.add(pts, [[0] + list(range(1, 7))], vary(SLATE, rng, .1), METAL, False)
        rivets(p, [(math.cos(a0) * r, math.sin(a0) * r, 1.2) for r in (.35, .7, 1.05)], (0, 0, 1), .018, ASH, METAL)
    for j in range(4):
        a = j / 4 * 2 * math.pi + math.pi / 4
        bevel_box(p, (math.cos(a) * .55, math.sin(a) * .55, 1.207), (.12, .12, .008), CHARCOAL, METAL, .004, math.degrees(a))  # hatches on the deck
    for s in (-1, 1):
        tube(p, [(1.53, s * .2, .3), (1.53, s * .2, 1.12)], .02, ASH, METAL, 6)
        for z, hull in ((.5, 1.45), (1.08, 1.41)):  # standoffs to the hull, which the ladder otherwise never touched
            tube(p, [(hull - .02, s * .2, z), (1.53, s * .2, z)], .016, ASH, METAL, 6)
    for z in np.linspace(.4, 1.05, 4):
        tube(p, [(1.53, -.2, z), (1.53, .2, z)], .016, ASH, METAL, 6)
    return weather(p, 351, reach=.9, depth=.4)


def pier():
    """A jetty of the Reservoir: tarred black piles with cross-bracing, pile caps and stringers, white
    painted deck planks laid with gaps and a little warp, gold mooring rings and a ladder at the end.
    12 x 3 x 1; the deck's top is z 1.0."""
    rng = np.random.default_rng(361)
    p = Part('SM_CN_Pier', (STONE, DARK, METAL, GILT))
    xs = np.linspace(-5.5, 5.5, 7)
    for x in xs:
        for y in (-1.35, 1.35):
            cylinder(p, (x + rng.uniform(-.03, .03), y, 0), .13, .78, vary(CHARCOAL, rng, .2), DARK, 10, .12)
        bevel_box(p, (x, 0, .78), (.1, 1.45, .08), vary(CHARCOAL, rng, .2), DARK, .02)
    for a, b in zip(xs, xs[1:]):
        for y in (-1.35, 1.35):
            strut(p, (a, y, .1), (b, y, .66), .05, .1, BLACK, DARK, (0, 1, 0))
    for y in (-1.2, -.4, .4, 1.2):
        bevel_box(p, (0, y, .905), (6.0, .055, .045), vary(BLACK, rng, .2), DARK, .012)
    for s in (-1, 1):
        bevel_box(p, (0, s * 1.47, .88), (6.0, .025, .07), vary(CHARCOAL, rng, .15), DARK, .01)
    for i, x in enumerate(np.arange(-5.9, 5.91, .2)):
        colour = tone(mix(WHITE, IVORY, rng.uniform(0, .6)), rng.uniform(.72, 1.02))
        bevel_box(p, (x, rng.uniform(-.01, .01), .975 + rng.uniform(-.003, 0)), (.094, 1.49, .025), colour, STONE, .008, rng.uniform(-.25, .25))
        if i % 3 == 0:
            rivets(p, [(x, y, 1.0) for y in (-1.2, -.4, .4, 1.2)], (0, 0, 1), .008, SLATE, METAL)
    for x in (-4.0, 0.0, 4.0):
        for s in (-1, 1):
            torus(p, (x, s * 1.5, .84), .07, .014, GOLD, GILT, 12, 5, 'y')
            bevel_box(p, (x, s * 1.5, .9), (.03, .012, .03), GOLD_PALE, GILT, .006)
    for y in (-.25, .25):
        tube(p, [(6.04, y, .05), (6.04, y, 1.0), (5.95, y, 1.0)], .022, ASH, METAL, 6)
    for z in np.arange(.2, .95, .25):
        tube(p, [(6.04, -.25, z), (6.04, .25, z)], .016, ASH, METAL, 6)
    return weather(p, 361, reach=.8, depth=.5)


def boat():
    """A fisher's skiff of the Reservoir: a lofted round-bilge hull (black below the water line, white
    above, a red rubbing strake), thwarts and floorboards, oars, gold oarlocks, a net heaped in the bow
    and a lantern on a pole at the stern. 5 x 2 x 1.5, bow at +x."""
    rng = np.random.default_rng(371)
    p = Part('SM_CN_Boat', (PAINT, DARK, REDS, STONE, GILT, CLOTH, GLOW, METAL))
    n_exp = 2.8
    stations = np.linspace(-2.4, 2.47, 15)

    def breadth(x):
        return max(.015, .98 * math.sqrt(max(0.0, 1 - ((x + .3) / 2.8) ** 2)))

    def sheer(x):
        return .8 + .18 * max(0.0, x / 2.5) ** 2 + .04 * max(0.0, -x / 2.4) ** 2

    def keel(x):
        return .03 + .22 * max(0.0, (x - 1.2) / 1.3) ** 2

    def section(x, th, inset=0.0):
        b, s, k = breadth(x) - inset, sheer(x), keel(x) + inset
        b = max(b, .008)
        th = np.asarray(th)
        y = b * np.sin(th) ** (2 / n_exp)
        z = k + (s - k) * (1 - np.cos(th) ** (2 / n_exp))
        return y, z

    def theta_at(x, zw):
        s, k = sheer(x), keel(x)
        f = min(.999, max(0.001, (zw - k) / max(s - k, 1e-3)))
        return math.acos((1 - f) ** (n_exp / 2))

    water = lambda x: theta_at(x, .28)  # noqa: E731  the boot-top: antifouling below, white paint above
    # A point inside the hull on its centre line, drawn toward midships: at the bow and stern the skin faces fore
    # and aft, so a point level with the face (same x) could not tell its outside from its inside.
    mid = lambda c: (.5 * max(-1.4, min(1.4, c[0])), 0.0, (keel(c[0]) + sheer(c[0])) / 2)  # noqa: E731
    out_mid = lambda c: np.asarray(c) + (np.asarray(c) - np.asarray(mid(c)))  # noqa: E731
    lower = []
    for x in stations:
        y, z = section(x, np.linspace(0.0, water(x), 5))
        # One ring per station, from the port water line under the keel to the starboard one.
        lower.append([(x, -yy, zz) for yy, zz in zip(y[:0:-1], z[:0:-1])] + [(x, yy, zz) for yy, zz in zip(y, z)])
    loft(p, lower, CHARCOAL, DARK, mid, closed=False)
    for s in (1, -1):
        upper = []
        for x in stations:
            th = np.linspace(water(x), math.pi / 2, 4)
            y, z = section(x, th)
            upper.append([(x, s * yy, zz) for yy, zz in zip(y, z)])
        loft(p, upper, WHITE_PURE, PAINT, mid, closed=False)
        inner = []
        for x in stations[:-1]:
            th = np.linspace(0.0, math.pi / 2, 6)
            y, z = section(x, th, .035)
            inner.append([(x, s * yy, zz) for yy, zz in zip(y, z)])
        loft(p, inner, vary(WHITE, rng, .05), PAINT, out_mid, closed=False)
        rail = [(x, s * (breadth(x) + .012), sheer(x) - .03) for x in stations]
        tube(p, rail, .032, RED, REDS, 6)
        tube(p, [(x, s * (breadth(x) - .02), sheer(x) + .005) for x in stations[:-1]], .028, WHITE, STONE, 6)
    x0 = stations[0]
    th = np.linspace(0, math.pi / 2, 6)
    y, z = section(x0, th)

    def transom(x, toward):
        """Closes the hull at station x on the lofts' own ring vertices (no slit along its edge): antifouling black
        below the boot-top, white above."""
        yu, zu = section(x, np.linspace(water(x), math.pi / 2, 4))   # the upper lofts' ring, boot-top to sheer
        yl, zl = section(x, np.linspace(0.0, water(x), 5))           # the lower loft's ring, keel to boot-top
        under = [(x, -a, b) for a, b in zip(yl[:0:-1], zl[:0:-1])] + [(x, a, b) for a, b in zip(yl, zl)]
        upper = [(x, -a, b) for a, b in zip(yu[::-1], zu[::-1])] + [(x, a, b) for a, b in zip(yu, zu)]
        polygon(p, under, CHARCOAL, DARK, toward=toward)
        polygon(p, upper, WHITE_PURE, PAINT, toward=toward)
    transom(x0, (-1, 0, 0))
    transom(stations[-1], (1, 0, 0))  # the bow ends in a little pram-bow transom behind the stem
    yi, zi = section(x0, th, .035)
    polygon(p, [(x0 + .03, -a, b) for a, b in zip(yi[::-1], zi[::-1])] + [(x0 + .03, a, b) for a, b in zip(yi[1:], zi[1:])],
            vary(WHITE, rng, .05), PAINT, toward=(1, 0, 0))
    bevel_box(p, (x0 + .01, 0, sheer(x0) - .01), (.03, breadth(x0), .03), WHITE, STONE, .01)
    # The inner lining ends a station short of the stem: a bulkhead closes it and a foredeck covers the bow.
    xb = stations[-2]
    yb_, zb_ = section(xb, th, .035)
    polygon(p, [(xb, -a, b) for a, b in zip(yb_[::-1], zb_[::-1])] + [(xb, a, b) for a, b in zip(yb_[1:], zb_[1:])],
            vary(WHITE, rng, .05), PAINT, toward=(-1, 0, 0))
    fore_x = np.linspace(xb, 2.47, 5)
    for xa, xc in zip(fore_x, fore_x[1:]):
        # Out to the skin under the rubbing strake: 2 cm short of it, the deck left a slit into the hollow bow.
        wa, wc = breadth(xa) + .004, breadth(xc) + .004
        polygon(p, [(xa, -wa, sheer(xa) - .004), (xa, wa, sheer(xa) - .004), (xc, wc, sheer(xc) - .004), (xc, -wc, sheer(xc) - .004)],
                vary(WHITE, rng, .04), STONE, toward=(0, 0, 1))
    stem = [(x, 0, keel(x) + (sheer(x) - keel(x)) * t) for x, t in ((2.47, 0), (2.48, .5), (2.5, 1.0))]
    tube(p, stem, .035, RED, REDS, 6)
    tube(p, [(x, 0, keel(x) - .015) for x in np.linspace(-2.38, 2.45, 10)], .022, BLACK, DARK, 6)
    for x, run in ((-1.9, .3), (-.9, .12), (.6, .12)):  # the stern sheets, then two rowing thwarts
        bevel_box(p, (x, 0, .5), (run, breadth(x) - .05, .022), vary(WHITE, rng, .05), STONE, .008)
    for x in np.linspace(-2.1, 1.6, 6):
        bevel_box(p, (x, 0, .1), (.28, .32, .012), vary(ASH, rng, .1), STONE, .004)
    for s in (-1, 1):
        a, b = (-1.6, s * .35, .56), (1.3, s * .5, .56)
        tube(p, [a, b], .022, WHITE_PURE, PAINT, 6)
        bevel_box(p, (b[0] + .25, b[1], .56), (.25, .07, .008), RED, REDS, .004)
        c = (-.3, s * (breadth(-.3) - .01), sheer(-.3) + .03)
        torus(p, c, .04, .008, GOLD, GILT, 10, 4, 'y', arc=math.pi, start=math.pi)  # the oarlock's U opens upward
    for k in range(5):
        c = (1.6 + rng.uniform(-.2, .3), rng.uniform(-.3, .3), .25 + k * .03)
        blob(p, c, (.28, .24, .1), vary(SLATE, rng, .2), CLOTH, 1, .3, 380 + k)
    for k in range(4):
        blob(p, (1.4 + rng.uniform(-.3, .4), rng.uniform(-.35, .35), .36), .045, WHITE_PURE, PAINT, 1, .05, 390 + k)
    tube(p, [(-1.95, .3, .52), (-1.95, .3, 1.38)], .022, WHITE_PURE, PAINT, 6)
    tube(p, [(-1.95, .3, 1.38), (-1.85, .3, 1.38)], .012, SLATE, METAL, 5)
    c = np.array([-1.85, .3, 1.42])
    cylinder(p, c - (0, 0, .07), .055, .14, LIGHT_WARM, GLOW, 8)
    cylinder(p, c + (0, 0, .07), .07, .02, CHARCOAL, METAL, 8, .02)
    cylinder(p, c - (0, 0, .09), .065, .02, CHARCOAL, METAL, 8)
    for j in range(4):
        a = j / 4 * 2 * math.pi + .4
        tube(p, [c + (math.cos(a) * .062, math.sin(a) * .062, -.07), c + (math.cos(a) * .062, math.sin(a) * .062, .07)], .006, CHARCOAL, METAL, 4)
    tube(p, bezier((2.5, 0, .95), (2.7, .1, .7), (2.3, .4, .45), (2.0, .45, .55), 6), .012, WHITE, CLOTH, 5)
    return weather(p, 371, reach=.6, depth=.3)


# ---------------------------------------------------------------- the Foundry

def clad(part, rng, fixed, axis, lo, hi, cols, rows, colour, slot, sign, t=.05, skip=None, rivet=.4):
    """Riveted plate cladding on one face of a box: plates in courses with 1 cm seams over a darker
    backing, rivets along every horizontal seam. axis is the face's normal axis (0 x, 1 y), fixed its
    coordinate, sign which way it faces; lo/hi are (u, z) corners in the face; skip(u, z) leaves a gap."""
    u_axis = 1 - axis
    us, zs = np.linspace(lo[0], hi[0], cols + 1), np.linspace(lo[1], hi[1], rows + 1)
    normal = np.zeros(3)
    normal[axis] = sign
    for i in range(cols):
        for j in range(rows):
            uc, zc = (us[i] + us[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
            if skip is not None and skip(uc, zc):
                continue
            c, h = np.zeros(3), np.zeros(3)
            c[axis], c[u_axis], c[2] = fixed + sign * t / 2, uc, zc
            h[axis], h[u_axis], h[2] = t / 2, (us[i + 1] - us[i]) / 2 - .005, (zs[j + 1] - zs[j]) / 2 - .005
            bevel_box(part, c, h, vary(colour, rng, .1), slot, .012)
            n = max(2, int((us[i + 1] - us[i]) / rivet))
            pts = []
            for k in range(n):
                p = np.zeros(3)
                p[axis], p[u_axis], p[2] = fixed + sign * t, us[i] + (us[i + 1] - us[i]) * (k + .5) / n, zs[j + 1] - .05
                pts.append(p)
            rivets(part, pts, normal, .018, tone(colour, 1.6), slot)


def furnace():
    """A Mechanoid smelting furnace: riveted black iron plates braced by buckstays and tie rods on a
    soot-black foundation, a hood and gold-banded chimney, blast pipes, gold gauges, and at the front
    (+x) a firebrick arch whose mouth glows white at the heart and red along its rims, under a raised
    iron door. 6 x 8 x 10."""
    rng = np.random.default_rng(401)
    p = Part('SM_CN_Furnace', (METAL, DARK, STONE, GLOW, GILT))
    bevel_box(p, (0, 0, .2), (3.0, 4.0, .2), CHARCOAL, DARK, .05)
    box(p, (0, 0, 3.0), (2.38, 3.38, 2.6), BLACK, METAL)
    mouth = lambda u, z: abs(u) < 1.75 and z < 4.0  # noqa: E731
    for sign in (-1, 1):
        clad(p, rng, sign * 3.38, 1, (-2.4, .4), (2.4, 5.6), 4, 4, CHARCOAL, METAL, sign)
    clad(p, rng, -2.38, 0, (-3.4, .4), (3.4, 5.6), 5, 4, CHARCOAL, METAL, -1)
    clad(p, rng, 2.38, 0, (-3.4, .4), (3.4, 5.6), 5, 4, CHARCOAL, METAL, 1, skip=mouth)
    bevel_box(p, (0, 0, 5.65), (2.45, 3.45, .06), SLATE, METAL, .02)
    for sign in (-1, 1):
        for x in (-1.8, -.6, .6, 1.8):
            ibeam(p, (x, sign * 3.5, .4), (x, sign * 3.5, 5.75), .22, .2, SLATE, METAL, (0, 1, 0))
    for x in (-1.8, -.6, .6, 1.8):
        tube(p, [(x, -3.62, 5.8), (x, 3.62, 5.8)], .04, ASH, METAL, 6)
        rivets(p, [(x, s * 3.62, 5.8) for s in (-1, 1)], [(0, s, 0) for s in (-1, 1)], .05, ASH, METAL)
    for x in (-2.4, 2.4):
        for y in (-3.4, 3.4):
            angle_iron(p, (x, y, .4), (x, y, 5.7), .12, SLATE, METAL, (np.sign(-x), np.sign(-y), 0))
    # The mouth: cast-iron portal, firebrick lining and the glowing hearth inside it. The firebrick is pale: a warm glow
    # on a bright refractory reads pale gold, on mid grey it read brown. The fire is white and warm white inside; red only
    # rims its sides and the hearth strip, and never lies over a gold polygon (red over gold flickered into orange).
    for s in (-1, 1):
        # The jambs stop under the lintel: running into it, their fronts shared its front plane and flickered.
        bevel_box(p, (2.7, s * 1.48, 1.95), (.3, .26, 1.55), SLATE, METAL, .04)
        for z in np.arange(1.0, 2.1, .27):
            bevel_box(p, (2.68, s * 1.27, z), (.28, .06, .13), tone(IVORY, rng.uniform(.85, .95)), STONE, .012)
    bevel_box(p, (2.7, 0, 3.75), (.3, 1.75, .25), SLATE, METAL, .04)
    arch(p, (2.69, 0, .9), 2.4, 2.4, .22, .56, tone(IVORY, .9), STONE, segments=9)
    bevel_box(p, (2.69, 0, .7), (.29, 1.5, .2), CHARCOAL, METAL, .03)
    back = [(2.42, -1.2, .9), (2.42, 1.2, .9), (2.42, 1.2, 2.1)] + [(2.42, -math.cos(a) * 1.2, 2.1 + math.sin(a) * 1.2) for a in np.linspace(0, math.pi, 13)[1:-1][::-1]] + [(2.42, -1.2, 2.1)]
    polygon(p, back, LIGHT_WARM, GLOW, toward=(1, 0, 0))
    heart = [(2.425, -.85, .92), (2.425, .85, .92), (2.425, .85, 1.9)] + [(2.425, -math.cos(a) * .85, 1.9 + math.sin(a) * .7) for a in np.linspace(0, math.pi, 11)[1:-1][::-1]] + [(2.425, -.85, 1.9)]
    polygon(p, heart, LIGHT_WHITE, GLOW, toward=(1, 0, 0))
    polygon(p, [(2.43, -.4, .93), (2.43, .4, .93), (2.43, .3, 1.5), (2.43, -.3, 1.5)], mix(LIGHT_GOLD, LIGHT_WHITE, .45), GLOW, toward=(1, 0, 0))
    polygon(p, [(2.42, -1.2, .905), (3.0, -1.2, .905), (3.0, 1.2, .905), (2.42, 1.2, .905)], tone(LIGHT_GOLD, .4), GLOW, toward=(0, 0, 1))
    for s in (-1, 1):
        polygon(p, [(2.42, s * 1.205, .9), (3.0, s * 1.205, .9), (3.0, s * 1.205, 2.1), (2.42, s * 1.205, 2.1)], LIGHT_RED, GLOW, toward=(0, -s, 0))
    bevel_box(p, (2.96, 0, .39), (.04, 1.3, .02), LIGHT_RED, GLOW, .01)
    # The raised door runs in guides bolted to the cladding, under a header its chains hang from (all three stood
    # clear of the wall before, the door hovering 8 cm in front of it).
    for s in (-1, 1):
        bevel_box(p, (2.55, s * 1.65, 4.75), (.12, .08, .75), ASH, METAL, .015)
    bevel_box(p, (2.55, 0, 5.55), (.12, 1.75, .05), SLATE, METAL, .015)
    bevel_box(p, (2.56, 0, 4.7), (.05, 1.58, .62), SLATE, METAL, .02)
    for z in (4.3, 4.7, 5.1):
        bevel_box(p, (2.62, 0, z), (.02, 1.5, .03), CHARCOAL, METAL, .006)
        rivets(p, [(2.64, y, z) for y in np.linspace(-1.4, 1.4, 8)], (1, 0, 0), .016, ASH, METAL)
    for s in (-1, 1):
        tube(p, [(2.62, s * 1.2, 5.32), (2.62, s * 1.2, 5.51)], .02, ASH, METAL, 5)
    # Hood, chimney and soot.
    cylinder(p, (0, 0, 5.71), 2.6, 1.5, CHARCOAL, METAL, 4, 1.15, False, 45.0)
    cylinder(p, (0, 0, 7.2), .78, 2.6, CHARCOAL, METAL, 20)
    for z in (7.7, 8.6, 9.45):
        cylinder(p, (0, 0, z), .82, .12, GOLD_DEEP, GILT, 20)
    cylinder(p, (0, 0, 9.8), .7, .04, BLACK, METAL, 20)
    cylinder(p, (0, 0, 9.84), .98, .16, BLACK, METAL, 20, .3)
    for j in range(4):
        a = j / 4 * 2 * math.pi + math.pi / 4
        strut(p, (math.cos(a) * .7, math.sin(a) * .7, 9.6), (math.cos(a) * .9, math.sin(a) * .9, 9.86), .04, .04, BLACK, METAL)
    # Blast pipes along both sides, feeding the tuyeres.
    for s in (-1, 1):
        # The main ends past the front buckstay: ending at 1.9 its cap lay in the buckstay's flank and flickered.
        tube(p, [(-2.1, s * 3.7, 2.0), (2.02, s * 3.7, 2.0)], .17, SLATE, METAL, 12)
        for x in (-1.2, 0.0, 1.2):
            tube(p, bezier((x, s * 3.7, 1.83), (x, s * 3.7, 1.5), (x, s * 3.55, 1.4), (x, s * 3.43, 1.4), 5), .09, SLATE, METAL, 8)
            cylinder(p, (x, s * 3.7, 2.17), .06, .1, GOLD, GILT, 8)
        tube(p, [(-2.1, s * 3.7, 2.0), (-2.3, s * 3.7, 2.0)], .22, CHARCOAL, METAL, 12)
    for y in (-2.3, 2.3):
        c = np.array([2.47, y, 1.75])
        tube(p, [c - (.04, 0, 0), c + (.03, 0, 0)], .16, GOLD, GILT, 16)
        polygon(p, [c + (.032, math.cos(a) * .13, math.sin(a) * .13) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)], WHITE, STONE, toward=(1, 0, 0))
        strut(p, c + (.04, 0, 0), c + (.04, .07, .07), .012, .006, BLACK, DARK, (1, 0, 0))
    # The ladder to the top climbs the back wall, which nothing else uses (on the side it ran through the blast main),
    # on standoffs to the plates.
    lx = -2.66
    for z in np.arange(.75, 5.6, .32):
        tube(p, [(lx, -.3, z), (lx, .3, z)], .018, ASH, METAL, 5)
    for y in (-.3, .3):
        tube(p, [(lx, y, .4), (lx, y, 5.95)], .025, ASH, METAL, 6)
        for z in (1.2, 3.2, 5.2):
            tube(p, [(-2.42, y, z), (lx, y, z)], .02, ASH, METAL, 5)
    return weather(p, 401, reach=2.5, depth=.4, grime=.3)


def crane():
    """The Foundry's gantry crane: end carriages on rails, A-frame legs with ties and braces, twin box
    girders with stiffeners, a hoist trolley with gold sheaves, a striped hook block, the operator's cab,
    a walkway and floodlights. 4 x 22 x 14 (span along y)."""
    rng = np.random.default_rng(411)
    p = Part('SM_CN_Crane', (METAL, PAINT, REDS, GILT, GLASS, GLOW, DARK))
    for s in (-1, 1):
        y = s * 10.5
        strut(p, (-2.0, y, .06), (2.0, y, .06), .12, .12, SLATE, METAL)
        bevel_box(p, (0, y, .48), (1.85, .32, .3), CHARCOAL, METAL, .04)
        # Hazard bands on the carriage's outer face, 30 cm tall and 2 cm proud (width and depth were swapped: a 2 cm
        # tall shelf stood 16 cm out of the face).
        stripes(p, (-1.84, y + s * .33, .48), (1.84, y + s * .33, .48), .3, .02, 8, (RED, WHITE_PURE), (REDS, PAINT), (0, 1, 0))
        for x in (-1.25, 1.25):
            tube(p, [(x, y - .2, .3), (x, y + .2, .3)], .28, SLATE, METAL, 14)
        for x in (-1.95, 1.95):
            tube(p, [(x - .1 * np.sign(x), y, .5), (x, y, .5)], .12, BLACK, DARK, 10)
        legs = [((-1.5, y, .78), (-.55, y, 12.0)), ((1.5, y, .78), (.55, y, 12.0))]
        for a, b in legs:
            strut(p, a, b, .44, .44, CHARCOAL, METAL, (0, 1, 0))
            bevel_box(p, (a[0], y, .8), (.32, .32, .03), SLATE, METAL, .01)
        for z, h in ((4.5, .22), (8.5, .22)):
            t = (z - .78) / 11.22
            xa = 1.5 + (.55 - 1.5) * t
            strut(p, (-xa, y, z), (xa, y, z), .25, h, CHARCOAL, METAL, (0, 1, 0))
        # The two braces lap at their crossing, one on each side of the frame's plane (in one plane they flickered).
        strut(p, (-1.32, y - .08, 1.6), (.9, y - .08, 8.4), .16, .16, SLATE, METAL, (0, 1, 0))
        strut(p, (1.32, y + .08, 1.6), (-.9, y + .08, 8.4), .16, .16, SLATE, METAL, (0, 1, 0))
        bevel_box(p, (0, y, 12.2), (1.2, .4, .2), CHARCOAL, METAL, .04)
    for x in (-.75, .75):
        bevel_box(p, (x, 0, 12.9), (.25, 11.0, .5), CHARCOAL, METAL, .05)
        for y in np.arange(-9.75, 9.8, 1.5):
            bevel_box(p, (x + np.sign(x) * .27, y, 12.9), (.02, .05, .46), SLATE, METAL, .008)
        rivets(p, [(x + np.sign(x) * .25, y, 13.32) for y in np.arange(-10.5, 10.6, .75)], (np.sign(x), 0, 0), .02, ASH, METAL)
        strut(p, (x, -10.9, 13.44), (x, 10.9, 13.44), .09, .08, ASH, METAL, (1, 0, 0))
    # Trolley and hoist.
    yt = 2.5
    bevel_box(p, (0, yt, 13.55), (1.1, .9, .07), SLATE, METAL, .02)
    for x in (-.75, .75):
        for dy in (-.6, .6):
            tube(p, [(x - .05, yt + dy, 13.52), (x + .05, yt + dy, 13.52)], .08, ASH, METAL, 8)
    tube(p, [(-.64, yt - .25, 13.8), (.64, yt - .25, 13.8)], .17, CHARCOAL, METAL, 14)  # into its flanges (2 cm short of them)
    for x in (-.65, .65):
        tube(p, [(x - .03, yt - .25, 13.8), (x + .03, yt - .25, 13.8)], .2, SLATE, METAL, 14)
    bevel_box(p, (0, yt + .45, 13.78), (.42, .3, .2), WHITE_PURE, PAINT, .03)
    bevel_box(p, (0, yt + .45, 13.99), (.44, .32, .01), CHARCOAL, METAL, .004)
    for x in (-.2, .2):
        torus(p, (x, yt, 13.3), .16, .03, GOLD, GILT, 16, 6, 'x')
        tube(p, [(x, yt + .16, 13.3), (x, yt + .16, 10.75)], .015, ASH, METAL, 5)
        tube(p, [(x, yt - .16, 13.3), (x, yt - .16, 10.75)], .015, ASH, METAL, 5)
    bevel_box(p, (0, yt, 10.5), (.32, .25, .28), RED, REDS, .04)
    for z in (10.36, 10.64):
        bevel_box(p, (0, yt, z), (.33, .26, .05), WHITE_PURE, PAINT, .01)
    tube(p, [(0, yt, 10.22), (0, yt, 9.95)], .05, GOLD, GILT, 8)
    torus(p, (0, yt + .14, 9.8), .16, .045, GOLD, GILT, 16, 8, 'x', arc=1.5 * math.pi, start=.5 * math.pi)
    # Operator's cab under the girders.
    yc = -7.8
    bevel_box(p, (0, yc, 11.55), (.9, .8, .85), WHITE_PURE, PAINT, .05)
    for s in (-1, 1):
        polygon(p, [(s * .91, yc - .6, 11.25), (s * .91, yc + .6, 11.25), (s * .91, yc + .6, 12.15), (s * .91, yc - .6, 12.15)],
                BLUE_PALE, GLASS, toward=(s, 0, 0))
    polygon(p, [(-.7, yc - .81, 11.2), (.7, yc - .81, 11.2), (.7, yc - .81, 12.15), (-.7, yc - .81, 12.15)], BLUE_PALE, GLASS, toward=(0, -1, 0))
    # Walkway with railing outside the +x girder.
    for y in np.arange(-10.5, 10.51, .5):
        strut(p, (1.0, y, 12.42), (1.7, y, 12.42), .03, .04, SLATE, METAL, (0, 1, 0))
    for x in (1.02, 1.7):
        strut(p, (x, -10.8, 12.45), (x, 10.8, 12.45), .05, .05, SLATE, METAL, (1, 0, 0))
    for y in np.arange(-10.5, 10.51, 1.5):
        strut(p, (1.7, y, 12.47), (1.7, y, 13.5), .04, .04, WHITE_PURE, PAINT, (1, 0, 0))
    for z in (13.0, 13.5):
        strut(p, (1.7, -10.6, z), (1.7, 10.6, z), .035, .035, WHITE_PURE, PAINT, (1, 0, 0))
    for y in (-6.0, 0.0, 6.0):
        # Each floodlight hangs from a tie between the girders' bottom flanges (it hung in the gap between them).
        strut(p, (-.9, y, 12.37), (.9, y, 12.37), .12, .06, SLATE, METAL)
        cylinder(p, (0, y, 12.22), .16, .12, CHARCOAL, METAL, 12)
        disc(p, (0, y), .13, LIGHT_WHITE, GLOW, 12, 12.215, up=False)
    lamp(p, (0, -10.5, 12.45), LIGHT_RED, .09)
    for z in np.arange(1.0, 12.3, .3):
        tube(p, [(1.98, -10.9, z), (1.98, -10.5, z)], .015, ASH, METAL, 5)
    for y in (-10.9, -10.5):
        tube(p, [(1.98, y, .78), (1.98, y, 12.45)], .022, ASH, METAL, 6)
    # Standoffs from the leg to rungs of the ladder, which otherwise stood free for 11 m, and at the top a last rung
    # tied to the walkway's edge.
    for z in (2.5, 4.9, 7.3, 10.0):
        leg_x = 1.5 + (.55 - 1.5) * (z - .78) / 11.22 + .2
        strut(p, (leg_x, -10.62, z), (1.98, -10.62, z), .04, .04, SLATE, METAL)
    tube(p, [(1.98, -10.9, 12.42), (1.98, -10.5, 12.42)], .015, ASH, METAL, 5)
    strut(p, (1.68, -10.7, 12.42), (1.98, -10.7, 12.42), .04, .04, SLATE, METAL)
    return weather(p, 411, reach=1.5, depth=.35)


def crane_bridge():
    """The bridge the crane lets down across the slag channel: twin plate girders and cross beams under
    bolted checker-plate deck panels, edge beams along both sides carrying red kick plates and a white railing, and
    gold rings through the lifting lugs. Deck 16 x 4 x 0.6 with its walk surface at z 0 (pivot at the deck's top
    centre)."""
    rng = np.random.default_rng(421)
    p = Part('SM_CN_CraneBridge', (METAL, PAINT, REDS, GILT))
    for y in (-1.6, 1.6):
        ibeam(p, (-8.0, y, -.325), (8.0, y, -.325), .55, .3, CHARCOAL, METAL)
        for x in np.arange(-7.0, 7.01, 1.0):
            bevel_box(p, (x, y, -.325), (.01, .13, .23), SLATE, METAL, .004)
    for x in np.arange(-7.9, 7.91, 1.975):  # up under the deck plates (they stopped 2.5 cm short), 2 mm below the girders' tops
        ibeam(p, (x, -1.6, -.177), (x, 1.6, -.177), .25, .14, SLATE, METAL)
    for s in (-1, 1):
        # Edge beams under the railing: the posts and kick plates stood 0.5-2.5 cm out beside the deck, on nothing.
        bevel_box(p, (0, s * 1.9425, -.1), (8.0, .0425, .1), CHARCOAL, METAL, .01)
    for i, x in enumerate(np.arange(-7.0, 7.01, 2.0)):
        bevel_box(p, (x, 0, -.025), (.995, 1.9, .025), vary(SLATE, rng, .12), METAL, .008)
        rivets(p, [(x + dx, y, 0) for dx in (-.9, .9) for y in np.linspace(-1.7, 1.7, 5)], (0, 0, 1), .014, ASH, METAL)
    for s in (-1, 1):
        # 2 mm up, so its underside (seen when the bridge hangs from the crane) is not in the posts' foot plane.
        bevel_box(p, (0, s * 1.92, .062), (8.0, .015, .06), RED, REDS, .005)
        for x in np.arange(-8.0, 8.01, 2.0):
            strut(p, (x, s * 1.95, 0), (x, s * 1.95, 1.075), .05, .05, WHITE_PURE, PAINT, (1, 0, 0))
        tube(p, [(-8.0, s * 1.95, 1.075), (8.0, s * 1.95, 1.075)], .025, WHITE_PURE, PAINT, 8)
        tube(p, [(-8.0, s * 1.95, .55), (8.0, s * 1.95, .55)], .018, WHITE_PURE, PAINT, 6)
        for x in (-6.5, 6.5):
            bevel_box(p, (x, s * 1.78, -.2), (.12, .03, .14), SLATE, METAL, .01)
            # A ring through the lug's eye (the shackle hung 3 cm out beside the lug, touching nothing).
            torus(p, (x, s * 1.78, -.33), .07, .016, GOLD, GILT, 12, 5, 'x')
    for x in (-8.0, 8.0):  # hazard bands across both ends, 16 cm tall and 2 cm proud (were a 4 cm shelf, size and depth swapped)
        stripes(p, (x, -1.88, -.1), (x, 1.88, -.1), .16, .04, 8, (RED, WHITE_PURE), (REDS, PAINT), (1, 0, 0))
    return weather(p, 421, ground=-.6, reach=.8, depth=.3)


def cable_lock():
    """One of the three couplings that hold the crane's bridge up: a gold cage of collars and bars around
    a red-glowing core of hardened cable, bolted ears on four sides and steel cable stubs entering top
    and bottom through gold ferrules. 1 x 1 x 1, centred."""
    p = Part('SM_CN_CableLock', (GILT, GLOW, METAL))
    prism(p, (0, 0, -.24), (0, 0, .24), .1, LIGHT_RED, GLOW, 6, .3)
    prism(p, (0, 0, -.2), (0, 0, -.27), .09, LIGHT_RED, GLOW, 6, .5)
    for s in (-1, 1):
        cylinder(p, (0, 0, s * .27 - .05), .3, .1, GOLD, GILT, 16)
        cylinder(p, (0, 0, s * .32 - .02), .2, .04, GOLD_PALE, GILT, 16)
        rivets(p, [(math.cos(a) * .25, math.sin(a) * .25, s * .32) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)], (0, 0, s), .02, GOLD_PALE, GILT)
    for j in range(6):
        a = j / 6 * 2 * math.pi
        tube(p, [(math.cos(a) * .24, math.sin(a) * .24, -.22), (math.cos(a) * .24, math.sin(a) * .24, .22)], .032, GOLD, GILT, 6)
    # A girdle round the bars at mid-height carries the four bolted ears (they hovered 3 cm off the cage).
    torus(p, (0, 0, 0), .262, .022, GOLD, GILT, 32, 6, 'z')
    for j in range(4):
        yaw = j * 90
        bevel_box(p, tuple(np.array([math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0]) * .375), (.125, .07, .06), GOLD, GILT, .015, yaw)
        c = np.array([math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0]) * .43
        rivets(p, [c + (0, 0, .06)], (0, 0, 1), .025, GOLD_PALE, GILT)
    for s in (-1, 1):
        cylinder(p, (0, 0, .34 if s > 0 else -.42), .07, .08, GOLD_PALE, GILT, 12)
        for k in range(3):  # three twisted strands make the cable read as wire rope
            a = k / 3 * 2 * math.pi
            strand = [(math.cos(a + t * 2.5) * .028, math.sin(a + t * 2.5) * .028, s * (.4 + t * .1)) for t in np.linspace(0, 1, 5)]
            tube(p, strand, .026, ASH, METAL, 6)
    return p


def workshop():
    """Forge-Mother Ilex's workshop hall: steel portal frames on a concrete slab, white panel cladding
    over a black kick band, clerestory windows, a standing-seam roof with skylights, gutters and
    downpipes, a gold gear emblem, and at the front (+x) a 6 x 5 m doorway whose red sliding doors stand
    open on their track. Inside: a workbench with a gold vise, a tool board and hanging lamps. 10 x 14 x 8."""
    rng = np.random.default_rng(431)
    p = Part('SM_CN_Workshop', (STONE, METAL, PAINT, REDS, GLASS, GLOW, GILT, DARK))
    hx, hy, eave, rise = 5.0, 7.0, 5.8, 1.8
    roof_z = lambda y: eave + rise * (1 - abs(y) / hy)  # noqa: E731
    bevel_box(p, (0, 0, .15), (hx, hy, .15), vary(ASH, rng, .05), STONE, .04)
    for x in np.linspace(-4.75, 4.75, 5):
        for s in (-1, 1):
            ibeam(p, (x, s * 6.8, .3), (x, s * 6.8, eave), .3, .2, CHARCOAL, METAL, (0, 1, 0))
            a, b = np.array([x, s * 6.8, eave]), np.array([x, 0, eave + rise - .1])
            d = b - a
            up = np.cross(d, (1, 0, 0))
            up = up if up[2] > 0 else -up
            # One side's rafters 4 mm narrower: where the two lap at the ridge their flanges' faces shared a plane.
            ibeam(p, a, b, .32, .18 - .004 * (s > 0), CHARCOAL, METAL, up)
    # Side walls: black kick band, white panels, a clerestory band of windows, a white frieze.
    for s in (-1, 1):
        y = s * 6.96
        for x0 in np.arange(-hx, hx - .01, 1.0):
            xc = x0 + .5
            # The kick band reaches 3 cm down into the slab's chamfered edge, so no wedge of shadow opens under the wall.
            bevel_box(p, (xc, y, .635), (.495, .04, .365), vary(CHARCOAL, rng, .15), METAL, .01)
            bevel_box(p, (xc, y, 2.8), (.495, .04, 1.8), vary(WHITE_PURE, rng, .05), PAINT, .012)
            bevel_box(p, (xc, y, 5.6), (.495, .04, .2), vary(WHITE_PURE, rng, .05), PAINT, .012)
        # The piers fill the band between the windows and out to both corners (stopping 25 cm short of the corners,
        # they left holes into the hall; neighbouring piers overlapped in one plane).
        windows = np.linspace(-3.56, 3.56, 4)
        edges = [-hx + .005] + [e for xc in windows for e in (xc - .82, xc + .82)] + [hx - .005]  # as the panels, inside the gables' faces
        for x0, x1 in zip(edges[::2], edges[1::2]):
            bevel_box(p, ((x0 + x1) / 2, y, 5.0), ((x1 - x0) / 2, .04, .4), WHITE_PURE, PAINT, .01)
        for xc in windows:
            window_frame(p, (xc, y + s * .02, 5.0), 1.6, .72, .1, CHARCOAL, METAL, BLUE_PALE, GLASS, 90.0 * s, 2, .04)
            # The pane seen from the hall, 5 mm inside the outer one: at the frame's back plane it shared that plane.
            polygon(p, [(xc - .8, y - s * .005, 4.64), (xc + .8, y - s * .005, 4.64), (xc + .8, y - s * .005, 5.36), (xc - .8, y - s * .005, 5.36)],
                    BLUE_PALE, GLASS, toward=(0, -s, 0))
    # Gable ends: the back closed, the front around the doorway.
    for sx in (-1, 1):
        x = sx * (hx - .04)
        for y0 in np.arange(-hy, hy - .01, 1.0):
            y1 = y0 + 1.0
            ya, yb = y0 + .005, y1 - .005
            z0 = .3
            if sx > 0 and y0 > -3.01 and y1 < 3.01:
                z0 = 5.0
            colour = vary(WHITE_PURE, rng, .05)
            pts = []
            for zb in (0, 1):
                for yy in (ya, yb):
                    for xb in (0, 1):
                        xx = x - .04 if xb == 0 else x + .04
                        pts.append((xx, yy, z0 if zb == 0 else roof_z(yy) - .02))
            hexa(p, pts, colour, PAINT)
            if z0 < 1:
                # 1 cm proud outside and 1 cm inside the wall's inner face (flush with it, the two flickered in the hall),
                # and down into the slab's chamfer like the side walls' bands.
                bevel_box(p, (x + sx * .01, (ya + yb) / 2, .635), (.04, (yb - ya) / 2 - .003, .365), vary(CHARCOAL, rng, .15), METAL, .01)
    # A painted steel liner behind the cladding: its 1 cm panel joints, and the 2 cm under the gables' tops, looked
    # straight into the hall (and let daylight in). The side liners leave the clerestory band open for its windows.
    for s in (-1, 1):
        for zc, hz in ((2.45, 2.15), (5.6, .2)):
            bevel_box(p, (0, s * 6.915, zc), (hx - .02, .005, hz), vary(WHITE, rng, .03), PAINT, .002)
    for sx in (-1, 1):
        x = sx * (hx - .085)
        spans = ((-hy + .01, hy - .01, .3),) if sx < 0 else ((-hy + .01, -3.0, .3), (3.0, hy - .01, .3), (-3.0, 3.0, 5.0))
        for y0, y1, z0 in spans:
            for ya, yb in ((y0, min(y1, 0.0)), (max(y0, 0.0), y1)):  # split at the ridge, so each piece is a plane
                if yb - ya > .01:
                    pts = [(x - .005 if xb == 0 else x + .005, yy, z0 if zb == 0 else roof_z(yy) + .02)
                           for zb in (0, 1) for yy in (ya, yb) for xb in (0, 1)]
                    hexa(p, pts, vary(WHITE, rng, .03), PAINT)
    for s in (-1, 1):
        # Jambs and their hazard bands down to the ground: outside the slab they began 30 cm up, over nothing. The bands
        # lie on the jamb's face (16 cm across, 2 cm proud); with width and depth swapped they were fins 16 cm deep.
        bevel_box(p, (hx + .02, s * 3.08, 2.5), (.06, .08, 2.5), CHARCOAL, METAL, .02)
        stripes(p, (hx + .085, s * 3.08, 0.0), (hx + .085, s * 3.08, 1.2), .16, .02, 6, (RED, WHITE_PURE), (REDS, PAINT), (1, 0, 0))
    bevel_box(p, (hx + .02, 0, 5.04), (.06, 3.16, .08), CHARCOAL, METAL, .02)
    # The doors' track bolted to the header and, past it, on brackets to the wall (it hung 2 cm clear of everything).
    strut(p, (hx + .15, -6.4, 5.22), (hx + .15, 6.4, 5.22), .1, .14, SLATE, METAL, (1, 0, 0))
    for y in (-5.6, -4.2, 4.2, 5.6):
        bevel_box(p, (hx + .04, y, 5.22), (.04, .04, .05), SLATE, METAL, .008)
    for s in (-1, 1):
        y0 = s * 4.6
        bevel_box(p, (hx + .2, y0, 2.55), (.04, 1.55, 2.47), RED, REDS, .02)  # hung from the track, 8 cm over the ground
        for z in (.6, 2.6, 4.6):
            bevel_box(p, (hx + .25, y0, z), (.015, 1.5, .06), RED_DEEP, REDS, .006)
        strut(p, (hx + .25, y0 - 1.45, .7), (hx + .25, y0 + 1.45, 4.5), .02, .08, WHITE_PURE, PAINT, (1, 0, 0))
        for dy in (-1.1, 1.1):
            torus(p, (hx + .17, y0 + dy, 5.12), .07, .02, ASH, METAL, 10, 4, 'x')
            # A hanger from the door's top to the roller's axle (the door hung 1 cm under its rollers, on nothing).
            bevel_box(p, (hx + .2, y0 + dy, 5.065), (.012, .03, .065), SLATE, METAL, .004)
            tube(p, [(hx + .15, y0 + dy, 5.12), (hx + .21, y0 + dy, 5.12)], .012, SLATE, METAL, 6)
        bevel_box(p, (hx + .27, y0 - s * 1.2, 1.2), (.03, .03, .2), GOLD, GILT, .008)
    gable_roof(p, (0, 0, eave), 2 * hx, 2 * hy, rise, CHARCOAL, METAL, .3, .15, 0.0)
    # The ridge roll runs 2 cm past the slabs' ends, so its end caps do not share their plane.
    tube(p, [(-hx - .32, 0, eave + rise + .15), (hx + .32, 0, eave + rise + .15)], .09, SLATE, METAL, 8)
    slope = rise / hy
    for s in (-1, 1):
        for x in np.arange(-5.1, 5.11, .6):
            a = (x, s * .15, eave + rise - slope * .15 + .17)
            b = (x, s * 7.25, eave + rise - slope * 7.25 + .17)
            strut(p, a, b, .03, .04, SLATE, METAL, (0, 0, 1))
        for x0 in (-3.2, 1.4):
            corners = [(x0, s * 1.6), (x0 + 1.6, s * 1.6), (x0 + 1.6, s * 4.2), (x0, s * 4.2)]
            pts = [(cx, cy, eave + rise - slope * abs(cy) + .205) for cx, cy in corners]
            polygon(p, pts, BLUE_PALE, GLASS, toward=(0, s * slope, 1))
            # A steel curb round each skylight, so the glass sits in a frame on the roof instead of hovering over it.
            normal = (0, s * slope, 1)
            for k, ((ax, ay), (bx, by)) in enumerate(zip(corners, corners[1:] + corners[:1])):
                za, zb = eave + rise - slope * abs(ay) + .185, eave + rise - slope * abs(by) + .185
                strut(p, (ax, ay, za), (bx, by, zb), .06, .07 - .004 * (k % 2), SLATE, METAL, normal)  # corners lap, unshared
        tube(p, [(-5.3, s * 7.32, eave - .06), (5.3, s * 7.32, eave - .06)], .07, CHARCOAL, METAL, 8)
        for x in (-5.0, 5.0):
            # A swan neck brings each downpipe from the gutter back to the wall, where brackets hold it.
            tube(p, [(x * .98, s * 7.32, eave - .1), (x * .98, s * 7.32, eave - .3), (x * .98, s * 7.06, eave - .55),
                     (x * .98, s * 7.06, .35)], .05, CHARCOAL, METAL, 8)
            for z in (1.2, 3.2):
                bevel_box(p, (x * .98, s * 7.04, z), (.06, .04, .02), CHARCOAL, METAL, .005)
    cylinder(p, (-2.0, 0, eave + rise), .3, .4, SLATE, METAL, 12)
    cylinder(p, (-2.0, 0, eave + rise + .4), .45, .05, CHARCOAL, METAL, 12, .2)
    c = np.array([hx + .06, 0, 6.35])
    torus(p, c, .38, .06, GOLD, GILT, 32, 6, 'x')
    for j in range(10):
        a = j / 10 * 2 * math.pi
        bevel_box(p, c + (.0, math.cos(a) * .5, math.sin(a) * .5), (.05, .07, .07), GOLD, GILT, .015, 0.0)
    tube(p, [c - (.04, 0, 0), c + (.04, 0, 0)], .13, GOLD_PALE, GILT, 12)
    # Interior.
    bevel_box(p, (-4.4, 0, .98), (.45, 2.6, .04), SLATE, METAL, .01)
    for y in (-2.4, 0, 2.4):
        for dx in (-.38, .38):
            strut(p, (-4.4 + dx, y, .3), (-4.4 + dx, y, .94), .06, .06, CHARCOAL, METAL)
    bevel_box(p, (-4.4, 1.6, 1.1), (.09, .07, .08), GOLD, GILT, .015)
    tube(p, [(-4.32, 1.6, 1.1), (-4.1, 1.6, 1.1)], .015, GOLD_PALE, GILT, 6)  # the vise's screw handle, out of its jaw
    bevel_box(p, (-4.89, 0, 2.2), (.02, 2.0, .7), CHARCOAL, DARK, .005)  # the tool board, on the back wall's liner
    for k in range(9):
        y = -1.7 + k * .42
        strut(p, (-4.86, y, 1.75 + .1 * (k % 3)), (-4.86, y, 2.55), .03, .02, ASH if k % 2 else GOLD_PALE, METAL if k % 2 else GILT, (1, 0, 0))
    for x in (-2.4, 0.0, 2.4):
        tube(p, [(x, 0, eave + rise - .2), (x, 0, 5.2)], .01, CHARCOAL, METAL, 4)
        cylinder(p, (x, 0, 4.95), .28, .25, CHARCOAL, METAL, 12, .08)
        disc(p, (x, 0), .25, LIGHT_WARM, GLOW, 12, 4.947, up=False)  # 3 mm under the shade's rim, not in its plane
    bevel_box(p, (2.8, -4.5, .9), (.6, .6, .6), vary(RED, rng, .05), REDS, .04)
    bevel_box(p, (2.0, -5.2, .65), (.35, .35, .35), vary(WHITE_PURE, rng, .05), PAINT, .03)
    bevel_box(p, (-1.0, 5.6, .35), (2.5, .5, .05), CHARCOAL, DARK, .01)
    return weather(p, 431, reach=1.2, depth=.35)


def pipe_rack():
    """A Foundry pipe rack: four steel bents on concrete footings with two tiers, longitudinal ties and
    cross-bracing, carrying steam, water and insulated lines (white with gold cladding bands, red, black,
    brass instrument air) and a cable tray; flanges, pipe shoes, a valve with a gold handwheel, and one
    line dropping to the ground. 2 x 10 x 4, lines along y."""
    rng = np.random.default_rng(441)
    p = Part('SM_CN_PipeRack', (METAL, PAINT, REDS, GILT, STONE, DARK))
    bents = (-4.2, -1.4, 1.4, 4.2)
    for y in bents:
        for x in (-.85, .85):
            bevel_box(p, (x, y, .12), (.25, .25, .12), vary(ASH, rng, .08), STONE, .03)
            ibeam(p, (x, y, .24), (x, y, 3.95), .2, .18, CHARCOAL, METAL, (1, 0, 0))
        for z in (2.3, 3.5):
            ibeam(p, (-1.0, y, z), (1.0, y, z), .2, .16, CHARCOAL, METAL)
    for x in (-.85, .85):
        for z in (1.2, 3.9):
            strut(p, (x, -4.3, z), (x, 4.3, z), .08, .08, SLATE, METAL, (1, 0, 0))
        for y0, y1 in ((-4.2, -1.4), (1.4, 4.2)):
            # The X's braces lap, one each side of the column web's plane (in one plane they flickered at the crossing).
            strut(p, (x - .03, y0, .4), (x - .03, y1, 2.2), .06, .06, SLATE, METAL, (1, 0, 0))
            strut(p, (x + .03, y1, .4), (x + .03, y0, 2.2), .06, .06, SLATE, METAL, (1, 0, 0))
    lines = ((2.4, -.7, .12, CHARCOAL, METAL), (2.4, -.33, .18, WHITE_PURE, PAINT), (2.4, .1, .1, RED, REDS),
             (2.4, .46, .15, WHITE_PURE, PAINT), (2.4, .8, .05, GOLD_PALE, GILT), (3.6, -.6, .16, CHARCOAL, METAL), (3.6, -.15, .12, RED, REDS))
    for base, x, r, colour, slot in lines:
        z = base + r
        tube(p, [(x, -5.0, z), (x, 5.0, z)], r, colour, slot, 12)
        for y in bents:
            bevel_box(p, (x, y, base + .03), (r * .7, .08, .03), SLATE, METAL, .006)
        if r > .09:
            for y in (-2.8, 0.0, 2.8):
                tube(p, [(x, y - .03, z), (x, y + .03, z)], r + .04, SLATE, METAL, 12)
        if colour is WHITE_PURE:
            for y in np.arange(-4.6, 4.61, .9):
                tube(p, [(x, y - .02, z), (x, y + .02, z)], r + .008, GOLD_PALE, GILT, 12)
    strut(p, (.3, -5.0, 3.62), (.85, -5.0, 3.62), .02, .04, SLATE, METAL, (0, 1, 0))
    for x in (.3, .85):
        strut(p, (x, -5.0, 3.68), (x, 5.0, 3.68), .02, .14, SLATE, METAL, (1, 0, 0))
    bevel_box(p, (.575, 0, 3.61), (.275, 5.0, .01), SLATE, METAL, .004)  # the cable tray's floor
    for x in np.linspace(.38, .77, 5):  # the cables end a centimetre inside the tray's ends, not in their planes
        tube(p, [(x, -4.99, 3.648), (x, 4.99, 3.648)], .03, BLACK, DARK, 6)  # resting in the tray (they floated 1 cm over it)
    c = np.array([.1, 1.0, 2.5])
    tube(p, [c - (0, .12, 0), c + (0, .12, 0)], .14, CHARCOAL, METAL, 12)
    tube(p, [c, c + (0, 0, .35)], .03, ASH, METAL, 6)
    torus(p, c + (0, 0, .36), .16, .015, GOLD, GILT, 20, 5, 'z')
    for j in range(4):
        a = j / 4 * 2 * math.pi
        tube(p, [c + (0, 0, .36), c + (math.cos(a) * .15, math.sin(a) * .15, .36)], .01, GOLD, GILT, 4)
    drop = bezier((-.7, 4.4, 2.52), (-.7, 5.0, 2.52), (-.7, 4.9, 2.4), (-.7, 4.9, 1.8), 6)
    # A size down from the main it branches from: the same radius ran coaxial inside it and the two skins flickered.
    tube(p, [tuple(q) for q in drop] + [(-.7, 4.9, .3)], .105, CHARCOAL, METAL, 12)
    bevel_box(p, (-.7, 4.9, .15), (.25, .25, .15), vary(ASH, rng, .06), STONE, .03)
    return weather(p, 441, reach=1.0)


# ---------------------------------------------------------------- the Spine Pylons

def pylon():
    """A Spine Pylon: a white stone plinth, an equipment house in riveted white panels with a steel door
    at the front (+x, where Physis relights it), louvred vents and a red band, then a tapering black
    steel lattice mast (angle legs, girts, X-bracing, gusset plates) with two courses of white panels,
    and a gold crown whose claws hold a light-blue crystal at the top. No light of its own: it reads
    drained until the scenario lights it and SM_CN_PylonBeam rises from the crystal. 5 x 5 x 18."""
    rng = np.random.default_rng(451)
    p = Part('SM_CN_Pylon', (STONE, METAL, PAINT, REDS, GILT, GLASS))
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(p, (sx * 1.25, sy * 1.25, .15), (1.245, 1.245, .15), vary(WHITE, rng, .05), STONE, .03)
    bevel_box(p, (0, 0, .45), (2.2, 2.2, .15), vary(IVORY, rng, .04), STONE, .03)
    box(p, (0, 0, 2.4), (1.44, 1.44, 1.8), BLACK, METAL)
    door = lambda u, z: abs(u) < .55 and z < 2.9  # noqa: E731
    vents = lambda u, z: abs(u) < .55 and 1.4 < z < 2.6  # noqa: E731
    clad(p, rng, 1.44, 0, (-1.44, .6), (1.44, 3.9), 3, 3, WHITE_PURE, PAINT, 1, t=.04, skip=door)
    clad(p, rng, -1.44, 0, (-1.44, .6), (1.44, 3.9), 3, 3, WHITE_PURE, PAINT, -1, t=.04)
    for s in (-1, 1):
        clad(p, rng, s * 1.44, 1, (-1.44, .6), (1.44, 3.9), 3, 3, WHITE_PURE, PAINT, s, t=.04, skip=vents)
        # The louvres fill the opening the skipped plate leaves (z 1.7-2.8); they started 20 cm low, over the plate below.
        for z in np.arange(1.78, 2.75, .12):
            strut(p, (-.45, s * 1.47, z), (.45, s * 1.47, z), .02, .07, SLATE, METAL, (0, s, 1))
        bevel_box(p, (0, s * 1.465, 2.25), (.5, .01, .55), CHARCOAL, METAL, .004)
    for s in (-1, 1):
        bevel_box(p, (0, s * 1.47, 4.0), (1.47, .03, .1), RED, REDS, .01)
        bevel_box(p, (s * 1.47, 0, 4.0), (.03, 1.47, .098), RED, REDS, .01)  # a hair lower, so the corners' tops differ
    bevel_box(p, (1.47, 0, 1.7), (.03, .5, 1.1), SLATE, METAL, .015)
    for z in (1.0, 2.4):
        bevel_box(p, (1.505, -.5, z), (.012, .03, .12), ASH, METAL, .004)
    bevel_box(p, (1.51, .38, 1.65), (.02, .02, .1), GOLD, GILT, .006)
    bevel_box(p, (1.49, 0, 2.85), (.05, .58, .05), CHARCOAL, METAL, .01)
    bevel_box(p, (0, 0, 4.2), (1.55, 1.55, .07), SLATE, METAL, .02)
    levels = (4.27, 6.3, 8.2, 10.0, 11.7, 13.3, 15.0)

    def half(z):
        return 1.35 + (.6 - 1.35) * (z - levels[0]) / (levels[-1] - levels[0])

    corners = ((1, 1), (-1, 1), (-1, -1), (1, -1))
    for z0, z1 in zip(levels, levels[1:]):
        for sx, sy in corners:
            angle_iron(p, (sx * half(z0), sy * half(z0), z0), (sx * half(z1), sy * half(z1), z1), .13, CHARCOAL, METAL, (-sx, -sy, 0))
        for k in range(4):
            (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
            strut(p, (ax * half(z0), ay * half(z0), z0), (bx * half(z1), by * half(z1), z1), .06, .05, SLATE, METAL)
            strut(p, (bx * half(z0), by * half(z0), z0), (ax * half(z1), ay * half(z1), z1), .06, .05, SLATE, METAL)
    for z in levels[1:]:
        h = half(z)
        for k in range(4):
            (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
            strut(p, (ax * h, ay * h, z), (bx * h, by * h, z), .08, .08, CHARCOAL, METAL)
        for sx, sy in corners:
            bevel_box(p, (sx * h, sy * h, z), (.09, .09, .1), SLATE, METAL, .012)
            rivets(p, [(sx * (h + .095), sy * h, z)], (sx, 0, 0), .03, ASH, METAL)
    for z0, z1 in ((levels[1], levels[2]), (levels[3], levels[4])):
        for k in range(4):
            (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
            inset = .93
            pts = []
            # Neighbouring panels end 4 mm apart in height: where they cross at a corner their tops shared a plane.
            for zb, zz in ((0, z0 + .12 + .004 * (k % 2)), (1, z1 - .12 - .004 * (k % 2))):
                h = half(zz) * inset
                for yb in (0, 1):
                    for xb in (0, 1):
                        cx, cy = (ax, ay) if xb == 0 else (bx, by)
                        nx, ny = (ax + bx) / 2, (ay + by) / 2
                        d = .02 if yb else -.02
                        pts.append((cx * h + nx * d, cy * h + ny * d, zz))
            hexa(p, pts, vary(WHITE_PURE, rng, .05), PAINT)
    tube(p, [(1.36, 1.2, 4.27), (.62, .55, 15.0)], .035, BLACK, METAL, 6)
    bevel_box(p, (0, 0, 15.06), (.85, .85, .06), SLATE, METAL, .02)
    cylinder(p, (0, 0, 15.12), .7, .12, GOLD, GILT, 24)
    for j in range(4):
        a = j / 4 * 2 * math.pi + math.pi / 4
        tube(p, [(math.cos(a) * .6, math.sin(a) * .6, 15.2), (math.cos(a) * .7, math.sin(a) * .7, 15.5)], .045, GOLD, GILT, 6)
    torus(p, (0, 0, 15.5), .75, .06, GOLD, GILT, 32, 8, 'z')
    for j in range(6):
        a = j / 6 * 2 * math.pi
        d = np.array([math.cos(a), math.sin(a), 0])
        claw = bezier(d * .75 + (0, 0, 15.5), d * 1.0 + (0, 0, 16.2), d * .8 + (0, 0, 17.0), d * .5 + (0, 0, 17.35), 8)
        tube(p, claw, np.linspace(.055, .025, 8), GOLD, GILT, 6)
        blob(p, d * .49 + (0, 0, 17.38), .04, GOLD_PALE, GILT, 1, 0.0, j)
    prism(p, (0, 0, 16.25), (0, 0, 18.0), .5, BLUE_PALE, GLASS, 6, .38)
    prism(p, (0, 0, 16.25), (0, 0, 15.62), .5, mix(BLUE_PALE, WHITE_COOL, .4), GLASS, 6, .9)
    return weather(p, 451, reach=1.5)


BEAM_HEIGHT = 690.0  # pylon crown to past the Spine's surface (axis at 706 m): the README's fixed length


def pylon_beam():
    """The light a relit pylon sends up to the Spine: a white-blue column of light, its brightness
    rippling along its length so it reads as flowing. Radius 2, 690 m tall, base pivot."""
    p = Part('SM_CN_PylonBeam', (GLOW,))
    zs = np.concatenate([np.arange(0, BEAM_HEIGHT, 10.0), [BEAM_HEIGHT]])
    profile = [(2.0 if z < BEAM_HEIGHT - 60 else 2.0 - .6 * (z - BEAM_HEIGHT + 60) / 60, z) for z in zs]
    sides = 16
    cols = []
    for r, z in profile:
        t = .5 + .5 * math.sin(z / 23.0) * math.cos(z / 57.0)
        c = mix(LIGHT_BLUE, LIGHT_WHITE, .35 + .5 * t)
        cols.extend([c] * sides)
    lathe(p, profile, cols, GLOW, sides)
    disc(p, (0, 0), 2.0, mix(LIGHT_BLUE, LIGHT_WHITE, .6), GLOW, sides, 0.0, up=False)
    disc(p, (0, 0), profile[-1][0], LIGHT_BLUE, GLOW, sides, BEAM_HEIGHT, up=True)
    return p


# ---------------------------------------------------------------- the Lightform Spire

SPIRE_SIDES = 12
SPIRE_RINGS = (.3, 9.3, 18, 30, 45, 60, 80, 100, 125, 150, 175, 200, 225, 250, 270, 288, 300)
SPIRE_TIP = 320.0
SPIRE_DOOR = (5.0, 9.3)  # half-width and top of the doorway in the front facet (+x); the floor is z 0.3


def spire_radius(z):
    """Outer circumradius of the Spire's faceted shell at height z (corners; the facet centres are
    cos 15 deg of it)."""
    return 22.5 * (1 - min(z, SPIRE_TIP) / SPIRE_TIP) ** .75


def spire_inner(z):
    return spire_radius(z) - (1.0 - .4 * z / SPIRE_TIP)


def spire_twist(z):
    """Degrees the facets have turned at height z: none up to the doorway's top, then a quarter facet."""
    return 0.0 if z <= SPIRE_DOOR[1] else 7.5 * (z - SPIRE_DOOR[1]) / (SPIRE_RINGS[-1] - SPIRE_DOOR[1])


def spire_corner(z, j, r=None):
    a = math.radians(-15.0 + 30.0 * j + spire_twist(z))
    r = spire_radius(z) if r is None else r
    return np.array([math.cos(a) * r, math.sin(a) * r, z])


def spire():
    """The Lightform Spire: a hollow, twelve-faceted tower of light-blue hardened light (glass) tapering
    from a white stone plinth to a point 320 m up, turning a quarter facet as it rises. White and gold
    ribs run up its corners; inside, veins and rings of light-blue light line the walls and a heart of
    light hangs under the tip; four gold rings float around its upper half and crystal spurs lean on its
    base. The doorway (10 m wide, 9 m tall, floor at z 0.3) is in the front facet (+x), where
    SM_CN_SpireGate stands; the hall inside is about 41 m across. Base radius 24, 320 tall."""
    rng = np.random.default_rng(461)
    p = Part('SM_CN_Spire', (GLASS, STONE, GILT, GLOW))
    n = SPIRE_SIDES
    half_w, door_top = SPIRE_DOOR
    glass = lambda z: mix(BLUE_PALE, WHITE_COOL, min(.85, .1 + z / 330.0))  # noqa: E731
    outer = [[spire_corner(z, j) for j in range(n)] for z in SPIRE_RINGS]
    inner = [[spire_corner(z, j, spire_inner(z)) for j in range(n)] for z in SPIRE_RINGS[:-1]]
    centre = lambda z: np.array([0., 0., z])  # noqa: E731

    def facet(a, b, c, d, toward, colour):
        polygon(p, [a, b, c, d], colour, GLASS, toward=toward)

    def door_point(ring, k, y):
        """The point of facet 0's edge on ring k (outer or inner) where the lateral offset is y."""
        a, b = ring[k][0], ring[k][1]
        t = (y - a[1]) / (b[1] - a[1])
        return a + (b - a) * t

    for k in range(len(SPIRE_RINGS) - 1):
        z0, z1 = SPIRE_RINGS[k], SPIRE_RINGS[k + 1]
        for j in range(n):
            jn = (j + 1) % n
            mid = (outer[k][j] + outer[k][jn] + outer[k + 1][j] + outer[k + 1][jn]) / 4
            out_dir = mid - centre(mid[2])
            if k == 0 and j == 0:  # the doorway: two jambs, their reveals and the soffit above
                lo, hi = door_point(outer, 0, -half_w), door_point(outer, 1, -half_w)
                facet(outer[0][0], lo, hi, outer[1][0], out_dir, glass(z0))
                lo2, hi2 = door_point(outer, 0, half_w), door_point(outer, 1, half_w)
                facet(lo2, outer[0][1], outer[1][1], hi2, out_dir, glass(z0))
                ilo, ihi = door_point(inner, 0, -half_w), door_point(inner, 1, -half_w)
                ilo2, ihi2 = door_point(inner, 0, half_w), door_point(inner, 1, half_w)
                facet(inner[0][0], ilo, ihi, inner[1][0], -out_dir, glass(z0))
                facet(ilo2, inner[0][1], inner[1][1], ihi2, -out_dir, glass(z0))
                facet(lo, ilo, ihi, hi, (0, 1, 0), glass(z0))
                facet(lo2, ilo2, ihi2, hi2, (0, -1, 0), glass(z0))
                facet(hi, hi2, ihi2, ihi, (0, 0, -1), glass(z1))
                continue
            facet(outer[k][j], outer[k][jn], outer[k + 1][jn], outer[k + 1][j], out_dir, glass(z0))
            if k < len(inner) - 1:
                facet(inner[k][j], inner[k][jn], inner[k + 1][jn], inner[k + 1][j], -out_dir, glass(z0))
    tip = np.array([0., 0., SPIRE_TIP])
    apex = np.array([0., 0., 298.0])
    for j in range(n):
        jn = (j + 1) % n
        a, b = outer[-1][j], outer[-1][jn]
        polygon(p, [a, b, tip], glass(SPIRE_TIP), GLASS, toward=(a + b) / 2 - centre(a[2]))
        a, b = inner[-1][j], inner[-1][jn]
        polygon(p, [a, b, apex], glass(SPIRE_TIP), GLASS, toward=centre(a[2]) - (a + b) / 2)
    # Ribs on the corners, white and gold by turns, standing a little proud of the glass.
    for j in range(n):
        pts = [spire_corner(z, j, spire_radius(z) + .22) for z in SPIRE_RINGS] + [spire_corner(SPIRE_TIP - 6, j, spire_radius(SPIRE_TIP - 6) + .1)]
        radii = [max(.12, .45 * (1 - z / 360.0)) for z in SPIRE_RINGS] + [.1]
        if j % 2:
            tube(p, pts, radii, GOLD, GILT, 6)
        else:
            tube(p, pts, radii, WHITE_COOL, STONE, 6)
    # Veins and rings of light lining the inside of the walls.
    vein_colour = mix(LIGHT_BLUE, LIGHT_WHITE, .25)
    for j in range(n):
        zs = [z for z in SPIRE_RINGS[:-1] if z > (door_top + .3 if j in (0, 1) else 2.0)]
        zs = ([door_top + .4] if j in (0, 1) else [2.0]) + zs
        tube(p, [spire_corner(z, j, spire_inner(z) - .25) for z in zs], .16, vein_colour, GLOW, 6)
    for z in (30.0, 60.0, 100.0, 150.0, 200.0, 250.0):
        loop = [spire_corner(z, j, spire_inner(z) - .25) for j in range(n)]
        tube(p, loop + [loop[0]], .12, LIGHT_BLUE, GLOW, 6, cap=False)
    prism(p, (0, 0, 284.0), (0, 0, 296.0), 1.5, LIGHT_WHITE, GLOW, 6, .5)
    prism(p, (0, 0, 284.0), (0, 0, 268.0), 1.5, LIGHT_BLUE, GLOW, 6, .7)
    # The floating rings, each with a band of light on its inner face, and shards that keep them company.
    for z in (110.0, 170.0, 222.0, 262.0):
        r = spire_radius(z) * math.cos(math.radians(15)) + 4.0
        torus(p, (0, 0, z), r, .42, GOLD, GILT, 64, 8, 'z')
        torus(p, (0, 0, z), r - .5, .13, LIGHT_BLUE, GLOW, 64, 6, 'z')
        for k in range(3):
            a = rng.uniform(0, 2 * math.pi)
            c = np.array([math.cos(a) * (r + 1.5), math.sin(a) * (r + 1.5), z + rng.uniform(-6, 6)])
            prism(p, c - (0, 0, 1.2), c + (0, 0, 1.6), rng.uniform(.35, .6), mix(BLUE_PALE, WHITE_COOL, .3), GLASS, 6, .4)
    # Crystal spurs leaning on the base, away from the doorway.
    for deg, length, lean in ((70, 26, .9), (112, 38, 1.0), (150, 30, 1.1), (180, 44, 1.0), (212, 28, .9), (250, 36, 1.1), (290, 24, 1.0)):
        a = math.radians(deg + rng.uniform(-6, 6))
        d = np.array([math.cos(a), math.sin(a), 0.])
        base = d * 23.2 + (0, 0, .3)
        top = d * (spire_radius(length) * math.cos(math.radians(15)) + lean) + (0, 0, length)
        prism(p, base, top, rng.uniform(1.4, 2.2), mix(BLUE_PALE, WHITE_COOL, rng.uniform(0, .4)), GLASS, 6, .22)
    # Plinth, footing course and floor. The rings are curved blocks (arc_blocks) whose joints follow the circle within a
    # centimetre: straight-chord rings of different counts left 6-10 cm cracks at r 10 and 16 and overlapped (and
    # flickered) at r 21, across the doorway's threshold. The gold inlays cover what mismatch is left.
    def alternate(a, b, spread):
        turn = iter(range(10 ** 6))
        return lambda: vary(a if next(turn) % 2 else b, rng, spread)

    def course(r0, r1, blocks, sub, colour, start=0.0):
        """One ring of `blocks` curved slabs, 1.2 cm joints at the outer edge; start (radians) staggers the joints."""
        rm = (r0 + r1) / 2
        arc_blocks(p, r0, r1, 0.0, .3, ((start, start + 2 * math.pi),), 2 * math.pi * rm / blocks, colour, STONE, 0.0, .012 / r1, sub)
    course(21.0, 24.0, 48, 2, alternate(WHITE, IVORY, .04))
    annulus(p, (0, 0), 23.25, 23.45, GOLD, GILT, 72, .302)
    annulus(p, (0, 0), 20.97, 21.03, GOLD, GILT, 192, .302)
    for j in range(1, n):
        a, b = spire_corner(.3, j, spire_radius(.3) + .35), spire_corner(.3, j + 1, spire_radius(.3) + .35)
        ai, bi = spire_corner(.3, j, spire_radius(.3) - .3), spire_corner(.3, j + 1, spire_radius(.3) - .3)
        hexa(p, [ai, bi, a, b, ai + (0, 0, 1.6), bi + (0, 0, 1.6), a + (0, 0, 1.6), b + (0, 0, 1.6)], vary(WHITE_COOL, rng, .04), STONE)
    cylinder(p, (0, 0, 0), 4.0, .3, vary(WHITE, rng, .03), STONE, 48, smooth=False)
    for r0, r1, segs, sub in ((4.0, 10.0, 16, 3), (10.0, 16.0, 24, 4), (16.0, 21.0, 32, 3)):
        course(r0, r1, segs, sub, alternate(WHITE_COOL, WHITE, .04), math.pi / segs)
        annulus(p, (0, 0), r0 - .06, r0 + .06, GOLD, GILT, segs * 4, .302)
    annulus(p, (0, 0), 2.9, 3.05, LIGHT_BLUE, GLOW, 48, .303)
    disc(p, (0, 0), 1.6, mix(LIGHT_BLUE, LIGHT_WHITE, .5), GLOW, 24, .304)
    return p


def spire_gate():
    """The Spire's gate: two white marble posts in three courses with gold capitals and gold-framed
    light-blue glass inlays split by a line of light, a semicircular arch of voussoirs with a gilt
    soffit, lines of light along its intrados, a gold keystone, and spandrels under a gold cornice.
    Clear opening 6.8 wide and 8.4 tall, the road through along x. 2 x 10 x 9."""
    rng = np.random.default_rng(471)
    p = Part('SM_CN_SpireGate', (STONE, GILT, GLASS, GLOW))
    bevel_box(p, (0, 0, .08), (1.0, 3.4, .08), vary(WHITE, rng, .03), STONE, .02)
    for s in (-1, 1):
        y = s * 4.2
        for z0, z1 in ((0, 1.6), (1.61, 3.2), (3.21, 4.8)):
            bevel_box(p, (0, y, (z0 + z1) / 2), (1.0, .8, (z1 - z0) / 2), vary(WHITE_COOL, rng, .04), STONE, .04)
        # Mortar 2 cm behind the 1 cm course joints (open, the one at 1.6 m let daylight through at eye height); it stops
        # 5 cm under the top, where its chamfers would lie in the stones' own.
        bevel_box(p, (0, y, 2.48), (.98, .78, 2.27), tone(ASH, 1.4), STONE, .01)
        bevel_box(p, (0, y, 4.9), (1.05, .85, .1), GOLD, GILT, .03)
        bevel_box(p, (0, y, .1), (1.04, .84, .1), vary(WHITE, rng, .03), STONE, .03)
        for sx in (-1, 1):
            x = sx * 1.004
            polygon(p, [(x, y - .3, .7), (x, y + .3, .7), (x, y + .3, 4.2), (x, y - .3, 4.2)], BLUE_PALE, GLASS, toward=(sx, 0, 0))
            for (ya, za), (yb, zb) in (((y - .34, .66), (y + .34, .66)), ((y - .34, 4.24), (y + .34, 4.24))):
                strut(p, (x, ya, za), (x, yb, zb), .03, .04, GOLD, GILT, (1, 0, 0))
            for yy in (y - .34, y + .34):  # 2 mm shallower than the rails, so their corner laps share no face plane
                strut(p, (x, yy, .66), (x, yy, 4.24), .03, .038, GOLD, GILT, (1, 0, 0))
            strut(p, (x + sx * .006, y, .75), (x + sx * .006, y, 4.15), .03, .008, LIGHT_BLUE, GLOW, (1, 0, 0))
    arch(p, (0, 0, .2), 6.8, 8.2, .6, 1.8, WHITE_COOL, STONE, segments=13)
    arch(p, (0, 0, .2), 6.7, 8.15, .05, 1.84, GOLD, GILT, segments=13)
    for sx in (-1, 1):
        ring = [(sx * .93, -math.cos(a) * 3.3, 5.0 + math.sin(a) * 3.3) for a in np.linspace(0, math.pi, 25)]
        tube(p, ring, .035, LIGHT_BLUE, GLOW, 6)
    a0, a1 = math.radians(86), math.radians(94)
    hexa(p, [(x, -math.cos(a) * r, 5.0 + math.sin(a) * r) for r in (3.32, 4.0) for a in (a0, a1) for x in (-1.0, 1.0)], GOLD, GILT)
    for s in (-1, 1):
        zs = (5.0, 5.9, 6.8, 7.6)
        for z0, z1 in zip(zs, zs[1:]):
            y0, y1 = math.sqrt(max(0, 16 - (z0 - 5.0) ** 2)) - .02, math.sqrt(max(0, 16 - (z1 - 5.0) ** 2)) - .02
            pts = [(x, s * yy, zz) for zz, yy_in in ((z0, y0), (z1, y1)) for yy in (yy_in, 5.0) for x in (-.95, .95)]
            hexa(p, pts, vary(WHITE_COOL, rng, .04), STONE)
        bevel_box(p, (0, s * 4.03, 7.68), (1.05, 1.02, .08), GOLD, GILT, .02)
    return weather(p, 471, reach=1.2, depth=.3)


def light_platform():
    """A floating platform of the Trial of Light: a hexagon of white hardened-light tiles around a hub,
    the seams between them lines of light-blue light, a gold rim, and under it a light-blue crystal keel
    glowing at its point. Hexagon radius 5 with flat edges square to +-x (corners at +-y): the climb yaws each
    platform along the ramp that arrives at it, so that ramp meets a flat edge 4.33 m out, where its buried end leaves
    an 18 cm step (28 cm on the 1.6x landing); at a corner it was a 40 cm wall (58 cm). 0.8 thick, walk surface z 0."""
    rng = np.random.default_rng(481)
    p = Part('SM_CN_LightPlatform', (STONE, GILT, GLASS, GLOW))
    R, rim, hub, top, bottom = 5.0, 4.72, 2.0, 0.0, -.25

    def corner(r, j, z):
        a = math.radians(60.0 * j + 30.0)
        return np.array([math.cos(a) * r, math.sin(a) * r, z])

    for j in range(6):
        pts = [corner(r, j + xb, z) for z in (bottom, top) for r in (hub, rim) for xb in (0, 1)]
        mid = np.mean(pts, 0)
        pts = [q + (mid - q) * np.array([.004, .004, 0]) for q in pts]
        hexa(p, pts, vary(WHITE_COOL, rng, .03), STONE)
        rim_pts = [corner(r, j + xb, z) for z in (-.32, top) for r in (rim, R) for xb in (0, 1)]
        hexa(p, rim_pts, GOLD, GILT)
        a, b = corner(hub, j, .002), corner(rim, j, .002)
        strut(p, a - (0, 0, .004), b - (0, 0, .004), .03, .008, LIGHT_BLUE, GLOW)
    cylinder(p, (0, 0, bottom), hub - .01, -bottom, vary(WHITE, rng, .03), STONE, 6, smooth=False, yaw=30.0)
    annulus(p, (0, 0), hub - .03, hub + .03, LIGHT_BLUE, GLOW, 6, .002, 30.0)
    disc(p, (0, 0), .55, mix(LIGHT_BLUE, LIGHT_WHITE, .4), GLOW, 6, .002, 30.0)
    annulus(p, (0, 0), rim - .07, rim - .03, LIGHT_BLUE, GLOW, 6, .002, 30.0)
    # The keel reaches up to the tiles' undersides (it hung 5 cm under them, held by nothing).
    cylinder(p, (0, 0, -.8), 1.3, .55, BLUE_PALE, GLASS, 6, 4.6, False, 30.0)
    disc(p, (0, 0), 1.1, LIGHT_BLUE, GLOW, 6, -.803, 30.0, up=False)
    return p


def light_ramp():
    """A ramp of hardened light between platforms: six white tiles with lines of light at their joints
    and along both edges, a raised gold lip on each side and a light-blue crystal spine beneath. 12 on x,
    3 wide, rising 4 m; the origin is the top surface of its low end."""
    rng = np.random.default_rng(491)
    p = Part('SM_CN_LightRamp', (STONE, GILT, GLASS, GLOW))
    run, rise, half = 12.0, 4.0, 1.5
    ztop = lambda x: rise * x / run  # noqa: E731
    thick = .47
    xs = np.linspace(0, run, 7)
    for a, b in zip(xs, xs[1:]):
        a2, b2 = a + .006 if a > 0 else a, b - .006 if b < run else b
        pts = [(x, y, ztop(x) - (thick if zb == 0 else 0)) for zb in (0, 1) for y in (-1.35, 1.35) for x in (a2, b2)]
        hexa(p, pts, vary(WHITE_COOL, rng, .03), STONE)
        if a > 0:
            strut(p, (a, -1.3, ztop(a) - .002), (a, 1.3, ztop(a) - .002), .03, .008, LIGHT_BLUE, GLOW, (-rise, 0, run))
    for s in (-1, 1):
        pts = [(x, s * yy, ztop(x) + (.03 if zb else -.5)) for zb in (0, 1) for yy in (1.35, half) for x in (0.0, run)]
        hexa(p, pts, GOLD, GILT)
        strut(p, (0, s * 1.12, .002), (run, s * 1.12, rise + .002), .04, .008, LIGHT_BLUE, GLOW, (-rise, 0, run))
    keel = [(x, y, ztop(x) + dz) for dz, w, x0, x1 in ((-.77, .4, .5, run - .5), (-.47, .9, 0.0, run)) for y in (-w, w) for x in (x0, x1)]
    hexa(p, keel, BLUE_PALE, GLASS)
    return p


def lattice():
    """A Light Lattice: bars of hardened light (light-blue uprights, white rails) in gold emitter cups,
    a faint light-blue membrane of hardened light between them, inside a bevelled gold frame. It opens
    when Physis Light Steps through it. 0.5 x 6 x 5, in the y-z plane."""
    p = Part('SM_CN_Lattice', (GILT, GLOW, GLASS))
    for s in (-1, 1):
        bevel_box(p, (0, s * 2.85, 2.5), (.25, .15, 2.5), GOLD, GILT, .04)
        bevel_box(p, (0, s * 2.67, 2.45), (.2, .03, 2.25), GOLD_PALE, GILT, .01)
    bevel_box(p, (0, 0, 4.85), (.25, 2.72, .15), GOLD, GILT, .04)
    bevel_box(p, (0, 0, .1), (.25, 2.72, .1), GOLD, GILT, .04)
    for z in (.22, 4.68):
        bevel_box(p, (0, 0, z), (.2, 2.68, .02), GOLD_PALE, GILT, .008)
    box(p, (0, 0, 2.45), (.008, 2.66, 2.24), BLUE_PALE, GLASS)
    for k, y in enumerate(np.arange(-2.4, 2.41, .4)):
        tube(p, [(0, y, .2), (0, y, 4.7)], .042, LIGHT_BLUE if k % 2 == 0 else mix(LIGHT_BLUE, LIGHT_WHITE, .45), GLOW, 8)
        for z, h in ((.2, .07), (4.63, .07)):
            cylinder(p, (0, y, z), .075, h, GOLD_PALE, GILT, 10)
    for z in (.95, 1.7, 2.45, 3.2, 3.95):
        tube(p, [(0, -2.66, z), (0, 2.66, z)], .026, LIGHT_WHITE, GLOW, 6)
    return p


def crown_dais():
    """The dais at the Spire's crown: a drum of white marble 1 m tall whose top is one floor out to 8.6 m (the climb's
    last ramp runs 0.5 m onto it at the top's height; over the old 0.34 and 0.67 m tiers its end hung 16 cm in the
    air), laid in three courses of curved slabs whose joints never line up, gold inlays over the course joints, a gold
    band round the riser and a step round the foot; in the middle a gold star within a ring of light-blue light.
    Radius 9, 1 tall."""
    rng = np.random.default_rng(495)
    p = Part('SM_CN_CrownDais', (STONE, GILT, GLOW))
    turn = iter(range(10 ** 6))

    def tint():
        return vary(WHITE_COOL if next(turn) % 2 else WHITE, rng, .03)
    # (inner, outer, slabs, joint offset in degrees): offsets chosen so no joint meets one of the next course.
    for r0, r1, n, start in ((1.5, 4.0, 16, 0.0), (4.0, 6.4, 24, 3.75), (6.4, 8.6, 32, 1.875)):
        a0 = math.radians(start)
        arc_blocks(p, r0 + .004, r1 - .004, 0.0, 1.0, ((a0, a0 + 2 * math.pi),), 2 * math.pi * (r0 + r1) / 2 / n, tint, STONE,
                   0.0, .012 / r1, 3)
    a0 = math.radians(.9375)
    arc_blocks(p, 8.55, 9.0, 0.0, .5, ((a0, a0 + 2 * math.pi),), 2 * math.pi * 8.78 / 48, tint, STONE, 0.0, .012 / 9.0, 2)
    for r, sides in ((1.5, 48), (4.0, 96), (6.4, 96)):  # inlays over the course joints
        annulus(p, (0, 0), r - .05, r + .05, GOLD, GILT, sides, 1.002)
    # Bands round the riser and the step, seated 6-9 mm into their faceted faces all the way round.
    lathe(p, [(8.588, .72), (8.606, .72), (8.606, .8), (8.588, .8)], GOLD, GILT, 128)
    lathe(p, [(8.994, .3), (9.006, .3), (9.006, .38), (8.994, .38)], GOLD, GILT, 128)
    cylinder(p, (0, 0, 0), 1.5, 1.0, vary(WHITE_COOL, rng, .03), STONE, 24)
    annulus(p, (0, 0), 2.6, 2.75, LIGHT_BLUE, GLOW, 48, 1.002)
    for j in range(8):
        a = j / 8 * 2 * math.pi
        tip = (math.cos(a) * 2.35, math.sin(a) * 2.35, 1.003)
        l = (math.cos(a - .35) * .7, math.sin(a - .35) * .7, 1.003)
        r = (math.cos(a + .35) * .7, math.sin(a + .35) * .7, 1.003)
        polygon(p, [(0, 0, 1.003), l, tip, r], GOLD, GILT, toward=(0, 0, 1))
    disc(p, (0, 0), .45, mix(LIGHT_BLUE, LIGHT_WHITE, .5), GLOW, 24, 1.004)
    return weather(p, 495, reach=.6, depth=.25)


# ---------------------------------------------------------------- the Spindle Docks

def cradle():
    """A docking cradle of the Spindle Docks: a concrete bed with rails and expansion joints, five steel
    frames whose curved saddles carry black rubber pads, hydraulic clamp arms (white cylinders, gold
    rods), braced columns striped red and white at the foot, walkways with railings along the top and
    lamp masts at the ends. 30 x 12 x 16, the berth along x."""
    rng = np.random.default_rng(501)
    p = Part('SM_CN_Cradle', (STONE, METAL, PAINT, REDS, GILT, DARK, GLOW))
    bevel_box(p, (0, 0, .3), (15.0, 6.0, .3), vary(ASH, rng, .05), STONE, .06)
    for x in np.arange(-10.0, 10.1, 5.0):
        box(p, (x, 0, .6), (.02, 5.98, .004), CHARCOAL, DARK)
    for y in (-3.0, 3.0):
        strut(p, (-15.0, y, .66), (15.0, y, .66), .12, .12, SLATE, METAL)
    frames = (-12.0, -6.0, 0.0, 6.0, 12.0)
    for x in frames:
        for s in (-1, 1):
            y = s * 5.4
            bevel_box(p, (x, y, 7.3), (.35, .45, 6.7), CHARCOAL, METAL, .05)
            bevel_box(p, (x, y, .7), (.55, .6, .1), SLATE, METAL, .02)
            rivets(p, [(x + dx, y + dy, .8) for dx in (-.42, .42) for dy in (-.45, .45)], (0, 0, 1), .035, ASH, METAL)
            for k in range(7):
                z = .8 + k * .2
                bevel_box(p, (x, y, z + .1), (.37, .47, .1), RED if k % 2 == 0 else WHITE_PURE, REDS if k % 2 == 0 else PAINT, .01)
            arm_a, arm_b = np.array([x, s * 5.0, 11.0]), np.array([x, s * 3.2, 9.2])
            tube(p, [arm_a, arm_a + (arm_b - arm_a) * .55], .2, WHITE_PURE, PAINT, 12)
            tube(p, [arm_a + (arm_b - arm_a) * .5, arm_b], .09, GOLD, GILT, 10)
            bevel_box(p, tuple(arm_b + (0, -s * .1, -.1)), (.4, .15, .3), BLACK, DARK, .04)
            bevel_box(p, (x, s * 5.0, 11.0), (.3, .12, .25), SLATE, METAL, .03)
        bevel_box(p, (x, 0, 1.3), (.6, 1.0, .7), CHARCOAL, METAL, .05)
        arc = [(x, -math.sin(a) * 5.0, 7.0 - math.cos(a) * 5.0) for a in np.linspace(-1.37, 1.37, 9)]
        for k, (a, b) in enumerate(zip(arc, arc[1:])):
            # Neighbouring segments 1 cm apart in width, so where they lap at a joint their flanks share no plane.
            strut(p, a, b, .5 - .01 * (k % 2), .4, SLATE, METAL, (0, 0, 1))
            m = (np.array(a) + np.array(b)) / 2
            inward = np.array([0, 0, 7.0]) + (x, 0, 0) - m
            inward[0] = 0
            inward /= np.linalg.norm(inward)
            strut(p, np.array(a) + inward * .3, np.array(b) + inward * .3, .44 - .01 * (k % 2), .16, BLACK, DARK, inward)
        for y in (-2.6, 2.6):
            strut(p, (x, y, .6), (x, y, 7.0 - math.sqrt(25 - y * y) - .2), .3, .3, SLATE, METAL, (1, 0, 0))
    for a, b in zip(frames, frames[1:]):
        for s in (-1, 1):
            y = s * 5.9
            # The braces lap at their crossing, one each side of the bracing's plane (in one plane they flickered).
            strut(p, (a, y - .07, 1.6), (b, y - .07, 7.5), .14, .14, SLATE, METAL, (0, 1, 0))
            strut(p, (b, y + .07, 1.6), (a, y + .07, 7.5), .14, .14, SLATE, METAL, (0, 1, 0))
            strut(p, (a, y, 7.5), (b, y, 7.5), .18, .18, SLATE, METAL, (0, 1, 0))
    for s in (-1, 1):
        y = s * 5.4
        bevel_box(p, (0, y, 14.3), (15.0, .45, .3), CHARCOAL, METAL, .05)
        rivets(p, [(xx, y + s * .45, 14.45) for xx in np.arange(-14.5, 14.6, 1.0)], (0, s, 0), .03, ASH, METAL)
        bevel_box(p, (0, y - s * .1, 14.64), (15.0, .55, .04), SLATE, METAL, .01)
        # The railing stands on the deck's outer edge (y +-5.82); at +-6.0 it stood 15 cm out in the air.
        for xx in np.arange(-15.0, 15.01, 1.5):
            strut(p, (xx, y + s * .42, 14.68), (xx, y + s * .42, 15.7), .05, .05, WHITE_PURE, PAINT, (1, 0, 0))
        for z in (15.2, 15.68):
            tube(p, [(-15.0, y + s * .42, z), (15.0, y + s * .42, z)], .03, WHITE_PURE, PAINT, 6)
        for xx in (-14.6, 14.6):
            tube(p, [(xx, y, 14.68), (xx, y, 15.85)], .06, SLATE, METAL, 8)
            lamp(p, (xx, y, 15.9), LIGHT_WHITE, .1)
    for z in np.arange(1.2, 14.2, .3):
        tube(p, [(12.45, -5.6, z), (12.45, -5.2, z)], .016, ASH, METAL, 5)
    for y in (-5.6, -5.2):
        tube(p, [(12.45, y, .6), (12.45, y, 14.3)], .025, ASH, METAL, 6)
    return weather(p, 501, reach=2.0, depth=.35)


def plated(part, rings, inside, base, plate, gap=.03, lift=.035, closed=True):
    """Hull plating: a dark structural skin lofted through rings, and over it one plate per cell, shrunk
    by gap and lifted by lift so every seam shows the dark skin between. plate(i, j) gives (colour, slot)
    for cell (ring i, column j), or None where a plate is missing (a wreck shows its structure there)."""
    loft(part, rings, base[0], base[1], inside, closed, smooth=False)
    rings = [np.asarray(r, np.float64) for r in rings]
    n = len(rings[0])
    for i in range(len(rings) - 1):
        for j in range(n if closed else n - 1):
            k = (j + 1) % n
            look = plate(i, j)
            if look is None:
                continue
            q = np.array([rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]])
            c = q.mean(0)
            normal = np.cross(q[1] - q[0], q[3] - q[0]) + np.cross(q[2] - q[1], q[0] - q[1])
            if np.linalg.norm(normal) < 1e-9:
                continue
            normal /= np.linalg.norm(normal)
            out = c - np.asarray(inside(c), np.float64)
            if np.dot(normal, out) < 0:
                normal = -normal
            pts = []
            for v in q:
                d = c - v
                pts.append(v + d * min(.45, gap / max(np.linalg.norm(d), 1e-6)) + normal * lift)
            polygon(part, pts, look[0], look[1], toward=normal)


def freighter():
    """A wrecked freighter in the Spindle Docks: a plated command section with a black window band and
    red chevrons, a black truss spine carrying white cargo pods (some missing, one broken open), and an
    engine block with three heat-tinted bells, radiator fins and a beacon mast. It broke at the middle:
    the bow half lies pitched nose-down and rolled, plates are missing round the break and debris lies
    about. 60 x 18 x 16, bow at +x."""
    rng = np.random.default_rng(511)
    p = Part('SM_CN_Freighter', (PAINT, METAL, REDS, GILT, GLOW, DARK))
    hull_white = lambda: vary(WHITE_PURE, rng, .12)  # noqa: E731
    fore = scratch(p)
    # Command section: an octagonal hull tapering to a blunt nose.
    stations = np.linspace(14.0, 30.0, 9)
    rings = []
    for x in stations:
        t = (x - 14.0) / 16.0
        hw = 6.4 * (1 - t ** 2.2) + .5
        top, bottom = 10.8 - 2.6 * t ** 1.6, 2.6 + 1.6 * t ** 1.8
        mid, hh = (top + bottom) / 2, (top - bottom) / 2
        ring = []
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            ca, sa = math.cos(a), math.sin(a)
            # A squared octagon: superellipse sections read as a pressure hull, not a tube.
            ring.append((x, hw * math.copysign(abs(ca) ** .55, ca), mid + hh * math.copysign(abs(sa) ** .55, sa)))
        rings.append(ring)

    def bow_plate(i, j):
        if 3 <= j <= 5 and 4 <= i <= 6:
            return (BLACK, PAINT)
        if j in (11, 12, 13) and i in (2, 6):
            return (RED, REDS)
        if i == 7 and j % 4 == 0:
            return (RED, REDS)
        return (hull_white(), PAINT)
    plated(fore, rings, lambda c: (c[0], 0, 6.5), (CHARCOAL, METAL), bow_plate)
    polygon(fore, [np.array(v) + (.04, 0, 0) for v in rings[0]], CHARCOAL, METAL, toward=(-1, 0, 0))
    for z in (4.0, 6.5, 9.0):
        strut(fore, (14.0, -5.6, z), (14.0, 5.6, z), .25, .3, SLATE, METAL, (1, 0, 0))
    for y in (-3.0, 0.0, 3.0):  # 26 cm deep against the rails' 30, so their faces never share a plane where they cross
        strut(fore, (14.0, y, 3.0), (14.0, y, 10.3), .25, .26, SLATE, METAL, (1, 0, 0))
    nose = [np.array(v) + (.02, 0, 0) for v in rings[-1]]
    polygon(fore, nose, vary(WHITE_PURE, rng, .08), PAINT, toward=(1, 0, 0))
    for j, deg in enumerate((-22, 0, 22)):
        a = math.radians(deg)
        strut(fore, (25.5, 0, 9.4), (25.5 + 4 * math.cos(a), 4 * math.sin(a), 8.2), .25, .06, RED, REDS, (0, 0, 1))
    # The forward spine stub and its pods.
    for y in (-3.0, 3.0):
        for z in (3.5, 9.5):
            end = rng.uniform(.6, 2.2)
            strut(fore, (end, y, z), (14.2, y, z), .35, .35, CHARCOAL, METAL)
    for x in np.arange(2.0, 14.1, 3.0):
        for (ya, za), (yb, zb) in (((-3, 3.5), (3, 3.5)), ((3, 3.5), (3, 9.5)), ((3, 9.5), (-3, 9.5)), ((-3, 9.5), (-3, 3.5))):
            strut(fore, (x, ya, za), (x, yb, zb), .25, .25, SLATE, METAL, (1, 0, 0))
    for x0 in (4.5, 10.5):
        for s in (-1, 1):
            pod(fore, rng, (x0, s * 5.6, 6.5), broken=(x0 == 4.5 and s > 0))
    tube(fore, [(3.5, 0, 6.5), (14.0, 0, 6.5)], .55, SLATE, METAL, 12)
    # The bow half pitched about the break until its nose rests on the deck, and rolled: at 5.5 degrees its belly was
    # the lowest point and the whole half hung 0.95 m in the air. At 9 its spine stub meets the aft spine's broken end.
    pivot = np.array([0.0, 0.0, 3.5])
    R = rot_y(-9.0) @ rot_x(3.5)
    v = (np.asarray(fore.v) - pivot) @ R.T + pivot
    fore.v = (v - (0, 0, v[:, 2].min())).tolist()
    merge(p, fore)
    # The aft spine, standing level on its legs.
    for y in (-3.0, 3.0):
        for z in (3.5, 9.5):
            strut(p, (-16.0, y, z), (rng.uniform(-1.6, -.4), y, z), .35, .35, CHARCOAL, METAL)
    for x in np.arange(-15.0, -1.0, 3.0):
        for (ya, za), (yb, zb) in (((-3, 3.5), (3, 3.5)), ((3, 3.5), (3, 9.5)), ((3, 9.5), (-3, 9.5)), ((-3, 9.5), (-3, 3.5))):
            strut(p, (x, ya, za), (x, yb, zb), .25, .25, SLATE, METAL, (1, 0, 0))
        strut(p, (x, -3, 3.5), (x + 3, 3, 9.5), .18, .18, SLATE, METAL, (1, 0, 0))
    tube(p, [(-16.0, 0, 6.5), (-1.2, 0, 6.5)], .55, SLATE, METAL, 12)
    for x in (-12.0, -6.0):  # the tanks sit centred on two of the spine's top cross members; at z 9.7 they hovered
        cylinder(p, (x, 0, 9.6), 1.1, 1.7, vary(WHITE_PURE, rng, .08), PAINT, 16)
        cylinder(p, (x, 0, 11.3), 1.1, .25, SLATE, METAL, 16, .7)
    for x0, s in ((-13.0, -1), (-7.0, 1), (-7.0, -1)):
        pod(p, rng, (x0, s * 5.6, 6.5), broken=False)
    # Engine block.
    box(p, (-23.0, 0, 6.5), (6.9, 6.9, 4.4), CHARCOAL, METAL)
    for s in (-1, 1):
        clad(p, rng, s * 6.9, 1, (-29.9, 2.1), (-16.1, 10.9), 5, 3, WHITE_PURE, PAINT, s, t=.06, rivet=1.2)
        bevel_box(p, (-23.0, s * 6.98, 8.2), (6.9, .03, .3), RED, REDS, .01)
    clad(p, rng, -29.9, 0, (-6.9, 2.1), (6.9, 10.9), 5, 3, WHITE_PURE, PAINT, -1, t=.06, rivet=1.2,
         skip=lambda u, z: any(abs(u - yy) < 2.2 and abs(z - 6.5) < 2.2 for yy in (-4.2, 0.0, 4.2)))
    bevel_box(p, (-23.0, 0, 10.95), (6.95, 6.95, .06), SLATE, METAL, .02)
    for y in (-4.2, 0.0, 4.2):
        bell = scratch(p)
        lathe(bell, [(1.0, 0), (1.35, .8), (1.75, 1.8), (2.05, 2.6)], SLATE, METAL, 20)
        # The bell's inside is soot-black from its last burn: rough soot (CN_Black), not the brushed steel outside.
        lathe(bell, [(1.9, 2.6), (1.55, 1.8), (1.15, .8), (.85, 0)], CHARCOAL, DARK, 20)
        torus(bell, (0, 0, 2.6), 1.98, .09, GOLD_DEEP, GILT, 20, 6, 'z')
        cylinder(bell, (0, 0, -.6), .9, .6, CHARCOAL, METAL, 20)
        merge(p, bell, rot_y(90), (-29.95, y, 6.5))
    for s in (-1, 1):
        for x in (-27.0, -23.0, -19.0):
            a = np.array([x, s * 6.95, 10.2])
            b = a + (0, s * 1.9, 1.1)
            hexa(p, [a + (-1.4, 0, -.05), a + (1.4, 0, -.05), b + (-1.4, 0, -.05), b + (1.4, 0, -.05),
                     a + (-1.4, 0, .05), a + (1.4, 0, .05), b + (-1.4, 0, .05), b + (1.4, 0, .05)], vary(WHITE_PURE, rng, .1), PAINT)
            for k in range(5):
                q = a + (b - a) * (k + .5) / 5
                strut(p, q + (-1.38, 0, .07), q + (1.38, 0, .07), .04, .03, CHARCOAL, METAL)
    tube(p, [(-20.0, 3.5, 11.0), (-20.0, 3.5, 15.6)], .12, SLATE, METAL, 8)
    for z in (12.5, 14.0):
        strut(p, (-20.0, 2.6, z), (-20.0, 4.4, z), .06, .06, SLATE, METAL, (1, 0, 0))
    lamp(p, (-20.0, 3.5, 15.75), LIGHT_RED, .14)
    # Landing legs: four under the stern, one bent under the bow's break.
    for x in (-26.0, -18.0):
        for s in (-1, 1):
            top = np.array([x, s * 6.0, 2.1])
            foot = np.array([x + 1.0, s * 7.6, .25])
            tube(p, [top, foot], .3, SLATE, METAL, 10)
            tube(p, [top + (2.0, 0, .2), foot + (0, 0, .4)], .12, GOLD, GILT, 8)
            cylinder(p, foot - (0, 0, .25), 1.0, .3, CHARCOAL, METAL, 12, .8)
    for s in (-1, 1):
        tube(p, [(-3.0, s * 3.0, 3.4), (-2.2, s * 4.4, .4)], .25, SLATE, METAL, 10)
        cylinder(p, (-2.2, s * 4.4, 0), .8, .4, CHARCOAL, METAL, 12, .7)
    # Debris from the break: plates lying on the deck, each tilted as one piece. (A tilt drawn per corner turned some
    # inside out, and their random heights left them hovering and lifted the whole ship off its feet.)
    for k in range(18):
        c = np.array([rng.uniform(-3, 5), rng.uniform(-8, 8), 0.0])
        yaw, tx, ty = rng.uniform(0, 360), rng.uniform(-.06, .06), rng.uniform(-.06, .06)
        corners = np.array([(dx, dy, dz) for dz in (-.04, .04) for dy in (-.6, .6) for dx in (-.9, .9)])
        corners[:, 2] += corners[:, 0] * tx + corners[:, 1] * ty
        corners = corners @ rot_z(yaw).T + c
        corners[:, 2] -= corners[:, 2].min()
        hexa(p, corners, vary(WHITE_PURE if k % 3 else CHARCOAL, rng, .2), PAINT if k % 3 else METAL)
    # Lowest point at z 0 (the feet, the bow's nose and the debris all rest there) and the footprint centred (README).
    v = np.asarray(p.v)
    lo, hi = v.min(0), v.max(0)
    p.v = (v - ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])).tolist()
    return weather(p, 511, reach=2.5, depth=.35, grime=.3, streak=.2, cell=3.0)


def pod(part, rng, c, broken=False):
    """A cargo pod clamped to a freighter's spine: white plates over a black frame, a red band and
    gold clamps; a broken one has lost its outer plates and shows its frames."""
    c = np.array(c, np.float64)
    hx, hy, hz = 2.8, 2.4, 2.6
    box(part, c, (hx - .08, hy - .08, hz - .08), CHARCOAL, METAL)
    side = np.sign(c[1]) if c[1] else 1.0
    if broken:
        for x in np.linspace(-hx + .3, hx - .3, 5):
            for z in (-hz + .3, hz - .3):
                strut(part, c + (x, -hy, z), c + (x, hy, z), .12, .12, SLATE, METAL, (1, 0, 0))
            # 4 mm slimmer than the rails it crosses, so no two frame faces share a plane at the crossings.
            strut(part, c + (x, side * hy, -hz), c + (x, side * hy, hz), .116, .116, SLATE, METAL, (1, 0, 0))
    else:
        clad(part, rng, c[1] + side * (hy - .08), 1, (c[0] - hx, c[2] - hz), (c[0] + hx, c[2] + hz), 3, 3, WHITE_PURE, PAINT, side, t=.05, rivet=1.0)
        bevel_box(part, c + (0, side * (hy - .01), .9), (hx - .05, .03, .22), RED, REDS, .01)
    bevel_box(part, c + (0, 0, hz - .03), (hx - .05, hy - .05, .05), vary(WHITE_PURE, rng, .08), PAINT, .02)
    for x in (-hx + .5, hx - .5):
        bevel_box(part, c + (x, -side * (hy - .02), 0), (.25, .12, .6), GOLD, GILT, .03)


def centred(part):
    """Moves a floating mesh so the middle of its bounds is the origin: items, augmentations and pickups hover, so
    their pivot is their centre (README, Meshes)."""
    v = np.asarray(part.v, np.float64)
    part.v = (v - (v.min(0) + v.max(0)) / 2).tolist()
    return part


def corrugated(part, origin, u, v, n, length, height, colour, slot, pitch=.1, depth=.022):
    """A sheet of corrugated steel (crate walls, doors, roofs): trapezoidal ribs repeating along u and running along
    v, standing proud toward n from the back plane through origin (the sheet's corner at u 0, v 0)."""
    origin, u, v, n = (np.asarray(a, np.float64) for a in (origin, u, v, n))
    count = max(1, int(round(length / pitch)))
    step = length / count
    prof = []
    for i in range(count):
        a = i * step
        prof += [(a, 0.0), (a + step * .18, depth), (a + step * .5, depth), (a + step * .68, 0.0)]
    prof.append((length, 0.0))
    for (a0, d0), (a1, d1) in zip(prof, prof[1:]):
        p0, p1 = origin + u * a0 + n * d0, origin + u * a1 + n * d1
        polygon(part, [p0, p1, p1 + v * height, p0 + v * height], colour, slot, toward=n)


def crate():
    """A cargo crate of the Spindle Docks: a welded steel frame of corner posts and rails with cast corner fittings
    (their twist-lock apertures black), corrugated walls painted white with a red band, a corrugated roof, and at
    the front (+x) double doors in their own frames with four locking bars turning in cam keepers, lever handles,
    a gold seal and hinges along both outer edges. 2 x 2 x 2."""
    rng = np.random.default_rng(521)
    p = Part('SM_CN_Crate', (PAINT, METAL, REDS, GILT, DARK))
    h, post, cast = 1.0, .075, .09
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(p, (sx * (h - post), sy * (h - post), h), (post, post, h - 2 * cast), CHARCOAL, METAL, .012)
            for sz in (-1, 1):
                c = np.array([sx * (h - cast), sy * (h - cast), h + sz * (h - cast)])
                bevel_box(p, c, (cast, cast, cast), vary(ASH, rng, .12), METAL, .014)
                for normal in ((sx, 0, 0), (0, sy, 0)) + (((0, 0, 1),) if sz > 0 else ()):
                    nrm = np.array(normal, np.float64)
                    a, b = frame(nrm)
                    pts = [c + nrm * (cast + .001) + a * math.cos(t) * .042 + b * math.sin(t) * .024
                           for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
                    polygon(p, pts, BLACK, DARK, toward=nrm)
    for z in (.065, 2 * h - .065):
        for s in (-1, 1):
            bevel_box(p, (0, s * (h - .05), z), (h - 2 * cast, .05, .065), SLATE, METAL, .012)
            bevel_box(p, (s * (h - .05), 0, z), (.05, h - 2 * cast, .065), SLATE, METAL, .012)
    # The steel floor between the bottom rails: without it a crate lifted, stacked or tipped showed its open underside.
    bevel_box(p, (0, 0, .1), (h - .1, h - .1, .01), SLATE, METAL, .004)
    span = h - 2 * post  # the walls run between the corner posts (half length)
    z0, z1 = .13, 2 * h - .13
    bands = ((z0, 1.36, 0), (1.36, 1.56, 1), (1.56, z1, 0))  # white, the red band, white
    plane = h - .035  # the walls' back plane, a little inside the posts' faces so the posts stand proud
    # Each wall weathered its own way: one tint per wall for the white and the red, so a wall reads as one sheet.
    walls = (((-span, plane, 0), (1, 0, 0), (0, 1, 0)), ((-span, -plane, 0), (1, 0, 0), (0, -1, 0)),
             ((-plane, -span, 0), (0, 1, 0), (-1, 0, 0)))
    for (ox, oy, _), u, n in walls:
        tints = ((vary(WHITE_PURE, rng, .05), PAINT), (vary(RED, rng, .05), REDS))
        for za, zb, k in bands:
            corrugated(p, (ox, oy, za), u, (0, 0, 1), n, 2 * span, zb - za, tints[k][0], tints[k][1])
    corrugated(p, (-.92, -.92, 2 * h - .045), (1, 0, 0), (0, 1, 0), (0, 0, 1), 1.84, 1.84, vary(WHITE_PURE, rng, .05), PAINT, .23, .012)
    door = h - .07  # the door leaves' back plane, set in between the corner posts
    tints = ((vary(WHITE_PURE, rng, .04), PAINT), (vary(RED, rng, .04), REDS))
    for s in (-1, 1):
        ya, yb = (.006, span) if s > 0 else (-span, -.006)
        ym, half = (ya + yb) / 2, (yb - ya) / 2
        for zc in (z0 + .035, z1 - .035):
            bevel_box(p, (door + .015, ym, zc), (.015, half, .035), SLATE, METAL, .006)
        for yc in (ya + .03, yb - .03):
            # Stiles 1.5 mm thinner than the rails, so their faces do not share the rails' planes at the corners.
            bevel_box(p, (door + .015, yc, (z0 + z1) / 2), (.0135, .03, (z1 - z0) / 2), SLATE, METAL, .006)
        for za, zb, k in bands:
            za2, zb2 = max(za, z0 + .07), min(zb, z1 - .07)
            corrugated(p, (door, ya + .06, za2), (0, 1, 0), (0, 0, 1), (1, 0, 0), yb - ya - .12, zb2 - za2, tints[k][0], tints[k][1], .1, .018)
        if s > 0:  # the rubber seal in the gap between the leaves, so the gap shows black, not the crate's inside
            bevel_box(p, (door + .012, 0, (z0 + z1) / 2), (.012, .008, (z1 - z0) / 2), BLACK, DARK, .003)
        for k, y in enumerate((s * .24, s * .62)):
            bx = door + .045
            tube(p, [(bx, y, z0 + .05), (bx, y, z1 - .05)], .016, ASH, METAL, 8)
            for zk in (z0 + .1, z1 - .1):
                bevel_box(p, (bx, y, zk), (.022, .034, .04), SLATE, METAL, .008)  # cam keepers
            # The handle: a lever folded flat across the door toward the hinge side, caught in its retainer.
            strut(p, (bx + .005, y, .98), (bx + .005, y + s * .2, .92), .028, .018, ASH, METAL, (1, 0, 0))
            bevel_box(p, (bx, y + s * .2, .9), (.02, .03, .03), SLATE, METAL, .006)
            if s > 0 and k == 0:  # the customs seal, a gold wire loop and tag
                torus(p, (bx + .012, y + .2, .86), .022, .005, GOLD, GILT, 12, 4, 'x')
                bevel_box(p, (bx + .012, y + .2, .83), (.006, .012, .018), GOLD_PALE, GILT, .003)
        for zh in (.4, .82, 1.24, 1.66):
            tube(p, [(door + .04, s * (span - .005), zh - .06), (door + .04, s * (span - .005), zh + .06)], .02, SLATE, METAL, 8)
            bevel_box(p, (door + .035, s * (span - .1), zh), (.008, .1, .025), SLATE, METAL, .004)
    return weather(p, 521, reach=.9, depth=.38, grime=.25, streak=.18)


def lift():
    """The Spindle Lift, which carried cargo up the north cap to the Spindle: four box-section steel columns on a
    concrete plinth (striped red and white at the foot), braced on three sides and open at the front (+x); guide
    rails, a counterweight running in its own rails at the back, and at the bottom the car: a checker-plate
    floor, white lower panels and glazed upper ones, a gold handrail, a red scissor gate folded open, a control
    panel and a lamp, hung from a crosshead. At the top a deck with a railing, the motor house and the gold
    traction sheave whose ropes run down to the car and the counterweight, a red warning lamp on its mast,
    floodlights under the deck's front edge and a ladder up the front corner. 8 x 8 x 20."""
    rng = np.random.default_rng(531)
    p = Part('SM_CN_Lift', (STONE, METAL, PAINT, REDS, GILT, GLASS, GLOW))
    top, c, cw = 18.4, 3.3, -2.6
    bevel_box(p, (0, 0, .2), (4.0, 4.0, .2), vary(ASH, rng, .05), STONE, .05)
    stripes(p, (3.84, -3.9, .405), (3.84, 3.9, .405), .16, .01, 16, (RED, WHITE_PURE), (REDS, PAINT), (0, 0, 1))
    for x, y in [(sx * c, sy * c) for sx in (-1, 1) for sy in (-1, 1)]:
        bevel_box(p, (x, y, .43), (.36, .36, .03), SLATE, METAL, .01)
        rivets(p, [(x + dx, y + dy, .46) for dx in (-.28, .28) for dy in (-.28, .28)], (0, 0, 1), .03, ASH, METAL)
        bevel_box(p, (x, y, (.46 + top) / 2), (.22, .22, (top - .46) / 2), CHARCOAL, METAL, .03)
        for k in range(6):
            bevel_box(p, (x, y, .56 + k * .2), (.226, .226, .1), RED if k % 2 == 0 else WHITE_PURE, REDS if k % 2 == 0 else PAINT, .012)
    levels = (4.4, 7.4, 10.4, 13.4, 16.4, 18.31)
    sides = (((c, -c), (c, c)), ((-c, -c), (-c, c)), ((-c, -c), (c, -c)), ((-c, c), (c, c)))
    for k, ((ax, ay), (bx, by)) in enumerate(sides):
        for z in levels:
            strut(p, (ax, ay, z), (bx, by, z), .2, .18, SLATE, METAL)
        zs = (.7,) + levels
        # Each X's braces lap at the crossing, one outside the side's plane and one inside (in one plane they
        # flickered at every crossing); both stay 5 mm inside the girts' faces.
        out = np.array([ax + bx, ay + by, 0.0])
        out = out / np.linalg.norm(out) * .045
        for za, zb in zip(zs, zs[1:]):
            if k == 0 and za < 4.4:
                continue  # the front stays open for the car
            strut(p, np.add((ax, ay, za), out), np.add((bx, by, zb), out), .1, .1, SLATE, METAL)
            strut(p, np.subtract((bx, by, za), out), np.subtract((ax, ay, zb), out), .1, .1, SLATE, METAL)
    rail_z, rail_h = (.4 + 18.2) / 2, (18.2 - .4) / 2  # from the plinth's top (they stopped 6 cm above it)
    for s in (-1, 1):
        bevel_box(p, (0, s * 2.05, rail_z), (.07, .012, rail_h), ASH, METAL, .004)  # the guide rail's flange
        bevel_box(p, (0, s * 2.0, rail_z), (.012, .04, rail_h), ASH, METAL, .004)   # its blade, which the shoes run on
        for z in (2.55,) + levels[:-1]:  # brackets to the girts, and one to the bracing's crossing
            strut(p, (0, s * (c - .09), z), (0, s * 2.065, z), .1, .1, SLATE, METAL)  # into the girt (2 cm short before)
        bevel_box(p, (cw, s * .6, rail_z), (.04, .03, rail_h), ASH, METAL, .004)    # the counterweight's rails
        for z in levels[:-1]:
            strut(p, (-c + .09, s * .6, z), (cw - .04, s * .6, z), .08, .08, SLATE, METAL)
    # The counterweight: cast plates in a frame painted red, tie rods through them.
    for k in range(8):
        bevel_box(p, (cw, 0, 9.15 + k * .3), (.15, .52, .145), vary(CHARCOAL, rng, .2), METAL, .02)
    for z in (8.93, 11.47):
        bevel_box(p, (cw, 0, z), (.19, .58, .075), RED, REDS, .015)
    for s in (-1, 1):
        tube(p, [(cw, s * .45, 8.86), (cw, s * .45, 11.54)], .025, ASH, METAL, 6)
        for z in (8.93, 11.47):
            bevel_box(p, (cw, s * .585, z), (.05, .02, .06), SLATE, METAL, .006)  # shoes on the rails
    # The car.
    bevel_box(p, (0, 0, .52), (1.75, 1.8, .06), SLATE, METAL, .015)
    # The sling's bottom channel under the floor, out to the stiles: the car stood in its sling touching none of it.
    bevel_box(p, (0, 0, .495), (.08, 1.92, .04), SLATE, METAL, .01)  # 5 mm below the floor's underside, not in its plane
    for x in np.linspace(-1.45, 1.45, 9):  # the checker plate's raised bars
        bevel_box(p, (x, 0, .585), (.04, 1.6, .006), ASH, METAL, .003)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(p, (sx * 1.7, sy * 1.75, 1.99), (.05, .05, 1.41), CHARCOAL, METAL, .01)
    for s in (-1, 1):
        bevel_box(p, (0, s * 1.9, 2.07), (.06, .04, 1.58), CHARCOAL, METAL, .01)  # the sling's stiles, channel to crosshead
        bevel_box(p, (0, s * 1.75, 1.05), (1.65, .025, .45), vary(WHITE_PURE, rng, .04), PAINT, .012)
        for off, toward in ((0.0, (0, s, 0)), (-.006 * s, (0, -s, 0))):  # glazed both ways, seen from in and out
            yy = s * 1.75 + off
            polygon(p, [(-1.65, yy, 1.5), (1.65, yy, 1.5), (1.65, yy, 3.3), (-1.65, yy, 3.3)], BLUE_PALE, GLASS, toward=toward)
        for x in (-.55, .55):
            strut(p, (x, s * 1.75, 1.5), (x, s * 1.75, 3.3), .05, .05, CHARCOAL, METAL)
        strut(p, (-1.65, s * 1.75, 1.52), (1.65, s * 1.75, 1.52), .06, .05, CHARCOAL, METAL)
    bevel_box(p, (-1.7, 0, 1.05), (.025, 1.7, .45), vary(WHITE_PURE, rng, .04), PAINT, .012)
    for off, toward in ((0.0, (-1, 0, 0)), (.006, (1, 0, 0))):
        xx = -1.7 + off
        polygon(p, [(xx, -1.65, 1.5), (xx, 1.65, 1.5), (xx, 1.65, 3.3), (xx, -1.65, 3.3)], BLUE_PALE, GLASS, toward=toward)
    for y in (-.6, .6):
        strut(p, (-1.7, y, 1.5), (-1.7, y, 3.3), .05, .05, CHARCOAL, METAL)
    strut(p, (-1.7, -1.7, 1.52), (-1.7, 1.7, 1.52), .06, .05, CHARCOAL, METAL)
    tube(p, [(-1.6, -1.4, 1.0), (-1.6, 1.4, 1.0)], .02, GOLD_PALE, GILT, 8)
    for y in (-1.2, 1.2):
        tube(p, [(-1.69, y, 1.0), (-1.6, y, 1.0)], .012, GOLD_PALE, GILT, 6)  # into the wall panel (5 mm short before)
    bevel_box(p, (0, 0, 3.47), (1.8, 1.865, .07), vary(WHITE_PURE, rng, .03), PAINT, .02)  # its edges into the stiles
    for s in (-1, 1):
        bevel_box(p, (0, s * 1.83, 3.36), (1.78, .025, .045), GOLD, GILT, .008)
        bevel_box(p, (s * 1.78, 0, 3.36), (.025, 1.8, .045), GOLD, GILT, .008)
    disc(p, (0, 0), .32, LIGHT_WARM, GLOW, 16, 3.397, up=False)
    ibeam(p, (0, -1.95, 3.74), (0, 1.95, 3.74), .3, .18, CHARCOAL, METAL)
    for s in (-1, 1):
        for z in (.62, 3.74):
            bevel_box(p, (0, s * 1.935, z), (.09, .035, .12), SLATE, METAL, .01)  # guide shoes on the rail blades
    bevel_box(p, (0, 0, 3.95), (.16, .16, .06), SLATE, METAL, .015)  # the rope hitch
    gx = 1.74  # the scissor gate, folded open against the left post
    ys = np.linspace(-1.68, -.98, 5)
    for y in ys:
        strut(p, (gx, y, .6), (gx, y, 3.3), .03, .03, RED, REDS, (1, 0, 0))
    for ya, yb in zip(ys, ys[1:]):
        for zg in np.arange(.6, 3.2, .45):  # the lazy-tongs pass either side of the bars, 3.5 mm proud of their faces
            strut(p, (gx + .011, ya, zg), (gx + .011, yb, zg + .45), .02, .015, RED, REDS, (1, 0, 0))
            strut(p, (gx - .011, yb, zg), (gx - .011, ya, zg + .45), .02, .015, RED, REDS, (1, 0, 0))
    strut(p, (gx, -1.7, 3.33), (gx, 1.7, 3.33), .05, .05, CHARCOAL, METAL, (1, 0, 0))
    # The control panel against the side wall and the front post (it floated 2-4 cm clear of both).
    bevel_box(p, (1.62, 1.63, 1.35), (.04, .1, .2), CHARCOAL, METAL, .01)
    tube(p, [(1.58, 1.63, 1.4), (1.5, 1.63, 1.5)], .012, GOLD, GILT, 6)
    # Ropes from the car and the counterweight over the sheave.
    sc = np.array([-1.3, 0.0, 18.58])
    for dy in (-.07, 0.0, .07):
        tube(p, [(0.0, dy, 4.01), (0.0, dy, sc[2])], .016, ASH, METAL, 5)
        tube(p, [(cw, dy, 11.545), (cw, dy, sc[2])], .016, ASH, METAL, 5)
    # The top: deck plates round the sheave's slot, the sheave, its bearings, gearbox and the motor house.
    for x0, x1, y0, y1 in ((-3.55, -2.78, -3.55, 3.55), (.18, 3.55, -3.55, 3.55), (-2.78, .18, -3.55, -.32), (-2.78, .18, .32, 3.55)):
        bevel_box(p, ((x0 + x1) / 2, (y0 + y1) / 2, top + .05), ((x1 - x0) / 2 - .004, (y1 - y0) / 2 - .004, .05), vary(SLATE, rng, .1), METAL, .01)
    torus(p, sc, 1.3, .055, GOLD, GILT, 40, 8, 'y')
    for dy in (-.075, .075):
        torus(p, sc + (0, dy, 0), 1.33, .025, GOLD_PALE, GILT, 40, 5, 'y')
    for j in range(8):
        a = j / 8 * 2 * math.pi
        d = np.array([math.cos(a), 0.0, math.sin(a)])
        tube(p, [sc + d * .2, sc + d * 1.26], .035, GOLD_DEEP, GILT, 6)
    tube(p, [sc - (0, .12, 0), sc + (0, .12, 0)], .2, GOLD_PALE, GILT, 14)
    tube(p, [sc - (0, .52, 0), sc + (0, .52, 0)], .07, ASH, METAL, 10)
    for s in (-1, 1):
        bevel_box(p, (sc[0], s * .45, 18.6), (.2, .08, .1), SLATE, METAL, .02)
    bevel_box(p, (sc[0], .66, 18.66), (.22, .1, .16), CHARCOAL, METAL, .02)
    tube(p, [(sc[0] + .22, .66, 18.7), (.8, .66, 18.7)], .06, ASH, METAL, 8)
    mx = 1.85
    bevel_box(p, (mx, 0, 19.15), (1.05, 1.0, .65), vary(WHITE_PURE, rng, .04), PAINT, .03)
    bevel_box(p, (mx, 0, 18.58), (1.07, 1.02, .08), RED, REDS, .012)
    bevel_box(p, (mx, 0, 19.84), (1.12, 1.07, .05), CHARCOAL, METAL, .015)
    for s in (-1, 1):
        for z in np.arange(18.95, 19.6, .1):
            strut(p, (mx - .5, s * 1.01, z), (mx + .5, s * 1.01, z), .02, .05, SLATE, METAL, (0, s, 1))
    bevel_box(p, (mx + 1.06, -.35, 19.05), (.015, .35, .45), SLATE, METAL, .008)
    bevel_box(p, (mx + 1.08, -.1, 19.05), (.012, .02, .06), GOLD, GILT, .004)
    # Railing round the deck, open where the ladder arrives.
    for k, ((ax, ay), (bx, by)) in enumerate((((-3.5, -3.5), (3.5, -3.5)), ((3.5, -3.5), (3.5, 3.5)), ((2.9, 3.5), (-3.5, 3.5)), ((-3.5, 3.5), (-3.5, -3.5)))):
        n = max(2, int(math.hypot(bx - ax, by - ay) / 1.4) + 1)
        for q in row((ax, ay, top + .1), (bx, by, top + .1), n)[:-1]:
            strut(p, q, q + (0, 0, 1.0), .045, .045, WHITE_PURE, PAINT)
        for z in (top + .6, top + 1.1):  # alternate sides' rails 2 mm apart in depth, so the corner laps share no plane
            strut(p, (ax, ay, z), (bx, by, z), .04, .04 - .002 * (k % 2), WHITE_PURE, PAINT)
    # The corner post where the second side's rails end (they ended in the air; the post at 2.9, 3.5 was doubled).
    strut(p, (3.5, 3.5, top + .1), (3.5, 3.5, top + 1.1), .045, .045, WHITE_PURE, PAINT)
    tube(p, [(-c, -c, top + .1), (-c, -c, 19.72)], .04, SLATE, METAL, 8)
    lamp(p, (-c, -c, 19.8), LIGHT_RED, .09)
    for y in (-2.2, 2.2):
        cylinder(p, (3.45, y, 18.1), .2, .22, CHARCOAL, METAL, 12)
        disc(p, (3.45, y), .17, LIGHT_WHITE, GLOW, 12, 18.098, up=False)
    lx, ly = c, 3.64
    for x in (lx - .22, lx + .22):
        tube(p, [(x, ly, .41), (x, ly, top + 1.1)], .024, ASH, METAL, 6)
    for z in np.arange(.7, top + .01, .3):
        strut(p, (lx - .22, ly, z), (lx + .22, ly, z), .025, .025, ASH, METAL)
    for z in np.arange(1.5, top, 3.0):
        strut(p, (lx, c + .2, z), (lx, ly, z), .05, .05, SLATE, METAL)
    return weather(p, 531, reach=2.0, depth=.35, grime=.25)


# ---------------------------------------------------------------- gates and locks

def clip_segment(a, b, lo, hi):
    """The part of the 2-D segment a-b inside the rectangle lo-hi, or None."""
    t0, t1 = 0.0, 1.0
    d = (b[0] - a[0], b[1] - a[1])
    for k in range(2):
        if abs(d[k]) < 1e-12:
            if a[k] < lo[k] or a[k] > hi[k]:
                return None
            continue
        ta, tb = (lo[k] - a[k]) / d[k], (hi[k] - a[k]) / d[k]
        t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
    if t1 - t0 < 1e-6:
        return None
    return (a[0] + d[0] * t0, a[1] + d[1] * t0), (a[0] + d[0] * t1, a[1] + d[1] * t1)


def honeycomb(r, lo, hi):
    """The edges of a pointy-topped hexagonal grid of circumradius r over the rectangle lo-hi (2-D), each shared
    edge once and every edge clipped to the rectangle."""
    w = math.sqrt(3) * r
    edges = {}
    rows, cols = int((hi[1] - lo[1]) / (1.5 * r)) + 2, int((hi[0] - lo[0]) / w) + 2
    for i in range(-1, rows + 1):
        for j in range(-1, cols + 1):
            cx, cy = lo[0] + j * w + (w / 2 if i % 2 else 0.0), lo[1] + i * 1.5 * r
            corners = [(cx + r * math.cos(math.radians(90 + 60 * k)), cy + r * math.sin(math.radians(90 + 60 * k))) for k in range(6)]
            for k in range(6):
                a, b = corners[k], corners[(k + 1) % 6]
                edges[tuple(sorted((tuple(np.round(a, 4)), tuple(np.round(b, 4)))))] = (a, b)
    out = []
    for a, b in edges.values():
        seg = clip_segment(a, b, lo, hi)
        if seg and math.dist(*seg) > .03:
            out.append(seg)
    return out


def barricade():
    """An AL barricade (BP_SettleBarrier's mesh): two emitter pylons of black plated metal with white armour plates,
    bolted feet, a channel of red light down the face toward the sheet and a red node held between black prongs
    on top; a ground rail with a slit of light; and between them the force sheet, a dim red field crossed by a
    honeycomb of brighter red light under a bar of light. Settle dissolves it. 1 x 8 x 4, the sheet in the y-z
    plane."""
    rng = np.random.default_rng(541)
    p = Part('SM_CN_Barricade', (METAL, PAINT, GLOW))
    ye = 3.7
    segs = ((.24, 1.4, .42, .38), (1.43, 2.6, .38, .34), (2.63, 3.55, .34, .29))  # z0, z1 and the half depth at each
    width = .62  # half width (y) as a fraction of half depth (x)

    def depth_at(seg, z):
        z0, z1, d0, d1 = seg
        return d0 + (d1 - d0) * (z - z0) / (z1 - z0)

    for s in (-1, 1):
        y = s * ye
        bevel_box(p, (0, y, .12), (.5, .3, .12), CHARCOAL, METAL, .03)
        rivets(p, [(dx, y + dy, .24) for dx in (-.4, .4) for dy in (-.2, .2)], (0, 0, 1), .028, ASH, METAL)
        for z0, z1, d0, d1 in segs:
            pts = [(sx * d, y + sy * d * width, z) for z, d in ((z0, d0), (z1, d1)) for sy in (-1, 1) for sx in (-1, 1)]
            hexa(p, pts, vary(BLACK, rng, .3), METAL)
        # The segments sit on a slimmer spine, so the 3 cm joints between them read as recessed seams instead of
        # slits that daylight showed through.
        bevel_box(p, (0, y, 1.9), (.27, .17, 1.68), CHARCOAL, METAL, .02)
        # White armour: plates on the front and back of the middle segment and the outer face of the lowest,
        # each following its face's taper.
        seg = segs[1]
        za, zb = seg[0] + .12, seg[1] - .12
        for sx in (-1, 1):
            pts = [(sx * (depth_at(seg, z) + t), y + sy * .17, z) for z in (za, zb) for sy in (-1, 1) for t in (-.004, .016)]
            hexa(p, pts, vary(WHITE_PURE, rng, .04), PAINT)
        seg = segs[0]
        za, zb = seg[0] + .16, seg[1] - .14
        pts = [(sx * .24, y + s * (depth_at(seg, z) * width + t), z) for z in (za, zb) for t in (-.004, .016) for sx in (-1, 1)]
        hexa(p, pts, vary(WHITE_PURE, rng, .04), PAINT)
        # The channel down the face toward the sheet, and the light in it.
        for seg in segs:
            z0, z1 = seg[0] + .05, seg[1] - .05
            a, b = (0, y - s * depth_at(seg, z0) * width, z0), (0, y - s * depth_at(seg, z1) * width, z1)
            strut(p, a, b, .1, .03, SLATE, METAL, (0, 1, 0))
            inset = (np.subtract(b, a)) * (.01 / math.dist(a, b))
            strut(p, np.add(a, inset), np.subtract(b, inset), .05, .036, LIGHT_RED, GLOW, (0, 1, 0))
        bevel_box(p, (0, y, 3.64), (.31, .2, .09), CHARCOAL, METAL, .03)
        for sx in (-1, 1):
            prism(p, (sx * .2, y, 3.7), (sx * .25, y, 4.0), .055, BLACK, METAL, 4, .5)
        blob(p, (0, y, 3.86), .085, LIGHT_RED, GLOW, 1, 0.0, 7)
        torus(p, (0, y, 3.86), .12, .018, SLATE, METAL, 16, 4, 'y')
    bevel_box(p, (0, 0, .08), (.2, ye - .28, .08), CHARCOAL, METAL, .02)
    strut(p, (0, -ye + .3, .163), (0, ye - .3, .163), .05, .008, LIGHT_RED, GLOW)
    # The sheet runs into the emitters' faces (hidden inside them below), so no slit of daylight shows at its sides,
    # and down into the ground rail (it stopped 3 cm above it).
    lo, hi = (-3.52, .15), (3.52, 3.5)
    for sx in (-1, 1):
        x = sx * .004
        cols = [tone(LIGHT_RED, k) for k in (.42, .42, .2, .2)]  # brightest where it rises from the rail
        polygon(p, [(x, lo[0], lo[1]), (x, hi[0], lo[1]), (x, hi[0], hi[1]), (x, lo[0], hi[1])], cols, GLOW, toward=(sx, 0, 0))
    for a, b in honeycomb(.32, lo, hi):
        # The three directions of the comb sit 1.5 mm apart in depth: where bars meet, one face is always in front.
        k = int((math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0) // 60.0)  # 30, 90 or 150 degrees
        x = .0015 * (k - 1)
        strut(p, (x, a[0], a[1]), (x, b[0], b[1]), .036, .026, tone(LIGHT_RED, rng.uniform(.62, 1.0)), GLOW, (1, 0, 0))
    strut(p, (0, lo[0], hi[1]), (0, hi[0], hi[1]), .06, .036, LIGHT_RED, GLOW, (1, 0, 0))  # in front of the comb's ends
    return weather(p, 541, reach=.8, depth=.3)


def arc_blocks(part, r0, r1, z0, z1, spans, size, colour, slot, offset=0.0, seam=.004, sub=1):
    """A course of curved blocks between radii r0 and r1 over angular spans [(a0, a1), ...] (radians), about size
    metres long with seams of `seam` radians between them; offset shifts the joints by a fraction of a block (so
    courses stagger), sub splits each block into flat facets so its faces follow the curve."""
    for a0, a1 in spans:
        n = max(1, int(round((a1 - a0) * (r0 + r1) / 2 / size)))
        cuts = [a0 + (a1 - a0) * (k + offset) / n for k in range(n + 1)]
        bounds = [a0] + [c for c in cuts if a0 + 1e-6 < c < a1 - 1e-6] + [a1]
        for b0, b1 in zip(bounds, bounds[1:]):
            tint = colour() if callable(colour) else colour
            edges = np.linspace(b0 + seam / 2, b1 - seam / 2, sub + 1)
            for e0, e1 in zip(edges, edges[1:]):
                pts = [(math.cos(aa) * rr, math.sin(aa) * rr, zz) for zz in (z0, z1) for rr in (r0, r1) for aa in (e0, e1)]
                hexa(part, pts, tint, slot)


def current():
    """The Divinity current (BP_Current's Shape, here and in the Center's sanctum): a round basin of white marble in
    two courses split by a gold string course, open at the front and back (+-x), where threshold slabs flush with
    the pool let Physis walk in; its pool a disc of light-blue light, brightest at the heart and rippled; two gold
    hoops crossing over it, collared in gold and lined with threads of light, rising from the pool to 5 m with a
    gold boss where they cross; and above head height three threads of light spiralling up into the boss. Pool
    radius 3; pivot at the pool's surface (z 0): the coping stands 0.24 above it and the basin reaches 0.45 below."""
    rng = np.random.default_rng(551)
    p = Part('SM_CN_Current', (STONE, GILT, GLOW))
    pool, segs, rings = 3.0, 48, 12
    verts, cols = [(0.0, 0.0, 0.0)], [mix(LIGHT_BLUE, LIGHT_WHITE, .55)]
    for r in np.linspace(0, pool, rings + 1)[1:]:
        fade = 1 - r / pool  # ripples die out at the rim, which meets the stone level
        wave = math.sin(r * 8.5 - .4)
        for j in range(segs):
            a = 2 * math.pi * j / segs
            verts.append((math.cos(a) * r, math.sin(a) * r, .007 * wave * fade))
            cols.append(tone(mix(LIGHT_BLUE, LIGHT_WHITE, .55 * fade ** 1.4), .64 + .2 * fade + .16 * (.5 + .5 * wave)))
    faces = [[0, 1 + j, 1 + (j + 1) % segs] for j in range(segs)]
    for i in range(rings - 1):
        a0, a1 = 1 + i * segs, 1 + (i + 1) * segs
        faces += [[a0 + j, a1 + j, a1 + (j + 1) % segs, a0 + (j + 1) % segs] for j in range(segs)]
    p.add(verts, faces, cols, GLOW, True)
    gap = math.asin(.85 / pool)  # half angle of each entrance, 1.7 m wide at the pool's edge
    ring_spans = ((gap, math.pi - gap), (math.pi + gap, 2 * math.pi - gap))
    arc_blocks(p, pool, 3.45, -.45, .09, ring_spans, 1.0, lambda: vary(WHITE, rng, .04), STONE, sub=3)
    arc_blocks(p, pool + .01, 3.47, .09, .115, ring_spans, .35, GOLD, GILT, seam=0.0)
    arc_blocks(p, 2.96, 3.52, .115, .24, ring_spans, 1.0, lambda: vary(IVORY, rng, .04), STONE, offset=.5, sub=3)
    door_spans = ((-gap, gap), (math.pi - gap, math.pi + gap))
    arc_blocks(p, pool - .01, 3.62, -.45, 0.0, door_spans, .45, lambda: vary(WHITE, rng, .05), STONE, sub=2)
    for a0, a1 in door_spans:  # a gold lip where the threshold meets the light
        edges = np.linspace(a0, a1, 7)
        for k, (e0, e1) in enumerate(zip(edges, edges[1:])):  # alternate pieces 1.5 mm thinner: their laps shared top planes
            strut(p, (math.cos(e0) * pool, math.sin(e0) * pool, .004), (math.cos(e1) * pool, math.sin(e1) * pool, .004), .07,
                  .012 - .0015 * (k % 2), GOLD, GILT)
    tube_r = .085
    for k, yaw in enumerate((45.0, 135.0)):
        d = np.array([math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0.0])
        R = 2.9 - .07 * k
        zc = 5.0 - tube_r - R - .06 * k
        t0 = math.asin((-.35 - zc) / R)  # the hoop's feet stand in the basin, below the light
        ts = np.linspace(t0, math.pi - t0, 44)

        def on_hoop(t, rr):
            return d * rr * math.cos(t) + (0, 0, zc + rr * math.sin(t))
        tube(p, [on_hoop(t, R) for t in ts], tube_r, GOLD, GILT, 10)
        for t in np.linspace(t0, math.pi - t0, 13)[1:-1]:
            q = on_hoop(t, R)
            if q[2] > .1:
                tangent = -d * math.sin(t) + np.array([0, 0, math.cos(t)])
                tube(p, [q - tangent * .045, q + tangent * .045], tube_r + .025, GOLD_PALE, GILT, 10)
        rr = R - tube_r - .02
        tube(p, [on_hoop(t, rr) for t in ts if zc + rr * math.sin(t) > .05], .022, LIGHT_BLUE, GLOW, 6)
    blob(p, (0, 0, 4.86), .14, GOLD_PALE, GILT, 2, .03, 5)
    # Threads of light start above Physis's head, so nothing in the pool snags her as she walks in.
    sides = 6
    for k in range(3):
        a0 = 2 * math.pi * k / 3 + .3
        ts = np.linspace(0, 1, 28)
        pts = [(math.cos(a0 + 3.4 * t) * (.6 - .45 * t), math.sin(a0 + 3.4 * t) * (.6 - .45 * t), 2.3 + 2.42 * t) for t in ts]
        thread = [c for t in ts for c in [tone(mix(LIGHT_BLUE, LIGHT_WHITE, .2 + .5 * t), .55 + .45 * t)] * sides]
        tube(p, pts, .03 * (1 - .6 * ts), thread, GLOW, sides)
    for k in range(14):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(.2, 1.5)
        blob(p, (math.cos(a) * r, math.sin(a) * r, rng.uniform(2.2, 4.3)), rng.uniform(.018, .035),
             mix(LIGHT_BLUE, LIGHT_WHITE, rng.uniform(.2, .7)), GLOW, 1, 0.0, 600 + k)
    return weather(p, 551, ground=-.1, reach=.45, depth=.25, grime=.12)


def still_point():
    """A Still Point (the ring at BP_Checkpoint, where Physis rests and saves): nine standing stones of white marble
    on a circle of radius 3, each with a bevelled cap and a groove of light-blue light on its inner face, around a
    paved floor of staggered rings of slabs: a gold inlay over one joint, lines of light from each stone to a ring
    of light round a disc of light at the centre. 6.8 across, the stones 0.7 to 1.1 tall."""
    rng = np.random.default_rng(561)
    p = Part('SM_CN_StillPoint', (STONE, GILT, GLOW, DARK))
    cylinder(p, (0, 0, 0), .9, .08, vary(WHITE, rng, .03), STONE, 48, smooth=False)
    # Curved slabs (arc_blocks), so every ring keeps its 1 cm joint all the way round: straight-chord rings cut into
    # the centre stone and the next ring out, where the player stands, and those overlaps flickered.
    for r0, r1, n, start, sub in ((.9, 1.8, 12, 0.0, 4), (1.8, 2.7, 18, 10.0, 3), (2.7, 3.4, 27, 3.0, 2)):
        turn = iter(range(100))
        a0 = math.radians(start)
        arc_blocks(p, r0 + .005, r1 - .005, 0.0, .08, ((a0, a0 + 2 * math.pi),), 2 * math.pi * (r0 + r1) / 2 / n,
                   lambda: vary(WHITE if next(turn) % 2 else WHITE_COOL, rng, .05), STONE, 0.0, math.radians(.35), sub)
    annulus(p, (0, 0), 1.77, 1.83, GOLD, GILT, 72, .083)
    annulus(p, (0, 0), .5, .58, LIGHT_BLUE, GLOW, 36, .083)
    disc(p, (0, 0), .3, mix(LIGHT_BLUE, LIGHT_WHITE, .45), GLOW, 24, .083)
    for k in range(9):
        a = 2 * math.pi * k / 9 + .17
        d, t = np.array([math.cos(a), math.sin(a), 0.0]), np.array([-math.sin(a), math.cos(a), 0.0])
        c = d * 3.0
        h = rng.uniform(.7, 1.1)
        # Dressed and a little tapered: wider at the foot (half widths along the circle, then across it).
        pts = [c + t * sx * (.3 if zb == 0 else .24) + d * sy * (.19 if zb == 0 else .15) + (0, 0, -.05 if zb == 0 else h - .1)
               for zb in (0, 1) for sy in (-1, 1) for sx in (-1, 1)]
        hexa(p, pts, vary(WHITE, rng, .06), STONE)
        bevel_box(p, c + (0, 0, h - .05), (.17, .27, .05), vary(IVORY, rng, .05), STONE, .02, math.degrees(a))
        lo, hi = c - d * .19 + (0, 0, .22), c - d * .155 + (0, 0, h - .22)
        strut(p, lo - (0, 0, .01), hi + (0, 0, .01), .1, .02, SLATE, DARK, d)
        strut(p, lo, hi, .05, .032, LIGHT_BLUE, GLOW, d)
        strut(p, d * .62 + (0, 0, .083), d * 2.75 + (0, 0, .083), .025, .006, LIGHT_BLUE, GLOW)
    return weather(p, 561, reach=.6, depth=.3, grime=.18)


def light_cache():
    """A Light Cache: condensed Divinity, a cluster of light-blue crystals of hardened light grown out of a glowing
    heart in every direction, a core of light down each, and the Lightforms' gold seal bands round the six
    largest. About 1 m, centred."""
    rng = np.random.default_rng(571)
    p = Part('SM_CN_LightCache', (GLASS, GLOW, GILT))
    blob(p, (0, 0, 0), .15, mix(LIGHT_BLUE, LIGHT_WHITE, .55), GLOW, 2, .1, 571)
    axes = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    diagonals = [(sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    for k, d in enumerate(axes + diagonals):
        d = np.asarray(d, np.float64)
        d = d / np.linalg.norm(d) + rng.normal(0, .1, 3)
        d /= np.linalg.norm(d)
        big = k < 6  # the six along the axes are the longest, so the cluster's bounds are about 1 m every way
        length = rng.uniform(.47, .5) if big else rng.uniform(.27, .36)
        r = rng.uniform(.075, .095) if big else rng.uniform(.045, .065)
        prism(p, d * .05, d * length, r, mix(BLUE_PALE, WHITE_COOL, rng.uniform(0, .35)), GLASS, 6, .3)
        prism(p, d * .06, d * length * .8, r * .32, LIGHT_BLUE, GLOW, 6, .35)
        if big:
            a, b = frame(d)
            c = d * .2
            loop = [c + r * .98 * (math.cos(t) * a + math.sin(t) * b) for t in np.linspace(0, 2 * math.pi, 17)]
            tube(p, loop, .011, GOLD, GILT, 6, cap=False)
    return centred(p)


def vault_door():
    """A sealed vault door of the Wise (BP_AbilitySocket's mesh where a later ability opens the way): a white marble
    surround of plinths, jambs in three courses with a fillet framing the leaves, a sill, a lintel and a stepped
    cornice; two leaves of black iron with raised panels, gold straps studded in gold and gold hinge pintles; and on
    the front (+x) the lock, a red sigil of light set in gold across the meeting stiles (a ring, a triangle within a
    second ring, rays and an eye) with a seam of red light between the leaves. 1 x 6 x 6, in the y-z plane."""
    rng = np.random.default_rng(581)
    p = Part('SM_CN_VaultDoor', (STONE, METAL, GILT, GLOW))
    for s in (-1, 1):
        y = s * 2.6
        bevel_box(p, (0, y, .2), (.5, .4, .2), vary(IVORY, rng, .04), STONE, .03)
        for z0, z1 in ((.4, 1.9), (1.91, 3.4), (3.41, 4.9)):
            bevel_box(p, (0, y, (z0 + z1) / 2), (.45, .38, (z1 - z0) / 2), vary(WHITE, rng, .05), STONE, .03)
        bevel_box(p, (0, y, 2.65), (.43, .36, 2.24), tone(ASH, 1.4), STONE, .01)  # mortar behind the open 1 cm joints
        for sx in (-1, 1):
            bevel_box(p, (sx * .46, s * 2.27, 2.65), (.02, .05, 2.25), vary(WHITE_COOL, rng, .03), STONE, .01)
    bevel_box(p, (0, 0, .2), (.45, 2.2, .2), vary(WHITE, rng, .04), STONE, .03)
    bevel_box(p, (0, 0, 5.2), (.45, 2.98, .3), vary(WHITE, rng, .04), STONE, .03)
    bevel_box(p, (0, 0, 5.62), (.5, 3.0, .12), vary(IVORY, rng, .04), STONE, .03)
    bevel_box(p, (0, 0, 5.87), (.46, 2.9, .13), vary(WHITE_COOL, rng, .04), STONE, .03)
    for s in (-1, 1):
        yc = s * 1.1
        # Up to the lintel, and a steel stop in each jamb behind the leaf's edge: the 2.4 cm gaps at the sides and the
        # 2 cm gap under the lintel were slits straight through the door.
        bevel_box(p, (0, yc, 2.65), (.15, 1.096, 2.25), CHARCOAL, METAL, .02)
        bevel_box(p, (-.06, s * 2.21, 2.65), (.04, .012, 2.25), SLATE, METAL, .004)
        for sx in (-1, 1):
            for z0, z1 in ((.6, 1.95), (2.15, 3.15), (3.35, 4.7)):
                bevel_box(p, (sx * .16, yc + s * .03, (z0 + z1) / 2), (.015, .85, (z1 - z0) / 2), vary(SLATE, rng, .1), METAL, .01)
        for z in (1.05, 4.25):  # the straps stop short of the sigil
            bevel_box(p, (.185, yc, z), (.012, 1.05, .07), GOLD, GILT, .006)
            rivets(p, [(.197, yy, z) for yy in np.linspace(yc - .95, yc + .95, 7)], (1, 0, 0), .022, GOLD_PALE, GILT)
            bevel_box(p, (-.185, yc, z), (.012, 1.05, .07), GOLD_DEEP, GILT, .006)
        for z in (1.0, 2.6, 4.2):
            tube(p, [(.17, s * 2.17, z - .16), (.17, s * 2.17, z + .16)], .045, GOLD, GILT, 10)
    bevel_box(p, (-.2, 0, 2.65), (.05, 2.1, .1), BLACK, METAL, .02)  # the bar across the back
    for y in (-1.6, 1.6):
        bevel_box(p, (-.2, y, 2.65), (.07, .1, .16), SLATE, METAL, .015)
    strut(p, (.155, 0, .45), (.155, 0, 4.85), .02, .01, LIGHT_RED, GLOW, (1, 0, 0))
    c = np.array([.2, 0.0, 2.65])
    # The lines of light ride on the front of their gold rings (set 3 cm forward, the outer one lay wholly inside its
    # ring and never showed); the triangle and rays lie on the leaves and the eye on a gold boss, not in the air.
    torus(p, c, .95, .06, GOLD, GILT, 48, 8, 'x')
    torus(p, c + (.058, 0, 0), .95, .022, LIGHT_RED, GLOW, 48, 6, 'x')
    torus(p, c, .62, .04, GOLD, GILT, 40, 6, 'x')
    torus(p, c + (.044, 0, 0), .62, .016, LIGHT_RED, GLOW, 40, 6, 'x')
    corners = [np.array([.175, math.cos(math.radians(90 + 120 * k)) * .58, c[2] + math.sin(math.radians(90 + 120 * k)) * .58]) for k in range(3)]
    for k in range(3):
        strut(p, corners[k], corners[(k + 1) % 3], .035, .05, LIGHT_RED, GLOW, (1, 0, 0))
    for k in range(12):
        a = math.radians(30 * k + 15)
        reach = 1.32 if k % 2 else 1.18
        d = np.array([0, math.cos(a), math.sin(a)])
        base = np.array([.17, 0.0, c[2]])
        strut(p, base + d * 1.04, base + d * reach, .03, .04, LIGHT_RED, GLOW, (1, 0, 0))
    tube(p, [(.14, 0, c[2]), (.238, 0, c[2])], .155, GOLD, GILT, 16)
    eye = [c + (.04, math.cos(a) * .14, math.sin(a) * .14) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    polygon(p, eye, LIGHT_RED, GLOW, toward=(1, 0, 0))
    torus(p, c + (.03, 0, 0), .17, .02, GOLD, GILT, 24, 5, 'x')
    return weather(p, 581, reach=1.2, depth=.35, grime=.22, streak=.15)


# ---------------------------------------------------------------- quest items

def sail(part, a, b, c, n, colour, slot, billow=0.0, skip=None, back=.002):
    """A triangle of cloth a-b-c (kites, pennants) in the y-z plane, subdivided n times and bellied back along -x by
    billow at its middle; two-sided, its front facing +x. colour(point) gives each vertex's colour; skip(centroid)
    leaves a facet out (torn or burnt away)."""
    a, b, c = (np.asarray(q, np.float64) for q in (a, b, c))
    index, verts = {}, []
    for i in range(n + 1):
        for j in range(n + 1 - i):
            w1, w2 = i / n, j / n
            w0 = 1 - w1 - w2
            index[(i, j)] = len(verts)
            verts.append(a * w0 + b * w1 + c * w2 - (billow * 27 * w0 * w1 * w2, 0, 0))
    verts = np.array(verts)
    tris = []
    for i in range(n):
        for j in range(n - i):
            tris.append([index[(i, j)], index[(i + 1, j)], index[(i, j + 1)]])
            if i + j < n - 1:
                tris.append([index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]])
    keep = []
    for f in tris:
        if skip is not None and skip(verts[f].mean(0)):
            continue
        if np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]])[0] < 0:
            f = f[::-1]
        keep.append(f)
    used = sorted({i for f in keep for i in f})  # facets skipped leave no loose vertices behind
    remap = {old: new for new, old in enumerate(used)}
    verts = verts[used]
    faces = [[remap[i] for i in f] for f in keep]
    cols = [colour(q) for q in verts]
    part.add(verts, faces, cols, slot, True)
    part.add(verts - (back, 0, 0), [f[::-1] for f in faces], cols, slot, True)


def kite():
    """Tamsin's kite, caught at the top of the Terraces and a little burnt: a diamond of cloth in white and red panels
    bellied by the wind, sewn to a black spine and a bowed cross spar, a red hem, a white bridle with the snapped end
    of its line, and a tail of red and white bows; the lower right panel is scorched and its edge burnt away. Faces
    +x; 0.94 tall, centred."""
    rng = np.random.default_rng(591)
    p = Part('SM_CN_Kite', (CLOTH, PAINT))
    T, L, R, B, C = (np.array(q, np.float64) for q in ((0, 0, .42), (0, -.31, .17), (0, .31, .17), (0, 0, -.34), (0, 0, .17)))

    def plain(colour):
        return lambda q: tone(colour, .9 + .1 * float(noise2(q[1] * 20, q[2] * 20, 5)))

    def burn_gap(q):  # distance from q to the burnt edge B-R
        e = R - B
        t = min(1.0, max(0.0, float(np.dot(q - B, e) / np.dot(e, e))))
        return float(np.linalg.norm(q - (B + e * t)))

    def scorched(q):
        k = max(0.0, 1 - burn_gap(q) / .09) ** 1.5
        return tone(WHITE_PURE, 1 - .88 * k * (.75 + .25 * float(noise2(q[1] * 30, q[2] * 30, 9))))

    sail(p, T, L, C, 6, plain(WHITE_PURE), CLOTH, .03)
    sail(p, T, C, R, 6, plain(RED), CLOTH, .03)
    sail(p, C, L, B, 7, plain(RED), CLOTH, .035)
    sail(p, C, B, R, 7, scorched, CLOTH, .035, lambda q: burn_gap(q) < .03 + .03 * float(noise2(q[1] * 25, q[2] * 25, 13)))
    tube(p, [L, T, R], .0045, RED, CLOTH, 5)
    tube(p, [L, B], .0045, RED, CLOTH, 5)
    tube(p, [R, R + (B - R) * .22], .004, CHARCOAL, CLOTH, 5)  # what is left of the hem on the burnt edge
    tube(p, [T + (-.012, 0, .012), C + (-.012, 0, 0), B + (-.012, 0, -.012)], .0065, BLACK, PAINT, 6)
    tube(p, [L + (-.014, -.012, 0), C + (-.04, 0, 0), R + (-.014, .012, 0)], .0055, BLACK, PAINT, 6)
    tow = np.array([.2, 0.0, .1])
    tube(p, [T * .75 + C * .25, tow, C * .45 + B * .55], .0022, WHITE, CLOTH, 4)
    tube(p, [tow, (.235, .05, -.06), (.25, .1, -.2)], .0022, WHITE, CLOTH, 4)
    tail = bezier(B, B + (0, .03, -.06), B + (0, .1, -.12), B + (0, .07, -.18), 7)
    tube(p, tail, .0025, WHITE, CLOTH, 4)
    for k, q in enumerate(tail[2::2]):
        across = np.array([0, 1.0, .25 * (k - 1)])
        across /= np.linalg.norm(across)
        ribbon(p, [q - across * .035, q, q + across * .035], np.array([.016, .005, .016]), RED if k % 2 == 0 else WHITE_PURE, CLOTH, normal=(1, 0, 0))
    return centred(weather(p, 591, reach=.01, depth=0.0, grime=.12, streak=.05))


def memory_core():
    """Halden-7's memory core: a cartridge of white porcelain between black lacquered end caps with grip rings, gold
    collars at the joints, a glass window through which light-blue light runs in bands along a lattice, a red status
    lamp, a crown of gold contacts at the plug end (below) and a carrying loop on top. 0.64 tall, centred."""
    p = Part('SM_CN_MemoryCore', (STONE, PAINT, GILT, GLOW, GLASS))
    s = 32
    lathe(p, [(.07, -.27), (.083, -.262), (.088, -.25), (.088, -.172)], BLACK, PAINT, s)
    lathe(p, [(.088, -.172), (.092, -.166), (.092, -.078), (.088, -.074)], WHITE_COOL, STONE, s)
    lathe(p, [(.086, -.074), (.086, .074)], BLUE_PALE, GLASS, s)
    lathe(p, [(.088, .074), (.092, .078), (.092, .166), (.088, .172)], WHITE_COOL, STONE, s)
    lathe(p, [(.088, .172), (.088, .25), (.083, .262), (.07, .27)], BLACK, PAINT, s)
    disc(p, (0, 0), .07, BLACK, PAINT, s, .27)
    disc(p, (0, 0), .07, BLACK, PAINT, s, -.27, up=False)
    for sign in (-1, 1):
        for z in np.linspace(.19, .245, 4):
            torus(p, (0, 0, sign * z), .089, .0035, CHARCOAL, PAINT, s, 4, 'z')
        torus(p, (0, 0, sign * .172), .09, .0045, GOLD, GILT, s, 5, 'z')
        torus(p, (0, 0, sign * .075), .088, .004, GOLD_PALE, GILT, s, 4, 'z')
    for k, z in enumerate(np.linspace(-.066, .066, 7)):
        cylinder(p, (0, 0, z - .008), .062, .016, tone(LIGHT_BLUE, .6 + .4 * (k % 2)), GLOW, 16)
    for j in range(8):
        a = j / 8 * 2 * math.pi
        strut(p, (math.cos(a) * .074, math.sin(a) * .074, -.07), (math.cos(a) * .074, math.sin(a) * .074, .07), .006, .006,
              mix(LIGHT_BLUE, LIGHT_WHITE, .4), GLOW)
    blob(p, (.0925, 0, .13), .008, LIGHT_RED, GLOW, 1, 0.0, 3)
    for j in range(10):
        a = j / 10 * 2 * math.pi
        tube(p, [(math.cos(a) * .046, math.sin(a) * .046, -.27), (math.cos(a) * .046, math.sin(a) * .046, -.3)], .0055, GOLD, GILT, 6)
    cylinder(p, (0, 0, -.29), .022, .02, GOLD_PALE, GILT, 16)
    torus(p, (0, 0, .29), .045, .008, BLACK, PAINT, 20, 5, 'x')
    return centred(p)


def ledger_page():
    """A page of the Ledger of Names, blown out of the Archive: heavy ivory paper aged darker at its edges, curled back
    at the sides and lifting at a corner, ruled in red with a gold-leaf ornament in its head corner and rows of names
    in black ink (strokes, never letters); its bound edge (-y) is torn where it left the Ledger. The writing faces
    +x; 0.32 x 0.45, centred."""
    rng = np.random.default_rng(611)
    p = Part('SM_CN_LedgerPage', (CLOTH, GILT))
    W, H, nu, nv = .16, .225, 10, 14

    def surface(u, v):  # u across (-1 the bound edge), v up; the page curls back at both sides
        x = -.045 * u * u + .014 * math.sin(math.pi * v * .9) - .03 * max(0.0, v) ** 2 * max(0.0, u)
        return np.array([x, u * W, v * H])

    verts = []
    for i in range(nu + 1):
        for j in range(nv + 1):
            v = -1 + 2 * j / nv
            u = -1 + 2 * i / nu
            if i == 0:  # torn from the binding: a ragged edge
                u = -1 + .05 * (.5 + .5 * float(noise2(v * 4.0, 0.0, 61))) + .02 * (j % 2)
            verts.append(surface(u, v))

    def aged(q):
        u, v = q[1] / W, q[2] / H
        edge = max(abs(u), abs(v))
        return tone(IVORY, (.98 - .28 * max(0.0, edge - .7) / .3) * (.93 + .07 * float(noise2(u * 6, v * 6, 62))))
    cols = [aged(q) for q in verts]
    faces = []
    for i in range(nu):
        for j in range(nv):
            faces.append([i * (nv + 1) + j, (i + 1) * (nv + 1) + j, (i + 1) * (nv + 1) + j + 1, i * (nv + 1) + j + 1])
    p.add(verts, faces, cols, CLOTH, True)
    p.add(np.asarray(verts) - (.0015, 0, 0), [f[::-1] for f in faces], cols, CLOTH, True)

    def mark(u0, u1, v0, v1, colour, slot, pieces_u=2, pieces_v=1, lift=.0012):
        """Ink or leaf laid on the page between u0-u1 and v0-v1, in pieces so it follows the curl."""
        us, vs = np.linspace(u0, u1, pieces_u + 1), np.linspace(v0, v1, pieces_v + 1)
        for a, b in zip(us, us[1:]):
            for c, d in zip(vs, vs[1:]):
                pts = [surface(a, c), surface(b, c), surface(b, d), surface(a, d)]
                polygon(p, [q + (lift, 0, 0) for q in pts], colour, slot, toward=(1, 0, 0))
    for r in range(17):
        v = .76 - r * .098
        u = -.5 + rng.uniform(0, .06)
        while u < .84:
            n = rng.uniform(.06, .24)
            mark(u, min(u + n, .88), v - .016, v + .016, tone(CHARCOAL, rng.uniform(.7, 1.3)), CLOTH)
            u += n + rng.uniform(.04, .08)
    mark(-.6, -.585, -.94, .9, RED, CLOTH, 1, 8)
    mark(-.9, .9, .845, .855, RED, CLOTH, 8, 1)
    mark(-.9, .9, .87, .878, RED, CLOTH, 8, 1)
    mark(-.9, -.72, .9, .985, GOLD, GILT, 2, 1)
    diamond = [surface(-.81, .91), surface(-.74, .9425), surface(-.81, .975), surface(-.88, .9425)]
    polygon(p, [q + (.0022, 0, 0) for q in diamond], RED, CLOTH, toward=(1, 0, 0))
    return centred(p)


def seed_pod():
    """Orsolya's Starlace seed pod: a lantern husk worn to lace, five-lobed (star-shaped in section), gold veins along
    its crests and valleys and in rings across them, some cells still filled with white papery membrane and the gold
    seeds showing through the open ones, under a calyx of five red sepals on a black stem. 0.46 tall (stem up),
    centred."""
    rng = np.random.default_rng(621)
    p = Part('SM_CN_SeedPod', (LEAF, DARK))
    lobes, per = 5, 4
    n = lobes * per
    z_lo, z_hi = -.2, .13
    levels = np.linspace(z_lo, z_hi, 10)

    def radius(z):  # a lantern: pointed below, full in the middle, drawn in under the calyx
        t = (z - z_lo) / (z_hi - z_lo)
        return .006 + .124 * math.sin(math.pi * min(1.0, .04 + .93 * t)) ** .8 * (1 - .25 * t)

    def point(z, k):
        a = 2 * math.pi * k / n
        return np.array([math.cos(a), math.sin(a), 0.0]) * radius(z) * (.78 + .22 * math.cos(lobes * a)) + (0, 0, z)

    for k in range(0, n, per // 2):  # crests and valleys
        tube(p, [point(z, k) for z in levels], .0035 if k % per == 0 else .0025, vary(GOLD_STRAW, rng, .1), LEAF, 5)
    for z in levels[1:-1]:
        loop = [point(z, k) for k in range(n)]
        tube(p, loop + [loop[0]], .0018, vary(GOLD_STRAW, rng, .1), LEAF, 4, cap=False)
    for i in range(len(levels) - 1):
        for k in range(n):
            if rng.uniform() < .45:
                continue  # worn through: the lace
            q = [point(levels[i], k), point(levels[i], k + 1), point(levels[i + 1], k + 1), point(levels[i + 1], k)]
            c = np.mean(q, 0)
            polygon(p, q, tone(WHITE_PURE, rng.uniform(.82, .98)), LEAF, toward=c - (0, 0, c[2]))
    for k in range(7):
        a, h = rng.uniform(0, 2 * math.pi), rng.uniform(-.09, .03)
        r = .022 if k else 0.0
        blob(p, (math.cos(a) * r, math.sin(a) * r, h), (.026, .026, .034), vary(GOLD_GRASS, rng, .1), LEAF, 1, .12, 630 + k)
    top = np.array([0, 0, z_hi])
    for k in range(lobes):
        a = math.radians(72 * k + 36 + rng.uniform(-8, 8))
        d = np.array([math.cos(a), math.sin(a), 0.0])
        pts = [top, top + d * .04 + (0, 0, .005), top + d * .065 - (0, 0, .03), top + d * .075 - (0, 0, .06)]
        ribbon(p, pts, np.array([.008, .02, .016, .003]), vary(RED_DEEP, rng, .1), LEAF, normal=(0, 0, 1))
    stem = bezier(top, top + (0, 0, .05), top + (.01, 0, .09), top + (.025, .005, .125), 5)
    tube(p, stem, np.linspace(.007, .0045, 5), BLACK, DARK, 6)
    return centred(p)


# ---------------------------------------------------------------- augmentations

def aug_shell(p, accent):
    """Every augmentation floats in the same gold armillary, so the five read as one family (as the Center's do): a
    horizontal and an upright ring of gold, each with a fine bead along both edges, bosses where they cross, and a
    thread of the augmentation's own light inside the horizontal ring."""
    R = .465
    for axis in ('z', 'x'):
        torus(p, (0, 0, 0), R, .028, GOLD, GILT, 56, 8, axis)
    for off in (-.024, .024):
        torus(p, (0, 0, off), R + .012, .008, GOLD_PALE, GILT, 56, 4, 'z')
        torus(p, (off, 0, 0), R + .012, .008, GOLD_PALE, GILT, 56, 4, 'x')
    for s in (-1, 1):
        blob(p, (0, s * R, 0), .05, GOLD_PALE, GILT, 1, 0.0, 9)
    # 2.4 cm thick: at 1.4 cm the thread that tells the five apart was under a pixel from 10 m.
    torus(p, (0, 0, 0), R - .045, .012, accent, GLOW, 56, 4, 'z')


def vane(part, spine, widths, thick, normal, colour, slot, back=.5):
    """A thin blade along a spine (feathers, a sword's blade): a diamond section reaching widths[i] to one side and
    back * widths[i] to the other across the plane facing `normal`, thick[i] to either face, capped at both ends."""
    spine = np.asarray(spine, np.float64)
    nrm = np.asarray(normal, np.float64)
    nrm = nrm / np.linalg.norm(nrm)
    widths = np.broadcast_to(np.asarray(widths, np.float64), (len(spine),))
    thick = np.broadcast_to(np.asarray(thick, np.float64), (len(spine),))
    rings = []
    for i, q in enumerate(spine):
        d = spine[min(i + 1, len(spine) - 1)] - spine[max(i - 1, 0)]
        side = np.cross(nrm, d)
        side /= np.linalg.norm(side)
        rings.append([q + side * widths[i], q + nrm * thick[i], q - side * widths[i] * back, q - nrm * thick[i]])
    loft(part, rings, colour, slot, lambda c: spine[np.argmin(np.linalg.norm(spine - c, axis=1))], smooth=False)
    for ring, d in ((rings[0], spine[0] - spine[1]), (rings[-1], spine[-1] - spine[-2])):
        polygon(part, ring, colour, slot, toward=d)


def aug_health():
    """Health Augmentation: a heart of red light, bright at its core, in a fine gold setting, inside the gold
    armillary. About 1 m, centred."""
    p = Part('SM_CN_AugHealth', (GILT, GLOW))
    ts = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    hy = 16 * np.sin(ts) ** 3
    hz = 13 * np.cos(ts) - 5 * np.cos(2 * ts) - 2 * np.cos(3 * ts) - np.cos(4 * ts) + 2.7  # its height centred on 0
    outline = np.stack([np.zeros_like(ts), hy * .0125, hz * .0125], 1)
    rings = [outline * math.cos(f) + (.11 * math.sin(f), 0, 0) for f in np.linspace(-1.25, 1.25, 9)]

    def light(verts):
        return [tone(LIGHT_RED, .5 + .5 * max(0.0, 1 - float(np.linalg.norm(q)) / .24)) for q in verts]
    loft(p, rings, light, GLOW, lambda c: (0, 0, 0))
    for ring, x in ((rings[0], -.11 * math.sin(1.25)), (rings[-1], .11 * math.sin(1.25))):
        centre = np.array([x, 0, 0])
        verts = np.concatenate([[centre], ring])
        faces = []
        for j in range(len(ring)):
            f = [0, 1 + j, 1 + (j + 1) % len(ring)]
            if np.cross(verts[f[1]] - verts[0], verts[f[2]] - verts[0])[0] * x < 0:
                f = f[::-1]
            faces.append(f)
        p.add(verts, faces, light(verts), GLOW, True)
    setting = outline * 1.04
    # In two halves capped at the notch and the tip: one closed tube folded back on itself at those cusps and turned
    # its faces inside out at the notch.
    half = len(setting) // 2
    for run in (setting[:half + 1], np.concatenate([setting[half:], setting[:1]])):
        tube(p, run, .011, GOLD, GILT, 6)
    aug_shell(p, LIGHT_RED)
    return centred(p)


def aug_katana():
    """Katana Augmentation: a short curved blade of light-blue hardened light with a core of light along it, a gold
    collar and guard ringed with red light, a black-wrapped grip with gold ornaments and a gold pommel, inside the
    gold armillary. About 1 m, centred."""
    p = Part('SM_CN_AugKatana', (GILT, GLOW, GLASS, CLOTH))
    ts = np.linspace(0, 1, 12)
    spine = [(0, .03 * t * t, -.1 + .5 * t) for t in ts]  # the curve (sori): the edge is on the convex side (-y)
    vane(p, spine, .036 * (1 - ts ** 4) + .002, .009 * (1 - ts ** 3) + .0015, (1, 0, 0), mix(BLUE_PALE, WHITE_COOL, .3), GLASS, .55)
    # The core of light fills half the blade's width along its whole curve (a 1 cm strip read as nothing past 10 m,
    # and the glass alone is faint), and stays inside the glass: half its width and 60% of its thickness.
    cts = np.linspace(.02, .97, 10)
    vane(p, [(0, .03 * t * t, -.1 + .5 * t) for t in cts], .5 * (.036 * (1 - cts ** 4) + .002), .6 * (.009 * (1 - cts ** 3) + .0015),
         (1, 0, 0), mix(LIGHT_BLUE, LIGHT_WHITE, .35), GLOW, 1.0)
    bevel_box(p, (0, 0, -.11), (.016, .045, .02), GOLD_PALE, GILT, .004)
    cylinder(p, (0, 0, -.145), .085, .016, GOLD, GILT, 24)
    torus(p, (0, 0, -.137), .085, .008, GOLD_PALE, GILT, 24, 4, 'z')
    annulus(p, (0, 0), .055, .065, LIGHT_RED, GLOW, 32, -.1275)
    annulus(p, (0, 0), .055, .065, LIGHT_RED, GLOW, 32, -.1465, up=False)
    tube(p, [(0, 0, -.145), (0, 0, -.36)], [.021, .019], BLACK, CLOTH, 10)
    for z in np.linspace(-.17, -.34, 6):
        torus(p, (0, 0, z), .021, .004, CHARCOAL, CLOTH, 12, 4, 'z')
    for s in (-1, 1):
        blob(p, (s * .02, 0, -.25), (.006, .014, .02), GOLD, GILT, 1, .1, 4)
    cylinder(p, (0, 0, -.385), .024, .025, GOLD, GILT, 16)
    aug_shell(p, LIGHT_WHITE)
    return centred(p)


def aug_pistol():
    """Pistol Augmentation: a faceted gold core in a cluster of three steel barrels with gold breech caps and muzzle
    rings, gold light in the muzzles, two steel clamp rings and a ring of gold light round the core, inside the
    gold armillary. About 1 m, centred."""
    p = Part('SM_CN_AugPistol', (GILT, METAL, GLOW))
    blob(p, (0, 0, 0), .11, GOLD, GILT, 1, 0.0, 17, smooth=False)
    torus(p, (0, 0, 0), .115, .008, LIGHT_GOLD, GLOW, 24, 4, 'x')
    for k in range(3):
        a = math.radians(90 + 120 * k)
        y, z = math.cos(a) * .13, math.sin(a) * .13
        tube(p, [(-.2, y, z), (.3, y, z)], .03, SLATE, METAL, 12)
        # The muzzle ring is open: a bore with the light at its bottom, 2 mm before the barrel's end (the light was a disc
        # 0.5 mm in front of a solid gold cap). Built along z and turned onto +x.
        bore = scratch(p)
        lathe(bore, [(.036, 0.0), (.036, .04)], GOLD, GILT, 12)
        lathe(bore, [(.036, .04), (.021, .04)], GOLD, GILT, 12, smooth=False)
        lathe(bore, [(.021, .04), (.021, .03)], GOLD, GILT, 12)
        lathe(bore, [(.0295, 0.0), (.036, 0.0)], GOLD, GILT, 12, smooth=False)
        disc(bore, (0, 0), .021, LIGHT_GOLD, GLOW, 12, .032)
        merge(p, bore, rot_y(-90), (.27, y, z))
        tube(p, [(-.23, y, z), (-.19, y, z)], .034, GOLD_PALE, GILT, 12)
    for x in (-.1, .16):
        torus(p, (x, 0, 0), .13, .042, CHARCOAL, METAL, 24, 8, 'x')
    aug_shell(p, LIGHT_GOLD)
    return centred(p)


def aug_defense():
    """Defense Augmentation: a hexagonal shield facing +x, its domed face of light-blue glazed ceramic in a gold rim
    with a gold boss and a fine gold inner hexagon, a ring of light-blue light behind it, inside the gold armillary.
    About 1 m, centred."""
    p = Part('SM_CN_AugDefense', (GILT, TILE, GLOW))

    def hexagon(r, x):  # pointy-topped, in the y-z plane
        return [(x, math.cos(math.radians(90 + 60 * k)) * r, math.sin(math.radians(90 + 60 * k)) * r) for k in range(6)]
    dome = [(.3, 0.0), (.22, .03), (.12, .048)]
    rings = [hexagon(-0.0 + .3, -.04)] + [hexagon(r, x) for r, x in dome]
    loft(p, rings, lambda verts: [tone(BLUE, .85 + .15 * (1 - float(np.hypot(q[1], q[2])) / .3)) for q in verts], TILE,
         lambda c: (-.1, 0, 0), smooth=False)
    peak = np.array([.055, 0, 0])
    last = rings[-1]
    for j in range(6):
        polygon(p, [last[j], last[(j + 1) % 6], peak], BLUE, TILE, toward=(1, 0, 0))
    polygon(p, hexagon(.3, -.04), tone(BLUE, .8), TILE, toward=(-1, 0, 0))
    rim = hexagon(.305, -.005)
    tube(p, rim + [rim[0]], .02, GOLD, GILT, 6, cap=False)
    inner = hexagon(.16, .0425)
    tube(p, inner + [inner[0]], .006, GOLD_PALE, GILT, 5, cap=False)
    blob(p, (.05, 0, 0), .05, GOLD, GILT, 2, 0.0, 3, squash=(.6, 1, 1))
    torus(p, (-.08, 0, 0), .22, .012, LIGHT_BLUE, GLOW, 36, 5, 'x')
    aug_shell(p, LIGHT_BLUE)
    return centred(p)


def aug_agility():
    """Agility Augmentation: two wings of four feathers each, white lacquer shading to light-blue hardened light at
    the tips, gold quills, spreading from a heart of light, inside the gold armillary. About 1 m, centred."""
    p = Part('SM_CN_AugAgility', (PAINT, GLASS, GLOW, GILT))
    light = mix(LIGHT_BLUE, LIGHT_WHITE, .5)
    for side in (-1, 1):
        for k in range(4):
            base = np.array([0, side * .03, -.1 + .02 * k])
            ang = math.radians(24 + 21 * k)
            length = .42 - .05 * k
            out = np.array([0, side * math.sin(ang), math.cos(ang)])
            bow = np.array([0, -side * math.cos(ang), math.sin(ang)]) * .04  # each feather curves back toward the body
            spine = bezier(base, base + out * length * .35, base + out * length * .7 + bow, base + out * length + bow * 1.6, 10)
            t = np.linspace(0, 1, 10)
            widths = .05 * np.sin(np.pi * np.clip(.08 + .92 * t, 0, 1)) ** .6 + .002
            cut = 7  # the outer part of each feather is hardened light
            vane(p, spine[:cut + 1], widths[:cut + 1], .006, (1, 0, 0), WHITE_PURE, PAINT, .35)
            vane(p, spine[cut:], widths[cut:], .005, (1, 0, 0), mix(BLUE_PALE, WHITE_COOL, .2), GLASS, .35)
            # A core of light in each tip, inside its glass (half its width, 60% of its thickness, clear of its ends),
            # so the hardened light reads past 10 m: the pale glass alone was lost against white stone.
            core = [spine[cut] + (spine[cut + 1] - spine[cut]) * .3, spine[cut + 1], spine[cut + 1] + (spine[-1] - spine[cut + 1]) * .75]
            reach = np.array([widths[cut] * .7 + widths[cut + 1] * .3, widths[cut + 1], widths[cut + 1] * .25 + widths[-1] * .75]) * .5
            vane(p, core, reach, .003, (1, 0, 0), light, GLOW, .35)
            back = (spine[0] - spine[1]) / np.linalg.norm(spine[0] - spine[1])
            tube(p, [spine[0] + back * .004] + list(spine[1:3]), .009, GOLD_PALE, GILT, 6)  # the quill's end shows past the vane's
    blob(p, (0, 0, -.08), .06, light, GLOW, 2, .05, 3)
    aug_shell(p, light)
    return centred(p)


# ---------------------------------------------------------------- pickups (BP_Pickup reskinned by Kind)

def pickup_health():
    """A health capsule: red light in a sealed cell between red lacquered end caps banded in gold, held in a white
    lacquered cage of four bars. About 0.5 m tall, centred."""
    p = Part('SM_CN_PickupHealth', (PAINT, GILT, GLOW))
    cylinder(p, (0, 0, -.16), .07, .32, LIGHT_RED, GLOW, 20)
    lathe(p, [(.1, .16), (.1, .2), (.085, .235), (.05, .25)], RED, PAINT, 24)
    lathe(p, [(.05, -.25), (.085, -.235), (.1, -.2), (.1, -.16)], RED, PAINT, 24)
    disc(p, (0, 0), .05, RED, PAINT, 24, .25)
    disc(p, (0, 0), .05, RED, PAINT, 24, -.25, up=False)
    annulus(p, (0, 0), .07, .1, RED_DEEP, PAINT, 24, .16, up=False)
    annulus(p, (0, 0), .07, .1, RED_DEEP, PAINT, 24, -.16)
    for z in (-.165, .165):
        torus(p, (0, 0, z), .1, .008, GOLD, GILT, 24, 4, 'z')
    for j in range(4):
        a = math.radians(45 + 90 * j)
        tube(p, [(math.cos(a) * .092, math.sin(a) * .092, -.165), (math.cos(a) * .092, math.sin(a) * .092, .165)], .012, WHITE_PURE, PAINT, 6)
    return centred(p)


def pickup_divinity():
    """A Divinity crystal: a double-pointed hexagonal crystal of light-blue hardened light with a core of light, a gold
    band round its waist. About 0.5 m tall, centred."""
    p = Part('SM_CN_PickupDivinity', (GLASS, GLOW, GILT))
    for s in (-1, 1):
        prism(p, (0, 0, -s * .02), (0, 0, s * .25), .1, BLUE_PALE, GLASS, 6, .45)
        # A core two thirds of the crystal's width (it was 0.4 of it: the pale glass hid it past 15 m); inside the glass.
        prism(p, (0, 0, -s * .01), (0, 0, s * .21), .065, LIGHT_BLUE, GLOW, 6, .55)
    torus(p, (0, 0, 0), .092, .014, GOLD, GILT, 24, 5, 'z')
    return centred(p)


def pickup_ammo():
    """An energy cell for the sidearm: a gold casing with machined grooves, a window of gold light behind gold bars,
    black steel end caps and a gold contact. About 0.5 m tall, centred."""
    p = Part('SM_CN_PickupAmmo', (GILT, METAL, GLOW))
    lathe(p, [(.085, -.2), (.09, -.195), (.09, -.06)], GOLD, GILT, 28)
    lathe(p, [(.09, .06), (.09, .195), (.085, .2)], GOLD, GILT, 28)
    cylinder(p, (0, 0, -.06), .084, .12, LIGHT_GOLD, GLOW, 28)
    annulus(p, (0, 0), .084, .09, GOLD, GILT, 28, -.06)            # the casing's edges round the window
    annulus(p, (0, 0), .084, .09, GOLD, GILT, 28, .06, up=False)
    for j in range(8):
        a = j / 8 * 2 * math.pi
        strut(p, (math.cos(a) * .087, math.sin(a) * .087, -.062), (math.cos(a) * .087, math.sin(a) * .087, .062), .014, .008, GOLD_PALE, GILT)
    for z in (-.15, -.1, .1, .15):
        torus(p, (0, 0, z), .09, .004, GOLD_DEEP, GILT, 28, 4, 'z')
    lathe(p, [(.085, .2), (.08, .23), (.06, .25)], CHARCOAL, METAL, 28)
    lathe(p, [(.06, -.25), (.08, -.23), (.085, -.2)], CHARCOAL, METAL, 28)
    disc(p, (0, 0), .06, CHARCOAL, METAL, 28, .25)
    disc(p, (0, 0), .06, CHARCOAL, METAL, 28, -.25, up=False)
    cylinder(p, (0, 0, .25), .02, .012, GOLD_PALE, GILT, 16)
    return centred(p)


MESHES = [hydro_bed, sluice, channel, board, pipe_bridge, buoy, pier, boat, furnace, crane, crane_bridge, cable_lock,
          workshop, pipe_rack, pylon, pylon_beam, spire, spire_gate, light_platform, light_ramp, lattice, crown_dais,
          cradle, freighter, crate, lift, barricade, current, still_point, light_cache, vault_door, kite, memory_core,
          ledger_page, seed_pod, aug_health, aug_katana, aug_pistol, aug_defense, aug_agility, pickup_health,
          pickup_divinity, pickup_ammo]
VARIANTS = {hydro_bed: 3}  # SM_CN_HydroBed (wheat), SM_CN_HydroBed1 (red chard), SM_CN_HydroBed2 (beans)

# Sizes (x, y, z metres) and pivots from Tools/conclave/README.md, for check.py. A 0 leaves that axis free where the
# README sizes only part of the mesh: the crane bridge's 0.6 is its deck's depth under the walk surface (z -0.6..0;
# its railing stands above), the light ramp's rise of 4 sits on its keel, the pipe bridge's footings set its width,
# and the current's 5 m ring stands on a basin that reaches below its pool.
CONTRACT = {
    'SM_CN_HydroBed': {'size': (3, 10, 1)},
    'SM_CN_HydroBed1': {'size': (3, 10, 1)},
    'SM_CN_HydroBed2': {'size': (3, 10, 1)},
    'SM_CN_Sluice': {'size': (1, 3, 3)},
    'SM_CN_Channel': {'size': (10, 1.2, .6)},
    'SM_CN_Board': {'size': (.4, 2, 2.2)},
    'SM_CN_PipeBridge': {'size': (12, 0, 4)},
    'SM_CN_Buoy': {'size': (3, 3, 1.2)},
    'SM_CN_Pier': {'size': (12, 3, 1)},
    'SM_CN_Boat': {'size': (5, 2, 1.5)},
    'SM_CN_Furnace': {'size': (6, 8, 10)},
    'SM_CN_Crane': {'size': (4, 22, 14)},
    'SM_CN_CraneBridge': {'size': (16, 4, 0), 'pivot': 'any'},
    'SM_CN_CableLock': {'size': (1, 1, 1), 'pivot': 'centre'},
    'SM_CN_Workshop': {'size': (10, 14, 8)},
    'SM_CN_PipeRack': {'size': (2, 10, 4)},
    'SM_CN_Pylon': {'size': (5, 5, 18)},
    'SM_CN_PylonBeam': {'size': (4, 4, BEAM_HEIGHT)},
    'SM_CN_Spire': {'size': (48, 48, 320)},
    'SM_CN_SpireGate': {'size': (2, 10, 9)},
    'SM_CN_LightPlatform': {'size': (8.66, 10, .8), 'pivot': 'any'},  # flats at +-x, where the climb's ramps arrive
    'SM_CN_LightRamp': {'size': (12, 3, 0), 'pivot': 'any'},
    'SM_CN_Lattice': {'size': (.5, 6, 5)},
    'SM_CN_CrownDais': {'size': (18, 18, 1)},
    'SM_CN_Cradle': {'size': (30, 12, 16)},
    'SM_CN_Freighter': {'size': (60, 18, 16)},
    'SM_CN_Crate': {'size': (2, 2, 2)},
    'SM_CN_Lift': {'size': (8, 8, 20)},
    'SM_CN_Barricade': {'size': (1, 8, 4)},
    'SM_CN_Current': {'size': (7, 7, 0), 'pivot': 'any'},
    'SM_CN_StillPoint': {'size': (6.8, 6.8, 0)},
    'SM_CN_LightCache': {'size': (1, 1, 1), 'pivot': 'centre'},
    'SM_CN_VaultDoor': {'size': (1, 6, 6)},
    'SM_CN_Kite': {'size': (0, .62, .94), 'pivot': 'centre'},
    'SM_CN_MemoryCore': {'size': (.18, .18, .64), 'pivot': 'centre'},
    'SM_CN_LedgerPage': {'size': (0, .32, .45), 'pivot': 'centre'},
    'SM_CN_SeedPod': {'size': (.24, .24, .46), 'pivot': 'centre'},
    'SM_CN_AugHealth': {'size': (1, 1, 1), 'pivot': 'centre'},
    'SM_CN_AugKatana': {'size': (1, 1, 1), 'pivot': 'centre'},
    'SM_CN_AugPistol': {'size': (1, 1, 1), 'pivot': 'centre'},
    'SM_CN_AugDefense': {'size': (1, 1, 1), 'pivot': 'centre'},
    'SM_CN_AugAgility': {'size': (1, 1, 1), 'pivot': 'centre'},
    'SM_CN_PickupHealth': {'size': (.2, .2, .5), 'pivot': 'centre'},
    'SM_CN_PickupDivinity': {'size': (.2, .2, .5), 'pivot': 'centre'},
    'SM_CN_PickupAmmo': {'size': (.18, .18, .51), 'pivot': 'centre'},
}
