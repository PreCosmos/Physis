"""Generate the opening cinematic's sky, title, ships, station hull and soundtrack.

Run: flatpak run org.blender.Blender -b --python Tools/build_physis_cinematic.py
Writes Art/UI, Art/Meshes and Art/Audio, then `outfit_operation play:cinema_build`.
"""
import math
import wave
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'Art/UI'
MESHES = ROOT / 'Art/Meshes'
AUDIO = ROOT / 'Art/Audio'
SECONDS = 42
RATE = 44100


def save(name, colour, alpha, folder=UI):
    height, width = alpha.shape
    pixels = np.dstack((np.clip(colour, 0, 1), np.clip(alpha, 0, 1)))[::-1].astype(np.float32)
    image = bpy.data.images.new(name, width, height, alpha=True, float_buffer=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(folder / (name + '.png'))
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)


def fractal(width, height, seed, turns=6):
    # Tileable-in-x cloud noise from layered random gratings.
    rng = np.random.default_rng(seed)
    y, x = np.meshgrid(np.linspace(0, 1, height, endpoint=False), np.linspace(0, 1, width, endpoint=False), indexing='ij')
    total = np.zeros((height, width))
    for octave in range(turns):
        scale = 2 ** octave
        for _ in range(8):
            kx = rng.integers(1, 3 * scale + 2)
            ky = rng.uniform(1, 2.2 * scale + 1)
            total += np.sin(2 * math.pi * (kx * x + ky * y) + rng.uniform(0, 6.3)) / scale
    return (total - total.min()) / (total.max() - total.min())


def sky():
    w, h = 4096, 2048
    rng = np.random.default_rng(12)
    a = fractal(w, h, 3)
    b = fractal(w, h, 9)
    lat = np.linspace(-1, 1, h)[:, None]
    lon = np.linspace(0, 2 * math.pi, w, endpoint=False)[None, :]
    # A band of galaxy crossing the sky, tilted by longitude.
    tilt = lat - .28 * np.sin(lon + .9)
    band = np.exp(-(tilt / .2) ** 2)
    glow = band * (.16 + a ** 2.2 * .95)
    dust = np.clip((b - .52) * 7, 0, 1) * band
    colour = np.zeros((h, w, 3))
    colour += glow[..., None] * np.array((.34, .24, .42))
    colour += (np.clip(a - .55, 0, 1) ** 2 * 5 * (1 - band * .4))[..., None] * np.array((.1, .24, .42))
    colour += (np.clip(b - .6, 0, 1) ** 2 * 4)[..., None] * np.array((.4, .13, .2))
    colour *= (1 - dust * .75)[..., None]
    # Bright galactic core behind the opening shot.
    cx, cy = w * .25, h * .44
    yy, xx = np.mgrid[0:h, 0:w]
    dx, dy = (xx - cx) / w * 2, (yy - cy) / h
    core = np.exp(-(dx * dx * 30 + dy * dy * 220)) * .32 + np.exp(-(dx * dx * 260 + dy * dy * 1800)) * .7
    colour += core[..., None] * np.array((1, .78, .55))
    for count, size, power in ((26000, 0, .55), (2600, 1, .9), (240, 2, 1.5)):
        sx = rng.integers(3, w - 3, count)
        sy = rng.integers(3, h - 3, count)
        tint = np.array((.75, .85, 1)) + rng.uniform(-.25, .25, (count, 1)) * np.array((-1, 0, 1))
        level = rng.uniform(.3, 1, (count, 1)) * power
        for ox in range(-size, size + 1):
            for oy in range(-size, size + 1):
                fall = 1 / (1 + ox * ox + oy * oy) ** 1.4
                colour[sy + oy, sx + ox] += tint * level * fall
    save('T_Sky_Space', colour, np.ones((h, w)))


