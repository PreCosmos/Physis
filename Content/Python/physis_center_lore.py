"""Scans, Logbook entries and story text for the Center of the Universe (level 2).

Divinity narrates every entry (Tools/build_physis_voice.py --center). Places are Unreal centimetres
(x north, y east); a z of None puts the marker 1.5 m above the ground.
"""

# Category, title, text, (x, y, z or None), important.
CENTER_SCANS = (
    # Regions.
    # 8 m north of where she wakes, inside the ring of glade crystals (15 m out). At (-67200, 900) the tag stood 22 cm
    # from Glade Crystal 1's axis, inside that 10 m crystal, where the visor's line of sight never reaches (2026-11-08).
    ('Rooms', 'The Still Glade', 'Where you woke. Divinity condensed you here once, at the very beginning, and it has drawn you home again. The Still Tree drinks from the heart of the universe. This glade is a Still Point: if you fall anywhere in the Center, you return here. The roads lead north-east, toward the ruins.', (-67600, 0, None), True),
    ('Rooms', 'Lantern Marsh', 'Shallow water and drowned lanterns. The First Ones lit these to guide their dead home, and human surveyors later wired them into a grid. Three still answer to touch, but only in the right order. A stele on the dry rise at the marsh edge remembers it. Somewhere in the marsh rests a Stillstone.', (-30000, -30000, None), True),
    ('Rooms', 'The Concourse', 'A human survey plaza the Center swallowed whole. The ring above it is First One work, older than the plaza by an age. Crystal hunters nest among the arches. The road east to the Choir Hollow stays sealed until the plaza is quiet.', (-4000, 3000, None), True),
    ('Rooms', 'Choir Hollow', 'A hidden canyon that hums. Every stone here remembers a single note. At its heart stands a shrine that waits for you to understand what happened at Meridian. Its guardians will not let you reach it easily.', (-11000, 48000, None), True),
    ('Rooms', 'Thornveil', 'Divinity grown into weapons: walls of crystal thorn that answer only to force, or to stillness. Blades skate off them. Physis cannot cut her way through. She could ask them to rest. A Stillstone lies at the heart of the thorns.', (26000, 28000, None), True),
    ('Rooms', 'Glass Highlands', 'The high country, cold and bright. Hollow Sentinels walk here: First One war-constructs that never stood down, far stronger than anything you have faced. You do not have to fight them. A Stillstone waits at the top of the drowned spire stair, and a patient path avoids them.', (30000, -38000, None), True),
    ('Rooms', 'Temple of the First Light', 'The first temple. Three Stillstones once sat in the sockets of its door, and until all three are returned it will not open. A wall of thorns guards the stair. Inside rests the Heartbloom.', (62000, 0, None), True),
    # Story.
    ('Story', 'The Still Tree', 'Divinity speaks. Before stars, before the war, before you, there was this tree, or the thing that dreams it. Its light is the oldest light. Everything that lives is a leaf of it. So are you.', (-69200, -800, None), False),
    ('Story', 'Survey Log: Arrival', 'Recorded by Surveyor Amaru Quist, of the Wise, in 2296, five years before the war. The instruments say this place is the exact centre of everything. The instruments also say it is singing. I have decided to believe both.', (-3000, -5000, None), False),
    ('Story', 'Survey Log: The Listeners', 'Recorded by Surveyor Amaru Quist. The First Ones were here long before us. They did not build, not at first. They sat and listened, and their listening grew into stone. We built a dish beside their ring. It has never received anything but music.', (8000, -8000, None), False),
    ('Story', 'Survey Log: Last Entry', 'Recorded by Surveyor Amaru Quist. The recall order came today. War with the First Ones. I asked the Center whether it takes sides. The marsh lit up, every lantern at once. I do not know what that means. I am leaving the lanterns lit.', (-38000, -50000, None), False),
    ('Story', 'Meridian, Remembered', 'Divinity speaks. At Meridian you did not fight. You were still, and the stillness spread. Two fleets lowered their weapons because, for one breath, nothing in you wanted anything from them. Do it again, and this time do it on purpose. That is Settle.', (-15000, 55000, None), True),
    ('Story', 'The First Ones Listen', 'Divinity speaks. The Serene came here to hear me. The Vigil came here to guard what the Serene heard. Neither came to fight. Their temple remembers both.', (60000, 6000, None), False),
    # Puzzle clues and items.
    ('Items', 'The Lantern Stele', 'A First One stele, its glyphs re-cut by human hands into survey numbers. It names the lanterns in the order of the dead they guided home: first the Red lantern beneath the willows, then the Blue lantern beside the drowned lamp post, last the Gold lantern under the great arch. All three stand beside the causeway that runs south-west from this stele to the arch. Interact with each to light it, in that order.', (-28500, -36500, None), True),
    ('Items', 'Stillstone', 'A stone of perfect quiet, one of three keys to the Temple of the First Light. Walk into it to carry it; the door will know. One rests in Lantern Marsh, one at the heart of Thornveil, one atop the Glass Highlands.', (-44000, -52000, None), True),
    ('Items', 'Settle Shrine', 'A ring of First One stone around a pool that never ripples. Stand in it and use Interact. What it teaches cannot be found in a chest. It has to be remembered.', (-14200, 55500, None), True),
    ('Items', 'Thorn Barrier', 'Weaponized crystal, grown to keep things out. Sword and gun only scatter sparks across it. Stand close and use Settle, V or D-pad Right, and the thorns will remember they were never meant to be walls.', (27000, 27500, None), True),
    ('Items', 'Divinity Wound', 'Raw Divinity, burning where the war tore it. It hurts to touch and throws you back. Stand at its edge and use Settle: the wound closes and stays closed.', (31500, 33000, None), False),
    # Beside Prism Pillar 0 (1800, 6800; 1.4 m in radius), 1.6 m clear of its side. On the pillar's own axis it was
    # inside the pillar, where the visor's line of sight never reaches (lantern review, 2026-11-08).
    ('Items', 'Light Prism', 'A First One prism set high on a pillar, dark and cracked. It cannot be reached, but a single shot from the sidearm will wake it. Draw with Tab or D-pad Up, aim, and fire.', (2100, 6800, None), False),
    # In the flower itself. It rests on the pedestal's column at 4275, and the flower mesh has no collision, so the
    # visor sees the tag. The old 3700 was inside the temple's base (Play test, 2026-11-07).
    ('Items', 'Heartbloom', 'The Heartbloom: a flower of crystal that has rested in the temple since the First Ones first listened. It holds the knowledge of mending. Use Interact to take it.', (76000, 0, 4400), True),
    ('Items', 'Echo Cache', 'A pocket of condensed Divinity sealed behind thorns. Walk into it to absorb the Divinity it holds. There are others, hidden across the Center for those who look.', (-60000, 9000, None), False),
)

