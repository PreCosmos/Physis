# Rewrites only DrawObjective (pause.py source + feat boss marker + feat2 timer call).
import sys
sys.path.insert(0,'Tools')
hf=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/hudfont.py').read()
exec(hf[:hf.index("var(H,'LineY','float')")])
f2=open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/feat2.py').read()
exec(f2.split('\n')[4])
a=f2.index("fe=open("); b=f2.index("\n",f2.index("exec(d.replace(",a))
exec(f2[a:b])
comp(H)
