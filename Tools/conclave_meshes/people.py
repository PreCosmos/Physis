"""People of the Conclave (level 3): the garments that dress the UE5 Mannequins, and the figures that
are not human (Tools/conclave/README.md, People).

Humans are SKM_Quinn_Simple / SKM_Manny_Simple playing MM_Idle. Three rigid garment meshes ride the Body's
bones (Lower -> pelvis, Upper -> spine_05, Head -> head): the scenario sets each to the actor's transform in
the bind pose and attaches it keeping that world transform, and BP_NPC's construction script and BeginPlay
attach them again keeping the stored bone-relative transform. So every garment here is modelled in actor
space over the Mannequin's bind pose: feet at z 0, facing +x,
the character's left at -y. A rigid garment can only cover what moves with its bone: skirts, coat
skirts and robes hang from the pelvis and keep a hand's room at the hips, where MM_Idle hangs the hands;
tops are sleeveless and stay inside CHEST_HALF where the arms hang beside the chest; hair, hats, hoods
and beards ride the head. _fit() fails the build if a garment reaches into the arms' room, _fit_head() if
headwear sinks into the skull or floats off it.

Cloth is a solid of real thickness (outer face, inner face and closed edges), so a hem, a lapel or an
armhole reads as fabric under PBR light and the inside of a skirt or a hood shades correctly. Vertex
colour carries the shading a real garment collects: fold valleys, the inside, dust toward the hem.

The figures (SM_CP_Robot, SM_CP_Courier, SM_CP_Mechanoid, SM_CP_Mecha, SM_CP_Lightform, SM_CP_Wisp) are
static meshes standing on z 0 facing +x: casings over joints and frames, worn toward the ground.

Who wears what is CAST in Content/Python/physis_conclave_cast.py (a pure literal the editor reads); this
module checks at import that every mesh CAST names is one it builds and that each garment is worn by the
body it was modelled on. Importing needs no numpy (only the builders do), so the table and the checks also
run in the editor's Python.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'Content/Python'))

from palette import (ASH, BLACK, BLUE, BLUE_PALE, CHARCOAL, GOLD, GOLD_DEEP, GOLD_PALE, GOLD_STRAW, IVORY,  # noqa: E402
                     LIGHT_BLUE, LIGHT_WHITE, RED, SLATE, WHITE, WHITE_COOL, WHITE_PURE, allowed, col)
from physis_conclave_cast import CAST_MANNEQUIN, CAST_METAHUMAN, MH  # noqa: E402
from physis_conclave_lore import PEOPLE  # noqa: E402

try:
    import numpy as np
    from toolkit import Part, bevel_box, bezier, frame, lathe, noise2
except ImportError:  # Unreal's bundled Python: only the cast checks run there
    np = None


# ---------------------------------------------------------------- the Mannequins' bind pose (metres)

# Torso sections (z, half-width along y, front x, back x). The README's landmarks fix the heights; the
# surfaces between are estimates, which is why garments keep ease and the tops are capped by room().
TORSO = {
    'Quinn': ((.84, .178, .080, -.118), (.90, .186, .092, -.132), (.96, .180, .098, -.124), (1.02, .152, .098, -.098),
              (1.07, .135, .096, -.090), (1.13, .137, .100, -.092), (1.19, .143, .110, -.098), (1.25, .147, .135, -.104),
              (1.30, .148, .140, -.107), (1.35, .146, .122, -.110), (1.40, .138, .100, -.106), (1.44, .124, .080, -.094),
              (1.47, .100, .068, -.080), (1.50, .072, .060, -.066), (1.53, .060, .056, -.058), (1.62, .056, .054, -.056)),
    'Manny': ((.82, .168, .085, -.112), (.88, .176, .098, -.124), (.94, .172, .104, -.118), (1.00, .158, .108, -.104),
              (1.06, .146, .110, -.098), (1.12, .148, .114, -.100), (1.18, .150, .120, -.106), (1.24, .151, .130, -.112),
              (1.30, .150, .135, -.116), (1.36, .148, .128, -.118), (1.41, .142, .110, -.112), (1.45, .128, .088, -.100),
              (1.48, .106, .074, -.084), (1.51, .078, .066, -.070), (1.54, .066, .060, -.062), (1.62, .062, .058, -.060)),
}
# Skull: centre, front, back, half-width, top (the head bone is at 1.625, the top of the head ~1.80).
HEAD = {'Quinn': ((.006, 0., 1.703), .094, .102, .076, .097), 'Manny': ((.006, 0., 1.703), .097, .106, .080, .097)}
# Lower face for beards (z, half-width, front, back): jaw and chin, then the beard's own hanging taper.
JAW = ((1.47, .020, .074, -.004), (1.50, .030, .084, -.010), (1.53, .040, .090, -.018), (1.555, .048, .094, -.028),
       (1.575, .055, .096, -.034), (1.60, .061, .099, -.036), (1.625, .066, .104, -.032), (1.65, .071, .108, -.026),
       (1.68, .075, .098, -.016), (1.71, .078, .090, -.006))
PIT = {'Quinn': 1.335, 'Manny': 1.345}       # armholes open above the armpit
SHOULDER = {'Quinn': 1.43, 'Manny': 1.445}   # where the straps leave the front and back panels
STRAP = {'Quinn': (.072, .118), 'Manny': (.078, .128)}  # neck-side and arm-side edge of a strap (y)
CHEST_HALF = .155
# MM_Idle's arms: beside the chest (CHEST_HALF), elbows and forearms beside the waist, hands beside the
# hips down to the fingertips. A garment's |y| stays inside room(z) where the arms hang (ARM_X).
_ROOM = ((.62, .45), (.70, .30), (.735, .212), (.95, .212), (.99, .186), (1.09, .186), (1.13, CHEST_HALF), (1.47, CHEST_HALF), (1.53, .45))
ARM_X = (-.06, .16)


def room(z):
    zs, ys = zip(*_ROOM)
    return np.interp(z, zs, ys)


def _fit(part):
    """Fails the build if a garment reaches into the arms' room: rigid cloth there would cut the arms."""
    v = np.asarray(part.v)
    over = (v[:, 0] > ARM_X[0]) & (v[:, 0] < ARM_X[1]) & (np.abs(v[:, 1]) > room(v[:, 2]) + .002)
    if over.any():
        i = int(np.argmax(np.where(over, np.abs(v[:, 1]) - room(v[:, 2]), -1.)))
        raise ValueError("%s reaches into the arms' room at %s (|y| <= %.3f there)" % (part.name, np.round(v[i], 3).tolist(), room(v[i, 2])))
    return part


# ---------------------------------------------------------------- palette-safe shading

_KMIN = {}


def _kmin(rgb):
    """The darkest factor that keeps a gold, red or blue in its palette family (greys go to black)."""
    key = tuple(round(float(v), 4) for v in rgb[:3])
    if key not in _KMIN:
        c = np.asarray(key)
        bad = next((k for k in np.linspace(1, .02, 50) if not allowed(c * k)), None)
        if bad is None:
            _KMIN[key] = 0.0
        else:
            lo, hi = bad, bad + .02
            for _ in range(20):
                mid = (lo + hi) / 2
                lo, hi = (lo, mid) if allowed(c * mid) else (mid, hi)
            _KMIN[key] = hi * 1.01 + .002
    return _KMIN[key]


def _tone(colour, k=1.0, cap=.9):
    """RGBA rows of colour scaled by k (scalar or array), kept inside its palette family and under the
    albedo cap (None for metals and lights, whose colour is reflectance or brightness)."""
    rgb = np.asarray(colour[:3], np.float64)
    lo = _kmin(rgb)
    hi = max(lo, (1.0 if cap is None else cap) / max(rgb.max(), 1e-6))
    k = np.clip(np.asarray(k, np.float64), lo, hi)
    out = k[..., None] * rgb
    return np.concatenate([out, np.ones(out.shape[:-1] + (1,))], -1)


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- solids: cloth sheets, shells, plates

def _grid(nv, nu, closed=False):
    i, j = np.meshgrid(np.arange(nv - 1), np.arange(nu if closed else nu - 1), indexing='ij')
    k = (j + 1) % nu
    return np.stack([i * nu + j, i * nu + k, (i + 1) * nu + k, (i + 1) * nu + j], -1).reshape(-1, 4)


def _rim(p, q, away, wrap, mask):
    """Edge quads closing a sheet between its outer border p and inner border q, facing away."""
    a, b, c, d = p, np.roll(p, -1, 0), np.roll(q, -1, 0), q
    w = away + np.roll(away, -1, 0)
    if not wrap:
        a, b, c, d, w = a[:-1], b[:-1], c[:-1], d[:-1], w[:-1]
    quads = np.stack([a, b, c, d], 1)
    back = np.sum(np.cross(b - a, c - a) * w, -1) < 0
    quads[back] = quads[back][:, ::-1]
    if mask is not True:
        quads = quads[np.asarray(mask, bool)]
    return quads


def _ngon(part, ring, toward, base, slot, k=1.0, cap=.9):
    """One flat polygon over a closed ring of points, its front turned toward the given direction."""
    ring = np.asarray(ring, np.float64)
    nrm = np.sum(np.cross(ring, np.roll(ring, -1, 0)), 0)
    order = list(range(len(ring))) if np.dot(nrm, toward) >= 0 else list(range(len(ring)))[::-1]
    part.add(ring, [order], _tone(base, k, cap), slot, False)


def _sheet(part, P, thick, base, slot, out, k=1.0, closed=False, inner=.6, rims=True, cap=.9, smooth=True, close_top=False,
           under=None):
    """A thin solid: P (rows, cols, 3) is the outer surface, the inner one lies thick behind it along the
    normal, and rims close the borders (top, bottom, left, right: True, False or a mask per segment).
    out(P) points to the outer side and fixes the winding. Colour is base scaled by k per vertex; the
    inside is darker. close_top caps the first row of a closed sheet (a crown). under (same shape as P)
    gives the inner surface itself, for a sheet whose outer face is combed into ridges: offset along those
    ridges' normals by more than their spacing, the inner face would fold through itself. Returns (outer, inner)."""
    P = np.asarray(P, np.float64)
    nv, nu = P.shape[:2]
    Pu = (np.roll(P, -1, 1) - np.roll(P, 1, 1)) if closed else np.gradient(P, axis=1)
    Pv = np.gradient(P, axis=0)
    n = np.cross(Pu, Pv)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
    flip = float(np.sum(n * out(P))) < 0
    if flip:
        n = -n
    t = np.asarray(thick, np.float64)
    Q = P - n * (t[..., None] if t.ndim else t) if under is None else np.asarray(under, np.float64)
    kk = np.broadcast_to(np.asarray(k, np.float64), (nv, nu)).ravel()
    faces = _grid(nv, nu, closed)
    if flip:
        faces = faces[:, ::-1]
    part.add(P.reshape(-1, 3), faces.tolist(), _tone(base, kk, cap), slot, smooth)
    # The inner face is wound the other way but keeps the outer face's diagonal ([a, d, c, b], not [d, c, b, a]),
    # so a twisted quad triangulates alike on both sides and the inside never shows through the outside.
    part.add(Q.reshape(-1, 3), np.roll(faces[:, ::-1], 1, axis=1).tolist(), _tone(base, kk * inner, cap), slot, smooth)
    flags = (True,) * 4 if rims is True else ((False,) * 4 if rims is False else rims)
    if close_top:
        _ngon(part, P[0], -Pv[0].sum(0), base, slot, float(np.mean(kk)), cap)
        _ngon(part, Q[0], Pv[0].sum(0), base, slot, float(np.mean(kk)) * inner, cap)
        flags = (False,) + tuple(flags[1:])
    groups = []
    if flags[0] is not False:
        groups.append(_rim(P[0], Q[0], -Pv[0], closed, flags[0]))
    if flags[1] is not False:
        groups.append(_rim(P[-1], Q[-1], Pv[-1], closed, flags[1]))
    if not closed:
        if flags[2] is not False:
            groups.append(_rim(P[:, 0], Q[:, 0], -Pu[:, 0], False, flags[2]))
        if flags[3] is not False:
            groups.append(_rim(P[:, -1], Q[:, -1], Pu[:, -1], False, flags[3]))
    groups = [g for g in groups if len(g)]
    if groups:
        quads = np.concatenate(groups)
        part.add(quads.reshape(-1, 3), np.arange(len(quads) * 4).reshape(-1, 4).tolist(), _tone(base, float(np.mean(kk)) * .8, cap), slot, False)
    return P, Q


def _axis(cx=0.0, cy=0.0):
    return lambda P: (P - np.array([cx, cy, 0.])) * np.array([1., 1., 0.])


def _away(c):
    return lambda P: P - np.asarray(c, np.float64)


def _dir(d):
    return lambda P: np.broadcast_to(np.asarray(d, np.float64), P.shape)


def _shell(part, c, r, base, slot, k=1.0, sides=16, rings=10, R=None, cap=.9, smooth=True, shade=None):
    """A closed ellipsoid on a latitude grid with polygon poles. r = (front, half-width, top) or
    (front, half-width, top, back, bottom) for an egg; R turns it (columns: local x, y, z)."""
    fr, hw, top = r[:3]
    bk, bot = (r[3], r[4]) if len(r) > 3 else (fr, top)
    psi = np.linspace(-math.pi / 2, math.pi / 2, rings + 2)[1:-1]
    phi = np.linspace(-math.pi, math.pi, sides, endpoint=False)
    PS, PH = np.meshgrid(psi, phi, indexing='ij')
    x = np.where(np.cos(PH) >= 0, fr, bk) * np.cos(PS) * np.cos(PH)
    y = hw * np.cos(PS) * np.sin(PH)
    z = np.where(PS >= 0, top, bot) * np.sin(PS)
    L = np.stack([x, y, z], -1)
    kk = np.broadcast_to(np.asarray(k if shade is None else shade(L), np.float64), PS.shape)
    W = L @ (np.eye(3) if R is None else np.asarray(R)).T + c
    faces = _grid(rings, sides, True)
    test = np.cross(W[0, 1] - W[0, 0], W[1, 0] - W[0, 0])
    if np.dot(test, W[0, 0] - np.asarray(c)) < 0:
        faces = faces[:, ::-1]
    part.add(W.reshape(-1, 3), faces.tolist(), _tone(base, kk.ravel(), cap), slot, smooth)
    _ngon(part, W[0], W[0].mean(0) - c, base, slot, float(kk[0].mean()), cap)
    _ngon(part, W[-1], W[-1].mean(0) - c, base, slot, float(kk[-1].mean()), cap)
    return W


def _tube(part, pts, radii, colour, slot, sides, closed=False):
    """toolkit.tube with its ring frames carried along the path (parallel transport). toolkit.frame() picks its
    reference axis by how steep the path is, so a path that crosses that threshold (a curling tail, a trail of light
    running down to the floor, any ring standing upright) turns one ring a quarter turn against the next, and the
    quads between them pinch and invert. Same rings, faces and caps otherwise; closed joins the last ring to the
    first (a ring, a loop) without caps."""
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (n,))
    if closed:
        T = np.roll(pts, -1, 0) - np.roll(pts, 1, 0)
    else:
        T = np.array([pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)] for i in range(n)])
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    a, b = frame(T[0])
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    rings = []
    for i in range(n):
        if i:
            carried = a - T[i] * np.dot(a, T[i])
            if np.linalg.norm(carried) < 1e-6:  # the path doubled back on itself: start a fresh frame
                a, b = frame(T[i])
            else:
                a = carried / np.linalg.norm(carried)
                b = np.cross(T[i], a)
        rings.append(pts[i] + radii[i] * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b))
    faces = [[i * sides + j, i * sides + (j + 1) % sides, ((i + 1) % n) * sides + (j + 1) % sides, ((i + 1) % n) * sides + j]
             for i in range(n if closed else n - 1) for j in range(sides)]
    if not closed:
        faces += [list(range(sides))[::-1], [(n - 1) * sides + j for j in range(sides)]]
    return part.add(np.concatenate(rings), faces, colour, slot, True)


def _torus(part, c, big, small, colour, slot, sides=48, ring=10, axis='z', arc=2 * math.pi, start=0.0):
    """toolkit.torus on _tube: a ring of radius big lying flat ('z') or standing upright facing x or y, which
    toolkit.frame() would twist where the ring runs steeply."""
    full = arc >= 2 * math.pi - 1e-6
    n = sides + (0 if full else 1)
    t = start + np.linspace(0, arc, n, endpoint=not full)
    u, w = np.cos(t) * big, np.sin(t) * big
    zero = np.zeros(n)
    path = {'x': (zero, u, w), 'y': (u, zero, w)}.get(axis, (u, w, zero))
    path = np.stack(path, -1) + np.asarray(c, np.float64)
    rgba = np.asarray(colour, np.float64)
    if rgba.ndim == 1:
        rgba = np.tile(rgba, (n * ring, 1))
    return _tube(part, path, small, rgba, slot, ring, closed=full)


def _limb(part, pts, radii, base, slot, sides=10, k=1.0, cap=.9):
    """A tube (_tube) with palette-safe shading per ring (k: scalar or one per point)."""
    pts = np.asarray(pts, np.float64)
    kk = np.broadcast_to(np.asarray(k, np.float64), (len(pts),))
    _tube(part, pts, radii, np.repeat(_tone(base, kk, cap), sides, 0), slot, sides)


def _box(part, c, h, base, slot, bevel=.01, k=1.0, R=None, yaw=0., cap=.9):
    """A bevelled box, turned by yaw or by a rotation R (columns: local x, y, z)."""
    if R is None:
        bevel_box(part, c, h, _tone(base, k, cap), slot, bevel, yaw)
        return
    tmp = Part('tmp', part.slots)
    bevel_box(tmp, (0, 0, 0), h, _tone(base, k, cap), slot, bevel)
    _merge(part, tmp, R, c)


def _merge(dst, src, R=None, t=(0, 0, 0)):
    """Appends src's faces to dst, turned by the rotation R and moved by t (winding is kept)."""
    v = np.asarray(src.v, np.float64)
    if R is not None:
        v = v @ np.asarray(R, np.float64).T
    v = v + np.asarray(t, np.float64)
    first = len(dst.v)
    dst.v.extend(v.tolist())
    dst.c.extend(src.c)
    for f, m, s in zip(src.f, src.m, src.s):
        dst.f.append([first + i for i in f])
        dst.m.append(dst.slots.index(src.slots[m]))
        dst.s.append(s)


def _basis(x, z_hint=(0, 0, 1)):
    """Rotation whose columns are local x (along x), y and z, right-handed, z as close to z_hint as can be."""
    x = np.asarray(x, np.float64)
    x = x / np.linalg.norm(x)
    y = np.cross(np.asarray(z_hint, np.float64), x)
    if np.linalg.norm(y) < 1e-6:
        y = np.cross((1., 0, 0) if abs(x[0]) < .9 else (0, 1., 0), x)
    y /= np.linalg.norm(y)
    return np.stack([x, y, np.cross(x, y)], 1)


def _rot(axis, deg):
    a = np.asarray(axis, np.float64)
    a = a / np.linalg.norm(a)
    t = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K


def _button(part, pos, nrm, r, base, slot, h=None, sides=10, k=1.0, cap=.9):
    """A domed button (or rivet, snap, stud) standing on a surface along nrm."""
    nrm = np.asarray(nrm, np.float64)
    nrm = nrm / np.linalg.norm(nrm)
    h = r * .45 if h is None else h
    a, b = frame(nrm)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    ring = np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b
    pos = np.asarray(pos, np.float64)
    verts = np.concatenate([pos + ring * r, pos + ring * r + nrm * h * .55, pos + ring * r * .68 + nrm * h])
    faces = [[j, (j + 1) % sides, sides + (j + 1) % sides, sides + j] for j in range(sides)]
    faces += [[sides + j, sides + (j + 1) % sides, 2 * sides + (j + 1) % sides, 2 * sides + j] for j in range(sides)]
    faces += [[2 * sides + j for j in range(sides)], list(range(sides))[::-1]]
    part.add(verts, faces, _tone(base, k, cap), slot, True)


def _plate(part, c, R, w, h, bulge, thick, base, slot, k=1.0, nu=6, nv=6, trim=None, trim_r=None, trim_k=1.0, round_=.35):
    """A bowed armour plate w x h in the local y-z plane, facing local +x, with thickness and closed
    edges; its corners are rounded by round_. trim adds a rolled edge in another colour (gold)."""
    R = np.asarray(R, np.float64)
    U, V = np.meshgrid(np.linspace(-1, 1, nu), np.linspace(1, -1, nv))
    corner = 1 - round_ * (U ** 2 * V ** 2)
    Lp = np.stack([bulge * (1 - .85 * U ** 2) * (1 - .45 * V ** 2), U * corner * w / 2, V * (1 - round_ * .5 * U ** 2 * V ** 2) * h / 2], -1)
    P = Lp @ R.T + np.asarray(c, np.float64)
    P, Q = _sheet(part, P, thick, base, slot, _dir(R[:, 0]), k=k, cap=None if slot in ('CN_Metal', 'CN_Gold') else .9)
    if trim is not None:
        loop = np.concatenate([P[0], P[1:, -1], P[-1, ::-1][1:], P[::-1, 0][1:-1]])
        mid = np.concatenate([Q[0], Q[1:, -1], Q[-1, ::-1][1:], Q[::-1, 0][1:-1]])
        edge = (loop + mid) / 2
        _limb(part, np.concatenate([edge, edge[:1]]), trim_r or thick * .7, trim, 'CN_Gold', 6, trim_k, None)
    return P, Q


# ---------------------------------------------------------------- garment surfaces

class Drape:
    """A garment surface: horizontal superellipse sections interpolated in z from rows (z, half-width,
    front x, back x), grown by ease (a number or ((z, ease), ...)) and kept inside the arms' room, with
    hanging folds that deepen from fold_top to fold_low, gathers under a waistband, blousing ripples
    (tuck) and fine wrinkles. Every piece laid on a garment (aprons, pockets, belts, buttons) asks at()
    for its points, so it follows the folds and never sinks into the cloth."""

    def __init__(self, rows, ease=0., n=2.2, folds=0, amp=0., fold_top=.9, fold_low=0., gathers=0, gather_amp=0.,
                 gather_top=1.06, tuck=None, wrinkle=0., wrinkle_top=1.38, seed=0, spare=.003, capped=True, ripples=(),
                 quilt=None):
        rows = sorted(rows)
        # ripples: ((z_lo, z_hi, count, amp), ...) gathers that grow toward z_hi (a drawstring neckline, a yoke);
        # quilt: (pitch, amp, z_lo, z_hi) padded channels between stitch lines (a gambeson).
        self.ripples, self.quilt = tuple(ripples), quilt
        spare = spare + sum(r[3] for r in self.ripples) + (quilt[1] if quilt else 0.)
        self.z, self.hw, self.f, self.b = (np.array(c, np.float64) for c in zip(*rows))
        self.ease, self.n, self.amp = ease, n, amp
        self.fold_top, self.fold_low = fold_top, fold_low
        self.gathers, self.gather_amp, self.gather_top = gathers, gather_amp, gather_top
        self.tuck, self.wrinkle, self.wrinkle_top = tuck, wrinkle, wrinkle_top
        self.seed, self.spare, self.capped = seed, spare, capped
        rng = np.random.default_rng(seed)
        # A few incommensurate fold frequencies (integers, so a closed skirt meets itself at the seam).
        self.modes = [(max(1, round(folds * m)), rng.uniform(0, 2 * math.pi), w, rng.uniform(-1.5, 1.5))
                      for m, w in ((1.0, 1.0), (1.62, .5), (2.71, .22))] if folds else []
        self.phase = rng.uniform(0, 2 * math.pi)

    def depth(self, z):
        t = np.clip((self.fold_top - np.asarray(z, np.float64)) / max(self.fold_top - self.fold_low, 1e-6), 0, 1)
        return self.amp * t ** 1.2

    def gather(self, z):
        return self.gather_amp * np.clip(1 - (self.gather_top - np.asarray(z, np.float64)) / .14, 0, 1) ** 1.5

    def disp(self, theta, z):
        theta, z = np.asarray(theta, np.float64), np.asarray(z, np.float64)
        d = np.zeros(np.broadcast(theta, z).shape)
        if self.modes:
            total = sum(m[2] for m in self.modes)
            d = d + self.depth(z) * sum(w * np.sin(m * theta + ph + drift * (self.fold_top - z)) for m, ph, w, drift in self.modes) / total
        if self.gather_amp:
            d = d + self.gather(z) * np.sin(self.gathers * theta + self.phase)
        if self.tuck:
            lo, hi, a = self.tuck
            w = np.clip((hi - z) / (hi - lo), 0, 1) ** 1.5 * (z >= lo - .01)
            d = d + a * w * np.sin(2 * math.pi * (z - lo) / .027 + 1.4 * np.sin(2 * theta + self.phase))
        if self.wrinkle:
            fade = np.clip((self.wrinkle_top + .04 - z) / .04, 0, 1)
            d = d + self.wrinkle * fade * noise2(theta * 5.0 + 3, z * 22.0, self.seed + 5)
        for z_lo, z_hi, count, a in self.ripples:
            d = d + a * _smooth((z - z_lo) / (z_hi - z_lo)) * np.sin(count * theta + self.phase + 2.0 * noise2(theta * 2.0, z * 9.0, self.seed + 13))
        if self.quilt:
            pitch, a, z_lo, z_hi = self.quilt
            inside = (z > z_lo) & (z < z_hi)
            d = d + a * inside * (np.abs(np.sin(math.pi * (z - z_lo) / pitch)) ** .6 - .5)
        return d

    def axes(self, z):
        z = np.asarray(z, np.float64)
        e = np.interp(z, *zip(*self.ease)) if np.ndim(self.ease) else self.ease
        hw = np.interp(z, self.z, self.hw) + e
        f = np.interp(z, self.z, self.f) + e
        b = np.interp(z, self.z, self.b) - e
        if self.capped:
            hw = np.minimum(hw, room(z) - self.depth(z) - self.gather(z) - self.wrinkle - self.spare)
        return hw, f, b

    def at(self, theta, z, extra=0., fold=1.0):
        theta, z = np.broadcast_arrays(np.asarray(theta, np.float64), np.asarray(z, np.float64))
        hw, f, b = self.axes(z)
        d = (fold * self.disp(theta, z) if fold else 0.) + extra
        c, s = np.cos(theta), np.sin(theta)
        e = 2.0 / self.n
        x = np.where(c >= 0, f + d, d - b) * np.sign(c) * np.abs(c) ** e
        y = (hw + d) * np.sign(s) * np.abs(s) ** e
        return np.stack([x, y, z], -1)

    def normal(self, theta, z, extra=0., fold=1.0):
        """Outward surface normal at (theta, z), from the surface's own derivatives."""
        pt = self.at(np.asarray(theta) + 1e-3, z, extra, fold) - self.at(np.asarray(theta) - 1e-3, z, extra, fold)
        pz = self.at(theta, np.asarray(z) + 1e-3, extra, fold) - self.at(theta, np.asarray(z) - 1e-3, extra, fold)
        n = np.cross(pt, pz)
        return n / (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12)


