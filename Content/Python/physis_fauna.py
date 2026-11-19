"""Living animals in the station, the Center, the Conclave and the Grove (author, 2026-11-17: organic enemies with
physical attacks in every level; Arche has its own). Species and text: physis_fauna_lore.py. Meshes and rigs:
Tools/arche_meshes/fauna.py and Tools/build_physis_fauna.py.

Run in the editor's Python (or headless: UnrealEditor-Cmd -run=pythonscript, see the project's tooling notes):

  import physis_fauna
  physis_fauna.import_all()            # the twelve meshes into /Game/Arche/Meshes, their rigs into /Game/Arche/Rigged
  physis_fauna.place('grove')          # 'ship', 'center', 'conclave' or 'grove': opens that level, adds the packs, saves

The animals are ADDED: no machine is moved or removed. place() first removes what an earlier run of it added (actors
labelled 'Scene Fauna ...'), so it can be run again. Each animal is a BP_TrainingDrone with Organic, Animal and Reach
set and its skinned mesh in Body, exactly as Arche's (physis_arche_scenario.Place.enemy and rig): it closes, calls,
draws back and strikes with its body, and never fires.

Where they go:
  the Center, the Conclave, the Grove   beside the loose machine packs that stand on open ground (RoomId 0): every
      few packs one gets a shoal about 12 m away, toward its nearest neighbour pack, so the animals hold the ground
      between the machines. Not within 30 m of a Still Point, nor 12 m of a person, relic, switch, socket or link node.
      What a shoal is follows how hard its ground is (the machines beside it, then the distance from where she
      arrives): the easiest half are four of the world's swarm animal, the next third its second animal with two of
      the swarm, the hardest fifth its third animal with its second.
  the station   none since 2026-11-18 (author: "Please remove some [of] the non robot enemies apart from the new
      creatures from the level", then of the rest: "Remove them too"). The station keeps its machines and the Pyre
      Lion (physis_monsters.STATION). Before that they joined the fight rooms, with the room's RoomId and box, so they
      fought only while she was in the room and the room's encounter counted them: Breach Mites in the Crew Ring and two
      wing rooms, a Coolant Bell in a wing room, a Coolant Bell and a Hull Limpet in the Reactor Gallery.
"""
import json
import math
import pathlib
import re

import unreal

import physis_gameplay_tools as game
import physis_fauna_lore as lore
from physis_lore import voice_name, image_name

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
MESHES, RIGGED = '/Game/Arche/Meshes', '/Game/Arche/Rigged'
KEEP = unreal.AttachmentRule.KEEP_WORLD
WORLDS = {'ship': ('/Game/Levels/L_BattleStation', '/Game/Audio/Voice'), 'center': ('/Game/Levels/L_CenterOfTheUniverse', '/Game/Center/Audio/Voice'),
          'conclave': ('/Game/Levels/L_Conclave', '/Game/Conclave/Audio/Voice'), 'grove': ('/Game/Levels/L_Grove', '/Game/Grove/Audio/Voice')}
SHOALS = {'center': 12, 'conclave': 10, 'grove': 6}        # how many packs of animals each open world gets
KEEP_FROM = (('BP_Checkpoint_C', 3000.0), ('BP_NPC_C', 1200.0), ('BP_Relic_C', 1200.0), ('BP_Switch_C', 1200.0), ('BP_AbilitySocket_C', 1200.0),
             ('BP_LinkNode_C', 1200.0), ('BP_Requirement_C', 1200.0), ('BP_Gate_C', 1200.0), ('BP_SettleBarrier_C', 900.0))
# The station: room id -> the tiers that join it (1 Breach Mite, 2 Coolant Bell, 3 Hull Limpet).
# No animals in the station any more (author, 2026-11-18: first the inner wing's, "Please remove some [of] the non
# robot enemies apart from the new creatures from the level", then the rest, "Remove them too"). It was
# {1: (1, 1), 105: (1, 1), 114: (1, 1), 108: (2,), 2: (2, 3)}.
STATION = {}


def wrap(text):
    import physis_grove_scenario as base
    return base.wrap(text)


