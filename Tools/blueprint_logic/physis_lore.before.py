"""Every scan and Logbook entry, shared by the game and Tools/build_physis_voice.py.

Divinity narrates each entry. Records found on the station name their speaker first.
"""

CATEGORIES = ('Rooms', 'Enemies', 'Station', 'Items', 'Story')

# Label of an existing scan target: category, title, text, important.
LOG_ENTRIES = {
    'Scan Conduit': ('Station', 'Live Power Conduit', "A power conduit overloaded by a Divinity surge. The engineers logged it as a fault. It is not a fault: the current is reacting to you. Scanning it traces the live line to the coolant valve on the far side of the room. Once it is traced, the valve will answer you.", True),
    'Scan Hull Breach': ('Station', 'Hull Breach', 'A First One lance strike tore this hole on day four thousand and fifteen of the war. Emergency foam is holding the vacuum back. It will not hold for long. There is nothing to do here, but do not linger.', False),
    'Scan Sealed Door': ('Station', 'Sealed Door', 'Sealed by Divinity, not by any lock. No human key will open this, and neither can you yet. You can feel it push back. Remember this door: you will return when you have learned more.', True),
    'Scan Crew Terminal': ('Story', 'Crew Log: Armory Override', 'Recorded by Quartermaster Lena Hart. Day four thousand and fifteen. Eleven years at the Meridian Front and they have never told us why. If the Armory locks down, the override is Red, then Gold, then Blue. Use the three panels on the Armory\'s left wall, in that order. A wrong press resets the lockdown.', True),
    'Scan Armory Rack': ('Items', 'Boarding Blades', 'Recorded by Sergeant Ivo Brand. Their edges stop First One guards where gunfire fails. Every marine here learns the same thing: when they come through the wall, you fight close. Your own blade works the same way.', False),
    'Scan Reactor': ('Station', 'Reactor Core', 'The station\'s heart. Divinity here is twisted into a shape that hurts to perceive. Humanity learned to burn it long before it learned what it was. To vent the core you need all three reactor fuses, then the Divinity node in this gallery to raise the platforms, then the vent panel at the top.', True)}

