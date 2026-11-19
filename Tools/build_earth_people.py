"""Earth's people's costumes (Content/Python/physis_earth_people.py: Commodore Marr, Edda Holt, Corin Vell, Warden
Maren Holt), by the Conclave's costume build (Tools/build_conclave_people.py) with their entries added to its tables.

  /usr/bin/blender -b --factory-startup --python-exit-code 1 --python Tools/build_earth_people.py -- Marr [Edda ...]
      in Blender, headless: needs each person's guides (earth:people_guides:<Key>); writes their costume FBX and cloth
      mask beside them (Art/Characters/Conclave/<Key>), for earth:people_import:<Key>
  python3 Tools/build_earth_people.py --test [Key ...]
      offline, no Blender: every costume on its stand-in guide, with check.py's mesh rules and the costume checks

Two things the Conclave's build does not do, both read from the entries:
  recolour  a ported garment keeps the colours it was modelled in, so its builder runs with the palette names it
            draws in bound to others for that one call ({'WHITE_COOL': 'BLACK'} turns the doctor's white coat black;
            the shading the builder paints, folds and hems, is kept, since it multiplies whatever colour it is given)
  reslot    material slots renamed on the built piece (the oilskin's light-blue body is drawn in CN_Blue; ochre cloth
            belongs in CN_Cloth)
and one garment of its own, SM_EP_G_OfficerCoat: the doctor's coat (costumes.coat_white) without her pens and
stethoscope, its buttons brass on CN_Gold.
"""
import functools
import math
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Content/Python'))
sys.path.insert(0, str(ROOT / 'Tools/conclave_meshes'))

import costumes  # noqa: E402  (before install(): people.py checks the cast against the Conclave's lore as it loads)
import numpy as np  # noqa: E402
import physis_earth_people as earth  # noqa: E402
from palette import PALETTE  # noqa: E402

import people as P  # noqa: E402  (already loaded by costumes: its garment helpers)

keys = earth.install()
PALETTE.update(earth.EXTRA_PALETTE)
OFFICER, GREATCOAT, CAP = 'SM_EP_G_OfficerCoat', 'SM_EP_G_GreatcoatSkirt', 'SM_EP_G_OfficerCap'


def officer_coat(m):
    """The body of an officer's coat of the Just: Doctor Okafor's coat (costumes.coat_white) cut the same, right over
    left, notched lapels, a breast pocket, three buttons, without her pens and stethoscope; the buttons are brass
    (WHITE_PURE, which the entry recolours) on the gold slot. Its colours are read from costumes' palette names at the
    call, so an entry's recolour reaches them."""
    c = costumes
    g, seed = m.g, 283
    cloth, button = c.WHITE_COOL, c.WHITE_PURE
    p = c.Part('coat', ('CN_Cloth', 'CN_Gold'))
    thick = .006
    dr = m.torso(((1.05, .02), (1.12, .015), (1.3, .012), (1.45, .010), (1.5, .004)), taut=True, wrinkle=.0009, seed=seed)
    z_break = m.z(1.19)
    fronts = c.front_edges(g, dr, z_break, .3, -1, thick)
    right_edge, left_edge, lift = fronts
    top = c.bodice(p, g, dr, cloth, 'CN_Cloth', thick=thick, z_bot=m.z(1.05), fronts=fronts, seed=seed)
    z_sh = top['z_sh']
    rise = np.linspace(z_break, z_sh, 40)
    cross = float(np.interp(0., [float(-left_edge(z)) for z in rise], rise))
    c._lapels(p, dr, fronts, {1: z_break, -1: cross + .01}, z_sh - .012, .4, .004, cloth, 'CN_Cloth', k=.94)
    th_end = top['th_neck'] - .03
    a_mid = max(.9, th_end + .1)
    c._collar(p, dr, th_end, c.collar_seam(g, dr, [th_end, math.pi / 2, math.pi], [z_sh - .022, m.z(1.49), m.z(1.452)], m.z(1.47)),
              lambda a: np.interp(a, [th_end, a_mid, math.pi / 2, math.pi], [z_sh + .018, m.z(1.515), m.z(1.545), m.z(1.52)]), .006, .005,
              cloth, 'CN_Cloth', stand=.008, k=.93, knots=(math.pi - top['th_neck'], math.pi + top['th_neck']))
    for z in list(m.z((1.08, 1.135))) + [z_break - .005]:
        e = float(lift(np.array(0.), np.array(z), 1)) + .0005
        c._button(p, dr.at(0., z, extra=e), dr.normal(0., z, e), .0075, button, 'CN_Gold', k=1.0)
    c._patch(p, dr, -.95, -.5, m.z(1.2), m.z(1.29), .0026, .003, cloth, 'CN_Cloth', 6, 4, k=.95, bulge=.003, fold=0.)
    return p, c._form(top, z_break)


