"""Run in Blender (headless): Director Voss's costume, by the Conclave's costume build (Tools/build_conclave_people.py)
with her entry added to its tables (Content/Python/physis_grove_people.py says why she is not in the Conclave's cast file).

  /usr/bin/blender -b --factory-startup --python-exit-code 1 --python Tools/build_grove_people.py

Needs her guides (grove:voss:people_guides, then the editor closed); writes her costume FBX and cloth mask beside them
(Art/Characters/Conclave/Voss), for grove:voss:people_import.
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Content/Python'))
sys.path.insert(0, str(ROOT / 'Tools/conclave_meshes'))

import costumes  # noqa: E402,F401  (before install(): people.py checks the cast against the Conclave's lore as it loads)
import physis_grove_people  # noqa: E402

key = physis_grove_people.install()

# The coat she wears is the Conclave doctor's, ported to her body, and a ported garment keeps the colours it was
# modelled in (white). Hers is the Just's graphite: every pale neutral of her costume is brought down to charcoal,
# keeping the shading the garment's builder painted (folds, hems), and the gold trim stays gold.
import numpy as np  # noqa: E402
from palette import PALETTE  # noqa: E402

_costume = costumes.costume


def _graphite(name, guide):
    made = _costume(name, guide)
    if name == key:
        c = np.asarray(made.part.c, np.float64)
        rgb = c[:, :3]
        lum = rgb @ np.array([.3, .59, .11])
        neutral = (rgb.max(1) - rgb.min(1)) < .06
        pale = neutral & (lum > .2)
        target = np.asarray(PALETTE['CHARCOAL'][:3], np.float64)
        rgb[pale] = target[None, :] * (.75 + .5 * np.clip(lum[pale], 0, 1))[:, None]
        made.part.c = c.tolist()
    return made


costumes.costume = _graphite
sys.argv = [a for a in sys.argv if a != '--'] + ['--', key]
runpy.run_path(str(ROOT / 'Tools/build_conclave_people.py'), run_name='__main__')
