"""Every scan and Logbook entry, shared by the game and Tools/build_physis_voice.py.

Divinity narrates each entry. Records found on the station name their speaker first.
"""

CATEGORIES = ('Rooms', 'Enemies', 'Station', 'Items', 'Story')

# Label of an existing scan target: category, title, text, important.
LOG_ENTRIES = {
    'Scan Conduit': ('Station', 'Live Power Conduit', "A power conduit overloaded by a Divinity surge. The engineers logged it as a fault. It is not a fault: the current is reacting to you. Now that you have traced it, follow the line. Something on the far side of the room is waiting for this signal.", True),
    'Scan Hull Breach': ('Station', 'Hull Breach', 'A First One lance strike tore this hole on day four thousand and fifteen of the war. Emergency foam is holding the vacuum back. It will not hold for long. There is nothing to do here, but do not linger.', False),
    'Scan Sealed Door': ('Station', 'Sealed Door', 'Sealed by Divinity, not by any lock. No human key will open this, and neither can you yet. You can feel it push back. Perhaps you will return when you have learned more.', True),
    'Scan Crew Terminal': ('Story', 'Crew Log: Armory Override', 'Recorded by Quartermaster Lena Hart. Day four thousand and fifteen. Eleven years at the Meridian Front and they have never told us why. If the Armory ever locks down, remember the override: Red, then Gold, then Blue.', True),
    'Scan Armory Rack': ('Items', 'Boarding Blades', 'Recorded by Sergeant Ivo Brand. Their edges stop First One guards where gunfire fails. Every marine here learns the same thing: when they come through the wall, you fight close. Your own blade works the same way.', False),
    'Scan Reactor': ('Station', 'Reactor Core', 'The station\'s heart. Divinity here is twisted into a shape that hurts to perceive. Humanity learned to burn it long before it learned what it was. The gallery\'s node still hums beneath the dead platforms; Divinity spent there would wake the platforms and the sealed door alike. The vent above is starved, with three fuse sockets empty.', True)}

# Category, title, text, place: scans placed in the level by the scenario.
STORY_SCANS = (
    ('Rooms', 'Breach Deck', 'Where you entered the station. The east door is dead, and so is the breaker that feeds it. Something is missing from it. The wreckage here is tall enough to climb. Scan the room for hints.', (900, -250, 150)),
    ('Rooms', 'Damage Control', 'Plasma runs hot and cold across this room. The coolant system is locked out, and a live conduit on the wall is crackling with current. Physis needs to scan the conduit with Divinity Sense to trace the power.', (2620, -600, 150)),
    ('Rooms', 'Crew Ring', 'The crew\'s living ring, overrun by First One units. The way onward stays sealed while they hold it. The crew left their records behind. Scan the room for hints.', (4500, 700, 150)),
    ('Rooms', 'Armory', 'The Armory is in lockdown. Three coloured panels wait on the wall, and only one order will lift it. Someone in the Crew Ring would have known it.', (6620, 600, 150)),
    ('Rooms', 'Boarding Spine', 'The First Ones flooded this corridor with plasma. Moving platforms still drift above it, and something glints on a side ledge. Divinity runs close to the surface here. Scan the room for hints.', (8330, 300, 150)),
    ('Rooms', 'Reactor Gallery', 'The gallery around the reactor core. Its guards will not let you work in peace. The door to the Fleet Bridge is sealed, and the gallery still answers to Divinity. Scan the core for hints.', (11300, -500, 150)),
    ('Rooms', 'Fleet Bridge Approach', 'The approach to the Fleet Bridge. Something enormous blocks the way. Scan it before you fight.', (13620, -760, 150)),
    ('Rooms', 'Observation Deck', 'Both fleets fill the viewport. The deck ends at a single terminal. What happens there is not something you choose.', (16620, -500, 150)),
    ('Story', 'The Last Medic', 'Final record of medical unit Mercy Seven, a Mechanoid, shut down mid-triage. Its last words to a dying marine: Stay with me. Humans, Robots and Mechanoids crewed this station side by side.', (4700, -700, 120)),
    ('Story', 'A Marine\'s Last Note', 'Written by Corporal Ines Varga. A stranger in pale clothes walked out of the breach. No suit. No fear. If she is theirs, we are finished. If she is not, then what is she?', (6800, 700, 120)),
    ('Story', 'The Boarding Cut', 'Recorded by Sergeant Ivo Brand. The First Ones opened this corridor in a single stroke. They looted nothing. They did not even look around.', (8320, -300, 140)),
    ('Story', 'Engineer\'s Log', 'Recorded by Chief Engineer Oduya Hale. We call them the Serene and the Vigil, as if a name could make them less strange. The Serene do not hate us. I think that is the worst part.', (11300, 960, 120)),
    ('Story', 'Standing Fleet Order', 'Issued by Admiral Teodor Sand to every ship at the front. All ships hold the Meridian line. There is no fallback position. There never was.', (13620, 760, 120)),
    ('Story', 'Between the Fleets', 'Divinity speaks. Two fleets, eleven years, and between them the same living substance. Divinity takes no side. Neither, you realize, do you.', (17900, 500, 140)),
    ('Items', 'Reactor Fuse', 'A shielded fuse from the emergency grid. Walk over it to collect it; the HUD counts how many you carry. A breaker uses one, and the reactor vent needs all three. They are scattered across the station.', (1600, 300, 290)),
    ('Items', 'Divinity Node', 'A place where Divinity runs close to the surface. Stand beside it and use Interact to spend the Divinity you carry. Each node shows its cost; collect crystals or destroy drones to gain more.', (2620, 620, 130)),
    ('Items', 'Health Capsule', 'A sealed medical capsule from the station stores. Walk over it to restore part of your health. Drones sometimes guard them, and some rooms keep a few by the entrance.', (2200, -350, 150)),
    ('Items', 'Divinity Crystal', 'A shard of Divinity grown solid. Walk over it to add to the Divinity you carry, shown in the HUD. Spend Divinity at nodes to calm plasma or wake machines, or on a Divinity Shot with the sidearm. Destroyed drones often release it too.', (1200, -350, 150)),
    ('Items', 'Ammo Cell', 'A charge cell for the marine sidearm. Walk over it to refill your reserve, shown at the lower right. Reload when the magazine runs dry.', (6700, 350, 150)),
    ('Items', 'Life Augmentation', 'A First One relic sealed away by the station\'s founders, humming with condensed Divinity. Walk over it to absorb it: Physis permanently gains a Health Tank and is fully healed. Only one rests on Meridian Station.', (3300, 1180, 200)),
    ('Station', 'Reactor Plasma', 'Coolant failed and the core bled through the deck. Liquid plasma burns on contact, costing a little health and throwing you back, or returning you to the last checkpoint in deep pools. Jump over it, or calm it at a Divinity node.', (2030, 620, 60)))