STROKES = {
    'P': [[(0, 1), (0, 0), (.75, 0), (1, .15), (1, .38), (.75, .52), (0, .52)]],
    'H': [[(0, 0), (0, 1)], [(1, 0), (1, 1)], [(0, .5), (1, .5)]],
    'Y': [[(0, 0), (.5, .5), (1, 0)], [(.5, .5), (.5, 1)]],
    'S': [[(1, .1), (.72, 0), (.28, 0), (0, .14), (0, .36), (.28, .48), (.72, .52), (1, .64), (1, .86), (.72, 1), (.28, 1), (0, .9)]],
    'I': [[(.5, 0), (.5, 1)]],
}


def distance(x, y, points):
    points = np.array(points, float)
    d = np.full(x.shape, 1e12)
    for a, b in zip(points, points[1:]):
        ex, ey = b - a
        wx, wy = x - a[0], y - a[1]
        t = np.clip((wx * ex + wy * ey) / max(ex * ex + ey * ey, 1e-6), 0, 1)
        d = np.minimum(d, (wx - ex * t) ** 2 + (wy - ey * t) ** 2)
    return np.sqrt(d)


def spread(values, passes):
    # Soft glow by repeated FFT-free box smoothing along both axes.
    out = values
    for _ in range(passes):
        out = (out + np.roll(out, 3, 0) + np.roll(out, -3, 0) + np.roll(out, 3, 1) + np.roll(out, -3, 1)) / 5
    return out


def title():
    # The emblem: a ring broken by a lightning bolt, over the wordmark.
    w, h = 1536, 960
    x, y = np.meshgrid(np.arange(w) + .5, np.arange(h) + .5)
    rng = np.random.default_rng(4)
    cx, cy = w / 2, 300
    r = np.hypot(x - cx, y - cy)
    turn = np.arctan2(y - cy, x - cx)
    # Ring tapers to points where the bolt breaks it.
    taper = np.abs(np.sin(turn + .35))
    ring = np.abs(r - 208) - (3 + 15 * np.clip(taper, 0, 1))
    gap = np.abs(np.cos(turn + .35)) > .94
    ring = np.where(gap, 1e3, ring)
    inner = np.abs(r - 168) - 2
    inner = np.where(np.abs(np.cos(turn + .35)) > .9, 1e3, inner)
    bolt_shape = [(cx + 66, 12), (cx - 66, 268), (cx + 8, 268), (cx - 82, 588), (cx + 96, 240), (cx + 14, 240), (cx + 128, 12)]
    points = np.array(bolt_shape, float)
    bolt_d = np.full(x.shape, 1e12)
    inside_sign = np.ones(x.shape)
    for i in range(len(points)):
        a, c = points[i], points[i - 1]
        ex, ey = c - a
        wx, wy = x - a[0], y - a[1]
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
        bolt_d = np.minimum(bolt_d, (wx - ex * t) ** 2 + (wy - ey * t) ** 2)
        c1, c2, c3 = y >= a[1], y < c[1], ex * wy > ey * wx
        inside_sign = np.where((c1 & c2 & c3) | (~c1 & ~c2 & ~c3), -inside_sign, inside_sign)
    bolt_d = np.sqrt(bolt_d) * inside_sign
    word = np.full(x.shape, 1e9)
    left = 162
    for letter in 'PHYSIS':
        width = 30 if letter == 'I' else 158
        for path in STROKES[letter]:
            word = np.minimum(word, distance(x, y, [(left + a * width, 668 + b * 190) for a, b in path]))
        left += width + 84
    word -= 13
    rule = np.maximum(np.abs(y - 896) - 1.5, np.abs(x - cx) - 520)
    d = np.minimum.reduce((ring, inner, bolt_d, word, rule))
    # Veins of lightning hop between the letters.
    arc = np.full(x.shape, 1e9)
    for _ in range(11):
        start = rng.uniform((130, 640), (1380, 880))
        pts = [start]
        for _ in range(7):
            pts.append(pts[-1] + rng.uniform((10, -30), (46, 30)))
        arc = np.minimum(arc, distance(x, y, pts))
    solid = np.clip(.5 - d, 0, 1)
    arcs = np.clip(1.3 - arc, 0, 1) * np.exp(-np.maximum(word, 0) / 40)
    halo = spread(solid, 26)
    wide = spread(halo, 60)
    ramp = (1 - (np.mod(y, 480) / 480))[..., None]
    fill = np.array((1, .52, .13)) * (1 - ramp) + np.array((1, .95, .78)) * ramp
    edge = np.clip(1 - np.abs(d + 4) / 2.5, 0, 1)[..., None]
    gold = np.array((1, .62, .2))
    colour = fill * solid[..., None] + np.array((1, 1, .92)) * edge * .7 + gold * (halo * 1.5 + wide * .9 + arcs)[..., None]
    save('T_UI_Title', colour, np.clip(solid + halo * 1.3 + wide + arcs, 0, 1))


