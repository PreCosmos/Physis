"""The living animals of the other four worlds: local species on the body plans of Arche's air-swimmers.

Author, 2026-11-17: "We need some organic enemies in all levels with physical attacks. Arche has been taken care of.
Do the rest." and, asked how: local species on shared plans, added as new packs. So each world has three species of its
own, and each is one of creatures.py's builds (the same mesh, bones, skin weights and the two animations, Swim and
Strike) given that world's proportions and colours:

  the station (Meridian)   SM_AE_BreachMite     Mote plan       pale ash hide, amber lights      swarm, darting bite
                           SM_AE_CoolantBell    Medusa plan     grey-teal bell, teal lights      turns and lashes
                           SM_AE_HullLimpet     Shellback plan  gunmetal shell, amber seams      armoured, rams
  the Center               SM_AE_LanternAngel   Mote plan       pearl hide, cyan and rose light  swarm, darting bite
                           SM_AE_GlassRay       Ray plan        frost-blue wing, rose wounds     fast, tail whip
                           SM_AE_MarshStalker   Stalker plan    deep teal hide, rose fractures   rears and bites
  the Conclave             SM_AE_GoldgrassMote  Mote plan       straw-gold hide, warm lights     swarm, darting bite
                           SM_AE_ReservoirBell  Medusa plan     green-bronze bell, gold lights   turns and lashes
                           SM_AE_TerraceRay     Ray plan        bronze-green wing, red wounds    fast, tail whip
  the Grove (Earth)        SM_AE_Blightfly      Mote plan       bark-brown hide, sick green      swarm, darting bite
                           SM_AE_Burlback       Shellback plan  bark shell, moss, blight violet  armoured, rams
                           SM_AE_CanopyStalker  Stalker plan    moss-green hide, blight violet   rears and bites

A species is a recolour by material slot and a rescale of the whole build, bones included, so it wears the same
materials as Arche's animals (the vertex colour is the albedo and the light) and needs no Blueprint of its own:
BP_TrainingDrone's Organic, Animal (the plan's number, for how the body moves) and Reach do the rest.
  hide, horn and frills   a gradient from the species' dark to its light by the old colour's brightness, so backs stay
                          dark and bellies pale
  light and crystal       Arche's ice blue becomes the species' own light, Arche's violet (the Lens's unweaving) the
                          colour of what has hurt it here

    P=Saved/AudioTools/kokoro_venv/lib/python3.14/site-packages
    PYTHONPATH=$P python3 Tools/arche_meshes/check.py fauna --preview
"""
from kit import *
import creatures

# plan -> (builder, BP_TrainingDrone.Animal, how far its blow reaches from its middle at scale 1, cm)
PLANS = {'mote': (creatures.mote, 1, 230.0), 'medusa': (creatures.medusa, 2, 300.0), 'shellback': (creatures.shellback, 3, 300.0),
         'ray': (creatures.ray, 4, 330.0), 'stalker': (creatures.stalker, 5, 350.0), 'leviathan': (creatures.leviathan, 6, 800.0)}


def c3(r, g, b):
    return np.array([r, g, b], np.float64)


