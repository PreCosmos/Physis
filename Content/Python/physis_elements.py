"""An element for every enemy already in the game (author, 2026-11-17: "give elemental types and attacks to the already
existing enemies"). The rules of the elements: Tools/blueprint_logic/elements.py.

  import physis_elements
  physis_elements.apply('conclave')     # 'ship', 'center', 'conclave', 'grove' or 'arche': opens the level, sets, saves

apply() goes through every moving BP_TrainingDrone of the level, finds its kind by the title of its Logbook tag, and
sets Element and Spits on it. It also adds one sentence naming the element to the tag's scan text (once). Nothing is
moved, added or removed. Run it again after a level's scenario is re-placed: the scenario scripts do not know the
elements, and a re-placed enemy has none until this runs.

ELEMENTS: Logbook title -> (element, spits). 1 fire, 2 ice, 3 thunder, 4 wind, 5 dark, 6 light. Machines always fire
their bolts, now of their element. A living animal looses a bolt only with spits True; the small swarm animals carry
their element on the bite alone. All of it Proposed, for the author to change.
"""
import json
import pathlib

import unreal

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
LEVELS = {'ship': 'L_BattleStation', 'center': 'L_CenterOfTheUniverse', 'conclave': 'L_Conclave', 'grove': 'L_Grove', 'arche': 'L_Arche'}
FIRE, ICE, THUNDER, WIND, DARK, LIGHT = 1, 2, 3, 4, 5, 6
NAMES = {1: 'fire', 2: 'ice', 3: 'thunder', 4: 'wind', 5: 'dark', 6: 'light'}
NOTES = {1: 'Element: fire. A hit sets you burning for three seconds.', 2: 'Element: ice. A hit slows your legs for a few seconds.',
         3: 'Element: thunder. A hit locks your muscles for half a second.', 4: 'Element: wind. A hit throws you back.',
         5: 'Element: dark. A hit takes fifteen Divinity.', 6: 'Element: light. Its bolt cannot be blocked or parried, only avoided.'}
ELEMENTS = {
    # Meridian Station
    'AL Drone': (THUNDER, True), 'Mecha Breacher': (FIRE, True), 'Breach Mite': (WIND, False), 'Coolant Bell': (ICE, True), 'Hull Limpet': (DARK, True),
    # the Center
    'Shardling': (FIRE, True), 'Shardling Matriarch': (THUNDER, True), 'Ember Skitter': (FIRE, True), 'Bastion': (ICE, True), 'Aegis Shard': (ICE, True),
    'Onyx Ward': (DARK, True), 'Prism Wraith': (LIGHT, True), 'Temple Warden': (WIND, True), 'Hollow Sentinel': (DARK, True),
    'Lantern Angel': (LIGHT, False), 'Glass Ray': (ICE, True), 'Marsh Stalker': (DARK, True),
    # the Conclave
    'AL Mite': (THUNDER, True), 'AL Lancer': (FIRE, True), 'AL Bulwark': (ICE, True), 'Echo Hunter': (LIGHT, True), 'AL Reaver': (DARK, True),
    'AL Siegeframe': (FIRE, True), 'AL Shepherd': (THUNDER, True), 'Goldgrass Mote': (LIGHT, False), 'Reservoir Bell': (ICE, True), 'Terrace Ray': (WIND, True),
    # the Grove
    'Hedge Wasp': (WIND, True), 'Hedge Lancet': (LIGHT, True), 'Hedge Burl': (ICE, True), 'Hedge Palisade': (DARK, True), 'Hedge Thresher': (WIND, True),
    'Hedge Harrow': (FIRE, True), 'The Warden': (THUNDER, True), 'Blightfly': (DARK, False), 'Burlback': (FIRE, True), 'Canopy Stalker': (WIND, True),
    # Arche
    'Ward Mite': (THUNDER, True), 'Ward Lancer': (LIGHT, True), 'Ward Bulwark': (ICE, True), 'Ward Hunter': (WIND, True), 'Ward Reaver': (DARK, True),
    'Ward Siegeframe': (FIRE, True), 'The Sunderer': (LIGHT, True), 'Drift Mote': (WIND, False), 'Bell Medusa': (THUNDER, True), 'Shellback': (ICE, True),
    'Sky Ray': (WIND, True), 'Crest Stalker': (DARK, True), 'Leviathan': (LIGHT, True),
}


def apply(world, save=True):
    import physis_grove_scenario as base
    editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorLevelLibrary.get_editor_world().get_name() != LEVELS[world]:
        editor.load_level('/Game/Levels/' + LEVELS[world])
    done, unknown, noted = {}, {}, 0
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if actor.get_class().get_name() != 'BP_TrainingDrone_C' or actor.get_editor_property('Static'):
            continue
        tags = [k for k in actor.get_attached_actors() if k.get_class().get_name() == 'BP_ScanTarget_C']
        title = str(tags[0].get_editor_property('ScanTitle')) if tags else ''
        if title not in ELEMENTS:
            unknown[title or actor.get_actor_label()] = unknown.get(title or actor.get_actor_label(), 0) + 1
            continue
        element, spits = ELEMENTS[title]
        actor.set_editor_property('Element', element)
        actor.set_editor_property('Spits', spits)
        done[title] = done.get(title, 0) + 1
        for tag in tags:
            text = str(tag.get_editor_property('ScanText'))
            if 'Element: ' not in text.replace('~', ' '):
                tag.set_editor_property('ScanText', base.wrap(text.replace('~', ' ').rstrip() + ' ' + NOTES[element]))
                noted += 1
    report = {'world': world, 'set': done, 'by_element': {}, 'unknown': unknown, 'scan_notes_added': noted}
    for title, count in done.items():
        name = NAMES[ELEMENTS[title][0]]
        report['by_element'][name] = report['by_element'].get(name, 0) + count
    report['saved'] = editor.save_current_level() if save else False
    (ROOT / 'Saved/Fauna').mkdir(parents=True, exist_ok=True)
    (ROOT / ('Saved/Fauna/elements_%s.json' % world)).write_text(json.dumps(report, indent=1))
    return report
