"""The Conclave's MetaHuman costumes (level 3; Tools/conclave/PEOPLE_DESIGN.md 3.3, Phase 0 step 6).

Each dressed person (physis_conclave_cast.MH) wears one skinned mesh on metahuman_base_skel, FILES['costume']: the
garments people.py modelled over the Mannequins, refitted to the person's own body; what the bare Mannequin limbs stood in
for (sleeves, trousers, socks, footwear); and the parts of the old headwear that the hair grooms have not replaced.
MH[key]['costume'] lists the pieces and their palette colours. This module builds them with numpy only, so a costume is
built and checked offline; Tools/build_conclave_people.py (headless Blender) reads the person's guides, calls measure()
and costume(), and writes the skinned FBX and the cloth mask.

Frame: people.py's, the Unreal actor frame of the body's reference pose in metres: x forward, y right (the character's
left at -y), z up, feet at z 0. The guides' FBX frame (centimetres, z up, the body facing -y, its left at +x) is this
frame turned and mirrored: from_fbx() converts, and a triangle's corners go in reverse (measure() refuses a guide whose
triangles face inward).

The guide format. people_guides (Content/Python/physis_conclave_people.py) exports the MetaHuman Creator preview's Body
and Face skeletal meshes as Physis's were exported (physis_character_tools export_body_guide, physis_outfit_tools
export_face_guide; Art/Characters/Physis/physis-*-guide.fbx are examples), to FILES['body_guide'] and FILES['face_guide']:
  - binary FBX (SkeletalMeshExporterFBX), z up, front -y, units cm; every LOD a mesh <name>_LOD<n> under a LodGroup, the
    reference skeleton as a bind pose, vertex weights as skin clusters, one UV per vertex (vertices split along seams)
  - the body: metahuman_base_skel (its core deform bones CORE are required), the mesh down from the collarbones, its UVs
    the ones the body's material samples (the cloth mask is baked over them)
  - the face: the head, the neck and a bib down the upper chest, on the face skeleton; its FACIAL_L/R_Eye, FACIAL_L/R_Ear
    and FACIAL_C_NoseBridge joints place spectacles and earrings (when they are not where a face has them, FACE_BOX, the
    Mannequins' places on the person's skull stand in)
The build reads the body's LOD1 (Physis's outfit was fitted to it) and the face's LOD0, labels each vertex with the core
bone carrying most of its weight (a helper, twist or face joint counts for its nearest core ancestor) and hands their
arrays to measure() (read_guide() does the same without Blender, for the test). Its Guide is what every builder here
reads; Guide.record() is the JSON the build writes beside the costume (costume-build.json).

What the builders do with it (people.py's helpers make every solid):
  ported garments   people.py's builders, each with the Mannequin it was modelled on (BUILT[name][1]) as the source of a
                    Port: heights go through the levels both bodies share (LEVELS), drape rows keep their ease over the
                    person's own sections and stay clear of the legs below the crotch, straps follow the person's
                    shoulders to their edges (sleeves meet them now), coats and the gambeson hang across the waist, and
                    headwear follows the person's skull grown by the hair groom's depth (HAIR_DEPTH)
  new pieces        sleeves, trousers, socks and footwear are shells fitted over the body guide's own surface (clipped at
                    their hems, lifted off the skin, relaxed, made solid); the undertop and the shirt's collar and front
                    are drapes; vambraces are plates round the forearms
Every piece's colours are palette colours (check.py checks them as it checks every Conclave mesh, under the SK_ budget),
of the families MH declares for it. A piece with a 'bone' in MH is rigid: all its vertices follow that bone. Skirts,
coats' skirts, aprons and belts hang from the pelvis and follow the thighs toward the hem; everything else takes the
weights of the body or face surface under it. Costume.covered says which body vertices the costume hides from the skin
(always MARGIN inside a hem, a cuff or a neckline; never the hands, the feet under a skirt or the arm down an open
sleeve), which the build bakes into the cloth mask.

Offline: python3 Tools/conclave_meshes/costumes.py builds all twelve costumes on
stand-in guides (the Mannequin a person's CAST row wears, at the person's MH height, with MetaHuman limbs: standin()),
measured back through measure(), and runs check.py's mesh checks and the costume checks on each; --physis adds Physis's own
guides (the real format). check.py costumes runs the mesh checks alone.
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'Content/Python'))

from palette import (ASH, BLACK, BLUE, BLUE_PALE, CHARCOAL, GOLD, GOLD_DEEP, GOLD_PALE, GOLD_STRAW, IVORY,  # noqa: E402
                     LIGHT_BLUE, PALETTE, RED, WHITE, WHITE_COOL, WHITE_PURE, family)
from people import (BUILT, HEAD, JAW, PIT, STRAP, TORSO, Drape, _band, _coil, _band_ring, _basis, _border, _bow, _box,  # noqa: E402
                    _button, _cloth_k, _coat_span, _collar, _edge_mid, _flat_collar, _fringe, _hat, _lapels, _limb,
                    _lobes, _merge, _neck_loop, _arm_loop, _panel, _patch, _path, _peak, _piping, _plate, _ribbon3d, _rot,
                    _satchel, _scalp, _sheet, _shell, _skirt, _skull, _smooth, _strip, _tone, _torus, _tube, _axis, _away,
                    _dir, _shawl_path)
from physis_conclave_cast import CAST_MANNEQUIN, FILES, MH, NEW_PIECES  # noqa: E402
from toolkit import SLOTS, Part, bezier, noise2  # noqa: E402

# ---------------------------------------------------------------- the skeleton

SIDES = ('l', 'r')
# The deform bones that stay on the body at every LOD (Tools/build_physis_outfit.py binds Physis's outfit to the same
# set): a helper, twist or face joint's weight counts for its nearest ancestor among these.
CORE = ('root', 'pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01', 'neck_02', 'head') + tuple(
    '%s_%s' % (bone, side) for side in SIDES for bone in ('clavicle', 'upperarm', 'lowerarm', 'hand', 'thigh', 'calf', 'foot', 'ball'))
TRUNK = ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01', 'neck_02', 'clavicle_l', 'clavicle_r')
ARM_PARTS = ('upperarm', 'lowerarm', 'hand')
# Each limb's joints (its bones' heads, root first) and the labels its sections are cut from.
LIMBS = {'arm_%s' % s: (('upperarm_' + s, 'lowerarm_' + s, 'hand_' + s), ('upperarm_' + s, 'lowerarm_' + s)) for s in SIDES}
LIMBS.update({'leg_%s' % s: (('thigh_' + s, 'calf_' + s, 'foot_' + s), ('thigh_' + s, 'calf_' + s)) for s in SIDES})
FOOT = {s: ('foot_' + s, 'ball_' + s) for s in SIDES}
SIDE_SIGN = {'l': -1.0, 'r': 1.0}  # the character's left is -y
# FACIAL_* joints of the face skeleton that place spectacles and earrings (people_guides exports them with the face).
FACE_JOINTS = {'eye': 'FACIAL_%s_Eye', 'ear': 'FACIAL_%s_Ear'}
BRIDGE_JOINT = 'FACIAL_C_NoseBridge'

# ---------------------------------------------------------------- measuring a body

WELD = 1e-5        # m: guide vertices this close are one (UV seams split the guide's vertices)
ROUNDEST = 2.2      # the roundest drape exponent a garment uses (people.Drape's default): the trunk table holds the
                    # body for it, so every squarer drape (tops use 2.4) holds the body too
TRUNK_STEP = .02    # m between the trunk table's sections: garment features are no finer than this
LIMB_STEP = .02     # m between a limb's radius stations
CROTCH_GAP = .006   # m: a section point this near the midline belongs to the crotch (the legs part below it)
CHIN_STEP = .03     # m: the chin is where the face's middle stands this much further forward than the throat
SHOULDER_DROP = .02 # m: the shoulder line is where the shoulders' half-width has fallen this far from its widest
                    # (people.SHOULDER on both Mannequins: 1.43 and 1.445)
NECK_FLARE = 1.35   # the neck's base is where the body is this many times wider than the neck under the jaw
ARMPIT_REACH = .03  # m beyond the shoulder joint's side within which the arm's lowest point is the armpit
STRAP_NECK = .014   # m from the neck's side to a strap's neck-side edge (people.STRAP less the Mannequins' necks)
STRAP_ARM = .004    # m inside the shoulders' half-width at the shoulder line for a strap's arm-side edge: tops now
                    # meet sleeves, so straps reach the shoulder's edge (people.py's stopped short of the bare arms)
SKULL_BAND = (.045, .095)  # the skull's widest-and-longest height is searched this far below the crown (x scale)
SOURCE_HEIGHT = 1.80       # the Mannequins' crown (people.HEAD: centre 1.703 + top .097)
SOURCE_CHIN = 1.555        # the Mannequins' chin (people.JAW: the jaw's front is widest there, the beard hangs below)
SOURCE_HEAD = 1.625        # the Mannequins' head bone (people.py's headwear checks)
LEVELS = ('ankle', 'knee', 'crotch', 'waist', 'pit', 'shoulder', 'neck', 'chin', 'head', 'skull', 'crown')

# The MetaHuman reference pose's limbs for stand-ins, as fractions of the crown's height, from Physis's body guide
# (Art/Characters/Physis/physis-body-guide.fbx, 2026-10-30, crown 1.681 m): joints (x, |y|, z) root first, and the mean
# radius at fractions of the chain's length (the upper arm or thigh is the first half). The arms hang about 52 degrees
# below level with the forearms turned forward, the feet stand apart.
STANDIN_JOINTS = {'arm': ((-.0149, .0874, .7971), (-.0101, .1868, .6669), (.0845, .2641, .5747)),
                  'leg': ((.0116, .0529, .5422), (.0063, .0650, .2845), (-.0029, .0755, .0455))}
STANDIN_RADII = {'arm': ((0., .0286), (.1, .0250), (.2, .0226), (.3, .0214), (.5, .0202), (.6, .0190), (.7, .0173),
                         (.8, .0143), (.9, .0119), (1., .0113)),
                 # the thigh starts thinner than Physis's .0506, so a stand-in's legs part at its crotch as a body's do
                 'leg': ((0., .0430), (.1, .0470), (.2, .0450), (.3, .0405), (.4, .0345), (.5, .0297), (.6, .0280),
                         (.7, .0286), (.8, .0238), (.9, .0184), (1., .0196))}
STANDIN_FOOT = (-.0321, .1148, .0898, .0297, .0434, .0125)  # heel x, toe x, centre |y|, half-width, instep top, toe top
FOOT_SIDES = 12                                               # a stand-in foot's points round, enough for a shoe over it
STANDIN_HAND = (.1011, .0250, .0110)                          # length along the forearm, half-width, half-thickness
# Face joints of a stand-in, on the Mannequins' heads (people.py's spectacles sat on these eyes): eye centre, ear.
STANDIN_FACE = {'eye': (.088, .031, 1.697), 'ear': (-.006, .066, 1.675)}  # the ear joints 2.2 cm under the eyes, as Physis's
STANDIN_BRIDGE = (.106, 1.70)


def _edges(tris):
    """The mesh's undirected edges, each once."""
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    return np.unique(e, axis=0)


def _cut(points, edges, origin, normal):
    """The points where edges cross the plane through origin with that normal: a section of the mesh."""
    d = (points - origin) @ normal
    a, b = d[edges[:, 0]], d[edges[:, 1]]
    m = (a > 0) != (b > 0)
    t = a[m] / (a[m] - b[m])
    pa, pb = points[edges[m, 0]], points[edges[m, 1]]
    return pa + t[:, None] * (pb - pa)


def _volume(points, tris):
    """The signed volume a surface encloses about its own centre: positive when its triangles face outward (a guide is
    open at the neck or the bib, which barely shifts it from there)."""
    o = points.mean(0)
    a, b, c = points[tris[:, 0]] - o, points[tris[:, 1]] - o, points[tris[:, 2]] - o
    return float(np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6)


def _majority(tris, keep):
    """The triangles at least two of whose corners are kept (a label boundary runs through the others)."""
    return tris[keep[tris].sum(1) >= 2]


def _labelled(labels, names):
    names = set(names)
    return np.array([str(l) in names for l in labels], bool)


def _hold(q, n=ROUNDEST):
    """(hw, f, b): the superellipse of exponent n about x 0, y 0 (people.Drape's section: half-width hw, front f, back b)
    that holds every point of the section q, its extents grown together until none is outside."""
    x, y = q[:, 0], np.abs(q[:, 1])
    hw, f, b = max(float(y.max()), .01), max(float(x.max()), .01), min(float(x.min()), -.01)

    def outside(d):
        a = np.where(x >= 0, f + d, -b + d)
        return np.any(np.abs(x / a) ** n + (y / (hw + d)) ** n > 1 + 1e-9)
    lo, hi = 0.0, .1
    if outside(lo):
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if outside(mid) else (lo, mid)
        return hw + hi, f + hi, b - hi
    return hw, f, b


def _taut(z, v):
    """The upper concave envelope of a profile v(z) (z rising): what cloth stretched over it follows."""
    hull = []
    for p in zip(z, v):
        while len(hull) >= 2 and ((hull[-1][0] - hull[-2][0]) * (p[1] - hull[-2][1]) - (hull[-1][1] - hull[-2][1]) * (p[0] - hull[-2][0])) >= 0:
            hull.pop()
        hull.append(p)
    hz, hv = zip(*hull)
    return np.interp(z, hz, hv)


def _tauten(rows, pit):
    """A trunk table (z, hw, f, b) with its sections below pit replaced by their outer envelope over z."""
    t = np.array(rows, np.float64)
    low = t[:, 0] <= pit
    for i, sign in ((1, 1.), (2, 1.), (3, -1.)):
        t[low, i] = sign * _taut(t[low, 0], sign * t[low, i])
    return t


def _hull2d(xy):
    """The convex hull of 2-D points, counter-clockwise (Andrew's monotone chain)."""
    pts = sorted(set(map(tuple, np.round(np.asarray(xy, np.float64), 6))))

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0]) <= 0:
                out.pop()
            out.append(p)
        return out
    lower, upper = half(pts), half(pts[::-1])
    return np.array(lower[:-1] + upper[:-1])


def _first(z, values, start, limit):
    """The height above start where values (sampled at z) first fall to limit, linearly between samples; None if they
    never do."""
    for i in range(len(z) - 1):
        if z[i + 1] <= start:
            continue
        a, b = values[i] - limit, values[i + 1] - limit
        if b <= 0:
            if a <= 0 and z[i] >= start:
                return float(z[i])
            return float(z[i] + (a / (a - b) if a != b else 0.0) * (z[i + 1] - z[i]))
    return None


def _trunk_levels(rows, crotch, pit, chin, scale, short_neck_hw=None):
    """waist, hip, shoulder, neck and the neck's half-width from a trunk table (z, hw, f, b): the same rules for the
    person and for the Mannequin a garment was modelled on, so the two match level for level. A neck too short for
    them (a child's: an adult-size head on the body model's least height, 135 cm, puts the shoulders 2 cm under the
    chin, so the trunk never narrows to a neck below it) takes short_neck_hw, the face guide's own neck, if given,
    with its base halfway from the shoulder line to the chin."""
    z, hw = rows[:, 0], rows[:, 1]
    band = (z >= crotch + .12 * scale) & (z <= pit - .08 * scale)
    waist = float(z[band][np.argmin(hw[band])])
    hips = (z >= crotch - .01) & (z <= waist)
    hip = float(z[hips][np.argmax(hw[hips])])
    upper = (z >= pit) & (z <= chin)
    peak = int(np.argmax(np.where(upper, hw, -1.)))
    shoulder = _first(z, hw, z[peak], hw[peak] - SHOULDER_DROP)
    neck_hw = float(np.interp(chin - .02, z, hw))
    neck = _first(z, hw, shoulder, NECK_FLARE * neck_hw) if shoulder is not None else None
    if short_neck_hw is not None and shoulder is not None and shoulder < chin and (neck is None or neck <= shoulder):
        neck_hw, neck = short_neck_hw, (shoulder + chin) / 2
    if shoulder is None or neck is None:
        raise ValueError('the trunk never narrows to a neck between the armpits (z %.3f) and the chin (z %.3f)' % (pit, chin))
    return dict(waist=waist, hip=hip, shoulder=shoulder, neck=neck), neck_hw


class Guide:
    """A person's body as the costumes need it, in the frame of the module docstring (metres). measure() makes one from
    the guides' arrays; record() is what the build writes beside the costume.
      mesh      the body guide: points (N, 3), tris (M, 3), labels (N,) core bones; uv (N, 2) when the build reads it
      surface   the same surface with the vertices its UV seams split welded (shells are fitted over it); weld (N,) maps
                each mesh vertex to its surface vertex
      bones     {core bone: its head in the reference pose}
      trunk     rows (z, hw, f, b) from the floor to the chin, TRUNK_STEP apart: the half-width, front and back of each
                horizontal section of the body without its arms (both legs below the crotch, the neck from the face
                guide), grown so a superellipse of exponent ROUNDEST through them holds the whole section
      levels    {LEVELS name: z}: ankle and knee (the foot and calf bones), crotch, waist (narrowest), hip (widest under
                it), pit (the armpits), shoulder (where a top's straps leave its panels), neck (its base), chin, head
                (the bone), skull (the skull's widest and longest), crown
      strap     (neck side, arm side): the |y| between which a top's straps cross the shoulders
      neck_hw   the neck's half-width under the jaw
      skull     ((cx, cy, cz), front, back, half-width, top): the cranium as an egg, people.HEAD's form
      face      {'eye': (x, |y|, z), 'ear': (x, |y|, z), 'bridge': (x, z)}: eye centres, ear centres, the nose bridge
      limbs     {'arm_l' ...: (joints (3, 3), stations (K,), radii (K,))}: shoulder, elbow, wrist (hip, knee, ankle) and
                the limb's mean radius at stations of arc length from its root joint
      feet      {'l', 'r': (heel x, toe x, sole outline (P, 2))}"""

    def __init__(self, mesh, bones, trunk, levels, strap, neck_hw, skull, face, limbs, feet, source):
        self.mesh, self.bones, self.trunk, self.levels = mesh, bones, trunk, levels
        self.strap, self.neck_hw, self.skull, self.face = strap, neck_hw, skull, face
        self.limbs, self.feet, self.source = limbs, feet, source
        self.scale = levels['crown'] / SOURCE_HEIGHT
        # The guide splits its vertices along UV seams (one UV each): shells are fitted over the surface welded whole,
        # or they would open along every seam. weld maps each guide vertex to its welded one.
        points, tris = mesh['points'], mesh['tris']
        _, first, self.weld = np.unique(np.round(points / WELD).astype(np.int64), axis=0, return_index=True, return_inverse=True)
        self.weld = self.weld.ravel()
        welded = self.weld[tris]
        welded = welded[(welded[:, 0] != welded[:, 1]) & (welded[:, 1] != welded[:, 2]) & (welded[:, 2] != welded[:, 0])]
        self.surface = {'points': points[first], 'tris': welded, 'labels': np.asarray(mesh['labels'])[first]}
        self.normals = _vertex_normals(self.surface['points'], welded)

    def section(self, z, taut=False):
        """(hw, f, b) of the trunk at height z (interpolated, the neck's above the chin); taut: of its outer envelope
        below the armpits (Port.torso)."""
        t = _tauten(self.trunk, self.levels['pit']) if taut else self.trunk
        return tuple(float(np.interp(z, t[:, 0], t[:, i])) for i in (1, 2, 3))

    def along(self, limb, s):
        """The point at arc length s along a limb's joints (beyond the last joint along its last bone) and the
        direction there."""
        joints = self.limbs[limb][0]
        seg = np.linalg.norm(np.diff(joints, axis=0), axis=1)
        if s <= seg[0]:
            d = (joints[1] - joints[0]) / seg[0]
            return joints[0] + d * s, d
        d = (joints[2] - joints[1]) / seg[1]
        return joints[1] + d * (s - seg[0]), d

    def axis(self, limb, s):
        """Points on a limb's joints at arc lengths s (an array, within its length)."""
        joints = self.limbs[limb][0]
        at = np.concatenate([[0.], np.cumsum(np.linalg.norm(np.diff(joints, axis=0), axis=1))])
        return np.stack([np.interp(s, at, joints[:, i]) for i in range(3)], -1)

    def length(self, limb):
        """Arc length from a limb's root joint to its end joint (the wrist, the ankle)."""
        return float(np.linalg.norm(np.diff(self.limbs[limb][0], axis=0), axis=1).sum())

    def radius(self, limb, s):
        stations, radii = self.limbs[limb][1:]
        return float(np.interp(s, stations, radii))

    def scaled(self, s):
        """The same body s times as big about the origin, the floor under it: costume() builds a child's clothes on her
        guide grown to the size the pieces were drawn for, then shrinks them back."""
        mesh = dict(self.mesh, points=np.asarray(self.mesh['points'], np.float64) * s)
        skull = (np.asarray(self.skull[0], np.float64) * s,) + tuple(v * s for v in self.skull[1:])
        return Guide(mesh, {k: np.asarray(v, np.float64) * s for k, v in self.bones.items()}, np.asarray(self.trunk, np.float64) * s,
                     {k: v * s for k, v in self.levels.items()}, tuple(v * s for v in self.strap), self.neck_hw * s, skull,
                     {k: np.asarray(v, np.float64) * s for k, v in self.face.items()},
                     {k: (np.asarray(j) * s, np.asarray(st) * s, np.asarray(r) * s) for k, (j, st, r) in self.limbs.items()},
                     {k: (h * s, t * s, np.asarray(o) * s) for k, (h, t, o) in self.feet.items()}, self.source)

    def record(self):
        """The measurements as JSON-able data (the mesh is the guide FBX's own)."""
        def r(v):
            return np.round(np.asarray(v, np.float64), 4).tolist()
        return {'source': self.source, 'levels': {k: round(v, 4) for k, v in self.levels.items()}, 'strap': r(self.strap),
                'neck_hw': round(self.neck_hw, 4), 'skull': [r(self.skull[0])] + r(self.skull[1:]),
                'face': {k: r(v) for k, v in self.face.items()}, 'trunk': r(self.trunk),
                'limbs': {k: {'joints': r(j), 'stations': r(s), 'radii': r(rr)} for k, (j, s, rr) in self.limbs.items()},
                'feet': {k: {'heel': round(h, 4), 'toe': round(t, 4), 'outline': r(o)} for k, (h, t, o) in self.feet.items()},
                'bones': {k: r(v) for k, v in sorted(self.bones.items())}}


def _chin(points, edges, scale):
    """The chin's height: going up the face guide's midline from the base of its neck, where the face first stands
    CHIN_STEP further forward than the throat below it."""
    z0, z1 = float(points[:, 2].min()), float(points[:, 2].max())
    below = []   # (z, front) of the last few heights the midline crosses
    for z in np.arange(z0 + .005, z1, .005):
        q = _cut(points, edges, np.array([0., 0., z]), np.array([0., 0., 1.]))
        mid = q[np.abs(q[:, 1]) < .02 * scale] if len(q) else q
        if not len(mid):
            continue
        front = float(mid[:, 0].max())
        if len(below) >= 4 and front - min(f for _, f in below[-4:]) > CHIN_STEP * scale:
            return below[-1][0]
        below.append((float(z), front))
    raise ValueError('the face guide has no chin: its middle never steps forward going up')


def _cranium(points, edges, crown, scale):
    """The cranium as people.HEAD's egg: centre and radii where the skull is longest within SKULL_BAND below the crown,
    its top at the crown, grown until it holds the skull above the centre (the ears' and the face's points left out)."""
    zs = np.arange(crown - SKULL_BAND[1] * scale, crown - SKULL_BAND[0] * scale, .004)
    best = None
    for z in zs:
        q = _cut(points, edges, np.array([0., 0., z]), np.array([0., 0., 1.]))
        if len(q) < 8:
            continue
        length = q[:, 0].max() - q[:, 0].min()
        if best is None or length > best[0]:
            best = (length, z, q)
    if best is None:
        raise ValueError('the face guide has no cranium below its crown')
    _, cz, q = best
    cx = float(q[:, 0].max() + q[:, 0].min()) / 2
    fr, bk, hw, up = float(q[:, 0].max()) - cx, cx - float(q[:, 0].min()), float(np.abs(q[:, 1]).max()), crown - cz
    above = points[points[:, 2] >= cz]
    x, y, z = above[:, 0] - cx, np.abs(above[:, 1]), above[:, 2] - cz

    def outside(d):
        a = np.where(x >= 0, fr + d, bk + d)
        return np.any((x / a) ** 2 + (y / (hw + d)) ** 2 + (z / (up + d)) ** 2 > 1 + 1e-9)
    lo, hi = 0.0, .05
    if outside(lo):
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if outside(mid) else (lo, mid)
        fr, bk, hw, up = fr + hi, bk + hi, hw + hi, up + hi
    return (np.array([cx, 0., cz]), fr, bk, hw, up), cz


