"""Text for level 8, Morrow, the Valley Before Morning, on Earth. Divinity's scans, the people's conversations, the
Stilled, the Morning's memories, the spoken final stage, enemies, tutorials and quest messages. Voices come from
Tools/build_physis_voice.py --morrow. Places are plan metres (physis_morrow_plan: x north, y east); a z of None puts a
scan marker 1.5 m above the ground, a number is centimetres.

Conversations (PEOPLE) work as in every level: a person appears while their Show token is held (or always, '') and until
their Hide token is held; a greeting, then topics, then Leave.

The Stilled (STILLED) are people the Rime caught. Sitting with one for its Hold wakes them: what Physis sees (narration)
and what they say (speech, voiced as "Talk <key> 0" in their own voice) show together, and they give their token. The
Morning's memories (MEMORIES) are sat with in the same way. The spoken final stage (STAGE) plays line by line while she
sits with the kneeling Unrisen; Maren's lines are voiced ("Talk MarenStage <k>"), the narration is not.

All of this is new writing for the author to review (GAME_ROADMAP.md "Level 8").
In-game text names actions, not keys; only the tutorial strips and the "learned" line show inputs.
"""
import physis_morrow_plan as plan

# ---------------------------------------------------------------- Divinity's scans

# Category, title, text, (x, y, z or None), important.
MORROW_SCANS = (
    # Places.
    ('Rooms', 'The Pass Chapel', 'Divinity speaks. Morrow, on Earth: a valley high in the northern mountains. The chapel on the pass, where travellers stopped to give thanks for getting over. The current that carried you here returns to the Center from this pool. This is a Still Point.', (-494, 10, None), True),
    ('Rooms', 'The Orchard Road', 'Divinity speaks. Apple trees in rows, every twig furred white. The fruit was never picked; it hangs frozen, the colour of the hour before sunrise. Something is holding this whole valley still.', (-420, 30, None), True),
    ('Rooms', 'The Mill House', 'Divinity speaks. The miller\'s house by the pond, and the only chimney in the valley with smoke coming out of it. Someone here keeps a fire. Someone here is not Stilled.', (-296, -10, None), True),
    ('Rooms', 'Edda\'s Bench', 'Divinity speaks. A bench by the frozen millpond, with a small brass plate on its back. A name is cut in it, and two dates twenty years old.', (-222, -34, None), True),
    ('Rooms', 'The Gorge', 'Divinity speaks. The river\'s gorge, frozen to its bed. The Ferry Bridge crossed it here; the Rime has heaped over it. Its keeper stands at the south end, as still as the ice.', (-166, 30, None), True),
    ('Rooms', 'Chapel Square', 'Divinity speaks. The town\'s square, where its ways part: west to the Schoolhouse, east up to the Glider Field and the Telegraph House, north along the Dam Road to the dam.', (-70, 12, None), True),
    ('Rooms', 'The Schoolhouse', 'Divinity speaks. The valley\'s one school. The Rime has grown round its yard in walls. Its teacher stands at the door, where she was standing when she heard.', (-10, -190, None), True),
    ('Rooms', 'The Glider Field', 'Divinity speaks. A bench of level ground above the town, where the gliding club flew in summer. A glider rests on the frost by the hangar, one wingtip down, as if it had only just landed.', (0, 190, None), True),
    ('Rooms', 'The Telegraph House', 'Divinity speaks. The valley\'s telegraph, on its rock. Every message that came into Morrow came in here first, down the wire from the Front.', (190, 260, None), True),
    ('Rooms', 'The Dam Stair', 'Divinity speaks. Morrow Dam: an earth embankment across the head of the valley, and a stair up the middle of it to the crest. The Frost Guard keep it. Behind the dam the reservoir is frozen solid.', (250, -10, None), True),
    ('Rooms', 'The Crest', 'Divinity speaks. The crest of the dam, and the Hold let into it: the Just\'s mountain depot, which fed the Front at Meridian. A woman stands on the crest with a letter in her hand. Everything in the valley is turned toward her.', (420, 40, None), True),
    ('Rooms', 'The Ice House', 'Divinity speaks. The Hold\'s old ice house, half let into the slope, from before there were engines to keep things cold. Three people stand Stilled at its door.', (-330, 256, None), True),
    # Story.
    ('Story', 'The Letter', 'Divinity speaks. It came over the wire from Meridian at five twenty in the morning, the last week of the fighting. Ines Okon wrote it out by hand. Pilgrim carried it up the Dam Stair. Warden Maren Holt read it on the crest, as the sun reached the top of the eastern ridge.', (196, 254, None), True),
    ('Story', 'The Lull', 'Divinity speaks. The Hold\'s cold engine, which kept the Front\'s stores frozen. Maren turned it on her own valley. It forces Divinity through every drop of water in Morrow, so that nothing goes on from that hour. It is the same forcing the Just did at Verdance and at Halcyon. This time it is done by one person, to time itself.', (300, 30, None), True),
    ('Story', 'The Rime', 'Divinity speaks. Where the Lull\'s forcing is strongest it stands up out of the frost: hoarfrost grown into walls of crystal, with the forced Divinity glowing magenta deep in its roots. It will not break. It is not that kind of thing.', (-140, 10, None), True),
    ('Story', 'The Stilled', 'Divinity speaks. The people of Morrow who were grieving that morning, caught by the Rime where they stood. They are alive. Their hearts beat about once a minute. They are not waiting for anything; that is the trouble.', (-250, -60, None), True),
    ('Story', 'A Hardened Place', 'Divinity speaks. The Hold is shut from inside, and what shuts it is a person. You cannot settle a grief. You cannot read it into the past or sing over it. The first door in this world that your power cannot open.', (410, 20, None), True),
    ('Story', 'The Frost Guard', 'Divinity speaks. Machines without will, in the Hold\'s service: the Hedge\'s own makes, painted white for the mountain. They were told to keep the dam. Nobody has told them anything since.', (-40, 20, None), True),
    # Items.
    ('Items', 'Sit With', 'Divinity speaks. You do not mend it. You do not settle it or argue with it. You kneel beside someone who cannot move, and you stay, until they can bear it, and then a little longer.', (-212, -46, None), True),
    ('Items', 'Frost Cache', 'Divinity speaks. A depot crate, packed against a hard winter. Walk into it to take what it holds. There are others in the valley.', (-470, -8, None), True),
    ('Items', 'Divinity Current', 'Divinity speaks. A current of Divinity between Earth and the Center. Step into its light and it will carry you across.', (-504, -6, None), True),
    ('Items', 'Pilgrim\'s Satchel', 'Divinity speaks. A courier\'s satchel, canvas and brass, empty. Pilgrim, at the Mill House, left it here. Walk into it to take it.', (258, 334, None), False),
    ('Items', 'The Lull\'s Heart', 'Divinity speaks. A Health Augmentation, left in the Hold where the Lull ran down: the core that held the cold, now holding nothing. Walk into it: one more Health Tank, and you are fully healed.', (420, -46, None), False),
    ('Items', 'The Icecutter\'s Blade', 'Divinity speaks. A Katana Augmentation: the long saw the Hold\'s crew cut lake ice with, before engines, kept in the ice house for luck. Walk into it, and every katana strike is stronger.', (-330, 290, None), False),
    # The Morning.
    ('Rooms', 'The Morning', 'Divinity speaks. Inside. The morning as Maren holds it: her kitchen, the letter on the table, the light just before the sun. Nothing here is real, and all of it is true.', (plan.KITCHEN[0] - 4.0, plan.KITCHEN[1] + 2.0, None), True),
)

