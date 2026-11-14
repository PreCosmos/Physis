# Movie Render Queue job (PIE executor), frames to Saved/Trailer/<name>/<frame>.jpg. Args from mrq_arg.json:
# name, map, sequence, start, end, warmup (engine warm-up frames), w, h, png, temporal (samples per frame).
import json, builtins
a = json.load(open('/home/precosmos/PhysisProject/Tools/trailer/mrq_arg.json'))
sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
queue = sub.get_queue()
for j in list(queue.get_jobs()):
    queue.delete_job(j)
job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
job.job_name = a['name']
leaf = lambda path: path + '.' + path.rsplit('/', 1)[1]
job.sequence = unreal.SoftObjectPath(leaf(a['sequence']))
job.map = unreal.SoftObjectPath(leaf(a['map']))
config = job.get_configuration()
out = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.output_directory = unreal.DirectoryPath('/home/precosmos/PhysisProject/Saved/Trailer/' + a['name'])
out.file_name_format = '{frame_number}'
out.output_resolution = unreal.IntPoint(a.get('w', 1920), a.get('h', 1080))
out.use_custom_frame_rate = True
out.output_frame_rate = unreal.FrameRate(30, 1)
out.use_custom_playback_range = True
out.custom_start_frame = a.get('start', 0)
out.custom_end_frame = a['end']
out.zero_pad_frame_numbers = 5
out.override_existing_output = True
config.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
config.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG if a.get('png') else unreal.MoviePipelineImageSequenceOutput_JPG)
aa = config.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.spatial_sample_count = 1
aa.temporal_sample_count = a.get('temporal', 1)
aa.engine_warm_up_count = a.get('warmup', 30)
aa.render_warm_up_count = 32
if a.get('gamemode', True):
    # Movie Render Queue's own game mode: no player pawn, no HUD, so no level start logic touches the shot.
    go = config.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
    for key, value in (('cinematic_quality_settings', False), ('use_lod_zero', False), ('disable_hlods', False), ('use_high_quality_shadows', False),
                       ('override_view_distance_scale', False), ('flush_grass_streaming', False), ('flush_streaming_managers', False)):
        try:
            go.set_editor_property(key, value)
        except Exception as error:
            unreal.log_warning('game override %s: %s' % (key, error))
    try:
        go.set_editor_property('texture_streaming', unreal.MoviePipelineTextureStreamingMethod.NONE)
    except Exception as error:
        unreal.log_warning('texture_streaming: %s' % error)
cv = config.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
QUALITY = {'r.MotionBlur.Amount': 0.15, 'sg.ShadowQuality': 3, 'sg.EffectsQuality': 3, 'sg.FoliageQuality': 3, 'sg.ViewDistanceQuality': 3, 'r.DetailMode': 3}
for name, value in dict(QUALITY, **a.get('cvars', {})).items():
    try:
        cv.add_or_update_console_variable(name, float(value))
    except Exception as error:
        unreal.log_warning('cvar %s: %s' % (name, error))
def finished(executor, success):
    builtins._mrq_state = {'done': True, 'ok': bool(success)}
builtins._mrq_state = {'done': False}
executor = sub.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
executor.on_executor_finished_delegate.add_callable(finished)
builtins._mrq_executor = executor
RESULT = {'rendering': sub.is_rendering(), 'job': a['name']}