def _cloth_k(dr, th, z, z_hem, seed, shade=5.0):
    """Cloth shading: ridges of folds catch light and valleys hold shadow, dust gathers toward the hem,
    and the dye is never perfectly even."""
    k = 1 + shade * dr.disp(th, z)
    k = k * (.84 + .16 * np.clip((z - z_hem) / .35, 0, 1))
    return k * (1 + .04 * noise2(th * 3.0 + 1, z * 8.0, seed + 3))


def _skirt(part, dr, base, slot, z_top, z_hem, nu=64, nv=22, thick=.008, span=None, lap=0, seed=0, wave=.006,
           hem_roll=.0025, k=1.0, extra=0., rims=True, fold=1.0):
    """The hanging body of a skirt, a coat's skirt or a robe on drape dr, from z_top down to the hem.
    span(z) -> (theta0, theta1) leaves the front open (a coat); None makes a closed tube with its seam at the
    back. lap +1 lifts the theta1 end where it laps over the theta0 end (left over right), -1 the other."""
    closed = span is None
    u = np.linspace(0, 1, nu, endpoint=not closed)
    length = z_top - z_hem
    v = np.concatenate([np.linspace(0, 1 - .018 / length, nv - 1), [1.0]])
    if closed:
        th_hem = -math.pi + 2 * math.pi * u
    else:
        a0, a1 = span(np.array(z_hem))
        th_hem = a0 + u * (a1 - a0)
    hem = z_hem + wave * noise2(np.cos(th_hem) * 2.3 + 7, np.sin(th_hem) * 2.3, seed + 11) + .22 * dr.disp(th_hem, z_hem)
    Z = z_top + v[:, None] * (hem[None, :] - z_top)
    if closed:
        TH = np.broadcast_to(th_hem, Z.shape).copy()
    else:
        a0, a1 = span(Z)
        TH = a0 + u[None, :] * (a1 - a0)
    X = np.zeros(Z.shape) + extra
    X[-2:] += hem_roll
    if lap and not closed:
        a0, a1 = span(Z)
        over = np.clip((a1 - a0 - 2 * math.pi) / .02, 0, 1)
        if lap > 0:
            X += (thick + .0025) * over * _smooth((TH - (a0 + 2 * math.pi - .085)) / .05)
        else:
            X += (thick + .0025) * over * _smooth(((a1 - 2 * math.pi + .085) - TH) / .05)
    P = dr.at(TH, Z, extra=X, fold=fold)
    kk = _cloth_k(dr, TH, Z, z_hem, seed) * k
    _sheet(part, P, thick, base, slot, _axis(), k=kk, closed=closed, rims=rims)
    return TH, Z, P


def _band(part, dr, z0, z1, extra, thick, base, slot, nu=64, k=1.0, rows=3, cap=.9):
    """A closed band around a drape (waistband, belt, sash, cuff), without the drape's folds."""
    th = np.linspace(-math.pi, math.pi, nu, endpoint=False)
    Z = np.linspace(z1, z0, rows)[:, None] + 0 * th[None, :]
    P = dr.at(th[None, :] + 0 * Z, Z, extra=extra, fold=0.)
    return _sheet(part, P, thick, base, slot, _axis(), k=k, closed=True, cap=cap)


def _patch(part, dr, th0, th1, z0, z1, extra, thick, base, slot, nu=7, nv=5, k=1.0, bulge=0., fold=1.0, cap=.9):
    """A piece laid on a garment between two angles and two heights: a pocket, a flap, an apron's bib."""
    TH, Z = np.meshgrid(np.linspace(th0, th1, nu), np.linspace(z1, z0, nv))
    b = bulge * np.sin(math.pi * (TH - th0) / (th1 - th0)) * np.sin(math.pi * (Z - z0) / (z1 - z0))
    P = dr.at(TH, Z, extra=extra + b, fold=fold)
    return _sheet(part, P, thick, base, slot, _axis(), k=k, cap=cap)


def _strip(part, dr, path_th, path_z, width, extra, thick, base, slot, k=1.0, fold=1.0, cols=3, crown=.0015, cap=.9, ends=True):
    """A strap, ribbon or scarf end lying on a garment along a (theta, z) path: its edges are set off
    the centreline across the surface, so it stays flat on curved cloth."""
    C = dr.at(path_th, path_z, extra=extra, fold=fold)
    N = dr.normal(path_th, path_z, extra, fold)
    T = np.gradient(C, axis=0)
    S = np.cross(N, T)
    S /= np.linalg.norm(S, axis=-1, keepdims=True) + 1e-12
    w = np.broadcast_to(np.asarray(width, np.float64), (len(C),))
    a = np.linspace(-1, 1, cols)
    P = C[:, None, :] + S[:, None, :] * (a[None, :, None] * w[:, None, None] / 2) + N[:, None, :] * (crown * (1 - a ** 2))[None, :, None]
    if np.ndim(k) == 1:
        k = np.asarray(k, np.float64)[:, None] + 0 * a[None, :]  # one shade per path point
    return _sheet(part, P, thick, base, slot, lambda Pp: np.broadcast_to(N[:, None, :], Pp.shape), k=k, cap=cap,
                  rims=True if ends else (False, False, True, True))


def _top(part, body, dr, base, slot, *, thick=.006, z_bot=1.0, neck_front=1.40, neck_back=1.47, neck_shape=2.2,
         fronts=None, k=1.0, nv=16, nn=13, ms=5, nt=8, seed=0):
    """A sleeveless top on a torso drape: front and back panels joined at the side seams, armholes above
    the armpit, straps over the shoulders and a neckline. fronts=None is one front panel; otherwise
    (right_edge(z), left_edge(z), lift(theta, z, side)) splits it for a coat or a wrap robe: the theta of
    each panel's front edge, and the lift that raises the panel lapping over (side +1 is the right panel,
    -1 the left). Returns the borders for trims."""
    n = dr.n
    e = 2.0 / n
    z_pit, z_sh = PIT[body], SHOULDER[body]
    th_neck, th_arm = _angles(body, dr)
    sb = np.linspace(th_neck, th_arm, ms)

    def span(z):
        t = np.clip((np.asarray(z, np.float64) - z_pit) / (z_sh - z_pit), 0, 1)
        return th_arm + (math.pi / 2 - th_arm) * (1 - t) ** 2

    def neck(th, z_c):
        return z_c + (z_sh - z_c) * np.clip(np.abs(th) / th_neck, 0, 1) ** neck_shape

    def grid(lo, hi, top_th, top_z):
        v = np.linspace(0, 1, nv)[:, None]
        Z = z_bot + v * (top_z[None, :] - z_bot)
        w0 = np.linspace(0, 1, len(top_th))[None, :]
        w1 = ((top_th - lo(top_z)) / (hi(top_z) - lo(top_z)))[None, :]
        return lo(Z) + (w0 + v * (w1 - w0)) * (hi(Z) - lo(Z)), Z

    def masks(TH, Z, top_th, border_lo, border_hi):
        # Rows run up from the hem (row 0) to the neckline and strap bases (the last row): the hem is closed
        # all along, the top only along the neckline (the straps carry on from the strap bases).
        top = (np.abs(top_th[:-1]) < th_neck + 1e-6) & (np.abs(top_th[1:]) < th_neck + 1e-6)
        lo = (Z[1:, 0] > z_pit + 1e-4) if border_lo == 'arm' else True
        hi = (Z[1:, -1] > z_pit + 1e-4) if border_hi == 'arm' else True
        return (True, top if top.any() else False, lo, hi)

    kk = lambda TH, Z: k * _cloth_k(dr, TH, Z, 0., seed, 3.0)
    out = _away((0, 0, 1.25))
    mid = np.linspace(-th_neck, th_neck, nn)
    back_th = np.concatenate([-sb[::-1], mid[1:-1], sb])
    back_z = np.where(np.abs(back_th) < th_neck - 1e-9, neck(back_th, neck_back), z_sh)
    TB, ZB = grid(lambda z: -span(z), span, back_th, back_z)
    TB = math.pi - TB
    PB, QB = _sheet(part, dr.at(TB, ZB), thick, base, slot, out, k=kk(TB, ZB), rims=masks(TB, ZB, back_th, 'arm', 'arm'))
    fronts_out = []
    if fronts is None:
        top_z = np.where(np.abs(back_th) < th_neck - 1e-9, neck(back_th, neck_front), z_sh)
        TF, ZF = grid(lambda z: -span(z), span, back_th, top_z)
        PF, QF = _sheet(part, dr.at(TF, ZF), thick, base, slot, out, k=kk(TF, ZF), rims=masks(TF, ZF, back_th, 'arm', 'arm'))
        left_f, right_f = (PF[-1, :ms], QF[-1, :ms]), (PF[-1, -ms:], QF[-1, -ms:])
        fronts_out = [(PF, QF, TF, ZF)]
        neck_line = PF[-1, ms - 1:len(back_th) - ms + 1]
    else:
        right_edge, left_edge, lift = fronts
        pieces = {}
        for side in (1, -1):
            edge = right_edge if side > 0 else left_edge
            e_top = float(edge(z_sh))
            if side * e_top < th_neck - .01:
                part_th = np.linspace(e_top, side * th_neck, nn // 2 + 1)[:-1]
                top_th = np.concatenate([part_th, sb]) if side > 0 else np.concatenate([-sb[::-1], part_th[::-1]])
            else:
                top_th = sb.copy() if side > 0 else -sb[::-1]
            top_z = np.where(np.abs(top_th) < th_neck - 1e-9, neck(top_th, neck_front), z_sh)
            if side > 0:
                TF, ZF = grid(right_edge, span, top_th, top_z)
                m = masks(TF, ZF, top_th, 'edge', 'arm')
            else:
                TF, ZF = grid(lambda z: -span(z), left_edge, top_th, top_z)
                m = masks(TF, ZF, top_th, 'arm', 'edge')
            PF, QF = _sheet(part, dr.at(TF, ZF, extra=lift(TF, ZF, side)), thick, base, slot, out, k=kk(TF, ZF), rims=m)
            pieces[side] = (PF, QF, TF, ZF)
        right_f = (pieces[1][0][-1, -ms:], pieces[1][1][-1, -ms:])
        left_f = (pieces[-1][0][-1, :ms], pieces[-1][1][-1, :ms])
        fronts_out = [pieces[1], pieces[-1]]
        neck_line = None
    # Straps: each strap column keeps its lateral position y over the top of the shoulder.
    zz = np.linspace(z_sh, 1.62, 400)
    hh = np.minimum.accumulate(dr.axes(zz)[0])
    straps = []
    for F, B, th_f in ((right_f[0], PB[-1, -ms:], sb), (left_f[0], PB[-1, :ms], -sb[::-1])):
        t = np.linspace(0, 1, nt)[:, None]
        TH = th_f[None, :] + t * (np.sign(th_f)[None, :] * math.pi - 2 * th_f[None, :])
        h = np.abs(F[:, 1])[None, :] / np.maximum(np.abs(np.sin(TH)), 1e-6) ** e
        S = dr.at(TH, np.interp(-h, -hh, zz))
        S[0], S[-1] = F, B
        straps.append(_sheet(part, S, thick, base, slot, out, k=k, rims=(False, False, True, True)))
    def over(y, count=9, side=1):
        """(theta, z) over one shoulder at lateral distance y, from the front seam to the back seam."""
        th_f = float(np.arcsin(min(1.0, y / float(dr.axes(z_sh)[0])) ** (n / 2)))
        t = np.linspace(0, 1, count)
        TH = th_f + t * (math.pi - 2 * th_f)
        Z = np.interp(-(y / np.maximum(np.abs(np.sin(TH)), 1e-6) ** e), -hh, zz)
        Z[0] = Z[-1] = z_sh
        return side * TH, Z

    return dict(back=(PB, QB, TB, ZB), fronts=fronts_out, straps=straps, neck_line=neck_line, th_neck=th_neck,
                th_arm=th_arm, z_sh=z_sh, z_pit=z_pit, span=span, over=over, ms=ms)


def _angles(body, dr):
    """The front angles of the straps' neck-side and arm-side edges where they leave the panels."""
    hw_sh = float(dr.axes(SHOULDER[body])[0])
    return tuple(float(np.arcsin(min(1.0, y / hw_sh) ** (dr.n / 2))) for y in STRAP[body])


def _path(*legs):
    """Joins (theta, z) legs into one path, dropping the repeated joint points."""
    th = np.concatenate([np.asarray(legs[0][0])] + [np.asarray(l[0])[1:] for l in legs[1:]])
    z = np.concatenate([np.asarray(legs[0][1])] + [np.asarray(l[1])[1:] for l in legs[1:]])
    return th, z


def _edge_mid(P, Q):
    return (np.asarray(P) + np.asarray(Q)) / 2


def _piping(part, pts, r, base, slot, k=1.0, closed=False, cap=.9):
    """A rolled binding along a cloth edge (pts are the edge's midline)."""
    pts = np.asarray(pts, np.float64)
    if closed:
        pts = np.concatenate([pts, pts[:1]])
    _limb(part, pts, r, base, slot, 6, k, cap)


def _neck_loop(top, ms):
    """The midline of a top's whole neckline: front, right strap, back, left strap."""
    PB, QB = top['back'][:2]
    (SR, SRq), (SL, SLq) = top['straps']
    front = [f for f in top['fronts']]
    if len(front) == 1:
        PF, QF = front[0][:2]
        f_line = _edge_mid(PF[-1, ms - 1:PF.shape[1] - ms + 1], QF[-1, ms - 1:QF.shape[1] - ms + 1])
    else:
        f_line = np.zeros((0, 3))
    r_side = _edge_mid(SR[:, 0], SRq[:, 0])
    b_line = _edge_mid(PB[-1, ms - 1:PB.shape[1] - ms + 1], QB[-1, ms - 1:QB.shape[1] - ms + 1])[::-1]
    l_side = _edge_mid(SL[:, -1], SLq[:, -1])[::-1]
    return np.concatenate([f_line, r_side[1:], b_line[1:], l_side[1:-1]])


def _arm_loop(top, side, ms):
    """The midline of one armhole: front panel edge, strap edge, back panel edge."""
    PB, QB = top['back'][:2]
    zp = top['z_pit']
    front = top['fronts'][0] if len(top['fronts']) == 1 else top['fronts'][0 if side > 0 else 1]
    PF, QF, _, ZF = front
    col = -1 if side > 0 else 0
    rows = ZF[:, col] >= zp - 1e-4
    f_edge = _edge_mid(PF[rows, col], QF[rows, col])
    S, Sq = top['straps'][0 if side > 0 else 1]
    scol = -1 if side > 0 else 0
    s_edge = _edge_mid(S[:, scol], Sq[:, scol])
    brow = top['back'][3][:, col] >= zp - 1e-4
    b_edge = _edge_mid(PB[brow, col], QB[brow, col])[::-1]
    return np.concatenate([f_edge, s_edge[1:], b_edge[1:]])


# ---------------------------------------------------------------- head: hair, caps, hats, beards

def _skull(head, phi, psi, extra=0.):
    (cx, cy, cz), fr, bk, hw, up = head
    c, s = np.cos(phi), np.sin(phi)
    a = np.where(c >= 0, fr, bk) + extra
    return np.stack([cx + a * np.cos(psi) * c, cy + (hw + extra) * np.cos(psi) * s, cz + (up + extra) * np.sin(psi)], -1)


def _scalp(part, head, base, slot, bottom, lift, *, thick=.012, nu=56, nv=18, psi_top=1.36, close_top=True, strands=0,
           strand=0., flare=0., inward=0., ends=0., seed=0, k=1.0, cap=.9, shade=None):
    """A shell over the skull: hair, a knitted cap, a headscarf, a helmet, a hood. Each column at azimuth
    phi (column 0 at the back) runs from the crown over the skull down to its own bottom height bottom(phi);
    below the skull's widest line it falls straight (hair) or flares (a hood onto the shoulders). lift(phi,
    psi) is the shell's height off the skull; strands cuts grooves along the fall (hair, knit ribs)."""
    (cx, cy, cz), fr, bk, hw, up = head
    phi = np.linspace(-math.pi, math.pi, nu, endpoint=False)
    zb = bottom(phi) + ends * noise2(np.cos(phi) * 3 + 2, np.sin(phi) * 3, seed + 21)
    P = np.zeros((nv, nu, 3))
    PS = np.zeros((nv, nu))
    for j, (ph, z_end) in enumerate(zip(phi, zb)):
        psi_end = math.asin(min(1.0, (z_end - cz) / up)) if z_end > cz else 0.0
        arc = np.linspace(psi_top, psi_end, 40)
        pts = _skull(head, ph, arc, lift(ph, arc))
        psis = arc
        if z_end < cz - 1e-4:
            dz = np.linspace(0, cz - z_end, 24)[1:]
            eq = pts[-1]
            radial = np.array([eq[0] - cx, eq[1] - cy, 0.])
            radial /= np.linalg.norm(radial) + 1e-9
            tip = np.clip((dz - (cz - z_end - .025)) / .025, 0, 1)
            drop = eq + radial * (flare * dz - inward * tip)[:, None] - np.outer(dz, (0, 0, 1.))
            pts = np.concatenate([pts, drop])
            psis = np.concatenate([psis, -dz / up])
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(seg)]) / max(seg.sum(), 1e-9)
        tgt = np.linspace(0, 1, nv)
        P[:, j] = np.stack([np.interp(tgt, s, pts[:, a]) for a in range(3)], -1)
        PS[:, j] = np.interp(tgt, s, psis)
    groove = np.zeros((nv, nu))
    if strands:
        wob = 1.3 * noise2(np.cos(phi) * 2 + 5, np.sin(phi) * 2, seed + 7)
        g = np.abs(np.sin(strands * phi / 2 + wob)) * 2 - 1
        fade = np.clip((psi_top - PS) / .35, 0, 1)
        groove = strand * g[None, :] * fade
        radial = P - np.array([cx, cy, cz])
        radial /= np.linalg.norm(radial, axis=-1, keepdims=True)
        P = P + radial * groove[..., None]
    kk = k * (1 + (6.0 * groove if strands else 0)) * (1 + .05 * noise2(phi[None, :] * 4 + 0 * PS, PS * 6, seed + 9))
    if shade is not None:
        kk = kk * shade(P, PS)
    PQ = _sheet(part, P, thick, base, slot, _away((cx, cy, cz - .03)), k=kk, closed=True, close_top=close_top, cap=cap)
    return PQ, phi, PS


def _coil(part, centre, axis, r, base, slot, turns=2.6, rad=.016, k=1.0, seed=0, height=None, sides=7):
    """A coiled bun or knot: a tapering rope wound round itself, filled at the centre."""
    a, b = frame(axis)
    axis = np.asarray(axis, np.float64) / np.linalg.norm(axis)
    t = np.linspace(0, 1, 64)
    ang = t * turns * 2 * math.pi + seed
    ring = r * (1 - .7 * t)
    h = (height if height is not None else r * .55) * np.sin(t * math.pi * .5)
    pts = np.asarray(centre) + ring[:, None] * (np.cos(ang)[:, None] * a + np.sin(ang)[:, None] * b) + h[:, None] * axis
    radii = rad * (.75 + .25 * np.sin(np.minimum(t * 9, math.pi))) * (1 - .35 * t)
    _limb(part, pts, radii, base, slot, sides, k * (1 + .08 * np.sin(t * 40)))
    _shell(part, np.asarray(centre) + axis * r * .25, (r * .55, r * .55, r * .5), base, slot, k * .85, 10, 6, R=_basis(axis, a))


def _beard(part, base, slot, length=.04, thick=.014, nu=34, nv=16, seed=0, k=1.0, top=1.646):
    """A full beard and moustache over the Mannequin's jaw (Manny), hanging length below the chin. Hair grows out of
    the skin, so the beard lies close along its top edge (the moustache under the nose, the cheek line rising to the
    sideburns) and gains its body toward the chin, rounding in again under it: a beard standing its full depth off
    the face at the top edge reads as a mask. The outer face is combed into wavy locks, a crease marks the mouth, and
    the inner face follows the jaw itself a little under the skin (offset along the locks it would fold)."""
    dr = Drape(JAW, n=2.0, capped=False)
    phi = np.linspace(-1.62, 1.62, nu)
    a = np.abs(phi)
    z_top = np.interp(a, [0, .3, .5, .8, 1.15, 1.4, 1.62], [top, top - .004, 1.628, 1.638, 1.658, 1.674, 1.69])
    z_bot = np.interp(a, [0, .5, 1.0, 1.35, 1.62], [1.565 - length, 1.57 - length * .8, 1.585 - length * .4, 1.605, 1.632])
    z_bot = z_bot + .006 * noise2(phi * 5, 1.0, seed + 2)
    v = np.linspace(0, 1, nv)[:, None]
    Z = z_top[None, :] + v * (z_bot - z_top)[None, :]
    TH = np.broadcast_to(phi, Z.shape)
    full = np.interp(a, [0, .4, 1.0, 1.62], [thick + .004, thick, thick * .8, thick * .45])[None, :]
    body = .2 + .8 * _smooth(v / .4) - .3 * _smooth((v - .8) / .2)
    mid = np.exp(-(phi / .45) ** 2)[None, :]
    mouth = mid * np.exp(-((Z - 1.618) / .007) ** 2)
    lip = mid * np.exp(-((Z - (top - .013)) / .009) ** 2)
    locks = np.abs(np.sin(phi * 13 + 1.7 * noise2(phi * 2, 4.0, seed) + 2.2 * noise2(phi * 3 + 7, Z * 40, seed + 4))) * 2 - 1
    off = full * body + .0035 * lip - .0045 * mouth + .0012 + locks * (.0012 + .0022 * v)
    P = dr.at(TH, Z, extra=off)
    kk = k * (1 + .2 * locks * (.4 + .6 * v)) * (.88 + .12 * (1 - v)) * (1 - .3 * mouth)
    _sheet(part, P, 0., base, slot, _away((0, 0, 1.61)), k=kk, cap=.9, under=dr.at(TH, Z, extra=-.004))


def _hat(part, head, base, slot, band_z, brim_r, crown_h, droop, *, tilt=0., thick=.005, nu=60, braid=0., crown_round=.5,
         k=1.0, seed=0, brim_wave=0., crease=0.):
    """A brimmed hat: the inner band fits the skull at band_z (elliptical like the head), the crown rises
    crown_h above it, the brim runs out to brim_r (round) and droops. braid cuts the rows of a straw braid
    or the stitch lines of a cloth brim; crease dents a cloth crown along its top."""
    (cx, cy, cz), fr, bk, hw, up = head
    psi = math.asin(min(.99, (band_z - cz) / up))
    rx_f, rx_b, ry = (fr * math.cos(psi) + .008, bk * math.cos(psi) + .008, hw * math.cos(psi) + .008)
    phi = np.linspace(-math.pi, math.pi, nu, endpoint=False)
    c, s = np.cos(phi), np.sin(phi)
    rx = np.where(c >= 0, rx_f, rx_b)
    r_band = 1 / np.sqrt((c / rx) ** 2 + (s / ry) ** 2)          # the head's ellipse at the band
    nb, nc, nt = 9, 6, 5
    rows = []
    # Brim: from its outer edge in to the band.
    for i in range(nb):
        t = i / (nb - 1)
        r = brim_r + (r_band - brim_r) * t
        z = band_z - droop * (1 - t) ** 1.6 + brim_wave * (1 - t) ** 2 * np.sin(3 * phi + seed)
        if braid:
            z = z + braid * .25 * np.sin(2 * math.pi * r / .011)
        rows.append(np.stack([cx + r * c, cy + r * s, z], -1))
    # Crown wall and its top.
    for i in range(1, nc):
        t = i / (nc - 1)
        r = r_band * (1 - .06 * t - crown_round * .25 * t ** 3) + (braid * np.sin(2 * math.pi * t * crown_h / .011) if braid else 0)
        rows.append(np.stack([cx + r * c, cy + r * s, band_z + crown_h * t + 0 * phi], -1))
    for i in range(1, nt):
        t = i / nt
        r = r_band * (1 - .06 - crown_round * .25) * (1 - t ** 1.5 * .9)
        z = band_z + crown_h + crown_h * crown_round * .35 * math.sin(t * math.pi / 2) - crease * np.cos(phi) ** 2 * math.sin(t * math.pi)
        rows.append(np.stack([cx + r * c, cy + r * s, z + 0 * phi], -1))
    P = np.array(rows[::-1])   # crown centre first, so close_top caps it
    if tilt:
        R = _rot((0, 1, 0), tilt)
        P = (P - (cx, cy, band_z)) @ R.T + (cx, cy, band_z)
    kk = k * np.ones(P.shape[:2])
    if braid:
        rr = np.linalg.norm(P[..., :2] - (cx, cy), axis=-1)
        kk = kk * (.9 + .1 * np.sin(2 * math.pi * (rr + P[..., 2]) / .011)) * (1 + .06 * noise2(phi[None, :] * 3 + 0 * rr, rr * 30, seed))
    return _sheet(part, P, thick, base, slot, _hat_out(cx, cy, band_z), k=kk, closed=True, close_top=True)


def _hat_out(cx, cy, z0):
    """Outside of a hat: up on the brim and the crown's top, away from the head on the crown wall."""
    def out(P):
        d = P - np.array([cx, cy, z0 - .06])
        return d
    return out


# ---------------------------------------------------------------- lower garments (pelvis)

def _coat_span(zs, overlaps):
    """A coat skirt's front: overlaps (theta) per height, positive where the panels lap, negative open."""
    def span(z):
        ov = np.interp(z, zs, overlaps)
        return -ov / 2, 2 * math.pi + ov / 2
    return span


def _torso_drape(body, ease, **kw):
    return Drape(TORSO[body], ease=ease, n=2.4, **kw)


def _bow(part, dr, theta, z, extra, base, slot, loop=.045, tail=.2, width=.03, k=1.0, seed=0):
    """A tied bow on a garment: knot, two loops and two tails hanging from it."""
    c = dr.at(theta, z, extra=extra + .006, fold=0.)
    nrm = dr.normal(theta, z, extra, 0.)
    side = np.cross((0, 0, 1.), nrm)
    side /= np.linalg.norm(side)
    _shell(part, c, (.012, .016, .014), base, slot, k * .9, 10, 6, R=_basis(nrm))
    for s in (-1, 1):
        a = np.linspace(.15, 2 * math.pi - .15, 14)
        ctr = c + side * s * loop * .8 + nrm * .006
        pts = ctr + side[None, :] * (s * np.cos(a)[:, None] * loop * .8) + np.array([0, 0, 1.])[None, :] * (np.sin(a)[:, None] * loop * .45)
        _limb(part, pts, np.full(len(pts), .0075), base, slot, 6, k)
        ths = theta + s * np.linspace(.02, .09, 8)
        zs = z - np.linspace(.01, tail, 8)
        _strip(part, dr, ths, zs, width * np.linspace(1, .8, 8), extra + .004, .0035, base, slot, k, fold=1.0)


