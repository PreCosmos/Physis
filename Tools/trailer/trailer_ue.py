"""Editor side of the trailer (run inside Unreal through Tools/trailer/tt.py).

build(level): makes /Game/Trailer/V2/SEQ_T2_<level> from Tools/trailer/shots.py: one spawnable cine camera and one
camera cut per shot, so Movie Render Queue renders each shot on its own with its own warm-up.
render(level, ...): renders that sequence in the map open in the editor to Saved/Trailer/v2/frames/<level>/<shot>.NNNN.jpeg
and writes Saved/Trailer/v2/frames/<level>/_done.json when it ends.
"""
import importlib
import json
import math
import os
import sys

import unreal

ROOT = '/mnt/Games/Unreal Projects/Physis'
sys.path.insert(0, ROOT + '/Tools/trailer')
FPS = 30
FOLDER = '/Game/Trailer/V2'
FRAMES = ROOT + '/Saved/Trailer/v2/frames'
RISE_LIGHT = .15  # SEQ_Awakening's light at full power bleaches her skin in close-ups
HANDLE = 0  # shots are rendered at their exact length; the cut does the trimming


def shots_for(level):
    import shots
    importlib.reload(shots)
    return shots.LEVELS[level]


def rotation(eye, look, roll=0.0):
    dx, dy, dz = (look[i] - eye[i] for i in range(3))
    return roll, math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx))


def smooth(u):
    return u * u * (3 - 2 * u)


def pose(shot, u):
    """Camera position, look-at point and roll at u (0..1) of a shot: straight between keys, eased if asked."""
    keys = shot['keys']
    if shot.get('ease'):
        u = smooth(u)
    for a, b in zip(keys, keys[1:]):
        if u <= b[0] or b is keys[-1]:
            k = min(1.0, max(0.0, (u - a[0]) / (b[0] - a[0])))
            mix = lambda p, q: tuple(p[i] + (q[i] - p[i]) * k for i in range(3))
            ra, rb = (a[3] if len(a) > 3 else 0.0), (b[3] if len(b) > 3 else 0.0)
            return mix(a[1], b[1]), mix(a[2], b[2]), ra + (rb - ra) * k


def dense(shot):
    """The keys to write: the shot's own, or one per frame for an eased move or one that turns about its target."""
    keys = shot['keys']
    if not shot.get('ease') and len(keys) == 2 and len(keys[0]) < 4:
        return keys
    n = shot['frames']
    return [(i / (n - 1),) + pose(shot, i / (n - 1)) for i in range(n)]


def awakening(seq, data, starts):
    """Binds the stand-in Physis: each shot plays the get-up clip and the eye clip from its own second."""
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    physis = [a for a in actors if a.get_actor_label() == 'Cine Physis'][0]
    parent = seq.add_possessable(physis)
    tick = seq.get_tick_resolution()
    per_second = tick.numerator / tick.denominator
    clips = {'Body': ('/Game/Characters/Physis/Animations/A_Physis_GetUp', 20.0), 'Face': ('/Game/Center/Cinema/A_Physis_EyesOpen', 14.0)}
    for part in physis.get_components_by_class(unreal.SkeletalMeshComponent):
        if part.get_name() not in clips:
            continue
        path, length = clips[part.get_name()]
        binding = seq.add_possessable(part)
        binding.set_parent(parent)
        track = binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
        for shot in data['shots']:
            at, n = shot['anim'], shot['frames']
            frames = min(n, int((length - at) * FPS))
            if frames <= 0:
                continue
            section = track.add_section()
            section.set_range(starts[shot['name']], starts[shot['name']] + frames)
            params = section.get_editor_property('params')
            params.set_editor_property('animation', unreal.load_asset(path))
            params.set_editor_property('force_custom_mode', True)
            params.set_editor_property('first_loop_start_frame_offset', unreal.FrameNumber(int(round(at * per_second))))
            section.set_editor_property('params', params)
    # The glow that lifts her as she rises (SEQ_Awakening's light track, by clip time).
    lights = [a for a in actors if a.get_actor_label() == 'Cine Rise Light']
    if lights:
        comp = lights[0].get_component_by_class(unreal.PointLightComponent)
        light = seq.add_possessable(comp)
        light.set_parent(seq.add_possessable(lights[0]))
        power = light.add_track(unreal.MovieSceneFloatTrack)
        power.set_property_name_and_path('Intensity', 'Intensity')
        section = power.add_section()
        section.set_range(0, sum(s['frames'] for s in data['shots']))
        channel = section.get_all_channels()[0]
        table = ((0, 0), (4.5, 0), (4.7, 2500), (6.5, 800), (10.0, 1200), (11.5, 3500), (14.5, 6000), (16.5, 1200), (19, 0), (40, 0))
        for shot in data['shots']:
            for i in range(0, shot['frames'], 3):
                t = shot['anim'] + i / FPS
                for (ta, va), (tb, vb) in zip(table, table[1:]):
                    if ta <= t <= tb:
                        channel.add_key(unreal.FrameNumber(starts[shot['name']] + i), float(va + (vb - va) * (t - ta) / (tb - ta)) * RISE_LIGHT, 0.0, unreal.MovieSceneTimeUnit.DISPLAY_RATE, unreal.MovieSceneKeyInterpolation.LINEAR)
                        break