# name: (plan, scale (x, y, z), hide dark, hide light, horn dark, horn light, own light, wound light, own crystal, wound crystal)
SPECIES = {
    # Meridian Station: things of the dark between ships, come in through the breach after the Divinity in the reactor.
    'SM_AE_BreachMite': ('mote', (1.0, 1.1, .9), c3(.10, .10, .11), c3(.62, .60, .56), c3(.05, .05, .06), c3(.34, .33, .31),
                         c3(1.0, .62, .22), c3(1.0, .25, .10), c3(.74, .70, .60), c3(.90, .50, .25)),
    'SM_AE_CoolantBell': ('medusa', (.62, .62, .58), c3(.07, .12, .13), c3(.50, .60, .60), c3(.05, .07, .08), c3(.30, .36, .37),
                          c3(.30, 1.0, .85), c3(1.0, .55, .18), c3(.45, .80, .78), c3(.90, .60, .30)),
    'SM_AE_HullLimpet': ('shellback', (.78, .86, .74), c3(.07, .08, .09), c3(.46, .47, .49), c3(.06, .065, .075), c3(.40, .41, .44),
                         c3(1.0, .62, .22), c3(1.0, .25, .10), c3(.60, .62, .66), c3(.90, .50, .25)),
    # The Center: creatures of its living crystal that have strayed too near the wounds.
    'SM_AE_LanternAngel': ('mote', (1.1, 1.25, 1.0), c3(.10, .16, .22), c3(.72, .76, .80), c3(.06, .09, .12), c3(.44, .50, .56),
                           c3(.40, .95, 1.0), c3(1.0, .30, .45), c3(.62, .86, .92), c3(.95, .45, .60)),
    'SM_AE_GlassRay': ('ray', (.92, .9, .92), c3(.07, .13, .20), c3(.62, .74, .82), c3(.05, .08, .12), c3(.40, .50, .58),
                       c3(.40, .95, 1.0), c3(1.0, .30, .45), c3(.60, .84, .92), c3(.95, .45, .60)),
    'SM_AE_MarshStalker': ('stalker', (.9, .9, .9), c3(.03, .11, .13), c3(.44, .62, .60), c3(.03, .06, .07), c3(.34, .42, .42),
                           c3(.40, .95, 1.0), c3(1.0, .30, .45), c3(.50, .82, .86), c3(.95, .45, .60)),
    # The Conclave: the Wise's garden and reservoir stock, driven wild by the swarm's noise.
    'SM_AE_GoldgrassMote': ('mote', (.95, 1.0, .95), c3(.16, .12, .05), c3(.74, .64, .36), c3(.09, .07, .04), c3(.46, .40, .26),
                            c3(1.0, .84, .45), c3(1.0, .16, .10), c3(.86, .78, .52), c3(.90, .30, .22)),
    'SM_AE_ReservoirBell': ('medusa', (.85, .85, .8), c3(.06, .13, .09), c3(.52, .62, .46), c3(.06, .08, .05), c3(.38, .40, .28),
                            c3(1.0, .84, .45), c3(1.0, .16, .10), c3(.62, .82, .62), c3(.90, .30, .22)),
    'SM_AE_TerraceRay': ('ray', (.8, .8, .8), c3(.09, .12, .06), c3(.58, .58, .38), c3(.07, .08, .05), c3(.42, .40, .28),
                         c3(1.0, .84, .45), c3(1.0, .16, .10), c3(.70, .80, .56), c3(.90, .30, .22)),
    # The Grove: the valley's own animals, forty years under the Array's discharges.
    'SM_AE_Blightfly': ('mote', (1.05, .95, .9), c3(.06, .045, .03), c3(.44, .36, .24), c3(.04, .03, .02), c3(.30, .25, .17),
                        c3(.62, 1.0, .35), c3(.72, .35, 1.0), c3(.56, .70, .40), c3(.62, .42, .86)),
    'SM_AE_Burlback': ('shellback', (1.0, 1.05, .95), c3(.055, .04, .028), c3(.40, .33, .22), c3(.05, .038, .026), c3(.36, .29, .19),
                       c3(.62, 1.0, .35), c3(.72, .35, 1.0), c3(.44, .60, .34), c3(.62, .42, .86)),
    'SM_AE_CanopyStalker': ('stalker', (1.0, 1.0, 1.0), c3(.035, .07, .03), c3(.42, .50, .28), c3(.04, .04, .025), c3(.34, .31, .21),
                            c3(.62, 1.0, .35), c3(.72, .35, 1.0), c3(.46, .66, .38), c3(.62, .42, .86)),
    # The elemental monsters (author, 2026-11-17: "monsters in all the levels with physical attacks and attacks like fire,
    # ice, thunder, wind and dark and light"). One of each element, the same animal in every world it is found in; each
    # wears its element: a charred hide lit from inside, a rimed shell, a storm-dark wing with bright cells, a pale
    # swollen air sac, a light-drinking black bell, a small ivory whale that glows.
    'SM_AE_PyreStalker': ('stalker', (1.15, 1.15, 1.15), c3(.018, .012, .010), c3(.30, .12, .05), c3(.03, .02, .015), c3(.34, .22, .12),
                          c3(1.0, .34, .04), c3(1.0, .80, .20), c3(.95, .40, .10), c3(1.0, .75, .25)),
    'SM_AE_Rimeback': ('shellback', (1.1, 1.15, 1.05), c3(.16, .22, .30), c3(.74, .82, .88), c3(.22, .30, .38), c3(.80, .86, .90),
                       c3(.55, .92, 1.0), c3(.85, .95, 1.0), c3(.70, .88, .96), c3(.86, .93, .98)),
    'SM_AE_StormRay': ('ray', (1.1, 1.1, 1.1), c3(.03, .035, .08), c3(.34, .36, .50), c3(.03, .03, .06), c3(.30, .30, .40),
                       c3(1.0, .95, .35), c3(.60, .80, 1.0), c3(.90, .88, .50), c3(.60, .78, 1.0)),
    'SM_AE_GaleMote': ('mote', (1.5, 1.9, 1.6), c3(.20, .24, .26), c3(.80, .84, .82), c3(.12, .15, .16), c3(.52, .56, .55),
                       c3(.75, 1.0, .82), c3(.90, 1.0, .95), c3(.78, .92, .86), c3(.90, .96, .92)),
    'SM_AE_UmbraBell': ('medusa', (1.0, 1.0, .95), c3(.006, .004, .012), c3(.12, .07, .18), c3(.008, .006, .014), c3(.10, .07, .14),
                        c3(.55, .10, .85), c3(.90, .15, .60), c3(.16, .06, .26), c3(.50, .12, .55)),
    'SM_AE_DawnCalf': ('leviathan', (.32, .32, .32), c3(.36, .30, .20), c3(.88, .84, .72), c3(.30, .25, .16), c3(.80, .74, .58),
                       c3(1.0, .97, .78), c3(1.0, .82, .40), c3(.92, .90, .78), c3(1.0, .86, .52)),
}
LUMA = np.array([.2126, .7152, .0722])


