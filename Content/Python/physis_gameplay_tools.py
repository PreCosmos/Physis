"""Fixed production steps for Physis's playable character and first level."""
import json
import pathlib
import unreal

BLUEPRINTS = '/Game/Characters/Physis/Blueprints'
CHARACTER = BLUEPRINTS + '/BP_Physis'
SOURCE = '/Game/MetaHumans/MH_Physis/BP_MH_Physis'
ACTIONS = '/Game/Input/Actions'


def save(asset):
    # save_loaded_asset skips assets it thinks are clean, and script edits such as
    # map_key do not always mark them dirty, so this always writes the package.
    path = asset.get_path_name().split('.')[0]
    if not unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False):
        raise RuntimeError('Could not save ' + path)


def key_name(key):
    text = key.export_text()
    return text.split('=')[-1].strip('()"')


def inspect():
    report = {}
    for path in ('/Game/Input/IMC_Default', '/Game/Input/IMC_MouseLook'):
        imc = unreal.load_asset(path)
        report[path.split('/')[-1]] = [(m.action.get_name(), key_name(m.key))
                                       for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')]
    mesh = unreal.load_asset('/Game/HandsomeKatana/Demo/Characters/Manny_UE5/Meshes/SKM_Manny_HK')
    sockets = {}
    for i in range(mesh.num_sockets()):
        socket = mesh.get_socket_by_index(i)
        sockets[str(socket.socket_name)] = {'bone': str(socket.bone_name), 'loc': str(socket.relative_location),
                                            'rot': str(socket.relative_rotation), 'scale': str(socket.relative_scale)}
    report['sockets'] = sockets
    katana = unreal.load_asset('/Game/HandsomeKatana/Weapon/SM_Katana_HK')
    box = katana.get_bounding_box()
    report['pack_katana'] = [str(box.min), str(box.max)]
    animation = unreal.load_asset('/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed')
    report['slots'] = [x for x in dir(unreal) if 'AnimNode_Slot' in x or 'AnimGraphNode_Slot' in x]
    report['montage_factory'] = hasattr(unreal, 'AnimMontageFactory')
    report['input_factory'] = [x for x in dir(unreal) if 'InputAction' in x and 'Factory' in x]
    return json.dumps(report, default=str)


def create_character():
    library = unreal.EditorAssetLibrary
    if not library.does_directory_exist(BLUEPRINTS):
        library.make_directory(BLUEPRINTS)
    if not library.does_asset_exist(CHARACTER):
        if not library.duplicate_asset(SOURCE, CHARACTER):
            raise RuntimeError('Could not duplicate ' + SOURCE)
    return json.dumps({'character': CHARACTER})


def template(name):
    bp = unreal.load_asset(CHARACTER)
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
        if isinstance(obj, unreal.ActorComponent) and obj.get_name().split('_GEN')[0] == name:
            return obj
    raise RuntimeError('No component named ' + name)


def input_actions():
    # Every action works on keyboard and mouse and on a gamepad (Light attack RB, Heavy attack RT, B parry or dodge).
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    library = unreal.EditorAssetLibrary
    bindings = {'IA_Sprint': (),
                # The gamepad's View (Select) button opens the level map (author, 2026-11-04); the Logbook keeps L
                # and stays a tab of the pause menu.
                'IA_Logbook': ('L',),
                'IA_Pause': ('Escape', 'P', 'Gamepad_Special_Right'),
                'IA_Dodge': ('LeftAlt',),
                # Controller B (Right Face Button) parries when an attack is coming and dodges otherwise.
                'IA_ParryDodge': ('Gamepad_FaceButton_Right',),
                'IA_Attack': ('LeftMouseButton', 'Gamepad_RightShoulder'),
                'IA_AttackHeavy': ('MiddleMouseButton', 'F', 'Gamepad_RightTrigger'),
                'IA_Block': ('RightMouseButton',),
                'IA_SwitchWeapon': ('Tab', 'Gamepad_DPad_Up'),
                'IA_Reload': ('R', 'Gamepad_DPad_Down'),
                'IA_ScanVisor': ('Q', 'Gamepad_FaceButton_Top'),
                'IA_Scan': ('LeftShift', 'Gamepad_LeftTrigger'),
                'IA_Interact': ('E', 'Gamepad_FaceButton_Left'),
                # Level 2 abilities (Tools/blueprint_logic/center_logic.py): Settle and the Mend heal.
                'IA_Settle': ('V', 'Gamepad_DPad_Right'),
                'IA_Mend': ('Z', 'Gamepad_DPad_Left'),
                # The level map (Tools/blueprint_logic/center_overrides.py part map): the pause menu's Map tab.
                'IA_Map': ('M', 'Gamepad_Special_Left')}
    imc = unreal.load_asset('/Game/Input/IMC_Default')
    # Remove any earlier attempt so every action ends up with exactly its two keys.
    for name in bindings:
        if library.does_asset_exist(ACTIONS + '/' + name):
            imc.unmap_all_keys_from_action(unreal.load_asset(ACTIONS + '/' + name))
    existing = {(m.action.get_name(), key_name(m.key)) for m in
                imc.get_editor_property('default_key_mappings').get_editor_property('mappings')}
    for name, keys in bindings.items():
        path = ACTIONS + '/' + name
        action = unreal.load_asset(path) if library.does_asset_exist(path) else \
            tools.create_asset(name, ACTIONS, unreal.InputAction, unreal.InputAction_Factory())
        save(action)
        for key in keys:
            if (name, key) not in existing:
                bound = unreal.Key()
                bound.set_editor_property('key_name', key)
                imc.map_key(action, bound)
    # The logbook pauses the game, so its own key must still fire to close it.
    for name in ('IA_Logbook', 'IA_Pause', 'IA_Scan', 'IA_Block', 'IA_Map'):
        menu = unreal.load_asset(ACTIONS + '/' + name)
        menu.set_editor_property('trigger_when_paused', True)
        save(menu)
    save(imc)
    return [(m.action.get_name(), key_name(m.key)) for m in
            imc.get_editor_property('default_key_mappings').get_editor_property('mappings')]


def setup_components():
    from editor_toolset.toolsets.actor import ActorTools
    bp = unreal.load_asset(CHARACTER)
    root = template('Root')
    root.set_editor_property('relative_location', unreal.Vector(0, 0, -90))
    root.set_editor_property('relative_rotation', unreal.Rotator(0, 0, -90))
    names = []
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
        if isinstance(obj, unreal.ActorComponent):
            names.append(obj.get_name().split('_GEN')[0])
    if 'CameraBoom' not in names:
        boom = ActorTools.add_component(root, unreal.SpringArmComponent.static_class(), 'CameraBoom')
        boom.set_editor_property('relative_location', unreal.Vector(0, 0, 150))
        boom.set_editor_property('target_arm_length', 320)
        boom.set_editor_property('use_pawn_control_rotation', True)
        boom.set_editor_property('enable_camera_lag', True)
        camera = ActorTools.add_component(boom, unreal.CameraComponent.static_class(), 'FollowCamera')
        camera.set_editor_property('use_pawn_control_rotation', False)
    if 'Katana' not in names:
        katana = ActorTools.add_component(template('Body'), unreal.StaticMeshComponent.static_class(), 'Katana')
        katana.set_static_mesh(unreal.load_asset('/Game/Stylized_Katana/Katana/Meshes/SM_Katana_1_A'))
        katana.set_editor_property('relative_scale3d', unreal.Vector(.4, .4, .4))
    # Grip from the animation pack's hand socket. The stylized blade points along -Y
    # where the pack's points along -Z, so it turns a quarter turn first.
    grip = unreal.Transform(unreal.Vector(-2.5, 2.1, -5.4), unreal.Rotator(173.04, -41.8, 163.32), unreal.Vector(1, 1, 1))
    blade = unreal.Transform(unreal.Vector(0, 0, 0), unreal.Rotator(90, 0, 0), unreal.Vector(.4, .4, .4))
    placed = blade * grip
    katana = template('Katana')
    katana.set_editor_property('relative_location', placed.translation)
    katana.set_editor_property('relative_rotation', placed.rotation.rotator())
    katana.set_editor_property('relative_scale3d', unreal.Vector(.4, .4, .4))
    katana.set_collision_profile_name('NoCollision')
    body = template('Body')
    body.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_BLUEPRINT)
    body.set_editor_property('anim_class', unreal.load_asset('/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed').generated_class())
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('use_controller_rotation_yaw', False)
    movement = cdo.get_editor_property('character_movement')
    movement.set_editor_property('orient_rotation_to_movement', True)
    movement.set_editor_property('rotation_rate', unreal.Rotator(0, 0, 540))
    # She runs by default; holding the walk input slows her down.
    movement.set_editor_property('max_walk_speed', 500)
    movement.set_editor_property('jump_z_velocity', 550)
    movement.set_editor_property('air_control', .35)
    save(bp)
    return {'components': sorted(set(names))}


KATANA_CLIPS = tuple('Physis_AS_HK_' + name for name in (
    'Slash2', 'Slash3', 'Slash4', 'Slash5', 'Slash6', 'Slash7', 'Slash8', 'Slash9', 'Stab', 'Kick1', 'Kick2',
    'Combo1', 'Combo2', 'Combo3', 'Combo4', 'Combo5', 'JumpAttack1', 'JumpAttack2', 'Evade', 'Block', 'Impact',
    'Hit_Back_Small', 'Hit_Front_Small', 'Hit_Front_Small1', 'Hit_Front_Big1', 'Hit_Front_Big2', 'Dead'))


def make_montages():
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    library = unreal.EditorAssetLibrary
    folder = '/Game/Characters/Physis/Animations/Katana/Montages'
    made = []
    clips = [(name.replace('Physis_AS_HK_', 'AM_Physis_'), name) for name in KATANA_CLIPS]
    for name, clip in [('AM_Physis_Slash', 'Physis_AS_HK_Slash1'), ('AM_Physis_Dodge', 'Physis_AS_HK_Dodge')] + clips:
        path = folder + '/' + name
        if not library.does_asset_exist(path):
            factory = unreal.AnimMontageFactory()
            factory.set_editor_property('source_animation', unreal.load_asset('/Game/Characters/Physis/Animations/Katana/' + clip))
            montage = tools.create_asset(name, folder, unreal.AnimMontage, factory)
            save(montage)
        made.append(path)
    return made


def game_mode():
    library = unreal.EditorAssetLibrary
    path = BLUEPRINTS + '/BP_PhysisGameMode'
    if not library.does_asset_exist(path):
        library.duplicate_asset('/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode', path)
    mode = unreal.load_asset(path)
    character = unreal.load_asset(CHARACTER)
    unreal.BlueprintEditorLibrary.compile_blueprint(mode)
    cdo = unreal.get_default_object(mode.generated_class())
    cdo.set_editor_property('default_pawn_class', character.generated_class())
    save(character);save(mode)
    controller = cdo.get_editor_property('player_controller_class')
    return {'mode': path, 'pawn': cdo.get_editor_property('default_pawn_class').get_name(),
            'controller': controller.get_name() if controller else None}