def build(level):
    data = shots_for(level)
    name = 'SEQ_T2_' + level
    path = FOLDER + '/' + name
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    lib = unreal.EditorAssetLibrary
    if lib.does_asset_exist(FOLDER + '/SEQ_Probe'):
        lib.delete_asset(FOLDER + '/SEQ_Probe')
    if lib.does_asset_exist(path):
        lib.delete_asset(path)
    seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, FOLDER, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(FPS, 1))
    total = sum(s['frames'] for s in data['shots'])
    seq.set_playback_start(0)
    seq.set_playback_end(total)
    cuts = seq.add_track(unreal.MovieSceneCameraCutTrack)
    start = 0
    starts = {}
    for shot in data['shots']:
        n = shot['frames']
        starts[shot['name']] = start
        cam = seq.add_spawnable_from_class(unreal.CineCameraActor)
        cam.set_display_name(shot['name'])
        template = cam.get_object_template()
        lens = template.get_editor_property('camera_component')
        lens.set_editor_property('constrain_aspect_ratio', False)
        lens.set_editor_property('current_focal_length', float(shot.get('focal', 24)))
        focus = lens.get_editor_property('focus_settings')
        if shot.get('focus'):
            focus.set_editor_property('focus_method', unreal.CameraFocusMethod.MANUAL)
            focus.set_editor_property('manual_focus_distance', float(shot['focus']))
            lens.set_editor_property('current_aperture', float(shot.get('aperture', 2.8)))
        else:
            focus.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
        lens.set_editor_property('focus_settings', focus)
        if shot.get('ev') is not None:
            pp = lens.get_editor_property('post_process_settings')
            pp.set_editor_property('override_auto_exposure_bias', True)
            pp.set_editor_property('auto_exposure_bias', float(shot['ev']))
            lens.set_editor_property('post_process_settings', pp)
        section = cam.add_track(unreal.MovieScene3DTransformTrack).add_section()
        section.set_range(start, start + n)
        channels = section.get_all_channels()
        keys = shot['keys']
        last_yaw = None
        interp = unreal.MovieSceneKeyInterpolation.LINEAR if len(keys) == 2 else unreal.MovieSceneKeyInterpolation.AUTO
        for key in dense(shot):
            t, eye, look = key[0], key[1], key[2]
            roll, pitch, yaw = rotation(eye, look, key[3] if len(key) > 3 and key[3] is not None else 0.0)
            if last_yaw is not None:
                while yaw - last_yaw > 180:
                    yaw -= 360
                while yaw - last_yaw < -180:
                    yaw += 360
            last_yaw = yaw
            f = unreal.FrameNumber(start + int(round(t * (n - 1))))
            for channel, value in zip(channels[:6], (eye[0], eye[1], eye[2], roll, pitch, yaw)):
                channel.add_key(f, float(value), 0.0, unreal.MovieSceneTimeUnit.DISPLAY_RATE, interp)
        cut = cuts.add_section()
        cut.set_range(start, start + n)
        cut.set_camera_binding_id(seq.get_binding_id(cam))
        start += n
    if 'anim' in data['shots'][0]:
        awakening(seq, data, starts)
    unreal.EditorAssetLibrary.save_loaded_asset(seq)
    return {'sequence': path, 'frames': total, 'starts': starts}


def render(level, width=1920, height=1080, temporal=8, warm=48, tag=None, cvars=None, sequence=None):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    out = FRAMES + '/' + (tag or level)
    os.makedirs(out, exist_ok=True)
    done = out + '/_done.json'
    if os.path.exists(done):
        os.remove(done)
    sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    queue = sub.get_queue()
    queue.delete_all_jobs()
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.job_name = level
    job.sequence = unreal.SoftObjectPath(sequence or (FOLDER + '/SEQ_T2_' + level))
    job.map = unreal.SoftObjectPath(world.get_path_name())
    cfg = job.get_configuration()
    o = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    o.output_directory = unreal.DirectoryPath(out)
    o.output_resolution = unreal.IntPoint(width, height)
    o.file_name_format = '{shot_name}.{frame_number_shot}'
    o.zero_pad_frame_numbers = 4
    o.override_existing_output = True
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_JPG)
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.spatial_sample_count = 1
    aa.temporal_sample_count = temporal
    aa.override_anti_aliasing = False
    aa.use_camera_cut_for_warm_up = False
    aa.engine_warm_up_count = warm
    aa.render_warm_up_count = warm
    aa.render_warm_up_frames = True
    con = cfg.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
    for k, v in (cvars or {}).items():
        con.add_or_update_console_variable(k, float(v))
    holder = sys.modules['unreal']
    executor = sub.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    holder._trailer_executor = executor

    def finished(ex, ok):
        open(done, 'w').write(json.dumps({'ok': bool(ok)}))
    holder._trailer_finished = finished
    executor.on_executor_finished_delegate.add_callable_unique(finished)
    return {'out': out}


