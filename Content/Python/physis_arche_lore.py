"""Text for level 5, Arche, the First Ones' Planet: Kathodos, the city of the Descent. Divinity's scans, the people's
conversations, enemies, tutorials and quest messages. Voices come from Tools/build_physis_voice.py --arche. Places are
plan metres (physis_arche_plan: x north, y east); a z of None puts a scan marker 1.5 m above the ground, a number is
centimetres.

Conversations (PEOPLE) work as in the Conclave and the Grove: a person appears while their Show token is held (or
always, '') and until their Hide token is held; a greeting, then topics, then Leave. When the greeting ends the
first time the person gives Give, sets the quest to Quest and grants any reward.

In-game text names actions, not keys; only the tutorial strips and the "learned" line show inputs.
"""
import physis_arche_plan as plan

# ---------------------------------------------------------------- Divinity's scans

# Category, title, text, (x, y, z or None), important.
ARCHE_SCANS = (
    # Places.
    ('Rooms', 'The Landing', 'Divinity speaks. Arche, the world the First Ones call the Beginning. The current that carried you here returns to the Center from this pool. Above you the city of Kathodos climbs in three tiers to the Lens. This is a Still Point.', (-494, 30, None), True),
    ('Rooms', 'The Processional', 'Divinity speaks. The road every First One walked once, down from the heights to be named, and up again to be remembered. The columns are older than the species that is at war with them.', (-430, 50, None), True),
    ('Rooms', 'The Hearthold', 'Divinity speaks. What is left of the people of Kathodos: the Serene, who would not leave and would not fight. They have lived on this one tier since the city was unwoven. The Lens\'s keepers do not come here. They were never told the Serene were an enemy.', (-296, 8, None), True),
    ('Rooms', 'The First Arch', 'Divinity speaks. The oldest standing thing in Kathodos, and the only one the unweaving did not take. The stone here remembers being raised. Aeon says it can be heard, by someone who is made of what it is made of.', (-219, 36, None), True),
    ('Rooms', 'The Great Chasm', 'Divinity speaks. The river that cut this is gone. A bridge crossed here, the Span, the widest in the city. Its stones are still above you. Nothing that walks, leaps or links will carry you over; if you fall, the knots on either rim will draw you out.', (-164, 22, None), True),
    ('Rooms', 'The Concourse', 'Divinity speaks. Where the Lower Tier\'s ways part: west to the Cisterns, north to the First Stair and the tiers above. Three great mirrors once lit this city by turning the Lens\'s light. This is a Still Point.', (-66, 16, None), True),
    ('Rooms', 'The Cisterns', 'Divinity speaks. Kathodos kept its water here, in a bowl the First Ones lined by hand. The western Mirror stands on the island. The causeway to it was unwoven with everything else, and what is rewoven over water does not hold for long.', (10, -156, None), True),
    ('Rooms', 'The Middle Tier', 'Divinity speaks. The second tier, where the city\'s makers lived. East lies the Crystal Garden; north, the Second Stair, in pieces above its own footings.', (132, 16, None), True),
    ('Rooms', 'The Crystal Garden', 'Divinity speaks. The First Ones grew these as other peoples grow trees, over ten thousand years. The eastern Mirror stands on the pinnacle. The Garden\'s old looms will hold a few shapes at a time and no more: choose which.', (144, 202, None), True),
    ('Rooms', 'The Galleries', 'Divinity speaks. A mesa the First Ones carved into halls and then lost the stairs to. The northern Mirror stands on its top, sixty feet up. The way is in the air, in pieces.', (314, 220, None), True),
    ('Rooms', 'The Lens Court', 'Divinity speaks. The Vigil\'s wall, and in it the Veil: hard light, woven by the Lens itself. Nothing you carry opens it. It was made to fall only if the city\'s three Mirrors were turned on it, which the Vigil made sure could never happen again.', (316, 8, None), True),
    ('Rooms', 'The Sundering Lens', 'Divinity speaks. A thing that unweaves. It does not break what it strikes: it makes it forget its shape. The Vigil raised it to keep the sky empty, and fed it their own city when it was hungry. Its keeper is the Sunderer.', (412, 10, None), True),
    ('Rooms', 'The Ossuary of Names', 'Divinity speaks. The First Ones do not bury bodies. They keep names, cut in stone, and they keep them here. A vault below still holds something the Serene set aside.', (-326, 262, None), False),
    # Story.
    ('Story', 'The Unweaving', 'Recorded by the Serene. When the first human engines crossed our sky, the Vigil asked the city for its bridges. They said a people who cannot be reached cannot be harmed. We said a people who cannot be reached are already gone. They took the bridges. We were both right.', (-284, -22, None), False),
    ('Story', 'The Count', 'Recorded by Aeon. I have counted the stones that hang over Kathodos: four hundred thousand and eleven. Each one knows where it stood. I have asked them. It is the Lens that will not let them go home.', (-270, 16, None), False),
    ('Story', 'The Ward', 'Divinity speaks. The Lens\'s keepers are AL: tools without will, the same the Vigil sent against Meridian. These were never sent anywhere. They were told to keep the city in pieces, and nothing has told them otherwise.', (-380, 34, None), True),
    ('Story', 'What the Vigil Feared', 'Recorded by Maruth, Lens-keeper of the Vigil. We watched a young species find Divinity and, within one lifetime, make a weapon of it. We had needed ten thousand years to be sure we never would. I do not ask to be forgiven for being afraid. I ask whether you would not have been.', (336, -14, None), False),
    ('Story', 'The Air-Swimmers', 'Divinity speaks. Arche had animals before it had First Ones: soft things that swim in the air, with crystal in their flesh. The Serene fed them from the terraces. The Lens has made them forget what they were, as it does to everything. They are not your enemy. They do not know that.', (-60, 60, None), True),
    ('Story', 'The Makers\' Row', 'Recorded by a maker of the Middle Tier. We built nothing here that could not be taken apart by the hands that built it. That was our law, and I was proud of it until I saw it used.', (150, -30, None), False),
    # How things work.
    ('Items', 'Sundered Stone', 'Divinity speaks. Stone the Lens has unwoven. It has not fallen, because it has forgotten that it has weight. Where a ring of slivers turns round a pearl of light, something can be made to remember its shape: look at it and Reweave.', (-158, 36, None), True),
    ('Items', 'Restless Stone', 'Divinity speaks. Some things you reweave will not stay. This near the Lens, or over water, a shape holds only as long as the stone can keep hold of the memory, and then lets go. Cross while it stands.', (16, -172, None), True),
    ('Items', 'Loom', 'Divinity speaks. An old maker\'s loom: a frame that holds shapes for the stones round it. It holds only so many. Reweave one more and the oldest lets go. What you need is rarely everything at once.', (150, 214, None), True),
    ('Items', 'Bulwark', 'Divinity speaks. A wall that was unmade. Reweave it and it will stand for a little while between you and whatever is firing at you.', (-20, 30, None), True),
    ('Items', 'Great Mirror', 'Divinity speaks. One of the three mirrors that carried the Lens\'s light down into the city. Its frame was unwoven so that it could never be turned. Reweave it, and it will turn toward the Veil of its own accord: it remembers that too.', (24, -200, 1050), True),
    ('Items', 'The Veil', 'Divinity speaks. The Veil waits for three lights: the Mirror of the Cisterns, the Mirror of the Garden and the Mirror of the Galleries. Each one that turns thins it. All three, and it is gone.', (320, -8, None), True),
    ('Items', 'Geode Cache', 'Divinity speaks. A stone the Serene split and filled with Divinity against a bad season. Walk into it to take what it holds. There are others in the city.', (-470, 12, None), False),
    ('Items', 'Divinity Current', 'Divinity speaks. A current of Divinity between Arche and the Center. Step into its light and it will carry you across.', (-504, 14, None), True),
    # Relics: their tags ride on BP_Relic (RelicTag, by token).
    ('Items', 'Ilun\'s Chime', 'Divinity speaks. A wind chime of the Serene, tuned to the Cisterns. It is Ilun\'s, lost when the Garden\'s stair was unwoven under it. Walk into it to take it, then bring it to Ilun at the Hearthold.', (188, 282, None), True),
    ('Items', 'A Record Tablet', 'Divinity speaks. A leaf of the city\'s record. Three were scattered when the Makers\' Row came apart: one at the Ossuary, one on the Middle Tier, one on the Galleries\' mesa. Walk into each to take it, then bring them to Oreth at the Hearthold.', (-320, 280, None), True),
    ('Items', 'A Seedstone', 'Divinity speaks. A seed of the Crystal Garden, the last the Serene set aside. It lies on the Mirror\'s island in the Cisterns. Walk into it to take it, then bring it to Sael at the Hearthold.', (20, -210, None), True),
    ('Items', 'The Lens\'s Heart', 'Divinity speaks. A Health Augmentation, left where the Sunderer fell: the part of the Lens that held things together, before it was told to hold them apart. Walk into it, and Physis gains a Health Tank and is whole again.', (424, 0, None), True),
    ('Items', 'The Namer\'s Edge', 'Divinity speaks. A Katana Augmentation: the chisel-steel the namers cut names with, kept in the Ossuary\'s vault. Walk into it, and every katana strike is stronger.', (-338, 290, None), True),
)

