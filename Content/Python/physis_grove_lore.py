"""Text for level 4, Earth: the Wounded Grove. Divinity's scans, the people's conversations, enemies, tutorials and
quest messages. Voices come from Tools/build_physis_voice.py --grove (scans in Divinity's voice, each person in their
own Kokoro voice). Places are plan metres (physis_grove_plan: x north, y east); a z of None puts a scan marker 1.5 m
above the ground.

Conversations (PEOPLE) work as the Conclave's: a person appears while their Show token is held (or always, '') and
until their Hide token is held; a greeting (pages), then topics the player picks from, each answered in pages, then
Leave. When the greeting ends the first time the person gives Give, sets the quest to Quest and grants any reward.

In-game text names actions, not keys; only the tutorial strips and the "learned" line show inputs.
"""
import physis_grove_plan as plan

# ---------------------------------------------------------------- Divinity's scans

# Category, title, text, (x, y, z or None), important.
GROVE_SCANS = (
    # Places.
    ('Rooms', 'The Hollow', 'Divinity speaks. A hollow in the old forest where Divinity pools of its own accord. The current that carried you here returns to the Center from this pool, whenever you step into it. This is a Still Point.', (-494, 40, None), True),
    ('Rooms', 'The Reclaimed Road', 'Divinity speaks. A highway, once. The valley\'s people left it when the Just closed the grove to them, forty years ago, and the forest has been taking it back ever since. It runs north to a field camp. The Hedge patrols it.', (-440, 84, None), True),
    ('Rooms', 'Old Town', 'Divinity speaks. A town the valley emptied when the Array was built. Nobody was made to leave. They were asked, and the asking came with soldiers. Something heavy still walks its streets. You do not have to meet it.', (-345, 245, None), False),
    ('Rooms', 'The Field Camp', 'Divinity speaks. The Array\'s field station: shelters, a glasshouse, a nursery of grafted saplings. One Robot of the Just keeps it alone. The Hedge does not come here. Nobody ever told it that its own people could be a threat.', (-262, 6, None), True),
    ('Rooms', 'The Graft', 'Divinity speaks. Two trunks, grown into one by a patient hand. Under them the roots of the whole valley meet. Something here is trying very hard to be heard.', (-166, 46, None), True),
    ('Rooms', 'The Gully', 'Divinity speaks. A gorge the river cut before the weir turned it aside. Its bridge fell long ago, and nothing that walks or leaps will cross it. If you fall in, follow its floor west to the one way out, on the south side.', (-122, 36, None), True),
    ('Rooms', 'The Understory', 'Divinity speaks. The middle of the valley, under the oldest canopy. The trails part here: west to the drowned campus and the weir, east to the great trees and the relay, north to the Rift. This is a Still Point.', (-36, 10, None), True),
    ('Rooms', 'The Drowned Campus', 'Divinity speaks. The Array\'s research blocks, under the lake the weir made of them. Their roofs still stand out of the water. The weir closes the lake\'s north end, and its deck is too high to climb from the water.', (22, -152, None), True),
    ('Rooms', 'The Weir', 'Divinity speaks. The Just dammed the river here to cool the Array, and sent what was left of it into the campus. The grove\'s western roots have had no river since. The headpond still holds one. The sluice that would release it has no hand to turn it.', (196, -248, 1500), True),
    ('Rooms', 'The High Canopy', 'Divinity speaks. The valley\'s great trees, three of them older than the Just. The botanists built platforms in their crowns to measure what the Array did to them. The relay stands on the mesa beyond the third.', (48, 190, None), True),
    ('Rooms', 'The Relay', 'Divinity speaks. A mast that once carried the valley\'s light. The Array took its charge for itself and left the capacitors full and unconnected. The old line to the Heartwood still crosses the Rift, dead.', (178, 326, 6400), True),
    ('Rooms', 'The Rift', 'Divinity speaks. The first time the Array fired, the ground tore open around the Heartwood. It has not closed. It is as wide as the Gully and deeper. If you fall in, its floor leads to one way out, on the south-east side, away from the tree.', (204, -14, None), True),
    ('Rooms', 'The Heartwood', 'Divinity speaks. The oldest tree in the valley, and in a way the only one: every trunk here grows from its roots. The Just built the Deeproot Array round its foot to push Divinity through those roots and out into the sky. It is in pain, and it has been for forty years.', (250, -12, None), True),
    ('Rooms', 'The Deeproot Array', 'Divinity speaks. A weapon made of a forest. It drives Divinity down into the Heartwood\'s roots, and the whole grove throws it at whatever is overhead. It fired twice in the war. Nobody is firing it now. Its defence, the Hedge, simply never stopped.', (284, -12, None), True),
    ('Rooms', 'The Falls', 'Divinity speaks. Where the river enters the valley. Something of the grove\'s has been growing up the cliff beside the water, out of the Hedge\'s reach.', (378, -262, None), False),
    # Story.
    ('Story', 'One Tree', 'Recorded by Thessaly-4, botanist. Site Verdance, survey one. Every trunk sampled shares one genome. The grove is a single organism, joined at the root, at least nine thousand years old. I have asked that the Array be sited elsewhere. I am told the roots are why it is sited here.', (-256, -20, None), False),
    ('Story', 'The Nursery', 'Recorded by Thessaly-4, botanist. Graft trials, year thirty-one. Scions cut from blighted wood take on clean rootstock nine times in ten. The wound is not in the tree. It is in what we ask the tree to carry.', (-236, -16, None), False),
    ('Story', 'Thornroot', 'Divinity speaks. Roots that Divinity was forced through. They came up black and barbed, and they hold the shape of the force that made them. Walls of it part for Settle, as weaponised things do. Knots of it break to the blade.', (-452, 66, None), True),
    ('Story', 'The Hedge', 'Divinity speaks. The Array\'s defence: forestry machines given weapons and one instruction, to keep everything out. The Just built it without a mind on purpose, so that it could never be argued with. It has not been told the war has stopped. There is no one in it to tell.', (-300, 44, None), True),
    ('Story', 'Burr', 'Divinity speaks. A Mechanoid loader of the Just, very strong and very patient. The overpass came down nine years ago with a survey crew beneath it. They walked out. He has held the slab ever since, because nobody told him he could stop, and because he is not sure the road has finished falling.', (-404, 100, None), False),
    ('Story', 'Site Verdance', 'Recorded by Director Maren Voss. Verdance is the seventh of seventeen. It is the only one that grows. If you are reading this from outside the wall, understand that the wall is not there to keep you from us. It is there to keep the sky from you.', (240, -28, None), False),
    ('Story', 'The Firing Log', 'Recorded by the Array. Discharge one: a Vigil picket, driven from low orbit. No losses on the ground. Discharge two: a Serene survey ship, engines stilled, its crew recovered by their own. Root mortality after discharge two: eleven percent. Recommendation: none. Standing order: maintain readiness.', (300, -44, None), False),
    # How things work.
    ('Items', 'Link Anchor', 'Divinity speaks. A knot of living root, holding a seed that resonates with every other in the valley. Look at it and use Resonance Link, and the link draws you to it. They grow where the grove wants to be reached.', (-118, 46, None), True),
    ('Items', 'Flow Source', 'Divinity speaks. Something that flows, gathered and waiting: water, charge, or Divinity itself. Use Resonance Link on it and you carry its flow with you on a thread of light, as far as the thread will stretch. Then give it to a relay, or to its socket.', (196, -284, 1350), True),
    ('Items', 'Flow Relay', 'Divinity speaks. A standing knot that can hold a flow and pass it on. Link it while you carry the flow it waits for, and the flow runs from here instead. A flow turns its corners at relays.', (196, -262, 1350), True),
    ('Items', 'Flow Socket', 'Divinity speaks. A cradle of root and brass, waiting for the flow that belongs in it. Carry that flow here and link the socket. Nothing else will fill it.', (196, -240, 1350), True),
    ('Items', 'The Sluice', 'Recorded by the weir\'s keeper. To open the east sluice by hand: draw from the headpond at the deck\'s west end, pass it on at the middle tower, and seat it in the wheel at the east end. The wheel does the rest. Never without the Director\'s word: the Array runs dry in a day.', (196, -256, 1350), True),
    ('Items', 'The Capacitor Bank', 'Recorded by the relay\'s engineer. The bank charges from the mast\'s own cells whether or not anyone wants it. To put the charge on the old line: take it from the bank, pass it on at the plinth, and seat it at the coupling on the mast\'s deck. The Array will feel it at once.', (172, 318, 6400), True),
    ('Items', 'The Array Gate', 'Divinity speaks. The gate reads two lines before it opens: the river in the western roots, and the charge on the old line from the relay. It was built to open only when the grove was whole enough to defend. Give the grove its water and its light, and the gate will take that for an order.', (252, -14, None), True),
    ('Items', 'The Core Coupling', 'Divinity speaks. Here the Array takes Divinity from the air and drives it down into the roots. The surge gathers at the emitter crown. The Heartwood\'s own heart is the socket at the trunk\'s foot. Carry the surge to the heart instead of the roots, relay by relay, and the forcing stops.', (292, -8, None), True),
    ('Items', 'Forced Vent', 'Divinity speaks. A wound the Array keeps open, to bleed off what the roots cannot carry. It burns in pulses. Cross while it is dark, or stand at its edge and Settle it, and it stays closed.', (296, 10, None), False),
    ('Items', 'Shield Emitter', 'Divinity speaks. One of the emitters that feed the Warden\'s guard, fixed high on the wall. A blade will not reach it. A shot will.', (372, -60, None), True),
    ('Items', 'Root Bridge', 'Divinity speaks. Roots that have drunk, and reached. The grove grows these where it is whole enough to. It will hold you.', (262, -124, None), False),
    ('Items', 'Seed Cache', 'Divinity speaks. Seeds the grove has set aside, heavy with Divinity. Walk into the cache to take what it holds. There are others in the valley.', (-470, 20, None), False),
    ('Items', 'Divinity Current', 'Divinity speaks. A current of Divinity between Earth and the Center. Step into its light and it will carry you across.', (-504, 24, None), True),
    # Relics: their tags ride on BP_Relic (center_logic.py RELIC_SCANS, by token), so the scenario places no free tag
    # for them (physis_grove_scenario.ATTACHED); their points are only where they lie.
    ('Items', "Burr's Coupling Pin", 'Divinity speaks. A loader\'s coupling pin, heavy steel with a brass collar. It is Burr\'s, lost when his hauler went into the lake. Walk into it to take it, then bring it to Burr, under the fallen overpass on the Reclaimed Road.', (-30, -214, None), True),
    ('Items', 'A Seed Canister', 'Divinity speaks. A sealed canister from the Array\'s seed bank: this valley\'s trees, kept against the day the Array killed them. Three were lost when the Hedge sealed the gates: one in Old Town, one on a roof of the Drowned Campus, one in the High Canopy. Walk into each to take it, then bring them to Wick at the Field Camp.', (-330, 262, None), True),
    ('Items', "The Heartwood's Gift", 'Divinity speaks. A Health Augmentation, grown at the Heartwood\'s foot from the first sap it has made freely in forty years. Walk into it, and Physis gains a Health Tank and is whole again.', (350, -20, None), True),
    ('Items', 'The Old Edge', 'Divinity speaks. A Katana Augmentation: a bar of blade steel from before the war, kept in Old Town\'s vault. Walk into it, and every katana strike is stronger.', (-300, 300, None), True),
)

