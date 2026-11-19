"""The elemental monsters in every level (author, 2026-11-17). Species and text: physis_monster_lore.py; models:
physis_monster_models.py (import_all, import_fx first); the elements' rules: Tools/blueprint_logic/elements.py.
Each monster wears a cloud of its element's motes (physis_monster_models.aura).

  import physis_monsters
  physis_monsters.import_all()        # meshes into /Game/Arche/Meshes, rigs into /Game/Arche/Rigged (GUI editor only)
  physis_monsters.place('grove')      # 'ship', 'center', 'conclave', 'grove' or 'arche': opens the level, adds, saves

Monsters are ADDED, like the animals of physis_fauna.py, whose placer this uses: a BP_TrainingDrone with Organic, Animal
and Reach, and now Element. place() first removes what an earlier run added ('Scene Monster ...').

Where: each world has the elements of physis_monster_lore.WORLDS, taken in turn.
  the open worlds   exactly one of every species, each beside a loose machine pack of its own, 25 m from any
      animal or monster already placed, 30 m from a Still Point, 12 m from a person, relic or switch where the level
      has the room (open_ground relaxes these in steps until every species has a place).
  the station       two Gale Motes in wing room 2, a Storm Ray in wing room 11, a Pyre Stalker in wing room 8, with the
      room's RoomId and box, so the room's encounter counts them.
Each species has one BP_LogVoice in every level it lives in, so its Logbook page speaks.
"""
import json
import math
import pathlib

import unreal

import physis_fauna as fauna
import physis_gameplay_tools as game
import physis_monster_lore as lore
from physis_lore import voice_name, image_name

ROOT = fauna.ROOT
LEVELS = dict(fauna.WORLDS, arche=('/Game/Levels/L_Arche', '/Game/Arche/Audio/Voice'))
VOICES = '/Game/Audio/Voice/Monsters'
STATION = {108: ('PyreLion',)}   # the station has one of them in all: the lion, in wing room 8


def import_all():
    import physis_arche_tools as arche
    report = {'meshes': {}}
    for row in lore.MONSTERS.values():
        report['meshes'][row[0]] = arche.import_meshes(row[0])
    report['rigs'] = arche.import_rigs(ROOT / 'Art/Meshes/Arche/RiggedMonsters', fauna.RIGGED)
    return report


def import_voices():
    if not unreal.EditorAssetLibrary.does_directory_exist(VOICES):
        unreal.EditorAssetLibrary.make_directory(VOICES)
    out = {}
    for _, title, _ in lore.entries():
        name = voice_name(title)
        game.import_file(str(ROOT / 'Art/Audio/Voice/Monsters' / (name + '.wav')), VOICES)
        sound = unreal.load_asset(VOICES + '/' + name)
        out[name] = round(sound.get_editor_property('duration'), 1) if sound else None
    return out


def ground_of(world):
    if world == 'arche':
        import physis_arche_level as level
        g = level.Ground()
        return lambda x, y: max(g.at(x, y), g.water * 100.0)
    return fauna.ground_of(world)


CLEAR_REACH = 160.0   # cm: the game's step test is 120 (BP_TrainingDrone DroneThink); a little more for margin


def clearance(ignore, context):
    """The test of a monster's spot: from its middle a ray must reach CLEAR_REACH cm in each of eight directions.
    In the game a monster steps only where a 120 cm ray from its middle is free, so one placed inside a pillar, a tree
    or a rock can never move. The station's lion (author, 2026-11-18: "I just played the whole Battle Station
    sequence. There was no Pyre Lion") stood with its middle inside a pillar: the station's clean-up took it for a
    machine sunk in the floor and destroyed it as soon as she came near. `ignore`: actors that move or do not count
    (the machines, scan tags). GUI editor only: a headless editor's traces find nothing."""
    def free(x, y, z):
        start = unreal.Vector(x, y, z)
        for k in range(8):
            a = k * math.pi / 4
            end = unreal.Vector(x + math.cos(a) * CLEAR_REACH, y + math.sin(a) * CLEAR_REACH, z)
            if unreal.SystemLibrary.line_trace_single(context, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore, unreal.DrawDebugTrace.NONE, False):
                return False
        return True
    return free


