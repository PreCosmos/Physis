"""Generate Physis HUD textures and gameplay meshes in Blender.

Run: flatpak run org.blender.Blender -b --python Tools/build_physis_ui.py [-- meshes | -- pad]
Writes Art/UI/*.png and Art/Meshes/*.fbx, then `outfit_operation play:ui_import`.
`-- pad` writes only the D-pad Left/Right, Start and Select glyphs (import them with aaa:ui_textures:<names>).
"""
import math
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'Art/UI'
MESHES = ROOT / 'Art/Meshes'
INK = np.array((.012, .022, .04))
STEEL = np.array((.05, .085, .12))
GOLD = np.array((1, .62, .2))
PALE = np.array((1, .9, .68))
TEAL = np.array((.25, 1, .8))
RED = np.array((1, .22, .14))


def grid(width, height):
    return np.meshgrid(np.arange(width) + .5, np.arange(height) + .5)


def polygon(x, y, points):
    # Signed distance to a polygon: negative inside.
    points = np.array(points, float)
    d = np.full(x.shape, 1e12)
    sign = np.ones(x.shape)
    for i in range(len(points)):
        a, b = points[i], points[i - 1]
        ex, ey = b - a
        wx, wy = x - a[0], y - a[1]
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
        d = np.minimum(d, (wx - ex * t) ** 2 + (wy - ey * t) ** 2)
        c1 = y >= a[1]
        c2 = y < b[1]
        c3 = ex * wy > ey * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        sign = np.where(flip, -sign, sign)
    return sign * np.sqrt(d)


def segments(x, y, points):
    points = np.array(points, float)
    d = np.full(x.shape, 1e12)
    for a, b in zip(points, points[1:]):
        ex, ey = b - a
        wx, wy = x - a[0], y - a[1]
        t = np.clip((wx * ex + wy * ey) / max(ex * ex + ey * ey, 1e-6), 0, 1)
        d = np.minimum(d, (wx - ex * t) ** 2 + (wy - ey * t) ** 2)
    return np.sqrt(d)


def bolt(start, end, rng, parts=11, wander=.1):
    start, end = np.array(start, float), np.array(end, float)
    normal = np.array((end[1] - start[1], start[0] - end[0]))
    points = [start + (end - start) * i / parts + normal * rng.uniform(-wander, wander) for i in range(parts + 1)]
    points[0], points[-1] = start, end
    return points


def edge(d, width=1.2):
    return np.clip(1 - np.abs(d) / width, 0, 1)


def inside(d):
    return np.clip(.5 - d, 0, 1)


def glow(d, reach):
    return np.exp(-np.maximum(d, 0) / reach)


def save(name, colour, alpha):
    height, width = alpha.shape
    pixels = np.dstack((np.clip(colour, 0, 1), np.clip(alpha, 0, 1)))[::-1].astype(np.float32)
    image = bpy.data.images.new(name, width, height, alpha=True, float_buffer=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(UI / (name + '.png'))
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)


def over(colour, alpha, tint, amount):
    amount = np.clip(amount, 0, 1)[..., None]
    colour = colour * (1 - amount) + tint * amount
    return colour, np.maximum(alpha, amount[..., 0])


def add(colour, alpha, tint, amount):
    amount = np.clip(amount, 0, 1)
    return colour + tint * amount[..., None], np.maximum(alpha, amount)


def plate(width, height, shape, seed, accent=GOLD):
    # A dark glass plate with a double gold rim and veins of lightning.
    rng = np.random.default_rng(seed)
    x, y = grid(width, height)
    d = polygon(x, y, shape)
    colour = np.zeros((height, width, 3))
    alpha = np.zeros((height, width))
    shade = (y / height)[..., None]
    fill = INK * (1 - shade) + STEEL * shade
    colour, alpha = over(colour, alpha, accent * .55, glow(d, 12) * .4 * (d > 0))
    colour = np.where((d < 0)[..., None], fill, colour)
    alpha = np.where(d < 0, .88, alpha)
    lines = (np.sin((x + y) * .9) > .96) * .05 * inside(d)
    colour = colour + accent * lines[..., None]
    inner = d + 7
    colour, alpha = add(colour, alpha, accent * .55, edge(inner, 1) * .7 * inside(d))
    # Veins hug the top and bottom edges so text stays clear.
    for index in range(4):
        band = (.1, .17) if index % 2 else (.84, .91)
        start = rng.uniform((width * .05, height * band[0]), (width * .75, height * band[1]))
        end = start + rng.uniform((width * .08, -height * .03), (width * .22, height * .03))
        vein = segments(x, y, bolt(start, end, rng))
        colour, alpha = add(colour, alpha, accent, (edge(vein, 1.1) * .8 + glow(vein, 4) * .22) * inside(d))
    colour, alpha = add(colour, alpha, PALE, edge(d, 1.6))
    colour, alpha = add(colour, alpha, accent, glow(np.abs(d), 3) * .6)
    return colour, alpha


