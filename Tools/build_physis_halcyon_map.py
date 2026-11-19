"""Render Halcyon's map for the pause menu: Art/UI/T_UI_MapHalcyon.png.

Port Halcyon from straight above in its own colours: turf and worn earth on the slope, grey rock where it is steep,
the sea grey-green (darker where it is deep), the Breach as the dark cut it is, the streets, every house of the town as
a small slate block (from scatter.json), and the set pieces as plain shapes: the Mole, the Held Sea's ring, the
Bastion's court, the lighthouse, the crane, the Signal House, the Clocktower. No text: the HUD writes the names.

Same frame as every level's map (physis_halcyon_plan.MAP_HALF, north up, east right).
Run after Tools/build_physis_halcyon.py:  python3 Tools/build_physis_halcyon_map.py [--size 1024]   then halcyon:map_art.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Art/Meshes/Halcyon'
sys.path.insert(0, str(ROOT / 'Content/Python'))
import physis_halcyon_plan as plan  # noqa: E402

E = plan.MAP_HALF
SUN = (-.45, .50, .74)
TURF, EARTH, ROCK, SURROUND = np.array((88, 104, 66), float), np.array((138, 124, 100), float), np.array((92, 94, 96), float), (14, 18, 20)
SEA_SHALLOW, SEA_DEEP = np.array((84, 112, 108), float), np.array((34, 56, 62), float)
ROAD, LANE, STONE, SLATE, AMBER, MAGENTA = (196, 192, 182), (170, 160, 140), (222, 218, 208), (54, 58, 66), (255, 170, 70), (230, 60, 190)


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
    land = TURF * (1 - np.clip(slope / .8, 0, 1))[..., None] + ROCK * np.clip(slope / .8, 0, 1)[..., None]
    rgb = land * (.55 + .6 * shade)[..., None]
    depth = np.clip(-h / 12.0, 0, 1)[..., None]
    sea = SEA_SHALLOW * (1 - depth) + SEA_DEEP * depth
    wet = h < 0.0
    rgb = np.where(wet[..., None], sea, rgb)
    # beyond the height grid the sea runs on to the north; elsewhere a dark surround
    north = (~inside) & (x > plan.SHORE_X) & (np.abs(y) < 200)
    rgb = np.where(north[..., None], SEA_DEEP, rgb)
    rgb = np.where((~inside & ~north)[..., None], np.array(SURROUND, float), rgb)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)

    def px(mx, my):
        return ((my + E) / (2 * E) * size, (E - mx) / (2 * E) * size)

    def m(v):
        return v / (2 * E) * size

    for name, kind, half, points in plan.PATHS:
        draw.line([px(a, b) for a, b in points], fill=ROAD if kind == 'road' else LANE, width=max(2, int(m(half * 2))))
    scatter = json.loads((DATA / 'scatter.json').read_text())
    for key, rows in scatter.items():
        if key.startswith('SM_HN_House'):
            for r in rows:
                cx, cy = px(r[0] / 100, r[1] / 100)
                s = m(3.6)
                yaw = math.radians(r[4])
                corners = [(cx + (dx * math.cos(yaw) - dy * math.sin(yaw)) * s * 0 + dx * s, cy + dy * s) for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                draw.polygon(corners, fill=SLATE)
    # the Mole, the Held Sea's ring, the court, the Breach's bridge line
    draw.line([px(plan.MOLE_SOUTH[0], 0), px(plan.SEA_GATE[0], 0)], fill=STONE, width=max(3, int(m(9))))
    bx, by = px(*plan.BASTION)
    r = m(plan.HELD_RADIUS)
    draw.ellipse([bx - r, by - r, bx + r, by + r], outline=MAGENTA, width=max(2, int(m(3))))
    rc = m(plan.COURT_RADIUS)
    cx, cy = px(*plan.COURT)
    draw.ellipse([cx - rc, cy - rc, cx + rc, cy + rc], fill=(110, 112, 104), outline=STONE, width=max(2, int(m(3))))
    draw.rectangle([cx - m(13), cy - rc - m(16), cx + m(13), cy - rc], fill=(80, 82, 76))
    for (lx, ly), rad, colour in ((plan.LIGHTHOUSE, 4.6, (240, 240, 236)), (plan.CLOCK, 3.3, STONE), (plan.FOREMAN, 4.0, AMBER),
                                   (plan.HARBOURMASTER, 4.0, STONE)):
        qx, qy = px(lx, ly)
        draw.ellipse([qx - m(rad), qy - m(rad), qx + m(rad), qy + m(rad)], fill=colour)
    sx_, sy_ = px(plan.SIGNAL[0] - 12.0, plan.SIGNAL[1])
    draw.rectangle([sx_ - m(8), sy_ - m(5), sx_ + m(8), sy_ + m(5)], fill=STONE)
    a, b = px(*plan.BRIDGE_SOUTH), px(*plan.BRIDGE_NORTH)
    draw.line([a, b], fill=(200, 210, 230), width=max(2, int(m(4))))
    img = img.filter(ImageFilter.SMOOTH)
    out = ROOT / 'Art/UI/T_UI_MapHalcyon.png'
    img.save(out)
    print('wrote', out, img.size)


if __name__ == '__main__':
    main()
