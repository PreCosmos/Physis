"""Offline validator and previewer for Hesper's mesh generators (level 7). No Blender needed.

  P=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages
  PYTHONPATH=$P python3 Tools/hesper_meshes/check.py flora structures machines [--quiet] [--preview [NAME ...]]

Each module (Tools/hesper_meshes/<name>.py) exposes, like the Conclave's:
  MESHES    list of builders; builder() -> Part, or builder(variant) -> Part when listed in VARIANTS
  VARIANTS  optional {builder: count}
  CONTRACT  {mesh name: {'size': (x, y, z) metres (0 = any), 'tol': fraction, 'pivot': 'base'|'centre'|'any', 'top': z}}

Checks per mesh: a unique name with a known prefix; known slots, each used by a face; albedo at most 0.9 outside the
glow slot and never negative; a triangle budget by prefix; finite coordinates; no degenerate faces; the pivot (a
mesh that stands on the ground has its lowest point at z 0 within 5 cm and its footprint centred within 10 %, unless
its CONTRACT pivot says otherwise); CONTRACT sizes. Exit status 1 if anything fails.

--preview writes Saved/Hesper/preview/<mesh>.png for every mesh (or only the named ones): two shaded views, the
front three-quarter and the back three-quarter, drawn by a small numpy rasteriser with the vertex colours, so a
mesh can be looked at without Blender or Unreal. Leaf cards are drawn as whole cards (no atlas cutout).
"""
import importlib
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit  # noqa: E402,F401  (puts the Conclave toolkit on the path and lifts its colour rule)
from toolkit import SLOTS, Part  # noqa: E402

ROOT = HERE.parents[1]
# SM_ST_ terrain and pools, SM_SN_ structures and props, SM_SE_ the Cantor.
# Raised on 2026-11-10 (author: "AAA quality assets, as realistic as possible"): LOD 0 budgets. Every mesh gets a LOD
# chain at import, so these are what a close view draws. Ground cover stays light: it is instanced by the hundred
# thousand.
BUDGET = {'SM_ST_': 150000, 'SM_SN_': 40000, 'SM_SE_': 60000}
BUDGET_EXCEPTIONS = {'SM_SN_Concord': 120000, 'SM_SN_Spire': 80000, 'SM_SE_Cantor': 90000}
GROUND_PIVOT = ('SM_SN_',)
GLOW = 'CN_Glow'
# A plant's own far versions (fewer, larger leaf cards and simpler wood, built by its generator: reduction deletes
# whole cards): <mesh>_LOD1, _LOD2, _LOD3, imported as that mesh's LODs. Each takes this share of its mesh's budget and
# its mesh's CONTRACT row.
LOD_SHARE = {'_LOD1': .45, '_LOD2': .16, '_LOD3': .045}


def lod_of(name):
    """(base mesh name, share of its triangle budget) of a mesh or of one of its _LODn versions."""
    for suffix, share in LOD_SHARE.items():
        if name.endswith(suffix):
            return name[:-len(suffix)], share
    return name, 1.0


def builds(module):
    variants = getattr(module, 'VARIANTS', {})
    for builder in module.MESHES:
        count = variants.get(builder, 0)
        for k in (range(count) if count else (None,)):
            yield builder(k) if count else builder()


def check_part(part, contract, problems, quiet=True):
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
        return
    used = set(part.m)
    for index, s in enumerate(part.slots):
        if s not in SLOTS:
            problems.append('%s: unknown slot %s' % (name, s))
        if index not in used:
            problems.append('%s: slot %s is declared but no face uses it (Unreal would import a stray slot)' % (name, s))
    cols = np.asarray(part.c, np.float64)
    if cols.shape != (len(v), 4) or not np.isfinite(cols).all() or cols.min() < 0:
        problems.append('%s: every vertex needs a finite, non-negative RGBA colour' % name)
    else:
        lit = np.zeros(len(v), bool)
        if GLOW in part.slots:
            g = part.slots.index(GLOW)
            for f, m in zip(part.f, part.m):
                if m == g:
                    lit[f] = True
        lit |= cols[:, 3] < .5     # leaf cards (vertex alpha 0) carry a tint on their scanned sheet, not an albedo
        # Terrain vertices carry layer weights (0 to 1), not an albedo (land.py's docstring).
        if 'CN_Ground' not in part.slots and (cols[~lit, :3] > .9 + 1e-6).any():
            problems.append('%s: albedo above 0.9 on %d vertices outside the glow slot' % (name, int((cols[~lit, :3] > .9 + 1e-6).any(1).sum())))
    tris = part.triangles()
    base, share = lod_of(name)
    limit = int(BUDGET_EXCEPTIONS.get(base, BUDGET[prefix]) * share)
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
    spec = contract.get(name, contract.get(base, {}))
    pivot = spec.get('pivot', 'base' if name.startswith(GROUND_PIVOT) else 'any')
    if pivot == 'base':
        if abs(lo[2]) > .05:
            problems.append('%s: lowest point at z %.3f m; a mesh that stands on the ground starts at z 0' % (name, lo[2]))
        off = np.abs((lo[:2] + hi[:2]) / 2)
        if (off > np.maximum(.1 * size[:2], .1)).any() and not spec.get('offset'):
            problems.append('%s: footprint centre is %.2f, %.2f m off the origin' % (name, off[0], off[1]))
    if pivot == 'centre':
        mid = (lo + hi) / 2
        if np.linalg.norm(mid) > max(.15, .1 * float(np.linalg.norm(size))):
            problems.append('%s: centre pivot wanted but the bounds centre is at %s' % (name, np.round(mid, 2).tolist()))
    if 'size' in spec:
        tol = spec.get('tol', .15)
        for axis, (got, want) in enumerate(zip(size, spec['size'])):
            if want > 0 and abs(got - want) > max(tol * want, .05):
                problems.append('%s: size %s is %.2f m, contract %.2f m' % (name, 'xyz'[axis], got, want))
    if 'top' in spec and abs(hi[2] - spec['top']) > max(spec.get('tol', .15) * abs(spec['top']), .05):
        problems.append('%s: highest point at z %.2f m, contract %.2f m' % (name, hi[2], spec['top']))
    if not quiet:
        print('  %-26s %6d tris  size %6.2f x %6.2f x %6.2f m  z %6.2f..%6.2f  slots %s' %
              (name, tris, size[0], size[1], size[2], lo[2], hi[2], ','.join(part.slots)))