def vitals():
    w, h = 1024, 256
    shape = [(14, 26), (930, 26), (1010, 106), (1010, 190), (960, 232), (70, 232), (14, 176)]
    save('T_UI_Vitals', *plate(w, h, shape, 3))


def panels():
    w, h = 1024, 200
    save('T_UI_Panel', *plate(w, h, [(40, 14), (984, 14), (1010, 40), (1010, 160), (984, 186), (40, 186), (14, 160), (14, 40)], 8))
    save('T_UI_PanelScan', *plate(w, h, [(14, 14), (960, 14), (1010, 64), (1010, 186), (64, 186), (14, 136)], 11, TEAL))
    w, h = 512, 256
    save('T_UI_Weapon', *plate(w, h, [(60, 14), (498, 14), (498, 196), (452, 242), (14, 242), (14, 60)], 5))


def bars():
    for name, low, high in (('T_UI_BarHealth', np.array((.95, .18, .06)), np.array((1, .72, .3))),
                            ('T_UI_BarDivinity', np.array((.12, .55, .95)), np.array((.75, 1, .95)))):
        w, h = 512, 32
        x, y = grid(w, h)
        band = (x / w)[..., None]
        sheen = (1 - np.abs(y / h - .32) * 2.2)[..., None]
        colour = (low * (1 - band) + high * band) * (.72 + .5 * np.clip(sheen, 0, 1))
        ticks = (np.mod(x + y * .6, 40) < 2)[..., None]
        save(name, np.where(ticks, colour * .55, colour), np.ones((h, w)))


def marker(name, tint, draw):
    w = h = 256
    x, y = grid(w, h)
    d = draw(x, y)
    colour = np.zeros((h, w, 3))
    alpha = np.zeros((h, w))
    colour, alpha = add(colour, alpha, tint, glow(d, 7) * .55)
    colour, alpha = add(colour, alpha, tint * .6 + .4, edge(d, 2.4))
    save(name, colour, alpha)


def corners(x, y):
    m, r = 34, 62
    paths = [[(m + r, m), (m, m), (m, m + r)], [(256 - m - r, m), (256 - m, m), (256 - m, m + r)],
             [(m + r, 256 - m), (m, 256 - m), (m, 256 - m - r)], [(256 - m - r, 256 - m), (256 - m, 256 - m), (256 - m, 256 - m - r)]]
    return np.min([segments(x, y, p) - 2 for p in paths], axis=0)


def diamond_lock(x, y):
    c = 128
    ring = np.abs(np.hypot(x - c, y - c) - 86) - 1.5
    gap = np.abs(np.abs(np.arctan2(y - c, x - c)) % (math.pi / 2) - math.pi / 4) < .36
    ring = np.where(gap, 1e3, ring)
    points = np.min([polygon(x, y, [(c + a * 106, c + b * 106), (c + a * 66 - b * 16, c + b * 66 - a * 16), (c + a * 66 + b * 16, c + b * 66 + a * 16)])
                     for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))], axis=0)
    return np.minimum(ring, points)


def reticle(x, y):
    c = 128
    ring = np.abs(np.hypot(x - c, y - c) - 62) - 1
    ring = np.where(np.abs(np.abs(np.arctan2(y - c, x - c)) % (math.pi / 2) - math.pi / 4) > .52, 1e3, ring)
    dot = np.hypot(x - c, y - c) - 4
    ticks = np.min([segments(x, y, [(c + a * 26, c + b * 26), (c + a * 46, c + b * 46)]) - 1 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))], axis=0)
    return np.minimum(np.minimum(ring, dot), ticks)