def _limb_radii(points, tris, labels, names, joints):
    """A limb's mean radius at stations LIMB_STEP apart along its joints, from sections of its own triangles at right
    angles to its bones (the bend's bisector at the middle joint)."""
    keep = _majority(tris, _labelled(labels, names))
    edges = _edges(keep)
    seg = np.linalg.norm(np.diff(joints, axis=0), axis=1)
    dirs = np.diff(joints, axis=0) / seg[:, None]
    stations, radii = [], []
    for s in np.arange(0., seg.sum() + 1e-9, LIMB_STEP):
        i = 0 if s < seg[0] else 1
        o = joints[i] + dirs[i] * (s - (0 if i == 0 else seg[0]))
        n = dirs[i]
        if abs(s - seg[0]) < LIMB_STEP / 2:
            n = dirs[0] + dirs[1]
            n /= np.linalg.norm(n)
        q = _cut(points, edges, o, n)
        if len(q) < 6:
            continue
        r = q - o
        r = np.linalg.norm(r - np.outer(r @ n, n), axis=1)
        r = r[r < 2 * np.median(r)]  # another part of the limb crossing the same plane (the hand, the other bone)
        stations.append(s)
        radii.append(float(r.mean()))
    if len(stations) < 3:
        raise ValueError('the limb %s has too few sections: are its vertices labelled %s?' % (names[0], ', '.join(names)))
    return np.array(stations), np.array(radii)


def measure(body, face, bones, landmarks=None, source=''):
    """A Guide from the guides' arrays: body and face are {'points': (N, 3) metres in the module's frame, 'tris': (M, 3),
    'labels': (N,) core bone names} (body may add 'uv'); bones {core bone: head}; landmarks {face joint: head}, the face
    skeleton's FACIAL_* joints when the guide has them. Raises ValueError when the body is not one a costume can be
    measured from (a missing part, levels out of order)."""
    bp, bt, bl = (np.asarray(body[k]) for k in ('points', 'tris', 'labels'))
    fp, ft = np.asarray(face['points'], np.float64), np.asarray(face['tris'])
    bp = bp.astype(np.float64)
    bones = {k: np.asarray(v, np.float64) for k, v in bones.items()}
    missing = [b for b in CORE if b != 'root' and b not in bones]
    if missing:
        raise ValueError('the body guide has no bones %s' % ', '.join(missing))
    for name, (pts, tris) in (('body', (bp, np.asarray(bt))), ('face', (fp, ft))):
        if _volume(pts, tris) <= 0:
            raise ValueError('the %s guide\'s triangles face inward in this frame (the FBX frame is mirrored: reverse each '
                             'triangle\'s corners)' % name)
    crown = float(fp[:, 2].max())
    scale = crown / SOURCE_HEIGHT
    f_edges = _edges(ft)
    chin = _chin(fp, f_edges, scale)
    # The trunk: the body without its arms and hands, and below the chin the face guide's neck and bib.
    trunk_tris = _majority(bt, ~np.array([str(l).startswith(ARM_PARTS) for l in bl], bool))
    points = np.concatenate([bp, fp])
    edges = np.concatenate([_edges(trunk_tris), f_edges + len(bp)])
    rows = []
    for z in np.arange(.01, chin - .004, TRUNK_STEP):
        q = _cut(points, edges, np.array([0., 0., z]), np.array([0., 0., 1.]))
        if len(q) >= 3:
            rows.append((z,) + _hold(q))
    trunk = np.array(rows)
    # The crotch: the lowest point of the trunk on its midline above the knees.
    mid = (np.abs(bp[:, 1]) < CROTCH_GAP) & (bp[:, 2] > .3 * crown) & ~np.array([str(l).startswith(ARM_PARTS) for l in bl])
    if not mid.any():
        raise ValueError('no body vertex on the midline above the knees: is the body guide whole?')
    crotch = float(bp[mid, 2].min())
    # The armpits: the arm's lowest point within reach of the shoulder joint's side, the same each side.
    pits = []
    for s in SIDES:
        j = bones['upperarm_' + s]
        arm = _labelled(bl, ['upperarm_' + s]) & (np.abs(bp[:, 1]) < abs(j[1]) + ARMPIT_REACH)
        if not arm.any():
            raise ValueError('no upperarm_%s vertices near the shoulder' % s)
        pits.append(float(np.clip(bp[arm, 2].min(), j[2] - .14 * scale, j[2] - .05 * scale)))
    pit = float(np.mean(pits))
    # The face guide's own neck (its vertices weighted most to the neck bones), for a neck too short for the trunk
    # table: as wide as the table finds the necks of the built women (4.6-5.8 cm, 2026-11-09).
    necks = _labelled(np.asarray(face['labels']), ('neck_01', 'neck_02')) if 'labels' in face else np.zeros(0, bool)
    short_neck_hw = float(np.percentile(np.abs(fp[necks, 1]), 95)) if necks.any() else None
    found, neck_hw = _trunk_levels(trunk, crotch, pit, chin, scale, short_neck_hw)
    skull, cz = _cranium(fp, f_edges, crown, scale)
    levels = dict(ankle=float(np.mean([bones['foot_' + s][2] for s in SIDES])),
                  knee=float(np.mean([bones['calf_' + s][2] for s in SIDES])), crotch=crotch, pit=pit, chin=chin,
                  head=float(bones['head'][2]), skull=float(cz), crown=crown, **found)
    order = [(name, levels[name]) for name in LEVELS]
    for (a, za), (b, zb) in zip(order, order[1:]):
        if not za < zb:
            raise ValueError('the guide\'s %s (z %.3f) is not below its %s (z %.3f)' % (a, za, b, zb))
    strap = (neck_hw + STRAP_NECK, float(np.interp(found['shoulder'], trunk[:, 0], trunk[:, 1])) - STRAP_ARM)
    limbs = {}
    for limb, (joint_names, names) in LIMBS.items():
        joints = np.array([bones[n] for n in joint_names])
        limbs[limb] = (joints,) + _limb_radii(bp, bt, bl, names, joints)
    feet = {}
    for s in SIDES:
        foot = bp[_labelled(bl, FOOT[s])]
        if len(foot) < 8:
            raise ValueError('the body guide has no %s foot' % s)
        sole = foot[foot[:, 2] < .025 * scale][:, :2]
        feet[s] = (float(foot[:, 0].min()), float(foot[:, 0].max()), _hull2d(sole if len(sole) >= 3 else foot[:, :2]))
    face_marks = _face_marks(landmarks or {}, skull)
    mesh = {'points': bp, 'tris': np.asarray(bt), 'labels': np.asarray(bl)}
    if body.get('uv') is not None:
        mesh['uv'] = np.asarray(body['uv'], np.float64)
    return Guide(mesh, bones, trunk, levels, strap, neck_hw, skull, face_marks, limbs, feet, source)


# Where on a skull each face joint may be, as fractions of it ((x from the centre, by the front radius or minus the back
# radius), |y| by the half-width, z from the centre by the top): a joint outside its box is not the person's (a face
# skeleton not yet fitted to the face, a renamed joint), and the Mannequins' place stands in for it.
FACE_BOX = {'eye': ((.5, 1.2), (.2, .6), (-.4, .4)), 'ear': ((-.6, .4), (.6, 1.2), (-.8, .2)), 'bridge': ((.7, 1.4), (0., .1), (-.5, .5))}


def _face_marks(landmarks, skull):
    """Eye centres, ear joints and the nose bridge from the face skeleton's joints; where a joint is missing or not where
    a face has it (FACE_BOX), where the Mannequins' were on their skull (people.HEAD), on this skull."""
    (cx, cy, cz), fr, bk, hw, up = skull
    (sx, sy, sz), sf, sb, sw, su = HEAD['Quinn']

    def onto(p):
        a = (p[0] - sx) / (sf if p[0] >= sx else sb)
        return np.array([cx + a * (fr if a >= 0 else bk), (p[1] - sy) / sw * hw, cz + (p[2] - sz) / su * up])

    def fits(name, p):
        if p is None:
            return False
        (x0, x1), (y0, y1), (z0, z1) = FACE_BOX[name]
        x = p[0] - cx
        return x0 <= x / (fr if x >= 0 else bk) <= x1 and y0 <= abs(p[1]) / hw <= y1 and z0 <= (p[2] - cz) / up <= z1

    marks = {}
    for name, pattern in FACE_JOINTS.items():
        found = [np.asarray(landmarks[pattern % side.upper()], np.float64) for side in SIDES if pattern % side.upper() in landmarks]
        p = np.array([np.mean([q[0] for q in found]), np.mean([abs(q[1]) for q in found]), np.mean([q[2] for q in found])]) if found else None
        marks[name] = p if fits(name, p) else onto(np.array(STANDIN_FACE[name]))
    bridge = landmarks.get(BRIDGE_JOINT)
    bridge = np.asarray(bridge, np.float64) if bridge is not None else None
    if not fits('bridge', bridge):
        bridge = onto(np.array([STANDIN_BRIDGE[0], 0., STANDIN_BRIDGE[1]]))
    marks['bridge'] = np.array([bridge[0], bridge[2]])
    return marks


# ---------------------------------------------------------------- from a Mannequin's garment to a person's

def _source(body):
    """A Mannequin as measure() would see it (people.TORSO, PIT, STRAP, HEAD; STANDIN_JOINTS for the knees and ankles):
    (trunk rows, levels, strap, skull), so a garment's heights and widths go to the person's level for level."""
    rows = np.array(TORSO[body], np.float64)
    found, _ = _trunk_levels(rows, rows[0, 0], PIT[body], SOURCE_CHIN, 1.0)
    leg = STANDIN_JOINTS['leg']
    levels = dict(ankle=leg[2][2] * SOURCE_HEIGHT, knee=leg[1][2] * SOURCE_HEIGHT, crotch=float(rows[0, 0]), pit=PIT[body],
                  chin=SOURCE_CHIN, head=SOURCE_HEAD, skull=HEAD[body][0][2], crown=SOURCE_HEIGHT, **found)
    return rows, levels, STRAP[body], HEAD[body]


SOURCES = {body: _source(body) for body in ('Quinn', 'Manny')}
NECK_REACH = .3   # m the trunk table's neck section is carried up past the chin, for collars and straps over it
# A refitted drape stands at least CLEAR off the body (more than people.py's thickest cloth, .009), and a top BODY_GAP
# further out than its ease over the Mannequin: people.TORSO was a smooth estimate, a guide's sections are the body's own
# outermost points, which cloth at the Mannequin's ease would graze.
CLEAR = .01
BODY_GAP = .004


class Port:
    """people.py's garments, modelled over the Mannequin src ('Quinn' or 'Manny'), moved onto a Guide: heights through
    the levels both share (z), drape rows by their ease over the trunk (rows, drape, torso), lateral places over the
    shoulders by the straps (y), and places on the head by the skull (head, hz)."""

    def __init__(self, guide, src):
        self.g, self.src = guide, src
        self.src_rows, self.src_levels, self.src_strap, self.src_skull = SOURCES[src]
        self.zs = np.array([0.] + [self.src_levels[n] for n in LEVELS])
        self.zd = np.array([0.] + [guide.levels[n] for n in LEVELS])
        # How much bigger the person's head is: a hat's brim and crown, a ring's span grow with it.
        self.kh = float(np.mean(guide.skull[1:]) / np.mean(self.src_skull[1:]))

    def z(self, z):
        """A height on the Mannequin to the same place on the person (straight between the levels, the last level's
        slope above the crown)."""
        z = np.asarray(z, np.float64)
        out = np.interp(z, self.zs, self.zd)
        slope = (self.zd[-1] - self.zd[-2]) / (self.zs[-1] - self.zs[-2])
        out = np.where(z > self.zs[-1], self.zd[-1] + (z - self.zs[-1]) * slope, out)
        return float(out) if out.ndim == 0 else out

    def _src_section(self, z, taut=False):
        t = _tauten(self.src_rows, self.src_levels['pit']) if taut else self.src_rows
        return tuple(float(np.interp(z, t[:, 0], t[:, i])) for i in (1, 2, 3))

    def rows(self, rows, taut=False):
        """Drape rows (z, hw, f, b) of a Mannequin garment as the person's: each keeps its ease over the body at its
        level (below the hips, over the hips' section, where a skirt hangs free), and stays CLEAR of the person's
        section there, which below the crotch is both legs. taut: over the trunk's envelope (a coat's skirt, whose body
        is Port.torso(taut=True))."""
        out = []
        hip_s, hip_d = self.src_levels['hip'], self.g.levels['hip']
        # Every TRUNK_STEP, not only at the garment's own rows: a person's hips or belly can bulge between two of them.
        given = np.array(sorted(rows), np.float64)
        zs = np.union1d(given[:, 0], np.arange(given[0, 0], given[-1, 0], TRUNK_STEP))
        dense = np.column_stack([zs] + [np.interp(zs, given[:, 0], given[:, i]) for i in (1, 2, 3)])
        for z, hw, f, b in dense:
            zd = self.z(z)
            s = self._src_section(max(z, hip_s), taut)
            d = self.g.section(max(zd, hip_d), taut)
            here = self.g.section(zd)
            out.append((zd, max(d[0] + hw - s[0], here[0] + CLEAR), max(d[1] + f - s[1], here[1] + CLEAR),
                        min(d[2] + b - s[2], here[2] - CLEAR)))
        return tuple(out)

    def _heights(self, kw):
        """A Drape's own heights (people.Drape's defaults are the Mannequins') mapped to the person."""
        kw = dict(kw)
        for key, default in (('fold_top', .9), ('fold_low', 0.), ('gather_top', 1.06), ('wrinkle_top', 1.38)):
            kw[key] = self.z(kw.get(key, default))
        if kw.get('tuck'):
            lo, hi, a = kw['tuck']
            kw['tuck'] = (self.z(lo), self.z(hi), a)
        if kw.get('ripples'):
            kw['ripples'] = tuple((self.z(lo), self.z(hi), count, a) for lo, hi, count, a in kw['ripples'])
        if kw.get('quilt'):
            pitch, a, lo, hi = kw['quilt']
            kw['quilt'] = (pitch, a, self.z(lo), self.z(hi))
        return kw

    def drape(self, rows, taut=False, **kw):
        """people.Drape(rows, ...) on the person (taut: see rows). Never capped: the arms are out of the way in the
        reference pose, and skinned cloth moves with them."""
        return Drape(self.rows(rows, taut), capped=False, **self._heights(kw))

    def torso(self, ease, taut=False, **kw):
        """people._torso_drape / Drape(TORSO[body], n=2.4, ...): the person's own trunk from the crotch up, the neck
        carried NECK_REACH above the chin, with the garment's ease (a number, or (z, ease) rows at Mannequin heights).
        taut: an unbelted coat or a padded gambeson hangs from the bust, the shoulder blades and the hips across the
        waist and the small of the back instead of following them in (below the armpits, the sections' outer envelope);
        belted robes follow the waist, so their sash and cord lie over them."""
        t = _tauten(self.g.trunk, self.g.levels['pit']) if taut else self.g.trunk
        t = t[t[:, 0] >= self.g.levels['crotch'] - TRUNK_STEP]
        rows = [tuple(r) for r in t]
        rows.append((t[-1, 0] + NECK_REACH,) + tuple(t[-1, 1:]))
        ease = tuple((self.z(z), e + BODY_GAP) for z, e in ease) if np.ndim(ease) else ease + BODY_GAP
        kw.setdefault('n', 2.4)
        return Drape(rows, ease=ease, capped=False, **self._heights(kw))

    def y(self, y):
        """A lateral distance over the shoulders (where a strap or a stole crosses them) on the person: the same place
        between the straps' neck-side and arm-side edges."""
        (a, b), (c, d) = self.src_strap, self.g.strap
        return c + (y - a) * (d - c) / (b - a)

    def skull(self, grow=0.):
        """The person's skull (people.HEAD's form) grown by grow all round: hair under a hat."""
        c, fr, bk, hw, up = self.g.skull
        return (c, fr + grow, bk + grow, hw + grow, up + grow)

    def hz(self, z, grow=0.):
        """A height on the Mannequin's head: above its skull's centre as a fraction of the skull's top, below it through
        the levels (the chin, the neck)."""
        (_, _, sz), _, _, _, su = self.src_skull
        (_, _, cz), _, _, _, up = self.skull(grow)
        z = np.asarray(z, np.float64)
        out = np.where(z >= sz, cz + (z - sz) / su * up, self.z(np.minimum(z, sz)))
        return float(out) if out.ndim == 0 else out

    def head(self, p, grow=0.):
        """A point on or near the Mannequin's head to the person's: across and along the skull as fractions of it
        (front and back apart), up by hz."""
        p = np.asarray(p, np.float64)
        (sx, sy, sz), sf, sb, sw, su = self.src_skull
        (cx, cy, cz), fr, bk, hw, up = self.skull(grow)
        a = (p[..., 0] - sx) / np.where(p[..., 0] >= sx, sf, sb)
        x = cx + a * np.where(a >= 0, fr, bk)
        y = cy + (p[..., 1] - sy) / sw * hw
        return np.stack([x, y, self.hz(p[..., 2], grow)], -1)


# ---------------------------------------------------------------- stand-in guides (offline)

def _tris(faces):
    """Polygons as a fan of triangles each."""
    return np.array([(f[0], f[i], f[i + 1]) for f in faces for i in range(1, len(f) - 1)], np.int64)


def _ring_mesh(rings, n_side):
    """Quads between consecutive rings of n_side points (a lofted tube, open at both ends), as triangles."""
    faces = []
    for i in range(len(rings) - 1):
        for j in range(n_side):
            a, b = i * n_side + j, i * n_side + (j + 1) % n_side
            faces += [(a, b, b + n_side), (a, b + n_side, a + n_side)]
    return np.concatenate(rings), np.array(faces, np.int64)


def _superellipse(hw, f, b, n, sides=32):
    th = np.linspace(-math.pi, math.pi, sides, endpoint=False)
    c, s, e = np.cos(th), np.sin(th), 2.0 / n
    x = np.where(c >= 0, f, -b) * np.sign(c) * np.abs(c) ** e
    y = hw * np.sign(s) * np.abs(s) ** e
    return np.stack([x, y], -1)


def standin(key):
    """Stand-in guide arrays for MH[key] (offline tests): the Mannequin their CAST row wore (people.TORSO, JAW, HEAD,
    PIT) scaled to their MH height, with MetaHuman limbs (STANDIN_*). Returns (body, face, bones, landmarks) as
    measure() takes them. Its limbs are tubes pushed into the trunk, not grown out of it as a body's are, so a shell over
    its shoulders fits less well than over a guide; --physis is the test on a real one."""
    entry = MH[key]
    src = CAST_MANNEQUIN[entry['rows'][0]]['body']
    rows, levels, _, head = SOURCES[src]
    crown = entry['body']['height_cm'] / 100.
    k = crown / SOURCE_HEIGHT
    parts, labels = [], []

    def add(points, tris, label):
        parts.append((np.asarray(points, np.float64), np.asarray(tris, np.int64)))
        labels.append(np.asarray(label if np.ndim(label) else [label] * len(points)))

    def joined(selection):
        pts, tris, labs, base = [], [], [], 0
        for (p, t), l in [(parts[i], labels[i]) for i in selection]:
            pts.append(p)
            tris.append(t + base)
            labs.append(l)
            base += len(p)
        return {'points': np.concatenate(pts), 'tris': np.concatenate(tris), 'labels': np.concatenate(labs)}

    def trunk_rings(z_lo, z_hi, label_of, table=rows, n=ROUNDEST):
        zs = np.arange(z_lo, z_hi + 1e-9, .02)
        rings = []
        for z in zs:
            hw, f, b = (float(np.interp(z, table[:, 0], table[:, i])) for i in (1, 2, 3))
            xy = _superellipse(hw, f, b, n)
            rings.append(np.column_stack([xy, np.full(len(xy), z)]))
        pts, tris = _ring_mesh(rings, 32)
        add(pts * k, tris, [label_of(p) for p in pts])

    w, pit, sh = levels['waist'], levels['pit'], levels['shoulder']

    def trunk_label(p):
        if p[2] > pit - .02 and abs(p[1]) > .07:
            return 'clavicle_%s' % ('l' if p[1] < 0 else 'r')
        return 'pelvis' if p[2] < w else 'spine_02' if p[2] < (w + pit) / 2 else 'spine_04' if p[2] < pit else 'spine_05'

    trunk_rings(rows[0, 0], levels['neck'] - .02, trunk_label)
    body_parts = [0]
    bones = {'root': np.zeros(3)}
    # Limbs: tubes along the joints with the radii of STANDIN_RADII, a hand and a foot.
    for limb, (joint_names, _) in LIMBS.items():
        kind, side = limb.split('_')
        sign = SIDE_SIGN[side]
        joints = np.array([(x * crown, sign * y * crown, z * crown) for x, y, z in STANDIN_JOINTS[kind]])
        for name, j in zip(joint_names, joints):
            bones[name] = j
        seg = np.linalg.norm(np.diff(joints, axis=0), axis=1)
        s = np.arange(0., seg.sum() + 1e-9, .02)
        pts = np.array([joints[0] + (joints[1] - joints[0]) * min(t / seg[0], 1.) if t <= seg[0] else
                        joints[1] + (joints[2] - joints[1]) * (t - seg[0]) / seg[1] for t in s])
        frac, rad = zip(*STANDIN_RADII[kind])
        radii = np.interp(s / seg.sum(), frac, rad) * crown
        tmp = Part('tmp', ('CN_Cloth',))
        _tube(tmp, pts, radii, (1., 1., 1., 1.), 'CN_Cloth', 16)
        tube_pts = np.asarray(tmp.v)
        ring_s = np.repeat(s, 16)
        lab = np.where(np.concatenate([ring_s, np.full(len(tube_pts) - len(ring_s), s[-1])]) <= seg[0], joint_names[0], joint_names[1])
        add(tube_pts, _tris(tmp.f), lab)
        body_parts.append(len(parts) - 1)
        d = (joints[2] - joints[1]) / seg[1]
        if kind == 'arm':
            length, half, thick = (v * crown for v in STANDIN_HAND)
            tmp = Part('tmp', ('CN_Cloth',))
            _box(tmp, joints[2] + d * length / 2, (length / 2, half, thick), (1., 1., 1., 1.), 'CN_Cloth', .004,
                 R=_basis(d, (0, 0, 1)))
            add(np.asarray(tmp.v), _tris(tmp.f), 'hand_' + side)
        else:
            heel, toe, mid, half, instep, top = (v * crown for v in STANDIN_FOOT)
            xs = np.linspace(heel, toe, 12)
            tops = np.interp(xs, [heel, heel + .35 * (toe - heel), toe], [instep, instep, top])
            a = np.linspace(-math.pi / 2, 1.5 * math.pi, FOOT_SIDES, endpoint=False)   # from the sole round over the instep
            rings = [np.column_stack([np.full(FOOT_SIDES, x), sign * mid + half * np.cos(a), np.maximum(.004, t * (.5 + .5 * np.sin(a)))])
                     for x, t in zip(xs, tops)]
            pts, tris = _ring_mesh(rings, FOOT_SIDES)
            caps = _tris([list(range(FOOT_SIDES))[::-1], list(range(len(pts) - FOOT_SIDES, len(pts)))])
            ball_x = .0761 * crown
            add(pts, np.concatenate([tris, caps]), np.where(pts[:, 0] < ball_x, 'foot_' + side, 'ball_' + side))
            bones['ball_' + side] = np.array([ball_x, sign * .0894 * crown, .0058 * crown])
        body_parts.append(len(parts) - 1)
    body = joined(body_parts)
    # The face guide: the neck and bib from below the shoulders to the chin, the jaw, the skull.
    first = len(parts)
    neck = levels['neck']
    trunk_rings(pit + .03, SOURCE_CHIN + .01, lambda p: 'spine_04' if p[2] < neck else 'neck_01')  # into the jaw, as a face is
    jaw = np.array([r for r in JAW if r[0] >= SOURCE_CHIN], np.float64)
    trunk_rings(jaw[0, 0], jaw[-1, 0], lambda p: 'head', table=jaw, n=2.0)
    (cx, cy, cz), fr, bk, hw, up = head
    psi = np.linspace(-math.pi / 2, math.pi / 2, 14)[1:-1]
    phi = np.linspace(-math.pi, math.pi, 32, endpoint=False)
    rings = [np.stack([cx + np.where(np.cos(phi) >= 0, fr, bk) * np.cos(a) * np.cos(phi), cy + hw * np.cos(a) * np.sin(phi),
                       np.full(32, cz + up * np.sin(a))], -1) for a in psi]
    pts, tris = _ring_mesh(rings, 32)
    pts = np.concatenate([pts, [(cx, cy, cz - up), (cx, cy, cz + up)]])
    poles = [(len(pts) - 2, (j + 1) % 32, j) for j in range(32)]
    poles += [(len(pts) - 1, len(pts) - 34 + j, len(pts) - 34 + (j + 1) % 32) for j in range(32)]
    add(pts * k, np.concatenate([tris, np.array(poles)]), 'head')
    face = joined(range(first, len(parts)))
    # The trunk's bones (their places matter only to the build's weights; measure() needs them to exist).
    spine = np.linspace(levels['crotch'] + .12, levels['neck'] - .1, 6)
    for name, z in zip(('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05'), spine):
        bones[name] = np.array([0., 0., z * k])
    bones.update(neck_01=np.array([0., 0., neck * k]), neck_02=np.array([0., 0., (neck + SOURCE_CHIN) / 2 * k]),
                 head=np.array([0., 0., SOURCE_HEAD * k]))
    for side in SIDES:
        bones['clavicle_' + side] = np.array([0., SIDE_SIGN[side] * .02 * k, (pit + .06) * k])
    landmarks = {FACE_JOINTS[name] % side.upper(): np.array([x, SIDE_SIGN[side] * y, z]) * k
                 for name, (x, y, z) in STANDIN_FACE.items() for side in SIDES}
    landmarks[BRIDGE_JOINT] = np.array([STANDIN_BRIDGE[0], 0., STANDIN_BRIDGE[1]]) * k
    return body, face, bones, landmarks


