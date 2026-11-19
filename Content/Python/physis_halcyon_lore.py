"""Text for level 6, Halcyon, the Drowned Harbour, on Earth. Divinity's scans, the people's conversations, enemies,
tutorials and quest messages. Voices come from Tools/build_physis_voice.py --halcyon. Places are plan metres
(physis_halcyon_plan: x north, y east); a z of None puts a scan marker 1.5 m above the ground, a number is centimetres.

Conversations (PEOPLE) work as in the Conclave, the Grove and Arche: a person appears while their Show token is held
(or always, '') and until their Hide token is held; a greeting, then topics, then Leave. When the greeting ends the
first time the person gives Give, sets the quest to Quest and grants any reward.

Echoes (ECHOES) are people the town remembers. They stand only in the past: Trace Reading shows them, and the first
time one is read it says its line (BP_Trace Done) and gives its token.

All of this is new writing for the author to review (GAME_ROADMAP.md "Level 6").
In-game text names actions, not keys; only the tutorial strips and the "learned" line show inputs.
"""
import physis_halcyon_plan as plan

# ---------------------------------------------------------------- Divinity's scans

# Category, title, text, (x, y, z or None), important.
HALCYON_SCANS = (
    # Places.
    ('Rooms', 'The Cliff Garden', 'Divinity speaks. Port Halcyon, on Earth. The town\'s garden on the cliff, where people came to watch the boats come in. The current that carried you here returns to the Center from this pool. This is a Still Point.', (-494, 30, None), True),
    ('Rooms', 'The High Street', 'Divinity speaks. The upper town, above the reach of the water. Some of these houses fell forty years ago and some eleven. You can tell which by what grows in them.', (-430, 50, None), True),
    ('Rooms', 'The Signal House', 'Divinity speaks. The harbour pilots\' house, where the signals were raised for the boats. The Wise have made it their camp. Kairos is here, and he has been waiting for you without knowing it.', (-296, 8, None), True),
    ('Rooms', 'The Clocktower', 'Divinity speaks. Its clock stopped at fourteen minutes past seven, the moment the sea came in. Nobody has wound it since. Nobody here could bear to.', (-222, 40, None), True),
    ('Rooms', 'The Breach', 'Divinity speaks. Where the sea wall broke and the water came through the town in one wave. It cut the town in two and the Harbour Bridge went with it. Nothing you can do now will cross it.', (-160, 40, None), True),
    ('Rooms', 'The Market Steps', 'Divinity speaks. The fish market, where the town\'s ways part: west to the Drowned Quarter, east to the Cannery Yards and the Point, north along the Mole to the Bastion.', (-70, 20, None), True),
    ('Rooms', 'The Drowned Quarter', 'Divinity speaks. The old harbour streets, below the sea since the morning of the strike. The harbourmaster\'s office still stands in the water. Its outside stair does not.', (-20, -160, None), True),
    ('Rooms', 'The Cannery Yards', 'Divinity speaks. Sheds and cranes where the boats were unloaded. The Tide Guard keeps them now, though there is nothing in them to keep.', (-4, 180, None), True),
    ('Rooms', 'Lighthouse Point', 'Divinity speaks. The headland and its lighthouse. The light has not been lit since the strike. The keeper\'s stair climbed the outside of the tower; it is gone.', (176, 250, None), True),
    ('Rooms', 'The Mole', 'Divinity speaks. The breakwater out to the harbour mouth, and at its end the Sea Gate, in the Held Sea. Something on the other side is pushing the water away with all its strength.', (150, 10, None), True),
    ('Rooms', 'Bastion Halcyon', 'Divinity speaks. The Just\'s coastal command, raised on the rock where the town\'s old light stood. It was built in a year, out of grief and concrete. It is still giving orders.', (380, 12, None), True),
    ('Rooms', 'The Drowned Library', 'Divinity speaks. The town library, on the hill. The water never reached it; the fire after the strike did. Its reading room is sealed. Its shelves stand only in the past.', (-330, 260, None), True),
    # Story.
    ('Story', 'The Morning of the Strike', 'Read by Kairos. Fourteen minutes past seven, in the war\'s first year. A First One lance struck the sea wall from orbit. Nobody on Earth had seen one before. The wave was nine metres high when it reached the High Street. Two thousand and six people. The record does not round it.', (-216, 46, None), True),
    ('Story', 'The Halcyon Litany', 'Divinity speaks. The oath the Just swore at the Bastion, the day it was finished. It has three lines, and the Sea Gate opens only to all three: Hold the line. Remember the drowned. Let no wave come again.', (126, 10, None), True),
    ('Story', 'The Held Sea', 'Divinity speaks. The Undertow forces Divinity through the water so that it stands back from the Bastion in walls. It is the same thing the Just did to the grove at Verdance. The sea here has been holding its breath for ten years.', (300, 40, None), True),
    ('Story', 'The Tide Guard', 'Divinity speaks. Machines without will, in the Just\'s coastal service: the Hedge\'s own makes, painted for the sea. They were told to keep the harbour closed. Nobody told them the war had paused.', (-40, 40, None), True),
    ('Story', 'What the Wise Read', 'Recorded by Petra Lune. Kairos says the past is not gone, it is only very quiet. We have read eleven years of it out of the stones of this town, a day at a time. You read the whole morning at once. I am trying not to mind.', (-284, -10, None), True),
    # Items.
    ('Items', 'Traces', 'Divinity speaks. What stood here once is still written in the Divinity of the place. Read the past and it shows in silver, and while you read, it will bear your weight. It does not last: the present comes back.', (-160, 22, None), True),
    ('Items', 'Echoes', 'Divinity speaks. People the town remembers. Read the past where one stood and they stand there again, for as long as you read, and say what they said.', (-220, 22, None), True),
    ('Items', 'Tide Cache', 'Divinity speaks. A pilots\' sea chest, packed against a bad night. Walk into it to take what it holds. There are others in the town.', (-470, 12, None), True),
    ('Items', 'Divinity Current', 'Divinity speaks. A current of Divinity between Earth and the Center. Step into its light and it will carry you across.', (-504, 14, None), True),
    ('Items', 'The Sea Gate', 'Divinity speaks. The Bastion\'s gate in the Held Sea. It opens to the Halcyon Litany, all three lines, spoken by those who first swore it. Three of them are still in the town, in the past.', (352, 10, None), True),
    ('Items', 'Undertow Pump', 'Divinity speaks. One of the pumps that drive the Undertow. The Keel\'s shield answers to them while they run. The sidearm will stop one.', (440, 40, 300), True),
    ('Items', 'Ledger\'s Logbook', 'Divinity speaks. A Robot\'s field logbook, canvas-bound, eleven years of readings in a very small hand. Ledger, at the Signal House, left it on Lighthouse Point. Walk into it to take it.', (260, 300, None), False),
    ('Items', 'The Undertow\'s Heart', 'Divinity speaks. A Health Augmentation, left where the Keel fell: the part of the engine that held the sea apart, now holding nothing. Walk into it: one more Health Tank, and you are fully healed.', (450, 0, None), False),
    ('Items', 'The Reader\'s Knife', 'Divinity speaks. A Katana Augmentation: the knife the librarians cut the pages of new books with, kept in the reading room. Walk into it, and every katana strike is stronger.', (-330, 290, None), False),
)

