"""Text for level 7, Hesper, the City of One Voice, on Arche. Divinity's scans, the people's conversations, enemies,
tutorials and quest messages. Voices come from Tools/build_physis_voice.py --hesper. Places are plan metres
(physis_hesper_plan: x north, y east); a z of None puts a scan marker 1.5 m above the ground, a number is centimetres.

Conversations (PEOPLE) work as in the Conclave, the Grove, Arche and Halcyon: a person appears while their Show token
is held (or always, '') and until their Hide token is held; a greeting, then topics, then Leave. When the greeting ends
the first time the person gives Give, sets the quest to Quest and grants any reward.

Unison (BP_Unison) is the Concord's tone standing in the air. Inside Dissonance it thins and lets her through; a shell
of it round a thing breaks for good once she holds Dissonance on it for 3 s, saying its Done line.

All of this is new writing for the author to review (GAME_ROADMAP.md "Level 7").
In-game text names actions, not keys; only the tutorial strips and the "learned" line show inputs.
"""
import physis_hesper_plan as plan

# ---------------------------------------------------------------- Divinity's scans

# Category, title, text, (x, y, z or None), important.
HESPER_SCANS = (
    # Places.
    ('Rooms', 'The Sunward Stair', 'Divinity speaks. Hesper, on Arche. The stair where the city came to watch the sun not set. The current that carried you here returns to the Center from this pool. This is a Still Point.', (-494, 30, None), True),
    ('Rooms', 'The Long Terrace', 'Divinity speaks. The road into Hesper along the edge of the plateau. The sun has stood on that horizon for longer than there have been First Ones to see it. Every shadow in this city points the same way.', (-430, 50, None), True),
    ('Rooms', 'The House of Listeners', 'Divinity speaks. Where the Serene of Hesper went when they stopped speaking. Aeon has come here from Kathodos. Something in the air makes your own thoughts sound like someone else\'s.', (-296, 8, None), True),
    ('Rooms', 'The Tuning Court', 'Divinity speaks. Where Hesper\'s bell-wrights tuned what they cast. A fallen bell lies in it, wrapped in the Concord\'s tone so that it cannot ring.', (-222, 40, None), True),
    ('Rooms', 'The Choir Wall', 'Divinity speaks. The Concord\'s tone, standing in the air from the edge to the cliffs. It is not a wall of anything. It is one note, held so hard that nothing out of tune with it can pass.', (-170, 40, None), True),
    ('Rooms', 'The Bell Market', 'Divinity speaks. Where the city bought and sold and argued about the price. The ways part here: west to the Reed Terraces, east to the Amber Galleries and the Watch Spire, north along the Nave to the Concord.', (-70, 20, None), True),
    ('Rooms', 'The Reed Terraces', 'Divinity speaks. Pools stepping down to the edge of the world, and the reeds the Serene cut their flutes from. The Low Bell hangs at the last pool, silenced.', (-20, -160, None), True),
    ('Rooms', 'The Amber Galleries', 'Divinity speaks. Colonnades where Hesper walked and talked in the long light. The Concord has closed their cross-walks with its tone. The Middle Bell hangs in the middle court.', (-4, 180, None), True),
    ('Rooms', 'The Watch Spire', 'Divinity speaks. The tower from which Hesper watched the dark side of the world for anything coming. Its terrace is barred by Unison gates. The High Bell hangs before the tower.', (176, 250, None), True),
    ('Rooms', 'The Nave', 'Divinity speaks. The processional way to the Concord. The tone is strongest here: it crosses the way again and again.', (226, 0, None), True),
    ('Rooms', 'The Concord', 'Divinity speaks. The engine the Vigil raised when the war began, so that Hesper would only ever say one thing. Its horn faces the city. It has not drawn breath in eleven years.', (380, 12, None), True),
    ('Rooms', 'The Hall of Withheld Votes', 'Divinity speaks. Where Hesper counted its disagreements. Three speaking stones stand before its door, sealed in the tone, and the door will not open while they are silent.', (-330, 260, None), True),
    # Story.
    ('Story', 'The Concord', 'Inscribed by the Vigil. Let Hesper speak with one voice, so that no enemy hears us hesitate. Below it, cut much later by another hand: and so that we never hear ourselves.', (-160, 46, None), True),
    ('Story', 'The Three Bells', 'Divinity speaks. Hesper\'s bells rang for a vote: low for no, high for yes, the middle bell for not yet. The Concord silenced all three, because a people with one voice has nothing to vote on. Its gate was cast to open only when they ring.', (126, 10, None), True),
    ('Story', 'Unison', 'Divinity speaks. The Concord\'s tone, where it is strongest, stands up in the air in walls and veils. It does not burn. It refuses. Anything out of tune with it is simply not allowed through.', (300, 40, None), True),
    ('Story', 'The Choir', 'Divinity speaks. The Concord\'s AL: tools without will, the same the Vigil sent to Meridian and set to keep the Lens at Kathodos. They keep the tone sounding. Nothing has ever told them to stop.', (-40, 40, None), True),
    ('Story', 'What Aeon Heard', 'Recorded by Aeon. Eleven years ago I stood on this road and heard a whole city agree with me. I have never been so frightened. Agreement is a thing two people make. Nobody made this.', (-284, -10, None), True),
    # Items.
    ('Items', 'Unison Veil', 'Divinity speaks. The Concord\'s tone standing in the air. Hold a note of your own and it thins around you for as long as you hold it. It will not close on you while you are inside it.', (-160, 22, None), True),
    ('Items', 'Unison Shell', 'Divinity speaks. The tone wrapped round a thing to silence it. Hold your note against it for three breaths and it breaks for good.', (-220, 22, None), True),
    ('Items', 'Dusk Cache', 'Divinity speaks. A First One traveller\'s store, sealed against the long night. Walk into it to take what it holds. There are others in the city.', (-470, 12, None), True),
    ('Items', 'Divinity Current', 'Divinity speaks. A current of Divinity between Arche and the Center. Step into its light and it will carry you across.', (-504, 14, None), True),
    ('Items', 'The Choir Gate', 'Divinity speaks. The Concord\'s gate. It was cast to open when the three bells of Hesper ring together, which the Vigil meant to be never.', (352, 10, None), True),
    ('Items', 'Tuning Pylon', 'Divinity speaks. One of the forks that hold the Concord\'s pitch. The Cantor\'s shield answers to them while they sound. Break the shell of tone round one, then the sidearm will stop it.', (440, 40, 300), True),
    ('Items', 'Tavor\'s Fork', 'Divinity speaks. A bell-wright\'s tuning fork, a metre of bronze, worn bright at the stem. Tavor, at the House of Listeners, left it at the foot of the Watch Spire. Walk into it to take it.', (240, 300, None), False),
    ('Items', 'Anwe\'s Flute', 'Divinity speaks. A reed flute with electrum bands, cut from the Reed Terraces. Anwe, at the House of Listeners, dropped it by the last pool. Walk into it to take it.', (70, -310, None), False),
    ('Items', 'The Concord\'s Heart', 'Divinity speaks. A Health Augmentation, left where the Cantor fell: the stone that held the city\'s one note, now holding nothing. Walk into it: one more Health Tank, and you are fully healed.', (450, 0, None), False),
    ('Items', 'The Dissenter\'s Blade', 'Divinity speaks. A Katana Augmentation: the knife the Hall\'s counters cut each vote-cord with, kept in the Hall of Withheld Votes. Walk into it, and every katana strike is stronger.', (-330, 290, None), False),
)

