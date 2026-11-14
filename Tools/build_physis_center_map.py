"""Render the Center of the Universe map for the pause menu: Art/UI/T_UI_MapCenter.png.

A stylised, cel-banded night map from the terrain height grid that Tools/build_physis_center.py writes
(Art/Meshes/Center/height.bin + height.json): hillshade, water below the water level, the mountain wall
darkened, roads as pale lines, regions tinted. North (+x) is at the TOP, east (+y) at the RIGHT.

Run with numpy (the Kokoro venv's packages, Python 3.14):
  PYTHONPATH=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages python3 Tools/build_physis_center_map.py [--size 1024]
Then import it alone with outfit_operation center:map_art (physis_center_tools.map_art); the HUD's PageMap
(Tools/blueprint_logic/center_overrides.py part map) must be rewritten after a re-import.

World -> map (E = EXTENT_CM, the half-width shown, in cm; x north, y east, both in cm):
  U = (y + E) / (2 E)          V = (E - x) / (2 E)          (0..1, origin top-left: HUD DrawTexture UVs)
  pixel = (U * size, V * size), texel (c, r) covers [c, c+1) x [r, r+1); its centre is ((c + .5) / size, (r + .5) / size).
"""
import argparse
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Art/Meshes/Center'
EXTENT_CM = 92000.0       # half-width shown: the walkable basin (to ~880-900 m) plus the foot of the mountain wall
WALL_START, WALL_SPAN = 820.0, 160.0   # build_physis_center.height(): m = clip((max(|x|,|y|) - 820) / 160, 0, 1)

# Display colours (sRGB, 0..1). Night palette in the HUD's ink / teal / gold family.
MEADOW = np.array((.120, .225, .190))
MEADOW_LOW = np.array((.075, .150, .150))
HEATH = np.array((.190, .140, .250))
LICHEN = np.array((.300, .350, .320))
MOSS = np.array((.300, .800, .700))
ROCK = np.array((.180, .190, .230))
MOUNTAIN = np.array((.060, .070, .110))
SHALLOW = np.array((.090, .300, .420))
DEEP = np.array((.025, .085, .190))
SHORE = np.array((.420, .950, .860))
ROAD = np.array((1.00, .860, .560))
ROAD_CASE = np.array((.030, .035, .050))
CONTOUR = np.array((.020, .030, .045))
GRID = np.array((.500, 1.00, .880))
REGION_TINT = {
    'Glade': (.150, .360, .300),       # the waking clearing, soft teal-green
    'Marsh': (.085, .165, .140),       # Lantern Marsh, dark olive (mostly water anyway)
    'Concourse': (.330, .300, .240),   # human ruins, pale stone
    'Choir': (.250, .170, .360),       # Choir Hollow, violet canyon
    'Thornveil': (.330, .140, .230),   # rose
    'Highlands': (.210, .250, .360),   # glassy, cold blue
    'Temple': (.450, .350, .170),      # the temple plateau, gold
}


def load():
    meta = json.loads((DATA / 'height.json').read_text())
    n = meta['n']
    # C order, as build_physis_center.terrain() wrote it from meshgrid(axis, axis, indexing='ij'):
    # h[i, j] is the height in metres at x = -half + i * cell (north), y = -half + j * cell (east).
    h = np.fromfile(DATA / 'height.bin', '<f4').reshape(n, n).astype(np.float64)
    return meta, h


def bilinear(grid, fi, fj):
    """Same interpolation as physis_center_tools.Ground.at (i along x, j along y)."""
    n = grid.shape[0]
    i = np.clip(np.floor(fi).astype(np.int64), 0, n - 2)
    j = np.clip(np.floor(fj).astype(np.int64), 0, n - 2)
    u, v = np.clip(fi - i, 0, 1), np.clip(fj - j, 0, 1)
    return (grid[i, j] * (1 - u) * (1 - v) + grid[i + 1, j] * u * (1 - v)
            + grid[i, j + 1] * (1 - u) * v + grid[i + 1, j + 1] * u * v)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def noise2(x, y, seed):
    """build_physis_center.noise2, verbatim: smooth value noise on a lattice."""
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    xf, yf = x - xi, y - yi
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)

    def h(a, b):
        n = (a * 374761393 + b * 668265263 + seed * 2147483647) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
    return (h(xi, yi) * (1 - u) * (1 - v) + h(xi + 1, yi) * u * (1 - v) + h(xi, yi + 1) * (1 - u) * v + h(xi + 1, yi + 1) * u * v) * 2 - 1


