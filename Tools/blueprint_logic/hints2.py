import pathlib, re
p = pathlib.Path('physis_lore.py')
s = p.read_text()
G = {
'Cargo Lift Hall': 'The floor gave way to the reactor plasma below. The cargo lifts still run on their old schedule. Watch them before you leap.',
'Mess Hall': 'Overturned tables and the hum of hostile drones. The far door will not open while they hunt here.',
'Comms Relay': 'The door ahead is slaved to the comms relay, and the relay is silent. Something in this room is at fault. Scan the room for hints.',
'Coolant Vats': 'The coolant vats have ruptured. Plasma breathes across the floor in a slow rhythm. Patience is a kind of path.',
'Barracks': 'Bunks, lockers and First One units. A band of plasma splits the room and does not stay hot for long. The exit stays sealed while the drones remain.',
'Signal Junction': 'Three signal panels lock this junction, and someone was tired of getting stuck in here. Scan the room for hints.',
'Starboard Gantry': 'A broken gantry above a pool of plasma. What is left of the walkway is uneven. Look up before you jump.',
'Drone Hangar': 'The hangar racks are still launching. Two support columns stand in the middle of the floor. The door onward stays sealed while the hangar is defended.',
'Pressure Locks': "Two pressure locks hold the exit, and the station\\'s pressure logic was built for safety, not speed. The lock beside the door may not be the place to start. Scan the room for hints.",
'Fuel Line Maze': 'A burst fuel line flooded the far side with plasma. The door release is somewhere beyond it, out of reach of any blade. Scan the room for hints.',
'Armory Annex': 'The annex guards keep to the high ground. The marines left supplies by the entrance for exactly this kind of fight.',
'Hydroponics': 'Plasma flooded the grow beds and the whole floor burns. Divinity runs close to the surface here. Scan the room for hints.',
'Ventilation Shaft': 'Lifts rise and fall across a plasma pit, each on its own rhythm. Timing is everything.',
'Officer Quarters': "The officers\\' deck, with a raised dais in the middle. Its guards will not let you pass. Someone left medical supplies near the door.",
'Medical Bay': "The bay door is locked to the medical systems. Mercy Seven\\'s colleagues would have known how to release it. Scan the room for hints.",
'Command Spur': "The inner ring\\'s command post. The commander left a final order here. Scan the room for hints.",
}
for name, text in G.items():
    pat = re.compile(r"\('" + re.escape(name.replace("'", "\\'")) + r"', '(\w+)', '(?:[^'\\]|\\.)*'\)")
    s, n = pat.subn(lambda m: "('%s', '%s', '%s')" % (name.replace("'", "\\'"), m.group(1), text), s)
    assert n == 1, name
W = {
"The relay node that drives the door. Its fault is a burned Divinity coupling: scanning it reroutes the signal. The relay switch beside the exit will now respond.":
"The relay node that drives the door. Its fault is a burned Divinity coupling. Your scan has rerouted the signal around it. Somewhere near the exit, a switch has woken.",
"The triage console that locks the bay. Its override reads: release on authorized scan. Your scan counts. The medical switch beside the exit will now open the door.":
"The triage console that locks the bay. Its override reads: release on authorized scan. Your scan counts. The medical switch is awake now, kept high and out of reach of patients.",
}
for old, new in W.items():
    assert old in s, old[:50]
    s = s.replace(old, new)
p.write_text(s)
print('ok')