def greatcoat_skirt(m):
    """The skirt of a field greatcoat: Doctor Okafor's coat skirt (costumes.coat_skirt_white) carried on from the knee
    to mid-calf (the Mannequin's .36 m, where Maren's Stilled figure's coat ends), the same pockets, buttons, half-belt
    and back vent. Colours read from costumes' palette names at the call, as officer_coat's."""
    c = costumes
    cloth, button = c.WHITE_COOL, c.WHITE_PURE
    hem = .36
    p = c.Part('coat_skirt', ('CN_Cloth', 'CN_Lacquer'))
    dr = m.drape(((1.075, .144, .108, -.100), (1.0, .170, .110, -.120), (.94, .190, .112, -.138), (.88, .198, .118, -.146),
                  (.80, .203, .128, -.152), (.72, .207, .140, -.160), (.60, .225, .160, -.176), (.50, .240, .176, -.190),
                  (.43, .249, .185, -.197), (hem, .258, .194, -.204)),
                 folds=8, amp=.02, fold_top=.84, fold_low=hem, wrinkle=.001, seed=113, spare=.008, taut=True)
    span = c._coat_span(m.z([hem, .82, .9, 1.08]), [-.3, -.04, .3, .3])
    c._skirt(p, dr, cloth, 'CN_Cloth', m.z(1.075), m.z(hem), nu=60, nv=19, thick=.006, span=span, lap=-1, seed=113)
    for z in m.z((.955, .89)):
        c._button(p, dr.at(0.0, z, extra=.0092), dr.normal(0.0, z, .0092), .0075, button, 'CN_Lacquer', k=.95)
    for s in (-1, 1):
        c._patch(p, dr, s * .55, s * 1.05, m.z(.77), m.z(.905), .0032, .0028, cloth, 'CN_Cloth', 7, 5, k=.96)
        c._patch(p, dr, s * .55, s * 1.05, m.z(.89), m.z(.905), .0062, .0022, cloth, 'CN_Cloth', 7, 2, k=.9)
    c._patch(p, dr, math.pi - .6, math.pi + .6, m.z(1.0), m.z(1.04), .0032, .004, cloth, 'CN_Cloth', 9, 3, k=.94, fold=0.)
    for s in (-1, 1):
        z = m.z(1.02)
        c._button(p, dr.at(math.pi + s * .5, z, extra=.0075, fold=0.), dr.normal(math.pi + s * .5, z, .0075, 0.), .007, button, 'CN_Lacquer',
                  k=.95)
    c._patch(p, dr, math.pi - .03, math.pi + .1, m.z(hem), m.z(.62), .0028, .004, cloth, 'CN_Cloth', 4, 7, k=.85)
    return p, dict(kind='coat', top=m.z(1.075), hem=m.z(hem), closed_to=m.z(.82))


def officer_cap(m, grow):
    """An officer's peaked cap of the Just, as Maren's Stilled figure wears it (Tools/morrow_meshes/figures.py,
    'officer'): a stiff band at the brow, the crown flaring to a flat top wider than the band and raised at the front,
    a black lacquered peak, a gold chin cord across the band's front and a gold badge above it. The cloth is
    WHITE_COOL and the cord and badge WHITE_PURE, for the entry's recolour; the peak stays BLACK."""
    c = costumes
    cloth, trim = c.WHITE_COOL, c.WHITE_PURE
    p = c.Part('cap', ('CN_Cloth', 'CN_Lacquer', 'CN_Gold'))
    head = m.skull(grow)
    (cx, cy, cz), fr, bk, hw, up = head
    band_z = m.hz(1.722, grow)
    psi = math.asin(min(.99, (band_z - cz) / up))
    rx_f, rx_b, ry = fr * math.cos(psi) + .008, bk * math.cos(psi) + .008, hw * math.cos(psi) + .008
    nu = 64
    phi = np.linspace(-math.pi, math.pi, nu, endpoint=False)
    cs, sn = np.cos(phi), np.sin(phi)
    r_band = 1 / np.sqrt((cs / np.where(cs >= 0, rx_f, rx_b)) ** 2 + (sn / ry) ** 2)
    front = np.clip(cs, 0, 1) ** 2
    band_h = .042 * m.kh
    rise = (.012 + .03 * front) * m.kh             # the crown's lift over the band, most at the front
    flare = 1.17 + .05 * front                       # the top's reach over the band's
    rows = []
    for t in np.linspace(0, 1, 4):                   # the band, straight up from its lower edge
        rows.append(np.stack([cx + r_band * cs, cy + r_band * sn, band_z + band_h * t + 0 * phi], -1))
    for t in np.linspace(.25, 1, 4):                 # the crown wall, out and up to the top's edge
        r = r_band * (1 + (flare - 1) * t ** .7)
        rows.append(np.stack([cx + r * cs, cy + r * sn, band_z + band_h + rise * t ** 1.3], -1))
    edge = band_z + band_h + rise
    for t in (.12, .35, .6, .85):                    # the top, nearly flat, falling a little toward the back
        r = r_band * flare * (1 - t)
        rows.append(np.stack([cx + r * cs, cy + r * sn, edge + .004 * t - .006 * t * (1 - front)], -1))
    P._sheet(p, np.array(rows[::-1]), .004, cloth, 'CN_Cloth', P._hat_out(cx, cy, band_z), k=.95, closed=True, close_top=True)
    P._peak(p, head, band_z + .006, .062 * m.kh, .02, 1.05, .004, c.BLACK, 'CN_Lacquer', k=1.0)
    # The chin cord across the band's front, between two small buttons at its ends, and the badge above it.
    ends = (-1.05, 1.05)
    arc = np.linspace(ends[0], ends[1], 15)
    rf = 1 / np.sqrt((np.cos(arc) / rx_f) ** 2 + (np.sin(arc) / ry) ** 2) + .0035
    cord = np.stack([cx + rf * np.cos(arc), cy + rf * np.sin(arc), band_z + .011 + 0 * arc], -1)
    P._limb(p, cord, .0018, trim, 'CN_Gold', 5, 1.0)
    for a in ends:
        r = 1 / math.sqrt((math.cos(a) / rx_f) ** 2 + (math.sin(a) / ry) ** 2) + .003
        P._shell(p, (cx + r * math.cos(a), cy + r * math.sin(a), band_z + .011), (.0035, .0035, .0035), trim, 'CN_Gold', 1.0, 8, 4)
    P._shell(p, (cx + rx_f + .0035, cy, band_z + band_h * .62), (.003, .011, .009), trim, 'CN_Gold', 1.0, 12, 6)
    return p, dict(kind='head')