LEVEL = '/Game/Levels/L_BattleStation'
WALL = 40
DOOR_WIDTH = 420
DOOR_HEIGHT = 340
# name, x1, x2, y1, y2, height
ROOMS = (('Breach Deck', 0, 2400, -900, 900, 500),
         ('Damage Control', 2400, 4200, -800, 800, 450),
         ('Crew Ring', 4200, 6400, -900, 900, 450),
         ('Armory', 6400, 8200, -800, 800, 450),
         ('Boarding Spine', 8200, 11000, -400, 400, 400),
         ('Reactor Gallery', 11000, 13400, -1200, 1200, 800),
         ('Fleet Bridge Approach', 13400, 16400, -1200, 1200, 700),
         ('Observation Deck', 16400, 18400, -900, 900, 500))


class Station:
    """Graybox builder: every piece is a collidable, labelled, foldered cube."""

    def __init__(self):
        self.actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.mesh = unreal.load_asset('/Engine/BasicShapes/Cube')
        self.gray = unreal.load_asset('/Game/LevelPrototyping/Materials/MI_PrototypeGrid_Gray')
        self.dark = unreal.load_asset('/Game/LevelPrototyping/Materials/MI_PrototypeGrid_TopDark')
        self.mark = unreal.load_asset('/Game/LevelPrototyping/Materials/MI_DefaultColorway')
        self.count = 0

    def box(self, label, folder, center, size, material=None):
        actor = self.actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*center))
        component = actor.static_mesh_component
        component.set_static_mesh(self.mesh)
        component.set_material(0, material or self.gray)
        actor.set_actor_scale3d(unreal.Vector(size[0] / 100, size[1] / 100, size[2] / 100))
        actor.set_actor_label(label)
        actor.set_folder_path('Station/' + folder)
        self.count += 1
        return actor

    def wall(self, label, folder, fixed, axis, start, end, height, gaps=()):
        """A wall along X (axis 0) or Y (axis 1), with door openings centered at gaps."""
        cuts = sorted(gaps)
        cursor = start
        def piece(a, b, z, h):
            if b - a < 1:
                return
            middle = (a + b) / 2
            center = (middle, fixed, z) if axis == 0 else (fixed, middle, z)
            size = (b - a, WALL, h) if axis == 0 else (WALL, b - a, h)
            self.box(label, folder, center, size)
        for gap in cuts:
            piece(cursor, gap - DOOR_WIDTH / 2, height / 2, height)
            piece(gap - DOOR_WIDTH / 2, gap + DOOR_WIDTH / 2, (height + DOOR_HEIGHT) / 2, height - DOOR_HEIGHT)
            cursor = gap + DOOR_WIDTH / 2
        piece(cursor, end, height / 2, height)

    def shell(self, label, x1, x2, y1, y2, height):
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        size = (x2 - x1, y2 - y1)
        self.box(label + ' Floor', label, (center[0], center[1], -20), (size[0], size[1], 40), self.dark)
        self.box(label + ' Ceiling', label, (center[0], center[1], height + 20), (size[0], size[1], 40))

    def light(self, label, folder, location, radius):
        actor = self.actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*location))
        component = actor.get_component_by_class(unreal.PointLightComponent)
        component.set_editor_property('intensity', 12000)
        component.set_editor_property('attenuation_radius', radius)
        component.set_cast_shadows(False)
        component.set_light_color(unreal.LinearColor(.85, .9, 1, 1))
        actor.set_actor_label(label)
        actor.set_folder_path('Station/' + folder)

    def sign(self, text, folder, location, yaw):
        # The author asks for 3D text explicitly; until then the graybox stays unsigned.
        return
        actor = self.actors.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(*location), unreal.Rotator(0, 0, yaw))
        component = actor.text_render
        component.set_editor_property('text', text)
        component.set_editor_property('horizontal_alignment', unreal.HorizTextAligment.EHTA_CENTER)
        component.set_editor_property('world_size', 60)
        component.set_editor_property('text_render_color', unreal.Color(r=120, g=220, b=255, a=255))
        actor.set_actor_label('Sign ' + text)
        actor.set_folder_path('Station/' + folder)


def build_level():
    library = unreal.EditorAssetLibrary
    if not library.does_directory_exist('/Game/Levels'):
        library.make_directory('/Game/Levels')
    unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    station = Station()
    for name, x1, x2, y1, y2, height in ROOMS:
        station.shell(name, x1, x2, y1, y2, height)
        south_gaps = [3300] if name == 'Damage Control' else [12000] if name == 'Reactor Gallery' else []
        station.wall(name + ' North Wall', name, y2, 0, x1, x2, height, [3300] if name == 'Damage Control' else [])
        station.wall(name + ' South Wall', name, y1, 0, x1, x2, height, south_gaps)
        for i in range(max(1, (x2 - x1) // 1600)):
            spacing = (x2 - x1) / max(1, (x2 - x1) // 1600)
            station.light(name + ' Light', name, (x1 + spacing * (i + .5), (y1 + y2) / 2, height - 60), 1800)
        station.sign(name.upper(), name, (x1 + 60, 0, DOOR_HEIGHT + 45), 0)
    # Walls between rooms, each with a central door; the ends of the run are closed.
    for index, (name, x1, x2, y1, y2, height) in enumerate(ROOMS):
        if index == 0:
            station.wall('Station West Wall', name, x1, 1, y1, y2, height)
        if index + 1 < len(ROOMS):
            other = ROOMS[index + 1]
            station.wall(name + ' East Wall', name, x2, 1, min(y1, other[3]), max(y2, other[4]), max(height, other[5]), [0])
        else:
            station.wall('Station East Wall', name, x2, 1, y1, y2, height)
    # Service Loop: a low corridor from the Reactor Gallery back to Damage Control.
    loop = 'Service Loop'
    station.shell(loop, 3100, 12400, -1600, -1200, 340)
    station.shell(loop + ' Link', 3100, 3500, -1200, -800, 340)
    station.wall(loop + ' North Wall', loop, -1200, 0, 3500, 11000, 340)
    station.wall(loop + ' South Wall', loop, -1600, 0, 3100, 12400, 340)
    station.wall(loop + ' West Wall', loop, 3100, 1, -1600, -800, 340)
    station.wall(loop + ' East Wall', loop, 12400, 1, -1600, -1200, 340)
    station.wall(loop + ' Link East Wall', loop, 3500, 1, -1200, -800, 340)
    for x in (4600, 7600, 10600):
        station.light(loop + ' Light', loop, (x, -1400, 280), 1600)
    station.sign('SERVICE LOOP', loop, (12000, -1230, 300), 90)
    # Sealed door from the design, in the Damage Control north doorway.
    station.box('Sealed Divinity Door', 'Damage Control', (3300, 800, 170), (DOOR_WIDTH, 60, 340), station.mark)
    station.sign('SEALED', 'Damage Control', (3300, 760, 370), -90)
    # Traversal and cover, one simple idea per space.
    for label, center, size in (('Crate Low', (900, 300, 40), (200, 200, 80)),
                                ('Crate Mid', (1250, 300, 70), (200, 200, 140)),
                                ('Crate High', (1600, 300, 100), (200, 200, 200)),
                                ('Collapsed Beam', (1900, -300, 60), (120, 900, 120))):
        station.box(label, 'Breach Deck', center, size, station.mark)
    for x in (8900, 9600, 10300):
        station.box('Cover Pillar', 'Boarding Spine', (x, 180, 100), (140, 140, 200), station.mark)
        station.box('Cover Pillar', 'Boarding Spine', (x + 340, -180, 100), (140, 140, 200), station.mark)
    station.box('Reactor Core', 'Reactor Gallery', (12200, 0, 400), (700, 700, 800), station.mark)
    for x in (14300, 15500):
        for y in (-600, 600):
            station.box('Arena Pillar', 'Fleet Bridge Approach', (x, y, 150), (240, 240, 300), station.mark)
    player = station.actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(300, 0, 110))
    player.set_folder_path('Station')
    sky = station.actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 900))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property('intensity', .6)
    sky.set_folder_path('Station')
    volume = station.actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    volume.set_editor_property('unbound', True)
    settings = volume.get_editor_property('settings')
    settings.set_editor_property('override_auto_exposure_min_brightness', True)
    settings.set_editor_property('auto_exposure_min_brightness', 1)
    settings.set_editor_property('override_auto_exposure_max_brightness', True)
    settings.set_editor_property('auto_exposure_max_brightness', 1)
    volume.set_editor_property('settings', settings)
    volume.set_folder_path('Station')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world_settings = world.get_world_settings()
    mode = unreal.load_asset(BLUEPRINTS + '/BP_PhysisGameMode')
    world_settings.set_editor_property('default_game_mode', mode.generated_class())
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
        raise RuntimeError('Could not save ' + LEVEL)
    return {'level': LEVEL, 'pieces': station.count}


def create_tutorial_assets():
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    library = unreal.EditorAssetLibrary
    made = {}
    for name, parent in (('BP_PhysisHUD', unreal.HUD), ('BP_TutorialTrigger', unreal.Actor)):
        path = BLUEPRINTS + '/' + name
        if not library.does_asset_exist(path):
            factory = unreal.BlueprintFactory()
            factory.set_editor_property('parent_class', parent)
            asset = tools.create_asset(name, BLUEPRINTS, unreal.Blueprint, factory)
            save(asset)
        made[name] = path
    return made


# Message, centre of the zone, zone scale (the Blueprint's box is 600 x 600 x 400).
TUTORIALS = (('Move: W A S D / |LS|     Look: Mouse / |RS|', (320, 0, 160), (1, 2.6, 1)),
             ('Jump: Space / |A|     Hold to jump higher', (800, 300, 160), (.5, 1.2, 1)),
             ('Walk: Hold Left Shift / |L3|', (1500, -500, 160), (.8, 1, 1)),
             ('Divinity Sense: Q / |Y|     Then hold Right Mouse / |LT| on a marker', (2800, 0, 160), (.5, 2.5, 1)),
             ('Crystals hold Divinity.  Capsules heal.  Cells are ammo.', (1250, 0, 160), (.4, 2.6, 1)),
             ('Sealed door.     Interact: E / |X|', (3300, 500, 160), (.7, .8, 1)),
             ('Dodge: Left Alt / |B|', (4700, 0, 160), (.5, 2.6, 1)),
             ('Door ahead.     Interact: E / |X|', (6150, 0, 160), (.5, 1.2, 1)),
             ('Light attack: Left Mouse / |RB|     Heavy attack: Middle Mouse or F / |RT|', (6900, 0, 160), (.5, 2.5, 1)),
             ('Hold Right Mouse / |LT| to lock on     Block: C / |LB|     Dodge: Left Alt / |B|', (8600, 0, 160), (.5, 1.2, 1)),
             ('Sidearm: Tab / |DU|     Reload: R / |DD|     Heavy attack fires a Divinity Shot', (9300, 0, 160), (.5, 2.5, 1)),
             ('The Service Loop leads back to Damage Control', (11900, -900, 160), (1, .8, 1)),
             ('Chain light and heavy attacks into combos', (13900, 0, 160), (.6, 3.5, 1)),
             ('End of the station prototype', (16900, 0, 160), (.6, 2.6, 1)))