# What each kind of lock is (Logbook entries without a marker of their own).
ARCHE_GATES = (
    ('Items', 'Sealed Vault', 'Divinity speaks. A vault of the First Ones, sealed with a lock you cannot open yet. Remember where it stands: what opens it is learned elsewhere.'),
)

# Enemies by level: mesh (the Conclave's AL: the same machines, at home), health, scale, hover height (cm), Logbook
# entry, EnemyKind (0 plain, 1 turns light blows, 3 fast, 4 its face turns every blow).
ARCHE_ENEMIES = {
    1: ('SM_CE_ALMite', 5, 1.0, 130, ('Enemies', 'Ward Mite', 'Level 1. The smallest AL of the Lens\'s Ward, and the commonest. Quick, and never alone. Five health.'), 3),
    2: ('SM_CE_ALLancer', 9, 1.0, 160, ('Enemies', 'Ward Lancer', 'Level 2. An AL that holds its distance and fires long volleys. Parry just before a bolt lands, dodge, or reweave a bulwark and let it waste its fire. Nine health.'), 0),
    3: ('SM_CE_ALBulwark', 16, 1.0, 180, ('Enemies', 'Ward Bulwark', 'Level 3. A heavy AL plated against the blade. Light blows glance off it: strike heavy, Settle it, or tether it to something softer. Sixteen health.'), 1),
    4: ('SM_CE_EchoHunter', 20, 1.0, 200, ('Enemies', 'Ward Hunter', 'Level 4. Fast, and it never stays put. Light Step through its volleys and strike as it turns. Twenty health.'), 3),
    5: ('SM_CE_ALReaver', 26, 1.0, 210, ('Enemies', 'Ward Reaver', 'Level 4. The Ward\'s guard, set over what the Vigil most wanted kept apart: the Mirrors and the stairs. Twenty-six health.'), 0),
    6: ('SM_CE_ALSiegeframe', 60, 1.0, 360, ('Enemies', 'Ward Siegeframe', 'Level 5, end-game. It walks the Ossuary road because nothing ever told it to stop. You do not have to fight it. Sixty health.'), 0),
    7: ('SM_AE_Sunderer', 120, 1.0, 520, ('Enemies', 'The Sunderer', 'Boss. The Lens\'s own keeper. Its face turns every blow and its fire unweaves cover in moments: reweave the bulwarks as you move, get behind it, or tether it to its own Ward. One hundred and twenty health.'), 4),
    # Arche's own animals: living things, maddened by the Lens. They are not destroyed: struck enough, one scatters
    # like breath on glass and gathers again far off (the game's rule for the living; GAME_ROADMAP.md "Fighting").
    8: ('SM_AE_Mote', 4, 1.0, 140, ('Enemies', 'Drift Mote', 'Level 1. A small air-swimmer of Arche, older than the city. The Lens has made it frantic. It comes in shoals and darts. Strike it and it scatters like breath on glass, to gather again somewhere quieter. Four health.'), 3),
    9: ('SM_AE_Medusa', 9, 1.0, 190, ('Enemies', 'Bell Medusa', 'Level 2. A drifting bell with long tendrils. It is not hunting you. It is in pain, and you are near. When it tips back and calls, it is about to turn and lash: step out of its reach, or parry the lash. Nine health.'), 0),
    10: ('SM_AE_Shellback', 18, 1.0, 170, ('Enemies', 'Shellback', 'Level 3. A grazer in a grown shell, crystal in every seam. Light blows glance off the shell: strike heavy, Settle it, or tether it to something softer. Eighteen health.'), 1),
    11: ('SM_AE_Ray', 20, 1.0, 230, ('Enemies', 'Sky Ray', 'Level 4. The fastest thing in Kathodos, a wing with a tail, and the tail is the weapon. It never holds still. When it banks and calls, step aside from the whip, then strike as it turns. Twenty health.'), 3),
    12: ('SM_AE_Stalker', 28, 1.0, 220, ('Enemies', 'Crest Stalker', 'Level 4. A hunter that keeps a territory, and the Lens has left it nothing else. The violet in its fractures is the unweaving, not its own light. Parry it, and strike while it recovers. Twenty-eight health.'), 0),
    13: ('SM_AE_Leviathan', 70, 1.0, 620, ('Enemies', 'Leviathan', 'Level 5, end-game. The oldest animal on Arche, circling the Ossuary where it has always circled. One great wound from the Lens has not closed. You do not have to fight it. If you do, it will scatter and gather again by morning, and remember nothing. Seventy health.'), 0),
}