# What each kind of lock is (Logbook entries without a marker of their own).
HESPER_GATES = (
    ('Items', 'Sealed Vault', 'Divinity speaks. A vault sealed with a lock you can open now. Use what opens it within reach.'),
)

# Enemies by level: mesh (the Ward's AL from the Conclave, in the Concord's service), health, scale, hover height (cm),
# Logbook entry, EnemyKind (0 plain, 1 turns light blows, 3 fast, 4 its face turns every blow). 8 to 13: Arche's animals.
HESPER_ENEMIES = {
    1: ('SM_CE_ALMite', 5, 1.0, 130, ('Enemies', 'Choir Mite', 'Level 1. The smallest AL of the Concord\'s Choir. Quick, and never alone. Five health.'), 3),
    2: ('SM_CE_ALLancer', 9, 1.0, 160, ('Enemies', 'Choir Lancer', 'Level 2. An AL that holds its distance and fires long volleys. Its bolts falter inside your note. Nine health.'), 0),
    3: ('SM_CE_ALBulwark', 16, 1.0, 180, ('Enemies', 'Choir Bulwark', 'Level 3. A heavy AL plated against the blade. Light blows glance off it: strike heavy, Settle it, or tether it to something softer. Sixteen health.'), 1),
    4: ('SM_CE_EchoHunter', 20, 1.0, 200, ('Enemies', 'Choir Hunter', 'Level 4. Fast, and it never stays put. Light Step through its volleys and strike as it turns. Twenty health.'), 3),
    5: ('SM_CE_ALReaver', 26, 1.0, 210, ('Enemies', 'Choir Reaver', 'Level 4. The Choir\'s guard, set over the bells and the Nave. Hold your note and its volleys go out before they reach you. Twenty-six health.'), 0),
    6: ('SM_CE_ALSiegeframe', 60, 1.0, 360, ('Enemies', 'Choir Siegeframe', 'Level 5, end-game. It walks before the Hall of Withheld Votes, to keep anyone from counting. You do not have to fight it. Sixty health.'), 0),
    7: ('SM_SE_Cantor', 140, 1.0, 560, ('Enemies', 'The Cantor', 'Boss. The Concord\'s own voice, made by the Vigil with a First One\'s face. Its shield answers to the four tuning pylons round the court: break each pylon\'s shell with your note, stop it with the sidearm, then fight the Cantor. Its face turns every blow. One hundred and forty health.'), 4),
    8: ('SM_AE_Mote', 4, 1.0, 140, ('Enemies', 'Dusk Mote', 'Level 1. A small air-swimmer of Arche, gold in this light. The tone has made it frantic. Strike it and it scatters like breath on glass, to gather again somewhere quieter. Four health.'), 3),
    9: ('SM_AE_Medusa', 9, 1.0, 190, ('Enemies', 'Bell Medusa', 'Level 2. A drifting bell with long tendrils. It hums the Concord\'s note and cannot stop. When it tips back and calls, it is about to lash: step out of its reach, or parry. Nine health.'), 0),
    10: ('SM_AE_Shellback', 18, 1.0, 170, ('Enemies', 'Shellback', 'Level 3. A grazer in a grown shell. Light blows glance off the shell: strike heavy, Settle it, or tether it to something softer. Eighteen health.'), 1),
    11: ('SM_AE_Ray', 20, 1.0, 230, ('Enemies', 'Sky Ray', 'Level 4. A wing with a tail, and the tail is the weapon. When it banks and calls, step aside from the whip, then strike as it turns. Twenty health.'), 3),
    12: ('SM_AE_Stalker', 28, 1.0, 220, ('Enemies', 'Crest Stalker', 'Level 4. A hunter that keeps a territory. Parry it, and strike while it recovers. Twenty-eight health.'), 0),
    13: ('SM_AE_Leviathan', 70, 1.0, 620, ('Enemies', 'Leviathan', 'Level 5, end-game. One of Arche\'s oldest animals, circling the Hall. You do not have to fight it. If you do, it will scatter and gather again by morning, and there is no morning here.'), 0),
}