def standin_guide(key):
    """measure() of standin(key): the Guide an offline costume is built on."""
    return measure(*standin(key), source='stand-in: %s at %.2f m' % (CAST_MANNEQUIN[MH[key]['rows'][0]]['body'],
                                                                         MH[key]['body']['height_cm'] / 100))


# ---------------------------------------------------------------- people.py's tops on a person

def strap_angles(g, dr):
    """people._angles on a guide: the front angles of the straps' neck-side and arm-side edges where they leave the
    panels."""
    hw_sh = float(dr.axes(g.levels['shoulder'])[0])
    return tuple(float(np.arcsin(min(1.0, y / hw_sh) ** (dr.n / 2))) for y in g.strap)


def bodice(part, g, dr, base, slot, *, thick=.006, z_bot=1.0, neck_front=1.40, neck_back=1.47, neck_shape=2.2, fronts=None,
           k=1.0, nv=16, nn=13, ms=5, nt=8, seed=0):
    """people._top on a guide (heights are the person's): front and back panels joined at the side seams below the
    armpits, armholes above them round the arms' roots, straps over the shoulders out to their edges, a neckline.
    fronts=None is one front panel; else (right_edge(z), left_edge(z), lift(theta, z, side)) from front_edges() splits
    it for a coat or a wrap robe. Returns the same borders as people._top, for trims, collars and sleeves."""
    n = dr.n
    e = 2.0 / n
    z_pit, z_sh = g.levels['pit'], g.levels['shoulder']
    th_neck, th_arm = strap_angles(g, dr)
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
        top = (np.abs(top_th[:-1]) < th_neck + 1e-6) & (np.abs(top_th[1:]) < th_neck + 1e-6)
        lo = (Z[1:, 0] > z_pit + 1e-4) if border_lo == 'arm' else True
        hi = (Z[1:, -1] > z_pit + 1e-4) if border_hi == 'arm' else True
        return (True, top if top.any() else False, lo, hi)

    kk = lambda TH, Z: k * _cloth_k(dr, TH, Z, 0., seed, 3.0)
    out = _away((0, 0, (g.levels['waist'] + z_sh) / 2))  # people._top's 1.25 on the Mannequins: midway up the torso
    mid = np.linspace(-th_neck, th_neck, nn)
    back_th = np.concatenate([-sb[::-1], mid[1:-1], sb])
    back_z = np.where(np.abs(back_th) < th_neck - 1e-9, neck(back_th, neck_back), z_sh)
    TB, ZB = grid(lambda z: -span(z), span, back_th, back_z)
    TB = math.pi - TB
    PB, QB = _sheet(part, dr.at(TB, ZB), thick, base, slot, out, k=kk(TB, ZB), rims=masks(TB, ZB, back_th, 'arm', 'arm'))
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
    # Straps: each strap column keeps its lateral place over the top of the shoulder.
    zz = np.linspace(z_sh, g.levels['chin'], 400)
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
                th_arm=th_arm, z_sh=z_sh, z_pit=z_pit, span=span, over=over, ms=ms, z_bot=z_bot, neck_front=neck_front)


def neck_opening(g, dr, neck_front, neck_back, shape):
    """people._opening on a guide: the height of a top's neck opening at any theta (the front neckline, the straps'
    neck-side edges over the shoulders, the back neckline), so a collar or a binding can sit on it."""
    z_sh = g.levels['shoulder']
    th_neck = strap_angles(g, dr)[0]
    zz = np.linspace(z_sh, g.levels['chin'], 240)
    hh = np.minimum.accumulate(dr.axes(zz)[0])
    th_e = np.arcsin(np.clip(g.strap[0] / hh, 0, 1) ** (dr.n / 2))
    stop = int(np.argmax(th_e >= math.pi / 2 - 1e-6)) if (th_e >= math.pi / 2 - 1e-6).any() else len(th_e) - 1
    th_e, zz = th_e[:stop + 1], zz[:stop + 1]

    def z_of(theta):
        a = np.abs(np.angle(np.exp(1j * np.asarray(theta, np.float64))))
        front = neck_front + (z_sh - neck_front) * np.clip(a / th_neck, 0, 1) ** shape
        back = neck_back + (z_sh - neck_back) * np.clip((math.pi - a) / th_neck, 0, 1) ** shape
        side = np.interp(np.minimum(a, math.pi - a), th_e, zz)
        return np.where(a < th_neck, front, np.where(math.pi - a < th_neck, back, side))
    return z_of


def front_edges(g, dr, z_break, overlap, lap, thick, curve=1.0):
    """people._fronts on a guide: a coat's or a wrap robe's front edges, closed from the waist to z_break with the panels
    overlapping, then opening in a V to the neck at the shoulders; lap +1 lays the left panel over the right."""
    th_neck = strap_angles(g, dr)[0]
    z_sh = g.levels['shoulder']

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


def collar_seam(g, dr, a_pts, z_pts, neck_back, neck_shape=2.2):
    """people._seam_line on a guide: a coat's collar's lower edge (z_pts at |theta| a_pts), kept under the neck opening
    the top cut (pass the opening's back dips to _collar as knots)."""
    z_open = neck_opening(g, dr, g.levels['shoulder'], neck_back, neck_shape)
    return lambda a: np.minimum(np.interp(a, a_pts, z_pts), z_open(a) - .006)


# ---------------------------------------------------------------- ported garments: below the waist
# Each is people.py's builder of the same name (its docstring says what it is) with the Mannequin's heights and sections
# taken through a Port m; it returns its Part and its form: what kind of garment it is and where it starts and ends,
# which says how it is weighted and what of the body it hides.

def skirt_satchel(m):
    """Petra Lune: a long red A-line skirt and the black canvas satchel she carries the Ledger in."""
    p = Part('skirt', ('CN_Cloth', 'CN_Gold'))
    dr = m.drape(((1.085, .142, .104, -.098), (1.04, .152, .104, -.102), (.98, .176, .106, -.122), (.92, .192, .110, -.138),
                  (.86, .198, .118, -.146), (.78, .201, .130, -.152), (.70, .206, .146, -.160), (.55, .232, .176, -.184),
                  (.35, .264, .214, -.216), (.18, .288, .240, -.240), (.08, .298, .250, -.248)),
                 folds=11, amp=.024, fold_top=.88, fold_low=.08, wrinkle=.0012, seed=31)
    _skirt(p, dr, RED, 'CN_Cloth', m.z(1.075), m.z(.085), seed=31)
    _band(p, dr, m.z(1.035), m.z(1.088), .0035, .006, RED, 'CN_Cloth', k=.92)
    for z in m.z((1.072, 1.051)):
        _button(p, dr.at(-math.pi / 2, z, extra=.0098, fold=0.), dr.normal(-math.pi / 2, z, .0098, 0.), .0055, GOLD, 'CN_Gold', k=1.0, cap=None)
    _satchel(p, dr, -2.45, m.z(.985), CHARCOAL, 'CN_Cloth')
    for th0, th1 in ((-2.18, -2.21), (-2.68, -2.66)):
        n = 7
        _strip(p, dr, np.linspace(th0, th1, n), m.z(np.linspace(1.13, .992, n)), .03, .0095, .004, CHARCOAL, 'CN_Cloth', fold=0.)
    return p, dict(kind='skirt', top=m.z(1.088), hem=m.z(.085))


def _apron_skirt(m, name, apron, apron_hem, skirt_hem, seed, pocket='patch'):
    """A gathered black skirt under a front apron tied at the back (Orsolya's white, Rhea's gold)."""
    p = Part(name, ('CN_Cloth', 'CN_Gold'))
    dr = m.drape(((1.085, .142, .104, -.098), (1.04, .155, .106, -.104), (.98, .178, .110, -.126), (.92, .194, .116, -.142),
                  (.86, .199, .126, -.150), (.78, .203, .142, -.160), (.72, .207, .156, -.170), (.55, .240, .190, -.198),
                  (.35, .278, .232, -.236), (.18, .305, .262, -.262), (.08, .316, .272, -.272)),
                 folds=13, amp=.026, fold_top=.9, fold_low=.08, gathers=46, gather_amp=.0032, gather_top=1.075,
                 wrinkle=.001, seed=seed, spare=.014)
    _skirt(p, dr, CHARCOAL, 'CN_Cloth', m.z(1.075), m.z(skirt_hem), nu=60, nv=18, seed=seed)
    _band(p, dr, m.z(1.035), m.z(1.088), .0075, .006, CHARCOAL, 'CN_Cloth', k=.85)
    # The apron hangs flatter than the skirt, standing off its fold ridges.
    nv, nu = 13, 20
    Z = m.z(np.linspace(1.07, apron_hem, nv))[:, None] + np.zeros((1, nu))
    half = np.interp(Z, m.z([apron_hem, 1.07]), [.92, 1.15])
    TH = half * np.linspace(-1, 1, nu)[None, :]
    X = .004 + .4 * dr.depth(Z) + .0025 + dr.gather(Z) + .0015 * np.sin(TH * 7 + seed)
    P = dr.at(TH, Z, extra=X, fold=.6)
    _sheet(p, P, .004, apron, 'CN_Cloth', _axis(), k=_cloth_k(dr, TH, Z, m.z(apron_hem), seed + 1, 3.0))
    _band(p, dr, m.z(1.04), m.z(1.072), .012, .004, apron, 'CN_Cloth', k=.95)
    _bow(p, dr, math.pi, m.z(1.056), .016, apron, 'CN_Cloth', seed=seed)
    if pocket == 'patch':
        z0, z1 = m.z(apron_hem + .36), m.z(apron_hem + .5)
        ex = float(.004 + .4 * dr.depth(z1) + .0025) + .0045
        _patch(p, dr, .2, .62, z0, z1, ex, .003, apron, 'CN_Cloth', 7, 5, k=.97, bulge=.004, fold=.6)
        # A trowel's black handle and gold ferrule stand out of the pocket.
        c = dr.at(.45, z1 - .02, extra=ex + .012, fold=.6)
        _limb(p, [c - (0, 0, .03), c + (.004, .01, .085)], [.009, .010], CHARCOAL, 'CN_Cloth', 8, .9)
        _limb(p, [c - (0, 0, .045), c - (0, 0, .025)], [.0105, .0105], GOLD, 'CN_Gold', 8, 1.0, None)
    else:
        z0, z1 = m.z(apron_hem + .1), m.z(apron_hem + .26)
        ex = float(.004 + .4 * dr.depth(z1) + .0025) + .0045
        _patch(p, dr, -.5, .5, z0, z1, ex, .003, apron, 'CN_Cloth', 9, 5, k=.95, bulge=.006, fold=.6)
        for s in (-1, 1):
            _strip(p, dr, np.full(4, s * .5), np.linspace(z1, z0, 4), .012, ex + .003, .002, apron, 'CN_Cloth', .85, fold=.6)
            q = dr.at(s * .5, z1 - .01, extra=ex + .0045, fold=.6)
            _button(p, q, dr.normal(s * .5, z1 - .01, ex + .0045, .6), .0042, GOLD, 'CN_Gold', h=.0022, sides=8, cap=None)
    return p, dict(kind='skirt', top=m.z(1.088), hem=m.z(skirt_hem))


def apron_skirt_white(m):
    """Orsolya Fenn: a long black skirt under a white gardening apron with a trowel in its pocket."""
    return _apron_skirt(m, 'skirt', WHITE, .24, .085, 41)


def apron_skirt_gold(m):
    """Rhea Sato: a mid-calf black skirt under a knee-length gold work apron with a wide front pocket."""
    return _apron_skirt(m, 'skirt', GOLD_DEEP, .46, .3, 47, pocket='kangaroo')


def skirt_gold(m):
    """Sefa Moreno: a tiered gold skirt, each tier gathered under the one above, a red sash and a purse."""
    p = Part('skirt', ('CN_Cloth', 'CN_Gold'))
    tiers = (
        (((1.085, .142, .104, -.098), (1.0, .172, .108, -.122), (.92, .195, .118, -.142), (.85, .200, .130, -.152), (.69, .205, .152, -.166)),
         1.075, .70, 40, .003, 15, .008),
        (((.73, .199, .146, -.160), (.60, .228, .172, -.182), (.40, .262, .212, -.214)), .725, .41, 54, .006, 17, .010),
        (((.43, .256, .205, -.208), (.25, .292, .246, -.244), (.085, .318, .272, -.266)), .425, .085, 66, .008, 19, .012),
    )
    first = None
    for i, (rows, top, hem, gathers, gamp, folds, amp) in enumerate(tiers):
        dr = m.drape(rows, folds=folds, amp=amp, fold_top=top - .02, fold_low=hem, gathers=gathers, gather_amp=gamp,
                     gather_top=top, wrinkle=.001, seed=60 + i, spare=.012 if i == 0 else .003)
        _skirt(p, dr, GOLD_DEEP, 'CN_Cloth', m.z(top), m.z(hem), nu=52, nv=(10, 8, 9)[i], seed=60 + i, k=(1.0, .96, .92)[i])
        first = first or dr
    _band(p, first, m.z(1.0), m.z(1.092), .0068, .005, RED, 'CN_Cloth', k=.95, rows=4)
    _coil(p, first.at(-.85, m.z(1.046), extra=.016, fold=0.), first.normal(-.85, m.z(1.046), 0., 0.), .016, RED, 'CN_Cloth', 1.6, .009)
    for s in (0, 1):
        n = 8
        _strip(p, first, -.85 + (s - .5) * .09 + np.linspace(0, .05 * (s - .5), n), m.z(np.linspace(1.035, .76 + .04 * s, n)), .045,
               .013, .0035, RED, 'CN_Cloth', .9 - .05 * s, fold=.5)
    # A small coin purse on a cord at the right hip, in front of the hand.
    c = first.at(.62, m.z(.935), extra=.03, fold=0.)
    nrm = first.normal(.62, m.z(.935), 0., 0.)
    _shell(p, c, (.018, .034, .036, .018, .03), CHARCOAL, 'CN_Cloth', .9, 12, 7, R=_basis(nrm))
    _limb(p, [c + (0, 0, .03), first.at(.6, m.z(1.0), extra=.012, fold=0.)], .0025, GOLD, 'CN_Gold', 5, 1.0, None)
    _torus(p, c + (0, 0, .026), .012, .0025, _tone(GOLD, 1.0, None), 'CN_Gold', 12, 5, axis='z')
    return p, dict(kind='skirt', top=m.z(1.092), hem=m.z(.085))


def tunic_skirt(m):
    """Tamsin: the knee-length lower half of her light-blue tunic and a white belt with a gold buckle. A child's skirt:
    it falls nearly straight from the hips with shallow folds (the Mannequin's A-line flare, .238 wide at the hem, hung
    off her like a grown-up's dress, author 2026-11-10)."""
    p = Part('tunic_skirt', ('CN_Cloth', 'CN_Gold'))
    dr = m.drape(((1.085, .150, .112, -.106), (1.03, .166, .113, -.114), (.97, .186, .114, -.132), (.91, .198, .118, -.146),
                  (.84, .201, .126, -.152), (.74, .203, .136, -.157), (.62, .208, .146, -.163), (.50, .214, .155, -.170)),
                 folds=9, amp=.011, fold_top=.86, fold_low=.5, wrinkle=.001, seed=71)
    _skirt(p, dr, BLUE, 'CN_Cloth', m.z(1.075), m.z(.5), nu=56, nv=16, seed=71)
    _band(p, dr, m.z(1.02), m.z(1.08), .0062, .005, WHITE_PURE, 'CN_Cloth', k=.95)
    c = dr.at(0., m.z(1.05), extra=.0115, fold=0.)
    nrm = dr.normal(0., m.z(1.05), .0115, 0.)
    R = _basis(nrm)
    _box(p, c + nrm * .002, (.003, .02, .016), GOLD, 'CN_Gold', .003, 1.0, R, cap=None)
    _box(p, c + nrm * .0045, (.0015, .011, .008), WHITE_PURE, 'CN_Cloth', .001, .9, R)
    return p, dict(kind='skirt', top=m.z(1.08), hem=m.z(.5))


def robe_skirt(m):
    """Old Wen: an ankle-length white robe below a wide black sash knotted at the front."""
    p = Part('robe_skirt', ('CN_Cloth',))
    dr = m.drape(((1.085, .161, .123, -.117), (1.04, .171, .124, -.121), (.98, .182, .126, -.132), (.92, .196, .128, -.146),
                  (.86, .201, .134, -.154), (.78, .204, .144, -.160), (.72, .208, .155, -.168), (.55, .240, .188, -.196),
                  (.35, .276, .228, -.230), (.18, .300, .256, -.254), (.085, .310, .266, -.262)),
                 folds=12, amp=.026, fold_top=.88, fold_low=.085, wrinkle=.0012, seed=81, spare=.009)
    _skirt(p, dr, IVORY, 'CN_Cloth', m.z(1.08), m.z(.085), seed=81)
    _band(p, dr, m.z(.995), m.z(1.09), .006, .006, CHARCOAL, 'CN_Cloth', k=.9, rows=4)
    knot = dr.at(-.32, m.z(1.04), extra=.02, fold=0.)
    _shell(p, knot, (.022, .03, .026), CHARCOAL, 'CN_Cloth', .85, 12, 7, R=_basis(dr.normal(-.32, m.z(1.04), 0., 0.)))
    for s, length in ((-1, .3), (1, .24)):
        n = 9
        _strip(p, dr, -.32 + s * .035 + np.linspace(0, s * .06, n), m.z(np.linspace(1.02, 1.02 - length, n)), np.linspace(.05, .06, n),
               .02, .004, CHARCOAL, 'CN_Cloth', .9, fold=.5)
    return p, dict(kind='skirt', top=m.z(1.09), hem=m.z(.085))


def robe_skirt_tall(m):
    """The Listener: a floor-length white robe with a gold band at the hem and a gold cord belt."""
    p = Part('robe_skirt', ('CN_Cloth', 'CN_Gold'))
    dr = m.drape(((1.085, .168, .136, -.123), (1.04, .172, .135, -.126), (.98, .182, .136, -.138), (.92, .189, .136, -.150),
                  (.86, .194, .140, -.155), (.78, .199, .150, -.162), (.72, .204, .160, -.170), (.55, .238, .192, -.198),
                  (.35, .272, .230, -.230), (.18, .296, .256, -.252), (.035, .310, .268, -.262)),
                 folds=12, amp=.03, fold_top=.86, fold_low=.035, wrinkle=.0012, seed=91, spare=.008)
    _skirt(p, dr, WHITE_PURE, 'CN_Cloth', m.z(1.08), m.z(.035), nv=21, seed=91, k=.96)
    th = np.linspace(-math.pi, math.pi, 64, endpoint=False)
    for z0, z1 in ((.05, .085), (.1, .108)):
        Z = np.array([[m.z(z1)], [m.z(z0)]]) + 0 * th[None, :]
        P = dr.at(th[None, :] + 0 * Z, Z, extra=.0028)
        _sheet(p, P, .002, GOLD, 'CN_Gold', _axis(), k=1.0, closed=True, cap=None)
    # A cord belt: two turns of gold rope, knotted at the front, tassels hanging.
    for i, z in enumerate(m.z((1.05, 1.032))):
        ring = dr.at(th, z + .004 * np.sin(th * 2 + i), extra=.0075, fold=0.)
        _limb(p, np.concatenate([ring, ring[:1]]), .0055, GOLD, 'CN_Gold', 6, 1.0 - .05 * i, None)
    knot = dr.at(.18, m.z(1.04), extra=.014, fold=0.)
    _shell(p, knot, (.012, .015, .014), GOLD, 'CN_Gold', .95, 10, 6, cap=None)
    for s in (-1, 1):
        end = dr.at(.18 + s * .05, m.z(.74 + .03 * s), extra=.03, fold=.4)
        _limb(p, [knot, (knot + end) / 2 + (0, 0, -.02), end], .0045, GOLD, 'CN_Gold', 6, .95, None)
        _shell(p, end - (0, 0, .03), (.009, .009, .032, .009, .02), GOLD_DEEP, 'CN_Cloth', .9, 8, 6)
    return p, dict(kind='skirt', top=m.z(1.085), hem=m.z(.035))


def coat_skirt_black(m):
    """Kairos: the skirt of a long black wool coat, lapping left over right, gold buttons, vent, flaps."""
    p = Part('coat_skirt', ('CN_Cloth', 'CN_Gold'))
    dr = m.drape(((1.075, .156, .120, -.108), (1.0, .168, .118, -.114), (.94, .182, .116, -.130), (.88, .188, .114, -.136),
                  (.80, .196, .120, -.142), (.72, .202, .132, -.150), (.60, .224, .158, -.170), (.45, .250, .188, -.194),
                  (.32, .268, .208, -.212)),
                 folds=7, amp=.022, fold_top=.84, fold_low=.32, wrinkle=.0012, seed=101, spare=.006, taut=True)
    span = _coat_span(m.z([.32, .84, .92, 1.08]), [-.34, -.05, .30, .30])
    _skirt(p, dr, CHARCOAL, 'CN_Cloth', m.z(1.075), m.z(.32), nu=64, nv=20, thick=.009, span=span, lap=1, seed=101, k=.95)
    for z in m.z((.958, .895)):
        lift = .0115
        _button(p, dr.at(0.0, z, extra=lift + .0005), dr.normal(0.0, z, lift), .0095, GOLD, 'CN_Gold', k=1.0, cap=None)
    for s in (-1, 1):
        _patch(p, dr, s * .62, s * 1.32, m.z(.885), m.z(.935), .0035, .007, CHARCOAL, 'CN_Cloth', 7, 3, k=.85)
        _button(p, dr.at(math.pi + s * .3, m.z(1.045), extra=.0005), dr.normal(math.pi + s * .3, m.z(1.045)), .009, GOLD, 'CN_Gold', k=.95, cap=None)
    _patch(p, dr, math.pi - .03, math.pi + .13, m.z(.33), m.z(.62), .003, .006, CHARCOAL, 'CN_Cloth', 4, 7, k=.8)
    return p, dict(kind='coat', top=m.z(1.075), hem=m.z(.32), closed_to=m.z(.84))


def coat_skirt_white(m):
    """Doctor Ama Okafor: the knee-length skirt of her white coat, right over left, pockets, a half-belt."""
    p = Part('coat_skirt', ('CN_Cloth', 'CN_Lacquer'))
    dr = m.drape(((1.075, .144, .108, -.100), (1.0, .170, .110, -.120), (.94, .190, .112, -.138), (.88, .198, .118, -.146),
                  (.80, .203, .128, -.152), (.72, .207, .140, -.160), (.60, .225, .160, -.176), (.50, .240, .176, -.190)),
                 folds=7, amp=.018, fold_top=.84, fold_low=.5, wrinkle=.001, seed=111, spare=.008, taut=True)
    span = _coat_span(m.z([.5, .82, .9, 1.08]), [-.3, -.04, .3, .3])
    _skirt(p, dr, WHITE_COOL, 'CN_Cloth', m.z(1.075), m.z(.5), nu=60, nv=16, thick=.006, span=span, lap=-1, seed=111)
    for z in m.z((.955, .89)):
        _button(p, dr.at(0.0, z, extra=.0092), dr.normal(0.0, z, .0092), .0075, WHITE_PURE, 'CN_Lacquer', k=.95)
    for s in (-1, 1):
        _patch(p, dr, s * .55, s * 1.05, m.z(.77), m.z(.905), .0032, .0028, WHITE_COOL, 'CN_Cloth', 7, 5, k=.96)
        _patch(p, dr, s * .55, s * 1.05, m.z(.89), m.z(.905), .0062, .0022, WHITE_COOL, 'CN_Cloth', 7, 2, k=.9)
    _patch(p, dr, math.pi - .6, math.pi + .6, m.z(1.0), m.z(1.04), .0032, .004, WHITE_COOL, 'CN_Cloth', 9, 3, k=.94, fold=0.)
    for s in (-1, 1):
        z = m.z(1.02)
        _button(p, dr.at(math.pi + s * .5, z, extra=.0075, fold=0.), dr.normal(math.pi + s * .5, z, .0075, 0.), .007, WHITE_PURE, 'CN_Lacquer', k=.95)
    _patch(p, dr, math.pi - .03, math.pi + .1, m.z(.5), m.z(.68), .0028, .004, WHITE_COOL, 'CN_Cloth', 4, 6, k=.85)
    return p, dict(kind='coat', top=m.z(1.075), hem=m.z(.5), closed_to=m.z(.82))


