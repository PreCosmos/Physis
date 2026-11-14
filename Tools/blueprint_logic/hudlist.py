import json,re
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
H=B+'BP_PhysisHUD.BP_PhysisHUD'
r=json.loads(json.loads(call('list_graphs',{'blueprint':{'refPath':H}},True))['returnValue'] if False else call('list_graphs',{'blueprint':{'refPath':H}},True))['returnValue']
out={}
for g in r:
    name=g['refPath'].split(':')[-1]
    t=call('read_graph_dsl',{'graph':{'refPath':g['refPath']}},True) or ''
    t=t.replace('\\n','\n').replace('\\"','"')
    open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/hud_'+name+'.dsl','w').write(t)
    out[name]=(t.count('DrawText'), t.count('DrawRect')+t.count('DrawTexture'), len(t))
for k,v in out.items(): print(k,v)