def species(name):
    plan, scale, hide_dark, hide_light, horn_dark, horn_light, light_own, light_wound, crystal_own, crystal_wound = SPECIES[name]
    part = PLANS[plan][0]()
    part.name = name
    scale = np.asarray(scale, np.float64)
    part.v = (np.asarray(part.v, np.float64) * scale).tolist()
    if getattr(part, 'normals', None) is not None:
        normals = np.asarray(part.normals, np.float64) / scale
        part.normals = (normals / np.maximum(norm(normals, axis=1, keepdims=True), 1e-12)).tolist()
    rig = part.rig
    rig['bones'] = [(bone, parent, np.asarray(head, np.float64) * scale, np.asarray(tail, np.float64) * scale) for bone, parent, head, tail in rig['bones']]
    # The slot of each vertex (a vertex belongs to the faces of one slot).
    slot = np.full(len(part.v), -1)
    for face, index in zip(part.f, part.m):
        slot[face] = index
    colours = np.asarray(part.c, np.float64)
    rgb = colours[:, :3]
    out = rgb.copy()
    luma = rgb @ LUMA
    peak = np.maximum(rgb.max(1), 1e-6)
    # How violet a light or a crystal is: Arche's own light has more green than red, the Lens's violet more red.
    wound = np.clip(((rgb[:, 0] - rgb[:, 1]) / peak + .1) / .25, 0, 1)[:, None]
    for index, material in enumerate(part.slots):
        mine = slot == index
        if material in (GLOW, CRYSTAL):
            own, hurt = (light_own, light_wound) if material == GLOW else (crystal_own, crystal_wound)
            out[mine] = (peak[:, None] * (own * (1 - wound) + hurt * wound))[mine]
        else:
            dark, light = (horn_dark, horn_light) if material == ROCK else (hide_dark, hide_light)
            t = np.clip((luma - .015) / .42, 0, 1)[:, None] ** .8
            out[mine] = (dark * (1 - t) + light * t)[mine]
    colours[:, :3] = np.clip(out, 0, None)
    part.c = colours.tolist()
    return part


def _builder(name):
    def build():
        return species(name)
    build.__name__ = name[6:].lower()
    return build


MESHES = [_builder(name) for name in SPECIES]
CONTRACT = {name: {'size': (0, 0, 0), 'tol': .1, 'pivot': 'centre'} for name in SPECIES}


def table():
    """name: (plan, Animal number, reach in cm at its scale) for the scenario side (Content/Python/physis_fauna.py
    keeps a copy, since the editor's Python has no numpy)."""
    return {name: (row[0], PLANS[row[0]][1], round(PLANS[row[0]][2] * float(np.mean(row[1])))) for name, row in SPECIES.items()}


if __name__ == '__main__':
    for _name, _row in table().items():
        print(_name, _row)