def monster(p, element, label, place, room=0, extra=None):
    import physis_monster_models as models
    row = lore.MONSTERS[element]   # `element` is the species' name
    # Sturdy: the station's clean-up of jammed machines leaves it alone (Tools/blueprint_logic/sturdy.py)
    actor = p.animal(0, label, place, room, dict(extra or {}, Element=row[8], Spits=True, Sturdy=True), row=row, prefix='Scene Monster ')
    models.aura(p.sub, actor, row[8], row[9], p.folder, row[10] if len(row) > 10 else None)
    return actor


def station(p, drones):
    import physis_aaa_tools as aaa
    by_room = {}
    for actor in drones:
        by_room.setdefault(actor.get_editor_property('RoomId'), []).append(actor)
    for room, elements in sorted(STATION.items()):
        mates, box = by_room.get(room), aaa.station_room_box(room)
        if not mates or not box:
            continue
        x1, x2, y1, y2 = box
        spots = [m.get_actor_location() for m in mates]
        cx, cy = sum(s.x for s in spots) / len(spots), sum(s.y for s in spots) / len(spots)
        floor = min(s.z for s in spots) - 130.0
        for k, element in enumerate(elements):
            z = floor + min(lore.MONSTERS[element][2], 190)
            base = (k + .5) / len(elements) * 2 * math.pi + 2.4
            # round the room's machines first, then anywhere on the room's floor, a metre apart, middle first
            rings = [(min(max(cx + math.cos(base + j * math.pi / 8) * r, x1 + 180.0), x2 - 180.0), min(max(cy + math.sin(base + j * math.pi / 8) * r, y1 + 180.0), y2 - 180.0))
                     for r in (480.0, 360.0, 600.0, 240.0, 720.0) for j in range(16)]
            grid = sorted(((x, y) for x in range(int(x1) + 200, int(x2) - 199, 100) for y in range(int(y1) + 200, int(y2) - 199, 100)),
                          key=lambda q: math.hypot(q[0] - (x1 + x2) / 2, q[1] - (y1 + y2) / 2))
            spot = next(((x, y) for x, y in rings + grid if all(math.hypot(x - s.x, y - s.y) >= 200.0 for s in spots) and p.free(x, y, z)), None)
            if spot is None:
                p.unplaced.append('%s in room %d' % (element, room))
                continue
            monster(p, element, 'Room %d %d' % (room, k), (spot[0], spot[1], z), room, aaa.room_box_props(room))


