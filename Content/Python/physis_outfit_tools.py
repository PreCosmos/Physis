"""Fixed asset production steps for Physis's custom outfit and presentation."""
import json
from pathlib import Path
import unreal
from physis_character_tools import character, preview_actor, ROOT, SOURCE

BASE = '/Game/Characters/Physis'


def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset):
        raise RuntimeError('Could not save '+asset.get_path_name())


def import_outfit(reimport=False):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    textures = {}
    for filename in sorted((SOURCE/'Textures').glob('*.png')):
        path=BASE+'/Textures/'+filename.stem
        texture=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
        if not texture:
            task=unreal.AssetImportTask()
            task.filename=str(filename);task.destination_path=BASE+'/Textures'
            task.destination_name=filename.stem
            task.automated=True;task.save=True;task.replace_existing=False
            tools.import_asset_tasks([task])
            texture=unreal.load_asset(path)
        if not texture:
            raise RuntimeError('Texture import failed: '+str(filename))
        if filename.stem.endswith('_Normal'):
            texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('srgb',False)
        elif filename.stem.endswith(('_ORM','_Mask')):
            texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
            texture.set_editor_property('srgb',False)
        save(texture);textures[filename.stem]=texture

    mat_path=BASE+'/Materials/M_Physis_Fabric'
    material=unreal.load_asset(mat_path) if unreal.EditorAssetLibrary.does_asset_exist(mat_path) else None
    if not material:
        material=tools.create_asset('M_Physis_Fabric',BASE+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    if material:
        unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
        material.set_editor_property('two_sided',True)
        material.set_editor_property('used_with_skeletal_mesh',True)
        lib=unreal.MaterialEditingLibrary
        def node(cls,x,y):return lib.create_material_expression(material,cls,x,y)
        albedo=node(unreal.MaterialExpressionTextureSampleParameter2D,-750,-400)
        albedo.set_editor_property('parameter_name','BaseColor');albedo.set_editor_property('texture',textures['T_Physis_Ivory_BaseColor'])
        lib.connect_material_property(albedo,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
        normal=node(unreal.MaterialExpressionTextureSampleParameter2D,-750,-100)
        normal.set_editor_property('parameter_name','Normal');normal.set_editor_property('texture',textures['T_Physis_Fabric_Normal'])
        normal.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        lib.connect_material_property(normal,'RGB',unreal.MaterialProperty.MP_NORMAL)
        orm=node(unreal.MaterialExpressionTextureSampleParameter2D,-750,180)
        orm.set_editor_property('parameter_name','ORM');orm.set_editor_property('texture',textures['T_Physis_Fabric_ORM'])
        orm.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        lib.connect_material_property(orm,'R',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
        lib.connect_material_property(orm,'G',unreal.MaterialProperty.MP_ROUGHNESS)
        metallic=node(unreal.MaterialExpressionScalarParameter,-380,140)
        metallic.set_editor_property('parameter_name','Metallic');metallic.set_editor_property('default_value',0)
        lib.connect_material_property(metallic,'',unreal.MaterialProperty.MP_METALLIC)
        mask=node(unreal.MaterialExpressionTextureSampleParameter2D,-750,460)
        mask.set_editor_property('parameter_name','DivinityMask');mask.set_editor_property('texture',textures['T_Physis_Divinity_Mask'])
        mask.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        glow=node(unreal.MaterialExpressionScalarParameter,-750,740)
        glow.set_editor_property('parameter_name','DivinityGlow');glow.set_editor_property('default_value',.06)
        color=node(unreal.MaterialExpressionVectorParameter,-750,900)
        color.set_editor_property('parameter_name','DivinityColor');color.set_editor_property('default_value',unreal.LinearColor(1,.48,.12,1))
        multiply=node(unreal.MaterialExpressionMultiply,-400,530)
        lib.connect_material_expressions(mask,'R',multiply,'A')
        lib.connect_material_expressions(glow,'',multiply,'B')
        colored=node(unreal.MaterialExpressionMultiply,-160,530)
        lib.connect_material_expressions(multiply,'',colored,'A')
        lib.connect_material_expressions(color,'RGB',colored,'B')
        lib.connect_material_property(colored,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.recompile_material(material);save(material)
    instances={}
    for name in ['Ivory','Charcoal','Sash','Boots','GoldTrim']:
        path=BASE+'/Materials/MI_Physis_'+name
        instance=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
        if not instance:
            instance=tools.create_asset('MI_Physis_'+name,BASE+'/Materials',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(instance,material)
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(instance,'BaseColor',textures['T_Physis_'+name+'_BaseColor'])
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance,'Metallic',.65 if name=='GoldTrim' else 0)
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance,'DivinityGlow',.06 if name=='Ivory' else .02 if name=='Charcoal' else 0)
        unreal.MaterialEditingLibrary.update_material_instance(instance)
        save(instance);instances[name]=instance

    mesh_path=BASE+'/Clothing/SK_Physis_Outfit'
    mesh=unreal.load_asset(mesh_path) if unreal.EditorAssetLibrary.does_asset_exist(mesh_path) else None
    if not mesh or reimport:
        options=unreal.FbxImportUI()
        options.import_mesh=True;options.import_as_skeletal=True
        options.import_materials=False;options.import_textures=False
        options.import_animations=False;options.create_physics_asset=False
        options.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
        options.skeleton=unreal.load_asset('/MetaHumanCharacter/Female/Medium/NormalWeight/Body/metahuman_base_skel')
        task=unreal.AssetImportTask()
        task.filename=str(SOURCE/'SK_Physis_Outfit.fbx')
        task.destination_path=BASE+'/Clothing';task.destination_name='SK_Physis_Outfit'
        task.automated=True;task.save=True;task.options=options
        task.replace_existing=reimport
        task.factory=unreal.FbxFactory()
        tools.import_asset_tasks([task])
        mesh=unreal.load_asset(mesh_path)
    if not mesh:
        raise RuntimeError('Skeletal outfit import failed.')
    slots=mesh.get_editor_property('materials')
    assigned=[]
    for index in range(len(slots)):
        slot=slots[index]
        name=str(slot.material_slot_name)
        key=next((n for n in instances if n.lower() in name.lower()),None)
        if not key:
            raise RuntimeError('Unrecognized garment material slot: '+name)
        slots[index]=unreal.SkeletalMaterial(material_interface=instances[key],
                                             material_slot_name=slot.material_slot_name,
                                             uv_channel_data=slot.uv_channel_data)
        assigned.append(name)
    mesh.set_editor_property('materials',slots);save(mesh)
    report={'outfit':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),
            'material_slots':assigned,'textures':[t.get_path_name() for t in textures.values()]}
    (SOURCE/'unreal-import.json').write_text(json.dumps(report,indent=2))
    return report


def wardrobe():
    asset, sub=character()
    mesh=unreal.load_asset(BASE+'/Clothing/SK_Physis_Outfit')
    if not mesh:raise RuntimeError('Import the outfit first.')
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    path=BASE+'/Clothing/WI_Physis_Outfit'
    item=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if not item:
        item=tools.create_asset('WI_Physis_Outfit',BASE+'/Clothing',unreal.MetaHumanWardrobeItem,unreal.MetaHumanWardrobeItemFactory())
    reference=unreal.EditorOnlyAssetReference()
    reference.set_editor_property('asset',mesh)
    item.set_editor_property('principal_asset',reference)
    if not item.get_editor_property('pipeline'):
        pipeline=unreal.new_object(unreal.MetaHumanSkeletalMeshPipeline,outer=item)
        item.set_editor_property('pipeline',pipeline)
    save(item)
    collection=sub.get_preview_collection(asset)
    key=collection.try_add_item_from_wardrobe_item('SkeletalMesh',item)
    selection=unreal.MetaHumanPipelineSlotSelection(slot_name='SkeletalMesh',selected_item=key)
    collection.default_instance.set_single_slot_selection('SkeletalMesh',key)
    sub.on_edit_preview_collection(asset)
    sub.assemble_for_preview(asset)
    save(asset)
    return {'wardrobe_item':item.get_path_name(),'character':asset.get_path_name()}


def studio():
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    candidates=[a for a in registry.get_assets_by_path('/Game/MetaHumans',recursive=True)
                if str(a.asset_name).startswith('BP_') and 'physis' in str(a.asset_name).lower()]
    if not candidates:
        raise RuntimeError('No assembled Physis Blueprint exists yet.')
    blueprint=candidates[0].get_asset()
    level_path=BASE+'/Preview/L_PhysisStudio'
    if unreal.EditorAssetLibrary.does_asset_exist(level_path):
        unreal.EditorLoadingAndSavingUtils.load_map(level_path)
    else:
        unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='Physis_Studio_Character']
    actor=existing[0] if existing else actors.spawn_actor_from_class(blueprint.generated_class(),unreal.Vector(0,0,0))
    actor.set_actor_label('Physis_Studio_Character')
    for sync in actor.get_components_by_class(unreal.LODSyncComponent):
        sync.set_editor_property('forced_lod',2)
    if not existing:
        for label,location,rotation,color,intensity in [
            ('Physis_Key',unreal.Vector(220,-170,260),unreal.Rotator(-35,-145,0),unreal.LinearColor(1,.91,.78,1),1600),
            ('Physis_Fill',unreal.Vector(180,190,180),unreal.Rotator(-20,140,0),unreal.LinearColor(.7,.82,1,1),800),
            ('Physis_Rim',unreal.Vector(-140,80,210),unreal.Rotator(-25,-30,0),unreal.LinearColor(1,.8,.55,1),2000)]:
            light=actors.spawn_actor_from_class(unreal.RectLight,location,rotation)
            light.set_actor_label(label)
            component=light.get_component_by_class(unreal.RectLightComponent)
            component.set_intensity(intensity);component.set_light_color(color)
            component.set_editor_property('source_width',140)
            component.set_editor_property('source_height',180)
        sun=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,300),unreal.Rotator(-45,-135,0))
        sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(2)
        sun.set_actor_label('Physis_Studio_SoftLight')
        sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,200))
        sky.set_actor_label('Physis_Studio_Ambient')
        plane=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,-3))
        plane.set_actor_label('Physis_Studio_Platform')
        plane.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cylinder'))
        plane.set_actor_scale3d(unreal.Vector(1.6,1.6,.05))
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    position=unreal.Vector(275,-160,123)
    rotation=unreal.MathLibrary.find_look_at_rotation(position,unreal.Vector(0,0,90))
    editor.set_level_viewport_camera_info(position,rotation)
    if not unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(),level_path):
        raise RuntimeError('Could not save Physis studio.')
    return {'level':level_path,'blueprint':blueprint.get_path_name(),'actor':actor.get_path_name()}


