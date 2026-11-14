"""Draws the gold ability emblems for the Pause Menu.

Run: flatpak run org.blender.Blender -b --python Tools/build_physis_icons.py
Blender is only used for numpy and PNG output. Writes Art/UI/Abilities/T_Ability_<Name>.png.
"""
import math
import pathlib

import bpy
import numpy as np

ROOT = pathlib.Path(bpy.path.abspath(__file__)).resolve().parent.parent
OUT = ROOT / 'Art/UI/Abilities'
SIZE = 256
OUT.mkdir(parents=True, exist_ok=True)
y, x = np.mgrid[0:SIZE, 0:SIZE].astype(float)
x = (x + .5) / SIZE * 2 - 1
y = 1 - (y + .5) / SIZE * 2
radius = np.hypot(x, y)
angle = np.arctan2(y, x)


def stroke(distance, width):
    """Antialiased line coverage from a distance field."""
    return np.clip((width - np.abs(distance)) * SIZE / 2 + .5, 0, 1)


def fill(distance):
    return np.clip(-distance * SIZE / 2 + .5, 0, 1)


def segment(ax, ay, bx, by):
    px, py, dx, dy = x - ax, y - ay, bx - ax, by - ay
    t = np.clip((px * dx + py * dy) / (dx * dx + dy * dy), 0, 1)
    return np.hypot(px - dx * t, py - dy * t)


def arc(r, start, end):
    """Distance to an arc of radius r between two angles in degrees."""
    a0, a1 = math.radians(start), math.radians(end)
    inside = ((angle - a0) % (2 * math.pi)) <= ((a1 - a0) % (2 * math.pi))
    tip = np.minimum(np.hypot(x - r * math.cos(a0), y - r * math.sin(a0)), np.hypot(x - r * math.cos(a1), y - r * math.sin(a1)))
    return np.where(inside, np.abs(radius - r), tip)


def leaf(cx, cy, length, width, turn):
    c, s = math.cos(turn), math.sin(turn)
    u = (x - cx) * c + (y - cy) * s
    v = -(x - cx) * s + (y - cy) * c
    return np.hypot(u / length, v / width) - 1


def blade(turn, length=.62):
    c, s = math.cos(turn), math.sin(turn)
    shaft = segment(-c * length, -s * length, c * length, s * length)
    guard = segment(-c * .38 - s * .16, -s * .38 + c * .16, -c * .38 + s * .16, -s * .38 - c * .16)
    return np.minimum(stroke(shaft, .045), 1) + stroke(guard, .04)


def emblem(shape):
    ring = stroke(radius - .9, .028) + stroke(radius - .82, .01)
    glyph = np.clip(shape, 0, 1)
    coverage = np.clip(ring + glyph, 0, 1)
    shade = .78 + .22 * (y + 1) / 2
    gold = np.stack((1.0 * shade, .78 * shade, .36 * shade), -1)
    disc = fill(radius - .9) * .55
    alpha = np.clip(coverage + disc, 0, 1)
    colour = gold * coverage[..., None] + np.array((.02, .05, .09)) * (disc * (1 - coverage))[..., None]
    colour = colour / np.maximum(alpha, 1e-4)[..., None]
    return np.dstack((colour, alpha))


def petals(count):
    out = np.zeros_like(x)
    for index in range(count):
        turn = math.pi / 2 + index * 2 * math.pi / 9
        out += fill(leaf(.36 * math.cos(turn), .36 * math.sin(turn), .3, .1, turn))
    return out + stroke(radius - .1, .03)


SHAPES = {
    'ScanVisor': stroke(np.hypot(x / .62, y / .3) - 1, .02 / .3) * .9 + fill(radius - .14) + stroke(radius - .24, .02),
    'BladeChain': blade(math.radians(45)) + blade(math.radians(135)) * .9,
    'PerfectParry': stroke(segment(-.5, .45, .5, .45), .03) + stroke(arc(.55, 200, 340), .035) + stroke(segment(-.5, .45, -.52, .1), .03) + stroke(segment(.5, .45, .52, .1), .03) + blade(math.radians(-60), .4) * .8,
    'Dodge': stroke(arc(.45, 30, 300), .04) + fill(leaf(.39, .22, .14, .06, math.radians(120))),
    'Sidearm': fill(np.maximum(np.abs(x + .05) - .45, np.abs(y - .12) - .1)) + fill(np.maximum(np.abs(x + .3) - .12, np.abs(y + .18) - .26)) + stroke(segment(.5, .12, .7, .12), .02),
    'DivinityShot': fill(np.abs(x) / .3 + np.abs(y) / .5 - 1) + stroke(segment(-.7, 0, -.36, 0), .025) + stroke(segment(.36, 0, .7, 0), .025),
}
for count, name in enumerate(('RisingCut', 'CrescentStep', 'FallingMoon', 'ThousandPetals', 'SeveringWind', 'FinalBloom'), 4):
    SHAPES[name] = petals(count)

for name, shape in SHAPES.items():
    pixels = emblem(shape)
    image = bpy.data.images.new('T_Ability_' + name, SIZE, SIZE, alpha=True)
    image.pixels = np.flipud(pixels).astype(np.float32).ravel()
    image.filepath_raw = str(OUT / ('T_Ability_%s.png' % name))
    image.file_format = 'PNG'
    image.save()
print('ICONS DONE', len(SHAPES), flush=True)
