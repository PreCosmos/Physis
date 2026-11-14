import builtins, os
d = '/home/precosmos/PhysisProject/Saved/Trailer/' + __import__('json').load(open('/home/precosmos/PhysisProject/Tools/trailer/mrq_arg.json'))['name']
RESULT = {'state': getattr(builtins, '_mrq_state', None), 'rendering': unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).is_rendering(),
          'frames': len(os.listdir(d)) if os.path.isdir(d) else 0}