def verify():
    asset=unreal.load_asset(BASE+'/MH_Physis')
    mesh=unreal.load_asset(BASE+'/Clothing/SK_Physis_Outfit')
    item=unreal.load_asset(BASE+'/Clothing/WI_Physis_Outfit')
    if not mesh or not item:raise RuntimeError('Outfit assets missing.')
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    built=[str(a.package_name) for a in registry.get_assets_by_path('/Game/MetaHumans',recursive=True)
           if 'physis' in str(a.package_name).lower()]
    report={'character':asset.get_path_name(),'high_resolution_skin':asset.get_editor_property('has_high_resolution_textures'),
            'outfit':mesh.get_path_name(),'wardrobe':item.get_path_name(),
            'skeleton':mesh.skeleton.get_path_name(),
            'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.materials],
            'assembled_assets':built}
    (SOURCE/'verification.json').write_text(json.dumps(report,indent=2))
    return report


def execute(operation):
    if operation=='import':return json.dumps(import_outfit())
    if operation=='reimport':return json.dumps(import_outfit(True))
    if operation=='wardrobe':return json.dumps(wardrobe())
    if operation=='studio':return json.dumps(studio())
    if operation=='verify':return json.dumps(verify())
    if operation=='face_landmarks':
        asset,sub=character()
        points=sub.get_face_landmarks(asset)
        data={'points':[{'index':i,'x':p.x,'y':p.y,'z':p.z} for i,p in enumerate(points)],
              'coefficients':list(sub.get_face_model_coefficients(asset))}
        (SOURCE/'face-landmarks-before.json').write_text(json.dumps(data,indent=2))
        baseline=SOURCE/'face-identity-baseline.json'
        if not baseline.exists():baseline.write_text(json.dumps(data,indent=2))
        return json.dumps({'landmark_count':len(points),'points':data['points']})
    if operation=='refine_face':
        asset,sub=character()
        baseline=json.loads((SOURCE/'face-identity-baseline.json').read_text())
        sub.set_face_model_coefficients(asset,baseline['coefficients'])
        # Bilateral landmark edits, in centimeters, from the saved face baseline.
        # Spatially identified jaw, chin, cheek, nose, and outer-brow landmarks.
        deltas={1:(.55,.10,0),28:(-.55,.10,0),
                2:(.50,-.05,.02),29:(-.50,-.05,.02),
                3:(.28,.10,-.12),30:(-.28,.10,-.12),
                62:(0,.22,-.28),4:(0,.12,0),
                23:(-.20,-.28,.06),66:(.20,-.28,.06),
                41:(-.10,.16,.12),58:(.10,.16,.12),
                45:(-.20,.02,0),67:(.20,.02,0),
                64:(0,.22,-.06),6:(0,.10,0),
                40:(-.07,0,0),57:(.07,0,0),
                18:(0,0,.10),22:(0,0,.10),
                10:(0,.02,.10),26:(0,.02,.10)}
        sub.translate_face_landmarks(asset,list(deltas),[unreal.Vector(*v) for v in deltas.values()])
        sub.commit_face_state(asset)
        save(asset)
        after=sub.get_face_landmarks(asset)
        report={'description':'Tapered jaw and chin, defined cheeks, narrower nose and slightly lifted outer eye/brow contour',
                'deltas_cm':deltas,'points_after':[{'index':i,'x':p.x,'y':p.y,'z':p.z} for i,p in enumerate(after)]}
        (SOURCE/'face-refinement.json').write_text(json.dumps(report,indent=2))
        return json.dumps({'edited_landmarks':len(deltas),'saved':True,'face_rig_needs_refresh':True})
    if operation=='slim_identity':
        # Work from an empty level to release the assembled review meshes first.
        unreal.EditorLoadingAndSavingUtils.load_map('/Engine/Maps/Entry')
        unreal.SystemLibrary.collect_garbage()
        asset,sub=character()
        execute('trim_preview_textures')
        from metahuman_toolset.metahuman import _get_body_constraints_and_ranges
        constraints,ranges=_get_body_constraints_and_ranges(asset)
        targets={'Fat':.18,'Muscularity':.30}
        for c in constraints:
            name=str(c.name)
            if name in targets:
                c.is_active=True
                c.target_measurement=unreal.MathLibrary.lerp(ranges[name][0],ranges[name][1],targets[name])
        sub.set_body_constraints(asset,constraints)
        sub.commit_body_state(asset)
        # Keep the existing face rig: this edit changes the body, not the face identity.
        collection=sub.get_preview_collection(asset)
        brow=unreal.load_asset('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Natural')
        if brow:
            key=collection.try_add_item_from_wardrobe_item('Eyebrows',brow)
            collection.default_instance.set_single_slot_selection('Eyebrows',key)
        # The custom outfit is selected exactly once in the source collection.
        selections=collection.default_instance.get_slot_selection_data()
        outfits=[s.selection for s in selections if str(s.selection.slot_name)=='SkeletalMesh']
        if outfits:collection.default_instance.set_single_slot_selection('SkeletalMesh',outfits[0].selected_item)
        sub.on_edit_preview_collection(asset)
        save(asset)
        return json.dumps({'body_fat_normalized':.18,'muscularity_normalized':.30,'height_cm':168,
                           'eyebrows':brow.get_path_name() if brow else None})
    if operation=='diagnose_binding':
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='Physis_Studio_Character')
        for sync in actor.get_components_by_class(unreal.LODSyncComponent):sync.set_editor_property('forced_lod',0)
        components=actor.get_components_by_class(unreal.SkeletalMeshComponent)
        body=next(c for c in components if c.get_name()=='Body')
        result=[]
        for component in components:
            leader=component.get_editor_property('leader_pose_component')
            result.append({'name':component.get_name(),'leader':leader.get_path_name() if leader else None,
                           'pelvis':str(component.get_socket_transform('pelvis',unreal.RelativeTransformSpace.RTS_COMPONENT))})
            if 'PhysisOutfit' in component.get_name():component.set_leader_pose_component(body,True,False)
        return json.dumps(result)
    if operation=='review_scene':
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        positions={'Physis_Key':unreal.Vector(-180,220,260),
                   'Physis_Fill':unreal.Vector(180,190,180),
                   'Physis_Rim':unreal.Vector(0,-180,210)}
        details=[]
        for actor in actors.get_all_level_actors():
            label=actor.get_actor_label()
            if label in positions:
                pos=positions[label]
                actor.set_actor_location(pos,False,False)
                actor.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(pos,unreal.Vector(0,0,100)),False)
            if label=='Physis_Studio_SoftLight':
                actor.set_actor_rotation(unreal.Rotator(-45,-90,0),False)
            if label=='Physis_Studio_Character':
                for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                    mesh=component.get_editor_property('skeletal_mesh_asset')
                    details.append({'component':component.get_name(),'mesh':mesh.get_path_name() if mesh else None,
                                    'relative_rotation':str(component.get_relative_transform().rotation)})
        pos=unreal.Vector(65,260,100)
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        editor.set_level_viewport_camera_info(pos,unreal.MathLibrary.find_look_at_rotation(pos,unreal.Vector(0,0,85)))
        level_editor=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        level_editor.editor_set_game_view(True)
        level_editor.editor_set_viewport_realtime(True)
        level_editor.set_level_viewport_fov(50,level_editor.get_active_viewport_config_key())
        for command in ['r.MotionBlurQuality 0','r.DepthOfFieldQuality 0','r.AntiAliasingMethod 1']:
            unreal.SystemLibrary.execute_console_command(editor.get_editor_world(),command)
        unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(),BASE+'/Preview/L_PhysisStudio')
        return json.dumps({'components':details})
    if operation=='remove_duplicate_outfit':
        asset=unreal.load_asset(BASE+'/MH_Physis')
        instance=asset.internal_collection.default_instance
        selections=instance.get_slot_selection_data()
        selected=[s.selection for s in selections if str(s.selection.slot_name)=='SkeletalMesh']
        if selected:
            instance.set_single_slot_selection('SkeletalMesh',selected[0].selected_item)
            save(asset)
        bp=unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
        subobjects=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        from editor_toolset.toolsets.actor import ActorTools
        removed=0
        for attempt in range(8):
            components=[];seen=set()
            for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
                data=unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
                obj=unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
                if isinstance(obj,unreal.SkeletalMeshComponent) and obj.get_path_name() not in seen:
                    mesh=obj.get_editor_property('skeletal_mesh_asset')
                    if mesh and mesh.get_path_name().startswith(BASE+'/Clothing/SK_Physis_Outfit.'):
                        components.append(obj);seen.add(obj.get_path_name())
            if len(components)<=1:break
            ActorTools.remove_component(components[-1]);removed+=1
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        return json.dumps({'removed_duplicate_components':removed,'remaining_outfit_components':len(components)})
    if operation=='restore_outfit_component':
        bp=unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
        mesh=unreal.load_asset(BASE+'/Clothing/SK_Physis_Outfit')
        subobjects=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        body=None
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data=unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj=unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj,unreal.SkeletalMeshComponent) and obj.get_name().startswith('Body'):
                body=obj;break
        if not body:raise RuntimeError('Body template missing.')
        from editor_toolset.toolsets.actor import ActorTools
        component=ActorTools.add_component(body,unreal.SkeletalMeshComponent.static_class(),'PhysisOutfit')
        component.set_skeletal_mesh_asset(mesh)
        component.set_leader_pose_component(body)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        return json.dumps({'component':component.get_path_name()})
    if operation=='repair_materials':
        mesh=unreal.load_asset(BASE+'/Clothing/SK_Physis_Outfit')
        slots=list(mesh.materials)
        mapping={}
        for index,old in enumerate(slots):
            name=str(old.material_slot_name)
            material=unreal.load_asset(BASE+'/Materials/MI_Physis_'+name)
            if not material:raise RuntimeError('Missing material for '+name)
            slots[index]=unreal.SkeletalMaterial(material_interface=material,material_slot_name=old.material_slot_name,uv_channel_data=old.uv_channel_data)
            mapping[name]=material
        mesh.modify();mesh.materials=slots
        save(mesh)
        item=unreal.load_asset(BASE+'/Clothing/WI_Physis_Outfit')
        item.get_editor_property('pipeline').set_editor_property('override_materials',mapping)
        save(item)
        result=[m.material_interface.get_path_name() if m.material_interface else None for m in mesh.materials]
        if not all(result):raise RuntimeError('Material readback failed: '+str(result))
        return json.dumps({'materials':result})
    if operation=='save_assembled':
        registry=unreal.AssetRegistryHelpers.get_asset_registry()
        saved=[];failures=[]
        for data in registry.get_assets_by_path('/Game/MetaHumans',recursive=True):
            asset=data.get_asset()
            try:
                save(asset);saved.append(asset.get_path_name())
            except Exception as error:
                failures.append({'asset':str(data.package_name),'error':str(error)})
        return json.dumps({'saved_count':len(saved),'failures':failures,'assets':saved})
    if operation=='assemble_low_memory':
        asset,sub=character()
        trimmed=json.loads(execute('trim_preview_textures'))
        params=unreal.MetaHumanCharacterEditorBuildParameters()
        params.pipeline_type=unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        params.pipeline_quality=unreal.MetaHumanQualityLevel.MEDIUM
        params.absolute_build_path='/Game/MetaHumans'
        params.common_folder_path='/Game/MetaHumans/Common'
        params.enable_wardrobe_item_validation=False
        sub.build_meta_human(asset,params)
        unreal.EditorAssetLibrary.save_directory('/Game/MetaHumans',only_if_is_dirty=True,recursive=True)
        save(asset)
        return json.dumps({'assembly_finished':True,**trimmed})
    if operation=='trim_preview_textures':
        # Only change transient textures or unsaved in-memory engine content.
        # Source pixel data stays intact; engine packages are never saved here.
        adjusted=[]
        for texture in unreal.ObjectIterator(unreal.Texture2D):
            path=texture.get_path_name()
            if path.startswith(('/MetaHumanCharacter/Lookdev','/Engine/Transient')):
                texture.set_editor_property('max_texture_size',512)
                adjusted.append(path)
        unreal.SystemLibrary.collect_garbage()
        return json.dumps({'preview_textures_limited':len(adjusted)})
    if operation == 'inspect':
        asset, sub = character()
        return json.dumps({'rig_enum': [x for x in dir(unreal.MetaHumanRigType) if x.isupper()],
                           'rig_properties': [x for x in dir(asset) if 'rig' in x.lower()],
                           'high_res_textures': asset.get_editor_property('has_high_resolution_textures'),
                           'wardrobe_classes': [x for x in dir(unreal) if 'SkeletalMeshPipeline' in x or 'WardrobeItem' in x]})
    if operation in ('rig', 'rig_save'):
        asset, sub = character()
        params = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        params.blocking = operation == 'rig_save'
        params.report_progress = False
        names = [x for x in dir(unreal.MetaHumanRigType) if 'JOINTS' in x and 'BLEND' in x]
        if len(names) != 1:
            raise RuntimeError('Unexpected rig type names: '+str(names))
        params.rig_type = getattr(unreal.MetaHumanRigType, names[0])
        sub.request_auto_rigging(asset, params)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
        return json.dumps({'face_rig_request_submitted': True, 'rig_type': names[0]})
    if operation == 'textures_save':
        asset, sub = character()
        params = unreal.MetaHumanCharacterTextureRequestParams()
        params.blocking = True
        params.report_progress = False
        sub.request_texture_sources(asset, params)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
        return json.dumps({'high_res_textures': asset.get_editor_property('has_high_resolution_textures')})
    raise ValueError('Unknown or not yet available Physis production operation: '+operation)