# What each kind of lock is (Logbook entries without a marker of their own).
GROVE_GATES = (
    ('Items', 'Sealed Vault', 'Divinity speaks. A vault of the Just, sealed with a lock you cannot open yet. Remember where it stands: what opens it is learned elsewhere.'),
)

# Enemies by level: mesh, health, scale, hover height (cm), Logbook entry, EnemyKind (0 plain, 1 turns light blows,
# 3 fast, 4 its face turns every blow; center_overrides.py DroneArmour).
GROVE_ENEMIES = {
    1: ('SM_GE_Wasp', 5, 1.0, 150, ('Enemies', 'Hedge Wasp', 'Level 1. The Hedge\'s smallest machine, a pruning drone with a sting. Quick, and never alone. It is the easiest thing in the valley to link a stronger machine to. Five health.'), 3),
    2: ('SM_GE_Lancet', 9, 1.0, 170, ('Enemies', 'Hedge Lancet', 'Level 2. A machine built to cut limbs from a distance, turned on whatever moves. Its volleys are long. Parry just before a bolt lands, or dodge. Nine health.'), 0),
    3: ('SM_GE_Burl', 16, 1.0, 190, ('Enemies', 'Hedge Burl', 'Level 3. A shell of plates round a small engine. Light blows glance off it. Strike heavy, Settle it, or link it to something softer and strike that. Sixteen health.'), 1),
    4: ('SM_GE_Palisade', 20, 1.0, 200, ('Enemies', 'Hedge Palisade', 'Level 4. A wall of staves that walks. Its face turns every blow. Strike its back, or link it to another machine: what one suffers, the other suffers. Twenty health.'), 4),
    5: ('SM_GE_Thresher', 26, 1.0, 220, ('Enemies', 'Hedge Thresher', 'Level 4. The Hedge\'s guard, set over what it was told to keep: the weir, the relay, the Rift. Parry its volleys and strike while it recovers. Twenty-six health.'), 0),
    6: ('SM_GE_Harrow', 60, 1.0, 380, ('Enemies', 'Hedge Harrow', 'Level 5, end-game. A machine for breaking ground, and it breaks whatever stands on it. You do not have to fight it. If you do: parry everything, Settle it, and bring capsules. Sixty health.'), 0),
    7: ('SM_GE_Warden', 110, 1.0, 430, ('Enemies', 'The Warden', 'Boss. The Hedge\'s core, grown into the Array. Its face turns every blow, and the emitters on the wall feed its guard: break those with the sidearm. Then link it to one of its own Wasps and strike the Wasp, or get behind it. One hundred and ten health.'), 4),
}