def place_tutorials():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        if actor.get_actor_label().startswith('Tutorial '):
            subsystem.destroy_actor(actor)
    trigger = unreal.load_asset(BLUEPRINTS + '/BP_TutorialTrigger').generated_class()
    for index, (message, location, scale) in enumerate(TUTORIALS):
        actor = subsystem.spawn_actor_from_class(trigger, unreal.Vector(*location))
        actor.set_actor_label('Tutorial %02d' % (index + 1))
        actor.set_actor_scale3d(unreal.Vector(*scale))
        actor.set_editor_property('Message', message)
        actor.set_folder_path('Station/Tutorial')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
        raise RuntimeError('Could not save ' + LEVEL)
    mode = unreal.load_asset(BLUEPRINTS + '/BP_PhysisGameMode')
    hud = unreal.load_asset(BLUEPRINTS + '/BP_PhysisHUD')
    unreal.BlueprintEditorLibrary.compile_blueprint(mode)
    cdo = unreal.get_default_object(mode.generated_class())
    cdo.modify()
    cdo.set_editor_property('hud_class', hud.generated_class())
    unreal.EditorAssetLibrary.save_asset(BLUEPRINTS + '/BP_PhysisGameMode', only_if_is_dirty=False)
    return {'placed': len(TUTORIALS), 'level': world.get_name(), 'hud': cdo.get_editor_property('hud_class').get_name()}


def create_gameplay_assets():
    from editor_toolset.toolsets.actor import ActorTools
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    library = unreal.EditorAssetLibrary
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    cube = unreal.load_asset('/Engine/BasicShapes/Cube')
    sphere = unreal.load_asset('/Engine/BasicShapes/Sphere')
    colour = unreal.load_asset('/Game/LevelPrototyping/Materials/MI_DefaultColorway')
    plans = (('BP_ScanTarget', cube, (.6, .15, 1.2)), ('BP_TrainingDrone', sphere, (.8, .8, .8)), ('BP_StationDoor', cube, (4.2, .4, 3.4)))
    for name, mesh, scale in plans:
        path = BLUEPRINTS + '/' + name
        if library.does_asset_exist(path):
            continue
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = tools.create_asset(name, BLUEPRINTS, unreal.Blueprint, factory)
        root = None
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj, unreal.SceneComponent):
                root = obj
        part = ActorTools.add_component(root, unreal.StaticMeshComponent.static_class(), 'Shape')
        part.set_static_mesh(mesh)
        part.set_material(0, colour)
        part.set_editor_property('relative_scale3d', unreal.Vector(*scale))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
    return [p[0] for p in plans]


# Label, description, location.
SCANS = (('Scan Conduit', 'Live power conduit. Overloaded by a Divinity surge.', (2900, -760, 170)),
         ('Scan Hull Breach', 'Hull breach sealed by emergency foam. It will not hold for long.', (2700, 760, 170)),
         ('Scan Sealed Door', 'Sealed by Divinity. No human key will open this door.', (3300, 770, 170)),
         ('Scan Crew Terminal', 'Crew log: the First Ones are boarding through the hangar.', (5300, 860, 170)),
         ('Scan Armory Rack', 'Boarding blades. Their edges stop First One guards where gunfire fails.', (7300, 760, 170)),
         ('Scan Reactor', 'Reactor core. Divinity here is twisted into a shape that hurts to perceive.', (12200, 370, 300)))
# Scans that matter show yellow instead of green and take twice as long.
IMPORTANT_SCANS = ('Scan Crew Terminal', 'Scan Reactor', 'Scan Sealed Door')
DRONE_SCAN = 'Training drone. Close-range striker. Keep moving, or block.'
DRONES = ((7300, 300, 130), (7700, -250, 130), (7900, 200, 130), (9250, 0, 130), (9950, 0, 130), (14900, 0, 130))


# Kind (0 health, 1 Divinity, 2 ammo), x, y.
PICKUPS = ((1, 1200, -350), (1, 2500, 350), (0, 2200, -350), (1, 3600, -300), (1, 5000, 350), (2, 6700, 350), (1, 7000, -350),
           (2, 8200, 250), (0, 8700, -300), (1, 9600, 300), (2, 10400, -250), (1, 11000, 0), (0, 12500, 0), (1, 13000, 300),
           (2, 14000, 0), (1, 15200, -250))


def hide_scan(actor):
    actor.set_actor_hidden_in_game(True)
    actor.set_actor_enable_collision(False)