# ---------------------------------------------------------------- people

QUEST_ARRIVE = 'Follow the Long Terrace north to the House of Listeners'
QUEST_TUNING = 'Go to the Tuning Court, north of the House of Listeners, with Aeon'
QUEST_WALL = 'Hold your note and pass through the Choir Wall'
QUEST_BELLS = 'Free the three bells: in the Reed Terraces, the Amber Galleries and before the Watch Spire'
QUEST_GATE = 'All three bells are ringing. Follow the Nave north to the Choir Gate'
QUEST_CANTOR = 'Silence the Cantor, in the Concord'
QUEST_VAELUN = 'Speak to Vaelun, the Precentor, in the Concord'
QUEST_AEON = 'Return to Aeon at the House of Listeners'
QUEST_DONE = 'Walk the city, or return to the Center from the Sunward Stair'
# Set once by the Center's temple current to Hesper when it opens (the Keel fallen, Hesper not yet visited).
QUEST_CURRENT = 'A new Divinity current has opened in the sanctum. Step into it to follow it back to the First Ones\' world'

H = plan.HOUSE
VAELUN_SPOT = (plan.CONCORD[0] - 14.0, plan.CONCORD[1] + 20.0)
STONE_GATE = (plan.CHOIR_GATE[0] - 12.0, plan.CHOIR_GATE[1] - 10.0)   # the Concord's speaking stone before the gate