# What each kind of lock is (Logbook entries without a marker of their own).
HALCYON_GATES = (
    ('Items', 'Sealed Vault', 'Divinity speaks. A vault sealed with a lock you cannot open yet. Remember where it stands: what opens it is learned elsewhere.'),
)

# Enemies by level: mesh (the Grove's Hedge: the same machines, in coastal service), health, scale, hover height (cm),
# Logbook entry, EnemyKind (0 plain, 1 turns light blows, 3 fast, 4 its face turns every blow).
HALCYON_ENEMIES = {
    1: ('SM_GE_Wasp', 5, 1.0, 150, ('Enemies', 'Tide Wasp', 'Level 1. A small Just drone with a sting, out of the Hedge\'s works, salt-white on its plates. Quick, and never alone. Five health.'), 3),
    2: ('SM_GE_Lancet', 9, 1.0, 170, ('Enemies', 'Tide Lancet', 'Level 2. It holds its distance over the water and fires long volleys. Parry just before a bolt lands, or dodge. Nine health.'), 0),
    3: ('SM_GE_Burl', 16, 1.0, 190, ('Enemies', 'Tide Burl', 'Level 3. A shell of plates round a small engine. Light blows glance off it. Strike heavy, Settle it, or link it to something softer. Sixteen health.'), 1),
    4: ('SM_GE_Palisade', 20, 1.0, 200, ('Enemies', 'Tide Palisade', 'Level 4. A wall of staves that walks the quays. Its face turns every blow: strike its back, or link it to another machine. Twenty health.'), 4),
    5: ('SM_GE_Thresher', 26, 1.0, 220, ('Enemies', 'Tide Thresher', 'Level 4. The Tide Guard\'s guard, set over the places the Litany is remembered and over the Mole. Parry its volleys and strike while it recovers. Twenty-six health.'), 0),
    6: ('SM_GE_Harrow', 60, 1.0, 380, ('Enemies', 'Tide Harrow', 'Level 5, end-game. It clears rubble, and it has decided the library is rubble. You do not have to fight it. Sixty health.'), 0),
    7: ('SM_HE_Keel', 130, 1.0, 600, ('Enemies', 'The Keel', 'Boss. The Bastion\'s command frame, grown into the Undertow. Its shield answers to the four pumps round its chamber: stop them with the sidearm, then fight it. Its face turns every blow; get behind it, or link it to its own Wasps. One hundred and thirty health.'), 4),
}

