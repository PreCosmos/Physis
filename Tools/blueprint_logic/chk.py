exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
H=B+'BP_PhysisHUD.BP_PhysisHUD'
for f in ('DrawTimer','DrawCinema'):
    t=call('read_graph_dsl',{'graph':{'refPath':H+':'+f}},True) or ''
    print(f, '705.0' in t, 'Skip' in t)