def recoloured(builder, recolour, reslot):
    """builder run with costumes' palette names rebound for the call, its slots renamed after; keeps builder's name
    (the sleeves' ease is looked up by the top's builder name)."""
    @functools.wraps(builder)
    def build(*args):
        kept = {name: getattr(costumes, name) for name in recolour}
        try:
            for name, to in recolour.items():
                setattr(costumes, name, PALETTE[to])
            part, form = builder(*args)
        finally:
            for name, value in kept.items():
                setattr(costumes, name, value)
        if reslot:
            part.slots = [reslot.get(slot, slot) for slot in part.slots]
        return part, form
    return build


costumes.PORTS.update({OFFICER: officer_coat, GREATCOAT: greatcoat_skirt, CAP: officer_cap})
costumes.BUILT.update({OFFICER: costumes.BUILT['SM_CP_G_CoatWhite'], GREATCOAT: costumes.BUILT['SM_CP_G_CoatSkirtWhite'],
                       CAP: costumes.BUILT['SM_CP_G_FieldHat']})
costumes.HEADWEAR = costumes.HEADWEAR + (officer_cap,)
costumes.SLEEVE_EASE['officer_coat'] = costumes.SLEEVE_EASE['coat_white']
for key in keys:
    costumes.CONTRACT[costumes.FILES['costume'].format(key=key).rsplit('/', 1)[1]] = {'pivot': 'any'}

_costume = costumes.costume


def costume(key, guide):
    """costumes.costume, with key's recoloured ports in place for its one call."""
    kept, headwear = dict(costumes.PORTS), costumes.HEADWEAR
    try:
        for spec in costumes.MH[key]['costume']:
            if spec.get('recolour') or spec.get('reslot'):
                original = kept[spec['port']]
                costumes.PORTS[spec['port']] = recoloured(original, spec.get('recolour', {}), spec.get('reslot', {}))
                if original in headwear:   # costume() passes a hat its hair depth: it knows hats by identity
                    costumes.HEADWEAR = costumes.HEADWEAR + (costumes.PORTS[spec['port']],)
        return _costume(key, guide)
    finally:
        costumes.PORTS.clear()
        costumes.PORTS.update(kept)
        costumes.HEADWEAR = headwear


costumes.costume = costume


def test(only):
    """Every costume on its stand-in guide: costumes.costume_problems and check.py's rules. Returns the problems."""
    from check import check_part
    problems = []
    for key in only or keys:
        guide = costumes.standin_guide(key)
        made = costumes.costume(key, guide)
        found = []
        check_part(made.part, costumes.CONTRACT, found, True)
        found += costumes.costume_problems(made, guide)
        hidden = float(np.mean(made.covered))
        print('%-6s %6d vertices, %d pieces, %.0f%% of the guide hidden%s' % (key, len(made.part.v), len(made.pieces), 100 * hidden,
                                                                          '' if not found else ': ' + '; '.join(found)))
        problems += found
    return problems


if __name__ == '__main__' and '--test' in sys.argv:
    wanted = [a for a in sys.argv[1:] if a in keys]
    sys.exit(1 if test(wanted) else 0)

if __name__ == '__main__':
    asked = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if not asked or any(a not in keys for a in asked):
        raise SystemExit('usage: blender -b --python Tools/build_earth_people.py -- <%s> [...]' % '|'.join(keys))
    sys.argv = [a for a in sys.argv if a != '--'] + ['--'] + asked
    runpy.run_path(str(ROOT / 'Tools/build_conclave_people.py'), run_name='__main__')
