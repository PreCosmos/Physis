exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
D=B+'BP_TrainingDrone.BP_TrainingDrone'
for f in ('TakeHit','DroneThink'):
    t=call('read_graph_dsl',{'graph':{'refPath':D+':'+f}},True) or ''
    print(f, 'StunUntil' in t, t.count('GetStunUntil'))
