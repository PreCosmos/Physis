"""Procedural space backdrop, explosion flipbooks, FX sprites and opening soundtrack.

Run: flatpak run org.blender.Blender -b --python Tools/build_physis_fx.py -- [stages] [preview]
Stages: sky planet fire smoke sprites audio review ad. No stage means all of them.
`noresim` reuses the stored fluid solve in Saved/FXPreview/sim when reshading fire or smoke.
`preview` renders at reduced resolution into the scratch folder Saved/FXPreview.

Everything is numpy. Noise is evaluated in 3D on the unit sphere, so the panorama has no
seam and no pole pinch. Workers are plain forks that write into shared memory.
"""
import math
import mmap
import os
import shutil
import struct
import sys
import time
import traceback
import wave
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PREVIEW = 'preview' in ARGS
STAGES = [a for a in ARGS if a not in ('preview', 'noresim')] or ['sky', 'planet', 'fire', 'smoke', 'sprites', 'audio', 'review', 'ad']
OUT = ROOT / 'Saved/FXPreview' if PREVIEW else ROOT / 'Art'
SKY = OUT / 'Sky'
FX = OUT / 'FX'
AUDIO = ROOT / 'Art/Audio'
REVIEW = ROOT / 'Art/Review'
WORKERS = 18
F = np.float32


# ---------------------------------------------------------------- plumbing

def shared(shape, dtype=F):
    size = int(np.prod(shape)) * np.dtype(dtype).itemsize
    return np.frombuffer(mmap.mmap(-1, size), dtype).reshape(shape)


def parallel(work, items, workers=WORKERS):
    # Fork-based map. Results travel through shared() arrays, so nothing is pickled.
    items, children = list(items), []
    for index in range(workers):
        pid = os.fork()
        if pid == 0:
            code = 0
            try:
                for item in items[index::workers]:
                    work(item)
            except BaseException:
                traceback.print_exc()
                code = 1
            os._exit(code)
        children.append(pid)
    for pid in children:
        if os.waitpid(pid, 0)[1] != 0:
            raise RuntimeError('worker failed')