# ---------------------------------------------------------------- people

QUEST_ARRIVE = 'Follow the High Street north to the Signal House'
QUEST_CLOCK = 'Go to the Clocktower, north of the Signal House, with Kairos'
QUEST_BREACH = 'Read the past at the Breach and cross the Harbour Bridge'
QUEST_ECHOES = 'Find the three who swore the Litany: in the Drowned Quarter, the Cannery Yards and on Lighthouse Point'
QUEST_GATE = 'All three lines of the Litany are found. Go out along the Mole to the Sea Gate'
QUEST_KEEL = 'Stop the Keel, in the Bastion'
QUEST_MARR = 'Speak to Commodore Marr, in the Bastion'
QUEST_KAIROS = 'Return to Kairos at the Signal House'
QUEST_DONE = 'Walk the town, or return to the Center from the Cliff Garden'
# Set once by the Center's temple current to Halcyon when it opens (the Sunderer fallen, Halcyon not yet visited).
QUEST_CURRENT = 'A new Divinity current has opened in the sanctum. Step into it to follow it back to Earth'

S = plan.SIGNAL
MARR_SPOT = (plan.COURT[0] - 14.0, plan.COURT[1] + 18.0)
SPEAKER = (plan.SEA_GATE[0] - 14.0, plan.SEA_GATE[1] - 8.0)   # the speaker post before the Sea Gate