def import_all():
    """The static meshes (Art/Meshes/Arche/SM_AE_<Name>.fbx) and the rigs (Art/Meshes/Arche/RiggedFauna) of every
    species, with Arche's importers, so they wear Arche's hide, horn, crystal and light materials."""
    import physis_arche_tools as arche
    report = {'meshes': {}, 'rigs': None}
    for rows in lore.FAUNA.values():
        for row in rows:
            report['meshes'][row[0]] = arche.import_meshes(row[0])
    report['rigs'] = arche.import_rigs(ROOT / 'Art/Meshes/Arche/RiggedFauna', RIGGED)
    return report


def ground_of(world):
    if world == 'center':
        import physis_center_tools as tools
        g = tools.Ground()
        return lambda x, y: max(g.at(x, y), g.water * 100.0)
    if world == 'conclave':
        import physis_conclave_scenario as scenario
        g = scenario.Ground()
        return lambda x, y: max(g.at(x, y), g.water * 100.0)
    if world == 'grove':
        import physis_grove_level as level
        g = level.Ground()
        return lambda x, y: max(g.at(x, y), g.water * 100.0)
    return None


class Placer:
    def __init__(self, world):
        self.world = world
        self.sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.drone = unreal.load_asset(game.BLUEPRINTS + '/BP_TrainingDrone').generated_class()
        self.scan = unreal.load_asset(game.BLUEPRINTS + '/BP_ScanTarget').generated_class()
        self.log = unreal.load_asset(game.BLUEPRINTS + '/BP_LogVoice').generated_class()
        self.rows, self.unrigged, self.folder = [], set(), 'Fauna'

    def animal(self, tier, label, place, room=0, extra=None, row=None, prefix='Scene Fauna '):
        """tier: the world's animal 1 to 3; or row, a (mesh, health, hover, kind, Animal, Reach, entry) of any animal."""
        mesh, health, hover, kind, number, reach, entry = (row or lore.FAUNA[self.world][tier - 1])[:7]
        actor = self.sub.spawn_actor_from_class(self.drone, unreal.Vector(*place))
        actor.set_actor_label(prefix + label)
        actor.set_folder_path(self.folder)
        for name, value in (('RoomId', room), ('Boss', False), ('Health', health), ('Static', False), ('EnemyKind', kind), ('Organic', True),
                            ('Animal', number), ('Reach', reach)) + tuple((extra or {}).items()):
            actor.set_editor_property(name, value)
        parts = [part for part in actor.get_components_by_class(unreal.StaticMeshComponent) if part.get_name().split('_GEN')[0] != 'Ward']
        shape = parts[0]
        shape.set_static_mesh(unreal.load_asset(MESHES + '/' + mesh))
        for slot in range(shape.get_num_materials()):
            shape.set_material(slot, None)
        for part in parts[1:]:
            part.set_visibility(False)
            part.set_collision_profile_name('NoCollision')
        stem = mesh[3:]
        skinned, swim, strike = (unreal.load_asset('%s/%s' % (RIGGED, name)) if unreal.EditorAssetLibrary.does_asset_exist('%s/%s' % (RIGGED, name)) else None
                                 for name in ('SK_' + stem, 'A_%s_Swim' % stem, 'A_%s_Strike' % stem))
        body = next((part for part in actor.get_components_by_class(unreal.SkeletalMeshComponent) if part.get_name().split('_GEN')[0] == 'Body'), None)
        if skinned and swim and strike and body:
            body.set_skeletal_mesh_asset(skinned)
            play = unreal.SingleAnimationPlayData()
            play.set_editor_property('anim_to_play', swim)
            play.set_editor_property('saved_looping', True)
            play.set_editor_property('saved_playing', True)
            body.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            body.set_editor_property('animation_data', play)
            actor.set_editor_property('Swim', swim)
            actor.set_editor_property('Strike', strike)
            shape.set_editor_property('visible', False)
        else:
            self.unrigged.add(stem)
        category, title, body_text = entry
        tag = self.sub.spawn_actor_from_class(self.scan, unreal.Vector(place[0], place[1], place[2] + 70))
        tag.set_actor_label(prefix + 'Tag ' + label)
        tag.set_folder_path(self.folder)
        for name, value in (('ScanCategory', category), ('ScanTitle', title), ('ScanText', wrap(body_text)), ('ScanImportant', True)):
            tag.set_editor_property(name, value)
        game.hide_scan(tag)
        tag.attach_to_actor(actor, 'None', KEEP, KEEP, KEEP, False)
        self.rows.append((label, title, [round(v) for v in place], room))
        return actor