# key, speaker, mesh, voice, kind, (x, y), yaw, show, hide, greeting pages, topics, give, quest, reward
PEOPLE = (
    ('AeonH', 'Aeon', 'SM_AP_Aeon', 'bm_george', 'firstone', (H[0] + 6.0, H[1] - 4.0), 200, '', ',dissonance,',
     ('You came. I hoped the current would bring you before I lost my nerve.',
      'This is Hesper, the Evening. The Vigil\'s city. Do you hear it? Listen to your own thoughts for a moment. They sound a little like a crowd agreeing with you.',
      'That is the Concord. When the war began the Vigil built an engine that sounds one note through every thread of Divinity in the city, so that every voice in Hesper says what the Vigil say. The Serene here stopped speaking rather than say it.',
      'One day soon you will want both our peoples at one table. The Vigil cannot sit at a table while an engine talks for them. Come to the Tuning Court, north of here. I will teach you to hold a note of your own.'),
     (('Why did they build it?', ('Because a people that argues is a people that hesitates, and they were afraid the hesitation would kill us. They were not entirely wrong. Being not entirely wrong is how most terrible things are built.',)),
      ('Why have you come?', ('Because I am the eldest of the Serene, and I let this happen by being patient. Patience is not the same as peace. It took me eleven years to learn that, which for me is quickly.',)),
      ('The Serene here.', ('Liss, Tavor and Anwe. They are speaking to you now with their hands. Be kind with them. Every word they say in this city comes out as someone else\'s.',))),
     ',aeon_h,', QUEST_TUNING, {}),
    ('AeonNote', 'Aeon', 'SM_AP_Aeon', 'bm_george', 'firstone', (H[0] + 6.0, H[1] - 4.0), 200, ',dissonance,', ',cantor,',
     ('You held it. A whole note, and the tone just stood aside. Tavor wept. I am told I did too, which I do not believe.',
      'The Concord\'s gate was cast to open when Hesper\'s three bells ring together: low for no, high for yes, the middle for not yet. The Vigil wrapped all three in the tone, so that the city could never vote again.',
      'The Low Bell is at the Reed Terraces, west. The Middle Bell in the Amber Galleries, east. The High Bell before the Watch Spire, north-east. Free them, and the gate will hear a city disagreeing with itself.'),
     (('How long can I hold it?', ('Eight breaths, then you must rest two. The tone will not close on you while you stand in it. It will wait. It is very good at waiting. So, now, are you.',)),
      ('What will the Vigil do?', ('Hear themselves, I hope, for the first time in eleven years. I do not know what they will say. That is rather the point.',))),
     '', QUEST_WALL, {}),
    ('AeonDone', 'Aeon', 'SM_AP_Aeon', 'bm_george', 'firstone', (H[0] + 6.0, H[1] - 4.0), 200, ',cantor,', '',
     ('Listen. The whole city is talking. Most of it is arguing. It is the most beautiful thing I have heard since your kind first looked up.',
      'Vaelun came down the Nave a little while ago and sat on the steps of the market, and three of the Serene sat down beside her, and nobody said anything sensible at all. It was perfect.',
      'You can ask them now, both peoples, to the same table. Asking is the easy part. Keeping them there when they begin to disagree will be the work of your life.',
      'Take this. It is not a gift from me. It is Divinity, and it was always yours. I am only standing where it fell.'),
     (('Will the Vigil come to the table?', ('Some of them. The ones who heard their own voices tonight and did not like what they had been saying. It is a start.',)),
      ('What will you do now?', ('Go home to Kathodos and count something else. The stones are all down. I find I miss them.',))),
     ',hesper_done,', QUEST_DONE, {'divinity': 80, 'heal': True, 'note': '80 Divinity, and you are fully healed.'}),
    # Liss, a singer of the Serene, who stopped singing.
    ('Liss', 'Liss', 'SM_AP_Serene0', 'af_nicole', 'firstone', (H[0] - 10.0, H[1] + 14.0), 160, '', ',hs_stones,',
     ('I sang in the Hall of Withheld Votes. When the city could not agree I sang the counting, so that everyone would hear the numbers and nobody would shout.',
      'The Vigil sealed the Hall\'s three speaking stones in the tone, so that no vote could ever be counted again. The door opens only when they speak.',
      'You hold a note the Concord cannot. Would you go to the Hall, east of the Long Terrace, and let the stones speak? I would like to hear a number again.'),
     (('What did you sing?', ('Numbers. Forty for, thirty-one against, nine not yet. It was the most important music in the city, and the most boring. I loved it.',)),),
     ',liss,', '', {}),
    ('LissThanks', 'Liss', 'SM_AP_Serene0', 'af_nicole', 'firstone', (H[0] - 10.0, H[1] + 14.0), 160, ',hs_stones,', '',
     ('I heard them from here. All three stones, saying their counts. I had forgotten they had different voices.',
      'Take this: the counter\'s rhythm, the way the Hall kept time when tempers rose. It will widen the moment in which a blow can be turned aside.'),
     (), ',aug_agility8,', '', {'note': 'Agility Augmentation: the moment in which a block becomes a perfect parry is longer.'}),
    # Tavor, the bell-wright.
    ('Tavor', 'Tavor', 'SM_AP_Serene1', 'bm_lewis', 'firstone', (H[0] + 16.0, H[1] + 18.0), 230, '', ',tuningfork,',
     ('I cast the Middle Bell. Not yet, it says. It is my favourite. It is the only honest answer to most questions.',
      'When the Choir came round the Spire I dropped my fork at its foot and ran. A bell-wright without his fork is a man shouting at bronze.',
      'If you are going to the High Bell, I would be grateful.'),
     (('Can a bell be tuned to the Concord?', ('Every bell in Hesper is. That is how they silenced them: the tone wrapped round each one, perfectly in tune, so the bronze could not move.',)),),
     ',tavor,', '', {}),
    ('TavorThanks', 'Tavor', 'SM_AP_Serene1', 'bm_lewis', 'firstone', (H[0] + 16.0, H[1] + 18.0), 230, ',tuningfork,', '',
     ('That is it. Still true. Listen. A. Exactly A.',
      'Here: a plate of bell-bronze from the casting pit, the part that hears the hammer and does not mind. What strikes you will matter less.'),
     (), ',aug_defense8,', '', {'note': 'Defense Augmentation: every hit you take costs you less.'}),
    # Anwe, the youngest.
    ('Anwe', 'Anwe', 'SM_AP_Serene2', 'af_sky', 'firstone', (H[0] - 4.0, H[1] - 18.0), 120, '', ',reedflute,',
     ('I was born after the Concord. I have never said a thing that was mine out loud.',
      'Before the Choir came I cut a flute from the reeds by the last pool on the Terraces and I dropped it there. I want to see whether it plays my note or theirs.'),
     (('What would you say, if you could?', ('I do not know yet. I think that is what I would say.',)),),
     ',anwe,', '', {}),
    ('AnweThanks', 'Anwe', 'SM_AP_Serene2', 'af_sky', 'firstone', (H[0] - 4.0, H[1] - 18.0), 120, ',reedflute,', '',
     ('It plays a note nobody taught it. I think it is mine.',
      'Take this. Tavor says it is a sight from an old bell-tower, for finding the true line to a far bell. I think it will make your shots land harder.'),
     (), ',aug_pistol7,', '', {'note': 'Pistol Augmentation: every shot strikes harder, the Divinity Shot too.'}),
    # Vaelun, Precentor of the Vigil: a voice in the speaking stone before the Choir Gate, then in person.
    ('VaelunStone', 'Vaelun', 'SM_AN_Obelisk', 'bf_lily', 'stone', STONE_GATE, 180, '', ',cantor,',
     ('Stop at the gate. You are standing in Hesper, and Hesper speaks with one voice. This is Vaelun, Precentor of the Vigil. I keep the Concord.',
      'I know what you are. I know Aeon brought you. Aeon has always believed that a people may disagree with itself in the middle of a war and live. Aeon is very old and has never had to win anything.',
      'We argued for ten thousand years under this sun. Then the human ships came, and we argued about them for a season, and in that season we lost three worlds. I will not lose a fourth to a debate.',
      'Go back to the stair. The Concord does not need you to agree with it. It only needs you to leave.'),
     (('The war has paused.', ('A pause is when the other side decides what to do next. I would rather we had already decided.',)),
      ('The Serene cannot speak.', ('They can speak. They simply say what we say. It was the only way to keep them safe from saying something else.',))),
     '', '', {}),
    ('Vaelun', 'Vaelun', 'SM_AP_Vigil', 'bf_lily', 'firstone', VAELUN_SPOT, 250, ',cantor,', '',
     ('It is so loud. Is it always this loud? I had forgotten.',
      'I can hear the Serene in the market. They are arguing about the price of reeds. I can hear my own people on the Nave saying that I was wrong, and some of them saying that I was right, and I do not know which of them frightens me more.',
      'I will not thank you. I do not know yet what you have done. I know that I could not have stopped it, and that it would have gone on long after there was anyone left in Hesper to agree with.',
      'Take what the Cantor left. And when Aeon\'s table is laid, I will come to it. I will disagree with everyone at it. I think that may be the point.'),
     (('What will the Vigil do?', ('Argue. For a season, perhaps longer. I will be in the middle of it, shouting. It is what a Precentor is for. I had forgotten that too.',)),
      ('Why did you keep it?', ('Because the alternative was to hear what we were doing. That is not an excuse. It is only the reason.',))),
     ',vaelun,', QUEST_AEON, {'note': 'Vaelun opens the Concord\'s stores to you.'}),
)