def place_gameplay():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        label = actor.get_actor_label()
        if label.startswith(('Scan ', 'Drone ', 'Door ', 'Pickup ')) or label == 'Sealed Divinity Door':
            subsystem.destroy_actor(actor)
    scan = unreal.load_asset(BLUEPRINTS + '/BP_ScanTarget').generated_class()
    for label, text, location in SCANS:
        actor = subsystem.spawn_actor_from_class(scan, unreal.Vector(*location))
        actor.set_actor_label(label)
        actor.set_editor_property('ScanText', text)
        actor.set_editor_property('ScanImportant', label in IMPORTANT_SCANS)
        actor.set_folder_path('Station/Gameplay')
        if label == 'Scan Sealed Door':
            hide_scan(actor)
    drone = unreal.load_asset(BLUEPRINTS + '/BP_TrainingDrone').generated_class()
    for index, location in enumerate(DRONES):
        actor = subsystem.spawn_actor_from_class(drone, unreal.Vector(*location))
        actor.set_actor_label('Drone %d' % (index + 1))
        # The drone carries its scan point, which goes when the drone is destroyed.
        tag = subsystem.spawn_actor_from_class(scan, unreal.Vector(location[0], location[1], location[2] + 70))
        tag.set_actor_label('Scan Drone %d' % (index + 1))
        tag.set_editor_property('ScanText', DRONE_SCAN)
        tag.set_folder_path('Station/Gameplay')
        hide_scan(tag)
        tag.attach_to_actor(actor, 'None', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
        actor.set_folder_path('Station/Gameplay')
    door = unreal.load_asset(BLUEPRINTS + '/BP_StationDoor').generated_class()
    armory = subsystem.spawn_actor_from_class(door, unreal.Vector(6400, 0, 170), unreal.Rotator(0, 0, 90))
    armory.set_actor_label('Door Armory')
    armory.set_folder_path('Station/Gameplay')
    sealed = subsystem.spawn_actor_from_class(door, unreal.Vector(3300, 800, 170))
    sealed.set_actor_label('Door Sealed')
    sealed.set_editor_property('DoorLocked', True)
    sealed.set_editor_property('LockedText', 'Sealed by Divinity. You cannot open this yet.')
    sealed.set_folder_path('Station/Gameplay')
    pickup = unreal.load_asset(BLUEPRINTS + '/BP_Pickup').generated_class()
    for index, (kind, x, y) in enumerate(PICKUPS):
        actor = subsystem.spawn_actor_from_class(pickup, unreal.Vector(x, y, 130))
        actor.set_actor_label('Pickup %02d' % (index + 1))
        actor.set_editor_property('Kind', kind)
        actor.set_folder_path('Station/Gameplay')
    result = place_tutorials()
    return {'scan': len(SCANS), 'drones': len(DRONES), 'doors': 2, 'tutorials': result['placed']}


def import_file(source, destination, options=None):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', source)
    task.set_editor_property('destination_path', destination)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    if options:
        task.set_editor_property('options', options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return task


def glow_material():
    library = unreal.EditorAssetLibrary
    lib = unreal.MaterialEditingLibrary
    path = '/Game/Gameplay/M_Physis_Item'
    if library.does_asset_exist(path):
        return unreal.load_asset(path)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    material = tools.create_asset('M_Physis_Item', '/Game/Gameplay', unreal.Material, unreal.MaterialFactoryNew())
    base = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -700, 0)
    base.set_editor_property('parameter_name', 'Colour')
    glow = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -900, 300)
    glow.set_editor_property('parameter_name', 'Glow')
    glow.set_editor_property('default_value', unreal.LinearColor(0, 0, 0, 1))
    rough = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -700, 150)
    rough.set_editor_property('parameter_name', 'Roughness')
    rough.set_editor_property('default_value', .3)
    clock = lib.create_material_expression(material, unreal.MaterialExpressionTime, -1100, 500)
    wave = lib.create_material_expression(material, unreal.MaterialExpressionSine, -900, 500)
    wave.set_editor_property('period', 1.6)
    lib.connect_material_expressions(clock, '', wave, '')
    swing = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -700, 500)
    swing.set_editor_property('const_b', .3)
    lib.connect_material_expressions(wave, '', swing, 'A')
    level = lib.create_material_expression(material, unreal.MaterialExpressionAdd, -550, 500)
    level.set_editor_property('const_b', 1)
    lib.connect_material_expressions(swing, '', level, 'A')
    bright = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -350, 350)
    lib.connect_material_expressions(glow, '', bright, 'A')
    lib.connect_material_expressions(level, '', bright, 'B')
    lib.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    lib.connect_material_property(bright, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    save(material)
    return material


ITEM_LOOKS = {'MI_Item_Dark': ((.02, .025, .035), (0, 0, 0), .35), 'MI_Item_Ivory': ((.85, .78, .62), (0, 0, 0), .4),
              'MI_Item_Glow': ((1, .55, .15), (9, 3.6, .7), .3), 'MI_Item_Divinity': ((.3, .8, 1), (2, 7, 12), .2),
              'MI_Item_Health': ((1, .3, .15), (10, 2, .6), .3), 'MI_Item_Tracer': ((1, .7, .3), (30, 13, 3), .5)}


def ui_import():
    library = unreal.EditorAssetLibrary
    lib = unreal.MaterialEditingLibrary
    root = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    for png in sorted((root / 'Art/UI').glob('T_*.png')):
        import_file(str(png), '/Game/UI')
        texture = unreal.load_asset('/Game/UI/' + png.stem)
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
        texture.set_editor_property('never_stream', True)
        texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
        texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
        save(texture)
    parent = glow_material()
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for name, (colour, glow, rough) in ITEM_LOOKS.items():
        path = '/Game/Gameplay/' + name
        instance = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset(name, '/Game/Gameplay', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(instance, parent)
        lib.set_material_instance_vector_parameter_value(instance, 'Colour', unreal.LinearColor(*colour, 1))
        lib.set_material_instance_vector_parameter_value(instance, 'Glow', unreal.LinearColor(*glow, 1))
        lib.set_material_instance_scalar_parameter_value(instance, 'Roughness', rough)
        lib.update_material_instance(instance)
        save(instance)
    looks = {'M_Dark': 'MI_Item_Dark', 'M_Ivory': 'MI_Item_Ivory', 'M_Glow': 'MI_Item_Glow'}
    sizes = {}
    for fbx in sorted((root / 'Art/Meshes').glob('*.fbx')):
        options = unreal.FbxImportUI()
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_as_skeletal', False)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
        options.static_mesh_import_data.set_editor_property('combine_meshes', True)
        options.static_mesh_import_data.set_editor_property('import_uniform_scale', .01)
        import_file(str(fbx), '/Game/Gameplay', options)
        mesh = unreal.load_asset('/Game/Gameplay/' + fbx.stem)
        slots = mesh.get_editor_property('static_materials')
        for index, slot in enumerate(slots):
            name = str(slot.get_editor_property('material_slot_name'))
            if fbx.stem == 'SM_Pickup_Divinity':
                name = 'divinity'
            look = 'MI_Item_Divinity' if name == 'divinity' else looks.get(name, 'MI_Item_Glow')
            if fbx.stem == 'SM_Pickup_Health' and name == 'M_Glow':
                look = 'MI_Item_Health'
            mesh.set_material(index, unreal.load_asset('/Game/Gameplay/' + look))
        save(mesh)
        sizes[fbx.stem] = [round(v, 1) for v in mesh.get_bounding_box().max.to_tuple()], [str(s.get_editor_property('material_slot_name')) for s in slots]
    return sizes


def pistol_stance():
    library = unreal.EditorAssetLibrary
    folder = '/Game/Characters/Physis/Animations/'
    source = folder + 'AnimBP/Physis_ABP_Unarmed'
    path = folder + 'AnimBP/Physis_ABP_Pistol'
    if not library.does_asset_exist(path):
        library.duplicate_asset(source, path)
    space_path = folder + 'AnimBP/Physis_BS_Pistol'
    if not library.does_asset_exist(space_path):
        library.duplicate_asset(folder + 'AnimBP/Physis_BS_Idle_Walk_Run', space_path)
    space = unreal.load_asset(space_path)
    samples = list(space.get_editor_property('sample_data'))
    speeds = sorted({sample.get_editor_property('sample_value').y for sample in samples})
    directions = {0: 'Fwd', 45: 'Fwd_Right', -45: 'Fwd_Left', 90: 'Right', -90: 'Left', 135: 'Bwd_Right', -135: 'Bwd_Left', 180: 'Bwd', -180: 'Bwd'}
    for sample in samples:
        value = sample.get_editor_property('sample_value')
        if value.y == speeds[0]:
            clip = 'Physis_MF_Pistol_Idle_ADS'
        else:
            clip = 'Physis_MF_Pistol_%s_%s' % ('Jog' if value.y == speeds[-1] else 'Walk', directions[round(value.x)])
        sample.set_editor_property('animation', unreal.load_asset(folder + clip))
    space.set_editor_property('sample_data', samples)
    save(space)
    abp = unreal.load_asset(path)
    name = path.split('/')[-1]
    base = '%s.%s:AnimGraph.AnimGraphNode_StateMachine_0.Locomotion.' % (path, name)
    idle = unreal.find_object(None, base + 'AnimStateNode_1.Idle.AnimGraphNode_SequencePlayer_1')
    walk = unreal.find_object(None, base + 'AnimStateNode_2.Walk / Run.AnimGraphNode_BlendSpacePlayer_0')
    node = idle.get_editor_property('node')
    node.import_text(node.export_text().replace('AnimBP/Physis_MM_Idle.Physis_MM_Idle', 'Physis_MF_Pistol_Idle_ADS.Physis_MF_Pistol_Idle_ADS'))
    idle.set_editor_property('node', node)
    node = walk.get_editor_property('node')
    node.import_text(node.export_text().replace('Physis_BS_Idle_Walk_Run.Physis_BS_Idle_Walk_Run', 'Physis_BS_Pistol.Physis_BS_Pistol'))
    walk.set_editor_property('node', node)
    unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    save(abp)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    montages = '/Game/Characters/Physis/Animations/Katana/Montages'
    made = {}
    for short in ('Fire', 'DryFire', 'Reload', 'Equip'):
        target = montages + '/AM_Physis_Pistol_' + short
        if not library.does_asset_exist(target):
            factory = unreal.AnimMontageFactory()
            factory.set_editor_property('source_animation', unreal.load_asset(folder + 'Physis_MM_Pistol_' + short))
            save(tools.create_asset('AM_Physis_Pistol_' + short, montages, unreal.AnimMontage, factory))
        made[short] = round(unreal.load_asset(target).get_play_length(), 2)
    return {'idle': 'Pistol_Idle_ADS' in idle.get_editor_property('node').export_text(), 'walk': 'Physis_BS_Pistol' in walk.get_editor_property('node').export_text(),
            'speeds': speeds, 'montages': made}


def combat_assets():
    from editor_toolset.toolsets.actor import ActorTools
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    library = unreal.EditorAssetLibrary
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    plans = (('BP_Pickup', '/Game/Gameplay/SM_Pickup_Divinity', 'OverlapAllDynamic', None, (1.3, 1.3, 1.3)),
             ('BP_GunTracer', '/Engine/BasicShapes/Cube', 'NoCollision', '/Game/Gameplay/MI_Item_Tracer', (1, 1, 1)))
    for name, mesh, profile, look, scale in plans:
        path = BLUEPRINTS + '/' + name
        if library.does_asset_exist(path):
            continue
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = tools.create_asset(name, BLUEPRINTS, unreal.Blueprint, factory)
        root = None
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj, unreal.SceneComponent):
                root = obj
        part = ActorTools.add_component(root, unreal.StaticMeshComponent.static_class(), 'Shape')
        part.set_static_mesh(unreal.load_asset(mesh))
        part.set_collision_profile_name(profile)
        part.set_editor_property('generate_overlap_events', True)
        part.set_editor_property('relative_scale3d', unreal.Vector(*scale))
        if look:
            part.set_material(0, unreal.load_asset(look))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
    tracer = unreal.load_asset(BLUEPRINTS + '/BP_GunTracer')
    unreal.get_default_object(tracer.generated_class()).set_editor_property('initial_life_span', .09)
    save(tracer)
    bp = unreal.load_asset(CHARACTER)
    names = []
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
        if isinstance(obj, unreal.ActorComponent):
            names.append(obj.get_name().split('_GEN')[0])
    if 'Gun' not in names:
        gun = ActorTools.add_component(template('Body'), unreal.StaticMeshComponent.static_class(), 'Gun')
        gun.set_static_mesh(unreal.load_asset('/Game/Gameplay/SM_Physis_Gun'))
    gun = template('Gun')
    gun.set_collision_profile_name('NoCollision')
    gun.set_editor_property('visible', False)
    gun.set_editor_property('relative_location', unreal.Vector(-9, 3.5, 1))
    gun.set_editor_property('relative_rotation', unreal.Rotator(0, 0, 90))
    gun.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    return names


CINEMA = '/Game/Cinematics'
CINEMA_LOOKS = {'MI_Hull': ((.1, .12, .15), (.016, .02, .026), .55), 'MI_Trim': ((.04, .05, .07), (.006, .008, .012), .4),
                'MI_Lights': ((1, .85, .6), (10, 8, 4.5), .4), 'MI_Drive': ((.3, .6, 1), (3, 9, 22), .4),
                'MI_Crystal': ((.1, .35, .5), (.03, .16, .22), .12), 'MI_CrystalGlow': ((.3, 1, .9), (2, 22, 18), .2)}
SLOTS = {'M_Hull': 'MI_ShipHuman', 'M_Trim': 'MI_ShipTrim', 'M_Lights': 'MI_Lights', 'M_Drive': 'MI_Drive', 'M_Crystal': 'MI_ShipFirst', 'M_CrystalGlow': 'MI_CrystalGlow'}


# Time, location, pitch, yaw. Starts past the fleets looking at empty space, turns, flies home.
SHOTS = ((0, (8500, -232000, 32000), 6, -98), (8, (8500, -229000, 32000), 4, -84), (12, (8700, -226500, 31000), 0, 20),
         (16, (8500, -224000, 29000), -5, 88), (21, (6000, -182000, 23000), -7, 92), (26, (9000, -118000, 16000), -5, 86),
         (31, (1500, -26000, 2200), -3, 88), (33.9, (300, -5650, 0), 0, 90), (34, (300, -5600, 0), 0, 90),
         (34.1, (340, -620, 330), -6, 66), (37, (120, -160, 200), -3, 22), (40, (32, 0, 150.1), 0, 0))


def cinema_place():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    library = unreal.EditorAssetLibrary
    for actor in subsystem.get_all_level_actors():
        if actor.get_actor_label().startswith('Cine '):
            subsystem.destroy_actor(actor)
    def solid(label, mesh, location, scale=1.0, look=None):
        actor = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*location))
        actor.set_actor_label(label)
        part = actor.static_mesh_component
        part.set_mobility(unreal.ComponentMobility.MOVABLE)
        part.set_static_mesh(unreal.load_asset(mesh))
        part.set_collision_profile_name('NoCollision')
        part.set_editor_property('cast_shadow', False)
        if look:
            part.set_material(0, unreal.load_asset(look))
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        actor.set_folder_path('Opening')
        return actor
    solid('Cine Sky', '/Engine/EngineSky/SM_SkySphere', (8500, 0, 0), 200, CINEMA + '/M_Space')
    hull = solid('Cine Hull', CINEMA + '/SM_Station_Hull', (0, 0, 0))
    # The hull's shell passes through the Inner Ring, so it exists only for the opening.
    hull.tags = ['CineOnly']
    ship = unreal.load_asset(BLUEPRINTS + '/BP_FleetShip').generated_class()
    rng = __import__('random').Random(9)
    fleets = ((-51500, 2500, 0, ('SM_Ship_Cruiser', 'SM_Ship_Frigate', 'SM_Ship_Frigate'), 'Human'),
              (68500, -2500, 180, ('SM_Ship_Vigil', 'SM_Ship_Shard', 'SM_Ship_Shard'), 'First'))
    # Sixty ships a side, in ranks that recede far behind each fleet's front line.
    for start, speed, yaw, models, name in fleets:
        back = -1 if speed > 0 else 1
        for index in range(60):
            rank = index // 10
            model = models[0] if index % 5 == 0 else models[1 + index % 2]
            place = unreal.Vector(start + back * rank * 16000 + rng.uniform(-9000, 9000), -130000 + rng.uniform(-70000, 70000), 15000 + rng.uniform(-24000, 24000))
            actor = subsystem.spawn_actor_from_class(ship, place, unreal.Rotator(0, rng.uniform(-3, 3), yaw + rng.uniform(-5, 5)))
            actor.set_actor_label('Cine %s %02d' % (name, index))
            actor.set_editor_property('SpeedX', speed * rng.uniform(.85, 1.1))
            part = actor.get_component_by_class(unreal.StaticMeshComponent)
            part.set_static_mesh(unreal.load_asset(CINEMA + '/' + model))
            actor.set_actor_scale3d(unreal.Vector(*[4 if index % 5 == 0 else 2.5] * 3))
            actor.set_folder_path('Opening')
    director = subsystem.spawn_actor_from_class(unreal.load_asset(BLUEPRINTS + '/BP_BattleDirector').generated_class(), unreal.Vector(0, 0, 0))
    director.set_actor_label('Cine Director')
    director.set_folder_path('Opening')
    camera = subsystem.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(*SHOTS[0][1]))
    camera.set_actor_label('Cine Camera')
    camera.set_folder_path('Opening')
    lens = camera.get_cine_camera_component()
    lens.set_editor_property('current_focal_length', 11.88)
    lens.set_editor_property('constrain_aspect_ratio', False)
    path = CINEMA + '/SEQ_Opening'
    if library.does_asset_exist(path):
        library.delete_asset(path)
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset('SEQ_Opening', CINEMA, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(30000, 1))
    sequence.set_playback_start_seconds(0)
    sequence.set_playback_end_seconds(40)
    frames = 1200
    tick = 1000
    binding = sequence.add_possessable(camera)
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
    section = track.add_section()
    section.set_range(0, frames)
    channels = section.get_all_channels()
    for when, place, pitch, yaw in SHOTS:
        key = unreal.FrameNumber(round(when * 30))
        for channel, value in zip(channels[:6], (place[0], place[1], place[2], 0, pitch, yaw)):
            channel.add_key(key, value)
    cuts = sequence.add_track(unreal.MovieSceneCameraCutTrack)
    cut = cuts.add_section()
    cut.set_range(0, frames)
    cut.set_camera_binding_id(sequence.get_binding_id(binding))
    audio = sequence.add_track(unreal.MovieSceneAudioTrack)
    sound = audio.add_section()
    sound.set_range(0, frames + 60)
    sound.set_sound(unreal.load_asset(CINEMA + '/S_Opening'))
    fades = sequence.add_track(unreal.MovieSceneFadeTrack)
    start = fades.add_section()
    start.set_range(0, 90)
    channel = start.get_all_channels()[0]
    channel.add_key(unreal.FrameNumber(0), 1.0)
    channel.add_key(unreal.FrameNumber(75), 0.0)
    flash = fades.add_section()
    flash.set_range(990, 1100)
    flash.set_editor_property('fade_color', unreal.LinearColor(1, .85, .6, 1))
    channel = flash.get_all_channels()[0]
    for key, value in ((990, 0.0), (1020, 1.0), (1024, 1.0), (1070, 0.0)):
        channel.add_key(unreal.FrameNumber(key), value)
    save(sequence)
    player = subsystem.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(0, 0, 0))
    player.set_actor_label('Cine Player')
    player.set_folder_path('Opening')
    player.set_sequence(sequence)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.EditorLoadingAndSavingUtils.save_map(world, LEVEL)
    return {'keys': len(SHOTS), 'bound': len(sequence.get_bindings()), 'tracks': len(sequence.get_tracks()), 'actors': 126}