def oilskin_skirt(m):
    """Dov Pell: the knee-length skirt of a light-blue oilskin, a snapped storm flap, big pocket flaps."""
    p = Part('oilskin_skirt', ('CN_Blue', 'CN_Lacquer'))
    dr = m.drape(((1.075, .157, .121, -.109), (1.0, .169, .120, -.116), (.94, .183, .119, -.132), (.88, .189, .118, -.138),
                  (.80, .197, .124, -.144), (.72, .203, .136, -.152), (.60, .222, .160, -.170), (.47, .242, .184, -.190)),
                 folds=5, amp=.016, fold_top=.8, fold_low=.47, wrinkle=.0015, seed=121, spare=.014, taut=True)
    span = _coat_span(m.z([.47, .66, .72, 1.08]), [-.22, -.02, .3, .3])
    _skirt(p, dr, BLUE, 'CN_Blue', m.z(1.075), m.z(.47), nu=60, nv=15, thick=.007, span=span, lap=1, seed=121)
    n = 12
    _strip(p, dr, np.full(n, .02), m.z(np.linspace(1.075, .72, n)), .05, .0125, .004, BLUE, 'CN_Blue', .95, fold=1.0)
    for z in m.z((.95, .87, .79)):
        _button(p, dr.at(.02, z, extra=.0168), dr.normal(.02, z, .0168), .0065, BLACK, 'CN_Lacquer', h=.004, k=1.0)
    for s in (-1, 1):
        _patch(p, dr, s * .6, s * 1.12, m.z(.8), m.z(.935), .0035, .0035, BLUE, 'CN_Blue', 7, 5, k=.95, bulge=.006)
        _patch(p, dr, s * .58, s * 1.14, m.z(.9), m.z(.955), .011, .004, BLUE, 'CN_Blue', 7, 3, k=.88)
    return p, dict(kind='coat', top=m.z(1.075), hem=m.z(.47), closed_to=m.z(.72))


def work_apron_skirt(m):
    """Marek Duran: a heavy black canvas work apron to the knee, red ties, tools in its pockets."""
    p = Part('apron_skirt', ('CN_Cloth', 'CN_Gold', 'CN_Red'))
    belt = m.torso(.006)
    # The waistband stands clear of the work shirt's tucked hem, so the shirt goes in under it.
    _band(p, belt, m.z(.965), m.z(1.01), .0035, .006, CHARCOAL, 'CN_Cloth', k=.75)
    dr = m.drape(((1.075, .157, .132, -.108), (1.0, .17, .136, -.114), (.92, .184, .140, -.13), (.84, .19, .146, -.136),
                  (.72, .196, .156, -.146), (.60, .2, .164, -.15), (.46, .204, .170, -.154)),
                 folds=4, amp=.008, fold_top=.9, fold_low=.46, wrinkle=.0015, seed=131, spare=.006)
    nv, nu = 14, 20
    Z = m.z(np.linspace(1.065, .46, nv))[:, None] + np.zeros((1, nu))
    TH = np.interp(Z, m.z([.46, 1.065]), [1.0, 1.22]) * np.linspace(-1, 1, nu)[None, :]
    P = dr.at(TH, Z)
    _sheet(p, P, .006, CHARCOAL, 'CN_Cloth', _axis(), k=_cloth_k(dr, TH, Z, m.z(.46), 131, 4.0) * .95)
    for s in (-1, 1):
        _patch(p, dr, s * .22, s * .72, m.z(.76), m.z(.9), .0035, .004, CHARCOAL, 'CN_Cloth', 7, 5, k=.8, bulge=.006)
    c = dr.at(.5, m.z(.88), extra=.018)
    jaw = c + (0, 0, .085)
    _limb(p, [c - (0, 0, .05), jaw - (0, 0, .012)], [.0075, .0085], GOLD, 'CN_Gold', 6, 1.0, None)
    _torus(p, jaw + (0, 0, .006), .016, .0055, _tone(GOLD, .95, None), 'CN_Gold', 12, 5, axis='x', arc=1.6 * math.pi, start=-.3 * math.pi)
    c2 = dr.at(-.4, m.z(.88), extra=.016)
    _limb(p, [c2 - (0, 0, .05), c2 + (.002, -.006, .06)], [.004, .004], RED, 'CN_Red', 6, 1.0)
    # Red ties from the apron's top corners round to a knot at the small of the back.
    for s in (-1, 1):
        n = 12
        th = s * np.linspace(1.22, math.pi - .1, n)
        _strip(p, belt, th, np.full(n, m.z(1.04)), .022, .0095, .003, RED, 'CN_Red', .95, fold=0.)
    knot = belt.at(math.pi, m.z(1.04), extra=.016, fold=0.)
    _shell(p, knot, (.014, .02, .015), RED, 'CN_Red', .9, 10, 6, R=_basis((-1, 0, 0)))
    for s in (-1, 1):
        _limb(p, [knot, knot + (-.012, s * .02, -.05), knot + (-.016, s * .03, -.11)], [.006, .006, .005], RED, 'CN_Red', 5, .9)
    return p, dict(kind='apron', top=m.z(1.065), hem=m.z(.46))


def guard_belt(m):
    """Teodor Vass: a black duty belt with a gold buckle, pouches, white armour tassets and a baton."""
    p = Part('belt', ('CN_Cloth', 'CN_Lacquer', 'CN_Gold', 'CN_Metal'))
    dr = m.torso(.014)
    _band(p, dr, m.z(.955), m.z(1.015), 0., .008, CHARCOAL, 'CN_Cloth', k=.8, rows=3)
    c = dr.at(0., m.z(.985), extra=.004, fold=0.)
    R = _basis(dr.normal(0., m.z(.985), 0., 0.))
    _box(p, c, (.006, .036, .026), GOLD, 'CN_Gold', .004, 1.0, R, cap=None)
    _box(p, c + R[:, 0] * .005, (.003, .024, .016), GOLD_PALE, 'CN_Gold', .002, .9, R, cap=None)
    for th in (-.62, .62, math.pi - .55, -(math.pi - .55)):
        c = dr.at(th, m.z(.975), extra=.026, fold=0.)
        R = _basis(dr.normal(th, m.z(.975), 0., 0.))
        _box(p, c, (.02, .036, .036), CHARCOAL, 'CN_Cloth', .008, .85, R)
        _box(p, c + R[:, 0] * .02 + (0, 0, .03), (.004, .036, .01), CHARCOAL, 'CN_Cloth', .003, .75, R)
        _button(p, c + R[:, 0] * .024 + (0, 0, .022), R[:, 0], .005, GOLD, 'CN_Gold', k=1.0, cap=None)
    # Tassets: white plates over the front of the thighs and one over the seat.
    tass = m.drape(((1.0, .175, .13, -.13), (.92, .19, .138, -.152), (.82, .2, .146, -.16)), n=2.3, spare=.004)
    for th0, th1 in ((-.62, -.06), (.06, .62), (math.pi - .5, math.pi + .5)):
        TH, Z = np.meshgrid(np.linspace(th0, th1, 7), m.z(np.linspace(.99, .84, 5)))
        P = tass.at(TH, Z, extra=.004 * np.sin(math.pi * (TH - th0) / (th1 - th0)))
        Pp, Qq = _sheet(p, P, .006, WHITE_PURE, 'CN_Lacquer', _axis(), k=.92 - .1 * (m.z(.99) - Z))
        edge = _edge_mid(Pp[-1], Qq[-1])
        _limb(p, edge, .0042, WHITE_PURE, 'CN_Lacquer', 6, .85)
        for t in (.2, .8):
            th = th0 + t * (th1 - th0)
            _button(p, tass.at(th, m.z(.965), extra=.0045), tass.normal(th, m.z(.965), .0045), .0045, ASH, 'CN_Metal', k=1.0, cap=None)
    # A baton hangs in a ring at the right hip, behind the hand.
    c = dr.at(2.35, m.z(.9), extra=.035, fold=0.)
    _limb(p, [c + (0, 0, .1), c - (0, 0, .22)], [.016, .015], BLACK, 'CN_Lacquer', 10, 1.0)
    _torus(p, c + (0, 0, .06), .021, .004, _tone(ASH, 1.0, None), 'CN_Metal', 14, 5, axis='z')
    return p, dict(kind='belt', top=m.z(1.015), hem=m.z(.84))


# ---------------------------------------------------------------- ported garments: the tops

def _form(top, z_open):
    """A top's form: its hem, the lowest point of its neck opening, and people._top's borders (the sleeves meet its
    armholes)."""
    return dict(kind='top', bottom=top['z_bot'], open=z_open, top=top)


