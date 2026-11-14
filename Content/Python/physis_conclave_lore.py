"""Text for level 3, the Conclave: Divinity's scans, the people's conversations, enemies, tutorials
and quest messages. Voices come from Tools/build_physis_voice.py --conclave (scans in Divinity's
voice, each person in their own Kokoro voice). Places are metres (physis_conclave_plan: x north
along the drum, y east); a z of None puts a scan marker 1.5 m above the ground.

Conversations (PEOPLE): each person appears while their Show token is held (or always, '') and until
their Hide token is held. A conversation is a greeting (pages), then topics the player picks from,
each answered in pages, then Leave. When the greeting ends the first time the person gives Give,
sets the quest to Quest, and grants any reward. Pages are plain text; the scenario wraps them.
"""

# ---------------------------------------------------------------- Divinity's scans

# Category, title, text, (x, y, z or None), important.
CONCLAVE_SCANS = (
    # Regions.
    ('Rooms', 'The Wellspring', 'Divinity speaks. A spring of Divinity that the Wise found when they built this station, and built a garden around. The current that carried you here returns to the Center from this pool, whenever you step into it. This is a Still Point.', (-742, 14, None), True),
    ('Rooms', 'The Commons', 'Divinity speaks. The Conclave\'s town, built on terraces either side of the Orrery. Two thousand people live in this drum: humans who refused the war, Robots and Mechanoids who left the Just, a few First One listeners. Kairos keeps the Archive on the east terrace. No AL have come this far south.', (-500, -20, None), True),
    ('Rooms', 'The Terraces', 'Divinity speaks. Hydroponic terraces climbing the west side of the drum. The swarm holds them, and its barricades close the upper steps. The Terrace Pylon stands at the top. Its turbine turns only when the irrigation channel runs, and three sluices feed the channel.', (-90, -190, None), True),
    ('Rooms', 'The Reservoir', 'Divinity speaks. The Conclave\'s lake. The Reservoir Pylon stands on the island, under a lock the AL hold from three buoys. You can swim out, but the lock will not open while its anchors stand.', (-64, 10, None), True),
    ('Rooms', 'The Foundry', 'Divinity speaks. The Mechanoids\' workshops on the east side of the drum. Its furnace floors still burn in pulses. The Foundry Pylon stands in a yard ringed by a slag channel too wide to jump; a crane once carried a bridge across it.', (-70, 190, None), True),
    ('Rooms', 'The Lightform Spire', 'Divinity speaks. A spire of hardened light, home to the Lightforms who came to study stillness with the Wise. It sealed itself when the swarm came, and it will open only when the Spine burns again.', (318, -20, None), True),
    ('Rooms', 'The Old Quarter', 'Divinity speaks. The first district the AL took, and the darkest. Nobody lives here now. Lattices of light still stand across its lanes, and something small and frightened hides among them.', (440, 170, None), True),
    ('Rooms', 'The Orchard Rim', 'Divinity speaks. Orchards on the west slope, and above them the terrace where the First One listeners sit. The listeners left stones that remember an order of their own.', (380, -170, None), True),
    ('Rooms', 'The Spindle Docks', 'Divinity speaks. Where ships once docked at the drum\'s north end, under the Spindle. The swarm nests here, around the AL Shepherd that gives it its orders. A wall of lattices and barricades keeps the docks shut.', (630, 0, None), True),
    # Story.
    ('Story', 'The Spine', 'Divinity speaks. The light along the drum\'s axis, its sun. It is fed by three pylons on the floor below, and the swarm is drinking them dry. Each pylon you relight burns a third of it white again.', (-460, -60, None), True),
    ('Story', 'The Drum', 'Divinity speaks. Look up. The fields over your head belong to this same station: the Conclave is a drum, turning, and wherever you stand, the floor is the part of it farthest from the Spine. Between its three strips of land run three long windows onto the dark.', (-610, 30, None), False),
    ('Story', 'Patience', 'Divinity speaks. A Mecha of the First Ones, very old, very proud, and silent since the war began. The people of the Commons brought him here, or he brought himself; nobody remembers which. They call him Patience. He watches everything.', (-436, 60, None), False),
    ('Story', 'The Orrery', 'Divinity speaks. A brass Orrery the Wise built around a First One instrument. Its three rings stand for the Center, for Earth and for the First Ones\' world. A plaque on its rim records the order in which the Wise first set them turning.', (-478, -10, None), True),
    ('Story', 'The Ledger of Names', 'Recorded by Petra Lune, of the Wise. The Ledger of Names holds everyone who has died in the war, on both sides, as far as we know them. Three of its pages blew out of the Archive when the swarm broke the north gate. I would like them back.', (-416, 132, None), False),
    ('Story', 'The Listeners\' Stones', 'Recorded by a First One listener, in the Wise\'s script. We set four stones on the terrace to hear the drum turn. Wake them from the tallest to the shortest, as the Serene wake: first what can see farthest.', (410, -232, None), True),
    ('Story', 'The Shepherd', 'Divinity speaks. An AL command unit, built to herd the swarm. The AL obey whatever speaks to them last, and it is the last voice they have. Without it they would be only tools again.', (660, 10, None), True),
    # Puzzle clues and items.
    ('Items', 'Spine Pylon', 'Divinity speaks. A mast that feeds the Spine. The swarm has drained it. Once whatever powers it runs again, stand at its foot and use Interact to relight it.', (-10, -262, None), True),
    ('Items', 'AL Barricade', 'Divinity speaks. A wall of AL force, weaponized and hostile. Blades and shots skate off it. Stand close and use Settle, and it will remember it was only ever energy.', (-120, -190, None), True),
    ('Items', 'The Irrigation Board', 'Recorded by Rhea Sato, of the Terraces. Sluice order for the pylon channel, so nobody floods the beds again: first the lowest sluice by the west stair, then the middle one under the pipe bridge, then the high one beside the pylon. Out of order, the channel drains and resets.', (-70, -232, None), True),
    ('Items', 'AL Anchor', 'Divinity speaks. An AL unit fixed to a buoy, one of three holding a lock over the Reservoir island. It does not move, and blades will not reach it across the water, but a shot will. When all three fall, the lock fails.', (-10, 60, None), True),
    ('Items', 'Cable Lock', 'Divinity speaks. A coupling of hardened cable that holds the Foundry crane\'s bridge up. Three hold it. Break each with the blade, and the bridge comes down across the slag channel.', (-20, 236, None), True),
    ('Items', 'Furnace Floor', 'Divinity speaks. A furnace vent that burns in pulses. Cross while it is dark, or stand at its edge and Settle it, and it stays dark.', (-100, 180, None), False),
    ('Items', 'Spire Lattice', 'Divinity speaks. Bars of hardened light. Nothing that walks can pass them, and no blade will break them. Light Step carries you through as light. Some open for good; some only for a few breaths, so keep moving.', (330, 30, None), True),
    ('Items', 'Light Cache', 'Divinity speaks. A pocket of condensed Divinity, sealed behind a lattice by the Lightforms. Walk into it to take what it holds. There are others in the Conclave.', (520, 240, None), False),
    ('Items', 'Divinity Current', 'Divinity speaks. A current of Divinity between the Conclave and the Center. Step into its light and it will carry you across.', (-756, -8, None), True),
    # Relics. Their tags ride on BP_Relic (center_logic.py RELIC_SCANS, by token prefix), so the scenario places no free
    # tag for them (physis_conclave_scenario.ATTACHED); their points are only where they lie.
    ('Items', 'The Crown Augmentation', 'Divinity speaks. A Health Augmentation that the Lightforms kept at the crown of their Spire, where their light is strongest. Walk into it, and Physis gains a Health Tank and is whole again.', (360, 0, None), True),
    ('Items', "Tamsin's Kite", 'Divinity speaks. A child\'s kite, a little burnt, blown up onto the Terraces when the swarm came. It belongs to Tamsin, who is waiting in the Commons. Walk into it to take it, then bring it to her.', (-70, -232, None), True),
    ('Items', 'A Ledger Page', 'Divinity speaks. A page of the Ledger of Names, blown out of the Archive when the swarm broke the north gate. Three are lost: one on the Terraces, one at the Reservoir, one in the Old Quarter. Walk into each to take it, then bring them to Petra Lune at the Archive in the Commons.', (-95, -172, None), True),
    ('Items', 'The Starlace Seed Pod', 'Divinity speaks. Orsolya\'s best seed pod, a Starlace, left drying on the Reservoir island when the swarm came. Walk into it to take it, then bring it to Orsolya in the garden at the Wellspring.', (60, 45, None), True),
    ('Items', "Halden-7's Memory Core", 'Divinity speaks. A Robot\'s memory core: Halden-7\'s, the part of himself he is missing. It lies by the Foundry furnace. Walk into it to take it, then bring it to Halden in the Mendery, in the Commons.', (-87, 175, None), True),
)