def fbm(x, y, seed, octaves=6, scale=1 / 260.0, gain=.5):
    """build_physis_center.fbm, verbatim (x, y in metres)."""
    total, amp, f = 0, 1, scale
    for i in range(octaves):
        total = total + amp * noise2(x * f, y * f, seed + i * 17)
        amp *= gain
        f *= 2.03
    return total


def blur(grid, radius):
    """Three box passes per axis (close to a Gaussian), edges clamped."""
    out = grid.copy()
    for _ in range(3):
        for axis in (0, 1):
            pad = np.pad(out, [(radius + 1, radius) if a == axis else (0, 0) for a in range(2)], mode='edge')
            c = np.cumsum(pad, axis=axis)
            hi = np.take(c, np.arange(2 * radius + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, np.arange(0, c.shape[axis] - 2 * radius - 1), axis=axis)
            out = (hi - lo) / (2 * radius + 1)
    return out


def cel(value, steps=4, soft=.12):
    """Bands like the level's cel post-process: floor plus a soft step at each band's middle."""
    q = value * steps
    return (np.floor(q) + smoothstep(.5 - soft, .5 + soft, q - np.floor(q))) / steps


def mix(colour, tint, amount):
    amount = np.clip(amount, 0, 1)[..., None]
    return colour * (1 - amount) + np.asarray(tint) * amount


def line(distance_px, half_width_px):
    """Anti-aliased coverage of a line whose centre is `distance_px` away."""
    return np.clip(half_width_px + .5 - distance_px, 0, 1)


def segment_distance(X, Y, polylines):
    best = np.full(X.shape, 1e9)
    for points in polylines:
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            dx, dy = bx - ax, by - ay
            t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
            best = np.minimum(best, np.hypot(X - ax - t * dx, Y - ay - t * dy))
    return best


def write_png(path, rgb):
    """Minimal 8-bit RGB PNG writer (zlib + struct, no PIL). rgb: uint8 array (rows top-down, cols, 3)."""
    height, width, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[r].tobytes() for r in range(height))   # filter type 0 on every row

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))   # 8-bit, colour type 2 (RGB)
           + chunk(b'sRGB', b'\x00')
           + chunk(b'IDAT', zlib.compress(raw, 9))
           + chunk(b'IEND', b''))
    Path(path).write_bytes(png)


def world_to_uv(x_cm, y_cm, extent_cm=EXTENT_CM):
    """World (cm) -> normalised map UV (origin top-left)."""
    return (y_cm + extent_cm) / (2 * extent_cm), (extent_cm - x_cm) / (2 * extent_cm)