def _satchel(part, dr, theta, z_top, base, slot, k=1.0):
    """A canvas satchel hanging against the skirt behind the hand, with a flap and a gold clasp."""
    c0 = dr.at(theta, z_top - .095, extra=0., fold=0.)
    nrm = dr.normal(theta, z_top - .095, 0., 0.)
    nrm[2] = 0
    nrm /= np.linalg.norm(nrm)
    R = _basis(nrm)
    c = c0 + nrm * .036
    _box(part, c, (.03, .1, .085), base, slot, .014, k * .9, R)
    # The flap folds over the top and down the outer face; the clasp holds it.
    flap = Part('tmp', part.slots)
    _plate(flap, (0, 0, 0), np.eye(3), .205, .1, .006, .004, base, slot, k=k, nu=5, nv=4, round_=.5)
    _merge(part, flap, R, c + nrm * .032 + np.array([0, 0, .04]))
    _box(part, c + nrm * .040 + np.array([0, 0, .0]), (.004, .016, .012), GOLD, 'CN_Gold', .003, 1.0, R, cap=None)
    # Strap rings at the top corners.
    t = np.cross((0, 0, 1.), nrm)
    for s in (-1, 1):
        _torus(part, c + t * s * .095 + np.array([0, 0, .09]), .008, .0022, _tone(GOLD, 1.0, None), 'CN_Gold', 10, 5, axis='z')


def skirt_satchel():
    """Petra Lune: a long red A-line skirt and the black canvas satchel she carries the Ledger in."""
    p = Part('SM_CP_G_SkirtSatchel', ('CN_Cloth', 'CN_Gold'))
    dr = Drape(((1.085, .142, .104, -.098), (1.04, .152, .104, -.102), (.98, .176, .106, -.122), (.92, .192, .110, -.138),
                (.86, .198, .118, -.146), (.78, .201, .130, -.152), (.70, .206, .146, -.160), (.55, .232, .176, -.184),
                (.35, .264, .214, -.216), (.18, .288, .240, -.240), (.08, .298, .250, -.248)),
               folds=11, amp=.024, fold_top=.88, fold_low=.08, wrinkle=.0012, seed=31)
    _skirt(p, dr, RED, 'CN_Cloth', 1.075, .085, seed=31)
    _band(p, dr, 1.035, 1.088, .0035, .006, RED, 'CN_Cloth', k=.92)
    for z in (1.072, 1.051):
        _button(p, dr.at(-math.pi / 2, z, extra=.0098, fold=0.), dr.normal(-math.pi / 2, z, .0098, 0.), .0055, GOLD, 'CN_Gold', k=1.0, cap=None)
    _satchel(p, dr, -2.45, .985, CHARCOAL, 'CN_Cloth')
    # The strap's two ends come down over the waistband from the blouse (BlouseStrap) to the bag's rings.
    for th0, th1 in ((-2.18, -2.21), (-2.68, -2.66)):
        n = 7
        _strip(p, dr, np.linspace(th0, th1, n), np.linspace(1.13, .992, n), .03, .0095, .004, CHARCOAL, 'CN_Cloth', fold=0.)
    return _fit(p)


def _apron_skirt(name, apron, apron_hem, skirt_hem, seed, pocket='patch'):
    """A gathered black skirt under a front apron tied at the back (Orsolya's white, Rhea's gold)."""
    p = Part(name, ('CN_Cloth', 'CN_Gold'))
    dr = Drape(((1.085, .142, .104, -.098), (1.04, .155, .106, -.104), (.98, .178, .110, -.126), (.92, .194, .116, -.142),
                (.86, .199, .126, -.150), (.78, .203, .142, -.160), (.72, .207, .156, -.170), (.55, .240, .190, -.198),
                (.35, .278, .232, -.236), (.18, .305, .262, -.262), (.08, .316, .272, -.272)),
               folds=13, amp=.026, fold_top=.9, fold_low=.08, gathers=46, gather_amp=.0032, gather_top=1.075,
               wrinkle=.001, seed=seed, spare=.014)
    _skirt(p, dr, CHARCOAL, 'CN_Cloth', 1.075, skirt_hem, nu=60, nv=18, seed=seed)
    _band(p, dr, 1.035, 1.088, .0075, .006, CHARCOAL, 'CN_Cloth', k=.85)
    # The apron hangs flatter than the skirt, standing off its fold ridges.
    nv, nu = 13, 20
    Z = np.linspace(1.07, apron_hem, nv)[:, None] + np.zeros((1, nu))
    half = np.interp(Z, [apron_hem, 1.07], [.92, 1.15])
    TH = half * np.linspace(-1, 1, nu)[None, :]
    X = .004 + .4 * dr.depth(Z) + .0025 + dr.gather(Z) + .0015 * np.sin(TH * 7 + seed)
    P = dr.at(TH, Z, extra=X, fold=.6)
    _sheet(p, P, .004, apron, 'CN_Cloth', _axis(), k=_cloth_k(dr, TH, Z, apron_hem, seed + 1, 3.0))
    _band(p, dr, 1.04, 1.072, .012, .004, apron, 'CN_Cloth', k=.95)
    _bow(p, dr, math.pi, 1.056, .016, apron, 'CN_Cloth', seed=seed)
    if pocket == 'patch':
        z0, z1 = apron_hem + .36, apron_hem + .5
        ex = float(.004 + .4 * dr.depth(z1) + .0025) + .0045
        _patch(p, dr, .2, .62, z0, z1, ex, .003, apron, 'CN_Cloth', 7, 5, k=.97, bulge=.004, fold=.6)
        # A trowel's black handle and gold ferrule stand out of the pocket.
        c = dr.at(.45, z1 - .02, extra=ex + .012, fold=.6)
        _limb(p, [c - (0, 0, .03), c + (.004, .01, .085)], [.009, .010], CHARCOAL, 'CN_Cloth', 8, .9)
        _limb(p, [c - (0, 0, .045), c - (0, 0, .025)], [.0105, .0105], GOLD, 'CN_Gold', 8, 1.0, None)
    else:
        z0, z1 = apron_hem + .1, apron_hem + .26
        ex = float(.004 + .4 * dr.depth(z1) + .0025) + .0045
        _patch(p, dr, -.5, .5, z0, z1, ex, .003, apron, 'CN_Cloth', 9, 5, k=.95, bulge=.006, fold=.6)
        for s in (-1, 1):
            _strip(p, dr, np.full(4, s * .5), np.linspace(z1, z0, 4), .012, ex + .003, .002, apron, 'CN_Cloth', .85, fold=.6)
            # Gold-toned rivets where the pocket takes the strain.
            q = dr.at(s * .5, z1 - .01, extra=ex + .0045, fold=.6)
            _button(p, q, dr.normal(s * .5, z1 - .01, ex + .0045, .6), .0042, GOLD, 'CN_Gold', h=.0022, sides=8, cap=None)
    return _fit(p)


def apron_skirt_white():
    """Orsolya Fenn: a long black skirt under a white gardening apron with a trowel in its pocket."""
    return _apron_skirt('SM_CP_G_ApronSkirtWhite', WHITE, .24, .085, 41)


def apron_skirt_gold():
    """Rhea Sato: a mid-calf black skirt under a knee-length gold work apron with a wide front pocket."""
    return _apron_skirt('SM_CP_G_ApronSkirtGold', GOLD_DEEP, .46, .3, 47, pocket='kangaroo')


def skirt_gold():
    """Sefa Moreno: a tiered gold skirt, each tier gathered under the one above, a red sash and a purse."""
    p = Part('SM_CP_G_SkirtGold', ('CN_Cloth', 'CN_Gold'))
    tiers = (
        (((1.085, .142, .104, -.098), (1.0, .172, .108, -.122), (.92, .195, .118, -.142), (.85, .200, .130, -.152), (.69, .205, .152, -.166)),
         1.075, .70, 40, .003, 15, .008),
        (((.73, .199, .146, -.160), (.60, .228, .172, -.182), (.40, .262, .212, -.214)), .725, .41, 54, .006, 17, .010),
        (((.43, .256, .205, -.208), (.25, .292, .246, -.244), (.085, .318, .272, -.266)), .425, .085, 66, .008, 19, .012),
    )
    first = None
    for i, (rows, top, hem, gathers, gamp, folds, amp) in enumerate(tiers):
        dr = Drape(rows, folds=folds, amp=amp, fold_top=top - .02, fold_low=hem, gathers=gathers, gather_amp=gamp,
                   gather_top=top, wrinkle=.001, seed=60 + i, spare=.012 if i == 0 else .003)
        _skirt(p, dr, GOLD_DEEP, 'CN_Cloth', top, hem, nu=52, nv=(10, 8, 9)[i], seed=60 + i, k=(1.0, .96, .92)[i])
        first = first or dr
    _band(p, first, 1.0, 1.092, .0068, .005, RED, 'CN_Cloth', k=.95, rows=4)
    _coil(p, first.at(-.85, 1.046, extra=.016, fold=0.), first.normal(-.85, 1.046, 0., 0.), .016, RED, 'CN_Cloth', 1.6, .009)
    for s in (0, 1):
        n = 8
        _strip(p, first, -.85 + (s - .5) * .09 + np.linspace(0, .05 * (s - .5), n), np.linspace(1.035, .76 + .04 * s, n), .045,
               .013, .0035, RED, 'CN_Cloth', .9 - .05 * s, fold=.5)
    # A small coin purse on a cord at the right hip, in front of the hand.
    c = first.at(.62, .935, extra=.03, fold=0.)
    nrm = first.normal(.62, .935, 0., 0.)
    _shell(p, c, (.018, .034, .036, .018, .03), CHARCOAL, 'CN_Cloth', .9, 12, 7, R=_basis(nrm))
    _limb(p, [c + (0, 0, .03), first.at(.6, 1.0, extra=.012, fold=0.)], .0025, GOLD, 'CN_Gold', 5, 1.0, None)
    _torus(p, c + (0, 0, .026), .012, .0025, _tone(GOLD, 1.0, None), 'CN_Gold', 12, 5, axis='z')
    return _fit(p)


def tunic_skirt():
    """Tamsin: the knee-length lower half of her light-blue tunic and a white belt with a gold buckle."""
    p = Part('SM_CP_G_TunicSkirt', ('CN_Cloth', 'CN_Gold'))
    dr = Drape(((1.085, .150, .112, -.106), (1.03, .166, .113, -.114), (.97, .186, .114, -.132), (.91, .198, .118, -.146),
                (.84, .203, .128, -.154), (.74, .207, .144, -.162), (.62, .222, .162, -.176), (.50, .238, .180, -.190)),
               folds=9, amp=.016, fold_top=.86, fold_low=.5, wrinkle=.001, seed=71)
    _skirt(p, dr, BLUE, 'CN_Cloth', 1.075, .5, nu=56, nv=16, seed=71)
    _band(p, dr, 1.02, 1.08, .0062, .005, WHITE_PURE, 'CN_Cloth', k=.95)
    c = dr.at(0., 1.05, extra=.0115, fold=0.)
    nrm = dr.normal(0., 1.05, .0115, 0.)
    R = _basis(nrm)
    _box(p, c + nrm * .002, (.003, .02, .016), GOLD, 'CN_Gold', .003, 1.0, R, cap=None)
    _box(p, c + nrm * .0045, (.0015, .011, .008), WHITE_PURE, 'CN_Cloth', .001, .9, R)
    return _fit(p)


def robe_skirt():
    """Old Wen: an ankle-length white robe below a wide black sash knotted at the front."""
    p = Part('SM_CP_G_RobeSkirt', ('CN_Cloth',))
    dr = Drape(((1.085, .161, .123, -.117), (1.04, .171, .124, -.121), (.98, .182, .126, -.132), (.92, .196, .128, -.146),
                (.86, .201, .134, -.154), (.78, .204, .144, -.160), (.72, .208, .155, -.168), (.55, .240, .188, -.196),
                (.35, .276, .228, -.230), (.18, .300, .256, -.254), (.085, .310, .266, -.262)),
               folds=12, amp=.026, fold_top=.88, fold_low=.085, wrinkle=.0012, seed=81, spare=.009)
    _skirt(p, dr, IVORY, 'CN_Cloth', 1.08, .085, seed=81)
    _band(p, dr, .995, 1.09, .006, .006, CHARCOAL, 'CN_Cloth', k=.9, rows=4)
    knot = dr.at(-.32, 1.04, extra=.02, fold=0.)
    _shell(p, knot, (.022, .03, .026), CHARCOAL, 'CN_Cloth', .85, 12, 7, R=_basis(dr.normal(-.32, 1.04, 0., 0.)))
    for s, length in ((-1, .3), (1, .24)):
        n = 9
        _strip(p, dr, -.32 + s * .035 + np.linspace(0, s * .06, n), np.linspace(1.02, 1.02 - length, n), np.linspace(.05, .06, n),
               .02, .004, CHARCOAL, 'CN_Cloth', .9, fold=.5)
    return _fit(p)


def robe_skirt_tall():
    """The Listener: a floor-length white robe with a gold band at the hem and a gold cord belt."""
    p = Part('SM_CP_G_RobeSkirtTall', ('CN_Cloth', 'CN_Gold'))
    dr = Drape(((1.085, .168, .136, -.123), (1.04, .172, .135, -.126), (.98, .182, .136, -.138), (.92, .189, .136, -.150),
                (.86, .194, .140, -.155), (.78, .199, .150, -.162), (.72, .204, .160, -.170), (.55, .238, .192, -.198),
                (.35, .272, .230, -.230), (.18, .296, .256, -.252), (.035, .310, .268, -.262)),
               folds=12, amp=.03, fold_top=.86, fold_low=.035, wrinkle=.0012, seed=91, spare=.008)
    _skirt(p, dr, WHITE_PURE, 'CN_Cloth', 1.08, .035, nv=21, seed=91, k=.96)
    th = np.linspace(-math.pi, math.pi, 64, endpoint=False)
    for z0, z1 in ((.05, .085), (.1, .108)):
        Z = np.array([[z1], [z0]]) + 0 * th[None, :]
        P = dr.at(th[None, :] + 0 * Z, Z, extra=.0028)
        _sheet(p, P, .002, GOLD, 'CN_Gold', _axis(), k=1.0, closed=True, cap=None)
    # A cord belt: two turns of gold rope, knotted at the front, tassels hanging.
    for i, z in enumerate((1.05, 1.032)):
        ring = dr.at(th, z + .004 * np.sin(th * 2 + i), extra=.0075, fold=0.)
        _limb(p, np.concatenate([ring, ring[:1]]), .0055, GOLD, 'CN_Gold', 6, 1.0 - .05 * i, None)
    knot = dr.at(.18, 1.04, extra=.014, fold=0.)
    _shell(p, knot, (.012, .015, .014), GOLD, 'CN_Gold', .95, 10, 6, cap=None)
    for s in (-1, 1):
        end = dr.at(.18 + s * .05, .74 + .03 * s, extra=.03, fold=.4)
        _limb(p, [knot, (knot + end) / 2 + (0, 0, -.02), end], .0045, GOLD, 'CN_Gold', 6, .95, None)
        _shell(p, end - (0, 0, .03), (.009, .009, .032, .009, .02), GOLD_DEEP, 'CN_Cloth', .9, 8, 6)
    return _fit(p)


def coat_skirt_black():
    """Kairos: the skirt of a long black wool coat, lapping left over right, gold buttons, vent, flaps."""
    p = Part('SM_CP_G_CoatSkirtBlack', ('CN_Cloth', 'CN_Gold'))
    dr = Drape(((1.075, .156, .120, -.108), (1.0, .168, .118, -.114), (.94, .182, .116, -.130), (.88, .188, .114, -.136),
                (.80, .196, .120, -.142), (.72, .202, .132, -.150), (.60, .224, .158, -.170), (.45, .250, .188, -.194),
                (.32, .268, .208, -.212)),
               folds=7, amp=.022, fold_top=.84, fold_low=.32, wrinkle=.0012, seed=101, spare=.006)
    span = _coat_span([.32, .84, .92, 1.08], [-.34, -.05, .30, .30])
    _skirt(p, dr, CHARCOAL, 'CN_Cloth', 1.075, .32, nu=64, nv=20, thick=.009, span=span, lap=1, seed=101, k=.95)
    for z in (.958, .895):
        lift = .0115
        _button(p, dr.at(0.0, z, extra=lift + .0005), dr.normal(0.0, z, lift), .0095, GOLD, 'CN_Gold', k=1.0, cap=None)
    for s in (-1, 1):
        _patch(p, dr, s * .62, s * 1.32, .885, .935, .0035, .007, CHARCOAL, 'CN_Cloth', 7, 3, k=.85)
        _button(p, dr.at(math.pi + s * .3, 1.045, extra=.0005), dr.normal(math.pi + s * .3, 1.045), .009, GOLD, 'CN_Gold', k=.95, cap=None)
    _patch(p, dr, math.pi - .03, math.pi + .13, .33, .62, .003, .006, CHARCOAL, 'CN_Cloth', 4, 7, k=.8)
    return _fit(p)


def coat_skirt_white():
    """Doctor Ama Okafor: the knee-length skirt of her white coat, right over left, pockets, a half-belt."""
    p = Part('SM_CP_G_CoatSkirtWhite', ('CN_Cloth', 'CN_Lacquer'))
    dr = Drape(((1.075, .144, .108, -.100), (1.0, .170, .110, -.120), (.94, .190, .112, -.138), (.88, .198, .118, -.146),
                (.80, .203, .128, -.152), (.72, .207, .140, -.160), (.60, .225, .160, -.176), (.50, .240, .176, -.190)),
               folds=7, amp=.018, fold_top=.84, fold_low=.5, wrinkle=.001, seed=111, spare=.008)
    span = _coat_span([.5, .82, .9, 1.08], [-.3, -.04, .3, .3])
    _skirt(p, dr, WHITE_COOL, 'CN_Cloth', 1.075, .5, nu=60, nv=16, thick=.006, span=span, lap=-1, seed=111)
    for z in (.955, .89):
        _button(p, dr.at(0.0, z, extra=.0092), dr.normal(0.0, z, .0092), .0075, WHITE_PURE, 'CN_Lacquer', k=.95)
    for s in (-1, 1):
        _patch(p, dr, s * .55, s * 1.05, .77, .905, .0032, .0028, WHITE_COOL, 'CN_Cloth', 7, 5, k=.96)
        _patch(p, dr, s * .55, s * 1.05, .89, .905, .0062, .0022, WHITE_COOL, 'CN_Cloth', 7, 2, k=.9)
    _patch(p, dr, math.pi - .6, math.pi + .6, 1.0, 1.04, .0032, .004, WHITE_COOL, 'CN_Cloth', 9, 3, k=.94, fold=0.)
    for s in (-1, 1):
        _button(p, dr.at(math.pi + s * .5, 1.02, extra=.0075, fold=0.), dr.normal(math.pi + s * .5, 1.02, .0075, 0.), .007, WHITE_PURE, 'CN_Lacquer', k=.95)
    _patch(p, dr, math.pi - .03, math.pi + .1, .5, .68, .0028, .004, WHITE_COOL, 'CN_Cloth', 4, 6, k=.85)
    return _fit(p)


def oilskin_skirt():
    """Dov Pell: the knee-length skirt of a light-blue oilskin, a snapped storm flap, big pocket flaps."""
    p = Part('SM_CP_G_OilskinSkirt', ('CN_Blue', 'CN_Lacquer'))
    dr = Drape(((1.075, .157, .121, -.109), (1.0, .169, .120, -.116), (.94, .183, .119, -.132), (.88, .189, .118, -.138),
                (.80, .197, .124, -.144), (.72, .203, .136, -.152), (.60, .222, .160, -.170), (.47, .242, .184, -.190)),
               folds=5, amp=.016, fold_top=.8, fold_low=.47, wrinkle=.0015, seed=121, spare=.014)
    span = _coat_span([.47, .66, .72, 1.08], [-.22, -.02, .3, .3])
    _skirt(p, dr, BLUE, 'CN_Blue', 1.075, .47, nu=60, nv=15, thick=.007, span=span, lap=1, seed=121)
    n = 12
    zs = np.linspace(1.075, .72, n)
    _strip(p, dr, np.full(n, .02), zs, .05, .0125, .004, BLUE, 'CN_Blue', .95, fold=1.0)
    for z in (.95, .87, .79):
        _button(p, dr.at(.02, z, extra=.0168), dr.normal(.02, z, .0168), .0065, BLACK, 'CN_Lacquer', h=.004, k=1.0)
    for s in (-1, 1):
        _patch(p, dr, s * .6, s * 1.12, .8, .935, .0035, .0035, BLUE, 'CN_Blue', 7, 5, k=.95, bulge=.006)
        _patch(p, dr, s * .58, s * 1.14, .9, .955, .011, .004, BLUE, 'CN_Blue', 7, 3, k=.88)
    return _fit(p)


def work_apron_skirt():
    """Marek Duran: a heavy black canvas work apron to the knee, red ties, tools in its pockets."""
    p = Part('SM_CP_G_WorkApronSkirt', ('CN_Cloth', 'CN_Gold', 'CN_Red'))
    belt = _torso_drape('Manny', .006)
    # The waistband stands clear of the work shirt's tucked hem (WorkApron: ease and blousing reach about 8 mm
    # off the body there), so the shirt goes in under it instead of showing through it.
    _band(p, belt, .965, 1.01, .0035, .006, CHARCOAL, 'CN_Cloth', k=.75)
    dr = Drape(((1.075, .157, .132, -.108), (1.0, .17, .136, -.114), (.92, .184, .140, -.13), (.84, .19, .146, -.136),
                (.72, .196, .156, -.146), (.60, .2, .164, -.15), (.46, .204, .170, -.154)),
               folds=4, amp=.008, fold_top=.9, fold_low=.46, wrinkle=.0015, seed=131, spare=.006)
    nv, nu = 14, 20
    Z = np.linspace(1.065, .46, nv)[:, None] + np.zeros((1, nu))
    TH = np.interp(Z, [.46, 1.065], [1.0, 1.22]) * np.linspace(-1, 1, nu)[None, :]
    P = dr.at(TH, Z)
    _sheet(p, P, .006, CHARCOAL, 'CN_Cloth', _axis(), k=_cloth_k(dr, TH, Z, .46, 131, 4.0) * .95)
    for s in (-1, 1):
        _patch(p, dr, s * .22, s * .72, .76, .9, .0035, .004, CHARCOAL, 'CN_Cloth', 7, 5, k=.8, bulge=.006)
    c = dr.at(.5, .88, extra=.018)
    jaw = c + (0, 0, .085)
    _limb(p, [c - (0, 0, .05), jaw - (0, 0, .012)], [.0075, .0085], GOLD, 'CN_Gold', 6, 1.0, None)
    _torus(p, jaw + (0, 0, .006), .016, .0055, _tone(GOLD, .95, None), 'CN_Gold', 12, 5, axis='x', arc=1.6 * math.pi, start=-.3 * math.pi)
    c2 = dr.at(-.4, .88, extra=.016)
    _limb(p, [c2 - (0, 0, .05), c2 + (.002, -.006, .06)], [.004, .004], RED, 'CN_Red', 6, 1.0)
    # Red ties from the apron's top corners round to a knot at the small of the back.
    for s in (-1, 1):
        n = 12
        th = s * np.linspace(1.22, math.pi - .1, n)
        _strip(p, belt, th, np.full(n, 1.04), .022, .0095, .003, RED, 'CN_Red', .95, fold=0.)
    knot = belt.at(math.pi, 1.04, extra=.016, fold=0.)
    _shell(p, knot, (.014, .02, .015), RED, 'CN_Red', .9, 10, 6, R=_basis((-1, 0, 0)))
    for s in (-1, 1):
        _limb(p, [knot, knot + (-.012, s * .02, -.05), knot + (-.016, s * .03, -.11)], [.006, .006, .005], RED, 'CN_Red', 5, .9)
    return _fit(p)


def guard_belt():
    """Teodor Vass: a black duty belt with a gold buckle, pouches, white armour tassets and a baton."""
    p = Part('SM_CP_G_GuardBelt', ('CN_Cloth', 'CN_Lacquer', 'CN_Gold', 'CN_Metal'))
    dr = _torso_drape('Manny', .014)
    _band(p, dr, .955, 1.015, 0., .008, CHARCOAL, 'CN_Cloth', k=.8, rows=3)
    c = dr.at(0., .985, extra=.004, fold=0.)
    R = _basis(dr.normal(0., .985, 0., 0.))
    _box(p, c, (.006, .036, .026), GOLD, 'CN_Gold', .004, 1.0, R, cap=None)
    _box(p, c + R[:, 0] * .005, (.003, .024, .016), GOLD_PALE, 'CN_Gold', .002, .9, R, cap=None)
    for th in (-.62, .62, math.pi - .55, -(math.pi - .55)):
        c = dr.at(th, .975, extra=.026, fold=0.)
        R = _basis(dr.normal(th, .975, 0., 0.))
        _box(p, c, (.02, .036, .036), CHARCOAL, 'CN_Cloth', .008, .85, R)
        _box(p, c + R[:, 0] * .02 + (0, 0, .03), (.004, .036, .01), CHARCOAL, 'CN_Cloth', .003, .75, R)
        _button(p, c + R[:, 0] * .024 + (0, 0, .022), R[:, 0], .005, GOLD, 'CN_Gold', k=1.0, cap=None)
    # Tassets: white plates over the front of the thighs and one over the seat.
    tass = Drape(((1.0, .175, .13, -.13), (.92, .19, .138, -.152), (.82, .2, .146, -.16)), n=2.3, capped=True, spare=.004)
    for th0, th1 in ((-.62, -.06), (.06, .62), (math.pi - .5, math.pi + .5)):
        TH, Z = np.meshgrid(np.linspace(th0, th1, 7), np.linspace(.99, .84, 5))
        P = tass.at(TH, Z, extra=.004 * np.sin(math.pi * (TH - th0) / (th1 - th0)))
        Pp, Qq = _sheet(p, P, .006, WHITE_PURE, 'CN_Lacquer', _axis(), k=.92 - .1 * (.99 - Z))
        edge = _edge_mid(Pp[-1], Qq[-1])
        _limb(p, edge, .0042, WHITE_PURE, 'CN_Lacquer', 6, .85)
        for t in (.2, .8):
            th = th0 + t * (th1 - th0)
            _button(p, tass.at(th, .965, extra=.0045), tass.normal(th, .965, .0045), .0045, ASH, 'CN_Metal', k=1.0, cap=None)
    # A baton hangs in a ring at the right hip, behind the hand.
    c = dr.at(2.35, .9, extra=.035, fold=0.)
    _limb(p, [c + (0, 0, .1), c - (0, 0, .22)], [.016, .015], BLACK, 'CN_Lacquer', 10, 1.0)
    _torus(p, c + (0, 0, .06), .021, .004, _tone(ASH, 1.0, None), 'CN_Metal', 14, 5, axis='z')
    return _fit(p)


# ---------------------------------------------------------------- upper garments (spine_05)

