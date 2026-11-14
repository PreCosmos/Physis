# A staged combat shot as a level sequence, from combat_arg.json:
#   physis: possess (tag CineOnly) or spawn (BP class); keys [[frame, x, y, z, yaw]]; anims [[start, end, path, rate, offset_s]];
#           weapon {mesh, material, loc, rot [roll, pitch, yaw], scale}
#   meshes: spawnable static meshes {mesh, material?, scale [x,y,z], keys [[frame, x, y, z, roll, pitch, yaw]], range [f0, f1]}
#   fx: spawnable effect actors {class, at [x, y, z], rot [roll, pitch, yaw], frame, len}
#   cameras: [{name, frames, from [x, y, z, yaw, pitch], to [...], focal}]
import json
import os
A = json.load(open(os.environ.get('COMBAT_ARG', '/home/precosmos/PhysisProject/Tools/trailer/combat_arg.json')))
lib = unreal.EditorAssetLibrary
path = A['sequence']
folder, name = path.rsplit('/', 1)
if lib.does_asset_exist(path):
    seq = unreal.load_asset(path)
    for b in list(seq.get_bindings()):
        b.remove()
    for tr in list(seq.get_tracks()):
        seq.remove_track(tr)
else:
    seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(30, 1))
seq.set_tick_resolution(unreal.FrameRate(30, 1))
total = A['frames']
seq.set_playback_start(0)
seq.set_playback_end(total)
report, notes = {}, []
F = lambda f: unreal.FrameNumber(int(f))

def transform_keys(binding, keys, start=0, end=None):
    sec = binding.add_track(unreal.MovieScene3DTransformTrack).add_section()
    sec.set_range(start, end if end is not None else total)
    ch = sec.get_all_channels()
    for k in keys:
        frame, vals = k[0], k[1:]
        for i, v in enumerate(vals):
            ch[i].add_key(F(frame), float(v))
    return sec

def spawn_window(binding, f0, f1):
    tracks = binding.find_tracks_by_type(unreal.MovieSceneSpawnTrack)
    track = tracks[0] if tracks else binding.add_track(unreal.MovieSceneSpawnTrack)
    secs = track.get_sections()
    sec = secs[0] if secs else track.add_section()
    sec.set_range(0, total)
    ch = sec.get_all_channels()[0]
    ch.set_default(False)
    for k in list(ch.get_keys()):
        ch.remove_key(k)
    if f0 > 0:
        ch.add_key(F(0), False)
    ch.add_key(F(f0), True)
    if f1 < total:
        ch.add_key(F(f1), False)

# Physis
ph = A['physis']
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if ph.get('possess'):
    actor = next(a for a in sub.get_all_level_actors() if ph['possess'] in [str(t) for t in a.tags])
    pb = seq.add_possessable(actor)
    body_obj = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
    body = seq.add_possessable(body_obj)
    body.set_parent(pb)
else:
    pb = seq.add_spawnable_from_class(unreal.load_asset(ph['spawn']).generated_class())
    body = None
    notes.append('spawned physis: body via component binding not available; anims on actor binding')
pb.set_display_name('Physis')
# Actor keys are x, y, z, yaw: the transform channels are x, y, z, roll, pitch, yaw.
transform_keys(pb, [[k[0], k[1], k[2], k[3], 0.0, 0.0, k[4]] for k in ph['keys']])
anim_target = body if body is not None else pb
track = anim_target.add_track(unreal.MovieSceneSkeletalAnimationTrack)
for start, end, apath, rate, offset in ph['anims']:
    sec = track.add_section()
    sec.set_range(int(start), int(end))
    params = sec.get_editor_property('params')
    params.set_editor_property('animation', unreal.load_asset(apath))
    pr = params.get_editor_property('play_rate')
    pr.set_fixed_play_rate(float(rate))
    params.set_editor_property('play_rate', pr)
    params.set_editor_property('start_frame_offset', unreal.FrameNumber(int(round(offset * 30))))
    params.set_editor_property('force_custom_mode', True)
    sec.set_editor_property('params', params)
