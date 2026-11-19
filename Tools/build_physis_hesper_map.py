"""Render Hesper's map for the pause menu: Art/UI/T_UI_MapHesper.png.

The plateau from straight above in its own colours: warm dust, red-brown rock where it is steep, the drop beyond the
western edge as dark haze, the Reed Terraces' pools, the roads, every house (from scatter.json), and the set pieces as
plain shapes: the Choir Wall as an amber band, the Galleries' ring, the Spire's rock, the Nave, the Concord's court.
No text: the HUD writes the names.

Same frame as every level's map (physis_hesper_plan.MAP_HALF, north up, east right).
Run after Tools/build_physis_hesper.py:  python3 Tools/build_physis_hesper_map.py [--size 1024]   then hesper:map_art.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Art/Meshes/Hesper'
sys.path.insert(0, str(ROOT / 'Content/Python'))
import physis_hesper_plan as plan  # noqa: E402

E = plan.MAP_HALF
SUN = (.10, -.75, .65)          # from the west, low
DUST, ROCK, HAZE, SURROUND = np.array((176, 146, 112), float), np.array((120, 64, 50), float), np.array((70, 42, 46), float), (22, 14, 16)
POOL = (64, 52, 40)
ROAD, TRAIL, STONE, ROOF, AMBER, BLUE = (226, 206, 176), (196, 172, 140), (236, 222, 200), (92, 60, 40), (255, 170, 60), (180, 220, 255)


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
    slope = np.clip(np.hypot(sx, sy) / .8, 0, 1)[..., None]
    rgb = (DUST * (1 - slope) + ROCK * slope) * (.5 + .6 * shade)[..., None]
    low = np.clip(-(h - 5.0) / 60.0, 0, 1)[..., None]
    rgb = rgb * (1 - low) + HAZE * low
    rgb = np.where(inside[..., None], rgb, np.array(SURROUND, float))
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)

    def px(mx, my):
        return ((my + E) / (2 * E) * size, (E - mx) / (2 * E) * size)

    def m(v):
        return v / (2 * E) * size

    for px_, py_, hx_, hy_, _, yaw in plan.POOLS:
        a = math.radians(yaw)
        corners = [px(px_ + dx * hx_ * math.cos(a) - dy * hy_ * math.sin(a), py_ + dx * hx_ * math.sin(a) + dy * hy_ * math.cos(a))
                   for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        draw.polygon(corners, fill=POOL)
    for name, kind, half, points in plan.PATHS:
        draw.line([px(a, b) for a, b in points], fill=ROAD if kind == 'road' else TRAIL, width=max(2, int(m(half * 2))))
    scatter = json.loads((DATA / 'scatter.json').read_text())
    for key, rows in scatter.items():
        if key.startswith('SM_AN_House'):
            for r in rows:
                cx, cy = px(r[0] / 100, r[1] / 100)
                s = m(3.6)
                draw.rectangle([cx - s, cy - s, cx + s, cy + s], fill=ROOF)
    # the Choir Wall, the House, the Tuning Court, the Galleries' ring, the Spire's rock, the Nave, the court
    draw.line([px(xx, yy) for xx, yy, _ in plan.wall_panels()], fill=AMBER, width=max(3, int(m(plan.WALL_THICK))))
    hx_, hy_ = px(plan.HOUSE[0] - 16.0, plan.HOUSE[1])
    draw.rectangle([hx_ - m(7), hy_ - m(11), hx_ + m(7), hy_ + m(11)], fill=STONE)
    for (lx, ly), rad, colour in ((plan.TUNING, 3.0, AMBER), (plan.LOW_BELL, 3.0, AMBER), (plan.MID_BELL, 3.0, AMBER), (plan.HIGH_BELL, 3.0, AMBER),
                                   (plan.SPIRE, 5.0, STONE), (plan.HORN, 13.0, (190, 140, 80))):
        qx, qy = px(lx, ly)
        draw.ellipse([qx - m(rad), qy - m(rad), qx + m(rad), qy + m(rad)], fill=colour)
    gx_, gy_ = px(*plan.MID_BELL)
    draw.ellipse([gx_ - m(26), gy_ - m(26), gx_ + m(26), gy_ + m(26)], outline=STONE, width=max(2, int(m(2.5))))
    rx_, ry_ = px(*plan.SPIRE_ROCK[:2])
    rr = m(plan.SPIRE_ROCK[2])
    draw.ellipse([rx_ - rr, ry_ - rr, rx_ + rr, ry_ + rr], outline=(150, 90, 70), width=max(2, int(m(3))))
    for side in (-1, 1):
        draw.line([px(plan.NAVE_SOUTH, side * 11.5), px(plan.CHOIR_GATE[0], side * 11.5)], fill=STONE, width=max(2, int(m(1.6))))
    cx, cy = px(*plan.CONCORD)
    rc = m(plan.COURT_WALL)
    draw.ellipse([cx - rc, cy - rc, cx + rc, cy + rc], outline=STONE, width=max(2, int(m(2.5))))
    qx, qy = px(*plan.STAIR)
    draw.ellipse([qx - m(5), qy - m(5), qx + m(5), qy + m(5)], fill=BLUE)
    img = img.filter(ImageFilter.SMOOTH)
    out = ROOT / 'Art/UI/T_UI_MapHesper.png'
    img.save(out)
    print('wrote', out, img.size)


if __name__ == '__main__':
    main()
