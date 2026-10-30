"""Physis character production operations, exposed through Unreal's MCP registry."""
import json
from pathlib import Path
import unreal
from toolset_registry import tool_call

ASSET = '/Game/Characters/Physis/MH_Physis'
ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
SOURCE = ROOT / 'Art/Characters/Physis'
_preview = None


def character():
    asset = unreal.load_asset(ASSET)
    if not asset:
        raise RuntimeError('Create MH_Physis before using this toolset.')
    sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not sub.is_object_added_for_editing(asset):
        if not sub.try_add_object_to_edit(asset):
            raise RuntimeError('Could not register Physis for editing.')
    return asset, sub


def output(data):
    return json.dumps(data, default=str)


def preview_actor():
    global _preview
    asset, sub = character()
    if _preview is None or not unreal.SystemLibrary.is_valid(_preview):
        _preview = sub.spawn_meta_human_actor(asset, True)
        if not _preview:
            raise RuntimeError('MetaHuman preview actor could not be created.')
        _preview.set_actor_label('Physis_Character_Preview')
        _preview.set_actor_location(unreal.Vector(0, 0, 0), False, False)
    return _preview


@unreal.uclass()
class PhysisCharacterTools(unreal.ToolsetDefinition):
    """Create and inspect Physis using the approved concept; no general script execution."""

    @tool_call
    def configure_identity() -> str:
        """Apply Physis's face, proportions, freckles, eyes, and dark loose hair, then save."""
        asset, sub = character()
        preset = unreal.load_asset('/MetaHumanCharacter/Optional/Presets/Ada')
        if not preset:
            raise RuntimeError('Ada face foundation is unavailable.')
        added = False
        if not sub.is_object_added_for_editing(preset):
            added = sub.try_add_object_to_edit(preset)
        try:
            coefficients = sub.get_face_model_coefficients(preset)
            sub.set_face_model_coefficients(asset, coefficients)
            sub.commit_face_state(asset)
        finally:
            if added:
                sub.remove_object_to_edit(preset)

        from metahuman_toolset.metahuman import MetaHumanToolset, BodyShape, EyeColor
        from metahuman_toolset.session import get_or_create_session
        session = get_or_create_session(ASSET)
        body = BodyShape()
        body.height_cm = 168.0
        body.masculine_feminine = 0.85
        body.fat = 0.18
        body.muscularity = 0.30
        MetaHumanToolset.set_body_shape(session, body)
        eyes = EyeColor()
        eyes.temperature = 0.12
        eyes.brightness = 0.65
        MetaHumanToolset.set_eye_color(session, eyes)

        skin = asset.skin_settings
        skin.skin.u = 0.22
        skin.skin.v = 0.52
        skin.skin.roughness = 1.05
        skin.freckles.density = 0.24
        skin.freckles.strength = 0.38
        skin.freckles.saturation = 0.55
        skin.freckles.tone_shift = 0.12
        skin.freckles.mask = unreal.MetaHumanCharacterFrecklesMask.TYPE2
        sub.commit_skin_settings(asset, skin)
        collection = sub.get_preview_collection(asset)
        hair = unreal.load_asset('/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_L_MessyClumps')
        if hair:
            key = collection.try_add_item_from_wardrobe_item('Hair', hair)
            selection = unreal.MetaHumanPipelineSlotSelection(slot_name='Hair', selected_item=key)
            if not collection.default_instance.try_add_slot_selection(selection):
                raise RuntimeError('Could not select hair.')
            sub.on_edit_preview_collection(asset)
            sub.assemble_for_preview(asset)
            params = collection.default_instance.get_instance_parameters(unreal.MetaHumanPaletteItemPath(item_key=key))
            for param in params:
                if str(param.name) == 'Melanin':
                    param.set_float(0.9)
                elif str(param.name) == 'Redness':
                    param.set_float(0.14)
            sub.on_edit_preview_collection(asset)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
        return output({'asset': ASSET, 'face_foundation': 'Ada', 'height_cm': 168,
                       'hair': hair.get_path_name() if hair else None,
                       'note': 'Concept likeness pass; exact facial match requires visual review.'})

    @tool_call
    def inspect_character() -> str:
        """Read Physis's saved identity, texture readiness, preview meshes, and relevant API availability."""
        asset, sub = character()
        actor = preview_actor()
        meshes = []
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            mesh = component.get_editor_property('skeletal_mesh_asset')
            meshes.append({'component': component.get_name(), 'mesh': mesh.get_path_name() if mesh else None,
                           'skeleton': mesh.skeleton.get_path_name() if mesh and mesh.skeleton else None})
        data = {'asset': asset.get_path_name(), 'preview_actor': actor.get_path_name(),
                'has_high_resolution_textures': asset.get_editor_property('has_high_resolution_textures'),
                'meshes': meshes,
                'face_texture_count': len(asset.get_editor_property('synthesized_face_textures')),
                'cloud_functions': [x for x in dir(sub) if any(k in x for k in ('rigging','texture_sources','rig_state'))]}
        SOURCE.mkdir(parents=True, exist_ok=True)
        (SOURCE / 'editor-inspection.json').write_text(output(data), encoding='utf-8')
        return output(data)

    @tool_call
    def open_character() -> str:
        """Open Physis in MetaHuman Creator and spawn her transient preview in the editor."""
        asset, _ = character()
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([asset])
        return output({'asset': asset.get_path_name(), 'preview_actor': preview_actor().get_path_name()})

    @tool_call
    def request_face_rig() -> str:
        """Request Physis's face rig from Epic; may present Epic sign-in. Check state before retrying."""
        asset, sub = character()
        params = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        params.blocking = False
        params.report_progress = True
        params.rig_type = unreal.MetaHumanRigType.JOINTS_AND_BLEND_SHAPES
        sub.request_auto_rigging(asset, params)
        return output({'request': 'face_rig', 'submitted': True})

    @tool_call
    def request_texture_sources() -> str:
        """Request the character's high-resolution skin sources from Epic. May require sign-in."""
        asset, sub = character()
        params = unreal.MetaHumanCharacterTextureRequestParams()
        params.blocking = False
        params.report_progress = True
        sub.request_texture_sources(asset, params)
        return output({'request': 'texture_sources', 'submitted': True})

    @tool_call
    def export_body_guide() -> str:
        """Export the current preview body and skeleton as FBX for fitting Physis's custom garments."""
        actor = preview_actor()
        candidates = []
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            mesh = component.get_editor_property('skeletal_mesh_asset')
            if mesh:
                candidates.append((component.get_name(), mesh))
        body = next((m for n,m in candidates if 'body' in n.lower()), None)
        if not body:
            raise RuntimeError('Preview body mesh not found: '+str([n for n,m in candidates]))
        SOURCE.mkdir(parents=True, exist_ok=True)
        task = unreal.AssetExportTask()
        task.object = body
        task.filename = str(SOURCE / 'physis-body-guide.fbx')
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        task.exporter = unreal.SkeletalMeshExporterFBX()
        task.options = unreal.FbxExportOption()
        task.options.ascii = False
        if not unreal.Exporter.run_asset_export_task(task):
            raise RuntimeError('Body guide FBX export failed.')
        return output({'file': task.filename, 'body': body.get_path_name(),
                       'skeleton': body.skeleton.get_path_name() if body.skeleton else None})

    @tool_call
    def assemble_character() -> str:
        """Build Physis's optimized runtime MetaHuman; requires completed cloud rig and texture requests."""
        asset, sub = character()
        params = unreal.MetaHumanCharacterEditorBuildParameters()
        params.pipeline_type = unreal.MetaHumanDefaultPipelineType.OPTIMIZED
        params.pipeline_quality = unreal.MetaHumanQualityLevel.MEDIUM
        params.absolute_build_path = '/Game/MetaHumans'
        params.common_folder_path = '/Game/MetaHumans/Common'
        params.enable_wardrobe_item_validation = False
        sub.build_meta_human(asset, params)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
        return output({'build_requested': True, 'output_root': '/Game/MetaHumans'})

    @tool_call
    def outfit_operation(operation: str) -> str:
        """Run a fixed Physis garment production operation: inspect, import, wardrobe, studio, or verify."""
        import importlib
        import physis_outfit_tools
        importlib.reload(physis_outfit_tools)
        return physis_outfit_tools.execute(operation)


def register():
    unreal.ToolsetRegistry.register_toolset_class(PhysisCharacterTools)
    unreal.log('Physis character tools registered for MCP.')