# ---------------------------------------------------------------- people

QUEST_ARRIVE = 'Follow the old road north to the Field Camp'
QUEST_GRAFT = 'Go to the Graft, north of the Field Camp, and listen to it'
QUEST_GULLY = 'Cross the Gully, north of the Graft, with Resonance Link'
QUEST_LIFELINES = 'Give the grove its water at the Weir, west, and its light at the Relay, east'
QUEST_GATE = 'Both lifelines are back. Cross the Rift to the gate of the Deeproot Array'
QUEST_CORE = 'Carry the surge from the emitter crown to the Heartwood, at the core coupling'
QUEST_WARDEN = 'Stop the Warden, behind the Heartwood'
QUEST_VOSS = 'Speak to Director Voss, at the control bunker in the Root Court'
QUEST_THESSALY = 'Return to Thessaly at the Field Camp'
QUEST_DONE = 'Explore the grove, or return to the Center through the Hollow'
# Set once by the Center's temple current to Earth when it opens (the Shepherd fallen, Earth not yet visited).
QUEST_CURRENT = 'A new Divinity current has opened in the sanctum. Step into it to follow it to Earth'

# Kokoro voice kinds (Tools/build_physis_voice.py KINDS): human, robot, mechanoid, and radio (a human on an intercom).
CAMP_POST = (plan.CAMP[0] + 14.0, plan.CAMP[1] + 12.0)
GATE_POST = (plan.FORECOURT[0] + 4.0, plan.FORECOURT[1] - 9.0)
CORE_POST = (plan.ROOT_COURT[0] + 6.0, plan.ROOT_COURT[1] + 9.0)
BUNKER = (plan.HEARTWOOD[0] - 6.0, plan.HEARTWOOD[1] + 52.0)       # the control bunker, in the Root Court's east side