# ---------------------------------------------------------------- people

QUEST_ARRIVE = 'Follow the Processional north to the Hearthold'
QUEST_ARCH = 'Go to the First Arch, north of the Hearthold, and listen to the stone'
QUEST_SPAN = 'Reweave the Span and cross the Great Chasm'
QUEST_MIRRORS = 'Reweave the three Mirrors: in the Cisterns, the Crystal Garden and the Galleries'
QUEST_VEIL = 'All three Mirrors are turned. Climb to the Lens Court'
QUEST_SUNDERER = 'Stop the Sunderer, in the Lens Court'
QUEST_MARUTH = 'Speak to Maruth, the Lens-keeper, in the Lens Court'
QUEST_AEON = 'Return to Aeon at the Hearthold'
QUEST_DONE = 'Walk the city, or return to the Center from the Landing'
# Set once by the Center's temple current to Arche when it opens (the Warden fallen, Arche not yet visited).
QUEST_CURRENT = 'A new Divinity current has opened in the sanctum. Step into it to follow it to the First Ones\' world'

H = plan.HEARTHOLD
MARUTH_SPOT = (plan.COURT[0] + 20.0, plan.COURT[1] + 44.0)
STONE_GATE = (plan.GATE[0] - 12.0, plan.GATE[1] - 10.0)   # the speaking stone before the Veil

