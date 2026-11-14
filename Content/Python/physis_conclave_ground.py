"""M_CNGround and M_CNWater, the Conclave's terrain and water masters (Tools/conclave/README.md "Materials and
rendering"). physis_conclave_tools.materials() builds both through its ground_module(), which reloads this module
(the outfit dispatcher reloads only the plan, the lore and the tools module).

Editor Python without numpy. The HLSL is generated here from the world plan (the roads, plazas and lake of
physis_conclave_plan) and from the texture manifest's tile sizes, so the shader draws the roads exactly where the
Blender build cut them.

M_CNGround (the floor's terrain tiles and the upper lands overhead, slot CN_Ground) works in world space:
- The vertex colour (2 m cells) says what the ground is: golden grass, white stone (paving, shore sand, steep rock)
  or dark ground (soil, slag, silt, the docks' deck). Class edges are blended by the texture sets' heights (cavity),
  so they are a few centimetres wide and grass takes a stone's joints first, and every class keeps its colour in
  its own family: where a cell mixes road white into the lawn, the stone is no cream and the grass no pale gold.
- Roads and the two plazas are drawn analytically (ROADS, from physis_conclave_plan.road_segments()): crisp edges
  instead of the 2 m vertex smear, setts laid across each road in road space, kerbs, a worn shoulder, the Orrery's
  compass of stone courses with gold inlays, and the Spire court's basalt bands.
- The upper lands (the far side, 700-1400 m up) take their detail in drum coordinates (x, arc length round the
  drum), which keeps it square overhead instead of streaking.
- Wet bands at the lake's edge, ripples parallel to its shore, and organic sets sampled twice to hide their tiling.
M_CNWater: deep-water waves that fade with distance (their lost slope becomes roughness), capillary ripples from
the Ripple set, a tint by the water's vertical depth, refraction, and a lap line of foam at the shore.
"""
import math

import unreal

import physis_conclave_plan as plan
import physis_conclave_tools as T

CM = T.CM

# ---------------------------------------------------------------- HLSL building blocks

# Every ground texture is sampled through the view's shared wrap sampler: eight sets are sixteen textures, the
# per-material sampler limit. Custom-node code receives each texture's own sampler whatever the texture object's
# sampler source says, so the code names the shared one itself (GetMaterialSharedSampler falls back to the
# texture's own on platforms without independent samplers, as the engine's own shared-sampler code does).
SHARED = 'View.MaterialTextureBilinearWrapedSampler'


def tap(texture, uv):
    """A sample of `texture` at `uv` through the shared sampler."""
    return 'Texture2DSample(%s, GetMaterialSharedSampler(%sSampler, %s), %s)' % (texture, texture, SHARED, uv)


def tap_grad(texture, uv, dx, dy):
    """A sample with explicit uv gradients (where uv jumps, an implicit one would pick the coarsest mip). Through
    FloatDeriv2, so ray-traced hits still take the engine's ray-cone mip instead of the zero gradients they have."""
    return ('Texture2DSample(%s, GetMaterialSharedSampler(%sSampler, %s), ConstructFloatDeriv2(%s, %s, %s))'
            % (texture, texture, SHARED, uv, dx, dy))


def hash12(out, point):
    """Statements that set float `out` to a hash in [0, 1) of the float2 expression `point` (Dave Hoskins' sin-free
    hash, as physis_conclave_tools' noises use)."""
    return ('float3 @_q = frac(float3((' + point + ').xyx) * 0.1031); @_q += dot(@_q, @_q.yzx + 33.33); '
            'float @ = frac((@_q.x + @_q.y) * @_q.z);\n').replace('@', out)


def line(out, dist, width):
    """Statements that set float `out` to the coverage of a line `width` cm wide at `dist` cm from its centre:
    anti-aliased over the pixel footprint fpx, and thinned to its average where it is narrower than a pixel."""
    return 'float %s = saturate((%s * 0.5 - (%s)) / fpx + 0.5) * saturate(%s / fpx);\n' % (out, width, dist, width)


def capped(name, uv, tile):
    """Statements declaring float2 `name`_dx and `name`_dy: the derivatives of `uv`, held to what the ground's own
    footprint allows. Where a road or shore frame switches (a mitre, a junction, the island's frame), uv jumps, and
    the jump's derivative would otherwise pick the coarsest mip along that line."""
    return ('float2 @_dx = DDX(%s), @_dy = DDY(%s); float @_cap = 2.0 * fpx / %s;\n'
            '@_dx *= min(1.0, @_cap / max(length(@_dx), 1e-6)); @_dy *= min(1.0, @_cap / max(length(@_dy), 1e-6));\n'
            % (uv, uv, tile)).replace('@', name)


# Organic sets (grass, sand, soil) are sampled twice, at offsets that change in patches, and blended where the patches
# meet (Inigo Quilez, "texture repetition", technique 3): k = 8 x value noise at a twentieth of the tile frequency.
# The noise follows world (or drum) position, not uv, so frames whose uv jumps (the shore's polar angle) keep it whole.
ANTI_TILE = 8.0


def untiled(name, texture, uv, at, dx, dy):
    """Statements declaring float4 `name`: the masks at `uv`, two taps blended. `name`_o0, _o1 (offsets) and _k (the
    blend) are kept for the normal map, so albedo and relief change patch together."""
    return (T.value_noise2('@_v', at) +
            ('float @_s = %.1f * @_v; float @_i = floor(@_s); float @_f = @_s - @_i;\n'
             'float2 @_o0 = sin(float2(3.0, 7.0) * @_i), @_o1 = sin(float2(3.0, 7.0) * (@_i + 1.0));\n'
             'float4 @_a = %s;\nfloat4 @_b = %s;\n'
             'float @_k = smoothstep(0.2, 0.8, @_f - 0.1 * (@_a.r - @_b.r));\n'
             'float4 @ = lerp(@_a, @_b, @_k);\n')
            % (ANTI_TILE, tap_grad(texture, uv + ' + @_o0', dx, dy), tap_grad(texture, uv + ' + @_o1', dx, dy))).replace('@', name)


def untiled_normal(out, texture, name, uv, dx, dy):
    """Statements declaring float2 `out`: the normal map's xy (-1..1) at the masks `name`'s two offsets and blend."""
    return ('float2 %s = lerp(%s.rg, %s.rg, %s_k) * 2.0 - 1.0;\n'
            % (out, tap_grad(texture, '%s + %s_o0' % (uv, name), dx, dy), tap_grad(texture, '%s + %s_o1' % (uv, name), dx, dy), name))


def f2(point):
    """A plan point in metres as an HLSL float2 in centimetres."""
    return 'float2(%.1f, %.1f)' % (point[0] * CM, point[1] * CM)


# ---------------------------------------------------------------- road space (ROADS)

ROAD_BAND = 300.0        # cm beyond a road's or plaza's edge where road space overrides the vertex classes
MITRE_MARGIN = 50.0      # cm a segment reaches past its bend's mitre, so it is still a candidate there


def _bend_reach(seg, other):
    """How far (cm) a segment's frame reaches past a bend it shares with `other`: to the bend's bisector across
    the whole road and its band, plus a margin."""
    turn = abs(math.atan2(seg[0] * other[1] - seg[1] * other[0], seg[0] * other[0] + seg[1] * other[1]))
    return (seg[2] * CM + ROAD_BAND) * math.tan(turn / 2) + MITRE_MARGIN


