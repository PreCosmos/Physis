import re, pathlib
p = pathlib.Path('physis_lore.py')
s = p.read_text()
R = {
# Station objects: clues, not walkthroughs.
"A power conduit overloaded by a Divinity surge. The engineers logged it as a fault. It is not a fault: the current is reacting to you. Scanning it traces the live line to the coolant valve on the far side of the room. Once it is traced, the valve will answer you.":
"A power conduit overloaded by a Divinity surge. The engineers logged it as a fault. It is not a fault: the current is reacting to you. Now that you have traced it, follow the line. Something on the far side of the room is waiting for this signal.",
"Sealed by Divinity, not by any lock. No human key will open this, and neither can you yet. You can feel it push back. Remember this door: you will return when you have learned more.":
"Sealed by Divinity, not by any lock. No human key will open this, and neither can you yet. You can feel it push back. Perhaps you will return when you have learned more.",
"Recorded by Quartermaster Lena Hart. Day four thousand and fifteen. Eleven years at the Meridian Front and they have never told us why. If the Armory locks down, the override is Red, then Gold, then Blue. Use the three panels on the Armory\\'s left wall, in that order. A wrong press resets the lockdown.":
"Recorded by Quartermaster Lena Hart. Day four thousand and fifteen. Eleven years at the Meridian Front and they have never told us why. If the Armory ever locks down, remember the override: Red, then Gold, then Blue.",
"The station\\'s heart. Divinity here is twisted into a shape that hurts to perceive. Humanity learned to burn it long before it learned what it was. To vent the core you need all three reactor fuses, then the Divinity node in this gallery to raise the platforms, then the vent panel at the top.":
"The station\\'s heart. Divinity here is twisted into a shape that hurts to perceive. Humanity learned to burn it long before it learned what it was. The vent above is starved: three fuse sockets sit empty. The gallery\\'s node still hums beneath the dead platforms.",
# Rooms: hints only.
"Where you entered the station. The east door has no power. Climb the crates on the right to reach a reactor fuse, then cross to the breaker on its island past the live floor. Use the breaker with Interact to open the door. Do not step on the plasma.":
"Where you entered the station. The east door is dead, and so is the breaker that feeds it. Something is missing from it. The wreckage here is tall enough to climb. Scan the room for hints.",
"Three strips of plasma cross this room. They heat and cool in turn: dark means safe, glowing means burning. Scan the live conduit on the right wall, then time your run to the coolant valve on the far left. Spending twenty Divinity at the node by the door calms the plasma for good.":
"Plasma runs hot and cold across this room. The coolant system is locked out, and something in here is crackling with current. Scan the room for hints.",
"Two AL drones hold this ring. Destroy them both to open the Armory. A reactor fuse rests on the shelf beside the crew terminal. Scan the terminal for the Armory override.":
"The crew\\'s living ring, overrun by First One units. The way onward stays sealed while they hold it. The crew left their records behind. Scan the room for hints.",
"The Armory is in lockdown. Press the three wall panels in the order from the crew log: Red, then Gold, then Blue. A wrong press resets them. Your sidearm is drawn with Tab, or up on the directional pad.":
"The Armory is in lockdown. Three coloured panels wait on the wall, and only one order will lift it. Someone in the Crew Ring would have known it.",
"The First Ones flooded this corridor with plasma. Jump across the moving platforms; hold the jump button longer to jump higher. The last reactor fuse waits on a side platform. A Divinity node at the entrance can calm the flood for thirty Divinity.":
"The First Ones flooded this corridor with plasma. Moving platforms still drift above it, and something glints on a side ledge. Divinity runs close to the surface here. Scan the room for hints.",
"Three drones guard the gallery. Destroy them, then spend twenty Divinity at the node to raise the platforms around the core. Climb to the top and use the vent with all three fuses to open the bridge.":
"The gallery around the reactor core. Its guards will not let you work in peace. The platforms are lowered and the vent sits far above. Scan the core for hints.",
"The Mecha Breacher waits here. Its armor turns every attack except one: the glowing red eye on its front. Stay in front of it and strike the eye with your blade, or draw your sidearm with Tab and shoot it. Dodge its triple bolts between attacks. Thirty hits bring it down.":
"The approach to the Fleet Bridge. Something enormous blocks the way. Scan it before you fight.",
"Both fleets fill the viewport. Walk to the terminal at the far end and use it. What happens there is not something you choose.":
"Both fleets fill the viewport. The deck ends at a single terminal. What happens there is not something you choose.",
}
for old, new in R.items():
    assert old in s, old[:60]
    s = s.replace(old, new)
s = s.replace("A shielded fuse from the emergency grid. Walk over it to collect it. The reactor cannot vent without all three: one on the Breach Deck crates, one in the Crew Ring, one in the Boarding Spine.",
              "A shielded fuse from the emergency grid. Walk over it to collect it; the HUD counts how many you carry. A breaker uses one, and the reactor vent needs all three. They are scattered across the station.")
items = """    ('Items', 'Health Capsule', 'A sealed medical capsule, white with a green cross of light. Walk over it to restore part of your health. Drones sometimes guard them, and some rooms keep a few by the entrance.', (2200, -350, 150)),
    ('Items', 'Divinity Crystal', 'A shard of Divinity grown solid. Walk over it to add to the Divinity you carry, shown in the HUD. Spend Divinity at nodes to calm plasma or wake machines, or on a Divinity Shot with the sidearm. Destroyed drones release it too.', (1200, -350, 150)),
    ('Items', 'Ammo Cell', 'A charge cell for the marine sidearm. Walk over it to refill your reserve, shown at the lower right. Reload with R when the magazine runs dry. The sidearm is drawn with Tab and fires with Left Mouse.', (6700, 350, 150)),
"""
s = s.replace("    ('Station', 'Reactor Plasma',", items + "    ('Station', 'Reactor Plasma',")
p.write_text(s)
print('ok')