# Category, title, text, place: scans placed in the level by the scenario.
STORY_SCANS = (
    ('Rooms', 'Breach Deck', 'Where you entered the station. The east door has no power. Climb the crates on the right to reach a reactor fuse, then cross to the breaker on its island past the live floor. Use the breaker with Interact to open the door. Do not step on the plasma.', (900, -250, 150)),
    ('Rooms', 'Damage Control', 'Three strips of plasma cross this room. They heat and cool in turn: dark means safe, glowing means burning. Scan the live conduit on the right wall, then time your run to the coolant valve on the far left. Spending twenty Divinity at the node by the door calms the plasma for good.', (2620, -600, 150)),
    ('Rooms', 'Crew Ring', 'Two AL drones hold this ring. Destroy them both to open the Armory. A reactor fuse rests on the shelf beside the crew terminal. Scan the terminal for the Armory override.', (4500, 700, 150)),
    ('Rooms', 'Armory', 'The Armory is in lockdown. Press the three wall panels in the order from the crew log: Red, then Gold, then Blue. A wrong press resets them. Your sidearm is drawn with Tab, or up on the directional pad.', (6620, 600, 150)),
    ('Rooms', 'Boarding Spine', 'The First Ones flooded this corridor with plasma. Jump across the moving platforms; hold the jump button longer to jump higher. The last reactor fuse waits on a side platform. A Divinity node at the entrance can calm the flood for thirty Divinity.', (8330, 300, 150)),
    ('Rooms', 'Reactor Gallery', 'Three drones guard the gallery. Destroy them, then spend twenty Divinity at the node to raise the platforms around the core. Climb to the top and use the vent with all three fuses to open the bridge.', (11300, -500, 150)),
    ('Rooms', 'Fleet Bridge Approach', 'The Mecha Breacher waits here. Its armor turns every attack except one: the glowing red eye on its front. Stay in front of it and strike the eye with your blade, or draw your sidearm with Tab and shoot it. Dodge its triple bolts between attacks. Thirty hits bring it down.', (13620, -760, 150)),
    ('Rooms', 'Observation Deck', 'Both fleets fill the viewport. Walk to the terminal at the far end and use it. What happens there is not something you choose.', (16620, -500, 150)),
    ('Story', 'The Last Medic', 'Final record of medical unit Mercy Seven, a Mechanoid, shut down mid-triage. Its last words to a dying marine: Stay with me. Humans, Robots and Mechanoids crewed this station side by side.', (4700, -700, 120)),
    ('Story', 'A Marine\'s Last Note', 'Written by Corporal Ines Varga. A stranger in pale clothes walked out of the breach. No suit. No fear. If she is theirs, we are finished. If she is not, then what is she?', (6800, 700, 120)),
    ('Story', 'The Boarding Cut', 'Recorded by Sergeant Ivo Brand. The First Ones opened this corridor in a single stroke. They looted nothing. They did not even look around.', (8320, -300, 140)),
    ('Story', 'Engineer\'s Log', 'Recorded by Chief Engineer Oduya Hale. We call them the Serene and the Vigil, as if a name could make them less strange. The Serene do not hate us. I think that is the worst part.', (11300, 960, 120)),
    ('Story', 'Standing Fleet Order', 'Issued by Admiral Teodor Sand to every ship at the front. All ships hold the Meridian line. There is no fallback position. There never was.', (13620, 760, 120)),
    ('Story', 'Between the Fleets', 'Divinity speaks. Two fleets, eleven years, and between them the same living substance. Divinity takes no side. Neither, you realize, do you.', (17900, 500, 140)),
    ('Items', 'Reactor Fuse', 'A shielded fuse from the emergency grid. Walk over it to collect it. The reactor cannot vent without all three: one on the Breach Deck crates, one in the Crew Ring, one in the Boarding Spine.', (1600, 300, 290)),
    ('Items', 'Divinity Node', 'A place where Divinity runs close to the surface. Stand beside it and use Interact to spend the Divinity you carry. Each node shows its cost; collect crystals or destroy drones to gain more.', (2620, 620, 130)),
    ('Station', 'Reactor Plasma', 'Coolant failed and the core bled through the deck. Liquid plasma burns on contact, costing a little health and throwing you back, or returning you to the last checkpoint in deep pools. Jump over it, or calm it at a Divinity node.', (2030, 620, 60)))
DRONE_ENTRY = ('Enemies', 'AL Drone', 'A First One AL unit. It strafes around you, holds its range and fires a slow red plasma bolt. Before each attack it sparks and whooshes: that is your cue. Block with Right Mouse just before the hit to parry and counter, or dodge with Left Alt. Six health. It drops Divinity when destroyed.')
BOSS_ENTRY = ('Enemies', 'Mecha Breacher', 'A First One siege Mecha built to open stations. Its plating turns blades and bullets alike, except at its glowing red eye. Face it head on: blade strikes and sidearm shots that land on the front of the eye do damage, hits from the side or behind do nothing. It fires three bolts at once, so dodge or parry between attacks. Thirty health.')


def all_entries():
    rows = [value[:3] for value in LOG_ENTRIES.values()] + [row[:3] for row in STORY_SCANS] + [DRONE_ENTRY, BOSS_ENTRY]
    return rows


def voice_name(title):
    return 'S_VO_' + ''.join(c for c in title.title() if c.isalnum())


def image_name(title):
    return 'T_Log_' + ''.join(c for c in title.title() if c.isalnum())


