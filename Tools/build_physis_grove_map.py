"""Render the Wounded Grove's map for the pause menu: Art/UI/T_UI_MapGrove.png.

A view straight down on the valley in natural colours: the land from the height grid (forest floor, bare rock where
it is steep, the cliffs of the rim), shaded under the level's late-afternoon sun from the south-west; the lake, the
headpond and the river; the Gully and the Rift as the dark cuts they are; the roads and trails of the world plan;
every scattered tree as its crown, the three great trees and the Heartwood as theirs; and what the Just built (the
Array's ring wall, the weir, the relay's mesa, the camp, Old Town, the campus blocks) as plain shapes. No text: the
HUD writes the names (Tools/blueprint_logic/grove_hud.py).

Same frame as the Center's and the Conclave's maps (physis_grove_plan.MAP_HALF metres, north up, east right), so the
pause menu's markers use one transform in every level:
  U = (y + E) / (2 E)          V = (E - x) / (2 E)          (0..1, origin top-left)

Run after Tools/build_physis_grove.py (height.bin, scatter.json):
  python3 Tools/build_physis_grove_map.py [--size 1024]
then grove:map_art in the editor, before grove_hud.py (whose PageMap names T_UI_MapGrove).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Art/Meshes/Grove'
sys.path.insert(0, str(ROOT / 'Content/Python'))
import physis_grove_plan as plan  # noqa: E402

E = plan.MAP_HALF
SUN = (-.52, -.60, .61)   # toward the sun: south-west, about 38 degrees up (x north, y east, z up)

FOREST = np.array((92, 108, 62), float)
MEADOW = np.array((128, 138, 78), float)
ROCK = np.array((132, 128, 118), float)
BLIGHT = np.array((120, 96, 104), float)
SURROUND = (22, 26, 24)
WATER_SHALLOW, WATER_DEEP = np.array((96, 150, 160), float), np.array((38, 84, 108), float)
ROAD, TRAIL = (176, 170, 156), (158, 140, 104)
CROWNS = {'SM_GV_Oak': ((66, 96, 44), 5.5), 'SM_GV_Beech': ((84, 118, 50), 5.0), 'SM_GV_Pine': ((40, 74, 46), 3.4), 'SM_GV_Birch': ((150, 146, 62), 3.0),
          'SM_GV_Snag': ((86, 80, 74), 1.6), 'SM_GV_Sapling': ((92, 124, 58), 1.4), 'SM_GV_Bush': ((78, 104, 52), 1.1)}
CONCRETE, STEEL, AMBER = (188, 184, 174), (120, 124, 128), (236, 170, 70)


def load():
    meta = json.loads((DATA / 'height.json').read_text())
    nx, ny = int(meta['nx']), int(meta['ny'])
    height = np.frombuffer((DATA / 'height.bin').read_bytes(), '<f4', nx * ny).reshape(nx, ny).astype(float)
    return meta, height


def land(meta, height, size):
    """The land as an RGB array (size x size), the frame beyond the grid in the surround's colour."""
    hx, hy, cell = meta['half_x'], meta['half_y'], meta['cell']
    row, col = np.mgrid[0:size, 0:size]
    x = E - (row + .5) / size * 2 * E          # north up
    y = (col + .5) / size * 2 * E - E
    fx, fy = (x + hx) / cell, (y + hy) / cell
    inside = (fx >= 0) & (fx <= height.shape[0] - 1.001) & (fy >= 0) & (fy <= height.shape[1] - 1.001)
    i, j = np.clip(fx.astype(int), 0, height.shape[0] - 2), np.clip(fy.astype(int), 0, height.shape[1] - 2)
    u, v = np.clip(fx - i, 0, 1), np.clip(fy - j, 0, 1)
    h = (height[i, j] * (1 - u) * (1 - v) + height[i + 1, j] * u * (1 - v) + height[i, j + 1] * (1 - u) * v + height[i + 1, j + 1] * u * v)
    step = 2 * E / size
    dzdx = -np.gradient(h, axis=0) / step      # rows run south
    dzdy = np.gradient(h, axis=1) / step
    normal = np.dstack((-dzdx, -dzdy, np.ones_like(h)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    light = np.clip(normal @ np.array(SUN), 0, 1)
    slope = np.hypot(dzdx, dzdy)
    rock = np.clip((slope - .55) / .5, 0, 1)[..., None]
    rim = np.hypot(x / plan.RIM[0], y / plan.RIM[1])
    open_ground = np.clip((rim - .9) / .12, 0, 1)[..., None] * .5
    colour = FOREST * (1 - open_ground) + MEADOW * open_ground
    blight = np.zeros_like(h)
    for bx, by, radius in plan.BLIGHT:
        blight = np.maximum(blight, np.clip(1 - np.hypot(x - bx, y - by) / radius, 0, 1))
    colour = colour * (1 - blight[..., None] * .55) + BLIGHT * blight[..., None] * .55
    colour = colour * (1 - rock) + ROCK * rock
    colour = colour * (.5 + .68 * light)[..., None]
    # Water: the lake at 0 m, the headpond north of the weir, the river's bed up to the Falls' pool.
    depth = np.clip(-h / 5.0, 0, 1)
    lake = (h < plan.WATER) & (np.hypot((x - plan.LAKE[0]) / (plan.LAKE[2] + 30), (y - plan.LAKE[1]) / (plan.LAKE[3] + 30)) < 1)
    water = WATER_SHALLOW * (1 - depth[..., None]) + WATER_DEEP * depth[..., None]
    colour = np.where(lake[..., None], water, colour)
    pond = (h < meta.get('headpond', plan.HEADPOND)) & (x > plan.WEIR[0] + 3) & (x < plan.WEIR[0] + 70) & (np.abs(y - plan.WEIR[1]) < 60) & ~lake
    colour = np.where(pond[..., None], WATER_SHALLOW * .92, colour)
    colour = np.where(inside[..., None], colour, np.array(SURROUND, float))
    return np.clip(colour, 0, 255).astype(np.uint8), (lambda px, py: ((py + E) / (2 * E) * size, (E - px) / (2 * E) * size))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, default=1024)
    size = parser.parse_args().size
    meta, height = load()
    rgb, at = land(meta, height, size)
    img = Image.fromarray(rgb, 'RGB')
    d = ImageDraw.Draw(img, 'RGBA')
    scale = size / (2 * E)   # pixels per metre

    def line(points, colour, width_m):
        d.line([at(x, y) for x, y in points], fill=colour, width=max(1, round(width_m * scale)), joint='curve')

    def disc(x, y, radius_m, colour, outline=None):
        cx, cy = at(x, y)
        r = max(1.0, radius_m * scale)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=colour, outline=outline)

    def box(x, y, half_x, half_y, colour):
        (x0, y0), (x1, y1) = at(x + half_x, y - half_y), at(x - half_x, y + half_y)
        d.rectangle((x0, y0, x1, y1), fill=colour, outline=(40, 40, 40))

    line(plan.RIVER, tuple(int(c) for c in WATER_SHALLOW) + (255,), plan.RIVER_HALF * 1.6)
    for _name, kind, half, points in plan.PATHS:
        line(points, (ROAD if kind == 'road' else TRAIL) + (255,), half * 2.2)
    # Crowns: every scattered tree, largest kinds last so the canopy reads as one.
    scatter = json.loads((DATA / 'scatter.json').read_text())
    for mesh in ('SM_GV_Bush', 'SM_GV_Sapling', 'SM_GV_Snag', 'SM_GV_Birch', 'SM_GV_Pine', 'SM_GV_Beech', 'SM_GV_Oak'):
        colour, radius = CROWNS[mesh]
        for index, row in enumerate(scatter.get(mesh, ())):
            x, y, s = row[0] / 100.0, row[1] / 100.0, row[6] if len(row) > 6 else 1.0
            tone = .86 + .28 * ((index * 7919) % 97) / 97.0
            disc(x, y, radius * s, tuple(min(255, int(c * tone)) for c in colour) + (235,))
    for x, y, _ in plan.GIANTS:
        disc(x, y, 16.0, (58, 90, 40, 245), (30, 50, 24))
    disc(plan.HEARTWOOD[0], plan.HEARTWOOD[1], 40.0, (70, 78, 50, 235), (30, 40, 24))
    disc(plan.HEARTWOOD[0], plan.HEARTWOOD[1], 8.5, (88, 70, 52, 255))
    # What the Just built.
    cx, cy = at(*plan.HEARTWOOD)
    r = plan.ARRAY_WALL * scale
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=CONCRETE + (255,), width=max(2, round(2.2 * scale)))
    gx, gy = at(*plan.GATE)
    d.ellipse((gx - 3, gy - 3, gx + 3, gy + 3), fill=AMBER + (255,))
    box(plan.WEIR[0], plan.WEIR[1], 4.0, plan.WEIR_HALF, CONCRETE + (255,))
    disc(plan.RELAY[0], plan.RELAY[1], 5.0, STEEL + (255,), (40, 40, 40))
    disc(plan.MAST[0], plan.MAST[1], 2.5, STEEL + (255,), (40, 40, 40))
    for x, y, hx, hy in ((50.0, -184.0, 4.0, 4.0), (90.0, -216.0, 8.0, 6.0), (132.0, -244.0, 6.0, 6.0), (164.0, -264.0, 8.0, 6.0)):
        box(x, y, hx, hy, CONCRETE + (255,))
    for x, y, hx, hy in ((-338.0, 248.0, 6.0, 5.0), (-306.0, 250.0, 4.5, 4.5), (-352.0, 290.0, 6.0, 5.0), (-322.0, 304.0, 4.5, 4.5), (-292.0, 300.0, 4.5, 3.5)):
        box(x, y, hx, hy, (150, 146, 138, 255))
    box(plan.OVERPASS[0], plan.OVERPASS[1], 13.0, 5.0, (150, 146, 138, 255))
    disc(plan.CAMP[0], plan.CAMP[1], 7.0, AMBER + (150,), (120, 90, 40))
    disc(plan.HOLLOW[0], plan.HOLLOW[1], 5.0, (150, 240, 200, 235), (60, 120, 100))
    img = img.filter(ImageFilter.UnsharpMask(1.2, 40, 2))
    out = ROOT / 'Art/UI/T_UI_MapGrove.png'
    img.save(out)
    print('wrote', out, img.size)


if __name__ == '__main__':
    main()