def coat_black(m):
    """Kairos: the body of his long black wool coat, lapping left over right like its skirt: notched lapels,
    four gold buttons, a breast pocket with a white square, a gold watch chain, a back seam and a collar."""
    g, seed = m.g, 201
    p = Part('coat', ('CN_Cloth', 'CN_Gold'))
    thick = .009
    dr = m.torso(((1.05, .022), (1.12, .016), (1.3, .013), (1.45, .010), (1.5, .004)), taut=True, wrinkle=.0009, seed=seed)
    z_break = m.z(1.265)
    fronts = front_edges(g, dr, z_break, .30, 1, thick)
    top = bodice(p, g, dr, CHARCOAL, 'CN_Cloth', thick=thick, z_bot=m.z(1.055), fronts=fronts, k=.95, seed=seed)
    right_edge, left_edge, lift = fronts
    z_sh = top['z_sh']
    rise = np.linspace(z_break, z_sh, 40)
    cross = float(np.interp(0., [float(right_edge(z)) for z in rise], rise))
    _lapels(p, dr, fronts, {-1: z_break, 1: cross + .01}, z_sh - .012, .36, .005, CHARCOAL, 'CN_Cloth')
    th_end = top['th_neck'] - .03
    a_mid = max(.9, th_end + .1)
    _collar(p, dr, th_end, collar_seam(g, dr, [th_end, math.pi / 2, math.pi], [z_sh - .022, m.z(1.5), m.z(1.462)], m.z(1.47)),
            lambda a: np.interp(a, [th_end, a_mid, math.pi / 2, math.pi], [z_sh + .018, m.z(1.525), m.z(1.558), m.z(1.535)]),
            .007, .006, CHARCOAL, 'CN_Cloth', stand=.008, knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    # Buttons on the left panel's edge line; the top one is where the lapels break.
    for z in list(m.z((1.075, 1.14, 1.205))) + [z_break - .005]:
        e = float(lift(np.array(0.), np.array(z), -1)) + .0005
        _button(p, dr.at(0., z, extra=e), dr.normal(0., z, e), .0095, GOLD, 'CN_Gold', k=1.0, cap=None)
    # Breast pocket on the left chest with a white square standing out of it.
    _panel(p, dr, -.86, -.5, m.z(1.292), m.z(1.306), .0035, .004, CHARCOAL, 'CN_Cloth', 6, 2, k=.8, fold=0.)
    for i, (a, b, h) in enumerate(((-.82, -.7, .028), (-.72, -.6, .022))):
        _panel(p, dr, a, b, m.z(1.3), m.z(1.3) + h, .0022 + .0012 * i, .0025, WHITE_PURE, 'CN_Cloth', 3, 3, k=.95 - .05 * i, fold=0.)
    # A gold watch chain from the third button to a pocket at the right waist (on the coat skirt's front).
    a = dr.at(0., m.z(1.14), extra=.014)
    b = dr.at(.62, m.z(1.08), extra=.004)
    _limb(p, bezier(a, a + (.005, .03, -.05), b + (.008, -.03, -.03), b, 14), .0018, GOLD, 'CN_Gold', 5, 1.0, None)
    _panel(p, dr, .5, .78, m.z(1.07), m.z(1.082), .0032, .004, CHARCOAL, 'CN_Cloth', 5, 2, k=.8, fold=0.)
    # Back seam and two darts.
    for th, w in ((math.pi, .012), (math.pi - .55, .007), (math.pi + .55, .007)):
        n = 9
        _strip(p, dr, np.full(n, th), m.z(np.linspace(1.065, 1.36 if w > .01 else 1.25, n)), w, .0006, .002, CHARCOAL, 'CN_Cloth', .75, fold=0.)
    return p, _form(top, z_break)


def blouse_strap(m):
    """Petra Lune: an ivory blouse with pin-tucks, a buttoned placket and a stand collar tied with a black
    ribbon, and the canvas strap of her satchel across it from the left hip over the right shoulder."""
    g, seed = m.g, 211
    p = Part('blouse', ('CN_Cloth', 'CN_Gold'))
    dr = m.torso(((1.07, .003), (1.11, .011), (1.3, .009), (1.45, .007), (1.5, .004)), tuck=(1.07, 1.15, .002), wrinkle=.0007, seed=seed)
    z_neck, shape = m.z(1.44), 1.6
    top = bodice(p, g, dr, IVORY, 'CN_Cloth', thick=.005, z_bot=m.z(1.07), neck_front=z_neck, neck_back=m.z(1.465), neck_shape=shape,
                 k=.97, seed=seed)
    z_open = neck_opening(g, dr, z_neck, m.z(1.465), shape)
    _collar(p, dr, .1, lambda a: z_open(a) - .004, lambda a: z_open(a) + .03, .006, .005, IVORY, 'CN_Cloth', k=.94)
    _bow(p, dr, 0., z_neck + .012, .006, CHARCOAL, 'CN_Cloth', loop=.02, tail=.075, width=.011, seed=seed)
    # Placket and its small gold buttons; three pin-tucks either side over the breast.
    _panel(p, dr, -.075, .075, m.z(1.07), z_neck - .006, .0026, .003, IVORY, 'CN_Cloth', 3, 12, k=.93)
    for z in np.linspace(m.z(1.11), z_neck - .025, 5):
        _button(p, dr.at(0., z, extra=.003), dr.normal(0., z, .003), .0042, GOLD, 'CN_Gold', h=.0024, sides=8, k=1.0, cap=None)
    for s in (-1, 1):
        for th in (.13, .19, .25):
            n = 8
            _strip(p, dr, np.full(n, s * th), np.linspace(m.z(1.2), z_neck - .01 - .02 * th, n), .0045, .0009, .002, IVORY, 'CN_Cloth', .9, cols=2)
    # The satchel's strap: from the bag's front ring at the left hip, across the front, over the right shoulder and down
    # the back to the bag's back ring (the skirt carries the last hand's breadth down to the bag).
    oth, oz = top['over'](m.y(.097), 9, 1)
    th_f, th_b = float(oth[0]), float(oth[-1])
    t = np.linspace(0, 1, 18)
    front = (np.interp(t, [0, .2, .55, .8, 1], [-2.18, -1.57, -.55, th_f - .25, th_f]),
             np.interp(t, [0, .2, .55, .8, 1], list(m.z((1.122, 1.098, 1.19, 1.34))) + [top['z_sh']]))
    t = np.linspace(0, 1, 14)
    back = (np.interp(t, [0, .25, .6, 1], [th_b, th_b + .3, math.pi + .4, 2 * math.pi - 2.68]),
            np.interp(t, [0, .25, .6, 1], [top['z_sh']] + list(m.z((1.36, 1.22, 1.122)))))
    th, z = _path(front, (oth, oz), back)
    _strip(p, dr, th, z, .03, .0062, .004, CHARCOAL, 'CN_Cloth', .9, fold=0.)
    return p, _form(top, z_neck)


def blouse_shawl(m):
    """Orsolya Fenn: a light-blue cotton blouse with a scooped neck, and a white knitted shawl round her
    shoulders, its ends crossed over the breast and tucked into her apron's band."""
    g, seed = m.g, 221
    p = Part('blouse', ('CN_Cloth',))
    dr = m.torso(((1.07, .003), (1.11, .012), (1.3, .010), (1.45, .008), (1.5, .004)), tuck=(1.07, 1.16, .0025), wrinkle=.0008, seed=seed)
    top = bodice(p, g, dr, BLUE, 'CN_Cloth', thick=.005, z_bot=m.z(1.07), neck_front=m.z(1.37), neck_back=m.z(1.45), neck_shape=2.0,
                 k=.95, seed=seed)
    _piping(p, _neck_loop(top, top['ms']), .003, BLUE, 'CN_Cloth', k=.85, closed=True)
    # One long shawl: from its right end tucked at the left waist, up across the breast, over the left shoulder,
    # dipping across the back, over the right shoulder and down across the breast to the right waist.
    y = m.y(.105)
    lth0 = -float(top['over'](y, 9, 1)[0][0])
    t = np.linspace(0, 1, 12)
    a = (np.interp(t, [0, .45, 1], [.36, -.2, lth0]), np.interp(t, [0, .45, 1], [m.z(1.062), m.z(1.2), top['z_sh']]))
    b = (np.interp(t, [0, .55, 1], [-lth0, .2, -.36]) - 2 * math.pi, np.interp(t, [0, .55, 1], [top['z_sh'], m.z(1.2), m.z(1.062)]))
    th, z = _shawl_path(top, y, m.z(1.29), a, b)
    s = np.linspace(0, 1, len(th))
    width = np.interp(s, [0, .2, .34, .5, .66, .8, 1], [.05, .075, .095, .15, .095, .075, .05])
    # The ends cross over the breast, the one laid last a little higher; both run on under the skirt's waistband.
    tuck = np.clip((z - m.z(1.088)) / .035, 0, 1)
    extra = .0015 + tuck * (.0047 + .0045 * (s > .5) * (th < -2 * math.pi + .9))
    rib = 1 + .06 * np.sin(np.arange(len(th)) * 2.2)
    _strip(p, dr, th, z, width, extra, .0075, WHITE, 'CN_Cloth', rib, fold=0., cols=4, crown=.003)
    return p, _form(top, m.z(1.37))


def tunic(m):
    """Tamsin: the bodice of her light-blue tunic, white piping, a white Peter Pan collar, two gold buttons on
    the left shoulder, and a pocket with the spool of her kite's string in it."""
    g, seed = m.g, 231
    p = Part('tunic', ('CN_Cloth', 'CN_Gold'))
    # Close over the chest as a child's bodice is (the Mannequin's 1.3 cm of ease left it boxy on her, author 2026-11-10).
    dr = m.torso(((1.05, .005), (1.1, .007), (1.3, .006), (1.45, .005), (1.5, .003)), wrinkle=.0008, seed=seed)
    z_neck, shape = m.z(1.415), 2.0
    top = bodice(p, g, dr, BLUE, 'CN_Cloth', thick=.005, z_bot=m.z(1.05), neck_front=z_neck, neck_back=m.z(1.46), neck_shape=shape, seed=seed)
    for side in (1, -1):
        _piping(p, _arm_loop(top, side, top['ms']), .003, WHITE_PURE, 'CN_Cloth', .92)
    z_open = neck_opening(g, dr, z_neck, m.z(1.46), shape)
    _flat_collar(p, dr, z_open, .046, .032, .0055, .004, WHITE_PURE, 'CN_Cloth', k=.95)
    oth, _ = top['over'](m.y(.1), 9, -1)
    for z in (top['z_sh'] - .012, top['z_sh'] - .04):
        _button(p, dr.at(oth[0], z, extra=.0005), dr.normal(oth[0], z, .0005), .0055, GOLD, 'CN_Gold', h=.003, sides=8, cap=None)
    th0, th1, z0, z1 = .3, .78, m.z(1.1), m.z(1.18)
    _patch(p, dr, th0, th1, z0, z1, .0028, .003, BLUE, 'CN_Cloth', 6, 4, k=.92, bulge=.004, fold=0.)
    _piping(p, dr.at(np.linspace(th0, th1, 6), z1, extra=.0045, fold=0.), .0022, WHITE_PURE, 'CN_Cloth', .9)
    c = dr.at(.55, z1 - .005, extra=.013, fold=0.)
    spool = Part('tmp', p.slots)
    for i, (r, h) in enumerate(((.012, .004), (.009, .026), (.012, .004))):
        zb = (0, .004, .03)[i]
        _tube(spool, [(0, 0, zb), (0, 0, zb + h)], r, _tone(WHITE_PURE, .9 - .12 * (i == 1)), 'CN_Cloth', 10)
    _merge(p, spool, _rot((1, 0, 0), 14), c)
    return p, _form(top, z_neck)


def robe_shawl(m):
    """Old Wen: the bodice of her ivory robe, wrapped left over right with a broad collar band, and a long
    black stole round her shoulders, gold fringe at its ends, the right end hanging longer than the left."""
    g, seed = m.g, 241
    p = Part('robe', ('CN_Cloth', 'CN_Gold'))
    thick = .006
    dr = m.torso(((1.0, .014), (1.1, .016), (1.3, .012), (1.45, .009), (1.5, .004)), wrinkle=.0009, seed=seed)
    z_break = m.z(1.24)
    fronts = front_edges(g, dr, z_break, .55, 1, thick, curve=.8)
    right_edge, left_edge, lift = fronts
    top = bodice(p, g, dr, IVORY, 'CN_Cloth', thick=thick, z_bot=m.z(1.0), fronts=fronts, k=.96, seed=seed)
    z_sh = top['z_sh']
    band = .2

    def ex(side):
        return lambda TH, Z: lift(TH, Z, side) + .0055
    (P, Q), _, _ = _panel(p, dr, lambda z: left_edge(z) - band, left_edge, m.z(1.0), z_sh, ex(-1), .005, IVORY, 'CN_Cloth', 4, 14, k=.88, fold=0.)
    _piping(p, _edge_mid(P[:, 0], Q[:, 0]), .0018, GOLD_PALE, 'CN_Gold', .95, cap=None)
    rise = np.linspace(m.z(1.0), z_sh, 60)
    cross = float(np.interp(0., [float(right_edge(z)) for z in rise], rise))
    _panel(p, dr, right_edge, lambda z: right_edge(z) + band, cross - .02, z_sh, ex(1), .005, IVORY, 'CN_Cloth', 4, 8, k=.88, fold=0.)
    th_end = top['th_neck'] - .02
    _collar(p, dr, th_end, collar_seam(g, dr, [th_end, math.pi / 2, math.pi], [z_sh - .01, m.z(1.495), m.z(1.455)], m.z(1.47)),
            lambda a: np.interp(a, [th_end, math.pi / 2, math.pi], [z_sh + .03, m.z(1.535), m.z(1.515)]), .0065, .005, IVORY, 'CN_Cloth', k=.88,
            knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    # The stole: from the left breast over the left shoulder, across the upper back and over the right shoulder to the
    # right breast; from each breast it falls straight, a hand's breadth clear of the sash.
    y = m.y(.1)
    lth0 = -float(top['over'](y, 9, 1)[0][0])
    t = np.linspace(0, 1, 6)
    a = (np.interp(t, [0, 1], [-.62, lth0]), np.interp(t, [0, 1], [m.z(1.275), z_sh]))
    b = (np.interp(t, [0, 1], [-lth0, .62]) - 2 * math.pi, np.interp(t, [0, 1], [z_sh, m.z(1.275)]))
    th, z = _shawl_path(top, y, m.z(1.3), a, b)
    s = np.linspace(0, 1, len(th))
    width = np.interp(s, [0, .25, .5, .75, 1], [.085, .1, .14, .1, .085])
    E = .0105 + .004 * np.exp(-((s - .5) / .2) ** 2)
    _strip(p, dr, th, z, width, E, .007, CHARCOAL, 'CN_Cloth', 1 + .05 * np.sin(np.arange(len(th)) * 1.7), fold=0., cols=4, crown=.003)
    for side, z_end in ((-1, 1.105), (1, .95)):
        th0 = side * .62
        c0 = dr.at(th0, m.z(1.275), extra=.0105, fold=0.)
        n = 7
        zs = m.z(np.linspace(1.275, z_end, n))
        C = np.stack([c0[0] + .012 * np.linspace(0, 1, n) ** 2, np.full(n, c0[1]) + side * .004 * np.linspace(0, 1, n), zs], -1)
        _ribbon3d(p, C, (0, 1, 0), (1, .0, 0), .085, .007, CHARCOAL, 'CN_Cloth', .95, cols=4, crown=.003)
        y0, y1 = c0[1] - .04, c0[1] + .04
        _fringe(p, (C[-1, 0], y0, zs[-1]), (C[-1, 0], y1, zs[-1]), 9, .06, .0022, GOLD_DEEP, 'CN_Cloth', seed + side, .95)
    return p, _form(top, z_break)


def work_apron(m):
    """Marek Duran: a light-blue chambray work shirt, and the bib of his black canvas apron over it, its neck
    strap, gold rivets, a pencil and a folding rule in the bib pocket."""
    g, seed = m.g, 251
    p = Part('shirt_apron', ('CN_Cloth', 'CN_Gold', 'CN_Red', 'CN_Lacquer'))
    dr = m.torso(((.99, .003), (1.05, .011), (1.3, .011), (1.45, .009), (1.5, .004)), tuck=(.99, 1.08, .002), wrinkle=.0009, seed=seed)
    z_neck, shape = m.z(1.445), 1.6
    top = bodice(p, g, dr, BLUE, 'CN_Cloth', thick=.005, z_bot=m.z(.99), neck_front=z_neck, neck_back=m.z(1.475), neck_shape=shape, k=.9,
                 seed=seed)
    z_open = neck_opening(g, dr, z_neck, m.z(1.475), shape)
    _flat_collar(p, dr, z_open, .07, .04, .0058, .004, BLUE, 'CN_Cloth', k=.86)
    _panel(p, dr, -.07, .07, m.z(.99), z_neck - .005, .0025, .003, BLUE, 'CN_Cloth', 3, 12, k=.86)
    for z in np.linspace(m.z(1.04), z_neck - .02, 6):
        _button(p, dr.at(0., z, extra=.0028), dr.normal(0., z, .0028), .0045, WHITE_PURE, 'CN_Lacquer', h=.0022, sides=8, k=.95)
    # The bib stands off the shirt where the canvas bridges the waist, and meets the apron's top edge below.
    z_lo, z_hi = m.z(1.16), m.z(1.32)

    def stand(TH, Z):
        return .014 + .006 * np.clip((z_lo - Z) / .1, 0, 1) - .004 * np.clip((Z - z_hi) / .05, 0, 1)
    z0, z1 = m.z(1.04), m.z(1.365)
    shade = _cloth_k(dr, 0 * np.ones((10, 9)), np.linspace(z1, z0, 10)[:, None] + np.zeros((10, 9)), z0, seed, 2.0) * .95
    (P, Q), TH, Z = _panel(p, dr, lambda z: -np.interp(z, [z0, z1], [.62, .44]), lambda z: np.interp(z, [z0, z1], [.62, .44]),
                           z0, z1, stand, .006, CHARCOAL, 'CN_Cloth', 9, 10, k=shade, fold=0.)
    _piping(p, _border(P, Q), .003, CHARCOAL, 'CN_Cloth', .8, closed=True)
    # Pocket across the bib, a red pencil and a white folding rule with gold joints in it.
    pz0, pz1 = m.z(1.21), m.z(1.3)
    _panel(p, dr, -.36, .36, pz0, pz1, lambda TH, Z: stand(TH, Z) + .0035, .004, CHARCOAL, 'CN_Cloth', 7, 4, k=.85, fold=0.)
    _strip(p, dr, np.zeros(4), np.linspace(pz0, pz1, 4), .004, float(stand(0, m.z(1.25))) + .0045, .002, CHARCOAL, 'CN_Cloth', .7, cols=2, fold=0.)
    c = dr.at(-.18, pz1 - .03, extra=float(stand(0, m.z(1.27))) + .0075, fold=0.)
    _limb(p, [c, c + (.003, .004, .1)], [.0042, .0042], RED, 'CN_Red', 6, 1.0)
    _limb(p, [c + (.003, .004, .1), c + (.0035, .0045, .112)], [.0042, .0012], WHITE, 'CN_Cloth', 6, .8)
    c = dr.at(.2, pz1 - .04, extra=float(stand(0, m.z(1.27))) + .0075, fold=0.)
    R = _basis(dr.normal(.2, pz1, 0., 0.))
    for i in range(3):
        _box(p, c + R[:, 2] * (.03 + .045 * i) + R[:, 1] * .003 * i, (.0025, .009, .024), WHITE_PURE, 'CN_Cloth', .0015, .92 - .04 * i, R)
        _button(p, c + R[:, 2] * (.054 + .045 * i) + R[:, 0] * .003, R[:, 0], .004, GOLD, 'CN_Gold', h=.002, sides=6, cap=None)
    # Neck strap from the bib's top corners over the shoulders to a buckle behind the neck; rivets at the corners.
    for side in (1, -1):
        oth, oz = top['over'](m.y(.088), 8, side)
        t = np.linspace(0, 1, 5)
        a = (np.interp(t, [0, 1], [side * .44, oth[0]]), np.interp(t, [0, 1], [z1 - .01, top['z_sh']]))
        b = (np.interp(t, [0, 1], [oth[-1], side * (math.pi - .02)]), np.interp(t, [0, 1], [top['z_sh'], m.z(1.478)]))
        th, z = _path(a, (oth, oz), b)
        E = np.interp(np.arange(len(th)), [0, 4, len(th) - 1], [float(stand(0, z1)) + .004, .0075, .0075])
        _strip(p, dr, th, z, .026, E, .004, CHARCOAL, 'CN_Cloth', .85, fold=0.)
        q = dr.at(side * .46, z1 - .022, extra=float(stand(0, z1)) + .002)
        _button(p, q, dr.normal(side * .46, z1 - .022, 0.), .0055, GOLD, 'CN_Gold', h=.003, sides=8, cap=None)
    c = dr.at(math.pi, m.z(1.478), extra=.012, fold=0.)
    _box(p, c, (.004, .02, .014), GOLD_PALE, 'CN_Gold', .003, 1.0, _basis((-1, 0, 0)), cap=None)
    return p, _form(top, z_neck)


def blouse(m):
    """Sefa Moreno: a white cotton blouse gathered on a drawstring at a wide neckline, an embroidered border
    of red, gold and light blue under it, and a necklace of small gold coins."""
    g, seed = m.g, 261
    p = Part('blouse', ('CN_Cloth', 'CN_Gold'))
    dr = m.torso(((1.07, .003), (1.11, .013), (1.3, .011), (1.45, .009), (1.5, .004)), tuck=(1.07, 1.17, .003), wrinkle=.0008, seed=seed,
                 ripples=((1.26, 1.4, 44, .0022),))
    z_neck, shape = m.z(1.385), 2.4
    top = bodice(p, g, dr, WHITE_PURE, 'CN_Cloth', thick=.005, z_bot=m.z(1.07), neck_front=z_neck, neck_back=m.z(1.44), neck_shape=shape,
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
    for half, z_c in ((0., z_neck), (math.pi, m.z(1.44))):
        edges = np.linspace(-th_neck * .96, th_neck * .96, 17)
        for i in range(16):
            th = np.linspace(edges[i], edges[i + 1], 3)
            z = z_c + (top['z_sh'] - z_c) * np.clip(np.abs(th) / th_neck, 0, 1) ** shape - .018
            _strip(p, dr, half + th, z, .014, .0032, .0022, colours[i % 4], 'CN_Cloth', .95, cols=2, fold=1.0, crown=.001)
    # A fine gold chain hung with coins, lying on the breast.
    t = np.linspace(-1, 1, 21)
    th = .58 * t
    z = m.z(1.43) - .085 * (1 - t ** 2) - .012 * np.abs(t)
    _limb(p, dr.at(th, z, extra=.0045, fold=1.0), .0013, GOLD, 'CN_Gold', 4, 1.0, None)
    for i in range(3, 18, 2):
        q = dr.at(th[i], z[i] - .011, extra=.0052, fold=1.0)
        _button(p, q, dr.normal(th[i], z[i] - .011, .0052, 1.0), .0072 if i != 10 else .0095, GOLD, 'CN_Gold', h=.0018, sides=10, cap=None)
    return p, _form(top, z_neck)


def armour_vest(m):
    """Teodor Vass: a quilted black gambeson, over it a white lacquered breastplate and backplate with gold
    edges, a keel and rivets, black leather shoulder straps with gold buckles, and a red sash."""
    g, seed = m.g, 271
    p = Part('armour', ('CN_Cloth', 'CN_Lacquer', 'CN_Gold', 'CN_Black', 'CN_Metal'))
    dr = m.torso(((.975, .004), (1.03, .014), (1.3, .015), (1.45, .011), (1.5, .005)), taut=True, wrinkle=.0006, seed=seed,
                 quilt=(.042, .0028, .975, 1.47))
    top = bodice(p, g, dr, CHARCOAL, 'CN_Cloth', thick=.008, z_bot=m.z(.975), neck_front=m.z(1.44), neck_back=m.z(1.47), neck_shape=1.8,
                 k=.9, nv=22, seed=seed)
    z_sh = top['z_sh']
    z_open = neck_opening(g, dr, m.z(1.44), m.z(1.47), 1.8)
    collar_top = m.z((1.475, 1.535, 1.515))
    _collar(p, dr, .2, lambda a: z_open(a) - .006, lambda a: np.maximum(z_open(a) + .012, np.interp(a, [0, math.pi / 2, math.pi], collar_top)),
            .009, .008, CHARCOAL, 'CN_Cloth', k=.85, stand=.004)
    # The plates follow the gambeson a finger off it; the breastplate has a keel down its middle.
    keel_lo = m.z(1.04)

    def plate_out(keel):
        def f(TH, Z):
            a = np.abs(np.angle(np.exp(1j * (TH - (0. if keel else math.pi)))))
            return .013 + (.006 * np.exp(-(a / .14) ** 2) * _smooth((Z - keel_lo) / .22) if keel else 0.)
        return f
    rivets = []
    widths = m.z((1.0, 1.3, 1.45))
    breast_top, back_top = m.z(1.42), m.z(1.43)
    for keel, mid, lo_z, hi_z, half_lo, half_hi in ((True, 0., m.z(1.03), lambda th: breast_top + .028 * (np.abs(th) / .52) ** 2, .9, .52),
                                                     (False, math.pi, m.z(1.04),
                                                      lambda th: back_top + .02 * (np.abs(np.angle(np.exp(1j * (th - math.pi)))) / .55) ** 2,
                                                      .95, .55)):
        def lo_th(z, mid=mid, a=half_lo, b=half_hi):
            return mid - np.interp(z, widths, [a, a, b])

        def hi_th(z, mid=mid, a=half_lo, b=half_hi):
            return mid + np.interp(z, widths, [a, a, b])
        shade = .93 - .08 * (m.z(1.3) - np.linspace(m.z(1.43), m.z(1.03), 10)[:, None]) ** 2 + 0 * np.ones((10, 11))
        (P, Q), TH, Z = _panel(p, dr, lo_th, hi_th, lo_z, hi_z, plate_out(keel), .005, WHITE_PURE, 'CN_Lacquer', 11, 10, k=shade, fold=0., cap=.9)
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
        oth, oz = top['over'](m.y(.112), 8, side)
        _strip(p, dr, oth, oz, .034, .0115, .005, CHARCOAL, 'CN_Black', .9, fold=0.)
        q = dr.at(oth[0], z_sh - .022, extra=.0175, fold=0.)
        R = _basis(dr.normal(oth[0], z_sh - .022, .0175, 0.))
        _box(p, q, (.0025, .015, .012), GOLD, 'CN_Gold', .002, 1.0, R, cap=None)
        _box(p, q + R[:, 0] * .0024, (.0012, .009, .007), CHARCOAL, 'CN_Black', .001, .8, R)
    # Side straps under the arms join the plates at the waist.
    for z in m.z((1.055, 1.09)):
        for side in (1, -1):
            th = side * np.linspace(.86, math.pi - .92, 9)
            _strip(p, dr, th, np.full(9, z), .016, .004, .004, CHARCOAL, 'CN_Black', .85, fold=0.)
            q = dr.at(side * .88, z, extra=.0175, fold=0.)
            _box(p, q, (.002, .011, .011), ASH, 'CN_Metal', .0015, 1.0, _basis(dr.normal(side * .88, z, .017, 0.)), cap=None)
    # A red sash worn as a baldric: from the right shoulder across the breastplate, under the left arm at the waist, and
    # back up across the backplate; a gold brooch holds it on the shoulder.
    oth, oz = top['over'](m.y(.097), 8, 1)
    t = np.linspace(0, 1, 13)
    front = (np.interp(t, [0, .28, .62, .85, 1], [-math.pi / 2 - .1, -.95, 0., oth[0] - .1, oth[0]]),
             np.interp(t, [0, .28, .62, .85, 1], list(m.z((1.04, 1.06, 1.24, 1.375))) + [z_sh]))
    back = (np.interp(t, [0, .15, .38, .72, 1], [oth[-1], oth[-1] + .1, math.pi, math.pi + .95, 1.5 * math.pi]),
            np.interp(t, [0, .15, .38, .72, 1], [z_sh] + list(m.z((1.375, 1.24, 1.06, 1.04)))))
    th, z = _path(front, (oth, oz), back)
    a = np.abs(np.angle(np.exp(1j * th)))
    on_plate = np.maximum(_smooth((.86 - a) / .1) * (z < breast_top + .01), _smooth((a - (math.pi - .9)) / .1) * (z < back_top + .01))
    E = .009 + .0105 * on_plate + .008 * (z > z_sh - .01)
    E[-1] += .004  # the back end laps over the front end under the arm
    _strip(p, dr, th, z, .046, E, .005, RED, 'CN_Cloth', 1 + .05 * np.sin(np.arange(len(th)) * 1.9), fold=0., cols=4, crown=.003)
    q = dr.at(oth[0] - .02, z_sh - .035, extra=.026, fold=0.)
    nrm = dr.normal(oth[0] - .02, z_sh - .035, .026, 0.)
    _button(p, q, nrm, .016, GOLD, 'CN_Gold', h=.005, sides=12, cap=None)
    _button(p, q + nrm * .004, nrm, .007, BLUE, 'CN_Lacquer', h=.004, sides=10, k=1.0)
    return p, _form(top, m.z(1.44))


def coat_white(m):
    """Doctor Ama Okafor: the body of her white coat, right over left like its skirt, notched lapels, white
    buttons, a breast pocket with two pens, and a stethoscope round her neck."""
    g, seed = m.g, 281
    p = Part('coat', ('CN_Cloth', 'CN_Lacquer', 'CN_Metal', 'CN_Gold'))
    thick = .006
    dr = m.torso(((1.05, .02), (1.12, .015), (1.3, .012), (1.45, .010), (1.5, .004)), taut=True, wrinkle=.0009, seed=seed)
    z_break = m.z(1.19)
    fronts = front_edges(g, dr, z_break, .3, -1, thick)
    right_edge, left_edge, lift = fronts
    top = bodice(p, g, dr, WHITE_COOL, 'CN_Cloth', thick=thick, z_bot=m.z(1.05), fronts=fronts, seed=seed)
    z_sh = top['z_sh']
    rise = np.linspace(z_break, z_sh, 40)
    cross = float(np.interp(0., [float(-left_edge(z)) for z in rise], rise))
    _lapels(p, dr, fronts, {1: z_break, -1: cross + .01}, z_sh - .012, .4, .004, WHITE_COOL, 'CN_Cloth', k=.94)
    th_end = top['th_neck'] - .03
    a_mid = max(.9, th_end + .1)
    _collar(p, dr, th_end, collar_seam(g, dr, [th_end, math.pi / 2, math.pi], [z_sh - .022, m.z(1.49), m.z(1.452)], m.z(1.47)),
            lambda a: np.interp(a, [th_end, a_mid, math.pi / 2, math.pi], [z_sh + .018, m.z(1.515), m.z(1.545), m.z(1.52)]), .006, .005,
            WHITE_COOL, 'CN_Cloth', stand=.008, k=.93, knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    for z in list(m.z((1.08, 1.135))) + [z_break - .005]:
        e = float(lift(np.array(0.), np.array(z), 1)) + .0005
        _button(p, dr.at(0., z, extra=e), dr.normal(0., z, e), .0075, WHITE_PURE, 'CN_Lacquer', k=.95)
    # Breast pocket on the left and two pens clipped in it.
    th0, th1, z0, z1 = -.95, -.5, m.z(1.2), m.z(1.29)
    _patch(p, dr, th0, th1, z0, z1, .0026, .003, WHITE_COOL, 'CN_Cloth', 6, 4, k=.95, bulge=.003, fold=0.)
    for i, (th, colour, slot) in enumerate(((-.62, BLACK, 'CN_Lacquer'), (-.75, BLUE, 'CN_Lacquer'))):
        c = dr.at(th, z1 - .035, extra=.0075, fold=0.)
        _limb(p, [c, c + (0, 0, .06 - .008 * i)], [.0045, .0045], colour, slot, 6, 1.0)
        _limb(p, [c + (0, 0, .06 - .008 * i), c + (.001, 0, .066 - .008 * i)], [.0045, .002], colour, slot, 6, .9)
        _box(p, dr.at(th, z1 + .008, extra=.0105, fold=0.), (.0012, .0022, .014), GOLD, 'CN_Gold', .0008, 1.0,
             _basis(dr.normal(th, z1, 0., 0.)), cap=None)
    # The stethoscope: tubing round the back of the neck over the collar, its two ends hanging down the lapels, the
    # chest piece on the right and the steel ear tubes on the left.
    t = np.linspace(0, 1, 15)
    th = np.interp(t, [0, .2, .5, .8, 1], [.3, .5, math.pi, 2 * math.pi - .5, 2 * math.pi - .32])
    z = np.interp(t, [0, .2, .35, .5, .65, .8, 1], m.z((1.27, 1.41, 1.5, 1.505, 1.5, 1.41, 1.3)))
    E = np.interp(t, [0, .2, .35, .65, .8, 1], [.016, .021, .027, .027, .021, .018])
    tubing = dr.at(th, z, extra=E, fold=0.)
    _limb(p, tubing, .0045, BLACK, 'CN_Lacquer', 7, 1.0)
    end = tubing[0]
    _limb(p, [end, end - (0, 0, .03)], [.0042, .0042], BLACK, 'CN_Lacquer', 7, 1.0)
    head = end - (0, 0, .045)
    nrm = dr.normal(.3, m.z(1.23), 0., 0.)
    _shell(p, head + nrm * .004, (.007, .019, .019), ASH, 'CN_Metal', 1.0, 12, 6, R=_basis(nrm), cap=None)
    _limb(p, [head + (0, 0, .018), end - (0, 0, .028)], [.0028, .0028], ASH, 'CN_Metal', 6, 1.2, None)
    e2 = tubing[-1]
    for s in (-1, 1):
        a = e2 + (0, s * .008, 0)
        _limb(p, [a, a + (.006, s * .004, -.05), a + (.012, s * .01, -.085)], [.0018, .0018, .0018], ASH, 'CN_Metal', 5, 1.3, None)
        _shell(p, a + (.013, s * .011, -.09), (.0045, .0045, .006), BLACK, 'CN_Lacquer', .9, 6, 4)
    return p, _form(top, z_break)


def robe_tall(m):
    """The Listener: the bodice of a white robe wrapped left over right in a deep V over a light-blue
    under-robe, a broad gold orphrey down both front edges and round the neck."""
    g, seed = m.g, 291
    p = Part('robe', ('CN_Cloth', 'CN_Gold'))
    thick = .006
    dr = m.torso(((1.0, .012), (1.1, .015), (1.3, .013), (1.45, .010), (1.5, .004)), wrinkle=.0009, seed=seed)
    inner = m.torso(((1.0, .004), (1.3, .005), (1.45, .004)), wrinkle=.0005, seed=seed + 1)
    z_break = m.z(1.14)
    fronts = front_edges(g, dr, z_break, .6, 1, thick, curve=.75)
    right_edge, left_edge, lift = fronts
    top = bodice(p, g, dr, WHITE_PURE, 'CN_Cloth', thick=thick, z_bot=m.z(1.0), fronts=fronts, k=.95, seed=seed)
    z_sh = top['z_sh']
    under = m.z(1.47)
    _panel(p, inner, -.62, .62, m.z(1.12), lambda th: under - .01 * (np.abs(th) / .62), .0, .004, BLUE, 'CN_Cloth', 9, 8, k=.95, fold=0.)
    band = .17

    def ex(side):
        return lambda TH, Z: lift(TH, Z, side) + .005
    for side in (-1, 1):
        edge = left_edge if side < 0 else right_edge
        z0 = m.z(1.0 if side < 0 else 1.22)
        lo = (lambda z, e=edge: e(z) - band) if side < 0 else edge
        hi = edge if side < 0 else (lambda z, e=edge: e(z) + band)
        (P, Q), TH, Z = _panel(p, dr, lo, hi, z0, z_sh, ex(side), .0045, GOLD_DEEP, 'CN_Cloth', 4, 14, k=1.0, fold=0.)
        for col in (0, -1):
            _piping(p, _edge_mid(P[:, col], Q[:, col]), .0022, GOLD, 'CN_Gold', 1.0, cap=None)
    th_end = top['th_neck'] - .02
    _collar(p, dr, th_end, collar_seam(g, dr, [th_end, math.pi / 2, math.pi], [z_sh - .012, m.z(1.49), m.z(1.455)], m.z(1.47)),
            lambda a: np.interp(a, [th_end, math.pi / 2, math.pi], [z_sh + .035, m.z(1.54), m.z(1.52)]), .006, .0045, GOLD_DEEP, 'CN_Cloth', k=1.0,
            knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    # Gold thread worked as a row of small studs down the middle of each front band.
    for side in (-1, 1):
        edge = left_edge if side < 0 else right_edge
        for z in np.linspace(m.z(1.02 if side < 0 else 1.24), z_sh - .02, 9):
            th = float(edge(z)) + (-band / 2 if side < 0 else band / 2)
            e = float(lift(np.array(th), np.array(z), side)) + .0055
            _button(p, dr.at(th, z, extra=e, fold=0.), dr.normal(th, z, e, 0.), .005, GOLD, 'CN_Gold', h=.002, sides=8, cap=None)
    # The under-robe fills the V, so the skin under the robe is covered to its top.
    return p, _form(top, under - .01)


def oilskin(m):
    """Dov Pell: the body of a light-blue oilskin coat: a snapped storm flap continuing the skirt's, a tall
    funnel collar lined in black, a shoulder yoke, and two chest pockets with flaps."""
    g, seed = m.g, 301
    p = Part('oilskin', ('CN_Blue', 'CN_Lacquer', 'CN_Cloth'))
    dr = m.torso(((1.05, .02), (1.12, .017), (1.3, .015), (1.45, .011), (1.5, .005)), taut=True, wrinkle=.0014, seed=seed)
    z_neck, shape = m.z(1.45), 1.6
    top = bodice(p, g, dr, BLUE, 'CN_Blue', thick=.007, z_bot=m.z(1.05), neck_front=z_neck, neck_back=m.z(1.475), neck_shape=shape, k=.95, seed=seed)
    z_sh = top['z_sh']
    z_open = neck_opening(g, dr, z_neck, m.z(1.475), shape)
    # Funnel collar: stands up round the neck, open a little at the throat; its black lining shows at the top.
    th_end = .2
    funnel = m.z((1.53, 1.57, 1.565))
    P, Q = _collar(p, dr, th_end, lambda a: z_open(a) - .006,
                   lambda a: np.maximum(z_open(a) + .03, np.interp(a, [th_end, math.pi / 2, math.pi], funnel)), .008, .006,
                   BLUE, 'CN_Blue', nu=34, nv=6, k=.93, stand=.012)
    _piping(p, _edge_mid(P[0], Q[0]), .0042, CHARCOAL, 'CN_Cloth', .85)
    for s in (-1, 1):
        th = s * (th_end + .04)
        z = float(z_open(th)) + .04
        _button(p, dr.at(th, z, extra=.0145, fold=0.), dr.normal(th, z, .0145, 0.), .006, BLACK, 'CN_Lacquer', h=.0035)
    # Storm flap over the front closure, snapped shut.
    n = 12
    _strip(p, dr, np.full(n, .02), np.linspace(m.z(1.05), z_neck - .004, n), .05, .0075, .004, BLUE, 'CN_Blue', .95, fold=1.0)
    for z in m.z((1.13, 1.22, 1.31, 1.4)):
        _button(p, dr.at(.02, z, extra=.0118), dr.normal(.02, z, .0118), .0065, BLACK, 'CN_Lacquer', h=.004)
    # Yoke across the shoulders and upper back.
    (P, Q), _, _ = _panel(p, dr, math.pi - 1.35, math.pi + 1.35, m.z(1.33), lambda th: z_sh + 0 * th, .0035, .003, BLUE, 'CN_Blue', 11, 4, k=.9)
    _piping(p, _edge_mid(P[-1], Q[-1]), .0018, BLUE, 'CN_Blue', .8)
    for s in (-1, 1):
        a, b = sorted((s * .38, s * .85))
        _patch(p, dr, a, b, m.z(1.16), m.z(1.27), .0035, .0035, BLUE, 'CN_Blue', 6, 5, k=.95, bulge=.005)
        _patch(p, dr, a - .02, b + .02, m.z(1.255), m.z(1.3), .0105, .0045, BLUE, 'CN_Blue', 6, 3, k=.88)
        mid = (a + b) / 2
        _button(p, dr.at(mid, m.z(1.268), extra=.015), dr.normal(mid, m.z(1.268), .015), .0052, BLACK, 'CN_Lacquer', h=.003)
    return p, _form(top, z_neck)


def blouse_bib(m):
    """Rhea Sato: a black work blouse with a small collar, and the bib of her gold apron over it, its straps
    crossed over the back and buttoned at the front."""
    g, seed = m.g, 311
    p = Part('blouse', ('CN_Cloth', 'CN_Gold'))
    dr = m.torso(((1.07, .003), (1.11, .012), (1.3, .010), (1.45, .008), (1.5, .004)), tuck=(1.07, 1.16, .0025), wrinkle=.0009, seed=seed)
    z_neck, shape = m.z(1.44), 1.6
    top = bodice(p, g, dr, CHARCOAL, 'CN_Cloth', thick=.005, z_bot=m.z(1.07), neck_front=z_neck, neck_back=m.z(1.47), neck_shape=shape,
                 k=.95, seed=seed)
    z_sh = top['z_sh']
    z_open = neck_opening(g, dr, z_neck, m.z(1.47), shape)
    _flat_collar(p, dr, z_open, .07, .038, .0058, .004, CHARCOAL, 'CN_Cloth', k=.85)
    # The bib meets the apron's band at the waist and stands off the blouse there.
    z_bridge = m.z(1.13)

    def stand(TH, Z):
        return .0185 * np.clip((z_bridge - Z) / .06, 0, 1) + .0065
    z0, z1 = m.z(1.045), m.z(1.325)
    (P, Q), TH, Z = _panel(p, dr, lambda z: -np.interp(z, [z0, z1], [.62, .5]), lambda z: np.interp(z, [z0, z1], [.62, .5]), z0, z1,
                           stand, .004, GOLD_DEEP, 'CN_Cloth', 9, 9, k=.97, fold=0.)
    _piping(p, _border(P, Q), .0026, GOLD_DEEP, 'CN_Cloth', .88, closed=True)
    _panel(p, dr, -.3, .3, m.z(1.17), m.z(1.25), lambda TH, Z: stand(TH, Z) + .0032, .003, GOLD_DEEP, 'CN_Cloth', 6, 4, k=.92, fold=0.)
    # Straps from the bib's top corners over the shoulders, crossed on the back, down to the apron's band.
    for side in (1, -1):
        oth, oz = top['over'](m.y(.1), 8, side)
        t = np.linspace(0, 1, 4)
        a = (np.interp(t, [0, 1], [side * .5, oth[0]]), np.interp(t, [0, 1], [z1 - .012, z_sh]))
        t = np.linspace(0, 1, 12)
        b = (np.interp(t, [0, 1], [oth[-1], side * (math.pi + .95)]), np.interp(t, [0, 1], [z_sh, m.z(1.075)]))
        th, z = _path(a, (oth, oz), b)
        E = .0072 + .0032 * (side < 0) * (np.arange(len(th)) > len(th) - 13)
        _strip(p, dr, th, z, .03, E, .0035, GOLD_DEEP, 'CN_Cloth', .95, fold=0.)
        q = dr.at(side * .5, z1 - .03, extra=float(stand(0, z1)) + .003)
        _button(p, q, dr.normal(side * .5, z1 - .03, 0.), .0068, GOLD, 'CN_Gold', h=.0035, sides=10, cap=None)
    return p, _form(top, z_neck)


# ---------------------------------------------------------------- ported headwear and what is left of the old hair
# The hair is a groom now, so headwear sits over it: on the skull grown by the groom's depth less people.py's own hair
# shell. Each keeps what MH[key]['costume'] says survives of its old garment.

# Hair a groom lays over the skull where headwear sits (m), from the grooms' looks (S short, M to the jaw); spike S12
# checks Teodor's helmet over his. A groom missing here takes its length class's.
HAIR_DEPTH = {'WI_Hair_S_BuzzCut': .004, 'WI_Hair_S_CoilBuzzCut': .006, 'WI_Hair_S_Clean': .010, 'WI_Hair_S_PulledBack': .010,
              'WI_Hair_S_LowPonytail': .010, 'WI_Hair_S_Updo': .014, 'WI_Hair_S_Messy': .020, 'WI_Hair_M_BobSlick': .014,
              'WI_Hair_M_BobBangs': .022}
HAIR_CLASS = {'S': .012, 'M': .022, 'L': .030}
PEOPLE_HAIR = .0045  # people.py's hats sat over its own hair shell this far off the skull
EAR_OUT, EAR_LOBE, HOOP = .012, .025, .012  # an earlobe's outside past the ear joint, its pierce under it, a hoop's radius


def hair_depth(grooms):
    """How far the person's Hair groom stands off the skull (0 without one)."""
    hair = grooms.get('Hair')
    if not hair:
        return 0.0
    name = hair[0].rsplit('/', 1)[-1]
    return HAIR_DEPTH.get(name, HAIR_CLASS.get(name.split('_')[2] if name.count('_') >= 2 else 'M', HAIR_CLASS['M']))


def straw_hat(m, grow):
    """Orsolya Fenn: a wide-brimmed straw hat with a black ribbon (people.straw_hat; the plait is her Hair groom)."""
    p = Part('hat', ('CN_Cloth',))
    head = m.skull(grow)
    band_z = m.hz(1.748, grow)
    _hat(p, head, GOLD_STRAW, 'CN_Cloth', band_z, .235 * m.kh, .085 * m.kh, .03 * m.kh, tilt=-3, thick=.005, braid=.0024,
         crown_round=.45, seed=441)
    _band_ring(p, head, band_z + .002, band_z + .024, .0115, CHARCOAL, 'CN_Cloth', k=.9, scale=.99)
    return p, dict(kind='head')


def cap(m, grow):
    """Marek Duran: a red wool flat cap with a short stiff peak and a covered button (people.cap_red; the hair is his
    groom)."""
    p = Part('cap', ('CN_Cloth',))
    head = m.skull(grow)
    (cx, cy, cz), fr, bk, hw, up = head
    band = _lobes(((0, m.hz(1.742, grow)), (1.6, m.hz(1.733, grow)), (math.pi, m.hz(1.722, grow))))
    lift = lambda phi, psi: .0105 + .021 * np.clip(np.cos(phi), 0, 1) ** 1.4 * np.clip(np.sin(psi), 0, 1) ** 2.5
    _scalp(p, head, RED, 'CN_Cloth', band, lift, thick=.006, nu=48, nv=12, strands=8, strand=.0012, seed=451, k=.95)
    _band_ring(p, head, m.hz(1.72, grow), m.hz(1.742, grow), .0125, RED, 'CN_Cloth', k=.82)
    _peak(p, head, m.hz(1.738, grow), .055 * m.kh, .012, 1.05, .006, RED, 'CN_Cloth', k=.85)
    _shell(p, (cx + .012, cy, cz + up + .022), (.008, .008, .004), RED, 'CN_Cloth', .9, 8, 4)
    return p, dict(kind='head')


def headscarf(m, grow):
    """Sefa Moreno: a red headscarf knotted at the nape with its two ends hanging, and gold hoop earrings
    (people.headscarf_red; the line of hair under its front edge is her groom)."""
    p = Part('headscarf', ('CN_Cloth', 'CN_Gold'))
    head = m.skull(grow)
    (cx, cy, cz), fr, bk, hw, up = head
    hz = lambda z: m.hz(z, grow)
    bottom = _lobes(((0, hz(1.768)), (.9, hz(1.738)), (1.35, hz(1.692)), (1.8, hz(1.645)), (2.6, hz(1.622)), (math.pi, hz(1.618))))
    lift = lambda phi, psi: .0085 + .004 * np.sin(np.clip(psi, 0, None)) + .002 * noise2(np.cos(phi) * 3, psi * 4, 461)
    _scalp(p, head, RED, 'CN_Cloth', bottom, lift, thick=.006, nu=52, nv=14, strands=14, strand=.0022, ends=.003, seed=461, k=.95)
    knot = np.array([cx - bk - .02, cy, hz(1.632)])
    _shell(p, knot, (.018, .026, .02), RED, 'CN_Cloth', .88, 10, 6)
    for s, L in ((-1, .1), (1, .085)):
        n = 6
        d = np.linspace(0, 1, n)
        C = np.stack([knot[0] - .004 - .012 * d, knot[1] + s * (.012 + .018 * d), knot[2] - .012 - L * d], -1)
        _ribbon3d(p, C, (0, 1, 0), (-1, 0, .1), np.linspace(.04, .03, n), .004, RED, 'CN_Cloth', .9, cols=3)
    ex, ey, ez = m.g.face['ear']
    for s in (-1, 1):
        lobe = np.array([ex, s * (ey + EAR_OUT), ez - EAR_LOBE * m.g.scale])
        _torus(p, lobe - (0, 0, HOOP), HOOP, .0017, _tone(GOLD, 1.0, None), 'CN_Gold', 16, 5, axis='y')
    return p, dict(kind='head')


def helmet(m, grow):
    """Teodor Vass: a white lacquered helmet over padding, a gold ridge and a red brush crest, a black peak,
    cheek guards hinged on gold rivets and a black chin strap (people.helmet)."""
    seed = 471
    p = Part('helmet', ('CN_Lacquer', 'CN_Gold', 'CN_Cloth', 'CN_Black'))
    head = m.skull(grow)
    (cx, cy, cz), fr, bk, hw, up = head
    hz = lambda z: m.hz(z, grow)
    bottom = _lobes(((0, hz(1.748)), (.8, hz(1.735)), (1.3, hz(1.69)), (1.8, hz(1.655)), (2.6, hz(1.632)), (math.pi, hz(1.628))))
    lift = lambda phi, psi: .021 + .004 * np.sin(np.clip(psi, 0, None))
    _scalp(p, head, WHITE_PURE, 'CN_Lacquer', bottom, lift, thick=.006, nu=48, nv=14, flare=.32, seed=seed, k=.95, psi_top=1.4)
    # A rolled rim round the helmet's edge.
    _scalp(p, head, WHITE_PURE, 'CN_Lacquer', lambda phi: bottom(phi) + .012, lambda phi, psi: lift(phi, psi) + .0035, thick=.004, nu=48,
           nv=3, flare=.32, seed=seed, k=.85, psi_top=math.asin(max(-.99, min(.99, (hz(1.7) - cz) / up))), close_top=False)
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
    _peak(p, head, hz(1.752), .04 * m.kh, .01, 1.0, .005, BLACK, 'CN_Lacquer', k=1.0)
    # Cheek guards hang from hinges under the helmet's edge and cover the cheeks to the jaw, front edges turned in.
    sw = m.src_skull[3]
    for s in (-1, 1):
        R = _basis((.22, s, 0), (0, 0, 1))
        _plate(p, m.head((.036, s * (sw + .021), 1.632), grow), R, .085 * m.kh, .11 * m.kh, .008, .005, WHITE_PURE, 'CN_Lacquer', k=.92,
               nu=5, nv=6, trim=GOLD, trim_r=.0026, round_=.5)
        for dx in (-.018, .018):
            _button(p, m.head((.036 + dx, s * (sw + .03), 1.678), grow), (0, s, 0), .0038, GOLD, 'CN_Gold', h=.0024, sides=8, cap=None)
        _limb(p, m.head(((.056, s * (sw + .012), 1.585), (.066, s * .058, 1.556), (.075, s * .03, 1.537)), grow), .0042, BLACK, 'CN_Black', 6, .9)
    _limb(p, m.head(((.075, -.03, 1.537), (.079, 0, 1.534), (.075, .03, 1.537)), grow), .0042, BLACK, 'CN_Black', 6, .9)
    return p, dict(kind='head')


def field_hat(m, grow):
    """Rhea Sato: a white cotton field hat with a turned-down brim, a gold band and a neck curtain against the sun,
    tied under the chin with a black cord (people.field_hat; the hair under it is her groom)."""
    seed = 511
    p = Part('hat', ('CN_Cloth', 'CN_Gold'))
    head = m.skull(grow)
    (cx, cy, cz), fr, bk, hw, up = head
    band_z = m.hz(1.742, grow)
    _hat(p, head, WHITE, 'CN_Cloth', band_z, .155 * m.kh, .072 * m.kh, .042 * m.kh, thick=.004, crown_round=.6, crease=.007, seed=seed, k=.95)
    _band_ring(p, head, band_z + .002, band_z + .018, .0115, GOLD_DEEP, 'CN_Cloth', k=1.0)
    for s in (-1, 1):
        for dx in (-.018, .018):
            q = _skull(head, s * math.pi / 2 + dx * 4, math.asin(min(.99, (band_z + .045 * m.kh - cz) / up)), .012)
            _torus(p, q, .0042, .0013, _tone(GOLD, 1.0, None), 'CN_Gold', 10, 4, axis='y')
    # The neck curtain hangs from inside the brim at the back and sides, standing off the neck, down to where it did on
    # the Mannequin.
    psi = math.asin((band_z - .004 - cz) / up)
    phi = np.linspace(math.pi - 1.75, math.pi + 1.75, 26)
    v = np.linspace(0, 1, 7)[:, None]
    top_pts = _skull(head, phi, np.full(len(phi), psi), .014)
    radial = np.stack([np.cos(phi), np.sin(phi), np.zeros(len(phi))], -1)
    a = np.abs(np.angle(np.exp(1j * (phi - math.pi))))
    drop = (band_z - m.z(1.742 - .205)) / .205
    length = np.interp(a, [0, 1.2, 1.75], [.205, .175, .12]) * drop
    hang = top_pts[None] + radial[None] * (.03 * v[..., None] ** 1.2) - np.array([0, 0, 1.]) * (length[None, :, None] * v[..., None])
    hang += radial[None] * (.003 * np.sin(phi * 9 + seed)[None, :, None] * v[..., None])
    _sheet(p, hang, .003, WHITE, 'CN_Cloth', _away((cx, cy, m.hz(1.62, grow))), k=.95 - .1 * v + 0 * a[None, :])
    # Chin cord from the band's sides under the chin.
    for s in (-1, 1):
        cord = np.concatenate([[(cx, s * (hw + .012), band_z - .01)],
                               m.head(((.03, s * .074, 1.63), (.055, s * .052, 1.565), (.062, s * .02, 1.54)))])
        _limb(p, cord, .0016, BLACK, 'CN_Cloth', 4, 1.0)
    _limb(p, m.head(((.062, -.02, 1.54), (.064, 0, 1.538), (.062, .02, 1.54))), .0016, BLACK, 'CN_Cloth', 4, 1.0)
    return p, dict(kind='head')


def knit_cap(m, grow):
    """Dov Pell: a black knitted watch cap with a turned-up cuff sitting above the ears (people.knit_cap_beard; the hair
    and the beard are his grooms)."""
    p = Part('cap', ('CN_Cloth',))
    head = m.skull(grow)
    band = _lobes(((0, m.hz(1.738, grow)), (1.6, m.hz(1.725, grow)), (math.pi, m.hz(1.712, grow))))
    lift = lambda phi, psi: .0095 + .006 * np.clip(np.sin(psi), 0, 1) ** 3
    _scalp(p, head, CHARCOAL, 'CN_Cloth', band, lift, thick=.006, nu=60, nv=12, strands=60, strand=.0016, seed=501, k=.92)
    _band_ring(p, head, m.hz(1.712, grow), m.hz(1.75, grow), .0185, CHARCOAL, 'CN_Cloth', k=.8, nu=60, thick=.006)
    return p, dict(kind='head')


def _hood_lift(phi, psi):
    """How far the Listener's hood stands off the skull (people.hood_halo's), deeper over the crown and at the back."""
    return .032 + .012 * np.sin(np.clip(psi, 0, None)) + .006 * np.clip(-np.cos(phi), 0, 1)


def hood(m, grow):
    """The Listener: a deep white hood falling onto the shoulders with a gold edge round the face (people.hood_halo),
    lined in light blue so the face under it reads under the Spine's light (PEOPLE_DESIGN.md 2)."""
    p = Part('hood', ('CN_Cloth', 'CN_Gold'))
    head = m.skull(grow)
    hz = lambda z: m.hz(z, grow)
    bottom = _lobes(((0, hz(1.792)), (.55, hz(1.745)), (.95, hz(1.62)), (1.25, hz(1.545)), (1.6, hz(1.51)), (2.3, hz(1.475)), (math.pi, hz(1.465))))
    first = len(p.v)
    (P, Q), phi, PS = _scalp(p, head, WHITE_PURE, 'CN_Cloth', bottom, _hood_lift, thick=.007, nu=52, nv=16, flare=.22, inward=0.,
                             strands=10, strand=.003, seed=491, k=.95)
    # people._sheet lays the outer face's vertices, then the inner face's: the inner face is the lining.
    inner = slice(first + P.shape[0] * P.shape[1], first + 2 * P.shape[0] * P.shape[1])
    p.c[inner] = _tone(BLUE_PALE, np.linspace(.86, .95, inner.stop - inner.start)).tolist()
    face = np.abs(np.angle(np.exp(1j * phi))) < 1.45
    edge = _edge_mid(P[-1, face], Q[-1, face])
    order = np.argsort(np.angle(np.exp(1j * phi[face])))
    _piping(p, edge[order], .0042, GOLD, 'CN_Gold', 1.0, cap=None)
    return p, dict(kind='hood', bottom=float(np.min(P[..., 2])))


# The listening ring's lights glow at half strength (PEOPLE_DESIGN.md 2: CN_Glow at 0.5), where allowed() still calls
# them light blue. A constant of its own, so retuning the figures' glows in people.py leaves the Listener as designed.
RING_LIGHT_TONE = .5


def ring(m, grow):
    """The Listener: the gold listening ring behind the hood, set with light-blue lights, on a bracket from the hood's
    back (people.hood_halo's ring; its lights at RING_LIGHT_TONE)."""
    p = Part('ring', ('CN_Gold', 'CN_Glow'))
    head = m.skull(grow)
    (sx, _, _), _, sb, _, _ = m.src_skull
    ring_c = m.head((sx - sb - .095, 0., 1.73), grow)
    big = .175 * m.kh
    _torus(p, ring_c, big, .0065, _tone(GOLD, 1.0, None), 'CN_Gold', 48, 6, axis='x')
    _torus(p, ring_c + (-.004, 0, 0), .158 * m.kh, .0028, _tone(GOLD_PALE, .95, None), 'CN_Gold', 48, 5, axis='x')
    for i in range(8):
        a = (i + .5) * 2 * math.pi / 8
        _shell(p, ring_c + (.004, big * math.cos(a), big * math.sin(a)), (.011, .011, .011), LIGHT_BLUE, 'CN_Glow', RING_LIGHT_TONE, 10, 6, cap=None)
    back = _skull(head, math.pi, -.25, _hood_lift(math.pi, -.25) + .004)
    _limb(p, [back, back + (-.03, 0, -.03), ring_c + (.0, 0, -big)], [.006, .006, .006], GOLD, 'CN_Gold', 6, 1.0, None)
    return p, dict(kind='head')


def spectacles(m, grow):
    """Petra Lune: wire spectacles with light-blue lenses (people.bun_black's; the hair and the bun are her groom), on
    the eyes, the nose bridge and the ears of the face guide."""
    p = Part('spectacles', ('CN_Gold', 'CN_Glass'))
    (ex, ey, ez), (ax, ay, az), (bx, bz) = m.g.face['eye'], m.g.face['ear'], m.g.face['bridge']
    k = ey / STANDIN_FACE['eye'][1]   # the Mannequin's lenses for its eyes, as wide apart as the person's
    lens_x = max(ex + .022, bx + .005)
    for s in (-1, 1):
        ctr = np.array([lens_x, s * ey, ez])
        _torus(p, ctr, .0175 * k, .0013, _tone(GOLD, 1.0, None), 'CN_Gold', 18, 5, axis='x')
        ang = np.linspace(0, 2 * math.pi, 16, endpoint=False)
        lens = np.stack([np.full(16, ctr[0] - .0005), ctr[1] + .0168 * k * np.cos(ang), ctr[2] + .0168 * k * np.sin(ang)], -1)
        p.add(lens, [list(range(16))[::-1] if np.dot(np.cross(lens[1] - lens[0], lens[2] - lens[0]), (1, 0, 0)) < 0 else list(range(16))],
              BLUE_PALE, 'CN_Glass', False)
        # The arm runs back from the rim past the temple, over the ear and down behind it, into the hair.
        side = ay + EAR_OUT + grow
        _limb(p, [ctr + (-.002, s * .018 * k, .004), (ax + .076, s * side, ez + .006), (ax - .004, s * (side + .003), az + .017),
                  (ax - .024, s * (side + .001), az - .003)], .0012, GOLD, 'CN_Gold', 4, 1.0, None)
    _limb(p, [(lens_x + .001, -.014 * k, ez + .004), (lens_x + .004, 0, ez + .007), (lens_x + .001, .014 * k, ez + .004)], .0013,
          GOLD, 'CN_Gold', 4, 1.0, None)
    return p, dict(kind='head')


def pins(m, grow):
    """Old Wen: two gold pins crossed through her bun (people.bun_white's; the hair is her groom), where the bun was on
    the Mannequin, over the groom's depth."""
    p = Part('pins', ('CN_Gold',))
    (sx, sy, sz), _, _, _, su = m.src_skull
    c = m.head((sx - .03, sy, sz + su + .004), grow)
    for s in (-1, 1):
        a = c + (.035, s * .05, .03)
        b = c + (-.03, -s * .045, .0)
        _limb(p, [a, b], [.0024, .0024], GOLD, 'CN_Gold', 5, 1.0, None)
        _shell(p, a, (.0045, .0045, .0045), GOLD, 'CN_Gold', 1.0, 8, 4, cap=None)
    return p, dict(kind='head')


def clip(m, grow):
    """Tamsin: a red clip on the right of her hair (people.short_hair's; the hair is her groom)."""
    p = Part('clip', ('CN_Lacquer',))
    head = m.skull(grow)
    q = _skull(head, .95, .62, .005)
    R = _basis(q - np.array(head[0]))
    _box(p, q, (.003, .006, .02), RED, 'CN_Lacquer', .002, 1.0, R @ _rot((1, 0, 0), 35))
    return p, dict(kind='head')


def band(m, grow):
    """Doctor Ama Okafor: a thin gold band across the crown from ear to ear (people.bob_black's), on the bob's surface."""
    p = Part('band', ('CN_Gold',))
    (cx, cy, cz), fr, bk, hw, up = m.skull(grow)
    a = math.pi / 2 - np.linspace(.32, math.pi - .32, 15)   # from the crown, positive toward the right ear
    pts = np.array([cx, cy, cz]) + np.stack([np.full(15, .012), (hw + .004) * np.sin(a), (up + .004) * np.cos(a)], -1)
    _limb(p, pts, .0026, GOLD, 'CN_Gold', 6, 1.0, None)
    return p, dict(kind='head')


# ---------------------------------------------------------------- fitted shells over the body guide

MARGIN = .03      # m: skin stays drawn this far inside a hem, a cuff or a neckline, so moving cloth never shows a hole
SOLE_TOP = .006   # m: a shoe's or a boot's upper starts here; the sole holds the foot's underside
SOLE = (-.004, .009, .016, .004)  # a sole's bottom (sunk a little: the feet stand on the floor), top, top at the heel, lip
RELAX = 3         # smoothing passes over a shell's lifted surface (it should read as cloth over the body, not skin)


def _vertex_normals(points, tris):
    fn = np.cross(points[tris[:, 1]] - points[tris[:, 0]], points[tris[:, 2]] - points[tris[:, 0]])
    n = np.zeros_like(points)
    for i in range(3):
        np.add.at(n, tris[:, i], fn)
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)


def _clip(points, tris, attr, d):
    """The part of a triangle mesh where d >= 0 (d per vertex, linear across faces), cut cleanly along d = 0. attr
    (per-vertex values) is carried and interpolated onto the cut's new vertices."""
    inside = d >= 0
    pts, att, made = list(points), list(attr), {}

    def cross(i, j):
        key = (min(i, j), max(i, j))
        if key not in made:
            t = d[i] / (d[i] - d[j])
            if t < 1e-6 or t > 1 - 1e-6:   # on the plane already: no sliver
                made[key] = i if t < .5 else j
            else:
                made[key] = len(pts)
                pts.append(points[i] + t * (points[j] - points[i]))
                att.append(attr[i] + t * (attr[j] - attr[i]))
        return made[key]
    out = []
    for tri in tris:
        flags = inside[tri]
        count = int(flags.sum())
        if count == 3:
            out.append(tuple(tri))
        elif count:
            k = int(np.argmax(flags if count == 1 else ~flags))   # the odd corner first, keeping the winding
            a, b, c = tri[k], tri[(k + 1) % 3], tri[(k + 2) % 3]
            if count == 1:
                out.append((a, cross(a, b), cross(a, c)))
            else:
                ab, ca = cross(a, b), cross(c, a)
                out += [(ab, b, c), (ab, c, ca)]
    out = np.array([t for t in out if len(set(t)) == 3], np.int64).reshape(-1, 3)
    used, inverse = np.unique(out, return_inverse=True)
    return np.asarray(pts)[used], inverse.reshape(-1, 3), np.asarray(att)[used]


def _boundary(tris):
    """The open edges (used by one face), in their faces' winding."""
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    key = np.sort(e, axis=1)
    _, inverse, count = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    return e[count[inverse.ravel()] == 1]


def _loops(edges):
    """Open edges chained into closed loops of vertex indices."""
    nxt = {int(a): int(b) for a, b in edges}
    loops, seen = [], set()
    for start in nxt:
        if start in seen:
            continue
        loop, v = [], start
        while v not in seen and v in nxt:
            seen.add(v)
            loop.append(v)
            v = nxt[v]
        if len(loop) >= 3:
            loops.append(np.array(loop))
    return loops


def _relax(points, tris, fixed, passes):
    """Uniform Laplacian smoothing, the fixed vertices held."""
    n = len(points)
    nb = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]], tris[:, [1, 0]], tris[:, [2, 1]], tris[:, [0, 2]]])
    for _ in range(passes):
        acc = np.zeros_like(points)
        cnt = np.zeros(n)
        np.add.at(acc, nb[:, 0], points[nb[:, 1]])
        np.add.at(cnt, nb[:, 0], 1)
        moved = points + .5 * (acc / np.maximum(cnt, 1)[:, None] - points)
        points = np.where(fixed[:, None], points, moved)
    return points


