import json,sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/wire5.py').read().split("y=6500")[0])
found=call('find_nodes',{'graph':G,'title':'IA_Block'})
e=next(n for n in found if 'EnhancedInputAction' in n['refPath'] or 'EnhancedInputAction' in json.dumps(n)) if found else None
n=node('CallFunction|PhysisBlockEnd',0,7500)
try:
    link(e,'Completed',n)
    link(e,'Canceled',n)
except Exception as x: print('link',str(x)[:200])
call('compile_blueprint',{'blueprint':{'refPath':P}});print('wired')