# Fauna scans: placed beside each herd's home.
FAUNA_SCANS = (
    ('Story', 'Glass Stag', 'A grazing creature of living crystal, its core a small sun of Divinity. Glass Stags are not hunted and do not hunt. They walk the same circles every night, and the Center keeps time by them.', 'SM_CC_Stag'),
    ('Story', 'Wisp Moth', 'Moths of light that feed on the glow of the marsh flowers. Where they gather, Divinity runs close to the surface. Follow a swarm and you will find something worth finding.', 'SM_CC_Moth'),
    ('Story', 'Lumen Jelly', 'Drifting bells of light that rise from the marsh at dusk. Their tendrils sing when they touch. They are harmless, and very curious about you.', 'SM_CC_Jelly'),
    ('Story', 'Veil Fox', 'A small, bold creature of violet glass. Veil Foxes follow travellers at a distance, and are said to lead the lost back to the Still Glade.', 'SM_CC_Fox'),
)

# Enemy entries by level. Mesh, health, scale, hover height (cm), entry.
ENEMY_ENTRIES = {
    1: ('SM_CE_Shardling', 5, 1.0, 140, ('Enemies', 'Shardling', 'Level 1. A crystal hunter, red with hunger for Divinity. It circles, keeps its distance and spits slow shards. Block just before the hit to parry, or dodge. Weak alone, dangerous in swarms. Five health.')),
    2: ('SM_CE_Shardling', 9, 1.45, 160, ('Enemies', 'Shardling Matriarch', 'Level 2. An older Shardling, grown heavy on stolen light. It hits as hard as its children and lasts twice as long. Settle stuns it for a few seconds. Nine health.')),
    3: ('SM_CE_Wraith', 16, 1.0, 190, ('Enemies', 'Prism Wraith', 'Level 3. A shape of shattered glass and trailing light that guards places of power. It strikes from range and drifts out of reach. Mix sword and gun, and Settle it when it closes in. Sixteen health.')),
    4: ('SM_CE_Warden', 26, 1.0, 220, ('Enemies', 'Temple Warden', 'Level 4. A ring of blades set by the First Ones to guard the temple. It does not tire and does not forgive. Parry its volleys and strike while it recovers. Twenty-six health.')),
    5: ('SM_CE_Sentinel', 60, 1.0, 420, ('Enemies', 'Hollow Sentinel', 'Level 5, end-game. A First One war-construct that never stood down. One of its volleys can break you. You are not meant to fight it yet, but you can: parry everything, Settle it often, and bring every capsule you have. Sixty health.')),
}