def shell(part, g, labels, planes, offset, thick, base, slot, k=1.0, lining=None, relax=RELAX, opening=None):
    """A layer fitted over the body guide's own surface: the triangles of the body whose corners are all on the core
    bones labels (or all in labels, a mask over the guide's surface vertices), cut by planes ((origin, normal): what lies
    on the normal's side is kept), lifted off the skin by offset(points) (m, per vertex) along the skin's normals and
    relaxed, then solid: the outer face, a lining thick inside it (lining's colour, else the cloth's darkened) and rims
    along its open edges. k shades the cloth (a number, or a function of the skin points). Returns the outer face's open
    loops (point arrays) and the surface vertices it hides (those it covers more than MARGIN inside its edges).
    opening(points) says which of the open edges' skin points are an opening skin shows through (a cuff, a hem); the
    rest lie under another piece (a sleeve's head under the top's strap), so skin is hidden right up to them. Every
    open edge is an opening when it is None."""
    P, T, L = g.surface['points'], g.surface['tris'], g.surface['labels']
    mask = isinstance(labels, np.ndarray) and labels.dtype == bool
    region = labels if mask else _labelled(L, labels)
    tris = T[region[T].all(1)]
    if not len(tris):
        raise ValueError('the body guide has no triangles on %s' % ('its region' if mask else ', '.join(labels)))
    used, inverse = np.unique(tris, return_inverse=True)
    pts, tris = P[used], inverse.reshape(-1, 3)
    attr = np.column_stack([g.normals[used], used.astype(np.float64), np.ones(len(used))])
    for origin, normal in planes:
        pts, tris, attr = _clip(pts, tris, attr, (pts - np.asarray(origin, np.float64)) @ np.asarray(normal, np.float64))
        if not len(tris):
            raise ValueError('a cut left nothing of a shell')
    normals = attr[:, :3] / (np.linalg.norm(attr[:, :3], axis=1, keepdims=True) + 1e-12)
    lift = np.asarray(offset(pts), np.float64) * np.ones(len(pts))
    open_edges = _boundary(tris)
    fixed = np.zeros(len(pts), bool)
    fixed[open_edges.ravel()] = True
    outer = _relax(pts + normals * lift[:, None], tris, fixed, relax)
    # Relaxing pulls a convex layer in toward the skin: never closer than half its lift.
    gap = np.einsum('ij,ij->i', outer - pts, normals)
    outer = outer + normals * np.maximum(0., .5 * lift - gap)[:, None]
    inner = outer - _vertex_normals(outer, tris) * thick
    shade = np.broadcast_to(np.asarray(k(pts) if callable(k) else k, np.float64), (len(pts),))
    first = part.add(outer, tris.tolist(), _tone(base, shade), slot, True)
    lining_rgba = _tone(lining, shade * .95) if lining is not None else _tone(base, shade * .6)
    second = part.add(inner, tris[:, ::-1].tolist(), lining_rgba, slot, True)
    rims = [(first + b, first + a, second + a, second + b) for a, b in open_edges]
    if rims:
        part.f.extend([list(r) for r in rims])
        part.m.extend([part.slots.index(slot)] * len(rims))
        part.s.extend([False] * len(rims))
    loops = [outer[loop] for loop in _loops(open_edges)]
    original = attr[:, 4] > 1 - 1e-9
    ids = np.round(attr[original, 3]).astype(np.int64)
    edge_pts = pts[np.unique(open_edges.ravel())]
    if opening is not None and len(edge_pts):
        edge_pts = edge_pts[np.asarray(opening(edge_pts), bool)]
    if len(edge_pts):
        near = np.zeros(len(ids), bool)
        for i in range(0, len(edge_pts), 256):
            block = edge_pts[i:i + 256]
            near |= (np.linalg.norm(pts[original][:, None, :] - block[None, :, :], axis=2) < MARGIN).any(1)
        ids = ids[~near]
    return loops, ids


