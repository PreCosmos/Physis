"""A lot of goldgrass (BP_CutGrass, the grass her blade cuts) in the Center, the Conclave, the Grove and Arche.

Author, 2026-11-17: "put A LOT of Goldgrass in all the levels apart from the Battle Station. Also reduce the
probabilities the goldgrass drops an item by 50%". The drop chance is in BP_CutGrass.GrassCut, edited in the editor
on the same day: a cut tuft now drops a pickup one time in four (it was one in two), and one time in two while she is
short of Divinity or health (it was always); a tuft with its own Chance set drops at half of it. The Blueprint's
empty Tick was also switched off, since a level now holds over a thousand tufts.

  import physis_goldgrass
  physis_goldgrass.place('grove')     # 'center', 'conclave', 'grove' or 'arche': opens the level, adds the fields, saves

The fields are ADDED to whatever grass a level already has (the Center's 310 tufts and the Conclave's 169 stay). place()
first removes what an earlier run added (actors labelled 'Scene Goldfield ...'), so it can be run again.

Where: beside the roads and paths of each world's plan, a field every FIELD_EVERY metres on alternating sides, 4 to 13 m
off the road's edge, so the grass lines the ways she walks without growing on them. A field is TUFTS tufts scattered
over a 5 m circle. A field is dropped if its ground is wet, steep, on the rim, in a gorge or chasm, or within 8 m of a
gameplay actor (a switch, a person, a relic, a Still Point ...); a tuft is dropped if it falls inside the box of a
static mesh actor smaller than 40 m (a house, a wall, a rock), so none grows through a floor.

How it looks: the Center's fields wear the Center's own tuft (SM_CT_CutGrass, its Gleamgrass) as its other patches do;
the Conclave, the Grove and Arche wear the Conclave's goldgrass (the Blueprint's own wheat in gold) at the Conclave's
size. No shadow and no collision, as the Center's. Every fourth field in the Center and the Conclave carries that
world's Logbook tag (Gleamgrass, Goldgrass); the Grove and Arche have no grass entry of their own, so theirs carry none.
"""
import json
import math
import pathlib
import random

import unreal

import physis_gameplay_tools as game

ROOT = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
LEVELS = {'center': '/Game/Levels/L_CenterOfTheUniverse', 'conclave': '/Game/Levels/L_Conclave', 'grove': '/Game/Levels/L_Grove', 'arche': '/Game/Levels/L_Arche'}
FIELD_EVERY = {'center': 22.0, 'conclave': 20.0, 'grove': 16.0, 'arche': 16.0}   # metres of road between fields
TUFTS = 14
GRASS_SIZE = (2.4, 2.4, 1.5)   # the Conclave's goldgrass (physis_conclave_scenario.GRASS_SIZE)
M = 100.0