# What each kind of lock is (Logbook entries without a marker of their own).
MORROW_GATES = (
    ('Items', 'Sealed Vault', 'Divinity speaks. A vault sealed with a lock you cannot open yet. Remember where it stands: what opens it is learned elsewhere.'),
)

# Enemies by level: mesh, health, scale, hover height (cm), Logbook entry, EnemyKind (0 plain, 1 turns light blows,
# 3 fast, 4 its face turns every blow). Levels 7-9 are Maren's grief in the Morning: living, in the game's sense (they
# scatter and gather again), with the animals' way of fighting (physis_morrow_scenario.ANIMALS).
MORROW_ENEMIES = {
    1: ('SM_GE_Wasp', 5, 1.0, 150, ('Enemies', 'Frost Wasp', 'Level 1. A small Just drone with a sting, out of the Hedge\'s works, its plates painted white for the mountain. Quick, and never alone. Five health.'), 3),
    2: ('SM_GE_Lancet', 9, 1.0, 170, ('Enemies', 'Frost Lancet', 'Level 2. It holds its distance over the frost and fires long volleys. Parry just before a bolt lands, or dodge. Nine health.'), 0),
    3: ('SM_GE_Burl', 16, 1.0, 190, ('Enemies', 'Frost Burl', 'Level 3. A shell of plates round a small engine. Light blows glance off it. Strike heavy, Settle it, or link it to something softer. Sixteen health.'), 1),
    4: ('SM_GE_Palisade', 20, 1.0, 200, ('Enemies', 'Frost Palisade', 'Level 4. A wall of staves that walks the Dam Road. Its face turns every blow: strike its back, or link it to another machine. Twenty health.'), 4),
    5: ('SM_GE_Thresher', 26, 1.0, 220, ('Enemies', 'Frost Thresher', 'Level 4. The Frost Guard\'s guard, set over the Stilled and the Dam Stair. Parry its volleys and strike while it recovers. Twenty-six health.'), 0),
    6: ('SM_GE_Harrow', 60, 1.0, 380, ('Enemies', 'Frost Harrow', 'Level 5, end-game. It was built to clear avalanche debris, and it has decided the ice house is debris. You do not have to fight it. Sixty health.'), 0),
    7: ('SM_OE_Shade', 6, 1.0, 150, ('Enemies', 'Rime-shape', 'Level 2. Grief, given the shape of frost. It has no face. It comes in close and lashes, then draws back. Strike it and it scatters into hoarfrost, to gather again when it is quiet. Six health.'), 3),
    8: ('SM_OE_Mourner', 18, 1.0, 260, ('Enemies', 'Mourner', 'Level 3. A tall veiled shape of Rime, its arms folded over something it will not show. When it lifts its head it is about to strike: step out of its reach. It scatters, and gathers again. Eighteen health.'), 0),
    9: ('SM_OE_Unrisen', 150, 1.0, 520, ('Enemies', 'The Unrisen', 'Boss. Maren\'s grief, holding the morning down in its arms so the sun cannot come up. It will not be beaten, only tired: fight it until it stops, then sit with it. One hundred and fifty health.'), 0),
}

