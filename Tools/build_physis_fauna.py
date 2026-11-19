"""The other worlds' animals (Tools/arche_meshes/fauna.py) as static meshes and as rigs with their animations.

  /usr/bin/blender -b --factory-startup --python-exit-code 1 --python Tools/build_physis_fauna.py -- [names]
Writes Art/Meshes/Arche/SM_AE_<Name>.fbx with Arche's static exporter (Tools/build_physis_arche.py) and
Art/Meshes/Arche/RiggedFauna/SK_AE_<Name>.fbx and A_AE_<Name>_Swim/_Strike.fbx with Arche's rig exporter
(Tools/build_physis_arche_rigs.py). They have a folder of their own because `arche:import_rigs` deletes and re-imports
every rig in the folder it reads, and Arche's own six must not lose their placed meshes. Then, in the editor:
`fauna:import` (Content/Python/physis_fauna.py).
"""
import importlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tools'))
import build_physis_arche as static  # noqa: E402
import build_physis_arche_rigs as rigs  # noqa: E402


def main():
    words = [a.lower() for a in (sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])]
    fauna = importlib.import_module('fauna')
    check = static.arche_check()
    rigs.OUT = ROOT / 'Art/Meshes/Arche/RiggedFauna'
    rigs.OUT.mkdir(parents=True, exist_ok=True)
    problems, warnings = [], []
    for builder in fauna.MESHES:
        start = time.time()
        part = builder()
        if words and not any(w in part.name.lower() for w in words):
            continue
        found = []
        check.check_part(part, fauna.CONTRACT, found, True)
        found += rigs.check_rig(part)
        if found:
            problems += found
            print('refused %s: %s' % (part.name, '; '.join(found)), flush=True)
            continue
        static.export(part, warnings)
        bones, written = rigs.export(builder())   # a fresh build: the static export has turned this one into an object
        print('fauna %-22s %7d tris  %3d bones  %s  %.1f s' % (part.name, part.triangles(), bones, ', '.join(written), time.time() - start), flush=True)
    for w in warnings:
        print('warning:', w)
    if problems:
        print('\nFAILED (%d):\n  - %s' % (len(problems), '\n  - '.join(problems)))
        sys.exit(1)
    print('\nall written')


if __name__ == '__main__':
    main()