def _along(g, limb, points):
    """Arc length along a limb's joints of the nearest point of its bones to each point."""
    joints = g.limbs[limb][0]
    seg = np.diff(joints, axis=0)
    length = np.linalg.norm(seg, axis=1)
    best_d, best_s = None, None
    start = 0.
    for a, v, l in zip(joints[:-1], seg, length):
        t = np.clip(((points - a) @ v) / (l * l), 0, 1)
        q = a + t[:, None] * v
        d = np.linalg.norm(points - q, axis=1)
        s = start + t * l
        if best_d is None:
            best_d, best_s = d, s
        else:
            closer = d < best_d
            best_d, best_s = np.where(closer, d, best_d), np.where(closer, s, best_s)
        start += l
    return best_s


def _station(g, limb, s):
    """The plane across a limb at arc length s, kept toward its root: (origin, normal)."""
    o, d = g.along(limb, s)
    return o, -d


def _roll(part, loop, centre, axis, radius, base, slot, k=1.0):
    """A rolled edge round an open loop of a sleeve or a boot top: a soft tube laid just outside it, away from the limb's
    axis (through centre along axis)."""
    loop = np.asarray(loop, np.float64)
    axis = np.asarray(axis, np.float64) / np.linalg.norm(axis)
    out = loop - centre
    out -= np.outer(out @ axis, axis)
    out /= np.linalg.norm(out, axis=1, keepdims=True) + 1e-12
    path = loop + out * radius * .8
    _limb(part, np.concatenate([path, path[:1]]), radius, base, slot, 8, k)


def _sole(part, g, side, base, slot, k=1.0):
    """A sole under one foot: the foot's outline at the floor, a lip wider, from just under the floor up past the foot's
    underside, rising toward the heel."""
    bottom, top, heel_top, lip = SOLE
    heel, toe, outline = g.feet[side]
    centre = outline.mean(0)
    ring = outline + (outline - centre) / (np.linalg.norm(outline - centre, axis=1, keepdims=True) + 1e-12) * lip
    rise = heel_top - top
    z_top = top + rise * np.clip((heel + .3 * (toe - heel) - ring[:, 0]) / (.3 * (toe - heel)), 0, 1)
    n = len(ring)
    pts = np.concatenate([np.column_stack([ring, np.full(n, bottom)]), np.column_stack([ring, z_top]),
                          [(centre[0], centre[1], bottom), (centre[0], centre[1], float(z_top.mean()))]])
    faces = [[j, (j + 1) % n, n + (j + 1) % n, n + j] for j in range(n)]
    faces += [[2 * n, (j + 1) % n, j] for j in range(n)] + [[2 * n + 1, n + j, n + (j + 1) % n] for j in range(n)]
    part.add(pts, faces, _tone(base, k), slot, False)
    return heel, toe


# ---------------------------------------------------------------- new pieces: what the Mannequin's bare limbs stood for

# How far a sleeve stands off the arm, by the top it is set in (coats and the gambeson are loose, blouses fitted).
SLEEVE_EASE = {'coat_black': .022, 'coat_white': .020, 'oilskin': .024, 'armour_vest': .020, 'robe_shawl': .016, 'robe_tall': .015,
               'work_apron': .013, 'blouse': .012, 'blouse_strap': .011, 'blouse_shawl': .012, 'blouse_bib': .012, 'tunic': .011}
SLEEVE_THICK = .004
SLEEVE_ROOT = .005   # m: how close a sleeve's head sits over the shoulder, under the top's strap and armhole
SLEEVE_HEAD = .08    # m along the arm (x scale) over which a sleeve loosens from its head to its ease
CUFF_REACH = .04     # m along the arm from a sleeve's cut within which its open edge is the cuff (the rest is its head)
# Where each cut ends, as a fraction of the forearm past the elbow (negative: of the upper arm, from the shoulder), and the
# flare it gains toward that end (m) from the fraction of the arm where it starts (bell and wide sleeves hang open).
SLEEVE_CUTS = {'wrist': (1.0, 0., 0.), 'three_quarter': (.55, 0., 0.), 'forearm_rolled': (.45, 0., 0.), 'elbow_rolled': (.08, 0., 0.),
               'short': (-.5, 0., 0.), 'bell': (1.0, .075, .45), 'wide': (1.0, .055, .3)}
ROLLED = ('elbow_rolled', 'forearm_rolled')
TROUSERS_LIFT = .015  # m: trousers stand at most this far off the legs (loose below the knee); boots clear them
TUCK = .05            # m trousers reach down inside a boot's shaft
CUFF = .055   # m: a long sleeve's cuff, set a little proud of the sleeve
QUILT = (.042, .0028)  # people.armour_vest's quilting: channel pitch and depth, carried down the gambeson's sleeves
FOREARM_FLAT = .012    # m a forearm's widest reaches past its mean radius (8 mm on Physis's guide), and a plate's gap


def _cut_s(g, limb, fraction):
    """Arc length along an arm where a sleeve cut at fraction ends."""
    elbow = float(np.linalg.norm(g.limbs[limb][0][1] - g.limbs[limb][0][0]))
    if fraction < 0:
        return -fraction * elbow
    return elbow + fraction * (g.length(limb) - elbow)


def sleeves(g, spec, ctx):
    """Sleeves for the top they are set in (ctx['upper']): shells over the arms and the shoulders' edges, from under the
    top's straps (where |y| passes between the straps' edges) to the cut; rolled cuts end in a roll, long ones in a cuff
    (Dov's black, Kairos's with gold buttons), bell and wide ones flare and hang, lined (the Listener's in BLUE_PALE);
    the gambeson's are quilted."""
    colours = [PALETTE[c] for c in spec['colours']]
    slot = spec.get('slot', 'CN_Cloth')
    p = Part(spec['piece'], (slot,) + tuple(s for s in ('CN_Cloth', 'CN_Gold') if s != slot))
    upper = ctx['upper']
    ease = SLEEVE_EASE[upper]
    end, flare, flare_from = SLEEVE_CUTS[spec['cut']]
    y_cut = (g.strap[0] + g.strap[1]) / 2
    covered, ends = [], {}
    for side in SIDES:
        limb = 'arm_' + side
        sign = SIDE_SIGN[side]
        s_end = _cut_s(g, limb, end)
        s_from = flare_from * g.length(limb)
        ends[side] = s_end

        def lift(pts, limb=limb):
            s = _along(g, limb, pts)
            # A sleeve's head fits the shoulder: tight at the root, its ease by the time it leaves the trunk.
            out = SLEEVE_ROOT + (ease - SLEEVE_ROOT) * _smooth(s / (SLEEVE_HEAD * g.scale)) + .0015 * noise2(s * 18., pts[:, 2] * 9., 7)
            if flare:
                t = _smooth((s - s_from) / max(s_end - s_from, 1e-6)) ** 1.5
                below = np.clip((g.axis(limb, s)[:, 2] - pts[:, 2]) / g.radius(limb, 0.), 0, 1)   # its underside hangs lower
                out = out + flare * t * (1 + .6 * below)
            if upper == 'armour_vest':
                out = out + QUILT[1] * (np.abs(np.sin(math.pi * s / QUILT[0])) ** .6 - .5)
            return out

        def shade(pts, limb=limb):
            s = _along(g, limb, pts)
            return .93 + .07 * noise2(s * 11., pts[:, 2] * 5., 3)
        planes = [((0, sign * y_cut, 0), (0, sign, 0)), _station(g, limb, s_end)]
        lining = colours[1] if spec['cut'] == 'bell' and len(colours) > 1 else None
        # The arm, the shoulder's edge and the side of the trunk round the arm's root, which the top's armhole leaves open.
        L, P = g.surface['labels'], g.surface['points']
        root = _labelled(L, TRUNK) & (np.linalg.norm(P - g.limbs[limb][0][0], axis=1) < SLEEVE_HEAD * 1.4 * g.scale)
        region = _labelled(L, ('clavicle_' + side, 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side)) | root
        # Only the cut is an opening: the head's edges lie under the top's strap and armhole, so the skin of the shoulder
        # is hidden right up to them (kept drawn there, it came through the tight head when the arms hang).
        def cuff_end(pts, limb=limb, s_end=s_end):
            return np.abs(_along(g, limb, pts) - s_end) < CUFF_REACH
        loops, ids = shell(p, g, region, planes, lift, SLEEVE_THICK, colours[0], slot, k=shade, lining=lining,
                           opening=cuff_end)
        if flare:   # the arm shows down an open sleeve's end, so only the skin above the flare is hidden
            ids = ids[_along(g, limb, g.surface['points'][ids]) < s_from - MARGIN]
        covered.append(ids)
        cuff_loop = min(loops, key=lambda l: np.linalg.norm(l.mean(0) - g.along(limb, s_end)[0]))
        centre = g.along(limb, s_end)[0]
        if spec['cut'] in ROLLED:
            r, d = .009, g.along(limb, s_end)[1]
            _roll(p, cuff_loop, centre, d, r, colours[0], slot, .9)
            _roll(p, cuff_loop - d * .018, centre - d * .018, d, r * .8, colours[0], slot, .85)
        elif spec['cut'] == 'wrist':
            cuff_colour = colours[1] if len(colours) > 1 and spec['colours'][1] != 'GOLD' else colours[0]
            cuff_slot = 'CN_Cloth' if cuff_colour is not colours[0] else slot
            planes = [_station(g, limb, s_end), g.along(limb, s_end - CUFF)]
            shell(p, g, ('lowerarm_' + side, 'hand_' + side), planes, lambda pts: ease + .0025, SLEEVE_THICK, cuff_colour, cuff_slot,
                  k=.97 if cuff_colour is colours[0] else .9)
            if 'GOLD' in spec['colours'] or 'button' in spec.get('note', ''):
                o, d = g.along(limb, s_end - CUFF / 2)
                side_dir = np.array([0., sign, 0.])
                side_dir -= d * (side_dir @ d)
                side_dir /= np.linalg.norm(side_dir)
                r = g.radius(limb, s_end - CUFF / 2) + ease + SLEEVE_THICK + .0025
                gold = 'GOLD' in spec['colours']
                for t in (-.012, .012):
                    _button(p, o + side_dir * r + d * t, side_dir, .0045, GOLD if gold else colours[0], 'CN_Gold' if gold else slot,
                            h=.0025, sides=8, k=1.0 if gold else .9, cap=None if gold else .9)
    return p, dict(kind='sleeves', covered=np.concatenate(covered), ends=ends, ease=ease)


def collar_cuffs(g, spec, ctx):
    """Kairos: the white shirt under his coat: its front in the coat's V, a stand collar over the coat's collar, and
    cuffs showing past the coat's sleeves."""
    m, colour = ctx['port'], PALETTE[spec['colours'][0]]
    p = Part(spec['piece'], ('CN_Cloth',))
    dr = m.torso(.003, wrinkle=.0005, seed=331)
    neck = g.levels['neck']
    z_open = neck_opening(g, dr, neck + .012, neck + .03, 2.2)
    z_break = ctx['form']['open']
    _panel(p, dr, -.5, .5, z_break - .04, lambda th: z_open(th) - .002, .0, .004, colour, 'CN_Cloth', 9, 8, k=.97, fold=0.)
    _collar(p, dr, .12, lambda a: z_open(a) - .006, lambda a: z_open(a) + .036, .005, .004, colour, 'CN_Cloth', k=.95, stand=.003)
    for z in np.linspace(z_break - .01, neck - .01, 3):
        _button(p, dr.at(0., z, extra=.005), dr.normal(0., z, .005), .0035, colour, 'CN_Cloth', h=.002, sides=8, k=.9)
    sleeve = ctx['sleeves']
    for side in SIDES:
        limb = 'arm_' + side
        s_end = sleeve['ends'][side]
        planes = [_station(g, limb, s_end + .014), g.along(limb, s_end - .03)]
        shell(p, g, ('lowerarm_' + side, 'hand_' + side), planes, lambda pts: .008, .003, colour, 'CN_Cloth', k=.98)
    return p, dict(kind='collar')


def undertop(g, spec, ctx):
    """Doctor Ama Okafor: a light-blue top under her coat, its crew neck filling the coat's V."""
    m, colour = ctx['port'], PALETTE[spec['colours'][0]]
    p = Part(spec['piece'], ('CN_Cloth',))
    dr = m.torso(.005, wrinkle=.0006, seed=341)
    neck = g.levels['neck']
    top = bodice(p, g, dr, colour, 'CN_Cloth', thick=.004, z_bot=g.levels['waist'] - .06 * g.scale, neck_front=neck + .008, neck_back=neck + .025,
                 neck_shape=2.2, k=.95, seed=341)
    _piping(p, _neck_loop(top, top['ms']), .0026, colour, 'CN_Cloth', .9, closed=True)
    return p, _form(top, neck + .008)


def trousers(g, spec, ctx):
    """Trousers: a shell over the hips and legs from below the waist to the ankle, loose enough to read as cloth."""
    colour = PALETTE[spec['colours'][0]]
    slot = spec.get('slot', 'CN_Cloth')
    p = Part(spec['piece'], (slot,))
    lv = g.levels
    top = lv['crotch'] + .6 * (lv['waist'] - lv['crotch'])
    # Over a shoe they break at the ankle; into a boot they tuck, ending well inside its shaft.
    feet = ctx.get('footwear')
    hem = BOOTS[feet['cut']](lv, g.scale) - TUCK * g.scale if feet and feet['make'] == 'boots' else lv['ankle'] - .01 * g.scale
    labels = ('pelvis', 'spine_01', 'spine_02', 'spine_03') + tuple('%s_%s' % (b, s) for s in SIDES for b in ('thigh', 'calf'))
    lift = lambda pts: TROUSERS_LIFT - .004 + .002 * noise2(pts[:, 0] * 14., pts[:, 2] * 7., 17) + .004 * _smooth((lv['knee'] - pts[:, 2]) / .25)
    shade = lambda pts: .92 + .08 * noise2(pts[:, 1] * 9., pts[:, 2] * 4., 5)
    _, ids = shell(p, g, labels, [((0, 0, top), (0, 0, -1)), ((0, 0, hem), (0, 0, 1))], lift, .004, colour, slot, k=shade)
    return p, dict(kind='legwear', covered=ids)


SOCK_TOP = .05     # m (x scale) under the knee joint where a knee sock ends, clear of the knee's bend
SOCK_LIFT = (.002, .0053)  # m a sock stands off the foot inside the shoe and off the leg, at a grown-up's size (a child's
                           # shrink with her clothes in costume(): Tamsin's 1.5 and 4 mm). Off the foot it stays well
                           # under the shoe's upper (.006: at the leg's lift the white came through it); off the leg, at
                           # 2.5 mm on her the calf came through when the knees bend.


def socks(g, spec, ctx):
    """Knee socks: a thin shell from the sole to under the knee. Only the top is an opening (the shoe holds the foot
    and the sock's edge at the sole), so the skin is hidden down to the sole."""
    colour = PALETTE[spec['colours'][0]]
    p = Part(spec['piece'], ('CN_Cloth',))
    covered = []
    for side in SIDES:
        labels = tuple('%s_%s' % (b, side) for b in ('calf', 'foot', 'ball'))
        top = g.levels['knee'] - SOCK_TOP * g.scale
        ankle = g.levels['ankle']

        def lift(pts, ankle=ankle):   # close on the foot, inside the shoe, full on the leg above the ankle
            return SOCK_LIFT[0] + (SOCK_LIFT[1] - SOCK_LIFT[0]) * _smooth((pts[:, 2] - ankle) / (.04 * g.scale))
        _, ids = shell(p, g, labels, [((0, 0, top), (0, 0, -1)), ((0, 0, SOLE_TOP), (0, 0, 1))], lift, .002, colour,
                       'CN_Cloth', k=.96, relax=1, opening=lambda pts, top=top: pts[:, 2] > top - .02)
        covered.append(ids)
    return p, dict(kind='legwear', covered=np.concatenate(covered))


# Footwear by kind and cut: (how high the upper reaches at the heel, as a fraction of the ankle's height, or a height on
# the leg; how low it is cut over the instep, as a fraction of the heel's; its lift off the foot).
SHOES = {('shoes', 'lace'): (.95, .8, .006), ('shoes', 'flat'): (.8, .5, .005), ('shoes', 'strap'): (.85, .5, .005),
         ('slippers', 'flat'): (.7, .45, .006)}
BOOTS = {'ankle': lambda lv, k: lv['ankle'] + .07 * k, 'mid_calf': lambda lv, k: (lv['ankle'] + lv['knee']) / 2 + .02 * k,
         'knee': lambda lv, k: lv['knee'] - .05 * k}


def _upper(p, g, labels, planes, lift, colour, slot, k):
    """A shoe's or a boot's upper: a shell over the foot down to SOLE_TOP, where the sole takes over."""
    return shell(p, g, labels, planes + [((0, 0, SOLE_TOP), (0, 0, 1))], lift, .004, colour, slot, k=k, relax=4)


def boots(g, spec, ctx):
    """Boots to the ankle, mid-calf or knee: a shell over the foot that loosens up the shaft, a rolled top, a sole
    (Dov's are rubber: CN_Lacquer)."""
    colour = PALETTE[spec['colours'][0]]
    slot = spec.get('slot', 'CN_Cloth')
    p = Part(spec['piece'], (slot,))
    top = BOOTS[spec['cut']](g.levels, g.scale)
    covered = []
    for side in SIDES:
        labels = tuple('%s_%s' % (b, side) for b in ('calf', 'foot', 'ball'))
        ankle = g.levels['ankle']
        # Tight over the foot, then clear of the trousers tucked into the shaft (their lift and their cloth).
        lift = lambda pts: .006 + (TROUSERS_LIFT + .004) * _smooth((pts[:, 2] - ankle + .02 * g.scale) / (.07 * g.scale))
        loops, ids = _upper(p, g, labels, [((0, 0, top), (0, 0, -1))], lift, colour, slot, .93)
        covered.append(ids)
        rim = max(loops, key=lambda l: l[:, 2].mean())
        _roll(p, rim, rim.mean(0), (0, 0, 1), .006, colour, slot, .85)
        _sole(p, g, side, colour, slot, .7)
    return p, dict(kind='footwear', covered=np.concatenate(covered))


def shoes(g, spec, ctx):
    """Shoes (lace-ups, flats, strapped) and slippers: a shell over the foot cut low over the instep, a sole; laces or a
    strap over the instep."""
    colour = PALETTE[spec['colours'][0]]
    slot = spec.get('slot', 'CN_Cloth')
    p = Part(spec['piece'], (slot,))
    heel_h, vamp, lift = SHOES[(spec['make'], spec['cut'])]
    covered = []
    for side in SIDES:
        heel, toe, _ = g.feet[side]
        back = np.array([heel, 0., heel_h * g.levels['ankle']])
        front = np.array([heel + .62 * (toe - heel), 0., vamp * heel_h * g.levels['ankle']])
        u = front - back
        normal = np.array([u[2], 0., -u[0]]) / np.linalg.norm(u)
        labels = tuple('%s_%s' % (b, side) for b in ('calf', 'foot', 'ball'))
        _, ids = _upper(p, g, labels, [(back, normal)], lambda pts: lift, colour, slot, .92)
        covered.append(ids)
        _sole(p, g, side, colour, slot, .7)
        foot = g.mesh['points'][_labelled(g.mesh['labels'], FOOT[side])]
        if spec['cut'] in ('lace', 'strap'):
            # Laces in three crossings up the instep, or one strap over it, on the upper's surface.
            xs = np.linspace(heel + .5 * (toe - heel), heel + .62 * (toe - heel), 3) if spec['cut'] == 'lace' else [heel + .5 * (toe - heel)]
            for x in xs:
                near = foot[np.abs(foot[:, 0] - x) < .01]
                if not len(near):
                    continue
                ztop = float(near[:, 2].max()) + lift + .004
                yc = float(near[:, 1].mean())
                half = .016 if spec['cut'] == 'lace' else float(np.ptp(near[:, 1])) / 2 + lift
                _box(p, (x, yc, ztop), (.004 if spec['cut'] == 'lace' else .007, half, .0025), colour, slot, .0015, .8)
    return p, dict(kind='footwear', covered=np.concatenate(covered))


def sandals(g, spec, ctx):
    """Sefa's red sandals: a sole, a strap across the toes' roots and one round the ankle, cut from shells of the foot."""
    colour = PALETTE[spec['colours'][0]]
    slot = spec.get('slot', 'CN_Cloth')
    p = Part(spec['piece'], (slot,))
    for side in SIDES:
        heel, toe, _ = g.feet[side]
        x = heel + .68 * (toe - heel)
        shell(p, g, FOOT[side], [((x - .012, 0, 0), (1, 0, 0)), ((x + .012, 0, 0), (-1, 0, 0)), ((0, 0, SOLE_TOP), (0, 0, 1))],
              lambda pts: .004, .003, colour, slot, k=.92, relax=1)
        ankle = g.levels['ankle']
        shell(p, g, ('calf_' + side,) + FOOT[side], [((0, 0, ankle + .004), (0, 0, 1)), ((0, 0, ankle + .022), (0, 0, -1))],
              lambda pts: .004, .003, colour, slot, k=.9, relax=1)
        _sole(p, g, side, colour, slot, .75)
    return p, dict(kind='footwear', covered=np.zeros(0, np.int64))