def png(path, data, quant=16):
    """Write a true 16-bit PNG. `quant` keeps that many significant bits so it compresses."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.clip(data, 0, 1)
    if data.ndim == 2:
        data = data[..., None]
    h, w, channels = data.shape
    steps = 2 ** quant - 1
    # Bit replication maps the top value exactly onto 65535.
    words = (np.round(data * steps).astype(np.uint32) * 65535 // steps).astype('>u2')
    raw = words.view(np.uint8).reshape(h, w * channels * 2)
    bpp = channels * 2
    filtered = raw.copy()
    filtered[:, bpp:] = raw[:, bpp:] - raw[:, :-bpp]
    rows = np.concatenate((np.ones((h, 1), np.uint8), filtered), 1)
    del filtered, raw, words
    per = 64
    bands = [(i, rows[i:i + per].tobytes()) for i in range(0, h, per)]

    def squeeze(band):
        start, chunk = band
        packer = zlib.compressobj(6, zlib.DEFLATED, -15)
        end = zlib.Z_FINISH if start + per >= h else zlib.Z_SYNC_FLUSH
        return packer.compress(chunk) + packer.flush(end)

    with ThreadPoolExecutor(WORKERS) as pool:
        packed = list(pool.map(squeeze, bands))
    check = 1
    for _, chunk in bands:
        check = zlib.adler32(chunk, check)
    body = b'\x78\x9c' + b''.join(packed) + struct.pack('>I', check)

    def tag(name, payload):
        return struct.pack('>I', len(payload)) + name + payload + struct.pack('>I', zlib.crc32(name + payload))

    kind = {1: 0, 3: 2, 4: 6}[channels]
    with open(path, 'wb') as out:
        out.write(b'\x89PNG\r\n\x1a\n')
        out.write(tag(b'IHDR', struct.pack('>IIBBBBB', w, h, 16, kind, 0, 0, 0)))
        out.write(tag(b'IDAT', body))
        out.write(tag(b'IEND', b''))
    print(f'  wrote {path.name} {w}x{h}x{channels} {path.stat().st_size / 1e6:.1f} MB', flush=True)


def load(path):
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = 'Non-Color'
    w, h = image.size
    pixels = np.empty(w * h * 4, F)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    return pixels.reshape(h, w, 4)[::-1]


def exr(path, data):
    h, w = data.shape[:2]
    image = bpy.data.images.new(Path(path).stem, w, h, alpha=False, float_buffer=True)
    image.colorspace_settings.name = 'Linear Rec.709'
    rgba = np.ones((h, w, 4), F)
    rgba[..., :3] = data
    image.pixels.foreach_set(rgba[::-1].ravel())
    settings = bpy.context.scene.render.image_settings
    settings.file_format = 'OPEN_EXR'
    settings.color_depth = '16'
    settings.color_mode = 'RGB'
    settings.exr_codec = 'ZIP'
    image.save_render(str(path), scene=bpy.context.scene)
    bpy.data.images.remove(image)
    print(f'  wrote {Path(path).name} {Path(path).stat().st_size / 1e6:.1f} MB', flush=True)


def area(image, height, width):
    # Exact box resample by cumulative sum, for any non-integer ratio.
    for axis, target in ((0, height), (1, width)):
        size = image.shape[axis]
        if size == target:
            continue
        total = np.concatenate((np.zeros_like(np.take(image, [0], axis)), np.cumsum(image.astype(np.float64), axis)), axis)
        edges = np.linspace(0, size, target + 1)
        low = np.floor(edges).astype(int).clip(0, size - 1)
        frac = (edges - low).reshape([-1 if a == axis else 1 for a in range(image.ndim)])
        at = np.take(total, low, axis) + np.take(np.diff(total, axis=axis), low, axis) * frac
        image = (np.diff(at, axis=axis) * (target / size)).astype(F)
    return image


def smooth(low, high, value):
    x = np.clip((value - low) / (high - low), 0, 1)
    return x * x * (3 - 2 * x)


def srgb(x):
    x = np.clip(x, 0, None)
    return np.where(x <= .0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - .055)


def linear(x):
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)


def planck(kelvin):
    """Blackbody colour at sRGB-like wavelengths, normalised to its brightest channel."""
    kelvin = np.asarray(kelvin, np.float64)[..., None]
    lam = np.array((612e-9, 549e-9, 464e-9))
    power = lam ** -5 / (np.exp(np.minimum(1.4388e-2 / (lam * kelvin), 500)) - 1)
    return (power / power.max(-1, keepdims=True)).astype(F)


# ---------------------------------------------------------------- 3D noise

N = 256
MASK = N - 1


def make_volume(seed=4):
    # Broad-band Gaussian noise, periodic on all axes. A narrow band reads as worms and
    # marble, so each lookup carries about two octaves of 1/k energy of its own.
    rng = np.random.default_rng(seed)
    spectrum = np.fft.rfftn(rng.standard_normal((N, N, N), F))
    axis = np.fft.fftfreq(N, 1 / N).astype(F)
    half = np.fft.rfftfreq(N, 1 / N).astype(F)
    k = np.sqrt(axis[:, None, None] ** 2 + axis[None, :, None] ** 2 + half[None, None, :] ** 2)
    spectrum *= smooth(2, 4, k) * smooth(36, 24, k) / np.maximum(k, 1)
    volume = np.fft.irfftn(spectrum, (N, N, N)).astype(F)
    return (volume / volume.std()).ravel()


VOLUME = None
ROTATE = None


def rotations(count=24, seed=7):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(count):
        q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
        out.append((q.astype(F), rng.uniform(0, N, 3).astype(F)))
    return out


def tri(x, y, z):
    ix, iy, iz = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    ix, iy, iz = ix.astype(np.int32) & MASK, iy.astype(np.int32) & MASK, iz.astype(np.int32) & MASK
    jx, jy, jz = (ix + 1) & MASK, (iy + 1) & MASK, (iz + 1) & MASK
    v = VOLUME
    c00 = v[(ix << 16) | (iy << 8) | iz] * (1 - fz) + v[(ix << 16) | (iy << 8) | jz] * fz
    c01 = v[(ix << 16) | (jy << 8) | iz] * (1 - fz) + v[(ix << 16) | (jy << 8) | jz] * fz
    c10 = v[(jx << 16) | (iy << 8) | iz] * (1 - fz) + v[(jx << 16) | (iy << 8) | jz] * fz
    c11 = v[(jx << 16) | (jy << 8) | iz] * (1 - fz) + v[(jx << 16) | (jy << 8) | jz] * fz
    return (c00 * (1 - fy) + c01 * fy) * (1 - fx) + (c10 * (1 - fy) + c11 * fy) * fx


def fbm(x, y, z, cycles, octaves, seed=0, gain=.5, mode='n', lacunarity=2.03):
    """cycles = features per unit length. mode: n signed, ridge 0..1, billow 0..~1."""
    total = np.zeros_like(x)
    amp, norm = 1., 0.
    scale = cycles * 9.
    for octave in range(octaves):
        r, off = ROTATE[(seed * 5 + octave) % len(ROTATE)]
        n = tri((r[0, 0] * x + r[0, 1] * y + r[0, 2] * z) * scale + off[0],
                (r[1, 0] * x + r[1, 1] * y + r[1, 2] * z) * scale + off[1],
                (r[2, 0] * x + r[2, 1] * y + r[2, 2] * z) * scale + off[2])
        if mode == 'ridge':
            n = (1 - np.minimum(np.abs(n), 1.6) / 1.6) ** 2
        elif mode == 'billow':
            n = np.minimum(np.sqrt(n * n + .07), 2.2) / 1.3
        total += n * amp
        norm += amp * (1 if mode != 'n' else amp)
        amp *= gain
        scale *= lacunarity
    return (total / norm if mode != 'n' else total / math.sqrt(norm)).astype(F)


def init_noise():
    global VOLUME, ROTATE
    if VOLUME is None:
        begin = time.time()
        VOLUME = make_volume()
        ROTATE = rotations()
        print(f'noise volume {time.time() - begin:.1f}s', flush=True)


# ---------------------------------------------------------------- sky

def direction(u, v):
    longitude, latitude = 2 * math.pi * (u - .5), math.pi * (.5 - v)
    return (np.array((math.cos(latitude) * math.cos(longitude), math.cos(latitude) * math.sin(longitude),
                      math.sin(latitude)), F))


CORE = direction(.25, .44)
_tilt = np.array((.42, 0, 1), F)
NORTH = _tilt - CORE * (_tilt @ CORE)
NORTH /= np.linalg.norm(NORTH)
EAST = np.cross(NORTH, CORE)

# Each entry: u, v, radius (rad), main colour, filament colour, heart colour, brightness.
NEBULAE = (
    (.640, .36, .78, (.070, .210, .330), (.150, .300, .520), (.520, .230, .430), .42),   # hero: cold First Ones blue
    (.545, .58, .40, (.300, .070, .170), (.520, .160, .200), (.620, .380, .240), .62),   # its rose companion
    (.160, .60, .46, (.340, .090, .120), (.540, .230, .120), (.640, .470, .260), .60),   # ember cloud near the core
    (.905, .30, .62, (.110, .070, .270), (.210, .170, .470), (.150, .320, .460), .95),   # far violet veil
    (.390, .19, .36, (.050, .140, .250), (.140, .310, .430), (.400, .270, .380), .55),
    (.800, .74, .44, (.060, .170, .210), (.130, .360, .330), (.320, .250, .410), .50),
)


def octaves_for(cycles, width):
    # Stop once the finest wavelength would drop below about three pixels.
    smallest = 3 * 2 * math.pi / width
    return max(1, int(math.log(1 / (smallest * cycles), 2.03)) + 1)


def sky_band(arg):
    row0, row1, width, height, light, depth = arg
    v = ((np.arange(row0, row1) + .5) / height).astype(F)[:, None]
    u = ((np.arange(width) + .5) / width).astype(F)[None, :]
    longitude, latitude = 2 * math.pi * (u - .5), math.pi * (.5 - v)
    x, y, z = np.cos(latitude) * np.cos(longitude), np.cos(latitude) * np.sin(longitude), np.sin(latitude) * np.ones_like(u)
    gx, gy, gz = (x * CORE[0] + y * CORE[1] + z * CORE[2], x * EAST[0] + y * EAST[1] + z * EAST[2],
                  x * NORTH[0] + y * NORTH[1] + z * NORTH[2])
    l, b = np.arctan2(gy, gx), np.arcsin(np.clip(gz, -1, 1))
    # Domain warps: everything organic is bent by these.
    wa = fbm(x, y, z, 1.25, 5, 1)
    wb = fbm(x, y, z, 1.25, 5, 2)
    wc = fbm(x, y, z, 1.25, 5, 3)
    xw, yw, zw = x + .13 * wa, y + .13 * wb, z + .13 * wc
    # Unresolved starlight of the disc, broken into clouds.
    clouds = fbm(xw, yw, zw, 3.2, octaves_for(3.2, width), 4, .56)
    fine = fbm(x, y, z, 48, octaves_for(48, width), 5, .6)
    scale = .095 + .032 * wb
    disc = np.exp(-np.abs(b) / np.clip(scale, .04, 1))
    along = .24 + .76 * np.exp(-(np.abs(l) / 1.55) ** 1.25)
    swell = (l / .36) ** 2 + (b / .19) ** 2
    bulge = np.exp(-1.75 * swell ** .60)
    heart = np.exp(-((l / .062) ** 2 + (b / .038) ** 2))
    pin = np.exp(-((l / .014) ** 2 + (b / .010) ** 2))
    glow = disc * along * (.24 + .76 * np.clip(.50 + .40 * clouds, 0, 1.6)) ** 3 * (.84 + .26 * fine)
    warm = np.clip(bulge * 1.5, 0, 1)[..., None]
    tint = np.array((.52, .66, 1.0), F) * (1 - warm) + np.array((1.0, .76, .50), F) * warm
    colour = glow[..., None] * tint * .15
    # Log-normal star clouds: bright knots over a dim floor, never an even wash.
    starclouds = np.exp(1.25 * clouds - .75) * (.84 + .26 * fine)
    colour += (bulge * starclouds)[..., None] * np.array((1.0, .80, .60), F) * .34
    # Rosy star-forming knots and blue young arms string along the band.
    arms = disc * along * smooth(.2, 1.6, fbm(xw, yw, zw, 2.1, 5, 44))
    colour += (arms * (1 - bulge))[..., None] * np.array((.30, .46, .80), F) * .050
    hii = disc * smooth(.75, 2.3, fbm(xw, yw, zw, 7, octaves_for(7, width), 45, .58))
    colour += hii[..., None] * np.array((.95, .22, .34), F) * .13
    colour += heart[..., None] * np.array((1.0, .80, .52), F) * 1.6
    colour += pin[..., None] * np.array((1.0, .93, .78), F) * 4.0
    # Dust: warped ridges hugging the plane plus one long central rift.
    xd, yd, zd = xw + .05 * wc, yw + .05 * wa, zw + .05 * wb
    ridges = fbm(xd, yd, zd, 5.0, octaves_for(5.0, width), 6, .62, 'ridge')
    knots = fbm(xw, yw, zw, 10, octaves_for(10, width), 7, .62)
    thick = np.exp(-(b / np.clip(.078 + .040 * wa, .03, 1)) ** 2) * (.38 + .62 * along)
    tau = thick * smooth(.20, .50, ridges) * 3.6 * (1 + .55 * np.clip(knots, -1.5, 2))
    offset = .022 * np.sin(l * 2.7 + .4) + .017 * wb
    rift = np.exp(-((b - offset) / (.020 + .012 * np.abs(wc))) ** 2) * smooth(.05, .55, along)
    tau += rift * (2.2 + 1.3 * smooth(-1, 1, clouds)) * smooth(.12, .42, ridges + .10 * knots)
    cirrus = fbm(xw * 1.3, yw * 1.3, zw * 1.3, 3.1, octaves_for(3.1, width), 8, .55, 'ridge')
    tau += .30 * smooth(.28, .62, cirrus) * smooth(.3, 1.1, wc + .35) * (1 - thick)
    tau = np.clip(tau, 0, None)
    # Nebulae live behind most of the dust, and have dark globules of their own.
    gas = np.zeros_like(colour)
    local = np.zeros_like(tau)
    pos = np.stack((x, y, z), -1)
    for index, (nu, nv, radius, main, thread, inner, level) in enumerate(NEBULAE):
        centre = direction(nu, nv)
        cosine = pos @ centre
        keep = cosine > math.cos(min(radius * 2.2, 3.0))
        if not keep.any():
            continue
        px, py, pz = x[keep], y[keep], z[keep]
        angle = np.arccos(np.clip(cosine[keep], -1, 1))
        seed = 11 + index * 3
        scale = 1 / radius
        wx = fbm(px, py, pz, .9 * scale, 4, seed)
        wy = fbm(px, py, pz, .9 * scale, 4, seed + 1)
        wz = fbm(px, py, pz, .9 * scale, 4, seed + 2)
        reach = radius * .13
        qx, qy, qz = px + wx * reach, py + wy * reach, pz + wz * reach
        edge = angle + radius * .24 * fbm(px, py, pz, .6 * scale, 3, seed + 3)
        veil = smooth(radius * 1.35, 0, edge) ** 1.5
        # Gas density is log-normal: dim wide clouds with few bright knots, as in real plates.
        puff = fbm(qx, qy, qz, 1.5 * scale, octaves_for(1.5 * scale, width), seed + 4, .60)
        knot = fbm(qx, qy, qz, 3.4 * scale, octaves_for(3.4 * scale, width), seed + 5, .62)
        tone = smooth(-1.0, 1.0, fbm(px, py, pz, .9 * scale, 4, seed + 7))[..., None]
        mass = veil * np.exp(.95 * puff + .30 * knot - .9)
        hot = (veil ** 2 * np.exp(1.5 * knot + .9 * puff - 2.2))[..., None]
        centre_glow = smooth(radius * .8, 0, edge) ** 3 * np.exp(.5 * puff - .3)
        body = np.array(main, F) * (1 - tone) + np.array(thread, F) * tone
        here = (mass[..., None] * body * 1.05 + hot * np.array(thread, F) * .50
                + centre_glow[..., None] * np.array(inner, F) * .45) * level
        patch = np.zeros((*keep.shape, 3), F)
        patch[keep] = here
        gas += patch
        lanes = fbm(qx, qy, qz, 1.9 * scale, octaves_for(1.9 * scale, width), seed + 6, .60)
        dark = np.zeros_like(tau)
        dark[keep] = veil * smooth(.15, 1.5, lanes) ** 1.3 * 2.2
        local += dark
    scatter = (1 - np.exp(-tau))[..., None] * ((disc * along + bulge)[..., None]) * np.array((.0070, .0042, .0030), F)
    extinct = np.array((.76, 1.0, 1.36), F)
    colour = colour * np.exp(-tau[..., None] * extinct) + scatter
    colour += gas * np.exp(-(local + .55 * tau)[..., None] * extinct)
    # Space is never pure black in a long exposure: a faint indigo and teal wash.
    wash = fbm(xw, yw, zw, .8, 4, 40)
    tide = fbm(x, y, z, .6, 3, 41)
    colour += np.array((.0016, .0021, .0046), F) * (1 + .5 * np.clip(wash, -1.5, 2))[..., None]
    colour += smooth(.2, 1.8, wash)[..., None] * np.array((.0007, .0034, .0056), F)
    colour += smooth(.2, 1.7, tide)[..., None] * np.array((.0046, .0014, .0060), F)
    light[row0:row1] = colour
    depth[row0:row1] = tau + local


def stretch_class(s):
    return np.searchsorted(np.array((1.2, 1.6, 2.2, 3, 4.5, 6, 9, 13, 20, 40)), s)


def splat(image, xs, ys, flux, colour, sigma, radius, s, halo):
    """Add stars whose footprint is widened in x by s, the equirectangular stretch."""
    h, w = image.shape[:2]
    rx, ry = int(math.ceil(radius * s)), radius
    ox = np.arange(-rx, rx + 1)[None, None, :]
    oy = np.arange(-ry, ry + 1)[None, :, None]
    for start in range(0, len(xs), 120000):
        end = start + 120000
        cx, cy = xs[start:end], ys[start:end]
        ix, iy = np.floor(cx).astype(np.int32), np.floor(cy).astype(np.int32)
        fx, fy = (cx - ix)[:, None, None], (cy - iy)[:, None, None]
        sg = sigma[start:end, None, None]
        r2 = ((ox - fx) / s) ** 2 + (oy - fy) ** 2
        shape = np.exp(-r2 / (2 * sg * sg)) + halo / (1 + r2 / (6 * sg * sg)) ** 2.4
        shape *= flux[start:end, None, None]
        px = np.broadcast_to(np.mod(ix[:, None, None] + ox, w), shape.shape).ravel()
        py = np.broadcast_to(np.clip(iy[:, None, None] + oy, 0, h - 1), shape.shape).ravel()
        shape = shape.ravel().astype(F)
        for channel in range(3):
            np.add.at(image[..., channel], (py, px), shape * np.repeat(colour[start:end, channel], ox.size * oy.size))


def stars(width, height, depth):
    rng = np.random.default_rng(2312)
    count = int(2.8e6 * (width / 8192) ** 2)
    uz = rng.uniform(-1, 1, count * 3).astype(F)
    phi = rng.uniform(0, 2 * math.pi, count * 3).astype(F)
    xy = np.sqrt(1 - uz * uz)
    x, y, z = xy * np.cos(phi), xy * np.sin(phi), uz
    b = np.arcsin(np.clip(x * NORTH[0] + y * NORTH[1] + z * NORTH[2], -1, 1))
    l = np.arctan2(x * EAST[0] + y * EAST[1] + z * EAST[2], x * CORE[0] + y * CORE[1] + z * CORE[2])
    density = .16 + .60 * np.exp(-np.abs(b) / .16) * (.35 + .65 * np.exp(-np.abs(l) / 1.4))
    # Stars gather in clouds and voids. Uniform scatter is what reads as TV static.
    gather = np.empty_like(x)
    for start in range(0, len(x), 1 << 20):
        i, j = start, start + (1 << 20)
        gather[i:j] = (.82 * fbm(x[i:j], y[i:j], z[i:j], 2.6, 4, 46, .55) + .42 * fbm(x[i:j], y[i:j], z[i:j], 11, 3, 47, .55))
    density = density * np.exp(gather - .35)
    keep = rng.uniform(0, 1, count * 3) < density
    u, latitude = (phi[keep] / (2 * math.pi) + .5) % 1, np.arcsin(z[keep])
    u, latitude = u[:count], latitude[:count]
    count = len(u)
    flux = (rng.uniform(1e-6, 1, count) ** (-1 / 1.35)).astype(F) * .0065
    flux = np.minimum(flux, 90)
    kelvin = np.exp(rng.normal(math.log(6400), .52, count)).clip(2500, 32000)
    # The brightest are hot blue giants or swollen red ones.
    bright = flux > 3
    kelvin[bright] = np.where(rng.uniform(0, 1, bright.sum()) < .3, rng.uniform(3000, 4200, bright.sum()),
                              rng.uniform(7500, 26000, bright.sum()))
    colour = planck(kelvin)
    grey = colour.mean(1, keepdims=True)
    colour = np.clip(grey + (colour - grey) * 1.25, .02, None)
    colour /= colour.max(1, keepdims=True)
    px, py = u * width, (.5 - latitude / math.pi) * height
    tau = depth[np.clip(py.astype(int), 0, height - 1), np.clip(px.astype(int), 0, width - 1)]
    # Depth along the line of sight: foreground stars sit in front of the dust.
    front = rng.uniform(0, 1, count) ** 1.5
    front[rng.uniform(0, 1, count) < .10] = 0
    flux = flux * np.exp(-tau * front * 1.5).astype(F)
    colour[:, 2] *= np.exp(-tau * front * .35).astype(F)
    colour[:, 1] *= np.exp(-tau * front * .15).astype(F)
    sigma = (.60 + .13 * np.log10(np.maximum(flux, .01) / .022)).astype(F).clip(.56, 1.5)
    strain = 1 / np.maximum(np.cos(latitude), .022)
    image = shared((height, width, 3))
    classes = stretch_class(strain)
    values = (1, 1.4, 1.9, 2.6, 3.8, 5.2, 7.5, 11, 16, 30, 45)
    tiers = ((flux < .8, 2, 0.), ((flux >= .8) & (flux < 12), 5, .012))

    def tier(job):
        cls, mask, radius, halo = job
        pick = np.nonzero(mask & (classes == cls))[0]
        if len(pick):
            splat_shared(image, px[pick], py[pick], flux[pick], colour[pick], sigma[pick], radius, values[cls], halo)

    jobs = [(cls, mask, radius, halo) for mask, radius, halo in tiers for cls in range(len(values))]
    for job in jobs:
        tier(job)
    # Hero stars get a real optical response: wide halo, and spikes on the very top few.
    order = np.nonzero(flux >= 12)[0]
    order = order[np.argsort(-flux[order])]
    for rank, index in enumerate(order):
        s = float(min(strain[index], 40))
        radius = int(min(9 + 7 * math.log2(flux[index] / 12 + 1), 44))
        splat(image, px[[index]], py[[index]], flux[[index]], colour[[index]], sigma[[index]], radius, s, .035)
        if rank < 10 and s < 1.5:
            reach = int(18 + flux[index] * .35)
            for ax, ay in ((.82, .57), (-.57, .82)):
                t = np.arange(-reach, reach + 1)
                sx = np.mod((px[index] + t * ax * s).astype(int), width)
                sy = np.clip((py[index] + t * ay).astype(int), 0, height - 1)
                fade = flux[index] * .022 * np.exp(-np.abs(t) / (reach * .26)) * (1 + .4 * np.cos(t * .9))
                np.add.at(image, (sy, sx), (fade[:, None] * colour[index]).astype(F))
    print(f'  {count} stars, {len(order)} heroes', flush=True)
    # Far galaxies: small, soft, warm smudges away from the plane.
    for _ in range(int(150 * (width / 8192))):
        pu, pv = rng.uniform(0, 1), rng.uniform(.1, .9)
        d = direction(pu, pv)
        if abs(d @ NORTH) < .3:
            continue
        size = rng.uniform(1.6, 7) * width / 8192
        turn, flat = rng.uniform(0, math.pi), rng.uniform(.25, .9)
        r = int(size * 4) + 2
        strain_here = 1 / max(math.cos(math.pi * (.5 - pv)), .1)
        oy, ox = np.mgrid[-r:r + 1, -int(r * strain_here):int(r * strain_here) + 1]
        ex, ey = ox / strain_here, oy
        a = (ex * math.cos(turn) + ey * math.sin(turn)) / size
        c = (ey * math.cos(turn) - ex * math.sin(turn)) / (size * flat)
        shape = np.exp(-2.1 * (a * a + c * c) ** .42) * rng.uniform(.03, .14)
        image[np.clip(int(pv * height) + oy, 0, height - 1), np.mod(int(pu * width) + ox, width)] += (
            shape[..., None] * planck(rng.uniform(3800, 7500))).astype(F)
    return image


def splat_shared(image, xs, ys, flux, colour, sigma, radius, s, halo):
    # Row-striped so workers never write the same pixel: each stripe adds only its own rows.
    h = image.shape[0]
    stripes = WORKERS * 3
    band = (ys / h * stripes).astype(np.int32).clip(0, stripes - 1)

    def work(job):
        odd, stripe = job
        pick = band == stripe
        if pick.any():
            splat(image, xs[pick], ys[pick], flux[pick], colour[pick], sigma[pick], radius, s, halo)

    # Even stripes first, then odd, so footprints spilling a row never collide.
    parallel(work, [(0, i) for i in range(0, stripes, 2)])
    parallel(work, [(1, i) for i in range(1, stripes, 2)])


def film(light, exposure):
    # Filmic toe and soft shoulder, with hue kept as a highlight desaturates.
    x = np.clip(light, 0, None) * exposure
    peak = x.max(-1, keepdims=True)
    mapped = 1 - np.exp(-peak)
    ratio = x / np.maximum(peak, 1e-7)
    white = smooth(.7, 3.0, peak)
    return np.clip(mapped * (ratio * (1 - white) + white), 0, 1)


def build_sky():
    width, height = (2048, 1024) if PREVIEW else (8192, 4096)
    init_noise()
    begin = time.time()
    light, depth = shared((height, width, 3)), shared((height, width))
    bands = [(j, min(j + 32, height), width, height, light, depth) for j in range(0, height, 32)]
    parallel(sky_band, bands)
    print(f'sky fields {time.time() - begin:.0f}s', flush=True)
    point = stars(width, height, depth)
    print(f'sky stars {time.time() - begin:.0f}s', flush=True)
    exposure = 1.0
    total = light + point
    display = film(total, exposure)
    # HDR keeps star peaks above 1 for bloom; the display curve holds everything else.
    excess = np.clip(point * exposure - 1.2, 0, 14)
    exr(SKY / 'T_Sky_Space_8K.exr', display + excess)
    rng = np.random.default_rng(1)
    encoded = srgb(display)
    # Dither about one 8-bit step, so a later BC7 or 8-bit conversion cannot band either.
    grain = (rng.random((height, width, 1), F) + rng.random((height, width, 1), F) - 1) * (.8 / 255)
    png(SKY / 'T_Sky_Space_8K.png', encoded + grain, 13)
    print(f'median {np.median(display, (0, 1))} p99 {np.percentile(display.mean(-1), 99):.3f}', flush=True)


# ---------------------------------------------------------------- planet and moon

SUN = np.array((-.66, .50, -.56), F)
SUN /= np.linalg.norm(SUN)
ATMOSPHERE = 1.042
H_RAY, H_MIE = .0092, .0030
B_RAY = np.array((4.2, 9.8, 23.0), F)
B_MIE = np.array((3.4, 3.4, 3.4), F)


def optical_table(sizes=(48, 180)):
    # Optical depth to the sun from height h, cosine mu. Inf-like inside the planet shadow.
    heights = np.linspace(0, ATMOSPHERE - 1, sizes[0])
    cosines = np.linspace(-1, 1, sizes[1])
    table = np.zeros((*sizes, 2), F)
    steps = 96
    for a, h in enumerate(heights):
        r = 1 + h
        for b, mu in enumerate(cosines):
            root = math.sqrt(max(ATMOSPHERE ** 2 - r * r * (1 - mu * mu), 0))
            far = -r * mu + root
            t = (np.arange(steps) + .5) / steps * far
            radius = np.sqrt(r * r + t * t + 2 * r * t * mu)
            ground = np.clip((1 - radius) / .004, 0, 1)
            ds = far / steps
            table[a, b, 0] = (np.exp(-(radius - 1).clip(0) / H_RAY) + ground * 40).sum() * ds
            table[a, b, 1] = (np.exp(-(radius - 1).clip(0) / H_MIE) + ground * 40).sum() * ds
    return table


TABLE = None


def sun_depth(h, mu):
    fa = np.clip(h / (ATMOSPHERE - 1), 0, 1) * (TABLE.shape[0] - 1)
    fb = np.clip((mu + 1) / 2, 0, 1) * (TABLE.shape[1] - 1)
    a, b = np.minimum(fa.astype(np.int32), TABLE.shape[0] - 2), np.minimum(fb.astype(np.int32), TABLE.shape[1] - 2)
    wa, wb = (fa - a)[..., None], (fb - b)[..., None]
    return ((TABLE[a, b] * (1 - wb) + TABLE[a, b + 1] * wb) * (1 - wa)
            + (TABLE[a + 1, b] * (1 - wb) + TABLE[a + 1, b + 1] * wb) * wa)


PLANET_R = 1680 / 4096
PLANET_C = (2330 / 4096, 2330 / 4096)     # x, y from top-left
MOON_R = 350 / 4096
MOON_C = (560 / 4096, 560 / 4096)


def turn(x, y, z):
    # Tilted spin axis, so cloud bands do not run straight across the card.
    c, s = math.cos(.42), math.sin(.42)
    x, y = x * c - y * s, x * s + y * c
    c, s = math.cos(.7), math.sin(.7)
    return x, y * c - z * s, y * s + z * c


def surface_band(arg):
    row0, row1, size, colour, cover = arg
    ys = ((np.arange(row0, row1) + .5) / size).astype(F)
    xs = ((np.arange(size) + .5) / size).astype(F)
    px, py = np.meshgrid((xs - PLANET_C[0]) / PLANET_R, (PLANET_C[1] - ys) / PLANET_R)
    r2 = px * px + py * py
    inside = r2 < 1
    cover[row0:row1] = inside
    if not inside.any():
        return
    nx, ny = px[inside], py[inside]
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    x, y, z = turn(nx, ny, nz)
    lit = nx * SUN[0] + ny * SUN[1] + nz * SUN[2]
    seen = lit > -.32
    wa, wb, wc = fbm(x, y, z, 1.2, 6, 60), fbm(x, y, z, 1.2, 6, 61), fbm(x, y, z, 1.2, 6, 62)
    wx, wy, wz = x + .16 * wa, y + .16 * wb, z + .16 * wc
    base = fbm(wx, wy, wz, 1.7, 11, 63, .55)
    coast = smooth(.34, .37, base + .16 * fbm(x, y, z, 24, 6, 64))
    rock = fbm(wx, wy, wz, 12, 8, 65, .60, 'ridge')
    # Mineral colours: gold deserts and dark basalt, since this is no second Earth.
    sand = np.array((.20, .135, .060), F)
    basalt = np.array((.075, .070, .075), F)
    moss = np.array((.075, .115, .060), F)
    mix = smooth(-.8, .9, fbm(wx, wy, wz, 4, 7, 66))[..., None]
    land = sand * mix + moss * (1 - mix)
    land = land * (1 - (smooth(.3, .8, rock) * .62)[..., None]) + basalt * (smooth(.3, .8, rock) * .62)[..., None]
    pole = smooth(.72, .9, np.abs(z) + .05 * wa)[..., None]
    land = land * (1 - pole) + .75 * pole
    shelf = smooth(.10, .35, base)[..., None]
    ocean = np.array((.0035, .017, .046), F) * (1 - shelf) + np.array((.012, .075, .095), F) * shelf
    ground = ocean * (1 - coast[..., None]) + land * coast[..., None]
    # Clouds: sheared bands, cyclone-like warps, two heights.
    bend = fbm(x, y, z, 1.7, 5, 67)
    qx, qy, qz = x + .10 * bend, y + .10 * wa, z * 1.9 + .30 * wc
    deck = fbm(qx, qy, qz, 2.6, 11, 68, .58)
    wisps = fbm(qx, qy * 1.3, qz, 6.5, 10, 69, .66, 'ridge')
    clouds = smooth(.34, .66, deck + 1.1 * (wisps - .30) + .30 * np.abs(z) + .25 * fbm(qx, qy, qz, 24, 6, 73, .6) + .24)
    ux, uy, uz = turn(np.full_like(nx, SUN[0]), np.full_like(nx, SUN[1]), np.full_like(nx, SUN[2]))
    shadow = smooth(.05, .85, fbm(qx + .012 * ux, qy + .012 * uy, qz + .03 * uz, 2.6, 7, 68, .58) + .35 * np.abs(z))
    h0 = np.zeros_like(lit)
    air = sun_depth(h0, lit)
    transmit = np.exp(-(air[..., 0, None] * B_RAY + air[..., 1, None] * B_MIE))
    # Cloud tops sit above most of the air, so they redden far less than the ground.
    bright = np.exp(-(air[..., 0, None] * B_RAY + air[..., 1, None] * B_MIE) * .62)
    wrap = np.clip((lit + .02) / 1.02, 0, 1)
    day = (ground * (1 - .75 * shadow[..., None]) * wrap[..., None]) * transmit * 3.0
    # Ocean sun glint, broken by wind and coastlines.
    vz = np.array((0, 0, 1), F)
    half = SUN + vz
    half /= np.linalg.norm(half)
    spec = np.clip(nx * half[0] + ny * half[1] + nz * half[2], 0, 1)
    gust = .55 + .25 * fbm(x, y, z, 30, 4, 70)
    glint = ((spec ** 900 * 9 + spec ** 90 * .10) * gust * (1 - coast) * (1 - clouds) * (lit > 0))[..., None] * transmit
    relief = np.clip((deck - fbm(qx + .006 * ux, qy + .006 * uy, qz + .015 * uz, 2.6, 11, 68, .58)) * 9, -.45, .6)
    white = (clouds * (.74 + relief))[..., None] * wrap[..., None] * bright * 2.3
    out = day * (1 - clouds[..., None]) + glint + white
    # Night cities, gold, on land under thin cloud, only well past the terminator.
    night = smooth(.02, -.16, lit)
    # Settlement: fine speckle gathered into regions and coasts, never connected ridges.
    region = smooth(.1, 1.0, fbm(wx, wy, wz, 5, 5, 72)) * (.35 + .65 * smooth(.42, .34, base))
    towns = smooth(.9, 1.7, fbm(x, y, z, 150, 2, 71, .55) + .5 * fbm(x, y, z, 60, 2, 74, .55)) * region
    out += (towns * coast * night * (1 - clouds) ** 2)[..., None] * np.array((1.0, .62, .24), F) * .16
    image = np.zeros((*inside.shape, 3), F)
    image[inside] = out * np.where(seen, 1, .999)[..., None].astype(F)
    colour[row0:row1] = image


def atmosphere_band(arg):
    row0, row1, size, scatter, through = arg
    ys = ((np.arange(row0, row1) + .5) / size).astype(F)
    xs = ((np.arange(size) + .5) / size).astype(F)
    px, py = np.meshgrid((xs - PLANET_C[0]) / PLANET_R, (PLANET_C[1] - ys) / PLANET_R)
    r2 = px * px + py * py
    keep = r2 < ATMOSPHERE ** 2
    if not keep.any():
        return
    x, y = px[keep], py[keep]
    r2 = r2[keep]
    z0 = np.sqrt(ATMOSPHERE ** 2 - r2)
    z1 = np.where(r2 < 1, np.sqrt(np.clip(1 - r2, 0, 1)), -z0)
    steps = 18
    ds = ((z0 - z1) / steps)[..., None]
    mu = SUN[2]  # cosine between the view ray (towards camera) and sun
    phase_r = .75 * (1 + mu * mu)
    g = .82
    phase_m = (1 - g * g) / (1 + g * g + 2 * g * mu) ** 1.5
    depth_r, depth_m = np.zeros_like(x), np.zeros_like(x)
    glow = np.zeros((len(x), 3), F)
    # March from the camera side down the ray.
    for i in range(steps):
        z = z0 - (i + .5) * ds[..., 0]
        radius = np.sqrt(r2 + z * z)
        h = np.clip(radius - 1, 0, None)
        rho_r, rho_m = np.exp(-h / H_RAY), np.exp(-h / H_MIE)
        depth_r += rho_r * ds[..., 0] * .5
        depth_m += rho_m * ds[..., 0] * .5
        cosine = (x * SUN[0] + y * SUN[1] + z * SUN[2]) / radius
        sun = sun_depth(h, cosine)
        decay = np.exp(-((depth_r + sun[..., 0])[..., None] * B_RAY + (depth_m + sun[..., 1])[..., None] * B_MIE))
        glow += decay * (rho_r[..., None] * B_RAY * phase_r + rho_m[..., None] * B_MIE * phase_m) * ds
        depth_r += rho_r * ds[..., 0] * .5
        depth_m += rho_m * ds[..., 0] * .5
    a, b = np.zeros((*keep.shape, 3), F), np.ones((*keep.shape, 3), F)
    a[keep] = glow
    b[keep] = np.exp(-(depth_r[..., None] * B_RAY + depth_m[..., None] * B_MIE))
    scatter[row0:row1] = a
    through[row0:row1] = b


def moon(size):
    """Returns premultiplied linear RGB and alpha for a phase-lit cratered moon."""
    rng = np.random.default_rng(9)
    g = (np.arange(size, dtype=F) + .5) / size * 2.08 - 1.04
    x, y = np.meshgrid(g, -g)
    inside = x * x + y * y < 1
    z = np.sqrt(np.clip(1 - x * x - y * y, 0, 1))
    height = np.zeros((size, size), F)
    px, py, pz = x * 1.0, y * 1.0, z * 1.0
    maria = fbm(px, py, pz, 1.0, 7, 80, .55)
    sea = smooth(.05, .55, maria)
    # Sizes follow a crater power law: few big basins, countless small pits.
    for rank in range(5200):
        radius = float(np.clip(.012 / (rng.uniform(0, 1) ** .62 + .010), .004, .24))
        centre = rng.normal(size=3)
        centre /= np.linalg.norm(centre)
        centre[2] = abs(centre[2]) * (1 if centre[2] > -.1 else 1)
        cx, cy = int((centre[0] + 1.04) / 2.08 * size), int((1.04 - centre[1]) / 2.08 * size)
        reach = int(radius * 2.6 / 2.08 * size) + 2
        x0, x1, y0, y1 = max(cx - reach, 0), min(cx + reach, size), max(cy - reach, 0), min(cy + reach, size)
        if x0 >= x1 or y0 >= y1:
            continue
        rho = np.arccos(np.clip(x[y0:y1, x0:x1] * centre[0] + y[y0:y1, x0:x1] * centre[1] + z[y0:y1, x0:x1] * centre[2], -1, 1)) / radius
        bowl = np.where(rho < 1, rho * rho - 1, 0) * .16 * radius
        rim = np.exp(-((rho - 1) / .22) ** 2) * .045 * radius
        ejecta = np.where(rho > 1, np.exp(-(rho - 1) * 2.4) * .02 * radius, 0)
        peak = np.exp(-(rho / .2) ** 2) * .09 * radius if radius > .05 else 0
        # Lava plains drowned the old craters, so only recent ones cut through a mare.
        flood = 1 - .78 * sea[y0:y1, x0:x1] if rank < 4300 else 1
        height[y0:y1, x0:x1] += (bowl + rim + ejecta + peak) * flood * (.38 + .62 * smooth(.012, .09, radius))
    rough = fbm(px, py, pz, 8, 4, 81, .55)
    height += .0006 * rough
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * size / 8.32
    dy = (np.roll(height, 1, 0) - np.roll(height, -1, 0)) * size / 8.32
    nx, ny, nz = x - dx * z, y - dy * z, z + dx * x + dy * y
    length = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
    lit = (nx * SUN[0] + ny * SUN[1] + nz * SUN[2]) / length
    geometric = x * SUN[0] + y * SUN[1] + z * SUN[2]
    # Bump may darken but not light rims past the true terminator, or thin arcs float in the dark.
    mu0 = np.clip(lit, 0, 1) * smooth(-.08, .07, geometric)
    # Lommel-Seeliger: airless bodies stay bright up to the limb.
    shade = mu0 / (mu0 + np.clip(z, .05, 1)) * 2
    tone = .25 - .135 * sea + .012 * rough
    tone = tone[..., None] * np.array((1.0, .95, .88), F)
    # The dark side keeps its albedo in faint planetshine, with bump, instead of a flat disc.
    shine = (.45 + .55 * np.clip(nz / length, 0, 1))[..., None] * np.array((.038, .052, .080), F) * tone / .22
    image = shade[..., None] * tone * 2.3 + shine * .16
    image *= inside[..., None]
    return image, inside.astype(F)


def build_planet():
    global TABLE
    size = 1024 if PREVIEW else 4096
    init_noise()
    begin = time.time()
    TABLE = optical_table()
    print(f'atmosphere table {time.time() - begin:.0f}s', flush=True)
    fine = size * 2
    colour, cover = shared((fine, fine, 3)), shared((fine, fine))
    parallel(surface_band, [(j, min(j + 48, fine), fine, colour, cover) for j in range(0, fine, 48)])
    print(f'surface {time.time() - begin:.0f}s', flush=True)
    scatter, through = shared((size, size, 3)), shared((size, size, 3))
    through[:] = 1
    parallel(atmosphere_band, [(j, min(j + 48, size), size, scatter, through) for j in range(0, size, 48)])
    print(f'air {time.time() - begin:.0f}s', flush=True)
    ground = area(colour * cover[..., None], size, size)
    disc = area(cover, size, size)
    image = ground * through + scatter
    alpha = disc + (1 - disc) * (1 - through.mean(-1))
    # The moon is rendered at twice its final size and laid into its corner.
    span = int(round(MOON_R * size * 2.08))
    shot, mask = moon(span * 2)
    shot, mask = area(shot, span, span), area(mask, span, span)
    x0, y0 = int(MOON_C[0] * size - span / 2), int(MOON_C[1] * size - span / 2)
    image[y0:y0 + span, x0:x0 + span] += shot
    alpha[y0:y0 + span, x0:x0 + span] += mask
    mapped = film(image, 1.0)
    rgba = np.dstack((srgb(mapped), np.clip(alpha, 0, 1)))
    png(SKY / 'T_Sky_Planet_4K.png', rgba)
    print(f'planet {time.time() - begin:.0f}s edge alpha {max(alpha[0].max(), alpha[-1].max(), alpha[:, 0].max(), alpha[:, -1].max()):.4f}', flush=True)


# ---------------------------------------------------------------- volumetric flipbooks

LIGHT = np.array((-.72, .60, .36), F)
LIGHT /= np.linalg.norm(LIGHT)


class Blast:
    # A few big uneven lobes clustered on favoured directions: the silhouette comes from here.
    def __init__(self, seed, count, reach, low, high):
        rng = np.random.default_rng(seed)
        major = rng.normal(size=(4, 3))
        major /= np.linalg.norm(major, axis=1, keepdims=True)
        d = major[np.arange(count) % 4] + rng.normal(size=(count, 3)) * .62
        self.dirs = (d / np.linalg.norm(d, axis=1, keepdims=True)).astype(F)
        self.speed = (rng.uniform(.30, 1, count) * reach).astype(F)
        self.size = (low + (high - low) * rng.uniform(0, 1, count) ** 1.8).astype(F)
        self.dirs[0] *= 0


# Fluid solve. Noise iso-surfaces gave foil creases and ball silhouettes, so the flipbooks now
# come from a real 3D solve: combustion with gas expansion, FFT pressure projection, MacCormack
# scalar advection and vorticity confinement. Velocity is in cells per step, in a periodic box
# with a sponge at its walls. Rendering ray-marches the stored density and temperature fields.
SIMS = {
    'fire': dict(seed=61, lobes=13, reach=.62, low=.19, high=.42, steps=190, spread=.20, rate=.050, expand=3.4, soot=1.,
                 heat=1.9, c0=.012, c3=.055, drag=.016, vort=.30, ease=1.55, stir=1.6),
    'smoke': dict(seed=62, lobes=9, reach=.52, low=.22, high=.44, steps=230, spread=.19, rate=.040, expand=2.6, soot=1.,
                  heat=1.2, c0=.016, c3=0., drag=.020, vort=.42, ease=1.25, stir=2.0),
}
G = {}
FRAME = None
DETAIL = None
SIM_DIR = ROOT / 'Saved/FXPreview/sim'


def take3(flat, n, ix, iy, iz, bounds=False):
    ix, iy, iz = np.clip(ix, 0, n - 1.001), np.clip(iy, 0, n - 1.001), np.clip(iz, 0, n - 1.001)
    i, j, k = ix.astype(np.int32), iy.astype(np.int32), iz.astype(np.int32)
    fx, fy, fz = ix - i, iy - j, iz - k
    at = (i * n + j) * n + k
    c000, c001, c010, c011 = flat[at], flat[at + 1], flat[at + n], flat[at + n + 1]
    far = at + n * n
    c100, c101, c110, c111 = flat[far], flat[far + 1], flat[far + n], flat[far + n + 1]
    value = (((c000 * (1 - fz) + c001 * fz) * (1 - fy) + (c010 * (1 - fz) + c011 * fz) * fy) * (1 - fx)
             + ((c100 * (1 - fz) + c101 * fz) * (1 - fy) + (c110 * (1 - fz) + c111 * fz) * fy) * fx)
    if not bounds:
        return value
    every = np.stack((c000, c001, c010, c011, c100, c101, c110, c111))
    return value, every.min(0), every.max(0)


def trace_slab(arg):
    a, b = arg
    n, u = G['n'], G['u']
    i, j, k = np.meshgrid(np.arange(a, b, dtype=F), np.arange(n, dtype=F), np.arange(n, dtype=F), indexing='ij')
    flats = [c.reshape(-1) for c in u]
    mid = [take3(f, n, i - .5 * u[0, a:b], j - .5 * u[1, a:b], k - .5 * u[2, a:b]) for f in flats]
    bx, by, bz = i - mid[0], j - mid[1], k - mid[2]
    G['foot'][0, a:b], G['foot'][1, a:b], G['foot'][2, a:b] = mid[0], mid[1], mid[2]
    for c, f in enumerate(flats):
        G['u2'][c, a:b] = take3(f, n, bx, by, bz)
    for c in range(3):
        f = G['s'][c].reshape(-1)
        G['fwd'][c, a:b] = take3(f, n, bx, by, bz)


def correct_slab(arg):
    a, b = arg
    n, m = G['n'], G['foot']
    i, j, k = np.meshgrid(np.arange(a, b, dtype=F), np.arange(n, dtype=F), np.arange(n, dtype=F), indexing='ij')
    ox, oy, oz = i + m[0, a:b], j + m[1, a:b], k + m[2, a:b]
    bx, by, bz = i - m[0, a:b], j - m[1, a:b], k - m[2, a:b]
    for c in range(3):
        back = take3(G['fwd'][c].reshape(-1), n, ox, oy, oz)
        value, low, high = take3(G['s'][c].reshape(-1), n, bx, by, bz, True)
        G['s2'][c, a:b] = np.clip(G['fwd'][c, a:b] + .5 * (G['s'][c, a:b] - back), low, high)


def project(u, source, k, k2):
    # Solves div(u) = source spectrally, so the expansion of burning gas pushes the flow.
    n = u.shape[1]
    with ThreadPoolExecutor(4) as pool:
        hats = list(pool.map(np.fft.rfftn, [u[0], u[1], u[2], source]))
    phi = -(1j * (k[0] * hats[0] + k[1] * hats[1] + k[2] * hats[2]) - hats[3]) / k2
    phi[0, 0, 0] = 0

    def back(c):
        u[c] = np.fft.irfftn(hats[c] - 1j * k[c] * phi, (n, n, n)).astype(F)

    with ThreadPoolExecutor(3) as pool:
        list(pool.map(back, range(3)))


def confine(u, strength):
    d = lambda f, axis: (np.roll(f, -1, axis) - np.roll(f, 1, axis)) * .5
    wx, wy, wz = d(u[2], 1) - d(u[1], 2), d(u[0], 2) - d(u[2], 0), d(u[1], 0) - d(u[0], 1)
    size = np.sqrt(wx * wx + wy * wy + wz * wz)
    gx, gy, gz = d(size, 0), d(size, 1), d(size, 2)
    norm = np.sqrt(gx * gx + gy * gy + gz * gz) + 1e-5
    gx, gy, gz = gx / norm, gy / norm, gz / norm
    u[0] += strength * (gy * wz - gz * wy)
    u[1] += strength * (gz * wx - gx * wz)
    u[2] += strength * (gx * wy - gy * wx)


def simulate(name, n, frames):
    cfg = SIMS[name]
    SIM_DIR.mkdir(parents=True, exist_ok=True)
    shape = (frames, n, n, n)
    paths = SIM_DIR / f'{name}_{n}_rho.f16', SIM_DIR / f'{name}_{n}_temp.f16'
    if 'noresim' in ARGS and paths[0].exists():
        return np.memmap(paths[0], np.float16, 'r', shape=shape), np.memmap(paths[1], np.float16, 'r', shape=shape)
    out_rho, out_temp = np.memmap(paths[0], np.float16, 'w+', shape=shape), np.memmap(paths[1], np.float16, 'w+', shape=shape)
    begin = time.time()
    axis = (np.arange(n, dtype=F) + .5) / n * 2 - 1
    x, y, z = np.meshgrid(axis, axis, axis, indexing='ij')
    blast = Blast(cfg['seed'], cfg['lobes'], cfg['reach'], cfg['low'], cfg['high'])
    phi = np.zeros_like(x)
    for d, speed, size in zip(blast.dirs, blast.speed, blast.size):
        c = d * speed * cfg['spread'] / .2 * .30
        r = size * .50
        phi += np.exp(-((x - c[0]) ** 2 + (y - c[1]) ** 2 + (z - c[2]) ** 2) / (r * r) * 1.5)
    pockets = fbm(x, y, z, 1.2, 3, 90, .55)
    fine = fbm(x, y, z, 3.4, 3, 91, .55)
    fuel = smooth(.42, .95, phi * (1 + .42 * pockets + .20 * fine))
    speedmap = np.exp(.75 * fbm(x, y, z, 1.7, 3, 92, .55))
    psi = [fbm(x, y, z, 1.5, 4, 93 + c, .6) for c in range(3)]
    d = lambda f, axis: (np.roll(f, -1, axis) - np.roll(f, 1, axis)) * .5
    curl = np.stack((d(psi[2], 1) - d(psi[1], 2), d(psi[0], 2) - d(psi[2], 0), d(psi[1], 0) - d(psi[0], 1)))
    del psi
    curl *= cfg['stir'] / curl.std() * smooth(.0, .5, phi)
    G.update(n=n, u=shared((3, n, n, n)), u2=shared((3, n, n, n)), foot=shared((3, n, n, n)),
             s=shared((3, n, n, n)), s2=shared((3, n, n, n)), fwd=shared((3, n, n, n)))
    G['u'][:] = curl
    del curl
    G['s'][0], G['s'][1], G['s'][2] = fuel * .15, fuel * .75, fuel     # rho, temp, fuel
    wall = smooth(.985, .84, np.maximum(np.maximum(np.abs(x), np.abs(y)), np.abs(z)))
    del x, y, z, phi, pockets, fine
    a = np.fft.fftfreq(n).astype(F) * 2 * math.pi
    b = np.fft.rfftfreq(n).astype(F) * 2 * math.pi
    k = np.stack(np.broadcast_arrays(a[:, None, None], a[None, :, None], b[None, None, :])).astype(F)
    k2 = (k * k).sum(0)
    k2[0, 0, 0] = 1
    slabs = [(i, min(i + max(n // 16, 1), n)) for i in range(0, n, max(n // 16, 1))]
    steps = cfg['steps']
    # A slow start can round two frames onto one step; each must still be stored.
    plan = {}
    last = 2
    for f in range(frames):
        at = max(int(round((f / (frames - 1)) ** cfg['ease'] * steps)), last + 1)
        plan[at] = f
        last = at
    steps = max(steps, last)
    for step in range(1, steps + 1):
        parallel(trace_slab, slabs, 8)
        parallel(correct_slab, slabs, 8)
        G['u'][:] = G['u2']
        G['s'][:] = G['s2']
        rho, temp, fuel = G['s']
        burn = np.minimum(fuel, cfg['rate'] * speedmap * smooth(.08, .28, temp))
        fuel -= burn
        rho += cfg['soot'] * burn
        temp += cfg['heat'] * burn
        temp *= np.exp(-(cfg['c0'] + cfg['c3'] * temp ** 3))
        np.clip(temp, 0, 1.25, temp)
        source = burn * cfg['expand']
        confine(G['u'], cfg['vort'])
        G['u'] *= (1 - cfg['drag']) * wall
        rho *= wall
        project(G['u'], source, k, k2)
        np.clip(G['u'], -4.5, 4.5, G['u'])
        if step in plan:
            f = plan[step]
            out_rho[f], out_temp[f] = rho.astype(np.float16), temp.astype(np.float16)
        if step % 20 == 0:
            print(f'  {name} step {step}/{steps} {time.time() - begin:.0f}s rho {rho.max():.2f} temp {temp.max():.2f} '
                  f'speed {np.abs(G["u"]).max():.2f}', flush=True)
    out_rho.flush(), out_temp.flush()
    return out_rho, out_temp


def set_frame(index, t):
    global FRAME, DETAIL
    FRAME = SIMDATA[0][index].astype(F).reshape(-1), SIMDATA[1][index].astype(F).reshape(-1), SIMDATA[0].shape[1]
    DETAIL = .78 + .55 * t


SIMDATA = None
VIEW = .68       # frames the blast tighter, so fewer texels go to empty space


def lookup(x, y, z):
    rho, temp, n = FRAME
    scale = n / 2
    return take3(rho, n, (x + 1) * scale - .5, (y + 1) * scale - .5, (z + 1) * scale - .5), temp, n, scale


def detailed(x, y, z, big, fine):
    # Wavelet-style upres: sub-grid billows from warping the lookup, in coordinates that grow
    # with the blast, so the added detail travels outward instead of swimming.
    rho, temp, n = FRAME
    scale = n / 2
    x, y, z = x * VIEW, y * VIEW, z * VIEW
    coarse = take3(rho, n, (x + 1) * scale - .5, (y + 1) * scale - .5, (z + 1) * scale - .5)
    out_rho, out_temp = np.zeros_like(x), np.zeros_like(x)
    keep = coarse > 2e-3
    if not keep.any():
        return out_rho, out_temp
    px, py, pz = x[keep], y[keep], z[keep]
    qx, qy, qz = px / DETAIL, py / DETAIL, pz / DETAIL + 2.0
    w = [fbm(qx, qy, qz, 3.6, 2, 26 + c, .5) * big + fbm(qx, qy, qz, 9.5, 2, 29 + c, .5) * fine for c in range(3)]
    ix, iy, iz = (px + w[0] + 1) * scale - .5, (py + w[1] + 1) * scale - .5, (pz + w[2] + 1) * scale - .5
    out_rho[keep], out_temp[keep] = take3(rho, n, ix, iy, iz), take3(temp, n, ix, iy, iz)
    return out_rho, out_temp


def fire_field(x, y, z, t):
    rho, temp = detailed(x, y, z, .026, .011)
    low = .03 + .95 * smooth(.42, 1, t) ** 1.5
    density = smooth(low, low + .30 + .25 * t, rho) * (1 - smooth(.86, 1, t))
    guard = smooth(.965, .86, np.maximum(np.abs(x), np.abs(y)))
    return density * guard, np.clip(temp, 0, 1.12)


def smoke_field(x, y, z, t):
    rho, _ = detailed(x, y, z, .030, .013)
    # Thin out softly: a hard rising threshold over warped detail leaves hair, not haze.
    low = .03 + .34 * smooth(.40, 1, t)
    density = smooth(low, low + .55 + .35 * t, rho) * (1 - smooth(.62, 1, t)) ** 1.3
    guard = smooth(.965, .86, np.maximum(np.abs(x), np.abs(y)))
    return density * guard, np.zeros_like(x)


def blur3(volume, sigma):
    spectrum = np.fft.rfftn(volume)
    n = volume.shape[0]
    a = np.fft.fftfreq(n).astype(F)
    b = np.fft.rfftfreq(n).astype(F)
    k2 = a[:, None, None] ** 2 + a[None, :, None] ** 2 + b[None, None, :] ** 2
    return np.fft.irfftn(spectrum * np.exp(-2 * (math.pi * sigma) ** 2 * k2), volume.shape).astype(F)


def resize2(slice2, n):
    # Bilinear upscale of a coarse slice to the fine grid.
    m = slice2.shape[0]
    at = (np.arange(n, dtype=F) + .5) / n * m - .5
    i = np.clip(np.floor(at).astype(int), 0, m - 2)
    w = (at - i).astype(F)
    a = slice2[i] * (1 - w)[:, None] + slice2[i + 1] * w[:, None]
    return a[:, i] * (1 - w)[None, :] + a[:, i + 1] * w[None, :]


def shift2(image, dx, dy):
    # Sub-pixel shift used by the sheared light sweep.
    ix, iy = int(math.floor(dx)), int(math.floor(dy))
    fx, fy = dx - ix, dy - iy
    a = np.roll(np.roll(image, iy, 0), ix, 1)
    b = np.roll(a, 1, 1)
    return ((a * (1 - fx) + b * fx) * (1 - fy) + (np.roll(a, 1, 0) * (1 - fx) + np.roll(b, 1, 0) * fx) * fy)


def volume_frame(field, t, n, emissive, albedo, extinction):
    """Streaming slice march, front to back, with the light swept in the same direction."""
    axis = (np.arange(n, dtype=F) + .5) / n * 2 - 1
    x, y = np.meshgrid(axis, -axis)
    # Coarse pass: multiple scattering and fire-light on soot both come from a blurred volume.
    coarse = 72
    grid = (np.arange(coarse, dtype=F) + .5) / coarse * 2 - 1
    cx, cy, cz = np.meshgrid(grid, -grid, -grid, indexing='xy')
    low, hot = field(cx, cy, cz, t)
    occlude = blur3(low, 3.2)
    glow = np.zeros_like(low)
    if emissive:
        glow = blur3(low * np.clip(hot, 0, 1.1) ** 3, 6.0)
    dz = 2 / n
    step = dz * extinction
    shear = (LIGHT[0] / LIGHT[2], LIGHT[1] / LIGHT[2])
    tau_light = np.zeros((n, n), F)
    through = np.ones((n, n), F)
    lit, burn, weight = np.zeros((n, n, 3), F), np.zeros((n, n, 3), F), np.zeros((n, n), F)
    tint = np.array((1.0, .96, .90), F)
    sky = np.array((.17, .20, .27), F)
    for k in range(n):
        z = 1 - (k + .5) * dz
        rho, temp = field(x, y, np.full_like(x, z), t)
        at = (k + .5) / n * coarse - .5
        c0 = min(max(int(at), 0), coarse - 2)
        w = at - c0
        ambient = resize2(occlude[c0 + 1 - 1] * (1 - w) + occlude[c0 + 1] * w, n)
        if emissive:
            soot = 1 - .90 * smooth(.25, .95, temp)
            sigma = rho * (.34 + 1.65 * soot * (.42 + .58 * smooth(.02, .6, t)))
        else:
            sigma = rho
        a = 1 - np.exp(-sigma * step)
        sun = np.exp(-tau_light * extinction * .78)
        fill = np.exp(-ambient * 2.1)
        radiance = sun[..., None] * tint * 1.25 + fill[..., None] * sky
        if emissive:
            fire = resize2(glow[c0] * (1 - w) + glow[c0 + 1] * w, n)
            radiance = radiance + (fire * 2.6)[..., None] * np.array((1.0, .36, .09), F)
        lit += (through * a)[..., None] * radiance * albedo
        if emissive:
            kelvin = 850 + 2900 * np.clip(temp, 0, 1.12)
            power = np.clip(temp, 0, 1.12) ** 4.6 * 3.0 + np.clip(temp, 0, 1) ** 1.25 * .50
            # Saturated above plain blackbody: film and camera response keep flame orange, not cream.
            energy = (through * rho * power * dz * 9)[..., None] * planck(kelvin) ** 2.3
            burn += energy
            weight += through * rho * power * dz * temp
        through = through * (1 - a)
        # Advance the light a slice deeper, sheared so it comes from up and to the left.
        tau_light = shift2(tau_light, shear[0], shear[1]) + rho * dz
    alpha = 1 - through
    colour = lit / np.maximum(alpha, 1e-4)[..., None]
    energy = burn.mean(-1) + 1e-6
    return colour, alpha, burn, np.clip(weight / energy, 0, 1)


def bleed(rgb, alpha):
    # Straight-alpha colour must continue past the silhouette, or filtering and mips drag the
    # black of empty texels into the edge. Fill from a colour pyramid of the solid pixels.
    h = alpha.shape[0]
    solid = (alpha > .004).astype(F)
    weighted = rgb * solid[..., None]
    fill = None
    for div in (256, 128, 64, 32, 16, 8, 4, 2):
        low_w = area(solid, h // div, h // div)
        low_c = area(weighted, h // div, h // div) / np.maximum(low_w, 1e-4)[..., None]
        known = resize2(low_w, h) > .02
        up = np.stack([resize2(low_c[..., c], h) for c in range(3)], -1)
        fill = up if fill is None else np.where(known[..., None], up, fill)
    return np.where(solid[..., None] > 0, rgb, fill)


def fire_tile(arg):
    index, n, tile, base, emit, temp = arg
    t = index / 63
    set_frame(index, t)
    colour, alpha, burn, heat = volume_frame(fire_field, t, n, True, np.array((.065, .058, .054), F), 36)
    row, col = index // 8, index % 8
    y0, x0 = row * tile, col * tile
    base[y0:y0 + tile, x0:x0 + tile, :3] = area(colour * alpha[..., None], tile, tile) / np.maximum(area(alpha, tile, tile), 1e-4)[..., None]
    base[y0:y0 + tile, x0:x0 + tile, 3] = area(alpha, tile, tile)
    emit[y0:y0 + tile, x0:x0 + tile] = area(burn, tile, tile)
    temp[y0:y0 + tile, x0:x0 + tile] = area(heat, tile, tile)
    print(f'  fire {index}', end='', flush=True)


def build_fire():
    global SIMDATA, VIEW
    init_noise()
    VIEW = .86       # the fire spreads wider than the smoke, and must clear the tile guard
    grid = 112 if PREVIEW else 192
    SIMDATA = simulate('fire', grid, 64)
    tile, n = (128, 192) if PREVIEW else (256, 384)
    size = tile * 8
    base, emit, temp = shared((size, size, 4)), shared((size, size, 3)), shared((size, size))
    begin = time.time()
    parallel(fire_tile, [(i, n, tile, base, emit, temp) for i in range(64)], 14)
    print(f'\nfire {time.time() - begin:.0f}s', flush=True)
    peak = float(np.percentile(emit.max(-1), 99.9))
    print(f'fire emissive gain {peak:.3f}', flush=True)
    finish = np.concatenate((srgb(np.clip(emit / peak, 0, 1)), temp[..., None]), 2)
    png(FX / 'T_FX_Fireball_Emissive.png', finish)
    base[..., :3] = srgb(bleed(np.clip(base[..., :3], 0, 1), base[..., 3]))
    png(FX / 'T_FX_Fireball_BaseColor.png', base)
    edges(base[..., 3], 8, 'fire')


def smoke_tile(arg):
    index, n, sheet = arg
    t = index / 35
    set_frame(index, t)
    colour, alpha, _, _ = volume_frame(smoke_field, t, n, False, np.array((.34, .335, .35), F), 16)
    y0, x0 = (index // 6) * n, (index % 6) * n
    sheet[y0:y0 + n, x0:x0 + n, :3] = colour
    sheet[y0:y0 + n, x0:x0 + n, 3] = alpha
    print(f'  smoke {index}', end='', flush=True)


def build_smoke():
    global SIMDATA
    init_noise()
    grid = 112 if PREVIEW else 192
    SIMDATA = simulate('smoke', grid, 36)
    n, size = (180, 1024) if PREVIEW else (420, 2048)
    sheet = shared((n * 6, n * 6, 4))
    begin = time.time()
    parallel(smoke_tile, [(i, n, sheet) for i in range(36)], 14)
    print(f'\nsmoke {time.time() - begin:.0f}s', flush=True)
    # 6 does not divide 2048, so the sheet is rendered large and box-resampled exactly.
    premult = np.concatenate((sheet[..., :3] * sheet[..., 3:], sheet[..., 3:]), 2)
    small = area(premult, size, size)
    colour = bleed(np.clip(small[..., :3] / np.maximum(small[..., 3:], 1e-4), 0, 1), small[..., 3])
    out = np.concatenate((srgb(colour), small[..., 3:]), 2)
    png(FX / 'T_FX_SmokePuff_BaseColor.png', out)
    edges(out[..., 3], 6, 'smoke')


def edges(alpha, cells, name):
    size = alpha.shape[0]
    worst = 0
    for i in range(1, cells):
        at = round(i * size / cells)
        worst = max(worst, alpha[at - 1:at + 1].max(), alpha[:, at - 1:at + 1].max())
    print(f'{name} worst alpha on cell borders {worst:.4f}, frame last peak {alpha[-size // cells:, -size // cells:].max():.4f}', flush=True)


# ---------------------------------------------------------------- sprites

def bezier(rng):
    a = np.array((rng.uniform(.15, .3), rng.uniform(.2, .8)))
    d = np.array((rng.uniform(.7, .88), rng.uniform(.2, .8)))
    c = (a + d) / 2 + rng.uniform(-.14, .14, 2)
    return a, c, d


def trace(u, v, points, widths, heats, canvas):
    # Glowing polyline. Canvas accumulates heat so overlapping streaks get hotter.
    a, b = points[:-1], points[1:]
    for p, q, w0, h0 in zip(a, b, widths, heats):
        ex, ey = q - p
        fx, fy = u - p[0], v - p[1]
        s = np.clip((fx * ex + fy * ey) / max(ex * ex + ey * ey, 1e-9), 0, 1)
        d2 = (fx - s * ex) ** 2 + (fy - s * ey) ** 2
        canvas[...] = np.maximum(canvas, h0 * np.exp(-d2 / (w0 * w0)) + .16 * h0 * np.exp(-np.sqrt(d2) / (w0 * 5)))


def spark_cell(index, n, rng):
    size = n * 2
    v, u = (np.mgrid[0:size, 0:size].astype(F) + .5) / size
    canvas = np.zeros((size, size), F)
    kind = index // 4
    if kind < 2:   # long curved streaks, head hot, tail cooling
        for _ in range(1 + index % 3):
            a, c, d = bezier(rng)
            s = np.linspace(0, 1, 34)[:, None]
            path = (1 - s) ** 2 * a + 2 * s * (1 - s) * c + s * s * d
            life = np.linspace(.15, 1.12, 33) ** 1.7 * rng.uniform(.75, 1)
            life *= .82 + .18 * np.sin(np.linspace(0, rng.uniform(8, 18), 33) + rng.uniform(0, 6))
            trace(u, v, path, np.linspace(.0026, .0085, 33) * rng.uniform(.9, 1.5), life, canvas)
    elif kind == 2:   # drifting embers: hot specks of many sizes, a few with short tails
        for _ in range(16 + 5 * (index % 4)):
            c = np.clip(rng.normal(.5, .17, 2), .1, .9)
            step = rng.normal(0, .012, 2)
            path = np.stack((c, c + step), 0)
            trace(u, v, path, np.array((rng.uniform(.0025, .0095),)), np.array((rng.uniform(.35, 1.15),)), canvas)
    else:   # radial burst of fine sparks
        for _ in range(26 + 8 * (index % 3)):
            turn_ = rng.uniform(0, 6.3)
            near, far = rng.uniform(.02, .2), rng.uniform(.2, .46)
            bend = rng.uniform(-.06, .06)
            s = np.linspace(0, 1, 9)[:, None]
            r = near + (far - near) * s
            angle = turn_ + bend * s
            path = .5 + r * np.concatenate((np.cos(angle), np.sin(angle)), 1)
            trace(u, v, path, np.linspace(.0020, .0050, 8), np.linspace(.2, rng.uniform(.5, 1.1), 8), canvas)
    window = smooth(.0, .07, u) * smooth(1, .93, u) * smooth(0, .07, v) * smooth(1, .93, v)
    canvas *= window
    return area(canvas, n, n)


def build_sprites():
    size = 512 if PREVIEW else 1024
    rng = np.random.default_rng(31)
    cell = size // 4
    heat = np.zeros((size, size), F)
    for i in range(16):
        heat[(i // 4) * cell:(i // 4 + 1) * cell, (i % 4) * cell:(i % 4 + 1) * cell] = spark_cell(i, cell, rng)
    heat = np.clip(heat, 0, 1.25) / 1.25
    kelvin = 1100 + 5400 * heat
    rgb = planck(kelvin)
    power = heat ** .55
    png(FX / 'T_FX_Sparks.png', np.concatenate((srgb(rgb * power[..., None]), heat[..., None] ** .6), 2))

    # Laser bolt: R core, G sheath, B glow. Slow plasma breathing along its length.
    h, w = (128, 512) if PREVIEW else (512, 2048)
    fine = 2
    y, x = np.mgrid[0:h * fine, 0:w * fine].astype(F)
    x = (x + .5) / (w * fine) * 2 - 1
    y = ((y + .5) / (h * fine) - .5) * (h / w * 2)
    head, tail = .80, -.84
    s = np.clip((x - tail) / (head - tail), 0, 1)
    px = tail + s * (head - tail)
    d = np.sqrt((x - px) ** 2 + y * y)
    wobble = .94 + .035 * np.sin(s * 13 + 1) + .02 * np.sin(s * 29 + 2)
    width = .0060 + .0190 * s ** 1.5
    r = np.exp(-(d / (width * wobble)) ** 2.2)
    g = np.exp(-(d / (width * 2.6)) ** 1.5) * (.25 + .75 * s ** .8)
    b = np.exp(-(d / (.022 + .038 * s)) ** 2) * (.06 + .94 * s ** 1.6)
    guard = smooth(1, .92, np.abs(x)) * smooth(.25, .21, np.abs(y))
    r, g, b = r * guard, g * guard, b * guard
    a = np.clip(r + .75 * g + .38 * b, 0, 1)
    png(FX / 'T_FX_LaserBolt.png', area(np.dstack((r, g, b, a)), h, w))

    # Engine glow: R core, G corona with faint jets, B anamorphic streak.
    s = 512 if PREVIEW else 2048
    y, x = (np.mgrid[0:s, 0:s].astype(F) + .5) / s * 2 - 1
    r = np.sqrt(x * x + y * y)
    theta = np.arctan2(y, x)
    fan = sum(np.cos(theta * m + p) * c for m, p, c in ((7, .3, .3), (13, 1.2, .24), (23, 2.5, .17), (41, .8, .12)))
    core = np.exp(-(r / .050) ** 2)
    corona = (np.exp(-r / .085) * .7 + .30 / (1 + (r / .16) ** 2) ** 1.6) * (1 + .22 * fan * smooth(.05, .4, r))
    streak = np.exp(-(y / (.0065 + .012 * np.abs(x))) ** 2) * np.exp(-np.abs(x) / .30) + .20 * np.exp(-(x / .0075) ** 2) * np.exp(-np.abs(y) / .16)
    guard = smooth(.99, .72, r)
    core, corona, streak = core * guard, corona * guard, streak * guard
    png(FX / 'T_FX_EngineGlow.png', np.dstack((core, corona / corona.max(), streak, np.clip(core + corona + .6 * streak, 0, 1))))


# ---------------------------------------------------------------- soundtrack

RATE = 44100
SECONDS = 42
INSIDE = 33.6


def band(signal, low, high, order=4):
    # Smooth-sloped FFT band filter on a padded signal, so nothing rings around the wrap.
    pad = len(signal) + RATE
    spectrum = np.fft.rfft(signal, pad)
    freq = np.fft.rfftfreq(pad, 1 / RATE) + 1e-3
    gain = 1 / np.sqrt(1 + (low / freq) ** (2 * order)) / np.sqrt(1 + (freq / high) ** (2 * order))
    return np.fft.irfft(spectrum * gain, pad)[:len(signal)]


def cannon(rng, heavy, distance):
    """A deep shot: sub drop, falling harmonic body, soft chest-thump transient, rumble tail."""
    length = int(RATE * (1.2 if heavy else .85))
    t = np.arange(length) / RATE
    top, low = (rng.uniform(150, 190), rng.uniform(40, 48)) if heavy else (rng.uniform(205, 260), rng.uniform(58, 72))
    pitch = low + (top - low) * np.exp(-t * (15 if heavy else 20))
    phase = 2 * math.pi * np.cumsum(pitch) / RATE
    body = sum(np.sin(phase * h + h) / h ** 1.25 for h in range(1, 8))
    body *= np.exp(-t * (6.5 if heavy else 9.5)) * (1 - np.exp(-t * 700))
    sub = np.sin(2 * math.pi * np.cumsum(38 + 74 * np.exp(-t * 26)) / RATE) * np.exp(-t * 6.5)
    noise = rng.normal(0, 1, length)
    knock = band(noise, 70, 1000, 2)
    knock = knock / np.abs(knock).max() * np.exp(-t * 90)
    rumble = band(noise, 35, 300, 2)
    rumble = rumble / np.abs(rumble).max() * np.exp(-t * 7) * (1 - np.exp(-t * 60))
    shot = body * .5 + sub * (.9 if heavy else .55) + knock * .32 + rumble * .34
    # Distance takes the top off first, as it does in air.
    return band(shot, 22, 1500 - 1180 * distance, 2) / 1.7


def blast(rng, seconds, big):
    length = int(RATE * seconds)
    t = np.arange(length) / RATE
    noise = rng.normal(0, 1, length)
    deep = band(noise, 22, 95, 2)
    mid = band(noise, 80, 340, 2)
    top = band(noise, 300, 1600, 2)
    shape = (1 - np.exp(-t * 80))
    out = (deep / deep.std() * np.exp(-t * 1.7 / seconds * 3.2) * .48 + mid / mid.std() * np.exp(-t * 3.6 / seconds * 3.2) * .22
           + top / top.std() * np.exp(-t * 11 / seconds * 3.2) * .08) * shape
    out += np.sin(2 * math.pi * np.cumsum(28 + 60 * np.exp(-t * 11)) / RATE) * np.exp(-t * 3.2) * (1.0 if big else .55)
    # Soft debris patter on the hull, never above the low mids.
    grains = np.zeros(length)
    for start in rng.uniform(.25, seconds * .8, 90 if big else 40):
        at = int(start * RATE)
        size = int(RATE * rng.uniform(.012, .05))
        if at + size < length:
            grains[at:at + size] += rng.normal(0, 1, size) * np.hanning(size) * rng.uniform(.1, .6) * math.exp(-start * 1.2)
    return (out + band(grains, 160, 1300, 2) * .7) / 1.3


def voice(n, t, notes, cutoff, levels, seed):
    # Low brass and strings: detuned band-limited saws through a slowly opening filter.
    rng = np.random.default_rng(seed)
    out = np.zeros((2, n))
    for note, level in zip(notes, levels):
        for detune, side in ((-.14, 0), (.11, 1), (.03, .5)):
            f0 = note + detune
            start = rng.uniform(0, 6.3)
            for h in range(1, int(1300 / f0) + 1):
                f = f0 * h
                gain = 1 / h / (1 + (f / cutoff) ** 4)
                wave_ = np.sin(2 * math.pi * f * t + start * h) * gain
                out[0] += wave_ * level * (1 - side)
                out[1] += wave_ * level * side
    return out


def build_audio():
    previous = AUDIO / 'S_Opening.wav'
    keep = AUDIO / 'S_Opening_v1.wav'
    if not keep.exists():
        shutil.copy2(previous, keep)
    rng = np.random.default_rng(2312)
    n = SECONDS * RATE
    t = np.arange(n) / RATE
    rise = np.clip((t - 6) / 14, 0, 1) ** 1.6
    near = np.zeros((2, n))
    send = np.zeros((2, n))

    def place(sound, start, pan, level, wet):
        begin = int(start * RATE)
        if begin >= n:
            return
        sound = sound[:n - begin]
        angle = pan * math.pi / 2
        delay = int(abs(pan - .5) * .022 * RATE)
        l, r = math.cos(angle), math.sin(angle)
        for channel, gain, late in ((0, l, delay if pan > .5 else 0), (1, r, delay if pan < .5 else 0)):
            s = sound[:n - begin - late]
            near[channel, begin + late:begin + late + len(s)] += s * gain * level
            send[channel, begin + late:begin + late + len(s)] += s * gain * level * wet

    # Gun batteries, each with its own cadence, so it plays as an exchange, not as noise.
    batteries = ((.28, 3.1, 3, .15, False, .78, 7.0), (.72, 2.3, 2, .34, True, .66, 9.5), (.12, 1.7, 4, .28, False, .52, 12.5),
                 (.86, 1.45, 3, .20, False, .42, 15), (.44, 2.7, 2, .52, True, .24, 18), (.60, 1.25, 4, .36, False, .30, 21),
                 (.32, 3.3, 3, .46, True, .16, 24))
    for pan, period, burst, level, heavy, distance, begin in batteries:
        when = begin
        while when < INSIDE:
            count = rng.integers(max(burst - 1, 1), burst + 1)
            for i in range(count):
                shot_at = when + i * (period * .13) * rng.uniform(.9, 1.1)
                if shot_at >= INSIDE + .1:
                    continue
                scale = level * (.30 + .70 * rise[min(int(shot_at * RATE), n - 1)]) * rng.uniform(.8, 1.1)
                place(cannon(rng, heavy, distance), shot_at, pan + rng.uniform(-.05, .05), scale, .22 + .55 * distance)
            when += period * rng.uniform(.82, 1.2)
    # Set-piece explosions land where the picture needs weight.
    for at, pan, level, big in ((11.6, .24, .20, False), (15.4, .74, .30, False), (20.0, .52, .95, True), (23.3, .18, .40, False),
                                (26.7, .80, .58, True), (29.2, .36, .42, False), (31.6, .64, .74, True)):
        place(blast(rng, 5.6 if big else 3.6, big), at, pan, level, .5)
    # Fly-bys: low pressure moving across the stereo field.
    for at, length, left in ((16.2, 3.0, True), (24.6, 2.6, False), (30.0, 2.8, True)):
        size = int(length * RATE)
        when = np.linspace(0, 1, size)
        roar = band(rng.normal(0, 1, size), 40, 620, 2)
        roar = roar / roar.std() * np.sin(math.pi * when) ** 2.4 * .22
        pan = when if left else 1 - when
        begin = int(at * RATE)
        near[0, begin:begin + size] += roar * np.cos(pan * math.pi / 2)
        near[1, begin:begin + size] += roar * np.sin(pan * math.pi / 2)
    # Score: D minor pedal that widens and opens from 6 s, and hits at 20 s.
    cutoff_hold = 780
    pad = voice(n, t, (36.71, 55.0, 73.42, 87.31, 110.0, 146.83), cutoff_hold, (1, .8, .55, .42, .34, .22), 5)
    pad = pad / np.abs(pad).max()
    swell = rise ** 1.15 * (1 + .12 * np.sin(2 * math.pi * .13 * t)) * np.where(t < 20, 1, .62 + .38 * np.exp(-(t - 20) / 2.5))
    swell = band(swell, .001, 6, 1)
    near += pad * swell * .34
    send += pad * swell * .12
    # A slow low riser through the last run at the hangar.
    run = np.clip((t - 29.5) / (INSIDE - 29.5), 0, 1) ** 2.2 * (t < INSIDE + .02)
    riser = band(rng.normal(0, 1, n), 35, 300 + 0 * t[0], 2)
    near += riser / riser.std() * run * .10
    # Hall: dark stereo reverberation, decorrelated between ears.
    size = int(3.2 * RATE)
    tail = np.arange(size) / RATE
    for channel in (0, 1):
        room = band(rng.normal(0, 1, size), 40, 1300, 2) * np.exp(-tail * 2.3)
        room[:int(.03 * RATE)] = 0
        pad_len = n + size
        wet = np.fft.irfft(np.fft.rfft(send[channel], pad_len) * np.fft.rfft(room, pad_len), pad_len)[:n]
        near[channel] += wet / np.sqrt((room ** 2).sum()) * .55
    # Through the hull: the whole battle drops away at the door, and the door itself lands.
    inside = smooth(INSIDE - .05, INSIDE + .45, t)
    for channel in (0, 1):
        dull = band(near[channel], 18, 240, 3)
        near[channel] = near[channel] * (1 - inside) + dull * inside * 1.15
    length = int(4 * RATE)
    when = np.arange(length) / RATE
    door = sum(np.sin(2 * math.pi * f * when + p) * a * np.exp(-when * d) for f, a, d, p in
               ((41, 1, 2.0, 0), (86, .55, 2.6, 1), (143, .3, 3.4, 2), (211, .2, 4.4, 3), (317, .10, 6, 1), (461, .05, 8, 2)))
    door *= 1 - np.exp(-when * 300)
    begin = int(INSIDE * RATE)
    size = min(length, n - begin)
    near[0, begin:begin + size] += door[:size] * .50
    near[1, begin:begin + size] += door[:size] * .46
    hum = band(rng.normal(0, 1, n), 40, 120, 2)
    hum = hum / hum.std() + .5 * np.sin(2 * math.pi * 50 * t) + .25 * np.sin(2 * math.pi * 100.3 * t)
    near += hum * smooth(INSIDE + .1, 36.5, t) * .055
    # The klaxon stays low and round: two sine-rich tones, well clear of the shrill band.
    pitch = np.where(np.mod(t - 34.4, 1.6) < .8, 174.6, 130.8)
    phase = 2 * math.pi * np.cumsum(pitch) / RATE
    horn = np.sin(phase) + .4 * np.sin(2 * phase) + .16 * np.sin(3 * phase)
    gate = smooth(0, .05, np.mod(t - 34.4, .8)) * smooth(.8, .72, np.mod(t - 34.4, .8)) * (t > 34.4)
    near += horn * gate * .055
    # Nothing shrill survives: a soft shelf from 1.8 kHz and a wall by 3.4 kHz.
    for channel in (0, 1):
        pad_len = n + RATE
        spectrum = np.fft.rfft(near[channel], pad_len)
        freq = np.fft.rfftfreq(pad_len, 1 / RATE) + 1e-3
        gain = 1 / np.sqrt(1 + (freq / 3000) ** 8) / np.sqrt(1 + (22 / freq) ** 6) * (.5 + .5 / (1 + (freq / 1800) ** 2))
        near[channel] = np.fft.irfft(spectrum * gain, pad_len)[:n]
    # Absolute silence before 6 s; the mix then rises, and tails out by 42 s.
    gate = smooth(6.0, 6.05, t) * np.clip((SECONDS - t) / 2.6, 0, 1)
    near *= gate
    near = near / np.abs(near).max() * 1.15
    stereo = np.tanh(near) / np.tanh(1.15) * .89
    stereo[:, t < 6.0] = 0
    report_audio('v1', keep)
    new = AUDIO / 'S_Opening.wav'
    with wave.open(str(new), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((stereo.T * 32767).astype(np.int16).tobytes())
    report_audio('v2', new)


def report_audio(name, path):
    with wave.open(str(path), 'rb') as source:
        data = np.frombuffer(source.readframes(source.getnframes()), np.int16).reshape(-1, 2).astype(F) / 32768
    mono = data.mean(1)
    edge = [0, 3, 6, 10, 14, 20, 27, 33, 34.5, 38, 42]
    levels = []
    for a, b in zip(edge, edge[1:]):
        part = data[int(a * RATE):int(b * RATE)]
        levels.append(f'{a:g}-{b:g}s {20 * math.log10(max(float(np.sqrt((part ** 2).mean())), 1e-6)):.1f}')
    freq = np.fft.rfftfreq(len(mono), 1 / RATE)
    power = np.abs(np.fft.rfft(mono)) ** 2
    share = {f'{a}-{b}': 100 * power[(freq >= a) & (freq < b)].sum() / power.sum() for a, b in ((0, 60), (60, 250), (250, 1000), (1000, 2500), (2500, 22050))}
    centre = (power * freq).sum() / power.sum()
    side = data[:, 0] - data[:, 1]
    width = float(np.sqrt((side ** 2).mean()) / np.sqrt(((data[:, 0] + data[:, 1]) ** 2).mean()))
    print(f'{name}: {len(mono) / RATE:.3f}s peak {np.abs(data).max():.3f} rms dB {levels}', flush=True)
    print(f'{name}: centroid {centre:.0f} Hz, band % {({k: round(v, 2) for k, v in share.items()})}, side/mid {width:.2f}', flush=True)


# ---------------------------------------------------------------- review sheet

def pano(sky, d):
    h, w = sky.shape[:2]
    u = np.arctan2(d[..., 1], d[..., 0]) / (2 * math.pi) + .5
    v = .5 - np.arcsin(np.clip(d[..., 2], -1, 1)) / math.pi
    fx, fy = u * w - .5, np.clip(v * h - .5, 0, h - 1.001)
    ix, iy = np.floor(fx).astype(int), fy.astype(int)
    wx, wy = (fx - ix)[..., None], (fy - iy)[..., None]
    a, b = np.mod(ix, w), np.mod(ix + 1, w)
    return ((sky[iy, a] * (1 - wx) + sky[iy, b] * wx) * (1 - wy) + (sky[iy + 1, a] * (1 - wx) + sky[iy + 1, b] * wx) * wy)


def camera(sky, look, fov, w, h):
    # Pinhole view exactly as the game sees it, with the same mapping as M_Space.
    look = np.array(look, F)
    look /= np.linalg.norm(look)
    up = np.array((0, 0, 1), F) if abs(look[2]) < .95 else np.array((1, 0, 0), F)
    right = np.cross(look, up)
    right /= np.linalg.norm(right)
    up = np.cross(right, look)
    span = math.tan(math.radians(fov) / 2)
    y, x = np.mgrid[0:h, 0:w].astype(F)
    x = ((x + .5) / w * 2 - 1) * span
    y = (1 - (y + .5) / h * 2) * span * h / w
    d = look + x[..., None] * right + y[..., None] * up
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return pano(sky, d)


def paint_label(image, text, x, y):
    # Blocky labels without an image library.
    glyph = {c: i for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -./')}
    font = FONT
    for i, c in enumerate(text.upper()):
        bits = font[glyph.get(c, 36)]
        for row, line in enumerate(bits):
            for col in range(5):
                if line >> (4 - col) & 1:
                    image[y + row * 2:y + row * 2 + 2, x + (i * 6 + col) * 2:x + (i * 6 + col) * 2 + 2] = .9


FONT = [(14, 17, 31, 17, 17), (30, 17, 30, 17, 30), (15, 16, 16, 16, 15), (30, 17, 17, 17, 30), (31, 16, 30, 16, 31), (31, 16, 30, 16, 16),
        (15, 16, 19, 17, 15), (17, 17, 31, 17, 17), (14, 4, 4, 4, 14), (7, 2, 2, 18, 12), (17, 18, 28, 18, 17), (16, 16, 16, 16, 31),
        (17, 27, 21, 17, 17), (17, 25, 21, 19, 17), (14, 17, 17, 17, 14), (30, 17, 30, 16, 16), (14, 17, 21, 18, 13), (30, 17, 30, 18, 17),
        (15, 16, 14, 1, 30), (31, 4, 4, 4, 4), (17, 17, 17, 17, 14), (17, 17, 17, 10, 4), (17, 17, 21, 27, 17), (17, 10, 4, 10, 17),
        (17, 10, 4, 4, 4), (31, 2, 4, 8, 31), (14, 19, 21, 25, 14), (4, 12, 4, 4, 14), (14, 1, 6, 8, 31), (30, 1, 14, 1, 30),
        (9, 9, 15, 1, 1), (31, 16, 30, 1, 30), (14, 16, 30, 17, 14), (31, 1, 2, 4, 4), (14, 17, 14, 17, 14), (14, 17, 15, 1, 14),
        (0, 0, 0, 0, 0), (0, 0, 14, 0, 0), (0, 0, 0, 0, 4), (1, 2, 4, 8, 16)]


def cycles_tile(sky_path, w, h):
    # A lit test: chrome and rough spheres under three-point lights, with the sky as environment.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 48
    scene.render.resolution_x, scene.render.resolution_y = w, h
    world = bpy.data.worlds.new('World')
    world.use_nodes = True
    scene.world = world
    nodes = world.node_tree.nodes
    env = nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(sky_path))
    env.image.colorspace_settings.name = 'Linear Rec.709'
    world.node_tree.links.new(env.outputs[0], nodes['Background'].inputs[0])
    nodes['Background'].inputs[1].default_value = 1.0
    material = bpy.data.materials.new('Hull')
    material.use_nodes = True
    shader = material.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = (.7, .68, .64, 1)
    shader.inputs['Metallic'].default_value = 1
    shader.inputs['Roughness'].default_value = .16
    for x in (-1.2, 1.2):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=1, location=(x, 0, 0))
        bpy.ops.object.shade_smooth()
        bpy.context.object.data.materials.append(material.copy() if x > 0 else material)
    bpy.context.object.active_material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .45
    for name, at, power, colour in (('Key', (-4, -4, 3), 240, (1, .86, .62)), ('Fill', (5, -3, 0), 40, (.45, .62, 1)), ('Rim', (1, 5, 3), 300, (.7, .85, 1))):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.color, data.size = power, colour, 3
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = at
        light.rotation_euler = (Vectorish(at))
    data = bpy.data.cameras.new('Cam')
    data.lens = 50
    cam = bpy.data.objects.new('Cam', data)
    scene.collection.objects.link(cam)
    cam.location = (0, -7.4, .6)
    cam.rotation_euler = (math.radians(85.4), 0, 0)
    scene.camera = cam
    scene.view_settings.view_transform = 'Standard'
    scene.render.image_settings.file_format = 'PNG'
    path = ROOT / 'Saved/FXPreview/cycles_tile.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return load(path)[..., :3]


def Vectorish(at):
    from mathutils import Vector
    return (-Vector(at)).to_track_quat('-Z', 'Y').to_euler()


def build_review():
    pick = lambda rel: OUT / rel if (OUT / rel).exists() else ROOT / 'Art' / rel
    name = 'space_fx_preview' if PREVIEW else 'space_fx'
    w = 2520
    rows = []

    def strip(tiles):
        height = tiles[0][0].shape[0]
        out = np.zeros((height, w, 3), F)
        x = 0
        for image, label in tiles:
            part = np.clip(image[..., :3], 0, 1)[:height, :max(w - x, 0)]
            out[:part.shape[0], x:x + part.shape[1]] = part
            paint_label(out, label, x + 8, 8)
            x += part.shape[1] + 6
        rows.append(out)

    sky = load(pick('Sky/T_Sky_Space_8K.png'))[..., :3]
    print('sky loaded', sky.shape, flush=True)
    full = area(sky, 1260 * sky.shape[0] // sky.shape[1], 1260)
    # What the game shows, in display space. M_Space multiplies by 1.7 in linear.
    view = lambda d, fov, a, b: srgb(linear(camera(sky, d, fov, a, b)))
    strip([(full, 'panorama 2 to 1'), (view(direction(.25, .44), 70, 1254, 630), 'game camera 70 fov core')])
    strip([(view(direction(.64, .36), 80, 836, 470), '80 fov hero nebula'), (view(direction(.905, .30), 80, 836, 470), '80 fov violet veil'),
           (view((0, 0, 1), 110, 836, 470), 'zenith pole')])
    # 1:1 crops: this is the honest test of star shape and grain.
    h, w0 = sky.shape[:2]
    cx, cy = int(.25 * w0), int(.44 * h)
    crop = sky[cy - 235:cy + 235, cx - 418:cx + 418]
    cx2, cy2 = int(.64 * w0), int(.36 * h)
    crop2 = sky[cy2 - 235:cy2 + 235, cx2 - 418:cx2 + 418]
    gain = sky[int(.8 * h) - 235:int(.8 * h) + 235, int(.1 * w0):int(.1 * w0) + 836]
    strip([(crop, '1 to 1 core'), (crop2, '1 to 1 nebula'), (np.clip(gain * 4, 0, 1), 'dark sky x4 banding check')])
    del full
    plate = load(pick('Sky/T_Sky_Planet_4K.png'))
    size = plate.shape[0]
    card = 840
    small = area(plate, card, card)
    backdrop = camera(sky, direction(.05, .55), 60, card, card)
    premult = linear(small[..., :3]) + linear(backdrop) * (1 - small[..., 3:])
    limb = plate[int(size * .35):int(size * .35) + 840 * size // 4096, int(size * .28):int(size * .28) + 840 * size // 4096]
    if limb.shape[0] != 840:
        limb = np.kron(limb, np.ones((840 // limb.shape[0] + 1, 840 // limb.shape[0] + 1, 1), F))[:840, :840]
    moon_crop = plate[:840 * size // 4096, :840 * size // 4096, :3]
    if moon_crop.shape[0] != 840:
        moon_crop = np.kron(moon_crop, np.ones((840 // moon_crop.shape[0] + 1, 840 // moon_crop.shape[0] + 1, 1), F))[:840, :840]
    strip([(srgb(premult), 'planet card over sky'), (limb[..., :3], '1 to 1 limb'), (moon_crop, '1 to 1 moon')])
    del plate, small
    base, emit = load(pick('FX/T_FX_Fireball_BaseColor.png')), load(pick('FX/T_FX_Fireball_Emissive.png'))
    def over(c, a, e, back):
        return srgb(linear(c) * a + linear(back) * (1 - a) + e * .6)
    size = base.shape[0]
    composite = over(base[..., :3], base[..., 3:], linear(emit[..., :3]) * 3.3, np.full((size, size, 3), .02, F))
    tile = size // 8
    picks = [2, 7, 14, 24, 40, 55]
    big = [composite[(i // 8) * tile:(i // 8 + 1) * tile, (i % 8) * tile:(i % 8 + 1) * tile] for i in picks]
    big = [np.kron(b, np.ones((2 * 256 // tile, 2 * 256 // tile, 1), F)) for b in big]
    strip([(area(composite, 1260, 1260), 'fireball sheet base plus emissive'),
           (np.concatenate((np.concatenate(big[:3], 1), np.concatenate(big[3:], 1)), 0)[:1260, :1254], 'frames 2 7 14 24 40 55')])
    smoke = load(pick('FX/T_FX_SmokePuff_BaseColor.png'))
    field = np.full((*smoke.shape[:2], 3), .035, F)
    smoke_view = srgb(linear(smoke[..., :3]) * smoke[..., 3:] * .9 + linear(field) * (1 - smoke[..., 3:]))
    sparks = load(pick('FX/T_FX_Sparks.png'))
    laser = load(pick('FX/T_FX_LaserBolt.png'))
    glow = load(pick('FX/T_FX_EngineGlow.png'))
    tint = lambda m, c: m[..., 0:1] * 4 + m[..., 1:2] * np.array(c, F) * 1.6 + m[..., 2:3] * np.array(c, F) * .5
    bolts = np.concatenate([area(srgb(1 - np.exp(-tint(laser, c))), 150, 1254) for c in ((1.0, .32, .10), (.12, .55, 1.0), (1.0, .72, .18))], 0)
    glows = np.concatenate([area(srgb(1 - np.exp(-(glow[..., 0:1] * 3 + glow[..., 1:2] * np.array(c, F) * 1.6 + glow[..., 2:3] * np.array(c, F) * .7))), 420, 420) for c in ((.2, .5, 1), (1, .6, .2), (.3, .9, .9))], 1)
    spark_view = area(sparks[..., :3] * sparks[..., 3:], 420, 420)
    right = np.concatenate((bolts[:450], np.concatenate((glows[:, :834], spark_view), 1)[:420, :1254], np.zeros((390, 1254, 3), F)), 0)
    strip([(area(smoke_view, 1260, 1260), 'smoke sheet'), (right, 'laser tints   engine glow tints   sparks')])
    tile_image = cycles_tile(pick('Sky/T_Sky_Space_8K.exr'), 1250, 500)
    strip([(tile_image, 'cycles three point test under sky env')])
    sheet = np.concatenate(rows, 0)
    png(REVIEW / f'{name}.png', sheet, 8)


def build_ad():
    """Art-director views: game resolution, recommended material settings, and the mip test."""
    pick = lambda rel: OUT / rel if (OUT / rel).exists() else ROOT / 'Art' / rel
    sky = load(pick('Sky/T_Sky_Space_8K.png'))[..., :3]
    rows = []
    w, h = 1250, 700

    def row(*tiles):
        rows.append(np.concatenate(tiles, 1))

    def tag(image, label):
        image = np.clip(image[..., :3], 0, 1).copy()
        paint_label(image, label, 8, 8)
        return image

    row(tag(camera(sky, direction(.25, .44), 45, w, h), '45 fov lens on the core'), tag(camera(sky, direction(.42, .62), 45, w, h), '45 fov empty sky'))
    row(tag(camera(sky, direction(.12, .46), 30, w, h), '30 fov disc band'), tag(camera(sky, direction(.60, .34), 30, w, h), '30 fov hero nebula'))
    plate = load(pick('Sky/T_Sky_Planet_4K.png'))
    size = plate.shape[0]
    scale = size / 4096
    a = int(1000 * scale)
    terminator = plate[int(1500 * scale):int(1500 * scale) + a, int(1500 * scale):int(1500 * scale) + a]
    moon_part = plate[int(160 * scale):int(960 * scale), int(160 * scale):int(960 * scale)]
    limb = plate[int(500 * scale):int(500 * scale) + a, int(1000 * scale):int(1000 * scale) + a]
    fit = lambda image: area(image[..., :3], h, h)
    filler = np.zeros((h, 2 * w - 3 * h, 3), F) if 2 * w > 3 * h else None
    tiles = [tag(fit(limb), 'lit limb 1 to 1'), tag(fit(terminator), 'terminator 1 to 1'), tag(fit(moon_part), 'moon')]
    row(*(tiles + ([filler] if filler is not None else [])))
    base, emit = load(pick('FX/T_FX_Fireball_BaseColor.png')), load(pick('FX/T_FX_Fireball_Emissive.png'))
    size = base.shape[0]
    tile = size // 8
    frames = [1, 4, 8, 13, 18, 24, 32, 44, 54, 60]
    side = (2 * w) // 5
    strip_a, strip_b = [], []
    for at, i in enumerate(frames):
        y0, x0 = (i // 8) * tile, (i % 8) * tile
        c, e = base[y0:y0 + tile, x0:x0 + tile], emit[y0:y0 + tile, x0:x0 + tile]
        back = np.array((.012, .016, .03), F)
        lit = linear(c[..., :3]) * .35 * c[..., 3:] + back * (1 - c[..., 3:]) + linear(e[..., :3]) * 2
        out = area(srgb(1 - np.exp(-lit)), side, side)
        (strip_a if at < 5 else strip_b).append(tag(out, f'fire {i} emissive x2'))
    row(*strip_a)
    row(*strip_b)
    smoke = load(pick('FX/T_FX_SmokePuff_BaseColor.png'))
    size = smoke.shape[0]
    tile = size // 6
    picks, strip_c = [3, 10, 16, 24, 31], []
    for i in picks:
        y0, x0 = (i // 6) * tile, (i % 6) * tile
        c = smoke[y0:y0 + tile, x0:x0 + tile]
        lit = linear(c[..., :3]) * c[..., 3:] + np.array((.012, .016, .03), F) * (1 - c[..., 3:])
        strip_c.append(tag(area(srgb(lit), side, side), f'smoke {i}'))
    row(*strip_c)
    # Mip fringe: filter straight alpha colour as a GPU does, and composite over a bright sky.
    y0, x0 = 3 * (base.shape[0] // 8), 3 * (base.shape[0] // 8)
    t = base.shape[0] // 8
    c = base[y0:y0 + t, x0:x0 + t]
    tiny = area(c, t // 8, t // 8)
    bright = np.array((.55, .6, .7), F)
    mip = np.kron(linear(tiny[..., :3]) * tiny[..., 3:] + bright * (1 - tiny[..., 3:]), np.ones((8 * side // t, 8 * side // t, 1), F))
    sparks = load(pick('FX/T_FX_Sparks.png'))
    laser = load(pick('FX/T_FX_LaserBolt.png'))
    glow = load(pick('FX/T_FX_EngineGlow.png'))
    sv = area(sparks[..., :3] * sparks[..., 3:], side, side)
    gv = area(srgb(1 - np.exp(-(glow[..., 0:1] * 3 + glow[..., 1:2] * np.array((.2, .5, 1), F) * 1.6 + glow[..., 2:3] * np.array((.2, .5, 1), F) * .7))), side, side)
    lv = area(srgb(1 - np.exp(-(laser[..., 0:1] * 4 + laser[..., 1:2] * np.array((1, .32, .1), F) * 1.6 + laser[..., 2:3] * np.array((1, .32, .1), F) * .5))), side // 4, side)
    lv = np.concatenate((lv, np.zeros((side - lv.shape[0], side, 3), F)), 0)
    row(tag(srgb(area(mip, side, side)), 'fire mip 3 over bright sky'), tag(sv, 'sparks'), tag(gv, 'glow'), tag(lv, 'laser'), np.zeros((side, 2 * w - 4 * side, 3), F))
    width = 2 * w
    rows[:] = [r if r.shape[1] == width else np.concatenate((r, np.zeros((r.shape[0], width - r.shape[1], 3), F)), 1) for r in rows]
    png(REVIEW / ('space_fx_ad_preview.png' if PREVIEW else 'space_fx_ad.png'), np.concatenate(rows, 0), 8)


stage = {'sky': build_sky, 'planet': build_planet, 'fire': build_fire, 'smoke': build_smoke, 'sprites': build_sprites,
         'audio': build_audio, 'review': build_review, 'ad': build_ad}
for name in STAGES:
    begin = time.time()
    SKY.mkdir(parents=True, exist_ok=True)
    FX.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    stage[name]()
    print(f'== {name} {time.time() - begin:.0f}s', flush=True)
print('PHYSIS_FX_DONE')