# key, speaker, mesh, voice, kind, (x, y), yaw, show, hide, greeting pages, topics, give, quest, reward
# mesh: a static figure, or for kind 'human' the built MetaHuman Blueprint's name (physis_halcyon_scenario.LOOKS).
PEOPLE = (
    # Kairos, keeper of the Wise's Archive, out in the field.
    ('KairosH', 'Kairos', 'Kairos', 'bm_george', 'human', (S[0] + 8.0, S[1] - 4.0), 200, '', ',trace,',
     ('You. I wondered when the current would bring you to Earth again. I hoped it would be here.',
      'Kairos, of the Archive, a long way from it. The Wise have been camped in this house for eleven months, reading what happened to this town out of its stones. A day at a time, with instruments. It is slow work. It is the only work I have ever wanted.',
      'The Just\'s Bastion is out in the harbour mouth, behind a sea that stands up on its hind legs. Its commander has been sealed in it since Meridian. Her machines will not let anyone near, us included.',
      'But I think you can do in a moment what takes us a month. Come to the Clocktower, north of here. I will show you what a room remembers.'),
     (('What happened here?', ('In the war\'s first year a First One lance broke the sea wall. Two thousand and six people. The Just built their Bastion where the old light stood and swore never to be taken by surprise again.',
                              'That oath is still running the harbour. Oaths are like that. They outlive the people who needed them.')),
      ('Why does the record matter?', ('Because one day both peoples will sit at one table, and someone will say what happened here. I would like that someone to be right.',)),
      ('You came all this way.', ('Historians go where the past is loudest. This town has not stopped shouting for ten years.',))),
     ',kairos_h,', QUEST_CLOCK, {}),
    ('KairosRead', 'Kairos', 'Kairos', 'bm_george', 'human', (S[0] + 8.0, S[1] - 4.0), 200, ',trace,', ',keel,',
     ('Petra says she saw the bridge from the window. For ten seconds there was a bridge. She is pretending to be calm about it and failing.',
      'The Sea Gate opens to the Litany, the Just\'s oath, three lines of it. We found where it was first spoken: three people of this town swore it at the Bastion\'s founding, and the town remembers each of them where they were that morning.',
      'The harbourmaster, in her office in the Drowned Quarter. The cannery foreman, in his crane. The lighthouse keeper, at the lamp. Read them, and you will have the lines.'),
     (('How does reading work?', ('You do not look harder. You look longer. Everything that has happened in a place is still in its Divinity. You let the present be quiet, and the past stands up.',
                                 'It does not last. And it only bears your weight while you are reading it: do not stop halfway across.')),
      ('Will the gate know it is me?', ('It will know the words. The Just built a lock that only remembers, never checks. It is very like them.',))),
     '', QUEST_BREACH, {}),
    ('KairosDone', 'Kairos', 'Kairos', 'bm_george', 'human', (S[0] + 8.0, S[1] - 4.0), 200, ',keel,', '',
     ('The sea lay down. I watched it from the window with a pencil in my hand and wrote nothing at all.',
      'We have the whole morning now, from the first light to fourteen minutes past seven, and the ten years after. Who fired, who warned, who ran toward the water. It is not a simple record. Good records never are.',
      'When the Just and the First Ones finally sit down together, this will be on the table. Not as an accusation. As a fact that both of them will have to carry.',
      'Take this. The Wise teach it to every reader: how to hold still at the exact moment. You will find more room in the instant a blow lands.'),
     (('What will the Just say?', ('That the First Ones did this, which is true. The First Ones will say the Just did worse at Verdance, which is also true. The work is in what comes after both true things.',)),
      ('What will you do now?', ('Write it down. Then go home and argue with Petra about the commas.',))),
     ',aug_agility7,', QUEST_DONE, {'divinity': 60, 'heal': True, 'note': 'Agility Augmentation: the moment in which a block becomes a perfect parry is longer. 60 Divinity, and you are fully healed.'}),
    # Petra Lune, the Conclave's archivist.
    ('PetraH', 'Petra Lune', 'Petra', 'bf_isabella', 'human', (S[0] - 10.0, S[1] + 14.0), 160, '', ',shelves,',
     ('Oh. It is you. Kairos said you would come, and I said nobody comes here on purpose.',
      'The library on the hill burned the night after the wave. Its reading room is sealed and the shelves in front of it are ash. But a shelf remembers being a shelf, does it not? Kairos says that is what you do.',
      'Three shelves stand before the reading-room door, in the past. If you read them, the room\'s lock will remember they were never burned, and open.'),
     (('What is in the reading room?', ('The town\'s own records. Births, boats, who owed who for a net. The things the war never bothered to remember.',)),),
     ',petra_h,', '', {}),
    ('PetraHThanks', 'Petra Lune', 'Petra', 'bf_isabella', 'human', (S[0] - 10.0, S[1] + 14.0), 160, ',shelves,', '',
     ('The whole room. Every ledger. I am going to need a bigger satchel and possibly a smaller life.',
      'Here: a sight-glass from my desk at the Archive. It finds the one true line through anything. I think it will make your shots land harder.'),
     (), ',aug_pistol6,', '', {'note': 'Pistol Augmentation: every shot strikes harder, the Divinity Shot too.'}),
    # Ledger, the Wise's Robot scribe.
    ('Ledger', 'Ledger', 'SM_CP_Robot', 'am_onyx', 'robot', (S[0] + 16.0, S[1] + 18.0), 230, '', ',logbook,',
     ('Ledger. I write down what the instruments say, so that Kairos can disagree with it.',
      'I left my field logbook on Lighthouse Point, by the lamp, when the Tide Guard came round the headland. Eleven years of readings. I have a copy. The copy is not the point.',
      'If you are going to the light, I would be grateful.'),
     (('What did you measure?', ('How loud the past is, by the hour. It is loudest at fourteen minutes past seven. Every morning. I have stopped finding that strange and started finding it sad.',)),),
     ',ledger,', '', {}),
    ('LedgerThanks', 'Ledger', 'SM_CP_Robot', 'am_onyx', 'robot', (S[0] + 16.0, S[1] + 18.0), 230, ',logbook,', '',
     ('That is the one. The corners are bent exactly as I bent them.',
      'Take this: a plate from a survey drone. It turned salt spray for six years. It will make what strikes you matter less.'),
     (), ',aug_defense7,', '', {'note': 'Defense Augmentation: every hit you take costs you less.'}),
    # Commodore Hollis Marr: a voice on the speaker post before the Sea Gate, then in person.
    ('MarrSpeaker', 'Commodore Marr', 'SM_HN_Speaker', 'bf_alice', 'radio', SPEAKER, 180, '', ',keel,',
     ('Whoever you are, stop at the gate. This is Commodore Hollis Marr, Bastion Halcyon. The harbour is closed.',
      'I know what you are. The fleets went quiet at Meridian and my machines did not, and I have had ten months in here to think about why. I decided I did not care.',
      'I was nine when the wave came. I was on the hill with my father, watching the boats. He went down to help. You may read that in the stones if you like. I would rather you did not.',
      'The Undertow holds the sea back from this rock and from this town. If it stops, nothing does. Go home.'),
     (('The war has paused.', ('A pause is when they reload. I have read history too, whatever Kairos thinks.',)),
      ('The sea is not your enemy.', ('No. It was the weapon. I am not waiting to find out who picks it up next.',))),
     '', '', {}),
    ('Marr', 'Commodore Marr', 'Marr', 'bf_alice', 'human', MARR_SPOT, 250, ',keel,', '',
     ('It is quiet. I had forgotten the Undertow made a sound until it stopped.',
      'I watched the water come down. I expected a wave. It just lay down, like something that had been standing too long.',
      'I am not going to thank you. I do not know yet whether you have done a good thing. I know I could not have done it, and that the Keel would have kept on long after I was dead, holding back a sea that was never coming.',
      'Take what the Keel left. And when the tables are laid and the First Ones sit down across from us, tell them Hollis Marr was nine, and on the hill, and that she is still on the hill.'),
     (('What will you do?', ('Go down to the town. I have not walked the High Street in ten years. I used to know every door.',)),
      ('Your father.', ('Do not. Not yet. Kairos can have the record. I want the morning for myself a little longer.',))),
     ',marr,', QUEST_KAIROS, {'note': 'Commodore Marr opens the Bastion\'s stores to you.'}),
)

