"""Mesh kit for level 4, Earth: the Wounded Grove (Tools/grove/README.md is the contract).

The grove's generators (Tools/grove_meshes/*.py) are pure numpy, like the Conclave's, and build on the Conclave's
toolkit (Tools/conclave_meshes/toolkit.py: Part and the primitives) and on its plant and machine helpers
(al_flora.py: limb, cards, leaf_cards, grow, wood, twig_crown, rock ...). This module puts both on the path, lifts the
Conclave's six-colour rule (Earth has natural colours), names the surfaces and the Earth palette, and holds the
grove's own finishing helpers. Import everything from here:

    from kit import *          # Part, toolkit primitives, fl (al_flora), np, math, slots, colours, helpers

Conventions (the same as the Conclave's):
  - Metres. x forward (a mesh with a front faces +x), y right, z up. Faces wind counter-clockwise seen from outside.
  - Things that stand on the ground have their lowest point at z 0 and their footprint centred on the origin
    (finish()). Things that hover or are picked up are centred on the origin (finish(part, ground=False) after
    centring them yourself, or centre()).
  - Vertex colour is the albedo (linear RGB, at most 0.9); the slot decides the surface. Every declared slot must be
    used by a face. Colours come from this module's palette (or mixes and shades of it), so the level keeps one look:
    warm, soft, painterly Earth.
  - Shade with vertex colour: darker toward the ground and in crevices, lighter on tops and edges (ao(), grime()).

Slots (the Conclave's slot names, each mapped to a grove look by Content/Python/physis_grove_tools.py):
  LEAF 'CN_Leaf'      foliage: two-sided, masked atlas cards (vertex alpha 0) and solid leaves (alpha 1); never collides
  BARK 'CN_Bark'      bark, roots, woody stems, thornroot
  CONCRETE 'CN_White' concrete, pale dressed stone
  ROCK 'CN_Black'     rock, boulders, asphalt, dark stone
  STEEL 'CN_Metal'    weathered steel, galvanised frames
  PAINT 'CN_Lacquer'  painted or enamelled metal and ceramic (machine plates, the Just's livery)
  BRASS 'CN_Gold'     brass, copper, gold-coloured metal
  RUST 'CN_Red'       rusted iron (rough, no shine)
  TILE 'CN_Blue'      glazed tile, solar cells, ceramic insulators
  CLOTH 'CN_Cloth'    tarpaulin, rope, canvas, paper
  MOSS 'CN_Plaster'   moss, lichen, soft earth, thatch
  GLOW 'CN_Glow'      light-emitting surfaces: brightness is the vertex colour (use the GLOW_* colours)
  GLASS 'CN_Glass'    glass (translucent)
  GROUND 'CN_Ground'  terrain only        WATER 'CN_Water'  water only
"""
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# The grove's own folder first: its check.py must win over the Conclave's of the same name.
for _path in (str(ROOT / 'Content/Python'), str(ROOT / 'Tools/conclave_meshes'), str(HERE)):
    if _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)

import toolkit  # noqa: E402
import al_flora as fl  # noqa: E402
from toolkit import (Part, arch, bevel_box, bezier, blob, blur, box, column, cylinder, fbm, frame, gable_roof, hexa, lathe,  # noqa: E402,F401
                     noise2, oriented, prism, quad, ribbon, stairs, torus, tube, window_frame, yawed)

# Earth has every colour: the Conclave's helpers keep a shaded colour inside its palette family, which here would
# stop a brown or an olive from being shaded at all. Any shade is allowed in the grove.
fl.floor_of = lambda colour: 0.0

TAU = 2 * math.pi
UP = np.array([0.0, 0.0, 1.0])

LEAF, BARK, CONCRETE, ROCK, STEEL, PAINT, BRASS, RUST, TILE, CLOTH, MOSS, GLOW, GLASS, GROUND, WATER = (
    'CN_Leaf', 'CN_Bark', 'CN_White', 'CN_Black', 'CN_Metal', 'CN_Lacquer', 'CN_Gold', 'CN_Red', 'CN_Blue', 'CN_Cloth',
    'CN_Plaster', 'CN_Glow', 'CN_Glass', 'CN_Ground', 'CN_Water')