# ---------------------------------------------------------------- quests

QUEST_ARRIVE = 'Follow the Orchard Road down to the Mill House'
QUEST_BENCH = 'Go down to the bench by the millpond with Edda'
QUEST_MILLER = 'Sit with the miller at his wheel, across the pond'
QUEST_BRIDGE = 'Sit with the bridge keeper at the Gorge, and cross the Ferry Bridge'
QUEST_THREE = 'Find the three who loved Tam best, Stilled in the town: at the Schoolhouse, on the Glider Field and at the Telegraph House'
QUEST_CREST = 'You carry all three memories. Climb the Dam Stair to the crest, and sit with Maren'
QUEST_MORNING = 'Go through the Morning to the crest as she remembers it'
QUEST_UNRISEN = 'The Unrisen waits on the crest. Fight it until it stops'
QUEST_SIT = 'Sit with the Unrisen'
QUEST_MAREN = 'Speak to Maren on the crest'
QUEST_EDDA = 'Return to Edda at the Mill House'
QUEST_DONE = 'Walk the valley in the morning, or return to the Center from the Pass Chapel'
# Set once by the Center's sanctum current to Morrow when it opens (the Cantor fallen, Morrow not yet visited).
QUEST_CURRENT = 'A new Divinity current has opened in the sanctum. Step into it to follow it back to Earth'