def roads_code():
    """ROADS, one unrolled pass over every road segment (physis_conclave_plan.road_segments(), metres) per pixel:
    return float4(dR, tangent x, tangent y, arc); output Lat.
    - dR: cm from the nearest road edge, negative on the road (the least distance-minus-half-width of any segment:
      the union of the strips, so junctions of a wide and a narrow road keep both edges).
    - The frame (tangent, arc along the road in cm, Lat = cm left of the centreline): from the segment whose strip
      is nearest when each segment reaches past its bends to the bisector. So the courses of setts meet in a mitre
      at every bend instead of smearing round its outer corner, and a road's own ends stay square at a junction."""
    rows = []
    for ax, ay, bx, by, half, arc0 in plan.road_segments():
        dx, dy = (bx - ax) * CM, (by - ay) * CM
        length = math.hypot(dx, dy)
        rows.append({'a': (ax, ay), 'u': (dx / length, dy / length), 'length': length, 'half': half * CM, 'arc0': arc0 * CM})
    code = ('float2 p = WP.xy;\nfloat dR = 1e9;\nfloat sel = 1e9;\nfloat3 frame = float3(1.0, 0.0, 0.0);\nfloat lat = 0.0;\n'
            'float2 d; float t; float tc; float ex;\n')
    for k, row in enumerate(rows):
        ux, uy = row['u']
        # A segment continues its road where the next row starts with arc0 > 0 (road_segments() lists each road's
        # segments in order, its first at arc0 0).
        before = rows[k - 1] if row['arc0'] > 0 else None
        after = rows[k + 1] if k + 1 < len(rows) and rows[k + 1]['arc0'] > 0 else None
        lo = -_bend_reach((ux, uy, row['half'] / CM), before['u']) if before else 0.0
        hi = row['length'] + (_bend_reach((ux, uy, row['half'] / CM), after['u']) if after else 0.0)
        code += ('d = p - %s; t = dot(d, float2(%.6f, %.6f));\n'
                 'tc = clamp(t, 0.0, %.2f); dR = min(dR, length(d - float2(%.6f, %.6f) * tc) - %.1f);\n'
                 'tc = clamp(t, %.2f, %.2f); ex = length(d - float2(%.6f, %.6f) * tc) - %.1f;\n'
                 'if (ex < sel) { sel = ex; frame = float3(%.6f, %.6f, %.2f + tc); lat = d.y * %.6f - d.x * %.6f; }\n'
                 % (f2(row['a']), ux, uy, row['length'], ux, uy, row['half'], lo, hi, ux, uy, row['half'],
                    ux, uy, row['arc0'], ux, uy))
    return code + 'Lat = lat;\nreturn float4(dR, frame);'


# ---------------------------------------------------------------- M_CNGround

GROUND_SETS = (('Grass', 'GrassMat'), ('Flag', 'Flagstone'), ('Sand', 'Sand'), ('Rock', 'Rock'), ('Soil', 'Soil'),
               ('Deck', 'Deck'), ('Setts', 'Setts'), ('Paving', 'Paving'))
TILE_FALLBACK = 200      # cm, for a set the manifest does not list (conclave:textures will have refused it anyway)
FAR_Z = 50000.0          # cm: the floor stays under about 120 m; above this is the far side (the upper lands)
GOLD_SAT = .45           # (max - min) / max in linear vertex colour: below it a grass colour is resaturated to gold
WHITE_SAT = .15          # ...and above it a stone colour is desaturated (IVORY is .18, a road-and-lawn cream .2-.5)
WHITE_PEAK = max(T.PAL.WHITE[:3])   # PaveBright is the albedo this white stone takes
KERB = 30.0              # cm: kerb stones along the inside of every road edge
KERB_STEP, KERB_JITTER = 80.0, 20.0   # cm: one kerb joint per step, jittered, so stones run 60-100 cm
KERB_JOINT = .8          # cm
SHOULDER = 50.0          # cm: the worn shoulder outside the kerb
VERGE = (60.0, 120.0)    # cm off a road: the vertex white there is the road's smear, so the verge is grass
# The Orrery's compass (plan.ORRERY): courses 60 cm wide from 6.5 m, stones about 90 cm long, an edge course of slate
# from 43.5 m to the plaza's rim, gold inlay rings 5 cm wide at 12, 24 and 36 m, and twelve hour lines inside 12 m.
COMPASS_IN, COMPASS_OUT, COMPASS_RING, COMPASS_STONE, COMPASS_JOINT = 650.0, 4350.0, 60.0, 90.0, .6
INLAY_RINGS, INLAY_WIDTH, HOURS = (1200.0, 2400.0, 3600.0), 5.0, 12
SPIRE_BAND, SPIRE_BAND_WIDTH = 600.0, 50.0    # cm: a basalt band every 6 m round the Spire court
BEVEL = 1.0              # cm: the rounded arris of a compass stone at its joints
ARRIS = 2.5              # cm: a kerb's rounded arris
# Shore frames (plan.LAKE, plan.RESERVOIR_ISLAND): ripples run parallel to the nearest shore. Polar angle round the
# lake's centre (ellipse-normalised) or the island's, whole tiles round each so the angle's seam is invisible.
ISLE_SHORE = 16.7        # m: the island's waterline (drum.py island_profile: 3 m top at 9 m, -4 m from 26 m)
ISLE_FRAME = 3500.0      # cm round the island where its own frame is used (under water beyond its beach)


def _lake_perimeter():
    """The lake shore's length in cm (Ramanujan's ellipse perimeter)."""
    a, b = plan.LAKE[2], plan.LAKE[3]
    return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b))) * CM


def _ground_constants():
    (ox, oy), orrery_r = plan.PLAZAS[0]
    (sx, sy), spire_r = plan.PLAZAS[1]
    qx, qy, qr, qb = plan.REGIONS['Old Quarter']
    return {'FAR_Z': '%.1f' % FAR_Z, 'ORRERY': f2((ox, oy)), 'ORRERY_R': '%.1f' % (orrery_r * CM), 'SPIRE': f2((sx, sy)),
            'SPIRE_R': '%.1f' % (spire_r * CM), 'OLD_QUARTER': f2((qx, qy)), 'OLD_QUARTER_R': '%.1f' % ((qr + qb / 2) * CM),
            'LAKE_C': f2(plan.LAKE[:2]), 'LAKE_A': f2(plan.LAKE[2:]), 'LAKE_P': '%.1f' % _lake_perimeter(),
            'ISLE_C': f2(plan.RESERVOIR_ISLAND), 'ISLE_R': '%.1f' % (ISLE_SHORE * CM),
            'ISLE_P': '%.1f' % (2 * math.pi * ISLE_SHORE * CM), 'ISLE_FRAME': '%.1f' % ISLE_FRAME,
            'COMPASS_IN': '%.1f' % COMPASS_IN, 'COMPASS_OUT': '%.1f' % COMPASS_OUT, 'COMPASS_RING': '%.1f' % COMPASS_RING,
            'COMPASS_STONE': '%.1f' % COMPASS_STONE, 'COMPASS_JOINT': '%.2f' % COMPASS_JOINT,
            'EDGE_MID': '%.1f' % ((COMPASS_OUT + orrery_r * CM) / 2), 'KERB': '%.1f' % KERB, 'KERB_STEP': '%.1f' % KERB_STEP,
            'KERB_JITTER': '%.1f' % KERB_JITTER, 'KERB_JOINT': '%.2f' % KERB_JOINT, 'BAND': '%.1f' % ROAD_BAND,
            'GOLD_SAT': '%.3f' % GOLD_SAT, 'WHITE_SAT': '%.3f' % WHITE_SAT, 'WHITE_PEAK': '%.4f' % WHITE_PEAK,
            'SHOULDER': '%.1f' % SHOULDER, 'VERGE0': '%.1f' % VERGE[0], 'VERGE1': '%.1f' % VERGE[1],
            'INLAY_WIDTH': '%.1f' % INLAY_WIDTH, 'INLAY_LAST': '%.1f' % INLAY_RINGS[0], 'HOURS': '%.1f' % HOURS,
            'SPIRE_BAND': '%.1f' % SPIRE_BAND, 'SPIRE_BAND_WIDTH': '%.1f' % SPIRE_BAND_WIDTH, 'BEVEL': '%.2f' % BEVEL,
            'ARRIS': '%.2f' % ARRIS}