# Category, name, text: every ability, in menu order. Techniques unlock by skill level.
ABILITIES = (
    ('Perception', 'Scan Visor', 'Open with Q. Hold Right Mouse on a marker to scan it into your Logbook.'),
    ('Combat', 'Blade Chain', 'Light attack with Left Mouse, heavy with Middle Mouse or F. Three strikes each.'),
    ('Combat', 'Perfect Parry', 'Block with Right Mouse just before a hit lands to take no damage and counter.'),
    ('Combat', 'Dodge', 'Left Alt rolls you clear of attacks and plasma.'),
    ('Combat', 'Sidearm', 'Tab draws the pistol. Light attack fires; R reloads. Opens armored seams.'),
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
    ('Cargo Lift Hall', 'platform', 'The floor gave way to the reactor plasma below. Two cargo lifts cross it: jump to the first, wait for the second to swing close, then jump again. Hold the jump button for distance. The exit is straight ahead.'),
    ('Mess Hall', 'enemies', 'Two AL drones fight here among overturned tables. Use the tables as cover from their bolts. The far door stays sealed until both are destroyed. Parry with Right Mouse just before a bolt hits, then close in with your blade.'),
    ('Comms Relay', 'relay', 'The door ahead is slaved to the comms relay. Open the Scan Visor with Q and scan the relay node on the side wall to find its fault, then use the relay switch beside the exit with Interact.'),
    ('Coolant Vats', 'pulse', 'Four bands of plasma pulse across this room in turn. Watch them: dark is safe, glowing burns. Cross each band while it is dark and wait between them.'),
    ('Barracks', 'enemies', 'Two drones hold the barracks, and a pulsing band of plasma splits the room. Fight on the near side or time your crossing while it is dark. Destroy both drones to unseal the exit. Lock on with Left Shift to keep them in front of you.'),
    ('Signal Junction', 'sequence', 'Three signal panels must be pressed in order. The order is in this room\'s scan: Gold, then Blue, then Red. A wrong press resets them. The exit opens when the sequence is complete.'),
    ('Starboard Gantry', 'gantry', 'A broken gantry crosses a pool of plasma. Three walkways remain: jump up to the high middle one, then down to the last. Falling in returns you to this room\'s entrance.'),
    ('Drone Hangar', 'enemies', 'Three drones launch from the hangar racks around two support columns. Destroy all three to open the door into the second half of the ring. Keep moving and use the columns: standing still lets them all fire at once.'),
    ('Pressure Locks', 'locks', 'Two pressure locks hold the exit. Release the far lock first, in the corner opposite the door, then the near lock beside the exit. The near lock will not move while the far one holds.'),
    ('Fuel Line Maze', 'shoot', 'A burst fuel line flooded the far side with plasma, and the door release sits beyond it, out of reach. Your blade cannot get there, but your sidearm can. Draw it with Tab, aim at the jammed release on the far wall and fire with Left Mouse.'),
    ('Armory Annex', 'enemies', 'Two drones guard the annex from high positions. Ammo cells line the entrance. Your sidearm works well here: draw it with Tab and fire with Left Mouse. Destroy both to unseal the exit.'),
    ('Hydroponics', 'node', 'Plasma flooded the grow beds and the whole floor burns. Collect the Divinity crystals by the entrance, then spend twenty Divinity at the node to calm the flood. Then walk across.'),
    ('Ventilation Shaft', 'lifts', 'Two lifts rise and fall across a plasma pit. Ride the first and jump when the second is level with you.'),
    ('Officer Quarters', 'enemies', 'Three drones hold the officers\' deck, with a raised dais in the middle. Fight from the dais to see them all. Destroy all three to unseal the exit. Health capsules wait by the entrance.'),
    ('Medical Bay', 'triage', 'The bay door is locked to the triage console. Scan the console on the side wall to read its override. The medical switch sits on the high gurney shelf: climb the stacked gurneys to reach it, then use it.'),
    ('Command Spur', 'final', 'The inner ring\'s command post. Scan the commander\'s last order on the desk, then use the command switch to release the ring. The door south leads back to the Armory.'))
WING_STORY = {
    'Comms Relay': ('Station', 'Comms Relay Node', 'The relay node that drives the door. Its fault is a burned Divinity coupling: scanning it reroutes the signal. The relay switch beside the exit will now respond.'),
    'Signal Junction': ('Story', 'Signal Officer\'s Note', 'Written by Signal Officer Mara Quill. If you are reading this, the junction locked again. Gold, then Blue, then Red. I wrote it everywhere so nobody else gets stuck in here.'),
    'Medical Bay': ('Station', 'Triage Console', 'The triage console that locks the bay. Its override reads: release on authorized scan. Your scan counts. The medical switch beside the exit will now open the door.'),
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