# ---------------------------------------------------------------- people

M = (plan.MILL[0] + 10.0, plan.MILL[1] + 2.0)      # before the Mill House's door
MAREN_SPOT = (plan.CREST[0] - 3.0, plan.CREST[1] + 8.0)
CORIN_SPOT = (plan.MILL[0] + 14.0, plan.MILL[1] + 14.0)
PILGRIM_SPOT = (plan.MILL[0] + 8.0, plan.MILL[1] - 14.0)

PEOPLE = (
    # Edda Holt, Maren's mother, Tam's grandmother.
    ('EddaH', 'Edda Holt', 'Edda', 'bf_lily', 'human', M, 190, '', ',sitwith,',
     ('You came over the pass. Nobody comes over the pass now. Sit down by the door, if you like. The fire is the only warm thing for a mile.',
      'I am Edda Holt. My daughter Maren is the Warden up at the Hold. Her boy, my grandson Tam, flew at Meridian. He was killed there in the last week of it.',
      'The news came at dawn. Maren read it on the crest, and the morning stopped. It has been the same morning for forty days. You will have noticed the sun.',
      'People ask me to go up there and make her stop. I could never make her eat her supper. Come down to my bench by the pond. There is something I want to show you, and it is not a thing you do with your hands.'),
     (('Can\'t you stop it?', ('No. And I do not think you can either, whatever you are. The Hold is shut from inside, and what shuts it is her.',)),
      ('Who are the frozen people?', ('The ones who were grieving that morning. The Rime took them where they stood. They are not dead. They are only very, very still. I know how they feel.',)),
      ('Why not you?', ('I lost my husband twenty years ago, on a morning very like this one. I did my standing still then. I think you only get the one.',))),
     ',edda,', QUEST_BENCH, {}),
    ('EddaWait', 'Edda Holt', 'Edda', 'bf_lily', 'human', M, 190, ',sitwith,', ',unrisen,',
     ('The three who loved him best are out in the town, Stilled. Ada Lowe at the school, who taught him. Jory on the glider field. Ines at the telegraph, who took the message down.',
      'Maren will not let anyone in who does not carry him. Go and sit with them. Take your time. There is nothing but time here.'),
     (('How did it feel?', ('Sitting with you? Like sitting with anyone. You are very still, for someone so bright.',)),
      ('Is it enough?', ('It is never enough. It is what there is.',))),
     '', '', {}),
    ('EddaDone', 'Edda Holt', 'Edda', 'bf_lily', 'human', M, 190, ',unrisen,', '',
     ('I saw the sun come over from the bench. I did not get up. I thought, if I get up I will run, and I am seventy-four.',
      'She is coming down. I can see her on the stair, holding the rail the way she did when she was small.',
      'You did the hard part. You did not do anything. Most people cannot manage that.',
      'Here. Tam\'s grandfather carried this. It kept his hand steady when nothing else was. It might do the same for you.'),
     (('Will she be all right?', ('No. And yes. Both, for a long time. That is what all right looks like, close up.',)),
      ('What will you do?', ('Make her eat something. Some things you can do with your hands.',))),
     ',aug_agility9,', QUEST_DONE, {'divinity': 60, 'heal': True, 'note': 'Agility Augmentation: the moment in which a block becomes a perfect parry is longer. 60 Divinity, and you are fully healed.'}),
    # Corin Vell, the dam's engineer.
    ('CorinH', 'Corin Vell', 'Corin', 'am_eric', 'human', CORIN_SPOT, 250, '', ',mw_crew,',
     ('Corin Vell. I keep the dam, or I did. I walked out of the Hold the first night, when the Lull came on. My crew did not.',
      'They are in the old ice house, the three of them, Stilled at the door. I tried to wake them. I shouted. I am an engineer; I thought it was a matter of volume.',
      'If what Edda says about you is true, would you go and sit with them? Up the lane past the orchards, south-east.'),
     (('What is the Lull?', ('The Hold\'s cold engine. It kept the Front\'s stores frozen. Maren turned it on the whole valley. It should not be able to do that. Nothing should be able to do that.',)),),
     ',corin,', '', {}),
    ('CorinThanks', 'Corin Vell', 'Corin', 'am_eric', 'human', CORIN_SPOT, 250, ',mw_crew,', '',
     ('They walked in the door and asked what was for breakfast. Forty days, and breakfast.',
      'Here: the sighting glass off my bench in the Hold. True to a hair. It will make your shots tell.'),
     (), ',aug_pistol8,', '', {'note': 'Pistol Augmentation: every shot strikes harder, the Divinity Shot too.'}),
    # Pilgrim, the Hold's courier, a Mechanoid of the Just.
    ('Pilgrim', 'Pilgrim', 'SM_CP_Robot', 'am_adam', 'robot', PILGRIM_SPOT, 120, '', ',satchel,',
     ('Pilgrim. Courier, the Hold. I carried the letter up the Dam Stair at five forty-one on the morning in question.',
      'Since then I have walked the route four hundred and twelve times, carrying nothing. I find I cannot stop. I left my satchel at the Telegraph House. I believe I left it there so that I would have a reason to go back.',
      'If you are going up to the rock, would you bring it to me? Then I think I can stop.'),
     (('Why can\'t you stop?', ('I delivered it. Delivering is the whole of my function, and it was the worst thing I have ever done. I have been trying to un-deliver it. That is not a thing.',)),),
     ',pilgrim,', '', {}),
    ('PilgrimThanks', 'Pilgrim', 'SM_CP_Robot', 'am_adam', 'robot', PILGRIM_SPOT, 120, ',satchel,', '',
     ('Thank you. It is empty. I knew it would be empty.',
      'Take this: a plate from my chassis, from the winter I fell down the Dam Stair in an ice storm. It turned the worst of that. It will turn some for you.'),
     (), ',aug_defense9,', '', {'note': 'Defense Augmentation: every hit you take costs you less.'}),
    # Warden Maren Holt, in person, once the Unrisen has been sat with.
    ('Maren', 'Warden Holt', 'Maren', 'af_aoede', 'human', MAREN_SPOT, 160, ',unrisen,', '',
     ('The sun is on the water. I had forgotten it does that. Forty days, and I had forgotten the colour.',
      'I left the light on, you know. In the kitchen. I have left it on every night since. I did not know why until just now.',
      'I cannot thank you. Not yet. Mother says that comes later, the thanks, along with everything else.',
      'The Hold is open. I opened it. Take what the Lull left inside. Then go down and tell Mother I am coming. I would like her to hear it from someone else first, in case I cannot say it.'),
     (('What will you do?', ('Go down the stair. Sit by the fire. Let her make me eat something. After that I do not know, and Mother says that is allowed.',)),
      ('Tam.', ('Not yet. Tomorrow, maybe. It will be tomorrow now. That is the strange part.',))),
     ',maren,', QUEST_EDDA, {'note': 'Warden Holt opens the Hold to you.'}),
)