def _fill(code):
    """Puts the constants into code written with $NAME placeholders."""
    for key, value in sorted(_ground_constants().items(), key=lambda item: -len(item[0])):
        code = code.replace('$' + key, value)
    if '$' in code:
        raise ValueError('unfilled constant in the ground HLSL: ' + code[code.index('$'):code.index('$') + 30])
    return code


# The vertex classes as before (gold by saturation; bright achromatic is stone; the rest dark), the far side's drum
# coordinates (p2: x, and arc length round the drum from the bottom; tvTop: the surface's own v direction there), the
# vertex rule for paving (level and above the shore; overhead the normal never passes 0.93, so bright ground is paved),
# the footprint fpx (cm per pixel) and two octaves of value noise.
CLASS = _fill('''float vmx = max(VC.r, max(VC.g, VC.b));
float vmn = min(VC.r, min(VC.g, VC.b));
float vsat = (vmx - vmn) / max(vmx, 0.0001);
float wg0 = saturate((vsat - 0.3) * 4.0);
float ws0 = (1.0 - wg0) * saturate((vmx - 0.35) * 6.0);
float wd0 = 1.0 - wg0 - ws0;
float far = step($FAR_Z, WP.z);
float ang = atan2(WP.y, AxisZ - WP.z);
float2 p2 = lerp(WP.xy, float2(WP.x, DrumR * ang), far);
float3 tvTop = lerp(float3(0.0, 1.0, 0.0), float3(0.0, cos(ang), sin(ang)), far);
float3 nv = normalize(VN);
float level = saturate((nv.z - 0.93) * 20.0);
float pavedV = lerp(level * saturate((WP.z - Water - 170.0) / 40.0), saturate((vmx - 0.55) * 8.0), far);
float fpx = max(max(length(DDX(WP)), length(DDY(WP))), 0.001);
''') + T.value_noise2('n1', 'p2 / 1150.0') + T.value_noise2('n2', 'p2 / 310.0 + float2(5.2, 1.3)')

# Where each set is sampled. Grass, flags, soil, deck and paving are projected from above (from the drum's axis on
# the far side), rock triplanar. Setts lie in road space (u along the road, v = Lat across it, so the courses run on
# over the centreline): each 2 m block along the road is shifted across it by its own amount, which hides the
# tiling without blending two copies of a pattern of joints (the set's courses end on the tile's edge, so the
# blocks meet on a course joint). Sand lies in the shore's polar frame (u along the shore: the set's ripple crests
# run along u), with the polar angle's gradients written out, since its seam would pick the coarsest mip.
FRAMES = _fill('''float2 uvG = p2 / GrassTile;
float2 uvG2 = float2(uvG.y, -uvG.x) * 0.37 + 0.31;
float2 uvF = p2 / FlagTile;
float2 uvD = p2 / SoilTile;
float2 uvK = p2 / DeckTile;
float2 uvP = p2 / PavingTile;
float3 pr = WP / RockTile;
float3 tw = pow(abs(nv), 4.0);
tw /= max(tw.x + tw.y + tw.z, 0.0001);
float2 tu = Road.yz;
float2 tvR = float2(-tu.y, tu.x);
float2 uvT = float2(Road.w, Lat) / SettsTile;
''') + hash12('blockShift', 'float2(floor(uvT.x), 17.0)') + capped('setts', 'uvT', 'SettsTile') + _fill('''float2 uvT2 = uvT + float2(0.0, blockShift);
float2 qL = (WP.xy - $LAKE_C) / $LAKE_A;
float2 dI = WP.xy - $ISLE_C;
float isle = step(length(dI), $ISLE_FRAME);
float2 qs = lerp(qL, dI, isle);
float rq2 = max(dot(qs, qs), 1e-8);
float rings = max(round(lerp($LAKE_P, $ISLE_P, isle) / SandTile), 1.0) / 6.2831853;
float across = lerp(length(WP.xy - $LAKE_C) * (1.0 - rsqrt(max(dot(qL, qL), 1e-8))), length(dI) - $ISLE_R, isle);
float2 uvS = float2(atan2(qs.y, qs.x) * rings, across / SandTile);
float2 qdx = DDX(qs), qdy = DDY(qs);
float2 sand_dx = float2((qs.x * qdx.y - qs.y * qdx.x) / rq2 * rings, DDX(across) / SandTile);
float2 sand_dy = float2((qs.x * qdy.y - qs.y * qdy.x) / rq2 * rings, DDY(across) / SandTile);
float sandCap = 2.0 * fpx / SandTile;
sand_dx *= min(1.0, sandCap / max(length(sand_dx), 1e-6));
sand_dy *= min(1.0, sandCap / max(length(sand_dy), 1e-6));
float2 svS = normalize(lerp(WP.xy - $LAKE_C, dI, isle) + float2(0.0001, 0.0));
float2 suS = float2(-svS.y, svS.x);
''')

# The two plazas, analytic: the Orrery's compass (courses round the Orrery, each cut into stones with radial joints
# staggered course to course, then the edge course) and the Spire court. Every compass stone takes the paving set's
# grain from its own offset (gradients from the unshifted uv, so the shifts do not blur the joints).
PLAZA = _fill('''float2 dOr = WP.xy - $ORRERY;
float rO = length(dOr);
float aO = atan2(dOr.y, dOr.x) / 6.2831853 + 0.5;
float rS = length(WP.xy - $SPIRE);
float dPlaza = min(rO - $ORRERY_R, rS - $SPIRE_R);
float compass = step($COMPASS_IN, rO) * step(rO, $ORRERY_R);
float edgeC = step($COMPASS_OUT, rO);
float ringF = (rO - $COMPASS_IN) / $COMPASS_RING;
float ringI = floor(ringF);
float stones = max(floor(6.2831853 * lerp($COMPASS_IN + (ringI + 0.5) * $COMPASS_RING, $EDGE_MID, edgeC) / $COMPASS_STONE), 1.0);
float sa = aO * stones + frac(ringI * 0.618034) * (1.0 - edgeC);
float stone = floor(sa) - stones * floor(floor(sa) / stones);
float dJR = lerp(min(ringF - ringI, 1.0 - (ringF - ringI)) * $COMPASS_RING, rO - $COMPASS_OUT, edgeC);
float dJA = min(frac(sa), 1.0 - frac(sa)) * 6.2831853 * rO / stones;
''') + hash12('stoneHash', 'float2(stone, lerp(ringI, -1.0, edgeC))') + line('jRing', 'dJR', '$COMPASS_JOINT') + \
    line('jRadial', 'dJA', '$COMPASS_JOINT') + _fill('''float jC = compass * max(jRing, jRadial);
float2 uvP2 = uvP + compass * float2(stoneHash, frac(stoneHash * 13.7));
''')
PLAZA = _fill(PLAZA)

