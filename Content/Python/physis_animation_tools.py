"""Fixed animation production steps for Physis."""
import json
import unreal

ROOT = '/Game/Characters/Physis/Animations'
SOURCE_MESH = '/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple'
TARGET_MESH = '/Game/MetaHumans/MH_Physis/Body/SKM_MH_Physis_BodyMesh'
TEST_SET = ('MM_Idle', 'MF_Unarmed_Walk_Fwd', 'MF_Unarmed_Jog_Fwd', 'MM_Jump', 'MM_Fall_Loop', 'MM_Land', 'MM_Attack_01')


def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset):
        raise RuntimeError('Could not save ' + asset.get_path_name())


def make_rig(name, mesh):
    path = ROOT + '/Retarget/' + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    rig = unreal.IKRigDefinitionFactory.create_new_ik_rig_asset(ROOT + '/Retarget', name)
    controller = unreal.IKRigController.get_controller(rig)
    if not controller.set_skeletal_mesh(mesh):
        raise RuntimeError('Mesh rejected by ' + name)
    controller.apply_auto_generated_retarget_definition()
    controller.apply_auto_fbik()
    save(rig)
    return rig


def make_retargeter():
    source_mesh = unreal.load_asset(SOURCE_MESH)
    target_mesh = unreal.load_asset(TARGET_MESH)
    source = make_rig('IK_Quinn', source_mesh)
    target = make_rig('IK_Physis', target_mesh)
    path = ROOT + '/Retarget/RTG_Quinn_To_Physis'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path), source, target
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'RTG_Quinn_To_Physis', ROOT + '/Retarget', unreal.IKRetargeter, unreal.IKRetargetFactory())
    controller = unreal.IKRetargeterController.get_controller(asset)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, source)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, target)
    controller.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, source_mesh)
    controller.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, target_mesh)
    controller.add_default_ops()
    controller.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.SOURCE, source)
    controller.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.TARGET, target)
    controller.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET)
    save(asset)
    return asset, source, target


def retarget(names=None, limit=20):
    """Convert sequences not yet converted, in saved batches.

    Overwriting existing results crashed the editor when the batch reported back, and
    a crash loses anything unsaved, so finished animations are skipped and each batch
    is saved before the next. Blend spaces and montages are rebuilt for Physis later.
    """
    asset, _, _ = make_retargeter()
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    library = unreal.EditorAssetLibrary
    pending = [a for a in registry.get_assets_by_path('/Game/Characters/Mannequins/Anims', recursive=True)
               if str(a.asset_class_path.asset_name) == 'AnimSequence'
               and (names is None or str(a.asset_name) in names)
               and not library.does_asset_exist(ROOT + '/Physis_' + str(a.asset_name))]
    batch = pending[:limit]
    if not batch:
        return [], 0
    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.assets_to_retarget = batch
    inputs.source_mesh = unreal.load_asset(SOURCE_MESH)
    inputs.target_mesh = unreal.load_asset(TARGET_MESH)
    inputs.ik_retarget_asset = asset
    inputs.target_path = ROOT
    inputs.prefix = 'Physis_'
    inputs.overwrite_existing_files = False
    inputs.include_referenced_assets = False
    made = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    library.save_directory(ROOT, only_if_is_dirty=True, recursive=True)
    return [str(a.package_name) for a in made], len(pending) - len(batch)