def _panel(part, dr, th_lo, th_hi, z0, z1, extra, thick, base, slot, nu=8, nv=8, k=1.0, fold=1.0, cap=.9, rims=True):
    """A piece of cloth laid on a drape between th_lo(z) and th_hi(z) (functions or numbers) from z0 up to z1:
    lapels, bibs, plackets, yokes, plates. z0 and z1 may be functions of theta (a curved neckline or hem; the
    theta bounds are then taken at the edge's mean height). extra(theta, z) (or a number) stands it off the cloth
    below. Returns ((outer, inner), theta, z)."""
    v = np.linspace(0, 1, nv)[:, None]
    u = np.linspace(0, 1, nu)[None, :]
    zf0 = z0 if callable(z0) else (lambda th, z=z0: z + 0 * th)
    zf1 = z1 if callable(z1) else (lambda th, z=z1: z + 0 * th)
    probe = np.linspace(-math.pi, math.pi, 9)
    n0, n1 = float(np.mean(zf0(probe))), float(np.mean(zf1(probe)))
    Zn = n1 + v * (n0 - n1) + 0 * u
    lo = th_lo(Zn) if callable(th_lo) else th_lo + 0 * Zn
    hi = th_hi(Zn) if callable(th_hi) else th_hi + 0 * Zn
    TH = lo + u * (hi - lo)
    Z = zf1(TH) + v * (zf0(TH) - zf1(TH)) if (callable(z0) or callable(z1)) else Zn
    E = extra(TH, Z) if callable(extra) else extra + 0 * Z
    P = dr.at(TH, Z, extra=E, fold=fold)
    PQ = _sheet(part, P, thick, base, slot, _axis(), k=k, cap=cap, rims=rims)
    return PQ, TH, Z


def _border(P, Q):
    """The midline round a sheet's four edges (a closed loop), for piping and trims."""
    mid = (np.asarray(P) + np.asarray(Q)) / 2
    return np.concatenate([mid[0], mid[1:, -1], mid[-1, ::-1][1:], mid[::-1, 0][1:-1]])


def _fronts(body, dr, z_break, overlap, lap, thick, curve=1.0):
    """The front edges of a coat or a wrap robe: closed from the waist to z_break, the panels overlapping by
    overlap (theta), then opening in a V to the neck at the shoulders. lap +1 lays the left panel over the
    right (a man's coat), -1 the right over the left; the panel on top climbs to its own thickness plus a hair
    before it reaches the other's edge (as _skirt's lapping panel does, so a coat's body and its skirt lap alike
    and neither shows through the other at the waist), and the two never cut each other. Returns (right_edge,
    left_edge, lift)."""
    th_neck = _angles(body, dr)[0]
    z_sh = SHOULDER[body]

    def right_edge(z):
        t = _smooth((np.asarray(z, np.float64) - z_break) / (z_sh - z_break)) ** curve
        return -overlap / 2 + t * (th_neck + overlap / 2)

    def left_edge(z):
        return -right_edge(z)

    def lift(TH, Z, side):
        if side != -lap:
            return 0.0 * TH
        ramp = (TH - right_edge(Z)) if side < 0 else (left_edge(Z) - TH)
        return (thick + .0025) * _smooth((ramp + .085) / .05)
    return right_edge, left_edge, lift


def _lapels(part, dr, fronts, z_from, z_notch, width, thick, base, slot, k=.92, nu=6, nv=10):
    """Notched lapels folded back from the V: each lies on its own panel (whose outer face is the drape plus the
    panel's lift) from where it shows (z_from[side]) to the notch, widest (width, in theta) just under it, with a
    rolled edge along the fold. A lapel starts a little wide, as a real one rolls from the top button."""
    right_edge, left_edge, lift = fronts
    out = {}
    for side in (1, -1):
        edge = right_edge if side > 0 else left_edge
        z0 = z_from[side]

        def w(z, z0=z0):
            t = np.clip((np.asarray(z, np.float64) - z0) / (z_notch - z0), 0, 1)
            return width * (.06 + .94 * np.sin(t * math.pi / 2) ** 1.4) * (1 - .55 * _smooth((t - .86) / .14))

        def lo(z, edge=edge, side=side, w=w):
            return edge(z) if side > 0 else edge(z) - w(z)

        def hi(z, edge=edge, side=side, w=w):
            return edge(z) + w(z) if side > 0 else edge(z)

        def extra(TH, Z, side=side, edge=edge):
            roll = .003 * _smooth(1 - np.abs(TH - edge(Z)) / .06)
            return lift(TH, Z, side) + thick + .001 + roll
        out[side] = _panel(part, dr, lo, hi, z0, z_notch, extra, thick, base, slot, nu, nv, k=k, fold=0.)
    return out


def _collar(part, dr, th_end, z_lo, z_hi, extra, thick, base, slot, nu=30, nv=5, k=.9, stand=0.0, knots=()):
    """A collar round the back of the neck from one front end (theta th_end) to the other. z_lo(a) and z_hi(a)
    give its lower and upper edge at |theta| = a (the points at th_end, the back at pi), so it climbs from the
    lapels' notch over the base of the neck; stand leans its top edge out (0 a stand collar, more a rolled one).
    knots are angles that must be columns (the corners of a seam line the collar's lower edge has to follow)."""
    th = np.unique(np.concatenate([np.linspace(th_end, 2 * math.pi - th_end, nu), np.asarray(knots, np.float64)]))
    a = np.abs(np.angle(np.exp(1j * th)))
    lo, hi = z_lo(a), z_hi(a)
    v = np.linspace(0, 1, nv)[:, None]
    Z = hi[None, :] + v * (lo - hi)[None, :]
    TH = np.broadcast_to(th, Z.shape)
    P = dr.at(TH, Z, extra=extra + stand * (1 - v) + 0 * Z, fold=0.)
    return _sheet(part, P, thick, base, slot, _axis(), k=k, cap=.9)


def _seam_line(body, dr, z_sh, a_pts, z_pts, neck_back=1.47, neck_shape=2.2):
    """The lower edge of a coat's or a wrap robe's collar: its own curve (z_pts at |theta| a_pts), kept under the
    neck opening _top cut (neck_back and neck_shape as the top was built). Behind the neck that opening dips to the
    shoulder line where each strap leaves the back panel, and a collar drawn above the dip leaves a hole there
    that shows the body; pass the dips (pi -+ th_neck) to _collar as knots."""
    z_open = _opening(body, dr, z_sh, neck_back, neck_shape)
    return lambda a: np.minimum(np.interp(a, a_pts, z_pts), z_open(a) - .006)