DRONE_ENTRY = ('Enemies', 'AL Drone', 'A First One AL unit. It strafes around you, holds its range and fires a slow red plasma bolt. Before each attack it sparks and whooshes: that is your cue. Parry just before the hit lands to counter, or dodge clear. Six health. When destroyed it often drops Divinity.')
BOSS_ENTRY = ('Enemies', 'Mecha Breacher', 'A First One siege Mecha built to open stations. It always turns to face you, and its front plating turns blades and bullets alike. Strike its glowing red eye three times, with blade or sidearm, and the shock paralyses it for five seconds. While it is frozen, get behind it: only hits to its back do damage. It fires three bolts at once, so dodge or parry between attacks. Thirty health.')
RELEASE_ENTRY = ('Items', 'Jammed Release', 'An emergency door release, jammed open-circuit by the plasma flood. It cannot be reached on foot, but a single hit trips it: draw the sidearm, aim at the release and fire. Tripping it drains the plasma and opens the door.')


def all_entries():
    rows = [value[:3] for value in LOG_ENTRIES.values()] + [row[:3] for row in STORY_SCANS] + [DRONE_ENTRY, BOSS_ENTRY, RELEASE_ENTRY]
    return rows


def voice_name(title):
    return 'S_VO_' + ''.join(c for c in title.title() if c.isalnum())


def image_name(title):
    return 'T_Log_' + ''.join(c for c in title.title() if c.isalnum())


# Category, name, text: every ability, in menu order. Techniques unlock by skill level.
ABILITIES = (
    ('Perception', 'Divinity Sense', 'Use Divinity Sense, then hold scan on a marker to add it to your Logbook.'),
    ('Combat', 'Blade Chain', 'Chain light and heavy attacks. Three strikes each.'),
    ('Combat', 'Perfect Parry', 'Parry just before a hit lands to take no damage and counter.'),
    ('Combat', 'Dodge', 'Dodge to roll clear of attacks and plasma. Parry and dodge share a button: it parries when a hit is coming.'),
    ('Combat', 'Sidearm', 'Draw the pistol and fire to shoot. Hold fire, then release, for a 5-ammo charged shot.'),
    ('Combat', 'Divinity Shot', 'Heavy attack with the sidearm drawn spends 25 Divinity on a powerful shot.'),
    ('Techniques', 'Rising Cut', 'Your chains extend to a fourth strike.'),
    ('Techniques', 'Crescent Step', 'Your chains extend to a fifth strike.'),
    ('Techniques', 'Falling Moon', 'Your chains extend to a sixth strike.'),
    ('Techniques', 'Thousand Petals', 'Your chains extend to a seventh strike.'),
    ('Techniques', 'Severing Wind', 'Your chains extend to an eighth strike.'),
    ('Techniques', 'Final Bloom', 'Your chains reach their ninth and final strike.'))