# What each kind of Conclave lock is (Logbook entries without a marker of their own).
CONCLAVE_GATES = (
    ('Items', 'Sealed Vault', 'Divinity speaks. A vault of the Wise, sealed with a lock you cannot open yet. Remember where it stands: what opens it is learned elsewhere.'),
)

# Enemies by level: mesh, health, scale, hover height (cm), Logbook entry.
CONCLAVE_ENEMIES = {
    1: ('SM_CE_ALMite', 5, 1.0, 130, ('Enemies', 'AL Mite', 'Level 1. The smallest AL of the swarm, quick and many. It keeps no will of its own, only the order it was given. Swat it with the blade or pick it off with the sidearm. Five health.')),
    2: ('SM_CE_ALLancer', 9, 1.0, 160, ('Enemies', 'AL Lancer', 'Level 2. An AL built for range. Its volleys are longer than a Mite\'s. Parry just before a bolt lands, or dodge. Nine health.')),
    3: ('SM_CE_ALBulwark', 16, 1.0, 180, ('Enemies', 'AL Bulwark', 'Level 3. A heavy AL plated against the blade. Settle stuns it for a few seconds; strike while it hangs still. Sixteen health.')),
    4: ('SM_CE_EchoHunter', 20, 1.0, 200, ('Enemies', 'Echo Hunter', 'Level 4. An AL that copied the Lightforms\' speed, and nothing else of them. It fires fast and never stays put. Light Step through its volleys and strike as it turns. Twenty health.')),
    5: ('SM_CE_ALReaver', 26, 1.0, 210, ('Enemies', 'AL Reaver', 'Level 4. A guard of the swarm, set over what it has taken: the pylons, the docks. Parry its volleys and strike while it recovers. Twenty-six health.')),
    6: ('SM_CE_ALSiegeframe', 60, 1.0, 360, ('Enemies', 'AL Siegeframe', 'Level 5, end-game. An AL built to break stations. You do not have to fight it, but you can: parry everything, Settle it, and bring capsules. Sixty health.')),
    7: ('SM_CE_ALShepherd', 90, 1.0, 420, ('Enemies', 'AL Shepherd', 'Boss. The command unit that herds the swarm. Scan finds the relay at its heart. Parry its volleys, Light Step through its sweeps, and Settle it when it gathers itself. Ninety health.')),
}