# ---------------------------------------------------------------- preview

def png(path, rgb):
    """Writes an (h, w, 3) uint8 array as a PNG."""
    h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def view(part, azimuth, elevation=22.0, size=440):
    """One orthographic view: the camera looks toward the origin from `azimuth` degrees round z (0 = from +x, so the
    mesh's front) and `elevation` above the ground. Lit from the upper left, shaded per face."""
    v = np.asarray(part.v, np.float64)
    c = np.clip(np.asarray(part.c, np.float64)[:, :3], 0, 1)
    az, el = np.radians(azimuth), np.radians(elevation)
    back = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])      # from the mesh toward the camera
    right = np.array([-np.sin(az), np.cos(az), 0.0])
    up = np.cross(back, right)
    p = np.stack([v @ right, v @ up, v @ back], 1)
    lo, hi = p[:, :2].min(0), p[:, :2].max(0)
    span = max((hi - lo).max(), 1e-6)
    s = (size - 16) / span
    off = (size - (hi - lo) * s) / 2
    sx, sy = (p[:, 0] - lo[0]) * s + off[0], size - ((p[:, 1] - lo[1]) * s + off[1])
    image = np.full((size, size, 3), .62)
    depth = np.full((size, size), -1e18)
    light = np.array([.35, -.45, .82])
    light = light / np.linalg.norm(light)
    glow = part.slots.index(GLOW) if GLOW in part.slots else -1
    leaf = part.slots.index('CN_Leaf') if 'CN_Leaf' in part.slots else -1
    for face, slot in zip(part.f, part.m):
        for k in range(1, len(face) - 1):
            i0, i1, i2 = face[0], face[k], face[k + 1]
            n = np.cross(v[i1] - v[i0], v[i2] - v[i0])
            length = np.linalg.norm(n)
            if length < 1e-14:
                continue
            n = n / length
            facing = float(n @ back)
            if facing <= 0 and slot != leaf:
                continue
            lit = float(n @ light)
            shade = 1.0 if slot == glow else .34 + .66 * max(abs(lit) if slot == leaf else lit, 0.0)
            x0, x1 = int(max(min(sx[i0], sx[i1], sx[i2]), 0)), int(min(max(sx[i0], sx[i1], sx[i2]) + 1, size - 1))
            y0, y1 = int(max(min(sy[i0], sy[i1], sy[i2]), 0)), int(min(max(sy[i0], sy[i1], sy[i2]) + 1, size - 1))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
            d = (sy[i1] - sy[i2]) * (sx[i0] - sx[i2]) + (sx[i2] - sx[i1]) * (sy[i0] - sy[i2])
            if abs(d) < 1e-12:
                continue
            w0 = ((sy[i1] - sy[i2]) * (gx - sx[i2]) + (sx[i2] - sx[i1]) * (gy - sy[i2])) / d
            w1 = ((sy[i2] - sy[i0]) * (gx - sx[i2]) + (sx[i0] - sx[i2]) * (gy - sy[i2])) / d
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            if not inside.any():
                continue
            z = w0 * p[i0, 2] + w1 * p[i1, 2] + w2 * p[i2, 2]
            window = depth[y0:y1 + 1, x0:x1 + 1]
            hit = inside & (z > window)
            if not hit.any():
                continue
            window[hit] = z[hit]
            colour = (w0[..., None] * c[i0] + w1[..., None] * c[i1] + w2[..., None] * c[i2]) * shade
            image[y0:y1 + 1, x0:x1 + 1][hit] = colour[hit]
    srgb = np.where(image <= .0031308, image * 12.92, 1.055 * np.clip(image, 0, 1) ** (1 / 2.4) - .055)
    return (np.clip(srgb, 0, 1) * 255).astype(np.uint8)


def preview(part, out):
    sheet = np.concatenate([view(part, 35.0), view(part, 215.0)], 1)
    png(out / (part.name + '.png'), sheet)


def main():
    args = sys.argv[1:]
    names = []
    if '--preview' in args:
        at = args.index('--preview')
        names = [a for a in args[at + 1:] if not a.startswith('--')]
        args = args[:at] + [a for a in args[at + 1:] if a.startswith('--')] + ['--preview']
    modules = [a for a in args if not a.startswith('--')]
    quiet, draw = '--quiet' in args, '--preview' in args
    out = ROOT / 'Saved/Hesper/preview'
    problems, seen = [], {}
    for module_name in modules:
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
            if draw and (not names or any(n.lower() in part.name.lower() for n in names)):
                preview(part, out)
            count += 1
        missing = [n for n in contract if n not in seen]
        if missing:
            problems.append('%s: CONTRACT names with no builder: %s' % (module_name, missing))
        print('  %d meshes' % count)
    if draw:
        print('previews in', out)
    if problems:
        print('\nFAILED (%d):' % len(problems))
        for p in problems:
            print('  -', p)
        sys.exit(1)
    print('\nall checks passed')


if __name__ == '__main__':
    main()
