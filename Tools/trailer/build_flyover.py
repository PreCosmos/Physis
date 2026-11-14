# A trailer flyover sequence: one spawnable cine camera per shot (the level is untouched), a straight eased move from
# start to end (x, y, height above ground, yaw, pitch), a camera cut per shot. Args from flyover_arg.json.
import json, importlib
import physis_center_tools as t
a = json.load(open('/home/precosmos/PhysisProject/Tools/trailer/flyover_arg.json'))
lib = unreal.EditorAssetLibrary
path = a['sequence']
folder, name = path.rsplit('/', 1)
if lib.does_asset_exist(path):
    seq = unreal.load_asset(path)  # reused and emptied (delete then create in one go can fail while it is loaded)
    for b in list(seq.get_bindings()):
        b.remove()
    for tr in list(seq.get_tracks()):
        seq.remove_track(tr)
else:
    seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(30, 1))
seq.set_tick_resolution(unreal.FrameRate(30, 1))
ground = t.Ground() if a.get('center', True) else None
def place(x, y, h, absolute):
    return h if absolute or ground is None else max(ground.at(x, y), 0.0) + h
cuts = seq.add_track(unreal.MovieSceneCameraCutTrack)
frame, report = 0, []
for shot in a['shots']:
    n = shot['frames']
    cam = seq.add_spawnable_from_class(unreal.CineCameraActor)
    cam.set_display_name(shot['name'])
    tpl = cam.get_object_template()
    comp = tpl.get_editor_property('camera_component')
    comp.set_editor_property('filmback', unreal.CameraFilmbackSettings(sensor_width=23.76, sensor_height=13.365))
    comp.set_editor_property('current_focal_length', float(shot.get('focal', 18.0)))
    comp.set_editor_property('current_aperture', 8.0)
    fs = comp.get_editor_property('focus_settings')
    fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
    comp.set_editor_property('focus_settings', fs)
    track = cam.add_track(unreal.MovieScene3DTransformTrack)
    sec = track.add_section()
    sec.set_range(frame, frame + n)
    ch = sec.get_all_channels()
    for key_frame, (x, y, h, yaw, pitch) in ((frame, shot['from']), (frame + n, shot['to'])):
        z = place(x, y, h, shot.get('absolute', False))
        for index, value in ((0, x), (1, y), (2, z), (3, 0.0), (4, pitch), (5, yaw)):
            ch[index].add_key(unreal.FrameNumber(key_frame), float(value))
    cut = cuts.add_section()
    cut.set_range(frame, frame + n)
    cut.set_camera_binding_id(seq.get_binding_id(cam))
    report.append([shot['name'], frame, frame + n])
    frame += n
seq.set_playback_start(0)
seq.set_playback_end(frame)
lib.save_asset(path, False)
RESULT = {'shots': report, 'frames': frame}
