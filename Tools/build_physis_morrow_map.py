"""Render Morrow's map for the pause menu: Art/UI/T_UI_MapMorrow.png.

The valley from straight above in its own colours at first light: frosted turf, grey rock and snow where it climbs
into the peaks, the reservoir's ice behind the dam, the Gorge as the dark cut it is, the streets, every house as a
small slate block (from scatter.json), and the set pieces as plain shapes: the dam's crest and the Hold, the Dam Stair,
the millpond, the Ferry Bridge, the Glider Field and its hangar, the Telegraph House, the Schoolhouse, the chapels. No
text: the HUD writes the names.

Same frame as every level's map (physis_morrow_plan.MAP_HALF, north up, east right).
Run after Tools/build_physis_morrow.py:  python3 Tools/build_physis_morrow_map.py [--size 1024]   then morrow:map_art.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Art/Meshes/Morrow'
sys.path.insert(0, str(ROOT / 'Content/Python'))
import physis_morrow_plan as plan  # noqa: E402

E = plan.MAP_HALF
SUN = (.15, .65, .74)      # first light from the east
TURF, ROCK, SNOW, SURROUND = np.array((112, 124, 112), float), np.array((96, 100, 108), float), np.array((222, 228, 236), float), (14, 16, 22)
ICE, GORGE = np.array((170, 190, 206), float), np.array((60, 70, 82), float)
ROAD, LANE, STONE, SLATE, AMBER, MAGENTA, ROSE = (204, 204, 200), (176, 172, 162), (226, 224, 218), (52, 56, 66), (255, 170, 70), (230, 70, 190), (255, 140, 120)


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
    inside = (fx >= 0) & (fx <= nx - 1) & (fy >= 0) & (fy <= ny - 1)
    i, j = np.clip(fx.astype(int), 0, nx - 2), np.clip(fy.astype(int), 0, ny - 2)
    h = height[i, j]
    gx, gy = np.gradient(height, cell)
    sx, sy = gx[i, j], gy[i, j]
    n = np.stack([-sx, -sy, np.ones_like(sx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    shade = np.clip((n * np.array(SUN)).sum(-1) / np.linalg.norm(SUN), 0, 1)
    slope = np.hypot(sx, sy)
    k = np.clip(slope / .8, 0, 1)[..., None]
    land = TURF * (1 - k) + ROCK * k
    snow = np.clip((h - 150.0) / 60.0, 0, 1)[..., None] * (1 - .5 * k)
    land = land * (1 - snow) + SNOW * snow
    rgb = land * (.55 + .6 * shade)[..., None]
    lake = (x > plan.CREST_X1) & (h < plan.ICE_Z)
    rgb = np.where(lake[..., None], ICE, rgb)
    gorge = (np.abs(x - (plan.GORGE_X + plan.GORGE_WAVE * np.sin(y / plan.GORGE_PERIOD + .6))) < plan.GORGE_FLOOR) & (np.hypot(x / plan.RIM[0], y / plan.RIM[1]) < .97)
    rgb = np.where(gorge[..., None], GORGE, rgb)
    rgb = np.where((~inside)[..., None], np.array(SURROUND, float), rgb)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)

    def px(mx, my):
        return ((my + E) / (2 * E) * size, (E - mx) / (2 * E) * size)

    def m(v):
        return v / (2 * E) * size

    def disc(at, rad, fill, outline=None):
        qx, qy = px(*at[:2])
        draw.ellipse([qx - m(rad), qy - m(rad), qx + m(rad), qy + m(rad)], fill=fill, outline=outline, width=max(1, int(m(2))))

    def rect(at, half_x, half_y, fill):
        qx, qy = px(*at[:2])
        draw.rectangle([qx - m(half_y), qy - m(half_x), qx + m(half_y), qy + m(half_x)], fill=fill)

    for name, kind, half, points in plan.PATHS:
        draw.line([px(a, b) for a, b in points], fill=ROAD if kind == 'road' else LANE, width=max(2, int(m(half * 2))))
    scatter = json.loads((DATA / 'scatter.json').read_text())
    for key, rows in scatter.items():
        if key.startswith('SM_HN_House'):
            for r in rows:
                cx, cy = px(r[0] / 100, r[1] / 100)
                s = m(3.6)
                draw.polygon([(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)], fill=SLATE)
    # The dam's crest across the valley, the Hold on it, the Dam Stair up the embankment.
    reach = plan.RIM[1] * (1 - (plan.CREST[0] / plan.RIM[0]) ** 2) ** .5
    a, b = px(plan.CREST[0], -reach), px(plan.CREST[0], reach)
    draw.line([a, b], fill=STONE, width=max(3, int(m(16))))
    rect(plan.HOLD, 7.0, 7.0, (88, 92, 70))
    draw.line([px(plan.STAIR_FOOT[0], 0), px(plan.CREST_X0, 0)], fill=(196, 196, 196), width=max(2, int(m(10))))
    disc(plan.POND, plan.POND[2], tuple(int(c) for c in ICE))
    disc(plan.FIELD, plan.FIELD_RADIUS, (138, 148, 132), STONE)
    rect((plan.FIELD[0] + 30.0, plan.FIELD[1] + 20.0), 7.0, 9.0, (110, 96, 80))
    disc(plan.ROCK, plan.ROCK[2], (120, 120, 126))
    rect(plan.TELEGRAPH, 2.5, 2.0, STONE)
    rect((plan.SCHOOL[0] + 14.0, plan.SCHOOL[1]), 4.5, 9.0, STONE)
    rect((plan.MILL[0] + 2.0, plan.MILL[1] - 10.0), 5.0, 4.0, STONE)
    rect(plan.ICEHOUSE, 4.5, 3.5, (160, 160, 158))
    for spot in (plan.CHAPEL, plan.SQUARE):
        rect((spot[0] + 14.0, spot[1] + 12.0), 4.5, 3.0, STONE)
    draw.line([px(*plan.BRIDGE_SOUTH), px(*plan.BRIDGE_NORTH)], fill=(150, 112, 80), width=max(2, int(m(5))))
    disc(plan.CREST, 6.0, None, MAGENTA)
    img = img.filter(ImageFilter.SMOOTH)
    out = ROOT / 'Art/UI/T_UI_MapMorrow.png'
    img.save(out)
    print('wrote', out, img.size)


if __name__ == '__main__':
    main()