# key, speaker, mesh, voice, kind, (x, y), yaw, show, hide, greeting pages, topics, give, quest, reward
PEOPLE = (
    ('Aeon', 'Aeon', 'SM_AP_Aeon', 'bm_george', 'firstone', (H[0] + 6.0, H[1] - 4.0), 200, '', ',reweave,',
     ('You came down the old road. Nothing has come down that road in a very long time that did not mean to burn it.',
      'I am Aeon. I was old when your kind first looked up. I have been here since the bridges went, counting what hangs in the air, because someone should know the number.',
      'This was Kathodos, the Descent. The Vigil, who are my people too, built a Lens at its head that makes things forget their shape. When your ships came they turned it on our own city, so that no one could ever walk it. It worked. No one has.',
      'You are made of the thing the Lens works in. I have waited to see whether that thing could remember as well as forget. Come to the First Arch, north of here. I will show you what I think you are for.'),
     (('Who are the Serene?', ('Those of us who would not leave, and would not fight. The Vigil call that doing nothing. It is the hardest work I know.',
                               'There are forty of us on this tier. There were more. Waiting costs, even if you are good at it.')),
      ('Why did the Vigil do this?', ('Because they were afraid, and they were not wrong to be. We have watched many peoples find Divinity. Most of them are not there to watch any more.',
                                      'Fear is not the Vigil\'s fault. What they built out of it is.')),
      ('What do you see in me?', ('A weight that does not fall. Something that has not decided what shape to be. I mean that as praise. I decided a long time ago, and I have regretted how early.',))),
     ',aeon,', QUEST_ARCH, {}),
    ('AeonWeave', 'Aeon', 'SM_AP_Aeon', 'bm_george', 'firstone', (H[0] + 6.0, H[1] - 4.0), 200, ',reweave,', ',sunderer,',
     ('I felt the Arch answer you from here. Four hundred thousand and eleven stones, and for the first time in my count one of them moved toward home.',
      'The Lens holds the city apart, and the Veil holds you from the Lens. Three great Mirrors once carried its light down the tiers: at the Cisterns, in the Crystal Garden, on the Galleries\' mesa. Turn all three on the Veil and it will not stand.',
      'Reweave the Span first. I would like to see it once more with something walking on it.'),
     (('How does reweaving work?', ('You do not build. You remind. Look at a thing that has been unmade, where the slivers turn, and it will take its shape from its own memory.',
                                    'Near the Lens the memory is thin, and over water it washes out. Such things stand a little and let go. And the old looms hold only a few shapes at once: choose.')),
      ('Will it hold?', ('The Span will. The stairs will. They were the city\'s bones, and bones remember longest.',))),
     '', QUEST_SPAN, {}),
    ('AeonDone', 'Aeon', 'SM_AP_Aeon', 'bm_george', 'firstone', (H[0] + 6.0, H[1] - 4.0), 200, ',sunderer,', '',
     ('I have lost my count. The stones are going home faster than I can number them. I find I do not mind.',
      'You did not break the Lens. You gave the city back its memory, and the Lens had nothing left to hold apart. The Vigil will say you destroyed their defence. Maruth knows better. Maruth watched.',
      'There are others like this, on this world and on yours. Fewer of ours, and older, and each one built by someone who was afraid for a good reason. Remember the reason when you unmake the thing.',
      'The current at the Landing will take you back whenever you wish. Kathodos is yours to walk. For the first time since I began counting, it can be walked.'),
     (('What will the Serene do?', ('Cross the Span. Some of us have family on the upper tiers we have not touched in an age. After that, I think, we will argue with the Vigil. We are owed a very long argument.',)),
      ('And you?', ('I will sit on the First Stair and watch people use it. I have wanted to for longer than your world has had cities.',))),
     ',arche_done,', QUEST_DONE, {'divinity': 60, 'heal': True, 'note': 'Aeon\'s thanks: 60 Divinity, and you are fully healed.'}),
    ('Ilun', 'Ilun', 'SM_AP_Serene0', 'bf_emma', 'firstone', (H[0] - 14.0, H[1] + 12.0), 130, '', ',chime,',
     ('Stranger. Forgive the lantern. I keep the Cisterns, and the Cisterns are across a chasm I cannot cross, so I keep the lantern instead.',
      'I am Ilun. When the stair in the Garden went, my chime went with it: I had hung it on the pinnacle to hear the water from there. It is the only thing I own that was tuned by my teacher.',
      'If your road takes you up to the Garden\'s Mirror, it will be near. I would know its voice anywhere.'),
     (('What were the Cisterns?', ('Every drop this city drank, and every drop it gave back. We kept the water the way the namers keep names. It is still clean. I checked it from here, by the light on it.',)),),
     ',ilun,', '', {}),
    ('IlunThanks', 'Ilun', 'SM_AP_Serene0', 'bf_emma', 'firstone', (H[0] - 14.0, H[1] + 12.0), 130, ',chime,', '',
     ('That is its voice. Do not tell me where it lay. Let me believe it waited on the pinnacle the whole time, ringing.',
      'Take this. It is a keeper\'s ward, cut for those who stand in water while others throw stones. It will make what strikes you matter less.'),
     (), ',aug_defense6,', '', {'note': 'Defense Augmentation: every hit you take costs you less.'}),
    ('Oreth', 'Oreth', 'SM_AP_Serene1', 'bm_lewis', 'firstone', (H[0] + 16.0, H[1] + 14.0), 215, '', ',tablets,',
     ('You are the one the stones have been leaning toward. Good. I have a use for someone the stones like.',
      'Oreth, of the record. When the Makers\' Row was unwoven, three leaves of the city\'s record went with it. Without them we know that Kathodos was built, and not why.',
      'One fell by the Ossuary, one on the Middle Tier, and one, I am sorry to say, on top of the Galleries. Bring them home and I can tell the Vigil exactly what they unmade.'),
     (('What is in the record?', ('Who raised each tier, and who they raised it for. The Vigil fed the Lens a city. I want them to hear its names.',)),),
     ',oreth,', '', {}),
    ('OrethThanks', 'Oreth', 'SM_AP_Serene1', 'bm_lewis', 'firstone', (H[0] + 16.0, H[1] + 14.0), 215, ',tablets,', '',
     ('All three. And legible. You have no idea how rarely those two things arrive together.',
      'A recorder\'s gift, then: the knack of the exact moment. It is how we know when to cut and when to wait. You will find more room in the instant a blow lands.'),
     (), ',aug_agility6,', '', {'note': 'Agility Augmentation: the moment in which a block becomes a perfect parry is longer.'}),
    ('Sael', 'Sael', 'SM_AP_Serene2', 'af_nicole', 'firstone', (H[0] - 2.0, H[1] + 22.0), 180, '', ',seedstone,',
     ('Are you the weight that does not fall? Aeon talks about you. Aeon does not talk about anything.',
      'I am Sael. I am the youngest here: I am only nine hundred. I have never seen the Garden. They say crystal grows there the way I grow impatient.',
      'There is one seedstone left, on the Mirror\'s island in the Cisterns. If you bring it I will plant it right here, where I can watch it, and it will be the first new thing in Kathodos in my whole life.'),
     (('Is it hard, waiting?', ('The old ones are better at it. I keep thinking something is about to happen. Today I was right, which will make me unbearable.',)),),
     ',sael,', '', {}),
    ('SaelThanks', 'Sael', 'SM_AP_Serene2', 'af_nicole', 'firstone', (H[0] - 2.0, H[1] + 22.0), 180, ',seedstone,', '',
     ('It is warm. Nobody said it would be warm.',
      'Here: the lens from my lantern. It gathers light to one point. I think you throw things; it should help them arrive.'),
     (), ',aug_pistol5,', '', {'note': 'Pistol Augmentation: every shot strikes harder, the Divinity Shot too.'}),
    # Maruth, Lens-keeper of the Vigil: a voice in the speaking stone before the Veil, then in person.
    ('MaruthStone', 'Maruth', 'SM_AN_Obelisk', 'bm_daniel', 'stone', STONE_GATE, 180, '', ',sunderer,',
     ('Stop there. This stone carries my voice; the rest of me is behind the Veil, where I intend to remain. I am Maruth. I keep the Lens.',
      'I know what you are doing with the Mirrors. I ordered their frames unwoven myself, so that this could never be done. I did not account for someone who could ask a stone to remember.',
      'Understand what you open. The Lens is the reason no human engine has ever stood over this world. Take it away and we are a city of old people under an open sky.',
      'I cannot stop you. The Sunderer does not take my orders: I made certain of that too, once, for reasons that seemed wise. I only wanted you to hear it from someone who is not Serene.'),
     (('The fleets have stopped.', ('I felt it. A silence is not a peace. I have outlived more silences than your species has had wars.',)),
      ('Why unweave your own city?', ('Because a wall that can be walked round is not a wall. I told myself the stones were only waiting. I have had a long time to hear how that sounds.',))),
     '', '', {}),
    ('Maruth', 'Maruth', 'SM_AP_Vigil', 'bm_daniel', 'firstone', MARUTH_SPOT, 250, ',sunderer,', '',
     ('It is quiet. I had forgotten the Lens made a sound until it stopped making it.',
      'I kept this place for longer than your kind has written anything down. I was certain every day. That is what I would warn you about, if you would take a warning from me: not fear. Certainty.',
      'The stones are going back. I gave the order that scattered them and I could not have given the one that calls them home. You did it by asking.',
      'Take what the Sunderer left. And when you come to the others like me, and you will, tell them Maruth of the Vigil stood under an open sky and it did not fall on him.'),
     (('Will the Vigil forgive this?', ('Some. The rest will need to see the sky stay empty for a few hundred years. We are slow. It has kept us alive.',)),
      ('Will you cross the Span?', ('Aeon has been waiting at the far end of it since before your Rome. I think I had better.',))),
     ',maruth,', QUEST_AEON, {'note': 'Maruth has nothing to give but his word, and gives it.'}),
)