class World:
    """One level's ground and plan: at(x, y) cm, roads as (ax, ay, bx, by, half width) metres, open(x, y) metres."""

    def __init__(self, name):
        self.name = name
        if name == 'center':
            import physis_center_tools as tools
            import physis_center_scenario as scenario
            g = tools.Ground()
            self.at, self.water = g.at, g.water * M
            self.roads = [(a[0], a[1], b[0], b[1], 3.0) for line in scenario.road_lines_cache() for a, b in zip(line, line[1:])]
            temple, wake = scenario.TEMPLE, scenario.WAKE
            self.open = lambda x, y: math.hypot(x * M - temple[0], y * M - temple[1]) > 18000 and math.hypot(x * M - wake[0], y * M - wake[1]) > 1500
        elif name == 'conclave':
            import physis_conclave_scenario as scenario
            import physis_conclave_plan as plan
            g = scenario.Ground()
            self.at, self.water = g.at, g.water * M
            self.roads = [tuple(s[:5]) for s in plan.road_segments()]
            self.open = lambda x, y: not plan.in_lake(x, y, 2.0)
        else:
            level = __import__('physis_grove_level' if name == 'grove' else 'physis_arche_level')
            plan = __import__('physis_grove_plan' if name == 'grove' else 'physis_arche_plan')
            g = level.Ground()
            self.at, self.water = g.at, g.water * M
            self.roads = [tuple(s[:5]) for s in plan.path_segments()]
            if name == 'grove':
                self.open = lambda x, y: plan.rim(x, y) < .85 and not (plan.in_lake(x, y, 2.0) or plan.in_gully(x, y, 3.0) or plan.in_rift(x, y, 3.0))
            else:
                self.open = lambda x, y: plan.rim(x, y) < .85 and not (plan.in_water(x, y, 2.0) or plan.in_chasm(x, y, 3.0) or plan.on_riser(x, y, 3.0))

    def road_gap(self, x, y):
        """Metres from (x, y) to the nearest road's edge."""
        best = 1e9
        for ax, ay, bx, by, half in self.roads:
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(dx * dx + dy * dy, 1e-6)))
            best = min(best, math.hypot(x - (ax + dx * t), y - (ay + dy * t)) - half)
        return best

    def level_ground(self, x, y):
        """A field's ground (cm) if it is dry and fairly level there, else None."""
        here = self.at(x * M, y * M)
        ring = [self.at(x * M + math.cos(k / 4 * math.pi) * 400, y * M + math.sin(k / 4 * math.pi) * 400) for k in range(8)]
        if min(ring + [here]) < self.water + 40 or max(ring) - min(ring) > 160:
            return None
        return here


def clear(sub):
    gone = 0
    for actor in sub.get_all_level_actors():
        if actor.get_actor_label().startswith('Scene Goldfield'):
            sub.destroy_actor(actor)
            gone += 1
    return gone