# ---------------------------------------------------------------- the Stilled

# (key, name, mesh, (x, y), yaw, voice, kind, narration, speech, after, token, need, denied)
#   narration: what Physis sees as they wake; speech: what they say (voiced); after: a line of what it means (or '')
#   need: a token they wait for before they can be reached (or ''), and what sitting with them says until then
STILLED = (
    ('Miller', 'Bram Lisle, the miller', 'SM_OP_Stilled0', plan.MILLER, 120, 'bm_lewis', 'human',
     'Physis kneels beside the miller and stays. After a long while the frost lets go of his hands.',
     'My wheel. I was going to break the ice off it before I went up to Maren. Then I thought: what for. What is any of it for. ... Still. It is cold to be standing about. I should see to Edda\'s fire.',
     'Sit With: what the Rime holds, it lets go when its person can move again.', ',mw_miller,', '', ''),
    ('Keeper', 'Hal Wren, the bridge keeper', 'SM_OP_Stilled1', plan.KEEPER, 30, 'bm_daniel', 'human',
     'Physis kneels beside the bridge keeper and stays. The bell rope is still in his hand.',
     'I ring for the first crossing every morning. That morning I thought: whoever crosses now is crossing into a world without that boy in it. So I did not ring. I just stood. ... Go on, then. It is your crossing.',
     'The Rime on the Ferry Bridge lets go.', ',mw_bridge,', '', ''),
    ('Ada', 'Ada Lowe, the teacher', 'SM_OP_Stilled2', (plan.SCHOOL[0] + 7.6, plan.SCHOOL[1] + .4), 180, 'af_jessica', 'human',
     'Physis kneels by the school door beside Ada Lowe, and stays. The chalk is still in her fingers.',
     'He was eight when he came to me, and he could not sit still for a single lesson. He spent a whole winter drawing aeroplanes in the margins of his sums. I kept them. I kept every page. I never told her.',
     'The first memory: Tam at eight, drawing aeroplanes in the margins of his sums.', ',mw_mem1,', '', ''),
    ('Jory', 'Jory Pike, his friend', 'SM_OP_Stilled3', (plan.FIELD[0] + 18.0, plan.FIELD[1] + 6.0), 200, 'am_liam', 'human',
     'Physis kneels beside Jory by the glider they built, and stays.',
     'Before his first flight alone he was sick behind the hangar. Then he came round the corner grinning like an idiot and said: Jory, if I don\'t come down, tell Mum the view was worth it. And he came down. He always came down.',
     'The second memory: Tam at sixteen, grinning behind the hangar before his first flight alone.', ',mw_mem2,', '', ''),
    ('Ines', 'Ines Okon, the operator', 'SM_OP_Stilled4', (plan.TELEGRAPH[0] + 4.4, plan.TELEGRAPH[1] + .9), 180, 'af_river', 'human',
     'Physis kneels beside Ines Okon at her key, and stays. Her hand is still on it.',
     'I took the message down. Then I sat here and could not get up to carry it. The last thing he ever sent, before the one about him, was to her. Leave the kitchen light on. I\'ll find my way. She never answered it. She thought there would be time.',
     'The third memory: the last thing he sent her. Leave the kitchen light on.', ',mw_mem3,', '', ''),
    ('Crew1', 'Dana Ruiz, of Corin\'s crew', 'SM_OP_Stilled5', (plan.ICEHOUSE[0] + 8.0, plan.ICEHOUSE[1] - 3.0), 160, 'af_alloy', 'human',
     'Physis kneels beside the first of Corin\'s crew, and stays.',
     'We were in the cold store when the Lull came on. I thought: good. Let it stay cold. Let nothing in here spoil. I did not think it meant us.',
     '', ',mw_crew1,', '', ''),
    ('Crew2', 'Teo Marsh, of Corin\'s crew', 'SM_OP_Stilled6', (plan.ICEHOUSE[0] + 8.5, plan.ICEHOUSE[1] + 1.0), 200, 'am_puck', 'human',
     'Physis kneels beside the second of Corin\'s crew, and stays.',
     'I had a letter for my sister in my pocket. I never sent it. That is the first thing I am doing. Before breakfast.',
     '', ',mw_crew2,', '', ''),
    ('Crew3', 'Ruth Abe, of Corin\'s crew', 'SM_OP_Stilled5', (plan.ICEHOUSE[0] + 7.0, plan.ICEHOUSE[1] + 4.5), 230, 'af_nicole', 'human',
     'Physis kneels beside the last of Corin\'s crew, and stays.',
     'Corin went for help. Corin always goes for help. Tell him we are all right. Tell him not to shout.',
     '', ',mw_crew3,', '', ''),
    ('MarenStilled', 'Warden Maren Holt', 'SM_OP_Stilled7', plan.MAREN, 90, 'af_aoede', 'human',
     'Physis kneels beside Maren and stays, and this time she does not stay outside. She carries the three of them in with her: the boy drawing aeroplanes, the boy grinning behind the hangar, the light left on. The Rime opens like a door.',
     '',
     '', ',mw_inner,', ',mw_mems,',
     'Maren Holt stands on the crest with the letter in her hand, rimed white. Physis kneels beside her and stays, and nothing changes. She has shut out everything that is not this morning. Even him. Find the three who loved him best, and bring him with you.'),
)