# key, speaker, mesh, voice, kind, (x, y), yaw (deg, 0 faces north), show, hide, greeting pages,
# topics ((label, pages), ...), give, quest, reward ({'divinity': n, 'heal': bool, 'note': text}).
PEOPLE = (
    # The Field Camp.
    ('Thessaly', 'Thessaly-4', 'SM_GP_Thessaly', 'af_kore', 'robot', (plan.CAMP[0] + 4.0, plan.CAMP[1] - 6.0), 200, '', ',resonance,',
     ('You are not on any list I was given. Good. Everything on my lists has been trying to kill this valley.',
      'Thessaly-4, field botany, Site Verdance. The Just built me to measure what the Array does to the grove. For forty years I have measured it, and reported it, and been thanked.',
      'This grove is one tree. Ten thousand trunks on one root, older than every city your kind ever built. The Array drives Divinity through that root as if it were cable. It is not cable. It comes up as thorns.',
      'When the fleets went quiet, the Array\'s defence sealed the wall with the Director inside it and me outside. It is still forcing the roots. A few more weeks, and there will be nothing left to measure.',
      'Come north of the camp, to my oldest graft. I think the grove has been trying to tell me something there for years. I am the wrong kind of listener. You may be the right kind.'),
     (('What is the Hedge?', ('Forestry machines with weapons and one instruction: keep everything out. The Just gave it no mind, so that nobody could ever talk it round. I have tried. It prunes me politely and carries on.',
                              'It does not come into the camp. Nobody ever told it that its own botanist might be a threat. I try not to give it ideas.')),
      ('Who is the Director?', ('Maren Voss. She has run Verdance for nineteen years. She is not cruel. She believes that if the Array stops, the sky is open, and she has seen what comes out of an open sky.',
                                'She talks on the intercom posts when she thinks I am not listening. I am always listening. It is most of what I am.')),
      ('Why did you stay?', ('The Robots who left for the Conclave asked me that. I told them someone should be here when it stopped hurting. I did not expect to be here this long.',))),
     ',tess,', QUEST_GRAFT, {}),
    ('ThessalyLink', 'Thessaly-4', 'SM_GP_Thessaly', 'af_kore', 'robot', (plan.CAMP[0] + 4.0, plan.CAMP[1] - 6.0), 200, ',resonance,', ',warden,',
     ('I saw the knots light from here. Forty years, and they light for someone who has been on Earth an afternoon. I am not offended. I am taking notes.',
      'The grove needs two things the Array took from it. The river: the weir in the west sends it into the old campus instead of the roots. And the charge from the relay mast in the east, which once ran to the Heartwood on its own line.',
      'Give both back and the Array\'s gate will open. It was built to open only for a grove strong enough to defend. Nobody thought anyone would make it strong on purpose.'),
     (('How do I use the link?', ('Look at what you want to reach, and reach. A knot will draw you to it. A source will give you its flow to carry, as far as the thread stretches. A relay will take it on from there. A socket will keep it.',
                                  'And the Hedge\'s machines can be tied to one another. What one suffers, the other suffers, plates or no plates. I worked that out on paper years ago. I never had the hands for it.')),
      ('Water or light first?', ('That is the question I would ask. The grove will not answer the same way to water first as to light first. The roots that wake first will lead. Either way, it ends at the Heartwood.',))),
     '', QUEST_LIFELINES, {}),
    ('ThessalyDone', 'Thessaly-4', 'SM_GP_Thessaly', 'af_kore', 'robot', (plan.CAMP[0] + 4.0, plan.CAMP[1] - 6.0), 200, ',warden,', '',
     ('The thorns are going back into the ground. I watched them come up for forty years, and I had no measurement for this. I have had to invent one.',
      'You did not break the Array. You gave what it was forcing somewhere else to go, and the forcing had nothing left to push against. I will write that down carefully. The Just will want to say they switched it off.',
      'Verdance is one of seventeen. The others are not groves. Some of them are worse. But at every one of them there is someone who has been measuring, as I have, and waiting for somebody who could listen.',
      'The current in the Hollow will take you back to the Center whenever you wish. The valley is yours to walk. It will want to show you what it can do, now that it can.'),
     (('What happens to the Director?', ('She walked out of her bunker and stood under the Heartwood for an hour without saying anything. Then she asked me for my data. All of it. I think that is how she apologises.',)),
      ('And you?', ('I have nine thousand years of tree to look after and, for the first time, nothing hurting it. I intend to be extremely boring about it.',))),
     ',grove_done,', QUEST_DONE, {'divinity': 60, 'heal': True, 'note': 'Thessaly\'s thanks: 60 Divinity, and you are fully healed.'}),
    ('Wick', 'Wick', 'SM_GP_Wick', 'am_liam', 'robot', (plan.CAMP[0] - 8.0, plan.CAMP[1] + 10.0), 140, '', ',cans,',
     ('Visitor! Visitor at the camp. I would announce you, but there is only Thessaly, and she saw you first. She sees everything first. It is very unfair.',
      'Wick. Courier, light, the last one. When the wall sealed, three canisters from the seed bank were out for survey. Every tree in this valley, in three tins. I know where I dropped each one. So does the Hedge.',
      'One in Old Town, one on a roof in the drowned campus, one up in the great trees. Bring them back and the grove has a spare of itself. I would go, but I am small and the Hedge is not.'),
     (('Any news?', ('The Director talked to the post for an hour last night. Nobody answered. I nearly did. Thessaly says that is called being kind, and to stop it.',)),),
     ',wick,', '', {}),
    ('WickThanks', 'Wick', 'SM_GP_Wick', 'am_liam', 'robot', (plan.CAMP[0] - 8.0, plan.CAMP[1] + 10.0), 140, ',cans,', '',
     ('One, two, three. All three! I have been rehearsing what I would say, and I have forgotten all of it.',
      'Here. My spare gyro. It is how a courier knows the exact moment to turn. You will know the exact moment to do whatever it is you do.'),
     (), ',aug_agility5,', '', {'note': 'Agility Augmentation: the moment in which a block becomes a perfect parry is longer.'}),
    # The Reclaimed Road.
    ('Burr', 'Burr', 'SM_GP_Burr', 'am_fenrir', 'mechanoid', (plan.OVERPASS[0] + 4.0, plan.OVERPASS[1] - 3.5), 160, '', ',pin,',
     ('Mind the slab. I have it. I have had it for nine years, two months and some days. I stopped counting the days. That was a mistake. Now I am curious.',
      'Burr. Loader, heavy, Site Verdance. The overpass came down on a survey crew. They got out. Nobody came back to say I could put it down, and I am not certain the road has finished falling.',
      'I could lock my shoulders and let the frame carry it, if I had my coupling pin. It went into the lake with my hauler, on the campus side. If you are ever out that way.'),
     (('Does it hurt?', ('I am a loader. Holding is what I am for. What I mind is the moss. It itches, and I have no hand free.',)),
      ('What do you think of the Array?', ('I carried half of it up that hill. Good concrete. Bad idea. Nobody asks the loader.',))),
     ',burr,', '', {}),
    ('BurrThanks', 'Burr', 'SM_GP_Burr', 'am_fenrir', 'mechanoid', (plan.OVERPASS[0] + 4.0, plan.OVERPASS[1] - 3.5), 160, ',pin,', '',
     ('That is my pin. You went into that lake for a loader\'s pin. Hold on. There. Locked.',
      'Now the frame has it, and I only stand here out of habit. I am a pillar instead of a loader. Pillars do not get tired.',
      'Take this. A brace plate from my own frame. With my shoulders locked I do not need it. Whatever hits you will find you harder to move.'),
     (), ',aug_defense5,', '', {'note': 'Defense Augmentation: every hit you take costs you less.'}),
    # Director Voss: a voice on three intercom posts, then in person.
    ('VossCamp', 'Director Voss', 'SM_GP_Intercom', 'af_sarah', 'radio', CAMP_POST, 215, '', ',warden,',
     ('This is Director Voss. I have you on the camp post. I do not know what you are, and I have stopped expecting to be told things.',
      'Thessaly will have said the Array is killing the grove. She is right. She has been right for forty years. I have signed every one of her reports.',
      'Here is what she does not sign. Twice in this war something came down out of that sky to end us, and twice this valley threw it back. Nothing else on Earth could. If the Array stops, there is nothing between those ships and every city under them.',
      'So I will not open the gate. I could not if I wished to: the Hedge takes my orders no more than yours. But I want it understood that I would not.'),
     (('The fleets have stopped.', ('For a week. I have had weeks before. A ceasefire is a thing that happens between firings.',)),
      ('How many are with you?', ('Eleven. We have air, and water, and one another\'s company, which is wearing thin. Do not come in on our account.',))),
     '', '', {}),
    ('VossGate', 'Director Voss', 'SM_GP_Intercom', 'af_sarah', 'radio', GATE_POST, 180, '', ',warden,',
     ('You have been busy. My instruments say the grove is taking back what we took from it. For nineteen years I was told that could not be done without taking the Array down first.',
      'The gate reads the grove\'s strength. It was meant as a safeguard: the Array arms only when the valley can bear it. You are turning my safeguard into a key. I should be angrier than I am.',
      'The Warden is behind the tree. It is the part of the Hedge that never left the wall. It will not know you from a warship. A week ago, nor would I.'),
     (), '', '', {}),
    ('VossCore', 'Director Voss', 'SM_GP_Intercom', 'af_sarah', 'radio', CORE_POST, 180, ',arraygate,', ',warden,',
     ('I can see you on the court cameras. You are smaller than the readings suggested.',
      'The coupling in front of you takes Divinity out of the air and drives it into the roots. You are going to send it into the heartwood instead. I know, because it is what I would try, if I were not afraid of what happens next.',
      'If you are wrong, we lose the valley and the sky together. If you are right, I have spent nineteen years hurting something for a reason that was never the only one. I do not know which I am hoping for.'),
     (), '', '', {}),
    ('Voss', 'Director Maren Voss', 'Voss', 'af_sarah', 'human', BUNKER, 100, ',warden,', '',
     ('I have not stood outside in nineteen years. I had forgotten that it smells of anything.',
      'It is quiet. Not the valley: the instruments. Forty years of the roots screaming on every channel I own, and I had stopped hearing it as screaming. I thought that was what a grove sounded like.',
      'I will not tell you I was wrong to be afraid. The ships were real. But I told myself the Array was the only thing between us and them, and I never once asked the grove what it could do if we stopped hurting it.',
      'There are sixteen more like this. I know their directors. Some will be harder to reach than I was, and I was not easy. Take this. It is the only thing here that is mine to give.'),
     (('What will you do now?', ('Open the wall. Let the valley\'s people come back, if any of them still want to. Hand Thessaly forty years of data she was never cleared to see. Then, I think, sit down.',)),
      ('Will the sky stay closed?', ('I do not know. That is the first honest answer I have given that question. Ask me again when you have been to the other sixteen.',))),
     ',voss,,aug_pistol4,', QUEST_THESSALY, {'note': 'Pistol Augmentation: every shot strikes harder, the Divinity Shot too.'}),
)