def execute(operation):
    if operation == 'make_retargeter':
        unreal.EditorAssetLibrary.delete_asset(ROOT + '/Retarget/RTG_Quinn_To_Physis')
        asset, source, target = make_retargeter()
        report = {}
        for name, rig in (('source', source), ('target', target)):
            controller = unreal.IKRigController.get_controller(rig)
            report[name] = {'root': str(controller.get_retarget_root()),
                            'chains': [str(c.chain_name) for c in controller.get_retarget_chains()]}
        controller = unreal.IKRetargeterController.get_controller(asset)
        report['ops'] = [str(controller.get_op_name(i)) for i in range(controller.get_num_retarget_ops())]
        return json.dumps(report)
    if operation.startswith('pose:'):
        # pose:NAME:SECONDS holds the studio character at one moment of an animation.
        _, name, seconds = operation.split(':')
        anim = unreal.load_asset(ROOT + '/' + name)
        if not anim:raise RuntimeError('No retargeted animation named ' + name)
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == 'Physis_Studio_Character')
        body = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        body.override_animation_data(anim, False, False, float(seconds), 0)
        # In the editor nothing runs the face's own animation, so it follows the body here.
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            if component.get_name() != 'Body':
                component.set_leader_pose_component(body, True, False)
        return json.dumps({'animation': anim.get_name(), 'length': anim.get_play_length(), 'at': float(seconds),
                           'hand_r': str(body.get_socket_location('hand_r')), 'foot_l': str(body.get_socket_location('foot_l'))})
    if operation == 'body_mask':
        # Skin under the clothes is not drawn, using a copy of the shared skin material.
        # Assembly resets the body instance, so this runs after every rebuild.
        lib = unreal.MaterialEditingLibrary
        library = unreal.EditorAssetLibrary
        base = '/Game/Characters/Physis'
        body = unreal.load_asset('/Game/MetaHumans/MH_Physis/Body/Materials/MI_Body_Baked_VT')
        parent = body.get_editor_property('parent')
        if parent.get_name() != 'MI_Physis_Body':
            head = parent
            master = head.get_editor_property('parent')
            path = base + '/Materials/M_Physis_Body'
            if not library.does_asset_exist(path):
                material = library.duplicate_asset(master.get_path_name().split('.')[0], path)
                material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
                save(material)
                execute('wire_body_mask')
            target = base + '/Materials/MI_Physis_Body'
            instance = unreal.load_asset(target) if library.does_asset_exist(target) else library.duplicate_asset(head.get_path_name().split('.')[0], target)
            lib.set_material_instance_parent(instance, unreal.load_asset(path))
            lib.update_material_instance(instance);save(instance)
            lib.set_material_instance_parent(body, instance)
            lib.update_material_instance(body);save(body)
        return json.dumps({'parent': body.get_editor_property('parent').get_name(),
                           'attributes': unreal.load_asset(base + '/Materials/M_Physis_Body').get_editor_property('use_material_attributes')})
    if operation == 'set_classes':
        # Assembly regenerates BP_MH_Physis, so this runs after every rebuild.
        library = unreal.EditorAssetLibrary
        folder = ROOT + '/AnimBP'
        path = folder + '/Physis_ABP_Unarmed'
        if not library.does_asset_exist(path):
            asset, _, _ = make_retargeter()
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            source = next(a for a in registry.get_assets_by_path('/Game/Characters/Mannequins/Anims/Unarmed', recursive=False)
                          if str(a.asset_name) == 'ABP_Unarmed')
            inputs = unreal.IKRetargetBatchOperationInputs()
            inputs.assets_to_retarget = [source]
            inputs.source_mesh = unreal.load_asset(SOURCE_MESH)
            inputs.target_mesh = unreal.load_asset(TARGET_MESH)
            inputs.ik_retarget_asset = asset
            inputs.target_path = folder
            inputs.prefix = 'Physis_'
            inputs.overwrite_existing_files = False
            inputs.include_referenced_assets = True
            unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
            library.save_directory(folder, only_if_is_dirty=True, recursive=True)
        anim = unreal.load_asset(path)
        if not anim:
            raise RuntimeError('Retargeted Animation Blueprint not found at ' + path)
        unreal.BlueprintEditorLibrary.compile_blueprint(anim)
        save(anim)
        generated = unreal.BlueprintEditorLibrary.generated_class(anim) if hasattr(unreal.BlueprintEditorLibrary, 'generated_class') else anim.generated_class()
        bp = unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        done = {}
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj, unreal.SkeletalMeshComponent) and obj.get_name().startswith('Body'):
                obj.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_BLUEPRINT)
                obj.set_editor_property('anim_class', generated)
                done[obj.get_name()] = generated.get_name()
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        return json.dumps({'set': done, 'skeleton': anim.get_editor_property('target_skeleton').get_name(),
                           'created': sorted(str(a.asset_name) for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(folder, recursive=False))[:8]})
    if operation == 'inspect_blueprint':
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        class_path = unreal.TopLevelAssetPath('/Script/Engine', 'Blueprint')
        blueprints = [str(a.package_name) for a in registry.get_assets_by_class(class_path, True) if 'physis' in str(a.asset_name).lower()]
        anim_path = unreal.TopLevelAssetPath('/Script/Engine', 'AnimBlueprint')
        anim_blueprints = [str(a.package_name) for a in registry.get_assets_by_class(anim_path, True)
                           if str(a.package_name).startswith('/Game') or 'MetaHuman' in str(a.package_name)]
        bp = unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        components = {}
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj, unreal.SkeletalMeshComponent):
                anim = obj.get_editor_property('anim_class')
                post = obj.get_skeletal_mesh_asset().get_editor_property('post_process_anim_blueprint') if obj.get_skeletal_mesh_asset() else None
                components[obj.get_name()] = {'mode': str(obj.get_editor_property('animation_mode')),
                                              'anim_class': anim.get_name() if anim else None,
                                              'post_process': post.get_name() if post else None}
        return json.dumps({'blueprints': blueprints, 'anim_blueprints': anim_blueprints[:24], 'components': components})
    if operation == 'wire_body_mask':
        # This material outputs combined attributes, so the plain opacity pin is ignored.
        # A last blend keeps the skin where the mask is white and zeroes opacity elsewhere.
        lib = unreal.MaterialEditingLibrary
        material = unreal.load_asset('/Game/Characters/Physis/Materials/M_Physis_Body')
        output = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        if output.get_class().get_name() == 'MaterialExpressionBlendMaterialAttributes':
            return json.dumps({'already_wired': True})
        def node(cls, x, y):
            return lib.create_material_expression(material, cls, x, y)
        sampler = node(unreal.MaterialExpressionTextureSampleParameter2D, -2000, 2000)
        sampler.set_editor_property('parameter_name', 'ClothMask')
        sampler.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        sampler.set_editor_property('texture', unreal.load_asset('/Game/Characters/Physis/Textures/T_Physis_Body_Mask'))
        hidden = node(unreal.MaterialExpressionOneMinus, -1700, 2000)
        lib.connect_material_expressions(sampler, 'R', hidden, '')
        nothing = node(unreal.MaterialExpressionConstant, -1700, 2150)
        nothing.set_editor_property('r', 0)
        make = node(unreal.MaterialExpressionMakeMaterialAttributes, -1500, 2150)
        lib.connect_material_expressions(nothing, '', make, 'OpacityMask')
        blend = node(unreal.MaterialExpressionBlendMaterialAttributes, -1200, 2000)
        lib.connect_material_expressions(output, '', blend, 'A')
        lib.connect_material_expressions(make, '', blend, 'B')
        lib.connect_material_expressions(hidden, '', blend, 'Alpha')
        connected = lib.connect_material_property(blend, '', unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        lib.recompile_material(material);save(material)
        return json.dumps({'connected': connected})
    if operation == 'respawn_studio':
        # Actors placed earlier can keep the animation override from the pose tool.
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        removed = 0
        for actor in actors.get_all_level_actors():
            if actor.get_actor_label() == 'Physis_Studio_Character':
                actors.destroy_actor(actor);removed += 1
        # The studio step reloads this level, so the removal has to be saved first.
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if not unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(), '/Game/Characters/Physis/Preview/L_PhysisStudio'):
            raise RuntimeError('Could not save the studio level.')
        return json.dumps({'removed': removed})
    if operation == 'inspect_template':
        bp = unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        rows = []
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj, unreal.SkeletalMeshComponent) and obj.get_name().startswith('Body'):
                anim = obj.get_editor_property('anim_class')
                rows.append({'object': obj.get_path_name().split(':')[-1], 'mode': str(obj.get_editor_property('animation_mode')),
                             'anim': anim.get_name() if anim else None})
        return json.dumps(rows)
    if operation == 'inspect_construction':
        lib = unreal.BlueprintEditorLibrary
        bp = unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
        generated = lib.generated_class(bp) if hasattr(lib, 'generated_class') else bp.generated_class()
        cdo = unreal.get_default_object(generated)
        interesting = [x for x in dir(cdo) if any(k in x.lower() for k in ('anim', 'retarget', 'preview', 'live', 'source', 'body', 'pose')) and not x.startswith('_')]
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = next(a for a in actors.get_all_level_actors() if a.get_actor_label() == 'Physis_Studio_Character')
        body = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        data = body.get_editor_property('animation_data')
        played = data.get_editor_property('anim_to_play') if data else None
        return json.dumps({'properties': interesting[:40], 'parent': str(generated.get_super_class().get_name()) if hasattr(generated, 'get_super_class') else None,
                           'mode': str(body.get_editor_property('animation_mode')),
                           'anim_class': (lambda c: c.get_name() if c else None)(body.get_editor_property('anim_class')),
                           'plays': played.get_path_name() if played else None,
                           'graphs': [g.get_name() for g in (bp.get_editor_property('function_graphs') if hasattr(bp, 'function_graphs') else [])],
                           'class_of_actor': actor.get_class().get_path_name()})
    if operation == 'clear_pose':
        # Remove the pose tool's override everywhere it could live, then report a clean spawn.
        lib = unreal.BlueprintEditorLibrary
        bp = unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
        subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        generated = None
        anim = unreal.load_asset(ROOT + '/AnimBP/Physis_ABP_Unarmed')
        anim_class = anim.generated_class()
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj, unreal.SkeletalMeshComponent) and obj.get_name().startswith('Body'):
                obj.set_editor_property('animation_data', unreal.SingleAnimationPlayData())
                obj.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_BLUEPRINT)
                obj.set_editor_property('anim_class', anim_class)
        lib.compile_blueprint(bp);save(bp)
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        report = {}
        for actor in actors.get_all_level_actors():
            if actor.get_actor_label() == 'Physis_Studio_Character':
                body = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
                report['before'] = str(body.get_editor_property('animation_mode'))
                body.set_editor_property('animation_data', unreal.SingleAnimationPlayData())
                body.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
                body.set_anim_instance_class(anim_class)
                report['after'] = str(body.get_editor_property('animation_mode'))
                instance = body.get_anim_instance()
                report['instance'] = instance.get_class().get_name() if instance else None
        test = actors.spawn_actor_from_class(bp.generated_class(), unreal.Vector(0, 1000, 0))
        body = next(c for c in test.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
        played = body.get_editor_property('animation_data').get_editor_property('anim_to_play')
        report['fresh_spawn'] = {'mode': str(body.get_editor_property('animation_mode')), 'plays': played.get_name() if played else None}
        actors.destroy_actor(test)
        unreal.EditorLoadingAndSavingUtils.save_current_level() if hasattr(unreal.EditorLoadingAndSavingUtils, 'save_current_level') else None
        return json.dumps(report)
    if operation.startswith('platform:'):
        # platform:0 hides the studio platform so the soles can be seen from below.
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for actor in actors.get_all_level_actors():
            if actor.get_actor_label() == 'Physis_Studio_Platform':
                actor.set_is_temporarily_hidden_in_editor(operation.endswith('0'))
        return json.dumps({'platform': operation})
    if operation.startswith('inspect_pack:'):
        # inspect_pack:/Game/Folder lists a pack's animations and skeletons.
        folder = operation.split(':', 1)[1]
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        kinds = {}
        skeletons = {}
        meshes = []
        for data in registry.get_assets_by_path(folder, recursive=True):
            kind = str(data.asset_class_path.asset_name)
            kinds[kind] = kinds.get(kind, 0) + 1
            if kind == 'SkeletalMesh':
                meshes.append(str(data.package_name))
            if kind == 'AnimSequence':
                skeleton = str(data.get_tag_value('Skeleton'))
                skeletons[skeleton] = skeletons.get(skeleton, 0) + 1
        return json.dumps({'kinds': kinds, 'skeletons': skeletons, 'meshes': meshes[:8]})
    if operation == 'scan_packs':
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        registry.scan_paths_synchronous(['/Game/HandsomeKatana', '/Game/Stylized_Katana'], True)
        return json.dumps({'scanned': True})
    if operation == 'retarget_katana':
        # Skips finished clips and saves each batch, as with the Mannequin library.
        asset, _, _ = make_retargeter()
        folder = ROOT + '/Katana'
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        library = unreal.EditorAssetLibrary
        pending = [a for a in registry.get_assets_by_path('/Game/HandsomeKatana/Animations/Manny_UE5', recursive=True)
                   if str(a.asset_class_path.asset_name) == 'AnimSequence'
                   and not library.does_asset_exist(folder + '/Physis_' + str(a.asset_name))]
        batch = pending[:12]
        if not batch:
            return json.dumps({'made': 0, 'left': 0})
        inputs = unreal.IKRetargetBatchOperationInputs()
        inputs.assets_to_retarget = batch
        inputs.source_mesh = unreal.load_asset('/Game/HandsomeKatana/Demo/Characters/Manny_UE5/Meshes/SKM_Manny_HK')
        inputs.target_mesh = unreal.load_asset(TARGET_MESH)
        inputs.ik_retarget_asset = asset
        inputs.target_path = folder
        inputs.prefix = 'Physis_'
        inputs.overwrite_existing_files = False
        inputs.include_referenced_assets = False
        made = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
        library.save_directory(folder, only_if_is_dirty=True, recursive=True)
        return json.dumps({'made': len(made), 'left': len(pending) - len(batch)})
    if operation == 'verify_katana':
        folder = ROOT + '/Katana'
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        sources = [a for a in registry.get_assets_by_path('/Game/HandsomeKatana/Animations/Manny_UE5', recursive=True)
                   if str(a.asset_class_path.asset_name) == 'AnimSequence']
        report = {'sources': len(sources), 'matched': 0, 'problems': [], 'names': []}
        for data in sources:
            name = str(data.asset_name)
            result = unreal.load_asset(folder + '/Physis_' + name)
            if not result:
                report['problems'].append('missing ' + name);continue
            if 'metahuman_base_skel' not in result.get_editor_property('skeleton').get_name():
                report['problems'].append('skeleton ' + name);continue
            if abs(result.get_play_length() - data.get_asset().get_play_length()) > .01:
                report['problems'].append('length ' + name);continue
            report['matched'] += 1;report['names'].append(name)
        return json.dumps(report)
    if operation == 'inspect_input':
        report = {}
        for path in ('/Game/Input/IMC_Default', '/Game/Input/IMC_MouseLook'):
            imc = unreal.load_asset(path)
            report[path.split('/')[-1]] = [(m.action.get_name() if m.action else None, str(m.key.key_name) if hasattr(m.key, 'key_name') else str(m.key),
                                            [x.get_class().get_name() for x in m.modifiers])
                                           for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')]
        report['imc_attrs'] = [x for x in dir(unreal.InputMappingContext) if 'map' in x.lower()]
        return json.dumps(report, default=str)
    if operation == 'inspect_katana':
        meshes = {}
        for n in ('1_A', '1_B', '4_A', '7_A', '10_A'):
            mesh = unreal.load_asset('/Game/Stylized_Katana/Katana/Meshes/SM_Katana_' + n)
            box = mesh.get_bounding_box()
            meshes[n] = {'min': [round(v, 1) for v in box.min.to_tuple()], 'max': [round(v, 1) for v in box.max.to_tuple()]}
        skeleton = unreal.load_asset('/Game/HandsomeKatana/Demo/Characters/Manny_UE5/Meshes/SKM_Manny_HK')
        names = [s.socket_name for s in skeleton.get_active_socket_list()] if hasattr(skeleton, 'get_active_socket_list') else []
        return json.dumps({'meshes': meshes, 'manny_sockets': [str(n) for n in names]})
    if operation == 'inspect_sockets':
        report = {}
        skeleton = unreal.load_asset('/Game/HandsomeKatana/Demo/Characters/Manny_UE5/Meshes/SKEL_Manny_HK')
        for socket in skeleton.get_editor_property('sockets') if hasattr(skeleton, 'sockets') else []:
            report[str(socket.socket_name)] = {'bone': str(socket.bone_name), 'loc': str(socket.relative_location), 'rot': str(socket.relative_rotation)}
        mesh = unreal.load_asset('/Game/HandsomeKatana/Demo/Characters/Manny_UE5/Meshes/SKM_Manny_HK')
        return json.dumps({'skeleton_sockets': report, 'attrs': [x for x in dir(skeleton) if 'sock' in x.lower()], 'mesh_attrs': [x for x in dir(mesh) if 'sock' in x.lower()]})
    if operation == 'pie_check':
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return json.dumps({'pie': False})
        report = {'pie': True}
        for actor in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.Actor):
            if 'BP_MH_Physis' not in actor.get_class().get_name():
                continue
            parts = {}
            for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                name = component.get_name()
                if name in ('Hair', 'Eyebrows'):
                    continue
                instance = component.get_anim_instance()
                leader = component.get_editor_property('leader_pose_component')
                parts[name] = {'anim': instance.get_class().get_name() if instance else None,
                               'mode': str(component.get_editor_property('animation_mode')),
                               'leader': leader.get_name() if leader else None,
                               'hand_r': [round(v, 1) for v in component.get_socket_location('hand_r').to_tuple()]}
            report[actor.get_name()] = parts
        return json.dumps(report)
    if operation == 'inspect_body':
        lib = unreal.MaterialEditingLibrary
        mesh = unreal.load_asset(TARGET_MESH)
        report = {}
        for slot in mesh.materials:
            m = slot.material_interface
            chain = []
            base = m
            while isinstance(base, unreal.MaterialInstance):
                chain.append(base.get_name());base = base.get_editor_property('parent')
            chain.append(base.get_name() if base else None)
            report[str(slot.material_slot_name)] = {
                'path': m.get_path_name(), 'chain': chain,
                'blend': str(base.get_editor_property('blend_mode')) if base else None,
                'textures': [str(p) for p in lib.get_texture_parameter_names(m)],
                'switches': [str(p) for p in lib.get_static_switch_parameter_names(m)],
                'mask_scalars': [str(p) for p in lib.get_scalar_parameter_names(m) if any(k in str(p).lower() for k in ('mask','hidden','opacity','cloth'))]}
        report['wardrobe_options'] = [x for x in dir(unreal) if 'HiddenFace' in x or 'BodyHidden' in x or 'HiddenFaces' in x]
        pipeline = unreal.load_asset('/Game/Characters/Physis/Clothing/WI_Physis_Outfit').get_editor_property('pipeline')
        report['pipeline_class'] = pipeline.get_class().get_name()
        report['pipeline_props'] = [x for x in dir(pipeline) if any(k in x.lower() for k in ('hidden','mask','body'))]
        return json.dumps(report)
    if operation == 'verify':
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        sources = [a for a in registry.get_assets_by_path('/Game/Characters/Mannequins/Anims', recursive=True)
                   if str(a.asset_class_path.asset_name) == 'AnimSequence']
        report = {'sources': len(sources), 'matched': 0, 'missing': [], 'wrong_skeleton': [], 'wrong_length': []}
        for data in sources:
            name = str(data.asset_name)
            result = unreal.load_asset(ROOT + '/Physis_' + name)
            if not result:
                report['missing'].append(name);continue
            if 'metahuman_base_skel' not in result.get_editor_property('skeleton').get_name():
                report['wrong_skeleton'].append(name);continue
            if abs(result.get_play_length() - data.get_asset().get_play_length()) > .01:
                report['wrong_length'].append(name);continue
            report['matched'] += 1
        return json.dumps(report)
    if operation == 'retarget_all':
        made, left = retarget()
        return json.dumps({'made': len(made), 'left': left})
    if operation == 'retarget_test':
        made, _ = retarget(TEST_SET)
        return json.dumps({'made': made})
    if operation == 'probe':
        names = [x for x in dir(unreal) if any(k in x for k in ('IKRig', 'IKRetarget', 'Retarget'))]
        batch = unreal.IKRetargetBatchOperation if hasattr(unreal, 'IKRetargetBatchOperation') else None
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        meshes = {}
        for path in ('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple',
                     '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple',
                     '/Game/MetaHumans/MH_Physis/Body/SKM_MH_Physis_BodyMesh'):
            mesh = unreal.load_asset(path)
            meshes[path.split('/')[-1]] = mesh.skeleton.get_path_name() if mesh and mesh.skeleton else None
        anims = registry.get_assets_by_path('/Game/Characters/Mannequins/Anims', recursive=True)
        sequence = [str(a.asset_name) for a in anims if str(a.asset_class_path.asset_name) == 'AnimSequence']
        kinds = {}
        for a in anims:
            kind = str(a.asset_class_path.asset_name)
            kinds[kind] = kinds.get(kind, 0) + 1
        found = {}
        for kind in ('IKRigDefinition', 'IKRetargeter'):
            class_path = unreal.TopLevelAssetPath('/Script/IKRig', kind)
            found[kind] = [str(a.package_name) for a in registry.get_assets_by_class(class_path)][:20]
        return json.dumps({'batch': [x for x in dir(batch) if not x.startswith('_') and not x.startswith(('get_', 'set_', 'cast', 'static', 'modify'))][:14],
                           'batch_doc': batch.run_batch_retarget.__doc__[:360] if hasattr(batch, 'run_batch_retarget') else None,
                           'settings': [x for x in dir(unreal.BatchRetargetSettings) if not x.startswith('_')][:30],
                           'controllers': [x for x in names if 'Controller' in x and ('IKRig' in x and 'Op' not in x or x == 'IKRetargeterController')],
                           'found': found, 'meshes': meshes, 'kinds': kinds, 'sequences': len(sequence)})
    if operation == 'inputs':
        return json.dumps({'doc': unreal.IKRetargetBatchOperationInputs.__doc__[:1800],
                           'attrs': [x for x in dir(unreal.IKRetargetBatchOperationInputs) if not x.startswith('_')][:40]})
    if operation == 'controllers':
        rig = [x for x in dir(unreal.IKRigController) if not x.startswith('_') and any(k in x for k in ('auto', 'mesh', 'get_controller', 'retarget_root', 'chain'))]
        rtg = [x for x in dir(unreal.IKRetargeterController) if not x.startswith('_') and any(k in x for k in ('auto', 'set_ik', 'mesh', 'default', 'op', 'pose', 'get_controller'))]
        return json.dumps({'rig': rig, 'retargeter': rtg,
                           'factory': [x for x in dir(unreal) if 'IKRig' in x and 'Factory' in x],
                           'factory_methods': [x for x in dir(unreal.IKRigDefinitionFactory) if 'create' in x],
                           'duplicate': unreal.IKRetargetBatchOperation.duplicate_and_retarget.__doc__[:420]})
    raise ValueError('Unknown Physis animation operation: ' + operation)