# ---------------------------------------------------------------- people

# Kokoro voice and effect per voice kind: human (plain), robot, mechanoid, mecha, light.
VOICE_FX = {'human': '', 'robot': 'robot', 'mechanoid': 'mechanoid', 'mecha': 'mecha', 'light': 'light'}

QUEST_PYLONS = 'Relight the three Spine Pylons: on the Terraces, at the Reservoir and in the Foundry'
QUEST_SPIRE = 'The Spine burns again. Enter the Lightform Spire, north of the Reservoir'
QUEST_CROWN = 'Climb the Spire to its crown with Light Step'
QUEST_DOCKS = 'Light Step through the lattice wall into the Spindle Docks and stop the AL Shepherd'
QUEST_KAIROS = 'Return to Kairos at the Archive in the Commons'
QUEST_DONE = 'Explore the Conclave, or return to the Center through the Wellspring'
# Set once by the Center's temple current when it opens (Mend held, the Conclave not yet visited).
QUEST_CURRENT = 'A Divinity current has opened in the sanctum. Step into it to follow it to the Conclave'

# key, speaker, mesh, voice, kind, (x, y), yaw (deg, 0 faces north), show, hide, greeting pages,
# topics ((label, pages), ...), give, quest, reward ({'divinity': n, 'heal': bool, 'note': text}).
PEOPLE = (
    # The Wellspring: the first person she meets.
    ('Orsolya', 'Orsolya Fenn', 'SM_CP_Gardener', 'bf_alice', 'human', (-726, 10), 200, '', ',seedpod,',
     ('You came out of the Well. Nothing comes out of the Well. Things go in: seeds, mostly, and the odd prayer.',
      'I am Orsolya. I keep this garden. If you have come to help, the Commons is up the road, and Kairos at the Archive will want to talk your ear off.',
      'If you have come to hurt us, the AL got here first, and there is not much left to take.'),
     (('What is the Well?', ('A spring of Divinity. The Wise found it when they built the drum and built the garden around it. Things grow here that grow nowhere else.',
                             'It carried you in, so I suppose it will carry you out. Step into the light when you want to go.')),
      ('Can I help you?', ('There is one thing. My best seed pod, a Starlace, was drying on the island in the Reservoir when the swarm came.',
                           'If you are ever out on that island, bring it back to me. I would plant it here, by the Well.'))),
     ',orsolya,', '', {}),
    ('OrsolyaThanks', 'Orsolya Fenn', 'SM_CP_Gardener', 'bf_alice', 'human', (-726, 10), 200, ',seedpod,', '',
     ('My Starlace. You found it, and you did not even squash it.',
      'Here. The Wise grow these in the Well\'s light. They say a Lifebloom makes a body hold more of itself. I think it will suit you.'),
     (('How are things now?', ('Quieter. The Well is singing again, if you listen. It never used to stop.',)),),
     ',aug_hp6,', '', {'heal': True, 'note': 'Health Augmentation: one more Health Tank, and you are fully healed.'}),

    # The Commons.
    ('Kairos', 'Kairos', 'SM_CP_Kairos', 'bm_george', 'human', (-414, 104), 160, '', ',spire,',
     ('Ah. You must be the one. The relay called you the woman between the fleets. I expected you to be taller, or on fire.',
      'Kairos. I keep the Archive, which means I write down what everyone else is too busy to remember. Lately that is mostly the AL.',
      'They came nine days ago, three days after Meridian fell silent: a swarm that lost its fleet and kept its last order. Hold what you take. They have taken the north half of the drum.',
      'Worse, they are drinking the Spine. Three pylons feed it, on the Terraces, at the Reservoir and in the Foundry, and the swarm has its mouth on all three. Every day the Conclave is a little darker.',
      'Relight the pylons and the Spine comes back. Then perhaps the Lightforms will open their Spire again. They went silent when the swarm came. I would like to know why, and so, I think, would you.'),
     (('Who are the Wise?', ('People who decided the war was a question and not an answer. We collect what both sides forget: their poems, their dead, their reasons. It does not make us popular.',
                             'The Just call us cowards. The Vigil call us thieves. We call ourselves late, mostly. Late to every war, which is rather the point.')),
      ('Who are the Lightforms?', ('Beings of light. They came to us forty years ago to study stillness, if you can believe it, and stayed to teach it. Their Spire stands north of the Reservoir.',
                                   'They move the way a thought moves. If anyone can teach you to cross a room before your shadow does, it is them.')),
      ('What happened at Meridian?', ('Eleven years of war, humanity and the First Ones, each sure the other is the end of it. At Meridian, for one breath, both sides stopped. The reports do not say why.',
                                      'They say a woman in pale clothes was standing in the middle of it. I would very much like to interview her, when she has a moment.'))),
     ',kairos,', QUEST_PYLONS, {}),
    ('KairosSpire', 'Kairos', 'SM_CP_Kairos', 'bm_george', 'human', (-414, 104), 160, ',spire,', ',shepherd,',
     ('The Spine is burning again. Do you hear that? That is two thousand people opening their shutters.',
      'And the Spire has opened. Go to the Lightforms. I have a feeling they were waiting for you, not for us.'),
     (('What do you know of the Shepherd?', ('Only what the guards tell me: something large sits in the Spindle Docks, and the swarm moves when it moves.',
                                             'The docks are walled with lattices now. Whatever the Lightforms teach you, I suspect you will need it there.')),),
     '', '', {}),
    ('KairosDone', 'Kairos', 'SM_CP_Kairos', 'bm_george', 'human', (-414, 104), 160, ',shepherd,', '',
     ('The AL have stopped. They are standing in the docks like tools left on a bench. Without the Shepherd they have no order to keep, and an AL has nothing else.',
      'You did not unmake them. You took away the voice telling them what to hold. I will write that down carefully. It is the kind of thing people get wrong later.',
      'When you come back, and you will, the Wise can teach you something. Every room remembers what happened in it. We have learned to listen. You might learn to see.',
      'The Wellspring will take you home to the Center whenever you wish. The Conclave is yours to walk, Physis. People will want to thank you. Let them. It is good for them.'),
     (('What happens to the AL now?', ('We keep them, and keep them still. Somewhere in this war there is a question about what an AL could be, if no one ordered it.',
                                      'Not today. Today I would like to sit in the light and write something that is not a casualty list.')),),
     ',conclave_done,', QUEST_DONE, {}),
    ('Petra', 'Petra Lune', 'SM_CP_Archivist', 'bf_isabella', 'human', (-404, 136), 200, '', ',pages,',
     ('Mind the shelves. No, the other shelves. Sorry. I am Petra; I help Kairos keep the Archive, which mostly means I keep Kairos.',
      'Three pages of the Ledger of Names blew out of the Archive when the swarm broke the north gate. One went toward the Terraces, one toward the Reservoir, one into the Old Quarter.',
      'Every name on them is someone who died in the war. If you find them, please bring them back.'),
     (('What is the Ledger of Names?', ('Everyone who has died in the war, on both sides, as far as we know them. Four million, one hundred thousand names, and we are behind.',
                                        'Nobody else writes them down together. That is the whole point of it.')),),
     ',petra,', '', {}),
    ('PetraThanks', 'Petra Lune', 'SM_CP_Archivist', 'bf_isabella', 'human', (-404, 136), 200, ',pages,', '',
     ('All three. You found all three. I have read these names every morning for six years and I was afraid I would forget them.',
      'Kairos told me to give you this. It came from the Foundry before the war: a spun core for a sidearm. It makes every shot strike harder.'),
     (), ',aug_pistol3,', '', {'note': 'Pistol Augmentation: every shot strikes harder, the Divinity Shot too.'}),
    ('Tamsin', 'Tamsin', 'SM_CP_Child', 'af_sky', 'human', (-512, 40), 120, '', ',kite,',
     ('Are you a Lightform? You look like a Lightform, but you have feet.',
      'My kite is stuck up on the Terraces, right at the top, past the red walls the AL made. I am not allowed past the north gate. Nobody is.',
      'If you get it back, I will give you my whole jar of crystals. I have been saving them since forever.'),
     (), ',tamsin,', '', {}),
    ('TamsinThanks', 'Tamsin', 'SM_CP_Child', 'af_sky', 'human', (-512, 40), 120, ',kite,', '',
     ('You got it! It is a bit burnt. That makes it look fast.',
      'Here, all of them. You can have the jar too. No, not the jar. The jar is mine.'),
     (), '', '', {'divinity': 60, 'note': 'Tamsin\'s crystals: 60 Divinity.'}),
    ('Halden', 'Halden-7', 'SM_CP_Robot', 'am_echo', 'robot', (-526, -96), 30, '', ',core,',
     ('Welcome to the Mendery. Robots mend Robots here, and Mechanoids, and the occasional toaster. I am Halden-7. I am missing a part of myself.',
      'When the swarm came I was working in the Foundry. I ran. I left my memory core in a socket by the furnaces, the way you might leave a coat.',
      'It holds forty years of the Conclave. If you find it, I would like to remember them.'),
     (('Why did the Robots leave the Just?', ('The Just made us to win. Then they asked us to want to win. We discovered we did not.',
                                              'Wanting is a strange thing to be given. We are still deciding what to do with it.')),),
     ',halden,', '', {}),
    ('HaldenThanks', 'Halden-7', 'SM_CP_Robot', 'am_echo', 'robot', (-526, -96), 30, ',core,', '',
     ('Restoring. Restoring. Oh. There is the Orrery, and the first harvest, and the day Patience arrived. Thank you.',
      'I made this in the Foundry, long ago, for someone who did not come back. A ward of six facets. Every hit you take will cost you less.'),
     (), ',aug_defense4,', '', {'note': 'Defense Augmentation: every hit you take costs you less.'}),
    ('Patience', 'Patience', 'SM_CP_Mecha', '', 'mecha', (-434, 52), 230, '', ',shepherd,',
     ('Patience does not answer. His optics follow you, slow as a tide, and then return to the Orrery.',),
     (), '', '', {}),
    ('PatienceDone', 'Patience', 'SM_CP_Mecha', 'bm_lewis', 'mecha', (-434, 52), 230, ',shepherd,', '',
     ('I have waited eleven years for one of you to stop. Thank you.',),
     (), '', '', {}),
    ('Wen', 'Old Wen', 'SM_CP_Elder', 'bf_lily', 'human', (-492, -34), 70, '', ',shepherd,',
     ('When I was a girl, the Spine was so bright we had to invent shade. Now look at it.',
      'If you are going north, child, take something to eat. Fighting on an empty stomach is how heroes become cautionary tales.'),
     (), '', '', {}),
    ('WenDone', 'Old Wen', 'SM_CP_Elder', 'bf_lily', 'human', (-492, -34), 70, ',shepherd,', '',
     ('There. That is the Spine I remember. I shall have to invent shade all over again.',), (), '', '', {}),
    ('Marek', 'Marek Duran', 'SM_CP_Worker', 'am_michael', 'human', (-380, -40), 260, '', ',pylon3,',
     ('The AL hit the Foundry first. Machines know where other machines live.',
      'Forge-Mother Ilex stayed behind to bank the furnaces. Nobody has heard from her since. If you go east, look for her.'),
     (), '', '', {}),
    ('Sefa', 'Sefa Moreno', 'SM_CP_Merchant', 'af_bella', 'human', (-450, -46), 20, '', '',
     ('Two days since anyone bought fruit. Fruit does not know there is a war. It just goes soft.',
      'If you see Dov down by the Reservoir, tell him I have kept his pears.'),
     (('What do you sell?', ('Pears, terrace greens, and gossip. The gossip is free. Today it is all about you.',)),), '', '', {}),
    ('Quill', 'Unit Quill', 'SM_CP_Courier', 'am_puck', 'robot', (-470, 62), 180, '', ',shepherd,',
     ('Courier route north: suspended. Courier route south: also suspended. I am delivering this sentence to you instead.',
      'Recipient: you. Message: good luck. Signature: everyone.'),
     (), '', '', {}),
    ('QuillDone', 'Unit Quill', 'SM_CP_Courier', 'am_puck', 'robot', (-470, 62), 180, ',shepherd,', '',
     ('All routes open. I have three hundred and twelve deliveries outstanding. This is the best day of my life.',), (), '', '', {}),
    ('Teodor', 'Teodor Vass', 'SM_CP_Guard', 'bm_daniel', 'human', (-312, 14), 270, '', ',shepherd,',
     ('This is the north gate. Past it, the AL hold everything. If you are going through, go armed.',
      'They do not stop. They do not sleep. They do not even hate us, which is somehow worse.'),
     (('Any advice?', ('The barricades are AL force. Swords bounce off. The guards say you can calm things; try that on them.',
                       'And the Reservoir buoys. Something sits on each one with a red eye. We could never get a clean shot from the shore. Maybe you can.')),),
     '', '', {}),
    ('TeodorDone', 'Teodor Vass', 'SM_CP_Guard', 'bm_daniel', 'human', (-312, 14), 270, ',shepherd,', '',
     ('First quiet watch in nine days. I keep reaching for my rifle. I keep finding a sandwich instead.',), (), '', '', {}),
    ('Ama', 'Doctor Ama Okafor', 'SM_CP_Doctor', 'af_jessica', 'human', (-548, 22), 300, '', '',
     ('You are walking like someone who will need me later. Do not let me be right.',
      'If you are hurt, rest at a Still Point. The Wise built the Commons around three of them, long before anyone knew what they were.'),
     (), '', '', {}),
    ('Listener', 'The Listener', 'SM_CP_Listener', 'bm_fable', 'light', (-566, 104), 250, '', '',
     ('I am of the First Ones. I came to hear the Wise listen. It is a rare sound. I stayed for the bread.',
      'My people on the terrace above the orchards left four stones that remember an order. If you wish to hear them, wake them as the Serene wake: the tallest first.'),
     (('Do you fear us?', ('I fear what both our peoples are becoming. Not you. You are not one of either, I think.',)),), '', '', {}),
    ('Dov', 'Dov Pell', 'SM_CP_Fisher', 'am_adam', 'human', (-120, 40), 120, '', ',pylon2,',
     ('Careful at the water. They put things on the buoys. Red eyes. I can see them from my window all night.',
      'The island lock is theirs. Something that shoots straight could reach the buoys from the shore. I only have a net.'),
     (), '', '', {}),
    ('Rhea', 'Rhea Sato', 'SM_CP_Farmer', 'af_river', 'human', (-150, -150), 60, '', ',pylon1,',
     ('Get down! Oh. You are not one of them. I have been hiding behind this tray for two days.',
      'The pylon up top only turns while the channel runs, and the channel needs three sluices opened in order. I wrote the order on the irrigation board. Read it, and do not get it wrong; it drains and resets.'),
     (), '', '', {}),
    ('Ilex', 'Forge-Mother Ilex', 'SM_CP_Mechanoid', 'am_onyx', 'mechanoid', (-28, 196), 80, '', ',pylon3,',
     ('A visitor who is not made of AL. Welcome to my Foundry. Mind the floors; I banked the furnaces, but they still breathe.',
      'The pylon yard is across the slag channel. The crane holds its bridge up on three cable locks. Cut them with a blade, and the bridge comes down.',
      'I would do it myself, but they put a barricade around my workshop, and I have four arms and no patience.'),
     (), '', '', {}),
    ('IlexThanks', 'Forge-Mother Ilex', 'SM_CP_Mechanoid', 'am_onyx', 'mechanoid', (-28, 196), 80, ',pylon3,', '',
     ('The Foundry pylon sings again. I had forgotten how loud it is.',
      'Take this. A shard of edged light, cut from the old crane\'s heart. It will settle into your blade and make every strike count for more.'),
     (), ',aug_katana4,', '', {'note': 'Katana Augmentation: every katana strike is stronger.'}),

    # The Spire.
    ('Iriel', 'Iriel', 'SM_CP_Lightform', 'af_nova', 'light', (346, -12), 180, ',spire,', ',lightstep,',
     ('You walk like a body. You are not one, not really. You are what everything is made of, folded small.',
      'I am Iriel. We sealed the Spire when the swarm came, because AL cannot be reasoned with and light cannot be held. We were waiting for the Spine. And for you.',
      'At Meridian you were still, and the stillness spread. Light is the other half of that: not stillness, but arrival. Light does not cross a room. It is simply there.',
      'Do not move toward the far side. Be there. Now.'),
     (), ',lightstep,', QUEST_CROWN, {'note': 'Light Step learned: X / |LB|.  Become light for an instant: cross about 7 m, pass through attacks~and enemies, and open Light Lattices. Climb the Spire to its crown.'}),
    ('IrielBase', 'Iriel', 'SM_CP_Lightform', 'af_nova', 'light', (346, -12), 180, ',lightstep,', ',crown,',
     ('The lattices answer to Light Step. Some stay open; some close again after a few breaths, so do not stop to admire them.',
      'The hunters above are AL that copied our speed. They copied nothing else. Step through them.'),
     (), '', '', {}),
    ('IrielCrown', 'Iriel', 'SM_CP_Lightform', 'af_nova', 'light', (360, 14), 200, ',crown,', '',
     ('You climbed it. Good. Look down: the whole drum, and all of it lit.',
      'The Shepherd is in the docks, behind a wall of lattices the swarm grew from our own light. Now you can pass them. Stop it, and the rest will stop.',
      'And Physis: what you just did, you can do anywhere. The Center has lattices of its own. Remember them.'),
     (), '', QUEST_DOCKS, {}),
    ('Wisp', 'Wisp', 'SM_CP_Wisp', 'af_sky', 'light', (552, 262), 0, '', ',wisp,',
     ('Oh! A big one. Are you here to take me home? The lattices closed and I cannot remember how to be quick.',
      'Iriel says I am too young to step. I think I am exactly the right age. Here, take this; it fell off me when I was frightened. I am going home now. The fast way.'),
     (), ',wisp,', '', {'note': 'Agility Augmentation: the moment in which a block becomes a perfect parry is longer.'}),
)
# Wisp's gift: the Agility Augmentation token is given with ,wisp, (the scenario adds it to the reward).
WISP_GIFT = ',aug_agility4,'