def cinema_assets():
    library = unreal.EditorAssetLibrary
    lib = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    root = pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
    report = {}
    import_file(str(root / 'Art/UI/T_UI_Title.png'), '/Game/UI')
    title = unreal.load_asset('/Game/UI/T_UI_Title')
    title.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    title.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    title.set_editor_property('never_stream', True)
    save(title)
    import_file(str(root / 'Art/UI/T_Sky_Space.png'), CINEMA)
    stars = unreal.load_asset(CINEMA + '/T_Sky_Space')
    stars.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    stars.set_editor_property('never_stream', True)
    save(stars)
    import_file(str(root / 'Art/Audio/S_Opening.wav'), CINEMA)
    # Unlit star sphere, mapped from view direction so its poles stay overhead and underfoot.
    path = CINEMA + '/M_Space'
    if library.does_asset_exist(path):
        library.delete_asset(path)
    material = tools.create_asset('M_Space', CINEMA, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    view = lib.create_material_expression(material, unreal.MaterialExpressionCameraVectorWS, -900, 0)
    mapping = lib.create_material_expression(material, unreal.MaterialExpressionCustom, -700, 0)
    mapping.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    mapping.set_editor_property('code', 'float3 d = normalize(-V); return float2(atan2(d.y, d.x) / 6.2831853 + 0.5, 0.5 - asin(d.z) / 3.1415927);')
    entry = unreal.CustomInput()
    entry.set_editor_property('input_name', 'V')
    mapping.set_editor_property('inputs', [entry])
    lib.connect_material_expressions(view, '', mapping, 'V')
    sample = lib.create_material_expression(material, unreal.MaterialExpressionTextureSample, -450, 0)
    sample.set_editor_property('texture', unreal.load_asset(CINEMA + '/T_Sky_Space'))
    lib.connect_material_expressions(mapping, '', sample, 'UVs')
    bright = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -200, 0)
    bright.set_editor_property('const_b', 1.7)
    lib.connect_material_expressions(sample, 'RGB', bright, 'A')
    lib.connect_material_property(bright, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    save(material)
    # Soft additive fireball; custom primitive data 0 fades it.
    path = CINEMA + '/M_Burst'
    if library.does_asset_exist(path):
        library.delete_asset(path)
    if True:
        material = tools.create_asset('M_Burst', CINEMA, unreal.Material, unreal.MaterialFactoryNew())
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
        fresnel = lib.create_material_expression(material, unreal.MaterialExpressionFresnel, -900, 0)
        fresnel.set_editor_property('exponent', 1.2)
        edge = lib.create_material_expression(material, unreal.MaterialExpressionOneMinus, -800, 0)
        lib.connect_material_expressions(fresnel, '', edge, '')
        soft = lib.create_material_expression(material, unreal.MaterialExpressionPower, -700, 0)
        soft.set_editor_property('const_exponent', 3.5)
        lib.connect_material_expressions(edge, '', soft, 'Base')
        fade = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -700, 200)
        fade.set_editor_property('parameter_name', 'Fade')
        fade.set_editor_property('default_value', 1)
        fade.set_editor_property('use_custom_primitive_data', True)
        fade.set_editor_property('primitive_data_index', 0)
        shaped = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -450, 80)
        lib.connect_material_expressions(soft, '', shaped, 'A')
        lib.connect_material_expressions(fade, '', shaped, 'B')
        colour = lib.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -450, 300)
        colour.set_editor_property('constant', unreal.LinearColor(16, 5.5, 1.3, 1))
        lit = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -200, 150)
        lib.connect_material_expressions(shaped, '', lit, 'A')
        lib.connect_material_expressions(colour, '', lit, 'B')
        lib.connect_material_property(lit, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.recompile_material(material)
        save(material)
    for stem in ('T_Ship_Human_D', 'T_Ship_Human_E', 'T_Ship_First_D', 'T_Ship_First_E'):
        import_file(str(root / 'Art/UI' / (stem + '.png')), CINEMA)
    # Textured hull plating; emissive holds the windows and crystal veins.
    path = CINEMA + '/M_Ship'
    if not library.does_asset_exist(path):
        material = tools.create_asset('M_Ship', CINEMA, unreal.Material, unreal.MaterialFactoryNew())
        base = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -800, 0)
        base.set_editor_property('parameter_name', 'Base')
        base.set_editor_property('texture', unreal.load_asset(CINEMA + '/T_Ship_Human_D'))
        light = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -800, 300)
        light.set_editor_property('parameter_name', 'Light')
        light.set_editor_property('texture', unreal.load_asset(CINEMA + '/T_Ship_Human_E'))
        tint = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -500, -150)
        tint.set_editor_property('parameter_name', 'Tint')
        tint.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
        tinted = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -300, 0)
        lib.connect_material_expressions(base, 'RGB', tinted, 'A')
        lib.connect_material_expressions(tint, '', tinted, 'B')
        lift = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -300, 150)
        lift.set_editor_property('const_b', .22)
        lib.connect_material_expressions(tinted, '', lift, 'A')
        power = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, 450)
        power.set_editor_property('parameter_name', 'LightPower')
        power.set_editor_property('default_value', 8)
        lit = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -300, 330)
        lib.connect_material_expressions(light, 'RGB', lit, 'A')
        lib.connect_material_expressions(power, '', lit, 'B')
        total = lib.create_material_expression(material, unreal.MaterialExpressionAdd, -120, 250)
        lib.connect_material_expressions(lift, '', total, 'A')
        lib.connect_material_expressions(lit, '', total, 'B')
        lib.connect_material_property(tinted, '', unreal.MaterialProperty.MP_BASE_COLOR)
        lib.connect_material_property(total, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.recompile_material(material)
        save(material)
    ship = unreal.load_asset(CINEMA + '/M_Ship')
    for name, base, light, tint, power in (('MI_ShipHuman', 'T_Ship_Human_D', 'T_Ship_Human_E', (1, 1, 1), 8), ('MI_ShipTrim', 'T_Ship_Human_D', 'T_Ship_Human_E', (.42, .45, .52), 8),
                                           ('MI_ShipFirst', 'T_Ship_First_D', 'T_Ship_First_E', (1, 1, 1), 14)):
        path = CINEMA + '/' + name
        instance = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset(name, CINEMA, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(instance, ship)
        lib.set_material_instance_texture_parameter_value(instance, 'Base', unreal.load_asset(CINEMA + '/' + base))
        lib.set_material_instance_texture_parameter_value(instance, 'Light', unreal.load_asset(CINEMA + '/' + light))
        lib.set_material_instance_vector_parameter_value(instance, 'Tint', unreal.LinearColor(*tint, 1))
        lib.set_material_instance_scalar_parameter_value(instance, 'LightPower', power)
        lib.update_material_instance(instance)
        save(instance)
    parent = glow_material()
    for name, (colour, glow, rough) in CINEMA_LOOKS.items():
        path = CINEMA + '/' + name
        instance = unreal.load_asset(path) if library.does_asset_exist(path) else tools.create_asset(name, CINEMA, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(instance, parent)
        lib.set_material_instance_vector_parameter_value(instance, 'Colour', unreal.LinearColor(*colour, 1))
        lib.set_material_instance_vector_parameter_value(instance, 'Glow', unreal.LinearColor(*glow, 1))
        lib.set_material_instance_scalar_parameter_value(instance, 'Roughness', rough)
        lib.update_material_instance(instance)
        save(instance)
    for stem in ('SM_Ship_Cruiser', 'SM_Ship_Frigate', 'SM_Ship_Vigil', 'SM_Ship_Shard', 'SM_Station_Hull'):
        options = unreal.FbxImportUI()
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_as_skeletal', False)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
        options.static_mesh_import_data.set_editor_property('combine_meshes', True)
        options.static_mesh_import_data.set_editor_property('import_uniform_scale', .01)
        import_file(str(root / 'Art/Meshes' / (stem + '.fbx')), CINEMA, options)
        mesh = unreal.load_asset(CINEMA + '/' + stem)
        for index, slot in enumerate(mesh.get_editor_property('static_materials')):
            mesh.set_material(index, unreal.load_asset(CINEMA + '/' + SLOTS.get(str(slot.get_editor_property('material_slot_name')), 'MI_Hull')))
        save(mesh)
        report[stem] = [round(v) for v in mesh.get_bounding_box().max.to_tuple()]
    from editor_toolset.toolsets.actor import ActorTools
    subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    plans = (('BP_FleetShip', '/Game/Cinematics/SM_Ship_Cruiser', None), ('BP_Burst', '/Engine/BasicShapes/Sphere', CINEMA + '/M_Burst'),
             ('BP_BoltTeal', '/Engine/BasicShapes/Cube', CINEMA + '/MI_CrystalGlow'), ('BP_BattleDirector', None, None))
    for name, mesh, look in plans:
        path = BLUEPRINTS + '/' + name
        if library.does_asset_exist(path):
            continue
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = tools.create_asset(name, BLUEPRINTS, unreal.Blueprint, factory)
        if mesh:
            root_part = None
            for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
                data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
                obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
                if isinstance(obj, unreal.SceneComponent):
                    root_part = obj
            part = ActorTools.add_component(root_part, unreal.StaticMeshComponent.static_class(), 'Shape')
            part.set_static_mesh(unreal.load_asset(mesh))
            part.set_collision_profile_name('NoCollision')
            part.set_editor_property('cast_shadow', False)
            if look:
                part.set_material(0, unreal.load_asset(look))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(unreal.load_asset(BLUEPRINTS + '/BP_Burst')):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
        if isinstance(obj, unreal.StaticMeshComponent):
            obj.set_material(0, unreal.load_asset(CINEMA + '/M_Burst'))
    unreal.BlueprintEditorLibrary.compile_blueprint(unreal.load_asset(BLUEPRINTS + '/BP_Burst'))
    save(unreal.load_asset(BLUEPRINTS + '/BP_Burst'))
    bolt = unreal.load_asset(BLUEPRINTS + '/BP_BoltTeal')
    unreal.get_default_object(bolt.generated_class()).set_editor_property('initial_life_span', .16)
    save(bolt)
    return report


def execute(operation):
    if operation == 'inspect':
        return inspect()
    if operation == 'components':
        bp = unreal.load_asset(CHARACTER)
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        rows = []
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj, unreal.ActorComponent):
                row = {'name': obj.get_name(), 'class': obj.get_class().get_name()}
                if isinstance(obj, unreal.SceneComponent):
                    parent = obj.get_attach_parent()
                    row['parent'] = parent.get_name() if parent else None
                rows.append(row)
        seen = []
        for row in rows:
            if row not in seen:
                seen.append(row)
        return json.dumps(seen)
    if operation == 'montages':
        return json.dumps(make_montages())
    if operation == 'game_mode':
        return json.dumps(game_mode())
    if operation == 'build_level':
        return json.dumps(build_level())
    if operation == 'pie_state':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return json.dumps({'pie': False})
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        if not pawn:
            return json.dumps({'pie': True, 'pawn': None, 'level': worlds[0].get_name()})
        parts = {c.get_name(): c for c in pawn.get_components_by_class(unreal.SceneComponent)}
        body = parts.get('Body')
        katana = parts.get('Katana')
        anim = body.get_anim_instance() if body else None
        velocity = pawn.get_velocity()
        return json.dumps({'pie': True, 'pawn': pawn.get_class().get_name(),
                           'controlled': bool(pawn.get_controller()),
                           'location': [round(v) for v in pawn.get_actor_location().to_tuple()],
                           'speed': round(velocity.length()), 'on_ground': pawn.character_movement.is_moving_on_ground(),
                           'anim': anim.get_class().get_name() if anim else None,
                           'montage': bool(anim.is_any_montage_playing()) if anim else None,
                           'input_vector': [round(v, 2) for v in pawn.get_last_movement_input_vector().to_tuple()],
                           'facing': [round(v) for v in pawn.get_actor_rotation().to_tuple()],
                           'katana_parent': katana.get_attach_parent().get_name() if katana and katana.get_attach_parent() else None,
                           'katana_socket': str(katana.get_attach_socket_name()) if katana else None})
    if operation.startswith('pie_call:'):
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        pawn.call_method(operation.split(':', 1)[1])
        return json.dumps({'called': operation})
    if operation == 'pie_keys':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pc = unreal.GameplayStatics.get_player_controller(worlds[0], 0)
        def make(name):
            key = unreal.Key()
            key.set_editor_property('key_name', name)
            return key
        down = [n for n in ('W', 'A', 'S', 'D', 'Up', 'Down', 'Left', 'Right', 'LeftShift', 'Gamepad_FaceButton_Bottom') if pc.is_input_key_down(make(n))]
        analog = {n: round(pc.get_input_analog_key_state(make(n)), 3) for n in ('Gamepad_LeftX', 'Gamepad_LeftY', 'Gamepad_RightX', 'Gamepad_RightY')}
        return json.dumps({'down': down, 'analog': analog})
    if operation == 'preview_katana':
        # Places a temporary BP_Physis in the editor level to check the grip by eye.
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = actors.spawn_actor_from_class(unreal.load_asset(CHARACTER).generated_class(), unreal.Vector(300, 0, 100))
        actor.set_actor_label('Physis_Preview_Temporary')
        parts = {c.get_name(): c for c in actor.get_components_by_class(unreal.SceneComponent)}
        body = parts['Body']
        body.override_animation_data(unreal.load_asset('/Game/Characters/Physis/Animations/Katana/Physis_AS_HK_Slash1'), False, False, .45, 0)
        for name, component in parts.items():
            if isinstance(component, unreal.SkeletalMeshComponent) and name != 'Body':
                component.set_leader_pose_component(body, True, False)
        parts['Katana'].attach_to_component(body, 'hand_r', unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, False)
        parts['Hair'].attach_to_component(body, 'head', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False) if False else None
        return json.dumps({'actor': actor.get_actor_label(), 'katana_world': [round(v) for v in parts['Katana'].get_world_location().to_tuple()],
                           'hand': [round(v) for v in body.get_socket_location('hand_r').to_tuple()]})
    if operation == 'clear_preview':
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        removed = 0
        for actor in actors.get_all_level_actors():
            if actor.get_actor_label() == 'Physis_Preview_Temporary':
                actors.destroy_actor(actor);removed += 1
        return json.dumps({'removed': removed})
    if operation == 'lock_roots':
        # Her Body is not the Character's main mesh, so root motion would pull the
        # body away from the capsule. Attacks play in place instead.
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        locked = 0
        for data in registry.get_assets_by_path('/Game/Characters/Physis/Animations/Katana', recursive=False):
            if str(data.asset_class_path.asset_name) == 'AnimSequence':
                clip = data.get_asset()
                clip.set_editor_property('force_root_lock', True)
                save(clip);locked += 1
        return json.dumps({'locked': locked})
    if operation == 'pie_parts':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        parts = {c.get_name(): c for c in pawn.get_components_by_class(unreal.SceneComponent)}
        body = parts['Body']
        head = body.get_socket_location('head')
        hand = body.get_socket_location('hand_r')
        centre = pawn.get_actor_location()
        def gap(a, b):
            return round(((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** .5, 1)
        return json.dumps({'head_to_capsule': gap(head, centre), 'hair_to_head': gap(parts['Hair'].get_world_location(), head),
                           'hair_parent': parts['Hair'].get_attach_parent().get_name(), 'hair_socket': str(parts['Hair'].get_attach_socket_name()),
                           'katana_to_hand': gap(parts['Katana'].get_world_location(), hand),
                           'katana_visible': parts['Katana'].is_visible()})
    if operation.startswith('pie_hold:'):
        # Holds forward like a pressed key and records foot movement for N seconds.
        seconds = float(operation.split(':')[1])
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        parts = {c.get_name(): c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent)}
        body, outfit = parts['Body'], parts['SkeletalMesh']
        state = {'left': seconds, 'samples': []}
        def local(component, bone):
            world = component.get_socket_location(bone)
            centre = pawn.get_actor_location()
            right = pawn.get_actor_right_vector()
            forward = pawn.get_actor_forward_vector()
            delta = world - centre
            return round(delta.dot(forward), 1), round(delta.z, 1)
        def finish():
            unreal.unregister_slate_post_tick_callback(state['handle'])
            import pathlib
            pathlib.Path(unreal.Paths.project_saved_dir(), 'Connection', 'pie_hold.json').write_text(json.dumps(state['samples']))
        def tick(dt):
            try:
                step(dt)
            except Exception as error:
                state['samples'].append({'error': str(error)})
                finish()
        def step(dt):
            state['left'] -= dt
            pawn.add_movement_input(unreal.Vector(1, 0, 0), 1, True)
            if int(state['left'] * 8) != state.get('last'):
                state['last'] = int(state['left'] * 8)
                anim = body.get_anim_instance()
                state['samples'].append({'foot_l': local(body, 'foot_l'), 'foot_r': local(body, 'foot_r'),
                                         'outfit_foot_l': local(outfit, 'foot_l'),
                                         'speed': anim.get_editor_property('GroundSpeed'),
                                         'move': anim.get_editor_property('ShouldMove'),
                                         'character': bool(anim.get_editor_property('Character')),
                                         'component': bool(anim.get_editor_property('MovementComponent')),
                                         'accel': round(pawn.character_movement.get_current_acceleration().length()),
                                         'mode': str(body.get_editor_property('animation_mode')),
                                         'anim_tick': str(body.get_editor_property('visibility_based_anim_tick_option'))})
            if state['left'] <= 0:
                finish()
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
        return json.dumps({'holding': seconds})
    if operation == 'inspect_blendspace':
        report = {}
        for path in ('/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run', '/Game/Characters/Physis/Animations/AnimBP/Physis_BS_Idle_Walk_Run'):
            space = unreal.load_asset(path)
            samples = []
            for sample in space.get_editor_property('sample_data'):
                anim = sample.get_editor_property('animation')
                samples.append((anim.get_name() if anim else None, str(sample.get_editor_property('sample_value'))[-44:]))
            report[space.get_name()] = {'skeleton': space.get_editor_property('skeleton').get_name(), 'samples': samples,
                                        'attrs': [x for x in dir(space) if 'axis' in x.lower() or 'blend_param' in x.lower()]}
        return json.dumps(report)
    if operation == 'pie_anim':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        parts = {c.get_name(): c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent)}
        anim = parts['Body'].get_anim_instance()
        report = {'state_api': [x for x in dir(anim) if 'state' in x.lower() or 'relevant' in x.lower()]}
        for name, call in (('main', lambda: anim.get_current_state_name(anim.get_state_machine_index('Main States'))),
                           ('locomotion', lambda: anim.get_current_state_name(anim.get_state_machine_index('Locomotion')))):
            try:
                report[name] = str(call())
            except Exception as error:
                report[name] = 'error: ' + str(error)[:120]
        report['tick'] = {n: str(parts[n].get_editor_property('visibility_based_anim_tick_option')) for n in ('Body', 'Face')}
        report['pause'] = parts['Body'].get_editor_property('pause_anims')
        report['lod'] = parts['Body'].get_predicted_lod_level() if hasattr(parts['Body'], 'get_predicted_lod_level') else None
        return json.dumps(report)
    if operation.startswith('clip:'):
        # clip:PATH:SECONDS poses a temporary BP_Physis and reports its feet.
        _, path, seconds = operation.split(':')
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == 'Physis_Preview_Temporary'), None)
        if not actor:
            actor = actors.spawn_actor_from_class(unreal.load_asset(CHARACTER).generated_class(), unreal.Vector(300, 0, 100))
            actor.set_actor_label('Physis_Preview_Temporary')
        body = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        clip = unreal.load_asset('/Game/Characters/Physis/Animations/' + path)
        if not clip:
            return json.dumps({'missing': path})
        body.override_animation_data(clip, False, False, float(seconds), 0)
        body.set_update_animation_in_editor(True)
        body.tick_pose(0.016, False) if hasattr(body, 'tick_pose') else None
        return json.dumps({'clip': clip.get_name(), 'length': round(clip.get_play_length(), 2), 'mode': str(body.get_editor_property('animation_mode'))})
    if operation == 'clip_read':
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == 'Physis_Preview_Temporary')
        body = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        return json.dumps({n: [round(v, 1) for v in body.get_socket_location(n).to_tuple()] for n in ('foot_l', 'foot_r')})
    if operation == 'clip_motion':
        # Reads foot positions straight from the animation data, with no viewport.
        report = {}
        ext = unreal.AnimPoseExtensions
        for label, path in (('source', '/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd'),
                            ('library', '/Game/Characters/Physis/Animations/Physis_MF_Unarmed_Jog_Fwd'),
                            ('animbp', '/Game/Characters/Physis/Animations/AnimBP/Physis_MF_Unarmed_Jog_Fwd'),
                            ('idle', '/Game/Characters/Physis/Animations/AnimBP/Physis_MM_Idle')):
            clip = unreal.load_asset(path)
            rows = []
            length = clip.get_play_length()
            for fraction in (0, .25, .5, .75):
                pose = ext.get_anim_pose_at_time(clip, length * fraction, unreal.AnimPoseEvaluationOptions())
                foot = ext.get_bone_pose(pose, 'foot_l', unreal.AnimPoseSpaces.WORLD)
                rows.append([round(v, 1) for v in foot.translation.to_tuple()])
            report[label] = {'length': round(length, 2), 'foot_l': rows, 'root_lock': clip.get_editor_property('force_root_lock')}
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        deps = registry.get_dependencies('/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed', unreal.AssetRegistryDependencyOptions())
        report['abp_uses'] = sorted(str(d) for d in deps if 'Anim' in str(d) or 'BS_' in str(d))[:30]
        return json.dumps(report)
    if operation == 'save_animbp':
        asset = unreal.load_asset('/Game/Characters/Physis/Animations/AnimBP/Physis_ABP_Unarmed')
        unreal.BlueprintEditorLibrary.compile_blueprint(asset)
        save(asset)
        return json.dumps({'saved': True})
    if operation == 'run_speed':
        bp = unreal.load_asset(CHARACTER)
        cdo = unreal.get_default_object(bp.generated_class())
        cdo.get_editor_property('character_movement').set_editor_property('max_walk_speed', 500)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        return json.dumps({'default': unreal.get_default_object(bp.generated_class()).get_editor_property('character_movement').get_editor_property('max_walk_speed')})
    if operation == 'disk_check':
        import os
        root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
        out = {}
        for rel in ('Input/IMC_Default.uasset', 'Characters/Physis/Blueprints/BP_Physis.uasset', 'Characters/Physis/Blueprints/BP_PhysisGameMode.uasset'):
            out[rel] = os.path.getmtime(root + rel)
        mode = unreal.load_asset(BLUEPRINTS + '/BP_PhysisGameMode')
        char = unreal.load_asset(CHARACTER)
        out['hud'] = unreal.get_default_object(mode.generated_class()).get_editor_property('hud_class').get_name()
        out['run'] = unreal.get_default_object(char.generated_class()).get_editor_property('character_movement').get_editor_property('max_walk_speed')
        return json.dumps(out)
    if operation == 'tutorial_assets':
        return json.dumps(create_tutorial_assets())
    if operation == 'trigger_box':
        from editor_toolset.toolsets.actor import ActorTools
        bp = unreal.load_asset(BLUEPRINTS + '/BP_TutorialTrigger')
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        names = {}
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj, unreal.ActorComponent):
                names[obj.get_name()] = obj
        if not any(n.startswith('Zone') for n in names):
            root = next((o for n, o in names.items() if isinstance(o, unreal.SceneComponent)), None)
            box = ActorTools.add_component(root, unreal.BoxComponent.static_class(), 'Zone') if root else None
            if not box:
                raise RuntimeError('No root component in ' + str(list(names)))
            box.set_editor_property('box_extent', unreal.Vector(300, 300, 200))
            box.set_collision_profile_name('Trigger')
        unreal.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
        return json.dumps({'components': list(names)})
    if operation == 'place_tutorials':
        return json.dumps(place_tutorials())
    if operation.startswith('pie_visit:'):
        # Moves her into a zone and reports the prompt the HUD then holds.
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        controller = unreal.GameplayStatics.get_player_controller(worlds[0], 0)
        location = TUTORIALS[int(operation.split(':')[1])][1]
        pawn.set_actor_location(unreal.Vector(location[0], location[1], 95), False, True)
        return json.dumps({'hud': controller.get_hud().get_class().get_name()})
    if operation == 'pie_prompt':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        controller = unreal.GameplayStatics.get_player_controller(worlds[0], 0)
        hud = controller.get_hud()
        mode = unreal.GameplayStatics.get_game_mode(worlds[0])
        if hud.get_class().get_name() != 'BP_PhysisHUD_C':
            return json.dumps({'hud_class': hud.get_class().get_name(), 'mode': mode.get_class().get_name() if mode else None,
                               'mode_hud': mode.get_editor_property('hud_class').get_name() if mode else None,
                               'pawn': mode.get_editor_property('default_pawn_class').get_name() if mode else None})
        return json.dumps({'text': hud.get_editor_property('TutorialText'), 'hide_at': round(hud.get_editor_property('TutorialHideAt'), 1),
                           'time': round(unreal.GameplayStatics.get_time_seconds(worlds[0]), 1)})
    if operation == 'set_hud':
        mode = unreal.load_asset(BLUEPRINTS + '/BP_PhysisGameMode')
        hud = unreal.load_asset(BLUEPRINTS + '/BP_PhysisHUD')
        unreal.BlueprintEditorLibrary.compile_blueprint(mode)
        cdo = unreal.get_default_object(mode.generated_class())
        cdo.modify()
        cdo.set_editor_property('hud_class', hud.generated_class())
        mode.modify()
        unreal.EditorAssetLibrary.save_asset(BLUEPRINTS + '/BP_PhysisGameMode', only_if_is_dirty=False)
        return json.dumps({'hud': unreal.get_default_object(mode.generated_class()).get_editor_property('hud_class').get_name()})
    if operation == 'save_hud':
        hud = unreal.load_asset(BLUEPRINTS + '/BP_PhysisHUD')
        unreal.BlueprintEditorLibrary.compile_blueprint(hud)
        unreal.EditorAssetLibrary.save_asset(BLUEPRINTS + '/BP_PhysisHUD', only_if_is_dirty=False)
        unreal.EditorAssetLibrary.save_asset(BLUEPRINTS + '/BP_TutorialTrigger', only_if_is_dirty=False)
        return json.dumps({'saved': True})
    if operation == 'input_report':
        imc = unreal.load_asset('/Game/Input/IMC_Default')
        rows = [(m.action.get_name(), key_name(m.key)) for m in
                imc.get_editor_property('default_key_mappings').get_editor_property('mappings')]
        return json.dumps({'mappings': rows[12:], 'count': len(rows),
                           'subsystem': [x for x in dir(unreal) if 'EnhancedInput' in x and 'Subsystem' in x],
                           'inject': [x for x in dir(unreal.EnhancedInputLocalPlayerSubsystem) if 'inject' in x or 'has_mapping' in x]})
    if operation.startswith('pie_inject:'):
        # pie_inject:IA_Attack sends the action through Enhanced Input, like a press.
        name = operation.split(':')[1]
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        controller = unreal.GameplayStatics.get_player_controller(worlds[0], 0)
        subsystem = unreal.EnhancedInputLibrary.get_local_player_subsystem(controller) if hasattr(unreal, 'EnhancedInputLibrary') and hasattr(unreal.EnhancedInputLibrary, 'get_local_player_subsystem') else None
        return json.dumps({'subsystem': str(subsystem), 'library': [x for x in dir(unreal.EnhancedInputLibrary) if not x.startswith('_')][:30] if hasattr(unreal, 'EnhancedInputLibrary') else None})
    if operation == 'gameplay_assets':
        return json.dumps(create_gameplay_assets())
    if operation == 'save_gameplay':
        for name in ('BP_ScanTarget', 'BP_TrainingDrone', 'BP_StationDoor', 'BP_Pickup', 'BP_GunTracer', 'BP_FleetShip', 'BP_Burst', 'BP_BattleDirector', 'BP_BoltTeal', 'BP_Physis'):
            bp = unreal.load_asset(BLUEPRINTS + '/' + name)
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            save(bp)
        drone = unreal.load_asset(BLUEPRINTS + '/BP_TrainingDrone')
        unreal.get_default_object(drone.generated_class()).set_editor_property('Health', 6)
        save(drone)
        physis = unreal.load_asset(BLUEPRINTS + '/BP_Physis')
        defaults = unreal.get_default_object(physis.generated_class())
        for name, value in (('PhysisHealth', 10), ('GunAmmo', 12), ('GunReserve', 24), ('Divinity', 0)):
            defaults.set_editor_property(name, value)
        save(physis)
        return json.dumps({'saved': True})
    if operation == 'place_gameplay':
        return json.dumps(place_gameplay())
    if operation == 'pie_world':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        drones = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if 'BP_TrainingDrone' in a.get_class().get_name()]
        doors = {a.get_actor_label() if hasattr(a, 'get_actor_label') else a.get_name(): not a.get_actor_enable_collision()
                 for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if 'BP_StationDoor' in a.get_class().get_name()}
        body = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        anim = body.get_anim_instance()
        hud = unreal.GameplayStatics.get_player_controller(world, 0).get_hud()
        return json.dumps({'location': [round(v) for v in pawn.get_actor_location().to_tuple()], 'drones': [d.get_editor_property('Health') for d in drones],
                           'doors': doors, 'montage': bool(anim.is_any_montage_playing()), 'prompt': hud.get_editor_property('TutorialText')})
    if operation.startswith('pie_goto:'):
        _, x, y = operation.split(':')
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        pawn.set_actor_location(unreal.Vector(float(x), float(y), 95), False, True)
        return json.dumps({'at': [x, y]})
    if operation.startswith('pie_face:'):
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        yaw = float(operation.split(':')[1])
        pawn.set_actor_rotation(unreal.Rotator(0, 0, yaw), True)
        controller = unreal.GameplayStatics.get_player_controller(worlds[0], 0)
        controller.set_control_rotation(unreal.Rotator(0, 0, yaw))
        return json.dumps({'yaw': yaw})
    if operation == 'visor_setup':
        # The visor drains and cools the picture through the follow camera.
        camera = template('FollowCamera')
        look = camera.get_editor_property('post_process_settings')
        look.set_editor_property('override_color_saturation', True)
        look.set_editor_property('color_saturation', unreal.Vector4(.35, .6, .7, 1))
        look.set_editor_property('override_color_gain', True)
        look.set_editor_property('color_gain', unreal.Vector4(.85, 1.05, 1.1, 1))
        camera.set_editor_property('post_process_settings', look)
        camera.set_editor_property('post_process_blend_weight', 0)
        keys = input_actions()
        placed = place_gameplay()
        tutorials = place_tutorials()
        return json.dumps({'keys': keys[-14:], 'placed': str(placed), 'tutorials': str(tutorials)})
    if operation == 'pie_visor':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        hud = unreal.GameplayStatics.get_player_controller(world, 0).get_hud()
        rows = {}
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if 'BP_ScanTarget' in actor.get_class().get_name():
                seen, aimed, done = (actor.get_editor_property(n) for n in ('ScanInView', 'ScanAimed', 'ScanDone'))
                if seen or aimed or done:
                    rows[actor.get_actor_label()] = [seen, aimed, done, round(actor.get_editor_property('ScanProgress'), 2), round(actor.get_editor_property('ScanAimDot'), 3)]
        return json.dumps({'on': pawn.get_editor_property('ScanVisorOn'), 'held': pawn.get_editor_property('ScanHeld'),
                           'blend': round(pawn.get_editor_property('VisorBlend'), 2), 'best': round(pawn.get_editor_property('VisorBest'), 3),
                           'count': [hud.get_editor_property('LogbookDone'), hud.get_editor_property('LogbookSeen')],
                           'result': hud.get_editor_property('ScanResult'), 'targets': rows})
    if operation.startswith('pie_shot'):
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        unreal.SystemLibrary.execute_console_command(worlds[0], 'Shot showui')
        return json.dumps({'shot': True})
    if operation == 'combat_clips':
        made = make_montages()
        folder = '/Game/Characters/Physis/Animations/Katana/Montages/'
        rows = {}
        for path in made:
            montage = unreal.load_asset(path)
            rows[path.split('/')[-1].replace('AM_Physis_', '')] = round(montage.get_play_length(), 2)
        return json.dumps(rows)
    if operation == 'pie_combat':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        body = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        active = body.get_anim_instance().get_current_active_montage()
        target = pawn.get_editor_property('LockTarget')
        drones = [a.get_editor_property('Health') for a in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.Actor) if 'BP_TrainingDrone' in a.get_class().get_name()]
        return json.dumps({'t': round(unreal.GameplayStatics.get_time_seconds(worlds[0]), 2), 'clip': active.get_name().replace('AM_Physis_', '') if active else None, 'step': pawn.get_editor_property('ChainStep'),
                           'skill': pawn.get_editor_property('SkillLevel'), 'gun': pawn.get_editor_property('GunEquipped'), 'ammo': [pawn.get_editor_property('GunAmmo'), pawn.get_editor_property('GunReserve')], 'div': pawn.get_editor_property('Divinity'), 'hp': pawn.get_editor_property('PhysisHealth'), 'dead': pawn.get_editor_property('PhysisDead'),
                           'lock': target.get_actor_label() if target else None, 'yaw': round(pawn.get_actor_rotation().yaw),
                           'at': [round(v) for v in pawn.get_actor_location().to_tuple()], 'drones': drones})
    if operation.startswith('pie_hurt:'):
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        pawn.call_method('PhysisHurt', (operation.split(':')[1] == 'front',))
        return json.dumps({'hurt': True})
    if operation == 'pie_jump':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        pawn.jump()
        return json.dumps({'jumped': True})
    if operation.startswith('pie_mash'):
        # Presses attack every frame for four seconds and records when each clip starts.
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        body = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        import pathlib
        # pie_mash:SECONDS presses attack for that many real seconds (default 4).
        state = {'left': float(operation.split(':')[1]) if ':' in operation else 4.0, 'last': None, 'log': []}
        def tick(dt):
            try:
                state['left'] -= dt
                pawn.call_method('PhysisAttack')
                active = body.get_anim_instance().get_current_active_montage()
                name = active.get_name() if active else None
                if name != state['last']:
                    state['last'] = name
                    state['log'].append([round(unreal.GameplayStatics.get_time_seconds(worlds[0]), 2), name])
                if state['left'] > 0:
                    return
            except Exception as error:
                state['log'].append(str(error))
            unreal.unregister_slate_post_tick_callback(state['handle'])
            pathlib.Path(unreal.Paths.project_saved_dir(), 'Connection', 'pie_mash.json').write_text(json.dumps(state['log']))
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
        return json.dumps({'mashing': True})
    if operation == 'ui_import':
        return json.dumps(ui_import())
    if operation == 'pistol_stance':
        return json.dumps(pistol_stance())
    if operation == 'combat_assets':
        return json.dumps(combat_assets())
    if operation == 'dress_props':
        for name, look in (('BP_TrainingDrone', 'MI_Item_Dark'), ('BP_StationDoor', 'MI_Item_Dark'), ('BP_ScanTarget', 'MI_Item_Glow')):
            bp = unreal.load_asset(BLUEPRINTS + '/' + name)
            subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
            for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
                data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
                obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
                if isinstance(obj, unreal.StaticMeshComponent):
                    obj.set_material(0, unreal.load_asset('/Game/Gameplay/' + look))
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            save(bp)
        return json.dumps({'dressed': True})
    if operation == 'pie_gun':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        gun = next(c for c in pawn.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'Gun')
        body = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        centre = pawn.get_actor_location()
        offset = lambda v: [round(n, 1) for n in (v - centre).to_tuple()]
        controller = unreal.GameplayStatics.get_player_controller(worlds[0], 0)
        return json.dumps({'actor_fwd': [round(n, 2) for n in pawn.get_actor_forward_vector().to_tuple()], 'gun_fwd': [round(n, 2) for n in gun.get_forward_vector().to_tuple()],
                           'gun_up': [round(n, 2) for n in gun.get_up_vector().to_tuple()], 'gun_at': offset(gun.get_world_location()), 'hand': offset(body.get_socket_location('hand_r')), 'head': offset(body.get_socket_location('head')),
                           'control_yaw': round(controller.get_control_rotation().yaw), 'visible': gun.is_visible()})
    if operation == 'pie_gun_solve':
        # Finds the hand-relative grip that levels the gun along her aim in the idle stance.
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        gun = next(c for c in pawn.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'Gun')
        body = next(c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        hand = body.get_socket_transform('hand_r')
        wanted = unreal.Transform(gun.get_world_location(), pawn.get_actor_rotation(), unreal.Vector(1, 1, 1))
        grip = wanted.make_relative(hand)
        turn = grip.rotation.rotator()
        return json.dumps({'location': [round(n, 2) for n in grip.translation.to_tuple()], 'rotator': [round(turn.roll, 2), round(turn.pitch, 2), round(turn.yaw, 2)]})
    if operation.startswith('gun_grip:'):
        values = [float(n) for n in operation.split(':')[1].split(',')]
        gun = template('Gun')
        gun.set_editor_property('relative_location', unreal.Vector(*values[:3]))
        gun.set_editor_property('relative_rotation', unreal.Rotator(*values[3:]))
        bp = unreal.load_asset(CHARACTER)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        return json.dumps({'grip': values})
    if operation == 'cinema_assets':
        return json.dumps(cinema_assets())
    if operation == 'pie_cam':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        camera = next(c for c in pawn.get_components_by_class(unreal.CameraComponent))
        turn = camera.get_world_rotation()
        return json.dumps({'loc': [round(v, 1) for v in camera.get_world_location().to_tuple()], 'pitch': round(turn.pitch, 2), 'yaw': round(turn.yaw, 2), 'fov': camera.get_editor_property('field_of_view')})
    if operation == 'mesh_bounds':
        mesh = unreal.load_asset('/Engine/EngineSky/SM_SkySphere')
        return json.dumps({'sky': str(mesh), 'max': [round(v) for v in mesh.get_bounding_box().max.to_tuple()] if mesh else None})
    if operation == 'cinema_place':
        return json.dumps(cinema_place())
    if operation == 'pie_view':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        manager = unreal.GameplayStatics.get_player_camera_manager(worlds[0], 0)
        return json.dumps({'worlds': len(worlds), 't': round(unreal.GameplayStatics.get_time_seconds(worlds[0]), 1), 'at': [round(v) for v in manager.get_camera_location().to_tuple()], 'yaw': round(manager.get_camera_rotation().yaw)})
    if operation == 'door_lock':
        # The door's lock flag is DoorLocked: a variable named Locked resolves to Slider's getter.
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if actor.get_actor_label() == 'Door Sealed':
                actor.set_editor_property('DoorLocked', True)
        unreal.EditorLevelLibrary.save_current_level()
        return json.dumps({'locked': True})
    if operation == 'pie_dodge':
        # Two dodge presses at once, then the travel speed right after the launch.
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        pawn.call_method('PhysisDodge')
        pawn.call_method('PhysisDodge')
        montage = unreal.load_asset('/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Dodge')
        return json.dumps({'dodge_seconds': round(montage.get_play_length(), 2), 'pending': pawn.get_velocity().length()})
    if operation == 'pie_side':
        # Holds sideways like a pressed key and dodges partway through.
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        state = {'left': .5, 'dodged': False}
        def tick(dt):
            try:
                state['left'] -= dt
                pawn.add_movement_input(unreal.Vector(0, 1, 0), 1, True)
                if state['left'] < .3 and not state['dodged']:
                    state['dodged'] = True
                    pawn.call_method('PhysisDodge')
                if state['left'] > 0:
                    return
            except Exception:
                pass
            unreal.unregister_slate_post_tick_callback(state['handle'])
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
        return json.dumps({'holding': True})
    if operation == 'pie_spam':
        # Five attack presses in the same instant: only the first may land.
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        for _ in range(5):
            pawn.call_method('PhysisAttack')
        montage = unreal.load_asset('/Game/Characters/Physis/Animations/Katana/Montages/AM_Physis_Slash')
        return json.dumps({'slash_seconds': round(montage.get_play_length(), 2)})
    if operation == 'pie_walk':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        pawn = unreal.GameplayStatics.get_player_pawn(worlds[0], 0)
        pawn.add_movement_input(unreal.Vector(1, 0, 0), 1, True)
        return json.dumps({'walk': True})
    if operation == 'input_actions':
        return json.dumps(input_actions())
    if operation == 'setup_components':
        return json.dumps(setup_components())
    if operation == 'create_character':
        return create_character()
    raise ValueError('Unknown Physis gameplay operation: ' + operation)