def coat_black():
    """Kairos: the body of his long black wool coat, lapping left over right like its skirt: notched lapels,
    four gold buttons, a breast pocket with a white square, a gold watch chain, a back seam and a collar."""
    body, seed = 'Manny', 201
    p = Part('SM_CP_G_CoatBlack', ('CN_Cloth', 'CN_Gold'))
    thick = .009
    dr = _torso_drape(body, ((1.05, .022), (1.12, .016), (1.3, .013), (1.45, .010), (1.5, .004)), wrinkle=.0009, seed=seed)
    z_break = 1.265
    fronts = _fronts(body, dr, z_break, .30, 1, thick)
    top = _top(p, body, dr, CHARCOAL, 'CN_Cloth', thick=thick, z_bot=1.055, fronts=fronts, k=.95, seed=seed)
    right_edge, left_edge, lift = fronts
    z_sh = top['z_sh']
    cross = float(np.interp(0., [float(right_edge(z)) for z in np.linspace(z_break, z_sh, 40)], np.linspace(z_break, z_sh, 40)))
    _lapels(p, dr, fronts, {-1: z_break, 1: cross + .01}, z_sh - .012, .36, .005, CHARCOAL, 'CN_Cloth')
    th_end = top['th_neck'] - .03
    _collar(p, dr, th_end, _seam_line(body, dr, z_sh, [th_end, math.pi / 2, math.pi], [z_sh - .022, 1.5, 1.462]),
            lambda a: np.interp(a, [th_end, .9, math.pi / 2, math.pi], [z_sh + .018, 1.525, 1.558, 1.535]),
            .007, .006, CHARCOAL, 'CN_Cloth', stand=.008, knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    # Buttons on the left panel's edge line; the top one is where the lapels break.
    for z in (1.075, 1.14, 1.205, z_break - .005):
        th = .0
        e = float(lift(np.array(th), np.array(z), -1)) + .0005
        _button(p, dr.at(th, z, extra=e), dr.normal(th, z, e), .0095, GOLD, 'CN_Gold', k=1.0, cap=None)
    # Breast pocket on the left chest with a white square standing out of it.
    _panel(p, dr, -.86, -.5, 1.292, 1.306, .0035, .004, CHARCOAL, 'CN_Cloth', 6, 2, k=.8, fold=0.)
    for i, (a, b, h) in enumerate(((-.82, -.7, .028), (-.72, -.6, .022))):
        _panel(p, dr, a, b, 1.3, 1.3 + h, .0022 + .0012 * i, .0025, WHITE_PURE, 'CN_Cloth', 3, 3, k=.95 - .05 * i, fold=0.)
    # A gold watch chain from the third button to a pocket at the right waist (on the coat skirt's front).
    a = dr.at(0., 1.14, extra=.014)
    b = dr.at(.62, 1.08, extra=.004)
    chain = bezier(a, a + (.005, .03, -.05), b + (.008, -.03, -.03), b, 14)
    _limb(p, chain, .0018, GOLD, 'CN_Gold', 5, 1.0, None)
    _panel(p, dr, .5, .78, 1.07, 1.082, .0032, .004, CHARCOAL, 'CN_Cloth', 5, 2, k=.8, fold=0.)
    # Back seam and two darts.
    for th, w in ((math.pi, .012), (math.pi - .55, .007), (math.pi + .55, .007)):
        n = 9
        _strip(p, dr, np.full(n, th), np.linspace(1.065, 1.36 if w > .01 else 1.25, n), w, .0006, .002, CHARCOAL, 'CN_Cloth', .75, fold=0.)
    return _fit(p)


def _opening(body, dr, neck_front, neck_back, shape):
    """The height of a top's neck opening at any theta: the front neckline, then the straps' neck-side edges
    climbing over the shoulders, then the back neckline (the same curves _top cuts), so a collar or a binding
    can sit on it."""
    z_sh = SHOULDER[body]
    th_neck = _angles(body, dr)[0]
    zz = np.linspace(z_sh, 1.6, 240)
    hh = np.minimum.accumulate(dr.axes(zz)[0])
    th_e = np.arcsin(np.clip(STRAP[body][0] / hh, 0, 1) ** (dr.n / 2))
    stop = int(np.argmax(th_e >= math.pi / 2 - 1e-6)) if (th_e >= math.pi / 2 - 1e-6).any() else len(th_e) - 1
    th_e, zz = th_e[:stop + 1], zz[:stop + 1]

    def z_of(theta):
        a = np.abs(np.angle(np.exp(1j * np.asarray(theta, np.float64))))
        front = neck_front + (z_sh - neck_front) * np.clip(a / th_neck, 0, 1) ** shape
        back = neck_back + (z_sh - neck_back) * np.clip((math.pi - a) / th_neck, 0, 1) ** shape
        side = np.interp(np.minimum(a, math.pi - a), th_e, zz)
        return np.where(a < th_neck, front, np.where(math.pi - a < th_neck, back, side))
    return z_of


def _shawl_path(top, y, z_back, front_l, front_r, n_back=13):
    """(theta, z) of a shawl or stole worn round the shoulders: front_l runs from one end up to the left shoulder's
    front seam, front_r from the right shoulder's front seam down to the other end (theta unwrapped below -pi); in
    between it lies over the left shoulder at lateral distance y, dips across the back to z_back at the spine, and
    comes over the right shoulder."""
    lth, lz = top['over'](y, 9, -1)
    rth, rz = top['over'](y, 9, 1)
    u = np.linspace(-1, 1, n_back)
    th_b = np.interp(u, [-1, 1], [lth[-1], -2 * math.pi + rth[-1]])
    z_b = z_back + (top['z_sh'] - z_back) * np.abs(u) ** 1.5
    return _path(front_l, (lth, lz), (th_b, z_b), (rth[::-1] - 2 * math.pi, rz[::-1]), front_r)


def _ribbon3d(part, C, side, out, width, thick, base, slot, k=1.0, cols=3, crown=.0015, cap=.9):
    """A flat strip with thickness along a centreline C in space, side its across direction and out its front:
    the ends of a stole or a sash where they leave the body and hang."""
    C = np.asarray(C, np.float64)
    S = np.broadcast_to(np.asarray(side, np.float64), C.shape).copy()
    S /= np.linalg.norm(S, axis=-1, keepdims=True)
    N = np.broadcast_to(np.asarray(out, np.float64), C.shape).copy()
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    w = np.broadcast_to(np.asarray(width, np.float64), (len(C),))
    a = np.linspace(-1, 1, cols)
    P = C[:, None, :] + S[:, None, :] * (a[None, :, None] * w[:, None, None] / 2) + N[:, None, :] * (crown * (1 - a ** 2))[None, :, None]
    return _sheet(part, P, thick, base, slot, lambda Pp: np.broadcast_to(N[:, None, :], Pp.shape), k=k, cap=cap)


def _fringe(part, a, b, count, length, r, base, slot, seed=0, k=1.0, cap=.9):
    """Threads hanging from the edge a-b, each a short tapering cord, their lengths and sway varied."""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    for t in np.linspace(0, 1, count):
        root = (1 - t) * a + t * b
        L = length * rng.uniform(.82, 1.1)
        sway = rng.uniform(-.007, .007, 2)
        pts = [root, root + (sway[0] * .4, sway[1] * .4, -L * .5), root + (sway[0], sway[1], -L)]
        _limb(part, pts, [r, r * .85, r * .55], base, slot, 4, k * rng.uniform(.88, 1.04), cap)


def _flat_collar(part, dr, z_open, th_end, depth, extra, thick, base, slot, nu=36, nv=4, k=.95, cap=.9):
    """A flat collar lying round a neck opening (z_open(theta)), depth wide, its two front ends rounded."""
    def z1(TH):
        return z_open(TH) + .004

    def z0(TH):
        a = np.abs(np.angle(np.exp(1j * TH)))
        t = np.clip((a - th_end) / .3, 0, 1)
        return z1(TH) - depth * np.sqrt(1 - (1 - t) ** 2) - .003
    return _panel(part, dr, th_end, 2 * math.pi - th_end, z0, z1, extra, thick, base, slot, nu, nv, k=k, fold=0., cap=cap)


def blouse_strap():
    """Petra Lune: an ivory blouse with pin-tucks, a buttoned placket and a stand collar tied with a black
    ribbon, and the canvas strap of her satchel across it from the left hip over the right shoulder."""
    body, seed = 'Quinn', 211
    p = Part('SM_CP_G_BlouseStrap', ('CN_Cloth', 'CN_Gold'))
    dr = Drape(TORSO[body], ease=((1.07, .003), (1.11, .011), (1.3, .009), (1.45, .007), (1.5, .004)), n=2.4, tuck=(1.07, 1.15, .002),
               wrinkle=.0007, seed=seed)
    z_neck, shape = 1.44, 1.6
    top = _top(p, body, dr, IVORY, 'CN_Cloth', thick=.005, z_bot=1.07, neck_front=z_neck, neck_back=1.465, neck_shape=shape,
               k=.97, seed=seed)
    z_open = _opening(body, dr, z_neck, 1.465, shape)
    th_end = .1
    _collar(p, dr, th_end, lambda a: z_open(a) - .004, lambda a: z_open(a) + .03, .006, .005, IVORY, 'CN_Cloth', k=.94)
    _bow(p, dr, 0., z_neck + .012, .006, CHARCOAL, 'CN_Cloth', loop=.02, tail=.075, width=.011, seed=seed)
    # Placket and its small gold buttons; three pin-tucks either side over the breast.
    _panel(p, dr, -.075, .075, 1.07, z_neck - .006, .0026, .003, IVORY, 'CN_Cloth', 3, 12, k=.93)
    for z in np.linspace(1.11, z_neck - .025, 5):
        _button(p, dr.at(0., z, extra=.003), dr.normal(0., z, .003), .0042, GOLD, 'CN_Gold', h=.0024, sides=8, k=1.0, cap=None)
    for s in (-1, 1):
        for th in (.13, .19, .25):
            n = 8
            _strip(p, dr, np.full(n, s * th), np.linspace(1.2, z_neck - .01 - .02 * th, n), .0045, .0009, .002, IVORY, 'CN_Cloth', .9, cols=2)
    # The satchel's strap: from the bag's front ring at the left hip, across the front, over the right shoulder
    # and down the back to the bag's back ring (the skirt carries the last hand's breadth down to the bag).
    oth, oz = top['over'](.097, 9, 1)
    th_f, th_b = float(oth[0]), float(oth[-1])
    t = np.linspace(0, 1, 18)
    front = (np.interp(t, [0, .2, .55, .8, 1], [-2.18, -1.57, -.55, th_f - .25, th_f]),
             np.interp(t, [0, .2, .55, .8, 1], [1.122, 1.098, 1.19, 1.34, top['z_sh']]))
    t = np.linspace(0, 1, 14)
    back = (np.interp(t, [0, .25, .6, 1], [th_b, th_b + .3, math.pi + .4, 2 * math.pi - 2.68]),
            np.interp(t, [0, .25, .6, 1], [top['z_sh'], 1.36, 1.22, 1.122]))
    th, z = _path(front, (oth, oz), back)
    _strip(p, dr, th, z, .03, .0062, .004, CHARCOAL, 'CN_Cloth', .9, fold=0.)
    return _fit(p)


def blouse_shawl():
    """Orsolya Fenn: a light-blue cotton blouse with a scooped neck, and a white knitted shawl round her
    shoulders, its ends crossed over the breast and tucked into her apron's band."""
    body, seed = 'Quinn', 221
    p = Part('SM_CP_G_BlouseShawl', ('CN_Cloth',))
    dr = Drape(TORSO[body], ease=((1.07, .003), (1.11, .012), (1.3, .010), (1.45, .008), (1.5, .004)), n=2.4, tuck=(1.07, 1.16, .0025),
               wrinkle=.0008, seed=seed)
    top = _top(p, body, dr, BLUE, 'CN_Cloth', thick=.005, z_bot=1.07, neck_front=1.37, neck_back=1.45, neck_shape=2.0, k=.95, seed=seed)
    _piping(p, _neck_loop(top, top['ms']), .003, BLUE, 'CN_Cloth', k=.85, closed=True)
    # One long shawl: from its right end tucked at the left waist, up across the breast, over the left shoulder,
    # dipping across the back, over the right shoulder and down across the breast to the right waist.
    lth0 = -float(top['over'](.105, 9, 1)[0][0])
    t = np.linspace(0, 1, 12)
    a = (np.interp(t, [0, .45, 1], [.36, -.2, lth0]), np.interp(t, [0, .45, 1], [1.062, 1.2, top['z_sh']]))
    b = (np.interp(t, [0, .55, 1], [-lth0, .2, -.36]) - 2 * math.pi, np.interp(t, [0, .55, 1], [top['z_sh'], 1.2, 1.062]))
    th, z = _shawl_path(top, .105, 1.29, a, b)
    s = np.linspace(0, 1, len(th))
    width = np.interp(s, [0, .2, .34, .5, .66, .8, 1], [.05, .075, .095, .15, .095, .075, .05])
    # The two ends cross over the breast: the one laid last stands a little higher. Both flatten onto the blouse
    # above the skirt's waistband (ApronSkirtWhite, top 1.088) and run on under it, so they are tucked in, not
    # cut off lying on top of it.
    tuck = np.clip((z - 1.088) / .035, 0, 1)
    extra = .0015 + tuck * (.0047 + .0045 * (s > .5) * (th < -2 * math.pi + .9))
    rib = 1 + .06 * np.sin(np.arange(len(th)) * 2.2)
    _strip(p, dr, th, z, width, extra, .0075, WHITE, 'CN_Cloth', rib, fold=0., cols=4, crown=.003)
    return _fit(p)


def tunic():
    """Tamsin: the bodice of her light-blue tunic, white piping, a white Peter Pan collar, two gold buttons on
    the left shoulder, and a pocket with the spool of her kite's string in it."""
    body, seed = 'Quinn', 231
    p = Part('SM_CP_G_Tunic', ('CN_Cloth', 'CN_Gold'))
    dr = Drape(TORSO[body], ease=((1.05, .008), (1.1, .013), (1.3, .012), (1.45, .009), (1.5, .004)), n=2.4, wrinkle=.0008, seed=seed)
    z_neck, shape = 1.415, 2.0
    top = _top(p, body, dr, BLUE, 'CN_Cloth', thick=.005, z_bot=1.05, neck_front=z_neck, neck_back=1.46, neck_shape=shape, seed=seed)
    for side in (1, -1):
        _piping(p, _arm_loop(top, side, top['ms']), .003, WHITE_PURE, 'CN_Cloth', .92)
    z_open = _opening(body, dr, z_neck, 1.46, shape)
    _flat_collar(p, dr, z_open, .06, .042, .0062, .004, WHITE_PURE, 'CN_Cloth', k=.95)
    oth, _ = top['over'](.1, 9, -1)
    for z in (top['z_sh'] - .012, top['z_sh'] - .04):
        _button(p, dr.at(oth[0], z, extra=.0005), dr.normal(oth[0], z, .0005), .0055, GOLD, 'CN_Gold', h=.003, sides=8, cap=None)
    th0, th1, z0, z1 = .3, .78, 1.1, 1.18
    _patch(p, dr, th0, th1, z0, z1, .0028, .003, BLUE, 'CN_Cloth', 6, 4, k=.92, bulge=.004, fold=0.)
    _piping(p, dr.at(np.linspace(th0, th1, 6), z1, extra=.0045, fold=0.), .0022, WHITE_PURE, 'CN_Cloth', .9)
    c = dr.at(.55, z1 - .005, extra=.013, fold=0.)
    spool = Part('tmp', p.slots)
    for i, (r, h) in enumerate(((.012, .004), (.009, .026), (.012, .004))):
        zb = (0, .004, .03)[i]
        _tube(spool, [(0, 0, zb), (0, 0, zb + h)], r, _tone(WHITE_PURE, .9 - .12 * (i == 1)), 'CN_Cloth', 10)
    _merge(p, spool, _rot((1, 0, 0), 14), c)
    return _fit(p)


def robe_shawl():
    """Old Wen: the bodice of her ivory robe, wrapped left over right with a broad collar band, and a long
    black stole round her shoulders, gold fringe at its ends, the right end hanging longer than the left."""
    body, seed = 'Quinn', 241
    p = Part('SM_CP_G_RobeShawl', ('CN_Cloth', 'CN_Gold'))
    thick = .006
    dr = Drape(TORSO[body], ease=((1.0, .014), (1.1, .016), (1.3, .012), (1.45, .009), (1.5, .004)), n=2.4, wrinkle=.0009, seed=seed)
    z_break = 1.24
    fronts = _fronts(body, dr, z_break, .55, 1, thick, curve=.8)
    right_edge, left_edge, lift = fronts
    top = _top(p, body, dr, IVORY, 'CN_Cloth', thick=thick, z_bot=1.0, fronts=fronts, k=.96, seed=seed)
    z_sh = top['z_sh']
    band = .2

    def ex(side):
        return lambda TH, Z: lift(TH, Z, side) + .0055
    (P, Q), _, _ = _panel(p, dr, lambda z: left_edge(z) - band, left_edge, 1.0, z_sh, ex(-1), .005, IVORY, 'CN_Cloth', 4, 14, k=.88, fold=0.)
    _piping(p, _edge_mid(P[:, 0], Q[:, 0]), .0018, GOLD_PALE, 'CN_Gold', .95, cap=None)
    cross = float(np.interp(0., [float(right_edge(z)) for z in np.linspace(1.0, z_sh, 60)], np.linspace(1.0, z_sh, 60)))
    _panel(p, dr, right_edge, lambda z: right_edge(z) + band, cross - .02, z_sh, ex(1), .005, IVORY, 'CN_Cloth', 4, 8, k=.88, fold=0.)
    th_end = top['th_neck'] - .02
    _collar(p, dr, th_end, _seam_line(body, dr, z_sh, [th_end, math.pi / 2, math.pi], [z_sh - .01, 1.495, 1.455]),
            lambda a: np.interp(a, [th_end, math.pi / 2, math.pi], [z_sh + .03, 1.535, 1.515]), .0065, .005, IVORY, 'CN_Cloth', k=.88,
            knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    # The stole: on the body from the left breast up over the left shoulder, across the upper back and over the
    # right shoulder to the right breast; from each breast it falls straight, a hand's breadth clear of the sash.
    lth0 = -float(top['over'](.1, 9, 1)[0][0])
    t = np.linspace(0, 1, 6)
    a = (np.interp(t, [0, 1], [-.62, lth0]), np.interp(t, [0, 1], [1.275, z_sh]))
    b = (np.interp(t, [0, 1], [-lth0, .62]) - 2 * math.pi, np.interp(t, [0, 1], [z_sh, 1.275]))
    th, z = _shawl_path(top, .1, 1.3, a, b)
    s = np.linspace(0, 1, len(th))
    width = np.interp(s, [0, .25, .5, .75, 1], [.085, .1, .14, .1, .085])
    E = .0105 + .004 * np.exp(-((s - .5) / .2) ** 2)
    _strip(p, dr, th, z, width, E, .007, CHARCOAL, 'CN_Cloth', 1 + .05 * np.sin(np.arange(len(th)) * 1.7), fold=0., cols=4, crown=.003)
    for side, z_end in ((-1, 1.105), (1, .95)):
        th0 = side * .62
        c0 = dr.at(th0, 1.275, extra=.0105, fold=0.)
        n = 7
        zs = np.linspace(1.275, z_end, n)
        C = np.stack([c0[0] + .012 * np.linspace(0, 1, n) ** 2, np.full(n, c0[1]) + side * .004 * np.linspace(0, 1, n), zs], -1)
        _ribbon3d(p, C, (0, 1, 0), (1, .0, 0), .085, .007, CHARCOAL, 'CN_Cloth', .95, cols=4, crown=.003)
        y0, y1 = c0[1] - .04, c0[1] + .04
        _fringe(p, (C[-1, 0], y0, z_end), (C[-1, 0], y1, z_end), 9, .06, .0022, GOLD_DEEP, 'CN_Cloth', seed + side, .95)
    return _fit(p)


def work_apron():
    """Marek Duran: a light-blue chambray work shirt, and the bib of his black canvas apron over it, its neck
    strap, gold rivets, a pencil and a folding rule in the bib pocket."""
    body, seed = 'Manny', 251
    p = Part('SM_CP_G_WorkApron', ('CN_Cloth', 'CN_Gold', 'CN_Red', 'CN_Lacquer'))
    dr = Drape(TORSO[body], ease=((.99, .003), (1.05, .011), (1.3, .011), (1.45, .009), (1.5, .004)), n=2.4, tuck=(.99, 1.08, .002),
               wrinkle=.0009, seed=seed)
    z_neck, shape = 1.445, 1.6
    top = _top(p, body, dr, BLUE, 'CN_Cloth', thick=.005, z_bot=.99, neck_front=z_neck, neck_back=1.475, neck_shape=shape, k=.9, seed=seed)
    z_open = _opening(body, dr, z_neck, 1.475, shape)
    _flat_collar(p, dr, z_open, .07, .04, .0058, .004, BLUE, 'CN_Cloth', k=.86)
    _panel(p, dr, -.07, .07, .99, z_neck - .005, .0025, .003, BLUE, 'CN_Cloth', 3, 12, k=.86)
    for z in np.linspace(1.04, z_neck - .02, 6):
        _button(p, dr.at(0., z, extra=.0028), dr.normal(0., z, .0028), .0045, WHITE_PURE, 'CN_Lacquer', h=.0022, sides=8, k=.95)
    # The bib stands off the shirt where the canvas bridges the waist, and meets the apron's top edge below.
    def stand(TH, Z):
        return .014 + .006 * np.clip((1.16 - Z) / .1, 0, 1) - .004 * np.clip((Z - 1.32) / .05, 0, 1)
    z0, z1 = 1.04, 1.365
    (P, Q), TH, Z = _panel(p, dr, lambda z: -np.interp(z, [z0, z1], [.62, .44]), lambda z: np.interp(z, [z0, z1], [.62, .44]),
                           z0, z1, stand, .006, CHARCOAL, 'CN_Cloth', 9, 10, k=_cloth_k(dr, 0 * np.ones((10, 9)), np.linspace(z1, z0, 10)[:, None] + np.zeros((10, 9)), z0, seed, 2.0) * .95, fold=0.)
    _piping(p, _border(P, Q), .003, CHARCOAL, 'CN_Cloth', .8, closed=True)
    # Pocket across the bib, a red pencil and a white folding rule with gold joints in it.
    pz0, pz1 = 1.21, 1.3
    _panel(p, dr, -.36, .36, pz0, pz1, lambda TH, Z: stand(TH, Z) + .0035, .004, CHARCOAL, 'CN_Cloth', 7, 4, k=.85, fold=0.)
    _strip(p, dr, np.zeros(4), np.linspace(pz0, pz1, 4), .004, float(stand(0, 1.25)) + .0045, .002, CHARCOAL, 'CN_Cloth', .7, cols=2, fold=0.)
    c = dr.at(-.18, pz1 - .03, extra=float(stand(0, 1.27)) + .0075, fold=0.)
    _limb(p, [c, c + (.003, .004, .1)], [.0042, .0042], RED, 'CN_Red', 6, 1.0)
    _limb(p, [c + (.003, .004, .1), c + (.0035, .0045, .112)], [.0042, .0012], WHITE, 'CN_Cloth', 6, .8)
    c = dr.at(.2, pz1 - .04, extra=float(stand(0, 1.27)) + .0075, fold=0.)
    R = _basis(dr.normal(.2, pz1, 0., 0.))
    for i in range(3):
        _box(p, c + R[:, 2] * (.03 + .045 * i) + R[:, 1] * .003 * i, (.0025, .009, .024), WHITE_PURE, 'CN_Cloth', .0015, .92 - .04 * i, R)
        _button(p, c + R[:, 2] * (.054 + .045 * i) + R[:, 0] * .003, R[:, 0], .004, GOLD, 'CN_Gold', h=.002, sides=6, cap=None)
    # Neck strap from the bib's top corners over the shoulders to a buckle behind the neck; rivets at the corners.
    for side in (1, -1):
        oth, oz = top['over'](.088, 8, side)
        t = np.linspace(0, 1, 5)
        a = (np.interp(t, [0, 1], [side * .44, oth[0]]), np.interp(t, [0, 1], [z1 - .01, top['z_sh']]))
        b = (np.interp(t, [0, 1], [oth[-1], side * (math.pi - .02)]), np.interp(t, [0, 1], [top['z_sh'], 1.478]))
        th, z = _path(a, (oth, oz), b)
        E = np.interp(np.arange(len(th)), [0, 4, len(th) - 1], [float(stand(0, z1)) + .004, .0075, .0075])
        _strip(p, dr, th, z, .026, E, .004, CHARCOAL, 'CN_Cloth', .85, fold=0.)
        q = dr.at(side * .46, z1 - .022, extra=float(stand(0, z1)) + .002)
        _button(p, q, dr.normal(side * .46, z1 - .022, 0.), .0055, GOLD, 'CN_Gold', h=.003, sides=8, cap=None)
    c = dr.at(math.pi, 1.478, extra=.012, fold=0.)
    _box(p, c, (.004, .02, .014), GOLD_PALE, 'CN_Gold', .003, 1.0, _basis((-1, 0, 0)), cap=None)
    return _fit(p)


def blouse():
    """Sefa Moreno: a white cotton blouse gathered on a drawstring at a wide neckline, an embroidered border
    of red, gold and light blue under it, and a necklace of small gold coins."""
    body, seed = 'Quinn', 261
    p = Part('SM_CP_G_Blouse', ('CN_Cloth', 'CN_Gold'))
    dr = Drape(TORSO[body], ease=((1.07, .003), (1.11, .013), (1.3, .011), (1.45, .009), (1.5, .004)), n=2.4, tuck=(1.07, 1.17, .003),
               wrinkle=.0008, seed=seed, ripples=((1.26, 1.4, 44, .0022),))
    z_neck, shape = 1.385, 2.4
    top = _top(p, body, dr, WHITE_PURE, 'CN_Cloth', thick=.005, z_bot=1.07, neck_front=z_neck, neck_back=1.44, neck_shape=shape,
               k=.95, seed=seed)
    _piping(p, _neck_loop(top, top['ms']), .0034, WHITE_PURE, 'CN_Cloth', .9, closed=True)
    # The drawstring's ends tied at the front of the neckline.
    c = dr.at(0., z_neck - .006, extra=.006, fold=0.)
    _shell(p, c, (.005, .006, .005), WHITE_PURE, 'CN_Cloth', .85, 8, 5)
    for s in (-1, 1):
        _limb(p, [c, c + (.004, s * .008, -.03), c + (.006, s * .012, -.065)], [.0018, .0016, .0012], WHITE_PURE, 'CN_Cloth', 4, .85)
        _shell(p, c + (.006, s * .012, -.068), (.004, .004, .006), RED, 'CN_Cloth', .95, 6, 4)
    # The embroidered border: blocks of colour a finger below the neckline, round the front and the back.
    th_neck = top['th_neck']
    colours = (RED, GOLD_DEEP, BLUE, GOLD_DEEP)
    for half, z_c in ((0., z_neck), (math.pi, 1.44)):
        edges = np.linspace(-th_neck * .96, th_neck * .96, 17)
        for i in range(16):
            th = np.linspace(edges[i], edges[i + 1], 3)
            z = z_c + (top['z_sh'] - z_c) * np.clip(np.abs(th) / th_neck, 0, 1) ** shape - .018
            _strip(p, dr, half + th, z, .014, .0032, .0022, colours[i % 4], 'CN_Cloth', .95, cols=2, fold=1.0, crown=.001)
    # A fine gold chain hung with coins, lying on the breast.
    t = np.linspace(-1, 1, 21)
    th = .58 * t
    z = 1.43 - .085 * (1 - t ** 2) - .012 * np.abs(t)
    chain = dr.at(th, z, extra=.0045, fold=1.0)
    _limb(p, chain, .0013, GOLD, 'CN_Gold', 4, 1.0, None)
    for i in range(3, 18, 2):
        q = dr.at(th[i], z[i] - .011, extra=.0052, fold=1.0)
        _button(p, q, dr.normal(th[i], z[i] - .011, .0052, 1.0), .0072 if i != 10 else .0095, GOLD, 'CN_Gold', h=.0018, sides=10, cap=None)
    return _fit(p)


def armour_vest():
    """Teodor Vass: a quilted black gambeson, over it a white lacquered breastplate and backplate with gold
    edges, a keel and rivets, black leather shoulder straps with gold buckles, and a red sash."""
    body, seed = 'Manny', 271
    p = Part('SM_CP_G_ArmourVest', ('CN_Cloth', 'CN_Lacquer', 'CN_Gold', 'CN_Black', 'CN_Metal'))
    dr = Drape(TORSO[body], ease=((.975, .004), (1.03, .014), (1.3, .015), (1.45, .011), (1.5, .005)), n=2.4, wrinkle=.0006, seed=seed,
               quilt=(.042, .0028, .975, 1.47))
    top = _top(p, body, dr, CHARCOAL, 'CN_Cloth', thick=.008, z_bot=.975, neck_front=1.44, neck_back=1.47, neck_shape=1.8, k=.9,
               nv=22, seed=seed)
    z_sh = top['z_sh']
    z_open = _opening(body, dr, 1.44, 1.47, 1.8)
    _collar(p, dr, .2, lambda a: z_open(a) - .006, lambda a: np.maximum(z_open(a) + .012, np.interp(a, [0, math.pi / 2, math.pi], [1.475, 1.535, 1.515])),
            .009, .008, CHARCOAL, 'CN_Cloth', k=.85, stand=.004)
    # The plates follow the gambeson a finger off it; the breastplate has a keel down its middle.
    def plate_out(keel):
        def f(TH, Z):
            a = np.abs(np.angle(np.exp(1j * (TH - (0. if keel else math.pi)))))
            return .013 + (.006 * np.exp(-(a / .14) ** 2) * _smooth((Z - 1.04) / .22) if keel else 0.)
        return f
    rivets = []
    for keel, mid, lo_z, hi_z, half_lo, half_hi in ((True, 0., 1.03, lambda th: 1.42 + .028 * (np.abs(th) / .52) ** 2, .9, .52),
                                                     (False, math.pi, 1.04, lambda th: 1.43 + .02 * (np.abs(np.angle(np.exp(1j * (th - math.pi)))) / .55) ** 2, .95, .55)):
        def lo_th(z, mid=mid, a=half_lo, b=half_hi):
            return mid - np.interp(z, [1.0, 1.3, 1.45], [a, a, b])

        def hi_th(z, mid=mid, a=half_lo, b=half_hi):
            return mid + np.interp(z, [1.0, 1.3, 1.45], [a, a, b])
        (P, Q), TH, Z = _panel(p, dr, lo_th, hi_th, lo_z, hi_z, plate_out(keel), .005, WHITE_PURE, 'CN_Lacquer', 11, 10,
                               k=.93 - .08 * (1.3 - np.linspace(1.43, 1.03, 10)[:, None]) ** 2 + 0 * np.ones((10, 11)), fold=0., cap=.9)
        loop = _border(P, Q)
        _piping(p, loop, .0045, GOLD, 'CN_Gold', 1.0, closed=True, cap=None)
        nrm = (P - Q) / (np.linalg.norm(P - Q, axis=-1, keepdims=True) + 1e-12)
        nb = np.concatenate([nrm[0], nrm[1:, -1], nrm[-1, ::-1][1:], nrm[::-1, 0][1:-1]])
        inset = np.concatenate([Q[1], Q[1:-1, -2], Q[-2, ::-1][1:-1], Q[::-1, 1][1:-1]])
        for i in range(0, len(loop), 4):
            j = min(i, len(inset) - 1)
            rivets.append((P.reshape(-1, 3)[np.argmin(np.linalg.norm(P.reshape(-1, 3) - (loop[i] * .7 + inset[j] * .3), axis=1))], nb[i]))
    for pos, nrm in rivets:
        _button(p, pos + nrm * .0002, nrm, .0034, GOLD_PALE, 'CN_Gold', h=.002, sides=6, cap=None)
    # Shoulder straps from the breastplate's top corners to the backplate's, buckled at the front.
    for side in (1, -1):
        oth, oz = top['over'](.112, 8, side)
        _strip(p, dr, oth, oz, .034, .0115, .005, CHARCOAL, 'CN_Black', .9, fold=0.)
        # The buckle sits on the front of the shoulder, facing forward, where the strap meets the breastplate.
        q = dr.at(oth[0], z_sh - .022, extra=.0175, fold=0.)
        R = _basis(dr.normal(oth[0], z_sh - .022, .0175, 0.))
        _box(p, q, (.0025, .015, .012), GOLD, 'CN_Gold', .002, 1.0, R, cap=None)
        _box(p, q + R[:, 0] * .0024, (.0012, .009, .007), CHARCOAL, 'CN_Black', .001, .8, R)
    # Side straps under the arms join the plates at the waist, low where the arms leave room.
    for z in (1.055, 1.09):
        for side in (1, -1):
            th = side * np.linspace(.86, math.pi - .92, 9)
            _strip(p, dr, th, np.full(9, z), .016, .004, .004, CHARCOAL, 'CN_Black', .85, fold=0.)
            q = dr.at(side * .88, z, extra=.0175, fold=0.)
            _box(p, q, (.002, .011, .011), ASH, 'CN_Metal', .0015, 1.0, _basis(dr.normal(side * .88, z, .017, 0.)), cap=None)
    # A red sash worn as a baldric: from the right shoulder across the breastplate, under the left arm at the
    # waist (where the arm leaves room), and back up across the backplate; a gold brooch holds it on the shoulder.
    oth, oz = top['over'](.097, 8, 1)
    t = np.linspace(0, 1, 13)
    front = (np.interp(t, [0, .28, .62, .85, 1], [-math.pi / 2 - .1, -.95, 0., oth[0] - .1, oth[0]]),
             np.interp(t, [0, .28, .62, .85, 1], [1.04, 1.06, 1.24, 1.375, z_sh]))
    back = (np.interp(t, [0, .15, .38, .72, 1], [oth[-1], oth[-1] + .1, math.pi, math.pi + .95, 1.5 * math.pi]),
            np.interp(t, [0, .15, .38, .72, 1], [z_sh, 1.375, 1.24, 1.06, 1.04]))
    th, z = _path(front, (oth, oz), back)
    a = np.abs(np.angle(np.exp(1j * th)))
    on_plate = np.maximum(_smooth((.86 - a) / .1) * (z < 1.43), _smooth((a - (math.pi - .9)) / .1) * (z < 1.44))
    E = .009 + .0105 * on_plate + .008 * (z > z_sh - .01)
    E[-1] += .004  # the back end laps over the front end under the arm
    _strip(p, dr, th, z, .046, E, .005, RED, 'CN_Cloth', 1 + .05 * np.sin(np.arange(len(th)) * 1.9), fold=0., cols=4, crown=.003)
    q = dr.at(oth[0] - .02, z_sh - .035, extra=.026, fold=0.)
    nrm = dr.normal(oth[0] - .02, z_sh - .035, .026, 0.)
    _button(p, q, nrm, .016, GOLD, 'CN_Gold', h=.005, sides=12, cap=None)
    _button(p, q + nrm * .004, nrm, .007, BLUE, 'CN_Lacquer', h=.004, sides=10, k=1.0)
    return _fit(p)


def coat_white():
    """Doctor Ama Okafor: the body of her white coat, right over left like its skirt, notched lapels, white
    buttons, a breast pocket with two pens, and a stethoscope round her neck."""
    body, seed = 'Quinn', 281
    p = Part('SM_CP_G_CoatWhite', ('CN_Cloth', 'CN_Lacquer', 'CN_Metal', 'CN_Gold'))
    thick = .006
    dr = _torso_drape(body, ((1.05, .02), (1.12, .015), (1.3, .012), (1.45, .010), (1.5, .004)), wrinkle=.0009, seed=seed)
    z_break = 1.19
    fronts = _fronts(body, dr, z_break, .3, -1, thick)
    right_edge, left_edge, lift = fronts
    top = _top(p, body, dr, WHITE_COOL, 'CN_Cloth', thick=thick, z_bot=1.05, fronts=fronts, seed=seed)
    z_sh = top['z_sh']
    cross = float(np.interp(0., [float(-left_edge(z)) for z in np.linspace(z_break, z_sh, 40)], np.linspace(z_break, z_sh, 40)))
    _lapels(p, dr, fronts, {1: z_break, -1: cross + .01}, z_sh - .012, .4, .004, WHITE_COOL, 'CN_Cloth', k=.94)
    th_end = top['th_neck'] - .03
    _collar(p, dr, th_end, _seam_line(body, dr, z_sh, [th_end, math.pi / 2, math.pi], [z_sh - .022, 1.49, 1.452]),
            lambda a: np.interp(a, [th_end, .9, math.pi / 2, math.pi], [z_sh + .018, 1.515, 1.545, 1.52]), .006, .005, WHITE_COOL,
            'CN_Cloth', stand=.008, k=.93, knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    for z in (1.08, 1.135, z_break - .005):
        e = float(lift(np.array(0.), np.array(z), 1)) + .0005
        _button(p, dr.at(0., z, extra=e), dr.normal(0., z, e), .0075, WHITE_PURE, 'CN_Lacquer', k=.95)
    # Breast pocket on the left and two pens clipped in it.
    th0, th1, z0, z1 = -.95, -.5, 1.2, 1.29
    _patch(p, dr, th0, th1, z0, z1, .0026, .003, WHITE_COOL, 'CN_Cloth', 6, 4, k=.95, bulge=.003, fold=0.)
    for i, (th, colour, slot) in enumerate(((-.62, BLACK, 'CN_Lacquer'), (-.75, BLUE, 'CN_Lacquer'))):
        c = dr.at(th, z1 - .035, extra=.0075, fold=0.)
        _limb(p, [c, c + (0, 0, .06 - .008 * i)], [.0045, .0045], colour, slot, 6, 1.0)
        _limb(p, [c + (0, 0, .06 - .008 * i), c + (.001, 0, .066 - .008 * i)], [.0045, .002], colour, slot, 6, .9)
        _box(p, dr.at(th, z1 + .008, extra=.0105, fold=0.), (.0012, .0022, .014), GOLD, 'CN_Gold', .0008, 1.0, _basis(dr.normal(th, z1, 0., 0.)), cap=None)
    # The stethoscope: tubing round the back of the neck over the collar, its two ends hanging down the lapels,
    # the chest piece on the right and the steel ear tubes on the left.
    t = np.linspace(0, 1, 15)
    th = np.interp(t, [0, .2, .5, .8, 1], [.3, .5, math.pi, 2 * math.pi - .5, 2 * math.pi - .32])
    z = np.interp(t, [0, .2, .35, .5, .65, .8, 1], [1.27, 1.41, 1.5, 1.505, 1.5, 1.41, 1.3])
    E = np.interp(t, [0, .2, .35, .65, .8, 1], [.016, .021, .027, .027, .021, .018])
    tubing = dr.at(th, z, extra=E, fold=0.)
    _limb(p, tubing, .0045, BLACK, 'CN_Lacquer', 7, 1.0)
    end = tubing[0]
    _limb(p, [end, end - (0, 0, .03)], [.0042, .0042], BLACK, 'CN_Lacquer', 7, 1.0)
    head = end - (0, 0, .045)
    nrm = dr.normal(.3, 1.23, 0., 0.)
    _shell(p, head + nrm * .004, (.007, .019, .019), ASH, 'CN_Metal', 1.0, 12, 6, R=_basis(nrm), cap=None)
    _limb(p, [head + (0, 0, .018), end - (0, 0, .028)], [.0028, .0028], ASH, 'CN_Metal', 6, 1.2, None)
    e2 = tubing[-1]
    for s in (-1, 1):
        a = e2 + (0, s * .008, 0)
        _limb(p, [a, a + (.006, s * .004, -.05), a + (.012, s * .01, -.085)], [.0018, .0018, .0018], ASH, 'CN_Metal', 5, 1.3, None)
        _shell(p, a + (.013, s * .011, -.09), (.0045, .0045, .006), BLACK, 'CN_Lacquer', .9, 6, 4)
    return _fit(p)


def robe_tall():
    """The Listener: the bodice of a white robe wrapped left over right in a deep V over a light-blue
    under-robe, a broad gold orphrey down both front edges and round the neck."""
    body, seed = 'Manny', 291
    p = Part('SM_CP_G_RobeTall', ('CN_Cloth', 'CN_Gold'))
    thick = .006
    dr = Drape(TORSO[body], ease=((1.0, .012), (1.1, .015), (1.3, .013), (1.45, .010), (1.5, .004)), n=2.4, wrinkle=.0009, seed=seed)
    inner = Drape(TORSO[body], ease=((1.0, .004), (1.3, .005), (1.45, .004)), n=2.4, wrinkle=.0005, seed=seed + 1)
    z_break = 1.14
    fronts = _fronts(body, dr, z_break, .6, 1, thick, curve=.75)
    right_edge, left_edge, lift = fronts
    top = _top(p, body, dr, WHITE_PURE, 'CN_Cloth', thick=thick, z_bot=1.0, fronts=fronts, k=.95, seed=seed)
    z_sh = top['z_sh']
    _panel(p, inner, -.62, .62, 1.12, lambda th: 1.47 - .01 * (np.abs(th) / .62), .0, .004, BLUE, 'CN_Cloth', 9, 8, k=.95, fold=0.)
    band = .17

    def ex(side):
        return lambda TH, Z: lift(TH, Z, side) + .005
    for side in (-1, 1):
        edge = left_edge if side < 0 else right_edge
        z0 = 1.0 if side < 0 else 1.22
        lo = (lambda z, e=edge: e(z) - band) if side < 0 else edge
        hi = edge if side < 0 else (lambda z, e=edge: e(z) + band)
        (P, Q), TH, Z = _panel(p, dr, lo, hi, z0, z_sh, ex(side), .0045, GOLD_DEEP, 'CN_Cloth', 4, 14, k=1.0, fold=0.)
        for col in (0, -1):
            _piping(p, _edge_mid(P[:, col], Q[:, col]), .0022, GOLD, 'CN_Gold', 1.0, cap=None)
    th_end = top['th_neck'] - .02
    _collar(p, dr, th_end, _seam_line(body, dr, z_sh, [th_end, math.pi / 2, math.pi], [z_sh - .012, 1.49, 1.455]),
            lambda a: np.interp(a, [th_end, math.pi / 2, math.pi], [z_sh + .035, 1.54, 1.52]), .006, .0045, GOLD_DEEP, 'CN_Cloth', k=1.0,
            knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    # Gold thread worked as a row of small studs down the middle of each front band.
    for side in (-1, 1):
        edge = left_edge if side < 0 else right_edge
        for z in np.linspace(1.02 if side < 0 else 1.24, z_sh - .02, 9):
            th = float(edge(z)) + (-band / 2 if side < 0 else band / 2)
            e = float(lift(np.array(th), np.array(z), side)) + .0055
            _button(p, dr.at(th, z, extra=e, fold=0.), dr.normal(th, z, e, 0.), .005, GOLD, 'CN_Gold', h=.002, sides=8, cap=None)
    return _fit(p)


def oilskin():
    """Dov Pell: the body of a light-blue oilskin coat: a snapped storm flap continuing the skirt's, a tall
    funnel collar lined in black, a shoulder yoke, and two chest pockets with flaps."""
    body, seed = 'Manny', 301
    p = Part('SM_CP_G_Oilskin', ('CN_Blue', 'CN_Lacquer', 'CN_Cloth'))
    dr = Drape(TORSO[body], ease=((1.05, .02), (1.12, .017), (1.3, .015), (1.45, .011), (1.5, .005)), n=2.4, wrinkle=.0014, seed=seed)
    z_neck, shape = 1.45, 1.6
    top = _top(p, body, dr, BLUE, 'CN_Blue', thick=.007, z_bot=1.05, neck_front=z_neck, neck_back=1.475, neck_shape=shape, k=.95, seed=seed)
    z_sh = top['z_sh']
    z_open = _opening(body, dr, z_neck, 1.475, shape)
    # Funnel collar: stands up round the neck, open a little at the throat; its black lining shows at the top.
    th_end = .2
    P, Q = _collar(p, dr, th_end, lambda a: z_open(a) - .006,
                   lambda a: np.maximum(z_open(a) + .03, np.interp(a, [th_end, math.pi / 2, math.pi], [1.53, 1.57, 1.565])), .008, .006,
                   BLUE, 'CN_Blue', nu=34, nv=6, k=.93, stand=.012)
    _piping(p, _edge_mid(P[0], Q[0]), .0042, CHARCOAL, 'CN_Cloth', .85)
    for s in (-1, 1):
        th = s * (th_end + .04)
        z = float(z_open(th)) + .04
        _button(p, dr.at(th, z, extra=.0145, fold=0.), dr.normal(th, z, .0145, 0.), .006, BLACK, 'CN_Lacquer', h=.0035)
    # Storm flap over the front closure, snapped shut.
    n = 12
    zs = np.linspace(1.05, z_neck - .004, n)
    _strip(p, dr, np.full(n, .02), zs, .05, .0075, .004, BLUE, 'CN_Blue', .95, fold=1.0)
    for z in (1.13, 1.22, 1.31, 1.4):
        _button(p, dr.at(.02, z, extra=.0118), dr.normal(.02, z, .0118), .0065, BLACK, 'CN_Lacquer', h=.004)
    # Yoke across the shoulders and upper back.
    (P, Q), _, _ = _panel(p, dr, math.pi - 1.35, math.pi + 1.35, 1.33, lambda th: z_sh + 0 * th, .0035, .003, BLUE, 'CN_Blue', 11, 4, k=.9)
    _piping(p, _edge_mid(P[-1], Q[-1]), .0018, BLUE, 'CN_Blue', .8)
    for s in (-1, 1):
        a, b = sorted((s * .38, s * .85))
        _patch(p, dr, a, b, 1.16, 1.27, .0035, .0035, BLUE, 'CN_Blue', 6, 5, k=.95, bulge=.005)
        _patch(p, dr, a - .02, b + .02, 1.255, 1.3, .0105, .0045, BLUE, 'CN_Blue', 6, 3, k=.88)
        mid = (a + b) / 2
        _button(p, dr.at(mid, 1.268, extra=.015), dr.normal(mid, 1.268, .015), .0052, BLACK, 'CN_Lacquer', h=.003)
    return _fit(p)


def blouse_bib():
    """Rhea Sato: a black work blouse with a small collar, and the bib of her gold apron over it, its straps
    crossed over the back and buttoned at the front."""
    body, seed = 'Quinn', 311
    p = Part('SM_CP_G_BlouseBib', ('CN_Cloth', 'CN_Gold'))
    dr = Drape(TORSO[body], ease=((1.07, .003), (1.11, .012), (1.3, .010), (1.45, .008), (1.5, .004)), n=2.4, tuck=(1.07, 1.16, .0025),
               wrinkle=.0009, seed=seed)
    z_neck, shape = 1.44, 1.6
    top = _top(p, body, dr, CHARCOAL, 'CN_Cloth', thick=.005, z_bot=1.07, neck_front=z_neck, neck_back=1.47, neck_shape=shape, k=.95, seed=seed)
    z_sh = top['z_sh']
    z_open = _opening(body, dr, z_neck, 1.47, shape)
    _flat_collar(p, dr, z_open, .07, .038, .0058, .004, CHARCOAL, 'CN_Cloth', k=.85)
    # The bib meets the apron's band at the waist and stands off the blouse there.
    def stand(TH, Z):
        return .0185 * np.clip((1.13 - Z) / .06, 0, 1) + .0065
    z0, z1 = 1.045, 1.325
    (P, Q), TH, Z = _panel(p, dr, lambda z: -np.interp(z, [z0, z1], [.62, .5]), lambda z: np.interp(z, [z0, z1], [.62, .5]), z0, z1,
                           stand, .004, GOLD_DEEP, 'CN_Cloth', 9, 9, k=.97, fold=0.)
    _piping(p, _border(P, Q), .0026, GOLD_DEEP, 'CN_Cloth', .88, closed=True)
    _panel(p, dr, -.3, .3, 1.17, 1.25, lambda TH, Z: stand(TH, Z) + .0032, .003, GOLD_DEEP, 'CN_Cloth', 6, 4, k=.92, fold=0.)
    # Straps from the bib's top corners over the shoulders, crossed on the back, down to the apron's band.
    for side in (1, -1):
        oth, oz = top['over'](.1, 8, side)
        t = np.linspace(0, 1, 4)
        a = (np.interp(t, [0, 1], [side * .5, oth[0]]), np.interp(t, [0, 1], [z1 - .012, z_sh]))
        t = np.linspace(0, 1, 12)
        b = (np.interp(t, [0, 1], [oth[-1], side * (math.pi + .95)]), np.interp(t, [0, 1], [z_sh, 1.075]))
        th, z = _path(a, (oth, oz), b)
        E = .0072 + .0032 * (side < 0) * (np.arange(len(th)) > len(th) - 13)
        _strip(p, dr, th, z, .03, E, .0035, GOLD_DEEP, 'CN_Cloth', .95, fold=0.)
        q = dr.at(side * .5, z1 - .03, extra=float(stand(0, z1)) + .003)
        _button(p, q, dr.normal(side * .5, z1 - .03, 0.), .0068, GOLD, 'CN_Gold', h=.0035, sides=10, cap=None)
    return _fit(p)


# ---------------------------------------------------------------- headwear and hair (head)

def _fit_head(part, body):
    """Fails the build if headwear sinks into the skull (more than the hair shell's own inner face may) or
    rides above where a head's crown can carry it: the head bone is at 1.625, the top of the head at ~1.80."""
    (cx, cy, cz), fr, bk, hw, up = HEAD[body]
    v = np.asarray(part.v)
    x = v[:, 0] - cx
    r = np.sqrt((x / np.where(x >= 0, fr, bk)) ** 2 + ((v[:, 1] - cy) / hw) ** 2 + ((v[:, 2] - cz) / up) ** 2)
    deep = (v[:, 2] > cz) & (r < .8)
    if deep.any():
        raise ValueError('%s sinks into the skull at %s' % (part.name, np.round(v[np.argmax(deep)], 3).tolist()))
    if v[:, 2].min() < 1.40 or v[:, 2].max() > 2.05:
        raise ValueError('%s does not sit on a head (z %.2f..%.2f)' % (part.name, v[:, 2].min(), v[:, 2].max()))
    return _fit(part)


def _lobes(bottom_pts):
    """bottom(phi) from (|phi|, z) control points, the same either side."""
    a, z = zip(*bottom_pts)
    return lambda phi: np.interp(np.abs(np.angle(np.exp(1j * np.asarray(phi, np.float64)))), a, z)


def _hair(part, body, base, bottom, lift, seed, strands=48, strand=.002, k=1.0, nu=56, nv=18, **kw):
    """A head of hair on the skull: _scalp with the hair's grooves, a ragged end and darker roots."""
    shade = lambda P, PS: .88 + .12 * np.clip(PS / 1.2, 0, 1)
    return _scalp(part, HEAD[body], base, 'CN_Cloth', bottom, lift, strands=strands, strand=strand, seed=seed, k=k, nu=nu, nv=nv,
                  shade=shade, **kw)


def _band_ring(part, head, z0, z1, extra, base, slot, k=1.0, nu=48, thick=.003, cap=.9, centre=None, scale=1.0):
    """A band round the head (a hatband, a cap's cuff, a headband) at the skull's own section between z0 and z1."""
    (cx, cy, cz), fr, bk, hw, up = head
    phi = np.linspace(-math.pi, math.pi, nu, endpoint=False)
    rows = []
    for z in (z1, z0):
        psi = math.asin(max(-.99, min(.99, (z - cz) / up)))
        rows.append(_skull(head, phi, np.full(nu, psi), extra) * np.array([scale, scale, 1.]) + np.array([cx * (1 - scale), cy * (1 - scale), 0.]))
        rows[-1][:, 2] = z
    P = np.array(rows)
    return _sheet(part, P, thick, base, slot, _away((cx, cy, (z0 + z1) / 2)), k=k, closed=True, cap=cap)


def sage_hair():
    """Kairos: long white hair combed back from a high forehead to his collar, and a full white beard."""
    body, seed = 'Manny', 401
    p = Part('SM_CP_G_SageHair', ('CN_Cloth',))
    bottom = _lobes(((0, 1.772), (.42, 1.786), (.9, 1.735), (1.3, 1.668), (1.62, 1.63), (2.2, 1.57), (math.pi, 1.548)))
    lift = lambda phi, psi: .006 + .008 * np.clip(1 - np.abs(np.sin(psi)), 0, 1) + .003 * np.abs(np.sin(phi))
    _hair(p, body, WHITE, bottom, lift, seed, strands=46, strand=.0026, flare=.06, inward=.004, ends=.01, k=.95)
    _beard(p, WHITE, 'CN_Cloth', length=.055, thick=.016, seed=seed, k=.95)
    return _fit_head(p, body)


def bun_black():
    """Petra Lune: black hair parted in the middle and drawn back into a low bun pinned with gold, and wire
    spectacles with light-blue lenses."""
    body, seed = 'Quinn', 411
    p = Part('SM_CP_G_BunBlack', ('CN_Cloth', 'CN_Gold', 'CN_Glass'))
    (cx, cy, cz), fr, bk, hw, up = HEAD[body]
    bottom = _lobes(((0, 1.776), (.5, 1.76), (.85, 1.73), (1.3, 1.68), (1.7, 1.655), (2.5, 1.63), (math.pi, 1.625)))
    lift = lambda phi, psi: .0045 + .0025 * np.sin(np.clip(psi, 0, None)) - .0028 * np.exp(-(phi / .07) ** 2) * (psi > .8)
    _hair(p, body, CHARCOAL, bottom, lift, seed, strands=64, strand=.0014, ends=.003, thick=.008, inward=.003)
    c = np.array([cx - bk - .016, cy, 1.655])
    _coil(p, c, (-1, 0, .3), .036, CHARCOAL, 'CN_Cloth', turns=2.4, rad=.015, seed=seed)
    _limb(p, [c + (.01, -.05, .03), c + (-.03, .05, -.02)], [.0022, .0022], GOLD, 'CN_Gold', 5, 1.0, None)
    _shell(p, c + (.01, -.052, .031), (.005, .005, .005), GOLD, 'CN_Gold', 1.0, 8, 4, cap=None)
    # Spectacles: two rims, the bridge, lenses and the arms running back over the ears into the hair.
    for s in (-1, 1):
        ctr = np.array([.111, s * .031, 1.697])
        _torus(p, ctr, .0175, .0013, _tone(GOLD, 1.0, None), 'CN_Gold', 18, 5, axis='x')
        ang = np.linspace(0, 2 * math.pi, 16, endpoint=False)
        lens = np.stack([np.full(16, ctr[0] - .0005), ctr[1] + .0168 * np.cos(ang), ctr[2] + .0168 * np.sin(ang)], -1)
        p.add(lens, [list(range(16))[::-1] if np.dot(np.cross(lens[1] - lens[0], lens[2] - lens[0]), (1, 0, 0)) < 0 else list(range(16))],
              BLUE_PALE, 'CN_Glass', False)
        _limb(p, [ctr + (-.002, s * .018, .004), (.07, s * .078, 1.703), (-.01, s * .081, 1.692), (-.03, s * .079, 1.672)],
              .0012, GOLD, 'CN_Gold', 4, 1.0, None)
    _limb(p, [(.112, -.014, 1.701), (.115, 0, 1.704), (.112, .014, 1.701)], .0013, GOLD, 'CN_Gold', 4, 1.0, None)
    return _fit_head(p, body)


def bun_white():
    """Old Wen: white hair drawn up into a high bun, two gold pins crossed through it, wisps at the temples."""
    body, seed = 'Quinn', 421
    p = Part('SM_CP_G_BunWhite', ('CN_Cloth', 'CN_Gold'))
    (cx, cy, cz), fr, bk, hw, up = HEAD[body]
    bottom = _lobes(((0, 1.772), (.5, 1.758), (.9, 1.735), (1.3, 1.69), (1.8, 1.66), (2.6, 1.645), (math.pi, 1.64)))
    lift = lambda phi, psi: .005 + .004 * np.sin(np.clip(psi, 0, None))
    _hair(p, body, IVORY, bottom, lift, seed, strands=56, strand=.0018, ends=.004, thick=.009, k=.95)
    c = np.array([cx - .03, cy, cz + up + .004])
    _shell(p, c + (0, 0, .03), (.036, .038, .032), IVORY, 'CN_Cloth', .95, 14, 8, R=_rot((0, 1, 0), -16))
    _coil(p, c + (0, 0, .004), (-.3, 0, 1), .042, IVORY, 'CN_Cloth', turns=1.6, rad=.014, seed=seed, k=.9, height=.02)
    for s in (-1, 1):
        a = c + (.035, s * .05, .03)
        b = c + (-.03, -s * .045, .0)
        _limb(p, [a, b], [.0024, .0024], GOLD, 'CN_Gold', 5, 1.0, None)
        _shell(p, a, (.0045, .0045, .0045), GOLD, 'CN_Gold', 1.0, 8, 4, cap=None)
    for s in (-1, 1):
        root = _skull(HEAD[body], s * .95, .55, .006)
        _limb(p, [root, root + (.006, s * .006, -.03), root + (.012, s * .004, -.055)], [.003, .0025, .001], IVORY, 'CN_Cloth', 4, .9)
    return _fit_head(p, body)


def short_hair():
    """Tamsin: short, tousled black hair with a fringe, and a red clip on the right."""
    body, seed = 'Quinn', 431
    p = Part('SM_CP_G_ShortHair', ('CN_Cloth', 'CN_Lacquer'))
    bottom = _lobes(((0, 1.738), (.6, 1.728), (1.0, 1.695), (1.35, 1.66), (2.0, 1.625), (math.pi, 1.612)))
    lift = lambda phi, psi: .008 + .009 * np.sin(np.clip(psi, 0, None)) + .003 * noise2(np.cos(phi) * 2, psi * 3, seed)
    _hair(p, body, CHARCOAL, bottom, lift, seed, strands=34, strand=.0045, ends=.009, thick=.012)
    q = _skull(HEAD[body], .95, .62, .019)
    R = _basis(q - np.array(HEAD[body][0]))
    _box(p, q, (.003, .006, .02), RED, 'CN_Lacquer', .002, 1.0, R @ _rot((1, 0, 0), 35))
    return _fit_head(p, body)


def straw_hat():
    """Orsolya Fenn: a wide-brimmed straw hat with a black ribbon, and a short black plait at her nape."""
    body, seed = 'Quinn', 441
    p = Part('SM_CP_G_StrawHat', ('CN_Cloth',))
    head = HEAD[body]
    (cx, cy, cz), fr, bk, hw, up = head
    band_z = 1.748
    _hat(p, head, GOLD_STRAW, 'CN_Cloth', band_z, .235, .085, .03, tilt=-3, thick=.005, braid=.0024, crown_round=.45, seed=seed)
    _band_ring(p, head, band_z + .002, band_z + .024, .0115, CHARCOAL, 'CN_Cloth', k=.9, scale=.99)
    bottom = _lobes(((0, 1.752), (.9, 1.72), (1.35, 1.68), (2.0, 1.645), (math.pi, 1.635)))
    _hair(p, body, CHARCOAL, bottom, lambda phi, psi: .0045 + 0 * phi, seed, strands=40, strand=.0012, nu=40, nv=10, thick=.008)
    # The plait: three strands wound round each other down the nape, tied off in a black band.
    top = np.array([cx - bk - .006, cy, 1.655])
    t = np.linspace(0, 1, 14)
    spine = top + np.outer(t, (-.012, 0, -.13))
    for i in range(3):
        a = t * 5 * math.pi + i * 2 * math.pi / 3
        pts = spine + np.stack([.006 * np.cos(a), .009 * np.sin(a), .004 * np.cos(2 * a)], -1)
        _limb(p, pts, np.linspace(.0085, .006, 14), CHARCOAL, 'CN_Cloth', 6, .9 + .06 * i)
    end = spine[-1]
    _limb(p, [end + (0, 0, .004), end - (0, 0, .008)], [.0085, .0085], CHARCOAL, 'CN_Cloth', 8, .7)
    _shell(p, end - (0, 0, .022), (.008, .01, .016), CHARCOAL, 'CN_Cloth', .85, 8, 5)
    return _fit_head(p, body)


def _peak(part, head, z_band, depth, drop, phi_span, thick, base, slot, k=1.0, nu=14, nv=4, cap=.9):
    """The stiff peak of a cap or a helmet: from the band at the forehead it reaches depth forward, curving
    round the brow, its outer edge drop lower than its root."""
    (cx, cy, cz), fr, bk, hw, up = head
    psi = math.asin(min(.99, (z_band - cz) / up))
    phi = np.linspace(-phi_span, phi_span, nu)
    root = _skull(head, phi, np.full(nu, psi), .006)
    radial = np.stack([np.cos(phi), np.sin(phi) * .8, np.zeros(nu)], -1)
    radial /= np.linalg.norm(radial, axis=-1, keepdims=True)
    reach = depth * np.cos(phi / phi_span * math.pi / 2) ** .6
    v = np.linspace(0, 1, nv)[:, None, None]
    P = root[None] + radial[None] * (reach[None, :, None] * v) - np.array([0, 0, 1.])[None, None] * (drop * v ** 1.3)
    P[..., 2] += 0 * v[..., 0]
    return _sheet(part, P, thick, base, slot, _dir((0, 0, 1)), k=k, cap=cap)


def cap_red():
    """Marek Duran: a red wool flat cap with a short stiff peak and a covered button, over short black hair."""
    body, seed = 'Manny', 451
    p = Part('SM_CP_G_CapRed', ('CN_Cloth',))
    head = HEAD[body]
    (cx, cy, cz), fr, bk, hw, up = head
    bottom = _lobes(((0, 1.762), (.9, 1.725), (1.3, 1.67), (1.55, 1.648), (2.2, 1.625), (math.pi, 1.618)))
    _hair(p, body, CHARCOAL, bottom, lambda phi, psi: .0035 + .002 * np.sin(np.clip(psi, 0, None)), seed, strands=30, strand=.0009,
          nu=44, nv=12, thick=.007)
    band = _lobes(((0, 1.742), (1.6, 1.733), (math.pi, 1.722)))
    lift = lambda phi, psi: .0105 + .021 * np.clip(np.cos(phi), 0, 1) ** 1.4 * np.clip(np.sin(psi), 0, 1) ** 2.5
    _scalp(p, head, RED, 'CN_Cloth', band, lift, thick=.006, nu=48, nv=12, strands=8, strand=.0012, seed=seed, k=.95)
    _band_ring(p, head, 1.72, 1.742, .0125, RED, 'CN_Cloth', k=.82)
    _peak(p, head, 1.738, .055, .012, 1.05, .006, RED, 'CN_Cloth', k=.85)
    _shell(p, (cx + .012, cy, cz + up + .022), (.008, .008, .004), RED, 'CN_Cloth', .9, 8, 4)
    return _fit_head(p, body)


def headscarf_red():
    """Sefa Moreno: a red headscarf over her hair, knotted at the nape with its two ends hanging, a line of
    black hair under its front edge, and gold hoop earrings."""
    body, seed = 'Quinn', 461
    p = Part('SM_CP_G_HeadscarfRed', ('CN_Cloth', 'CN_Gold'))
    head = HEAD[body]
    (cx, cy, cz), fr, bk, hw, up = head
    _hair(p, body, CHARCOAL, _lobes(((0, 1.752), (.9, 1.72), (1.35, 1.69), (2.0, 1.65), (math.pi, 1.64))),
          lambda phi, psi: .004 + 0 * phi, seed, strands=0, nu=40, nv=10, thick=.007)
    bottom = _lobes(((0, 1.768), (.9, 1.738), (1.35, 1.692), (1.8, 1.645), (2.6, 1.622), (math.pi, 1.618)))
    lift = lambda phi, psi: .0085 + .004 * np.sin(np.clip(psi, 0, None)) + .002 * noise2(np.cos(phi) * 3, psi * 4, seed)
    _scalp(p, head, RED, 'CN_Cloth', bottom, lift, thick=.006, nu=52, nv=14, strands=14, strand=.0022, ends=.003, seed=seed, k=.95)
    knot = np.array([cx - bk - .02, cy, 1.632])
    _shell(p, knot, (.018, .026, .02), RED, 'CN_Cloth', .88, 10, 6)
    for s, L in ((-1, .1), (1, .085)):
        n = 6
        d = np.linspace(0, 1, n)
        C = np.stack([knot[0] - .004 - .012 * d, knot[1] + s * (.012 + .018 * d), knot[2] - .012 - L * d], -1)
        _ribbon3d(p, C, (0, 1, 0), (-1, 0, .1), np.linspace(.04, .03, n), .004, RED, 'CN_Cloth', .9, cols=3)
    for s in (-1, 1):
        q = _skull(head, s * 1.62, math.asin((1.672 - cz) / up), .004)
        _torus(p, q - (0, 0, .013), .012, .0017, _tone(GOLD, 1.0, None), 'CN_Gold', 16, 5, axis='y')
    return _fit_head(p, body)


def helmet():
    """Teodor Vass: a white lacquered helmet over padding, a gold ridge and a red brush crest, a black peak,
    cheek guards hinged on gold rivets and a black chin strap."""
    body, seed = 'Manny', 471
    p = Part('SM_CP_G_Helmet', ('CN_Lacquer', 'CN_Gold', 'CN_Cloth', 'CN_Black'))
    head = HEAD[body]
    (cx, cy, cz), fr, bk, hw, up = head
    bottom = _lobes(((0, 1.748), (.8, 1.735), (1.3, 1.69), (1.8, 1.655), (2.6, 1.632), (math.pi, 1.628)))
    lift = lambda phi, psi: .021 + .004 * np.sin(np.clip(psi, 0, None))
    _scalp(p, head, WHITE_PURE, 'CN_Lacquer', bottom, lift, thick=.006, nu=48, nv=14, flare=.32, seed=seed, k=.95, psi_top=1.4)
    # A rolled rim round the helmet's edge.
    _scalp(p, head, WHITE_PURE, 'CN_Lacquer', lambda phi: bottom(phi) + .012, lambda phi, psi: lift(phi, psi) + .0035, thick=.004, nu=48,
           nv=3, flare=.32, seed=seed, k=.85, psi_top=math.asin(max(-.99, min(.99, (1.7 - cz) / up))), close_top=False)
    # Ridge and crest along the helmet's middle, front to back, on the shell's own surface.
    ang = np.linspace(.35, math.pi - .55, 16)
    reach = np.where(np.cos(ang) >= 0, fr, bk) + .027
    ridge = np.stack([cx + reach * np.cos(ang), np.zeros(16), cz + (up + .027) * np.sin(ang)], -1)
    _limb(p, ridge, .0065, GOLD, 'CN_Gold', 6, 1.0, None)
    # The brush crest: a dense red horsehair comb, taller over the crown, its top edge ragged.
    hgt = .034 * np.sin(np.linspace(.25, math.pi - .25, 16)) ** .6
    v = np.linspace(0, 1, 4)[:, None, None]
    radial = (ridge - np.array([cx, cy, cz])) / np.linalg.norm(ridge - np.array([cx, cy, cz]), axis=-1, keepdims=True)
    F = ridge[None] + radial[None] * (.004 + hgt[None, :, None] * v)
    F[-1] += radial * (.005 * noise2(np.arange(16) * 1.7, 2.0, seed)[:, None])
    F[..., 1] += .0125 * (1 - .35 * v[..., 0])
    _sheet(p, F, .025 * (1 - .35 * v[..., 0]) + 0 * hgt[None, :], RED, 'CN_Cloth', _dir((0, 1, 0)),
           k=np.linspace(.78, 1.0, 4)[:, None] + .08 * noise2(np.arange(16)[None, :] * 2.3, np.arange(4)[:, None] * 1.1, seed + 3))
    _peak(p, head, 1.752, .04, .01, 1.0, .005, BLACK, 'CN_Lacquer', k=1.0)
    # Cheek guards hang from hinges under the helmet's edge and cover the cheeks to the jaw, their front edges
    # turned in toward the face (smaller and square to the side, they read as ear muffs).
    for s in (-1, 1):
        R = _basis((.22, s, 0), (0, 0, 1))
        _plate(p, (.036, s * (hw + .021), 1.632), R, .085, .11, .008, .005, WHITE_PURE, 'CN_Lacquer', k=.92, nu=5, nv=6, trim=GOLD,
               trim_r=.0026, round_=.5)
        for dx in (-.018, .018):
            _button(p, (.036 + dx, s * (hw + .03), 1.678), (0, s, 0), .0038, GOLD, 'CN_Gold', h=.0024, sides=8, cap=None)
        _limb(p, [(.056, s * (hw + .012), 1.585), (.066, s * .058, 1.556), (.075, s * .03, 1.537)], .0042, BLACK, 'CN_Black', 6, .9)
    _limb(p, [(.075, -.03, 1.537), (.079, 0, 1.534), (.075, .03, 1.537)], .0042, BLACK, 'CN_Black', 6, .9)
    return _fit_head(p, body)


def bob_black():
    """Doctor Ama Okafor: a sleek black bob to the jaw with a fringe, its ends turned under, and a thin gold
    band across the crown."""
    body, seed = 'Quinn', 481
    p = Part('SM_CP_G_BobBlack', ('CN_Cloth', 'CN_Gold'))
    head = HEAD[body]
    bottom = _lobes(((0, 1.742), (.55, 1.738), (.92, 1.71), (1.12, 1.62), (1.45, 1.592), (2.3, 1.598), (math.pi, 1.602)))
    lift = lambda phi, psi: .0085 + .0065 * np.sin(np.clip(psi, 0, None)) + .002 * np.cos(phi) ** 2
    _hair(p, body, CHARCOAL, bottom, lift, seed, strands=70, strand=.0011, inward=.007, ends=.002, thick=.011, flare=.015)
    # The band follows the hair's own surface over the crown from ear to ear.
    a = math.pi / 2 - np.linspace(.32, math.pi - .32, 15)   # from the crown, positive toward the right ear
    pts = np.array(head[0]) + np.stack([np.full(15, .012), (head[3] + .016) * np.sin(a), (head[4] + .016) * np.cos(a)], -1)
    _limb(p, pts, .0026, GOLD, 'CN_Gold', 6, 1.0, None)
    return _fit_head(p, body)


def hood_halo():
    """The Listener: a deep white hood falling onto the shoulders, dark inside, a gold edge round the face, and
    behind it a gold listening ring set with light-blue lights on a bracket from the hood."""
    body, seed = 'Manny', 491
    p = Part('SM_CP_G_HoodHalo', ('CN_Cloth', 'CN_Gold', 'CN_Glow'))
    head = HEAD[body]
    (cx, cy, cz), fr, bk, hw, up = head
    bottom = _lobes(((0, 1.792), (.55, 1.745), (.95, 1.62), (1.25, 1.545), (1.6, 1.51), (2.3, 1.475), (math.pi, 1.465)))
    lift = lambda phi, psi: .032 + .012 * np.sin(np.clip(psi, 0, None)) + .006 * np.clip(-np.cos(phi), 0, 1)
    (P, Q), phi, PS = _scalp(p, head, WHITE_PURE, 'CN_Cloth', bottom, lift, thick=.007, nu=52, nv=16, flare=.22, inward=0., strands=10,
                            strand=.003, seed=seed, k=.95)
    # A gold edge round the face opening.
    face = np.abs(np.angle(np.exp(1j * phi))) < 1.45
    edge = _edge_mid(P[-1, face], Q[-1, face])
    order = np.argsort(np.angle(np.exp(1j * phi[face])))
    _piping(p, edge[order], .0042, GOLD, 'CN_Gold', 1.0, cap=None)
    # The ring stands behind the head, facing forward, held by a bracket from the back of the hood.
    ring_c = np.array([cx - bk - .095, cy, 1.73])
    _torus(p, ring_c, .175, .0065, _tone(GOLD, 1.0, None), 'CN_Gold', 48, 6, axis='x')
    _torus(p, ring_c + (-.004, 0, 0), .158, .0028, _tone(GOLD_PALE, .95, None), 'CN_Gold', 48, 5, axis='x')
    for i in range(8):
        a = (i + .5) * 2 * math.pi / 8
        q = ring_c + (.004, .175 * math.cos(a), .175 * math.sin(a))
        _shell(p, q, (.011, .011, .011), LIGHT_BLUE, 'CN_Glow', 1.0, 10, 6, cap=None)
    back = _skull(head, math.pi, -.25, lift(math.pi, -.25) + .004)
    _limb(p, [back, back + (-.03, 0, -.03), ring_c + (.0, 0, -.175)], [.006, .006, .006], GOLD, 'CN_Gold', 6, 1.0, None)
    return _fit_head(p, body)


def knit_cap_beard():
    """Dov Pell: a black knitted watch cap with a turned-up cuff sitting above the ears, short black hair below
    it, and a full black beard."""
    body, seed = 'Manny', 501
    p = Part('SM_CP_G_KnitCapBeard', ('CN_Cloth',))
    head = HEAD[body]
    _hair(p, body, CHARCOAL, _lobes(((0, 1.745), (.9, 1.72), (1.3, 1.665), (1.6, 1.645), (2.3, 1.625), (math.pi, 1.62))),
          lambda phi, psi: .0035 + 0 * phi, seed, strands=0, nu=40, nv=10, thick=.007)
    band = _lobes(((0, 1.738), (1.6, 1.725), (math.pi, 1.712)))
    lift = lambda phi, psi: .0095 + .006 * np.clip(np.sin(psi), 0, 1) ** 3
    _scalp(p, head, CHARCOAL, 'CN_Cloth', band, lift, thick=.006, nu=60, nv=12, strands=60, strand=.0016, seed=seed, k=.92)
    _band_ring(p, head, 1.712, 1.75, .0185, CHARCOAL, 'CN_Cloth', k=.8, nu=60, thick=.006)
    _beard(p, CHARCOAL, 'CN_Cloth', length=.045, thick=.015, seed=seed, k=.9)
    return _fit_head(p, body)


def field_hat():
    """Rhea Sato: a white cotton field hat with a turned-down brim, a gold band and a neck curtain against the
    sun, tied under the chin with a black cord, over black hair."""
    body, seed = 'Quinn', 511
    p = Part('SM_CP_G_FieldHat', ('CN_Cloth', 'CN_Gold'))
    head = HEAD[body]
    (cx, cy, cz), fr, bk, hw, up = head
    band_z = 1.742
    _hair(p, body, CHARCOAL, _lobes(((0, 1.748), (.9, 1.72), (1.3, 1.68), (2.0, 1.64), (math.pi, 1.632))),
          lambda phi, psi: .004 + 0 * phi, seed, strands=30, strand=.001, nu=40, nv=10, thick=.007)
    _hat(p, head, WHITE, 'CN_Cloth', band_z, .155, .072, .042, thick=.004, crown_round=.6, crease=.007, seed=seed, k=.95)
    _band_ring(p, head, band_z + .002, band_z + .018, .0115, GOLD_DEEP, 'CN_Cloth', k=1.0)
    for s in (-1, 1):
        for dx in (-.018, .018):
            q = _skull(head, s * math.pi / 2 + dx * 4, math.asin((band_z + .045 - cz) / up), .012)
            _torus(p, q, .0042, .0013, _tone(GOLD, 1.0, None), 'CN_Gold', 10, 4, axis='y')
    # The neck curtain hangs from inside the brim at the back and sides, standing off the neck.
    psi = math.asin((band_z - .004 - cz) / up)
    phi = np.linspace(math.pi - 1.75, math.pi + 1.75, 26)
    v = np.linspace(0, 1, 7)[:, None]
    top_pts = _skull(head, phi, np.full(len(phi), psi), .014)
    radial = np.stack([np.cos(phi), np.sin(phi), np.zeros(len(phi))], -1)
    a = np.abs(np.angle(np.exp(1j * (phi - math.pi))))
    length = np.interp(a, [0, 1.2, 1.75], [.205, .175, .12])
    hang = top_pts[None] + radial[None] * (.03 * v[..., None] ** 1.2) - np.array([0, 0, 1.]) * (length[None, :, None] * v[..., None])
    hang += radial[None] * (.003 * np.sin(phi * 9 + seed)[None, :, None] * v[..., None])
    _sheet(p, hang, .003, WHITE, 'CN_Cloth', _away((cx, cy, 1.62)), k=.95 - .1 * v + 0 * a[None, :])
    # Chin cord from the band's sides under the chin.
    for s in (-1, 1):
        _limb(p, [(.0, s * (hw + .012), band_z - .01), (.03, s * .074, 1.63), (.055, s * .052, 1.565), (.062, s * .02, 1.54)],
              .0016, BLACK, 'CN_Cloth', 4, 1.0)
    _limb(p, [(.062, -.02, 1.54), (.064, 0, 1.538), (.062, .02, 1.54)], .0016, BLACK, 'CN_Cloth', 4, 1.0)
    return _fit_head(p, body)


# ---------------------------------------------------------------- figures that are not human (Shape)

# Figure glows that keep their colour (2026-11-07 review; palette.py is not edited): at full strength LIGHT_GOLD blew
# out to a white core with a peach rim on the Mechanoid, and the light-blue eyes and lenses read white. GLOW_GOLD is a
# deeper, more saturated gold, and both run at about half strength, where allowed() still calls them gold and light blue.
GLOW_GOLD = col(1.0, .70, .12)
GOLD_GLOW_TONE = .55
BLUE_GLOW_TONE = .5


def _to_height(part, height):
    """Scales a figure about its feet (the origin) to the README's height."""
    v = np.asarray(part.v, np.float64)
    part.v = (v * (height / v[:, 2].max())).tolist()
    return part


def _joint(part, c, r, base=SLATE, slot='CN_Metal', sides=10, rings=6, k=1.0):
    """A ball joint of dark steel."""
    _shell(part, np.asarray(c, np.float64), (r, r, r), base, slot, k, sides, rings, cap=None)


def _pod(part, a, b, r, base, slot, sides=14, rings=8, squash=1.0, k=1.0, cap=.9, bulge=(1.0, 1.0), shade=None, face=(1., 0., 0.)):
    """A limb casing: an egg-shaped shell from a to b, r across (squash flattens it toward face, bulge scales its
    two ends), its local front turned toward face."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    L = float(np.linalg.norm(b - a))
    d = (b - a) / L
    u = np.asarray(face, np.float64) - d * np.dot(face, d)
    if np.linalg.norm(u) < 1e-6:
        u = np.cross(d, (0, 1., 0))
    u /= np.linalg.norm(u)
    R = np.stack([u, np.cross(d, u), d], 1)
    rr = (r * squash, r, L / 2 * bulge[1], r * squash, L / 2 * bulge[0])
    return _shell(part, (a + b) / 2, rr, base, slot, k, sides, rings, R=R, cap=cap, shade=shade)


def _seam(part, pts, r=.0035, base=CHARCOAL, slot='CN_Metal', k=1.0, closed=False):
    """A panel line between two casing plates (a thin dark bead along the joint)."""
    _piping(part, pts, r, base, slot, k, closed, None)


def _ellipse(c, rx, ry, z, n=24, start=0.0, arc=2 * math.pi):
    t = start + np.linspace(0, arc, n, endpoint=arc < 2 * math.pi - 1e-6)
    return np.stack([c[0] + rx * np.cos(t), c[1] + ry * np.sin(t), np.full(n, z)], -1)


def _hand(part, wrist, side, scale=1.0, base=SLATE, slot='CN_Metal', pad=CHARCOAL, pad_slot='CN_Black', curl=.35, k=1.0):
    """A mechanical hand hanging at the side, palm turned in: a palm plate, four two-jointed fingers curling
    forward and a thumb."""
    w = np.asarray(wrist, np.float64)
    s = scale
    palm_c = w + np.array([.012, 0, -.052]) * s
    _box(part, palm_c, (.034 * s, .014 * s, .044 * s), base, slot, .008 * s, k)
    _box(part, palm_c + (0, -side * .012 * s, 0), (.03 * s, .004 * s, .038 * s), pad, pad_slot, .003 * s, k * .9)
    for i, dx in enumerate((-.024, -.008, .008, .024)):
        root = palm_c + np.array([dx * s, 0, -.044 * s])
        length = (.03, .036, .034, .026)[i] * s
        mid = root + np.array([curl * .25 * length, 0, -length])
        tip = mid + np.array([curl * length, 0, -length * .8])
        _limb(part, [root, mid, tip], [.0075 * s, .0068 * s, .0055 * s], base, slot, 6, k)
        _joint(part, mid, .0078 * s, CHARCOAL, slot, 6, 4)
    t0 = palm_c + np.array([.034 * s, -side * .008 * s, -.01 * s])
    _limb(part, [t0, t0 + np.array([.02, -side * .012, -.025]) * s, t0 + np.array([.032, -side * .014, -.05]) * s], [.008 * s, .007 * s, .0055 * s],
          base, slot, 6, k)


def _hull(part, rows, base, slot, n=2.6, nu=24, k=1.0, shade=None, cap=.9, centre=(0., 0.)):
    """A closed casing whose horizontal sections are superellipses through rows (z, half-width, front depth, back
    depth; both depths positive), capped at both ends: a robot's chest or pelvis, a Mecha's torso. One surface."""
    rows = sorted(rows)
    th = np.linspace(-math.pi, math.pi, nu, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    e = 2.0 / n
    rings = []
    for z, hw, f, b in rows:
        x = np.where(c >= 0, f, b) * np.sign(c) * np.abs(c) ** e + centre[0]
        y = hw * np.sign(s) * np.abs(s) ** e + centre[1]
        rings.append(np.stack([x, y, np.full(nu, z)], -1))
    V = np.concatenate(rings)
    kk = np.ones(len(V)) * k if shade is None else k * shade(V)
    faces = [[i * nu + (j + 1) % nu, i * nu + j, (i + 1) * nu + j, (i + 1) * nu + (j + 1) % nu] for i in range(len(rows) - 1) for j in range(nu)]
    test = np.cross(V[faces[0][1]] - V[faces[0][0]], V[faces[0][2]] - V[faces[0][0]])
    if np.dot(test, V[faces[0][0]] - np.array([centre[0], centre[1], V[faces[0][0], 2]])) < 0:
        faces = [f[::-1] for f in faces]
    part.add(V, faces, _tone(base, kk, cap), slot, True)
    _ngon(part, rings[0], (0, 0, -1), base, slot, float(kk[:nu].mean()), cap)
    _ngon(part, rings[-1], (0, 0, 1), base, slot, float(kk[-nu:].mean()), cap)
    return rings


def robot():
    """Halden-7, the Mendery's Robot: a humanoid of white ceramic casings over a dark steel frame, gold trim,
    light-blue eyes behind a black visor and a status light on its chest, worn and dusty from years of mending."""
    p = Part('SM_CP_Robot', ('CN_White', 'CN_Metal', 'CN_Black', 'CN_Gold', 'CN_Glow', 'CN_Lacquer'))
    ceramic = WHITE_COOL
    dirt = lambda L: .78 + .22 * np.clip(L[..., 2] / .35, -1, 1)
    for s in (-1, 1):
        # Foot, ankle, shin, knee, thigh, hip.
        _box(p, (.04, s * .11, .013), (.135, .058, .013), CHARCOAL, 'CN_Black', .008, .8)
        _shell(p, (.05, s * .11, .055), (.11, .052, .045, .075, .03), ceramic, 'CN_White', .78, 12, 6, shade=dirt)
        _joint(p, (0, s * .11, .105), .042, sides=8, rings=5, k=.8)
        _pod(p, (0, s * .11, .13), (0, s * .11, .47), .06, ceramic, 'CN_White', sides=12, rings=7, squash=1.08, k=.86, bulge=(.9, 1.0))
        _limb(p, [(-.055, s * .11, .15), (-.06, s * .11, .44)], [.014, .014], SLATE, 'CN_Metal', 6, .85)
        _seam(p, _ellipse((0, s * .11), .066, .062, .3, 14), closed=True)
        _joint(p, (0, s * .11, .5), .05, sides=8, rings=5)
        _plate(p, (.052, s * .11, .505), _basis((1, 0, .1)), .085, .1, .012, .008, ceramic, 'CN_White', k=.9, nu=4, nv=4)
        _pod(p, (0, s * .105, .53), (0, s * .1, .89), .074, ceramic, 'CN_White', sides=12, rings=7, squash=1.05, k=.94)
        _seam(p, _ellipse((0, s * .103), .079, .076, .72, 14), closed=True)
        _joint(p, (0, s * .1, .915), .058, sides=8, rings=5)
    # Pelvis casing, the gold maker's plate, the flexible waist.
    _hull(p, ((.86, .11, .07, .08), (.9, .155, .1, .11), (.96, .172, .12, .13), (1.0, .158, .112, .122), (1.03, .125, .092, .1)),
          ceramic, 'CN_White', nu=20, k=.92)
    _box(p, (.124, 0, .955), (.008, .045, .03), GOLD, 'CN_Gold', .005, 1.0, cap=None)
    _shell(p, (0, 0, 1.065), (.1, .125, .07), CHARCOAL, 'CN_Black', .9, 12, 5)
    for z in (1.04, 1.075):
        _limb(p, np.concatenate([_ellipse((0, 0), .104, .13, z, 16), _ellipse((0, 0), .104, .13, z, 16)[:1]]), .011, SLATE, 'CN_Metal', 5, .9)
    # Chest casing, broad at the shoulders: pectoral plates, an abdominal plate, the serial plate, the status light.
    _hull(p, ((1.09, .12, .09, .09), (1.16, .148, .106, .1), (1.24, .176, .124, .114), (1.32, .19, .134, .124), (1.4, .194, .13, .125),
              (1.46, .174, .11, .11), (1.5, .118, .08, .085)), ceramic, 'CN_White', nu=24, k=.96)
    for s in (-1, 1):
        R = _basis((1, s * .3, .12))
        _plate(p, (.125, s * .082, 1.36), R, .13, .12, .014, .009, ceramic, 'CN_White', k=1.0, nu=5, nv=5, trim=GOLD_PALE, trim_r=.0026)
    _plate(p, (.118, 0, 1.17), _basis((1, 0, -.15)), .16, .09, .01, .008, ceramic, 'CN_White', k=.92, nu=5, nv=4)
    _box(p, (.124, .095, 1.245), (.004, .03, .016), GOLD, 'CN_Gold', .003, 1.0, _basis((1, .3, 0)), cap=None)
    for dy in (-.022, .022):
        _button(p, (.128, .095 + dy, 1.245), (1, .3, 0), .0035, GOLD_PALE, 'CN_Gold', h=.002, sides=6, cap=None)
    _button(p, (.128, -.095, 1.245), (1, -.3, 0), .016, CHARCOAL, 'CN_Metal', h=.005, sides=10)
    _button(p, (.133, -.096, 1.245), (1, -.3, 0), .009, LIGHT_BLUE, 'CN_Glow', h=.004, sides=8, k=BLUE_GLOW_TONE, cap=None)
    # Power pack on the back, with vents and two exhaust pipes.
    _box(p, (-.165, 0, 1.3), (.05, .115, .15), SLATE, 'CN_Metal', .02, .85)
    for z in np.linspace(1.2, 1.4, 4):
        _box(p, (-.216, 0, z), (.004, .085, .008), CHARCOAL, 'CN_Black', .003, .8)
    for s in (-1, 1):
        _limb(p, [(-.18, s * .08, 1.42), (-.19, s * .085, 1.52)], [.02, .018], SLATE, 'CN_Metal', 8, .7)
    # Neck, the gold collar ring, cables.
    _limb(p, [(0, 0, 1.49), (0, 0, 1.6)], [.042, .038], SLATE, 'CN_Metal', 10, .9)
    _torus(p, (0, 0, 1.505), .07, .011, _tone(GOLD, 1.0, None), 'CN_Gold', 20, 5)
    for s in (-1, 1):
        _limb(p, bezier((-.035, s * .05, 1.49), (-.03, s * .07, 1.54), (-.02, s * .06, 1.58), (-.01, s * .045, 1.62), 5), .008, CHARCOAL, 'CN_Black', 5, .9)
    # Shoulders and arms hanging a little forward, elbows soft.
    for s in (-1, 1):
        _joint(p, (0, s * .222, 1.42), .062, sides=8, rings=5)
        _shell(p, (0, s * .232, 1.44), (.085, .08, .065, .088, .05), ceramic, 'CN_White', .98, 12, 6)
        _pod(p, (-.005, s * .243, 1.39), (.0, s * .255, 1.15), .05, ceramic, 'CN_White', sides=10, rings=6, k=.95)
        _joint(p, (.008, s * .257, 1.12), .044, sides=8, rings=5)
        _pod(p, (.015, s * .257, 1.1), (.068, s * .25, .885), .048, ceramic, 'CN_White', sides=10, rings=6, k=.93, bulge=(.85, 1.0))
        _limb(p, [(.0, s * .232, 1.08), (.05, s * .232, .9)], [.011, .011], SLATE, 'CN_Metal', 5, .8)
        _joint(p, (.074, s * .25, .868), .028, sides=8, rings=4)
        _hand(p, (.074, s * .25, .862), s)
    # Head: casing, black visor with two light-blue eyes, ear discs and an antenna.
    hc = np.array([0, 0, 1.69])
    _shell(p, hc, (.108, .094, .11, .104, .1), ceramic, 'CN_White', .97, 18, 10)
    ph, ps = np.meshgrid(np.linspace(-1.05, 1.05, 10), np.linspace(.3, -.28, 4))
    V = np.stack([hc[0] + .114 * np.cos(ps) * np.cos(ph), hc[1] + .1 * np.cos(ps) * np.sin(ph), hc[2] - .012 + .11 * np.sin(ps)], -1)
    _sheet(p, V, .006, BLACK, 'CN_Lacquer', _away(hc), k=1.0, cap=.9)
    for s in (-1, 1):
        d = np.array([math.cos(.36), s * math.sin(.36), 0.])
        _shell(p, hc + d * .118 * np.array([1, .88, 1]) + (0, 0, -.006), (.006, .02, .009), LIGHT_BLUE, 'CN_Glow', BLUE_GLOW_TONE, 8, 4,
               R=_basis(d), cap=None)
        _limb(p, [hc + (-.01, s * .088, 0), hc + (-.01, s * .112, 0)], [.034, .034], SLATE, 'CN_Metal', 12, .9)
        _torus(p, hc + (-.01, s * .113, 0), .028, .005, _tone(GOLD_PALE, 1.0, None), 'CN_Gold', 12, 4, axis='y')
    _limb(p, [hc + (-.04, .1, .04), hc + (-.05, .11, .118)], [.005, .003], SLATE, 'CN_Metal', 5, .9)
    _shell(p, hc + (-.05, .11, .122), (.008, .008, .008), GOLD, 'CN_Gold', 1.0, 6, 4, cap=None)
    a = np.linspace(.55, math.pi - .35, 12)
    _seam(p, np.stack([hc[0] + np.where(np.cos(a) > 0, .109, .105) * np.cos(a), np.zeros(12), hc[2] + .111 * np.sin(a)], -1))
    return p


def _turned(part, profile, colour, slot, sides=24):
    """A lathe-turned solid from a profile [(r, z), ...] that runs from the bottom face's rim up to the top face's
    rim (no points on the axis, which would make slivers): the side is lathed and both ends get flat caps."""
    rings = lathe(part, profile, colour, slot, sides)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    for (r, z), toward in ((profile[0], (0, 0, -1)), (profile[-1], (0, 0, 1))):
        ring = np.stack([r * np.cos(ang), r * np.sin(ang), np.full(sides, z)], -1)
        c = np.asarray(colour, np.float64)
        part.add(ring, [list(range(sides)) if np.dot(np.cross(ring[1] - ring[0], ring[2] - ring[0]), toward) > 0 else list(range(sides))[::-1]],
                 c, slot, False)
    return rings


def courier():
    """Unit Quill, the courier: a white egg-shaped hull hovering over its charging dock, a single light-blue
    lens in a black sensor head, a gold band, a cargo drawer at its back and two small arms folded at its sides."""
    p = Part('SM_CP_Courier', ('CN_White', 'CN_Metal', 'CN_Black', 'CN_Gold', 'CN_Glow', 'CN_Lacquer'))
    ceramic = WHITE_COOL
    # The dock: a low steel disc with a gold rim and a ring of light where the hull's field meets it.
    _turned(p, [(.3, 0.0), (.322, .012), (.315, .03), (.25, .038)], _tone(SLATE, .85, None), 'CN_Metal', 28)
    _torus(p, (0, 0, .03), .316, .006, _tone(GOLD, .95, None), 'CN_Gold', 32, 5)
    _torus(p, (0, 0, .039), .2, .007, _tone(LIGHT_BLUE, .8, None), 'CN_Glow', 28, 5)
    _turned(p, [(.12, .0385), (.12, .041)], _tone(LIGHT_BLUE, .45, None), 'CN_Glow', 20)
    # The hull.
    hull_c = np.array([0, 0, .73])
    _shell(p, hull_c, (.24, .22, .26, .25, .27), ceramic, 'CN_White', .97, 22, 12, shade=lambda L: .9 + .1 * np.clip(L[..., 2] / .25 + .5, 0, 1))
    _torus(p, hull_c + (0, 0, .03), .237, .011, _tone(GOLD, 1.0, None), 'CN_Gold', 36, 6)
    for z in (-.11, .15):
        rz = math.sqrt(max(0., 1 - (z / (.26 if z > 0 else .27)) ** 2))
        _seam(p, _ellipse((0, 0), .243 * rz, .223 * rz, hull_c[2] + z, 24), r=.003, closed=True)
    # The field emitter under the hull.
    _turned(p, [(.08, .47), (.1, .49), (.09, .52), (.05, .53)], _tone(SLATE, .8, None), 'CN_Metal', 18)
    _turned(p, [(.065, .465), (.065, .469)], _tone(LIGHT_BLUE, .9, None), 'CN_Glow', 16)
    # Sensor head: a black dome with the lens in a steel bezel, two short aerials.
    head_c = np.array([.02, 0, 1.035])
    _shell(p, head_c, (.12, .12, .14, .115, .07), BLACK, 'CN_Lacquer', 1.0, 18, 9)
    _torus(p, head_c + (0, 0, -.045), .118, .01, _tone(ASH, 1.0, None), 'CN_Metal', 28, 5)
    lens_c = head_c + np.array([.11, 0, .02])
    _limb(p, [lens_c - (.02, 0, 0), lens_c + (.012, 0, 0)], [.045, .042], SLATE, 'CN_Metal', 16, 1.0, None)
    _shell(p, lens_c + (.012, 0, 0), (.012, .034, .034), LIGHT_BLUE, 'CN_Glow', BLUE_GLOW_TONE, 14, 6, cap=None)
    _torus(p, lens_c + (.012, 0, 0), .038, .004, _tone(GOLD_PALE, 1.0, None), 'CN_Gold', 18, 4, axis='x')
    for s in (-1, 1):
        a = head_c + (-.06, s * .06, .1)
        _limb(p, [a, a + (-.03, s * .01, .06)], [.0045, .0025], SLATE, 'CN_Metal', 5, 1.0, None)
        _shell(p, a + (-.03, s * .01, .063), (.006, .006, .006), GOLD, 'CN_Gold', 1.0, 6, 4, cap=None)
    # The cargo drawer at the back: a steel box set into the hull, a gold pull.
    _box(p, (-.235, 0, .74), (.045, .13, .11), SLATE, 'CN_Metal', .015, .9)
    _box(p, (-.282, 0, .74), (.004, .118, .098), CHARCOAL, 'CN_Black', .004, .8)
    _limb(p, [(-.29, -.05, .76), (-.3, -.05, .76), (-.3, .05, .76), (-.29, .05, .76)], .0045, GOLD, 'CN_Gold', 6, 1.0, None)
    # Two small arms folded against the hull's sides, two-fingered grippers.
    for s in (-1, 1):
        sh = np.array([.06, s * .215, .82])
        el = sh + (-.02, s * .03, -.15)
        wr = el + (.12, s * .0, -.02)
        _joint(p, sh, .03, sides=8, rings=5)
        _pod(p, sh, el, .022, ceramic, 'CN_White', 10, 6, k=.95)
        _joint(p, el, .02, sides=8, rings=4)
        _pod(p, el, wr, .02, ceramic, 'CN_White', 10, 6, k=.95)
        for dz in (-.012, .012):
            _limb(p, [wr, wr + (.03, 0, dz * 1.5), wr + (.05, 0, dz * .6)], [.006, .005, .004], SLATE, 'CN_Metal', 5, 1.0, None)
    return p


def mechanoid():
    """Forge-Mother Ilex: a four-armed Mechanoid of the Foundry, 2.6 m: black steel under sooty white plates and
    gold trim, a furnace glowing gold behind the grille in her chest, exhaust stacks on her back, gold eyes in a
    low helm; her big arms hang ready, the small ones hold a forging hammer and tongs."""
    p = Part('SM_CP_Mechanoid', ('CN_White', 'CN_Metal', 'CN_Black', 'CN_Gold', 'CN_Glow'))
    plate = ASH
    soot = lambda L: .55 + .45 * np.clip((L[..., 2] + .1) / .4, 0, 1)
    for s in (-1, 1):
        y = s * .23
        _box(p, (.08, y, .06), (.22, .11, .06), CHARCOAL, 'CN_Metal', .03, .7)
        _box(p, (.27, y, .05), (.05, .1, .045), plate, 'CN_White', .02, .62)
        _joint(p, (0, y, .19), .095, sides=10, rings=6, k=.75)
        _pod(p, (0, y, .24), (.02, y, .86), .14, plate, 'CN_White', 14, 8, squash=1.1, k=.7, shade=soot)
        _limb(p, [(-.12, y, .3), (-.11, y, .82)], [.03, .03], SLATE, 'CN_Metal', 8, .7)
        _joint(p, (.02, y, .93), .11, sides=10, rings=6)
        _plate(p, (.13, y, .95), _basis((1, 0, .15)), .17, .2, .025, .014, plate, 'CN_White', k=.8, nu=5, nv=5, trim=GOLD_PALE, trim_r=.005)
        _pod(p, (.02, y * .96, .98), (0, y * .92, 1.42), .17, plate, 'CN_White', 14, 8, squash=1.05, k=.82)
        _joint(p, (0, y * .9, 1.47), .12, sides=10, rings=6)
    _hull(p, ((1.36, .22, .16, .18), (1.42, .3, .2, .22), (1.52, .32, .22, .24), (1.6, .28, .2, .22)), plate, 'CN_White', nu=20, k=.84)
    _hull(p, ((1.58, .26, .2, .2), (1.7, .3, .24, .24), (1.85, .38, .3, .28), (2.0, .43, .33, .3), (2.15, .45, .32, .3),
              (2.28, .42, .28, .27), (2.36, .3, .2, .22)), plate, 'CN_White', nu=24, k=.88)
    _seam(p, _ellipse((0, 0), .27, .33, 1.72, 24), r=.007, closed=True)
    # The furnace behind its grille.
    fc = np.array([.325, 0, 2.02])
    R = _basis((1, 0, 0))
    _shell(p, fc - (.01, 0, 0), (.02, .14, .14), GLOW_GOLD, 'CN_Glow', GOLD_GLOW_TONE, 16, 6, R=R, cap=None)
    _torus(p, fc + (.005, 0, 0), .145, .016, _tone(GOLD, 1.0, None), 'CN_Gold', 28, 6, axis='x')
    for z in np.linspace(-.1, .1, 6):
        w = math.sqrt(max(0., .145 ** 2 - z ** 2))
        _box(p, fc + (.012, 0, z), (.006, w, .0075), CHARCOAL, 'CN_Metal', .003, .8)
    # Exhaust stacks on the back, sooted at the top.
    for s in (-1, 1):
        _limb(p, [(-.26, s * .15, 1.95), (-.3, s * .16, 2.4), (-.3, s * .16, 2.57)], [.06, .055, .055], CHARCOAL, 'CN_Metal', 12, .8)
        _torus(p, (-.3, s * .16, 2.57), .055, .012, _tone(SLATE, .6, None), 'CN_Metal', 14, 5)
    # Helm: low and forward, a gold-lit visor slit.
    hc = np.array([.13, 0, 2.43])
    _hull(p, ((2.34, .12, .14, .14), (2.4, .15, .19, .15), (2.47, .14, .19, .15), (2.53, .1, .13, .12), (2.56, .05, .07, .07)),
          plate, 'CN_White', nu=20, k=.92, centre=(hc[0], 0.))
    _box(p, hc + (.19, 0, .015), (.008, .1, .012), GLOW_GOLD, 'CN_Glow', .004, GOLD_GLOW_TONE, cap=None)
    _box(p, hc + (.185, 0, .015), (.006, .115, .022), BLACK, 'CN_Black', .006, 1.0)
    # The big arms: shoulders, upper arms, forearms bent forward, three-fingered hands.
    for s in (-1, 1):
        sh = np.array([0, s * .5, 2.2])
        _joint(p, sh, .13, sides=10, rings=6)
        _shell(p, sh + (0, s * .03, .07), (.2, .18, .14, .2, .07), plate, 'CN_White', .9, 14, 7)
        _torus(p, sh + (0, s * .03, .03), .19, .01, _tone(GOLD_PALE, .95, None), 'CN_Gold', 24, 4)
        el = np.array([.1, s * .58, 1.72])
        wr = np.array([.38, s * .55, 1.45])
        _pod(p, sh, el, .125, plate, 'CN_White', 12, 7, k=.86)
        _joint(p, el, .095, sides=10, rings=5)
        _pod(p, el, wr, .115, plate, 'CN_White', 12, 7, k=.82)
        _joint(p, wr, .07, sides=8, rings=5)
        for i, (dy, dz) in enumerate(((-.05, 0), (.05, 0), (0, .06))):
            base = wr + (.05, s * dy, -.02 + dz * 0)
            f1 = base + (.08, s * dy * .4, -.08 + dz)
            f2 = f1 + (.06, 0, -.09)
            _limb(p, [base, f1, f2], [.03, .026, .015], SLATE, 'CN_Metal', 7, .85, None)
            _joint(p, f1, .03, sides=6, rings=4)
    # The small arms from the lower ribs: the right holds a forging hammer, the left a pair of tongs.
    for s in (-1, 1):
        sh = np.array([.15, s * .36, 1.86])
        el = np.array([.3, s * .45, 1.6])
        wr = np.array([.48, s * .42, 1.42])
        _joint(p, sh, .07, sides=8, rings=5)
        _pod(p, sh, el, .06, plate, 'CN_White', 10, 6, k=.85)
        _joint(p, el, .055, sides=8, rings=5)
        _pod(p, el, wr, .05, plate, 'CN_White', 10, 6, k=.82)
        _joint(p, wr, .045, sides=8, rings=4)
        grip = wr + (.05, 0, -.03)
        _box(p, grip, (.04, .035, .05), SLATE, 'CN_Metal', .012, .85)
        if s > 0:
            _limb(p, [grip + (0, 0, .25), grip + (0, 0, -.9)], [.022, .022], CHARCOAL, 'CN_Black', 8, .9)
            _box(p, grip + (0, 0, -.98), (.13, .06, .07), CHARCOAL, 'CN_Metal', .02, .7)
            _box(p, grip + (.14, 0, -.98), (.015, .07, .08), GOLD, 'CN_Gold', .01, .9, cap=None)
        else:
            for dy in (-.012, .012):
                _limb(p, [grip + (0, dy, .04), grip + (.03, dy * 2, -.3), grip + (.08, dy * 4, -.52)], [.01, .009, .008], SLATE, 'CN_Metal', 6, .8)
    return p


def mecha():
    """Patience: an old First One Mecha seated on the ground, 7 m, knees raised and forearms resting on them, his
    head bowed. Ivory armour worn and dusty, gold trim rubbed pale, black joints, a visor that barely glows."""
    p = Part('SM_CP_Mecha', ('CN_White', 'CN_Metal', 'CN_Black', 'CN_Gold', 'CN_Glow'))
    ivory = IVORY
    dust = lambda L: .72 + .28 * np.clip(.5 + L[..., 2] / 1.4, 0, 1)
    # Pelvis on the ground and the torso leaning a little forward.
    _hull(p, ((0.0, .9, .9, 1.0), (.35, 1.15, 1.05, 1.15), (.9, 1.2, 1.0, 1.15), (1.4, 1.0, .85, 1.0)), ivory, 'CN_White', nu=24, k=.8)
    torso = ((1.3, .95, .8, .95), (1.9, 1.0, .9, 1.0), (2.6, 1.18, 1.05, 1.05), (3.3, 1.35, 1.15, 1.1), (3.9, 1.42, 1.15, 1.1),
             (4.4, 1.32, 1.0, 1.05), (4.75, .95, .75, .85), (4.9, .55, .5, .55))
    _hull(p, torso, ivory, 'CN_White', nu=24, k=.9, centre=(.15, 0.))
    for z, rx, ry in ((2.25, 1.02, 1.1), (3.0, 1.15, 1.28)):
        _seam(p, _ellipse((.15, 0), rx, ry, z, 28), r=.03, base=SLATE, closed=True)
    # Chest plates with gold borders, and the dark core under them, set into the torso's front where it leans
    # forward (on its surface: inside the hull it would not show at all), in a pale gold ring.
    for s in (-1, 1):
        _plate(p, (1.2, s * .55, 3.75), _basis((1, s * .35, .1)), .95, .9, .1, .06, ivory, 'CN_White', k=.95, nu=5, nv=5, trim=GOLD_PALE,
               trim_r=.025, trim_k=.9)
    zs, fronts = [r[0] for r in torso], [r[2] + .15 for r in torso]
    core = np.array([float(np.interp(3.15, zs, fronts)), 0., 3.15])
    lean = (np.interp(3.38, zs, fronts) - np.interp(2.92, zs, fronts)) / .46
    nrm = np.array([1., 0., -lean]) / math.hypot(1., lean)
    _shell(p, core - nrm * .025, (.06, .2, .2), LIGHT_WHITE, 'CN_Glow', .25, 12, 6, R=_basis(nrm), cap=None)
    ring = Part('tmp', p.slots)
    _torus(ring, (0, 0, 0), .23, .035, _tone(GOLD_PALE, .9, None), 'CN_Gold', 20, 6, axis='x')
    _merge(p, ring, _basis(nrm), core + nrm * .006)
    # Back: a thruster housing with vents.
    _box(p, (-1.15, 0, 3.4), (.3, .8, .9), SLATE, 'CN_Metal', .12, .7)
    for z in np.linspace(2.8, 4.0, 5):
        _box(p, (-1.46, 0, z), (.02, .6, .05), CHARCOAL, 'CN_Black', .015, .7)
    # Head, bowed: a long helm, a dim visor, two swept gold crest fins.
    hc = np.array([.85, 0, 5.55])
    _limb(p, [(.3, 0, 4.85), (.6, 0, 5.2)], [.38, .34], SLATE, 'CN_Metal', 12, .8)
    R = _rot((0, 1, 0), 22)
    _shell(p, hc, (.62, .5, .6, .55, .45), ivory, 'CN_White', .95, 16, 9, R=R)
    ph, ps = np.meshgrid(np.linspace(-.8, .8, 9), np.linspace(.18, -.12, 3))
    V = np.stack([.645 * np.cos(ps) * np.cos(ph), .52 * np.cos(ps) * np.sin(ph), .6 * np.sin(ps)], -1) @ R.T + hc
    _sheet(p, V, .03, BLACK, 'CN_Black', _away(hc), k=1.0)
    V2 = np.stack([.66 * np.cos(ps[1:2]) * np.cos(ph[1:2]), .53 * np.cos(ps[1:2]) * np.sin(ph[1:2]), .6 * np.sin(ps[1:2])], -1) @ R.T + hc
    _limb(p, V2[0], .022, LIGHT_WHITE, 'CN_Glow', 6, .3, None)
    # A gold V crest rising from the brow, the mark of a First One Mecha.
    root = hc + R @ np.array([.5, 0, .22])
    face = R @ np.array([1., 0, 0])
    for s in (-1, 1):
        d = R @ np.array([.12, s * .58, .8])
        d /= np.linalg.norm(d)
        x = face - d * np.dot(face, d)
        x /= np.linalg.norm(x)
        M = np.stack([x, np.cross(d, x), d], 1)
        # Sheet gold, thinner than the fin's tip is wide, so the back face cannot fold through the front there (three
        # columns: with more, round_ this strong bends the corner columns back past their neighbours).
        _plate(p, root + d * .48, M, .14, .95, .015, .011, GOLD_PALE, 'CN_Gold', k=.92, nu=3, nv=6, round_=.85)
    _box(p, root, (.06, .1, .07), GOLD_PALE, 'CN_Gold', .02, .9, R, cap=None)
    # Shoulders and arms, forearms resting on the knees, hands hanging over them.
    for s in (-1, 1):
        sh = np.array([.1, s * 1.55, 4.35])
        _joint(p, sh, .42, sides=12, rings=7)
        _shell(p, sh + (0, s * .1, .25), (.62, .58, .45, .62, .25), ivory, 'CN_White', .92, 16, 8)
        _torus(p, sh + (0, s * .1, .1), .6, .035, _tone(GOLD_PALE, .9, None), 'CN_Gold', 24, 5)
        el = np.array([1.1, s * 1.85, 2.95])
        wr = np.array([2.55, s * 1.42, 3.05])
        _pod(p, sh, el, .34, ivory, 'CN_White', 14, 8, k=.9, shade=dust)
        _joint(p, el, .3, sides=10, rings=6)
        _pod(p, el, wr, .32, ivory, 'CN_White', 14, 8, k=.88, shade=dust)
        _joint(p, wr, .2, sides=10, rings=5)
        palm = wr + np.array([.3, -s * .05, -.15])
        _box(p, palm, (.25, .2, .12), SLATE, 'CN_Metal', .05, .85)
        for i, dy in enumerate((-.14, -.05, .05, .14)):
            root = palm + (.22, s * dy, -.05)
            f1 = root + (.18, 0, -.2)
            f2 = f1 + (.05, 0, -.28)
            _limb(p, [root, f1, f2], [.06, .055, .04], SLATE, 'CN_Metal', 7, .85, None)
            _joint(p, f1, .06, sides=6, rings=4)
        t0 = palm + (.1, -s * .2, -.05)
        _limb(p, [t0, t0 + (.15, -s * .08, -.2), t0 + (.22, -s * .06, -.4)], [.065, .055, .04], SLATE, 'CN_Metal', 7, .85, None)
    # Legs: thighs from the hips up to the raised knees, shins down to the feet flat on the ground.
    for s in (-1, 1):
        hip = np.array([.35, s * .75, .75])
        kn = np.array([2.65, s * 1.15, 2.55])
        an = np.array([3.05, s * 1.05, .62])
        _joint(p, hip, .5, sides=12, rings=6, k=.8)
        _pod(p, hip, kn, .52, ivory, 'CN_White', 14, 8, k=.86, shade=dust)
        _joint(p, kn, .42, sides=12, rings=6)
        _plate(p, kn + (.4, 0, .1), _basis((1, 0, .4)), .7, .7, .1, .06, ivory, 'CN_White', k=.95, nu=4, nv=4, trim=GOLD_PALE, trim_r=.02)
        _pod(p, kn, an, .4, ivory, 'CN_White', 14, 8, k=.82, shade=dust)
        _joint(p, an, .3, sides=10, rings=5, k=.75)
        _box(p, (3.35, s * 1.05, .2), (.75, .42, .2), SLATE, 'CN_Metal', .08, .65)
        _box(p, (3.25, s * 1.05, .48), (.5, .36, .12), ivory, 'CN_White', .06, .7)
    # Seated, he reaches from his thruster housing to his toes: the pivot goes to the middle of that footprint
    # (README: a ground mesh's footprint is centred on the origin), not his pelvis, about 1.5 m behind it.
    _to_height(p, 7.0)
    v = np.asarray(p.v, np.float64)
    v[:, :2] -= (v[:, :2].min(0) + v[:, :2].max(0)) / 2
    p.v = v.tolist()
    return p


def lightform():
    """Iriel, a Lightform: a tall figure of light, 2.1 m, its core burning white inside a light-blue veil of
    hardened light that falls like a robe and trails to the ground; a gold circlet, two rings of light about its
    head, one hand raised as it teaches, motes drifting round it."""
    p = Part('SM_CP_Lightform', ('CN_Glow', 'CN_Glass', 'CN_Gold'))
    rng = np.random.default_rng(601)
    core = lambda k: _tone(LIGHT_WHITE, k, None)
    blue = lambda k: _tone(LIGHT_BLUE, k, None)
    # Core: a slender lathe from the hem's light to the shoulders, brightest at the heart.
    prof = [(.02, .08), (.15, .1), (.16, .35), (.13, .8), (.11, 1.15), (.12, 1.35), (.15, 1.5), (.13, 1.6), (.06, 1.66), (.035, 1.72)]
    _turned(p, prof, core(.85), 'CN_Glow', 20)
    # The veil: a robe of light-blue glass around the core, its folds hanging, open a little at the front.
    th = np.linspace(-math.pi, math.pi, 36, endpoint=False)
    rows = []
    zs = (.14, .3, .45, .65, .85, 1.02, 1.2, 1.4, 1.55, 1.63, 1.7)
    for z, r in zip(zs, np.interp(zs, [.14, .45, .85, 1.2, 1.4, 1.55, 1.63, 1.7], [.3, .27, .22, .18, .17, .2, .17, .09])):
        fold = 1 + .07 * np.sin(th * 7 + z * 1.2) * np.clip((1.3 - z) / .6, 0, 1)
        rows.append(np.stack([r * fold * np.cos(th) * 1.05, r * fold * np.sin(th), np.full(len(th), z)], -1))
    V = np.array(rows)
    _sheet(p, V, .006, BLUE_PALE, 'CN_Glass', _axis(), k=1.0, closed=True, cap=.9)
    # Trailing light below the hem down to the floor.
    for i in range(9):
        a = i * 2 * math.pi / 9 + rng.uniform(-.2, .2)
        top = np.array([.27 * math.cos(a), .27 * math.sin(a), .16])
        pts = [top, top * np.array([1.08, 1.08, .5]) + (rng.uniform(-.02, .02), rng.uniform(-.02, .02), 0), top * np.array([1.15, 1.15, 0]) + (0, 0, .002)]
        _limb(p, pts, [.025, .016, .004], LIGHT_BLUE, 'CN_Glow', 6, .8, None)
    # Head: a bright ovoid in a hood of veil, a gold circlet, two tilted rings of light.
    hc = np.array([.02, 0, 1.86])
    _limb(p, [(0, 0, 1.68), (.01, 0, 1.78)], [.045, .04], core(.7), 'CN_Glow', 10, 1.0, None)
    _shell(p, hc, (.1, .085, .12, .095, .1), LIGHT_WHITE, 'CN_Glow', 1.0, 16, 9, cap=None)
    _shell(p, hc + (-.01, 0, .01), (.12, .105, .145, .12, .12), BLUE_PALE, 'CN_Glass', 1.0, 18, 10)
    _torus(p, hc + (0, 0, .04), .113, .006, _tone(GOLD, 1.0, None), 'CN_Gold', 28, 5)
    for tilt, r in ((14, .19), (-9, .23)):
        ring = Part('tmp', p.slots)
        _torus(ring, (0, 0, 0), r, .005, blue(1.0), 'CN_Glow', 36, 4)
        _merge(p, ring, _rot((1, 0, 0), tilt) @ _rot((0, 1, 0), 8), hc + (0, 0, .1))
    # Arms of light in veil sleeves: the left hangs, the right is raised before the chest, palm up.
    arms = {-1: [(0, -.17, 1.52), (-.01, -.21, 1.25), (.03, -.22, 1.02), (.06, -.2, .9)],
            1: [(0, .17, 1.52), (.05, .23, 1.28), (.25, .18, 1.25), (.36, .12, 1.32)]}
    for s, pts in arms.items():
        pts = np.array(pts)
        _limb(p, pts, [.04, .033, .028, .02], core(.8), 'CN_Glow', 8, 1.0, None)
        # The sleeve starts a little down the arm, so its end cap and the arm's do not lie in one plane.
        sleeve = np.concatenate([pts[:1] + .15 * (pts[1:2] - pts[:1]), pts[1:3]])
        _limb(p, sleeve, [.06, .055, .05], BLUE_PALE, 'CN_Glass', 10, 1.0)
        hand = pts[-1]
        for f in range(4):
            d = np.array([.05, s * (f - 1.5) * .012, .025 if s > 0 else -.05])
            if s < 0:
                d = np.array([.01 + .004 * f, s * (f - 1.5) * .01, -.06])
            _limb(p, [hand, hand + d * .5 + (0, 0, .01), hand + d], [.009, .007, .003], core(.9), 'CN_Glow', 5, 1.0, None)
    # Motes drifting about it.
    for i in range(12):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(.35, .55)
        q = (rr * math.cos(a), rr * math.sin(a), rng.uniform(.4, 2.0))
        _shell(p, q, (.012, .012, .012), LIGHT_BLUE, 'CN_Glow', rng.uniform(.6, 1.0), 6, 4, cap=None)
    return _to_height(p, 2.1)


def wisp():
    """The Wisp: a lost Lightform child, 0.8 m: a small bright body and head inside light-blue glass, two little
    arms of light reaching forward, a tail of light curling down to the ground, and a few motes."""
    p = Part('SM_CP_Wisp', ('CN_Glow', 'CN_Glass'))
    rng = np.random.default_rng(611)
    body = np.array([0, 0, .44])
    _shell(p, body, (.1, .1, .13), LIGHT_WHITE, 'CN_Glow', .95, 16, 9, cap=None)
    # The glass round the body is a small robe, full below and narrowing to the neck, so body and head read as a
    # child of light rather than two balls stacked.
    _turned(p, [(.05, .27), (.11, .3), (.145, .37), (.15, .45), (.13, .53), (.095, .59), (.05, .625)], BLUE_PALE, 'CN_Glass', 18)
    head = np.array([.02, 0, .68])
    _shell(p, head, (.075, .07, .08), LIGHT_WHITE, 'CN_Glow', 1.0, 14, 8, cap=None)
    _shell(p, head, (.095, .09, .1), BLUE_PALE, 'CN_Glass', 1.0, 16, 9)
    _limb(p, [body + (0, 0, .12), head - (0, 0, .07)], [.04, .035], _tone(LIGHT_BLUE, .9, None), 'CN_Glow', 8, 1.0, None)
    for s in (-1, 1):
        sh = body + (.02, s * .11, .06)
        _limb(p, [sh, sh + (.07, s * .05, -.03), sh + (.14, s * .03, .0)], [.022, .016, .007], _tone(LIGHT_BLUE, 1.0, None), 'CN_Glow', 6, 1.0, None)
    t = np.linspace(0, 1, 14)
    tail = np.stack([-.03 - .06 * t + .05 * np.sin(t * 5), .06 * np.sin(t * 7), .32 * (1 - t) ** 1.2 + .002], -1)
    tail[0] = body - (0, 0, .1)
    _limb(p, tail, np.linspace(.06, .006, 14), _tone(LIGHT_BLUE, .85, None), 'CN_Glow', 8, 1.0, None)
    for i in range(6):
        a = rng.uniform(0, 2 * math.pi)
        q = (.22 * math.cos(a), .22 * math.sin(a), rng.uniform(.25, .75))
        _shell(p, q, (.01, .01, .01), LIGHT_BLUE, 'CN_Glow', rng.uniform(.6, 1.0), 6, 4, cap=None)
    return p


# ---------------------------------------------------------------- the module's meshes, the cast check, the contract

# Mesh name -> (builder, the body it was modelled on; None for a figure).
BUILT = {
    'SM_CP_G_SkirtSatchel': (skirt_satchel, 'Quinn'), 'SM_CP_G_ApronSkirtWhite': (apron_skirt_white, 'Quinn'),
    'SM_CP_G_ApronSkirtGold': (apron_skirt_gold, 'Quinn'), 'SM_CP_G_SkirtGold': (skirt_gold, 'Quinn'),
    'SM_CP_G_TunicSkirt': (tunic_skirt, 'Quinn'), 'SM_CP_G_RobeSkirt': (robe_skirt, 'Quinn'),
    'SM_CP_G_RobeSkirtTall': (robe_skirt_tall, 'Manny'), 'SM_CP_G_CoatSkirtBlack': (coat_skirt_black, 'Manny'),
    'SM_CP_G_CoatSkirtWhite': (coat_skirt_white, 'Quinn'), 'SM_CP_G_OilskinSkirt': (oilskin_skirt, 'Manny'),
    'SM_CP_G_WorkApronSkirt': (work_apron_skirt, 'Manny'), 'SM_CP_G_GuardBelt': (guard_belt, 'Manny'),
    'SM_CP_G_CoatBlack': (coat_black, 'Manny'), 'SM_CP_G_BlouseStrap': (blouse_strap, 'Quinn'),
    'SM_CP_G_BlouseShawl': (blouse_shawl, 'Quinn'), 'SM_CP_G_Tunic': (tunic, 'Quinn'), 'SM_CP_G_RobeShawl': (robe_shawl, 'Quinn'),
    'SM_CP_G_WorkApron': (work_apron, 'Manny'), 'SM_CP_G_Blouse': (blouse, 'Quinn'), 'SM_CP_G_ArmourVest': (armour_vest, 'Manny'),
    'SM_CP_G_CoatWhite': (coat_white, 'Quinn'), 'SM_CP_G_RobeTall': (robe_tall, 'Manny'), 'SM_CP_G_Oilskin': (oilskin, 'Manny'),
    'SM_CP_G_BlouseBib': (blouse_bib, 'Quinn'),
    'SM_CP_G_SageHair': (sage_hair, 'Manny'), 'SM_CP_G_BunBlack': (bun_black, 'Quinn'), 'SM_CP_G_BunWhite': (bun_white, 'Quinn'),
    'SM_CP_G_ShortHair': (short_hair, 'Quinn'), 'SM_CP_G_StrawHat': (straw_hat, 'Quinn'), 'SM_CP_G_CapRed': (cap_red, 'Manny'),
    'SM_CP_G_HeadscarfRed': (headscarf_red, 'Quinn'), 'SM_CP_G_Helmet': (helmet, 'Manny'), 'SM_CP_G_BobBlack': (bob_black, 'Quinn'),
    'SM_CP_G_HoodHalo': (hood_halo, 'Manny'), 'SM_CP_G_KnitCapBeard': (knit_cap_beard, 'Manny'), 'SM_CP_G_FieldHat': (field_hat, 'Quinn'),
    'SM_CP_Robot': (robot, None), 'SM_CP_Courier': (courier, None), 'SM_CP_Mechanoid': (mechanoid, None), 'SM_CP_Mecha': (mecha, None),
    'SM_CP_Lightform': (lightform, None), 'SM_CP_Wisp': (wisp, None),
}


def _cast_problems():
    """Everything wrong between the cast and this module, in both tables (the scenario uses whichever LOOKS picks,
    and flipping LOOKS is the rollback): a person without a look, a look for nobody, a mesh that is not built here, a
    garment on a body it was not modelled on, a figure given a body, and a look that disagrees with the lore's mesh
    about who is a figure (the scenario's look() prefers CAST, so the lore would be ignored). A MetaHuman row (one
    with 'mh') keeps the Mannequin look that stands in until its Look is assembled, so it passes the same checks; its
    'mh' names the MH entry of its own speaker, a person on a body and not pending, and that entry's rows are exactly
    the lore's rows of that speaker."""
    keys = [row[0] for row in PEOPLE]
    out = []
    for table, cast in (('CAST_MANNEQUIN', CAST_MANNEQUIN), ('CAST_METAHUMAN', CAST_METAHUMAN)):
        out += ['PEOPLE %s has no row in %s' % (k, table) for k in keys if k not in cast]
        out += ['%s %s is not in PEOPLE' % (table, k) for k in cast if k not in keys]
        for key, look in cast.items():
            if look.get('body') not in ('Quinn', 'Manny', None) or look.get('skin') not in ('Porcelain', 'Obsidian', None):
                out.append('%s %s: body %r / skin %r' % (table, key, look.get('body'), look.get('skin')))
            if (look.get('body') is None) == (look.get('shape') is None):
                out.append('%s %s: a person has a body or a shape, not both or neither' % (table, key))
            if look.get('body') and look.get('skin') is None:
                out.append('%s %s: a body without a skin' % (table, key))
            if not isinstance(look.get('scale'), (int, float)) or not .5 <= look['scale'] <= 1.25:
                out.append('%s %s: scale %r' % (table, key, look.get('scale')))
            for field in ('lower', 'upper', 'head', 'shape'):
                name = look.get(field)
                if name is None:
                    continue
                garment = field != 'shape'
                if name not in BUILT or name.startswith('SM_CP_G_') != garment:
                    out.append('%s %s: %s %s is not a %s people.py builds' % (table, key, field, name, 'garment' if garment else 'figure'))
                elif BUILT[name][1] != (look.get('body') if garment else None):
                    out.append('%s %s: %s %s was modelled on %s, worn by %s' % (table, key, field, name, BUILT[name][1], look.get('body')))
            mh = look.get('mh')
            if mh is not None and (table == 'CAST_MANNEQUIN' or mh not in MH or MH[mh]['pending'] or key not in MH[mh]['rows']
                                   or look.get('body') is None):
                out.append('%s %s: mh %r is not a MetaHuman this row can show' % (table, key, mh))
        speakers = {}
        for row in PEOPLE:
            if row[0] in cast:
                speakers.setdefault(row[1], []).append(cast[row[0]])
                figure = row[2] if row[2] in BUILT and BUILT[row[2]][1] is None else None
                if cast[row[0]].get('shape') != figure:
                    out.append('%s %s: shape %r, but the lore shows %s' % (table, row[0], cast[row[0]].get('shape'), row[2]))
        out += ['%s: %s changes clothes between rows' % (table, s) for s, looks in speakers.items() if any(l != looks[0] for l in looks)]
    for key, entry in MH.items():
        rows = tuple(row[0] for row in PEOPLE if row[1] == entry['name'])
        if not rows or entry['rows'] != rows or key != rows[0]:
            out.append('MH %s: rows %s, but the lore gives %r the rows %s' % (key, entry['rows'], entry['name'], rows))
        shown = [row for row in entry['rows'] if CAST_METAHUMAN.get(row, {}).get('mh') == key]
        if entry['pending'] and shown:
            out.append('MH %s is pending, but CAST_METAHUMAN shows it on %s' % (key, ', '.join(shown)))
        elif not entry['pending'] and len(shown) != len(entry['rows']):
            out.append('MH %s: CAST_METAHUMAN shows it on %s of its rows %s' % (key, shown, entry['rows']))
    return out


_PROBLEMS = _cast_problems()
assert not _PROBLEMS, 'people.py / physis_conclave_cast: ' + '; '.join(_PROBLEMS)


def _named(name, builder):
    """The builder as check.py and the Blender build call it, refusing a mesh whose name drifted from BUILT."""
    def build():
        part = builder()
        if part.name != name:
            raise ValueError('%s built %s' % (name, part.name))
        return part
    build.__name__, build.__doc__ = builder.__name__, builder.__doc__
    return build


MESHES = [_named(name, builder) for name, (builder, _) in BUILT.items()]

# Garments are modelled in actor space over the bind pose, so their lowest point is a hem, not z 0 (the
# pivot that matters is the actor's feet, which every garment shares). Figures stand on z 0; their heights
# are the README's.
CONTRACT = {name: {'pivot': 'any'} for name in BUILT if name.startswith('SM_CP_G_')}
CONTRACT.update({
    'SM_CP_Robot': {'size': (0, 0, 1.8), 'tol': .05, 'pivot': 'base'},
    'SM_CP_Courier': {'size': (0, 0, 1.2), 'tol': .05, 'pivot': 'base'},
    'SM_CP_Mechanoid': {'size': (0, 0, 2.6), 'tol': .05, 'pivot': 'base'},
    'SM_CP_Mecha': {'size': (0, 0, 7.0), 'tol': .05, 'pivot': 'base'},
    'SM_CP_Lightform': {'size': (0, 0, 2.1), 'tol': .05, 'pivot': 'base'},
    'SM_CP_Wisp': {'size': (0, 0, .8), 'tol': .05, 'pivot': 'base'},
})