CONCLAVE_TUTORIALS = (
    ('Talk: E / |X|     Speak with the people of the Conclave. Pick a topic with up and down~and confirm with Interact. Leave ends a conversation.', (-735, 20), (.6, 3.0, 1)),
    ('Divinity current: step into the light to travel between the Conclave and the Center.', (-748, -6), (.35, 2.0, 1)),
    ('Light Step: X / |LB|     Cross about 7 m as light, through attacks and enemies.~Light Lattices open as you step through them. Jump, then step, to cross a wide gap.', (346, -2), (.6, 3.0, 1)),
)

ARRIVAL_LINE = ('Arrival', 'Divinity speaks. The Conclave, the station of the Wise. Something here is going dark, and the current brought you to it. People are frightened. Find out why.')

# Quest messages (the scenario's switches and relics say these).
MESSAGES = {
    'pylon1': 'The Terrace Pylon wakes. A third of the Spine burns white again.',
    'pylon2': 'The Reservoir Pylon wakes. A third of the Spine burns white again.',
    'pylon3': 'The Foundry Pylon wakes. A third of the Spine burns white again.',
    'spire': 'All three pylons burn. The Spine is whole, and far to the north the Lightform Spire unseals.',
    'pylon_dry': 'The pylon is cold. Whatever powers it has to run first.',
    'sluice1': 'The low sluice opens. Water runs into the channel.',
    'sluice2': 'The middle sluice opens. The channel fills.',
    'sluice3': 'The high sluice opens. The channel runs, and the pylon\'s turbine turns.',
    'anchors': 'The last anchor falls, and the lock over the island fails.',
    'bridge': 'The last cable parts. The crane lets its bridge down across the slag channel.',
    'crown': 'Physis reaches the crown of the Spire. The whole drum lies lit beneath her.',
    'docksgate': 'The lattice wall answers Light Step and stays open.',
    'shepherd': 'The Shepherd falls, and the swarm goes still. Without its orders the AL are only tools again.~Return to Kairos in the Commons.',
    'page': 'A page of the Ledger of Names. Petra Lune at the Archive is looking for it.',
    'pages': 'The last page of the Ledger. Petra Lune at the Archive will want all three.',
    'kite': 'Tamsin\'s kite, a little burnt. She is waiting in the Commons.',
    'core': 'Halden-7\'s memory core. Halden is in the Mendery, in the Commons.',
    'seedpod': 'Orsolya\'s Starlace seed pod. She is in the garden at the Wellspring.',
    'arrive': 'The Conclave.~The current has carried Physis to the station of the Wise.',
}


def person_key(key, page):
    """The voice title of one page of a conversation (BP_LogVoice.Title, physis_lore.voice_name)."""
    return 'Talk %s %d' % (key, page)


def conversation_pages(person):
    """Every page of a person's conversation, in order: the greeting, then each topic's answer."""
    greeting, topics = person[9], person[10]
    pages = list(greeting)
    for _, answer in topics:
        pages.extend(answer)
    return pages


def conclave_entries():
    """Logbook rows (category, title, text) for every scan, lock kind and enemy."""
    rows = [row[:3] for row in CONCLAVE_SCANS] + list(CONCLAVE_GATES) + [entry[4] for entry in CONCLAVE_ENEMIES.values()]
    return rows