# Enemy kinds (author, 2026-11-08: tanks, shields, fast enemies and ones hurt only from the sides or behind, each
# beaten in its own way). BP_TrainingDrone EnemyKind 1-4: Tools/blueprint_logic/center_overrides.py gives each its
# rules, physis_center_scenario KINDS its look. Each text says how to beat it. No title here appears in another
# entry's title or text, and no text holds another entry's title, so no Logbook match can confuse two entries.
KIND_ENTRIES = {
    1: ('Enemies', 'Bastion', 'Level 3. A hunter grown into a fortress of slate crystal around a deep red core. Light cuts and quick shots only chip it, for half their strength. Break it with heavy finishers, charged or Divinity shots and the counter after a perfect parry, and while Settle or a parry stuns it, every blow lands in full. It is slow, but its reach is long. Twenty health.'),
    2: ('Enemies', 'Aegis Shard', 'Level 2. A hunter that carries a ward of frozen light on its front. The ward turns every blow and shot that meets it, but its sides and back are bare: dodge round it and strike there. A heavy finisher, a charged or Divinity shot, a perfect parry or Settle breaks the ward for a few breaths, and while it is down the plate is gone. Ten health.'),
    3: ('Enemies', 'Ember Skitter', 'Level 1. A small, quick splinter of a hunter. It keeps its distance and darts in just before it strikes. Watch for the dash: block or parry it, then cut while it is close, for it breaks at a touch. Four health.'),
    4: ('Enemies', 'Onyx Ward', 'Level 3. A ring of dark glass that always shows you its face, and no blow or shot that meets its face can hurt it. It turns slowly and strikes only what is in front of it: circle round it, or dodge past it, and hit its sides and back. Settle or a perfect parry stuns it, and while it is stunned it cannot turn. Fourteen health.'),
}

# Items that only carry a tag at runtime (center_logic.py RELIC_SCANS), never placed as a standalone tag. A Divinity Cache
# is a cache that a puzzle or a fight keeps, with no thorns round it: the Echo Cache text says thorns, and only the
# caged caches and the Garden Cache have them (2026-11-08 review).
ITEM_ROWS = (
    ('Items', 'Divinity Cache', 'A pocket of condensed Divinity, kept by the place around it until its puzzle is solved or its guardians fall. Walk into it to absorb the Divinity it holds. There are others, hidden across the Center for those who look.'),
)

# The grass her blade cuts (physis_center_scenario.Place.grass): one tag over every patch, all of this one kind, so the
# first scan logs it and the rest turn grey (author, 2026-11-15: "make the grass that can be cut scannable as well").
# No voice or Logbook image yet.
GRASS_SCAN = ('Story', 'Gleamgrass', 'Tall pale grass with gold seed heads. Its roots drink the Divinity that runs under the Center and hold whatever the ground has swallowed. Cut it with your blade: a tuft may give up a Divinity crystal, a health capsule or an ammo cell. It grows back within minutes.')

