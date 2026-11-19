"""Mesh kit for level 8, Morrow, the Valley Before Morning, on Earth (Tools/morrow/README.md is the contract).

Morrow's generators (Tools/morrow_meshes/*.py) are pure numpy and build on the Grove's kit, which builds on the
Conclave's toolkit (Part and the primitives) and its helpers (al_flora as fl). Import everything from here:

    from kit import *      # Part, the toolkit primitives, fl, np, math, the slots, Morrow's palette, the helpers

Conventions are the Grove's: metres; x forward (a mesh with a front faces +x), y right, z up; faces wound
counter-clockwise seen from outside; what stands on the ground has its lowest point at z 0 and its footprint centred
on the origin (finish()); what hovers or is picked up is centred on the origin (centre()). Vertex colour is the albedo
(linear RGB, at most 0.9; glow slots carry the light's colour) and the slot decides the surface.

Slots on Morrow (the same slot names as every level; Content/Python/physis_morrow_tools.py maps each to a look):
  STONE 'CN_White'    granite and whitewash: houses, the chapel, the mill, the dam's crest wall
  ROCK 'CN_Black'     grey rock and the Just's poured concrete (the Hold, the spillway)
  ALLOY 'CN_Metal'    weathered steel: the Hold's doors, rails, the Frost Guard's frames, the telegraph
  ENAMEL 'CN_Lacquer' painted wood and steel: doors, shutters, the glider's skin, the Just's olive paint
  ELECTRUM 'CN_Gold'  brass: the telegraph key, lamps, the bell
  RED 'CN_Red'        red paint                              TILE 'CN_Blue'  slate roofs
  CLOTH 'CN_Cloth'    wool, canvas, rope; the Stilled        LICHEN 'CN_Plaster'  frost and rime (white, glossy)
  WOOD 'CN_Bark'      old timber: the mill wheel, beams      GLOW 'CN_Glow'  light (vertex colour)
  CRYSTAL 'CN_Glass'  window glass, ice                      GROUND, WATER   terrain and the reservoir only

The look (author, 2026-11-19): realistic, cold dawn. Blue hour before sunrise, mist in the low ground, frost on
everything. Three lights: the Just's machines amber, the Rime (forced Divinity) magenta in white frost, Sit With a
warm ember rose.
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
# Everything the Grove's kit offers (toolkit primitives, fl, np, math, helpers), then Morrow's own folder first on the
# path so `import check` and `import land` find Morrow's.
globals().update({k: v for k, v in vars(_grove).items() if not k.startswith('_') and k not in ('HERE', 'ROOT')})
for _path in (_GROVE, str(HERE)):
    if _path in sys.path:
        sys.path.remove(_path)
sys.path.insert(0, _GROVE)
sys.path.insert(0, str(HERE))

col = _grove.col
STONE, ROCK, ALLOY, ENAMEL, ELECTRUM, RED, TILE, CLOTH, LICHEN, GLOW, CRYSTAL, GROUND, WATER, WOOD = (
    'CN_White', 'CN_Black', 'CN_Metal', 'CN_Lacquer', 'CN_Gold', 'CN_Red', 'CN_Blue', 'CN_Cloth', 'CN_Plaster', 'CN_Glow', 'CN_Glass',
    'CN_Ground', 'CN_Water', 'CN_Bark')

# ---------------------------------------------------------------- Morrow's palette (linear RGB)
GRANITE = col(.300, .305, .310)         # the valley's grey granite: the reference colour of the STONE slot
GRANITE_SHADE = col(.160, .165, .170)
GRANITE_WORN = col(.240, .245, .250)
WHITEWASH = col(.600, .610, .615)       # lime-washed walls
WASH_GREY = col(.400, .410, .415)
SOOT = col(.080, .080, .082)
CONCRETE_JUST = col(.290, .290, .285)   # the Hold's poured concrete
CONCRETE_DARK = col(.140, .140, .140)
ROCK_GREY = col(.160, .165, .170)
SLATE = col(.050, .055, .065)           # the reference colour of the TILE slot
SLATE_PALE = col(.110, .115, .125)
STEEL_W = col(.190, .190, .195)
RUST_W = col(.200, .085, .040)
PAINT_GREEN = col(.040, .090, .070)
PAINT_BLUE = col(.040, .070, .140)
PAINT_WHITE = col(.640, .640, .630)
PAINT_OLIVE = col(.110, .120, .060)     # the Just's olive
PAINT_RED = col(.400, .040, .030)
PAINT_YELLOW = col(.550, .380, .060)    # the glider's wingtips
BRASS_DULL = col(.500, .380, .160)
TIMBER = col(.150, .110, .080)
TIMBER_GREY = col(.230, .220, .210)
FROST = col(.780, .800, .830)           # hoarfrost: the reference colour of the LICHEN slot
FROST_BLUE = col(.600, .680, .780)
ICE = col(.300, .400, .480)
WOOL = col(.300, .260, .220)
WOOL_DARK = col(.120, .110, .100)
CANVAS_W = col(.420, .400, .350)
GLASS_COLD = col(.260, .320, .360)
SNOW = col(.820, .830, .850)
# Lights (GLOW slot): the Just's machines, the Rime, Sit With, a lamp.
GLOW_JUST = col(1.0, .550, .120)
GLOW_RIME = col(1.0, .140, .680)
GLOW_EMBER = col(1.0, .430, .330)
GLOW_LAMP = col(1.0, .780, .500)
