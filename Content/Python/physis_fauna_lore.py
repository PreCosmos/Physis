"""The living animals of the station, the Center, the Conclave and the Grove: their meshes, numbers and Logbook text.

Author, 2026-11-17: "We need some organic enemies in all levels with physical attacks. Arche has been taken care of. Do
the rest." Each world has three species of its own on the body plans of Arche's air-swimmers
(Tools/arche_meshes/fauna.py builds them; the mesh names here are that file's). They fight as Arche's animals do: with
their bodies, never with fire (BP_TrainingDrone Organic, Animal, Reach; Tools/blueprint_logic/arche_shared.py animals).

Everything written here is Proposed, for the author to review: the species, their names, where each comes from and
every line of Logbook text. The game's rule for the living holds (GAME_ROADMAP.md): they are not destroyed, they
scatter and gather again.

FAUNA[world] is a list by tier (1 the swarm animal, 2, 3): mesh, health, hover height over the ground (cm), EnemyKind
(0 plain, 1 turns light blows, 3 fast), BP_TrainingDrone.Animal (the body plan: 1 Mote, 2 Medusa, 3 Shellback, 4 Ray,
5 Stalker), Reach (cm from its middle, the plan's reach at this species' scale), Logbook entry.
"""

FAUNA = {
    'ship': [
        ('SM_AE_BreachMite', 3, 130, 3, 1, 230.0, ('Enemies', 'Breach Mite', 'Level 1. A small swimmer of the dark between ships. It came in through the breach, after the Divinity the reactor bleeds. It comes in shoals and darts in to bite. It is not a machine, and it does not hate you: it is hungry and afraid. Three health.')),
        ('SM_AE_CoolantBell', 7, 150, 0, 2, 180.0, ('Enemies', 'Coolant Bell', 'Level 2. A drifting bell that has settled into the warmth of the station. When it tips back and calls, it is about to turn and lash with its tendrils: step out of its reach, or parry the lash. Seven health.')),
        ('SM_AE_HullLimpet', 12, 140, 1, 3, 240.0, ('Enemies', 'Hull Limpet', 'Level 3. A grazer that scraped the hull of this station for years before the breach let it in. Light blows glance off its shell. Strike heavy, or step aside when it rams and strike as it turns. Twelve health.')),
    ],
    'center': [
        ('SM_AE_LanternAngel', 4, 140, 3, 1, 255.0, ('Enemies', 'Lantern Angel', 'Level 1. A small swimmer of the marsh air, drawn to any light. The wounds have made it frantic. It comes in shoals and darts in to bite. Strike it and it scatters like breath on glass, to gather again somewhere quieter. Four health.')),
        ('SM_AE_GlassRay', 16, 230, 3, 4, 300.0, ('Enemies', 'Glass Ray', 'Level 3. A wing of living glass that rides the air over the highlands. A wound has touched it, and it strikes at whatever is near. When it banks and calls, step aside from the tail, then strike as it turns. Sixteen health.')),
        ('SM_AE_MarshStalker', 22, 210, 0, 5, 315.0, ('Enemies', 'Marsh Stalker', 'Level 4. A hunter of the reeds, older than the lanterns. The rose light in its fractures is the wound\'s, not its own. It rears before it bites: parry it, and strike while it recovers. Twenty-two health.')),
    ],
    'conclave': [
        ('SM_AE_GoldgrassMote', 4, 140, 3, 1, 220.0, ('Enemies', 'Goldgrass Mote', 'Level 1. The Wise kept these to tend the goldgrass, and they did, until the swarm\'s signal filled the drum. Now they shoal and bite. Strike one and it scatters, to gather again when it is quiet. Four health.')),
        ('SM_AE_ReservoirBell', 9, 180, 0, 2, 250.0, ('Enemies', 'Reservoir Bell', 'Level 2. A drifting bell from the Reservoir, where the Wise kept them to clean the water. The swarm\'s noise has driven it out. When it tips back and calls, it is about to turn and lash: step out of its reach, or parry the lash. Nine health.')),
        ('SM_AE_TerraceRay', 18, 220, 3, 4, 265.0, ('Enemies', 'Terrace Ray', 'Level 3. It glided over the terraces, and the children of the Commons watched for it. The swarm\'s signal hurts it now, and it strikes at what is near. When it banks and calls, step aside from the tail, then strike as it turns. Eighteen health.')),
    ],
    'grove': [
        ('SM_AE_Blightfly', 4, 140, 3, 1, 220.0, ('Enemies', 'Blightfly', 'Level 1. An insect of the valley, grown large and strange in forty years of the Array\'s discharges. It swarms and bites. It is not the Hedge\'s, and it serves no one. Strike it and it scatters, to gather again somewhere quieter. Four health.')),
        ('SM_AE_Burlback', 18, 170, 1, 3, 300.0, ('Enemies', 'Burlback', 'Level 3. A grazer of the forest floor, in a shell like a burl of old wood. The blight shows violet in its seams. Light blows glance off the shell: strike heavy, Settle it, or link it to something softer. Eighteen health.')),
        ('SM_AE_CanopyStalker', 26, 220, 0, 5, 350.0, ('Enemies', 'Canopy Stalker', 'Level 4. The valley\'s hunter, and the Array has left it little to hunt. It keeps to the trees and comes down for whatever moves. It rears before it bites: parry it, and strike while it recovers. Twenty-six health.')),
    ],
}


def entries(world):
    """(category, title, text) rows of one world's animals, for the Logbook and Divinity's voice."""
    return [row[6] for row in FAUNA[world]]