def render(size, extent_cm=EXTENT_CM, grid_every_m=200.0):
    meta, h = load()
    half, cell, water = meta['half'], meta['cell'], meta['water']
    E = extent_cm / 100.0                       # metres
    px = 2 * E / size                           # metres per pixel
    t = (np.arange(size) + .5) / size           # texel centres
    X = np.repeat((E - t * 2 * E)[:, None], size, 1)     # rows: north (top) -> south
    Y = np.repeat((-E + t * 2 * E)[None, :], size, 0)    # cols: west (left) -> east
    fi, fj = (X + half) / cell, (Y + half) / cell
    H = bilinear(h, fi, fj)
    gx, gy = np.gradient(h, cell)               # dz/dx (north), dz/dy (east), metres per metre
    DX, DY = bilinear(gx, fi, fj), bilinear(gy, fi, fj)
    slope = np.hypot(DX, DY)
    sx, sy = np.gradient(blur(h, 2), cell)      # smoothed relief for the shading only
    SX, SY = bilinear(sx, fi, fj), bilinear(sy, fi, fj)

    # Hillshade: light from the north-west (upper left on the map), 1.6x relief so the gentle basin reads,
    # banded into three cel steps.
    exag, az, alt = 1.6, math.radians(-45), math.radians(40)
    light = np.array((math.cos(alt) * math.cos(az), math.cos(alt) * math.sin(az), math.sin(alt)))
    nx, ny = -SX * exag, -SY * exag
    lit = np.clip((nx * light[0] + ny * light[1] + light[2]) / np.sqrt(nx * nx + ny * ny + 1), 0, 1)
    shade = .34 + 1.0 * cel(lit, 3, .2)         # flat ground (lit = sin 40 deg = .64) lands near 1.0

    # Ground colour: meadow, violet heath on low rolling ground, rock on steep slopes, regions tinted.
    colour = mix(np.broadcast_to(MEADOW, H.shape + (3,)), MEADOW_LOW, smoothstep(6, 0, H - water))
    # Same patch masks as build_physis_center.terrain(): violet heath (seed 43), pale lichen (44), glow moss (42).
    heath = np.clip(fbm(X, Y, 43, 4, 1 / 70.0) * 2.5 - .6, 0, 1)
    lichen = np.clip(fbm(X, Y, 44, 4, 1 / 25.0) * 3 - 1.6, 0, 1)
    moss = np.clip(fbm(X, Y, 42, 4, 1 / 18.0) * 3 - .9, 0, 1)
    colour = mix(colour, HEATH, .55 * heath)
    colour = mix(colour, LICHEN, .25 * lichen)
    colour = mix(colour, MOSS, .12 * moss * smoothstep(.6, .3, slope))
    for name, (cx, cy, r, _floor, blend) in meta['regions'].items():
        if name in REGION_TINT:                 # a region added to the generator later stays untinted
            w = smoothstep(0, 1, 1 - (np.hypot(X - cx, Y - cy) - r) / blend)
            colour = mix(colour, REGION_TINT[name], .30 * w)
    colour = mix(colour, ROCK, smoothstep(.55, .95, slope))
    colour = colour * (1 + .10 * np.clip(H / 80.0, 0, 1))[..., None]     # a little lighter with height

    # The mountain wall: dark, with its own relief left visible.
    edge = np.maximum(np.abs(X), np.abs(Y))
    wall = np.clip((edge - WALL_START) / WALL_SPAN, 0, 1)
    colour = mix(colour, MOUNTAIN, smoothstep(0, .55, wall) * .85)
    colour = colour * shade[..., None]

    # Water: shallow to deep by depth, flat (no hillshade), then a bright shoreline of constant pixel width.
    depth = water - H
    wet = smoothstep(-.02, .02, depth)
    water_col = mix(np.broadcast_to(SHALLOW, H.shape + (3,)), DEEP, smoothstep(.2, 4.0, depth))
    colour = mix(colour, water_col, wet)
    gradient_px = slope * px + 1e-4             # metres of height per pixel
    colour = mix(colour, SHORE, .85 * line(np.abs(H - water) / gradient_px, .6))

    # Contours every 10 m (stronger every 50 m), on land only, faded on the mountain wall.
    for step, strength, width in ((10.0, .22, .45), (50.0, .38, .6)):
        dz = np.abs(H - step * np.round(H / step))
        colour = mix(colour, CONTOUR, strength * line(dz / gradient_px, width) * (1 - wet) * (1 - .7 * wall))

    # Navigation grid (faint teal), every grid_every_m metres through the origin.
    if grid_every_m:
        gdx = np.abs(X - grid_every_m * np.round(X / grid_every_m)) / px
        gdy = np.abs(Y - grid_every_m * np.round(Y / grid_every_m)) / px
        colour = mix(colour, GRID, .07 * np.maximum(line(gdx, .5), line(gdy, .5)))

    # Roads: dark casing, then a pale gold core (widths in pixels, scaled for the 1024 look).
    s = size / 1024.0
    road = segment_distance(X, Y, meta['paths']) / px
    colour = mix(colour, ROAD_CASE, .75 * line(road, 3.2 * s))
    colour = mix(colour, ROAD, .95 * line(road, 1.5 * s))

    # Soft vignette so the square sits in the dark menu panel.
    fade = (1 - .35 * smoothstep(.92, 1.0, np.abs(X) / E)) * (1 - .35 * smoothstep(.92, 1.0, np.abs(Y) / E))
    colour = colour * fade[..., None]
    return (np.clip(colour, 0, 1) * 255 + .5).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, default=1024)
    parser.add_argument('--extent', type=float, default=EXTENT_CM, help='half-width shown, cm')
    parser.add_argument('--out', default=str(ROOT / 'Art/UI/T_UI_MapCenter.png'))
    # Also runs under Blender's Python (`blender -b --python THIS -- --size 1024`): only parse after '--'.
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    rgb = render(args.size, args.extent)
    write_png(args.out, rgb)
    print('map', args.out, rgb.shape, 'extent_cm', args.extent, 'm/px', round(2 * args.extent / 100 / args.size, 3))


if __name__ == '__main__':
    main()