def col(r, g, b, a=1.0):
    return (float(r), float(g), float(b), float(a))


# ---------------------------------------------------------------- the Earth palette (linear RGB)
# Living things: warm greens with yellow in them, never blue-green; autumn touches for the birches and the litter.
LEAF_GREEN = col(.060, .135, .030)      # broadleaf in sun
LEAF_DEEP = col(.022, .058, .016)       # the shaded inside of a crown, conifer needles, ivy
LEAF_LIGHT = col(.150, .260, .055)      # young leaves, backlit crowns, fern tips
LEAF_GOLD = col(.420, .300, .045)       # birch and beech turning
LEAF_RUSSET = col(.300, .110, .030)     # the reddest autumn leaves, bracken
GRASS = col(.095, .170, .045)
GRASS_DRY = col(.300, .260, .100)       # seed heads, late-summer grass
MOSS_GREEN = col(.085, .135, .035)
MOSS_DEEP = col(.035, .060, .020)
BARK_BROWN = col(.095, .065, .042)      # oak, the giants
BARK_GREY = col(.170, .155, .135)       # beech
BARK_DARK = col(.042, .032, .026)       # wet or old bark, pine
BARK_BIRCH = col(.660, .640, .590)
WOOD_PALE = col(.360, .270, .160)       # split wood, sawn planks
WOOD_OLD = col(.150, .120, .090)        # weathered timber
SOIL = col(.070, .050, .034)
SOIL_DARK = col(.030, .022, .016)
SAND = col(.400, .340, .240)
ROCK_GREY = col(.210, .205, .195)
ROCK_WARM = col(.290, .245, .200)
ROCK_DARK = col(.085, .082, .080)
FLOWER_WHITE = col(.860, .840, .780)
FLOWER_YELLOW = col(.850, .600, .060)
FLOWER_VIOLET = col(.300, .140, .550)
FLOWER_PINK = col(.780, .300, .420)
# Made things: forty years of weather on the Just's concrete and steel.
CONCRETE_PALE = col(.430, .420, .395)
CONCRETE_STAIN = col(.240, .235, .215)
CONCRETE_DARK = col(.120, .118, .110)
ASPHALT = col(.050, .050, .054)
ROAD_PAINT = col(.720, .700, .620)
STEEL_GREY = col(.270, .280, .290)
STEEL_DARK = col(.075, .078, .082)
RUST_ORANGE = col(.330, .130, .045)
RUST_DARK = col(.130, .055, .028)
BRASS_WARM = col(.800, .560, .220)
COPPER = col(.720, .330, .180)
VERDIGRIS = col(.180, .420, .340)
TARP_BLUE = col(.090, .200, .330)
TARP_OCHRE = col(.520, .360, .120)
CANVAS = col(.560, .520, .420)
ROPE = col(.380, .300, .180)
GLASS_GREEN = col(.550, .700, .640)     # old glass: a faint bottle green
SOLAR = col(.035, .050, .110)
# The Just's livery (the Hedge, the Array, the people's machines): bone-white plates, graphite frames, a signal
# orange stripe, and amber light. The AL are red and the Lightforms light blue; the Just are amber.
JUST_BONE = col(.640, .610, .540)
JUST_GRAPHITE = col(.045, .047, .052)
JUST_ORANGE = col(.780, .240, .030)
JUST_OLIVE = col(.170, .190, .110)      # field equipment, crates, shelters
GLOW_AMBER = col(1.0, .520, .080)       # the Hedge's lenses and emitters
GLOW_WARM = col(1.0, .800, .500)        # lamps, lit windows
GLOW_WHITE = col(1.0, 1.0, 1.0)
# Resonance: the link's own light, a living green-gold turquoise. Thornroot's is a sick magenta ember.
GLOW_LINK = col(.250, 1.0, .700)
GLOW_FLOW_WATER = col(.300, .800, 1.0)
GLOW_FLOW_POWER = col(1.0, .780, .250)
GLOW_BLIGHT = col(1.0, .100, .380)
THORN = col(.034, .020, .040)           # thornroot: near-black violet
THORN_PALE = col(.110, .060, .120)