# The open puzzles (physis_center_scenario puzzles()): one scan tag at each, above whatever stands there, saying what
# to do (lantern review, 2026-11-08: none of the eight had one, so the Sunken Causeway showed only a gold ray over an
# islet no one could climb). Category, title, text; the titles are the puzzles' own names.
PUZZLE_SCANS = (
    ('Rooms', 'Bell Ruins', 'A ruined court where three glass bells still stand. Ring each one with Interact, in any order. When all three sound together, the court raises the cache it has kept for an age.'),
    ('Rooms', 'Sunken Causeway', 'An islet holds its cache out on the deep water, its sides sheer. A causeway lies drowned between it and the shore, and the standing stone on the shore still remembers raising it. Use Interact beside the stone, then cross on the stones that rise.'),
    ('Rooms', 'Four Monoliths', 'Four First One stones of four heights, standing out of order around this spot. Each wakes to Interact, but only after the stone just shorter than it. Wake them from the shortest to the tallest, and their centre answers.'),
    ('Rooms', 'Drifting Steps', 'Slabs that rise and fall, each a little higher than the last, climb to a ledge on a pillar. Jump onto each slab as it sinks to its lowest, ride it up, and jump to the next. The cache waits on the ledge.'),
    ('Rooms', 'Thorn Garden', 'A walled garden whose only gate is grown shut with thorns. Blades and shots only scatter sparks on them. Stand close to the gate and use Settle, V or D-pad Right, then walk in to the cache the garden has kept.'),
    ('Rooms', 'Wounded Gully', 'A dead-end gully with a cache at its far end. Three wounds of raw Divinity cross its floor and burn in turn. Run past each one while it is dark, or stand at its edge and use Settle to close it for good.'),
    ('Rooms', 'Root Stair', 'A crystal among the roots of the hill. Use Interact beside it, and the roots lift into a stair that climbs to a lookout, where a cache looks out over the north.'),
    ('Rooms', 'Sky Stones', 'Stones float in a spiral here, each one a short jump above the last, up to a crown that holds a cache. Climb them one jump at a time. A fall only means climbing again.'),
)

CENTER_TUTORIALS = (
    ('Map: M / View     Divinity Rays rise over every puzzle: gold, a puzzle (some sealed by thorns that need Settle);~cyan, an Echo Cache for Settle; violet, a vault for abilities from later. A ray goes out once its puzzle is solved.', (-66300, 0), (.5, 3.0, 1)),
    ('Settle: V / |DR|     Calms creatures, dissolves thorn barriers, closes Divinity wounds. Costs 10 Divinity.', (-14200, 55500), (.6, 2.6, 1)),
    # No Mend hint. The Heartbloom's Done text already gives Mend's keys and cost. The strip that used to stand in the
    # sanctum sat inside the temple's base and never fired. On the floor it would fire during the Wardens' fight,
    # before Mend, and cover the Done text (review, 2026-11-07).
)

