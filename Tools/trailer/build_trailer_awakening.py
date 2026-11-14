# SEQ_Trailer_Awakening: SEQ_Awakening (camera, fade, rise light) plus the stand-in's wake-up clips from frame 0, as
# BP_Awakening CineEach(0) plays them in the game (Body A_Physis_GetUp, Face A_Physis_EyesOpen).
lib = unreal.EditorAssetLibrary
SRC, DST = '/Game/Center/Cinema/SEQ_Awakening', '/Game/Trailer/SEQ_Trailer_Awakening'
if lib.does_asset_exist(DST):
    lib.delete_asset(DST)
seq = lib.duplicate_asset(SRC, DST)
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cine = next(a for a in sub.get_all_level_actors() if 'CineOnly' in [str(t) for t in a.tags])
actor_binding = seq.add_possessable(cine)
clips = {'Body': ('/Game/Characters/Physis/Animations/A_Physis_GetUp', 600), 'Face': ('/Game/Center/Cinema/A_Physis_EyesOpen', 420)}
out = {'actor': cine.get_actor_label()}
for comp in cine.get_components_by_class(unreal.SkeletalMeshComponent):
    if comp.get_name() not in clips:
        continue
    path, frames = clips[comp.get_name()]
    b = seq.add_possessable(comp)
    try:
        if b.get_parent().get_id() != actor_binding.get_id():
            b.set_parent(actor_binding)
    except Exception as error:
        b.set_parent(actor_binding)
    track = b.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    sec = track.add_section()
    sec.set_range(0, frames)
    params = sec.get_editor_property('params')
    params.set_editor_property('animation', unreal.load_asset(path))
    try:
        params.set_editor_property('force_custom_mode', True)
    except Exception as error:
        out['custom_mode_error'] = str(error)
    sec.set_editor_property('params', params)
    out[comp.get_name()] = [str(b.get_display_name()), str(b.get_parent().get_display_name()), frames]
lib.save_asset(DST, False)
out['bindings'] = [str(x.get_display_name()) for x in seq.get_bindings()]
RESULT = out