def tone(colour, k=1.0):
    """colour times shading k (a number or an array), at most 0.9 albedo: fl.tone without the Conclave's floor."""
    return fl.tone(colour, k)


def mix(a, b, t):
    return fl.mix(a, b, t)


def vary(rng, colour, spread=.12):
    """colour at a random brightness within +-spread (one draw)."""
    return tone(colour, 1.0 + rng.uniform(-spread, spread))


# ---------------------------------------------------------------- finishing

def ao(part, start=0, height=1.5, floor=.55, keep=(GLOW,)):
    """Ambient occlusion by height: vertices added since `start` darken toward z 0, from 1 at `height` m to `floor`
    on the ground. Glow faces keep their brightness."""
    v = np.asarray(part.v[start:], np.float64)
    if len(v):
        fl.shade(part, floor + (1 - floor) * np.clip(v[:, 2] / max(height, 1e-6), 0, 1), start, keep)


def grime(part, start=0, amount=.25, scale=1.3, seed=0, keep=(GLOW,)):
    """Weather: blotchy darkening by 3-D noise of about `scale` m, up to `amount`."""
    v = np.asarray(part.v[start:], np.float64)
    if len(v):
        n = .5 + .5 * noise2(v[:, 0] / scale + v[:, 2] * .37 / scale, v[:, 1] / scale - v[:, 2] * .41 / scale, seed + 3)
        fl.shade(part, 1 - amount * n, start, keep)


def centre(part, z=True):
    """Moves the part so its bounds' centre is the origin (hovering things, items). z False keeps the height."""
    v = np.asarray(part.v, np.float64)
    mid = (v.min(0) + v.max(0)) / 2
    if not z:
        mid[2] = 0.0
    part.v = (v - mid).tolist()
    return part


def finish(part, ground=True, centre_xy=True, normals=True):
    """Stands the part on z 0 with its footprint centred on the origin (as the contract wants for everything that
    stands on the ground), and gives a part with atlas cards its canopy normals (fl.card_normals)."""
    v = np.asarray(part.v, np.float64)
    lo, hi = v.min(0), v.max(0)
    shift = np.array([-(lo[0] + hi[0]) / 2 if centre_xy else 0.0, -(lo[1] + hi[1]) / 2 if centre_xy else 0.0, -lo[2] if ground else 0.0])
    part.v = (v + shift).tolist()
    return fl.card_normals(part) if normals else part


def scale(part, factor, start=0):
    v = np.asarray(part.v[start:], np.float64) * np.asarray(factor, np.float64)
    part.v[start:] = v.tolist()
    return part


def move(part, offset, start=0, yaw=0.0):
    """Turns (degrees about z) then moves every vertex added since start."""
    v = np.asarray(part.v[start:], np.float64)
    if yaw:
        v = yawed(v, yaw)
    part.v[start:] = (v + np.asarray(offset, np.float64)).tolist()
    return part


def merge(part, other, offset=(0, 0, 0), yaw=0.0, factor=1.0):
    """Appends another Part (same slot names, in any order) turned, scaled and moved. Slots are matched by name."""
    index = [part.slots.index(s) for s in other.slots]
    base = len(part.v)
    v = np.asarray(other.v, np.float64) * factor
    if yaw:
        v = yawed(v, yaw)
    part.v.extend((v + np.asarray(offset, np.float64)).tolist())
    part.c.extend(other.c)
    part.uv.extend(other.uv if len(other.uv) == len(other.v) else [None] * len(other.v))
    for f, m, s in zip(other.f, other.m, other.s):
        part.f.append([base + i for i in f])
        part.m.append(index[m])
        part.s.append(s)
    for start, nrm in getattr(other, 'card_normals', []):
        if not hasattr(part, 'card_normals'):
            part.card_normals = []
        n = np.asarray(nrm, np.float64)
        part.card_normals.append((base + start, yawed(n, yaw) if yaw else n))
    return base


def png(path, rgb):
    """Writes an (h, w, 3) uint8 array as a PNG (no imaging library is installed)."""
    h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