def icons():
    w = h = 256
    x, y = grid(w, h)
    blade = polygon(x, y, [(214, 18), (238, 22), (232, 46), (92, 186), (70, 164)])
    guard = polygon(x, y, [(48, 150), (62, 136), (120, 194), (106, 208)])
    grip = polygon(x, y, [(72, 176), (84, 188), (36, 236), (24, 224)])
    sword = np.minimum(np.minimum(blade, guard), grip)
    slide = polygon(x, y, [(26, 80), (226, 80), (232, 92), (232, 122), (26, 122)])
    frame = polygon(x, y, [(70, 122), (172, 122), (160, 142), (116, 142), (100, 222), (48, 222), (62, 146)])
    gun = np.minimum(slide, frame)
    drop = polygon(x, y, [(128, 22), (206, 128), (128, 236), (50, 128)])
    bullet = polygon(x, y, [(100, 228), (156, 228), (156, 96), (128, 28), (100, 96)])
    cross = np.minimum(polygon(x, y, [(106, 40), (150, 40), (150, 216), (106, 216)]), polygon(x, y, [(40, 106), (216, 106), (216, 150), (40, 150)]))
    for name, d, tint in (('T_UI_IconSword', sword, PALE), ('T_UI_IconGun', gun, PALE), ('T_UI_IconDivinity', drop, np.array((.5, .9, 1))),
                          ('T_UI_IconAmmo', bullet, GOLD), ('T_UI_IconHealth', cross, np.array((1, .4, .25)))):
        shade = (1 - y / h * .45)[..., None]
        colour = np.zeros((h, w, 3))
        alpha = np.zeros((h, w))
        colour, alpha = add(colour, alpha, tint, glow(d, 9) * .55)
        colour, alpha = over(colour, alpha, tint * shade, inside(d))
        colour, alpha = add(colour, alpha, np.array((1, 1, 1)), edge(d + 2, 1.5) * .7)
        save(name, colour, alpha)


LETTERS = {
    'A': [[(0, 1), (.5, 0), (1, 1)], [(.2, .62), (.8, .62)]],
    'X': [[(0, 0), (1, 1)], [(1, 0), (0, 1)]],
    'Y': [[(0, 0), (.5, .5), (1, 0)], [(.5, .5), (.5, 1)]],
    'L': [[(.1, 0), (.1, 1), (.9, 1)]],
    'R': [[(.1, 1), (.1, 0), (.7, 0), (.95, .14), (.95, .36), (.7, .5), (.1, .5)], [(.5, .5), (1, 1)]],
    'T': [[(0, 0), (1, 0)], [(.5, 0), (.5, 1)]],
    'S': [[(.95, .1), (.7, 0), (.3, 0), (.05, .14), (.05, .36), (.3, .48), (.7, .52), (.95, .64), (.95, .86), (.7, 1), (.3, 1), (.05, .9)]],
    'B': [[(.1, 0), (.1, 1), (.72, 1), (.95, .86), (.95, .64), (.72, .5), (.1, .5)], [(.1, 0), (.68, 0), (.88, .12), (.88, .36), (.68, .5)]],
    '3': [[(.05, .1), (.3, 0), (.72, 0), (.95, .14), (.95, .36), (.7, .5), (.35, .5)], [(.7, .5), (.95, .64), (.95, .86), (.72, 1), (.3, 1), (.05, .9)]],
}


def word(x, y, text, cx, cy, height, stroke):
    # Draws capitals from the stroke table, centred on cx, cy.
    width = height * .72
    gap = height * .24
    left = cx - (len(text) * width + (len(text) - 1) * gap) / 2
    top = cy - height / 2
    d = np.full(x.shape, 1e9)
    for index, letter in enumerate(text):
        origin = left + index * (width + gap)
        for path in LETTERS[letter]:
            d = np.minimum(d, segments(x, y, [(origin + a * width, top + b * height) for a, b in path]) - stroke)
    return d