# The Morning's memories: (key, mesh, (x, y, z cm above the room's floor), yaw, scale, narration, token).
MEMORIES = (
    ('Chair', 'SM_ON_Chair', (plan.KITCHEN[0] + 1.6, plan.KITCHEN[1] - .3, 0.0), 160, 1.0,
     'His chair, pushed back from the table the way he always left it, as if he had only gone to fetch something. Physis sits with it, and the Rime in the door to the hall loosens.',
     ',mw_room1,'),
    ('Door', None, (plan.HALL[0] + .6, plan.HALL[1] + 1.4, 0.0), 0, 1.0,
     'The door to his room, its frame marked in pencil at every height he ever was. The last mark is above the top of the door: he stood on a chair to make it, to show he could. Physis sits with it, and the end of the hall opens.',
     ',mw_room2,'),
    ('Glider', 'SM_ON_Glider', (plan.FIELD_IN[0] + 6.0, plan.FIELD_IN[1] - 8.0, 0.0), 30, 1.0,
     'The glider in the mist, one wingtip resting on the frost the way it came down after his first solo. Physis sits with it, and out over the mist a way opens to the crest.',
     ',mw_room3,'),
)

# The spoken final stage: (speaker, line). 'Maren' lines are voiced ("Talk MarenStage <k>"); '' lines are narration.
STAGE = (
    ('Maren', 'Do not. Do not come any closer. If you come any closer it will be morning.'),
    ('', 'Physis does not come closer. She kneels where she is, and stays.'),
    ('Maren', 'They want me to put it down. Everyone wants me to put it down. Mother. Corin. The whole valley, standing out there in the cold.'),
    ('Maren', 'If I put it down, the sun comes up. And then it is the first day he is not in. And then the second. And one day it is a year, and I have got used to it. I will not get used to it.'),
    ('', 'There is nothing true to say that would help. Physis says nothing, and stays.'),
    ('Maren', 'He used to draw aeroplanes on his sums. Did you know that? Ada kept them. I did not know she kept them.'),
    ('Maren', 'He was sick behind the hangar before his first flight. Jory told me years after. I was so angry with him for not telling me. I was not angry. I was so proud I could not speak.'),
    ('Maren', 'Leave the kitchen light on. That was the last thing. I never answered it. I thought there would be time to answer it.'),
    ('', 'The light in its arms is shaking. Physis stays.'),
    ('Maren', 'You are still here.'),
    ('Maren', 'I do not want it to be morning. I do not want it to be morning, and it is going to be anyway, is it not. With me or without me.'),
    ('Maren', 'All right. All right. Stay with me while it comes up. Do not go.'),
    ('', 'The Unrisen opens its arms, and the light goes up out of them the way the sun comes over a ridge: not at all, and then all at once.'),
)
STAGE_STEP = 6.5      # seconds of sitting per line