# The masks, every one sampled outside any branch (sampling in divergent flow has undefined derivatives).
TAPS = (untiled('mG', 'TexGrass', 'uvG', 'p2 / (GrassTile * 20.0)', 'DDX(uvG)', 'DDY(uvG)') +
        'float gm = %s.r;\nfloat4 mF = %s;\n' % (tap('TexGrass', 'uvG2'), tap('TexFlag', 'uvF')) +
        untiled('mS', 'TexSand', 'uvS', 'WP.xy / (SandTile * 20.0)', 'sand_dx', 'sand_dy') +
        'float4 mR = %s * tw.x + %s * tw.y\n          + %s * tw.z;\n' % (tap('TexRock', 'pr.zy'), tap('TexRock', 'pr.xz'), tap('TexRock', 'pr.xy')) +
        untiled('mD', 'TexSoil', 'uvD', 'p2 / (SoilTile * 20.0)', 'DDX(uvD)', 'DDY(uvD)') +
        'float4 mK = %s;\nfloat4 mT = %s;\nfloat4 mP = %s;\n' % (
            tap('TexDeck', 'uvK'), tap_grad('TexSetts', 'uvT2', 'setts_dx', 'setts_dy'), tap_grad('TexPaving', 'uvP2', 'DDX(uvP)', 'DDY(uvP)')))

# The paved shape: roads and plazas, on the floor only. Its edge is crisp; the grass beyond overhangs the edge stones
# by its tufts and wanders slowly along them (the stones themselves are straight). Inside: the plazas' own stone,
# else kerb stones along the inside of the edge, then setts (flagstone in the Old Quarter, whose streets are older).
# Behind a kerb, where the grass line leaves a gap, is grit. cavPaved is the paved stone's height for the blend.
SHAPE = _fill('''float dShape = min(Road.x, dPlaza);
float e = max(1.5 * fpx, 1.0);
float onShape = (1.0 - far) * (1.0 - smoothstep(-e, e, dShape + EdgeTuft * (mG.b - 0.5) + EdgeWander * (n2 - 0.5)));
float inBand = (1.0 - far) * (1.0 - smoothstep($BAND - 100.0, $BAND, dShape));
float plaza = 1.0 - smoothstep(-e, e, dPlaza);
float kerb = (1.0 - plaza) * smoothstep(-$KERB - e, -$KERB + e, Road.x);
float oldQuarter = 1.0 - smoothstep($OLD_QUARTER_R - 50.0, $OLD_QUARTER_R + 50.0, length(WP.xy - $OLD_QUARTER));
float setts = (1.0 - plaza) * (1.0 - kerb) * (1.0 - oldQuarter);
float flagR = (1.0 - plaza) * (1.0 - kerb) * oldQuarter;
float kerbCell = floor(Road.w / $KERB_STEP);
''') + hash12('kerbA', 'float2(kerbCell, 3.0)') + hash12('kerbB', 'float2(kerbCell + 1.0, 3.0)') + _fill('''float kerbJ0 = kerbCell * $KERB_STEP + $KERB_JITTER * (kerbA - 0.5);
float kerbJ1 = (kerbCell + 1.0) * $KERB_STEP + $KERB_JITTER * (kerbB - 0.5);
float kerbStone = kerbCell - step(Road.w, kerbJ0);
''') + hash12('kerbTone', 'float2(kerbStone, 5.0)') + line('kJoint', 'min(abs(Road.w - kerbJ0), abs(Road.w - kerbJ1))', '$KERB_JOINT') + \
    _fill('''float kBack = smoothstep(-e, e, Road.x);
float cavPlaza = lerp(mP.b, 1.0 - jC, compass);
float cavShape = cavPlaza * plaza + (1.0 - kJoint) * (1.0 - kBack) * kerb + mT.b * setts + mF.b * flagR;
float cavPaved = lerp(mF.b, cavShape, onShape);
''')
SHAPE = _fill(SHAPE)

PREFIX = CLASS + FRAMES + PLAZA + TAPS + SHAPE

# GROUND_W: the class weights and the paved share (float4: grass, stone, dark, paved).
# - On the shape everything is paved stone. In the band off it the vertex white is the road's smear: white mixed with
#   any gold, and all of it in the first metre, is verge grass, and the shoulder wears toward soil (a class weight, so
#   it shows as bare patches between tufts, never as a brown mix of the two colours).
# - Then each class's height (its weight, its set's cavity, a little noise) decides: the highest wins within Band
#   (wider with distance, so far edges do not alias), and a class absent from the vertex colour never appears.
GROUND_W = PREFIX + _fill('''float off = (1.0 - onShape) * inBand;
float verge = max(1.0 - smoothstep($VERGE0, $VERGE1, dShape), saturate((vsat - 0.1) * 10.0)) * off;
float wear = Wear * (1.0 - smoothstep(0.0, $SHOULDER, dShape)) * off;
float3 win = float3(wg0 + ws0 * verge, ws0 * (1.0 - verge), wd0) * (1.0 - wear) + float3(0.0, 0.0, wear);
win = win * (1.0 - onShape) + float3(0.0, onShape, 0.0);
float pavedF = onShape + (1.0 - onShape) * pavedV;
float sandy = (1.0 - pavedF) * saturate(1.0 - (WP.z - Water - 60.0) / 250.0);
float bs = lerp(lerp(mR.b, mS.b, sandy), cavPaved, pavedF);
float3 h3 = win + float3(BlendHeight * (mG.b - 0.5) + BlendNoise * (n2 - 0.5), BlendHeight * (bs - 0.5) - BlendNoise * (n2 - 0.5),
                         BlendHeight * (mD.b - 0.5) + BlendNoise * (n1 - 0.5));
float hm = max(h3.x, max(h3.y, h3.z));
float bd = max(Band, 0.0075 * fpx);
float3 w = saturate((h3 - hm + bd) / bd) * saturate(win * 20.0);
float sw = w.x + w.y + w.z;
w = sw > 0.001 ? w / sw : win;
return float4(w, pavedF);''')

# Shared by GROUND and GROUND_NORMAL: the weights from GROUND_W, the shore sand share and the docks' deck (which wins
# over any ground but grass there).
WEIGHTS = '''float wg = W.x;
float ws = W.y;
float wd = W.z;
float paved = W.w;
float sandy = (1.0 - paved) * saturate(1.0 - (WP.z - Water - 60.0) / 250.0);
float dock = saturate((DockR - length(WP.xy - DockC.xy)) / 800.0) * (1.0 - wg);
'''

