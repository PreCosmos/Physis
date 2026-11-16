"""Render Arche's map for the pause menu: Art/UI/T_UI_MapArche.png.

Kathodos from straight above in its own colours: pale stone dust, blue-black rock where it is steep, the three tiers
read by their risers' shadow, the Great Chasm as the dark cut it is, the Cisterns' water, the roads, crystal as points
of ice blue (the Garden thick with them), and what was built as plain shapes: the Span's line, the Stairs, the Lens
Court's ring wall and the Lens, the Hearthold, the Ossuary. No text: the HUD writes the names.

Same frame as every level's map (physis_arche_plan.MAP_HALF, north up, east right).
Run after Tools/build_physis_arche.py:  python3 Tools/build_physis_arche_map.py [--size 1024]   then arche:map_art.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Art/Meshes/Arche'
sys.path.insert(0, str(ROOT / 'Content/Python'))
import physis_arche_plan as plan  # noqa: E402

E = plan.MAP_HALF
SUN = (-.45, .50, .74)
DUST, ROCK, SURROUND = np.array((150, 154, 162), float), np.array((58, 64, 80), float), (16, 19, 26)
WATER_SHALLOW, WATER_DEEP = np.array((92, 150, 172), float), np.array((30, 70, 104), float)
ROAD, TRAIL, STONE, VIOLET, ICE = (206, 208, 214), (176, 176, 178), (224, 226, 232), (176, 120, 255), (150, 220, 255)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, default=1024)
    size = parser.parse_args().size
    meta = json.loads((DATA / 'height.json').read_text())
    nx, ny, cell, hx, hy = int(meta['nx']), int(meta['ny']), meta['cell'], meta['half_x'], meta['half_y']
    height = np.frombuffer((DATA / 'height.bin').read_bytes(), '<f4', nx * ny).reshape(nx, ny).astype(float)
    row, col = np.mgrid[0:size, 0:size]
    x, y = E - (row + .5) / size * 2 * E, (col + .5) / size * 2 * E - E
    fx, fy = (x + hx) / cell, (y + hy) / cell
    inside = (fx >= 0) & (fx <= nx - 1.001) & (fy >= 0) & (fy <= ny - 1.001)
    i, j = np.clip(fx.astype(int), 0, nx - 2), np.clip(fy.astype(int), 0, ny - 2)
    u, v = np.clip(fx - i, 0, 1), np.clip(fy - j, 0, 1)
    h = height[i, j] * (1 - u) * (1 - v) + height[i + 1, j] * u * (1 - v) + height[i, j + 1] * (1 - u) * v + height[i + 1, j + 1] * u * v
    step = 2 * E / size
    dzdx, dzdy = -np.gradient(h, axis=0) / step, np.gradient(h, axis=1) / step
    normal = np.dstack((-dzdx, -dzdy, np.ones_like(h)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    light = np.clip(normal @ np.array(SUN), 0, 1)
    rock = np.clip((np.hypot(dzdx, dzdy) - .5) / .6, 0, 1)[..., None]
    tier = (np.clip((h - plan.TIER[0]) / (plan.TIER[2] - plan.TIER[0]), 0, 1) * .16)[..., None]
    colour = (DUST * (1 + tier)) * (1 - rock) + ROCK * rock
    colour = colour * (.45 + .75 * light)[..., None]
    deep = np.clip((plan.TIER[0] - 4 - h) / 30.0, 0, 1)[..., None]
    colour = colour * (1 - deep * .75)
    cx, cy, ax, ay = plan.CISTERNS
    lake = (h < plan.WATER) & (np.hypot((x - cx) / (ax + 12), (y - cy) / (ay + 12)) < 1)
    depth = np.clip(-h / 5.0, 0, 1)[..., None]
    colour = np.where(lake[..., None], WATER_SHALLOW * (1 - depth) + WATER_DEEP * depth, colour)
    colour = np.where(inside[..., None], colour, np.array(SURROUND, float))
    img = Image.fromarray(np.clip(colour, 0, 255).astype(np.uint8), 'RGB')
    d = ImageDraw.Draw(img, 'RGBA')
    scale = size / (2 * E)

    def at(px, py):
        return ((py + E) / (2 * E) * size, (E - px) / (2 * E) * size)

    def disc(px, py, radius, fill, outline=None):
        cx_, cy_ = at(px, py)
        r = max(1.0, radius * scale)
        d.ellipse((cx_ - r, cy_ - r, cx_ + r, cy_ + r), fill=fill, outline=outline)

    def box(px, py, half_x, half_y, fill):
        (x0, y0), (x1, y1) = at(px + half_x, py - half_y), at(px - half_x, py + half_y)
        d.rectangle((x0, y0, x1, y1), fill=fill, outline=(40, 44, 56))

    for _name, kind, half, points in plan.PATHS:
        d.line([at(px, py) for px, py in points], fill=(ROAD if kind == 'road' else TRAIL) + (255,), width=max(1, round(half * 2.2 * scale)), joint='curve')
    scatter = json.loads((DATA / 'scatter.json').read_text())
    for name, radius in (('SM_AV_Crystal0', 1.2), ('SM_AV_Crystal1', 1.8), ('SM_AV_Crystal2', 2.6), ('SM_AV_CrystalGreat', 6.0)):
        for r in scatter.get(name, ()):
            disc(r[0] / 100.0, r[1] / 100.0, radius * r[6], ICE + (230,))
    box(plan.chasm_x(plan.CHASM_CROSS_Y), plan.CHASM_CROSS_Y, 16.0, 3.0, STONE + (255,))
    for sx in (plan.STAIR1[0], plan.STAIR2[0]):
        box(sx - 6.0, 0.0, 9.0, 4.5, STONE + (255,))
    ccx, ccy = at(*plan.COURT)
    r = plan.COURT_WALL * scale
    d.ellipse((ccx - r, ccy - r, ccx + r, ccy + r), outline=STONE + (255,), width=max(2, round(2.4 * scale)))
    disc(plan.LENS[0], plan.LENS[1], 9.0, VIOLET + (255,), (60, 40, 110))
    gx, gy = at(*plan.GATE)
    d.ellipse((gx - 3, gy - 3, gx + 3, gy + 3), fill=VIOLET + (255,))
    for mx, my in plan.MIRRORS.values():
        disc(mx, my, 3.2, (255, 226, 160, 255), (120, 96, 50))
    for dx, dy in ((22, -24), (26, 2), (20, 28), (-26, -22), (-30, 6), (-22, 32)):
        box(plan.HEARTHOLD[0] + dx, plan.HEARTHOLD[1] + dy, 4.0, 3.5, STONE + (255,))
    box(plan.OSSUARY[0], plan.OSSUARY[1], 7.0, 11.0, STONE + (255,))
    disc(plan.LANDING[0], plan.LANDING[1], 5.0, ICE + (240,), (60, 110, 140))
    img = img.filter(ImageFilter.UnsharpMask(1.2, 40, 2))
    out = ROOT / 'Art/UI/T_UI_MapArche.png'
    img.save(out)
    print('wrote', out, img.size)


if __name__ == '__main__':
    main()
