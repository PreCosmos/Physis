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
        # Panels scale their UVs for the branch pattern; the weave keeps its own scale.
        coordinates=node(unreal.MaterialExpressionTextureCoordinate,-1200,-100)
        weave=node(unreal.MaterialExpressionScalarParameter,-1200,0)
        weave.set_editor_property('parameter_name','WeaveTiling');weave.set_editor_property('default_value',1)
        scaled=node(unreal.MaterialExpressionMultiply,-980,-60)
        lib.connect_material_expressions(coordinates,'',scaled,'A')
        lib.connect_material_expressions(weave,'',scaled,'B')
        lib.connect_material_expressions(scaled,'',normal,'UVs')
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
        # Lightning: the branch traces pulse instead of glowing evenly.
        speed=node(unreal.MaterialExpressionScalarParameter,-900,1100)
        speed.set_editor_property('parameter_name','DivinityFlickerSpeed');speed.set_editor_property('default_value',.35)
        clock=node(unreal.MaterialExpressionTime,-900,1250)
        timed=node(unreal.MaterialExpressionMultiply,-700,1150)
        lib.connect_material_expressions(speed,'',timed,'A')
        lib.connect_material_expressions(clock,'',timed,'B')
        wave=node(unreal.MaterialExpressionSine,-520,1150)
        lib.connect_material_expressions(timed,'',wave,'')
        depth=node(unreal.MaterialExpressionMultiply,-350,1150)
        depth.set_editor_property('const_b',.45)
        lib.connect_material_expressions(wave,'',depth,'A')
        pulse=node(unreal.MaterialExpressionAdd,-180,1150)
        pulse.set_editor_property('const_b',.55)
        lib.connect_material_expressions(depth,'',pulse,'A')
        flicker=node(unreal.MaterialExpressionMultiply,60,600)
        lib.connect_material_expressions(colored,'',flicker,'A')
        lib.connect_material_expressions(pulse,'',flicker,'B')
        lib.connect_material_property(flicker,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
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
        options.skeleton=unreal.load_asset('/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel')
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
    if operation.startswith('aaa:'):
        import importlib
        import physis_gameplay_tools
        import physis_lore
        import physis_aaa_tools
        importlib.reload(physis_gameplay_tools)
        importlib.reload(physis_lore)
        importlib.reload(physis_aaa_tools)
        return physis_aaa_tools.execute(operation.split(':',1)[1])
    if operation.startswith('center:'):
        import importlib
        import physis_gameplay_tools
        import physis_center_lore
        import physis_center_tools
        importlib.reload(physis_gameplay_tools)
        importlib.reload(physis_center_lore)
        importlib.reload(physis_center_tools)
        return physis_center_tools.execute(operation.split(':',1)[1])
    if operation.startswith('conclave:'):
        import importlib
        import physis_gameplay_tools
        import physis_center_tools
        import physis_conclave_plan
        import physis_conclave_lore
        import physis_conclave_tools
        # The Conclave's tools build on the Center's material and actor helpers, so those reload first too.
        importlib.reload(physis_gameplay_tools)
        importlib.reload(physis_center_tools)
        importlib.reload(physis_conclave_plan)
        importlib.reload(physis_conclave_lore)
        importlib.reload(physis_conclave_tools)
        return physis_conclave_tools.execute(operation.split(':',1)[1])
    if operation.startswith('play:'):
        import importlib
        import physis_gameplay_tools
        importlib.reload(physis_gameplay_tools)
        return physis_gameplay_tools.execute(operation.split(':',1)[1])
    if operation.startswith('anim:'):
        import importlib
        import physis_animation_tools
        importlib.reload(physis_animation_tools)
        return physis_animation_tools.execute(operation.split(':',1)[1])
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
    if operation=='refine_nose':
        # Concept-sheet nose: slim straight high bridge, narrow pinched nostrils,
        # and a projected, slightly upturned point at the tip (elf-like).
        # Rebuilt from the baseline so the result is reproducible: the earlier
        # refine_face deltas are reapplied, and the nose deltas are added on top.
        asset,sub=character()
        baseline=json.loads((SOURCE/'face-identity-baseline.json').read_text())
        previous=json.loads((SOURCE/'face-refinement.json').read_text())['deltas_cm']
        deltas={int(k):list(v) for k,v in previous.items()}
        # The face model absorbs most of a landmark move (about 40%), so these
        # requests are deliberately larger than the change wanted on the mesh.
        nose={64:(0,.70,.28),   # tip: project forward and lift into a point
              65:(0,.30,.20),   # columella / under-tip: follow the upturn
              6:(0,.40,0),      # mid bridge: higher, straighter dorsum
              59:(0,.25,0),     # upper bridge between the eyes
              40:(-.40,0,0),57:(.40,0,0),            # bridge sides: narrower
              45:(-.70,-.15,.08),67:(.70,-.15,.08),  # nostril wings: pinched and set back
              70:(.35,0,0),74:(-.35,0,0)}            # nose-to-cheek sides: narrower
        for index,v in nose.items():
            base=deltas.get(index,[0,0,0])
            deltas[index]=[round(base[i]+v[i],4) for i in range(3)]
        before=sub.get_face_landmarks(asset)
        sub.set_face_model_coefficients(asset,baseline['coefficients'])
        sub.translate_face_landmarks(asset,list(deltas),[unreal.Vector(*v) for v in deltas.values()])
        sub.commit_face_state(asset)
        save(asset)
        after=sub.get_face_landmarks(asset)
        moved={i:[round(after[i].x-before[i].x,3),round(after[i].y-before[i].y,3),round(after[i].z-before[i].z,3)] for i in nose}
        report={'description':'Concept nose: slim straight bridge, narrow nostrils, projected upturned point',
                'nose_deltas_cm':nose,'combined_deltas_cm':deltas,'nose_landmark_change_cm':moved,
                'points_after':[{'index':i,'x':p.x,'y':p.y,'z':p.z} for i,p in enumerate(after)]}
        (SOURCE/'face-nose-refinement.json').write_text(json.dumps(report,indent=2))
        return json.dumps({'edited_landmarks':len(deltas),'nose_landmark_change_cm':moved,
                           'saved':True,'face_rig_needs_refresh':True})
    if operation.startswith('set_hair:'):
        # Swap the groom, keeping the concept's near-black, cool brown color.
        asset,sub=character()
        name=operation.split(':',1)[1]
        hair=unreal.load_asset('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/'+name)
        if not hair:raise RuntimeError('Hair not found: '+name)
        collection=sub.get_preview_collection(asset)
        key=collection.try_add_item_from_wardrobe_item('Hair',hair)
        collection.default_instance.set_single_slot_selection('Hair',key)
        sub.on_edit_preview_collection(asset)
        sub.assemble_for_preview(asset)
        params=collection.default_instance.get_instance_parameters(unreal.MetaHumanPaletteItemPath(item_key=key))
        names=[]
        for param in params:
            names.append(str(param.name))
            if str(param.name)=='Melanin':param.set_float(.95)
            elif str(param.name)=='Redness':param.set_float(.04)
        sub.on_edit_preview_collection(asset)
        save(asset)
        return json.dumps({'hair':hair.get_path_name(),'parameters':names,'saved':True})
    if operation.startswith('review_lod:'):
        # Force a detail level on the studio character; 0 is the full-quality review.
        lod=int(operation.split(':',1)[1])
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='Physis_Studio_Character')
        for sync in actor.get_components_by_class(unreal.LODSyncComponent):sync.set_editor_property('forced_lod',lod)
        unreal.SystemLibrary.execute_console_command(None,'r.HairStrands.Enable 1')
        return json.dumps({'forced_lod':lod,'components':[c.get_name() for c in actor.get_components_by_class(unreal.SceneComponent)
                           if 'Hair' in c.get_name() or 'Eyebrow' in c.get_name() or 'Groom' in c.get_class().get_name()]})
    if operation=='empty_level':
        # Release the assembled review meshes before they are rebuilt.
        unreal.EditorLoadingAndSavingUtils.load_map('/Engine/Maps/Entry')
        unreal.SystemLibrary.collect_garbage()
        return json.dumps({'level':'/Engine/Maps/Entry'})
    if operation.startswith('set_brows:'):
        asset,sub=character()
        name=operation.split(':',1)[1]
        brows=unreal.load_asset('/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/'+name)
        if not brows:raise RuntimeError('Eyebrows not found: '+name)
        collection=sub.get_preview_collection(asset)
        key=collection.try_add_item_from_wardrobe_item('Eyebrows',brows)
        collection.default_instance.set_single_slot_selection('Eyebrows',key)
        sub.on_edit_preview_collection(asset)
        sub.assemble_for_preview(asset)
        params=collection.default_instance.get_instance_parameters(unreal.MetaHumanPaletteItemPath(item_key=key))
        for param in params:
            if str(param.name)=='Melanin':param.set_float(.95)
            elif str(param.name)=='Redness':param.set_float(.04)
        sub.on_edit_preview_collection(asset)
        save(asset)
        return json.dumps({'eyebrows':brows.get_path_name(),'saved':True})
    if operation=='inspect_look':
        asset,sub=character()
        skin=asset.skin_settings
        eyes=asset.get_editor_property('eyes_settings') if hasattr(asset,'eyes_settings') else None
        return json.dumps({'skin_uv':[skin.skin.u,skin.skin.v,skin.skin.roughness],
                           'freckles':[skin.freckles.density,skin.freckles.strength,skin.freckles.saturation,skin.freckles.tone_shift],
                           'eyes':str(eyes),
                           'eye_attrs':[x for x in dir(eyes) if not x.startswith('_')][:40] if eyes else [x for x in dir(asset) if 'eye' in x.lower()],
                           'geometry_script':[x for x in dir(unreal) if 'GeometryScript' in x and ('Skeletal' in x or 'AssetUtil' in x or 'MeshQuery' in x or 'BasicEdit' in x or 'Transform' in x)]})
    if operation=='fit_neck':
        # The face mesh continues into a chest bib that the body-fitted shell does
        # not cover. Reproject the collar ring over neck and bib as a high neck.
        import math
        lib=unreal.GeometryScript_AssetUtils
        def load(path):
            mesh=unreal.DynamicMesh()
            mesh,outcome=lib.copy_mesh_from_skeletal_mesh(unreal.load_asset(path),mesh,
                unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
            if 'SUCCESS' not in str(outcome):raise RuntimeError('Could not read '+path)
            return mesh
        asset_mesh=unreal.load_asset(BASE+'/Clothing/SK_Physis_Outfit')
        face=load('/Game/MetaHumans/MH_Physis/Face/SKM_MH_Physis_FaceMesh')
        body=load('/Game/MetaHumans/MH_Physis/Body/SKM_MH_Physis_BodyMesh')
        outfit=load(BASE+'/Clothing/SK_Physis_Outfit')
        face_bvh=face.build_bvh_for_mesh()[1];body_bvh=body.build_bvh_for_mesh()[1]
        options=unreal.GeometryScriptSpatialQueryOptions()
        def distance(mesh,bvh,origin,direction):
            result=mesh.find_nearest_ray_intersection_with_mesh(bvh,origin,direction,options)
            hit=next(r for r in result if isinstance(r,unreal.GeometryScriptRayHitResult))
            return hit.ray_parameter if hit.hit else None
        heights={4:143.5,3:141,2:137.5,1:133,0:129}
        positions=outfit.get_all_vertex_positions(False)
        positions=next(r for r in positions if isinstance(r,unreal.GeometryScriptVectorList))
        positions=unreal.GeometryScript_List.convert_vector_list_to_array(positions)
        ring=[];shell=[]
        for index,p in enumerate(positions):
            radial=((p.x/7.0)**2+((p.y+2)/5.6)**2)**.5
            row=(p.z-135.5)/1.625
            if abs(radial-1)<.05 and abs(row-round(row))<.03 and 0<=round(row)<=4:
                ring.append((index,int(round(row))))
            elif 122<p.z<136:shell.append((index,p))
        if len(ring)!=485:
            raise RuntimeError('Expected the 485 collar vertices, found %d. Reimport the outfit first.'%len(ring))
        moved=[];rows={}
        for index,row in sorted(ring,key=lambda r:r[1]):
            p=positions[index]
            angle=math.atan2(p.x,p.y+2)
            direction=unreal.Vector(math.sin(angle),math.cos(angle),0)
            # Rows are far apart, so clear the bib at the heights between them too.
            reach=[]
            for lift in (-1,0,1) if row<4 else (0,):
                origin=unreal.Vector(0,-1,heights[row]+lift)
                on_face=distance(face,face_bvh,origin,direction)
                on_body=distance(body,body_bvh,origin,direction)
                if on_face is not None:reach.append(on_face+.9)
                if on_body is not None:reach.append(on_body+.4)
            radius=max(reach) if reach else rows.get((row-1,round(angle,3)),9)
            rows[(row,round(angle,3))]=radius
            moved.append((index,row,unreal.Vector(direction.x*radius,-1+direction.y*radius,heights[row])))
        # The two lowest rows sit on the chest, so they take chest weights.
        reweighted=0
        for index,row,target in moved:
            if row<=1:
                source=min(shell,key=lambda s:(s[1].x-target.x)**2+(s[1].y-target.y)**2+(s[1].z-target.z)**2)[0]
                result=outfit.get_vertex_bone_weights(source)
                weights=next((r for r in result if isinstance(r,unreal.Array)),None)
                if not weights:raise RuntimeError('No bone weights on outfit vertex %d'%source)
                outfit.set_vertex_bone_weights(index,weights);reweighted+=1
            outfit.set_vertex_position(index,target)
        write=unreal.GeometryScriptCopyMeshToAssetOptions()
        write.enable_recompute_normals=True;write.enable_recompute_tangents=True
        write.replace_materials=False;write.use_original_vertex_order=True
        target_lod=unreal.GeometryScriptMeshWriteLOD();target_lod.lod_index=0
        result=lib.copy_mesh_to_skeletal_mesh(outfit,asset_mesh,write,target_lod)
        if 'SUCCESS' not in str(result):raise RuntimeError('Outfit write failed: '+str(result))
        save(asset_mesh)
        return json.dumps({'collar_vertices':len(moved),'reweighted':reweighted,
                           'row_radius_front':{r:round(next(v for k,v in rows.items() if k[0]==r and abs(k[1])<.1),2) for r in heights}})
    if operation=='material_params':
        # Run after the import has compiled: earlier, the instances drop these silently.
        lib=unreal.MaterialEditingLibrary
        glow={'Ivory':2.4,'Charcoal':2.4}
        report={}
        for name in ['Ivory','Charcoal','Sash','Boots','GoldTrim']:
            mi=unreal.load_asset(BASE+'/Materials/MI_Physis_'+name)
            texture=unreal.load_asset(BASE+'/Textures/T_Physis_'+name+'_BaseColor')
            # Overrides from before the parent was rebuilt read back fine but do nothing.
            lib.clear_all_material_instance_parameters(mi)
            # This call returns False even when it works, so read the value back below.
            lib.set_material_instance_texture_parameter_value(mi,'BaseColor',texture)
            lib.set_material_instance_scalar_parameter_value(mi,'Metallic',.65 if name=='GoldTrim' else 0)
            lib.set_material_instance_scalar_parameter_value(mi,'DivinityGlow',glow.get(name,0))
            lib.set_material_instance_scalar_parameter_value(mi,'WeaveTiling',3.57 if name=='Ivory' else 1)
            lib.update_material_instance(mi);save(mi)
            used=lib.get_material_instance_texture_parameter_value(mi,'BaseColor')
            report[name]=used.get_name() if used else None
            if report[name]!='T_Physis_'+name+'_BaseColor':raise RuntimeError('BaseColor did not apply to '+name)
        return json.dumps(report)
    if operation=='hair_sparse':
        # A hair Seed has too few values to pick out single strands, so strands are chosen
        # by a hash of Root UV, and each bolt rests between flashes on its own schedule.
        lib=unreal.MaterialEditingLibrary
        material=unreal.load_asset(BASE+'/Materials/M_Physis_Hair')
        nodes=lib.get_material_expressions(material)
        if any(isinstance(n,unreal.MaterialExpressionConstant2Vector) and abs(n.get_editor_property('r')-12.9898)<.001 for n in nodes):
            return json.dumps({'already_sparse':True})
        def node(cls,x,y):return lib.create_material_expression(material,cls,x,y)
        def scaled(source,value,x,y):
            made=node(unreal.MaterialExpressionMultiply,x,y)
            made.set_editor_property('const_b',value)
            lib.connect_material_expressions(source,'',made,'A')
            return made
        def single(cls,source,x,y):
            made=node(cls,x,y)
            lib.connect_material_expressions(source,'',made,'')
            return made
        def inputs(item):
            return lib.get_inputs_for_material_expression(material,item)
        def at(x,y):
            # The shared material has its own nodes of these types, so find ours by position.
            return next(n for n in nodes if tuple(lib.get_material_expression_node_position(n))==(x,y))
        hair=at(-3200,2400);over=at(-2900,2500);sharpened=at(-2700,2500);scatter=at(-2900,2850)
        phase=at(-2500,2800);wrapped=at(-2300,2800);flipped=at(-2100,2900);bump=at(-1900,2800)
        x=-3200
        weights=node(unreal.MaterialExpressionConstant2Vector,x-300,2100)
        weights.set_editor_property('r',12.9898);weights.set_editor_property('g',78.233)
        dot=node(unreal.MaterialExpressionDotProduct,x,2100)
        lib.connect_material_expressions(hair,'Root UV',dot,'A')
        lib.connect_material_expressions(weights,'',dot,'B')
        sine=single(unreal.MaterialExpressionSine,dot,x+200,2100)
        sine.set_editor_property('period',6.2831853)
        strand=single(unreal.MaterialExpressionFrac,scaled(sine,43758.5453,x+400,2100),x+600,2100)
        lib.connect_material_expressions(strand,'',over,'A')
        lib.connect_material_expressions(strand,'',scatter,'A')
        sharpened.set_editor_property('const_b',100000)
        # One flash in three cycles: the rest of the time the strand stays dark.
        lib.connect_material_expressions(scaled(phase,1/3,x+800,3050),'',wrapped,'')
        burst=single(unreal.MaterialExpressionSaturate,scaled(wrapped,3,x+950,3050),x+1100,3050)
        lib.connect_material_expressions(burst,'',flipped,'')
        lib.connect_material_expressions(burst,'',bump,'A')
        # Low detail: fewer streaks, and patches of hair take turns flashing.
        lit=at(-1600,3800);mask=at(-1900,3750)
        at(-2300,3750).set_editor_property('const_b',.72)
        where=node(unreal.MaterialExpressionLocalPosition,x,4900)
        turn=node(unreal.MaterialExpressionConstant3Vector,x,5050)
        turn.set_editor_property('constant',unreal.LinearColor(.4,.7,.2,1))
        spread=node(unreal.MaterialExpressionDotProduct,x+250,4950)
        lib.connect_material_expressions(where,'',spread,'A')
        lib.connect_material_expressions(turn,'',spread,'B')
        clock=node(unreal.MaterialExpressionTime,x,5200)
        moving=node(unreal.MaterialExpressionAdd,x+450,5000)
        lib.connect_material_expressions(spread,'',moving,'A')
        lib.connect_material_expressions(scaled(clock,1.5,x+250,5200),'',moving,'B')
        wave=single(unreal.MaterialExpressionSine,moving,x+650,5000)
        wave.set_editor_property('period',6.2831853)
        above=node(unreal.MaterialExpressionSubtract,x+850,5000)
        above.set_editor_property('const_b',.6)
        lib.connect_material_expressions(wave,'',above,'A')
        gate=single(unreal.MaterialExpressionSaturate,scaled(above,5,x+1050,5000),x+1250,5000)
        gated=node(unreal.MaterialExpressionMultiply,x+1450,4400)
        lib.connect_material_expressions(mask,'',gated,'A')
        lib.connect_material_expressions(gate,'',gated,'B')
        lib.connect_material_expressions(gated,'',lit,'A')
        lib.recompile_material(material);save(material)
        return json.dumps({'sparse':True,'pins':[str(n) for n in lib.get_material_expression_output_names(hair)]})
    if operation.startswith('open_level:'):
        unreal.EditorLoadingAndSavingUtils.load_map(operation.split(':',1)[1])
        return json.dumps({'level':unreal.EditorLevelLibrary.get_editor_world().get_name()})
    if operation=='hair_count':
        groom=unreal.load_asset('/Game/MetaHumans/MH_Physis/Grooms/WI_Hair_M_Layered') or next(a for a in map(unreal.load_asset,unreal.EditorAssetLibrary.list_assets('/Game/MetaHumans/MH_Physis/Grooms',recursive=True)) if isinstance(a,unreal.GroomAsset) and 'Hair_M_Layered' in a.get_name())
        info=groom.get_editor_property('hair_groups_info')
        return json.dumps({'asset':groom.get_name(),'groups':[i.export_text() for i in info]})
    if operation=='hair_cards_shape':
        # Finer, longer, sparser streaks so low detail matches the strand sparks.
        lib=unreal.MaterialEditingLibrary
        material=unreal.load_asset(BASE+'/Materials/M_Physis_Hair')
        def pins(node):
            names=[str(n) for n in lib.get_material_expression_input_names(node)]
            return dict(zip(names,lib.get_inputs_for_material_expression(material,node)))
        def show(node):
            return {n:(i.get_class().get_name() if i else None) for n,i in pins(node).items()}
        switch=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        attributes=lib.get_inputs_for_material_expression(material,switch)[0]
        make=lib.get_inputs_for_material_expression(material,attributes)[0]
        trace={'make':{k:v for k,v in show(make).items() if v}}
        both=next(i for i in pins(make).values() if i)
        trace['both']=show(both)
        cards=list(pins(both).values())[1]
        trace['cards']=show(cards)
        lit=list(pins(cards).values())[0]
        trace['lit']=show(lit)
        mask=list(pins(lit).values())[0]
        trace['mask']=(mask.get_class().get_name(),show(mask))
        sharp=list(pins(mask).values())[0]
        trace['sharp']=show(sharp) if sharp else None
        over=list(pins(sharp).values())[0]
        trace['over']=show(over)
        noise=list(pins(over).values())[0]
        if pins(noise).get('World Position'):
            return json.dumps({'already_wired':True})
        def vector(values,x,y):
            made=lib.create_material_expression(material,unreal.MaterialExpressionConstant3Vector,x,y)
            made.set_editor_property('constant',unreal.LinearColor(values[0],values[1],values[2],1))
            return made
        where=lib.create_material_expression(material,unreal.MaterialExpressionLocalPosition,-3200,4300)
        stretched=lib.create_material_expression(material,unreal.MaterialExpressionMultiply,-2950,4300)
        lib.connect_material_expressions(where,'',stretched,'A')
        lib.connect_material_expressions(vector((5,5,.3),-3200,4450),'',stretched,'B')
        clock=lib.create_material_expression(material,unreal.MaterialExpressionTime,-3200,4600)
        drift=lib.create_material_expression(material,unreal.MaterialExpressionMultiply,-2950,4600)
        lib.connect_material_expressions(clock,'',drift,'A')
        lib.connect_material_expressions(vector((0,0,1.5),-3200,4700),'',drift,'B')
        moving=lib.create_material_expression(material,unreal.MaterialExpressionAdd,-2750,4450)
        lib.connect_material_expressions(stretched,'',moving,'A')
        lib.connect_material_expressions(drift,'',moving,'B')
        wired=lib.connect_material_expressions(moving,'',noise,'World Position')
        over.set_editor_property('const_b',.55)
        sharp.set_editor_property('const_b',40)
        lib.recompile_material(material);save(material)
        return json.dumps({'wired':wired,'noise':show(noise)})
    if operation.startswith('hair_cards:'):
        # hair_cards:GLOW sets the lower-detail hair lightning.
        lib=unreal.MaterialEditingLibrary
        value=float(operation.split(':')[1])
        for name in ('MI_Physis_Hair_Cards','MI_Physis_Hair_Helmet'):
            mi=unreal.load_asset(BASE+'/Materials/'+name)
            lib.set_material_instance_scalar_parameter_value(mi,'LightningCardGlow',value)
            lib.update_material_instance(mi);save(mi)
        return json.dumps({'card_glow':value})
    if operation.startswith('hair_tune:'):
        # hair_tune:GLOW:CUT, for example hair_tune:4:0.9
        _,glow,cut=operation.split(':')
        lib=unreal.MaterialEditingLibrary
        mi=unreal.load_asset(BASE+'/Materials/MI_Physis_Hair')
        lib.set_material_instance_scalar_parameter_value(mi,'LightningGlow',float(glow))
        lib.set_material_instance_scalar_parameter_value(mi,'LightningStrandCut',float(cut))
        lib.update_material_instance(mi);save(mi)
        names=[str(p) for p in lib.get_scalar_parameter_names(unreal.load_asset('/Game/MetaHumans/MH_Physis/Grooms/MI_WI_Hair_M_Layered_Hair'))]
        return json.dumps({'glow':lib.get_material_instance_scalar_parameter_value(mi,'LightningGlow'),
                           'cut':lib.get_material_instance_scalar_parameter_value(mi,'LightningStrandCut'),
                           'groom_has_params':'LightningGlow' in names})
    if operation=='hair_lightning':
        # Bolts travel root to tip along a fraction of the strands, using a copy of
        # the shared hair material. Assembly resets the groom instances: run it after.
        lib=unreal.MaterialEditingLibrary
        library=unreal.EditorAssetLibrary
        common='/Game/MetaHumans/Common/Materials/'
        path=BASE+'/Materials/M_Physis_Hair'
        if not library.does_asset_exist(path):
            material=library.duplicate_asset(common+'M_hair_v4',path)
            switch=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
            attributes=lib.get_inputs_for_material_expression(material,switch)[0]
            def node(cls,x,y):return lib.create_material_expression(material,cls,x,y)
            def param(cls,name,value,x,y):
                made=node(cls,x,y)
                made.set_editor_property('parameter_name',name);made.set_editor_property('default_value',value)
                return made
            def join(cls,a,b,x,y,a_pin='',b_pin=''):
                made=node(cls,x,y)
                lib.connect_material_expressions(a,a_pin,made,'A')
                lib.connect_material_expressions(b,b_pin,made,'B')
                return made
            x=-3200
            hair=node(unreal.MaterialExpressionHairAttributes,x,2400)
            # hair_sparse later replaces Seed here with a hash, for a few single strands.
            cut=param(unreal.MaterialExpressionScalarParameter,'LightningStrandCut',.42,x,2700)
            speed=param(unreal.MaterialExpressionScalarParameter,'LightningSpeed',.4,x,2850)
            glow=param(unreal.MaterialExpressionScalarParameter,'LightningGlow',14,x,3000)
            color=param(unreal.MaterialExpressionVectorParameter,'LightningColor',unreal.LinearColor(1,.48,.12,1),x,3150)
            clock=node(unreal.MaterialExpressionTime,x,3350)
            # Only strands whose random seed passes the cut carry lightning.
            over=join(unreal.MaterialExpressionSubtract,hair,cut,x+300,2500,'Seed','')
            sharpened=node(unreal.MaterialExpressionMultiply,x+500,2500)
            sharpened.set_editor_property('const_b',60)
            lib.connect_material_expressions(over,'',sharpened,'A')
            mask=node(unreal.MaterialExpressionSaturate,x+700,2500)
            lib.connect_material_expressions(sharpened,'',mask,'')
            # Each strand fires on its own schedule, moving along U from root to tip.
            along=node(unreal.MaterialExpressionMultiply,x+300,2700)
            along.set_editor_property('const_b',1.5)
            lib.connect_material_expressions(hair,'U',along,'A')
            scatter=node(unreal.MaterialExpressionMultiply,x+300,2850)
            scatter.set_editor_property('const_b',7)
            lib.connect_material_expressions(hair,'Seed',scatter,'A')
            start=join(unreal.MaterialExpressionAdd,along,scatter,x+500,2750)
            elapsed=join(unreal.MaterialExpressionMultiply,clock,speed,x+500,2950)
            phase=join(unreal.MaterialExpressionSubtract,start,elapsed,x+700,2800)
            wrapped=node(unreal.MaterialExpressionFrac,x+900,2800)
            lib.connect_material_expressions(phase,'',wrapped,'')
            flipped=node(unreal.MaterialExpressionOneMinus,x+1100,2900)
            lib.connect_material_expressions(wrapped,'',flipped,'')
            bump=join(unreal.MaterialExpressionMultiply,wrapped,flipped,x+1300,2800)
            scaled=node(unreal.MaterialExpressionMultiply,x+1500,2800)
            scaled.set_editor_property('const_b',4)
            lib.connect_material_expressions(bump,'',scaled,'A')
            bolt=node(unreal.MaterialExpressionPower,x+1700,2800)
            bolt.set_editor_property('const_exponent',8)
            lib.connect_material_expressions(scaled,'',bolt,'Base')
            lit=join(unreal.MaterialExpressionMultiply,mask,bolt,x+1900,2600)
            bright=join(unreal.MaterialExpressionMultiply,lit,glow,x+2100,2700)
            final=join(unreal.MaterialExpressionMultiply,bright,color,x+2300,2800,'','RGB')
            make=node(unreal.MaterialExpressionMakeMaterialAttributes,x+2500,2800)
            lib.connect_material_expressions(final,'',make,'EmissiveColor')
            # The node ending the graph leaves this input free and does not set emissive.
            lib.connect_material_expressions(make,'',attributes,'MaterialAttributes')
            lib.recompile_material(material);save(material)
        material=unreal.load_asset(path)
        if 'LightningCardGlow' not in [str(p) for p in lib.get_scalar_parameter_names(material)]:
            # Lower detail hair: streaks from noise stretched along the hair, drifting down.
            switch=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
            attributes=lib.get_inputs_for_material_expression(material,switch)[0]
            make=lib.get_inputs_for_material_expression(material,attributes)[0]
            strands=next(i for i in lib.get_inputs_for_material_expression(material,make) if i)
            def node(cls,x,y):return lib.create_material_expression(material,cls,x,y)
            def vector(values,x,y):
                made=node(unreal.MaterialExpressionConstant3Vector,x,y)
                made.set_editor_property('constant',unreal.LinearColor(values[0],values[1],values[2],1))
                return made
            def join(cls,a,b,x,y,b_pin=''):
                made=node(cls,x,y)
                lib.connect_material_expressions(a,'',made,'A')
                lib.connect_material_expressions(b,b_pin,made,'B')
                return made
            x=-3200
            where=node(unreal.MaterialExpressionLocalPosition,x,3600)
            stretched=join(unreal.MaterialExpressionMultiply,where,vector((1.6,1.6,.05),x,3750),x+250,3650)
            clock=node(unreal.MaterialExpressionTime,x,3900)
            drift=join(unreal.MaterialExpressionMultiply,clock,vector((0,0,.5),x,4000),x+250,3900)
            moving=join(unreal.MaterialExpressionAdd,stretched,drift,x+450,3750)
            noise=node(unreal.MaterialExpressionNoise,x+650,3750)
            noise.set_editor_property('turbulence',False)
            noise.set_editor_property('levels',2)
            lib.connect_material_expressions(moving,'',noise,'Position')
            over=node(unreal.MaterialExpressionSubtract,x+900,3750)
            over.set_editor_property('const_b',.42)
            lib.connect_material_expressions(noise,'',over,'A')
            sharp=node(unreal.MaterialExpressionMultiply,x+1100,3750)
            sharp.set_editor_property('const_b',30)
            lib.connect_material_expressions(over,'',sharp,'A')
            mask=node(unreal.MaterialExpressionSaturate,x+1300,3750)
            lib.connect_material_expressions(sharp,'',mask,'')
            glow=node(unreal.MaterialExpressionScalarParameter,x+1300,3900)
            glow.set_editor_property('parameter_name','LightningCardGlow');glow.set_editor_property('default_value',0)
            color=node(unreal.MaterialExpressionVectorParameter,x+1300,4050)
            color.set_editor_property('parameter_name','LightningColor');color.set_editor_property('default_value',unreal.LinearColor(1,.48,.12,1))
            lit=join(unreal.MaterialExpressionMultiply,mask,glow,x+1600,3800)
            cards=join(unreal.MaterialExpressionMultiply,lit,color,x+1800,3800,'RGB')
            both=join(unreal.MaterialExpressionAdd,strands,cards,x+2300,3200)
            lib.connect_material_expressions(both,'',make,'EmissiveColor')
            lib.recompile_material(material);save(material)
        parents={}
        for name,source,parent in (('MI_Physis_Hair','MI_Hair',material),
                                   ('MI_Physis_Hair_Cards','MI_Hair_Cards',None),
                                   ('MI_Physis_Hair_Helmet','MI_Hair_Helmet',None)):
            target=BASE+'/Materials/'+name
            instance=unreal.load_asset(target) if library.does_asset_exist(target) else library.duplicate_asset(common+source,target)
            lib.set_material_instance_parent(instance,parent or parents['MI_Physis_Hair'])
            # Cards and helmet have no per-strand data, so they use the noise streaks instead.
            if not parent:
                lib.set_material_instance_scalar_parameter_value(instance,'LightningGlow',0)
                lib.set_material_instance_scalar_parameter_value(instance,'LightningCardGlow',14)
            lib.update_material_instance(instance);save(instance)
            parents[name]=instance
        linked={}
        for name,parent in (('Hair','MI_Physis_Hair'),('Hair_Cards','MI_Physis_Hair_Cards'),('Hair_Helmet','MI_Physis_Hair_Helmet')):
            groom=unreal.load_asset('/Game/MetaHumans/MH_Physis/Grooms/MI_WI_Hair_M_Layered_'+name)
            lib.set_material_instance_parent(groom,parents[parent])
            lib.update_material_instance(groom);save(groom)
            linked[name]=groom.get_editor_property('parent').get_name()
        return json.dumps(linked)
    if operation=='relink_outfit':
        # A Blueprint loaded while the outfit asset is missing keeps an empty mesh slot.
        bp=unreal.load_asset('/Game/MetaHumans/MH_Physis/BP_MH_Physis')
        mesh=unreal.load_asset(BASE+'/Clothing/SK_Physis_Outfit')
        subobjects=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        found=[]
        for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
            data=unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
            obj=unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
            if isinstance(obj,unreal.SkeletalMeshComponent):
                current=obj.get_editor_property('skeletal_mesh_asset')
                found.append((obj.get_name(),current.get_name() if current else None))
                if obj.get_name().startswith(('SkeletalMesh','PhysisOutfit')):
                    obj.set_skeletal_mesh_asset(mesh)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        return json.dumps({'components_before':found})
    if operation=='export_face_guide':
        # The outfit must also clear the neck and chest bib, which belong to the face mesh.
        task=unreal.AssetExportTask()
        task.object=unreal.load_asset('/Game/MetaHumans/MH_Physis/Face/SKM_MH_Physis_FaceMesh')
        task.filename=str(SOURCE/'physis-face-guide.fbx')
        task.automated=True;task.prompt=False;task.replace_identical=True
        task.exporter=unreal.SkeletalMeshExporterFBX()
        task.options=unreal.FbxExportOption()
        task.options.ascii=False
        if not unreal.Exporter.run_asset_export_task(task):raise RuntimeError('Face guide export failed.')
        return json.dumps({'file':task.filename})
    if operation=='inspect_outfit':
        mesh=unreal.load_asset(BASE+'/Clothing/SK_Physis_Outfit')
        dynamic=unreal.DynamicMesh()
        dynamic,outcome=unreal.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dynamic,
            unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
        report={'slots':[(str(s.material_slot_name),s.material_interface.get_name() if s.material_interface else None) for s in mesh.materials],
                'vertices':dynamic.get_vertex_count(),
                'triangles_by_material':{}}
        ids=dynamic.get_all_triangle_material_i_ds()
        ids=next((r for r in ids if isinstance(r,unreal.GeometryScriptIndexList)),None) if isinstance(ids,tuple) else ids
        for material_id in unreal.GeometryScript_List.convert_index_list_to_array(ids):
            key=str(material_id);report['triangles_by_material'][key]=report['triangles_by_material'].get(key,0)+1
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for actor in actors.get_all_level_actors():
            if actor.get_actor_label()=='Physis_Studio_Character':
                for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                    name=component.get_name()
                    if name not in ('Body','Face'):
                        used=component.get_editor_property('skeletal_mesh_asset')
                        report[name]={'mesh':used.get_name() if used else None,
                                      'materials':[m.get_name() if m else None for m in component.get_materials()],
                                      'overrides':[m.get_name() if m else None for m in component.get_editor_property('override_materials')]}
        return json.dumps(report)
    if operation=='inspect_brow_component':
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='Physis_Studio_Character')
        report={}
        for component in actor.get_components_by_class(unreal.SceneComponent):
            if component.get_name() in ('Eyebrows','Hair'):
                groom=component.get_editor_property('groom_asset') if hasattr(component,'groom_asset') else None
                report[component.get_name()]={'class':component.get_class().get_name(),'groom':groom.get_path_name() if groom else None,
                    'materials':[m.get_path_name() if m else None for m in component.get_materials()] if hasattr(component,'get_materials') else None}
        face=next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name()=='Face')
        report['face_materials']=[m.get_name() if m else None for m in face.get_materials()][:12]
        return json.dumps(report)
    if operation=='brow_color':
        # Assembly leaves the groom's Region color at its reddish default.
        lib=unreal.MaterialEditingLibrary
        changed=[]
        for name in ('MI_WI_Eyebrows_M_Full_Hair','MI_WI_Eyebrows_M_Full_Facial_Hair'):
            mi=unreal.load_asset('/Game/MetaHumans/MH_Physis/Grooms/'+name)
            if not mi:raise RuntimeError('Missing '+name)
            lib.set_material_instance_scalar_parameter_value(mi,'RegionMelanin',.95)
            lib.set_material_instance_scalar_parameter_value(mi,'RegionRedness',.04)
            lib.set_material_instance_vector_parameter_value(mi,'hairDye',unreal.LinearColor(.12,.1,.09,1))
            lib.update_material_instance(mi)
            save(mi);changed.append(name)
        return json.dumps({'updated':changed})
    if operation=='inspect_brows':
        asset,sub=character()
        collection=sub.get_preview_collection(asset)
        report={'selections':[(str(s.selection.slot_name),str(s.selection.selected_item)) for s in collection.default_instance.get_slot_selection_data()]}
        def values(item_key):
            found={}
            for param in collection.default_instance.get_instance_parameters(unreal.MetaHumanPaletteItemPath(item_key=item_key)):
                name=str(param.name)
                if name in ('Melanin','Redness','Lightness','Whiteness','Roughness'):
                    found[name]=param.get_float() if hasattr(param,'get_float') else None
            return found
        report['items']={str(s.selection.slot_name):values(s.selection.selected_item) for s in collection.default_instance.get_slot_selection_data()
                         if str(s.selection.slot_name) in ('Hair','Eyebrows')}
        materials={}
        registry=unreal.AssetRegistryHelpers.get_asset_registry()
        for data in registry.get_assets_by_path('/Game/MetaHumans/MH_Physis/Grooms',recursive=False):
            name=str(data.asset_name)
            if name.startswith('MI_') and ('Eyebrows' in name or 'Hair_M_Layered' in name):
                mi=data.get_asset();lib=unreal.MaterialEditingLibrary
                scalars={}
                for p in lib.get_scalar_parameter_names(mi):
                    value=lib.get_material_instance_scalar_parameter_value(mi,p)
                    if any(k in str(p).lower() for k in ('melanin','red','light','white','color','dye')):
                        scalars[str(p)]=round(value,3)
                vectors={}
                for p in lib.get_vector_parameter_names(mi):
                    if any(k in str(p).lower() for k in ('color','tint','dye')):
                        c=lib.get_material_instance_vector_parameter_value(mi,p);vectors[str(p)]=[round(c.r,3),round(c.g,3),round(c.b,3)]
                materials[name]={'parent':mi.get_editor_property('parent').get_name(),'scalars':scalars,'vectors':vectors}
        report['materials']=materials
        return json.dumps(report,default=str)
    if operation=='refine_look':
        # Concept coloring: soft grey-blue eyes, warmer skin, visible light freckles.
        asset,sub=character()
        eyes=asset.get_editor_property('eyes_settings')
        for eye in (eyes.eye_left,eyes.eye_right):
            eye.iris.global_saturation=.75
            eye.iris.primary_color_v=.55;eye.iris.secondary_color_v=.55
        sub.commit_eyes_settings(asset,eyes)
        skin=asset.skin_settings
        skin.skin.u=.30;skin.skin.v=.55
        skin.freckles.density=.5;skin.freckles.strength=.65
        sub.commit_skin_settings(asset,skin)
        save(asset)
        return json.dumps({'saved':True})
    if operation=='measure_neck':
        # Radial reach of face and outfit around the neck, per height band.
        lib=unreal.GeometryScript_AssetUtils
        def rows(path):
            mesh=unreal.DynamicMesh()
            opts=unreal.GeometryScriptCopyMeshFromAssetOptions()
            target=unreal.GeometryScriptMeshReadLOD()
            mesh,outcome=lib.copy_mesh_from_skeletal_mesh(unreal.load_asset(path),mesh,opts,target)
            return mesh,str(outcome)
        face,o1=rows('/Game/MetaHumans/MH_Physis/Face/SKM_MH_Physis_FaceMesh')
        outfit,o2=rows(BASE+'/Clothing/SK_Physis_Outfit')
        methods=[x for x in dir(face) if 'vertex' in x.lower() or 'bvh' in x.lower() or 'nearest' in x.lower() or 'normal' in x.lower()]
        count=face.get_vertex_count()
        def bands(mesh):
            out={}
            result=mesh.get_all_vertex_positions(False)
            if isinstance(result,tuple):
                result=next(r for r in result if not isinstance(r,unreal.DynamicMesh) and not isinstance(r,bool))
            points=unreal.GeometryScript_List.convert_vector_list_to_array(result)
            for p in points:
                if 118<p.z<155:
                    band=int(p.z//4*4);b=out.setdefault(band,[99,-99,99,-99,0])
                    b[0]=min(b[0],p.x);b[1]=max(b[1],p.x);b[2]=min(b[2],p.y);b[3]=max(b[3],p.y);b[4]+=1
            return {k:[round(v,1) for v in out[k]] for k in sorted(out)}
        return json.dumps({'face':o1,'outfit':o2,'face_vertices':count,'methods':methods,
                           'to_skel_doc':lib.copy_mesh_to_skeletal_mesh.__doc__[:900],
                           'face_bands':bands(face),'outfit_bands':bands(outfit)})
    if operation=='live_review':
        # Hide the baked studio actor and show the live Creator preview in its place.
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for actor in actors.get_all_level_actors():
            if actor.get_actor_label()=='Physis_Studio_Character':
                actor.set_is_temporarily_hidden_in_editor(True)
        return json.dumps({'preview_actor':preview_actor().get_path_name()})
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
        # build_meta_human only logs a refusal, so check this first.
        if not asset.get_editor_property('has_high_resolution_textures'):
            raise RuntimeError('Assembly would be refused: run textures_save first.')
        # Baking runs on the GPU; on 2026-10-30 a full VRAM stalled the whole laptop.
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_viewport_realtime(False)
        trimmed=json.loads(execute('trim_preview_textures'))
        params=unreal.MetaHumanCharacterEditorBuildParameters()
        params.pipeline_type=unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        params.pipeline_quality=unreal.MetaHumanQualityLevel.MEDIUM
        params.absolute_build_path='/Game/MetaHumans'
        params.common_folder_path='/Game/MetaHumans/Common'
        params.enable_wardrobe_item_validation=False
        sub.build_meta_human(asset,params)
        # Saving renders thumbnails; free the baking memory first or Vulkan runs out.
        unreal.SystemLibrary.collect_garbage()
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