MORROW_TUTORIALS = (
    ('Divinity current: step into the light to travel between Earth and the Center.', (plan.CHAPEL[0] + 8.0, plan.CHAPEL[1] + 6.0), (.35, 2.0, 1)),
    ('Sit With: H / hold |DPadLeft|     Kneel beside someone who cannot move, and stay. Moving, attacking or being struck ends it.',
     (plan.MILLER[0] + 6.0, plan.MILLER[1] + 6.0), (.6, 3.0, 1)),
    ('The Stilled wake when you have sat with them long enough. What their Rime held lets go.', (plan.KEEPER[0] - 8.0, plan.KEEPER[1]), (.6, 3.0, 1)),
    ('Nothing in the Morning can be broken. What blocks the way is a memory: sit with it.', (plan.KITCHEN[0] - 3.0, plan.KITCHEN[1]), (.5, 2.5, 1)),
)

ARRIVAL_LINE = ('Arrival at Morrow', 'Divinity speaks. Earth again: Morrow, in the northern mountains. It is the hour before sunrise, and it has been for forty days. Smoke is rising from one chimney, by the pond in the valley. Go down.')
MORNING_LINE = ('Arrival in the Morning', 'Divinity speaks. Inside. The morning as Maren holds it: her kitchen, the letter on the table, the light just before the sun. Nothing here is real, and all of it is true.')