# The ability vaults (physis_center_vaults.py): fifteen sealed vaults that each need abilities from every phase
# of the game (blade or sidearm, the Scan Visor, Settle, and at least one ability from a later level), each
# holding an augmentation. Category, title, text; the vault builder places each stele.
VAULT_SCANS = (
    ('Rooms', 'Vault of the Patient Heart', 'Inscribed by the Vigil, who sealed this vault. Settle the thorns at the outer gate. In the outer court, break the three crystal locks with the blade. The middle gate is a lattice of light: pass it with Light Step. In the middle court, wake the node with Resonance Link. The inner gate is a field: hold it open with Dissonance. When the locks are broken and the node sings, a Health Augmentation rises at the centre.'),
    ('Rooms', 'Vault of the High Ledger', 'Inscribed by the Serene. Our ledger is kept above the reach of hands. A stair once climbed this stone and is only a memory now: read its trace at the echo by the foot of the stone, and walk the stair the past still holds. At the top, a door of grief: sit with it, and it will open. Inside, wake the two prisms on their pillars with the sidearm and close the wounds with Settle. Then the Health Augmentation is yours.'),
    ('Rooms', 'Vault of the Unwoven Span', 'Inscribed by the Vigil. The ramp to this vault fell in the war, but its anchor still stands at the foot of the stone: Reweave the ramp from it. At the top, Settle the thorns and defeat the three Prism Wraiths that guard the court. The inner lattice yields only to Light Step. A Health Augmentation waits within.'),
    ('Rooms', 'Vault of the Long Silence', 'Inscribed by the Serene. This vault keeps its silence behind three gates. The first is a door of grief: sit with it. In the first court, wake the four stones from the tallest to the shortest. The second gate is thorn: Settle it. In the second court, break the two crystal locks with the blade. The last gate is a field: hold it open with Dissonance. The fourth Health Augmentation rests at the centre.'),
    ('Rooms', 'Court of Edges', 'Inscribed by the Vigil, for their blade-dancers. Pass the lattice at the gate with Light Step, and be quick, for it closes again. Six crystal locks stand in the court among pulsing wounds: break every one with the blade, timing your path between the pulses or closing them with Settle. Then Settle the thorns of the inner gate. The Katana Augmentation within makes every cut strike harder.'),
    ('Rooms', 'The Resonant Blades', 'Inscribed by the Vigil. Three stones stand apart, once joined by bridges of resonance. Wake the node at the foot of the first stone with Resonance Link, and its bridge will rise; wake the node on each stone to reach the next. On every stone, break the crystal lock with the blade and close the wound with Settle. When all three locks are broken, the last stone gives up its Katana Augmentation.'),
    ('Rooms', 'The Rewoven Arena', 'Inscribed by the Vigil. Our arena stood above the plain until its ramp was broken: Reweave the ramp at the anchor below. Settle the thorns at the arena gate, defeat its guardians, two Prism Wraiths and a Temple Warden, and break the two crystal locks at the heart of the arena with the blade. When all of it is done, the arena\'s prize, a Katana Augmentation, rises.'),
    ('Rooms', 'The Prism Gallery', 'Inscribed by the Serene. The gallery\'s four prisms stand far above any blade. Settle the thorns at the gate, then wake all four prisms with the sidearm. The inner lattice opens only to Light Step. Within lies a Pistol Augmentation, which makes every shot strike harder.'),
    ('Rooms', 'The Far Lights', 'Inscribed by the Serene. Three lights stand far out on the plain, and only the observatory sees them. Reweave its ramp at the anchor to climb up. Close the wounds on the terrace with Settle, then wake the three distant prisms with the sidearm from up there. The cell is held shut by a field: open it with Dissonance. Inside waits a Pistol Augmentation.'),
    ('Rooms', 'The Furnace Walk', 'Inscribed by the Vigil. Those who would ward themselves walked this furnace first. Five wounds burn across the gully floor: Settle each one, or Mend as you burn. Two Temple Wardens keep the far end: defeat them. The cell beyond is held shut by a field: open it with Dissonance. A Defense Augmentation waits there, and every hit you take afterwards will cost you less.'),
    ('Rooms', 'The Sentinel Hold', 'Inscribed by the Vigil. A door of grief guards this hold: sit with it to enter. Inside waits a Hollow Sentinel that never stood down. Defeat it: parry everything, Settle it often, and Mend when you must. Then Settle the thorns of the inner gate. The Defense Augmentation is the Sentinel\'s charge.'),
    ('Rooms', 'The Burning Stair', 'Inscribed by the Vigil. Climb the stair around the stone. Its landings burn in pulses: cross while they are dark, or close them with Settle. At the top, the bridge to the far stone is broken: Reweave it from its anchor. Two Prism Wraiths guard the far stone. Defeat them, and the Defense Augmentation rises.'),
    ('Rooms', 'The Lattice Run', 'Inscribed by the students of the Lightforms. Settle the thorns at the start. Three lattices bar the run, and each opens for only a few breaths after Light Step: pass, then cross the pulsing wounds beyond while they are dark. At the end, wake the prism high above the cell with the sidearm. The Agility Augmentation there lengthens the moment in which a block becomes a perfect parry.'),
    ('Rooms', 'The Pulse Garden', 'Inscribed by the Serene. Settle the thorns at the gate. The garden\'s wounds pulse in turn: walk them while they are dark, or Settle them. Wake the prism above the inner gate with the sidearm, then pass the lattice with Light Step before it closes. At the centre, wake the node with Resonance Link, and the Agility Augmentation will rise.'),
    ('Rooms', 'The Drift Spire', 'Inscribed by the students of the Lightforms. The stones around this spire rise and fall: time each jump to a stone\'s low point. Halfway up, the stair ends in the present: read the echo there with Trace Reading, and the rest of it returns. At the crown, close the wounds with Settle and break the crystal lock with the blade. The Agility Augmentation is yours.'),
)
# What each kind of vault lock is, and what will open it (one Logbook entry per kind).
GATE_SCANS = (
    ('Items', 'Light Lattice', 'Divinity speaks. Bars of hardened light. Nothing that walks can pass them, and no blade or shot will break them. Light Step, which the Lightforms will teach you, carries you through as light, and some lattices open for only a few breaths after it. Remember where this one stands.'),
    ('Items', 'Dissonance Field', 'Divinity speaks. A standing wave of hostile Divinity. It cannot be cut, shot or settled. Dissonance, which you will learn before the Reckoning, holds a field like this open long enough to walk through it. Remember where it stands.'),
    ('Items', 'Door of Grief', 'Divinity speaks. A door sealed by grief, not by stone, and force will never open it. When you have learned to Sit With what hurts, in the first hardened facility, stand before it and it will open for good.'),
    ('Items', 'Resonance Node', 'Divinity speaks. A node still humming with an old connection. Resonance Link, learned on Earth in the Wounded Grove, will wake it, and whatever it was joined to will answer: a bridge, a stair, a door.'),
    ('Items', 'Reweave Anchor', 'Divinity speaks. The anchor of something broken, a ramp or a bridge that still remembers its shape. In the First Ones\' ruins you will learn Reweave. Use it here, and the anchor will rebuild what it holds.'),
    ('Items', 'Trace Echo', 'Divinity speaks. The past is thin here: something stood in this place and was forgotten. Trace Reading, which Kairos and the Wise will teach you, shows what was. Use it beside the echo, and the past will be solid enough to walk on.'),
    ('Items', 'Crystal Lock', 'Divinity speaks. A lock of brittle First One crystal, set into a vault. The blade breaks it best: strike it until it shatters. Most vaults hold more than one.'),
)
AUG_SCANS = (
    ('Items', 'Health Augmentation', 'Divinity speaks. A heart of condensed Divinity, sealed in a vault. Walk into it to absorb it: you gain a Health Tank, ten more health shown as a reserve tank under your health bar, and you are fully healed. Four lie in the Center\'s vaults.'),
    ('Items', 'Katana Augmentation', 'Divinity speaks. A shard of edged light that settles into your blade. Each one makes every katana strike a quarter stronger. Three lie in the Center\'s vaults.'),
    ('Items', 'Pistol Augmentation', 'Divinity speaks. A spun core of Divinity that tightens your sidearm. Each one makes every shot almost a third stronger, the Divinity Shot too. Two lie in the Center\'s vaults.'),
    ('Items', 'Defense Augmentation', 'Divinity speaks. A ward of six facets that steadies your composure. Each one takes fifteen percent off every hit you take. Three lie in the Center\'s vaults.'),
    ('Items', 'Agility Augmentation', 'Divinity speaks. Two feathers of light that quicken your guard. Each one lengthens the moment in which a block becomes a perfect parry by a tenth of a second, and lets you parry attacks from further away. Three lie in the Center\'s vaults.'),
)

AWAKEN_LINE = 'Divinity speaks. You are home, Physis. Not to rest. To learn what you did at Meridian, and how to do it again.'


def center_entries():
    rows = [row[:3] for row in CENTER_SCANS] + [row[:3] for row in FAUNA_SCANS] + [entry[4] for entry in ENEMY_ENTRIES.values()]
    rows += list(VAULT_SCANS) + list(GATE_SCANS) + list(AUG_SCANS)
    # Added 2026-11-08. Their voices (Tools/build_physis_voice.py --center) and Logbook images come later: until
    # then each one's BP_LogVoice has no sound or image, and scanning only adds the text.
    rows += [KIND_ENTRIES[kind] for kind in sorted(KIND_ENTRIES)] + list(PUZZLE_SCANS) + list(ITEM_ROWS) + [GRASS_SCAN]
    return rows