report['anims'] = len(ph['anims'])
# Weapon on hand_r
w = ph.get('weapon')
if w:
    wb = seq.add_spawnable_from_class(unreal.StaticMeshActor)
    wb.set_display_name('Weapon')
    tpl = wb.get_object_template()
    smc = tpl.get_editor_property('static_mesh_component')
    smc.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    smc.set_editor_property('static_mesh', unreal.load_asset(w['mesh']))
    smc.set_editor_property('override_materials', [unreal.load_asset(w['material'])])
    smc.set_collision_profile_name('NoCollision')
    att = wb.add_track(unreal.MovieScene3DAttachTrack).add_section()
    att.set_range(0, total)
    try:
        att.set_constraint_binding_id(seq.get_binding_id(pb))
    except Exception as error:
        notes.append('attach binding: %s' % error)
    for key, value in (('attach_socket_name', 'hand_r'), ('attach_component_name', 'Body')):
        try:
            att.set_editor_property(key, value)
        except Exception as error:
            notes.append('attach %s: %s' % (key, error))
    r = w['rot']
    sec = wb.add_track(unreal.MovieScene3DTransformTrack).add_section()
    sec.set_range(0, total)
    ch = sec.get_all_channels()
    for i, v in enumerate(list(w['loc']) + [r[0], r[1], r[2]] + [w['scale']] * 3):
        ch[i].set_default(float(v))
    report['weapon'] = True
# Static meshes (enemies, bolts, tracers)
for m in A.get('meshes', []):
    mb = seq.add_spawnable_from_class(unreal.StaticMeshActor)
    mb.set_display_name(m.get('name', 'Mesh'))
    tpl = mb.get_object_template()
    smc = tpl.get_editor_property('static_mesh_component')
    smc.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    smc.set_editor_property('static_mesh', unreal.load_asset(m['mesh']))
    if m.get('material'):
        smc.set_editor_property('override_materials', [unreal.load_asset(m['material'])])
    smc.set_collision_profile_name('NoCollision')
    smc.set_editor_property('cast_shadow', bool(m.get('shadow', True)))
    sx, sy, sz = m.get('scale', [1, 1, 1])
    transform_keys(mb, [list(k) + [sx, sy, sz] for k in m['keys']])
    if m.get('range'):
        spawn_window(mb, m['range'][0], m['range'][1])
report['meshes'] = len(A.get('meshes', []))
# Effects
for e in A.get('fx', []):
    eb = seq.add_spawnable_from_class(unreal.load_asset(e['class']).generated_class())
    eb.set_display_name(e['class'].rsplit('/', 1)[1])
    x, y, z = e['at']
    r = e.get('rot', [0, 0, 0])
    transform_keys(eb, [[e['frame'], x, y, z, r[0], r[1], r[2]]])
    spawn_window(eb, e['frame'], e['frame'] + e['len'])
report['fx'] = len(A.get('fx', []))
# Cameras
cuts = seq.add_track(unreal.MovieSceneCameraCutTrack)
frame = 0
for shot in A['cameras']:
    cam = seq.add_spawnable_from_class(unreal.CineCameraActor)
    cam.set_display_name(shot['name'])
    comp = cam.get_object_template().get_editor_property('camera_component')
    comp.set_editor_property('filmback', unreal.CameraFilmbackSettings(sensor_width=23.76, sensor_height=13.365))
    comp.set_editor_property('current_focal_length', float(shot.get('focal', 24.0)))
    fs = comp.get_editor_property('focus_settings')
    fs.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
    comp.set_editor_property('focus_settings', fs)
    n = shot['frames']
    keys = [[frame] + [shot['from'][0], shot['from'][1], shot['from'][2], 0.0, shot['from'][4], shot['from'][3]],
            [frame + n] + [shot['to'][0], shot['to'][1], shot['to'][2], 0.0, shot['to'][4], shot['to'][3]]]
    transform_keys(cam, keys, frame, frame + n)
    cut = cuts.add_section()
    cut.set_range(frame, frame + n)
    cut.set_camera_binding_id(seq.get_binding_id(cam))
    frame += n
lib.save_asset(path, False)
report['notes'] = notes
RESULT = report