def pad_icon(name, shape, label, tint, size=None, stroke=9):
    h = w = 192
    x, y = grid(w, h)
    d = shape(x, y)
    colour = np.zeros((h, w, 3))
    alpha = np.zeros((h, w))
    colour, alpha = add(colour, alpha, tint, glow(d, 5) * .5)
    colour, alpha = over(colour, alpha, INK * (1.5 - y[..., None] / h), inside(d))
    colour, alpha = add(colour, alpha, tint, edge(d + 3, 3))
    if label:
        colour, alpha = over(colour, alpha, tint * .55 + .45, inside(word(x, y, label, 96, 96, size or 86, stroke)))
    save(name, colour, alpha)


def circle(x, y):
    return np.hypot(x - 96, y - 96) - 84


def pill(x, y):
    return polygon(x, y, [(14, 56), (34, 40), (158, 40), (178, 56), (178, 138), (158, 152), (34, 152), (14, 138)])


def trigger(x, y):
    return polygon(x, y, [(46, 14), (146, 14), (172, 44), (178, 176), (14, 176), (20, 44)])


def stick(x, y):
    ring = np.hypot(x - 96, y - 96)
    return ring - 84


def dpad(arm):
    def draw(x, y):
        return np.minimum(polygon(x, y, [(64, 10), (128, 10), (128, 182), (64, 182)]), polygon(x, y, [(10, 64), (182, 64), (182, 128), (10, 128)]))
    return draw


def controller():
    # Xbox-layout face colours, shoulder and stick glyphs in the HUD's gold and ink.
    for label, tint in (('A', (.35, .9, .35)), ('B', (1, .3, .25)), ('X', (.3, .6, 1)), ('Y', (1, .82, .25))):
        pad_icon('T_Pad_' + label, circle, label, np.array(tint), 104, 11)
    for label in ('LB', 'RB'):
        pad_icon('T_Pad_' + label, pill, label, GOLD, 64, 7)
    for label in ('LT', 'RT'):
        pad_icon('T_Pad_' + label, trigger, label, GOLD, 72, 8)
    for label in ('LS', 'RS', 'L3'):
        pad_icon('T_Pad_' + label, stick, label, PALE, 68, 7)
    for name, points in (('DU', [(96, 24), (72, 58), (120, 58)]), ('DD', [(96, 168), (72, 134), (120, 134)])):
        dpad_arrow(name, points)


def dpad_arrow(name, points):
    # A D-pad with the pressed arm's arrow lit in gold.
    h = w = 192
    x, y = grid(w, h)
    d = dpad(name)(x, y)
    colour = np.zeros((h, w, 3))
    alpha = np.zeros((h, w))
    colour, alpha = add(colour, alpha, PALE, glow(d, 5) * .5)
    colour, alpha = over(colour, alpha, INK * 1.2, inside(d))
    colour, alpha = add(colour, alpha, PALE, edge(d + 3, 3))
    colour, alpha = over(colour, alpha, GOLD, inside(polygon(x, y, points)))
    save('T_Pad_' + name, colour, alpha)


def controller_extra():
    # Added 2026-11-04 for the Center's prompts and the Map: D-pad Left/Right, and the small round Start (Menu,
    # three lines) and Select (View, two overlapping frames) buttons. These are the fallbacks when Steam Input
    # has no glyph (UPhysisSteamInputLibrary::GetPadGlyph tokens DL, DR, Menu, View).
    dpad_arrow('DL', [(24, 96), (58, 72), (58, 120)])
    dpad_arrow('DR', [(168, 96), (134, 72), (134, 120)])
    h = w = 192
    x, y = grid(w, h)
    shade = INK * (1.5 - y[..., None] / h)
    mark = PALE * .55 + .45
    for name in ('Menu', 'View'):
        d = np.hypot(x - 96, y - 96) - 78
        colour = np.zeros((h, w, 3))
        alpha = np.zeros((h, w))
        colour, alpha = add(colour, alpha, PALE, glow(d, 5) * .5)
        colour, alpha = over(colour, alpha, shade, inside(d))
        colour, alpha = add(colour, alpha, PALE, edge(d + 3, 3))
        if name == 'Menu':
            lines = np.minimum.reduce([segments(x, y, [(62, row), (130, row)]) - 8 for row in (68, 96, 124)])
            colour, alpha = over(colour, alpha, mark, inside(lines))
        else:
            back = segments(x, y, [(50, 56), (118, 56), (118, 112), (50, 112), (50, 56)]) - 6
            colour, alpha = over(colour, alpha, mark, inside(back))
            front = polygon(x, y, [(74, 80), (142, 80), (142, 136), (74, 136)])
            colour, alpha = over(colour, alpha, shade, inside(front - 6))
            colour, alpha = over(colour, alpha, mark, inside(np.abs(front) - 6))
        save('T_Pad_' + name, colour, alpha)