BENCH_DONE = ('Edda sits down on the bench and pats the boards beside her, and Physis sits. Neither of them says anything for a long time. Across the frozen pond the miller stands at his wheel, rimed white.~'
              '"That is all it is," Edda says at last. "You stay. You do not fix it. You do not tell them it will be all right. You stay until they can bear it, and then a little longer."~'
              'Sit With learned: H / hold |DPadLeft|.  Kneel beside someone who cannot move, and stay. Moving, attacking or being struck ends it.~'
              'The miller has stood at his wheel since the morning. Go and sit with him.')

MESSAGES = {
    'arrive': 'Morrow.~The current has carried Physis back to Earth.',
    'bench_denied': 'Edda\'s bench, by the frozen pond. Edda, at the Mill House, wants to show you something here.',
    'sit_alone': 'Physis kneels and stays. There is no one here to stay with.',
    'memories': 'The three memories: the boy drawing aeroplanes, the boy grinning behind the hangar, the light left on.~Maren is on the crest of the dam.',
    'still': 'The Unrisen stops. It sinks to its knees, holding the light against itself. It is not beaten. It is only tired.~Sit with it.',
    'sunrise': 'The sun comes over the eastern ridge.~All down the valley the Rime lets go, and the Stilled lift their heads.',
    'heart': 'The Lull\'s Heart. Health Augmentation: one more Health Tank, and you are fully healed.',
    'blade': 'The Icecutter\'s Blade. Katana Augmentation: every katana strike is stronger.',
    'crew': 'All three of Corin\'s crew are awake. The ice house door stands open.',
    'satchel': 'Pilgrim\'s satchel. Pilgrim, at the Mill House, will want it.',
    'cache': 'A frost cache. Divinity +40.',
    'hold_shut': 'The Hold\'s doors, shut from inside. Settle finds nothing to settle: what keeps them shut is not a machine. It is a person.',
    'fell': 'Physis comes back to the Morning\'s kitchen.',
}


def person_key(key, page):
    return 'Talk %s %d' % (key, page)


def conversation_pages(person):
    greeting, topics = person[9], person[10]
    pages = list(greeting)
    for _, answer in topics:
        pages.extend(answer)
    return pages


def stilled_text(row):
    """What shows when one of the Stilled wakes: narration, their words, what it means (pages joined by ~)."""
    key, name, mesh, spot, yaw, voice, kind, narration, speech, after = row[:10]
    pages = [narration]
    if speech:
        pages.append('%s: "%s"' % (name.split(',')[0], speech))
    if after:
        pages.append(after)
    return '~'.join(pages)


def voiced_lines():
    """(title, text, voice, kind) of every line voiced in a person's own voice besides conversations: the Stilled's
    words as they wake, and Maren's lines in the final stage."""
    rows = [(person_key(row[0], 0), row[8], row[5], row[6]) for row in STILLED if row[8]]
    rows += [(person_key('MarenStage', k), line, 'af_aoede', 'human') for k, (who, line) in enumerate(STAGE) if who == 'Maren']
    return rows


def morrow_entries():
    """Logbook rows (category, title, text) for every scan, lock kind and enemy."""
    return [row[:3] for row in MORROW_SCANS] + list(MORROW_GATES) + [entry[4] for entry in MORROW_ENEMIES.values()]