# The keepers who stayed at their posts across the city (author, 2026-11-17: the level felt empty): each has a
# greeting and one thing to ask. They give nothing and want nothing.
def keeper(key, mesh, voice, spot, yaw, greeting, question, answer):
    return (key, key, mesh, voice, 'firstone', spot, yaw, '', '', greeting, ((question, (answer,)),), '', '', {})


KEEPERS = (
    keeper('Thessin', 'SM_AP_Serene2', 'bf_isabella', (plan.LANDING[0] + 14.0, plan.LANDING[1] - 20.0), 60,
           ('You came by the current. I felt the pool rise before I saw you. I am Thessin. I keep the Landing, which until today meant keeping an empty pool.',
            'The road north is the Processional. It is watched by the Ward, the Lens\'s machines, and by the air-swimmers, who were gentle before the Lens. Neither will listen to me. They may listen to you.'),
           'What is the current?', 'Divinity, moving. It runs between worlds the way water runs between pools. When you are done here, stand in it again and it will carry you back the way you came.'),
    keeper('Vael', 'SM_AP_Serene1', 'bm_daniel', (-388.0, 6.0), 40,
           ('Walk softly here. The Drift Motes shoal along this road at this hour, and they bite first now.',
            'I am Vael. I counted them every evening for the record. I still count. There are fewer each year, and they come back from being struck remembering less.'),
           'Can they be helped?', 'Stop the Lens and I think they will quiet. Until then, when one calls and draws back, step aside. It is not hunting. It is frightened, and you are near.'),
    keeper('Corun', 'SM_AP_Serene0', 'bm_fable', (plan.FIRST_ARCH[0] - 8.0, plan.FIRST_ARCH[1] + 15.0), 300,
           ('Put your hand on the stone if you like. It is leaning toward you. They all are, since you came down the road.',
            'Corun. I listen to stone. Every block in Kathodos remembers the shape it was cut for. The Lens made them forget each other, not themselves. That is why they hang, and do not fall.'),
           'Why do the stones hang?', 'Because nothing told them to stop being a bridge. Ask them, the way Aeon will show you, and they will come home in the order they were laid.'),
    keeper('Halae', 'SM_AP_Serene2', 'bf_alice', (plan.chasm_x(52.0) - plan.CHASM_RIM - 12.0, 56.0), 20,
           ('You are not the first to look over that edge and wonder. Most who go down did not mean to.',
            'I am Halae. I hung these slabs against the wall myself, one each season, so that anyone who falls can walk out again. It comes up on this side only. I will not build a way round the Span.'),
           'Where is the way up?', 'On the floor of the Chasm, east of the Span, look for two lanterns. The slabs rise from there along the south wall to where we are standing.'),
    keeper('Imreth', 'SM_AP_Serene1', 'bm_lewis', (plan.CONCOURSE[0] - 9.0, plan.CONCOURSE[1] - 16.0), 70,
           ('Three ways part here. Ahead, the First Stair, which is broken. West, the trail to the Cisterns. And behind you, the only bridge, which I am told is standing again.',
            'Imreth. I kept the Concourse when it was a market. Now I keep count of which bulwarks are whole. It is a short count.'),
           'What are the bulwarks?', 'Walls that will not stay. Reweave one and it holds for a while, long enough to stand behind when the Ward fires. Then it lets go. Do not take it personally. Nothing here stays until the Lens stops.'),
    keeper('Sova', 'SM_AP_Serene0', 'bf_lily', (plan.CISTERN_SHORE[0] - 10.0, plan.CISTERN_SHORE[1] + 9.0), 250,
           ('Do not drink until you have looked. The water is clean, but the Medusae come down to it in the evening, and their tendrils reach further than they seem.',
            'I am Sova, Ilun\'s student. She keeps the lantern at the Hearthold. I keep the shore, and wait for the day she can cross and tell me everything I have done wrong.'),
           'How do I reach the island?', 'There were causeways. They are there still, in pieces, above the water. Some will hold once rewoven, and some are restless and will let go under you. Cross quickly, and look before each one.'),
    keeper('Deluin', 'SM_AP_Serene1', 'bm_george', (plan.STAIR1[0] + 22.0, -16.0), 160,
           ('You climbed the First Stair. Then it is true, and I owe Oreth an apology and a jar of salt.',
            'Deluin. This was the makers\' tier. Every house you see hanging in pieces up here was a workshop. We made the Mirrors here, and the Lens, to our shame.'),
           'What do the Mirrors do?', 'They turn light. Three of them, turned on the Veil together, will open it. The Vigil unmade them so that no one could. One is in the Cisterns, one in the Crystal Garden, one on the Galleries.'),
    keeper('Arath', 'SM_AP_Serene2', 'bf_emma', (plan.GARDEN_STILL[0] - 12.0, plan.GARDEN_STILL[1] - 8.0), 30,
           ('Mind the tall ones. A great crystal sings when you pass, and the Sky Rays come to the singing.',
            'I am Arath. I tend the Garden. It does not need tending. Crystal grows whether or not anyone watches. But someone should watch.'),
           'What is the loom?', 'The stepping stones in the Garden share one memory. Reweave a new one and the oldest lets go. Think about which stone you are standing on before you ask for another.'),
    keeper('Nemi', 'SM_AP_Serene0', 'bf_isabella', (plan.STAIR2[0] + 24.0, 18.0), 200,
           ('This high, the Lens is loud. You feel it in your teeth. I have stopped noticing, which frightens me more than the noise did.',
            'Nemi. I was of the Vigil, once. I left when Maruth lit the Lens. I could not unmake it, so I stayed where I could see it, to be sure I never forgot what we did.'),
           'What is inside the Court?', 'A ring wall, a veil of light across its gate, and behind it the Sunderer, which is the Lens\'s own hand. Its face turns every blow. Get behind it. And do not hate Maruth. Maruth was afraid, as all of us were.'),
)
PEOPLE = PEOPLE + KEEPERS