# GROUND: base colour and roughness, and (output Metallic) the compass's gold inlays.
# - Class colours: grass resaturated to gold (straw where the vertex colour has no gold at all), stone desaturated
#   to white, dark ground the vertex grey (verge soil where the vertex colour is the road's) warmed by DarkTint: soil,
#   slag and silt under the light-blue sky light rendered navy.
# - Lawns: dry straw patches moved +-0.25 by two broad octaves (meadows of gold and straw). Never below 0.72 of the
#   vertex gold: palette.py's gold needs sRGB value 0.5, so darker reads brown.
# - Paved stone at PaveBright (WHITE at 0.82 sat on the tone curve's shoulder and flattened every joint); setts with
#   darker grit in their joints near the edges and a polished band down the middle; grey kerbs; the compass's stones
#   each their own tone, its slate edge course, the Spire court's basalt bands.
# - Sand at SandBright (at 0.82-0.85 white sand rendered as snow). Shore bands, never on gold: swash (wet, a mirror),
#   damp sand, and a thin residue line above them.
GROUND = PREFIX + WEIGHTS + T.value_noise2('n3', 'p2 / 4000.0 + float2(1.7, 8.3)') + \
    T.value_noise2('n4', 'p2 / 16000.0 + float2(6.1, 2.9)') + line('gHour', 'abs(frac(aO * $HOURS + 0.5) - 0.5) * 6.2831853 * rO / $HOURS', '$INLAY_WIDTH') + \
    line('gRing', 'min(min(abs(rO - 1200.0), abs(rO - 2400.0)), abs(rO - 3600.0))', '$INLAY_WIDTH') + \
    line('band', 'abs(frac(rS / $SPIRE_BAND + 0.5) - 0.5) * $SPIRE_BAND', '$SPIRE_BAND_WIDTH') + _fill('''float dry = saturate(DryShare + 0.25 * ((n3 - 0.5) * 1.2 + (n4 - 0.5) * 0.8));
float dmx = max(Dry.r, max(Dry.g, Dry.b));
float3 gold = vmx - (vmx - VC.rgb) * max(1.0, $GOLD_SAT / max(vsat, 0.01));
float3 grassBase = lerp(Dry.rgb * (vmx / max(dmx, 0.0001)), gold, saturate((vsat - 0.05) * 8.0));
float3 whiteBase = vmx - (vmx - VC.rgb) * min(1.0, $WHITE_SAT / max(vsat, 0.0001));
float3 darkBase = lerp(Verge.rgb, vmn.xxx, saturate(wd0 * 2.0)) * DarkTint.rgb;
float gv = (n1 - 0.5) * 0.9 + (n2 - 0.5) * 0.8;
float3 grass = lerp(grassBase, Dry.rgb, dry * saturate((n1 - 0.45) * 2.5) * saturate((n2 - 0.3) * 2.0));
float gmul = 1.0 + GrassVar * 2.0 * gv + GrassDetail * (mG.r * 2.0 - 1.0) + 0.5 * GrassDetail * (gm * 2.0 - 1.0);
gmul *= lerp(1.0, GapDark, mG.a);
grass *= clamp(gmul, 0.72, 1.25);
float sv = (n2 - 0.5) * 0.6;
float3 pave = whiteBase * (PaveBright / $WHITE_PEAK) * (1.0 + StoneVar * sv);
float3 flag = pave * (1.0 + FlagDetail * (mF.r * 2.0 - 1.0)) * lerp(1.0, mF.b, 0.5) * lerp(1.0, GroutDark, mF.a);
float grit = lerp(GroutDark, GroutDark * 0.7, smoothstep(-100.0, -40.0, Road.x));
float3 sett = pave * (1.0 + SettsDetail * (mT.r * 2.0 - 1.0)) * lerp(1.0, mT.b, 0.5) * lerp(1.0, grit, mT.a);
float3 kerbCol = Kerb.rgb * (1.0 + 0.1 * (2.0 * kerbTone - 1.0)) * (1.0 + 0.3 * RockDetail * (mR.r * 2.0 - 1.0)) * lerp(1.0, GroutDark, kJoint);
kerbCol = lerp(kerbCol, Verge.rgb, kBack);
float pmx = max(Pave.r, max(Pave.g, Pave.b));
float grain = lerp(mP.r, 0.5, mP.a * compass) * 2.0 - 1.0;
float3 slab = Pave.rgb * (PaveBright / max(pmx, 0.0001)) * (1.0 + 0.12 * (2.0 * stoneHash - 1.0) * compass) * (1.0 + PavingDetail * grain)
    * lerp(1.0, mP.b, 0.5 * (1.0 - compass)) * lerp(1.0, GroutDark, lerp(mP.a, jC, compass));
slab = lerp(slab, Course.rgb * (1.0 + PavingDetail * grain) * lerp(1.0, GroutDark, jC), edgeC * compass);
slab = lerp(slab, Basalt.rgb * (1.0 + PavingDetail * grain), band * step(0.5 * $SPIRE_BAND, rS) * (1.0 - step($ORRERY_R, -rO)));
float3 shapeCol = slab * plaza + kerbCol * kerb + sett * setts + flag * flagR;
float3 sand = whiteBase * (SandBright / max(vmx, 0.05)) * (1.0 + StoneVar * sv) * (1.0 + SandDetail * (mS.r * 2.0 - 1.0)) * lerp(1.0, 1.08, mS.a);
float3 rock = whiteBase * (1.0 + StoneVar * sv) * (1.0 + RockDetail * (mR.r * 2.0 - 1.0)) * lerp(1.0, mR.b, 0.6);
float3 stone = lerp(lerp(rock, sand, sandy), lerp(flag, shapeCol, onShape), paved);
float dv = (n2 - 0.5) * 0.7;
float3 dark = darkBase * clamp(1.0 + SoilVar * 2.0 * dv + SoilDetail * (mD.r * 2.0 - 1.0), 0.55, 1.6) * lerp(1.0, mD.b, 0.6);
float3 col = grass * wg + stone * ws + dark * wd;
float3 deck = vmn.xxx * DarkTint.rgb * (1.0 + DeckDetail * (mK.r * 2.0 - 1.0)) * lerp(1.0, mK.b, 0.5);
col = lerp(col, deck, dock);
float flagRough = StoneRough + RVar * (mF.g * 2.0 - 1.0) + 0.3 * mF.a;
float settsRough = StoneRough + RVar * (mT.g * 2.0 - 1.0) + 0.3 * mT.a - Polish * (1.0 - smoothstep(80.0, 120.0, abs(Lat)));
float kerbRough = lerp(StoneRough + 0.05 + 0.3 * kJoint, SoilRough, kBack);
float plazaRough = StoneRough + RVar * (mP.g * 2.0 - 1.0) + 0.3 * lerp(mP.a, jC, compass);
float shapeRough = plazaRough * plaza + kerbRough * kerb + settsRough * setts + flagRough * flagR;
float rough = (GrassRough + RVar * (mG.g * 2.0 - 1.0)) * wg
    + lerp(lerp(StoneRough + 0.12 + RVar * (mR.g * 2.0 - 1.0), SandRough + RVar * (mS.g * 2.0 - 1.0), sandy),
           lerp(flagRough, shapeRough, onShape), paved) * ws
    + (SoilRough + RVar * 1.5 * (mD.g * 2.0 - 1.0)) * wd;
rough = lerp(rough, DeckRough + RVar * (mK.g * 2.0 - 1.0), dock);
float hw = WP.z - Water;
float swash = (1.0 - smoothstep(0.0, 25.0, hw)) * (1.0 - wg);
float damp = (smoothstep(0.0, 25.0, hw) - smoothstep(25.0, 80.0, hw)) * (1.0 - wg);
float residue = (smoothstep(21.0, 23.0, hw) - smoothstep(27.0, 29.0, hw)) * (1.0 - wg);
col *= lerp(1.0, WetDark, swash) * lerp(1.0, DampDark, damp) * (1.0 + Residue * residue * (0.4 + 0.6 * mS.a));
rough = lerp(lerp(rough, WetRough, swash), DampRough, damp);
float gilt = saturate(InlayStrength * compass * max(gRing, gHour * step(rO, $INLAY_LAST)) * plaza * onShape * paved * ws);
col = lerp(col, Inlay.rgb, gilt);
rough = lerp(rough, 0.3, gilt);
float peak = max(max(col.r, col.g), col.b);
col *= min(1.0, 0.9 / max(peak, 0.0001));
Metallic = gilt;
return float4(col, saturate(rough));''')