def vambrace(g, spec, ctx):
    """Teodor's white lacquered vambraces over the gambeson's sleeves, gold-edged: a plate curved round the back of each
    forearm, from below the elbow to above the wrist (one per side; MH names the bone)."""
    side = spec['bone'][-1]
    limb, sign = 'arm_' + side, SIDE_SIGN[side]
    colours = [PALETTE[c] for c in spec['colours']]
    slot = spec.get('slot', 'CN_Lacquer')
    p = Part(spec['piece'], (slot, 'CN_Gold'))
    ease = ctx['sleeves']['ease'] + SLEEVE_THICK + QUILT[1] + FOREARM_FLAT
    elbow = float(np.linalg.norm(g.limbs[limb][0][1] - g.limbs[limb][0][0]))
    s = np.linspace(elbow + .25 * (g.length(limb) - elbow), elbow + .88 * (g.length(limb) - elbow), 7)
    phi = np.linspace(-1.9, 1.9, 11)
    rows, axis = [], []
    for si in s:
        o, d = g.along(limb, si)
        out = np.array([0., sign, .4])
        out -= d * (out @ d)
        out /= np.linalg.norm(out)
        w = np.cross(d, out)
        r = g.radius(limb, si) + ease + .006 * (1 - ((si - s[0]) / (s[-1] - s[0]) - .5) ** 2)
        rows.append(o + r * (np.cos(phi)[:, None] * out + np.sin(phi)[:, None] * w))
        axis.append(np.repeat(o[None], len(phi), 0))
    P, C = np.array(rows), np.array(axis)
    P, Q = _sheet(p, P, .004, colours[0], slot, lambda Pp: Pp - C, k=.92, cap=.9)
    _piping(p, _border(P, Q), .0025, GOLD, 'CN_Gold', 1.0, closed=True, cap=None)
    return p, dict(kind='rigid')


NEW = {'sleeves': sleeves, 'collar_cuffs': collar_cuffs, 'undertop': undertop, 'trousers': trousers, 'socks': socks, 'boots': boots,
       'shoes': shoes, 'slippers': shoes, 'sandals': sandals, 'vambrace': vambrace}
# The cuts each new piece's builder makes; the cast's NEW_PIECES must ask for none other (main() checks it).
CUTS = {'sleeves': tuple(SLEEVE_CUTS), 'collar_cuffs': ('shirt',), 'undertop': ('crew',), 'trousers': ('ankle',), 'socks': ('knee',),
        'boots': tuple(BOOTS), 'shoes': tuple(c for k, c in SHOES if k == 'shoes'), 'slippers': tuple(c for k, c in SHOES if k == 'slippers'),
        'sandals': ('flat',), 'vambrace': ('forearm',)}


# ---------------------------------------------------------------- a person's costume

PORTS = {'SM_CP_G_SkirtSatchel': skirt_satchel, 'SM_CP_G_ApronSkirtWhite': apron_skirt_white, 'SM_CP_G_ApronSkirtGold': apron_skirt_gold,
         'SM_CP_G_SkirtGold': skirt_gold, 'SM_CP_G_TunicSkirt': tunic_skirt, 'SM_CP_G_RobeSkirt': robe_skirt,
         'SM_CP_G_RobeSkirtTall': robe_skirt_tall, 'SM_CP_G_CoatSkirtBlack': coat_skirt_black, 'SM_CP_G_CoatSkirtWhite': coat_skirt_white,
         'SM_CP_G_OilskinSkirt': oilskin_skirt, 'SM_CP_G_WorkApronSkirt': work_apron_skirt, 'SM_CP_G_GuardBelt': guard_belt,
         'SM_CP_G_CoatBlack': coat_black, 'SM_CP_G_BlouseStrap': blouse_strap, 'SM_CP_G_BlouseShawl': blouse_shawl, 'SM_CP_G_Tunic': tunic,
         'SM_CP_G_RobeShawl': robe_shawl, 'SM_CP_G_WorkApron': work_apron, 'SM_CP_G_Blouse': blouse, 'SM_CP_G_ArmourVest': armour_vest,
         'SM_CP_G_CoatWhite': coat_white, 'SM_CP_G_RobeTall': robe_tall, 'SM_CP_G_Oilskin': oilskin, 'SM_CP_G_BlouseBib': blouse_bib,
         # Headwear, by what MH keeps of it (the Listener's old garment was his hood and his ring at once).
         'SM_CP_G_StrawHat': straw_hat, 'SM_CP_G_CapRed': cap, 'SM_CP_G_HeadscarfRed': headscarf, 'SM_CP_G_Helmet': helmet,
         'SM_CP_G_FieldHat': field_hat, 'SM_CP_G_KnitCapBeard': knit_cap, 'SM_CP_G_BunBlack': spectacles, 'SM_CP_G_BunWhite': pins,
         'SM_CP_G_ShortHair': clip, 'SM_CP_G_BobBlack': band, 'SM_CP_G_HoodHalo': {'hood': hood, 'ring': ring}}
HEADWEAR = (straw_hat, cap, headscarf, helmet, field_hat, knit_cap, spectacles, pins, clip, band, hood, ring)
HANGING = ('skirt', 'coat', 'apron', 'belt')  # garments that hang from the pelvis and follow the thighs toward the hem
# What a new piece is made for, which MH must list before it: sleeves are set in the person's top (its kind of garment
# sets their ease), a shirt's cuffs and a vambrace go over the sleeves, an undertop and a shirt front under the top.
NEEDS = {'sleeves': ('upper',), 'collar_cuffs': ('upper', 'sleeves'), 'undertop': ('upper',), 'vambrace': ('sleeves',)}


class Costume:
    """A person's costume on a Guide.
      part       every piece merged into one toolkit.Part named after FILES['costume'] (SK_<key>_Costume), its slots the
                 ones the pieces use
      pieces     (name, first vertex, vertex count, weighting, kind) per piece in MH order; weighting is 'body' (the
                 build transfers the body guide's own weights), 'skirt' (the pelvis, and the near thigh toward the hem)
                 or a bone (rigid: all of it follows that bone); kind is what the builder made (top, skirt, coat, apron,
                 belt, hood, head, sleeves, legwear, footwear, collar, rigid)
      covered    per body guide vertex, True where the costume hides the skin (the build bakes it into the cloth mask)
      problems   what does not match MH (empty when the costume is right)"""

    def __init__(self, key, part, pieces, covered, problems):
        self.key, self.part, self.pieces, self.covered, self.problems = key, part, pieces, covered, problems


def _families(part):
    return {family(c[:3]) for c in part.c}


def _merged(name, parts):
    """The parts as one Part, their slots in toolkit.SLOTS order, only those a face uses (a stray slot imports as an
    empty material)."""
    used = {p.slots[i] for p in parts for i in p.m}
    whole = Part(name, [s for s in SLOTS if s in used])
    for p in parts:
        base = len(whole.v)
        whole.v.extend(p.v)
        whole.c.extend(p.c)
        whole.uv.extend([None] * len(p.v))
        whole.f.extend([[base + i for i in f] for f in p.f])
        whole.m.extend([whole.slots.index(p.slots[i]) for i in p.m])
        whole.s.extend(p.s)
    return whole


COVER_REACH = (.004, .012, .025, .04, .06, .08)  # m out along the skin's normal where cloth must lie for skin to be hidden
COVER_CELL = .025                                 # m: the cloth's vertices are looked up in cells this size, and count
                                                  # within it of a point out along the normal (cloth vertices lie closer)


def _cloth_over(g, cloth, candidates):
    """Which of the candidate body vertices have the costume's cloth over them: a cloth vertex within COVER_CELL of a
    point out along the skin's normal (COVER_REACH). Skin is hidden only where something is seen in its place."""
    keys = np.floor(cloth / COVER_CELL).astype(np.int64)
    cells = {}
    for i, k in enumerate(map(tuple, keys)):
        cells.setdefault(k, []).append(i)
    near = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)]
    points, normals = g.mesh['points'], g.normals[g.weld]
    out = np.zeros(len(points), bool)
    for i in np.nonzero(candidates)[0]:
        for t in COVER_REACH:
            q = points[i] + normals[i] * t
            k = np.floor(q / COVER_CELL).astype(np.int64)
            found = [j for o in near for j in cells.get((k[0] + o[0], k[1] + o[1], k[2] + o[2]), ())]
            if found and (np.linalg.norm(cloth[found] - q, axis=1) < COVER_CELL).any():
                out[i] = True
                break
    return out


def _near(points, sources, which, reach):
    """Which of the points which marks lie within reach of one of the points sources marks."""
    out = np.zeros(len(points), bool)
    src = points[sources]
    if not len(src):
        return out
    cells = {}
    for i, k in enumerate(map(tuple, np.floor(src / reach).astype(np.int64))):
        cells.setdefault(k, []).append(i)
    near = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)]
    for i in np.nonzero(which)[0]:
        k = np.floor(points[i] / reach).astype(np.int64)
        found = [j for o in near for j in cells.get((k[0] + o[0], k[1] + o[1], k[2] + o[2]), ())]
        if found and (np.linalg.norm(src[found] - points[i], axis=1) < reach).any():
            out[i] = True
    return out


OFF_TRUNK = ('head', 'hood', 'footwear', 'rigid')   # pieces that never cover the trunk: hats, hoods, shoes, vambraces
STRAP_MARGIN = .01  # m of skin kept drawn round a neck opening's corners under the straps (MARGIN elsewhere)


def _hidden(g, forms, cloth, layers):
    """Which body vertices the pieces hide: under a top between its hem and its neck opening (above the armpits only
    between the straps), under a closed skirt (and the legs inside it; not the feet, whose toes show under the longest
    hem) or the closed part of a coat's skirt, and what the shells say they cover; always MARGIN inside every opening,
    and only where the costume's cloth lies over the skin (cloth: its vertices), so a leg deep in a wide skirt stays
    drawn. Sleeves close a top's armholes, so beside the straps' neck-side edges it covers the whole shoulder: there
    the skin is hidden too, from its hem up, but STRAP_MARGIN round the skin no garment lies over (layers: the vertices
    of the pieces not OFF_TRUNK: a neck opening cut wider than the straps); between the straps it stays the band."""
    P, L = g.mesh['points'], g.mesh['labels']
    z = P[:, 2]
    trunk = _labelled(L, TRUNK)
    legs = _labelled(L, ['%s_%s' % (b, s) for s in SIDES for b in ('thigh', 'calf')])
    sleeved = any(form['kind'] == 'sleeves' for form in forms)
    if sleeved:
        # The shoulders: beside the straps' neck-side edges, with the strip of them labelled to the upper arms short of
        # the sleeves' heads (y_cut), which is in neither the trunk nor a sleeve. Kept drawn, they came through the
        # straps and the sleeves' heads when the arms hang.
        heads = _labelled(L, ('upperarm_l', 'upperarm_r')) & (np.abs(P[:, 1]) < (g.strap[0] + g.strap[1]) / 2)
        shoulders = (trunk | heads) & ~_labelled(L, ('neck_01', 'neck_02')) & (np.abs(P[:, 1]) > g.strap[0])
        bare = trunk & ~_cloth_over(g, layers, trunk)
        shoulders &= ~_near(P, bare, shoulders, STRAP_MARGIN)
    hidden = np.zeros(len(P), bool)
    for form in forms:
        kind = form['kind']
        if kind == 'top':
            band = trunk & (z > form['bottom'] + MARGIN) & (z < form['open'] - MARGIN)
            if sleeved:
                hidden |= band | (shoulders & (z > form['bottom'] + MARGIN))
            else:
                # Above the armpits only the middle of the chest and back: the armholes open round the arms' roots there.
                hidden |= band & ((z < g.levels['pit'] - MARGIN) | (np.abs(P[:, 1]) < g.strap[0]))
        elif kind == 'skirt':
            hidden |= (trunk | legs) & (z > form['hem'] + MARGIN) & (z < form['top'] - MARGIN)
        elif kind == 'coat':
            hidden |= trunk & (z > form['closed_to'] + MARGIN) & (z < form['top'] - MARGIN)
        if 'covered' in form:
            shelled = np.zeros(len(g.surface['points']), bool)
            shelled[form['covered']] = True
            hidden |= shelled[g.weld]
    return _cloth_over(g, cloth, hidden)


def costume(key, guide):
    """MH[key]'s costume built on guide (pending entries too: building is not showing). Raises KeyError for a piece no
    builder makes and ValueError for a guide the pieces cannot fit. A child's (age under 18) is built on her guide grown
    to the Mannequins' height (SOURCE_HEIGHT) and shrunk back to hers: the pieces' ease, folds, collars, belts and
    buttons are drawn in metres for grown-ups, so at her size they hung off her (Tamsin, 2026-11-10)."""
    entry = MH[key]
    grown = 1.0 / guide.scale if entry['age'] is not None and entry['age'] < 18 else 1.0
    real = guide
    if grown != 1.0:
        guide = guide.scaled(grown)
    grow = max(0., hair_depth(entry['grooms']) - PEOPLE_HAIR) * grown   # hair under a hat is her real hair's depth
    ctx, built, forms, problems = {}, [], [], []
    # Trousers end over shoes or inside boots, whichever the costume has.
    ctx['footwear'] = next((spec for spec in entry['costume'] if spec.get('make') in ('boots', 'shoes', 'slippers', 'sandals')), None)
    for spec in entry['costume']:
        if 'port' in spec:
            builder = PORTS[spec['port']]
            builder = builder[spec['piece']] if isinstance(builder, dict) else builder
            m = Port(guide, BUILT[spec['port']][1])
            part, form = builder(m, grow) if builder in HEADWEAR else builder(m)
            if form['kind'] == 'top' and 'upper' not in ctx:
                ctx.update(upper=builder.__name__, port=m, form=form)
        else:
            missing = [what for what in NEEDS.get(spec['make'], ()) if what not in ctx]
            if missing:
                raise ValueError('%s %s comes before the %s it is made for: reorder MH[%r][\'costume\']' % (key, spec['piece'], missing[0], key))
            part, form = NEW[spec['make']](guide, spec, ctx)
            if spec['make'] == 'sleeves':
                ctx['sleeves'] = form
        part.name = spec['piece']
        made, declared = _families(part), {family(PALETTE[c][:3]) for c in spec['colours']}
        if made - declared or declared - made:
            problems.append('%s %s: colours of the families %s, MH declares %s' % (key, spec['piece'], sorted(made), sorted(declared)))
        if spec.get('bone') and spec['bone'] not in CORE:
            problems.append('%s %s: bone %s is not one the costume can follow (CORE)' % (key, spec['piece'], spec['bone']))
        weighting = spec.get('bone') or ('skirt' if form['kind'] in HANGING else 'body')
        built.append((spec['piece'], part, weighting, form['kind']))
        forms.append(form)
    whole = _merged(FILES['costume'].format(key=key).rsplit('/', 1)[1], [part for _, part, _, _ in built])
    pieces, first = [], 0
    for name, part, weighting, kind in built:
        pieces.append((name, first, len(part.v), weighting, kind))
        first += len(part.v)
    layers = np.asarray([v for _, part, _, kind in built if kind not in OFF_TRUNK for v in part.v], np.float64).reshape(-1, 3)
    covered = _hidden(guide, forms, np.asarray(whole.v, np.float64), layers)   # vertex ids: the same at either size
    if grown != 1.0:
        whole.v = (np.asarray(whole.v, np.float64) / grown).tolist()
        assert abs(real.levels['crown'] - guide.levels['crown'] / grown) < 1e-9
    return Costume(key, whole, pieces, covered, problems)


# ---------------------------------------------------------------- offline: check.py costumes, and the costume test

def _built(key):
    """check.py's builder for key: the costume on its stand-in guide."""
    def build():
        return costume(key, standin_guide(key)).part
    build.__name__ = 'costume_' + key.lower()
    build.__doc__ = "MH[%r]'s costume on its stand-in guide." % key
    return build


MESHES = [_built(key) for key in MH]
CONTRACT = {FILES['costume'].format(key=key).rsplit('/', 1)[1]: {'pivot': 'any'} for key in MH}  # skinned: feet at z 0, worn


def read_fbx(path):
    """The node tree of a binary FBX (the guides' format): (name, properties, children) tuples; numeric arrays come back
    as numpy arrays. Enough for the test to read a guide without Blender."""
    import struct
    import zlib
    data = Path(path).read_bytes()
    if not data.startswith(b'Kaydara FBX Binary'):
        raise ValueError('%s is not a binary FBX' % path)
    wide = struct.unpack_from('<I', data, 23)[0] >= 7500
    arrays = {b'f': '<f4', b'd': '<f8', b'l': '<i8', b'i': '<i4', b'b': '<i1'}
    scalars = {b'Y': ('<h', 2), b'C': ('<?', 1), b'I': ('<i', 4), b'F': ('<f', 4), b'D': ('<d', 8), b'L': ('<q', 8)}

    def node(pos):
        end, count, _ = struct.unpack_from('<QQQ' if wide else '<III', data, pos)
        pos += 24 if wide else 12
        length = data[pos]
        if end == 0:
            return None, pos + length + 1
        name = data[pos + 1:pos + 1 + length].decode('latin1')
        pos += 1 + length
        props = []
        for _ in range(count):
            kind = data[pos:pos + 1]
            pos += 1
            if kind in scalars:
                fmt, size = scalars[kind]
                props.append(struct.unpack_from(fmt, data, pos)[0])
                pos += size
            elif kind in arrays:
                n, encoding, size = struct.unpack_from('<III', data, pos)
                raw = data[pos + 12:pos + 12 + size]
                pos += 12 + size
                props.append(np.frombuffer(zlib.decompress(raw) if encoding else raw, arrays[kind], n).copy())
            else:   # S string, R raw
                size = struct.unpack_from('<I', data, pos)[0]
                props.append(data[pos + 4:pos + 4 + size].decode('latin1') if kind == b'S' else data[pos + 4:pos + 4 + size])
                pos += 4 + size
        children = []
        while pos < end:
            child, pos = node(pos)
            if child is None:
                break
            children.append(child)
        return (name, props, children), end
    top, pos = [], 27
    while pos < len(data):
        found, pos = node(pos)
        if found is None:
            break
        top.append(found)
    return top


def from_fbx(points):
    """Guide FBX coordinates (cm; z up, the body facing -y, its left at +x) to this module's frame (m). It mirrors, so a
    triangle's corners go in reverse."""
    p = np.asarray(points, np.float64)
    return np.stack([-p[..., 1], -p[..., 0], p[..., 2]], -1) / 100.


def read_guide(path, lod):
    """A guide FBX as measure() takes it, without Blender: {'points', 'tris', 'labels', 'uv'} of its <name>_LOD<lod> mesh
    (each vertex labelled with the core bone carrying most of its weight once each bone's weight counts for its nearest
    core ancestor), and {bone: head} of every bone of its bind pose."""
    top = {name: children for name, _, children in read_fbx(path)}
    objects = {props[0]: (name, props, children) for name, props, children in top['Objects']}
    label = lambda props: props[1].split('\x00')[0]
    parent, owners = {}, {}
    for _, props, _ in top['Connections']:
        if props[0] == 'OO':
            owners.setdefault(props[2], []).append(props[1])
            child, owner = objects.get(props[1]), objects.get(props[2])
            if child and owner and child[0] == owner[0] == 'Model':
                parent[label(child[1])] = label(owner[1])
    field = lambda children, name: next(c for c in children if c[0] == name)
    geometry = next(o for o in objects.values() if o[0] == 'Geometry' and label(o[1]).endswith('_LOD%d' % lod))
    vertices = field(geometry[2], 'Vertices')[1][0].reshape(-1, 3)
    index = field(geometry[2], 'PolygonVertexIndex')[1][0].copy()
    ends = np.where(index < 0)[0]
    index[ends] = -index[ends] - 1
    tris = _tris(np.split(index, ends[:-1] + 1))
    uv = next((field(c[2], 'UV')[1][0].reshape(-1, 2) for c in geometry[2] if c[0] == 'LayerElementUV'), None)
    weights = np.zeros((len(vertices), len(CORE)))
    for skin in owners.get(geometry[1][0], []):
        for cluster in owners.get(skin, []):
            node = objects.get(cluster)
            bone = [label(objects[b][1]) for b in owners.get(cluster, []) if b in objects and objects[b][0] == 'Model']
            if not node or node[0] != 'Deformer' or not bone or not any(c[0] == 'Indexes' for c in node[2]):
                continue
            core = bone[0]
            while core not in CORE and core in parent:
                core = parent[core]
            np.add.at(weights[:, CORE.index(core if core in CORE else 'root')], field(node[2], 'Indexes')[1][0],
                      field(node[2], 'Weights')[1][0])
    pose = next(o for o in objects.values() if o[0] == 'Pose')
    bones = {}
    for pose_node in pose[2]:
        if pose_node[0] == 'PoseNode':
            target = objects.get(field(pose_node[2], 'Node')[1][0])
            if target:
                bones[label(target[1])] = from_fbx(field(pose_node[2], 'Matrix')[1][0].reshape(4, 4)[3, :3])
    return ({'points': from_fbx(vertices), 'tris': tris[:, ::-1], 'labels': np.array(CORE)[weights.argmax(1)], 'uv': uv}, bones)


DRAPED = ('top', 'skirt', 'coat', 'apron', 'belt')   # pieces wrapped round the trunk's sections, not lifted off its surface
ROUND_TRIP = .025   # m at the Mannequins' scale: a stand-in's coarse mesh measures its levels this near the Mannequin's
CLEAR_SHARE = .01   # a drape's share of vertices allowed inside the body's sections (a fold's valley, a knot's back)
PHYSIS_GUIDES = HERE.parents[1] / 'Art/Characters/Physis'


def _inside(g, points):
    """Which points lie inside the body's trunk sections (between the crotch and the armpits, where drapes wrap it)."""
    z = points[:, 2]
    band = (z > g.levels['crotch'] + .02) & (z < g.levels['pit'] - .02)
    hw, f, b = (np.interp(z, g.trunk[:, 0], g.trunk[:, i]) for i in (1, 2, 3))
    a = np.where(points[:, 0] >= 0, f, -b)
    return band & ((np.abs(points[:, 0] / a) ** ROUNDEST + np.abs(points[:, 1] / hw) ** ROUNDEST) < 1)


def costume_problems(c, g):
    """What is wrong with a built costume beyond check.py's mesh checks: MH mismatches (Costume.problems), empty pieces,
    drapes inside the body, skin hidden that shows (the hands, the head) or a body with nothing hidden."""
    out = list(c.problems)
    points = np.asarray(c.part.v, np.float64)
    for name, first, count, weighting, kind in c.pieces:
        if not count:
            out.append('%s %s: empty' % (c.key, name))
        elif kind in DRAPED:   # shells are lifted off the body's own surface; this checks what is drawn round it
            inside = _inside(g, points[first:first + count]).mean()
            if inside > CLEAR_SHARE:
                out.append('%s %s: %.1f%% of it inside the body' % (c.key, name, 100 * inside))
    shown = _labelled(g.mesh['labels'], [b for s in SIDES for b in ('hand_' + s,)])
    if (c.covered & shown).any():
        out.append('%s: the mask hides %d hand vertices' % (c.key, int((c.covered & shown).sum())))
    if not c.covered.any():
        out.append('%s: the costume hides no skin' % c.key)
    return out


def main():
    """The offline costume test (no Blender): every MH costume on its stand-in guide, measured back through measure();
    with --physis, also on Physis's own guides (the real MetaHuman guide format) when they are there."""
    from check import check_part
    quiet = '--quiet' in sys.argv
    problems = ['physis_conclave_cast.NEW_PIECES asks for %s %s, which no builder here makes' % (kind, cut)
                for kind, cuts in NEW_PIECES.items() for cut in cuts if cut not in CUTS.get(kind, ())]
    guides = [(key, standin_guide(key)) for key in MH]
    for key, g in guides:
        levels = SOURCES[CAST_MANNEQUIN[MH[key]['rows'][0]]['body']][1]
        problems += ['%s stand-in: measured %s %.3f, the Mannequin\'s %.3f' % (key, n, g.levels[n] / g.scale, levels[n])
                     for n in LEVELS if abs(g.levels[n] / g.scale - levels[n]) > ROUND_TRIP]
    if '--physis' in sys.argv:
        body_fbx, face_fbx = PHYSIS_GUIDES / 'physis-body-guide.fbx', PHYSIS_GUIDES / 'physis-face-guide.fbx'
        if body_fbx.exists() and face_fbx.exists():
            body, bones = read_guide(body_fbx, 1)
            face, face_bones = read_guide(face_fbx, 0)
            physis = measure(body, face, {k: bones[k] for k in CORE if k in bones},
                             {k: v for k, v in face_bones.items() if k.startswith('FACIAL_')}, source=str(body_fbx))
            guides += [(key, physis) for key in MH]
        else:
            print('no Physis guides in %s: --physis skipped' % PHYSIS_GUIDES)
    for key, g in guides:
        c = costume(key, g)
        found = []
        check_part(c.part, CONTRACT, found, True)
        found += costume_problems(c, g)
        problems += ['%s on %s: %s' % (key, g.source, f) for f in found]
        if not quiet:
            print('%-9s %-44s %6d tris  hides %4d of %4d body vertices  %s' % (key, g.source[-44:], c.part.triangles(), c.covered.sum(),
                                                                              len(c.covered), ','.join(c.part.slots)))
    if problems:
        print('\nFAILED (%d):' % len(problems))
        for p in problems:
            print('  -', p)
        sys.exit(1)
    print('\nall costume checks passed')


if __name__ == '__main__':
    main()
