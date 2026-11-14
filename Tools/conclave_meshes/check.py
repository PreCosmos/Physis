"""Offline validator for the Conclave's mesh generators. No Blender needed.

  PYTHONPATH=~/PhysisProject/Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages \\
      python3 Tools/conclave_meshes/check.py architecture districts people al_flora drum [--quiet]

Each module (Tools/conclave_meshes/<name>.py) exposes:
  MESHES    list of builders; builder() -> Part, or builder(variant) -> Part when listed in VARIANTS
  VARIANTS  optional {builder: count}
  CONTRACT  optional {mesh name: {'size': (x, y, z) metres, 'tol': fraction, 'pivot': 'base'|'centre'|'any',
                                  'top': z metres}}
            (Tools/conclave/README.md lists the sizes gameplay depends on; 'top' is the highest point's height, for
            what hangs from its top rather than standing on z 0)

Checks per mesh: unique, prefixed name; known slots, each used; every vertex colour in the palette;
triangle budget by prefix; finite coordinates; no degenerate or repeated-index faces; pivot (a
ground-standing mesh's lowest point is at z 0 within 5 cm unless its CONTRACT pivot says otherwise);
CONTRACT sizes and top. Exit status 1 if anything fails.
"""
import importlib
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'Content/Python'))

from toolkit import SLOTS, Part, check_colours  # noqa: E402

# The AL are tessellated twice as finely as the rest (al_flora.AL_DETAIL) and the trees, hedges and shrubs are made of
# dense cutout cards (2026-11-07 review), so they have budgets of their own.
# SK_ is a MetaHuman's whole costume (costumes.py), one skinned mesh with sleeves, legwear and shoes fitted over the body
# guide's own surface: about as heavy as Physis's outfit (Art/Characters/Physis/outfit-build.json).
BUDGET ={'SM_CN_': 14000, 'SM_CP_': 9000, 'SM_CE_': 18000, 'SM_CV_': 1200, 'SM_CD_': 120000, 'SK_': 50000}
BUDGET_EXCEPTIONS = {'SM_CN_Spire': 30000, 'SM_CN_Freighter': 24000, 'SM_CN_Archive': 24000, 'SM_CN_Orrery': 20000,
                     'SM_CE_ALShepherd': 24000, 'SM_CE_ALSiegeframe': 24000,
                     'SM_CV_TreeWhite': 12000, 'SM_CV_TreeRed': 12000, 'SM_CV_TreeBlack': 12000, 'SM_CV_FruitTree': 12000,
                     'SM_CV_Hedge': 3000, 'SM_CV_Shrub': 2500}
GROUND_PIVOT = ('SM_CN_', 'SM_CP_', 'SM_CV_')  # stand on the ground: lowest point at z 0


def builds(module):
    variants = getattr(module, 'VARIANTS', {})
    for builder in module.MESHES:
        count = variants.get(builder, 0)
        if count:
            for k in range(count):
                yield builder(k)
        else:
            yield builder()


def check_part(part, contract, problems, quiet):
    name = part.name
    prefix = next((p for p in BUDGET if name.startswith(p)), None)
    if prefix is None:
        problems.append('%s: name must start with one of %s' % (name, ', '.join(BUDGET)))
        return
    v = np.asarray(part.v, np.float64)
    if len(v) == 0 or len(part.f) == 0:
        problems.append('%s: empty mesh' % name)
        return
    if not np.isfinite(v).all():
        problems.append('%s: non-finite coordinates' % name)
    for s in part.slots:
        if s not in SLOTS:
            problems.append('%s: unknown slot %s' % (name, s))
    used = set(part.m)
    for index, s in enumerate(part.slots):
        if index not in used:
            problems.append('%s: slot %s is declared but no face uses it (Unreal would import a stray slot)' % (name, s))
    bad = check_colours(part)
    if bad:
        problems.append('%s: %d colours outside the palette, e.g. %s' % (name, len(bad), bad[:4]))
    tris = part.triangles()
    limit = BUDGET_EXCEPTIONS.get(name, BUDGET[prefix])
    if tris > limit:
        problems.append('%s: %d triangles, budget %d' % (name, tris, limit))
    degenerate = 0
    for f in part.f:
        if len(set(f)) != len(f):
            degenerate += 1
            continue
        a, b, c = v[f[0]], v[f[1]], v[f[2]]
        if np.linalg.norm(np.cross(b - a, c - a)) < 1e-12:
            degenerate += 1
    if degenerate > max(2, len(part.f) * .01):
        problems.append('%s: %d degenerate faces' % (name, degenerate))
    lo, hi = v.min(0), v.max(0)
    size = hi - lo
    spec = contract.get(name, {})
    pivot = spec.get('pivot', 'base' if name.startswith(GROUND_PIVOT) else 'any')
    if pivot == 'base' and abs(lo[2]) > .05:
        problems.append('%s: lowest point at z %.3f m; ground-standing meshes must start at z 0' % (name, lo[2]))
    if pivot == 'centre':
        mid = (lo + hi) / 2
        if np.linalg.norm(mid) > max(.15, .1 * float(np.linalg.norm(size))):
            problems.append('%s: centre pivot wanted but the bounds centre is at %s' % (name, np.round(mid, 2).tolist()))
    if 'size' in spec:
        want = np.asarray(spec['size'], np.float64)
        tol = spec.get('tol', .15)
        for axis, (got, w) in enumerate(zip(size, want)):
            if w > 0 and abs(got - w) > max(tol * w, .05):
                problems.append('%s: size %s on %s is %.2f m, contract %.2f m' % (name, 'xyz'[axis], name, got, w))
    if 'top' in spec and abs(hi[2] - spec['top']) > max(spec.get('tol', .15) * spec['top'], .05):
        problems.append('%s: highest point at z %.2f m, contract %.2f m' % (name, hi[2], spec['top']))
    if not quiet:
        print('  %-28s %6d tris  size %6.2f x %6.2f x %6.2f m  slots %s' % (name, tris, size[0], size[1], size[2], ','.join(part.slots)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    quiet = '--quiet' in sys.argv
    problems, seen = [], {}
    for module_name in args:
        module = importlib.import_module(module_name)
        contract = getattr(module, 'CONTRACT', {})
        print(module_name)
        count = 0
        for part in builds(module):
            if not isinstance(part, Part):
                problems.append('%s: a builder returned %r, not a Part' % (module_name, type(part)))
                continue
            if part.name in seen:
                problems.append('%s: name used twice (%s and %s)' % (part.name, seen[part.name], module_name))
            seen[part.name] = module_name
            check_part(part, contract, problems, quiet)
            count += 1
        missing = [n for n in contract if n not in seen]
        if missing:
            problems.append('%s: CONTRACT names with no builder: %s' % (module_name, missing))
        print('  %d meshes' % count)
    if problems:
        print('\nFAILED (%d):' % len(problems))
        for p in problems:
            print('  -', p)
        sys.exit(1)
    print('\nall checks passed')


if __name__ == '__main__':
    main()
