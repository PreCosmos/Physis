exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
for f in ('PhysisFire','PhysisFireDivine'):
    print('==',f);print((call('read_graph_dsl',{'graph':{'refPath':P+':'+f}},True) or '').replace('\\n','\n')[:2500])