ARCHE_TUTORIALS = (
    ('Divinity current: step into the light to travel between Arche and the Center.', (plan.LANDING[0] + 8.0, plan.LANDING[1] + 6.0), (.35, 2.0, 1)),
    ('Reweave: B / |R3|     Look at a turning ring of slivers and reweave: the thing remembers its shape.', (plan.SPAN_SOUTH[0] - 16.0, plan.SPAN_SOUTH[1]), (.6, 3.0, 1)),
    ('Restless stone holds only a few seconds: reweave the next piece from the one you stand on.', (plan.CISTERN_SHORE[0], plan.CISTERN_SHORE[1]), (.6, 3.0, 1)),
    ('Bulwarks: reweave a broken wall for cover. It stands a little while, then lets go.', (plan.CONCOURSE[0] + 30.0, plan.CONCOURSE[1]), (.6, 3.0, 1)),
)

ARRIVAL_LINE = ('Arrival on Arche', 'Divinity speaks. Arche. The Beginning. A city that was taken apart by the people who built it, and left hanging. Every stone above you knows where it belongs. Find who is still here, and listen.')

ARCH_DONE = ('Aeon lays a hand on the First Arch, and Physis hears it: every stone remembering the one beneath it.~'
             'Reweave learned: B / |R3|.  Look at a turning ring of slivers and reweave, and the thing takes its shape again.~'
             'The city\'s bones hold for good. Restless stone holds a little while. A loom holds only so many shapes.~'
             'The Span lies north of here. Reweave it.')