# The echoes: (key, mesh, (x, y), z offset cm above the ground or None, yaw, the line, token). Read where they stood.
ECHOES = (
    ('Harbourmaster', 'SM_HP_Echo0', plan.HARBOURMASTER, 720.0, 200,
     'The harbourmaster stands on her roof with a signal lamp, looking out at the wall that is about to break.~"Hold the line," she says to someone below. "Hold the line, and get the children up the hill."~The Litany\'s first line: Hold the line.',
     ',ha_line1,'),
    ('Foreman', 'SM_HP_Echo1', plan.FOREMAN, None, 250,
     'The foreman leans out of his crane cab, counting the boats still at sea on his fingers.~"Remember the drowned," he says, very quietly. "Every name. Somebody has to."~The Litany\'s second line: Remember the drowned.',
     ',ha_line2,'),
    ('Keeper', 'SM_HP_Echo2', plan.LIGHTHOUSE, 2200.0, 190,
     'The keeper stands at the lamp as the light in the sky grows, too late to warn anyone of anything.~"Let no wave come again," she says. "Not here. Not anywhere."~The Litany\'s third line: Let no wave come again.',
     ',ha_line3,'),
)

HALCYON_TUTORIALS = (
    ('Divinity current: step into the light to travel between Earth and the Center.', (plan.GARDEN[0] + 8.0, plan.GARDEN[1] + 6.0), (.35, 2.0, 1)),
    ('Trace Reading: T / hold |DPadDown|     Read the past: what stood here shows in silver and bears your weight while you read.',
     (plan.BRIDGE_SOUTH[0] - 16.0, plan.BRIDGE_SOUTH[1]), (.6, 3.0, 1)),
    ('A reading lasts ten seconds. Read again before it ends to keep the past standing.', (plan.QUARTER_STILL[0], plan.QUARTER_STILL[1]), (.6, 3.0, 1)),
)