def place(name, save=True):
    editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorLevelLibrary.get_editor_world().get_path_name().split('.')[0] != LEVELS[name]:
        editor.load_level(LEVELS[name])
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    removed = clear(sub)
    world = World(name)
    grass = unreal.load_asset(game.BLUEPRINTS + '/BP_CutGrass').generated_class()
    scan = unreal.load_asset(game.BLUEPRINTS + '/BP_ScanTarget').generated_class()
    keep, boxes, before, folder = [], {}, 0, 'Goldfields'
    for actor in sub.get_all_level_actors():
        kind = actor.get_class().get_name()
        if kind == 'BP_CutGrass_C':
            before += 1
            folder = str(actor.get_folder_path()).rsplit('/', 1)[0] + '/Goldfields' if '/' in str(actor.get_folder_path()) else folder
        elif kind.startswith('BP_') and kind not in ('BP_TrainingDrone_C', 'BP_ScanTarget_C', 'BP_LogVoice_C', 'BP_DivinityRay_C', 'BP_Creature_C'):
            spot = actor.get_actor_location()
            keep.append((spot.x, spot.y))
        elif isinstance(actor, unreal.StaticMeshActor):
            origin, extent = actor.get_actor_bounds(True)
            if max(extent.x, extent.y) < 4000.0 and extent.z > 15.0:
                for cx in range(int((origin.x - extent.x) // 2000), int((origin.x + extent.x) // 2000) + 1):
                    for cy in range(int((origin.y - extent.y) // 2000), int((origin.y + extent.y) // 2000) + 1):
                        boxes.setdefault((cx, cy), []).append((origin.x - extent.x - 40, origin.x + extent.x + 40, origin.y - extent.y - 40, origin.y + extent.y + 40,
                                                               origin.z - extent.z, origin.z + extent.z))
    keep_cells = {}
    for x, y in keep:
        keep_cells.setdefault((int(x // 800), int(y // 800)), []).append((x, y))

    def near_gameplay(x, y):
        cx, cy = int(x // 800), int(y // 800)
        return any(math.hypot(x - px, y - py) < 800.0 for i in (-1, 0, 1) for j in (-1, 0, 1) for px, py in keep_cells.get((cx + i, cy + j), ()))

    def built(x, y, z):
        return any(x1 < x < x2 and y1 < y < y2 and z1 - 60 < z < z2 for x1, x2, y1, y2, z1, z2 in boxes.get((int(x // 2000), int(y // 2000)), ()))

    entry = None
    if name == 'center':
        from physis_center_lore import GRASS_SCAN as entry
        tuft_mesh = unreal.load_asset('/Game/Center/Meshes/SM_CT_CutGrass')
    elif name == 'conclave':
        from physis_conclave_lore import GRASS_ENTRY as entry
    try:
        import physis_grove_scenario as base
        wrap = base.wrap
    except Exception:
        wrap = lambda text: text
    rng = random.Random('goldgrass ' + name)
    fields, tufts, tags, centres = 0, 0, 0, []
    every = FIELD_EVERY[name]
    for ax, ay, bx, by, half in world.roads:
        length = math.hypot(bx - ax, by - ay)
        if length < 1.0:
            continue
        ux, uy = (bx - ax) / length, (by - ay) / length
        steps = max(1, int(length / every))
        for k in range(steps):
            t = (k + rng.uniform(.25, .75)) / steps
            side = 1 if (k + fields) % 2 else -1
            off = half + rng.uniform(4.0, 13.0)
            x, y = ax + ux * length * t - uy * off * side, ay + uy * length * t + ux * off * side
            if not world.open(x, y) or world.road_gap(x, y) < 3.0 or world.level_ground(x, y) is None or near_gameplay(x * M, y * M):
                continue
            if any(math.hypot(x - px, y - py) < 9.0 for px, py in centres):
                continue
            made = []
            for i in range(TUFTS):
                a, r = rng.uniform(0, 2 * math.pi), 500.0 * math.sqrt(rng.uniform(.02, 1))
                tx, ty = x * M + math.cos(a) * r, y * M + math.sin(a) * r
                tz = world.at(tx, ty)
                if tz < world.water + 25 or world.road_gap(tx / M, ty / M) < .6 or built(tx, ty, tz):
                    continue
                size = rng.uniform(.85, 1.2)
                actor = sub.spawn_actor_from_class(grass, unreal.Vector(tx, ty, tz), unreal.Rotator(0, 0, rng.uniform(0, 360)))
                actor.set_actor_label('Scene Goldfield %d Grass %d' % (fields, i))
                actor.set_folder_path(folder)
                shape = actor.get_component_by_class(unreal.StaticMeshComponent)
                if name == 'center':
                    actor.set_actor_scale3d(unreal.Vector(size, size, size * rng.uniform(.9, 1.15)))
                    shape.set_static_mesh(tuft_mesh)
                    for index in range(len(tuft_mesh.get_editor_property('static_materials'))):
                        shape.set_material(index, tuft_mesh.get_material(index))
                    shape.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
                else:
                    shape.set_editor_property('relative_scale3d', unreal.Vector(GRASS_SIZE[0] * size, GRASS_SIZE[1] * size, GRASS_SIZE[2] * size * rng.uniform(.9, 1.15)))
                shape.set_collision_profile_name('NoCollision')
                shape.set_editor_property('cast_shadow', False)
                made.append(actor)
            if not made:
                continue
            if entry and fields % 4 == 0:
                category, title, text = entry
                tag = sub.spawn_actor_from_class(scan, unreal.Vector(x * M, y * M, world.at(x * M, y * M) + 150))
                tag.set_actor_label('Scene Goldfield %d Tag' % fields)
                tag.set_folder_path(folder)
                for key, value in (('ScanCategory', category), ('ScanTitle', title), ('ScanText', wrap(text)), ('ScanImportant', False)):
                    tag.set_editor_property(key, value)
                game.hide_scan(tag)
                tags += 1
            centres.append((x, y))
            fields += 1
            tufts += len(made)
    report = {'world': name, 'removed': removed, 'grass_before': before, 'fields': fields, 'tufts_added': tufts, 'tags': tags, 'road_segments': len(world.roads),
              'saved': editor.save_current_level() if save else False}
    (ROOT / 'Saved/Fauna').mkdir(parents=True, exist_ok=True)
    (ROOT / ('Saved/Fauna/goldgrass_%s.json' % name)).write_text(json.dumps(report, indent=1))
    return report