MESSAGES = {
    'arrive': 'Arche.~The current has carried Physis to the First Ones\' world.',
    'arch_denied': 'An arch of pale stone, older than anything else here. Aeon, at the Hearthold, keeps it.',
    'span': 'Four hundred stones come down out of the air and the Span stands across the Chasm.',
    'stair1': 'The First Stair knits itself, tread by tread, up to the Middle Tier.',
    'stair2': 'The Second Stair takes its shape again. The Upper Tier is open.',
    'mirror_w': 'The Mirror of the Cisterns turns toward the Veil.',
    'mirror_e': 'The Mirror of the Garden turns toward the Veil.',
    'mirror_n': 'The Mirror of the Galleries turns toward the Veil.',
    'mirror_guard': 'The Ward is down. The Mirror\'s frame can be rewoven.',
    'veil': 'Three lights meet on the Veil, and it is gone.~The Lens Court is open.',
    'veil_wait': 'The Veil stands. It waits for the three Mirrors.',
    'sunderer': 'The Sunderer falls, and the Lens goes dark. All over Kathodos, stone begins to come down.~Maruth, the Lens-keeper, is in the court.',
    'chime': 'Ilun\'s chime. Ilun keeps a lantern at the Hearthold.',
    'tablet': 'A record tablet. Oreth, at the Hearthold, is looking for three.',
    'tablets': 'The last record tablet. Oreth, at the Hearthold, will want all three.',
    'seedstone': 'A seedstone. Sael, at the Hearthold, wants to plant it.',
    'heart': 'The Lens\'s Heart. Health Augmentation: one more Health Tank, and you are fully healed.',
    'edge': 'The Namer\'s Edge. Katana Augmentation: every katana strike is stronger.',
    'vault': 'The vault\'s stair is whole again.',
    'cache': 'A geode cache. Divinity +40.',
}


def person_key(key, page):
    return 'Talk %s %d' % (key, page)


def conversation_pages(person):
    greeting, topics = person[9], person[10]
    pages = list(greeting)
    for _, answer in topics:
        pages.extend(answer)
    return pages


def arche_entries():
    """Logbook rows (category, title, text) for every scan, lock kind and enemy."""
    return [row[:3] for row in ARCHE_SCANS] + list(ARCHE_GATES) + [entry[4] for entry in ARCHE_ENEMIES.values()]