# GROUND_NORMAL: each layer's texture normal (xy, in its own frame: top projection, road space, the shore frame),
# whiteout-blended onto the terrain's; the lawns' and soil's 1.5 m undulation; the kerbs' rounded arrises and the
# compass stones' bevels (both fade before they are a pixel wide); rock triplanar as before.
GROUND_NORMAL = PREFIX + WEIGHTS + \
    untiled_normal('gG', 'TexGrassN', 'mG', 'uvG', 'DDX(uvG)', 'DDY(uvG)') + \
    untiled_normal('gS', 'TexSandN', 'mS', 'uvS', 'sand_dx', 'sand_dy') + \
    untiled_normal('gD', 'TexSoilN', 'mD', 'uvD', 'DDX(uvD)', 'DDY(uvD)') + \
    'float2 gF = %s.rg * 2.0 - 1.0;\nfloat2 gK = %s.rg * 2.0 - 1.0;\nfloat2 gT = %s.rg * 2.0 - 1.0;\nfloat2 gP = %s.rg * 2.0 - 1.0;\n' % (
        tap('TexFlagN', 'uvF'), tap('TexDeckN', 'uvK'), tap_grad('TexSettsN', 'uvT2', 'setts_dx', 'setts_dy'),
        tap_grad('TexPavingN', 'uvP2', 'DDX(uvP)', 'DDY(uvP)')) + \
    T.value_noise2('b1', 'p2 / 150.0 + float2(3.7, 9.2)') + _fill('''float rockw = ws * (1.0 - paved) * (1.0 - sandy) * (1.0 - dock);
float wShape = ws * paved * onShape;
float2 gTop = gG * GrassN * wg + gF * FlagN * ws * paved * lerp(1.0, flagR, onShape) + gP * PavingN * (1.0 - mP.a * compass) * wShape * plaza
    + gD * SoilN * wd * (1.0 - dock) + gK * DeckN * dock;
gTop += b1_g * (GrassBump * 0.55 * wg + SoilBump * 0.35 * wd) * saturate(150.0 / fpx * 0.25 - 1.0);
float arris = ArrisTilt * saturate(2.0 * $ARRIS / fpx - 1.0) * (smoothstep(-$ARRIS, 0.0, Road.x) - (1.0 - smoothstep(-$KERB, -$KERB + $ARRIS, Road.x))) * (1.0 - kBack);
float2 gRoad = gT * SettsN * wShape * setts + float2(0.0, sign(Lat) * arris) * wShape * kerb;
float2 gSand = gS * SandN * ws * sandy;
float2 rh = dOr / max(rO, 0.001);
float bevel = ArrisTilt * saturate(2.0 * $BEVEL / fpx - 1.0) * compass * wShape * plaza;
float2 gBevel = (rh * lerp(sign(ringF - ringI - 0.5), -1.0, edgeC) * (1.0 - smoothstep($COMPASS_JOINT * 0.5, $COMPASS_JOINT * 0.5 + $BEVEL, dJR))
    + float2(-rh.y, rh.x) * sign(frac(sa) - 0.5) * (1.0 - smoothstep($COMPASS_JOINT * 0.5, $COMPASS_JOINT * 0.5 + $BEVEL, dJA))) * bevel;
float3 top = normalize(nv + float3(1.0, 0.0, 0.0) * gTop.x + tvTop * gTop.y + float3(tu, 0.0) * gRoad.x + float3(tvR, 0.0) * gRoad.y
    + float3(suS, 0.0) * gSand.x + float3(svS, 0.0) * gSand.y + float3(gBevel, 0.0));
''') + 'float2 ax = (%s.rg * 2.0 - 1.0) * RockN;\nfloat2 ay = (%s.rg * 2.0 - 1.0) * RockN;\nfloat2 az = (%s.rg * 2.0 - 1.0) * RockN;\n' % (
        tap('TexRockN', 'pr.zy'), tap('TexRockN', 'pr.xz'), tap('TexRockN', 'pr.xy')) + '''float3 tx = float3(ax + nv.zy, sqrt(saturate(1.0 - dot(ax, ax))) * nv.x);
float3 ty = float3(ay + nv.xz, sqrt(saturate(1.0 - dot(ay, ay))) * nv.y);
float3 tz = float3(az + nv.xy, sqrt(saturate(1.0 - dot(az, az))) * nv.z);
float3 rn = normalize(tx.zyx * tw.x + ty.xzy * tw.y + tz.xyz * tw.z);
return normalize(lerp(top, rn, rockw));'''


def custom_outputs(expression, extra):
    """Gives a Custom node named outputs besides its return value (the engine's AdditionalOutputs): its code assigns
    each by name, and its first output becomes 'return'. Set before anything connects to the node's outputs."""
    entries = []
    for name, kind in extra:
        entry = unreal.CustomOutput()
        entry.set_editor_property('output_name', name)
        entry.set_editor_property('output_type', kind)
        entries.append(entry)
    expression.set_editor_property('additional_outputs', entries)
    return expression