ARRIVAL_LINE = ('Arrival at Halcyon', 'Divinity speaks. Earth again: Port Halcyon. The first place on your world the war ever reached. The town is quiet, and under the quiet it is still the morning of the strike. Kairos is here. Find him.')

CLOCK_DONE = ('Kairos lays his hand on the Clocktower\'s door, and Physis lets the present go quiet. The street fills, for a moment, with people who are not there: the morning before the wave.~'
              'Trace Reading learned: T / hold |DPadDown|.  Read the past: what stood here once shows in silver, and bears your weight while you read.~'
              'A reading lasts ten seconds. Read again to keep it.~'
              'The Breach is north of here. The Harbour Bridge stood across it.')

MESSAGES = {
    'arrive': 'Port Halcyon.~The current has carried Physis back to Earth.',
    'clock_denied': 'The Clocktower, stopped at fourteen minutes past seven. Kairos, at the Signal House, wants to show you something here.',
    'bridge': 'The Harbour Bridge, as it stood. It will bear you while you read.',
    'gate': 'Three lines, spoken by those who first swore them, and the Sea Gate opens.~The Bastion is ahead.',
    'gate_wait': 'The Sea Gate waits for the Litany: all three lines.',
    'keel': 'The Keel goes still, and the Undertow stops. All round the Bastion, the Held Sea lies down.~Commodore Marr is in the court.',
    'shelf': 'A shelf of the library, as it stood before the fire.',
    'shelves': 'The reading room\'s lock remembers its shelves. It opens.',
    'logbook': 'Ledger\'s logbook. Ledger, at the Signal House, will want it back.',
    'heart': 'The Undertow\'s Heart. Health Augmentation: one more Health Tank, and you are fully healed.',
    'knife': 'The Reader\'s Knife. Katana Augmentation: every katana strike is stronger.',
    'cache': 'A tide cache. Divinity +40.',
    'echo_guard': 'The Tide Guard here is down. The past is quiet enough to read.',
    'pontoons': 'The town has laid a bridge of pontoons across the Breach.',
}


def person_key(key, page):
    return 'Talk %s %d' % (key, page)


def conversation_pages(person):
    greeting, topics = person[9], person[10]
    pages = list(greeting)
    for _, answer in topics:
        pages.extend(answer)
    return pages


def halcyon_entries():
    """Logbook rows (category, title, text) for every scan, lock kind and enemy."""
    return [row[:3] for row in HALCYON_SCANS] + list(HALCYON_GATES) + [entry[4] for entry in HALCYON_ENEMIES.values()]