def scrub(level, frame):
    """Opens the level's sequence in Sequencer and shows one frame of it in the editor world (for scout captures)."""
    lib = unreal.LevelSequenceEditorBlueprintLibrary
    seq = unreal.load_asset(FOLDER + '/SEQ_T2_' + level)
    if lib.get_current_level_sequence() != seq:
        lib.open_level_sequence(seq)
    params = unreal.MovieSceneSequencePlaybackParams()
    params.set_editor_property('frame', unreal.FrameTime(unreal.FrameNumber(int(frame))))
    params.set_editor_property('position_type', unreal.MovieScenePositionType.FRAME)
    params.set_editor_property('update_method', unreal.UpdatePositionMethod.JUMP)
    lib.set_global_position(params)
    lib.force_update()
    body = [c for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label() == 'Cine Physis' for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body']
    if body:
        h = body[0].get_socket_location('head')
        return [frame, lib.get_global_position().frame.frame_number.value, round(h.x - -68400, 1), round(h.y, 1), round(h.z - 1183.6, 1)]
    return frame


def close():
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    return True


def head():
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() == 'Cine Physis':
            for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
                if c.get_name() == 'Body':
                    h = c.get_socket_location('head')
                    return [round(h.x + 68400, 1), round(h.y, 1), round(h.z - 1183.6, 1), str(c.get_editor_property('animation_mode')), c.get_editor_property('update_animation_in_editor')]


def scrub2(level, frame):
    lib = unreal.LevelSequenceEditorBlueprintLibrary
    seq = unreal.load_asset(FOLDER + '/SEQ_T2_' + level)
    cur = lib.get_current_level_sequence()
    if cur != seq:
        lib.open_level_sequence(seq)
    lib.set_current_time(int(frame))
    lib.refresh_current_level_sequence()
    return [str(cur), lib.get_current_time(), [str(o) for o in lib.get_bound_objects(seq.get_binding_id(seq.get_bindings()[-3]))] if hasattr(lib, 'get_bound_objects') else None, [str(b.get_display_name()) for b in seq.get_bindings()]]


def realtime(on=True):
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_viewport_realtime(on)
    return on


def eye(names=('FACIAL_L_Eye', 'FACIAL_R_Eye', 'FACIAL_C_NoseTip', 'FACIAL_C_FacialRoot')):
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() == 'Cine Physis':
            for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
                if c.get_name() == 'Face':
                    out = {}
                    for n in names:
                        h = c.get_socket_location(n)
                        out[n] = [round(h.x + 68400, 1), round(h.y, 1), round(h.z - 1183.6, 1)]
                    return out


def preset(width=1920, height=1080, temporal=1, warm=48, name='MRQ_Trailer', cvars=None):
    """The saved Movie Render Queue settings the command-line render uses (Tools/trailer/render.sh)."""
    path = FOLDER + '/' + name
    lib = unreal.EditorAssetLibrary
    if lib.does_asset_exist(path):
        lib.delete_asset(path)
    cfg = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, FOLDER, unreal.MoviePipelinePrimaryConfig, None)
    o = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    o.output_directory = unreal.DirectoryPath(FRAMES + '/{sequence_name}')
    o.output_resolution = unreal.IntPoint(width, height)
    o.file_name_format = '{camera_name}.{frame_number_shot}'
    o.zero_pad_frame_numbers = 4
    o.override_existing_output = True
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_JPG)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.spatial_sample_count = 1
    aa.temporal_sample_count = temporal
    aa.override_anti_aliasing = False
    aa.use_camera_cut_for_warm_up = False
    aa.engine_warm_up_count = warm
    aa.render_warm_up_count = warm
    aa.render_warm_up_frames = True
    con = cfg.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
    for k, v in (cvars or {}).items():
        con.add_or_update_console_variable(k, float(v))
    unreal.EditorAssetLibrary.save_loaded_asset(cfg)
    return path


def face_report():
    """What the stand-in's face is driven by, and what the eye clip holds (for checking the awakening's eyes)."""
    out = {}
    clip = unreal.load_asset('/Game/Center/Cinema/A_Physis_EyesOpen')
    out['clip_length'] = clip.get_play_length()
    out['curves'] = [str(n) for n in unreal.AnimationLibrary.get_animation_curve_names(clip, unreal.RawCurveTrackTypes.RCT_FLOAT)]
    out['skeleton'] = clip.get_editor_property('skeleton').get_path_name() if hasattr(clip, 'skeleton') else '?'
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() == 'Cine Physis':
            for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
                mesh = c.get_skeletal_mesh_asset()
                out[c.get_name()] = {'mesh': mesh.get_path_name() if mesh else None, 'skeleton': mesh.get_editor_property('skeleton').get_path_name() if mesh else None,
                                     'mode': str(c.get_editor_property('animation_mode')), 'anim_class': str(c.get_editor_property('anim_class')),
                                     'post': str(mesh.get_editor_property('post_process_anim_blueprint')) if mesh else None, 'leader': str(c.get_editor_property('leader_pose_component')) if hasattr(c, 'leader_pose_component') else None}
    return out