def clear(sub):
    gone = 0
    for actor in sub.get_all_level_actors():
        if actor.get_actor_label().startswith('Scene Fauna'):
            sub.destroy_actor(actor)
            gone += 1
    return gone


def level_of(label):
    found = re.search(r'Enemy L(\d+)', label)
    return int(found.group(1)) if found else 1


def station(p, drones):
    import physis_aaa_tools as aaa
    by_room = {}
    for actor in drones:
        by_room.setdefault(actor.get_editor_property('RoomId'), []).append(actor)
    for room, tiers in sorted(STATION.items()):
        mates = by_room.get(room)
        box = aaa.station_room_box(room)
        if not mates or not box:
            continue
        x1, x2, y1, y2 = box
        spots = [m.get_actor_location() for m in mates]
        cx, cy = sum(s.x for s in spots) / len(spots), sum(s.y for s in spots) / len(spots)
        floor = min(s.z for s in spots) - 130.0
        for k, tier in enumerate(tiers):
            # Round the room's own drones, turned so they do not sit on one, and kept 1.5 m inside the walls.
            a = (k + .5) / len(tiers) * 2 * math.pi + .9
            x = min(max(cx + math.cos(a) * 420.0, x1 + 150.0), x2 - 150.0)
            y = min(max(cy + math.sin(a) * 420.0, y1 + 150.0), y2 - 150.0)
            hover = lore.FAUNA['ship'][tier - 1][2]
            p.animal(tier, 'Room %d %d' % (room, k), (x, y, floor + hover), room, aaa.room_box_props(room))


