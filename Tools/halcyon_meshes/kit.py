"""Mesh kit for level 6, Halcyon, the Drowned Harbour, on Earth (Tools/halcyon/README.md is the contract).

Halcyon's generators (Tools/halcyon_meshes/*.py) are pure numpy and build on the Grove's kit, which builds on the
Conclave's toolkit (Part and the primitives) and its helpers (al_flora as fl). Import everything from here:

    from kit import *      # Part, the toolkit primitives, fl, np, math, the slots, Halcyon's palette, the helpers

Conventions are the Grove's: metres; x forward (a mesh with a front faces +x), y right, z up; faces wound
counter-clockwise seen from outside; what stands on the ground has its lowest point at z 0 and its footprint centred
on the origin (finish()); what hovers or is picked up is centred on the origin (centre()). Vertex colour is the albedo
(linear RGB, at most 0.9; glow slots carry the light's colour) and the slot decides the surface.

Slots on Halcyon (the same slot names as every level; Content/Python/physis_halcyon_tools.py maps each to a look):
  STONE 'CN_White'    limestone and lime render: houses, quays, the sea wall, the clocktower
  ROCK 'CN_Black'     grey rock and the Just's poured concrete (the Bastion)
  ALLOY 'CN_Metal'    weathered steel: cranes, rails, lamp posts, the Tide Guard's frames
  ENAMEL 'CN_Lacquer' painted wood and steel: doors, shutters, boats, the Just's olive paint
  ELECTRUM 'CN_Gold'  brass: the clock's hands, ship fittings
  RED 'CN_Red'        red paint (buoys, a lifebelt)          TILE 'CN_Blue'  slate roofs
  CLOTH 'CN_Cloth'    canvas, nets, rope                     LICHEN 'CN_Plaster'  wrack, weed and lichen
  WOOD 'CN_Bark'      old timber: piers, boats, beams        GLOW 'CN_Glow'  light (vertex colour)
  CRYSTAL 'CN_Glass'  window glass                           GROUND, WATER   terrain and sea only

The look (author, 2026-11-18): realistic, neutral. Overcast marine light, grey-white limestone, slate, weathered
steel, a grey-green sea. Three lights: the Just's machines amber, forced Divinity (the Held Sea) magenta, Trace
Reading's past pale silver.
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
# Everything the Grove's kit offers (toolkit primitives, fl, np, math, helpers), then Halcyon's own folder first on the
# path so `import check` and `import land` find Halcyon's.
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

# ---------------------------------------------------------------- Halcyon's palette (linear RGB)
LIME = col(.560, .550, .520)            # limestone in light: the reference colour of the STONE slot
LIME_SHADE = col(.300, .295, .280)
LIME_WORN = col(.430, .420, .400)
RENDER = col(.620, .610, .580)          # lime render on the houses, a little paler
RENDER_GREY = col(.420, .420, .410)
SOOT = col(.090, .088, .085)
CONCRETE_JUST = col(.300, .300, .290)   # the Bastion's poured concrete
CONCRETE_WET = col(.150, .150, .145)
ROCK_GREY = col(.180, .180, .175)       # the coast's rock
SLATE = col(.060, .065, .075)           # the reference colour of the TILE slot
SLATE_PALE = col(.120, .125, .135)
STEEL_W = col(.200, .200, .200)         # weathered steel
RUST_W = col(.220, .090, .040)
PAINT_GREEN = col(.050, .110, .080)     # doors and shutters
PAINT_BLUE = col(.040, .080, .150)
PAINT_WHITE = col(.650, .650, .630)
PAINT_OLIVE = col(.110, .120, .060)     # the Just's olive
PAINT_RED = col(.450, .040, .030)
BRASS_DULL = col(.500, .380, .160)
TIMBER = col(.180, .140, .100)
TIMBER_GREY = col(.250, .240, .220)     # sea-bleached timber
WRACK = col(.090, .085, .040)           # kelp and wrack on everything the tide reached
WEED_GREEN = col(.080, .120, .050)
CANVAS_W = col(.420, .400, .350)
GLASS_SEA = col(.300, .360, .380)
SAND_W = col(.420, .390, .330)
# Lights (GLOW slot): the Just's machines, forced Divinity, the past, a lamp.
GLOW_JUST = col(1.0, .550, .120)
GLOW_FORCED = col(1.0, .120, .700)
GLOW_PAST = col(.820, .860, .920)
GLOW_LAMP = col(1.0, .800, .500)