# The Inner Ring: sixteen rooms between the Crew Ring and the Armory.
# Column one climbs north from the Crew Ring, column two returns south to the Armory.
WING_X = ((4800, 6400), (6400, 8000))
WING_Y0, WING_SIZE, WING_HEIGHT = 1500, 1600, 450
# Name, kind, Logbook guidance.
WING = (
    ('Cargo Lift Hall', 'platform', 'The floor gave way to the reactor plasma below. The cargo lifts still run on their old schedule. Watch them before you leap.'),
    ('Mess Hall', 'enemies', 'Overturned tables and the hum of hostile drones. The far door will not open while they hunt here.'),
    ('Comms Relay', 'relay', 'The door ahead is slaved to the comms relay, and the relay is silent. Something in this room is at fault. Scan the room for hints.'),
    ('Coolant Vats', 'pulse', 'The coolant vats have ruptured. Plasma breathes across the floor in a slow rhythm. Patience is a kind of path.'),
    ('Barracks', 'enemies', 'Bunks, lockers and First One units. A band of plasma splits the room and does not stay hot for long. The exit stays sealed while the drones remain.'),
    ('Signal Junction', 'sequence', 'Three signal panels lock this junction, and someone was tired of getting stuck in here. Scan the room for hints.'),
    ('Starboard Gantry', 'gantry', 'A broken gantry above a pool of plasma. What is left of the walkway is uneven. Look up before you jump.'),
    ('Drone Hangar', 'enemies', 'The hangar racks are still launching. Two support columns stand in the middle of the floor. The door onward stays sealed while the hangar is defended.'),
    ('Pressure Locks', 'locks', 'Two pressure locks hold the exit, and the station\'s pressure logic was built for safety, not speed. The lock beside the door may not be the place to start. Scan the room for hints.'),
    ('Fuel Line Maze', 'shoot', 'A burst fuel line flooded the far side with plasma. The door release is somewhere beyond it, out of reach of any blade. Scan the room for hints.'),
    ('Armory Annex', 'enemies', 'The annex guards keep to the high ground. The marines left supplies by the entrance for exactly this kind of fight.'),
    ('Hydroponics', 'node', 'Plasma flooded the grow beds and the whole floor burns. Divinity runs close to the surface here. Scan the room for hints.'),
    ('Ventilation Shaft', 'lifts', 'Lifts rise and fall across a plasma pit, each on its own rhythm. Timing is everything.'),
    ('Officer Quarters', 'enemies', 'The officers\' deck, with a raised dais in the middle. Its guards will not let you pass. Someone left medical supplies near the door.'),
    ('Medical Bay', 'triage', 'The bay door is locked to the medical systems. Mercy Seven\'s colleagues would have known how to release it. Scan the room for hints.'),
    ('Command Spur', 'final', 'The inner ring\'s command post. The commander left a final order here. Scan the room for hints.'))
WING_STORY = {
    'Comms Relay': ('Station', 'Comms Relay Node', 'The relay node that drives the door. Its fault is a burned Divinity coupling. Your scan has rerouted the signal around it. Somewhere near the exit, a switch has woken.'),
    'Signal Junction': ('Story', 'Signal Officer\'s Note', 'Written by Signal Officer Mara Quill. If you are reading this, the junction locked again. Gold, then Blue, then Red. I wrote it everywhere so nobody else gets stuck in here.'),
    'Medical Bay': ('Station', 'Triage Console', 'The triage console that locks the bay. Its override reads: release on authorized scan. Your scan counts. The medical switch is awake now, kept high and out of reach of patients.'),
    'Pressure Locks': ('Station', 'Pressure Interlock', 'The interlock panel for the exit. Its readout shows two locks in series: the one beside the door is slaved to a partner lock back in the Drone Hangar, and will hold until the partner lets go.'),
    'Hydroponics': ('Story', 'Botanist\'s Note', 'Written by Botanist Sela Wren. The beds flooded again. The node by the door still drinks Divinity. Feed it enough and the plasma sleeps. I keep a few crystals by the entrance for exactly that.'),
    'Command Spur': ('Story', 'Commander\'s Last Order', 'Recorded by Commander Aurel Voss. Release the inner ring and fall back to the Armory. Whoever finds this: the station is yours now. Hold it.'),
}


def wing_room(index):
    """Bounds, entrance point and exit point of a room, by its place in the walk."""
    column = 0 if index < 8 else 1
    row = index if index < 8 else 15 - index
    x1, x2 = WING_X[column]
    y1 = WING_Y0 + WING_SIZE * row
    y2 = y1 + WING_SIZE
    cx = (x1 + x2) / 2
    if column == 0:
        entry = (cx, y1)
        exit_ = (x2, (y1 + y2) / 2) if index == 7 else (cx, y2)
    else:
        entry = (x1, (y1 + y2) / 2) if index == 8 else (cx, y2)
        exit_ = (cx, y1)
    return x1, x2, y1, y2, entry, exit_


def wing_entries():
    rows = []
    for index, (name, kind, guide) in enumerate(WING):
        x1, x2, y1, y2, entry, exit_ = wing_room(index)
        inward = 1 if entry[1] == y1 else -1
        place = (x1 + 160, entry[1] + inward * 220, 150) if entry[0] != x1 else (x1 + 220, y1 + 160, 150)
        rows.append(('Rooms', name, guide, place))
        if name in WING_STORY:
            category, title, text = WING_STORY[name]
            rows.append((category, title, text, (x2 - 120, (y1 + y2) / 2, 140)))
    return rows


STORY_SCANS = STORY_SCANS + tuple(wing_entries())
