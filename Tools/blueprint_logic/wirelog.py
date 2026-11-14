import json,sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/wire5.py').read().split("y=6500")[0])
y=7200
e=node('Input|EnhancedActionEvents|IA_Pause',-400,y)
link(e,'Started',node('CallFunction|PhysisPause',0,y))
call('compile_blueprint',{'blueprint':{'refPath':P}})
print('wired')