def open_ground(p, drones, others, taken, ground, world):
    loose = [d for d in drones if d.get_editor_property('RoomId') == 0]
    packs = []
    for actor in sorted(loose, key=lambda a: a.get_actor_label()):
        spot = actor.get_actor_location()
        home = next((pack for pack in packs if any(math.hypot(spot.x - q.x, spot.y - q.y) < 2000.0 for q in pack)), None)
        if home is None:
            home = []
            packs.append(home)
        home.append(spot)
    sites = []
    for pack in packs:
        cx, cy = sum(s.x for s in pack) / len(pack), sum(s.y for s in pack) / len(pack)
        if min(s.z for s in pack) - ground(cx, cy) > 700.0:
            continue
        sites.append((cx, cy))
    sites.sort(key=lambda s: (round(s[1] / 4000.0), s[0]))    # another order than the animals', so other packs come up
    # The author, 2026-11-18: "The Battle Station needs one of these enemies in it. The rest of the levels must have
    # one of each in them." So an open world gets exactly one of every species of lore.WORLDS[world], each at a pack
    # of its own. The first pass spreads them over the level (every stride-th pack, clear of everything); if that
    # leaves a species without a place, later passes take any pack left, then look nearer and farther from it and
    # accept less room, until each species stands somewhere.
    elements = lore.WORLDS[world]
    want = len(elements)
    stride = max(1, len(sites) // want)
    placed, used = [], set()
    for spread_out, rings, apart, room in ((True, (1300.0,), 2500.0, 1.0), (False, (1300.0,), 2500.0, 1.0), (False, (900.0, 1800.0, 2600.0), 1800.0, 1.0),
                                           (False, (900.0, 1800.0, 2600.0, 3600.0), 1200.0, 0.6), (False, (700.0, 1500.0, 2600.0, 3600.0, 5000.0), 900.0, 0.35)):
        for index, (cx, cy) in enumerate(sites):
            if len(placed) >= want:
                break
            if index in used or (spread_out and index % stride != stride // 2):
                continue
            element = elements[len(placed) % len(elements)]
            hover = lore.MONSTERS[element][2] + 20.0   # DroneHover keeps its lowest point 20 cm off the ground
            spot = None
            for ring in rings:
                for k in range(8):
                    a = k / 8 * 2 * math.pi + .4
                    x, y = cx + math.cos(a) * ring, cy + math.sin(a) * ring
                    if (all(math.hypot(x - ox, y - oy) >= need * room for ox, oy, need in others) and all(math.hypot(x - px, y - py) > apart for px, py in placed + taken)
                            and abs(ground(x, y) - ground(cx, cy)) < 500.0 and p.free(x, y, ground(x, y) + hover)):
                        spot = (x, y)
                        break
                if spot:
                    break
            if spot is None:
                continue
            used.add(index)
            placed.append(spot)
            monster(p, element, 'Lair %d 0' % len(placed), (spot[0], spot[1], ground(spot[0], spot[1]) + lore.MONSTERS[element][2]))
    return len(sites), len(placed)


def place(world, save=True):
    level, _ = LEVELS[world]
    editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorLevelLibrary.get_editor_world().get_path_name().split('.')[0] != level:
        editor.load_level(level)
    p = fauna.Placer(world)
    removed = 0
    for actor in p.sub.get_all_level_actors():
        if actor.get_actor_label().startswith('Scene Monster'):
            p.sub.destroy_actor(actor)
            removed += 1
    drones, others, taken, voice_spot = [], [], [], unreal.Vector(0.0, 0.0, -50000.0)
    needs = dict(fauna.KEEP_FROM)
    for actor in p.sub.get_all_level_actors():
        name, spot, label = actor.get_class().get_name(), actor.get_actor_location(), actor.get_actor_label()
        if name == 'BP_TrainingDrone_C':
            if label.startswith('Scene Fauna'):
                taken.append((spot.x, spot.y))
            elif not actor.get_editor_property('Static') and not actor.get_editor_property('Boss'):
                drones.append(actor)
        elif name in needs:
            others.append((spot.x, spot.y, needs[name]))
        elif name == 'BP_LogVoice_C':
            voice_spot = spot
    ignore = [a for a in p.sub.get_all_level_actors() if a.get_class().get_name() in ('BP_TrainingDrone_C', 'BP_ScanTarget_C', 'BP_Pickup_C')]
    p.free = clearance(ignore, ignore[0] if ignore else None)
    p.unplaced = []
    if drones:
        folder = str(drones[0].get_folder_path())
        p.folder = (folder.rsplit('/', 1)[0] + '/Monsters') if '/' in folder else 'Monsters'
    report = {'world': world, 'removed': removed, 'machines': len(drones)}
    if world == 'ship':
        station(p, drones)
    else:
        report['open_packs'], report['lairs'] = open_ground(p, drones, others, taken, ground_of(world), world)
    missing = []
    for element in lore.WORLDS[world]:
        category, title, body = lore.MONSTERS[element][6]
        actor = p.sub.spawn_actor_from_class(p.log, voice_spot)
        actor.set_actor_label('Scene Monster Voice ' + title)
        actor.set_folder_path(p.folder)
        actor.set_editor_property('Title', title)
        path = VOICES + '/' + voice_name(title)
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            actor.set_editor_property('Voice', unreal.load_asset(path))
        else:
            missing.append(voice_name(title))
        image = '/Game/UI/Log/' + image_name(title)
        if unreal.EditorAssetLibrary.does_asset_exist(image):
            actor.set_editor_property('Image', unreal.load_asset(image))
    report.update(voices_missing=missing, monsters=len(p.rows), unrigged=sorted(p.unrigged), by_species={}, unplaced=p.unplaced)
    # every monster placed, tested again where it now stands (its own body and clouds aside)
    mine = [a for a in p.sub.get_all_level_actors() if a.get_actor_label().startswith('Scene Monster') and a.get_class().get_name() == 'BP_TrainingDrone_C']
    check = clearance(ignore + [k for a in mine for k in [a] + list(a.get_attached_actors())], ignore[0] if ignore else None)
    report['not_free'] = [a.get_actor_label() for a in mine if not check(a.get_actor_location().x, a.get_actor_location().y, a.get_actor_location().z)]
    for _, title, _, _ in p.rows:
        report['by_species'][title] = report['by_species'].get(title, 0) + 1
    report['rows'] = p.rows
    report['saved'] = editor.save_current_level() if save else False
    (ROOT / 'Saved/Fauna').mkdir(parents=True, exist_ok=True)
    (ROOT / ('Saved/Fauna/monsters_%s.json' % world)).write_text(json.dumps(report, indent=1, default=str))
    return report