def plating(size, seed, tone, windows):
    # Recursive armour panels, seams, grime, markings and lit window rows.
    rng = np.random.default_rng(seed)
    value = np.zeros((size, size))
    seam = np.ones((size, size))
    light = np.zeros((size, size, 3))
    stack = [(0, 0, size, size, 0)]
    while stack:
        x, y, w, h, depth = stack.pop()
        if depth < 6 and (depth < 3 or rng.random() < .72) and max(w, h) > 40:
            if w > h * rng.uniform(.7, 1.4):
                cut = int(w * rng.uniform(.3, .7))
                stack += [(x, y, cut, h, depth + 1), (x + cut, y, w - cut, h, depth + 1)]
            else:
                cut = int(h * rng.uniform(.3, .7))
                stack += [(x, y, w, cut, depth + 1), (x, y + cut, w, h - cut, depth + 1)]
            continue
        value[y:y + h, x:x + w] = rng.uniform(.62, 1.08)
        seam[y:y + 2, x:x + w] = .28
        seam[y:y + h, x:x + 2] = .28
        seam[min(y + 2, size - 1):y + 3, x:x + w] *= 1.5
        kind = rng.random()
        if kind < windows and w > 60 and h > 24:
            pitch = rng.choice((10, 14, 18))
            lit = rng.random(((w - 12) // pitch + 1, )) < .72
            row = y + h // 2
            warm = np.array((1, .82, .5)) if rng.random() < .8 else np.array((.6, .85, 1))
            for index, on in enumerate(lit):
                if on:
                    light[row:row + 5, x + 6 + index * pitch:x + 6 + index * pitch + 6] = warm
        elif kind < windows + .05 and w > 70 and h > 30:
            band = np.mod(np.arange(w)[None, :] + np.arange(16)[:, None], 28) < 14
            value[y + 6:y + 22, x + 6:x + w - 6] = np.where(band[:16, :w - 12], 1.5, .2)
        elif kind < windows + .13 and w > 40 and h > 40:
            step = 14
            seam[y + 8:y + h - 8:step, x + 8:x + w - 8:step] = .45
    grime = fractal(size, size, seed + 1, 5)
    streak = np.clip(fractal(size, size, seed + 2, 4) - .48, 0, 1) * 3
    base = (value * seam * (.66 + grime * .6) * (1 - streak * .35))[..., None]
    return base * np.array(tone), light


def crystal(size, seed):
    # Toroidal Voronoi facets with bright veins along their edges.
    rng = np.random.default_rng(seed)
    points = rng.uniform(0, size, (170, 2))
    x, y = np.meshgrid(np.arange(size), np.arange(size))
    near = np.full((size, size), 1e12)
    second = np.full((size, size), 1e12)
    shade = np.zeros((size, size))
    tones = rng.uniform(.45, 1.1, len(points))
    for point, tone in zip(points, tones):
        dx = np.abs(x - point[0])
        dy = np.abs(y - point[1])
        d = np.minimum(dx, size - dx) ** 2 + np.minimum(dy, size - dy) ** 2
        closer = d < near
        second = np.where(closer, near, np.minimum(second, d))
        near = np.where(closer, d, near)
        shade = np.where(closer, tone, shade)
    width = np.sqrt(second) - np.sqrt(near)
    vein = np.exp(-width / 2.2)
    cloud = fractal(size, size, seed + 1, 5)
    colour = shade[..., None] * np.array((.13, .36, .46)) * (.6 + cloud[..., None] * .9) + np.exp(-width / 12)[..., None] * np.array((.1, .4, .45))
    glow = (vein ** 2 * np.clip(cloud * 2.2 - .55, .08, 1))[..., None] * np.array((.2, 1, .85))
    return colour, glow


def ship_textures():
    colour, light = plating(2048, 31, (.52, .56, .62), .16)
    save('T_Ship_Human_D', colour, np.ones((2048, 2048)))
    save('T_Ship_Human_E', light, np.ones((2048, 2048)))
    colour, light = crystal(1536, 41)
    save('T_Ship_First_D', colour, np.ones((1536, 1536)))
    save('T_Ship_First_E', light, np.ones((1536, 1536)))


def material(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def box(size, location, slot, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    item = bpy.context.object
    item.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    item.data.materials.append(slot)
    return item


def tube(radius, length, location, slot, axis='X', vertices=32, end=None, capped=True):
    bpy.ops.mesh.primitive_cone_add(end_fill_type='NGON' if capped else 'NOTHING', vertices=vertices, radius1=radius, radius2=end if end is not None else radius, depth=length, location=location,
                                    rotation=(0, math.pi / 2, 0) if axis == 'X' else (math.pi / 2, 0, 0) if axis == 'Y' else (0, 0, 0))
    item = bpy.context.object
    item.data.materials.append(slot)
    return item


def shard(length, width, location, slot, rotation=(0, 0, 0)):
    mesh = bpy.data.meshes.new('shard')
    half = width / 2
    verts = [(length * .62, 0, 0), (-length * .38, 0, 0), (0, half, 0), (0, -half, 0), (.1 * length, 0, half * .7), (.1 * length, 0, -half * .7)]
    faces = [(0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2), (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5)]
    mesh.from_pydata(verts, [], faces)
    item = bpy.data.objects.new('shard', mesh)
    bpy.context.collection.objects.link(item)
    item.location = location
    item.rotation_euler = rotation
    item.data.materials.append(slot)
    return item


def export(name, parts, tile=1400):
    bpy.ops.object.select_all(action='DESELECT')
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # Box-projected UVs so plating keeps one scale across every part.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=tile, scale_to_bounds=False, correct_aspect=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.export_scene.fbx(filepath=str(MESHES / (name + '.fbx')), use_selection=True, axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, mesh_smooth_type='FACE', add_leaf_bones=False)
    bpy.ops.object.delete()


def human(name, length, seed):
    # Federation warship: stacked armour, sponsons, turrets, hangars, drives. Nose along +X.
    hull, trim, lights, drive = material('M_Hull'), material('M_Trim'), material('M_Lights'), material('M_Drive')
    rng = np.random.default_rng(seed)
    k = length / 6000
    parts = [tube(760 * k, 4600 * k, (300 * k, 0, 0), hull, vertices=6, end=240 * k),
             box((3600 * k, 2100 * k, 420 * k), (-500 * k, 0, 120 * k), trim),
             box((2000 * k, 700 * k, 900 * k), (-1100 * k, 0, 760 * k), hull),
             box((1100 * k, 460 * k, 420 * k), (-1100 * k, 0, 1320 * k), trim),
             box((520 * k, 900 * k, 300 * k), (-800 * k, 0, 1620 * k), hull),
             box((60 * k, 760 * k, 60 * k), (-520 * k, 0, 1630 * k), lights)]
    # Sponsons with hangar mouths.
    for side in (-1, 1):
        parts.append(box((2400 * k, 520 * k, 560 * k), (-700 * k, side * 1240 * k, 100 * k), hull))
        parts.append(box((1500 * k, 40 * k, 240 * k), (-700 * k, side * 1520 * k, 100 * k), lights))
        for x in range(-1700, 400, 280):
            parts.append(box((110 * k, 620 * k, 680 * k), (x * k, side * 1240 * k, 100 * k), trim))
        for x in range(-1800, 1400, 700):
            parts.append(box((90 * k, 90 * k, 900 * k), (x * k, side * 1080 * k, 500 * k), trim, (side * .25, 0, 0)))
    # Dorsal and ventral turrets.
    for x in (-2100, -300, 300, 900, 1500):
        for up in (1, -1):
            z = (520 if x > -1000 else 780) * up * k
            parts.append(tube(170 * k, 130 * k, (x * k, 0, z), trim, axis='Z', vertices=12))
            for y in (-46, 46):
                parts.append(tube(26 * k, 460 * k, ((x + 290) * k, y * k, z + 60 * up * k), hull, vertices=8))
    # Drives with collars and fins.
    for y in (-760, 0, 760):
        for z in (120, 620) if y == 0 else (120,):
            parts.append(tube(330 * k, 1100 * k, (-2300 * k, y * k, z * k), trim, vertices=16))
            for x in (-2100, -2350, -2600):
                parts.append(tube(360 * k, 60 * k, (x * k, y * k, z * k), hull, vertices=16))
            parts.append(tube(270 * k, 90 * k, (-2880 * k, y * k, z * k), drive, vertices=16))
    for _ in range(40):
        x = rng.uniform(-2200, 1200) * k
        side = rng.choice((-1, 1))
        parts.append(box((rng.uniform(120, 420) * k, 26 * k, 34 * k), (x, side * 1062 * k, 120 * k), lights))
    # Greebles along every upper surface.
    for _ in range(130):
        parts.append(box((rng.uniform(60, 420) * k, rng.uniform(50, 300) * k, rng.uniform(20, 130) * k),
                         (rng.uniform(-2300, 1000) * k, rng.uniform(-1000, 1000) * k, 340 * k + rng.uniform(0, 40) * k), rng.choice((hull, trim))))
    for _ in range(60):
        x = rng.uniform(-1800, 2200)
        spread = 700 * (1 - (x + 1800) / 5200) + 120
        parts.append(box((rng.uniform(80, 300) * k, rng.uniform(40, 160) * k, rng.uniform(30, 90) * k),
                         (x * k, rng.uniform(-spread, spread) * k, 640 * (1 - (x + 1800) / 7000) * k), hull))
    parts.append(tube(14 * k, 1300 * k, (-1000 * k, 240 * k, 2300 * k), trim, axis='Z', vertices=6, end=2 * k))
    parts.append(tube(14 * k, 900 * k, (-1250 * k, -200 * k, 2100 * k), trim, axis='Z', vertices=6, end=2 * k))
    export(name, parts)


def first_one(name, length, seed):
    # First Ones vessel: suspended crystal around a luminous core. Nose along +X.
    crystal, core = material('M_Crystal'), material('M_CrystalGlow')
    rng = np.random.default_rng(seed)
    k = length / 6000
    parts = [shard(6000 * k, 1300 * k, (0, 0, 0), crystal), shard(3200 * k, 340 * k, (300 * k, 0, 0), core)]
    for index in range(14):
        turn = index / 14 * 2 * math.pi
        radius = rng.uniform(760, 1350) * k
        parts.append(shard(rng.uniform(1500, 3400) * k, rng.uniform(220, 540) * k,
                           (rng.uniform(-1100, 400) * k, math.cos(turn) * radius, math.sin(turn) * radius), crystal,
                           (rng.uniform(0, 3), rng.uniform(-.14, .14), rng.uniform(-.14, .14))))
    # A swarm of small fragments held in orbit.
    for _ in range(70):
        turn = rng.uniform(0, 2 * math.pi)
        radius = rng.uniform(900, 1900) * k
        parts.append(shard(rng.uniform(160, 620) * k, rng.uniform(50, 160) * k, (rng.uniform(-2400, 2000) * k, math.cos(turn) * radius, math.sin(turn) * radius),
                           rng.choice((crystal, crystal, core)), tuple(rng.uniform(0, 3, 3))))
    for x, size in ((-2000, 1200), (-1200, 1700), (-300, 1500), (700, 1000)):
        bpy.ops.mesh.primitive_torus_add(major_radius=size * k, minor_radius=40 * k, major_segments=64, minor_segments=6,
                                         location=(x * k, 0, 0), rotation=(0, math.pi / 2, 0))
        ring = bpy.context.object
        ring.data.materials.append(core)
        parts.append(ring)
        for index in range(12):
            turn = index / 12 * 2 * math.pi
            parts.append(shard(420 * k, 90 * k, (x * k, math.cos(turn) * (size + 180) * k, math.sin(turn) * (size + 180) * k), crystal, (turn, math.pi / 2, 0)))
    export(name, parts, 1100)


def station():
    # Meridian Station's outer hull around the playable decks, which run x 0 to 17000.
    hull, trim, lights = material('M_Hull'), material('M_Trim'), material('M_Lights')
    rng = np.random.default_rng(21)
    # Open-ended shells: the playable decks run through these, so no disc may cross them.
    parts = [tube(5200, 26000, (8500, 0, 0), hull, vertices=48, capped=False)]
    parts += [tube(7200, 2600, (x, 0, 0), trim, vertices=48) for x in (-1500, 19000)]
    parts += [tube(5200, 3400, (-5400, 0, 0), hull, vertices=48, end=2200), tube(5200, 3400, (23400, 0, 0), hull, vertices=48, end=2200),
              tube(420, 13000, (31000, 0, 0), trim, vertices=12, end=40)]
    for x in range(1500, 17000, 1800):
        parts.append(tube(5320, 220, (x, 0, 0), trim, vertices=48, capped=False))
    for _ in range(420):
        turn = rng.uniform(0, 2 * math.pi)
        y, z = math.cos(turn) * 5240, math.sin(turn) * 5240
        parts.append(box((rng.uniform(150, 640), 70, 70), (rng.uniform(-3000, 20000), y, z), lights, (turn, 0, 0)))
    for x in (2200, 8500, 14800):
        for turn in (.8, 2.3, 3.9, 5.5):
            y, z = math.cos(turn) * 5500, math.sin(turn) * 5500
            parts.append(box((1100, 900, 620), (x, y, z), trim, (turn, 0, 0)))
            parts.append(box((2200, 180, 180), (x + 1300, y * 1.08, z * 1.08), hull, (turn, 0, 0)))
    # Hangar mouth on the -Y flank: the camera flies into this light.
    parts.append(box((3400, 400, 1500), (300, -5240, 0), lights))
    export('SM_Station_Hull', parts, 2400)


def filtered(signal, low, high):
    spectrum = np.fft.rfft(signal)
    freq = np.fft.rfftfreq(len(signal), 1 / RATE)
    spectrum *= (freq >= low) & (freq <= high)
    return np.fft.irfft(spectrum, len(signal))


def soundtrack():
    rng = np.random.default_rng(77)
    n = SECONDS * RATE
    t = np.arange(n) / RATE
    left, right = np.zeros(n), np.zeros(n)
    # The void: a low breath that is there from the first frame.
    drone = filtered(rng.normal(0, 1, n), 18, 90)
    drone = drone / np.abs(drone).max()
    swell = np.clip(t / 5, 0, 1) * .24
    left += drone * swell * (1 + .15 * np.sin(t * .4))
    right += np.roll(drone, 1800) * swell
    fight = np.clip((t - 6.5) / 13, 0, 1) ** 1.7
    def place(sound, start, pan, level):
        begin = int(start * RATE)
        if begin >= n:
            return
        sound = sound[:n - begin]
        scale = level * fight[min(begin + len(sound) // 4, n - 1)]
        left[begin:begin + len(sound)] += sound * scale * (1 - pan) * 1.4
        right[begin:begin + len(sound)] += sound * scale * pan * 1.4
    for start in np.cumsum(rng.exponential(.62, 240)) + 6:
        length = int(rng.uniform(1.2, 2.8) * RATE)
        burst = filtered(rng.normal(0, 1, length), 24, rng.uniform(260, 900))
        burst = burst / np.abs(burst).max() * np.exp(-np.arange(length) / RATE * rng.uniform(1.6, 3.4))
        burst *= 1 - np.exp(-np.arange(length) / RATE * 120)
        place(burst, start, rng.uniform(.1, .9), rng.uniform(.3, .85))
    # Laser cannons: a falling pitch body, a low thump and a soft crack, never shrill.
    for index, start in enumerate(np.cumsum(rng.exponential(.3, 200)) + 7):
        heavy = index % 3 == 0
        length = int(rng.uniform(.34, .55) * RATE if heavy else rng.uniform(.2, .32) * RATE)
        when = np.arange(length) / RATE
        top, bottom = (rng.uniform(260, 340), rng.uniform(55, 80)) if heavy else (rng.uniform(420, 620), rng.uniform(90, 140))
        pitch = bottom + (top - bottom) * np.exp(-when * (11 if heavy else 16))
        phase = 2 * math.pi * np.cumsum(pitch) / RATE
        body = np.sin(phase) + .35 * np.sin(phase * 2) + .12 * np.sin(phase * 3)
        thump = np.sin(2 * math.pi * 52 * when) * np.exp(-when * 16)
        crack = filtered(rng.normal(0, 1, length), 180, 1300)
        crack = crack / np.abs(crack).max() * np.exp(-when * 48)
        shot = (body * .6 + thump * .7 + crack * .3) * np.exp(-when * (6 if heavy else 9)) * (1 - np.exp(-when * 500))
        place(shot, start, rng.uniform(.08, .92), rng.uniform(.14, .3))
    # Everything blooms in the hull, then is muffled once she is inside.
    room = np.exp(-np.arange(int(2.4 * RATE)) / RATE * 2.6) * rng.normal(0, 1, int(2.4 * RATE))
    for channel in (left, right):
        channel += np.fft.irfft(np.fft.rfft(channel) * np.fft.rfft(room, n), n) * .012
    inside = np.clip((t - 33.6) / .5, 0, 1)
    for channel in (left, right):
        channel[:] = channel * (1 - inside) + filtered(channel, 15, 240) * inside * 1.3
    klaxon = np.sign(np.sin(2 * math.pi * np.where(np.mod(t, 1.6) < .8, 196, 147) * t))
    alarm = filtered(klaxon, 90, 700) * np.clip(t - 34.2, 0, 1) * np.clip(np.mod(t, 1.6) * 10, 0, 1) * .07
    left += alarm
    right += alarm
    # Nothing above this survives into the mix.
    left, right = filtered(left, 0, 2600), filtered(right, 0, 2600)
    tail = np.clip((SECONDS - t) / 2.6, 0, 1)
    left *= tail
    right *= tail
    peak = max(np.abs(left).max(), np.abs(right).max())
    stereo = np.stack((left, right), 1) / peak * .92
    stereo = np.tanh(stereo * 1.3) / np.tanh(1.3)
    with wave.open(str(AUDIO / 'S_Opening.wav'), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((stereo * 32000).astype(np.int16).tobytes())


AUDIO.mkdir(parents=True, exist_ok=True)
sky()
title()
ship_textures()
soundtrack()
print('PHYSIS_ART_DONE')
bpy.ops.wm.read_factory_settings(use_empty=True)
human('SM_Ship_Cruiser', 6000, 1)
human('SM_Ship_Frigate', 2600, 2)
first_one('SM_Ship_Vigil', 7000, 3)
first_one('SM_Ship_Shard', 2800, 4)
station()
print('PHYSIS_CINEMA_DONE')