def open_ground(p, drones, others, ground, start):
    loose = [d for d in drones if d.get_editor_property('RoomId') == 0]
    # Packs: loose machines within 20 m of one another.
    packs = []
    for actor in sorted(loose, key=lambda a: a.get_actor_label()):
        spot = actor.get_actor_location()
        home = next((pack for pack in packs if any(math.hypot(spot.x - q.x, spot.y - q.y) < 2000.0 for q, _ in pack)), None)
        if home is None:
            home = []
            packs.append(home)
        home.append((spot, level_of(actor.get_actor_label())))
    sites = []
    for pack in packs:
        cx, cy = sum(s.x for s, _ in pack) / len(pack), sum(s.y for s, _ in pack) / len(pack)
        # Machines standing on something built (a deck, a roof, the temple) keep it to themselves.
        if min(s.z for s, _ in pack) - ground(cx, cy) > 700.0:
            continue
        sites.append((cx, cy, max(level for _, level in pack)))
    sites.sort(key=lambda s: (round(s[0] / 4000.0), s[1]))
    want = SHOALS[p.world]
    stride = max(1, len(sites) // want)
    placed, chosen = [], []
    for index, (cx, cy, level) in enumerate(sites):
        if len(placed) >= want or index % stride:
            continue
        near = sorted((math.hypot(ox - cx, oy - cy), ox, oy) for ox, oy, _ in sites if (ox, oy) != (cx, cy))
        toward = math.atan2(near[0][2] - cy, near[0][1] - cx) if near else 0.0
        reach = min(1400.0, max(900.0, near[0][0] / 2)) if near else 1200.0
        spot = None
        for turn in (0.0, math.pi / 2, -math.pi / 2, math.pi):
            x, y = cx + math.cos(toward + turn) * reach, cy + math.sin(toward + turn) * reach
            if all(math.hypot(x - ox, y - oy) >= need for ox, oy, need in others) and all(math.hypot(x - px, y - py) > 2500.0 for px, py in placed):
                if abs(ground(x, y) - ground(cx, cy)) < 500.0:   # the same shelf as the machines, not over a drop
                    spot = (x, y)
                    break
        if spot is None:
            continue
        placed.append(spot)
        chosen.append((spot, level))
    # What each shoal is: the easiest half (by the machines beside it, then by how far it is from where she arrives) is
    # the world's swarm animal, the next third its second animal with two of the swarm, the hardest its third and second.
    order = sorted(range(len(chosen)), key=lambda k: (chosen[k][1], math.hypot(chosen[k][0][0] - start[0], chosen[k][0][1] - start[1])))
    for rank, k in enumerate(order):
        share = (rank + .5) / len(order)
        tiers = (1, 1, 1, 1) if share <= .5 else (2, 1, 1) if share <= .8 else (3, 2)
        spot = chosen[k][0]
        for i, tier in enumerate(tiers):
            a = i / len(tiers) * 2 * math.pi + .6
            spread = 380.0 if tier == 1 else 520.0
            x, y = spot[0] + math.cos(a) * spread, spot[1] + math.sin(a) * spread
            p.animal(tier, 'Shoal %d %d' % (k + 1, i), (x, y, ground(x, y) + lore.FAUNA[p.world][tier - 1][2]))
    return len(sites), len(placed)


def voices(p, voice_folder, spot):
    """A BP_LogVoice per species, so its Logbook page speaks (the wavs: Tools/build_physis_divinity_voice.py)."""
    missing = []
    for category, title, body in lore.entries(p.world):
        path = voice_folder + '/' + voice_name(title)
        voice = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
        image = '/Game/UI/Log/' + image_name(title)
        actor = p.sub.spawn_actor_from_class(p.log, spot)
        actor.set_actor_label('Scene Fauna Voice ' + title)
        actor.set_folder_path(p.folder)
        actor.set_editor_property('Title', title)
        if voice:
            actor.set_editor_property('Voice', voice)
        else:
            missing.append(voice_name(title))
        if unreal.EditorAssetLibrary.does_asset_exist(image):
            actor.set_editor_property('Image', unreal.load_asset(image))
    return missing


def place(world, save=True):
    level, voice_folder = WORLDS[world]
    editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorLevelLibrary.get_editor_world().get_path_name().split('.')[0] != level:
        editor.load_level(level)
    p = Placer(world)
    removed = clear(p.sub)
    drones, others, voice_spot, start = [], [], unreal.Vector(0.0, 0.0, -50000.0), (0.0, 0.0)
    needs = dict(KEEP_FROM)
    for actor in p.sub.get_all_level_actors():
        name = actor.get_class().get_name()
        spot = actor.get_actor_location()
        if name == 'BP_TrainingDrone_C':
            if not actor.get_editor_property('Static') and not actor.get_editor_property('Boss'):
                drones.append(actor)
        elif name in needs:
            others.append((spot.x, spot.y, needs[name]))
        elif name == 'BP_LogVoice_C':
            voice_spot = spot
        elif name == 'PlayerStart':
            start = (spot.x, spot.y)
    if drones:
        folder = str(drones[0].get_folder_path())
        p.folder = (folder.rsplit('/', 1)[0] + '/Fauna') if '/' in folder else 'Fauna'
    report = {'world': world, 'removed': removed, 'machines': len(drones)}
    if world == 'ship':
        station(p, drones)
    else:
        report['open_packs'], report['shoals'] = open_ground(p, drones, others, ground_of(world), start)
    # the station's three species live nowhere now, so their Logbook voices are not placed either
    report['voices_missing'] = [] if world == 'ship' and not STATION else voices(p, voice_folder, voice_spot)
    report['animals'] = len(p.rows)
    report['by_species'] = {}
    for _, title, _, _ in p.rows:
        report['by_species'][title] = report['by_species'].get(title, 0) + 1
    report['unrigged'] = sorted(p.unrigged)
    report['rows'] = p.rows
    report['saved'] = editor.save_current_level() if save else False
    (ROOT / 'Saved/Fauna').mkdir(parents=True, exist_ok=True)
    (ROOT / ('Saved/Fauna/placed_%s.json' % world)).write_text(json.dumps(report, indent=1, default=str))
    return report