# The bells: (key, place, token, its line when it rings).
BELLS = (
    ('Low', plan.LOW_BELL, ',hs_bell1,', 'The shell of tone breaks, and the Low Bell swings, and rings: no.~For a moment the whole city hears a word it has not been allowed to say.'),
    ('Middle', plan.MID_BELL, ',hs_bell2,', 'The shell of tone breaks, and the Middle Bell rings: not yet.~Somewhere in the House of Listeners, Tavor laughs out loud.'),
    ('High', plan.HIGH_BELL, ',hs_bell3,', 'The shell of tone breaks, and the High Bell rings out over the plateau: yes.~The Concord\'s note wavers, very slightly, for the first time in eleven years.'),
)

HESPER_TUTORIALS = (
    ('Divinity current: step into the light to travel between Arche and the Center.', (plan.STAIR[0] + 8.0, plan.STAIR[1] + 6.0), (.35, 2.0, 1)),
    ('Dissonance: C / hold |DPadUp|     Hold a note of your own: Unison thins inside the ring around you, and the Choir\'s bolts falter.',
     (plan.wall_x(30.0) - 16.0, 30.0), (.6, 3.0, 1)),
    ('A note lasts eight seconds, then rests two. Unison never closes on you while you stand in it.', (plan.TERRACE_STILL[0], plan.TERRACE_STILL[1]), (.6, 3.0, 1)),
)

