import sys,re
sys.path.insert(0,'Tools')
src=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/feel.py').read()
exec(src[:src.index('# Effect actors')])
cb=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read()
exec(re.search(r"^SHIPS=.*$",cb,re.M).group(0))
i=cb.index("fn(P,'PhysisCinemaCleanup'"); j=cb.index("fn(P,'PhysisCinemaStart'",i)
exec(cb[i:j].replace('(fn PhysisCinemaCleanup ()','(fn PhysisCinemaCleanup ()\n  (CallFunction|PhysisMusic)\n  (for hull (Actor|GetAllActorswithTag :Tag "CineOnly")\n    (Actor|DestroyActor :self hull))'))
comp(P)