def shared_sampler(texture):
    """The texture object's sampler source set to the shared wrap sampler (the plan's setting; the HLSL samples
    through the shared sampler itself). A refusal is reported, not raised, as master() reports its settings."""
    try:
        texture.set_editor_property('sampler_source', unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
    except Exception as error:
        T.SKIPPED.append('%s.sampler_source: %s' % (texture.get_editor_property('parameter_name'), error))


def material_ground():
    m = T.master('M_CNGround', tangent_space_normal=False)
    vc = T.node(m, unreal.MaterialExpressionVertexColor, -1700, -500)
    wp = T.node(m, unreal.MaterialExpressionWorldPosition, -1700, -350)
    vn = T.node(m, unreal.MaterialExpressionVertexNormalWS, -1700, -200)
    sets = T.detail_sets()
    masks, normals, tiles = {}, {}, {}
    for i, (short, name) in enumerate(GROUND_SETS):
        masks[short], normals[short] = T.detail_parameters(m, -2600, -1400 + i * 320, prefix=short, set_name=name)
        shared_sampler(masks[short])
        shared_sampler(normals[short])
        tiles[short] = T.scalar(m, short + 'Tile', sets.get(name, {}).get('tile_cm', TILE_FALLBACK), -2300, -1400 + i * 320)
    roads = custom_outputs(T.custom(m, roads_code(), [('WP', wp)], -2000, -800, T.FLOAT4), [('Lat', T.FLOAT1)])
    shared = [('VC', vc), ('WP', wp), ('VN', vn), ('Water', T.scalar(m, 'Water', plan.WATER * CM, -1700, -50)),
              ('DrumR', T.scalar(m, 'DrumR', plan.R * CM, -1700, 30)), ('AxisZ', T.scalar(m, 'AxisZ', plan.AXIS_Z * CM, -1700, 110)),
              ('Road', roads), ('Lat', (roads, 'Lat')),
              ('EdgeTuft', T.scalar(m, 'EdgeTuft', 8.0, -1700, 190)), ('EdgeWander', T.scalar(m, 'EdgeWander', 15.0, -1700, 270))]
    shared += [(short + 'Tile', tiles[short]) for short, _ in GROUND_SETS]
    shared += [('Tex' + short, masks[short]) for short, _ in GROUND_SETS]
    weights = T.custom(m, GROUND_W, shared + [
        ('Band', T.scalar(m, 'Band', .06, -1400, -1100)), ('BlendHeight', T.scalar(m, 'BlendHeight', .5, -1400, -1020)),
        ('BlendNoise', T.scalar(m, 'BlendNoise', .35, -1400, -940)), ('Wear', T.scalar(m, 'ShoulderWear', .35, -1400, -860))],
        -1000, -900, T.FLOAT4)
    dock = [('DockC', T.param(m, 'DockCentre', (plan.DOCKS_ARENA[0] * CM, plan.DOCKS_ARENA[1] * CM, 0.0), -1400, 900)),
            ('DockR', T.scalar(m, 'DockRadius', 6200.0, -1400, 980))]
    ground = custom_outputs(T.custom(m, GROUND, shared + dock + [('W', weights)] + [
        ('GrassVar', T.scalar(m, 'GrassVariation', .22, -1400, -780)), ('Dry', T.cparam(m, 'DryColour', T.PAL.GOLD_STRAW, -1400, -700)),
        ('DryShare', T.scalar(m, 'DryShare', .45, -1400, -620)), ('StoneVar', T.scalar(m, 'StoneVariation', .12, -1400, -540)),
        ('SoilVar', T.scalar(m, 'SoilVariation', .25, -1400, -460)), ('GrassRough', T.scalar(m, 'GrassRoughness', .9, -1400, -380)),
        ('StoneRough', T.scalar(m, 'StoneRoughness', .62, -1400, -300)), ('SandRough', T.scalar(m, 'SandRoughness', .82, -1400, -220)),
        ('SoilRough', T.scalar(m, 'SoilRoughness', .88, -1400, -140)), ('DeckRough', T.scalar(m, 'DeckRoughness', .5, -1400, -60)),
        ('RVar', T.scalar(m, 'RoughnessVariation', .12, -1400, 20)), ('Polish', T.scalar(m, 'CentrePolish', .12, -1400, 100)),
        ('GrassDetail', T.scalar(m, 'GrassDetail', .35, -1100, -780)), ('GapDark', T.scalar(m, 'GapDark', .8, -1100, -700)),
        ('FlagDetail', T.scalar(m, 'FlagDetail', .28, -1100, -620)), ('GroutDark', T.scalar(m, 'GroutDark', .55, -1100, -540)),
        ('SettsDetail', T.scalar(m, 'SettsDetail', .3, -1100, -460)), ('PavingDetail', T.scalar(m, 'PavingDetail', .25, -1100, -380)),
        ('SandDetail', T.scalar(m, 'SandDetail', .35, -1100, -300)), ('RockDetail', T.scalar(m, 'RockDetail', .35, -1100, -220)),
        ('SoilDetail', T.scalar(m, 'SoilDetail', .4, -1100, -140)), ('DeckDetail', T.scalar(m, 'DeckDetail', .3, -1100, -60)),
        ('PaveBright', T.scalar(m, 'PaveBright', .72, -1100, 20)), ('SandBright', T.scalar(m, 'SandBright', .7, -1100, 100)),
        ('WetDark', T.scalar(m, 'WetDark', .35, -1100, 180)), ('WetRough', T.scalar(m, 'WetRough', .08, -1100, 260)),
        ('DampDark', T.scalar(m, 'DampDark', .65, -1100, 340)), ('DampRough', T.scalar(m, 'DampRough', .45, -1100, 420)),
        ('Residue', T.scalar(m, 'ResidueBright', .25, -1100, 500)), ('InlayStrength', T.scalar(m, 'InlayStrength', 1.0, -1100, 580)),
        ('DarkTint', T.cparam(m, 'DarkTint', (1.0, .95, .88), -800, -780)), ('Verge', T.cparam(m, 'VergeSoil', T.PAL.grey(.045), -800, -680)),
        ('Pave', T.cparam(m, 'PaveColour', T.PAL.WHITE, -800, -580)), ('Kerb', T.cparam(m, 'KerbColour', T.PAL.ASH, -800, -480)),
        ('Course', T.cparam(m, 'CourseColour', T.PAL.SLATE, -800, -380)), ('Basalt', T.cparam(m, 'BandColour', T.PAL.CHARCOAL, -800, -280)),
        ('Inlay', T.cparam(m, 'InlayColour', T.PAL.GOLD, -800, -180))],
        -600, -500, T.FLOAT4), [('Metallic', T.FLOAT1)])
    T.lib.connect_material_property(T.mask(m, ground, 'rgb', -300, -550), '', T.PROP.MP_BASE_COLOR)
    T.lib.connect_material_property(T.mask(m, ground, 'a', -300, -420), '', T.PROP.MP_ROUGHNESS)
    T.lib.connect_material_property(ground, 'Metallic', T.PROP.MP_METALLIC)
    T.lib.connect_material_property(T.scalar(m, 'Specular', .45, -300, -300), '', T.PROP.MP_SPECULAR)
    normal = T.custom(m, GROUND_NORMAL, shared + dock + [('W', weights)] + [('Tex%sN' % short, normals[short]) for short, _ in GROUND_SETS] + [
        ('GrassN', T.scalar(m, 'GrassNormalStrength', 1.0, -1100, 700)), ('FlagN', T.scalar(m, 'FlagNormalStrength', 1.0, -1100, 780)),
        ('SandN', T.scalar(m, 'SandNormalStrength', 1.0, -1100, 860)), ('RockN', T.scalar(m, 'RockNormalStrength', 1.0, -1100, 940)),
        ('SoilN', T.scalar(m, 'SoilNormalStrength', 1.0, -1100, 1020)), ('DeckN', T.scalar(m, 'DeckNormalStrength', 1.0, -1100, 1100)),
        ('SettsN', T.scalar(m, 'SettsNormalStrength', 1.0, -1100, 1180)), ('PavingN', T.scalar(m, 'PavingNormalStrength', 1.0, -1100, 1260)),
        ('GrassBump', T.scalar(m, 'GrassBump', .35, -1100, 1340)), ('SoilBump', T.scalar(m, 'SoilBump', .4, -1100, 1420)),
        ('ArrisTilt', T.scalar(m, 'ArrisTilt', .6, -1100, 1500))],
        -600, 600, T.FLOAT3)
    T.lib.connect_material_property(normal, '', T.PROP.MP_NORMAL)
    return T.finish(m)


# ---------------------------------------------------------------- M_CNWater

# Deep-water waves (omega^2 = g k), 1.1 to 6 m long in five directions, and two long swells. The 37-71 cm waves are
# gone: at 50-150 m they drew concentric moire. Each fades out as its wavelength shrinks from 8 to 4 pixels, as
# physis_conclave_tools.wave_gradient() does, and the slope it loses goes into roughness, so the water far off is a
# soft mirror of the drum instead of a shimmer. (dx, dy, wavelength cm, slope amplitude)
WATER_WAVES = ((0.17, 0.99, 113.0, .035), (-0.88, -0.47, 167.0, .03), (0.72, 0.69, 241.0, .025),
               (-0.25, -0.97, 389.0, .02), (0.99, -0.12, 613.0, .015), (0.8, 0.6, 900.0, .01), (-0.5, 0.87, 1400.0, .01))
# Capillary ripples: the Ripple set's normal twice, the second smaller (0.61 of the tile) and turned 37 degrees, both
# drifting; they fade like a 3 m wave.
CAPILLARY_TURN, CAPILLARY_SCALE = math.radians(37.0), .61
CAPILLARY_DRIFT = ((0.021, 0.013), (-0.017, -0.011))   # tiles per second (at RippleSpeed 1)


def ripple_code():
    """The water's normal (return) and its roughness with the faded waves' slope folded in (output WaveRough)."""
    code = ('float2 wp = WP.xy;\nfloat tt = T * Speed;\nfloat fpx = max(max(length(DDX(WP)), length(DDY(WP))), 0.001);\n'
            'float2 g = float2(0.0, 0.0);\nfloat lost = 0.0;\nfloat ph; float fade;\n')
    for k, (dx, dy, length, amp) in enumerate(WATER_WAVES):
        norm = math.hypot(dx, dy)
        dx, dy = dx / norm, dy / norm
        wave = 2 * math.pi / length
        code += ('fade = saturate(%.1f / (4.0 * fpx) - 1.0); ph = dot(wp, float2(%.5f, %.5f)) * %.6f - tt * %.5f + %.3f;\n'
                 'g += float2(%.5f, %.5f) * (cos(ph) * %.4f * fade); lost += %.8f * (1.0 - fade);\n'
                 % (length, dx, dy, wave, math.sqrt(981.0 * wave), k * 1.37, dx, dy, amp, amp * amp))
    c, s = math.cos(CAPILLARY_TURN), math.sin(CAPILLARY_TURN)
    (u1, v1), (u2, v2) = CAPILLARY_DRIFT
    code += ('float cfade = saturate(Tile / (4.0 * fpx) - 1.0) * Detail;\n'
             'float2 c1 = Texture2DSample(TexR, TexRSampler, wp / Tile + tt * float2(%.4f, %.4f)).rg * 2.0 - 1.0;\n'
             'float2 q2 = float2(dot(wp, float2(%.6f, %.6f)), dot(wp, float2(%.6f, %.6f)));\n'
             'float2 c2 = Texture2DSample(TexR, TexRSampler, q2 / (Tile * %.3f) + tt * float2(%.4f, %.4f)).rg * 2.0 - 1.0;\n'
             'float2 cap = (c1 + float2(c2.x * %.6f + c2.y * %.6f, c2.y * %.6f - c2.x * %.6f)) * cfade;\n'
             % (u1, v1, c, -s, s, c, CAPILLARY_SCALE, u2, v2, c, s, c, s))
    # The texture holds the normal's xy (minus the slope), the waves their slope: both made a slope before the bend.
    return code + '''WaveRough = sqrt(R0 * R0 + 2.0 * K * K * lost);
float3 n = normalize(VN);
float3 gg = float3(g * K - cap, 0.0);
gg -= dot(gg, n) * n;
return normalize(n - gg);'''


# The water's vertical depth under this pixel (cm): the scene depth behind it less its own, along the view ray (the
# depths are along the camera's axis), times the ray's vertical share.
WATER_DEPTH = '''float3 v = normalize(V);
float along = max(dot(-v, normalize(Fwd)), 0.05);
return max(SD - PD, 0.0) / along * abs(v.z);'''
# Colour, opacity, roughness and refraction from that depth: light blue only in the shallow fringe over white sand, a
# dark neutral mirror beyond (light blue over the black silt rendered navy); clarity by Beer's law, Fresnel on top;
# a lap line of foam a few centimetres wide where the water thins out, breathing with the wavelets; refraction growing
# from nothing at the edge (so the shoreline never tears) to IOR at a metre.
WATER_SHADE = T.value_noise2('nf', 'WP.xy / 40.0 + T * 0.05') + '''float op = saturate(MaxOp * (1.0 - exp(-D / max(Clarity, 0.01))) + FO * F);
float fw = max(FoamW * (1.5 + 0.5 * sin(T * 0.8 + 6.0 * nf)), 0.01);
float foam = saturate(FoamS * (1.0 - smoothstep(0.0, fw, D)) * saturate(1.5 * nf));
op = max(op, 0.9 * foam);
float3 col = lerp(WaterC.rgb, BodyC.rgb, saturate(D / max(TintD, 0.01)));
col = lerp(col, FoamC.rgb, foam);
FinalRough = lerp(R, 0.6, foam);
Refract = lerp(1.0, IOR, saturate(D / 100.0));
return float4(col, op);'''


def material_water():
    """M_CNWater. Its parameters are the contract MI_CN_Water and MI_CN_WaterBasin set (the defaults are the lake):
    Ripple, RippleSpeed, RippleDetail, Clarity, MaxOpacity, FresnelOpacity, TintDepth, Specular, Roughness, FoamWidth,
    FoamStrength, IOR; WaterColour, BodyColour, FoamColour."""
    m = T.master('M_CNWater', blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, two_sided=True, tangent_space_normal=False,
                 translucency_lighting_mode=unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING,
                 screen_space_reflections=True, compute_fog_per_pixel=True,
                 refraction_method=unreal.RefractionMode.RM_PIXEL_NORMAL_OFFSET)
    wp = T.node(m, unreal.MaterialExpressionWorldPosition, -1500, -300)
    time = T.node(m, unreal.MaterialExpressionTime, -1500, -200)
    ripple = T.detail_sets().get('Ripple', {}).get('tile_cm', 300)
    surface = custom_outputs(T.custom(m, ripple_code(), [
        ('WP', wp), ('T', time), ('VN', T.node(m, unreal.MaterialExpressionVertexNormalWS, -1500, -100)),
        ('K', T.scalar(m, 'Ripple', .3, -1200, -400)), ('Speed', T.scalar(m, 'RippleSpeed', 1.0, -1200, -320)),
        ('Detail', T.scalar(m, 'RippleDetail', .35, -1200, -240)), ('Tile', T.scalar(m, 'RippleTile', ripple, -1200, -160)),
        ('R0', T.scalar(m, 'Roughness', .02, -1200, -80)),
        ('TexR', T.node(m, unreal.MaterialExpressionTextureObjectParameter, -1500, -500, parameter_name='RippleNormal',
                        texture=T.detail_texture('Ripple', 'N'), sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL))],
        -800, -300, T.FLOAT3), [('WaveRough', T.FLOAT1)])
    T.lib.connect_material_property(surface, '', T.PROP.MP_NORMAL)
    forward = T.node(m, unreal.MaterialExpressionConstant3Vector, -1500, 250, constant=unreal.LinearColor(0.0, 0.0, 1.0, 0.0))
    depth = T.custom(m, WATER_DEPTH, [
        ('SD', T.node(m, unreal.MaterialExpressionSceneDepth, -1500, 100)), ('PD', T.node(m, unreal.MaterialExpressionPixelDepth, -1500, 170)),
        ('V', T.node(m, unreal.MaterialExpressionCameraVectorWS, -1500, 330)),
        ('Fwd', T.transform(m, forward, (unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_VIEW,
                                         unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD), -1250, 250))],
        -1000, 150, T.FLOAT1)
    shade = custom_outputs(T.custom(m, WATER_SHADE, [
        ('D', depth), ('F', T.node(m, unreal.MaterialExpressionFresnel, -1000, 300, exponent=5.0)), ('WP', wp), ('T', time),
        ('R', (surface, 'WaveRough')),
        ('MaxOp', T.scalar(m, 'MaxOpacity', .75, -1000, 400)), ('Clarity', T.scalar(m, 'Clarity', 120.0, -1000, 480)),
        ('FO', T.scalar(m, 'FresnelOpacity', .6, -1000, 560)), ('TintD', T.scalar(m, 'TintDepth', 20.0, -1000, 640)),
        ('FoamW', T.scalar(m, 'FoamWidth', 3.0, -1000, 720)), ('FoamS', T.scalar(m, 'FoamStrength', 1.0, -1000, 800)),
        ('IOR', T.scalar(m, 'IOR', 1.33, -1000, 880)),
        ('WaterC', T.cparam(m, 'WaterColour', T.PAL.BLUE_ICE, -700, 400)), ('BodyC', T.cparam(m, 'BodyColour', T.PAL.grey(.02), -700, 500)),
        ('FoamC', T.cparam(m, 'FoamColour', T.PAL.WHITE_PURE, -700, 600))],
        -500, 300, T.FLOAT4), [('FinalRough', T.FLOAT1), ('Refract', T.FLOAT1)])
    T.lib.connect_material_property(T.mask(m, shade, 'rgb', -200, 250), '', T.PROP.MP_BASE_COLOR)
    T.lib.connect_material_property(T.mask(m, shade, 'a', -200, 350), '', T.PROP.MP_OPACITY)
    T.lib.connect_material_property(shade, 'FinalRough', T.PROP.MP_ROUGHNESS)
    T.lib.connect_material_property(shade, 'Refract', T.PROP.MP_REFRACTION)
    T.lib.connect_material_property(T.scalar(m, 'Specular', .35, -200, 500), '', T.PROP.MP_SPECULAR)
    return T.finish(m)