ARRIVAL_LINE = ('Arrival at Hesper', 'Divinity speaks. Arche again: Hesper, the Evening, the Vigil\'s seat, where the sun never sets. Listen to your own thoughts. They sound like someone else\'s. Aeon is waiting for you.')

TUNING_DONE = ('Aeon stands beside the fallen bell and hums, very low, a note that is not the Concord\'s. Physis finds it, and holds it, and the tone round the bell thins and parts.~'
               'Dissonance learned: C / hold |DPadUp|.  Hold a note of your own: Unison thins inside the ring around you, and shells of it break when held.~'
               'A note lasts eight seconds, then rests two.~'
               'The Choir Wall is north of here.')

MESSAGES = {
    'arrive': 'Hesper.~The current has carried Physis back to the First Ones\' world.',
    'tuning_denied': 'A fallen bell, wrapped in the Concord\'s tone. Aeon, at the House of Listeners, wants to show you something here.',
    'gate': 'Three bells, ringing together: no, not yet, yes. The Choir Gate opens.~The Concord is ahead.',
    'cantor': 'The Cantor falls silent, and the Concord with it. All over Hesper the tone lets go, and the city draws one ragged breath and starts to talk.~Vaelun is in the court.',
    'stone': 'A speaking stone of the Hall, free of the tone. It says its count.',
    'stones': 'All three stones have spoken. The Hall\'s door opens.',
    'fork': 'Tavor\'s tuning fork. Tavor, at the House of Listeners, will want it back.',
    'flute': 'Anwe\'s reed flute. Anwe, at the House of Listeners, will want it back.',
    'heart': 'The Concord\'s Heart. Health Augmentation: one more Health Tank, and you are fully healed.',
    'blade': 'The Dissenter\'s Blade. Katana Augmentation: every katana strike is stronger.',
    'cache': 'A dusk cache. Divinity +40.',
    'bell_guard': 'The Choir here is down. Hold your note against the bell\'s shell.',
    'pylon': 'The pylon\'s shell breaks. It stands open to the sidearm.',
    'tuning_bell': 'The fallen bell\'s shell breaks. It does not ring: it is cracked. But it is free.',
}


def person_key(key, page):
    return 'Talk %s %d' % (key, page)


def conversation_pages(person):
    greeting, topics = person[9], person[10]
    pages = list(greeting)
    for _, answer in topics:
        pages.extend(answer)
    return pages


def hesper_entries():
    """Logbook rows (category, title, text) for every scan, lock kind and enemy."""
    return [row[:3] for row in HESPER_SCANS] + list(HESPER_GATES) + [entry[4] for entry in HESPER_ENEMIES.values()]