def visor():
    w, h = 1024, 576
    x, y = grid(w, h)
    u, v = x / w * 2 - 1, y / h * 2 - 1
    frame = np.clip((u * u + v * v) * .7 - .28, 0, 1) ** 1.4
    scan = (np.sin(y * .9) > .75) * .035
    q, r = x / 46, y / 40
    hexes = np.abs(np.sin(q * math.pi + np.floor(r) * math.pi / 2)) * np.abs(np.sin(r * math.pi))
    mesh = (hexes < .05) * .045
    alpha = frame * .55 + scan + mesh
    colour = np.ones((h, w, 3)) * (TEAL * .7)
    rim = np.minimum.reduce([np.abs(np.abs(u) - .94) * w / 2, np.abs(np.abs(v) - .9) * h / 2])
    keep = (np.abs(u) > .78) & (np.abs(v) > .68)
    colour, alpha = add(colour, alpha, TEAL, edge(rim, 1.8) * keep)
    save('T_UI_VisorFrame', colour, alpha)


def box(name, size, location=(0, 0, 0), bevel=.08, material=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    item = bpy.context.object
    item.name = name
    item.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = item.modifiers.new('Bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    bpy.ops.object.shade_smooth()
    if material:
        item.data.materials.append(material)
    return item


def material(name):
    made = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    return made


def export(name, parts):
    bpy.ops.object.select_all(action='DESELECT')
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    for part in parts:
        bpy.context.view_layer.objects.active = part
        for mod in list(part.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.export_scene.fbx(filepath=str(MESHES / (name + '.fbx')), use_selection=True, axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, mesh_smooth_type='FACE', add_leaf_bones=False)
    bpy.ops.object.delete()


def meshes():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dark, ivory, glowing = material('M_Dark'), material('M_Ivory'), material('M_Glow')
    # A heavy Federation sidearm: 24 long, muzzle along +X, grip at the origin.
    parts = [box('Slide', (24, 3.2, 3.6), (7, 0, 6), .35, ivory),
             box('Under', (19, 2.8, 2.2), (6, 0, 3.4), .3, dark),
             box('Grip', (4.6, 2.8, 12), (-1, 0, -2.6), .5, dark),
             box('Guard', (7, 1, 1), (4, 0, -.5), .2, dark),
             box('Core', (15, 3.4, .7), (8, 0, 6.2), .1, glowing),
             box('Muzzle', (2.4, 2.6, 2.6), (19.6, 0, 5.8), .3, glowing),
             box('Sight', (1.6, .9, 1), (-3, 0, 8.2), .1, dark)]
    export('SM_Physis_Gun', parts)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=22)
    crystal = bpy.context.object
    crystal.scale = (.7, .7, 1.25)
    crystal.data.materials.append(glowing)
    export('SM_Pickup_Divinity', [crystal])
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=13, depth=34)
    body = bpy.context.object
    body.data.materials.append(ivory)
    bpy.ops.object.shade_smooth()
    export('SM_Pickup_Health', [body, box('Band', (28, 28, 8), (0, 0, 0), .6, glowing)])
    export('SM_Pickup_Ammo', [box('Clip', (20, 30, 34), (0, 0, 0), 1.2, dark), box('Cell', (22, 12, 22), (0, 0, 2), .5, glowing)])


UI.mkdir(parents=True, exist_ok=True)
MESHES.mkdir(parents=True, exist_ok=True)
if 'pad' in __import__('sys').argv:
    controller_extra()  # only the four glyphs added on 2026-11-04
else:
    vitals();panels();bars();icons();visor();controller();controller_extra()
    marker('T_UI_Lock', RED, diamond_lock)
    marker('T_UI_ScanMarker', np.array((1, 1, 1)), corners)
    marker('T_UI_Reticle', TEAL, reticle)
    marker('T_UI_ReticleGun', GOLD, reticle)
print('PHYSIS_UI_DONE')
if 'meshes' in __import__('sys').argv:
    meshes()
