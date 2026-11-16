"""Mesh kit for level 5, Arche, the First Ones' Planet (Tools/arche/README.md is the contract).

Arche's generators (Tools/arche_meshes/*.py) are pure numpy and build on the Grove's kit, which builds on the
Conclave's toolkit (Part and the primitives) and its helpers (al_flora as fl). Import everything from here:

    from kit import *      # Part, the toolkit primitives, fl, np, math, the slots, Arche's palette, the helpers

Conventions are the Grove's (Tools/grove_meshes/kit.py): metres; x forward (a mesh with a front faces +x), y right,
z up; faces wound counter-clockwise seen from outside; what stands on the ground has its lowest point at z 0 and its
footprint centred on the origin (finish()); what hovers or is picked up is centred on the origin (centre()). Vertex
colour is the albedo (linear RGB, at most 0.9; glow slots carry the light's colour) and the slot decides the surface.
Every declared slot must be used by a face.

Slots on Arche (the same slot names as every level; Content/Python/physis_arche_tools.py maps each to a look):
  STONE 'CN_White'    pale dressed stone: the First Ones' masonry, terraces, stairs, columns (a scanned stone, cool)
  ROCK 'CN_Black'     dark living rock, basalt, the raw canyon
  ALLOY 'CN_Metal'    the First Ones' silver alloy: fittings, frames, the Lens's ring
  ENAMEL 'CN_Lacquer' enamelled plate: the AL's shells, inlay bands
  ELECTRUM 'CN_Gold'  pale gold metal: inlay lines, the Serene's ornaments, mirror backs
  RED 'CN_Red'        the AL's red (matte)
  TILE 'CN_Blue'      deep glazed ceramic: cistern linings, roof tiles
  CLOTH 'CN_Cloth'    robes, banners, cord
  LICHEN 'CN_Plaster' lichen, frost-moss, dust drifts
  GLOW 'CN_Glow'      light: the vertex colour is the light's colour (use the GLOW_* colours)
  CRYSTAL 'CN_Glass'  crystal and glass (translucent)
  GROUND 'CN_Ground'  terrain only        WATER 'CN_Water'  water only

The look (author, 2026-11-16): realistic, in a cool palette. Pale stone, dark rock, silver, ice-blue and violet
crystal with luminous edges, under a cold sun. Three lights tell three things apart: the Serene's light is a pale
ice blue, the Vigil's works (the Lens, the veils, the unweaving) glow a cold violet, and Reweave, a thing
remembering its shape, glows a warm pearl gold. The AL keep their red. No warm browns or greens except lichen.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_GROVE = str(ROOT / 'Tools/grove_meshes')
if _GROVE not in sys.path:
    sys.path.insert(0, _GROVE)
import importlib.util as _util  # noqa: E402

_spec = _util.spec_from_file_location('physis_grove_kit', ROOT / 'Tools/grove_meshes/kit.py')
_grove = _util.module_from_spec(_spec)
_spec.loader.exec_module(_grove)
# Everything the Grove's kit offers (toolkit primitives, fl, np, math, helpers), then Arche's own folder first on the
# path so `import check` and `import land` find Arche's.
globals().update({k: v for k, v in vars(_grove).items() if not k.startswith('_') and k not in ('HERE', 'ROOT')})
for _path in (_GROVE, str(HERE)):
    if _path in sys.path:
        sys.path.remove(_path)
sys.path.insert(0, _GROVE)
sys.path.insert(0, str(HERE))

col = _grove.col
STONE, ROCK, ALLOY, ENAMEL, ELECTRUM, RED, TILE, CLOTH, LICHEN, GLOW, CRYSTAL, GROUND, WATER = (
    'CN_White', 'CN_Black', 'CN_Metal', 'CN_Lacquer', 'CN_Gold', 'CN_Red', 'CN_Blue', 'CN_Cloth', 'CN_Plaster', 'CN_Glow', 'CN_Glass',
    'CN_Ground', 'CN_Water')

# ---------------------------------------------------------------- Arche's palette (linear RGB)
STONE_PALE = col(.560, .580, .610)      # dressed stone in light: the reference colour of the STONE slot
STONE_SHADE = col(.300, .320, .360)     # the same stone in crevices and low courses
STONE_WORN = col(.420, .430, .440)      # trodden treads, weathered tops
STONE_DARK = col(.130, .140, .165)      # old courses, soot of the unweaving
ROCK_BLUE = col(.110, .120, .145)       # the canyon's living rock: the reference colour of the ROCK slot
ROCK_DEEP = col(.045, .050, .065)
ROCK_PALE = col(.240, .250, .270)
DUST = col(.470, .470, .460)            # pale dust and scree
ALLOY_SILVER = col(.560, .580, .600)    # the reference colour of the ALLOY slot
ALLOY_DARK = col(.120, .130, .150)
ELECTRUM_PALE = col(.820, .740, .480)
ENAMEL_WHITE = col(.700, .700, .690)    # AL shells and inlay
ENAMEL_NIGHT = col(.030, .034, .050)    # near-black blue enamel
TILE_DEEP = col(.030, .070, .190)       # deep blue glaze
TILE_TEAL = col(.040, .200, .230)
CLOTH_PEARL = col(.620, .620, .640)     # the Serene's robes
CLOTH_INDIGO = col(.050, .060, .180)
CLOTH_VIOLET = col(.200, .100, .320)    # the Vigil's colours
LICHEN_FROST = col(.380, .470, .430)    # pale grey-green lichen
LICHEN_DEEP = col(.100, .160, .150)
CRYSTAL_ICE = col(.550, .780, .900)     # crystal bodies (translucent slot): ice blue
CRYSTAL_VIOLET = col(.520, .420, .880)
CRYSTAL_CLEAR = col(.800, .860, .900)
AL_RED = col(.560, .040, .030)
# Lights (GLOW slot): the Serene, the Vigil, Reweave, the AL.
GLOW_SERENE = col(.550, .850, 1.0)
GLOW_VIGIL = col(.620, .380, 1.0)
GLOW_WEAVE = col(1.0, .880, .620)
GLOW_AL = col(1.0, .120, .080)
GLOW_WHITE = col(1.0, 1.0, 1.0)