GROVE_TUTORIALS = (
    ('Divinity current: step into the light to travel between Earth and the Center.', (plan.HOLLOW[0] + 8.0, plan.HOLLOW[1] + 6.0), (.35, 2.0, 1)),
    ('Resonance Link: G / |L3|     Look at a glowing knot and link: it draws you to it.~Knots only answer within their reach, and in plain sight.', (plan.GULLY_SOUTH[0] - 6.0, plan.GULLY_SOUTH[1]), (.6, 3.0, 1)),
    ('Flows: link a source to carry its flow, a relay to pass it on, and its socket to deliver it.~The thread only stretches so far.', (plan.QUAY[0], plan.QUAY[1]), (.6, 3.0, 1)),
    ('Tether: link an enemy to tie it to the nearest other. What one suffers, both suffer,~whatever their armour.', (plan.UNDERSTORY[0] + 30.0, plan.UNDERSTORY[1]), (.6, 3.0, 1)),
)

ARRIVAL_LINE = ('Arrival on Earth', 'Divinity speaks. Earth. A valley that is one living thing, and it is in pain. Someone made a weapon of it and never told the weapon to stop. Find who is still here, and listen.')

# The Graft's line when she listens (it teaches the input, like the Heartbloom's).
GRAFT_DONE = ('Physis lays her hand on the graft, and the valley answers: every root, every trunk, one thing.~'
              'Resonance Link learned: G / |L3|.  Look at a glowing knot and link, and it draws you to it.~'
              'Link a source to carry its flow, and its socket to deliver it. Link an enemy to tie it to another.~'
              'The Gully lies north of here. Cross it.')

