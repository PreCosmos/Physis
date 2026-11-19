"""Mesh kit for level 7, Hesper, the City of One Voice, on Arche (Tools/hesper/README.md is the contract).

Hesper is on Arche, so its generators (Tools/hesper_meshes/*.py) build on Arche's kit (which builds on the Grove's,
over the Conclave's toolkit) and reuse Arche's masonry helpers (Tools/arche_meshes/structures.py: course, gbox, loft,
column12, weather...). Import everything from here:

    from kit import *      # Part, the toolkit primitives, fl, np, math, the slots, Arche's palette and Hesper's

Conventions are Arche's: metres; x forward (a mesh with a front faces +x), y right, z up; faces wound counter-clockwise
seen from outside; what stands on the ground has its lowest point at z 0 and its footprint centred on the origin; what
hovers is centred on the origin. Vertex colour is the albedo (linear RGB, at most 0.9; glow slots carry the light's
colour) and the slot decides the surface. Every declared slot must be used by a face.

The slots are Arche's (Content/Python/physis_hesper_tools.py maps each to Hesper's warm grading of Arche's look).

The look (author, 2026-11-18): realistic, a warm dusk. The sun sits on the western horizon: the First Ones' pale
stone takes it as honey and rose, the rock is red-brown and violet, shadows are long and violet. Four lights: Unison
(the Concord's tone) amber gold, the Serene's lamps ice blue, the Vigil's works violet, Dissonance a clear blue-white.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
_ARCHE = str(ROOT / 'Tools/arche_meshes')
import importlib.util as _util  # noqa: E402

_spec = _util.spec_from_file_location('physis_arche_kit', ROOT / 'Tools/arche_meshes/kit.py')
_arche = _util.module_from_spec(_spec)
_spec.loader.exec_module(_arche)
globals().update({k: v for k, v in vars(_arche).items() if not k.startswith('_') and k not in ('HERE', 'ROOT')})
# Arche's kit put its own folder first on the path: Hesper's goes in front of it so `import land` finds Hesper's.
for _path in (_ARCHE, str(HERE)):
    while _path in sys.path:
        sys.path.remove(_path)
sys.path.insert(0, str(HERE))

col = _arche.col

# ---------------------------------------------------------------- Hesper's palette (linear RGB)
STONE_HONEY = col(.600, .520, .420)     # the First Ones' pale stone in the dusk: the reference colour of the STONE slot
STONE_ROSE = col(.560, .440, .400)
STONE_DUSK = col(.330, .270, .240)      # in shadow and low courses
ROCK_RED = col(.180, .095, .075)        # the plateau's rock: the reference colour of the ROCK slot
ROCK_PLUM = col(.110, .070, .090)
DUST_WARM = col(.450, .380, .300)
BRONZE = col(.420, .300, .160)          # the Concord's metal (ALLOY slot, warm)
BRONZE_DARK = col(.140, .095, .060)
REED = col(.300, .260, .120)            # reeds and dry grass
GLAZE_AMBER = col(.420, .210, .050)     # glazed tile, the Vigil's amber
GLAZE_PLUM = col(.200, .060, .120)
# Lights (GLOW slot): Unison, Dissonance (the Serene's, the Vigil's and the AL's are Arche's).
GLOW_UNISON = col(1.0, .640, .200)
GLOW_DISSONANCE = col(.700, .880, 1.0)
GLOW_DUSK = col(1.0, .760, .520)