# Quest messages (the scenario's switches, sockets and relics say these).
MESSAGES = {
    'arrive': 'Earth.~The current has carried Physis to a wounded valley.',
    'graft_denied': 'Two trunks grown into one. Thessaly, at the Field Camp, knows this tree.',
    'thorn_road': 'The thornroot parts. The road north is open.',
    'water': 'The wheel turns, and the river runs east again, into the roots.~Far off, something long dry begins to drink.',
    'power': 'The coupling takes the charge. The old line hums across the valley, toward the Heartwood.',
    'first_w': 'The western roots wake first. They will lead.',
    'first_e': 'The eastern roots wake first. They will lead.',
    'arraygate': 'The gate reads the river in the roots and the charge on the line, and unlocks.',
    'gate_wait': 'The gate is sealed. It waits for the river in the western roots and the charge on the old line.',
    'stabilized': 'The surge turns from the roots and pours into the Heartwood. The forcing stops.~Behind the trunk, a cage of thorn sinks into the ground. Something there wakes.',
    'warden': 'The Warden falls, and the Hedge goes quiet across the valley. The grove breathes out.~Director Voss is at the control bunker.',
    'weir_gate': 'The service gate unlocks from this side. The path beyond leads to the Rift.',
    'weir_guard': 'The deck is clear. The headpond\'s source wakes.',
    'relay_guard': 'The mesa is clear. The capacitor bank wakes.',
    'source_wait': 'It will not give its flow while the Hedge stands guard over it.',
    'pin': 'Burr\'s coupling pin. He is under the fallen overpass, on the Reclaimed Road.',
    'can': 'A seed canister. Wick, at the Field Camp, is looking for three.',
    'cans': 'The last seed canister. Wick, at the Field Camp, will want all three.',
    'gift': 'The Heartwood\'s gift. Health Augmentation: one more Health Tank, and you are fully healed.',
    'edge': 'The Old Edge. Katana Augmentation: every katana strike is stronger.',
    'vault': 'The vault\'s motor takes the charge, and its door grinds open.',
    'cache': 'A seed cache. Divinity +40.',
    'bridge': 'Roots swell out of the Rift\'s wall and knit into a bridge.',
    'falls': 'The grove\'s highest cache. Divinity +80.',
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


def grove_entries():
    """Logbook rows (category, title, text) for every scan, lock kind and enemy."""
    return [row[:3] for row in GROVE_SCANS] + list(GROVE_GATES) + [entry[4] for entry in GROVE_ENEMIES.values()]
